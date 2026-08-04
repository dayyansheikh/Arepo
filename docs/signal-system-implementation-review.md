# Signal system implementation review (Agent D)

Independent code audit of the signal pipeline: ingestion → persistence → feature creation →
normalisation → direction → confidence → ranking → API → Signal Lab → Opportunity Board → Market
Detail → alerts → Replay. Cross-checked against `docs/signal-replay-functional-baseline.md`
(recorded 2026-08-04). Findings are code-grounded (file:line); each was traced, not assumed.

---

## Severity-ranked findings

### 1. HIGH — Directional gate disagrees between Board and Signal Lab / Market Detail for the same signal
- **Backend** (`backend/astrolabe/opportunity/hypothesis.py:26-35`): `has_directional_view` requires
  a resolved direction **AND** (`n_families >= 1` **OR** `signal_strength >= 0.40`). `n_families`
  (`backend/astrolabe/opportunity/scoring.py:214-215`) counts price, book (`_book_family`,
  scoring.py:97-102, fires at `book_imbalance` normalized ≥ 0.5), flow, wallet and timing families —
  the last three only exist in Live mode from trade data.
- **Frontend** (`frontend/lib/directional.ts:34-49`): `directionalVerdict`, used identically by
  Signal Lab (`SignalItem.tsx:23`) and Market Detail (`ModelView.tsx:16`), only checks
  `strength >= 0.40` **OR** `priceFamilyFires` (price components only). It never looks at
  `book_imbalance`, and cannot look at flow/wallet/timing at all — the `Signal` type
  (`frontend/lib/types.ts:85-103`) carries none of that (those live only on `OpportunityCard`).
- **Consequence**: a signal whose only firing family is order-book imbalance (`book_imbalance`
  normalized ≥ 0.5) with composite strength < 0.40 (diluted by other weighted components), or one
  whose directional case rests on a live trade-flow/wallet/timing family, is `directional=true` on
  the Board but shows "Observational only, not a directional view" on Signal Lab and Market Detail
  for the identical market/token. The `directional.ts` header comment claims it "mirrors the
  backend rule" — it mirrors only the price-family half of it.
- **Fix**: either expose `n_families`/family membership on the `Signal`/`OutcomeView` API contract
  so the frontend gate can be identical to the backend's, or (simpler) have Market Detail and Signal
  Lab consume the same `has_directional_view` inputs already computed server-side (extend
  `SignalsResponse`/`MarketDetail` to carry a `directional: bool` + `n_families` per signal, computed
  once in `market_service.py`, instead of recomputing a partial version in the browser).

### 2. HIGH — Confidence is two different numbers across surfaces, confirmed at both API and label level
- `signals.py:13-19` → `MarketService.signals()` (`market_service.py:445-473`) returns raw
  `Signal.confidence`, which is `quality.confidence` from `assess_quality`
  (`backend/astrolabe/analytics/quality.py:38-46`) — a pure data-quality term that is exactly `1.0`
  whenever history/spread/depth/freshness/book-sidedness are all healthy (baseline: 1.00/1.00/1.00
  across all 15 Signal Lab entries).
- `opportunity/service.py:137-141` (Board) and `evaluation/historical.py` both call
  `score_opportunity`, whose returned `confidence` is `reliability_confidence(...)`
  (`scoring.py:118-139`) — data quality × family corroboration × microstructure completeness
  (baseline: 0.004–0.762 over the same universe).
