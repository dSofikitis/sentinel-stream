package producer

import (
	"bytes"
	"context"
	"encoding/json"
	"strings"
	"testing"

	"github.com/dSofikitis/sentinel-stream/ingest/internal/event"
)

func TestStdoutProducer_PublishWritesJSONLine(t *testing.T) {
	var buf bytes.Buffer
	p := NewStdoutProducer(&buf)
	ev := event.RawEvent{
		EventID:      "abc",
		TenantID:     "acme",
		Source:       "auth",
		ReceivedAt:   "2026-05-02T12:00:00Z",
		IngestNodeID: "node-1",
		Transport:    event.TransportHTTP,
		Raw:          json.RawMessage(`{"k":"v"}`),
	}
	if err := p.Publish(context.Background(), ev); err != nil {
		t.Fatalf("publish: %v", err)
	}
	if p.Count() != 1 {
		t.Fatalf("count = %d, want 1", p.Count())
	}
	out := buf.String()
	if !strings.HasSuffix(out, "\n") {
		t.Fatalf("output should end with newline, got %q", out)
	}
	var got event.RawEvent
	if err := json.Unmarshal([]byte(strings.TrimRight(out, "\n")), &got); err != nil {
		t.Fatalf("unmarshal output: %v", err)
	}
	if got.EventID != ev.EventID || got.TenantID != ev.TenantID {
		t.Fatalf("round-trip mismatch: %+v", got)
	}
}

func TestStdoutProducer_ConcurrentPublishesAreLine(t *testing.T) {
	var buf bytes.Buffer
	p := NewStdoutProducer(&buf)
	const n = 50
	done := make(chan struct{})
	for i := 0; i < n; i++ {
		go func() {
			defer func() { done <- struct{}{} }()
			_ = p.Publish(context.Background(), event.RawEvent{
				EventID:      "x",
				TenantID:     "t",
				Source:       "s",
				ReceivedAt:   "now",
				IngestNodeID: "n",
				Transport:    event.TransportHTTP,
				Raw:          json.RawMessage(`{}`),
			})
		}()
	}
	for i := 0; i < n; i++ {
		<-done
	}
	if got := p.Count(); got != n {
		t.Fatalf("count = %d, want %d", got, n)
	}
	// Each output line must be parseable JSON: this catches torn writes.
	for i, line := range strings.Split(strings.TrimRight(buf.String(), "\n"), "\n") {
		var ev event.RawEvent
		if err := json.Unmarshal([]byte(line), &ev); err != nil {
			t.Fatalf("line %d not valid JSON: %v", i, err)
		}
	}
}
