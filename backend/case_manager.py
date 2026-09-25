"""case_manager.py -- Case lifecycle management (Section 12).

Handles:
- Opening cases with frozen evidence windows
- Cooldown to prevent case storms
- Mid-investigation parameter changes: supersede or merge
- Case state transitions
"""

from __future__ import annotations

import uuid
import pymongo
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from schemas.case_state import CaseState, CaseStatus, AgentStatus, EscalationLevel
from schemas.evidence import EvidenceStore


class CaseManager:
    """Manages the lifecycle of investigation cases.

    Enforces:
    - Evidence window freeze at case-open (Section 12)
    - Cooldown between cases on the same machine/line (Section 12)
    - Supersede/merge on mid-investigation parameter changes (Section 12)
    """

    def __init__(self, cooldown_ticks: int = 60):
        self._cases: dict[str, CaseState] = {}
        self._active_cases: dict[str, str] = {}  # machine_id -> case_id (if active)
        self._last_case_tick: dict[str, int] = {}  # machine_id -> tick when last case opened
        self._cooldown_ticks = cooldown_ticks
        self._lock = threading.Lock()
        self._load_from_mongo()

    def _load_from_mongo(self):
        try:
            import pymongo
            import os
            mongo_host = os.environ.get('MONGO_HOST', 'host.docker.internal')
            client = pymongo.MongoClient(f"mongodb://{mongo_host}:27017/?directConnection=true", serverSelectionTimeoutMS=2000)
            db = client["factorybrain"]
            col = db["cases"]
            docs = col.find()
            for doc in docs:
                try:
                    doc.pop('_id', None)
                    case = CaseState(**doc)
                    self._cases[case.case_id] = case
                    if case.status not in ("closed", "resolved"):
                        self._active_cases[case.machine_id] = case.case_id
                except Exception as ex:
                    print(f"Failed to load case {doc.get('case_id')}: {ex}")
            print(f"Loaded {len(self._cases)} cases from MongoDB", flush=True)
        except Exception as e:
            print(f"Failed to load cases from MongoDB: {e}", flush=True)



    def _sync_to_mongo(self, case):
        try:
            if not hasattr(self, '_mongo_client'):
                import pymongo
                import os
                mongo_host = os.environ.get('MONGO_HOST', 'host.docker.internal')
                self._mongo_client = pymongo.MongoClient(f"mongodb://{mongo_host}:27017/?directConnection=true", serverSelectionTimeoutMS=2000)
                self._mongo_db = self._mongo_client["factorybrain"]
                self._mongo_col = self._mongo_db["cases"]
            
            data = case.model_dump(mode="json")
            # Upsert
            self._mongo_col.update_one({"case_id": case.case_id}, {"$set": data}, upsert=True)
            print("SYNCED TO MONGO:", case.case_id, flush=True)
        except Exception as e:
            print(f"Failed to sync case to MongoDB: {e}", flush=True)

    def save_case(self, case_id: str):
        print(f"save_case called with {case_id}", flush=True)
        with self._lock:
            case = self._cases.get(case_id)
            if case:
                print(f"case found, syncing {case_id}", flush=True)
                self._sync_to_mongo(case)
            else:
                print(f"case not found in dict: {case_id}", flush=True)


    #     # ── Open a new case ─────────────────────────────────────────────

    def open_case(
        self,
        machine_id: str,
        line_id: str,
        current_tick: int,
        evidence_window_start: datetime,
        evidence_window_end: datetime,
        trigger_evidence_ids: list[str] = None,
        parameter_snapshot: dict[str, Any] = None,
        severity: str = "medium",
    ) -> Optional[CaseState]:
        """Open a new investigation case.

        Returns None if cooldown is still active for this machine.
        If a case is already active for this machine, the new case
        supersedes the old one (Section 12).
        """
        with self._lock:
            # Check cooldown
            last_tick = self._last_case_tick.get(machine_id, -9999)
            if current_tick - last_tick < self._cooldown_ticks:
                return None  # cooldown active

            # Check for existing active case -> supersede
            existing_case_id = self._active_cases.get(machine_id)
            superseded_case = None
            if existing_case_id and existing_case_id in self._cases:
                existing = self._cases[existing_case_id]
                if existing.status in (CaseStatus.OPEN, CaseStatus.INVESTIGATING):
                    superseded_case = existing

            # Create the new case
            case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
            case = CaseState(
                case_id=case_id,
                machine_id=machine_id,
                line_id=line_id,
                status=CaseStatus.OPEN,
                severity=severity,
                evidence_window_start=evidence_window_start,
                evidence_window_end=evidence_window_end,  # FROZEN at open
                trigger_evidence_ids=trigger_evidence_ids or [],
                parameter_snapshot_at_open=parameter_snapshot or {},
            )

            # Handle supersession
            if superseded_case is not None:
                superseded_case.status = CaseStatus.SUPERSEDED
                superseded_case.superseded_by = case_id
                superseded_case.closed_at = datetime.now(timezone.utc)

            self._cases[case_id] = case
            self._sync_to_mongo(case)
            self._active_cases[machine_id] = case_id
            self._last_case_tick[machine_id] = current_tick

            return case

    # ── Case state transitions ──────────────────────────────────────

    def start_investigation(self, case_id: str) -> Optional[CaseState]:
        """Transition a case to INVESTIGATING status."""
        with self._lock:
            case = self._cases.get(case_id)
            if case and case.status == CaseStatus.OPEN:
                case.status = CaseStatus.INVESTIGATING
                case.investigation_start = datetime.now(timezone.utc)
                self._sync_to_mongo(case)
            return case

    def complete_investigation(self, case_id: str) -> Optional[CaseState]:
        """Transition to AWAITING_DECISION after all agents finish."""
        with self._lock:
            case = self._cases.get(case_id)
            if case and case.status == CaseStatus.INVESTIGATING:
                case.status = CaseStatus.AWAITING_DECISION
                case.investigation_end = datetime.now(timezone.utc)
                if case.investigation_start:
                    delta = case.investigation_end - case.investigation_start
                    case.wall_time_seconds = delta.total_seconds()
                self._sync_to_mongo(case)
            return case

    def mark_needs_review(self, case_id: str) -> Optional[CaseState]:
        """Route to human review due to low confidence/trust (Section 10.3)."""
        with self._lock:
            case = self._cases.get(case_id)
            if case:
                case.status = CaseStatus.NEEDS_HUMAN_REVIEW
                self._sync_to_mongo(case)
            return case

    def apply_decision(
        self,
        case_id: str,
        action: str,
        payload: dict[str, Any] = None,
        operator_id: str = "operator",
        notes: str = "",
    ) -> Optional[CaseState]:
        """Apply a human decision (approve/reject/modify)."""
        from schemas.case_state import HumanDecision
        with self._lock:
            case = self._cases.get(case_id)
            if case is None:
                return None
            case.decision = HumanDecision(
                action=action,
                payload=payload or {},
                operator_id=operator_id,
                notes=notes,
            )
            if action == "approve":
                case.status = CaseStatus.APPROVED
            elif action == "reject":
                case.status = CaseStatus.REJECTED
            elif action == "modify":
                case.status = CaseStatus.MODIFIED
            self._sync_to_mongo(case)
            return case

    def close_case(self, case_id: str) -> Optional[CaseState]:
        """Close a case."""
        with self._lock:
            case = self._cases.get(case_id)
            if case:
                case.status = CaseStatus.CLOSED
                case.closed_at = datetime.now(timezone.utc)
                # Remove from active cases
                if self._active_cases.get(case.machine_id) == case_id:
                    del self._active_cases[case.machine_id]
                self._sync_to_mongo(case)
            return case

    def acknowledge(self, case_id: str) -> Optional[CaseState]:
        """Acknowledge a case (stops escalation timer)."""
        with self._lock:
            case = self._cases.get(case_id)
            if case:
                case.acknowledged = True
                case.acknowledged_at = datetime.now(timezone.utc)
                self._sync_to_mongo(case)
            return case

    # ── Mid-investigation parameter change handling (Section 12) ────

    def handle_parameter_change_during_investigation(
        self,
        machine_id: str,
        current_tick: int,
        change_tick: int,
        evidence_window_start: datetime,
        evidence_window_end: datetime,
        line_id: str = "L-03",
    ) -> Optional[CaseState]:
        """Handle a parameter change while a case is being investigated.

        If the change happens during an active investigation:
        - If close in time (within cooldown), don't open a new case (absorbed
          by cooldown logic).
        - Otherwise, supersede the current case with a new one.

        Returns the new case if created, None if cooldown blocked it.
        """
        with self._lock:
            active_id = self._active_cases.get(machine_id)
            if active_id and active_id in self._cases:
                active_case = self._cases[active_id]
                if active_case.status in (CaseStatus.OPEN, CaseStatus.INVESTIGATING):
                    # Check if cooldown allows a new case
                    last_tick = self._last_case_tick.get(machine_id, -9999)
                    if current_tick - last_tick < self._cooldown_ticks:
                        return None  # within cooldown — absorbed
        # Outside the lock, open a new case (which will supersede inside)
        return self.open_case(
            machine_id=machine_id,
            line_id=line_id,
            current_tick=current_tick,
            evidence_window_start=evidence_window_start,
            evidence_window_end=evidence_window_end,
        )

    # ── Queries ─────────────────────────────────────────────────────

    def get_case(self, case_id: str) -> Optional[CaseState]:
        return self._cases.get(case_id)

    def get_active_case(self, machine_id: str) -> Optional[CaseState]:
        cid = self._active_cases.get(machine_id)
        if cid:
            return self._cases.get(cid)
        return None

    def list_cases(self, status: Optional[CaseStatus] = None) -> list[CaseState]:
        if status:
            return [c for c in self._cases.values() if c.status == status]
        return list(self._cases.values())

    def is_cooldown_active(self, machine_id: str, current_tick: int) -> bool:
        last_tick = self._last_case_tick.get(machine_id, -9999)
        return (current_tick - last_tick) < self._cooldown_ticks

    @property
    def case_count(self) -> int:
        return len(self._cases)

    def set_cooldown(self, ticks: int) -> None:
        self._cooldown_ticks = ticks
