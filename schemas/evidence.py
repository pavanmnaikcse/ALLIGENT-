"""evidence.py — Evidence objects: the atomic unit of cited, traceable proof.

Every claim any agent makes must point at one or more Evidence objects by ID.
Trust-check outputs (Section 8.1) are also stored as Evidence objects, not as
a side-channel — they flow through the same evidence store as anomaly detections,
change-points, and correlations.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class EvidenceSource(str, Enum):
    """Where the evidence was generated."""

    ANOMALY_DETECTOR = "anomaly_detector"
    CHANGEPOINT = "changepoint"
    CORRELATION = "correlation"
    TRUST_CHECK = "trust_check"         # Section 8.1 — computed upstream of agents
    AGENT = "agent"                     # Agents can create evidence during analysis
    TWIN = "twin"                       # Direct twin state (e.g. snapshot diff)
    SETPOINT_LOG = "setpoint_log"       # Audit-log entries treated as evidence


class Evidence(BaseModel):
    """One piece of traceable evidence.

    Independently fetchable by ``id`` so any claim traces back to concrete
    data.  The ``source`` field tells you *what* produced this evidence; the
    ``signal`` field tells you which physical/logical signal it pertains to.
    """

    id: str = Field(
        default_factory=lambda: f"ev-{uuid.uuid4().hex[:12]}",
        description="Globally unique evidence identifier.",
    )
    source: EvidenceSource = Field(..., description="Subsystem that produced this evidence.")
    signal: str = Field(
        ...,
        description=(
            "Signal or parameter this evidence pertains to, "
            "e.g. 'machines.M-04.temperature_c', 'trust.M-04.vibration_mm_s'."
        ),
    )
    window_start: datetime = Field(..., description="Start of the data window analysed.")
    window_end: datetime = Field(..., description="End of the data window analysed.")
    statistic: str = Field(
        ...,
        description=(
            "Name of the statistic or method, e.g. 'isolation_forest_score', "
            "'cusum_change_point', 'physics_residual', 'data_trust'."
        ),
    )
    value: float = Field(..., description="Numeric result of the statistic.")
    description: str = Field(
        default="",
        description="Human-readable explanation of what this evidence means.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra structured data (thresholds, raw values, etc.).",
    )


class EvidenceStore(BaseModel):
    """In-memory evidence store for one case.

    Provides lookup by ID and by source so agents and the reducer chain can
    efficiently retrieve what they need.
    """

    items: dict[str, Evidence] = Field(default_factory=dict)

    def add(self, ev: Evidence) -> str:
        """Add an evidence object and return its id."""
        self.items[ev.id] = ev
        return ev.id

    def get(self, evidence_id: str) -> Optional[Evidence]:
        return self.items.get(evidence_id)

    def by_source(self, source: EvidenceSource) -> list[Evidence]:
        return [e for e in self.items.values() if e.source == source]

    def by_signal(self, signal: str) -> list[Evidence]:
        return [e for e in self.items.values() if e.signal == signal]

    def by_signal_prefix(self, prefix: str) -> list[Evidence]:
        """E.g. by_signal_prefix('machines.M-04') returns all evidence for M-04."""
        return [e for e in self.items.values() if e.signal.startswith(prefix)]

    def trust_for_signal(self, signal: str) -> Optional[float]:
        """Return the precomputed data_trust value for a signal, if available."""
        trust_evs = [
            e for e in self.items.values()
            if e.source == EvidenceSource.TRUST_CHECK
            and e.signal == signal
            and e.statistic == "data_trust"
        ]
        if trust_evs:
            # Most recent if multiple exist
            return sorted(trust_evs, key=lambda e: e.window_end)[-1].value
        return None

    @field_validator("items", mode="before")
    @classmethod
    def _coerce_list(cls, v: Any) -> dict:
        """Accept either a dict or a list of Evidence on construction."""
        if isinstance(v, list):
            return {ev.id if isinstance(ev, Evidence) else ev["id"]: ev for ev in v}
        return v
