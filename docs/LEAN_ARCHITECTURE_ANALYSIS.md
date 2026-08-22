# Arepo Lean Research Architecture — Quantification & Cadence Decision

Status: **analysis + design** on `codex/lean-research-architecture` (build-now / deploy-later, §14).
Date anchor: 2026-08-22. All figures marked *(measured)* come from production this session;
*(est.)* are derived from the ORM schema + measured growth and carry real error bars (exact
per-table bytes require a DB size query — see "Measurement gap" below).

## 0. What is already done (do not repeat)

- **Automatic deep scans PAUSED** in production (PR #12, `e50f063`): the heavy `arepo-scan`
  schedule is removed; `workflow_dispatch` retained; `collect`/`digest` still scheduled so
  already-frozen cohorts finish their forward horizons. This stops the growth described below.
- Deployed egress/stability fixes (prior turns): backup daily→weekly, scan market-cache read
  id-only + bulk write, `pool_pre_ping`, in-process Explore cache (the last is explicitly
  superseded by §12 — see "Render memory" below).

## 1. Measured production state

| Metric | Value |
|---|---|
| DB size *(measured)* | **935 MB** / 500 MB Free limit (187%, `critical`) |
| Growth, recent *(measured 6 h, Aug 22)* | ~132 MB/day |
| Growth, 7-day avg *(measured)* | ~80 MB/day (accelerating as the universe grew) |
| Egress, billing cycle *(user-reported)* | 20.26 GB / 5.5 GB |
| Latest deep scan *(measured)* | 3,708 analysed / 2,546 directional; complete discovery (union 121,897) |
| Universe growth | ~900 → ~3,708 analysed after the scan-stability fixes (~4×) |

The universe quadrupling is the root inflator: every scan/cohort now writes ~4× more, and the
deep scan ran **~48×/day** (every 30 min), so snapshot churn dominates.

## 2. Cadence comparison (§2)

Deep-scan cadence and forward-collection cadence are **independent** and must stay so (§1C).

| Item | Current (6h / ~48 scans/day) | Proposed (2 deep scans/day, 00:00 & 12:00 UTC) |
|---|---|---|
| Deep scans/day | ~48 (30-min, due-gated) | **2** |
| Frozen cohorts/day | 4 (00/06/12/18) | **2** (00/12) |
| Snapshot generation/day *(est.)* | ~460 MB/day churn | ~19 MB/day (**~24× less**) |
| Snapshot steady (2-day retention) *(est.)* | ~900 MB bounded | ~39 MB bounded |
| Permanent research/day *(est.)* | ~45 MB/day | ~23 MB/day (**~½**) |
| Unique markets/events per scan | ~3,708 / ~event-count | **unchanged** — coverage per scan is not reduced |
| Independent training examples | inflated by 4× repeated near-duplicate 6h snapshots | fewer rows, **far less correlated** (§ "prefer fewer, cleaner, distinct") |
| Compute/runtime/day | ~48 × ~19 min | 2 × ~19 min (**~24× less**) |

**The 24× snapshot-churn reduction is the single biggest lever** and is almost certainly the bulk
of both the storage growth and the egress overage (a 2-day snapshot window at 48 scans/day of a
3,708-market universe is the largest object in the DB).

## 3. Do the outcome labels survive 2 deep scans/day? (§26)

**Yes.** Outcome labels (1h/6h/24h/7d/pre-close) depend on **forward-collection** frequency, not
scan frequency. With freezes at 00:00 and 12:00 UTC, `collect` (unchanged, ~15-min cadence) still
records each cohort's readings at frozen_at+1h/+6h/+24h/+7d. Every frozen signal still gets its full
horizon set. No label is lost by scanning twice a day instead of forty-eight times.

## 4. ML sample size (§2, §22)

- 2 cohorts/day × ~2,546 directional = ~5,092 directional signals/day, ~unique per market.
- The old 6h/30-min cadence produced thousands of **repeated snapshots of the same market** hours
  apart — highly correlated, low marginal information. The prompt explicitly prefers *fewer, cleaner,
  genuinely distinct* observations. Two daily snapshots (12 h apart, spanning distinct intraday
  regimes) retain most of the independent signal while cutting correlated bulk.
- Time to meaningful new prospective ML evidence: at ~5k directional signals/day with full
  horizons completing over 7 days, a few weeks yields ~10⁵ labelled directional rows across
  thousands of unique markets — sufficient for the shadow logistic/tree models with grouped CV.

## 5. Steady-state storage projection under the lean architecture (§10)

Assumptions *(est.)*: entry ~2.2 KB, forward obs ~0.3 KB, snapshot ~2.6 KB, compact ML row ~0.45 KB
(~80% smaller than a detailed entry+forward set), 14-day full-detail retention, 2 cohorts/day.

| Component | Size |
|---|---|
| 14-day detailed working set | ~318 MB |
| Snapshots (2-day, 2 scans/day) | ~39 MB |
| Base (users, market index, scan_runs, misc) | ~60 MB |
| Compact archive (>14 days) | grows ~3.3 MB/day |

Projected total: **day 30 ~470 MB · day 90 ~670 MB · day 365 ~1.6 GB.**

**Conclusion:** 2 deep scans/day + 14-day retention + compaction brings the *active* working set to
~420–470 MB and makes Free *viable for roughly the first ~5–6 weeks*, but the ever-growing compact
archive still crosses 500 MB. True multi-month steady-state on 500 MB Free additionally needs one of:
(a) a tighter compact schema (~200 B/row, **directional-only** — abstentions have little ML value),
(b) cold archival of >90-day compact rows to R2/local (archive-before-delete), or (c) accepting
~1 year of hot history and cold-archiving beyond. This directly feeds the §25 infra recommendation.

## 6. Measurement gap (honest limitation)

Exact per-table bytes require `pg_total_relation_size` per table, which needs a DB connection /
credentials I do not hold and must not handle. The byte figures above are schema-derived estimates
with wide error bars; the **qualitative** conclusions (snapshot churn dominates; 24× cadence win;
labels survive; compaction needed for the permanent tail) are robust regardless.

**Next concrete step (buildable, safe):** add a read-only table-size breakdown to the tick health
snapshot (`SELECT relname, pg_total_relation_size(...)`), so the very next `status` run reports the
real per-table sizes and replaces these estimates with measurements before any compaction runs.

## 7. Cadence decision (§26 summary)

- Old deep-scan frequency: ~48/day (30-min), 4 frozen cohorts/day.
- New: **2 deep scans/day at 00:00 & 12:00 UTC, 2 frozen cohorts/day.**
- Rationale: ~24× less snapshot churn + ~½ permanent data, unchanged per-scan coverage and unique
  markets, negligible ML loss (removes correlated repeats), labels fully preserved via unchanged
  forward collection.
- Prospective only (§3): recorded via a new `coverage_policy_version` / `scan_cadence` on cohorts
  frozen *after* the change. **Old cohorts are never rewritten** to pretend they used the new cadence.
