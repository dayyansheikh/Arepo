# AREPO — Plain-English Progress

**Last updated:** 2026-10-11 10:38 UTC+1
**Current phase:** **Phase 3 closed**, with its last gap fixed this morning. **Phase 4 is in progress.**
**Overall status:** On track. No decisions needed from you.
**Current objective:** Finish the 24-hour forecasting test (E004/E005/E006, results tonight) and decide whether order flow earns a registered experiment.

## 1. Where we are
AREPO asks whether information knowable *before* a prediction helps forecast Polymarket price moves better than the
current price and recent momentum.
- **Research machinery:** complete and proven live.
  - The full pipeline passed its final test (D116).
  - The one missing piece, matched "control" comparison markets, worked live this morning (D118 **PASS**).
- **Forecasting:** one confirmed short-term pattern (price reversal), which is not tradable as it stands. More tests finish tonight.

## 2. What changed since the last update
- **D118 PASSED (09:22–09:36 UTC).**
  - 12 markets went end to end, all of them complete.
  - Two triggered markets were each matched with a comparison market, and both pairs completed.
  - There were zero engineering problems, and timing was well inside the safety limits (26 s against 40 s).
  - An independent review accepted it.
- **How we got there:**
  - an Opus max-effort diagnosis;
  - a Fable 5.1 review that corrected over-optimistic odds;
  - a rehearsal that **rejected** the first design before launch (it would have run too slow);
  - a smaller redesign;
  - two Opus reviews, then the freeze.
- **Honest scope:** this proves the comparison *mechanism* works, on markets with at least $1,000 liquidity.
  - One of the two pairs was almost certainly sibling markets (Knicks vs Thunder playoff odds), so it isn't an independent comparison.
  - 5 of 7 triggered markets found no comparison partner. It works, but not reliably enough yet to measure effects.
- **Order flow lead weakened.** In the latest trade-active sample it mostly turned negative. One more sample decides it.

## 3. What AREPO can actually do today
- Run its full research pipeline live, including matched comparisons, in about 14–24 minutes.
- Snapshot all of Polymarket every 2 hours and log forecasts before outcomes.
- Sample order books and trades fairly.
- Run leakage-safe, fully logged experiments with power calculations.
- Back up all research data to a private, checksum-verified GitHub archive.

## 4. Experiment scoreboard
| | Status |
|---|---|
| E002 reversal | **Confirmed (exploratory)**: about 21% of the last-hour move reverses within about 5h; not shown tradable |
| E003 order-book imbalance | No value at about 2 min (a useful negative) |
| E004/E005/E006 | Collecting, 5 of 12 snapshots; results about 23:00 UTC+1 tonight |
| Order flow (development) | Lead weakened; one more sample decides whether it becomes E007 |

## 5. Issues and risks
| Issue | Why it matters | Blocks? | Action |
|---|---|---|---|
| Disk 14 GiB free (D118 added about 3 GB) | Fine for collection | No | The local backup copy (2.9 GB, safe on GitHub) could be removed with your OK if needed |
| Comparison markets are often unavailable | Limits future trigger-vs-control studies | No | Any such study must be designed around it |
| Reversal may be quote noise | It may not be usable | No | E004's spread-crossing test |

## 6. Decisions I need from you
**None. Autonomous work is continuing.**

## 7. What's next
1. Collection passes every 2h; E004/E005/E006 scored tonight.
2. Decide on order flow (E007) after the next trade-active sample.
3. Lock the Phase 4 baselines formally and plan the next experiment families.

## 8. Scientific reality check
- **Demonstrated:** the full, honest data machinery works live, comparisons included; one forecasting pattern held on unseen data.
- **Unproven:** tradability, stability over many days, and any signal beyond the reversal.
- **Validated edge beyond momentum:** **none yet.**

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [D118 addendum](implementation/d118/D118_ADDENDUM.md)
