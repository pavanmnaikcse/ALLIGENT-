"""Step 1 Verification Script -- schemas + hypothesis library.

Tests:
1. Every Pydantic schema can be constructed with valid dummy data.
2. AgentFinding with empty evidence_ids is REJECTED (R3).
3. All eight hypotheses (H1-H8) are present in the library.
4. S1-S5 + NOISE_ONLY scenario mappings are present and unambiguous.
5. Every scenario maps to at least one hypothesis, and every hypothesis
   in the mapping is a valid HypothesisID.
"""

import sys
import os
import traceback
from datetime import datetime, timedelta, timezone

# Force UTF-8 output on Windows
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure the project root is on the path
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from schemas.telemetry import (
    EnergyTelemetry,
    MachineTelemetry,
    MaterialTelemetry,
    NetworkTelemetry,
    ProcessTelemetry,
    QualityTelemetry,
    SetpointChangeRecord,
    TelemetryTick,
)
from schemas.evidence import Evidence, EvidenceSource, EvidenceStore
from schemas.agent_output import (
    AgentFinding,
    CorrelationResult,
    CounterfactualReplayResult,
    HypothesisScore,
    RecommendedAction,
    RecommendationResult,
    RootCauseResult,
    TimelineEntry,
    TimedEvent,
    VerifierResult,
)
from schemas.case_state import (
    AgentStatus,
    CaseState,
    CaseStatus,
    EscalationLevel,
    HumanDecision,
)
from schemas.hypotheses import (
    HYPOTHESIS_LIBRARY,
    HypothesisID,
    SCENARIO_HYPOTHESIS_MAP,
    get_all_hypotheses,
    get_hypothesis,
    get_scenario_ground_truth,
)


# ===== Utilities (defined BEFORE any test calls) =====

passed = 0
failed = 0
total = 0

NOW = datetime.now(timezone.utc)
WINDOW_START = NOW - timedelta(minutes=5)
WINDOW_END = NOW


def assert_(condition, msg="Assertion failed"):
    if not condition:
        raise AssertionError(msg)


def _expect_fail(fn):
    """Assert that calling fn() raises an exception."""
    try:
        fn()
    except Exception:
        return  # Expected
    raise AssertionError("Expected an exception but none was raised.")


def check(name: str, fn):
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


def make_evidence(signal="machines.M-04.temperature_c", source=EvidenceSource.ANOMALY_DETECTOR):
    return Evidence(
        source=source,
        signal=signal,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
        statistic="isolation_forest_score",
        value=0.92,
        description="Temperature anomaly detected.",
    )


def _test_evidence_store():
    store = EvidenceStore()
    ev = make_evidence()
    eid = store.add(ev)
    assert store.get(eid) is not None
    assert store.get(eid).signal == "machines.M-04.temperature_c"
    assert len(store.by_source(EvidenceSource.ANOMALY_DETECTOR)) == 1
    assert len(store.by_signal("machines.M-04.temperature_c")) == 1
    assert len(store.by_signal_prefix("machines.M-04")) == 1


def _test_trust_lookup():
    store = EvidenceStore()
    trust_ev = Evidence(
        source=EvidenceSource.TRUST_CHECK,
        signal="machines.M-04.temperature_c",
        window_start=WINDOW_START, window_end=WINDOW_END,
        statistic="data_trust", value=0.95,
        description="High trust.",
    )
    store.add(trust_ev)
    assert store.trust_for_signal("machines.M-04.temperature_c") == 0.95
    assert store.trust_for_signal("machines.M-04.vibration_mm_s") is None


def _test_full_case_state():
    cs = CaseState(
        case_id="CASE-002", machine_id="M-04", line_id="L-03",
        status=CaseStatus.INVESTIGATING, severity="high",
        evidence_window_start=WINDOW_START, evidence_window_end=WINDOW_END,
        superseded_by=None, merged_into=None,
    )
    assert_(cs.status == CaseStatus.INVESTIGATING, "Status mismatch")
    assert_(cs.agent_statuses["machine"] == AgentStatus.PENDING, "Agent status mismatch")
    assert_(cs.escalation_level == EscalationLevel.NONE, "Escalation mismatch")


def _check_mapping_validity():
    for sid, mapping in SCENARIO_HYPOTHESIS_MAP.items():
        for h in mapping.ground_truth_hypotheses:
            assert_(h in HypothesisID, f"{sid} references invalid {h}")
            assert_(h in HYPOTHESIS_LIBRARY, f"{sid} references {h} not in library")


# ===== Run all checks =====

