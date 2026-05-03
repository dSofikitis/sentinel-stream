# SentinelStream

> **Sentinel** — a guard standing watch. **Stream** — events flowing past it.

A real-time security-event detection pipeline. Events flow through a
multi-language streaming graph that ingests, parses, enriches,
detects, and persists at sustained throughput, with Sigma-rule and
ML-driven detection running side by side.

## What this is for

The same shape every SOC product (Splunk, Elastic Security, Wazuh,
Datadog Security) is built on: **log sources → ingest → parse/enrich
→ detect → store → visualize.** SentinelStream implements that whole
loop end-to-end as a learning + portfolio piece, with the
architectural seams that let it scale.

| Capability | Where it shows up |
|---|---|
| **Multi-language systems work** | Go on the IO-heavy edges (ingest, sink); Rust on the CPU-bound parsing stage; Python on the ML/orchestration stages (detector, generator). |
| **Streaming architecture** | Kafka-protocol broker (Redpanda) with three explicit topic contracts under `schemas/`: `events.raw` → `events.enriched` → `alerts`. |
| **Detection engineering** | Both layers a real SOC needs: declarative **Sigma** rules (the open standard, `sigma/*.yml`) and an **Isolation Forest** anomaly model, behind a clean abstraction so either side can be swapped. |
| **Time-series analytics** | ClickHouse column-store schemas with month-partitioning and TTLs (`deploy/compose/clickhouse/init.sql`); Grafana with two provisioned dashboards. |
| **Production hygiene** | JSON Schema contracts between services, parallel CI matrix (Go / Rust / Python), distroless Dockerfiles, structured (slog/structlog) logs, weekly Dependabot across all six ecosystems. |

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
| `generator` | Python | Replays a corpus or emits synthetic auth / network / dns events at a configurable rate, with optional attack scenarios. |
| `ingest` | Go | `POST /events` HTTP API; validates and produces a stamped `RawEvent`. |
| `parser` | Rust | Parses timestamps, classifies, normalizes severity, extracts entity fields; produces `EnrichedEvent`. |
| `detector` | Python | Sigma rule engine + Isolation Forest anomaly model; emits `Alert`s. |
| `sink` | Go | Batches `EnrichedEvent`s and `Alert`s into ClickHouse over HTTP `JSONEachRow`. |
| `demo-seed` | Python (one-shot) | Populates ClickHouse directly so Grafana renders before the v0.2 broker integration lands. |

Backbone: **Redpanda** (Kafka API), **ClickHouse**, **Grafana** with
two pre-baked dashboards (Events + Alerts).

## Status (v0.1)

Everything below works today. The pipeline can run **as a Unix
pipe** (no broker required) for local development:

```bash
sentinel-generator --dry-run --rate 50 --duration 5 --inject brute_force_ssh \
  | sentinel-parser \
  | sentinel-detector --rules ./sigma \
  | sentinel-sink
```

Each stage is an independent binary with its own tests and
Dockerfile. The Compose stack stands up Redpanda + ClickHouse +
Grafana alongside the `ingest` HTTP service. The Kafka-backed
consumer/producer wiring on `parser`, `detector`, and `sink` lands
in v0.2; for now `make seed-grafana` populates ClickHouse via the
`demo-seed` one-shot so the dashboards have something to render.

## Quickstart

```bash
make compose-up        # redpanda + clickhouse + grafana + ingest
make seed-grafana      # 600 enriched events + ~200 alerts straight into ClickHouse
```

Open Grafana at <http://localhost:3000> (admin / admin) → *Dashboards*
→ *SentinelStream* folder. **Set the time picker to "Last 3 hours"**
or wider; the seeder spreads events across that window.

## Sending real events through `ingest`

The `ingest` service speaks plain HTTP. Examples live in
[`examples/`](examples/):

```bash
# Single auth success event
curl -X POST http://localhost:8080/events \
  -H 'Content-Type: application/json' \
  -d @examples/payloads/auth-success.json

# Reply: {"event_id":"<uuid v4 minted by ingest>"}
```

A whole batch of canned events:

```bash
bash examples/curl/post-all.sh
```

A scripted attack burst:

```bash
bash examples/curl/brute-force-ssh.sh   # 12 failed SSH logins + a final success
bash examples/curl/port-scan.sh         # 25 distinct dst-port drops from one IP
```

Or run the synthetic generator inside a container at any rate /
duration:

```bash
docker compose -f deploy/compose/docker-compose.yml \
  --profile tools run --rm generator \
  --target http://ingest:8080/events \
  --rate 50 --duration 30 --inject brute_force_ssh
```

Watch ingest's stdout to confirm events land:

```bash
make compose-logs   # or: docker compose ... logs -f ingest
```

## Architecture
See [ARCHITECTURE.md](ARCHITECTURE.md) for the data-flow diagram, topic
contracts, and rationale behind each language pick.

## Development

Polyglot monorepo. Each service builds and tests independently.

| Service | Build | Test |
|---|---|---|
| `services/generator` | `pip install -e .` | `pytest` |
| `services/ingest` | `go build ./...` | `go test ./...` |
| `services/parser` | `cargo build` | `cargo test` |
| `services/detector` | `pip install -e .` | `pytest` |
| `services/sink` | `go build ./...` | `go test ./...` |

Top-level `make help` lists targets; CI
(`.github/workflows/ci.yml`) runs the same lint + test matrix on
every push to `main` and every PR.

## License
MIT. Copyright (c) 2026 @dSofikitis.
