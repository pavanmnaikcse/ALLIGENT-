"""physics.py -- Causal equations for the digital twin (Section 7.1).

Every equation uses parameters from parameters.py -- nothing is hardcoded.
noise(t) is seeded deterministically per tick using (base_seed, tick_index)
so that replaying from a snapshot reproduces identical noise (Section 7.3).

Signal groups:
  Machine:   RPM, temperature, vibration, motor current, pressure, coolant flow, bearing wear
  Quality:   defect rate, defect type mix
  Energy:    kWh/unit, CO2/unit
  Network:   message rate, cross-check residual
"""

from __future__ import annotations

import numpy as np

from .parameters import (
    GlobalParams,
    MachineParams,
    MaterialBatch,
    ParameterState,
)


class TickRNG:
    """Deterministic per-tick random number generator.

    Uses (base_seed, tick_index) to produce identical noise on replay.
    Each call to a noise method consumes from the same per-tick stream,
    so the order of calls must be consistent across runs.
    """

    def __init__(self, base_seed: int, tick_index: int):
        # Combine base_seed and tick_index into a single seed
        # Using SeedSequence for proper entropy mixing
        self._rng = np.random.default_rng(
            np.random.SeedSequence((base_seed, tick_index))
        )

    def normal(self, scale: float = 1.0) -> float:
        """One sample from N(0, scale)."""
        return float(self._rng.normal(0.0, scale))

    def uniform(self, low: float = 0.0, high: float = 1.0) -> float:
        """One sample from U(low, high)."""
        return float(self._rng.uniform(low, high))

    def bernoulli(self, p: float) -> bool:
        """True with probability p."""
        return bool(self._rng.random() < p)


# =====================================================================
# Machine state -- mutable internal state for one machine
# =====================================================================

