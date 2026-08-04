# Signal Lab / Replay — independent quantitative audit (Agent B)

Scope: `analytics/{anomaly,quality,zscore,abnormality,movement,volatility}.py`,
`opportunity/{scoring,hypothesis}.py`, `evaluation/{historical,replay_stats}.py`,
`service/enrich.py`, cross-checked against `docs/signal-replay-functional-baseline.md`,
`docs/methodology.md`, `docs/quant-final-review.md`, `docs/research-paper-evidence-audit.md`.

Verdict up front: **no edge claim is statistically justified.** The only live evaluation sample
(reconstructed Replay, n=4) is explicitly labelled inconclusive by the code itself
(`sample_verdict`), and the underlying comparison is confounded by at least one measurement-bias
bug (flat-move asymmetry) and one metric-choice gap (no proper scoring rule) that must be fixed
before the n=4 result means anything. This review does not recommend changing any threshold to
improve reported performance; all fixes below are about correctness of measurement, not about
tuning outcomes.

---

## CRITICAL

### C1. Flat 24h moves are scored as directional misses for Arepo/momentum/price-only, but as wins for the no-change baseline — confirmed, asymmetric comparison
**Files:**
- `backend/astrolabe/evaluation/replay_stats.py:50-53` (`_correct`) — `(move > 0)` / `(move < 0)`, strict, no epsilon.
- `backend/astrolabe/evaluation/replay_stats.py:108-122` (no-change baseline) — `abs(m) <= FLAT_EPS` (0.01) counted **correct**.
- `backend/astrolabe/evaluation/historical.py:204-205` (`direction_correct_24h`) — same strict `(move24 > 0)` / `(move24 < 0)`, independently re-implements the identical bug for the per-entry display column.

**Failing scenario (reproduced from the recorded baseline, not hypothetical):** rank 3 and 4 in
`docs/signal-replay-functional-baseline.md` moved exactly `0.000` over 24h. Both are counted
`False` (miss) for Arepo, momentum and price-only via `_correct`, while the same two rows are
counted **correct** for the no-change baseline via the separate `abs(m) <= FLAT_EPS` branch. This
is not a marginal effect: it accounts for 2 of Arepo's 4 "misses" and both of the no-change
baseline's 2 "hits." The headline "Arepo 0/4 vs no-change 2/4" is *entirely* explained by this
asymmetry plus one genuine miss and one genuine directional call with no room to be right (rank 1
had strength 0.51 but the market moved the other way; that one is a genuine miss).

**Why this is a correctness bug, not a modeling choice:** every predictor is being scored against
the same forward move with two different tolerance rules. A directional predictor is being
penalized for "failing" to predict a nonzero direction on a market that did not move, while the
no-change predictor is rewarded for correctly calling that same non-move. There is no `flat`
outcome bucket in `HistoricalScreen`/`BaselineComparison` at all — `moved_expected_24h` /
`moved_against_24h` / `pending_24h` do not sum to `selected` when a flat move occurs (it silently
lands in `moved_against_24h`).

