# Creative batch 18 (CB18): silent edits, program versus human, races, the front page and the last-mid map (round 10's remainder)

`evidence_role: none` at drafting (design only) | planned roles: `exploratory_historical` (pre-censuses and the CH175
map on worn pre-window host data, counts and descriptives only), `prospective` (CB18-S's SCREEN_18 and REP_18 windows,
which start at least 24 h after the rules commit) | status: **DRAFT, challenger R1 = REVISE (2026-10-20), R1 response
written 2026-10-21 (§11), R2 = ACCEPT_WITH_CHANGES (2026-10-21), R2 response written 2026-10-21 (§12); part `pre` and the
census code implemented as a candidate (not frozen, not run); nothing queued.** Drafted 2026-10-20 20:19
UTC+1 (2026-10-20T19:19Z) on branch `feat/cb18` from `9a68ea2f`
(`chore/arepo-claude-setup`). No host probe, no network request and no window data were used. Every count quoted is a
round-9/10 probe, LT3/LT4 census or CB17 pre-census figure on worn data, named as such; everything else is **unprobed**.

This is research tooling. Nothing here is an edge, calibration, tradability or profitability claim. AREPO never trades;
every "route" is a paper rule, and economics never changes a verdict.

**Source ideas.** `CREATIVE_HYPOTHESES_2026-10-24.md` (round 10) ideas that LT4 (`LIVE_TESTS_4.md` §7.2, on
`feat/live-tests-4`) did not take: **CH172** (program versus human), **CH175** (last-mid outcome map), **CH176** (the
front page as a clock), **CH177** (silent edits) and **CH179** (races). **CH178 is excluded** (§0.2). The file follows
`CREATIVE_BATCH_17.md` (CB17) for batch governance and `LIVE_TESTS_4.md` (LT4, after its R1 response, §14) for the
live-test sketches. "As CB17 §x" or "as LT4 §x" means the rule applies unchanged, including their freeze-check fixes.

## 0. Summary, routing and scope

The round-10 remainder is mostly **unprobed**. So CB18 is first a set of counts-only pre-censuses on worn host data
with **pre-declared, counts-only routing rules**: each idea goes to exactly one of (a) a CB18 SCREEN/REP batch test,
(b) a member of a future registered live-test family **LT5**, (c) a map or census only (k = 0), or (d) dropped
uncounted. The route is read from worn-data counts before any rules part binds, so a census drop is uncounted.

| Family | Idea | Census first (worn, counts only) | Default vehicle (if the census gates pass) | Why this vehicle | Counted in CB18 |
|---|---|---|---|---|---|
| **CB18-S** silent edits | CH177 | **yes** (`updated_at` semantics, silent counts by `chg_*` flag status, burst shares, proxy SE) | **CB18 SCREEN_18 / REP_18**, event-arm split; LT5 only if powered unsplit but not split; else dropped | field semantics are unknown and may drift (indexer behaviour), so two windows on disjoint event arms test stability; sign-free, EV 2, no taker route; its units are disjoint by construction from every change-conditioned live primary (not from LT2's E012 population, disclosed in §1.3), so a batch screen costs no Holm slot elsewhere | S1 (Stage 1), S1-rep (Stage 2, triggered): **0-2** |
| **CB18-P** program versus human | CH172 | **yes** (parallel re-centerings in the active frame, fade/follow/none split, coverage, permutable share) | **LT5 member** (28-day window) | power is the binding risk; a 14-day half-arm screen would kill a true effect; the trade-sample reader convention is LT's | 0 (counted in LT5 if registered) |
| **CB18-R** races | CH179 | the race **map** only (same-second multi-order rows, `ts` resolution, fingerprint and same-side shares; descriptive) | **map only (k = 0)**; the counted moderator test is **dropped** (R1 finding 1) | its gate was the residualised donor gate that LT4 R2 recorded as failing size (corr 0.5: 0.085 against 0.075) and LT3 ruling 2 found structurally invalid; re-using it would be a redraw | 0 |
| **CB18-F** front page | CH176 | **yes** (rank churn at candidate breakpoints) | **census only (k = 0)**, re-entry rule for a 60-day live test | the breakpoint `B` and the venue's sort cannot be fixed without a network look (not allowed here); the money target needs 60+ days | 0 |
| **CB18-M** last-mid map | CH175 | the map itself (host-only historical, descriptive) | **map (k = 0)** | an enabler, not a hypothesis | 0 |

**Counted in CB18: 0-2** (S1 if CB18-S routes to the batch; S1-rep only if S1 advances). Every other test is counted
in LT5's own family, if and when LT5 registers it. **LT5 candidates: CH172 (CB18-P) and CH177 only under routing rule
RS-2** (§3.1). CH179 (CB18-R) is no longer a candidate (R1 finding 1; §4.3).
LT5 is a separate document (`LIVE_TESTS_5.md`, not written here); §4 gives each
member in LT4's shape so it can be lifted without re-deriving the unit, null or gate.

### 0.1 Honest expectation
- **CB18-P will almost certainly drop at its census.** With the R1 design-effect floor (`DE_gate = max(3.0, computed)`)
  its pessimistic planning MDE reaches the 0.5c floor only with about **12,900 fades in 28 days (about 460 a day)**,
  §4.2; round 10 guessed 60-120 a day (1.39c and 0.98c pessimistic at 1,680 and 3,360 fades). Under the existing rule
  (GP5) that is a drop, uncounted; no longer window is declared (R1 Q8).
- **CB18-S lives or dies on a field nobody has read**: if `updated_at` moves on an indexer clock, the idea is dead at the
  census, uncounted. If it survives, it is a sign-free maker-protection mechanism at best. **Power (R1 finding 2):** at
  the GS4 kill line (200 silent units a day) the pessimistic arm-level 14-day MDE is **1.58c** against the 1.0c floor
  (SD 6c, DE 3, the 1.5 factor, no quiet-side variance); the CB route (RS-1) needs about **500 silent units a day** with
  unlimited quiet units, about 630 with quiet = 4 x silent, 1,000 with quiet = silent. The unsplit 28-day LT
  alternative (RS-2) is at 0.71-1.00c at 200 a day. So under planning numbers CB18-S **does not meet its floor on the CB
  route** and, by the existing routing rule, goes to RS-2 (an LT5 member) or is dropped at RS-3; the census proxy SE
  decides.
- **CB18-R is a map only** (R1 finding 1). E023 and E024 were dropped by LT4 R2 (k = 3), and LT3 ruling 2 made the
  donor gate non-binding for E016/E018; the moderator test CB18-R proposed had the same defective gate and is dropped.
- **CB18-F and CB18-M count nothing.** CB18-M is the most useful output for the programme: it says which calibration
  arms of rounds 1-9 can ever be pure readers.

### 0.2 CH178 excluded (double count of E015), and why
CH178 is E015's traded-versus-quoted contrast on the sweep-pair clock in the 2,000 sampled markets. Its direction,
target family (2 h continuation of the move) and hypothesis are E015's (LT3 primary; window proposed 2026-10-24 to
2026-11-14), and its origins would overlap E015's in time and markets. Running it now, in any family, is a second
counted test of E015's hypothesis on overlapping data before E015 is analysed: a double count (LT4 §7.2 made the same
call). It is **not proposed in CB18**. Re-entry: only after E015's analysis commit (on or after 2026-11-15T12:00Z), as a
declared replication of E015 on an origin window disjoint from E015's, counted under E015's replication line, and
reported as a replication, never as a new mechanism. E015's own M1 (sweep target) already reads part of the staleness
question.

### 0.3 Queue id mapping (q0500-q0519; drafts only)

All specs are drafts in `docs/research_lab/queue/drafts/` (never `queue/jobs/`). `argv[0]` is `scripts/run_cb18.py`, **which
does not exist yet**, except the restores, which use the existing `scripts/restore_from_archive.py`. Family
`creative_batch_18`.

