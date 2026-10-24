# Maker P&L held to resolution, with liquidity rewards (prior-art gaps 5 and 6)

Development study and live design, 2026-10-20/21 (branch `feat/maker-rewards`). **Development only.** Nothing here is
a registered test, nothing is counted in `trials.jsonl`, and no result is evidence of an edge. AREPO never trades;
every "maker" below is either the anonymous counterparty of a public fill or a paper quote.

## 1. Summary

- **Feasibility.** Maker P&L held to resolution can be measured honestly from public data, without books. The Data
  API serves each fill once on its taker side (`takerOnly=true`, the default). The maker is the other side of the
  same fill. A probe on 2026-10-20 matched `taker_only=true` against `taker_only=false` rows by transaction hash
  in the 5 busiest rewarded markets. In 1,399 of 1,399 fills with maker rows, the maker rows were the exact
  opposite of the taker row (size-balanced). Six more fills had no maker rows on the fetched page. This checks the feed against itself, not against the chain (see §7).
- **Coverage.** The `h2_main` and `h3_power` backfills give 8,961 resolved markets, 7,676 events and 2.33M fills
  (markets ending 2026-01 to 2026-10). That is about 800 times the 2,931 fills that CB13-T's mark-out design could
  use. CB13-T and CB16-Q were not testable because they needed a fresh book touch at fill time, or a tick grain,
  on the host's 4-day SCREEN window. A hold-to-resolution mark needs only the print and the resolution.
- **Gap 5 result (development).** Before rewards, makers are about break-even per contract in every class.
  - Non-sports, share-weighted: **+0.74c [-0.56, +2.17]**.
  - Fill-weighted: **-0.37c [-0.64, -0.10]**. The typical maker fill loses a little before rebates.
  - Takers lose roughly the fee: -0.93c [-2.36, +0.37] after the docs fee.
  - Per dollar, non-sports makers return +1.5% [-1.1, +4.5] and takers -1.8% [-4.6, +0.7]. Nothing like Kalshi's
    -9.64% vs -31.46% (Bürgi et al.) appears.
  - Crypto short-dated (up/down) makers: **-0.06c [-0.37, +0.22]** share-weighted, the same in both halves, and
    -0.58c [-0.94, -0.22] fill-weighted. The rebate adds only +0.14c.
- **One lead.** Fills more than 30 days before close (non-sports) have maker **+3.13c [+0.01, +9.62]**
  share-weighted and +1.39c [+0.04, +3.43] fill-weighted. The sign holds in h2 and h3, and it matches gap 3
  (long-horizon underconfidence). But the top 5 events hold 53% of the shares, it is 1 of about 40 cells, and it is
  not adjusted for multiplicity.
- **A methods trap, now fixed.** Averaging each event's own ratio with equal weight per event (the first draft's
  primary) is biased under a perfectly calibrated market. In simulation the bias is about +1c on class cells and
  about ±5.5c on maker-price-band cells, almost exactly the "favourite-longshot" pattern the first draft showed. Only
  pooled ratios are reported now; the per-event mean is kept in the JSON, labelled `BIASED_reference`. A unit test
  pins this.
- **Gap 6 (rewards).** Historical reward rates are not recoverable. Gamma `clobRewards` is null once a market
  closes, and the CLOB endpoints serve only current and future configurations, whose `start_date` rolls forward. A
  development snapshot on 2026-10-20 bounded the reward income of one paper quote, two-sided at minimum size:
  - 12 pairs of 2-hourly sidecar and book-sweep captures, 13,683 rewarded markets.
  - Native pool **$138k-182k per day**.
  - Median **$0.05 to $1.00 per day** (low and high bounds), on about $19 of capital. Weather pays most (median
    $0.37 to $4.61).
  - That is of the same order as one adversely selected 20-share fill (1-7c per share, ECON part B). Whether rewards
    turn the near-zero maker edge positive is therefore an empirical question about fill frequency. The live design
    in §6 answers it.
- **Recommendation.** Start the keyless reward-parameter collector, 2-hourly, before 2026-10-22. Register E025
  (provisional number; §6.2) with a fill-weighted primary. Close gap 5 as "no pre-reward maker edge" if E025 part A
  confirms the development nulls.

## 2. Sources (fetched 2026-10-19/20)

