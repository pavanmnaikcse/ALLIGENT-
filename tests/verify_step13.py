"""verify_step13.py -- Verification for Step 13 (Communication & Escalation)."""

import sys
import os
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.main import app
from schemas.case_state import CaseState, CaseStatus, AgentFinding
from backend.agents.orchestrator import OrchestratorContext
from backend.agents.communication import run_escalation_ladder

client = TestClient(app)

def test_escalation_ladder():
    """Verify that the escalation ladder runs without crashing."""
    now = datetime.now(timezone.utc)
    case = CaseState(
        case_id="TEST-13",
        machine_id="M-04",
        line_id="L1",
        status=CaseStatus.NEEDS_HUMAN_REVIEW,
        evidence_window_start=now,
        evidence_window_end=now,
    )
    
    # Add dummy finding
    case.findings["anomaly_specialist"] = AgentFinding(
        agent_name="anomaly_specialist",
        summary="Test finding",
        evidence_ids=["E1"],
        data_trust=0.9,
        confidence=0.9
    )
    
    # It should skip gracefully if env vars are missing
    ctx = OrchestratorContext(
        evidence_store=None,
        feature_engine=None,
        twin_state={},
    )
    
    # Run
    run_escalation_ladder(case, ctx)
    
    assert len(ctx.execution_log) > 0
    assert "ESCALATION: Ladder triggered" in ctx.execution_log[-1]

def test_twilio_webhook_no_signature():
    """Verify that missing/invalid twilio signature returns 403 when configured."""
    os.environ["TWILIO_AUTH_TOKEN"] = "fake-token"
    resp = client.post(
        "/voice/webhook",
        data={"Digits": "1"},
        headers={"X-Twilio-Signature": "fake-signature"}
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    os.environ.pop("TWILIO_AUTH_TOKEN")
    
def test_twilio_webhook_no_auth():
    """Verify that if no token is configured, it passes (for demo environments)."""
    if "TWILIO_AUTH_TOKEN" in os.environ:
        os.environ.pop("TWILIO_AUTH_TOKEN")
        
    resp = client.post(
        "/voice/webhook",
        data={"Digits": "1"}
    )
    assert resp.status_code == 200
    assert "Acknowledgment received" in resp.text

def main():
    print("\n=== STEP 13 VERIFICATION: Escalation Ladder ===")
    
    passes = 0
    total = 3
    
    try:
        test_escalation_ladder()
        print("  [PASS] Escalation ladder runs (PDF/Email/Voice)")
        passes += 1
    except Exception as e:
        print(f"  [FAIL] Escalation ladder: {e}")
        
    try:
        test_twilio_webhook_no_signature()
        print("  [PASS] Webhook rejects invalid signature")
        passes += 1
    except Exception as e:
        print(f"  [FAIL] Webhook invalid signature: {e}")
        
    try:
        test_twilio_webhook_no_auth()
        print("  [PASS] Webhook processes acknowledgment")
        passes += 1
    except Exception as e:
        print(f"  [FAIL] Webhook acknowledgment: {e}")
        
    print("\n============================================================")
    print(f"RESULTS: {passes}/{total} passed, {total - passes} failed")
    if passes == total:
        print("[OK] ALL CHECKS PASSED -- Step 13 complete.")
        sys.exit(0)
    else:
        print("!! SOME CHECKS FAILED -- see above for details.")
        sys.exit(1)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