| Id | Job | Family | Lane / mem | Earliest |
|---|---|---|---|---|
| q0500 | `cb18_census_restore_captures` (worn captures, sidecars, sweeps; byte for byte from releases) | all | net / 600 | any time (data movement only) |
| q0501 | `cb18_census_restore_samples` (the 23 LT3-C2-sealed samples of 10-16/17, incl. `plan.json`) | P, R | net / 600 | any time |
| q0502 | `cb18_pre_census_S` (CH177) | S | cpu / 380 | part `pre` + census code + tests + `seals/cb18_census_inputs.json` |
| q0503 | `cb18_pre_census_P` (CH172) | P | cpu / 380 | as q0502 |
| q0504 | `cb18_pre_census_R` (CH179: the race map only, descriptive; no gates, no route) | R | cpu / 390 | as q0502 |
| q0505 | `cb18_pre_census_F` (CH176) | F | cpu / 300 | as q0502 |
| q0506 | `cb18_map_lastmid` (CH175 map) | M | cpu / 350 | as q0502 |
| q0590 | `cb18_smoke` (part hashes, refusals, exact reproduction of q0502's counts with frozen code) | S | cpu / 390 | parts `common`, `S` committed + code freeze record |
| q0591 | `cb18_exclusion_keys` (ids only; seal copies; overlap counts) | S | cpu / 300 | after q0590 PASS |
| q0592 | `cb18_restore_screen` (SCREEN_18 captures, sidecars, sweep 1 rotated off the host) | S | net / 600 | `not_before` S_18 + 15 d + 8 h |
| q0593 | `cb18_frame_screen_S` (arm-0 units, features only, raw target-mid table, no target computed) | S | cpu / 390 | after q0592, q0591 |
| q0594 | `cb18_census_18` (window gates, SE-only power gate, informativeness at the selected level) | S | cpu / 390 | after q0593 |
| q0595 | `cb18_screen_18` (Stage 1: S1) | S | cpu / 900 | after q0594, E011's **and E012's** analysis commits (E012: on or after 2026-11-13T12:00Z; R2 finding 5), code-against-design freeze check |
| q0596 | `cb18_restore_rep` (REP_18 inputs) | S | net / 600 | `not_before` S_18 + 29 d + 8 h; only if S1 advanced |
| q0597 | `cb18_frame_rep_S` (arm-1 units; sealed) | S | cpu / 390 | after q0596 and the SCREEN result commit |
| q0598 | `cb18_rep_18` (Stage 2: S1-rep, triggered) | S | cpu / 900 | after q0597 |
| q0599 | `cb18_stage2_final` (one strict Holm over triggered Stage-2 tests; write-once) | S | cpu / 300 | after q0598 |
| q0517-q0519 | reserved (LT5 jobs take their own ids in `LIVE_TESTS_5.md`) | - | - | - |

If CB18-S does not route to the batch, q0590-q0599 are withdrawn (recorded in the ledger, never promoted).

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Role in CB18 | Evidence ceiling |
|---|---|---|
| Complete captures `snapshots/<id>/rows.csv.gz` + `rows_ext.csv.gz` (+ `manifest.json`, `ext_manifest.json`) of **`[2026-10-11T22:31Z, 2026-10-17T22:31Z]`** (67 captures; the six captures 2026-10-14T00:31Z-10:31Z exist in no release and are **unavailable**, §3) and the book sweeps of the 2026-10-15/16 passes (48 directories, sweep 1 and 2 of 24 passes), restored byte for byte (q0500; releases confirmed against the committed catalogues, §11) | pre-censuses q0502-q0505 and the q0506 map; counts, origin-side features and SEs on pre-origin proxies only (§3). The days already worn by CB17 P2/P3, LT3 C1 and LT4 CQ/CH/CF | counts |
| The **23 LT3-C2-sealed active-frame trade samples** of 2026-10-16/17 (`seals/lt3_census_inputs_C2.json`; 92 files: `manifest.json`, `plan.json`, `features.csv.gz`, `trades.csv.gz`; in releases `data-20261017-dsheikh` (2 samples), `data-20261018-dsheikh` (12), `data-20261019-dsheikh` (9)), restored by q0501. The 24th sample of those days (`20261017T044014Z_4439c7c6`, release `data-20261018-dsheikh-2`) is **not in the seal and is not used**; pass pairs that need it are unavailable, counted | q0503, q0504; counts and origin-side features (`ts, side, price, size, outcome_index, asset, tx_hash`; `origin_utc`, `trades_truncated`; `plan.json` for frame membership and the sampling stratum) | counts |
| Captures, sidecars and sweep 1 of SCREEN_18 and REP_18 (host copies where present, else restored byte for byte, hash-checked against the release manifests) | CB18-S Stage 1 (arm 0) and Stage 2 (arm 1) | L2 (post-freeze live window) |
| Trade samples during an LT5 window | LT5 members only, through LT5's own per-pass reader (not a CB18 job) | LT5's |
| `live_trades/` (monitor), `cross_venue_live/` (E009/E010, sealed to 2026-11-03), `surprise_live/` (E011), `live_tests2/`, `live_tests3/`, `live_tests4/`, `creative_batch16/`, `creative_batch17/`, CB8-H holders, `e001/`-`e007/`, `forecasts/`, `flow_screen/`, every `h*` root | **never opened** (runner refuses; unit-tested) | - |

**Not read anywhere in CB18:** wallet fields of any kind; the **values** of `chg_1h/1d/1w` (E004-E007 guard, as CB17
§1.3); `outcome_prices`, `closed_time`, any Gamma outcome field; question text. `chg_1h`, `chg_1d`, `chg_1w`,
`uma_resolution_statuses` and `event_comment_count` are read **only as raw byte-equality flags** between two captures
(string comparison of the bytes as written, never parsed, never written out; R1 findings 3 and 9, Q2, Q3), plus one
byte comparison of `uma_resolution_statuses` at k against the writer's empty literal (§4.1 (10)). Because
`cb13_common.py` lists `chg_*` in `FORBIDDEN_CAPTURE_COLUMNS` (:135) and `uma_resolution_statuses` in
`FORBIDDEN_SIDECAR_COLUMNS` (:137), `cb18_common` carries an **explicit, unit-tested whitelist exception** that exposes
these four columns only through a `bytes_equal(a, b)` / `is_empty_literal(x)` helper; any other access raises.

### 1.2 Dates (declared; UTC)

| Name | Value | Meaning |
|---|---|---|
| `T18_draft` | 2026-10-20T19:19Z | this draft; no CB18 quantity computed |
| `T18_pre` | target 2026-10-22T12:00Z (soft) | commit of part `pre` of `seals/cb18_rules.json` (census paths and cut-offs, whitelists, every census gate and routing rule of §3, the strata ladders and selection rule, the proxy-SE recipe), after the challenger round on this file and **before any census code runs on data** |
| census cut-off | 2026-10-17T22:31Z (captures, samples); map: 2026-10-16T00:00Z | census paths refuse any file or row timed after it |
| routing record | target 2026-10-24T12:00Z | after q0502-q0506; `seals/cb18_routing.json` (counts and the route of each idea, by the §3 rules only) and a ledger line, before any part other than `pre` |
| `T18_rules` | target **2026-10-25T18:00Z** (soft) | committer time of the commit that lands parts `common` and `S` (CB route only) on `chore/arepo-claude-setup`, with the census-fixed values written in (CB17 ruling O2's definition) |
| lookback floor | 2026-10-26T00:00Z | no CB18 **window** path reads a row timed before it (keeps J4-R `[10-16, 10-21)`, CB13-T HOLDOUT `[10-21, 10-26)` and the census days untouched **by window paths**; the pre-censuses do read inside J4-R, disclosed in §1.3 (R2 finding 1)). **CB18-S's longest lookback is capture k − 12** (R1 finding 5: the prior-quiet count is capped at **11**, so it reads intervals back to (k − 12, k − 11); the `|mid_k − mid_{k−12}|` control reads k − 12; dormancy reads only the book stamp of sweep 1 of pass k, a value capped at 24 h, never a row). The first SCREEN_18 origin capture is 2026-10-27T00:31Z, so k − 12 = 2026-10-26T00:31Z, inside the floor. The runner refuses any capture, sweep or row timed before the floor (unit-tested at 2026-10-25T22:31Z, the old k − 13) |
| `S_18` | `max(2026-10-27T00:00Z, the first 00:00Z at or after T18_rules + 24 h)` | start of SCREEN_18; depends only on the rules commit time. With `T18_rules` by 2026-10-26T00:00Z, **S_18 = 2026-10-27T00:00Z** |
| SCREEN_18 | origin (decision) times in `[S_18, S_18 + 14 d)` = **[2026-10-27, 2026-11-10)** | Stage 1, arm-0 events only |
| REP_18 | origin times in `[S_18 + 14 d, S_18 + 28 d)` = **[2026-11-10, 2026-11-24)** | Stage 2, arm-1 events only |
| event arm | `arm(e) = int(sha256("cb18-arm-v1|" + event_id).hexdigest()[0], 16) mod 2`; `event_id` = Gamma event id, else the market id | arm 0 → SCREEN_18, arm 1 → REP_18; disjoint by construction; fixed before data. Targets of late SCREEN units read REP-window captures of arm-0 events only |
| election-night exclusion | origin or target capture in `[2026-11-03T18:00Z, 2026-11-05T00:00Z)` | excluded and counted (as CB17) |
| `T18_code` | target: before `S_18`; at the latest before the first read of any SCREEN_18 file (q0593, 2026-11-11T08:00Z); never before an accepting code-against-design freeze check | as CB17 §1.2 `T17_code` and ruling 6: no agent opens a SCREEN_18 or REP_18 file before the freeze record exists; ledger attestation |
| E011 | analysed once after 2026-11-11T13:00Z | q0595 refuses before E011's analysis commit (S's target is a 24 h movement, close to E011's object; costs about one day) |
| E012 | analysed once on or after 2026-11-13T12:00Z (`LIVE_TESTS_2.md`:27) | q0595 also refuses before E012's analysis commit (R2 finding 5: E012's population contains S's units and its target is a 24 h change, §1.3; waiting costs about two more days and keeps S1 from being read before the overlapping registered primary) |
| LT5 (proposed) | `REGISTERED_UTC` = the first 00:00Z at least 24 h after the LT5 registration commit, at least 48 h after LT4's `REGISTERED_UTC`, and **not before 2026-10-30T00:00Z**; 28 days; analysis once at `END_UTC + 36 h` | proposed **2026-10-30T00:00Z to 2026-11-27T00:00Z**, analysis on or after 2026-11-28T12:00Z; fixed end, no extension (as LT4 §1.1) |

If `S_18` slides, both windows slide; lengths are fixed. Frames run after each window and its 24 h targets close:
q0593 not before `S_18 + 15 d + 8 h` (2026-11-11T08:00Z); q0597 not before `S_18 + 29 d + 8 h` (2026-11-25T08:00Z).

### 1.3 Overlaps and sealed data
- **J4-R disclosure (R2 finding 1).** The pre-censuses read **inside J4-R `[2026-10-16, 2026-10-21)`**: census S and F read
  the complete captures of 2026-10-16 and sweep 1 of its passes; census P and the race map read the 23 trade samples of
  2026-10-16/17 and the captures of 2026-10-16/17. CB17 refused census rows at or after 10-16 (`CREATIVE_BATCH_17.md`:253,
  281); LT3 refuses J4-R only for maker mark-out objects (`LIVE_TESTS_3.md`:529), and CB18 follows LT3's rule. **No census
  object is a mark-out**: every census reads origin-side fields at or before each unit's decision time (captures k − 12 ..
  k, sweep 1 of pass k, trade rows with `ts` at or before the pass k + 1 origin) and writes counts, shares and standard
  errors only; no forward price, no target, no mark and no outcome is read or written (unit-tested: the result writer
  refuses such keys). The statement "J4-R untouched" in §1.2 holds for window paths only. The CB13-T **HOLDOUT
  `[2026-10-21, 2026-10-26)` is untouched** by every CB18 path: the census cut-off is 2026-10-17T22:31Z and the window floor
  2026-10-26T00:00Z.
- **CB18-S units are disjoint by construction from every change-conditioned live primary's units**: an S unit is a
  market-interval in which no capture numeric field (nor a `chg_*` byte flag) changed and the book was untouched (§4.1).
  E015/E020 (quote-only moves), E017 (volume surges), E021/E022 (traded moves), E019 (re-quoted ladders), CB17-B (sweep
  pairs with touch rules; B2 needs a shift) and CB17-C (traded event-intervals) all require a change that S excludes.
  **Not disjoint from LT2's E012** (correction; R1 "could not verify"): E012's units are complete-universe markets at
  6-hourly grid origins with no change condition and a 24 h target, so CB18-S's units and 24 h targets in SCREEN_18 and
  REP_18 can be a subset of E012's population where E012's window (analysis 2026-11-13) overlaps; the contrasts differ
  (signed 24 h change x liquidity there; silent versus quiet absolute move here). E014 (flow-model gain by time to the
  as-of end) reads trade samples, not S's units. Both are disclosed; neither is pooled with or cited as corroborating
  CB18-S. Collection overlap with LT2-LT4, E011, CB16 and CB17 windows is disclosed; no store is opened; no pooling.
- **CB18-P** overlaps E015's parallel class (same units at capture k, different contrast and target, E015's window to
  11-14). **CB18-R** is a map only; its rows are the trade samples E013, E016 and E018 also read (no target, no
  moderator test). Both are disclosed in LT5's overlap table; never cited as corroborating one another.
- **Prior use of `updated_at`-derived ages (R1 finding 6; disclosure).** `updated_at` is not new to AREPO: the ML panels
  of `history/h2_main` and `h1_first` carried `quote_age_s` and `ml_quote_staleness_h` (the age of Gamma `updated_at` at
  the origin; `ml_panel.py:281-284, 331`) as pooled-model features, with no demonstrated gain on 12.7% book coverage
  (ML-r4_book; `CREATIVE_HYPOTHESES_2026-10-22.md`:106, 331). CB18-S uses a different construct (the **change** of the
  stamp between two consecutive captures with every numeric field and the book unchanged, not its age), on
  post-floor prospective windows, but the field family has been seen in development and is not a fresh variable. The
  ML-panel result is not evidence for or against CB18-S and is not cited as such.
- **Exclusion keys (q0591, no network):** CB16 q0380's key file (sha256 copied from its write-once manifest, never
  hashed from disk) and every seal copy; a market or event is dropped only if a sealed historical set stores a
  timestamp inside SCREEN_18 or REP_18 (none expected), counted by source.
- **Outcome guards:** no CB18 path reads a resolution outcome. CB18-M's last mid is a price, and the map writes no
  comparison of any earlier price with it (§4.5).

### 1.4 Rules files
`seals/cb18_rules.json`, hashed per part, as CB17 §1.4:
- **`pre`**: census inputs (seal file name), cut-offs, whitelists, every gate and routing rule of §3 with its constants,
  the strata ladders and the 60% selection rule (§2.3), the proxy-SE recipe, the quiet-thinning rule (§4.1), the
  census-to-spec value list. Committed before any census code runs on data.
- **`common`** (CB route only): refused roots, lookback floor, seeds 18101-18140, cluster ways, small-G rule, Holm,
  disk guards, whitelists, smoke criteria, the event-arm hash, pinned sha256 of every imported function (LT3
  `classify`/slot helpers, CB17 `is_sports_sidecar`, LT4 `fl_perm_gate`).
- **`S`** (CB route only): eligibility, classes, target, controls, the selected strata level, the thinning rate, gates,
  labels, Stage-2 rule.
- **Order:** `pre` → censuses → routing record → `common`, `S` (if routed) → `T18_rules`. Nothing in a later part is
  chosen from a target, an outcome or a statistic; census-fixed values come from counts and features by rules in `pre`.
  Jobs refuse (exit 2) on a hash mismatch.
- LT5 members are pinned in LT5's spec, not here; CB18 hands LT5 only the routing record and the census values.

## 2. Common rules

### 2.0 Lessons carried in from CB17 and LT2-LT4 (binding from this draft)

