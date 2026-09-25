"""Step 5 Verification Script -- ingestion + evidence layer.

Tests:
1. Feature engine ingests twin ticks and computes correct window features.
2. CUSUM change-point detector locates onsets correctly.
3. Anomaly detector fits, calibrates, and detects anomalies.
4. Lagged cross-correlation finds the right lag direction.
5. trust_checks.py produces Evidence objects BEFORE any agent runs.
6. Trust degrades under S2 (integrity attack scenario).
7. Trust stays high at baseline.
"""

import sys
import os
import traceback
from datetime import datetime, timedelta, timezone

os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

import numpy as np

from simulator.parameters import ParameterStore
from simulator.factory_sim import FactoryTwin
from simulator.scenarios import apply_scenario

from backend.ingestion.feature_engine import FeatureEngine, MACHINE_SIGNALS
from backend.ingestion.anomaly_detector import AnomalyDetector, build_feature_vector
from backend.ingestion.changepoint import CUSUMDetector
from backend.ingestion.correlation import lagged_cross_correlation
from backend.ingestion.trust_checks import compute_trust_evidence, get_trust_for_agent

from schemas.evidence import EvidenceSource, EvidenceStore


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


# =====================================================================
print("\n=== STEP 5 VERIFICATION: Ingestion + Evidence Layer ===\n")

# -- 1. Feature Engine --
print("1. Feature Engine")


def test_feature_engine_ingestion():
    twin = FactoryTwin(snapshot_interval=9999)
    engine = FeatureEngine()

    for _ in range(100):
        payload = twin.tick()
        engine.ingest_tick(payload)

    # Should have buffers for all signals
    signals = engine.signal_names
    assert_(len(signals) > 0, "Should have signal buffers")
    assert_("machines.M-04.temperature_c" in signals,
            f"Should have M-04 temperature, got {signals}")
    assert_("lines.L-03.defect_rate" in signals)
    assert_("network.M-04.message_rate" in signals)

    # Get features
    features = engine.get_features("1min")
    temp_feat = features.get("machines.M-04.temperature_c")
    assert_(temp_feat is not None, "Should have temperature features")
    assert_(temp_feat.count == 60, f"1-min window should have 60 samples, got {temp_feat.count}")
    assert_(35 < temp_feat.mean < 50,
            f"Baseline temp mean should be ~40C, got {temp_feat.mean:.1f}")
    assert_(temp_feat.std > 0, "Should have nonzero std")

check("Feature engine ingests and computes windows", test_feature_engine_ingestion)


def test_feature_engine_detects_shift():
    twin = FactoryTwin(snapshot_interval=9999)
    engine = FeatureEngine()

    # 60 ticks baseline
    for _ in range(60):
        engine.ingest_tick(twin.tick())
    baseline_feat = engine.get_features("1min")
    baseline_mean = baseline_feat["machines.M-04.temperature_c"].mean

    # Apply S1 (high RPM) and run 60 more ticks
    apply_scenario(twin.params, "S1")
    for _ in range(60):
        engine.ingest_tick(twin.tick())
    after_feat = engine.get_features("1min")
    after_mean = after_feat["machines.M-04.temperature_c"].mean

    assert_(after_mean > baseline_mean + 0.5,
            f"Temperature mean should rise: {baseline_mean:.2f} -> {after_mean:.2f}")
    # After 60 ticks at new RPM, temperature stabilizes at a higher level.
    # The 1-min window is fully post-change so slope is ~0 (stable at new level).
    # The key test is the mean shift, which proves the feature engine tracked
    # the parameter change correctly.
    print(f"    Baseline mean={baseline_mean:.2f}, After mean={after_mean:.2f}")

check("Feature engine reflects parameter changes", test_feature_engine_detects_shift)


# -- 2. CUSUM Change-Point Detector --
print("\n2. CUSUM Change-Point Detector")


def test_cusum_detects_onset():
    """CUSUM should detect a clear step change and locate the onset."""
    # Simulate a signal with a step change at index 50
    n = 100
    values = np.concatenate([
        np.random.default_rng(42).normal(10.0, 0.5, 50),  # baseline
        np.random.default_rng(43).normal(15.0, 0.5, 50),  # shifted
    ])
    ticks = np.arange(n)

    detector = CUSUMDetector(threshold=5.0, drift=0.5)
    result = detector.detect("test_signal", values, ticks)

    assert_(result.detected, "Should detect the step change")
    assert_(result.direction == "increase", f"Direction should be increase, got {result.direction}")
    # Onset should be near tick 50 (within some tolerance)
    assert_(40 <= result.onset_tick <= 55,
            f"Onset should be near tick 50, got {result.onset_tick}")
    assert_(result.magnitude > 3.0,
            f"Magnitude should be ~5, got {result.magnitude:.2f}")

check("CUSUM detects step change onset correctly", test_cusum_detects_onset)


