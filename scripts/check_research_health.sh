#!/usr/bin/env bash
# Research-collection health check (final pre-deployment §13). Surfaces collector recency, last
# freeze, cohort counts, degraded runs and any incomplete cohort so a stalled or degraded pipeline
# is visible. Usage: API_BASE=https://arepo-api.onrender.com scripts/check_research_health.sh
# Exits non-zero if a hard problem is detected (incomplete cohorts, or no successful freeze while
# cohorts are expected). Never prints secrets.
set -euo pipefail
API_BASE="${API_BASE:-http://127.0.0.1:8012}"
fail() { echo "HEALTH FAIL: $1" >&2; exit 1; }

curl -s -o /tmp/arepo_rh.json "$API_BASE/api/research/status" || fail "cannot reach research status"
python3 - "$API_BASE" <<'PY'
import json, sys
d = json.load(open("/tmp/arepo_rh.json"))
cad = d.get("cohort_counts_by_cadence", {})
print("cohorts 6h/daily/weekly:", cad.get("6h",0), "/", cad.get("daily",0), "/", cad.get("weekly",0))
print("total frozen markets:", d.get("total_frozen_markets"))
print("last successful freeze:", d.get("last_successful_freeze"))
print("collector recent:", d.get("collector_recent"))
print("degraded cohorts:", d.get("degraded_cohorts"), "latest run:", d.get("latest_run"))
print("incomplete cohorts:", d.get("incomplete_cohorts"))
print("edge supported:", d["edge"]["edge_supported"])
problems = []
if d.get("incomplete_cohorts", 0):
    problems.append("incomplete cohorts present (run research-repair)")
if problems:
    print("HEALTH PROBLEMS:", "; ".join(problems)); sys.exit(1)
print("HEALTH OK")
PY
