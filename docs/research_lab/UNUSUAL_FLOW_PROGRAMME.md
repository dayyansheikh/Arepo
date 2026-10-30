# Unusual-flow detection programme (2026-10-12)

**Status:** design and governance for the case-study / unusual-flow work. Nothing here is evidence. Every
result produced under this programme is labelled `evidence_role: exploratory_historical` until a registered
LIVE test (section 7) is scored. AREPO never labels a wallet, a trade or a market as insider activity; the
object of study is *unusual pre-move flow*, a statistical pattern in public, hashed, taker-side trade data.

Companion files: `UNUSUAL_FLOW_DETECTOR.md` (the frozen variants and their hashes),
`backend/astrolabe/research_lab/detector_eval.py` (registry, engine, held-out harness),
`backend/astrolabe/research_lab/detector_specs/` (frozen rule specs, `FROZEN.json` index),
`CASE_STUDY_MADURO.md` (tuning case), `CASE_CATALOGUE.md` (held-out cases),
`INFORMED_FLOW_SIGNAL_THEORY.md` (candidate signals). Governance follows
`FEATURE_DISCOVERY_PROGRAMME.md` section 3 (cumulative trial count, BY/Holm, fresh-data budget).

## 1. Question

Does a fixed, pre-specified rule over public trade-flow and wallet-concentration features, applied to a
market at time *t* using only data strictly before *t*, select market-hours that are followed by large price
moves more often than matched market-hours it did not select, at a fixed alert budget and after costs?
The question is about *flow preceding price discovery*, not about who traded or why.

## 2. Data roles (the split)

| Role | Data | Allowed use | Forbidden use |
|---|---|---|---|
| **Tuning** | Maduro markets (`CASE_STUDY_MADURO.md`), the `INFORMED_FLOW_SIGNAL_THEORY.md` candidates, and the **discovery half** of the broad sample (rows with `t` before the discovery cut) | Choosing feature set, functional form, thresholds, windows, centres and scales of the frozen rules | Reporting any metric as a result |
| **Held out: cases** | `CASE_CATALOGUE.md` markets (reported pre-news trading, researched by a separate agent; list hash pinned before any detector freeze) | Recall (did a frozen rule fire before the public news time), lead time, and the matched quiet-case controls of section 5 | Precision, base rates, any tuning. Cases added after a freeze are a separate `post_freeze` bucket |
| **Broad sample** | Random, stratified historical markets from `history_backfill` (seeded `draw_sample`), judgement half = rows with `t` at or after the discovery cut | Base rates, precision at budget vs matched controls, recall on large moves, cost-aware value | Any rule change after seeing it |
| **Live** | AREPO collector passes after the registration commit | The only data that can move a rule past L3 (section 7) | Everything else |

Discovery cut: the broad sample's row-time median, computed once on the sample manifest and written into
`UNUSUAL_FLOW_DETECTOR.md` before any judgement-half metric is produced. Catalogue-case markets are
removed from the broad sample (by `condition_id`) so a reported case never appears in a base rate.
Maduro markets are removed from every metric. Nothing is pooled across roles.

## 3. Panel contract (what the engine evaluates)

One row = one market at one origin time. Canonical columns (`detector_eval.normalise_panel` maps the
historical `ml_tf_*`/`ml_wlt_*` names and the live `flow_*`/`wlt_*` names onto these; the mapping id
is recorded in every trial):

- identity and clocks: `market_id`, `cluster` (event id, falling back to market id), `t` (epoch s),
  `mid` (token-0 mid at *t*), `liquidity`, `fee_category`, optional `fee_schedule`/`fees_enabled`;
- executability: `traded_before_t` (1/0/NaN). Rows with 0 or NaN are **excluded** before scoring and
  counted (`n_excluded_untraded`): a market with no trade before *t* has no executable price;
- flow features, short window (`_s`: 1h live, 2h historical) and long window (`_l`: 6h live, 24h
  historical): `imb_s` (signed outcome-0 share in [-1, 1]), `n_s`, `n_l`, `burst` (short-window
  count / long-window rate), `large_trade_rel` (largest short-window trade / long-window mean size),
  `top1_share_l`, `hhi_l`, `n_wallets_s`, `n_wallets_l`, `new_wallet_share_l`, `new_wallets_s`,
  `last_trade_age_h`, `ltp_minus_mid`;
- outcomes: `fwd_move_{h}h` = `mid(t+h) - mid(t)` in token-0 terms for h in {2, 6, 24} (NaN when the
  target is unavailable: never extrapolated); for case rows `news_ts` (public news time, epoch s).

Short and long windows are not identical across sources. The frozen rule is defined on the canonical
names; a trial records `panel_source` (`history` or `live`) and the comparison across sources is
descriptive only. The live confirmation (section 7) uses the live mapping and nothing else.

## 4. Detector specification and freezing

