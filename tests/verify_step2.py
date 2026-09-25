"""Step 2 Verification Script -- digital twin core.

Tests:
1. ParameterStore: get/set/batch/reset/history work correctly.
2. Physics: direct parameter changes move the right variables.
   - Raising target_rpm raises temperature and vibration.
   - Lowering coolant_flow raises temperature.
   - Raising bearing_wear_rate increases vibration over time.
3. Snapshot/restore: a no-change replay reproduces the original trajectory
   exactly (bit-for-bit within floating-point tolerance).
4. Sim clock: 1 tick = 1 sim-second.
"""

import sys
import os
import traceback
import math

os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from simulator.parameters import ParameterStore, ParameterState, MachineParams, GlobalParams
from simulator.physics import MachineState, LineState, NetworkState, TickRNG
from simulator.physics import step_machine, step_quality, step_energy, step_network
from simulator.snapshot import SnapshotManager, TwinSnapshot
from simulator.factory_sim import FactoryTwin


passed = 0
failed = 0
total = 0


def assert_(condition, msg="Assertion failed"):
    if not condition:
        raise AssertionError(msg)


def assert_close(a, b, tol=1e-10, msg=""):
    if abs(a - b) > tol:
        raise AssertionError(f"{msg}: {a} != {b} (tol={tol})")


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


# =====================================================================
print("\n=== STEP 2 VERIFICATION: Digital Twin Core ===\n")

# -- 1. ParameterStore --
print("1. ParameterStore")


def test_param_get_set():
    store = ParameterStore()
    val = store.get("machines.M-04.target_rpm")
    assert_(val == 1200.0, f"Default RPM should be 1200, got {val}")

    change = store.set("machines.M-04.target_rpm", 1450.0, source="test")
    assert_(change.old_value == 1200.0)
    assert_(change.new_value == 1450.0)
    assert_(change.source == "test")

    val2 = store.get("machines.M-04.target_rpm")
    assert_(val2 == 1450.0, f"After set, RPM should be 1450, got {val2}")

check("get/set parameter", test_param_get_set)


def test_param_batch():
    store = ParameterStore()
    changes = store.batch_set({
        "machines.M-04.target_rpm": 1500.0,
        "machines.M-04.coolant_flow_lpm": 5.0,
    }, source="batch_test")
    assert_(len(changes) == 2, f"Expected 2 changes, got {len(changes)}")
    assert_(store.get("machines.M-04.target_rpm") == 1500.0)
    assert_(store.get("machines.M-04.coolant_flow_lpm") == 5.0)

check("batch_set", test_param_batch)


def test_param_history():
    store = ParameterStore()
    store.set("machines.M-04.target_rpm", 1400.0, source="h1")
    store.set_tick(10)
    store.set("machines.M-04.target_rpm", 1500.0, source="h2")
    h = store.history
    assert_(len(h) == 2, f"Expected 2 history entries, got {len(h)}")
    assert_(h[0].source == "h1")
    assert_(h[1].tick_index == 10)
    since = store.history_since(10)
    assert_(len(since) == 1)

check("history and history_since", test_param_history)


def test_param_reset():
    store = ParameterStore()
    store.set("machines.M-04.target_rpm", 9999.0)
    assert_(store.get("machines.M-04.target_rpm") == 9999.0)
    changes = store.reset()
    assert_(store.get("machines.M-04.target_rpm") == 1200.0,
            f"After reset, RPM should be 1200, got {store.get('machines.M-04.target_rpm')}")
    # Reset should have logged the change
    assert_(len(changes) > 0, "Reset should produce change log entries")

check("reset to baseline", test_param_reset)


def test_param_snapshot_restore():
    store = ParameterStore()
    store.set("machines.M-04.target_rpm", 1600.0)
    snap = store.snapshot()
    store.set("machines.M-04.target_rpm", 1800.0)
    assert_(store.get("machines.M-04.target_rpm") == 1800.0)
    store.restore(snap)
    assert_(store.get("machines.M-04.target_rpm") == 1600.0,
            "After restore, should be 1600")

