//! Wire types for events.raw (input) and events.enriched (output).
//! Mirrors schemas/event.raw.schema.json and event.enriched.schema.json.

use serde::{Deserialize, Serialize};
use serde_json::Value;

/// What we read off events.raw.
#[derive(Debug, Clone, Deserialize)]
pub struct RawEvent {
    pub event_id: String,
    pub tenant_id: String,
    pub source: String,
    pub received_at: String,
    pub ingest_node_id: String,
    #[serde(default)]
    pub transport: Option<String>,
    pub raw: Value,
}

/// What we write to events.enriched.
#[derive(Debug, Clone, Serialize)]
pub struct EnrichedEvent {
    pub event_id: String,
    pub tenant_id: String,
    pub source: String,
    pub received_at: String,
    pub ts: String,
    pub event_class: EventClass,
    pub severity: Severity,

    pub host: Option<String>,
    pub user: Option<String>,
    pub src_ip: Option<String>,
    pub dst_ip: Option<String>,
    pub src_port: Option<u16>,
    pub dst_port: Option<u16>,

    pub geo: Option<Geo>,

    pub message: Option<String>,
    pub parser_version: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum EventClass {
    Auth,
    Network,
    Dns,
    Process,
    File,
    Other,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum Severity {
    Debug,
    Info,
    Notice,
    Warning,
    Error,
    Critical,
    Alert,
    Emergency,
}

#[derive(Debug, Clone, Serialize)]
pub struct Geo {
    pub country_code: Option<String>,
    pub city: Option<String>,
}
