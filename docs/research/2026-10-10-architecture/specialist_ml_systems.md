# AREPO: ML systems and experimental infrastructure review

Read-only review, 2026-10-10. Branch `chore/arepo-claude-setup` at `19d7bd3`. Nothing was run except library version checks, `du`, `ls` and one snapshot manifest read.

**Measured environment.** The machine is an 8 GB RAM, 8-core Mac with **8.6 GiB of free disk**. `data-dumps/` holds 21 GB. The backend venv has only numpy 2.4.6 and pandas 2.3.3: no scipy, scikit-learn, statsmodels, duckdb, pyarrow, polars, lightgbm, xgboost, pymc, numpyro or mlflow. One complete Gamma snapshot (`20261010T204959Z_4520b6b7`) has 272,660 rows and is 27 MB as CSV.gz. About 43k of those rows are forecast-eligible binary markets, spread over about 10k events.

## 1. Inventory: what exists

**Research lab** (`backend/astrolabe/research_lab/`, about 2.9k LOC, 8 test files in `backend/tests/unit/test_research_lab_*.py`):

| Capability | Status | Where |
|---|---|---|
| Point-in-time features | Yes, for snapshot pairs. Features come from origin columns only, and the registry refuses label columns (`LABEL_COLUMNS`). | `features.py` (`FeatureSpec`, `register`, `compute_origin`), `panel.compute_features` |
| Point-in-time collection | Complete keyset enumeration, a per-page receipt clock, page body sha256 and a manifest | `collector.py`, `extract.py`, `book_sweep.py` |
| Leakage guards | Training is purged by actual label availability (`t_j <= min t_i` of the test bin, in 60s bins). Lambda is chosen on an inner time split, never on test data. Ablations drop `depends_on` children. Tests cover all three. | `evaluate.purged_train_mask`, `compare._inner_split`, `compare.ablations`, `test_research_lab_compare.py` |
| Temporal split | Walk-forward over capture periods only. `split="walk_forward_by_period"` is hard-coded and nothing else is accepted. | `compare.run_comparison` |
| Event-clustered inference | Cluster bootstrap that aggregates SSE per cluster before resampling, so it is O(B·k) and cheap. Event is the default since M1. | `compare.paired_bootstrap`, `e004.event_clusters` (market fallback counted) |
| Paired bootstrap | One set of resamples is shared across models, giving difference CIs | `compare.paired_bootstrap`, `e003.paired_diff_ci` |
| Ablations | Leave-one-family-out and add-one-family, over 5 families (price, momentum, context, interaction, book) | `compare.ablations` |
| Pre-registration | Markdown ledger committed before outcomes. Clarifications are timestamped and deviations recorded. | `docs/research_lab/EXPERIMENT_LEDGER.md` (E001–E004, M1) |
| Prospective forecast log | Append-only (`open(...,"x")`). Records the spec sha256, snapshot manifest and rows sha256, commit and dirty flag. Scoring recomputes forecasts and asserts equality with the log. | `forecast.predict`, `forecast._check_logged_forecast` |
| Model specs | One frozen JSON spec, `e002_reversal_v1`, with coefficient and registered commit. Comparison specs exist only as `ModelSpec` objects in code. | `model_specs/`, `compare.ModelSpec` |
| Provenance | Each run stores results JSON with manifest sha, code sha256, git HEAD, seed and feature versions. It refuses to overwrite a run directory. | `compare.run_comparison`, `write_new_json` |
| Execution check | Touch-to-touch P&L with an event-clustered CI | `e004.trade_pnl` |

**Phase 1–3 stack** (`feature_store/`, `research_panel/`, about 20k LOC). This is the canonical v2 entity/clock/identity store, plus the panel selection, origin and window machinery, and the in-progress `d116_evaluator.py`. The research lab deliberately does not import it (see the `collector.py` docstring).

