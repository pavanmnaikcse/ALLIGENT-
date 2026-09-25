"""snapshot.py -- Periodic full-state snapshots + restore (Section 7.3).

The twin serializes its complete internal state at a configurable interval
(every N ticks) and keeps recent snapshots in memory.  This is required for
counterfactual replay (Section 10.2): the Verifier agent restores to a
snapshot just before the candidate cause's onset, reverts the parameter,
and re-runs forward with the same per-tick seed.

A snapshot captures:
  - tick_index and sim_time_s
  - All MachineState, LineState, NetworkState
  - The full ParameterState (deep copy)
  - The RNG base_seed (so replay uses the same seed)
"""

from __future__ import annotations

import copy
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

from .physics import LineState, MachineState, NetworkState
from .parameters import ParameterState


@dataclass
class TwinSnapshot:
    """Complete internal state of the twin at one point in time."""

    tick_index: int
    sim_time_s: float
    machine_states: dict[str, dict]   # machine_id -> MachineState.to_dict()
    line_states: dict[str, dict]      # line_id -> LineState.to_dict()
    network_states: dict[str, dict]   # machine_id -> NetworkState.to_dict()
    parameter_state: dict             # ParameterState.model_dump()
    base_seed: int

    def get_machine_state(self, machine_id: str) -> MachineState:
        return MachineState.from_dict(self.machine_states[machine_id])

    def get_line_state(self, line_id: str) -> LineState:
        return LineState.from_dict(self.line_states[line_id])

    def get_network_state(self, machine_id: str) -> NetworkState:
        return NetworkState.from_dict(self.network_states[machine_id])

    def get_parameter_state(self) -> ParameterState:
        return ParameterState.model_validate(self.parameter_state)


class SnapshotManager:
    """Manages periodic snapshots of the twin's internal state.

    Keeps up to `max_snapshots` most recent snapshots in memory.
    The default interval is every 30 ticks (~30 sim-seconds).
    """

    def __init__(self, interval: int = 30, max_snapshots: int = 100):
        self.interval = interval
        self._snapshots: deque[TwinSnapshot] = deque(maxlen=max_snapshots)

    def should_snapshot(self, tick_index: int) -> bool:
        """Check if a snapshot should be taken at this tick."""
        return tick_index % self.interval == 0

    def capture(
        self,
        tick_index: int,
        sim_time_s: float,
        machine_states: dict[str, MachineState],
        line_states: dict[str, LineState],
        network_states: dict[str, NetworkState],
        parameter_state: ParameterState,
        base_seed: int,
    ) -> TwinSnapshot:
        """Take a snapshot and store it."""
        snap = TwinSnapshot(
            tick_index=tick_index,
            sim_time_s=sim_time_s,
            machine_states={
                mid: ms.to_dict() for mid, ms in machine_states.items()
            },
            line_states={
                lid: ls.to_dict() for lid, ls in line_states.items()
            },
            network_states={
                mid: ns.to_dict() for mid, ns in network_states.items()
            },
            parameter_state=parameter_state.model_dump(),
            base_seed=base_seed,
        )
        self._snapshots.append(snap)
        return snap

    def get_nearest_before(self, tick_index: int) -> Optional[TwinSnapshot]:
        """Return the snapshot with the largest tick_index <= the given tick."""
        best: Optional[TwinSnapshot] = None
        for snap in self._snapshots:
            if snap.tick_index <= tick_index:
                if best is None or snap.tick_index > best.tick_index:
                    best = snap
        return best

    def get_all(self) -> list[TwinSnapshot]:
        """Return all stored snapshots, oldest first."""
        return list(self._snapshots)

    @property
    def count(self) -> int:
        return len(self._snapshots)

    def clear(self) -> None:
        self._snapshots.clear()
