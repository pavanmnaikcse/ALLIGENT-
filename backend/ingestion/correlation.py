"""correlation.py -- Lagged cross-correlation between signal pairs (Section 8).

Computes pairwise lagged cross-correlation to find which signals lead
or lag others, supporting the Correlation agent's timeline construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class LaggedCorrelationResult:
    """Result of lagged cross-correlation between two signals."""

    signal_a: str
    signal_b: str
    max_correlation: float      # peak cross-correlation value
    optimal_lag: int            # lag (in ticks) where correlation peaks
    lag_direction: str          # "a_leads_b" or "b_leads_a" or "synchronous"
    description: str = ""


def lagged_cross_correlation(
    signal_a_name: str,
    signal_b_name: str,
    values_a: np.ndarray,
    values_b: np.ndarray,
    max_lag: int = 60,
) -> Optional[LaggedCorrelationResult]:
    """Compute lagged cross-correlation between two signals.

    Args:
        signal_a_name: Name of signal A.
        signal_b_name: Name of signal B.
        values_a: Time-series values for signal A.
        values_b: Time-series values for signal B.
        max_lag: Maximum lag to search (in ticks).

    Returns:
        LaggedCorrelationResult, or None if insufficient data.
    """
    n = min(len(values_a), len(values_b))
    if n < 10:
        return None

    # Truncate to same length
    a = values_a[:n].astype(float)
    b = values_b[:n].astype(float)

    # Normalize (z-score)
    a_std = np.std(a)
    b_std = np.std(b)
    if a_std < 1e-10 or b_std < 1e-10:
        return LaggedCorrelationResult(
            signal_a=signal_a_name, signal_b=signal_b_name,
            max_correlation=0.0, optimal_lag=0,
            lag_direction="synchronous",
            description="One or both signals have near-zero variance.",
        )

    a_norm = (a - np.mean(a)) / a_std
    b_norm = (b - np.mean(b)) / b_std

    # Compute cross-correlation at each lag
    best_corr = -1.0
    best_lag = 0

    for lag in range(-min(max_lag, n // 3), min(max_lag, n // 3) + 1):
        if lag >= 0:
            # a leads b by 'lag' ticks
            corr_vals = a_norm[:n - lag] * b_norm[lag:n]
        else:
            # b leads a by '-lag' ticks
            corr_vals = a_norm[-lag:n] * b_norm[:n + lag]

        if len(corr_vals) < 5:
            continue

        corr = abs(float(np.mean(corr_vals)))
        if corr > best_corr:
            best_corr = corr
            best_lag = lag

    # Determine direction
    if abs(best_lag) <= 2:
        direction = "synchronous"
    elif best_lag > 0:
        direction = "a_leads_b"
    else:
        direction = "b_leads_a"

    return LaggedCorrelationResult(
        signal_a=signal_a_name,
        signal_b=signal_b_name,
        max_correlation=best_corr,
        optimal_lag=best_lag,
        lag_direction=direction,
        description=(
            f"Peak correlation={best_corr:.3f} at lag={best_lag} ticks "
            f"({direction})"
        ),
    )


def compute_pairwise_correlations(
    signals: dict[str, np.ndarray],
    max_lag: int = 60,
) -> list[LaggedCorrelationResult]:
    """Compute lagged cross-correlation for all signal pairs.

    Args:
        signals: Dict of signal_name -> values array.
        max_lag: Maximum lag to search.

    Returns:
        List of LaggedCorrelationResult for all pairs.
    """
    names = list(signals.keys())
    results = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            result = lagged_cross_correlation(
                names[i], names[j],
                signals[names[i]], signals[names[j]],
                max_lag=max_lag,
            )
            if result is not None:
                results.append(result)
    return results
