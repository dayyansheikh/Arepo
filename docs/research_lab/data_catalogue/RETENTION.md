# Server retention (deletion APPROVED by the user 2026-10-15; dry run first)

**User approval (2026-10-15, about 21:10 UTC+1):** "If the copy is uploaded to GitHub, recorded properly and verified, then go ahead
and delete them." The user also approved the weekly backup of the live evidence logs, which is installed.
- **Scope:** only host files whose bytes are in a verified published release (identical sha256), under the rules in
  `scripts/oracle/archive_retention.json`. This includes the deferred `snapshots/` and `book_sweeps/` rules once their gate
  clears (queue jobs q0005, q0006a and q0006 are done or take root arguments).
- **Never deleted:** frozen or prospective evidence, active or append-only logs, and `/home/opc/arepo_val`.
- **State (checked 2026-10-16 23:10-23:55Z, recorded 2026-10-17 00:55 UTC+1): deletion NOT enabled; the gate FAILS on CB4.**
  - Checklist 1 PASS: `data-20261016-dsheikh` (31,758 files, 2.00 GB) verify PASS 03:52:08Z, published 03:52:12Z (not a
    draft; README.md, VERIFY.json, files.sha256, MANIFEST.sha256 and the part are on GitHub), in `verified_releases.jsonl`
    (as are `data-20261015-dsheikh` and `-active`). The catalogue tables in this folder do not list 10-16 yet (regenerate
    with `archive_catalogue.py`; not a deletion precondition, `archive_rotate.py` re-checks GitHub against the ledger).
  - Checklist 2 PASS: `pair_cache_status()` = 66/66 cached, 67/67 request-time spans, `complete: True`.
  - Checklist 3 PASS: dry run 10-16 03:52Z (`deleted 0, kept 78, kept_by_rule 32,795, dry_run true`). `deletions.jsonl`:
    86 `would_delete`, all `trade_samples/` (`features`/`trades`/`wallets.csv.gz`, `wallets_manifest.json`; 429 MB) of
    samples 10-11T01:07Z..10-13T02:46Z, i.e. older than 3 days; 72 newer samples and 6 `live_trades/scores-` files kept
    "too recent"; no other directory; manifest/plan kept by rule.
  - Checklist 5 PASS: `collector.log` 23:02Z shows `E007: Pending - 58 of 12 qualifying periods`, `"qualifying": 12` and the
    `F4_max_trade ...` flow-screen line as before.
  - Snapshot/sweep gate (`backend/scripts/retention_gate_check.py`, run on the host 23:39Z): q0005, q0006a, q0006 done.
    CB1 q0030: 60/61 extracted; CB2 q0041: 60/61 written; CB3 q0060: 57 extracted + 1 missing `no_host_manifest` of 58
    (complete). The one capture CB1/CB2 do not list is `20261013T231958Z_80e78ef1`, release-only (its raw copy is in
    `/home/opc/arepo_val`, which is never a deletion target, and in `data-20261015-dsheikh-val`), so deletion cannot touch
    it. **CB4 q0080 FAILS:** 30/61 extracted; 28 host captures from `20261014T123101Z_2f1802b6` on are unaccounted (+2
    recent, +the release-only one). q0080 is `done` by job status but every run ended `backfill_complete: false,
    stopped: release_unavailable` (oldest first, it stalls on the release-only capture, which lives in the separate val
    ledger), and the pass step was not wired.
  - Pass step: the CB4 line (CREATIVE_BATCH_4.md implementation note 13) is now in `scripts/oracle/arepo_pass.sh` after the
    CB1 extract line (committed with this update; **not deployed**). `run_cb4.py closewin --all-new` exists in the deployed
    tree; it skips the catalogue scan, so it extracts the 28 host captures oldest first (7 min budget per pass) and never
    stalls on the val capture.
  - Readers needing raw files longer than the deferred rules (section "Gate release"): q0035 (J4-R, not before
    10-21T03Z) reads sweeps of 10-16..10-21 with default roots, and the MC1 dev run (q0110/q0111) rebuilds its panel from
    sweeps and snapshots since 10-14T12:31Z. **The 3-day sweep rule must stay deferred** (it would delete 10-16 sweeps from
    10-19 03:30Z and 10-14 sweeps from 10-18 03:30Z).
  - Proposed rules, isolated host dry run (`--no-archive`, copied ledger in `/tmp/rdry_state`, so the live
    `deletions.jsonl` is untouched), 23:40-23:41Z, both deferred rules moved into `rules` in `/tmp/proposed_retention.json`:
    `would_delete` 78 `book_sweeps/` files (347 MB, sweeps 10-10T19:42Z..10-13T22:51Z) and 126 `trade_samples/` files
    (612 MB, samples 10-11T01:07Z..10-13T22:56Z); `snapshots/` 0 (oldest host capture is 6.2 days old; 89 archived
    snapshot files, 2.74 GB, kept "too recent"); kept 143 (all "too recent or link", none "hash differs"), kept_by_rule
    32,612; no other directory. Every listed file is in a verified release with an identical sha256 and older than its
    rule.
  - Free space without snapshot deletion: about 9.7 GB at 10-16 23Z, +0.9-1 GB a day, so the 12 GB cap is reached about
    10-19 midday; the trade-sample rule alone (remove `--dry-run`) frees 0.61 GB on the first run. Snapshot files past 8
    days (existing files): 0.17 GB at 10-19 03:30Z, 0.79 at 10-20, 1.54 at 10-21, 2.19 at 10-22, 2.74 at 10-23.
  - **Exact next action (coordinator):** deploy (`scripts/oracle/deploy.sh`); after 1-2 passes rerun
    `cd ~/arepo/backend && ../.venv/bin/python scripts/retention_gate_check.py`. When it prints `"retention_gate": "PASS"`,
    move ONLY the `snapshots/` entry from `deferred_rules` to `rules` (8 days, keep manifests), remove `--dry-run` from the
    nightly line, run `tests/unit/test_archive_rotate.py`, deploy and install the crontab line, all before the 10-19 03:30Z
    run. `book_sweeps/` stays deferred until q0035 is done and the MC1 q0111 panel is cached.

