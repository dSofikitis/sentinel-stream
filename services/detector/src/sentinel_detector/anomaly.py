"""Lightweight anomaly detector built on Isolation Forest.

Each event is scored independently from a small numeric feature
vector — deliberately simple, so reviewers can read the entire
scorer. Anything more ambitious (autoencoders, sliding-window
features) slots behind the same ``Anomaly.score`` API without
changing callers.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import IsolationForest


SEVERITY_RANK = {
    "debug": 0,
    "info": 1,
    "notice": 2,
    "warning": 3,
    "error": 4,
    "critical": 5,
    "alert": 6,
    "emergency": 7,
}


def featurize(event: dict) -> list[float]:
    """Project an EnrichedEvent dict to a fixed-length feature vector."""
    sev = SEVERITY_RANK.get(str(event.get("severity", "info")).lower(), 1)
    src_port = float(event.get("src_port") or 0)
    dst_port = float(event.get("dst_port") or 0)
    src_ip = str(event.get("src_ip") or "")
    src_ip_bucket = (
        int(hashlib.sha1(src_ip.encode("utf-8")).hexdigest()[:8], 16) % 1024
        if src_ip
        else 0
    )
    received_at = str(event.get("received_at") or "")
    hour = 0
    if len(received_at) >= 13 and received_at[10] == "T":
        try:
            hour = int(received_at[11:13])
        except ValueError:
            hour = 0
    return [
        float(sev),
        src_port,
        dst_port,
        float(src_ip_bucket),
        float(hour),
    ]


@dataclass
class AnomalyResult:
    score: float  # in [0, 1] — higher = more anomalous
    is_anomaly: bool


class Anomaly:
    """Wraps an Isolation Forest with online predict + a stable
    [0, 1] anomaly score."""

    MODEL_NAME = "isolation-forest-v1"

    def __init__(self, *, contamination: float = 0.05, random_state: int = 7) -> None:
        self._model = IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=random_state,
        )
        self._fitted = False
        # Decision function range on the training set, used to map
        # raw scores into [0, 1] for downstream consumers.
        self._df_min = 0.0
        self._df_max = 1.0

    def fit(self, training_events: list[dict]) -> None:
        if not training_events:
            raise ValueError("anomaly model needs at least one training event")
        x = np.array([featurize(ev) for ev in training_events], dtype=float)
        self._model.fit(x)
        df = self._model.decision_function(x)
        self._df_min = float(df.min())
        self._df_max = float(df.max())
        if self._df_max - self._df_min < 1e-9:
            self._df_max = self._df_min + 1.0
        self._fitted = True

    def score(self, event: dict, threshold: float = 0.65) -> AnomalyResult:
        if not self._fitted:
            raise RuntimeError("anomaly model not fitted; call fit() first")
        x = np.array([featurize(event)], dtype=float)
        raw = float(self._model.decision_function(x)[0])
        norm = 1.0 - (raw - self._df_min) / (self._df_max - self._df_min)
        norm = max(0.0, min(1.0, norm))
        return AnomalyResult(score=norm, is_anomaly=norm >= threshold)
