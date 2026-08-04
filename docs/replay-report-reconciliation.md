# Replay report reconciliation (spec §2)

Resolves the inconsistencies between the original specification and the previous final report.

## §2.1 Baselines: what changed and what was missing

**Originally requested:** no-change, current implied probability, price-only, momentum,
order-book-only (where historical data genuinely exists).

**Previous report listed:** no-change, momentum, always-up, always-down.

**Explanation of the difference.** The previous pass shipped the four simplest directional
baselines and added the two naive references (always-up / always-down) but did not implement
current-implied or price-only, and did not explain the order-book-only omission. That was an
undisclosed gap.

**Now implemented (this pass), all causally valid at the cut-off:**
| Baseline | Rule (uses only cut-off information) | Status |
| --- | --- | --- |
| No change | predicts flat; correct when the real 24h move is within 0.01 | present |
| Current implied | up if entry implied probability > 0.5, else down (favourite-drift) | **added** |
| Price only | sign of the trailing lookback trend (entry vs the start of the lookback) | **added** |
| Momentum | sign of the short trailing pre-cut-off move | present |
| Always up / Always down | naive references | present |

**Order-book-only: not implementable, and why.** It requires a **historical order book** at the
cut-off. Polymarket's public API exposes only the *current* order book; historical books were never
stored by Arepo (or by Polymarket for retrieval). So the exact input is unavailable, cannot be
recovered retrospectively, and can only be collected **prospectively** going forward. A partial
version built from current books would be look-ahead and misleading, so it is deliberately omitted
rather than faked. (Confirmed in `docs/component-availability-audit.md`.)

## §2.2 Replay-result reconciliation (canonical table)

The previously reported "1/2 at -7d", "0/1 at -14d" and "Arepo 3/5" were **different runs at
different universe sizes on different days**, not one dataset. Canonical run (universe 80, top 5,
cut-off relative to 2026-08-04, 24h horizon):

| Cut-off | Timestamp (UTC) | Candidates | Had price data | Eligible | Directional | Selected | Arepo correct | Verdict |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| -1 day | 2026-08-03 | 160 | 160 | 3 | 3 | 3 | 2 / 3 | inconclusive |
| -3 days | 2026-08-01 | 160 | 160 | 2 | 2 | 2 | 0 / 2 | inconclusive |
| -7 days | 2026-07-28 | 160 | 160 | 7 | 7 | 5 | 3 / 5 | inconclusive |
| -14 days | 2026-07-21 | 160 | 160 | 2 | 2 | 2 | 1 / 2 | inconclusive |
| -30 days | 2026-07-05 | 160 | 160 | 0 | 0 | 0 | 0 / 0 | inconclusive |

**Why the figures are not contradictory.** The number of eligible markets swings between 0 and 7
depending on how many currently-discoverable markets had usable, moving price history before that
cut-off. Each cut-off is a **separate, tiny sample**, so hit rates of 0/2, 1/2, 2/3 and 3/5 are all
statistical noise (a Wilson 95% interval on 2-5 Bernoulli trials spans almost all of 0-100%). The
"3/5" and "0/1" are both **inconclusive**, so neither is evidence and neither contradicts the other.
The 24h horizon is fixed across all rows. Confidence in every row is the reduced, price-only
historical confidence (~0.30), not current confidence.

## §2.3 Component availability (separated numbers)

The vague "0/40 to ~12/16" is replaced by an explicit report:

| Item | Value |
| --- | --- |
| Markets/tokens inspected (live) | 40 tokens at baseline |
| Faster-trading-activity (volume acceleration) available | **0 before wiring; rises as the collector runs** |
| Spread-change available | **0 before wiring; rises as the collector runs** |
| Depth-change available | **0 before wiring; rises as the collector runs** |
| Snapshots required before a change can be computed | at least 2 (a single snapshot cannot produce a change) |
| Snapshot interval (production cron) | every 5 minutes (UTC) |
| Time before first calculation | a few minutes once the collector is running |
| Stale-data threshold | 60 s (data older is flagged; a stale snapshot is not used) |

Once collected, valid values influence the composite score (proven by
`test_microstructure_changes.py`), and therefore the **Opportunity Board**, **Market Detail**,
**Signal Lab**, **confidence** (a reading with missing components is penalised) and **Research
Priority** (which scales with the composite). See `docs/component-availability-audit.md`. Historical
reconstruction is price-only, so these three are unavailable at a past cut-off and labelled so.

## §2.4 Edge wording audit

No page, alert, methodology section, README, portfolio report or status document claims a
demonstrated predictive edge. The defensible conclusion, stated consistently:

- the sample is small;
- historical results are inconclusive;
- Arepo has not yet outperformed the tested baselines (on the current sample its hit rate matches
  momentum and always-down);
- the prospective evaluation framework exists to gather stronger evidence over time.

The Replay UI shows an explicit **Inconclusive** banner and a baseline table whenever the sample is
below the meaningful minimum, and Research Priority is labelled a heuristic, not expected profit.