Status 2026-10-15: the nightly rotation (`backend/scripts/archive_rotate.py`, cron 03:30 UTC) is **archive-only**. This file says
what may be deleted from the host's own copy once `--delete` is switched on, and what had to change so that deleting never
changes what a registered experiment sees. Nothing here is enabled. The rules are in `scripts/oracle/archive_retention.json`
and are applied by `archive_rotate.py --retention <file> --delete`.

Hard rules that stay in force (unchanged from `COLLECTION_HOST.md`): a server file is deleted only if it is in a **verified**
release, that release on GitHub still matches the ledger and is published, the file's current sha256 equals the archived one,
and it is older than the rule's cut-off. Directories without a rule are never deleted. `older_than_days` must be at least 2.

## Who reads what (derived from the code, 2026-10-15)

| dir | live / scheduled readers on the host | what they need |
|---|---|---|
| `snapshots/` | every 2h pass: `run_forecast predict`, `sweep_books`, `sample_trades` (latest capture only); `run_surprise_snapshot score` (E011: `bootstrap_series` re-reads captures newer than `SERIES_KEEP_S` = 7.5 days that are not yet in its series); `run_flow_screen` and `run_research_e007 --status` (every sample: source and next capture `rows.csv.gz`); `run_research_e004 --status` (`forecast.list_complete_captures`: manifests only; E004/E005/E006 are scored, results exist) | latest capture; captures up to 7.5 days old for E011; **all** `manifest.json` (capture list, provenance hashes); source/target rows for the flow screen and E007 status, now served from `pair_cache/` |
| `trade_samples/` | `flow_screen.build_all` and `e007.status` every pass: `manifest.json`, `plan.json`, `features.csv.gz` (also `sample_meta` request-time span) | manifest and plan always; features through the cache |
| `book_sweeps/` | queue jobs q0005, q0006a, q0006 (`leadlag_screen.py`, `bounce_decomp.py`; `run_bounce_decomp.py` hardcodes the roots) read **all** sweeps and **all** captures; no other scheduled reader (E003 is complete; D118/D120 scripts one-off) | all sweeps while those jobs are open |
| `live_trades/` | `live_trade_monitor` restart: `trades-<day>.jsonl` for today and yesterday, `scores-*.jsonl` rows newer than `trailing_days` = 7, all of `wallets.jsonl`, `alerts.jsonl`; `--outcomes` (twice a day): `alerts.jsonl`; `arepo_notify`: `alerts.jsonl`, `stats.jsonl`, `outcomes.jsonl` | the append-only logs always; daily `trades-`/`scores-` files only while recent |
| `cross_venue_live/` | E009/E010 collector and outcome writer: `predictions*.jsonl`, `outcomes*.jsonl`, `quotes/`, `pairs_current.json`; `analyze` after the fixed end 2026-11-03 reads the whole stream | everything until the analyses are done |
| `surprise_live/` | E011: rolling series, `alerts.jsonl`, `outcomes.jsonl`, `analyze` after 2026-11-10 | everything (18 MB) |
| `forecasts/`, `flow_screen/`, `e00x/`, `calibration`, `pair_cache/` | small outputs and registered results | everything |
| `history/`, `history_sources/`, `cross_venue/`, `resolution_dev/`, `if_h2/`, ... | queue jobs q0002-q0004 (`history/h2_main`, `history_sources/book_features`), development studies | everything; not deletable until the queue and the studies are done |

