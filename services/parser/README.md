# sentinel-parser

The CPU-bound stage. Consumes `events.raw`, parses timestamps,
extracts `src_ip` / `dst_ip` / `host` / `user`, runs GeoIP enrichment,
classifies events (auth / network / dns / ...), and produces to
`events.enriched`.

Written in Rust because parsing and regex enrichment dominate the
per-event cost path; the rest of the pipeline is IO-bound.

Implementation lands in phase 5. The current commit only ships a stub
to keep CI green.