| Fact | Source |
|---|---|
| Reward score `((v-s)/v)^2·b`, `Q_one`/`Q_two`, `Q_min` with c = 3.0, two-sided only outside [0.10, 0.90], sampled once a minute at a random offset, daily UTC epoch, paid at midnight UTC, $1 minimum | https://docs.polymarket.com/market-makers/liquidity-rewards |
| Gamma `rewardsMinSize` (shares), `rewardsMaxSpread` (cents), `clobRewards[]` (`rewardsDailyRate`, `rewardsAmount`, `startDate`, `endDate`); `holdingRewardsEnabled`; `feeSchedule.{rate, exponent, takerOnly, rebateRate}` | https://docs.polymarket.com/market-data/market-details |
| `GET clob.polymarket.com/rewards/markets/current` (no auth, 500 per page, `sponsored=true` switches feed; `native_daily_rate`, `sponsored_daily_rate`, `total_daily_rate`, `sponsors_count`) | https://docs.polymarket.com/api-reference/rewards/get-current-active-rewards-configurations |
| `GET /rewards/markets/{condition_id}`: present and future configs only | https://docs.polymarket.com/api-reference/rewards/get-raw-rewards-for-a-specific-market |
| Maker rebate: daily, per market, `fee_equivalent = C·feeRate·p(1-p)`, pro rata to the market's pool; shares crypto 20%, sports 15%, most others 25%, geopolitics n/a; makers never pay fees | https://docs.polymarket.com/programs/maker-rebates.md, https://docs.polymarket.com/trading/fees |
| Data API v2 `/v2/trades`: `taker_only` default true, "each fill is served once, on its taker side"; `false` adds maker rows; `side` is "from this wallet's perspective" | https://docs.polymarket.com/api-reference/feeds/list-trades.md |
| Holding rewards 3.25% APY on listed long-dated events | `PRIOR_ART_2026-10-19.md` §2.6 (help.polymarket.com/en/articles/13364459) |

Rules changed in 2026: fees were rolled out from 01-05 to 03-30, rebate shares changed, and rewards have repeatedly
been re-dated. So the as-of reward parameters must be captured at the time; they cannot be read back later.

## 3. Feasibility and coverage

| Dataset (host `~/arepo/data-dumps/research_lab/`) | Fills? | Maker / taker identified? | Resolution? | Usable for gap 5 |
|---|---|---|---|---|
| `history/h2_main` (3,200 sampled markets, frame `frame-v2-random-windows`, no volume filter) | Data API taker prints (`side`, `outcome_index`, price, size, ts, wallet hash), up to 10k per market (41 truncated) | taker side by API semantics; maker = counterparty | frame `outcome_prices` for markets closed at fetch | **yes (used)** |
| `history/h3_power` (10,000 markets, topic-oversampled 3×, never sealed, retired from replication) | same (60 truncated) | same | same | **yes (used)** |
| `history/h1_first` (500) | same | same | same | yes (not used; small, overlaps the h2 design) |
| `history/h5_cb1`, `history/h6_weather` | same | same | same | **no: sealed** for CB1 / CB2-W (the runner refuses them) |
| `history/h7_*`, `h8_*`, `h11_*` | partial or text-only | same | partly | not needed now |
| `trade_samples/` (2h live samples) | taker prints for a sampled subset | same | needs a later resolution lookup | yes, prospectively |
| `live_trades/` (monitor, cash ≥ $1k only) | large taker prints only | same | later lookup | biased to large prints; not used |
| pmxt v2 hourly books, `history_sources/book_features` | books, no fills | n/a | n/a | queue / touch context only |
| `snapshots/*/rows_ext.csv.gz` (since 2026-10-11 12:33Z, 2-hourly) | no | n/a | n/a | **reward parameters** (Gamma native only) |
| `book_sweeps/` (2-hourly, all tokens; touch, 1c and 5c depth) | no | n/a | n/a | competing reward depth (bounded) |

Coverage of the development run (h2 + h3, 13,200 sampled markets):

| Step | Markets dropped |
|---|---|
| Not closed at fetch | 840 |
| Resolution not 0/1 (50/50 or other) | 209 |
| Trade history truncated at the 10k offset cap | 89 |
| Closed with no fill before close | 3,101 |

The run used **8,961 markets, 7,676 events and 2,333,836 fills**. A further 3,684 fills at or after close, or
invalid, were dropped. All fills are before 2026-10-12, so strictly before 2026-10-22.

