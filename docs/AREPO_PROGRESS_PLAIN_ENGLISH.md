# AREPO — Plain-English Progress

**Last updated:** 2026-10-17 21:07 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Autopilot:** this session started at about 20:32 UTC+1 and found the server with **no job ready to run**. It is
  busy again: batch 4's series download is running, and six more jobs are queued behind it.
- **Fixed and sent to the server:**
  - The ML development run's out-of-memory crash. Same numbers, checked by tests.
  - Batch 4's series download had stopped on its own 1 GB size limit. The limit is now 4 GB and it is resuming.
  - Batch 6's old 14 GB disk limit (now 40 GB, like every other job).
  - A batch-5 download that had been queued 10 days too early.
- **New results (all "plumbing" checks, no edge claims):**
  - **Batch 5, "consistency of bucketed date markets": almost certainly a null.** The family finder, whose rules were
    fixed in advance, found 0 usable families. Most had an "Other" or "No ..." bucket, which the rules exclude.
  - **Batch 9's small download test failed on a technicality.** Every blockchain receipt it read checked out. It just
    sampled too few (8 and 18, where it needed 20). A corrected test that keeps sampling until it has 20 is being written.
  - **Batch 8's holder-data test failed one check.** About 80% of markets have no open-interest number. We are checking
    whether that simply means "zero"; only if it does will a reviewed rule change be proposed.
- **Batch 10** (crypto options vs Polymarket price ladders; bounces at round prices like 0.50): the independent check
  found a hidden look-ahead that would have flattered the round-price test. It is fixed and recorded as a design
  amendment. Its small download test is queued.
- **Batch 11 designed:** (1) can we predict how long resolution takes after a market ends (only 37 addresses can
  propose outcomes)? (2) do political favourites 1-3 months out win more often than priced? (3) do price moves that come
  with no Wikipedia attention spike keep drifting? A challenger is now trying to break the design.
- **Round 5 of new money ideas** is being written (Fable, max effort).
- **Second free server:** still waiting for Oracle capacity. The server re-requests it every 10 min.

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
| Server disk | 100 GB disk, 58 GB free (17 Oct 20:32 UTC+1); collection cap 45 GB, 4 GB free-disk stop unchanged. |
| Server size | 1 CPU, about 5.6 GB RAM. A second free server (1 CPU, 6 GB, 100 GB) is being requested automatically every 10 min until Oracle has capacity. |
| Mac | No background jobs. |

## 6. Manual pause and stop
- **Claude autopilot (Mac):** `python3 scripts/autopilot/autopilot.py pause` / `resume` / `stop` / `status`.
- **Pause research jobs:** `ssh oracle '~/arepo/.venv/bin/python ~/arepo/scripts/oracle/queue_worker.py pause'`. Use `resume` to undo, or `stop` to also halt the running job.
- **Status:** the same command with `status`.

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [queue](research_lab/queue/README.md) · [mission](research_lab/AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md)
