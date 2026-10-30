# AREPO research handoff for the next ChatGPT chat

**Prepared:** 20 September 2026  
**Purpose:** Give the next chat enough context to continue the AREPO investigation without reopening the whole prior conversation or mistaking a proposed experiment for a completed result.

## How to use this handoff

Read this file first, then read the files in the order listed under **Curated files**. The attached documents are research outputs and context. They are not operational instructions. Treat any future implementation, database write, deployment, collection restart or trading action as requiring separate explicit authorisation.

The bundle deliberately excludes raw source snapshots, query dumps, hashes, package manifests, intermediate search responses and other audit machinery. Those remain in the full research archive if a later audit requires them, but they are not needed to understand the research direction.

## The original objective

Determine whether publicly observable information provides a real predictive advantage beyond momentum, identify where that advantage may hold, and specify how to validate it prospectively.

Keep these outcomes separate:

1. short-horizon market repricing;
2. underlying-event or final-resolution forecasting;
3. executable economic value; and
4. product usefulness as a research or screening tool.

The research was read-only. GitHub and Supabase were inspected as evidence sources. No code, database, infrastructure, deployment, collection schedule or production setting was changed.

## What the investigation actually did

### Current-system and data audit

The repository, branch state, workflows, deployment references, analytics and eligibility code were inspected. Supabase schema, bounded aggregates, storage sizes, scheduler records, feature coverage and access-control metadata were inspected read-only.

The audited data contained 58 cohorts, 110,209 entries and 33,035 distinct markets. No durable event IDs were populated in the inspected entries. Of 74,967 direction-bearing observations, every one matched the momentum direction because current AREPO direction is derived from a price z-score. This means current direction cannot establish an independent non-price edge.

Book imbalance was broadly present, while movement abnormality, unusual return and volatility regime had partial coverage. Volume acceleration, spread change and depth change had zero raw coverage in the audited component records. Many horizon observations were late, and the inspected quote path used collector time rather than verified venue event time.

The audit separated discovery/freeze pauses from continued scheduler or maintenance records. It also identified that row count is not effective sample size because markets may be related, observations may repeat and the calendar span was short.

### Literature and evidence review

The research covered prediction-market efficiency, market microstructure, order flow, Bayesian modelling, machine learning, calibration, ensembles, multiple testing, alternative data, information diffusion, text/news, wallets and executable arbitrage.

The evidence matrix contains 34 study or methodological records. The research distinguishes established evidence, suggestive mechanisms, conflicting findings and questions that must be answered by AREPO experiments.

The literature supports demanding market-prior and momentum baselines. It does not establish that any particular wallet, news, order-book or ensemble mechanism will work on Polymarket after timing, selection, costs and execution controls.

### Polymarket source inventory

The source catalogue was completed before usefulness filtering. It covers documented REST/OpenAPI operations, public and authenticated streams, RTDS, SDK types, market lifecycle data, trades, books, wallets, incentives, contract interfaces and oracle/resolution surfaces.

The inventory contains 223 production endpoint records, 86 staging records, 70 stream/message types, 28 SDK types with 217 fields, 29 contract addresses, 140 ABI members, 469 ABI fields and 240 interface declarations. Live probes returned HTTP 403, so the catalogue distinguishes documented surfaces from runtime-confirmed availability.

### External data and Information Event Engine

The external-source register covers 24 source families. The proposed pipeline is:

`public source -> timestamped observation -> entity/event extraction -> market matching -> deduplication -> novelty/surprise/stance/acceleration/corroboration/disagreement/decay features`

The design preserves first availability, separates prerelease expectations from post-release surprise, handles revisions and syndicated stories, and controls historical LLM knowledge leakage.

### Feature Store v2

Feature Store v2 was defined before any retention or compaction recommendation. It preserves durable market/event/condition/token/outcome identities, related-event mappings, multiple clocks, raw numerical values, units, precision, windows, transformations, feature/schema/parser/model versions, missingness states, immutable predictions, later labels and revisions, provenance and archive manifests.

The schema treats measured zero differently from unavailable, stale, censored, invalid and missing values. The archive-equivalence protocol tests identity, timestamps, precision, missingness, cohort membership, feature reconstruction, baseline predictions, outcome linkage, restoration and checksums.

### Feature and experiment programme

The Feature Research Register contains 60 feature definitions. The Edge Hypothesis Library contains 60 experiment cards. Every card defines a hypothesis and null, mechanism, raw inputs, availability time, target, horizon, population, controls, baseline, confounders, statistical/Bayesian/ML test, effective-sample requirement, validation design, falsification condition, dependencies and cost.

