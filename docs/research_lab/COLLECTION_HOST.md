# Collection host: Oracle server (since 2026-10-14)

AREPO's always-on public-data collection moved from the user's Mac (launchd) to the user's Oracle Cloud server, as the user
approved on 2026-10-13. The research code, specs and frozen models are unchanged; only the host changed. The cutover time and
any gap are recorded in `EXPERIMENT_LEDGER.md` ("Operational deviation: collection host moved").

## Host
- `ssh oracle` (alias in the Mac's `~/.ssh/config`; never copy the key). The user is `opc`, the host runs Oracle Linux 8 aarch64
  with 1 OCPU and about 6 GB RAM, and the clock is UTC. A resize to 2 OCPU / 12 GB is scheduled for 2026-10-22 02:40Z
  (see "Host resize" below).
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
| `*/2` | `scripts/oracle/queue_worker.py tick`: research queue, one job at a time; never starts while the pass holds the collector lock. Log: `queue.log`. See `queue/README.md` | none (added 2026-10-15) |

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
Status (2026-10-15): **installed ARCHIVE-ONLY** (no `--delete`) at 03:30 UTC nightly, `--scan data-dumps/research_lab
--older-than-days 1`, niced. `zstd` (dnf) and `gh` 2.62.0 (`~/.local/bin`) installed; `gh` logged in with a user-made fine-grained
token (arepo-data only, Contents RW, no expiry) stored at `~/.arepo/github_token` (600). First run started 18:29Z (release
`data-20261015-dsheikh`). Deletion is still OFF: `snapshots/` (3.1 GB, about 0.9 GB/day) is read by open E011/E004-E006
status runs, so freeing space needs readers that restore from the archive first (or a reviewed rule) before the 12 GB cap
(about 22 Oct). `/home/opc/arepo_val` is now E009/E010 evidence for the outage window (ledger, 2026-10-15): never delete it.

Catalogue, restore and retention (2026-10-15): `docs/research_lab/data_catalogue/` lists every archived file with its experiment
labels (`archive_catalogue.py` regenerates it); `backend/scripts/restore_from_archive.py` brings selected files back byte for byte
(round-trip proven on 23 files, README there); `RETENTION.md` and `scripts/oracle/archive_retention.json` are the per-directory deletion
proposal (`archive_rotate.py --retention`; deletion still OFF). The validation copy `/home/opc/arepo_val` has its own release
(`data-20261015-dsheikh-val`, separate `--state`/`--tag-suffix val`).

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

## Host resize to 2 OCPU / 12 GB (owner-approved 2026-10-21; scheduled 2026-10-22 02:40Z)
The owner approved ("Yes, but at a quiet time") growing this host to the tenancy's whole Always Free A1 allowance,
**2 OCPU / 12 GB**. The A1 limits are per availability domain: AD-1 has 2 cores / 12 GB, with 1 / 6 in use by this host,
and the account is Free Tier. Storage is not touched, so the cost stays at 0. The resize restarts the server once.

**Scripts** (`scripts/oracle/`, unit tests in `backend/tests/unit/test_resize_host.py`):
- `resize_host.py` runs with `~/oci_venv/bin/python`.
  - `--check` (read-only): prints the shape, the A1 instances in the tenancy, the per-AD limit and availability, and the
    would-be totals. It exits 3 and refuses if the result would exceed 2 / 12, if any other A1 instance exists (in any
    state except TERMINATED), if this instance is not RUNNING A1.Flex, or if it is already at the target.
  - `--run` (cron 02:40Z daily): acts only on or after the night in `~/.arepo/resize/schedule.json` (default 2026-10-22),
    between 02:40 and 03:05Z, and only when no `STARTED`, `DONE` or `GAVE_UP` marker exists.
    1. It touches `~/.arepo/oci_retry/DONE`, which stops the second-server retries.
    2. It pauses the queue. A pause that was already there is kept and is not lifted afterwards.
    3. It waits for the 02:31 pass's lock. If the lock is not free by 03:05 it undoes everything, moves to the next
       night and notifies.
    4. Light queue jobs (mem_mb < 500, such as the LT2 collector q0460) finish on their own.
    5. It waits for the E009/E010 poller to log its next 10-minute grid cycle.
    6. It takes the light-job locks (streams, reward params, lab push, cb12/cb15) and waits for unlocked short jobs to end.
    7. It runs `queue_worker.py stop` on heavier jobs. Their state is recorded as `stopped`: they are re-queued and the
       attempt is not counted.
    8. It holds the supervisor lock and sends SIGTERM to both monitors, which exit between cycles.
    9. It writes `~/.arepo/resize/gap.json` and re-runs the guard.
    10. It calls `compute.update_instance` with `UpdateInstanceShapeConfigDetails(ocpus=2, memory_in_gbs=12)` and
        `ALLOW_DOWNTIME`, then writes `STARTED` and notifies.
    11. It holds every lock until the shutdown ends it.

    If OCI rejects the request (`ServiceError`, for example out of host capacity), it undoes everything and notifies
    "server unchanged". A capacity or 5xx error retries the next night, up to 7 nights in total; any other error writes
    `GAVE_UP`. An unexpected error before the change also undoes everything and retries the next night.
  - `--status`, `--schedule YYYY-MM-DD`, `--install-cron` and `--remove-cron` edit only this script's own cron block,
    using Python. They take a backup in `~/.arepo/crontab.bak.<epoch>` first and verify the result.
- `post_resize_check.py` runs from AREPO venv cron, at `@reboot sleep 150` and every 10 minutes. It is idempotent and only
  acts after `STARTED` and before `DONE`.
  - It checks the shape (`nproc`, MemTotal at least 10.5 GiB, and metadata `shapeConfig`).
  - It restarts the monitors with `supervise.sh`, the normal mechanism.
  - It resumes the queue, but only if `resize_host.py` paused it.
  - It records the gap end and the measured windows in `gap.json`: the last and first E009/E010 poller cycle, missed
    120 s cycles, 10-minute grid origins with no poll, live-trade-monitor cycles, stream polls, and passes inside the window.
  - It writes `~/.arepo/resize/ledger_deviation_draft.md` (facts only) for the autopilot to append to
    `EXPERIMENT_LEDGER.md`. An aborted night that interrupted collection writes `ledger_deviation_draft_aborted_<date>.md`.
  - It notifies in plain English and writes `DONE`. If the server did not restart within 40 minutes of the accepted
    update, it reports "server unchanged".
- Log: `~/arepo_collector/logs/resize.log` (JSON lines).

**Expected impact on the night.** The 02:31 pass ends at about 02:57-03:02. The next pass is at 04:31, so no pass falls
inside the window. The light jobs pause from about 03:00 to 03:10 (the grid wait comes first), and the outage runs from
there until the reboot finishes. LT2 (E012-E014) is safe: q0460 freezes the 02:31 capture and sample only after the
queue resumes, and its late bound is the 04:31 target capture, so the resize must be done and the queue resumed by about
04:20. The post-check resumes the queue at boot, or 40 minutes after the accepted update if no restart happens. If the
host is still down at 03:30, that night's archive run is skipped, because cron does not run missed jobs, and the next
night archives as usual. The gap is an operational deviation: it is not backfilled and missing stays missing.

**Restart audit (2026-10-21).** What comes back after a reboot:

| Process | How it starts | After a reboot |
|---|---|---|
| E009/E010 `run_cross_venue_live.py`, `run_live_trade_monitor.py` | `supervise.sh` (cron `@reboot sleep 90` + `*/5`) | restarted. Stale pidfiles are detected by pid + cmdline (sandbox-tested 2026-10-21); exit 3 or `.disabled` blocks the restart |
| Collection pass (E011 score, CB extracts) | cron `31 */2`, `flock /tmp/arepo_collector.lock` | next scheduled pass; a lock file has no stale state |
| Research queue (q0460 LT2 collector, research jobs) | cron `*/2` `queue_worker.py tick` | yes. A job killed by the reboot becomes `interrupted` and is retried; the resize stops jobs first, so they are `stopped` and not counted |
| Streams, reward params, lab push, notify, outcomes, archive, oci retry | cron | next slot |
| crond, atd, sshd, firewalld, oracle-cloud-agent, swap (`/.swapfile` in fstab) | systemd / fstab, enabled | yes |
| `rota_runner.py` (not AREPO; its cron line was removed when the owner retired rota on 2026-10-14, but the process has run since June) | nothing | **will not come back**, which matches the retirement. Not restarted |
| Ad-hoc `ssh ... until pgrep ...` watcher loops from agent sessions | nothing | gone; they are transient |

**Rollback (shrink back to 1 OCPU / 6 GB).** This is the same OCI call with 1 / 6, and it restarts the server again.
On the host, at a quiet time, run `~/arepo/.venv/bin/python ~/arepo/scripts/oracle/queue_worker.py pause`, then:
```bash
~/oci_venv/bin/python - <<'PY'
import json, oci, urllib.request
r = urllib.request.Request("http://169.254.169.254/opc/v2/instance/", headers={"Authorization": "Bearer Oracle"})
iid = json.load(urllib.request.urlopen(r))["id"]
c = oci.core.ComputeClient(oci.config.from_file()); m = oci.core.models
c.update_instance(iid, m.UpdateInstanceDetails(shape_config=m.UpdateInstanceShapeConfigDetails(ocpus=1, memory_in_gbs=6),
                                               update_operation_constraint="ALLOW_DOWNTIME"))
PY
```
After the restart, run `supervise.sh` (or wait for its `@reboot` entry) and `queue_worker.py resume`. Record the change in
the ledger.

If the host does not come back, the OCI API key exists only on the host. Use the console instead (sign-in details in the
operator notes; tenancy `dayyanatifsheikh`, region uk-london-1): Compute, then Instances, then `dsheikh`. Start the
instance, or use Edit and then Shape. Cancel a scheduled run that has not started yet with
`touch ~/.arepo/resize/GAVE_UP`; remove the cron block with `resize_host.py --remove-cron`.
