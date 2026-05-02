# sentinel-ingest

Edge of the pipeline. Receives raw security events over HTTP
(`POST /events`) and a syslog UDP listener, validates against
`schemas/event.raw.schema.json`, and produces them to the
`events.raw` Redpanda topic.

Implementation lands in phase 4. The current commit only ships a stub
to keep CI green.
