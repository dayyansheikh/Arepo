# Cross-venue study: Polymarket vs Kalshi (exploratory, historical)

**Status (2026-10-13): REVISED, see section 10; the v1 sections below are kept as originally written and the gap conclusions in them are SUPERSEDED.** `exploratory_historical`. Hypothesis-generating only. No edge, calibration, profitability or
tradability claim. Not prospective evidence and never poolable with prospective panels. Promotion-ladder rung for any
finding below: L1 (Exploratory). Code: `backend/astrolabe/research_lab/cross_venue.py`, runner
`backend/scripts/run_cross_venue.py`, tests `backend/tests/test_research_lab_cross_venue.py` (19 tests).
Artifacts (git-ignored): `data-dumps/research_lab/cross_venue/` (356 MB; `results.json`, `matches.json`, `series/`).

> **Revision r1 (2026-10-13).** An audit found 9 mismatched pairs (inverted Yes/No, before-vs-on dates, AND-vs-single awards) and 16
> halftime-template pairs among the 341. On the cleaned set the lead-lag survives unchanged, but the "gap adds no out-of-sample value" result
> below reverses (+5% at 1h, CI excludes 0). The v1 null was produced by the mismatched pairs. See section 10.

## 1. Question and short answer

Does one venue lead the other on events listed on both? Do Kalshi-minus-Polymarket gaps predict convergence, and which side moves?

- **Kalshi moves first, by a short margin.** Over 10-minute changes, Kalshi's change in one step correlates with Polymarket's change
  in the following step (r about 0.24); the reverse is about 0. Peak lead is 10-20 minutes depending on how Polymarket
  timestamps are read (section 6), so the lead is at the limit of what 10-minute data can resolve. Beyond 30 minutes the lead
  is not distinguishable from zero.
- **Polymarket does most of the closing.** Of the adjustment toward the other venue's price, Polymarket accounts for 86% at 1h
  (95% CI 80-91%), Kalshi for 14%. Divergence half-life is about 80 minutes (CI 54-119; descriptive).
- **The gap itself adds no out-of-sample predictive value** for Polymarket's next move over M0 at 1h or 6h (gap only: relative
  MSE gain +1.6% at 1h, CI -4.1 to +4.9%; 6h +1.8%, CI -10.7 to +8.4%). The only predictive content is Kalshi's own latest
  change over the next 10 minutes (+5.3%, CI +1.1 to +9.2%, BY-passing), which is the lead-lag finding again.
- **Economics is not resolved.** Gap exceeds modelled two-venue costs on 15% of grid steps under a mid scenario, often for hours, which
  more likely reflects basis/stale-price artefacts and unmodelled constraints than free money (section 5.6).
- A cross-venue gap is **not** shown to be a strong signal of "something happening". The evidence supports a small, fast,
  one-directional information lag that has not been tested for economic value.

## 2. Data and Kalshi access

- **Kalshi public market data needs no key** (probed 2026-10-12): `/markets`, `/historical/markets` (settled before the
  2026-08-12 cutoff), `/series`, `/events`, and candlesticks (`/series/{s}/markets/{t}/candlesticks` live,
  `/historical/markets/{t}/candlesticks` older) with 1-minute bid/ask/last/volume, at most 5000 candles per request. Only GET
  market-data endpoints were used; no account, no trading endpoints.
- **Polymarket:** Gamma `/events` (closed, volume >= 20k, 3-day end-date windows, 148,384 markets), CLOB `prices-history` at
  fidelity 10 minutes for the Yes token, 14-day windows (`history_backfill.fetch_prices`). Calls yield to the live collector
  (`live_pass_running`; 360 s waited). Rate <= 4.5 req/s per venue (Kalshi series scan used 6 processes at 0.8 req/s each).
  Requests in the pair-series fetch: Kalshi 2,769, Polymarket 985. Disk 356 MB (cap 1 GB). The heavy lock was not needed (no
  multi-GB step; analysis peak memory is small).
