"""verify_step10.py -- Verification for Step 10 (What-If & Case Resolution Lifecycle)."""

import sys
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.main import app, param_store, case_manager
from schemas.case_state import CaseState, CaseStatus, AgentStatus, AgentFinding, HumanDecision
from backend.agents.whatif_simulator import run_whatif_prediction
from simulator.factory_sim import FactoryTwin

client = TestClient(app)

def test_whatif_engine():
    """Verify the What-If engine runs a forward simulation and measures metrics."""
    twin = FactoryTwin(snapshot_interval=9999)
    # Ensure stable base metrics
    for _ in range(10):
        twin.tick()
        
    metrics = run_whatif_prediction(
        twin=twin,
        machine_id="M-04",
        parameter_changes={"machines.M-04.target_rpm": 1200.0},
        sim_ticks=20
    )
    
    assert "predicted_peak_temperature" in metrics
    assert "predicted_peak_vibration" in metrics
    assert metrics["predicted_peak_vibration"] > 0, "Simulation should produce some vibration"

def test_case_approval_lifecycle():
    """Verify that approving a case applies parameters to the live store."""
    now = datetime.now(timezone.utc)
    # 1. Create a dummy case in case_manager that is AWAITING_DECISION
    case = CaseState(
        case_id="TEST-10",
        machine_id="M-04",
        line_id="L1",
        status=CaseStatus.AWAITING_DECISION,
        evidence_window_start=now,
        evidence_window_end=now,
    )
    case_manager._cases["TEST-10"] = case
    
    # 2. Check current param store state
    param_store.set("machines.M-04.target_rpm", 1500.0)
    
    # 3. Hit the decision endpoint to approve with a payload
    resp = client.post(
        "/cases/TEST-10/decision",
        json={
            "action": "approve",
            "payload": {"machines.M-04.target_rpm": 1000.0},
            "operator_id": "Op-1",
            "notes": "Looks good"
        }
    )
    assert resp.status_code == 200, resp.text
    
    # 4. Verify case status changed
    updated_case = resp.json()
    assert updated_case["status"] == "approved"
    assert updated_case["decision"]["action"] == "approve"
    assert updated_case["decision"]["operator_id"] == "Op-1"
    
    # 5. Verify live parameter was changed
    assert param_store.get("machines.M-04.target_rpm") == 1000.0, "Parameter should have been updated by approval"

def main():
    print("\n=== STEP 10 VERIFICATION: What-If & Case Lifecycle ===")
    
    passes = 0
    total = 2
    
    try:
        test_whatif_engine()
        print("  [PASS] What-If simulator grounds metrics in physics")
        passes += 1
    except Exception as e:
        print(f"  [FAIL] What-If simulator: {e}")
        
    try:
        test_case_approval_lifecycle()
        print("  [PASS] Case approval endpoint mutates live parameter store")
        passes += 1
    except Exception as e:
        print(f"  [FAIL] Case approval endpoint: {e}")
        
    print("\n============================================================")
    print(f"RESULTS: {passes}/{total} passed, {total - passes} failed")
    if passes == total:
        print("[OK] ALL CHECKS PASSED -- Step 10 complete.")
        sys.exit(0)
    else:
        print("!! SOME CHECKS FAILED -- see above for details.")
        sys.exit(1)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
