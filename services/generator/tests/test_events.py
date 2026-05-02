from sentinel_generator.events import (
    auth_event,
    dns_event,
    network_event,
    random_event,
    random_events,
)

REQUIRED_TOP = {"event_id", "tenant_id", "source", "transport", "raw"}


def test_auth_event_shape() -> None:
    ev = auth_event(success=True, user="alice")
    assert REQUIRED_TOP <= set(ev.keys())
    assert ev["raw"]["event_class"] == "auth"
    assert ev["raw"]["outcome"] == "success"
    assert ev["raw"]["user"] == "alice"


def test_auth_event_failure_severity() -> None:
    ev = auth_event(success=False)
    assert ev["raw"]["outcome"] == "failure"
    assert ev["raw"]["severity"] == "warning"


def test_network_event_drop() -> None:
    ev = network_event(accepted=False, src_ip="1.2.3.4", dst_port=22)
    assert ev["raw"]["event_class"] == "network"
    assert ev["raw"]["action"] == "drop"
    assert ev["raw"]["src_ip"] == "1.2.3.4"
    assert ev["raw"]["dst_port"] == 22


def test_dns_event_default_query() -> None:
    ev = dns_event()
    assert ev["raw"]["event_class"] == "dns"
    assert ev["raw"]["query"]


def test_random_event_returns_known_class() -> None:
    ev = random_event()
    assert ev["raw"]["event_class"] in {"auth", "network", "dns"}


def test_random_events_count() -> None:
    assert sum(1 for _ in random_events(7)) == 7
