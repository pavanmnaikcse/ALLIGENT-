"""run_demo.py -- Step 19 Offline Demo / Soak Test Mode.

Continuously triggers 5 historical cases in sequence, simulating the full lifecycle
including automatic approval of fixes to keep the loop running without human intervention.
"""

import sys
import time
from datetime import datetime, timezone

from simulator.factory_sim import FactoryTwin
from backend.ingestion.feature_engine import FeatureEngine
from simulator.scenarios import SCENARIOS, apply_scenario
from schemas.case_state import CaseState, CaseStatus
from schemas.evidence import EvidenceStore
from backend.agents.orchestrator import OrchestratorContext, run_investigation, register_llm_agents

def run_soak_test(num_iterations=5):
    print(f"Starting Offline Soak Test ({num_iterations} iterations)...\n")
    register_llm_agents()
    
    twin = FactoryTwin(snapshot_interval=10)
    engine = FeatureEngine()
    
    scenarios = ["S1", "S2", "S3", "S4", "S5"]
    
    for i in range(num_iterations):
        scenario_id = scenarios[i % len(scenarios)]
        print(f"\n[{i+1}/{num_iterations}] --- Injecting Scenario {scenario_id} ---")
        
        # 1. Baseline
        for _ in range(20):
            engine.ingest_tick(twin.tick())
            
        # 2. Anomaly
        print("  -> Applying anomaly...")
        apply_scenario(twin.params, scenario_id)
        
        for _ in range(40):
            engine.ingest_tick(twin.tick())
            
        # 3. Investigation
        print("  -> Starting orchestrator investigation...")
        now = datetime.now(timezone.utc)
        case = CaseState(
            case_id=f"SOAK-{i+1}",
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
        
        # 4. Auto-Approval / Fix Application
        print(f"  -> Investigation concluded with status: {case.status.value}")
        
        # In soak mode, we bypass human review and apply the top recommendation directly
        if "recommendation_specialist" in case.findings:
            rec_finding = case.findings["recommendation_specialist"]
            actions = rec_finding.metadata.get("actions", [])
            if actions:
                top_action = actions[0]
                print(f"  -> Auto-approving recommendation: {top_action['description']}")
                # Apply changes to twin
                changes = top_action.get("parameter_changes", {})
                for k, v in changes.items():
                    twin.params.set(k, v)
                print(f"  -> Applied parameter changes: {changes}")
            else:
                print("  -> No recommended actions found to apply.")
        else:
            print("  -> No recommendations provided by agents.")
            
        # Cool down phase
        print("  -> Running cooldown...")
        for _ in range(20):
            engine.ingest_tick(twin.tick())
            
    print("\nSoak test completed successfully.")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    run_soak_test(5)
