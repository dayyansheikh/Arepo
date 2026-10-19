# AREPO — Plain-English Progress

**Last updated:** 2026-10-19 05:38 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Autopilot:** a session has been running since about 05:05 UTC+1 (19 Oct). The previous one stopped about 03:05
  with two pieces of work unsaved. This session finished both, had them reviewed, and saved them.
- **Server:** it had run out of ready work overnight. Starting after its 06:30 UTC+1 quiet window, it has:
  - **Batch 11's ID check, rebuilt.** The old version read the full list of about 4 million markets instead of the
    roughly 14,000 actually sampled. An independent review accepted the fix. It takes about 1-2 hours; batch 11's
    downloads (about 10-15 hours) then follow automatically.
  - Two short connection checks for batch 13.
- **Batch 13 (where makers lose money; touch-versus-end crypto markets):** the review found faults in the
  final-decision code (the second-stage multiple-testing step could never add a pass, as the design intends, and one
  stalled path could wait forever). They are fixed and re-checked. Next is a blind check of its market labeller, then
  its data jobs.
- **Batch 14 (Wikipedia edit bursts; speech mentions):** the review found 18 code faults, for example that the live
  part would have tracked nothing. They are being fixed now. Nothing has run.
- **Batch 15 (US election night, 3 Nov):** the design was challenged and revised:
  - The leaderboard idea was withdrawn before any data was seen: the archived pages have no usable table.
  - Election night now compares states only within the same poll-closing hour, so a national swing cannot fake a
    result.
  - Two independent helpers are compiling, from saved 2022/2024 sources (no 2026 polls or prices), which way each
    state's late count usually moves. The code is being written.
  - **It must be frozen by 1 Nov midday UTC, or it is recorded as "not run".**
- **New ideas, round 7 (Fable, as you asked):** 13 new ideas. Top ones: crypto "dip to" markets priced above
  "reach" markets in the same event (a hedging premium), and outer buckets of economic-data markets overpriced just
  before the release. A design for the ideas that can be tested on data already on the server is being drafted
  (batch 16).
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
| Server disk | 100 GB disk, 58 GB free (measured 18 Oct 20:49 UTC+1); collection cap 45 GB, 4 GB free-disk stop unchanged. |
| Server size | 1 CPU, about 5.6 GB RAM. A second free server (1 CPU, 6 GB, 100 GB) is being requested automatically every 10 min until Oracle has capacity. |
| Mac | No background jobs. |

## 6. Manual pause and stop
- **Claude autopilot (Mac):** `python3 scripts/autopilot/autopilot.py pause` / `resume` / `stop` / `status`.
- **Pause research jobs:** `ssh oracle '~/arepo/.venv/bin/python ~/arepo/scripts/oracle/queue_worker.py pause'`. Use `resume` to undo, or `stop` to also halt the running job.
- **Status:** the same command with `status`.

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [queue](research_lab/queue/README.md) · [mission](research_lab/AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md)