- Frontend labelling is honest where it appears: `ModelView.tsx:65` explicitly says "Confidence
  (data quality)"; `SignalItem.tsx:121,151` and `frontend/lib/metrics.ts:35-42` describe the same
  raw data-quality meaning. **However**, `OpportunityCardView.tsx` never renders `card.confidence`
  numerically at all (verified: `grep -rn "\.confidence\b" frontend/components frontend/app` finds
  it nowhere in the Board card). So the reliability number is computed and returned by the API but
  currently invisible on the Board UI — not a side-by-side contradictory number on screen, but a
  materially different quantity silently backing two different card fields (see #3) while sharing
  the same field name (`confidence`) as the data-quality number shown elsewhere.
- **Fix**: rename one of the two so `confidence` is a single contract-wide meaning (e.g. keep
  `Signal.confidence` = data quality, rename `OpportunityCard.confidence` →
  `reliability_confidence`), and pick one number to actually surface on every card face.

### 3. HIGH — Alert eligibility silently filters on reliability confidence while its own UI copy calls it "data quality"
- `backend/astrolabe/alerts/service.py:74` (`eligibility`) and
  `backend/astrolabe/alerts/user_alerts.py:60` (`user_matches`) gate on `card.confidence`, i.e.
  `reliability_confidence` (max ~0.76 in the baseline universe).
- `frontend/app/account/page.tsx:190-198`: the "Minimum confidence" slider's hint reads *"Only
  alert me when the data quality is at least this good"* and is described 0–100%.
- **Consequence**: a user who sets "min confidence" to 90% believing it maps to the (near-universal)
  "good" data-quality band will receive **zero** alerts — that threshold is essentially unreachable
  under `reliability_confidence`'s current range — with no indication why. The control's real
  meaning (multi-family corroboration + completeness, not data cleanliness) is never disclosed.
- **Fix**: correct the hint text to describe reliability/corroboration, or rename the preference to
  match what it actually filters on.

### 4. MEDIUM — `volume_acceleration` is wired but structurally dead (0/120), confirmed at the source
- Live/cached path: `enrich.py:100` prefers `changes.volume_acceleration` from
  `microstructure_store.changes_for_token` → `microstructure_changes.volume_acceleration`
  (`backend/astrolabe/analytics/microstructure_changes.py:66-77`), which differences
  **cumulative** market volume snapshots and requires ≥5 snapshots *and* a positive baseline delta
  (`baseline <= 0 → None`, line 75-76). `record_snapshot` stores `market.volume` (lifetime
  cumulative volume) once per minute-bucket per token (`microstructure_store.py:106-108`); for most
  polled markets this barely changes between 5-minute collector ticks, so `deltas` are frequently
  all-zero and the baseline check returns `None` every round — confirmed present-count 0/120 at
  baseline despite 493 stored snapshots.
- Replay-only fallback `enrich.py:53-62` (`_volume_acceleration`) is never reached live/cached
  because `volumes` is only populated in replay mode (`market_service.py` passes `td.volumes` from
  the source; live/cached `TokenData.volumes` is not populated with a real series either — same root
  cause).
- This component still carries a non-zero composite weight (`DEFAULT_WEIGHTS["volume_acceleration"]
  = 0.12`, `anomaly.py:29`) that is silently renormalised away every single time in live/cached mode,
  and it is still listed in `SignalItem.tsx`'s component table (always rendered as "Not enough
  volume history yet" — a permanent, never-resolving placeholder row per spec §4).
- **Fix**: either lower the collector interval / use a per-tick trade-volume delta instead of
  cumulative lifetime volume as the baseline input (so deltas are non-zero often enough), or disable
  the component (drop weight, remove from `DEFAULT_WEIGHTS`/`DEFAULT_CAPS` and the UI's component
  table) until it can genuinely populate, per spec §4's "remove permanently-empty placeholders."

### 5. MEDIUM — Flat 24h forward moves scored as directional misses (confirmed, asymmetric with no-change baseline)
- `backend/astrolabe/evaluation/historical.py:205`: `dir_correct = (move24 > 0) if sig.direction ==
  "up" else (move24 < 0)` — a move of exactly `0.0` is `False` for any resolved direction.
- `backend/astrolabe/evaluation/replay_stats.py:50-53` (`_correct`) has the identical asymmetry.
- `backend/astrolabe/evaluation/replay_stats.py:110`: the no-change baseline instead uses `abs(m) <=
  FLAT_EPS` (0.01) as **correct**.
- No `flat` bucket exists in `HistoricalScreen` (`historical.py:78-90`) — only
  `moved_expected_24h`/`moved_against_24h`/`pending_24h`.
- **Fix**: add a `flat` outcome bucket using the same `FLAT_EPS` threshold as the no-change
  baseline, and exclude flat moves from "against" counts (or count them separately), matching spec
  §10/§11.

### 6. LOW — 2822017 has no automated regression test; only 2694364 does
- `backend/tests/unit/test_market_routing.py` covers only id `2694364` in all three tests (lines
  1-77). `docs/market-routing-investigation.md:52` claims both `2694364` and `2822017` were manually
  verified in `live`/`replay`, but no hermetic respx-mocked test exercises `2822017`. The fix is
  generic (canonical-id fallback via `LiveSource.get_market`, `market_service.py:390-406`), so this
  is a coverage gap, not a known-broken path — but the spec explicitly names both IDs, and only one
  is guarded against regression.
- **Fix**: parametrize `test_canonical_id_resolves_in_all_modes` (or add a twin fixture) for
  `2822017`.

### 7. LOW — `MicrostructureChanges` is honestly `None`-on-missing; no missing-as-zero found in the traced piperic
- Checked `enrich.py`, `scoring.py`, `anomaly.py`, `quality.py`, `microstructure_changes.py`,
  `opportunity/service.py` for `or 0` / `?? 0` patterns masking missing data as zero. The only
  `or 0.0` uses found (`anomaly.py:135`, `opportunity/service.py:275,285`) are legitimate
  divide-by-zero guards on denominators (`wsum`, `markets`, `tokens`), not missing-value coercions.
  Confidence, components and family counts correctly propagate `None`/absence rather than `0`.
  **PASS.**

---

## Stage-by-stage trace summary

| Stage | File | Verdict |
| --- | --- | --- |
| Ingestion / persistence | `ingest/microstructure_store.py` | PASS (idempotent per-minute, provenance-tagged); volume_acceleration input choice is the root cause of #4 |
| Feature creation | `service/enrich.py`, `analytics/anomaly.py` | PASS; missing components stay `None`, weights renormalise correctly |
| Direction | `analytics/anomaly.py:166-168` | PASS (sign of zscore only when present) |
| Confidence (data quality) | `analytics/quality.py` | PASS as a data-quality term; see #2/#3 for surface mismatch |
| Confidence (reliability) | `opportunity/scoring.py:118-139` | PASS as computed; see #2/#3 for exposure/labelling |
| Ranking (Research Priority) | `opportunity/scoring.py:172-284` | PASS |
| API (signals/opportunity/markets/historical/replay) | `api/routes/*.py` | PASS — each endpoint returns exactly what its service computes; the defect is in what the services compute/label, not the routes |
| Signal Lab (frontend) | `app/signals/page.tsx`, `SignalItem.tsx` | Defect #1 (gate), otherwise honest labelling |
| Opportunity Board (frontend) | `OpportunityCardView.tsx` | Defect #2/#3 (confidence not shown / mislabeled downstream) |
| Market Detail (frontend) | `app/markets/[id]/page.tsx`, `ModelView.tsx` | Defect #1 (gate) |
| Alerts | `alerts/service.py`, `alerts/user_alerts.py`, `app/account/page.tsx` | Defect #3 |
| Replay | `evaluation/historical.py`, `evaluation/replay_stats.py` | Defect #5 |

## Cross-surface consistency table

For the same underlying signal/token, what each surface shows:

| Surface | Direction | Strength | Confidence shown | Evidence-family count | Directional gate used |
| --- | --- | --- | --- | --- | --- |
| Signal Lab | `signal.direction` | `signal.strength` | raw data-quality (`signal.confidence`, ≈1.00 when data is good) | not shown | frontend `directionalVerdict` (price family + strength only) |
| Opportunity Board | `card.direction` (only if `directional`) | `card.signal_strength` | **not displayed** (reliability value computed but unrendered) | `card.n_families` shown as "N independent lines of evidence" | backend `has_directional_view` (price/book/flow/wallet/timing families + strength) |
| Market Detail | `signal.direction` | `signal.strength` | raw data-quality, labelled "(data quality)" | not shown | frontend `directionalVerdict` — **same code path as Signal Lab**, so Market Detail and Signal Lab agree with each other but not with the Board (#1) |
| Alerts | n/a (subject line only) | `card.signal_strength` gate | reliability confidence gate, mislabelled "data quality" in UI (#3) | `card.n_families` gate | backend `has_directional_view` (via `card.directional`/board build) |
| Replay (reconstructed) | `sig.direction` | `sig.strength` | raw data-quality (`entry.confidence`) | components listed, no family count | own `dir_correct` movement check (#5), not the directional-view gate |

---

## Answers to the specific questions asked

- **Signal Lab confidence label**: displays and labels `signal.confidence`, the raw data-quality
  term, consistently as "Confidence" with a data-quality-flavoured tooltip
  (`frontend/lib/metrics.ts:35-42`) — matches what it actually is.
- **Board/Market Detail reliability path**: Market Detail actually shows the *same raw* data-quality
  confidence as Signal Lab (both consume `Signal.confidence` via `SignalItem`/`ModelView`), not
  reliability. Only the Board's API payload (`OpportunityCard.confidence`) carries
  `reliability_confidence`, and it is not rendered as a number anywhere in the Board UI today. The
  baseline's framing ("Board and Market Detail show reliability") is only half right: Market Detail
  shows the same number as Signal Lab; the Board computes but hides the reliability number, and only
  gates alerts on it internally.
- **Directional gate consistency**: NOT consistent. See finding #1 — Board's gate (`n_families>=1
  OR strength>=0.40`, families spanning price/book/flow/wallet/timing) is broader than the
  frontend's shared gate (`strength>=0.40 OR price-family-only`) used by both Signal Lab and Market
  Detail.
- **`volume_acceleration`**: wired end-to-end (weight, cap, UI row, missing-reason copy) but
  structurally returns `None` live/cached because the baseline-delta of cumulative lifetime volume
  is usually zero between 5-minute polls. Candidate for removal or a redesigned input per spec §4.
- **Empty component placeholders**: `volume_acceleration`'s row in `SignalItem.tsx`'s component
  table is a permanent, never-resolving "Not enough volume history yet" placeholder given #4 — this
  is the one concrete instance found.
- **Identifier routing**: canonical resolution (`market_service.py:390-406`,
  `LiveSource.get_market`) is id-generic, not ID-specific, so both `2694364` and `2822017` route
  correctly by design and by manual verification recorded in
  `docs/market-routing-investigation.md`. Automated test coverage only exists for `2694364` (#6).
- **Missing-as-zero**: none found in the traced pipeline (confidence, components, family counts all
  propagate `None`); the only `or 0.0` uses are safe division-by-zero guards.
