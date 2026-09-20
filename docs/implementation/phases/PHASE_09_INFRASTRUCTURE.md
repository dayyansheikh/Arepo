# Phase 09 — Infrastructure sizing

Status: provisional; refine after prerequisite evidence. Owner: current AREPO implementation task.

## Objective

Measure workload and preservation costs, then propose infrastructure that fits the demonstrated requirements.

## Why this phase exists

Capacity decisions require measured growth and verified preservation, not destructive guesses.

## Research basis

Report V/W/X; full archive-equivalence protocol and measured source/panel volumes, not planning cost estimates. See immutable package in ../../research/2026-09-20 and canonical contracts in ../../architecture.

## Dependencies

Phase 08 accepted/tested tip and its actual outputs. Earlier contracts remain binding. Cost/source-rights measurements may be gathered earlier, but final tier choices use actual workloads. Before work: read checkpoint/master/this plan, inspect prior outputs and relevant current code/tests, refine tasks and record architecture changes in ../AREPO_V2_DECISIONS.md.

## Current repository state

Configuration declares Render Free API, Supabase, GitHub Actions and Vercel. Research audit storage/load figures are dated; local archive implementation verifies only hash/count, R2 backend unimplemented. This is the Phase 0 inventory; refresh this section from actual code before starting.

## In scope

Measure workload and preservation costs, then propose infrastructure that fits the demonstrated requirements. Work remains in the existing repository and nonproduction environment.

## Out of scope

Production merges/deployments/migrations, infrastructure or credential changes, data deletion, retention shortening, scan restarts, paid purchases and trades. Later scientific choices remain evidence-dependent; do not implement later phases to bypass this phase gate.

## Ordered implementation tasks

1. Measure panel/DB/object bytes, growth, memory, egress, query plans, collector backlog and analytical runtime.
2. Implement/benchmark independent archive readers and full preservation protocol before any compaction proposal.
3. Test corrupt/missing partitions, restore duration/access and end-to-end baseline/label replay.
4. Compare capacity and cost scenarios with current official pricing once concrete sizes are known.
5. Recommend infrastructure and rollback/restore plan; do not change service plans, env vars or live retention.

## Likely modules/files

Archive/measurement adapters and benchmark reports; scheduler/archive.py studied, no automatic retention wiring.

## Data model, API and migration implications

Use versioned v2 entities and immutable artifact manifests. Refine any additive schema proposal from observed prerequisite needs; no automatic production migration or serving API promotion.

## Tests required

All ten archive-equivalence stages, missing/corrupt files and full-cohort restore; representative measured loads and reproducible query/compute benchmarks.

## Acceptance criteria

Measured sizing and full preservation equivalence, restore and cost report; concrete recommendation with no external service changes.

## Exit checklist

- [ ] Prerequisites reloaded and plan refined against real outputs.
- [ ] All scoped tasks and acceptance criteria satisfied; limitations explicit.
- [ ] Required tests passed with exact command/target/result recorded.
- [ ] Diff self-reviewed for causal leakage, data loss, unrelated changes and protected boundaries.
- [ ] Documentation/decision log/master status current.
- [ ] Coherent safe work committed; branch and draft PR/dependency recorded.
- [ ] Checkpoint updated with safe commit, files, tests, blockers and exact next action.

## Protected boundaries

Never fabricate prospective observations, tune on final confirmation, or treat repeated rows as independent events. Preserve complete discovery separately from public limits and sampled deep collection. Archive equivalence does not authorise deletion. A protected action requires the user's explicit decision; record BLOCKED — USER DECISION REQUIRED with the concrete action. Missing access/data is a real blocker; synthetic fixtures are not a substitute for empirical acceptance.

## Handoff/output

Measured infrastructure recommendation, complete preservation/restore evidence and cost scenarios.
