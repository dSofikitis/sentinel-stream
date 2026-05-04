# deploy/compose

The full SentinelStream data plane via Docker Compose: broker,
column store, ingest, and dashboards.

| Service | Image | Ports | Notes |
|---|---|---|---|
| `redpanda` | `redpandadata/redpanda` | 9092 (Kafka), 8082 (HTTP), 9644 (admin) | Kafka-API broker. |
| `redpanda-init` | `redpandadata/redpanda` | — | One-shot job: creates `events.raw`, `events.enriched`, `alerts` topics. |
| `clickhouse` | `clickhouse/clickhouse-server:24.8` | 8123 (HTTP), 9000 (native) | Schema seeded from `clickhouse/init.sql`. |
| `grafana` | `grafana/grafana:11.2.0` | 3000 | ClickHouse plugin + datasource provisioned; dashboards mounted from `dashboards/`. |
| `ingest` | built locally | 8080 | Go HTTP `POST /events` endpoint. |
| `generator` | built locally (`tools` profile) | — | Synthetic event source; on-demand. |
| `demo-seed` | built locally (`tools` profile) | — | One-shot ClickHouse seeder for dashboard demos. |

Bring it up:

```bash
docker compose -f deploy/compose/docker-compose.yml up -d
docker compose -f deploy/compose/docker-compose.yml logs -f redpanda-init   # confirm topics created
```

Open Grafana at <http://localhost:3000> (admin / admin). The
ClickHouse datasource and the *SentinelStream — Events* /
*SentinelStream — Alerts* dashboards are auto-provisioned.

ClickHouse query check:

```bash
curl -u sentinel:sentinel \
  "http://localhost:8123/?query=SHOW%20TABLES%20FROM%20sentinel"
# events_enriched
# alerts
```
