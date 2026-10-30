# Creative batch 6 (CB6): ex-ante longshot tail classifier, neg-risk conversion dumps, reward-shadow discontinuity at 0.90, fill-probability measurement

`evidence_role: exploratory_historical` (CH60 screen and holdout on the fresh `h8_tail` fetch) / `exploratory_dev` (CH66,
CH71, CH77 dev windows on live-period data) / `prospective` (CH66 and CH71 replications, CH77 evaluation; data after the
freeze) | status: **REVISED after challenger round 1; not frozen.** Last updated 2026-10-17 00:56 UTC+1
(2026-10-16T23:56Z). The round-1 items and the change made for each are in §10; this revision only tightens or discloses.

This file turns CH60, CH66, CH71 and CH77 from `CREATIVE_HYPOTHESES_2026-10-17.md` into declared, falsifiable tests. It
follows `CREATIVE_BATCH_1.md` (CB1), `CREATIVE_BATCH_4.md` (CB4) and the **revised** `CREATIVE_BATCH_5.md` (CB5) in
structure and rules, and it is written to avoid, up front, every failure mode CB5's challenger found (§9):
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim. AREPO never
  trades. Every P&L is a paper rule at modelled or recorded prices.
- CB6 has **two kinds of work, counted separately** (§2.5):
  - **Routes** (CH60 `T`, CH66 `N`, CH71 `R`): screen (Stage 1), frozen replication (Stage 2), then a separate
    prospective registration (Stage P) and an economic check at recorded prices.
  - **Measurement** (CH77 `C`): a capacity fact for every maker envelope. No money route; never read as edge.
- Test tables bind only once the CB6 declaration hash is committed (`model_specs/cb6_v1.json`, the CB6 freeze). The one
  exception is the `h8_tail` fetch and its rules file (§1.4), which are fixed by this document so that the fetch can run
  before `T_seal`, before any CB6 analysis code exists.
- Queue specs (§5) are drafts. None is committed to `queue/jobs/` by this document.
- **Where CB6 says "as CB1 §x", "as CB3 §x", "as CB4 §x" or "as CB5 §x"**, that rule applies unchanged, including its
  challenger-round and freeze-check fixes.
- **Queue numbering.** CB6 uses **q0120-q0134, one id per job, no letter suffixes** (§0.1); q0135-q0139 are reserved for
  CB6 renumbering in a challenger round and are never used for anything else. q0101-q0114 are CB5's; q0110 and q0111
  are also taken by MC1 (`q0110_mc1_dev_dryrun` is committed). No CB6 id shares a numeric prefix with any committed or
  drafted spec (checked against `queue/jobs/` and `queue/drafts/` at drafting).

## 0. Summary, selection and ranking

| Rank | Job | Hypothesis | Tests (counted) | Screen / dev data | Replication data | Queue ids | CPU-h | Peak RAM |
|---|---|---|---|---|---|---|---|---|
| 1 | **CB6-F** data | `h8_tail` fetch + seal (**before `T_seal`**); extractor v5 tables `band/`, `printflag/`; conversion probe and fetches; `cb6_followup/` pass step (R2 only) | none | n/a | n/a | q0120, q0121, q0122, q0123, q0124, q0131 | 2 + about 3.5 h network wall before `T_seal` | 1.2 GB |
| 2 | **CB6-T** ex-ante tail classifier (CH60) | longshots in an ex-ante flagged class (discrete-decision rule text, or a week of upward drift, or a large buy by a young wallet) resolve YES more often than priced, relative to unflagged longshots (T1); a paper longshot ask in the unflagged class, held to resolution, pays (T2) | T1 (mechanism), T2 (economic) | `h8_tail` SCREEN block | `h8_tail` HOLDOUT block (sealed, never read before Stage 1 is final) | q0126, q0130 | 1.0 | 1.2 GB |
| 3 | **CB6-N** neg-risk conversion dumps (CH66) | a converter's sells of unwanted YES tokens revert more than ordinary same-size sells on the same member (N1); a paper bid posted 60 s after the conversion on every received member, one tick above the last bid-side print before it, exited by a taker 2h later, pays (N2) | N1 (mechanism), N2 (economic) | conversions (Polygon logs) and Data API prints in the dev window | the same in `[T6_rep_start, T6_rep_start + 21 d)` | q0123, q0124, q0127, q0131, q0132 | 0.8 | 1.0 GB |
| 4 | **CB6-R** reward-shadow discontinuity (CH71) | the quoted spread jumps at the folded mid 0.90 in rewarded markets (R1, donut RD, two-sided at Stage 1); a touch maker in the folded band [0.90, 0.96) is net-positive (R2, single stage on post-freeze data, follow-up fills; unreplicated) | R1 (mechanism); R2 (economic, Stage 2 directly) | `cb6_extract/band/` dev captures | `band/` + `cb6_followup/` in `[T6_rep_start, T6_rep_start + 21 d)` | q0122, q0128, q0133 | 0.8 | 1.5 GB |
| 5 | **CB6-C** where the fills are (CH77), measurement | public capture fields beyond volume and liquidity improve the out-of-sample prediction of "≥ 1 print in the next 2h" (M1) | M1 (measurement) | `cb6_extract/printflag/` dev passes (fit only, no test) | frozen model evaluated on `[T6_rep_start, T6_rep_start + 14 d)` | q0122, q0129, q0134 | 0.5 | 1.5 GB |

The pre-freeze census q0125 is shared by T, N, R and C.

**Why this order.**
- **`h8_tail` is the only CB6 job with a hard calendar deadline.** As CB4 §1.3: every historical row is capped at
  `min(T_fetch8, T_seal)` and the fetch must be **complete before `T_seal` = 2026-10-22T00:00Z**, otherwise it is
  `not_run_deadline` (no seal, no analysis, no refetch, the cap is not moved; T1 and T2 recorded "not run (deadline)",
  p = 1, counted). Its spec (q0120) has no dependency on any CB6 analysis code or on the CB6 freeze. It can be committed
  as soon as (a) the fetcher code passes a `science-reviewer` freeze check, (b) `seals/cb6_tail_rules.json` (§1.4) is
  committed, and (c) the §2.8 headroom precondition holds. It goes on the `net` lane at priority 61 in **90-minute
  chunks**, so the T_seal-bound jobs already queued at 61 with lower ids (q0043 h6, q0081/q0082 h7) win the lane at
  every chunk boundary (the worker breaks priority ties by ascending id, `queue_worker.py:326`). Round 1 adds two
  preconditions before the q0120 commit: (d) every exclusion file exists and matches the sha256 pinned in the rules file
  (§1.4), and (e) the fidelity-60 price smoke test passes (§CB6-F). q0120 may be queued before the CB6 freeze.
- The extractor v5 tables come next. `printflag/` is calendar-bound: raw trade samples are deleted after 3 days
  (`data_catalogue/RETENTION.md`), so the pass step should be live soon; older passes come from verified release copies
  where they exist (missing stays missing). `band/` reads captures, which are not yet deletable (snapshot rule gated);
  release streaming covers any later loss (CB4 §2.10 machinery). CB6 places **no new gate on retention**.
- CB6-N and CB6-C need nothing before `T_seal`: Polygon logs and Data API prints are permanent public records, and
  trade-sample print flags are extracted per pass. Their dev data are fetched after `T6_dev_end`.

### 0.1 Queue id mapping (one id per job)

| Id | Job | Family | Earliest commit |
|---|---|---|---|
| q0120 | `h8_tail_fetch` (fresh historical fetch, `T_seal`-bound) | F (for T) | after the fetcher freeze check, the smoke test and `seals/cb6_tail_rules.json` with pinned exclusion hashes |
| q0121 | `h8_tail_seal` (listing hash, event-level disjointness re-check, h7-overlap drop list, SCREEN/HOLDOUT split) | F (for T) | after q0120 completes |
| q0122 | `cb6_extract_backfill` (extractor v5: `band/`, `printflag/`) | F (for R, C) | after the extractor freeze check |
| q0123 | `cb6_conv_probe` (chain-source probe, 20 conversions, no prints analysed) | F (for N) | after the probe code exists |
| q0124 | `cb6_conv_dev_fetch` (dev-window conversions + member prints) | F (for N) | after `T6_dev_end` + 3 h and q0123 PASS |
| q0125 | `cb6_census` (T on SCREEN only; N, R, C dev; counts and gates) | shared | after q0121, q0122, q0124 |
| q0126 | `cb6_screen_T` (Stage 1, SCREEN block) | T | after the CB6 freeze |
| q0127 | `cb6_screen_N` (Stage 1, dev) | N | after the CB6 freeze |
| q0128 | `cb6_screen_R` (Stage 1, R1 on dev captures) | R | after the CB6 freeze |
| q0129 | `cb6_fit_C` (fit the declared model on dev passes; writes the frozen coefficients) | C | after the CB6 freeze, before `T6_rep_start` |
| q0130 | `cb6_holdout_T` (Stage 2 on the HOLDOUT block) | T | only if T1 advanced or T2 was carried |
| q0131 | `cb6_conv_rep_fetch` (rolling, replication window) | F (for N) | only if N1 or N2 advanced or was carried |
| q0132 | `cb6_rep_N` (Stage 2) | N | after `T6_N_rep_end` + 3 h |
| q0133 | `cb6_rep_R` (Stage 2: R1 replication + R2) | R | only if R1 advanced; after `T6_R_rep_end` + 12 h |
| q0134 | `cb6_eval_C` (M1 on the evaluation window) | C | after `T6_C_eval_end` + 3 h |

### 0.2 Selection and scope

No census was run for this draft. **No CB6 quantity has been computed, and the drafting session read no price, book,
trade, outcome, chain log or rule text.** It read committed documents and code only, ran
`battery2.cumulative_count()` (§2.5), and fetched one public documentation page (Polymarket liquidity rewards, §0.3).
Every count below comes from a committed document or is stated as an assumption that the census replaces.

| Idea | Decision | Reason |
|---|---|---|
| **CH60** tail classifier | **include (T)** | The CB1 C1 screen (224 filled orders, 62 events, -3.84c, 7 losing clusters) shows a tail-loss structure. The question is whether the tail is identifiable *ex ante*. h2 is worn and h5 is CB1's sealed set, so the test needs a fresh fetch, disjoint from both at market **and event** level (§1.3), capped at `T_seal`. Features are fixed now (§CB6-T), before any fetch. C1's five worst events: identities not recorded anywhere (§1.3) |
| **CH66** conversion dumps | **include (N)** | Novelty 5. Conversion is atomic and public on chain (`PositionsConverted` on the neg-risk adapter, to be verified by probe q0123), so the episode list does not depend on AREPO's 2,000-market trade sample (which almost never holds 3 members of one event at once). Data API `/trades?market=<comma-separated condition ids>&start&end` returns all members of an event in one windowed request (`large_trade_census.py:40`) |
| **CH71** reward shadow | **include (R), mechanism corrected (§0.3)** | The idea text reads the rewards rule backwards. The documented rule still changes exactly at 0.90 (single-sided quotes stop scoring), so a regression discontinuity is identified. Non-rewarded markets at the same cutoff give a placebo that can fail. Kept rather than swapped (below) |
| **CH77** fill probability | **include (C), measurement** | It reprices every maker envelope (C1 fill rate 6.8%). It uses capture fields and per-pass trade samples, with a very large n. The informative question is *incremental* predictability beyond volume and liquidity, because "volume predicts prints" cannot fail |
| CH67 sibling-resolution unwind | not in CB6 (concrete reason) | Its primary (sum of member asks after a `closed` flip, from captures) is a near-copy of CB1-D's sealed neg-risk sum statistic inside CB1-D's replication window (to 2026-11-09). As with CB5-L (round-1 item 11), it would have to be held until CB1-D's read, so it gains nothing by being in CB6 now |
| CH73 Kalshi-skewed maker | not in CB6 | It runs on the C1 cross-venue set, already analysed by v1, r1 and CB5-K. Its only clean check is E009's stream after 2026-11-03 with owner sign-off. Better as a follow-up to CB5-K |
| CH63 specificity discount | not in CB6 | It needs a second fresh pre-`T_seal` fetch (`h8_text`, about 6,000 markets), competing with `h8_tail` and the h7 jobs for the congested `net` lane and the last 0.3 GB of disk headroom (§2.8). `h8_tail` is reserved for CB6-T and cannot be reused for CH63 |
| CH61, CH62, CH64, CH65, CH68-CH70, CH72, CH74-CH76, CH78 | not in CB6 | ranks below 8, or each needs its own source join or fetch; CH61/CH62 depend on CH60's classifier existing first |

