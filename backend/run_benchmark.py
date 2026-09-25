"""run_benchmark.py -- CLI entrypoint for the Benchmark Harness (Step 17)."""

import argparse
import sys
from scripts.benchmark import run_benchmark, FactoryTwin, FeatureEngine, CaseState, CaseStatus, EvidenceStore, OrchestratorContext, run_investigation, apply_scenario, datetime, timezone

def main():
    parser = argparse.ArgumentParser(description="Run the FactoryBrain Benchmark Harness.")
    parser.add_argument("--scenarios", nargs="+", default=["S1", "S2", "S3", "S4", "S5"], help="List of scenarios to benchmark")
    args = parser.parse_args()
    
    print(f"Starting CLI Benchmark Harness for scenarios: {args.scenarios}\n")
    
    hypothesis_map = {
        "S1": "H1", "S2": "H5", "S3": "H3", "S4": "H2", "S5": "H4"
    }
    
    correct = 0
    total = len(args.scenarios)
    import time
    start_time = time.time()
    
    from backend.agents.orchestrator import register_llm_agents
    register_llm_agents()
    
    for i, scenario_id in enumerate(args.scenarios):
        ground_truth = hypothesis_map.get(scenario_id, "UNKNOWN")
        print(f"[{i+1}/{total}] Testing Scenario {scenario_id} (Expected Root Cause: {ground_truth})")
        
        # 1. Setup environment
        twin = FactoryTwin()
        engine = FeatureEngine()
        
        for _ in range(30):
            engine.ingest_tick(twin.tick())
            
        apply_scenario(twin.params, scenario_id)
        for _ in range(40):
            engine.ingest_tick(twin.tick())
            
        now = datetime.now(timezone.utc)
        case = CaseState(
            case_id=f"BENCH-CLI-{i}",
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
        
        case = run_investigation(case, ctx)
        
        predicted_cause = None
        if "verifier" in case.findings:
            predicted_cause = case.findings["verifier"].metadata.get("top_hypothesis_id")
        
        if predicted_cause == ground_truth:
            print(f"      -> SUCCESS (Predicted: {predicted_cause})")
            correct += 1
        else:
            print(f"      -> FAILED  (Predicted: {predicted_cause}, Expected: {ground_truth})")
            
    acc = correct / total if total > 0 else 0
    print("\n" + "="*40)
    print("BENCHMARK RESULTS")
    print("="*40)
    print(f"Total Cases: {total}")
    print(f"Correctly Identified: {correct}")
    print(f"Accuracy: {acc*100:.1f}%")
    print(f"Elapsed Time: {time.time() - start_time:.2f}s")
    print("="*40)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
