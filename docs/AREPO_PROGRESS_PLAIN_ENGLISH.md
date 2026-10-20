# AREPO — Plain-English Progress

**Last updated:** 2026-10-20 06:11 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Autopilot:** session running since 02:27 UTC+1 (20 Oct).
- **Server:** the network lane runs batch 11 attention data (round 10 of at most 12; Wikipedia look-ups, about
  1,650 of at most 3,000 done). Batch 17's four counting jobs on older data finished at 03:04-03:27 UTC+1. Its
  open-versus-close part was withdrawn before testing, as planned: trade direction could be inferred for only 93% of
  trades against the 97% required. The other batch 17 parts go ahead from 26 Oct. The compute lane is idle until the
  batch 12 options check (15:05 UTC+1). The live-trade monitor's storage limit was raised from 3 to 8 GB (reviewed),
  effective at its next restart.
- **Connection checks finished overnight:** batch 13 touch markets PASS, batch 14 Wikipedia edits PASS, batch 15
  Kalshi-first pairs PASS. Batch 14 speech clock FAILED (the speech-transcript site returned nothing), so its 2 tests
  are recorded as "not testable" (counted, no result either way).
- **Also recorded "not testable" on 19 Oct:** batch 13 maker losses (2), batch 15 election night (2), batch 16
  price grain (1).
- **Queued next on the network lane:** batch 12 speech and earthquake data, then the shared exclusion-key jobs that
  unlock batches 13-16 (one after another).
- **Live tests:** 3 running (Kalshi lead E009/E010, surprise detector E011). Four more (E012-E014) were drafted by a
  separate session that stopped last night; the autopilot ran their independent review (verdict: revise, all fixable)
  and is applying the fixes, aiming to register them before their planned start on 22 Oct 01:00 UTC+1.
- **New ideas:** round 9 is done (13 ideas, Fable). Its top ideas are being drafted as a new group of live tests (LT3,
  E015 onward), each with a fresh screening window and then a separate confirmation window.
- **Second free server:** still "out of host capacity" at Oracle; it retries every 10 min.

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
- **Stale cross-venue horizons (batch 12):** no finding; a shuffled-horizon check reproduced the pattern.
- **Kalshi lead:** the strongest historical predictor; live test (E009/E010) is analysed after 3 Nov.

| Leading candidates | Awaiting confirmation | Confirmed edge |
|---|---|---|
| Kalshi lead; order flow; book/liquidity interactions (being tested) | E009/E010 (3 Nov), E011 (11 Nov) | **None** |

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
