# AREPO — Plain-English Progress

**Last updated:** 2026-10-21 05:07 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Autopilot:** a new session started at 04:32 UTC+1 (21 Oct), right after the usage limit reset. Your interactive
  session hit the limit at about 01:00 UTC+1, so several of its helpers stopped mid-task; this session picks up the
  research ones (not the website/board changes you asked for at 01:11).
- **Fixed: the E012-E014 live collector was being held up.** During the server's nightly quiet window (03:45-06:30 UTC+1),
  a bigger job waiting at the front of the queue blocked the small collector, which is allowed to run then. That would
  have made its daily 03:31 freeze late. The queue now lets small allowed jobs pass; the collector started at 04:36.
- **LT3 is down to one test (E015).** The last counting check (order-flow data, counts only) showed too little usable
  data for E016 and E018 (for example 51,828 usable market-periods where 60,000 were required). By the rules set in
  advance, both are dropped and not counted. LT3 now registers E015 alone (quote-only versus traded price moves).
  An independent pre-registration review said "ready, with fixes"; the fixes are made and checked (the analysis now
  computes only E015, and the dropped tests are no longer collected, so a fault there cannot hurt E015). Because the
  code changed, the large size check runs once more; it must give exactly the same safety numbers as the first run.
  A test run on the server is under way. Target start 24 Oct (registration by the end of 22 Oct).
- **Copy-skilled-wallets live test:** the design helper stopped at the usage limit with code written but no design
  document. This session restarted it; you will get a phone note when the design is done.
- **Model run (MC1):** fixed. It was killed twice by the server running out of memory while it read its data table back.
  It now reads the table column by column with identical numbers (estimated peak about 4 GB instead of over the limit).
  It is queued to run after the current size check and must finish before the E012-E014 collection starts on 22 Oct.
- **Queue rule:** small live-collector jobs can now run beside a big "run alone" job, so registered live tests never wait.
- **Signal engine:** the experiments side now hands it a list of 12 candidate signal families from replicated results
  (`signal_engine/CANDIDATES.md`), each with its source and the date until which it must stay hidden (live tests running).
- **New ideas:** creative round 11 (Fable, deep effort) restarted after the usage limit cut it off.
- **LT4 (E020-E022):** its counting checks are queued on the server. **Batch 17:** reproduction run queued; window 26 Oct.
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
