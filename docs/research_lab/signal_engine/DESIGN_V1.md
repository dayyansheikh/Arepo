# Signal engine v1: design

- **Status:** BUILT on `feat/signal-engine` (2026-10-21), tested (synthetic end-to-end), dry-run on the host (read-only,
  `/tmp/sigeng`, deleted). **Not deployed; no queue job promoted.** Deploy steps: section 11.
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
| book | has-book, top / 1c / 5c imbalance, 5c depth, microprice minus **sweep** mid, book age, levels | first book sweep of the pass (received ~8 min after the capture; no sweep-Gamma gap) |
| xvenue | has-pair, Kalshi mid minus Gamma mid, Kalshi spread, quote age (<= 30 min) | `cross_venue_live/quotes` lines received before the capture start (quotes only) |
| wallet | has-sample, log distinct wallets 24 h, top-1 notional share, HHI | `wallets.csv.gz` of the trade sample, trades in [origin - 24 h, origin); hashed wallets |
| tte (derived) | near-24 h / near-72 h indicators, their products with momentum, chg 1h x log hours | computed at fit/predict time from stored columns |

Derived transforms (logit mid, |mid - 0.5|, log1p of hours/ages) are applied in `learners.py`, so the store stays
primitive. Causality: no feature reads any capture after the origin; inputs from other streams are received before the
prediction is written, and every prediction is only scored if written before its target capture (section 6).
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

## 7. Promotion rule `se-promotion-v1` (pre-declared; `promotion.py`)

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
| surprise (no model yet) | 2026-11-12T00:00Z | E011 |
| chg1d_x_liq (no model yet) | 2026-11-14T00:00Z | E012 |
| tte | 2026-11-14T00:00Z | E014 |
| flow | 2026-11-16T00:00Z | E013, E014 (LT2, 2026-11-13T12Z), E016, E018 (LT3 proposed 2026-11-15T12Z) |
| book | 2026-11-18T00:00Z | E015, E019 (LT3), E020, E022 (LT4 proposed 2026-11-17T12Z) |
| wallet | 2026-11-18T00:00Z | E024 (LT4) |

LT3/LT4 dates are the proposed windows; when they register, move the dates **later** if needed (never earlier). A new
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
- Next: per-market signal feed for the website (owner-approved deploy), SHAP family attribution for LightGBM, more
  challengers from replicated effects after their embargoes, scored-capture caching to speed the daily scorer.
