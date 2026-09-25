"""Step 7 Verification Script -- LangGraph orchestrator skeleton.

Tests:
1. Agent registry: register/lookup works.
2. Stub agents receive frozen evidence + trust data.
3. Reducer chain runs in correct order (fan-out THEN verifier THEN recommendation).
4. Confidence gate routes low-confidence to NEEDS_HUMAN_REVIEW.
5. Confidence gate routes low-trust to NEEDS_HUMAN_REVIEW.
6. Full pipeline produces complete findings chain.
7. Trust evidence exists BEFORE fan-out agents run.
8. All agent statuses are DONE after pipeline completes.
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

from simulator.parameters import ParameterStore
from simulator.factory_sim import FactoryTwin
from simulator.scenarios import apply_scenario

from backend.ingestion.feature_engine import FeatureEngine
from backend.ingestion.trust_checks import get_trust_for_agent

from backend.agents.orchestrator import (
    OrchestratorContext,
    register_agent,
    register_stubs,
    get_agent,
    run_investigation,
    prepare_node,
    fan_out_node,
    verifier_node,
    recommendation_node,
    confidence_gate_node,
)

from schemas.case_state import CaseState, CaseStatus, AgentStatus
from schemas.evidence import EvidenceSource, EvidenceStore


passed = 0
failed = 0
total = 0
NOW = datetime.now(timezone.utc)


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


def make_test_case(machine_id="M-04", line_id="L-03"):
    return CaseState(
        case_id="TEST-001",
        machine_id=machine_id,
        line_id=line_id,
        status=CaseStatus.OPEN,
        severity="medium",
        evidence_window_start=NOW - timedelta(minutes=5),
        evidence_window_end=NOW,
    )


def make_test_context(twin_ticks=100):
    """Build a FeatureEngine with data and return a context."""
    twin = FactoryTwin(snapshot_interval=9999)
    engine = FeatureEngine()
    for _ in range(twin_ticks):
        engine.ingest_tick(twin.tick())
    store = EvidenceStore()
    return OrchestratorContext(
        evidence_store=store,
        feature_engine=engine,
        twin_state=twin.get_state(),
    ), twin


# Register stubs before tests
register_stubs()


# =====================================================================
print("\n=== STEP 7 VERIFICATION: LangGraph Orchestrator Skeleton ===\n")

# -- 1. Agent registry --
print("1. Agent registry")


def test_registry():
    fn = get_agent("anomaly_specialist")
    assert_(callable(fn), "Registered agent should be callable")
    fn2 = get_agent("verifier")
    assert_(callable(fn2))

check("Agent registry lookup works", test_registry)


def test_registry_unknown():
    try:
        get_agent("nonexistent_agent")
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass

check("Unknown agent raises ValueError", test_registry_unknown)


# -- 2. Stubs receive frozen evidence + trust --
print("\n2. Stubs receive frozen evidence + trust")


def test_stubs_receive_trust():
    ctx, twin = make_test_context(100)
    case = make_test_case()

    # Run PREPARE to populate trust
    case = prepare_node(case, ctx)

    # Trust evidence should now exist
    trust_evs = ctx.evidence_store.by_source(EvidenceSource.TRUST_CHECK)
    assert_(len(trust_evs) > 0, "Trust evidence should exist after PREPARE")

    # Run one specialist
    anomaly_fn = get_agent("anomaly_specialist")
    case = anomaly_fn(case, ctx.evidence_store)

    # The finding should have data_trust from the evidence store
    assert_(len(case.findings) >= 1)
    finding = list(case.findings.values())[-1]
    assert_(finding.data_trust > 0.0, "Finding should have data_trust from evidence store")
    assert_(finding.agent_name == "anomaly_specialist")

check("Stubs read trust from evidence store", test_stubs_receive_trust)


def test_stubs_evidence_ids_nonempty():
    """R3: every finding must cite at least one evidence ID."""
    ctx, twin = make_test_context(100)
    case = make_test_case()
    case = prepare_node(case, ctx)

    for agent_name in ["anomaly_specialist", "correlation_specialist", "root_cause_specialist"]:
        fn = get_agent(agent_name)
        case = fn(case, ctx.evidence_store)

    for f in case.findings.values():
        assert_(len(f.evidence_ids) > 0,
                f"R3 violated: {f.agent_name} has empty evidence_ids")

check("R3: all findings cite evidence (no empty evidence_ids)", test_stubs_evidence_ids_nonempty)


# -- 3. Reducer chain order --
print("\n3. Reducer chain runs in correct order")


def test_reducer_order():
    """Fan-out runs BEFORE verifier, verifier BEFORE recommendation."""
    ctx, twin = make_test_context(100)
    case = make_test_case()

    # Run full pipeline
    case = run_investigation(case, ctx)

    # Check execution log order
    log = ctx.execution_log
    prepare_idx = next(i for i, m in enumerate(log) if "PREPARE" in m)
    fanout_idx = next(i for i, m in enumerate(log) if "FAN-OUT" in m)
    verifier_idx = next(i for i, m in enumerate(log) if "verifier" in m.lower() and "REDUCE" in m)
    rec_idx = next(i for i, m in enumerate(log) if "recommendation" in m.lower() and "REDUCE" in m)
    gate_idx = next(i for i, m in enumerate(log) if "GATE" in m)

    assert_(prepare_idx < fanout_idx, "PREPARE must come before FAN-OUT")
    assert_(fanout_idx < verifier_idx, "FAN-OUT must come before VERIFIER")
    assert_(verifier_idx < rec_idx, "VERIFIER must come before RECOMMENDATION")
    assert_(rec_idx < gate_idx, "RECOMMENDATION must come before GATE")

check("Execution order: PREPARE -> FAN-OUT -> VERIFIER -> RECOMMENDATION -> GATE",
      test_reducer_order)


def test_verifier_sees_specialist_findings():
    """Verifier should see the specialist findings."""
    ctx, twin = make_test_context(100)
    case = make_test_case()
    case = run_investigation(case, ctx)

    verifier_findings = [f for f in case.findings.values() if f.agent_name == "verifier"]
    assert_(len(verifier_findings) == 1, "Should have exactly 1 verifier finding")
    assert_("specialist findings reviewed" in verifier_findings[0].summary.lower() or
            "reviewed" in verifier_findings[0].summary.lower(),
            "Verifier should reference specialist findings")

check("Verifier sees specialist findings", test_verifier_sees_specialist_findings)


# -- 4. Confidence gate: low confidence -> human review --
print("\n4. Confidence gate")


def test_gate_low_confidence():
    """If max confidence is below threshold, route to NEEDS_HUMAN_REVIEW."""
    ctx, twin = make_test_context(100)
    ctx.confidence_threshold = 0.99  # absurdly high -> everything fails

    case = make_test_case()
    case = run_investigation(case, ctx)

    assert_(case.status == CaseStatus.NEEDS_HUMAN_REVIEW,
            f"Low confidence should route to human review, got {case.status}")

check("Low confidence -> NEEDS_HUMAN_REVIEW", test_gate_low_confidence)


def test_gate_normal_confidence():
    """Normal confidence/trust should route to AWAITING_DECISION."""
    ctx, twin = make_test_context(100)
    ctx.confidence_threshold = 0.3  # normal
    ctx.data_trust_threshold = 0.3

    case = make_test_case()
    case = run_investigation(case, ctx)

    assert_(case.status == CaseStatus.AWAITING_DECISION,
            f"Normal confidence should be AWAITING_DECISION, got {case.status}")

check("Normal confidence -> AWAITING_DECISION", test_gate_normal_confidence)


# -- 5. Low trust -> human review --
print("\n5. Trust gate")


def test_gate_low_trust():
    """If data_trust is low (S2 scenario), route to human review."""
    twin = FactoryTwin(snapshot_interval=9999)
    engine = FeatureEngine()
    for _ in range(100):
        engine.ingest_tick(twin.tick())

    # Apply S2 (integrity attack)
    apply_scenario(twin.params, "S2")
    for _ in range(200):
        engine.ingest_tick(twin.tick())

    store = EvidenceStore()
    ctx = OrchestratorContext(
        evidence_store=store,
        feature_engine=engine,
        twin_state=twin.get_state(),
        confidence_threshold=0.3,
        data_trust_threshold=0.5,
    )

    case = make_test_case()
    case = run_investigation(case, ctx)

    assert_(case.status == CaseStatus.NEEDS_HUMAN_REVIEW,
            f"Low trust (S2) should route to human review, got {case.status}")

check("Low trust (S2) -> NEEDS_HUMAN_REVIEW", test_gate_low_trust)


# -- 6. Full pipeline completeness --
print("\n6. Full pipeline completeness")


def test_full_pipeline():
    """Full pipeline produces findings from all 5 agents."""
    ctx, twin = make_test_context(100)
    ctx.confidence_threshold = 0.3
    ctx.data_trust_threshold = 0.3
    case = make_test_case()
    case = run_investigation(case, ctx)

    agents_in_findings = set(f.agent_name for f in case.findings.values())
    expected = {"anomaly_specialist", "correlation_specialist",
                "root_cause_specialist", "verifier", "recommendation"}
    assert_(agents_in_findings == expected,
            f"Expected findings from {expected}, got {agents_in_findings}")

check("All 5 agents produce findings", test_full_pipeline)


def test_all_statuses_done():
    """All agent statuses should be DONE after pipeline."""
    ctx, twin = make_test_context(100)
    case = make_test_case()
    case = run_investigation(case, ctx)

    for agent_name in ["anomaly_specialist", "correlation_specialist",
                       "root_cause_specialist", "verifier", "recommendation"]:
        status = case.agent_statuses.get(agent_name)
        assert_(status == AgentStatus.COMPLETED,
                f"{agent_name} should be COMPLETED, got {status}")

check("All agent statuses are COMPLETED after pipeline", test_all_statuses_done)


# -- 7. Trust before fan-out --
print("\n7. Trust populated before fan-out")


def test_trust_before_fanout():
    """Trust evidence must exist after PREPARE, before FAN-OUT."""
    ctx, twin = make_test_context(100)
    case = make_test_case()

    # Run only PREPARE
    case = prepare_node(case, ctx)

    trust_evs = ctx.evidence_store.by_source(EvidenceSource.TRUST_CHECK)
    assert_(len(trust_evs) > 0, "Trust evidence should exist after PREPARE")

    # The fan-out hasn't run yet, so no specialist findings
    assert_(len(case.findings) == 0, "No findings yet -- fan-out hasn't run")

check("Trust exists after PREPARE, before any agent", test_trust_before_fanout)


def test_investigation_wall_time():
    """Pipeline should record wall time."""
    ctx, twin = make_test_context(100)
    case = make_test_case()
    case = run_investigation(case, ctx)

    assert_(case.wall_time_seconds is not None, "Should have wall_time_seconds")
    assert_(case.wall_time_seconds >= 0, "Wall time should be non-negative")
    assert_(case.investigation_start is not None)
    assert_(case.investigation_end is not None)

check("Investigation records wall time", test_investigation_wall_time)


# =====================================================================
print(f"\n{'='*60}")
print(f"RESULTS: {passed}/{total} passed, {failed} failed")
if failed > 0:
    print("!! SOME CHECKS FAILED -- see above for details.")
    sys.exit(1)
else:
    print("[OK] ALL CHECKS PASSED -- Step 7 complete.")
    sys.exit(0)
