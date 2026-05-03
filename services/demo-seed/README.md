# demo-seed

A one-shot container that populates ClickHouse with realistic-looking
enriched events + alerts so Grafana has something to render *before*
the v0.2 broker integration lands.

It does **not** pretend to be the production pipeline. It runs:

1. The actual `sentinel_generator` event factories + attack scenarios.
2. A small Python re-implementation of the parser's enrichment
   (the Rust binary needs a Kafka backend before it joins the live
   stack — that's deferred to v0.2).
3. The actual `sentinel_detector` Sigma engine + Isolation Forest.
4. Direct batch inserts into ClickHouse via HTTP `JSONEachRow`.

## Run it

```bash
docker compose -f deploy/compose/docker-compose.yml \
  --profile tools run --rm demo-seed
```

…or via the Makefile:

```bash
make seed-grafana
```

Defaults: 600 events spread across the last 3 hours, brute-force SSH
+ port-scan scenarios injected, anomaly threshold 0.65. Tweak with
`--rows N`, `--minutes-back N`, `--no-anomaly`, etc.

## When the real pipeline is here

This container goes away in v0.2 — the same `events_enriched` /
`alerts` rows will arrive via the broker, and Grafana keeps working
without changes.
