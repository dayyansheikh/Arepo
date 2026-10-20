# Live tests 3 (LT3): E015-E019, DRAFT pre-registrations

**Status: DRAFT, not registered, nothing counted.** Drafted 2026-10-20 on branch `feat/live-tests-3` from the research tip
`0bbb66b4`. E-numbers are provisional; they are assigned at registration. Before registration this needs: the
pre-registration censuses (section 8, counts only, worn pre-window data), a challenger review (`science-reviewer`) of
this file and later of the code, the fixes, the `SPEC_SHA256` and code-hash pin, the ledger entry (section 12) and the
reader's installation. Until the pin exists, every line the reader writes is `prospective_unregistered` by construction.

This is research tooling. No edge, calibration, profitability or tradability claim exists or is implied. Every number
quoted from the round-9 probes is a **counts-only development figure on worn data**. Every MDE here is a **planning
estimate** built on stated assumptions, not a measurement.

Source ideas: `CREATIVE_HYPOTHESES_2026-10-23.md` (round 9) CH156, CH157, CH158, CH159, CH161 and CH162. CH160 is out
(it needs CB17 branch S, and q0400 returned branch T, ledger 2026-10-20). The design is built to avoid, from the start,
the nine faults of the LT2 challenger round 1 (`reviews/LT2_CHALLENGER_R1_2026-10-20.md`). Section 1.12 maps each
fault to the rule that answers it.

## 0. Summary

| ID | Idea | Hypothesis (direction) | Stream | Primary | Planning MDE (estimate; Holm worst case, k = 5) | Floor |
|---|---|---|---|---|---|---|
| **E015** | CH156 | Within a market, the 2 h continuation after a **parallel** quote-only re-centering is higher than after a **traded** move (one-sided, > 0) | complete-universe captures (+ sidecar, + sweep 1 for the mechanism reading) | expanding-past demeaned OLS of `c` on 1[parallel] over parallel and traded units | **about 0.16-0.23c** (range 0.1-0.4c) | 0.5c |
| **E016** | CH161 | 6 h taker flow continues more when more of it was **walked** (off-grid aggregated prices): slope of `x6 · zW` > 0 | trade samples + captures | E013-form expanding-past demeaned OLS plus a distant-donor gate | **about 0.0018-0.0029 per SD of zW** | gross 0.5c in the favourable cell |
| **E017** | CH157 | The 24 h outcome-0 (YES) mid change after an **attention-only volume surge** (`volume24hr` >= 3x and >= +$500, \|x\| < 1c) is higher than after the same market's non-surge intervals (> 0) | captures + sidecar | market-FE OLS of the 24 h change on 1[attention-only], two-day-block inference | **about 0.6-1.25c** (power at the floor) | 1.0c |
| **E018** | CH162 arm 2 | 6 h taker flow continues less when more of it arrived in same-signed **trains** (rows with a same-signed neighbour within 300 s): slope of `x6 · zH` < 0 | trade samples + captures | as E016 (sign reversed) | **about 0.0018-0.0029 per SD of zH** | gross 0.5c |
| **E019** | CH159 | Within a non-sports neg-risk event, the members' 2 h continuation after a **high-breadth** untraded interval (>= 80% of members re-quoted) is higher than after a **low-breadth** one (< 50%) (> 0) | captures + sidecar | expanding-past demeaned OLS of `C` on 1[high] within event | **about 0.4-1.0c** (borderline; census-gated) | 0.5c |

- **Family:** one Holm family over the k primaries, one-sided, familywise alpha 0.05, separate from LT2 (E012-E014) and
  E009-E011. **k = 5** if every census gate in section 8 passes. A test whose census gate fails is dropped *before*
  registration, uncounted, and k is the number of tests that survive their gates (E015 has by far the largest projected
  population and is the least likely to drop).
  k is fixed in the spec at registration and never changes afterwards. A primary that is unavailable or fails its gate
  enters Holm with p = 1.
- **Dropped:** CH158 (underpowered: the effective sample is the pass, really the day; section 7.1), CH160 (branch T),
  CH162 arm 1 (needs print direction, branch T), CH157's carry arm (needs a resolution fetch). E015 takes one primary
  (parallel minus traded); one-sided minus traded becomes a mechanism secondary (section 2).
- **Window:** whole captures with start in `[REGISTERED_UTC, END_UTC)`, 21 days. Proposed `REGISTERED_UTC =
  2026-10-24T00:00:00Z`, `END_UTC = 2026-11-14T00:00:00Z`. Single analysis on or after `2026-11-15T12:00:00Z`.

## 1. Common rules

### 1.1 Registration, window, single analysis
- `REGISTERED_UTC` is the first 00:00Z at least 24 h after the registration commit (spec pin plus ledger entry), never
  earlier than 2026-10-23T00:00Z. The proposed value is 2026-10-24T00:00Z. If the commit slips, `REGISTERED_UTC` moves to
  the next qualifying 00:00Z, `END_UTC = REGISTERED_UTC + 21 d` and the analysis date `END_UTC + 36 h`. This rule uses no
  data. The move is recorded in the ledger.
- **Window membership is by capture start** (`capture_start_utc`), whole captures in or out, as in E011. The origin of every
  unit is its own row's `received_utc` (section 1.3).
- **Fixed end, no extension.** Round 9 proposed a 28-day extension behind a counts gate. It is not adopted: the brief asks
  for a fixed end, and a counts-triggered extension is one more researcher degree of freedom. Shortfalls are labelled
  (section 1.9), not extended.
- **One analysis**, once, on or after the analysis date (`run_live_tests3.py analyze` refuses before it; `--out` refuses to
  overwrite). No interim look at any outcome (section 1.6).
- **Effective start** = max(`REGISTERED_UTC`, the first capture processed by the reader at the pinned commit). The analysis
  keeps only lines whose `spec_sha` equals the pin, whose `code_sha` equals the pinned code hashes and whose role is
  `prospective_confirmation`.

### 1.2 Streams read (all already written by the host's pass; nothing new is fetched)
- **Complete-universe captures** `snapshots/<id>/rows.csv.gz` (every 2 h at :31; `state=complete` only): `received_utc`,
  `capture_start_utc`, `market_id`, `condition_id`, `event_id`, `closed`, `active`, `binary`, `best_bid`, `best_ask`,
  `spread`, `last_trade_price`, `volume24hr`, `chg_1h/1d/1w`, `liquidity`, `end_date`, `clob_token_id_0`, `neg_risk`,
  `neg_risk_market_id`.
- **Sidecar** `rows_ext.csv.gz` of the same capture: `fee_type`, `fee_category`, `fees_enabled`, `fee_schedule`,
  `taker_base_fee`, `order_price_min_tick_size`, `created_at`, `series_slugs`. If the sidecar is `missing` for a capture,
  units at that capture that need it are not formed (counted as `sidecar_missing`); nothing is borrowed from another capture.
- **Book sweep 1 of the same pass** `book_sweeps/<id>/` (outcome-0 token best bid and ask and the batch receipt clock), only
  for the mechanism secondaries of E015 and E019. Never used in a primary.
