# Unusual-flow detector: frozen variants (batch 1, 2026-10-12)

**Status:** frozen rule specifications for the held-out and broad-sample evaluations described in
`UNUSUAL_FLOW_PROGRAMME.md`. Nothing here is a result. `evidence_role: exploratory_historical` applies to
every evaluation of these rules until a registered live test exists. No wallet, trade or market is, or will
be, labelled as insider activity; the rules describe public, hashed taker-flow patterns only.

Specs live in `backend/astrolabe/research_lab/detector_specs/` (`<rule_id>.json`, index `FROZEN.json`).
`detector_eval.HeldOutHarness` refuses anything not listed below with exactly these hashes, any
`engine_version` other than `detector-eval-v1`, and any run without a valid `evidence_role`.

## Frozen variants (3 of the 5 slots)

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

## Remaining slots (2 of 5) and the theory doc

`INFORMED_FLOW_SIGNAL_THEORY.md` had not landed when batch 1 was frozen. Up to two theory-derived variants may be
frozen as batch 2 under these conditions: (a) they are written from the theory doc and the Maduro tuning
case only; (b) they are frozen (`freeze_rules`, committed, hashes added here) **before** any held-out or
judgement-half result of batch 1 is committed to `CASE_CATALOGUE.md` or `CASE_STUDY_MADURO.md` Part B.
Otherwise batch 2 is labelled `post_hoc` in this file and is not part of the Holm set. Holm runs across all
frozen variants (≤ 5) on the primary statistic.

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
- Budget accounting: 3 detector trials pre-committed (one per variant on the judgement half) plus the
  same 3 in case mode; `prior_detector_trials` in every `trials.jsonl` line carries the cumulative count.

## Live data needed before a registered live test (programme doc section 7)

| Canonical feature | Live status (`flow_features.py` sidecar) | Needed |
|---|---|---|
| `large_trade_rel` | Not available: live has `flow_max_trade_liq_1h` (divides by liquidity, not by mean trade size) | Add largest 1h trade / mean 6h trade size to the live features (collector change, separate admission note) |
| `new_wallets_s` | Not available | Optional; batch-1 rules do not use it |
| `new_wallet_share_l` | `wlt_new_share_6h`, NaN until the first-seen index spans 7 days | Nothing; coverage grows with time |
| `n_wallets_l` | `wlt_n_buy_6h + wlt_n_sell_6h` (wallets with net zero excluded) | Acceptable approximation; record in the admission note |
| `burst` | derived `flow_n_1h / (flow_n_6h / 6)` | Nothing |
| Alert line, matched-control ids at alert time | Not written anywhere | New append-only `alerts.jsonl` written by the pass before any outcome exists |
| `fwd_move_6h/24h` | From complete-universe snapshots | Join step; pending/unavailable/evaluated kept distinct |

`uf_large_trade_v1` therefore cannot be part of a live registration until the collector change lands; it
remains a historical-only variant unless that happens.

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
