"""Attack scenarios. Each yields a sequence of events that, in aggregate,
should fire one or more downstream detections."""

from __future__ import annotations

from typing import Iterable

from sentinel_generator.events import auth_event, network_event


def brute_force_ssh(user: str = "root", attempts: int = 12, src_ip: str = "203.0.113.66") -> Iterable[dict]:
    """N failed logins for the same user from the same IP, then a success."""
    for _ in range(attempts):
        ev = auth_event(success=False, user=user)
        ev["raw"]["src_ip"] = src_ip
        ev["raw"]["service"] = "ssh"
        yield ev
    ev = auth_event(success=True, user=user)
    ev["raw"]["src_ip"] = src_ip
    ev["raw"]["service"] = "ssh"
    yield ev


def port_scan(src_ip: str = "203.0.113.77", ports: int = 25) -> Iterable[dict]:
    """Single source hammering many distinct destination ports."""
    seen: set[int] = set()
    while len(seen) < ports:
        port = (len(seen) + 1) * 17 % 65535
        if port < 1 or port in seen:
            continue
        seen.add(port)
        yield network_event(accepted=False, src_ip=src_ip, dst_port=port)


SCENARIOS = {
    "brute_force_ssh": brute_force_ssh,
    "port_scan": port_scan,
}