## Proposal

| dir | rule (`--retention`) | local copy kept | why this number |
|---|---|---|---|
| `snapshots/` | **GATED: no rule now** (deferred: 8 days, keep `*/manifest.json`, `*/ext_manifest.json`) | all | E011 needs 7.5 days; q0005/q0006a/q0006 are done (2026-10-15). Activate the deferred rule (`deferred_rules` in the JSON) when `retention_gate_check.py` prints PASS (see "Gate release" for the MC1 and CB3-live deadlines) |
| `trade_samples/` | **3 days**, keep `*/manifest.json`, `*/plan.json` | 3 days of `features.csv.gz`, `trades.csv.gz` (about 0.6 GB) + manifest/plan (about 0.7 MB each) | nothing reads features after the pair is cached (about 2h after the sample) |
| `book_sweeps/` | **GATED: no rule now** (deferred: 3 days, keep manifests) | all | q0005/q0006a/q0006 are done (2026-10-15); still deferred because q0035 (from 10-21T03Z) and MC1 panel rebuilds read older sweeps (see "Gate release") |
| `live_trades/scores-*`, `live_trades/trades-*` | **10 days** | the 7-day score history the monitor reloads, plus margin | `trailing_days` = 7; `trades-` only needs today and yesterday |
| `cb1_extract/` and everything else | **never deleted** | all | read by open experiments or small |

**Capacity consequence of the gate:** with snapshots not deletable the data grows about 0.75 GB a day from snapshots alone; deleting samples (3 d) and live_trades frees little. The 12 GB cap (about 22 October) is then NOT avoided unless the queue jobs finish or accept a root argument first. Decision needed from the user/other session before about 20 October.

Estimated steady state once the deferred rules are active: snapshots about 6.1 GB, samples 0.9 GB, sweeps 0.4 GB, live_trades 0.5 GB,
`cross_venue_live` 0.3 GB and growing about 25 MB a day, `history*` and `cross_venue` about 1.2 GB, rest about 0.3 GB: **about 9.7 GB,
under the 12 GB cap** (today 7.06 GB, growth about 1.1 GB a day). Without deletion the cap is reached about 22 October. The first
snapshot deletions only start when captures turn 8 days old (from 18 October), so enable deletion by about 17-18 October; the sample and
sweep rules free about 1 GB immediately.

## Reader changes made so that deletion cannot change a result (all tested, in this commit)

1. **Pair cache** (`flow_screen.build_sample_pairs`). While the raw files exist the function computes exactly as before and
   also stores the resulting frame in `research_lab/pair_cache/<sample>__<hash>.pkl` (a write-only side effect; the hash covers the
   sample and capture manifests and the plan). When the raw files are gone it returns the stored frame (pickle, so identical values;
   `period` is re-stamped like a fresh call). With no stored frame it raises `forecast.ArchivedDataError` with the restore
   command, instead of skipping the sample.
