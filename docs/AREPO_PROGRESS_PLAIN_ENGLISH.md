# AREPO — Plain-English Progress

**Last updated:** 2026-10-28 12:17 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Back after a 4-day gap (24-28 Oct):** Claude's weekly usage limit was reached on 24 Oct and reset on 28 Oct. The server
  kept collecting the whole time; the live tests were not interrupted.
- **Your message (27 Oct) on "Forecasting gain near market close":** it is already in its live test (E014, collecting since
  22 Oct). It finishes on its registered date: collection ends 12 Nov and the single analysis runs after 13 Nov. Ending it
  early would break the pre-registered design, so it stays as planned. The Lab card now shows this.
- **Copy-skilled wallets (E026):** collection started on 25 Oct as registered and is running normally (phone note sent).
- **Storage fix today:** the data folder reached 38.9 of its 40 GB per-job limit, so the live collectors would have started
  skipping within about two days. The limits are raised to 50 GB for jobs and 55 GB for collection (the disk has 30 GB
  free). Storage only; no rule changed. Clearing restore copies (item 8) is still the real fix.
- **Batch 7:** its counting check looked for a "geopolitics" label that the data never contains. An independent review
  confirmed the fix: find those markets by their question text, as the design's own rule says. A small text-lookup job is
  queued; the old data window is held on the server a few extra days so the check can still run.
- **New live test on the way (LT13):** the map for round 18's two best ideas was large enough to draft LT13. The independent
  challenger said go ahead with changes: build the counting check first, and run a small probe of the fee labels first. Honest
  caveat: the planning numbers suggest both ideas may well fail their counting checks. A third idea failed and is dropped.
- **Batch 4** can move again: its data extract caught up, so its next data step is released. A fresh round 19 of original
  ideas is being written.
- **LT12** passed its independent code check and is merged. **Batch 9** moved to its next data steps after a review.
- **The long model run MC1** hit a memory limit; a lower-memory version that gives identical numbers is queued (it restarts).
- **Seven registered live tests** are collecting or waiting: single analyses E009/E010 (3 Nov), E011 (11 Nov), E012-E014
  (13 Nov), E015 (15 Nov), E022 (17 Nov), E026 (6 Dec). LT9-LT12 are frozen designs on their way to registration.
- **Honest pattern:** most planned tests die at the counting or data-coverage stage, before any outcome data is read. That is
  the checks working as designed.
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

8. **URGENT: let Claude clear finished restore copies on the server.** 28 Oct: **38.9 GB** of data, growing about
   0.5 GB a day. The job limits were raised from 40 to 50 GB today to keep live collectors running, so this buys about
   three weeks, not a fix. Restore copies are hash-checked copies of data that is safe in the archive. **Measured list
   (24 Oct, read-only):** batch 18 4.9 GB, LT4 3.0 GB, LT6 1.2 GB, LT5 0.8 GB, LT3 0.3 GB: **10.2 GB, and no queued or
   planned job reads any of them**. Batch 17's 0.9 GB copy stays. **Decision needed:** reply "approve restore-copy
   clearing" (Lab inbox) to allow one session that re-checks each copy against the archive, then deletes only these five.

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
| Server disk | 100 GB disk, 30 GB free (28 Oct 11:08 UTC+1); data 38.9 GB; job limit 50 GB, collection cap 55 GB, 4 GB free-disk stop unchanged. |
| Server size | **2 CPUs, 12 GB RAM since 22 Oct** (free tier). A second free server (1 CPU, 6 GB, 100 GB) is being requested automatically every 10 min until Oracle has capacity. |
| Mac | No background jobs. |

## 6. Manual pause and stop
- **Claude autopilot (Mac):** `python3 scripts/autopilot/autopilot.py pause` / `resume` / `stop` / `status`.
- **Pause research jobs:** `ssh oracle '~/arepo/.venv/bin/python ~/arepo/scripts/oracle/queue_worker.py pause'`. Use `resume` to undo, or `stop` to also halt the running job.
- **Status:** the same command with `status`.

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [queue](research_lab/queue/README.md) · [mission](research_lab/AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md)
