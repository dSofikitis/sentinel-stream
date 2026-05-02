package sink

// Route classifies a parsed JSON record. An alert payload has a
// "kind" field (sigma|anomaly); enriched events do not.
func Route(rec map[string]any) string {
	if _, ok := rec["kind"]; ok {
		return "alerts"
	}
	return "events_enriched"
}

// FlattenEnriched lifts the geo sub-object onto top-level columns
// matching the ClickHouse schema (geo_country, geo_city). Returns a
// fresh map; the input is not mutated.
func FlattenEnriched(rec map[string]any) map[string]any {
	out := make(map[string]any, len(rec)+1)
	for k, v := range rec {
		if k == "geo" {
			continue
		}
		out[k] = v
	}
	if geo, ok := rec["geo"].(map[string]any); ok {
		if v, ok := geo["country_code"]; ok {
			out["geo_country"] = v
		}
		if v, ok := geo["city"]; ok {
			out["geo_city"] = v
		}
	}
	return out
}
