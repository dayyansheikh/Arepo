# AREPO — Plain-English Progress

**Last updated:** 2026-10-17 10:58 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Autopilot:** a session started at 10:19 UTC+1 and is working.
- **Server disk fixed for now.** Data had grown from 9.9 to 12.5 GB in five hours (mostly the multi-signal ML panel cache,
  which is wanted, and one batch-4 download). I cleared about 3 GB of old software-package caches on the server (they
  rebuild themselves), so 9.3 GB of disk is free, and raised the data limit for collection from 13 to 14 GB. Collection
  is not at risk; snapshot deletion of 8-day-old backed-up copies still starts on 19 Oct.
- **Two download tests failed, both for set-up reasons, not because the data source is bad:**
  - Batch 7's test picked 200 markets at random and then kept only those that ended in 2025 with real trading. Only 2
    qualified, so the test could not pass. A corrected test (markets chosen from the 33 that qualify) was independently
    reviewed and accepted with changes; it is being built.
  - Batch 8's "biggest holders" test found no markets at all: Polymarket's market list never reports each market's open
    interest (only the whole event's). Another Polymarket service does give it per market, 60 at a time. The reviewer
    accepted the fix with changes. If either corrected test fails, that part of the batch is recorded as not run.
- **Batch 3:** its counting job finished (13,510 quote-vacuum events; the selective-maker part is small, 146 independent
  groups, so its power will be low). The batch freezes after its live counting job on 25 Oct, as planned.
- **Two jobs ran out of memory** (batch 4's pilot and one of its sampling frames). The pilot is retrying with more
  memory; proper fixes for both are being written.
- **Batch 5:** a backup file it needs is being restored from the GitHub data backup to the server.
- **New idea round 4 is done** (Fable, 20 ideas). Top: (1) check whether the public trade feed even gets the buy/sell
  side right (a 2026 paper says only ~59 % agree with the blockchain record; if so, our order-flow results are understated
  about 5x); (2) market-making in daily markets settled by a public price feed (Pyth/Chainlink), where fair value is
  public; (3) parlay ("Combos") pricing. These are being turned into batch 9 designs now.
- **Batch 6 got far fewer markets than planned** (362 instead of about 4,500), because the sampling rule plus the
  exclusion of earlier samples' series removed most candidates. Nothing about outcomes was seen. A reviewed top-up
  download (same rules, more sampling windows) is being built so the test has a fair chance; it must finish before 22 Oct.
- **Batch 7's corrected download test is queued** (it passed its code check).
- **Multi-signal ML:** the real development run starts by itself once 40 unbroken 2-hourly captures exist (about 19:30 UTC+1 today).
- **Tests counted so far: 1,106** (unchanged today; smoke tests and counts are not outcome tests).

## 2. Approvals needed from you
1. ~~Automatic Claude sessions~~ **APPROVED and installed 15 Oct** (full power, your call).
   - Pause: `python3 scripts/autopilot/autopilot.py pause` (on the Mac, in the repo). Use `resume` to undo, or `stop` to
     end the running session.
   - It only runs while the Mac is awake. If you chat with me while it's working, pause it first, so two sessions don't
     edit at once.
2. **One-time usage reset (deadline Wed 21 Oct).**
   - No automatic redemption is documented, and I can't see your account page.
   - Check claude.ai/settings/usage (or `/usage`). If there's a claim/redeem button, press it around Sun 18 Oct, after this week's allowance is used.
   - A phone alert was sent 19:2x UTC+1.
3. ~~Server disk~~ **APPROVED 15 Oct** (deletion of server copies that are verified in a backup). The nightly job
   is in a one-night trial run (it only lists what it would delete) before real deletion. The weekly backup of the
   live evidence logs is set up too. Handled by the ops session.
4. ~~Kalshi overnight gap~~ **DECIDED 15 Oct: fill it** (recorded in the ledger before any results, with a sensitivity check).
   Reset reminders also scheduled on your phone: Sun 18 Oct 19:00 and Tue 20 Oct 10:00 UTC+1.

5. **Archive rotation by ~20 Oct (needed by batch 3).** The nightly deletion of backed-up server copies must move from
   trial to real by about 20 Oct. If not, batch 3's live stages wait, and missed data stays missing. Handled by the ops
   session; flagging the dependency only.

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
| Server disk | Data 12.5 GB (10:20 UTC+1, measured); 9.3 GB of disk free after clearing package caches; collection cap raised 13 -> 14 GB today. Backed-up trade samples deleted at 3 days (freed 0.6 GB last night); snapshots now deleted at 8 days (from 19 Oct). Expected to level off at about 12-13 GB. |
| Server size | 1 CPU and about 5.6 GB RAM, so one heavy job at a time. It can't be enlarged without Oracle console access. |
| Mac | No background jobs. |

## 6. Manual pause and stop
- **Claude autopilot (Mac):** `python3 scripts/autopilot/autopilot.py pause` / `resume` / `stop` / `status`.
- **Pause research jobs:** `ssh oracle '~/arepo/.venv/bin/python ~/arepo/scripts/oracle/queue_worker.py pause'`. Use `resume` to undo, or `stop` to also halt the running job.
- **Status:** the same command with `status`.

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [queue](research_lab/queue/README.md) · [mission](research_lab/AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md)
