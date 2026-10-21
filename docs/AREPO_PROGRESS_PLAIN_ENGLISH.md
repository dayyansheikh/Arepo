# AREPO — Plain-English Progress

**Last updated:** 2026-10-21 15:09 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Autopilot:** a session has been running since about 15:00 UTC+1 (21 Oct).
- **Copy-skilled-wallets test (E026):** the counting results are now written into the design (counts only, no results).
  - About 450 usable copy signals a day from 160 wallets across 650 events. Over the 21-day window that comes to about
    9,400 copies, far above the pre-set minimum of 400. The smallest effect it can reliably detect is about 4 cents per
    dollar. Average trading costs are about 5 cents per dollar, so a copy would have to earn more than that to show anything.
  - An honest caveat: AREPO first sees a skilled wallet's trade a median 4.5 hours after it happens, so "copy at once"
    really means about 6.6 hours late.
  - **A measurement bug was found and fixed:** the memory figure for the live recorder was really the memory of its
    parent process. A short re-check (q0545, counts only) is queued for tonight to measure the true figure before
    registration.
  - Also disclosed: an early, uncommitted count was seen before the pass/fail gates were written down. The gates sit far
    below those numbers, so they could not have been placed to pass narrowly, but they were not set blind.
  - **Now:** the independent challenger review is running. Registration is still planned before 24 Oct, collection
    25 Oct to 15 Nov. You get a phone note at the review verdict.
- **Bounce re-check (SB2-J4-R) finished: VOID.** Its own pre-set safety check (a shuffled-data placebo) failed for 2 of
  its 5 tests, so by its rules no verdict is read. The 5 tests stay counted. No new run is planned; it is low priority.
- **LT3 (E015) is registered.** Collection 24 Oct to 14 Nov, single analysis after 15 Nov.
- **Tonight (handled by later sessions):** LT5's counting jobs and seal (must run before 04:30 UTC+1), the batch 4/6/7/8
  seals after midnight UTC, and the **server resize to 2 CPU / 12 GB at about 03:40 UTC+1** (your approval). No
  deploys during 03:40-04:45 UTC+1. After the resize, the model run (MC1) is re-queued with the bigger memory.
- **Live:** the E012-E014 collector is running; LT3's collector is installed. Registered live tests waiting for their
  single analysis: E009/E010 (3 Nov), E011 (11 Nov), E012-E014 (13 Nov), E015 (15 Nov).

## 2. Approvals needed from you
1. ~~Automatic Claude sessions~~ **APPROVED and installed 15 Oct** (full power, your call).
   - Pause: `python3 scripts/autopilot/autopilot.py pause` (on the Mac, in the repo). Use `resume` to undo, or `stop` to
     end the running session.
   - It only runs while the Mac is awake. If you chat with me while it's working, pause it first, so two sessions don't
     edit at once.
2. ~~One-time usage reset~~ **HANDLED by you (17 Oct)**; no more reminders needed.
3. ~~Server disk~~ **APPROVED 15 Oct** (deletion of server copies that are verified in a backup). The nightly job
   is in a one-night trial run (it only lists what it would delete) before real deletion. The weekly backup of the
   live evidence logs is set up too. Handled by the ops session.
4. ~~Kalshi overnight gap~~ **DECIDED 15 Oct: fill it** (recorded in the ledger before any results, with a sensitivity check).
   Reset reminders also scheduled on your phone: Sun 18 Oct 19:00 and Tue 20 Oct 10:00 UTC+1.

5. **Archive rotation by ~20 Oct (needed by batch 3).** The nightly deletion of backed-up server copies must move from
   trial to real by about 20 Oct. If not, batch 3's live stages wait, and missed data stays missing. Handled by the ops
   session; flagging the dependency only.

6. ~~Server disk~~ **DONE 17 Oct** (you enlarged it to 100 GB, free).

7. ~~More server memory for MC1~~ **APPROVED 21 Oct:** resize to 2 CPU / 12 GB (still free), scheduled automatically
   for 22 Oct about 03:40 UTC+1. MC1 is re-queued afterwards.

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
- **Stale cross-venue horizons (batch 12):** no finding; a shuffled-horizon check reproduced the pattern.
- **Kalshi lead:** the strongest historical predictor; live test (E009/E010) is analysed after 3 Nov.

| Leading candidates | Awaiting confirmation | Confirmed edge |
|---|---|---|
| Kalshi lead; order flow; book/liquidity interactions (being tested) | E009/E010 (3 Nov), E011 (11 Nov), E012-E014 (13 Nov), E015 (15 Nov) | **None** |

## 5. Infrastructure
| Item | State |
|---|---|
| Server disk | 100 GB disk, 56 GB free (measured 19 Oct 21:39 UTC+1); collection cap 45 GB, 4 GB free-disk stop unchanged. |
| Server size | 1 CPU, about 5.6 GB RAM. A second free server (1 CPU, 6 GB, 100 GB) is being requested automatically every 10 min until Oracle has capacity. |
| Mac | No background jobs. |

## 6. Manual pause and stop
- **Claude autopilot (Mac):** `python3 scripts/autopilot/autopilot.py pause` / `resume` / `stop` / `status`.
- **Pause research jobs:** `ssh oracle '~/arepo/.venv/bin/python ~/arepo/scripts/oracle/queue_worker.py pause'`. Use `resume` to undo, or `stop` to also halt the running job.
- **Status:** the same command with `status`.

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [queue](research_lab/queue/README.md) · [mission](research_lab/AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md)
