# AREPO — Plain-English Progress

**Last updated:** 2026-10-17 15:37 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Autopilot:** a new session started at about 15:30 UTC+1 and is working.
- **Server disk (urgent this afternoon): eased for about 3 days.** Data had reached 13.1 of the 14 GB collection limit.
  I cleared 1.7 GB of software-package caches and old system logs again, and stopped the package cache from rebuilding
  itself (it had refilled within a day). I raised the collection limit to 16 GB. The real safety limit (stop when less
  than 4 GB of disk is free) is unchanged, and at about 1.1 GB a day it is reached around 20 Oct. Deletion of
  backed-up 8-day-old snapshots starts freeing space about 21 Oct, so there is a risk of losing about a day of collection.
  **Your approval would remove this risk** (see section 2, item 6).
- **Building batch 9 now** (from idea round 4): a check of whether the public trade feed labels buys and sells correctly,
  market-making in daily stock markets settled by a public price feed, a "flow-aware" market maker, and how the displayed
  mid price is formed. The challenger's fixes are applied. Two programmers are writing the code in parallel; an
  independent check of code against design comes next. Its downloads wait until after 22 Oct (the data deadline of
  earlier batches).
- **Batch 4's series download keeps running out of memory** (4 attempts, about 1.7 h each before failing). A fix that
  does not change any output is being written.
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

6. **Server disk, before about 20 Oct (recommended: option a).** The safety hook stops me moving data on the server
   without your approval for that session. Options:
   a. Let a session move about 3 GB of unused research data (the ML cache and finished downloads, all also in the
      GitHub backup) onto the server's spare 10 GB volume. Nothing is deleted; the files stay reachable at the same
      paths. To allow it, start a session with `AREPO_RETIREMENT_SESSION=1` and ask for "the /var/oled relocation in
      the checkpoint".
   b. Enlarge the server disk in the Oracle console (free up to 200 GB in total). This takes about 10 minutes in the
      console, then a session grows the partition.
   c. Do nothing. Collection may pause for about a day around 20-21 Oct, and the missed data stays missing.

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
| Server disk | Data 13.1 GB (15:30 UTC+1, measured); 7.5 GB of disk free after clearing caches again; collection cap raised to 16 GB (4 GB free-disk stop unchanged). Backed-up trade samples deleted at 3 days (freed 0.6 GB last night); snapshots now deleted at 8 days (from 19 Oct). Expected to level off at about 12-13 GB. |
| Server size | 1 CPU and about 5.6 GB RAM, so one heavy job at a time. It can't be enlarged without Oracle console access. |
| Mac | No background jobs. |

## 6. Manual pause and stop
- **Claude autopilot (Mac):** `python3 scripts/autopilot/autopilot.py pause` / `resume` / `stop` / `status`.
- **Pause research jobs:** `ssh oracle '~/arepo/.venv/bin/python ~/arepo/scripts/oracle/queue_worker.py pause'`. Use `resume` to undo, or `stop` to also halt the running job.
- **Status:** the same command with `status`.

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [queue](research_lab/queue/README.md) · [mission](research_lab/AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md)
