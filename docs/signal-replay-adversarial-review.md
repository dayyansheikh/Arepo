# Signal Lab and Replay — adversarial review

Independent adversarial pass (Agent F) over the functional baseline recorded 2026-08-04
(`docs/signal-replay-functional-baseline.md`). Goal: disprove the honesty of the reported
numbers. Each item below is an attempted disproof: files read, a concrete exploit scenario
constructed, and a verdict (confirmed / refuted) with severity and fix. Skepticism is applied to
the code, not invented — several hunted-for bugs did not hold up and are recorded as refuted so
they are not re-litigated later.

---

## Confirmed findings

### 1. CRITICAL — The flat-move miscount also lives in the *real* prospective evaluation, not only the disclosed illustrative reconstruction

- `backend/astrolabe/evaluation/tracking.py:124-131` (`_movement_correct`):
  ```python
  def _movement_correct(direction, movement):
      if direction is None or movement is None:
          return None
      if direction == "up":
          return movement > 0
      if direction == "down":
          return movement < 0
      return None
  ```
  A 24h move of exactly `0.0` returns `False` for both directions — scored as a miss.
- Consumed by `evaluation/service.py:192-198` into `moved_against`, rendered verbatim in
  `frontend/app/replay/page.tsx:279` (`StatTile label="Moved against"`) and `:330-334`
  (`movementVerdict` → red "Moved against" for `mc === false`, no distinction from a genuine
  directional miss).
- `evaluation/schemas.py:82-97` (`CohortSummary`) has no flat/neutral bucket — only
  `moved_expected` / `moved_against` / `movement_pending`.

