# AREPO — Plain-English Progress

**Last updated:** 2026-10-17 16:12 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Autopilot:** a new session started at about 15:30 UTC+1 and is working.
- **Server disk: solved.** You enlarged the disk to 100 GB (still free). There is now 61 GB free, and the collection limit is 45 GB.
- **Second free server: waiting for Oracle.** London is out of free servers right now. The server now asks Oracle again
  every 10 minutes and creates `arepo-research` (1 CPU, 6 GB, 100 GB, free) the moment one is available. Then it
  stops and alerts your phone. It cannot go over the free limits. Some experiments move there after that.
- **Batch 9's code is written and tested** (94 tests). An independent check that the code matches the design is
  running; its small download test can then run before 22 Oct, and its real downloads after.
- **Batch 5's family-listing job ran out of memory again.** Cause found: this morning's fix had been written but never
  connected to the program. Now connected (same output, checked by a test) and sent to the server; one retry is left.
- **Batch 6's top-up download started** at 16:08 UTC+1.
- **Batch 4's series download kept running out of memory** (4 attempts). Fixed without changing any output (it now
  streams the file instead of loading it whole) and sent to the server; it runs after batch 6's top-up download.
- **Batch 8's analysis code for "Binance terminal minutes"** (buying the near-certain side of daily crypto Up/Down
  markets in the last minutes) is written and tested; the other two batch-8 analyses are being written now.
- **Batch 10 drafted** from the remaining round-4 ideas: (1) do crypto options prices (Deribit, a professional market)
  predict Polymarket's daily Bitcoin/Ether price-ladder outcomes beyond Polymarket's own price; (2) do prices bounce back
  after breaking round levels like 0.50. Four other ideas were dropped with reasons (e.g. parlay prices are not public).
  The challenger found 15 required fixes, including a hidden bias that would have made the options test look better
  than it is. The author applied all 15; the options test now runs only if a power check (made without looking at
  outcomes) shows it can detect a useful effect. Its code is being written.
- **Batch 7's two main downloads finished** (text markets and geography markets). Batch 6's top-up download had been
  refusing to start because of the disk limit; it can start now.
- **Batch 4's small test** found the behaviour it looks for almost never happens, so that part (N1/N2) is recorded as
  "not testable", as its pre-set stop rule says.
- **Multi-signal ML:** the real development run should start by itself at about 19:30 UTC+1 today.

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
| Server disk | 100 GB disk, 61 GB free (17 Oct 16:05 UTC+1); collection cap 45 GB, 4 GB free-disk stop unchanged. |
| Server size | 1 CPU, about 5.6 GB RAM. A second free server (1 CPU, 6 GB, 100 GB) is being requested automatically every 10 min until Oracle has capacity. |
| Mac | No background jobs. |

## 6. Manual pause and stop
- **Claude autopilot (Mac):** `python3 scripts/autopilot/autopilot.py pause` / `resume` / `stop` / `status`.
- **Pause research jobs:** `ssh oracle '~/arepo/.venv/bin/python ~/arepo/scripts/oracle/queue_worker.py pause'`. Use `resume` to undo, or `stop` to also halt the running job.
- **Status:** the same command with `status`.

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [queue](research_lab/queue/README.md) · [mission](research_lab/AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md)
