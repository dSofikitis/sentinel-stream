from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from typing import Iterable


_USERS = ["alice", "bob", "carol", "dan", "erin", "frank", "grace", "heidi"]
_HOSTS = ["api-1", "api-2", "edge-fw", "auth-eu1", "auth-us1", "db-1", "wrk-3"]
_DOMAINS = [
    "google.com",
    "github.com",
    "cloudflare.com",
    "amazonaws.com",
    "stackoverflow.com",
]
_TENANTS = ["acme", "globex", "initech"]
_PUBLIC_RANGE = lambda: f"203.0.113.{random.randint(1, 254)}"  # noqa: E731 - TEST-NET-3
_PRIVATE_RANGE = lambda: f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"  # noqa: E731


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def auth_event(success: bool | None = None, user: str | None = None, host: str | None = None) -> dict:
    if success is None:
        success = random.random() > 0.15  # ~15% failure rate normally
    return {
        "event_id": _new_id(),
        "tenant_id": random.choice(_TENANTS),
        "source": "auth-service",
        "transport": "http",
        "raw": {
            "@timestamp": _now_iso(),
            "event_class": "auth",
            "outcome": "success" if success else "failure",
            "user": user or random.choice(_USERS),
            "host": host or random.choice(_HOSTS),
            "src_ip": _PUBLIC_RANGE(),
            "severity": "info" if success else "warning",
            "message": (
                f"User {user or 'anon'} logged in" if success else f"Login failed for user {user or 'anon'}"
            ),
        },
    }


def network_event(
    accepted: bool | None = None,
    src_ip: str | None = None,
    dst_port: int | None = None,
) -> dict:
    if accepted is None:
        accepted = random.random() > 0.25
    return {
        "event_id": _new_id(),
        "tenant_id": random.choice(_TENANTS),
        "source": "edge-firewall",
        "transport": "syslog",
        "raw": {
            "@timestamp": _now_iso(),
            "event_class": "network",
            "action": "accept" if accepted else "drop",
            "src_ip": src_ip or _PUBLIC_RANGE(),
            "dst_ip": _PRIVATE_RANGE(),
            "src_port": random.randint(1024, 65535),
            "dst_port": dst_port if dst_port is not None else random.choice([22, 80, 443, 3389, 5432, 6379]),
            "protocol": "tcp",
            "severity": "info" if accepted else "notice",
            "message": "fw " + ("accept" if accepted else "drop"),
        },
    }


def dns_event(domain: str | None = None) -> dict:
    return {
        "event_id": _new_id(),
        "tenant_id": random.choice(_TENANTS),
        "source": "dns-resolver",
        "transport": "syslog",
        "raw": {
            "@timestamp": _now_iso(),
            "event_class": "dns",
            "query": domain or random.choice(_DOMAINS),
            "qtype": "A",
            "rcode": "NOERROR",
            "src_ip": _PRIVATE_RANGE(),
            "severity": "debug",
            "message": "dns query",
        },
    }


_FACTORIES = [auth_event, network_event, dns_event]


def random_event() -> dict:
    return random.choice(_FACTORIES)()


def random_events(n: int) -> Iterable[dict]:
    for _ in range(n):
        yield random_event()