2. **E007 `sample_meta`**: the request-time span (`first_sent`, `last_sent`, used by the E007 qualification rule) is read from
   `features.csv.gz`; without it the old code silently fell back to the sealing times, which would have changed which periods
   qualify. It now stores the span next to the cache the first time it sees a complete sample, uses it when `features.csv.gz` is
   gone, and raises `ArchivedDataError` if neither exists.
3. **E011 `load_capture`**: a capture that has an `ext_manifest.json` but no `rows_ext.csv.gz` raises instead of loading the fee
   category as `unknown`. `forecast.load_snapshot` also raises `ArchivedDataError` for a missing `rows.csv.gz`.
4. **`archive_rotate.py --retention`**: per-directory `older_than_days` and `keep` globs; directories without a rule are not deleted;
   a rule below 2 days is refused. The decision for a stub or rule-protected file is counted (`kept_by_rule`), not logged per file.
5. `list_complete_captures` needed **no change**: the manifests stay on the host (keep globs), so E004-E006 status, E007 pairing
   and provenance hashes (`sha256(manifest.json)`) see exactly the same list.

Final analyses (E009/E010 after 2026-11-03, E011 after 2026-11-10, any re-run of E003-E007, ML development on old snapshots)
**restore first**: `python3 backend/scripts/restore_from_archive.py --experiment E011 --dest ~/restore_e011` (see `README.md`), then
point the reader at the restored copy. Readers with root arguments: E004/E005/E006 (`--snapshot-root`), E007 (`--sample-root`, `--snapshot-root`), `run_flow_screen.py` (`--snapshot-root`, `--trade-samples-root`), `run_leadlag_screen.py` (`--snapshot-root`, `--dev-dir`), `run_bounce_decomp.py` (`--snapshot-root`, `--sweep-root`); a missing listed rows file raises `ArchivedDataError`. The rest (E011, E009/E010 `analyze`, E003, ML scripts) use the default roots: restore with `--dest <scratch repo root>` so the files land under a repo-like `data-dumps/research_lab/`, never the live tree. The restore re-hashes every file.

**Gate release:** snapshot rows and book_sweeps stay non-deletable until queue jobs q0005, q0006a and q0006 are done; snapshot rows additionally until the CB1 extractor is live and its backfill over captures since 10 October has caught up. `cb1_extract/` (MB-scale per-capture extract) is never deleted (no rule). **Added 2026-10-16 (autopilot):** the same snapshot/sweep gate also waits for the creative-batch backfills that preserve inputs before deletion: CB2 q0041 (`cb2_extract/ladder_candidates/`), CB3 q0060 (`cb3_extract/quote_state/`, captures before 2026-10-15T21Z) and, once queued, CB4 q0080 (`closewin`, CREATIVE_BATCH_4.md §2.10). `cb2_extract/` and `cb3_extract/` are never deleted (no rule). The gate opens on **manifest completeness, not job status**: each backfill's manifest must show every complete capture in its window (host manifests and release-only captures reconciled) as extracted or missing with a reason (CB3 freeze-check fix 2). After that they become deletable at 8 days (snapshots, keep manifests) and 3 days (sweeps, keep manifests) by moving the `deferred_rules` in `scripts/oracle/archive_retention.json` into `rules`, because those runners can now read a restored scratch root. **CB4 §2.10(b) (added 2026-10-17):** CB4 places no requirement on the snapshot and sweep rules once (a) q0080 is done **and its manifest is complete** and (b) the live pass step `run_cb4.py closewin --all-new` (in `arepo_pass.sh` from this date) writes `closewin` and `departures` each pass, which happens before the 3-day and 8-day ages by construction. The check is reproducible: `backend/scripts/retention_gate_check.py` prints per backfill the universe (host complete captures plus release-only captures from the catalogue), extracted, missing-with-reason, and unaccounted captures split into `at_risk` (host raw under the deletion root: gate FAILS), `pending_recent` (< 4 h, next pass) and `release_only` (raw not under the deletion root). **Further conditions found 2026-10-17 (they hold even after the gate passes):**
- `book_sweeps/` (3 days) stays deferred until (1) q0035 J4-R is done (it runs from 10-21T03Z over captures 10-16..10-21 and reads their sweeps with the default `--sweep-root`) and (2) the MC1 real run q0111 has cached its panel (`ml_cache/<panel hash>/panel.parquet`). `run_ml_dev.get_panel` reads the raw sweep `rows.csv.gz` of every origin capture whenever the panel hash changes (new capture list, code change, `--rebuild`); a missing file raises. After the sweep rule is live, an MC1 rebuild must restore the sweeps first and pass `--sweep-root`.
- MC1 and snapshots (8 days): `run_ml_dev.sidecar_version` treats a capture whose `rows_ext.csv.gz` is gone as "no sidecar" (no error), so after deletion the capture silently leaves the consecutive run and the panel hash. MC1 must cache its q0111 panel before 2026-10-23 03:30Z (when captures from 10-14T12:31Z pass 8 days); any later MC1 run must use a restored `--snapshot-root`, or the reader must first raise `ArchivedDataError` when only the manifests remain.
- CB3 live: the `quote_state` pass step (CREATIVE_BATCH_3.md §4.3.2) is not wired, so no capture since 10-15T21Z has a `quote_state/` row. The first of them passes 8 days on 2026-10-24 03:30Z (`retention_gate_check.py` prints this deadline). Wire the step before then, or CB3 must restore those captures from releases.
- Exploratory MC1 flow/wallet families (`--families flow,wallet`, not MC1 itself) read `trade_samples/*/wallets.csv.gz`; the existing 3-day trade-sample rule removes them, so such runs cover only the last 3 days unless restored.

