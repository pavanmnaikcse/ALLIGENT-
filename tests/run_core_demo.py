"""run_core_demo.py -- End-to-end integration test of the FactoryBrain Core."""

import json
from datetime import datetime, timezone
from simulator.factory_sim import FactoryTwin
from simulator.scenarios import apply_scenario
from backend.ingestion.feature_engine import FeatureEngine
from schemas.evidence import EvidenceStore
from schemas.case_state import CaseState, CaseStatus
from backend.agents.orchestrator import OrchestratorContext, run_investigation, register_llm_agents

def run_demo():
    print("1. Initializing Digital Twin & Feature Engine...")
    twin = FactoryTwin(snapshot_interval=10)
    engine = FeatureEngine()
    
    print("2. Simulating 30 seconds of normal baseline operations...")
    for _ in range(30):
        engine.ingest_tick(twin.tick())
        
    print("3. Injecting Anomaly (Scenario S1: RPM exceeds safe limits)...")
    apply_scenario(twin.params, "S1")
    
    print("4. Simulating 40 seconds of anomalous operations (heat & vibration rising)...")
    for _ in range(40):
        engine.ingest_tick(twin.tick())
        
    store = EvidenceStore()
    now = datetime.now(timezone.utc)
    
    # Normally the Anomaly Detector / Rules engine triggers this
    case = CaseState(
        case_id="INC-DEMO-001",
        machine_id="M-04",
        line_id="L1",
        status=CaseStatus.OPEN,
        evidence_window_start=now,
        evidence_window_end=now,
    )
    
    ctx = OrchestratorContext(
        evidence_store=store,
        feature_engine=engine,
        twin_state=twin.get_state(),
        twin=twin,
    )
    
    # Ensure LLM agents are registered
    register_llm_agents()
    
    print(f"\n5. Kicking off Orchestrator for Case {case.case_id}...")
    case = run_investigation(case, ctx)
    
    print("\n" + "="*60)
    print("INVESTIGATION COMPLETE")
    print("="*60)
    print(f"Final Case Status: {case.status.value.upper()}")
    print("\nEXECUTION LOG:")
    for log_msg in ctx.execution_log:
        print(f"  {log_msg}")
        
    print("\nFINDINGS SUMMARY:")
    for agent_name, finding in case.findings.items():
        print(f"\n[{agent_name.upper()}] (Confidence: {finding.confidence:.2f}, Trust: {finding.data_trust:.2f})")
        print(f"Summary: {finding.summary}")
        if agent_name == "verifier":
            print(f"Verdict: {finding.metadata.get('verdict', 'N/A')}")
            for replay in finding.metadata.get("replay_results", []):
                print(f"  Replay: Reverted {replay['parameter_reverted']} -> Anomaly Resolved: {replay['anomaly_resolved']}")
                
    print("="*60)

if __name__ == "__main__":
    run_demo()
