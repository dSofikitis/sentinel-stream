package event

import (
	"encoding/json"
	"strings"
	"testing"
	"time"
)

var fixedNow = func() time.Time {
	return time.Date(2026, 5, 2, 12, 0, 0, 0, time.UTC)
}

func TestInbound_Validate(t *testing.T) {
	cases := []struct {
		name    string
		in      Inbound
		wantErr bool
		errField string
	}{
		{
			name: "happy path",
			in: Inbound{
				TenantID: "acme",
				Source:   "auth",
				Raw:      json.RawMessage(`{"k":"v"}`),
			},
			wantErr: false,
		},
		{
			name: "missing tenant",
			in: Inbound{
				Source: "auth",
				Raw:    json.RawMessage(`{}`),
			},
			wantErr: true,
			errField: "tenant_id",
		},
		{
			name: "missing source",
			in: Inbound{
				TenantID: "acme",
				Raw:      json.RawMessage(`{}`),
			},
			wantErr: true,
			errField: "source",
		},
		{
			name: "missing raw",
			in: Inbound{
				TenantID: "acme",
				Source:   "auth",
			},
			wantErr: true,
			errField: "raw",
		},
		{
			name: "raw not json",
			in: Inbound{
				TenantID: "acme",
				Source:   "auth",
				Raw:      json.RawMessage(`{not-json`),
			},
			wantErr: true,
			errField: "raw",
		},
		{
			name: "bogus transport",
			in: Inbound{
				TenantID:  "acme",
				Source:    "auth",
				Transport: "carrier-pigeon",
				Raw:       json.RawMessage(`{}`),
			},
			wantErr: true,
			errField: "transport",
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			err := tc.in.Validate()
			if tc.wantErr && err == nil {
				t.Fatalf("expected error, got nil")
			}
			if !tc.wantErr && err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if tc.wantErr {
				var inv ErrInvalid
				ok := false
				if e, asErr := err.(ErrInvalid); asErr {
					inv, ok = e, true
				}
				if !ok {
					t.Fatalf("expected ErrInvalid, got %T (%v)", err, err)
				}
				if inv.Field != tc.errField {
					t.Fatalf("err.Field = %q, want %q", inv.Field, tc.errField)
				}
			}
		})
	}
}

func TestMint_FillsDefaults(t *testing.T) {
	in := Inbound{
		TenantID: "acme",
		Source:   "auth",
		Raw:      json.RawMessage(`{"k":"v"}`),
	}
	got, err := Mint(in, "node-1", TransportHTTP, fixedNow)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.EventID == "" {
		t.Errorf("EventID was not minted")
	}
	if !strings.HasPrefix(got.ReceivedAt, "2026-05-02T12:00:00") {
		t.Errorf("ReceivedAt = %q, want fixed timestamp prefix", got.ReceivedAt)
	}
	if got.IngestNodeID != "node-1" {
		t.Errorf("IngestNodeID = %q, want node-1", got.IngestNodeID)
	}
	if got.Transport != TransportHTTP {
		t.Errorf("Transport = %q, want http", got.Transport)
	}
}

func TestMint_PassesThroughExplicitID(t *testing.T) {
	in := Inbound{
		EventID:  "deadbeef",
		TenantID: "acme",
		Source:   "auth",
		Raw:      json.RawMessage(`{}`),
	}
	got, err := Mint(in, "node-1", TransportHTTP, fixedNow)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.EventID != "deadbeef" {
		t.Errorf("EventID overwritten: got %q", got.EventID)
	}
}

func TestMint_RejectsInvalid(t *testing.T) {
	if _, err := Mint(Inbound{}, "node-1", TransportHTTP, fixedNow); err == nil {
		t.Fatal("expected validation error, got nil")
	}
}
