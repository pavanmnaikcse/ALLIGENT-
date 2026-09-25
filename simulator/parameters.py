"""parameters.py -- Single source of truth for every adjustable value.

Every constant, threshold, and setpoint the twin uses lives here.
Nothing is hardcoded elsewhere.  The ParameterStore manages current values,
baseline values, a full change-log with timestamps, and supports atomic
batch updates, reset, and scenario application (all via the same code path).

Categories (Section 13.1):
  A. Process/setpoints (per machine)
  B. Degradation/condition (per machine)
  C. Material (per line)
  D. Integrity (global/per-machine)
  E. Environment/thresholds (global)
  F. Simulation
"""

from __future__ import annotations

import copy
import threading
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


# =====================================================================
# Material batch definitions
# =====================================================================

class MaterialBatch(BaseModel):
    """Properties of one material batch."""
    batch_id: str
    supplier: str = "SupplierA"
    hardness_deviation: float = 0.0
    material_sensitivity: float = 1.0


# =====================================================================
# Machine-level parameters
# =====================================================================

class MachineParams(BaseModel):
    """All adjustable parameters for one machine."""

    # A. Process / setpoints
    target_rpm: float = Field(default=1200.0, description="RPM setpoint.")
    coolant_flow_lpm: float = Field(default=12.0, description="Coolant flow (L/min).")
    pressure_bar: float = Field(default=5.0, description="Process pressure (bar).")
    feed_rate: float = Field(default=50.0, description="Feed rate (units/min).")

    # B. Degradation / condition
    bearing_wear_rate: float = Field(
        default=0.0001, description="Bearing wear increment per tick (0=no degradation)."
    )
    sensor_noise_multiplier: float = Field(
        default=1.0, description="Multiplier on all sensor noise (1.0 = nominal)."
    )

    # D. Integrity (per-machine overrides)
    sensor_drift_rate: float = Field(
        default=0.0, description="Drift added to sensors per tick."
    )
    unauthorized_write_probability: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Probability per tick of an unauthorized setpoint write.",
    )
    message_rate_burst_multiplier: float = Field(
        default=1.0, ge=1.0,
        description="Multiplier on network message rate (1.0 = normal).",
    )


# =====================================================================
# Line-level parameters
# =====================================================================

class LineParams(BaseModel):
    """Parameters for one production line."""

    # C. Material
    active_material_batch_id: str = Field(
        default="BATCH-DEFAULT", description="Currently active batch ID."
    )


# =====================================================================
# Global parameters
# =====================================================================

class GlobalParams(BaseModel):
    """Environment thresholds and simulation settings."""

    # E. Environment / thresholds
    rpm_stable_max: float = Field(
        default=1300.0, description="Max RPM before thermal/vibration rise."
    )
    temp_safe_threshold: float = Field(
        default=75.0, description="Temperature (C) above which defect rate rises."
    )
    vibration_safe_threshold: float = Field(
        default=7.0, description="Vibration (mm/s) above which defect rate rises."
    )
    anomaly_sensitivity: float = Field(
        default=0.05, description="IsolationForest contamination parameter."
    )
    changepoint_threshold: float = Field(
        default=5.0, description="CUSUM threshold for change-point detection."
    )
    case_cooldown_ticks: int = Field(
        default=60, description="Cooldown ticks before a new case on the same machine."
    )

    # F. Simulation
    ticks_per_second: float = Field(
        default=20.0,
        description=(
            "How many sim ticks run per real second.  1 tick = 1 sim-second, "
            "so 20 tps = 20x real-time speed.  Adjustable 1-100."
        ),
    )
    base_seed: int = Field(
        default=42, description="Base RNG seed for deterministic per-tick noise."
    )

    # Physics constants -- Section 7.1
    k1_rpm_temp: float = Field(default=0.015, description="RPM excess -> temperature.")
    k2_coolant_temp: float = Field(default=0.8, description="Coolant flow -> temperature reduction.")
    k3_rpm_vibration: float = Field(default=0.004, description="RPM excess -> vibration.")
    k4_wear_vibration: float = Field(default=15.0, description="Bearing wear -> vibration.")
    k5_temp_defect: float = Field(default=0.003, description="Excess temperature -> defect rate.")
    k6_vibration_defect: float = Field(default=0.005, description="Excess vibration -> defect rate.")
    k7_material_defect: float = Field(default=0.002, description="Material sensitivity * RPM excess -> defect rate.")
    k8_rpm_energy: float = Field(default=0.0008, description="RPM -> energy per unit.")
    k9_temp_energy: float = Field(default=0.005, description="Temperature -> energy per unit.")
    co2_per_kwh: float = Field(default=0.4, description="kg CO2 per kWh.")

    # Baselines
    baseline_temp: float = Field(default=40.0, description="Baseline temperature (C).")
    baseline_vibration: float = Field(default=2.0, description="Baseline vibration (mm/s).")
    base_defect_rate: float = Field(default=0.01, description="Baseline defect rate.")
    base_energy_kwh: float = Field(default=1.5, description="Baseline energy per unit (kWh).")
    base_message_rate: float = Field(default=100.0, description="Baseline network messages/sec.")
    base_motor_current: float = Field(default=12.0, description="Baseline motor current (A).")

    # Confidence gating (Section 10.3)
    confidence_threshold: float = Field(
        default=0.4,
        description="Below this, case is routed to human review.",
    )
    data_trust_threshold: float = Field(
        default=0.5,
        description="Below this, case is flagged as low-trust.",
    )


