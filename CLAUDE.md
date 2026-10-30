@AGENTS.md

# Claude Code on AREPO

## Purpose
AREPO tests whether information beyond market price and momentum has genuine out-of-sample, prospective predictive
value on Polymarket data. It is research tooling: no alpha, calibration, profitability or trading claims exist.

## Hard status (read before acting)
- **Phase 3 is CLOSED** (D117, then D119: the D118 live PASS validated the control-pairing *mechanism* on liquid markets;
  see `docs/implementation/d118/D118_ADDENDUM.md`). Trigger-vs-control *effect* studies still need their own registered
  design that addresses control availability and pair dependence. **Phase 4 is in progress** under the research-lab governance
  (`docs/research_lab/EXPERIMENT_LEDGER.md`): pre-registration, MDE, event clustering, Holm, challenger review. No
  edge claims without prospective confirmation and an economic check.
- Standing user authorisation (2026-10-10): work autonomously towards the research objective, including routine
  protocol drafting, prospective freezing (after an accepting `science-reviewer` pass), bounded authorised public
  collection and phase advancement when acceptance is genuinely met. Never change thresholds, formulas or gates to
  obtain a pass; a design change needs a written scientific justification and review.
- Old failed pilots (D082/D094/D097/D114...) keep their original outcomes. Never redraw, relabel, pool, backfill
  or reinterpret them. Missing data stays missing.

## Protected boundaries
No production merge/deploy/migration/infra/env change, no remote branch deletion, no force-push, no secrets in output.
**Owner exception (2026-10-21):** Claude may merge its OWN pull requests into `arepo-free-production-v1`. Conditions:
- Only after the full frontend/backend validation passes and a self-review of the diff.
- Through GitHub (`~/.local/bin/gh pr merge`), never a direct push to the production branch.
- Right after merging, tell the owner in plain English what changed and give the PR link, so they can review.
- Verify the Render and Vercel deploys afterwards.
- This exception does not cover destructive migrations, env/secret changes, infra changes or data deletion. Those still need explicit owner approval.
Never edit `docs/implementation/*EVIDENCE*.json`, frozen `*_PROTOCOL.md`, or canonical runs in `data-dumps/`.
**Frozen for registered live test E026 until 2026-12-07** (any edit voids it): `backend/astrolabe/research_lab/`
`copy_skilled.py`, `copy_skilled_analysis.py`, `wallet_skill.py`, `wallet_skill_dev.py`, `costs.py`, and
`model_specs/copy_skilled_v1.json`, `model_specs/cost_model_calibration_v1.json`. Put changes in new files instead.
Data retirement only via the capsule-first policy in `docs/implementation/PHASE_03_BOUNDED_RETENTION.md`, with explicit
user approval for that session.

## Session routine
1. `git status` and branch; read `docs/AREPO_V2_CHECKPOINT.md` (short) and use `docs/DOCS_INDEX.md` to locate files.
2. Load only task-relevant code, contracts, tests and evidence; use bounded `grep`/ranges, never whole evidence JSONs,
   `data-dumps/` contents or the research package wholesale.
3. State the task and acceptance criteria, implement the smallest coherent change, run proportionate tests
   (`cd backend && source .venv/bin/activate && pytest <scoped> && ruff check <files>`), review the diff.
4. Before finishing: update the checkpoint live section (rewrite, do not append), commit, and leave the exact next action.
   Put state in the repo, never only in conversation.

## When to stop and ask the user
Only for: a fundamental change of objective or methodology; an unresolvable material scientific disagreement; repeated
failures where the next change would compromise a scientific contract; a result questioning programme validity; risk of
losing irreplaceable evidence; insufficient storage or missing independent backup for a risky collection; any protected
action (production, trades, purchases, credentials, data retirement); unexpected cost; an
external blocker. Explain in plain English, recommend, and name the exact decision. Never silently bypass a boundary.
Routine test failures, defects, commits, new D-numbers and protocols are handled autonomously.

## Models and delegation
Main session: Opus at medium effort as orchestrator (direction, delegation, assessing results). Delegate: `implementer`
(Sonnet, medium) for code, tests, debugging and routine docs; `repo-scout` (Haiku) for bounded lookups and inventories;
`science-reviewer` (Opus, high) for independent review, protocol freezes and causal/leakage questions. Delegate when
useful, give clear scope and success criteria, avoid concurrent edits to the same files. Ultracode off by default.
`/compact` only after state is written to the repo. No recurring or background continuation chains.

## Context hygiene (sweet spot: stay under about 60% of the window; at most 2 compactions per session)
Auto-compaction fires at 600k tokens (`autoCompactWindow` in `~/.claude/settings.json`). You cannot see your own usage, so
do not guess a percentage. Count compactions instead:
- **Counter.** Every compaction summary must begin with the line `Compactions this session: N` (N = previous N + 1; a
  fresh session has none, which means 0). If you see no such line, assume 0.
- **Compactions 1 and 2 are fine.** Before each one (when you can choose the moment), write state to the repo first.
- **After the 2nd compaction, switch to handover.** Do not continue into a 3rd. At the next task boundary, or at once if
  the user says context is high, do the handover below. A compaction is lossy; a clean session reading the checkpoint is
  better than a third summary of a summary.
- **Handover.** (1) Rewrite `docs/AREPO_V2_CHECKPOINT.md` live section and `docs/AREPO_PROGRESS_PLAIN_ENGLISH.md`.
  (2) Rewrite `docs/HANDOVER_NEXT_SESSION.md` (rewrite, never append) with: objective, state, decisions made, files
  changed, running or scheduled jobs, open user decisions, and the exact next action. (3) Commit. (4) Tell the user in
  plain English: "Context is high; recommend a new chat", and print this ready-to-paste prompt:
  `Read CLAUDE.md, AGENTS.md, docs/AREPO_V2_CHECKPOINT.md and docs/HANDOVER_NEXT_SESSION.md. State the task and acceptance
  criteria from the handover, then continue from its exact next action. Do not redo finished work.`
- **Task boundaries.** When a task finishes and the next one is unrelated, recommend `/clear` or a new session (use the
  handover if work remains). Do not start an unrelated large task in a session that has already finished several.
- **Keep bulk output out of the chat:** `| tail`/`| head`, bounded greps, never whole logs or evidence JSONs; delegate wide
  reading to `repo-scout` and report only conclusions.
- **Compaction focus:** keep the current phase and objective, protected boundaries, active experiment IDs and verdicts,
  pending user decisions, files changed this session, the compaction counter and the exact next action. Drop tool output,
  logs and dead ends.

## Progress reporting
Keep `docs/AREPO_PROGRESS_PLAIN_ENGLISH.md` (the user's one-page dashboard; complements, never contradicts, the
technical checkpoint) current after milestones, experiments, consequential failures, phase transitions, new decisions
for the user, and before handover/compaction. Rewrite, do not append logs. The `Last updated` line must carry
date and exact time (HH:MM, user local time written as UTC+1, e.g. `2026-10-10 22:17 UTC+1`), taken from `TZ=Etc/GMT-1 date`, never an estimate.
