# AREPO — Plain-English Progress

**Last updated:** 2026-10-21 00:21 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Autopilot:** a new session started at 23:39 UTC+1 (20 Oct). The 18:38 session stopped at about 21:40 UTC+1.
- **Two archive restores were failing; fixed.** They need an index of what each nightly backup holds, and that index
  had not been refreshed since 15 Oct. It is now refreshed for every backup up to 20 Oct, and both restores are back in
  the queue (the LT3 input restore and the batch 17 reproduction inputs). The LT3 counting check that follows still has
  time before its 23 Oct deadline.
- **Live tests:** 4 registered groups (E009/E010, E011, E012-E014); E012-E014 start collecting **22 Oct 01:00 UTC+1**.
  - **LT3 (E015, E016, E018):** the independent reviewer looked again and found that one safety check (comparing a
    market with itself at other times) cannot work as designed, however it is scaled. Ruling: it stays as information only,
    and these tests use the same reshuffling check as the others. That change is made and under final review; then a
    large size check (2,000 simulated worlds) runs on the server. If any required scenario fails, LT3 is not registered
    and is not redesigned again. Target start 24 Oct, or the next allowed day.
  - **LT4 (now E020-E022):** review fixes done and checked; its counting checks are queued on the server behind two
    archive restores. It registers after LT3.
- **Batches 12-15 tonight:** batch 12's speech-mention and earthquake parts closed (failed their readiness checks set in
  advance: too little power; too few independent events), counted as 3 tests that found nothing (batch 12 total: 5 of 10).
  Batch 14's Wikipedia part failed its blind name-matching check (38 of 56 articles were the right person; 90% needed) and
  has too few markets anyway (94; 150 needed), so it will close as "not testable", counted. Batch 13's price download and
  batch 15's exclusion list are queued.
- **Note:** an interactive session queued a 6-hour model run that runs alone on the server, so other jobs pause while it runs.
- **Batch 17:** code frozen; its reproduction run waits for the restore above. Test window starts **26 Oct**.
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
| Kalshi lead; order flow; book/liquidity interactions (being tested) | E009/E010 (3 Nov), E011 (11 Nov), E012-E014 (13 Nov) | **None** |

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
