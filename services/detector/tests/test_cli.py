import io
import json
from pathlib import Path

import pytest

from sentinel_detector.cli import main

RULES_DIR = Path(__file__).resolve().parents[3] / "sigma"


def _enriched(extra: dict | None = None) -> dict:
    base = {
        "event_id": "e-1",
        "tenant_id": "acme",
        "source": "auth",
        "received_at": "2026-05-02T12:00:00Z",
        "ts": "2026-05-02T12:00:00.000Z",
        "event_class": "auth",
        "severity": "warning",
        "host": "api-1",
        "user": "alice",
        "src_ip": "203.0.113.1",
        "dst_ip": None,
        "src_port": 51234,
        "dst_port": 22,
        "geo": None,
        "message": None,
        "parser_version": "0.2.0",
    }
    if extra:
        base.update(extra)
    return base


def _run(events: list[dict], extra_args: list[str], monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO("\n".join(json.dumps(e) for e in events) + "\n"),
    )
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    rc = main(["--rules", str(RULES_DIR), "--no-anomaly", *extra_args])
    assert rc == 0
    out.seek(0)
    return [json.loads(line) for line in out.read().splitlines() if line.strip()]


def test_cli_fires_sigma_rule_on_failed_ssh(monkeypatch) -> None:
    event = _enriched({"raw": {"outcome": "failure", "service": "ssh"}})
    alerts = _run([event], [], monkeypatch)
    assert any(a["kind"] == "sigma" and a["rule_id"] == "ssh_login_failure" for a in alerts)


def test_cli_fires_no_alert_for_clean_event(monkeypatch) -> None:
    event = _enriched(
        {"event_class": "auth", "raw": {"outcome": "success", "service": "ssh"}}
    )
    alerts = _run([event], [], monkeypatch)
    sigma_alerts = [a for a in alerts if a["kind"] == "sigma"]
    assert sigma_alerts == []
