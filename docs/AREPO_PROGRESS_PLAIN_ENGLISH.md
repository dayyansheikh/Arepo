# AREPO — Plain-English Progress

**Last updated:** 2026-10-17 00:45 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Autopilot:** sessions between about 21:45 and 23:30 UTC+1 failed at once on a network (DNS) error. It recovered at 23:57; nothing was lost.
- **Creative batch 1, first results: nothing advanced.** Carry ideas A1, A2 and C1 were negative after costs. E could not be tested
  (2,886 of 3,200 markets have no stored question text; a data gap, not a negative result). B could not be tested (52 usable ladders
  against 300 needed). The sealed fresh sample stays unopened for these. 9 tests counted.
- **Batch 1-D (neg-risk sets):** the capture list is frozen (60 captures). The screen ran out of memory once; it's fixed and re-queued.
- **ML near-resolution effect (J8):** the extra model skill in a market's last 24 hours survives all three checks the challenger asked
  for (look-ahead, after-end, near-end). It is still forecasting only, with no cost check. Next it goes into the live ML run.
- **Live multi-signal ML run (MC1):** never run so far; it needs 40 unbroken 2-hourly captures, which we'll have at about 20:00 UTC+1
  today. A dry run is on the server now.
- **Batch 3:** independent re-check passed; its counting job is queued.
- **Batch 5:** challenged (one placebo could never fail; fixed), revised, and its code is being written.
- **Batch 6 (new):** a fresh Fable round produced 19 new ideas, for example neg-risk conversion dumps, a "reward-shadow" price band at
  0.90-0.96, and predicting the catastrophic losses that sank batch 1's longshot idea. Batch 6 is being designed now.
- **Server:** the weather download (batch 2) is running after a memory fix.

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

5. **Archive rotation by ~20 Oct (needed by batch 3).** The nightly deletion of backed-up server copies must move from
   trial to real by about 20 Oct. If not, batch 3's live stages wait, and missed data stays missing. Handled by the ops
   session; flagging the dependency only.

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
| Server disk | Data 9.7 GB of the 12 GB cap (22:57Z). Deletion of backed-up copies is now ON for trade samples (first run 04:30 UTC+1, frees ~0.6 GB). Snapshots stay protected until batch 4's backfill is complete (a fix is in progress). Without that, the cap is reached about 20 Oct. |
| Server size | 1 CPU and about 5.6 GB RAM, so one heavy job at a time. It can't be enlarged without Oracle console access. |
| Mac | No background jobs. |

## 6. Manual pause and stop
- **Claude autopilot (Mac):** `python3 scripts/autopilot/autopilot.py pause` / `resume` / `stop` / `status`.
- **Pause research jobs:** `ssh oracle '~/arepo/.venv/bin/python ~/arepo/scripts/oracle/queue_worker.py pause'`. Use `resume` to undo, or `stop` to also halt the running job.
- **Status:** the same command with `status`.

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [queue](research_lab/queue/README.md) · [mission](research_lab/AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md)
