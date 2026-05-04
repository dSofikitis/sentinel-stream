"""Tiny in-process Sigma matcher.

Real Sigma is a rich detection language with selections, modifiers,
near/aggregation conditions, and field mappings. This matcher
covers the subset that handles ~80% of single-event detections:

- Multiple named ``selection_*`` blocks under ``detection``.
- Each selection is a flat ``{field: value}`` dict where the value is
  either a scalar (equality) or a list (membership).
- A small set of field modifiers: ``contains``, ``startswith``,
  ``endswith``, ``gte``, ``lte``.
- A ``condition`` of the form ``selection`` or
  ``selection_a and selection_b``.

Anything richer can be handled by wrapping pysigma's backend pipeline
behind the same ``Detector`` API without changing callers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml


@dataclass(frozen=True)
class SigmaRule:
    id: str
    title: str
    severity: str
    selections: dict[str, dict[str, Any]]
    condition: str
    description: str | None = None

    @classmethod
    def from_yaml(cls, source: str | Path) -> "SigmaRule":
        if isinstance(source, Path):
            raw = yaml.safe_load(source.read_text(encoding="utf-8"))
        else:
            raw = yaml.safe_load(source)
        if not isinstance(raw, dict):
            raise ValueError("rule must be a mapping")
        detection = raw.get("detection") or {}
        if not isinstance(detection, dict):
            raise ValueError("detection must be a mapping")
        condition = detection.get("condition")
        if not isinstance(condition, str) or not condition.strip():
            raise ValueError("detection.condition is required")
        selections: dict[str, dict[str, Any]] = {}
        for key, value in detection.items():
            if key == "condition":
                continue
            if not isinstance(value, dict):
                raise ValueError(f"selection {key!r} must be a mapping")
            selections[key] = value
        return cls(
            id=str(raw.get("id") or raw["title"]).lower().replace(" ", "_"),
            title=str(raw["title"]),
            severity=str(raw.get("level") or "medium"),
            selections=selections,
            condition=condition.strip(),
            description=raw.get("description"),
        )


def load_rules(directory: Path) -> list[SigmaRule]:
    rules: list[SigmaRule] = []
    for path in sorted(directory.glob("*.yml")) + sorted(directory.glob("*.yaml")):
        rules.append(SigmaRule.from_yaml(path))
    return rules


_BARE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class SigmaMatcher:
    """Evaluates a single SigmaRule against a single event dict."""

    def __init__(self, rule: SigmaRule) -> None:
        self._rule = rule
        self._tokens = _tokenize_condition(rule.condition)

    @property
    def rule(self) -> SigmaRule:
        return self._rule

    def match(self, event: dict) -> bool:
        sels = {name: _selection_matches(sel, event) for name, sel in self._rule.selections.items()}
        return _eval_condition(self._tokens, sels)


def _tokenize_condition(condition: str) -> list[str]:
    tokens: list[str] = []
    for token in re.split(r"\s+", condition.strip()):
        if not token:
            continue
        lowered = token.lower()
        if lowered in {"and", "or", "not"} or _BARE.match(token):
            tokens.append(lowered if lowered in {"and", "or", "not"} else token)
        else:
            raise ValueError(f"unsupported condition token: {token!r}")
    return tokens


def _eval_condition(tokens: list[str], sels: dict[str, bool]) -> bool:
    # Recursive-descent over: term ('and'|'or' term)*, with NOT as a unary prefix.
    pos = [0]

    def peek() -> str | None:
        return tokens[pos[0]] if pos[0] < len(tokens) else None

    def consume() -> str:
        tok = tokens[pos[0]]
        pos[0] += 1
        return tok

    def parse_term() -> bool:
        tok = peek()
        if tok == "not":
            consume()
            return not parse_term()
        if tok is None:
            raise ValueError("unexpected end of condition")
        if tok in {"and", "or"}:
            raise ValueError(f"unexpected operator {tok!r}")
        consume()
        if tok not in sels:
            raise ValueError(f"condition references unknown selection {tok!r}")
        return sels[tok]

    def parse_expr() -> bool:
        left = parse_term()
        while True:
            tok = peek()
            if tok in {"and", "or"}:
                op = consume()
                right = parse_term()
                left = (left and right) if op == "and" else (left or right)
            else:
                break
        return left

    result = parse_expr()
    if pos[0] != len(tokens):
        raise ValueError("trailing tokens in condition")
    return result


def _selection_matches(selection: dict[str, Any], event: dict) -> bool:
    raw = event.get("raw", {}) if isinstance(event.get("raw"), dict) else {}
    for key, expected in selection.items():
        field, modifier = _split_modifier(key)
        actual = event.get(field, raw.get(field))
        if not _field_matches(actual, modifier, expected):
            return False
    return True


def _split_modifier(key: str) -> tuple[str, str]:
    if "|" in key:
        field, modifier = key.split("|", 1)
        return field, modifier.lower()
    return key, ""


def _field_matches(actual: Any, modifier: str, expected: Any) -> bool:
    if isinstance(expected, list):
        return any(_field_matches(actual, modifier, e) for e in expected)
    if actual is None:
        return False
    if modifier == "":
        return actual == expected
    if modifier == "contains":
        return isinstance(actual, str) and isinstance(expected, str) and expected in actual
    if modifier == "startswith":
        return isinstance(actual, str) and isinstance(expected, str) and actual.startswith(expected)
    if modifier == "endswith":
        return isinstance(actual, str) and isinstance(expected, str) and actual.endswith(expected)
    if modifier in {"gte", "ge"}:
        return _coerce_num(actual) is not None and _coerce_num(actual) >= _coerce_num(expected)
    if modifier in {"lte", "le"}:
        return _coerce_num(actual) is not None and _coerce_num(actual) <= _coerce_num(expected)
    raise ValueError(f"unsupported modifier: {modifier!r}")


def _coerce_num(v: Any) -> float | None:
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def evaluate_all(matchers: Iterable[SigmaMatcher], event: dict) -> list[SigmaRule]:
    return [m.rule for m in matchers if m.match(event)]
