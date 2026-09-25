"""verify_step8.py -- Verification for Step 8 (Real LLM Specialist Agents)."""

import sys
from datetime import datetime, timezone
from typing import Any

from schemas.evidence import EvidenceStore, Evidence, EvidenceSource
from backend.agents.orchestrator import (
    register_llm_agents,
    run_investigation,
    OrchestratorContext,
)
from schemas.case_state import CaseState, CaseStatus, AgentStatus
from backend.ingestion.feature_engine import FeatureEngine
from simulator.factory_sim import FactoryTwin

def make_test_context(twin_ticks=10):
    twin = FactoryTwin(snapshot_interval=9999)
    engine = FeatureEngine()
    for _ in range(twin_ticks):
        engine.ingest_tick(twin.tick())
    store = EvidenceStore()
    return OrchestratorContext(
        evidence_store=store,
        feature_engine=engine,
        twin_state=twin.get_state(),
    )

def check(name: str, fn: Any) -> bool:
    try:
        fn()
        print(f"  [PASS] {name}")
        return True
    except AssertionError as e:
        print(f"  [FAIL] {name}: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] {name}: {type(e).__name__} - {e}")
        return False

def make_test_case() -> CaseState:
    now = datetime.now(timezone.utc)
    return CaseState(
        case_id="TEST-CASE-8",
        machine_id="M-04",
        line_id="L1",
        status=CaseStatus.OPEN,
        evidence_window_start=now,
        evidence_window_end=now,
    )

def test_llm_agents_complete():
    """Verify LLM agents run and complete successfully."""
    register_llm_agents()
    
    ctx = make_test_context()
    now = datetime.now(timezone.utc)
    ctx.evidence_store.add(Evidence(
        source=EvidenceSource.TRUST_CHECK,
        signal="machines.M-04",
        window_start=now,
        window_end=now,
        statistic="overall_trust",
        value=0.98,
        description="Trust check pass",
    ))
    case = make_test_case()
    case = run_investigation(case, ctx)
    
    # All 5 agents should have findings
    assert len(case.findings) == 5, f"Expected 5 findings, got {len(case.findings)}"
    for name in ["anomaly_specialist", "correlation_specialist", "root_cause_specialist", "verifier", "recommendation"]:
        assert name in case.findings, f"Missing finding for {name}"
        assert case.agent_statuses.get(name) == AgentStatus.COMPLETED, f"Agent {name} not completed"

def test_llm_findings_contain_metadata():
    """Verify that findings contain structured metadata (R3 + Detailed schemas)."""
    register_llm_agents()
    ctx = make_test_context()
    now = datetime.now(timezone.utc)
    ctx.evidence_store.add(Evidence(
        source=EvidenceSource.TRUST_CHECK,
        signal="machines.M-04",
        window_start=now,
        window_end=now,
        statistic="overall_trust",
        value=0.95,
        description="Trust check pass",
    ))
    case = make_test_case()
    case = run_investigation(case, ctx)
    
    rc = case.findings["root_cause_specialist"]
    assert "ranked_hypotheses" in rc.metadata, "Root cause finding missing 'ranked_hypotheses' in metadata"
    assert len(rc.metadata["ranked_hypotheses"]) > 0
    
    corr = case.findings["correlation_specialist"]
    assert "timeline" in corr.metadata, "Correlation finding missing 'timeline' in metadata"
    
    rec = case.findings["recommendation"]
    assert "actions" in rec.metadata, "Recommendation finding missing 'actions' in metadata"

def main():
    print("\n=== STEP 8 VERIFICATION: LLM Specialist Agents ===")
    
    print("\n1. Pipeline execution with LLM agents")
    passes = []
    passes.append(check("LLM agents run and complete successfully", test_llm_agents_complete))
    passes.append(check("Findings contain structured metadata", test_llm_findings_contain_metadata))
    
    total = len(passes)
    passed = sum(passes)
    
    print(f"\n============================================================")
    print(f"RESULTS: {passed}/{total} passed, {total - passed} failed")
    if passed == total:
        print("[OK] ALL CHECKS PASSED -- Step 8 complete.")
        sys.exit(0)
    else:
        print("!! SOME CHECKS FAILED -- see above for details.")
        sys.exit(1)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
