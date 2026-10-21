# AREPO — Plain-English Progress

**Last updated:** 2026-10-21 20:44 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Autopilot:** a session has been running since about 19:55 UTC+1 (21 Oct).
- **LT4 counting checks finished: one of three tests goes ahead (E022).**
  - E022 asks whether displayed liquidity that cannot really be traded against tells us anything. It passed every
    pre-set counting check.
  - E020 (new orders versus cancellations) and E021 (how recent the last trade was) failed theirs: too few usable
    cases, and too little power to see a half-cent effect. They are dropped before registration and do not count.
  - Done tonight: the code was trimmed to the one remaining test, an independent freeze check found one real problem
    (the size check shuffled data differently from the real test) which is now fixed, and the code is frozen.
  - Next: the size check runs on the server from about 05:00 UTC+1 on 22 Oct (2-4 hours), then registration
    before 25 Oct so collection can start on 26 Oct.
- **Three batch checks failed their population gates (recorded, nulls included):** batch 13-R (too few complete
  frames and events), batch 14-W (58 markets where 150 were needed) and batch 15-P (37 pairs where 60 were needed).
  Batch 14-W and 15-P count 2 tests each as "not testable"; 13-R will count 1 when its last job writes it.
- **Fixed:** five batch 18 counting jobs were stuck in a retry loop because they asked for 20 GB of disk headroom for
  tiny output files. They now ask for 0.25 GB and can run. Ten batch 18 job drafts were renumbered because their numbers
  clashed with the signal engine's jobs.
- **LT6 code, part 2 finished** (the recorder and the analysis entry point; 137 tests pass). Still waiting on E022's
  registration date, as planned.
- **Copy-skilled wallets (E026):** registered; collection starts 25 Oct (phone note then).
- **Tonight (handled by later sessions):** LT5's counting jobs and seal (must run before 04:30 UTC+1), the batch 4/6/7/8
  seals after midnight UTC, and the **server resize to 2 CPU / 12 GB at about 03:40 UTC+1** (your approval). No
  deploys during 03:40-04:45 UTC+1. After the resize, the model run (MC1) is re-queued with the bigger memory.
- **Live:** the E012-E014 collector is running; LT3's collector is installed. Registered live tests waiting for their
  single analysis: E009/E010 (3 Nov), E011 (11 Nov), E012-E014 (13 Nov), E015 (15 Nov), E026 (6 Dec).

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

8. **NEW (21 Oct): let Claude clear temporary restore copies on the server.** Batch 17's smoke check refuses to
   run because a 925 MB restore copy (a hash-checked copy of data that is safe in the archive) sits inside batch 17's
   folder, which has a 0.3 GB limit. The safety hook rightly stops Claude from moving or deleting anything in the data
   folder. **Decision needed:** allow Claude to move that copy out of the batch 17 folder (nothing is lost), or to
   delete it (it is in the archive). More generally, finished restore copies (about 9 GB now: batch 18 4.9 GB, LT4
   3.0 GB, LT5 0.8 GB, batch 17 0.9 GB) will need clearing within about a week, because jobs stop at a 40 GB data
   limit (now 30 GB). Batch 17 is not late yet (its window opens 26 Oct).

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
| Kalshi lead; order flow; book/liquidity interactions (being tested) | E009/E010 (3 Nov), E011 (11 Nov), E012-E014 (13 Nov), E015 (15 Nov), E026 (6 Dec) | **None** |

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