| # | Lesson (source) | CB18 rule |
|---|---|---|
| L1 | Exact float writes (LT2 fix F, LT3 freeze fix 1) | every CSV written with `float_format="%.17g"`, read with `float_precision="round_trip"`; quotes, mids and spreads float64 (CB17 window fix 3: float32 put a third of exact 1c/2c/5c spreads in the wrong band); epochs int64 ms; unit test on exact round trip |
| L2 | Unknown never counts as met (CB17 window fix 4, §2.3) | every gate, guard, placebo and robustness check returns `True`, `False` or `None`; only `True` passes; an untestable check is `None` and blocks an advance; a NaN census value fails its gate (LT3 fix 2) |
| L3 | Missing data exits 75 (CB17 window fix 1, delta fix 2) | a missing input file exits 75 with "restore byte for byte, hash-checked" unless a committed per-day "source stopped" record (with reason and evidence) covers it; a stopped source makes dependent values **unknown**, never 0 |
| L4 | Worn-file pins from release manifests (CB17 delta fix 1 and 3; ruling O12) | `seals/cb18_census_inputs.json` takes every sha256 from the releases' `files.sha256`, never from disk; pinned mode refuses an unpinned, mismatched **or missing** pinned file; the pin set's completeness (the exact capture, sweep and sample counts of §3) is checked before any count |
| L5 | Freedman-Lane gates (LT4 R1 finding 7; `LT3_PERM_GATE_CHECK`); no donor gates (LT4 R2 finding 1; LT3 donor-gate ruling 2, 2026-10-21) | where the tested label or moderator correlates with controls, the permutation gate shuffles the control-residualised target within strata with the label fixed (`fl_perm_gate`). **Donor gates are not used as binding gates anywhere in CB18**: the residualised donor gate failed a binding size scenario (LT4 R2) and real and donor statistics are not exchangeable (LT3 ruling 2) |
| L6 | Size checks on the code to be pinned (LT3 13.5, LT4 L5; LT4 R2 finding 3; CB18 R1 finding 4) | every gate is size-checked at >= 2,000 worlds per scenario, including label-control correlation 0.4 and 0.5 (binding) and 0.7 (reported), and the **binding overlapping-target scenario** of §2.3 (MA(11) target in slot steps, persistent clustered label, at the selected strata level, level 2 included); a failing scenario blocks the pin, and no redesign, level change or second draw follows from that run |
| L7 | No selection on post-decision marks (CB17 ruling O9) | eligibility uses only information at or before the decision time; target unavailability is a status in the availability denominator with a binding bound (§2.6), never an eligibility filter |
| L8 | Smoke tied to frozen code (CB17 window fix 2) | q0590 stores `code_sha256` and refuses unless the code freeze record exists; it reproduces q0502's printed counts exactly (a different count is a FAIL and is investigated, not adjusted) |
| L9 | Skip-slot targets where bounce contaminates (round 10 lesson 5; LT4 L9) | CB18-P's target skips the slot holding the taker's trade; CB18-S has no quote event at the origin (by construction) and needs none; CB18-R has no target (map only) |
| L10 | Clustering (LT4 L10; CB4 A-C1; CB10 §2.3 small-G) | ways: event, event x UTC day (two-way), and UTC day; p = max, with t on G − 1 df for the one-way ways; in 14-day CB windows UTC day (G = 14) is replaced in the max by the 6 h block (G = 56) and leave-one-day-out binds (as CB17 §2.3) |
| L11 | Census drops are uncounted only before the rules bind (CB15-L, CB17 §2.5) | after a part commit every declared test is counted, with p = 1 if a gate fails |
| L12 | Readers at the pass cadence (round 10 lesson 6) | LT5 members read samples online (3-day host retention); CB18-S reads captures and sweeps after the window from host copies or byte-for-byte restores |
| L13 | Composition is not a placebo (CB16 §11, CB17 §2.6) | CB18-S keeps CB17's two-part composition guard, with its permutation part made Freedman-Lane |
| L14 | Planning MDE at or below the floor in every census (LT3 fix 4, LT4 L4; LT4 R2 finding 4; CB18 R1 finding 2) | each routing rule includes a pessimistic MDE recomputed on census-projected effective counts with **`DE_gate = max(3.0, computed)`** (the 0.02 intra-event correlation in the §2.4 formula is an example, not an estimate; a NaN DE fails), the 1.5 SD factor and both class terms |

### 2.1 Clocks and slots
As LT3/LT4 §1.3: slot grid `grid0 = 2026-10-01T00:31Z`, 2 h, tolerance 30 min, first complete capture of a slot; "k − 1"
and "k + h" are slots, not file order. A capture's time is the `received_utc` of its last page (CB17 finding 8). A
pass's sweep 1 is the first sweep directory of the pass (`series_index` 0); its time is the token row's
`batch_receipt_utc`. Book age `a = batch_receipt_utc − book_timestamp/1000`; `a < −5 s` is a clock anomaly (excluded,
counted). Trade rows use venue `ts` (seconds).

### 2.2 Uncertainty and decision rule (CB route; CB18-S)
As CB17 §2.3 with L10: analytic CR1 per way, one-sided p = max over event (t, G − 1), event x UTC day (two-way, normal)
and 6 h block (t, G − 1); UTC day reported with t on 13 df and **leave-one-day-out must keep p < 0.05 and the sign**.
**Stage 1** advance: one-sided p < 0.01 (strict), point estimate at or above the floor, every binding check of §2.3 and
§2.6 `True`, Holm over k1 = 1. **Stage 2** (S1-rep, only if S1 advanced): one CB18-wide strict Holm at one-sided α 0.05
over triggered tests (at most 1), the floor and the binding checks. BY (q = 0.10 over the cumulative count) is triage
only. Verdict labels as CB17: "not detected at MDE x", "not testable (...)", "not run (power)".

### 2.3 Valid within-unit nulls and their size
- **Freedman-Lane permutation gate** (CB18-S; CB18-P in LT5): after expanding-past demeaning, regress the target on the
  controls (reduced model), permute the residuals within the selected stratum, add back the fitted values, refit the
  full model; 200 draws, seeds from 18101. CB route rule (CB16 §11 amended): the gate holds iff **at most 3 of 200**
  permuted coefficients reach the observed one; an uncomputable draw counts as reaching it. LT route rule: as LT4
  (`p_perm < 0.05`, the LT family's convention).
- **Permutation strata ladder** (fixed in `pre`): level 0 market x UTC day; level 1 market x 2-day block; level 2 market x
  7-day block. A unit is in a permutable stratum if the stratum holds >= 4 units with both values of a binary label (or
  a non-constant continuous one). **Selection:** the finest level whose worn-data permutable share is >= 60% (CB17's 10-point
  margin over the 50% window rule); none → the test fails its census gate (dropped uncounted before the rules bind).
- **Calibration placebo** (CB18-S): the label circularly shifted within market (units in time order, offset uniform on
  {1, …, n − 1}), 200 draws, each judged on one-sided p < 0.01 alone; advance rate must be at most 3 of 200.
- **Donor gate:** none (L5). CB18-R, the only family that used one, is a map only (§4.3).
- **Size check** (L6): CB-route gates at 2,000 worlds must pass at most **0.0251** of null worlds (the 3-of-200 rule's
  nominal 4/201 ≈ 0.0199 plus 1.645 sqrt(0.02 x 0.98 / 2,000)); LT-route gates at most 0.058 (LT4 L5). Scenarios: iid
  labels; persistent market label rates; AR(1) labels; label-control correlation 0.4 and 0.5 (binding) and 0.7
  (reported); heavy-tailed targets (CB18-S's |move| has a point mass at 0).
- **Latent-volatility label scenario (CB18-S; R2 finding 2; reported, not binding).** The binding scenario below keeps the
  label independent of the innovations; this one does not. Null world as the binding scenario (same layout, MA(11)
  target, selected level and level 2), plus a per-market latent log-volatility `v_t` in slot steps (AR(1), persistence
  0.95, stationary SD 0.5) that scales the slot innovations (`e_t x exp(v_t)`) **and** raises the silent probability
  (logit coupling γ in {0.5, 1.0} per SD of `v_t`); the two `|mid|` controls are computed from the simulated mid path, so
  they capture `v_t` only imperfectly. There is no silent-edit effect in this world, so any advance is confounding the
  controls leave. **Reported at minimum and not binding**, because its rejection rate measures the bias left at an
  assumed coupling γ, which no worn count identifies (making it binding would let an arbitrary γ decide S1); the rates of
  the Freedman-Lane gate and the Stage-1 rule are printed in the size-check output and the S1 result. If either exceeds
  the route's limit (0.0251 CB, 0.058 LT) at γ = 0.5, the S1 result carries the label *latent-volatility sensitive* (a
  label; it never changes a verdict), and the limitation is stated with any advance.
- **Binding overlapping-target scenario (CB18-S; R1 finding 4, Q9).** CB18-S's target spans 12 slots, so consecutive
  units of one market share 11 of their 12 slot steps. Null world: per market, iid heavy-tailed slot innovations (with a
  point mass at 0); unit target `Y_k = |Σ_{j=1..12} e_{k+j}|`, i.e. an **MA(11) process in slot steps** before the
  absolute value; a **persistent, clustered silent label** (within market a two-state Markov chain with stay probability
  0.9 at the census-like silent rate, plus a capture-level common shock that lifts the silent probability of every
  market in 10% of captures, kept below the 20% burst line); the label independent of the innovations (size), plus the
  0.5 label-control correlation through dormancy and hour; units laid out on the real 2 h slot grid over 14 days, with
  the **selected permutation stratum level, and level 2 (market x 7-day block) in all cases**. Binding for the
  Freedman-Lane gate, the circular-shift placebo and the Stage-1 decision rule at the 0.0251 limit (CB route) or the
  Freedman-Lane gate at 0.058 (RS-2 / LT route). A failure blocks the pin: S1 is then "not testable (size)", p = 1,
  counted if part `S` is committed (L11); the level is never changed after the run and no second draw is taken.

### 2.4 Materiality floors and planning-MDE conventions
- **Floors (declared now):** CB18-S **+1.0c** on the 24 h absolute-move contrast (round 10); CB18-P **0.5c** on the
  skip-slot continuation (the fade coefficient, in the declared negative direction); CB18-R none (map only, R1 finding
  1); CB18-F none (k = 0).
- **Planning MDE.** Two-class: `MDE = M x SD x sqrt(1/n1 + 1/n0) x sqrt(DE_gate) x 1.5` (pessimistic; the 1.5 covers SD
  misestimation, as LT4 §8). `M = 3.80` for CB route ((z_0.99 + z_0.80) x 1.2, CB17 §2.7), `3.388` for LT route (LT4 §8).
  `DE_computed = 1 + (m_W − 1) x 0.02`, `m = Σ n_e² / Σ n_e` by event on the census population, `m_W = m x W / census
  days` (LT4 R1 finding 8); **`DE_gate = max(3.0, DE_computed)`** (R1 finding 2, LT4 R2 finding 4: 0.02 is an example
  value, not an estimate from a completed worn experiment, so the computed value may only raise the floor of 3); a NaN
  `m` fails the gate (L2). Both class terms always enter (`1/n0` uses the projected **thinned** quiet count, §4.1).
- **Census-SE ways (R1 finding 2).** A census proxy SE spans two UTC days, so the UTC-day way (G = 2) and the two-way
  event x UTC day are **not** used in any census SE; the census SE is the max over the event way and the 6 h block way.
  The window analysis keeps §2.2's ways.
- **SD sources (assumptions, round 9/10, LT3/LT4):** 24 h move SD about 6c (round 9); 24 h absolute move about 5c (round
  10, CH177); 4 h skip-slot change about 5c (LT4 §14.3, E021); log event volume change 0.5 (round 10, CH176). Where a
  census can compute the estimator's own clustered SE on a **pre-origin proxy target** (SE only; no point estimate
  written; CB17 §2.7), that SE replaces the formula **for CB18-S** (RS-1/RS-2; the formula only as the NaN fallback).
  **For CB18-P (R2 finding 3) GP5 binds on the larger of the two routes**: `MDE_GP5 = max(MDE_formula, MDE_proxy)` (§3.2);
  the formula alone binds if the proxy SE is NaN.

### 2.5 Counting (M3)
- Kinds `cb18_test`, `cb18_replication` (counted) and `cb18_descriptive` (EXCLUDE), added to `battery2.KIND_RULES`
  fail-closed (unknown kinds raise). Count lines: `creative_batch_18:S` **1** (S1, only if CB18-S routes to the batch);
  `creative_batch_18:S:rep` **<= 1** (S1-rep, triggered).
- **Uncounted:** the five pre-censuses and the map (q0502-q0506), the routing record, the smoke, keys, window census,
  gates, placebos, size checks, the sports arm, secondaries, mechanism readings, taker lines. A census drop or a route
  away from the batch happens **before** part `S` is committed and is uncounted (L11). After part `S` is committed, S1
  is counted whatever happens (p = 1 if a gate fails or the source stops).
- LT5 members are counted by LT5 (kind `live_tests5`, `n_tests = k`), never by CB18.
- The cumulative count (`battery2.cumulative_count()`; over 1,280 at round 10) is recorded by every counting job.

### 2.6 Missing data and availability (never imputed)
- Missing input file: exit 75 (L3). Missing row or field at the origin: no unit, counted by reason (`sidecar_missing`,
  `noprev`, `nosweep`, `updated_at_missing`, `stamp_missing`, `lookback_missing`; in census S also
`lookback_unavailable` for the declared 10-14 capture gap, §3).
- Each eligible unit receives one target status: `two_sided`, `one_sided`, `closed_flag`, `absent` (left the listing),
  `capture_missing`. Only `two_sided` units carry a target.