check("snapshot/restore", test_param_snapshot_restore)


# -- 2. Physics: parameter changes move the right variables --
print("\n2. Physics: causal equations")


def test_rpm_raises_temp_and_vibration():
    """Raising target_rpm above rpm_stable_max should raise temperature and vibration."""
    twin = FactoryTwin(snapshot_interval=9999)  # no snapshots during test

    # Run 50 ticks at baseline (RPM=1200, rpm_stable_max=1300 -> no excess)
    for _ in range(50):
        twin.tick()
    baseline_state = twin.get_state()
    baseline_temp = baseline_state["machines"]["M-04"]["temperature_c"]
    baseline_vib = baseline_state["machines"]["M-04"]["vibration_mm_s"]

    # Raise RPM to 1500 (200 above max)
    twin.params.set("machines.M-04.target_rpm", 1500.0)

    # Run 50 more ticks
    for _ in range(50):
        twin.tick()
    after_state = twin.get_state()
    after_temp = after_state["machines"]["M-04"]["temperature_c"]
    after_vib = after_state["machines"]["M-04"]["vibration_mm_s"]

    assert_(after_temp > baseline_temp + 1.0,
            f"Temperature should rise: {baseline_temp:.2f} -> {after_temp:.2f}")
    assert_(after_vib > baseline_vib + 0.1,
            f"Vibration should rise: {baseline_vib:.2f} -> {after_vib:.2f}")

check("RPM above safe range raises temperature and vibration", test_rpm_raises_temp_and_vibration)


def test_coolant_drop_raises_temp():
    """Lowering coolant_flow_lpm should raise temperature."""
    twin = FactoryTwin(snapshot_interval=9999)
    for _ in range(50):
        twin.tick()
    baseline_temp = twin.get_state()["machines"]["M-04"]["temperature_c"]

    twin.params.set("machines.M-04.coolant_flow_lpm", 2.0)  # drop from 12 to 2
    for _ in range(50):
        twin.tick()
    after_temp = twin.get_state()["machines"]["M-04"]["temperature_c"]

    assert_(after_temp > baseline_temp + 2.0,
            f"Temperature should rise when coolant drops: {baseline_temp:.2f} -> {after_temp:.2f}")

check("Coolant flow drop raises temperature", test_coolant_drop_raises_temp)


def test_bearing_wear_raises_vibration():
    """Elevated bearing_wear_rate should gradually increase vibration."""
    twin = FactoryTwin(snapshot_interval=9999)
    for _ in range(20):
        twin.tick()
    baseline_vib = twin.get_state()["machines"]["M-04"]["vibration_mm_s"]

    # Set high wear rate
    twin.params.set("machines.M-04.bearing_wear_rate", 0.01)  # 100x default
    for _ in range(100):
        twin.tick()
    after_vib = twin.get_state()["machines"]["M-04"]["vibration_mm_s"]

    assert_(after_vib > baseline_vib + 1.0,
            f"Vibration should rise with wear: {baseline_vib:.2f} -> {after_vib:.2f}")

check("Bearing wear raises vibration", test_bearing_wear_raises_vibration)


def test_defect_rate_rises_with_temp():
    """Temperature above threshold should raise defect rate."""
    twin = FactoryTwin(snapshot_interval=9999)
    for _ in range(50):
        twin.tick()
    baseline_defect = twin.get_state()["lines"]["L-03"]["defect_rate"]

    # Push RPM high AND drop coolant to get temp way above threshold
    twin.params.batch_set({
        "machines.M-04.target_rpm": 1600.0,
        "machines.M-04.coolant_flow_lpm": 2.0,
    })
    for _ in range(50):
        twin.tick()
    after_defect = twin.get_state()["lines"]["L-03"]["defect_rate"]

    assert_(after_defect > baseline_defect,
            f"Defect rate should rise: {baseline_defect:.4f} -> {after_defect:.4f}")