- **Active-frame trade sample of the same pass** `trade_samples/<id>/` (`plan.json`, `manifest.json`, `features.csv.gz`,
  `trades.csv.gz`): for E016 and E018. Wallet fields are never read (they are not in these files).
- **Not read:** the live large-trade monitor (CH160 and CH162 arm 1 are dropped), the cross-venue stream (sealed to
  2026-11-03), `surprise_live/` (E011), `live_tests2/` (LT2), CB17's and CB16's stores, Gamma outcome fields of any kind.

### 1.3 Clocks and slots
- **Origin `t`** = the market row's `received_utc` in capture k (the time the page body holding the row was fully
  received). States use capture k and strictly earlier captures only. Trade rows are used only if `ts < t` (venue seconds,
  strict).
- **Slots:** captures map to the 2 h grid (`grid0 = 2026-10-01T00:31Z`, tolerance 30 min, first complete capture of a slot),
  as in LT2. "k − 1" and "k + h" mean slots, not file order. A unit needs captures in slots k − 1 and k; a missing slot gives
  no unit (counted from slot gaps). Target slots: k + 1 (2 h), k + 3 (6 h), k + 12 (24 h).
- **Late rule:** a unit's frozen line must be written before its earliest target slot can start (`now < slot time − 60 s`),
  otherwise a `.late` marker is written and the unit is lost (counted). At analysis, a line whose `frozen_utc` is not
  strictly before the start of its target capture is excluded and counted.

### 1.4 Shared origin-side eligibility (a move unit at capture k)
Every filter below uses captures k − 1 and k (and the sidecar of k) only. Each is applied in this order and each exclusion
is counted.
1. `binary == 1`, `closed` false and `active` true at k − 1 and k.
2. Two-sided at k − 1 and k: both quotes present, `best_ask > best_bid`.
3. Tight at k − 1 and k: spread (Gamma `spread`, else ask − bid) <= 0.10.
4. `mid_k` in [0.02, 0.98] (E015, E019) or [0.05, 0.95] (E017).
5. As-of end date: `end_date` unknown or > `t` + 3 h (E015, E019), > `t` + 48 h (E017).
6. Non-sports by `cb17_census.is_sports_sidecar(fee_type, fee_category, series_slugs)` on the sidecar of k (imported by
   sha256 at registration). The sports arm is computed with the same code and reported uncounted (category is a parameter;
   the user's sports decision is open).
7. One row per `condition_id` (the first row in page order; duplicates counted).

### 1.5 Missing data and per-capture attrition status (never imputed)
- At every target slot, each frozen unit receives exactly one **status**: `two_sided`, `one_sided`, `closed_flag`
  (present with `closed` true or `active` false), `absent` (the capture is complete but the market is not in it; resolved
  and delisted markets land here and cannot be told apart) or `capture_missing` (no complete capture in the slot 3 h after
  its time). The reader writes the status from the target capture as soon as it is complete, write-once, so the analysis
  never needs the raw captures (the archive rotation may later remove them from the host).
- Only `two_sided` units have a target. The other statuses are counted by class and by test.
- **Attrition rule (pre-declared, per test):** let `a_1` and `a_0` be the non-`two_sided` shares (excluding
  `capture_missing`) of the two contrasted classes. If `|a_1 − a_0| > 2` percentage points, the result carries the label
  **attrition-differential**, and Lee-type trimming bounds are reported: the class with less attrition is trimmed by the
  difference in shares from the top and from the bottom of its target distribution, and the primary is re-estimated at both
  ends. The verdict is not changed by the bounds; the label is. The share of `absent` by class is always reported.

### 1.6 What is not looked at before the analysis date
- No mid, move, target, P&L, regression, correlation or plot from `live_tests3/` files, or from in-window captures, sweeps or
  trade samples, for these hypotheses. Only `run_live_tests3.py ops-stats` may run: file, line, role, class and status
  counts. It reads no price column, enforced by a unit test.
- The flow-screen development lines (one per pass, F1 of E007) keep running on the same trade samples and must not be
  consulted for any LT3 decision.
- No change of thresholds, scales, populations, estimators or k after registration. Operational fixes are logged as
  deviations.

### 1.7 Estimators and dependence-aware inference
- **Expanding-past demeaning** (J4-R, accepted 2026-10-16; used by LT2 E012 and E013) for E015, E016, E018 and E019: every
  regressor (the tested term and every control) minus the mean of the market's (E019: event's) strictly earlier units; the
  target is raw; the first unit of each market drops. It needs no "markets holding both classes" rule, so **no unit's
  inclusion depends on anything after its origin** (a both-class rule would decide early units by later ones). It is
  unbiased under independent increments and attenuates under the alternative (conservative). Why not the full-sample
  within estimator for E015 and E019: a later unit's class is a function of the move that forms an earlier unit's target
  (unit k + 1's class describes `mid_k → mid_{k+1}`, which is unit k's target), a Nickell-type coupling the full-sample
  mean would let in. E017 uses the full-sample market FE because its tested label (a surge with no move) carries no sign,
  so this coupling cannot bias a signed 24 h change; its expanding-past version is a sensitivity.
- **Standard errors:** CR1 clustered (a) on the event (E019: on the **series-or-event**, the first `series_slugs` entry if
  present, else the event id, because daily crypto strike ladders are separate events driven by one spot price) and (b) on
  the **UTC day of the origin** for 2 h and 6 h targets, or on **two-day blocks** from `REGISTERED_UTC` for E017's 24 h
  target (11 blocks, the last one day long), because 24 h targets cross midnight.
- **Primary one-sided p** = max(p_event with a normal reference, p_day with a t reference on G − 1 df), G = number of UTC
  days (E017: blocks) with at least one unit. The conservative 95% CI is the hull of a 2,000-draw event-cluster bootstrap CI
  and beta ± t_{G−1, 0.975} · SE_day.
- **Controls** are listed per test. They are all origin-side and all demeaned the same way as the tested term.

### 1.8 Placebos and gates (valid within-unit nulls)
- **E015, E019: label permutation gate.** 200 draws; in each, the class labels of the contrasted units are permuted within
  market (E019: event) x UTC day, the target and controls staying attached to their unit; the estimator is re-run. Gate:
  `p_perm = (1 + #{draw >= real}) / (1 + draws) < 0.05`. Strata with fewer than 4 contrasted units are left unpermuted
  (counted). This is a check on the clustered SEs, **not** a mechanism control: a permutation null cannot tell bounce from
  information. The mechanism controls are the readings in each test.
- **E016, E018: distant-donor gate** (LT2 finding 1 fixed by design). Only markets with **>= 4 usable units** enter the gate.
  In each of 200 draws, every unit's moderator (`W` or `H`) is replaced by the moderator of a donor unit of the same market
  drawn uniformly with replacement from units whose origin is **at least 12 h away** (6 h flow window + 6 h horizon, so a
  donor's flow window cannot overlap the recipient's flow window or its target). A unit with fewer than 2 eligible donors
  keeps its own value and is counted. Everything else (flow, timing, target, controls) is unchanged. Gate as above. A
  simulated-null unit test (iid flow and AR(1) flow with no moderation) must show rejection <= 0.05 at the pinned code.
