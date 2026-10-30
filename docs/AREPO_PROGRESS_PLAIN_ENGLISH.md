# AREPO — Plain-English Progress

**Last updated:** 2026-10-30 03:13 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **New ideas (round 19):** eight original ideas are written up. The lead one: after someone formally proposes how a
  market resolved, does the winning side still trade at a discount worth more than the small risk the proposal is
  overturned? A reviewer agreed that such questions can be run as pre-registered *measurements* (a number with an error
  bar, frozen in advance, never called a finding). One of the eight needs redesign because it accidentally used
  information from the future. A light counting job is being built to decide which ideas go forward.
- **Batch 9 unblocked:** the size limit that stopped one data step was reviewed. The reviewer confirmed it limits disk space
  only, was set before any results were seen, and that raising it changes nothing scientific. The step is queued again
  from scratch.
- **LT13 (new live test):** a full independent re-check said "go, with changes". The changes are made, and a final check
  before freezing the design is running.
- **LT12 (frozen live test):** Polymarket's 20 Oct fee change moved about 1,800 markets from "sports" to "non-sports" under
  LT12's fixed rule. The review says this is a disclosure, not a breach: the whole LT12 window comes after the change, so
  the rule applies the same way throughout.
- **Batch 3:** its new data step ran for the first time at 00:31 tonight, so its development window now ends on 3 Nov
  (by its own rule).
- **Batch 5:** the code re-check passed with one item. With zero usable families found, the count must record the declared
  result "too rare to test", not "data missing". That fix is being made.
- **Server:** the long model run (MC1) is working through its folds. When it pauses (about 06:00 UTC+1), the batch 7 count
  (due before 3 Nov) and the batch 4 trade fetch get their turn.
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
