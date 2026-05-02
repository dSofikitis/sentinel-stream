package sink

import "testing"

func TestRouteAlert(t *testing.T) {
	rec := map[string]any{"kind": "sigma", "rule_id": "x"}
	if got := Route(rec); got != "alerts" {
		t.Fatalf("got %q, want alerts", got)
	}
}

func TestRouteEnriched(t *testing.T) {
	rec := map[string]any{"event_id": "e", "tenant_id": "acme"}
	if got := Route(rec); got != "events_enriched" {
		t.Fatalf("got %q, want events_enriched", got)
	}
}

func TestFlattenEnriched(t *testing.T) {
	in := map[string]any{
		"event_id": "e",
		"src_ip":   "203.0.113.1",
		"geo":      map[string]any{"country_code": "US", "city": "Reno"},
	}
	out := FlattenEnriched(in)
	if _, ok := out["geo"]; ok {
		t.Fatal("geo subobject should be removed")
	}
	if got, _ := out["geo_country"].(string); got != "US" {
		t.Fatalf("geo_country = %v", out["geo_country"])
	}
	if got, _ := out["geo_city"].(string); got != "Reno" {
		t.Fatalf("geo_city = %v", out["geo_city"])
	}
	if _, ok := in["geo"]; !ok {
		t.Fatal("input should not be mutated")
	}
}

func TestFlattenEnriched_NoGeo(t *testing.T) {
	in := map[string]any{"event_id": "e"}
	out := FlattenEnriched(in)
	if _, ok := out["geo_country"]; ok {
		t.Fatal("geo_country should not be set when geo is absent")
	}
}
