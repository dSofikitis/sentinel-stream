package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/dSofikitis/sentinel-stream/ingest/internal/producer"
	"github.com/dSofikitis/sentinel-stream/ingest/internal/server"
)

// Version is bumped per release.
const Version = "0.2.0"

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	}))

	addr := getenv("INGEST_ADDR", ":8080")
	nodeID := getenv("INGEST_NODE_ID", hostname())

	prod := producer.NewStdoutProducer(os.Stdout)
	defer prod.Close()

	cfg := server.Config{
		Addr:   addr,
		NodeID: nodeID,
	}
	handler := server.New(cfg, prod, logger)

	srv := &http.Server{
		Addr:              addr,
		Handler:           handler,
		ReadHeaderTimeout: 5 * time.Second,
	}

	logger.Info(
		"sentinel-ingest starting",
		"version", Version,
		"addr", addr,
		"node_id", nodeID,
		"producer", "stdout",
	)

	errCh := make(chan error, 1)
	go func() { errCh <- srv.ListenAndServe() }()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)

	select {
	case err := <-errCh:
		if err != nil && !errors.Is(err, http.ErrServerClosed) {
			logger.Error("server crashed", "error", err)
			os.Exit(1)
		}
	case sig := <-stop:
		logger.Info("shutting down", "signal", sig.String())
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		if err := srv.Shutdown(ctx); err != nil {
			logger.Error("shutdown error", "error", err)
		}
	}
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func hostname() string {
	if h, err := os.Hostname(); err == nil {
		return h
	}
	return "ingest-unknown"
}