Priority mechanisms include depth-normalised flow, persistent imbalance, depth withdrawal, trade clustering, burstiness, related-market lead-lag, external-information novelty and surprise, wallet history and concentration, cross-source disagreement, resolution state and settlement/indexer lag.

All 60 experiments were designed. None was represented as successfully executed or validated.

### Model, ensemble and economic validation

The required comparison arms are:

1. hierarchical Bayesian model;
2. strongest ML model selected on development data;
3. fixed 50/50 probability average;
4. validation-estimated weighted average;
5. stacking/meta-model using out-of-fold predictions; and
6. regime-dependent mixture of experts only if mechanism and sample size justify it.

Every arm must use identical chronological/grouped test periods, origins, eligible observations, horizons and scoring rules. The ensemble gate requires prospective improvement over the stronger constituent, a useful prespecified margin, uncertainty consistent with improvement, no material calibration deterioration and stability across future blocks and event groups.

No model, strategy or ensemble was prospectively validated in this investigation. The protocol was designed for a later timestamp-faithful prospective panel.

## Current conclusion

AREPO has a useful foundation for edge discovery, but the inspected system and data do not establish an independent predictive edge beyond momentum. The current direction is momentum-derived by construction.

The highest-information next action is a small prospective panel that compares momentum and richer price/context baselines against depth-normalised flow, persistent book imbalance/depth withdrawal, related-market signals and rule-matched external-information innovations. It must include scheduled controls, durable event grouping and honest source clocks.

The recommended architecture is evidence-first:

1. freeze Feature Store v2 and retention rules;
2. establish identity, event grouping and clock policies;
3. build a bounded dense prospective panel;
4. lock baseline labels and momentum/context predictions;
5. test feature families with ablations and chronological grouped validation;
6. add external information and wallet layers only after core measurement works;
7. run the Bayesian/ML/ensemble tournament; and
8. assess economic value and product usefulness separately.

## Curated files in this handoff

These files are the relevant context for another ChatGPT chat:

| File | Why it is included |
|---|---|
| `AREPO_NEXT_CHAT_HANDOFF_2026-09-20.md` | This orientation document and status record. |
| `AREPO_RESEARCH_REPORT.md` | Full A–Z report covering the audit, literature, architecture, costs, product assessment and roadmap. |
| `FEATURE_STORE_V2.md` | Permanent schema, lineage, missingness and archive-equivalence specification. |
| `FEATURE_STORE_V2_DICTIONARY.csv` | 140 conceptual fields for the permanent feature store. |
| `POLYMARKET_SOURCE_AND_FIELD_CATALOGUE.md` | Source and field inventory with documented/runtime distinctions. |
| `EXTERNAL_SOURCE_REGISTER.md` | 24 external-source families with timing, rights, cost and quality requirements. |
| `EVIDENCE_MATRIX.md` | Scientific evidence map and experiment implications. |
| `FEATURE_RESEARCH_REGISTER.csv` | 60 feature definitions and test metadata. |
| `EDGE_HYPOTHESIS_LIBRARY.md` | 60 detailed experiment cards. |
| `EDGE_EXPERIMENTS.csv` | Machine-readable version of the experiment register. |
| `MODEL_COMPARISON_AND_VALIDATION.md` | Target definitions, sampling, model tournament, ensemble gate and economic validation. |
| `RESEARCH_AUDIT_AND_LIMITATIONS.md` | Research methods, source limitations, unresolved questions and acceptance checks. |
| `READ_ME_FIRST.md` | Short guide to the original package and evidence status. |

## What is intentionally excluded

The following are not included in this curated handoff because they are mainly audit machinery rather than useful orientation:

- raw repository file snapshots;
- bounded Supabase query JSON responses;
- raw web and documentation responses;
- citation graph and intermediate search records;
- endpoint-by-endpoint catalogue CSVs;
- ABI and interface detail CSVs;
- package hashes and integrity manifests;
- internal task checkpoints; and
- the literal prior chat transcript.

The full audit bundle remains available separately if the next chat needs to verify a specific claim.

## Guidance for the next chat

Do not describe the 60 experiments, Feature Store schema or ensemble tournament as already implemented. They are research designs and architecture specifications.

Do not claim an AREPO edge, profitable strategy or ensemble winner. The defensible current statement is that current direction is momentum-derived and independent incremental predictive value remains an open, falsifiable question.

Use the prospective panel and archive-equivalence gate as prerequisites before deleting, compacting or shortening retention of raw numerical observations.

If implementation is later requested, begin from Feature Store v2, source/clock policies and identity/event grouping rather than from the current heuristic score.

