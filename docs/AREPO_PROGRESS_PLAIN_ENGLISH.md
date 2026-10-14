# AREPO — Plain-English Progress

**Last updated:** 2026-10-14 22:04 UTC+1
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

## 2a. Latest (12 Oct afternoon)
- **E007 order flow: Supported**, and it is not a quote-lag artefact. It is real but tiny (about 0.36c).
- **Hypothesis battery:** 72 pre-declared tests, 18 survived correction.
  - Survivors include: aggressive buying continues; price moves without trades reverse (quote noise); longshots and favourites drift.
  - Nulls: wallet freshness, repeat winners, cross-market and order-book effects.
  - **None covers trading costs.**
- **Economic conditions:** 95 setups (liquid markets, strong signals, combined signals, passive orders). **None is profitable after costs.**
- **Learned surprise detector:** about 4x better than chance at flagging surprise jumps, and it beats 100/100 placebos. It is driven by "volatile week, quiet day", not wallets. It is mostly false alarms and has no paper profit. It is now **live in the monitor**, as a genuine prospective test.
- **Polymarket vs Kalshi, now live (E009):** history said Kalshi moves first by 10-20 min. A live test now polls about 110 matched pairs on both venues every 2 minutes, writes a frozen prediction before the outcome exists and checks Polymarket 10/20/60 min later, including a paper taker trade. Registered (reviewed) to run until 3 Nov, analysed once. Honest expectation: probably **inconclusive** (only about 25-40 independent events; Kalshi prices in these long-dated markets rarely move).
- **Running:** deadline ladders and about 10k more historical markets.

## 2. What changed overnight (11–12 Oct)
- **24-hour forecasting test, scored and independently checked:**
  - Price reversal (E004) is real but **not tradable**. Buying at the ask and selling at the bid lost about 4.5c per share.
  - Linked-market consistency (E005): no value.
  - When reversal is stronger (E006): the direction was confirmed, but the effect size did not carry over.
- **Resolution forecasting** (about 7,500 resolved markets): no model beat the bias-corrected market price. A 7-day "bias" turned out to be placeholder prices in markets that had never traded, so it was rejected.
- **Historical ML** (3,200 markets, 9 months):
  - Most of the apparent gain was just predicting volatility.
  - Beyond a fair baseline, **trade flow adds a small, demonstrated amount of direction skill at 2h and 6h** (about 2%), but part of it may be a data-timing artefact.
  - New-wallet signals: nothing demonstrated.
  - The sanity checks (placebos) now behave correctly.
- **Unusual pre-news flow** (your Maduro idea):
  - **Maduro:** a 6-day-old wallet bought about $32.5k of "Maduro out" at about 7.5c, roughly 3.4h before the price jumped. But similar bets had happened 7 times before in that market with nothing following.
  - **5 locked alarms on about 357 random past markets:** no better than chance, and far too few alarm episodes to tell.
  - **11 reported cases** (Iran strikes, Nobel, Google Year in Search and others): alarms went off before 4 of 10. The "large trade" alarm fired on about half of the case markets against about 1 in 15 controls. But every alarm fired 36–52h early, while the reported bets came in the **final hours**.
  - **So the next step is a live 5-minute large-trade monitor**, now being built and piloted.
- **Trading costs:** a typical round trip costs about 4.5c. Any edge most likely lives in liquid markets or in large predicted moves.

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
| E007 order flow | **Supported**: one-sided buying predicts a small continued drift (about 0.36c), in 11/12 periods. It is not a quote-lag artefact (it survives excluding the last 15 min of trades). Too small to trade directly, but the first live evidence that flow carries information. |
| E009 Kalshi lead (live) | **Registered**, collecting until 3 Nov; one analysis then |
| D120 pairing | **PASS** (mechanism; reliability untested) |
| Combined-signal model | Built and reviewed; collecting development data (needs ~40 snapshots) |

## 5. Issues and risks
| Issue | Why it matters | Blocks? | Action |
|---|---|---|---|
| Disk 16 GB free; each pass adds ~150 MB | Fine; the pairing test needs 15.4 GB at launch | No | Run the pairing test soon |
| Comparison markets are often unavailable | Limits future trigger-vs-control studies | No | Any such study must be designed around it |
| Reversal may be quote noise | It may not be usable | No | E004's spread-crossing test |

Data rights are out of scope during the private research phase (your decision, 2026-10-11).

## 6. Decisions and actions
**Done (13–14 Oct):**
- Infrastructure fixes deployed (PR #18). The API no longer crashes on the status page.
- Supabase security lockdown applied.
- Supabase archived and pruned: **951 → 359 MB**, under the free limit. The old snapshots are in the private `arepo-data` release `provenance-archive-2026-10-12`, restorable with one command.
- Etherscan key stored on the Mac, the Oracle server and as a GitHub secret.
- ntfy push alerts are live.
- **Collection moved to the Oracle server.** The Mac no longer runs anything in the background. Switched at 11:29 UTC on 14 Oct. Before the switch, the Mac was offline overnight from about 00:00 to 10:45 UTC, so 6 snapshots and about 11 hours of live monitoring are missing. Those gaps stay missing. The server has room for about 8 more days of data unless the archive rotation is switched on.

- **Mac data retired (user-run, 2026-10-14 ~21:30 UTC+1):** 306,147 files deleted after hash checks against verified GitHub releases. **Mac free disk: about 42 GiB.** Logs are in `~/arepo_retirement_logs/`.

**Pending:**
- A GitHub token for the server's archive rotation (the server disk cap is reached around 22 Oct without it).
- Whether to count the server validation copy for the overnight E009/E010 gap.
- The Resend audit (later).

## 7. What's next
1. Collection every 2h; E004/E005/E006 scored tonight.
2. Add sanity-check placebos to the model runner; keep collecting for it.
3. First development model fits at ~40 snapshots (around 14–15 Oct).

## 8. Scientific reality check
- **Demonstrated:** the full, honest data machinery works live, comparisons included; one forecasting pattern held on unseen data.
- **Unproven:** tradability, stability over many days, and any signal beyond the reversal.
- **Validated edge beyond momentum:** **none yet.**

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [D118 addendum](implementation/d118/D118_ADDENDUM.md)
