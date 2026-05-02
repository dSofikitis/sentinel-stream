# SentinelStream

> **Sentinel** — a guard standing watch. **Stream** — events flowing past it.

A real-time security-event detection pipeline. Events flow through a
multi-language streaming graph that ingests, parses, enriches,
detects, and persists at sustained throughput, with Sigma-rule and
ML-driven detection running side by side.

## Pipeline at a glance

```
generator ─► ingest ─► (events.raw) ─► parser ─► (events.enriched) ─► detector ─► (alerts)
                                                       │                              │
                                                       └─────────► sink ◄─────────────┘
                                                                    │
                                                                    ▼
                                                                ClickHouse ◄── Grafana
```

| Service | Language | Role |
|---|---|---|
| `generator` | Python | Replays a corpus or emits synthetic auth/network/dns events at a configurable rate, with optional attack scenarios. |
| `ingest` | Go | HTTP `POST /events`; validates and produces a stamped `RawEvent`. |
| `parser` | Rust | Parses timestamps, classifies, normalizes severity, extracts entity fields; produces `EnrichedEvent`. |
| `detector` | Python | Sigma rule engine + Isolation Forest anomaly model; emits `Alert`s. |
| `sink` | Go | Batches `EnrichedEvent`s and `Alert`s into ClickHouse over HTTP `JSONEachRow`. |

Backbone: **Redpanda** (Kafka API), **ClickHouse**, **Grafana** with
two pre-baked dashboards.

## Status

The MVP is a polyglot detection pipeline that can run **as a Unix
pipe** (no broker needed) for local development and demos:

```bash
sentinel-generator --dry-run --rate 50 --duration 5 --inject brute_force_ssh \
  | sentinel-parser \
  | sentinel-detector --rules ./sigma \
  | sentinel-sink
```

Each stage is an independent binary with its own tests and Dockerfile.
The Compose stack stands up Redpanda, ClickHouse, and Grafana
alongside the `ingest` HTTP service; the Kafka-backed
consumer/producer wiring on `parser`, `detector`, and `sink` lands in
v0.2 — they're already structured behind the right interfaces.

## Quickstart

Bring up the data plane (datastores + Grafana + ingest):

```bash
docker compose -f deploy/compose/docker-compose.yml up -d
```

Open Grafana at <http://localhost:3000> (admin / admin). The
dashboards land in the *SentinelStream* folder.

Generate some events into the ingest service:

```bash
docker compose -f deploy/compose/docker-compose.yml \
  --profile tools run --rm generator \
  --target http://ingest:8080/events --rate 50 --duration 30 --inject brute_force_ssh
```

Watch ingest's stdout to confirm `RawEvent`s are being published:

```bash
docker compose -f deploy/compose/docker-compose.yml logs -f ingest
```

## Architecture
See [ARCHITECTURE.md](ARCHITECTURE.md) for the data-flow diagram, topic
contracts, and rationale behind the language picks per service.

## Development

Polyglot monorepo. Each service builds and tests independently.

| Service | Build | Test |
|---|---|---|
| `services/generator` | `pip install -e .` | `pytest` |
| `services/ingest` | `go build ./...` | `go test ./...` |
| `services/parser` | `cargo build` | `cargo test` |
| `services/detector` | `pip install -e .` | `pytest` |
| `services/sink` | `go build ./...` | `go test ./...` |

CI (`.github/workflows/ci.yml`) runs lint + test in a parallel matrix
across Go, Rust, and Python on every push to `main` and every PR.

## License
MIT. Copyright (c) 2026 @dSofikitis.
