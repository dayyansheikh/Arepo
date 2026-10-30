#!/bin/bash
# Read-only view of the research queue on the Oracle host (for people and the restricted autopilot).
#   scripts/oracle/queue_status.sh            status.json + last 20 attempts + collector health
#   scripts/oracle/queue_status.sh log <id>   last 60 lines of the newest log of job <id>
set -euo pipefail
if [ "${1:-}" = "log" ]; then
  id=${2:?job id}
  [[ "$id" =~ ^[A-Za-z0-9_]+$ ]] || { echo "bad job id"; exit 2; }
  ssh -o BatchMode=yes oracle "ls -t ~/arepo/run/queue/logs/$id.*.log 2>/dev/null | head -1 | xargs -r tail -n 60"
  exit 0
fi
ssh -o BatchMode=yes oracle 'cat ~/arepo/run/queue/status.json; echo; tail -n 20 ~/arepo/run/queue/attempts.jsonl;
  echo; date -u +%FT%TZ; df -h / | tail -1; du -sh ~/arepo/data-dumps; free -m | head -2;
  ~/arepo/scripts/oracle/supervise.sh status; grep -E "^pass (start|end)" ~/arepo_collector/logs/collector.log | tail -2'