- **Kalshi universe:** 6,134 series whose titles share a content bigram with a Polymarket Yes/No title (of 14,975 series; hourly and
  15-minute series dropped), all settled markets closing in the last 12 months with volume >= 5,000 contracts, multivariate
  combos excluded: 326,380 markets. Economics-category series (Fed, unemployment rate, CPI) are in the universe, see section 3 for why none matched.

## 3. Matching (deterministic, conservative, one-to-one)

Rules (`cross_venue.match_markets`): Polymarket must be Yes/No (so Kalshi Yes = Polymarket Yes); resolution times within 3 days;
the set of numbers in the two texts must be identical; word Jaccard >= 0.6 with >= 3 shared words; contract-changing words
(margin, spread, exact, total, least, above, below, over, under, between, average, ...) must not appear on one side only;
mutual best candidate with a 0.10 margin over each runner-up, ties dropped. Outcomes are never used for matching.

- Matched pairs: **958** (688 sports). Capped for the 100-500 target by a hash-of-ticker rule: Sports kept 230 of 688, other categories whole:
  **500 selected**. 493 had a usable window; **341 pairs (190 Polymarket events) have >= 200 usable grid steps** and form the analysis set
  (Sports 153, Elections 83, Entertainment 54, Politics 21, Mentions 18, Science and Technology 8, Financials 4).
