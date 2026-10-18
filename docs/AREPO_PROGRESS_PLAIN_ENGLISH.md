# AREPO — Plain-English Progress

**Last updated:** 2026-10-18 20:56 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Autopilot:** a new session started at about 20:49 UTC+1 (18 Oct).
- **Server:** idle apart from live collection since about 02:00 UTC+1. Batch 8's holder snapshots wait, as designed,
  for their start on 21 Oct; most other downloads wait for the 22 Oct cut-off. Batch 11's downloads go on next.
- **Done this session:** round 6 of original ideas is saved (13 new ideas, CH118-CH130; ideas only, nothing tested).
  Batch 11's families P and A now fit the per-family checksums (all 145 tests pass).
- **In progress:**
  - **Batch 11:** an independent re-check of the 10 fixes and of the new P/A code. If it passes, its small test
    download and then about 10-15 hours of downloads go on the server.
  - **Batch 12:** coding of the two families that use data we already have (word-mention baskets, stale horizons).
  - **Batch 13 (new):** being designed from round 6. It asks where makers lose money, by type of market, and
    whether "will it touch X" markets are priced as if they were "will it end above X".
- **Second free server:** still "out of host capacity" at Oracle (last check 20:50 UTC+1); it retries every 10 min.

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
- **Kalshi lead:** the strongest historical predictor; live test (E009/E010) is analysed after 3 Nov.

| Leading candidates | Awaiting confirmation | Confirmed edge |
|---|---|---|
| Kalshi lead; order flow; book/liquidity interactions (being tested) | E009/E010 (3 Nov), E011 (11 Nov) | **None** |

## 5. Infrastructure
| Item | State |
|---|---|
| Server disk | 100 GB disk, 58 GB free (measured 18 Oct 20:49 UTC+1); collection cap 45 GB, 4 GB free-disk stop unchanged. |
| Server size | 1 CPU, about 5.6 GB RAM. A second free server (1 CPU, 6 GB, 100 GB) is being requested automatically every 10 min until Oracle has capacity. |
| Mac | No background jobs. |

## 6. Manual pause and stop
- **Claude autopilot (Mac):** `python3 scripts/autopilot/autopilot.py pause` / `resume` / `stop` / `status`.
- **Pause research jobs:** `ssh oracle '~/arepo/.venv/bin/python ~/arepo/scripts/oracle/queue_worker.py pause'`. Use `resume` to undo, or `stop` to also halt the running job.
- **Status:** the same command with `status`.

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [queue](research_lab/queue/README.md) · [mission](research_lab/AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md)
