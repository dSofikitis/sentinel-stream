# Schemas

JSON Schema files defining the contracts between pipeline stages.
Treated as the single source of truth — every service that produces
or consumes these topics validates against the same file.

- [`event.raw.schema.json`](event.raw.schema.json) — what the ingest
  layer publishes.
- [`event.enriched.schema.json`](event.enriched.schema.json) — what
  the parser publishes.
- [`alert.schema.json`](alert.schema.json) — what the detector
  publishes.
