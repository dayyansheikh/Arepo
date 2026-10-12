# Informed-flow signal theory (2026-10-12)

**Status:** theory and design only: no pipeline, no registration, no edge claim. Numbers are descriptive (field probe
2026-10-12, 37 keyless requests with the collector idle; local aggregates; `exploratory_historical` data). Signals
describe *informed-flow-consistent patterns* in public pseudonymous data; AREPO never labels a wallet or a person an
insider and is never proof of insider activity. Reported cases, including the founding Maduro example (reportedly a
new account staking heavily on his leaving office while the price called it unlikely, shortly before his capture),
motivate mechanics only and are never evidence. Names use the neutral prefix `ifx_`; wallets are HMAC hashes. Each
signal is an L0 candidate (`FEATURE_DISCOVERY_PROGRAMME.md` §3); FX ids come with the ledger note that admits it.

## 1. Mechanics: what informed flow must look like

**1.1 The trader's problem.** Someone who knows outcome `o` early maximises `S*(1 - pbar)` minus costs under four
constraints. *Convexity:* a share bought at `p` pays `(1-p)/p` per dollar, so knowledge is worth most where the market
is most wrong, usually a cheap outcome; taker fees `C*rate*p(1-p)` are also lowest there and zero in geopolitics.
*Deadline:* the edge dies at disclosure; a lone informed trader facing an uncertain disclosure time spreads orders
(Kyle 1985, Back 1992), while competitors or an imminent disclosure force fast trading (Holden and Subrahmanyam 1992).
*Capacity:* books at extreme prices are thin, so size moves price and can leak the signal to copy-traders and
whale-alert bots. *Detection:* a public ledger pushes towards fresh or multiple accounts, slicing and indirect
instruments. Each trace (convex stake, unusual identity, price-insensitive or stealthy execution, instrument choice,
timing before news) is common among innocent traders (§1.8); their conjunction is not.

