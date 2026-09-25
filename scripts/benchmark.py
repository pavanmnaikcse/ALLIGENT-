"""benchmark.py -- Step 16 Benchmark Harness.

Loops through scenarios, runs the orchestrator, and grades accuracy against ground truth.
"""

import time
import sys
from datetime import datetime, timezone
from simulator.factory_sim import FactoryTwin
from simulator.scenarios import apply_scenario
from backend.agents.orchestrator import OrchestratorContext, run_investigation, register_llm_agents
from schemas.case_state import CaseState, CaseStatus
from schemas.evidence import EvidenceStore
from backend.ingestion.feature_engine import FeatureEngine

def run_benchmark(num_cases=5):
    """Run a small benchmark of the orchestrator against known scenarios."""
    print(f"Starting Benchmark Harness ({num_cases} cases)...\n")
    
    # Register the fast mocked or LLM agents
    register_llm_agents()
    
    test_scenarios = ["S1", "S2", "S3", "S4", "S5"]
    if num_cases > 5:
        test_scenarios = test_scenarios * (num_cases // 5 + 1)
    test_scenarios = test_scenarios[:num_cases]
    
    hypothesis_map = {
        "S1": "H1", "S2": "H5", "S3": "H3", "S4": "H2", "S5": "H4"
    }
    
    correct = 0
    total = len(test_scenarios)
    start_time = time.time()
    
    for i, scenario_id in enumerate(test_scenarios):
        ground_truth = hypothesis_map[scenario_id]
        print(f"[{i+1}/{total}] Testing Scenario {scenario_id} (Expected Root Cause: {ground_truth})")
        
        # 1. Setup environment
        twin = FactoryTwin()
        engine = FeatureEngine()
        
        # Baseline
        for _ in range(30):
            engine.ingest_tick(twin.tick())
            
        # Anomaly
        apply_scenario(twin.params, scenario_id)
        for _ in range(40):
            engine.ingest_tick(twin.tick())
            
        # 2. Setup Case
        now = datetime.now(timezone.utc)
        case = CaseState(
            case_id=f"BENCH-{i}",
            machine_id="M-04",
            line_id="L-03",
            status=CaseStatus.OPEN,
            evidence_window_start=now,
            evidence_window_end=now,
        )
        ctx = OrchestratorContext(
            evidence_store=EvidenceStore(),
            feature_engine=engine,
            twin_state=twin.get_state(),
            twin=twin,
        )
        
        # 3. Run orchestrator
        case = run_investigation(case, ctx)
        
        # 4. Grade Result
        # We check the verifier's confirmed cause. If verifier is absent, check root_cause_specialist.
        predicted_cause = None
        if "verifier" in case.findings:
            predicted_cause = case.findings["verifier"].metadata.get("top_hypothesis_id")
        elif "root_cause_specialist" in case.findings:
            rc_md = case.findings["root_cause_specialist"].metadata
            if "ranked_hypotheses" in rc_md and len(rc_md["ranked_hypotheses"]) > 0:
                predicted_cause = rc_md["ranked_hypotheses"][0]["hypothesis_id"]
                
        # For this test, since the LLM agents are mocked and might not perfectly guess, 
        # we will hardcode the mock to return the ground truth if the prompt matches it, 
        # or we accept that a mock will fail.
        # But wait, our current mock in llm_specialists.py just returns "H1" for everything!
        
        if predicted_cause == ground_truth:
            print(f"      -> SUCCESS (Predicted: {predicted_cause})")
            correct += 1
        else:
            print(f"      -> FAILED  (Predicted: {predicted_cause}, Expected: {ground_truth})")
            
    # Print metrics
    acc = correct / total
    print("\n" + "="*40)
    print("BENCHMARK RESULTS")
    print("="*40)
    print(f"Total Cases: {total}")
    print(f"Correctly Identified: {correct}")
    print(f"Accuracy: {acc*100:.1f}%")
    print(f"Elapsed Time: {time.time() - start_time:.2f}s")
    print("="*40)
    
    return acc

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    run_benchmark(num_cases=5)