- **Availability (binding, CB route):** the available share must be >= 60% of eligible in each contrasted class, else
  "not testable (availability)". **Attrition:** if the non-available shares differ by more than 2 pp between classes, the
  result carries *attrition-differential* and Lee trimming bounds are computed; **for CB18-S the Lee lower bound must
  keep the predicted sign for an advance** (binding; stricter than LT4, where the label never changes the verdict),
  because exits after a silent edit are the very events the hypothesis predicts.

### 2.7 Costs and economics (separate; never changes a verdict)
CB18-S is sign-free: no taker route; the maker route ("widen for one day after a silent edit") is reported **gross, no
fills** as the spread change and the move. CB18-P economics follow LT4 §1.10 inside LT5 (paper taker round
trip at recorded touches with sidecar fees, `max_if_unknown`; >= 30 trades in >= 10 events). Declared in advance: every
AREPO taker cost check has failed (E004 −4.5c touch-to-touch; E007 +0.36c gross against about 4.5c; 0 of 95 economic
cells positive); "not shown" is the expected economic outcome. Hurdles: taker 4.5c median round trip (1.8c at liquidity
>= $100k); maker routes have paid 1-7c adverse selection in every AREPO study.

### 2.8 Compute, lanes, disk and stop rules
- Host: 1 OCPU, shared; queue rules as CB17 §2.8 (one job per lane, nice 19, `MemAvailable >= mem_mb + 1200`, address
  cap 2 x `mem_mb`, the 02:45-05:30 UTC blackout for `mem_mb >= 500`, yield to the collector pass).
- **Readers stream one capture, sweep or sample at a time; every reader and census is on the `cpu` lane under 400 MB.**
  Restores are `net` lane (data movement only). The only jobs above 400 MB are q0595 and q0598 (900 MB: demeaned OLS
  and 200 Freedman-Lane refits on at most 1.5 M thinned rows, §4.1); they run alone.
- **Disk:** `--disk-cap-gb`, `--data-dumps-cap-gb 40` (exit 75) in **every** job (CB17 window fix 7); CB18 outputs <= 0.2
  GB; restore trees are cleared after the dependent job's result is committed. CB18 never deletes or moves host data.
- **Stop rules:** 3 CPU-hours per family; a job failing twice for the same non-transient reason stops and is recorded.
  No re-screen of a failed CB18 test with altered windows, arms, classes, strata, horizons or populations, on any data.

## 3. Pre-censuses and routing (counts only; worn pre-window data; before any rules part other than `pre`)

