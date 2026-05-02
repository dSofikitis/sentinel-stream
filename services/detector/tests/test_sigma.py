from pathlib import Path

import pytest

from sentinel_detector.sigma import SigmaMatcher, SigmaRule, load_rules

RULES_DIR = Path(__file__).resolve().parents[3] / "sigma"


def _rule(yaml_text: str) -> SigmaRule:
    return SigmaRule.from_yaml(yaml_text)


def test_simple_equality_match() -> None:
    rule = _rule(
        """
title: Auth failure
detection:
  selection:
    event_class: auth
    outcome: failure
  condition: selection
"""
    )
    matcher = SigmaMatcher(rule)
    assert matcher.match({"event_class": "auth", "outcome": "failure"})
    assert not matcher.match({"event_class": "auth", "outcome": "success"})


def test_list_value_acts_as_or() -> None:
    rule = _rule(
        """
title: Suspicious TLD
detection:
  selection:
    event_class: dns
    query|endswith:
      - .zip
      - .xyz
  condition: selection
"""
    )
    matcher = SigmaMatcher(rule)
    assert matcher.match({"event_class": "dns", "query": "evil.zip"})
    assert matcher.match({"event_class": "dns", "query": "weird.xyz"})
    assert not matcher.match({"event_class": "dns", "query": "google.com"})


def test_lte_modifier() -> None:
    rule = _rule(
        """
title: Privileged port
detection:
  selection:
    dst_port|lte: 1023
  condition: selection
"""
    )
    matcher = SigmaMatcher(rule)
    assert matcher.match({"dst_port": 22})
    assert matcher.match({"dst_port": 1023})
    assert not matcher.match({"dst_port": 1024})


def test_contains_modifier() -> None:
    rule = _rule(
        """
title: Failed string in message
detection:
  selection:
    message|contains: "failed"
  condition: selection
"""
    )
    matcher = SigmaMatcher(rule)
    assert matcher.match({"message": "auth failed for user"})
    assert not matcher.match({"message": "user logged in"})


def test_and_condition() -> None:
    rule = _rule(
        """
title: Multi-selection
detection:
  sel_a:
    event_class: auth
  sel_b:
    outcome: failure
  condition: sel_a and sel_b
"""
    )
    matcher = SigmaMatcher(rule)
    assert matcher.match({"event_class": "auth", "outcome": "failure"})
    assert not matcher.match({"event_class": "auth", "outcome": "success"})
    assert not matcher.match({"event_class": "network", "outcome": "failure"})


def test_or_condition() -> None:
    rule = _rule(
        """
title: Either
detection:
  sel_a:
    event_class: auth
  sel_b:
    event_class: dns
  condition: sel_a or sel_b
"""
    )
    matcher = SigmaMatcher(rule)
    assert matcher.match({"event_class": "auth"})
    assert matcher.match({"event_class": "dns"})
    assert not matcher.match({"event_class": "network"})


def test_not_condition() -> None:
    rule = _rule(
        """
title: Inverted
detection:
  sel:
    event_class: auth
  condition: not sel
"""
    )
    matcher = SigmaMatcher(rule)
    assert not matcher.match({"event_class": "auth"})
    assert matcher.match({"event_class": "network"})


def test_field_falls_back_to_raw_block() -> None:
    rule = _rule(
        """
title: Raw payload field
detection:
  selection:
    service: ssh
  condition: selection
"""
    )
    matcher = SigmaMatcher(rule)
    # value lives under 'raw' (matches our generator's shape)
    assert matcher.match({"event_class": "auth", "raw": {"service": "ssh"}})


def test_load_rules_loads_repo_sigma_directory() -> None:
    rules = load_rules(RULES_DIR)
    ids = {r.id for r in rules}
    assert "ssh_login_failure" in ids
    assert "fw_drop_public_to_priv_port" in ids
    assert "dns_query_suspicious_tld" in ids


def test_unknown_modifier_raises() -> None:
    rule = _rule(
        """
title: Bad mod
detection:
  selection:
    field|nope: 1
  condition: selection
"""
    )
    matcher = SigmaMatcher(rule)
    with pytest.raises(ValueError):
        matcher.match({"field": 1})