- **No Fed-decision, CPI or other macro pair was matched**: the venues list different contract shapes (Polymarket "cut by 25 bps after the
  meeting" vs Kalshi "upper bound above X%"), and the conservative matcher rejects non-identical contracts. The study therefore
  says nothing about macro markets. (The conflict-word rule also dropped three unemployment-rate pairs, "Exactly 4.2%" vs "4.2%", where "exactly" is stylistic: a conservative loss, left as is rather than tuned after the fact.)
- Post-hoc diagnostic only (not used to filter): resolved Yes/No agree in 929 of 946 matched pairs (98.2%), so about 2% of matches are likely
  rule-mismatched or wrong.
- A first matcher run (979 pairs) printed a false positive ("margin of victory for Lula" vs "win the first round"); the conflict-word
  rule was added before any price data were fetched.

### Hand verification of 30 printed pairs (seeded sample of the 500 selected)

I read each pair at the title level (resolution rules were not read line by line). All 30 describe the same proposition. Four
carry wording differences that I could not settle from titles alone: #1 (Feastable vs Feastables), #11 and #26 ("perform at the Super
Bowl" vs "during the halftime show"), #12 (Jampzey vs Jampzey.hl). No pair judged wrong: 30/30 plausible, upper bound on error
by the Wilson 95% interval for 0/30 observed errors is about 11%, and the 2% resolution disagreement above is the better estimate.

| # | Kalshi category | Kalshi | Polymarket | Jaccard | date gap (d) |
|---|---|---|---|---|---|
| 1 | Mentions | What will MrBeast say during Next MrBeast Youtube Video? Feastable | Will MrBeast say "Feastables" during his next YouTube video? | 0.88 | 0.0 |
| 2 | Elections | Who will be the Democratic nominee for Attorney General in Rhode Island? Kim Ahe | Will Kim Ahern be the Rhode Island Attorney General Democratic nominee? | 1.00 | 0.4 |
| 3 | Elections | Will Colin Allred be the Democratic nominee for TX-33? | Will Colin Allred be the Democratic nominee for TX-33? | 1.00 | 0.1 |
| 4 | Elections | Will Jay Feely be the Republican nominee for AZ-1? | Will Jay Feely be the Republican nominee for AZ-01? | 1.00 | 0.2 |
| 5 | Elections | Will Mikie Sherrill win the 2025 New Jersey gubernatorial election? | Will Mikie Sherrill win the New Jersey Governor Election in 2025 Mikie Sherrill  | 0.71 | 1.9 |
| 6 | Sports | Will Ashlyn Krueger win the Wimbledon Women Singles 2026? | Will Ashlyn Krueger be the 2026 Women’s Wimbledon Winner? | 0.67 | 0.0 |
| 7 | Politics | Will Nancy Pelosi attend the 2026 State of the Union Address? | Will Nancy Pelosi attend the 2026 State of the Union address? | 1.00 | 0.2 |
| 8 | Entertainment | Will Ariana Grande be the #1 rank on Google’s Year in Search 2025 Global – Actor | Will Ariana Grande be ranked #1 globally in Google’s Year in Search 2025 Actors? | 0.60 | 0.3 |
| 9 | Sports | Lamine Yamal: 1+ assists? | Lamine Yamal: 1+ assists | 1.00 | 0.1 |
| 10 | Mentions | What will Donald Trump say during meetings with the Prime Minister of the Slovak | Will Trump say "Tariff" during meetings with Slovak Prime Minister? | 0.80 | 0.3 |
| 11 | Entertainment | Who will perform at the Super Bowl LX? J Balvin | Will J Balvin perform during the Super Bowl LX halftime show? | 0.62 | 0.2 |
| 12 | Sports | Will Jampzey win the Synthetix Mainnet Trading Competition? | Will Jampzey.hl win the Synthetix trading competition? | 0.67 | 0.1 |
| 13 | Entertainment | Will Juliano Floss win Big Brother Brasil 26? | Will Juliano Floss win Big Brother Brasil 26? | 1.00 | 0.4 |
| 14 | Sports | Lionel Messi: 1+ goals | Lionel Messi: 1+ goals | 1.00 | 0.0 |
| 15 | Entertainment | 2025 Game of the Year? Hades II | Will Hades II win Game of the Year at the 2025 Game Awards? | 0.80 | 0.3 |
| 16 | Entertainment | Will Player 58 win 'Beast Games' Season 2? | Will Player 58 win Beast Games: Season 2? | 1.00 | 0.2 |
| 17 | Sports | Liverpool at Wolverhampton: Both Teams to Score | Wolverhampton Wanderers FC vs. Liverpool FC: Both Teams to Score | 0.62 | 0.1 |
| 18 | Elections | Will Byron Donalds be the Republican nominee for Governor in Florida? | Will Byron Donalds be the Republican nominee for Florida Governor? | 1.00 | 0.1 |
| 19 | Elections | Will Jeannette Jara win the Chilean presidential election? | Will Jeannette Jara win the Chilean presidential election? | 1.00 | 0.1 |
| 20 | Sports | Mikel Merino: 1+ goals | Mikel Merino: 1+ goals | 1.00 | 0.0 |
| 21 | Sports | Harry Kane: 1+ goals | Harry Kane: 1+ goals | 1.00 | 0.0 |
| 22 | Sports | Who will be HLTV Awards: Player of the Year? Mathieu "ZywOo" Herbaut | Will Mathieu "ZywOo" Herbaut win the HLTV Player of the Year award? | 1.00 | 0.6 |
| 23 | Elections | Will Jay Collins be the Republican nominee for Governor in Florida? | Will Jay Collins be the Republican nominee for Florida Governor? | 1.00 | 0.1 |
| 24 | Elections | Will Elmano de Freitas win the 2026 Ceará gubernatorial election? | Will Elmano de Freitas win the 2026 Ceará gubernatorial election? | 1.00 | 0.2 |
| 25 | Elections | Will Chong Won-o win the 2026 Seoul mayoral election? | Will Chong Won-oh win the 2026 Seoul Mayoral Election | 0.83 | 0.4 |
| 26 | Entertainment | Who will perform at the Super Bowl LX? Ricky Martin | Will Ricky Martin perform during the Super Bowl LX halftime show? | 0.67 | 0.1 |
| 27 | Sports | Nico Williams: 1+ goals | Nico Williams: 1+ goals | 1.00 | 0.0 |
| 28 | Entertainment | Will SILENT HILL f win Outstanding Visual Style Award at The 2025 Steam Awards? | Will Silent Hill f win Outstanding Visual Style at the 2025 Steam Awards? | 1.00 | 0.0 |
| 29 | Sports | Will the Ghana win the 2026 Men's World Cup? | Will Ghana win the 2026 FIFA World Cup? | 0.60 | 0.1 |
| 30 | Elections | Will Sanae Takaichi be the next Prime Minister of Japan? | Will Sanae Takaichi be the next Prime Minister of Japan? | 1.00 | 1.2 |

## 4. Alignment (point-in-time)

- 10-minute UTC grid (the Polymarket history resolution; the requested 5-minute lag is below what the data can resolve, so the smallest
  lag tested is 10 minutes).
- Polymarket point stamped t' is usable at grid time t only if t' + 600 s <= t (conservative: the stamp may be a bucket start). Maximum age 1h.
  Kalshi candle usable once its end timestamp <= t; value = mid of closing bid/ask where 0 < bid < ask < 1 and spread <= 10c (no last-trade
  fallback); maximum age 30 min. Gaps stay missing; nothing is interpolated.
- A step is used only if both prices lie in [3%, 97%] at that step. Window: up to 30 days before the earlier resolution time,
  not before either market opened. Pairs with fewer than 200 usable steps (about 33 hours) are dropped (a pair-level rule
  using the whole window, not outcomes). Used steps: 551,224 (10th/50th/90th percentile date 2025-11-18 / 2026-04-03 / 2026-07-30).
- Sensitivity (descriptive, outside the BY family): Polymarket points usable at their own stamp (`pm_lag = 0`).

## 5. Results

Cluster = Polymarket event id (190 clusters); 4,000 event-cluster bootstrap resamples; 95% percentile CIs. Benjamini-Yekutieli at
q = 0.10 over the study's **pre-declared family of 20 tests** (lead-lag asymmetry at 7 lags, Granger arms 6, error-correction betas 6,
jump lead 1). Clustering by event does not capture common shocks across events at the same time, so CIs are probably too narrow.

