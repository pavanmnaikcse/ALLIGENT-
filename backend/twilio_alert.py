"""twilio_alert.py -- Automated & Custom Voice Alerting via Twilio API for Alligent.

Supports Twilio Trial Accounts using HTTPS Twimlets Echo with clean XML escaping.
Speaks the exact standardized Alligent prompt:
"Hello Prajwal. Alligent speaking, this machine is facing issue, please look after it."
"""

from __future__ import annotations

import os
import time
import urllib.parse
from xml.sax.saxutils import escape
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from twilio.rest import Client

# Load environment configuration
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
ENGINEER_PHONE_NUMBER = os.getenv("ENGINEER_PHONE_NUMBER", "+917019934791")

# Machine Name Mapping
MACHINE_NAMES = {
    "M-01": "Raw Material Feed & Ingestion Gateway",
    "M-02": "Automated Vision Quality Inspection Cell",
    "M-03": "Robotic Pick-and-Place Transfer Unit",
    "M-04": "High-Speed CNC Processing Unit",
    "M-05": "Finished Goods Sorting & Packaging Gate",
    "robot_pick_place": "Robotic Pick-and-Place Unit",
    "processing_unit": "High-Precision Processing Unit",
    "vision_automated": "Automated Vision Inspection System",
    "raw_materials": "Raw Materials Feeder",
    "finish_gate": "Finished Assembly Gate",
}

# In-memory cooldown tracking { "M-04": timestamp }
_COOLDOWN_MAP: dict[str, float] = {}
COOLDOWN_SECONDS = 5


def _sanitize_for_twiml(text: str) -> str:
    """Cleans and XML-escapes text for voice synthesis without XML parser errors."""
    if not text:
        return ""
    # Strip dangerous characters and replace ampersands
    clean = text.replace("&", " and ").replace("<", " ").replace(">", " ").replace('"', "'")
    return escape(clean.strip())


