#!/bin/bash
# Watchdog for the two long-running AREPO monitors on the Oracle host (cron: @reboot and every
# 5 min). Replaces the Mac launchd KeepAlive jobs com.arepo.live-trade-monitor and
# com.arepo.cross-venue-live. A monitor is (re)started when its pid is not alive, unless
#   - ~/arepo/run/<name>.disabled exists (manual stop / rollback), or
#   - its last exit code was 3 (the monitor's own storage cap: intentional stop, needs a human).
# Usage: supervise.sh            check and restart
#        supervise.sh status     print state only
#        supervise.sh stop       create .disabled markers and SIGTERM both monitors
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
AREPO_HOME=${AREPO_HOME:-/home/opc/arepo}
RUN="$AREPO_HOME/run"
LOGS=${AREPO_LOGS:-/home/opc/arepo_collector/logs}
PY="$AREPO_HOME/.venv/bin/python"
mkdir -p "$RUN" "$LOGS"
if [ -z "${1:-}" ]; then  # only the restarting mode needs the lock; children must not inherit it
  exec 8>"$RUN/supervise.lock"
  flock -n 8 || exit 0
fi

declare -A CMD=(
  [live-trade-monitor]="scripts/run_live_trade_monitor.py"
  [cross-venue-live]="scripts/run_cross_venue_live.py"
)

alive() { local p; p=$(cat "$RUN/$1.pid" 2>/dev/null) && [ -n "$p" ] && kill -0 "$p" 2>/dev/null \
  && grep -q "${CMD[$1]}" "/proc/$p/cmdline" 2>/dev/null; }

for name in "${!CMD[@]}"; do
  if [ "${1:-}" = "stop" ]; then
    touch "$RUN/$name.disabled"
    alive "$name" && kill -TERM "$(cat "$RUN/$name.pid")" && echo "$name: SIGTERM sent"
    continue
  fi
  if alive "$name"; then
    [ "${1:-}" = "status" ] && echo "$name: running pid $(cat "$RUN/$name.pid")"
    continue
  fi
  last=$(cat "$RUN/$name.exit" 2>/dev/null)
  if [ -e "$RUN/$name.disabled" ]; then
    [ "${1:-}" = "status" ] && echo "$name: disabled (marker $RUN/$name.disabled)"; continue
  fi
  if [ "$last" = "3" ]; then
    [ "${1:-}" = "status" ] && echo "$name: stopped at its storage cap (exit 3); not restarting"; continue
  fi
  [ "${1:-}" = "status" ] && { echo "$name: NOT running (last exit ${last:-none})"; continue; }
  echo "$(date -u +%FT%TZ) starting $name (last exit ${last:-none})" >> "$LOGS/supervise.log"
  cd "$AREPO_HOME/backend" || exit 1
  rm -f "$RUN/$name.exit"
  # the pidfile holds the python pid itself (so SIGTERM reaches the monitor); the wrapper only
  # records its exit code for the restart policy above
  setsid nohup bash -c "'$PY' ${CMD[$name]} >> '$LOGS/$name.out' 2>> '$LOGS/$name.err' & \
    echo \$! > '$RUN/$name.pid'; wait \$!; echo \$? > '$RUN/$name.exit'" \
    < /dev/null > /dev/null 2>&1 8>&- &
  sleep 2
done