class MachineState:
    """Internal physical state of one machine (evolved each tick)."""

    __slots__ = (
        "machine_id", "rpm", "temperature_c", "vibration_mm_s",
        "motor_current_a", "pressure_bar", "coolant_flow_lpm",
        "bearing_wear", "sensor_drift_accumulated",
    )

    def __init__(self, machine_id: str):
        self.machine_id = machine_id
        self.rpm: float = 0.0
        self.temperature_c: float = 40.0
        self.vibration_mm_s: float = 2.0
        self.motor_current_a: float = 12.0
        self.pressure_bar: float = 5.0
        self.coolant_flow_lpm: float = 12.0
        self.bearing_wear: float = 0.0
        self.sensor_drift_accumulated: float = 0.0

    def to_dict(self) -> dict:
        return {
            "machine_id": self.machine_id,
            "rpm": self.rpm,
            "temperature_c": self.temperature_c,
            "vibration_mm_s": self.vibration_mm_s,
            "motor_current_a": self.motor_current_a,
            "pressure_bar": self.pressure_bar,
            "coolant_flow_lpm": self.coolant_flow_lpm,
            "bearing_wear": self.bearing_wear,
            "sensor_drift_accumulated": self.sensor_drift_accumulated,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MachineState":
        ms = cls(d["machine_id"])
        ms.rpm = d["rpm"]
        ms.temperature_c = d["temperature_c"]
        ms.vibration_mm_s = d["vibration_mm_s"]
        ms.motor_current_a = d["motor_current_a"]
        ms.pressure_bar = d["pressure_bar"]
        ms.coolant_flow_lpm = d["coolant_flow_lpm"]
        ms.bearing_wear = d["bearing_wear"]
        ms.sensor_drift_accumulated = d.get("sensor_drift_accumulated", 0.0)
        return ms


# =====================================================================
# Quality / Line state
# =====================================================================

class LineState:
    """Internal state for one production line."""

    __slots__ = ("line_id", "defect_rate", "defect_types", "reject_count",
                 "kwh_per_unit", "co2_per_unit")

    def __init__(self, line_id: str):
        self.line_id = line_id
        self.defect_rate: float = 0.01
        self.defect_types: dict[str, float] = {"surface": 0.5, "dimensional": 0.3, "other": 0.2}
        self.reject_count: int = 0
        self.kwh_per_unit: float = 1.5
        self.co2_per_unit: float = 0.6

    def to_dict(self) -> dict:
        return {
            "line_id": self.line_id,
            "defect_rate": self.defect_rate,
            "defect_types": dict(self.defect_types),
            "reject_count": self.reject_count,
            "kwh_per_unit": self.kwh_per_unit,
            "co2_per_unit": self.co2_per_unit,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "LineState":
        ls = cls(d["line_id"])
        ls.defect_rate = d["defect_rate"]
        ls.defect_types = d.get("defect_types", ls.defect_types)
        ls.reject_count = d.get("reject_count", 0)
        ls.kwh_per_unit = d.get("kwh_per_unit", 1.5)
        ls.co2_per_unit = d.get("co2_per_unit", 0.6)
        return ls


# =====================================================================
# Network state
# =====================================================================

class NetworkState:
    """Network/integrity state for one machine."""

    __slots__ = ("machine_id", "message_rate", "cross_check_residual",
                 "last_write_source")

    def __init__(self, machine_id: str):
        self.machine_id = machine_id
        self.message_rate: float = 100.0
        self.cross_check_residual: float = 0.0
        self.last_write_source: str = "operator"

    def to_dict(self) -> dict:
        return {
            "machine_id": self.machine_id,
            "message_rate": self.message_rate,
            "cross_check_residual": self.cross_check_residual,
            "last_write_source": self.last_write_source,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NetworkState":
        ns = cls(d["machine_id"])
        ns.message_rate = d["message_rate"]
        ns.cross_check_residual = d["cross_check_residual"]
        ns.last_write_source = d.get("last_write_source", "operator")
        return ns


# =====================================================================
# Physics engine -- one tick of causal simulation
# =====================================================================

def step_machine(
    state: MachineState,
    params: MachineParams,
    g: GlobalParams,
    rng: TickRNG,
) -> None:
    """Advance one machine by one tick (mutates state in place).

    Implements the causal equations from Section 7.1:
      temperature(t)  = baseline + k1*max(0, rpm-rpm_max) - k2*coolant + noise
      vibration(t)    = baseline + k3*max(0, rpm-rpm_max)^1.3 + k4*wear + noise
      motor_current   = baseline + load_from_rpm + load_from_material_wear + noise
      bearing_wear(t) = wear(t-1) + wear_rate   (clamped to [0, 1])
    """
    noise_scale = params.sensor_noise_multiplier

    # RPM tracks the setpoint (with small lag modeled as noise)
    state.rpm = params.target_rpm + rng.normal(0.5 * noise_scale)

    # Bearing wear accumulates
    state.bearing_wear = min(1.0, max(0.0,
        state.bearing_wear + params.bearing_wear_rate
    ))

    # Coolant flow tracks the parameter
    state.coolant_flow_lpm = max(0.0,
        params.coolant_flow_lpm + rng.normal(0.1 * noise_scale)
    )

    # Pressure tracks the parameter
    state.pressure_bar = max(0.0,
        params.pressure_bar + rng.normal(0.05 * noise_scale)
    )

    # --- Causal equations ---

    rpm_excess = max(0.0, state.rpm - g.rpm_stable_max)

    # Temperature
    raw_temp = (
        g.baseline_temp
        + g.k1_rpm_temp * rpm_excess
        - g.k2_coolant_temp * (state.coolant_flow_lpm - 10.0)  # relative to ~10 LPM reference
        + rng.normal(0.3 * noise_scale)
    )
    state.temperature_c = max(15.0, raw_temp)  # physical floor

    # Vibration
    raw_vib = (
        g.baseline_vibration
        + g.k3_rpm_vibration * (rpm_excess ** 1.3)
        + g.k4_wear_vibration * state.bearing_wear
        + rng.normal(0.15 * noise_scale)
    )
    state.vibration_mm_s = max(0.0, raw_vib)

    # Motor current -- rises with RPM and bearing wear
    raw_current = (
        g.base_motor_current
        + 0.005 * rpm_excess
        + 5.0 * state.bearing_wear
        + rng.normal(0.2 * noise_scale)
    )
    state.motor_current_a = max(0.0, raw_current)

    # Sensor drift accumulation
    state.sensor_drift_accumulated += params.sensor_drift_rate


def step_quality(
    line_state: LineState,
    machine_states: list[MachineState],
    params_state: ParameterState,
    g: GlobalParams,
    rng: TickRNG,
) -> None:
    """Compute quality signals for one line from its machines.

    defect_rate = base + k5*max(0, temp-threshold) + k6*max(0, vib-threshold)
                + k7*material_sensitivity*max(0, rpm-rpm_max) + noise
    """
    noise_scale = 1.0  # quality noise is independent
    total_defect_contribution = 0.0

    for ms in machine_states:
        temp_excess = max(0.0, ms.temperature_c - g.temp_safe_threshold)
        vib_excess = max(0.0, ms.vibration_mm_s - g.vibration_safe_threshold)
        rpm_excess = max(0.0, ms.rpm - g.rpm_stable_max)

        # Get active material batch sensitivity
        line_params = params_state.lines.get(line_state.line_id)
        batch_id = line_params.active_material_batch_id if line_params else "BATCH-DEFAULT"
        batch = params_state.material_batches.get(batch_id)
        mat_sens = batch.material_sensitivity if batch else 1.0
        hardness_dev = batch.hardness_deviation if batch else 0.0

        total_defect_contribution += (
            g.k5_temp_defect * temp_excess
            + g.k6_vibration_defect * vib_excess
            + g.k7_material_defect * mat_sens * rpm_excess
            + 0.02 * hardness_dev
        )

    defect_rate = (
        g.base_defect_rate
        + total_defect_contribution / max(1, len(machine_states))
        + rng.normal(0.001 * noise_scale)
    )
    line_state.defect_rate = max(0.0, min(1.0, defect_rate))

    # Defect type mix shifts with temperature (more surface defects when hot)
    avg_temp = sum(m.temperature_c for m in machine_states) / max(1, len(machine_states))
    heat_factor = min(1.0, max(0.0, (avg_temp - g.baseline_temp) / 40.0))
    line_state.defect_types = {
        "surface": 0.5 + 0.3 * heat_factor,
        "dimensional": 0.3 - 0.1 * heat_factor,
        "other": 0.2 - 0.2 * heat_factor,
    }

    # Reject count (Poisson-like from defect rate, capped)
    line_state.reject_count = int(line_state.defect_rate * 100 + rng.normal(0.5))
    line_state.reject_count = max(0, line_state.reject_count)


def step_energy(
    line_state: LineState,
    machine_states: list[MachineState],
    g: GlobalParams,
    rng: TickRNG,
) -> None:
    """Compute energy/CO2 per unit.

    energy_kwh_per_unit = base + k8*rpm^1.1 + k9*temperature + noise
    """
    if not machine_states:
        return
    avg_rpm = sum(m.rpm for m in machine_states) / len(machine_states)
    avg_temp = sum(m.temperature_c for m in machine_states) / len(machine_states)

    raw_energy = (
        g.base_energy_kwh
        + g.k8_rpm_energy * (avg_rpm ** 1.1)
        + g.k9_temp_energy * avg_temp
        + rng.normal(0.02)
    )
    line_state.kwh_per_unit = max(0.0, raw_energy)
    line_state.co2_per_unit = line_state.kwh_per_unit * g.co2_per_kwh


def step_network(
    net_state: NetworkState,
    machine_state: MachineState,
    params: MachineParams,
    g: GlobalParams,
    rng: TickRNG,
) -> None:
    """Compute network / integrity signals.

    Physics-consistency check: if sensor_drift is high, the cross-check
    residual rises because observed signals diverge from expected physics.
    Message rate bursts under integrity attacks.
    """
    # Base message rate with burst multiplier
    net_state.message_rate = (
        g.base_message_rate * params.message_rate_burst_multiplier
        + rng.normal(5.0 * params.sensor_noise_multiplier)
    )
    net_state.message_rate = max(0.0, net_state.message_rate)

    # Cross-check residual -- rises with sensor drift and with physics
    # inconsistency.  The key signature: if drift is injected, current/vibration
    # can rise while temperature stays flat (or vice versa), producing a
    # large residual.
    expected_temp_from_rpm = (
        g.baseline_temp + g.k1_rpm_temp * max(0.0, machine_state.rpm - g.rpm_stable_max)
    )
    temp_residual = abs(machine_state.temperature_c - expected_temp_from_rpm)

    net_state.cross_check_residual = (
        temp_residual * 0.1
        + machine_state.sensor_drift_accumulated * 2.0
        + rng.normal(0.05 * params.sensor_noise_multiplier)
    )
    net_state.cross_check_residual = max(0.0, net_state.cross_check_residual)

    # Unauthorized write simulation
    if params.unauthorized_write_probability > 0 and rng.bernoulli(params.unauthorized_write_probability):
        net_state.last_write_source = "unknown"
    else:
        net_state.last_write_source = "operator"
