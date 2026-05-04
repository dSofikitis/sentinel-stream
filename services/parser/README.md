# sentinel-parser

The CPU-bound stage. Takes `events.raw` payloads, parses the
authoritative timestamp, classifies the event, normalizes severity,
extracts entity fields (host, user, src/dst IP+port), and emits
`events.enriched` payloads matching `schemas/event.enriched.schema.json`.

Written in Rust because parsing dominates the per-event cost path; the
rest of the pipeline is IO-bound.

## What it does (per event)

1. Reads RFC 3339 from `raw["@timestamp"]` if present, else
   `received_at`. Rejects events with no parseable timestamp.
2. Classifies into `auth | network | dns | process | file | other` —
   first by an explicit `raw.event_class`, then by source-name
   keyword (`auth`, `firewall`, `dns`, ...).
3. Normalizes severity (warn → warning, crit → critical, ...) into
   the syslog scale.
4. Lifts `host`, `user`, `src_ip`, `dst_ip`, `src_port`, `dst_port`
   from the raw payload onto the top-level enriched record.
5. Stamps `parser_version`.
6. Attaches an empty `geo` slot when `src_ip` is present so
   downstream consumers can rely on the field's existence; a real
   MMDB-backed lookup is a one-line addition behind the same
   `enrich` API.

## Run it

The binary is a stdin → stdout filter, which is enough to run the
whole pipeline as a Unix pipe:

```bash
cargo run --quiet --release < ../../data/sample-events.jsonl > /tmp/enriched.jsonl
```

End-to-end with the generator:

```bash
sentinel-generator --dry-run --rate 100 --duration 5 --seed 1 \
  | cargo run --quiet --release --manifest-path services/parser/Cargo.toml
```

The `enrich::enrich` function is the unit a Kafka consumer/producer
wraps when running against the live broker.
