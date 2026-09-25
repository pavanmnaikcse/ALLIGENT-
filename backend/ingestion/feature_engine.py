"""feature_engine.py -- Rolling window feature computation (Section 8).

Computes rolling 1/5/15-minute windows of mean, std, and slope per signal
from raw telemetry buffers.  These features feed the anomaly detector,
change-point detector, and correlation engine.

Since 1 tick = 1 sim-second, window sizes in ticks are:
  1 min  = 60 ticks
  5 min  = 300 ticks
  15 min = 1500 ticks  (only used when enough data is available)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import numpy as np


# =====================================================================
# Rolling buffer for one signal
# =====================================================================

class SignalBuffer:
    """Fixed-size rolling buffer for a single time-series signal."""

    def __init__(self, max_len: int = 1500):
        self._data: deque[float] = deque(maxlen=max_len)
        self._ticks: deque[int] = deque(maxlen=max_len)

    def append(self, tick: int, value: float) -> None:
        self._data.append(value)
        self._ticks.append(tick)

    def last_n(self, n: int) -> np.ndarray:
        """Return the last n values as a numpy array."""
        data = list(self._data)
        return np.array(data[-n:]) if len(data) >= n else np.array(data)

    def last_n_with_ticks(self, n: int) -> tuple[np.ndarray, np.ndarray]:
        """Return (ticks, values) for the last n entries."""
        data = list(self._data)
        ticks = list(self._ticks)
        if len(data) >= n:
            return np.array(ticks[-n:]), np.array(data[-n:])
        return np.array(ticks), np.array(data)

    @property
    def count(self) -> int:
        return len(self._data)

    @property
    def values(self) -> np.ndarray:
        return np.array(list(self._data))


# =====================================================================
# Window features
# =====================================================================

@dataclass
class WindowFeatures:
    """Computed features for one signal over one window."""

    signal: str
    window_ticks: int
    mean: float
    std: float
    slope: float          # linear regression slope
    min_val: float
    max_val: float
    latest: float
    z_score: float        # (latest - mean) / std, or 0 if std is tiny
    count: int            # how many samples were in the window


def compute_window_features(
    signal_name: str,
    values: np.ndarray,
    window_ticks: int,
) -> Optional[WindowFeatures]:
    """Compute mean/std/slope/z-score over a window of values."""
    if len(values) < 3:
        return None

    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
    min_val = float(np.min(values))
    max_val = float(np.max(values))
    latest = float(values[-1])

    # Linear regression slope
    x = np.arange(len(values), dtype=float)
    if len(values) > 1:
        slope = float(np.polyfit(x, values, 1)[0])
    else:
        slope = 0.0

    # Z-score of latest value
    z_score = (latest - mean) / std if std > 1e-10 else 0.0

    return WindowFeatures(
        signal=signal_name,
        window_ticks=window_ticks,
        mean=mean,
        std=std,
        slope=slope,
        min_val=min_val,
        max_val=max_val,
        latest=latest,
        z_score=z_score,
        count=len(values),
    )


# =====================================================================
# Feature engine -- manages buffers and computes features per machine
# =====================================================================

# The signal names we track per machine
MACHINE_SIGNALS = [
    "rpm", "temperature_c", "vibration_mm_s", "motor_current_a",
    "pressure_bar", "coolant_flow_lpm", "bearing_wear",
]

# Line-level signals
LINE_SIGNALS = ["defect_rate", "kwh_per_unit", "co2_per_unit"]

# Network signals
NETWORK_SIGNALS = ["message_rate", "cross_check_residual"]

# Window sizes (in ticks = sim-seconds)
WINDOW_SIZES = {
    "1min": 60,
    "5min": 300,
    "15min": 1500,
}


class FeatureEngine:
    """Manages rolling buffers and computes window features for all signals.

    Call `ingest_tick(payload)` each tick with the twin's output payload.
    Call `get_features()` to retrieve current features for all signals/windows.
    """

    def __init__(self, buffer_size: int = 1500):
        self._buffers: dict[str, SignalBuffer] = {}
        self._buffer_size = buffer_size

    def _get_buffer(self, signal: str) -> SignalBuffer:
        if signal not in self._buffers:
            self._buffers[signal] = SignalBuffer(max_len=self._buffer_size)
        return self._buffers[signal]

    def ingest_tick(self, payload: dict) -> None:
        """Ingest one tick of telemetry from the twin's output."""
        tick = payload["tick_index"]

        # Machine signals
        for mid, mdata in payload.get("machines", {}).items():
            for sig in MACHINE_SIGNALS:
                if sig in mdata:
                    buf = self._get_buffer(f"machines.{mid}.{sig}")
                    buf.append(tick, mdata[sig])

        # Line signals
        for lid, ldata in payload.get("lines", {}).items():
            for sig in LINE_SIGNALS:
                if sig in ldata:
                    buf = self._get_buffer(f"lines.{lid}.{sig}")
                    buf.append(tick, ldata[sig])

        # Network signals
        for mid, ndata in payload.get("network", {}).items():
            for sig in NETWORK_SIGNALS:
                if sig in ndata:
                    buf = self._get_buffer(f"network.{mid}.{sig}")
                    buf.append(tick, ndata[sig])

    def get_features(self, window_name: str = "1min") -> dict[str, WindowFeatures]:
        """Compute features for all signals at a given window size.

        Returns a dict of signal_name -> WindowFeatures.
        Signals with insufficient data are omitted.
        """
        window_ticks = WINDOW_SIZES.get(window_name, 60)
        result = {}
        for signal, buf in self._buffers.items():
            values = buf.last_n(window_ticks)
            feat = compute_window_features(signal, values, window_ticks)
            if feat is not None:
                result[signal] = feat
        return result

    def get_all_features(self) -> dict[str, dict[str, WindowFeatures]]:
        """Compute features for all signals at all window sizes."""
        return {
            wname: self.get_features(wname)
            for wname in WINDOW_SIZES
        }

    def get_buffer(self, signal: str) -> Optional[SignalBuffer]:
        """Access a raw signal buffer for direct analysis."""
        return self._buffers.get(signal)

    @property
    def signal_names(self) -> list[str]:
        return list(self._buffers.keys())
