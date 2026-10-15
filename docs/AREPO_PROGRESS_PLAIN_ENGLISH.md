# AREPO — Plain-English Progress

**Last updated:** 2026-10-15 19:23 UTC+1
**Phase:** Phase 4 (edge discovery) in progress. Autonomous programme started 15 Oct.
**Programme state:** RUNNING on the server (research queue live). Claude sessions are manual for now (see Approvals).
**Next Claude session:** when you open one. Automatic sessions are not yet approved. **Server queue:** checks every 2 minutes.

## 1. Right now
- **Server (Oracle):** collection every 2h, live trade monitor, Kalshi live test and the new **research queue worker**.
  - All healthy as of 18:23Z (measured).
- **Research queue:** live since 15 Oct 18:19Z.
  - Runs one job at a time.
  - Survives Claude usage limits, session ends and server reboots.
  - Tested by killing a job mid-run: it was detected and rerun automatically.
- **Jobs queued** (book and liquidity family; answers "does liquidity change which signals matter?"):
  1. Build the order-book table for the 3,200-market history set (resumable, multi-hour, network-bound).
  2. Finalise that table.
  3. Re-run the history model with book features (`r4_book`, a step declared earlier).
- **Data:** history datasets are being restored from the GitHub archive onto the server (about 1.1 GB).

## 2. Approvals needed from you
1. **Automatic Claude sessions (decision).** I built a Mac "autopilot" that starts a bounded Claude session every 30 min.
   - It sleeps through usage limits and uses only your Max login (never an API key).
   - Claude Code's own safety check **blocked me from testing it**, because it would run unattended with all permissions.
   - **Choose:**
     - **(a)** You approve and run it yourself.
     - **(b)** I build a restricted version (fewer powers, so it may pass the check).
     - **(c)** Server-only: research keeps computing, and Claude resumes whenever you open a chat.
   - Details: `research_lab/autopilot/PERSISTENCE.md`.
2. **One-time usage reset (deadline Wed 21 Oct).**
   - No automatic redemption is documented, and I can't see your account page.
   - Check claude.ai/settings/usage (or `/usage`). If there's a claim/redeem button, press it around Sun 18 Oct, after this week's allowance is used.
   - A phone alert was sent 19:2x UTC+1.
3. **Server GitHub token (by about 20 Oct)**, so the server can archive old data before its 12 GB cap fills.
   - Make the token at github.com/settings/personal-access-tokens/new: name `arepo-server-archive`, 1 year, repo `arepo-data` only, Contents read/write.
   - Then run `ssh -t oracle 'umask 077; read -rs -p "Paste token: " t; echo; printf %s "$t" > ~/.arepo/github_token; echo saved'`.
4. **Kalshi overnight gap:** reply "include it" (recommended) or "leave the gap".

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
| Server disk | 15 GB free; data 5.2 GB of a 12 GB cap. It fills around 22 Oct without the token above. |
| Server size | 1 CPU and about 5.6 GB RAM, so one heavy job at a time. It can't be enlarged without Oracle console access. |
| Mac | No background jobs. |

## 6. Manual pause and stop
- **Pause research jobs:** `ssh oracle '~/arepo/.venv/bin/python ~/arepo/scripts/oracle/queue_worker.py pause'`. Use `resume` to undo, or `stop` to also halt the running job.
- **Status:** the same command with `status`.

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [queue](research_lab/queue/README.md) · [mission](research_lab/AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md)
