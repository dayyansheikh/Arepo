# Creative batch 18 (CB18): silent edits, program versus human, races, the front page and the last-mid map (round 10's remainder)

`evidence_role: none` at drafting (design only) | planned roles: `exploratory_historical` (pre-censuses and the CH175
map on worn pre-window host data, counts and descriptives only), `prospective` (CB18-S's SCREEN_18 and REP_18 windows,
which start at least 24 h after the rules commit) | status: **DRAFT, not reviewed, nothing frozen, nothing queued, no
code.** Drafted 2026-10-20 20:19 UTC+1 (2026-10-20T19:19Z) on branch `feat/cb18` from `9a68ea2f`
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
| **CB18-S** silent edits | CH177 | **yes** (`updated_at` semantics, silent counts, burst shares, proxy SE) | **CB18 SCREEN_18 / REP_18**, event-arm split; LT5 only if powered unsplit but not split; else dropped | field semantics are unknown and may drift (indexer behaviour), so two windows on disjoint event arms test stability; sign-free, EV 2, no taker route; its units are disjoint by construction from every live primary, so a batch screen costs no Holm slot elsewhere | S1 (Stage 1), S1-rep (Stage 2, triggered): **0-2** |
| **CB18-P** program versus human | CH172 | **yes** (parallel re-centerings in the active frame, fade/follow/none split, coverage, permutable share) | **LT5 member** (28-day window) | power is the binding risk; a 14-day half-arm screen would kill a true effect; the trade-sample reader convention is LT's | 0 (counted in LT5 if registered) |
| **CB18-R** races | CH179 | **yes** (same-second multi-order rows, `ts` resolution, fingerprint share, corr and VIF gates) + the race **map** | **LT5 member** (flow moderator on the E016 form) | flow moderators need the whole window's events (an arm-split 14-day screen roughly doubles the MDE past the 0.0036 gate) | 0 (map k = 0; counted in LT5 if registered) |
| **CB18-F** front page | CH176 | **yes** (rank churn at candidate breakpoints) | **census only (k = 0)**, re-entry rule for a 60-day live test | the breakpoint `B` and the venue's sort cannot be fixed without a network look (not allowed here); the money target needs 60+ days | 0 |
| **CB18-M** last-mid map | CH175 | the map itself (host-only historical, descriptive) | **map (k = 0)** | an enabler, not a hypothesis | 0 |

**Counted in CB18: 0-2** (S1 if CB18-S routes to the batch; S1-rep only if S1 advances). Every other test is counted
in LT5's own family, if and when LT5 registers it. **LT5 candidates: CH172 (CB18-P), CH179 (CB18-R), and CH177 only
under routing rule RS-2** (§3.1). LT5 is a separate document (`LIVE_TESTS_5.md`, not written here); §4 gives each
member in LT4's shape so it can be lifted without re-deriving the unit, null or gate.

### 0.1 Honest expectation
- **CB18-P will probably drop at its census.** Its pessimistic planning MDE reaches the 0.5c floor only with about
  4,800-6,500 fades in 28 days (170-230 a day, §4.2); round 10 guessed 60-120 a day. The design is written so the census
  decides cheaply.
- **CB18-S lives or dies on a field nobody has read**: if `updated_at` moves on an indexer clock, the idea is dead at the
  census, uncounted. If it survives, it is a sign-free maker-protection mechanism at best.
