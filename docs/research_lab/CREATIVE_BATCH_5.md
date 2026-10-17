# Creative batch 5 (CB5): seed-anchor reversion, ladder-vs-bucket CDF consistency, hour-of-day moderation of the Kalshi lead

`evidence_role: exploratory_historical` (CH56 screen on `h2_main`; CH58 measurement on the audited cross-venue pairs) /
`exploratory_dev` (CH59 dev on live captures) / `prospective` (CH56 and CH59 replications; data after the freeze) |
status: **REVISED after challenger round 1; not frozen; awaiting freeze check of code.** Last updated 2026-10-17
00:10 UTC+1. The round-1 items and the changes they caused are listed in §9.

This file turns CH56, CH59 and CH58 from `CREATIVE_HYPOTHESES_2026-10-16.md` into declared, falsifiable tests. It
follows `CREATIVE_BATCH_1.md` (CB1), `CREATIVE_BATCH_2.md` (CB2) and `CREATIVE_BATCH_4.md` (CB4) in structure and rules:
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim. AREPO never
  trades. Every P&L is a paper rule at modelled or recorded prices.
- CB5 has **two kinds of work, counted separately** (§2.5):
  - **Routes** (CH56 `G`, CH59 `L`): money-route hypotheses. Each has a screen, a frozen replication on data collected
    after the freeze, and an economic check. The primary quantity of an economic test is net P&L per filled share (or
    per pair) at modelled or recorded executable prices after fees, with `R_ann` and capacity beside it.
  - **Measurement** (CH58 `K`): a conditioning fact for any Kalshi-anchored design. It has no money route and is never
    read as edge.
- Test tables bind only once the CB5 declaration hash is committed (`model_specs/cb5_v1.json`, the CB5 freeze).
- Queue specs (§5) are drafts. None is committed to `queue/jobs/` by this document.
- **Where CB5 says "as CB1 §x", "as CB2 §x" or "as CB4 §x"**, that rule applies unchanged, including its
  challenger-round and freeze-check fixes.
- **Queue numbering (revised in challenger round 1, §9 item 4).** CB4's drafts q0084-q0093 keep their numbers (CB4
  was declared first). q0100 is taken (`q0100_j8_tte_diag`). **CB5 uses q0101-q0114, one id per job, no letter
  suffixes** (mapping in §0.1). No CB5 id shares a numeric prefix with any CB1-CB4 or other committed spec.
- **No overlap with CB1-CB4 hypotheses.** CB1-E (CH22, genesis NO carry) uses the same `h2_main` listing windows as
  CB5-G but a different feature, the question text, and no seed. The data overlap is disclosed in §1.3. CB2-L
  (CH12/CH13) covers within-ladder and cross-event date ladders. CB5-L covers only the cumulative-vs-exclusive identity,
  which CB2's grouper excludes by construction ("in <month>" is excluded there). CB4 has no cross-venue or listing test.

## 0. Summary, selection and ranking

| Rank | Job | Hypothesis | Tests (counted) | Screen / dev data | Replication data | Own queue ids (§0.1) | CPU-h | Peak RAM |
|---|---|---|---|---|---|---|---|---|
| 1 | **CB5-F** data | `cb5_extract/listings` (backfill + pass step), `h2_main/cb5/head_prices`, seed-census cohort fetch, CDF family frame (IF-H2 metadata + fresh walk), `cb5_extract/cdf` (backfill + pass step) | none | n/a | n/a | q0101, q0102, q0103, q0104, q0105 | 3-4 + 2-3 h network wall | 1.5 GB |
| 2 | **CB5-G** seed-anchor reversion (CH56) | after the first trades move the price away from the pre-trade seeded quote, it reverts toward the seed over days 1-3 (G1). A maker order on the seed side at +24h, exited at +72h, pays after costs (G2) | G1 (mechanism), G2 (economic) | `h2_main` (worn, L1 ceiling) + head refetch | **prospective** listing cohort in `[T5_rep_start, T5_rep_start + 21 d)` | q0108, q0111, q0112 | 1.0 | 1.2 GB |
| 3 | **CB5-L** ladder-vs-bucket CDF consistency (CH59) | `P(by D) = Σ P(bucket ≤ D)` is violated at the touch by more than fees, and the violation is still present at the touch 2h later (L1; touch sizes are not recorded, so "executable" is checked only on the depth subset) | L1 (economic) | live captures `[T5_dev_start, T5_dev_end)` via `cb5_extract/cdf` | live captures `[T5_rep_start, T5_L_rep_end)` | q0107, q0109, q0113 | 0.5 | 1.5 GB |
| 4 | **CB5-K** hour-of-day moderation of the Kalshi lead (CH58), measurement | the 10-20 min Kalshi→Polymarket lead is larger in US overnight hours than in US day/evening hours (K1) | K1 (measurement) | cross-venue C1 set (316 pairs, worn) | optional K1-R on E009/E010 live data **after** their own analyses (≥ 2026-11-03), declared now, needs owner sign-off | q0110, q0114 | 0.3 | 1.0 GB |

The pre-freeze census q0106 is shared by G, L and K.

**Why this order.**
- The `listings` extractor table must start first. CB5-G's pre-freeze seed-semantics check (§2.7, item G-v) needs the
  first-seen touch of new listings in captures from 2026-10-11T12:00Z. Raw snapshots become deletable at 8 days from
  about 2026-10-18 (`data_catalogue/RETENTION.md`). Captures already deleted are streamed from verified release copies
  one at a time (CB4 §2.10 machinery). CB5 places no new gate on retention.
- The CDF family frame (q0104) must exist before the CDF extract can be filtered (captures carry no question text,
  §1.1). It reads metadata only, and its grouper is hashed before any text is read.
- CB5-K needs no new data. It is the cheapest job but has the weakest power (§CB5-K). It runs after the freeze, behind
  the routes' data jobs.

### 0.1 Queue id mapping (one id per job; revised in challenger round 1)

