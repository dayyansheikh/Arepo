# AREPO — Plain-English Progress

**Last updated:** 2026-10-17 06:01 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Autopilot:** a session started at 05:38 UTC+1 and is working.
- **Server disk:** deleting old copies of the 2-hourly market snapshots (once they are 8 days old and safely backed up) is now
  switched on. The safety check that all four creative batches had saved what they need passed first. Snapshot deletion starts on 19 Oct.
  Until it catches up, I raised the server's data limit from 12 to 13 GB, so collection does not pause around 19-20 Oct. Disk space
  is still fine.
- **Batch 1-D (neg-risk sets): nothing advanced.** D1 was +0.78 points (p 0.016), which fails the pre-set bar (p < 0.01, at least
  1 point, and surviving removal of the top 5 events; it fell to +0.15). D2 had too few cases to test. The sealed sample stays unopened.
  Total tests counted so far: 1,106.
- **Jobs that ran out of memory:** the multi-signal ML dry run is fixed (now about a quarter of the memory) and queued again;
  batch 3's counting job is being fixed.
- **Deadline 22 Oct:** fresh downloads for batches 4 and 6 must finish before the seal date. Independent checks passed (with fixes
  applied), and their first jobs are queued: batch 4's sampling frames, and batch 6's 20-market test download. Batch 5's downloads
  and counting job are queued too. The server has well over 12 hours of work lined up.
- **Batch 4 analysis code:** the independent check found 6 things to fix before any counted test. One is a design flaw: a
  week-level check could never have had enough weeks to run. These are being fixed without looking at any outcome data.
- **Batch 7 (new):** being designed from the next ideas on the list: a "specificity discount" in market rules, geopolitics longshots,
  stepping aside as a maker after Kalshi moves, and price unwinds after a sibling market resolves.

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
| Server disk | Data 9.9 GB (05:39 UTC+1); cap raised 12 -> 13 GB today. Backed-up trade samples deleted at 3 days (freed 0.6 GB last night); snapshots now deleted at 8 days (from 19 Oct). Expected to level off at about 11-12 GB. 8.6 GB of disk free. |
| Server size | 1 CPU and about 5.6 GB RAM, so one heavy job at a time. It can't be enlarged without Oracle console access. |
| Mac | No background jobs. |

## 6. Manual pause and stop
- **Claude autopilot (Mac):** `python3 scripts/autopilot/autopilot.py pause` / `resume` / `stop` / `status`.
- **Pause research jobs:** `ssh oracle '~/arepo/.venv/bin/python ~/arepo/scripts/oracle/queue_worker.py pause'`. Use `resume` to undo, or `stop` to also halt the running job.
- **Status:** the same command with `status`.

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [queue](research_lab/queue/README.md) · [mission](research_lab/AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md)
