// Package event defines the RawEvent contract that the ingest service
// produces onto the events.raw topic. It mirrors
// schemas/event.raw.schema.json — keep them in sync.
package event

import (
	"crypto/rand"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"
)

// Transport enumerates the accepted ingest channels.
type Transport string

const (
	TransportHTTP   Transport = "http"
	TransportSyslog Transport = "syslog"
)

// RawEvent is the on-the-wire shape published to the events.raw topic.
type RawEvent struct {
	EventID      string          `json:"event_id"`
	TenantID     string          `json:"tenant_id"`
	Source       string          `json:"source"`
	ReceivedAt   string          `json:"received_at"`
	IngestNodeID string          `json:"ingest_node_id"`
	Transport    Transport       `json:"transport"`
	Raw          json.RawMessage `json:"raw"`
}

// Inbound is the payload accepted by the ingest layer. event_id /
// received_at / ingest_node_id / transport are minted by the server
// if missing.
type Inbound struct {
	EventID   string          `json:"event_id,omitempty"`
	TenantID  string          `json:"tenant_id"`
	Source    string          `json:"source"`
	Transport Transport       `json:"transport,omitempty"`
	Raw       json.RawMessage `json:"raw"`
}

// ErrInvalid is returned when a payload fails validation.
type ErrInvalid struct {
	Field string
	Msg   string
}

func (e ErrInvalid) Error() string { return fmt.Sprintf("invalid %s: %s", e.Field, e.Msg) }

// Validate ensures the inbound payload satisfies the schema's required
// fields and enums, before any minting takes place.
func (i Inbound) Validate() error {
	if strings.TrimSpace(i.TenantID) == "" {
		return ErrInvalid{Field: "tenant_id", Msg: "required, non-empty"}
	}
	if strings.TrimSpace(i.Source) == "" {
		return ErrInvalid{Field: "source", Msg: "required, non-empty"}
	}
	if len(i.Raw) == 0 {
		return ErrInvalid{Field: "raw", Msg: "required"}
	}
	if !json.Valid(i.Raw) {
		return ErrInvalid{Field: "raw", Msg: "not valid JSON"}
	}
	if i.Transport != "" && i.Transport != TransportHTTP && i.Transport != TransportSyslog {
		return ErrInvalid{Field: "transport", Msg: "must be http or syslog"}
	}
	return nil
}

// Mint produces a publish-ready RawEvent from an Inbound payload.
// nodeID is the ingest replica identifier; defaultTransport is used
// when the inbound payload didn't specify one.
func Mint(in Inbound, nodeID string, defaultTransport Transport, now func() time.Time) (RawEvent, error) {
	if err := in.Validate(); err != nil {
		return RawEvent{}, err
	}
	id := in.EventID
	if id == "" {
		newID, err := newUUIDv4()
		if err != nil {
			return RawEvent{}, err
		}
		id = newID
	}
	transport := in.Transport
	if transport == "" {
		transport = defaultTransport
	}
	return RawEvent{
		EventID:      id,
		TenantID:     in.TenantID,
		Source:       in.Source,
		ReceivedAt:   now().UTC().Format(time.RFC3339Nano),
		IngestNodeID: nodeID,
		Transport:    transport,
		Raw:          in.Raw,
	}, nil
}

// newUUIDv4 returns a UUID v4 in canonical 8-4-4-4-12 form.
func newUUIDv4() (string, error) {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		return "", errors.New("rand read failed")
	}
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16]), nil
}
