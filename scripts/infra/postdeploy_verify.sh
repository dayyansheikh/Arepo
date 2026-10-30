#!/usr/bin/env bash
# Post-deploy verification for fix/infra-2026-10-11 (read-only; ~10 requests, spaced to avoid
# Render's Cloudflare bot challenge). Usage: scripts/infra/postdeploy_verify.sh [merge_time_utc]
# Expected (PASS criteria) are printed next to each line.
set -uo pipefail
API=https://arepo-api.onrender.com
WWW=https://www.arepolabs.com
SINCE=${1:-$(date -u -v-3H +%FT%TZ 2>/dev/null || date -u -d '-3 hours' +%FT%TZ)}
fail=0

probe() {  # label url max_seconds expected_code
  local out code t
  out=$(curl -s -m 120 -o /dev/null -w "%{http_code} %{time_total}" "$2")
  code=${out% *}; t=${out#* }
  local ok=PASS
  [ "$code" = "$4" ] || ok=FAIL
  awk -v t="$t" -v m="$3" 'BEGIN{exit !(t<=m)}' || ok=FAIL
  [ $ok = FAIL ] && fail=1
  printf '%-4s %-34s code=%s time=%5.1fs   expect %s within %ss\n' "$ok" "$1" "$code" "$t" "$4" "$3"
  sleep 3
}

echo "== API (first call may include a Render cold start of up to ~60 s)"
probe "health (wake)"               "$API/health"                      90 200
probe "health (warm)"               "$API/health"                       3 200
probe "research/status (first)"     "$API/api/research/status"         45 200
probe "research/status (cached)"    "$API/api/research/status"          3 200
probe "research/replay/cohorts"     "$API/api/research/replay/cohorts" 60 200
probe "markets/Explore (first)"     "$API/api/markets?limit=20"        45 200
probe "markets/Explore (cached)"    "$API/api/markets?limit=20"         5 200
probe "status poll"                 "$API/api/status"                   10 200
echo "== Frontend via Vercel rewrite"
probe "www home"                    "$WWW/"                             10 200
probe "www -> /api/status"          "$WWW/api/status"                   15 200
code=$(curl -s -m 30 -o /dev/null -w "%{http_code}" https://arepolabs.com/)
printf '%-4s %-34s code=%s   expect 308 (apex -> www)\n' "$([ "$code" = 308 ] && echo PASS || { fail=1; echo FAIL; })" "apex redirect" "$code"

echo "== GitHub Actions since $SINCE (expect: all success; collect run ~1-2 min, not ~8)"
gh run list -R dayyansheikh/Arepo -L 30 --json name,conclusion,status,createdAt,updatedAt \
  -q ".[] | select(.createdAt >= \"$SINCE\") | \"\(.createdAt) \(.name) \(.status)/\(.conclusion) \(.updatedAt)\"" \
  || fail=1
echo "== Latest collect tick summary (expect forward.already_present ~440836, storage.level critical until archive prune)"
id=$(gh run list -R dayyansheikh/Arepo -w arepo-collect -L 1 --json databaseId -q '.[0].databaseId')
gh run view "$id" -R dayyansheikh/Arepo --log 2>/dev/null | grep -oE '"already_present": [0-9]+|"size_mb": [0-9.]+|"level": "[a-z]+"' | head -3

[ $fail = 0 ] && echo "OVERALL: PASS" || echo "OVERALL: FAIL (see lines above; rollback in docs/infra/DEPLOY_RUNBOOK_2026-10-12.md)"
exit $fail
