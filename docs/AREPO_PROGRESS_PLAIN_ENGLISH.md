# AREPO — Plain-English Progress

**Last updated:** 2026-10-15 20:49 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Server (Oracle):** collection every 2h, live trade monitor, Kalshi live test and the research queue. All healthy at 19:05Z (measured).
- **Research queue** (live since 15 Oct 18:19Z; tested with a mid-run kill):
  - Running since 19:02Z: building the order-book table for the 3,200-market history set (multi-hour, resumable).
  - Queued next: finalise the table, then rerun the history model with book features (`r4_book`).
- **Data:** history datasets restored from the GitHub archive onto the server; 31,674 files, all checksums OK.
- **Next research batch (batch 2):** 8 jobs for your questions (when order flow predicts; whether liquidity changes
  signals; delayed moves in related markets; whether reversal is just bid-ask bounce).
  - All **12 reviewer fixes applied** (20:15 UTC+1). The corrected multiple-testing total is **906** tests so far
    (it was undercounted at 598).
  - **All batch-2 code passed an independent check** (it caught a real bug: the bounce test's shuffled-data control
    produced a fake effect; fixed before anything ran). Everything is frozen and **queued on the server**: about
    15-20 hours of work, behind the order-book build.
- **Your new priority (creative, original money ideas):** a list of 34 ideas is in the repo
  (`docs/research_lab/CREATIVE_HYPOTHESES_2026-10-15.md`). The autopilot is now turning the top runnable ones into a
  reviewed test batch: holding near-certain markets to resolution, neg-risk price inconsistencies, selling longshots
  passively, deadline ladders and newly listed markets.
- **Autopilot tests passed:** a real unattended run, and a session killed mid-run that was recovered on the next check.

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
3. **Server disk (decide by about 17-18 Oct).** Backups to `arepo-data` run nightly and are verified. Freeing space
   needs you to switch on deletion of old server copies under the rules in
   `docs/research_lab/data_catalogue/RETENTION.md` (only files already verified in a backup; open experiments keep what
   they read). Without it the 12 GB data cap is reached about 22 Oct and collection would stop.
   - Also ready but not switched on: a weekly backup of the live evidence logs (Kalshi test, surprise test, live trade
     alerts) that the nightly backup skips because they are always being written. Recommend switching it on.
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
