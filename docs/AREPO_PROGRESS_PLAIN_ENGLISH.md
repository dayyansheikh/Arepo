# AREPO — Plain-English Progress

**Last updated:** 2026-10-22 17:30 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Seven registered live tests** are collecting or waiting to collect (E009/E010, E011, E012-E014, E015, E022, E026).
  Single analyses: E009/E010 (3 Nov), E011 (11 Nov), E012-E014 (13 Nov), E015 (15 Nov), E022 (17 Nov), E026 (6 Dec).
- **LT7 (five planned tests from round 12): second reviewer ruling today.** A follow-up count (counts only, no outcomes)
  found that about 12% of markets flip between "reward programme listed" and "nothing listed" within the same day. That
  points to the data source sometimes leaving the field out, so "nothing listed" cannot always mean "no programme". The
  reviewer ruled that a market counts as rewarded if it was listed at any capture in the previous 24 hours, using only
  earlier captures (never later ones). The code change is written and passed its independent re-check (a test also caught a
  bug that would have stopped the rule from ever applying; fixed). The first counting check (volume and wording, which
  reads no reward field) runs first; the two reward-dependent checks follow it. All checks must finish before 28 Oct.
- **LT8 (three planned tests from round 13):** the code fixes from its review are saved. Its re-check waits for the LT7
  code change, because LT8 reuses LT7's counting code.
- **Model run (MC1)** hit its 6-hour time limit without running out of memory. It is parked; the next step is to add
  progress timing so a fixed attempt can be sized from measurements.
- **Cross-venue twins (batch 16, K):** the size count passed. It can only become a test in a later batch, and only if a
  blind check of 100 pairs finds at least 90 true twins.
- **Batch 7 and batch 8:** the seal for batch 7's text data is committed; its fetch code passed review and started, and its counting job follows from 24 Oct.
  Batch 8's crypto Up/Down part has started its data jobs.
- **New ideas round 14** is being written, aimed at ideas that survive the counting checks.
- **Copy-skilled wallets (E026):** registered; collection starts 25 Oct (phone note then).
- **Honest pattern:** most planned tests die at the counting stage, before any outcome data is read. That is the checks
  working as designed.
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

8. **NEW (21 Oct, not urgent): let Claude clear finished restore copies on the server.** Restore copies are
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