### 5.1 Lead-lag (conservative alignment)

r(K_t, P_t+L) is the correlation between Kalshi's 10-minute change and Polymarket's change L later; asymmetry = r(K->P) - r(P->K) (> 0: Kalshi leads).

| Lag | r K->P | r P->K | Asymmetry (95% CI) | p (2-sided) | BY p | Pass |
|---|---|---|---|---|---|---|
| 10 min | 0.054 | -0.003 | 0.057 (0.026, 0.098) | 0.001 | 0.008 | yes |
| 20 min | 0.243 | 0.001 | 0.242 (0.180, 0.308) | 0.0005 | 0.0045 | yes |
| 30 min | 0.013 | -0.015 | 0.029 (0.008, 0.050) | 0.0075 | 0.054 | yes |
| 1 h | 0.008 | 0.003 | 0.005 (-0.012, 0.023) | 0.52 | 1.0 | no |
| 2 h | -0.009 | 0.002 | -0.011 (-0.043, 0.013) | 0.46 | 1.0 | no |
| 3 h | 0.001 | 0.001 | 0.000 (-0.016, 0.014) | 0.89 | 1.0 | no |
| 6 h | 0.002 | 0.001 | 0.001 (-0.008, 0.009) | 0.76 | 1.0 | no |

With `pm_lag = 0` the spike moves to 10 minutes (r K->P 0.245, asymmetry 0.231, CI 0.170-0.295) and the 20-minute value falls to 0.02.
So the lead is one 10-minute step plus whatever the Polymarket timestamp convention adds; **it cannot be pinned to better than 10-20 minutes**.
Sports and non-sports agree (asymmetry at the peak 0.166 and 0.289).

### 5.2 Granger-style out-of-sample prediction of Polymarket's next move

Target: change in Polymarket price over the next 10 min / 1 h / 6 h. M0 = own 1- and 6-step changes + level terms. Models: M0 + gap
("gap"), M0 + gap + Kalshi 1- and 6-step changes ("gapk"). Chronological walk-forward in 4 calendar blocks (blocks 2-4 scored,
training rows purged so their targets end before the scored block), standardised ridge, non-overlapping origins per horizon.
Relative MSE gain over M0 (positive = better).

