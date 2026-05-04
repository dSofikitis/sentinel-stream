# sentinel-ingest

Edge of the pipeline. Accepts security events over HTTP, validates,
mints `event_id` / `received_at` / `ingest_node_id`, and publishes
them downstream.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness probe; `{"status":"ok"}`. |
| POST | `/events` | Accepts an `Inbound` event. Returns `202` with `{"event_id":"..."}`. |

`Inbound` schema (the bits the caller fills in):

```json
{
  "tenant_id": "acme",
  "source": "auth-service",
  "transport": "http",          // optional; ingest defaults to http
  "event_id": "...",            // optional; minted if absent
  "raw": { "...": "..." }       // free-form
}
```

The server fills in `event_id` (UUID v4 if missing), `received_at`
(RFC 3339 UTC), `ingest_node_id`, and `transport=http`, then publishes
the resulting `RawEvent` to the configured producer.

## Producer pluggability

`internal/producer.Producer` is the publisher seam. The default
build wires the `StdoutProducer` (one JSON line per event, written
to stdout) so the service runs with no external dependencies — easy
to compose into a Unix pipe and trivial to test. A `KafkaProducer`
(franz-go against Redpanda) slots in behind the same interface
without touching the HTTP path.

## Run it

Locally:

```bash
go run ./...
# in another shell
curl -s -X POST http://localhost:8080/events \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id":"acme","source":"auth","raw":{"hello":"world"}}'
```

Via Compose:

```bash
docker compose -f deploy/compose/docker-compose.yml up -d ingest
docker compose -f deploy/compose/docker-compose.yml logs -f ingest
```

## Configuration

| Env var | Default | Notes |
|---|---|---|
| `INGEST_ADDR` | `:8080` | HTTP listen address. |
| `INGEST_NODE_ID` | hostname | Stamped onto every event for traceability. |
