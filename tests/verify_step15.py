"""verify_step15.py -- Verification for Step 15 (History Agent)."""

import sys
from datetime import datetime, timezone
from simulator.factory_sim import FactoryTwin
from simulator.scenarios import apply_scenario
from backend.agents.history_agent import history_agent
from schemas.case_state import CaseState, CaseStatus
from backend.agents.orchestrator import OrchestratorContext
from schemas.evidence import EvidenceStore
from scripts.generate_history import generate_dataset

def test_history_agent():
    # Ensure there is a history dataset
    generate_dataset(num_cases=50, output_path="data/history.json")
    
    twin = FactoryTwin()
    for _ in range(30):
        twin.tick()
        
    apply_scenario(twin.params, "S1")
    for _ in range(50):
        twin.tick()
        
    now = datetime.now(timezone.utc)
    case = CaseState(
        case_id="TEST-15",
        machine_id="M-04",
        line_id="L-03",
        status=CaseStatus.OPEN,
        evidence_window_start=now,
        evidence_window_end=now,
    )
    ctx = OrchestratorContext(
        evidence_store=EvidenceStore(),
        feature_engine=None,
        twin_state=twin.get_state(),
        twin=twin,
    )
    
    # Run the history agent
    case = history_agent(case, ctx)
    
    finding = case.findings.get("history_specialist")
    assert finding is not None, "History finding missing"
    
    # S1 should match some historical S1 cases with > 0.85 similarity
    metadata = finding.metadata
    if "similar_cases" in metadata and len(metadata["similar_cases"]) > 0:
        top_case = metadata["similar_cases"][0]
        assert top_case["similarity_score"] > 0.85, f"Expected similarity > 0.85, got {top_case['similarity_score']}"
        print(f"  [INFO] Found match: {top_case['scenario_id']} with sim {top_case['similarity_score']:.3f}")
    else:
        assert False, "Expected to find similar cases > 0.85, but none were found."
        
def main():
    print("\n=== STEP 15 VERIFICATION: History Agent ===")
    passes = 0
    total = 1
    
    try:
        test_history_agent()
        print("  [PASS] History agent successfully found past similar cases (>0.85)")
        passes += 1
    except Exception as e:
        print(f"  [FAIL] History agent: {e}")
        
    print("\n============================================================")
    print(f"RESULTS: {passes}/{total} passed, {total - passes} failed")
    if passes == total:
        print("[OK] ALL CHECKS PASSED -- Step 15 complete.")
        sys.exit(0)
    else:
        print("!! SOME CHECKS FAILED -- see above for details.")
        sys.exit(1)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