**Gaps, all concrete:**
1. **Incomplete code hashing.** `compare.code_sha256` hashes only `compare.py` and `features.py`. It leaves out `panel.py`, `evaluate.py` and `models.py`, which define eligibility, features, purging and the estimators. `pairs_content_hash` covers only `period, t_i, dmid` and no feature columns. `e004` hashes only `e004.py`. `compare` has no dirty flag; `forecast` does.
2. **No trial log in git.** `run_comparison.py` writes to git-ignored `data-dumps/research_lab/comparisons/`. Post-hoc runs such as `e001-family-ablation-1` are visible only through prose in M1, so the forking-paths count is not recoverable from the repo.
3. **No data-role partition.** Nothing stops a development query from reading snapshots that a future confirmation will use. E002 and E004 rely on "first N snapshots after commit X" rules, which works but is enforced per experiment by hand.
4. **No group-held-out or unseen-event split, and no time-block (date) bootstrap.** Both are required by `MODEL_COMPARISON_AND_VALIDATION.md` §5.
5. **No multiplicity control.** Every ledger test uses a nominal 95% CI. There is no α budget across E001–E004 or across the 5-model family inside E001.
6. **Storage is CSV.gz plus pandas, with no columnar or out-of-core layer.**
7. **No calibration or probabilistic targets.** All current targets are continuous `dmid` with SSE-based R2.
8. **Some estimators are duplicated outside `compare`.** `e003`/`e004` reimplement OLS, bootstrap and verdict logic instead of going through `compare`.

Don't reinvent any of these: the feature registry, the purge, paired cluster bootstrap, ablations, the append-only forecast log, write-once results, or the ledger. They are correct and adequate in shape. The gaps above call for extending them, not replacing them.

## 2. Evaluation of needs (lightest adequate tool for each)

| Need | Concrete problem here | Lightest adequate tool | Heavier tool justified when |
|---|---|---|---|
| Point-in-time feature store | Features must use only origin-side, receipt-clocked data | **Keep `features.py`** and extend `FeatureSpec` with `max_staleness` and source clock. The Phase 1–3 store remains the evidence store. | Never Feast or Tecton. They solve online/offline serving skew, and AREPO serves no model. |
| Reproducible datasets | E001 rebuilds pairs from CSVs, and the hash covers only 3 columns | A **dataset manifest**: snapshot ids plus file sha256, builder code sha256 and a full-frame content hash. Write it as Parquet (pyarrow) and commit the manifest JSON. | DVC or lakeFS only if data must be shared across machines or people |
| Purged, embargoed, grouped splits | Common shocks within a time block, and the unseen-event question | Add `split="group_holdout"` (frozen event-hash) and a **time-block bootstrap** option to `compare`. An embargo is unnecessary beyond the existing label-availability purge, because horizons are pair-defined. | Never a framework; this is about 100 lines |
| Regularised linear | Already done (closed-form ridge, numpy) | Add logistic/L1 through **scikit-learn** when a class target appears | n/a |
| Bayesian hierarchical | Partial pooling across categories and events (§6) | **numpyro on CPU**, or PyMC, fitted on **event-subsampled or aggregated** data (≤1–2M rows) | Full-data NUTS on more than 10M rows is the only GPU case, and subsampling is the better answer |
| Gradient boosting | The nonlinear challenger (§7) | **LightGBM on CPU**, with a fixed budget recorded in the registration | Never distributed below about 500M rows |
| Interaction discovery | E003 showed the effect is confined to a subgroup (wide spreads) | Pre-registered interaction sets in ridge. Grouped permutation importance and LightGBM `interaction_constraints`. Interactions found in development go to validation as new ledger entries. | SHAP-interaction or EBM only after a stable main-effect model exists |
| Experiment registry | Trial count, the forking paths, and α spent | **Markdown ledger plus a committed `trials.jsonl`**, one line per run of any comparison (run id, spec hash, data role, outcome hash) | MLflow only when more than 2–3 people, or more than about 500 runs a month need a UI |
| Dev vs confirmation | Nothing enforces separation | A role manifest plus a loader guard (§4) | Never a service |
| Model registry | One JSON spec, with the other specs in code | **`model_specs/*.json` with sha256, plus fitted artefacts** (coefficients, LightGBM text dump) under the same naming | MLflow registry only if models are served |
| Calibration | Not yet relevant (continuous targets) | When probabilistic targets arrive: isotonic or Platt in scikit-learn inside folds, event-clustered reliability | n/a |
| Prospective inference | Done for one model | Generalise `forecast.predict` to take any spec and run it from the collector loop (cron or launchd locally) | Dagster or Prefect only when more than about 5 scheduled pipelines exist with dependencies and failures to triage. GitHub Actions already exists for production. |
| Outcome scoring | Done per experiment, with duplicated code | One `score(spec, forecast_log, outcome_snapshots)` function reused by E002 and E004 | n/a |
| Monitoring and retraining | Drift in the coefficient (E001 slopes −0.28 to −0.37) | A per-period coefficient and feature-coverage table appended to the trial log. Retraining is itself a registered experiment (§6 "online updating"). | Evidently or W&B only for a live serving product |
| Audit | Reconstruct any claim from the repo | Extend the hash set (gap 1), keep the trial log in git, and record the role-access log | n/a |

