# Signal Lab and Replay functional baseline

Recorded 2026-08-04, at the start of the Signal Intelligence and Replay functional validation
pass, on branch `arepo-signal-replay-functional-validation` (safety tag
`arepo-before-signal-replay-functional-validation`). This is the honest state **before** any
model, selection or evaluation logic is changed. All figures are captured from the running
product in live mode (backend on `127.0.0.1:8012`, real Polymarket upstream).

Gates at baseline: backend **309 tests pass**, ruff clean; frontend **21 vitest pass**, tsc/lint
clean. Working tree clean at the tag.

## How captured

- `GET /api/signals?limit=25` (Signal Lab)
- `GET /api/opportunity/board?view=directional&top=30` (Opportunity Board)
- `GET /api/opportunity/diagnostics` (universe-wide distributions)
- `GET /api/historical/screen?days=7&limit=80&top_n=10` (reconstructed Replay)
- `GET /api/replay/data-status` (collector / cohort status)

Raw JSON archived under the session scratchpad (`baseline_*.json`).

---

## Signal Lab baseline

From `/api/signals` (live) and `/api/opportunity/diagnostics` (60-market universe).

| Field | Value |
| --- | --- |
| Total signals returned (Signal Lab) | 15 (one per market, strongest outcome) |
| Signal kinds | all `composite_anomaly` |
| Directional signals (up/down) | 6 of 15 (3 up, 3 down) |
| Non-directional (direction = None) | 9 of 15 |
| Duplicate binary complements | 0 (consolidated to one signal per market) |
| Signal strength min / median / max | 0.04 / 0.12 / 0.41 |
| **Confidence min / median / max (Signal Lab)** | **1.00 / 1.00 / 1.00** |
| Data-quality band | all `good` |
| Universe screened (diagnostics) | 60 markets, 120 tokens |
| Directional coverage (diagnostics) | 27 / 60 = 45.0% |
| Confidence min/median/mean/p90/max (Board reliability) | 0.004 / 0.42 / 0.398 / 0.761 / 0.762 |
| Confidence == 100% (Board reliability) | 0.0% |
| Confidence > 90% (Board reliability) | 0.0% |
| Family-count distribution (diagnostics) | 0 fam: 21, 1 fam: 29, 2 fam: 10 |
| Research Priority distribution (Board) | min 0, median 16, max 78 |
| Board family distribution | 2 fam: 14, 3 fam: 7 |
| Component availability: spread_change | 80/120 present (66.7%) |
| Component availability: depth_change | 72/120 present (60.0%) |
| Component availability: volume_acceleration | **0/120 present (0.0%)** |
| Consistency warnings (diagnostics) | 6 (past end dates on active markets; title/date year mismatches) |

### Baseline observations (recorded, not yet fixed)

1. **Confidence is reported two different ways for the same signal.** Signal Lab
   (`/api/signals`) returns the raw data-quality term (`signal.confidence` from
   `assess_quality`), which is **1.00 for every good-data signal**. The Opportunity Board and
   Market Detail instead show the *reliability* confidence
   (`reliability_confidence(dq, n_families, completeness)`), which ranges 0.004–0.762 for the
   same universe. This is a cross-surface inconsistency (spec §17) and a direct §6 concern
   ("do not display 100% unless the implementation can defend what 100% means"). The reliability
   confidence is the defensible number and should be used on every surface.

2. **`volume_acceleration` is wired but never present (0/120).** It requires a persisted volume
   series the live path does not build, so it contributes nothing to the live model and is
   permanently missing. Candidate for honest removal/disable per spec §4.

3. Signal Lab confidence field carries no reliability signal (all 1.00), so a user cannot tell a
   one-family, thin-data lead from a three-family, rich-data one on the Signal Lab surface.

---

## Replay baseline

### Reconstructed Replay, cut-off = 7 days ago (`days=7`, `limit=80`, `top_n=10`)

| Field | Value |
| --- | --- |
| Provenance | `reconstructed` |
| Cut-off (`as_of`) | 2026-07-28T17:35Z |
| Universe considered (had usable price data) | 160 |
| Candidates total | 160 |
| Had price data | 160 |
| **Eligible** | **4** |
| Directional | 4 |
| **Selected** | **4** |
| moved_expected_24h | 0 |
| moved_against_24h | **4** |
| pending_24h | 0 |
| Sample verdict | inconclusive |