| Horizon | Model | Gain (95% CI) | p (1-sided) | BY p | Blocks positive |
|---|---|---|---|---|---|
| 10 min | gap | +0.5% (-4.1, +3.4) | 0.36 | 1.0 | 1/3 |
| 1 h | gap | +1.6% (-4.1, +4.9) | 0.23 | 1.0 | 2/3 |
| 6 h | gap | +1.8% (-10.7, +8.4) | 0.35 | 1.0 | 2/3 |
| 10 min | gap+K changes | +5.3% (+1.1, +9.2) | 0.010 | 0.067 | 3/3 |
| 1 h | gap+K changes | +3.3% (-3.6, +9.0) | 0.14 | 0.83 | 2/3 |
| 6 h | gap+K changes | +0.8% (-8.8, +6.1) | 0.38 | 1.0 | 2/3 |

With `pm_lag = 0` the 10-minute gap+K arm becomes +9.8% (CI +5.2, +15.0); the other five arms stay indistinguishable from 0.
Observations: 340,144 (10 min), 52,764 (1 h), 8,318 (6 h).

### 5.3 Which side moves (error correction)

Slope of the future change on the gap g = K - P: beta_P from dP on g, beta_K from dK on -g (both > 0 means each side moves toward the other).
Raw gap (includes any persistent basis); share_P = beta_P / (beta_P + beta_K).

| Horizon | beta_P (CI) | beta_K (CI) | share_P (CI) | BY (both betas) |
|---|---|---|---|---|
| 10 min | 0.032 (0.017, 0.074) | 0.003 (0.001, 0.006) | 92% (89, 96) | 0.003 |
| 1 h | 0.067 (0.036, 0.139) | 0.011 (0.005, 0.023) | 86% (80, 91) | 0.003 |
| 6 h | 0.149 (0.083, 0.295) | 0.054 (0.026, 0.095) | 73% (60, 86) | 0.003 |

With the pair's expanding past-only mean gap removed (basis-adjusted) the shares are 92%, 86% and 76%, and beta_P is 0.069/0.125/0.251.
`pm_lag = 0` gives 90%, 82%, 74%. Sports lean more to Polymarket (91% at 1h) than non-sports (83%).

### 5.4 Who moves first around large moves

Events: the Kalshi-Polymarket average moves >= 5c within 1 h, both venues move the same way by >= 2c, all points usable; non-overlapping
per pair. Lead = (step at which Polymarket has covered half of its own move) minus the same for Kalshi (positive: Kalshi first).
**1,322 events, 159 clusters: Kalshi first 811, Polymarket first 350, tie 161** (70% of decided). Mean lead 0.68 steps (about 7 min), CI 0.51-0.83
steps, BY-passing. With `pm_lag = 0`: 0.29 steps (0.14-0.41), Kalshi first in 66% of decided. Resolution is 10 minutes, so
this is "Kalshi first more often", not a measured latency.

### 5.5 Divergence half-life

Pooled AR(1) of the pair-demeaned gap (the mean uses the whole sample, so this is descriptive, not a forecast): phi = 0.918 per 10 min
(CI 0.880-0.943), **half-life 81 min (54-119)**. When the gap starts at >= 3c (101,003 steps): 77 min (50-116). `pm_lag = 0`: 81 (53-120).

### 5.6 Economic sense check (optimistic; not a tradability estimate)

Locked pair per unit contract: buy Yes where cheaper, No where dearer. Net = absolute gap - Kalshi half-spread (measured from candle
bid/ask, median 1.0c) - Polymarket half-spread (assumed 0.5/1/2c: the history endpoint has no book) - Kalshi taker fee 0.07 p(1-p) -
Polymarket fee (0 or the docs rate 0.05 p(1-p)). Absolute-gap distribution (551,224 steps): median 1.5c, 75th 3c, 90th 5c, 99th 22.9c.