## 3. Compute thresholds (with arithmetic)

**Stage A: full-universe snapshots at 4 per day for 1 year.** 1,460 snapshots.
- Raw rows: 272,660 × 1,460 ≈ 398M. At about 30 columns × 8 B that is about 95 GB uncompressed.
- On disk at today's 27 MB CSV.gz per snapshot: 1,460 × 27 MB ≈ **39 GB per year**. At E004's 2-hourly cadence (12 per day) it is ≈ **118 GB per year, or 324 MB per day**.
- **Today's 8.6 GiB of free disk fills in about 26 days at 12 per day.** Storage, not compute, is the first binding constraint, and it overlaps the existing D116 blocker.
- Eligible modelling rows: 43k × 1,460 ≈ 63M. With 30 features: float64 is 15 GB, float32 is 7.5 GB.

**Stage B: a dense panel of 5k markets at 1-minute resolution.**
- 5,000 × 1,440 × 365 ≈ 2.63B rows per year. At 50 float32 features that is about 525 GB.
- Subsampling origins to every 15 minutes gives 175M rows, about 35 GB.
- Rows at 1-minute resolution are heavily autocorrelated. Independent information is bounded by perhaps 1–2k events × time blocks, so subsample origins rather than buy memory.

**Training memory:**
- **Ridge or OLS:** streaming X'X needs O(p²) memory, so any N works chunk-wise from DuckDB or Parquet. Stage A trains in minutes on 8 GB.
- **LightGBM:** the binned matrix is about N·p bytes. For 63M × 30 that is about 1.9 GB, plus gradients and hessians (2 × 4 B × N ≈ 0.5 GB), for about 3–4 GB peak if the Dataset is built from float32 chunks. Going through a float64 pandas frame first needs 15 GB and **fails on this 8 GB machine**. A 16 GB machine handles Stage A comfortably. Time is about 10–40 minutes per fit for 500 trees on 8 cores, so a grid of 50 fits × 10 folds is roughly an overnight run. That is acceptable.
- **Hierarchical Bayes, NUTS:** one gradient is about 2·N·p ≈ 2 × 63M × 30 ≈ 4 GFLOP. 4 chains × 2,000 draws × about 30 leapfrog steps ≈ 240k gradients ≈ 1e15 FLOP. At about 50 GFLOP/s on CPU that is about 5–6 hours, if it converges at all.
  - Subsample to 1M rows, stratified so every event is kept (the information sits in groups, not repeated rows), and it drops to about 5 minutes.
  - **GPU (JAX) is justified only for full-data NUTS above about 10M rows, or for deferred deep sequence models.** For tabular gradient boosting and linear models with fewer than about 100M rows, CPU is adequate. The bottleneck is independent events, not FLOPs. So: **almost never.**
- **Bootstrap:** already aggregated per cluster, so 1,000 × 10k clusters is trivial.

