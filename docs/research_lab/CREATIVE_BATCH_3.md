# Creative batch 3 (CB3): quote-vacuum recovery (CH35) and the selective maker (CH39, CH40, CH41)

`evidence_role: exploratory_historical` (B screen on `h2_main` + pmxt books) / `exploratory_dev` (A screen on worn
captures) / `prospective` (A and B Stage 2 and Stage P, data after the freeze) | status: **DRAFT-REVISED, not frozen;
challenger round 1 ACCEPT_WITH_REQUIRED_CHANGES, all 13 required changes, the rulings and all optional items applied
(response at the end; single response round).** One open user decision (§8: disk / archive rotation). Last updated
2026-10-16 06:05 UTC+1 (2026-10-16T05:05Z).

This file turns four ideas from `CREATIVE_HYPOTHESES_2026-10-16.md` into declared, falsifiable tests:
- **Family A, first step:** CH35's mechanism test (does the fair value stay at the last tight mid when one side of a
  tight book vanishes?). Its result decides whether family A (CH35-CH38) has a money route at all.
- **Family B, "selective maker":** three presence filters for a paper liquidity provider, tested against the
  unfiltered maker: CH39 (leave after a large-for-market print), CH40 (leave late in the market's life), CH41 (quote
  where round-trip "farmer" flow is high).

It follows `CREATIVE_BATCH_1.md` (CB1) and `CREATIVE_BATCH_2.md` (CB2) in structure and rules:
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim. AREPO never
  trades; every P&L is a paper rule at modelled (history) or recorded (prospective) books and prints.
- The primary quantity of every economic test is net P&L **per filled share** at the declared fill rule, after fees
  (maker fee 0) and the maker rebate, with the expected value per posted quote beside it. Liquidity rewards are never
  in a primary number (§2.1). Mechanism tests are labelled as such and are never read as profitability.
- Test tables bind only once the CB3 declaration hash is committed (`model_specs/cb3_v1.json`, the CB3 freeze).
- Queue specs (§5) are drafts. None is committed to `queue/jobs/` by this document.
- **Where CB3 says "as CB1 §x" or "as CB2 §x"**, that rule applies unchanged, including its challenger-round fixes.

## 0. Summary, selection and ranking

