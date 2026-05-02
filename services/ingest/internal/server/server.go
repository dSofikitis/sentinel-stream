// Package server wires the HTTP routes for sentinel-ingest.
package server

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"time"

	"github.com/dSofikitis/sentinel-stream/ingest/internal/event"
	"github.com/dSofikitis/sentinel-stream/ingest/internal/producer"
)

// Config holds runtime knobs for the HTTP server.
type Config struct {
	Addr   string
	NodeID string
	Now    func() time.Time
}

// New returns an http.Handler with /health and POST /events wired up.
func New(cfg Config, prod producer.Producer, logger *slog.Logger) http.Handler {
	if cfg.Now == nil {
		cfg.Now = time.Now
	}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", handleHealth)
	mux.HandleFunc("POST /events", handleEvents(cfg, prod, logger))
	return logging(logger, mux)
}

func handleHealth(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_, _ = w.Write([]byte(`{"status":"ok"}`))
}

func handleEvents(cfg Config, prod producer.Producer, logger *slog.Logger) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		defer r.Body.Close()
		var in event.Inbound
		if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
			writeJSONError(w, http.StatusBadRequest, "invalid json: "+err.Error())
			return
		}
		ev, err := event.Mint(in, cfg.NodeID, event.TransportHTTP, cfg.Now)
		if err != nil {
			writeJSONError(w, http.StatusBadRequest, err.Error())
			return
		}
		if err := prod.Publish(r.Context(), ev); err != nil {
			logger.Error("publish failed", "error", err, "event_id", ev.EventID)
			writeJSONError(w, http.StatusServiceUnavailable, "publish failed")
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusAccepted)
		_ = json.NewEncoder(w).Encode(map[string]string{"event_id": ev.EventID})
	}
}

func writeJSONError(w http.ResponseWriter, status int, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]string{"error": message})
}

func logging(logger *slog.Logger, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rec, r)
		logger.Info(
			"http",
			"method", r.Method,
			"path", r.URL.Path,
			"status", rec.status,
			"duration_ms", time.Since(start).Milliseconds(),
		)
	})
}

type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(code int) {
	r.status = code
	r.ResponseWriter.WriteHeader(code)
}
