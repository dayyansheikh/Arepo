AREPO: what happened today (10:00 to 18:20 UTC+1, Sunday 11 October) and where the project stands

THE ONE-PARAGRAPH VERSION
Today AREPO finished proving its research machinery works. A new "fair comparison" mechanism passed a live test, matching each triggered market with an independent comparison market. Following your reminder, I also pivoted the hunt for an edge. Instead of testing one idea at a time, AREPO now has a combined model that weighs many signals at once and uses Shapley values to show what each signal contributes. It is fully built and independently reviewed several times, and it is now collecting the data it needs. The first real model results are due around the evening of 14 October. Nothing found so far proves an edge that would make money after costs.


PART 1: THE MORNING (10:00 to 12:40)

1. The first comparison test (D118) passed, with a big asterisk.
Background: to know whether a "trigger" (for example a sudden order-book imbalance) matters, you compare triggered markets with similar untriggered ones, like a drug trial compares treated patients with untreated controls. Phase 3 had shown everything worked except this matching step.
- We redesigned the test overnight. A rehearsal rejected the first design because it ran too slowly, and a smaller design was locked in at 10:22.
- It ran live from 10:22 to 10:36 and passed: 12 of 12 markets processed, with no engineering faults.
- The asterisk: only 2 of 7 triggered markets found a comparison partner. One of those pairs was almost certainly "sibling" markets (Knicks vs Thunder playoff odds from the same event). Siblings move together, so they are not a fair comparison.
- Verdict (D119): the mechanism works, but not reliably enough to measure anything yet. Phase 3 was declared closed and Phase 4, the edge-hunting phase, continued.

2. Collector fix.
The 2-hourly "photograph of all of Polymarket" (about 250,000 markets each time) had failed overnight. Polymarket's security firewall blocks certain specific page requests. I found a workaround that asks for a slightly different page size, and every snapshot since has been complete.

3. Three quick studies.
- Calibration (C1, about 3,000 resolved markets): one day before markets close, Polymarket prices are close to honest probabilities. Things priced at 85% happen about 84% of the time. In everyday terms, the crowd is a good forecaster at that horizon, so there is no easy "the market is systematically wrong" edge one day out.
- Sibling markets (L1): when one market in an event moves, its siblings do not reliably follow a little later. Nothing to exploit.
- Order flow (five screens): of five ideas about trading activity predicting price moves, only one survived. It was formally registered as experiment E007, with its rules locked before any new data. It needs 12 samples, one per snapshot, by 18 October.

4. Full regression check: 2,125 backend and 101 frontend tests all pass.

5. Pairing redesign (D120) designed.
To fix the asterisk from step 1, a specialist designed a better approach. First screen many markets cheaply. Then pick triggered and comparison markets that come from separate "families" (different events and series), across all categories, not just sports. A second, independent AI model (Fable 5.1) reviewed it and its suggested changes were adopted.

(Separately, another session wrote a draft plan for a future automated trading engine. As you instructed, I have not touched it.)


PART 2: THE BIG PIVOT (from about 13:00)

6. You reminded me the goal is not to test ideas one by one, but to combine many signals with machine learning, Bayesian methods and Shapley values. You were right. I had drifted into testing single ideas (E001 to E007), which is slow and narrow. Here is what was built this afternoon.

The question the model answers: for each market, will its price go down, stay flat, or go up by the next snapshot two hours later? Right now about 85% of markets stay flat. The skill is in spotting the 15% that move, and which way. The model gives probabilities, and it is scored on how good those probabilities are, not just on right or wrong.

The signals it uses (all knowable before the prediction):
- recent price moves and momentum, the spread, liquidity and time left until the market closes;
- order-book shape: whether buyers or sellers are stacked up, and how deep the book is;
- whether sibling markets just moved;
- how stale the quotes are;
- new details we used to throw away: fees, market age, rewards, open interest, comment counts and linked events. Every snapshot now saves these.

The four models, from simple to clever:
- M0: the baseline, using price and momentum only. This is the bar to beat.
- M1: a simple regularised statistical model.
- M2: gradient boosting, a strong ML model. It is also where the Shapley values come from, showing how much each signal contributed.
- M3: a Bayesian model that "pools" what it learns across categories and events. Think of it as letting small categories borrow strength from big ones without pretending they are identical.

