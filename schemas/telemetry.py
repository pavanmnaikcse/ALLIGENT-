"""telemetry.py — Exact shape of one tick of machine/line/energy/network data.

Every field is typed, documented, and validated. One TelemetryTick is the
atomic unit of data that the twin emits and the evidence layer consumes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── Machine-level signals ────────────────────────────────────────────

class MachineTelemetry(BaseModel):
    """Sensor readings for a single machine at one tick."""

    machine_id: str = Field(..., description="Unique machine identifier, e.g. 'M-04'.")
    rpm: float = Field(..., ge=0, description="Current rotational speed (rev/min).")
    temperature_c: float = Field(..., description="Surface / bearing temperature (°C).")
    vibration_mm_s: float = Field(..., ge=0, description="Vibration velocity (mm/s RMS).")
    motor_current_a: float = Field(..., ge=0, description="Motor current draw (A).")
    pressure_bar: float = Field(..., ge=0, description="Hydraulic / process pressure (bar).")
    coolant_flow_lpm: float = Field(..., ge=0, description="Coolant flow rate (litres/min).")
    bearing_wear: float = Field(
        ..., ge=0.0, le=1.0,
        description="Normalised bearing wear index 0 (new) → 1 (end-of-life).",
    )


# ── Process-level signals ───────────────────────────────────────────

class SetpointChangeRecord(BaseModel):
    """One entry in the setpoint change audit log."""

    timestamp: datetime
    parameter: str = Field(..., description="Full parameter path, e.g. 'machines.M-04.target_rpm'.")
    old_value: float
    new_value: float
    source: str = Field(
        ...,
        description=(
            "Who/what made the change: 'operator', 'scenario:<id>', "
            "'api', 'unknown' — needed for H6 (unauthorized write)."
        ),
    )


class ProcessTelemetry(BaseModel):
    """Setpoint and control state for a machine at one tick."""

    machine_id: str
    target_rpm: float = Field(..., ge=0, description="Current RPM setpoint.")
    feed_rate: float = Field(..., ge=0, description="Feed rate (units/min).")
    recent_setpoint_changes: list[SetpointChangeRecord] = Field(
        default_factory=list,
        description="Setpoint changes within the current evidence window.",
    )


# ── Material signals ────────────────────────────────────────────────

class MaterialTelemetry(BaseModel):
    """Active material batch information for a line."""

    line_id: str = Field(..., description="Production line, e.g. 'L-03'.")
    batch_id: str = Field(..., description="Active material batch identifier.")
    supplier: str = Field(default="", description="Supplier name/code.")
    hardness_deviation: float = Field(
        default=0.0,
        description="Deviation from nominal hardness (positive = harder).",
    )
    material_sensitivity: float = Field(
        default=1.0, ge=0.0,
        description="Multiplier for how strongly this batch amplifies defects under stress.",
    )


# ── Quality signals ─────────────────────────────────────────────────

class QualityTelemetry(BaseModel):
    """Inspection results at one tick."""

    line_id: str
    defect_rate: float = Field(..., ge=0.0, le=1.0, description="Fraction defective [0,1].")
    defect_type_mix: dict[str, float] = Field(
        default_factory=dict,
        description="Breakdown by defect type, e.g. {'surface': 0.6, 'dimensional': 0.4}.",
    )
    reject_count: int = Field(default=0, ge=0)


# ── Energy signals ──────────────────────────────────────────────────

class EnergyTelemetry(BaseModel):
    """Energy consumption and emissions estimate at one tick."""

    line_id: str
    kwh_per_unit: float = Field(..., ge=0, description="Energy consumed per good unit produced.")
    co2_kg_per_unit: float = Field(..., ge=0, description="Estimated CO₂ per good unit.")


# ── Network / integrity signals ─────────────────────────────────────

class NetworkTelemetry(BaseModel):
    """Network and integrity signals at one tick."""

    machine_id: str
    message_rate: float = Field(..., ge=0, description="OT network messages/sec.")
    sensor_cross_check_residual: float = Field(
        default=0.0,
        description=(
            "Physics-consistency residual: e.g. current/vibration rising while "
            "temperature stays flat produces a high residual → sensor-fault / spoofing."
        ),
    )
    last_setpoint_write_source: Optional[str] = Field(
        default=None,
        description="Source of the most recent setpoint write for integrity checking.",
    )


# ── Full tick ────────────────────────────────────────────────────────

class TelemetryTick(BaseModel):
    """Complete telemetry snapshot for the entire factory at one simulation tick."""

    tick_index: int = Field(..., ge=0)
    sim_time_s: float = Field(..., ge=0, description="Simulated elapsed time (seconds).")
    wall_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    machines: list[MachineTelemetry] = Field(..., min_length=1)
    processes: list[ProcessTelemetry] = Field(..., min_length=1)
    materials: list[MaterialTelemetry] = Field(..., min_length=1)
    quality: list[QualityTelemetry] = Field(..., min_length=1)
    energy: list[EnergyTelemetry] = Field(..., min_length=1)
    network: list[NetworkTelemetry] = Field(..., min_length=1)

    @field_validator("machines", "processes", "network")
    @classmethod
    def _at_least_one(cls, v: list) -> list:
        if len(v) == 0:
            raise ValueError("At least one entry required.")
        return v