A **rule** is a declarative JSON spec (no code): `rule_id`, `version`, `theory_ref` (section of the
theory doc or `programme_prelisted`), `conditions` (all must hold: `feature op value`), `terms`
(`feature`, `transform` in {raw, abs, log1p}, `center`, `scale`, `weight`, `cap`), `min_terms_present`,
`direction_feature` (sign gives the alert direction; null for undirected rules). Score =
sum over present terms of `weight * clip((transform(x) - center) / scale, -cap, cap)`; rows failing a
condition, or with fewer than `min_terms_present` finite terms, are not alertable. Higher = more
unusual. `center`/`scale` are **numbers written in the spec**, taken from tuning data only, never
recomputed from the evaluated panel; so the same spec gives the same score anywhere.

Process:
1. Candidates come from the theory doc's ranked hypotheses plus the programme's pre-listed flow/wallet
   features (`flow_features.py`, `history_backfill._trade_flow`). Each candidate is written as a spec.
2. Tuning (Maduro + discovery half): descriptive plots and alert lists only; choose **at most 5 variants**
   (`FEATURE_DISCOVERY_PROGRAMME` budget: each variant is one trial line, Holm across the set). Prefer
   one composite primary and mechanistically distinct secondaries over threshold tweaks of one idea.
3. Freeze: `detector_eval.freeze_rules()` writes `detector_specs/<rule_id>.json` and `FROZEN.json`
   (sha256 of the canonical JSON of each spec, `engine_version`, freeze commit, UTC). The sha256 list is
   copied into `UNUSUAL_FLOW_DETECTOR.md` and committed. A `rule_id` can never be overwritten; a change is a
   new `rule_id`/`version` with a written justification and it spends budget.
4. The held-out harness refuses any rule not in `FROZEN.json`, any spec whose recomputed hash differs from
   the frozen one, any `engine_version` mismatch, and any run without a valid `evidence_role`. Every
   harness run appends a `trials.jsonl` line (kind `detector_eval`) whatever the result.

## 5. Evaluation metrics for rare events

All metrics are computed by `detector_eval.evaluate()` on alertable rows only, per horizon *h* and move
size δ (primary: h = 24, δ = 0.10 in probability units; secondary: h = 6, δ = 0.05). An **alert episode** is
a run of alerted rows of one market separated by less than `cooloff_s` (default 24h); the first row of an
episode carries the outcome. Large-move episodes are defined the same way on `|fwd_move_h| >= δ`.

1. **Alert budget.** Top-k rows by score, k = `budget` × alertable rows (default 1%); ties broken by
   (market_id, t). The budget is fixed before the run and written into the trial.
2. **Precision at budget vs matched controls.** For each alert episode, controls are up to `k_controls`
   (default 5) non-alerted rows from the same time bucket (same UTC day), same `|mid-0.5|` band
   ({<0.05, 0.05-0.20, 0.20-0.45, ≥0.45}) and same liquidity tercile (terciles cut on the evaluated panel),
   different market, chosen by seeded hash. Per-alert excess `d_i = hit_i − mean(hit_controls)`, where hit =
   large move within *h* in the alert's direction (directional rules) or either direction (undirected).
   Report precision, control base rate, lift, and the **event-clustered bootstrap** (`ml_explain.cluster_boot`,
   cluster = `cluster`) CI and one-sided p for mean `d_i > 0`. This is the **primary statistic**.
3. **Random-budget placebo.** The same k alerts drawn at random within the same strata, 200 draws:
   the observed precision's rank among placebo precisions.
4. **Recall on large moves.** Share of large-move episodes whose market was alerted in [t − lookback, t]
   (lookback = h). Reported with its cluster CI; never the primary (the detector is not meant to catch
   every move).
5. **Lead time.** For case rows with `news_ts`: `news_ts − t_first_alert` over alerts in [news_ts − 72h,
   news_ts); distribution (min, median, IQR) and share of cases with any pre-news alert. For broad rows:
   time from first alert of an episode to the first row whose `|fwd_move_h| >= δ`.
6. **Cost-aware value.** Directional alerts only: buy the alerted outcome at `mid + spread/2`, taker fee via
   `economics.fee_spec`/`taker_fee` (unknown fee -> `MAX_DOCS_RATE`, policy `max_if_unknown`), exit at
   `mid(t+h) − spread/2` with a second fee, `min_order_size` shares. Mean net P&L per alert with
   `economics.boot_ratio` one-sided lower bound, clustered. Labelled "optimistic, not tradable" (no depth
   walk in history; book sweeps exist live only).

**Multiple testing.** ≤ 5 frozen variants, one primary metric each: Holm across the set (`ml_explain.holm`),
one-sided. The cumulative detector trial count is reported in every trial line. Secondary metrics are
descriptive. **Minimum sample.** A precision comparison is "not testable" below 30 alert episodes or 10
clusters with an alert (the `economics.h2a` convention). **MDE.** Given the control base rate *b* and the
number of alert episodes *n* from the broad sample, `detector_eval.alerts_needed(b, delta)` gives the episodes
required for 80% power (one-sided 5%) to detect an excess precision of `delta`; the registered LIVE test
reports its planned *n* against this.

