"""changepoint.py -- CUSUM change-point detection per signal (Section 8).

Detects the onset time of a shift in a signal using a cumulative sum
(CUSUM) algorithm.  Returns the tick at which the signal appears to have
shifted from its baseline behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class ChangePointResult:
    """Result of change-point detection for one signal."""

    signal: str
    detected: bool            # True if a change point was found
    onset_tick: Optional[int] # tick index of the detected onset
    magnitude: float          # estimated shift magnitude
    direction: str            # "increase" or "decrease"
    cusum_max: float          # peak CUSUM statistic
    threshold: float          # threshold used
    description: str = ""


class CUSUMDetector:
    """CUSUM (Cumulative Sum) change-point detector.

    For each signal, maintains a running CUSUM that accumulates deviations
    from the baseline mean.  When the CUSUM exceeds a threshold, a change
    point is detected, and the onset tick is estimated by walking back to
    where the accumulation started.

    Parameters:
        threshold: CUSUM statistic threshold for declaring a change point.
        drift: Allowance for normal variation (subtracted from each step).
    """

    def __init__(self, threshold: float = 5.0, drift: float = 0.5):
        self.threshold = threshold
        self.drift = drift

    def detect(
        self,
        signal_name: str,
        values: np.ndarray,
        ticks: Optional[np.ndarray] = None,
        baseline_mean: Optional[float] = None,
        baseline_std: Optional[float] = None,
    ) -> ChangePointResult:
        """Run CUSUM on a signal array.

        Args:
            signal_name: Name of the signal.
            values: Array of signal values (time-ordered).
            ticks: Optional array of tick indices corresponding to values.
            baseline_mean: Mean of the baseline period. If None, uses the
                           first quarter of values.
            baseline_std: Std of the baseline. If None, computed from data.

        Returns:
            ChangePointResult with onset tick and magnitude.
        """
        n = len(values)
        if n < 5:
            return ChangePointResult(
                signal=signal_name, detected=False, onset_tick=None,
                magnitude=0.0, direction="none", cusum_max=0.0,
                threshold=self.threshold,
                description="Insufficient data for change-point detection.",
            )

        if ticks is None:
            ticks = np.arange(n)

        # Estimate baseline from the first quarter
        baseline_n = max(5, n // 4)
        if baseline_mean is None:
            baseline_mean = float(np.mean(values[:baseline_n]))
        if baseline_std is None:
            baseline_std = float(np.std(values[:baseline_n], ddof=1))
            if baseline_std < 1e-10:
                baseline_std = 1.0  # prevent division by zero

        # Normalize
        normalized = (values - baseline_mean) / baseline_std

        # Two-sided CUSUM
        cusum_pos = np.zeros(n)  # detects increase
        cusum_neg = np.zeros(n)  # detects decrease

        for i in range(1, n):
            cusum_pos[i] = max(0.0, cusum_pos[i - 1] + normalized[i] - self.drift)
            cusum_neg[i] = max(0.0, cusum_neg[i - 1] - normalized[i] - self.drift)

        max_pos = float(np.max(cusum_pos))
        max_neg = float(np.max(cusum_neg))

        # Check which side triggered
        if max_pos >= self.threshold or max_neg >= self.threshold:
            if max_pos >= max_neg:
                # Increase detected
                alarm_idx = int(np.argmax(cusum_pos >= self.threshold))
                if cusum_pos[alarm_idx] < self.threshold:
                    alarm_idx = int(np.argmax(cusum_pos))
                # Walk back to find onset (where CUSUM was last near zero)
                onset_idx = alarm_idx
                for j in range(alarm_idx, -1, -1):
                    if cusum_pos[j] < 0.1:
                        onset_idx = j + 1
                        break
                onset_idx = max(0, min(onset_idx, n - 1))
                direction = "increase"
                cusum_max = max_pos
            else:
                # Decrease detected
                alarm_idx = int(np.argmax(cusum_neg >= self.threshold))
                if cusum_neg[alarm_idx] < self.threshold:
                    alarm_idx = int(np.argmax(cusum_neg))
                onset_idx = alarm_idx
                for j in range(alarm_idx, -1, -1):
                    if cusum_neg[j] < 0.1:
                        onset_idx = j + 1
                        break
                onset_idx = max(0, min(onset_idx, n - 1))
                direction = "decrease"
                cusum_max = max_neg

            # Magnitude: mean of post-onset vs baseline
            post_values = values[onset_idx:]
            magnitude = abs(float(np.mean(post_values)) - baseline_mean)
            onset_tick = int(ticks[onset_idx])

            return ChangePointResult(
                signal=signal_name,
                detected=True,
                onset_tick=onset_tick,
                magnitude=magnitude,
                direction=direction,
                cusum_max=cusum_max,
                threshold=self.threshold,
                description=(
                    f"Change point detected: {direction} of ~{magnitude:.3f} "
                    f"starting at tick {onset_tick} "
                    f"(CUSUM={cusum_max:.2f} > threshold={self.threshold:.2f})"
                ),
            )
        else:
            return ChangePointResult(
                signal=signal_name,
                detected=False,
                onset_tick=None,
                magnitude=0.0,
                direction="none",
                cusum_max=max(max_pos, max_neg),
                threshold=self.threshold,
                description="No change point detected.",
            )