Why CB13-T and CB16-Q found no fills: their designs mark the maker at a later book mid and need a book touch at most
60 minutes old at the fill time (CB13-T: 2,931 fills, of which 163 LOW / 427 NEWS passed gates needing ≥ 500 fills in
≥ 60 events) or sub-cent tick grain (CB16-Q: 125 eligible fills). Both ran on the host's 4-day SCREEN window. The
hold-to-resolution mark removes both requirements. The price is resolution latency, and a market-level rather than
a quote-level counterfactual.

## 4. Method (development)

For each fill, all quantities are in outcome-0 terms (`backend/astrolabe/research_lab/maker_rewards.py`):

- `d0` = +1 if the taker ends long outcome 0, else -1.
- `p0` is the fill price, and `y0` is 1 if outcome 0 won, else 0.
- Maker gross P&L per share is `-d0·(y0-p0)`. It is the exact negative of the taker's, before fees.
- Maker cost is the price of the token the maker bought; taker cost is the complement.
- The taker fee is the docs rate × `p(1-p)`, applied from the category rollout date (crypto 2026-03-06, sports
  02-18, others 03-30; geopolitics and `other:zero_fees` 0). The historical per-market schedule is not in the
  frames, so the fee is a secondary reconstruction.
- The maker rebate is the docs share × fee, the optimistic pro-rata assumption used in ECON part B.

**Classes.** The first match wins:

