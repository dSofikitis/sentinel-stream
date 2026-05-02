"""sentinel-detector CLI: stdin (events.enriched) -> stdout (alerts).

Real Kafka wiring slots behind the same evaluation path in a follow-up.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from pathlib import Path

from sentinel_detector import alerts as alert_builders
from sentinel_detector.anomaly import Anomaly
from sentinel_detector.events_warmup import warmup_corpus
from sentinel_detector.sigma import SigmaMatcher, load_rules


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="sentinel-detector")
    parser.add_argument(
        "--rules",
        type=Path,
        default=Path("/sigma"),
        help="Directory with Sigma rule files (.yml).",
    )
    parser.add_argument(
        "--anomaly-threshold",
        type=float,
        default=0.65,
        help="Score (0..1) above which an anomaly alert is emitted.",
    )
    parser.add_argument(
        "--no-anomaly",
        action="store_true",
        help="Disable the Isolation Forest stage; only Sigma rules will fire.",
    )
    parser.add_argument(
        "--warmup-size",
        type=int,
        default=512,
        help="Synthetic events used to fit the anomaly model on startup.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=7,
        help="Seed for warmup generation.",
    )
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")

    if args.rules.exists():
        rules = load_rules(args.rules)
    else:
        logging.warning("rules dir %s does not exist; running with zero rules", args.rules)
        rules = []
    matchers = [SigmaMatcher(r) for r in rules]
    logging.info("loaded %d Sigma rule(s)", len(rules))

    anomaly: Anomaly | None = None
    if not args.no_anomaly:
        random.seed(args.seed)
        anomaly = Anomaly()
        anomaly.fit(warmup_corpus(args.warmup_size))
        logging.info("anomaly model fitted (warmup=%d)", args.warmup_size)

    sigma_count = 0
    anomaly_count = 0
    seen = 0

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            logging.warning("skipping non-JSON line: %s", exc)
            continue
        seen += 1
        for matcher in matchers:
            if matcher.match(event):
                alert = alert_builders.from_sigma_match(matcher.rule, event)
                sys.stdout.write(json.dumps(alert) + "\n")
                sigma_count += 1
        if anomaly is not None:
            result = anomaly.score(event, threshold=args.anomaly_threshold)
            if result.is_anomaly:
                alert = alert_builders.from_anomaly(result.score, event)
                sys.stdout.write(json.dumps(alert) + "\n")
                anomaly_count += 1
        sys.stdout.flush()

    logging.info(
        "sentinel-detector done: events=%d sigma_alerts=%d anomaly_alerts=%d",
        seen,
        sigma_count,
        anomaly_count,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