- **E017: pre-trend placebo.** The same estimator with the target replaced by the market's prior 24 h change,
  `mid_{k−1} − mid_{k−13}` (all pre-origin). If it is one-sided significant at 0.05 in the predicted direction and at least
  half the primary estimate, the result is labelled **pre-existing trend** and cannot be read as attention.
- A failed gate gives the primary p = 1 in Holm and the label "within-unit timing not shown" (E016, E018) or "SE check
  failed" (E015, E019).

### 1.9 Verdicts and labels (per primary, after Holm over k)
- **Supported (exploratory, prospective):** Holm-adjusted one-sided p < 0.05, estimate in the predicted direction, gate passed.
- **Contradicted:** the conservative 95% CI lies entirely on the other side of 0.
- **Inconclusive:** otherwise.
- **Unavailable:** below the test's floor counts (stated per test), or fewer than 10 UTC days (E017: 5 blocks) with units.
- **Labels (attached, never change a verdict):** *material* (the point estimate is at or above the floor);
  *underpowered* (for an Inconclusive result, when `(t_{G−1, 1−0.05/k} + t_{G−1, 0.8}) x SE_day` from the realised fit
  exceeds the floor); *attrition-differential* (1.5); *possibly mechanical* or *Gamma-quote mechanics* (per test); *pre-existing
  trend* (E017); *coverage-limited* (E016, E018).

### 1.10 Economics (separate; never changes a verdict)
- **Declared cost model:** paper taker round trip per share, entry at the origin capture's recorded touch and exit at the
  target capture's recorded touch (long outcome 0: `bid_target − ask_origin`; short: `bid_origin − ask_target` on the
  outcome-0 book, i.e. buying outcome 1); taker fee on both legs from the origin sidecar (`economics.fee_spec`,
  `resolve_rate(..., "max_if_unknown")`, `rate · p(1 − p)` per leg). No depth, queue or latency, so it is optimistic.
- Event-clustered mean, one-sided p (`battery.mean_test`), valid only with >= 30 trades in >= 10 events
  (`economics.MIN_TRADES`, `MIN_CLUSTERS`). "Covers taker costs (paper)" only if the mean is > 0 with p < 0.05, else "not
  shown".
- Maker routes have no fill model: only the gross mid-to-mid move of the cell is reported, labelled "gross, no fills".
- **Declared in advance:** every AREPO taker cost check has failed so far (E004 −4.5c/share touch-to-touch; E007 +0.36c gross
  against about 4.5c; 0 of 95 economic cells positive), so "not shown" is the expected economics outcome. A Supported
  primary without it is a forecasting fact, not a route.

