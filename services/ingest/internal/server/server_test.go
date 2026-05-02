package server

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/dSofikitis/sentinel-stream/ingest/internal/event"
	"github.com/dSofikitis/sentinel-stream/ingest/internal/producer"
)

type capturingProducer struct {
	events []event.RawEvent
	err    error
}

func (c *capturingProducer) Publish(_ context.Context, ev event.RawEvent) error {
	if c.err != nil {
		return c.err
	}
	c.events = append(c.events, ev)
	return nil
}

func (c *capturingProducer) Close() error { return nil }

var _ producer.Producer = (*capturingProducer)(nil)

func newTestHandler(prod producer.Producer) http.Handler {
	cfg := Config{
		NodeID: "test-node",
		Now:    func() time.Time { return time.Date(2026, 5, 2, 12, 0, 0, 0, time.UTC) },
	}
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	return New(cfg, prod, logger)
}

func TestHealth(t *testing.T) {
	handler := newTestHandler(&capturingProducer{})
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), `"status":"ok"`) {
		t.Fatalf("body = %q", rec.Body.String())
	}
}

func TestEvents_HappyPath(t *testing.T) {
	prod := &capturingProducer{}
	handler := newTestHandler(prod)
	body := bytes.NewBufferString(`{
        "tenant_id": "acme",
        "source": "auth-service",
        "raw": {"hello": "world"}
    }`)
	req := httptest.NewRequest(http.MethodPost, "/events", body)
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusAccepted {
		t.Fatalf("status = %d, want 202; body = %s", rec.Code, rec.Body.String())
	}
	if len(prod.events) != 1 {
		t.Fatalf("publish count = %d, want 1", len(prod.events))
	}
	got := prod.events[0]
	if got.TenantID != "acme" || got.Source != "auth-service" {
		t.Fatalf("unexpected event: %+v", got)
	}
	if got.IngestNodeID != "test-node" {
		t.Fatalf("node id = %q, want test-node", got.IngestNodeID)
	}
	if got.Transport != event.TransportHTTP {
		t.Fatalf("transport = %q, want http", got.Transport)
	}
	if got.EventID == "" {
		t.Fatalf("event id was not minted")
	}
	var responseBody map[string]string
	if err := json.NewDecoder(rec.Body).Decode(&responseBody); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if responseBody["event_id"] != got.EventID {
		t.Fatalf("response event_id %q != published %q", responseBody["event_id"], got.EventID)
	}
}

func TestEvents_BadJSON(t *testing.T) {
	handler := newTestHandler(&capturingProducer{})
	req := httptest.NewRequest(http.MethodPost, "/events", strings.NewReader(`{not-json`))
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", rec.Code)
	}
}

func TestEvents_MissingTenant(t *testing.T) {
	handler := newTestHandler(&capturingProducer{})
	req := httptest.NewRequest(http.MethodPost, "/events", strings.NewReader(`{"source":"x","raw":{}}`))
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "tenant_id") {
		t.Fatalf("body should mention tenant_id, got %q", rec.Body.String())
	}
}

func TestEvents_PublishError(t *testing.T) {
	prod := &capturingProducer{err: errFake("boom")}
	handler := newTestHandler(prod)
	req := httptest.NewRequest(
		http.MethodPost,
		"/events",
		strings.NewReader(`{"tenant_id":"acme","source":"auth","raw":{"k":1}}`),
	)
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusServiceUnavailable {
		t.Fatalf("status = %d, want 503", rec.Code)
	}
}

type errFake string

func (e errFake) Error() string { return string(e) }