**Sports and weather.** Category scope is the user's decision (`CB6_SPORTS_IN_PRIMARY = false`). Sports is a reported,
uncounted stratum in every CB6 test. Weather (`fee_category == "weather"` or CB2's `TEMP_RE`) is excluded from every CB6
population and from the `h8_tail` sample, so CB6 never touches CB2-W's live stage or `h6_weather`.

### 0.3 CH71's mechanism, checked against the venue documentation

`CREATIVE_HYPOTHESES_2026-10-17.md` CH71 says rewards "require two-sided quotes inside [0.10, 0.90]" and that reward
quoters disappear above 0.90. The liquidity-rewards page (https://docs.polymarket.com/developers/market-makers/liquidity-rewards,
fetched 2026-10-16T23:3xZ) says the reverse:
- midpoint in [0.10, 0.90]: "single-sided liquidity can score", `Q_min = max(min(Q_one, Q_two), max(Q_one/c, Q_two/c))`,
  with c = 3.0 on all markets;
- midpoint in [0, 0.10) or (0.90, 1.0]: "liquidity must be double-sided to score", `Q_min = min(Q_one, Q_two)`;
- each incentivised market sets a max spread `v` and a minimum size.

**So rewards do not stop at 0.90. Single-sided scoring stops there.** A quoter who rests on one side only is paid at
1/3 rate below 0.90 and nothing above it. A two-sided quoter is paid on both sides of the cutoff. The quoted spread can
therefore jump in either direction at 0.90: wider if one-sided reward quoters leave, narrower if they switch to two-sided
quotes. The discontinuity is identified by a venue constant; **its sign is not predicted.** CB6-R therefore tests R1
two-sided at Stage 1 and replicates in the Stage-1 direction. The money route (a maker above 0.90 faces less reward
competition) survives only if R1's sign is "wider above". The route test R2 is registered (single stage, post-freeze data) only in that case
(§CB6-R). The cutoff belongs to the inside region: x = 0.90 exactly is "below" (one-sided scoring allowed).

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Prior use | Role in CB6 | Evidence ceiling |
|---|---|---|---|
| `history/h8_tail` (**new**, q0120; seeded sample of about 4,500 binary markets created 2025-09-01..2026-07-31 with scheduled `end_at ≤ T_fetch8 − 7 d`, disjoint from h1/h2/h3/h5/h5_ladders by market id **and** by Gamma event id, `negRiskMarketID` and series (h7 at seal), weather excluded; Gamma frame **with `description`, event id, `negRiskMarketID`, series ids**; hourly prices around ≤ 3 declared origins per market; windowed taker prints; first-trade times of large buyers (hashed); outcomes only in `outcomes_guarded.csv.gz`) | none | **CB6-T only.** Split once at seal (q0121) by event-hash into SCREEN (Stage 1) and HOLDOUT (Stage 2, sealed) | L1 (SCREEN) / L2-dev (HOLDOUT, same calendar) |
| Polygon logs of the neg-risk adapter's conversion event (**new**, q0123/q0124/q0131; keyless public RPC; logs from `T6_dev_start − 96 h`, so every control wallet can be checked for conversions in its whole print window) | none | **CB6-N episode list** (block time, hashed stakeholder, neg-risk market id, index set, amount) | as below |
| Data API windowed taker prints for converted events' members (**new**, q0124/q0131; `takerOnly=true`) | none | **CB6-N targets, controls and fills.** One window `[t_conv − 96 h, t_conv + 3 h]` per conversion with ≥ 1 received member, all members in one comma-separated `market=` list (paged, ≤ 10 pages; a window that hits the cap makes every unit of that conversion unavailable) | L1 (dev) / L2-dev (rep) |
| Gamma market metadata for converted events (q0124/q0131) | none | member list, `negRiskMarketID`, `fee_category`, tick size, `outcomes` labels. **No outcome fields** (parse guard drops `outcomePrices`, `umaResolutionStatus`) | - |
| `cb6_extract/band/` (**new**, extractor v5, §4.3) | none | **CB6-R.** Per complete capture, binary rows with folded mid in [0.55, 0.99]: touch, rewards fields from the sidecar, first-sweep sizes and 1c/5c depth, ids for clustering | L1 (dev) / L2-dev (rep) |
| `cb6_extract/printflag/` (**new**, extractor v5, §4.3) | none | **CB6-C.** Per pass i and per market in the pass-i trade sample: inclusion probability, the print indicator over `[r_{i−1}, r_{i−1} + 2 h)` and its availability, plus the capture-(i−1) feature row | fit (dev) / measurement (eval) |
| `cb6_followup/` (**new**, pass step, R2 only, §4.4) | none | **CB6-R2 fills.** At pass i+1, windowed taker prints `(t, t + 2 h]` for a seeded sample of ≤ 200 band markets swept at pass i | L1 (single stage, unreplicated) |
| Raw complete captures, `rows_ext` sidecar, book sweeps, trade samples (host; verified release copies) | E-series, SB2, CB1-CB5 | read only by the extractor (`band`, `printflag`) and the follow-up step | - |
| `h2_main`, `h3_power` | many; h2 worn beyond budget, h3 retired from replication (Ledger M3) | **not read** (runner refuses) | - |
| `h4_seal`, `h5_cb1`, `h5_cb1_ladders`, `h6_weather`, `h7_cb4_era`, `h7_cb4_series` | SB2, CB1, CB2-W, CB4 | **not read** (runner refuses the run ids). Only committed seal copies under `docs/research_lab/seals/` (h5, h5_ladders, and h7 once committed) are read, for **market ids only** (exclusion and the drop list) | - |
| `cb1_extract/` .. `cb5_extract/`, `cb3_followup/` | CB1-CB5 inputs | **not read by any CB6 code path** | - |
| `cross_venue_live/` (E009/E010), `surprise_live/` (E011), live trade monitor alerts | registered experiments | **not read** | - |

### 1.2 Dates (declared; UTC)

| Name | Value | Meaning |
|---|---|---|
| `T6_draft` | 2026-10-16T23:37Z | First draft. No CB6 quantity computed |
| `T_seal` | 2026-10-22T00:00Z | SB2's h4 seal boundary (CB1 §1.3, CB4 §1.2). `h8_tail` rows are capped at `min(T_fetch8, T_seal)` and **the fetch must be complete before `T_seal`** (no new chunk at or after it); otherwise `not_run_deadline` |
| `T_fetch8` | request clock of the `h8_tail` frame fetch, pinned in its manifest (expected 2026-10-17..21) | h8 data end; administrative censoring `T_censor8 = T_fetch8`; frame completeness `end_at ≤ T_fetch8 − 7 d` |
| `T6_dev_start` | 2026-10-11T12:00Z | First sidecar capture (as CB1-CB5). Start of the N, R and C dev windows |
| `J4-R window` | `[t_j4r_start, t_j4r_end)` from the committed `seals/j4r_window.json` (2026-10-16T00:00Z to 2026-10-21T00:00Z, end can only move forward) | **No CB6 analysis or census uses a capture, sweep, trade-sample pass, conversion or print timed inside it** (as CB3 §1.2). The extractor still writes rows for it (data copying only) |
| `T6_dev_end` | **2026-10-28T00:00Z** | N, R and C dev windows: `[T6_dev_start, t_j4r_start) ∪ [t_j4r_end, T6_dev_end)` (about 4.5 + 7 days, about 138 complete captures, about 46 six-hour blocks but only about 12 UTC dates, which is why R and C cluster time by 6-hour block, §2.3) |
| `T6_rep_start` | **max(2026-10-30T00:00Z, first complete capture ≥ CB6 freeze commit + 2 h, first pass ≥ 48 h after the `cb6_followup/` step is deployed)**, pinned in a committed file (CB1 freeze-fix 9) | Start of the N and R replication windows and of the C evaluation window |
| `T6_R_rep_end`, `T6_N_rep_end` | `T6_rep_start` + 21 d | End of the R and N replication windows |
| `T6_C_eval_end` | `T6_rep_start` + 14 d | End of the C evaluation window |
| `T6_mark_lag` | 12 h | No R or N window is analysed until its last origin + 12 h |
| `T6_T2_register_deadline` | **2026-11-21T00:00Z** (just after the expected `T6_R_rep_end`) | If `model_specs/cost_regimes_v1.json` is not committed by then, T2 is recorded "not run (register missing)", p = 1, counted, and the Stage-2 Holm k is fixed without it |

### 1.3 Sealed and untouched data (named)

- **Refused run ids and roots.** `run_cb6.py` refuses `h2_main`, `h3_power`, `h4_seal`, `h5_cb1`, `h5_cb1_ladders`,
  `h6_weather`, `h7_cb4_era`, `h7_cb4_series`, every path under `cb1_extract/` to `cb5_extract/`, `cb3_followup/`,
  `cross_venue_live/` and `surprise_live/`.
- **SEALED-H8 (CB6-T).**
  - `h8_tail` is fetched and sealed (manifest, per-file sha256, listing sha256) **before any CB6-T analysis**. The seal
    copy `docs/research_lab/seals/h8_tail_SEAL.json` is committed before q0125 is committed.
  - **SCREEN/HOLDOUT split at seal.** Every market gets `block = SCREEN` if `sha256("arepo-cb6-tail-split|" +
    event_key)` is even in its first byte, else `HOLDOUT`, where `event_key` is the Gamma event id (market id if none),
    merged across `negRiskMarketID` (all members of one neg-risk event share a block). The split file (ids only) is
    hashed into the seal. The runner refuses to open any HOLDOUT file until Stage 1 of CB6-T is final and committed
    and T1 advanced or T2 was carried. Every h8 reader verifies the listing hash and appends to
    `history/h8_tail/ACCESS_LOG.jsonl` (as CB1 SEALED-H5).
  - **Why an event-hash split, not a time split.** CB4-S split its series store by roll date. Here the features are
    fixed before any fetch, so nothing is tuned on SCREEN that a time split would protect against. A creation-date split
    would put most censored (still unresolved) markets in the later block and make the blocks unequal in their censoring.
    The cost is stated: **HOLDOUT is market-disjoint but shares the calendar**, so a Stage-2 pass is "development-
    replicated, same calendar (L2-dev)". Out-of-time evidence comes only from Stage P (§2.10).
  - **Event-level disjointness from h1/h2/h3/h5/h5_ladders (round 1, item 5).** Market-id disjointness is not enough:
    h2's 270-day lookback (`CASE_STUDY_MADURO.md` Part B) overlaps h8's creation window, so sibling markets of C1's 62
    events (including its five worst) could enter h8 and share their outcomes. The fetcher builds an **exclusion key
    set** = every Gamma event id, `negRiskMarketID` and series id of every market in the exclusion files (h1_first,
    h2_main, h3_power `sample.csv.gz`; the h5 and h5_ladders seal copies), looked up by market id from Gamma metadata
    (parse guard keeps id, event ids, `negRiskMarketID`, series ids only; no outcome or price field), written to
    `exclusion_keys.csv.gz` and hashed into the manifest. **Any frame market sharing any key with the set is removed
    before sampling** and counted by key type. If more than 2% of exclusion market ids return no metadata, disjointness
    is "unverified" and T1/T2 are "not testable (disjointness unverified)", p = 1, counted (an unverified gate never
    counts as met). q0121 re-checks every sealed h8 market against the stored key set and drops any residual match
    (counted; expected 0).
  - **h7 overlap.** The h8 and h7 fetches are independent (as CB4's two h7 fetches). At seal (q0121) any h8 market whose
    id appears in a committed h7 seal copy, **or that shares an event id, `negRiskMarketID` or series id with such a
    market** (Gamma lookup by id, same parse guard), is dropped from both blocks, never read and counted. If an h7 run ended
    `not_run_deadline`, there is nothing to drop. q0121 waits until both h7 runs are terminal (sealed or
    `not_run_deadline`); the h8 *fetch* does not wait for h7.
  - **h4_seal unchanged.** h8 holds no information after `T_fetch8 < T_seal`; SEALED-H4 analyses use origins ≥ `T_seal`.
    No frozen SB2 parameter changes.
- **Live-period windows (N, R, C).** Their dev and replication windows lie partly after `T_seal`. They use CB6's own
  extract tables and post-hoc API and chain reads of CB6-selected markets, never h4 data (as CB4-C and CB5, disclosed).
- **SEALED-P overlaps (disclosed).** The N/R/C windows overlap CB1-D's replication window (to 2026-11-09), CB3's
  prospective windows (from `T3_rep_start` ≥ 2026-10-27), CB4-C's and CB5-L's live windows, and E011's window (to
  2026-11-10). The calendar is shared; populations, statistics and output tables differ, and **no CB6 job reads their
  extract tables, follow-up files or outputs**. CB6-N reads prints of neg-risk event members; it never computes a member
  ask or bid sum (CB1-D's statistic). CB6-R's comparison band [0.84, 0.90) overlaps CB3-B's population ([0.10, 0.90]) in
  calendar time; CB6's follow-up sample is seeded independently of CB3's.
- **Overlap with registered experiments.** E009/E010 (cross-venue) and E011 (surprise detector) inputs and outputs are
  never opened. CB6 statistics (tail-class resolution excess on h8, conversion reversal, spread discontinuity, print
  probability) cannot be computed from, or reveal, E009-E011 outcomes. CB6 results on captures inside E011's window are
  aggregates and contain no per-market E011 alert information.
- **CB1-C overlap (CH60) and what is known about C1's five worst events (round 1, item 6).** CB6-T never opens CB1-C's
  unit lists, and h8 is disjoint from h2 and h5 by market id and by event, neg-risk and series key (above).
  - **Who has seen the five worst events.** Checked 2026-10-17 by grep of the repository (docs, code, `trials.jsonl`)
    and by listing the key paths, **without reading values**, of the only C1 results files
    (`creative_batch1/history/h2_main/{results_cb1_C.json,census.json}` on the host): no committed document, code
    output or results file names, or stores an identifier of, any C1 event. `cb1_history.evaluate_c` and
    `census_counts` persist counts, p values and means only; `cb1_structural._top_drop` forms the top-5 drop set in
    memory and discards it. `CREATIVE_BATCH_1.md` reports only the without-top-5 sensitivity (+4.6c). **No record shows
    that any session viewed their identities.** It cannot be excluded that a session printed the in-memory order frame
    interactively; nothing logs that. The CH60 headline sentence "C1's five worst events are concentrated in [the
    discrete-decision / drift / young-wallet class]" (`CREATIVE_HYPOTHESES_2026-10-17.md`, CH60) is therefore a
    **conjecture of the hypothesis author, not an observation**; CB6 treats it as the hypothesis to test, never as
    evidence. Anyone can recover the identities by re-running the CB1 C code on h2; doing so before CB6-T's Stage 2 is
    final is forbidden by this document.
  - **The design is not "CH60 without change of substance" (the draft's claim was false).** Changes from the CH60 text,
    all made before any h8 data exist and none chosen from C1's events: (1) primary changed from a logistic regression
    with four feature coefficients (odds ratios) to a single band-weighted flagged-minus-unflagged difference Δ for the
    disjunction F (the logistic is now robustness (vii)); (2) origins changed from "6h origins in a resolved market's
    last 60 days, selected because a leg was in [0.02, 0.10]" to an unselected weekly Monday grid `≤ T_fetch8 − 60 d`,
    with the price band applied only as an eligibility rule at each origin; (3) the frame is no longer "resolved
    markets" but scheduled `end_at ≤ T_fetch8 − 7 d` (round-1 item 4); (4) 10-minute prices became hourly (fidelity
    60); (5) the drift feature got a threshold (+0.01 over 7 days) that CH60 did not state; (6) feature (iii)'s median
    gained its window (30 d) and minimum (10 prints); (7) the regex word lists gained inflections and a description
    fallback; (8) the clarification marker list was operationalised. These are disclosed as design changes, not as
    operational details.
- **Results outside data directories.** Every CB6 result goes to `research_lab/creative_batch6/`. Nothing is written
  inside `history/h8_tail/` after the seal except `ACCESS_LOG.jsonl`.

### 1.4 The `h8_tail` rules file (committed before q0120)

`docs/research_lab/seals/cb6_tail_rules.json` holds, with a top-level `rules_sha256`, everything the fetch or the
CB6-T analysis needs that could otherwise be chosen after seeing data:
- the frame windows, sampling seed (`arepo-h8-tail`), strata and weights, exclusion run ids and seal copies (§CB6-F);
- **the path and sha256 of every exclusion file** (h1_first, h2_main, h3_power `sample.csv.gz`; `seals/h5_cb1_SEAL.json`;
  `seals/h5_cb1_ladders_SEAL.json`), the event-level exclusion rule (key types, the 2% unverified threshold) and the
  smoke-test rule (§CB6-F);
- the origin rule and its seed (`arepo-h8-tail-origins`);
- the class regexes, the clarification-marker list and the tie rules (feature (i));
- the drift, large-buy and wallet-age thresholds (features (ii)-(iv));
- the split seed (`arepo-cb6-tail-split`).
The fetcher refuses to start unless the committed file's hash equals the code's **and every exclusion file exists and
matches its pinned sha256** (a missing or changed exclusion file is a refusal, exit 2, never a silent skip: a skipped
file would let worn markets into h8). **No regex or threshold is computed from, or revised after, any h8 read.** Every
threshold the fetch or CB6-T uses is in the file before q0120 is committed.

## 2. Common rules (deltas from CB1 §2, CB3 §2, CB4 §2 and CB5 §2)

### 2.1 Costs

As CB5 §2.1, read through **`cost_regimes.cost_regime(date, fee_category, price)`** (version `cost-regimes-v1`): taker
`fee_rate` per leg as `r·a·(1 − a)` never below the CB1 conservative rate; `half_spread` from the CB1 band table
(`cb1_history.HALF_SPREAD`: 2.05c below 0.05, 1.5c in [0.05, 0.20), 1.1c in [0.20, 0.80), 1.5c in [0.80, 0.95),
1.25c above), never lower; `a_as_cents` (R2) on maker fills before the category's rollout date. Category rates follow
`economics.DOCS_CATEGORY_RATE` (crypto 0.07; sports, economics, culture, other 0.05; finance, politics, mentions, tech
0.04; geopolitics 0).

| Item | Rule |
|---|---|
| Maker fee | 0 everywhere |
| Maker rebate | per filled share `ρ_cat · r_cat · P(1 − P)` with `economics.REBATE_SHARE` (crypto 0.20, sports 0.15, geopolitics 0, all others 0.25); unknown category → 0. **Every economic floor and sign must also hold with the rebate halved (binding, as CB3 §2.1 item 6).** Liquidity rewards never enter `net` |
| T2 (paper ask, held to resolution) | modelled ask `a_c = min(m_c + half_spread(m_c), 0.999)` on the longshot side; `net = a_c − Y_c − a_AS` per filled share; no fee (maker); rebate as above (tiny at these prices). **CB6-T's T2 refuses to run until `model_specs/cost_regimes_v1.json` is committed** (as CB5-G), because most h8 origins predate the 2026-03-30 rollout and the absent-register default sets `a_AS = 0` |
| N2 (maker bid, taker exit) | entry bid `q` (§CB6-N); exit by a taker sell at the exit-window bid-side VWAP `x`; `net = x − q − f(x) + rebate(q)`, `f(x) = r·x·(1 − x)` with `r = cost_regime(exit date, fee_category).fee_rate` |
| R2 (touch maker) | `net = mark-out + rebate(q)`; no exit fee (mark-to-mid, as CB3-B) |
| Binding cost robustness | +0.75c on every bought or exit leg (T2: on `a_c`, i.e. the ask lowered by 0.75c; N2: on `x`; R2: on the mark) keeps net > 0 |
| Measurement (C) | no P&L |

### 2.2 Clocks

As CB1 §2.2 and CB5 §2.2. In particular:
- A history price point stamped `s` is usable at `t` iff `s + 600 ≤ t` and it is at most 2h old (h8 points are hourly,
  so "at most 2h old" means one of the two latest points).
- Prints use the Data API venue `ts`. A condition at `t` uses prints with `ts < t`. Truncation rule as CB1 §2.2: a print
  condition is known true, unavailable or false. Unavailable units are excluded and counted, and enter the declared
  worst case.
- Capture rows use the row's own `received_utc` as their time (as E011), never the capture start.
- Chain events use the block timestamp. Conversions are joined to prints by time only; a Data API print and a chain
  event in the same second are ordered by the chain event first (a dump cannot precede its conversion).
- `closed_time` and Gamma `closedTime` are never a population condition or a window anchor. "Open at t" means the
  market has a usable price point at t and no resolution before t on the market's own price path is detectable.
- **Scoped exception (smoke v2 only; science-reviewer, 2026-10-17).** The smoke v2 pool (q0136) alone uses the worn
  exclusion-sample column `close_epoch`, as the condition `close_epoch ≥ end − 2 d`, so that the smoke window lies
  inside the market's life. It is never used in the h8 frame, the sample, the origins or any CB6-T analysis. It dropped
  **1** market from the smoke pool (573 → 33; the other 539 were dropped by the life ≥ 14 d rule).

### 2.3 Uncertainty and decision rule

As CB5 §2.3, unchanged:
- Unweighted estimates are primary. One-sided p (routes; R1 two-sided at Stage 1) = the max over the declared cluster
  ways of CR1 (normal z). CI by a 2,000-draw cluster bootstrap (seed 616).
- **Small-G rule** (CB2 §2.3): G ≥ 30 CR1 normal; 15 ≤ G < 30 CR2 with t(G − 1) and a Webb wild-cluster bootstrap (9,999
  draws), larger p; G < 15 in any way → "not testable", p = 1, counted.
- Testability otherwise: ≥ 100 units and ≥ 30 clusters in each declared way, else "not testable" (p = 1, counted).
- **Time clustering for R and C (round 1, item 2).** The draft's "capture UTC date" way had about 12 clusters in the R
  dev window and 14 in the C evaluation window, so R1 and M1 were untestable by the rules above. The time way for R1,
  R2 and M1, at every stage, is the **6-hour UTC block** (00, 06, 12, 18 UTC, the cohort cadence): about 46 blocks in
  the dev window, 84 in a 21-day replication window and 56 in the 14-day evaluation window, all ≥ 30. *Why 6 hours,
  considering dependence:* captures are about 2 h apart and resting quotes persist across adjacent captures, so a
  per-capture way (about 138 clusters) would treat strongly dependent neighbours as independent; a 6-hour block holds
  about 3 consecutive captures and absorbs that persistence. The windows were not lengthened because that would delay
  the freeze and the evaluation without addressing within-day dependence. **Binding dependence check:** because
  adjacent blocks can still be correlated, the test must also meet its p threshold with **12-hour blocks** under the
  small-G rule (about 23 blocks in the dev window and 28 in the evaluation window → CR2 with t(G − 1) and the Webb wild
  bootstrap; G < 15 → fails). The fixture-day group way is unchanged. p = the max over fixture-day group and 6-hour
  block; the 12-hour check is an additional condition, never a substitute.
- **Routes.**
  - **Stage 1:** advance iff p < 0.01 (one-sided; R1 two-sided), the §2.4 floor is met, `R_ann` ≥ 10% where defined,
    the calibration placebo holds (§2.6), the binding robustness holds, and every binding gate is **met** (an
    "unknown", "unverified" or "inconclusive" gate never counts as met). A BY label (q = 0.10 over
    `battery2.cumulative_count()`) is attached as triage only.
  - **Carry rule for economic tests (as CB5 §2.3, declared now).** If the mechanism test of a family advances and its
    economic test is "not testable" at Stage 1 **for size only** (filled units < 100 or fill clusters < 30) with a point
    estimate ≥ 0, the economic test enters Stage 2 as "carried, untested at Stage 1" and is counted in the Stage-2 Holm
    k. A testable economic test that failed is not carried. (Applies to T2 and N2. R2 has no Stage 1, §CB6-R.)
  - **Stage 2:** Holm at α = 0.05 one-sided over **all CB6 route tests reaching Stage 2** (T1, T2, N1, N2, R1, R2;
    k ≤ 6), each in its Stage-1 direction (R1: the sign found at Stage 1). Early finishers are reported against α/k with
    k fixed when the last Stage 1 ends; the batch Holm can only add passes. A pass is "development-replicated
    (L2-dev)", never confirmation (§2.10). **Exception: R2 has no Stage 1**, so an R2 pass is labelled "single-stage
    result on post-freeze data, unreplicated (L1)", never L2-dev; it still counts in the Holm k.
- **Measurement (M1).** Family **C** = {M1}, single stage on the evaluation window, one-sided α = 0.05 (k = 1).
  Reported as "unreplicated measurement".

### 2.4 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate |
|---|---|---|
| T1 | mechanism | `Δ ≥ +2.0c` (flagged minus unflagged resolution excess; at a 5c mean price this is a 40% relative difference in the YES rate) |
| T2 | economic | net ≥ +0.5c per filled share (C1's floor), `R_ann ≥ 10%`, the CB1 tail gate (§CB6-T) |
| N1 | mechanism | `Δ_N ≥ +0.3c` (dump recovery minus matched-sell recovery) |
| N2 | economic | net ≥ +0.25c per filled share (CB3-B floor) and EV per posted opportunity > 0 |
| R1 | mechanism | `|τ| ≥ 0.3c` (donut spread discontinuity, §CB6-R) |
| R2 | economic | net ≥ +0.25c per filled share and EV per quote > 0 |
| M1 | measurement | `ΔLL ≥ 0.005` nats per unit (baseline minus full log loss) |

`R_ann` for T2 uses the hold from fill to resolution (censored units excluded, §CB6-T); for N2 and R2 the hold is 2h
and `R_ann` is reported, not gating (a 2h maker hold is capital-light by construction).

### 2.5 Counting (M3 rule)

- Every counted test writes one `trials.jsonl` line via `provenance.append_trial`.
  - Routes: kinds `cb6_test` (Stage 1) and `cb6_replication` (Stage 2), with count lines `creative_batch_6:T`,
    `creative_batch_6:N`, `creative_batch_6:R` (`ml_explain` kind, `n_tests`).
  - Measurement: kind `cb6_measurement`, count line `creative_batch_6:C`, counted in the cumulative M3 total, its own
    family, never in the route Holm.
  - `cb6_descriptive` (EXCLUDE, no inference): census, gates, per-component logistic odds ratios, flag prevalences,
    episode counts, density tests, fake-cutoff tables, decile tables, sports strata, every reported variant.
- New `battery2.KIND_RULES` entries: `cb6_test`, `cb6_replication`, `cb6_measurement` EXCLUDE ("counted by the matching
  `creative_batch_6:*` count line"); `cb6_descriptive` EXCLUDE. Unknown kinds still raise. A unit test runs the counter on
  the real `trials.jsonl`.
- Placebo lines: `evidence_role: "placebo"`, count 0.
- **Cumulative count at drafting.** `battery2.cumulative_count()` on the working-tree `trials.jsonl` (rule
  `battery2-count-v1`) returned **1,104** at 2026-10-16T23:3xZ (325 automatic `flow_screen` lines, 492 `ml_explain`; no
  `cb1_test`-type kinds counted separately). **This is the Mac working tree only, so it is a lower bound:** the host
  appends `flow_screen` lines to its own copy, and `COLLECTION_HOST.md` ("Code updates and trials.jsonl") requires the
  two copies to be merged (`deploy.sh` runs `union_jsonl.py`: append-only exact-line union) before any count. Every CB6
  run that counts trials first runs that union step; the post-union value is recorded in every CB6 results file.
- **CB6 adds 6 fixed tests (T1, T2, N1, N2, R1, M1) and up to 6 conditional ones (T1, T2, N1, N2, R1 at Stage 2; R2 at
  Stage 2): 6-12 tests, taking the denominator to 1,110-1,116.** At that denominator BY at q = 0.10 needs z ≈ 4.1, which is
  why the Stage-1 gate plus Stage-2 Holm, not BY, is the decision rule (Ledger M3).
- Tests behind a failed or unknown gate (GT, GN, GR, GC, the N probe, the h8 deadline, a missing register for T2) are
  "not testable" or "not run" (p = 1) and **still counted**.

### 2.6 Placebos and robustness

**Design rule (from CB5 round 1, item 1).** Every binding placebo below is checked against one question: *is there a
plausible alternative under which it advances?* The alternative each one guards against is named. A placebo that would
pass whatever the data are is not used as a gate.

**Calibration placebos are judged on the p threshold alone (round 1, item 7).** For the calibration placebos (T1
calibrated null, T2, N2 and R2 break-even, M1 permutation) a draw "advances" iff it meets the test's p threshold (and,
for T2, the tail gate, which is itself a p-type bound); **materiality floors, `R_ann` and the other point-estimate
conditions are switched off in the placebo.** A floor several SEs above zero would make a calibration placebo pass
however anti-conservative the p value is (M1: the 0.005-nat floor is about 5 SE), so it would test nothing. The
alternative-effect placebos (N1 pseudo-episodes, R1 fake cutoffs) keep their stated rules: the N1 placebo keeps the full
gate because a generic sub-floor reversion must not veto a floor-sized conversion-specific effect (CB5 failure mode 5),
and R1's rule (b) is already p-only.

- **T1 calibrated-null placebo (calibration; binding).** Outcomes are redrawn **per event** (round 1): one uniform
  `U_e` per event cluster e (neg-risk members merged). For a market k in a non-neg-risk event, every unit (k, t) gets
  `Y'_c = 1{U_e < m_c(t)}` (comonotone across origins and across the event's markets: the strongest positive
  dependence, so the most demanding version). For the members of a neg-risk event, which cannot both resolve YES, member
  k is given the sub-interval `[o_k, o_k + p_k(t))` of `[0, 1)`, where `p_k(t)` is k's YES price at the unit's origin and
  the offset `o_k = Σ_{j<k} p̄_j` (members in market-id order, `p̄_j` = member j's mean YES price over its units, all
  offsets and lengths scaled by `1 / max(1, Σ_j p̄_j)`); YES_k' = `1{U_e ∈ [o_k, o_k + p_k(t))}` and `Y'_c` follows
  from the longshot side. At most one member resolves YES per draw, and every unit stays calibrated to its own price up
  to the scaling. T1 is recomputed on 200 draws (seed 6161), floors off. **Advance rate ≤ 1.5%.** *Alternative it guards against:* the cluster-robust p is anti-conservative for a rare binary
  outcome repeated across a market's origins and an event's members. If the clustering is too fine or G too small, the
  placebo advances far more than 1.5% and T1 cannot advance.
- **T1 class-shuffle attribution (binding for crediting the rule-text component only).** Feature (i) is reassigned by
  permuting markets within `fee_category` × creation month (features (ii)-(iv) kept). T1 is recomputed on 200 draws (seed
  6162). The text component is credited only if the real T1 exceeds the 98.5th percentile of the shuffled T1.
  *Alternative:* the class regex only tags categories in which longshots are underpriced (category, not rule class).
  If it fails, a T1 advance stands, but the verdict reads "tail predicted by price path / flow and category, not by rule
  class".
- **T2 break-even placebo (calibration; binding, as CB1).** Fill prices are kept; outcomes are replaced by
  `Y' = 1{U_e < a_c}`, drawn per event with the same neg-risk mutual-exclusion construction as the T1 placebo (intervals
  of length `a_c` on the longshot side), so expected net is 0. The T2 p condition and the tail gate run on 200 draws
  (seed 6163), floor and `R_ann` off. **Advance rate ≤ 1.5%.** *Alternative:* the rare-event tail gate and the exact event-level
  bound are miscalibrated at the realised number of winning clusters.
- **N1 pseudo-episode placebo (calibration; binding; replaces the idea's increment-shuffle placebo).** For each real
  episode, a pseudo-conversion time `t*` is drawn uniformly in `[t_conv − 72 h, t_conv − 30 h]` (inside the fetched
  window, at least 30h before the real conversion). On every hit member, the pseudo-"dump" is the non-converter sell
  burst (definition below) in `[t*, t* + 30 min)` **whose notional is nearest the real dump's `V_d`**, within
  `[0.5 V_d, 2 V_d]` (round 1: the draft's "largest burst" selected more extreme bursts than the real dumps; matching by
  notional copies the real units' size selection, so the placebo isolates the timing link to the conversion); none in
  range → that pseudo-unit is unavailable. Controls come from `[t* − 24 h, t* − 6 h]` by the same matching rule. N1 is
  recomputed with the full gate on 200 draws (seed 6164). **Advance rate ≤ 1.5%.**
  *Alternative:* "a burst of the dump's size reverts more than notional-matched ordinary bursts a day earlier" is a
  generic effect (intraday reversion pattern, depth refill after a sweep of that size). The pseudo-episodes copy the
  size selection and the control rule, so if the effect is generic the placebo advances and N1 cannot. The increment-shuffle
  placebo in the idea text was not adopted: it breaks the timing link and the bid-ask structure together, so it would
  pass whenever any sell reverts at all.
- **N2 break-even placebo (binding).** Entry prices and fills are kept; the exit `x` is replaced by `q + δ` with δ drawn
  from the member's own demeaned 2h bid-side VWAP changes in `[t_conv − 96 h, t_conv − 6 h]` (expected net 0 before
  fees). 200 draws (seed 6165), p condition only (floor and EV condition off), advance rate ≤ 1.5%.
- **R1 fake-cutoff placebo (calibration; binding).** The R1 estimator (same bandwidth, kernel, **donut**, population,
  clustering) runs at the 24 fake cutoffs 0.60, 0.61, ..., 0.83, each with its own donut `[c − 0.005, c + 0.005]` and
  the same "x = c is below" convention (every window lies inside [0.57, 0.86], disjoint from the real window [0.87,
  0.93]). **R1 may advance only if (a) the real |t| exceeds every fake |t| and (b) at most 1 of the 24 fake cutoffs
  reaches two-sided p < 0.01.** *Alternative:* price heaping at whole cents and curvature of the spread in price produce
  "discontinuities" at many round cutoffs; the fake cutoffs share that heaping, so the placebo fails if heaping drives
  R1. The expected number of fake rejections under a calibrated test is 0.24; (b) allows one. *Why the donut is now
  primary here too (round 1, item 3):* with a 1c tick, a whole-cent mid forces an even-cent spread (≥ 2c) and a
  half-cent mid an odd one, so without a donut the point mass at x = c (whole cent, "below") against x = c + 0.005 (half
  cent, "above") creates a mechanical jump at **every** whole-cent cutoff, real and fake alike. Rule (b) would then
  block a true effect, and τ would mix the reward effect with tick parity. Excluding `[c − 0.005, c + 0.005]` removes
  the three nearest grid points and leaves the same alternation of whole- and half-cent mids on both sides.
- **R1 reward attribution (binding for crediting the reward rule).** The same RD in markets **without** rewards
  (`clob_rewards` empty or 0 at the capture). The difference-in-discontinuities `τ_DD = τ_rewarded − τ_unrewarded` must
  have τ's sign and at least half its magnitude. If the unrewarded population fails gate GR's size rule, attribution is
  "unverified" and R1 **cannot be credited** to the reward rule at that stage (a Stage-1 advance stands only as "a
  discontinuity at 0.90, cause unverified", and R2 is then **not** registered). *Alternative:* something else changes at
  0.90 for all markets (a UI band, a bot convention). Less data can never make crediting easier.
- **R1 sorting check (binding for crediting the reward rule; round 1 should-fix).** Quoters steering the mid to stay
  at or below 0.90 is part of the hypothesised mechanism, and it would also break the RD continuity assumption. The
  McCrary density test of x at 0.90, with the same donut, is run at 0.90 and at the 24 fake cutoffs. "Sorting detected"
  iff the 0.90 test has two-sided p < 0.01 **and** its |t| exceeds every fake-cutoff |t| (heaping at whole cents is
  common to all cutoffs). If sorting is detected, R1 is reported as "a discontinuity with sorting at the cutoff,
  non-causal", the reward rule is **not credited**, and R2 is **not registered**. Without sorting, τ is still an
  intent-to-treat estimate (below), never a structural effect.
- **R2 break-even placebo (binding).** Fills kept; the mark replaced by entry mid plus a demeaned 2h mid change drawn
  from the same market's previous 3 days of tight captures. 200 draws (seed 6166), p condition only (floor and EV
  condition off), advance rate ≤ 1.5%.
- **M1 permutation calibration (binding).** The added feature block (§CB6-C) is permuted across units within
  (capture × baseline-score decile) cells in both the fit and evaluation windows; the model is refitted and M1
  re-evaluated on 200 draws (seed 6167), **judged on M1's p < 0.05 alone, floor off**. **Advance rate ≤ 7.5%**, i.e.
  1.5 × M1's α, the same ratio to the nominal level as the route placebos' 1.5% against α = 0.01. (The draft's "≤ 1.5%
  with the full gate" could not fail because of the floor; "≤ 1.5% with the floor off" could not pass, since a
  calibrated test at α = 0.05 advances in about 5% of draws.) *Alternative:* the clustered ΔLL inference is
  anti-conservative (for example, the same market's repeated captures dominate a cluster way).

**Binding robustness for any advance or pass:**
- (i) routes: the +0.75c cost robustness (§2.1) keeps net > 0;
- (ii) the test still meets its p threshold and floor without the top 5 clusters by absolute contribution, in each way;
- (iii) unweighted and cluster-equal-weighted estimates agree in sign;
- (iv) the rebate-halved economic estimate keeps net above the floor (T2, N2, R2);
- (v) the declared worst case for unavailable units (per test) keeps the estimate on the declared side;
- (vi) the era rule (CB5 §CB5-G) for T2 when the register says `post_rollout_or_interaction`;
- (vii) T1: the logistic version (`logit P(Y = 1) = α + β·F + γ·logit(m_c) + band FE`) has β on Δ's side; the
  design-weighted Δ (h8 `sample_weight`) has Δ's sign;
- (viii) N1/N2: the result holds with the converter-wallet cluster way (G ≥ 15) as well as event × day;
- (ix) R1: the **wider-donut** estimate (excluding x ∈ [0.89, 0.91], again symmetric in tick parity) has τ's sign and
  ≥ half its magnitude, and the estimate stratified by tick size (`order_price_min_tick_size` 0.01 vs 0.001) agrees in
  sign in every stratum with ≥ 30 clusters (the narrow donut is now the primary, §CB6-R; the no-donut estimate is
  reported only, because tick parity biases it mechanically);
- (x) M1: the market-disjoint evaluation (evaluation units whose market never appears in the fit window) has M1's sign
  and ≥ half its magnitude;
- (xi) R1, R2, M1: the p threshold also holds with 12-hour time blocks under the small-G rule (§2.3).

Reported, not binding: sign by month and fee category, the sports strata, +1c cost, hold-to-resolution variants
(N2, R2), per-component T1 contributions, the no-donut R1 estimate, decile print-rate tables (M1), T1 excluding 50-50
resolutions. (The McCrary density test at 0.90 moved to binding for crediting, above.)

### 2.7 Pre-freeze census (q0125; counts only)

An outcome guard drops outcome columns before population code runs (CB1 §2.9). **No target, coefficient, net,
mark-out, spread-at-cutoff or log loss is computed.** Each family's census receives its inputs through an accessor that
returns only the fields listed; a unit test asserts that no census path receives a target field.

**T (SCREEN block only; HOLDOUT is never opened by the census):**
- T-i: frame and sample counts by stratum; frame markets removed by the event-level exclusion (by key type) and the
  share of exclusion ids without metadata; dropped h7 overlaps; capped-window exclusions; markets with a clarification
  marker (share, by category); share of frame markets whose `closed_time` precedes `end_at` by more than 7 days (a
  status count, reported to show whether Gamma rewrites `end_at` on early resolution, which would reintroduce
  outcome-dependent selection through the `end_at ≤ T_fetch8 − 7 d` rule).
- T-ii: eligible units (origin rule, §CB6-T) and markets; censored share (market not closed at `T_fetch8`, a status, not
  an outcome); truncation counts for features (iii)/(iv); wallet-lookup failures.
- T-iii: prevalence of each feature and of F, by category and price band. **Expected YES count** `Σ m_c` per F stratum
  (a price, not an outcome).
- T-iv: **gate GT:** ≥ 1,000 eligible SCREEN units, ≥ 300 units and ≥ 100 market clusters in each F stratum, and
  `Σ m_c ≥ 40` in each stratum. Fail → T1/T2 "not testable" (counted); CH60 then needs a new declaration on a new fetch.
- T-v: the Stage-1 MDE recomputed from these counts (never used to change a threshold).

**N (dev window, excluding the J4-R window):**
- N-i: probe result (q0123): conversions found, share whose stakeholder hash has ≥ 1 print in the event within ±1 day,
  share matched by the same conversion in the stakeholder's Data API `/activity` (type `CONVERSION`, if the type
  exists).
- N-ii: conversions per day; episodes (≥ 1 converter sell within 30 min); hit members; distinct converter hashes.
- N-iii: units with a non-empty exit window and ≥ 1 matched control (**counts only**, via a count-only accessor);
  event × day clusters.
- N-iv: **gate GN:** ≥ 100 available units, ≥ 30 event × day clusters, ≥ 15 converter hashes. Fail → N1/N2 "not testable"
  (counted).

**R (dev window):**
- R-i: market-captures with folded mid x in [0.87, 0.93] by side of 0.90, rewarded and unrewarded, non-sports; fixture-
  day clusters by side; tick-size mix. The accessor returns `x`, ids and reward fields, never bid, ask or spread
  separately.
- R-ii: McCrary density estimate of x at 0.90 and at the fake cutoffs (x only, donut), reported here; it binds only
  through the sorting check at Stage 1 (§2.6) and is never used to change the window, donut or bandwidth.
- R-iii: **gate GR:** in rewarded non-sports markets, ≥ 2,000 market-captures and ≥ 100 fixture-day clusters on each side
  within the bandwidth **outside the donut**, and ≥ 30 six-hour blocks. Fail → R1 "not testable". The same thresholds on unrewarded markets decide whether attribution
  (§2.6) is checkable.

**C (dev passes):**
- C-i: units per pass, pass coverage by day (host raw vs release copy vs missing), frame type in `plan.json`, inclusion
  probabilities, availability of the target window, feature missingness.
- C-ii: **gate GC:** ≥ 50,000 available dev units over ≥ 5 dev days. Fail → the fit runs anyway on what exists, and M1
  carries "fit on short dev window" (a label; M1's own test is on the evaluation window).

Floors are never revised from the census.

### 2.8 Compute, network, disk and stop rules

- Host: 1 OCPU, about 5.6 GiB RAM shared with the collector. Queue worker as CB5 §2.8 (one job per lane, nice 19,
  `MemAvailable ≥ mem_mb + 1200`, address cap 2 × `mem_mb`, 02:45-05:30 UTC start blackout for `mem_mb ≥ 500`). Never two
  multi-GB jobs at once.
- **Lanes.** q0120 (`h8_tail`) is on `net` at priority 61, `--budget-min 90`, repeat-until-complete. It yields the lane at
  every chunk boundary to the T_seal-bound jobs with lower ids (q0043, q0081, q0082) and beats q0002 (60). Every other
  CB6 fetch (q0121's h7 key lookup, q0123, q0124, q0131) is light and runs on `cpu` at `--rps 2` (half the shared limiter's 4 rps, so two
  concurrent processes stay ≤ 6 rps in total), as CB4/CB5's API fetches do while q0002 holds `net`.
- **Priorities.** q0120 61; q0121 58; extractor backfill q0122 56 (below CB5's q0101 at 57); probe and dev fetch 44;
  census 40; measurement 39; screens and replications 38.
- **`h8_tail` deadline mechanics.** As CB4 §1.3: the fetcher refuses to start a new chunk at or after `T_seal`; a run
  still incomplete at `T_seal` writes `NOT_RUN_DEADLINE.json` and exits 0 with `not_run_deadline`. Request budget about
  **39k** (frame about 6k; per market about 3 price windows, about 3 windowed print requests, about 1 wallet lookup) at
  ≤ 4 rps: about 2.7 h of request time, about **3.5 h wall** with collector yields, i.e. 3 chunks. **Latest safe start on
  the host: 2026-10-21T12:00Z.** **No Mac fallback (removed 2026-10-17, coordinator).** The Mac data-dumps were
  retired and the Mac runs no background jobs, so the earlier same-parameter Mac fallback (round 1) is withdrawn.
  q0120 runs on the host only. If it cannot complete on the host before `T_seal`, it is recorded `not_run_deadline`
  and counted. h8 is fetched, sealed and read on the host; the read location recorded at seal is the host, and
  `ACCESS_LOG.jsonl` exists only there.
- **Disk guard and headroom precondition (as CB5 §2.8 item 15).** Host `data-dumps` was 9.7 GB at 2026-10-16T22:57Z
  against the 12 GB cap, growing **about 0.9-1 GB a day** while snapshot deletion is gated (`data_catalogue/RETENTION.md`;
  the draft's 0.75 GB was too low, so the precondition below uses 1.0 GB a day). Every CB6 data job refuses to
  start above 10 GB. Output caps: `h8_tail` **0.12 GB** (parse guards keep only the origin windows: hourly points in
  `[t − 8 d, t + 2 d]` and prints in `[t − 30 d, t + 6 h]` per origin), `band/` 0.15 GB, `printflag/` 0.03 GB,
  conversions and member prints 0.06 GB (dev) + 0.08 GB (rep), `cb6_followup/` 0.05 GB. Before any CB6 data job is
  committed, the coordinator records in the commit message either (a) that snapshot deletion is active on the host, or
  (b) that current size + 1.0 GB × (days to the job's last scheduled run) + its cap ≤ 10 GB with ≥ 3 GB free. If
  neither holds, the job is held (q0120: no Mac fallback; incomplete at `T_seal` → `not_run_deadline`). The precondition never changes retention.
  **Disclosed:** at 9.7 GB on 10-16 and +0.9-1 GB/day, (b) already fails for q0120 on the host; q0120 runs on the host only
  if retention activates (archive rotation, pending user decision 2 of 2026-10-15) or another session frees space. The h7
  fetches are in the same position (they refuse above 10 GB too).
- 10 CPU-hour cap per family. A job failing twice for the same non-transient reason stops and is recorded.
- A null is "not detected at MDE x", never "absent". No re-screen of a failed CB6 test with altered windows, horizons,
  thresholds, regexes, cutoffs, bandwidths, feature sets or populations, on any data.
- **Network etiquette:** shared `Limiter`, yield to the live collector, 429 and `Retry-After` back-off, stop on repeated
  429, collector-health stop (as CB2/CB4 §2.8). Polygon RPC: ≤ 2 rps, block range per `eth_getLogs` call set by the probe
  (≤ 2,000 blocks if the endpoint caps lower ranges), fallback endpoint list pinned in the declaration.

### 2.9 Snapshot inputs and the retention gate

`RETENTION.md` is owned by another session. CB6 states its rule here; the coordinator adds it to the reader list.
- CB6 readers of raw captures, sweeps and trade samples: only `run_cb1_extract.py --tables band,printflag` (pass step
  and backfill q0122) and the `cb6_followup/` step (reads the current pass's sweep only).
- **CB6 places no requirement on retention.** Inputs deleted before the backfill reaches them are streamed from verified
  release copies one at a time (CB4 §2.10). A pass whose release copy is missing or fails verification is counted as
  missing, never reconstructed.
- `cb6_extract/` and `cb6_followup/` are never deleted (no rule).

### 2.10 Funnel and what a prospective registration would look like

As CB5 §2.10: screen (Stage 1) → selection by gate, placebo, attribution and robustness → frozen replication (Stage 2,
L2-dev) → separate prospective confirmation (Stage P, recorded prices) → economic validation at recorded prices.

- **R2 is not part of this funnel's Stage 2 in the usual sense:** it is first tested on post-freeze data, so a pass is
  L1 (single stage, unreplicated) and Stage P-R would be its first replication.
- **T survivor (Stage P-T).** A `description`-at-first-sighting column added to the live `listings`-type extractor (CB5's
  table, or its own), the class flag computed on the stored first-sighting text (removing the current-text risk), drift
  from captures, and large buys plus wallet ages from the live trade monitor's pipeline (which already computes
  `wallet_age_h` causally). Population: open non-sports, non-weather binary markets with a longshot side in [0.02, 0.10]
  at a weekly capture. Paper asks at the recorded touch, queue fills from a targeted trade stratum, held to resolution
  (weeks to months). Acceptance: T1 one-sided p < 0.05 after Holm, floor, tail gate. The economic read waits for
  resolutions, so Stage P-T takes months.
- **N survivor (Stage P-N).** A conversion watcher (Polygon logs every 2-5 minutes, keyless) plus targeted windowed
  prints and a targeted sweep of the hit members within minutes of the conversion. Execution at the recorded book.
- **R survivor (Stage P-R).** The follow-up stratum continued with a queue-position rule from recorded prints and
  recorded depth, rebate halved, hold-to-resolution tail reported.
- **C (measurement).** No Stage P. An adopted M1 supplies the fill-probability model that every later maker
  registration must state (its expected fills per quote, and which decile it quotes in). It can never lower a cost or
  relax a gate of a frozen test (one-directional use, as CB4 R0).

---

## 3. Jobs

### CB6-T: Ex-ante tail classifier for longshot sellers (CH60)

**Question.** Among binary longshots priced 0.02-0.10, do those in a class flagged by public, ex-ante features resolve YES
more often than their price says, relative to unflagged longshots (T1)? Does a paper longshot ask in the unflagged class,
held to resolution, pay after costs (T2)?

**Why new / overlap.** CB1-C (C1) tested unconditional longshot ask-selling on h2 and failed (-3.84c; resolution excess
-4.75c). CB6-T asks whether the loss is concentrated in an identifiable class. Disjoint data (h8), features fixed before
any fetch, C1's unit list never opened (§1.3).

**Data: the `h8_tail` fetch (q0120; spec in §CB6-F).** Seeded sample, disjoint from prior runs by market and by event /
neg-risk / series key, of about 4,500 binary markets with
Gamma `description`, hourly price windows around ≤ 3 declared origins, windowed prints, buyer first-trade times, guarded
outcomes, rows capped at `min(T_fetch8, T_seal)`.

**Population (frozen frame).**
- Binary (two outcomes), `fee_category` not weather (excluded) and not sports (reported stratum). Crypto "Up or Down"
  questions excluded (scheduled life < 14 d anyway). Created in `[2025-09-01, 2026-07-31]`, **scheduled
  `end_at ≤ T_fetch8 − 7 d`** (round 1, item 4), scheduled life `end_at − created_at ≥ 14 d`.
- **Why `end_at ≤ T_fetch8 − 7 d` (replacing the draft's `end_at ≤ T_fetch8 + 400 d`).** With long-dated markets in the
  frame, a market whose longshot already happened is resolved early and stays, while one whose longshot has not
  happened is still open, censored and dropped: the kept set is selected on YES. Restricting to markets whose
  scheduled end is at least 7 days before `T_fetch8` means both kinds have had their scheduled chance to resolve, so
  censoring is rare and no longer driven by the outcome. Cost, stated: CB6-T covers only markets scheduled to end by
  about 2026-10-10; long-dated markets (multi-year political questions) are outside its scope. Residual risk: if Gamma
  rewrote `endDate` to the resolution time on early resolution, early YES markets with a later original end would
  still enter; CB1 found that h2 omits early-resolved markets with a future `endDate` (CB1 §6 risk 4), i.e. Gamma keeps
  the scheduled date, and the census reports the early-closure share (§2.7 T-i).
- **Clarification rule.** Markets whose stored `description` matches a clarification marker (`clarif`, `update:`,
  `updated`, `additional context`, `edit:`, `note:` followed by a date, case-insensitive; the list in the rules file)
  are excluded from the primary and counted. Reason: the description is the *current* text and a post-event clarification
  could encode the outcome. Likely direction of the resulting bias: against the hypothesis (clarifications follow
  surprises). T1 including them is reported.
- **Origins (declared; seed `arepo-h8-tail-origins`).** The weekly grid of Mondays 00:00 UTC inside the market's scheduled
  life `[created_at + 7 d, end_at − 24 h]` and `≤ T_fetch8 − 60 d`. Up to **3 origins per market** are drawn uniformly
  without replacement from that grid, seeded by market id. The draw uses only `created_at` and `end_at` (as of the frame),
  never prices or outcomes. **Disclosed look-ahead:** `end_at` is read at `T_fetch8`, not at listing; Gamma may have
  moved it. It enters only the origin grid, never a feature.
- **Unit eligibility at origin t** (all as of t):
  - market open at t (§2.2);
  - longshot side c = token 0 if `p0(t) ≤ 0.5`, else token 1; `m_c(t)` ∈ [0.02, 0.10] from the usable hourly point;
  - ≥ 1 print in `[t − 7 d, t)` (truncation rule: unavailable is excluded and counted);
  - a usable point at `t − 7 d` (for feature (ii)).
- Unit = (market, origin). Outcome `Y_c` = 1 if side c resolved YES, 0 if NO (guarded file). **50-50 resolutions enter
  the primary with `Y_c = 0.5`** (the actual payout), so `e = 0.5 − m_c`; they count as non-wins in the tail gate's π
  and as not-YES for the ≥ 10 YES-cluster rule; T1 excluding them is reported. Censored (not resolved at `T_fetch8`):
  excluded from the point estimate and counted; the T1 and T2 censoring worst cases below are **binding**.

**Features (fixed now; hashed in the rules file before any fetch).**
- **(i) Discrete-decision class.** Over the question text (lowercased): `D` matches any of `\bannounc\w*`, `\bcourt\w*`,
  `\border\w*`, `\baward\w*`, `\bnominat\w*`, `\bstrike\w*`; `C` matches any of `\bprice\w*`, `\btemperature\w*`,
  `\bscore\w*`, `\bpoll\w*`. Class D iff the question matches D and not C. If the question matches neither, the same rule
  is applied to the first 500 characters of the description. Otherwise not D. (These are exactly CH60's word lists with
  inflections; no word was added.)
- **(ii) Upward drift.** `m_c(t) − m_c(t − 7 d) ≥ +0.01`.
- **(iii) Large longshot buy.** A print buying side c (BUY of c, or SELL of the other token at `1 − price`) in
  `[t − 24 h, t)` with notional (size × price of c) ≥ 5 × the median print notional of the market over `[t − 30 d, t)`
  (median over ≥ 10 prints; fewer → unavailable).
- **(iv) Young buyer.** For a (iii) print, the buyer's first trade (Data API `/activity`, earliest TRADE at or before the
  print, `event_study.first_trade_lookups`; raw address only in memory, hash stored) is later than the print `ts − 30 d`.
- **Flag `F` = (i) OR (ii) OR [(iii) AND (iv)].** Disjunction, because the money route excludes any unit in any risky
  class.
- Truncation: if the market's stored prints do not cover `[t − 30 d, t)` (window paging hit its cap), (iii) and (iv) are
  unavailable; such a unit takes `F` = 1 if (i) or (ii) is true, otherwise it is **unavailable** (excluded, counted, and
  in the worst case below).

**T1 statistic.** Resolution excess `e = Y_c − m_c(t)`. Price bands b ∈ {[0.02, 0.04), [0.04, 0.07), [0.07, 0.10]}.
`Δ = Σ_b w_b · [mean(e | F = 1, b) − mean(e | F = 0, b)]`, with `w_b` the pooled band share of units. Test Δ > 0.

**T2 (economic).** Units with F = 0 only. A 5-share paper ask at `a_c = min(m_c + half_spread(m_c), 0.999)` resting over
`[t, t + 6 h)`, **filled on a trade-through only** (a print buying c at a price strictly above `a_c`; queue sizes are not
available historically). `net = a_c − Y_c − a_AS` per filled share; capital `1 − a_c`; held to resolution. The touch rule
(any buy of c at ≥ `a_c`) is a bracket that must agree in sign (binding).

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **T1** | mechanism | eligible (market, origin), resolved | band-weighted flagged-minus-unflagged resolution excess Δ | > 0 |
| **T2** | economic | filled paper ask, F = 0 | mean net per filled share | > 0 |

**Clustering.** Event × resolution ISO week (CB1 carries; neg-risk members merged into one event) and market. One-sided
p = the max over the two ways (small-G rule). T1 additionally requires **≥ 10 YES-event clusters in each F stratum**;
fewer → "not testable" (p = 1, counted; fewer YES events can never make T1 easier).

**Binding gates.**
- **Tail gate on T2 (as CB1 §2.3 / C1).** `π` = share of filled orders whose longshot wins; `π* = mean(a_c)`. The
  one-sided upper bound (Wilson on `n/deff`, or the exact event-level bound below 10 winning clusters; 99% at Stage 1,
  95% at Stage 2) must be `< π* − 0.005`.
- **Adverse selection (as CB1 C1 "PX1", decided by an upper bound).** `Δ_drift` = mean 24h post-fill drift of filled
  orders minus that of unfilled orders (hourly points). Its upper bound (hull of the bootstrap 95% limit and
  `Δ̂ + z·max SE`) must be below the mean captured half-spread `mean(a_c − m_c)` of filled orders; otherwise T2 is capped
  "inconclusive: adverse selection not excluded" even if it passes.
- **Censoring worst case (binding for T1 and T2; round 1, item 4).** T1: Δ recomputed with every censored unit set to
  YES if F = 0 and to NO if F = 1 (the direction that shrinks Δ) must stay > 0 and keep the T1 p threshold (the draft
  only reported it); T2: censored fills counted as filled losers (`net = a_c − 1`) must keep T2 > 0.
- **Truncation worst case (binding for T1).** Unavailable units added back with F chosen against the hypothesis (F = 0
  if `Y_c = 1`, F = 1 if `Y_c = 0`); Δ must stay > 0.
- **Era rule** (§2.6 (vi)) for T2; `a_AS` on pre-rollout fills.
- **Register deadline for T2.** T2 waits for `model_specs/cost_regimes_v1.json`; if it is not committed by
  `T6_T2_register_deadline` (2026-11-21T00:00Z), T2 is "not run (register missing)", p = 1, counted, and is not carried.

**MDE (assumptions; the census replaces them; the round-1 frame restriction to shorter-dated markets and the event-level
exclusion may lower the eligible count, never the floors).** About 4,500 markets × 3 origins × about 35% eligible ≈ 4,700 units,
about 2,350 per block in about 1,300 markets. Base rate ≈ mean price ≈ 5%, `Var(e) ≈ 0.048`; F prevalence about 50%;
outcomes are identical across a market's origins, so the design effect is about the origins per market (≈ 1.8).
SE(Δ) ≈ √(0.048 · 2 / 1,175) · 1.34 ≈ 1.2c. **Stage-1 MDE ≈ 3.8c** (z 2.33 + 0.84); **Stage-2 MDE ≈ 3.4-3.9c** (Holm
z between 1.96 at the last step and 2.39 at the first step with k = 6, plus 0.84). The 2.0c floor is below the MDE:
**T1 can detect only a strong class effect** (for example flagged excess +2c vs unflagged −2c). T2: at a trade-through
fill rate near C1's 6.8%, about 80-120 fills per block; per-fill SD ≈ 22c gives SE ≈ 2.5c and MDE ≈ 8c. **T2 is expected
to be "not testable for size" in both blocks**; if T1 advances, the carry rule applies, and the economic answer then rests
on Stage P-T.

**MDE restated 2026-10-17 (amendment A-T1, last section; supersedes the figures above before the seal).** The h8_tail frame
yielded 362 markets / 670 origins (1.85 origins per market, not 1.8). With the h8_tail_b top-up the union is about
1,860-3,260 markets and about **1,140-1,530 units** at the 26-35% eligibility range, not 4,700. MDE = 3.8c × √(4,700 / units)
≈ **6.7-7.7c** (Stage 1; Stage 2 scales the same way). **T1 detects only strong effects**; without the top-up (h8_tail alone,
about 235 units) the MDE is about 17c. The ≥ 10 YES-cluster rule and every floor are unchanged. The census replaces these
assumptions; the MDE is never used to change a threshold.

**What would kill CH60.** GT fails; event-level disjointness unverified; T1 not detected at MDE; the calibrated-null
placebo advances (inference not trustworthy); the truncation or censoring worst case flips Δ; T1 holds only with clarification-marked markets; T2 ≤ 0 or fails the
tail gate at the binding cost; adverse selection not excluded.

**Verdict map.**
- T1 replicated on HOLDOUT (and T2 passed or carried and passed) → "ex-ante tail class development-replicated on
  same-calendar data (L2-dev)" → Stage P-T.
- T1 replicated, T2 not → "the tail is predictable, but the unflagged carry is not shown to pay after costs".
- T1 not detected → "longshot tail not predictable from these four features at MDE x"; CH61 and CH62 lose their
  classifier premise.
- Class-shuffle attribution fails → the verdict names price path / flow and category, not rule class.

**Stop rule.** No T1 advance and no carried T2 → q0130 is not committed and HOLDOUT is never opened (it stays sealed and
unread, available to a future declaration only with that history disclosed).

### CB6-N: Neg-risk conversion dumps (CH66)

**Question.** When a holder converts NO positions on members of a neg-risk event, receives YES on the other members and
sells some of them within minutes, do the hit members' bid-side prices recover more than after an ordinary large sell on
the same member (N1)? Does a paper bid posted 60 s after the conversion on every received member, priced from
information available at that moment, exited 2h later by a taker, pay (N2)?

**Why new / overlap.** No AREPO study uses conversions. J5's sibling reversal used captures; CB1-D tests neg-risk ask sums
(not read here, §1.3); CB4-S is series rolls. The episode list comes from the chain, not from the trade sample.

**Data.**
- **Probe (q0123, before the census).** Read the neg-risk adapter and its conversion event signature from Polymarket's
  contracts documentation (the address and topic are pinned in the declaration at probe time, not from memory); pull one
  day of logs; take 20 conversions at random (seed `arepo-cb6-probe`); for each, fetch the event's member prints in
  `[t_conv − 1 d, t_conv + 1 d]` and check (a) that the stakeholder hash has ≥ 1 print in the event (the stakeholder is
  the proxy wallet that trades), (b) that the index set decodes to members that exist in Gamma's member list. **PASS iff
  ≥ 16 of 20 satisfy both.** FAIL → CB6-N "not testable (source)" (N1, N2 counted, p = 1); a trade-signature variant would
  need a new declaration. The probe reads no price for analysis; it prints counts only.
- **Dev fetch (q0124, after `T6_dev_end` + 3 h).** All conversion logs from **`T6_dev_start − 96 h`** to `T6_dev_end`
  (the extra 96 h are used only to check control and pseudo-episode wallets for conversions; episodes are conversions
  inside the dev window, J4-R excluded); for every dev conversion whose event has ≤ 40 members and at least one member
  outside the converted index set: Gamma member metadata (guarded) and one windowed print fetch
  `[t_conv − 96 h, t_conv + 3 h]` over the comma-separated member list (paged, ≤ 10 pages). **If the 10-page cap is hit,
  the window is truncated and every unit of that conversion (N1 and N2) is unavailable**, counted and entered in the
  worst case; it is never analysed on a partial window. Raw addresses (stakeholder, `proxyWallet`) are hashed in memory
  with the HMAC key; only hashes are written.
- **Print semantics (declared).** Requests use `takerOnly=true`: each fill appears once, from the taker's side;
  `proxyWallet` is the taker and `side` is the taker's side on the printed token (`asset`). A **converter sell** is a
  print whose `proxyWallet` hash equals the stakeholder hash with `side = SELL` on YES_j, or `side = BUY` on NO_j (mapped
  to a YES sell at `1 − price`). Converter sells executed as a resting maker order are not visible as converter prints
  (the taker is the buyer); CB6-N therefore studies **taker dumps only**, which is CH66's mechanism, and the episode
  count is a lower bound on conversions followed by sells (disclosed).
- **Replication fetch (q0131, rolling):** the same for `[T6_rep_start, T6_N_rep_end)`, each conversion fetched at
  `t_conv + 3 h + 30 min`.

**Definitions.**
- **Received members** of a conversion: members not in the converted index set (the converter now holds their YES).
- **Converter dump on member j:** the converter's (hash-matched) SELL prints of YES_j (or BUY of NO_j, mapped) in
  `[t_conv, t_conv + 30 min)`. `t_d` = last such print; `p_d` = their VWAP; notional `V_d`.
- **Episode** = a conversion with a dump on ≥ 1 received member. **Unit** = (episode, hit member j). Members with
  `order_price_min_tick_size` unknown are excluded and counted.
- **Bid-side print series** on member j, non-converter wallets only: taker SELL of YES_j and taker BUY of NO_j (mapped to
  YES terms). `P_B[a, b)` = their VWAP, unavailable if empty.
- **Recovery** `y = P_B[t_d + 30 min, t_d + 2 h) − p_d` (cents). Same-side prints, so bid-ask bounce cannot create it.
- **Sell burst** (for controls and placebos): all bid-side prints on member j by one non-converter wallet within 30
  minutes, aggregated (VWAP, notional, last print time).
- **Matched controls:** sell bursts on the same member j in `[t_conv − 24 h, t_conv − 6 h]`, by wallets that made no
  conversion on the event in the fetched window, with notional in `[0.5 V_d, 2 V_d]`; up to 5 nearest in notional
  (ties by time). Their recovery `y_c` uses the same windows relative to each burst's last print. `ȳ_c` = mean.
  No control → unit unavailable (counted).
- **N1 statistic:** `Δ_N = mean_u (y_u − ȳ_c,u)`, test > 0.
- **N2 (economic; causal bid rule, round 1, item 1).** The draft bid only on members where the converter sold after the
  bid was posted and priced the bid from that later sale (`q = p_first + tick`, with `p_first` below q), so every bid
  filled by construction: it used future data. Replaced by a rule that uses only information available at
  `t_post = t_conv + 60 s` (the conversion's block time plus 60 s latency):
  - **Bid set:** every **received member** j of every qualifying conversion (whether or not the converter later sells
    on j); a unit is (conversion, received member).
  - **Price:** `q = b_last + tick`, where `b_last` = the price of the last bid-side print on j (any wallet, YES terms)
    with `ts < t_post` inside `[t_post − 24 h, t_post)`, and tick = j's `order_price_min_tick_size`. No such print →
    no bid (counted "not placeable"). If `q` is at or above the last ask-side print (taker BUY of YES_j or SELL of NO_j)
    with `ts < t_post` in the same 24 h, the bid would be marketable and is not posted (counted).
  - Resting `[t_post, t_post + 30 min)`. **Fill on a trade-through:** a bid-side print (any wallet, including the
    converter) strictly below q. Touch bracket (any bid-side print at ≤ q) must agree in sign (binding). Exit: taker
    sell at `x = P_B[t_fill + 1.5 h, t_fill + 2.5 h)`; `net = x − q − f(x) + rebate(q)`. EV per posted bid = Σ net over
    fills / posted bids.
  - Reported, not counted: N2 split by whether the converter later sold on j (an ex-post split, descriptive only).
- **Worst case for unavailable exits (binding, §2.6 (v)):** exit at the lowest print price on member j (any side) in
  `[t_fill, t_fill + 2.5 h]`, or at `q − 0.02` floored at 0.001 if there is none.

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **N1** | mechanism | (episode, hit member) with target and ≥ 1 control | `Δ_N` = dump recovery − matched ordinary-sell recovery (cents) | > 0 |
| **N2** | economic | filled paper bid on a received member (posted at `t_conv + 60 s`, priced from prints before it) | mean net per filled share | > 0 |

**Clustering.** Event × UTC day of the conversion, and converter hash; one-sided p = the max over the two ways
(small-G rule; the converter way needs G ≥ 15, else "not testable").

**Reported, not counted.** Recovery share `y / (b0 − p_d)` with `b0` the bid-side VWAP in `[t_conv − 2 h, t_conv)`;
behaviour of received members the converter did *not* sell (held YES), as a context check for news-driven
conversions; N1 by member price band and by event size; the sports stratum.

**MDE (assumptions; census replaces).** Conversion frequency is unknown. If about 30 qualifying episodes a day with
about 2 hit members each, about 11.5 usable dev days, and about 50% availability: about 350 units in about 200 event-day
clusters. Per-unit SD of `y − ȳ_c` ≈ 1.5c, design effect 2: SE ≈ 0.11c, **Stage-1 MDE ≈ 0.36c**, just above the 0.3c
floor. N2: the bid set is now every received member (more bids than hit members), but fills are no longer guaranteed;
the trade-through fill rate one tick above the last bid-side print is unknown. At about 30 conversions a day × about 3
received members × 11.5 days × 10% fills, about 100 fills → borderline "not testable for size" at Stage 1 (carry
rule).

**What would kill CH66.** Probe FAIL; GN fails; N1 not detected; the pseudo-episode placebo advances (generic
selected-burst reversal); the converter cluster way loses significance; N2 ≤ 0 after the exit fee, the binding cost or the
worst case.

**Verdict map.** N1 and N2 replicated → "conversion dumps revert beyond ordinary same-size sells, and a 60-s maker bid on
received members pays (L2-dev)" → Stage P-N. N1 only → "dumps are uninformed flow, not capturable at 60 s latency after a taker exit".
N1 not detected → CH66 closed at MDE.

**Stop rule.** No N advance and no carried N2 → q0131/q0132 are not committed.

### CB6-R: Reward-shadow discontinuity at the folded mid 0.90 (CH71)

**Question.** Does the quoted spread change discontinuously at the folded mid 0.90, where single-sided reward scoring ends
(R1)? If it is wider above, is a touch maker in [0.90, 0.96) net-positive (R2)?

**Why new / overlap.** No AREPO test uses the reward cutoff. CB3-B's maker population is mid ∈ [0.10, 0.90] (disjoint from
the shadow band); CB1-A's decided carry is [0.95, 0.99] on h2/h5 (not read). CB6 reads no CB3 or CB1 table.

**Data.** `cb6_extract/band/` (§4.3) for dev and replication captures; `cb6_followup/` fills (R2, post-freeze only).

**Population (R1).** Binary, two-sided, non-crossed, `accepting_orders`, not weather, not sports (stratum), **rewarded**
(`clob_rewards` non-empty with a positive daily rate in the sidecar at that capture), `end_date > received_utc + 8 h`.
Running variable `x = max(mid0, 1 − mid0)`, `mid0` the token-0 touch mid. Window `x ∈ [0.87, 0.93]`. "Above" = `x > 0.90`.

**R1 estimator (donut RD; round 1, item 3).** Local linear regression of the quoted spread `s = ask − bid` (cents) on
`x − 0.90` separately on each side, triangular kernel, fixed bandwidth h = 0.03 (declared; no data-driven bandwidth),
**excluding the donut x ∈ [0.895, 0.905]** from both sides. `τ = lim_{x↓0.90} E[s|x] − lim_{x↑0.90} E[s|x]`, each limit
extrapolated from outside the donut. Stage 1: two-sided test of τ ≠ 0. Units are market-captures. Every capture of a
market is used; the cluster ways absorb the repetition. *Why the donut is primary:* with a 1c tick, whole-cent mids
(0.890, 0.900, 0.910) force even-cent spreads and half-cent mids (0.895, 0.905) odd ones; the point mass at exactly
0.900 sits "below" and 0.905 "above", so a no-donut estimate has a mechanical parity jump at every whole-cent cutoff.
A half-cent-mid indicator was considered and **declined**: mid parity is a deterministic function of spread parity
(the outcome), so controlling for it would absorb part of a true 1c effect. The donut leaves the same parity mix on
both sides and is applied identically at the fake cutoffs (§2.6).

**What τ estimates (disclosed).** The venue scores rewards on its own midpoint, which the documentation describes as
possibly size-adjusted (orders below the market's minimum size may be ignored), not necessarily the touch mid used here.
Treatment is therefore not a deterministic function of x: the design is a **fuzzy RD** whose first stage (the venue's
reward midpoint) is not observed. τ is an intent-to-treat discontinuity in the touch mid, diluted toward 0 relative to
the effect at the venue's own cutoff; no fuzzy-RD rescaling is attempted. With the sorting check (§2.6), τ is labelled
causal for the reward rule only if attribution is credited and no sorting is detected; otherwise it is a descriptive
discontinuity.

**Clustering (round 1, item 2).** Fixture-day group (`category_aware`: `ml_panel.dep_group`, event ∪ parentEventId ∪
negRisk ∪ series × UTC day ∪ underlying, per `DEPENDENCE_CLUSTERING_ANALYSIS.md` §5) and **6-hour UTC block** of
`received_utc` (replacing capture UTC date, which gave about 12 clusters in the dev window); p = the max over the two
ways; the 12-hour block dependence check (§2.3) is binding. Season-level grouping (S1) reported. R2 uses the same ways
(the fixture-day group of the quoted market and the 6-hour block of the quote time) and the same 12-hour check.

**R2 (economic; single stage on replication-window data, registered only if R1 advances with τ > 0, reward attribution
credited and no sorting detected).** R2 has no Stage 1, so a pass is labelled "single-stage result on post-freeze data,
unreplicated (L1)", not L2-dev, though it is counted in the Stage-2 Holm k. At the first
sweep of each replication pass, the `cb6_followup/` stratum (seeded sample of ≤ 200 rewarded, non-sports, non-weather
binary markets with folded x in [0.84, 0.96), two-sided, spread ≤ 0.10, swept, open, `end_date > t + 8 h`; about 60% from
[0.90, 0.96) and 40% from [0.84, 0.90)). One 5-share bid and one 5-share ask at the touch, life 2h. **Queue fill** (as CB3
§2.1: cumulative opposite-aggressor volume at or through the price reaches the displayed size at entry + 5) from the
follow-up windowed prints `(t, t + 2 h]`; touch rule bracket binding. Mark: the mid of the first **tight** observation
(two-sided, spread ≤ 0.05) of the market at or after `t_fill + 2 h` (next pass sweep or capture; up to `t_fill + 6 h`),
unavailable otherwise. `net = mark-out + rebate(q)`. Statistic: mean net per filled share in [0.90, 0.96), test > 0.
**Band attribution (binding):** the same net in [0.84, 0.90) must be lower (sign of the difference only; no significance
needed). **Worst case (binding):** unavailable marks → only the side with the lower mark-out fills, marked at the far
touch at the next observation, no rebate (as CB3 §2.1). Hold-to-resolution net reported.

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **R1** | mechanism | rewarded market-capture, x ∈ [0.87, 0.895) ∪ (0.905, 0.93] | donut spread discontinuity τ at x = 0.90 | Stage 1 two-sided; Stage 2 in the Stage-1 sign |
| **R2** | economic (single stage, post-freeze, L1) | filled paper touch quote, x ∈ [0.90, 0.96) | mean net per filled share | > 0 |

**Binding gates.** GR (§2.7); fake-cutoff placebo, reward attribution and the sorting check (§2.6); wider-donut and
tick-stratified robustness (§2.6 (ix)); 12-hour block check (§2.6 (xi)). **If R1 advances with τ < 0** ("narrower above": one-sided quoters convert to two-sided), R1 still goes to
Stage 2 as a mechanism replication, but R2 is **not** registered: the route premise (less competition above 0.90) is then
contradicted, and CH71's route is closed.

**MDE (assumptions; census replaces).** About 18,800 rewarded markets per capture (CB1 §0.1), about 60% non-sports, perhaps
4% within the window: about 450 market-captures per capture, about 62,000 over about 138 dev captures, heavily repeated
within markets. With an effective cluster-adjusted n of about 2,000 per side and spread SD ≈ 2c, SE(τ) ≈ 0.09c and the
**two-sided Stage-1 MDE ≈ 0.3c** (z 2.58 + 0.84), equal to the floor. **Round-1 caveat:** the donut removes perhaps a
sixth of the window and the estimate extrapolates across it, and the 6-hour-block way (G ≈ 46) and 12-hour check
(G ≈ 23, CR2) will widen SE; the true MDE is likely 0.4-0.5c, above the floor. The census recomputes it; the floor is
not changed. R2 (Stage 2): about 120 shadow-band markets per pass
× 2 quotes × 8% queue fills × 12 passes × 21 days ≈ 4,800 fills; per-fill SD ≈ 1.5c, design effect 3: SE ≈ 0.04c,
**MDE ≈ 0.14c**, below the 0.25c floor, which binds.

**What would kill CH71.** GR fails; R1 not detected; the fake-cutoff placebo fails (heaping or curvature); unrewarded
markets jump as much (not the reward rule); sorting detected at 0.90; wider donut or tick strata disagree; the 12-hour
block check fails; τ < 0 (route premise contradicted); R2 ≤ 0 after the halved rebate or the worst case; R2 not better
than the comparison band.

**Verdict map.** R1 (τ > 0, credited, no sorting) replicated and R2 passed → "reward-shadow band: wider spreads above
0.90 (development-replicated, L2-dev, intent-to-treat) and a net-positive modelled touch maker (single stage,
unreplicated, L1)" → Stage P-R. R1 replicated only → "the 0.90 reward cutoff moves spreads (sign s), no
maker route shown". R1 not detected → "no spread discontinuity at 0.90 at MDE x".

**Stop rule.** No R1 advance → q0133 is not committed and the `cb6_followup/` step is not deployed.

### CB6-C: Where the fills are (CH77), measurement

**Question.** Do public capture fields beyond volume and liquidity improve the out-of-sample prediction of whether a
market prints at least once in the next 2 hours?

**Why new / overlap.** HB2 and MC1 model price moves; D1 counted non-trading markets descriptively. No AREPO model targets
print occurrence. The measurement is a fill-capacity input, not a signal; it is never read as edge. The trade samples are
also read by `flow_screen` and E007 (their own outputs); CB6 reads only its own `printflag/` table.

**Unit.** (market j in the pass-i trade sample, features from capture i−1). Target `z = 1` iff ≥ 1 taker print on either
token in `[r_{i−1}, r_{i−1} + 2 h)`, `r_{i−1}` = j's `received_utc` in capture i−1. Available iff the pass-i sample's
request time is ≥ `r_{i−1} + 2 h` and either the newest stored print is older than the window start, or the window
contains a print, or the 500 stored prints reach back before the window start (otherwise unavailable, counted). The
sample is a probability sample of capture i's frame with recorded inclusion probabilities (`trade_sample.py`).

**Features (all as of capture i−1; sidecar from 2026-10-11T12:00Z).**
- **Baseline B0:** `log(1 + volume24hr)`, `log(1 + liquidity)`, spread, `|mid − 0.5|` band, `fee_category`.
- **Added block A:** `volume24hr` rank within the capture (UI list position), age `r − created_at` (days, log), hours to
  scheduled `end_date` (log, capped at 365 d), `|oneHourPriceChange|`, event size (markets sharing the event or
  neg-risk id in the capture), series membership (`series_slugs` non-empty), `competitive`, rewards flag.
- **Model (declared):** logistic regression; continuous features enter as natural cubic splines with 4 knots at dev-window
  quintiles (knots frozen with the coefficients); `fee_category` as fixed effects; L2 penalty λ = 1e-4 (fixed, no tuning).
  B0 and B0 + A are fitted on the same dev units (q0129); coefficients, knots and the code hash are written to
  `model_specs/cb6_C_frozen.json` and committed **before `T6_rep_start`** (if later, the evaluation window starts at the
  first pass ≥ that commit + 2h, and ends 14 days later).

**M1 statistic.** On the evaluation window, `ΔLL = mean_u [ℓ_B0(u) − ℓ_B0+A(u)]` (log loss in nats per unit, unweighted),
test > 0. Clustering (round 1, item 2): fixture-day group and **6-hour UTC block** of `r_{i−1}` (max p; about 56 blocks
in the 14-day window, where capture UTC date gave 14, below the small-G limit), plus the binding 12-hour block check
(about 28 blocks, CR2). The design-weighted ΔLL (1 / inclusion probability) must have the same sign (binding
robustness, added to §2.6 (iii)).

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **M1** | measurement | sampled market-capture, evaluation window | ΔLL of B0 + A over B0, frozen models | > 0 |

**Reported.** Print rate by decile of the B0 + A score vs the B0 score; the share of all evaluation prints that fall in
each model's top decile; calibration curve; fill-rate translation (expected queue fills per quote by decile, using the
CB3/CB6 fill rules where follow-up data exist). Per-feature ablations are descriptive (`cb6_descriptive`).

**MDE.** About 2,000 units per pass × 12 passes × 14 days ≈ 336,000 evaluation units; with a per-unit ΔLL SD of about 0.1
nats, the time way now has only about 56 blocks (28 in the 12-hour check), so SE is set by block-to-block variation of
ΔLL and is likely 0.001-0.002. **The 0.005-nat floor most likely binds, not the SE.** The binding robustness and the
calibration placebo (now judged on p alone, §2.6) carry the falsification.

**What would kill CH77 as a capacity tool.** M1 below the floor; the market-disjoint check loses sign (the gain is
memorised market identity, which does not transfer to new listings); the permutation calibration advances.

**Verdict map.** Adopted → every later maker registration states its fill model (§2.10). Not adopted → "public UI fields
add no fill predictability beyond volume and liquidity at floor 0.005 nats".

### CB6-F: Data jobs

**`h8_tail` fetch (q0120; the urgent job).** Entry point `scripts/run_cb6.py tail-fetch`, built on
`history_backfill` primitives (`fetch_frame`, the CB1 weighted sampler, `fetch_prices`, windowed prints as
`large_trade_census.anchor_trades`, `event_study.first_trade_lookups`). Parameters (all fixed here and in the rules file):
- **Frame** (`frame-v2-random-windows`, 1 random 15-minute window per day per walk): closed markets by `end_date` over
  `[2025-09-01, T_fetch8 − 7 d]`, and active markets by `end_date` over the same range (ended but not yet closed:
  they stay in the frame and become censored units, so censoring is counted, not hidden). **The draft's forward walk
  `(T_fetch8, T_fetch8 + 400 d]` is removed** (round 1, item 4): it admitted early-resolved markets with a future
  `endDate`, a set selected on the outcome. Capped windows (2,000-row offset cap) are excluded entirely and counted
  (h5 rule). `frame_row(..., with_text=True, with_outcomes=True)` plus new columns: `description` (first 4,000
  characters), **`neg_risk_market_id`** (Gamma `negRiskMarketID`; the current `frame_row` keeps only a `neg_risk` flag),
  **`series_ids`** (ids of `events[0].series`, `;`-joined; empty if none) and all event ids (`event_ids`, `;`-joined;
  `event_id` stays the first). `outcomePrices`, `umaResolutionStatus` go only to `outcomes_guarded.csv.gz`.
- **Completeness:** `created_at ∈ [2025-09-01, 2026-07-31]`, `end_at ≤ T_fetch8 − 7 d`, binary, not weather (fee
  category or `TEMP_RE`), not crypto "Up or Down", scheduled life ≥ 14 d.
- **Exclusions (by id and by key; every file pinned by sha256 in the rules file, any missing or mismatched file →
  refuse):** h1_first, h2_main, h3_power `sample.csv.gz`; `seals/h5_cb1_SEAL.json` and `seals/h5_cb1_ladders_SEAL.json`
  file tables (market ids from `prices/<id>.csv.gz` names, as CB4). Their event, neg-risk and series keys come from a
  Gamma lookup by market id (§1.3); frame markets sharing any key are removed before sampling. h7 overlaps (id and key)
  are dropped at seal (§1.3).
- **Smoke test before the q0120 commit (round 1, q0120 condition).** `run_cb6.py tail-smoke`: 20 closed markets drawn
  (seed `arepo-h8-smoke`) from the h1/h2/h3 exclusion ids with `end_at` in 2025 (worn markets, never in h8). For each,
  one `prices-history` request at fidelity 60 over a 10-day window ending 2 days before `end_at`. **PASS iff ≥ 18 of 20
  return ≥ 80% of the expected hourly points with median spacing within 3,600 ± 300 s.** Output: counts only
  (`tail_smoke.json`); no price is stored or analysed. FAIL → q0120 is not committed; a different fidelity or source
  is a design change needing review, and the deadline is not moved.
- **Sample:** 4,500 markets, strata status × `cb1_topic` × creation month, weights other non-sports 1.0, sports 0.5,
  seed `arepo-h8-tail`; `inclusion_prob` and `sample_weight` stored. **No price-, volume- or outcome-based selection.**
- **Origins:** drawn at fetch time from `created_at`/`end_at` only (§CB6-T), ≤ 3 per market, stored in `origins.csv.gz`
  before any price request.
- **Prices:** per origin one CLOB `prices-history` request at fidelity 60 over `[t − 8 d, t + 2 d]` (inside the 14-day
  window limit); stored as hourly points.
- **Prints:** per origin a windowed `/trades?market=<cid>&start&end&takerOnly=true` request over `[t − 30 d, t + 6 h]`,
  limit 1,000, ≤ 3 pages; `window_truncated` recorded. Wallets hashed in memory.
- **Wallet ages:** the fetcher applies the frozen rule (iii) to the stored prints (no outcome involved) and looks up the
  first trade of each distinct qualifying buyer (one `/activity` request each, cached); raw addresses never written.
- **Cap:** every stored point and print `ts ≤ min(T_fetch8, T_seal)`; dropped counts per market. No chunk starts at or
  after `T_seal`; incomplete at `T_seal` → `not_run_deadline`.
- **Size:** ≈ 39k requests (frame somewhat below the draft's ≈ 6k without the forward walk, ≈ 13.5k price, ≈ 14k print,
  ≈ 5k wallet, plus ≈ 300 exclusion-key lookups at ≤ 50 ids per request), ≈ 3.5 h wall in 90-minute chunks; disk
  ≤ 0.12 GB; RAM ≤ 0.8 GB. If the eligible frame holds fewer than 4,500 markets, all are taken (recorded).

**`h8_tail` seal (q0121).** `run_cb6.py tail-seal`: per-file sha256, listing sha256, request clocks, capped-window and
cap-drop counts, the event-level re-check against `exclusion_keys.csv.gz` (residual drops, expected 0), the h7 drop
list (ids from committed h7 seal copies, plus markets sharing their event / neg-risk / series keys via a light Gamma
lookup at ≤ 2 rps), the SCREEN/HOLDOUT split file and its hash, the read location (§2.8), git commit, seal time. Appends one `history_seal_declaration` trial line, creates `ACCESS_LOG.jsonl`. The coordinator commits
the copy `docs/research_lab/seals/h8_tail_SEAL.json` before q0125.

**Extractor v5 backfill (q0122)** for `band/` and `printflag/` from `T6_dev_start` (host raw, else release copies
streamed one at a time); pass step afterwards.

**Conversion probe (q0123)** and **dev fetch (q0124)**: §CB6-N. Dev fetch size: unknown conversion count; at about 30
qualifying conversions a day, about 500 conversions × about 3 paged requests + about 400 RPC log requests ≈ 2k requests,
under 30 min at 2 rps.

**`cb6_followup/` pass step (R2 only):** deployed only if R1 advances with τ > 0, credited and without sorting; ≤ 200 markets ×
≤ 3 pages per pass, budget 3 minutes, failure never affects the pass.

---

## 4. Code needed

### 4.1 Modules

- `backend/astrolabe/research_lab/cb6_tail.py` (CH60)
  - `RULES` (loaded from and hashed against `seals/cb6_tail_rules.json`), `class_d(question, description)`,
    `has_clarification(description)`.
  - `draw_origins(market_id, created_at, end_at, t_fetch, seed)` (Monday grid, ≤ 3, no price input).
  - `exclusion_keys(files, pins, gamma)` (sha256 check of every file, market ids, Gamma key lookup, unverified share),
    `drop_by_keys(frame, keys)`, `smoke_prices(...)` (counts only).
  - `unit_eligibility(points, prints, t)` (open, longshot side, band, 7-day print rule with truncation states, point at
    `t − 7 d`); `features(points, prints, wallet_first, t)` → (i)-(iv), F, availability.
  - `delta_t1(units, bands)`, `t1_logit(...)`, `t1_test(units, ways)` (YES-cluster minimum, small-G), `calibrated_null(...)`
    (one draw per event, neg-risk members mutually exclusive, floors off), `class_shuffle(...)`.
  - `t2_orders(units, prints, cost_regime)` (modelled ask, trade-through and touch fills, `a_AS`, +0.75c, rebate halved),
    `tail_gate(...)` (reuse CB1 `tail_bound`), `px1_bound(...)` (reuse CB1), `breakeven_t2(...)`, `censor_worst_case(...)`,
    `truncation_worst_case(...)`, `carry_rule(t1, t2)`.
  - Fetch side: `tail_fetch(...)` (frame with `description`, sampler, origins file, prices, windowed prints, wallet
    lookups, cap, deadline, resumable chunks), `tail_seal(...)` (split file, h7 drop list).
- `backend/astrolabe/research_lab/cb6_conv.py` (CH66)
  - `rpc_logs(start_block, end_block, address, topic, endpoints)`, `decode_conversion(log)` → (ts, stakeholder hash,
    neg-risk id, index set, amount), `probe(...)`.
  - `member_prints(event, window, limiter)` (comma-separated `market=` paging), `dumps(conv, prints)`,
    `sell_bursts(prints, member)`, `match_controls(...)`, `recovery(...)`, `n1_test(units, ways)`, `pseudo_episodes(...)`.
  - `n2_bids(...)` (every received member, `t_post = t_conv + 60 s`, `q` from the last bid-side print with `ts < t_post`,
    marketable check, tick from metadata, trade-through and touch fills, exit window, fee, rebate, worst case),
    `breakeven_n2(...)`.
- `backend/astrolabe/research_lab/cb6_band.py` (CH71)
  - `folded_x(bid, ask)`, `rd_local_linear(df, cutoff, h, donut, kernel="triangular")`, `r1_test(...)` (fixture-day and
    6-hour ways, 12-hour check, small-G), `fake_cutoffs(...)` (same donut), `diff_in_disc(...)`, `tick_strata(...)`,
    `mccrary(..., donut)` at real and fake cutoffs (sorting check).
  - `followup_stratum(sweep_rows, seed, n_max)`, `r2_quotes(...)` (queue and touch fills, tight mark, worst case, rebate
    halved, band attribution), `breakeven_r2(...)`.
- `backend/astrolabe/research_lab/cb6_fills.py` (CH77)
  - `printflag_units(extract)` (availability rule), `features_b0(...)`, `features_a(...)`, `fit_frozen(...)` (splines,
    fixed λ, writes `cb6_C_frozen.json`), `delta_ll(...)`, `m1_test(...)`, `permutation_calibration(...)`,
    `market_disjoint(...)`, `deciles(...)`.
- `backend/astrolabe/research_lab/cb6_declaration.py`: `HYPOTHESES_CB6`, `declaration_sha256()` covering every population,
  window, rule, regex, threshold, floor, gate, cutoff, bandwidth, seed, date, the carry rule and the Polygon endpoint list.
- Shared statistics are **imported, not copied**: CB1/CB2/CB4/CB5 cluster gate, bootstrap, small-G p, tail bound, PX1
  bound, `queue_fill`, break-even placebo frame, `log_trials`, census guard, CB4's release-stream reader,
  `cost_regimes.cost_regime`, `economics.REBATE_SHARE`, `ml_panel.dep_group`.

### 4.2 Runner

`backend/scripts/run_cb6.py {tail-smoke,tail-fetch,tail-seal,conv-probe,conv-fetch,census,screen,fit-C,holdout,rep-fetch,
replicate,eval-C} --family T|N|R|C`.
- Refuses the run ids and roots of §1.3; writes only under `research_lab/creative_batch6/` and `history/h8_tail/`
  (fetch and seal only).
- `tail-fetch` refuses unless the committed rules-file hash matches, **every exclusion file (h1/h2/h3 samples and both h5
  seal copies) exists and matches its sha256 pinned in the rules file**, `tail_smoke.json` records PASS, data-dumps
  ≤ 10 GB (host runs), and the clock is before `T_seal`; marks `not_run_deadline` at `T_seal`.
- Every command that counts trials runs the `trials.jsonl` union step first (§2.5) and records the post-union count.
- Declaration-hash guard (committed `model_specs/cb6_v1.json` must equal the code's hash) on `census`, `screen`, `fit-C`,
  `holdout`, `replicate`, `eval-C`.
- `census --family T` and `screen --family T` read SCREEN only; `holdout` refuses until the Stage-1 T results file is
  committed with T1 advanced or T2 carried. `screen --family T --tests T2` refuses until `cost_regimes_v1.json` is
  committed.
- Every analysis loader drops rows timed in the pinned J4-R window. `T6_rep_start` is read from its pinned committed
  file. `eval-C` refuses unless `cb6_C_frozen.json` was committed before the evaluation window's first pass.
- `replicate --family R` refuses before `T6_R_rep_end + 12 h`; `replicate --family N` before `T6_N_rep_end + 3 h`.
- Results are never overwritten.

### 4.3 Extractor addition (`creative_batch1.py`, version `cb1-extract-v5`; no change to `arepo_pass.sh`)

- Own root `research_lab/cb6_extract/` and manifest. CB1-CB5 tables stay byte-identical (test). If CB5's v4 has not landed
  first, CB6's tables go into the next version in one change.
- `band/<capture_id>.csv.gz`: binary rows with folded x in [0.55, 0.99]: `capture_id, received_utc, market_id,
  condition_id, event_id, neg_risk_market_id, parent_event_id, series_slugs, fee_category, best_bid, best_ask,
  volume24hr, liquidity, accepting_orders, end_date, order_price_min_tick_size, clob_rewards, rewards_max_spread,
  rewards_min_size` plus first-sweep `best_bid, best_ask, bid_size_1, ask_size_1, depth_1c, depth_5c` (blank if not swept).
- `printflag/<pass_id>.csv.gz`: per market in the pass-i trade sample: `pass_id, condition_id, market_id, inclusion_prob,
  stratum, request_ts, r_prev, n_prints_window, newest_ts, oldest_ts, n_stored, available`, plus the capture-(i−1)
  feature columns of §CB6-C. No wallet field.
- Backfills use `--release-stream`. The 10-minute and 500 MB pass limits hold.

### 4.4 Follow-up step (`cb6_followup.py`, pass hook; deployed only for R2)

Writes `cb6_followup/<pass_id>/{stratum.csv.gz,trades.csv.gz,manifest.json}`; the stratum is drawn from the pass's first
sweep with seed `arepo-cb6-fu|<pass_id>`; trades for the previous pass's stratum by windowed taker-only paging; hashed
wallets only; budget and failure isolation as CB3's follow-up step.

### 4.5 Tests (`backend/tests/unit/test_cb6_tail.py`, `test_cb6_conv.py`, `test_cb6_band.py`, `test_cb6_fills.py`)

- **Tail.** The class regex reproduces CH60's lists exactly (fixtures: "court rules" → D; "price above" → not D; "strike
  price" → not D; neither in question → description used). Clarification markers exclude. Origins depend only on
  `created_at`/`end_at` (a planted price or outcome change leaves them unchanged) and are ≤ 3 Mondays inside the scheduled
  life. A point stamped 9 minutes before t is not usable; 10 minutes is. Feature (iii) uses prints strictly before t; a
  truncated window yields unavailable, never false. Wallet age uses the first trade at or before the print. F is a
  disjunction; an unavailable (iii)/(iv) with (i) true gives F = 1. Δ is band-weighted. The calibrated-null placebo
  draws once per event, never gives two YES members of one neg-risk event, keeps each unit's mean at its own price, runs
  with floors off, and gives about 1% advances on a no-effect fixture with heavy within-event repetition, and far more
  when clustering is (wrongly) set to the unit. The fetcher refuses when any exclusion file is missing or its sha256
  differs from the pin; a frame market sharing an event id, `negRiskMarketID` or series id with an exclusion market is
  removed before sampling; > 2% exclusion ids without metadata → "disjointness unverified"; no frame market has
  `end_at > T_fetch8 − 7 d`; the frame keeps `event_ids`, `neg_risk_market_id`, `series_ids`; the smoke test stores
  counts only and its PASS rule is 18/20. A 50-50 resolution enters Δ with Y = 0.5. The censoring worst case is
  binding. T2 fills only on trade-through; the touch bracket; `a_AS` only before
  the rollout; censored fills as losers. The fetcher refuses after `T_seal`, writes `not_run_deadline`, caps rows, never
  writes raw addresses, and stores outcomes only in the guarded file. The split keeps neg-risk members together and the
  runner refuses HOLDOUT before the Stage-1 file exists.
- **Conv.** Log decoding on a recorded fixture; stakeholder matching by hash; index-set → received members. A dump print
  before the conversion's block time is impossible (ordering rule). Recovery uses bid-side non-converter prints only.
  Controls come from `[t_conv − 24 h, t_conv − 6 h]` with notional in [0.5, 2]×. Pseudo-episodes stay inside the fetched
  window and pick the burst nearest `V_d` in notional; on a fixture where every burst of that size reverts by
  construction (generic effect only), the pseudo-episode placebo advances (it can fail) and N1 is blocked. **N2 is
  causal:** a planted converter sell after `t_post` leaves the bid set and every `q` unchanged; `q` uses only prints
  with `ts < t_post`; a bid is posted on every received member with a prior bid-side print; marketable bids are not
  posted; on a fixture with no price move, N2's fill rate is below 100% and its mean net is ≤ 0 after the fee. A window
  that hit the 10-page cap makes all its units unavailable. `takerOnly` side mapping (SELL YES = BUY NO at `1 − p`).
- **Band.** Folded x; x = 0.90 is "below". Local linear RD recovers a planted jump and gives none on a smooth fixture.
  **Tick-parity fixture:** 1c ticks, a spread smooth in x except for the parity rule (whole-cent mid → even spread,
  half-cent → odd); the no-donut estimate shows a jump at 0.90 and at the fake cutoffs, the donut estimate shows none at
  either. Fake cutoffs are 0.60..0.83 with the same donut and never overlap [0.87, 0.93]; on a fixture with heaping at
  whole cents and no reward effect, the fake-cutoff placebo fails. Sorting check fires on a fixture with excess mass
  just below 0.90 only. 6-hour and 12-hour block ids from `received_utc`. Diff-in-disc; wider donut; tick strata.
  Census accessor returns no spread. Queue and
  touch fills; tight mark; worst case; band attribution sign.
- **Fills.** Target availability (500-print visibility cases). Features as of capture i−1 only (a planted change in
  capture i leaves them unchanged). Splines and λ fixed; frozen file hashed; evaluation refuses a model committed after
  the window start. Market-disjoint subset excludes every market seen in the fit window. Permutation within (capture ×
  decile) cells, judged on p < 0.05 with the floor off, threshold 7.5%.
- **Runner.** Refusals (run ids, roots, J4-R rows, before freeze, before register, before Stage-1 file, before window ends);
  `KIND_RULES` has the CB6 kinds and the counter runs on the real `trials.jsonl`.

---

## 5. Draft queue specs

Paths follow `queue/README.md` (`argv[0]` under `backend/scripts/`, `cwd` `backend`). No spec is committed before its
code and tests exist; analysis jobs also need the reviewed CB6 freeze commit. q0120 needs only the fetcher freeze check,
the committed rules file (every threshold and the exclusion-file sha256 pins in it), a smoke-test PASS and the headroom
precondition (no Mac fallback, §2.8); it may be queued before the CB6 freeze.

```json
{"id": "q0120_h8_tail_fetch", "title": "CB6-T: h8_tail backfill (4,500 binary markets created 2025-09..2026-07, scheduled end <= T_fetch8 - 7 d, disjoint from h1/h2/h3/h5 by market id and by event / negRiskMarketID / series key; description, hourly prices and windowed prints around <= 3 declared origins, large-buyer first-trade times; capped at T_seal)",
 "family": "history_data", "priority": 61, "expected_value": "fresh market- and event-disjoint data for the CH60 ex-ante tail classifier; must complete before T_seal",
 "data": ["public Gamma/CLOB/Data API", "history/h1_first, h2_main, h3_power sample.csv.gz (exclusion ids only; sha256 pinned in the rules file)", "docs/research_lab/seals/h5_cb1_SEAL.json and h5_cb1_ladders_SEAL.json file tables (ids only; sha256 pinned)", "docs/research_lab/seals/cb6_tail_rules.json (hash-checked)", "research_lab/creative_batch6/tail_smoke.json (PASS required)"],
 "resources": {"mem_mb": 800, "cpu": 1, "network": "gamma-api, clob, data-api", "lane": "net"},
 "depends_on": ["q0018_h5_cb1_seal"],
 "argv": ["scripts/run_cb6.py", "tail-fetch", "--run-id", "h8_tail", "--seed", "arepo-h8-tail", "--n-markets", "4500", "--created-from", "2025-09-01", "--created-to", "2026-07-31", "--end-before-fetch-days", "7", "--windows-per-day", "1", "--max-origins", "3", "--price-fidelity", "60", "--print-pages", "3", "--exclude-runs", "h1_first,h2_main,h3_power", "--exclude-seal-ids", "../docs/research_lab/seals/h5_cb1_SEAL.json,../docs/research_lab/seals/h5_cb1_ladders_SEAL.json", "--exclude-event-keys", "event,neg_risk_market,series", "--max-unverified-key-share", "0.02", "--exclude-categories", "weather", "--rules", "../docs/research_lab/seals/cb6_tail_rules.json", "--require-smoke", "research_lab/creative_batch6/tail_smoke.json", "--cap-at", "2026-10-22T00:00Z", "--rps", "4", "--disk-cap-gb", "0.12", "--budget-min", "90"],
 "timeout_s": 6600, "max_retries": 3, "repeat": {"max_runs": 8, "until_log_regex": "\"status\": \"(tail_fetch_complete|not_run_deadline|disjointness_unverified)\""},
 "outputs": ["data-dumps/research_lab/history/h8_tail/{frame.csv.gz,exclusion_keys.csv.gz,key_drops.json,sample.csv.gz,origins.csv.gz,prices/,trades/,wallet_first.csv.gz,outcomes_guarded.csv.gz,progress.jsonl,frame_report.json,request_clock.json,manifest.json}"],
 "next_action": "q0121 after both h7 runs are terminal",
 "notes": "CREATIVE_BATCH_6.md CB6-F (revised after challenger round 1). May be committed before the CB6 freeze once the fetcher freeze check passes, the rules file (all thresholds, exclusion-file sha256 pins) is committed and tail-smoke PASSed. About 39k requests, about 3.5 h wall in 90-min chunks so the T_seal-bound q0043/q0081/q0082 (also priority 61, lower ids) win the net lane at every boundary. Terminal states: tail_fetch_complete; not_run_deadline if incomplete at T_seal 2026-10-22T00:00Z (NOT_RUN_DEADLINE.json; no seal, no analysis, no refetch, cap unchanged); disjointness_unverified if > 2% of exclusion ids lack Gamma metadata (T1/T2 not testable, counted). Refuses (exit 2) on a rules-file hash mismatch, ANY missing or sha256-mismatched exclusion file, missing smoke PASS, data-dumps > 10 GB, run ids h3_power/h4_seal/h5_cb1/h5_cb1_ladders/h6_weather/h7_*. Event-level exclusion applied to the frame before sampling. Origins drawn from created_at/end_at only and written before any price request. Outcome fields only in outcomes_guarded.csv.gz. Raw wallet addresses never written. Commit message must record the section 2.8 headroom check (1.0 GB/day); host only (the Mac fallback was removed 2026-10-17, section 2.8): if q0120 cannot complete on the host before T_seal it is recorded not_run_deadline."}
```
```json
{"id": "q0121_h8_tail_seal", "title": "CB6-T: h8_tail seal (listing hash, event-level disjointness re-check, h7 id and key overlap drop list, SCREEN/HOLDOUT event-hash split, read location)",
 "family": "history_data", "priority": 58, "expected_value": "sealed, split h8_tail before any CB6-T read",
 "data": ["history/h8_tail", "docs/research_lab/seals/h7_cb4_era_SEAL.json, h7_cb4_series_SEAL.json (ids only, if committed)"],
 "resources": {"mem_mb": 500, "cpu": 1, "lane": "cpu", "network": "gamma-api"},
 "depends_on": ["q0120_h8_tail_fetch"], "argv": ["scripts/run_cb6.py", "tail-seal", "--run-id", "h8_tail", "--split-seed", "arepo-cb6-tail-split", "--h7-seals", "../docs/research_lab/seals", "--recheck-keys", "--rps", "2"],
 "timeout_s": 1800, "max_retries": 1, "outputs": ["data-dumps/research_lab/history/h8_tail/{SEAL.json,split.csv.gz,h7_drop.csv.gz,key_recheck.json,ACCESS_LOG.jsonl}", "trials.jsonl (history_seal_declaration)"],
 "next_action": "coordinator commits docs/research_lab/seals/h8_tail_SEAL.json", "notes": "refuses until both h7 runs are terminal (sealed or not_run_deadline); never runs on a not_run_deadline or disjointness_unverified h8; h7 key lookup by market id (parse guard: ids and keys only); records the read location (section 2.8)"}
```
```json
{"id": "q0122_cb6_extract_backfill", "title": "CB6-F: extractor v5 band/ and printflag/ from captures, sweeps and trade samples since 2026-10-11T12:00Z (host raw, else release copies)",
 "family": "creative_batch_6", "priority": 56, "expected_value": "R and C inputs preserved without a retention gate",
 "data": ["research_lab/snapshots rows + rows_ext, book_sweeps, trade_samples (host, else verified release copies)"], "resources": {"mem_mb": 900, "cpu": 1, "lane": "cpu"},
 "depends_on": [], "argv": ["scripts/run_cb1_extract.py", "--backfill-from", "2026-10-11T12:00Z", "--tables", "band,printflag", "--release-stream", "--budget-min", "150", "--disk-cap-gb", "0.18"],
 "timeout_s": 10800, "max_retries": 2, "repeat": {"max_runs": 6, "until_log_regex": "backfill_complete"},
 "outputs": ["data-dumps/research_lab/cb6_extract/{band/,printflag/,manifest.json}"], "next_action": "pass step continues (extractor v5)",
 "notes": "idempotent by capture/pass id; CB1-CB5 tables untouched; printflag is calendar-bound (trade-sample raw kept 3 days): deploy the pass step first; passes with no raw and no verified release copy are counted missing"}
```
```json
{"id": "q0123_cb6_conv_probe", "title": "CB6-N: chain-source probe (neg-risk conversion logs, 20 random conversions, stakeholder-hash and index-set checks; counts only)",
 "family": "creative_batch_6", "priority": 44, "expected_value": "whether conversion episodes can be identified from public logs",
 "data": ["Polygon public JSON-RPC (keyless)", "public Gamma, Data API"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu", "network": "polygon-rpc, gamma-api, data-api"},
 "depends_on": [], "argv": ["scripts/run_cb6.py", "conv-probe", "--day", "2026-10-12", "--n", "20", "--seed", "arepo-cb6-probe", "--rps", "2"],
 "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch6/conv_probe.json", "trials.jsonl (cb6_descriptive)"],
 "next_action": "PASS (>= 16/20): q0124 after T6_dev_end; FAIL: N1/N2 not testable (source)", "notes": "adapter address and event topic pinned from the Polymarket contracts page at probe time; prints counts only; hashes only"}
```
```json
{"id": "q0124_cb6_conv_dev_fetch", "title": "CB6-N: dev-window conversions and member prints [t_conv-96h, t_conv+3h] (excluding the J4-R window)",
 "family": "creative_batch_6", "priority": 44, "expected_value": "episodes, targets, controls and pseudo-episode windows for the CH66 screen",
 "data": ["Polygon public JSON-RPC", "public Gamma (guarded)", "public Data API windowed trades"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu", "network": "polygon-rpc, gamma-api, data-api"},
 "depends_on": ["q0123_cb6_conv_probe"], "argv": ["scripts/run_cb6.py", "conv-fetch", "--window", "dev", "--max-members", "40", "--rps", "2", "--disk-cap-gb", "0.06"],
 "timeout_s": 5400, "max_retries": 2, "outputs": ["research_lab/creative_batch6/conv_dev/{conversions.csv.gz,members.csv.gz,prints/,manifest.json}"],
 "next_action": "q0125", "notes": "commit after 2026-10-28T03:00Z and probe PASS; raw addresses hashed in memory; outcome fields dropped at parse"}
```
```json
{"id": "q0125_cb6_census", "title": "CB6: pre-freeze census (T on SCREEN only: eligibility, flags, expected YES, GT; N: episodes, availability, GN; R: counts by side, density, GR; C: units, coverage, GC)",
 "family": "creative_batch_6", "priority": 40, "expected_value": "gates and MDEs before the freeze; no target, net, mark-out, spread-at-cutoff or log loss",
 "data": ["history/h8_tail SCREEN block (verified seal)", "creative_batch6/conv_dev", "cb6_extract/{band,printflag} (dev window, J4-R excluded)"], "resources": {"mem_mb": 1500, "cpu": 1, "lane": "cpu"},
 "depends_on": ["q0121_h8_tail_seal", "q0122_cb6_extract_backfill", "q0124_cb6_conv_dev_fetch"], "argv": ["scripts/run_cb6.py", "census", "--family", "T,N,R,C"],
 "timeout_s": 5400, "max_retries": 1, "outputs": ["research_lab/creative_batch6/census.json", "trials.jsonl (cb6_descriptive)"],
 "next_action": "Claude session: insert counts and gates here; science-reviewer; freeze (model_specs/cb6_v1.json); pin T6_rep_start", "notes": "outcome guard; HOLDOUT never opened; floors never revised from the census; if h8 is not_run_deadline the T part records that and the rest proceeds"}
```
```json
{"id": "q0126_cb6_screen_T", "title": "CB6-T: Stage-1 screen on h8_tail SCREEN (T1 flag excess; T2 unflagged paper ask; calibrated-null, class-shuffle and break-even placebos; tail gate; worst cases)",
 "family": "creative_batch_6", "priority": 38, "expected_value": "whether CH60 advances to the sealed HOLDOUT block",
 "data": ["history/h8_tail SCREEN", "model_specs/cb6_v1.json", "model_specs/cost_regimes_v1.json (T2 only)"], "resources": {"mem_mb": 1200, "cpu": 1, "lane": "cpu"},
 "depends_on": ["q0125_cb6_census"], "argv": ["scripts/run_cb6.py", "screen", "--family", "T", "--block", "SCREEN", "--n-boot", "2000"],
 "timeout_s": 5400, "max_retries": 1, "outputs": ["research_lab/creative_batch6/T_screen/results.json", "trials.jsonl (2 cb6_test + count line + placebos + descriptive)"],
 "next_action": "if T1 advanced or T2 carried: commit q0130", "notes": "commit after the freeze; runs at the h8 read location only; T2 runs only when cost_regimes_v1.json is committed (else T2 pending, T1 reported; T2 becomes not run (register missing), p = 1, counted, if the register is not committed by 2026-11-21T00:00Z); exits 0 'not testable' if GT failed, disjointness unverified or h8 not_run_deadline"}
```
```json
{"id": "q0127_cb6_screen_N", "title": "CB6-N: Stage-1 dev screen (N1 dump vs matched-sell recovery; N2 60-s maker bid; pseudo-episode and break-even placebos; worst case)",
 "family": "creative_batch_6", "priority": 38, "expected_value": "whether CH66 advances to the replication window",
 "data": ["creative_batch6/conv_dev", "model_specs/cb6_v1.json"], "resources": {"mem_mb": 1000, "cpu": 1, "lane": "cpu"},
 "depends_on": ["q0125_cb6_census"], "argv": ["scripts/run_cb6.py", "screen", "--family", "N", "--window", "dev", "--n-boot", "2000"],
 "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch6/N_dev/results.json", "trials.jsonl (2 cb6_test + count line + placebos + descriptive)"],
 "next_action": "if advanced or carried: commit q0131/q0132", "notes": "commit after the freeze; exits 0 'not testable' on probe FAIL or GN"}
```
```json
{"id": "q0128_cb6_screen_R", "title": "CB6-R: Stage-1 R1 on dev captures (RD at folded mid 0.90, rewarded; fake cutoffs 0.60-0.83; unrewarded diff-in-disc; donut; tick strata)",
 "family": "creative_batch_6", "priority": 38, "expected_value": "whether the reward cutoff moves spreads, and in which direction",
 "data": ["cb6_extract/band (dev window, J4-R excluded)", "model_specs/cb6_v1.json"], "resources": {"mem_mb": 1500, "cpu": 1, "lane": "cpu"},
 "depends_on": ["q0125_cb6_census"], "argv": ["scripts/run_cb6.py", "screen", "--family", "R", "--window", "dev", "--n-boot", "2000"],
 "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch6/R_dev/results.json", "trials.jsonl (1 cb6_test + count line + placebos + descriptive)"],
 "next_action": "if R1 advanced: deploy cb6_followup (only if tau > 0, credited and no sorting), commit q0133", "notes": "commit after the freeze; donut RD primary; time way 6-hour blocks plus 12-hour check; exits 0 'not testable' if GR failed"}
```
```json
{"id": "q0129_cb6_fit_C", "title": "CB6-C: fit the declared B0 and B0+A logistic models on dev printflag units; write model_specs/cb6_C_frozen.json (no test)",
 "family": "creative_batch_6", "priority": 39, "expected_value": "frozen fill-probability models before the evaluation window",
 "data": ["cb6_extract/printflag (dev window, J4-R excluded)", "model_specs/cb6_v1.json"], "resources": {"mem_mb": 1500, "cpu": 1, "lane": "cpu"},
 "depends_on": ["q0125_cb6_census"], "argv": ["scripts/run_cb6.py", "fit-C", "--window", "dev"],
 "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch6/C_fit/{cb6_C_frozen.json,fit_report.json}", "trials.jsonl (cb6_descriptive)"],
 "next_action": "coordinator commits model_specs/cb6_C_frozen.json before T6_rep_start", "notes": "commit after the freeze; descriptive only; no evaluation-window row exists when it runs"}
```
```json
{"id": "q0130_cb6_holdout_T", "title": "CB6-T: Stage-2 replication on the sealed h8_tail HOLDOUT block (advanced/carried T tests; Holm over the CB6 route Stage-2 set)",
 "family": "creative_batch_6", "priority": 38, "expected_value": "development replication (L2-dev, same calendar) of the ex-ante tail class",
 "data": ["history/h8_tail HOLDOUT (first read)", "creative_batch6/T_screen/results.json", "model_specs/cb6_v1.json", "model_specs/cost_regimes_v1.json"], "resources": {"mem_mb": 1200, "cpu": 1, "lane": "cpu"},
 "depends_on": ["q0126_cb6_screen_T"], "argv": ["scripts/run_cb6.py", "holdout", "--family", "T", "--n-boot", "2000"],
 "timeout_s": 5400, "max_retries": 1, "outputs": ["research_lab/creative_batch6/T_holdout/results.json", "trials.jsonl (cb6_replication + count line)"],
 "next_action": "batch Holm; ledger; Stage P-T registration if passed", "notes": "commit only if T1 advanced or T2 carried; access logged; exits 0 'nothing advanced'"}
```
```json
{"id": "q0131_cb6_conv_rep_fetch", "title": "CB6-N: replication-window conversions and member prints (rolling; each at t_conv + 3h30m)",
 "family": "creative_batch_6", "priority": 41, "expected_value": "post-freeze episodes for the CH66 replication",
 "data": ["Polygon public JSON-RPC", "public Gamma (guarded)", "public Data API windowed trades"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu", "network": "polygon-rpc, gamma-api, data-api"},
 "depends_on": ["q0127_cb6_screen_N"], "argv": ["scripts/run_cb6.py", "rep-fetch", "--family", "N", "--max-members", "40", "--rps", "2", "--disk-cap-gb", "0.08"],
 "timeout_s": 3600, "max_retries": 3, "repeat": {"max_runs": 90, "until_log_regex": "rep_fetch_complete"},
 "outputs": ["research_lab/creative_batch6/conv_rep/{conversions.csv.gz,members.csv.gz,prints/,manifest.json}"], "next_action": "q0132 after T6_N_rep_end + 3h",
 "notes": "commit only if N1 or N2 advanced or N2 was carried; rolling every 6h; no target computed by the fetcher"}
```
```json
{"id": "q0132_cb6_rep_N", "title": "CB6-N: Stage-2 replication (advanced/carried N tests; Holm over the CB6 route Stage-2 set)",
 "family": "creative_batch_6", "priority": 38, "expected_value": "development replication (L2-dev) of conversion-dump reversion",
 "data": ["creative_batch6/conv_rep", "creative_batch6/N_dev/results.json", "model_specs/cb6_v1.json"], "resources": {"mem_mb": 1000, "cpu": 1, "lane": "cpu"},
 "depends_on": ["q0131_cb6_conv_rep_fetch"], "argv": ["scripts/run_cb6.py", "replicate", "--family", "N", "--n-boot", "2000"],
 "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch6/N_rep/results.json", "trials.jsonl (cb6_replication + count line)"],
 "next_action": "batch Holm; ledger; Stage P-N if passed", "notes": "refuses before T6_N_rep_end + 3h"}
```
```json
{"id": "q0133_cb6_rep_R", "title": "CB6-R: Stage-2 (R1 replication in the Stage-1 sign on replication captures; R2 touch maker in [0.90, 0.96) with cb6_followup fills, if registered)",
 "family": "creative_batch_6", "priority": 38, "expected_value": "development replication (L2-dev) of the reward-shadow discontinuity and, if registered, a single-stage (L1) test of its maker route",
 "data": ["cb6_extract/band (replication window)", "cb6_followup/", "book_sweeps (marks)", "creative_batch6/R_dev/results.json", "model_specs/cb6_v1.json"], "resources": {"mem_mb": 1500, "cpu": 1, "lane": "cpu"},
 "depends_on": ["q0128_cb6_screen_R"], "argv": ["scripts/run_cb6.py", "replicate", "--family", "R", "--n-boot", "2000"],
 "timeout_s": 5400, "max_retries": 1, "outputs": ["research_lab/creative_batch6/R_rep/results.json", "trials.jsonl (cb6_replication + count line)"],
 "next_action": "batch Holm; ledger; Stage P-R if passed", "notes": "commit only if R1 advanced; R2 only if tau > 0, reward attribution credited and no sorting; an R2 pass is labelled single-stage unreplicated (L1), not L2-dev; refuses before T6_R_rep_end + 12h"}
```
```json
{"id": "q0134_cb6_eval_C", "title": "CB6-C: M1 on the evaluation window (frozen models; permutation calibration; market-disjoint and design-weighted checks)",
 "family": "creative_batch_6", "priority": 39, "expected_value": "a fill-capacity measurement for maker envelopes",
 "data": ["cb6_extract/printflag (evaluation window)", "model_specs/cb6_C_frozen.json", "model_specs/cb6_v1.json"], "resources": {"mem_mb": 1500, "cpu": 1, "lane": "cpu"},
 "depends_on": ["q0129_cb6_fit_C"], "argv": ["scripts/run_cb6.py", "eval-C", "--n-perm", "200"],
 "timeout_s": 5400, "max_retries": 1, "outputs": ["research_lab/creative_batch6/C_eval/results.json", "trials.jsonl (1 cb6_measurement + count line + placebo + descriptive)"],
 "next_action": "ledger; adoption note for later maker registrations", "notes": "refuses before T6_C_eval_end + 3h or if cb6_C_frozen.json was committed after the window start; labelled 'unreplicated measurement'"}
```

## 6. Test budget and compute

| Job | Tests counted | Kind(s) | Family |
|---|---|---|---|
| Routes, Stage 1: T1, T2 (h8 SCREEN), N1, N2 (dev), R1 (dev) | 5 | `cb6_test` + count lines `creative_batch_6:T` (`n_tests` 2), `:N` (2), `:R` (1) | each gated alone at p < 0.01 (R1 two-sided); BY triage |
| Routes, Stage 2 (advanced or carried; R2 enters directly) | ≤ 6 | `cb6_replication` + count lines | one Holm, one-sided α = 0.05, k ≤ 6 |
| Measurement M1 | 1 | `cb6_measurement` + count line `creative_batch_6:C` | **C**: one-sided α = 0.05, k = 1 |
| Census, flags, episodes, density, fake-cutoff tables, deciles, strata, gates | 0 | `cb6_descriptive` | - |
| **Total** | **6 fixed + up to 6 conditional = 6-12** | | cumulative ≥ 1,104 at drafting (Mac working tree; host union pending) → ≥ 1,110-1,116 |

**Host compute.** About 4-5 CPU-hours at nice 19 in total (extractor backfill largest). Peak memory 1.5 GB (census, R,
C). No two multi-GB jobs at once. **Network:** `h8_tail` ≈ 39k requests (≈ 3.5 h wall, `net`, before `T_seal`); probe and
dev conversions ≈ 2k; replication conversions ≈ 3k over three weeks; follow-up ≤ 600 requests per pass (R2 only).
**Disk:** ≤ 0.55 GB in total across all CB6 outputs (caps in §2.8).

## 7. Main scientific risks

1. **`h8_tail` may not run (T).** The `net` lane is held by q0043 (h6, about 6-9 h from 2026-10-16T23Z), then the h7
   fetches; the host is at 9.7 GB against a 10 GB job guard and grows about 0.9-1 GB a day. Without retention activation
   on the host (there is no Mac fallback, §2.8), CB6-T is "not run (deadline)" and counted. A smoke-test FAIL (fidelity-60 history unavailable
   for closed markets) would also stop it. This is the main calendar risk of the batch.
2. **Power (T).** Stage-1 MDE ≈ 3.8c on Δ, above the 2c floor; T2 is expected to be not testable for size. CB6-T can find
   only a strong class effect, and its economic answer will usually wait for Stage P.
3. **Current text and the end-date look-ahead (T).** Descriptions are current; clarifications are excluded and the bias
   is likely conservative. `end_at` read at `T_fetch8` enters the origin grid and, since round 1, the frame rule
   `end_at ≤ T_fetch8 − 7 d`; if Gamma rewrote `endDate` on early resolution this would select on YES (the census
   reports the early-closure share). CB6-T's scope is markets scheduled to end by about 2026-10-10.
3a. **Disclosed design changes from CH60 (T).** The primary, origins, frame, price fidelity and drift threshold all
   differ from the CH60 text (§1.3); C1's five worst events are not recorded anywhere and CH60's claim about their class
   is a conjecture.
4. **Same-calendar holdout (T).** HOLDOUT is market-disjoint, not time-disjoint; a regime effect in 2025-09..2026-07
   would replicate. Stage P is the out-of-time check.
5. **Source and frequency (N).** The chain probe may fail (stakeholder ≠ trading proxy), and conversions with dumps may be
   rarer than 30 a day; GN then stops CB6-N.
6. **Selection effects (N).** A dump-sized sell after a conversion may revert for generic reasons; the pseudo-episode
   placebo is designed to catch this and may leave "reversion exists, not specific to conversions".
7. **Direction and attribution (R).** The idea's mechanism was backwards (§0.3); the sign of τ is open. Heaping at whole
   cents, tick parity and tick regimes can create apparent jumps; the donut primary, the fake cutoffs with the same
   donut, the wider donut and the tick strata guard this. The reward midpoint may be size-adjusted, so τ is an
   intent-to-treat estimate of a fuzzy design; sorting at 0.90 makes it non-causal. A τ < 0 closes the route.
8. **Fill model realism (R2, N2, T2).** Trade-through and queue rules from public prints ignore cancellations and hidden
   priority; brackets (touch rule) and worst cases bound but do not remove this.
9. **The measurement may be trivially small or trivially large (C).** The floor and the market-disjoint check decide;
   the result is never a signal.
10. **Shared calendar with sealed windows (N, R, C).** CB1-D, CB3, CB4-C, CB5-L and E011 share the calendar. CB6 never
    opens their tables; the disclosures in §1.3 stand.

## 8. Next actions

1. **Today (urgent, T_seal-bound):** delegate to `implementer` the `h8_tail` fetcher (`run_cb6.py tail-smoke` /
   `tail-fetch` / `tail-seal`, `cb6_tail.py` fetch side, tests) per the round-1 spec (§10, q0120 implementer spec) and
   write `seals/cb6_tail_rules.json` from §CB6-T, §CB6-F and §1.4 (including the exclusion-file sha256 pins). Run
   `tail-smoke`. Then a `science-reviewer` freeze check of the fetcher and rules file only. Commit the rules file, then
   q0120 (recording the §2.8 headroom check at 1.0 GB/day), and deploy. If it cannot complete on the
   host before `T_seal`, it is recorded `not_run_deadline` (no Mac fallback, §2.8).
2. **Challenger round 1 is done** (§10; one challenge, one response, then proceed). No second round.
3. Extractor v5 (`band/`, `printflag/`) with the pass step; then q0122. Probe code; q0123 any time.
4. After `T6_dev_end` (2026-10-28): q0124, then q0125 census once the h8 seal copy is committed. Insert counts and gates
   here; freeze (`model_specs/cb6_v1.json`); pin `T6_rep_start`.
5. After the freeze: q0126 (T1 at once; T2 when the CB4 cost register is committed), q0127, q0128, q0129 (commit
   `cb6_C_frozen.json` before `T6_rep_start`). Commit q0130-q0133 only for advanced or carried tests; deploy
   `cb6_followup/` only if R1 advanced with τ > 0, credited and without sorting. q0134 after the evaluation window.

## 9. CB5 challenger failure modes, avoided up front

| CB5 round-1 item | Failure mode | How CB6 avoids it | Where |
|---|---|---|---|
| 1 | a placebo that cannot fail (L1 coin-flip direction: `net_A + net_B < 0` always) | every binding placebo names the alternative under which it advances: calibrated-null (anti-conservative clustering), pseudo-episodes (generic selected-burst reversion), fake cutoffs (heaping, curvature), unrewarded diff-in-disc (non-reward cause), class shuffle (category not text), permutation calibration (anti-conservative ΔLL); CH66's increment-shuffle placebo was rejected because it would pass whenever any sell reverts | §2.6, §CB6-N |
| 2 | a gate where less data is easier (`r_inc` unknown handed over to a weaker gate) | every "unknown / unverified / inconclusive" gate blocks: T1 needs ≥ 10 YES clusters per stratum; truncation and censoring worst cases are chosen against the hypothesis; unrewarded markets too few → R1 cannot be credited and R2 is not registered; N needs ≥ 15 converter clusters; unavailable exits/marks enter binding worst cases | §2.3, §2.6, §CB6-T, §CB6-R |
| 3 | an impossible calibration scheme (200 circular shifts on a 144-step grid) | every placebo is feasible as specified: 200 outcome or exit redraws; pseudo-episode times inside the fetched 96-h window; 24 fake cutoffs whose windows lie in [0.57, 0.86]; permutations within capture × decile cells that exist by construction | §2.6 |
| 4 | queue id clash | q0120-q0134 one id per job, no suffixes; q0135-q0139 reserved for CB6 only; checked against `queue/jobs/` and `queue/drafts/` (q0110 is MC1's committed job) | header, §0.1, §5 |
| 5 | a falsifier that rejects the true effect when a nuisance coexists | T1 is a band-stratified *difference* between strata, so a general favourite-longshot bias cancels; the class shuffle is attribution-only and does not block a T1 advance; R's attribution is a difference-in-discontinuities, not "no jump anywhere else" | §CB6-T, §2.6 |
| 6-7 | post-listing information in sampling or population | h8 sampling uses creation-known strata only; origins use `created_at`/`end_at` only, drawn before any price request (the `end_at` look-ahead is disclosed and enters no feature); clarification exclusion disclosed with its likely direction | §CB6-T, §CB6-F |
| 8 | census reads contradicting the guard | each census uses a field-restricted accessor (R: no spread; N: count-only availability; T: SCREEN only, expected YES from prices) with a unit test | §2.7, §4.5 |
| 10 | "executable" claims without sizes | T2 trade-through fills on modelled asks are labelled modelled; R2 uses recorded sweep sizes for the queue; N2 uses trade-through plus touch bracket | §CB6-T, §CB6-R, §CB6-N |
| 11 | reading a near-copy of a sealed statistic | CH67 excluded for exactly this reason; CB6-N never computes member ask/bid sums; no CB1-CB5 extract or E009-E011 file is read | §0.2, §1.3 |
| 12 | MDE from the wrong data | every MDE is stated as an assumption with its inputs and is recomputed by the census from actual counts | §CB6-T/N/R/C, §2.7 |
| 15 | disk guard close | release-time headroom precondition per data job; the h8 problem is disclosed with a same-parameter Mac fallback (superseded 2026-10-17: Mac fallback removed, §2.8) | §2.8 |
| 16 | stale test count | `battery2.cumulative_count()` recomputed for this draft: 1,104 | §2.5 |

**Open questions for the challenger.**
1. The event-hash SCREEN/HOLDOUT split (same calendar) versus a creation-date split (unequal censoring): acceptable?
2. F as a disjunction of four components (one test) rather than four counted coefficients: acceptable, given that
   per-component odds ratios are reported only?
3. The Mac fallback for `h8_tail` if the host lane or disk blocks it before 2026-10-20T12:00Z: acceptable as an
   operational fallback with identical parameters? (Superseded 2026-10-17: the Mac fallback is removed, §2.8.)
4. R1 tested two-sided at Stage 1 and replicated in the found sign, with R2 registered only for τ > 0: acceptable?
5. N1's pseudo-episode placebo: strong enough against depth-refill and news-driven conversions?
6. M1's added block includes `volume24hr` rank (a monotone transform of a baseline variable within a capture). Should it
   move to the baseline?

## 10. Challenger round 1 (2026-10-17) and response

One challenger pass (`science-reviewer`) on the committed draft `03ea835`, one response (this revision), then proceed
(mission §6). Verdicts: **F (q0120) ACCEPT_WITH_CHANGES; T REVISE; N REVISE; R REVISE; C ACCEPT_WITH_CHANGES.** Every
change below makes the design stricter or more honest; no threshold, floor or gate was relaxed to make passing easier.
Each row gives the change and a one-line scientific justification.

### 10.1 Must-fix items

| # | Finding | Change | Justification | Where |
|---|---|---|---|---|
| 1 | N2 used future data: bids only where the converter later sold, priced from that sale, so every bid filled | Bid on **every received member** at `t_post = t_conv + 60 s`, `q` = last bid-side print before `t_post` + tick; no prior print → no bid; marketable → not posted; ex-post split reported only | A bid rule may use only information available when the bid is posted; otherwise fill rate and net are artefacts | §CB6-N, §4.1, §4.5 |
| 2 | R1 and M1 untestable: time way "capture UTC date" had about 12 (R dev) and 14 (C eval) clusters | Time way → **6-hour UTC block** (about 46 / 84 / 56 blocks); binding **12-hour block** check under the small-G rule; windows not lengthened | 6-hour blocks absorb the persistence of resting quotes across adjacent 2-h captures; the 12-hour check guards residual serial correlation | §2.3, §2.6 (xi), §CB6-R, §CB6-C |
| 3 | R1 driven by tick parity (whole-cent mid → even spread, half-cent → odd), shared by every whole-cent fake cutoff | **Donut [c − 0.005, c + 0.005] is primary** at 0.90 and at all fake cutoffs; robustness is now a wider donut [0.89, 0.91]; no-donut estimate reported only. Half-cent indicator **declined** | The donut gives both sides the same parity mix; a parity covariate is a function of the outcome's parity and would absorb a true 1c effect | §2.6, §CB6-R |
| 4 | T1 censoring outcome-dependent (long-dated markets kept only if their longshot already happened) | Frame restricted to scheduled `end_at ≤ T_fetch8 − 7 d`; forward walk removed; ended-but-open markets kept as counted censored units; **T1 censoring worst case binding** (Δ > 0 and p threshold) | Censoring must not depend on the outcome; where some remains, the decision must survive the adverse assignment | §CB6-T, §CB6-F, §2.7 |
| 5 | h8 separated from h2/h5 by market id only; h2's 270-day lookback overlaps h8, so C1's sibling markets could enter | Exclusion key set (event ids, `negRiskMarketID`, series ids of every h1/h2/h3/h5/h5_ladders market, via Gamma lookup by id); frame markets sharing any key removed **before sampling**; > 2% ids without metadata → "disjointness unverified" (T not testable, counted); seal re-checks; h7 overlap also at key level | Markets in one event share their outcome, so market-id disjointness does not give independent evidence | §1.3, §CB6-F, q0120, q0121 |
| 6 | "Without change of substance" was false; who has seen C1's five worst events? | All changes from CH60 listed (primary, origins, frame, fidelity, drift threshold, median window, inflections, markers). Checked: no committed doc, code output or results file stores any C1 event identifier (host results files inspected by key path only, values not read); no record that anyone viewed them; CH60's class claim declared a conjecture; recovering the identities before CB6-T Stage 2 is final is forbidden | A reader must be able to tell a pre-specified test from one adapted after seeing data | §1.3, §7 risk 3a |
| 7 | M1 permutation placebo could not fail (0.005-nat floor ≈ 5 SE) | Calibration placebos (T1, T2, N2, R2, M1) judged on the **p threshold alone, floors off** (T2 keeps its tail gate, a p-type bound); M1 placebo threshold 7.5% (1.5 × α = 0.05, the same ratio as the routes' 1.5% at α = 0.01) | A calibration placebo must test the p value; a floor several SEs high hides an anti-conservative p | §2.6 |
| 8 | q0120 could silently skip worn ids (refused only when h5 seal copies were missing) | Refuse if **any** exclusion file is missing or its sha256 differs from the pin in `seals/cb6_tail_rules.json` | A skipped exclusion file lets worn markets into a "fresh" sample with no trace | §1.4, §4.2, q0120 |

### 10.2 Should-fix items

| Finding | Change | Justification |
|---|---|---|
| N1 pseudo-dump was "largest burst" | Pseudo-dump = burst nearest `V_d` in notional within [0.5, 2] × | The placebo must copy the real units' size selection, so it isolates timing |
| N fetch semantics | `takerOnly=true` declared; converter sell = taker SELL YES / BUY NO by the stakeholder hash; maker dumps invisible (lower bound, disclosed); 10-page cap → every unit of the conversion unavailable; logs from `T6_dev_start − 96 h` | Unstated side semantics and partial windows would make targets ambiguous |
| R1 density only reported | **Sorting check binding for crediting** (McCrary at 0.90 vs fake cutoffs, same donut); sorting → non-causal, not credited, R2 not registered. Rewards midpoint possibly size-adjusted → fuzzy RD; τ is intent-to-treat | Manipulation of the running variable breaks RD identification, and the treatment rule is not observed exactly |
| R2 has no Stage 1 | An R2 pass is "single stage on post-freeze data, unreplicated (L1)", never L2-dev; still in the Holm k | Labels must say how many times a result was seen |
| Calibrated null drawn per market | One draw **per event**; neg-risk members mutually exclusive (sub-intervals of [0, 1)); same for the T2 placebo | Event-level dependence is the dependence that matters for the outcome |
| Disk growth 0.75 GB/day | 0.9-1 GB/day (RETENTION.md); precondition uses 1.0 | Use the measured rate |
| 1,104 count is the Mac working tree | Disclosed as a lower bound; union with the host `trials.jsonl` (`deploy.sh` / `union_jsonl.py`) before any count; post-union value recorded | `COLLECTION_HOST.md` requires the merge before counting |
| T2 "pending" open-ended | `T6_T2_register_deadline` 2026-11-21T00:00Z, then "not run (register missing)", p = 1, counted | An open-ended pending state could keep k unfixed |
| 50-50 resolutions unstated | Enter the primary at Y = 0.5; non-wins in π and in the YES-cluster rule; exclusion reported | The primary must be computable without a later choice |
| Mac fallback mechanics (superseded 2026-10-17: removed, §2.8) | Own limiter at 3 rps (no cross-host limiter or collector yield); host partial runs discarded, never merged; release asset is the canonical hash-checked copy; one read location fixed at seal with one access log; q0121/q0125-T/q0126/q0130 run there | One canonical copy and one access log keep the seal auditable |
| q0120 conditions | May be queued before the CB6 freeze after its own freeze check; frame keeps `event_ids`, `neg_risk_market_id`, `series_ids`; all thresholds in the rules file before commit; 20-market fidelity-60 smoke test (PASS ≥ 18/20) | The fetch must not run with an unverified price source or unpinned thresholds |

**Declined or partly declined.** (a) Half-cent-mid indicator for R1: declined (conditions on outcome parity); the donut
primary is the adopted alternative. (b) Lengthening the R and C windows: declined in favour of 6-hour blocks plus the
12-hour check, because longer windows delay the freeze and the evaluation and do not address within-day dependence.
Nothing else was declined.

### 10.3 q0120 implementer spec (what the fetcher code must do)

`run_cb6.py tail-smoke | tail-fetch | tail-seal`, `cb6_tail.py` fetch side, tests (§4.5):
1. **Rules file.** Load `seals/cb6_tail_rules.json`; refuse (exit 2) unless its `rules_sha256` equals the code's. It holds
   frame windows, seeds (`arepo-h8-tail`, `arepo-h8-tail-origins`, `arepo-h8-smoke`, `arepo-cb6-tail-split`), strata and
   weights, regexes and marker list, thresholds, `end_before_fetch_days = 7`, `max_unverified_key_share = 0.02`, and
   `{path, sha256}` for the five exclusion files.
2. **Exclusion files.** Refuse if any of h1_first/h2_main/h3_power `sample.csv.gz`, `seals/h5_cb1_SEAL.json`,
   `seals/h5_cb1_ladders_SEAL.json` is missing or its sha256 differs from the pin. Market ids from the sample files and
   from the seal copies' `prices/<id>.csv.gz` names.
3. **Exclusion keys.** Gamma lookup of every exclusion id (≤ 50 ids per request; retry with `closed=true` for missing);
   parse guard keeps only id, all event ids, `negRiskMarketID`, series ids. Write `exclusion_keys.csv.gz`. Share of ids
   without metadata > 2% → write status `disjointness_unverified` and exit 0 (no sample, no prices).
4. **Smoke (`tail-smoke`, before commit).** 20 seeded exclusion-id markets with `end_at` in 2025; one fidelity-60
   `prices-history` request each over `[end_at − 12 d, end_at − 2 d]`; PASS iff ≥ 18 return ≥ 80% of expected hourly points
   with median spacing 3,600 ± 300 s. Write counts only to `creative_batch6/tail_smoke.json`; `tail-fetch` refuses without
   PASS.
5. **Frame.** Closed and active markets by `end_date` over `[2025-09-01, T_fetch8 − 7 d]`, 1 random 15-min window per
   day per walk; **no forward walk**; capped windows dropped and counted. Columns: `frame_row(with_text, with_outcomes)` +
   `description` (4,000 chars), `event_ids`, `neg_risk_market_id`, `series_ids`. Outcome fields only to
   `outcomes_guarded.csv.gz`. Pin `T_fetch8` in `request_clock.json`.
6. **Filters before sampling.** Created in `[2025-09-01, 2026-07-31]`, `end_at ≤ T_fetch8 − 7 d`, binary, not weather
   (fee category or `TEMP_RE`), not crypto "Up or Down", life ≥ 14 d; drop exclusion ids; **drop any market sharing an
   event id, `negRiskMarketID` or series id with the key set**; counts by reason in `key_drops.json` / `frame_report.json`.
7. **Sample.** 4,500 (or all if fewer), strata status × `cb1_topic` × creation month, weights non-sports 1.0 / sports 0.5,
   seed `arepo-h8-tail`; store `inclusion_prob`, `sample_weight`. No price/volume/outcome input.
8. **Origins.** Monday 00:00 UTC grid in `[created_at + 7 d, end_at − 24 h]` and `≤ T_fetch8 − 60 d`, ≤ 3 drawn without
   replacement seeded by market id; write `origins.csv.gz` before any price request.
9. **Prices / prints / wallets.** Per origin: fidelity-60 `prices-history` over `[t − 8 d, t + 2 d]`; `/trades?market=
   <cid>&takerOnly=true` over `[t − 30 d, t + 6 h]`, limit 1,000, ≤ 3 pages, `window_truncated` flag; rule (iii) applied to
   stored prints, one cached `/activity` first-trade lookup per qualifying buyer; HMAC-hash wallets in memory, never write
   raw addresses. Cap every stored row at `ts ≤ min(T_fetch8, T_seal)`, count drops.
10. **Run control.** `--rps 4` shared limiter + collector yield on the host (the Mac `--rps 3` variant was removed 2026-10-17); 429
    back-off; resumable 90-min chunks; no chunk starts at or after `T_seal` → `NOT_RUN_DEADLINE.json`, status
    `not_run_deadline`; refuse above 10 GB data-dumps on the host; output ≤ 0.12 GB; terminal statuses
    `tail_fetch_complete | not_run_deadline | disjointness_unverified`; manifest with per-file sha256 and run location.
11. **Seal (`tail-seal`).** Re-check sealed markets against `exclusion_keys.csv.gz`; h7 drop by id and by key (light
    Gamma lookup, 2 rps) after both h7 runs are terminal; event-hash SCREEN/HOLDOUT split merged across
    `neg_risk_market_id`; listing sha256; read location; create `ACCESS_LOG.jsonl`; append one
    `history_seal_declaration` trial line.

## Implementation notes (q0120 fetcher)

Code: `backend/astrolabe/research_lab/cb6_tail.py`, runner `backend/scripts/run_cb6.py` (`rules`, `exclusion-keys`, `tail-smoke`,
`tail-fetch` / `fetch`, `tail-seal` / `seal`, `verify-seal`), tests `backend/tests/unit/test_cb6_tail.py`, queue drafts
`queue/drafts/q0135_h8_tail_smoke.json` (promoted), `q0120_h8_tail_fetch.json`, `q0121_h8_tail_seal.json` (ids renamed at the freeze check, see below). Rules file `seals/cb6_tail_rules.json` (`rules_sha256` 57a265d0620c45ea2c82e606e1194846aed6012e2848753a81cfdbb90aa2f3df after the freeze-check fixes; the first draft hash 74969607... is superseded), generated
by `run_cb6.py rules`; it carries the five exclusion-file sha256 pins and the hash of the source of every rule function. Choices the spec left open
(for the freeze check; none relaxes a threshold):
- **Frame stored in full, outcomes guarded.** `frame.csv.gz` holds every walked row with `description`, `event_ids` (all events), `neg_risk_market_id`
  and `series_ids` (series of all events, a superset of `events[0].series`, so the key drop is stricter). `status` and `closed` stay in the frame
  (strata, censoring); `outcomePrices`, `umaResolutionStatus`, volume, liquidity, `closedTime` go only to `outcomes_guarded.csv.gz` (sampled markets).
- **Streaming.** The walk appends one gzip member per day to `frame_partial.jsonl.gz`; filters, key drop and sampling read it record by record and
  keep only market ids per stratum (a test bounds the peak at under 6 MB for 12 MB of descriptions). The partial file is deleted when
  `frame_report.json` (the stage marker) is written.
- **Origins** need only `created_at` and `end_at`; a sampled market with no Monday in its life stays in the sample with no origin and is counted
  (`n_sample_without_origin`); the sample is not pre-restricted to markets with origins.
- **Wallet lookups** run only for origins whose usable longshot price (last hourly point stamped at least 600 s before t, not older than 7,200 s)
  lies in [0.02, 0.10], for buyers qualifying under rule (iii) on the stored prints; truncated print windows make (iii) unavailable.
  Raw addresses stay in memory; `wallet_first.csv.gz` holds hashes only.
- **Prints** are stored once per market (deduplicated union over its origins); `origin_windows.csv.gz` keeps each origin's window, page count,
  `window_truncated`, oldest print and cap-drop counts.
- **Clarification markers**: the five literal markers plus `note:` followed by an ISO, numeric or month-name date (pattern in the rules file).
- **Headroom** is exit 75 (data-dumps size + the 0.12 GB cap above 10 GB); at 9.7 GB on 10-16 it holds on the host (section 2.8).
- **Chunk length.** `--budget-min 85` with `timeout_s 5400` (the section 5 draft said 90 and 6600).
- **Seal** records drops as `DROPPED_KEY` / `DROPPED_H7` blocks in `split.csv.gz` (sealed files are never edited). h7 ids come from the committed
  seal copies' `prices|trades/<id>[__event]` names (the series store lists only successor market ids there); the h7 key lookup catches siblings.
- A live probe on 2026-10-17 (three recent closed markets; not the smoke test) confirmed that `id=` lookups return closed markets only with
  `closed=true`, that fidelity 60 returns hourly points (239 of 240) and that windowed taker prints and series ids parse.

### Freeze-check fixes (2026-10-17)

The science-reviewer freeze check of the `h8_tail` fetcher returned GO_WITH_CONDITIONS. Applied, with tests in `test_cb6_tail.py`; no declared threshold or selection rule changed.

1. **Smoke result write-once.** `tail-smoke` exits 2 if the result file exists (checked before any request, and again by exclusive create), so a FAIL cannot be replaced by a later PASS.
2. **Outcomes capped at T_fetch8.** A sampled market with `close_epoch > T_fetch8` is stored in `outcomes_guarded.csv.gz` with every outcome field blank (censored) and counted as `outcomes_censored_post_cap` in `frame_report.json`.
3. **Full disk budget is a declared end state.** Manifest `status: disk_budget`, exit 4 (not the retried 75); the status is in the q0120 repeat regex so it does not loop. Estimate: `frame.csv.gz` (4000-char descriptions) and `frame_partial.jsonl.gz` coexist while the frame outputs are built, so 0.12 GB was tight; the output cap is now **0.25 GB** (`--disk-cap-gb 0.25`) and the dump headroom guard 12.5 GB (host cap 13 GB), as in q0081/q0082.
4. **Seal verifies fetched files.** `tail-seal` recomputes sha256 of every file in the fetch manifest `file_sha256` and exits 2 on any mismatch or missing file.
5. **Ids.** Seal is `q0121_h8_tail_seal`; the smoke is `q0135_h8_tail_smoke` (reserved id); q0120 `depends_on` q0135, q0121 on q0120. No letter suffixes remain.
6. **Rules file.** `event_key_split`, `hb.cb1_topic`, `_is_weather` and `tail_row` are now in `RULE_FUNCS`; the (never consumed) rules file was regenerated: new `rules_sha256` **57a265d0620c45ea2c82e606e1194846aed6012e2848753a81cfdbb90aa2f3df**.
7. **h7 wait.** The smoke and the fetch do not depend on h7. The seal's exit-75 wait is bounded by the queue at 48 tempfails (about 24 h) while h7 may run to 2026-10-22, so the coordinator promotes q0121 only after q0120 is complete and both h7 SEAL/NOT_RUN records are committed; the wait is a safety net only.

Promoted to `queue/jobs/`: q0135 only (q0120 waits for a committed smoke PASS; q0121 for q0120 complete and the h7 records).

## Smoke test result (2026-10-17): FAIL

The write-once smoke job `q0135_h8_tail_smoke` ran on the host at 2026-10-17T05:04:13Z (code `06ce95d`, rules
`57a265d0…`) and returned **FAIL**: `n_pass` 4 of 20 (threshold 18), `n_ge_80pct_points` 4, `n_spacing_ok` 7,
`n_failed_requests` 0, `n_candidates_available` 573; fraction of expected hourly points: `lt_0.5` 16, `0.5_to_0.8` 0,
`0.8_to_1.1` 4, `ge_1.1` 0. The host file is unchanged (write-once). Its byte-identical copy is
`docs/research_lab/seals/cb6_tail_smoke_FAIL_20261017.json`, sha256
`ae21aefec15c0122310682fab70a640a21f68b8486ae18f4b9f3490be65e28be` (same hash on the host).

Consequence, as declared in CB6-F: **q0120 is not committed**. A different fidelity or source is a design change that
needs review, and `T_seal` (2026-10-22T00:00Z) is not moved. The diagnosis follows below.

### Diagnosis (2026-10-17; counts-only probes, no outcome column read)

Two request probes and three zero-request counts ran from the host venv with the code's own seeded selection
(`smoke_candidates`, seed `arepo-h8-smoke`, the same 20 markets as q0135; the smoke result was not touched): 300 public
requests in all at 2 rps, 0 retries, 0 throttled. Only
counts and timestamp offsets were printed; nothing was stored. Columns read from the sample files: `market_id`, `token0`,
`condition_id`, `created_at`, `start_epoch`, `end_epoch`, `close_epoch`, `closed`, `fee_category` (never
`outcome_prices`, `uma_status`, volume or liquidity). **The probe scripts were deleted from the host afterwards and were
not committed** (working copies survive only in the Mac's volatile `/tmp`), so the diagnosis counts below cannot be
reproduced from the repository. Future diagnostic probes must keep their scripts in the repository.

| Question | Evidence (counts) | Verdict |
|---|---|---|
| (d) window / denominator mis-specified | **16 of 20** smoke markets had scheduled life `end − created` of 0.1-6.5 days, so the window `[end − 12 d, end − 2 d]` began 5.5-11.9 days *before the market was created*; these are exactly the 16 in the `lt_0.5` bin. The 3 extra `n_spacing_ok` markets are partial series starting at creation (first point 0.0-0.1 d after `created_at`; 43-103 points). The 4 markets whose life covered the window (13.6-27.4 d) returned 239-240 hourly points, median gap 3,600 s: **4 of 4 pass**. Of the 573 closed 2025-end exclusion-sample markets, 539 (94%) have life < 14 d | **Cause.** The smoke pool omitted the h8 frame's own `life ≥ 14 d` rule, so the expected-points denominator counted hours before the market existed. The code implements the declared spec literally; the error is in the spec |
| (a) no trading in the window | In-window taker prints: 0 for 14 of the 16 failing markets (the window predates them; the other 2 traded only after creation, late in the window); whole-life prints exist for 13 of the 16 (3 never traded) | Not an independent cause: no trades because no market yet |
| (b) API downsamples old history | 2025 markets with a covered window: 239-240 hourly points at fidelity 60 and 1,440-1,441 at fidelity 10 | **No** |
| (c) wrong request parameters | Same `market=<token0>&startTs&endTs&fidelity=60` request returns full hourly series where the market is live; `interval=max` returns [] for 20 of the 20 smoke markets (known, already avoided) | **No code bug** |

**Representativeness (20 worn h8-like markets: created 2025-09-01..2026-07-31, closed, end ≤ 2026-10-10, life ≥ 14 d,
not weather, ranked by the v1 seed; drawn only from the h1/h2/h3 exclusion `sample.csv.gz` files, so every one is an
exclusion id that the h8 frame drops by id before sampling (and its event / neg-risk / series siblings by key): the
fetch cannot sample them, and no price of an h8-samplable market was seen; the frozen h8 origin rule `draw_origins` applied; one fidelity-60 request over
`[t − 8 d, t + 2 d]` per origin).** 50 origins: 36 meet the smoke criterion (≥ 80% of 240 points, median gap
3,600 ± 300 s). Of the 14 that do not, **8 lie after the market's actual close** (early closure before the scheduled
end; points stop at `close_epoch`, e.g. 42 and 103 points where the close fell 6.3 and 3.7 d before t); 23% (225 of
976) of the h8-like pool closed > 2 d before its scheduled end. Of the **42 pre-close origins, 36 (86%) pass**; the 6
others are genuinely sparse or empty mid-life windows (0, 53, 98, 123, 143, 151 points; one with a 3-hour median gap).
A usable point at t (CB6-T rule) exists for 37 of 50 origins (37 of 42 pre-close).

### Smoke v2 (design change; science-reviewer acceptance required before q0136 is promoted)

**Review outcome (2026-10-17): ACCEPT_V2_WITH_CHANGES.** The 18-of-20 threshold is kept. A v2 FAIL is final. The
already-probed market among the 20 draws is accepted with disclosure. The required doc changes 1-4 are applied: the
§2.2 scoped `close_epoch` exception, the provenance of the h8-like probe markets, the pass-chance wording below, and
the record of the deleted probe scripts. The coordinator also removed the Mac fallback (§2.8). No code, pool or
rules-hash change was made. `q0136_h8_tail_smoke2` is promoted to `queue/jobs/`.

**Change (pool only).** Smoke v2 draws from closed 2025-end h1/h2/h3 exclusion-sample markets with scheduled life
`≥ 14 d` (the h8 frame rule, already declared) **and** `close_epoch ≥ end − 2 d`, so the whole window lies inside
`[created_at, close]`; new seed `arepo-h8-smoke2`; drop counts by reason are written. **Unchanged:** n = 20, PASS iff
≥ 18 of 20, ≥ 80% of 240 expected points, median spacing 3,600 ± 300 s, window `[end − 12 d, end − 2 d]`, fidelity 60,
request form, counts only, write-once. Pool size on the host: 573 → 33 (539 life < 14 d, 1 closed before the window
end; zero-request count). Fetch, origin rule, frame and every CB6-T rule are unchanged.

**Justification.** The smoke exists to test the *source* (risk 1: "fidelity-60 history unavailable for closed
markets"). Its denominator presumes the market exists and trades through the window. v1 violated that for 16 of 20
draws, so its FAIL measured the pool's short-lived markets, not the source. v2 restores the presumption with two
rules fixed from metadata only: the h8 frame's declared life rule and the market's close time. Neither involves a
price, a print count or an outcome.

**Disclosure.** The v2 rule was written after the probes above. They are counts only on worn markets. Two of the 33 v2
pool markets were among the 20 probed v1 draws (239 and 240 points), and one of those two is among the
first 20 v2 draws (checked by a zero-request count). None of the 20 h8-like probe markets is in the v2 pool. The v2 seed is new and was not used in any probe. The
thresholds were not changed. The pass chance is only a rough figure from a different window population: the
86% pre-close rate comes from mid-life origin windows `[t − 8 d, t + 2 d]` of h8-like markets, not from near-end
windows `[end − 12 d, end − 2 d]`. At p = 0.86, P(≥ 18 of 20) ≈ 0.45; given that one of the 20 v2 draws is the already
probed market (239-240 points; accepted with this disclosure), P(≥ 17 of the other 19) ≈ 0.49. **The 18-of-20
threshold was kept in spite of this estimate.** So v2 can still FAIL. A v2 FAIL is final: no smoke v3, q0120 not committed, and CB6-T recorded as "not run
(smoke FAIL)" and counted.

**Code and files.** `cb6_tail.py` `smoke_pool` / `run_smoke` (v2), `smoke_ok` requires `smoke_version` =
`h8-tail-smoke-v2`; runner refuses the v1 output name. New rules file `seals/cb6_tail_rules_v2.json`, `rules_sha256`
**bf05c8ee7c3a1e55dafaa4b4344d9ba0be35afe545c372e7e6b288c08eceee16** (`rules_version` `cb6-tail-rules-v2`; `smoke_pool`
and `run_smoke` added to the hashed `RULE_FUNCS`; the smoke block records the superseded v1 FAIL). The v1 file
`seals/cb6_tail_rules.json` (57a265d0…) is kept unchanged as the record of q0135. Drafts: `queue/drafts/q0136_h8_tail_smoke2.json`
(new output `creative_batch6/tail_smoke2.json`; **not promoted**). `q0120_h8_tail_fetch.json` is repointed to rules v2,
`--require-smoke tail_smoke2.json` and `depends_on` q0136.

**Consequences for CB6-T power.** The frozen eligibility rules (market open at t; usable point at t and at t − 7 d)
already exclude post-close and empty-window origins, so no CB6-T rule changes. If the MDE's 35% eligibility assumption
did not already absorb them, the probe's 74% usable-at-t rate lowers it to about 26% (about 3,500 units). Stage-1 MDE
then rises from about 3.8c to about 4.4c (×√(35/26)). The 2c floor is unchanged, and T1 can still detect only a strong
class effect. The census replaces these assumptions.

**Clock.** q0136 takes about 20 requests (under 2 min). q0120 needs about 3.5 h and must finish before `T_seal`
2026-10-22T00:00Z. The latest safe host start stays 2026-10-21T12:00Z; there is no Mac fallback (§2.8). The deadline is not
moved. If review does not accept v2 in time, CB6-T is "not run (smoke FAIL)" and counted.

## Smoke v2 result (2026-10-17): PASS
q0136 ran on the host at 05:30Z (rules v2 `bf05c8ee…`): **20 of 20 pass, 0 failed requests**. The write-once result is copied
byte-identical to `seals/cb6_tail_smoke2_PASS_20261017.json` (sha256 `d1f7a4ef693e494e18320bac45fde8918d5a961565f24a5b24ae3e5589ab0bf4`).
The v1 FAIL stays on record. q0120 (`h8_tail` fetch, `--require-smoke research_lab/creative_batch6/tail_smoke2.json`) promoted to
`queue/jobs/`; q0121 (seal) is promoted only after q0120 is complete and both h7 SEAL/NOT_RUN records are committed.

## h8_tail fetch result and sample shortfall (2026-10-17; proposal A-T1 needs review)

**Result (q0120, 08:12-08:27Z, `tail_fetch_complete`):** 362 markets, 670 origins, 145,430 price rows, 49,262 print rows,
0 failed items, 3,668 requests, 17 MB. `frame_report.json` (sha256 `b2e41922…`): 405 days × 2 walks × 1 random 15-min
window → 65,584 raw rows; dropped created outside `[2025-09-01, 2026-07-31]` 33,305, life < 14 d 22,725, crypto Up/Down
7,417, weather 692; exclusion ids 15; **exclusion keys 1,068** (series 1,053 any-match, 981 series-only); kept 362, all
taken (`taken_all`, 21 strata). Outcomes were not read (guarded file only). This is what the frozen rules specify ("if the
eligible frame holds fewer than 4,500, all are taken"), but it is **about 8 % of the planned 4,500 markets** (the §CB6-T
MDE assumed ≈ 4,700 units). At ≈ 35 % eligible origins that is ≈ 235 units, ≈ 118 per block: near the ≥ 100-unit floor,
and the T1 MDE scales to roughly 3.8c × √(4,700 / 235) ≈ 17c, so T1 could detect nothing plausible. The planning error was
the frame yield per window (≈ 81 rows per 15-min window, and filters + series keys removing 99.4 % of rows), not the source.

**Proposal A-T1 (top-up before `T_seal`; no outcome, price or print of h8_tail has been read by any analysis):**
- New run `h8_tail_b` with the **same rules** (filters, exclusions by id and key, strata, weights, origin rule, price and
  print windows, wallet rule, cap at `T_seal`) except: `--windows-per-day 8` with a new seed `arepo-h8-tail-b` for window
  draws and sampling, h8_tail's market ids excluded by id (and its event / neg-risk / series keys, so the two runs share no
  event or series and the event-hash split stays clean). Expected yield ≈ 8 × 362 less the extra key drops, i.e. ≈ 1,500-2,900
  markets; ≈ 20-30k requests (≈ 2-2.5 h at 4 rps, `net` lane), ≤ 0.15 GB.
- q0121 seals h8_tail and h8_tail_b **together** (one listing, one event-hash SCREEN/HOLDOUT split over the union); CB6-T
  reads the union. If h8_tail_b is not complete before `T_seal`, it is dropped entirely (`not_run_deadline`) and CB6-T runs
  on h8_tail alone, as frozen.
- Disclosure: the top-up was decided from frame counts only (the shortfall), never from any outcome or price; both runs'
  frame reports are kept.
- Alternative (if the reviewer rejects A-T1): CB6-T runs on h8_tail as frozen and is expected "not testable for size" or
  "not detected at MDE ≈ 17c", counted.

## Amendment A-T1: reviewer verdict ACCEPT_WITH_CHANGES and the implemented design (2026-10-17)
The proposal above is accepted with these binding changes, which supersede its "Proposal A-T1" bullets where they differ
(the new seed `arepo-h8-tail-b`, 8 windows per day and key exclusion of h8_tail are **not** used):
1. **Same seed, nested windows.** `h8_tail_b` uses the seed `arepo-h8-tail` with 9 windows per day and walks only the 8 windows
   h8_tail did not walk. The draw is `random.Random(f"{seed}|{day}").sample(valid, k)`; its first element is `randbelow(len(valid))`
   for any k, so h8_tail's single window (k = 1) is always among the k = 9 picks. The union therefore equals the frozen frame rule
   at 9 windows per day with one selection probability. Verified by a test over 405 days × 8 slot counts; the walk refuses if the
   nesting ever failed. Sampling: all eligible taken as before; the rule holds over the union. If the union pool exceeded 4,500 the
   frozen sampler runs over the union pool (h8_tail's rows join the strata) and h8_tail_b keeps its chosen rows (flagged in
   `frame_report.json` `sample.union_pool_exceeds_n_markets`; not expected, the pool is about 1,900-3,300).
2. **Clock pinned to h8_tail's `T_fetch8`** (`request_clock.json`, cross-checked with the manifest) for the frame cutoff, days and
   slots, the origin limit ≤ `T_fetch8 − 60 d`, outcome censoring and the price / print cap `min(T_fetch8, T_seal)` (the rules'
   cap; it cannot bind because origins are at least 58 days before `T_fetch8`). Recorded in h8_tail_b `manifest.params.topup`.
3. **h8_tail excluded by market id only** (`sample.csv.gz` pinned by the parent manifest `file_sha256`; the read is appended to
   the parent's `ACCESS_LOG.jsonl`). Key exclusions stay against h1/h2/h3/h5 as frozen; the parent's event / series keys are not
   excluded, and the event-hash split runs over the union rows.
4. **Every non-complete ending drops h8_tail_b entirely** (`not_run_deadline`, `disk_budget`, `disjointness_unverified`, any
   refusal): no third run. The union is used whenever h8_tail_b completes, whatever its yield. h8_tail alone still seals.
5. **MDE restated** before the seal (above). 6. **Ledger and trials** record the design change (`trials.jsonl` kind
   `design_change`, not a test; `EXPERIMENT_LEDGER.md`). 7. **Code** (commit `30e0356`): `refuse_run_id`, declared arguments
   (`--run-id h8_tail_b --topup-of h8_tail --windows-per-day 9`), rules v3 `seals/cb6_tail_rules_v3.json` (rules_sha256
   `ad7f5baa5d6e63a27f913b37b5b263f18579750a6c085ebafc5c5cb5bbdf35fb`, own commit; v2 kept; every v2 rule function is byte-identical,
   tested), explicit pinned smoke carry-over (the smoke v2 PASS file, sha256 `d1f7a4ef…0bf4`, made under the v2 hash `bf05c8ee…`,
   is accepted under v3 only through `smoke.carry_over` in the hashed rules; tested), union seal (`tail-seal --topup-run h8_tail_b`:
   both manifests complete with file hashes verified, equal clocks, cross-run id disjointness, h7 drops and the event-hash split over
   the union, one listing `union_listing_sha256`, one trial line, one seal copy), `verify_tail` / `read_tail_sealed` check both
   runs. 8. **Data-dumps guard:** `--data-dumps-cap-gb` (default 12.5) lets the job pass 13 (collector cap 14 GiB).
9. **Queue:** drafts `q0120b_h8_tail_b_fetch.json` and an updated `q0121_h8_tail_seal.json` (depends on q0120b terminal: complete
   or dropped). Nothing is in `queue/jobs/`. Latest safe start stays 2026-10-21T12:00Z minus the 2-2.5 h run.

## A-T1 freeze-check conditions (2026-10-17)
Applied after the A-T1 freeze check (GO_WITH_CONDITIONS). q0120b and `seals/cb6_tail_rules_v3.json` (ad7f5baa...) are unchanged;
no function hashed by the rules (`RULE_FUNCS`) was touched: `seal_tail`, `topup_state` and the new `topup_refusal_reason` are
not in `RULE_FUNCS`, so the v3 rules do not cover the seal path.
- **Must-fix 1 (code, `seal_tail`).** Sealing h8_tail without `--topup-run` while h8_tail_b is pending (manifest in progress, or
  not started) before T_seal (2026-10-22T00:00Z) raises `NotNow` (exit 75); a complete h8_tail_b is still refused. At or after
  T_seal a pending/incomplete h8_tail_b is dropped with its real reason (`not_run_deadline`, or `never_started_by_T_seal`).
  The q0121 draft keeps `--topup-run h8_tail_b` and no longer invites an empty value.
- **Ruling 2.** If `union_pool_exceeds_n_markets` is true (`frame_report.json` `sample`), CB6-T stops for review before any
  read, uses the recorded `sample_weight`, and discloses n. Not expected: 362 x 9 ~ 3,258 < 4,500. No rules change.
- **Ruling 3.** A dropped top-up records `topup.refusal_reason` in the seal, manifest-level `recheck` and declaration, separate
  from `reason`: `no_run_left_fetch_refused_or_never_started` when h8_tail_b left no manifest (a fetch refusal or never
  started), else `none`. The states stay distinct from `not_run_deadline`.
- **Ruling 4.** When the union is sealed, the declaration carries `topup_frame_disclosure`: the h8_tail_b frame reflects Gamma
  state after T_fetch8 (status, edited end dates), limited by outcome censoring (`end_at <= T_fetch8 - 7 d`) and the price cap.
- **Ruling 5 (ops note).** The q0120b headroom guard needs data-dumps <= 12.75 GB (cap flag 13 less the 0.25 GB output cap)
  at start; check `du` on the host before promoting. q0120b itself is not edited.