**1.2 Venue.**
- *Makers and takers.* All orders are limit orders; a UI "market" order is a marketable FOK/FAK limit with a worst
  price, so one decision can produce several fills in one transaction (group by `transactionHash` and wallet).
  `/trades?takerOnly=true` gives taker rows (side = the taker's side on `asset`); `takerOnly=false` adds maker legs
  (probe: 110 extra rows sharing a taker's transaction with another wallet; there is no role field, so roles come from
  differencing the two responses). An informed trader who rests bids is invisible in taker-only data, and
  Collin-Dufresne and Fos (2015) found measured impact *lower* when informed activists trade, because they use limit
  orders in liquid periods. All current AREPO flow features are taker-only.
- *Slicing.* A parent order is split into children below alert thresholds, often at regular gaps. Signals therefore
  work on episodes (§3) and record child counts and the coefficient of variation (CV) of child sizes and gaps.
- *Buy YES versus sell NO.* The book is unified (buy YES at `p` = sell NO at `1-p`; complementary buys mint pairs).
  The exposure is the same, but a SELL needs inventory, so it closes a position: a fresh wallet can only open, and a
  fresh wallet that sells must have split or received tokens by transfer (itself a linking trace). Every trade is
  mapped to "exposure acquired on outcome `o` at price `p_o`" (BUY `o`: `p_o` = price; SELL the other outcome:
  `p_o` = 1 - price), consistent with `trade_sample._sign`.
- *Neg-risk.* 39% of open binary markets are neg-risk members. `NO_j` pays in every state except `j` and converts into
  YES of the complement, so a view "k wins" can be built from a thin `YES_k` or from liquid NOs on siblings that look
  like yield farming. Exposure must be computed per event as a payoff vector.
- *Split, merge, rewards.* SPLIT/MERGE and REWARD (liquidity rewards) activity mark market makers and arbitrageurs;
  MAKER_REBATE only means some resting order was filled, common among ordinary users (probe: types TRADE, REDEEM,
  MERGE, REWARD, MAKER_REBATE, TAKER_REBATE observed). 99.7% of open binary markets carry a reward configuration, so a
  reward-eligible *market* discriminates nothing; reward-earning *counterparties* do.
- *Proxies and collateral.* Users trade through proxy wallets (`proxyWallet`); one person can control many. Since CLOB
  V2 (2026-04-28) collateral is pUSD via the Collateral Onramp, and V2 `OrderFilled` carries maker, taker, amounts, fee
  and a `builder` code (routing app). Deposits mostly pass through exchanges, bridges and Polymarket's relayer, which
  are shared hubs: funding resolves identity only for transfers between proxies or from non-hub addresses.

**1.3 Wallet lifecycle.** Observable as of `t`: first-trade time (`/activity`, `end = t-1`, exact), profile creation
(`public-profile.createdAt`), prior trades, markets and activity types, the share of lifetime notional in one event,
the stake against the wallet's own history, dormancy, and on-chain funding time, amount and route. The
informed-consistent lifecycle: a new account, funded just before a first large bet in one event, a stake close to the
deposit, then little except redemption. Freshness alone is common: new bots (probe: a wallet 47 days past its first
trade logged 500 activities in under 72 minutes), hype newcomers and whales' alternate accounts. History is
left-censored at the Data API's coverage start, which affects "old" wallets, not "fresh" ones.

**1.4 Price impact and toxicity.** Kyle: `dp = lambda*OF + e`. Informed flow is persistent and its impact permanent;
liquidity-demand flow partly reverts. *Flow without price response* has three readings: (a) a patient informed
accumulator meeting replenished liquidity, price not yet informed (future drift); (b) better-informed makers absorbing
a wrong whale (no drift, or reversal); (c) reward farmers refilling mechanically. Only the counterparties' identity
(maker legs) and the post-burst book (depletion without refill = makers infer toxicity) separate them. VPIN uses the
known taker side, but one-sidedness is structural at extreme prices, so only deviations from own baseline count.

**1.5 Cross-market structure.** The instrument is a trace. Knowing *when* favours the nearest deadline of a ladder
("by 31 Jan" over "by 31 Mar"), the cheapest and most convex contract; knowing *who* favours YES on the winner or NO on
the favourite in a neg-risk event; needing size favours the most liquid linked market. Exposure that points coherently
at one latent outcome across markets is informative; hedged exposure (arbitrage, market making) is not.

**1.6 Timing.** Informed flow precedes the earliest public report; news-followers come after it. GDELT `seendate` is a
conservative proxy for that clock; X, Telegram and local-language press are faster and not collected, so "news
silence" has false positives. Scheduled announcements (awards, decisions, earnings calls, launches) open a
decision-to-announcement window in which leaks concentrate. Hour of day against the market's own activity profile
and the decider's time zone is a weak modifier.

**1.7 Information-asymmetry classes** (versioned rule on metadata only, hashed before any outcome is seen).
- **A**, few deciders and decision before disclosure: awards and honours, pre-recorded shows, organisational
  announcements and launch dates, listings, government and military actions, appointments, pardons, sanctions, court
  rulings with a set date, mention markets and other speaker-controlled counts.
- **B**, many actors with partial insiders: vote counts, negotiations and meetings, embargoed statistics, resignations
  and health of public figures.
- **C**, public process: sports results, crypto and financial prices, weather, continuous public observables.

Inputs: `question`, slug, `groupItemTitle`, event title, tags, `series_slugs`, `fee_category` (snapshots hold none of
the text today); unmatched markets stay `unclassified`. Fee-free `fee_category` "unknown" is geopolitics (military
action, next leader out, summit venues; 694 active markets). Sports scope is open, so class C stays as a contrast.

**1.8 Innocent look-alikes.**

| Look-alike | Fingerprint | Separating evidence |
|---|---|---|
| Conviction whale (e.g. the 2024 multi-account election whale) | large, liquid flagship markets, mid prices, long history | age, breadth, price band, class B/C |
| Hedger | steady sizes, long-dated, related real-world exposure | no timing link to news; established wallet |
| Market maker, reward farmer | two-sided; SPLIT/MERGE, REWARD; many markets | activity types, `mergeable` positions, two-sidedness |
| Arbitrage bot | legs across siblings or venues | flat event payoff vector (`kappa` ≈ 0) |
| News-follower | after the earliest report; many wallets join | lead time, news burst, breadth |
| Coordinated retail, fandom | many small same-side wallets, social spike | stake per wallet, age, comment growth, later reversal |
| Copy-trading bot | small same-side trades seconds to minutes after a tracked wallet | lag to the leader (the leader carries the signal) |
| Wash or volume farming | round trips, linked maker and taker, net exposure ≈ 0 | net exposure, maker = taker cluster |
| Resolution or certainty buyer | favourites ≥ 0.9 after the outcome is public | price band, UMA state, post-news timing |
| Manipulator | wrong-way size in visible thin markets; impact reverts | not separable ex ante; outcome labels, persistence |

## 2. Data reality (probe 2026-10-12; local aggregates)

| Source | Signal-relevant content | Live | Historical |
|---|---|---|---|
| AREPO trade sample (2h, 2,000 active markets, 500 newest taker trades, hashed wallets) | ts, side, price, size, outcome, tx, wallet. About 10% of sampled markets hit the 500 cap; median stake $8, p99 $1k; 9-15 stakes ≥ $1k at `p_o` ≤ 0.15 per 24h, almost all politics or geopolitics | yes | from 2026-10-11 |
| Gamma complete snapshot (2h) | mid, liquidity, volume24hr, event and neg-risk ids, end date, fees, rewards, `series_slugs`, comment count; 18,335 active binary markets in 5,433 events | yes | no (end-of-life values) |
| Book sweeps (2 per pass) | touch, depth within 1c and 5c (eligible tokens) | yes | pmxt v2, 2026-04-13 to 08-10 |
| Data API `/trades`, `/v2/trades` | adds `proxyWallet`, `transactionHash`, `eventSlug`. `filterType=CASH&filterAmount` works globally: 500 trades ≥ $1k span 94 min (177 markets); ≥ $10k span 10.1 h. v2: `token_id`, `pagination.next_cursor` (completeness unverified), no builder field | yes | per market; `start`/`end` windows (`event_study`) |
| `/activity?user=` | types above, `usdcSize`, as of `end`; SPLIT and CONVERSION filters accepted but unconfirmed; no deposits | yes | yes, left-censored |
| `/positions`, `/holders`, Gamma `public-profile` | avgPrice, totalBought, `mergeable`, `negativeRisk`; top 20 holders per token; `createdAt`, `takerTier`, `weightedVolume` | current state only (point in time at request) | `createdAt` only |
| Polygon, keyless | publicnode: receipts work (one trade transaction: 20 logs, including ERC-1155 and exchange events); `eth_getLogs` works over the last 20 blocks (1,410 USDC.e transfers) and is refused from 1,000 blocks (archive token required); drpc free plan refused; Blockscout 403; polygon-rpc.com 401 | head window only | **not keyless** |
| GDELT DOC (`external_news.py`) | `seendate`, counts, tone | yes | re-processed: development only |

Two cautions. (1) `HISTORICAL_ML_DEV.md` found no average-case value for the wallet family, but an ablation over 98k
origins cannot see rare episodes and its "new-to-sample" wallets were left-censored: that null neither refutes nor
supports this programme. (2) The h2_main random sample (3,200 markets, 263 days) holds only 55 BUY episodes ≥ $1k at
VWAP ≤ 0.15 (22 markets, 19 events); 19% of the 48 labelled reached `max(2*vwap, vwap+0.10)` within 7 days. Only a
census of large trades can supply this target. The rate is a power input; no signal or control contrast was computed.

## 3. Ranked candidate signals

**Notation (point in time).** A value enters at `t` only if its source time is `< t` and AREPO received it by `t`.
Trade `i`: wallet `w`, outcome acquired `o`, price `p_o`, shares `s`, stake `n = s*p_o`. Episode `E`: maximal run of
one wallet's (or cluster's) trades acquiring the same `o` in market `m`, with gaps ≤ 2h; `S_E`, `n_E`,
`pbar_E = n_E/S_E`, start `t_E`. `L_m`: Gamma liquidity at the last snapshot before `t`; `D_o`: ask depth within 5c on
`o` at the last book before `t_E`; `V_m`: median daily notional over `[t-15d, t-1d)`; `v_o(t)`: mid of `o` at the
last snapshot or book before `t`; `G`: the event (neg-risk siblings and deadline ladder). "Live" = current AREPO
collection or a cheap addition (§6); "hist" = free keyless history.

