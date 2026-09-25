"""hypotheses.py — The fixed hypothesis library (Section 6).

This is the SINGLE SOURCE OF TRUTH for the candidate root causes.  Both the
Root Cause agent's scoring (Section 10.1) and the benchmark harness
(Section 16) import from here — they never drift out of sync.

Each hypothesis maps to the concrete twin parameter(s) that represent it
(Section 13.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class HypothesisID(str, Enum):
    """The eight canonical hypotheses."""

    H1 = "H1"
    H2 = "H2"
    H3 = "H3"
    H4 = "H4"
    H5 = "H5"
    H6 = "H6"
    H7 = "H7"
    H8 = "H8"


@dataclass(frozen=True)
class HypothesisDefinition:
    """One entry in the hypothesis library."""

    id: HypothesisID
    name: str
    description: str
    twin_parameters: list[str]
    detection_signals: list[str]
    causal_direction: str  # e.g. "parameter up → symptom up"


# ── The library itself ──────────────────────────────────────────────

HYPOTHESIS_LIBRARY: dict[HypothesisID, HypothesisDefinition] = {

    HypothesisID.H1: HypothesisDefinition(
        id=HypothesisID.H1,
        name="Speed above safe envelope",
        description=(
            "RPM setpoint raised beyond the safe range for the current "
            "material batch — target_rpm exceeding rpm_stable_max given "
            "the active batch's material_sensitivity."
        ),
        twin_parameters=["target_rpm", "rpm_stable_max", "material_sensitivity"],
        detection_signals=[
            "machines.*.rpm",
            "machines.*.temperature_c",
            "machines.*.vibration_mm_s",
            "quality.*.defect_rate",
        ],
        causal_direction="target_rpm ↑ → temperature ↑, vibration ↑, defects ↑",
    ),

    HypothesisID.H2: HypothesisDefinition(
        id=HypothesisID.H2,
        name="Bearing wear",
        description=(
            "Elevated bearing_wear_rate causing accumulated bearing_wear(t) "
            "to raise vibration independently of RPM."
        ),
        twin_parameters=["bearing_wear_rate", "bearing_wear"],
        detection_signals=[
            "machines.*.vibration_mm_s",
            "machines.*.motor_current_a",
            "machines.*.temperature_c",
        ],
        causal_direction="bearing_wear ↑ → vibration ↑ (gradual), current ↑",
    ),

    HypothesisID.H3: HypothesisDefinition(
        id=HypothesisID.H3,
        name="Low coolant flow",
        description="Reduced coolant_flow_lpm causes temperature to rise.",
        twin_parameters=["coolant_flow_lpm"],
        detection_signals=[
            "machines.*.coolant_flow_lpm",
            "machines.*.temperature_c",
            "quality.*.defect_rate",
        ],
        causal_direction="coolant_flow ↓ → temperature ↑ → defects ↑",
    ),

    HypothesisID.H4: HypothesisDefinition(
        id=HypothesisID.H4,
        name="Bad material batch",
        description=(
            "Active batch switched to one with high material_sensitivity / "
            "hardness_deviation — raises load and lowers RPM tolerance."
        ),
        twin_parameters=["active_material_batch_id", "material_sensitivity", "hardness_deviation"],
        detection_signals=[
            "materials.*.batch_id",
            "materials.*.hardness_deviation",
            "quality.*.defect_rate",
            "machines.*.motor_current_a",
        ],
        causal_direction="material_sensitivity ↑ → defects ↑ at same RPM",
    ),

    HypothesisID.H5: HypothesisDefinition(
        id=HypothesisID.H5,
        name="Sensor drift or spoofing",
        description=(
            "Elevated sensor_drift_rate and/or unauthorized_write_probability "
            "produces a physics-inconsistent signal — e.g. current/vibration "
            "rising while temperature stays flat."
        ),
        twin_parameters=["sensor_drift_rate", "unauthorized_write_probability"],
        detection_signals=[
            "network.*.sensor_cross_check_residual",
            "network.*.message_rate",
            "trust.*",
        ],
        causal_direction="sensor_drift ↑ → cross-check residual ↑, trust ↓",
    ),

    HypothesisID.H6: HypothesisDefinition(
        id=HypothesisID.H6,
        name="Unauthorized setpoint write",
        description=(
            "A setpoint change in the audit log whose write-source fails "
            "the Integrity agent's source check."
        ),
        twin_parameters=["unauthorized_write_probability"],
        detection_signals=[
            "process.*.recent_setpoint_changes",
            "network.*.last_setpoint_write_source",
            "network.*.message_rate",
        ],
        causal_direction="unauthorized write → unexpected setpoint change → downstream effects",
    ),

    HypothesisID.H7: HypothesisDefinition(
        id=HypothesisID.H7,
        name="Noise only — no physical fault",
        description=(
            "Elevated sensor_noise_multiplier with no other parameter moved "
            "from baseline. A legitimate, honest output — not a failure."
        ),
        twin_parameters=["sensor_noise_multiplier"],
        detection_signals=["trust.*", "machines.*"],
        causal_direction="noise ↑ → spurious anomaly detections, but no consistent causal chain",
    ),

    HypothesisID.H8: HypothesisDefinition(
        id=HypothesisID.H8,
        name="Unknown / combined cause",
        description=(
            "None of H1–H7 scores decisively above the others, or two or "
            "more score comparably. This is a valid, honest output, not a "
            "failure state."
        ),
        twin_parameters=[],  # No single parameter — that's the point
        detection_signals=[],
        causal_direction="multiple or unclear causal chains",
    ),
}


# ── Scenario → Hypothesis mapping (Section 7.2) ────────────────────

@dataclass(frozen=True)
class ScenarioMapping:
    """Maps a named scenario to its ground-truth hypothesis/hypotheses."""

    scenario_id: str
    name: str
    description: str
    ground_truth_hypotheses: list[HypothesisID]
    parameter_changes: dict[str, str]  # parameter_path → qualitative change description


SCENARIO_HYPOTHESIS_MAP: dict[str, ScenarioMapping] = {

    "S1": ScenarioMapping(
        scenario_id="S1",
        name="Speed setpoint raised beyond safe range",
        description="target_rpm raised above rpm_stable_max for the current batch.",
        ground_truth_hypotheses=[HypothesisID.H1],
        parameter_changes={"target_rpm": "raised above rpm_stable_max"},
    ),

    "S2": ScenarioMapping(
        scenario_id="S2",
        name="Sensor drift/spoofed readings + unauthorized write",
        description=(
            "sensor_drift_rate elevated and/or unauthorized_write_probability "
            "raised, with possible message_rate burst."
        ),
        ground_truth_hypotheses=[HypothesisID.H5, HypothesisID.H6],
        parameter_changes={
            "sensor_drift_rate": "elevated",
            "unauthorized_write_probability": "elevated",
            "message_rate_burst_multiplier": "may be elevated",
        },
    ),

    "S3": ScenarioMapping(
        scenario_id="S3",
        name="Coolant flow drops",
        description="coolant_flow_lpm reduced significantly.",
        ground_truth_hypotheses=[HypothesisID.H3],
        parameter_changes={"coolant_flow_lpm": "reduced"},
    ),

    "S4": ScenarioMapping(
        scenario_id="S4",
        name="Gradual bearing wear",
        description="bearing_wear_rate elevated, causing gradual wear accumulation.",
        ground_truth_hypotheses=[HypothesisID.H2],
        parameter_changes={"bearing_wear_rate": "elevated"},
    ),

    "S5": ScenarioMapping(
        scenario_id="S5",
        name="Bad material batch swapped in",
        description=(
            "active_material_batch_id switched to a batch with high "
            "material_sensitivity and hardness_deviation."
        ),
        ground_truth_hypotheses=[HypothesisID.H4],
        parameter_changes={
            "active_material_batch_id": "switched to bad batch",
            "material_sensitivity": "high",
            "hardness_deviation": "high",
        },
    ),

    "NOISE_ONLY": ScenarioMapping(
        scenario_id="NOISE_ONLY",
        name="Noise-only negative test",
        description="Only sensor_noise_multiplier raised — no physical fault.",
        ground_truth_hypotheses=[HypothesisID.H7],
        parameter_changes={"sensor_noise_multiplier": "elevated"},
    ),
}


def get_hypothesis(h_id: HypothesisID) -> HypothesisDefinition:
    """Look up a hypothesis by ID."""
    return HYPOTHESIS_LIBRARY[h_id]


def get_all_hypotheses() -> list[HypothesisDefinition]:
    """Return all hypotheses in canonical order H1..H8."""
    return [HYPOTHESIS_LIBRARY[h] for h in HypothesisID]


def get_scenario_ground_truth(scenario_id: str) -> list[HypothesisID]:
    """Return the ground-truth hypothesis IDs for a scenario."""
    mapping = SCENARIO_HYPOTHESIS_MAP.get(scenario_id)
    if mapping is None:
        raise ValueError(f"Unknown scenario: {scenario_id}")
    return mapping.ground_truth_hypotheses
