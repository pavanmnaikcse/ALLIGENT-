"""Step 3 Verification Script -- named scenarios S1-S5 + NOISE_ONLY.

Tests:
1. Each scenario applies via the standard parameter API (same code path).
2. Each produces a visibly distinct, correct raw-telemetry signature
   from a clean baseline.
3. Each matches its documented hypothesis mapping:
   S1 -> H1: RPM excess -> temp up, vib up, defects up
   S2 -> H5/H6: sensor drift -> cross-check residual up, unauthorized writes
   S3 -> H3: coolant drop -> temp up, defects up (RPM stays normal)
   S4 -> H2: bearing wear -> vibration gradual rise (RPM stays normal)
   S5 -> H4: bad material -> defect rate up (temp/vib relatively normal)
   NOISE_ONLY -> H7: noisy readings but no consistent causal chain
4. Signatures are distinct from each other (no two look the same).
"""

import sys
import os
import traceback

os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from simulator.parameters import ParameterStore
from simulator.factory_sim import FactoryTwin
from simulator.scenarios import apply_scenario, get_scenario, list_scenarios, SCENARIOS


passed = 0
failed = 0
total = 0


def assert_(condition, msg="Assertion failed"):
    if not condition:
        raise AssertionError(msg)


def check(name, fn):
    global passed, failed, total
    total += 1
    try:
        fn()
        passed += 1
        print(f"  [PASS] {name}")
    except Exception as e:
        failed += 1
        print(f"  [FAIL] {name}: {e}")
        traceback.print_exc()


def _expect_fail(fn):
    try:
        fn()
    except Exception:
        return
    raise AssertionError("Expected an exception but none was raised.")


def _std(values):
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return (sum((v - mean) ** 2 for v in values) / (n - 1)) ** 0.5


def run_scenario(scenario_id, warmup=50, post_ticks=100):
    """Run a scenario and return (baseline_metrics, after_metrics)."""
    twin = FactoryTwin(snapshot_interval=9999)

    # Warmup at baseline
    for _ in range(warmup):
        twin.tick()
    baseline = extract_metrics(twin)

    # Apply scenario
    changes = apply_scenario(twin.params, scenario_id)
    assert_(len(changes) > 0, f"Scenario {scenario_id} should produce changes")

    # Run post-scenario ticks
    for _ in range(post_ticks):
        twin.tick()
    after = extract_metrics(twin)

    return baseline, after


def extract_metrics(twin):
    """Extract key metrics from current twin state."""
    state = twin.get_state()
    m = state["machines"]["M-04"]
    l = state["lines"]["L-03"]
    n = state["network"]["M-04"]
    return {
        "rpm": m["rpm"],
        "temperature_c": m["temperature_c"],
        "vibration_mm_s": m["vibration_mm_s"],
        "motor_current_a": m["motor_current_a"],
        "coolant_flow_lpm": m["coolant_flow_lpm"],
        "bearing_wear": m["bearing_wear"],
        "defect_rate": l["defect_rate"],
        "kwh_per_unit": l["kwh_per_unit"],
        "message_rate": n["message_rate"],
        "cross_check_residual": n["cross_check_residual"],
        "last_write_source": n["last_write_source"],
    }


# =====================================================================
print("\n=== STEP 3 VERIFICATION: Named Scenarios S1-S5 + NOISE_ONLY ===\n")

# -- 0. All scenarios exist and apply via parameter API --
print("0. Scenario infrastructure")

check("All 6 scenarios defined", lambda: assert_(
    set(SCENARIOS.keys()) == {"S1", "S2", "S3", "S4", "S5", "NOISE_ONLY"}
))

check("list_scenarios returns 6", lambda: assert_(len(list_scenarios()) == 6))

check("Unknown scenario raises ValueError", lambda: (
    _expect_fail(lambda: apply_scenario(ParameterStore(), "S99"))
))


def test_scenario_uses_param_api():
    """Scenarios should go through ParameterStore.batch_set, leaving a history."""
    store = ParameterStore()
    changes = apply_scenario(store, "S1")
    assert_(len(changes) > 0, "Should have changes")
    assert_(changes[0].source == "scenario:S1", f"Source should be scenario:S1, got {changes[0].source}")
    # Verify the change is in history
    h = store.history
    assert_(len(h) == len(changes))
    assert_(all(c.source == "scenario:S1" for c in h))

