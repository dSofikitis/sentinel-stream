# Contributing

Polyglot monorepo. Each service in `services/` is independently
buildable and tested with its own toolchain.

## Quick start

From the repo root:

```bash
make help        # list every target
make build       # build all services
make test        # run all tests
make lint        # ruff + go vet + cargo clippy + cargo fmt
make compose-up  # bring up redpanda + clickhouse + grafana + ingest
```

Per-service workflow lives in each service's README:

| Service | Toolchain | Where |
|---|---|---|
| `generator`, `detector` | Python ≥ 3.11 | `services/<name>/` (pyproject) |
| `ingest`, `sink` | Go ≥ 1.23 | `services/<name>/` (go.mod) |
| `parser` | Rust stable | `services/parser/` (Cargo.toml) |

## Branches and PRs

- One logical change per commit; small PRs land faster.
- The PR template asks for a short summary, the services touched,
  and a test plan (manual or `make test`).
- CI (`.github/workflows/ci.yml`) runs lint + test in a parallel
  matrix across Go, Rust, and Python on every push to `main` and
  every PR. Keep all jobs green.

## Adding a new Sigma rule

Drop a `.yml` file in `sigma/`. The detector picks it up on next
start. Rules must use the subset documented in
`services/detector/src/sentinel_detector/sigma.py`:

- Multiple named selections under `detection`.
- Flat `{field: value}` (or list-as-OR) selections.
- Modifiers: `contains`, `startswith`, `endswith`, `gte`, `lte`.
- `condition` over selection names with `and` / `or` / `not`.

Anything richer should land via a follow-up that wraps pysigma's
backend pipeline.

## Adding a new event class or schema field

Edit `schemas/event.{raw,enriched}.schema.json` first — those files
are the contract between services. Then update the parser's
`EventClass` / extraction logic, the detector's featurizer if it
matters for anomalies, the sink's ClickHouse schema in
`deploy/compose/clickhouse/init.sql`, and the dashboards.

## Adding a new service language

If you introduce a fourth language (e.g. for a UI), add a CI job to
`.github/workflows/ci.yml` and per-target rules to the top-level
`Makefile`. Make sure the tests are runnable in CI without external
network access beyond `pip` / `cargo` / `go mod download`.
