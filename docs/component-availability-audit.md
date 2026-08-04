# Component availability audit (spec §9)

End-to-end trace of the three components the user repeatedly saw missing, why they were missing,
what was fixed, and how to verify.

## The three components
| Display name | Internal id | Evidence family |
| --- | --- | --- |
| Faster trading activity | `volume_acceleration` | trade activity |
| Spread change | `spread_change` | order book |
| Available depth change | `depth_change` | order book |

## End-to-end trace (before the fix)
| Stage | Finding |
| --- | --- |
| Source endpoint | CLOB `/prices-history` returns `{t, p}` only (no volume); Gamma exposes cumulative `volume`/`volume24hr` scalars; CLOB `/book` returns a single current snapshot |
| Collector | `ingest/microstructure_store.py` (added last pass) records `(spread, near_mid_depth, cumulative_volume)` per token, idempotent per minute |
| Persistence | `microstructure_snapshots` table (registered in the idempotent bootstrap) |
| Calculation | `analytics/microstructure_changes.py` computes each change from the prior series (returns `None`, never `0`, when the series is too short) |
| **Live model wiring** | **BROKEN: `compute_token_analytics` was never passed `changes`** on the live/cached path, so `RawComponents.spread_change/depth_change/volume_acceleration` were always `None`. Baseline: **0/40 tokens** had any of the three. |
| Opportunity Board / Market Detail / Signal Lab | all showed the components as empty (a bare dash) |
| Replay | correctly price-only; these components are not reconstructed historically (no historical order books) |

Also confirmed: `LiveSource`/`CachedSource` still hardcode `volumes=[]`, so the old in-frame
`_volume_acceleration` path can never fire on live; the series-based path is now the source of
truth.

## Fix (this pass)
1. **Live wiring (§9.4/§9.5).** `MarketService._enrich_market` now records the current snapshot
   (idempotent per minute) and reads the prior series via `changes_for_token`, passing the
   resulting `MicrostructureChanges` into `compute_token_analytics`. One session per market
   (concurrency-safe across markets); best-effort so a storage hiccup never breaks enrichment; the
   current reading is excluded from its own baseline. **After:** once a series accumulates, ~12/16
   live tokens carry a microstructure change (was 0).
2. **Missing stays missing, never zero (§9.6).** `changes_for_token` returns `None` for a
   component until `MIN_BASELINE_SNAPSHOTS` prior snapshots exist; a single snapshot cannot produce
   a change; recording is idempotent per minute; spread and depth come from the same book snapshot
   so their timestamps are comparable.
3. **Confidence penalty (§8/§9).** `reliability_confidence` now scales down with the fraction of
   these components present, so a reading built on incomplete microstructure history cannot show
   full confidence.
4. **Honest UI reason (§9.8/§9.9).** The Signal Lab component table shows an explicit reason in
   place of a dash: "Not enough volume history yet" / "Needs at least two order-book snapshots".
5. **Diagnostic route (§9.7).** `GET /api/opportunity/diagnostics` reports, over the current
   universe: directional coverage, confidence distribution, family-count distribution and
   per-component present/missing counts with the reason. Covered by
   `test_opportunity_diagnostics_replay`.
6. **Composite-contribution test (§9.10).** `test_microstructure_changes.py` proves each of the
   three components moves the composite score when a valid value is present.

## Collection: does it run?
- **Locally:** the enrich path records a snapshot every time a market is looked at (idempotent per
  minute), so a series builds from normal usage; `python -m astrolabe.ingest.microstructure_cli
  collect --mode live` records on demand.
- **Production:** `render.yaml` runs `microstructure_cli collect` every 5 minutes (UTC), so the
  series accumulates independently of any browser or laptop.

## Verify
```
# Availability + confidence + coverage over the live universe:
curl "$API/api/opportunity/diagnostics?mode=live&universe=60"
# Force a few collections a minute apart, then re-check: present counts rise.
python -m astrolabe.ingest.microstructure_cli collect --mode live
```

## Honest limitation
For a **historical cut-off** these components remain unavailable (no historical order-book series
exists), and Replay labels them so; they are never reconstructed from current books. They are a
**prospective** signal that strengthens as the collector runs forward in time. None of the three
was removed, because each can now demonstrably contribute once its series exists (§9.10, §9.11).
