# Dayyan Signal Lab + Replay acceptance (spec §22)

Branch `arepo-signal-replay-functional-validation`. Verified against a running backend (live mode,
:8012) and the production frontend build. No locally testable item is Fail. Gates at acceptance:
**backend 320 tests pass, ruff clean; frontend tsc/lint clean, 21 vitest, `next build` 16/16
routes.**

## Signal Lab

| Item | State | Evidence |
| --- | --- | --- |
| Useful ranked current signals | Pass | `/api/signals` returns 15, one per market, ranked by strength. |
| Directional filter | Pass | Status filter (all / directional / observational), URL-persisted. |
| Observational filter | Pass | Same control; observational = no directional gate. |
| Every sorting option | Pass | Strength ↑/↓, confidence ↑/↓ (now on reliability), recent. |
| Collapsed / expanded detail | Pass | "Why this fired" discloses component breakdown. |
| Market links | Pass | Each card links to `/markets/{id}?mode=live`. |
| Consistency with Market Detail | Pass | Same reliability confidence + directional gate; `test_cross_surface.py`. |
| Confidence explanation | Pass | Reliability = data quality × corroboration × completeness; capped < 100%; MetricHelp updated. |
| Missing-component explanation | Pass | Honest warm-up reasons, never zero. |
| Data freshness | Pass | Status envelope with data age; data-status panel. |
| No duplicate complements | Pass | One signal per market (strongest outcome). |
| **No 100% confidence displayed** | Pass | Signal Lab, Market Detail and Board all ≤ 0.95; live-verified (was 1.00). |

## Replay

| Item | State | Evidence |
| --- | --- | --- |
| Default last-week view | Pass | Reconstructed "last week's opportunities", not synthetic. |
| Each cut-off | Pass | `days` 1–30; snapped to UTC day (reproducible). 3d and 7d verified. |
| Each closing-soon lens | Pass | 24h / 3d / 7d / all, URL-persisted; "closing soon ≠ better" note. |
| Prospective data | Pass (empty) | 0 real cohorts yet; honest empty state + data-status. |
| Reconstructed data | Pass | Point-in-time, price-only, no look-ahead. |
| Synthetic separated / hidden | Pass | Behind a disclosure; `/cohorts/latest` refuses synthetic (404). |
| Top 5–10 selection | Pass | Up to `top_n`; fewer when fewer qualify, funnel shown. |
| Confidence / strength / RP at cut-off | Pass | Per-row, reconstructed; confidence now reliability-at-cut-off. |
| Forward moves | Pass | 1h / 24h / 7d. |
| Resolution outcomes | Pass (where available) | Final price/movement + resolution field; separated from repricing (§11). |
| Baselines | Pass | no-change, current-implied, price-only, momentum, always-up/down; flats symmetric. |
| **Flat handling** | Pass | correct / incorrect / **flat** / pending; flats excluded from hit rate; live-verified. |
| Sample funnel | Pass | candidates → price data → eligible → directional → selected. |
| Data-status panel | Pass | snapshots, cohorts, cut-offs, "open browser doesn't grow the sample". |
| Stable refresh | Pass | Cut-off snapped to UTC day. |
| Correct market links | Pass | Rows link to the historical market context. |
| Momentum-agreement + Brier honesty | Pass | Agreement % shown; Brier/log-loss marked N/A, not fabricated. |

## Failure states

| Item | State | Evidence |
| --- | --- | --- |
| Collector stopped | Pass | data-status shows "no recent collection". |
| No historical data | Pass | Empty state: "No markets had enough real, moving price history…". |
| All pending | Pass | pending bucket + inconclusive banner. |
| Upstream error | Pass | ErrorState surfaced; degradation reason in status. |
| Invalid market | Pass | `/markets/{bad}` → 404 rich error (routing tests, IDs 2694364 + 2822017). |
| Stale data | Pass | Data-age / freshness penalties; labelled, never silently current. |

## Not locally testable (out of scope this pass)

- Manual page-zoom checks at 80–150% (browser tooling cannot set zoom).
- Live deployment (external accounts); code/config ready, not requested this session.
- Accumulating a meaningful prospective sample (requires the backend weekly freeze over weeks).

## Reviewer outcomes

Quant (B), provenance (C), implementation (D), adversarial (F), adversarial re-review (F′) and
independent final QA (G) all completed. G's verdict: **accept-with-minor**; both minors fixed
(Board-vs-Lab confidence now explained; jargon removed). F′ found one incomplete fix (Market Detail
outcome cards) which is now fixed and tested. No critical or major finding remains open.
