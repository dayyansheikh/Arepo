@AGENTS.md

# Claude Code on AREPO

## Purpose
AREPO tests whether information beyond market price and momentum has genuine out-of-sample, prospective predictive
value on Polymarket data. It is research tooling: no alpha, calibration, profitability or trading claims exist.

## Hard status (read before acting)
- **Phase 3 is PROVISIONAL.** The final repaired implementation has had no integrated live prospective validation.
  The Oct 10 "complete" closeout is history only. **No Phase 4 modelling.**
- Standing user authorisation (2026-10-10): work autonomously towards the research objective, including routine
  protocol drafting, prospective freezing (after an accepting `science-reviewer` pass), bounded authorised public
  collection and phase advancement when acceptance is genuinely met. Never change thresholds, formulas or gates to
  obtain a pass; a design change needs a written scientific justification and review.
- Old failed pilots (D082/D094/D097/D114...) keep their original outcomes. Never redraw, relabel, pool, backfill
  or reinterpret them. Missing data stays missing.

## Protected boundaries
No production merge/deploy/migration/infra/env change, no remote branch deletion, no force-push, no secrets in output.
Never edit `docs/implementation/*EVIDENCE*.json`, frozen `*_PROTOCOL.md`, or canonical runs in `data-dumps/`.
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
action (production, trades, purchases, credentials, data retirement); unexpected cost or provider-rights issues; an
external blocker. Explain in plain English, recommend, and name the exact decision. Never silently bypass a boundary.
Routine test failures, defects, commits, new D-numbers and protocols are handled autonomously.

## Models and delegation
Main session: Opus at medium effort as orchestrator (direction, delegation, assessing results). Delegate: `implementer`
(Sonnet, medium) for code, tests, debugging and routine docs; `repo-scout` (Haiku) for bounded lookups and inventories;
`science-reviewer` (Opus, high) for independent review, protocol freezes and causal/leakage questions. Delegate when
useful, give clear scope and success criteria, avoid concurrent edits to the same files. Ultracode off by default.
`/compact` only after state is written to the repo. No recurring or background continuation chains.

## Progress reporting
Keep `docs/AREPO_PROGRESS_PLAIN_ENGLISH.md` (the user's one-page dashboard; complements, never contradicts, the
technical checkpoint) current after milestones, experiments, consequential failures, phase transitions, new decisions
for the user, and before handover/compaction. Rewrite, do not append logs.