1. **`ifx_convex_stake`** (F01-like). `X1 = S_E*(1 - pbar_E) / max(L_m, 100)`: profit if right, in units of market
   liquidity, reported by band `pbar_E` ≤ 0.05/0.10/0.20/0.35. Live: trades + snapshots (census needed for slicing);
   hist: Data API trades with `V_m` in place of `L_m`. Look-alikes: lottery buyers (tiny `X1`), hedgers and contrarian
   whales (old wallets, liquid markets), manipulators (outcome labels only). Drift towards `o` until disclosure
   (24h, 7d, resolution).
2. **`ifx_fresh`** (F03/F04). `age_w = t_E - first_trade_w` < 14d and prior trades `k_w` < 100 (excludes new bots);
   also profile age and `ifx_first_big = 1[n_E ≥ every earlier stake of w]`. Live and hist: `/activity` ascending,
   `limit=1`, `end=t-1` (1 request per wallet, cached; `history_sources.run_wallet_step` does this for history).
   Look-alikes: new bots (`k_w`, market-maker activity), hype newcomers (small stakes, news bursts), whale alternate
   accounts (breadth, mid prices), sybil farmers (net ≈ 0). No direction alone; it gates `X1`.
3. **`ifx_focus`** (F34-like). `F = notional of w in G before t / all notional of w before t`, distinct markets
   `M_w`, and `n_E / median earlier stake of w`. Live: `/activity` (≤ 3 pages), `/positions`; hist: `/activity`.
   Look-alikes: fans and partisans (many small, older wallets), per-market whale accounts (large but in liquid
   flagship markets). Modifier.
