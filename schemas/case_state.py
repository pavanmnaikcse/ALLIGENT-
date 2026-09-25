"""case_state.py — LangGraph shared state object for a single investigation case.

This is the typed shared state that flows through the LangGraph graph.
It tracks: case lifecycle, per-agent status, all findings, the event
timeline, ranked hypotheses, verifier result, recommendation, human
decision, escalation state, and edge-case fields (superseded_by,
merged_into) per Section 12.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from .agent_output import (
    AgentFinding,
    CorrelationResult,
    RecommendationResult,
    RootCauseResult,
    VerifierResult,
)
from .evidence import EvidenceStore


class CaseStatus(str, Enum):
    """Lifecycle states of an investigation case."""

    OPEN = "open"
    INVESTIGATING = "investigating"
    AWAITING_VERIFICATION = "awaiting_verification"
    AWAITING_DECISION = "awaiting_decision"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    SUPERSEDED = "superseded"
    MERGED = "merged"
    CLOSED = "closed"


class AgentStatus(str, Enum):
    """Status of an individual agent within a case."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class EscalationLevel(int, Enum):
    """Escalation ladder levels."""

    NONE = 0
    DASHBOARD_ALERT = 1
    VOICE_CALL = 2
    EMAIL_PDF = 3


class HumanDecision(BaseModel):
    """Record of the human engineer's decision."""

    action: str = Field(..., description="'approve', 'reject', or 'modify'.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="For 'modify': the adjusted parameter changes.",
    )
    operator_id: str = Field(default="operator", description="Who made the decision.")
    notes: str = Field(default="")


class CaseState(BaseModel):
    """The complete shared state for one investigation case.

    This is the LangGraph state object — every node reads from and writes
    to fields in this model.
    """

    # ── Identity & lifecycle ────────────────────────────────────────
    case_id: str = Field(..., description="Unique case identifier.")
    status: CaseStatus = Field(default=CaseStatus.OPEN)
    severity: str = Field(default="medium", description="'low', 'medium', 'high', 'critical'.")
    machine_id: str = Field(..., description="Primary machine under investigation.")
    line_id: str = Field(..., description="Production line.")

    # ── Timing ──────────────────────────────────────────────────────
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = None
    investigation_start: Optional[datetime] = None
    investigation_end: Optional[datetime] = None
    wall_time_seconds: Optional[float] = Field(
        default=None,
        description="Actual wall-clock time the investigation took.",
    )

    # ── Evidence window (frozen at case-open, Section 12) ──────────
    evidence_window_start: datetime = Field(
        ..., description="Start of the telemetry window frozen at case-open."
    )
    evidence_window_end: datetime = Field(
        ..., description="End of the telemetry window frozen at case-open."
    )
    evidence_store: EvidenceStore = Field(default_factory=EvidenceStore)

    # ── Per-agent status ────────────────────────────────────────────
    agent_statuses: dict[str, AgentStatus] = Field(
        default_factory=lambda: {
            "machine": AgentStatus.PENDING,
            "process": AgentStatus.PENDING,
            "quality": AgentStatus.PENDING,
            "material": AgentStatus.PENDING,
            "energy": AgentStatus.PENDING,
            "integrity": AgentStatus.PENDING,
            "history": AgentStatus.PENDING,
            "correlation": AgentStatus.PENDING,
            "root_cause": AgentStatus.PENDING,
            "verifier": AgentStatus.PENDING,
            "recommendation": AgentStatus.PENDING,
            "communication": AgentStatus.PENDING,
        },
    )

    # ── Agent findings ──────────────────────────────────────────────
    findings: dict[str, AgentFinding] = Field(
        default_factory=dict,
        description="Agent name → its validated AgentFinding.",
    )

    # ── Reducer chain outputs ───────────────────────────────────────
    correlation_result: Optional[CorrelationResult] = None
    root_cause_result: Optional[RootCauseResult] = None
    verifier_result: Optional[VerifierResult] = None
    recommendation_result: Optional[RecommendationResult] = None

    # ── Human decision ──────────────────────────────────────────────
    decision: Optional[HumanDecision] = None

    # ── Escalation ──────────────────────────────────────────────────
    escalation_level: EscalationLevel = Field(default=EscalationLevel.NONE)
    acknowledged: bool = Field(default=False)
    acknowledged_at: Optional[datetime] = None
    escalation_log: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Audit log of every escalation action taken.",
    )

    # ── Edge-case handling (Section 12) ─────────────────────────────
    superseded_by: Optional[str] = Field(
        default=None,
        description="Case ID of the new case that superseded this one.",
    )
    merged_into: Optional[str] = Field(
        default=None,
        description="Case ID this case was merged into.",
    )

    # ── Metadata ────────────────────────────────────────────────────
    trigger_evidence_ids: list[str] = Field(
        default_factory=list,
        description="Evidence IDs that triggered case opening.",
    )
    parameter_snapshot_at_open: dict[str, Any] = Field(
        default_factory=dict,
        description="Snapshot of all parameters at case-open time.",
    )
    tags: list[str] = Field(default_factory=list)
    notes: str = Field(default="")
