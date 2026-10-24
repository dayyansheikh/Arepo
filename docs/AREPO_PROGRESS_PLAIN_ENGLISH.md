# AREPO — Plain-English Progress

**Last updated:** 2026-10-24 04:58 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Early 24 Oct: batch 8's "last-minute certainty" test (crypto Up/Down vs Binance) is closed as not testable.** Its
  pre-declared first step checked whether the historical order-book archive covers enough of the markets: it needed 90% of
  sampled market-days and found 73%. So, as written in advance, the test stops there. It is counted, no price or outcome was
  read, and there is no retry (the one allowed retry was this run).
- **Fixed a second silent stall:** one background extraction for batch 4 had stopped at a small size limit since 18 Oct.
  The limit is raised (storage only; no rule changed). Nothing is lost; it catches up over the next passes.
- **Being fixed now (in parallel):** LT11's last six review fixes, then it merges; batch 9's market-overlap check (failed on the
  same ID-format problem batch 8 hit, so the same reviewed fix is being reused); LT12's code (two tests: "the mirror" and "the
  farmed half"), then its independent code check; and a fresh round of original ideas (round 18).
- **Server:** the long model run MC1 is working through its folds; live collectors healthy.
- **Seven registered live tests** are collecting or waiting to collect (E009/E010, E011, E012-E014, E015, E022, E026).
  Single analyses: E009/E010 (3 Nov), E011 (11 Nov), E012-E014 (13 Nov), E015 (15 Nov), E022 (17 Nov), E026 (6 Dec).
- **Planned live-test families:** LT9 (frozen, code done, data seal after 12 Nov), LT10 (frozen, code done, counting checks after
  3 Nov), LT11 (frozen, final code fixes), LT12 (frozen, code in progress). LT5-LT8 closed at their counting checks with no test.
- **Copy-skilled wallets (E026):** registered; collection starts 25 Oct (phone note then).
- **Security check (23 Oct):** no confirmed holes; 5 things to check (`docs/security/AUDIT_2026-10-23_RUN1.md`); most important:
  confirm Render has a strong AUTH_SECRET.
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

8. **URGENT (needed within about 3 days): let Claude clear finished restore copies on the server.** 24 Oct 04:37 UTC+1:
   **37 of 40 GB**, growing about 1 GB a day; at 40 GB jobs (including live collectors' extracts) start refusing. Restore
   copies are hash-checked copies of data that is safe in the archive, made so a job could re-read old files. **Measured
   list (24 Oct, read-only):** batch 18 `cb18_census/restore` 4.9 GB (batch 18 closed), LT4 `live_tests4_census/restore`
   3.0 GB, LT6 1.2 GB, LT5 0.8 GB, LT3 0.3 GB: **10.2 GB in total, and no queued or planned job reads any of them**
   (checked against every job and draft). Batch 17's 0.9 GB copy is still needed and stays. The safety hook rightly stops
   Claude from deleting anything in the data folder. **Decision needed:** reply "approve restore-copy clearing" (Lab
   inbox) to allow one session that re-checks each copy against the archive, then deletes only these five folders.

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