1. `sports` (reported separately; scope is the user's open decision).
2. `crypto_short`: crypto with lifetime ≤ 25h. It proxies up/down: on h3, where slugs exist, 1,605 of 1,906 such
   markets have an up/down slug.
3. `crypto_other`.
4. `negrisk_multi`: a neg-risk member of a multi-outcome event.
5. `politics_binary`: only 18 events. The random end-date frame rarely draws standalone political binaries; most
   are neg-risk.
6. `single_binary`: every other standalone binary.

Two orthogonal cuts are also reported: the fill's horizon to close (< 1d, 1-7d, 7-30d, > 30d) and the price of the
token the maker bought.

**Statistic.** Each cell reports a pooled ratio with a percentile bootstrap over events (2,000 resamples, seed
20261020), one cluster per event:

- share-weighted Σ pnl·size / Σ size;
- fill-weighted (each fill weight 1);
- per-dollar returns, each side over its own outlay.

Under a calibrated price every fill has zero expected P&L whatever predictable rule picks it, so the pooled ratios
are consistent for zero under the null. **The equal-weight-per-event mean of each event's own ratio is not.** Its
normaliser uses the event's whole future path. Under a calibrated martingale price (`p_t = Φ(W_t/√(T-t))`), it shows:

- +5.8 / -5.4c in the 0.50-0.70 and 0.30-0.50 maker-price bands, with pooled values of +0.1 / -0.1c;
- about +1.1c (s.e. 0.23) on a class cell where makers lean to favourites and trading clusters near 0.5.

The first draft's "+5.9c for makers buying 0.50-0.70" was exactly this artefact. It is now in the JSON only as
`maker_gross_c_unit_mean_BIASED_reference` and is pinned by
`test_calibrated_market_pooled_is_unbiased_but_unit_mean_is_not`. Inputs are unweighted (the h3 topic oversampling
is not undone). The top-5-event share of shares is reported for concentration.

## 5. Development results

Files: `docs/research_lab/maker_rewards_dev/pnl_h2_h3.json`, plus `pnl_h2_only.json` and `pnl_h3_only.json` for the
split-sample check, and `rewards_2026-10-20.json`. Units: cents per share; returns in % of outlay; 95% CIs.

### 5.1 Maker vs taker, held to resolution (pre-reward)

| cell | events | fills | maker gross c/share (share-wtd) | maker gross c/share (fill-wtd) | maker + rebate | taker net (after fee) | maker return %/$ | taker return %/$ | h2 / h3 share-wtd | top-5 event share |
|---|---|---|---|---|---|---|---|---|---|---|
| all_incl_sports | 7,676 | 2,333,836 | +1.08 [-0.17, +2.30] | -0.35 [-0.61, -0.08] | +1.14 | -1.44 [-2.67, -0.19] | +2.16 [-0.34, +4.66] | -2.87 [-5.33, -0.37] | +0.83 / +1.17 | 0.08 |
| all_ex_sports | 5,154 | 2,058,786 | +0.74 [-0.56, +2.17] | -0.37 [-0.64, -0.10] | +0.78 | -0.93 [-2.36, +0.37] | +1.51 [-1.14, +4.52] | -1.81 [-4.56, +0.72] | -0.16 / +1.10 | 0.11 |
| crypto_short | 2,516 | 1,217,239 | -0.06 [-0.37, +0.22] | -0.58 [-0.94, -0.22] | +0.08 | -0.65 [-0.95, -0.33] | -0.14 [-0.79, +0.48] | -1.23 [-1.80, -0.62] | -0.06 / -0.07 | 0.03 |
| crypto_other | 243 | 72,028 | +0.29 [-0.24, +0.88] | -0.24 [-1.21, +0.76] | +0.40 | -0.81 [-1.48, -0.28] | +0.61 [-0.49, +1.81] | -1.56 [-2.84, -0.54] | -0.72 / +0.72 | 0.38 |
| negrisk_multi | 881 | 343,598 | -0.90 [-2.42, +0.57] | -0.09 [-0.72, +0.59] | -0.88 | +0.81 [-0.65, +2.31] | -1.82 [-5.09, +1.13] | +1.61 [-1.27, +4.54] | -0.57 / -1.18 | 0.25 |
| single_binary | 1,496 | 414,369 | +1.90 [-0.82, +4.53] | -0.03 [-0.54, +0.52] | +1.90 | -1.91 [-4.54, +0.82] | +3.83 [-1.62, +9.38] | -3.77 [-8.92, +1.63] | +0.08 / +2.33 | 0.19 |
| politics_binary | 18 | 11,552 | not estimated (< 30 events) | | | | | | | |
| sports (flagged) | 2,524 | 275,050 | +2.02 [-0.36, +4.53] | -0.19 [-1.03, +0.66] | +2.14 | -2.83 [-5.32, -0.44] | +3.83 [-0.69, +8.56] | -5.98 [-11.27, -0.92] | +5.53 / +1.33 | 0.14 |
| ex_sports, h < 1d | 5,031 | 1,766,768 | +0.60 [-1.09, +2.46] | -0.50 [-0.78, -0.22] | +0.64 | -0.82 [-2.66, +0.88] | +1.22 [-2.18, +5.03] | -1.60 [-5.20, +1.76] | -0.58 / +0.91 | 0.11 |
| ex_sports, h 1-7d | 1,559 | 170,312 | +1.16 [-1.25, +3.81] | +0.18 [-0.55, +0.95] | +1.19 | -1.26 [-3.91, +1.15] | +2.52 [-2.69, +8.09] | -2.34 [-7.41, +2.14] | +0.87 / +1.33 | 0.19 |
| ex_sports, h 7-30d | 468 | 67,228 | +0.09 [-1.10, +1.18] | +0.45 [-0.51, +1.56] | +0.12 | -0.20 [-1.34, +0.93] | +0.15 [-2.31, +2.53] | -0.47 [-2.68, +1.84] | -0.33 / +1.00 | 0.52 |
| ex_sports, h > 30d | 174 | 54,478 | +3.13 [+0.01, +9.62] | +1.39 [+0.04, +3.43] | +3.14 | -3.18 [-9.69, -0.09] | +7.29 [+0.03, +24.35] | -5.57 [-16.46, -0.15] | +0.74 / +10.44 | 0.53 |
| negrisk_multi, h > 30d | 115 | 39,471 | +4.41 [-0.06, +13.78] | +1.26 [-0.43, +4.13] | +4.43 | -4.47 [-13.88, -0.00] | +11.07 [-0.16, +37.33] | -7.43 [-22.66, -0.01] | +0.84 / +12.16 | 0.63 |
| single_binary, h > 30d | 49 | 11,246 | +0.47 [-2.72, +2.02] | +1.66 [-0.22, +3.15] | +0.47 | -0.48 [-2.05, +2.68] | +0.95 [-5.92, +4.30] | -0.96 [-3.85, +4.97] | +0.58 / n<30 | 0.75 |

Pooled docs fee and rebate per share:

| Class | Fee | Rebate |
|---|---|---|
| Non-sports | 0.19c | 0.04c |
| crypto_short | 0.72c | 0.14c |
| sports | 0.81c | 0.12c |
| single_binary | 0.01c | 0.002c |

single_binary is low because most of its fills predate the fee rollout or have an unknown category.

### 5.2 By the price of the token the maker bought (fill-weighted is the honest column)

| maker bought | ex-sports events | ex-sports fill-wtd | ex-sports share-wtd | sports fill-wtd | per-event mean, BIASED (do not read) |
|---|---|---|---|---|---|
| p < 0.10 | 5,108 | +0.37 [-0.38, +1.18] | +1.43 [-0.29, +3.73] | +1.77 [-1.02, +6.53] | -0.03 |
| 0.10-0.30 | 3,586 | -1.83 [-3.82, +0.26] | -1.11 [-5.26, +3.23] | -1.95 [-6.14, +2.59] | -4.43 |
| 0.30-0.50 | 3,466 | **-2.48 [-4.12, -0.89]** | -0.01 [-8.67, +9.14] | -3.99 [-8.18, +0.36] | -5.25 |
| 0.50-0.70 | 3,361 | +1.04 [-0.68, +2.79] | +3.53 [-3.22, +9.87] | +1.76 [-2.45, +6.06] | +5.90 |
| 0.70-0.90 | 3,364 | +1.73 [-0.58, +4.03] | +0.11 [-3.87, +3.87] | +2.71 [-1.81, +6.90] | +4.21 |
| ≥ 0.90 | 3,815 | +0.18 [-0.75, +1.04] | -0.87 [-3.50, +0.63] | +0.76 [-0.70, +1.93] | +0.47 |

Makers who buy the token priced 0.10-0.50 lose per fill; makers who buy 0.50-0.90 gain. This is a
favourite-longshot-shaped pattern, but only the 0.30-0.50 fill-weighted CI excludes 0. That band is negative in both halves (h2 -4.13, h3 -1.94). By class (share-weighted, then fill-weighted), crypto_short makers buying ≥ 0.50 get
+1.69 [-0.22, +3.35] / +1.37 [-0.57, +3.10], and buying < 0.50 -1.56 [-3.01, +0.14] / **-1.91 [-3.44, -0.18]**.
This is the Bürgi et al. "makers buying ≥ 50c" direction, at a fraction of the size, and not significant on the
money-weighted column.

### 5.3 Reading against the prior art

| Prior-art finding | Development result here |
|---|---|
| Kalshi makers -9.64% vs takers -31.46% (Bürgi et al.; trade-equal returns, long-shot-heavy) | Dollar-weighted Polymarket returns are near zero on both sides: makers +1.5% [-1.1, +4.5], takers -1.8% [-4.6, +0.7] non-sports. The definitions differ, so this is not a contradiction, but no large maker-taker gap appears. |
| Kalshi single-name makers +1.91c (Bartlett & O'Hara) | single_binary makers have a share-weighted point estimate of +1.90c [-0.82, +4.53] (h3 +2.33, h2 +0.08) but a fill-weighted -0.03c. The point estimate agrees; the evidence does not. |
| 15-min crypto makers +$728k pre-fee in one week (Telonex, Feb 2026) | crypto_short makers are at zero share-weighted (-0.06c, CI ±0.3c, both halves) and lose fill-weighted (-0.58c). The rebate (+0.14c) does not close this. |
| ECON part B (2h mark-outs): adverse selection 1-7c per filled order | The hold-to-resolution maker P&L of all public fills is about 0. The large ECON losses came from AREPO's own signal-conditioned orders, not from passive liquidity as a whole. |

## 6. Live design

### 6.1 Reward-parameter collector (code, tests, queue draft)

- `backend/astrolabe/research_lab/reward_params_collector.py` and `backend/scripts/collect_reward_params.py`.
  - Keyless walk of `/rewards/markets/current`, native and `sponsored=true`.
  - Writes verbatim records plus `feed` into a write-once `<capture_id>/rows.jsonl.gz` and `manifest.json` (pages,
    counts, sha256, timings, state).
  - Writes to a temp directory, then renames. Refuses an existing id. A failed capture stays `failed`, and missing
    stays missing.
- Local smoke, 2026-10-20T23:01Z: complete; 14,223 native and 42 sponsored markets; about 30 requests; 0.64 MB.
- At 2-hourly cadence that is about 7.7 MB a day, about 230 MB a month.
- Queue draft `q0532_reward_params_capture_smoke` (net lane, 200 MB).
- Proposed cron line, after the smoke, for the coordinator to add to `scripts/oracle/crontab.txt`. It runs after the
  `:31` pass's sweeps finish, so each capture pairs with that pass's snapshot and sweep:
  `35 */2 * * * cd ~/arepo/backend && ../.venv/bin/python scripts/collect_reward_params.py --out-root ../data-dumps/research_lab/reward_params >> ~/arepo/run/reward_params.log 2>&1`
- **Not captured anywhere yet:** Gamma `holdingRewardsEnabled`. Recommendation: add it to the snapshot sidecar as
  `ext v4`. That is a separate, reviewed change to the live collector.

### 6.2 Pre-registration sketch: E025 (provisional number)

E023 and E024 were drafted for LT4 and then dropped, so E025 is the next number never used. The number must be
confirmed against the ledger at registration. This is a **sketch, not a registration**: it needs a challenger
review, a code freeze and a ledger entry first.

**Common elements**

| Element | Sketch |
|---|---|
| Origins | ≥ 2026-10-22T00:00Z. Fill window 2026-10-22T00:00Z to 2026-11-19T00:00Z. Markets must resolve by 2026-12-20; the fixed analysis date is 2026-12-21. Unresolved markets are reported as unavailable, never imputed. |
| Universe | Frozen sampler over the 2-hourly complete-universe snapshots. A market enters at its first snapshot in the window with `end_date ≤ 2026-12-15`, stratified by the §4 classes. The seed is fixed at registration. Sports is a separate, reported-only stratum unless the user decides otherwise. |

**Part A (gap 5, public fills)**

| Element | Sketch |
|---|---|
| Data | Every taker fill (`taker_only=true`, v2 `/v2/trades?condition=`) of sampled markets inside the window. Fetched after resolution: prints are immutable public facts, so the timing of the fetch does not matter. Truncated markets are excluded and counted. |
| Primary statistic | Per class, the pooled **fill-weighted** maker gross P&L per contract held to resolution (§4), with an event-cluster bootstrap. |
| Hypotheses | Two-sided, Holm across the 5 non-sports classes. |
| Secondary | Share-weighted values, net of rebate, per-dollar returns, horizon bands, maker-price bands (fill-weighted only), and the h > 30d lead (expected to be underpowered; descriptive). |
| Planning MDE | From development SEs, at α = 0.05/5 and 80% power: crypto_short about 0.6c at 2,500 events; single_binary about 1.5-2c at 300-800 resolving events; negrisk_multi about 2c. A census sets the final k. Classes below 60 events are "not run (power)". |

**Part B (gap 6, reward-inclusive paper maker)**

| Element | Sketch |
|---|---|
| Quote | At each 2h origin, for each sampled reward-eligible non-sports market with a two-sided book and mid in [0.10, 0.90], one paper quote: two-sided, minimum size, on outcome 0, at `s = max(v/2, half-spread)`, alive until the next origin. |
| Reward | Per market-day: the as-of collector rate × [low, high] share from the 2h book sweeps (`paper_quote_reward`). The primary uses the **low** bound. |
| Fills | Queue rule. The fill occurs when public taker volume at or through the price exceeds the displayed size ahead plus ours. A touch rule is the optimistic sensitivity. |
| Mark | Filled shares are held to resolution. Net = HTR P&L of the filled shares + reward(low) + rebate. |
| Unit | Market-day, clustered by event. |
| H6b | Markets in the top quintile of ex-ante expected reward ÷ expected adverse selection have net > 0; the bottom quintile is reported. The quintiles come from the origin-time reward bound and class-level development adverse selection, frozen at registration. |
| Gate | Part B runs only if the collector has ≥ 90% of its 2h captures complete in the window. |

**Decision rules (sketch)**

- If part A's fill-weighted maker P&L is ≤ 0 in all classes and every CI upper bound is below +0.5c, close gap 5 as
  "no pre-reward maker edge on Polymarket" in this period.
- Part B positive in the top quintile under the low-bound reward and the queue rule would be a **candidate** for an
  economic check, never an edge claim. It would then need prospective confirmation on a new window and a separate
  realism review (queue position, latency, inventory limits).

## 7. Limitations

- **Adverse selection is in, by construction.** Public fills are what makers actually got, so hold-to-resolution
  P&L includes adverse selection. But the population is all makers: professional market makers who cancel quickly,
  plus everyone else. A new paper maker would sit at the back of the queue and get the residual, worse fills, so
  realised P&L would be lower than §5.
- **Queue position is unobservable.** No public data says which resting order filled or what was ahead of it. Part
  B's queue rule uses the 2-hourly displayed size, a coarse proxy; the touch rule is optimistic.
- **Fill realism.**
  - Paper fills ignore cancellation latency and inventory limits.
  - They ignore the fact that a filled quote stops earning rewards until it is re-posted.
  - Reward-farming makers also hedge or merge positions, which is not modelled.
- **Reward bounds are wide.**
  - Sweep summary depth only gives the touch, 1c and 5c buckets, so distances are bounded.
  - The competitors' `Q_min` aggregation over unknown makers is bounded in `[(Q1+Q2)/2c, Q1+Q2]`.
  - The mid is the touch mid, not the size-cutoff-adjusted mid.
  - The book is assumed stationary over the day, against once-a-minute sampling.
  - The high bound is not realistic: it places competing depth at the far edge of each bucket.
  - Sponsored pools are absent from Gamma: 42 markets on 2026-10-20.
- **Feed truth.**
  - The maker side is inferred from Data API taker rows. The feed is internally consistent (§1), but on-chain
    truth is unaudited: CB9-S0 is pending, and Dubach 2026 reports only about 59% chain agreement for a public sign.
  - A wrong `side` flips a fill's maker P&L sign, so CB9-S0's verdict should be applied to E025 before any reading.
  - Reverted or reward-gaming matches ("Ghosts of Polymarket") and wash trades (Sirolly et al., about 20-25% of
    volume) are not filtered. Wash fills are zero-sum between colluding wallets but still enter the pooled ratio.
- **Fees.** Historical fees and rebates are a docs reconstruction. Per-market `feeSchedule` history is not in the
  history frames; the 2-hourly sidecar has it only from 2026-10-11. Crypto 15-minute fees from 2026-01-05 are not
  separated from the 03-06 all-crypto rollout. The rebate is assumed optimistically pro rata.
- **Sample.** The history frames under-represent markets that live less than a day, apart from crypto_short, and
  under-represent standalone politics (18 events). h3 topic oversampling is not reweighted. Only markets closed at
  fetch (2026-10-11/12) enter, so long-dated markets resolved since then are missing. Market-level selection is by
  end date (outcome-blind).
- **Multiplicity.** About 40 descriptive cells are shown. None is a test; the h > 30d lead is one of them.

## 8. Recommendations

1. **Collector now.** Run the q0532 smoke, then the 2-hourly cron line in §6.1 before 2026-10-22T00:00Z; otherwise
   E025 part B has no as-of reward rates. Archive the captures with the nightly rotation (small).
2. **E025.** Register part A first. It is cheap: prints are fetched after resolution and need no new live collector.
   Part B follows once the collector has 2 complete days. Wire CB9-S0's side-truth result in as a pre-stated
   adjustment.
3. **Use pooled statistics only.** Do not use equal-weight per-event ratios for any fill-level P&L in AREPO. Check
   CB1-C's "-3.84c longshot ask-selling on 62 events" and any other per-event-normalised mark-out for the same
   artefact. That is a methods check, not a relabel: past outcomes stand.
4. **Lead to carry into gap 3.** The h > 30d maker lead (non-sports, both halves positive) fits the long-horizon
   underconfidence hypothesis. Fold it into CB11-P / CH88 as a descriptive maker-route variant rather than a new
   test family.
5. **Cost-model reconciliation.** The parallel `feat/cost-model` stream (`costs.py`, uncommitted at the time of
   reading) has `maker_rebate_ps` and `maker_entry`. Once both branches merge, the fee/rebate helpers here should
   call it, so there is one fee table.
6. **Sidecar v4.** Add `holdingRewardsEnabled` (reviewed change) so that the H3c holding-reward contrast becomes
   possible.

## 9. Reproduce

```bash
# development (read-only; writes only --out); measured on the host 2026-10-20: 64 s / 247 MB and 51 s / 405 MB
python scripts/run_maker_dev.py pnl --history-root ~/arepo/data-dumps/research_lab/history --runs h2_main h3_power --out <dir>
python scripts/run_maker_dev.py rewards --research-root ~/arepo/data-dumps/research_lab --n-pairs 12 --out <dir>
# collector (keyless)
python scripts/collect_reward_params.py --out-root <dir>
# tests
cd backend && PYTHONPATH=$PWD python -m pytest -q tests/unit/test_maker_rewards.py tests/unit/test_reward_params_collector.py
```

The development runs were made from a scratch copy in `/tmp/makerdev/` on the host (read-only on `~/arepo`, deleted
after). Queue drafts `q0530` and `q0531` reproduce them durably; `q0532` is the collector smoke.
