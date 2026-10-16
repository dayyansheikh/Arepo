# AREPO — Plain-English Progress

**Last updated:** 2026-10-16 06:46 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Server (Oracle):** healthy at 05:44Z (3.2 GB RAM free). Running: the order-book table, and the batch-2 ladder list
  (the first batch-2 job).
  - Next on the server: the fresh 7,000-market download. It ran out of memory twice. It is now fixed, but the fix is
    untested on the real data.
- **Battery-2 re-test on 5,000 different markets (HB2-R): 3 of 6 ideas replicate.**
  - The 3: order-flow momentum is stronger in volatile markets and in wide-spread markets; 1-day drift depends on
    liquidity.
  - 3 do not replicate: near-resolution flow, large-for-market trades, and 24h flow × liquidity.
  - None pays: the move is about 1c per trade against about 3.5c of spread and fees.
- **ML regime test (J7):** the full model's gain sits where trades just happened (largely expected). No learned
  pairwise interaction adds anything. The liquidity comparison was unmeasurable because of a design flaw, which is
  recorded.
- **Your creative priority:**
  - **Batch 1 is FROZEN.** Screens start once the fresh download is sealed.
  - **Batch 2:** code done, independently checked, and all 20 fixes landed. The ladder list is running now.
  - **Batch 3** (safe quoting; one side of the book vanishing):
    - Code written. The independent check asked for 18 fixes, including 3 silent biases in the maker test.
    - The data save (fixed) is released. The analysis fixes are in progress.
  - **Batch 4** (selling before order books close; series roll-overs; fee/rebate rule changes as cost measurements):
    - The data code is checked and fixed, and its data save is released.
    - The analysis code is being written. Its two new market samples are due by 22 Oct.
  - I also caught and fixed a scheduling bug before it ran: a job that would have blocked the server's job slot.
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
| Server disk | 12 GB free; data 7.6 GB of a 12 GB cap (measured 03:56Z). Nightly deletion of backed-up copies is in its trial run. |
| Server size | 1 CPU and about 5.6 GB RAM, so one heavy job at a time. It can't be enlarged without Oracle console access. |
| Mac | No background jobs. |

## 6. Manual pause and stop
- **Claude autopilot (Mac):** `python3 scripts/autopilot/autopilot.py pause` / `resume` / `stop` / `status`.
- **Pause research jobs:** `ssh oracle '~/arepo/.venv/bin/python ~/arepo/scripts/oracle/queue_worker.py pause'`. Use `resume` to undo, or `stop` to also halt the running job.
- **Status:** the same command with `status`.

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [queue](research_lab/queue/README.md) · [mission](research_lab/AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md)
