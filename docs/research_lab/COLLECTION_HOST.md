# Collection host: Oracle server (since 2026-10-14)

AREPO's always-on public-data collection moved from the user's Mac (launchd) to the user's Oracle Cloud server, as the user
approved on 2026-10-13. The research code, specs and frozen models are unchanged; only the host changed. The cutover time and
any gap are recorded in `EXPERIMENT_LEDGER.md` ("Operational deviation: collection host moved").

## Host
- `ssh oracle` (alias in the Mac's `~/.ssh/config`; never copy the key). The user is `opc`, the host runs Oracle Linux 8 aarch64
  with 1 OCPU and about 6 GB RAM, and the clock is UTC.
- Python 3.11 venv: `/home/opc/arepo/.venv`. It is pinned to the Mac venv's versions (numpy 2.4.6, pandas 2.3.3,
  lightgbm 4.7.0, scikit-learn 1.9.1, scipy 1.17.1) and holds an editable install of `backend/`.
- The host is shared with the user's other work (`rev-build`, `revision-build`). Leave anything that isn't AREPO alone.

## Layout
| Path | What |
|---|---|
| `/home/opc/arepo/` | Shallow git clone (history since 2026-10-09, so the registration commits exist), deployed from the Mac |
| `/home/opc/arepo/data-dumps/research_lab/` | Canonical data. It has the same relative layout as on the Mac (code resolves `<repo>/data-dumps`) |
| `/home/opc/arepo/run/` | Monitor pidfiles, exit codes and `.disabled` markers |
| `/home/opc/arepo_collector/logs/` | `collector.log` (notify parses it), `live-trade-monitor.*`, `cross-venue-live.*`, `live-trade-outcomes.*`, `notify.*`, `supervise.log` |
| `/home/opc/.arepo/` (700) | `wallet_hash_key` (the same key as the Mac, so wallet hashes stay consistent), `ntfy_topic`, `notify_state.json`; all mode 600 |
| `/home/opc/arepo_val/` | Validation copy used before cutover. It is not canonical and can be deleted |

Data copied from the Mac at cutover: `snapshots`, `forecasts`, `e001`–`e007`, `book_sweeps`, `trade_samples`, `flow_screen`,
`surprise_live` (E011 state), `live_trades` (monitor state and 7-day history), `cross_venue` and `cross_venue_live` (E009/E010 state).
Other `research_lab` directories (history, if_h2, ml_cache, etc.) stay on the Mac only; the live jobs do not read them.

## Jobs (`crontab -l`; the source is `scripts/oracle/crontab.txt`)
| Schedule (UTC) | Job | Mac equivalent (retired) |
|---|---|---|
| `31 */2` | `scripts/oracle/arepo_pass.sh` (snapshot -> forecast -> 2 sweeps -> trade sample -> flow screen -> E011 score -> E004/E007 status) | `com.arepo.collector` |
| `@reboot`, `*/5` | `scripts/oracle/supervise.sh`: keeps `run_live_trade_monitor.py` and `run_cross_venue_live.py` running | `com.arepo.live-trade-monitor`, `com.arepo.cross-venue-live` |
| `10 2,14` | `run_live_trade_monitor.py --outcomes` | `com.arepo.live-trade-outcomes` (03:10/15:10 BST) |
| `*/15` | `arepo_notify.py check` (ntfy) | `com.arepo.notify` |

- **Pass guards.** The pass takes `flock /tmp/arepo_collector.lock`, so passes never overlap. It skips with a logged line if free
  disk is below 4 GB or if `data-dumps` is above `AREPO_DATA_CAP_GB` (default 12). A skip shows up in notify as "collector has not
  finished a pass for 6+ hours".
- **Supervisor restart policy.** The supervisor restarts a dead monitor unless `run/<name>.disabled` exists, or unless the monitor's
  last exit code was 3 (its own storage cap: 3 GB for live_trades, 2 GB for cross_venue_live). A monitor stopped at its cap needs a human.
- **Measured load.** A pass measured on this host (2026-10-13 validation) takes about 18 min with about 1.0 GB peak RSS. The monitors
  together hold about 0.5 GB.
- **Notify quirk.** `notify.py` writes its own log to `~/Library/Logs/arepo-notify.log`, a path that is harmless on Linux.

## Health check (from the Mac)
```bash
ssh oracle 'tail -n 12 ~/arepo_collector/logs/collector.log; ~/arepo/scripts/oracle/supervise.sh status; \
  tail -n 2 ~/arepo_collector/logs/live-trade-monitor.err ~/arepo_collector/logs/cross-venue-live.err; \
  du -sh ~/arepo/data-dumps; df -h / | tail -1; free -m | head -2; crontab -l | grep -c arepo'
```
A healthy host shows `pass end` within the last 2 h with `state=complete`, both monitors `running`, recent `cycle` lines, and
`data-dumps` under 12 GB.

## Code updates and trials.jsonl
- **Deploying.** Commit on the Mac, then run `scripts/oracle/deploy.sh`. It deploys the committed branch tip, never the working tree.
  The collection pass picks up the new code at its next run. To restart the monitors on new code:
  `ssh oracle '~/arepo/scripts/oracle/supervise.sh stop; rm ~/arepo/run/*.disabled; ~/arepo/scripts/oracle/supervise.sh'`.
- **trials.jsonl.** The flow screen appends DEVELOPMENT rows to `docs/research_lab/trials.jsonl` on the host. `deploy.sh` merges that
  file both ways (`scripts/oracle/union_jsonl.py`: append-only, exact-line union, nothing dropped), so run it, or just its trials
  step, before any analysis that counts trials (Holm families) on the Mac.
- **Pulling data.** Data for analysis is pulled read-only with `rsync -a oracle:/home/opc/arepo/data-dumps/research_lab/<dir> ...`.
  Never run collection on both hosts at once.

## Disk
- **Growth.** Snapshots are about 67 MB each, so the passes write about 1 GB/day in all (snapshots, trade samples, sweeps). The
  12 GB cap is reached roughly 8 days after cutover unless old data is archived off the host. The archive-to-GitHub rotation
  (separate work) must keep this layout. The pass guard stops collection rather than exceeding the cap, so it never deletes anything.

## Rollback to the Mac
1. On the host: `crontab -e` and delete the `# --- AREPO` block, then `~/arepo/scripts/oracle/supervise.sh stop`.
2. Copy the host's new data back with `rsync -a oracle:/home/opc/arepo/data-dumps/research_lab/<dir>/ <mac repo>/data-dumps/research_lab/<dir>/`
   for `snapshots forecasts book_sweeps trade_samples flow_screen surprise_live live_trades cross_venue_live e00?`, and merge
   trials with `python3 scripts/oracle/union_jsonl.py docs/research_lab/trials.jsonl <host copy>`.
3. On the Mac, restore each plist: `cd ~/Library/LaunchAgents && for f in com.arepo.*.plist.disabled; do mv "$f" "${f%.disabled}"; launchctl load "${f%.disabled}"; done`.
4. Record the move back in `EXPERIMENT_LEDGER.md`.
