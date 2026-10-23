# AREPO — Plain-English Progress

**Last updated:** 2026-10-23 18:35 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **This evening (23 Oct):** the **LT11 design is frozen** (three ideas from round 16: do price moves backed by more money keep
  going; does a neg-risk market's spread widen after its sister markets' bids rise; do spreads widen when a rewarded market first
  crosses 10c or 90c). It passed the challenger review, a re-check and a final check; nothing was loosened. The venue's reward
  page was re-read at the freeze and confirms the documented rule (one-sided quotes score only between 10c and 90c). Its code is
  being written now, then an independent code check. Counting checks run after 7 Nov; if any test survives, collection from 18 Nov.
- **Batch 8, "last-minute certainty" in daily crypto Up/Down markets: no markets left to study.** The rule that removes anything
  related to earlier samples removed every one of the 783 candidates, because they all belong to a few daily series that earlier
  samples had touched. No price or outcome was read. An independent reviewer is deciding whether a declared variant (ignore the
  series link, keep the per-market exclusions) is scientifically fair. **Ruling: allowed, with 7 conditions** (it gets one
  try only and is counted once). The change is written and its check asked for 4 small fixes, which are being made.
- **New ideas round 17 is done** (10 ideas). The three best live-test candidates: "the mirror" (a two-option event has two
  order books for one question: does one book's spread change predict the other's?), "the farmed half" (in a multi-option event
  only some options pay market-maker rewards: do the unpaid ones react differently to the same shock?) and "the fee as the price
  of urgency". Their author expects about a 50% chance that none survives its counting check. A counts-only map of how many
  usable cases exist is being built now and runs on past data, so the design can start soon.
- **Your 23 Oct message ("why have you stopped?"): it had not stopped.** Sessions kept running but were cut off by the usage limit
  before writing their summary; the Lab board now shows how long such a session worked and its last progress note.
- **Server:** the model run MC1 is working through its folds (healthy); the live collectors are healthy.
- **Seven registered live tests** are collecting or waiting to collect (E009/E010, E011, E012-E014, E015, E022, E026).
  Single analyses: E009/E010 (3 Nov), E011 (11 Nov), E012-E014 (13 Nov), E015 (15 Nov), E022 (17 Nov), E026 (6 Dec).
- **Planned live-test families:** LT9 (frozen, code done, data seal after 12 Nov), LT10 (frozen, code done, counting checks after
  3 Nov), LT11 (frozen today, code in progress). LT5-LT8 closed at their counting checks with no test (nothing counted).
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
   03:10 UTC+1: the data folder is at **34 of 40 GB** and grows about 1 GB a day, so jobs (including the LT2 live
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
