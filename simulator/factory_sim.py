"""factory_sim.py -- The always-on digital twin process.

Line 03 with machine M-04, a cooling unit, conveyor, and inspection station.
One continuous simulation: not pre-recorded data, not a one-off script.

The twin:
  - Ticks at a configurable rate (Section 11: 1 tick = 1 sim-second)
  - Applies causal physics every tick (Section 7.1)
  - Uses deterministic per-tick noise (Section 7.3)
  - Takes periodic snapshots (Section 7.3)
  - Logs every parameter change (Section 13.2)
  - Reacts to parameter changes immediately

This module can run standalone (for testing) or be driven tick-by-tick
by the backend server.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from .parameters import (
    MachineParams,
    ParameterState,
    ParameterStore,
)
from .physics import (
    LineState,
    MachineState,
    NetworkState,
    TickRNG,
    step_energy,
    step_machine,
    step_network,
    step_quality,
)
from .snapshot import SnapshotManager, TwinSnapshot


# Machine-to-line mapping
MACHINE_LINE_MAP: dict[str, str] = {
    "M-04": "L-03",
}


class FactoryTwin:
    """The digital twin: always-on, parameter-reactive, deterministic.

    Usage:
        twin = FactoryTwin()
        twin.start()             # starts the background tick loop
        twin.params.set(...)     # parameter changes take effect next tick
        snap = twin.get_state()  # read current state
        twin.stop()

    Or drive manually:
        twin = FactoryTwin(auto_run=False)
        for _ in range(100):
            twin.tick()
    """

    def __init__(
        self,
        params: Optional[ParameterStore] = None,
        snapshot_interval: int = 30,
        on_tick: Optional[Callable[["FactoryTwin"], None]] = None,
    ):
        # Parameter store
        self.params = params or ParameterStore()

        # Internal state
        self._machine_states: dict[str, MachineState] = {}
        self._line_states: dict[str, LineState] = {}
        self._network_states: dict[str, NetworkState] = {}

        # Initialize machines and lines from the parameter state
        ps = self.params.get_state()
        for mid in ps.machines:
            self._machine_states[mid] = MachineState(mid)
            self._network_states[mid] = NetworkState(mid)
        for lid in ps.lines:
            self._line_states[lid] = LineState(lid)

        # Tick counter and sim clock
        self._tick_index: int = 0
        self._sim_time_s: float = 0.0

        # Snapshot manager (Section 7.3)
        self._snapshots = SnapshotManager(
            interval=snapshot_interval, max_snapshots=200,
        )

        # Callback after each tick (for pushing telemetry)
        self._on_tick = on_tick

        # Background loop control
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    # ── Properties ──────────────────────────────────────────────────

    @property
    def tick_index(self) -> int:
        return self._tick_index

    @property
    def sim_time_s(self) -> float:
        return self._sim_time_s

    @property
    def snapshots(self) -> SnapshotManager:
        return self._snapshots

    # ── Core tick ───────────────────────────────────────────────────

    def tick(self) -> dict[str, Any]:
        """Advance the simulation by one tick.

        Returns a dict with the current state of all machines, lines,
        and network for this tick (the telemetry payload).
        """
        with self._lock:
            ps = self.params.get_state()
            g = ps.globals
            self.params.set_tick(self._tick_index)

            # Deterministic per-tick RNG (Section 7.3)
            rng = TickRNG(g.base_seed, self._tick_index)

            # Step each machine
            for mid, ms in self._machine_states.items():
                mp = ps.machines.get(mid, MachineParams())
                step_machine(ms, mp, g, rng)

            # Apply manual overrides if set (e.g. from mobile digital twin controller)
            if hasattr(self, "_manual_overrides") and self._manual_overrides:
                for (ov_mid, ov_param), ov_val in self._manual_overrides.items():
                    target_ms = self._machine_states.get(ov_mid)
                    if not target_ms and ov_mid in ("processing_unit", "all"):
                        target_ms = self._machine_states.get("M-04")
                    if target_ms:
                        if ov_param in ("vibration", "vibration_mm_s"):
                            target_ms.vibration_mm_s = float(ov_val)
                            target_ms.bearing_wear = min(1.0, max(target_ms.bearing_wear, float(ov_val) / 8.0))
                        elif ov_param in ("temperature", "temperature_c"):
                            target_ms.temperature_c = float(ov_val)
                        elif ov_param in ("rpm", "target_rpm"):
                            target_ms.rpm = float(ov_val)
                        elif ov_param in ("pressure", "pressure_bar"):
                            target_ms.pressure_bar = float(ov_val)

            # Step each line (quality + energy)
            for lid, ls in self._line_states.items():
                # Find machines on this line
                line_machines = [
                    self._machine_states[mid]
                    for mid, mapped_lid in MACHINE_LINE_MAP.items()
                    if mapped_lid == lid and mid in self._machine_states
                ]
                step_quality(ls, line_machines, ps, g, rng)
                step_energy(ls, line_machines, g, rng)

            # Step network for each machine
            for mid, ns in self._network_states.items():
                ms = self._machine_states[mid]
                mp = ps.machines.get(mid, MachineParams())
                step_network(ns, ms, mp, g, rng)

            # Periodic snapshot (Section 7.3)
            if self._snapshots.should_snapshot(self._tick_index):
                self._snapshots.capture(
                    tick_index=self._tick_index,
                    sim_time_s=self._sim_time_s,
                    machine_states=self._machine_states,
                    line_states=self._line_states,
                    network_states=self._network_states,
                    parameter_state=ps,
                    base_seed=g.base_seed,
                )

            # Build telemetry payload
            payload = self._build_payload()

            # Advance counters
            self._tick_index += 1
            self._sim_time_s += 1.0  # 1 tick = 1 sim-second (Section 11)

        # Fire callback outside the lock
        if self._on_tick:
            self._on_tick(self)

        return payload

    def _build_payload(self) -> dict[str, Any]:
        """Build the telemetry payload for the current tick."""
        return {
            "tick_index": self._tick_index,
            "sim_time_s": self._sim_time_s,
            "wall_time": datetime.now(timezone.utc).isoformat(),
            "machines": {
                mid: ms.to_dict() for mid, ms in self._machine_states.items()
            },
            "lines": {
                lid: ls.to_dict() for lid, ls in self._line_states.items()
            },
            "network": {
                mid: ns.to_dict() for mid, ns in self._network_states.items()
            },
        }

    # ── State access ────────────────────────────────────────────────

    def take_snapshot(self, tag: str = ""):
        with self._lock:
            return self._snapshots.capture(
                tick_index=self._tick_index,
                sim_time_s=self._sim_time_s,
                machine_states=self._machine_states,
                line_states=self._line_states,
                network_states=self._network_states,
                parameter_state=self.params.get_state(),
                base_seed=self.params.get_state().globals.base_seed,
            )

    def get_state(self) -> dict[str, Any]:
        """Thread-safe snapshot of the current simulation state."""
        with self._lock:
            return self._build_payload()

    def get_machine_state(self, machine_id: str) -> Optional[MachineState]:
        return self._machine_states.get(machine_id)

    def get_line_state(self, line_id: str) -> Optional[LineState]:
        return self._line_states.get(line_id)

    # ── Restore from snapshot (for replay) ──────────────────────────

    def restore_from_snapshot(self, snap: TwinSnapshot) -> None:
        """Restore the twin to a previous snapshot state.

        Used by the counterfactual replay engine (Section 10.2).
        """
        with self._lock:
            self._tick_index = snap.tick_index
            self._sim_time_s = snap.sim_time_s

            for mid, ms_dict in snap.machine_states.items():
                self._machine_states[mid] = MachineState.from_dict(ms_dict)
            for lid, ls_dict in snap.line_states.items():
                self._line_states[lid] = LineState.from_dict(ls_dict)
            for mid, ns_dict in snap.network_states.items():
                self._network_states[mid] = NetworkState.from_dict(ns_dict)

            self.params.restore(snap.get_parameter_state())

    # ── Background loop ─────────────────────────────────────────────

    def start(self) -> None:
        """Start the background tick loop."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the background tick loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _run_loop(self) -> None:
        """Main simulation loop — runs at configured ticks_per_second."""
        while self._running:
            tps = self.params.get_state().globals.ticks_per_second
            start = time.monotonic()
            self.tick()
            elapsed = time.monotonic() - start
            sleep_time = max(0.0, (1.0 / tps) - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

    @property
    def is_running(self) -> bool:
        return self._running
