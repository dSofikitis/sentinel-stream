# Grafana dashboards

Provisioned dashboards (JSON) and the ClickHouse datasource config.
Loaded automatically by the Grafana container in `deploy/compose`.

Dashboards land in phase 8:
- `events-flow.json` — ingest rate, parser lag, severity histogram.
- `alerts.json` — active rule firings, top sources, MTTR.
