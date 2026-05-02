# deploy/compose

The full SentinelStream stack via Docker Compose.

## What's in this commit (phase 2)

Datastores + Grafana wired up; services join in their own phases.

| Service | Image | Ports | Notes |
|---|---|---|---|
| `redpanda` | `redpandadata/redpanda` | 9092 (Kafka), 8082 (HTTP), 9644 (admin) | Kafka-API broker. |
| `redpanda-init` | `redpandadata/redpanda` | — | One-shot job: creates `events.raw`, `events.enriched`, `alerts` topics. |
| `clickhouse` | `clickhouse/clickhouse-server:24.8` | 8123 (HTTP), 9000 (native) | Schema seeded from `clickhouse/init.sql`. |
| `grafana` | `grafana/grafana:11.2.0` | 3000 | ClickHouse plugin + datasource provisioned; dashboards mounted from `dashboards/`. |

Bring it up:

```bash
docker compose -f deploy/compose/docker-compose.yml up -d
docker compose -f deploy/compose/docker-compose.yml logs -f redpanda-init   # confirm topics created
```

Open Grafana at <http://localhost:3000> (admin / admin). The
ClickHouse datasource is preconfigured. Dashboards land in phase 8.

ClickHouse query check:

```bash
curl -u sentinel:sentinel \
  "http://localhost:8123/?query=SHOW%20TABLES%20FROM%20sentinel"
# events_enriched
# alerts
```

## What's coming
- Phase 3: `generator` Python service joins.
- Phase 4: `ingest` Go service joins, starts producing to `events.raw`.
- Phase 5: `parser` Rust service joins.
- Phase 6: `detector` Python service joins.
- Phase 7: `sink` Go service joins, starts persisting to ClickHouse.
- Phase 8: dashboards drop into `dashboards/` and auto-load.