def trigger_voice_alert(
    case_id: str,
    machine_id: str,
    parameter: str = "Vibration and Temperature",
    current_val: str = "Critical threshold",
    threshold_val: str = "Safe Envelope",
    ai_explanation: str = "",
    risk_score: float = 85.0,
    failure_date: str = "December 03, 2026",
    decline_products: str = "960",
    to_phone: Optional[str] = None
) -> Optional[str]:
    """Triggers the automated escalation phone call directly via Twilio.
    
    Speaks the exact standardized Alligent prompt:
    'Alligent speaking, this machine is facing issue, please look after it.'
    Followed by asset telemetry, failure impact forecast, and immediate inspection mandate.
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        print("[Twilio] Credentials not configured in .env", flush=True)
        return None

    target_phone = to_phone or ENGINEER_PHONE_NUMBER
    if not target_phone:
        print("[Twilio] No destination phone number available.", flush=True)
        return None

    now = time.time()
    last_called = _COOLDOWN_MAP.get(machine_id, 0)
    if now - last_called < COOLDOWN_SECONDS:
        print(f"[Twilio] Voice alert skipped for {machine_id} due to {COOLDOWN_SECONDS}s cooldown.", flush=True)
        return None

    _COOLDOWN_MAP[machine_id] = now

    clean_machine = machine_id.replace("_", " ").title() if "_" in machine_id else machine_id
    machine_name = MACHINE_NAMES.get(machine_id, f"Machine {clean_machine}")
    
    explanation_clean = _sanitize_for_twiml(ai_explanation) if ai_explanation else "Sensors indicate accelerated mechanical wear and harmonic vibration."
    param_clean = _sanitize_for_twiml(parameter)
    val_clean = _sanitize_for_twiml(current_val)
    date_clean = _sanitize_for_twiml(failure_date)
    prod_clean = _sanitize_for_twiml(str(decline_products))

    # Standardized speech script integrating user's required wording:
    # "Alligent speaking this machine is facing issue look after it"
    twiml_payload = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response>'
        f'<Pause length="1"/>'
        f'<Say voice="alice">Hello Prajwal. Alligent speaking, this machine is facing issue, please look after it.</Say>'
        f'<Pause length="1"/>'
        f'<Say voice="alice">Machine {clean_machine}, {machine_name}, has triggered critical escalation for {param_clean}. Current value is {val_clean}.</Say>'
        f'<Say voice="alice">{explanation_clean}</Say>'
        f'<Pause length="1"/>'
        f'<Say voice="alice">Warning: If this defect persists, production will decline by {prod_clean} products, with projected breakdown by {date_clean}.</Say>'
        f'<Say voice="alice">The current machine risk score is {int(risk_score)} percent.</Say>'
        f'<Pause length="1"/>'
        f'<Say voice="alice">Please look after this machine and inspect it immediately.</Say>'
        f'<Say voice="alice">A complete 21-section engineering report has also been dispatched to your email. Goodbye.</Say>'
        f'</Response>'
    )

    encoded = urllib.parse.urlencode({"Twiml": twiml_payload})
    twimlet_url = f"https://twimlets.com/echo?{encoded}"

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        call = client.calls.create(
            to=target_phone,
            from_=TWILIO_PHONE_NUMBER,
            url=twimlet_url
        )
        print(f"[Twilio Voice Escalation SUCCESS] SID: {call.sid} -> {target_phone} | Case: {case_id} | Machine: {clean_machine}", flush=True)
        return call.sid
    except Exception as e:
        print(f"[Twilio Voice Escalation FAILED] {e}", flush=True)
        return None


def make_custom_voice_call(
    sentence: str,
    to_phone: Optional[str] = None,
    machine_id: str = "M-04",
    voice: str = "alice",
    include_intro: bool = True
) -> Dict[str, Any]:
    """Places an outbound voice call with a custom sentence provided by the user.
    
    Guarantees clean HTTPS Twimlets URL for trial accounts.
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        return {"success": False, "error": "Twilio account credentials not configured in environment"}

    target_phone = to_phone or ENGINEER_PHONE_NUMBER
    if not target_phone:
        return {"success": False, "error": "No recipient phone number specified"}

    clean_sentence = _sanitize_for_twiml(sentence)
    if not clean_sentence:
        return {"success": False, "error": "Sentence cannot be empty"}

    clean_machine = machine_id.replace("_", " ").title() if "_" in machine_id else machine_id
    machine_name = MACHINE_NAMES.get(machine_id, f"Machine {clean_machine}")

    intro_block = (
        f'<Say voice="{voice}">Hello Prajwal. Alligent speaking, this machine is facing issue, please look after it.</Say>'
        f'<Say voice="{voice}">Incident alert on {clean_machine}, {machine_name}.</Say>'
        f'<Pause length="1"/>'
        if include_intro else ""
    )

    twiml_payload = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response>'
        f'<Pause length="1"/>'
        f'{intro_block}'
        f'<Say voice="{voice}">{clean_sentence}</Say>'
        f'<Pause length="1"/>'
        f'<Say voice="{voice}">Please look after this machine immediately. Alligent dispatch complete. Goodbye.</Say>'
        f'</Response>'
    )

    encoded = urllib.parse.urlencode({"Twiml": twiml_payload})
    twimlet_url = f"https://twimlets.com/echo?{encoded}"

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        call = client.calls.create(
            to=target_phone,
            from_=TWILIO_PHONE_NUMBER,
            url=twimlet_url
        )

        print(f"[Twilio Custom Voice Call SUCCESS] SID: {call.sid} -> {target_phone} | Spoken: '{clean_sentence}'", flush=True)
        return {
            "success": True,
            "call_sid": call.sid,
            "to": target_phone,
            "sentence": clean_sentence,
            "voice": voice,
            "status": "queued"
        }
    except Exception as e:
        print(f"[Twilio Custom Voice Call FAILED] {e}", flush=True)
        return {
            "success": False,
            "error": str(e)
        }