## 6. Selection bias from reported cases, and how it is handled

Reported cases are selected on the outcome (a large move happened), on conspicuousness (someone noticed the
flow) and on salience (politics, geopolitics, celebrity). Any metric conditioned on them is inflated.

- Cases never contribute to precision or base rates (section 2). They answer only: *given* a reported case,
  did a frozen rule fire before the public news time, and how early?
- **Quiet-case controls.** For every catalogue case the catalogue agent draws, by seeded hash and before
  seeing any alert, (a) 5 markets of the same category, price band and liquidity band whose `|fwd_move|`
  reached δ in the same month **without** a reported case, and (b) 5 such markets with no large move. If a
  rule fires on (a) as often as on cases, it detects large moves in general, not reported-case flow; (b)
  gives the look-alike false-alert rate. Both are reported next to case recall.
- Case list hash (`sha256` of the sorted `condition_id` list) is pinned in `CASE_CATALOGUE.md` **before**
  `UNUSUAL_FLOW_DETECTOR.md` is committed; the detector author never sees the case list. Cases found later
  go to `post_freeze` and are reported separately.
- Case recall is reported with the number of cases, the reporting-conditioned caveat, and the base rate from
  the broad judgement half beside it. No lift is computed from cases.
- Maduro, the founding example, is tuning only and absent from every table.

## 7. Path to a pre-registered LIVE prospective test

The live collector (launchd, 2-hourly) already samples about 2,000 trade-active markets with hashed wallets
(`trade_sample`, `wallets.csv.gz`), and complete-universe scans give `mid(t+h)`. Needed additions, all
read-only public collection, each with its own admission note:

1. **Alert line at collection time.** After each pass, score the frozen rules on that pass's features
   (`flow_features.features_for_sample` -> `normalise_panel`) and append every alert (rule_id, spec hash,
   market, t, score, direction, matched-control market ids drawn at the same time) to an append-only
   `data-dumps/research_lab/alerts/alerts.jsonl` **before any outcome exists**. The budget per pass is fixed
   in the registration (default 1% of alertable rows, cap 20).
2. **Outcome join.** `fwd_move_6h`/`fwd_move_24h` from the next complete snapshots at or after t+h
   (scheduled time kept separate from receipt time, `MAX_QUOTE_AGE_S` rule). Pending, unavailable and
   evaluated outcomes stay distinct.
3. **News time (secondary).** Not needed for the primary metric. If used, a pre-declared public source
   (GDELT 15-min publish time, first mention of the market's entity) is annotated after the window
   closes, by the pre-declared recipe, never by hand-picking.
4. **Registration** (ledger line, `science-reviewer` accepting pass): rule hashes, primary metric
   (section 5 item 2, h = 24, δ = 0.10, budget), MDE and planned number of passes from the broad sample's
   base rate, stopping rule (fixed number of passes, no peeking), Holm across ≤ 5 variants, the exact
   control-matching recipe, and the economic check as a separate secondary. Only `evidence_role:
   prospective_confirmation` rows after the registration commit are scored; `provenance.require_confirmation_role`
   guards the scorer.
5. **Verdict** recorded whatever its sign; a negative result closes the variant set for that data window.

## 8. Instructions for the other agents

**Maduro agent** (after `UNUSUAL_FLOW_DETECTOR.md` is committed): (a) do not touch the frozen specs;
(b) build the broad panel with `history_backfill.build_panel` (seeded stratified sample, catalogue
`condition_id`s and Maduro markets removed, `traded_before_t` kept as a column) and pass it through
`detector_eval.normalise_panel(df, source="history")`; (c) compute the discovery cut (row-time median) and
write it into the detector doc before any judgement metric; (d) run `HeldOutHarness(registry).evaluate(rule_id,
panel[judgement], budget=0.01, horizon_h=24, delta=0.10, evidence_role="exploratory_historical", dataset=...)`
for every frozen `rule_id`, then `holm_across_rules`; (e) report base rates, precision, lift, recall,
lead time, P&L, `alerts_needed` and the cumulative trial count in `CASE_STUDY_MADURO.md` Part B.

**Catalogue agent**: (a) pin the case-list hash in `CASE_CATALOGUE.md` before reading the detector doc;
(b) build per-case panels (case market rows plus the quiet-case controls of section 6) with `news_ts` set
on case rows only, normalise with `source="history"`; (c) run the same harness call with
`case_mode=True`; it reports recall-before-news, lead-time distribution, and the alert rates on control
groups (a) and (b), and refuses precision; (d) write results into `CASE_CATALOGUE.md` with the
reporting-conditioned caveat verbatim from section 6.

Both: no requests while `arepo_pass.sh` runs, ≤ 5 req/s, check swap before `build_panel`.
