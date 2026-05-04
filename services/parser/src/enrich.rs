//! Enrichment: takes a [`RawEvent`] and produces an [`EnrichedEvent`]
//! with normalized timestamp, classification, severity, and extracted
//! entity fields. The `geo` field is left as an empty placeholder so
//! downstream consumers can rely on the field's existence; an
//! MMDB-backed lookup is a one-line addition behind the same API.

use chrono::{DateTime, SecondsFormat, Utc};
use serde_json::Value;

use crate::event::{EnrichedEvent, EventClass, Geo, RawEvent, Severity};
use crate::PARSER_VERSION;

/// Errors surfaced by [`enrich`]. The caller decides whether to drop
/// the event or surface it as a poison-pill alert.
#[derive(Debug, PartialEq, Eq)]
pub enum EnrichError {
    /// `received_at` couldn't be parsed and `raw.@timestamp` is also
    /// missing/unparseable.
    NoTimestamp,
}

impl std::fmt::Display for EnrichError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NoTimestamp => write!(f, "no parseable timestamp on raw event"),
        }
    }
}

impl std::error::Error for EnrichError {}

/// Map a [`RawEvent`] to an [`EnrichedEvent`].
pub fn enrich(raw: &RawEvent) -> Result<EnrichedEvent, EnrichError> {
    let ts = parse_ts(raw)?;
    let event_class = classify(&raw.raw, &raw.source);
    let severity = severity(&raw.raw);

    Ok(attach_geo_placeholder(EnrichedEvent {
        event_id: raw.event_id.clone(),
        tenant_id: raw.tenant_id.clone(),
        source: raw.source.clone(),
        received_at: raw.received_at.clone(),
        ts,
        event_class,
        severity,
        host: string_field(&raw.raw, "host"),
        user: string_field(&raw.raw, "user"),
        src_ip: string_field(&raw.raw, "src_ip"),
        dst_ip: string_field(&raw.raw, "dst_ip"),
        src_port: u16_field(&raw.raw, "src_port"),
        dst_port: u16_field(&raw.raw, "dst_port"),
        geo: None, // GeoIP enrichment lands in a follow-up phase.
        message: string_field(&raw.raw, "message"),
        parser_version: PARSER_VERSION.to_string(),
    }))
}

fn attach_geo_placeholder(mut e: EnrichedEvent) -> EnrichedEvent {
    if e.src_ip.is_some() {
        e.geo = Some(Geo {
            country_code: None,
            city: None,
        });
    }
    e
}

fn parse_ts(raw: &RawEvent) -> Result<String, EnrichError> {
    if let Some(ts) = raw.raw.get("@timestamp").and_then(Value::as_str) {
        if let Ok(parsed) = DateTime::parse_from_rfc3339(ts) {
            return Ok(parsed
                .with_timezone(&Utc)
                .to_rfc3339_opts(SecondsFormat::Millis, true));
        }
    }
    if let Ok(parsed) = DateTime::parse_from_rfc3339(&raw.received_at) {
        return Ok(parsed
            .with_timezone(&Utc)
            .to_rfc3339_opts(SecondsFormat::Millis, true));
    }
    Err(EnrichError::NoTimestamp)
}

fn classify(raw: &Value, source: &str) -> EventClass {
    if let Some(s) = raw.get("event_class").and_then(Value::as_str) {
        return match s.to_ascii_lowercase().as_str() {
            "auth" => EventClass::Auth,
            "network" => EventClass::Network,
            "dns" => EventClass::Dns,
            "process" => EventClass::Process,
            "file" => EventClass::File,
            _ => EventClass::Other,
        };
    }
    let s = source.to_ascii_lowercase();
    if s.contains("auth") || s.contains("login") || s.contains("ssh") {
        EventClass::Auth
    } else if s.contains("firewall") || s.contains("net") {
        EventClass::Network
    } else if s.contains("dns") {
        EventClass::Dns
    } else {
        EventClass::Other
    }
}

