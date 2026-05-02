package sink

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestInsertBatchPostsJSONEachRow(t *testing.T) {
	var seen struct {
		query string
		body  string
	}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		seen.query = r.URL.Query().Get("query")
		buf, _ := io.ReadAll(r.Body)
		seen.body = string(buf)
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	client := NewClickHouse(srv.URL, "sentinel", "u", "p")
	rows := []map[string]any{
		{"a": 1, "b": "x"},
		{"a": 2, "b": "y"},
	}
	n, err := client.InsertBatch(context.Background(), "events_enriched", rows)
	if err != nil {
		t.Fatalf("InsertBatch error: %v", err)
	}
	if n != 2 {
		t.Fatalf("n = %d, want 2", n)
	}
	if !strings.Contains(seen.query, "INSERT INTO sentinel.events_enriched FORMAT JSONEachRow") {
		t.Fatalf("query = %q", seen.query)
	}
	if !strings.Contains(seen.body, `"a":1`) || !strings.Contains(seen.body, `"a":2`) {
		t.Fatalf("body missing rows: %q", seen.body)
	}
}

func TestInsertBatchEmptyShortCircuit(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(_ http.ResponseWriter, _ *http.Request) {
		t.Fatal("server should not be called for an empty batch")
	}))
	defer srv.Close()
	client := NewClickHouse(srv.URL, "sentinel", "", "")
	if n, err := client.InsertBatch(context.Background(), "events_enriched", nil); err != nil || n != 0 {
		t.Fatalf("InsertBatch(nil) = (%d, %v); want (0, nil)", n, err)
	}
}

func TestInsertBatchSurfacesUpstreamErrors(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusBadRequest)
		_, _ = w.Write([]byte("Code: 60. DB::Exception: Unknown table"))
	}))
	defer srv.Close()
	client := NewClickHouse(srv.URL, "sentinel", "", "")
	_, err := client.InsertBatch(context.Background(), "nope", []map[string]any{{"a": 1}})
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !strings.Contains(err.Error(), "clickhouse 400") {
		t.Fatalf("unexpected error: %v", err)
	}
}
