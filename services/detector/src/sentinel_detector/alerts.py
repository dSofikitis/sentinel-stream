"""Builders for the alert.schema.json wire format."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sentinel_detector import __version__
from sentinel_detector.sigma import SigmaRule


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def from_sigma_match(rule: SigmaRule, event: dict) -> dict:
    return {
        "alert_id": str(uuid.uuid4()),
        "tenant_id": event.get("tenant_id", "default"),
        "ts": _now_iso(),
        "kind": "sigma",
        "rule_id": rule.id,
        "rule_title": rule.title,
        "model": None,
        "score": None,
        "severity": rule.severity,
        "event_id": event["event_id"],
        "message": rule.description,
        "detector_version": __version__,
    }


def from_anomaly(score: float, event: dict, model: str = "isolation-forest-v1") -> dict:
    severity = (
        "high"
        if score >= 0.85
        else "medium"
        if score >= 0.7
        else "low"
    )
    return {
        "alert_id": str(uuid.uuid4()),
        "tenant_id": event.get("tenant_id", "default"),
        "ts": _now_iso(),
        "kind": "anomaly",
        "rule_id": None,
        "rule_title": None,
        "model": model,
        "score": round(float(score), 4),
        "severity": severity,
        "event_id": event["event_id"],
        "message": f"Anomaly score {score:.3f} from {model}",
        "detector_version": __version__,
    }
