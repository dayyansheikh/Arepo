# AREPO — Plain-English Progress

**Last updated:** 2026-10-22 02:59 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Autopilot:** a session started at about 01:10 UTC+1 (22 Oct).
- **LT5 (planned live tests from round 11):** its data list is sealed, but the counting job ran out of memory twice on the
  small server (it needs about 5 GB). It is set to run again after tonight's resize to 12 GB, at about 06:30 UTC+1. To keep
  its sealed data safe until then, the server now keeps price snapshots for 10 days instead of 8 (longer, never shorter;
  it goes back to 8 days after the job). Nothing was lost and nothing was counted.
- **LT6 (four planned live tests):** the code passed an independent re-check after fixes; its counting checks run
  tomorrow (22 Oct) after a data restore.
- **LT7 (new, five planned live tests from ideas round 12):** the design passed an independent challenger review after
  changes and is frozen; one idea was dropped as a near-repeat of an earlier confirmed result. Its code for the counting
  checks is written and being fixed after review. Honest planning says most of these may fail their counting checks.
- **Batch 8 result (a null, recorded):** the "worked-order footprints" idea could not be tested (its data check needed 20
  qualifying past markets, only 5 qualified); counted as one "not testable" test. Its sister idea continues.
- **Seals done tonight:** batch 4 history (about 14,000 files); batch 6's seal job is queued.
- **E012-E014 (LT2):** collecting since 01:00 UTC+1 today.
- **LT4 / E022:** size check from about 05:00-07:00 UTC+1, then registration before 25 Oct.
- **Server resize to 2 CPU / 12 GB at about 03:40 UTC+1** (your approval). After it, the model run (MC1) is re-queued.
- **Copy-skilled wallets (E026):** registered; collection starts 25 Oct (phone note then).
- **Live tests waiting for their single analysis:** E009/E010 (3 Nov), E011 (11 Nov), E012-E014 (13 Nov), E015
  (15 Nov), E026 (6 Dec).
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
   are finished with (batch 18 4.9 GB, LT4 3.0 GB, batch 17 0.9 GB; LT5's 0.8 GB after tonight). Jobs stop at a
   40 GB data limit (now about 30 GB), so they will need clearing within about a week. The safety hook rightly stops
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
