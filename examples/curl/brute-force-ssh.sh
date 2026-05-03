#!/usr/bin/env bash
# Brute-force SSH: 12 failed logins for `root` from a single IP, then a
# success. Mirrors the generator's `brute_force_ssh` scenario so the
# detector's ssh_login_failure rule fires repeatedly and the anomaly
# model picks up the burst.

set -euo pipefail

INGEST="${INGEST:-http://localhost:8080}"
USER="${USER_TARGET:-root}"
SRC_IP="${SRC_IP:-203.0.113.66}"
HOST="${HOST:-auth-eu1}"

post() {
  local outcome="$1"
  local severity="$2"
  local message="$3"
  curl -sS -o /dev/null -X POST "$INGEST/events" \
    -H 'Content-Type: application/json' \
    -d "{
      \"tenant_id\": \"acme\",
      \"source\": \"auth-service\",
      \"transport\": \"http\",
      \"raw\": {
        \"@timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)\",
        \"event_class\": \"auth\",
        \"outcome\": \"$outcome\",
        \"user\": \"$USER\",
        \"host\": \"$HOST\",
        \"src_ip\": \"$SRC_IP\",
        \"service\": \"ssh\",
        \"severity\": \"$severity\",
        \"message\": \"$message\"
      }
    }"
}

echo "Brute-force burst: 12 failures + 1 success against $USER@$HOST from $SRC_IP"
for i in $(seq 1 12); do
  post failure warning "Login failed for user $USER ($i)"
done
post success info "User $USER logged in"
echo "done."