| Rank | Job | Hypothesis | Tests (counted) | Screen / dev data | Replication / prospective data | Queue ids | CPU-h | Peak RAM |
|---|---|---|---|---|---|---|---|---|
| 1 | **CB3-F** data | `quote_state/` extract (backfill + live), follow-up trade step (collector), census | none | n/a | n/a | q0060, q0061, q0064 | 1.5 + pass step | 1.2 GB |
| 2 | **CB3-A** quote vacuum (CH35) | when one side of a tight book vanishes, the next tight mid returns most of the way to the old mid (A1), so a re-quote of the vacated side at the old touch is worth > 0 (A2), and filled re-quotes are net-positive (A3) | A1 (mechanism), A2 (economic, unconditional); A3 enters Stage 2 directly | captures started before 2026-10-15T21:00Z (J4's worn window), via `quote_state/` | `quote_state/` + follow-up vacuum stratum in `[T3_rep_start, T3_rep_end)`; Stage P after | q0062, q0065, q0067 | 1.0 + 3.5 | 2.0 GB |
| 3 | **CB3-B** selective maker (CH39, CH40, CH41) | adverse selection of a standing touch quote is concentrated after large prints (B1), late in life (B3), and is lower where round-trip flow is high (B5); the filtered maker is net-positive (B2, B4, B6) | B1-B6 (3 mechanism, 3 economic) | `h2_main` trades + pmxt book table (q0003), 6h grid, 2026-04-13 to 08-10 | follow-up sample + sweeps in `[T3_rep_start, T3_rep_end)`; Stage P after | q0063, q0066, q0067 | 1.0 + 3.0 + 3.0 | 2.0 GB |

**Why this order.** The `quote_state/` backfill must run before the raw captures of 10-15 October become deletable
under the pending snapshot retention (deferred rule: 8 days; release copies remain). The follow-up trade step must be
live and tested before the CB3 dev window so that the prospective windows are not lost; it is cheap and data-only.
CH35 runs first because it is cheap, on data that already exist, and its kill rule closes four ideas at once. The B
screen waits for the pmxt book table (q0002 still running, then q0003).

### 0.1 Selection

No census was run for this draft. **No CB3 quantity has been computed on any dataset**; the only numbers used below
come from committed documents (J4, the J4 diagnosis q0031/q0032, ECONOMIC_CONDITIONS part B, HISTORICAL_SOURCES, HB2).

| Idea | Decision | Reason |
|---|---|---|
| **CH35** quote-vacuum re-quoting | **include (A1, A2; A3 at Stage 2)** | Ranked 1. The J4 diagnosis found 9.6% of triple rows with a wide-state leg (`|d_bm|` 0.107 vs 0.003). Runs on existing captures and sweeps; its kill rule (recovery < 0.5) decides family A |
| CH36 bot-footprint outages | defer to after A1 | Its money route is the reward share during outages, which needs CH35's premise (vacuums are mechanical). Descriptive only; can reuse `quote_state/` later |
| CH37 artefact-induced flow | defer to after A1 | Needs the vacuum trade stratum (built here for A3) and A1 passing; would be counted later |
| CH38 Kalshi anchor | defer | Matched-pair history only; E009/E010 live data sealed until 2026-11-03; worth it only if A1 passes |
| **CH39** post-print retreat | **include (B1, B2)** | Ranked 2. Seed HB2 F7 (h2). Reuses CB1-C / ECONOMIC_CONDITIONS queue-fill machinery |
| **CH40** late-life schedule | **include (B3, B4)** | Ranked 8, but same machinery and data as CH39 at almost zero extra cost. Seed HB2 F3 (h2) |
| **CH41** farmer-flow share | **include, narrowed: CH41-narrow (B5, B6)** | Ranked 3. Tested as **within-market round-trip share** (§CB3-B) under the prospective 500-print visibility in both stages (ruling 1). The universe-level farmer rule (Data API `/activity`, 30-day cross-market stats) is not tested: it cannot be observed consistently across stages and is truncated for the heaviest farmers. Every CB3 output names the test "CH41-narrow"; it says nothing about cross-market or maker-side farmers |
| CH42 disposition sellers | defer | Needs `/positions` entry prices per seller; a wallet-cost study of its own |
| CH43 surprise score as risk filter | exclude now | E011 labels may not be read before 2026-11-11; the score's rows overlap E011's window |
| CH44, CH45 reward geometry | defer | Need per-minute qualifying depth (level-by-level books) and in-play sports scope (user's call) |

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Prior use | Role in CB3 | Evidence ceiling |
|---|---|---|---|
| `history/h2_main` (3,200 sampled markets; 1,759 panel markets; trades newest-first with `wallet_hash`, 10-min prices, outcomes, `created_at`, `end_at`) | r0-r5 ML, HB1, HB2 (F3, F7 are CB3-B's seeds), surprise detector, SB2 J1/J3/J7, CB1-A/C/E screens | **B Stage 1 screen** (with the pmxt table). Worn far beyond budget; HB2 found F3/F7 on the same trades, so B1/B3 on h2 are **seeded, not independent** (disclosed in every results file) | L1 |
| `history_sources/book_features` (pmxt v2 hourly archive, as-of book at **6h-grid** origins, outcome-0 token, h2 panel pairs, 2026-04-13 to 08-10 minus 06-12..06-17) | ECONOMIC_CONDITIONS part B, r4_book (q0004), J3 (q0011), CB1-C (q0021) | B Stage 1 entry books (touch, `sw_bid_size_1`/`sw_ask_size_1` for the queue, 1c/5c depth). Being built by q0002 (43,902 h2 pairs); finalised by q0003. The h1 build was 49% two-sided, 49% `no_book` (HISTORICAL_SOURCES) | L1 |
| Complete captures `research_lab/snapshots` started **before 2026-10-15T21:00Z** | J4 (q0006), J4 diagnosis q0031/q0032 (the wide-state finding was made on these), J5, E011 | **A Stage 1 screen** via the `quote_state/` backfill (q0060). Worn: CH35 was conceived from J4's diagnosis of these captures | L1 |
| Book sweeps (2 per pass, E001-eligible tokens, touch, `bid_size_1`/`ask_size_1`, 1c/5c depth) | J4 P1x, CB1/CB2 depth checks | A: within-pass persistence and sweep confirmation of onsets. B (prospective): entry book, queue size, marks. Copied into `quote_state/` | - |
| `research_lab/trade_samples` (2,000 active-frame markets per pass, last 500 trades up to the request time, hashed wallets; raw kept 3 days) | E007, flow_screen | B (prospective): pre-origin trades of the follow-up subsample, copied by the follow-up step before the 3-day retention removes them, **filtered to `ts < t` explicitly** (the sample runs after the sweeps and stores trades up to its request time; challenger item 5) | - |
| **`cb3_followup/` (new, §4.3)**: per pass, trades fetched again for a seeded 50% of the previous pass's trade sample, plus a vacuum stratum | none | B Stage 2 / Stage P fills; A3 fills | L2-dev / stage P |
| **`cb3_extract/quote_state/` (new, build spec §4.3.1)**: every binary market E001-tight at the capture or any of the 4 previous, plus a per-capture id list | none | A dev (backfill) and A rep / Stage P (live); B prospective entry books and marks | L1 / L2-dev / stage P |
| `rows_ext` sidecar (since 2026-10-11T12:00Z: `created_at`, `accepting_orders`, `clob_rewards`, `rewards_max_spread`, `rewards_min_size`, `fee_schedule`, parent/neg-risk ids) | CB1, CB2 | prospective life fraction (CH40), fees, dep_group, reward scenario lines | - |
| `h3_power` | HB1-R, SB2 J2/J6/J8 (reads 4-6) | **not read.** Retired from replication use after SB2 (Ledger M3). The runner refuses the run id | - |
| `h4_seal`, `h5_cb1`, `h5_cb1_ladders`, `h6_weather`, `h1_first` | SB2, CB1, CB2 reservations; pilot | **not read by any CB3 code path**; runner refuses the run ids | - |
| E009/E010 live poller, E011 labels, live trade monitor | registered experiments | **not read** | - |

### 1.2 Dates (declared; UTC)

| Name | Value | Meaning |
|---|---|---|
| `T3_draft` | 2026-10-16T04:18Z | First draft. No CB3 quantity computed on any dataset |
| `T3_A_dev_end` | **2026-10-15T21:00Z** | A dev uses complete captures with `capture_start_utc < T3_A_dev_end` only (the captures q0031/q0032 used, `--until-utc 2026-10-15T21:00Z`) |
| `T_J4R` | [2026-10-16T00:00Z, `T_J4R_end`), `T_J4R_end` = J4-R's actual final `--until` (2026-10-21T00:00Z, later if q0035's exit-3 rule moves it) | J4-R's frozen window. **CB3 analyses and censuses never read a row whose capture, onset capture or follow-up origin pass lies in it** (J4-R freeze integrity note; challenger item 11). The live extractor and follow-up step still write rows for it (data copying only); `run_cb3.py` refuses to load them |
| `T3_fu_start` | deployment commit time of the follow-up step (expected 2026-10-18) | First follow-up pass. Recorded in `cb3_followup/manifest.json` |
| `T3_dev_end` | **2026-10-25T00:00Z**, moved forward by whole UTC days if fewer than 3 full days lie in `[max(T3_fu_start, T_J4R_end), T3_dev_end)` | Prospective dev window **`[max(T3_fu_start, T_J4R_end), T3_dev_end)`** (item 11): counts and coverage only (q0064); **no mark-out, recovery or net computed on it** |
| `T3_rep_start` | **max(2026-10-27T00:00Z, first complete capture ≥ CB3 freeze commit + 2h, `T3_dev_end` + 2d, first UTC day at which archive rotation is verified active (§8, user decision))** | Stage 2 (A and B) uses only captures, sweeps and follow-ups from here. Pinned in a committed file at the freeze (CB1 freeze-fix 9), before any row at or after it is read |
| `T3_rep_end` | `T3_rep_start` + 28 d (about 2026-11-24) | End of Stage 2 origins (about 336 captures) |
| `T3_P_start`, `T3_P_end` | `T3_rep_end`, `T3_rep_end` + 28 d (about 2026-12-22) | Stage P origins, only for Stage-2 passes |
| `T3_mark_lag` | 12 h | Analysis of a window waits until its last origin + 12 h (marks up to about 10h after the last fill) |
| `T3_res_out` | `T3_P_end` + 30 d | Resolution mark-outs (reported only) |

### 1.3 Sealed and untouched data (named)

- **No untouched historical book data exist for family B.** pmxt ends 2026-08-10; its only AREPO table covers `h2_main`
  pairs; `h3_power` is retired; `h5_cb1` belongs to CB1's one-read-per-family rule; `h4_seal` (origins ≥ 2026-10-22) has
  no historical books. A new `h7` backfill with its own pmxt build would cost about as much as q0002 (240 GB streamed
  for h1-scale coverage, HISTORICAL_SOURCES) and is not proposed. **Replication is therefore prospective.**
- **SEALED-P (CB3).** Every capture, sweep, `quote_state/` row and `cb3_followup/` file with origin at or after
  `T3_rep_start`, used only under the committed CB3 declaration. Stage P data (≥ `T3_P_start`) are additionally unread
  until Stage 2 is final. These dates overlap CB1's replication window (to 2026-11-09), CB2's windows and E011's window
  (to 2026-11-11): the calendar is shared, the statistics, populations and output tables differ, and no CB3 job reads
  `cb1_extract/`, `cb2_extract/`, E011 inputs or outputs.
- **Dev windows are worn, disclosed.** The A dev captures are the ones on which the wide-state channel was found. The B
  history screen is seeded by HB2 F3/F7 on the same h2 trades. Both are L1 and serve as stop rules, not evidence.
- **h2 book table sharing.** r4_book, J3, CB1-C and CB3-B all read the same pmxt table and h2 trades. CB3-B's population
  excludes CB1-C's longshot band by construction (entry mid in [0.10, 0.90]; CB1-C uses [0.02, 0.10]).
- **J4-R.** CB3 reads no row tied to a capture in `T_J4R` for any analysis or census (including vacuum strata built
  from `T_J4R` onsets and follow-ups whose origin pass is in `T_J4R`), and its prospective dev window starts at
  `T_J4R_end`. If q0035 moves its `--until` forward (exit-3 rule), `T_J4R_end` and the dev-window start move with it,
  and `T3_dev_end` / `T3_rep_start` follow their rules (§1.2).
- **HB2-R (q0010) is pending.** If F7 or F3 fails to replicate on h3, the B1/B3 seeds weaken; CB3 proceeds (different
  target), and the verdict text records it.
- Results are never written inside a sealed or source directory: CB3 outputs go to `research_lab/creative_batch3/`.

## 2. Common rules

### 2.1 The paper maker (shared by A3 and all B tests)

| Item | Rule |
|---|---|
| Token | Outcome 0 (`clob_token_id_0` / pmxt `token0`). Prints of outcome 1 are converted to outcome-0 terms (`cb1_history.buys_longshot` convention: a BUY of outcome 1 at q is a taker SELL of outcome 0 at 1 − q) |
| Quote opportunity (B) | At origin t, a market with a two-sided, non-crossed book, spread ≤ 0.10, mid in [0.10, 0.90], traded before t (CB1 trade-condition rule; truncated-unknown is unavailable, never 0), binary, open, `end_at` > t + 8h. One bid at `best_bid` and one ask at `best_ask`, **5 shares each** (`cb1_history.C_ORDER_SHARES`), resting unchanged for a life `L = 2h` |
| Origins (B) | History: 6h grid of the pmxt table (both book clocks ≤ t). Prospective: the first sweep of each pass for markets in the follow-up subsample (t = that market's sweep batch receipt time) |
| **Fill rule (primary: queue)** | `cb1_history.queue_fill`: an order fills (all-or-nothing) when cumulative opposite-aggressor volume at or through its price within `(t, t + L)` reaches the displayed size at that level at entry (`sw_bid_size_1` / `bid_size_1` for the bid; ask likewise) plus 5. Fill time = the completing print. Cancellations ahead of us are ignored: conservative for fill *counts* only, not for toxicity (the fills it keeps are those reached by heavy flow). **Touch** rule (any print at or through) brackets it from the other side; for every economic advance or pass the touch-rule estimate must agree in sign (**binding**, challenger item 8) |
| Trade availability (challenger item 4) | Prospective: the post window `(t, request time]` is fetched with **windowed `/trades?market&start&end&takerOnly=true` paging** (limit 1,000, offset pages; the `large_trade_census.anchor_trades` pattern, up to 5 pages), so a window is complete unless the page cap binds. History: a fill status over a window that begins before a truncated market's oldest stored print is unavailable (CB1 §2.2). **Every residual unavailable quote enters the binding worst case:** only the side with the lower mark-out fills (5 shares at its price), marked at the far touch at the mark time, no rebate. An economic advance or pass requires the estimate with these worst-case fills added to stay > 0 (CB1 §2.2's binding worst case). Unavailable counts are reported by side, price band and outcome of the worst case |
| Visibility of pre-origin prints (ruling 1) | Origin features (large-order history, round-trip share) use only the **newest 500 prints before t**, in both stages (history mimics the prospective trade-sample page). A feature whose window is not covered by those 500 prints is unavailable; the unit leaves that test's population (a causal, pre-t rule, not outcome-dependent) |
| Mark (6h, primary) | History: the market's as-of price at `t_fill + 6h` (`cb1_history.asof_quote`: stamp + 600 s, ≤ 2h old). Prospective: the first-sweep mid of the first pass with sweep receipt ≥ `t_fill + 6h` whose book is E001-tight (two-sided, spread ≤ 0.10); if not tight, the next pass within 4h; else **mark unavailable** (counted; worst case below) |
| Mark-out | Buy fill at P: `mo = M − P`; sell fill at P: `mo = P − M` (cents per share) |
| Fees and rebate | Maker fee 0. Rebate per filled share `= ρ_cat · r_cat · P(1 − P)` with `r_cat` from `economics.DOCS_CATEGORY_RATE` (history: docs table by `fee_category`; prospective: sidecar `fee_schedule`, `fee_policy="conservative"`) and `ρ_cat` the category rebate share (crypto 0.20, sports 0.15, geopolitics 0, all others 0.25; the `econ_conditions_maker.REBATE` table moved to `economics.REBATE_SHARE`). The pmxt window is after the 2026-03-30 fee rollout, so fees and rebates exist throughout. Applied pro rata to our own fill (an assumption: the allocation is undocumented). Unknown or null category → ρ = 0 (as `econ_conditions_maker.REBATE.get(cat, 0.0)`). At mid prices the rebate is ρ·r·¼ ≈ 0.25-0.35c per filled share, as large as the B economic floor, so **every economic floor and sign must also hold with the rebate halved (binding; challenger item 6)** |
| **net** | `net = mo + rebate` per filled share. **EV per quote** = Σ net over the quote's fills × 5 / (2 × 5) (cents per quoted share-side) |
| Rewards | **Never in a primary.** History has no reward configuration, so only the break-even subsidy is reported: `−EV` per quote-hour where negative. Prospective (reported): an upper bound on reward income by the public formula `S = ((v − s)/v)² · b` with `v` = `rewards_max_spread`, s = our distance from the adjusted mid, `b` = 1 (the in-game multiplier is unpublished), competitor score bounded below by the sweep 1c depth on both sides at the touch distance, daily pool from `clob_rewards`, both sides required outside [0.10, 0.90], scored at `rewards_min_size` (our 5-share fill model does not qualify; disclosed) |
| Worst cases (binding where stated) | Unavailable mark → the far touch of the last available sweep (a taker exit). Unavailable fill status → the binding worst case in "Trade availability" above |
| Capacity | Fills per day in the sampled set × 5 shares × (1 / inclusion probability), and median displayed depth at the touch, beside every economic estimate |
| Category scope | Parameter `CATEGORY_SCOPE = "non_sports"` (in the declaration hash). Sports units are computed and reported as a `cb3_descriptive` stratum, not counted. Including sports is the user's call and would need its own declaration |

**The unfiltered maker U (baseline, B0).** Every quote opportunity and every fill above. Reported at every stage
(`cb3_descriptive`, not counted): fill rate, mean `mo`, mean net per filled share, EV per quote, by side, price band,
spread band and category. Every filter's economic test is compared with U.

### 2.2 Clocks

As CB1 §2.2 and CB2 §2.2. In addition:
- **History:** prints are Data API venue timestamps (seconds); a print at exactly t is not in `(t, t + L)`. Origin
  features (large-print history, round-trip share, life fraction) use prints strictly before the time they describe.
- **Prospective:** t = the market's first-sweep batch receipt time. Pre-origin prints = the pass-i trade-sample rows
  **with `ts < t`**, filtered explicitly (the trade sample runs after the sweeps and stores prints up to its request
  time; challenger item 5); post-origin prints = the windowed follow-up fetch at pass i+1 for `(t, request time]`. The
  union is de-duplicated on (`tx_hash`, `asset`, `side`, `size`, `price`, `ts`) before any use. If the follow-up request
  time is earlier than t + L, the life is truncated at the request time and the quote is flagged; a binding
  sensitivity excludes flagged quotes.
- **Scheduled anchors only.** `end_at` = Gamma `endDate` (history: at fetch time, a look-ahead risk; prospective: the
  capture's `end_date`, as-of). `created_at` from the h2 frame or the sidecar. `closed_time` is never an anchor.
- Execution latency (A3): the re-quote is posted at the second sweep of the onset pass, never at the Gamma capture
  that detected the onset.

### 2.3 Uncertainty and decision rule

- **Fill-level estimates are unweighted** (primary). Design-weighted secondaries: history `h2_design_weights`;
  prospective 1 / (trade-sample π × 0.5) for B, 1 / vacuum-stratum π for A3. Weighted and unweighted must agree in
  sign for any advance or pass (binding).
- **Clusters.** One-sided p = max over declared cluster ways of CR1 (normal z, HB1 rule); CI by a 2,000-draw
  cluster bootstrap (seed 316) over the first way.
  - B (all stages): event and `dep_group` (fixture-day, category-aware: `ml_panel.dependence_group_ids`). Stage 2 and
    P add the UTC origin day; with 28 days that way falls under the **CB2 small-G rule** (CR2 + t(G − 1) and a Webb
    wild-cluster bootstrap, larger p; G < 15: not testable).
  - A: event, `dep_group` (event fallback before the sidecar, flagged) and **onset capture** (a bot outage hits many
    markets in one capture, CH36). A dev has about 49 captures, so the capture way is CR1 (G ≥ 30).
  - Regression tests use `bounce_decomp.fit_test` generalised to arbitrary cluster ways (max-SE across ways).
- **Testability.** ≥ 30 clusters in each declared event-type way (event, `dep_group`, capture) and ≥ 100 units (fills
  for fill-level tests, onsets for A1/A2); otherwise "not testable" (p = 1, still counted). **The 28-day UTC-day way of
  Stage 2 and P is governed only by the CB2 small-G rule** (CR2 + t(G − 1) with the wild-cluster p for 15 ≤ G < 30;
  G < 15 not testable), never by the ≥ 30 rule (challenger item 9).
- **Stage 1** (A on dev captures; B on h2/pmxt): advance iff one-sided p < 0.01 in the declared direction, the §2.4
  floor is met by the point estimate, the test's placebo rule (§2.6) is met, and the binding robustness holds. BY label
  (q = 0.10, `battery2.cumulative_count()`) attached as triage only.
  - **B entry exception (declared now; accepted, ruling 3).** If a B test is *not testable* on h2 (counts), it enters
    Stage 2 directly, like CB1's B1/B2. If it is testable and does not advance, it stops (no Stage-2 read).
  - **A3** has no Stage 1 (dev captures have no post-onset trades except by chance). It enters Stage 2 iff A1 advanced.
- **Stage 2** (prospective, `[T3_rep_start, T3_rep_end)`, frozen): Holm at α = 0.05 one-sided over **all CB3 tests
  reaching Stage 2** (k ≤ 9). Tests finishing early are reported against Bonferroni α/k with k fixed when Stage 1
  ends; the final batch Holm (`cb1_history.batch_holm`) can only add passes. A pass is "development-replicated on
  prospective data" (L2-dev). Stage 2 is already at recorded books and prints.
- **Stage P** (prospective, `[T3_P_start, T3_P_end)`): only the economic tests A3, B2, B4, B6 that passed Stage 2; own
  Holm family at α = 0.05 (k ≤ 4). This is CB3's only path to a confirmation claim and is itself the economic check.

### 2.4 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate |
|---|---|---|
| A1 | mechanism | recovery ratio R̂ ≥ 0.60 (H1: R > 0.50) |
| A2 | mechanism (unconditional re-quote value; relabelled from "economic", optional item) | G ≥ +0.50c per onset |
| A3 | economic | net ≥ +0.50c per filled share **and** fill rate ≥ 2% of eligible onsets |
| B1 | mechanism | expanding-past within-market slope β39 ≤ −0.50c per filled share |
| B3 | mechanism | expanding-past within-market slope β40 (with week FE) ≤ −1.0c per unit life fraction |
| B5 | mechanism | expanding-past within-market slope β41 ≥ +1.0c per unit round-trip share |
| B2, B4, B6 | economic | filtered maker net ≥ +0.25c per filled share, EV per quote > 0, **and** the binding improvement rule (§2.6); all with the rebate halved |

`R_ann` is reported for every economic test, not gated: for a 2h quote with a 6h mark the capital-time floor
`max(d, 1)` makes it uninformative (CB1's 10% floor would pass trivially).

### 2.5 Counting (M3 rule)

- Every primary test writes one `trials.jsonl` line via `provenance.append_trial` (kinds `cb3_test`,
  `cb3_replication`, `cb3_prospective`), and each run writes one `ml_explain` count line
  (`source: "creative_batch_3:<job>"`, `n_tests`).
- New `battery2.KIND_RULES` entries: those three EXCLUDE ("counted by the matching `creative_batch_3:*` count line");
  `cb3_descriptive` EXCLUDE (no inference). Unknown kinds still raise; a unit test runs the counter on the real
  `trials.jsonl`.
- **Prior cumulative count at drafting: 993** (`battery2.cumulative_count()` on the local `trials.jsonl`, last line
  2026-10-16T03:24Z; of which `ml_explain` 431, `flow_screen` 275, `econ_conditions_taker` 95). The host may hold more
  automatic `flow_screen` lines and CB1/CB2 lines by run time; each results file records the run-time value.
- Placebo lines `evidence_role: "placebo"`, count 0. U (B0), the census, the sports stratum, the reward scenarios and
  every "reported" line are `cb3_descriptive`.

### 2.6 Estimators, placebos, the J4 lesson, and robustness

**The J4 lesson applied (challenger item 1).** J4's pooled slope was almost entirely between-market, and a
within-market permutation reproduced it. Any CB3 association between a market-state variable and a mark-out can be
between-market: volatile, wide, large-print or late-life markets may simply be worse markets. The draft's
`T = β − mean(β_placebo)` was rejected: it returns the within-market slope shrunk by the within-market share of the
regressor's variance, so its floors had no fixed meaning. **The primary statistic of every B mechanism test is now
J4-R's expanding-past within-market slope:**
- Fills (B1, B3) or quote opportunities (B5) of each market in time order; the regressor and every control are
  replaced by their value minus that market's expanding mean over its *earlier* rows (`bounce_decomp.expanding_demean`,
  first row of each market dropped); the target (`net`) is raw; OLS with intercept; cluster ways as §2.3.
- **B3 adds calendar-week fixed effects** (within a market, life fraction moves one-for-one with calendar time, so
  common weekly shocks would otherwise load on LF).
- Floors (§2.4) apply to this slope. Markets with one row contribute nothing; the number of markets and rows used is
  reported, and the census (§2.7) gives it before the freeze.
- **Reported beside it (SB2 consequence 5):** the pooled slope β, the draft's `T`, and the within/between decomposition
  of β (market-mean regression vs within-market regression).

**Matched placebos and the J4-R reading rule.**

| Test | Placebo (20 draws, seed 317, as J4-R) | What it keeps |
|---|---|---|
| B1 (CH39) | circular shift of each market's large-order time stream by a uniform offset in [1 d, market span − 1 d] (fills and fill prints untouched); flags recomputed; same expanding-past estimator | each market's large-print frequency and clustering |
| B3 (CH40) | within-market permutation of life fraction across that market's fills; same estimator with week FE | each market's life-fraction distribution |
| B5 (CH41-narrow) | within-market permutation of round-trip share across that market's quote opportunities; same estimator | each market's round-trip-share distribution |
| A1, A2 (CH35; challenger item 2) | **keep every real onset** (real quotes at i−1, i, i+1); from i+1 on, rebuild the mid as a martingale `m'_{i+1+k} = m_{i+1} + Σ` increments drawn with replacement from the market's pooled valid mid increments (J4-R market-pooled bootstrap); keep the observed half-spread path, so bid/ask = m' ∓ hs (clipped to [0.001, 0.999]); re-apply the T rule (tightness from the observed spread and the rebuilt mid band) and the unrecovered coding | the real onset set and each market's spread-state sequence |

- **Reading rule (J4-R, every mechanism test):** the family is **void** if the 2.5-97.5% range of a test's 20 placebo
  estimates does not cover 0 (A1: the placebo value of `R`; B: the placebo slope); a test is read only if |mean
  placebo estimate| ≤ 0.5 × its real max-SE, otherwise "inconclusive (placebo bias)". Status is written into every
  trial line. Under the A placebo the mid is a martingale, so `R_placebo ≈ 0` and `G_placebo ≈ mean(hs_i − |D|)`
  (negative); this checks construction and selection, not A1's H0 (R ≤ 0.5).
- **A placebo minimum.** The A placebo uses the real onsets, so its onset count equals the real count; the number of
  placebo units reaching a tight T and the number of capture clusters are reported per draw. The A family is "not
  testable" with fewer than 1,000 onsets or 30 capture clusters.
- **One summary placebo line per test** (optional item adopted): each test writes a single `evidence_role: "placebo"`
  line with the draw distribution summary (mean, SD, 2.5/97.5%, reading status), not one line per draw.

**Binding improvement rule (B2, B4, B6; challenger item 7).** The filtered maker must beat U by more than a matched
random filter acting **in the filter's own units**, on **the same population** and with **EV per quote over the fixed
U denominator** of that population (removed opportunities or cancelled quotes contribute 0 to the numerator and stay
in the denominator):

| Test | Population (= U restricted to) | Random filter (200 draws, seed 318) |
|---|---|---|
| B2 | quote opportunities in markets with classifiable large-order history (ruling 7) | cancel each quote at a random time: the same number of quotes is cancelled as the real rule cancels, each at a time drawn from the real rule's distribution of cancellation offsets (time since posting) within its stratum |
| B4 | all quote opportunities | remove the same number of quote opportunities as the `LF ≥ 0.90` rule, at random within strata |
| B6 | quote opportunities with RT defined | select the same number of quote opportunities as the top decile, at random within strata |

- Strata: spread band × price band × category × **activity tercile** (taker orders among the visible 500 prints in
  `[t − 24h, t)`, terciles frozen at q0061); B6 also × 1c-depth decile (the liquidity match).
- The real EV improvement must exceed the 99th percentile (Stage 1) / 95th (Stage 2, P) of the random-filter
  improvements. This is the CH41 liquidity control and CH39's "forgone fills carry more spread than the avoided
  losses" kill, made binding.

**Binding robustness for any advance or pass:**
- (i) The estimate keeps its sign and floor without the top 5 clusters by absolute contribution, in each declared way.
- (ii) Weighted and unweighted agree in sign.
- (iii) B mark source (ruling 4). History: the pmxt book mid at the first 6h-grid origin ≥ `t_fill + 4h` (two-sided,
  spread ≤ 0.10) on the covered subset keeps **sign and floor** (the 0.75c source gap exceeds the floors).
  Prospective: the worst-case mark coding (§2.1) keeps sign.
- (iv) A1/A2: the estimate on **sweep-confirmed onsets** (the pass's first sweep shows the vacated side ≥ 3c from its
  level at i) keeps the declared side of 0.5 (A1) or of 0 (A2).
- (v) B3/B4 (history only): the end-date look-ahead sensitivity (drop markets closed > 24h before `end_at`, the F3
  rule) keeps sign and floor.
- (vi) Prospective: the truncated-life sensitivity (§2.2) keeps sign.
- (vii) Economic tests: the **touch-rule** estimate agrees in sign (item 8); the floor and sign hold with the
  **rebate halved** (item 6); the **residual-unavailable worst case** (§2.1) keeps the estimate > 0 (item 4).

**Reported, not binding:** the 2h mark (history: as-of price at `t_fill + 2h`; prospective: first tight sweep ≥
`t_fill + 2h`); resolution mark-outs (CB1 censoring rule, at `T3_res_out`); the taker-exit variant (exit at the far
touch at the mark time); sign by month (history) / week (prospective) and by category; the sports stratum; reward
scenarios; capacity; the **book-age sensitivity** (history: drop quotes whose pmxt `sw_book_age_s` > 3600 s); A: the
mid at i+4 regardless of state and the recovered-only estimate (ruling 5), and A1/A2 on the A3-eligible stratum
(swept at i+1 and persistent).

### 2.7 Pre-freeze census (q0061 history and A-dev; q0064 prospective dev window)

Counts only. No mark, recovery ratio, net or EV is computed; a guard drops outcome columns (`outcome_prices`,
`uma_status`) before population code runs, and **the census never reads the 6h/2h marks, the T-capture mids of A
onsets, or any price after a fill**. It produces:
- A (dev captures): onsets per capture by vacated side, displacement band (5-10c, 10-20c, ≥ 20c) and price band;
  exclusions (not tight at i−1, one-sided at i+1, closed or not accepting, no trade before i, gap-rule breaks);
  clusters per way; the share of onsets swept at i+1 and sweep-confirmed (book states only, no later mids).
- B (h2/pmxt): quote opportunities after each filter; pmxt states; fills by rule and side (fills are part of the
  fill-level population and are disclosed as such: they use prints after t, not marks); unavailable-fill counts by
  side; large-order classification coverage (≥ 50 prior orders); fills with a large order in the prior 30 min; the
  life-fraction distribution of fills; round-trip-share population size (≥ 20 prints in 6h) and its decile cuts on
  **all** quote opportunities (frozen for every stage); the activity terciles (§2.6 strata); for the expanding-past
  estimator, the number of markets with ≥ 2 rows and their row counts per test; clusters per way.
- Prospective dev window (q0064, after `T3_dev_end`): follow-up coverage (requests, 429s, missing passes, truncated
  pages, life-truncation share), quote opportunities and fills per pass, vacuum-stratum sizes and swept shares,
  `quote_state/` and `cb3_followup/` bytes per pass, `created_at` coverage from the sidecar, windowed-paging page-cap
  hits. q0064 reads only rows whose capture, onset capture and origin pass are at or after `T_J4R_end` (item 11).
  **From these counts q0064 states the Stage-2 MDE of every test** (ruling 3), allowing for overlapping 6h marks of
  one market (repeated-market design effect estimated from row counts per market) and the small-G day way; the MDEs are
  written into this file before the freeze.
- Floors are never revised from the census. The large-order, round-trip and life-fraction definitions, all cut rules
  and the onset rule are hashed into the declaration before q0061 runs; the census only fills in counts and the frozen
  decile cuts.

### 2.8 Compute and stop rules

- Queue worker, one job per lane, nice 19, `MemAvailable ≥ mem_mb + 1200`, address cap 2 × `mem_mb`; never two
  multi-GB jobs at once. All CB3 jobs use the `cpu` lane.
- Priorities: CB3 analysis ≤ 48 (below CB1's ≤ 52 and CB2's ≤ 50); the `quote_state/` backfill q0060 at 57 (below
  every CB1/CB2 data job; the coordinator may raise it if snapshot retention is activated first).
- 15 CPU-hour cap per family (A, B). A job failing twice for the same non-transient reason stops and is recorded.
- A null is "not detected at MDE x", never "absent". No re-screen of a failed CB3 test with altered thresholds,
  windows, marks, filters or populations, on any data.
- **Disk guard.** `quote_state/` and `cb3_followup/` writers stop (the pass is counted as missing, never backfilled)
  while host `data-dumps` exceeds 11 GB; each job refuses to start above 10.5 GB. Expected growth with the wider
  membership (item 12) about 4-6 MB per pass (about 50-70 MB a day, 1.3-2.0 GB per 28-day window; measured by q0064).
  **Every CB3 window depends on archive rotation being active (§8, user decision; challenger item 13).**
- **Pass limits (challenger item 10).** Each CB3 pass step is its own line in `arepo_pass.sh`, after the CB1/CB2
  extract line, so the CB1/CB2 600 s budget is untouched: `quote_state/` (`timeout 600`, self-limit 8 min, peak RSS
  ≤ 500 MB) and the follow-up step (`timeout 600`, self-limit 9 min, peak RSS ≤ 500 MB). Both end with `|| true` and
  can never fail the pass.
- **Network etiquette.** The follow-up step uses `trade_sample`'s transport with ≤ 4 rps, `Retry-After` honoured,
  exponential back-off from 1 s capped at 30 s, within its 9-minute budget. Markets are requested in a seeded random
  order, so markets not reached when the budget ends are a random subset (missing, counted, never backfilled). CB2
  §2.8's 429 stop applies (rps halved above 1% 429s in 10 minutes; step ends after 50).

---

## 3. Jobs

### CB3-A: Quote-vacuum recovery (CH35)

**Question (mechanism).** When a tight book loses one side (the touch on that side jumps ≥ 5c away while the other
side stays), does the next tight mid return most of the way to the pre-onset mid (A1)? Is a re-quote of the vacated
side at the old touch worth more than 0 at the next tight mid, before fill selection (A2)? Are filled re-quotes
net-positive after the 2h latency the pass schedule imposes (A3, Stage 2 only)?

**Why new / overlap.** J4 found the wide state as a contaminant of a Gamma-mid regression and diagnosed it (9.6% of
rows) without asking where the fair value is. No AREPO test conditions on one-sided quote vacuums. J4-R (frozen)
requires tightness at h and i and reads a different window; CB3 does not read J4-R's window.

**Population (frozen).** Consecutive complete captures c_{i−1}, c_i, c_{i+1} with gaps in [1.5, 3] h; binary markets
open and (where the sidecar exists) accepting orders at c_i; traded before c_i (`last_trade_price` non-empty and
`volume_num` > 0 where present; blank `volume_num` with a last trade counts as traded, CB2-P rule).
- **Tight at c_{i−1} and c_i** (E001 rule `bounce_decomp.h_tight_mask`: two-sided, spread ≤ 0.10, mid in [0.02, 0.98]).
- **Onset at c_{i+1}**, two-sided:
  - ask vacuum: `a_{i+1} − a_i ≥ 0.05` and `|b_{i+1} − b_i| < 0.01`;
  - bid vacuum: `b_i − b_{i+1} ≥ 0.05` and `|a_{i+1} − a_i| < 0.01`.
  One-sided books at c_{i+1} (a side gone entirely) are counted and reported, not tested.
- `m_c` = Gamma mid at capture c. `D = m_{i+1} − m_i`; `s = sign(D)` (+ for ask vacuums). Old touch on the vacated
  side `q = a_i` (ask vacuum) or `b_i` (bid vacuum); `hs_i = (a_i − b_i)/2`.
- **Recovery mark.** T = the first capture in {i+2, i+3, i+4} (gap rule throughout) at which the market is E001-tight;
  `m_T` its mid. If none is tight: **unrecovered**, coded `m_T := m_{i+1}` (the vacuum treated as fully informative;
  conservative for the money route). A gap-rule break before T (collector outage, not a market event) excludes the unit,
  counted. A market closed with a valid payout before T takes `m_T := Y` (counted); a market closed **without** a valid
  payout before T is coded unrecovered (optional item adopted).
- One unit per (market, onset capture). A market may contribute several onsets over time.

**Statistics.**

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **A1** | mechanism | onset | `R = 1 − Σ s(m_T − m_i) / Σ |D|` (ratio of sums; cluster CI via `economics.boot_ratio`, z by the delta method per cluster way) | R > 0.50 |
| **A2** | mechanism (unconditional re-quote value) | onset | `G = mean g`, with `g = q − m_T` (ask vacuum) or `m_T − q` (bid vacuum), cents | G > 0 |
| **A3** | economic (Stage 2 and P only) | filled re-quote | `net = mo + rebate(q)` per filled share, with `mo` against the B mark (below), fills under the rule below | net > 0 |

A2 values the re-quote as if it filled with certainty, so it is an upper bound on the fill-conditional value (fills
are adversely selected). Under "vacuums are information" (fair moved to `m_{i+1}`), `g = hs_i − |D| < 0` for most
onsets; under "vacuums are noise" `g ≈ hs_i > 0`. Break-even recovery is about `1 − hs_i/|D|`.

**A3 fill rule (prospective).** Onsets in the vacuum stratum (§4.3: ≤ 300 per pass, seeded, inclusion probability
recorded) that are swept at pass i+1 (spread ≤ 0.10 at c_{i+1}, so the onset is at most a 9c jump from a tight book)
and **persistent**: in both sweeps of pass i+1 the vacated side's best level is still ≥ 3c beyond q and the other side
within 1c of its c_i level. The re-quote (5 shares at q) is posted at the second sweep's receipt time s2 and lives
until s2 + 2h; it fills when cumulative opposite-aggressor volume at or through q in `(s2, s2 + 2h)` from the
follow-up trades (windowed paging, §2.1) reaches 5 (queue ahead 0 at posting, because the level was empty in both
sweeps). **Mark (challenger item 3):** the §2.1 B rule, i.e. the first-sweep mid of the first pass with sweep receipt ≥
`t_fill + 6h` that is E001-tight (next pass within 4h, else the far-touch worst case), never `m_T` (capture i+2 can
start before `s2 + 2h`, so `m_T` could precede the fill). `mo = q − M` (re-posted ask) or `M − q` (re-posted bid).
Fill rate = fills / eligible persistent onsets. Residual unavailable fill statuses take the §2.1 binding worst case.

**Baselines (reported, `cb3_descriptive`).** (a) Same g computed for a random side of tight-tight-tight markets with
no onset (a touch quote in a quiet market). (b) The recovered-only R̂ and the unrecovered share. (c) R̂ and G with
`m_T` replaced by the mid at i+4 regardless of state (ruling 5). (d) R̂ and G on the A3-eligible stratum (swept at
i+1 and persistent; optional item).

**Clustering.** Event, `dep_group`, onset capture (p = max; §2.3).

**Family, counting, MDE.**
- Stage 1: 2 `cb3_test` lines (A1, A2) plus the count line `creative_batch_3:A` (`n_tests: 2`); one summary placebo
  line per test.
- Sample (estimated, census to confirm): J4 had about 46,000 triples per period with i tight, 49 periods, 33,375 event
  clusters. If 1-2% of tight markets show a one-sided ≥ 5c onset at the next capture, the dev window has about
  20,000-45,000 onsets. Taking 20,000 onsets, a capture-cluster design effect of 5 (n_eff 4,000), per-onset SD of
  `s(m_T − m_i)`/E|D| about 1 and of g about 5c: SE(R̂) ≈ 0.016, **Stage-1 MDE vs 0.5 ≈ 0.05** (R ≥ 0.55 detectable);
  SE(G) ≈ 0.08c, MDE ≈ 0.25c. Stage 2 (about 336 captures) is about 7× larger. Power is not the risk; bias is (§7).
- A3 (Stage 2): ≤ 300 sampled onsets × 336 passes ≈ 100,000; if 30% are swept and persistent and 5-20% fill, 1,500-6,000
  fills; SD 5c, design effect 3: SE ≈ 0.11-0.22c, MDE ≈ 0.3-0.7c.

**What would kill this (declared).**
- A1 point estimate R̂ < 0.50, or A1 not advancing at Stage 1: **the vacuum is information**; CH35 closed, and CH37 and
  CH38 lose their premise (recorded; CH36 may still be run as a descriptive footprint map).
- A1 advances but A2 does not (G ≤ 0 or below floor): the recovery exists but the half-spread does not cover it;
  CH35 closed as "noise, not capturable at the old touch".
- A3 fill rate < 2% of persistent onsets, or A3 not passing at Stage 2: the route is theoretical at pass latency.
- The A placebo void rule triggers: the family is void and reported as such.

**Economic check.** A2 is a mechanism bound. The economic check is A3 at Stage 2 and Stage P: recorded sweep books,
recorded prints, 2h latency (posting at the second sweep), queue-free fill only because the level was empty in both
sweeps, the 6h tight-sweep mark, rebate as §2.1 (and halved, binding), the touch-rule sign check, no rewards. Capacity = fills per day × 5 shares / π. Not modelled, disclosed: a live maker
would see vacuums within seconds (WebSocket), not after a pass; our own bot would be exposed to the same heartbeat
cancellations; other makers re-quoting inside us.

**Verdict map.**
- A1, A2 advance; A3 passes Stage 2 and P with the binding robustness → "prospectively supported quote-vacuum re-quote
  at pass latency (paper)"; CH37/CH38 designs may follow.
- A1, A2 pass Stage 2, A3 fails or is untestable → "vacuums are mostly noise, not capturable at 2h latency"; a
  minute-level collector design would be the only route.
- A1 fails → kill as above.

**Compute.** Dev: q0062 reads `quote_state/` for about 49-51 captures into a compact market × capture panel (about
120,000 markets × 51 × 4 float32 ≈ 0.1 GB; paths are complete for every market tight at any of the 5 most recent
captures, item 12), onsets, R̂, G, bootstrap (2,000) and 20 martingale rebuilds from i+1: about 1 CPU-h, 1.5 GB. Stage 2: q0065, about 336 captures, about 3.5 CPU-h, 2.0 GB.

**Stop rule.** No A1 advance → no Stage-2 analysis for A (the extract keeps accruing, data only).

### CB3-B: The selective maker (CH39, CH40, CH41)

**Question.** For a standing two-sided touch quote (§2.1), is the adverse selection of filled orders concentrated in
identifiable states (after a large-for-market print, late in the market's life) and lower where flow comes from
within-market round-trippers? Does leaving those states (or selecting the low-risk state) give a maker that is
net-positive per filled share and better than random presence?

**Why new / overlap.** ECONOMIC_CONDITIONS part B tested signal-driven passive orders (filled orders moved 1-7c against
us); CB1-C tests longshot ask-selling. Neither tested unconditional two-sided presence with state filters. HB2 F3/F7
measured price continuation, not maker mark-outs, on the same h2 trades (seeded, §1.3).

**Shared definitions (frozen; hashed before q0061).**
- **Taker order.** Prints with the same (`tx_hash` or history `trade_key` group, side, outcome) aggregated; history
  without a transaction id: same (ts, `wallet_hash`, side, outcome). Notional = Σ size × price.
- **Large order (CH39).** Notional ≥ the 90th percentile of the market's previous **200 taker orders** (strictly
  before), requiring ≥ 50 prior orders; otherwise unclassified. A count-based window is used, not F7's 30-day q80,
  because it needs only contiguous stored history (robust to newest-first truncation) and is computable identically
  from the prospective 500-print pages. For the quote's origin the window is taken within the visible newest 500 prints
  before t (§2.1); prints during the quote's life are classified against all prints before them in pre ∪ post. F7's
  exact definition is a reported history sensitivity. A market is **classifiable** at t if ≥ 50 taker orders are
  visible before t.
- **Life fraction (CH40).** `LF = (t_fill − created_at) / (end_at − created_at)`, clipped to [0, 1]; scheduled `end_at`
  (§2.2). Undefined without `created_at` (prospective: sidecar coverage reported by q0064).
- **Round-trip share (CH41-narrow).** A wallet w is a **round-tripper in market m at t** if, over its taker trades in m in
  `[t − 24h, t)`: ≥ 4 trades, both signs present on outcome 0, and `|Σ signed shares| ≤ 0.10 · Σ |shares|`.
  `RT(m, t)` = notional share of m's taker volume in `[t − 6h, t)` from round-trippers. Defined only when m has ≥ 20
  prints in `[t − 6h, t)` and the **newest 500 prints before t reach back to t − 24h** (the prospective visibility,
  applied in history too; ruling 1). Data API trade wallets are the taker's proxy wallet, so farmer *makers* and
  cross-market farmers are invisible (CH41's named fake; disclosed as CH41-narrow).

**Tests.**

| ID | Kind | Unit | Regressor / filter | Statistic | Direction |
|---|---|---|---|---|---|
| **B1** | mechanism (CH39) | fill (classifiable markets) | `post = 1` if a large order (not the filling order) printed in `[t_fill − 30 min, t_fill)` | expanding-past within-market slope β39 of `net` on `post` with controls (§2.6) | β39 < 0 |
| **B2** | economic (CH39) | fill of the retreat maker, **classifiable markets only** (ruling 7) | quotes cancelled for the rest of their life at the first large order after posting (both sides) | mean `net` per filled share | > 0 |
| **B3** | mechanism (CH40) | fill | `LF` | expanding-past within-market slope β40 of `net` on LF with controls and calendar-week FE | β40 < 0 |
| **B4** | economic (CH40) | fill of the schedule maker | no quote opportunity with `LF(t) ≥ 0.90` | mean `net` per filled share | > 0 |
| **B5** | mechanism (CH41-narrow) | quote opportunity (RT defined), `net` summed over its fills (0 if none) | `RT(m, t)` | expanding-past within-market slope β41 of EV per quote on RT with liquidity controls | β41 > 0 |
| **B6** | economic (CH41-narrow) | fill of the top-decile maker | quote opportunities with RT in the top decile (cut frozen at q0061) | mean `net` per filled share | > 0 |

- **Controls (all mechanism regressions).** Entry spread, log(1 + touch depth 1c, own side), the market's absolute
  24h own-price change before t (history: the price series; prospective: Gamma `chg_1d`; not identical, disclosed),
  price-band and side dummies, category fixed effects. B5 adds log(1 + depth 1c, both sides) and log(1 + taker notional
  in `[t − 24h, t)`) (the liquidity correlate). CH39's spread confound (F5) is in every B1 regression.
- **Why the retreat is "leave for the rest of the life".** CH39's text re-quotes after W minutes. History has only the
  6h as-of book, so a re-quote price after a large print is unknown; re-posting at the stale price could cross the
  book. CB3 therefore tests the "leave after a large print" rule in both stages, and uses the 30-minute window only for
  the mechanism (B1). W ∈ {5, 15, 60} min are reported, not counted (CH39 asked for one declared W; accepted, ruling 7).
- **Economic tests vs U.** B2/B4/B6 levels are compared with U and must pass the binding improvement rule (§2.6), so a
  pass cannot come from U already being positive.

**Clustering.** Event and `dep_group` (all stages) plus UTC day at Stage 2 and P (small-G rule).

**Family, counting, MDE.**
- Stage 1: 6 `cb3_test` lines plus the count line `creative_batch_3:B` (`n_tests: 6`); one summary placebo line per
  test (B1, B3, B5 placebos; B2, B4, B6 random filters), count 0. U is one `cb3_descriptive` line.
- **MDEs below were made for the draft's pooled statistic and are optimistic for the expanding-past estimator**, which
  uses only within-market variation from markets with ≥ 2 rows. h2 has about 1.5-2 fills per market in the pmxt
  window, so perhaps 40-60% of fills carry information; the Stage-1 MDEs are about 1.3-1.6× those listed (B1 about
  2.5-3c, B3 about 3-4c per unit LF, B5 about 8-12c per unit RT). q0061 reports the usable counts; B5 in particular
  may be "not testable" on h2 and then enters Stage 2 under the entry exception (ruling 3).
- **Stage-1 sample (estimated for the draft, census to confirm; q0002/q0003 not finished).** 43,902 h2 pairs at 6h origins; if about
  49% are two-sided (the h1 build), about 21,500; after spread, mid-band [0.10, 0.90], traded-before and `end_at`
  filters perhaps 10,000-15,000 quote opportunities. ECONOMIC_CONDITIONS queue-rule fill rates were 6-19% per order
  within 2h, so two sides give about 2,000-3,500 fills from perhaps 300-600 events.
  - B1: if 10-20% of fills in classifiable markets are post-large (about 300-500), SD of net per fill about 6c,
    design effect 2: SE(β) ≈ 0.45c; the placebo adds about √2: **MDE ≈ 2.0c**. The CH39 envelope (60% of a 1-7c loss in
    the post-print window) is about 1-4c, so a large concentration is detectable and a modest one is not.
  - B3: SD of LF about 0.28: SE ≈ 0.55c per unit LF, × √2 for the placebo: **MDE ≈ 2.5c per unit LF**.
  - B5: perhaps 25% of opportunities have ≥ 20 prints in 6h (about 600-900 fills), SD of RT about 0.15:
    **MDE ≈ 6-8c per unit RT** (0.6-0.8c per 0.1 of share). Probably underpowered on h2; the B entry exception applies
    only if it is *not testable* by counts.
  - B2, B4, B6: SE of a mean over about 2,000 fills (B6 about 200-300) with design effect 2 ≈ 0.19c (B6 ≈ 0.5-0.6c):
    **MDE ≈ 0.6c** (B6 ≈ 1.7c).
- **Stage-2 sample (prospective, estimated).** Follow-up subsample about 1,000 markets per pass × 12 passes × 28 days
  ≈ 336,000 quote opportunities; if 10% get a fill on either side, about 35,000 fills. Allowing for overlapping 6h
  marks of one market (consecutive passes' marks share 4h of path), a market-repetition design effect of about 10, and
  the small-G day way (G = 28, t(27) reference, which adds about 5%; optional item): SE ≈ 0.10c and MDE ≈ 0.35c for
  B2/B4 (B6 about 1c), mechanism MDEs about 0.8c (B1), 1c per unit LF (B3) and 3c per unit RT (B5). **These are
  superseded by q0064's stated MDEs before the freeze** (ruling 3). Stage P is the same size.

**What would kill this (declared).**
- **CH39:** B1's within-market slope is not below −0.50c (the concentration is a market-level fact or absent), or B2 fails
  the improvement rule (the cancelled fills were worth as much as random fills: the forgone spread outweighs the
  avoided loss).
- **CH40:** a flat within-market slope with week effects (B3), or B4 failing the improvement rule.
- **CH41-narrow:** no within-market slope after the liquidity controls (B5), or B6 failing to beat the liquidity-matched random
  decile: round-trip flow is just a liquidity proxy.
- **The whole family:** U's mean net per filled share below −1.5c at Stage 1 with no filter advancing, which would say a
  touch maker at 2h life is dominated by adverse selection in every identifiable state (recorded as the family verdict).

**Economic check.** B2, B4, B6 are economic tests at recorded books at Stage 2 and P (sweep touch and displayed size,
recorded prints, queue rule, maker fee 0, rebate), with three binding brackets: the touch rule agrees in sign, the
floor holds with the rebate halved, and the residual-unavailable worst case stays > 0 (§2.6 (vii)). Reported beside them: capacity; the break-even subsidy per
quote-hour against the distribution of the reward upper bound by formula (sidecar `clob_rewards`, `rewards_max_spread`,
`rewards_min_size`); the taker-exit variant. Not modelled, disclosed: re-pricing a quote during its life; latency of
detecting a large print (the rule is evaluated at print time, which a WebSocket maker could approach but not equal);
partial fills; our own impact on queue priority; the subsidy can be withdrawn.

**Verdict map.**
- A mechanism and its economic test both pass Stage 2 and the economic test passes Stage P → "prospectively supported
  selective-maker filter (paper)", with capacity and the subsidy comparison.
- Mechanism passes, economic fails → "adverse selection is concentrated as claimed, but the filter does not make the
  maker profitable at the touch at 2h life" (a component of any maker design, not a route).
- Mechanism fails at Stage 1 → that hypothesis closed at MDE (B entry exception aside).

**Compute.** Stage 1 (q0063): the pmxt table (≤ 44,000 rows), h2 trades per market (1,759 markets, read once), queue
fills, regressions, 20 placebo draws × 3 tests (re-flagging and re-fitting only), 200 random-filter draws × 3, 2,000
bootstrap: about 1 CPU-h, 1.5 GB. Stage 2 (q0066) and P (q0067): about 336,000 opportunities and their prints streamed
per pass: about 3 CPU-h each, 2.0 GB.

**Stop rule.** A B test that is testable at Stage 1 and does not advance is not read at Stage 2. No B test reaching
Stage 2 → q0066 exits 0 "nothing advanced" (the follow-up data stay collected; their use by a later design would
need its own freeze).

---

## 4. Code needed

### 4.1 Modules

- `backend/astrolabe/research_lab/cb3_quote_state.py` (A)
  - `load_quote_panel(extract_root, since, before)`: `quote_state/` files into a market × capture panel (gap rule as
    `bounce_decomp.build_snapshot_triples`).
  - `detect_onsets(panel)`: tight at i−1 and i (`bounce_decomp.h_tight_mask`), one-sided ≥ 5c / < 1c rule, exclusion
    counts by reason.
  - `recovery_mark(panel, onsets)`: first tight capture in {i+2, i+3, i+4}, unrecovered coding, closed-with-payout
    coding, gap-break exclusion.
  - `a_tests(units)`: R̂ (ratio of sums, `economics.boot_ratio`, delta-method z per way), G; robustness (sweep-confirmed
    subset, top-5 clusters).
  - `martingale_placebo(panel, onsets, seed)`: keeps the real onsets and rebuilds each onset market's mid from i+1 on
    from increments drawn with replacement from the market's pooled valid increments (the J4-R bootstrap of
    `bounce_decomp._rebuild_shuffled_levels`), observed half-spread path kept; re-applies the T rule;
    `bounce_decomp.placebo_reading` reused (item 2).
  - `a3_units(onsets, quote_state, followup)`: persistence, posting at s2, windowed fills, the 6h tight-sweep mark
    (item 3), net, worst case.
- `backend/astrolabe/research_lab/cb3_maker.py` (B)
  - `quote_opportunities_history(books, panel, frame)` (`cb1_history.load_books`, `asof_quote`) and
    `quote_opportunities_prospective(quote_state, followup, rows_ext)`.
  - `fills(opps, prints)`: both sides via `cb1_history.queue_fill` (and the touch variant), side conversion as
    `cb1_history.buys_longshot`, unavailable status by the CB1 truncation rule.
  - `marks(...)`: history `asof_quote` at +6h / +2h and the pmxt book-mid check; prospective tight-sweep rule and worst
    case.
  - `taker_orders(prints)`, `large_order_flags(orders)`, `life_fraction(...)`, `round_trip_share(...)`.
  - `filters`: retreat, schedule, top-decile; `u_baseline`.
  - `mech_test(df, regressor, controls, ways, placebo, week_fe=False)`: `bounce_decomp.expanding_demean` on the
    regressor and controls, raw target, generalised `bounce_decomp.fit_test` (max-SE over ways), the matched placebo and
    `placebo_reading`; reports pooled β, the draft's T and the within/between split (item 1).
  - `improvement_rule(...)`: random filters in the filter's own units, same population, fixed U denominator, strata
    incl. activity tercile (item 7); `econ_test(...)` with the touch-rule, half-rebate and worst-case brackets (items
    4, 6, 8).
  - `prints_union(pre, post, t)`: `ts < t` / `ts > t` filters and de-duplication (item 5); `visible_500(prints, t)`
    (ruling 1).
  - `reward_upper_bound(...)`, `breakeven_subsidy(...)`, `capacity(...)` (reuse `cb1_history.capacity`).
- Shared, **imported, not copied**: `cb1_history` (queue fill, as-of quote, cluster test, batch Holm, `log_trials`
  pattern, `require_declaration`, outcome-column guard), `bounce_decomp` (capture iteration, tightness, fit_test,
  placebo machinery), `economics` (fee table, `boot_ratio`; new `REBATE_SHARE` moved from
  `scripts/econ_conditions_maker.py`, which then imports it so its outputs stay identical), `ml_panel.dependence_group_ids`,
  `battery2.cumulative_count`, the CB2 small-G p-value.
- `HYPOTHESES_CB3` and `declaration_sha256()` covering every population, onset rule, threshold, window, fill rule,
  mark rule, filter, control set, placebo, floor, date and the category scope in this file.

### 4.2 Runner

`backend/scripts/run_cb3.py {census,screen,replicate,stagep,resolution} --family A|B`.
- Refuses run ids `h1_first`, `h3_power`, `h4_seal`, `h5_cb1`, `h5_cb1_ladders`, `h6_weather`.
- Refuses any row whose capture, onset capture or follow-up origin pass is in `T_J4R` (reading `T_J4R_end` from the
  committed J4-R record), and, for `screen --family A`, any capture with start ≥ `T3_A_dev_end`; `census --family P`
  starts at `max(T3_fu_start, T_J4R_end)` (item 11).
- Declaration-hash guard (committed `model_specs/cb3_v1.json` must equal the code's hash) on `screen`, `replicate`,
  `stagep`; `T3_rep_start` read from the committed pin file; `replicate` refuses before `T3_rep_end + T3_mark_lag`,
  `stagep` before `T3_P_end + T3_mark_lag`.
- `census` refuses to compute marks (guarded column list; unit test).
- Results under `research_lab/creative_batch3/<stage>_<family>/results.json`, never overwritten.

### 4.3 Data additions (collector and extractor)

#### 4.3.1 `quote_state/` table and the q0060 backfill (build spec; buildable now)

This subsection is self-contained so that an implementer can build q0060 before the freeze (challenger: q0060 may be
built and run before the response round with item 12's membership). It is data-only: no statistic is computed.

- **Code location.** A new table `quote_state` in `backend/astrolabe/research_lab/creative_batch1.py` (extractor
  version `cb1-extract-v3`), selected by `scripts/run_cb1_extract.py --tables quote_state`. CB1 and CB2 tables stay
  byte-identical (test). New flag `--backfill-before <UTC>` (exclusive upper bound on capture start).
- **Location.** Own root `data-dumps/research_lab/cb3_extract/` with its own `manifest.json`:
  - `cb3_extract/quote_state/<capture_id>.csv.gz` (rows, below);
  - `cb3_extract/quote_state/<capture_id>.ids.csv.gz` (one column `market_id`: every binary market present in the
    capture's `rows.csv.gz`, sorted; so "no row" can be told apart from "not in the capture"; item 12).
- **Inputs (read-only).** The capture's `rows.csv.gz` and `manifest.json` (state must be `complete`), its
  `rows_ext.csv.gz` when present (captures ≥ 2026-10-11T12:00Z), and the complete book sweeps whose manifest
  `snapshot_id` equals the capture id (`series_index` 0 = sweep 1, 1 = sweep 2; `bounce_decomp.load_sweep_mid`'s
  selection rule). No network request, no outcome field, no text field.
- **Membership (item 12).** A binary market (`binary == 1`) gets a row in capture c iff it is **E001-tight**
  (`bounce_decomp.h_tight_mask`: two-sided, `best_bid < best_ask < 1`, spread ≤ 0.10, mid in [0.02, 0.98]) in c **or
  in any of the 4 previous complete captures** in start order (no gap rule at extraction; the analysis applies it).
  So the path of a market tight at i is stored at i+1 … i+4 whatever its state. The extractor keeps a rolling set of
  the tight ids of the last 4 complete captures; at the start of a backfill (or after a missing capture) it computes
  that set from the 4 preceding complete captures on disk, and sets `membership_complete = false` in the manifest
  entry when fewer than 4 predecessors exist.
- **Row schema** (one row per member market; blank = unavailable, never 0):
  `capture_id, capture_start_utc, received_utc, market_id, condition_id, event_id, binary, best_bid, best_ask, spread,
  last_trade_price, volume_num, volume24hr, chg_1d, closed, active, end_date, tight` (0/1, E001 at c),
  `tight_mask_prev4` (4-bit string, oldest first), sidecar fields `accepting_orders, created_at, fee_category,
  fee_schedule, neg_risk_id, parent_event_ids, series_slugs` (blank before the sidecar), and for each sweep k ∈ {1, 2}:
  `s{k}_batch_receipt_utc, s{k}_state, s{k}_best_bid, s{k}_best_ask, s{k}_bid_size_1, s{k}_ask_size_1,
  s{k}_depth_bid_1c, s{k}_depth_ask_1c` (blank if the outcome-0 token was not swept). Values copied exactly as stored
  (no recomputation); float formatting as in the source.
- **Manifest entry per capture:** `capture_id, capture_start_utc, extractor_version, git_commit, n_rows, n_ids,
  n_tight, n_sweeps_found, membership_complete, source_sha256 {rows, rows_ext, sweep files}, sha256 {csv, ids},
  written_utc, mode (backfill|live)`.
- **Idempotency.** Keyed by `capture_id`: a capture already in the manifest with the same `extractor_version` is
  skipped; a different version refuses (a new version needs a new root). Writes go to a temp file and are renamed;
  the manifest is updated atomically after both files exist. Re-running after a crash completes missing captures only.
- **Disk caps.** The job refuses to start, and stops between captures, while host `data-dumps` exceeds 10.5 GB
  (`--data-dumps-max-gb 10.5`) or `cb3_extract/` exceeds its cap (`--disk-cap-gb 0.30` for q0060). Expected about
  70,000-90,000 rows and 2.5-3.5 MB per capture plus about 0.5 MB of ids, so about 0.15-0.2 GB for the about 50 dev
  captures.
- **Windows.** q0060 (backfill): every complete capture with start < **2026-10-15T21:00Z** (`T3_A_dev_end`), from the
  first complete capture on the host. **Captures in `T_J4R` are never read by q0060** (they are after its bound).
  Live (pass step, §4.3.2): every new complete capture, including those in `T_J4R` (data copying only; `run_cb3.py`
  refuses to load any `quote_state/` row whose `capture_start_utc` is in `T_J4R`, unit-tested).
- **Missing data.** A capture absent from the host is restored from its release copy (`scripts/restore_from_archive.py`)
  into a scratch directory if available; otherwise it is recorded as missing in the manifest and never fabricated.
  A sweep absent for a capture leaves the sweep columns blank (`n_sweeps_found` records it).
- **Retention.** `cb3_extract/` gets no deletion rule until q0067 (and q0068 for the fill tables) have run; after that,
  archive-before-delete as every other table. During the windows it is archived to releases daily by the rotation job
  once rotation is active (§8).
- **Tests.** Membership (a market tight only at c−4 has a row at c; at c−5 it does not); the ids file lists every
  binary market; idempotent rerun writes nothing; version mismatch refuses; disk caps refuse; `--backfill-before`
  excludes the bound; CB1/CB2 tables byte-identical; values copied exactly (fixture round-trip).

#### 4.3.2 Live pass steps and the follow-up trade step

- **`quote_state/` live** as its own line after the CB1/CB2 extract line (item 10):
  `timeout 600 nice -n 10 $PY scripts/run_cb1_extract.py --all-new --tables quote_state --data-dumps-max-gb 11 2>&1 | tail -1 || true`
  (self-limit 8 min, peak RSS ≤ 500 MB), so the CB1/CB2 600 s budget is untouched.
- **Follow-up trade step** `backend/scripts/sample_trades_followup.py`, its own line after that:
  `timeout 600 nice -n 10 $PY scripts/sample_trades_followup.py --snapshot latest --frac 0.5 --vacuum-max 300 --rps 4 --budget-s 540 2>&1 | tail -1 || true`
  (self-limit 9 min, peak RSS ≤ 500 MB; no earlier step or registered input changes).
  - **B subsample:** a seeded 50% Bernoulli draw (seed written to `plan.json` before the first request) of the previous
    pass's 2,000-market trade sample. For each: copy its pass-i rows from `trade_samples/<i>/trades.csv.gz` and
    `wallets.csv.gz` unchanged into `cb3_followup/<i+1>/pre/` (no request; before the 3-day retention), then fetch the
    window `(pass-i capture start, request time]` with **windowed `/trades?market&start&end&takerOnly=true` paging**
    (limit 1,000, offset pages, ≤ 5 pages; the `large_trade_census.anchor_trades` pattern; item 4) into
    `cb3_followup/<i+1>/post/`, with wallet hashes only (`WalletSidecar`), page-cap flags and request times. The
    step stores raw windows; **the analysis applies `ts < t` to pre/ and `ts > t` to post/ with t = the market's
    sweep-1 receipt, and de-duplicates the union** (item 5).
  - **Vacuum stratum (A3):** onsets at the current capture by the A rule (current and previous captures; tightness at
    i−1 from `quote_state/`), seeded uniform draw of ≤ 300 with inclusion probability recorded; their windows are
    fetched at the **next** pass (`cb3_followup/<i+2>/vacuum/`), same paging.
  - Markets are requested in a seeded random order; those not reached in the budget are missing (counted).
  - About 1,300-1,600 requests per pass (about 6-7 min at 4 rps), ≤ 0.3 GB RAM, about 0.5-1.5 MB per pass.
  - Reuses `trade_sample.parse_trades`, `httpx_transport`, `_atomic_csv_gz`, `WalletSidecar`. The probability sample's
    own outputs (E007/flow_screen inputs) are untouched (test).
- This is a collector change. Under the standing authorisation it is bounded, public and keyless; it adds about 7
  minutes of network-bound work per pass on the 1-OCPU host and, with `quote_state/`, about 1.3-2.0 GB per 28-day
  window of disk (§2.8), which makes archive rotation a dependency (§8).

### 4.4 Tests (`backend/tests/unit/test_cb3_quote_state.py`, `test_cb3_maker.py`, `test_cb3_followup.py`)

- Onset rule: ask and bid vacuum fixtures; a two-sided move (both sides ≥ 1c) is not an onset; tight at i−1 required;
  one-sided at i+1 counted, not tested.
- Recovery mark: first tight capture chosen; unrecovered coded `m_{i+1}`; a gap break excludes; a payout before T
  codes Y. A planted change after i+4 does not move R̂.
- R̂ ratio-of-sums and G on a synthetic world: a pure-noise toggling world gives R ≈ 1, G ≈ hs; a martingale world
  gives R ≈ 0; the martingale placebo keeps the real onset set and the half-spread path, changes mids only from i+1,
  and gives R ≈ 0 on a noise world (so it has power: item 2).
- A3: the mark is never before `t_fill + 6h` (a fixture where capture i+2 precedes `s2 + 2h`; item 3).
- The runner refuses `T_J4R` captures, A captures ≥ `T3_A_dev_end`, and the forbidden run ids.
- Queue fill: displayed size + 5 needed; a print exactly at t is excluded; fills of outcome-1 prints converted;
  truncated history gives unavailable, not unfilled.
- Taker-order aggregation; large-order flag needs ≥ 50 prior orders, uses strictly earlier orders, and the filling
  order is never its own trigger.
- Life fraction from scheduled `end_at`; `closed_time` never read by the LF code.
- Round-trip: the four-trade, both-signs, 10% net rule; window coverage required; RT undefined below 20 prints.
- Estimator: on a planted between-market-only association the expanding-past slope ≈ 0 while the pooled β ≠ 0; a
  planted within-market effect is recovered unshrunk; week FE absorb a planted common time trend in B3 (item 1).
- Placebos: the circular shift keeps each market's large-order count; the within-market permutation keeps each market's
  multiset; the reading rule voids a family whose placebo range excludes 0.
- Improvement rule: B2 random cancellations cancel the same number of quotes at offsets from the real distribution;
  B4 removes opportunities; B6 selects among RT-defined opportunities; the U denominator is fixed; a filter equal to U
  fails (item 7).
- Brackets: touch-rule sign check, rebate halved, residual-unavailable worst case each able to block a pass (items
  4, 6, 8); unknown category gives ρ = 0.
- Follow-up analysis: a pre/ print with ts ≥ t is dropped; a print in both pre/ and post/ counts once (item 5); a
  feature outside the visible 500 prints is unavailable (ruling 1).
- Marks: as-of +6h uses the 600 s lag; prospective tight-sweep rule and worst case; a planted price after the mark time
  is ignored.
- Rebate by category (geopolitics 0); maker fee 0; rewards never enter `net`.
- Census guard: no mark or T-capture mid column reachable.
- Follow-up step: seed sealed before requests; 50% draw reproducible; windowed paging covers the window or flags the
  page cap; no raw wallet in any file; the trade-sample directory is byte-identical after the step; 540 s budget,
  seeded request order and 429 stop.
- Extractor v3: §4.3.1 tests.
- `KIND_RULES` contains the CB3 kinds; the counter runs on the real `trials.jsonl`.

---

## 5. Draft queue specs

Paths follow `queue/README.md` (`argv[0]` under `backend/scripts/`, `cwd` `backend`). No spec is committed before its
code and tests exist; test jobs also need the reviewed CB3 freeze commit. The follow-up step is a pass step deployed by
`scripts/oracle/deploy.sh`, not a queue job.

```json
{"id": "q0060_cb3_quote_state_backfill", "title": "CB3-F: one-off quote_state/ extract from complete captures started before 2026-10-15T21:00Z (A dev window; no analysis)",
 "family": "creative_batch_3", "priority": 57, "expected_value": "preserves the CH35 dev inputs before raw captures become deletable",
 "data": ["research_lab/snapshots + book_sweeps on host (else release copies via restore_from_archive.py)"], "resources": {"mem_mb": 1000, "cpu": 1},
 "depends_on": [], "argv": ["scripts/run_cb1_extract.py", "--backfill-from", "2026-10-09T00:00Z", "--backfill-before", "2026-10-15T21:00Z", "--tables", "quote_state", "--budget-min", "150", "--disk-cap-gb", "0.30", "--data-dumps-max-gb", "10.5"],
 "timeout_s": 10800, "max_retries": 2, "repeat": {"max_runs": 2, "until_log_regex": "\"backfill_complete\": true"},
 "outputs": ["data-dumps/research_lab/cb3_extract/quote_state/", "data-dumps/research_lab/cb3_extract/manifest.json"],
 "next_action": "q0061 census", "notes": "Build spec: CREATIVE_BATCH_3.md §4.3.1 (schema, membership = E001-tight at c or any of the 4 previous complete captures, plus <capture_id>.ids.csv.gz). New flag --backfill-before (exclusive). Idempotent by capture_id + extractor_version; CB1/CB2 tables byte-identical; never reads T_J4R captures (all after the bound); missing captures restored from release or recorded missing; about 50 captures x 3-4 MB"}
```
```json
{"id": "q0061_cb3_census", "title": "CB3: pre-freeze census (A dev onset counts and exclusions; B h2/pmxt opportunities, fills, classification coverage, RT decile cuts; no marks)",
 "family": "creative_batch_3", "priority": 48, "expected_value": "testability, MDEs and frozen cuts before the freeze",
 "data": ["cb3_extract/quote_state (< T3_A_dev_end)", "history_sources/book_features/book_features.csv.gz", "history/h2_main (trades, frame, panel_H6h; no outcome file)"], "resources": {"mem_mb": 1500, "cpu": 1},
 "depends_on": ["q0060_cb3_quote_state_backfill", "q0003_books_finalize"], "argv": ["scripts/run_cb3.py", "census", "--family", "A,B"],
 "timeout_s": 5400, "max_retries": 1, "outputs": ["research_lab/creative_batch3/census.json", "trials.jsonl (1 cb3_descriptive)"],
 "next_action": "Claude session: insert counts into CREATIVE_BATCH_3.md; freeze after q0064", "notes": "outcome and mark guard; definitions hashed before run; floors not revised"}
```
```json
{"id": "q0062_cb3_screen_A", "title": "CB3-A: CH35 dev screen on quote_state/ before 2026-10-15T21:00Z (A1, A2; spread-kept placebo, 20 draws)",
 "family": "creative_batch_3", "priority": 48, "expected_value": "decides whether family A has a money route",
 "data": ["cb3_extract/quote_state (frozen dev capture list + sha256)", "model_specs/cb3_v1.json"], "resources": {"mem_mb": 1500, "cpu": 1},
 "depends_on": ["q0061_cb3_census"], "argv": ["scripts/run_cb3.py", "screen", "--family", "A", "--before", "2026-10-15T21:00Z", "--n-boot", "2000", "--placebo-draws", "20"],
 "timeout_s": 7200, "max_retries": 1, "outputs": ["research_lab/creative_batch3/S1_A/results.json", "trials.jsonl (2 cb3_test + count + placebo + descriptive)"],
 "next_action": "if A1 advanced: A3 enters Stage 2; ledger", "notes": "commit only after the CB3 freeze; declaration-hash guard; refuses T_J4R and later captures"}
```
```json
{"id": "q0063_cb3_screen_B", "title": "CB3-B: selective-maker screen on h2_main + pmxt books (B1-B6; U baseline; placebos and random filters)",
 "family": "creative_batch_3", "priority": 48, "expected_value": "which maker filters advance to prospective Stage 2",
 "data": ["history_sources/book_features/book_features.csv.gz", "history/h2_main (trades, prices, frame, panel)", "model_specs/cb3_v1.json"], "resources": {"mem_mb": 1500, "cpu": 1},
 "depends_on": ["q0061_cb3_census"], "argv": ["scripts/run_cb3.py", "screen", "--family", "B", "--run-id", "h2_main", "--n-boot", "2000", "--placebo-draws", "20", "--random-filter-draws", "200"],
 "timeout_s": 7200, "max_retries": 1, "outputs": ["research_lab/creative_batch3/S1_B/results.json", "trials.jsonl (6 cb3_test + count + placebo + descriptive)"],
 "next_action": "record advanced / not-testable tests; ledger", "notes": "commit only after the CB3 freeze; beyond-budget L1 label; seeded by HB2 F3/F7 (disclosed)"}
```
```json
{"id": "q0064_cb3_prospective_census", "title": "CB3: prospective dev-window census [T3_fu_start, 2026-10-25T00:00Z) (follow-up coverage, opportunities, fills, vacuum stratum, bytes per pass; no marks)",
 "family": "creative_batch_3", "priority": 48, "expected_value": "Stage-2 MDEs and the disk projection before the freeze",
 "data": ["cb3_followup (< T3_dev_end)", "cb3_extract/quote_state (< T3_dev_end, outside T_J4R)", "rows_ext"], "resources": {"mem_mb": 1200, "cpu": 1},
 "depends_on": ["q0061_cb3_census"], "argv": ["scripts/run_cb3.py", "census", "--family", "P", "--before", "2026-10-25T00:00Z"],
 "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch3/census_prospective.json"],
 "next_action": "Claude session: counts into the doc; challenger freeze check; CB3 freeze; pin T3_rep_start", "notes": "commit after 2026-10-25T00:00Z; disk projection > 1.5 GB per 28 d -> ask the user before T3_rep_start"}
```
```json
{"id": "q0065_cb3_rep_A", "title": "CB3-A: frozen Stage 2 on [T3_rep_start, T3_rep_end) (A1, A2 if advanced; A3 if A1 advanced)",
 "family": "creative_batch_3", "priority": 48, "expected_value": "prospective replication of the vacuum recovery and the filled re-quote",
 "data": ["cb3_extract/quote_state (frozen rep list + sha256)", "cb3_followup vacuum stratum", "Gamma payouts of units closed before T (if any)"], "resources": {"mem_mb": 2000, "cpu": 1, "network": "gamma-api"},
 "depends_on": ["q0062_cb3_screen_A"], "argv": ["scripts/run_cb3.py", "replicate", "--family", "A", "--n-boot", "2000", "--placebo-draws", "20", "--rps", "4"],
 "timeout_s": 18000, "max_retries": 1, "outputs": ["research_lab/creative_batch3/S2_A/results.json", "trials.jsonl"],
 "next_action": "Bonferroni interim; batch Holm with q0066", "notes": "commit after T3_rep_end + 12h; exits 0 'nothing advanced'"}
```
```json
{"id": "q0066_cb3_rep_B", "title": "CB3-B: frozen Stage 2 on the follow-up sample [T3_rep_start, T3_rep_end) (advanced or not-testable B tests)",
 "family": "creative_batch_3", "priority": 48, "expected_value": "prospective replication of the maker filters at recorded books",
 "data": ["cb3_followup (rep window)", "cb3_extract/quote_state (rep window, marks to +10h)", "rows_ext"], "resources": {"mem_mb": 2000, "cpu": 1},
 "depends_on": ["q0063_cb3_screen_B"], "argv": ["scripts/run_cb3.py", "replicate", "--family", "B", "--n-boot", "2000", "--placebo-draws", "20", "--random-filter-draws", "200"],
 "timeout_s": 14400, "max_retries": 1, "outputs": ["research_lab/creative_batch3/S2_B/results.json", "trials.jsonl"],
 "next_action": "batch Holm over S2_A + S2_B; Stage P list", "notes": "commit after T3_rep_end + 12h; streams per pass"}
```
```json
{"id": "q0067_cb3_stageP", "title": "CB3: Stage P on [T3_P_start, T3_P_end) for Stage-2-passing economic tests (A3, B2, B4, B6)",
 "family": "creative_batch_3", "priority": 48, "expected_value": "the prospective economic check",
 "data": ["cb3_followup + quote_state (Stage P window)", "rows_ext"], "resources": {"mem_mb": 2000, "cpu": 1},
 "depends_on": ["q0065_cb3_rep_A", "q0066_cb3_rep_B"], "argv": ["scripts/run_cb3.py", "stagep", "--n-boot", "2000", "--placebo-draws", "20", "--random-filter-draws", "200"],
 "timeout_s": 14400, "max_retries": 1, "outputs": ["research_lab/creative_batch3/SP/results.json", "trials.jsonl (cb3_prospective + count)"],
 "next_action": "verdicts per §3 maps; ledger; q0068 resolution marks at T3_res_out", "notes": "commit after T3_P_end + 12h; exits 0 'nothing passed Stage 2'"}
```
```json
{"id": "q0068_cb3_resolution_marks", "title": "CB3: resolution mark-outs for Stage 2 and P fills (reported only, not counted)",
 "family": "creative_batch_3", "priority": 46, "expected_value": "hold-to-resolution view of the maker fills",
 "data": ["S2/SP fill tables", "Gamma outcomes"], "resources": {"mem_mb": 800, "cpu": 1, "network": "gamma-api"},
 "depends_on": ["q0067_cb3_stageP"], "argv": ["scripts/run_cb3.py", "resolution", "--rps", "4"],
 "timeout_s": 7200, "max_retries": 2, "outputs": ["research_lab/creative_batch3/resolution.json", "trials.jsonl (cb3_descriptive)"],
 "next_action": "append to the CB3 write-up", "notes": "commit after T3_res_out; one outcome request per distinct market (estimate 20-40k, about 1.5-3 h at 4 rps; collector-health pause as CB2 §2.8); CB1 censoring rule"}
```

## 6. Test budget and compute

| Job | Tests counted | Kind(s) |
|---|---|---|
| A Stage 1 (A1, A2) | 2 | `cb3_test` + count line |
| B Stage 1 (B1-B6) | 6 | `cb3_test` + count line |
| U baseline, census, sports stratum, reward scenarios, resolution marks | 0 | `cb3_descriptive` |
| Stage 2 (A1, A2, A3, B1-B6 that advanced or entered) | ≤ 9 | `cb3_replication` + count lines |
| Stage P (A3, B2, B4, B6 that passed) | ≤ 4 | `cb3_prospective` + count line |
| **Total** | **8 fixed + up to 13 conditional (8-21)** | |

Families: Stage 1 per-test gate (p < 0.01, BY label as triage); Stage 2 one Holm family (α = 0.05, k ≤ 9); Stage P
one Holm family (α = 0.05, k ≤ 4).

**Host compute.**
- Queue jobs about 12-13 CPU-hours over two months at nice 19 (A about 4.5, B about 7, census and backfill about 1.5),
  peak 2.0 GB; within the 15 CPU-hour cap per family.
- Pass steps (own lines, item 10): follow-up about 1,300-1,600 Data API requests per pass (about 6-7 min wall,
  network-bound, ≤ 0.3 GB, 9-minute self-limit); `quote_state/` about 10-30 s per pass.
- Disk: about 4-6 MB per pass with the item-12 membership (about 1.3-2.0 GB per 28-day window; 3-4.5 GB for dev +
  Stage 2 + Stage P if nothing is rotated off the host), measured by q0064, under the §2.8 guard. Depends on archive
  rotation (§8).
- Network: q0068 about 20-40k Gamma requests; q0065 a handful.

## 7. Main scientific risks

1. **Between-market confounding (the J4 lesson).** Large-print, late-life, round-trip and vacuum markets may simply
   be different markets. The timing-component estimator with placebos matched to each regressor (§2.6) addresses this
   for the mechanisms; the stratified random-filter rule addresses it for the economics. A filter that only selects
   better markets can still pass the economic test (that is legitimate money) but cannot be credited to its stated
   mechanism unless the mechanism test passes too.
2. **Selection on the path in A.** Requiring tight at i−1 and i, wide at i+1 and tight at T conditions on the quote
   path. The spread-kept placebo checks that the construction does not create recovery; the unrecovered-as-informative
   coding keeps recovery from being manufactured by dropping slow recoveries. A Gamma-cache artefact (the Gamma touch
   lags the CLOB) would look like a recoverable vacuum; the sweep-confirmed robustness guards it.
3. **Fill model optimism and pessimism.** Static 2h quotes, all-or-nothing queue fills, cancellations ahead ignored,
   no re-pricing, 6h-grid books in history. The queue rule is the honest choice made by the economic study; the touch
   rule is reported. History marks are the price series (mid-like, unverified; 0.75c mean gap to pmxt books),
   prospective marks are tight sweep mids with a worst case; the two stages measure slightly different things.
4. **Seeded and worn Stage 1.** B1/B3 are seeded by HB2 F3/F7 on the same h2 trades; A dev is the J4 diagnosis window.
   Stage 1 is a stop rule; evidence comes from Stage 2 and P. The B entry exception (not testable → Stage 2) needs a
   ruling.
5. **CH41 construct.** The within-market round-trip share is a narrower hypothesis than "farmer flow": it misses
   cross-market airdrop farmers and maker-side farmers. It was chosen because it is observable identically in both
   stages.
6. **Sample sizes are estimates.** The pmxt table is not finished; onset and fill counts come from analogous studies,
   not from the census. B5 is probably underpowered on h2. The census decides testability; floors are not revised.
7. **Collector load and disk.** The follow-up step and `quote_state/` add about 7 minutes and 4-6 MB per pass on a
   1-OCPU host whose `data-dumps` was 7.6 GB of a 12 GB cap at 2026-10-16T03:56Z and grows about 1 GB a day until
   archive rotation deletes verified copies. Without rotation the host reaches the cap around 22 October, before any
   CB3 window starts (§8). Missing passes stay missing.
8. **Rewards and venue rules.** Rewards are excluded from every primary; they can dominate maker economics and can be
   withdrawn. Heartbeat cancel-all, cancel-only mode and book clears (the April 2026 upgrade, the 2026-08-31 halt) are
   regime events inside the pmxt window; they are not removed (no post-hoc exclusions), and their dates are reported.
9. **Calendar overlap.** Stage 2 and P overlap CB1, CB2 and E011 in calendar time; statistics and inputs are disjoint.

## 8. Next actions

1. Challenger round 1 is done and its response is applied (sections below). This is the single response round, as in
   CB1/CB2. The next review is the code-against-design freeze check.
2. **Now (allowed before the freeze):** delegate q0060 to `implementer` from the §4.3.1 build spec (extractor v3
   `quote_state` table + `--backfill-before`), test, commit the spec and run it.
3. Delegate the rest to `implementer`: `quote_state/` live line and `sample_trades_followup.py` (+ pass-step lines,
   §4.3.2), `cb3_quote_state.py`, `cb3_maker.py`, `run_cb3.py`, `economics.REBATE_SHARE`, `KIND_RULES`, tests (§4).
   Deploy the pass steps as early as possible (data only).
4. After q0003 and q0060: q0061 census; after `T3_dev_end`: q0064 (window from `T_J4R_end`); insert counts and the
   Stage-2 MDEs here; science-reviewer freeze check; CB3 freeze (`model_specs/cb3_v1.json`) before 2026-10-26T22:00Z so
   that `T3_rep_start` can stay at 2026-10-27T00:00Z if rotation is active; pin it.
5. Then q0062 and q0063; q0065/q0066 after `T3_rep_end` + 12h; q0067 after `T3_P_end` + 12h; q0068 after `T3_res_out`.

**Open questions (draft round; resolved by challenger round 1).** 1 CH41: accepted as CH41-narrow with the 500-print
visibility in history (ruling 1). 2 Collector: follow-up step and `quote_state/` accepted with items 4, 10, 12; the
unit-row recorder rejected (ruling 2). 3 Entry exception: accepted, with q0064 stating Stage-2 MDEs (ruling 3).
4 Marks: price series kept at Stage 1, pmxt check binding on sign and floor (ruling 4). 5 Unrecovered coding:
accepted, i+4 mid and recovered-only reported (ruling 5). 6 Estimator: expanding-past within-market slope (item 1).
7 CH39 window: accepted, B2 on classifiable markets only (ruling 7). 8 Intra-hour pmxt paths: not required (ruling 8).

**User decisions.**
1. **Disk and archive rotation (open; challenger item 13).** Every CB3 window depends on it.
   - *Context.* On 15 October the user approved deleting server copies that are verified in a backup; the nightly
     deletion job is in a one-night dry-run trial. Host data was 7.6 GB of a 12 GB cap at 2026-10-16T03:56Z and grows
     about 1 GB a day, so without rotation the cap is reached around 22 October.
   - *What CB3 needs.* Before `T3_rep_start`: (a) the nightly verified-backup deletion live for `snapshots/` and
     `book_sweeps/` under their deferred rules, once their readers allow (J4-R needs `T_J4R` captures until q0035 has
     run); (b) daily archiving of `cb3_extract/` and `cb3_followup/` to releases so that host copies older than 3 days
     can be deleted after verification and restored by the analysis jobs (`restore_from_archive.py`). CB3's own growth
     is about 1.3-2.0 GB per 28 days.
   - *Fallback if rotation is not active.* The CB3 writers pause above 11 GB and jobs refuse above 10.5 GB (§2.8);
     paused passes stay missing and are never backfilled. `T3_rep_start` is the first UTC day at which rotation is
     verified active (§1.2), pinned at the freeze before any rep row is read, so no window is silently shortened; if
     rotation is still not active on 2026-11-10, CB3's prospective stages are suspended and recorded, and only the
     Stage-1 results stand. The q0060 backfill (about 0.2 GB) needs no rotation.
   - *Recommendation.* Activate the nightly deletion after the dry run is checked, before about 20 October.
2. Sports: stay a reported stratum unless the user includes them (category scope parameter).

---

## Challenger review, round 1 (science-reviewer, 2026-10-16T04:31Z): ACCEPT_WITH_REQUIRED_CHANGES

(The reviewer is read-only; the coordinator pasted this text verbatim.)

Checked: count 993 (ml_explain 431, flow_screen 275, econ_conditions_taker 95; local run); J4 figures; part B fill
rates 6-19%; the F3 look-ahead rule; maker rebate share (REBATE) and the queue rule (`queue_fill`).

**REQUIRED**
1. **Mechanism estimator (Q6).** `T = β − mean β_placebo` only gives the within-market slope shrunk by the
   within-market share of the regressor's variance, so the floors mean nothing for B5. Primary: J4-R's expanding-past
   within-market slope, its matched placebo and its reading rule. Report T and the within/between split (SB2
   consequence 5). Add calendar-week fixed effects to B3 (within a market, life fraction moves one-for-one with time).
2. **A placebo has no power.** In the rebuilt world an onset needs the mid change to equal the half-spread change to
   within 1c, so placebo onsets are rare and the void check toothless. Primary: keep the real onsets, rebuild the mid
   from i+1 as a bootstrapped martingale and re-apply the T rule. Report placebo onset counts, with a minimum.
3. **A3 mark can precede the fill.** Capture i+2 starts before s2+2h. Use the B rule: first tight sweep at or after
   t_fill + 6h.
4. **Truncation.** "Counted, reported" breaks CB1 §2.2 (CREATIVE_BATCH_1.md:139-151), which requires a binding worst
   case. Fetch the post window with windowed `/trades?start&end` paging (large_trade_census.py:384-391); any residual
   unavailable quote gets a binding worst case.
5. **pre/ is not "before t".** The trade sample runs after the sweeps and stores trades up to request time
   (trade_sample.py:296-299 filters only inside features). Filter `ts < t` explicitly; dedupe the pre/ ∪ post/ union.
6. **Rebate ≥ floor.** ρ·r·¼ ≈ 0.25-0.35c per filled share at mid matches or beats the 0.25c B floor, and the allocation
   is undocumented. Floors must hold with the rebate halved (binding). Unknown category → ρ = 0
   (econ_conditions_maker.py:23).
7. **Improvement-rule denominators.** Random filters must act in the filter's own units (B4 removes opportunities; B2
   cancels quotes at random times). EV per quote over a fixed U denominator and the same population (B2: classifiable
   markets; B6: markets where RT is defined). Add an activity stratum.
8. **Fill bracketing.** Ignoring cancellations is conservative for fill counts only, not toxicity. For economic passes
   the touch rule must agree in sign (binding).
9. **Testability.** State that the 28-day UTC-day way uses only the small-G rule, not the ≥ 30 cluster rule.
10. **Host limits.** `timeout 720` breaks the 10-min / 500 MB pass limit (CREATIVE_BATCH_1.md:321). Write
    `quote_state/` after the CB1/CB2 tables or as its own step, so the CB1/CB2 600 s budget is untouched.
11. **J4-R.** q0064's window holds vacuum strata built from T_J4R captures. Start it at J4-R's actual end.
12. **`quote_state/` membership too narrow.** A market wide at i+1 and i+2 has no row at i+2, and the placebo needs full
    paths. Store every binary market tight at any of the last 4 captures, plus a per-capture list of market ids.
13. **User decision.** Disk fills around 22 Oct without archive rotation (AREPO_V2_CHECKPOINT.md:49,163); every CB3
    window depends on it. Name it; "None required" is wrong.

**Optional:** book-age sensitivity (`sw_book_age_s`); relabel A2 as a mechanism test; report A1/A2 on the A3-eligible
stratum; code closed markets with no payout as unrecovered; one summary placebo line per test instead of about
1,200; restate Stage-2 MDEs allowing for overlapping 6h marks and the day way.

**Rulings**
1. Accept the within-market round-trip share, labelled CH41-narrow; use the prospective 500-print visibility in
   history too.
2. Accept the follow-up step and `quote_state/` with items 4, 10 and 12. Reject the unit-row recorder (no placebo panel).
3. Accept the entry exception; state the Stage-2 MDE from q0064 before the freeze.
4. Keep the price series at Stage 1, but the pmxt-mark check keeps both sign and floor (the 0.75c source gap exceeds the
   floor).
5. Accept the coding; report the i+4 mid and the recovered-only result.
6. See item 1.
7. Accept; B2 on classifiable markets only.
8. Not required.

**q0060** may be built and run before the response round, but only with item 12's wider membership. It is data-only,
uses captures before T3_A_dev_end and never T_J4R, and can be rerun from release copies.

**Not verified:** HB2-R (q0010) status, host disk use, release copies for 9-15 Oct captures, actual `quote_state/` size.

## Response to challenger round 1

Drafting session, 2026-10-16T05:05Z. All 13 required items, all rulings and all optional items are adopted (two with a
modification, stated). This is the single response round; the next review is the code-against-design freeze check.

| Item | Response | Where |
|---|---|---|
| 1 Mechanism estimator | **Adopted.** Primary for B1, B3, B5 is J4-R's expanding-past within-market slope (`bounce_decomp.expanding_demean`, raw target), its matched placebo (20 draws) and the J4-R reading rule (void / inconclusive-placebo-bias). Floors apply to that slope. Pooled β, the draft's T and the within/between split are reported. B3 has calendar-week fixed effects. MDEs restated (about 1.3-1.6× the draft's on h2). *Modification:* B5's unit is the quote opportunity (EV per quote, 0 if unfilled), because RT is an opportunity-level variable and must vary within market across opportunities, matching item 7's denominator | §2.4, §2.6, §CB3-B tests and MDE, §4.1, §4.4 |
| 2 A placebo power | **Adopted.** The placebo keeps every real onset and rebuilds the mid from i+1 on as a bootstrapped martingale (market-pooled increments), observed half-spread path kept, T rule re-applied. Placebo units reaching a tight T and capture clusters are reported per draw; minimum 1,000 onsets and 30 capture clusters, else the A family is not testable | §2.6, §4.1, §4.4 |
| 3 A3 mark before fill | **Adopted.** A3 uses the B mark (first E001-tight first-sweep mid at or after `t_fill + 6h`, next pass within 4h, else far-touch worst case); `m_T` is never used for A3 | §CB3-A A3 rule, §4.4 |
| 4 Truncation | **Adopted.** The follow-up step fetches the post window by windowed `/trades?market&start&end&takerOnly=true` paging (limit 1,000, ≤ 5 pages, `large_trade_census.anchor_trades` pattern). Every residual unavailable quote (page cap, history truncation) enters a binding worst case: only the side with the lower mark-out fills, marked at the far touch, no rebate; the economic estimate with these added must stay > 0 | §2.1, §2.6 (vii), §4.3.2 |
| 5 pre/ not before t | **Adopted.** The step stores raw windows; the analysis applies `ts < t` to pre/ and `ts > t` to post/ (t = the market's sweep-1 receipt) and de-duplicates the union on (`tx_hash`, `asset`, `side`, `size`, `price`, `ts`) | §1.1, §2.2, §4.3.2, §4.4 |
| 6 Rebate ≥ floor | **Adopted.** Every economic floor and sign must also hold with the rebate halved (binding). Unknown category → ρ = 0 | §2.1, §2.4, §2.6 (vii) |
| 7 Improvement-rule units | **Adopted.** Random filters act in the filter's own units: B2 cancels the same number of quotes at offsets drawn from the real rule's cancellation-offset distribution; B4 removes opportunities; B6 selects among RT-defined opportunities. EV per quote over the fixed U denominator of the same population (B2 classifiable markets, B6 RT-defined). Activity tercile added to the strata | §2.6, §CB3-B, §4.1 |
| 8 Fill bracketing | **Adopted.** For every economic advance or pass, the touch-rule estimate must agree in sign (binding); the text no longer calls ignoring cancellations conservative for toxicity | §2.1, §2.6 (vii) |
| 9 Testability | **Adopted.** The 28-day UTC-day way is governed only by the CB2 small-G rule | §2.3 |
| 10 Host limits | **Adopted.** `quote_state/` and the follow-up step are separate lines after the CB1/CB2 extract, each `timeout 600` with self-limits of 8 and 9 minutes and peak RSS ≤ 500 MB; the CB1/CB2 600 s budget is untouched. The follow-up requests markets in a seeded random order so that budget cut-offs drop a random subset | §2.8, §4.3.2 |
| 11 J4-R window | **Adopted.** `T_J4R` now ends at J4-R's actual final `--until`; q0064's window starts at `max(T3_fu_start, T_J4R_end)`; no row tied to a `T_J4R` capture, onset or origin pass is read by any CB3 analysis or census; `T3_dev_end` moves forward by whole days if fewer than 3 days remain | §1.2, §1.3, §2.7, §4.2 |
| 12 `quote_state/` membership | **Adopted, with a modification.** Membership is "E001-tight at the capture **or any of the 4 previous** complete captures" (the challenger wrote "any of the last 4 captures"; the A rule needs the path at i+1 … i+4 of a market tight at i, which is 4 captures back at i+4), plus a per-capture `<capture_id>.ids.csv.gz` of every binary market. Size re-estimated at 3-4 MB per capture | §4.3.1, §2.8, §6 |
| 13 User decision | **Adopted.** Named in §8 as an open user decision: archive rotation (verified-backup deletion approved 15 October, nightly job in dry-run trial; host 7.6 GB of 12 GB at 03:56Z, cap reached about 22 October without rotation). States what CB3 needs (rotation live for snapshots/sweeps once readers allow, plus daily archiving of `cb3_extract/` and `cb3_followup/`) and the fallback (writers pause, `T3_rep_start` waits for verified rotation, suspension recorded if not active by 2026-11-10; q0060 unaffected) | §1.2, §2.8, §6, §7 risk 7, §8 |
| Optional: book age | Adopted (reported): drop quotes with pmxt `sw_book_age_s` > 3600 s | §2.6 |
| Optional: A2 label | Adopted: A2 is a mechanism test (unconditional re-quote value); floor unchanged | §2.4, §CB3-A |
| Optional: A3-eligible stratum | Adopted (reported): A1/A2 on onsets swept at i+1 and persistent | §2.6, §CB3-A baselines |
| Optional: closed without payout | Adopted: coded unrecovered | §CB3-A population |
| Optional: one placebo line per test | Adopted: one summary placebo line per test | §2.6, §CB3-A, §CB3-B |
| Optional: Stage-2 MDEs | Adopted: restated with overlapping 6h marks (design effect about 10) and the small-G day way; superseded by q0064's stated MDEs | §CB3-B MDE |
| Ruling 1 | Adopted: "CH41-narrow" everywhere; history uses the newest-500-prints visibility for origin features | §0.1, §2.1, §CB3-B |
| Ruling 2 | Adopted (with items 4, 10, 12); unit-row recorder dropped | §4.3 |
| Ruling 3 | Adopted; q0064 states every Stage-2 MDE before the freeze | §2.3, §2.7 |
| Ruling 4 | Adopted: the pmxt-mark check must keep sign **and** floor | §2.6 (iii) |
| Ruling 5 | Adopted: i+4 mid and recovered-only reported | §2.6, §CB3-A baselines |
| Ruling 6 | See item 1 | - |
| Ruling 7 | Adopted: B2 on classifiable markets only | §CB3-B tests, §2.6 |
| Ruling 8 | Noted: no intra-hour pmxt paths | §8 |
| q0060 | Build spec made self-contained (schema, item-12 membership, ids file, location, idempotency, disk caps, `T_J4R` never read, missing-data and retention rules, tests); queue draft updated (cap 0.30 GB) | §4.3.1, §5 |

Test count unchanged: 8 fixed + up to 13 conditional (A2 relabelled, still counted). The "not verified" items (HB2-R
status, host disk use, release copies for 9-15 October captures, actual `quote_state/` size) are carried into q0060's
manifest (sizes, missing captures) and q0064's census.

## Implementation notes (CB3)

Written by the implementing session, 2026-10-16, after the DRAFT-REVISED text (a767ab8). The code is NOT frozen: no
`model_specs/cb3_v1.json` exists, so every counted run is refused. The declaration hash of the first code state was
`24f33c360214410878accf4d68075b38a84c9ca0610d8c64b5a424c78803222f` (superseded; current hash in the freeze-check fix status below) (`cb3_declaration.declaration_sha256()`); it changes with any rule, band, floor, date, placebo or estimator in
`cb3_declaration.py`. Each item below is an ambiguity resolved with the most conservative reading for research integrity.
A reviewer should confirm or overturn each at the code-against-design freeze check.

**Files.** `cb3_declaration.py` (HYPOTHESES_CB3, constants, hash, guards, pin), `cb3_common.py` (multi-way CR1 mean / ratio / slope
tests, CB2 small-G rule via `cb2_weather.small_g_pvalue`, placebo reading, trial logging, batch Holm), `cb3_quote_vacuum.py` (A),
`cb3_maker.py` (B and the shared paper maker), `cb3_followup.py` + `scripts/sample_trades_followup.py` (post-window step, NOT wired into
`arepo_pass.sh`), `scripts/run_cb3.py`. `economics.REBATE_SHARE` (new; `econ_conditions_maker.REBATE` now aliases it, identical
values) and four additive `battery2.KIND_RULES` entries (`cb3_test`, `cb3_replication`, `cb3_prospective`, `cb3_descriptive`, all
EXCLUDE). Two files beyond the requested list (`cb3_common.py`, `cb3_followup.py`) because the logic is shared or must be importable by tests.

**Units and floors.** Everything is in price units (1c = 0.01); the declared floors are stored as 0.60 (R), 0.005 (A2, A3 net),
0.0025 (B economic), -0.005 / -0.010 / +0.010 (B1 / B3 / B5 slopes).

**Family A.**
1. *Placebo reading for A2.* The literal rule voids a test whose placebo range excludes 0, but the declared A placebo makes
   `G_placebo ~ mean(hs - |D|)`, which is negative by construction, so applying it to A2 would void A2 always. The void and bias checks
   are applied to A1 (R); A2's placebo G is reported as a construction check and A2 inherits the family status of A1 (void or bias on A1
   blocks both). Placebo units below 1,000 or capture clusters below 30 in any draw block the advance.
2. *dep_group in A.* `quote_state/` carries `neg_risk_id` and `parent_event_ids`, not the fixture-day link fields `ml_panel.dependence_group_ids`
   needs. `dep_group := neg_risk_id, else the first parent event id, else the event id` (the event fallback share is reported in the census).
3. *Closed markets.* The dev screen reads no outcome and has no payouts, so every market closed before T is coded unrecovered
   (`closed_no_payout`, `m_T := m_(i+1)`). `recovery_mark` accepts a payouts mapping (`closed_payout`, `m_T := Y`) for Stage 2; the Gamma
   fetch of payouts is not wired into the runner (q0065 would need it).
4. *Window end.* A unit whose window runs past the last loaded capture before T is excluded and counted (`window_end`), like a gap break.
5. *Persistent / sweep-confirmed.* A side missing in a sweep (one-sided book) counts as not persistent and not sweep-confirmed
   (conservative). Swept at i+1 = spread at the capture <= 0.10 and both sweeps present.
6. *Top-5 robustness (A).* Clusters are ranked by the absolute sum of `0.5|D| - s(m_T - m_i)` (A1) or of `g` (A2); the estimate must keep
   the floor (R >= 0.60, G >= 0.5c) without them, in each of the three ways.
7. *Loader and J4-R.* `load_quote_panel` takes an explicit window and refuses ANY selected capture in T_J4R (the live extractor writes them
   into the same root); `T_J4R_end` is read from the `--until` of the committed q0035 spec and fails closed. The follow-up step reads
   `quote_state/` with the guard disabled because it only copies data.
8. *A3 fills.* The re-quote is posted at the second sweep's receipt and the windowed vacuum prints are read from `cb3_followup/<i+2>/vacuum`;
   a window that was not reached, failed or hit the page cap is passed as truncated, so an empty file never reads as "not filled".

**Family B and the maker.**
9. *Unavailable fills.* The status is -1 whenever a truncated market's oldest stored print is later than the quote's posting time, even if
   the stored prints already complete the queue (the true fill time would be earlier and unknown). Residual unavailable quotes and
   mark-unavailable fills enter the worst-case bracket: for a quote, only the side with the lower far-touch mark-out fills; no rebate.
10. *History far touch.* History has no book at the mark time; the far touch is the mark -/+ the entry half-spread. A market with no price
    point at all is a total loss (buy value 0, sell value 1).
11. *Populations.* B2: classifiable markets; B4: opportunities with a defined life fraction (LF needs both scheduled anchors; undefined LF
    cannot be filtered, so it leaves the population, a pre-t rule); B6: RT-defined. EV per quote is the sum of kept net over 2 (5 shares
    each over 10 quoted share-sides) over the fixed population size.
12. *B2 cancel rule.* A fill at or before the first large order after posting counts (a maker cannot react to the order that fills it).
13. *B1 circular-shift placebo.* The large-order stream of a market is the union of large orders flagged in any of its fill streams; its
    span is the first to last stored print (history) or the fills' range padded by 3 days (prospective, where the builder keeps no raw
    stream). Markets with a span under 2 days use an offset of half the span.
14. *Slope robustness.* The top-5 clusters are ranked by the absolute sum of `x~ (y - ybar)` with `x~` the expanding-demeaned regressor. The
    small-G form for the UTC-day way of a slope tests the mean of `x~ y~` (score-mean form of the CB2 rule); ways at Stage 1 are event and
    dep_group only.
15. *Weighted sign.* Mechanism tests compare the design-weighted expanding slope (`sample_weight`, Stage 1 only) in sign; economic tests the
    weighted mean net. Prospective weights are `1 / (pi x frac)` from the follow-up `plan.json`.
16. *Union key.* `pre/` and `post/` share no transaction id (the trade sample's wallets file has none), so the cross-source key is
    (side, outcome, price, size, ts, wallet hash); identical prints inside one source are kept.
17. *Frozen cuts.* The RT top-decile cut and the activity tercile cuts are not part of the hash (they exist only after q0061); they live in the
    committed spec's `frozen_cuts` and `screen` refuses without them. The census emits a `frozen_cuts_proposal`.
18. *Prospective builder.* The origin is a market's first sweep of pass j; only markets in the seeded subsample (`pre/wallets.csv.gz`)
    enter; prospective 24h price change is not available, so `abs_chg_24h` is NaN there (rows drop from the regression, disclosed; Gamma
    `chg_1d` is in `quote_state/` and can replace it only by a declaration change).

**Follow-up step layout (assumed, to be reconciled with the deploy).** `cb3_followup/<c>/{plan.json, pre/{trades,wallets}.csv.gz,
post/trades.csv.gz, vacuum/trades.csv.gz, vacuum_plan.json, meta.json, manifest.json}` for capture `c` = pass i+1; `pre` is read from
`wallets.csv.gz` (hashed wallets, same rows as the trade sample); trades carry hashed wallets and no `trade_key` (the project key embeds the
raw wallet). The subsample is a hash-based Bernoulli draw (`sha256(seed|market_id)`), reproducible from `plan.json`.

**Census.** `census_history` builds no marks and reads no price series; its frames are asserted free of `CENSUS_FORBIDDEN_COLUMNS` and
mark columns (unit-tested with the mark methods patched to raise). `census_prospective` states the Stage-2 MDEs from counts with the design's
outcome SDs as stated assumptions and an assumed within-market correlation of 0.25 for the repeated-market design effect.

**Not done.** The reported-only items: reward scenarios and break-even subsidy, the taker-exit variant, sign by month / week and by category,
the 2h-mark and resolution mark-outs in the results (the 2h mark-out is computed per fill, not summarised), and the `resolution` subcommand
(guarded, exits 2). Analysis queue specs q0062, q0063, q0065-q0068 are not created (the freeze comes first); only the census specs q0061 and
q0064 are committed. `arepo_pass.sh` is untouched.

## Freeze check (science-reviewer, 2026-10-16T05:39Z): CB3 code against the design
(The reviewer is read-only; the coordinator pasted this text, lightly condensed.)
Code: 1d3ab59, 6186dfa, d125465, a0e7518, b431e88, 6c828eb. 95 scoped tests pass; declaration hash reproduces as `24f33c36…`;
no `cb3_v1.json`, no rep pin.

**Verdicts:** q0060 extractor/spec REVISE (1-2 URGENT); declaration/hash/runner REVISE (3 before q0061, 4 before any spec);
family A ACCEPT_WITH_REQUIRED_FIXES; family B/maker REVISE; follow-up step REVISE (before deploy); `REBATE_SHARE` swap ACCEPT
(identical values; geopolitics 0 = old default); KIND_RULES ACCEPT; q0061/q0064 specs REVISE.

**Rulings on the implementation notes:** A2 void check on A1 only (note 1) accepted (under the placebo G − mean s(q − m_{i+1})
= −mean s(m_T′ − m_{i+1}), A1's R quantity up to weighting); add a binding *centred* A2 bias check on that difference.
Unavailable-fill rule (note 9) accepted (conservative, CB1 §2.2). `cb3_followup/` layout accepted with fixes 7-9. Frozen cuts
outside the hash (note 17) acceptable only if the spec carries `frozen_cuts_sha256` and the `census.json` sha, the runner checks
the cuts equal `frozen_cuts_proposal`, the spec blob can never change after its first commit (`spec_committed` only compares
with HEAD, `cb3_declaration.py:274-284`), and every result and trial line records the cuts hash. Notes 2-8 and 10-16 accepted;
note 18 rejected (fix 11).

**Required fixes**
1. **URGENT (deadlock).** Over 10.5 GB the job exits 1 (`run_cb3_quote_state.py:69`); with `max_retries` 2 it ends `failed`
   after about 35 min while snapshot deletion waits for q0060. Refuse only on real headroom (output ≤ 0.3 GB under 12 GB).
2. **URGENT (silent incompleteness).** Budget, `disk_cap` and lock stops exit 0 (`cb3_quote_state.py:266-271`); with
   `repeat.max_runs` 2 the job becomes `done` with `backfill_complete` false, and the retention gate opens on job status. Make
   `disk_cap` non-zero; release retention only when the manifest shows every complete capture before 10-15T21Z extracted or
   missing with a reason; reconcile release-only captures (`:245`) and the §4.3.1 restore step before release.
3. **Before q0061 (gate it).** The hash covers only constants and text (`cb3_declaration.py:228-249`). Add source hashes of every
   rule-applying function (cb3_*, `cb1_history.queue_fill/asof_quote/trade_condition_state`,
   `bounce_decomp.h_tight_mask/expanding_demean`, `small_g_pvalue`, `fee_spec/resolve_rate`) and the follow-up sampling
   constants (frac 0.5, LIMIT, MAX_PAGES). CB2 fix 1 again.
4. **Bypass flags.** `--spec` disables the commit check (`run_cb3.py:108`); `--now` skips the stage clock; `--n-boot`,
   `--placebo-draws`, `--random-filter-draws`, `--max-markets` override declared values (`test_cb3_quote_vacuum.py:377` runs a
   counted screen with an uncommitted spec, 0 bootstrap and 3 placebo draws; `--placebo-draws 0` removes the placebo gate,
   `cb3_quote_vacuum.py:530`). Remove them (CB2 fix 10 again).
5. **Look-ahead in B.** `panel_from_frames` keeps the latest non-empty `end_date`, `created_at`, fee fields
   (`cb3_quote_vacuum.py:99-103`), so eligibility and LF use future values (`cb3_maker.py:1244,1262`); §2.2 needs as-of values.
   Store them per capture.
6. **Rebate inflated.** "Conservative" = max(schedule, docs); unknown schedule gets `MAX_DOCS_RATE` (`cb3_maker.py:59-61`,
   `economics.py:121-131`); `fees_enabled` never passed, so fee-free markets get the maximum rebate. For income use the minimum,
   unknown = 0; add `fees_enabled` to `quote_state`.
7. **Failed requests hidden.** `build_prospective` ignores `not_reached`/`failed`/`http_*` (`cb3_maker.py:1254-1267`), so those
   quotes count as unfilled. Exclude not-reached markets (counted), failed/partial windows unavailable, counts by status in q0064.
8. **Pre-origin visibility.** RT and visibility use the post page-cap flag (`:376`, `:1267`); the trade sample's 500-print cap
   (`trade_sample.py:314`) and per-market fetch status are not carried. Add both to `pre/`.
9. **Pass alignment.** `P.cap_ids[j+1]` assumed to be pass j's follow-up (`cb3_maker.py:1220`; `cb3_quote_vacuum.py:686,695`):
   check `plan.previous_capture_id`. Without a wallet key wallets are blank (`cb3_followup.py:247-251`): record such passes as
   missing. Exhausted retries are recorded as http_429 (`:184`).
10. **Stage 2 B reads Stage P origins** (`[r0, r1+12h)`, `pass_range=None`, `run_cb3.py:203,219`; same for stagep `:248,261`).
    Restrict origins to `< r1` and `< p1`.
11. **Note 18.** The design names Gamma `chg_1d`; coded as all-NaN, the control column is silently dropped (`control_frame :458`).
    Load `chg_1d`. Use 1c depth (`s{k}_depth_*_1c` / pmxt) for the depth control and the B6 depth decile (`:929`, `:665`).
12. **B1 prospective placebo** shifts the fills' own `t_fill − 60` (`:1312`), not the market's large-order stream (discarded at
    `:1271`). Keep the real stream.
13. **Weighted sign check** applied only at Stage 1 for mechanism tests (`:1117`); §2.6(ii) applies it at every stage.
14. `stage2_expected` silently lowers k when an S1 file is missing (`cb3_common.py:293`): refuse. Census P `--before` not clamped
    to `T3_dev_end` (`run_cb3.py:138`). The `T3_dev_end` three-day extension is not coded.
15. **Fails open.** `T_J4R_end` read from the mutable q0035 spec (`cb3_declaration.py:25,320`). Pin it from J4-R's actual run.
16. **q0064** depends only on q0061; its "no passes" refusal exits 3 and burns retries (`run_cb3.py:134`). Gate it until 10-25
    plus ≥ 3 days of deployed follow-up.
17. `pin_rep_start` checks only the floor; verify the max rule and that the pin is committed.
18. Minor: `SweepMarks` lacks the [0.02, 0.98] mid band (`:280`); pmxt mark search unbounded (`:908`); a NaN SE passes the bias
    rule (`cb3_common.py:210`); history far-touch mark ignores `after` (`:262`); `dep` fallback share unreported in history.

**Not verified:** host data-dumps size and q0060 queue position; complete captures before 10-15T21Z on host vs the 0.30 GB cap;
release-only captures; Data API page order; real `quote_state` size; whether q0061/q0064 are deployed.

**Order:** 1-2 before q0060 (or hold it); 3 before q0061; 7-9 before deploying the follow-up; 4-6 and 10-17 before the freeze.

**Coordinator action (2026-10-16 ~05:45Z):** q0060 held behind gate q0060a, q0061 behind q0061a, q0064 behind q0064a (4a40d67,
deployed). RETENTION.md now opens the gate on manifest completeness, not job status.

### Freeze-check fix status (implementer, 2026-10-16)
Done and committed: 1, 2 (0dc00e4, with 8aea370 for the operational cap); 3, 4 (728395e); 5, 6 (0dc00e4: as-of end_date, created_at and fee fields per
capture, `fees_enabled` in `quote_state` schema v2; income rebate = minimum of schedule and docs rate, unknown = 0); 15 (e9c97d3, `seals/j4r_window.json`);
16 (4a40d67, gate q0064a). Coded in the commit that carries this section ("CB3 freeze-check fixes 7-14, 17, 18 and ruling conditions"):
- 7: not-reached, failed and partial windows are passed as truncated or unavailable (never as "unfilled"); `retries_exhausted` is its own status.
- 8: the trade sample's `features.csv.gz` (per-market fetch status, n_returned, 500-print cap) is copied to `pre/`.
- 9: a pass is used only if `plan.previous_capture_id` names the onset capture (misaligned counted); no wallet key = pass recorded `missing_no_wallet_key`.
- 10: Stage 2 and Stage P origins restricted to `< r1` and `< p1` (`origin_before`), `pass_range` removed.
- 11: Gamma `chg_1d` is loaded; the depth control and B6 depth decile use the 1c depth (`s1_depth_*_1c` / pmxt).
- 12: the B1 prospective placebo keeps the real large-order stream. 13: the weighted-sign check applies at every stage.
- 14: `stage2_expected` refuses a missing S1 file; census P `--before` is bounded by `dev_window_end` (T3_dev_end moved by whole days to give >= 3 days);
  census P refuses while the J4-R pin is not final.
- 17: `pin_rep_start` verifies the section 1.2 max rule and that the freeze commit holds the spec.
- 18: SweepMarks mid band [0.02, 0.98], pmxt mark search bounded to one 6h grid step, NaN or non-positive real SE is "inconclusive", history far touch
  respects `after`, `dep` fallback share reported.
- Ruling conditions: binding centred A2 placebo check (`A2_centred`); spec carries `frozen_cuts_sha256` and `census_sha256`, the runner checks the cuts against
  `frozen_cuts_proposal` and the census sha, `single_commit` refuses a spec with more than one commit, and every result and trial line records the cuts hash;
  the declaration hash now also covers `cb3_declaration` source. Bypass flags are removed (fix 4).
Needs a science-reviewer re-check before q0061a: fixes 3, 5-9, 11-12 and the centred A2 check (the declaration hash changed, so `24f33c36...` is superseded).

### Freeze-check re-check HOLD fixes (implementer, 2026-10-16)
Science-reviewer ruled HOLD on census q0061 until these; all coded in the commit named below.
- (a) `source_hashes` now also covers `cb3_quote_state`, a file sha256 of `backend/scripts/run_cb3.py` (stage windows, `origin_before`, Holm k, census clamps) and
  the helpers `cb1_history.load_sample` / `drop_outcome_columns` / `load_books` and `history_backfill.load_prices`.
- (b) `verify_cuts_against_census` refuses unless `census["declaration_sha256"] == spec["declaration_sha256"]`; the census output records the declaration hash,
  `git_head` and `git_dirty`.
- (c) Unit tests for the `A2_centred` gate in `gate_a`; `reading()` now checks the placebo covers-zero VOID before the NaN-SE "inconclusive" return.
- Fix 11 (partial): history depth falls back to touch size when `sw_depth_*_1c` is absent (kept); `depth_touch_fallback` is counted in `exclusions` and
  `depth_touch_fallback_share` is reported in the history census.
- No threshold, floor or formula changed. **Current declaration hash:** `eb6a143c5f78cab4aaa98dfa8387d14833b5e780b04118e0a025c8108cc76ffe`
  (`24f33c36...` and `db87350d...` are superseded). Any later edit to a hashed function or `run_cb3.py` changes it; recompute before the freeze.
