# ALLIGENT REST & WebSocket API Reference

**Product:** ALLIGENT — AI-Powered Industrial Investigation & Decision Support  
**Document:** API Specification & Endpoint Documentation  
**Version:** 1.0.0  
**Base URL:** `http://localhost:8000` (or `http://<host>:8000`)  

---

## 1. API Route Summary Table

| Method | Endpoint | Description | Request Body | Response Status |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | System health, MongoDB status, simulator state. | None | `200 OK` |
| `WS` | `/ws/telemetry` | Persistent 10Hz telemetry streaming channel. | WS Handshake | `101 Switching Protocols` |
| `POST` | `/parameters/batch` | Real-time override modulation of twin parameters. | `BatchParameterUpdate` | `200 OK` |
| `POST` | `/parameters/reset` | Resets all active manual overrides in digital twin. | None | `200 OK` |
| `POST` | `/scenarios/trigger` | Injects pre-configured fault scenarios. | `ScenarioTriggerRequest` | `200 OK` |
| `POST` | `/investigation/trigger`| Triggers full multi-agent diagnostic investigation. | `InvestigationRequest` | `202 Accepted` |
| `GET` | `/cases` | Lists all historical and active incident cases. | Query params (`limit`, `skip`)| `200 OK` |
| `GET` | `/cases/{case_id}` | Retrieves detailed telemetry and investigation for a case. | Path param (`case_id`) | `200 OK` / `404 Not Found` |
| `POST` | `/reports/generate-pdf`| Dynamically compiles 21-section ReportLab engineering PDF. | `PDFReportRequest` | `200 OK` (`application/pdf`) |
| `POST` | `/alerts/email` | Dispatches executive action email with attached PDF. | `EmailAlertRequest` | `200 OK` |
| `POST` | `/alerts/voice` | Triggers automated Twilio emergency voice phone call. | `VoiceAlertRequest` | `200 OK` |

---

## 2. Endpoint Details & Payloads

### 2.1 System Health (`GET /health`)
Returns current backend execution state, database connectivity, and active simulator tick counter.

* **Response:**
```json
{
  "status": "healthy",
  "system": "ALLIGENT Industrial Core",
  "version": "1.0.0",
  "digital_twin": {
    "status": "running",
    "frequency_hz": 10,
    "active_overrides": 0
  },
  "database": {
    "mongodb_connected": true,
    "redis_connected": true
  },
  "timestamp": 1727254800.124
}
```

---

### 2.2 Parameter Modulation (`POST /parameters/batch`)
Allows external controllers, test harnesses, and the Mobile Gateway to modulate physical parameters on the live running twin.

* **Request Body:**
```json
{
  "spindle_speed": 17200.0,
  "coolant_pressure": 1.5,
  "feed_rate": 2600.0
}
```
* **Response:**
```json
{
  "status": "success",
  "applied_overrides": {
    "spindle_speed": 17200.0,
    "coolant_pressure": 1.5,
    "feed_rate": 2600.0
  },
  "timestamp": 1727254802.155
}
```

---

### 2.3 Scenario Injection (`POST /scenarios/trigger`)
Injects a deterministic, pre-calibrated multi-stage industrial fault scenario into the digital twin.

* **Request Body:**
```json
{
  "scenario_id": "SCN-BEARING-STARVATION",
  "duration_seconds": 60,
  "intensity": 0.85
}
```
* **Supported Scenario IDs:**
  * `SCN-BEARING-STARVATION`: Coolant pump pressure drop followed by bearing temperature surge.
  * `SCN-TOOL-BREAKAGE`: Sudden cutting force shock, severe vibration chatter, and edge failure.
  * `SCN-MOTOR-OVERLOAD`: Axis binding leading to excessive active power draw.
* **Response:**
```json
{
  "status": "injected",
  "scenario_id": "SCN-BEARING-STARVATION",
  "start_timestamp": 1727254805.000,
  "estimated_alarm_time": "12 seconds"
}
```

---

### 2.4 Multi-Agent Investigation (`POST /investigation/trigger`)
Initiates the 4-phase multi-agent diagnostic pipeline across the 11 specialized agents.

* **Request Body:**
```json
{
  "machine_id": "CNC-M04",
  "trigger_reason": "MANUAL_INVESTIGATION",
  "evidence_snapshot": {
    "temperature": 78.4,
    "vibration": 4.82,
    "spindle_speed": 14200.0
  }
}
```
* **Response (`202 Accepted`):**
```json
{
  "investigation_id": "INV-2026-0925-0012",
  "status": "PROCESSING",
  "case_id": "INC-2026-0925-0042",
  "active_phase": "PHASE_1_DOMAIN_SPECIALISTS"
}
```

---

### 2.5 Generate Engineering PDF Report (`POST /reports/generate-pdf`)
Compiles the complete 21-section technical report dynamically.

* **Request Body:**
```json
{
  "case_id": "INC-2026-0925-0042",
  "include_fft_spectra": true,
  "include_loto_protocol": true
}
```
* **Response:** Binary PDF stream (`Content-Type: application/pdf`, `Content-Disposition: attachment; filename="ALLIGENT-INC-M04-REPORT.pdf"`).

---

### 2.6 Emergency Voice Call Dispatch (`POST /alerts/voice`)
Initiates a spoken briefing via Twilio Voice API.

* **Request Body:**
```json
{
  "recipient_phone": "+15551234567",
  "recipient_name": "Prajwal",
  "machine_id": "CNC-M04",
  "custom_message": "Alligent speaking this machine is facing issue please look after it"
}
```
* **Response:**
```json
{
  "status": "queued",
  "call_sid": "CA1234567890abcdef1234567890abcdef",
  "timestamp": 1727254810.500
}
```

---

## 3. Error Codes & Validation

ALLIGENT APIs strictly enforce Pydantic v2 schemas. In the event of a validation or runtime error, endpoints return standard RFC-7807 error responses:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Field 'coolant_pressure' must be greater than or equal to 0.0 bar",
    "details": [
      {
        "loc": ["body", "coolant_pressure"],
        "msg": "Input should be greater than or equal to 0.0",
        "type": "greater_than_equal"
      }
    ]
  }
}
```
