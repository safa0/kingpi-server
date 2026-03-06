#!/usr/bin/env bash
# Atomic counter correctness test using hey (Go-based, true concurrency).
#
# Usage:
#   bash tests/stress/test_atomicity.sh        # default 100 requests
#   bash tests/stress/test_atomicity.sh 500    # custom count

set -euo pipefail

N="${1:-100}"
HOST="${KINGPI_BASE_URL:-http://localhost:8000}"
PACKAGE="text2digits"
EVENT_TYPE="install"

# Reset databases
docker compose exec redis redis-cli FLUSHALL > /dev/null
docker compose exec postgres psql -U kingpi -d kingpi -c "TRUNCATE package_events;" > /dev/null
sleep 1
echo "Flushed Redis + truncated Postgres"

# Fire N concurrent requests with hey, capture output
echo "Sending $N concurrent POST requests..."
HEY_OUTPUT=$(hey -n "$N" -c "$N" \
  -m POST \
  -H "Content-Type: application/json" \
  -d "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"package\":\"$PACKAGE\",\"type\":\"$EVENT_TYPE\"}" \
  "$HOST/api/v1/event" 2>&1)

echo "$HEY_OUTPUT"

# Parse successful 201 responses from hey's status code distribution
SUCCESSFUL=$(echo "$HEY_OUTPUT" | grep '\[201\]' | awk '{print $2}')
SUCCESSFUL="${SUCCESSFUL:-0}"

# Query actual total from the API
ACTUAL=$(curl -s "$HOST/api/v1/package/$PACKAGE/event/$EVENT_TYPE/total")

echo ""
echo "============================================================"
echo "CORRECTNESS CHECK"
echo "  Successful POSTs: $SUCCESSFUL"
echo "  Actual total:     $ACTUAL"
if [ "$ACTUAL" -eq "$SUCCESSFUL" ]; then
  echo "  Result:           PASS"
else
  DIFF=$((SUCCESSFUL - ACTUAL))
  echo "  Result:           FAIL (off by $DIFF)"
  exit 1
fi
echo "============================================================"
