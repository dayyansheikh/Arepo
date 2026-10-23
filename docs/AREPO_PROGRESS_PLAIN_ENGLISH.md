# AREPO — Plain-English Progress

**Last updated:** 2026-10-23 13:21 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING. Server queue plus **Claude autopilot (approved by you, installed 15 Oct ~20:05 UTC+1)**.
**Next Claude session:** automatic. The autopilot checks every 30 min and starts a session (up to 5h) whenever none is
running. After a usage limit it waits for the reset time, then continues. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Your 23 Oct message ("why have you stopped?"): it had not stopped.** Eight experiment sessions ran since Wednesday
  evening (about every 5 hours, 1 to 3 hours each, about 460 commits). Each one ran until the usage limit cut it off before
  it could write its closing summary, so the Lab board showed only "hit your session limit". **Fixed (23 Oct):** the board
  now shows, for such a session, how long it worked and its last progress note. A phone update was sent at about 13:30.
- **Restarted after the last cut-off:** the independent re-check of LT10's code fixes, the LT11 design draft, and a fix for
  the failed batch 8 "exclusion keys" job (its small disk allowance ran out).
- **Security check (23 Oct):** Cloudflare's security audit was run on the site and the lab code. No confirmed holes; the lab lock and passkeys held up. There are 5 things to check or fix (details sent to your phone; summary in `docs/security/AUDIT_2026-10-23_RUN1.md`). The most important is to confirm that Render has a strong AUTH_SECRET.
- **Planned live-test families in the pipeline:** LT8 (counting checks today), LT9 (code done, data from 12 Nov), LT10
  (design frozen; code written and independently checked, fixes being re-checked).
- **Seven registered live tests** are collecting or waiting to collect (E009/E010, E011, E012-E014, E015, E022, E026).
  Single analyses: E009/E010 (3 Nov), E011 (11 Nov), E012-E014 (13 Nov), E015 (15 Nov), E022 (17 Nov), E026 (6 Dec).
- **LT7 (five planned tests from round 12): closed, no test.** All five failed their counting checks tonight, before any
  outcome was read (too few usable cases, too little power, or too much overlap with known factors). Two were expected to
  fail when the design was written. Nothing is counted.
- **LT8 (three planned tests from round 13): closed, no test.** Both counting checks finished this morning (07:03 and
  08:41 UTC+1), before any outcome was read. The "busy hours" idea had far too few markets with a regular schedule (about 3
  per snapshot against 1,200 needed). The "quiet order book" idea passed every power and overlap check but fell short on
  volume (about 431,000 projected cases against 504,000). The "sweep clock" idea had too few "held" moves (7% against 15%).
  Nothing is counted. Because LT8 closed, LT9 may now start collecting from 30 Dec instead of 21 Jan.
- **LT9 (three planned tests from round 14, about reward-programme quoting; a fourth only if its count allows):** design text **frozen** (22 Oct, after the
  challenger review and a re-check). Its code (data seal and counting checks) passed an independent
  code check after fixes (23 Oct) and is merged. Its data seal waits until the 2 to 12 Nov data exists.
- **Cross-venue twins (batch 16, K): closed, not testable** (a blind check found 3 true twins in 100 sampled pairs; 90 needed).
- **Model run (MC1):** now running on the server in 5.5-hour pieces (about 32 hours in total), giving way to LT8's checks.
- **Batch 7:** its counting job starts from 24 Oct. **Batch 8/9:** both failed data jobs are fixed and queued.
- **New ideas round 14** done (10 ideas), all now used by LT9 or the signal engine. **Round 15 done** (10 ideas, CH222-CH231). Its main
  finding: comparing venues every 2 hours never gives enough pairs, but the 2-minute Kalshi + Polymarket poller (used by
  E009) does. **LT10** (three ideas on that poller: does Kalshi's quoting move Polymarket's spread or its next move) **design frozen**
  (23 Oct, after an independent challenger review asked for changes and a re-check accepted them), well before E009's
  analysis on 3 Nov, so it cannot be shaped by that result. Next: its code. About 3 in 4 that none of the three survives
  its counting check (the designer's estimate).
- **New ideas round 16 done** (10 ideas, CH232-CH241), written to clear the counting checks that killed LT5-LT8. Its key
  observation: on this venue a resting order ties up the money of its side, so cheap-side orders are over-supplied. Top
  candidates for a planned LT11: whether price moves bought with more money keep going (about 40% chance of surviving its
  counting check, the author's estimate), whether arbitrage across a multi-outcome event widens spreads, and what happens
  when a rewarded market's price crosses 10c or 90c. **The counts-only map ran this morning** (9:33 UTC+1, one week of
  snapshots): all three populations are large enough on paper (for example about 1,240 traded price moves per snapshot
  where 335 are needed), with two warnings: the trade-volume field is blank for most markets, and the 10c crossings bounce
  back often. **The LT11 design is being drafted now**, then an independent challenger review.
- **Copy-skilled wallets (E026):** registered; collection starts 25 Oct (phone note then).
- **Honest pattern:** most planned tests die at the counting stage, before any outcome data is read (LT5, LT6, LT7 and now
  LT8 all closed this way). New-ideas round 16 (running now) is told to aim for much larger case counts. That is the checks working as designed.
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

8. **NOW TIME-SENSITIVE (needed by about 27 Oct): let Claude clear finished restore copies on the server.** Measured 23 Oct
   03:10 UTC+1: the data folder is at **34 of 40 GB** and grows about 1 GB a day, so jobs (including the LT2 live
   collector) would start refusing around 29 Oct. Batch 18's 4.9 GB copy is finished now and LT8 does not use it. Restore copies are
   hash-checked copies of data that is safe in the archive, made so a job can re-read old files. About 9 GB of them
   are finished with or soon will be (measured 22 Oct: batch 18 4.9 GB finished now; LT4 3.0 GB and LT3 0.3 GB after
   LT6's flow count today; LT5 0.8 GB after its count today; LT6 1.2 GB after its counts). Jobs stop at a
   40 GB data limit (**33 GB on 22 Oct**, and LT7's restore will add more), so they will need clearing within days. The safety hook rightly stops
   Claude from deleting anything in the data folder. **Decision needed:** approve a short clearing session for these
   copies only (each one listed and checked against the archive first). Batch 17 no longer needs this: it now writes
   to a fresh folder instead.

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
| Server disk | 100 GB disk, 38 GB free (measured 22 Oct 06:20 UTC+1); collection cap 45 GB, 4 GB free-disk stop unchanged. |
| Server size | **2 CPUs, 12 GB RAM since 22 Oct** (free tier). A second free server (1 CPU, 6 GB, 100 GB) is being requested automatically every 10 min until Oracle has capacity. |
| Mac | No background jobs. |

## 6. Manual pause and stop
- **Claude autopilot (Mac):** `python3 scripts/autopilot/autopilot.py pause` / `resume` / `stop` / `status`.
- **Pause research jobs:** `ssh oracle '~/arepo/.venv/bin/python ~/arepo/scripts/oracle/queue_worker.py pause'`. Use `resume` to undo, or `stop` to also halt the running job.
- **Status:** the same command with `status`.

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [queue](research_lab/queue/README.md) · [mission](research_lab/AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md)
