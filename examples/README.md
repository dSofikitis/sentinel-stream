# Examples

Concrete payloads and one-line scripts for talking to the running
`ingest` service. Pair these with the rest of the demo:

```bash
make compose-up                 # bring up redpanda + clickhouse + grafana + ingest
bash examples/curl/post-all.sh  # send one of every event class
make seed-grafana               # bulk-seed ClickHouse for Grafana
```

## Layout

| Path | What's inside |
|---|---|
| `payloads/*.json` | Inbound payloads matching `Inbound` in `services/ingest/internal/event`. The ingest service validates them, mints `event_id` / `received_at` / `ingest_node_id` / `transport`, and produces a `RawEvent`. |
| `curl/*.sh` | Shell scripts that POST one or more payloads to `http://localhost:8080/events`. Override the host with `INGEST=...` if you're hitting a remote box. |

## Payloads

| File | Class | Outcome / action | Notes |
|---|---|---|---|
| `auth-success.json` | auth | success | Single successful login. |
| `auth-failure.json` | auth | failure | Single failed SSH login. Combined with the brute-force script, will fire `ssh_login_failure`. |
| `firewall-drop.json` | network | drop | Drop to a privileged port; fires `fw_drop_public_to_priv_port`. |
| `firewall-accept.json` | network | accept | Allow to 443; doesn't fire any rule. |
| `dns-suspicious-tld.json` | dns | (n/a) | Query for a `.zip` domain; fires `dns_query_suspicious_tld`. |
| `dns-clean.json` | dns | (n/a) | Query for `cloudflare.com`; doesn't fire. |

## Scripts

| Script | What it does |
|---|---|
| `post-all.sh` | One event per payload file, sequentially. |
| `brute-force-ssh.sh` | 12 failed SSH logins + a final success, all from `203.0.113.66` on user `root`. Mirrors the generator's `brute_force_ssh` scenario. |
| `port-scan.sh` | 25 distinct destination-port drops from a single source IP. Mirrors the generator's `port_scan` scenario. |

All scripts default to `INGEST=http://localhost:8080`. Override:

```bash
INGEST=http://my-host:8080 bash examples/curl/post-all.sh
```
