"""Populate ClickHouse with realistic-looking enriched events + alerts
*without* the Kafka-backed pipeline.

Runs the actual generator + detector module logic in-process, applies
a Python re-implementation of the parser's enrichment (the Rust
binary needs a Kafka backend before it joins the live stack), and
batch-inserts both `events_enriched` and `alerts` into ClickHouse via
HTTP `JSONEachRow`.

Used as the `demo-seed` one-shot in the Compose `tools` profile so
Grafana has something to render before the v0.2 broker integration
lands.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sentinel_detector.anomaly import Anomaly
from sentinel_detector.events_warmup import warmup_corpus
from sentinel_detector.sigma import SigmaMatcher, load_rules
from sentinel_generator.events import random_event
from sentinel_generator.scenarios import SCENARIOS


SEVERITY_ALIASES = {
    "warn": "warning",
    "informational": "info",
    "err": "error",
    "crit": "critical",
    "emerg": "emergency",
}
EVENT_CLASSES = {"auth", "network", "dns", "process", "file", "other"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="seed_demo")
    p.add_argument("--rows", type=int, default=600, help="Total events to generate.")
    p.add_argument("--inject-attacks", action="store_true", default=True)
    p.add_argument("--no-anomaly", action="store_true")
    p.add_argument("--anomaly-threshold", type=float, default=0.65)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--rules-dir", default="/sigma")
    p.add_argument("--clickhouse-url", default=os.environ.get("CLICKHOUSE_URL", "http://clickhouse:8123"))
    p.add_argument("--clickhouse-db", default=os.environ.get("CLICKHOUSE_DB", "sentinel"))
    p.add_argument("--clickhouse-user", default=os.environ.get("CLICKHOUSE_USER", "sentinel"))
    p.add_argument("--clickhouse-password", default=os.environ.get("CLICKHOUSE_PASSWORD", "sentinel"))
    p.add_argument("--minutes-back", type=int, default=180, help="Spread events across the last N minutes.")
    return p.parse_args()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _rand_past_ts(start: datetime, end: datetime) -> str:
    delta = (end - start).total_seconds()
    offset = random.uniform(0, delta)
    return (start + timedelta(seconds=offset)).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def synthesize_events(total: int, inject_attacks: bool, start: datetime, end: datetime) -> list[dict]:
    out: list[dict] = []
    if inject_attacks:
        out.extend(SCENARIOS["brute_force_ssh"](user="root", attempts=18, src_ip="203.0.113.66"))
        out.extend(SCENARIOS["port_scan"](src_ip="203.0.113.77", ports=24))
    while len(out) < total:
        out.append(random_event())
    out = out[:total]
    for ev in out:
        ev["received_at"] = _rand_past_ts(start, end)
        if isinstance(ev.get("raw"), dict) and "@timestamp" not in ev["raw"]:
            ev["raw"]["@timestamp"] = ev["received_at"]
    random.shuffle(out)
    return out


def classify(raw: dict, source: str) -> str:
    cls = raw.get("event_class")
    if isinstance(cls, str) and cls.lower() in EVENT_CLASSES:
        return cls.lower()
    s = source.lower()
    if any(k in s for k in ("auth", "ssh", "login")):
        return "auth"
    if any(k in s for k in ("firewall", "net")):
        return "network"
    if "dns" in s:
        return "dns"
    return "other"


def severity(raw: dict) -> str:
    v = str(raw.get("severity", "info")).lower()
    return SEVERITY_ALIASES.get(v, v if v in {
        "debug", "info", "notice", "warning", "error", "critical", "alert", "emergency"
    } else "info")


def parse_ts(received_at: str, raw: dict) -> str:
    inner = raw.get("@timestamp") if isinstance(raw, dict) else None
    if isinstance(inner, str):
        try:
            datetime.fromisoformat(inner.replace("Z", "+00:00"))
            return inner
        except ValueError:
            pass
    return received_at


def enrich(raw_event: dict) -> dict:
    raw = raw_event.get("raw") if isinstance(raw_event.get("raw"), dict) else {}
    ts = parse_ts(raw_event.get("received_at", ""), raw)
    geo = None
    if raw.get("src_ip"):
        geo = {"country_code": None, "city": None}
    return {
        "event_id": raw_event["event_id"],
        "tenant_id": raw_event.get("tenant_id", "default"),
        "source": raw_event.get("source", "unknown"),
        "received_at": raw_event.get("received_at", ts),
        "ts": ts,
        "event_class": classify(raw, raw_event.get("source", "")),
        "severity": severity(raw),
        "host": raw.get("host"),
        "user": raw.get("user"),
        "src_ip": raw.get("src_ip"),
        "dst_ip": raw.get("dst_ip"),
        "src_port": raw.get("src_port"),
        "dst_port": raw.get("dst_port"),
        "geo": geo,
        "message": raw.get("message"),
        "parser_version": "demo-seed",
        "_raw_for_sigma": raw,  # consumed by detector then dropped before insert
    }


def detect_sigma(matchers: list[SigmaMatcher], event: dict) -> list[dict]:
    raw = event.get("_raw_for_sigma") or {}
    target = {**event, "raw": raw}
    matches = []
    for m in matchers:
        if m.match(target):
            matches.append(_alert_from_sigma(m.rule, event))
    return matches


def detect_anomaly(model: Anomaly, event: dict, threshold: float) -> dict | None:
    result = model.score(event, threshold=threshold)
    if not result.is_anomaly:
        return None
    return _alert_from_anomaly(result.score, event)


def _alert_from_sigma(rule, event: dict) -> dict:
    return {
        "alert_id": str(uuid.uuid4()),
        "tenant_id": event.get("tenant_id", "default"),
        "ts": _now().isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "kind": "sigma",
        "rule_id": rule.id,
        "rule_title": rule.title,
        "model": None,
        "score": None,
        "severity": rule.severity,
        "event_id": event["event_id"],
        "message": rule.description,
        "detector_version": "demo-seed",
    }


def _alert_from_anomaly(score: float, event: dict) -> dict:
    sev = "high" if score >= 0.85 else "medium" if score >= 0.7 else "low"
    return {
        "alert_id": str(uuid.uuid4()),
        "tenant_id": event.get("tenant_id", "default"),
        "ts": _now().isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "kind": "anomaly",
        "rule_id": None,
        "rule_title": None,
        "model": "isolation-forest-v1",
        "score": round(float(score), 4),
        "severity": sev,
        "event_id": event["event_id"],
        "message": f"Anomaly score {score:.3f}",
        "detector_version": "demo-seed",
    }


def _flatten_enriched(rec: dict) -> dict:
    out = {k: v for k, v in rec.items() if k not in ("geo", "_raw_for_sigma")}
    geo = rec.get("geo") or {}
    out["geo_country"] = geo.get("country_code")
    out["geo_city"] = geo.get("city")
    return out


def insert(url: str, db: str, table: str, rows: list[dict], user: str, password: str) -> int:
    if not rows:
        return 0
    body = "\n".join(json.dumps(r) for r in rows).encode("utf-8")
    query = urllib.parse.urlencode({
        "query": f"INSERT INTO {db}.{table} FORMAT JSONEachRow",
        "date_time_input_format": "best_effort",
    })
    target = url.rstrip("/") + "/?" + query
    req = urllib.request.Request(target, data=body, method="POST")
    req.add_header("Content-Type", "application/x-ndjson")
    if user:
        token = (user + ":" + password).encode("utf-8")
        import base64
        req.add_header("Authorization", "Basic " + base64.b64encode(token).decode("ascii"))
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status >= 400:
            raise RuntimeError(f"clickhouse {resp.status}: {resp.read()!r}")
    return len(rows)


def main() -> int:
    args = parse_args()
    random.seed(args.seed)

    end = _now()
    start = end - timedelta(minutes=args.minutes_back)

    rules_dir = Path(args.rules_dir)
    matchers = [SigmaMatcher(r) for r in load_rules(rules_dir)] if rules_dir.exists() else []
    print(f"[seed] loaded {len(matchers)} sigma rule(s)")

    anomaly = None
    if not args.no_anomaly:
        anomaly = Anomaly()
        anomaly.fit(warmup_corpus(512))
        print("[seed] anomaly model fitted")

    raw = synthesize_events(args.rows, args.inject_attacks, start, end)
    enriched = [enrich(e) for e in raw]
    print(f"[seed] synthesized + enriched {len(enriched)} events")

    alerts: list[dict] = []
    for ev in enriched:
        alerts.extend(detect_sigma(matchers, ev))
        if anomaly is not None:
            a = detect_anomaly(anomaly, ev, args.anomaly_threshold)
            if a:
                alerts.append(a)
    print(f"[seed] generated {len(alerts)} alert(s)")

    enriched_rows = [_flatten_enriched(e) for e in enriched]
    t0 = time.time()
    n_events = insert(args.clickhouse_url, args.clickhouse_db, "events_enriched", enriched_rows,
                      args.clickhouse_user, args.clickhouse_password)
    n_alerts = insert(args.clickhouse_url, args.clickhouse_db, "alerts", alerts,
                      args.clickhouse_user, args.clickhouse_password)
    print(f"[seed] inserted events={n_events} alerts={n_alerts} in {time.time() - t0:.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
