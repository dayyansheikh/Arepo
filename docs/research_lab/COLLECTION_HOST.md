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

## Nightly archive rotation (`backend/scripts/archive_rotate.py`)
Status: written and unit-tested on the Mac (`tests/unit/test_archive_rotate.py`); **not installed** on the host. Added 2026-10-13
by the archive session; see `DATA_ARCHIVE_2026-10-13.md`.

What one run does:
1. It selects the files under `--scan` dirs whose mtime is older than `--older-than-days` and skips `*.lock`, `*.pid`, `*.tmp`,
   `*.partial` and `*state*.json`.
2. It builds a draft release `data-YYYYMMDD-<host>` in `dayyansheikh/arepo-data` with `archive_release.py`. This is the same scheme
   as `data-20261011`: a zstd tar of the original bytes, `files.sha256`, `MANIFEST.sha256` and a README. Each part (up to 1.9 GB) is
   uploaded as soon as it is full, then its staging copy is deleted.
3. It streams every part back, checks each hash, and re-hashes every member. Only a PASS publishes the release, uploads `VERIFY.json`
   and records the release in `~/.arepo/archive_rotate/verified_releases.jsonl`.
4. With `--delete`, it deletes a server file only when all of these hold: the file is in a verified release; that release on GitHub
   still matches the ledger and is published; the file is still older than the cut-off; and its current sha256 equals the archived
   hash. Every decision (`deleted`, `kept`, `would_delete`) is appended with its path, sha256, bytes and release to
   `~/.arepo/archive_rotate/deletions.jsonl`. A file that is not verified-archived is never deleted. The user approved deleting the
   server's own copies under these rules.

Before installing (open decisions for the user or the migration agent):
- **Tools and credentials.** The host has neither `zstd` nor `gh`. Install both, for example `gh` and `zstd` binaries in `~/.local/bin`
  with no sudo needed. `gh` also needs a GitHub token that can write releases to `dayyansheikh/arepo-data` only, for example a
  fine-grained token with Contents read and write on that one repo, stored by `gh auth login --with-token`. Creating that token is a
  credential decision for the user.
- **Which dirs may rotate.** This is a scientific dependency question. E004, E005 and E006 list *all* complete snapshot captures since
  registration (`forecast.list_complete_captures`), and E003 and E007 read old snapshots and sweeps by id. Deleting old
  `snapshots/` or `book_sweeps/` from the host would silently change what those status and evaluation runs see. Either those readers
  first learn to restore from the archive (or read a frozen capture list), or those dirs are not rotated until their experiments close.
  The same applies to E009/E010, which read the `cross_venue_live` stream until 2026-11-03, and to E011, which reads complete-universe
  snapshots and runs its analysis once after 2026-11-11 (`EXPERIMENT_LEDGER.md`). **Rule: never use `--delete` on a dir that a
  non-COMPLETE registered experiment reads.** Until that is settled, run archive-only (omit `--delete`), or limit `--scan` to dirs that
  no open experiment reads.
- **Cut-off.** The 12 GB cap fills in about 8 days, so `--older-than-days` of 3 to 5 is needed once deletion is allowed.

Suggested crontab line, to add to `scripts/oracle/crontab.txt` after the decisions above (it runs at 03:30 UTC, outside the `:31`
passes; it has its own lock and must not take the pass lock, because an upload can run for hours and would block
collection):
```
30 3 * * * cd /home/opc/arepo/backend && /home/opc/arepo/.venv/bin/python scripts/archive_rotate.py --root /home/opc/arepo --scan data-dumps/research_lab/<dir> --older-than-days 5 --delete >> /home/opc/arepo_collector/logs/archive-rotate.log 2>&1
```
- **Dry run.** Add `--dry-run` to `--delete` for a first run that only logs `would_delete`.
- **Load.** Uploads run at the host's uplink speed. zstd `-12 --long=27 -T2` stays under about 1 GB of RAM.