| PM half-spread | PM fee rate | Steps net > 0 | (gap <= 15c only) | Mean net when > 0 | Pairs with >= 1h persistent | Episodes >= 1h |
|---|---|---|---|---|---|---|
| 0.5c | 0 | 29.4% | 28.2% | 3.5c | 304 | 6,020 |
| 0.5c | 5% | 20.3% | 18.9% | 4.2c | 293 | 4,138 |
| 1c | 0 | 22.1% | 20.7% | 4.1c | 291 | 4,564 |
| **1c** | **5%** | **14.7%** | **13.2%** | **5.2c** | **270** | **3,004** |
| 2c | 0 | 12.0% | 10.4% | 6.2c | 251 | 2,525 |
| 2c | 5% | 8.2% | 6.6% | 7.9c | 223 | 1,761 |

Top-10 pairs hold 15-22% of positive steps, so it is not a few outliers. Why this is not evidence of tradable arbitrage:
(1) gaps that persist for an hour or more in most pairs, with an 80-minute half-life, look like a structural basis (different rule wording,
tie/early-close handling, 2% resolution disagreement) or a stale/last-trade Polymarket history price more than a free lunch;
(2) no depth or size, no latency, no slippage, and Polymarket spread is assumed; (3) capital is locked until resolution (days to months),
so a few cents is a small annualised return; (4) fee schedules used are current, not historical. Treat the table as an upper bound.

## 6. Limitations and caveats

- **Timestamp semantics.** Polymarket `prices-history` stamps are not documented as bucket start or end. The two conventions put the lead at 10 or 20
  minutes. Sub-10-minute lead (the 5-minute lag asked for) is not identifiable here. A prospective design with websocket receipt times is needed.
- **Staleness bias.** Polymarket history points can be last-trade-like and stale for thin markets while Kalshi mids update; asynchronous
  quoting alone produces a lead of the more frequently updated series. The lead may partly reflect update frequency rather than information.
- **Selection.** Only pairs with two-sided Kalshi quotes and prices inside 3-97% for >= 33 hours survive (341 of 493 fetched); the last 30 days before
  resolution only; the matcher requires near-identical wording (no macro pairs, sports capped at 230 of 688). Results do not transport to the full universe.
- **Dependence.** Event clustering only; common shocks across events at the same time are not modelled. 190 clusters is modest.
- **Pooling.** Correlations pool pairs and weight high-volatility pairs more. Gains are in squared-error terms on small price changes, which are mostly zero.
- **No outcome used.** The 98.2% resolution concordance is a diagnostic; pairs were never filtered by outcome.

## 7. Deviations and disclosure

1. After a quick preview (200 bootstrap resamples) of the primary statistics on the final data, I added the `pm_lag = 0` sensitivity, the
   sports/non-sports subgroups and the economics persistence/trim diagnostics. These are descriptive and outside the BY family; the
   20-test family and the primary alignment were fixed before the preview.
2. The runner was executed twice. The first run (24 `trials.jsonl` lines) was superseded by an identical-protocol rerun (24 lines) after the
   economics diagnostics were added; seeded bootstrap results outside the economics block are identical. Both sets stay in the log:
   **48 `history_cross_venue` lines, evidence_role `exploratory_historical`.**
3. The BY denominator is this study's 20 tests only, as instructed; it is not merged into the programme's cumulative denominator.
4. Matcher: conflict-word rule added after reading matches (before any price fetch). Sports cap and seed fixed before fetching.

## 8. Next steps (nothing scheduled)

- If the Kalshi lead is to be pursued, register a prospective test with receipt-timed quotes from both venues (WS), the 10-20 minute lead as
  the single primary hypothesis, an MDE from the dev sd, and Polymarket depth for the economic check. Until then it stays at L1.
- Extend the matcher with explicit macro templates (Fed bound ladder, CPI buckets) under their own review; do not loosen the generic matcher.

## 9. Reproduce