- **CB18-R is mostly a map.** Its counted moderator is the fifth on the same flow regression (after E016, E018, E023,
  E024) and is likely correlated with E018's trains; the corr gate may drop it.
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
| q0501 | `cb18_census_restore_samples` (the 23 LT3-C2-sealed samples of 10-16/17) | P, R | net / 600 | any time |
| q0502 | `cb18_pre_census_S` (CH177) | S | cpu / 380 | part `pre` + census code + tests + `seals/cb18_census_inputs.json` |
| q0503 | `cb18_pre_census_P` (CH172) | P | cpu / 380 | as q0502 |
| q0504 | `cb18_pre_census_R` (CH179, incl. the race map) | R | cpu / 390 | as q0502 |
| q0505 | `cb18_pre_census_F` (CH176) | F | cpu / 300 | as q0502 |
| q0506 | `cb18_map_lastmid` (CH175 map) | M | cpu / 350 | as q0502 |
| q0507 | `cb18_smoke` (part hashes, refusals, exact reproduction of q0502's counts with frozen code) | S | cpu / 390 | parts `common`, `S` committed + code freeze record |
| q0508 | `cb18_exclusion_keys` (ids only; seal copies; overlap counts) | S | cpu / 300 | after q0507 PASS |
| q0509 | `cb18_restore_screen` (SCREEN_18 captures, sidecars, sweep 1 rotated off the host) | S | net / 600 | `not_before` S_18 + 15 d + 8 h |
| q0510 | `cb18_frame_screen_S` (arm-0 units, features only, raw target-mid table, no target computed) | S | cpu / 390 | after q0509, q0508 |
| q0511 | `cb18_census_18` (window gates, SE-only power gate, informativeness at the selected level) | S | cpu / 390 | after q0510 |
| q0512 | `cb18_screen_18` (Stage 1: S1) | S | cpu / 900 | after q0511, E011's analysis commit, code-against-design freeze check |
| q0513 | `cb18_restore_rep` (REP_18 inputs) | S | net / 600 | `not_before` S_18 + 29 d + 8 h; only if S1 advanced |
| q0514 | `cb18_frame_rep_S` (arm-1 units; sealed) | S | cpu / 390 | after q0513 and the SCREEN result commit |
| q0515 | `cb18_rep_18` (Stage 2: S1-rep, triggered) | S | cpu / 900 | after q0514 |
| q0516 | `cb18_stage2_final` (one strict Holm over triggered Stage-2 tests; write-once) | S | cpu / 300 | after q0515 |
| q0517-q0519 | reserved (LT5 jobs take their own ids in `LIVE_TESTS_5.md`) | - | - | - |

If CB18-S does not route to the batch, q0507-q0516 are withdrawn (recorded in the ledger, never promoted).

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Role in CB18 | Evidence ceiling |
|---|---|---|
| Complete captures `snapshots/<id>/rows.csv.gz` + `rows_ext.csv.gz` and sweep 1 `book_sweeps/<id>/` of **`[2026-10-11T22:31Z, 2026-10-17T22:31Z]`**, restored byte for byte (q0500) | pre-censuses q0502-q0505 and the q0506 map; counts, origin-side features and SEs on pre-origin proxies only (§3). The days already worn by CB17 P2/P3, LT3 C1 and LT4 CQ/CH/CF | counts |
| The **23 LT3-C2-sealed active-frame trade samples** of 2026-10-16/17 (`seals/lt3_census_inputs_C2.json`), restored by q0501 | q0503, q0504; counts and origin-side features (`ts, side, price, size, outcome_index, asset, tx_hash`; `origin_utc`, `trades_truncated`) | counts |
| Captures, sidecars and sweep 1 of SCREEN_18 and REP_18 (host copies where present, else restored byte for byte, hash-checked against the release manifests) | CB18-S Stage 1 (arm 0) and Stage 2 (arm 1) | L2 (post-freeze live window) |
| Trade samples during an LT5 window | LT5 members only, through LT5's own per-pass reader (not a CB18 job) | LT5's |
| `live_trades/` (monitor), `cross_venue_live/` (E009/E010, sealed to 2026-11-03), `surprise_live/` (E011), `live_tests2/`, `live_tests3/`, `live_tests4/`, `creative_batch16/`, `creative_batch17/`, CB8-H holders, `e001/`-`e007/`, `forecasts/`, `flow_screen/`, every `h*` root | **never opened** (runner refuses; unit-tested) | - |

**Not read anywhere in CB18:** wallet fields of any kind; `chg_1h/1d/1w` (E004-E007 guard, as CB17 §1.3);
`outcome_prices`, `closed_time`, any Gamma outcome field; question text. `uma_resolution_statuses` and
`event_comment_count` are read **only as byte-equality change flags** between two captures, never parsed (§4.1, open
question 3).

### 1.2 Dates (declared; UTC)

| Name | Value | Meaning |
|---|---|---|
| `T18_draft` | 2026-10-20T19:19Z | this draft; no CB18 quantity computed |
| `T18_pre` | target 2026-10-22T12:00Z (soft) | commit of part `pre` of `seals/cb18_rules.json` (census paths and cut-offs, whitelists, every census gate and routing rule of §3, the strata ladders and selection rule, the proxy-SE recipe), after the challenger round on this file and **before any census code runs on data** |
| census cut-off | 2026-10-17T22:31Z (captures, samples); map: 2026-10-16T00:00Z | census paths refuse any file or row timed after it |
| routing record | target 2026-10-24T12:00Z | after q0502-q0506; `seals/cb18_routing.json` (counts and the route of each idea, by the §3 rules only) and a ledger line, before any part other than `pre` |
| `T18_rules` | target **2026-10-25T18:00Z** (soft) | committer time of the commit that lands parts `common` and `S` (CB route only) on `chore/arepo-claude-setup`, with the census-fixed values written in (CB17 ruling O2's definition) |
| lookback floor | 2026-10-26T00:00Z | no CB18 window path reads a row timed before it (keeps J4-R `[10-16, 10-21)`, CB13-T HOLDOUT `[10-21, 10-26)` and the census days untouched); CB18-S's longest lookback is 24 h (§4.1), so S_18 >= 2026-10-27T00:00Z never needs a pre-floor row |
| `S_18` | `max(2026-10-27T00:00Z, the first 00:00Z at or after T18_rules + 24 h)` | start of SCREEN_18; depends only on the rules commit time. With `T18_rules` by 2026-10-26T00:00Z, **S_18 = 2026-10-27T00:00Z** |
| SCREEN_18 | origin (decision) times in `[S_18, S_18 + 14 d)` = **[2026-10-27, 2026-11-10)** | Stage 1, arm-0 events only |
| REP_18 | origin times in `[S_18 + 14 d, S_18 + 28 d)` = **[2026-11-10, 2026-11-24)** | Stage 2, arm-1 events only |
| event arm | `arm(e) = int(sha256("cb18-arm-v1|" + event_id).hexdigest()[0], 16) mod 2`; `event_id` = Gamma event id, else the market id | arm 0 → SCREEN_18, arm 1 → REP_18; disjoint by construction; fixed before data. Targets of late SCREEN units read REP-window captures of arm-0 events only |
| election-night exclusion | origin or target capture in `[2026-11-03T18:00Z, 2026-11-05T00:00Z)` | excluded and counted (as CB17) |
| `T18_code` | target: before `S_18`; at the latest before the first read of any SCREEN_18 file (q0510, 2026-11-11T08:00Z); never before an accepting code-against-design freeze check | as CB17 §1.2 `T17_code` and ruling 6: no agent opens a SCREEN_18 or REP_18 file before the freeze record exists; ledger attestation |
| E011 | analysed once after 2026-11-11T13:00Z | q0512 refuses before E011's analysis commit (S's target is a 24 h movement, close to E011's object; costs about one day) |
| LT5 (proposed) | `REGISTERED_UTC` = the first 00:00Z at least 24 h after the LT5 registration commit, at least 48 h after LT4's `REGISTERED_UTC`, and **not before 2026-10-30T00:00Z**; 28 days; analysis once at `END_UTC + 36 h` | proposed **2026-10-30T00:00Z to 2026-11-27T00:00Z**, analysis on or after 2026-11-28T12:00Z; fixed end, no extension (as LT4 §1.1) |

If `S_18` slides, both windows slide; lengths are fixed. Frames run after each window and its 24 h targets close:
q0510 not before `S_18 + 15 d + 8 h` (2026-11-11T08:00Z); q0514 not before `S_18 + 29 d + 8 h` (2026-11-25T08:00Z).

### 1.3 Overlaps and sealed data
- **CB18-S units are disjoint by construction from every live primary's units**: an S unit is a market-interval in which
  no capture numeric field changed and the book was untouched (§4.1). E015/E020 (quote-only moves), E017 (volume
  surges), E021/E022 (traded moves), E019 (re-quoted ladders), CB17-B (sweep pairs with touch rules; B2 needs a shift)
  and CB17-C (traded event-intervals) all require a change that S excludes. Collection overlap with LT2-LT4, E011,
  CB16 and CB17 windows is disclosed; no store is opened; no pooling.
- **CB18-P** overlaps E015's parallel class (same units at capture k, different contrast and target, E015's window to
  11-14). **CB18-R** shares every trade sample, `x6` and `y6` with E013, E016, E018, E023 and E024 (a new moderator;
  W and H are controls). Both are disclosed in LT5's overlap table; never cited as corroborating one another.
- **Exclusion keys (q0508, no network):** CB16 q0380's key file (sha256 copied from its write-once manifest, never
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
| L5 | Freedman-Lane gates (LT4 R1 finding 7; `LT3_PERM_GATE_CHECK`) | where the tested label or moderator correlates with controls, the permutation gate shuffles the control-residualised target within strata with the label fixed (`fl_perm_gate`); donor gates donate only the moderator's within-market residual (`donor_gate_resid`) with a `corr_controlled` <= 0.5 census gate |
| L6 | Size checks on the code to be pinned (LT3 13.5, LT4 L5) | every gate is size-checked at >= 2,000 worlds per scenario, including label-control correlation 0.4 and 0.5 (binding) and 0.7 (reported); a failing scenario blocks the pin |
| L7 | No selection on post-decision marks (CB17 ruling O9) | eligibility uses only information at or before the decision time; target unavailability is a status in the availability denominator with a binding bound (§2.6), never an eligibility filter |
| L8 | Smoke tied to frozen code (CB17 window fix 2) | q0507 stores `code_sha256` and refuses unless the code freeze record exists; it reproduces q0502's printed counts exactly (a different count is a FAIL and is investigated, not adjusted) |
| L9 | Skip-slot targets where bounce contaminates (round 10 lesson 5; LT4 L9) | CB18-P's target skips the slot holding the taker's trade; CB18-S has no quote event at the origin (by construction) and needs none; CB18-R keeps the E016 target with LT3's early-ending-window label |
| L10 | Clustering (LT4 L10; CB4 A-C1; CB10 §2.3 small-G) | ways: event, event x UTC day (two-way), and UTC day; p = max, with t on G − 1 df for the one-way ways; in 14-day CB windows UTC day (G = 14) is replaced in the max by the 6 h block (G = 56) and leave-one-day-out binds (as CB17 §2.3) |
| L11 | Census drops are uncounted only before the rules bind (CB15-L, CB17 §2.5) | after a part commit every declared test is counted, with p = 1 if a gate fails |
| L12 | Readers at the pass cadence (round 10 lesson 6) | LT5 members read samples online (3-day host retention); CB18-S reads captures and sweeps after the window from host copies or byte-for-byte restores |
| L13 | Composition is not a placebo (CB16 §11, CB17 §2.6) | CB18-S keeps CB17's two-part composition guard, with its permutation part made Freedman-Lane |
| L14 | Planning MDE at or below the floor in every census (LT3 fix 4, LT4 L4) | each routing rule includes a pessimistic MDE recomputed on census-projected effective counts with a measured design effect (LT4 R1 finding 8) |

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
- **Donor gate** (CB18-R in LT5): `donor_gate_resid` (LT4 §14.1 item 7), donors >= 12 h away in the same market.
- **Size check** (L6): CB-route gates at 2,000 worlds must pass at most **0.0251** of null worlds (the 3-of-200 rule's
  nominal 4/201 ≈ 0.0199 plus 1.645 sqrt(0.02 x 0.98 / 2,000)); LT-route gates at most 0.058 (LT4 L5). Scenarios: iid
  labels; persistent market label rates; AR(1) labels; label-control correlation 0.4 and 0.5 (binding) and 0.7
  (reported); heavy-tailed targets (CB18-S's |move| has a point mass at 0).

### 2.4 Materiality floors and planning-MDE conventions
- **Floors (declared now):** CB18-S **+1.0c** on the 24 h absolute-move contrast (round 10); CB18-P **0.5c** on the
  skip-slot continuation (the fade coefficient, in the declared negative direction); CB18-R gross **0.5c** in the
  favourable cell plus the **0.0036 per SD** MDE gate (LT4 §8: E007's whole 1 h flow effect); CB18-F none (k = 0).
- **Planning MDE.** Two-class: `MDE = M x SD x sqrt(1/n1 + 1/n0) x sqrt(DE) x 1.5` (pessimistic; the 1.5 covers SD
  misestimation, as LT4 §8). Continuous moderator: LT4's `0.002873 x sqrt(5,000 / projected events) x sqrt(VIF)`.
  `M = 3.80` for CB route ((z_0.99 + z_0.80) x 1.2, CB17 §2.7), `3.388` for LT route (LT4 §8).
  `DE = 1 + (m_W − 1) x 0.02`, `m = Σ n_e² / Σ n_e` by event on the census population, `m_W = m x W / census days` (LT4 R1
  finding 8; pessimistic for short-lived events).
- **SD sources (assumptions, round 9/10, LT3/LT4):** 24 h move SD about 6c (round 9); 24 h absolute move about 5c (round
  10, CH177); 4 h skip-slot change about 5c (LT4 §14.3, E021); log event volume change 0.5 (round 10, CH176). Where a
  census can compute the estimator's own clustered SE on a **pre-origin proxy target** (SE only; no point estimate
  written; CB17 §2.7), that SE replaces the formula.

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
  `noprev`, `nosweep`, `updated_at_missing`, `stamp_missing`).
- Each eligible unit receives one target status: `two_sided`, `one_sided`, `closed_flag`, `absent` (left the listing),
  `capture_missing`. Only `two_sided` units carry a target.
- **Availability (binding, CB route):** the available share must be >= 60% of eligible in each contrasted class, else
  "not testable (availability)". **Attrition:** if the non-available shares differ by more than 2 pp between classes, the
  result carries *attrition-differential* and Lee trimming bounds are computed; **for CB18-S the Lee lower bound must
  keep the predicted sign for an advance** (binding; stricter than LT4, where the label never changes the verdict),
  because exits after a silent edit are the very events the hypothesis predicts.

### 2.7 Costs and economics (separate; never changes a verdict)
CB18-S is sign-free: no taker route; the maker route ("widen for one day after a silent edit") is reported **gross, no
fills** as the spread change and the move. CB18-P and CB18-R economics follow LT4 §1.10 inside LT5 (paper taker round
trip at recorded touches with sidecar fees, `max_if_unknown`; >= 30 trades in >= 10 events). Declared in advance: every
AREPO taker cost check has failed (E004 −4.5c touch-to-touch; E007 +0.36c gross against about 4.5c; 0 of 95 economic
cells positive); "not shown" is the expected economic outcome. Hurdles: taker 4.5c median round trip (1.8c at liquidity
>= $100k); maker routes have paid 1-7c adverse selection in every AREPO study.

### 2.8 Compute, lanes, disk and stop rules
- Host: 1 OCPU, shared; queue rules as CB17 §2.8 (one job per lane, nice 19, `MemAvailable >= mem_mb + 1200`, address
  cap 2 x `mem_mb`, the 02:45-05:30 UTC blackout for `mem_mb >= 500`, yield to the collector pass).
- **Readers stream one capture, sweep or sample at a time; every reader and census is on the `cpu` lane under 400 MB.**
  Restores are `net` lane (data movement only). The only jobs above 400 MB are q0512 and q0515 (900 MB: demeaned OLS
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
(NaN fails; L2). Census days: **S, F: the complete captures of UTC 2026-10-15 and 2026-10-16** with slot k − 1 from
2026-10-14T22:31Z and sweep 1 of each pass (the days LT3 C1 and LT4 CQ/CH wore; the 10-15 files are also CB17's pinned
P2/P3 set). **P, R: the 23 sealed samples of 2026-10-16/17** with captures from 2026-10-15T12:31Z (look-back k − 12, k −
4) to 2026-10-17T22:31Z. **M: captures `[2026-10-12T00:31Z, 2026-10-16T00:00Z)`** (CB17's worn span; the 10-14
00:31-10:31Z captures are missing on the host and are unavailable, counted).

### 3.1 CB18-S (CH177) census q0502 and routing rule
Counts (non-sports and sports separately; per capture and per day): eligible market-intervals; intervals numerically
unchanged (§4.1 field set) with both books untouched; among them, `updated_at` changed (**silent**) or not (**quiet**);
`updated_at` changed among **all** eligible intervals; `updated_at` missing, unparseable or after the capture receipt;
`uma_resolution_statuses` and `event_comment_count` change flags; sidecar-only changes; `end_date` changes (CH07's class);
the top capture's share of silent units and the number of captures over the 20% burst line; silent units per event;
`m` (DE); the quiet:silent ratio; permutable shares at strata levels 0-2; composition-strata informativeness shares
(§4.1); the proxy SE of the primary estimator on `Y_pre = |mid_k − mid_{k−12}|` (SE only, max over ways).

| Gate (all must hold; NaN fails) | Value |
|---|---|
| GS1 not an indexer clock | `updated_at` changed in <= 50% of numerically unchanged, book-untouched non-sports intervals |
| GS2 not a tick clock (round 10's line) | `updated_at` changed in <= 50% of all eligible non-sports intervals |
| GS3 field usable | `updated_at` missing/unparseable/anomalous <= 10% of eligible rows |
| GS4 population | projected silent non-sports units after the burst exclusion >= 200 a day |
| GS5 null usable | permutable share >= 60% at some ladder level (§2.3) |

**Routing (counts only; declared now):** **RS-0** any gate fails → CB18-S dropped uncounted (recorded with counts).
**RS-1** gates pass and the pessimistic **arm-level 14-day** MDE (`3.80 x SE_proxy x sqrt(census days / 14) x sqrt(2)`,
max over ways; the formula of §2.4 if the proxy SE is NaN) <= 1.0c → **CB route** (parts `common`, `S`). **RS-2** else, if
the pessimistic **unsplit 28-day** LT MDE (`3.388 x ...`, §2.4) <= 1.0c → **LT5 member** with the §4.1 design and LT
inference. **RS-3** else dropped uncounted. Values written into part `S`: the strata level, the quiet-thinning rate q
(the largest of {1, 1/2, 1/4, 1/8} whose projected arm-0 frame is <= 1.5 M rows), and the dormancy tercile cut points (features only); nothing else.

### 3.2 CB18-P (CH172) census q0503 and routing rule
Counts (all categories and non-sports): parallel quote-only re-centerings (LT3 `classify`, |x| >= 1c) at capture k among
markets in pass k+1's sample; page coverage of `(t_k, t_{k+1}]` (oldest row `ts <= t_k` or page not full) versus truncated;
units with >= 1 row in `(t_k, t_{k+1}]`; **fade / follow / none / balanced** by the E007-signed net flow; `side` unusable
rows; fades per day; `m` (DE); top series family share; permutable shares at levels 0-2 (fade versus none); the
proxy SE on `c_pre = s x (mid_{k−2} − mid_{k−4})` (SE only).

| Gate | Value |
|---|---|
| GP1 population | projected 28-day fades >= 2,000 (round 10's line) in the routed population |
| GP2 split | fades between 20% and 80% of reacted (fade + follow) units |
| GP3 sign usable | `side` unusable (not BUY/SELL or outcome unknown) <= 10% of rows in the state windows |
| GP4 coverage | truncated <= 5% of otherwise eligible units |
| GP5 power | pessimistic two-class MDE (M = 3.388, SD 5c, effective fades against effective none units, measured DE) <= 0.5c |
| GP6 null usable | permutable share >= 60% at some ladder level |

**Routing:** non-sports primary if GP1-GP6 hold on non-sports units; else all categories (sports split reported, as
LT4 E021) if they hold on all categories; else dropped uncounted. A pass → **LT5 member**. Planning arithmetic: the
pessimistic gate needs about 4,800 (DE 1.1) to 6,500 (DE 1.5) fades in 28 days, against round 10's guess of 1,680-3,360:
**drop expected** (open question 8 asks whether a 42-day single-test LT5b is admissible).

### 3.3 CB18-R (CH179) census q0504, the race map and routing rule
Counts and features (all categories): covered market-samples under E016's coverage rule; units with >= 3 signed rows in
`[t − 6 h, t)`; rows with a same-market, same-`ts`, different-`tx_hash` partner (**raced rows**) and their share of rows;
`R` = raced share per unit, its distribution (share of units with `R = 0`); the `ts` resolution (share of rows with
`ts mod 60 != 0`; the histogram of gaps between consecutive distinct `ts` in a market, 1 s through 10 s); the
**fingerprint-identical** share of raced pairs (same side, outcome, size and price: possibly one taker splitting an order);
the same-side share of raced pairs; `zR` centre and scale; `|corr(zR, z_other)|` for every controlled moderator (`zW`,
`zH`, `zN`, `zSize`, `zSPR`, `zRV`, `zHTE`); VIF of `x6·zR` on the model's other `x6` terms after demeaning; projected
events. **The race map** (descriptive, k = 0): raced share by sidecar category, UTC hour, row-count decile and price band.

| Gate | Value |
|---|---|
| GR1 rate | raced rows >= 3% of rows in covered windows (round 10) |
| GR2 population | `R` > 0 in projected >= 20,000 covered units over 28 days (round 10's 20,000, held at the LT5 window) |
| GR3 resolution | share of rows with `ts mod 60 != 0` >= 50% (LT4 E021's second-level check) |
| GR4 not order splitting | fingerprint-identical pairs <= 50% of raced pairs |
| GR5 not E018 | `|corr(zR, zH)|` <= 0.5 and `corr_controlled` (max over all controlled moderators) <= 0.5 |
| GR6 power | `0.002873 x sqrt(5,000 / projected 28-day events) x sqrt(VIF)` <= 0.0036 |

**Routing:** all hold → **LT5 member**; else dropped uncounted, the map published either way (k = 0).

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
decision time. All state from captures k − 1, k, sweep 1 of pass k, and (for dormancy) captures back to k − 12 only.

**Eligibility** (in order, each exclusion counted): (1) binary, active, not closed at k − 1 and k; (2) two-sided at both
(`0 < bid < ask <= 1`); (3) spread <= 0.10 at both; (4) `mid_k` in [0.02, 0.98]; (5) as-of `end_date` unknown or more than
27 h after `t_k`; (6) non-sports by CB17's `is_sports_sidecar` on the sidecar of k (missing sidecar → excluded,
counted); (7) one row per `condition_id`; (8) **numerically unchanged**: byte-equal after float64 round-trip parse at
k − 1 and k for `best_bid, best_ask, spread, last_trade_price, volume24hr, liquidity, end_date, closed, active,
neg_risk` and the market-level sidecar fields `fee_type, fee_category, fees_enabled, fee_schedule, taker_base_fee,
order_price_min_tick_size, order_min_size, rewards_*, clob_rewards`; (9) **book untouched**: `book_timestamp` of both
tokens in sweep 1 of pass k at or before `t_{k−1}` (outcome-0 only where the sweep holds no outcome-1 row, flagged);
(10) `uma_resolution_statuses` byte-equal at k − 1 and k (a change is a resolution-process event, excluded, counted);
(11) not in a **burst capture** (more than 20% of the capture's otherwise eligible non-sports units silent: an indexer
re-sync), counted; (12) not in the election-night exclusion; (13) arm 0 (SCREEN_18) or arm 1 (REP_18).
`end_date` changes, sidecar-only changes and `event_comment_count` changes are reported classes, never silent.

**Classes.** `silent`: `updated_at(k) != updated_at(k − 1)` (parsed to epoch ms), `updated_at(k)` at or before
`received_utc(k) + 5 s`, and not earlier than `updated_at(k − 1)`; `quiet`: equal. Anything else: excluded, counted.
Quiet units are thinned by a seeded hash (`sha256("cb18-thin-v1|" + market_id + "|" + slot_iso)`, keep if the first 8
hex digits / 2^32 < q; q census-fixed, §3.1); thinning is independent of every feature and target.

**Target and horizon.** `Y = |mid_{k+12} − mid_k|` (Gamma mids, slot k + 12, 24 h; status `two_sided` at k + 12). No
skip slot: the origin carries no quote event by construction, and the book-untouched rule makes `mid_k` the decision-time
mid. Secondaries (reported): `spread_{k+12} − spread_k`; **exit within 24 h** (status `absent` at k + 12, CH175's proxy)
by class; `Y` at 6 h; the sports arm; the `end_date`-change class; each restricted to non-burst captures.

**Primary.** Expanding-past market-demeaned OLS of `Y` on `1[silent]` over silent and (thinned) quiet units, controls
(all origin-side, demeaned the same way): `log1p volume24hr_k`, `spread_k`, `|mid_k − 0.5|`, log hours to the as-of end
(capped at 30 d; unknown flag), dormancy (log book age at sweep 1 of pass k, capped at 24 h, so no read before the
floor), the number of consecutive prior quiet intervals (capped at 12), the `event_comment_count` change flag, UTC 6 h
band dummies. Clustering and p as §2.2. **Floor: β_silent >= +1.0c.**

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

**Planning MDE (estimate; §2.4).** Unknown counts: at 200 silent non-sports a day (the kill line), an arm holds about
1,400 silent units in 14 days; quiet units are far more numerous (unprobed). With SD 5c and DE 1.5: `3.80 x 5 x
sqrt(1/1,400) x sqrt(1.5) ≈ 0.62c`; pessimistic (SD 6c, DE 3): about 1.06c, just over the 1.0c floor; at 500 a day:
0.39c (0.67c pessimistic). RS-1 uses the census proxy SE instead. CB17's window power rule also binds at q0511: MDE >
2 x floor → "not run (power)", counted.

**Leakage and confounds.** The sweep is minutes after capture k; it is the decision time, so the stamp is not future
information. `updated_at` may move on indexer re-syncs (GS1, GS2, the burst rule), on `chg_*` recomputation (not
readable here; disclosed; open question 2) or on reverted quote flickers (excluded by the book-untouched rule). Silent
edits may concentrate in markets about to resolve; the as-of end control, the 27 h end rule and the exit secondary
address it; the Lee bound binds.

### 4.2 CB18-P: program versus human (CH172) → LT5 sketch

**Hypothesis (one-sided).** After a parallel quote-only re-centering of sign `s` at capture k (a program moved its
level), a taker who trades **against** it in `(t_k, t_{k+1}]` (a **fade**) is followed by continuation in the taker's
direction beyond the next slot: the skip-slot continuation after a fade is **lower** than after no taker reaction.
**Direction: β_fade < 0.** The "programs win" reading predicts β_fade >= 0 (reported).

**Unit.** Sampled market x pass k + 1 (the market is in pass k + 1's active-frame sample) whose interval (k − 1, k) is a
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
taker rows in `[t_k − 6 h, t_k]` (activity; the frame is selected on activity at k + 1); coefficient on `1[fade]` against
none. **Floor 0.5c** (|β_fade| in the declared direction). Inference as LT4 §1.7 (event, event x UTC day, UTC day with
G = 28; p = max). **Gate:** Freedman-Lane permutation of the residualised `c` within the census-selected stratum (`p_perm
< 0.05`; the fade label correlates with `|f|` and the row count by construction). **Binding mechanism label:** *generic
flow continuation (not program-specific)* if the asymmetry `β_fade + β_follow` is not one-sided < 0 at p < 0.05 (a taker
pulls the price whichever way it trades, E007's +0.36c; the program reading needs the fade to pull harder than the follow
pushes; open question 7). Series-family rule as LT4 §14.2(9) (> 40% → excluded from the primary).

**Census and route:** §3.2. **Planning MDE:** 28 days, F fades, N ≈ 1.5F none units, SD 5c, DE 1.2-1.5, M 3.388:
F = 1,680 → 0.65c (0.98c pessimistic); F = 3,360 → 0.46c (0.69c pessimistic). Below the floor pessimistically only at
F >= about 4,800-6,500.

**Economics (LT5, reported):** maker: after a fade, do not re-post at the program's level ("humans win") or quote into
the fade ("programs win"), gross, no fills; taker follow-the-fade at recorded touches against 4.5c.

**Leakage and confounds.** The state window ends at `t_{k+1}`, before the decision; the frame's activity selection is at
the decision time (origin-side) but makes the none class "active through other trades", hence the activity control; a
fade may be a closer or hedger (the CH171 open/close split is E023's, reported here only as a descriptive); crypto series
may dominate parallel re-centerings (family rule).

### 4.3 CB18-R: races (CH179) → LT5 sketch, and the race map

**Hypothesis (one-sided).** Within a market, 6 h taker flow continues **less** when more of its rows were raced (another
taker row in the same market at the same venue second, different `tx_hash`): raced flow is mechanical arbitrage on an
external input, not information. **Direction: β(x6 · zR) < 0.** The opposite sign (races are informed bots) is reported.

**Unit.** Market x trade sample under E016's coverage rule (LT3 §3) with >= 3 signed rows in `[t − 6 h, t)` (as LT4's
E024). **State.** `R` = raced rows / rows in the window; `zR` standardised with the census centre and scale (fixed in
LT5's spec). **Target** `y6 = mid(slot k + 3) − mid_t`; `x6` as E016 (`imb6` over `[t − 6 h, t)`, clipped, scaled).

**Primary.** E016-form expanding-past demeaned OLS of `y6` on `x6 · zR` with controls `x6`, `zR`, `x6 · |mid − 0.5|`,
`x6 · zN`, `zN`, `x6 · zSize`, `x6 · zSPR`, `x6 · zRV`, `x6 · zHTE`, **`x6 · zW` and `x6 · zH`** (E016's and E018's
moderators held fixed, never re-tested), with their main effects. **Gate:** `donor_gate_resid` (donors >= 12 h apart);
failure → p = 1, "within-unit timing not shown". **Floor:** gross 0.5c in the favourable cell (label *material*), and the
census MDE gate 0.0036 per SD. Inference as LT4 §1.7. Labels: *coverage-limited* (truncated > 3%); *block-resolution*
if the census gap histogram shows `ts` quantised at 2 s (then "same second" reads "same block"; disclosed).

**Census and route:** §3.3. **Planning MDE:** as LT4's E024, about 0.0022-0.0046 per SD at 21 days, x 0.87 at 28 days
(0.0019-0.0040), before the measured VIF; census-gated.

**Economics:** maker map only (widen where races are common); no taker route.

**The race map (k = 0, published whatever the route).** From q0504 on worn samples and, if registered, from LT5's
reader: raced share by category, hour, row-count decile, price band; the fingerprint and same-side shares; the
cross-venue pair list overlap **only after 2026-11-03** (the sealed stream's end) and only in LT5's analysis.

### 4.4 CB18-F: the front page as a clock (CH176): census only, with a re-entry rule

**Why no counted test now.** (1) The breakpoint `B` (the category list's default length) and the venue's sort key
("volume" versus an undocumented "trending") cannot be fixed without looking at the venue, which this batch may not do;
round 10 itself made `B` an assumption. (2) Round 10's own arithmetic: about 300-600 crossings in 21 days put the money
target's (members' 24 h outcome-0 mid change, E017's target) MDE at 1.5-2c against a 1.0c floor; only the attention
target (2 h log volume change) is powered, and attention is not a route. (3) Entry/exit labels are mechanically tied to
the volume trajectory (an entry is a surge, E017's object): round 10's entry-minus-exit contrast would mostly re-measure
mean reversion in volume.

**Re-entry rule (declared now).** A counted CH176 test may be registered in a later live-test family only if all hold
before its registration: (a) `B` and the sort key are fixed by a documented, dated observation of the venue's category
pages committed to the repo (an owner action or a separately approved fetch; no price recorded), with the observation's
date before the window; (b) q0505 shows >= 20% of positions in `[B − 10, B + 10]` change hands per pass for that `B`; (c)
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
be complete and present in the window).

**Counts (by sports/non-sports via the sidecar, structure standalone / neg-risk member / other multi, as-of horizon at
the last presence: past end, 0-2 h, 2-24 h, > 24 h, unknown):** (1) exits per day by the last two-sided mid's band
`[0, 0.01)`, `[0.01, 0.05]`, `(0.05, 0.95)`, `[0.95, 0.99]`, `(0.99, 1]`, and "no two-sided quote at last presence" (then the
last two-sided mid within 6 h, within 24 h, or none); (2) the lag from the as-of `end_date` to the exit; (3)
self-consistency: re-appearances after an exit (expected 0; a count above 0 measures listing flicker), and neg-risk
events whose members all exit within 24 h: the number with exactly one member in the upper tail; (4) the number of
middle-band exit ids a light Gamma fetch would need per day (counted, nothing fetched); (5) the window arithmetic: for
CH163, CH164's resolution arm, CH157/E017's carry arm and CH62, the projected number of markets with as-of end inside a
21, 60 and 90-day window whose exit lands in a tail band, by class.

**Forbidden in the map (unit-tested):** any comparison of an earlier price with the last mid (no calibration,
favourite-longshot or drift statistic), any return, any P&L. **Consequence:** the map's days are worn for every
resolution or calibration arm; no counted test may later use `[2026-10-12, 2026-10-16)` for one.

## 5. Jobs (draft specs)

The JSON specs are in `docs/research_lab/queue/drafts/q0500_*.json` .. `q0516_*.json` (status DRAFT in each `notes`).
None is promoted before: the challenger round on this file; part `pre`; census code with unit tests (forbidden fields and
roots, cut-off refusals, pin completeness, exact float writes, the class truth tables); and, for q0500/q0501, the
release tags confirmed against the release list. Window jobs (q0507-q0516) also need parts `common` and `S`, the code
freeze record and the code-against-design freeze check. Priorities: restores 30, censuses 28 (they decide LT5's
membership; ahead of CB batch work, behind registered live tests), window jobs 9 (as CB17).

## 6. Code needed (not written by this document)

- `backend/astrolabe/research_lab/cb18_common.py`: pin-checked readers (captures, sidecars, sweep 1, samples) with
  whitelists and refused roots; exit-75 missing-input handling with the stopped-source record; the arm and thinning
  hashes; the strata-ladder selection; the proxy-SE power gate (SE only); imports by pinned sha256 of LT3 `classify` and
  slot helpers, CB17 `is_sports_sidecar`, LT4 `fl_perm_gate`, `donor_gate_resid` and the CR1 engine.
- `cb18_pre.py`: q0502-q0505 censuses and the routing writer (`seals/cb18_routing.json`); `cb18_map.py`: q0506.
- `cb18_s.py`: the S frame (features, raw target-mid table, statuses), the window census, Stage 1, Stage 2, labels.
- `backend/scripts/run_cb18.py` with subcommands `census-s`, `census-p`, `census-r`, `census-f`, `map-lastmid`, `smoke`,
  `keys`, `frame`, `census-window`, `screen`, `rep`, `stage2-final`, `size-check`.
- Tests `test_cb18_*.py`: forbidden fields (wallets, `chg_*`, outcome fields; `uma_resolution_statuses` reaching anything
  but a byte-equality flag); census cut-offs; pin completeness and missing-pin refusal; exact float round trip; float64
  quotes; the silent/quiet truth table (each field of the equality set; `updated_at` earlier, equal, later, after receipt);
  book-untouched edges (stamp at `t_{k−1}` exactly, outcome-1 missing); burst rule at 20%; thinning independence; the
  fade/follow/none/balanced table; coverage at the page edge; the race definition (same `ts` and same `tx_hash` is not a
  race; three rows in one second); the map's exit rule with a capture gap; the map's forbidden statistics; `None` never
  passes; exit 75 on a missing file; Freedman-Lane gate recovers a planted effect and holds size under label-control
  correlation; the 3-of-200 rule's edges; battery2 kinds.

## 7. Test budget, compute and calendar

| Job | Counted | Kind |
|---|---|---|
| S1 (Stage 1; only if routed RS-1) | 1 | `cb18_test`, `creative_batch_18:S` |
| S1-rep (only if S1 advanced) | <= 1 | `cb18_replication`, `creative_batch_18:S:rep` |
| Pre-censuses, routing, race map, F census, M map, smoke, keys, window census, gates, placebos, size checks, sports arm, secondaries | 0 | `cb18_descriptive` |
| CB18-P, CB18-R (and S under RS-2) | 0 here | counted by LT5 if registered |
| **Total in CB18** | **0-2** | cumulative count recorded at each counting run |

**Compute.** Censuses about 2-3 CPU-hours in all on worn data (two capture days, 23 samples); the map under 1 h; S frames
about 1 h per window; S screen about 1-2 h (200 Freedman-Lane refits). Peak RAM 900 MB (q0512, q0515, alone); every
reader and census < 400 MB. Network: restores only (net lane). Disk <= 0.2 GB of outputs plus transient restore trees.

| By (UTC) | Deliverable | Owner |
|---|---|---|
| 2026-10-21 | challenger round 1 on this file; response | `science-reviewer`, designer |
| 2026-10-22 12:00 | part `pre` committed; census input seal from the release manifests; q0500/q0501 restores; census code and tests | implementer, queue |
| 2026-10-23 | q0502-q0506 run (cpu lane, < 400 MB each) | queue |
| **2026-10-24 12:00** | **routing record** (`seals/cb18_routing.json`, ledger): each idea's route by §3's rules | orchestrator |
| 2026-10-24 → | `LIVE_TESTS_5.md` drafted from the LT5-routed members (§4.2, §4.3, §4.1 under RS-2) | designer |
| **2026-10-25 18:00** | parts `common`, `S` landed (CB route only) = `T18_rules` → **S_18 = 2026-10-27T00:00Z** | orchestrator |
| before 2026-10-27 (preferred), 2026-11-11 08:00 at the latest | S window code, size check, code-against-design freeze check, freeze record, q0507 PASS, q0508 | implementer, `science-reviewer` |
| by about 2026-10-28 | LT5 registration commit (challenger, size check, pins) → **LT5 `REGISTERED_UTC` 2026-10-30T00:00Z** (rule in §1.2) | orchestrator |
| 2026-11-11 08:00 → after E011's analysis commit | q0509 → q0510 → q0511 → q0512 (Stage 1) | queue |
| 2026-11-25 08:00 | q0513 → q0514 → q0515 → q0516 (only if S1 advanced) | queue |
| 2026-11-28 12:00 | LT5 single analysis (if registered) | LT5 |

## 8. Open questions for the challenger

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
## CB18 DRAFT (design only), 2026-10-20 ~19:20Z; nothing frozen, queued, run or counted
- Round 10's remainder after LT4: CH172 (CB18-P), CH175 (CB18-M map), CH176 (CB18-F census), CH177 (CB18-S),
  CH179 (CB18-R + race map). CH178 excluded: a second counted test of E015's hypothesis on overlapping origins before
  E015's analysis (re-entry only as a declared E015 replication after 2026-11-15T12:00Z, disjoint origins).
- Pre-declared counts-only routing (part `pre`, before any census runs): S → CB18 SCREEN_18/REP_18 (RS-1) or LT5 (RS-2)
  or dropped; P → LT5 or dropped (drop expected on power); R → LT5 or dropped (map published); F census only (re-entry
  rule); M map only. Census drops and routes away are uncounted (before the rules bind).
- Counted in CB18: 0-2 (S1; S1-rep if triggered). LT5 members counted by LT5 only.
- Proposed dates: part `pre` 2026-10-22T12Z; routing 2026-10-24T12Z; T18_rules 2026-10-25T18Z → S_18 2026-10-27T00Z;
  SCREEN_18 [10-27, 11-10), REP_18 [11-10, 11-24); LT5 REGISTERED_UTC 2026-10-30T00Z, 28 days, analysis >= 11-28T12Z.
- Queue drafts q0500-q0516 (`queue/drafts/`; argv `scripts/run_cb18.py`, not yet written); q0517-q0519 reserved.
- Branch `feat/cb18` (<commit>). Next: challenger round 1 (science-reviewer) on CREATIVE_BATCH_18.md.
```

## 10. Next actions
1. Challenger round 1 (`science-reviewer`) on this file, with §8's questions; one response; the orchestrator decides.
2. Implementer: part `pre` (after the response), then census code and tests; confirm the release tags for q0500/q0501;
   write `seals/cb18_census_inputs.json` from the release manifests; promote q0500-q0506.
3. Orchestrator: commit the routing record from the census outputs by §3's rules only; draft `LIVE_TESTS_5.md` from the
   LT5-routed members; land parts `common`, `S` by 2026-10-25T18:00Z if CB18-S routes to the batch.