**Thresholds:**
- The 8 GB laptop stops being enough once any single in-memory frame exceeds about 3 GB. That is roughly more than 12M rows × 30 float64, or about 60 snapshots of eligible pairs, which E004-scale pooling reaches in about a week of 2-hourly collection. Mitigate with DuckDB/Parquet plus float32 before buying hardware.
- A 16–64 GB VM is justified for Stage B, or for Stage A LightGBM grids.
- Distributed compute (Spark or Ray) is justified only above about 1B modelling rows that cannot be subsampled. That will not happen in this programme's horizon.

## 4. Statistical power and false discovery

**Calibrating from E001** (14,879 events, 161,902 test pairs, 4 periods):
- Event-clustered CI for B3 is [+0.004, +0.069], so SE ≈ 0.0166. The market-clustered CI gives SE ≈ 0.0043. That is a 3.9× ratio, a variance design effect of about 15, meaning roughly 15 pairs per effective observation.
- Paired difference (M1 family ablation, +0.030 [+0.011, +0.049]): SE ≈ 0.0097. Pairing roughly halves the SE.

Required event clusters N ≈ 14,879 × (SE_E001 · z / d)², with z = 1.645 + 0.84 = 2.49 (one-sided α = 0.05, 80% power):

| Effect d (R2_oos or paired ΔR2) | Unpaired vs B0 | Paired vs baseline | Paired, Bonferroni over 60 (z = 3.98) |
|---|---|---|---|
| 0.037 (E001 B1h size) | about 19k | about 7k | about 18k |
| 0.010 (plausible incremental feature) | about 254k | about 87k | about 222k |
| 0.005 | about 1.0M | about 347k | about 890k |

- The universe holds only about 10–15k active events at once, and events persist across periods. So **incremental effects below about 0.01 are not detectable from one cross-section.** They need many time blocks, and the binding unit becomes the time block.
- The per-period SD of B1h R2 is about 0.016 across 4 periods. Detecting d = 0.01 at the period level needs n ≈ (2.49 × 0.016 / 0.01)² ≈ **16 independent periods**. d = 0.005 needs about 64 periods.
- Periods a few hours apart share events and news, so count days or weeks, not snapshots. Report two-way (event × time-block) clustering. The current single-way event clustering still understates uncertainty from common shocks.

**Proposed governance scheme** (fits the existing ledger; no new service):

1. **Role assignment at collection time, deterministic and committed in advance.** A committed `docs/research_lab/DATA_ROLES.md` defines:
   - **Time role:** ISO week number mod 4. Weeks 0–1 are DEV, week 2 is VALIDATION, week 3 is SEALED.
   - **Event role** (for the unseen-event question): `sha256(salt‖event_id) mod 10 ≥ 8` → HELD-OUT-EVENT. The salt's hash is committed first and the salt revealed only at confirmation.
   - Alternating weeks cost some recency. A pure forward split ("everything after date D is SEALED") also works but leaves no development data later on. Interleaving keeps all three roles growing.
2. **Loader guard.** A single `load_pairs(role=...)` reads the role manifest. SEALED rows load only when passed a `model_spec` whose sha256 appears in a ledger entry with status REGISTERED. Every load appends `{time, role, spec_sha, purpose}` to a committed `access_log.jsonl`. Without code-level enforcement, the vault is only a convention.
3. **Ledger semantics:**
   - DEV: unlimited exploration, every run logged to `trials.jsonl`.
   - VALIDATION: registered entries, which may still be iterated a declared number of times.
   - SEALED: registered and frozen spec, one shot, verdict final. This matches what E002/E004 already do by hand and E003's S1/S2.
4. **α-spending.** Give confirmation an annual budget of α = 0.05 family-wise. Each SEALED registration declares its α_i, and the ledger tracks the cumulative sum. LORD/alpha-investing (online FDR) is the principled sequential alternative. Validation-stage results use Benjamini–Yekutieli over the 60 cards grouped into families, which is dependence-robust. Development results only nominate candidates.
5. **Retire a vault slice once its outcome has been inspected.** It becomes DEV, and this is logged.

## 5. Staged platform

