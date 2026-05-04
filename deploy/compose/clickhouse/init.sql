-- SentinelStream ClickHouse schema.
-- The sink writes events.enriched and alerts payloads here; Grafana
-- reads from these tables.

CREATE TABLE IF NOT EXISTS sentinel.events_enriched
(
    event_id        String,
    tenant_id       LowCardinality(String),
    source          LowCardinality(String),
    received_at     DateTime64(3, 'UTC'),
    ts              DateTime64(3, 'UTC'),
    event_class     LowCardinality(String),
    severity        LowCardinality(String),
    host            Nullable(String),
    user            Nullable(String),
    src_ip          Nullable(IPv4),
    dst_ip          Nullable(IPv4),
    src_port        Nullable(UInt16),
    dst_port        Nullable(UInt16),
    geo_country     Nullable(FixedString(2)),
    geo_city        Nullable(String),
    message         Nullable(String),
    parser_version  LowCardinality(String)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (tenant_id, event_class, ts, event_id)
TTL toDateTime(ts) + INTERVAL 30 DAY;

CREATE TABLE IF NOT EXISTS sentinel.alerts
(
    alert_id          String,
    tenant_id         LowCardinality(String),
    ts                DateTime64(3, 'UTC'),
    kind              LowCardinality(String),
    rule_id           Nullable(String),
    rule_title        Nullable(String),
    model             Nullable(String),
    score             Nullable(Float32),
    severity          LowCardinality(String),
    event_id          String,
    message           Nullable(String),
    detector_version  LowCardinality(String)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (tenant_id, severity, ts, alert_id)
TTL toDateTime(ts) + INTERVAL 90 DAY;
