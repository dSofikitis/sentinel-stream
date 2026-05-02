from sentinel_generator.scenarios import SCENARIOS, brute_force_ssh, port_scan


def test_brute_force_ssh_yields_failures_then_success() -> None:
    events = list(brute_force_ssh(user="root", attempts=5, src_ip="1.1.1.1"))
    assert len(events) == 6
    failures = [e for e in events[:5] if e["raw"]["outcome"] == "failure"]
    assert len(failures) == 5
    assert events[-1]["raw"]["outcome"] == "success"
    assert {e["raw"]["src_ip"] for e in events} == {"1.1.1.1"}
    assert {e["raw"]["user"] for e in events} == {"root"}


def test_port_scan_distinct_ports_from_one_source() -> None:
    events = list(port_scan(src_ip="2.2.2.2", ports=10))
    assert len(events) == 10
    ports = [e["raw"]["dst_port"] for e in events]
    assert len(set(ports)) == 10
    assert {e["raw"]["src_ip"] for e in events} == {"2.2.2.2"}
    assert all(e["raw"]["action"] == "drop" for e in events)


def test_scenarios_registry_contains_known_scenarios() -> None:
    assert "brute_force_ssh" in SCENARIOS
    assert "port_scan" in SCENARIOS
