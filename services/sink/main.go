package main

import (
	"bufio"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"os"
	"strconv"
	"time"

	"github.com/dSofikitis/sentinel-stream/sink/internal/sink"
)

// Version is bumped per release.
const Version = "0.2.0"

type config struct {
	chEndpoint string
	chDB       string
	chUser     string
	chPassword string
	batchSize  int
	flushEvery time.Duration
}

func loadConfig() config {
	cfg := config{
		chEndpoint: getenv("CLICKHOUSE_URL", "http://clickhouse:8123"),
		chDB:       getenv("CLICKHOUSE_DB", "sentinel"),
		chUser:     getenv("CLICKHOUSE_USER", "sentinel"),
		chPassword: getenv("CLICKHOUSE_PASSWORD", "sentinel"),
		batchSize:  envInt("SINK_BATCH_SIZE", 100),
		flushEvery: time.Duration(envInt("SINK_FLUSH_MS", 1000)) * time.Millisecond,
	}
	return cfg
}

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	cfg := loadConfig()
	client := sink.NewClickHouse(cfg.chEndpoint, cfg.chDB, cfg.chUser, cfg.chPassword)

	logger.Info(
		"sentinel-sink starting",
		"version", Version,
		"clickhouse", cfg.chEndpoint,
		"database", cfg.chDB,
		"batch_size", cfg.batchSize,
	)

	if err := run(context.Background(), os.Stdin, client, cfg, logger); err != nil && !errors.Is(err, io.EOF) {
		logger.Error("sink terminated", "error", err)
		os.Exit(1)
	}
}

func run(ctx context.Context, in io.Reader, client *sink.ClickHouse, cfg config, logger *slog.Logger) error {
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)
	buffers := map[string][]map[string]any{
		"events_enriched": nil,
		"alerts":          nil,
	}

	flush := func(table string) {
		batch := buffers[table]
		if len(batch) == 0 {
			return
		}
		buffers[table] = nil
		if _, err := client.InsertBatch(ctx, table, batch); err != nil {
			logger.Error("insert failed", "table", table, "rows", len(batch), "error", err)
			return
		}
		logger.Info("flushed", "table", table, "rows", len(batch))
	}
	flushAll := func() {
		for table := range buffers {
			flush(table)
		}
	}
	defer flushAll()

	ticker := time.NewTicker(cfg.flushEvery)
	defer ticker.Stop()

	lines := make(chan string, 256)
	go func() {
		defer close(lines)
		for scanner.Scan() {
			lines <- scanner.Text()
		}
	}()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			flushAll()
		case line, ok := <-lines:
			if !ok {
				return scanner.Err()
			}
			if line == "" {
				continue
			}
			var rec map[string]any
			if err := json.Unmarshal([]byte(line), &rec); err != nil {
				logger.Warn("skipping non-JSON line", "error", err)
				continue
			}
			table := sink.Route(rec)
			if table == "events_enriched" {
				rec = sink.FlattenEnriched(rec)
			}
			buffers[table] = append(buffers[table], rec)
			if len(buffers[table]) >= cfg.batchSize {
				flush(table)
			}
		}
	}
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func envInt(key string, fallback int) int {
	v := os.Getenv(key)
	if v == "" {
		return fallback
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		fmt.Fprintf(os.Stderr, "invalid %s=%q, using default %d\n", key, v, fallback)
		return fallback
	}
	return n
}
