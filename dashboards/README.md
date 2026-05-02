# Grafana dashboards

Provisioned via the Compose stack (`deploy/compose`). Grafana picks
these up automatically through `provisioning/dashboards/sentinel.yml`
and connects to the ClickHouse datasource defined in
`provisioning/datasources/clickhouse.yml`.

| File | UID | Title | What it shows |
|---|---|---|---|
| `events-flow.json` | `ss-events` | SentinelStream — Events | 24h totals (events, distinct sources, distinct event classes), events/min by `event_class`, severity pie, top sources. |
| `alerts.json` | `ss-alerts` | SentinelStream — Alerts | 24h totals (count, sigma-vs-anomaly split, distinct rules, high/critical), alerts/min by kind, top firing rules, recent 50 alerts. |

To iterate on a dashboard live: edit it in Grafana, export JSON via
*Share → Export → Save to file*, replace the file in this directory,
and the next reload picks it up (provisioning watches every 30s).
