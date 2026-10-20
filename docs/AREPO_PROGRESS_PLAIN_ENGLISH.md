# AREPO — Plain-English Progress

**Last updated:** 2026-10-20 19:30 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Autopilot:** a new session started at 18:38 UTC+1 (20 Oct). The 13:25 session had stopped at about 14:01 UTC+1.
- **Server queue was idle at 18:38 again.** Cause: the server's copy of the code was 15 commits behind, so the jobs
  promoted this afternoon never reached it (most likely a deploy from a side branch overwrote the newer one). Fixed:
  the current code was sent at 18:40 and the work restarted. From now on, deploys go only from the main research branch.
  Two smaller server faults were fixed too: a restore job could not find the GitHub tool, and one price job needed more memory.
- **Live tests: E012-E014 are now REGISTERED** (18:51 UTC+1). The last server dry run passed (memory 584 MB of
  960 MB allowed) and the independent check passed, with one correction to the wording: the server only lists open
  markets, so a market that closes or resolves shows up as "gone from the list", which the attrition rule already counts.
  Collection starts **22 Oct 01:00 UTC+1** and runs to 12 Nov; the single analysis comes after 13 Nov.
  That makes **4 registered live-test groups** (E009/E010, E011, E012-E014), 3 of them collecting now.
- **Next live tests:**
  - LT3 (E015-E019): the first counting check is done. E015 (quote-only versus traded moves) passed. E017 (volume surges
    without a price move) and E019 (ladder breadth) were dropped before registration: too few cases in 21 days to detect
    the minimum effect. Dropped tests are not counted. E016/E018 wait for one more check (before 23 Oct); target start 24 Oct.
  - LT4 (E020-E024, new from round 10 of ideas): designed and coded. The independent challenger asked for changes to three
    of the five tests (one could be distorted by the minimum price step, one would mostly measure bid/ask bounce, one needs
    a better comparison within each market); the other two were accepted with small changes. The revisions are being made.
    Target start 26 Oct, after LT3 is registered.
- **Round 10 of ideas** (11 new ideas, CH169 onward) is saved. They cover order arrivals versus cancellations, how old a
  price move is, and liquidity that is displayed but cannot actually be traded against.
- **Batch 12, options part (CB12-O): closed, not testable.** Its readiness check needed dividend dates for an index fund
  (SPY), and the free source has none. By the rule written in advance, it counts as 2 tests that found nothing. We did
  not swap in another source after the check failed, because that would mean changing the rules to get a pass.
- **Batch 17:** its rules are final (an independent check made three of them stricter before any data exist). The rules
  were fixed at 19:27 UTC+1 today, so its test window starts on **26 Oct**. The code passed its main check with 7 fixes,
  all applied; a last check on those fixes is running. Then a reproduction run on the server.
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