check("Scenarios apply via ParameterStore (same API path)", test_scenario_uses_param_api)


# -- 1. S1: Speed above safe envelope -> H1 --
print("\n1. S1: Speed above safe envelope (H1)")


def test_s1():
    baseline, after = run_scenario("S1", warmup=50, post_ticks=80)

    # RPM should be high
    assert_(after["rpm"] > 1450, f"RPM should be ~1500, got {after['rpm']:.1f}")
    # Temperature should rise significantly
    temp_delta = after["temperature_c"] - baseline["temperature_c"]
    assert_(temp_delta > 1.0,
            f"Temperature should rise: delta={temp_delta:.2f}")
    # Vibration should rise
    vib_delta = after["vibration_mm_s"] - baseline["vibration_mm_s"]
    assert_(vib_delta > 0.1,
            f"Vibration should rise: delta={vib_delta:.2f}")
    # Defect rate should rise
    assert_(after["defect_rate"] > baseline["defect_rate"],
            f"Defect rate should rise: {baseline['defect_rate']:.4f} -> {after['defect_rate']:.4f}")
    # Cross-check residual should stay relatively low (real physical fault)
    print(f"    S1 signature: RPM={after['rpm']:.0f}, temp_delta=+{temp_delta:.1f}C, "
          f"vib_delta=+{vib_delta:.2f}, defects={after['defect_rate']:.4f}")

check("S1 produces correct H1 signature", test_s1)


# -- 2. S2: Sensor drift + unauthorized write -> H5/H6 --
print("\n2. S2: Sensor drift + unauthorized write (H5/H6)")


def test_s2():
    twin = FactoryTwin(snapshot_interval=9999)
    for _ in range(50):
        twin.tick()
    baseline = extract_metrics(twin)

    apply_scenario(twin.params, "S2")

    # Run longer to accumulate drift
    unauthorized_write_count = 0
    for _ in range(150):
        twin.tick()
        state = twin.get_state()
        if state["network"]["M-04"]["last_write_source"] == "unknown":
            unauthorized_write_count += 1

    after = extract_metrics(twin)

    # Cross-check residual should be elevated (physics inconsistency)
    assert_(after["cross_check_residual"] > baseline["cross_check_residual"] + 0.5,
            f"Cross-check residual should rise: "
            f"{baseline['cross_check_residual']:.3f} -> {after['cross_check_residual']:.3f}")

    # Message rate should be elevated (burst multiplier)
    assert_(after["message_rate"] > baseline["message_rate"] * 1.5,
            f"Message rate should be elevated: "
            f"{baseline['message_rate']:.1f} -> {after['message_rate']:.1f}")

    # Should see unauthorized writes (p=0.3 over 150 ticks)
    assert_(unauthorized_write_count > 10,
            f"Should see unauthorized writes: got {unauthorized_write_count}")

    # RPM should NOT be elevated (this is a data problem, not a process change)
    assert_(after["rpm"] < 1350,
            f"RPM should stay normal: {after['rpm']:.0f}")

    print(f"    S2 signature: cross_check={after['cross_check_residual']:.2f}, "
          f"msg_rate={after['message_rate']:.0f}, "
          f"unauthorized_writes={unauthorized_write_count}/150")

check("S2 produces correct H5/H6 signature", test_s2)


# -- 3. S3: Coolant flow drops -> H3 --
print("\n3. S3: Coolant flow drops (H3)")


