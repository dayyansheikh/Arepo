#!/bin/bash
# AREPO 2-hourly collection pass on the Oracle host (cron: even UTC hours at :31).
# Linux port of the Mac's ~/arepo_collector/arepo_pass.sh (launchd com.arepo.collector, retired
# 2026-10-14). Same steps, order, arguments and log lines; differences: flock instead of a mkdir
# lock (survives a reboot without a stale lock), no caffeinate, `free -m` instead of the macOS
# swap line, and an AREPO data cap (default 45 GiB since 2026-10-17, after the boot volume grew to 100 GB) next to the 4 GB free-disk guard.
# Snapshot (+1 retry) -> frozen forecast -> 2 book sweeps -> active trade sample -> flow screen
# -> E011 score -> E004 / E007 status. See docs/research_lab/COLLECTION_HOST.md.
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
AREPO_HOME=${AREPO_HOME:-/home/opc/arepo}
CAP_GB=${AREPO_DATA_CAP_GB:-45}   # 12 -> 13 -> 14 -> 16 -> 45 GiB on 2026-10-17 (autopilot; 45 at 15:35Z after the user grew the boot volume to 100 GB: root 89 GB, 60 GB free); the 4 GB free-disk guard is unchanged
exec 9>/tmp/arepo_collector.lock
flock -n 9 || { echo "$(date -u +%FT%TZ) skipped: another pass holds the lock"; exit 0; }
free=$(df -Pk / | tail -1 | awk '{print $4}')
if [ "$free" -lt 4000000 ]; then echo "$(date -u +%FT%TZ) skipped: free disk ${free} KiB < 4 GB"; exit 0; fi
used=$(du -sk "$AREPO_HOME/data-dumps" 2>/dev/null | cut -f1)
if [ "${used:-0}" -gt $((CAP_GB * 1024 * 1024)) ]; then
  echo "$(date -u +%FT%TZ) skipped: AREPO data ${used} KiB > ${CAP_GB} GB cap"; exit 0
fi
cd "$AREPO_HOME/backend" || exit 1
PY="$AREPO_HOME/.venv/bin/python"
echo "pass start $(date -u +%FT%TZ) mem: $(free -m | awk '/^Mem/{print "avail="$7"M"} /^Swap/{print "swap_used="$3"M"}' | tr '\n' ' ')"
out=$($PY scripts/collect_universe_snapshot.py 2>&1 | tail -1); echo "$out"
if ! echo "$out" | grep -q "state=complete"; then sleep 300; out=$($PY scripts/collect_universe_snapshot.py 2>&1 | tail -1); echo "retry: $out"; fi
if echo "$out" | grep -q "state=complete"; then
  $PY scripts/run_forecast.py predict --snapshot latest 2>&1 | tail -1
  $PY scripts/sweep_books.py --snapshot latest --repeat 2 2>&1 | tail -2
  $PY scripts/sample_trades.py --snapshot latest --frame active --n 2000 2>&1 | tail -1
  $PY scripts/run_flow_screen.py 2>&1 | tail -1
  $PY scripts/run_surprise_snapshot.py score --rps 4 2>&1 | tail -2   # E011 (registered 3e628ec)
  timeout 600 nice -n 10 $PY scripts/run_cb1_extract.py --all-new --rps 2 --max-requests 300 2>&1 | tail -1 || true   # CB1 extract (CREATIVE_BATCH_1.md §2.11)
  timeout 600 nice -n 10 $PY scripts/run_cb4.py closewin --all-new --data-dumps-max-gb 40 2>&1 | tail -1 || true   # CB4 closewin/departures (CREATIVE_BATCH_4.md §2.10)
  timeout 600 nice -n 10 $PY scripts/run_cb5.py extract --all-new --tables listings --data-dumps-max-gb 40 2>&1 | tail -1 || true   # CB5 listings (CREATIVE_BATCH_5.md §4.3)
  timeout 600 nice -n 10 $PY scripts/run_cb3_quote_state.py --all-new --data-dumps-cap-gb 40 2>&1 | tail -1 || true   # CB3 quote_state (CREATIVE_BATCH_3.md §4.3.2)
  timeout 600 nice -n 10 $PY scripts/run_signal_engine.py tick --max-items 2 --data-dumps-cap-gb 40 2>&1 | tail -1 | cut -c1-400 || true   # signal engine features + write-once predictions (signal_engine/DESIGN_V1.md §11); last step, so no registered step is delayed
fi
$PY scripts/run_research_e004.py score --status 2>&1 | grep -E '"qualifying"'
$PY scripts/run_research_e007.py score --status 2>&1 | head -1
echo "pass end $(date -u +%FT%TZ)"
