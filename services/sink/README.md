# sentinel-sink

The persistence stage. Consumes `events.enriched` and `alerts` from
Redpanda and batch-inserts into ClickHouse so Grafana can query.

Implementation lands in phase 7. The current commit only ships a stub
to keep CI green.
