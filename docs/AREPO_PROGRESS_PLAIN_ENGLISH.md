# AREPO — Plain-English Progress

**Last updated:** 2026-10-16 00:35 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Server (Oracle):** collection every 2h, live trade monitor, Kalshi live test and the research queue: healthy at
  22:51Z (measured; 1.5 GB RAM free, 13 GB disk free).
- **Research queue:** running the bounce-test diagnostic. Next: the creative-batch data jobs, the batch-2 hypothesis
  features, and the order-book table (part done, resumes).
- **Batch 2, related markets (J5): one candidate.** When the other markets of the same event moved in the last hour,
  this market's price tends to drift back the other way over the next 2 hours. The signal is stable (34 of 39 fresh
  periods). But it only beats a simple baseline, not our best model; it may be quote noise; and it is not shown to be
  tradable. Next comes a check on newer data. No registration yet.
- **Bounce test (J4):** the failed sanity check came from comparing *different* markets with each other, not from
  any market's own history. The reviewer agreed, but rejected re-using the same data to measure the "real" effect,
  because a statistical bias could fake it. A clean re-test on fresh data from 16 Oct onward is designed (about 4 days of
  data needed; it runs around 20 Oct).
- **Batch 2, hypothesis battery (HB2): 6 of 13 ideas pass the first screen** (the shuffled-data check is clean).
  Order-flow momentum is stronger in volatile and wide-spread markets, near resolution, and when it comes from
  trades that are large for that market. One result (volatility) passes the strict all-tests-so-far bar (947 tests).
  Now re-testing on 5,000 different markets (queued); only that counts as "replicated". Not yet tested against costs.
- **Your creative priority:** all 13 reviewer fixes are verified. The fresh 7,000-market download is now allowed to
  start. Two last rules are being added, then the five creative tests get frozen (locked before any results exist).
  **Creative batch 2 drafted** (weather-market favourites; "impossible" price orderings in deadline ladders); its
  review is running. **A new round of original ideas** is being generated (Fable, as you asked), steered by this
  week's findings. Nothing creative has been tested yet.

## 2. Approvals needed from you
1. ~~Automatic Claude sessions~~ **APPROVED and installed 15 Oct** (full power, your call).
   - Pause: `python3 scripts/autopilot/autopilot.py pause` (on the Mac, in the repo). Use `resume` to undo, or `stop` to
     end the running session.
   - It only runs while the Mac is awake. If you chat with me while it's working, pause it first, so two sessions don't
     edit at once.
2. **One-time usage reset (deadline Wed 21 Oct).**
   - No automatic redemption is documented, and I can't see your account page.
   - Check claude.ai/settings/usage (or `/usage`). If there's a claim/redeem button, press it around Sun 18 Oct, after this week's allowance is used.
   - A phone alert was sent 19:2x UTC+1.
3. ~~Server disk~~ **APPROVED 15 Oct** (deletion of server copies that are verified in a backup). The nightly job
   is in a one-night trial run (it only lists what it would delete) before real deletion. The weekly backup of the
   live evidence logs is set up too. Handled by the ops session.
4. ~~Kalshi overnight gap~~ **DECIDED 15 Oct: fill it** (recorded in the ledger before any results, with a sensitivity check).
   Reset reminders also scheduled on your phone: Sun 18 Oct 19:00 and Tue 20 Oct 10:00 UTC+1.

## 3. Usage plan (your schedule; reset times are your statement, not verified)
| When | Plan |
|---|---|
| Now to Sun 18 Oct | Phase A: build, experiment, review |
| After the one-time reset, before Wed 21 Oct | Phase B: strongest experiments, wider screening |
| Thu 22 Oct onward (normal weekly reset) | Phase C: continue |

## 4. Findings so far (all development or exploratory; no tradable edge)
- **Order flow (E007):** real but tiny (about 0.36c).
- **Reversal (E004):** real, but not tradable; likely quote noise.
- **95 economic setups:** none profitable after costs.
- **Hypothesis battery:** 18 of 72 survived; 16 replicate on fresh markets. None covers costs.
- **Wallet freshness:** null in 3 analyses.
- **Surprise detector:** beats chance, but is volatility-driven; live test (E011) is analysed after 11 Nov.
- **Kalshi lead:** the strongest historical predictor; live test (E009/E010) is analysed after 3 Nov.

| Leading candidates | Awaiting confirmation | Confirmed edge |
|---|---|---|
| Kalshi lead; order flow; book/liquidity interactions (being tested) | E009/E010 (3 Nov), E011 (11 Nov) | **None** |

## 5. Infrastructure
| Item | State |
|---|---|
| Server disk | 15 GB free; data 5.2 GB of a 12 GB cap. It fills around 22 Oct without the token above. |
| Server size | 1 CPU and about 5.6 GB RAM, so one heavy job at a time. It can't be enlarged without Oracle console access. |
| Mac | No background jobs. |

## 6. Manual pause and stop
- **Claude autopilot (Mac):** `python3 scripts/autopilot/autopilot.py pause` / `resume` / `stop` / `status`.
- **Pause research jobs:** `ssh oracle '~/arepo/.venv/bin/python ~/arepo/scripts/oracle/queue_worker.py pause'`. Use `resume` to undo, or `stop` to also halt the running job.
- **Status:** the same command with `status`.

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [queue](research_lab/queue/README.md) · [mission](research_lab/AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md)
