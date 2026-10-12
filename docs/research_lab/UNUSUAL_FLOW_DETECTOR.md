# Unusual-flow detector: frozen variants (final set of 5, 2026-10-12)

**Status:** frozen rule specifications for the held-out and broad-sample evaluations described in
`UNUSUAL_FLOW_PROGRAMME.md`. Nothing here is a result. `evidence_role: exploratory_historical` applies to
every evaluation of these rules until a registered live test exists. No wallet, trade or market is, or will
be, labelled as insider activity; the rules describe public, hashed taker-flow patterns only.

Specs live in `backend/astrolabe/research_lab/detector_specs/` (`<rule_id>.json`, index `FROZEN.json`).
`detector_eval.HeldOutHarness` refuses anything not listed below with exactly these hashes, any
`engine_version` other than `detector-eval-v1`, and any run without a valid `evidence_role`.

## Batch 1: frozen variants (slots 1-3)

Freeze commit `492efd6` (design + engine), `frozen_utc` 2026-10-12T00:59:28Z. Score = sum of
`weight * clip((transform(x) - center) / scale, -cap, cap)` over present terms, `cap = 4`; higher = more
unusual; alert direction = sign of `imb_s` (+1 outcome 0, -1 outcome 1). Canonical feature names and the
history/live mapping are in `detector_eval.normalise_panel` (`detector-panel-map-v1`).

| rule_id | sha256 | Mechanism | Conditions | Terms (feature, transform, center, scale, weight) |
|---|---|---|---|---|
| `uf_imbalance_burst_v1` | `34ae5f40440e50124e63f4aa6989d7fcf154b78f6ba49b51fcd9c26f97d90acd` | One-sided taker pressure arriving faster than the market's own long-window pace; flow only | `n_s >= 3` | `imb_s` abs 0.4 0.3 1.0; `burst` log1p ln2 0.5 1.0; min present 2 |
| `uf_new_wallet_concentration_v1` | `c13c0cd5ed65b27cb0bb999cd6ecd855fb923089d77e5106996f923b464339f7` | Fresh (new-to-sample) and concentrated (top-1 share) participation on one side | `n_s >= 3`, `n_wallets_l >= 2` | `new_wallet_share_l` raw 0.15 0.15 1.0; `top1_share_l` raw 0.35 0.2 1.0; `imb_s` abs 0.4 0.3 1.0; min present 3 |
| `uf_large_trade_v1` | `99b47270b24cdcdcb8cf174fa1d21e10d4fc97dcaa6a193664b072b7fedda464` | A single short-window print far larger than the long-window mean trade size, on one side | `n_s >= 1` | `large_trade_rel` log1p ln4 0.7 1.0; `imb_s` abs 0.4 0.3 0.5; min present 2 |

`theory_ref` for all three is `programme_prelisted` (feature register IDs F01/F07/F11, F03/F04/F05,
F02/F12). **Centres and scales are a priori feature-range values**, chosen from the feature definitions
(`flow_features.py`, `history_backfill._trade_flow`), not estimated from Maduro or discovery-half data,
because neither panel existed at freeze time. This is weaker than the programme design intends; the alert
budget (top 1%) makes ranking, not absolute scale, decisive. Re-centring with tuning data would be a new
`rule_id`/version and spends one of the remaining slots.

## Batch 2: theory-derived variants (slots 4-5)

Source: `INFORMED_FLOW_SIGNAL_THEORY.md` (de76b8d) section 4, hand-off paragraph: the two most distinct
theory variants that map onto the market-level 2h canonical panel, each needing one derived column at `t`.
Both are computable from historical data now (Data API trades for `imb_s`, `large_trade_rel`,
`top1_share_l`; prices-history for `mid` and the 2h lag `ml_own_dmid_prev`). Frozen `frozen_utc`
2026-10-12T01:18:28Z against `2ada424`; the engine support (`detector_eval.add_derived`, canonical columns
`mid_change_s`, `p_acq`, `resp_s`) lands in the same commit as these specs. No judgement-half or catalogue
outcome had been read or committed when they were frozen.

Derived columns (`add_derived`, point in time): `p_acq = mid if imb_s > 0 else 1 - mid` (NaN when the
flow is balanced or unknown); `resp_s = sign(imb_s) * mid_change_s`, with `mid_change_s = mid(t) - mid(t-2h)`
historically (`ml_own_dmid_prev`) and Gamma `chg_1h` live (shorter lag; recorded by the panel map).

