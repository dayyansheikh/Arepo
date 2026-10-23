# Signal engine v1: design

- **Status:** DEPLOYED on the host 2026-10-21 (signal-engine autopilot): per-pass `tick` is the last step of
  `scripts/oracle/arepo_pass.sh`; queue jobs q0512 (refit), q0513 (score), q0514 (walkforward) promoted; q0510/q0511
  stay drafts (the tick replaces them). Feature backfill of the captures still on the host ran once by hand. Auxiliary
  families (section 16) added the same day. Live state: `STATUS.md`.
- **Scope:** forecast quality only (North Star, `NORTH_STAR.md`). Outputs are labelled *signal strength*, never probability
  of profit or an edge. The E-test confirmation programme is separate and unchanged. The engine never reads any E-test
  outcome or prediction file (it reads the collector's raw inputs only).
- **Code:** `backend/astrolabe/signal_engine/` (config, store, features, labels, specs, learners, training, predict,
  scoring, promotion, walkforward, dashboard), runner `backend/scripts/run_signal_engine.py`, specs in
  `backend/astrolabe/signal_engine/specs/`, tests `backend/tests/unit/test_signal_engine.py`, /lab section in
  `scripts/lab/lab_host.py` (`build_signal_engine`).

## 1. Architecture

```
complete capture (every 2 h) --features--> quotes/<cap>.parquet  (every binary market: status, bid, ask)
  + book sweep 1, trade sample,            features/<cap>.parquet (eligible markets, float32 families)
  + Kalshi pair quotes (inputs only)        meta/<cap>.json        (slot, clocks, counts, sources, sha256)
                                                   |
daily refit (fit_time F) <-- rolling window of features + labels available before F
   models/<model_id>/<stamp>/{<target>.json, fit.json}      (write-once; fit.json written last)
                                                   |
predict (each new capture) -- newest fit with fit_time <= capture start
   predictions/<cap>/<model_id>.parquet + logs/predictions-YYYYMMDD.jsonl (receipt time)
                                                   |
daily score -- resolve labels (Gamma by id) -> score matured, on-time predictions (28 days)
   leaderboard/<stamp>.json, promotion decision, champion/history.jsonl, dashboard.json -> /lab
```

Every data file is write-once (temp file + fsync + hard link; an existing file is never touched). Logs are append-only
and split by UTC day so the nightly archive rotation can release them. `state/` holds rebuildable caches only.
Rewritable convenience files: `dashboard.json`, `leaderboard/latest.json`, `dev/latest.json`.

## 2. Targets and labels (`labels.py`)

| target | definition | eligible at origin (ex ante) | label available |
|---|---|---|---|
| `dir_2h`, `dir_6h`, `dir_24h` | 3-class Gamma-mid change from the origin capture (slot k) to the complete capture of slot k + h/2: down if dmid < -0.005, up if > 0.005, else flat (δ frozen 2026-10-11 in `MULTI_SIGNAL_PIPELINE_DESIGN.md` §1) | base eligibility and scheduled end after the target slot (or unknown) | when the target capture's quotes file exists (availability time = its finish time) |
| `res_7d` | outcome 0 resolves YES (1) / NO (0), C1 rules (`calibration.parse_outcome`) | base eligibility and scheduled end in (origin + 2 h, origin + 7 d] | fetch receipt time of a resolved record |

- **Base eligibility** (origin row only): binary, open, active, two-sided, spread <= 0.10, mid in [0.02, 0.98], end after
  the origin (`panel.eligibility_mask` rules), and **no UMA resolution proposal** in the origin sidecar row (counted).
- **States, never filled:** `labelled`, `pending`, `unavailable_missing_capture` (target capture absent 3 h after its
  slot), `unavailable_absent` (market not in the target listing; closed markets leave the `closed=false` listing),
  `unavailable_closed/inactive/one_sided`, `unavailable_split`, `unavailable_other`, `unavailable_unresolved` (30 days
  after the scheduled end). The leaderboard publishes the per-day counts of every state (attrition is visible).
- **Primary target:** `dir_2h` (fastest to mature, most power; the historical gains were largest at 2 h).

## 3. Feature families (`features.py`, `se-features-v1`)

| family | columns (NaN = missing; never filled in the store) | source and clock |
|---|---|---|
| market_state | mid, spread, log liquidity, log 24 h volume, hours to end (+ unknown flag), last trade - mid, quote staleness, market age, tick, neg-risk flag, own 24 h realised volatility, prior observations; category (`fee_category`) | origin row + sidecar; own look-backs from earlier quotes files |
| momentum | Gamma chg 1h / 1d / 1w; own mid change over 2 h, 6 h, 24 h | origin row; earlier quotes files only |
| flow | sampled flag, log trades 1 h, log notional 1 h, signed share, largest trade / liquidity, time since last trade | active-frame trade sample of the pass (trades strictly before the market's origin row receipt) |
| book | has-book, top / 1c / 5c imbalance, 5c depth, microprice minus **sweep** mid, book age, levels | first book sweep of the pass (received ~7-8 min after the capture, so **after the label origin**: see section 21; no sweep-Gamma gap) |
| xvenue | has-pair, Kalshi mid minus Gamma mid, Kalshi spread, quote age (<= 30 min) | `cross_venue_live/quotes` lines received before the capture start (quotes only) |
| wallet | has-sample, log distinct wallets 24 h, top-1 notional share, HHI | `wallets.csv.gz` of the trade sample, trades in [origin - 24 h, origin); hashed wallets |
| tte (derived) | near-24 h / near-72 h indicators, their products with momentum, chg 1h x log hours | computed at fit/predict time from stored columns |

Derived transforms (logit mid, |mid - 0.5|, log1p of hours/ages) are applied in `learners.py`, so the store stays
primitive. Causality: no feature reads any capture after the origin; inputs from other streams are received before the
prediction is written, and every prediction is only scored if written before its target capture (section 6). **One
exception to "before the origin" (disclosed 2026-10-22, section 21):** the `book` family comes from a sweep received
~7 min after the origin capture, while direction labels start at the origin's Gamma mid, so book inputs partly overlap
the label window. They are available before the prediction is written, but a model holding them can be credited for a
move that has already happened.
Measured coverage on 2026-10-20 20:31Z (46,448 eligible): book 98%, flow and wallet 4.3% (2,000-market sample), xvenue
0.25% (116 pairs). A feature definition change needs a new `FEATURES_VERSION` and new spec versions (specs pin it).

## 4. Models (`specs/`, `specs.py`, `learners.py`)

A spec is a JSON file; its id is `spec_sha256` = sha256 of its canonical JSON; `specs/registry.json` pins every sha and
loading refuses a mismatch (tested). Fields: `model_id`, `version`, `features_version`, `learner`, `families`,
`derived`, `isolates` (every family/derived set added to the champion's market_state + momentum), `broad`, `targets`,
`train` (window_days 14, res_window_days 28, max_rows, min_rows, min_days, require_sources), `params`, `description`.

| model | learner | adds | role |
|---|---|---|---|
| `se0_champion_lr_mm` | logistic (C = 1, standardised, missing flags, category one-hot) | - | **champion v0** (momentum + market state) |
| `se1_lgbm_mm` | LightGBM | - (learner only) | separates a learner effect from a family effect (like M2v) |
| `se2_lr_flow` | logistic | flow | challenger (embargoed, section 8) |
| `se3_lr_book` | logistic | book | challenger (embargoed) |
| `se4_lr_xvenue` | logistic | xvenue | challenger (embargoed) |
| `se5_lr_tte` | logistic | tte interactions (C-TTE) | challenger (embargoed) |
| `se6_lr_wallet` | logistic | wallet | challenger (embargoed) |
| `se7_lgbm_all` | LightGBM | every family + tte (`broad`) | broad combination |

LightGBM: fixed parameters (no search), early stopping on the last 20% of training origins (inner rows whose labels
fall after the first validation origin are purged), temperature scaling on that block. Logistic predictions are numpy
from JSON coefficients; LightGBM from the booster text. Families needing a stream (`require_sources`) train only on
captures where that stream existed.

## 5. Walk-forward fits and memory (`training.py`)

A fit at time F uses origins started before F and labels **available** before F (direction: target capture finished
before F; resolution: fetched before F). Prediction for a capture uses the newest fit with fit_time <= capture start,
so no training label postdates the origin. The frame is built one capture at a time: only the needed columns are read,
each capture is subsampled with a seeded generator to `ceil(max_rows / captures)`, everything is float32. This avoids
the MC1 failure (a 2.1M x 123 panel exhausted the 2 x 3.2 GB address-space cap): measured peak 1.07 GB RSS for a
385k-row frame and 8 models x 3 targets under a 3 GB cap.

## 6. Prospective scoring and leaderboard (`predict.py`, `scoring.py`)

- **Write-once predictions** per (capture, model): uint16-quantised probabilities (the stored value is the frozen
  prediction; p_flat = 1 - p_down - p_up, clipped at 1e-6 and renormalised), an eligibility bit mask, metadata (spec
  sha, fit id, features sha). The `predictions` log line written after the file is in place is the receipt time.
- **On time:** direction targets only if logged before the target capture's slot time; resolution only if logged before
  the market's close (and scheduled end). Late predictions are counted (`late`) and excluded. Captures whose 24 h target
  slot has started are never predicted. Newest capture first.
- **Metrics** per target x model x window (7/14/28 days) x category (primary target, 28 days): mean log loss, Brier,
  calibration slope and intercept (logistic recalibration on 80 logit bins; mean over the up and down events for
  direction), AUC (1,000 p bins; mean of up and down one-vs-rest), coverage (on-time predictions / eligible rows),
  late count, days.
- **Gain over the champion:** per-row `ll(champion) - ll(challenger)` on rows both scored; mean = sum / rows; 95%
  percentile CI from a cluster bootstrap over Gamma **event** clusters (market id when the event is unknown; events
  contain markets, so this is at least as conservative as market clustering), B = 2,000 multinomial draws, seeded;
  plus `days_positive / n_days`. Memory is O(models x targets x windows x clusters) (dense per-window cluster sums).
- **Output:** `leaderboard/<stamp>.json` (write-once, `evidence_role: prospective_engine`) with `rows`,
  `category_rows`, `label_states`, the promotion decision and `info`; `dashboard.json` for /lab.

## 7. Promotion rule `se-promotion-v1` (pre-declared; `promotion.py`; superseded by v2 on 2026-10-21, §20)

v1 never fired: no challenger could meet condition 1 before 2026-11-04. The rule in force is v2 (§20), which is v1
with a stricter condition 2.

A challenger replaces the champion only if **all** hold on the day's prospective leaderboard:
1. not embargoed; >= 14 distinct UTC days of paired primary-target scores in the 28-day window; first prospective
   prediction >= 14 days old;
2. `dir_2h` mean log-loss gain over the champion: event-clustered bootstrap CI at level 1 - 0.05/K (Bonferroni over the
   K challengers evaluated that day) with lower bound > 0;
3. daily mean gain positive on >= 2/3 of the scored days;
4. calibration not materially worse: |slope - 1| <= champion's + 0.10 and |intercept| <= champion's + 0.05;
5. no secondary target (dir_6h, dir_24h, res_7d) with a significant loss (95% CI upper bound < 0, judged with >= 50
   clusters);
6. coverage >= champion's - 0.01;
7. >= 7 days since the last promotion.

Ties: the largest lower bound wins. Promotions are appended to `champion/history.jsonl` (never removed); retired
champions keep predicting while their spec stays `active` in the registry. A promotion is a forecast-quality decision,
not an edge claim. Changing any constant is a new rule version declared here first, never tuned to make a challenger pass.

## 8. Embargo (orchestrator integrity constraint, 2026-10-21)

Registered or drafted prospective live tests must not be shadowed before their single analyses. `config.EMBARGO` maps
a token (a family or derived set) to `until`. A model whose spec **isolates** an embargoed token (non-broad, token in
`isolates`) gets **no scores computed** (prospective or development) and **no numbers displayed** before `until`:
leaderboard, dashboard and the /lab snapshot show only `embargoed_until` (lab_host re-checks independently of the
file). Its predictions are still written (write-once), so the history exists and is scored after the date. The
champion (market state + momentum), the learner reference and broad multi-family combinations are not embargoed.

| token | until | tests |
|---|---|---|
| xvenue | 2026-11-04T00:00Z | E009, E010 (fixed end 2026-11-03) |
| surprise | 2026-11-19T00:00Z (from 11-12, 2026-10-21) | E011 (window ends 11-10, analysis after 11-11; moved for margin on the science review's note, since pending outcomes are retried); model `se15_lgbm_surprise` since 2026-10-21 ~15:00Z (no score computed or shown before). Its spec description still says 11-12: the spec is pinned, and the date lives in `config.EMBARGO` |
| chg1d_x_liq (no model yet) | 2026-11-14T00:00Z | E012 |
| tte | 2026-11-14T00:00Z | E014 |
| flow | 2026-11-16T00:00Z (11-16 -> 11-22 on 2026-10-21 for LT5 J/O; that extension withdrawn 2026-10-22 ~12:00Z, both dropped at q0562; E016/E018 dropped at q0472, 11-16 kept as margin) | E013, E014 (LT2, 2026-11-13T12Z) |
| book | 2027-02-14T00:00Z (from 11-18, then 11-22, both 2026-10-21; then 12-09; 12-31 on 2026-10-22 for LT7 CH195/CH197, round 4; 2027-01-23 on 2026-10-22 ~12:00Z for LT8 CH202/CH203, LIVE_TESTS_8.md section 9; 2027-02-14 on 2026-10-22 ~23:00Z for LT9 CH214, LIVE_TESTS_9.md section 9, the later of that and LT9's analysis commit, **withdrawn back to 2027-01-23 if CH214 drops at census**; that fallback was LT8's and is void since LT8 closed 2026-10-23: a CH214 drop needs a new ledger line) | E015, E022 (LT4 registered), LT9 CH214 (LT8 CH202/CH203 pruned 2026-10-23 08:00Z when LT8 closed with no test; E019, E020, LT5 H/R and LT6 V were dropped at census and pruned 2026-10-22; LT7 CH195/CH197 pruned 2026-10-22 ~23:00Z when LT7 closed with no test) |
| book0 | 2027-02-14T00:00Z (same date and tests as `book`; added 2026-10-22 ~03:00Z with `se19_lr_book0` and broad `se18_lgbm_all_b0`, before any book0 table or score existed; section 22) | as `book`; also hides `book0` in se18's family attribution. Disclosed: the visible se7 minus se18 score contrast compares sweep-1 book with book0 (section 22) |
| wallet | 2026-12-07T00:00Z (from 11-18, 2026-10-21) | E026 copy-skilled (analysis on/after 2026-12-06T12Z); E024 dropped before any census, pruned 2026-10-22 |
| wallet_skill (no model yet) | 2026-12-07T00:00Z | E026 |
| rewards | 2026-11-18T00:00Z (the later of that and E022's analysis commit; 11-18 -> 11-22 on 2026-10-21 for LT5 R, that extension withdrawn 2026-10-22 ~12:00Z after LT5 R dropped at q0561) | E022 S2 (registered; reward versus non-reward split, analysis not before 2026-11-17T12Z). E020 dropped at the LT4 census. LT7 has rewarded secondaries but requests no token |
| event | **withdrawn 2026-10-22T12:00Z** (was 11-22) | LT5 F (CH184) dropped at census (q0561); no registered or drafted test uses event-sibling features. se8 / se10 are visible from then (neither had a fit or score before). Disclosed: that census read 2026-10-20/21 captures for counts only |
| movetype | 2026-11-22T00:00Z (11-22 -> 12-31 on 2026-10-22 for LT7 CH193, round 4; that extension **withdrawn 2026-10-23T00:00Z**: LT7 closed at census with no test, and neither LT8 nor LT9 requests movetype) | E015 (LT3 registered 2026-10-21, analysis not before 2026-11-15T12Z); same date as `book`; added 2026-10-21 ~14:30Z with `se14_lgbm_movetype` (which also isolates `book`), before any movetype score was computed or shown |
| participation | 2026-11-25T00:00Z | CB17-C (CH150, drafted: event-volume change as eligibility, event liquidity as control; REP_8 ends no earlier than 11-23T08Z); added 2026-10-21 with `se16_lgbm_participation` before any table or score existed (science review REVISE) |
| vote, clips, deadline, siblings (no models) | **withdrawn 2026-10-22T12:00Z** (were 12-09) | LT6 V, K, D, B, all dropped at census (q0582, q0583) |
| hollow (no model yet) | 2026-11-18T00:00Z | E022 (LT4, CH174; registration planned 2026-10-25, analysis not before 2026-11-17T12Z; experiments round-3 request, added 2026-10-21 ~20:50Z): any feature combining Gamma `liquidity` with sweep depth (`h`, `L/D`, `log L - log D`, `zh`, h terciles). Liquidity alone stays usable. E022's depth control (`log1p D` of the outcome-0 5c depth) is `bk_depth5c`, already under `book` (12-09). Broad `se7_lgbm_all` holds `liquidity` and `bk_depth5c` as separate columns (no hollow column); as a broad model it stays unembargoed under this section's rule, disclosed here |
| resist, capath, deepbook, absorbed, ivr (no models) | **withdrawn 2026-10-23T00:00Z** (were 12-31) | LT7 closed at census with no test (CH191, CH192, CH193 dropped at CC7; CH195, CH197 at CS7; ledger 2026-10-22). Before that: LT7 (draft; CH195, CH191, CH194, CH197, CH193, CH192; experiments round-4 request, added 2026-10-22 ~01:00Z). Each date is the later of 12-31 and LT7's analysis commit (a later request follows if LT7 slides). `mm_fresh` is the isolated chg_1h x own 2 h set; the champion's momentum family stays usable `mm_fresh` was **withdrawn 2026-10-22T12:00Z** with CH194 (LT7 R1 response) |
| quietbook, swclock (no models) | **withdrawn 2026-10-23T08:00Z** (were 2027-01-23) | LT8 CH203, CH202 (design text frozen c124db50; section 9 requests applied 2026-10-22 ~12:00Z, before the 12-01 deadline). `sched` (CH204, no model) was **withdrawn 2026-10-23T07:30Z** with `attrlimit_lt8`'s per-market slot-of-day limit (made for CH204 only): CH204 dropped at LT8's captures census CC8 (q0622, counts only). CH203 and CH202 dropped at the sweeps census CS8 (q0623): LT8 closed with no test, and `quietbook`, `swclock` and all of `attrlimit_lt8` were withdrawn at 08:00Z |
| bandbreak, pool, rwblink (no models yet) | 2027-02-14T00:00Z (the later of that and LT9's analysis commit) | LT9 CH213, CH214, CH212 (design text frozen 11fee7a0; LIVE_TESTS_9.md section 9 requests, round 6, applied 2026-10-22 ~23:00Z). No isolating `pool` challenger is scored before LT8's `quietbook` date in any case. `rwend` (CH215) gets a token only if CH215 enters at its census; no rwend family is built before then |
| dispgap | 2026-11-14T00:00Z (the later of that and LT2's analysis commit, q0461) | E012 (`dg_1d` is E012's primary x minus its pre-declared Gamma `oneDayPriceChange` sensitivity; se22 is scored on `dir_24h`, E012's horizon), E013 / E014 (`chg_1d` / `chg_1w` as controls); added 2026-10-22 ~23:15Z with `se22_lgbm_dispgap` (science review must-fix 2), before any table or score existed (section 26) |
| dormant | 2026-11-19T00:00Z (as `surprise`) | E011 (its surprise label requires a quiet prior day, and secondary (a) reads "quiet markets that then move"; `dm_*` encode that quietness); added 2026-10-22 ~23:15Z with `se23_lgbm_dormant` (science review must-fix 1; CH220 asked for it), before any table or score existed (section 26) |
| attrlimit_lt8, attrlimit_lt9 (attribution limits, not family tokens) | lt8 **withdrawn 2026-10-23T08:00Z** (was 2027-01-23; LT8 closed with no test), lt9 2027-02-14T00:00Z | LT8 and LT9 section 9: no attribution (SHAP or otherwise) of the champion, se18 / se9 or any broad model on the listed interaction terms (`limits`), and no LT8 / LT9 family in a broad model (`no_broad_families`), before the date. They match no family or spec, so they hide nothing by themselves; the engine's attribution is per family only (section 17), so none of the terms is computed. A test guards `no_broad_families` |

LT3/LT4 dates are the proposed windows; when they register, move the dates **later** if needed (never earlier).

**Withdrawal (2026-10-22).** The only way a date moves earlier: when a test drops at its census before registration,
its token and any extension made only for it are withdrawn with a ledger line (the programme's rule, e.g.
LIVE_TESTS_8.md section 9). A withdrawn entry stays in `config.EMBARGO` with `until` set to the withdrawal time, the
structured fields `withdrawn_utc` and `until_before`, and a `WITHDRAWN` note, so the record stays auditable and
`embargo_of` at earlier times still returns the embargo (with the withdrawal time as its date; prediction logs keep
the date that applied when they were written). An entry whose date moved earlier always carries these fields. A
withdrawal raises the promotion rule's K at once (every active non-embargoed challenger counts, §21), which only makes
the bar stricter. First use: 2026-10-22T12:00Z (`event`, `vote`, `clips`, `deadline`, `siblings`, `mm_fresh`; the LT5
extensions of `flow` (to 11-16) and `rewards` (to 11-18)); K 5 -> 7 (se8 and se10 join). Expected K path as later
embargoes lapse: 9 at 11-04 (xvenue), 11 at 11-14 (tte), 13 at 11-16 (flow), 14 at
11-18 (rewards), 15 at 11-19 (surprise), 16 at 11-25 (participation), 17 at 12-07 (wallet), 20 at 2027-01-23 (book,
book0, movetype); these steps follow the declared definition and are not tuning. Update 2026-10-22 ~23:00Z: `se21_lgbm_hwm`
adds one to every step from its first score (K 8 now), and the book step moves to 2027-02-14 (LT9; se3, se14, se19).
Second use of withdrawal: 2026-10-23T00:00Z, LT7's five tokens and the `movetype` extension (no model changes K: se14
also isolates `book`). Update 2026-10-22 ~23:15Z (section 26): `se22_lgbm_dispgap` joins at 11-14 and `se23_lgbm_dormant` at
11-19, so from 11-14 every later step is one higher, and from 11-19 two higher.

**Fit diagnostics under an embargo (science review 2026-10-21).**
- A LightGBM fit computes its inner-split validation loss, because early stopping and temperature calibration need it.
  The loss is stored in the fit artifact.
- Nothing reads it before the embargo date: not scoring, not promotion, not the dashboard, not /lab. It is a fitting
  quantity, not a score.
- The SHAP family attribution is a development diagnostic. Since 2026-10-21 it is **not computed** while the spec is
  embargoed (`attribution: null`).
  - Fits made before that by se10-se13 may hold an attribution in their artifacts. It was never displayed, and the
    dashboard skips embargoed models.
  - After the date, the next refit computes it. A new
challenger that isolates any hypothesis under a live test must add its token here first.

## 9. Storage, retention class and catalogue

Root `data-dumps/research_lab/signal_engine/` (catalogue label `SIGNAL-ENGINE`, `data_catalogue.DIR_EXPERIMENTS`).
Measured sizes: features 2.5 MB + quotes 0.85 MB per capture (~40 MB/day); predictions 5.2 MB per capture for 8 models
(~62 MB/day); fits ~1-10 MB/day; leaderboards and logs small. **Retention class:** derived, write-once, archived
nightly by the existing rotation, independent of the 8-day snapshot rule; proposed host rules (in
`scripts/oracle/archive_retention.json` `deferred_rules`, not active): `predictions/` 35 days, `features/` and
`quotes/` 45 days (training reads <= 28 days); `meta/`, `models/`, `leaderboard/`, `dev/`, `champion/`, `logs/` are
never deleted. Steady state on the host with the rules: ~4 GB. The engine refuses new writes (exit 75) above 8 GB of
its own directory and honours `--data-dumps-cap-gb 40`.

## 10. Resource budget (host dry run 2026-10-20 23:26-23:45Z, 1 OCPU, other queue jobs running)

| step | measured | budget |
|---|---|---|
| features, 1 capture | 6.8-10 s, 359-408 MB RSS (488 MB during a 24-capture backfill), 1.2 GB AS cap | mem_mb 480, as_cap 1600 |
| refit, 8 models x 4 targets, 385k-row frame | 6.7-7.5 min, 1.07 GB RSS, 3.0 GB AS cap | mem_mb 1500, as_cap 3500, ~10-15 min at 14 days |
| predict, 8 models x 47,461 rows | 31 s, 295 MB | mem_mb 400 |
| resolve, 2 requests (100 ids) | 2.3 s, 160 MB; 100/100 parsed resolved | <= 800 requests/day |
| score (1 capture) | 1.2 s, 145 MB; steady state estimated ~6 min + bootstraps, < 600 MB | mem_mb 700 |

## 11. Deploy steps (coordinator / owner)

1. Merge `feat/signal-engine` (code, specs, tests, drafts, catalogue entry, lab_host section); `scripts/oracle/deploy.sh`.
2. Promote the drafts in order: `q0510_se_features` (backfills every capture still on the host, 2 per run) and
   `q0511_se_predict`; then `q0512_se_refit` once >= 2 days are backfilled (first fit), `q0513_se_score`, and the
   one-off `q0514_se_walkforward` after >= 3 days are backfilled. Or, preferred for timeliness: add one line
   `timeout 300 nice -n 10 $PY scripts/run_signal_engine.py tick --max-items 2 --data-dumps-cap-gb 40 2>&1 | tail -1 || true`
   to `scripts/oracle/arepo_pass.sh` after `sample_trades.py`, and promote only q0512-q0514.
3. Activate the `signal_engine/` retention rules after the first verified releases contain these files.
4. /lab: the host snapshot carries `signal_engine` on the next 10-minute push; the website needs the UI below.

## 12. Bootstrap honestly

Until 14 days of prospective scores exist the dashboard says `status: bootstrapping` and shows a separate
**development/historical** block from `walkforward` (fits before each test day, scored retrospectively; never pooled,
never used for promotion, embargo applied). The prospective block always comes only from write-once predictions.

## 13. Standing workflow: how a session adds a challenger

1. Pick a candidate (a replicated/advanced effect, a new stream, a learned combination). If it needs a new feature,
   add it to `features.py`, bump `FEATURES_VERSION`, and create new versions of every spec (old specs stay registered
   until retired; never edit a pinned spec).
2. Write `specs/<new_id>.json` (declare `isolates`; `broad` only for multi-family combinations), add it to
   `registry.json` with its `spec_sha256` (`python -c "from astrolabe.signal_engine import specs as SP; ..."`), status
   `active`.
3. If it isolates a hypothesis under a live E-test, add the token and date to `config.EMBARGO` first.
4. Run `pytest tests/unit/test_signal_engine.py`, commit, deploy. It starts predicting after the next refit; it is
   scored daily; promotion needs >= 14 days. Retire a model by setting `status: retired` (history kept).
5. Every session: at least one unit of signal-engine work (North Star standing rule); read `dashboard.json` /
   `leaderboard/latest.json` and record notable movements in the checkpoint.

## 14. /lab UI spec (website repo, later; not built here)

Snapshot key `signal_engine` (optional; schema `se-dash-v1`; `arepo-lab-v1` stays backward compatible):
- **Header card:** champion id and family, `prospective.status` (bootstrapping / scoring), days scored, last refit,
  last prediction (capture id, time), stale flag.
- **Leaderboard table** (`prospective.rows`, 14-day window): model, family, target, rows, log loss, Brier, calibration
  slope/intercept, AUC, coverage, gain vs champion with CI and days positive. Embargoed rows show only "embargoed until
  <date> (live test)" with no numbers. Sort by target, then gain.
- **Family gains over time** (`family_gains`): one line per challenger family, 14-day primary-target gain with CI band.
- **Development (historical)** (`development.rows`): same table, visibly labelled "development (historical, not
  prospective)".
- **Promotions** (`promotions`): dated list (new champion, previous, gain and CI).
- Vocabulary: "signal strength / forecast quality", never "probability of profit"; no edge claims.

## 15. Known limits and next steps

- The trade sample covers ~4% of eligible markets (flow/wallet mostly NaN by design); xvenue covers ~0.25%.
- `dir_24h` LightGBM needs > ~1.25 days of training history before its inner split exists (reported as `error` until then).
- `unavailable_absent` mixes resolved and delisted markets (the listing is `closed=false`); attrition is published.
- Resolution labels have a backlog at start (19k due after 2.3 days); 800 requests/day clears it in ~3 days.
- Next: per-market signal feed on the public website (owner-approved deploy; the /lab feed is section 27), SHAP family attribution for LightGBM, more
  challengers from replicated effects after their embargoes, scored-capture caching to speed the daily scorer.

## 16. Auxiliary feature families (2026-10-21, `aux.py`)

The v1 store is write-once and pinned by every v1 spec, so new families do not go into `features/`. An auxiliary
family writes its own write-once table `aux/<family>/<capture>.parquet`: one row per eligible market in the features
file's row order. Parquet metadata: `aux_version`, the aligned `features_sha256`, `rows_sha256` of the snapshot rows
read, `prev_capture_id`, write time and commit. A line also goes to `logs/aux-YYYYMMDD.jsonl`.
- **Build:** `features` / `tick` run `aux.run_aux` after the base append, newest capture first, with a budget of
  2 x max-items (minimum 4). So the newest capture has its aux tables before `predict`. A capture whose snapshot
  rows were archived first never gets one (missing stays missing; counted as `unbuildable_no_rows`).
- **Join:** `read_features` checks length and `market_id` order. A missing or misaligned table reads as NaN.
  `attrs["aux_ok"]` (the join result, not the file's existence) sets `src_<family>` in training frames.
- **Specs:** list the family in `families` and pin `aux_versions: {family: version}` (validated). v1 specs have no
  pin and keep their sha.
- **Comparability (science review 2026-10-21, finding 2):** `train.require_full_coverage: true` means a target is
  fitted only when every labelled capture in its window joined the family (`insufficient_coverage` otherwise). The
  aux challenger then never trains on a different, shorter or more recent, row set than the champion. Fits record
  `aux_coverage`: captures, joined, and a sha256 of the joined capture list.
- **Predictions:** an aux model's prediction is never written without its family (`aux_pending`, retried while the
  capture is predictable). Predictions record `aux_sha256` per family. A missing prediction lowers that model's
  coverage, which promotion check 6 sees.
- **Causality:** a builder reads only the origin capture's own rows, the engine's own earlier quotes files, or
  streams received before the capture start.
- **Changing a family** means a new version string and new spec versions. Old tables are never rewritten.

**First family `event` (`se-aux-event-v1`), challenger `se8_lr_event`.** Inputs: the capture's complete binary listing
(open, active markets, including siblings that are not eligible themselves) and the previous slot's quotes file.
- `ev_log_n`: log event size.
- `ev_sum_mid_m1`: neg-risk events only; the sum of two-sided sibling mids minus 1. NaN if nothing is quoted.
- `ev_quoted_share`: the share of the event's markets that are two-sided.
- `ev_norm_gap`: own mid / sum minus own mid.
- `ev_rank`: the own mid's rank among the quoted siblings.
- `ev_max_other`: the largest quoted sibling mid.
- `ev_sib_chg1h` / `ev_sib_chg1d`: the siblings' mean Gamma changes.
- `ev_sib_d2h`: the siblings' mean own 2 h mid change, from the earlier quotes file.
- Sibling means exclude the own market and skip missing values (never read as zero). Each needs a value for at
  least half of the siblings.

Events whose sibling rows were received more than 5 s apart are left NaN. On 2026-10-21 the intra-event receipt
spread was median 0 s, p90 0.2 s and p99 201 s, and a sibling quote received minutes after a market's own row could
carry part of that market's later move. This removes some large events selectively, so the score report should show
coverage by event size (to do). Measured on a host capture (42,161 eligible): ev_log_n 90%, overround 44%, rank 79%,
sib_chg1h 20%, sib_chg1d 56%, sib_d2h 71%. Build ~14 s per capture under load.

**Second family `rewards` (`se-aux-rewards-v1`), challenger `se9_lr_rewards` (embargoed until 2026-11-18, E020).**
Inputs: the same capture's Gamma sidecar (`rows_ext.csv.gz`: `rewards_min_size`, `rewards_max_spread`, `clob_rewards`).
Columns:
- `rw_has`: an active programme on the capture's UTC date.
- `rw_log_rate`: log1p of the summed `rewardsDailyRate`.
- `rw_max_spread`: in cents.
- `rw_log_min_size`.
- `rw_in_band`: the current spread is within the max spread, for markets with an active programme.
- `rw_new`: a programme started within the last 2 days.

A market absent from the sidecar is NaN. Present with no programme listed means rate 0. On 2026-10-21, 5.2% of
markets had a programme. An older sidecar without the reward columns gives an all-NaN table for that capture.

**Third family `movetype` (`se-aux-movetype-v1`), challenger `se14_lgbm_movetype` (2026-10-21; embargoed under
`movetype` and `book` until 2026-11-22, E015).** CANDIDATES C07 (traded versus quote-only moves, replicated in HB1-R)
plus C12 (move over spread). The classes follow LIVE_TESTS_3.md §2 (E015). They are computed from the engine's own float32
quotes and features files of capture k and of slot k - 1, so the tolerances are wider: ltp change > 1e-5, and
|d volume24hr| > max($0.01, 4e-6 x volume). This is the engine's own definition, not E015's frozen one.
- It needs no snapshot rows (`needs_rows: False`), so archived captures still get a table (an earlier, already
  causal file, never a reconstruction).
- Values are NaN when the market is not two-sided at k - 1, or not in k - 1's features file (not eligible there).
- Class indicators are 0/1 where the class is decidable and NaN where it is not.
- Columns:
  - `mt_db` / `mt_da`: bid and ask change.
  - `mt_dltp`: last-trade-price change.
  - `mt_dlogvol`: change of log1p 24 h volume.
  - Class: `mt_traded` (ltp changed, appeared, or volume up), `mt_never` (no ltp at either end), `mt_ambig` (volume
    down with no visible trade, or ltp disappeared).
  - Quote-only sub-classes: `mt_q_still` (both quotes within 0.0005), `mt_q_parallel` (same sign as the move, both
    >= 0.005, gap <= 0.005), `mt_q_onesided`, `mt_q_spread` (opposite signs).
  - `mt_x_spread`: move / spread (C12).
  - `mt_x_traded` and `mt_x_parallel`: move x class.
- Only a LightGBM challenger is added (§18 rule), with se1's params. Read it against se1.
- Refit cost: about +9-10 min on 1 OCPU. Per-capture build: under 2 s (4 small parquet reads).
- Differences from E015 (recorded 2026-10-21 ~14:15Z, before any fit read the tables):
  - A missing `volume24hr` (with the last trade unchanged) leaves every class indicator NaN (undecided). E015 calls
    it `ambiguous`. Neither counts it as quote-only.
  - A last trade price of 0 is read as present. E015 reads ltp <= 0 as absent. 0 of 49,569 rows had ltp 0 on
    10-21 12:31Z.
- Host coverage (10-21 12:31Z capture, 49,569 eligible):
  - Gamma omits `last_trade_price` on 56% of rows and `volume24hr` on 78%.
  - Hence `mt_never` covers 72% of markets; `mt_db` is defined for 92%.
  - Among 2 h movers (|x| >= 0.01, 4,244), the shares are: traded 30%, ambiguous 4%, parallel 4.4%, one-sided 5.4%,
    spread-change 1.5%. Counts only, no target read.
- Backfill: 105 tables written on the host at 14:06Z in 40 s (`~/.arepo/signal_engine/aux_backfill_movetype.sh`).

**Fourth family `surprise` (`se-aux-surprise-v1`), challenger `se15_lgbm_surprise` (2026-10-21; embargoed under
`surprise` until 2026-11-19, E011).** CANDIDATES C06. These are price-path primitives from SURPRISE_MOVE_DETECTOR.md §3,
not the frozen detector.
- Inputs: the engine's own quotes files of slots k - 84 .. k (7 days of 2 h slots, the origin's own file last). No
  snapshot rows.
- Columns:
  - `sp_rv6h`, `sp_rv3d`, `sp_rv7d`: root mean square of the finite 2 h mid changes over the last 3, 36 and 84
    steps. This is `ms_rv24`'s definition. Each needs at least 2, 12 and 24 finite changes.
  - `sp_r6h_24h`, `sp_r24h_7d`, `sp_r6h_7d`: ratios. NaN when the denominator is 0.
  - `sp_maxabs24`: the largest |2 h change| of the last 12 steps (at least 3 finite).
  - `sp_dow`, `sp_hour`: UTC weekday and hour of the capture start.
- Missing values stay missing. A market new to the listing has NaN long-window values until it has the history.
- A test checks that the 24 h denominator equals the stored `ms_rv24`.
- The builders share a `SlotMids` cache that evicts the newest slots (captures are built newest first), so a
  backfill reads each quotes file about once. A live capture reads 85 small files.
- Host backfill 2026-10-21 14:17Z: 105 tables in about 60 s, peak RSS 551 MB. Coverage on 10-21 12:31Z: `sp_rv6h` 98%,
  `sp_rv3d` 85%, `sp_rv7d` 78%. The 24 h denominator matches `ms_rv24` to 3e-8.
- The first attempt hit a MemoryError under the backfill's 2 GB address-space cap. The cache then held pandas
  Series, and every reindex built a hash table. It now holds sorted numpy arrays. Since then `run_aux` isolates each
  family: a builder error is recorded under `errors`, no table is written, it is retried at the next run, and the
  other families and the tick's predictions go on.

Embargo (event): token `event` until 2026-11-22 since 2026-10-21 (LT5 F draft; §8). Before that request: E005 (neg-risk band deviation) closed 2026-10-11 as not supported. E019 was dropped uncounted.
SB2-J5 is development only. `ev_sib_*` resembles SB2-J5's L1 and `ev_norm_gap` resembles E005's band deviation, so
se8 is recorded in the ledger as a counted development look at both: any later live test of either must declare
that it is not fresh.

**Fifth family `participation` (`se-aux-participation-v1`), challenger `se16_lgbm_participation` (2026-10-21;
embargoed until 2026-11-25 under `participation`, CB17-C).** Event-level participation and attention breadth (CANDIDATES row 14).
- Inputs: the origin capture's own sidecar `rows_ext.csv.gz` (`event_volume`, `event_liquidity`, `competitive`,
  `event_created_at`, `volume_num`) and its snapshot rows (`liquidity`). For the 2 h change only, the previous slot's
  sidecar. Nothing after the origin is read. An absent previous sidecar leaves the change columns NaN; an older
  sidecar missing a column leaves that column NaN. Nothing is filled.
- Columns (float32, NaN = missing):
  - `pp_log_ev_vol`, `pp_log_ev_liq`: log1p of the event's volume and liquidity.
  - `pp_d_ev_vol`: log1p of the positive part of the event volume change since the previous slot, joined on
    `market_id`. `pp_ev_vol_fell`: 1 if the event volume fell by more than 1e-6, else 0 (a data-quality flag).
  - `pp_liq_share`: the market's own liquidity over the event liquidity, clipped to [0, 1]; NaN if the event
    liquidity is 0 or missing.
  - `pp_competitive`: Gamma's `competitive` score.
  - `pp_log_ev_age_h`: log1p of the hours from the event's creation to the capture start (floored at 0).
  - `pp_log_vol_num`: log1p of the market's lifetime volume (45% of eligible markets on the 10-21 14:31Z capture).
- Clock: all of it comes from the same Gamma response as the origin row, received at the row's receipt time, before
  the prediction.
- **Embargo `participation` until 2026-11-25T00:00Z (science review 2026-10-21, REVISE applied before any table or
  score existed).** CB17-C (CH150, drafted) uses the 2 h event-volume change as its eligibility rule (dV > 0), a
  trailing-tercile stratum and a robustness trim, and log event liquidity as a control
  (`CREATIVE_BATCH_17.md` 761-764, 791-793); its REP_8 frame runs to no earlier than 2026-11-23T08:00Z. Same
  precedent as `rewards` (a control role in a draft). Move the date later if CB17-C slips, never earlier.
- Excluded on purpose: `event_open_interest` (CB17-C's tested ratio), `open_interest`, `event_comment_count` (comment bursts died in the probes:
  9 of 22,111 events changed in 2 h, CREATIVE_HYPOTHESES_2026-10-22.md section 3), `rewards_*` and `clob_rewards`
  (the `rewards` family). E017 was dropped uncounted.
- `se16_lgbm_participation` has se1's params, families market_state + momentum + participation, and trains only on
  captures that have the table. It is read against se1 (learner-matched). It has no development evidence yet.
- Host probe (read-only, 10-21 14:31Z capture, 51,790 eligible): 3.9 s, 317 MB; coverage event volume 73%, its 2 h
  change 72% (positive in 14,795), liquidity share / competitive / event age 100%; the `fell` flag never fired.
- Notes: slots may sit up to 30 min off the grid (`SLOT_TOL_S`), so the "2 h" change spans 1-3 h and is not
  normalised for the gap. The aux metadata records the previous sidecar actually read (`prev_sidecar_capture_id`,
  `prev_sidecar_sha256`). The liquidity share is clipped at 1 (market above event liquidity is hidden).

## 17. Family attribution (2026-10-21, `learners.family_attribution`)

Every LightGBM fit stores `attribution`: mean |SHAP| (LightGBM `pred_contrib`, raw-score scale, summed over classes)
per feature family (derived `tte` and `category` are their own entries). It is computed on a seeded subsample of up to
20,000 rows of the fit's inner validation block. It is a development diagnostic of the fit, never a score, and plays no
part in promotion. `dashboard.json` carries `attribution` for the newest primary-target fit of each active,
non-embargoed LightGBM model.
- Families under an active embargo token are dropped entirely: no value and no share. Only their names are listed
  under `hidden`, so the remaining numbers reveal nothing about them.
- `lab_host.py` re-applies the drop independently, using the file's `embargo_tokens` plus the code's `EMBARGO`.
  An unparseable date counts as embargoed.

## 18. Learner-matched family challengers (2026-10-21)

The development walk-forward (10-14 to 10-20, development only) shows `se1_lgbm_mm` beating the logistic champion by
0.04-0.05 nats on every direction target with the same inputs: a learner effect. A family added to the logistic
champion therefore measures "family on a weak learner", and its gain may vanish if a LightGBM model is promoted.
Rule from now on: a new family gets a LightGBM challenger with `se1_lgbm_mm`'s params (read against se1 for the family
effect; the leaderboard's gain column stays "vs the current champion"). Logistic family challengers already registered
keep running unchanged. First: `se10_lgbm_event` (event family; embargoed with se8 under `event` until 2026-11-22). Embargoed families (flow, book, xvenue,
tte, wallet, rewards) get LightGBM versions only after their embargo dates, or as hidden predictions under the same
token if added earlier.

2026-10-21 ~10:15Z: hidden LightGBM versions added under their tokens, with se1's params and the matching logistic
spec's families / derived / isolates / require_sources: `se11_lgbm_flow` (flow, 11-22), `se12_lgbm_tte` (tte, 11-14),
`se13_lgbm_xvenue` (xvenue, 11-04). Predictions are written from their first fit; no score (prospective or development)
is computed or shown before the embargo date, and the walk-forward skips them until then. Not added yet: book, rewards,
wallet (refit budget first). Measured on the Mac copy (development data, 10 days): each extra LightGBM model costs ~110 s
of fit time (4 threads), the refit of 5 models peaked at 1.28 GB RSS (refit mem_mb 1500); host estimate ~3 min per LightGBM
model, 6 LightGBM + 7 logistic models ~20 min against the 3600 s timeout.
Known, self-healing: LightGBM `res_7d` fits fail with "inner split too small (train 0)" for every LightGBM model. A
resolution label's availability time is its fetch receipt time, the whole backlog was first fetched on 2026-10-21, so no
training row has its label before the validation cut. The split rule is causal and stays; the fits start once receipts
precede the cut (~6 days of steady fetches, around 10-28). The logistic `res_7d` fits are unaffected (no inner split).

## 19. Learner budget and the `regime` dead end (2026-10-21 ~19:30Z, development only)

The host fits of `se1_lgbm_mm` stop at or near the 300-round cap (best iteration 281 / 300 / 278 on 10-21 11:34Z). A
scratch development walk-forward on a Mac copy of the store (features, quotes, meta, logs, copied read-only from the
host; test days 10-18..10-20; every fit uses only data before the test day; LightGBM threads raised for speed, which
does not change the method) compared learner budgets on the champion's inputs. Mean paired dir_2h gain over the
champion, in nats (6 h, 24 h in brackets):

| config (se1's tree params unless stated) | dir_2h | vs se1 |
|---|---|---|
| se1 (300k rows, 300 rounds, early stop 30) | 0.0431 (0.0568, 0.0574) | - |
| 63 leaves, min leaf 300, 1000 rounds, stop 50 | 0.0433 | +0.0002 |
| 1000 rounds, stop 50 | 0.0433 | +0.0002 |
| 900k rows | 0.0450 (0.0592, 0.0595) | +0.0021 |
| **900k rows, 1000 rounds, stop 50** | **0.0456 (0.0601, 0.0597)** | **+0.0027** |

Capacity and rounds alone give nothing; more rows give a small, consistent gain on every horizon. The last row is
registered as `se17_lgbm_mm_900k` (no family, not embargoed). It was **selected** from four development configs, so
its development gain is optimistic; only prospective scoring counts. Consequences:
- The shared direction frame now holds up to 900k rows (the maximum over the active specs). Every other model still
  draws its own seeded `max_rows` subsample from it: same distribution, different realised rows from the 10-22 refit on.
- Host cost (Mac-to-host ratio from the se1 fits): se17 ~18-31 min of the refit on 1 thread; frame peak +~200 MB.
  q0512 `timeout_s` 7200 -> 10800 and `mem_mb` 1600 -> 2200. Prediction ~3x se1's (~45 s per capture).

**`regime` (not registered).** A candidate aux family of unsigned market-wide and category-wide activity: share of
eligible markets with |2 h change| > δ at the previous capture, and among rows received strictly before the market's
own row in the same capture, plus mean |2 h change| and |1 h change|. Science review: no leakage and no shadowed test
(REVISE for NaN receipt times, the receipt-order count, the variable k-1 gap and the per-capture common shock, which an
event-clustered CI ignores). On the development walk-forward above it was **worse** than se1 on every direction target
(dir_2h -0.0017, dir_6h -0.0022, dir_24h -0.0005 nats): about 12 distinct values a day are mostly capture-level noise
the trees overfit. The code was removed; do not retry without a new argument (e.g. a much longer history of captures).

## 20. Promotion rule `se-promotion-v2` (declared 2026-10-21 at its commit time, before any challenger can qualify)

**Why.** The v1 CI (condition 2) clusters by Gamma event only. A shock shared by all markets on one day (a news day, a
venue-wide move, a capture-level artefact) moves every event's gain together, so event clustering treats it as if it
were independent evidence. The science review of the `regime` family (§19) flagged this. v2 fixes it before any
challenger can be judged: the earliest possible v1 pass was 2026-11-04, and on 10-21 one day of scores exists.

**What changes.** Only condition 2. It now needs BOTH of these, at the same level `1 - 0.05/K`:
- **2a (v1, unchanged):** the event-clustered bootstrap percentile CI lower bound is > 0.
- **2b (new):** `mean - t_{n_days-1} * sqrt(V_event + V_day) > 0` on dir_2h in the 28-day window, where:
  - `V_g = G/(G-1) * sum_g (D_g - mean * N_g)^2 / N^2` is the linearised cluster-robust variance of the ratio mean over
    G clusters (D_g = sum of the paired gains in cluster g, N_g = its rows, N = all rows);
  - the event clusters are those of v1, and the day clusters are UTC origin days (the per-day sums the leaderboard
    already keeps for `days_positive`);
  - this is the Cameron-Gelbach-Miller (2011) two-way variance without its `- V_event x day` term. That term is a
    cluster variance (>= 0), so leaving it out can only widen the interval relative to CGM, and the variance can never
    come out negative. This is conservative relative to CGM, not a coverage guarantee (see Known limits);
  - `t` uses `n_days - 1` degrees of freedom because the day clusters are few (14-28).
- Ties: the largest 2b lower bound wins (v1 used 2a).
- Unchanged: conditions 1 and 3-7 and every constant. Condition 5 (secondary-target loss veto) stays event-clustered
  only. That is deliberate: the tighter interval makes the veto easier to trigger, which is the conservative direction.

**Known limits.** Origin-day clusters do not fully separate overlapping labels: a dir_24h label from a late capture
spans the next day. That is only a secondary target, and 2b is judged on dir_2h, where at most the last 2 h of a day
cross midnight. Shocks that persist over several days are only partly covered. The day-level `days_positive` share
(condition 3) is a second guard there.

**Code.** `promotion.py` (`cluster_var`, `twoway_bound`, `RULE_VERSION = "se-promotion-v2"`). `registry.json`
must declare exactly this rule: `evaluate` refuses to promote when the registry declares a different rule or none. The leaderboard
metrics and `scoring_version` are unchanged. Tests: a day-shock case that v1 passes and v2 blocks; a steady gain
passes both; one day and zero rows fail safe; a hand-computed `cluster_var`; the rule-mismatch refusal.
Science review (2026-10-21): ACCEPT_WITH_FIXES (exact registry match, the "relative to CGM" wording, edge-case
tests). All fixes are applied. It agrees that condition 5 stays event-only, and that the timing is legitimate
because 2b cannot be computed with one day of scores.

**Dashboard view (2026-10-21 ~21:05Z, display only).** `dashboard.json` carries `promotion`: the rule, K, level and,
per non-embargoed candidate, the seven checks, `days_to_min` (days until 14 days of age), the event-only lower bound
`lo_event`, the two-way bound `lo_twoway` and its components `se_event` and `se_day`. It copies the leaderboard's
decision and never recomputes it. Embargoed models are skipped in `dashboard._promotion` and again in `lab_host`.

## 21. Book timing and promotion eligibility (2026-10-22 ~00:50Z; science review REVISE, applied)

**The overlap.** Direction labels are measured from the origin capture's Gamma mid (rows received ~hh:31Z). The `book`
family is read from sweep 1 of the same pass, which starts ~7 min later (e.g. capture 22:31:01Z, sweep 1
22:38:19-22:39:38Z, sweep 2 22:39:38-22:40:58Z, predictions written ~22:58Z). Predictions are still write-once and
written before the target capture, but the book inputs are observed inside the label window.

**Measured (host, two captures of 10-21, development diagnostic, ~50k eligible markets each):**
- |sweep-1 mid - origin Gamma mid| > DELTA: 6.4% and 5.4% of eligible markets; |2 h label move| > DELTA: 19.9% and 16.6%.
  So about a third of 2 h movers have already moved by the time the sweep is read.
- Correlation with the in-window move (`pre` = sweep-1 mid - origin mid): `bk_micro` -0.276 / -0.224; `bk_imb1c`
  -0.061 / -0.041; `bk_imb5c` -0.051 / -0.032. With the rest of the move (`post` = target mid - sweep-1 mid): `bk_micro`
  +0.127 / +0.073. With the whole label move: small and mixed in sign (-0.06 to +0.05).

**Why it matters.** The primary score is the 3-class log loss of dir_2h. Magnitude information (flat versus moved)
counts, and `bk_age_s` is close to a "the book updated after the origin" flag. A model holding book inputs can
therefore be scored partly on a move that has already happened. The bias favours only models with book inputs, and its
size cannot be bounded from the evidence, so it is treated as material.

**Decisions:**
1. **CH200 `sweep2` declined.** Sweep-2 minus sweep-1 mid is a direct piece of the label's own path (CANDIDATES.md row 18).
2. **`se7_lgbm_all` is promotion-ineligible** on the origin-anchored dir_2h (`config.PROMOTION_INELIGIBLE`, since
   2026-10-22T00:50Z). It is still predicted, scored and shown, and its dashboard row carries `eligible: false`.
   - It still counts in K, so the level `1 - 0.05/K` that se1 and se17 face is not loosened.
   - No pinned spec, rule constant or formula changed.
   - The reason is the timing measurement above, not any se7 score. Disclosed: se7's day-1 leaderboard (10-21, one
     day) had been seen, about +0.05 nats over the champion, the same as se1.
   - The entry is never removed. A later diagnostic cannot restore eligibility.
3. **The isolating book models `se3_lr_book` and `se14_lgbm_movetype` are promotion-ineligible too** (same `since`,
   science re-check). They are declared while embargoed (book until 2026-12-31 since round 4), before any of their scores was
   computed or seen. They are still predicted, and they are scored once their embargo lifts.
4. **Future fix (built 2026-10-22 as `book0`, section 22):** a `book` v2 family read from the previous pass's last sweep, strictly before the origin,
   and/or a new broad model built on it. It would be registered and frozen as a new spec, and it would build its own
   prospective age. Optional development diagnostic: se7 versus se1 on a sweep-anchored label, for information only.

## 22. `book0`: the order book strictly before the origin (2026-10-22 ~03:00Z)

**Family `book0` (`se-aux-book0-v1`, `aux.py`).** The honest replacement for the sweep-1 `book` family (section 21).
- **Which sweep:** the newest complete **pass** sweep (its `snapshot_id` is an indexed grid capture that started before
  the origin) whose manifest `finished_utc` is before the origin capture's `started_utc` and at most 3 h before it
  (ties: higher `series_index`). Ad-hoc or subset sweeps and hidden `.tmp_` folders are never chosen. One sweep per
  capture, for every market. On the host this is the previous pass's last sweep, ~110 min
  before the capture. Nothing within 3 h: every column is NaN (never filled from an older sweep). Sweep rows received
  at or after the capture start are dropped (defensive; none expected).
- **Columns:** the eight `book` columns with the same formulas (`b0_` prefix; `book_columns` is shared with
  `features.book_features`, output unchanged), plus `b0_lag_s` (capture start minus the row's receipt), `b0_spread`
  (sweep ask minus bid) and `b0_gap` (origin Gamma mid minus the sweep mid: a pre-origin price change, not a
  sweep-after-origin gap).
- **Inputs:** sweep files only (no snapshot rows), so tables are buildable for every capture in the store. The table
  metadata records the sweep id, its `snapshot_id`, `series_index` and `finished_utc`, and the sha256 of its manifest
  and rows.
- **Causality rests on the construction, not on any correlation.** `book_sweep.run_sweep` writes a sweep in a `.tmp_`
  folder, stamps `finished_utc` (same host clock) after the last batch's receipt, then renames it, so a finish time
  before the capture start bounds every row receipt. The ~110 min margin dwarfs any clock skew.

**Models.**
- `se18_lgbm_all_b0`: `se7_lgbm_all` with `book` replaced by `book0` (same learner, params, derived sets, other
  families). Broad, so not embargoed (section 8) and **promotion-eligible**. It holds Gamma liquidity and `b0_depth5c`
  as separate columns (no hollow column), as se7 does. It raises K from 3 to 4 (se1, se7, se17, se18), which makes
  the level stricter for every challenger. Read against se1 and se7.
- **Disclosed: the se7 minus se18 contrast.** Both broad models are visible, so the difference of their scores is a
  visible comparison of the sweep-1 book against `book0`, i.e. book information under the 12-31 embargo, close to LT6
  V's "imbalance at k-1's sweep" control. Judged acceptable (science review 2026-10-22): the post-origin overlap of
  se7 (section 21) dominates that difference, and se7 is promotion-ineligible. Written down like the `hollow` note.
- `se19_lr_book0`: the `se3_lr_book` analogue on book0 (isolates `book0` and `book`; embargoed to 2026-12-31). The
  learner-matched LightGBM version (section 18) waits for refit budget.
- Embargo token `book0` (same date and tests as `book`). It also hides `book0` in se18's family attribution.
- Both specs set `require_full_coverage`, so they fit only once every labelled capture in the window has a book0 table
  (one-off host backfill after deploy).

**Development diagnostic (host, 8 captures of 10-21, ~50k eligible markets each; information only, not a score).**
- Lag ~110 min; coverage 92-94% of eligible markets.
- Correlation with the in-window move (own sweep-1 mid minus origin Gamma mid): `b0_micro` -0.11 to +0.02 (mostly
  |r| < 0.05) and `b0_imb5c` -0.00 to +0.04, against v1 `bk_micro` -0.27 to +0.17. This is consistent with the
  construction above; it is a symptom, not the proof of causality.
- `b0_gap` correlates -0.08 to -0.28 with that move and -0.04 to -0.16 with the 2 h label move: a reversal of the
  pre-origin change, from inputs that all predate the origin. Part of it may be anchor or quote-bounce reversal (the
  label's own anchor, the Gamma mid, against an earlier CLOB mid) rather than a real market move; it counts for
  forecast quality only. `b0_spread` correlates +0.09 to +0.15 with a move larger than DELTA.
- **Order of events (disclosed):** the columns (including `b0_gap` and `b0_spread`) and both specs were written before
  this diagnostic was run; the diagnostic, including the correlations with the 2 h label, was seen before the specs
  were committed, and nothing was changed after it.
- **Backfill:** the one-off host backfill writes book0 tables for past captures as training inputs only. No prediction
  is ever written for a capture whose 2 h target slot has started (`predict.py`, section 6), so the prospective age of
  se18 / se19 starts at their first live prediction (`promotion.first_prediction_ts`).


## 23. `crypto`: a spot-price reference for crypto template markets (2026-10-22 ~06:00Z)

**Family `crypto` (`se-aux-crypto-v1`, `aux.py`; CANDIDATES builder row 20, which unblocks row 5).** Polymarket lists
thousands of crypto markets whose fair price is a function of one spot price (up/down windows, strike ladders, "hit
price" barriers). The champion sees only each market's own price history; this family gives it the spot path.
- **Mapping (no text parsing):** a market is mapped when its own sidecar row (`rows_ext`, same capture) has
  `fee_category == "crypto"` and a `series_slugs` entry matching `<asset>-<kind>-<cadence>` with kind in up-or-down,
  multi-strikes, neg-risk, hit-price and asset in a fixed list (btc/bitcoin, eth/ethereum, sol/solana, xrp, bnb,
  doge/dogecoin, zec/zcash, hype/hyperliquid, ethena, chainlink/link) mapped to a Binance USDT pair. Strikes are not
  known (no question text in captures), so ladders and barriers are read through the market's own empirical beta to
  spot. Capture 10-22 04:31Z: ~4,800 of 5,870 crypto sidecar rows map. Unmapped markets: `cr_has = 0`, rest NaN.
- **Spot inputs:** Binance spot klines (`data-api.binance.vision/api/v3/klines`, public market data; 1000 x 1 m and
  1000 x 5 m bars per mapped asset) requested with `endTime` = capture start - 1 ms, and kept only if the bar **closed
  at or before the capture start** (re-checked when read). Closed klines are venue-clocked and not revised. They are
  stored write-once per capture in `aux_inputs/crypto/<capture>.json.gz` with their fetch time; the table metadata holds
  that file's sha256, the fetch time and the symbols. A capture with no mapped market fetches nothing; a failed request
  writes nothing (retried next tick; never filled from another capture).
- **Columns (15):** `cr_has`, `cr_kind` (1 up/down, 2 strikes, 3 neg-risk, 4 hit-price), `cr_cad_h` (up/down window
  length), `cr_win_h` (window start minus capture start, hours); spot log returns `cr_r5m`, `cr_r30m`, `cr_r2h` (1 m
  closes), `cr_r24h` (5 m); realised volatility `cr_rv1h` (last 60 x 1 m) and `cr_rv24h` (288 x 5 m, per-hour scale);
  for up/down windows that started before the capture, `cr_ud_z` = log(spot / window open) over rv x sqrt(time left)
  and `cr_ud_gap` = Phi(z) minus the origin mid; `cr_beta` = the market's own 2 h mid change regressed on the 2 h spot
  log return over the previous 36 two-hour pairs (latest pair excluded, >= 4 finite pairs), `cr_lag` = beta x the
  latest spot return minus the latest mid change, `cr_xs` = |beta| x rv1h x sqrt 2. Spot is NaN for an asset with no
  closed 1 m bar within 5 min of the capture start (columns stay NaN, never carried forward).
- **Causality:** every spot value is from a bar closed before the capture start; every mid is the engine's own quotes
  file of the origin slot or earlier (written by the feature step before any aux table). The origin's Gamma mid is
  received after the capture start, so it may already contain spot moves of those minutes; that can only weaken the
  family, never give it future information.
- **Limits (disclosed, science review 2026-10-22 ACCEPT_WITH_FIXES):**
  - Binance spot is a proxy, not each market's resolution source. CB13-R closed on exactly that basis gap (GR basis
    0.915), and short-cadence up/down markets may resolve on another feed (e.g. Chainlink). The family is a forecast
    input only; nothing here claims the reference equals the settlement price.
  - The window open is the open of the Binance 1 m bar that opens at `end_ts` minus the cadence. Daily up/down markets
    use the close of the 1 m bar labelled 12:00 ET (`cb8_updown.py`), one minute later; kept as written.
  - `cr_win_h`, `cr_ud_z` and `cr_ud_gap` are NaN for every market that is not an up/down window. `cr_ud_gap` assumes
    outcome 0 (the engine's `ms_mid`) is "Up", the Polymarket listing order; not checked per market.
  - A market missing from the sidecar has `cr_has` NaN (unknown, the engine's convention), not 0. A symbol Binance
    answers with HTTP 400 is recorded in the inputs file's `unavailable` list and its columns stay NaN (permanent, not
    retried); every other failure writes nothing and is retried. All requests of one capture share a 120 s budget, so
    a slow network cannot push a pass's tick past its timeout before predictions are written. The table metadata also
    records the sidecar's sha256.
  - On 10-22 every symbol in the list (including HYPEUSDT, ENAUSDT, ZECUSDT) answered 200 from the host.
- **Coverage and first fit:** snapshot rows (and sidecars) are kept only from 10-13 04:31Z (temporary 10-day snapshot
  retention), so the 14 engine captures before that have no crypto table and never will (missing stays missing).
  With `require_full_coverage`, se20's direction fits start once those captures leave the 14-day window (the
  10-27 refit, like se8 / se10 / se16) and `res_7d` once they leave the 28-day one (~11-10).
- **Backfill:** tables for past captures fetch the same closed bars now, after the fact (public, immutable data); they
  are training inputs only. No prediction is written for a past capture (section 6), so se20's prospective age starts
  at its first live prediction.

**Model `se20_lgbm_crypto`:** LightGBM with se1's params on the champion's families + `crypto` (learner-matched,
section 18; read against se1). `require_full_coverage` and `require_sources: ["crypto"]`.
- **Embargo: none.** No registered or drafted live test uses a spot reference: CB13-R (CH118, the Binance barrier test)
  closed "not testable (basis)" on 2026-10-21 ~19:58Z, and E019 / LT6 use crypto only as a population or cluster label.
  `cr_win_h` + `cr_cad_h` give time to the end for up/down markets, which the champion's `log_hours` already holds, so
  this adds nothing to E014's `tte` token.
- **Promotion:** eligible, and it raises the non-embargoed K from 4 to 5 (se1, se7, se17, se18, se20), which makes the
  level stricter for every challenger.
- **Order of events (disclosed):** the columns and spec were written on 2026-10-22 between 02:23Z and 02:41Z (the session that was cut off) before any crypto table
  was built on real captures (a host coverage diagnostic was attempted and not run); the coverage count above
  (sidecar slugs only, no outcomes) was read at ~05:45Z, after the spec, and nothing was changed after it.
- **Tick aux budget (operational fix, 2026-10-22 ~06:00Z):** a features run built at most `max(2 x max_items, 4)` aux
  tables, 4 at a pass's tick, so with 6 families the 5th and 6th (`participation`, `book0`) of each new capture waited
  for the next pass, after the capture's 2 h target had started (seen on capture 10-22 04:31Z; se16 has no fit yet
  and se18 / se19 had not predicted, so no prediction was affected). The budget is now `len(AUX_FAMILIES) x max_items`
  (newest capture first), so every family of a new capture is built before its predictions in the same tick.

## 24. Market-price reference for `res_7d` (2026-10-22 ~21:00Z)

**Why.** AREPO's question is whether information beyond the market price predicts outcomes. On the resolution target
the obvious forecast is the price itself, and until now no leaderboard row said whether the champion (or any model)
beats it. The direction targets have no comparable price forecast (their natural benchmark is the class frequency,
which every fitted model already contains), so this is `res_7d` only.
- **Reference `market_price_reference` (`scoring.REF_MODEL`):** P(yes) = `ms_mid` of the origin's write-once features
  file, i.e. the outcome-0 Gamma mid `(best_bid + best_ask) / 2` at the capture, the same price every model sees.
  No fit, no parameter, no prediction file (it is a function of a stored capture-time observation, so there is nothing
  to write once). Scored on every labelled, res-eligible row with a finite mid; clipped like every probability
  (`P_CLIP`). Coverage = rows with a finite mid / eligible rows.
- **Rows.** One leaderboard row per window (`role: "reference"`, `target: res_7d`) with the usual metrics and
  `gain_vs_champion` = ll(champion) - ll(reference) on rows both scored (negative: the price beats the champion).
  Every scored model's `res_7d` row carries `gain_vs_market_mid` = ll(reference) - ll(model) on that model's scored
  rows (event-clustered bootstrap CI, as every gain); `dashboard.json` carries it as `gain_vs_mid` / `_lo` / `_hi`.
- **What it is not.** Not a model, not in the registry, never a promotion candidate, never in the family-gain series,
  no effect on K, the promotion rule (`se-promotion-v2`) or any existing score. Embargoed models get no
  `gain_vs_market_mid` before their date (they are not scored at all). A positive gain over the mid is forecast
  quality on a 7-day resolution window, not an edge or profit claim: no costs, no fill, and the mid is not a price
  anyone can trade at.
- **First rows:** the daily score of 2026-10-23 (the reference covers the 28-day lookback of stored features at once,
  i.e. the champion's history since 10-21; LightGBM `res_7d` rows appear once those fits work, ~10-28).

## 25. `hwm`: own high-water marks (2026-10-22 ~22:00Z; development family)

**Why.** CH181 (`CREATIVE_HYPOTHESES_2026-10-25.md`): a market near a salient extreme of its own path may behave
differently from one in the middle of its range (George and Hwang 2004 on the 52-week high: anchoring at the peak). The
champion's momentum family holds fixed-horizon changes only, so it cannot see where the price sits relative to its own
recent highs and lows. LT5 H (the live test of CH181) was dropped at census, so no test is shadowed. Ideas only: no
evidence yet, development or prospective.
- **Aux family `hwm` (`se-aux-hwm-v1`, `aux.hwm_features`):** from the engine's own quotes files of slots k - 84 .. k
  (the earlier captures plus the origin's own mid, the same inputs as `surprise`; no snapshot rows). Over the
  earlier slots of the window only (so a new high gives a negative distance):
  - `hw_dhi3d`, `hw_dlo3d`, `hw_dhi7d`, `hw_dlo7d`: highest mid minus the origin mid, and origin mid minus the lowest,
    over 36 / 84 earlier 2 h slots (3 d / 7 d); missing below 12 / 24 quoted slots or without an origin mid.
  - `hw_agehi7d`, `hw_agelo7d`: hours since the 7 d high / low (2 h per slot, the newest earlier slot is 2 h; ties go
    to the most recent).
  - `hw_pos7d`: (mid - low) / (high - low) over 7 d, missing when the range is below one cent.
  - `hw_cov7d`: share of the 84 earlier slots quoted (history is truncated for markets older than AREPO's captures).
- **Windows of 3 d and longer only,** so the family carries no 6 h step path (LT7 `capath`, CH191) and no time-of-day
  schedule (LT8 `sched`, CH204). No embargo token. `hw_dhi7d + hw_dlo7d` is the 7 d range, a volatility measure near
  `sp_rv7d` (`surprise`, E011 until 11-19); no token is needed because E011 tests a frozen detector, not a learned
  direction score, and the champion already holds `ms_rv24` and the 1 w change.
- **Departures from CH181 as listed in CANDIDATES:** raw probability distances, not within-market SD units (dividing by
  own volatility would bring the `surprise` quantity in); no explicit new-extreme flag (it is `hw_dhi* < 0`, and
  `hw_pos7d` is not clipped: above 1 at a new high, below 0 at a new low); `hw_cov7d` is reported even below the
  24-slot minimum.
- **Science review (2026-10-22 ~22:10Z): ACCEPT_WITH_FIXES.** No leakage (extremes over earlier slots only; the origin
  quotes file is the same capture's Gamma rows as the label anchor; no sweep input, so §21 does not arise); no token
  needed (LT5 H and E021 dropped; LT7, LT8, LT9 draft, E015, E022 checked); not promotion-ineligible. Fixes applied:
  the `surprise` rationale, the departures and the ranges above, written down. One availability caveat: a quotes file
  that arrived late enters a backfilled table but would not have entered a live-built one (not leakage).
- **Challenger `se21_lgbm_hwm`:** LightGBM with `se1_lgbm_mm`'s parameters on the champion's features plus `hwm`,
  `require_full_coverage`, read against se1 for the family effect. One pre-declared configuration, no development
  selection; its first evidence is prospective. K rises by one (the conservative direction for every challenger).
- **Backfill.** `run_aux` builds the table for every processed capture whose features file exists, newest first, from
  quotes files written at or before that capture. A backfilled table is a deterministic function of stored pre-origin
  observations, like every earlier aux family; training still uses only labels available before each fit.
- **Cost.** About 8 float32 columns on the direction and resolution frames (~55 MB at the caps), one more LightGBM fit
  per refit (~2 min of the ~48 min), one more prediction per capture. The q0512 / q0513 caps are unchanged.
- Tests: `test_hwm_features_hand_example`, `test_hwm_family_reads_only_earlier_quotes`.

## 26. `dispgap` and `dormant`: two engine-first round-14 families (2026-10-22 ~23:15Z; development families)

**Why.** Round 14 (`CREATIVE_HYPOTHESES_2026-10-28.md`, section 2 C / D) proposed CH218 and CH220 as engine-first: each
is a per-market, per-capture quantity that no live test can contrast honestly, so its only honest yardstick is forecast
quality. LT9 section 6.2 left both to the engine. Ideas only: no evidence yet, development or prospective. Each gets its
own challenger (champion + one family, se1's learner), so the family effect is read against se1. K rises by one per
challenger (se22 from 11-14, se23 from 11-19, when their embargoes lift): the conservative direction, and a small cost
(Bonferroni z(1 - 0.05 / 2K) about 2.73 at K = 8 -> 2.81 at K = 10).
- **`dispgap` (`se-aux-dispgap-v1`, `aux.dispgap_features`, CH218).** Gamma's venue-computed `oneDayPriceChange` and
  `oneWeekPriceChange` (the champion's `mo_chg_1d` / `mo_chg_1w`, what the site's mover lists rank on) against the host's
  own path at the capture clock. Where they disagree, one of them is stale or uses a different reference.
  - `dg_1d` = `mo_chg_1d - mo_d24h`. This is the difference of two champion columns, made explicit because trees
    approximate differences poorly.
  - `dg_1w` = `mo_chg_1w` minus the own 7 d mid change (the quotes mids of slot k and slot k - 84). Missing without both.
  - `dg_abs1d` = |`dg_1d`|.
  - `dg_vs2h` = `dg_1d` x sign(`mo_d2h`). It is positive when the display shows more move than the book in the direction
    the book just moved, and 0 with no 2 h move. CH218's money route (display ahead of a move the book has unmade) is
    its negative tail.
  - `dg_chg` = `dg_1d` minus the previous slot's `dg_1d`, read from the previous slot's features file and matched by
    market id. It separates a fresh disagreement from a persistent per-market trait of the venue's computation, which is
    CH218's "boring explanation".
  - Inputs: the features files of slots k and k - 1, and the quotes files of slots k and k - 84. The table records
    `prev_features_capture_id`.
  - **Departures from CH218:** no two-tick flag (`dg_abs1d` carries it, and trees split on it at any level). `dg_sign`
    is replaced by `dg_vs2h`, CH218's own money-route sign. `dg_chg` is added for the persistence question.
  - **Embargo token `dispgap` to the later of 2026-11-14T00:00Z and LT2's analysis commit (E012, E013, E014).**
    CH218 proposed a token tied to LT7's `capath`; LT7 closed at census with no test (`capath` withdrawn 2026-10-23T00:00Z),
    so that reason is gone. The builder's first draft said no other test reads the venue's 1 d / 1 w fields. That was
    wrong (science review): LT2 is running, and E012 pre-declares Gamma `oneDayPriceChange` in place of its `x` (the own
    24 h change) as a sensitivity, so `dg_1d` is exactly E012's primary `x` minus its sensitivity `x`. se22 is scored on
    `dir_24h`, E012's horizon. E013 / E014 use `chg_1d` / `chg_1w` as controls (`LIVE_TESTS_2.md`). The contrast does not
    isolate E012's `x · zL` term, but hiding se22 until LT2's analysis costs only about three weeks. LT8 CH202 (`swclock`)
    is a different object. The `chg_1h` field is not used.
- **`dormant` (`se-aux-dormant-v1`, `aux.dormant_features`, CH220).** Run lengths of the 2 h steps ending at the origin in
  which the mid did not move. Inputs: the engine's own quotes files of slots k - 12 .. k, with the origin's own quotes
  mid last (as `surprise` / `hwm`).
  - `dm_flat`: steps with |dmid| <= DELTA (0.005, the direction targets' own flat band), capped at 12 (24 h).
  - `dm_still`: steps with no change at all (<= `DELTA_TOL`), capped at 12.
  - A run that reaches an unquoted slot before a move or the cap is missing (NaN). A capped run or a run ended by a move
    is known.
  - `dm_woke`: 1 when the last step moved by more than DELTA after at least 6 known flat steps (12 h); 0 when the last
    step did not move, or the run before it was known to be shorter; NaN otherwise.
  - **Departure from CH220:** the run uses the targets' DELTA rather than "one tick" (ticks vary by market, and DELTA is
    the flat class the targets score). `dm_still` keeps the any-change reading.
  - **Embargo token `dormant` to 2026-11-19T00:00Z (E011, the same date as `surprise`).** CH220's text asks for the
    `surprise` embargo. The builder first read that as "compare with se15 only after `surprise` lifts", by `hwm`'s
    reasoning. The science review overruled that: E011's surprise label requires a quiet prior day, its secondary (a)
    reads "quiet markets that then move", and `dm_flat == 12` / `dm_woke` encode exactly that quietness, which `hwm`'s 7 d
    range did not. The token lives in `config.EMBARGO`, so the pinned spec sha is unchanged (se23 isolates `dormant`).
- **Census (counts only, no outcome; fixed before it runs, science review must-fixes 4-6).** These are round 14's kill
  lines, made exact.
  - **Frame:** every row of the family's aux tables (one row per eligible market; the tables are built on the features
    file's rows) of the captures that started in [2026-10-16T00:00Z, 2026-10-23T00:00Z). These are 84 slots, all
    collected before the families existed. "Non-sports" means `category != "sports"` (the features file's
    `fee_category`), with `unknown` counted as non-sports.
  - **`dispgap`:** killed if qualifying rows are fewer than 2% of all frame rows. A row qualifies when `dg_1d` is
    finite, `ms_tick` is finite and > 0, and |`dg_1d`| >= 2 x `ms_tick`. Rows with a NaN `dg_1d` or a NaN or zero tick
    count in the denominator as not qualifying. Reported for all rows and non-sports, alongside the NaN shares of
    `dg_1d` and `ms_tick`, the median |`dg_1d`| in ticks, and the within-market share of rows whose |`dg_chg`| is under
    one tick. The last is CH218's persistence question, reported but not a kill line.
  - **`dormant`:** the 3% / 60% line applies to **`dm_still == 12`**. CH220 declared it on "slots since |mid change| >= 1
    tick", i.e. no change at all for 24 h, and `dm_still` is that variable; `dm_flat` uses the wider DELTA band and
    would move the share. Killed if `dm_still == 12` rows are fewer than 3% or more than 60% of the non-sports frame rows.
    NaN rows count in the denominator as not dormant. The NaN share is reported, and `dm_flat == 12` is reported for
    information only.
  - **Order:** the census runs on the host right after the backfill (2026-10-22 ~23:30Z), before the daily refit
    (~15:44Z) can make a first fit. If the refit ran first, a killed challenger would still be set `retired` before any
    of its scores is computed or shown, which the embargoes already guarantee until 11-14 / 11-19. A killed family's
    challenger is set `retired`, with a ledger line.
- **Challengers `se22_lgbm_dispgap`, `se23_lgbm_dormant`.** LightGBM with `se1_lgbm_mm`'s parameters and se21's train
  block (`require_full_coverage`, `require_sources` = the family). One pre-declared configuration each, no development
  selection. Their first evidence is prospective.
- **Leakage and timing.** Neither family reads a sweep, a snapshot row or anything received after the capture.
  - `dg_1d` / `dg_vs2h` / `dg_abs1d` are functions of capture k's own champion columns.
  - `dg_chg` reads the earlier slot's features file.
  - The quotes inputs are the same files `surprise` and `hwm` read.
  - Section 21's sweep-timing issue does not arise.
- **Cost.** 8 float32 columns in total on the frames (~55 MB at the caps), two more LightGBM fits per refit (~4 min of
  the ~48 min), and two more predictions per capture. The q0512 / q0513 caps are unchanged; the peak RSS is watched at
  the 10-23 refit.
- **Science review (2026-10-22 ~23:10Z): ACCEPT_WITH_FIXES.**
  - No leakage: no sweep, no row received after the capture, `dg_chg` from slot k - 1 only. Section 21 does not arise,
    and neither challenger is promotion-ineligible. There is the same availability caveat as `hwm`: a late quotes or
    features file enters a backfilled table but would not have entered a live-built one.
  - Fixes applied: the tokens `dormant` (11-19, E011) and `dispgap` (11-14, LT2); the false sentence above corrected;
    the section 8 table and the K path; the census column, denominators and order; a real oldest-slot test in place of
    a tautological one.
  - Not verified, and noted: the reference price behind Gamma's `oneDayPriceChange` (last trade or mid; absolute
    change). The census reports its scale against the own 24 h change.
- Tests: `test_dispgap_features_hand_example`, `test_dormant_features_hand_example`,
  `test_dispgap_and_dormant_read_only_earlier_inputs`, and registry assertions in
  `test_repo_registry_loads_and_embargo_assignment` (embargo dates).

## 27. Per-market signal feed `se-feed-v1` (2026-10-23 ~02:30Z; display output, no scoring change)

North Star output 6: the engine's suggested signals, per market, for the owner's /lab first. A public website surface
needs a separate owner-approved web deploy, and its own wording review.
- **Source.** Only the current champion (`specs.current_champion`). It is never shown while `specs.embargo_of` covers
  the champion; lab_host re-checks this on every push. The values are the stored quantised probabilities of the
  champion's newest write-once `predictions/<capture>/<champion>.parquet`, read back with `predict.dequantise_dir`.
  Nothing is refitted or recomputed. The feed carries the prediction's receipt time (`written_utc`) and sha256 from the
  predictions log. A features file that no longer matches the prediction's pinned `features_sha256` gives no feed.
- **Signal strength** = P(up) - P(down) for each direction target, in [-1, 1]. The value is null where the market is
  not eligible for that target.
  - Ranking: |`s_2h`| (the primary target), then log liquidity, **only inside the display pool**: spread <= 2c and mid
    in [0.05, 0.95]. The pool was declared 2026-10-23 ~02:45Z, before any outcome was read. It is a display choice,
    not a model change. The first host build (capture 10-23 00:31Z, no pool) ranked 2-3c longshots with 3-5c
    spreads on top. On such books the 0.5c flat band lies far inside the spread, so the strength mostly reflects the
    mid's quote mechanics, not a move a user could act on. `pool.markets` reports the pool size.
  - It lists the top 20 up and the top 20 down, and per target the eligible count, counts with |s| >= 0.1 and >= 0.25,
    the mean, and `valid_until` (the target slot).
  - `res_7d` is left out: a model-versus-price gap at resolution reads as a trade suggestion.
- **Context shipped with it.**
  - The champion's own 14-day prospective leaderboard rows (log loss, Brier, AUC, calibration) for the direction
    targets.
  - The label "forecast quality only: not a probability of profit, not an edge claim, not advice".
- **Titles.** One bounded public Gamma `markets?id=...` request (at most 60 ids, 10 s timeout) for ids not yet in
  `feed/titles.json` (cache capped at 3,000). A failure only leaves `title` / `url` null (`titles_error`).
- **Where.** `run_signal_engine.py tick` rebuilds `feed/latest.json` (a rewritable view, never evidence) when the
  champion has a newer prediction than the current feed. It never changes the tick's exit code (`feed_error` on
  failure; `--no-feed-titles` skips the lookup). `lab_host.build_signal_feed` embeds the feed as `signal_engine.feed`.
  It is stale after 6 h, dropped if the feed is not the current champion's, and dropped first when the snapshot is
  over its size limit.
- **Cost.** Reads one predictions parquet and 6 feature columns per new capture (~55k rows), well under 100 MB and 1 s.
  The output is about 15 KB.
- Tests: `test_signal_feed_reads_back_the_champions_stored_prediction`,
  `test_signal_feed_title_failure_and_embargoed_or_misaligned_champion`, `test_lab_host_signal_feed_recheck`.

## 28. LT10 round 7: `kxbook`, `attrlimit_lt10` and a second `xvenue` read root (2026-10-23 ~04:10Z; no scoring change)

Applied from `CANDIDATES.md` round 7 (LIVE_TESTS_10.md section 9, design text frozen at 34b7e22e), before any `kxbook`
family or `se-aux-xvenue2-v1` exists, so nothing has been computed or shown on these terms.
- **Embargo.** `config.EMBARGO` gains `kxbook` (until 2026-12-04T00:00Z, LT10-CH224 / CH223 / CH222) and
  `attrlimit_lt10` (kind `attribution_limit`, same date, `no_broad_families: ["kxbook"]`), with the requested text
  verbatim. `xvenue` is not extended: `se4` / `se13` at their current spec versions hold capture-time levels only and
  still lapse at 11-04. When `se-aux-xvenue2-v1` is built, `kx_last_chg_2h`, `kx_pull_2h` and `kx_spread_chg_2h` go into a
  separate `kxbook` family (not `xvenue2`); any spec holding it isolates `kxbook`, and no broad spec may hold it.
- **Second read root (LT10 step O3).** `features.xvenue_features` reads E009's `cross_venue_live/quotes/` and the
  quotes-only successor's `xv_quotes/quotes/` (`config.XV_QUOTES2_ROOT`, `Paths.xv_quotes2`). It is one continuous
  stream with the same line schema (the successor adds a trailing `"src"`); quotes from both are pooled under the
  unchanged rule (last `k_recv` before the capture start per market, age <= 30 min). No column definition changes, so
  `se-features-v1` and every spec hash stay as they are. While the second directory is absent or empty the output and
  the meta `inputs.xvenue` string are identical to before; names from the second root are prefixed `xv_quotes/`. This
  keeps `se4` / `se13` from getting NaN `xvenue` inputs after the handover.
- Tests: `test_lt10_round7_requests`, `test_xvenue_reads_both_roots_and_keeps_e009_src`; the LT7/LT9 broad-spec test now
  also lists `attrlimit_lt10`, and its generic loop fails if a broad spec holds `kxbook`.

## 29. `tilt`: collateral-tilt levels (2026-10-23 ~13:10Z; development family, CH235)

**Why.** Round 16 (`CREATIVE_HYPOTHESES_2026-10-30.md` section D) ranks CH235 first of its engine-first families. On a
binary venue the price of a share is its collateral, so a maker paid per minute or per fill is pushed to the cheap side
`min(p, 1 - p)`, and the taker fee has the price shape `rate x p(1 - p)`. The logistic champion holds `mid` and the
category only as separate main effects and cannot form either shape. Prior: HB1 PX1 (longshots drift down over 24 h)
survived as a level fact, and PX5 carried the same sign without surviving Holm. Ideas only: no evidence yet.
- **Aux family `tilt` (`se-aux-tilt-v1`, `aux.tilt_features`), level columns only.** p = the origin Gamma mid (`ms_mid`).
  - `tl_collat` = min(p, 1 - p); `tl_cheap_side` = sign(p - 0.5); `tl_spread_collat` = spread / `tl_collat`.
  - `tl_fee_ps` = the market's own Gamma `fee_schedule` rate x (p(1 - p)) ** exponent (exponent 1 when absent); 0 where
    `fees_enabled` is false; NaN without a schedule. No docs-rate fallback: `costs.taker_rate`'s conservative 0.07 for an
    unknown category is a cost-check convention, not a measured value, so missing stays missing.
  - `tl_rebate_ps` = the schedule's `rebateRate` x `tl_fee_ps` (0 where fees are off; `rebateRate` is the fee-rebate
    share, not the liquidity-rewards programme).
  - Inputs: capture k's features file and its own sidecar `rows_ext.csv.gz` (the same Gamma response as the origin row),
    whose sha256 the table records (`rows_ext_sha256`). An older sidecar without the fee columns gives NaN fee columns.
- **Not built.** `tl_w2h` (a collateral weight signed by the 2 h move, the post-move analogue of CH234's `w`):
  `LIVE_TESTS_11.md` section 9 asks that no scored family hold it before LT11's freeze (CH234 is LT11's lead test), and
  that is followed exactly; it may come back as a new aux version after the freeze, under `dollarw` if CH234 registers.
  The dated `tl_w_traded` (11-22, `movetype`) and `tl_rew_outside` (11-18, `rewards`) are not built either.
- **Departures from CH235:** the rebate uses the per-market schedule's `rebateRate`, not the category's docs share; an
  exponent of 0 is taken literally (every observed schedule has exponent 1).
- **No embargo token.** LT11 section 9 names `tl_collat`, `tl_cheap_side`, `tl_fee_ps` and `tl_rebate_ps` as levels that
  may be built; `tl_spread_collat` (the origin spread over min(p, 1 - p)) is a level of the same kind and none of the hold's
  three objects (a weight x move product, a siblings' bid- / ask-sum change, a 0.10 / 0.90 crossing indicator). With no move-signed column, neither challenger isolates
  CH234: se24's trees can form sign(d) x (p - 0.5) from `mo_d2h` and `tl_cheap_side` exactly as se1 can from `mo_d2h` and
  `mid`, which is LT11's requested `attrlimit_lt11` (no attribution of se1 or broad models on mid x own 2 h change), not a
  family token. se25's logistic holds the level and the move as separate main effects only. **Request for LT11's freeze:**
  `attrlimit_lt11`'s models list should name `se24_lgbm_tilt` and `se25_lr_tilt` beside the champion, se1 and broad models
  (science review must-fix; the engine's per-family attribution never computes that interaction, so nothing leaks now). No other test reads the
  collateral or fee levels as its state (E015 traded classes and E022 rewards are not touched).
- **History of this section (disclosed).** A first build, the same afternoon and never deployed, held `tl_w2h` under a
  provisional token `tilt` to 2027-03-09 (science review ACCEPT_WITH_FIXES: no leakage; the fixes were wording). Before
  deploy the builder read LT11's section 9 pre-freeze hold, merged into chore shortly before, and removed the column and
  the token. No tilt table, fit, prediction or score existed at any point under either version.
- **Challengers.** `se24_lgbm_tilt`: se1's LightGBM params, se21's train block with `require_sources: ["tilt"]`, read
  against se1. `se25_lr_tilt`: the champion's logistic learner and params with `require_full_coverage` and the family,
  read against se0 (CH235's logistic isolate). One pre-declared configuration each, no development selection; first
  evidence prospective. K rises by two (8 -> 10 for the visible set; the conservative direction).
- **Leakage and timing.** No sweep, no snapshot row and nothing received after the capture. Section 21 does not arise;
  neither challenger is promotion-ineligible.
- **Science review (2026-10-23 ~13:05Z, two passes): ACCEPT_WITH_FIXES.** No leakage; fee parse correct; `parentsib`
  census sound; levels-only with no token complies with LT11 section 9; the attribution-limit request above added.
- **Coverage (counts only, capture 10-23 10:31Z).** 98.1% of eligible rows (93.8% non-sports) carry a fee schedule;
  `fees_enabled` is 0 on 1,131 of 58,294; schedule rates 0.05 / 0 / 0.03 / 0.07 on 35,062 / 12,397 / 4,968 / 4,721 rows.
- **Cost.** 5 float32 columns (~35 MB on the frames at the caps), one LightGBM fit (~2 min) and four logistic fits
  (seconds) per refit, two predictions per capture. The q0512 / q0513 caps are unchanged.
- **CH237 `parentsib` killed at census (counts only).** Capture 2026-10-23T10:31Z: 27 of 18,349 eligible non-sports rows
  (0.15%) carry a non-null `parent_event_ids` (CH237's line: 5%); 44% of all eligible rows have one, almost all sports.
  No family is built; a re-census only if sports rows come into scope or the field's coverage widens.
- Tests: `test_tilt_features_hand_example`, `test_tilt_reads_only_its_own_capture`, and registry assertions in
  `test_repo_registry_loads_and_embargo_assignment`.

## 30. LT11 freeze: `dollarw`, `nrslack`, `bandside` and `attrlimit_lt11` (2026-10-23 ~18:20Z; no scoring change)

Applied from the `CANDIDATES.md` LT11 freeze request (LIVE_TESTS_11.md section 9, design text frozen at 3627d7fd), before any
column of these families exists, so nothing has been computed or shown on these terms.
- **Embargo.** `config.EMBARGO` gains `dollarw` (LT11-CH234), `nrslack` (LT11-CH233) and `bandside` (LT11-CH232), each until
  2026-12-12T00:00Z (the later of that and LT11's analysis commit), and `attrlimit_lt11` (kind `attribution_limit`, same date,
  models champion, se1, se24, se25 and any broad model; `no_broad_families: ["dollarw", "nrslack", "bandside"]`).
- **Column routing.** `tilt`'s planned `tl_w2h` and `tl_w_traded` go under `dollarw`: a `tilt` version that adds either must
  list `dollarw` in the isolating spec's `isolates`, and se24 / se25 at their current versions (levels only) stay visible. The
  `rewards` family's planned `rw_cross_out_2h` / `rw_cross_in_2h` go under `bandside`. The `event` family's levels are not
  covered; a sibling bid- / ask-sum *change* goes only into an `nrslack` family.
- **Builder judgement (not built this session).** None of the three families is built. Each would be an isolating
  challenger hidden to 12-12 and adds 1 to the promotion K; the priors are the live tests' own mechanisms, which the tests
  themselves will settle first.
- Tests: `test_lt11_freeze_requests`; the generic attribution-limit loop now also lists `attrlimit_lt11`.

## 31. Input-coverage monitor `se-input-health-v1` (2026-10-23 ~23:15Z; operations only, no model, feature or score change)

Why: a broken input (a stream that stops, an API field that vanishes, a sweep with no books) leaves NaN or zero columns.
The models still predict, so nothing fails, and days of prospective scores are spent on a broken family before anyone
notices. `input_health.py` checks the newest capture at every tick.
- **Reads.** Only the engine's own write-once `features/` and `aux/` tables and `meta/` files of the newest 13 captures. It
  never reads labels, predictions or scores, so it carries no outcome information. The embargo does not apply (inputs
  only), and the numbers stay in the host file; the dashboard gets statuses and the alert list.
- **Per column:** the finite share and the finite-and-nonzero share, compared with the median over the previous 12
  captures (one day). Rules, fixed before any host run:
  - `absent`: the share is 0 where the trailing median is above 0.
  - `drop`: the share is below half the trailing median, where that median is at least 2%.
  - `all_zero`: finite values but none nonzero, where the trailing nonzero median is at least 2%. This catches an outage
    that writes zeros, such as `bk_has` = 0 everywhere. `sp_dow` / `sp_hour` are exempt because they are constant within
    a capture.
  - `missing`: an aux table is still absent 4 h after the capture start, for a family that had tables in the trail. It
    is `pending` before 4 h.
  - `universe`: eligible rows below 70% of the trailing median.
  - `capture_gap`: missed 2 h slots in the trailing day, counted from the engine's first capture.
  - Fewer than 4 earlier tables: `short_history`, not judged.
- **Outputs.** `state/input_health.json` is a rewritable view, never evidence. `state/input_health_cache.json` holds
  per-capture summaries; the tables are write-once, and an entry with a pending table is recomputed. The tick's JSON
  gains `inputs` (status, alert count, the first 6 alerts) or `inputs_error`; the monitor never changes the tick's exit
  code. `dashboard.live_status` adds `inputs`, so `dashboard.json` and the /lab snapshot carry it on every push, and
  `run_signal_engine.py status` prints it.
- **Host check (read-only, 2026-10-23 ~23:10Z).** On capture 10-23 22:31Z: 2.4 s, 226 MB RSS, status ok, no alerts.
  Backtest over the 72 captures from 10-18 to 10-23: 9 captures alert. All 9 trace to the two missed passes of
  10-21 00:31Z and 02:31Z. The 2 h / 6 h / 24 h look-backs (momentum, `movetype`, `surprise`, `dispgap`) are NaN for the
  following 2 h, 6 h and 24 h captures, and the `dormant` runs reset. There are no false alarms on unbroken stretches.
- Tests: `tests/unit/test_signal_engine_input_health.py` (stable inputs; a zeroed book, a vanished stream, a sparse drop
  and a shrunk universe; pending, then missing, then backfilled; short history; a missed capture; `live_status`).
- Not done: the /lab web page does not render `inputs` yet (a production-branch PR); until then it is visible in
  `dashboard.json`, the snapshot and `status`.
