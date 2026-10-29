# AREPO — Plain-English Progress

**Last updated:** 2026-10-30 00:12 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Your storage message (28 Oct): done.** I measured the server. Its data folder holds 45 GB, and 37 GB of that is already
  copied to GitHub (the nightly archive uploads and checks everything older than a day). The issue was copies kept on the
  server after upload. Five finished "restore copies" (about 10 GB) belong to closed or finished tests, and no current job reads
  them. They are now set to be removed from the server in tonight's 03:30 run. That run only deletes a file when its fingerprint
  matches the checked copy on GitHub, and any of them can be brought back with one command. Expect about 35 GB after tonight.
  Other large folders stay for now because live work uses them. Each has a review point: the model cache after the MC1 run,
  older market snapshots after the batch 7 count, and an old history folder once its last reader is done.
- **Three stuck jobs found and being fixed (no rule changed):**
  - **The long model run (MC1)** could never finish. Each restart rebuilt its data from a rolling window, so the pieces did
    not match. It now uses one fixed saved dataset and is queued again.
  - **Batch 4's trade fetch** ran out of memory.
  - **Batch 9's frame** hit a tiny disk limit.
  The last two are being fixed now.
- **Batch 7's counting check** is queued. Its text lookup finished (all 13,148 markets found), so the data it needs is pinned.
  It must run before 3 Nov, while the server still holds those snapshots.
- **LT13 (new live test):** its fee-label probe finished. The pre-declared decision rule is being applied now, and an
  independent re-check follows.
- **Round 19 of original ideas** is being written. This time the brief favours ideas that can become light live tests on data
  the server already collects.
- **Batch 3** missed its freeze date during the 24-28 Oct gap. An independent reviewer is ruling on what its own rules say
  happens now. The missed window will not be quietly moved to rescue it.
- **Registered live tests** keep collecting: E009/E010 (3 Nov), E011 (11 Nov), E012-E014 (13 Nov), E015 (15 Nov), E022 (17 Nov),
  E026 (6 Dec).
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

8. ~~Clear restore copies~~ **ANSWERED by your 28 Oct message.** About 10 GB of verified-archived restore copies are cleared
   in the nightly run from 30 Oct. Nothing that a current or planned job reads was touched.

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
| Kalshi lead; order flow; book/liquidity interactions (being tested) | E009/E010 (3 Nov), E011 (11 Nov), E012-E014 (13 Nov), E015 (15 Nov), E022 (17 Nov), E026 (6 Dec) | **None** |

## 5. Infrastructure
| Item | State |
|---|---|
| Server disk | 100 GB disk, 23 GB free (29 Oct 23:50 UTC+1); data 45.2 GB, about 10 GB of it cleared from 30 Oct; job limit 50 GB, collection cap 55 GB, 4 GB free-disk stop unchanged. |
| Server size | **2 CPUs, 12 GB RAM since 22 Oct** (free tier). A second free server (1 CPU, 6 GB, 100 GB) is being requested automatically every 10 min until Oracle has capacity. |
| Mac | No background jobs. |

## 6. Manual pause and stop
- **Claude autopilot (Mac):** `python3 scripts/autopilot/autopilot.py pause` / `resume` / `stop` / `status`.
- **Pause research jobs:** `ssh oracle '~/arepo/.venv/bin/python ~/arepo/scripts/oracle/queue_worker.py pause'`. Use `resume` to undo, or `stop` to also halt the running job.
- **Status:** the same command with `status`.

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [queue](research_lab/queue/README.md) · [mission](research_lab/AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md)