**Recommended fix:** add a third `flat` outcome bucket, defined once (e.g. `abs(move) <=
FLAT_EPS`), and apply the identical tolerance to every predictor including Arepo, momentum and
price-only — not just no-change. Report correct / incorrect / flat / pending as four disjoint
counts that sum to the evaluated sample for every predictor, in both `replay_stats._score` and
`historical.direction_correct_24h`. Do not simply drop flat cases from the denominator (that would
inflate everyone's hit rate); show them as a separate bucket.

### C2. Brier score / log loss are not implemented anywhere in the codebase, despite being claimed as existing
**Files:** `backend/astrolabe/evaluation/replay_stats.py` (entire file — no probabilistic scoring
function of any kind, only the binary `_correct`/Wilson-CI machinery); confirmed via
`grep -rni "brier\|log_loss" backend/astrolabe/` → zero matches outside third-party packages.

`docs/quant-final-review.md:50` asserts *"Brier/log-loss framework exists in `replay_stats`; extend
to the resolution target as the prospective sample grows."* This is **false** as of this audit —
no such framework exists in `replay_stats.py` or anywhere else in `backend/astrolabe/`. Only a
binary hit/miss (`_correct`) and a Wilson interval on the binary hit rate are computed. The
research audit (`docs/research-paper-evidence-audit.md:49,111`) correctly identifies Brier/log
loss as required (spec §12) but the adopted-feature list was never actually implemented.

**Why this matters statistically:** collapsing a probabilistic/directional signal to a binary
correct/incorrect call throws away calibration information and cannot distinguish a
well-calibrated 51%-confidence call from an overconfident 99%-confidence call that happened to be
right. With n=4 this is doubly important — Brier/log loss on the *entry probability itself* (the
market's own implied probability as the baseline forecast) is the only sane way to compare
Arepo's implied edge to the market without needing a much larger binary sample to reach
significance.

**Recommended fix:** implement Brier score (`(p - outcome)^2`) and log loss over whichever
probability the "prediction" implies (for a directional call, treat it as a claim that the
outcome token's probability moves toward 1; for a resolution-based test, score against the
market's own implied probability as the reference forecast). Track this in `replay_stats.py`
alongside the binary hit rate. Do not remove the binary hit rate — report both, since the audience
understands "hit rate" more readily, but the Brier/log-loss number is the one that should gate any
edge claim.

### C3. Direction is mechanically the sign of momentum, evaluated at a horizon where the code's own sample shows it losing to "no prediction at all"
**Files:**
- `backend/astrolabe/analytics/anomaly.py:166-168` — `direction = "up" if raw.zscore > 0 else "down" if raw.zscore < 0 else None`.
- `backend/astrolabe/analytics/zscore.py:42-51,62-83` — the z-score's sign is, by construction, the sign of `last_return - mean(baseline)`; since the baseline is a short trailing window whose mean is typically close to zero for a probability series, `sign(z) == sign(last_return)` in the overwhelming majority of cases. This *is* one-step price momentum, relabeled "repricing pressure" in `opportunity/hypothesis.py:9-13`.
- Evaluated at 24h in `evaluation/historical.py:202-205` and compared against a `momentum` baseline (`replay_stats.py:126`, `historical.py:184-189`) built from the *same* sign-of-recent-return logic (`trail = entry - trail_from`).

**Failing scenario:** because Arepo's `direction` and the `momentum` baseline are both, mechanically,
"the sign of the market's most recent move" (differing only in the sample used — a z-scored
20-period window vs. a raw 4-point trailing diff), they are not independent predictors. Comparing
"Arepo" against "Momentum" in `compare_baselines` (`replay_stats.py:84-129`) is close to comparing
a method against a near-copy of itself, not against an independent baseline. In the recorded
baseline sample both score 0/4 — consistent with (not proof of) mean-reversion dominating at the
24h horizon for near-mid markets, which is the textbook alternative hypothesis to momentum
continuation. Nothing in the codebase or cited research (`docs/research-paper-evidence-audit.md`
explicitly notes the cited literature's edge is "seconds-to-minutes", not 24h) supports momentum
continuation being the right prior at this horizon.

**Why this is CRITICAL, not just a modeling nuance:** the product's central claim ("Arepo detects
repricing pressure worth investigating") is operationalized as a momentum bet, and the one
horizon it is evaluated at is exactly the kind of horizon where naive momentum is most likely to
be anti-predictive for mean-reverting order flow. If that holds up at scale, the strategy is not
merely "no edge" but "negative edge dressed as a screening heuristic." The current n=4 cannot
distinguish these cases, which is itself the point: the confident "repricing pressure" language in
`hypothesis.py:79-82` is not warranted by anything computed so far.

**Recommended fix:** (a) do not present `momentum` as an independent baseline when Arepo's own
direction is mechanically correlated with it — report the pairwise agreement rate between Arepo's
direction and the momentum baseline's direction alongside the comparison table, so a reader can
see how much apparent "beating momentum" is actually a wash; (b) before any edge claim, test
directional accuracy at multiple horizons (1h/24h/7d — already collected in `DEFAULT_HORIZONS`)
and report whether accuracy is monotonically related to horizon, which is the standard diagnostic
for momentum-vs-reversion; (c) keep presenting the result as inconclusive until n is large enough
for the horizon-by-horizon breakdown to be meaningful.

---

## MAJOR

### M1. Signal Lab and Board/Detail display two different numbers under the same label "confidence" for the same signal — confirmed
**Files:**
- `backend/astrolabe/analytics/anomaly.py:207-213` — `Signal.confidence = quality.confidence`, the raw multiplicative data-quality penalty score from `analytics/quality.py:24-36,57` which **starts at 1.0 and is only reduced by explicit penalties**; on the live universe (all "good" band) it is 1.00 for every signal.
- `backend/astrolabe/api/routes/signals.py:13-19` + `service/market_service.py:445-473` — `/api/signals` returns `Signal` objects unmodified, so `signal.confidence` (the 1.00 raw term) reaches the client as-is. Confirmed by grep: no reliability recomputation anywhere in the signals path.
- `backend/astrolabe/opportunity/scoring.py:118-139,253-262` — `ScoredOpportunity.confidence = reliability_confidence(signal.confidence, n_families, component_completeness)`, a **different, smaller** number (0.004–0.762 in the recorded baseline) that also folds in family corroboration and component completeness. This is what `/api/opportunity/board` and Market Detail show for the *same underlying signal*.

**Failing scenario:** a user opens Signal Lab, sees "Confidence: 100%" on a one-family, thin-data
lead, forms an impression the reading is maximally trustworthy, then opens the same market's
Detail page or the Board and sees "Confidence: 4%–76%" for the identical signal. There is no
version skew here — both numbers are computed from the same `Signal` object in the same request
cycle; they are simply two different statistics sharing one label.

**Which is correct:** `reliability_confidence` is the defensible one — it is the only one of the
two that responds to the thing a reader would reasonably infer from the word "confidence"
(how much independent evidence and how complete the inputs are), and it is the one the code's own
docstrings (`scoring.py:105-116`) argue for. The raw `quality.confidence` term measures something
narrower ("no data-quality penalty triggered") and is better labelled "data quality: good/limited/
poor" (which already exists as `signal.data_quality`) than "confidence."

**Recommended fix:** either (a) surface `reliability_confidence` on every surface including Signal
Lab, computing `n_families`/`component_completeness` for the Signal Lab context the same way
`score_opportunity` does, or (b) rename the Signal Lab field to something that does not overload
"confidence" (e.g. "data quality: good") and only ever call the reliability number "confidence."
Do not ship both under the same label on different pages.

### M2. `volume_acceleration` is permanently absent (0/120), so the documented 12% weight is silently redistributed to the other six components on every single live signal
**Files:**
- `backend/astrolabe/analytics/anomaly.py:25-33` (`DEFAULT_WEIGHTS`, `volume_acceleration: 0.12`) and `:124-135` (`composite_anomaly_score` — `score = num/wsum`, weight renormalisation over present components only).
- `backend/astrolabe/service/enrich.py:98-102` — `vol_accel` sourced from a persisted snapshot series (`changes.volume_acceleration`) that the live path does not build, confirmed absent in 0/120 tokens per the recorded baseline.

**Failing scenario:** the live composite's *effective* weights are not the documented ones — with
`volume_acceleration` always missing, the renormalised effective weights are `unusual_return
≈0.273, movement_abnormality ≈0.227, volatility_regime ≈0.182, book_imbalance ≈0.136,
spread_change ≈0.091, depth_change ≈0.091` (each original weight / 0.88), not the `0.24/0.20/0.16/
0.12/0.08/0.08` published in `docs/methodology.md` and in the code comments. Because this
happens on 100% of live signals (not occasionally, as the renormalisation design assumes), the
"documented weights" are not the weights the running system ever actually uses.

**Recommended fix:** either wire the persisted-snapshot volume series into the live enrichment
path so the component is genuinely available (the stated intent per `enrich.py:98-99`'s comment),
or remove `volume_acceleration` from `DEFAULT_WEIGHTS`/`DEFAULT_CAPS` entirely and redistribute
its weight explicitly and document the resulting six-component weights as the live default —
don't leave a permanently-dead component silently inflating the other six via renormalisation.

### M3. Research Priority and displayed confidence are not independent axes — both increase mechanically with `n_families`
**Files:**
- `backend/astrolabe/opportunity/scoring.py:225` — `family_bonus = min(1.0, n_families / TARGET_FAMILIES)`, weighted 0.45 into `priority` (`:235-236`).
- `backend/astrolabe/opportunity/scoring.py:135-136` — `corroboration = min(1.0, n_families / TARGET_FAMILIES)`, weighted `RELIABILITY_SPAN=0.55` into the *displayed* `confidence` (`reliability_confidence`).

**Failing scenario:** both formulas use the identical ratio `n_families / TARGET_FAMILIES` as a
primary driver. A market that goes from 1 to 3 fired families moves both Research Priority
(directly, +0.45 of the `raw` term) and displayed confidence (directly, +0.55 of the reliability
factor) in the same direction from the same underlying count, with no independent variation. The
two numbers are presented on the Board as though they answer different questions ("how much
attention" vs. "how much to trust it"), but a large share of their variance across the universe
will be explained by the same single input. This is exactly the "Research Priority duplicates
strength/confidence" failure mode the spec is trying to avoid (the composite-anomaly refactor
comment in `anomaly.py:159-163` explicitly says this was fixed once for strength×confidence — the
same coupling has re-appeared one level up, via shared dependence on `n_families`).

**Recommended fix:** decorrelate the two uses of family count — e.g., let Research Priority use
raw family count/magnitude while confidence uses a genuinely distinct completeness/corroboration
measure (such as agreement in *direction* across families, not just count), or report the
correlation between RP and confidence across the live universe as a diagnostic so this coupling is
visible rather than assumed away.

### M4. Universe selection for the reconstructed Replay ranks candidates by *today's* trading volume, not cut-off-time volume — a look-ahead channel beyond the disclosed "survivorship" note
**Files:**
- `backend/astrolabe/evaluation/historical.py:344-360` (`run_live_historical`) — calls
  `market_service.active_markets(requested_mode="live", limit=universe_limit, by="volume_24hr")`.
- `backend/astrolabe/service/market_service.py:289-299` — `active_markets` has no `as_of`
  parameter; it always sorts **current** markets by their **current** `volume_24hr`.

**Failing scenario:** for a cut-off 7 days in the past, the candidate pool is chosen by which
markets are most actively traded *today*, not by which were active or notable at the historical
cut-off. A market that becomes heavily traded today (plausibly *because* of a large move in the
intervening week — the very kind of event the signal is trying to detect) is more likely to enter
the candidate pool than one that was equally interesting at the cut-off but has since gone quiet.
This is a stronger and more specific effect than the disclosed "mild survivorship" note in
`historical.py:352-356` (which frames it only as "a market that has since resolved trades less
now") — it is a selection channel correlated with the *post-cutoff outcome itself*, not merely
market continued-existence.

**Recommended fix:** either select the candidate universe using volume/activity **as of the
cut-off** (requires a point-in-time activity snapshot, may not exist yet — if so, disclose this
explicitly and separately from survivorship), or, at minimum, expand the disclosed limitation to
name the mechanism precisely: "candidates are ranked by current volume, which can correlate with
the post-cut-off price action being measured."

---

## MODERATE

### N1. Evidence families are not statistically independent, and nothing in the code tests or enforces the "independent" claim
**Files:** `backend/astrolabe/analytics/flow.py:14-21` (comment asserts independence),
`opportunity/scoring.py:1-6` (same assertion), no correlation/de-duplication logic anywhere in
either file.

**Failing scenario:** `trade_flow` (large-relative-trade / clustered-trades / contrarian-flow) and
`timing` (late-large-trade) are both derived from the same underlying trade tape. A single large
trade arriving late in a market's life can simultaneously fire "Clustered trades" (flow family)
and "Late large trade" (timing family) — one real-world event counted as two independent
corroborating families, inflating both `family_bonus` (Research Priority) and `corroboration`
(reliability confidence). The project's own research audit
(`docs/research-paper-evidence-audit.md`, "Overfitting" section: *"family-count bonus inflates
when correlated symptoms fire together"*) already names this risk; it is not resolved in code —
only the three *price* sub-features were consolidated into one family (`scoring.py:88-94`,
correctly handled, a genuine **PASS** on that narrower point).

**Recommended fix:** either measure empirical co-firing rates across families on the live universe
and report them (so "3 independent families" can be qualified with how independent they actually
are), or restructure `timing` as a modifier on `trade_flow` rather than a separate family when
they are triggered by the same trade record.

### N2. A flat-then-single-tick move produces the maximum possible standardised return, regardless of the tick's economic size
**File:** `backend/astrolabe/analytics/zscore.py:70-81` (`flat_baseline_move` branch).

**Failing scenario:** if a market sits at a constant price for the baseline window (`std == 0`)
and then ticks by any nonzero amount greater than `1e-12` — e.g. 0.5000 → 0.5010, a one-tenth of
one probability point move — the function returns `z = ±clip` (±10 by default), the largest z-score
the system ever emits. Through `squash(x, cap=4.0)` (`quality.py:17-21`) this saturates the
`unusual_return` component to its maximum normalised value of 1.0, identical to what a genuine
4+ standard-deviation move would produce. The statistical justification ("a real move off a
perfectly flat baseline is *maximally unusual*") is true in a narrow relative sense but conflates
*statistical* surprise (division by a near-zero baseline std) with *economic* magnitude — nothing
in the code floors the move by an absolute probability-point size before applying the extreme
label.

**Recommended fix:** add a minimum absolute-move floor (e.g. require `abs(move) >= some small
probability-point threshold`, not just `> 1e-12`) before emitting the extreme `flat_baseline_move`
signed value, or scale the extreme by the move's absolute size rather than a fixed clip, so a
one-tick move off a flat baseline does not automatically saturate the strongest component in the
composite.

---

## Verified against the recorded baseline (`docs/signal-replay-functional-baseline.md`)

| Baseline claim | Verified? | Evidence |
| --- | --- | --- |
| #1 Confidence double-standard (Signal Lab 1.00 vs Board reliability) | **Confirmed** | See M1 above; exact line numbers now attached on both sides. |
| #4 Flat moves counted as Arepo misses, but wins for no-change | **Confirmed, and shown to also corrupt the Arepo/momentum/price-only scores themselves**, not just the `moved_expected/against` display counters | See C1; both `replay_stats._correct` and `historical.direction_correct_24h` independently reimplement the same bug. |
| #2 `volume_acceleration` 0/120 | **Confirmed, and shown to silently change the live model's effective weights** on every signal, not just "contributes nothing" | See M2. |
| #5 Thin eligibility funnel (160→4) | **Confirmed as a genuine data limitation**, and additionally: the funnel's *composition* (not just size) is affected by present-day-volume ranking, not just history length (see M4) | See M4. |
| #6 Zero prospective cohorts | **Confirmed.** The resolution-vs-repricing separation required by spec §11 (`docs/methodology.md:606-616`) exists only in the prospective/frozen-cohort pipeline (`evaluation/tracking.py`); since zero prospective cohorts have ever been frozen, **no resolution-based accuracy statistic has ever been computed for real data** — every number a user has seen is pure forward-price movement, never checked against actual market resolution. |

## New findings beyond the recorded baseline
- Brier/log loss are absent from the code entirely, contradicting a prior review document's claim
  that they exist (C2).
- Direction is mechanically momentum, tested at a horizon with no positive prior for momentum
  continuation, and compared against a "momentum" baseline that is not statistically independent
  of it (C3).
- Research Priority and displayed confidence share a mechanical dependency on `n_families` (M3).
- Universe selection for reconstructed Replay uses present-day trading volume, a look-ahead
  channel distinct from and stronger than the disclosed survivorship note (M4).
- Evidence-family independence is asserted in comments but neither tested nor enforced (N1).
- The z-score's flat-baseline extreme-value branch can saturate the strongest composite component
  from an economically trivial tick (N2).

## Overall conclusion
Every number currently shown to a user in Signal Lab, the Opportunity Board and Replay should be
treated as **inconclusive**, and the code's own `sample_verdict`/`inconclusive` labelling on
Replay is the right call. The two changes with the highest priority before any further evaluation
is trusted are C1 (fix the flat-move asymmetry, since it currently drives the entire visible "Arepo
underperforms no-change" headline) and C2 (add Brier/log loss, since a binary hit rate on n=4 can
never be more than anecdotal). C3 is the most consequential long-run finding: until direction is
tested against reversion as well as continuation at multiple horizons, there is no basis to expect
the signal to have positive expected value even in principle, independent of sample size.
