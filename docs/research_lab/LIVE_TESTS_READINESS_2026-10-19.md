# Live tests readiness audit (E009, E010, E011), 2026-10-19

Written 2026-10-19 22:54 UTC+1 (host checks 21:43–21:52Z). Branch `feat/live-audit`. This is an audit document, not a
protocol. It changes no frozen protocol, evidence JSON, threshold or registered statistic.

**Blinding.** Nothing below looks at an outcome value, effect size, hit rate or test statistic on live data. The host checks
read only line counts, `t`/`t0`/`due`/`capture_t` timestamps, ids, `role`/`evidence_role`, receipt times (`kr`, `pr`, which are
operational exclusion inputs), event ids and key sets. They did not read outcome `status`, `dp`, P&L, `hit_*`, moves, mids or
predictions. The scripts were piped to the host on stdin and wrote nothing there.

**Scope.** The registered live tests are E009, E010 and E011: `stage: live_test`, `status: collecting` in
`lab_dashboard/registry.json`, and `REGISTERED (pre-outcome)` in the ledger. E005 is a closed `live_test` (scored 2026-10-11).
E004, E006 and E007 are scored. No CB-series design is frozen as a live test, so none is in scope (CB3 freezes after 10-25 at
the earliest).

## Summary

| Test | Analysis | Ready? | Blocking items | Sample so far (counts only) | Projection to window end |
|---|---|---|---|---|---|
| E009 | once, after 2026-11-03T02:00Z | **Not yet**: one blocker, two to-dos | B1 gap-fill code missing; R1 analysis memory | 39,684 non-late 20-min-grid origins, 51 events | about 130,000 origins (plan 100,000; minimum 5,000 evaluated), 50+ events (minimum 20) |
| E010 | once, after 2026-11-03T08:00Z | **Not yet**: same blocker | B1 gap-fill code missing (B1 is biggest for the 6h horizon) | 13,059 non-late hourly origins, 51 events | about 43,000 per horizon (plan 34,000; minimum 2,000) |
| E011 | once, after 2026-11-11T13:00Z | **Ready** after fix F1; secondaries incomplete | none blocking; S1 secondaries | 4,200 alert lines, 70 captures, 837 episodes, 377 clusters | about 19,380 lines (target 19,700, 98%), about 3,600 episodes (plan "> 4,000") |

## 1. Frozen artefacts (all match)

Everything below was verified by `tests/test_live_tests_readiness.py::test_frozen_artefacts_and_constants_match_registration`
and by hand.

