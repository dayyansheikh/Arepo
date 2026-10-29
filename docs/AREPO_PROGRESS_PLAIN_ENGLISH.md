# AREPO — Plain-English Progress

**Last updated:** 2026-10-30 00:43 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Your storage message (28 Oct): done.** The server's data folder is down from **45 GB to 36 GB**, and the disk now has
  33 GB free.
  - I measured it first. 37 of the 45 GB was already copied to GitHub by the nightly archive. The problem was copies kept
    on the server after upload.
  - Five finished "restore copies" (about 11 GB, from closed or finished tests, read by no current job) were removed.
    Every file was first checked against its GitHub copy (886 of 886 matched), and any of them can be brought back with one
    command.
  - I did this tonight rather than at 03:30 because the folder was 1.4 GB from the limit where collectors start skipping.
  - Other large folders stay for now because live work uses them. Each has a review point: the model cache after the MC1
    run, older market snapshots after the batch 7 count, and an old history folder once its last reader is done.
- **Stuck jobs fixed (no rule changed):**
  - **MC1 (long model run):** could never finish, because each restart rebuilt its data from a moving window. It now uses
    one fixed saved dataset and is running.
  - **Batch 4 trade fetch:** ran out of memory. It now loads only the columns it uses (same results, a third of the memory)
    and is queued again.
  - **Batch 9:** one data step hit a size limit that the design itself set far too small. Changing a declared limit needs a
    written amendment and an independent review, which is under way.
- **Batch 3:** it missed its freeze date during the 24-28 Oct gap. The independent ruling says the date was a target: its
  own rules push the later windows back, and nothing is rescued by moving goalposts. A data-collection step that had never
  been switched on was reviewed and switched on tonight.
- **Batch 5:** the reviewer's code check found five defects before its next data fetch. For example, a failed download could
  be recorded as finished. All five are fixed and waiting for a re-check.
- **LT13 (new live test):** the fee probe showed that Polymarket switched about 26,000 markets to zero fees on 20 Oct. That
  breaks the fee-charging comparison, so that idea is withdrawn before counting, exactly as its pre-declared rule said. The
  second idea continues alone. A reviewer is also checking whether the same fee change affects the frozen LT12 design.
- **Batch 7's counting check** is queued with its inputs pinned, due before 3 Nov. **Round 19 of original ideas** is being
  written.
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
   on 30 Oct 00:38 UTC+1 (each file checked against GitHub first). Nothing that a current or planned job reads was touched.

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
| Server disk | 100 GB disk, 33 GB free (30 Oct 00:40 UTC+1); data 36 GB after clearing 11 GB of archived restore copies; job limit 50 GB, collection cap 55 GB, 4 GB free-disk stop unchanged. |
| Server size | **2 CPUs, 12 GB RAM since 22 Oct** (free tier). A second free server (1 CPU, 6 GB, 100 GB) is being requested automatically every 10 min until Oracle has capacity. |
| Mac | No background jobs. |

## 6. Manual pause and stop
- **Claude autopilot (Mac):** `python3 scripts/autopilot/autopilot.py pause` / `resume` / `stop` / `status`.
- **Pause research jobs:** `ssh oracle '~/arepo/.venv/bin/python ~/arepo/scripts/oracle/queue_worker.py pause'`. Use `resume` to undo, or `stop` to also halt the running job.
- **Status:** the same command with `status`.

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [queue](research_lab/queue/README.md) · [mission](research_lab/AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md)
