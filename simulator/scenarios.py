"""scenarios.py -- Named parameter presets S1-S5 + NOISE_ONLY (Section 7.2).

Each scenario is a named combination of parameter changes from Section 13.1.
Applying a scenario calls the same ParameterStore API a manual change would --
no separate code path for presets.

Every scenario has a documented mapping to one or more hypotheses (Section 6).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .parameters import ParameterStore


@dataclass(frozen=True)
class ScenarioPreset:
    """A named scenario preset."""

    scenario_id: str
    name: str
    description: str
    parameter_changes: dict[str, Any]  # path -> value


# =====================================================================
# Scenario definitions
# =====================================================================

SCENARIOS: dict[str, ScenarioPreset] = {

    # S1: Speed setpoint raised beyond safe range -> H1
    "S1": ScenarioPreset(
        scenario_id="S1",
        name="Speed setpoint raised beyond safe range",
        description=(
            "target_rpm raised to 1500 (well above rpm_stable_max=1300) "
            "for the current batch. Should cause temperature and vibration "
            "to rise, followed by increased defect rate."
        ),
        parameter_changes={
            "machines.M-04.target_rpm": 1500.0,
        },
    ),

    # S2: Sensor drift/spoofed readings + unauthorized write -> H5, H6
    "S2": ScenarioPreset(
        scenario_id="S2",
        name="Sensor drift + unauthorized setpoint write",
        description=(
            "sensor_drift_rate elevated, unauthorized_write_probability "
            "raised, message_rate_burst_multiplier increased. Should cause "
            "physics-inconsistent signals (high cross-check residual) and "
            "unauthorized write events in the log."
        ),
        parameter_changes={
            "machines.M-04.sensor_drift_rate": 0.5,
            "machines.M-04.unauthorized_write_probability": 0.3,
            "machines.M-04.message_rate_burst_multiplier": 3.0,
        },
    ),

    # S3: Coolant flow drops -> H3
    "S3": ScenarioPreset(
        scenario_id="S3",
        name="Coolant flow drops",
        description=(
            "coolant_flow_lpm reduced from 12 to 3. Should cause "
            "temperature to rise significantly, leading to defects."
        ),
        parameter_changes={
            "machines.M-04.coolant_flow_lpm": 3.0,
        },
    ),

    # S4: Gradual bearing wear -> H2
    "S4": ScenarioPreset(
        scenario_id="S4",
        name="Gradual bearing wear",
        description=(
            "bearing_wear_rate raised to 0.005 (50x default). Should cause "
            "vibration to gradually increase over many ticks, eventually "
            "raising motor current and temperature slightly."
        ),
        parameter_changes={
            "machines.M-04.bearing_wear_rate": 0.005,
        },
    ),

    # S5: Bad material batch swapped in -> H4
    "S5": ScenarioPreset(
        scenario_id="S5",
        name="Bad material batch swapped in",
        description=(
            "Switch to BATCH-BAD (hardness_deviation=2.5, "
            "material_sensitivity=2.0). Should raise defect rate even "
            "at normal RPM, and amplify defects if RPM is near the safe limit."
        ),
        parameter_changes={
            "lines.L-03.active_material_batch_id": "BATCH-BAD",
        },
    ),

    
    # S6: Complex Multi-Factor Degradation
    "S6": ScenarioPreset(
        scenario_id="S6",
        name="Multi-Factor System Degradation",
        description=(
            "Simulates a complex failure involving variations in pressure, "
            "reduced coolant (raises temperature), increased wear (raises vibration), "
            "and excessive RPM. Leads to significant machine failure and low production yield."
        ),
        parameter_changes={
            "machines.M-04.target_rpm": 1450.0,
            "machines.M-04.pressure_bar": 15.0,  # Elevated pressure
            "machines.M-04.coolant_flow_lpm": 5.0, # Reduced coolant -> high temp
            "machines.M-04.bearing_wear_rate": 0.003, # Fast wear -> high vibration
            "lines.L-03.active_material_batch_id": "BATCH-BAD", # Low yield
        },
    ),

    # NOISE_ONLY

    "NOISE_ONLY": ScenarioPreset(
        scenario_id="NOISE_ONLY",
        name="Noise-only negative test",
        description=(
            "Only sensor_noise_multiplier raised to 5.0. No physical fault. "
            "Should produce noisier readings but no consistent causal chain. "
            "The system should NOT confidently pick H1-H6."
        ),
        parameter_changes={
            "machines.M-04.sensor_noise_multiplier": 5.0,
        },
    ),
}


def apply_scenario(store: ParameterStore, scenario_id: str) -> list:
    """Apply a named scenario preset via the standard parameter API.

    Returns the list of ParameterChange objects logged.
    Raises ValueError if the scenario_id is unknown.
    """
    preset = SCENARIOS.get(scenario_id)
    if preset is None:
        raise ValueError(
            f"Unknown scenario '{scenario_id}'. "
            f"Available: {list(SCENARIOS.keys())}"
        )
    return store.batch_set(
        preset.parameter_changes,
        source=f"scenario:{scenario_id}",
    )


def get_scenario(scenario_id: str) -> ScenarioPreset:
    """Look up a scenario by ID."""
    preset = SCENARIOS.get(scenario_id)
    if preset is None:
        raise ValueError(f"Unknown scenario '{scenario_id}'.")
    return preset


def list_scenarios() -> list[ScenarioPreset]:
    """Return all available scenario presets."""
    return list(SCENARIOS.values())
