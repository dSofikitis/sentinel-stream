#!/usr/bin/env bash
# Port scan: 25 distinct destination-port drops from a single source IP.
# Fires the fw_drop_public_to_priv_port Sigma rule on the ones that hit
# privileged ports (<=1023).

set -euo pipefail

INGEST="${INGEST:-http://localhost:8080}"
SRC_IP="${SRC_IP:-203.0.113.77}"
DST_IP="${DST_IP:-10.0.0.5}"
PORTS="${PORTS:-25}"

post() {
  local port="$1"
  curl -sS -o /dev/null -X POST "$INGEST/events" \
    -H 'Content-Type: application/json' \
    -d "{
      \"tenant_id\": \"globex\",
      \"source\": \"edge-firewall\",
      \"transport\": \"syslog\",
      \"raw\": {
        \"@timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)\",
        \"event_class\": \"network\",
        \"action\": \"drop\",
        \"src_ip\": \"$SRC_IP\",
        \"dst_ip\": \"$DST_IP\",
        \"src_port\": $((50000 + port)),
        \"dst_port\": $port,
        \"protocol\": \"tcp\",
        \"severity\": \"notice\",
        \"message\": \"fw drop\"
      }
    }"
}

echo "Port scan: $SRC_IP -> $DST_IP across $PORTS distinct ports"
seen=0
port=20
while [ "$seen" -lt "$PORTS" ]; do
  post "$port"
  seen=$((seen + 1))
  port=$(( (port + 17) % 65535 ))
  if [ "$port" -lt 1 ]; then port=1; fi
done
echo "done."
