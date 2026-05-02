"""Synthetic warmup events for fitting the anomaly model.

Held off in its own module so production can swap the corpus for a
historical pull from ClickHouse without touching the CLI.
"""

from __future__ import annotations

import random


def warmup_corpus(n: int) -> list[dict]:
    """Returns n events that look like normal traffic across auth /
    network / dns classes."""
    events: list[dict] = []
    for _ in range(n):
        kind = random.random()
        if kind < 0.4:
            events.append(
                {
                    "received_at": _ts(business_hours_bias=True),
                    "severity": random.choices(
                        ["info", "warning"],
                        weights=[0.85, 0.15],
                    )[0],
                    "src_port": random.randint(30000, 60000),
                    "dst_port": random.choice([80, 443]),
                    "src_ip": _ip(public=True),
                }
            )
        elif kind < 0.85:
            events.append(
                {
                    "received_at": _ts(business_hours_bias=True),
                    "severity": "info",
                    "src_port": random.randint(30000, 60000),
                    "dst_port": random.choice([22, 80, 443, 5432, 6379]),
                    "src_ip": _ip(public=False),
                }
            )
        else:
            events.append(
                {
                    "received_at": _ts(business_hours_bias=True),
                    "severity": "debug",
                    "src_port": 0,
                    "dst_port": 53,
                    "src_ip": _ip(public=False),
                }
            )
    return events


def _ts(business_hours_bias: bool = False) -> str:
    if business_hours_bias:
        hour = random.choices(
            list(range(0, 24)),
            weights=[1, 1, 1, 1, 1, 1, 1, 2, 4, 6, 6, 6, 5, 6, 6, 5, 4, 3, 2, 1, 1, 1, 1, 1],
        )[0]
    else:
        hour = random.randint(0, 23)
    return f"2026-05-02T{hour:02d}:00:00Z"


def _ip(public: bool) -> str:
    if public:
        return f"203.0.113.{random.randint(1, 254)}"
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
