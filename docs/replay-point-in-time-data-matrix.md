# Replay point-in-time data provenance matrix

Independent Agent C review (historical-data / provenance track). Traces every field the Replay
system (reconstructed screen + prospective cohorts) surfaces back to its source, and judges
whether it was genuinely knowable at the point in time it is presented as describing.

Scope read in full: `docs/signal-replay-functional-baseline.md`,
`backend/astrolabe/evaluation/historical.py`, `replay_stats.py`, `models.py`, `engine.py`,
`snapshots.py`, `tracking.py`, `service/market_service.py`, `service/sources.py`,
`service/enrich.py`, `ingest/normalize.py`, `ingest/microstructure_store.py`, `ingest/pipeline.py`,
`api/routes/historical.py`, `api/routes/replay.py`, `analytics/consistency.py`.

## Classification key

- **historical** = available-historically-from-official-source (immutable/archival at origin)
- **prospective** = stored-prospectively-by-Arepo (only accumulates forward from when a collector runs)
- **limited** = reconstructable-with-limitations (real, but an unverified or degraded proxy)
- **current-only** = only the present value is obtainable; no historical series exists
- **unavailable** = not obtainable for a past cut-off at all
- **synthetic** = fabricated/illustrative, never presented as a real observation

## Point-in-time availability matrix

