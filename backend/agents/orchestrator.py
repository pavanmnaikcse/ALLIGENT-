"""orchestrator.py -- LangGraph investigation orchestrator (Section 9/10).

Topology:
  1. PREPARE: populate evidence store with trust (Section 8.1)
  2. FAN-OUT: Anomaly + Correlation + RootCause run in parallel
  3. REDUCE: Verifier (adversarial) reads all specialist findings
  4. REDUCE: Recommendation reads verified findings
  5. GATE: confidence/trust gating -> route to human or auto-close

The graph uses CaseState as its shared state, passed by reference.
Evidence store is injected via config.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from schemas.case_state import CaseState, CaseStatus, AgentStatus
from schemas.evidence import EvidenceStore
from backend.ingestion.feature_engine import FeatureEngine
from backend.ingestion.trust_checks import compute_trust_evidence


# =====================================================================
# Agent registry -- maps agent name to its callable
# =====================================================================

AgentCallable = Callable[[CaseState, EvidenceStore], CaseState]

_AGENT_REGISTRY: dict[str, AgentCallable] = {}


def register_agent(name: str, fn: AgentCallable) -> None:
    """Register a specialist agent function."""
    _AGENT_REGISTRY[name] = fn


def get_agent(name: str) -> AgentCallable:
    """Look up a registered agent."""
    if name not in _AGENT_REGISTRY:
        raise ValueError(f"Agent '{name}' not registered. Available: {list(_AGENT_REGISTRY.keys())}")
    return _AGENT_REGISTRY[name]


# =====================================================================
# Orchestrator context -- injected into the graph
# =====================================================================

class OrchestratorContext:
    """Holds references to shared resources for the investigation."""

    def __init__(
        self,
        evidence_store: EvidenceStore,
        feature_engine: FeatureEngine,
        twin_state: dict,
        twin: Any = None,
        confidence_threshold: float = 0.4,
        data_trust_threshold: float = 0.5,
    ):
        self.evidence_store = evidence_store
        self.feature_engine = feature_engine
        self.twin_state = twin_state
        self.twin = twin
        self.confidence_threshold = confidence_threshold
        self.data_trust_threshold = data_trust_threshold
        self.execution_log: list[str] = []

    def log(self, msg: str) -> None:
        self.execution_log.append(msg)


# =====================================================================
# Graph nodes
# =====================================================================

def prepare_node(state: CaseState, ctx: OrchestratorContext) -> CaseState:
    """PREPARE: populate trust evidence BEFORE any agent runs.

    This is the Section 8.1 fix -- trust is computed once, here,
    in the evidence layer, before the agent fan-out.
    """
    ctx.log("PREPARE: computing trust evidence")
    state.status = CaseStatus.INVESTIGATING
    state.investigation_start = datetime.now(timezone.utc)

    compute_trust_evidence(
        ctx.feature_engine,
        ctx.twin_state,
        ctx.evidence_store,
        window_start=state.evidence_window_start,
        window_end=state.evidence_window_end,
    )

    # Mark all agents as PENDING
    for agent_name in ["anomaly_specialist", "correlation_specialist",
                       "root_cause_specialist", "verifier", "recommendation"]:
        state.agent_statuses[agent_name] = AgentStatus.PENDING

    ctx.log(f"PREPARE: trust evidence populated, "
            f"{len(ctx.evidence_store.by_source('trust_check'))} trust items")
    return state


def fan_out_node(state: CaseState, ctx: OrchestratorContext) -> CaseState:
    ctx.log("FAN-OUT: starting parallel specialists")

    for agent_name in ["machine", "process", "quality", "material", "energy", "integrity", "history", "correlation", "root_cause"]:
        state.agent_statuses[agent_name] = AgentStatus.RUNNING
        ctx.log(f"  Running {agent_name}")

        try:
            from backend.main import case_manager
            case_manager._cases[state.case_id] = state
            case_manager.save_case(state.case_id)
        except Exception as e:
            print("Failed to save live state:", e)

        agent_fn = get_agent(agent_name)
        state = agent_fn(state, ctx)

        if state.agent_statuses.get(agent_name) != AgentStatus.COMPLETED:
            state.agent_statuses[agent_name] = AgentStatus.COMPLETED

        try:
            case_manager._cases[state.case_id] = state
            case_manager.save_case(state.case_id)
        except Exception as e:
            pass

    ctx.log(f"FAN-OUT: complete, {len(state.findings)} findings so far")
    return state


def verifier_node(state: CaseState, ctx: OrchestratorContext) -> CaseState:
    ctx.log("REDUCE: running verifier")
    state.agent_statuses["verifier"] = AgentStatus.RUNNING

    try:
        from backend.main import case_manager
        case_manager._cases[state.case_id] = state
        case_manager.save_case(state.case_id)
    except: pass

    agent_fn = get_agent("verifier")
    state = agent_fn(state, ctx)

    try:
        case_manager._cases[state.case_id] = state
        case_manager.save_case(state.case_id)
    except: pass

    ctx.log(f"REDUCE: verifier complete, {len(state.findings)} findings")
    return state


def recommendation_node(state: CaseState, ctx: OrchestratorContext) -> CaseState:
    ctx.log("REDUCE: running recommendation")
    state.agent_statuses["recommendation"] = AgentStatus.RUNNING

    try:
        from backend.main import case_manager
        case_manager._cases[state.case_id] = state
        case_manager.save_case(state.case_id)
    except: pass

    agent_fn = get_agent("recommendation")
    state = agent_fn(state, ctx)

    try:
        case_manager._cases[state.case_id] = state
        case_manager.save_case(state.case_id)
    except: pass

    ctx.log(f"REDUCE: recommendation complete, {len(state.findings)} findings")
    return state


def confidence_gate_node(state: CaseState, ctx: OrchestratorContext) -> CaseState:
    """GATE: Check confidence and trust -- route to human or auto-close.

    Section 10.3: if max_confidence < threshold OR any data_trust < threshold,
    route to NEEDS_HUMAN_REVIEW.
    """
    ctx.log("GATE: checking confidence and trust")

    if not state.findings:
        state.status = CaseStatus.NEEDS_HUMAN_REVIEW
        ctx.log("GATE: no findings -> needs human review")
        return state

    max_confidence = max(f.confidence for f in state.findings.values())
    min_trust = min(f.data_trust for f in state.findings.values())

    state.investigation_end = datetime.now(timezone.utc)
    if state.investigation_start:
        delta = state.investigation_end - state.investigation_start
        state.wall_time_seconds = delta.total_seconds()

    if max_confidence < ctx.confidence_threshold:
        state.status = CaseStatus.NEEDS_HUMAN_REVIEW
        ctx.log(f"GATE: max_confidence={max_confidence:.3f} < threshold "
                f"-> needs human review")
    elif min_trust < ctx.data_trust_threshold:
        state.status = CaseStatus.NEEDS_HUMAN_REVIEW
        ctx.log(f"GATE: min_trust={min_trust:.3f} < threshold "
                f"-> needs human review (low data trust)")
    else:
        state.status = CaseStatus.AWAITING_DECISION
        ctx.log(f"GATE: confidence={max_confidence:.3f}, trust={min_trust:.3f} "
                f"-> awaiting decision")

    return state


# =====================================================================
# Full pipeline -- runs the investigation graph
# =====================================================================

def run_investigation(
    case: CaseState,
    ctx: OrchestratorContext,
) -> CaseState:
    """Run the full investigation pipeline on a case.

    Executes the graph:
      PREPARE -> FAN-OUT -> VERIFIER -> RECOMMENDATION -> GATE

    Returns the updated CaseState.
    """
    ctx.log(f"=== Starting investigation for {case.case_id} ===")

    # Node execution order
    pipeline = [
        ("prepare", prepare_node),
        ("fan_out", fan_out_node),
        ("verifier", verifier_node),
        ("recommendation", recommendation_node),
        ("confidence_gate", confidence_gate_node),
    ]

    for node_name, node_fn in pipeline:
        case = node_fn(case, ctx)

    ctx.log(f"=== Investigation complete: status={case.status.value} ===")
    return case


# =====================================================================
# Registration of default stubs
# =====================================================================

def register_stubs() -> None:
    pass # Disable stubs



def register_llm_agents() -> None:
    """Register the real LLM agents (Step 8)."""
    from backend.agents.llm_specialists import (
        machine_agent_llm, process_agent_llm, quality_agent_llm, 
        material_agent_llm, energy_agent_llm, integrity_agent_llm, 
        history_agent_llm, correlation_agent_llm, root_cause_agent_llm, 
        verifier_agent_llm, recommendation_agent_llm
    )
    register_agent("machine", machine_agent_llm)
    register_agent("process", process_agent_llm)
    register_agent("quality", quality_agent_llm)
    register_agent("material", material_agent_llm)
    register_agent("energy", energy_agent_llm)
    register_agent("integrity", integrity_agent_llm)
    register_agent("history", history_agent_llm)
    
    register_agent("correlation", correlation_agent_llm)
    register_agent("root_cause", root_cause_agent_llm)
    register_agent("verifier", verifier_agent_llm)
    register_agent("recommendation", recommendation_agent_llm)