# =====================================================================
# Full parameter state
# =====================================================================

class ParameterState(BaseModel):
    """Complete parameter state for the entire factory."""

    machines: dict[str, MachineParams] = Field(default_factory=dict)
    lines: dict[str, LineParams] = Field(default_factory=dict)
    material_batches: dict[str, MaterialBatch] = Field(default_factory=dict)
    globals: GlobalParams = Field(default_factory=GlobalParams)


# =====================================================================
# Parameter change log entry
# =====================================================================

class ParameterChange(BaseModel):
    """One entry in the parameter change audit log."""

    timestamp: datetime
    tick_index: int
    path: str              # e.g. "machines.M-04.target_rpm"
    old_value: Any
    new_value: Any
    source: str            # "operator", "scenario:S1", "api", "reset", etc.


# =====================================================================
# ParameterStore -- runtime manager
# =====================================================================

class ParameterStore:
    """Thread-safe runtime parameter manager.

    Provides:
    - get/set individual parameters by dotted path
    - atomic batch updates
    - full change history (Section 7.3 / 13.2)
    - reset to baseline
    - deep-copy snapshots for replay
    """

    def __init__(self, initial: Optional[ParameterState] = None):
        self._lock = threading.Lock()
        if initial is None:
            initial = self._make_default()
        self._state = initial.model_copy(deep=True)
        self._baseline = initial.model_copy(deep=True)
        self._history: list[ParameterChange] = []
        self._tick_index: int = 0

    # ── Factory default ─────────────────────────────────────────────

    @staticmethod
    def _make_default() -> ParameterState:
        """Construct the factory's default parameter state."""
        return ParameterState(
            machines={
                "M-04": MachineParams(),
            },
            lines={
                "L-03": LineParams(),
            },
            material_batches={
                "BATCH-DEFAULT": MaterialBatch(
                    batch_id="BATCH-DEFAULT", supplier="SupplierA",
                    hardness_deviation=0.0, material_sensitivity=1.0,
                ),
                "BATCH-BAD": MaterialBatch(
                    batch_id="BATCH-BAD", supplier="SupplierB",
                    hardness_deviation=2.5, material_sensitivity=2.0,
                ),
            },
            globals=GlobalParams(),
        )

    # ── Tick tracking ───────────────────────────────────────────────

    def set_tick(self, tick: int) -> None:
        self._tick_index = tick

    @property
    def tick_index(self) -> int:
        return self._tick_index

    # ── Read ────────────────────────────────────────────────────────

    def snapshot(self) -> ParameterState:
        """Return a deep copy of the current state (for replay)."""
        with self._lock:
            return self._state.model_copy(deep=True)

    def get_state(self) -> ParameterState:
        """Return a reference to the current state (for fast reads inside the sim loop)."""
        return self._state

    def get(self, path: str) -> Any:
        """Get a parameter value by dotted path, e.g. 'machines.M-04.target_rpm'."""
        with self._lock:
            return self._resolve_path(self._state, path)

    def get_baseline(self, path: str) -> Any:
        """Get the baseline value for comparison."""
        return self._resolve_path(self._baseline, path)

    # ── Write ───────────────────────────────────────────────────────

    def set(self, path: str, value: Any, source: str = "api") -> ParameterChange:
        """Set one parameter and log the change."""
        with self._lock:
            old = self._resolve_path(self._state, path)
            self._set_path(self._state, path, value)
            change = ParameterChange(
                timestamp=datetime.now(timezone.utc),
                tick_index=self._tick_index,
                path=path,
                old_value=old,
                new_value=value,
                source=source,
            )
            self._history.append(change)
            return change

    def batch_set(self, changes: dict[str, Any], source: str = "api") -> list[ParameterChange]:
        """Apply multiple changes atomically."""
        with self._lock:
            results = []
            for path, value in changes.items():
                old = self._resolve_path(self._state, path)
                self._set_path(self._state, path, value)
                change = ParameterChange(
                    timestamp=datetime.now(timezone.utc),
                    tick_index=self._tick_index,
                    path=path, old_value=old, new_value=value,
                    source=source,
                )
                self._history.append(change)
                results.append(change)
            return results

    def reset(self) -> list[ParameterChange]:
        """Reset all parameters to baseline, logging each change."""
        with self._lock:
            changes = []
            # Compute diffs and log them
            current_dict = self._state.model_dump()
            baseline_dict = self._baseline.model_dump()
            diffs = self._diff_dicts(current_dict, baseline_dict, "")
            for path, (old, new) in diffs.items():
                change = ParameterChange(
                    timestamp=datetime.now(timezone.utc),
                    tick_index=self._tick_index,
                    path=path, old_value=old, new_value=new,
                    source="reset",
                )
                self._history.append(change)
                changes.append(change)
            self._state = self._baseline.model_copy(deep=True)
            return changes

    # ── History ─────────────────────────────────────────────────────

    @property
    def history(self) -> list[ParameterChange]:
        """Full parameter change log (Section 7.3 / 13.2)."""
        return list(self._history)

    def history_since(self, tick: int) -> list[ParameterChange]:
        """Changes since a given tick (inclusive)."""
        return [c for c in self._history if c.tick_index >= tick]

    # ── Restore from snapshot (for replay) ──────────────────────────

    def restore(self, state: ParameterState) -> None:
        """Replace current state with a snapshot (used by replay engine)."""
        with self._lock:
            self._state = state.model_copy(deep=True)

    # ── Path resolution ─────────────────────────────────────────────

    @staticmethod
    def _resolve_path(obj: Any, path: str) -> Any:
        """Resolve 'machines.M-04.target_rpm' to the actual value."""
        parts = path.split(".")
        current = obj
        for part in parts:
            if isinstance(current, BaseModel):
                current = getattr(current, part, None)
                if current is None:
                    # Try dict-like access on model fields that are dicts
                    raise KeyError(f"Path segment '{part}' not found on {type(current)}")
            elif isinstance(current, dict):
                if part not in current:
                    raise KeyError(f"Key '{part}' not found in dict at path")
                current = current[part]
            else:
                raise KeyError(f"Cannot traverse into {type(current)} at '{part}'")
        return current

    @staticmethod
    def _set_path(obj: Any, path: str, value: Any) -> None:
        """Set a value at a dotted path."""
        parts = path.split(".")
        current = obj
        for part in parts[:-1]:
            if isinstance(current, BaseModel):
                next_val = getattr(current, part, None)
                if next_val is None:
                    raise KeyError(f"Path segment '{part}' not found")
                current = next_val
            elif isinstance(current, dict):
                if part not in current:
                    raise KeyError(f"Key '{part}' not found in dict")
                current = current[part]
            else:
                raise KeyError(f"Cannot traverse into {type(current)}")

        last = parts[-1]
        if isinstance(current, BaseModel):
            if not hasattr(current, last):
                raise KeyError(f"Field '{last}' not found on {type(current)}")
            setattr(current, last, value)
        elif isinstance(current, dict):
            current[last] = value
        else:
            raise KeyError(f"Cannot set on {type(current)}")

    @staticmethod
    def _diff_dicts(current: dict, baseline: dict, prefix: str) -> dict[str, tuple]:
        """Recursively find differing leaf values between two dicts."""
        diffs = {}
        for key in set(list(current.keys()) + list(baseline.keys())):
            path = f"{prefix}.{key}" if prefix else key
            cv = current.get(key)
            bv = baseline.get(key)
            if isinstance(cv, dict) and isinstance(bv, dict):
                diffs.update(ParameterStore._diff_dicts(cv, bv, path))
            elif cv != bv:
                diffs[path] = (cv, bv)
        return diffs