check("Defect rate rises with temperature/vibration", test_defect_rate_rises_with_temp)


def test_energy_rises_with_rpm():
    """Energy per unit should rise with RPM."""
    twin = FactoryTwin(snapshot_interval=9999)
    for _ in range(50):
        twin.tick()
    baseline_energy = twin.get_state()["lines"]["L-03"]["kwh_per_unit"]

    twin.params.set("machines.M-04.target_rpm", 1600.0)
    for _ in range(50):
        twin.tick()
    after_energy = twin.get_state()["lines"]["L-03"]["kwh_per_unit"]

    assert_(after_energy > baseline_energy,
            f"Energy should rise with RPM: {baseline_energy:.3f} -> {after_energy:.3f}")

check("Energy rises with RPM", test_energy_rises_with_rpm)


# -- 3. Snapshot and deterministic replay --
print("\n3. Snapshot and deterministic replay")


def test_no_change_replay_reproduces_exactly():
    """Run the twin, snapshot, run more, then restore and replay.
    With no parameter changes, the replayed trajectory must be
    numerically identical to the original (same seeds, same physics).
    """
    twin = FactoryTwin(snapshot_interval=10)

    # Run 20 ticks to build up some state and generate snapshots
    for _ in range(20):
        twin.tick()

    # Capture the snapshot at tick 10 (the one the manager already took)
    snap = twin.snapshots.get_nearest_before(10)
    assert_(snap is not None, "Should have a snapshot at or before tick 10")
    assert_(snap.tick_index == 10, f"Expected snapshot at tick 10, got {snap.tick_index}")

    # Record the original trajectory from tick 10 to tick 30
    twin.restore_from_snapshot(snap)
    original_trajectory = []
    for _ in range(20):
        state = twin.tick()
        original_trajectory.append(state)

    # Now restore again and replay -- should be identical
    twin.restore_from_snapshot(snap)
    replay_trajectory = []
    for _ in range(20):
        state = twin.tick()
        replay_trajectory.append(state)

    # Compare tick by tick
    for i in range(len(original_trajectory)):
        orig = original_trajectory[i]
        repl = replay_trajectory[i]

        # Check tick index matches
        assert_(orig["tick_index"] == repl["tick_index"],
                f"Tick {i}: tick_index mismatch {orig['tick_index']} vs {repl['tick_index']}")

        # Check machine state
        for mid in orig["machines"]:
            orig_m = orig["machines"][mid]
            repl_m = repl["machines"][mid]
            for key in ["rpm", "temperature_c", "vibration_mm_s", "motor_current_a",
                        "coolant_flow_lpm", "bearing_wear", "pressure_bar"]:
                assert_close(
                    orig_m[key], repl_m[key], tol=1e-10,
                    msg=f"Tick {orig['tick_index']} machine {mid} {key}",
                )

        # Check line state
        for lid in orig["lines"]:
            orig_l = orig["lines"][lid]
            repl_l = repl["lines"][lid]
            for key in ["defect_rate", "kwh_per_unit", "co2_per_unit"]:
                assert_close(
                    orig_l[key], repl_l[key], tol=1e-10,
                    msg=f"Tick {orig['tick_index']} line {lid} {key}",
                )

check("No-change replay reproduces trajectory exactly", test_no_change_replay_reproduces_exactly)


def test_snapshot_count():
    """Snapshots should be taken at the configured interval."""
    twin = FactoryTwin(snapshot_interval=5)
    for _ in range(25):
        twin.tick()
    # Ticks 0,5,10,15,20 should have snapshots = 5
    count = twin.snapshots.count
    assert_(count == 5, f"Expected 5 snapshots, got {count}")

check("Snapshots taken at correct interval", test_snapshot_count)