**Exploit scenario**: once real prospective cohorts accumulate (currently zero — see finding 5),
any frozen entry whose token happens to sit exactly flat 24h after freeze will be counted in
`moved_against`, identical in weight and UI styling to an entry that moved decisively the wrong
way. The plain-English sentence `evaluation/service.py:257-266` ("Arepo selected N signals... of
those, X moved as expected, Y moved against it") will assert a false "against" verdict for a
market that simply didn't move.

The baseline doc (issue #3) scoped this bug to `historical.py` / `replay_stats.py` only — i.e. to
the explicitly-illustrative reconstructed screen. It missed that the identically-shaped bug is
duplicated, independently, in `tracking.py`, which feeds the "only real long-term performance
record" (per `replay/page.tsx:127-128`). No test exercises `movement == 0` in
`backend/tests/*` for `tracking.py` (`grep` across `backend/tests` found zero hits for
`_movement_correct`/flat with a zero movement case).

**Fix**: introduce one shared flat-aware classifier (generalize `replay_stats.FLAT_EPS` /
`_correct`) used by both `tracking.py` and `historical.py`; add a `moved_flat` field to
`CohortSummary` and `HistoricalScreen`; update both plain-summary generators and the UI verdict
(`movementVerdict` in `replay/page.tsx`) to render a distinct neutral "Flat" tone instead of
folding it into "Moved against."

### 2. MAJOR — Flat-mislabeling materially distorts the reconstructed Replay headline, and the UI presents it with no explanation

Confirms and quantifies baseline-doc issue #3/#4. `historical.py:203-205` and
`replay_stats.py:50-53` both compute `direction_correct(move)` as `move > 0` / `move < 0`, so
`move == 0.0` is `False`. In the captured baseline sample (`docs/signal-replay-functional-baseline.md`
lines 92-98), 2 of the 4 selected entries moved exactly `0.000` over 24h; both are counted in
`moved_against_24h` (Arepo "0/4"), while the "No change" baseline (`replay_stats.py:108-110`,
`abs(m) <= FLAT_EPS`) scores those same two markets **correct** ("No change 2/4").

**Exploit scenario**: `frontend/app/replay/page.tsx:826-833` (`HistoricalRow`) renders those two
flat rows with `direction_correct_24h === false` → red "✗ Against", visually and textually
identical to a genuine wrong-direction call. Directly below, `BaselineTable`
(`replay/page.tsx:655-702`) shows "No change 2/4" in the same table. A reader sees Arepo lose to a
coin-flip-simple baseline by 50 points on an n=4 sample, with no note that half the "losses" and
half the baseline's "wins" are the *same two markets that simply didn't move* — i.e. the same
underlying outcome is booked as a loss for one predictor and a win for another in the same
side-by-side comparison, without disclosure. `BaselineTable`'s only caveat text
(`replay/page.tsx:668-670`, "Any edge must beat these baselines... not statistically meaningful")
addresses sample size, not this asymmetry.

**Fix**: same shared flat bucket as finding 1, applied to `HistoricalEntry`/`HistoricalScreen` and
`compare_baselines`; render a distinct "Flat (no directional call was tested)" verdict in
`HistoricalRow`, and adjust `BaselineComparison`'s no-change scoring or footnote so the flat
overlap between Arepo's denominator and no-change's numerator is stated explicitly.

### 3. MAJOR — Replay's per-row "confidence" is not a real per-entry reliability signal; it is a fixed constant, and it uses the already-flagged wrong confidence definition

- `historical.py:155-162` calls `enrich.compute_token_analytics(..., book=None, ...)` for every
  reconstructed candidate (historical order books are never available, by design).
- `analytics/quality.py:82-84`: `if not two_sided_book: q.penalise(0.3, "incomplete order book
  (one-sided)")`. Since `book=None` always in reconstruction, `two_sided_book` is always `False`,
  so this fixed 0.3× penalty always applies.
- No other penalty in `assess_quality` can fire in this path: `n_history >= min_history(30) >=
  ideal_history(20)` so the short-history penalty never triggers; `relative_spread`,
  `near_mid_depth`, `data_age_seconds` are all `None` for every reconstructed candidate (no book,
  no live timestamp) so their penalties never trigger either.
- Net effect: `sig.confidence` is mathematically pinned to **exactly 0.30** for essentially every
  reconstructed entry, which is exactly what the baseline table shows (conf column: 0.30, 0.30,
  0.30, 0.30, all four rows).
- `HistoricalEntry.confidence = r["sig"].confidence` (`historical.py:254`) — the *raw
  data-quality* term, not `reliability_confidence()` from `opportunity/scoring.py:118-139`, which
  the Board and Market Detail use instead. This is the same cross-surface inconsistency the
  baseline doc's issue #1 already flags for Signal Lab (raw 1.00 vs reliability 0.004–0.762) —
  Replay independently reproduces the identical inconsistency with a different constant (0.30
  instead of 1.00).
- Rendered at `replay/page.tsx:386` and `:849`: `` confidence {formatPercent(entry.confidence, 0)} ``
  — placed next to Signal strength and Research Priority, both of which genuinely vary per row,
  implying "confidence" varies too.

**Exploit scenario**: a user comparing two reconstructed rows with very different lookback depth,
strength, or component mix will see identical "confidence 30%" on both, and reasonably read that
as "Arepo rates these two readings equally reliable," when in fact the number carries zero
per-entry information in this code path — it is a constant artifact of the fact that reconstructed
analysis never has an order book, not a measurement of anything about the specific signal.

**Fix**: either compute and display `reliability_confidence()` consistently on Replay rows (as
already recommended for Signal Lab in baseline issue #1), or drop the misleading fixed figure from
reconstructed rows entirely and state once, structurally: "historical order books are unavailable,
so data-quality confidence for every reconstructed row is capped at the same fixed value and does
not vary."

### 4. MAJOR — No caching and a wall-clock-recomputed cut-off make the reconstructed screen's headline non-reproducible between requests

- `backend/astrolabe/api/routes/historical.py:30`: `as_of = datetime.now(UTC) -
  timedelta(days=days)` — recomputed fresh on **every** call; there is no `as_of` query parameter,
  only relative `days`.
- `run_live_historical` (`historical.py:358-360`) calls `market_service.active_markets(
  requested_mode="live", limit=universe_limit, by="volume_24hr")` — a live Gamma discovery call
  each time, sorted by **today's** 24h volume (see finding 5), then fetches full live price
  history per candidate concurrently (`historical.py:378-384`).
- No caching wraps this endpoint: `backend/astrolabe/api/deps.py`'s `@lru_cache` only memoizes
  singleton service/engine *objects*, not response data; the only response-level cache in the API
  (`SwrCache` in `api/routes/opportunity.py`) wraps `/api/opportunity/board` only, not
  `/api/historical/screen`. The frontend's fetch helper explicitly disables HTTP caching
  (`cache: "no-store"`).

**Exploit scenario**: two calls to `GET /api/historical/screen?days=7` a few minutes apart use two
different `as_of` instants and two independently-fetched "today's top-volume" universes; if the
live 24h-volume ranking shifts near the `limit=80` boundary, or if a market crosses/re-crosses the
near-mid gate between calls, the eligible set (and therefore `selected`, `moved_against_24h`,
`baseline_comparison`, `sample_verdict`, and the entire plain-English summary) can differ between
two back-to-back page loads with identical query parameters. The functional-baseline doc's
"Arepo 0/4" headline is a one-off snapshot (it says so — "Raw JSON archived"), but nothing in the
product itself discloses to an ordinary user that reloading the Replay page can silently produce a
different sample and a different verdict for the "same" 7-day cut-off.

**Fix**: pin `as_of` to a deterministic point (e.g. UTC midnight N days ago) and cache the response
for that calendar day, so the same `days` value is reproducible intraday; alternatively, add an
explicit UI/API disclosure that the reconstruction is recomputed live on every load and results can
move between visits.

### 5. MAJOR — Survivorship bias in the reconstruction's candidate universe is real, structural, and stated more mildly than it is

- `market_service.py:289-299` (`active_markets`) has no point-in-time parameter; it always sorts
  **today's** live market list.
- `sources.py:119-125` (`LiveSource.markets`): Gamma discovery is called with `active=True,
  closed=False` — i.e. only markets that are *still open right now* are ever candidates, for every
  cut-off (1/3/7/14/30 days back).
- `historical.py:344-356` (docstring on `run_live_historical`) calls this "a mild survivorship
  effect: a market that has since resolved trades less now, so it is less likely to be scanned" —
  understating that it isn't merely "less likely," it is a **hard, 100% exclusion**: any market
  that has closed/resolved between the cut-off and now can never appear in the reconstruction at
  all, for any `days` value.

**Exploit scenario**: this is very likely the dominant cause of the 160→4 eligible funnel reported
in the baseline (issue #5): the universe is skewed toward markets that are *still* genuinely
uncertain today (else they'd have closed and dropped out), which correlates with markets less
likely to have made a large, decisive move in the reconstructed window — the opposite of a
representative sample of "what Arepo would have flagged historically." It is disclosed (assumptions
list, `historical.py:326-328`, and baseline issue #5), so this is not hidden, but "mild" is the
wrong word for a filter that can zero out an entire category of outcome.

**Fix**: reword the limitation to state the exclusion is total, not mild; longer-term, source the
historical top-volume snapshot from a persisted daily market list (already-closed markets
included) rather than only today's live discovery.

### 6. MAJOR (backend gap, currently mitigated only by the frontend) — `/api/cohorts/latest` and `/api/cohorts/weeks` are not filtered by provenance, and right now `/api/cohorts/latest` returns the synthetic demo cohort

- `evaluation/repository.py` `list_cohorts()`: `SELECT * FROM weekly_cohort ORDER BY iso_year
  desc, iso_week desc` — no `WHERE provenance_class = ...` clause.
- `api/routes/cohorts.py:19-22` (`/api/cohorts/weeks`) and `:31-42` (`/api/cohorts/latest`) both
  consume this unfiltered list; `/latest` takes `weeks_list[0]` with no provenance check at all.
- Per the baseline's own data-status capture (`docs/signal-replay-functional-baseline.md` lines
  132-144): `weekly_cohorts_total = 1`, `prospective_cohorts = 0` — the **only** cohort that exists
  in the database right now is the synthetic 2026-W28 demo (`evaluation/seed.py`, fabricated
  forward-price drifts and a forced-true/forced-false resolution pair). This means
  **`GET /api/cohorts/latest`, called right now, returns that synthetic cohort** — fabricated
  data — as "the most recent cohort," with `provenance_class: "synthetic"` present only as a field
  inside the payload the caller must know to check.
- Only `CohortReadService.provenance()` (`evaluation/service.py:82-105`,
  `GET /api/cohorts/provenance`) correctly separates prospective/reconstructed/synthetic counts.

**Exploit scenario**: any API consumer other than this specific frontend page — a partner
integration, a mobile client, a future dashboard, or simply `curl
/api/cohorts/latest` — gets synthetic, fabricated performance data back from an endpoint named
"latest," with no structural signal that it isn't real. The current frontend avoids surfacing this
by (a) defaulting the Replay page to the "historical" tab, not "prospective"
(`replay/page.tsx:73-79`, with an explicit in-repo comment: *"the prospective cohort list, which
currently holds only labelled synthetic demo data and showed a stale cohort as if it were
current"*), and (b) labelling non-prospective weeks in its own dropdown and banner
(`replay/page.tsx:173-175,189-190,215-229`) — i.e. the acknowledged fix is entirely client-side.
The backend endpoint itself has no such guard.

**Fix**: filter `/api/cohorts/latest` (and by default `/api/cohorts/weeks`) to
`provenance_class == "prospective"`, returning an honest 404/empty state ("no prospective cohorts
recorded yet") instead of silently substituting synthetic data; keep synthetic access available
only via an explicit opt-in parameter or the dedicated `/api/cohorts/{year}/{week}` lookup by
exact (labelled) week.

---

## Attempted disproofs that did not hold up (refuted)

- **Triple-counting the 3 price features as 3 evidence families.** `opportunity/scoring.py:88-94`
  (`_price_family`) takes the `max()` over `unusual_return` / `movement_abnormality` /
  `volatility_regime` and contributes exactly one `FAMILY_PRICE` entry to `family_mag`; `n_families`
  and the reliability-confidence corroboration term (`scoring.py:135`) both key on distinct family
  identifiers, not components. Not a bug.
- **Duplicated binary markets (Yes/No double counting).** Deduped consistently in three places:
  Signal Lab (`market_service.py:457-471`, `best_by_market` keyed by `market_id`), Opportunity
  Board (`opportunity/service.py:118-121`, `max(analytics, key=strength)` per market), and Replay
  reconstruction (`historical.py:232-241`, explicit `seen`/`deduped` set on `market_id`). Baseline
  doc's own "Duplicate binary complements: 0" figure checks out against the code.
- **Missing components treated as zero.** `composite_anomaly_score`
  (`analytics/anomaly.py:110-135`) renormalizes weights over only the present components (a
  missing input is excluded from both numerator and denominator, not zeroed); `_volume_acceleration`
  (`enrich.py:53-56`) explicitly returns `None`, not `0.0`, on insufficient data; component
  completeness in `scoring.py:257-262` degrades the confidence multiplier rather than zeroing the
  score. Consistent with the documented design.
- **Misleading "edge"/"beat"/"outperform"/"proven"/"accurate" language on the Replay/Signals
  pages.** Every occurrence of "edge" or "beat" in `replay/page.tsx` is explicitly hedged/negating
  ("no edge... claims no edge," "any edge must beat these baselines... not statistically
  meaningful," "not proof that Arepo has an edge"); "outperform," "proven," and "accurate" do not
  appear in either file. `signals/page.tsx` explicitly warns against over-reading strength as a
  verdict and against treating the score as insider-trading evidence. No hype language found here
  (repo-wide docs were not exhaustively re-audited beyond the requested grep, which surfaced only
  hedged usages).
- **Unhandled pending/closed markets producing a fabricated forward price.**
  `_price_at_or_after` (`historical.py:106-112`) falls back to the last known price only when the
  series genuinely ends before the target time (i.e. the market stopped trading), and documents
  this explicitly rather than inventing a value. For a resolved market this correctly reflects the
  settled price. Not a look-ahead or fabrication bug.

---

## Summary table

| # | Severity | File:line | Issue |
| --- | --- | --- | --- |
| 1 | CRITICAL | `evaluation/tracking.py:124-131`, `evaluation/service.py:192-198` | Flat-move miscount duplicated in the real prospective evaluation pipeline, undisclosed and untested |
| 2 | MAJOR | `evaluation/historical.py:203-205`, `replay_stats.py:50-53,108-110`, `replay/page.tsx:826-833` | Flat reconstructed moves shown as red "Against" identical to genuine misses; drives the "Arepo 0/4" headline undisclosed |
| 3 | MAJOR | `evaluation/historical.py:155-254`, `analytics/quality.py:82-84` | Replay confidence column is a fixed constant (0.30), not a real per-entry signal; also uses the wrong (raw, not reliability) confidence definition |
| 4 | MAJOR | `api/routes/historical.py:30`, no caching | Reconstructed screen's `as_of` and candidate universe are live-recomputed every call; headline numbers are not reproducible between page loads |
| 5 | MAJOR | `market_service.py:289-299`, `sources.py:119-125` | Candidate universe hard-excludes any market that has since closed; understated as "mild" survivorship |
| 6 | MAJOR | `api/routes/cohorts.py:31-42`, `repository.py list_cohorts` | `/api/cohorts/latest` unfiltered by provenance; currently returns the synthetic demo cohort as "latest" |

---

## Re-review after fixes (branch `arepo-signal-replay-functional-validation`, commits d6976e9..b1e94f9)

Verified by reading `replay_stats.py`, `zscore.py`, `scoring.py`, `enrich.py`, `historical.py`,
`tracking.py`, `service.py`, `cohorts.py`, `api/routes/historical.py`, the frontend
`types.ts`/`SignalItem.tsx`/`signal-arrange.ts`/`OutcomePanel.tsx`/`ModelView.tsx`, running
`pytest` (318 passed), and curling the live server (`/api/signals`, `/api/markets/{id}`,
`/api/cohorts/latest`, `/api/cohorts/weeks`, `/api/cohorts/2026/28`).

1. NEW, MAJOR | `frontend/components/OutcomePanel.tsx:42` + `astrolabe/service/enrich.py:155,180` + `astrolabe/service/schemas.py:37` | **Market Detail's per-outcome card still displays the raw 100% data-quality confidence, unlabeled, as "confidence".** `enrich.outcome_view()` sets `OutcomeView.confidence = ta.confidence = signal.confidence` (the raw data-quality term), and `OutcomeView` has no `reliability_confidence` field at all — the fix was applied to the `Signal` payload (`SignalItem.tsx`, `signal-arrange.ts` correctly use `signal.reliability_confidence ?? signal.confidence`) but never reached `OutcomeView`/`OutcomePanel`. Live-verified: `GET /api/markets/2747434` returns `outcomes[0].confidence: 1.0` with no `reliability_confidence` key, while the market's own `signals[0]` in the same response carries `confidence: 1.0, reliability_confidence: 0.82`. `OutcomePanel.tsx:42` renders `confidence {formatPercent(outcome.confidence, 0)}` unqualified, right next to the `DataQualityBadge`, on the same market-detail page where `ModelView.tsx:65` correctly labels its own (intentionally-raw) figure `"Confidence (data quality)"`. This directly contradicts fix claim #1 ("Market Detail now displays reliability_confidence... no surface shows 100%") — one card on that exact page still can and does show 100%. `tests/unit/test_cross_surface.py` only exercises `signal_reliability()`/`Signal` directly, never `OutcomeView`, so this gap has no test coverage and the suite is green despite it.
2. NEW, MODERATE | `astrolabe/analytics/backtest.py:164-198` (used by `service/market_service.py:480`, exposed at `GET /api/replay/backtest`, rendered in `frontend/app/replay/page.tsx:988-990` "Show the signal backtest (demonstration dataset)") | **The flat-handling fix does not reach the separate demo backtest module.** `run_backtest`'s `followed_through`/`hit_rate`/`false_positive_rate` are computed from `dir_sign * forward_move >= move_threshold` with no `classify_directional`/`FLAT_EPS` involved; a forward move that is genuinely flat (near zero, below the 0.02 `move_threshold`) is counted into `no_follow` and thus into `false_positive_rate` exactly as a directionally-wrong move would be — the same class of flat-as-miss conflation the fix pass eliminated in `evaluation/historical.py` and `evaluation/tracking.py`. This module is out of the fix pass's stated scope and untouched by `test_replay_regression.py`, but it is a user-visible number on the Replay page, so the flat leak the task asked me to hunt for does exist here.
3. Confirmed correct | `astrolabe/evaluation/replay_stats.py:28-129` | `classify_directional`/`_score` are shared by every predictor identically (Arepo, no-change, current-implied, price-only, momentum, always-up, always-down all route through the same function), so flats are excluded from every predictor's hit-rate denominator, not just Arepo's. One subtlety, not a bug: the flat check (`abs(move) <= flat_eps`) runs *before* the abstain check (`direction not in ("up","down")`), so a market that is both flat and one where the predictor made no directional call is bucketed as `"flat"` rather than a distinct abstain/`None`. This does not affect the hit-rate math (`n = correct + incorrect`, flats excluded either way) but means Arepo's reported "flat" count can include markets where Arepo had no call at all, not just markets where it called and was flat. Cosmetic, not a scoring bug.
4. Confirmed correct | `astrolabe/evaluation/tracking.py:126-131`, `astrolabe/evaluation/service.py:187-274` | Both route through `classify_directional`; `CohortSummary.moved_flat` is wired end-to-end and shown in the plain-language summary. Live-verified against the synthetic cohort (`GET /api/cohorts/2026/28`): `moved_flat: 0` present and consistent with `moved_expected`/`moved_against`/`movement_pending`.
5. Confirmed correct | `astrolabe/analytics/zscore.py:29,78-91` | `FLAT_BASELINE_MIN_MOVE = 0.005` correctly gates the "flat baseline, real move" branch: a sub-materiality move off a zero-variance baseline now returns `None`/`"zero_variance"` instead of saturating to +/-clip; only a move `>= 0.005` yields the signed extreme. Matches spec intent, no leak found elsewhere in `zscore.py`.
6. Confirmed correct | `astrolabe/api/routes/cohorts.py:31-49` | `/api/cohorts/latest` filters `provenance_class != "synthetic"` and 404s honestly when only synthetic exists — live-verified (`GET /api/cohorts/latest` → 404 while only the synthetic 2026-W28 cohort exists). `/weeks` and `/{iso_year}/{iso_week}` are not filtered, but this is not a bypass: both responses carry `provenance_class: "synthetic"` so a direct week request is still clearly labelled (verified: `GET /api/cohorts/2026/28` returns `note: "Synthetic demonstration cohort..."`), and `CohortReadService.provenance()`/`available_weeks()` keep synthetic counted separately from prospective/reconstructed. No evidence synthetic leaks into aggregate performance stats.
7. Confirmed correct | `astrolabe/api/routes/historical.py:30-40` | Cut-off is built directly as `datetime(target_day.year, target_day.month, target_day.day, tzinfo=UTC)` — the start of the target UTC day — so repeated same-day requests with the same `days` resolve to the same cut-off, as claimed.
8. Confirmed correct | `astrolabe/evaluation/replay_stats.py:90-108,181-194` | `arepo_momentum_agreement` and `probabilistic_metrics_note` are computed/wired correctly and threaded through `historical.py`'s `baseline_comparison` dict.
9. Confirmed correct | import graph | No cycle: `astrolabe.service.enrich` and `astrolabe.opportunity.scoring` both import cleanly under the venv interpreter; the lazy `from ..opportunity.scoring import signal_reliability` inside `enrich.compute_token_analytics` is defensive style, not required to break a cycle (`opportunity/scoring.py` has no import back to `service`).
10. Confirmed correct | `astrolabe/opportunity/scoring.py:142-156`, `tests/unit/test_confidence_reliability.py` | Excluding `volume_acceleration` from `COMPLETENESS_COMPONENTS` is well-reasoned (live path never populates it) and the existing confidence tests operate on the pure `reliability_confidence()` function with explicit `component_completeness` args, so they're insulated from this change either way — no evidence of a test being adjusted to paper over a regression. However, no test directly exercises `_component_completeness`/`signal_reliability` against a `Signal` with populated vs. missing `volume_acceleration` to confirm live-path confidence isn't silently over- or under-stated; this is a coverage gap, not a demonstrated bug.
