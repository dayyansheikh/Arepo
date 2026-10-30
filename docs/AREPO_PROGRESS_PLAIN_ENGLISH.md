# AREPO — Plain-English Progress

**Last updated:** 2026-10-30 05:24 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **LT13 (new live test) is designed, frozen and coded.** Its counting-check code passed an independent check. That check
  found a real flaw in the frozen text: three controls that always add up exactly, which would have made every fit fail and
  the test drop out by construction. A small reviewed amendment removed the redundant one. The maths shows this changes no
  result, threshold or date, and the amendment is recorded openly. The counting check starts after 17 Nov.
- **New ideas (round 19) counted:** the light counting job ran this morning (counts only, nothing tested). By the rules
  written before it ran, three ideas go forward to written designs:
  - the "carry" after a market's outcome is formally proposed (about 820 proposals a day), as a pre-registered
    *measurement* (a number with an error bar, never called a finding);
  - the "overdue favourite" past its end date (about 160 a day), also a measurement, after a redesign the reviewer asked for;
  - LT14, an economic check of the signal engine's own top picks against trading costs (about 175 candidates a capture).
  - One idea (the market close by rule type) fell short of its line (20 a day, needed more than 30) and is not drafted.
  - One signal-engine idea was dropped at its own kill line; another passed.
  - The first two drafts are being written now.
- **Batch 9, part P is not testable:** every one of its 1,235 candidate markets had already been used by an earlier test,
  so the no-reuse rule removes them all. An independent review confirmed the rule worked as written. It is counted as
  "not testable", which is not a null result.
- **Three stuck batches unblocked, each after an independent review:**
  - Batch 9: a disk-size limit set far too small was raised. The reviewer confirmed it was a size limit only, decided
    without seeing any result. The step is queued from scratch.
  - Batch 10: the review caught a wrong file in the next step's settings (the whole data frame instead of the 1,000-market
    sample the design names). Fixed before it ever ran.
  - Batch 5: one idea found zero usable market groups. The code now records the declared result, "not testable (too rare)",
    and counts it. The next data fetch is queued.
- **Batch 3:** its new data step ran for the first time tonight, so its development window ends on 3 Nov (by its own rule).
- **LT12 (frozen live test):** Polymarket's 20 Oct fee change moved about 1,800 markets from "sports" to "non-sports" under
  LT12's fixed rule. This is recorded as a disclosure, not a breach, because LT12's whole window comes after the change.
- **Housekeeping:** five out-of-date tests fixed (two of them wrote stray rows into the real trial log; none of the stray
  rows were kept).
- **Server:** the long model run (MC1) is working through its folds. When it pauses (about 05:50 UTC+1), the queued jobs
  get their turn (the batch 7 count is due before 3 Nov).
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