### 1.11 Overlaps, dependence and counting
- E015 and E019 share units (E019's movers are E015-type units grouped by event); E016 and E018 share every trade sample,
  origin and target. All are in one Holm family and are never counted as independent confirmations.
- **Collection overlap (disclosed):** LT2 (window from 2026-10-22, E013 on the same trade samples with the same `x6`), E011 (to
  2026-11-10, same captures), CB-batch SEALED-P windows and E009/E010 (other streams). Different hypotheses, no pooling, and
  no store opened by another test.
- **Counting (Methods note M3):** the analysis adds **k counted tests**, one per primary, kind `live_tests3`. Placebo and
  gate draws, secondaries, mechanism readings, economics and the section 8 censuses count 0 (descriptive). A count rule for
  `live_tests3` must be added to `battery2.cumulative_count` (fail-closed) before the analysis. The cumulative count is
  recorded at registration and at analysis. The verdicts use Holm within LT3 only, as LT2 and E009-E011 do.

### 1.12 The nine LT2 round-1 faults and where each is answered
| # | Fault | LT3 rule |
|---|---|---|
| 1 | invalid within-market null (rotation swaps in overlapping neighbour flow; 2-3-row markets) | 1.8: donors >= 12 h away, markets >= 4 units, simulated-null unit test; label permutations only within market x day with >= 4 units |
| 2 | quote-noise/bounce mechanics when x and y share a mid | E015, E019: a sweep-to-sweep target that shares no Gamma quote with `x`, and an explicit mechanism-label rule; E016, E018: an early-ending flow window label rule; E017: a signed target with an unsigned label plus the pre-trend placebo |
| 3 | attrition unmeasurable | 1.5: per-capture status for every unit, written online; the 2 pp rule with bounds |
| 4 | population or coverage depending on post-origin data | 1.4 origin-side filters only; 1.7 no both-class rule; E016/E018 coverage by an origin-side `volume24hr` cut, residual truncation counted and labelled; train neighbours from pre-origin rows only |
| 5 | optimistic day-level inference | 1.7: p = max(event, day with G − 1 df); two-day blocks for 24 h; MDEs computed with t on G − 1 df |
| 6 | spec/code mismatch incl. counting | 1.11 counting k stated once; 9.3 pins code and spec hashes together; unit tests for every label rule |
| 7 | power realism | MDEs per test with assumptions; census gates on projected counts; *underpowered* label |
| 8 | mechanism reading | a named mechanism-reading secondary with a pre-declared label rule per test |
| 9 | explicit filters | 1.4 and each test's filter list, in order, each counted |

## 2. E015: quoted versus traded moves (CH156)

- **Hypothesis and mechanism.** A 2 h mid move happens either through a trade (a taker pushed the touch) or with no trade.
  A no-trade move with both quotes moving together by the same amount (a parallel re-centering) is a quoter's model
  update: information from outside the book (Hasbrouck 1991's quote revisions not caused by trades). A traded move holds
  a temporary-impact part that refills. Prediction: within a market, parallel re-centerings continue more (revert less)
  over the next 2 h than traded moves. **Direction: D_PT > 0, one-sided.**
- **Why this primary, and not one-sided minus traded.** Round 9 proposed two primaries. A one-sided quote move (one quote
  changed, the other did not) is the bid/ask bounce by construction: its reversal is close to certain under pure mechanics,
  and E004/E006 already found the pooled reversal "consistent with bounce". Spending a Holm slot on it buys little, so it
  is a pre-declared mechanism secondary (S1). Parallel minus traded is the contrast bounce cannot produce directly, because
  a parallel move cannot be a spread change. It is still partly predicted by microstructure (temporary impact of trades),
  and the reading says so.
- **Unit.** Market x capture k satisfying 1.4 with `|x| >= 0.01`, `x = mid_k − mid_{k−1}` (Gamma mids, `mid = (bid +
  ask)/2`).
- **Class (frozen; from captures k − 1 and k only; tolerances absorb float error on tick grids).** `db = bid_k − bid_{k−1}`,
  `da = ask_k − ask_{k−1}`; `L` = `last_trade_price` present at both ends and changed (|diff| > 1e-9), or absent at k − 1
  and present at k; `V+` = `volume24hr_k − volume24hr_{k−1} > 0.01`; `V0` = |diff| <= 0.01; `V−` = diff < −0.01. In order:
  1. **never-traded:** `last_trade_price` absent at both ends (reported).
  2. **traded:** `L` or `V+`.
  3. **ambiguous:** not `L` and `V−` (a roll-off of the rolling 24 h volume with no visible trade, or a trade netted by
     roll-off): excluded, counted. `last_trade_price` present at k − 1 and absent at k: excluded, counted.
  4. **quote-only** (not `L`, `V0`), split into **parallel** (`sign(db) = sign(da) = sign(x)`, both |.| >= 0.005, `|db − da|
     <= 0.005`), **one-sided** (one of |db|, |da| <= 0.0005), **spread-change** (opposite signs, both |.| > 0.0005) and
     **same-side unequal** (the rest).
- **Target.** `c = sign(x) · (mid_{k+1} − mid_k)`, Gamma mids, status `two_sided` at k + 1 (tightness at k + 1 is **not**
  required, because it is post-origin; j-tight is a sensitivity).
- **Primary statistic.** Expanding-past demeaned OLS (1.7) of `c` on `P = 1[parallel]` over parallel and traded units,
  ordered by origin within market, with controls `log |x|`, spread at k, `|mid_k − 0.5|`, logit `mid_k` and `log1p
  volume24hr_k` (class composition differs in move size and activity). D_PT = coefficient on P. SEs, p and CI as 1.7
  (event; UTC day, G − 1 df); seed 20261024. Gate: label permutation (1.8), seed 20261124.
- **Mechanism reading (pre-declared label rule).** M1 re-estimates the primary with the **sweep-to-sweep target** `c_sw =
  sign(x) · (smid_{k+1} − smid_k)`, `smid` = the outcome-0 book mid from sweep 1 of each pass, a CLOB measurement minutes
  after the capture that shares no Gamma quote with `x`. If E015 is Supported and M1's estimate is below 50% of D_PT, or
  M1's one-sided p >= 0.05, the result is labelled **Gamma-quote mechanics** (a capture-level, not book-level, contrast). M2
  reports a 6 h skip target `sign(x) · (mid_{k+3} − mid_{k+1})`: persistence beyond the first pass.
- **Secondaries (descriptive, not counted).** S1: one-sided minus traded (predicted < 0), the J4 bounce question answered by
  class; S2: never-traded class level; S3: class x price band and class x |x| dose; S4: full-sample within estimator; S5: the
  sports arm; S6: counts per class, the share of `V−`, and both-class market counts.
- **Planning MDE (estimate).** Projection from P1/P1b (counts only, one worn day): about 2,750 non-sports movers per
  interval, so about 690,000 in 21 days; 13% x 60% are parallel (about 54,000) and 27% traded (about 187,000).
  Assumptions: after the filters and the first-unit drop, about 30,000 parallel and 100,000 traded units contribute; the SD
  of `c` is 4c; the event-cluster design effect is 2-3 and day clustering adds x 1.3-1.5. Then `SE = 4c · sqrt(1/30,000 +
  1/100,000) · sqrt(2..3) · (1.3..1.5)` = 0.048-0.068c, and `MDE = (t_{20, 1−0.01} + t_{20, 0.8}) · SE = (2.528 + 0.860) ·
  SE` = **0.16-0.23c** (range 0.1-0.4c if the parallel class is half as large or the SD is 6c). The floor, 0.5c, binds,
  not power.
- **Floors (Unavailable):** < 5,000 parallel units, < 20,000 traded units, < 300 events or < 10 days.
- **Economics.** (a) Taker follow of parallel moves with `|x| >= 0.03`, entry at the k touch in the direction of x, exit at
  the k + 1 touch. (b) Reported: taker fade of one-sided moves with `|x| >= 0.03` (the bounce trade, which E004 says loses).
  Maker: gross mid move by class, "gross, no fills".
- **Filters in order:** 1.4 (1-7), `|x| >= 0.01`, class rules 1-4 (never-traded and ambiguous out), status `two_sided` at k + 1.

## 3. E016: walked flow continues (CH161)

- **Hypothesis and mechanism.** The Data API returns one aggregated row per taker order (probe P2: 659,082 rows,
  659,082 distinct transactions), so an order that filled across two or more price levels prints a volume-weighted price
  off the market's tick grid (probe P2b: 23% of sampled rows have >= 4 decimals). Paying through the book is urgency, and
  urgent orders carry more information (Biais, Hillion and Spatt 1995; Kaniel and Liu 2006). Prediction: E007-style flow
  continuation is stronger when more of the window's signed flow was walked. **Direction: beta(x6 · zW) > 0, one-sided.**
- **Unit and population (origin-side only).** Market x trade sample, where the sample is the active-frame sample taken
  right after a complete in-window capture, and its `origin_utc` is the market's row `received_utc`. Filters in order:
  request status 200; 1.4 items 1-3 and 7 at the sample's capture (the frame already enforces eligibility); `end_date`
  unknown or > `t` + 7 h; **`volume24hr_t <= V*`**, the coverage cut fixed by census C2 (the largest value at which the
  census's 6 h truncation rate was <= 2%); at least one signed row with `t − 6 h <= ts < t`. All categories, as E013 and
  E007 (sports reported split, not excluded, so as to stay comparable with the flow family).
- **Coverage.** A unit is covered if the returned page held < 500 rows or its oldest row is at or before `t − 6 h`. The page
  also holds rows after `t`, so coverage can depend on post-origin trading; the `V*` cut makes this rare, and the
  remaining truncated units get `x6` = NaN (unavailable, counted, never 0). If truncated units exceed 3% of the
  `V*`-population, the result is labelled **coverage-limited** and a sensitivity at `V*/2` is reported.
- **Features (frozen).** Signed rows only (`trade_sample._sign`, the E007 convention: + for BUY outcome 0 or SELL outcome 1).
  `imb6 = Σ sign · size · price / Σ size · price` over rows with `t − 6 h <= ts < t`; `x6 = clip(imb6, −1, 1) / 0.85782`
  (E013's definition, copied verbatim into the LT3 spec). **Walked** row: the `price` string in `trades.csv.gz` (read as
  text) has >= 4 decimals after stripping trailing zeros. This is off-grid under both the 0.01 and the 0.001 tick regimes, so
  no sidecar tick is needed. `W = Σ_{walked} size · price / Σ size · price` over the same rows; `zW = (W − c_W)/s_W` (census
  C2). `N6` = number of signed rows; `zN = (log N6 − c_N)/s_N`; `zSPR` as E013 (spread at `t`, LT2 census scale).
- **Target.** `y6 = mid(slot k + 3) − mid_t` (Gamma mids, status `two_sided` at k + 3).
- **Primary statistic.** Expanding-past demeaned OLS of `y6` on `x6 · zW` with controls `x6`, `zW`, `x6 · zN`, `zN`, `x6 ·
  zSPR`, `zSPR`, logit mid, `|mid − 0.5|`, Gamma `chg_1h`, `chg_1d`, `chg_1w` with missing flags, `dprev = mid_t −
  mid(slot k − 1)` with its flag. The `x6 · zN` and `x6 · zSPR` controls separate walking from thin books and activity (a
  walked order is more likely in a thin book, and LT2's F5 already tests the spread moderator). SEs, p, CI as 1.7; seed
  20261025. Gate: distant donors (1.8), seed 20261125.
- **Mechanism reading (label rule).** M1: `x6` and `W` recomputed on a window ending 30 min before `t`. A walked order moves
  the touch, so if the Gamma mid at `t` lags the book, part of `y6` is mechanical catch-up. If E016 is Supported and M1's
  interaction is below 50% of the primary or its one-sided p >= 0.05, the label is **possibly mechanical (stale-mid
  catch-up)**. M2: the target from the sweep 1 mid of pass k to sweep 1 of pass k + 3.
- **Secondaries.** Within-market FE; `W` on row counts; a 1 h window on E007's own unit and 2 h target; by category.
- **Planning MDE (estimate).** About 1,000 market-samples per pass with 6 h flow (P2: 943-1,080; LT2 census about 1,000),
  12 a day, about 250,000 units in 21 days before the `V*` cut, in an assumed 5,000-8,000 events (LT2's estimate on the
  same stream). Scaling SB2-J2's h3 SE for a standardised flow moderator (F4: 0.00055 at 2,100 events) by `sqrt(2,100 /
  5,000)` and x 1.5 for proxy noise and demeaning attenuation gives SE about 0.00053, and x 1.0-1.6 for day clustering.
  `MDE = (2.528 + 0.860) · SE` = **0.0018-0.0029 per SD of zW**. E007's whole 1 h flow effect is 0.0036, so the test detects
  only a moderation of roughly half the main effect per SD. There is no development estimate for `W` (the aggregation fact
  is new). **Declared in advance: Inconclusive is a likely outcome.**
- **Floors (Unavailable):** < 20,000 covered units, < 500 events, < 10 days.
- **Economics.** Upper `W` tercile (census cut), `|imb6| >= 0.5`: follow `sign(imb6)`, taker round trip to the 6 h target;
  gross mid move must exceed 0.5c to be called material. Expected "not shown".
- **Sign caveat (disclosed).** q0400 found that the Data API `side` agrees with the touch-implied direction for 93.3% of
  CB13-T non-sports fills (below CB17's 97% bar, hence branch T). E016 uses `side` through the E007 convention, which E007
  used prospectively; mis-signing attenuates `x6`. If mis-signing is more common in walked rows, the interaction is biased
  toward 0 (conservative) or, with an inverted aggregate side, negative. Question 5 asks the challenger to rule on it.

## 4. E017: attention without a price (CH157)

- **Hypothesis and mechanism.** A market whose 24 h volume at least triples in one 2 h interval while its mid barely moves
  has been *noticed*, not informed: information moves the price, attention moves the volume. Attention buys (Barber and
  Odean 2008), and the high-volume premium (Gervais, Kaniel and Mingelgrin 2001), together with this venue's taker YES tilt,
  gives the demand a direction. Prediction: the noticed market's outcome-0 mid drifts up over the next 24 h relative to
  its own non-surge intervals. **Direction: D_A > 0, one-sided.**
- **Unit and population (origin-side only).** Market x capture k satisfying 1.4 (mid band [0.05, 0.95], end > `t` + 48 h)
  and, from the sidecar of k, `created_at` <= `t` − 48 h, plus `volume24hr_{k−1} > 0` (new markets out; CH154 owns them).
- **Labels.** Surge `S`: `volume24hr_k >= 3 · volume24hr_{k−1}` and `volume24hr_k − volume24hr_{k−1} >= 500`. Attention-only
  `A`: `S` and `|x| < 0.01`. Surge with a move `SM`: `S` and `|x| >= 0.01`. Baseline: not `S`.
- **Target.** `y24 = mid_{k+12} − mid_k` (outcome 0, status `two_sided` at k + 12). Signed; the label carries no sign, so
  the shared `mid_k` adds variance, not a directional artefact.
- **YES convention (disclosed).** `rows.csv.gz` has no outcome labels. Outcome 0 is "Yes" for neg-risk members and for
  yes/no binaries; some non-sports binaries are not yes/no (crypto Up/Down, head-to-heads). The end-date > 48 h filter
  removes most short Up/Down markets. Secondary S1 restricts to neg-risk members, where outcome 0 is always Yes.
- **Primary statistic.** Market-FE OLS (1.7 explains why FE here) of `y24` on `A` and `SM`, over all eligible units, with
  controls logit `mid_k`, `|mid_k − 0.5|`, `log hours-to-end` (as-of; unknown flagged), `log1p volume24hr_{k−1}`, Gamma
  `chg_1d` with its flag. D_A = coefficient on `A`. SEs: event and **two-day blocks** (G = 11, df 10); p = the max; seed
  20261026. Placebo: pre-trend (1.8).
- **Mechanism reading (label rule).** If Supported and the `SM` coefficient is as large (within its CI) and of the same
  sign, the drift follows any volume surge and is labelled **volume, not attention-without-news**. The share of `A` units
  whose `volume24hr` falls back below `2 · volume24hr_{k−1}` within 24 h (a wash or reward-farming signature, post-origin) is
  reported by class; it is never a filter.
- **Secondaries.** S1 neg-risk members only; S2 standalone binaries; S3 dose (3x, 5x, 10x); S4 the 6 h version; S5
  expanding-past estimator; S6 the sports arm (outcome 0 is a team, so this is undirected and reported only).
- **Planning MDE (estimate).** P1b counted 77 non-sports no-move surges in four intervals, about 230 a day, about 4,800 in
  21 days. Assume 60% survive the age, end-date and band filters (about 2,900 units) in 1,200-2,500 events, a 24 h SD of
  6c, a x 1.1 within-market factor, and a x 1.3-1.8 block factor. Then `SE = 6c / sqrt(events) · 1.1 · (1.3..1.8)` =
  0.17-0.34c and `MDE = (t_{10, 0.99} + t_{10, 0.8}) · SE = (2.764 + 0.879) · SE` = **0.6-1.25c**, against the 1.0c floor:
  power at the floor. Gate C3 requires a projected >= 2,000 `A` units in >= 1,500 events (MDE about 0.8-1.1c there), else
  E017 is dropped before registration.
- **Floors (Unavailable):** < 800 `A` units, < 100 events, < 5 blocks.
- **Economics.** Taker buy of outcome 0 at the k ask on `A` units, sold at the k + 12 bid, fees both legs; expected to fail
  (3.6-4.5c round trip). The NO carry to resolution (round 9's carry arm) needs a resolution fetch and is not part of LT3.
- **Filters in order:** 1.4 (with E017's band and end rule), `created_at`, `volume24hr_{k−1} > 0`, labels, status at k + 12.

## 5. E018: trains and herds in the flow (CH162 arm 2)

- **Hypothesis and mechanism.** Taker rows arrive in trains (probe P2c: 5,523 of 7,105 pre-origin rows had a same-market row
  within 300 s). Herding by retail traders follows attention and imitation and does not predict returns (Barber, Odean and
  Zhu 2009). So flow that arrived as same-signed trains is more copycat than informed and continues less. **Direction:
  beta(x6 · zH) < 0, one-sided.** The opposite reading (a train is one informed trader working an order, CH69) predicts > 0.
  The one-sided test cannot detect it; it is reported.
- **Unit, population, coverage, target, controls, estimator:** exactly E016's, with `H` in place of `W`. Seeds 20261027 (OLS)
  and 20261127 (gate).
- **Feature (frozen).** A signed row in `[t − 6 h, t)` is *in a train* if another signed row of the same market **with the
  same sign** and `ts` in `[t − 6 h, t)` lies within 300 s of it (before or after, but **never at or after `t`**, so no
  post-origin row can make an earlier row a train member). `H = Σ_{train} size · price / Σ size · price`; `zH` from census C2.
  Because the train probability rises mechanically with the row count, `x6 · zN` and `zN` are in the controls (as E016).
- **Mechanism reading (label rule).** As E016's M1 (window ending 30 min early): label **possibly mechanical** on the same
  rule. M3: `H` built from rows of any sign (unsigned trains), reported.
- **Planning MDE (estimate):** as E016, **0.0018-0.0029 per SD of zH**. Census C2 must show `H` strictly between 0 and 1 in
  at least 40% of covered units, else E018 is dropped before registration (with 78% of rows clustered, `H` may be
  degenerate at 1 in active markets).
- **Redundancy (disclosed).** `W` and `H` are both urgency or shape measures of the same flow and may correlate. Census C2
  reports corr(`zW`, `zH`). If it exceeds 0.5, E018 is dropped before registration (two slots for one moderator), k is
  reduced, and the drop is recorded.
- **Floors, economics:** as E016 (lower `H` tercile, follow the flow).
- **Why not arm 1 (prints).** Train *position* in the monitor needs the print direction for the same-direction flag; under
  branch T that is not available at CB17's agreement standard, and an undirected |mark-out| contrast is not a forecasting
  test of the hypothesis. Dropped (7.3).

## 6. E019: ladder breadth (CH159)

- **Hypothesis and mechanism.** Ladders (neg-risk events) are quoted by few programs that price every member from one input.
  When most members re-quote in the same interval with no trade, a program updated its view of the whole distribution and
  the moves persist. When one member re-quotes alone, a single maker moved and the move reverts toward the siblings.
  **Direction: D_HL > 0, one-sided** (high-breadth continuation minus low-breadth).
- **Unit and population (origin-side only).** Event x capture k for **non-sports neg-risk events** (`neg_risk` true, one
  `event_id`) with **>= 3 members** eligible under 1.4 at k − 1 and k. The interval is **untraded** if no eligible member is
  in E015's `traded` or `ambiguous` class at k (intervals with a traded member are reported separately, because a traded
  member re-prices siblings mechanically, E005's band). It needs at least one member with a quote-only move, `|x| >= 0.01`.
- **State.** Breadth `b` = (eligible members with a quote-only move `|x| >= 0.01`) / (eligible members). High: `b >= 0.8`; low:
  `b < 0.5`; middle reported.
- **Target.** `C` = mean over the interval's quote-only movers of E015's `c` (members with status `two_sided` at k + 1; the
  event-interval needs at least one).
- **Primary statistic.** Expanding-past demeaned OLS (demeaned within **event**, by strictly earlier event-intervals) of `C`
  on `1[high]` over high and low untraded event-intervals, with controls `log` number of eligible members, mean `log |x|` of
  the movers and mean spread. SEs: **series-or-event** clusters and UTC day (G − 1 df); p = the max; seed 20261028. Gate:
  label permutation within event x UTC day, seed 20261128.
- **Mechanism reading (label rule).** M1 as E015's sweep-to-sweep target: label **Gamma-quote mechanics** on the same rule.
  A lone mover is one quote change, which is bounce-prone by construction; a high-breadth move is many simultaneous quote
  changes, which noise rarely produces. M2: crypto strike ladders (series slug rule fixed in the spec) versus the rest,
  reported. These are the natural high-breadth class, where a "program update" is a spot move.
- **Planning MDE (estimate).** Round 9 counted 250 event-intervals at >= 80% breadth in four intervals across all
  categories, about 15,000 in 21 days. Assume 25-50% are non-sports and untraded (1,500-3,750 high-breadth units against many
  more low-breadth ones), a 3c SD of `C`, a within-event factor `sqrt(1.25)`, a series-cluster design effect of 2-3 and a day
  factor of 1.5-2.0. Then `SE = 3c / sqrt(N_high) · sqrt(1.25) · sqrt(2..3) · (1.5..2.0)` = 0.12-0.30c and `MDE = 3.388 ·
  SE` = **0.4-1.0c** against the 0.5c floor: **borderline.** Gate C4 requires a projected >= 3,000 high-breadth untraded
  non-sports intervals and >= 300 events holding both classes, so the projected MDE is <= about 0.55c, else E019 is dropped
  before registration.
- **Floors (Unavailable):** < 150 events with both classes, < 50 series-or-event clusters, < 10 days.
- **Economics.** Taker follow of high-breadth quote-only movers with `|x| >= 0.02`, and taker fade of low-breadth lone movers
  with `|x| >= 0.03`, at the recorded touches, 2 h. Maker: gross only.

## 7. Ideas dropped or narrowed, and why

### 7.1 CH158 (venue tilt as a common factor): dropped, *underpowered* in 21 days
- The tested variable `u_{-e}(k)` (the leave-one-event-out up-share of non-sports movers) takes **one value per pass**: 252
  passes in 21 days. The hypothesis is a time-series one (an aligned tilt reverts next pass), whatever the unit count. Tilts
  of neighbouring passes share news and US/EU trading hours, so the independent information is closer to the **21 days**
  than the 252 passes, and inference must use t on 20 df.
- The variable may barely vary. The only probe day had 55-60% up in each of 11 intervals; a range of 5 pp means an SD of
  about 1.5-2 pp and an IQR probably below the 4 pp round 9 itself set as the kill line. With `a = sign(x) · (2u − 1)`, the
  SD of `a` across passes is about 0.035.
- Planning arithmetic (estimate): `SE(beta per unit a) ≈ σ_pass / (σ_a · sqrt(N_eff))`. With a pass-level residual SD of the
  aligned continuation of 0.1-0.3c (common shocks dominate; 10,000 movers average the idiosyncratic part to 0.04c) and
  `N_eff` from 252 (optimistic) to 40-60 (day-dominated): SE 0.18-1.36c, **MDE 0.6-4.6c per unit of a** against a 0.5c floor.
  A realistic effect is a fraction of a cent per unit of `a`, and `a` itself is about 0.1 in a typical pass, so even the
  optimistic case is underpowered by a factor of several.
- Mechanical confounds that 21 clusters cannot separate: time decay of favourites (a persistent up-tilt in outcome-0
  mids), common Gamma refresh timing within a capture, and one large event night.
- **Recommendation (not counted):** compute `u_{-e}` per pass as a descriptive map in the E015 reader output (its IQR,
  autocorrelation and hour-of-day profile over the LT3 window), and design a >= 90-day test only if the map shows variation.

### 7.2 CH160 (walked prints on the monitor): not testable
It needs the print direction under CB17's branch S; q0400 returned 93.3% agreement against 97%, so branch T. Withdrawn as
round 9 pre-declared. The walk fact lives on in E016 at the flow level.

### 7.3 CH162 arm 1 (train position of large prints): not testable as specified
Same branch-T reason (the same-direction flag), and the monitor's 9-minute median receipt lag makes its money route
unreachable. The flow-level arm is E018.

### 7.4 CH157 carry arm and CH156 H1
The NO carry to resolution needs a light Gamma fetch of departed ids (CH167). It is not a pure reader and is out of LT3.
CH156's one-sided minus traded is E015's secondary S1 (2).

### 7.5 Considered and not chosen
- The J4-R increment bootstrap as the E015 placebo: it is built for reversal slopes on `x`, not for class contrasts; the
  permutation gate plus the sweep target answer the two different risks.
- A both-class market population for E015 and E019 (round 9's sketch): rejected, because it decides early units' inclusion
  from later units (fault 4).
- `ctx_*` monitor fields as states: post-print, a leak (round 9 section 4).

## 8. Pre-registration censuses (counts only; before registration; worn pre-window data; no target read)

Each runs once, on captures and samples that **started before 2026-10-22T00:00Z** (before LT2's and LT3's windows), reads
origin-side fields only (no mid at any later capture, no target, no P&L), prints counts, and is committed with its sha256
before the registration commit. A failed gate drops that test before registration (uncounted); k is set accordingly.

| Census | Inputs (proposed) | Prints | Gate |
|---|---|---|---|
| C1 (E015, E019 classes) | the 12 captures of one full day already worn by P1 (2026-10-15) and one more day before 10-22 | units by class and test filter, `V−` share, never-traded share, both-class market counts, the sports split, `u_{-e}` per pass (descriptive, for 7.1) | E015: projected 21-day parallel >= 20,000, traded >= 50,000; traded share of non-sports movers in [15%, 60%]; `last_trade_price` absent for <= 60% of non-sports movers |
| C2 (E016, E018 flow) | the trade samples of 2-3 days before 10-22 (CSVs on the host from 10-16) | the 6 h truncation rate by `volume24hr` (fixes `V*`), W and H distributions (centre, scale, terciles), the share with H strictly in (0, 1), corr(zW, zH), the zN scale, the share of signed rows | E016: projected covered units with W in (0, 1) >= 60,000; walked share of rows >= 10%. E018: H in (0, 1) for >= 40% of covered units and corr(zW, zH) <= 0.5 |
| C3 (E017 surges) | the C1 captures plus their sidecars | `A`, `SM` and baseline counts after every filter, events, the neg-risk share | projected `A` >= 2,000 units in >= 1,500 events (planning MDE about 0.8-1.1c at the gate); fewer: dropped |
| C4 (E019 breadth) | the C1 captures | untraded high, middle and low non-sports event-intervals, events with both, series-or-event clusters, the crypto-ladder share | projected high >= 3,000 and events with both >= 300 |

Projection = the day count x 21, stated as an estimate. Census code reads no price at any capture after the one being
classified. Scales and cut points (`c_W`, `s_W`, `c_H`, `s_H`, `c_N`, `s_N`, `V*`, terciles) are written into the spec JSON
before the pin.

## 9. Light implementation plan (no code in this commit)

### 9.1 Modules
- `backend/astrolabe/research_lab/live_tests3.py`: the reader. `run_once()` finds new complete captures and their pass's
  sweep 1 and trade sample, and for each one in order:
  1. writes `live_tests3/series/<capture>.csv.gz`: all binary rows, compact (market id, event id, series key, bid, ask,
     `last_trade_price`, `volume24hr`, closed, active, two-sided flag, end date, created at, the sports flag, plus the
     sweep-1 bid and ask and their receipt clock);
  2. freezes origin units from slots k − 1 and k: `units/move/<capture>.csv.gz` (E015 units with class and controls; E019
     event-intervals) and `units/surge/<capture>.csv.gz` (E017), and from the trade sample `units/flow/<sample>.csv.gz`
     (`x6`, `W`, `H`, `N6`, the early-window versions, coverage and `V*` flags, controls);
  3. writes target outcomes and statuses for earlier units whose target slot this capture fills, `outcomes/<capture>.csv.gz`;
  4. appends `passes.jsonl`.
  Every data file is write-once (atomic hard link; an existing file is never touched), as LT2.
- `backend/astrolabe/research_lab/live_tests3_analysis.py`: the single analysis (estimators 1.7, gates 1.8, verdicts 1.9,
  economics 1.10, Holm over k, counting).
- `backend/scripts/run_live_tests3.py`: `run`, `census`, `ops-stats`, `analyze`.
- Spec: `backend/astrolabe/research_lab/model_specs/live_tests3_v1.json` (every frozen constant, k, the seeds, the dates, the
  census scales, the imported sports-rule hash).
- Reuse without modification: `panel.eligibility_mask` pieces, `trade_sample._sign`, `cb17_census.is_sports_sidecar`,
  `battery.beta_test` / `mean_test`, `economics.fee_spec` / `resolve_rate`. Nothing from `live_tests2*` is imported (stores
  and code stay separate; E013's `x6` is copied as a constant definition).

### 9.2 Resources
- **Memory:** per pass, two captures' selected columns (about 150-200k rows each, `usecols` and categorical ids), one sidecar,
  one sweep and one trade sample (about 220k rows, five columns). Target peak < 350 MB (P1 streamed 12 captures at 311 MB),
  hard cap `mem_mb 480`, below the queue's 500 MB blackout exemption (02:45-05:30Z), so the 04:31 slot is never lost.
- **CPU and time:** about 1-2 min per pass (estimate). No network.
- **Disk:** series about 2-3 MB per capture, units and outcomes < 1 MB: about 0.8 GB over the window plus look-back (estimate);
  the reader stops writing at 1.5 GB in `live_tests3/` and exits 75 above the data-dumps cap. Missing stays missing.
- **Lane:** the queue holds one job per lane, and LT2's collector already occupies `net` for its window. A 21-day `cpu`-lane
  job would block every cpu job, so the recommended install is a host cron entry (as CB14-W): `10 1-23/2 * * *`, after the
  :31 pass finishes and well before the next one, own `flock`, `nice -n 19`, never the collector lock. The alternative is a
  queue job that yields after each pass. This is an orchestrator decision (question 13). Installing it is a host change
  under the standing collection authorisation, not done here.

### 9.3 Tests and pins (before registration)
- `backend/tests/unit/test_research_lab_live_tests3.py`: class labels on hand-built capture pairs (every branch, including `V−`
  and first-trade); walked detection on price strings (`0.45`, `0.4500`, `0.453`, `0.4537`); train membership never using a
  row at or after `t`; `V*` and coverage flags; causality (future captures with wild prices leave every frozen line
  byte-identical); late refusal; write-once; status coding including `absent` and `capture_missing`; expanding-past
  demeaning; the distant-donor gate under simulated iid and AR(1) nulls (rejection <= 0.05) and on a planted effect;
  permutation within stratum; the pre-trend placebo uses no post-origin mid; Holm with m = k; the counting rule equals k;
  `ops-stats` reads no price column; the analysis refuses before the date and refuses an unpinned spec.
- At registration: `SPEC_SHA256` and the sha256 of `live_tests3.py`, `live_tests3_analysis.py` and the spec are pinned
  together in the spec, the ledger and the code guard; the analysis refuses if any differ.

## 10. Disclosures

- **Selection history.** All five ideas came from round 9 (Fable xhigh creative pass, `d72e1006`), written after six
  counts-only host probes on **worn data**: the 12 captures of 2026-10-15 (worn earlier by CB17's P3), the 10-15 monitor
  file (worn by CB17 P1), and, for features only, three 2026-10-16 trade samples, one sidecar and the 10-16 monitor file
  (inside J4-R's window, which is refused only for maker-mark-out objects). The probes decoded no `side`, no wallet, no
  forward price, no mark-out and no outcome. The ideas were ranked by a judgement score, so the choice of these five out of
  13 is itself a selection. The censuses (8) are a further counts-only read of pre-window data.
- **The designer** (this draft) read the ideas file, the ledger sections named in the brief, LT2's draft and challenger
  review, and collector code. No data, host or outcome was read.
- **Closest prior AREPO tests.** E015/E019: E002 and E004 (pooled 2 h reversal, Supported, "consistent with bounce", not
  tradable), E006 H1 (liquidity moderation of the reversal, Supported on sign, consistent with bounce), SB2-J4 (bounce
  decomposition; verdicts withheld because the permuted-target placebo was not null), SB2-J3 (book-mid bounce
  decomposition), CB3 (quote vacuum), CB17-B (book age); E005 (neg-risk band, Not supported) for E019. E016/E018: E007 (1 h
  flow continuation, Supported, +0.36c, "flow-quote continuation"), LT2 E013 F4/F5 (6 h flow moderators, same stream, same
  `x6`, concurrent window), CB16-Q (sub-cent grain, terminal), HB1 size features. E017: CB11-A (attention without news,
  Wikipedia), CH24/CH97/CH132; CB12-X (attention-type flow, not identifiable).
- **Mechanics stated up front.** E015 and E019 contrasts are partly predicted by quote mechanics (temporary impact; lone
  quote changes). E016's walk is correlated with thin books and with the touch moving. E017's surge can be wash or reward
  volume. Each has a named reading and label; none is called information without it.
- **Shared data.** LT2, E011, CB-batch SEALED-P windows and the flow-screen lines read the same captures and samples.
  Overlap only.

## 11. Questions for the challenger

1. E015: is parallel minus traded the right single primary, with one-sided minus traded as a mechanism secondary? Or is the
   bounce class itself the programme's open question (J4) and worth the slot?
2. Expanding-past demeaning with a binary class regressor (E015, E019), against the full-sample FE for E017: is the stated
   Nickell-type coupling argument right, and is the mix acceptable?
3. The distant-donor gate (12 h, >= 4 units, donors with replacement): a valid null for a moderator with a persistent level?
   Is p = 1 in Holm on failure still right?
4. Day-level inference: max(p_event, p_day on G − 1 df) for 2 h and 6 h targets, two-day blocks (df 10) for 24 h. Enough,
   or should 6 h targets also use blocks?
5. After q0400's 93.3% side agreement, is the E007 sign convention acceptable for E016 and E018? Should census C2 add a
   walked-versus-on-grid comparison of `side` against the origin touch (counts only), with a drop rule?
6. Is E018 worth a slot next to E016 (correlated stream, modest novelty), and is corr(zW, zH) <= 0.5 the right drop rule?
7. Census gates that can drop a test before registration based on projected counts (never outcomes): acceptable, and are
   the thresholds tied to the floors correctly?
8. Walked = >= 4 decimals in the CSV price string: the trade sample parses `price` with `float()` and pandas writes the
   shortest repr. Is that faithful to the API's string? (Probe P2b read the same CSV.)
9. The attrition rule: is 2 pp with Lee-type bounds right for 2 h targets (about 0.4% loss in LT2's dry run) and for 24 h
   targets (much more)?
10. `volume24hr` semantics: rolling, refreshed on Gamma's cadence. Do the `V+`/`V0`/`V−` rules and the surge definition
    misclassify when Gamma updates volume with a lag?
11. The outcome-0 = YES convention for E017 outside neg-risk: is S1 (neg-risk only) enough, or should it be the primary?
12. E019 clusters on series-or-event: is the first `series_slugs` entry a sound family key for crypto ladders?
13. Lane: host cron entry versus a queue job; the late rule's exposure if the reader is delayed past the next slot.
14. CH158 dropped as underpowered (7.1): agree, or is a pass-level test with 20 df still worth a slot?

## 12. Draft ledger block (DRAFT, not registered, not counted)

> ## E015-E019 — Live tests 3 (LT3): DRAFT pre-registration (not registered, nothing counted)
> - **Design:** `docs/research_lab/LIVE_TESTS_3.md`. Pure reader of streams the host already writes (complete captures, sidecar,
>   sweep 1, active trade samples); cpu work, no network, < 350 MB target, `mem_mb 480`.
> - **E015** (CH156) parallel quote-only versus traded 2 h continuation within market, > 0; planning MDE about 0.16-0.23c, floor 0.5c.
> - **E016** (CH161) walked share moderates 6 h flow continuation, `x6 · zW` > 0; about 0.0018-0.0029 per SD; Inconclusive likely.
> - **E017** (CH157) attention-only volume surge, 24 h YES drift within market, > 0; about 0.6-1.25c against the 1.0c floor.
> - **E018** (CH162 arm 2) train share moderates 6 h flow continuation, `x6 · zH` < 0; as E016; census-gated (degeneracy, redundancy).
> - **E019** (CH159) high- minus low-breadth untraded ladder intervals, 2 h, > 0; about 0.4-1.0c, census-gated.
> - **Family:** Holm over k (5 if every census gate passes, else the number surviving), one-sided, alpha 0.05; p = max(event, day with G − 1 df;
>   two-day blocks for 24 h). Window: captures starting in `[REGISTERED_UTC, +21 d)`, proposed `[2026-10-24T00:00Z,
>   2026-11-14T00:00Z)`; single analysis on or after 2026-11-15T12:00Z. Economics: paper taker round trips, expected "not shown".
> - **Dropped:** CH158 (underpowered: 252 passes, about 21 independent days), CH160 and CH162 arm 1 (branch T), CH157 carry (needs a fetch).
> - **Status:** DRAFT awaiting censuses C1-C4 and the challenger; no line is `prospective_confirmation` until the pin.