| rule_id | sha256 | Mechanism (theory ref) | Conditions | Terms (feature, transform, center, scale, weight) |
|---|---|---|---|---|
| `uf_convex_longshot_v1` | `1230c0d14dab05a4ac8e0c60d4522ab99f8e14cf006adb83b5714f971f91f226` | Convex longshot pressure: one-sided flow acquiring an outcome priced ≤ 0.20, large print, concentrated participation (s3.1 `ifx_convex_stake`, IFC1 gate) | `n_s >= 3`, `p_acq <= 0.20` | `imb_s` abs 0.4 0.3 1.0; `large_trade_rel` log1p ln4 0.7 1.0; `top1_share_l` raw 0.35 0.2 1.0; min present 3 |
| `uf_pressure_no_response_v1` | `14f234d7be348af2605de4288b32cfdaa598acd6212c5d65bdc361508296d183` | Pressure without price response: concentrated one-sided flow whose short-window price change in the flow's direction is small or negative (s3.10 `ifx_stealth`, IFC2) | `n_s >= 3` | `imb_s` abs 0.4 0.3 1.0; `top1_share_l` raw 0.35 0.2 1.0; `resp_s` raw 0.0 0.05 **-1.0**; min present 3 |

The theory doc's IFC1 identity gate (`ifx_fresh`, `ifx_focus`: true wallet age, prior trade count, focus
share) and `ifx_aggression` (book depth consumed) are **not** in these specs: the canonical panel carries no
true wallet age or depth, and `new_wallet_share_l` is left-censored at sample start. They remain the live
registration's candidates once `/activity` first-trade lookups run at collection time (programme doc section 7).
Centres and scales are a priori feature-range values, as in batch 1, for the same reason.

## FINAL FREEZE

**FINAL FREEZE: 5 variants, commit `692ab61`.** The set is closed: `FROZEN.json` holds exactly
the five `rule_id`s above with the hashes shown; the shipped-registry test asserts the count and the hashes. Any
further rule is a new data window's budget, not an addition to this set. Holm runs across these five on the
primary statistic.

## Declared evaluation (fixed before any run)

- Primary statistic: matched-control excess directional precision at budget, `EvalConfig(budget=0.01,
  horizon_h=24, delta=0.10, cooloff_s=86400, k_controls=5, n_boot=1000, n_placebo=200, seed=116)`;
  one-sided clustered bootstrap p of `mean(d_i) > 0`, cluster = event id. Holm across the frozen set.
- Secondary (descriptive): h = 6, δ = 0.05; random-budget placebo rank; recall on large moves; lead time;
  paper P&L (`shares = 5`, `fee_policy = max_if_unknown`, spread from the panel or 0.02 assumed and counted).
- Not testable below 30 alert episodes or 10 clusters with an alert; reported as such, never as a pass.
- Discovery cut (broad sample row-time median): **to be written here by the Maduro agent before any
  judgement-half metric is produced** (`discovery_cut_epoch = 1785391200` = 2026-07-30T06:00:00Z; written 2026-10-12 before any judgement-half metric. Broad panel: `history/h2_main` `build_panel` outputs (2h grid, horizons 2/6/24) restricted to the seeded sub-sample `bsample` (1,500 of 3,200 markets, seed `arepo-unusual-flow-b1`, `draw_sample` by status x fee_category x created month), Maduro/Venezuela markets (2,316 condition ids from the Gamma search) and catalogue condition ids removed; 1,005 markets with rows, 327,766 rows (163,845 discovery / 163,921 judgement); cut = median `t` over all rows before the `traded_before_t` filter. File `data-dumps/research_lab/event_study/broad_panel.csv.gz` + manifest.)
- Case-list hash (`sha256` of sorted catalogue `condition_id`s): **to be written in `CASE_CATALOGUE.md` by the
  catalogue agent before reading this file's variants**; the detector author did not see the case list.
- Budget accounting: 5 detector trials pre-committed (one per variant on the judgement half) plus the
  same 5 in case mode; `prior_detector_trials` in every `trials.jsonl` line carries the cumulative count.