4. **`ifx_aggression`**. Within `E`: price levels crossed, price walk `p_last - p_first` while still buying, depth
   consumed `S_E / D_o`, slicing (children, CV of sizes and gaps). Live: trades + books; hist: pmxt (Apr-Aug 2026).
   Look-alikes: impatient whales, liquidations, arbitrage legs (hedged elsewhere), post-news buyers. Drift towards
   `o`, hours to days. Blind to patient limit-order informed trading (see 10).
5. **`ifx_persist`**. For a burst `B` (top 1% of the market's 15-min signed notional) ending ≥ 30 min before `t`:
   `P = (v_o(t) - v_o(B_start-)) / (v_o(B_end+) - v_o(B_start-))`; NaN unless ≥ 3 trades or book updates follow `B`
   (stale books persist mechanically). Live: snapshots (coarse), event-triggered books; hist: prices-history (10 min,
   +600 s lag). Look-alike: news bursts also persist (news gate). Continuation, 24h-7d.
6. **`ifx_cluster`** (F35). Components over wallets active in `G` in `[t-24h, t)`, with edges for (a) transfers
   between proxies, (b) a shared non-hub funder, (c) both fresh, same market and side, first trades within 48h,
   trades within 30 min, stake ratio in [0.5, 2]. Features: component size, combined `X1`, side coherence. Edge (c) is
   keyless now; (a) and (b) need on-chain data (§2). Look-alikes: chat groups (older, small), copy bots (lagged,
   small; their leader carries the signal), sybil farmers (shared funder, round trips, many markets). Drift towards
   the cluster's side.
7. **`ifx_funding`**. Lag from first inflow to first trade and from last inflow to `t_E`; `n_E / inflow`; funder
   class (exchange, bridge/onramp/relayer, another proxy, fresh EOA < 7d, established EOA) from a frozen versioned hub
   list. On-chain only: live head-window watcher; history needs a keyed source. Look-alikes: ordinary newcomers also
   deposit and trade at once; hub-funded wallets are unresolved (NaN, never "clean"). Modifier.
8. **`ifx_coherence`**. For `w` over `[t-6h, t)` across `G`: `g_k` = net profit if state `k` occurs (`YES_k` pays in
   `k`, `NO_j` in every state except `j`, minus cost); `kappa = (g_(1) - g_(2)) / (g_(1) - g_min)` in [0, 1], 0 if
   `g` is flat (two states: 1 minus the hedge ratio); `ifx_route = 1[the instrument used had the highest payout per
   dollar for that view]`. Live: census of siblings, neg-risk ids, CONVERSION/MERGE activity; hist: Data API per
   sibling. Look-alikes: arbitrage and market making (`kappa` ≈ 0), "NO on every longshot" yield farmers (prices
   ≥ 0.95, many events). Drift towards `argmax g`.
9. **`ifx_term`**. Ladder `d1 < d2` in one event, `N = v(by d1)/v(by d2)`, which decays if nothing happens. With
   `Nc(u) = (1-exp(-h*(d1-u))) / (1-exp(-h*(d2-u)))` and a constant hazard `h` fitted to `v(by d2)` at `t-6h`:
   `R = (N(t) - N(t-6h)) - (Nc(t) - Nc(t-6h))`, `z = R / sd(R over the prior 14 days)`. Live: snapshots (complete,
   now) plus ladder metadata (`groupItemTitle`, question: not stored yet); hist: prices-history. Look-alikes: public
   news of imminence (news gate), stale near-dated quotes (needs trades or a book change), inconsistent ladders
   (`N` > 1: E005-type arbitrage). Near-dated YES drifts up and resolves by `d1` more often than priced.
10. **`ifx_stealth`** (F33-like). Over `[t-24h, t)`: `OF3` = net shares on `o` of the 3 largest net acquirers;
    `lambda_m` = OLS slope of 15-min `dv_o` on 15-min signed shares over `[t-15d, t-1d)` (≥ 30 non-empty intervals);
    `stealth = 1 - dv_o(24h) / (lambda_m*OF3)`, scored where `OF3*v_o/L_m` ≥ its class 95th percentile. Pre-declared
    moderator: share of absorbing maker volume from wallets with REWARD activity in 30 days. Live: census with
    maker legs; hist: Data API + prices-history. Look-alikes: reward farmers refilling, a wrong whale absorbed by
    better-informed makers (moderator and sign). Continuation, 24h-7d.
11. **`ifx_vpin`**. Buckets of `V_m/50` notional; `VPIN = mean |B-S|/bucket` (taker buy and sell notional) over the
    last 20 buckets, z against the market's own previous 30 values; lag-1 autocorrelation of signed bucket imbalance.
    Live: census; hist: Data API. Look-alikes: news-driven one-sidedness, resolution buying, structural one-sidedness
    at extremes (own baseline). Continuation, hours to 1d. Must add beyond E007 `signed_share` and `flow_imb_*`.
12. **`ifx_retreat`**. Ask depth within 5c on `o` 15 min after a burst over depth before; spread ratio. Live: event
    books (new); hist: pmxt. Look-alike: quotes pulled before scheduled news or at night. Continuation, hours.
13. **`ifx_open`**. Share of `S_E` that opens exposure (no prior holding of the other outcome by `w`). Live: census
    history, `/positions`; hist: `/activity`. Look-alike: hedgers also open. Modifier.
14. **`ifx_preannounce`**. Markets with a scheduled announcement `T_a` (frozen parser on description and end date):
    net directional stake in `[T_a-72h, t)`, z-scored on the market's own daily net stake in `[T_a-30d, T_a-72h)`.
    Look-alikes: pre-announcement attention (use concentration, freshness), public forecasts. Towards the outcome.
15. **`ifx_quiet`**. `1[ext_news_ratio_6h ≤ 1.5 and ext_news_n_1h ≤ 1 and the event's 6h comment growth ≤ its own
    75th percentile]`. Live only. Look-alike: fast news outside GDELT (false quiet). A gate, never standalone.
16. **`ifx_record`** (F06/F34/F55). Empirical-Bayes shrunk mean of `Y_j - pbar_j` over `w`'s class-A episodes
    resolved before `t`, with count. Needs AREPO resolution labels. Look-alikes: luck (shrinkage), public-information
    skill (predictive but no evidence of non-public information; reported separately). Complements `ifx_fresh`.
17. **`ifx_dormant`**. Last activity ≥ 60 days before `t_E` and `n_E` ≥ the wallet's earlier maximum stake. Live and
    hist: `/activity`. Look-alike: users returning for big news. Modifier like `ifx_fresh`.
18. **`ifx_offhours`**. `-log((v_ch + 1) / (sum_h v_ch + 24))` for the UTC hour `h` of `t_E`, where `v_ch` is class
    notional in hour `h` over the prior 30 days; plus a frozen decider-time-zone night flag. Weak modifier.

Rank = prior plausibility × separability from look-alikes × point-in-time cleanliness and cost: 1-4 are the founding
pattern and cheap; 5-9 add independent families; 10-12 need maker legs or event books; 13-18 are modifiers.

## 4. Composite designs

**Principles.** (1) Positives are rare and unlabelled while candidate episodes are plentiful, so model the null:
thresholds are quantiles of the candidate-episode distribution in development data, never tuned on outcomes.
(2) Evidence counts by independent family, not by correlated indicators (the lesson of v1 `analytics/flow.py`): edge
(1, 4), identity (2, 3, 6, 7, 16, 17), context (class, 14, 15), market response (5, 10-12), structure (8, 9).
(3) Each family alone is mostly look-alikes; informedness lives in the conjunction. Composites are therefore gates,
and a gated set is ranked by one pre-declared quantity, never by hand-set weights.

**IFC1, episode level (primary): fresh or focused × convex stake vs liquidity × extreme price × high asymmetry.**
- Gates: class A or B; `pbar_E` ≤ 0.20 (variant 0.35); `n_E` ≥ $1,000 and `X1` ≥ the 99th percentile of the
  class-and-price-band null; identity = `ifx_fresh` or `ifx_dormant` or (`F` ≥ 0.8 and `M_w` ≤ 3), at wallet or
  cluster level.
- Vetoes (as of `t`): REWARD or MERGE activity in 30 days, ≥ 20 markets in 7 days, or `mergeable` positions in ≥ 3
  markets (MAKER_REBATE share is a stratum, not a veto); `kappa` < 0.5; UMA proposal open or end date passed; news
  burst (`ext_news_ratio_1h` ≥ 3, live only); `v_o` already up ≥ 0.15 in the 2h before `t_E` (news or momentum).
- Rank by `X1`; budget 10 alerts per ISO week, one per (event, outcome). Signals 4-7, 13-15 and 18 are recorded as
  pre-declared strata for secondary analysis, never used to rank.

**IFC2, market level: stealth accumulation.** Class A or B; `stealth` ≥ 0.75 with `OF3*v_o/L_m` ≥ its class 95th
percentile; `ifx_vpin` z ≥ 2; `ifx_quiet`; IFC1 vetoes. Rank by `OF3*v_o/L_m`.

**IFC3, event level: instrument choice.** `ifx_term` z ≥ 2 with `ifx_quiet`, or `kappa` ≥ 0.7 across ≥ 2 markets
with stake ≥ $1,000. Ranked separately by `z` and by `kappa*stake/L_m`.

**Rules or learned models.** Rules for anything registered: few parameters fixed by theory and null quantiles,
auditable, no labels needed. Unsupervised surprise for development: per-family tail probabilities under strata nulls
(class × price band × liquidity tercile), combined by Fisher's method, to check that each gate adds selectivity. A
supervised ranker is trained only on mechanical labels (§5.2) over all candidate episodes, never on reported cases. It
becomes a challenger once ≥ 300 positive-label episodes over ≥ 100 events exist, and replaces a rule only if its
precision@k beats the rule on later blocks with a CI excluding 0 (the programme ladder and the A-ML1 logic).

**Hand-off to `UNUSUAL_FLOW_PROGRAMME.md` batch 2 (≤ 2 variants).** Its canonical panel is market-level on a 2h grid
(`imb_s`, `burst`, `large_trade_rel`, `top1_share_l`, `new_wallet_share_l`, `mid`; no liquidity, no true wallet age),
so IFC1 maps only approximately. The two most distinct theory variants, each needing one derived column at `t`:
(a) *convex longshot pressure* (§3.1, IFC1 gate): `p_acq = mid if imb_s > 0 else 1 - mid`; conditions `n_s ≥ 3`,
`p_acq ≤ 0.20`; terms `imb_s` (abs), `large_trade_rel` (log1p), `top1_share_l` (raw); direction `imb_s`. (b) *pressure
without price response* (§3.10, IFC2): `resp_s = sign(imb_s) * (mid - mid 2h earlier)`; conditions `n_s ≥ 3`; terms
`imb_s` (abs), `top1_share_l` (raw), `resp_s` (raw, negative weight). Centres and scales follow that programme's
tuning rules; its declared evaluation (top 1%, 24h, δ = 0.10, 5 controls, Holm) is the historical analogue of §5.

## 5. Evaluation for rare events

**5.1 Unit and clock.** Unit = candidate episode (any class, `n_E` ≥ $500) built only from data received by the alert
time `t_a`, the receipt time of the last input that completed the gate (trades and wallet lookups); detection latency
`t_a - t_E` is reported. Universe = every class A/B episode (census) plus a probability sample of class C with
recorded inclusion probabilities. Primary analyses keep the first alert per (event, outcome) per 7 days.

**5.2 Labels** (`v_o` from the first complete snapshot at or after the time, or the payout once resolved). Primary:
`hit = 1[v_o(t_a+7d) - v_o(t_a) ≥ 0.10]`. Continuous: `D_7d`, `D_24h`. Resolution excess `Y_o - p_cal(t_a)` with the
frozen recalibration map (ledger calibration study C1, T5-DEV), for markets resolving within 90 days. Barrier labels
are descriptive only: by Doob's inequality a martingale started at `p` reaches `2p` with probability up to 1/2, and
the development rate was 19%. The 7-day horizon keeps the test feasible; the resolution label covers slower news.

**5.3 Base rates and matched controls.** `pi0` = hit rate of all candidate episodes in the same stratum (class ×
price band × `X1` tercile × time-to-end band × week). Each alert gets up to 5 controls from the same class, price
band and week, nearest in `log X1` and time to end, that pass the same vetoes and fail *only* the identity gate
(established, unfocused wallets), isolating identity; a second set fails only the size gate. Under efficient prices
`E[D] = 0`; the favourite-longshot bias makes it negative for longshots, which the controls absorb.

**5.4 Precision at a fixed budget.** Primary metric: precision@10 per week (share of alerts with `hit`; k = 5 and 20
secondary). It is contrasted (i) with matched controls (difference, event-clustered bootstrap, one-sided) and (ii)
with the naive ranker (top 10 per week by `X1` without identity gates and vetoes, paired by week); if identity adds
nothing, (ii) shows it. Report the lift `precision/pi0`, mean `D_7d` and the loser share. AUC and PR-AUC are
reported, never decisive.

**5.5 Lead time.** For hits: `lead_price` = first snapshot meeting the hit condition minus `t_a`; `lead_news` =
earliest GDELT `seendate` of a matching article minus `t_a`, plus a pre-declared manual search (fixed source list,
same procedure for alerts and controls). Report the median, the IQR and the share with lead ≥ 2h. An alert after the
earliest report is a news-follower, whatever its outcome.

**5.6 Reported cases.** They are known because they won, were large, and were found with the very features under
test (fresh wallets); their timestamps are reconstructed afterwards. So they never train, set thresholds or choose
features; they serve only as a recall audit (`CASE_CATALOGUE.md`, held out, with quiet-case controls: would IFC1, run
as of the time, have fired, and when?). Precision always uses the full candidate universe, losers included.

**5.7 Multiple testing.** Confirmatory family = the three hypotheses of §7, one primary each, Holm at α = 0.05.
Variants (age 7/14/30d, price 0.10/0.20/0.35, k, horizons, class B in or out) are secondary, BY-screened at q = 0.10
on the cumulative trial count, one `trials.jsonl` line each. Development = historical episode censuses of class A/B
markets chosen by metadata only (`exploratory_historical`, at most L2) plus pre-registration live data; confirmation
= alerts with `t_a` after the registration commit.

**5.8 Placebos.** Side flip (the other outcome's `D`); pre-trend (`D` over `[t_a-7d, t_E]` as a covariate); identity
shuffle within strata (precision should fall to the naive ranker's); alert time shifted by +7 days.

**5.9 Power.** Two-sample binomial, `pi0` = 0.10, one-sided α = 0.05, power 0.8, 60 alert events (12 weeks × 10, ~2
per event), ~150 effective controls: detectable precision ≈ 0.22 (lift ≈ 2.2); if informed episodes are rarer the
verdict is "inconclusive". Recompute with the measured `pi0` and clustering (`power.py`) before registering.

## 6. Minimal live collection to start now

| ID | Data | Cadence | Requests/day | Stored/day | Needed by |
|---|---|---|---|---|---|
| N1 | Global large-taker feed: `/trades?takerOnly=true&filterType=CASH&filterAmount=500`, paged until overlap | 10 min | ~300 | ~2 MB | all; alert latency ≤ 10 min |
| N2 | Class A/B taker census: `/v2/trades` global cursor from the head every 2 min, keeping class A/B rows and a 5% recorded sample of the rest. Fallback: per-market incremental `/trades?market=` every 2h for the ~5,000 class A/B markets with volume24hr > 0 | 2 min (fallback 2h) | 1-3k (fallback ~60k) | 10-25 MB | IFC1 slicing, IFC2 (14-day burn-in for `lambda_m`), 11 |
| N3 | Maker legs (`takerOnly=false`) for markets with a candidate episode ≥ $500, at detection and +2h | event | ≤ 1k | < 2 MB | IFC2 moderator, 4, wash check |
| N4 | Wallet enrichment for wallets with an N1 trade or a class A/B episode ≥ $500: first TRADE (`end=t-1`), one `/activity` page, `public-profile`, `/positions`; first trade cached forever, the rest refreshed at most daily | queue | 5-15k, falling | < 5 MB | 2, 3, 13, 17, vetoes |
| N5 | Event-triggered books: token `/book` at detection, +15 and +60 min; siblings' `/books` at detection; for gate passes and class A/B prints ≥ $2,000 | event | ≤ 2.5k | ~5 MB | 4, 5, 12 |
| N6 | Market text for the class rule and ladders (`question`, slug, `groupItemTitle`, event title, tags, description hash), once per new market, from pages already fetched where present | snapshot | 0-200 | ~5 MB | class gate, 9, 14 |
| N7 | GDELT DOC query per gate pass (existing module, 10 s spacing) | event | ≤ 200 | < 1 MB | 15, lead time |
| N8 | Optional: keyless pUSD mint and Transfer watcher on the last ≤ 20 blocks (publicnode), then USDC/USDC.e inflows into each newly funded proxy (≥ $500) in the same window | 30 s | 3-6k | < 5 MB | 6, 7 |

Totals (preferred path): ~15-30k requests/day (< 0.4/s, far below published limits), ≤ 40 MB/day stored (~1.2 GB a
month), ≤ 1 GB/day transferred; free disk is 16 GiB and the collector stops below 4 GB. Daily global trade counts are
unmeasured, so N2 figures are bounds. Priority: **P0** N1, N4, N6 (IF-H1 on large prints, IF-H2); **P1** N2, N3, N5,
N7; **P2** N8. The 2,000-market sample, E007 and the detector's `alerts.jsonl` path stay unchanged.

Rules: every job yields to `arepo_pass.sh` via `pgrep -f '^[^ ]*sh [^ -][^ ]*arepo_pass\.sh'` (a loose `pgrep -f
arepo_pass.sh` also matches waiting shells that mention the name); no two multi-GB jobs at once; raw addresses in
memory only, HMAC hashes on disk, no names, bios or images; the hub list holds only public infrastructure addresses.
Historical funding traces need a keyed explorer or an archive RPC: a credentials decision for the user.

## 7. Top three hypotheses to pre-register first

**IF-H1 (IFC1): convex stakes from fresh or focused wallets in high-asymmetry markets.** Among class A/B episodes
built from taker prints ≥ $500 (N1, N4), the weekly top 10 by `X1` that pass the IFC1 gates have a higher 7-day hit
rate than matched controls that fail only the identity gate. Primary: precision@10 minus the matched-control hit rate,
event-clustered, one-sided. Secondary: against the naive ranker; `D_7d`; resolution excess; lead time. *Why first:*
it is the founding pattern and follows from §1.1 (convexity, deadline, detection); it separates the main look-alikes
(whales, market makers, bots, hype newcomers) with features observable as of `t`; it needs only P0 data (one
`/activity` request per new wallet); and it asks what the h2_main wallet null could not: does identity add to size
and price in the rare tail?

**IF-H2 (IFC3, `ifx_term`): timing information in deadline ladders.** In class A/B ladders, a decay-adjusted near-term
share residual `z` ≥ 2 over 6h without a news burst predicts the near-dated contract's 7-day drift and its resolution
excess. *Why:* someone who knows *when* buys the cheapest, most convex near-dated contract, so the trace is in relative
prices, which AREPO already captures for the whole universe every 2 hours. No wallet data is needed, the look-alikes
(decay, public news, stale quotes) are controllable, and it can be developed now on prices-history. Needs N6.

**IF-H3 (IFC2): stealth accumulation.** In class A/B markets, concentrated net acquisition with a price response under
a quarter of what the market's own `lambda` predicts is followed by 24h and 7-day continuation beyond E007
`signed_share` and the frozen reversal, with the reward-earning-maker share as the one pre-declared moderator. *Why:*
Kyle and Collin-Dufresne-Fos imply that the most skilful informed traders leave little price footprint, so detection
must rely on cumulative concentrated flow, not impact. It covers what IF-H1 misses (patient limit orders, mid prices,
established wallets), and the moderator tests the maker-refill story. Needs N2, N3 and a 14-day burn-in.

## 8. Open items and non-claims

- Next hypotheses: `ifx_cluster` once N8 or a keyed source exists; `ifx_preannounce` once schedules are parsed.
- User decisions: a keyed on-chain source for historical funding traces (credentials); sports scope (class C contrast).
- Verify in development: `/v2/trades` cursor completeness against per-market pulls; SPLIT and CONVERSION activity
  types; the V2 `OrderFilled` layout and `builder` code from receipts; the pUSD onramp mint pattern; the size of the
  publicnode head window.
- Non-claims: patterns, not people; no wallet is ever called an insider; no trading, profitability or calibration
  claim. An economic check (L5) is separate and later. Development data reach L2 at most.