| Id | Job | Family | CB5 first-draft id (retired, never to be used) |
|---|---|---|---|
| q0101 | `cb5_listings_backfill` (extractor `listings`) | F | q0090 |
| q0102 | `cb5_h2_head_fetch` | F (for G) | q0091 |
| q0103 | `cb5_seed_cohort_fetch` (census cohort) | F (for G) | q0091a |
| q0104 | `cb5_cdf_frame` (grouper, text-only audit print) | F (for L) | q0092 |
| q0105 | `cb5_cdf_extract_backfill` (extractor `cdf`) | F (for L) | q0092a |
| q0106 | `cb5_census` (G, L, K counts and gates) | shared | q0093 |
| q0107 | `cb5_rinc` (guarded historical outcome read) | L | q0093a |
| q0108 | `cb5_screen_G` (Stage 1 on h2) | G | q0094 |
| q0109 | `cb5_screen_L_dev` (Stage 1, held until CB1-D's replication read) | L | q0095 |
| q0110 | `cb5_measure_K` | K | q0096 |
| q0111 | `cb5_rep_G_fetch` (rolling) | G | q0097 |
| q0112 | `cb5_rep_G` (Stage 2) | G | q0097a |
| q0113 | `cb5_rep_L` (Stage 2) | L | q0098 |
| q0114 | `cb5_K_rep_live` (optional K1-R) | K | q0099 |

### 0.2 Selection and scope

No census was run for this draft. **No CB5 quantity has been computed, and the drafting session read no price, book,
trade, outcome or question text.** It ran read-only file-existence and size checks on the host (2026-10-16 ~18:10Z)
and listed file *names* in the archive release manifest `data-20261013-research-lab/files.sha256`. It read the CSV
header lines of one capture (`rows.csv.gz`, `rows_ext.csv.gz`) to learn the column names. Every other count below
comes from committed documents.

| Idea | Decision | Reason |
|---|---|---|
| **CH56** seed anchor | **include (G)** | `h2_main` holds raw 10-minute prices and hashed trades for 3,200 sampled markets (host: 3,200 price and 3,200 trade files). The ML panel excluded day 0, but the points exist where the fetch window reached the listing. The named "fake" is real and documented: `HISTORICAL_ML_DEV.md` found `price_unchanged_since_listing` "rarely true ... mostly because the series begins at the first trade", and untraded rows sit near 0.5 (53% within 0.02 of 0.5). So the seed definition and a pre-freeze seed-semantics gate are central (§CB5-G, §2.7). The replication is **prospective**: `h3_power` is retired from replication (Ledger M3), `h5_cb1` is CB1's sealed replication set, `h6_weather` is CB2-W's, and both `h7` runs are CB4's. A new historical backfill would have to finish before `T_seal` = 2026-10-22 behind the h5/h6/h7 jobs (CB4 §1.3), so it is not proposed |
| **CH59** ladder vs bucket | **include (L)** | IF-H2 walked 303,136 events (metadata including `negRisk`, `groupItemTitle`, `question`, `endDate`). Its grouper excluded neg-risk "which month" events by design, and CB2's excludes "in <month>". So no AREPO grouper has paired the two representations. IF-H2's `events.jsonl.gz` survives only in the release `data-20261013-research-lab` (the host has no `if_h2/`). It **stores `outcomePrices`**, so the parser drops outcome fields by guard (§CB5-L). Executable gaps need touches, which exist only in live captures, so the test is live (dev, then prospective replication), as CB2-L |
| **CH58** hour moderation | **include (K), measurement, small** | The 493 pair series (`cross_venue/series/*.npz`, 357 MB on the host) carry Polymarket points (`ps`) and Kalshi candles with bid, ask and volume (`kc`), so hour, Kalshi spread and Kalshi activity are derivable. No fetch is needed. The sealed E009/E010 poller (`cross_venue_live/`) is refused by the runner before 2026-11-03 (§1.3) |
| CH55, CH57 | not in CB5 | CH55 needs a new trade poller. CH57 must wait for the `h6_weather` seal and must not touch CB2-W's holdout |

**Sports and weather.** The category scope is the user's decision (`CB5_SPORTS_IN_PRIMARY = false`). Sports is a
reported, uncounted stratum in G, L and K. For K this also removes the in-play confound: games cluster in US evenings,
inside the "retail" bucket. Weather (`fee_category == "weather"` or CB2's `TEMP_RE`) is excluded from every CB5
population, as in CB4 §1.3, so CB5 never touches CB2-W's live stage P.

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Prior use | Role in CB5 | Evidence ceiling |
|---|---|---|---|
| `history/h2_main` (3,200 sampled markets; raw 10-min prices, hashed trades newest-first ≤ 10,000, frame with `created_at`, `start_at`, `end_at`, `closed_time`, `fee_category`) | r0-r5 ML, HB1, HB2 (SB2 J1/J3/J7), surprise detector, CB1-A/C/E screens (q0019 census done; q0020 not yet committed) | **CB5-G Stage 1 (screen).** Worn far beyond its budget: every CB5 result on it is labelled "beyond budget", **L1 at most** | L1 |
| `history/h2_main/cb5/head_prices/` (**new**, q0102) | none | Price points in `[created_at − 1h, created_at + 4d + 1h]` for every eligible h2 market, refetched so that listing coverage does not depend on how late a market closed (CB1 freeze-check fix 1: h2 coverage misses `[created, end + 1d]` for 367 of 414 active and 755 of 2,786 closed units) | as h2 |
| `cb5_extract/listings/` (**new**, extractor table, §4.3) | none | First sighting of each new market in the complete captures: ids, `created_at`, `start_date`, `end_date`, `fee_category`, touch, sizes, `last_trade_price`, `volume_num`. **Census cohort** (listings `< T5_dev_end`): seed-semantics check only. **Replication cohort** (listings in the G replication window) | none (census) / L2-dev (rep) |
| Post-hoc CLOB `prices-history` and Data API trades for listing cohorts (**new**, q0103, q0111) | none | Census cohort: points and trades only up to `first trade + 1h` (a parse guard drops later rows). Replication cohort: `[L − 1h, L + 4d + 1h]` | as above |
| IF-H2 `events.jsonl.gz` (303,136 events, release `data-20261013-research-lab`, restored to a scratch directory on the host) | IF-H2 r0 grouper; CB1/CB2 exclusion lists | **CB5-L frame only.** Metadata read with `outcomePrices`/`outcomes` dropped at parse. One separate, guarded outcome read for the historical inconsistent-resolution rate (q0107, after the grouper audit) | none (frame) |
| Fresh Gamma `/events` walk, start dates 2026-10-01 to the q0104 run (**new**) | none | CB5-L frame for events listed after IF-H2's walk. Same guard | none |
| `cb5_extract/cdf/` (**new**, extractor table, list-filtered) | none | CB5-L dev (captures `< T5_dev_end`) and replication (`[T5_rep_start, T5_L_rep_end)`) touches of every leg of every frozen family | L1 (dev) / L2-dev (rep) |
| Raw complete captures, sidecar, book sweeps (host; release copies) | E-series, SB2, CB1-CB4 | read only by the extractor (`listings`, `cdf`) and by the K census's J4 wide-state-by-hour count (captures `< 2026-10-20T03:00Z`, spread and mid only) | - |
| `cross_venue/series/*.npz` + `matches.json` (C1 set: 316 pairs, 183 events, 517,616 usable steps; 149 sports pairs) | cross-venue v1 and r1 (20-test BY family, twice), E009 design | **CB5-K measurement.** Worn: the lead itself was found here. L1 ceiling, labelled "unreplicated measurement" | measurement |
| `cross_venue_live/` (E009/E010 2-min poller) | E009, E010 (sealed until 2026-11-03) | **Not read** before 2026-11-03 or before both E009 and E010 final analyses are committed. Optional K1-R afterwards, only with the owner's sign-off (§CB5-K) | - |
| `h3_power` | many; retired from replication (Ledger M3) | **not read** (runner refuses) | - |
| `h5_cb1`, `h5_cb1_ladders`, `h6_weather`, `h7_cb4_era`, `h7_cb4_series`, `h4_seal` | reserved by CB1, CB2-W, CB4, SB2 | **not read** (runner refuses the run ids). Only committed seal copies under `docs/research_lab/seals/` may be read, for market-id exclusion | - |
| `cb1_extract/`, `cb2_extract/`, `cb3_extract/`, `cb4_extract/` | CB1-CB4 analysis inputs | **not read by any CB5 code path** (as CB4 §1.1). CB5 extracts its own tables | - |

### 1.2 Dates (declared; UTC)

| Name | Value | Meaning |
|---|---|---|
| `T5_draft` | 2026-10-16T18:40Z | First draft. No CB5 quantity has been computed |
| `T5_dev_start` | 2026-10-11T12:00Z | First sidecar capture (as CB1, CB2, CB4). Start of the L dev captures and of the G census cohort |
| `T5_dev_end` | **2026-10-27T00:00Z** | L dev: captures with `capture_start_utc < T5_dev_end` (about 15.5 days, about 186 captures). G census cohort: listings with `created_at < T5_dev_end − 1d` |
| `T5_rep_start` | **max(2026-10-29T00:00Z, first complete capture ≥ CB5 freeze commit + 2h)**, pinned in a committed file (CB1 freeze-fix 9) | Start of the G replication cohort (by `created_at`) and of the L replication captures |
| `T5_G_rep_end` | `T5_rep_start` + 21 d | End of the G replication listing window |
| `T5_G_read` | `T5_G_rep_end` + 4 d + 2 h | G replication read: every cohort market's day-3 window is complete |
| `T5_L_rep_end` | `T5_rep_start` + 28 d | End of the L replication captures |
| `T5_L_out` | `T5_L_rep_end` + 30 d | Realised-payoff read for L triggers |
| `T_h2_clock` | 2026-10-11T23:00:33Z | `h2_main` request clock. The h2 head refetch requires `created_at + 4d + 1h ≤ T_h2_clock`, so it adds no information after the h2 sample was drawn |
| `T_seal` | 2026-10-22T00:00Z | SB2's h4 seal boundary. CB5 has **no historical fetch whose rows reach `T_seal`**. The head refetch ends before `T_h2_clock`, and the IF-H2 and fresh-walk frame is metadata (the r_inc outcome read uses events closed before `T5_dev_start`, §CB5-L) |
| `T_E9_unseal` | 2026-11-03 | Earliest date for the optional K1-R, and only after both E009 and E010 final analyses are committed |
| `T_CB1D_rep` | 2026-11-09T00:00Z (CB1 `T_rep_end`) | End of CB1-D's sealed replication window. CB5-L dev output (q0109) is held until CB1-D's replication results are committed or CB1-D is recorded as stopped, and never before this date (§CB5-L, round-1 item 11) |
| `T_J4R` | 2026-10-20T03:00Z | J4-R's first fresh capture (`not_before` of q0035). The K census's wide-state count uses only captures before it |

### 1.3 Sealed and untouched data (named)

- **Refused run ids and roots.** `run_cb5.py` refuses `h3_power`, `h4_seal`, `h5_cb1`, `h5_cb1_ladders`, `h6_weather`,
  `h7_cb4_era`, `h7_cb4_series`, any path under `cb1_extract/` to `cb4_extract/`, and `cross_venue_live/` (the latter
  until a committed K1-R spec exists, §CB5-K).
- **h2 wear and the CB1-E overlap (disclosed).** CB1-E screens on the same h2 listing windows: origin `created + 24h`
  (CB5's `t1`), target 7-day YES drift (it overlaps CB5's 72h window), NO bought at the ask. Its screen (q0020) is not
  yet committed. If its results are known at the CB5 freeze, the freeze commit records it. CB1-E's unconditional
  drift says nothing about the seed-conditional slope G1, but both read the same day 1-7 paths. That is one more reason
  why CB5-G's h2 result is L1 at most and **only the prospective replication can carry it forward**.
- **h4_seal unchanged.** The h2 head refetch ends before `T_h2_clock`. The G and L replication data lie after
  `T_seal` in calendar time (as CB4-C, disclosed). They are CB5's own listing and CDF extracts plus post-hoc API fetches
  of CB5-selected markets, never h4 data. No frozen SB2 parameter changes.
- **SEALED-P overlaps (disclosed, as CB4 §1.3).** The L dev and replication windows overlap CB1-D's, CB2-L's and
  CB4-C's live windows. CB5 never opens their extract tables. Its hypothesis (the cumulative-vs-exclusive identity
  across two events) differs from CB1-D's (neg-risk sums within one event) and CB2-L's (monotone rungs). A bucket event
  of a CB5 family is also a CB1-D neg-risk event. CB1-D is frozen, so CB5 results cannot change its tests.
- **Census cohort vs replication cohort (G).** Listings created before `T5_dev_end − 1d` form the census cohort. They are
  read only up to their first trade + 1h, for the seed-semantics check (§2.7). **They are never used for G1/G2 and
  never read past that window.** The replication cohort starts at `T5_rep_start`. The two cannot share a market.
- **CB5-K.** The C1 pairs were analysed twice (v1 and r1), and E009 froze coefficients from v1. K1 is a new statistic
  on worn data and cannot change E009/E010. The runner refuses `cross_venue_live/`.
- **Results outside data directories.** Every CB5 result goes to `research_lab/creative_batch5/`. Nothing is written
  inside `history/h2_main/` except the new `cb5/head_prices/` subdirectory (as CB1 wrote `h2_main/cb1/`).

## 2. Common rules (deltas from CB1 §2, CB2 §2 and CB4 §2)

### 2.1 Costs

As CB1 §2.1 and CB4 §2.1, read through the shared cost model **`cost_regimes.cost_regime(date, fee_category, price)`**
(`backend/astrolabe/research_lab/cost_regimes.py`, version `cost-regimes-v1`):
- `fee_rate` per taker leg as `r·a·(1 − a)`, never below the CB1 conservative rate (R0);
- `half_spread` from the CB1 band table, never lower;
- `a_as_cents`, the R2 maker adverse-selection term, applied to maker fills before the category's rollout date;
- `post_rollout` and `era_rule`, the R1 inputs.

If the register (`model_specs/cost_regimes_v1.json`, CB4 q0089) is absent, the module returns the CB1 defaults flagged
`absent_defaults`. CB5-G's screen **refuses to run until the register is committed** (as CB4-S), because most h2
listings predate the fee rollout. Maker fee 0; rebates only as an optimistic secondary.

| Item | Rule |
|---|---|
| Genesis half-spread | `h_gen(p) = max(half_spread(p), 0.025)` (CB1-E's 2.5c genesis floor) |
| G2 maker order (paper) | placed at `t1` on the seed side at `q = min(p(t1) + h_gen + 0.01, 0.99)` (ask) or `max(p(t1) − h_gen − 0.01, 0.01)` (bid). **Filled at q only on a trade-through** in `(t1, t1 + 24h]`: an ask-side print strictly above q (ask) or a bid-side print strictly below q (bid). Exit at `t3` as a taker: buy back at `a_x = min(p(t3) + h_gen(p(t3)), 0.999)` or sell at `b_x = max(p(t3) − h_gen(p(t3)), 0.001)`. `net_ask = q − a_x − f(a_x) − a_AS`, capital `1 − q`; `net_bid = b_x − q − f(b_x) − a_AS`, capital `q`. **Binding +0.75c** on the exit price. Hold-to-resolution `q − Y0` / `Y0 − q` reported, not tested |
| L legs (taker, tier 0) | every leg at the recorded touch; fee per leg `r_j·a_j·(1 − a_j)` with `r_j = cost_regime(capture date, fee_category_j).fee_rate`. Tier sensitivity `(1 − ρ)·F`, `ρ ∈ {0.25, 0.50}`, reported only (CB4 R3). Maker legs: reported as an optimistic variant only (no fill model at 2h cadence) |
| K | no P&L |

### 2.2 Clocks

As CB1 §2.2, CB2 §2.2 and CB4 §2.2. In particular:
- A history price point stamped `s` is usable at `t` iff `s + 600 ≤ t` and it is at most 2h old (CB1). This also
  protects the seed definition: a point whose bucket contains the first trade cannot be usable before that trade,
  whichever bucket-stamp convention applies.
- Trades use venue `ts`. A condition at `t` uses trades with `ts < t`. Truncation rule as CB1 §2.2: a trade condition is
  known true, unavailable or false. Unavailable units are excluded and counted, and at the screen they are reported by
  outcome.
- `L` (listing) = Gamma `created_at`. `start_at` is reported, never used as an anchor. `closed_time` is never a
  population condition or a window anchor (CB1 §2.2).
- Snapshot pairs for L execution: consecutive complete captures with a start gap in [1.5, 3] h (CB1-D/CB2-L rule).
- **Coverage invariance.** Every fetch window is anchored on `created_at` (G) or on capture times (L), never on how
  late a market closed. A unit-level test asserts this.

### 2.3 Uncertainty and decision rule

- Unweighted estimates are primary. One-sided p (routes) or two-sided p (measurement) = the max over the declared
  cluster ways of CR1 (normal z). CI by a 2,000-draw cluster bootstrap (seed 516).
- **Small-G rule** as CB2 §2.3: G ≥ 30 uses CR1 normal; 15 ≤ G < 30 uses CR2 with t(G − 1) and a Webb wild-cluster
  bootstrap (9,999 draws), taking the larger p; G < 15 in any way is "not testable", p = 1, still counted.
- Testability otherwise: ≥ 100 units and ≥ 30 clusters in each declared way, else "not testable" (p = 1, counted).
- **Routes (G1, G2, L1).**
  - **Stage 1** (G on h2; L on dev captures): advance iff one-sided p < 0.01 in the declared direction, the §2.4 floor
    is met, `R_ann` ≥ 10% for economic tests, the placebo is calibrated (§2.6), the binding robustness holds, and the
    test's attribution rule holds. A BY label (q = 0.10, `battery2.cumulative_count()`) is attached as triage only.
  - **G2 carry rule (declared now).** h2 will probably give fewer than 100 G2 fills (§CB5-G MDE). If G1 advances and G2
    is "not testable" on h2 *for size only* (fills < 100 or fill clusters < 30) with a point estimate ≥ 0, G2 enters
    Stage 2 as "carried, untested at Stage 1". It is counted in the Stage-2 Holm k like any advanced test. A G2 that
    was testable and failed is not carried.
  - **Stage 2** (G replication cohort; L replication captures; all collected after the freeze): Holm at α = 0.05
    one-sided over **all CB5 route tests reaching Stage 2** (G1, G2, L1; k ≤ 3). Early finishers are reported against
    Bonferroni α/k with k fixed when Stage 1 ends; the batch Holm can only add passes. A pass is
    "development-replicated (L2-dev)". It is **not** confirmation (see §2.10).
- **Measurement (K1).** Family **K** = {K1}, single stage, two-sided α = 0.05 (k = 1). Reported as "unreplicated
  measurement" and never as edge. The optional K1-R (§CB5-K) is a separate one-test family.

### 2.4 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate |
|---|---|---|
| G1 | mechanism | slope `β ≤ −0.20` (at least 20% of the day-1 deviation from the seed reverts by day 3) |
| G2 | economic | net ≥ +1.0c per filled share and `R_ann` ≥ 10% |
| L1 | economic | mean executed net ≥ +0.5c per pair (CH59's materiality) and `R_ann` ≥ 10% |
| K1 | measurement | `|K1| ≥ 0.10` (asymmetry units, A10 + A20) |

### 2.5 Counting (M3 rule)

- Every counted test writes one `trials.jsonl` line via `provenance.append_trial`.
  - Routes: kinds `cb5_test` (Stage 1) and `cb5_replication` (Stage 2), with count lines `creative_batch_5:G` and
    `creative_batch_5:L` (`ml_explain` kind, `n_tests`).
  - Measurement: kind `cb5_measurement`, count line `creative_batch_5:K`. It is counted in the cumulative M3 total but
    has its own family and never enters the route Holm.
  - `cb5_descriptive` (EXCLUDE, no inference): seed census, the 0.50-seed stratum estimate, the incidence and
    persistence curves, the r_inc census, the sports strata, the J4 wide-state-by-hour counts, the K activity controls,
    gates and every reported variant.
- New `battery2.KIND_RULES` entries: `cb5_test`, `cb5_replication`, `cb5_measurement` EXCLUDE ("counted by the
  matching `creative_batch_5:*` count line"); `cb5_descriptive` EXCLUDE. Unknown kinds still raise. A unit test runs
  the counter on the real `trials.jsonl`.
- Placebo lines: `evidence_role: "placebo"`, count 0.
- **Cumulative count at drafting.** `battery2.cumulative_count()` on the working-tree `trials.jsonl`
  (rule `battery2-count-v1`) returned 1,080 in the first draft (2026-10-16 ~18:20Z) and **1,104** when recomputed for
  the round-1 response (2026-10-16 ~23:05Z). That includes 325 automatic `flow_screen` lines (their counting is an open
  governance question, Ledger M3). No CB1-CB4 test kind has a counted line yet. The value at run time,
  which will include whatever CB1-CB4 have logged, is recorded in every CB5 results file. **CB5 adds 4 fixed tests
  (G1, G2, L1, K1) and up to 4 conditional ones (G1, G2 and L1 at Stage 2; K1-R).** At a denominator near 1,100, BY at
  q = 0.10 needs z ≈ 4.1. That is why the two-stage rule (Stage-1 gate, Stage-2 Holm), not BY, is the decision rule
  (Ledger M3).
- Tests behind a failed gate (G56, the seed-semantics gate, the side audit, G59, the grouper audit, an unknown `r_inc`,
  an untestable L1 coherence placebo, a failed K pseudo-split calibration) are "not testable" or "not advanced"
  (p = 1) and still counted.

### 2.6 Placebos and robustness

- **Level-controlled slope (defined here, used below).** `β^LC` = the G1 slope of `y` on `d` with `VWAP₁` and
  `|VWAP₁ − 0.5|` as covariates. Because `d = VWAP₁ − σ`, `β^LC` is identified only from variation in the seed at a
  given first-day level, so generic reversion toward 0.5 or toward the cross-section cannot produce it.
- **G1 seed-permutation placebo (calibration; run on `β^LC`, revised in round 1).** Each informative-seed market's
  seed is replaced by the seed of another informative-seed market drawn without replacement within the same
  `fee_category` × listing ISO week. `β^LC` is recomputed with the full Stage-1 gate, 200 draws (seed 5161). The advance
  rate must be ≤ 1.5%. Under the level covariates a permuted seed carries no own-market information, so the placebo
  stays calibrated when level reversion exists; a raw-slope placebo would "advance" whenever `y` depends on `VWAP₁`
  and so would reject true anchoring (round-1 item 5). **The raw-slope placebo (same draws) is reported alongside**,
  never binding. If the `β^LC` placebo advances, the effect is not anchoring to the market's own seed.
- **G1 0.50-seed stratum (CH56's placebo; attribution, binding; revised in round 1).** Markets whose seed is exactly
  0.50 (`|σ − 0.5| < 0.0005`, the template or placeholder value) carry no market-specific anchor. Within this stratum
  `d = VWAP₁ − 0.50` is collinear with the level covariates, so `β^LC` is not identified there. The stratum is
  therefore used to **measure level reversion where no anchor exists**: fit `y = a + γ·VWAP₁ + δ·|VWAP₁ − 0.5|` on the
  0.50 stratum, form the residual `ỹ = y − ŷ_0.5(VWAP₁)` on the informative-seed units, and take the slope `β^{|0.5}` of
  `ỹ` on `d` (same clustering). The fitted level function is applied only inside the 0.50 stratum's 5th-95th
  percentile range of `VWAP₁`; informative units outside it are excluded from `β^{|0.5}` and counted (no
  extrapolation). CH56 is **credited** only if (a) the 0.50 stratum has ≥ 50 units and (b) `β^{|0.5}` has
  the declared sign and at least half the magnitude of the raw informative slope, `β^{|0.5} ≤ β_inf / 2` (level
  reversion measured on template seeds explains at most half the slope). If (b) fails, the verdict is "generic
  first-day reversal, not seed anchoring". If (a) fails, attribution is "unverified" and CH56 cannot be credited at
  that stage. The draft's raw comparison (`β₀.₅` against `β_inf / 2`) is reported, not binding.
- **G2 break-even placebo** (as CB1): fill prices kept, the exit replaced so that expected net is 0 (`p(t3)` drawn from
  the as-of `p(t1)` path permuted within market), 200 draws, advance rate ≤ 1.5%.
- **L1 coherence placebo (mismatched families; binding; replaces the draft's direction placebo, round-1 item 1).** The
  draft's coin-flip direction placebo could never fail, because `net_A + net_B = −(spreads + fees) < 0` at every
  capture. The replacement asks whether the grouper's matched pairs price the identity at all. For every (f, D) and
  dev pair-capture, `gap_mid = mid(L_D) − Σ_{b∈B_D} mid(b)`; the statistic `M` = the median over (f, D) of the median
  over captures of `|gap_mid|`. A placebo draw keeps every rung `L_D` and replaces its bucket event by a randomly drawn
  **non-matched** audited bucket event of the same granularity (month, quarter or year) with a period boundary on the
  same New York calendar day D, taking its buckets ending ≤ D; the same eligibility, leg-timing and capture rules apply.
  200 draws (seed 5162). **L1 may advance only if at most 1.5% of draws have `M_placebo ≤ M_matched`.** (f, D) pairs with
  no eligible mismatch are excluded from both sides and counted; fewer than 20 families with an eligible mismatch →
  "placebo not testable" and L1 cannot advance. This can fail: if the matched pairs are no more coherent than unrelated
  pairs, the grouper is pairing different questions and any touch "gap" is a directional bet. The L1 statistic
  recomputed on the mismatched draws (same trigger and execution rules) is reported as a descriptive contrast; it is
  expected to be large, which is why a positive `net'` alone is never read as a riskless gap. A lag placebo (trigger at
  c − 1, execute at c) was considered and not adopted: it has the same trigger-to-execution alignment as the primary
  and would reproduce it, so it cannot calibrate (§9).
- **K1 pseudo-split calibration (binding; replaces the draft's hour-shift placebo, round-1 item 3).** Within one real
  bucket, the 10-minute steps are split into two pseudo-buckets with the real O : R size ratio by random assignment
  of (pair, New York calendar date, half-hour slot) blocks (a step belongs to the block of its grid time t; blocks keep
  the short-range dependence of the 10-20 minute lags). K1 is recomputed with the full two-sided test on 200 splits
  within R and 200 within O (seed 5164). **The pooled two-sided rejection rate at p < 0.05 over the 400 splits must be
  ≤ 6.5%**; each bucket's rate is reported. (The draft's "200 circular shifts within day" is impossible on a 144-step
  daily grid, and near-zero shifts reproduce the real split, so it measured power rather than size.) The single
  **+12h hour-label shift** (R ↔ O swap) is kept as a reported contrast. The study's own reverse-direction asymmetry
  `r(ΔP_t, ΔK_{t+L})` by bucket is reported.
- **Binding robustness for any advance or pass:**
  - (i) routes: +0.75c on every bought or exit leg keeps net > 0 (G2: on `a_x`/`b_x`; L1: spread across legs as
    +0.75c total per pair);
  - (ii) the test still meets its p threshold and floor without the top 5 clusters by absolute contribution, in each
    declared way;
  - (iii) the unweighted and cluster-equal-weighted estimates agree in sign;
  - (iv) G1: the ask-side, bid-side and history-price targets agree in sign, and **the level-controlled slope**
    `β^LC` has the same sign and at least half the magnitude;
  - (v) G1, G2: the truncation worst case keeps the estimate on the declared side;
  - (vi) the era rule (§CB5-G) when the register says `post_rollout_or_interaction`;
  - (vii) L1: the divergence gate, the realised-payoff gate and the depth check (§CB5-L). **An "unknown" or
    "inconclusive" outcome of any of them blocks crediting** (round-1 item 2): unknown `r_inc` blocks a Stage-1
    advance; an inconclusive payoff or depth check leaves a Stage-2 pass "pending, not credited";
  - (viii) K1: the activity-matched contrast and the within-pair contrast each have the same sign and ≥ half the
    magnitude (§CB5-K);
  - (ix) G1 at Stage 1 (h2 only): the stratum-adjusted slope (h2 draw strata as fixed effects, §CB5-G) has the same sign
    (round-1 item 6).
- Reported, not binding: sign by month and by fee category, +1c cost, the sports strata, `ρ` tier sensitivity (L),
  maker-leg variant (L), hold-to-resolution (G2), `pm_lag = 0` alignment (K).

### 2.7 Pre-freeze census (q0106, q0107; counts only)

An outcome guard drops outcome columns before population code runs (CB1 §2.9). No target, coefficient, net, mark-out
or lead statistic is computed.

**G (on h2 and the census cohort; reads only price points and trades in `[L − 1h, min(first trade + 1h, L + 24h)]`,
with two declared, guarded exceptions on h2 only, round-1 item 8):** G-vi reads token, side and price of h2 trades and
the as-of history price in `[L, L + 24h)` (the feature window, never a target window); G-vii calls a **count-only
accessor** `window_count(trades, a, b)` on the entry and exit windows, which returns the number of prints and never a
price, size or side. The census cohort (q0103) is stored only up to `min(first trade + 1h, L + 24h)` and has no
exception. A unit test asserts that no census code path receives a target-window price.
- G-i: eligible h2 markets (population rules of §CB5-G except the seed rule); those with untruncated trades back to
  `L`; with head-refetch coverage; **with a valid seed** (≥ 1 usable pre-trade point); share.
- G-ii: among valid seeds, the share with `σ` equal to the first trade's token-0 price (`|Δ| < 0.0005`), and the
  distribution of `t_ft − s_first` (minutes from the first point to the first trade). **If more than 50% of valid
  seeds equal the first trade price**, the series is judged to start at the first trade ("seed is a first-trade echo"):
  CB5-G stops before the freeze and is recorded.
- G-iii: the share of valid seeds with `σ` exactly 0.50; the informative-seed and 0.50-seed counts by category.
- G-iv: determinism. On points stamped in the overlap of the stored h2 series and the head refetch, the share that are
  identical (`|Δ| < 0.0005`). Below 95%: disclosed; the head refetch is primary.
- **G-v (seed-semantics gate, the CH56 "fake" check).** In the census cohort (listings in
  `[T5_dev_start, T5_dev_end − 1d)`, non-sports, non-weather), take markets whose first sighting in `listings/`
  precedes their first trade and shows a two-sided touch with spread ≤ 0.10 ("checkable"). Among them, measure the
  share whose seed `σ` lies within 0.01 of that touch mid. **Gate: ≥ 50 checkable markets and agreement ≥ 75%.**
  - Below 75%: pre-trade `prices-history` points are not the seeded book quote. CB5-G stops before the freeze ("seed
    semantics unverified") and is recorded.
  - Fewer than 50 checkable: the gate is "unverified". The screen may run, but every Stage-1 result carries that label.
    The check is repeated on the replication cohort before any Stage-2 target is read, with the same thresholds.
  - **Era limit (round-1 item 9).** G-v can only check Oct 2026 listings. h2 listings come from a 270-day lookback,
    and the API's pre-trade point semantics may have changed over that period. Every h2 Stage-1 result therefore carries
    "seed semantics unverified for era" (in addition to "beyond budget", L1) whatever G-v shows. G1 is reported by listing
    quarter, not counted. Only the replication cohort, checked by the repeated G-v, has verified semantics.
- G-vi: **side audit** (as CB4-S, h2 day-0 trades). Per token, the share of `BUY` prints at or above the as-of history
  price, and the share of `SELL` prints at or below it, must each be ≥ 75%. Otherwise CB5-G stops before the freeze
  ("side convention unverified").
- G-vii: **gate G56.** At least 100 informative-seed units with both the entry and exit print windows non-empty (an
  availability count, not a value), ≥ 30 events and ≥ 30 listing dates. Also reported: units with `|d| ≥ 3c` (the G2
  population size, no sign), the 0.50-stratum count, and truncation counts. Fail → G1 and G2 "not testable" on h2
  (counted). G1 can then still be registered prospectively only by a new declaration.
- G-viii: listings per day in the census cohort meeting the replication population rules, used to state the Stage-2
  MDE.

**L (frame, dev extract, historical metadata):**
- L-i: families matched by the frozen grouper (§CB5-L), by fee category, bucket granularity (month/quarter/year), and
  `K_D` (buckets up to D). Separately: historical (both events closed before `T5_dev_start`) and live (at least one
  eligible pair-capture in `[T5_dev_start, T5_dev_end)`).
- L-ii: **grouper audit gate** (text only, before any price is read): a seeded random 50 live and 50 historical
  families are printed with event titles, member questions, `groupItemTitle`s and the masked descriptions, and labelled
  "same question, same resolution source and time zone" or not (coordinator plus `science-reviewer`). If more than 5%
  are not genuine, the rules are revised **once** and re-hashed before any price is read. A second failure stops CB5-L.
  (Calibration: the cross-venue matcher's live run mispaired 56 of 167 pairs, and CB2's text-free ladder proxy found
  none of 10 genuine. A text grouper without an audit is not acceptable.)
- L-iii: eligible pair-captures per family in the dev window (eligibility only, no gap computed).
- L-iv: **gate G59: at least 20 audited live families with eligible pair-captures in the dev window.** Fewer → CB5-L is
  "not testable: n families" (L1 counted with p = 1) and stops; CH59 is closed at "too rare in the live universe".
- L-v (q0107, the guarded outcome read): the **historical inconsistent-resolution rate** on audited historical
  families, computed **at family level** (round-1 item 2): `r_inc` = the share of resolved families with at least one
  inconsistent (f, D), and `r_inc⁺` = its Wilson 95% upper bound with n = resolved families (the nested (f, D) units of
  one family are not independent). The (f, D)-level rate is reported. **Fewer than 30 resolved families → `r_inc`
  "unknown", which blocks any L1 advance** (it no longer hands over to the payoff gate, so less data can never make the
  gate easier). The minimum family count at which the gate can be passed at all is stated in §CB5-L.

**K (no lead statistic):**
- K-i: C1 pairs and events by category; usable steps and event clusters per bucket (R, O) in the non-sports primary
  and in the sports stratum; G per way (event, UTC date) for the small-G rule; pairs with ≥ 30 usable steps in both
  buckets (the within-pair contrast); and **the recomputed K1 MDE** from these counts and the C1 20-minute SE
  (≈ 0.036, round-1 item 12). The MDE is stated, never used to change a threshold.
- K-ii: Kalshi spread distribution and the share of steps with a Kalshi mid change, by bucket; the Polymarket
  flat-step share by bucket.
- K-iii: **J4 wide-state rate by hour.** From complete captures with `capture_start_utc < T_J4R`: the share of rows
  with a two-sided quote and mid in [0.02, 0.98] whose spread exceeds 0.10, by capture hour mapped to R/O in New York
  time. If R and O differ by more than 2 percentage points, every K1 verdict carries the label "Polymarket quote state
  differs by hour (J4 confound possible)". This uses Oct 2026 captures, while the pairs span Nov 2025 to Jul 2026, so
  it is context, not a control within the sample.

Floors are never revised from the census. **The CDF grouper (patterns, period tables, matching rule) is hashed into
the declaration before q0104 reads any title or question.**

### 2.8 Compute, network and stop rules

- Host: 1 OCPU, about 5.6 GiB RAM shared with the live collector (MemAvailable about 4.4 GiB at the 18:10Z check).
  Queue worker: one job per lane (`cpu` default, `net`), nice 19, start only if `MemAvailable ≥ mem_mb + 1200`, address
  cap 2 × `mem_mb`, start blackout 02:45-05:30 UTC for jobs with `mem_mb ≥ 500`. Never two multi-GB jobs at once.
- **Lanes.** The network jobs (q0102, q0103, q0104, q0107, q0111) use the `net` lane: q0002 is done and no longer holds
  it. The extractor backfills (q0101, q0105) stream release copies and use `cpu`, as do the analysis jobs. Never two
  multi-GB jobs at once.
- **Priorities.** CB5 analysis stays below every CB1-CB4 job: census 40, measurement 39, screens and replications 38.
  Data jobs: the `listings` backfill q0101 at **57** (calendar-bound: dev captures become deletable from about
  2026-10-18; below the h7 jobs at 58 so it cannot delay CB4's `T_seal` deadline). The head refetch, frame, cohort fetch
  and CDF backfill at 41-46.
- 10 CPU-hour cap per family. A job failing twice for the same non-transient reason stops and is recorded.
- A null is "not detected at MDE x", never "absent". No re-screen of a failed CB5 test with altered windows, horizons,
  thresholds, seeds definitions, groupers or populations, on any data.
- **Disk guard.** Host `data-dumps` was 8.8 GB at drafting (9.8 GB free on the volume). Every CB5 data job refuses to
  start above 12 GB (hard ceiling 14 GB; the collector cap is 13 GB and snapshot 8-day deletion has been active since 2026-10-17 04:39Z; CB4 used 10 GB). The 12 GB figure is operational and sits outside the declaration hash (section 10). Output caps: `listings` 0.05 GB, `head_prices` 0.05 GB, census cohort 0.03 GB,
  CDF frame 0.02 GB (the restored IF-H2 `events.jsonl.gz` lives in a scratch directory and is deleted after q0104 and
  q0107), `cdf` 0.05 GB, replication cohort 0.10 GB. Release copies are streamed one capture at a time (peak ≤ 0.2 GB).
  **Headroom precondition at release time (round-1 item 15).** The guard is close: 8.8 GB on 2026-10-16, growing about
  0.75 GB a day while snapshot deletion is gated (`RETENTION.md`). Before any CB5 data job (q0101-q0105, q0111) is
  committed, the coordinator checks and records in the commit message either (a) that snapshot deletion is active on
  the host, or (b) that the current size plus 0.75 GB × (days until the job's last scheduled run) plus the job's output
  cap stays ≤ 12 GB, with ≥ 3 GB free on the volume. If neither holds, the job is not committed and the hold is
  recorded. The precondition never changes retention; it only delays CB5.
- **Network etiquette:** as CB2 §2.8 and CB4 §2.8 (shared `Limiter` ≤ 4 rps, yield to the live collector, 429 and
  `Retry-After` back-off, stop on repeated 429, collector-health stop).
- **IF-H2 restore.** The release is six zstd tar parts (about 4.8 GB). A Claude session (not the queue) restores only
  the member `research_lab/if_h2/events.jsonl.gz`: download the parts on the Mac, verify `MANIFEST.sha256`, extract the
  one member, check it against `files.sha256`, copy it to `~/arepo/scratch/cb5/` on the host, and delete the Mac parts.
  Recorded in q0104's manifest. No release asset is modified.

### 2.9 Snapshot inputs and the retention gate

`RETENTION.md` is owned by another session. CB5 states its rule here; the coordinator adds it to the gate-release rule.
- CB5 readers of raw captures: only `run_cb1_extract.py --tables listings,cdf` (pass step and the backfills q0101,
  q0105) and the q0106 K-iii count (captures `< T_J4R`, row-level spread and mid only).
- **CB5 places no requirement on snapshot retention.** Captures deleted before the backfills reach them are streamed
  from verified release copies one at a time (CB4 §2.10 machinery, reused). A capture whose release copy is missing or
  fails verification is counted as missing, never reconstructed. The K-iii count runs before deletion if possible;
  otherwise it runs on release copies.
- `cb5_extract/` is never deleted (no rule), like `cb1_extract/`.

### 2.10 Funnel and what a prospective registration would look like

CB5 follows the mission's funnel (`AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md` §4): **A** screen (Stage 1) → **B**
selection by the Stage-1 gate, placebo, attribution and robustness (never one strong backtest) → **D** frozen
development replication on post-freeze data (Stage 2, L2-dev) → a separate **prospective confirmation** registration
with recorded prices (Stage P) → **E** economic validation at recorded prices. Stage 2 here is *prospective in time*,
but its prices are modelled (G) or 2h-latency touches (L), so it is development replication, not confirmation. Stage P
for any survivor needs its own registration, frozen before its data exist:

- **G survivor (Stage P-G).** Population: non-sports, non-weather new listings, first seen in `listings/`. One-week
  pilot first for the sweep budget, then ≥ 8 weeks. New collection: a **targeted sweep stratum** at age `L + 24h ± 30
  min` and `L + 72h ± 30 min` for every population market with `|d| ≥ 3c` (an addition to `sweep_books.py`, budgeted
  against its pass limit), plus the trade-sample stratum for the same markets over `(t1, t1 + 24h]`. Execution: a
  maker order at the recorded touch on the seed side with a queue-position fill rule from recorded prints; exit at the
  recorded touch at `t3`. Primary: net per filled share after fees and R2; capacity from recorded depth. Frozen:
  seed definition, `d` threshold, horizons, clustering (event, listing date), Holm over the registration's tests.
  Acceptance: one-sided p < 0.05 after Holm, floor 1.0c, +0.75c robustness, attribution rule.
- **L survivor (Stage P-L).** The frozen family list with weekly additive versions applied prospectively (CB2 rule).
  Sweeps of every leg at trigger time (full depth to the size needed for the pair), executed against the next sweep or
  capture. A maker-leg variant with trade-through fills from targeted trade samples. Realised payoff at each family's
  deadline (UMA lag allowed, censoring declared). Capacity in $ per week.
- **K (measurement).** No Stage P of its own. If K1 is adopted (two-sided pass, floor, controls), the next
  Kalshi-anchored registration (a CH38 or E009/E010 follow-up on receipt-timed data) must either include the declared
  hour interaction or state "hour moderation not detected at MDE x (CB5-K)". K1 can never lower a cost or relax a gate
  of a frozen test (one-directional use, as CB4 R0).

---

## 3. Jobs

### CB5-G: Seed-anchor reversion on day-0 slices (CH56)

**Question.** In a new market, the pre-trade price (the seeded two-sided quote) is a model-based anchor. When the
first day's trading moves the price away from it, does the price revert toward the seed over days 1-3 (G1)? Does a
maker order on the seed side at +24h, exited at +72h, pay after costs (G2)?

**Why new / overlap.** CB1-E (CH22) uses the same windows with a text rule and no seed. The ML panel and HB1/HB2 start
one day after the first price and exclude untraded rows (T5-DEV placeholder rule). Here the pre-trade point is a
*feature*, never a target. Every target uses trades.

**Data.**
- Stage 1: `h2_main` trades and frame, plus `h2_main/cb5/head_prices/` (q0102). One CLOB `prices-history` request per
  eligible market for `[L − 1h, L + 4d + 1h]` at `fidelity=10` (one window ≤ 14 days). A second request at
  `fidelity=1` for `[L − 1h, L + 24h]` is stored as a reported seed-resolution variant if the API returns sub-10-minute
  spacing (recorded either way).
- Stage 2: the replication cohort. Markets first seen in `listings/` with `created_at ∈ [T5_rep_start,
  T5_G_rep_end)`, fetched by q0111 at `L + 4d + 2h` (prices as above, Data API trades newest-first ≤ 10,000; with 4 days
  of history, truncation should be rare and is counted). Outcomes are fetched only at `T5_G_read` + 30 d, for the
  reported hold-to-resolution variant.

**Population (frozen frame; the same rules in both stages).**
- Binary markets (two outcomes), token 0 as the reference token. `fee_category` not sports (stratum) and not weather
  (excluded). Not a member of a neg-risk event with more than 2 members (multi-outcome seeding follows a different
  template; reported stratum).
- Scheduled life `end_at − L ≥ 4 d` (a scheduled fact). A market that resolves before `t3` anyway takes its payout as
  the exit price (CB1-E convention). Inclusion never depends on early resolution.
- **As-of time of `end_at` and the neg-risk member count (round-1 item 7).** In the replication cohort both are taken
  from the market's first sighting in `listings/` (the member count = markets sharing its `neg_risk_market_id` in that
  capture, counted over the full capture by the extractor and stored as `neg_risk_n_members_at_sighting`; the first sweep's
  `batch_receipt_utc` is stored as `sweep_batch_receipt_utc`, the as-of time of the sweep sizes). In h2 they are only available as of `T_h2_clock`, after the listing: end dates can be moved and members
  added later. This is a disclosed look-ahead in the h2 population (one more reason for the L1 ceiling). It cannot
  enter the replication.
- h2 only: `L + 4d + 1h ≤ T_h2_clock`.
- **Untruncated trade history back to L** (stored trades known to reach `L`). Otherwise unavailable, excluded and
  counted (reported by outcome at the screen).
- ≥ 3 trades in `[L, t1)`, `t1 = L + 24h`.
- **Valid seed** (below), with `σ ∈ [0.02, 0.98]`.
- One unit per market. Event id and listing date (UTC date of L) recorded for clustering.
- **h2 sampling strata (round-1 item 6).** h2 was drawn by `draw_sample` stratified by status × `fee_category` ×
  created month (`CASE_STUDY_MADURO.md`, Part B). Status at the draw (active or closed at `T_h2_clock`) is post-listing
  information. The unweighted h2 estimate describes the drawn sample, not the listing population, and is labelled so.
  A stratum-adjusted G1 slope (the draw strata as fixed effects) is computed and must agree in sign (§2.6 (ix)); a
  design-weighted slope is reported if the draw's sampling probabilities are recoverable from the h2 manifest. The
  replication cohort is not stratified by status.

**Definitions.**
- `t_ft` = venue `ts` of the first trade on either token. Trades on token 1 are mapped to token 0 as `1 − p`.
- **Seed.** `S = {points stamped s with L − 600 ≤ s and s + 600 ≤ t_ft}` (usable strictly before the first trade).
  Valid iff `|S| ≥ 1`. `σ` = the latest point in S. Reported: `|S|`, `max(S) − min(S)` (seed stability), and
  `t_ft − L`.
- **Informative seed:** `|σ − 0.5| ≥ 0.0005`. **0.50 seed:** `|σ − 0.5| < 0.0005` (the §2.6 attribution stratum).
- `VWAP₁` = size-weighted mean token-0 price of all trades in `[t_ft, t1)`. **Feature `d = VWAP₁ − σ`.**
- **Print series.** Ask-side prints = token-0 `BUY` and token-1 `SELL` (mapped); bid-side = token-0 `SELL` and token-1
  `BUY` (mapped). `P_A[a, b)` = ask-side VWAP over `[a, b)`, unavailable if empty; `P_B` likewise.
- **Disjoint windows.** Entry `E = P_A[t1, t1 + 6h)`; exit `X = P_A[t3 − 6h, t3)` with `t3 = L + 72h`.
  **Target `y = X − E`** (cents). The feature window `[L, t1)` and the target windows do not overlap, so noise in `VWAP₁`
  can only attenuate β, not create it. Same-side prints remove bid-ask bounce from the target.
- Bid-side target `y_B` and history-price target `y_H = p(t3) − p(t1 + 6h)` (usable rule): binding sign agreement.
- **G1 statistic:** OLS slope β of `y` on `d` (with intercept), informative-seed units. Test β < 0.
- **G2 units:** informative-seed units with `|d| ≥ 3c` at `t1`. Side `= sign(d)` (ask if the price rose above the seed,
  bid if it fell). Order, fill and exit as §2.1. Statistic: mean net per filled share, test > 0.

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **G1** | mechanism | informative-seed market with `E` and `X` available | slope β of `y` on `d` | < 0 |
| **G2** | economic | filled paper maker order | mean net per filled share | > 0 |

**Clustering.** One-sided p = the max over event and listing date (UTC) of CR1 (small-G rule per way).

**Era rule (from the CB4 register, declared now).** If `era_rule = post_rollout_or_interaction`, G1 and G2 may advance
or pass only if the post-rollout subset (`L` on or after the category's `era_window_start`) has the declared sign.
G2's pre-rollout fills carry `−a_AS` (R2). q0108 depends on CB4's q0089 for this reason. The replication cohort is
entirely post-rollout.

**Truncation worst case (binding).** h2 units excluded for truncation are added back with `y_H` (history-price target)
and, for G2, with the fill decided on history prices crossing `q`. The estimate must stay on the declared side.

**Attribution (binding, §2.6).** The level-calibrated 0.50-seed stratum rule and the seed-permutation placebo on
`β^LC`. Both must pass for an advance or pass to be credited to CH56. Otherwise the label is "generic first-day reversal".

**MDE (the census replaces these).** Inputs from documents only: CB1-E expects about 200-400 eligible h2 markets for a
similar genesis rule; the valid-seed share is unknown and may be small (`HISTORICAL_ML_DEV.md`: series mostly begin at
the first trade). Assume SD(y) ≈ 6c over two days (CB1-E's 7-day SD ≈ 8c), SD(d) ≈ 6c (CH56 envelope 5-15c), and a
cluster design effect of 2. Then SE(β) ≈ SD(y) / (SD(d)·√(n/2)):
- h2, n = 100: SE ≈ 0.14, **Stage-1 MDE ≈ 0.45** (z 2.33 + 0.84). n = 300: SE ≈ 0.08, MDE ≈ 0.26. CH56's envelope is
  β ≈ −0.5, so h2 can detect only the top of it, and G56 may fail.
- Replication cohort: listings per day are unknown (census G-viii). At 900 units over three weeks, SE ≈ 0.047 and
  **Stage-2 MDE ≈ 0.14** (Holm k = 3, z ≈ 2.13 + 0.84).
- G2: 60% of units with `|d| ≥ 3c` and a 30-50% trade-through fill rate give **20-90 fills on h2, below the
  testability minimum** (hence the carry rule, §2.3). Replication: 160-270 fills with a per-fill SD ≈ 8c give SE ≈
  0.7-0.9c, **MDE ≈ 2.1-2.7c**, against an envelope (half of a 5-15c deviation, minus ≈ 3.5c exit cost) of roughly
  0-4c. **G2 is expected to fail its cost check unless the reversion is near the top of the envelope.**

**What would kill CH56.** The first-trade-echo check (G-ii) or the seed-semantics gate (G-v) fails; the side audit
fails; G56 fails; G1 not detected at MDE; G1 present but the 0.50 stratum reverts as much (generic reversal) or the
seed-permutation placebo on `β^LC` advances; the print and history targets disagree in sign; the level-controlled slope loses
sign; the effect exists only before the fee rollout; G2 ≤ 0 after the binding cost.

**Verdict map.**
- G1 and G2 replicated with attribution → "development-replicated seed-anchor reversion with a modelled maker route
  (L2-dev)" → Stage P-G (§2.10).
- G1 replicated, G2 not → "seed anchoring exists, not capturable after a taker exit at MDE"; a hold-to-resolution or
  maker-exit design would need its own registration.
- G1 not detected → "seed-anchor reversion not detected at MDE x". CH56 is closed for this seed definition.

**Stop rule.** No G advance and no carried G2 → q0111/q0112 are not committed. The census cohort is never read past
its census window.

### CB5-L: Ladder-versus-bucket CDF consistency (CH59)

**Question.** When the same timing question is listed as a cumulative ladder rung ("X by D") and as an exclusive
neg-risk bucket event ("X in <month>", ..., "not in YYYY"), the identity `P(by D) = Σ_{periods ending ≤ D} P(bucket)`
must hold. Is it violated at the touch by more than fees, and is the violation still present at the touch at the next
capture (L1)? The `cdf` rows carry touch prices but no touch sizes, so L1 measures **persistence at the touch**, not
executability; executability is checked only on the depth subset (round-1 item 10).

**Why new / overlap.** IF-H2's grouper excludes neg-risk "which month" events; CB2's excludes "in <month>"; CB1-D tests
neg-risk sums within one event. No AREPO test pairs the two representations.

**Frame (q0104; grouper `cdf-grouper-v1`, hashed before any title or question is read).**
- **Sources.** (1) IF-H2 `events.jsonl.gz` (restored, §2.8): events with start dates 2025-06-01 to 2026-10-10.
  (2) A fresh Gamma `/events` walk of start dates from 2026-10-01 to the q0104 run (7-day windows split at the offset
  cap, as IF-H2), with `closed` true and false. Parse guard: `outcomePrices` and `outcomes` are dropped before any
  record is kept. `umaResolutionStatus` is kept only as a string for the exclusion list.
- **Ladder side (L-events).** Binary, non-neg-risk markets whose question contains "by" or "before" with a deadline
  parsed by the IF-H2 parser (`if_h2.parse_deadline`, `groupItemTitle` first; "before D" means by D − 1 day; deadline
  = 23:59:59 America/New_York on that day). Direction INC only (CB2's DEC forms such as "through D" and "continue
  through D" are excluded). A rung may sit in a multi-rung event or be a one-market event.
- **Bucket side (B-events).** Neg-risk events, `negRiskAugmented = false`, no member flagged as an "Other" placeholder
  (CB1-D rule), every member's `groupItemTitle` parsing to a **period** under the frozen period table:
  - month (`January` ... `December`, optional year);
  - quarter (`Q1` ... `Q4`, optional year);
  - year (`2026`);
  - an opening bucket (`Before <period>` or `By <date>`);
  - a closing bucket (`Not in YYYY`, `After <period>`, `<YYYY+1> or later`, `Never`).
  Each period has [start, end] in New York time. The open periods must tile a contiguous range with no overlap.
  Otherwise the event is excluded and counted.
- **Subject match.** Ladder stem = question with the date phrase removed, lowercased, punctuation and whitespace
  normalised, stopwords dropped (`if_h2` stem rule). Bucket stem = event title with the period phrase removed ("in which
  month", "when will", "in <period>", "by ...") under the same normalisation. A ladder rung and a bucket event match iff
  (a) the token-set Jaccard of the stems is ≥ 0.6 with ≥ 3 shared content tokens; (b) the sets of numbers in the stems
  are identical (cross-venue rule); (c) no contract-changing word appears on one side only (the `cross_venue` conflict
  list plus `announce`, `confirm`, `officially`, `first`, `again`, `before`, `after`); (d) their masked descriptions
  share the resolution-source domain or named source (`resolution source` tokens; a mismatch excludes); (e) mutual best
  match with a 0.10 Jaccard margin, ties dropped.
- **Pair (f, D).** A family f = (matched ladder rungs, bucket event). For each rung with deadline D such that D equals
  the end of a bucket period (same New York calendar day), the pair `(f, D)` uses the rung `L_D` and the set
  `B_D = {buckets whose period ends ≤ D}`, `K_D = |B_D|`. Rungs whose D is not a bucket boundary are excluded and
  counted.
- **Versioning.** As CB2-L: v1 applies retrospectively to the dev captures (later text is a disclosed look-ahead in the
  frame, never in prices). Weekly additive versions apply prospectively from their `listed_utc`. The replication uses
  only versions listed before each capture.
- **Audit gate:** §2.7 L-ii (text only; one revision allowed; a second failure stops CB5-L).

**Definitions at capture c** (every leg open, `accepting_orders`, two-sided, `volume_num > 0`; legs read from
`cdf/<capture_id>`; **leg timing:** `max − min` of `received_utc` over all legs of the pair ≤ 5 min, otherwise the
pair-capture is ineligible, excluded as a trigger and counted, round-1 item 10):
- **Direction A (ladder rich):** buy every bucket in `B_D` at its ask and buy NO on `L_D` at `1 − bid(L_D)`. The payoff
  is exactly 1 in every state. `net_A = bid(L_D) − Σ_{b∈B_D} ask(b) − Σ fees`.
- **Direction B (bucket rich):** buy YES on `L_D` at its ask and NO on every bucket in `B_D` at `1 − bid(b)`. The payoff
  is exactly `K_D` in every state. `net_B = Σ_{b∈B_D} bid(b) − ask(L_D) − Σ fees`.
- Fees: §2.1, one taker leg per market at the price paid. Capital: A ≈ 1; B ≈ `K_D − Σ bid + ask` (conservative; a
  conversion-adjusted capital is reported as optimistic).
- **Trigger:** `max(net_A, net_B) ≥ 0.5c` at c. **Execution** at the next complete capture c' (gap 1.5-3h), same
  direction, at c' touches if every leg is still eligible, including the 5-minute leg-timing rule; otherwise no trade,
  net 0, kept (CB2 rule). `net'` = the net at the c' touches ("persistent at touch").
- **Pair-hours** (descriptive): each triggered pair-capture counts 2h. Reported per family-week, with the persistence
  curve (share of triggers with same-direction net > 0 at c+1, c+2, c+3 and c+6).
- `R_ann` uses the hold from c' to D (the deadline). Small gaps over long holds fail the 10% floor. That is the
  economic answer, not a defect (CB2).

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **L1** | economic | trigger (f, D, c) | mean `net'` per pair (cents), executed at c' | > 0 |

**Clustering.** One-sided p = the max over family and family × ISO week (small-G rule per way).

**Binding gates on L1 (beyond §2.3; revised in round 1). An "unknown" or "inconclusive" gate never counts as met.**
- **Coherence placebo** (§2.6): at most 1.5% of mismatched-family draws as coherent as the matched pairs; "not
  testable" blocks the advance.
- **Historical divergence (from q0107).** An (f, D) is inconsistent when the ladder rung's outcome differs from the OR
  of the bucket outcomes over `B_D` (including bucket events resolved to a closing bucket while the rung resolved YES,
  and the reverse). `r_inc` and `r_inc⁺` are family-level (§2.7 L-v). L1 may advance only if
  `mean(net') − 100c × r_inc⁺ > 0`: every inconsistent resolution is costed as a full one-unit loss on the pair
  (conservative). This is CH59's kill ("an inconsistent-resolution rate above the mean gap"). **If `r_inc` is unknown
  (< 30 resolved families), L1 cannot advance** (the draft let the payoff gate stand in; that made less data easier).
  - **Minimum n at which the gate is passable.** With zero inconsistent families the Wilson upper bound is
    3.84 / (n + 3.84). It falls below 6c (the top of CH59's 2-6c gross envelope) only at **n ≥ 61 resolved families**,
    below 4c at n ≥ 93, below 2c at n ≥ 189 and below 1.3c at n ≥ 292. At the 30-family minimum it is about 11.3c. So
    with fewer than about 61 historical families the gate cannot be passed by any plausible `net'`, and the census
    states this before the freeze.
- **Realised payoff (prospective, as CB2-L).** On triggered pairs determined by `T5_L_out`, the share whose realised
  payoff falls short of the promised one (1 for A, `K_D` for B) must be ≤ 2%. Fewer than 30 determined pairs →
  "inconclusive (payoff unverified)". Deadlines are often months away, so this is likely. **An inconclusive payoff
  gate blocks crediting:** a Stage-2 Holm pass is recorded as "passed, pending payoff verification, not credited", no
  Stage P-L registration may start, and the gate is re-read once at the first date by which ≥ 30 triggered pairs are
  determined, at the latest 2027-06-30. Still inconclusive then → "not credited (payoff unverified)", final.
- **Depth.** Recomputed on triggers whose legs were all swept with size ≥ 5 at the next pass; must agree in sign;
  fewer than 30 family clusters → "inconclusive (depth unverified)", which also blocks crediting.
- **CB1-D overlap hold (round-1 item 11).** When `K_D = N − 1` (every bucket except the closing one), `Σ ask` over `B_D`
  is close to CB1-D's neg-risk ask sum, computed on captures inside CB1-D's sealed replication window
  (`[CB1 T_rep_start, 2026-11-09)`), which overlaps the L dev window. **q0109 is not committed, and no L dev statistic
  is computed or printed, until CB1-D's replication results are committed or CB1-D is recorded as stopped, and never
  before `T_CB1D_rep`.** The census computes eligibility only and never a bucket sum. The replication q0113 runs after
  `T5_L_rep_end`, which is later than `T_CB1D_rep`, under the same condition.

**MDE (the census replaces these).** The family count is unknown (gate G59 ≥ 20). With per-trigger SD ≈ 3c (CB2-L's
CB1-D analogue) and 20-40 family clusters, SE ≈ 0.5-0.7c, so the **dev MDE ≈ 1.6-2.2c** and the replication MDE about
the same at k ≤ 3. CH59's envelope (2-6c gross across N legs) is above the MDE gross, but the taker fee on `K_D + 1`
legs is large: at mid prices and the conservative rate, 4-7 legs cost several cents. **Expect L1 to be "not testable"
(G59) or to fail the cost check outside zero-fee categories.** A maker-leg route cannot be tested at 2h cadence and is
reported only.

**What would kill CH59.** G59 (< 20 families); the grouper audit fails twice; the coherence placebo fails (matched
pairs no more coherent than unrelated ones); L1 not detected at MDE; `r_inc` unknown or the divergence gate fails
(mean net' below the costed divergence loss); realised payoff > 2% short; depth disagreement.

**Verdict map.**
- L1 replicated with every gate met (payoff and depth verified) → "ladder-bucket CDF violations persist at the touch
  for 2h (L2-dev); executability shown on the depth subset only" → Stage P-L (§2.10).
- L1 replicated, payoff or depth inconclusive → "passed, pending verification, not credited".
- L1 not detected, high pair-hour incidence → "violations exist at the touch but do not persist at the touch for 2h
  after taker fees" (maker route untested).
- G59 fails → CH59 closed: "too rare in the live universe (n families)".

**Stop rule.** No L1 dev advance → the replication spec q0113 is not committed.

### CB5-K: Hour-of-day moderation of the Kalshi lead (CH58), measurement

**Question.** Is the 10-20 minute Kalshi→Polymarket lead on the audited historical pairs different between US overnight
hours and US day/evening hours?

**Data and population.** `cross_venue/series/*.npz` with `matches.json`. The **C1 set** is reproduced in code through
`run_cross_venue.load_pair_series(cv.POINT_LAG_S)` and `audit_sets(...)["rule"]` (the r1 title/rule drops): 316 pairs,
183 events, 517,616 usable steps. **C1 provenance (disclosed, round-1 item 14).** The rule-based drops use no outcome,
but the 4 hand-dropped date/inversion pairs were first surfaced by the outcome-disagreement list
(`CROSS_VENUE_STUDY.md`, Part A caveat), although each is identifiable from its title. C1 membership is therefore not
fully outcome-blind, and K1 inherits that. If those 4 pairs are identifiable from the committed drop list, K1 with them
re-added is reported (not counted). Alignment is the study's conservative one (Polymarket point usable
at `stamp + 600 s`, Kalshi candle mid with spread ≤ 10c, both prices in [3%, 97%], nothing interpolated). Primary =
**non-sports C1 pairs** (`k_cat ≠ Sports`). Sports pairs are a reported stratum. Window as the study (up to 30 days
before the earlier resolution).

**Hour buckets (declared; America/New_York, DST-aware, assigned by the grid time t of the Kalshi move).**
- **R (US day and evening): [09:30, 23:00).** **O (US overnight): [23:00, 09:30).** All weekdays.
- **Declared deviation from the idea text.** CH58 named "US retail 13:30-20:00 ET-equivalent vs other", but its
  mechanism contrasts retail hours with *overnight*, and mobile retail flow runs into the evening. A two-way R/O split
  near 56/44 also maximises power. The market-hours split (weekday 09:30-16:00 vs the rest) is reported, not counted.

**Statistic.** For a bucket b, `A_b(L) = r(ΔK_t, ΔP_{t+L}) − r(ΔP_t, ΔK_{t+L})` over the steps of b pooled across pairs
(10-minute changes, study §5.1). The lead is one 10-minute step plus the timestamp convention (study §5.1: the peak
moves between 10 and 20 min with `pm_lag`), so the primary sums both lags:
**`K1 = [A_O(10) + A_O(20)] − [A_R(10) + A_R(20)]`.** CH58 predicts K1 > 0, but as a measurement it is tested
two-sided.

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **K1** | measurement | 10-min step (pooled), clustered | overnight minus day/evening lead asymmetry, lags 10+20 min | two-sided |

**Inference.** Two-sided p = the max over event-cluster and UTC-date-cluster bootstraps (4,000 draws each, as the
study; seed 5163), percentile. Small-G rule per way.

**Confound controls.**
- **Activity matching (binding for adoption).** Steps in R are reweighted to O's joint distribution of `|ΔK|` deciles
  and Kalshi-spread terciles (inverse-probability cell weights; empty cells dropped and counted). `K1_matched` must have
  K1's sign and at least half its magnitude. Otherwise the label is "hour difference explained by Kalshi activity
  and spread" and K1 is not adopted.
- **Within-pair contrast (binding for adoption; round-1 item 13).** The pooled K1 mixes pairs whose step shares in R
  and O differ, so a between-pair composition difference could create it. `K1_pair` = the pair-equal-weight mean over
  pairs with ≥ 30 usable steps in each bucket of `[A_O,p(10) + A_O,p(20)] − [A_R,p(10) + A_R,p(20)]`, with the same
  cluster bootstraps. It must have K1's sign and at least half its magnitude. Pairs below the step minimum are counted.
  An event-fixed-effects version is reported.
- **Reported:** Kalshi candle volume by bucket (the direct retail-activity proxy) and K1 by Kalshi-volume tercile;
  Polymarket flat-step share by bucket; K-iii J4 wide-state rate by hour (§2.7), as a label.
- **Adoption** (one-directional, §2.10): two-sided p < 0.05, `|K1| ≥ 0.10`, the pseudo-split calibration holds
  (§2.6), activity matching and the within-pair contrast hold, and robustness (ii)-(iii) of §2.6.

**MDE (recomputed in round 1 on C1, item 12; the census K-i replaces it).** The draft used the v1 figures (341 pairs,
190 clusters, SE 0.033). On C1 the 20-minute asymmetry is 0.257 with CI (0.190, 0.332) (`CROSS_VENUE_STUDY.md` §10.3),
so SE ≈ 0.036 on 316 pairs and 183 events. 149 of the 316 pairs are sports, so the non-sports primary keeps about 53%
of the pairs (its step share is unknown until K-i). With R about 56% and O about 44% of steps: SE_R ≈ 0.036 / √(0.53 ×
0.56) ≈ 0.066 and SE_O ≈ 0.036 / √(0.53 × 0.44) ≈ 0.075; the difference has SE ≈ 0.09-0.10 (event pairing helps a
little; summing two lags changes this little; fewer non-sports event clusters would raise it). **Two-sided MDE ≈
0.25-0.28 (working figure 0.27), about the size of the whole lead.** K1 can only detect a lead that roughly vanishes in
one bucket. A null means "hour moderation not detected at MDE ≈ 0.27" (or the K-i figure), never "no moderation".

**Optional K1-R (declared now, conditional).** After `T_E9_unseal` **and** after both E009 and E010 final analyses are
committed, the same K1 (same buckets, both lags mapped to E009's receipt-timed 2-minute grid as the 10- and 20-minute
changes) may be computed once on the E009/E010 live pairs. It is a separate one-test family (two-sided α = 0.05) and
needs the E009/E010 owner's written sign-off in the ledger before its spec is committed. It cannot alter any
E009/E010 verdict. Without sign-off it is not run and not counted.

**What cannot be concluded.** Hour is a proxy for Kalshi flow composition. No Robinhood or Kalshi routing data exist
(CH58, §4 of the hypotheses file). Even an adopted K1 says only that the lead differs by hour on 2025-11 to 2026-07
non-sports pairs, at the 10-20 minute resolution limit. The Polymarket timestamp convention remains ambiguous (study
§6). No standalone money route exists.

**Verdict map.** Adopted → the conditioning rule of §2.10 binds the next Kalshi-anchored registration. Not adopted →
that registration states "not detected at MDE ≈ 0.27 (CB5-K)" (or the K-i figure).

### CB5-F: Data jobs

- **`listings` extractor table** (§4.3): pass step from deployment, plus the q0101 backfill from `T5_dev_start` (host
  raw captures, else release copies streamed one at a time).
- **h2 head refetch** (q0102): about 3,200 + 3,200 CLOB requests at ≤ 4 rps (about 30-45 min wall); output about 30 MB.
- **Census-cohort fetch** (q0103, after `T5_dev_end`): prices and trades of census-cohort listings (seeded sample of
  at most 3,000 non-sports, non-weather markets), stored only up to `min(first trade + 1h, L + 24h)` by a parse guard.
  About 6-10k requests, under 1 h.
- **CDF frame** (q0104): IF-H2 restore (Claude session, §2.8), plus a fresh walk of about 100-300 Gamma pages, plus
  the grouper and the text-only audit print. About 15-30 min, 1.5 GB peak (streamed JSON parse).
- **CDF extract backfill** (q0105, after the audit freeze of the family list): dev captures, list-filtered, host raw
  or release copies streamed (at most about 186 × 70 MB ≈ 13 GB ingress if all were deleted; peak disk ≤ 0.2 GB); pass
  step afterwards.
- **Replication-cohort fetch** (q0111): rolling; each listing fetched at `L + 4d + 2h`; at most 5,000 markets, about
  10k requests over three weeks.

---

## 4. Code needed

### 4.1 Modules

- `backend/astrolabe/research_lab/cb5_seed.py` (CH56)
  - `seed_points(points, t_ft, created_at)` (the §CB5-G set S with the +600 s rule), `seed(...)` → `(σ, |S|, range)`,
    `is_template_seed(σ)`.
  - `first_trade(trades)`; `map_token0(trades)` (token 1 as `1 − p`); `ask_side(trades)`, `bid_side(trades)`;
    `vwap(trades, a, b)`.
  - `g_population(frame, trades, prices, ...)`: every rule and exclusion counted, including truncation-known-true back
    to L, the scheduled-life rule and h2's clock rule. Uses `created_at` and `end_at` only.
  - `g_units(...)`: `d`, `E`, `X`, `y`, `y_B`, `y_H`; payout as exit if closed before `t3`.
  - `g1_slope(units, ways)` (OLS, CR1 per way, small-G), `g1_level_controlled(...)` (`β^LC`),
    `seed_permutation_placebo(..., slope="level_controlled")` (within `fee_category` × listing ISO week; the raw-slope
    variant reported), `template_stratum(...)` (the level-calibrated 0.50 rule: level fit on the 0.50 stratum, residual
    slope `β^{|0.5}` on informative units inside the stratum's 5th-95th `VWAP₁` range), `g1_stratum_adjusted(...)` (h2
    draw strata as fixed effects).
  - `g2_orders(units, prices, trades, cost_regime)`: placement, trade-through fill, exit, `+0.75c`, R2 `a_AS`;
    `breakeven_placebo_g2(...)`; `carry_rule(g1, g2)`.
  - `era_subset_rule(...)` (reads `cost_regimes`); `truncation_worst_case_g(...)`.
  - Census: `seed_echo_share(...)` (G-ii), `determinism_share(...)` (G-iv), `seed_book_agreement(listings, seeds)`
    (G-v), `side_audit_day0(...)` (G-vi), `window_count(trades, a, b)` (count-only accessor for G-vii),
    `g56_gate(...)`.
- `backend/astrolabe/research_lab/cb5_cdf.py` (CH59)
  - `PERIOD_TABLE`, `parse_period(group_item_title, created_at)` → (start, end) in America/New_York or None;
    `tiles(periods)` (contiguity and no overlap).
  - `ladder_rungs(events)` (reusing `if_h2.parse_deadline` and the stem rule; INC only), `bucket_events(events)`
    (neg-risk, not augmented, no "Other" placeholder, all members parse, tiling holds).
  - `stem_ladder(q)`, `stem_bucket(title)`, `match_families(rungs, buckets)` (Jaccard ≥ 0.6, ≥ 3 shared tokens, the
    numbers rule, the conflict words, the source rule, mutual best with 0.10 margin), `pairs(f)` → (f, D, B_D, K_D).
  - `grouper_declaration()` → the hashed rule text (patterns, tables, word lists, thresholds).
  - `guarded_events(path)` (drops `outcomePrices`/`outcomes` at parse), `walk_events(start, end, limiter)` (as
    `if_h2`, guard applied).
  - `audit_sample(families, seed)` (text only), `apply_audit(labels)` (one revision; the second failure raises).
  - `pair_state(capture_rows, pair, cost_regime)` → `net_A`, `net_B`, eligibility; `triggers(...)`;
    `execute_next(...)` (gap [1.5, 3] h, ineligible → 0); `persistence_curve(...)`, `pair_hours(...)`.
  - `leg_timing_ok(rows, max_spread_s=300)`; `l1_test(...)` (two ways, small-G), `coherence_placebo(...)` (mismatched
    families, same granularity and boundary day), `depth_check(...)`, `r_inc(historical_families, outcomes)` with the
    family-level Wilson bound, `divergence_gate(...)`, `realised_payoff_gate(...)`, `g59_gate(...)`.
- `backend/astrolabe/research_lab/cb5_hours.py` (CH58)
  - `c1_pairs()` (wraps `run_cross_venue.load_pair_series` and `audit_sets`; asserts 316 pairs and 183 events),
    `bucket_of(t_utc)` (America/New_York, DST-aware), `asymmetry(steps, lag)`, `k1(...)`,
    `k1_bootstrap(ways=("event", "utc_date"))`, `pseudo_split_calibration(...)` (block assignment within one
    bucket, 200 + 200 splits), `shift_12h_contrast(...)` (reported), `within_pair_k1(...)`, `activity_matched_k1(...)`,
    `k_census(...)`, `j4_wide_by_hour(capture_root, before=T_J4R)` (spread and mid only).
  - Refuses any path under `cross_venue_live/` unless a committed K1-R spec and sign-off file exist.
- Shared statistics are **imported, not copied**: the CB1/CB2/CB4 cluster gate, bootstrap, small-G p-value, LODO,
  break-even placebo, capacity, `log_trials`, census guard, `fetch_outcomes`, CB4's release-stream reader, and
  `cost_regimes.cost_regime`.
- `HYPOTHESES_CB5` and `declaration_sha256()` covering every population, window, seed rule, bucket, threshold, floor,
  gate, date, the grouper declaration and the carry and era rules.

### 4.2 Runner

`backend/scripts/run_cb5.py {head-fetch,cohort-fetch,cdf-frame,cdf-audit-apply,census,rinc,screen,measure-K,rep-fetch,
replicate,fetch-outcomes} --family G|L|K`.
- Refuses the run ids and roots of §1.3, and writes only under `research_lab/creative_batch5/` (plus
  `h2_main/cb5/head_prices/`).
- Declaration-hash guard (committed `model_specs/cb5_v1.json` must equal the code's hash) on `screen`, `measure-K`,
  `replicate`, `fetch-outcomes` and `rinc`.
- `cdf-frame` refuses until the grouper hash is committed. `cdf-audit-apply` writes the frozen family list (sha256) and
  refuses a third version. `rinc` refuses until the family list is frozen **and** the committed seal file carries
  `rinc_functions_sha256` equal to the code's (sources of `r_inc`, `wilson_upper`, `divergence_gate`, `credit_status`,
  `rinc_run` and `RINC_MIN_FAMILIES`, sealed together with the grouper hash before q0107 runs). It reads outcomes only for
  families whose every leg (rung and bucket member) closed, with a known close time, before `T5_dev_start`.
  `write-spec` refuses when `rinc.json` is absent, and the L counted runs refuse a spec with no `rinc_sha256`.
- `screen --family L` refuses until CB1-D's replication results (or its recorded stop) are committed and never before
  `T_CB1D_rep`. `rinc` writes `r_inc` "unknown" below 30 resolved families.
- `screen --family G` refuses until `cost_regimes_v1.json` is committed (era rule). `replicate --family G` refuses
  before `T5_G_read`, and runs the G-v check on the replication cohort before reading any target. `replicate --family
  L` refuses before `T5_L_rep_end`. `fetch-outcomes --family L` refuses before `T5_L_out`. `T5_rep_start` is read from
  its pinned committed file.
- `cohort-fetch --window census` stores nothing after `min(first trade + 1h, L + 24h)` (guard plus test).
  `rep-fetch` selects only listings with `created_at ≥ T5_rep_start`.
- Results are never overwritten.

### 4.3 Extractor addition (`creative_batch1.py`, version `cb1-extract-v4`; no change to `arepo_pass.sh`)

- Own root `research_lab/cb5_extract/` and manifest. CB1-CB4 tables stay byte-identical (test). **Coordination:** if
  CB3 or CB4 bump the extractor version again first, CB5's tables go into the next version in one change.
- `listings/<capture_id>.csv.gz`: rows for markets absent from the previous complete capture's listing and with
  `created_at ≥ capture_start − 6h`. Columns: `capture_id, capture_start_utc, received_utc, market_id, condition_id,
  event_id, clob_token_id_0, clob_token_id_1, created_at, start_date, end_date, fee_category, neg_risk,
  neg_risk_market_id, event_neg_risk_augmented, best_bid, best_ask, spread, last_trade_price, volume_num,
  accepting_orders, order_price_min_tick_size` plus first-sweep `best_bid, best_ask, bid_size_1, ask_size_1` (blank if
  not swept). Expected hundreds of rows per capture (measured by the backfill).
- `cdf/<capture_id>.csv.gz`: the same touch columns (without `created_at` and `start_date`) for every market id in the
  current frozen family-list version whose `listed_utc` precedes the capture. Tiny.
- Backfills use `--release-stream` (CB4 §2.10). The 10-minute and 500 MB pass limits hold.

### 4.4 Tests (`backend/tests/unit/test_cb5_seed.py`, `test_cb5_cdf.py`, `test_cb5_hours.py`)

- **Seed.** A point stamped 9 minutes before the first trade is not in S, and 10 minutes before it is. Points before
  `L − 600` are ignored. `σ` is the latest point in S. The 0.50 test uses the 0.0005 tolerance. Token-1 trades map to
  `1 − p`, and the ask/bid side assignment holds for all four (token, side) combinations. The feature window `[L, t1)`
  and the target windows `[t1, t1 + 6h)` and `[t3 − 6h, t3)` are disjoint: a planted shock in the last feature hour does
  not change E. Truncated history before L → unavailable. Early resolution → payout exit, and inclusion is unchanged
  (a fixture with an early `closed_time` stays in). The h2 clock rule holds. G2: a print at q does not fill and one
  strictly beyond q does; +0.75c applies; `a_AS` applies only to pre-rollout fills. The seed-permutation placebo
  draws within `fee_category` × week and uses `β^LC`; on a fixture with pure level reversion and real seed anchoring the
  `β^LC` placebo stays at or below 1.5% advances, while the raw-slope variant advances far more often. The level-calibrated template rule blocks
  crediting on a pure-level-reversion fixture and credits a fixture with seed anchoring added on top. `window_count`
  returns integers only. The stratum-adjusted slope uses the h2 draw strata. The
  carry rule fires only for "not testable for size" with an estimate ≥ 0. The census-cohort guard drops rows after the
  first trade + 1h. The G-v agreement uses only markets whose first sighting precedes the first trade with spread ≤
  0.10.
- **CDF.** Period parsing for months, quarters, years, opening and closing buckets with and without a year; tiling
  failure on a gap or overlap; augmented and "Other" events excluded. "by June 30" pairs with buckets ending ≤ June 30
  and "before July" equals "by June 30". A rung with D inside a period is excluded. The conflict-word, numbers and
  source rules reject planted mismatches (vice-president vs president; "announce" vs "happen"; different source
  domains). Mutual-best with margin; ties dropped. The parse guard leaves no `outcomePrices` in any stored record. The
  `net_A` and `net_B` arithmetic gives payoff 1 or `K_D` in every state of a synthetic outcome table. The execution gap
  rule and ineligible legs → 0; a pair-capture whose legs' `received_utc` spread exceeds 5 min is ineligible. The
  coherence placebo draws only non-matched bucket events of the same granularity with a boundary on D, and a synthetic
  frame where matched pairs are no more coherent than mismatched ones fails it. The divergence gate with the
  family-level Wilson `r_inc⁺` (0 of 30 families gives ≈ 0.113); unknown `r_inc` blocks the advance; an inconclusive
  payoff or depth gate yields "pending, not credited". The runner refuses q0109's `screen --family L` before CB1-D's
  replication results (or recorded stop) exist. The audit allows one
  revision and raises on the second. Prospective versioning: a family listed after a capture is absent from that
  capture's `cdf` rows.
- **Hours.** DST transitions (a step at 23:30 New York time on both sides of the November and March changes lands in
  O). C1 reproduction asserts 316 pairs and 183 events. Asymmetry equals the study's formula on a fixture.
  Activity-matching weights reproduce O's cell shares. The pseudo-split calibration assigns whole (pair, date,
  half-hour) blocks within one bucket at the O : R ratio and gives about 5% rejections on a no-moderation fixture. The
  within-pair contrast uses equal pair weights and the 30-step minimum. Refusal to open `cross_venue_live/`.
  The J4 count reads only captures before `T_J4R`.
- **Runner.** Refusals (run ids, roots, before freeze, before out-dates, before register, before grouper hash); writes
  outside data directories; `KIND_RULES` holds the CB5 kinds and the counter runs on the real `trials.jsonl`.

---

## 5. Draft queue specs

Paths follow `queue/README.md` (`argv[0]` under `backend/scripts/`, `cwd` `backend`). No spec is committed before its
code and tests exist; analysis jobs also need the reviewed CB5 freeze commit. **Numbering:** q0101-q0114, one id per
job (§0.1); CB4's q0084-q0093 drafts are unaffected.

```json
{"id": "q0101_cb5_listings_backfill", "title": "CB5-F: listings/ extract (first sightings of new markets) from complete captures since 2026-10-11T12:00Z (host raw, else release copies)",
 "family": "creative_batch_5", "priority": 57, "expected_value": "preserves the first-seen seeded touches needed for the CH56 seed-semantics gate",
 "data": ["research_lab/snapshots rows + rows_ext + book_sweeps (host, else verified release copies)"], "resources": {"mem_mb": 900, "cpu": 1, "lane": "cpu"},
 "depends_on": [], "argv": ["scripts/run_cb1_extract.py", "--backfill-from", "2026-10-11T12:00Z", "--tables", "listings", "--release-stream", "--budget-min", "150", "--disk-cap-gb", "0.05"],
 "timeout_s": 10800, "max_retries": 2, "repeat": {"max_runs": 4, "until_log_regex": "backfill_complete"},
 "outputs": ["data-dumps/research_lab/cb5_extract/{listings/,manifest.json}"], "next_action": "pass step continues (extractor v4)",
 "notes": "idempotent by capture_id; CB1-CB4 tables untouched; release copies streamed one capture at a time (peak <= 0.2 GB); priority 57 sits below the T_seal-bound h7 jobs (58)"}
```
```json
{"id": "q0102_cb5_h2_head_fetch", "title": "CB5-G: h2_main head prices [created-1h, created+4d+1h] at fidelity 10 (+ day-0 fidelity 1, reported) for eligible h2 markets",
 "family": "creative_batch_5", "priority": 41, "expected_value": "coverage-invariant listing windows for the CH56 h2 screen",
 "data": ["history/h2_main frame (ids, created_at, end_at)", "public CLOB prices-history"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu", "network": "clob"},
 "depends_on": [], "argv": ["scripts/run_cb5.py", "head-fetch", "--run-id", "h2_main", "--clock-cap", "2026-10-11T23:00:33Z", "--rps", "4", "--disk-cap-gb", "0.05"],
 "timeout_s": 7200, "max_retries": 2, "outputs": ["data-dumps/research_lab/history/h2_main/cb5/{head_prices/,manifest.json}"],
 "next_action": "q0106 census", "notes": "no trade or outcome read; windows end before the h2 request clock; refuses h3/h4/h5/h6/h7 run ids; yields to the collector"}
```
```json
{"id": "q0103_cb5_seed_cohort_fetch", "title": "CB5-G: census-cohort prices and trades up to first trade + 1h (listings created 2026-10-11T12:00Z .. T5_dev_end-1d)",
 "family": "creative_batch_5", "priority": 41, "expected_value": "the seed-vs-book agreement check (gate G-v) before the freeze",
 "data": ["cb5_extract/listings (< T5_dev_end)", "public CLOB prices-history", "public Data API trades"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu", "network": "clob, data-api"},
 "depends_on": ["q0101_cb5_listings_backfill"], "argv": ["scripts/run_cb5.py", "cohort-fetch", "--window", "census", "--max-markets", "3000", "--seed", "arepo-cb5-census", "--rps", "4", "--disk-cap-gb", "0.03"],
 "timeout_s": 5400, "max_retries": 2, "outputs": ["research_lab/creative_batch5/census_cohort/{prices/,trades/,manifest.json}"],
 "next_action": "q0106", "notes": "commit after 2026-10-27T00:00Z; parse guard stores nothing after min(first trade + 1h, L + 24h); never used for G1/G2"}
```
```json
{"id": "q0104_cb5_cdf_frame", "title": "CB5-L: CDF family frame (cdf-grouper-v1 over restored IF-H2 events.jsonl.gz + fresh Gamma walk from 2026-10-01; text-only audit print)",
 "family": "creative_batch_5", "priority": 46, "expected_value": "matched ladder-bucket families, frozen before any price is read",
 "data": ["scratch/cb5/if_h2_events.jsonl.gz (restored from release data-20261013-research-lab, verified)", "public Gamma /events"], "resources": {"mem_mb": 1500, "cpu": 1, "lane": "cpu", "network": "gamma-api"},
 "depends_on": [], "argv": ["scripts/run_cb5.py", "cdf-frame", "--ifh2-events", "../../scratch/cb5/if_h2_events.jsonl.gz", "--walk-from", "2026-10-01", "--rps", "2", "--audit-n", "50", "--seed", "arepo-cb5-cdf"],
 "timeout_s": 5400, "max_retries": 1, "outputs": ["research_lab/creative_batch5/cdf_frame/{families_v1.json,audit_sample.json,manifest.json}"],
 "next_action": "Claude session + science-reviewer: label the audit sample; run cdf-audit-apply; commit the family list hash", "notes": "refuses until the grouper hash is committed; outcomePrices/outcomes dropped at parse; one revision allowed; restore is a Claude-session step (section 2.8)"}
```
```json
{"id": "q0105_cb5_cdf_extract_backfill", "title": "CB5-L: cdf/ extract (all legs of frozen families) from dev captures since 2026-10-11T12:00Z (host raw, else release copies)",
 "family": "creative_batch_5", "priority": 45, "expected_value": "dev touches for the CH59 screen",
 "data": ["research_lab/snapshots (host, else verified release copies)", "creative_batch5/cdf_frame/families_v1.json (frozen)"], "resources": {"mem_mb": 900, "cpu": 1, "lane": "cpu"},
 "depends_on": ["q0104_cb5_cdf_frame"], "argv": ["scripts/run_cb1_extract.py", "--backfill-from", "2026-10-11T12:00Z", "--tables", "cdf", "--family-list", "../data-dumps/research_lab/creative_batch5/cdf_frame/families_v1.json", "--release-stream", "--budget-min", "150", "--disk-cap-gb", "0.05"],
 "timeout_s": 10800, "max_retries": 2, "repeat": {"max_runs": 6, "until_log_regex": "backfill_complete"},
 "outputs": ["data-dumps/research_lab/cb5_extract/{cdf/,manifest.json}"], "next_action": "pass step continues; q0106",
 "notes": "commit only after the audited family list is committed; up to about 13 GB release ingress if every dev capture was deleted (streamed, peak <= 0.2 GB)"}
```
```json
{"id": "q0106_cb5_census", "title": "CB5: pre-freeze census (G seed echo, determinism, seed-vs-book gate, side audit, G56; L families, eligible pair-captures, G59; K steps/clusters per bucket, activity, J4 wide-by-hour)",
 "family": "creative_batch_5", "priority": 40, "expected_value": "gates and MDEs before the freeze; no target, net or lead statistic",
 "data": ["history/h2_main (frame, trades, prices up to first trade + 1h)", "h2_main/cb5/head_prices", "creative_batch5/census_cohort", "cb5_extract/{listings,cdf} (< T5_dev_end)", "cross_venue/series + matches.json", "snapshots < 2026-10-20T03:00Z (spread, mid)"], "resources": {"mem_mb": 1500, "cpu": 1, "lane": "cpu"},
 "depends_on": ["q0102_cb5_h2_head_fetch", "q0103_cb5_seed_cohort_fetch", "q0105_cb5_cdf_extract_backfill"], "argv": ["scripts/run_cb5.py", "census", "--family", "G,L,K"],
 "timeout_s": 5400, "max_retries": 1, "outputs": ["research_lab/creative_batch5/census.json", "trials.jsonl (cb5_descriptive)"],
 "next_action": "Claude session: insert counts and gates here; freeze (model_specs/cb5_v1.json); pin T5_rep_start", "notes": "outcome guard; floors never revised from the census"}
```
```json
{"id": "q0107_cb5_rinc", "title": "CB5-L: historical inconsistent-resolution rate on audited closed families (guarded outcome read)",
 "family": "creative_batch_5", "priority": 40, "expected_value": "r_inc and its Wilson upper bound for the L1 divergence gate",
 "data": ["creative_batch5/cdf_frame/families_v1.json (historical, closed before 2026-10-11T12:00Z)", "public Gamma market outcomes"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "cpu", "network": "gamma-api"},
 "depends_on": ["q0104_cb5_cdf_frame"], "argv": ["scripts/run_cb5.py", "rinc", "--rps", "2"],
 "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch5/rinc.json", "trials.jsonl (cb5_descriptive)"],
 "next_action": "freeze", "notes": "reads outcomes only of historical families, never of live families or prices; commit after the family list is frozen"}
```
```json
{"id": "q0108_cb5_screen_G", "title": "CB5-G: Stage-1 screen on h2_main (G1 slope, G2 maker; 0.50-seed attribution; seed-permutation and break-even placebos; era rule)",
 "family": "creative_batch_5", "priority": 38, "expected_value": "whether CH56 advances to the prospective replication",
 "data": ["history/h2_main", "h2_main/cb5/head_prices", "model_specs/cb5_v1.json", "model_specs/cost_regimes_v1.json"], "resources": {"mem_mb": 1200, "cpu": 1, "lane": "cpu"},
 "depends_on": ["q0106_cb5_census", "q0089_cb4_measure_commit"], "argv": ["scripts/run_cb5.py", "screen", "--family", "G", "--run-id", "h2_main", "--n-boot", "2000"],
 "timeout_s": 5400, "max_retries": 1, "outputs": ["research_lab/creative_batch5/G_screen/results.json", "trials.jsonl (2 cb5_test + count line + placebos + descriptive)"],
 "next_action": "if advanced or carried: commit q0111/q0112", "notes": "commit after the freeze; exits 0 'not testable' if G56 or a pre-freeze gate failed; labels 'beyond budget', L1"}
```
```json
{"id": "q0109_cb5_screen_L_dev", "title": "CB5-L: dev screen (L1 at c' touches; coherence placebo; family-level divergence gate; depth; persistence and pair-hours reported)",
 "family": "creative_batch_5", "priority": 38, "expected_value": "whether CH59 advances to the replication captures",
 "data": ["cb5_extract/cdf (frozen dev capture list + sha256)", "book_sweeps (depth check)", "rinc.json", "model_specs/cb5_v1.json"], "resources": {"mem_mb": 1000, "cpu": 1, "lane": "cpu"},
 "depends_on": ["q0106_cb5_census", "q0107_cb5_rinc"], "argv": ["scripts/run_cb5.py", "screen", "--family", "L", "--window", "dev", "--n-boot", "2000"],
 "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch5/L_dev/results.json", "trials.jsonl (1 cb5_test + count line + placebo + descriptive)"],
 "next_action": "if advanced: commit q0113", "notes": "commit after the freeze AND after CB1-D's replication results (or recorded stop) are committed, never before 2026-11-09; exits 0 'not testable' if G59, the coherence placebo or r_inc (unknown) blocks"}
```
```json
{"id": "q0110_cb5_measure_K", "title": "CB5-K: hour-of-day moderation of the Kalshi lead on the C1 pairs (K1; pseudo-split calibration; activity matching; within-pair contrast; J4 label)",
 "family": "creative_batch_5", "priority": 39, "expected_value": "a conditioning fact for Kalshi-anchored designs",
 "data": ["cross_venue/series/*.npz + matches.json (C1)", "creative_batch5/census.json", "model_specs/cb5_v1.json"], "resources": {"mem_mb": 1000, "cpu": 1, "lane": "cpu"},
 "depends_on": ["q0106_cb5_census"], "argv": ["scripts/run_cb5.py", "measure-K", "--n-boot", "4000"],
 "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch5/K/results.json", "trials.jsonl (1 cb5_measurement + count line + placebo + descriptive)"],
 "next_action": "ledger; adoption note for the next Kalshi-anchored registration", "notes": "commit after the freeze; refuses cross_venue_live/; labelled 'unreplicated measurement'"}
```
```json
{"id": "q0111_cb5_rep_G_fetch", "title": "CB5-G: replication-cohort fetch (listings created in [T5_rep_start, T5_rep_start+21d); prices [L-1h, L+4d+1h], trades; each at L+4d+2h)",
 "family": "creative_batch_5", "priority": 41, "expected_value": "post-freeze day-0..3 data for the CH56 replication",
 "data": ["cb5_extract/listings (>= T5_rep_start)", "public CLOB prices-history", "public Data API trades"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu", "network": "clob, data-api"},
 "depends_on": ["q0108_cb5_screen_G"], "argv": ["scripts/run_cb5.py", "rep-fetch", "--family", "G", "--max-markets", "5000", "--seed", "arepo-cb5-rep", "--rps", "4", "--disk-cap-gb", "0.10"],
 "timeout_s": 3600, "max_retries": 3, "repeat": {"max_runs": 120, "until_log_regex": "rep_fetch_complete"},
 "outputs": ["research_lab/creative_batch5/rep_cohort/{prices/,trades/,manifest.json}"], "next_action": "q0112 after T5_G_read",
 "notes": "commit only if G advanced or G2 was carried; rolling (one run per 6h); no target computed by the fetcher"}
```
```json
{"id": "q0112_cb5_rep_G", "title": "CB5-G: Stage-2 replication on the post-freeze listing cohort (G-v recheck first; advanced/carried G tests; Holm over the CB5 route Stage-2 set)",
 "family": "creative_batch_5", "priority": 38, "expected_value": "development replication (L2-dev) of seed-anchor reversion",
 "data": ["creative_batch5/rep_cohort", "cb5_extract/listings", "creative_batch5/G_screen/results.json", "model_specs/cb5_v1.json"], "resources": {"mem_mb": 1200, "cpu": 1, "lane": "cpu"},
 "depends_on": ["q0111_cb5_rep_G_fetch"], "argv": ["scripts/run_cb5.py", "replicate", "--family", "G", "--n-boot", "2000"],
 "timeout_s": 5400, "max_retries": 1, "outputs": ["research_lab/creative_batch5/G_rep/results.json", "trials.jsonl (cb5_replication + count line)"],
 "next_action": "batch Holm with L rep; ledger; Stage P-G registration if passed", "notes": "refuses before T5_G_read; exits 0 'nothing advanced'"}
```
```json
{"id": "q0113_cb5_rep_L", "title": "CB5-L: replication on captures in [T5_rep_start, T5_rep_start+28d) (L1 if advanced; payoff gate read at T5_L_out)",
 "family": "creative_batch_5", "priority": 38, "expected_value": "development replication (L2-dev) of CDF violations persistent at the touch",
 "data": ["cb5_extract/cdf (frozen rep capture list + sha256)", "book_sweeps", "Gamma outcomes (guarded, at T5_L_out)"], "resources": {"mem_mb": 1000, "cpu": 1, "lane": "cpu", "network": "gamma-api"},
 "depends_on": ["q0109_cb5_screen_L_dev"], "argv": ["scripts/run_cb5.py", "replicate", "--family", "L", "--window", "rep", "--n-boot", "2000"],
 "timeout_s": 3600, "max_retries": 2, "outputs": ["research_lab/creative_batch5/L_rep/results.json", "trials.jsonl"],
 "next_action": "batch Holm over the CB5 route Stage-2 set; ledger", "notes": "commit after T5_L_rep_end with the rep capture list; payoff gate after T5_L_out; exits 0 'nothing advanced'"}
```
```json
{"id": "q0114_cb5_K_rep_live", "title": "CB5-K: optional K1-R on E009/E010 live pairs (conditional; after both final analyses are committed and owner sign-off)",
 "family": "creative_batch_5", "priority": 38, "expected_value": "replication of the hour moderation on receipt-timed quotes",
 "data": ["cross_venue_live/ (unsealed, after E009 and E010 final analyses)"], "resources": {"mem_mb": 1000, "cpu": 1, "lane": "cpu"},
 "depends_on": ["q0110_cb5_measure_K"], "argv": ["scripts/run_cb5.py", "measure-K", "--live-replication", "--n-boot", "4000"],
 "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch5/K_rep/results.json", "trials.jsonl (1 cb5_measurement + count line)"],
 "next_action": "ledger", "notes": "DRAFT ONLY: not committed without a ledger sign-off line from the E009/E010 owner; never before 2026-11-03; cannot change any E009/E010 verdict"}
```

## 6. Test budget and compute

| Job | Tests counted | Kind(s) | Family |
|---|---|---|---|
| Routes, Stage 1: G1, G2 (h2), L1 (dev) | 3 | `cb5_test` + count lines `creative_batch_5:G` (`n_tests` 2), `:L` (1) | each gated alone at one-sided p < 0.01; BY triage over the cumulative count |
| Routes, Stage 2 (advanced or carried only) | ≤ 3 | `cb5_replication` + count lines | one Holm, one-sided α = 0.05, k ≤ 3 |
| Measurement K1 | 1 | `cb5_measurement` + count line `creative_batch_5:K` | **K**: two-sided α = 0.05, k = 1; never in the route Holm |
| Optional K1-R | ≤ 1 | `cb5_measurement` | own family, k = 1, only with sign-off |
| Census, seed strata, incidence, persistence, r_inc, J4 counts, sports strata, gates | 0 | `cb5_descriptive` | - |
| **Total** | **4 fixed + up to 4 conditional = 4-8** | | adds to the cumulative count (1,104 at the round-1 response) |

**Host compute.**
- About 3-5 CPU-hours at nice 19 in total (extractor backfills are the largest). Peak memory 1.5 GB (frame, census).
  The five network jobs use the `net` lane (q0002 is done); no two multi-GB jobs run at once.
- Network: head refetch about 6.4k requests (30-45 min); census cohort 6-10k (< 1 h); frame walk a few hundred pages;
  r_inc a few hundred metadata requests; replication cohort about 10k over three weeks. All at ≤ 4 rps with the shared
  limiter and collector yield.
- Disk: CB5 outputs ≤ 0.3 GB in total; the IF-H2 scratch copy is deleted after q0104/q0107; release streams peak at
  ≤ 0.2 GB.

## 7. Main scientific risks

1. **Seed semantics (G).** The decisive unknown. Prior evidence says `prices-history` mostly starts at the first trade,
   and untraded points cluster at 0.5. If the valid-seed share is small, G56 fails. If pre-trade points are not the
   book quote, G-v stops CB5-G. Both are designed to stop the work rather than test a placeholder.
2. **Generic reversal vs anchoring (G).** First-day prices may revert toward the cross-section, or toward 0.5, whatever
   the seed. The seed-permutation placebo, the 0.50-seed attribution rule and the level-controlled slope separate them;
   they may leave "reversion exists, not attributable to the seed".
3. **h2 wear and CB1-E (G).** h2 is beyond budget. CB1-E reads the same windows and may run first. Stage 1 is L1 at
   most, and the only meaningful evidence is the prospective Stage 2, whose prices are modelled (taker exit at
   `p ± h_gen`, maker fills from trade-throughs).
4. **Early-book economics (G2).** Thin day-1 books, the 2.5c genesis half-spread and the taker exit make G2 likely to
   fail. Even a pass needs Stage P with targeted sweeps before any economic statement.
5. **Grouper errors (L).** Different resolution sources, time zones, or "announce" vs "happen" wording turn a
   "riskless" pair into a directional bet. The text-only audit gate, the conservative divergence gate (`r_inc⁺` costed
   as full loss) and the realised-payoff gate guard this. Payoff checks will often be "unverified" because deadlines
   are months away.
6. **Rarity and fees (L).** Families may be fewer than 20. `K_D + 1` taker legs make the fee wall high outside zero-fee
   categories. The maker route is untestable at 2h cadence.
7. **Power and proxy (K).** MDE ≈ 0.27 on C1 (recomputed in round 1), about the whole lead. Hour is a proxy for flow composition, the data are worn,
   the J4 check is from another period, and the Polymarket stamp convention is ambiguous. Most outcomes will read "not
   detected at MDE".
8. **Calendar and queue (all).** CB5-G's screen waits for CB4's cost register (q0089), which waits for pmxt jobs behind
   q0002 on the `net` lane. The L dev window ends 2026-10-27, and the replications end late November (G) and early
   December (L), with L payoffs in January 2027.
9. **Retention.** Dev captures from 2026-10-11 become deletable around 2026-10-18. CB5 relies on CB4's release-stream
   reader. A capture missing from releases is lost for `listings` and `cdf` (counted, never reconstructed).
10. **Disk headroom.** Snapshot deletion is gated (`RETENTION.md`), and the host grows about 0.75 GB a day while it is.
    The §2.8 release-time precondition can hold CB5's data jobs until deletion is active.
11. **CB1-D overlap (L).** The L dev screen is held until CB1-D's replication read (§CB5-L), which moves it to mid
    November at the earliest.

## 8. Next actions

1. Challenger round 1 is done and answered (§9). Next: the freeze check of the CB5 code (`science-reviewer`), then the
   freeze after the census.
2. Coordinator: add CB5 to the `RETENTION.md` reader list (§2.9; no new gate). Check the §2.8 disk precondition before
   committing q0101.
3. Delegate to `implementer`: extractor v4 tables (`listings`, `cdf`, `--release-stream` reuse), `cb5_seed.py`,
   `cb5_cdf.py`, `cb5_hours.py`, `run_cb5.py`, `KIND_RULES`, tests (§4). Commit the CDF grouper hash before q0104 reads
   text.
4. Commit and run q0101 at once after the code passes its freeze check (dev captures are deletable from about 10-18;
   release streaming covers any loss). Restore IF-H2 `events.jsonl.gz` (Claude session, §2.8), then q0104, the text
   audit, `cdf-audit-apply`, q0105, q0107. Run q0102 any time.
5. After `T5_dev_end`: q0103, then the q0106 census. Insert counts and gates here, then freeze
   (`model_specs/cb5_v1.json`) and pin `T5_rep_start`.
6. Then q0110 (K1). q0109 (L dev) only after CB1-D's replication read (§CB5-L hold, not before 2026-11-09). Run q0108
   (G screen) once CB4's register is committed. Commit q0111/q0112 and
   q0113 only for advanced or carried tests. q0114 only with E009/E010 owner sign-off after 2026-11-03.

**Open questions put to the challenger in round 1** (kept for the record; answers and changes in §9).
1. Queue prefixes: should CB5 or CB4's drafts move? (Answered: CB5 moved to q0101-q0114.)
2. G Stage 1 on worn `h2_main` versus using the live census cohort (listings 10-11..10-26) as the screen. The census
   cohort is unworn but small and calendar-bound; h2 is larger but beyond budget and overlaps CB1-E.
3. The G-v thresholds (≥ 50 checkable, ≥ 75% agreement within 1c) and the first-trade-echo stop at 50%: are they
   strict enough, or too strict?
4. The G2 carry rule (an untested-at-Stage-1 economic test entering the Stage-2 Holm when G1 advances): acceptable, or
   should G2 wait for its own registration?
5. The seed-permutation placebo as a hard calibration gate: is it the right falsifier, or will it reject true anchoring
   whenever generic reversal coexists (the level-controlled slope is the alternative)?
6. CDF grouper: is the Jaccard ≥ 0.6 + numbers + conflict-word + source rule adequate given the 56/167 live
   cross-venue mispairing? Is costing every inconsistent resolution as a full loss (`r_inc⁺`) the right gate?
7. Reading historical family outcomes (q0107) before the freeze to set a binding gate: acceptable, given it never
   touches prices or live families?
8. K bucket deviation (R = 09:30-23:00 New York, O = overnight, versus the idea's 13:30-20:00) and non-sports primary:
   accepted? Is K1 worth running at MDE ≈ 0.24, or should it wait for the receipt-timed live data only (K1-R)?
9. K1-R on E009/E010 data after their analyses: is a pre-declared secondary on unsealed live data acceptable to the
   E009/E010 governance?

## 9. Challenger round 1 (2026-10-16) and response

Verdicts: G ACCEPT_WITH_CHANGES, L REVISE, K ACCEPT_WITH_CHANGES, F ACCEPT_WITH_CHANGES. This is the single response
round (mission §6). Every change makes the design stricter or more honest; no threshold, floor or α was relaxed. The
one rule that can now credit a case the draft would have rejected (item 5, G attribution) replaces a falsifier that
rejected true anchoring whenever level reversion existed, and it adds a level-controlled requirement in its place.

| # | Item | Change made | Why (one line) | Where |
|---|---|---|---|---|
| 1 | L1 direction placebo cannot fail (`net_A + net_B < 0` always) | Replaced by the **mismatched-family coherence placebo** (same granularity, same boundary day; matched pairs must be more coherent than ≥ 98.5% of draws; < 20 families with a mismatch → not testable, blocks). The literal "same L1 statistic on mismatched pairs" is kept only as a reported contrast, because unrelated prices give large persistent touch gaps and it would advance almost always. The lag placebo (trigger c − 1, execute c) is **declined**: it has the primary's own alignment and reproduces it | a calibration must be able to fail under the alternative it guards against (grouper pairs unrelated questions) | §2.6, §CB5-L gates, §4.1, §4.4 |
| 2 | `r_inc` gate: Wilson at 0/30 ≈ 11.3c; < 30 units swapped to a gate expected to be inconclusive, so less data was easier | `r_inc` and `r_inc⁺` at **family level** (n = families); unknown (< 30 families) **blocks** the advance; minimum passable n stated (61 families for 6c, 93 for 4c, 189 for 2c, 292 for 1.3c); any inconclusive payoff or depth gate blocks crediting ("pending, not credited"; one re-read, final by 2027-06-30) | missing evidence must never be easier than adverse evidence; nested (f, D) units are not independent | §2.6 (vii), §2.7 L-v, §CB5-L gates and verdict map |
| 3 | K1 hour-shift placebo: one +12h shift; 200 circular shifts impossible on 144 steps; small shifts measure power | **Pseudo-split calibration**: within one bucket, random (pair, date, half-hour) blocks split at the O : R ratio, 200 splits in R + 200 in O, pooled two-sided rejection ≤ 6.5%; +12h kept as a single reported contrast | a size check needs a null with no hour contrast and the real dependence structure | §2.6, §CB5-K adoption, §4.1, §4.4 |
| 4 | Queue ids clash with CB4's q0084-q0093 | CB5 moved to **q0101-q0114**, one id per job, no suffixes; mapping table | unambiguous provenance in `queue/` and `trials.jsonl` | header, §0, §0.1, §5 |
| 5 | G seed-permutation placebo kills real anchoring when level reversion exists | Placebo runs on the **level-controlled slope `β^LC`** (raw-slope placebo reported). `β^LC` is not identified in the 0.50 stratum (`d` collinear with the level terms), so the 0.50 stratum now estimates level reversion where no anchor exists, and the residual informative slope must keep ≥ half the raw slope (no extrapolation outside the stratum's `VWAP₁` range); raw comparison reported | the falsifier must separate own-seed anchoring from level reversion, not conflate them | §2.6, §CB5-G attribution, §4.1, §4.4 |
| 6 | h2 drawn by status × fee_category × created month; status is post-listing | Unweighted h2 estimate labelled as describing the sample; **stratum-fixed-effect G1 slope must agree in sign** (binding at Stage 1); design-weighted slope reported if recoverable | conditioning on post-listing status can bias the slope; the adjustment is cheap | §CB5-G population, §2.6 (ix), §4.1 |
| 7 | `end_at` and neg-risk member count as of `T_h2_clock` in h2 | Replication: taken at first sighting in `listings/`. h2: disclosed look-ahead | population rules must use information available at listing | §CB5-G population |
| 8 | Census read window contradicted by G-vi/G-vii | Two declared guarded exceptions on h2: G-vi reads the feature window `[L, L + 24h)` only; G-vii uses a **count-only accessor**; test that no census path sees a target-window price | the guard must match what the code actually reads | §2.7, §4.1 |
| 9 | G-v validates seed semantics only for Oct 2026 listings | Every h2 Stage-1 result labelled **"seed semantics unverified for era"**; G1 by listing quarter reported | a check on one era cannot certify another | §2.7 G-v |
| 10 | L leg timing; `cdf` rows lack leg sizes | Legs' `received_utc` spread ≤ 5 min, else ineligible (counted; at c' → net 0); wording changed to **"persistent at touch"**; executability only on the depth subset | non-simultaneous legs are not one pair; touches without sizes are not executable fills | §0, §CB5-L question, definitions, verdict map, §4.4 |
| 11 | L/CB1-D overlap: `Σ ask` over `B_D` at `K_D = N − 1` ≈ CB1-D's sealed statistic before 2026-11-09 | **q0109 held** (not committed, nothing computed) until CB1-D's replication results or recorded stop, never before `T_CB1D_rep`; census computes no bucket sum; runner refusal | CB5 must not read a near-copy of a sealed statistic inside its seal | §1.2, §CB5-L gates, §4.2, §5, §7, §8 |
| 12 | K MDE used v1 figures | Recomputed on C1 (SE ≈ 0.036, 149/316 sports): **MDE ≈ 0.25-0.28, working 0.27**; census K-i recomputes from actual counts | the stated MDE must describe the data actually tested | §CB5-K MDE, §2.7 K-i, §7 |
| 13 | K pooled statistic mixes pairs | **Binding within-pair (pair-equal-weight) contrast**, same sign and ≥ half; event-FE version reported | a between-pair composition difference must not create K1 | §2.6 (viii), §CB5-K |
| 14 | C1 hand drops surfaced via the outcome-disagreement list | Disclosed; K1 with the 4 pairs re-added reported if identifiable | C1 is not fully outcome-blind | §CB5-K data |
| 15 | Disk guard close (8.8 GB, +0.75 GB/day while deletion is gated) | **Release-time headroom precondition** (deletion active, or projected size ≤ 12 GB with ≥ 3 GB free), recorded in the commit; otherwise the job is held | avoid hitting the cap mid-job without touching retention | §2.8, §7, §8 |
| 16 | Test count 1,080 is stale | Recomputed `battery2.cumulative_count()` = **1,104** (325 `flow_screen` lines) | the denominator recorded must be the current one | §2.5, §6 |

Open questions 2-4 and 6-9 of §8 were not raised as must-fix or should-fix items; the draft's answers stand (h2 stays
the Stage-1 screen with the L1 ceiling; G-v thresholds unchanged; the G2 carry rule unchanged; the grouper audit and
historical-only outcome read unchanged; K buckets, non-sports primary and the K1-R conditions unchanged). Question 5 is
answered by item 5.

## 10. Implementation notes (2026-10-17; code committed, not frozen; freeze-check fixes A1-A5 and B1-B10 applied, awaiting the re-check)

**What exists** (all under `backend/`; tests `backend/tests/unit/test_cb5_*.py`, 98 tests, all green together with the CB1/CB2/battery2 tests):

| File | Content |
|---|---|
| `astrolabe/research_lab/cb5_extract.py` | `listings/` and `cdf/` extractor tables, own root `data-dumps/research_lab/cb5_extract/`, own manifest, lock and version `cb5-extract-v1`; release-stream via `cb4_data.ReleaseCopies`; headroom refusal; `_chain/prev_ids.csv.gz` carries the previous capture's listing so a first sighting is certain (`first_seen_certain` 0 when the chain is broken); `cdf` rows only for families whose `listed_utc` precedes the capture |
| `astrolabe/research_lab/cb5_seed.py` | G: seed, units, G1 (raw, `beta^LC`, stratum-adjusted), seed-permutation placebo, 0.50-stratum rule, G2 orders, break-even placebo, carry rule, era rule, truncation worst cases, census functions (`trim_census`, `window_count`, G-ii..G-vii) |
| `astrolabe/research_lab/cb5_cdf.py` | L: parse guard, period table, tiling, rungs, bucket events, matching, pairs, audit, family list, pair state, triggers, execution, coherence placebo, `r_inc`, gates, credit status |
| `astrolabe/research_lab/cb5_hours.py` | K: buckets, per-step sufficient statistics, K1 bootstraps, pseudo-split calibration, activity matching, within-pair contrast, J4, census, refusal of `cross_venue_live/` |
| `astrolabe/research_lab/cb5_fetch.py` | head-price refetch, census/replication cohort fetch (parse guard, wallet hashes blanked), guarded YES-payout fetch |
| `astrolabe/research_lab/cb5_run.py` | orchestration: census, screens, replications, measurement, frame, audit, `r_inc`, trials logging |
| `astrolabe/research_lab/cb5_declaration.py` | the declaration hash, spec, grouper seal, windows and guards |
| `scripts/run_cb5.py` | CLI: `extract, head-fetch, cohort-fetch, rep-fetch, cdf-frame, cdf-audit-apply, census, rinc, screen, measure-K, replicate, fetch-outcomes, write-grouper-seal, write-spec, pin-rep-start` |
| `astrolabe/research_lab/battery2.py` | `KIND_RULES`: `cb5_test`, `cb5_replication`, `cb5_measurement`, `cb5_descriptive` (EXCLUDE; the count lines carry the tests; the counter runs on the real `trials.jsonl`, 1,104 unchanged) |
| `docs/research_lab/queue/drafts/q0101..q0114_*.json` | the 14 drafts (not in `jobs/`) |

**Deviations from sections 4.1-4.3 (all stricter or neutral; the coordinator should accept them at the freeze check).**
- The extractor is a separate module and version (`cb5-extract-v1`), not `creative_batch1.py` `cb1-extract-v4`. `creative_batch1.py`, its version (`cb1-extract-v2`) and every CB1-CB4 table are untouched (a test asserts it). The pass step is `run_cb5.py extract`.
- Declaration (`cb5_declaration.py`): the hash covers the source of every function and class of the five CB5 modules, the imported rule functions (cost model, cluster statistics, `if_h2` deadline and stem, `cross_venue` tokenizer, CB4 release reader) **and every UPPER_CASE module constant read at call time**, so a changed threshold, seed, word list or window changes the hash even where no function changed. The grouper hash is sealed separately (`write-grouper-seal` -> `docs/research_lab/seals/cb5_grouper_hash.json`); `cdf-frame` refuses until it is committed and equal to the code's.
- `rinc` (q0107) is a pre-freeze job: no declaration guard (a guard would be circular, the freeze needs its result). It refuses until the family list is frozen and the r_inc functions are sealed (see 4.2). `write-spec` binds `census.json` and `rinc.json` by sha256 into `model_specs/cb5_v1.json`, and every counted run re-verifies both (`verify_inputs_bound`).
- A trigger at the last capture of a window has no c' (the sample ends); it is censored, not counted as a net-0 trade. A gap outside [1.5, 3] h or an ineligible c' stays net 0, kept.
- h2 has no neg-risk member count, so every h2 neg-risk market is excluded from G (conservative; the replication cohort uses the first-sighting member count).
- The G-iv determinism overlap is restricted to the census window (stamps up to `min(first trade + 1h, L + 24h)`), so the census never compares target-window price values.
- Source rule (d): both sides name sources -> must intersect; neither names one -> pass and flag `source_unknown` (IF-H2 records carry no descriptions, so historical families are all `source_unknown`); one side only -> exclude.

**Declaration hash (code at the commit that applies freeze re-check must-fixes 1-6; recomputed by `cb5_declaration.declaration_sha256()`):**
`42bde44f715f6025f986b6ef7c0035cb9730b329ec502d6c79ec42e97f898ede`. Grouper hash: `aaac0948ba1ccb209066ae3c22133aec30cc5cde77719cab9af6410bb872084b`. r_inc functions hash (sealed with the grouper): `8f51ef36e4c3c38fd082b37a332f0023f66dac4f9da22cb1a9ffd27fa9fd2fb4`. Any further code change moves them; re-read them at the freeze commit. The hash covers `cb5_run`, `cb5_fetch`, the imported rule functions (now also `cross_venue.boot_stat`, `cb1_history.load_sample` and `norm_rec`, `creative_batch1.sweep_index`, `forecast.list_complete_captures`, and the script functions `run_cross_venue.load_pair_series` and `audit_sets` executed by `cb5_hours.c1_pairs`) and the imported constants `cross_venue.POINT_LAG_S`, `if_h2.DATE_RE`, `if_h2.EXCLUDE_TAGS`, `cost_regimes.FEE_ERAS`, `ERA_BUFFER_D`, `ERA_RULE_POST`. **Operational constants** `JOB_REFUSE_GB` (12), `DATA_DUMPS_MAX_GB` (14), `DEFAULT_BUDGET_S` and `SCRATCH_CAP_GB` of `cb5_extract` are excluded from the hash (`OPERATIONAL_CONSTANTS`): headroom is an operational precondition, tuned at run time, and cannot change any result. The r_inc seal now also covers `fetch_yes_payouts`, `rinc_market_ids` (the historical-id selection) and `OUTCOME_FAILED`.

**Freeze re-check must-fixes (this commit).** (1) hash coverage gaps closed as listed above. (2) operational constants out of the hash; headroom 12 GB because the collector cap is 13 GB and snapshot deletion is active. (3) Unfinished code: the K1-R stub moved to `cb5_reported.py`, **excluded from the hash with its own note** (`NOTE`); it will be sealed with its own spec before q0114 runs (q0114 stays a draft). The reported-only variants (open item 2) are **formally dropped from this declaration**: none is implemented, none will be reported as a CB5 result, and any later analysis of one is a new, labelled exploratory item outside CB5's tests and trials. (4a) `fetch_yes_payouts` records a non-200 or transport failure as `failed` (`OUTCOME_FAILED`, -1.0), distinct from `unresolved` (NaN); `r_inc` returns `blocked_fetch_failed` when any leg failed; `rinc` and `fetch-outcomes` write nothing and exit 3 on a failure, so a failed run never blocks the single-shot rerun; a mocked-session test fixes the batch format (repeated `id` params, 40 per call). (4b) the sealed r_inc set includes `fetch_yes_payouts` and the id selection. (5) the L screen asserts the frozen family list sha256 equals `census["L"]["family_list_sha256"]` and `rinc["family_list_sha256"]`. (6) a non-200 (400, 404, 422) in the frame walk counts as a failed window and `cdf-frame` refuses while any exists.

**Process deviation (disclosed).** q0101 was promoted (f05629f, 2026-10-17 01:09Z) before snapshot deletion was active (04:39Z), contrary to the section 2.8 precondition's order. No result is affected (the job writes only the `listings` table, idempotent, and tempfailed on the headroom guard until the raise to 12 GB).

**Disclosed open items carried to the freeze.** Open items 4 (IF-H2 lacks `negRiskAugmented`, `conditionId`, descriptions), 6 (timing is synthetic) and 7 (no CB5 quantity computed on real data) stand, as does B9 (shared CB4 test helpers stay in `test_cb4_data.py`). The K-iii J4 count (`cb5_hours.j4_wide_by_hour`) has **no release-copy fallback**: a deleted capture appears as `n_missing_raw` and is not recovered from release copies.

**Freeze-check fix status.**
- A1 done: a missing capture no longer resets the listings chain (retries each pass cannot make later captures `first_seen_certain = 0`; adjacency detects a missing predecessor). A2 done: `neg_risk_n_members_at_sighting` (counted over the full capture) and `sweep_batch_receipt_utc` are stored; the replication cohort reads the stored count (no look-ahead). A3 done: q0101 and q0105 pass `--retry-missing`. A4 done: exit 75 (`EX_TEMPFAIL`) on a headroom refusal; the queue worker waits 30 min without counting an attempt (cap 48). A5 done: pass step uses `--data-dumps-max-gb` (10 at drafting, 12 since 2026-10-17: see section 2.8).
- B1 done (hash scope). B2 = A2. B3 done: an absent or unknown G-ii, G-vi or G-v stops as `census_incomplete`; an absent G-v adds the label "G-v absent: seed semantics unverified". B4 done: `assert_census_frame` on every census input frame (h2 sample after dropping forbidden columns, listings, cdf rows). B5 done: historical = every leg closed with a known close time before `T5_dev_start` (bucket members now carry `closed_time`). B6 done (seal, `rinc` refusal, `write-spec` and `verify_inputs_bound`). B7 done: mismatches with no eligible series are dropped up front, so `M_matched` and every draw use the same pairs. B8 done (lanes; section 2.8 amended). B9 not done (the shared CB4 test helpers stay in `test_cb4_data.py`). B10 done (no change; constants out of the hash).

**Pass-step line (do not edit `scripts/oracle/arepo_pass.sh` from this branch; the owner adds it after the line for CB4, line 32):**
```
  timeout 600 nice -n 10 $PY scripts/run_cb5.py extract --all-new --tables listings --data-dumps-max-gb 12 2>&1 | tail -1 || true   # CB5 listings (CREATIVE_BATCH_5.md §4.3)
```
After the family list is frozen and q0105 has run, extend it to `--tables listings,cdf --family-list auto` (the `cdf` table is skipped with a note while no list is frozen). The run is idempotent by (capture_id, table), writes only under `cb5_extract/`, and exits 75 (EX_TEMPFAIL) only on a headroom refusal (the `|| true` keeps the pass alive). A capture whose raw files are gone is recorded `missing` and retried on every all-new pass (a missing capture never resets the listings chain; the next capture's `first_seen_certain` is 0 only because its predecessor is the missing one). q0101 and q0105 pass `--retry-missing` so host captures marked missing by a pass are retried from release copies.

**Queue notes.** Network-bound jobs (q0102, q0103, q0104, q0107, q0111) use lane `net` (q0002 is done and no longer holds it; section 2.8 amended). Data jobs and the pass step pass `--data-dumps-max-gb 12` (size + allowance + scratch must stay under 12 GB; the collector cap is 13 GB); a refusal exits 75, which the queue worker treats as wait-30-min-and-retry (not an attempt; at most 48 in a row). `done` for q0101/q0105 requires `backfill_complete` in the log. `mem_mb`: 400-1,500 (q0104 and q0106 at 1,500, the streamed frame parse and the census).

**Open items for the freeze check (not implemented or unverified; none changes a declared threshold).**
1. K1-R (q0114): the live-pair loader and the receipt-timed 2-minute grid mapping are not implemented; the stub lives in `cb5_reported.py`, outside the declaration hash (the runner refuses first, then stops).
2. Reported-only variants (formally dropped from this declaration, see the re-check paragraph above; not implemented): G sign by month/category, +1c cost, hold-to-resolution (G2), design-weighted slope, the fidelity-1 seed variant (stored, not analysed); L tier sensitivity, maker-leg and conversion-adjusted capital variants; K market-hours split, K by Kalshi-volume tercile, K with the 4 hand-dropped pairs re-added, the Polymarket flat-step share by bucket (K-ii). The binding items are implemented.
3. `fetch_yes_payouts` batches Gamma `/markets?id=...` (repeated `id` parameter, 40 per call); not exercised against the live API. A wrong batch format would read as "unresolved" (NaN), which can only make `r_inc` unknown, never easier.
4. The IF-H2 `events.jsonl.gz` has no `negRiskAugmented`, `conditionId` or descriptions: historical bucket events are treated as not augmented (unflagged) and `source_unknown`. The audit gate (L-ii) is the guard.
5. The `rinc` pre-freeze status (see 4.2: sealed functions, committed seal, `rinc.json` bound by hash) should be confirmed by the reviewer.
6. Timing (synthetic C1-sized table, 510k steps, 170 pairs): step table 5 s, K1 with 4,000 draws 1.2 s, 400 pseudo-split tests about 3 minutes, within-pair 1 s; q0110's 3,600 s limit is ample.
7. No CB5 quantity has been computed on real data; all numbers in the tests come from synthetic fixtures.
