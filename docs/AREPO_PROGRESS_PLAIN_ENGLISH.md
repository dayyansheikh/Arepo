# AREPO — Plain-English Progress

**Last updated:** 2026-10-16 05:36 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Server (Oracle):** healthy at 03:56Z (measured: 3.3 GB RAM free, 12 GB disk free, data 7.6 GB of the 12 GB cap).
  The order-book table job is running. New jobs wait until 05:30Z (the nightly quiet window).
- **Two overnight failures fixed and re-queued:**
  - The fresh 7,000-market download ran out of memory when it resumed. It now streams its checkpoint file.
  - The battery-2 replication crashed on blank values in one robustness check. The main tests were not affected.
- **ML regime test (J7) finished.** The full model's gain over the price-only model is concentrated where trades
  happened in the last 2 hours. That is largely expected, because the order-flow inputs are empty otherwise. For
  2-hour direction the gain is also larger in the last day before the end date.
  - No learned interaction between two inputs adds anything (0 of 15).
  - The liquidity comparison could not be measured: a design flaw left its "low" group empty. This is recorded, not
    patched.
  - The 4 passing comparisons now go to a frozen re-test on different markets.
- **Your creative priority:**
  - **Batch 1 is FROZEN.** Screens start once the fresh data is sealed (after the download above finishes).
  - **Batch 2** (weather favourites; impossible ladder orderings): all code is written (155 tests pass).
    - An independent check of the code against the design asked for 20 fixes. One is urgent: the ladder list must be
      locked to the exact code that builds it.
    - Fixes are being made now. The ladder and weather downloads are held until they land.
  - **Batch 3** (quote only when it is safe; when one side of the book vanishes): drafted and reviewed (13 required
    changes). The revision is in progress.
  - **Batch 4** (new; rule mechanics and natural experiments):
    - The ideas are: selling before order books close; what happens when one market in a series resolves; and two
      fee/rebate rule changes, used to measure true costs.
    - Status: drafted and reviewed (13 required changes). The revision is in progress.
  - Nothing creative has been tested yet.

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
| Server disk | 12 GB free; data 7.6 GB of a 12 GB cap (measured 03:56Z). Nightly deletion of backed-up copies is in its trial run. |
| Server size | 1 CPU and about 5.6 GB RAM, so one heavy job at a time. It can't be enlarged without Oracle console access. |
| Mac | No background jobs. |

## 6. Manual pause and stop
- **Claude autopilot (Mac):** `python3 scripts/autopilot/autopilot.py pause` / `resume` / `stop` / `status`.
- **Pause research jobs:** `ssh oracle '~/arepo/.venv/bin/python ~/arepo/scripts/oracle/queue_worker.py pause'`. Use `resume` to undo, or `stop` to also halt the running job.
- **Status:** the same command with `status`.

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [queue](research_lab/queue/README.md) · [mission](research_lab/AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md)