| Artefact | Registered | Committed file / code |
|---|---|---|
| E009 spec `model_specs/cross_venue_live_v1.json` | `e63f20cc…6e2b` | match (file sha256 = pinned `SPEC_SHA256`; host start log `spec=e63f20cc095b`) |
| E009 hand verdicts `cross_venue_live_verified.json` | `1d6f942a…ac54c` | match: unchanged since registration, so no verdicts were added in the window |
| E010 spec `cross_venue_live_e010_v1.json` | `62b992c6…961c` | match (host log `E010 writer on: spec=62b992c6af95`) |
| E011 rule `sm_learned_v2` (`FROZEN_SURPRISE_SNAPSHOT.json` entry) | `ee227e7e…4c14ef1` | match (recomputed `RuleSpec.sha256()`; the index file's own sha is `5c095deb…`, not a registered value) |
| E011 `STAGE1` | `2f5ef241…84a679c5` | match |
| E011 `SnapshotConfig` hash | `7087fec7c4f95feb` | match (cap 400 candidates, 60 alerts, 3 controls) |
| Windows | E009 `[2026-10-13T00:00Z, 11-03T00:00Z)`; E010 `[10-13T02:00Z, 11-03T00:00Z)`; E011 captures `[10-13T14:00Z, 11-10T00:00Z)` | match (constants and `analyze` defaults) |
| Bootstrap | E009 4,000 / seed 20261012; E010 4,000 / 20261013 + h; E011 4,000 / 20261013 | match |

**Code since registration.** `cross_venue_live.py`, `cross_venue_live_e010.py` and `run_cross_venue_live.py` are unchanged
since `9beda37`, the E010 registration. Its E009-side change, the hook and `RETIRE_KEEP_S`, is logged in the ledger.
`run_surprise_snapshot.py` is unchanged since `3e628ec`. Later changes to dependencies were checked line by line, and none
changes a registered computation:

- `surprise_snapshot.py`: `afd67c3` added the archive-aware `require_local`, which raises instead of reading an archived
  sidecar as "unknown". This audit adds F1.
- `economics.py`: `REBATE_SHARE`, `cost_regime` and `planning_band_map` were added. `taker_fee`, `MIN_TRADES` (30) and
  `MIN_CLUSTERS` (10) are untouched.
- `cross_venue.py`: `AUDIT_CONFLICT` and `audit_conflict` were added. The matcher's `CONFLICT` is unchanged.
- `ml_explain.cluster_boot`: an optional `weights` argument was added. The unweighted path is identical.
- `history_backfill.Limiter.get`: an optional `max_retries` argument was added (operational only).

**Running code.** The host poller has run as one process since 2026-10-14T11:32:29Z, on the code it started with. There
have been 3,906 cycles and no restarts. The log has 0 `cycle failed`, 0 `extra writer` failures and 0 RSS-budget warnings.
The last cycle was 2.4 s at 187 MB.

## 2. Code against the registered analysis

### E009 (`cross_venue_live.analyze`, `--analyze START END`)
Matches:

- Primary G = 1 − SSE(M1)/SSE(M0) on `t % 1200 == 0` origins in `[start, end)`, role `prospective_confirmation`, status
  `evaluated`.
- Event-clustered bootstrap (Polymarket event id) with a percentile CI.
- Hygiene: dedup on `(id, h)` keeping the first line; `kr`/`pr` lag > 60 s gives `origin_late`; outcome receipt lag > 60 s
  is `unavailable`; due-but-absent lines are `missing_line`.
- Secondaries at 10 and 60 min, simple and partial dk1 slopes, largest-event share, leave-one-event-out range.
- Executable P&L with the 30-trade/10-cluster minimum, plus the descriptive |dk1| >= 2c companion.

Discrepancies and notes:

- **B1 (blocker): the user's gap-fill decision has no implementation.** The decision is dated 2026-10-15T18:31Z and recorded
  in the ledger's "Operational deviation" section. It says:
  - The validation copy `/home/opc/arepo_val` fills 2026-10-14 00:02Z–10:44Z.
  - Substituted rows carry `source=validation_copy`.
  - A sensitivity result excluding the window is reported.

  `analyze` reads one root and knows nothing of the copy. Before 11-03, a merge step must be written, reviewed and
  committed. It should never edit either source, should write a merged analysis root, and should then run `--analyze`
  twice (merged = primary, canonical-only = sensitivity). **One rule question must be settled in writing first, before
  anyone looks at results.** Some origins precede 00:02Z but their outcome falls due inside the window. The canonical stream
  holds lines written for them when the Mac woke; the copy holds its own lines for the same `(id, h)`. Counted on the host
  by `t0`/`due` only:
  - E009: 74 lines at 20 min (20-min grid), 74 at 10 min, 221 at 60 min.
  - E010: 74 lines at 1h and **299 at 6h** (origins 18:00Z–00:00Z).

  Option (a) replaces only rows whose origin is in the window. Option (b) also replaces outcome lines whose due is in the
  window. Option (b) is the closer reading of "where the canonical stream has no valid quotes". The ids are deterministic
  (`pid|t`) and identical in both streams, so the merge must pick per `(id, h)` explicitly; concatenating the files would
  feed the dedup's "first line kept" rule by file order.

  Also record:
  - The copy has its own 3-cycle gap (00:28–00:34Z).
  - Its files also contain Mac rows synced before 23:22Z; only rows inside the rule are used.
  - E009 hour 11:00Z and E010 origin 11:00Z stay missing: canonical warm-up, outside the rule.
- **D1 (not in the ledger): extra canonical gaps on 2026-10-13.** Prediction cycles stop 21:24–22:22Z and 22:28–23:12Z (Mac),
  so E010 has no 22:00Z or 23:00Z origin. The validation copy started at 23:33Z and cannot cover these gaps. Missing stays
  missing. Recommend one deviation line in the ledger, counts only.
- **N1: no verdict function in code.** The verdict comes from the ledger table by hand. Mapping:
  - **Unavailable** if `horizons["20"].n_clusters < 20` or `horizons["20"].n_origins < 5,000`.
  - **Supported** if `p_one_sided < 0.05` and `rel_mse_gain > 0` and the "dk1 slope point estimate > 0". The plain reading is
    `slope_dp_on_dk1`, the simple slope. **Confirm this reading in writing before 11-03.**
  - **Contradicted** if `ci[1] < 0`. It becomes "lead present, frozen scale miscalibrated" if `partial_slope_ci[0] > 0`.
  - **Economics:** "covers taker costs (paper)" only if `executable_pnl.status == "ok"` and its `p_one_sided < 0.05` with a
    positive mean.
- **N2 (minor, frozen code):** p = (#{G* <= 0} + 1)/(B + 1), not the bare share. This differs by < 0.00025 at B = 4,000. A
    bootstrap G* that is NaN (SSE0 = 0, practically impossible) counts as > 0. Leave both as frozen.

### E010 (`cross_venue_live_e010.analyze`, `--analyze-e010 START END`)
Matches:

- Hourly origins.
- G for M1 and for M-gap at 60 and 360 min, seed 20261013 + h.
- Holm with m = 2 always; a missing horizon enters with p = 1.
- The same hygiene.
- Per-horizon executable P&L.

Discrepancies and notes:

- **B1** applies, and is biggest at the 6h horizon (299 lines).
- **N1:** the verdict is by hand from `holm_m1[h]`: Supported if `holm_m1[h] < 0.05` and `rel_mse_gain_m1 > 0`;
  Contradicted if `ci_m1[1] < 0`; Unavailable if `n_clusters < 20` or `n_origins < 2,000` at that horizon. A horizon that
  `analyze` marks `insufficient` (< 2 clusters) enters Holm with p = 1, as registered.

### E011 (`surprise_snapshot.analyze`, `run_surprise_snapshot.py analyze`)
Matches:

- Window by `capture_t`, whole captures in or out at both edges, role filter.
- Episode = first alert line of a market, with later lines less than 24 h apart collapsing. Collapse is chained from the
  previous line, not anchored on the head; that is the frozen code's reading of "closer than 24 h", and the test pins it.
- A dropped head is never replaced.
- Controls are the evaluated controls of the head.
- Excess = alert hit_6h − mean control hit_6h; `cluster_boot` with 4,000 resamples, seed 20261013, `p_pos`.
- Verdict rules as registered, including Unavailable at < 30 episodes or < 10 clusters.
- Pending lines are never imputed.

Fix and discrepancies:

- **F1 (fix applied, restores the registration exactly):** "cluster = Gamma event id (market id when absent)". Alert lines
  store `str(row["event_id"])`, so a capture row without an event id arrives as the string `"nan"`. The old
  `a.get("event_id") or a["market_id"]` treats `"nan"` as present, which would pool all such markets into one `"nan"`
  cluster. `_cluster_id()` now treats `"nan"`, `"None"`, empty and null as absent. Effect on collected data today: **none**,
  because 0 of 4,200 window alert lines carry a missing-like event id. The host's latest capture has 1 such row in 246,961,
  so it can happen. The test is `test_e011_missing_event_id_falls_back_to_market_id`. The host runs the deployed tree, so
  analysis must run from a commit that contains F1.
- **S1 (registered secondaries that `analyze` does not output; descriptive only, no verdict role):**
  - (c) the 2h label (`hit_2h` excess);
  - (e) a sports vs non-sports split (only `by_fee_category` exists);
  - (f) the `control_match` composition (today all 13,140 controls are `stratum`);
  - (g) passes missed and the request/timing statistics (they are in `passes.jsonl`).
  - (d) is computed for alerts only, with no control rate.

  Recommend a small, pre-declared descriptive supplement that reads the same files, committed before 11-11 and listed as
  a secondary. It must not touch `analyze`.
- **N3:** duplicate outcome lines resolve as last line wins (dict). The host has none (0 duplicate `alert_id`s), and
  `write_outcomes` writes only `evaluated`/`unavailable` once each. Note only.
- **N4:** `SnapshotConfig.day_cap_bytes`/`total_cap_bytes` are not enforced anywhere, so there is no early-stop risk.
  `surprise_live` is 47 MB.

## 3. Tests added (synthetic, schema-shaped)

New file `backend/tests/test_live_tests_readiness.py`, 7 tests. All lines are produced by the real writers from seeded,
generated quotes and series.

1. Frozen hashes and registered constants for all three tests.
2. **E009 end to end.** A real `Poller` with the E010 writer, real frozen specs, 7 pairs and 4 events. It replays the
   10-13/10-14 timeline:
   - Mac cycles 21:00Z–00:02Z, no cycles until 10:44Z, the same process resumes.
   - **Host move:** a new process at 11:31Z with recovery, and the 11:30Z grid point lost.
   - A supervise restart at 15:03Z with 1h and 6h outcomes pending.
   - A late-receipt cycle (13:00Z, +75 s) and a one-sided book interval.

   It checks:
   - No duplicate lines across restarts.
   - The first post-outage prediction comes at 11:44Z (60-min lookback).
   - Outcomes due in the outage are written `unavailable`.
   - `missing_line` is 0.
   - Per horizon, **evaluated + unavailable + missing = non-late grid origins**.
   - `origin_late` and `unavailable_late_receipt` are counted exactly.
   - The result is deterministic.
   - Dedup keeps the first line: an appended conflicting duplicate leaves G unchanged.
   - Start is inclusive and end exclusive; unregistered-role rows are excluded.
3. **E010** on the same stream:
   - No 6h origin in the outage.
   - 6h lines due in the outage are `unavailable`.
   - The 12:00Z 6h line is written by the restarted process at its exact due quote.
   - The same accounting identity holds.
   - Holm uses m = 2 and adjusted p >= raw p.
   - The late origin is counted.
4. **E011 end to end** through `Scorer.run_pass` and `write_outcomes`. It uses 5 captures: one before REGISTERED_UTC, and a
   missed 18:31Z pass. It checks:
   - `already_scored` makes reruns idempotent.
   - Before due there are no lines; the outcome passes repeat with no duplicates.
   - The statuses are correct: empty 200 means unavailable after 12 h; 503 stays pending.
   - The accounting sums, the window, episode collapse, and the Unavailable verdict at < 30 episodes.
5. **E011 rules:**
   - Chaining: 0/20/40 h lines form 1 episode and the 65 h line a 2nd.
   - The END edge (`capture_t` = END is out, END − 1 s is in) and unregistered roles.
   - The Contradicted, Inconclusive and Unavailable (< 10 clusters) paths.
6. F1 (missing event id).
7. Pending lines are never imputed and dropped heads are counted.

Result:
`pytest -q tests/test_live_tests_readiness.py tests/test_research_lab_cross_venue_live.py
tests/test_research_lab_cross_venue_live_e010.py tests/unit/test_research_lab_surprise_snapshot.py` gives **38 passed**, and
`ruff` is clean.

## 4. Collection completeness on the host (counts only, 2026-10-19 ~21:44Z)

**E009 (`cross_venue_live/predictions.jsonl`, 228 MB).**
- 399,266 lines: 396,563 `prospective_confirmation`, 2,703 pilot. 0 bad JSON lines, 0 duplicate ids.
- 2 key sets (pilot lines lack `code`).
- Non-late 20-min-grid origins: **39,684**, and 0 late. Per day: 10-13 5,035; 10-14 2,899 (outage); 10-15 5,735; 10-16
  5,943; 10-17 6,601; 10-18 7,046; 10-19 (to 21:44Z) 6,425.
- 51 distinct events, 23–46 per day.
- Hours without cycles: 10-14 01:00–10:00Z (the documented outage).
- Thin hours, as cycles out of 30: 10-13 21:00 (13), 22:00 (4), 23:00 (24); 10-14 00:00 (2), 11:00 (8). The 10-13 gaps are D1.

`outcomes.jsonl`: 238,485 lines (about 79k per horizon), 0 duplicate `(id, h)`, 0 bad lines.

**E010.** Predictions: 13,210 lines (13,059 confirmation), 0 duplicates, all on the hourly grid, 0 late, 51 events. Hours
without an origin: 10-13 22:00 and 23:00 (D1); 10-14 01:00–11:00 (outage plus warm-up). Outcomes: 25,740 lines (13,113 at
60 min and 12,627 at 360 min), 0 duplicates.

**Validation copy** (`/home/opc/arepo_val`, 363 MB, present). Outage window 10-14 00:00–11:00Z: 2,508 E009 20-min-grid
origins (25 events) and 836 E010 hourly origins. No duplicates.

**E011 (`surprise_live`).**
- `alerts.jsonl`: 4,380 alert and 13,140 control lines. 180 alert and 540 control lines are pre-registration dry runs.
- 70 window captures, 60 alerts each, 3 controls per alert, 0 shortfalls, 0 duplicate ids, 0 missing-like event ids.
- One capture gap, 10-13 22:31Z to 10-14 12:31Z: the 6 documented missed passes. No other pass is missed (76 slots − 6 = 70).
- 73 passes, all `ok`.
- Outcomes: 14,639 lines, 0 duplicate `alert_id`. 1 line is 2 h past due without an outcome line (normal retry lag).
- Episodes so far (counted from alert lines only): **837** in **377** event clusters. About 130 per day on 10-15..10-18.

**Mac→Oracle deviation (2026-10-14).**
- Confirmed: the canonical stream has no cycles 00:02Z–10:44Z, resumes 10:44Z and has predictions again from 11:44Z.
- The host process started 11:32:29Z.
- E011 is missing the 6 passes 00:31Z–10:31Z.
- Not in the ledger: the 10-13 21:24–22:22Z and 22:28–23:12Z canonical gaps (D1).

### Sample-size trajectory (counts only; outcome availability not inspected)

| Test | Now | Rate (recent days) | Projected at window end | Registered need |
|---|---|---|---|---|
| E009 primary origins (non-late, 20-min grid) | 39,684 | about 6,500/day | about 130,000 (+2,508 from the gap fill) | Unavailable below 5,000 evaluated; plan about 100,000 |
| E009/E010 event clusters | 51 | 23–46 active per day | at least 51 already (only grows; rough guess 55–80) | at least 20 (plan 40) |
| E010 hourly origins | 13,059 | about 2,150/day | about 43,000 (+836 from the gap fill) | at least 2,000 per horizon; plan 34,000 |
| E011 alert lines | 4,200 | 720/day (12 passes) | **about 19,380** (253 more passes, 10-19T22:31Z..11-09T22:31Z) | about 19,700; the 6 lost passes explain the 360-line shortfall |
| E011 episodes | 837 (377 clusters) | about 130/day | **about 3,600** (3,300–3,800) | at least 30 and 10 clusters; the plan said "> 4,000"; MDE table: 1,743 for +2 pts at b = 5% (independent) |

E011 will likely land about 10% below the planning figure for episodes. That is well above the independent-episode
requirement, but below the "about 5,200 for +2 pts at b = 5% with 3× dependence" scenario. This is not a design change;
report it with the result.

## 5. Operational risks before the analysis dates, with mitigations

| # | Risk | Status now | Mitigation |
|---|---|---|---|
| R1 | **E009 analysis memory on the host.** `analyze` keeps every in-window prediction dict. On synthetic lines shaped like the real ones, it measured about 2.7 KB per line plus 0.33 GB: 100k lines peaked at 0.61 GB and 300k at 1.15 GB. The projection is about 1.4M lines, so about **4 GB**. The host has 5.6 GB total and 3.9 GB available, with the trade monitor at 0.5 GB. | likely OOM on the host | Run E009 on a machine with at least 8 GB, from a copy of the input files with their sha256 recorded, and nothing else memory-heavy at the same time (memory rule). E010 (about 45k lines) and E011 are small. |
| R2 | **Stopping collection too early.** E009's 60-min outcomes need the poller until about 11-03T01:05Z and E010's 6h outcomes until about 11-03T06:05Z. E011's last outcomes need collector passes (`write_outcomes`) until 11-11T13:00Z. | poller and collector running | Do not stop, migrate or restart either before 11-03T08:00Z and 11-11T13:00Z. A planned host move (second A1 instance, MC1) must wait or be logged as a deviation. |
| R3 | **E009/E010 2 GB cap** (`CapReached`, exit 3, needs a human; supervise does not restart it). | `cross_venue_live` is 425 MB, growing about 60 MB/day, so about 1.3 GB at 11-03 | Margin of about 0.7 GB. Check `du` weekly. |
| R4 | **Collector data cap** (`AREPO_DATA_CAP_GB` = 45 GiB; the pass skips above it, which stops E011 captures and outcomes) and the 4 GB free-disk guard. | data-dumps is 17 GB; root has 56 GB free | Snapshots now rotate at 8 days. Queue jobs (ml_cache, extracts) are the main growth. Watch `du` daily. `notify` alerts on 6 h without a pass and on low disk, but not on a cap skip as such. |
| R5 | **Retention deleting inputs.** | safe | `cross_venue_live/`, `surprise_live/` and `/home/opc/arepo_val` have no retention rule, so they are never deleted. The poller's own `gzip_old_quotes` compresses quote files but keeps them, and `analyze` does not read quotes. `snapshots/` deletes at 8 days, which is enough for E011's 7.5-day series bootstrap. |
| R6 | **Backup of the growing evidence logs.** | weekly active snapshot is installed (Sun 06:10Z; release `data-20261018-dsheikh-active` verified) | Take an extra active snapshot just after 11-03T08:00Z and 11-11T13:00Z, before the analyses, and cite its sha256 in the result entry. |
| R7 | **Host reboot or crash.** | `@reboot` + `*/5` supervise restart the poller | A restart loses only the down cycles (missing stays missing). Recovery is tested here. Code on disk is the deployed tree, so a restart picks up `HEAD`. E009/E010 code is unchanged since `9beda37`, so that is safe. |
| R8 | **No alert for a hung or stopped poller.** `notify` watches collector passes, disk and the trade-monitor stats. It does not watch `predictions.jsonl` freshness or the exit-3 cap. | gap | Add a check: `cross_venue_live/predictions.jsonl` mtime older than 15 min, or `run/cross-venue-live.exit` = 3. This is an ops change; deploy separately. |
| R9 | **Oracle Always Free idle reclamation** (instances below the published CPU, network and memory utilisation thresholds for 7 days may be reclaimed). | 1 OCPU, load about 1.0 | Load is high enough in practice. Keep the off-host archive current (R6). |
| R10 | **Analysis run from the wrong tree.** | F1 lives only on this branch | Merge F1 and the B1 merge step before the dates. Record the commit in each result. |

## 6. Next actions as first written (all done; see the addendum)

Steps 1–5 (gap-fill rule and merge, the dk1 reading, the D1 ledger line, the E011 supplement, the watchdog) are done on
this branch. Step 6, running the analyses, is now addendum A7.

## Addendum (2026-10-21 00:02 UTC+1): actions 1–6 done, before any result was seen

Throughout, only counts, timestamps and ids were used, as before. Nothing here was run on the real E009, E010 or E011
outcome files.

### A1. Gap fill (B1): rule declared first, then code
- **Rule:** `docs/research_lab/E009_E010_GAPFILL_RULE.md` (`gapfill-v1`). It was committed in `4870bc6c` **before** any
  merge code or merged output existed (sha256 `28064e33d78db0438b3d73fec261bdb4cf5c0bbd62109c1a4c9f94113d8c4da2`).
  - Window `W` = the open interval (2026-10-14 00:02Z, 10:44Z).
  - Canonical is primary and copied byte for byte.
  - Copy predictions are added only for origins in `W` that have no canonical id, together with their own outcome lines.
  - A straddling outcome (origin outside `W`, due inside `W`) is taken from the copy only if all hold: the canonical record
    is missing or not `evaluated`; the copy has the outcome line; the copy has the prediction; that prediction equals the
    canonical one on every field `analyze` uses. If the prediction differs, the record is refused and counted, never
    mixed.
  - Copy lines are tagged `source=validation_copy`. The merged root is new, and neither source is edited.
  - Primary = merged root; sensitivity = canonical only.
- **Code:** `backend/astrolabe/research_lab/cross_venue_gapfill.py`, CLI `backend/scripts/run_cross_venue_gapfill.py`
  (commit `6218e274`).
  - `MERGE_MANIFEST.json` records the rule sha, the code commit, the sha256 and line count of each of the 8 inputs and 4
    outputs, and the counts per rule branch (R2 added, R3 per horizon, R4 substituted and refused per reason). It never
    records outcome values.
  - It refuses an existing target folder, or one inside a source.
  - It re-hashes the inputs after the merge and fails if they changed. **It must therefore run on frozen copies, not on
    the live folder the poller is still appending to.**
- **Tests:** `backend/tests/test_cross_venue_gapfill.py`, on synthetic straddling cases:
  - substituted at 20 and 60 min;
  - refused because canonical is `evaluated`, the copy outcome is missing, the copy prediction is missing, or the
    prediction differs;
  - receipt-only differences are allowed;
  - the window endpoint and copy rows outside `W` are ignored;
  - a pre-existing canonical duplicate is kept;
  - an E010 6h substitution, and the copy's unwritten 6h line counted as `missing_line`;
  - output sha256s match;
  - `analyze` reads the merged root;
  - an empty copy gives a merged root byte-identical to canonical.
- **For the science-reviewer:** whether (b) the straddle substitution is the right reading of "where the canonical stream
  has no valid quotes" (rule §5 gives the reasons).

### A2. "dk1 slope" and mechanical verdicts
- **Reading.** `EXPERIMENT_LEDGER.md` line 829–830 (E009 secondaries) names two slopes: "the slope of dP(20 min) on dk1"
  and "the partial slope on dk1 given the frozen M0 prediction". Line 863 (Supported) says "the dk1 slope point
  estimate > 0" without qualification. Line 865 (Contradicted) says "partial-slope CI" explicitly. The registration names
  the partial slope wherever it means it, so the unqualified "dk1 slope" is **the simple slope at the primary horizon**:
  the frozen output `horizons["20"]["slope_dp_on_dk1"]`. The code's names match the two registered quantities one to one:
  `slope_dp_on_dk1` and `partial_slope_dk1_given_m0`.
- **Verdict script.** `backend/astrolabe/research_lab/live_verdicts.py`, CLI
  `backend/scripts/live_verdicts.py {e009,e010,e011} <saved analysis JSON>` (commit `b3b54f93`).
  - It only reads the frozen output and applies the ledger thresholds. It prints the fields used and the input's sha256.
  - E009: Unavailable (< 20 clusters or < 5,000 origins at 20 min) → Supported → Contradicted (with the "frozen scale
    miscalibrated" label) → Inconclusive, plus the economics label.
  - E010: per horizon on `holm_m1`, minimum 2,000 origins.
  - E011: re-derives the verdict and checks it equals the frozen code's.
  - Tests: `backend/tests/test_live_verdicts.py`.
- **One flag for the reviewer (E010).** The frozen code gives Holm p = 1 only to a horizon with fewer than 2 clusters. A
  horizon that is Unavailable by the registered minimum (fewer than 20 clusters or fewer than 2,000 origins) still enters
  Holm with its own p. The script reports the frozen `holm_m1` as is and adds a note in that case. The reviewer states
  before reporting whether "a horizon without a test" includes it. Given the projected counts (about 43,000 origins, 51+
  events), the case is unlikely to arise.

### A3. Ledger
An operational-deviation entry for the canonical gaps on 2026-10-13 (21:24–22:22Z and 22:28–23:12Z) is appended at the
end of `EXPERIMENT_LEDGER.md` (commit `88d60792`, facts only). The main branch's ledger has moved, so the coordinator
merges it.

### A4. E011 descriptive supplement (S1)
`backend/astrolabe/research_lab/surprise_supplement.py`, CLI `backend/scripts/run_surprise_supplement.py` (commit
`711a9107`). It outputs:
- (c) 2h-label rates and matched excess;
- (d) |move| >= 0.15 rates at 6h and 24h for alerts **and** controls;
- (e) sports vs non-sports (`fee_category == "sports"`);
- (f) the `control_match` line composition and control shortfalls;
- (g) slots on the 2h pass grid, missed slots, passes logged, statuses, and request/time/eligible medians and maxima.

It forms episodes exactly as `analyze` does; a test pins the equality of `n_episodes` and `n_episodes_analysed`. It is
descriptive only: there is no verdict key, nothing enters the multiplicity count, and its CIs use seed 20261015. Run it
once, straight after `run_surprise_snapshot.py analyze`. Test: `backend/tests/test_surprise_supplement.py`.

### A5. Watchdog (R8)
`backend/scripts/live_tests_watchdog.py` (commit `eac5a4f9`) runs every 15 min and alerts through `arepo_notify.py send
--type breakage` (deduplicated per key). It never acts. It checks:
- E009 has no new prediction origin for more than 30 min;
- E010 has none for more than 2h15m;
- the poller exit marker is 3 (cap);
- `cross_venue_live` is at 85% or more of 2 GB;
- E011 has no scored capture for more than 2 intervals (+30 min);
- E011 outcomes have not been written for the same time;
- data-dumps is at 85% or more of the 45 GiB collector cap (hourly);
- free disk is below 8 GB.

It stops watching E009/E010 after 2026-11-03T08:00Z and E011 after 2026-11-11T13:00Z. It reads only tails, mtimes and
sizes. The cron line is in `scripts/oracle/crontab.txt`, commented and **not installed** (no deploy). Test:
`backend/tests/test_live_tests_watchdog.py`. A local `--dry-run` with no data correctly reports every stream as stale.

### A6. Memory plan for E009 (R1), with a dry run at final size
- **Dry run.** The probe used 1,400,000 synthetic prediction lines (1.00 GB) and 420,000 outcome lines (0.35 GB), the same
  schema as the real files, generated from a seed, on this Mac (8 GB). It ran the frozen `cvl.analyze` with `n_boot=50`.
  It **completed in 148 s**. Peak resident set was 1.16 GB, because macOS compressed and swapped the rest: swap in use was
  5.1 GB, with editor and agent processes also running.
  - The true heap is about 2.7 KB per line. That figure is linear from earlier unpressured runs (100k lines: 0.61 GB;
    300k: 1.15 GB), which puts the final run at about **4 GB**.
  - The 4,000-resample bootstrap works on per-event sums (about 60 rows), so it adds seconds, not memory.
  - E010 (about 45k lines), the gap-fill merge (streams, keeps only about 6 h of straddle candidates) and E011 are small.
- **Plan.**
  1. After 2026-11-03T08:00Z, take an active snapshot (R6). Then copy `cross_venue_live/{predictions,outcomes}*.jsonl`
     from the host and `/home/opc/arepo_val/data-dumps/research_lab/cross_venue_live/` to a new folder on the Mac, and
     record the sha256 of every file on both ends (they must match).
  2. Close other heavy apps. Run nothing else multi-GB at the same time (memory rule).
  3. Run `run_cross_venue_gapfill.py` into a new folder, then `--analyze` and `--analyze-e010` on the merged root
     (primary), then on the canonical copy (sensitivity). Save each stdout to a file and run `live_verdicts.py` on it.
  4. The host (5.6 GB, 3.9 GB available, live trade monitor running) is not used for E009.

  E011 can run on the host (small), after 2026-11-11T13:00Z, from a tree containing F1, followed by the supplement.

### A7. Remaining actions
1. `science-reviewer`: check the `gapfill-v1` rule, the dk1 reading, the E010 Holm note and F1. Any change becomes
   `gapfill-v2` and is recorded before any merge on real data.
2. Coordinator: merge `feat/live-audit` (ledger append included). Deploy the watchdog and uncomment its cron line when
   deploying is allowed.
3. 11-03 after 08:00Z: E009/E010 per A6. 11-11 after 13:00Z: E011, then the supplement.

## Addendum 2 (2026-10-21): science-reviewer ACCEPT_WITH_CHANGES applied, before any merge on real data

1. **Gap fill is now `gapfill-v2`.** The rule is in `E009_E010_GAPFILL_RULE_V2.md` (commit `b225ac39`, declared before the
   code change); v1 is kept. The code is in commit `4751a46d`.
   - §1 now gives the straddling counts per outcome-line grid and per analysed grid. E009: 74, 148 and 368 lines at
     10/20/60 min on the line grid, but only 74 per horizon on the analysed grid (origin 00:00Z). E010: 74 lines at 1 h
     and 299 at 6 h, all analysed.
   - The §5 bound is restated to match: at most 74 E009 analysed origins per horizon, and 74 / 299 for E010.
   - New refusal `canonical_pred_duplicate`, checked after `canonical_evaluated`. `analyze` keeps the last line of a
     duplicated id. There are 0 such ids today.
   - Disclosure added: refusals under R4(d) are a non-random subset (the two hosts' books differed at `t`). This is not a
     leak.
   - The manifest adds `r4_*_analysed_grid` counts.
   - The CLI records HEAD and refuses a dirty tree; `--allow-dirty` records `tree_dirty: true`.
2. **E010 verdict rule** (ledger entry "E010 verdict rule declared", commit `084b16bc`; code in `e5f6ca7f`). A horizon that
   is Unavailable by the registered minimum enters Holm with p = 1, so the other horizon's adjusted p is
   min(1, 2·p_raw). `live_verdicts.py e010` reports the declared and the frozen `holm_m1` side by side, and shows both
   verdict sets when they differ.
3. **Ledger deviation entry for F1** (`_cluster_id`): the facts, the reason, and the effect, which is 0 of 4,200 current
   window alert lines.
4. **E011 supplement disclosures** (module header):
   - the frozen `analyze` counts a missing `fwd_move` as a non-hit, while the supplement excludes it;
   - the (d) denominators differ from `n_episodes_analysed`;
   - a missing `fee_category` falls into non-sports.
5. **D1 ledger entry reworded:** "strictly between" the bounding cycles, which are present, and "cause unknown". This
   entry was amended in place because it had not been merged yet. The other ledger edits are appended entries.
