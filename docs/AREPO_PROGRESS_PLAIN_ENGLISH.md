# AREPO — Plain-English Progress

**Last updated:** 2026-10-12 00:02 UTC+1
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
| E004 reversal (24h test) | **Supported** but **not tradable**: about 23% of the last-hour move reverses; buying at ask and selling at bid lost about 4.5c/share |
| E005 linked-market consistency | **Not supported** |
| E006 when reversal is stronger | Supported on direction only: stronger in illiquid markets and far from close; the effect sizes did not carry over |
| E007 order flow | Collecting (5 of 12) |
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
**Infrastructure fixes are READY FOR APPROVAL.** They are coded and tested on branch `fix/infra-2026-10-11`, not deployed. Details: `docs/infra/INFRA_FIXES_2026-10-11.md` on that branch.
1. **Merge and deploy the fix branch.**
   - The research status page was running about 550,000 database queries per request, which crashed the API. It now uses a few queries.
   - The collector re-read about 110,000 rows twice per run and wrote nothing. It now skips finished cohorts.
   - Backups no longer re-download unchanged data.
   - Memory caches are capped.
   - Expected effect: far less database bandwidth and disk I/O, and no more memory crashes.
   - Rollback: revert the merge.
   - An independent pre-deploy code review is running first.
2. **Run the prepared security SQL in Supabase.** It locks 7 tables that the app never uses through the Data API. Rollback is included.
3. **Database size (951 MB against the 500 MB free limit). Choose one:**
   - **(a)** archive old snapshot history to a verified backup, then prune it. This is data-destructive, the restore is tested, and it also needs a science review.
   - **(b)** Supabase Pro at $25/month.
4. **Resend:** dashboard access is needed to check email delivery. The code looks fine, and digests are off.

5. **Optional: an API key for on-chain history.** To trace where a betting wallet's money came from (a strong signal for the Maduro-style detector), AREPO needs a blockchain-data key, because the free keyless routes are blocked. Free tiers exist (for example Polygonscan or Alchemy). Creating the key and storing it is your decision.

Everything else is running autonomously.

## 7. What's next
1. Collection every 2h; E004/E005/E006 scored tonight.
2. Add sanity-check placebos to the model runner; keep collecting for it.
3. First development model fits at ~40 snapshots (around 14–15 Oct).

## 8. Scientific reality check
- **Demonstrated:** the full, honest data machinery works live, comparisons included; one forecasting pattern held on unseen data.
- **Unproven:** tradability, stability over many days, and any signal beyond the reversal.
- **Validated edge beyond momentum:** **none yet.**

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [D118 addendum](implementation/d118/D118_ADDENDUM.md)
