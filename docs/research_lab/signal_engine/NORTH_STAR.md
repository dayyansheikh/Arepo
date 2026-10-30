# North Star: the continuously improving signal engine (owner directive, 2026-10-21 00:01 UTC+1)

**What the owner asked for (paraphrased):**
- One continuous goal, always being worked on whatever else happens: find which signals predict Polymarket
  markets and make the repo's suggested signals as accurate and predictive as possible.
- Users are shown signals and do their own research.
- The baseline can be momentum and market state. The goal is to keep improving it with any other signal (order flow,
  wallets, cross-venue, books, crypto, news...), even when no edge is confirmed.

## Principle
This track is about forecast quality, not about edge claims.
- Its yardstick is honest out-of-sample, prospective accuracy:
  - log-loss and Brier for direction/resolution targets at fixed horizons;
  - calibration;
  - category breakdowns, with event-clustered uncertainty.
- It never claims profitability. The product labels outputs as signal strength, not probability or expected profit (AGENTS.md).
- The confirmation programme (E-tests, Holm, sealed windows) continues separately and unchanged.

## Mechanism: champion / challengers
1. **Champion v0:** momentum + market state baseline (frozen spec, hashed).
2. **Challengers:** the champion plus one family, or a learned combination. Each is a frozen, hashed spec with a version.
3. **Prospective scoring:**
   - At every complete-universe capture, the champion and every active challenger write predictions for every eligible
     market before outcomes exist (write-once, receipt-timed).
   - Outcomes are labelled later.
   - A rolling leaderboard is computed daily.
4. **Promotion:** a challenger replaces the champion only under a rule declared in advance. Example: at least 14 days
   of prospective scoring, and a market-clustered CI of the log-loss gain over the champion that excludes zero.
   Retired champions stay in the record.
5. **Retraining:**
   - Models refit on a fixed schedule, on data strictly before each prediction origin (walk-forward). No future data.
   - Light, incremental and memory-safe (host: 1 OCPU / 5.6 GB; heavy jobs run exclusive).
6. **Outputs:**
   - The leaderboard and feature-family contributions on the owner's /lab dashboard.
   - A per-market signal feed the website can show, after an owner-approved web deploy.

## Standing rule for every session (autopilot and interactive)
- At least one unit of work per session goes to the signal engine: build, fix, add a challenger, improve
  features or data, or review the leaderboard.
- The queue should always have signal-engine work scheduled or running.
- Findings from every other experiment feed challengers. A replicated or advanced effect becomes a candidate feature family.
