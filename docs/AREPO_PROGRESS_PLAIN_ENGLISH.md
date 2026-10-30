# AREPO — Plain-English Progress

**Last updated:** 2026-10-30 06:02 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Two more live tests have frozen designs tonight (more prospective tests, as you asked):**
  - **LT13** (listing batches): frozen, coded, independently checked. A flaw in the frozen text that would have failed it
    by construction was found and fixed by a small reviewed amendment. Counting check after 17 Nov.
  - **LT14** (new, round 19): the economic check beside the signal engine's accuracy. Do the engine's strongest calls move
    by more than a round-trip trading cost? Frozen this morning with the engine model pinned; its counting-check code is
    being written. The final check caught two more flaws of the same "fails by construction" kind before the freeze.
- **M1, a pre-registered measurement (new):** after a market's outcome is formally proposed, how big is the remaining
  discount compared with the risk of reversal and the cost? Two reviews done; a light counting step is queued; the freeze
  is due before 22 Nov. The reviewer showed the result will very likely be "coarse" (too few events for a tight bound), and
  that is written down in advance. A second measurement (M2, the overdue favourite) is being drafted.
- **Round-19 ideas counted:** by rules written before the count, three went forward (M1, M2, LT14), one fell short and one
  engine idea was dropped. Two small defects in that counting job were found later and recorded openly; the affected test
  keeps its own binding count.
- **Unblocked after independent reviews:** batch 9 (a disk limit; and part P is "not testable" because every candidate was
  already used by an earlier test), batch 10 (a wrong file setting caught before it ran), batch 5 (the "too rare" result is
  now recorded properly; its next fetch is queued).
- **Batch 3:** development window ends 3 Nov (its new data step started tonight). **LT12:** the 20 Oct fee change is a
  disclosure, not a breach.
- **Server:** the long model run (MC1) pauses and resumes in slices; the batch 7 count (due before 3 Nov) runs at the next
  slice break.
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
