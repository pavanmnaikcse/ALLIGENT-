"""anomaly_detector.py -- IsolationForest per machine (Section 8).

Trains on historical "normal" windows (baseline) and scores new windows
as anomalous or not.  The threshold is calibrated on validation data, and
the calibrated threshold + measured false-positive rate are reported.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from sklearn.ensemble import IsolationForest

from .feature_engine import FeatureEngine, WindowFeatures, MACHINE_SIGNALS


@dataclass
class AnomalyResult:
    """Result of anomaly detection for one signal or feature set."""

    signal: str
    score: float           # IsolationForest decision_function (lower = more anomalous)
    is_anomaly: bool       # score < threshold
    threshold: float
    description: str = ""


class AnomalyDetector:
    """IsolationForest-based anomaly detection per machine.

    Usage:
        1. Collect baseline windows (warm-up at normal parameters).
        2. Call fit() to train on baseline feature vectors.
        3. Call detect() on new feature windows to get anomaly scores.
    """

    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self._contamination = contamination
        self._random_state = random_state
        self._models: dict[str, IsolationForest] = {}
        self._thresholds: dict[str, float] = {}
        self._false_positive_rates: dict[str, float] = {}
        self._fitted = False

    def fit(
        self,
        machine_id: str,
        baseline_features: np.ndarray,
        validation_features: Optional[np.ndarray] = None,
    ) -> dict:
        """Train an IsolationForest on baseline feature vectors.

        Args:
            machine_id: Machine identifier.
            baseline_features: (n_samples, n_features) array of normal data.
            validation_features: Optional validation set for threshold calibration.

        Returns:
            Dict with calibrated threshold and false-positive rate.
        """
        model = IsolationForest(
            contamination=self._contamination,
            random_state=self._random_state,
            n_estimators=100,
        )
        model.fit(baseline_features)
        self._models[machine_id] = model

        # Calibrate threshold on validation data (or training data if none)
        cal_data = validation_features if validation_features is not None else baseline_features
        scores = model.decision_function(cal_data)

        # Threshold at the contamination percentile
        threshold = float(np.percentile(scores, self._contamination * 100))
        self._thresholds[machine_id] = threshold

        # Measure false-positive rate on the calibration set
        fp_rate = float(np.mean(scores < threshold))
        self._false_positive_rates[machine_id] = fp_rate

        self._fitted = True
        return {
            "machine_id": machine_id,
            "threshold": threshold,
            "false_positive_rate": fp_rate,
            "n_training_samples": len(baseline_features),
        }

    def detect(
        self,
        machine_id: str,
        features: np.ndarray,
    ) -> list[AnomalyResult]:
        """Score a feature vector against the trained model.

        Args:
            machine_id: Machine identifier.
            features: (1, n_features) or (n_samples, n_features) array.

        Returns:
            List of AnomalyResult, one per sample.
        """
        if machine_id not in self._models:
            raise ValueError(f"No model trained for {machine_id}. Call fit() first.")

        model = self._models[machine_id]
        threshold = self._thresholds[machine_id]

        if features.ndim == 1:
            features = features.reshape(1, -1)

        scores = model.decision_function(features)
        results = []
        for i, score in enumerate(scores):
            results.append(AnomalyResult(
                signal=f"machines.{machine_id}",
                score=float(score),
                is_anomaly=bool(score < threshold),
                threshold=threshold,
                description=(
                    f"Anomaly score={score:.4f} "
                    f"(threshold={threshold:.4f}, "
                    f"{'ANOMALOUS' if score < threshold else 'normal'})"
                ),
            ))
        return results

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    def get_calibration_info(self, machine_id: str) -> dict:
        """Return calibration details for a machine."""
        return {
            "machine_id": machine_id,
            "threshold": self._thresholds.get(machine_id),
            "false_positive_rate": self._false_positive_rates.get(machine_id),
        }


def build_feature_vector(features: dict[str, WindowFeatures], machine_id: str) -> np.ndarray:
    """Build a feature vector for anomaly detection from window features.

    Uses mean, std, slope, z_score for each machine signal.
    """
    vector = []
    for sig in MACHINE_SIGNALS:
        key = f"machines.{machine_id}.{sig}"
        feat = features.get(key)
        if feat is not None:
            vector.extend([feat.mean, feat.std, feat.slope, feat.z_score])
        else:
            vector.extend([0.0, 0.0, 0.0, 0.0])
    return np.array(vector)
