# sentinel-sink

The persistence stage. Reads JSONL from stdin (mixed
`events.enriched` payloads and `alerts` payloads), routes each line
to the right ClickHouse table, batches by size + time, and inserts
via ClickHouse's HTTP `JSONEachRow` interface.

## Routing

Records carrying a `kind` field (`sigma` | `anomaly`) are written to
`sentinel.alerts`; everything else is treated as an enriched event
and written to `sentinel.events_enriched`. The `geo` sub-object is
flattened into `geo_country` / `geo_city` columns to match the
ClickHouse schema in `deploy/compose/clickhouse/init.sql`.

## Run it

End-to-end as a Unix pipe:

```bash
sentinel-generator --dry-run --rate 50 --duration 5 \
  | sentinel-parser \
  | sentinel-detector --rules ./sigma \
  | sentinel-sink
```

## Configuration

| Env var | Default | Notes |
|---|---|---|
| `CLICKHOUSE_URL` | `http://clickhouse:8123` | HTTP base URL (no trailing path). |
| `CLICKHOUSE_DB` | `sentinel` | |
| `CLICKHOUSE_USER` | `sentinel` | Empty disables BasicAuth. |
| `CLICKHOUSE_PASSWORD` | `sentinel` | |
| `SINK_BATCH_SIZE` | `100` | Rows per insert per table. |
| `SINK_FLUSH_MS` | `1000` | Forced flush interval, in ms. |