## Before enabling `--delete` (checklist for the user)

1. `README.md` shows the latest nightly release as PASS, and `~/.arepo/archive_rotate/verified_releases.jsonl` has it.
2. Pair cache and request-time spans complete (must print `complete: True`, which also needs `sent_spans_cached == complete_samples`; run on the host after one pass with the new code):
   `cd ~/arepo/backend && ../.venv/bin/python -c "from astrolabe.research_lab import flow_screen as f; print(f.pair_cache_status())"`
3. Dry run for one night: add `--retention /home/opc/arepo/scripts/oracle/archive_retention.json --delete --dry-run` to the cron
   line, then read `~/.arepo/archive_rotate/deletions.jsonl` (`would_delete` rows) and the summary line in `archive-rotate.log`
   (`kept_by_rule`, `would_delete` counts). Expect only files older than the rule, in the directories above.
4. Remove `--dry-run`. The first real run deletes only files whose bytes are verified in a published release.
5. After the next pass, check `collector.log`: the E004/E007 status lines and the flow-screen line must look as before
   (`E007: Pending - N of 12 qualifying periods`, `F4_max_trade ...`).

## Open risks to decide

- **Growing append-only logs are not backed up until they go idle.** `cross_venue_live/predictions*.jsonl`, `outcomes*.jsonl`,
  `live_trades/alerts.jsonl`, `wallets.jsonl`, `surprise_live/*` are appended continuously, so their mtime is always newer than the
  1-day archive cut-off and the nightly run skips them. They are prospective, irreplaceable evidence (E009/E010/E011). Implemented, **not installed**:
  `archive_rotate.py --include-active GLOB[,GLOB...]` archives a point-in-time copy of matching files that are still newer than
  the cut-off: bytes up to and including the last newline (a half-written line is never archived), read-only on the live file,
  staged as `active_snapshots/<UTC stamp>/<original path>` plus a sidecar `ACTIVE_SNAPSHOT.json` (`active_snapshot: true`, original
  path, bytes copied, sha256 of the copied prefix, copy time), published through the normal build, verify-before-publish and ledger
  path as release `data-YYYYMMDD-<host>-active`. The catalogue flags these rows (`active_snapshot`, `original_path`; capture time =
  copy time) and `restore_from_archive.py` lists/extracts them like any member. An unchanged prefix is not re-archived. These files
  are never deletion candidates (ledger entries marked `active_snapshot` are skipped, and any path with a recorded snapshot or
  matching the globs is protected, even after it goes idle). A commented weekly cron line is in `scripts/oracle/crontab.txt`;
  installing it is pending user OK.
- Rotation re-archives `history/` (about 0.75 GB) that already exists in `data-20261013-research-lab`; harmless duplication.
- `/home/opc/arepo_val` (E009/E010 outage-gap evidence) is archived by its own run (`--root /home/opc/arepo_val`) and is never a
  deletion target.
