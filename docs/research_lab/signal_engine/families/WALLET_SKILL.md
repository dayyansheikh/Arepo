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

**DEVELOPMENT, exploratory_historical. Not a confirmation, not an edge claim.** Single run, 2026-10-20 23:31-23:34Z,
at commit `319bcd2c` (the declaration commit). No code or parameter changed after the run. Full output:
`wallet_skill_dev_results_2026-10-20.json` (next to this file; no wallet hashes). Mac, 202 s, 0.96 GB peak RSS.

**Coverage.** 3,215,468 taker trades, 324,385 wallets, 9,995 markets with trades, 12,698 markets with a final outcome
(trades 2025-04-03 to 2026-10-12; outcomes known 2025-09-30 to 2026-10-13). Profiles: 2,586,655 trades (125 truncated
markets excluded), 824,112 resolved positions (632,041 known before SPLIT). Daily skilled set from about 600 wallets
(median of origin days; about 6,100 eligible) growing to 3,462 by late September 2026. **Only 6.0% of 24 h origins
(6.4% of 6 h origins) had any skilled-wallet trade in the prior 24 h**, against about 50% with any trade at all.

**P1 persistence (Holm p 0.002, passes).** Skilled set chosen on positions known before 2026-07-01 (2,795 skilled of
27,950 eligible); 3,194 wallets are eligible in both periods.

| quantity | value |
|---|---|
| S1 top-decile skilled with `skill_z > 0` in S2 | **71.2%** (459 wallets) vs 59.7% of all eligible-in-both; permutation null 59.6%, p 0.0005 |
| Spearman of `skill_z` S1 vs S2 | 0.109 [0.073, 0.146] |
| S2 P&L per dollar at risk, S1-skilled | +21.7c [+1.4, +39.6] (wallet bootstrap) vs others +3.6c [-1.7, +8.5] |
| sign-flip significant (one-sided p < 0.05) in S1 | 16.8% of eligible wallets (4,685; the null rate is 5%) |
| significant in S2 given significant in S1 | **44.4%** (554 wallets) vs 21.1% base; p 0.0005 (cf. Gómez-Cram 44%) |
| P&L-ranked winners (top decile of S1 `ppd`) with `skill_z > 0` in S2 | 52.6% (247 wallets), below the 59.7% base; p 0.99. P&L-ranked winners do not persist (WA6-style ranking fails, as in the literature) |
| event-level flips (sensitivity) | same picture: 70.9% vs 59.6%, Spearman 0.102, S2 ppd +22.3c |

**P2 / P3 / P4: null (Holm-adjusted p 1.0 for all three).** Walk-forward monthly folds (Dec 2025 / Jan 2026 to Oct 2026).

| target | rows (event clusters) | generic flow M0 -> M1 | skilled flow M1 -> M2 (primary) | M1 -> M2z (`ws_zflow24`) | M1 -> M3 (all family columns) |
|---|---|---|---|---|---|
| 24 h mid change (MSE gain x 1e6) | 51,171 (2,399) | +27 [+18, +36] | **-5 [-9, -1]**, p 0.998 | -3 [-4, -1] | -39 [-91, -5] |
| 6 h mid change (MSE gain x 1e6) | 53,724 (3,343) | +23 [+14, +33] | **-2 [-7, +4]**, p 0.74 | 0 [-3, +4] | -59 [-129, -8] |
| resolution (log-loss gain x 1e4) | 25,719 (1,957) | -9.6 [-16.5, -3.3] | **-2.5 [-5.4, +0.4]**, p 0.95 | -9.9 [-20.0, 0.0] | +2.0 [-21.7, +28.6] |

Descriptive only: pooled per-SD coefficient of `ws_net24h` (with C0 and generic flow) +0.03c [-0.07, +0.12] on the 24 h
change and +0.10c [+0.04, +0.17] on the 6 h change (in sample, not walk-forward; it does not survive out of sample).
Sports vs non-sports: M1 -> M2 is negative in both (-43 and -5 x 1e-6).

**Reading.**
- Taker skill measured by sign randomisation is real and persistent in this sample, at about the size reported by
  Gómez-Cram et al. P&L rank is not skill. This settles the HB1 WA6 question in the direction the literature predicts:
  ranking by P&L picks lucky wallets.
- Persistent wallet skill does **not** become a better market forecast at 6 h, 24 h or resolution once generic flow is
  in the model. Skilled wallets touch only about 6% of market-days, and where they trade, their flow carries nothing
  out of sample beyond what generic flow and the price already carry. The extra columns overfit (M3 is worse).
- Caveats:
  - Skill is relative to the trade price. A wallet that systematically exploits a price-level bias (for example
    selling long shots, or NO carry) counts as skilled. That is real P&L, but not private information.
  - Taker trades only.
  - Wallet records cover AREPO's sampled markets only (12.7k markets), so the profiles are thin; many truly skilled
    wallets are never eligible.
  - The 48 h outcome lag is conservative.
  - The panels' price series are "mid-like" (HB1 price-semantics caveat).
  - Market selection was made at fetch time from closed/active status, without outcomes.
- For the engine: keep `wallet_skill` as a **low-priority challenger**. The prospective leaderboard is the right judge,
  and the development prior is a null. A more promising use of P1 is wallet-level (follow the specific skilled wallets'
  positions to resolution, with copy latency). That needs its own registered design (gap 1 H1b-style copy-latency test)
  and is not built here.
- **Count:** 4 counted development tests (P1-P4, Holm). Descriptive lines are not counted.

**Host dry run (2026-10-20 ~23:40Z, read-only, `/tmp/wskill`, deleted afterwards).**
- Inputs: seeded from `h1_first` (196,866 profile trades, 345 outcomes), then ingested the 12 newest trade samples
  (2026-10-20, 2,892,119 rows read, 1,357,476 new after dedup over 12,270 markets).
- Result: snapshot of 33,873 wallets (759 eligible, 76 skilled); family features for all 2,000 markets of the newest
  sample (1,999 non-null; 228 with skilled flow; mean `ws_cov24` 0.35).
- Cost: **41 s wall, 439 MB peak RSS**, measured while two other jobs (LT3 census, engine refit) were running.
- State after one day: `pending.parquet` 43 MB (568k open wallet-market rows), `sums.parquet` 3.5 MB, snapshot 65 kB.
  Pending grows with open markets, so the live job should drop pending rows of markets unresolved 30 days after their
  end (engine `RES_GIVEUP_S`).
- 20.4% of the sample wallets also appear in the 500-market `h1_first` history, which confirms that the sidecar and the
  history backfill use the same HMAC key. History-built profiles can therefore seed the live builder; this is an
  optional, causal warm start, since every history outcome was known before go-live.

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
5. Warm start: the live builder starts empty by default. A live-only builder needs weeks of resolved positions before
   it is meaningful, and `family_features` returns NaN while a snapshot has fewer than 200 eligible wallets
   (`MIN_ELIGIBLE_SNAPSHOT`). Optional, still causal: seed it with the HB1 history positions (same HMAC key, every
   outcome known before go-live) via `wallet_skill_dev.profile_trades` + `ProfileBuilder.add_trades/add_resolutions`.
6. Pruning: drop pending rows of markets still unresolved 30 days after their scheduled end (`RES_GIVEUP_S`), so the
   pending table stays bounded (one day of samples gives about 568k rows / 43 MB).