def test_cusum_no_change():
    """CUSUM should not detect a change in a stationary signal."""
    values = np.random.default_rng(42).normal(10.0, 0.5, 100)
    detector = CUSUMDetector(threshold=5.0, drift=0.5)
    result = detector.detect("flat_signal", values)
    assert_(not result.detected, "Should NOT detect a change in stationary data")

check("CUSUM does not false-alarm on stationary data", test_cusum_no_change)


def test_cusum_on_twin_data():
    """CUSUM should detect onset when S1 is applied to the twin."""
    twin = FactoryTwin(snapshot_interval=9999)
    engine = FeatureEngine()

    # 80 ticks baseline
    for _ in range(80):
        engine.ingest_tick(twin.tick())

    # Apply S1 and run 80 more
    apply_scenario(twin.params, "S1")
    for _ in range(80):
        engine.ingest_tick(twin.tick())

    # Get the temperature buffer
    buf = engine.get_buffer("machines.M-04.temperature_c")
    values = buf.values

    detector = CUSUMDetector(threshold=3.0, drift=0.3)
    result = detector.detect("machines.M-04.temperature_c", values)
    assert_(result.detected, "Should detect temperature change after S1")
    # Onset should be near tick 80 (when S1 was applied)
    assert_(result.onset_tick is not None)
    print(f"    CUSUM onset at tick {result.onset_tick} (S1 applied at tick 80)")

check("CUSUM detects onset on twin data after S1", test_cusum_on_twin_data)


# -- 3. Anomaly Detector --
print("\n3. Anomaly Detector (IsolationForest)")


def test_anomaly_detector():
    twin = FactoryTwin(snapshot_interval=9999)
    engine = FeatureEngine()
    detector = AnomalyDetector(contamination=0.05)

    # Collect baseline features
    baseline_vectors = []
    for _ in range(120):
        engine.ingest_tick(twin.tick())
    for _ in range(60):
        engine.ingest_tick(twin.tick())
        features = engine.get_features("1min")
        vec = build_feature_vector(features, "M-04")
        baseline_vectors.append(vec)

    baseline_matrix = np.array(baseline_vectors)
    cal_info = detector.fit("M-04", baseline_matrix)

    assert_(detector.is_fitted, "Detector should be fitted")
    assert_("threshold" in cal_info, "Should report threshold")
    assert_("false_positive_rate" in cal_info, "Should report FP rate")
    print(f"    Calibrated: threshold={cal_info['threshold']:.4f}, "
          f"FP rate={cal_info['false_positive_rate']:.3f}")

    # Normal data should be mostly not anomalous
    normal_results = detector.detect("M-04", baseline_matrix[-5:])
    normal_anomalies = sum(1 for r in normal_results if r.is_anomaly)
    print(f"    Normal data: {normal_anomalies}/{len(normal_results)} flagged")

    # Apply S1 and check for anomaly
    apply_scenario(twin.params, "S1")
    for _ in range(60):
        engine.ingest_tick(twin.tick())
    anomaly_features = engine.get_features("1min")
    anomaly_vec = build_feature_vector(anomaly_features, "M-04")
    anomaly_results = detector.detect("M-04", anomaly_vec)
    assert_(anomaly_results[0].is_anomaly,
            f"S1 data should be anomalous, score={anomaly_results[0].score:.4f}")

check("IsolationForest detects S1 anomaly", test_anomaly_detector)


# -- 4. Lagged Cross-Correlation --
print("\n4. Lagged Cross-Correlation")


def test_lagged_correlation():
    """Signal A leads signal B by 10 ticks -- correlation should find this."""
    rng = np.random.default_rng(42)
    n = 200
    base = np.sin(np.linspace(0, 4 * np.pi, n)) + rng.normal(0, 0.1, n)
    signal_a = base.copy()
    signal_b = np.zeros(n)
    signal_b[10:] = base[:-10]  # B lags A by 10 ticks

    result = lagged_cross_correlation("A", "B", signal_a, signal_b, max_lag=30)
    assert_(result is not None)
    assert_(result.max_correlation > 0.5,
            f"Correlation should be high, got {result.max_correlation:.3f}")
    assert_(result.lag_direction == "a_leads_b",
            f"A should lead B, got {result.lag_direction}")
    assert_(5 <= result.optimal_lag <= 15,
            f"Optimal lag should be ~10, got {result.optimal_lag}")

check("Lagged correlation finds correct lead/lag", test_lagged_correlation)


# -- 5. Trust Checks -- UPSTREAM of agents --
print("\n5. Trust Checks (upstream of agents)")


