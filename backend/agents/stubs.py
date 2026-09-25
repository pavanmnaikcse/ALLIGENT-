"""stubs.py -- Specialist agent stubs for Step 7 (orchestrator skeleton).

Each stub:
- Receives the CaseState with frozen evidence window + pre-populated trust
- Reads trust from the evidence store (does NOT compute it)
- Produces an AgentFinding with real evidence_ids (R3 enforced)
- Returns an updated CaseState

These stubs will be replaced by real agents in Step 8.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from schemas.agent_output import AgentFinding
from schemas.case_state import AgentStatus, CaseState
from schemas.evidence import Evidence, EvidenceSource, EvidenceStore
from backend.ingestion.trust_checks import get_trust_for_agent


# =====================================================================
# Helper: create a stub evidence object
# =====================================================================

def _create_stub_evidence(
    store: EvidenceStore,
    signal: str,
    statistic: str,
    value: float,
    description: str,
) -> Evidence:
    """Create and store a stub evidence item."""
    ev = Evidence(
        source=EvidenceSource.AGENT,
        signal=signal,
        window_start=datetime.now(timezone.utc),
        window_end=datetime.now(timezone.utc),
        statistic=statistic,
        value=value,
        description=description,
    )
    store.add(ev)
    return ev


# =====================================================================
# Anomaly Specialist Stub
# =====================================================================

def anomaly_agent_stub(
    state: CaseState,
    evidence_store: EvidenceStore,
) -> CaseState:
    """Stub anomaly detection agent."""
    machine_id = state.machine_id
    data_trust = get_trust_for_agent(evidence_store, f"machines.{machine_id}")

    ev = _create_stub_evidence(
        evidence_store,
        signal=f"machines.{machine_id}.temperature_c",
        statistic="anomaly_score",
        value=-0.5,
        description=f"[STUB] Anomaly detected on {machine_id} temperature",
    )

    finding = AgentFinding(
        agent_name="anomaly_specialist",
        summary=f"[STUB] Anomaly detected on machine {machine_id}",
        confidence=0.7,
        evidence_ids=[ev.id],
        data_trust=data_trust,
    )

    state.findings["anomaly_specialist"] = finding
    state.agent_statuses["anomaly_specialist"] = AgentStatus.COMPLETED
    return state


# =====================================================================
# Correlation Specialist Stub
# =====================================================================

def correlation_agent_stub(
    state: CaseState,
    evidence_store: EvidenceStore,
) -> CaseState:
    """Stub correlation / timeline agent."""
    machine_id = state.machine_id
    data_trust = get_trust_for_agent(evidence_store, f"machines.{machine_id}")

    ev = _create_stub_evidence(
        evidence_store,
        signal=f"machines.{machine_id}.vibration_mm_s",
        statistic="lag_correlation",
        value=0.85,
        description=f"[STUB] Vibration leads temperature by 5 ticks on {machine_id}",
    )

    finding = AgentFinding(
        agent_name="correlation_specialist",
        summary=f"[STUB] Timeline: vibration leads temperature on {machine_id}",
        confidence=0.65,
        evidence_ids=[ev.id],
        data_trust=data_trust,
    )

    state.findings["correlation_specialist"] = finding
    state.agent_statuses["correlation_specialist"] = AgentStatus.COMPLETED
    return state


# =====================================================================
# Root-Cause Specialist Stub
# =====================================================================

def root_cause_agent_stub(
    state: CaseState,
    evidence_store: EvidenceStore,
) -> CaseState:
    """Stub root-cause analysis agent."""
    machine_id = state.machine_id
    data_trust = get_trust_for_agent(evidence_store, f"machines.{machine_id}")

    ev = _create_stub_evidence(
        evidence_store,
        signal=f"machines.{machine_id}.rpm",
        statistic="hypothesis_match",
        value=0.9,
        description=f"[STUB] RPM excess matches H1 pattern on {machine_id}",
    )

    finding = AgentFinding(
        agent_name="root_cause_specialist",
        summary=f"[STUB] Root cause: H1 (speed above safe envelope) on {machine_id}",
        confidence=0.75,
        evidence_ids=[ev.id],
        data_trust=data_trust,
    )

    state.findings["root_cause_specialist"] = finding
    state.agent_statuses["root_cause_specialist"] = AgentStatus.COMPLETED
    return state


# =====================================================================
# Verifier Stub (REDUCER -- runs AFTER fan-out)
# =====================================================================

def verifier_agent_stub(
    state: CaseState,
    evidence_store: EvidenceStore,
) -> CaseState:
    """Stub verifier agent (adversarial)."""
    machine_id = state.machine_id
    data_trust = get_trust_for_agent(evidence_store, f"machines.{machine_id}")

    specialist_findings = {
        k: v for k, v in state.findings.items()
        if k in ("anomaly_specialist", "correlation_specialist", "root_cause_specialist")
    }

    ev = _create_stub_evidence(
        evidence_store,
        signal=f"machines.{machine_id}.temperature_c",
        statistic="counterfactual_check",
        value=0.8,
        description=f"[STUB] Counterfactual replay supports root cause on {machine_id}",
    )

    finding = AgentFinding(
        agent_name="verifier",
        summary=(
            f"[STUB] Verified: {len(specialist_findings)} specialist findings reviewed. "
            f"Counterfactual supports root cause."
        ),
        confidence=0.7,
        evidence_ids=[ev.id],
        data_trust=data_trust,
    )

    state.findings["verifier"] = finding
    state.agent_statuses["verifier"] = AgentStatus.COMPLETED
    return state


# =====================================================================
# Recommendation Stub (REDUCER -- runs AFTER verifier)
# =====================================================================

def recommendation_agent_stub(
    state: CaseState,
    evidence_store: EvidenceStore,
) -> CaseState:
    """Stub recommendation agent."""
    machine_id = state.machine_id
    data_trust = get_trust_for_agent(evidence_store, f"machines.{machine_id}")

    ev = _create_stub_evidence(
        evidence_store,
        signal=f"machines.{machine_id}.rpm",
        statistic="recommendation",
        value=1200.0,
        description=f"[STUB] Recommend resetting RPM to safe range on {machine_id}",
    )

    finding = AgentFinding(
        agent_name="recommendation",
        summary=f"[STUB] Recommendation: reset target_rpm to 1200 on {machine_id}",
        confidence=0.8,
        evidence_ids=[ev.id],
        data_trust=data_trust,
    )

    state.findings["recommendation"] = finding
    state.agent_statuses["recommendation"] = AgentStatus.COMPLETED
    return state
