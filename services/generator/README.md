# sentinel-generator

Posts synthetic security events to the `ingest` service at a
controlled rate. Used to drive the pipeline during demos and load
tests.

## Run it

Dry-run (prints JSONL to stdout, useful before `ingest` exists):

```bash
sentinel-generator --dry-run --rate 20 --duration 5 --seed 42
```

Against a running ingest:

```bash
sentinel-generator --target http://localhost:8080/events --rate 50 --duration 60
```

Inject an attack scenario alongside normal traffic so downstream
detections have something to fire on:

```bash
sentinel-generator --inject brute_force_ssh --inject port_scan --duration 30
```

## Via Compose

The generator joins the stack under the `tools` profile so it doesn't
auto-start with `docker compose up`. Run it on demand:

```bash
docker compose -f deploy/compose/docker-compose.yml \
  --profile tools run --rm generator \
  --target http://ingest:8080/events --rate 100 --duration 60
```

## Event classes

- `auth` — login success/failure with user, host, src_ip.
- `network` — firewall accept/drop with src/dst_ip + dst_port.
- `dns` — A-record query against a small list of public domains.

## Scenarios

- `brute_force_ssh` — N failed SSH logins for one user from one IP,
  then a success.
- `port_scan` — single source hammering many distinct destination
  ports.

Add new scenarios in `src/sentinel_generator/scenarios.py` and
register them in the `SCENARIOS` dict.