```
PYTHONPATH=backend python backend/scripts/run_cross_venue.py --stage match    # universes must exist
PYTHONPATH=backend python backend/scripts/run_cross_venue.py --stage fetch    # resumable, yields to the collector
PYTHONPATH=backend python backend/scripts/run_cross_venue.py --stage analyze  # writes results.json, appends trials.jsonl
cd backend && source .venv/bin/activate && pytest tests/test_research_lab_cross_venue.py && ruff check astrolabe/research_lab/cross_venue.py scripts/run_cross_venue.py
```

## 10. Revision r1: pair audit and rerun on the cleaned set (2026-10-13)

**Trigger.** The live build (\`cross_venue_live.py\`) found its matcher paired 56 of 167 live pairs wrongly (vice-president vs president,
full match vs halftime, ...). I re-audited the 341 historical pairs. \`cross_venue.AUDIT_CONFLICT\` mirrors the live list
(\`LIVE_EXTRA_CONFLICT\`); the v1 matcher (\`CONFLICT\`) is unchanged so the original selection stays reproducible. E009's registration
is untouched by this document.

### 10.1 Audit

- **Audit words (symmetric difference)** flagged 16 pairs, all "Who will perform at the Super Bowl LX?" vs "...during the halftime show". In
  substance these are probably the same proposition (performers appear at the halftime show) but they are dropped for consistency with
  the live rule.
- **Resolved outcomes disagreed for 9 pairs** (of 341; 98.4% agreement among the remaining pairs after the rule/hand drops). Title-level verdicts:
  *different contracts (4)*: Claude Opus "before Jul 24" vs "released on Jul 24"; Claude Opus "before Jul 31" vs Polymarket "will **not** be
  released by Jul 31" (Yes/No inverted); Trump visit China "before May 15" vs "on May 15"; "before May 13" vs "on May 13".
  *Same by title, outcome differs (5)*: Mythos-class model by Sep 1; Time Person of the Year 2025 for Musk, Huang, Altman and "a woman"
  (a Kalshi/Polymarket resolution-wording difference I cannot judge from titles). One further disagreement (Karol G, Super Bowl) is in the
  halftime set.
- **Random sample of 100 further pairs** (seeded, drawn from the unflagged 316; read at title level): 96 same, **4 different**: Cape Verde
  "qualify for the quarterfinals" vs "be eliminated in the quarterfinals"; Bosnia "get eliminated in the Round of 16" vs "reach the Round of 16";
  Messi "Golden Boot **and** Golden Ball" vs Golden Ball only; Drake album "before Dec 2025" vs "in 2025". A targeted template scan of the
  remaining unsampled pairs (words such as eliminated, qualify, reach, not, boot, golden, before, by, exact) found one more of the same kind
  (Mbappe Golden Boot and Golden Ball). Residual error rate among the pairs kept is therefore unknown but plausibly 2-4%.
- Caveat: the 4 date/inversion pairs were first surfaced by the outcome-disagreement list, although each is identifiable from its title
  alone, and I judged them on titles.

### 10.2 Cleaned sets

- **C1 (primary, title/rule based, no outcome used):** drop the 16 halftime pairs and 9 hand-different pairs (Opus x2, Trump China x2, the 4 from the
  sample, Mbappe) minus overlap = **25 dropped, 316 pairs, 183 events, 517,616 usable steps** (Sports 149, Elections 83, Entertainment 37, Politics 19,
  Mentions 18, Science and Technology 6, Financials 4).
- **C2 (sensitivity, outcome-based):** C1 plus the 5 pairs whose outcomes still disagree = 311 pairs. Selecting on agreeing outcomes is selection on the
  future (it favours pairs whose gap later converged), so C2 is reported but not primary. Results are nearly identical to C1.
- Same protocol, bootstrap (4,000 event clusters), 20-test BY family, alignment and seeds as v1. The primary designation of C1 over C2 was made after
  seeing both, for the look-ahead reason above.

### 10.3 Results on C1

| Quantity | v1 (341 pairs) | r1 / C1 (316 pairs) |
|---|---|---|
| r K->P at 20 min | 0.243 | **0.258** |
| Asymmetry at 10 / 20 / 30 min | 0.057 / 0.242 / 0.029 | 0.058 (0.024, 0.102) / **0.257 (0.190, 0.332)** / 0.038 (0.020, 0.058); all BY-pass |
| Asymmetry at 1 h and beyond | not distinguishable from 0 | unchanged (1 h 0.005, CI -0.014 to 0.024) |
| Gap-only OOS gain, 10 min / 1 h / 6 h | +0.5% / +1.6% / +1.8% (all CIs span 0) | **+3.2% (2.3, 4.2) / +5.1% (4.1, 6.2) / +7.5% (1.2, 11.2)**; 3/3 blocks positive each; BY p 0.002 / 0.002 / 0.056 |
| Gap + Kalshi changes, 10 min / 1 h / 6 h | +5.3% (BY p 0.067) / +3.3% / +0.8% | **+8.4% (6.4, 11.3) / +7.0% (3.2, 12.7) / +6.9% (2.3, 9.8)**; BY p 0.002 / 0.002 / 0.013 |
| Polymarket adjustment share at 10 min / 1 h / 6 h | 92% / 86% / 73% | 93% / 88% (84, 92) / 78% (66, 86) |
| Large-move events, Kalshi first (of decided) | 70% | 71% (722 vs 290; mean lead 0.72 steps, CI 0.53-0.88) |
| Half-life (all / gap >= 3c) | 81 min (54-119) / 77 | 66 min (48-86) / 61 (43-81) |
| Economics, mid scenario, steps net > 0 | 14.7% | 13.8% (13.2% -> 12.7% with gap <= 15c); mean net 3.3c |

BY outcome: 16 of 20 tests pass in C1 (v1: 11). Only the lags >= 1 h of the lead-lag fail.

**Attribution** (extra descriptive runs, logged): dropping only the 9 hand-different pairs reproduces the full reversal (gap-only +3.1% / +5.2% / +8.4%,
all CIs above 0); dropping only the 16 halftime pairs leaves the v1 null (+0.5% / +1.4% / +1.6%). The v1 null was caused by the contract mismatches: a
pair whose Yes/No is inverted or whose date differs has a large spurious gap that dominates squared error and attenuates the pooled coefficient.

### 10.4 Does the finding survive?

- **Lead-lag: yes.** About 0.26 correlation, Kalshi first, 10-20 minute lead (same timestamp-convention caveat), BY-passing, and the +8.4% gap+Kalshi
  10-minute arm (v1 +5.3%) also passes.
- **v1 null on the gap: no, reversed.** The gap now predicts Polymarket's next move out of sample at all three horizons (direction: Polymarket moves toward
  Kalshi). This is a much stronger statement than v1 and is still exploratory: residual mismatches of 2-4% remain possible, the signal rests on
  the tests of this one cleaned set, and the dependence and timestamp caveats of section 6 apply. It has not been tested for economic value.
- **Economic reading is essentially unchanged**: still not a tradability estimate (section 5.6).

### 10.5 Note for E009

E009 froze its coefficients from the original v1 fit on the 341-pair set that included the 9 mismatched pairs. The cleaning materially changes
the **gap coefficient's evidential standing** (it was estimated on data where the gap looked uninformative at 1h/6h; on C1 it is informative) and
may change the fitted coefficients themselves; the lead-lag coefficient is stable. I have not refit or recompared E009's frozen coefficients; any use of
the cleaned set for E009 would need a separate future registration, and E009's committed registration must not be edited.

### 10.6 Disclosure

\`trials.jsonl\` now has 34 \`r1_\` lines (one superseded first r1 run under the labels C1_rule_only / C2_primary, which used 21 flagged pairs and
did not yet include the 4 date/inversion hand verdicts; the final run; and 2 attribution runs) on top of the 48 v1 lines. The BY family stays at 20 tests per set;
v1 and r1 are not combined into one denominator. Reproduce: \`--stage revision\`; files \`results_r1.json\`, \`results_r1_attribution.json\`,
\`audit_flags.json\`, \`audit_sample100.json\` under \`data-dumps/research_lab/cross_venue/\`.
