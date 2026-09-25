"""agent_output.py — Structured output every specialist agent must return.

Per R2: every specialist returns a schema-validated Pydantic JSON object.
Per R3: findings with empty evidence_ids are invalid and rejected.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TimedEvent(BaseModel):
    """A detected event with onset timing and magnitude."""

    variable: str = Field(..., description="Which signal/parameter changed, e.g. 'temperature_c'.")
    onset_time: datetime = Field(..., description="When the event started.")
    magnitude: float = Field(..., description="Size of the change (absolute or z-score).")
    direction: str = Field(
        default="increase",
        description="'increase' or 'decrease'.",
    )
    description: str = Field(default="", description="Human-readable note.")


class AgentFinding(BaseModel):
    """The unified output model every specialist agent returns.

    Validation enforces R3: evidence_ids must be non-empty for the finding
    to be accepted as a conclusion.
    """

    agent_name: str = Field(..., description="Name of the agent that produced this finding.")
    summary: str = Field(..., min_length=1, description="Brief textual summary of the finding.")
    evidence_ids: list[str] = Field(
        ...,
        description=(
            "IDs of Evidence objects supporting this finding. "
            "Must be non-empty (R3) — a finding with no evidence is rejected."
        ),
    )
    detected_events: list[TimedEvent] = Field(
        default_factory=list,
        description="Timed events detected by this agent.",
    )
    data_trust: float = Field(
        ...,
        ge=0.0, le=1.0,
        description=(
            "Data trust score for the relevant signal(s), COPIED from the "
            "evidence layer's precomputed trust_checks.py output — never "
            "independently computed inside a specialist (Section 8.1)."
        ),
    )
    confidence: float = Field(
        ...,
        ge=0.0, le=1.0,
        description="Confidence in the finding, computed from statistical effect size.",
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Agent-specific extra structured data.",
    )

    @field_validator("evidence_ids")
    @classmethod
    def _evidence_ids_non_empty(cls, v: list[str]) -> list[str]:
        """R3: a finding with no evidence ID is rejected."""
        if len(v) == 0:
            raise ValueError(
                "evidence_ids must be non-empty (R3). "
                "A finding with no evidence cannot be shown as a conclusion."
            )
        return v


# ── Correlation agent output ────────────────────────────────────────

class TimelineEntry(BaseModel):
    """One entry in the ordered event timeline built by the Correlation agent."""

    time: datetime
    event: str = Field(..., description="What happened.")
    source_agent: str = Field(..., description="Which specialist reported this.")
    evidence_id: str = Field(..., description="Evidence supporting this timeline entry.")
    causal_note: Optional[str] = Field(
        default=None,
        description="Causal annotation, e.g. 'precedes defect rise by ~45s'.",
    )


class CorrelationResult(BaseModel):
    """Output of the Correlation agent — an ordered, annotated event chain."""

    timeline: list[TimelineEntry] = Field(
        ..., min_length=1,
        description="Ordered sequence of events with causal annotations.",
    )
    lagged_correlations: dict[str, float] = Field(
        default_factory=dict,
        description="Pairwise lagged correlation coefficients between key signals.",
    )
    precedence_violations: list[str] = Field(
        default_factory=list,
        description="Causal-graph violations (e.g. 'defect_rate change preceded rpm change').",
    )


# ── Root-cause scoring output ───────────────────────────────────────

class HypothesisScore(BaseModel):
    """Scored hypothesis from the Root Cause agent."""

    hypothesis_id: str = Field(..., description="H1..H8 from the hypothesis library.")
    hypothesis_name: str
    raw_score: float = Field(..., description="Unnormalized score from the scoring formula.")
    normalized_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Softmax-normalized probability.",
    )
    temporal_precedence: float = Field(default=0.0)
    evidence_coverage: float = Field(default=0.0)
    historical_prior: float = Field(default=0.0)
    counterfactual_support: float = Field(default=0.0)
    contradictions: float = Field(default=0.0)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    explanation: str = Field(default="")


class RootCauseResult(BaseModel):
    """Output of the Root Cause agent — all eight hypotheses scored and ranked."""

    ranked_hypotheses: list[HypothesisScore] = Field(
        ..., min_length=1,
        description="All hypotheses ranked by normalized score, highest first.",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Overall confidence: f(score_gap_top_two, data_trust).",
    )
    needs_human_review: bool = Field(
        default=False,
        description="True if confidence is below the gating threshold (Section 10.3).",
    )
    scoring_weights: dict[str, float] = Field(
        default_factory=dict,
        description="The w1..w5 weights used, for transparency.",
    )


# ── Verifier output ────────────────────────────────────────────────

class CounterfactualReplayResult(BaseModel):
    """Result of one counterfactual replay run."""

    hypothesis_id: str
    snapshot_tick: int = Field(..., description="Tick index of the snapshot used.")
    parameter_reverted: str = Field(..., description="Which parameter was set back to pre-onset.")
    reverted_value: float
    original_value: float
    replay_ticks: int = Field(..., description="Number of ticks replayed forward.")
    anomaly_resolved: bool = Field(
        ...,
        description="True if the failure signature disappeared in the replay.",
    )
    peak_temperature_replay: Optional[float] = None
    peak_vibration_replay: Optional[float] = None
    peak_defect_rate_replay: Optional[float] = None
    explanation: str = Field(default="")


class VerifierResult(BaseModel):
    """Output of the Verifier agent."""

    top_hypothesis_id: str
    objections: list[str] = Field(
        default_factory=list,
        description="Devil's-advocate objections raised.",
    )
    objections_resolved: list[str] = Field(default_factory=list)
    objections_open: list[str] = Field(default_factory=list)
    replay_results: list[CounterfactualReplayResult] = Field(default_factory=list)
    adjusted_confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Confidence after verification (may go up or down).",
    )
    verdict: str = Field(
        ...,
        description="'confirmed', 'weakened', 'refuted', or 'inconclusive'.",
    )


# ── Recommendation output ──────────────────────────────────────────

class RecommendedAction(BaseModel):
    """One proposed corrective action with what-if prediction."""

    action_id: str
    description: str
    parameter_changes: dict[str, float] = Field(
        ...,
        description="Parameter path → proposed new value.",
    )
    predicted_defect_rate: float = Field(..., ge=0.0, le=1.0)
    predicted_kwh_per_unit: float = Field(..., ge=0.0)
    predicted_peak_temperature: float
    predicted_peak_vibration: float = Field(default=0.0)
    predicted_co2_per_unit: float = Field(..., ge=0.0)
    risk_level: str = Field(default="low", description="'low', 'medium', 'high'.")
    explanation: str = Field(default="")


class RecommendationResult(BaseModel):
    """Output of the Recommendation agent."""

    case_id: str
    verified_cause: str = Field(..., description="Hypothesis ID of the verified root cause.")
    actions: list[RecommendedAction] = Field(..., min_length=1)
    comparison_note: str = Field(
        default="",
        description="Side-by-side comparison note for multiple options.",
    )


class SimilarCase(BaseModel):
    case_id: str
    scenario_id: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    true_root_cause: str
    resolution_notes: str

class HistoryResult(BaseModel):
    similar_cases: list[SimilarCase] = Field(...)
