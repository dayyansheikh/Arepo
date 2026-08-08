# Agent 8 — Portfolio / hiring reviewer

**Overall verdict: a strong, differentiated portfolio project — upper tier for a recent graduate,
provided the candidate frames it as a research/systems project, not an alpha claim.**

## Genuinely sophisticated aspects (code-verified)
- **Causal/research honesty as a first-class design goal:** immutable append-only cohorts, actual-vs-
  scheduled freeze timing, refusal to freeze incomplete scans, unavailable-not-fabricated observations,
  per-cohort denominator identities. This "assume provenance is wrong" discipline is rare and reads as
  genuine quant maturity (`evaluation/`, `discovery/cohort_from_scan.py`).
- **Production systems engineering:** idempotent single-tick scheduler with DB leasing and causal due-
  logic, dialect-portable ORM + additive metadata-diff migrator, read-only self-reconciling SQLite→PG
  importer, bounded category-C retention with archive-before-delete, health/observability, GitHub-Actions
  scheduling replacing paid cron. Deployment is real, not aspirational.
- **Testing:** 438 backend tests + ruff, 86 vitest, Playwright real-browser specs incl. disconnect/
  recovery and overflow. Above typical graduate norms.
- **Honest docs:** capacity audit *quantifies* the £0 storage lifetime instead of hand-waving; DECISIONS
  log explains trade-offs.

## Weaknesses / over-engineering / risky claims
| Sev | Finding | Fix |
|--|--|--|
| Medium | **Surface area is large** for a solo project (edge-research CLI machinery — `research_analysis`, `walk_forward`, `calibration` — is not product-exposed). Could read as over-engineering. | Frame it as "research harness, product shows the honest subset"; it's defensible but be ready to justify. |
| Medium | Evidence base is tiny (2 cohorts); a reviewer will probe whether any "edge" is claimed. | Claim **only** "honest prospective evaluation of a selection hypothesis; too early for edge." (The product already does this.) |
| Low | Some naming/scope sprawl across `evaluation/` (`research_*` vs `evaluation/*`). | Minor; a short module map in README helps. |

## Answers
- **Impressive for a recent graduate?** Yes — clearly above average, especially the causal-integrity and
  deployment engineering.
- **Rough band (subjective):** top ~10–15% of graduate data/quant portfolio projects for *engineering and
  research honesty*; mid for *novelty of signal* (momentum-derived).
- **Interview questions it invites (good):** "Why per-cohort not pooled Replay?"; "How do you prevent
  look-ahead in freeze timing?"; "What cadence gives independent samples?"; "How would you prove selection
  beats the wider set?"; "Walk me through the migration reconciliation." The candidate can defend all of
  these from the code.
- **Claim to avoid:** any predictive **edge/alpha**. Say "research-useful, evidentially immature."
- **Does live deployment help?** Materially — a URL that updates itself for weeks and accumulates an
  honest track record is far stronger than a local demo.

## Top 3 improvements for hiring signal
1. The **long-term selected-vs-wider scoreboard** (deduplicated) — turns the thesis into visible evidence.
2. **Daily cadence** + a short write-up on sample independence — shows statistical judgement.
3. A one-page **README architecture/module map** so a reviewer navigates the (large) codebase fast.

**Conclusion: ship** as a portfolio piece (with the fixes above raising the ceiling).
