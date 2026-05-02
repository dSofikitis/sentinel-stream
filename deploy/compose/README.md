# deploy/compose

`docker-compose.yml` for the full SentinelStream stack: Redpanda,
ClickHouse, Grafana, and the five services from `services/`.

Lands in phase 2 (datastores wired up first), then services are
added one phase at a time.
