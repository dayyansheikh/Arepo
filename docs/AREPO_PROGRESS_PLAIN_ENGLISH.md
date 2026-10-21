# AREPO — Plain-English Progress

**Last updated:** 2026-10-21 13:30 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Autopilot:** a session has been running since 09:43 UTC+1 (21 Oct).
- **NEW: LT3 (E015) is REGISTERED (21 Oct).** It asks whether price moves made only by quotes (no trade) behave differently over the next hours from moves made by trades.
  - The re-run of the safety (size) check gave exactly the same numbers as the first run, and the three binding rates passed (4.4-4.8% against a 5.8% limit).
  - Collection runs 24 Oct to 14 Nov, with a single analysis after 15 Nov. No early looks.
  - Registered live tests now waiting for their single analysis: E009/E010, E011, E012-E014 (LT2) and E015 (LT3).
- **Batch 18 (CB18):** the counting code was finished, checked by an independent reviewer and fixed. Its 7 jobs are now on the server queue (restores, then five counting checks; counts only).
- **Three more queued jobs:** batch 13's sealed holdout, batch 15's "listed on Kalshi first" count, and batch 16's exclusion list.
- **LT5 (five possible new live tests) moved fast today.**
  - The design passed an independent challenger review (accepted with changes, the changes re-checked).
  - Its counting code was checked three times until clean. One fix had quietly loosened a rule; the reviewer caught it and it was put back as originally written.
  - Its counting jobs are queued. They must run tonight, before the server's routine deletion of 8-day-old data at 04:30 UTC+1, which would remove some of the history they need. Tonight's session handles that.
  - Earliest start is 30 Oct.
- **Copy-skilled-wallets test (E026):** the design is done (phone note sent). Its counting check passed all three pre-set gates: about 450 usable copy signals a day from 160 wallets across 650 events, in three days of data. These are counts only, no results. Next come the challenger review and registration (planned before 24 Oct), then collection from 25 Oct to 15 Nov.
- **Model run (MC1) ran out of memory again** (about 4.9 GB of 5.6 GB). It won't be retried on this server; see approval 7.
- **Live:** the E012-E014 collector is running. LT4's counting checks and batch 17's reproduction check are queued. Oracle still says "out of host capacity" for the second server.

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

7. **NEW: more server memory for the model run (MC1).** The run needs more than the server's 5.6 GB. The second free
   server still can't be created ("out of host capacity"). Another option: in the Oracle console, resize this server
   from 1 CPU / 6 GB to 2 CPU / 12 GB. That stays inside the free allowance (4 CPU / 24 GB in total, even with the
   planned second server). A resize means a reboot of a few minutes. Do it right after a collection pass (passes start
   at :31 past every even hour). **Your decision:** resize now, or keep waiting for the second server. Until then, MC1
   waits.

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
