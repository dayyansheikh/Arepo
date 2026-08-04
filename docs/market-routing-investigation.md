# Market routing investigation (spec §3)

## Symptom
Searching and opening certain markets showed "Market not found. This market does not exist in the
current mode." The reproduced case occurred with **Replay** selected.

## Reproduced IDs
| ID | Live Gamma status | Question |
| --- | --- | --- |
| `2694364` | active, not closed | Will James Graf win the 2026 Montgomery County race? |
| `2822017` | active, not closed | Putin out as President of Russia by June 30, 2027? |

Both are **valid, active live markets**. So the failure was not an invalid ID.

## Root cause (which of the candidate causes)
**Data-mode resolution failure + Replay-only routing.** Two coupled defects in
`market_service.market_detail`:

1. It resolved the market by scanning **only the selected mode's discovery list**
   (`source.markets()`): `market = next(m for m in markets if m.id == market_id)`. Replay's dataset
   is a small fixed set, so a live market id was never found → 404.
2. Even in **Live** mode, `source.markets()` is the ~60-item discovery page (top active markets by
   volume). Any market outside that page (which most search results are) also 404'd. So the bug was
   broader than Replay: the detail route could not open an arbitrary market by id in any mode.

Not the cause: invalid ID, stale search result, missing cached record. The identifier itself was
correct (a Gamma market id); the resolution contract was wrong.

## Identifier audit (§3.10)
The route uses the **Gamma market id** as the canonical id end to end: search results
(`normalize_events_to_markets` / `normalize_market` set `Market.id` = Gamma id), Opportunity Board
(`market_id`), Signal Lab (`signal.market_id`), market-detail route (`/markets/{id}`), Replay rows,
saved markets and alerts all key on this same Gamma market id. Token ids (`clobTokenIds`) are used
only for per-outcome book/price data, condition ids only for trade-flow. **No identifier mixing was
found**, so a separate canonical-mapping layer (§3.11) was not required; the fix was to resolve the
existing canonical id independently of the interface mode.

## Fix (§3.2, §3.4 option 3, §3.12)
- **Backend canonical resolution.** New `LiveSource.get_market(id)` fetches a single canonical
  market by Gamma id (`gamma /markets/{id}` + `normalize_market`). `market_detail` now falls back to
  it when the id is absent from the selected mode's dataset, loads it against the live source, and
  labels `data_source=live`. It returns 404 **only** when the market exists in no supported source.
- **Frontend source context.** Full-universe search results link with `?mode=live`; the detail page
  reads an explicit `?mode=` from the URL and uses it over the global interface mode (§3.5, §3.6),
  so a live result opens in Live even while Replay is selected. Saved markets and alerts can use the
  same `?mode=` convention.
- **Rich error state (§3.13, §3.14).** If resolution genuinely fails, the page shows a compact card
  with the searched id, the requested mode, and "Open in Live", "Retry" and "Return to search"
  actions - never a large blank page; the footer follows it naturally.

## Verification
- Live: `market_detail("2694364"|"2822017", mode="replay"|"live")` all return the market with
  `data_source=live`.
- Hermetic tests (`tests/unit/test_market_routing.py`, respx-mocked): opens-regardless-of-selected
  mode; genuine-missing → 404; resolves in live/cached/replay.
- Backend 308 pass, ruff clean; frontend tsc/lint/build clean.

## Residual note
`get_market` keeps the `_is_tradeable` filter (needs a two-sided order book, not near-resolved), so
a fully-resolved or book-less market opened directly still 404s with the rich error card rather
than erroring on a book fetch. Search results are already filtered to tradeable markets, so this
does not affect the reported flow.