## Live data needed before a registered live test (programme doc section 7)

| Canonical feature | Live status (`flow_features.py` sidecar) | Needed |
|---|---|---|
| `large_trade_rel` | Not available: live has `flow_max_trade_liq_1h` (divides by liquidity, not by mean trade size) | Add largest 1h trade / mean 6h trade size to the live features (collector change, separate admission note) |
| `new_wallets_s` | Not available | Optional; batch-1 rules do not use it |
| `new_wallet_share_l` | `wlt_new_share_6h`, NaN until the first-seen index spans 7 days | Nothing; coverage grows with time |
| `n_wallets_l` | `wlt_n_buy_6h + wlt_n_sell_6h` (wallets with net zero excluded) | Acceptable approximation; record in the admission note |
| `burst` | derived `flow_n_1h / (flow_n_6h / 6)` | Nothing |
| `mid_change_s`, `resp_s` | Gamma `chg_1h` (1h lag; history uses a 2h as-of lag) | Acceptable; or compute a 2h own-history lag from consecutive passes in the collector |
| `p_acq` | derived from `imb_s` and `mid` | Nothing |
| Alert line, matched-control ids at alert time | Not written anywhere | New append-only `alerts.jsonl` written by the pass before any outcome exists |
| `fwd_move_6h/24h` | From complete-universe snapshots | Join step; pending/unavailable/evaluated kept distinct |

`uf_large_trade_v1` and `uf_convex_longshot_v1` therefore cannot be part of a live registration until the
collector change lands; they remain historical-only variants unless that happens.

## Instructions (verbatim summary of programme doc section 8)

- **Maduro agent:** `panel = detector_eval.normalise_panel(build_panel_output, "history")`; drop catalogue
  and Maduro `condition_id`s; write `discovery_cut_epoch` above; then for each `rule_id` in
  `RuleRegistry().frozen_ids()`: `HeldOutHarness().evaluate(rule_id, panel[panel.t >= cut],
  evidence_role="exploratory_historical", dataset="<run_id>", cfg=EvalConfig())`, then
  `holm_across_rules(results)`; report `alerts_needed(control_base_rate, 0.05)` beside the numbers.
- **Catalogue agent:** pin the case-list hash first; build case + quiet-case-control panels with `news_ts`
  on case rows and `control_group` in {`case`, `quiet_move`, `quiet_nomove`}; same harness call with
  `cfg=EvalConfig(case_mode=True)`; precision is refused by design; report recall-before-news, lead time
  and per-group alert rates with the reporting-conditioned caveat.
- Both: yield to `arepo_pass.sh`, ≤ 5 req/s, check swap before `build_panel`; never edit
  `detector_specs/` or this file's hashes.

## Judgement-half results (broad sample, 2026-10-12; exploratory_historical)

Run exactly as programme §8 (d) after FINAL FREEZE (`692ab61`), on `h2_main_bsample_b1:judgement`
(t ≥ 1785391200; 119,346 traded rows, 357 markets, 269 clusters, 44,575 untraded rows excluded).
**Primary statistic (h = 24, δ = 0.10, 1% budget): no variant shows excess directional precision over matched
controls; Holm p = 1.0 for all five; every CI includes 0. `uf_convex_longshot_v1`,
`uf_new_wallet_concentration_v1` and `uf_pressure_no_response_v1` are not testable (< 30 episodes).** Recall on
large moves is 0-2%, and mean paper P&L is negative for every variant. `alerts_needed(b, 0.05)` = 281-659
episodes against 6-80 observed: null and underpowered. The full table, Maduro descriptive firings and
caveats are in `CASE_STUDY_MADURO.md` (Part B). Results file:
`data-dumps/research_lab/event_study/judgement_results.json`. Cumulative `detector_eval` trials: 8.

## Revision census-anchored-1: large-trade census (plan, probes, estimates; written before any evaluation)

**Why.** The judgement-half run was underpowered: 6-80 alert episodes against `alerts_needed` 281-659.
This revision anchors evaluation on large taker prints across a fresh data window and adds IF-H1. It spends
new budget: IF-H1 is one new trial, and the 5 frozen variants re-run on a new panel are 5 more. The
cumulative count is carried in `trials.jsonl`.

