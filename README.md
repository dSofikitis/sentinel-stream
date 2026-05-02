# SentinelStream

> **Sentinel** — a guard standing watch. **Stream** — events flowing past it.

A real-time security-event detection pipeline. Events flow through a
multi-language streaming graph that ingests, parses, enriches, detects,
and persists at sustained throughput, with Sigma-rule and ML-driven
detection running side by side.

## Pipeline at a glance

```
generator ─► ingest ─► events.raw ─► parser ─► events.enriched ─► detector ─► alerts
                                                       │                          │
                                                       └──────► sink ──────► ClickHouse ◄── Grafana
```

| Service | Language | Role |
|---|---|---|
| `generator` | Python | Replays a seed corpus or emits synthetic auth/network events at a configurable rate. |
| `ingest` | Go | HTTP `POST /events` and a syslog UDP listener; validates and produces to `events.raw`. |
| `parser` | Rust | Consumes `events.raw`, normalizes timestamps, extracts IP/host/severity, GeoIP enrichment; produces to `events.enriched`. |
| `detector` | Python | Consumes `events.enriched`, runs Sigma rules + an Isolation Forest anomaly model; produces to `alerts`. |
| `sink` | Go | Persists `events.enriched` and `alerts` into ClickHouse for analytics. |

Backbone: **Redpanda** (Kafka API), **ClickHouse**, **Grafana**.

## Quickstart

```bash
docker compose -f deploy/compose/docker-compose.yml up -d --build
```

Open Grafana at <http://localhost:3000> (admin/admin), pick the
*SentinelStream — Events* dashboard, and start the generator:

```bash
docker compose -f deploy/compose/docker-compose.yml run --rm generator \
  --rate 50 --duration 60s
```

## Architecture
See [ARCHITECTURE.md](ARCHITECTURE.md) for the data-flow diagram, topic
contracts, and rationale behind the language picks per service.

## Development

This is a polyglot monorepo. Each service is independently buildable and
tested.

| Service | Build | Test |
|---|---|---|
| `services/generator` | `pip install -e .` | `pytest` |
| `services/ingest` | `go build ./...` | `go test ./...` |
| `services/parser` | `cargo build` | `cargo test` |
| `services/detector` | `pip install -e .` | `pytest` |
| `services/sink` | `go build ./...` | `go test ./...` |

CI (`.github/workflows/ci.yml`) runs lint + test matrix for Go, Rust,
and Python on every push to `main` and on pull requests.

## License
MIT. Copyright (c) 2026 @dSofikitis.
