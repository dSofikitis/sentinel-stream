// Package producer abstracts the egress of the ingest service. The
// stdout implementation is the default during early phases; a real
// Kafka/Redpanda producer slots in behind the same Producer interface.
package producer

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"sync"
	"sync/atomic"

	"github.com/dSofikitis/sentinel-stream/ingest/internal/event"
)

// Producer publishes events.raw payloads to the broker.
type Producer interface {
	Publish(ctx context.Context, ev event.RawEvent) error
	Close() error
}

// StdoutProducer writes one JSON line per event to the supplied
// writer. Useful for local runs and tests.
type StdoutProducer struct {
	mu     sync.Mutex
	w      io.Writer
	count  atomic.Uint64
}

// NewStdoutProducer returns a Producer that writes to w. Pass os.Stdout
// for the default behaviour.
func NewStdoutProducer(w io.Writer) *StdoutProducer {
	return &StdoutProducer{w: w}
}

// Publish writes the event as a JSON line.
func (p *StdoutProducer) Publish(_ context.Context, ev event.RawEvent) error {
	payload, err := json.Marshal(ev)
	if err != nil {
		return fmt.Errorf("marshal event: %w", err)
	}
	p.mu.Lock()
	defer p.mu.Unlock()
	if _, err := p.w.Write(append(payload, '\n')); err != nil {
		return fmt.Errorf("write event: %w", err)
	}
	p.count.Add(1)
	return nil
}

// Count returns the number of events successfully published.
func (p *StdoutProducer) Count() uint64 { return p.count.Load() }

// Close is a no-op for stdout but satisfies the interface.
func (p *StdoutProducer) Close() error { return nil }
