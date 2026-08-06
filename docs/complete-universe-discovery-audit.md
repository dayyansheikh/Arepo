# Complete universe discovery audit (why the cohort contained 60 markets)

_Branch `arepo-complete-short-horizon-universe`. This traces the exact path from upstream Polymarket
discovery to the stored 60-market prospective cohort and proves whether previous discovery was
complete or truncated. It does not change the existing historical 60-market cohort._

## Verdict

**Previous discovery was truncated, not complete.** The number 60 came from a hard-coded page/limit
of 60 applied at three compounding points with **no pagination at all**. The real active universe is
far larger than 60 (see the real funnel below). The public top-ten limit was never the cause; the
cause was upstream discovery being capped at a single 60-item page.

## Exact cause chain (code trace)

The prospective freeze that produced the stored cohort runs, in order:

1. `astrolabe/evaluation/research_cli.py::_freeze` calls
   `screen_universe(service, data_api, now=now)` using the **default** `universe_limit`.
2. `astrolabe/evaluation/research_engine.py::screen_universe(..., universe_limit: int = 60)` calls
   `market_service.enrich_markets(requested_mode="live", limit=universe_limit)` — so `limit=60`.
3. `astrolabe/service/market_service.py::enrich_markets` sorts the markets and then slices
   `subset = subset[:limit]` — a hard **`[:60]` slice**.
4. The markets it slices come from `astrolabe/service/sources.py::LiveSource.markets()`, which calls
   `self._gamma.list_events(limit=self._settings.discovery_limit, active=True, closed=False)`.
5. `astrolabe/config.py::Settings.discovery_limit = 60`, and
   `astrolabe/clients/gamma.py::list_markets` / `list_events` issue **one** HTTP request with that
   `limit` and **never follow any offset or cursor**. There is no pagination loop anywhere in the
   client.

So three independent caps all equal to 60 (`discovery_limit=60`, `screen_universe(universe_limit=60)`,
`enrich_markets`'s `subset[:60]`) sat on top of a **single, unpaginated** upstream page. Whichever
cap you remove, the others still hold the universe at 60. The stored cohort therefore has exactly
60 entries (universe_size 60, 19 directional, 10 public, 9 shadow), which is an artefact of the
`limit=60` single page, not the true short-horizon universe.

### Which category of cause (from the prompt list)

- upstream page size: **yes** (`list_events(limit=60)` = one page of 60).
- a hard-coded `limit`: **yes** (`discovery_limit = 60`).
- a slice such as `[:60]`: **yes** (`enrich_markets` `subset[:limit]` with `limit=60`, and
  `screen_universe(universe_limit=60)`).
- an early pagination stop: **yes, in the strongest form** - there is no pagination loop, so every
  scan stops after page one.
- eligibility / token / close-time / quality / liquidity / category / dedup: **not the cause of 60**.
  Those rules run only over the 60 markets that were fetched; they can only reduce below 60, never
  reveal the markets that were never fetched. The `screen_universe` funnel already records per-market
  exclusions, but only within the truncated 60.
- fixture/demo leak: **no**. The live path is real Gamma; the cap is a real config default.

## Real discovery funnel (measured against live Polymarket, env clock 2026-08-06)

Measured directly against `https://gamma-api.polymarket.com/markets?active=true&closed=false` by
following offset pages until the upstream signalled completion:

| stage | count |
| --- | --- |
| raw records via offset pages (21 pages x 100) | 2100 |
| unique active-open markets reached via offset | 2100 |
| markets with no close time | 170 |
| already-closed by date (0 or negative time remaining) | 107 |
| closing 0-6h | 0 |
| closing 6-24h | 0 |
| closing 1-7d | 73 |
| closing 7-30d | 108 |
| closing after 30 days | 1642 |
| **eligible within 30 days (valid close, >0 and <=30d)** | **181** |

The old code saw at most 60 of these. 181 short-horizon markets is already three times the entire
old cohort, and the true universe is larger still (see next section).

## Upstream pagination reality (important for the fix)

Two upstream facts shape the pagination implementation and are proven by probes:

1. **Gamma `/markets` offset pagination hard-caps at offset 2100.** Requesting `offset >= 2100`
   returns HTTP 422 `{"error":"offset too large, use /markets/keyset for deeper pagination"}`.
2. **The full active universe exceeds the offset cap.** Ordered by `endDate` ascending, the first
   2100 markets are all already-closed-by-date (relative to the 2026-08-06 environment clock);
   ordered by `endDate` descending, the first 2100 are all far-future (>30 days). The 181 within-30d
   markets sit between those two bands, so the complete universe is well over 4000 markets. The
   `/markets/keyset` cursor endpoint returns a `next_cursor` but does not advance on this deployment
   (every documented cursor parameter returns page one again).

Consequence for correctness: the scanner follows **every** offset page until the upstream signals
completion (an empty page) or its documented offset cap. When the cap is reached and the cursor path
cannot advance, the scan is marked **incomplete and degraded and fails loudly** rather than being
presented as a complete universe (prompt sections 2 and 20). A cohort freeze refuses to proceed or
marks itself degraded on an incomplete scan. This is the honest behaviour the prompt requires: never
convert an incomplete scan into a valid-looking cohort.

The environment clock being roughly a year ahead of the live API's real-world state is what fills the
first 2100 offset slots with stale already-closed markets; in a correctly-clocked production
deployment the short-horizon markets sit near the front and are fully reachable. The scanner does not
assume this - it measures and reports pagination completeness every run.

## Fix summary (implemented in this pass)

- Real offset pagination in the Gamma client (`paginate_markets`) that follows every page, records
  page/raw/unique counts and offset progression, detects non-progressing offsets and repeated pages,
  uses bounded retries, enforces an emergency loop cap that **fails loudly**, and marks the scan
  incomplete instead of returning a misleading partial universe.
- A backend 30-day eligibility gate and non-overlapping short-horizon buckets applied **before**
  scoring and public ranking, so ten is only a display limit.
- The complete eligible universe is analysed, ranked per bucket and overall, stored append-only, and
  only the top ten is shown publicly. The existing historical 60-market cohort is left untouched.
