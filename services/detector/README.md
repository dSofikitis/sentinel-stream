# sentinel-detector

The detection brain. Reads `events.enriched` lines from stdin and runs
two layers in parallel:

- **Sigma rules** (`sigma/` at the repo root) — declarative YAML
  detections. The MVP ships an in-process matcher that supports
  flat selections, list-as-OR values, the `contains / startswith /
  endswith / gte / lte` modifiers, and `and` / `or` / `not` /
  per-name conditions. Rich pysigma-backend wiring is a follow-up.
- **Isolation Forest** (`scikit-learn`) — fits on a synthetic warmup
  corpus on startup, then scores each enriched event independently.
  Anomalies above `--anomaly-threshold` produce alerts. The model is
  hidden behind an `Anomaly.score` API so swapping in autoencoders or
  windowed features later doesn't touch the CLI.

Both layers emit alerts on stdout matching `schemas/alert.schema.json`.
The Kafka-backed consumer/producer wraps this same evaluation path
in a follow-up phase.

## Run it

End-to-end as a Unix pipe (no Kafka required):

```bash
sentinel-generator --dry-run --rate 50 --duration 5 --inject brute_force_ssh \
  | sentinel-parser \
  | sentinel-detector --rules ./sigma
```

The detector will print one Sigma or anomaly alert per matching
event. Pipe to `jq` if you want to pretty-print:

```bash
... | sentinel-detector --rules ./sigma | jq -c .
```

## Flags

| Flag | Default | Notes |
|---|---|---|
| `--rules` | `/sigma` | Directory of `*.yml` Sigma rules. |
| `--anomaly-threshold` | `0.65` | Score floor for emitting an anomaly alert. |
| `--no-anomaly` | off | Disable the Isolation Forest stage. |
| `--warmup-size` | `512` | Synthetic events used to fit the model. |
| `--seed` | `7` | Seed for warmup sampling. |