Per-entry 24h outcome:

| Rank | dir | momentum | strength | conf | RP | 24h move | correct? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | down | down | 0.51 | 0.30 | 11 | +0.055 | False (genuine miss) |
| 2 | up | up | 0.27 | 0.30 | 8 | −0.040 | False (genuine miss) |
| 3 | up | down | 0.27 | 0.30 | 7 | **0.000** | False (**flat, mis-counted**) |
| 4 | up | down | 0.12 | 0.30 | 6 | **0.000** | False (**flat, mis-counted**) |

### Baseline comparison over the selected top-4 (24h forward direction)

| Predictor | correct / evaluated | hit rate |
| --- | --- | --- |
| Arepo | 0 / 4 | 0.00 |
| No change | 2 / 4 | 0.50 |
| Current implied | 2 / 4 | 0.50 |
| Price only | 1 / 4 | 0.25 |
| Momentum | 0 / 4 | 0.00 |
| Always up | 1 / 4 | 0.25 |
| Always down | 1 / 4 | 0.25 |

All verdicts `inconclusive` (n = 4, below the 20-market meaningful floor). Wilson CI on Arepo:
[0.00, 0.49].

### Baseline observations (recorded, not yet fixed)

4. **Flat forward moves are counted as directional misses.** `direction_correct_24h` in
   `historical.py` and `_correct` in `replay_stats.py` compute `(move > 0)` / `(move < 0)`, so a
   move of exactly 0.0 is scored **incorrect** for any directional call. Ranks 3 and 4 above
   moved exactly 0.000 over 24h yet are counted in `moved_against_24h`. Meanwhile the no-change
   baseline treats `|move| <= FLAT_EPS (0.01)` as **correct**. This asymmetry is the dominant
   driver of the headline "Arepo 0/4 vs no-change 2/4": two of the four Arepo "misses" are flat
   markets that no-change scores as wins. There is no `flat` bucket in `HistoricalScreen`, which
   spec §10/§11 require (separate correct / incorrect / flat, with a predeclared move rule).

5. **Thin eligibility funnel.** 160 candidates → 4 eligible (2.5%). The near-mid gate
   (0.1–0.9 at the cut-off) plus `min_history 30` plus `min_strength 0.12` filter heavily. This
   is a genuine data limitation (documented in the screen's limitations), not itself a defect,
   but it means every reconstructed cut-off is an inconclusive micro-sample.

### Replay data-status

| Field | Value |
| --- | --- |
| Microstructure snapshots stored | 493 |
| Last collection at | 2026-08-04T17:35Z (14s ago) |
| Collector recent | true |
| Weekly cohorts total | 1 |
| **Prospective cohorts** | **0** |
| Oldest / newest cut-off | 2026-07-12 / 2026-07-12 (the single synthetic demo cohort) |

Observation 6: there are **zero prospective cohorts**. The only stored cohort is the labelled
synthetic demo. The prospective performance record (the strongest evidence mode, spec §8) has
not begun accumulating because `cli rank --mode live` has never been run to freeze a real
weekly cohort.

---

## Summary of confirmed baseline issues to carry into the audit

| # | Area | Issue | Spec |
| --- | --- | --- | --- |
| 1 | Confidence | Signal Lab shows 1.00 data-quality confidence; Board/Detail show reliability confidence for the same signal | §6, §17 |
| 2 | Components | `volume_acceleration` present 0/120 (never contributes) | §4 |
| 3 | Replay eval | Flat 24h moves scored as directional misses; no `flat` bucket; asymmetric with no-change | §10, §11 |
| 4 | Replay growth | Zero prospective cohorts; only a synthetic demo cohort exists | §8, §14 |
| 5 | Replay funnel | 160 → 4 eligible; every reconstructed cut-off is an inconclusive micro-sample (data limitation, disclose) | §9 |

These are recorded before any change. Fixes are decided by the reviewers and Opus synthesis, and
must not be chosen to improve reported performance after seeing outcomes.