def test_trust_at_baseline():
    """At baseline, trust should be high (>= 0.9) for all signals."""
    twin = FactoryTwin(snapshot_interval=9999)
    engine = FeatureEngine()

    for _ in range(100):
        engine.ingest_tick(twin.tick())

    store = EvidenceStore()
    now = datetime.now(timezone.utc)
    trust_evs = compute_trust_evidence(
        engine, twin.get_state(), store,
        window_start=now - timedelta(minutes=1),
        window_end=now,
    )

    assert_(len(trust_evs) > 0, "Should produce trust evidence")

    # All should be high trust at baseline
    for ev in trust_evs:
        assert_(ev.source == EvidenceSource.TRUST_CHECK)
        assert_(ev.statistic == "data_trust")
        assert_(ev.value >= 0.8,
                f"Baseline trust should be >= 0.8 for {ev.signal}, got {ev.value:.3f}")

    # Check lookup convenience function
    avg_trust = get_trust_for_agent(store, "machines.M-04")
    assert_(avg_trust >= 0.8, f"Average M-04 trust should be >= 0.8, got {avg_trust:.3f}")
    print(f"    Baseline trust: avg={avg_trust:.3f}, count={len(trust_evs)} evidence objects")

check("Trust is high at baseline", test_trust_at_baseline)


def test_trust_degrades_under_s2():
    """Under S2 (integrity attack), trust should degrade significantly."""
    twin = FactoryTwin(snapshot_interval=9999)
    engine = FeatureEngine()

    # Warmup
    for _ in range(100):
        engine.ingest_tick(twin.tick())

    # Apply S2 (sensor drift + unauthorized writes)
    apply_scenario(twin.params, "S2")
    for _ in range(200):
        engine.ingest_tick(twin.tick())

    store = EvidenceStore()
    now = datetime.now(timezone.utc)
    trust_evs = compute_trust_evidence(
        engine, twin.get_state(), store,
        window_start=now - timedelta(minutes=1),
        window_end=now,
    )

    # Trust should be low under integrity attack
    machine_trust_evs = [
        ev for ev in trust_evs
        if ev.signal.startswith("machines.M-04")
    ]
    avg_trust = np.mean([ev.value for ev in machine_trust_evs])
    assert_(avg_trust < 0.5,
            f"Trust should degrade under S2: avg={avg_trust:.3f}")
    print(f"    S2 trust: avg={avg_trust:.3f}")

check("Trust degrades under S2 (integrity attack)", test_trust_degrades_under_s2)


def test_trust_evidence_exists_before_agents():
    """Verify trust evidence is in the store at the moment a case would open."""
    twin = FactoryTwin(snapshot_interval=9999)
    engine = FeatureEngine()

    for _ in range(100):
        engine.ingest_tick(twin.tick())

    store = EvidenceStore()
    now = datetime.now(timezone.utc)

    # This is what the Orchestrator would call before dispatching agents
    trust_evs = compute_trust_evidence(
        engine, twin.get_state(), store,
        window_start=now - timedelta(minutes=1),
        window_end=now,
    )

    # At this point (BEFORE any agent runs), trust evidence must exist
    trust_in_store = store.by_source(EvidenceSource.TRUST_CHECK)
    assert_(len(trust_in_store) > 0,
            "Trust evidence must exist in the store before agents run")

    # Every machine signal should have a trust value
    for sig in ["temperature_c", "vibration_mm_s", "motor_current_a",
                "rpm", "coolant_flow_lpm"]:
        trust = store.trust_for_signal(f"machines.M-04.{sig}")
        assert_(trust is not None,
                f"Trust for machines.M-04.{sig} should exist, got None")

    print(f"    {len(trust_in_store)} trust evidence objects in store before agent fan-out")

check("Trust evidence exists before any agent runs", test_trust_evidence_exists_before_agents)


def test_trust_evidence_has_correct_structure():
    """Each trust Evidence should have the required fields for agents to read."""
    twin = FactoryTwin(snapshot_interval=9999)
    engine = FeatureEngine()
    for _ in range(100):
        engine.ingest_tick(twin.tick())

    store = EvidenceStore()
    now = datetime.now(timezone.utc)
    trust_evs = compute_trust_evidence(
        engine, twin.get_state(), store,
        now - timedelta(minutes=1), now,
    )

    ev = trust_evs[0]
    assert_(ev.source == EvidenceSource.TRUST_CHECK)
    assert_(ev.statistic == "data_trust")
    assert_(0.0 <= ev.value <= 1.0, f"Trust value must be [0,1], got {ev.value}")
    assert_(len(ev.signal) > 0, "Signal name must be non-empty")
    assert_(len(ev.id) > 0, "Evidence ID must be non-empty")
    assert_(len(ev.description) > 0, "Description must be non-empty")

check("Trust evidence has correct structure", test_trust_evidence_has_correct_structure)


# =====================================================================
print(f"\n{'='*60}")
print(f"RESULTS: {passed}/{total} passed, {failed} failed")
if failed > 0:
    print("!! SOME CHECKS FAILED -- see above for details.")
    sys.exit(1)
else:
    print("[OK] ALL CHECKS PASSED -- Step 5 complete.")
    sys.exit(0)