**Stage 0 (now: four experiments, one modeller, an 8 GB laptop)**
- **Build:**
  - Extend the hashes to `panel.py`, `evaluate.py` and `models.py`, hash the full frame, and add a dirty flag.
  - Commit `trials.jsonl`.
  - Move E003/E004 scoring onto `compare`.
  - Add a time-block bootstrap option.
  - Write and commit `DATA_ROLES.md` **before** the E004 loop accumulates further. New data is the scarce asset.
- **Do not build:** MLflow, Feast, Dagster, W&B, GPU work, or a new dataset store.

**Stage 1. Entry trigger:** any of the following:
- more than 30 snapshots, or more than 3 GB of research-lab data;
- any frame above 3 GB in memory;
- more than about 10 registered experiments;
- the first SEALED read.

Components:
- Parquet via pyarrow, with DuckDB for out-of-core pair building.
- Role loader guard plus the access log.
- Generalised `forecast.predict` and `score`, run per snapshot by the collector loop.
- A storage plan for growth of about 120 GB per year. This needs **user approval**, because it means an external disk or paid object storage.
- scikit-learn (logistic, isotonic) when a class target is registered.
- **Do not build:** an orchestrator or a model UI.

**Stage 2. Entry trigger:**
- a development-stage effect that survives VALIDATION with the paired CI above 0, **and**
- more than 16 independent time blocks with more than 50k event clusters.

Components:
- LightGBM and numpyro as pinned optional dependencies (`[research]` extra), with a fixed search budget declared per registration.
- Event-held-out evaluation.
- A 16–32 GB VM or desktop if the measured peak exceeds 6 GB.
- **Do not build:** ensembles (Phase 7), GPU, or distributed compute.

**Stage 3. Entry trigger:**
- two or more constituents locked with SEALED-confirmed gains, **and**
- the Phase 3 / D116 panel accepted, **and**
- more than 5 scheduled pipelines.

Components:
- An ensemble tournament on identical origins (§8).
- A lightweight scheduler (Dagster or Prefect, self-hosted) only if cron failures become the bottleneck.
- MLflow only if collaborators join.
- **Do not build:** deep sequence or graph models unless simpler models leave a stable residual with more than 100k independent event-blocks.

## 6. Ranked recommendations

1. **Useful now: write and commit `DATA_ROLES.md` and a loader guard before more collection.** Every snapshot collected without a role is effectively DEV-only for future hypotheses. This is cheap, and it is impossible to apply retroactively.
2. **Useful now: close the provenance gaps.** Hash `panel.py`, `evaluate.py` and `models.py`; hash the full pair frame; add a dirty flag to `compare`. Commit a `trials.jsonl` with one line per comparison run, including post-hoc runs. Without the trial count, FDR control has no denominator.
3. **Useful now: add a time-block (day) bootstrap or two-way clustering to `compare`, and report it alongside event clustering.** E001 showed the market→event change widened CIs about 4×. Time-block dependence is likely the next 1.5–3×. E004's 8-of-11 rule partly covers this.
4. **Prepare next: storage and columnar migration.** At 324 MB per day against 8.6 GiB free, a continuous loop exhausts the disk in about 3–4 weeks and competes with D116. Plan Parquet/DuckDB and an external-storage decision; the latter is a user decision because it involves cost or a device.
5. **Defer: LightGBM, Bayesian hierarchical models, MLflow, orchestrators and GPU.** At about 10–15k concurrent events, the plausible incremental effects (≤ 0.01) need about 16+ independent time blocks before any challenger model can be distinguished from ridge. Complexity now would only add forking paths.

## Three least-certain assumptions

1. **SE scaling as 1/√events, using the E001 SE.** E001 had only 4 periods, and its B3 event-clustered SE is itself noisy. Between-period heterogeneity may dominate, which would make the sample sizes above optimistic.
2. **Storage growth of 27 MB per snapshot, and Parquet savings.** These were measured from a single snapshot. Parquet's gain over CSV.gz is not measured, and the universe size (272k markets) may change.
3. **Event identity as the right independence unit.** Neg-risk groups and cross-event themes (elections, macro) link events. If those links are strong, effective N is smaller still, and clusters should be connected components, as §5 of the validation doc already suggests.
