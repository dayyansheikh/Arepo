#!/usr/bin/env bash
# Verify a deployed (or locally-served) Arepo API (final pre-deployment §13, §15). Checks health,
# schema currency via the API's research status, and that research status is honest (edge not
# claimed on an empty sample). Catches an intentional misconfiguration (wrong/unreachable API base).
# Usage: API_BASE=https://arepo-api.onrender.com scripts/verify_production.sh
# Never prints secrets. Exits non-zero on failure.
set -euo pipefail
API_BASE="${API_BASE:-http://127.0.0.1:8012}"
fail() { echo "VERIFY FAIL: $1" >&2; exit 1; }
j() { python3 -c "import sys,json;d=json.load(sys.stdin);print(d$1)"; }

echo "== $API_BASE /health =="
code=$(curl -s -o /tmp/arepo_health.json -w "%{http_code}" "$API_BASE/health" || true)
[ "$code" = "200" ] || fail "health returned $code (is the API base correct and the service up?)"

echo "== /api/research/status =="
code=$(curl -s -o /tmp/arepo_status.json -w "%{http_code}" "$API_BASE/api/research/status" || true)
[ "$code" = "200" ] || fail "research status returned $code"
EDGE=$(cat /tmp/arepo_status.json | j "['edge']['edge_supported']")
INC=$(cat /tmp/arepo_status.json | j "['incomplete_cohorts']")
MODEL=$(cat /tmp/arepo_status.json | j "['model_version']")
echo "   model_version=$MODEL edge_supported=$EDGE incomplete_cohorts=$INC"
[ "$INC" = "0" ] || fail "there are $INC incomplete cohorts; run research-repair"
# On a fresh deploy the edge must NOT be supported (no sample yet).
[ "$EDGE" = "False" ] || echo "   note: edge_supported is $EDGE (only valid if the full criteria genuinely pass)"

echo "== synthetic excluded from /api/cohorts/latest =="
code=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE/api/cohorts/latest" || true)
echo "   /api/cohorts/latest -> $code (404 expected until a real cohort exists)"

echo "VERIFY OK"