7. How we keep it honest. This is most of the afternoon's work.
Every piece (the design, the data builder, the models, the runner) went through independent reviews, and about 40 fixes were made. The important ones, in plain terms:
- Comparing like with like. In the first design, the "start" price and the "end" price came from two different data sources. The model could have "won" just by predicting the small gap between those sources, not real price moves. Both ends now use the same source.
- Fair fight. The challenger models got a final calibration tweak that the baseline didn't. Every model now gets the same treatment.
- Crystal-ball check. Each signal must be knowable at the start time. One example: running totals like volume can only be read from the start snapshot, never from the end one, or the model would be peeking.
- Resolution leak. Markets that already have a proposed resolution are excluded, because their answer is half-known.
- Counting evidence fairly. Markets about the same thing move together, so counting them as independent evidence would overstate how sure we are. A specialist measured this from real price data. Markets in the same game move together strongly, and games in the same league on the same day move together somewhat. A whole season adds almost nothing on top of that. So related markets are grouped by "game-day" (about 4,900 independent groups per snapshot).
- Sanity checks (placebos). The runner also runs deliberately broken models:
  - one with scrambled answers, which should show no edge;
  - one fed "future" data, which must show a big edge, proving the system can catch cheating;
  - one that only knows quote age.
  If a broken model "wins", something is leaking.
- One shot. The final test of the best model is decided in advance, on data it has never seen. It must beat the baseline on probability accuracy first. Only then is the money question checked: would trading on it have profited after fees? There is no peeking partway through.

8. Disk space. With your OK, I deleted the local copy of the data backup (2.7 GB) after checking byte for byte that the GitHub copy is identical. The GitHub copy is private and complete.


PART 3: THE AFTERNOON RESULTS

9. The redesigned comparison test (D120) PASSED.
- It was built, rehearsed (the rehearsal again forced a smaller design), reviewed twice, then locked in with a fingerprint of every file.
- It ran once, live, from 15:47 to 16:02. All 6 triggered markets found an independent comparison partner, compared with 2 of 7 this morning, and no siblings. The pairs were a genuine mix:
  - weather: Amsterdam vs Chicago temperatures;
  - politics (two pairs): French presidential ballot vs Victorian election, and an Israeli minister vs Canada joining the EU;
  - sports (two pairs): a Norwegian football match vs an Argentine spread, and Champions League vs NFL winners;
  - economics: ECB rate cut vs Eurozone inflation.
- An independent check confirmed it, with honest caveats:
  - The economics pair are separate events but share a driver, the European economy.
  - One run proves the mechanism works, not that it works every time.
- Recorded as decisions D120 and D121.

10. Collection now runs on its own. You approved a scheduler on your Mac that takes a snapshot every 2 hours even when no Claude session is open. It only works while the Mac is awake, and the first scheduled run is at 19:31.


WHERE THE PROJECT STANDS NOW

What AREPO can do:
- photograph all of Polymarket every 2 hours, completely and reliably;
- run leakage-safe experiments with locked rules, fair comparisons and honest statistics;
- build the combined-signal model's data, fit four models, explain them with Shapley values and score them fairly;
- keep all data backed up privately on GitHub.

Experiment scoreboard:
- E002 (price reversal): confirmed. About 21% of a market's last-hour move tends to reverse within about 5 hours. Not shown to be tradable after costs.
- E003 (order-book imbalance): no value.
- E004/E005/E006 (24-hour forecasting test): 9 of 12 snapshots. Results tonight, around 23:40.
- E007 (order flow): 2 of 12 samples. Deadline 18 October.
- Combined-signal model: collecting data. The first real development results need 40 consecutive snapshots, around 21:30 on 14 October. The single locked final test then needs about 2 to 3 more days.

Honest bottom line:
- Proven: the machinery works, end to end, live, including fair comparisons.
- Not proven: any signal that makes money after fees. The one confirmed pattern (reversal) is real but small.
- The combined model is the best shot so far at finding an edge, because it lets many weak signals add up. It could still find nothing, and if so we will say so.

Decisions needed from you: none right now. Two small things help:
1. Keep the Mac awake and plugged in until 15 October, so the snapshot chain is not broken.
2. Email doesn't work from my current session. Reconnecting Gmail (/mcp, or restarting Claude Code) would let me email you directly.

Next steps:
1. Snapshots 10 to 12 tonight; the 24-hour forecasting test is scored straight after the last one.
2. Collection continues automatically to 14 October; then the first combined-model results.
3. A final independent review, then the single locked test of the best model.
