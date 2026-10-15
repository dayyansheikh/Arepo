# Handover to next session (written 2026-10-15 19:10 UTC+1, 18:10Z)

The previous session reached its compaction limit (2 compactions). Per CLAUDE.md it handed over instead of continuing.

## Objective
The user's new standing mission is in `docs/research_lab/AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md`. Read it in full; it is the task. In short:
- Run a sustained, autonomous edge-discovery programme (screening funnel → candidate selection → intensive modelling → frozen prospective confirmation → economic check).
- Establish **verified** persistence that resumes after the 5-hour and weekly usage limits.
- Maintain a phone-friendly dashboard.
- Usage plan: exhaust the current weekly allowance by about Sun 18 Oct. Use the one-time reset, which **expires Wed 21 Oct**, before then. The normal weekly reset is Thu 22 Oct.

## Acceptance criteria (first milestone)
1. **Persistence mechanism:**
   - Chosen and implemented.
   - Tested with one harmless real run plus one controlled interruption and recovery.
   - Documented, with a manual pause and stop.
   - If unattended Claude re-invocation is not possible on the subscription, say so plainly and ship the server-side experiment runner instead.
   - No billable API use without approval.
2. **Durable research queue:**
   - A queue file or directory in the repo with the fields in mission §8.
   - Plus a server worker that runs queued jobs with a lock, idempotency, timeouts and bounded retries.
3. **First real screening jobs** queued and running. Every attempt is logged to the trial ledger, nulls included.
4. **Dashboard** `docs/AREPO_PROGRESS_PLAIN_ENGLISH.md` rewritten to mission §9: running or waiting state, next invocation, worker health, experiments, usage milestones, and approvals needed.
5. **User alert** about the one-time reset, telling them whether it needs manual redemption and the exact steps, before Wed 21 Oct.

## State (measured 2026-10-15 18:07Z)
- **Repo:**
  - Branch `chore/arepo-claude-setup`; production untouched.
  - Another session may commit here, so commit only your own files.
  - Untracked `.codex/` and `backend/data-dumps/` are not ours; leave them.
- **Oracle server** (`ssh oracle`, BatchMode; see `docs/research_lab/COLLECTION_HOST.md`):
  - **Hardware:** 1 OCPU aarch64, about 5 GiB RAM (3 GiB available), 15 GB disk free. `data-dumps` is 5.2 GB against a 12 GB cap.
  - **This is small.** Concurrency on the host must be about 1 heavy job. The Mac (8 GB) is comparable or faster for single fits.
  - Oracle's free tier allows up to 4 OCPU / 24 GB on Ampere, but the user can't log into the Oracle console, so it can't be resized for now.
- **Host cron (live, healthy):**
  - `arepo_pass.sh` at `31 */2`;
  - `supervise.sh` at `*/5` (live trade monitor + cross-venue-live E009/E010);
  - outcomes at `10 2,14`;
  - ntfy notify at `*/15`.
- **Mac:** collection retired (launchd plists `*.disabled`). Data-dumps retired; 42 GiB free. Data lives in the private GitHub repo `dayyansheikh/arepo-data` (releases) plus the server. Restore guide: `docs/research_lab/DATA_ARCHIVE_2026-10-13.md`.
- **Notifications:**
  - ntfy push works; the topic is in `~/.arepo/ntfy_topic`, sent via `backend/astrolabe/research_lab/notify.py`. Use this for user alerts (e.g. the reset deadline).
  - The Gmail tool may not be connected.

## Research results so far (do not redo)
See `docs/research_lab/EXPERIMENT_LEDGER.md` and `docs/AREPO_V2_CHECKPOINT.md`.
- **Signals that hold:**
  - Order flow (E007) is real but tiny, about 0.36c.
  - Reversal (E004) is real but not tradable; it is likely bid-ask/quote noise.
  - Hypothesis battery 1: 18 of 72 survive; 16 replicate on `h3_power`.
- **Not profitable:** 95 economic conditions, none profitable after costs.
- **Wallet features:** null in 3 analyses.
- **Kalshi lead:** the strongest historical predictor. Live as E009/E010; analyse once after 2026-11-03.
- **Learned surprise detector `sm_learned_v2`:** about 6.5% precision against a 0.87% base rate. It is volatility-driven and not profitable. Live as E011; analyse once after 2026-11-11 13:00Z.
- **Code base for screening:** `backend/astrolabe/research_lab/` (`ml_panel.py`, `ml_models.py`, `ml_explain.py`, `flow_features.py`, `economics.py`, `history_backfill.py`, `detector_eval.py`, `surprise_*.py`).
- **Trial budget:** `trials.jsonl`, unioned by `scripts/oracle/deploy.sh`.

## Decisions made / standing
- The protected boundaries in CLAUDE.md all stand.
- **Wallets:** HMAC hashes only, never labelled "insider".
- **Category scope:** a parameter.
- **Trading engine:** don't touch.
- **Heavy jobs:** never run two memory-heavy jobs at once (heavy-lock convention in `~/arepo_collector/heavy_lock.md`).

## Open user items
1. **Server GitHub token, needed by about 22 Oct.**
   - **What:** a fine-grained token, `arepo-data` only, Contents Read/Write.
   - **Why:** for server archive rotation (`scripts/oracle/archive_rotate.py`, written but not installed). Without it the 12 GB cap fills at about 1 GB/day.
   - **Install:** give the user a hidden-input command (`ssh oracle`, `read -s`, saved to `~/.arepo/github_token`, chmod 600). The server lacks `gh` and `zstd`; install them or use Python equivalents.
2. **E009/E010 overnight gap:**
   - **Decision:** "include it" or "leave the gap" for the server validation copy `/home/opc/arepo_val`, covering about 00:00–10:47Z on 10-14.
   - **Recommendation:** include it, logged as a disclosed deviation before the outcome analysis.
   - **Status:** awaiting the user.
3. **Resend audit:** deferred by the user.
4. **One-time usage reset:** verify whether it needs manual redemption, then alert the user via ntfy with steps before Wed 21 Oct.

## Running / scheduled jobs
- Only the host cron above. No Claude loops or cron jobs are active.

## Exact next action
1. Read the mission file.
2. Research the options for unattended Claude Code runs on a subscription:
   - `claude -p` headless with `claude setup-token` / `CLAUDE_CODE_OAUTH_TOKEN`;
   - cloud routines via RemoteTrigger or `/schedule`;
   - how rate-limit and reset errors surface.
3. Check the account's usage and reset facts that are visible to you.
4. Pick a mechanism.
5. Build the research queue and the server worker, then test a harmless run plus an interruption.
6. Queue the first screening family. The first data step is pulling `h3_power` and the history panels from the `arepo-data` releases onto the server.