| Field | Reconstructed screen (`historical.py`) | Prospective cohort (`snapshots.py`/`engine.py`) | Class | Notes |
| --- | --- | --- | --- | --- |
| Market existence | Universe = today's Gamma `active=True, closed=False` list only | Same (current `enrich_markets`) | **current-only / limited** | A market that existed and was active at the cut-off but has since closed is 100% excluded (`sources.py:119-124`), not merely deprioritized. Hard survivorship filter. |
| Title (question) | Current Gamma `question` field, fetched now | Current, at snapshot time (accurate — that's the actual capture instant) | **limited** (reconstructed) / **historical** (prospective) | Reconstructed mode assumes today's title equals the title at the cut-off; never verified. |
| Close date (`end_date`) | `cand.end_date = m.end_date`, current Gamma `endDate`, treated as "known at the cut-off" (`historical.py:48,177`) | `expected_close = market.end_date` at capture time (correct — real snapshot-time value) | **limited** (reconstructed) / **historical** (prospective) | See Critical Check 2 below — the "known at the time" assumption is asserted in a comment but not verified against Gamma's actual edit history. |
| Outcome token IDs | From `clobTokenIds`, immutable at market creation | Same | **historical** | Sound. |
| Condition ID | From `conditionId`, immutable | Same | **historical** | Sound. |
| Price history | Real timestamped CLOB `/prices-history`, split prefix/suffix at `as_of` (`historical.py:136-140`) | Real, at capture instant | **historical** | This is the one genuinely archival, causal series in the system. |
| Public trades | Never fetched; `score_opportunity(sig, [], ...)` (`historical.py:171`) | Fetched live at snapshot time only; no persisted trade store found | **unavailable** (reconstructed) / **current-only** (prospective) | Correctly excluded from reconstruction — no leak. |
| Order books | `book=None` passed explicitly (`historical.py:159`) | Live book at snapshot time; not persisted in full (only spread/depth summaries) | **unavailable** (reconstructed) / **current-only** (prospective) | Correctly excluded from reconstruction — no leak. |
| Spread | Not computed (no book) | `microstructure_snapshots` table, forward-collecting only (`microstructure_store.py:1-11`) | **unavailable** (reconstructed) / **prospective** (live, forward-only) | No historical spread series exists before Arepo started collecting. |
| Depth (near-mid) | Not computed (no book) | Same `microstructure_snapshots` series | **unavailable** (reconstructed) / **prospective** | Same as spread. |
| Wallet activity | Not fetched | Live-only pull for flow/wallet-concentration in opportunity scoring; not persisted | **unavailable** (reconstructed) / **current-only** (prospective) | Correctly excluded from reconstruction. |
| Liquidity | Explicitly passed `liquidity=None` to `score_opportunity` (`historical.py:171`) | Current Gamma `liquidity` field only, no historical series | **unavailable** (reconstructed, by design) / **current-only** | Correctly excluded — no leak into historical scoring. |
| Volume (cumulative/24h) | `volumes=[]` passed to `compute_token_analytics` (`historical.py:160`) | `cumulative_volume` recorded prospectively per snapshot | **unavailable** (reconstructed) / **prospective** | `volume_acceleration` is `None` in both baseline live (0/120) and reconstructed paths. |
| Resolution | N/A to reconstructed screen | `market_resolution()` derives from **current** Gamma status+price (closed & one outcome ≥0.99); `resolved_at` is stamped `utcnow()` at poll time, not the true oracle resolution timestamp (`tracking.py` via `service.py:316-333`) | **limited** | Resolution fact itself is real once it fires; the recorded *time* of resolution is poll-time, not event-time — minor imprecision, low impact since it's forward-only tracking. |
| Category | Derived from current Gamma event tags, recomputed at fetch (`normalize.py:339-351`) | Same, at snapshot time | **limited** (reconstructed) / **historical** (prospective) | Assumes tags unchanged since cut-off. |
| Other metadata (slug, description, tick size, image) | Current Gamma fetch | At snapshot time | **limited** (reconstructed) / **historical** (prospective) | Same class of assumption as title/category. |
| Evidence tags (flow/wallet/imbalance labels) | Cannot fire — no book/trades in reconstruction | Real, from live book/trades at snapshot time | **unavailable** (reconstructed) / **historical** (prospective) | Degrades honestly to price-only; no fabricated tags. |
| Confidence inputs (`data_quality`) | `n_history` real; `relative_spread`, `near_mid_depth`, `data_age_seconds` all `None`; `two_sided_book=False` (forced) | All real, from the live book at snapshot time | **limited** (reconstructed) / **historical** (prospective) | Reconstructed confidence is honestly degraded (~0.30 ceiling per `replay-report-reconciliation.md` §2.2), not a leak. |
| Research Priority inputs | `score_opportunity(sig, [], liquidity=None, relative_spread=None, data_age_seconds=None, now=as_of)` (`historical.py:170-172`) | All real components at snapshot time | **limited** (reconstructed) / **historical** (prospective) | Confirmed price-only; no current-state leak (see Critical Check 3). |

---

## Critical checks

### 1. Does `run_live_historical` use TODAY's active market list and filter backwards? Survivorship bias from current 24h volume?

**CONFIRMED**, and worse than the code's own comments claim.

- `historical.py:358-360` calls `market_service.active_markets(requested_mode="live", limit=universe_limit, by="volume_24hr")`.
- `active_markets` (`market_service.py:289-299`) sources markets from `source.markets()`, which for `LiveSource` is `gamma.list_events(active=True, closed=False)` (`sources.py:119-124`) — **today's** currently-active, non-closed markets only.
- Any market that was active and tradeable at the cut-off (e.g. 7 days ago) but has since resolved/closed is **completely excluded** from the candidate universe, not merely down-ranked. `_is_tradeable`/Gamma's `closed=False` filter removes it outright.
- The `active_markets` docstring (`market_service.py:292-296`) claims *"the historical retrospective sorts by total 'volume'"* — but the actual call passes `by="volume_24hr"`, i.e. **today's** trailing-24h trading activity, not total volume and not activity as of the cut-off. This is a documentation/implementation mismatch and a genuine current-info-in-selection issue: which markets get screened for a 7-day-old cut-off is decided by how much they have traded **in the last 24 hours from now**.
- Concrete scenario: a market that traded heavily in the week around 7 days ago, then went quiet, would score low on today's `volume_24hr` and be dropped from the candidate universe even though it had a perfectly reconstructable price history and would have been discoverable at the cut-off. Conversely, a market that only became active/liquid in the last 24 hours (after the cut-off) can enter the universe purely because of post-cut-off trading, even though its cut-off-time price history may be thin.
- The signal itself (strength, direction) is still computed causally from prefix-only prices, so this is a **universe-selection bias**, not a look-ahead in scoring. But it is understated in the code's own limitations text, which calls it a "mild survivorship effect."

### 2. Is the close date the CURRENT close date, or the one known at the cut-off?

**CONFIRMED as an unverified assumption, with corroborating evidence it can be wrong.**

- `historical.py:48`: `end_date: datetime | None = None   # the market's scheduled close (set at creation; causal)`.
- `historical.py:177`: `close_at = cand.end_date`, and `cand.end_date` is populated at `historical.py:372` from `m.end_date`, which is `active_markets()`'s **current** fetch of Gamma's `endDate` (`normalize.py:294-296`, parsed fresh from `raw.get("endDate")` on every discovery call).
- Gamma's `endDate` is not asserted immutable anywhere in the client/normalize layer, and the repo's own consistency checker (`analytics/consistency.py:33-40`, `check_close_state`) exists specifically because **end dates on active markets have been observed in the past** (baseline doc records "6 consistency warnings... past end dates on active markets; title/date year mismatches", `signal-replay-functional-baseline.md:49`). This is direct evidence that Gamma's `endDate` field is not perfectly stable/reliable metadata.
- Net effect: `close_at`/`time_remaining_hours` in a reconstructed entry reflect **today's** value of `endDate`, presented as if it were "known at the cut-off." If Polymarket/Gamma extended or corrected a market's close date after the reconstructed cut-off, the reconstructed screen would silently show the wrong close/remaining-time for that historical moment. This is a genuine, if likely low-frequency, point-in-time integrity gap — not causal by construction the way price is.

### 3. Is any current order book / liquidity / wallet state used in historical eligibility or scoring?

**REFUTED — no leak found.** `historical.py:159` passes `book=None` into `compute_token_analytics`, and `historical.py:171` calls `score_opportunity(sig, [], liquidity=None, relative_spread=None, data_age_seconds=None, now=as_of)`. Trades list is `[]`, liquidity is `None`, relative spread is `None`. Eligibility (`near_mid` gate) is applied to `entry = prices[-1]` from the pre-cut-off prefix only (`historical.py:143-151`), never today's price. This part of the system is causal and honest as documented.

### 4. Is the reconstructed cut-off reproducible/frozen, or does it recompute live each refresh?

**CONFIRMED non-reproducible.** `api/routes/historical.py:30`: `as_of = datetime.now(UTC) - timedelta(days=days)`. There is no caching (only `functools.lru_cache` on service/singleton construction in `api/deps.py`, not on this endpoint), no persistence of the computed `as_of`, and the candidate universe/price history are fetched fresh from live sources on every call. Two calls to `GET /api/historical/screen?days=7` made minutes apart use two different `as_of` instants; calls a day apart shift the whole window and the whole candidate universe (which itself is today's-active-list, per Check 1). `docs/replay-report-reconciliation.md` §2.2 independently documents this — different runs "at different universe sizes on different days" produced 0/2, 1/2, 2/3, 3/5 — none of which is reproducible or citable as a fixed result. Spec §16's requirement for a frozen, reproducible cut-off is not met by this endpoint; only the prospective `WeeklyCohortRow.frozen`/`cutoff_at` path (`models.py:86-99`, `engine.py:175-195`) actually freezes anything.

### 5. Are prospective cohorts actually being frozen, or is the store empty?

**CONFIRMED empty**, consistent with the baseline. `docs/signal-replay-functional-baseline.md:130-144` records 0 prospective cohorts, 1 synthetic cohort. Code-level confirmation: `update_rankings`/`freeze_week`/`collect_forward_prices`/`record_resolutions`/`evaluate_all` are only invoked from `evaluation/cli.py` (manual `python -m astrolabe.evaluation.cli rank|freeze|...`) and `evaluation/seed.py` (the synthetic demo). No in-process scheduler (`grep` for APScheduler/cron found nothing) drives them; `cli.py`'s own docstring defers to "docs/deployment.md for scheduler setup (e.g. GitHub Actions / provider cron)" — i.e. an external cron this repo cannot verify is running. The synthetic cohort (`seed.py`) is correctly isolated: `provenance_class=PROVENANCE_SYNTHETIC`, and `CohortReadService.provenance()` (`service.py:82-105`) and `cohort_detail()` (per ISO week) never aggregate across provenance classes, so the synthetic demo cannot silently pollute a "real performance" number. No aggregate-across-cohorts endpoint exists that mixes provenance classes.

---

## Findings (severity-ranked)

1. **HIGH — Reconstructed cut-off is not frozen or reproducible.**
   `backend/astrolabe/api/routes/historical.py:30`. `as_of = datetime.now(UTC) - timedelta(days=days)` recomputes on every request against wall-clock now, and the candidate universe/history are re-fetched live each time. Any two calls, or the same `days` value on different days, produce different, non-comparable samples — undermining any claim of a stable, citable Replay result (spec §16).
   *Fix:* accept an explicit `as_of` timestamp (or persist/cache the resolved `as_of` and universe per day), and/or route "real" performance claims exclusively through the frozen prospective cohort path, which already has the right immutability primitives (`WeeklyCohortRow.frozen`).

2. **HIGH — Candidate universe is selected by TODAY's active-market list and TODAY's 24h volume, not cut-off-time activity; survivorship is a hard exclusion, understated in the docstring.**
   `backend/astrolabe/evaluation/historical.py:358-360` (`by="volume_24hr"`) vs. `backend/astrolabe/service/market_service.py:292-296` (docstring claims sort by total "volume"); root cause `backend/astrolabe/service/sources.py:119-124` (`gamma.list_events(active=True, closed=False)`, current-only). Markets that existed and were reconstructable at the cut-off but have since closed are 100% excluded, not "mildly" affected as the code comment states.
   *Fix:* either correct the docstring to match reality and strengthen the disclosed limitation to say "hard exclusion of anything closed since," or (better) source the universe from a point-in-time market list/cached discovery snapshot near the cut-off rather than today's live discovery.

3. **MEDIUM — Close date (and title/category/other metadata) used in the reconstructed screen is today's Gamma value, asserted but not verified to equal the value at the cut-off.**
   `backend/astrolabe/evaluation/historical.py:48,177,372`; sourced via `backend/astrolabe/ingest/normalize.py:294-296`. The repo's own `check_close_state`/`check_title_end_year` (`backend/astrolabe/analytics/consistency.py:33-58`) exist because Gamma `endDate`/title-year mismatches have actually been observed (baseline: 6 consistency warnings). The comment "set at creation; causal" is not backed by any check that the value hasn't changed since.
   *Fix:* either persist `end_date` at candidate-discovery time (so at least the value is contemporaneous with the market being read, not stale across the async gather), or add a disclosed caveat that `close_at`/`time_remaining_hours` reflect current metadata and may not equal the value known at the cut-off.

4. **LOW — Resolution timestamp is poll-time, not event-time.**
   `backend/astrolabe/evaluation/service.py:316-333` stamps `resolved_at=utcnow()` when a resolution is *discovered*, not when Polymarket actually resolved the market. Low practical impact (forward-only tracking, resolution fact itself is correct), but the timestamp field name implies more precision than it has.
   *Fix:* rename/document as `resolution_recorded_at`, or source the true resolution timestamp from Gamma/oracle metadata if available.

5. **CONFIRMED-GOOD (no defect) — No current order book, liquidity, or wallet state leaks into historical eligibility or scoring.**
   `backend/astrolabe/evaluation/historical.py:159,171`: `book=None`, `liquidity=None`, `relative_spread=None`, trades `[]`. The near-mid eligibility gate and signal strength both use only the pre-cut-off price prefix. This part of the system does what its comments claim.

6. **CONFIRMED-GOOD (no defect, matches baseline) — Prospective cohort store is empty; synthetic demo is correctly isolated.**
   No scheduler in this repo drives `update_rankings`/`freeze_week` (only manual CLI / external cron per `evaluation/cli.py` docstring). `PROVENANCE_SYNTHETIC` is never aggregated with `PROVENANCE_PROSPECTIVE` in `evaluation/service.py`'s read paths. This confirms baseline observation 6 at the code level — the gap is operational (nobody has run the scheduler), not a provenance-mixing bug.

Full detail and matrix: `docs/replay-point-in-time-data-matrix.md` (this file).
