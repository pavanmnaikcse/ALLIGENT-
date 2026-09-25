"""communication.py -- Step 13 Communication Agent & Escalation Ladder.

Implements the escalation ladder: PDF generation, Email sending, and Voice calls.
"""

import os
import smtplib
from email.message import EmailMessage
import json
from datetime import datetime, timezone

from schemas.case_state import CaseState
from backend.agents.orchestrator import OrchestratorContext

def generate_pdf_report(case: CaseState) -> bytes:
    """Generate a mock PDF report (raw bytes) summarizing the case.
    In a real app, this would use reportlab or similar.
    """
    report = f"FactoryBrain Investigation Report\n"
    report += f"Case ID: {case.case_id}\n"
    report += f"Status: {case.status.value}\n"
    report += f"Machine ID: {case.machine_id}\n\n"
    report += f"Findings:\n"
    for agent, finding in case.findings.items():
        report += f"- {agent}: {finding.summary} (Conf: {finding.confidence})\n"
        
    # Return as bytes representing a PDF (we just use text for simplicity in this demo)
    return report.encode('utf-8')


def send_email(case: CaseState, pdf_bytes: bytes, recipient: str = "oncall@example.com"):
    """Send an email with the PDF report attached."""
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    
    if not all([smtp_server, smtp_port, smtp_user, smtp_pass]):
        print(f"  [Escalation] Skipping email to {recipient} (SMTP credentials missing)")
        return
        
    msg = EmailMessage()
    msg['Subject'] = f"FactoryBrain Alert: {case.case_id} requires review"
    msg['From'] = smtp_user
    msg['To'] = recipient
    msg.set_content(f"Case {case.case_id} requires human review. See attached report.")
    
    # Attach "PDF"
    msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=f"{case.case_id}_report.pdf")
    
    try:
        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print(f"  [Escalation] Email sent to {recipient}")
    except Exception as e:
        print(f"  [Escalation] Failed to send email: {e}")


def trigger_voice_call(case: CaseState, phone_number: str = "+1234567890"):
    """Trigger a Twilio voice call to the on-call engineer."""
    twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_from_number = os.getenv("TWILIO_FROM_NUMBER")
    base_url = os.getenv("PUBLIC_URL", "https://example.ngrok.io")
    
    if not all([twilio_account_sid, twilio_auth_token, twilio_from_number]):
        print(f"  [Escalation] Skipping voice call to {phone_number} (Twilio credentials missing)")
        return
        
    try:
        from twilio.rest import Client
        client = Client(twilio_account_sid, twilio_auth_token)
        
        call = client.calls.create(
            twiml=f'<Response><Say>Factory Brain alert for case {case.case_id}. Please review immediately. Press 1 to acknowledge.</Say><Gather action="{base_url}/voice/webhook" numDigits="1"/></Response>',
            to=phone_number,
            from_=twilio_from_number
        )
        print(f"  [Escalation] Voice call initiated: {call.sid}")
    except Exception as e:
        print(f"  [Escalation] Failed to initiate voice call: {e}")


def run_escalation_ladder(case: CaseState, ctx: OrchestratorContext):
    """Execute the escalation ladder for a case requiring human review."""
    ctx.log("ESCALATION: Running escalation ladder")
    
    # 1. Generate report
    pdf_bytes = generate_pdf_report(case)
    
    # 2. Email
    send_email(case, pdf_bytes)
    
    # 3. Voice Call
    trigger_voice_call(case)
    
    # Audit log
    ctx.execution_log.append(f"ESCALATION: Ladder triggered at {datetime.now(timezone.utc).isoformat()}")