Each census reads only the inputs named in `seals/cb18_census_inputs.json` (L4), refuses anything after its cut-off,
reads origin-side fields only (no capture, sweep or row after a unit's decision time, no target, no P&L), prints
counts, and is committed with its sha256 before the routing record. "Projected" = census count x W / census days.
"Effective" = units in markets with >= 2 units of the test's population in the census days. Every gate is fail-closed
(NaN fails; L2). Census SEs use the event and 6 h block ways only (§2.4; no UTC-day way at G = 2). Census days: **S, F:
the complete captures of UTC 2026-10-15 and 2026-10-16** with slot k − 1 from 2026-10-14T22:31Z, look-back captures
from 2026-10-14T12:31Z (S: k − 12), and sweep 1 of each pass (the days LT3 C1 and LT4 CQ/CH wore; the 10-15 files are
also CB17's pinned P2/P3 set). **P, R: the 23 sealed samples of 2026-10-16/17** with captures from 2026-10-15T16:31Z
(P's longest look-back is k − 4, the proxy `mid_{k−4}`; k − 4 of the first pass 10-16T00:31Z is 10-15T16:31Z; R2
finding 4: the earlier label "k − 12 from 10-15T12:31Z" was wrong, P reads no k − 12; the q0500 restore range is
unchanged and already covers it) to 2026-10-17T22:31Z; R reads only the sidecar of each sample's own capture k (for
the category; no price). **M: captures `[2026-10-12T00:31Z, 2026-10-16T00:00Z)`** (CB17's worn
span).

**Unavailable captures (declared; R1 finding 5).** The six complete captures of slots 2026-10-14T00:31Z, 02:31Z, 04:31Z,
06:31Z, 08:31Z and 10:31Z exist on no host copy and in no release (checked against the committed catalogues through
`data-20261020-dsheikh`; the only capture between 10-13T22:31Z and 10-14T12:31Z is the off-grid validation copy
`20261013T231958Z_80e78ef1` in `data-20261015-dsheikh-val`, 49 min after its slot and outside the 30 min tolerance, never
used). They are **unavailable**, never 0 and never interpolated: in census S the units at origins 10-15T00:31Z to
10:31Z need one of them for `|mid_k − mid_{k−12}|` and the prior-quiet count (`|mid_k − mid_{k−3}|` is unaffected); they
get status `lookback_unavailable`; it enters every count that needs only k − 1, k and sweep 1 (GS1-GS4, burst,
classes) and is left out of the proxy SE and the feature distributions, counted. In map M they are a capture gap
(§4.5).

### 3.1 CB18-S (CH177) census q0502 and routing rule
Counts (non-sports and sports separately; per capture and per day): eligible market-intervals; intervals numerically
unchanged (§4.1 field set) with both books untouched; among them, `updated_at` changed (**silent**) or not (**quiet**);
`updated_at` changed among **all** eligible intervals; `updated_at` missing, unparseable or after the capture receipt;
`uma_resolution_statuses` and `event_comment_count` change flags; `uma_resolution_statuses` at k by class (empty literal /
non-empty / missing); sidecar-only changes; `end_date` changes (CH07's class); **the `chg_*` byte flags (R1 finding 3):
the silent units of the pre-R1 definition (every §4.1 (8) field except `chg_*` equal) split by flag status (no `chg_*`
changed; `chg_1h` only; `chg_1d` or `chg_1w`; all three), the `chg_only` class (§4.1) and the quiet units by the same
flag split**; `lookback_unavailable` units (§3); the top capture's share of silent units and the number of captures over
the 20% burst line; silent units per event; `m` (DE); the quiet:silent ratio; permutable shares at strata levels 0-2;
composition-strata informativeness shares (§4.1); the proxy SE of the primary estimator on `Y_pre = |mid_k − mid_{k−12}|`
(SE only, event and 6 h block ways, §2.4), computed on silent and quiet units **thinned at the route's census-fixed rate
q** (so the `1/n0` term is the window's), with the primary's controls **minus the two `|mid|` controls** (the proxy is one
of them; leaving both out can only raise the SE).

| Gate (all must hold; NaN fails) | Value |
|---|---|
| GS1 not an indexer clock | `updated_at` changed in <= 50% of numerically unchanged (§4.1 (8), `chg_*` flags included), book-untouched non-sports intervals |
| GS2 not a tick clock (round 10's line) | `updated_at` changed in <= 50% of all eligible non-sports intervals |
| GS3 field usable | `updated_at` missing/unparseable/anomalous <= 10% of eligible rows |
| GS4 population | projected silent non-sports units (R1 definition: `chg_*` flags equal, `uma_resolution_statuses` empty at k) after the burst exclusion >= 200 a day |
| GS5 null usable | permutable share >= 60% at some ladder level (§2.3) |

**Routing (counts only; declared now; R1 finding 2 and Q5):** **RS-0** any gate fails → CB18-S dropped uncounted
(recorded with counts). **RS-1** gates pass and the pessimistic **arm-level 14-day** MDE
`MDE_RS1 = 3.80 x SE_proxy(q_CB) x sqrt(census days / 14) x sqrt(2) x sqrt(max(3, DE_W14 / DE_census)) x 1.5`
<= 1.0c → **CB route** (parts `common`, `S`). Here `SE_proxy(q)` is the census proxy SE (max over the event and 6 h
block ways) on units thinned at q; `DE_W14` and `DE_census` are `DE_computed` (§2.4) with `m_W` for the 14-day arm-0
window and for the census days; the inflation factor is never below sqrt(3). If the proxy SE is NaN, `MDE_RS1` is the
§2.4 formula with M = 3.80, SD **6c**, `n1` = projected arm-0 silent units, `n0` = projected thinned arm-0 quiet
units, `DE_gate` and the 1.5 factor. **RS-2** else, if the pessimistic **unsplit 28-day** LT MDE
`MDE_RS2 = 3.388 x SE_proxy(q_LT) x sqrt(census days / 28) x sqrt(max(3, DE_W28 / DE_census)) x 1.5` (NaN fallback as
RS-1 with M = 3.388 and 28-day unsplit counts) <= 1.0c → **LT5 member** with the §4.1 design and LT inference. **RS-3**
else dropped uncounted. **Both `MDE_RS1` and `MDE_RS2` are written into the routing record whichever route is taken**
(Q5). Values written into part `S`: the strata level, the quiet-thinning rate (q_CB: the largest of {1, 1/2, 1/4, 1/8}
whose projected arm-0 14-day frame is <= 1.5 M rows; q_LT: the same on the projected unsplit 28-day frame; each fixed
from counts before its proxy SE is computed), and the dormancy tercile cut points (features only); nothing else.

**Planning values (unprobed counts; R1 finding 2).** With SD 6c and DE 3: `MDE_RS1` at 200 silent units a day (1,400 per
arm) is **1.58c** with unlimited quiet units, 1.77c with quiet = 4 x silent, 2.24c with quiet = silent; RS-1 needs
about 500 / 630 / 1,000 silent units a day. `MDE_RS2` at 200 a day is 0.71c / 0.79c / 1.00c. At planning numbers RS-1
fails and the existing rule sends CB18-S to RS-2 (LT5) or RS-3 (drop); no looser rule is added.

### 3.2 CB18-P (CH172) census q0503 and routing rule
Counts (all categories and non-sports): parallel quote-only re-centerings (LT3 `classify`, |x| >= 1c) at capture k among
markets **in both pass k's and pass k+1's samples** (R1 finding 8; frame membership and the sampling stratum from each
sample's `plan.json`; 21 usable pass pairs among the 23 sealed samples, the two pairs that need the unsealed
10-17T04:40Z sample unavailable, counted), with the count of re-centerings dropped by the both-frames rule and the
fade/follow/none split by pass-k+1 sampling stratum; page coverage of `(t_k, t_{k+1}]` (oldest row `ts <= t_k` or page not full) versus truncated;
units with >= 1 row in `(t_k, t_{k+1}]`; **fade / follow / none / balanced** by the E007-signed net flow; `side` unusable
rows; fades per day; `m` (DE); top series family share; permutable shares at levels 0-2 (fade versus none); the
proxy SE on `c_pre = s x (mid_{k−2} − mid_{k−4})` (SE only).

| Gate | Value |
|---|---|
| GP1 population | projected 28-day fades >= 2,000 (round 10's line) in the routed population |
| GP2 split | fades between 20% and 80% of reacted (fade + follow) units |
| GP3 sign usable | `side` unusable (not BUY/SELL or outcome unknown) <= 10% of rows in the state windows |
| GP4 coverage | truncated <= 5% of otherwise eligible units |
| GP5 power | `MDE_GP5 = max(MDE_formula, MDE_proxy)` <= 0.5c (R2 finding 3). `MDE_formula`: pessimistic two-class MDE (M = 3.388, SD 5c, projected effective fades against projected effective none units, `DE_gate = max(3.0, computed)`, the 1.5 factor). `MDE_proxy = 3.388 x SE_proxy x sqrt(21 / (28 x 12)) x sqrt(max(3, DE_W28 / DE_census)) x 1.5`, `SE_proxy` = the fade coefficient's census SE on `c_pre` (max over the event and 6 h block ways); NaN proxy SE → `MDE_formula` alone; NaN formula → fails |
| GP6 null usable | permutable share >= 60% at some ladder level |

**Routing:** non-sports primary if GP1-GP6 hold on non-sports units; else all categories (sports split reported, as
LT4 E021) if they hold on all categories; else dropped uncounted. A pass → **LT5 member**. "Projected" for P = census
count x (28 x 12 pass pairs) / 21 usable pairs. Planning arithmetic (R1 finding 2): with `DE_gate` = 3 the pessimistic
gate needs about **12,900 fades in 28 days (about 460 a day)**, against round 10's guess of 1,680-3,360 (pessimistic
MDE 1.39c and 0.98c against the 0.5c floor): **drop expected**. **No 42-day LT5b branch is declared** (R1 Q8: it would
have to be declared in part `pre` now; declaring it would add a looser route after the pessimistic numbers are known,
the degree of freedom LT4 §1.1 refused). GP5 failing drops CB18-P, uncounted.

### 3.3 CB18-R (CH179): the race map q0504 (descriptive; no gates, no route)
**R1 finding 1: the counted CB18-R moderator test is dropped.** Its gate was the residualised donor gate that LT4 R2
recorded as failing a binding size scenario (corr 0.5: 0.085 against 0.075; "drop rather than redesign") and that LT3
donor-gate ruling 2 (2026-10-21) found structurally invalid (real and donor statistics are not exchangeable). Carrying the
same gate would be a redraw. No replacement null is declared in this response, so **CB18-R cannot be revived from this
census**: a revival would need a new null, declared before the census that informs it, passing a size check at that
census's measured label-control correlation (and, per Q11, one Holm across E016, E018 and R); none is proposed.

Counts and features (all categories; descriptive, k = 0): covered market-samples under E016's coverage rule; units with
>= 3 signed rows in `[t − 6 h, t)`; rows with a same-market, same-`ts`, different-`tx_hash` partner (**raced rows**) and
their share of rows; `R` = raced share per unit and its distribution (share of units with `R = 0`); the `ts` resolution
(share of rows with `ts mod 60 != 0`; the histogram of gaps between consecutive distinct `ts` in a market, 1 s through
10 s); the **fingerprint-identical** share of raced pairs (same side, outcome, size and price: possibly one taker
splitting an order); the same-side share of raced pairs. **The race map:** raced share by sidecar category, UTC hour,
row-count decile and price band. **Label (Q10):** if the gap histogram shows `ts` quantised at 2 s or coarser, every
"same second" in the map reads **"same block"** (disclosed in the map's header). Nothing about `zR` against the flow
moderators (correlations, VIF), no `x6`, no `y6`, no target: those served the dropped test only. Published whatever the
counts show.

### 3.4 CB18-F (CH176) census q0505
Counts only: per capture and `fee_type` (non-sports), events ranked by the sum of members' `volume24hr`; for each
candidate breakpoint **B in {10, 12, 20, 24, 50}** (declared now: the venue's list length is unknown), the share of rank
positions in `[B − 10, B + 10]` that change hands between consecutive captures, entries and exits across B per day, and
events per category with any crossing; the share of crossings with an E017-style surge label at the same capture (the
confound). **No price is read.** Re-entry rule in §4.4. Nothing routes to a counted test in CB18.

### 3.5 CB18-M (CH175) map q0506
Specified in §4.5 (descriptive; it reads last mids, so it is a map run on worn days only).

## 4. Families

### 4.1 CB18-S: silent edits (CH177)

**Hypothesis (one-sided).** Within a market, the 24 h absolute mid change after an interval in which Gamma's
`updated_at` moved while every numeric field the capture holds stayed put and the book was untouched (a **silent edit**:
a metadata change such as a rule clarification, description, date-adjacent or image change) is **larger** than after the
same market's quiet intervals (no change at all). **Direction: β_silent > 0.** Mechanism: rule edits are resolution risk
made visible on the page but not on the chart (CH08's trace without text); makers who keep quoting through them pay the
re-pricing. Who would be wrong: the indexer reading, under which `updated_at` is a sync stamp and the contrast is null.

**Unit.** Non-sports market x interval (k − 1, k) of consecutive complete captures. **Decision time:** the receipt of the
outcome-0 token's row in sweep 1 of pass k (minutes after capture k), so the book-untouched check is information at the
decision time (R1 Q1: accepted with the strict stamp rule). All state from captures k − 1, k, sweep 1 of pass k, and
(for the look-back controls and the prior-quiet count) captures back to k − 12 only (R1 finding 5). **Population
disclosure (Q1):** the strict stamp rule (both tokens' `book_timestamp` at or before `t_{k−1}`) restricts S to
**dormant books** (no book change of any depth for at least one slot); the result, whatever it is, speaks only about
silent edits on dormant books, not about silent edits on books that are being re-quoted.

**Eligibility** (in order, each exclusion counted): (1) binary, active, not closed at k − 1 and k; (2) two-sided at both
(`0 < bid < ask <= 1`); (3) spread <= 0.10 at both; (4) `mid_k` in [0.02, 0.98]; (5) as-of `end_date` unknown or more than
27 h after `t_k`; (6) non-sports by CB17's `is_sports_sidecar` on the sidecar of k (missing sidecar → excluded,
counted); (7) one row per `condition_id`; (8) **numerically unchanged**: byte-equal after float64 round-trip parse at
k − 1 and k for `best_bid, best_ask, spread, last_trade_price, volume24hr, liquidity, end_date, closed, active,
neg_risk` and the market-level sidecar fields `fee_type, fee_category, fees_enabled, fee_schedule, taker_base_fee,
order_price_min_tick_size, order_min_size, rewards_*, clob_rewards`, **and the raw byte-equality flags of `chg_1h`,
`chg_1d`, `chg_1w`** (R1 finding 3, Q2: flags only, the bytes as written, never parsed; a `chg_*` value can change while
the price stands still, because the look-back window rolls over an earlier move, so a `chg_*` change marks recent
volatility, not an edit); (9) **book untouched**: `book_timestamp` of both
tokens in sweep 1 of pass k at or before `t_{k−1}` (outcome-0 only where the sweep holds no outcome-1 row, flagged);
(10) `uma_resolution_statuses` byte-equal at k − 1 and k **and equal to the empty literal at k** (R1 finding 9, Q3; the
empty literal is the exact byte string the sidecar writer emits for an empty or absent list, fixed in part `pre` from
the writer's code, never from data; a change or a non-empty status is a resolution-process state, excluded, counted;
read through the whitelist exception of §1.1 only);
(11) not in a **burst capture** (more than 20% of the capture's otherwise eligible non-sports units silent: an indexer
re-sync), counted; (12) not in the election-night exclusion; (13) arm 0 (SCREEN_18) or arm 1 (REP_18).
`end_date` changes, sidecar-only changes and `event_comment_count` changes are reported classes, never silent.
**`chg_only`** (R1 finding 3): every (8) field equal except at least one `chg_*` flag, book untouched, (10)-(12) met;
reported by whether `updated_at` moved (counts and, in the window, the same secondaries as the primary), never silent or
quiet.

**Classes** (both require all of (1)-(13), so both have equal `chg_*` flags). `silent`: `updated_at(k) !=
updated_at(k − 1)` (parsed to epoch ms), `updated_at(k)` at or before `received_utc(k) + 5 s`, and not earlier than `updated_at(k − 1)`; `quiet`: equal. Anything else: excluded, counted.
Quiet units are thinned by a seeded hash (`sha256("cb18-thin-v1|" + market_id + "|" + slot_iso)`, keep if the first 8
hex digits / 2^32 < q; q census-fixed, §3.1); thinning is independent of every feature and target.

**Target and horizon.** `Y = |mid_{k+12} − mid_k|` (Gamma mids, slot k + 12, 24 h; status `two_sided` at k + 12). No
skip slot: the origin carries no quote event by construction, and the book-untouched rule makes `mid_k` the decision-time
mid. Secondaries (reported): `spread_{k+12} − spread_k`; **exit within 24 h** (status `absent` at k + 12, CH175's proxy)
by class; `Y` at 6 h; the sports arm; the `end_date`-change class; each restricted to non-burst captures.

**Primary.** Expanding-past market-demeaned OLS of `Y` on `1[silent]` over silent and (thinned) quiet units, controls
(all origin-side, demeaned the same way): `log1p volume24hr_k`, `spread_k`, `|mid_k − 0.5|`, log hours to the as-of end
(capped at 30 d; unknown flag), dormancy (log book age at sweep 1 of pass k, capped at 24 h, so no read before the
floor), the number of consecutive prior quiet intervals (**capped at 11**, R1 finding 5), **`|mid_k − mid_{k−3}|` and
`|mid_k − mid_{k−12}|`** (6 h and 24 h prior absolute moves of the Gamma mid; R1 finding 3: they absorb the recent
volatility that an uncaptured field change could proxy; a unit whose k − 3 or k − 12 capture is missing or not two-sided
is not a unit, counted as `lookback_missing`, never imputed), the `event_comment_count` change flag, UTC 6 h band
dummies. Clustering and p as §2.2. **Floor: β_silent >= +1.0c.**

**Binding checks for an advance** (all `True`; L2): (1) the Freedman-Lane gate at the selected stratum (§2.3; the silent
label correlates with dormancy and hour by design); (2) the composition guard (CB17 §2.6, part (a) with its permutation
part replaced by (1)): unit x stratum FE with strata = UTC 6 h band x dormancy tercile x spread band {<= 2c, > 2c}
(ladder: that; dormancy tercile x spread band; dormancy tercile; level chosen in `pre` by the 60% informativeness rule)
keeps the sign and at least half the estimate with p < 0.05; (3) the circular-shift calibration placebo; (4) drop the
top 5 clusters of each way: p and the floor hold; (5) leave-one-day-out; (6) availability >= 60% per class; (7) the Lee
lower bound keeps the sign (§2.6). A failed or `None` check: "not testable (...)" or "not detected", p = 1 in Holm,
counted.

**Stage 2.** S1-rep: the same estimator, controls, frozen strata level and thinning rate on arm-1 units in REP_18;
one-sided p < 0.05 under §2.2's Stage-2 Holm, the floor and checks (1)-(7). No econ test (sign-free). **Stage P** (only
if S1-rep passes): an LT-format registration of the maker widening rule (gross spread and move after silent edits),
never a claim from CB18 itself.

**Mechanism labels (never change a verdict).** *exit-driven* if the exit-within-24h difference (silent − quiet) is
positive and the available-unit contrast is not (the effect lives in the attrition); *event-level* if more than 50% of
silent units are in events where more than half the members were silent in the same capture (a bulk edit).

**Planning MDE (estimate; §2.4; recomputed in R1 finding 2).** Unknown counts: at 200 silent non-sports a day (the kill
line), an arm holds about 1,400 silent units in 14 days; the thinned quiet count `n0` is unprobed. Nominal (SD 5c, DE
1.5, no 1.5 factor, `n0` unlimited): `3.80 x 5 x sqrt(1/1,400) x sqrt(1.5) ≈ 0.62c`. **Pessimistic (SD 6c, `DE_gate` 3,
the 1.5 factor): 1.58c with `n0` unlimited, 1.77c with `n0` = 4 `n1`, 2.24c with `n0` = `n1`** (the draft's 1.06c
omitted the 1.5 factor and the `1/n0` term). At 500 a day: 1.00c / 1.12c / 1.42c. **The CB route does not meet the 1.0c
floor at planning numbers**; it needs about 500 (unlimited quiet) to 1,000 (quiet = silent) silent units a day. Routing
stays as declared (RS-1 on the census proxy SE, else RS-2, else RS-3). CB17's window power rule also binds at q0594: MDE
> 2 x floor → "not run (power)", counted.

**Leakage and confounds.** The sweep is minutes after capture k; it is the decision time, so the stamp is not future
information. `updated_at` may move on indexer re-syncs (GS1, GS2, the burst rule), on `chg_*` recomputation (now
excluded from silent and quiet by the byte flags and reported as `chg_only`; R1 finding 3), on changes of fields the
capture does not hold or CB18 may not read (rolling volumes other than `volume24hr`, `outcome_prices`: not checked;
the two prior-move controls absorb the recent volatility such changes would proxy; disclosed) or on reverted quote
flickers (excluded by the book-untouched rule). Silent
edits may concentrate in markets about to resolve; the as-of end control, the 27 h end rule and the exit secondary
address it; the Lee bound binds.

### 4.2 CB18-P: program versus human (CH172) → LT5 sketch

**Hypothesis (one-sided).** After a parallel quote-only re-centering of sign `s` at capture k (a program moved its
level), a taker who trades **against** it in `(t_k, t_{k+1}]` (a **fade**) is followed by continuation in the taker's
direction beyond the next slot: the skip-slot continuation after a fade is **lower** than after no taker reaction.
**Direction: β_fade < 0.** The "programs win" reading predicts β_fade >= 0 (reported).

**Unit.** Sampled market x pass k + 1 (the market is in **both pass k's and pass k + 1's active-frame samples**; R1
finding 8, Q15) whose interval (k − 1, k) is a
parallel quote-only re-centering under LT3's `classify` (|x| >= 1c) with LT4 §1.4's eligibility at k − 1 and k, as-of end
more than `t_{k+1}` + 9 h, page covering `(t_k, t_{k+1}]` (else truncated, excluded, counted). Population: non-sports
or all categories by the §3.2 routing rule. **Decision time:** the pass k + 1 sample's receipt.

**State.** Net E007-signed taker notional `f` over rows with `t_k < ts <= t_{k+1}` (YES terms; `side` under the E007
convention with q0400's 93.3% agreement disclosed as attenuation). Classes: **fade** `sign(f) = −s`; **follow** `sign(f)
= s`; **none** no row; **balanced** rows with `f = 0` (excluded, counted).

**Target.** Skip-slot `c = s x (mid_{k+4} − mid_{k+2})` (4 h): excludes slot k + 1 (the taker's own trade and its bounce)
and the k + 1 → k + 2 response (L9). Mechanism readings: `s x (mid_{k+2} − mid_{k+1})` (the immediate give-way; M1) and
`s x (mid_{k+1} − mid_k)` read as a label (the program's own re-adjustment, never a target).

**Primary.** Expanding-past market-demeaned OLS of `c` on `1[fade]`, `1[follow]` over fade, follow and none units;
controls `log1p |f|`, `log1p` rows in the state window, `log |x|`, logit `mid_k`, `spread_k`, `log1p volume24hr_k`, `log1p`
taker rows in `[t_k − 6 h, t_k]` (activity), and **pass k + 1 sampling-stratum dummies** (the volume-quartile stratum
from pass k + 1's `plan.json`; R1 finding 8); coefficient on `1[fade]` against none. **Collider (R1 finding 8):** pass
k + 1's sample is drawn by volume quartile, and that volume includes the state window's trades, so membership at k + 1
alone conditions on the state. Requiring membership at pass k (drawn before the state window) and adding the k + 1
stratum dummies compares fade, follow and none units within the same k + 1 sampling stratum among markets already in
the frame before the state began; residual selection inside a stratum is disclosed. **Floor 0.5c** (|β_fade| in the declared direction). Inference as LT4 §1.7 (event, event x UTC day, UTC day with
G = 28; p = max). **Gate:** Freedman-Lane permutation of the residualised `c` within the census-selected stratum (`p_perm
< 0.05`; the fade label correlates with `|f|` and the row count by construction). **Binding mechanism label:** *generic
flow continuation (not program-specific)* if the asymmetry `β_fade + β_follow` is not one-sided < 0 at p < 0.05 (a taker
pulls the price whichever way it trades, E007's +0.36c; the program reading needs the fade to pull harder than the follow
pushes; open question 7). Series-family rule as LT4 §14.2(9) (> 40% → excluded from the primary).

**Census and route:** §3.2. **Planning MDE (recomputed in R1 finding 2):** 28 days, F fades, N ≈ 1.5F none units, SD 5c,
M 3.388: nominal (DE 1.5, no 1.5 factor) F = 1,680 → 0.65c, F = 3,360 → 0.46c; **pessimistic (`DE_gate` 3, the 1.5
factor) F = 1,680 → 1.39c, F = 3,360 → 0.98c**. Below the 0.5c floor pessimistically only at F >= about **12,900**
(about 460 fades a day), and the both-frames rule only lowers F. **CB18-P does not meet its floor at planning numbers;
by GP5 it is expected to be dropped at the census, uncounted.**

**Economics (LT5, reported):** maker: after a fade, do not re-post at the program's level ("humans win") or quote into
the fade ("programs win"), gross, no fills; taker follow-the-fade at recorded touches against 4.5c.

**Leakage and confounds.** The state window ends at `t_{k+1}`, before the decision; the frame's activity selection is at
the decision time (origin-side) but makes the none class "active through other trades", hence the activity control; a
fade may be a closer or hedger (the CH171 open/close split was E023's, which LT4 R2 dropped; reported here only as a descriptive); crypto series
may dominate parallel re-centerings (family rule).

### 4.3 CB18-R: races (CH179): the race map only (k = 0)

**Status after R1 (finding 1).** The counted LT5 moderator test (`β(x6 · zR) < 0` on the E016 form, gated by
`donor_gate_resid`) is **dropped, uncounted** (no rules part had bound). Its gate is the residualised donor gate that
LT4 R2 recorded as failing a binding size scenario (corr 0.5: 0.085 against 0.075) and that LT3 donor-gate ruling 2
found structurally invalid; LT4 dropped E023/E024 (k = 3) for the same reason, and LT3 made the donor gate non-binding
for E016/E018. The draft's text calling E023/E024 live moderators was wrong and is withdrawn. The hypothesis (raced
flow is mechanical arbitrage and continues less) is recorded as **untested**, not as rejected. Re-entry: only as a new
design with a null declared before the census that informs it and size-checked at that census's measured label-control
correlation, Holm across E016, E018 and R (Q11); none is proposed here.

**The race map (k = 0, published whatever it shows).** From q0504 on the 23 worn samples only (§3.3): raced share by
category, UTC hour, row-count decile and price band; the fingerprint and same-side shares; the `ts` resolution and gap
histogram, with the *same-block* reading if `ts` is quantised (Q10). No target, no flow statistic, no comparison with
any later price; the cross-venue pair list is not used (the sealed stream ends 2026-11-03 and CB18 opens no window
store). **Economics:** none (descriptive).

### 4.4 CB18-F: the front page as a clock (CH176): census only, with a re-entry rule

**Why no counted test now.** (1) The breakpoint `B` (the category list's default length) and the venue's sort key
("volume" versus an undocumented "trending") cannot be fixed without looking at the venue, which this batch may not do;
round 10 itself made `B` an assumption. (2) Round 10's own arithmetic: about 300-600 crossings in 21 days put the money
target's (members' 24 h outcome-0 mid change, E017's target) MDE at 1.5-2c against a 1.0c floor; only the attention
target (2 h log volume change) is powered, and attention is not a route. (3) Entry/exit labels are mechanically tied to
the volume trajectory (an entry is a surge, E017's object): round 10's entry-minus-exit contrast would mostly re-measure
mean reversion in volume.

**Re-entry rule (declared now).** A counted CH176 test may be registered in a later live-test family only if all hold
before its registration: (a) `B` and the sort key are fixed **only** by a documented, dated observation of the venue's
category pages committed to the repo (an owner action or a separately approved fetch; no price recorded), with the
observation's date before the window; **q0505's churn shares never choose, suggest or break a tie for `B`** (R1 finding
11); (b) q0505 shows >= 20% of positions in `[B − 10, B + 10]` change hands per pass for that observed `B`; if the
observed `B` is not in {10, 12, 20, 24, 50}, q0505 is **re-run on the same pinned worn inputs, counts only, for that
`B` alone** (a new job id at that time; no price read) before (b) is judged, and no other `B` is computed; (c)
the projected crossings over a 60-day window put the money target's pessimistic MDE at or below 1.0c. **Design sketch
for that test:** a regression discontinuity at rank `B` within `fee_type` x capture (running variable: the log volume gap
to the B-th event; local linear, triangular kernel, bandwidth fixed before data; event x UTC day clusters), the E017 surge
label as a control, placebo cutoffs at `B ± 5` as binding falsification; primary on the money target; the attention
target reported. Until then CH176 is a census (k = 0).

### 4.5 CB18-M: the last-mid outcome map (CH175)

**What it is.** A host-only historical **map** (k = 0) on the worn captures of `[2026-10-12T00:31Z, 2026-10-16T00:00Z)`
(about 3.6 effective days; round 10 asked for a week; the shortfall is disclosed). **Exit** = a market present in
complete capture j and absent from the next two complete captures in the map window; markets whose last presence is
after 2026-10-15T20:00Z are "undetermined" (counted). Capture gaps never create exits (the two following captures must
be complete and present in the window). **Gap disclosure (R1 finding 10, Q13):** the six unavailable captures of
2026-10-14T00:31Z-10:31Z (§3) sit inside the map window. A market that left during the gap is recorded as last present
at 10-13T22:31Z (its true last presence and last mid can be up to 12 h later than recorded), and its absence is first
confirmed at 10-14T12:31Z and 14:31Z, so end-to-exit lags around the gap are **stretched or shifted by up to 12 h**.
Exits whose recorded last presence is 10-13T22:31Z carry a `gap_adjacent` flag; every count and lag is reported with and
without them. 3.6 effective
days are accepted as enough for the map (Q13).

**Counts (by sports/non-sports via the sidecar, structure standalone / neg-risk member / other multi, as-of horizon at
the last presence: past end, 0-2 h, 2-24 h, > 24 h, unknown):** (1) exits per day by the **symmetric** band of the last
two-sided mid's distance from one half, `d = |mid − 0.5|` (R1 finding 10: the two tails are folded, so the map never
records on which side a market left): `d > 0.49` (the old `[0, 0.01)` and `(0.99, 1]`), `0.45 <= d <= 0.49` (the old
`[0.01, 0.05]` and `[0.95, 0.99]`), `d < 0.45` (the old `(0.05, 0.95)`), and "no two-sided quote at last presence" (then
the band of the last two-sided mid within 6 h, within 24 h, or none); (2) the lag from the as-of `end_date` to the exit; (3)
self-consistency: re-appearances after an exit (expected 0; a count above 0 measures listing flicker), and neg-risk
events whose members all exit within 24 h: the number whose members are all at `d > 0.49` versus not (the draft's
"exactly one member in the upper tail" needs a side and is dropped under the fold); (4) the number of
middle-band exit ids a light Gamma fetch would need per day (counted, nothing fetched); (5) the window arithmetic: for
CH163, CH164's resolution arm, CH157/E017's carry arm and CH62, the projected number of markets with as-of end inside a
21, 60 and 90-day window whose exit lands in a folded tail band (`d >= 0.45`), by class.

**Forbidden in the map (unit-tested):** any comparison of an earlier price with the last mid (no calibration,
favourite-longshot or drift statistic), any return, any P&L. **Consequence:** the map's days are worn for every
resolution or calibration arm; no counted test may later use `[2026-10-12, 2026-10-16)` for one.

## 5. Jobs (draft specs)

The JSON specs are in `docs/research_lab/queue/drafts/q0500_*.json` .. `q0599_*.json` (status DRAFT in each `notes`).
None is promoted before: the R1 re-check on this file; part `pre`; census code with unit tests (forbidden fields and
roots, cut-off refusals, pin completeness, exact float writes, the class truth tables). **q0500/q0501 release tags and
globs are now fixed from the committed catalogues and checked with `restore_from_archive.py --list` (release metadata
only; §11, finding 7):** q0500 selects 364 files (67 captures x 4 files; 48 sweep directories x 2 files) from
`data-20261015-dsheikh` (112), `-16` (28), `-17` (96), `-18` (88), `-18-2` (4), `-19` (36), each capture from exactly one
release (the Mac-era `data-20261013-research-lab` and `data-20261014-research-lab-tail` duplicate 10-11..10-13 captures
and would clash, so they are not used); q0501 selects exactly the 92 files of `seals/lt3_census_inputs_C2.json` from
`data-20261017-dsheikh` (8), `-18` (48), `-19` (36), and their `files.sha256` hashes equal the seal's
`files_sha256_sha256` values and all 92 per-file hashes. Window jobs (q0590-q0599) also need parts `common` and `S`, the code
freeze record and the code-against-design freeze check. Priorities: restores 30, censuses 28 (they decide LT5's
membership; ahead of CB batch work, behind registered live tests), window jobs 9 (as CB17).

## 6. Code needed (not written by this document)

- `backend/astrolabe/research_lab/cb18_common.py`: pin-checked readers (captures, sidecars, sweep 1, samples) with
  whitelists and refused roots; exit-75 missing-input handling with the stopped-source record; the arm and thinning
  hashes; the strata-ladder selection; the proxy-SE power gate (SE only); imports by pinned sha256 of LT3 `classify` and
  slot helpers, CB17 `is_sports_sidecar`, LT4 `fl_perm_gate` and the CR1 engine (no `donor_gate_resid`; L5); the
  explicit whitelist exception for `chg_1h/1d/1w` and `uma_resolution_statuses` (byte equality and the empty-literal
  test only; §1.1); the floor guard (no capture, sweep or row before 2026-10-26T00:00Z on a window path).
- `cb18_pre.py`: q0502, q0503, q0505 censuses and the routing writer (`seals/cb18_routing.json`, with both `MDE_RS1`
  and `MDE_RS2`); `cb18_map.py`: q0504 (race map) and q0506.
- `cb18_s.py`: the S frame (features, raw target-mid table, statuses), the window census, Stage 1, Stage 2, labels.
- `backend/scripts/run_cb18.py` with subcommands `census-s`, `census-p`, `map-race`, `census-f`, `map-lastmid`, `smoke`,
  `keys`, `frame`, `census-window`, `screen`, `rep`, `stage2-final`, `size-check`.
- Tests `test_cb18_*.py`: forbidden fields (wallets, `chg_*` values, outcome fields; `chg_*` or
  `uma_resolution_statuses` reaching anything but the byte-equality / empty-literal helpers); the `chg_only` class and
  the silent/quiet split by `chg_*` flag; a non-empty `uma_resolution_statuses` at k excluded; the look-back cap (prior
  quiet count stops at 11; a read at k − 13 or before 2026-10-26T00:00Z refused); `lookback_unavailable` for the
  10-14 gap (never 0); `DE_gate` never below 3 and NaN `m` failing; the RS-1/RS-2 formulas with the 1.5 factor and the
  inflation floor; P's both-frames rule and the k + 1 stratum dummies; the map's folded bands (no side written) and
  `gap_adjacent`; census cut-offs; pin completeness and missing-pin refusal; exact float round trip; float64
  quotes; the silent/quiet truth table (each field of the equality set; `updated_at` earlier, equal, later, after receipt);
  book-untouched edges (stamp at `t_{k−1}` exactly, outcome-1 missing); burst rule at 20%; thinning independence; the
  fade/follow/none/balanced table; coverage at the page edge; the race definition (same `ts` and same `tx_hash` is not a
  race; three rows in one second); the map's exit rule with a capture gap; the map's forbidden statistics; `None` never
  passes; exit 75 on a missing file; Freedman-Lane gate recovers a planted effect and holds size under label-control
  correlation; the binding overlapping-target scenario (MA(11) target, persistent clustered label, selected level and
  level 2); the 3-of-200 rule's edges; battery2 kinds.

## 7. Test budget, compute and calendar

| Job | Counted | Kind |
|---|---|---|
| S1 (Stage 1; only if routed RS-1) | 1 | `cb18_test`, `creative_batch_18:S` |
| S1-rep (only if S1 advanced) | <= 1 | `cb18_replication`, `creative_batch_18:S:rep` |
| Pre-censuses, routing, race map (CB18-R, map only), F census, M map, smoke, keys, window census, gates, placebos, size checks, sports arm, secondaries | 0 | `cb18_descriptive` |
| CB18-P (and S under RS-2) | 0 here | counted by LT5 if registered |
| CB18-R moderator test | 0 | dropped before any rules part (R1 finding 1); not counted anywhere |
| **Total in CB18** | **0-2** | cumulative count recorded at each counting run |

**Compute.** Censuses about 2-3 CPU-hours in all on worn data (two capture days, 23 samples); the map under 1 h; S frames
about 1 h per window; S screen about 1-2 h (200 Freedman-Lane refits). Peak RAM 900 MB (q0595, q0598, alone); every
reader and census < 400 MB. Network: restores only (net lane). Disk <= 0.2 GB of outputs plus transient restore trees.

| By (UTC) | Deliverable | Owner |
|---|---|---|
| 2026-10-21 | challenger round 1 (REVISE, 2026-10-20) and response (§11) done; R1 re-check | `science-reviewer`, designer |
| 2026-10-22 12:00 | part `pre` committed; census input seal from the release manifests; q0500/q0501 restores; census code and tests | implementer, queue |
| 2026-10-23 | q0502-q0506 run (cpu lane, < 400 MB each) | queue |
| **2026-10-24 12:00** | **routing record** (`seals/cb18_routing.json`, ledger): each idea's route by §3's rules | orchestrator |
| 2026-10-24 → | `LIVE_TESTS_5.md` drafted from the LT5-routed members (§4.2, §4.1 under RS-2), if any | designer |
| **2026-10-25 18:00** | parts `common`, `S` landed (CB route only) = `T18_rules` → **S_18 = 2026-10-27T00:00Z** | orchestrator |
| before 2026-10-27 (preferred), 2026-11-11 08:00 at the latest | S window code, size check, code-against-design freeze check, freeze record, q0590 PASS, q0591 | implementer, `science-reviewer` |
| by about 2026-10-28 | LT5 registration commit (challenger, size check, pins) → **LT5 `REGISTERED_UTC` 2026-10-30T00:00Z** (rule in §1.2) | orchestrator |
| 2026-11-11 08:00 → after E011's and E012's analysis commits (E012 on or after 2026-11-13T12:00Z) | q0592 → q0593 → q0594 → q0595 (Stage 1) | queue |
| 2026-11-25 08:00 | q0596 → q0597 → q0598 → q0599 (only if S1 advanced) | queue |
| 2026-11-28 12:00 | LT5 single analysis (if registered) | LT5 |

## 8. Open questions for the challenger (answered in R1; the answers and resulting changes are in §11)

1. **CB18-S decision time at the sweep.** Is moving the decision time to sweep 1's receipt (to make "book untouched"
   origin-side) sound, and is "both tokens' `book_timestamp` at or before `t_{k−1}`" too strict (dormant books only) or
   not strict enough (deep-level changes do update the stamp; P2 says hash and stamp move together)?
2. **`chg_*` fields.** Gamma may bump `updated_at` when it recomputes price-change fields. CB18 keeps CB17's guard (never
   parsed). Should byte-equality flags of `chg_*` be admitted to the numerically-unchanged set (flags only), or is the
   indexer-clock gate GS1 enough?
3. **`uma_resolution_statuses` as a change flag.** Reading only byte equality to exclude resolution-process events: an
   acceptable use of a resolution-adjacent field, or should it be dropped entirely (then such events stay in "silent")?
4. **Binding Lee lower bound** for S (§2.6): right, given exits are the predicted events, or over-strict?
5. **CB18-S routing (RS-1 before RS-2).** Is preferring the batch route on stability grounds right, when an unsplit
   28-day LT test would have more power?
6. **Thinning quiet units** by a seeded hash at a census-fixed rate: acceptable, or must the full quiet population enter
   (memory permitting)?
7. **CB18-P primary.** Fade versus none with the asymmetry `β_fade + β_follow` as a binding label, or the asymmetry as the
   primary (it nets out generic flow continuation but leans on symmetric continuation and doubles the variance)?
8. **CB18-P power.** If GP5 fails at 28 days, is a separately registered 42-day single-test LT5b admissible (the length
   chosen from worn counts before registration), or is that the researcher degree of freedom LT4 §1.1 refused?
9. **Permutation ladder** up to market x 7-day block (§2.3): still a valid within-unit null for sparse units?
10. **CB18-R semantics.** If `ts` is the Polygon block time (about 2 s), "same second" is "same block": keep R with the
    *block-resolution* label, or redefine? Is the 50% fingerprint-identical kill the right guard against order splitting
    without wallets?
11. **Moderator multiplicity.** CB18-R would be the fifth moderator (E016, E018, E023, E024) on the same flow regression
    across three families. Should LT5 adjust for the moderator family across LT3-LT5, or is per-family Holm plus the M3
    count sufficient?
12. **CB18-F.** Is the candidate set B in {10, 12, 20, 24, 50} reasonable for a counts-only census, and is an
    owner-documented observation an acceptable way to fix `B` before a future registration?
13. **CB18-M.** Is 3.6 worn days enough for the map's arithmetic, or should it wait for a full week of later worn data
    (which would wear those days for every resolution arm)?
14. **Small G in a 14-day screen.** S uses CB17's convention (6 h block in the max, UTC day by leave-one-day-out). Accept,
    or use LT's (UTC day in the max with t on 13 df)?
15. **Activity selection in CB18-P.** The active frame at pass k + 1 is chosen partly on trades in the state window. Is
    the activity control enough, or should the primary be restricted to markets in the frame at both passes k and k + 1?

## 9. Draft ledger block (DRAFT, not recorded, nothing counted)

```
## CB18 DRAFT (design only), 2026-10-20 ~19:20Z; R1 REVISE 2026-10-20; R1 response 2026-10-21; nothing frozen, queued, run or counted
- Round 10's remainder after LT4: CH172 (CB18-P), CH175 (CB18-M map), CH176 (CB18-F census), CH177 (CB18-S),
  CH179 (CB18-R race map only). CH178 excluded: a second counted test of E015's hypothesis on overlapping origins before
  E015's analysis (re-entry only as a declared E015 replication after 2026-11-15T12:00Z, disjoint origins).
- R1 response: CB18-R counted test dropped (donor gate failed size in LT4 R2; invalid per LT3 ruling 2), map kept;
  DE_gate = max(3.0, computed), RS-1/RS-2 with SE inflation, 1.5 factor and the 1/n0 term; chg_* byte flags and two
  prior-move controls in CB18-S; binding MA(11) overlapping-target size scenario; prior-quiet cap 11 (no read before
  10-26T00Z); the 10-14 00:31-10:31Z captures declared unavailable; q0500/q0501 tags and globs fixed from the catalogues;
  CB18-P both-frames rule + k+1 stratum dummies; uma empty-literal exclusion; M bands folded; F's B only from a dated
  venue observation.
- Pessimistic planning: CB18-S 1.58c (200 silent/day, CB route) vs 1.0c floor -> RS-1 not expected; RS-2 (LT5) 0.71-1.00c;
  CB18-P 0.98-1.39c vs 0.5c floor (needs ~12,900 fades/28 d) -> drop expected at GP5. Routing rules unchanged.
- Counted in CB18: 0-2 (S1; S1-rep if triggered), expected 0 at planning numbers. LT5 members counted by LT5 only.
- Proposed dates: part `pre` 2026-10-22T12Z; routing 2026-10-24T12Z; T18_rules 2026-10-25T18Z → S_18 2026-10-27T00Z;
  SCREEN_18 [10-27, 11-10), REP_18 [11-10, 11-24); LT5 REGISTERED_UTC 2026-10-30T00Z, 28 days, analysis >= 11-28T12Z.
- Queue drafts q0500-q0599 (`queue/drafts/`; argv `scripts/run_cb18.py`, not yet written); q0517-q0519 reserved.
- Branch `feat/cb18` (<commit>). Next: R1 re-check (science-reviewer) of §11.
```

## 10. Next actions
1. R1 re-check (`science-reviewer`) of the response in §11 (findings 1-11 and Q1-Q15); the orchestrator decides.
2. Implementer, after an accepting re-check: part `pre`, then census code and tests; write
   `seals/cb18_census_inputs.json` from the release manifests (q0500/q0501 tags and globs are fixed, §5); promote
   q0500-q0506.
3. Orchestrator: commit the routing record from the census outputs by §3's rules only; draft `LIVE_TESTS_5.md` from the
   LT5-routed members; land parts `common`, `S` by 2026-10-25T18:00Z if CB18-S routes to the batch.

## 11. R1 response (2026-10-21)

Response to `reviews/CB18_CHALLENGER_R1_2026-10-20.md` (REVISE), written 2026-10-21 00:25 UTC+1 (2026-10-20T23:25Z) on
`feat/cb18` after merging `chore/arepo-claude-setup` (catalogues through `data-20261020-dsheikh`, LT3/LT4 changes, the
LT4 R2 review and re-check, LT3 donor-gate ruling 2). No census ran, no data file was opened, no outcome was read; the
only data-side action was `restore_from_archive.py --list` (release metadata: `MANIFEST.sha256`, `files.sha256`). No
alpha, floor, threshold, gate or MDE requirement was loosened; where a family misses its floor at the pessimistic
numbers, it is said so and the existing routing rule applies.

| # | Finding | Change | Where |
|---|---|---|---|
| 1 | HIGH: CB18-R reuses the failed residualised donor gate (a redraw) | CB18-R's counted moderator test **dropped, uncounted** (before any rules part); the race map kept as descriptive (k = 0) with the Q10 *same-block* label; GR1-GR6, `zR` correlations/VIF and the routing rule removed; no replacement null declared, so no revival from this census; "E023/E024 live" text corrected (dropped by LT4 R2, k = 3); donor gates removed from CB18 (L5) | §0 table, §0.1, §1.3, §2.0 L5/L9, §2.3, §2.4, §2.7, §3.3, §4.3, §6, §7; q0504 |
| 2 | HIGH: DE formula treats 0.02 as an estimate; RS-1 misses factors | `DE_gate = max(3.0, computed)` (NaN fails); RS-1 = `3.80 x SE_proxy(q_CB) x sqrt(days/14) x sqrt(2) x sqrt(max(3, DE_W14/DE_census)) x 1.5`, RS-2 likewise with 3.388 and 28 days; proxy SE on units thinned at the route's q (the `1/n0` term), census SE ways = event and 6 h block (no UTC-day way, G = 2); NaN fallback uses SD 6c; both MDEs in the routing record. **Pessimistic planning: S 1.58c at 200/day (unlimited quiet; 1.77c / 2.24c at quiet = 4x / 1x) vs 1.0c floor, needs ~500-1,000 silent/day; RS-2 0.71-1.00c at 200/day. P 1.39c / 0.98c at 1,680 / 3,360 fades vs 0.5c floor, needs ~12,900.** Both miss their floors on planning numbers; routing unchanged (S → RS-2 or RS-3 unless the census proxy SE says otherwise; P → drop at GP5) | §0.1, §2.0 L14, §2.4, §3.1, §3.2, §4.1, §4.2; q0502, q0503 |
| 3 | HIGH: "silent" may be uncaptured numeric changes (volatility proxy) | raw byte-equality flags of `chg_1h/1d/1w` added to the unchanged set (never parsed); new reported class `chg_only`; controls `|mid_k − mid_{k−3}|` and `|mid_k − mid_{k−12}|`; census counts silent (pre-R1 definition) and quiet units by flag status; whitelist exception to `cb13_common` forbidden lists; residual unchecked fields (`outcome_prices`, other rolling volumes) disclosed | §1.1, §3.1, §4.1 (8), classes, controls, leakage; §6; q0502 |
| 4 | HIGH: no size check with overlapping targets | binding scenario: MA(11) target in slot steps (absolute value, point mass at 0), persistent (Markov 0.9) and capture-clustered silent label, 0.5 label-control correlation, 2 h grid over 14 days, at the selected level **and** level 2; binding for the FL gate, the placebo and the Stage-1 rule (0.0251) or the LT gate (0.058); failure → "not testable (size)", p = 1 if part `S` is committed, no level change or second draw | §2.0 L6, §2.3, §6 |
| 5 | MEDIUM: lookback to k − 13 reads inside the CB13-T HOLDOUT; census needs the missing 10-14 captures | prior-quiet count capped at **11** (longest read k − 12 = 10-26T00:31Z for the first origin; S_18 unchanged); floor guard unit-tested at the old k − 13; the six captures 10-14T00:31Z-10:31Z declared **unavailable** (in no release, checked against the catalogues; the off-grid `-val` capture not used): census S units at 10-15T00:31Z-10:31Z get `lookback_unavailable` (counted, out of the proxy SE, never 0) | §1.2, §2.6, §3 intro, §4.1, §6 |
| 6 | MEDIUM: undisclosed prior `updated_at`-derived ages | disclosure of `quote_age_s` / `ml_quote_staleness_h` (`ml_panel.py:281-284, 331`; `CREATIVE_HYPOTHESES_2026-10-22.md`:106, 331), different construct, not cited as evidence | §1.3 |
| 7 | MEDIUM: q0501 tags miss `data-20261019-dsheikh`; `plan.json` not restored | q0501: tags `data-20261017/18/19-dsheikh`, globs `trade_samples/2026101[67]T*/{manifest.json,plan.json,features.csv.gz,trades.csv.gz}` (no wallets); `--list` selects 8 + 48 + 36 = 92 files = the seal's 92 paths exactly; the three `files.sha256` hashes equal the seal's `files_sha256_sha256` and all 92 per-file hashes match. q0500 also fixed: tags `data-20261015/16/17/18-dsheikh`, `data-20261018-dsheikh-2` (the 10-17T04:31Z capture, previously missing), `data-20261019-dsheikh`; `data-20261014-research-lab-tail` removed (duplicates `-15`, would clash); per-capture globs so each capture comes from one release; `--list` selects 364 files (67 captures x 4, 48 sweep dirs x 2) | §1.1, §5; q0500, q0501 |
| 8 | MEDIUM: CB18-P collider (k + 1 frame sampled on volume incl. the state window) | unit restricted to markets in **both** pass k's and pass k + 1's samples; pass k + 1 sampling-stratum dummies in the primary (dummies chosen over 1/pi weights); census counts on the restricted population over 21 usable pass pairs (the unsealed 10-17T04:40Z sample is not used; its two pairs unavailable) | §1.1, §3.2, §4.2; q0503 |
| 9 | LOW: `uma_resolution_statuses` needs a whitelist exception | explicit exception (byte equality and empty-literal test only); units whose status at k is not the writer's empty literal (fixed from the writer code in part `pre`) excluded, counted | §1.1, §4.1 (10), §6 |
| 10 | LOW: CB18-M tails reveal side; gap stretches lags | bands folded to `d = |mid − 0.5|` (> 0.49, 0.45-0.49, < 0.45); the side-dependent neg-risk count dropped; `gap_adjacent` flag and lags with/without; 3.6 days accepted (Q13) | §4.5; q0506 |
| 11 | LOW: CB18-F `B` must not come from churn | `B` only from the dated venue observation, never from q0505's shares; if not in {10, 12, 20, 24, 50}, q0505 re-run counts-only on the same inputs for that `B` alone | §4.4 |

**Answers taken (Q1-Q15).** Q1 sweep decision time and strict stamp rule kept, dormant-books-only population disclosed
(§4.1). Q2 `chg_*` flags admitted (finding 3). Q3 `uma_resolution_statuses` flag kept with finding 9. Q4 binding Lee
bound kept. Q5 RS-1 first; both MDEs in the routing record (§3.1). Q6 hash thinning kept. Q7 fade versus none stays
primary. Q8 **no 42-day LT5b declared** (a looser route chosen after the pessimistic numbers; GP5 failing drops P).
Q9 7-day level kept, subject to the finding-4 scenario at level 2. Q10 *same-block* label in the race map. Q11 moot (R
dropped); a revival would need one Holm across E016, E018, R. Q12 accepted with finding 11. Q13 3.6 days accepted. Q14
CB17's small-G convention kept. Q15 = finding 8.

**R1 "could not verify", now checked or still open.** Release tags for the 10-16/17 captures and sweeps: **checked**
against the committed catalogues and `--list` (finding 7). Overlap with LT2: **E012's population contains CB18-S's units**
(no change condition, 24 h target); disclosed in §1.3, not pooled; E014 reads samples. **Still open:** whether the host's
3-day sweep deletion is enabled (q0592/q0596 restore byte for byte from releases either way, so the frames do not depend
on it); the releases for 2026-10-26..11-24 (do not exist yet; q0592/q0596 tags stay placeholders, fixed before
promotion); LT4's `REGISTERED_UTC` (enters only LT5's date rule, §1.2); Gamma `updated_at` semantics (the census's GS1-GS3
decide; nothing assumed).

**Families after R1.** Counted in CB18: **CB18-S only** (S1, S1-rep: 0-2), and only if RS-1 passes on the census proxy
SE, which the pessimistic planning numbers do not expect (expected k = 0 in CB18; S then goes to LT5 under RS-2 or is
dropped). LT5 candidates: CB18-S (RS-2), CB18-P (drop expected). Not counted: CB18-R (map), CB18-F (census), CB18-M
(map).

## 12. R2 response (2026-10-21)

Response to `reviews/CB18_CHALLENGER_R2_2026-10-21.md` (ACCEPT_WITH_CHANGES), written 2026-10-21 on `feat/cb18` before part
`pre` is frozen and before any census ran. No floor, alpha, threshold, gate or MDE requirement was changed except as listed;
finding 3 makes P's power gate the stricter of its two readings.

| # | Finding | Change | Where |
|---|---|---|---|
| 1 | MEDIUM: censuses read inside J4-R `[10-16, 10-21)` without saying so | disclosure added: S, F read the 10-16 captures and sweeps, P and the race map the 10-16/17 samples and captures; CB18 follows LT3's rule (J4-R refused only for maker mark-out objects); **no census object is a mark-out** (origin-side fields at or before each unit's decision time; counts, shares and SEs only; the writer refuses outcome keys); "J4-R untouched" restricted to window paths; HOLDOUT `[10-21, 10-26)` untouched (cut-off 10-17T22:31Z, floor 10-26T00:00Z) | §1.2 lookback floor row, §1.3 first bullet; part `pre` (`J4R_DISCLOSURE`) |
| 2 | MEDIUM-LOW: no size scenario with the label tracking latent volatility | new scenario: per-market AR(1) latent log-volatility scaling the innovations and raising the silent probability (γ in {0.5, 1.0}), `|mid|` controls from the simulated path; **reported, not binding** (its rate measures confounding at an assumed γ, which no count identifies); above the route's limit at γ = 0.5 → label *latent-volatility sensitive* on S1, never a verdict change | §2.3; part `S` size check (CB route) or LT5 (RS-2) |
| 3 | LOW: P's power gate ambiguous (proxy SE vs formula) | GP5 pinned as `max(MDE_formula, MDE_proxy) <= 0.5c`, both written; proxy NaN → formula alone; the S routing (proxy SE replaces the formula) unchanged | §2.4, §3.2 GP5; part `pre` (`GP5_RULE`); q0503 |
| 4 | LOW: P's look-back label "k − 12 from 10-15T12:31Z" wrong | label fixed: P reads back to k − 4 (from 10-15T16:31Z); no restore change (q0500 covers it); R reads only each sample's capture-k sidecar (category), so q0504 now depends on q0500 | §3 intro; q0503, q0504 |
| 5 | LOW: q0595 waits for E011 but not E012 | q0595 also refuses before E012's analysis commit (on or after 2026-11-13T12:00Z; overlapping population and 24 h target) | §0.3 table, §1.2 date table, §7 calendar; q0595 (`--require-e012-analysis`) |


## 13. Census interpretation notes, 2026-10-21, written before any census run

Written after the independent code check of the census code (`science-reviewer`, verdict CENSUS_READY_WITH_FIXES,
2026-10-21) and before q0502-q0506 ran on real data. The sealed rules (`seals/cb18_rules.json`, part `pre`; its hash is
unchanged by everything below) leave the following readings open. Each choice is the conservative or rule-faithful one;
no threshold, gate or formula changed.

| # | Point | Choice and reason |
|---|---|---|
| 1 | Capture time | The time of a capture is the maximum `received_utc` over **all** rows of its file, taken before any market filter or de-duplication (the sealed `CAPTURE_TIME_RULE`: the last page's receipt). Fixed in `cb18_common.read_capture`; it feeds P's state-window start, S's `t_{k-1}` in the book-untouched test and the cut-off check. |
| 2 | P category | A unit whose category cannot be read (sidecar missing or incomplete, or the market absent from it) has an **unknown** category. It is excluded from the non-sports population, kept in the all-category population and counted (`category_unknown_units`). Reason: unknown never passes; treating it as non-sports would fail open. |
| 3 | Book untouched, outcome 1 | If the outcome-1 book is in sweep 1 but its stamp is missing, the book is not untouched (`b1 = ~ok1 or (finite stamp and stamp <= t_{k-1})`). Reason: unknown never passes. |
| 4 | Sweep receipt | An unparseable or missing sweep-1 receipt makes the age unknown: the unit is excluded and counted in the waterfall step `receipt_missing`. |
| 5 | GP3 | The side-unusable share is computed over **all categories'** state-window rows and used for both gate sets (non-sports and all). Reason: the rule gives one share of "rows in the state windows"; the all-category share is the larger sample; the non-sports-only share is derivable from the counts and is not used. |
| 6 | GP4 | The denominator of the truncated share is the units with status `ok` (non-ok units are reported separately as `status_not_ok`, not counted as truncated or as eligible). Reason: coverage is undefined without a returned trade page. |
| 7 | P design effect | The design-effect population is the **fades**, by Gamma event id (else market id), as for S's silent units. |
| 8 | GS4 (disclosure) | GS4 counts silent units whose look-back status is `lookback_missing`; the frame (and the proxy SE, features) leaves them out, counted. GS4 needs only k - 1, k and sweep 1. |
| 9 | Eligibility step (6) (disclosure) | Step (6) requires the sidecar at k - 1 as well as at k (the (8) equalities need both). A missing sidecar at k - 1 therefore moves a unit out of GS2/GS3's denominators (both start at step (7)). Counted as `sidecar_missing`. |
| 10 | Map M exits (disclosure and change) | The first code version undid an exit when the market re-appeared later, so the exit tables depended on later captures. M carries no gate and no route (it is descriptive; its window arithmetic is planning only), so no gate could be affected. It is nevertheless changed so that an exit is judged **only on information up to its own confirmation time**: a later re-appearance is counted once per market (`reappearances_after_exit`, the flicker measure of §4.5) and never removes the exit or overwrites its record. |
| 11 | Routing record | `routing` refuses an output whose `rules_pre_sha256` is not the current one, and refuses if the five outputs do not share one `code_sha256`. |

**Later parts.** Parts `common` and `S` must be declared in their own module, never by adding constants to
`cb18_rules_pre.py` (that would change the part `pre` hash).
