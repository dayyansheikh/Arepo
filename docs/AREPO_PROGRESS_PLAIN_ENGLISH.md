# AREPO — Plain-English Progress

**Last updated:** 2026-10-11 17:48 UTC+1
**Current phase:** **Phase 3 closed**, with its last gap fixed this morning. **Phase 4 is in progress.**
**Overall status:** On track. No decisions needed from you.
**Current objective:** Build the combined-signal model (many signals, ML + Bayesian, Shapley breakdown) and collect its data; finish the 24-hour forecasting test tonight; run the pairing redesign (D120) once.

## 1. Where we are
AREPO asks whether information knowable *before* a prediction helps forecast Polymarket price moves better than the
current price and recent momentum.
- **Research machinery:** complete and proven live.
  - The full pipeline passed its final test (D116).
  - The one missing piece, matched "control" comparison markets, worked live this morning (D118 **PASS**).
- **Forecasting:** one confirmed short-term pattern (price reversal), which is not tradable as it stands. More tests finish tonight.

## 2. What changed since the last update
- **Combined-signal model (your direction):** instead of testing one idea at a time, AREPO now combines many signals in four models (the price+momentum baseline, a regularised model, gradient boosting and a Bayesian model) with a Shapley breakdown of what each signal adds.
  - Its design, data builder and model code each passed independent reviews (about 20 fixes made).
  - It will be judged once, prospectively, against the baseline, on accuracy and a fees-included money check.
  - It needs about 40 snapshots (3–4 days) of development data, then 2–3 days of test data. Nothing is trained on real data yet.
- **Extra market details** (fees, market age, open interest, rewards, linked events) are now saved with every snapshot. The existing files are unchanged.
- **Grouping related markets:** a specialist found related markets should be grouped by game-day, not whole season. The pairing test's stricter grouping stays valid.
- **Disk:** the local backup copy was deleted with your OK (verified identical on GitHub); 16 GB free.
- **Pairing redesign (D120) PASSED live (15:47–16:02 UTC+1):** 6 of 6 triggered markets got independent comparison partners (weather, politics, sports, economics). An independent check confirmed it, with caveats: one pair (ECB rate cut vs Eurozone inflation) shares an economic driver, and one run doesn't prove reliability. Recorded as D120/D121.
- **Snapshots 8 and 9** done; order flow (E007) has 2 of 12 samples. The model runner is built and waits for 40 snapshots with the new details (around 14–15 Oct).

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
| E004/E005/E006 | Collecting, 9 of 12 snapshots; results about 23:40 UTC+1 tonight |
| E007 order flow | Registered; collecting (2 of 12) |
| D120 pairing | **PASS** (mechanism; reliability untested) |
| Combined-signal model | Built and reviewed; collecting development data (needs ~40 snapshots) |

## 5. Issues and risks
| Issue | Why it matters | Blocks? | Action |
|---|---|---|---|
| Disk 16 GB free; each pass adds ~150 MB | Fine; the pairing test needs 15.4 GB at launch | No | Run the pairing test soon |
| Comparison markets are often unavailable | Limits future trigger-vs-control studies | No | Any such study must be designed around it |
| Reversal may be quote noise | It may not be usable | No | E004's spread-crossing test |

Data rights are out of scope during the private research phase (your decision, 2026-10-11).

## 6. Decisions I need from you
**None. Autonomous work is continuing.**

## 7. What's next
1. Collection every 2h; E004/E005/E006 scored tonight.
2. Add sanity-check placebos to the model runner; keep collecting for it.
3. First development model fits at ~40 snapshots (around 14–15 Oct).

## 8. Scientific reality check
- **Demonstrated:** the full, honest data machinery works live, comparisons included; one forecasting pattern held on unseen data.
- **Unproven:** tradability, stability over many days, and any signal beyond the reversal.
- **Validated edge beyond momentum:** **none yet.**

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [D118 addendum](implementation/d118/D118_ADDENDUM.md)