**Probes (2026-10-12, `large_trade_census.PROBE`).**
- The global v1 `/trades` without `market` ignores `start`/`end`. It is newest-first with an offset cap of
  10,000 and limit 10,000, so it reaches about 29h of prints ≥ $1k.
- `/v2/trades` has a signed keyset cursor. It was monotonic and complete against a v1 cross-check
  (331/331), but it is **exhausted at 2026-09-01 00:07Z**: 813 pages, 812,970 prints ≥ $500, about
  20k/day. That covers only September-October 2026, all inside the judgement-half months, so it is kept on
  disk but not used.
- v1 `market=<comma-separated list>&start&end` honours windows. The census therefore uses this route.

**Route and estimates.**
1. **Gamma universe.** Closed markets by end date, 2025-11-01 to 2026-10-12, plus still-open markets by
   start date from 2024-01. `volume_num_min=500` loses nothing for a ≥ $500 census. Days with 500 to
   more than 2,100 markets are split recursively at the offset cap. Estimate: 10-25k requests (about
   1-2h at 4 req/s), no bulk disk (slim rows).
2. **Class rule** `class-v1` (`run_census.CLASS_RULE`; metadata only; fixed in code before any outcome was
   seen): C first (fee category sports/crypto/weather/finance or C keywords), then A, then B.
3. **v1 census of class A/B markets**, prints ≥ $500, window 2025-11-01 to 2026-08-07, 40 markets per
   request, windows halved at the cap. Estimate: 3-6k requests, under 200 MB. Cap 2 GB, ≤ 5 req/s,
   yields to `arepo_pass.sh`.
4. **IF-H1 enrichment** for the gated pool only: one v1 request per wallet to recover the address
   transiently, 1-2 `/activity` pages per episode, and prices per (market, outcome). Estimate: a few
   thousand requests.
5. **Anchored panel** for the 5 frozen variants: 6,000 seeded anchors (one per market and 2h slot, origin =
   gate print + 10 min), all taker trades in [t-24h, t) (1-3 requests), and the merged token-0 price windows.
   Estimate: about 15k requests, about 1.5h.

**Windows.** IF-H1 null quantiles (dev): 2025-11-15 to 2025-12-31. Evaluation: 2026-01-01 to 2026-07-30
(t_a). There is no overlap with the judgement half (t ≥ 2026-07-30T06Z). The months overlap the broad
sample's discovery half, which was tuning data for the 5 variants but a different unit and different markets.
Maduro/Venezuela and catalogue markets are excluded.

**Power expectation.** For the 5 variants the declared 1% budget fixes alerts at about 1% of anchored rows,
so 6,000 anchors give about 60 alerts: still below `alerts_needed`. Reaching it would need 30k or more
anchors (about 90k requests). For IF-H1 (top 10 per week over about 30 weeks) the ceiling is about 300 alerts.

### IF-H1 frozen (before any evaluation)

`if_h1_hist_v1`, sha256 `f92952cbce94bdf260836de4c7e126439613e1a6c6049f694af2ec8480e6e839`, frozen
2026-10-12T05:10:07Z (`detector_specs/if_h1_hist_v1.json`, index `FROZEN_IF_H1.json`; a `trials.jsonl` line
of kind `detector_eval_if_h1`, status `frozen`). The class rule is `class-v2`: a pre-outcome metadata fix of
v1, which had sent fee-less daily club matches ("Will <club> win on <date>?") to B and matched `deport*` on
club names. No outcome or label was computed before the fix or the freeze.

Dev-window `X1` q99 per class and band (pbar ≤ 0.05 / 0.10 / 0.20), with n in brackets:
- A: 8,577 (397), 480 (174), 171 (396)
- B: 303 (113), 214 (175), 157 (321)

These are thin null cells: each q99 rests on its top 1-4 episodes.

Census as built:
- Universe: 1,155,140 markets with ≥ $500 volume, 0 capped windows; class A 26,888, B 19,759, C 1,085,822,
  unclassified 22,671.
- v1 census: 46,647 class A/B markets, 883 batches, 2,232 requests, 1,275,965 prints ≥ $500, 0 incomplete
  windows.
- Episodes reaching $1k: 345,066 (dev 43,965; eval 301,101).
- Disk 944 MB of the 2 GB cap, mostly the uncompressed universe JSON.
