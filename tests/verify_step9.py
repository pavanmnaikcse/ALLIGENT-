"""verify_step9.py -- Verification for Step 9 (Counterfactual Replay)."""

import sys
from datetime import datetime, timezone

from simulator.factory_sim import FactoryTwin
from simulator.scenarios import apply_scenario
from backend.ingestion.feature_engine import FeatureEngine
from schemas.evidence import EvidenceStore
from schemas.case_state import CaseState, CaseStatus
from backend.agents.orchestrator import (
    register_llm_agents,
    run_investigation,
    OrchestratorContext,
)

def make_anomalous_twin() -> tuple[FactoryTwin, FeatureEngine, EvidenceStore]:
    """Create a twin, apply S1 (RPM too high), and run it so it gets hot."""
    twin = FactoryTwin(snapshot_interval=9999)
    engine = FeatureEngine()
    
    # Run 50 ticks normal
    for _ in range(50):
        engine.ingest_tick(twin.tick())
        
    # Apply S1
    apply_scenario(twin.params, "S1")
    
    # Run 50 ticks anomalous -> temp goes up
    for _ in range(50):
        engine.ingest_tick(twin.tick())
        
    store = EvidenceStore()
    return twin, engine, store

def test_counterfactual_replay():
    register_llm_agents()
    
    twin, engine, store = make_anomalous_twin()
    
    ctx = OrchestratorContext(
        evidence_store=store,
        feature_engine=engine,
        twin_state=twin.get_state(),
        twin=twin,
    )
    
    now = datetime.now(timezone.utc)
    case = CaseState(
        case_id="TEST-CASE-9",
        machine_id="M-04",
        line_id="L1",
        status=CaseStatus.OPEN,
        evidence_window_start=now,
        evidence_window_end=now,
    )
    
    # Run investigation
    case = run_investigation(case, ctx)
    
    # Verifier should have run replay
    verifier_finding = case.findings.get("verifier")
    assert verifier_finding is not None, "Verifier finding missing"
    
    metadata = verifier_finding.metadata
    assert "replay_results" in metadata, "replay_results missing from verifier metadata"
    replays = metadata["replay_results"]
    assert len(replays) > 0, "No replay results found"
    
    replay = replays[0]
    assert replay["hypothesis_id"] == "H1", f"Expected H1 replay, got {replay['hypothesis_id']}"
    assert replay["anomaly_resolved"] is True, "Anomaly should have resolved when reverting H1"
    assert replay["parameter_reverted"] == "machines.M-04.target_rpm"
    assert replay["reverted_value"] == 1000.0, "Should have reverted to safe value 1000.0"
    assert replay["original_value"] == 1500.0, "Original anomalous value should be 1500.0"

def main():
    print("\n=== STEP 9 VERIFICATION: Counterfactual Replay ===")
    
    try:
        test_counterfactual_replay()
        print("  [PASS] Counterfactual replay resolves S1 anomaly")
        print("\n============================================================")
        print("RESULTS: 1/1 passed, 0 failed")
        print("[OK] ALL CHECKS PASSED -- Step 9 complete.")
        sys.exit(0)
    except Exception as e:
        print(f"  [FAIL] Counterfactual replay: {type(e).__name__} - {e}")
        print("\n============================================================")
        print("RESULTS: 0/1 passed, 1 failed")
        print("!! SOME CHECKS FAILED -- see above for details.")
        sys.exit(1)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
