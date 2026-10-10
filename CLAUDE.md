@AGENTS.md

# Claude Code on AREPO

## Purpose
AREPO tests whether information beyond market price and momentum has genuine out-of-sample, prospective predictive
value on Polymarket data. It is research tooling: no alpha, calibration, profitability or trading claims exist.

## Hard status (read before acting)
- **Phase 3 is PROVISIONAL.** The final repaired implementation has had no integrated live prospective validation.
  The Oct 10 "complete" closeout is history only. **No Phase 4 modelling.**
- Do not design, approve, freeze or run the final validation protocol, start live collection, or change thresholds,
  formulas or acceptance gates unless the user explicitly asks in the current session.
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

## Models and context
Sonnet for everyday implementation/debugging; Opus (`science-reviewer` subagent or `/model opus`) for protocol freezes,
causal/leakage review and difficult design; Haiku (`repo-scout`) for bounded read-only lookups. Prefer deterministic
tests over extra agents. `/clear` between unrelated tasks; `/compact` mid-task only after state is written to the repo.
No recurring or background continuation chains.