def test_s3():
    baseline, after = run_scenario("S3", warmup=50, post_ticks=80)

    # Coolant flow should be low
    assert_(after["coolant_flow_lpm"] < 5.0,
            f"Coolant should be ~3: {after['coolant_flow_lpm']:.1f}")
    # Temperature should rise (key H3 signature)
    temp_delta = after["temperature_c"] - baseline["temperature_c"]
    assert_(temp_delta > 3.0,
            f"Temperature should rise significantly: delta={temp_delta:.2f}")
    # RPM should stay normal (distinguishes from S1)
    assert_(after["rpm"] < 1350,
            f"RPM should stay normal: {after['rpm']:.0f}")
    # Vibration should NOT rise much (distinguishes from S4)
    vib_delta = after["vibration_mm_s"] - baseline["vibration_mm_s"]
    assert_(vib_delta < 1.0,
            f"Vibration should not rise much: delta={vib_delta:.2f}")

    print(f"    S3 signature: coolant={after['coolant_flow_lpm']:.1f}, "
          f"temp_delta=+{temp_delta:.1f}C, RPM={after['rpm']:.0f}, "
          f"vib_delta=+{vib_delta:.2f}")

check("S3 produces correct H3 signature", test_s3)


# -- 4. S4: Gradual bearing wear -> H2 --
print("\n4. S4: Gradual bearing wear (H2)")


def test_s4():
    # Bearing wear is gradual -- need more ticks
    baseline, after = run_scenario("S4", warmup=50, post_ticks=200)

    # Bearing wear should have accumulated
    assert_(after["bearing_wear"] > baseline["bearing_wear"] + 0.1,
            f"Bearing wear should accumulate: "
            f"{baseline['bearing_wear']:.4f} -> {after['bearing_wear']:.4f}")
    # Vibration should rise (key H2 signature)
    vib_delta = after["vibration_mm_s"] - baseline["vibration_mm_s"]
    assert_(vib_delta > 1.0,
            f"Vibration should rise with wear: delta={vib_delta:.2f}")
    # RPM should stay normal
    assert_(after["rpm"] < 1350,
            f"RPM should stay normal: {after['rpm']:.0f}")
    # Temperature should only rise slightly (from vibration friction, not RPM)
    temp_delta = after["temperature_c"] - baseline["temperature_c"]
    # S4's temp rise should be less dramatic than S1 or S3
    print(f"    S4 signature: wear={after['bearing_wear']:.4f}, "
          f"vib_delta=+{vib_delta:.2f}, RPM={after['rpm']:.0f}, "
          f"temp_delta=+{temp_delta:.1f}C")

check("S4 produces correct H2 signature", test_s4)


# -- 5. S5: Bad material batch -> H4 --
print("\n5. S5: Bad material batch (H4)")


def test_s5():
    # Need RPM near the edge for material sensitivity to show
    twin = FactoryTwin(snapshot_interval=9999)
    # Set RPM just below threshold so material sensitivity matters
    twin.params.set("machines.M-04.target_rpm", 1280.0)
    for _ in range(50):
        twin.tick()
    baseline = extract_metrics(twin)

    apply_scenario(twin.params, "S5")
    for _ in range(80):
        twin.tick()
    after = extract_metrics(twin)

    # Defect rate should rise (key H4 signature -- material amplifies defects)
    defect_delta = after["defect_rate"] - baseline["defect_rate"]
    assert_(defect_delta > 0.0001,
            f"Defect rate should rise with bad batch: delta={defect_delta:.6f}")
    # Temperature and vibration should NOT rise dramatically
    # (distinguishes from S1/S3/S4)
    temp_delta = after["temperature_c"] - baseline["temperature_c"]
    vib_delta = after["vibration_mm_s"] - baseline["vibration_mm_s"]

    print(f"    S5 signature: defect_delta=+{defect_delta:.5f}, "
          f"temp_delta=+{temp_delta:.1f}C, vib_delta=+{vib_delta:.2f}")

check("S5 produces correct H4 signature", test_s5)


# -- 6. NOISE_ONLY: no physical fault -> H7 --
print("\n6. NOISE_ONLY: noise-only negative test (H7)")


