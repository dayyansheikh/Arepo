# Signal-engine family `wallet_skill` (causal skilled-wallet flow)

Research tooling only. Nothing here trades, labels a wallet as informed or insider, or claims an edge. Wallets are HMAC
hashes (`wallet_sidecar.hash_wallet`, key on the host only); no raw address is read, stored or printed.

- **Code:** `backend/astrolabe/research_lab/wallet_skill.py` (profiles, skill statistics, market features, engine
  adapter), `backend/astrolabe/research_lab/wallet_skill_dev.py` (development evaluation),
  `backend/scripts/run_wallet_skill.py` (`dev` and `host-dry-run`).
- **Tests:** `backend/tests/unit/test_research_lab_wallet_skill.py`.
- **Prior art:** `PRIOR_ART_2026-10-19.md` gap 7 (Gómez-Cram, Guo, Jensen & Kung 2026: sign-randomisation, 3.14% of
  accounts skilled, 44% stay skilled out of sample; Akey et al.: persistence weak or modest, contested) and gap 1
  (informed long-shot buys). AREPO history: HB1 wallet family WA1-WA8 (freshness, HHI, prior-winner/loser) null in HB1,
  HB1-R and the h3 first-trade re-run; WA6 prior-winner flow the closest miss (+0.28c/SD, BY 0.18). E007: generic flow
  continuation is real but small (+0.36c per fully one-sided hour), so any wallet signal must beat generic flow.

## 1. Definitions

Per trade *i* (taker print from the Data API): direction `d = +1` BUY / `-1` SELL of outcome `k` at price `p` for `size`
shares. Realised P&L at resolution `x_i = d (payout_k - p) size`; cash at risk `c_i = size p` (BUY) or `size (1 - p)`
(SELL); price-implied win chance `c_i / size`.

A **position** is all of a wallet's trades in one market (they share one outcome). It is kept as six additive sums
(`A0`, `A1`, `B`, cost, shares, n) so the outcome is applied only once it is known: `x_g = A0 pay0 + A1 pay1 - B`.

Per wallet, over its resolved positions `g = 1..n`:

| field | definition |
|---|---|
| `n_pos`, `n_trades` | resolved positions, trades in them |
| `pnl`, `cost`, `ppd` | `sum x_g`, `sum c_g`, P&L per dollar at risk |
| `hit_rate`, `implied_rate` | `mean[x_g > 0]`, `mean(c_g / shares_g)` |
| `calib_excess` | `mean(x_g / shares_g)`: share-weighted win minus price-implied chance, averaged over positions |
| `skill_z` | sign-randomisation statistic `pnl / sqrt(sum x_g^2)`. Under H0 each position's direction is a fair coin, so `S* = sum e_g x_g` has mean 0 and variance `sum x_g^2` exactly; `sign_flip_pvalue` gives the exact (n <= 16) or Monte-Carlo one-sided p |
| shrinkage | `skill_score = skill_z sqrt(n / (n + 10))`, `ppd_shr = ppd n / (n + 10)`, `calib_shr = sum(x_g / shares_g) / (n + 10)` |
| `eligible` | `n_pos >= 5` |
| **skilled set at t** | eligible wallets with `skill_z > 0` whose `skill_score` is in the top 10% of eligible wallets |

The flip unit is the market position (all trades in one market move together). Event-level flips (one unit per
wallet x event, for correlated sibling markets) are a batch sensitivity in the development study.

## 2. Point-in-time rule

- A profile as of `t` uses only positions in markets whose outcome was **known strictly before `t`**. Live: known =
  receipt time of the Gamma fetch that showed the final price vector (`resolutions_from_engine_log`). History: known =
  `closedTime + 48 h` (HB1 rule; `RES_LAG_S`). Final vectors only: (1, 0), (0, 1) or the 50/50 split (pays 0.5).
- Every trade of a resolved market precedes its close. `ProfileBuilder.advance_to(t)` refuses if a trade at or after
  `t` was ingested (unless the caller guarantees every trade precedes its market's close; the history study drops
  post-close prints for that reason).
- Market features at an origin use trades with `ts < t_cut` and the skilled set of a snapshot taken at or before the
  origin (daily snapshots at 00:00Z; the snapshot of day D uses outcomes known before D 00:00Z).
- Incremental = batch: `ProfileBuilder` (daily ingestion of trades and outcomes) reproduces `build_profiles_batch`
  exactly (tested on random data to 1e-9).

## 3. Market-level features (family columns, float32 in the engine, NaN = missing)

Windows `[t_cut - W, t_cut)`; signs point to outcome 0 (BUY outcome 0 or SELL outcome 1 = +1); shares are divided by
the window's total notional (all wallets); a covered window without trades gives 0; a window that starts before the
oldest trade of a full (possibly cut) trade page is NaN.

| column | meaning |
|---|---|
| `ws_has` | a wallet source was present for the market |
| `ws_net1h`, `ws_net6h`, `ws_net24h` | net signed notional of skilled wallets / total notional |
| `ws_share24` | skilled wallets' share of 24 h notional |
| `ws_nskill24` | log(1 + distinct skilled wallets buying in 24 h) ("entering") |
| `ws_ls24` | net signed notional of skilled long-shot buys (BUY at `p <= 0.35`) / total notional (gap 1) |
| `ws_zflow24` | `sum dir x notional x clip(skill_score, -3, 3) / total notional` over eligible wallets (continuous variant) |
| `ws_cov24` | share of 24 h notional from eligible (profiled) wallets (coverage diagnostic) |

`gen_net1h/6h/24h` (all wallets, same clock) are the generic-flow comparators; they are not family columns (the engine's
`flow` family already carries generic flow).

## 4. Data coverage

