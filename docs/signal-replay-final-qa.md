# Signal Lab / Replay — Independent Final QA (Agent G)

Date: 2026-08-04. Backend tested live at http://127.0.0.1:8012.

## What was tested
- `GET /api/signals?limit=25` (15 signals returned)
- `GET /api/opportunity/board?view=directional&top=30` (21 cards)
- `GET /api/opportunity/diagnostics`
- `GET /api/historical/screen?days=7&limit=80&top_n=10` (9.4s, well under 180s budget)
- `GET /api/replay/data-status`
- `GET /api/cohorts/latest`, `GET /api/cohorts/weeks`
- Skimmed `frontend/app/signals/page.tsx`, `frontend/app/replay/page.tsx`, `frontend/components/SignalItem.tsx`, and the scoring source (`astrolabe/opportunity/scoring.py`, `astrolabe/evaluation/replay_stats.py`) to check claims against implementation.

## Findings by area

**1. Confidence — PASS, with a naming trap.** The raw `confidence` field on a signal *does* read 1.0 for 13/15 signals in `/api/signals` — that field is a pure data-quality/completeness term, not the displayed reliability. Every signal also carries `reliability_confidence` (0.45–0.82, never 1.0), and `SignalItem.tsx:124` correctly renders `reliability_confidence ?? confidence`, so the UI never shows 100%. `reliability_confidence` scales sensibly with `n_families` (0→0.45, 1→0.60–0.63, 2→0.82) and with the raw confidence term. Cross-checking the 7 markets shared between Signal Lab and the Board: `signal_strength` matches exactly, but confidence differs for 3 of 7 (board higher, since it adds trade-flow families) — this is intentional and documented in code (spec §17) but nowhere explained in the UI itself; a user diffing the two screens for the same market could reasonably flag it as inconsistent. Minor concern.

**2. Replay honesty — PASS.** `/api/historical/screen` cleanly separates correct/incorrect/flat/pending (3/1/3/0 of 7 selected); flats are excluded from the hit-rate denominator by construction (`classify_directional`, `FLAT_EPS=0.01`) and never counted as a miss. `plain_summary` text matches the counts exactly. `sample_verdict: "inconclusive"` is set (n=4 < MIN_MEANINGFUL_SAMPLE=20) and the frontend surfaces this with an explicit "too small to be evidence of skill" banner.

**3. Baselines — PASS.** Arepo and 4 of 5 baselines (current_implied, price_only, momentum, always_up/down) are scored on the identical n=4 sample with the same 3 flats excluded. The `no_change` baseline is scored differently by design (n=7, 0 flats) because it predicts flatness itself — this is a coherent, well-commented design choice, not an asymmetry bug, though the top-level `baseline_comparison.sample_size: 4` could be misread as applying uniformly. Frontend explicitly flags "Arepo vs momentum" as near-self-referential (~construction: Arepo's direction is the latest-return z-score sign) — good, undersells rather than oversells the edge. No edge is claimed; frontend states differences are "not statistically meaningful."

**4. Synthetic separation — PASS.** `/api/cohorts/latest` returns HTTP 404 with an explicit message: "No real cohorts recorded yet... only a synthetic demonstration cohort exists so far." It does not serve the synthetic cohort as real. `/api/cohorts/weeks` does list the one synthetic week but labels it `provenance_class: "synthetic"` plainly.

**5. Failures/nonsense — none found.** All 6 endpoints returned 200 (my first pass misread `/api/cohorts/latest`'s intentional 404 as belonging to `/api/replay/data-status`; re-verified individually, data-status is 200). `/api/opportunity/diagnostics` is internally consistent (`pct_eq_100: 0.0`, matches reliability_confidence distribution, not the raw confidence field).

## Defects (severity | where | issue)
1. Minor | Signal Lab vs Opportunity Board | Same market can show different confidence (e.g. market 2850825: 1.0 vs 0.82; 559653: 1.0 vs 0.82) because the board adds trade-flow families. Intentional per code comment (spec §17) but undocumented in either UI — recommend a one-line note on the Board explaining why confidence can exceed Signal Lab's for the same market.
2. Cosmetic | `/api/opportunity/board` tag text | "1133.5 robust standard deviations above this market's median trade size" is technically correct but reads as noise to a non-quant; consider capping/rephrasing for extreme values.

## Verdict: accept-with-minor