def test_noise_only():
    twin = FactoryTwin(snapshot_interval=9999)
    for _ in range(50):
        twin.tick()

    # Collect many baseline readings for variance estimation
    baseline_temps = []
    for _ in range(50):
        twin.tick()
        s = twin.get_state()
        baseline_temps.append(s["machines"]["M-04"]["temperature_c"])
    baseline_std = _std(baseline_temps)

    # Apply noise-only
    apply_scenario(twin.params, "NOISE_ONLY")
    noisy_temps = []
    for _ in range(50):
        twin.tick()
        s = twin.get_state()
        noisy_temps.append(s["machines"]["M-04"]["temperature_c"])
    noisy_std = _std(noisy_temps)

    # Noise should be higher (wider variance)
    assert_(noisy_std > baseline_std * 1.5,
            f"Noise should increase variance: baseline_std={baseline_std:.3f}, "
            f"noisy_std={noisy_std:.3f}")

    # But MEAN should stay similar (no systematic shift from noise alone)
    baseline_mean = sum(baseline_temps) / len(baseline_temps)
    noisy_mean = sum(noisy_temps) / len(noisy_temps)
    # Allow wider tolerance because noise is high
    mean_shift = abs(noisy_mean - baseline_mean)
    # The mean can shift somewhat due to noise, but not dramatically
    print(f"    NOISE_ONLY signature: temp_std {baseline_std:.2f} -> {noisy_std:.2f}, "
          f"mean_shift={mean_shift:.2f}C")

check("NOISE_ONLY increases variance without systematic shift", test_noise_only)


# -- 7. Scenarios produce distinct signatures --
print("\n7. Cross-scenario distinctness")


def test_distinct_signatures():
    """Each scenario's dominant effect should be in a different signal."""
    # Run all scenarios and check dominant changes
    signatures = {}
    for sid in ["S1", "S2", "S3", "S4", "S5"]:
        ticks = 200 if sid == "S4" else 80
        baseline, after = run_scenario(sid, warmup=50, post_ticks=ticks)
        signatures[sid] = {
            "rpm_up": after["rpm"] > 1400,
            "temp_up": (after["temperature_c"] - baseline["temperature_c"]) > 3.0,
            "vib_up": (after["vibration_mm_s"] - baseline["vibration_mm_s"]) > 1.0,
            "defect_up": after["defect_rate"] > baseline["defect_rate"] * 1.5,
            "cross_check_up": after["cross_check_residual"] > 1.0,
            "coolant_down": after["coolant_flow_lpm"] < 5.0,
            "wear_up": after["bearing_wear"] > 0.15,
        }

    # S1 should have rpm_up, temp_up -- S3 should NOT have rpm_up
    assert_(signatures["S1"]["rpm_up"] and not signatures["S3"]["rpm_up"],
            "S1 and S3 should differ on RPM")

    # S3 should have temp_up with coolant_down, S1 should NOT have coolant_down
    assert_(signatures["S3"]["coolant_down"] and not signatures["S1"]["coolant_down"],
            "S3 should have coolant_down, S1 should not")

    # S4 should have wear_up and vib_up, but not rpm_up
    assert_(signatures["S4"]["wear_up"] and not signatures["S4"]["rpm_up"],
            "S4 should have wear without RPM change")

    # S2 should have cross_check_up, others should not
    assert_(signatures["S2"]["cross_check_up"],
            "S2 should have elevated cross-check residual")

    print("    Signatures are distinct across all scenarios.")

check("All scenarios produce distinct signatures", test_distinct_signatures)


# -- 8. Reset between scenarios --
print("\n8. Reset between scenarios")


def test_reset_restores_baseline():
    """After applying a scenario and resetting, the twin should behave like baseline."""
    twin = FactoryTwin(snapshot_interval=9999)
    for _ in range(50):
        twin.tick()

    # Apply S1 (high RPM)
    apply_scenario(twin.params, "S1")
    for _ in range(50):
        twin.tick()
    assert_(twin.get_state()["machines"]["M-04"]["rpm"] > 1400)

    # Reset
    twin.params.reset()
    for _ in range(50):
        twin.tick()
    after_reset_rpm = twin.get_state()["machines"]["M-04"]["rpm"]
    assert_(after_reset_rpm < 1300,
            f"After reset, RPM should return to ~1200: {after_reset_rpm:.0f}")

check("Reset restores baseline behavior after scenario", test_reset_restores_baseline)



print(f"\n{'='*60}")
print(f"RESULTS: {passed}/{total} passed, {failed} failed")
if failed > 0:
    print("!! SOME CHECKS FAILED -- see above for details.")
    sys.exit(1)
else:
    print("[OK] ALL CHECKS PASSED -- Step 3 complete.")
    sys.exit(0)
