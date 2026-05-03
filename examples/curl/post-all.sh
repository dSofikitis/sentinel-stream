#!/usr/bin/env bash
# Post one of every payload under examples/payloads/ to the running ingest.
# Override the target with INGEST=http://my-host:8080 ...

set -euo pipefail

INGEST="${INGEST:-http://localhost:8080}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for payload in "$HERE"/payloads/*.json; do
  echo ">>> POST $(basename "$payload")"
  curl -sS -X POST "$INGEST/events" \
    -H 'Content-Type: application/json' \
    --data-binary @"$payload"
  echo
done
