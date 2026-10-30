# AREPO research package — 19 September 2026

Start with **[the A–Z research report](AREPO_RESEARCH_REPORT.md)**. It explains what is verified, what existing data can support, and which experiment should come next. This is a research and architecture deliverable; it contains no production implementation or claim of a proven edge.

## Main deliverables

| Document | Purpose |
|---|---|
| [A–Z research report](AREPO_RESEARCH_REPORT.md) | Current-system audit, literature synthesis, architecture, costs, product assessment and roadmap. |
| [Polymarket source and field catalogue](POLYMARKET_SOURCE_AND_FIELD_CATALOGUE.md) | Inventory boundary, source families, stream/chain coverage, field-table guide and access gaps. |
| [Scientific evidence matrix](EVIDENCE_MATRIX.md) | 34 studies/methodological sources with findings, limits, inspection depth and experiment implications. |
| [External-source register](EXTERNAL_SOURCE_REGISTER.md) | 24 source families with timing, rights, cost and quality requirements. |
| [Feature Store v2](FEATURE_STORE_V2.md) | Permanent causal numerical schema, lineage, preservation matrix and archive-equivalence protocol. |
| [Feature Store dictionary](FEATURE_STORE_V2_DICTIONARY.csv) | 140 conceptual fields with types, meaning and as-of rules. |
| [Feature Research Register](FEATURE_RESEARCH_REGISTER.csv) | 60 feature definitions with raw inputs, confounders, availability and falsification links. |
| [Edge Hypothesis Library](EDGE_HYPOTHESIS_LIBRARY.md) | 60 full experiment cards; all designed, none presented as executed. |
| [Model comparison and validation](MODEL_COMPARISON_AND_VALIDATION.md) | Targets, sampling, Bayesian/ML/ensemble tournament, calibration, power, economic gates and promotion criteria. |
| [Audit and limitations](RESEARCH_AUDIT_AND_LIMITATIONS.md) | Evidence methods, source coverage, unresolved questions and acceptance checks. |

## Machine-readable catalogues

The `catalogues/` folder contains the production/staging endpoint lists, nested REST fields/references, stream and SDK types, contract addresses and ABI/interface fields. Start with `polymarket_production_endpoints.csv` (223 records), then follow source links and schema pointers into the field files. Counts include documented authenticated/transactional operations for completeness; they are not all public research reads. `catalogue_counts.json` gives exact row counts and avoids adding overlapping definitions as unique fields.

The evidence, external-source and experiment registers also have CSV versions. The source-code map connects experiment source abbreviations to primary documentation. Full source responses, bounded database queries/results, pinned repository files and documentation hashes are retained locally in `evidence/` for traceability; they are excluded from the portable package to avoid bundling operational metadata and unnecessary source copies.

## The main decision

Do not treat current direction as an independent signal beyond momentum, and do not discard numerical history. Design a small prospective book/flow/external-source panel with event grouping, honest clocks, scheduled controls and strong price/context baselines. Recommend an ensemble only if it beats its stronger constituent on the locked prospective test.

Live API probes returned HTTP 403, so the catalogue distinguishes documented fields from runtime-observed evidence. No profitable strategy, trained model or validated ensemble is claimed. No code, database or infrastructure changes were made.
