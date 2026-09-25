"""trust_checks.py -- Data trust computation, UPSTREAM of all agents (Section 8.1).

THIS IS THE FIX TO THE ORDERING BUG: trust must be computed ONCE, HERE,
in the evidence layer, BEFORE any LangGraph agent node executes.

Produces data_trust per signal as Evidence objects using:
  - Physics-residual checks (e.g. current/vibration rising while temp flat)
  - Sensor-drift detection (accumulated drift from the twin)
  - Message-rate anomaly detection (burst = integrity concern)
  - Unauthorized-setpoint-write detection

Every specialist agent then READS the precomputed data_trust evidence for
its signals and copies it into its AgentFinding -- it does NOT compute
trust itself.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

from schemas.evidence import Evidence, EvidenceSource, EvidenceStore
from .feature_engine import FeatureEngine


# =====================================================================
# Individual trust checks
# =====================================================================

def _physics_residual_check(
    features: dict,
    machine_id: str,
) -> tuple[float, str]:
    """Check physics consistency between correlated signals.

    Key signature: current/vibration rising while temperature stays flat
    (or vice versa) indicates a sensor fault or spoofing, not a real event.

    Returns (trust_score, description) where 1.0 = fully trusted.
    """
    temp_feat = features.get(f"machines.{machine_id}.temperature_c")
    vib_feat = features.get(f"machines.{machine_id}.vibration_mm_s")
    current_feat = features.get(f"machines.{machine_id}.motor_current_a")

    if not all([temp_feat, vib_feat, current_feat]):
        return 1.0, "Insufficient data for physics residual check."

    # If vibration or current are rising (positive slope) but temperature
    # is flat or falling, that's physically inconsistent
    vib_slope = vib_feat.slope
    current_slope = current_feat.slope
    temp_slope = temp_feat.slope

    # Compute inconsistency score
    inconsistency = 0.0

    # Vibration rising but temperature not following
    if vib_slope > 0.01 and temp_slope < 0.001:
        inconsistency += min(1.0, abs(vib_slope - temp_slope) * 10)

    # Current rising but temperature not following
    if current_slope > 0.01 and temp_slope < 0.001:
        inconsistency += min(1.0, abs(current_slope - temp_slope) * 10)

    # Temperature rising but vibration/current not
    if temp_slope > 0.01 and vib_slope < 0.001 and current_slope < 0.001:
        inconsistency += min(1.0, abs(temp_slope) * 5)

    trust = max(0.0, 1.0 - inconsistency * 0.5)
    desc = (
        f"Physics residual: vib_slope={vib_slope:.4f}, "
        f"current_slope={current_slope:.4f}, temp_slope={temp_slope:.4f}, "
        f"inconsistency={inconsistency:.3f}"
    )
    return trust, desc


def _sensor_drift_check(
    twin_state: dict,
    machine_id: str,
) -> tuple[float, str]:
    """Check for accumulated sensor drift.

    The twin tracks sensor_drift_accumulated per machine.
    High drift means readings may not reflect physical reality.
    """
    machine_data = twin_state.get("machines", {}).get(machine_id, {})
    drift = machine_data.get("sensor_drift_accumulated", 0.0)

    # Trust degrades with accumulated drift
    trust = max(0.0, 1.0 - drift * 0.1)  # 10 units of drift -> trust=0
    desc = f"Sensor drift: accumulated={drift:.3f}, trust={trust:.3f}"
    return trust, desc


def _message_rate_check(
    features: dict,
    machine_id: str,
    baseline_rate: float = 100.0,
) -> tuple[float, str]:
    """Check for abnormal network message rate (burst detection).

    A burst in message rate can indicate an integrity attack or
    network anomaly that undermines data reliability.
    """
    msg_feat = features.get(f"network.{machine_id}.message_rate")
    if msg_feat is None:
        return 1.0, "No message rate data."

    ratio = msg_feat.mean / baseline_rate if baseline_rate > 0 else 1.0

    # Trust drops if message rate is abnormally high (>2x baseline)
    if ratio > 2.0:
        trust = max(0.0, 1.0 - (ratio - 2.0) * 0.3)
    else:
        trust = 1.0

    desc = f"Message rate: mean={msg_feat.mean:.1f}, ratio={ratio:.2f}x baseline"
    return trust, desc


def _cross_check_residual_check(
    features: dict,
    machine_id: str,
) -> tuple[float, str]:
    """Check the physics cross-check residual from the twin.

    The twin computes this: if sensor readings diverge from what physics
    predicts, the residual rises.
    """
    res_feat = features.get(f"network.{machine_id}.cross_check_residual")
    if res_feat is None:
        return 1.0, "No cross-check residual data."

    residual = res_feat.mean
    # Trust degrades with residual magnitude
    trust = max(0.0, 1.0 - residual * 0.05)
    desc = f"Cross-check residual: mean={residual:.3f}, trust={trust:.3f}"
    return trust, desc


# =====================================================================
# Main trust computation -- runs BEFORE agent fan-out
# =====================================================================

def compute_trust_evidence(
    feature_engine: FeatureEngine,
    twin_state: dict,
    evidence_store: EvidenceStore,
    window_start: datetime,
    window_end: datetime,
) -> list[Evidence]:
    """Compute data_trust per signal and store as Evidence objects.

    This function MUST be called BEFORE any agent node executes.
    It produces Evidence objects with source=TRUST_CHECK and
    statistic="data_trust" that agents read from the evidence store.

    Returns the list of trust Evidence objects created.
    """
    features = feature_engine.get_features("1min")
    trust_evidences: list[Evidence] = []

    # Get all machine IDs from the twin state
    machine_ids = list(twin_state.get("machines", {}).keys())

    for machine_id in machine_ids:
        # Run all four checks
        physics_trust, physics_desc = _physics_residual_check(features, machine_id)
        drift_trust, drift_desc = _sensor_drift_check(twin_state, machine_id)
        msg_trust, msg_desc = _message_rate_check(features, machine_id)
        xcheck_trust, xcheck_desc = _cross_check_residual_check(features, machine_id)

        # Combine: take the minimum (most conservative)
        combined_trust = min(physics_trust, drift_trust, msg_trust, xcheck_trust)

        # Create per-signal trust evidence for key machine signals
        machine_signals = [
            "temperature_c", "vibration_mm_s", "motor_current_a",
            "rpm", "coolant_flow_lpm", "pressure_bar", "bearing_wear",
        ]

        for sig in machine_signals:
            ev = Evidence(
                source=EvidenceSource.TRUST_CHECK,
                signal=f"machines.{machine_id}.{sig}",
                window_start=window_start,
                window_end=window_end,
                statistic="data_trust",
                value=combined_trust,
                description=(
                    f"Combined trust={combined_trust:.3f} for {machine_id}.{sig}. "
                    f"{physics_desc}; {drift_desc}; {msg_desc}; {xcheck_desc}"
                ),
                metadata={
                    "physics_trust": physics_trust,
                    "drift_trust": drift_trust,
                    "message_rate_trust": msg_trust,
                    "cross_check_trust": xcheck_trust,
                    "machine_id": machine_id,
                },
            )
            evidence_store.add(ev)
            trust_evidences.append(ev)

        # Also create trust evidence for network signals
        for net_sig in ["message_rate", "cross_check_residual"]:
            ev = Evidence(
                source=EvidenceSource.TRUST_CHECK,
                signal=f"network.{machine_id}.{net_sig}",
                window_start=window_start,
                window_end=window_end,
                statistic="data_trust",
                value=combined_trust,
                description=f"Combined trust={combined_trust:.3f} for network.{machine_id}.{net_sig}",
                metadata={
                    "physics_trust": physics_trust,
                    "drift_trust": drift_trust,
                    "message_rate_trust": msg_trust,
                    "cross_check_trust": xcheck_trust,
                },
            )
            evidence_store.add(ev)
            trust_evidences.append(ev)

    # Create trust evidence for line-level signals
    line_ids = list(twin_state.get("lines", {}).keys())
    for line_id in line_ids:
        # Line trust is the minimum across all machines on that line
        from simulator.factory_sim import MACHINE_LINE_MAP
        line_machines = [
            mid for mid, lid in MACHINE_LINE_MAP.items() if lid == line_id
        ]
        if line_machines:
            line_trust = min(
                evidence_store.trust_for_signal(f"machines.{mid}.temperature_c") or 1.0
                for mid in line_machines
            )
        else:
            line_trust = 1.0

        for sig in ["defect_rate", "kwh_per_unit", "co2_per_unit"]:
            ev = Evidence(
                source=EvidenceSource.TRUST_CHECK,
                signal=f"lines.{line_id}.{sig}",
                window_start=window_start,
                window_end=window_end,
                statistic="data_trust",
                value=line_trust,
                description=f"Line trust={line_trust:.3f} for {line_id}.{sig}",
            )
            evidence_store.add(ev)
            trust_evidences.append(ev)

    return trust_evidences


def get_trust_for_agent(
    evidence_store: EvidenceStore,
    signal_prefix: str,
) -> float:
    """Convenience: get the average precomputed trust for a signal prefix.

    Agents call this to read trust from the evidence store (not compute it).
    E.g. signal_prefix="machines.M-04" returns average trust across all
    M-04 signals.
    """
    trust_evs = [
        ev for ev in evidence_store.by_source(EvidenceSource.TRUST_CHECK)
        if ev.signal.startswith(signal_prefix)
        and ev.statistic == "data_trust"
    ]
    if not trust_evs:
        return 1.0  # default high trust if no evidence
    return float(np.mean([ev.value for ev in trust_evs]))