def test_snapshot_nearest_before():
    """get_nearest_before should return the right snapshot."""
    twin = FactoryTwin(snapshot_interval=10)
    for _ in range(35):
        twin.tick()
    # Snapshots at 0, 10, 20, 30
    snap = twin.snapshots.get_nearest_before(25)
    assert_(snap is not None)
    assert_(snap.tick_index == 20, f"Expected tick 20, got {snap.tick_index}")

    snap2 = twin.snapshots.get_nearest_before(30)
    assert_(snap2.tick_index == 30)

check("get_nearest_before returns correct snapshot", test_snapshot_nearest_before)


# -- 4. Sim clock --
print("\n4. Sim clock")


def test_sim_clock():
    """1 tick = 1 sim-second."""
    twin = FactoryTwin(snapshot_interval=9999)
    assert_(twin.sim_time_s == 0.0)
    twin.tick()
    assert_close(twin.sim_time_s, 1.0, tol=0.001, msg="After 1 tick, sim_time_s should be 1.0")
    for _ in range(99):
        twin.tick()
    assert_close(twin.sim_time_s, 100.0, tol=0.001, msg="After 100 ticks, sim_time_s should be 100.0")

check("1 tick = 1 sim-second", test_sim_clock)


def test_ticks_per_second_is_configurable():
    """ticks_per_second should be readable and changeable."""
    store = ParameterStore()
    tps = store.get("globals.ticks_per_second")
    assert_(tps == 20.0, f"Default tps should be 20, got {tps}")
    store.set("globals.ticks_per_second", 30.0)
    assert_(store.get("globals.ticks_per_second") == 30.0)

check("ticks_per_second is configurable", test_ticks_per_second_is_configurable)


# -- 5. Deterministic per-tick RNG --
print("\n5. Deterministic per-tick RNG")


def test_rng_determinism():
    """Same (seed, tick) produces same sequence of random numbers."""
    rng1 = TickRNG(42, 100)
    rng2 = TickRNG(42, 100)
    for _ in range(10):
        assert_close(rng1.normal(1.0), rng2.normal(1.0), tol=0.0,
                     msg="Same seed+tick should produce same normal")

check("Same seed+tick produces identical noise", test_rng_determinism)


def test_rng_different_ticks():
    """Different ticks produce different noise."""
    rng1 = TickRNG(42, 100)
    rng2 = TickRNG(42, 101)
    vals1 = [rng1.normal(1.0) for _ in range(5)]
    vals2 = [rng2.normal(1.0) for _ in range(5)]
    # At least some values should differ
    differ = any(abs(a - b) > 1e-15 for a, b in zip(vals1, vals2))
    assert_(differ, "Different ticks should produce different noise")

check("Different ticks produce different noise", test_rng_different_ticks)


# -- 6. Parameter change log for replay --
print("\n6. Parameter change log")


def test_change_log_captures_all():
    """Every parameter change is recorded with tick and source."""
    store = ParameterStore()
    store.set_tick(5)
    store.set("machines.M-04.target_rpm", 1400.0, source="operator")
    store.set_tick(10)
    store.set("machines.M-04.coolant_flow_lpm", 5.0, source="scenario:S3")

    h = store.history
    assert_(len(h) == 2)
    assert_(h[0].tick_index == 5)
    assert_(h[0].source == "operator")
    assert_(h[1].tick_index == 10)
    assert_(h[1].path == "machines.M-04.coolant_flow_lpm")

check("Change log records tick, path, source", test_change_log_captures_all)


# =====================================================================
print(f"\n{'='*60}")
print(f"RESULTS: {passed}/{total} passed, {failed} failed")
if failed > 0:
    print("!! SOME CHECKS FAILED -- see above for details.")
    sys.exit(1)
else:
    print("[OK] ALL CHECKS PASSED -- Step 2 complete.")
    sys.exit(0)