def main():
    print("\n=== STEP 1 VERIFICATION: Schemas + Hypothesis Library ===\n")

    # -- 1. Telemetry --
    print("1. Telemetry schemas")

    check("MachineTelemetry valid", lambda: MachineTelemetry(
        machine_id="M-04", rpm=1200, temperature_c=42.5, vibration_mm_s=2.1,
        motor_current_a=15.3, pressure_bar=4.5, coolant_flow_lpm=12.0,
        bearing_wear=0.15,
    ))

    check("MachineTelemetry rejects negative rpm", lambda: _expect_fail(
        lambda: MachineTelemetry(
            machine_id="M-04", rpm=-10, temperature_c=42.5, vibration_mm_s=2.1,
            motor_current_a=15.3, pressure_bar=4.5, coolant_flow_lpm=12.0,
            bearing_wear=0.15,
        )
    ))

    check("MachineTelemetry rejects bearing_wear > 1", lambda: _expect_fail(
        lambda: MachineTelemetry(
            machine_id="M-04", rpm=1200, temperature_c=42.5, vibration_mm_s=2.1,
            motor_current_a=15.3, pressure_bar=4.5, coolant_flow_lpm=12.0,
            bearing_wear=1.5,
        )
    ))

    check("SetpointChangeRecord valid", lambda: SetpointChangeRecord(
        timestamp=NOW, parameter="machines.M-04.target_rpm",
        old_value=1200, new_value=1450, source="operator",
    ))

    check("ProcessTelemetry valid", lambda: ProcessTelemetry(
        machine_id="M-04", target_rpm=1200, feed_rate=50.0,
    ))

    check("MaterialTelemetry valid", lambda: MaterialTelemetry(
        line_id="L-03", batch_id="BATCH-2024-001", supplier="SupplierA",
        hardness_deviation=0.5, material_sensitivity=1.3,
    ))

    check("QualityTelemetry valid", lambda: QualityTelemetry(
        line_id="L-03", defect_rate=0.03,
        defect_type_mix={"surface": 0.6, "dimensional": 0.4}, reject_count=2,
    ))

    check("EnergyTelemetry valid", lambda: EnergyTelemetry(
        line_id="L-03", kwh_per_unit=1.8, co2_kg_per_unit=0.35,
    ))

    check("NetworkTelemetry valid", lambda: NetworkTelemetry(
        machine_id="M-04", message_rate=120.5, sensor_cross_check_residual=0.02,
    ))

    check("Full TelemetryTick valid", lambda: TelemetryTick(
        tick_index=100, sim_time_s=100.0,
        machines=[MachineTelemetry(
            machine_id="M-04", rpm=1200, temperature_c=42.5, vibration_mm_s=2.1,
            motor_current_a=15.3, pressure_bar=4.5, coolant_flow_lpm=12.0,
            bearing_wear=0.15,
        )],
        processes=[ProcessTelemetry(machine_id="M-04", target_rpm=1200, feed_rate=50.0)],
        materials=[MaterialTelemetry(line_id="L-03", batch_id="BATCH-001")],
        quality=[QualityTelemetry(line_id="L-03", defect_rate=0.02)],
        energy=[EnergyTelemetry(line_id="L-03", kwh_per_unit=1.8, co2_kg_per_unit=0.35)],
        network=[NetworkTelemetry(machine_id="M-04", message_rate=120.5)],
    ))

    check("TelemetryTick rejects empty machines list", lambda: _expect_fail(
        lambda: TelemetryTick(
            tick_index=0, sim_time_s=0.0, machines=[], processes=[],
            materials=[], quality=[], energy=[], network=[],
        )
    ))

    # -- 2. Evidence --
    print("\n2. Evidence schemas")

    check("Evidence valid", lambda: make_evidence())
    check("EvidenceStore add/get/by_source", _test_evidence_store)
    check("EvidenceStore trust_for_signal", _test_trust_lookup)

    # -- 3. Agent output --
    print("\n3. Agent output schemas")

    check("AgentFinding valid", lambda: AgentFinding(
        agent_name="machine",
        summary="Temperature anomaly detected on M-04.",
        evidence_ids=["ev-abc123"],
        detected_events=[TimedEvent(
            variable="temperature_c", onset_time=NOW, magnitude=8.5,
        )],
        data_trust=0.95,
        confidence=0.87,
    ))

    check("AgentFinding REJECTS empty evidence_ids (R3)", lambda: _expect_fail(
        lambda: AgentFinding(
            agent_name="machine",
            summary="This should be rejected.",
            evidence_ids=[],  # R3 violation
            data_trust=0.9, confidence=0.5,
        )
    ))

    check("AgentFinding rejects confidence > 1", lambda: _expect_fail(
        lambda: AgentFinding(
            agent_name="machine",
            summary="Invalid confidence.",
            evidence_ids=["ev-x"],
            data_trust=0.9, confidence=1.5,
        )
    ))

    check("CorrelationResult valid", lambda: CorrelationResult(
        timeline=[TimelineEntry(
            time=NOW, event="Temperature spike", source_agent="machine",
            evidence_id="ev-abc123",
        )],
    ))

    check("HypothesisScore valid", lambda: HypothesisScore(
        hypothesis_id="H1", hypothesis_name="Speed above safe envelope",
        raw_score=4.2, normalized_score=0.45,
        temporal_precedence=0.9, evidence_coverage=0.8,
    ))

    check("RootCauseResult valid", lambda: RootCauseResult(
        ranked_hypotheses=[HypothesisScore(
            hypothesis_id="H1", hypothesis_name="Speed above safe envelope",
            raw_score=4.2, normalized_score=0.45,
        )],
        confidence=0.82,
        scoring_weights={"w1": 0.3, "w2": 0.25, "w3": 0.15, "w4": 0.2, "w5": 0.1},
    ))

    check("VerifierResult valid", lambda: VerifierResult(
        top_hypothesis_id="H1", adjusted_confidence=0.88, verdict="confirmed",
    ))

    check("RecommendationResult valid", lambda: RecommendationResult(
        case_id="CASE-001", verified_cause="H1",
        actions=[RecommendedAction(
            action_id="A1", description="Reduce RPM to 1200",
            parameter_changes={"target_rpm": 1200.0},
            predicted_defect_rate=0.02, predicted_kwh_per_unit=1.5,
            predicted_peak_temperature=45.0, predicted_co2_per_unit=0.28,
        )],
    ))

    # -- 4. Case state --
    print("\n4. Case state schema")

    check("CaseState valid", lambda: CaseState(
        case_id="CASE-001", machine_id="M-04", line_id="L-03",
        evidence_window_start=WINDOW_START, evidence_window_end=WINDOW_END,
    ))

    check("CaseState with all fields", _test_full_case_state)

    check("CaseState superseded_by field", lambda: CaseState(
        case_id="CASE-003", machine_id="M-04", line_id="L-03",
        status=CaseStatus.SUPERSEDED, superseded_by="CASE-004",
        evidence_window_start=WINDOW_START, evidence_window_end=WINDOW_END,
    ))

    check("HumanDecision valid", lambda: HumanDecision(action="approve"))

    # -- 5. Hypothesis library --
    print("\n5. Hypothesis library")

    check("All 8 hypotheses present", lambda: assert_(
        len(HYPOTHESIS_LIBRARY) == 8, f"Expected 8, got {len(HYPOTHESIS_LIBRARY)}"
    ))

    check("H1-H8 IDs match", lambda: assert_(
        set(HYPOTHESIS_LIBRARY.keys()) == set(HypothesisID),
        f"Keys: {set(HYPOTHESIS_LIBRARY.keys())} != {set(HypothesisID)}",
    ))

    check("get_hypothesis(H1) returns correct name", lambda: assert_(
        get_hypothesis(HypothesisID.H1).name == "Speed above safe envelope"
    ))

    check("get_all_hypotheses returns 8", lambda: assert_(
        len(get_all_hypotheses()) == 8
    ))

    check("Every hypothesis has a non-empty description", lambda: [
        assert_(len(h.description) > 10, f"{h.id} description too short")
        for h in get_all_hypotheses()
    ])

    # -- 6. Scenario -> Hypothesis mapping --
    print("\n6. Scenario -> Hypothesis mapping")

    check("S1-S5 + NOISE_ONLY all present", lambda: assert_(
        set(SCENARIO_HYPOTHESIS_MAP.keys()) == {"S1", "S2", "S3", "S4", "S5", "NOISE_ONLY"},
        f"Got: {set(SCENARIO_HYPOTHESIS_MAP.keys())}",
    ))

    check("S1 -> H1", lambda: assert_(
        get_scenario_ground_truth("S1") == [HypothesisID.H1]
    ))
    check("S2 -> H5, H6", lambda: assert_(
        set(get_scenario_ground_truth("S2")) == {HypothesisID.H5, HypothesisID.H6}
    ))
    check("S3 -> H3", lambda: assert_(
        get_scenario_ground_truth("S3") == [HypothesisID.H3]
    ))
    check("S4 -> H2", lambda: assert_(
        get_scenario_ground_truth("S4") == [HypothesisID.H2]
    ))
    check("S5 -> H4", lambda: assert_(
        get_scenario_ground_truth("S5") == [HypothesisID.H4]
    ))
    check("NOISE_ONLY -> H7", lambda: assert_(
        get_scenario_ground_truth("NOISE_ONLY") == [HypothesisID.H7]
    ))

    check("Every mapping references valid HypothesisIDs", _check_mapping_validity)

    check("Unknown scenario raises ValueError", lambda: _expect_fail(
        lambda: get_scenario_ground_truth("S99")
    ))

    # -- Results --
    print(f"\n{'='*60}")
    print(f"RESULTS: {passed}/{total} passed, {failed} failed")
    if failed > 0:
        print("!! SOME CHECKS FAILED -- see above for details.")
        sys.exit(1)
    else:
        print("[OK] ALL CHECKS PASSED -- Step 1 complete.")
        sys.exit(0)


if __name__ == "__main__":
    main()
