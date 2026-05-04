# demo-seed

A one-shot container that populates ClickHouse with realistic-looking
enriched events + alerts directly, so Grafana has something to render
without standing up the full streaming pipe.

It does **not** pretend to be the production pipeline. It runs:

1. The actual `sentinel_generator` event factories + attack scenarios.
2. A small Python re-implementation of the parser's enrichment so the
   seeder stays self-contained (no Rust toolchain needed at runtime).
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

## Relationship to the streaming pipeline

`demo-seed` writes to the same `events_enriched` / `alerts` ClickHouse
tables the streaming `sink` writes to, using the same row shapes. A
Grafana dashboard built against demo-seed data renders identically
when fed by the live pipeline.