fn severity(raw: &Value) -> Severity {
    let s = raw
        .get("severity")
        .and_then(Value::as_str)
        .unwrap_or("info")
        .to_ascii_lowercase();
    match s.as_str() {
        "debug" => Severity::Debug,
        "info" | "informational" => Severity::Info,
        "notice" => Severity::Notice,
        "warn" | "warning" => Severity::Warning,
        "err" | "error" => Severity::Error,
        "crit" | "critical" => Severity::Critical,
        "alert" => Severity::Alert,
        "emerg" | "emergency" => Severity::Emergency,
        _ => Severity::Info,
    }
}

fn string_field(raw: &Value, key: &str) -> Option<String> {
    raw.get(key).and_then(Value::as_str).map(|s| s.to_string())
}

fn u16_field(raw: &Value, key: &str) -> Option<u16> {
    raw.get(key)
        .and_then(Value::as_u64)
        .and_then(|n| u16::try_from(n).ok())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn raw_event(payload: Value) -> RawEvent {
        RawEvent {
            event_id: "e-1".into(),
            tenant_id: "acme".into(),
            source: "auth-service".into(),
            received_at: "2026-05-02T12:00:00Z".into(),
            ingest_node_id: "node-1".into(),
            transport: Some("http".into()),
            raw: payload,
        }
    }

    #[test]
    fn classify_uses_explicit_field() {
        let r = raw_event(json!({"event_class": "dns"}));
        let e = enrich(&r).unwrap();
        assert_eq!(e.event_class, EventClass::Dns);
    }

    #[test]
    fn classify_falls_back_to_source_keyword() {
        let mut r = raw_event(json!({}));
        r.source = "edge-firewall".into();
        let e = enrich(&r).unwrap();
        assert_eq!(e.event_class, EventClass::Network);
    }

    #[test]
    fn severity_normalized() {
        let r = raw_event(json!({"severity": "WARN"}));
        let e = enrich(&r).unwrap();
        assert_eq!(e.severity, Severity::Warning);
    }

    #[test]
    fn extracts_host_user_ips_ports() {
        let r = raw_event(json!({
            "host": "api-1",
            "user": "alice",
            "src_ip": "203.0.113.10",
            "dst_ip": "10.0.0.5",
            "src_port": 51514,
            "dst_port": 22
        }));
        let e = enrich(&r).unwrap();
        assert_eq!(e.host.as_deref(), Some("api-1"));
        assert_eq!(e.user.as_deref(), Some("alice"));
        assert_eq!(e.src_ip.as_deref(), Some("203.0.113.10"));
        assert_eq!(e.dst_ip.as_deref(), Some("10.0.0.5"));
        assert_eq!(e.src_port, Some(51514));
        assert_eq!(e.dst_port, Some(22));
    }

    #[test]
    fn ts_prefers_inner_timestamp() {
        let r = raw_event(json!({"@timestamp": "2026-05-02T10:00:00Z"}));
        let e = enrich(&r).unwrap();
        assert!(e.ts.starts_with("2026-05-02T10:00:00"));
    }

    #[test]
    fn ts_falls_back_to_received_at() {
        let r = raw_event(json!({}));
        let e = enrich(&r).unwrap();
        assert!(e.ts.starts_with("2026-05-02T12:00:00"));
    }

    #[test]
    fn ts_error_when_neither_parseable() {
        let mut r = raw_event(json!({}));
        r.received_at = "not-a-date".into();
        assert!(matches!(enrich(&r), Err(EnrichError::NoTimestamp)));
    }

    #[test]
    fn geo_present_when_src_ip_present() {
        let r = raw_event(json!({"src_ip": "203.0.113.10"}));
        let e = enrich(&r).unwrap();
        assert!(e.geo.is_some());
    }

    #[test]
    fn geo_absent_when_no_src_ip() {
        let r = raw_event(json!({}));
        let e = enrich(&r).unwrap();
        assert!(e.geo.is_none());
    }
}