| source | wallet | side | timestamps | resolution | use |
|---|---|---|---|---|---|
| `history/{h1_first,h2_main,h3_power}/trades` (HB1) | HMAC hash | yes (taker) | venue ts | `sample.csv` final prices + closedTime | development profiles and evaluation |
| `trade_samples/<id>/wallets.csv.gz` (2 h, newest 500 taker trades per sampled market, active frame) | HMAC hash (same key file) | yes | venue ts, origin = row receipt | via the engine's Gamma resolution log | live profiles + features |
| `live_trades/trades-*.jsonl` (>= $1k taker prints, since 2026-10-12) | HMAC hash | yes | venue + receipt | Gamma (separate fetch) | possible extra live input (not used here) |

All are taker-only: the skill measured is taker skill. Makers (the main winners in Akey et al.) are invisible. Profiles
cover only the sampled markets, so a wallet's record is its record on AREPO's samples, not its whole history.

## 5. Development evaluation: declaration (written before any result was computed, 2026-10-20 23:30Z)

Label: **DEVELOPMENT, exploratory_historical** (HB1 history data; every trade and origin is before 2026-10-13, far
before the LT2-LT4 sealed windows from 2026-10-22T00:00Z; no E009-E024 input or outcome file is read).

- **Data:** h1_first + h2_main + h3_power trades (taker, wallet hashes), `sample.csv` outcomes, `panel_H24h` and
  `panel_H6h` origins (price-aligned: `t_cut = t_i - quote_age_s`), one origin per market per UTC day, rows with a
  trade before `t` and an available target. Profiles exclude markets whose trade history was truncated (features still
  use their trades, with NaN windows before the oldest stored trade).
- **P1 persistence:** skill on positions known before SPLIT = 2026-07-01T00:00Z (HB1's split) vs positions known in
  [SPLIT, data end). Primary statistic: share of S1 top-decile skilled wallets (eligible in both periods) with
  `skill_z > 0` in S2, one-sided label-permutation p (2,000 draws). Secondary: Spearman of `skill_z`, S2 P&L per dollar
  of S1-skilled vs others, P&L-ranked winners (top decile of S1 `ppd`) as the WA6-style comparator, significance
  persistence (sign-flip p < 0.05 in S1 and S2), event-level flips.
- **P2 / P3:** walk-forward monthly folds (train on rows whose label was known before the fold start; expanding).
  OLS of the 24 h (P2) / 6 h (P3) mid change. M1 = C0 (HB1 controls: logit mid, |mid - 0.5|, 1 h / 1 d / 1 w change
  and own previous 2 h change, with missing flags) + generic net flow 1 h / 6 h / 24 h. M2 = M1 + skilled net flow 1 h /
  6 h / 24 h. Statistic: mean out-of-sample squared-error reduction M1 -> M2, event-clustered bootstrap (2,000), one-sided.
- **P4:** same folds, logistic model of the resolution (outcome 0 wins; resolved 0/1 markets only; label time = known
  time). R1 = logit(mid) + generic flow; R2 = R1 + skilled net flow. Statistic: mean log-loss reduction R1 -> R2.
- **Family:** Holm over P1-P4 at 0.05. Descriptive only (not counted): M0 -> M1 (generic flow), M2z (continuous
  `ws_zflow24`), M3 (all family columns), the pooled per-SD coefficient of `ws_net24h`, sports vs non-sports.
- **Nothing is tuned:** MIN_POS 5, N0 10, top 10%, long-shot 0.35, windows and the 48 h lag are fixed above. A null is
  reported as a null.

## 6. Development results

Pending (filled in after the single run of `run_wallet_skill.py dev`).

## 7. Signal-engine integration (adapter)

The engine (`backend/astrolabe/signal_engine/`, branch `feat/signal-engine`) was not committed when this family was
built, so the family lives in `research_lab` and plugs in with these steps (no engine file is edited here):

1. `features.py`: add `"wallet_skill": wallet_skill.COLUMNS` to `FAMILY_COLUMNS` and `"wallet_skill"` to
   `SOURCE_FAMILIES`; in `build_capture`, after `find_sample`, call
   `wallet_skill.family_features(sample, f, snap)` with `snap` = the latest snapshot file whose `as_of <= capture start`
   (never a later one), and concatenate it with the other family frames. Bump `FEATURES_VERSION` (new columns).
2. A daily job (light lane, after 00:00Z): load `ProfileBuilder` state from `ENGINE_ROOT/wallet_skill/state/`, ingest
   the new trade samples' `wallets.csv.gz` through `TradeDeduper` (overlapping samples counted once), ingest resolution
   records with `resolutions_from_engine_log(labels.load_resolutions(paths))`, `advance_to(day 00:00Z)`, write
   `snapshots/<day>.parquet` (`snapshot_frame`, write-once) and save the state. The builder needs outcomes for every
   market with pending positions: add those market ids to the engine's resolution candidates (`due_for_fetch`).
3. Specs: a challenger = champion families + `wallet_skill`, `isolates: ["wallet_skill"]`.
4. **Embargo:** the family carries signed flow, so isolated scoring of it would report a quantity correlated with the
   sealed flow-continuation tests (E013, E016, E018; LT4 E024 concentration). Add
   `{"token": "wallet_skill", "until": "2026-11-18T00:00:00Z", "tests": ["E013", "E014", "E016", "E018"], ...}` to
   `config.EMBARGO` (the later of the `flow` and `wallet` embargoes). Prospective prediction writing can start at once.
5. Warm start: the live builder starts empty (the HB1 profiles were built on other markets and are not used live, to
   keep one clean causal record). Skilled sets need weeks of resolved positions before they are meaningful; until a
   snapshot has at least 200 eligible wallets the family should be NaN (to be added in the engine adapter).
