// Package sink wraps the bits of the ClickHouse HTTP interface we need
// to batch-insert JSON each-row payloads.
package sink

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

// ClickHouse is a thin client around CH's /?query= HTTP endpoint.
// We POST JSONEachRow-formatted bodies; CH parses and inserts them.
type ClickHouse struct {
	endpoint string
	user     string
	password string
	database string
	client   *http.Client
}

// NewClickHouse returns a client pinned to the (database, endpoint).
// endpoint is the full http://host:port/ root URL.
func NewClickHouse(endpoint, database, user, password string) *ClickHouse {
	return &ClickHouse{
		endpoint: strings.TrimRight(endpoint, "/"),
		user:     user,
		password: password,
		database: database,
		client:   &http.Client{Timeout: 30 * time.Second},
	}
}

// InsertBatch posts rows (each a JSON object) into the given table
// using the FORMAT JSONEachRow path. Returns the number of rows
// written or an error.
func (c *ClickHouse) InsertBatch(ctx context.Context, table string, rows []map[string]any) (int, error) {
	if len(rows) == 0 {
		return 0, nil
	}
	var body bytes.Buffer
	encoder := json.NewEncoder(&body)
	for _, row := range rows {
		if err := encoder.Encode(row); err != nil {
			return 0, fmt.Errorf("encode row: %w", err)
		}
	}
	q := fmt.Sprintf("INSERT INTO %s.%s FORMAT JSONEachRow", c.database, table)
	u, err := url.Parse(c.endpoint + "/")
	if err != nil {
		return 0, fmt.Errorf("parse endpoint: %w", err)
	}
	values := u.Query()
	values.Set("query", q)
	values.Set("date_time_input_format", "best_effort")
	u.RawQuery = values.Encode()

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, u.String(), &body)
	if err != nil {
		return 0, fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("Content-Type", "application/x-ndjson")
	if c.user != "" {
		req.SetBasicAuth(c.user, c.password)
	}
	resp, err := c.client.Do(req)
	if err != nil {
		return 0, fmt.Errorf("post: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		buf, _ := io.ReadAll(resp.Body)
		return 0, fmt.Errorf("clickhouse %d: %s", resp.StatusCode, strings.TrimSpace(string(buf)))
	}
	return len(rows), nil
}
