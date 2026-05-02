from __future__ import annotations

import argparse
import json
import logging
import random
import sys
import time

from sentinel_generator.events import random_event
from sentinel_generator.poster import Poster
from sentinel_generator.scenarios import SCENARIOS


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="sentinel-generator")
    parser.add_argument(
        "--target",
        default="http://ingest:8080/events",
        help="Ingest endpoint URL.",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=10.0,
        help="Target events per second.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=30.0,
        help="Run for this many seconds.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed RNG for reproducible runs.",
    )
    parser.add_argument(
        "--inject",
        action="append",
        choices=sorted(SCENARIOS.keys()),
        default=[],
        help="Inject one of the named attack scenarios alongside normal traffic. Repeatable.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print JSONL to stdout instead of posting to the target.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
    )
    return parser.parse_args(argv)


def _drain_scenarios(scenarios: list[str]) -> list[dict]:
    queue: list[dict] = []
    for name in scenarios:
        queue.extend(SCENARIOS[name]())
    return queue


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")
    if args.seed is not None:
        random.seed(args.seed)

    scenario_queue = _drain_scenarios(args.inject)
    if scenario_queue:
        logging.info("scenarios queued: %d events from %s", len(scenario_queue), args.inject)

    poster: Poster | None = None
    if not args.dry_run:
        poster = Poster(args.target)

    interval = 1.0 / args.rate if args.rate > 0 else 0.0
    deadline = time.monotonic() + args.duration
    sent = 0
    while time.monotonic() < deadline:
        event = scenario_queue.pop(0) if scenario_queue else random_event()
        if args.dry_run:
            sys.stdout.write(json.dumps(event) + "\n")
            sys.stdout.flush()
        else:
            assert poster is not None
            poster.post(event)
        sent += 1
        if interval:
            time.sleep(interval)

    if poster is not None:
        logging.info("done. sent=%d failed=%d", poster.sent, poster.failed)
        poster.close()
        return 0 if poster.failed == 0 else 1
    logging.info("done. printed=%d", sent)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
