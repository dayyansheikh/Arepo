# AREPO — Plain-English Progress

**Last updated:** 2026-10-24 00:22 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Tonight (23-24 Oct): LT11's code check found real problems, now being fixed.** The independent reviewer found that the
  simulated "fake data" worlds, used to check that the tests don't raise false alarms, were built more simply than the frozen
  design says. That would have made the safety check too easy to pass. Every fix is in the code; the frozen design is unchanged.
  A second check follows. Counting checks after 7 Nov; collection from 18 Nov if a test survives.
- **LT12 design is frozen (23 Oct, late evening).** Two tests: "the mirror" (in a two-option event, does one order book's
  spread change predict the other's?) and "the farmed half" (when only some options in an event pay market-maker rewards, do
  the unpaid ones react differently to the same shock?). The third idea, the fee, was removed by the challenger. It passed a
  challenger review, a re-check and a final check; nothing was loosened. Its code is being written now. Counting checks on
  7-17 Nov data; collection 10-31 Dec if a test survives. Its author's honest estimate: about a 60% chance that neither survives.
- **Batch 8, "last-minute certainty" (crypto Up/Down):** the allowed retry found 665 markets. The order-book coverage check is
  queued behind the long model run MC1.
- **Fixed a silent stall:** two background data extractions (for batches 4 and 5) had been refusing to run since 17 Oct
  because of an old disk limit. Raised to the standard limit. Nothing was lost (the server still holds all the raw data); it
  is only a delay.
- **Your 23 Oct message ("why have you stopped?"): it had not stopped.** Sessions kept running but were cut off by the usage limit
  before writing their summary; the Lab board now shows how long such a session worked and its last progress note.
- **Server:** the model run MC1 is working through its folds (healthy); the live collectors are healthy.
- **Seven registered live tests** are collecting or waiting to collect (E009/E010, E011, E012-E014, E015, E022, E026).
  Single analyses: E009/E010 (3 Nov), E011 (11 Nov), E012-E014 (13 Nov), E015 (15 Nov), E022 (17 Nov), E026 (6 Dec).
- **Planned live-test families:** LT9 (frozen, code done, data seal after 12 Nov), LT10 (frozen, code done, counting checks after
  3 Nov), LT11 (frozen 23 Oct, code being fixed after its check), LT12 (frozen 23 Oct, code in progress). LT5-LT8 closed at their counting checks with no test (nothing counted).
- **Copy-skilled wallets (E026):** registered; collection starts 25 Oct (phone note then).
- **Security check (23 Oct):** no confirmed holes; 5 things to check (`docs/security/AUDIT_2026-10-23_RUN1.md`); most important:
  confirm Render has a strong AUTH_SECRET.
- **Honest pattern:** most planned tests die at the counting stage, before any outcome data is read. That is the checks working
  as designed.
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

8. **NOW TIME-SENSITIVE (needed by about 27 Oct): let Claude clear finished restore copies on the server.** Measured 23 Oct
   03:10 UTC+1: the data folder was at 34 of 40 GB, **36 of 40 GB at 23:30**, and grows about 1 GB a day, so jobs (including the LT2 live
   collector) would start refusing around 29 Oct. Batch 18's 4.9 GB copy is finished now and LT8 does not use it. Restore copies are
   hash-checked copies of data that is safe in the archive, made so a job can re-read old files. About 9 GB of them
   are finished with or soon will be (measured 22 Oct: batch 18 4.9 GB finished now; LT4 3.0 GB and LT3 0.3 GB after
   LT6's flow count today; LT5 0.8 GB after its count today; LT6 1.2 GB after its counts). Jobs stop at a
   40 GB data limit (**33 GB on 22 Oct**, and LT7's restore will add more), so they will need clearing within days. The safety hook rightly stops
   Claude from deleting anything in the data folder. **Decision needed:** approve a short clearing session for these
   copies only (each one listed and checked against the archive first). Batch 17 no longer needs this: it now writes
   to a fresh folder instead.

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
| Server disk | 100 GB disk, 38 GB free (measured 22 Oct 06:20 UTC+1); collection cap 45 GB, 4 GB free-disk stop unchanged. |
| Server size | **2 CPUs, 12 GB RAM since 22 Oct** (free tier). A second free server (1 CPU, 6 GB, 100 GB) is being requested automatically every 10 min until Oracle has capacity. |
| Mac | No background jobs. |

## 6. Manual pause and stop
- **Claude autopilot (Mac):** `python3 scripts/autopilot/autopilot.py pause` / `resume` / `stop` / `status`.
- **Pause research jobs:** `ssh oracle '~/arepo/.venv/bin/python ~/arepo/scripts/oracle/queue_worker.py pause'`. Use `resume` to undo, or `stop` to also halt the running job.
- **Status:** the same command with `status`.

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [queue](research_lab/queue/README.md) · [mission](research_lab/AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md)
