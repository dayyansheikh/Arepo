# Agent 2 — Sophisticated prediction-market user

**Overall verdict: genuinely useful as a curated scanner + honest evaluation harness; not (yet) an edge
source, and it doesn't pretend to be.** I would revisit it to triage short-horizon markets.

## Within 10 seconds (Opportunities screenshot)
- Yes: I immediately see a ranked shortlist with **direction (Down), strength bar (17/100), time-to-close
  (Closes 4d/1h/3h), and a plain reason** ("Strength 17, up 1 point over the last hour. Direction
  unchanged for 2 consecutive scans") plus evidence chips (Order-book pressure, Trade timing, Trade
  activity) and a Priority badge. The denominator line is honest: "20 opportunities shown from 974
  directional signals across 1382 eligible markets." Strong.
- The "Out of date · updated 34 hours ago / Live refresh is delayed" banner is honest about staleness —
  a real user trusts that.

## Curation & usefulness
- **Opportunities is meaningfully curated:** top-20 of 974 directional by Research Priority then strength,
  scoped to a closing window. That is a real triage aid vs scrolling raw Polymarket.
- **Signal Lab** exposes the full directional surface with filters (closing universe, signals shown) and
  progressive "Details" — useful for going deeper.
- **Replay** actually answers the key question per cohort ("6-hour performance: 16 expected / 13 against /
  1 no change / 50 pending", "55% of markets that moved went in Arepo's recorded direction") and lets me
  compare **Opportunities vs All signals vs Research comparison** scope. This is the differentiator: an
  honest scoreboard of its own past calls.

## Weaknesses
| Sev | Finding | Fix |
|--|--|--|
| Medium | Evidence chips ("Trade timing", "Trade activity") are **generic** — I can't tell *how strong* each factor was or which drove the rank | Add a compact per-factor magnitude (already in Details for Signal Lab; surface a one-line "top driver" on the card) |
| Medium | No **at-a-glance long-term "selected vs wider" scoreboard** — Replay is per-cohort, so I can't yet see whether selection beats the wider set *over time* | Build the long-term aggregate summary (spec §7); this is the single highest-value addition |
| Low | 1h/6h Replay shows many "Unavailable" — reads as gaps | Show a one-line "why unavailable" (market closed / no near-term quote) |

## Would I revisit?
Yes, as a **short-horizon triage tool** — it surfaces order-book/trade-flow context faster than the raw
market page and keeps an honest track record. I would not treat any signal as a trade recommendation,
which the product explicitly tells me not to.

**Single highest-value improvement:** the long-term, market-deduplicated **"do selected Opportunities
outperform the wider directional set?"** scoreboard. That is the whole thesis and it deserves a durable,
honest home. **Conclusion: ship-with-fixes.**
