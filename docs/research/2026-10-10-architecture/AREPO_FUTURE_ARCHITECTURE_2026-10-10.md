# AREPO future architecture, data economics, ML platform and product: research package

**Date:** 2026-10-10 (prices retrieved the same day).
**Status:** Independent strategic research. Read-only against the repository. No spending, deployments or production changes.
**Intended integration point:** `docs/research/2026-10-10-architecture/` (proposed), or input to Phase 09, at the main orchestrator's discretion.

**Method.** Four independent specialists each produced a report:
- data and storage;
- ML systems;
- cloud economics;
- product and UX.

The lead merged them into a proposal. An independent challenger (science-reviewer) then reviewed it and returned **REVISE**. The lead responded and made the final decisions in §9. Specialist reports are kept alongside this file.

**Evidence labels:**
- **OBS:** measured from the repository or disk, with the source path given.
- **REP:** reported in docs or the brief, not re-measured.
- **EST:** an estimate, with the arithmetic shown.

---

## 1. Executive summary (plain English)

1. **AREPO's bottleneck is not compute. It is disk, backup and uninterrupted collection.**
   - The research laptop has 8 GB RAM and 8 cores (OBS), which is enough for every model the programme can currently justify.
   - Its 228 GiB disk is 95–96% full, with 8.6–11 GiB free and the figure changing as the main session works (OBS).
   - It holds 20–21 GB of research evidence that has **no offsite copy and no Time Machine** (OBS).
   - That single point of failure is the largest risk to the programme today.
2. **The evidence compresses extremely well.**
   - `data-dumps/` holds about 33.5 GB of actual content (OBS). A verified, streamed `zstd --long` archive of all of it is estimated at about 2 GB (EST, ±2×).
   - Separately, about 15 GB of disk can be reclaimed **losslessly**, with nothing deleted, by extending the exact-byte compression already approved in principle (D099). That would unblock D116.
   - Both need the user's approval.
3. **Storage is cheap; reliability costs money.** At any realistic AREPO workload, offsite object storage costs $1–10 a month. The only cost that matters is an always-on collector, about €6–7 a month, and it buys scientific integrity:
   - Prospective cohorts that the laptop misses can never be reconstructed.
   - GitHub cron is officially documented as able to delay or drop runs.
   - The production scan cron has been paused since 2026-08-22 (OBS).
4. **The format, not the database, is the problem.**
   - About 89% of a 27 MB compact snapshot is two long ID columns (OBS).
   - Moving IDs into an immutable lookup map and storing new collections as Parquet + zstd with exact decimals would cut snapshots about 10× (EST).
   - Parquet files plus DuckDB on the laptop are the right analytical store. Postgres is for the product only. A time-series database, a feature-store platform, MLflow, orchestrators and GPUs are all unjustified for now.
5. **Statistics limit how many hypotheses can be tested.**
   - Event clustering inflates variance about 15× (OBS, E001).
   - Detecting a realistic improvement over momentum (ΔR² ≈ 0.01) needs tens of thousands of event clusters spread over many independent days (EST).
   - AREPO should therefore run **2–4 confirmatory tests at a time**, each with a stated minimum detectable effect. Development screening should decide which hypotheses earn those scarce confirmation slots.
6. **The irreversible scientific loss today is full order-book depth.**
   - Book sweeps keep top-of-book and 1c/5c depth summaries only. Individual levels and raw responses are discarded (OBS).
   - Depth and shape features can never be backfilled.
   - A bounded, registered 6-hour full-depth collection is the cheap way to keep that research option. It serves development only; confirmation always needs fresh data.
7. **The honest product today is a verifiable track record, not an "opportunity" screener.**
   - The current home page is titled "Opportunities" and headlines a momentum call, which is the very baseline AREPO is trying to beat (REP, product specialist).
   - The defensible public product is a timestamped, hash-committed **forecast ledger plus open lab notebook**, with failures kept visible.
   - Forecast cards should appear only after a prospective confirmation, and alerts only after a positive economic verdict.
8. **Nothing here should touch E002/E004/E005 or D116 while they run.**
   - No collector or format changes until the running series finish.
   - Backups run at low priority on static directories only.

**What the user needs to decide now** (§9.3):
- a backup destination: an external disk, a free cloud tier, or both;
- a storage session to approve lossless compression of about 15 GB.

**Later decision:** an always-on collector at about €7 a month, after a paired trial.

---

## 2. Verified current state

| Item | Finding | Label / source |
|---|---|---|
| Research machine | 8 GB RAM, 8 cores; disk 228 GiB, 95–96% used, 8.6–11 GiB free | OBS `sysctl`, `df` |
| `data-dumps/` | 20–21 GB on disk; ~33.5 GB logical; 4 captures already APFS-compressed ~6.4×; ~17.7 GB still uncompressed | OBS `du -sk` vs `du -skA` |
| Offsite backup of research data | **None**. No Time Machine. `data-dumps/` is git-ignored. | OBS `tmutil` |
| Production DB backup | Weekly `pg_dump` as a GitHub artifact, cut from daily to stay under Supabase Free's 5 GB egress | OBS `.github/workflows/backup.yml` |
| Production scan | Cron **commented out since 2026-08-22**, after the DB reached 935 MB against the 500 MB Free cap. The collect workflow is still scheduled. | OBS `scheduler-scan.yml` |
| Repo visibility | `dayyansheikh/Arepo` is **PUBLIC**: Actions minutes are free; nothing data-bearing may be committed | OBS `gh repo view` |
| Universe scan | 276,706 / 275,906 / 272,660 markets in 7m07s / 6m42s / 11m44s. "7 minutes" was true only of the first run. | OBS snapshot manifests |
| Compact snapshot size | 15.5 MB (first, no token column), then **27.7 / 27.4 MB** csv.gz (~100 B/market). "16 MB" is out of date. | OBS |
| What the snapshot keeps / drops | Drops raw Gamma JSON (~1.78 GB per scan), events, tags, fees, rewards, tick size, `outcomePrices`, second token. Decimals are parsed to float and raw is not kept, so page hashes cannot be re-verified. | OBS `extract.py:56-75`, `collector.py` |
| Order-book sweep | 43,420 books in 79.5–81.6 s (first series); 42,386 books in 116–141 s (second). 4.25 MB per sweep (~100 B/book). Raw 58–59 MB discarded (`keep_raw: false`). | OBS |
| Sweep coverage | Only E001-eligible markets (spread ≤ 0.10, mid 0.02–0.98, >3h to end), outcome-0 token: **~15.5% of the universe, not "all books"** | OBS `book_sweep.select_tokens`, `panel.eligibility_mask` |
| Book depth | Mean 32.8 levels, max 318. Only top-of-book plus 1c/5c depth and level counts kept. | OBS |
| fs2 captures | One directory per 100-market page: `raw.bin` (exact body, 580–730 KB JSON), plus derived `parsed.json` and `frame_page.json` (~58% of each capture) | OBS |
| Market-count growth | 236.6k (Oct 3) to 273–277k (Oct 10): +15% as a step. Also −4k within 90 min (unexplained churn). | OBS e001 manifest |
| ML/research code | `backend/astrolabe/research_lab/` (~2.9k lines, 8 test files) | OBS |
| Python environment | numpy 2.4.6, pandas 2.3.3 only. No scipy, sklearn, statsmodels, pyarrow, duckdb, polars, lightgbm, pymc or mlflow. | OBS venv |
| Forecasting status | E001 exploratory reversal (R²_oos +0.037; likely partly an errors-in-variables artefact of quote noise, per the ledger). E003 null for book imbalance at ~2 min. E002/E004/E005 pending prospectively. **No validated edge.** | OBS `EXPERIMENT_LEDGER.md` |

**What the research lab already does.** These are real strengths to extend, not rebuild:
- Origin-only feature registry that refuses label columns (`features.py`).
- Training purged by label-availability time (`evaluate.purged_train_mask`). Lambda is chosen on an inner time split and never on test data.
- Event-clustered paired bootstrap with resamples shared across models (`compare.paired_bootstrap`).
- Family ablations that also drop dependent features (`compare.ablations`).
- Append-only forecast log with spec and snapshot hashes checked at scoring time (`forecast.py`).
- Write-once result directories and a pre-registration ledger.

**Gaps:**
- **Partial code hashing.** `compare.code_sha256` hashes only `compare.py` and `features.py`, not `panel.py`, `evaluate.py` or `models.py`. There is no dirty-tree flag and no environment lock hash.
- **No committed trial log.** Comparison runs land in git-ignored `data-dumps/`.
- **No multiplicity control, time-block inference or held-out-event split.**
- **Duplicated logic.** `e003` and `e004` re-implement estimator and bootstrap code that `compare` already provides.
- **Text-only storage.** Everything is CSV.gz read through pandas.

---

## 3. Architecture proposal: ingestion to user experience

```
Polymarket Gamma / CLOB / Data API (public)
        │  one canonical collector host (laptop now; small VM after paired trial)
        ▼
[Receipts]  raw responses: change-only Gamma objects + weekly full anchor; raw L2 books in registered collections
        │  sha256 manifest per capture (host, NTP offset, clamp count, code+env hash, dictionary version)
        ▼
[Observations]  per-capture immutable Parquet+zstd, exact decimals, IDs as integer keys
        │  + append-only ID map (immutable) + change-history table for mutable metadata (tags, fees, tick, rewards)
        ▼
[Analytical store]  local Parquet lake + DuckDB queries (laptop); offsite copy in private object storage
        │
        ▼
[Research lab]  existing research_lab: point-in-time features → purged splits → models (ridge / logistic now;
        │       GBM / hierarchical later) → event-clustered + per-day inference → registered prospective forecasts
        │       + committed trials.jsonl + post-registration confirmation windows
        ▼
[Forecast ledger]  append-only forecasts with commitment hashes → outcome collection → scoring vs B0/B1 baselines
        ▼
[Serving]  small derived tables pushed to Postgres (Supabase) → FastAPI → Next.js
           public: ledger + lab notebook (+ descriptive context later); Labs: researcher workbench, same backend
```

**Design principles behind the diagram:**
1. **Receipts, not just numbers.** The cheapest insurance for features nobody has invented yet is raw source responses kept where they change, plus exact decimals. Recomputing derived tables is cheap; recovering lost source bytes is impossible.
2. **One file per capture, immutable, hashed.** The file is the unit of backup, restore and provenance. This fits the existing manifest and capsule culture.
3. **Postgres serves, it does not archive.** The Supabase overflow to 935 MB is direct evidence of this.
4. **Reversible choices.**
   - Parquet is an open format, and DuckDB is a library rather than a server.
   - Object storage is S3-compatible across R2, B2 and AWS, so providers can be swapped.
   - Nothing here locks in a vendor.

---

## 4. Storage growth and retention model

### 4.1 Per-family unit sizes

| Family | Unit size | Label |
|---|---|---|
| Compact snapshot, current csv.gz | 27.4 MB per universe scan | OBS |
| Same, per-column zstd (Parquet proxy) | 20.5 MB, of which IDs are 18.3 MB | OBS |
| Normalised snapshot (IDs moved to a lookup map) | ~2.2–2.5 MB | EST from OBS |
| Book sweep summary | 4.25 MB (3.3 MB columnar; ~1.9 MB without token ID) | OBS |
| Full-depth L2, eligible books, parsed | ~6 MB per sweep | EST, untested |
| Full-depth L2, raw gz | ~7–10 MB per sweep | EST, untested |
| Raw Gamma, change-only | ~6.5 MB per day | EST |
| Raw Gamma weekly full anchor | ~117 MB per week gz (~16.7 MB/day) | EST |
| Trades | ~50 B/trade × an unknown count (1M/day assumed) | EST, very uncertain |

### 4.2 Projections

Assumptions:
- constant 273k markets;
- for 2× per year market growth, multiply the 1-year total by 1.44 and the 3-year total by 3.37;
- the growth rate rests on one weekly step and is uncertain.

| Strategy | 1 mo | 6 mo | 1 yr | 3 yr |
|---|---|---|---|---|
| Current csv.gz snapshots, 6h | 3.3 GB | 20 | 40 | 120 |
| Current csv.gz snapshots, 1h | 20 | 120 | 240 | 720 |
| Current csv.gz, 2-hourly (E004-style loop) | 9.7 | 58 | 118 | 355 |
| **Normalised snapshots, 6h** | 0.3 | 1.8 | 3.7 | 11 |
| Normalised snapshots, 1h | 1.8 | 11 | 22 | 66 |
| Normalised snapshots, 15 min (infeasible: a scan takes 7–12 min) | 7.2 | 44 | 88 | 263 |
| Full-depth L2, eligible books, 6h (parsed) | 0.7 | 4.4 | 8.8 | 26 |
| Full-depth L2, 1h | 4.3 | 26 | 53 | 158 |
| Targeted panel, 2k markets at 5 min | 2.4 | 15 | 30 | 88 |
| Targeted panel, 5k markets at 1 min | 30 | 183 | 368 | 1,100 |
| Trades (1M/day assumption) | 1.5 | 9 | 18 | 55 |

**Recommended baseline plan.** This is corrected by the challenger to include raw receipts.

Daily volume:

| Component | MB/day |
|---|---|
| Normalised 6h snapshots (4 × 2.5 MB) | 10 |
| Raw L2 gz at 6h (4 × 7–10 MB) | 28–40 |
| Change-only raw Gamma | 6.5 |
| Weekly Gamma anchor | 16.7 |
| **Total** | **≈ 61–73** |

Parsed L2 is not stored separately because it can be re-derived from the raw responses. Per year:

| Basis | GB/yr |
|---|---|
| Flat market count | ≈ 22–27 |
| With 2× growth, year 1 | ≈ 32–39 |
| With 2× growth, 3-year total | ≈ 75–90 |

This is the **Low** workload in §5. **Base** (~300 GB/yr) corresponds to adding a 2k-market 5-minute panel plus trades. **High** (~2 TB/yr) corresponds to dense 1-minute panels or high-cadence full depth.

**Time to fill the current free disk:** current-format 2-hourly ≈ 26 days; current-format 1h ≈ 13 days.

### 4.3 What each data level allows you to recover later

| Retained level | Can later compute | Cannot |
|---|---|---|
| Top-of-book + 1c/5c depth summaries (today) | spread, mid, microprice, near-touch imbalance | depth-weighted imbalance, book shape or slope, wall detection, level-count dynamics, any feature beyond 5c |
| Full-depth L2 at 6h | book shape and slope at 6h to multi-day horizons, cross-sectional depth features | queue, cancel or replenishment dynamics; anything minute-scale |
| Top-10 levels at 1h | most shape features at 1h | far-book liquidity (measure the share of depth beyond 10 levels first) |
| Raw Gamma change-only + anchors | as-known tags, fees, rewards, tick size, category, metadata revisions | nothing within its cadence |
| No raw Gamma (today) | current values only | as-of metadata history: **Gamma serves only current metadata** |
| Trades and wallets | probably backfillable from Data API or on-chain fills | UNVERIFIED; needs one bounded probe |

**Key scientific constraint (challenger).** Under AREPO's prospective rule, banked historical data can only ever be **development** data. Its value is in choosing which hypotheses earn scarce confirmation slots, not in confirming them.

### 4.4 Tiered retention policy

| Tier | Contents | Treatment | Information lost |
|---|---|---|---|
| **T0 Canonical** | evidence capsules (4.4 MB, the only record of 1.82 GB of retired runs), D082/D088/D094/D097/D114 frames, frozen forecasts and protocols, EVIDENCE JSONs | Never delete. Exact-byte compression only, in a user storage session, with before/after per-file sha256. First in every backup. | None |
| **T1 Exploratory raw** | `research_lab` snapshots and sweeps, non-canonical pilots, future raw receipts | Keep originals. New collections are written as Parquet only *between* registered series, after an equivalence test. | None |
| **T2 Reconstructable derived** | `parsed.json`, `frame_page.json`, `projection.json`, extracts, comparison outputs | Retire only capsule-first under `PHASE_03_BOUNDED_RETENTION.md`, with approval, and never inside canonical runs | Historical parser output: replay becomes re-derivation by current code |
| **T3 Redundant physical bytes** | uncompressed copies of the above | Transparent APFS compression, ≈17.7 GB to ≈3 GB on disk | None |

---

## 5. Deployment options and monthly cost

Prices are as of 2026-10-10, mostly in USD. Hetzner prices are in EUR excluding VAT; possible 20% UK VAT is flagged, not assumed. The full table with citations is in `specialist_economics.md`. Key official rates:
- **Cloudflare R2:** $0.015/GB-month, free egress, 10 GB free.
- **Backblaze B2:** $6.95/TB-month, egress free up to 3× stored, first 10 GB free.
- **Hetzner CX23:** €5.49 (2 vCPU, 4 GB, 40 GB), excluding VAT and IPv4, after the 15 Jun 2026 rise.
- **Supabase Pro:** $25 with 8 GB included, then $0.125/GB.
- **Vercel Hobby:** $0 but **non-commercial only**.
- **GitHub Actions:** free for public repos; schedules "may be delayed… dropped".

**Three architectures:**
- **A, local-first:** laptop, external disk and B2.
- **B, lean hybrid:** one small VM collector, R2 and the free product tiers.
- **C, managed AWS:** EC2 in a public subnet, RDS micro and S3 tiered.

USD per month, excluding VAT:

| Workload | Arch | Month 1 | Month 6 | Month 12 | Month 36 |
|---|---|---|---|---|---|
| **Low (≈ recommended plan, 50 GB/yr)** | A | 4.7 | 4.8 | 5.0 | 5.7 |
| | B | 11.7 | 12.0 | 12.4 | 13.9 |
| | C | 35.6 | 35.4 | 35.5 | 35.9 |
| Base (300 GB/yr: + 5-min panel + trades) | A | 4.8 | 5.7 | 6.8 | 10.9 |
| | B | 12.0 | 13.9 | 16.2 | 25.2 |
| | C | 36.0 | 37.1 | 37.7 | 41.0 |
| High (2 TB/yr: dense 1-min panels) | A | 10.2 | 16.0 | 23.0 | 50.8 |
| | B (R2 / B2) | 22 / 20.5 | 34.5 / 26.3 | 49.5 / 33.3 | 109.5 / 61.1 |
| | C | 68 | 78 | 82 | 104 |

**Notes on these figures:**
- A and B include about $4.6/month for a 4 TB external HDD (~£130) amortised over 36 months.
- If the product becomes commercial, add Vercel Pro at $20.
- Add Supabase Pro plus Render Starter (+$32) only when their triggers fire.

**Bounds.** The low and high estimates for each cell are the workload rows themselves. Price uncertainty is ±20% for VAT and ±10% for the USD/EUR rate.

**What drives cost:** at Low and Base, always-on compute is the cost driver in B and C. Storage stays under about $10 a month.

**Surprise-charge risks and guards:**
- **Per-object writes.** Writing one object per order book would mean about 124M writes a month, roughly **$557/month on R2**. Batch to one file of at least 16 MB per capture.
- **AWS NAT Gateway:** about $33/month plus $0.045/GB. Use a public subnet only.
- **CloudWatch logs:** cap retention at 14 days.
- **Minimum storage durations:** S3-IA has 30 days and Glacier 90–180 days, so don't tier short-lived files.
- **Supabase egress:** 5 GB/month on Free. This already forced weekly backups.
- **Vercel function overage** applies on Pro only; use a hard pause.

**Universal guards:**
- budget alerts and hard spend caps where offered;
- one bucket per environment;
- lifecycle rules written down before any upload.

**When spending becomes justified:**
- **External disk:** justified now. The disk is past 80% full and there is no second copy.
- **Always-on VM (A to B):**
  - the laptop log shows more than 1% missed or late (>10 min) slots over 14 days during a registered series, **or**
  - a registered experiment's minimum detectable effect calculation needs more independent days than an intermittently-on laptop can deliver, **and**
  - the paired laptop–VM trial (§8, C4) passes.
- **Managed AWS (B to C):** only for one of these:
  - a commercial launch with an SLA;
  - a product DB larger than 8 GB;
  - more than one collector host;
  - an archive larger than about 5 TB;
  - a regulatory or contractual audit need.

  None is in sight.
- **Bigger compute (16–64 GB VM):** only for a registered dense 1-minute panel, or GBM grids on more than about 3 GB of in-memory frames.
- **GPU:** not foreseeable. Tabular models here are limited by independent events, not FLOPs.

---

## 6. Staged ML and research platform

**Compute arithmetic (EST, from the ML specialist).**

Data volumes:
- One year at 4 snapshots a day is about 398M raw rows, or about 63M eligible rows.
- 30 features take 7.5 GB as float32.

Model costs:
- **Ridge:** streams X'X (memory grows with features squared, not rows).
- **LightGBM:** about 3–4 GB peak when built from float32 chunks. A float64 pandas frame **fails on 8 GB**.
- **Full-data hierarchical NUTS:** about 5–6 h. A 1M-row event-stratified subsample takes about 5 min.

**Power (calibrated on E001; arithmetic re-derived by the challenger):**
- The event-clustered SE is 0.0166, against 0.0043 market-clustered: a variance design effect of about 15.
- Paired ΔR² = 0.01 needs about 87k event clusters (about 222k with Bonferroni across 60 tests). ΔR² = 0.037 needs about 7k–19k.

**Caveats on these power figures:**
- The 0.037 is probably inflated by the quote-noise errors-in-variables artefact.
- The period SD comes from only 4 periods, so the required number of independent days could be about 5 or more than 200.
- E004's 11 periods cover about one day and count as roughly 1–2 independent time blocks.

**Implications:**
- Every registration states its minimum detectable effect.
- Run 2–4 confirmatory tests at a time.
- Treat ΔR² < 0.02 as out of reach until months of independent days exist.

| Stage | Entry trigger (measured) | Build | Do not build yet |
|---|---|---|---|
| **0, now** (while E002/E004/E005 run) | none | 1. Full-module code hash plus dirty flag plus environment-lock hash in every result. 2. Auto-appended, committed `trials.jsonl` (every run, including post hoc). 3. Minimum detectable effect statement in each registration. 4. Per-day period tests or randomisation across days, with event clustering within days (two-way clustering is unreliable below ~20 time clusters). 5. Fold `e003`/`e004` estimators back into `compare`. | anything touching the running collectors or `snapshots/` |
| **1** | E004/E005 scored, **or** more than 30 snapshots, more than 3 GB of frames, or more than 10 experiments | Immutable ID map plus per-capture Parquet with exact decimals, behind a value-equivalence test against the CSV writer. DuckDB and pyarrow as pinned extras. Post-registration confirmation-window rule written into the ledger template. Generic forecast and scoring. Paired laptop/VM trial. | loader "guard" enforcement, SCD-2 for IDs, LORD |
| **2** | an effect survives development and validation, with at least 16 independent days and at least 50k event clusters | LightGBM and numpyro (pinned optional), event-held-out evaluation (salted hash, salt committed), reliability diagrams (CORP with resampling bands), interaction screening with family-wise control | MLflow, Feast, orchestrators |
| **3** | at least 2 locked constituent models, D116 accepted, more than 5 recurring pipelines | ensemble tournament; Prefect/Dagster and MLflow *only if* cron plus manifests demonstrably fail | GPU, distributed compute |

**Data governance (final, after the challenger):**
- **Confirmation data.** Use only origins strictly after the registration commit, within a window declared at registration. Drop origins whose label window crosses the window edge. AREPO already uses this rule (E002/E004/E005).
- **Calendar partition rejected.** The ISO-week mod-4 partition the ML specialist proposed is rejected: it leaks labels across block edges, takes 4× longer to confirm, and is redundant with the rule above.
- **Development data:** everything banked. Unlimited use, all runs logged in `trials.jsonl`.
- **Unseen-event questions:** a salted event-holdout hash, only when a registration asks one.
- **Multiplicity:** a pre-declared α per registration, Holm within a declared family, tracked in the ledger. This suits a programme running about 1–5 confirmatory tests a year. LORD/alpha-investing is premature.
- **Access log:** an audit convention, not "enforcement". It is a single-user repo with plain files.
- **Not retroactive:** none of this relabels E002–E005 verdicts or reassigns their snapshots. It applies from E006.

---

## 7. Product directions

These are summarised from `specialist_product.md`, which also covers the competitive landscape and wording examples.

| Concept | User | Honest today? | Cost | Main risk |
|---|---|---|---|---|
| **A. Verifiable forecast ledger** (hash-committed forecasts, auto-scored against momentum, failures visible) | forecasters, quants, sceptical journalists | **Yes** | low–moderate | outsiders may not value a record of mostly null results |
| **B. Market-context explainer / anomaly screener** (what moved, when, how unusual, descriptively) | journalists, analysts | Yes, if descriptive | moderate | drifts towards "insider" or "smart money" readings |
| **C. Open lab notebook** (one page per experiment, from pre-registration to verdict) | researchers, credibility seekers | **Yes** | low | niche audience |
| **D. Alerts-first** | traders | **No**: needs a positive Phase 08 economic verdict | moderate | implies advice; highest regulatory and reputational risk |

**Recommendation.** One application sharing a backend and design system, with separate Labs and public navigation and a promotion gate between them. The public product is **A + C now**, with B as a descriptive layer next. Forecast cards on market pages follow a prospective confirmation. D waits for a positive economic verdict.

**Stating predictive value honestly:**
- skill scores against both B0 (no change) and price-plus-momentum, the latter being the incremental test;
- event-clustered intervals;
- three counts always shown: forecasts, unique markets and unique events;
- the share of skill contributed by the top 5 events;
- abstention coverage, with abstentions scored as the baseline;
- economics as separate rows: gross, net of half-spread, net of fees and delay, and "real fills: not measured".

**Features to avoid** (they look like a trading product but carry no validated information):
- strength gauges;
- red/green arrows;
- "smart money" tags;
- a headline "30% reversal" figure.

**Current-surface issues for the main team (low cost, production copy changes, need user sign-off):**
- Rename or demote "Opportunities".
- Label the momentum call as the *baseline*.
- Give Research Lab question titles and readable score tables instead of IDs and raw JSON.
- Reword Replay so it does not imply realised profit.

**Source rights.** Polymarket's Terms of Use body could not be retrieved, and no API licence was found in its docs. **Commercial use or redistribution of raw data is UNVERIFIED.** A human, ideally counsel, should read the terms before any paid tier, data export or public raw download. Backups and buckets must be private, especially since the repo is public.

---

## 8. Adversarial review: outcomes

| # | Issue | Challenger verdict | Lead decision |
|---|---|---|---|
| C1 | ISO-week mod-4 data roles | REJECT | **Adopted rejection.** Post-registration confirmation windows with a horizon embargo instead. |
| C2 | Power and how many tests to run | ACCEPT WITH CHANGE | **Adopted.** Minimum detectable effect per registration; 2–4 concurrent confirmatory tests; per-day inference. Measure the per-day SD of R²_oos over at least 10 distinct days, and the share contributed by the top 5 events. |
| C3 | 6h full-depth L2 "option value" | ACCEPT WITH CHANGE | **Adopted with a partial disagreement.** The lead agrees banked L2 is development-only, but holds that development screening is exactly what allocates the 2–4 scarce confirmation slots. So a bounded L2 collection (registered, end-dated, cohort-aligned) is worth its ~10–15 GB/yr. **Resolve by:** one `keep_raw=True` sweep (actual bytes, depth share beyond 10 levels and 5c) plus a one-day hourly series (1h/6h autocorrelation of shape features). If top-10 at 1h dominates, switch. If no book-shape hypothesis is selected for confirmation within ~8 weeks, stop collecting. Decide eligible vs universe frame at registration. |
| C4 | VM vs laptop comparability | DEFER-PENDING-MEASUREMENT | **Adopted.** Add `collector_host`, NTP offset and clamp-event count to manifests (`collector.py:166-167` silently clamps backward clocks). Paired 2–3-cycle trial outside `snapshots/`, comparing quote equality, `updated_at` age, duration, 429s and peak RSS. Never switch hosts inside a registered series; no pooling across hosts unless registered. |
| C5 | Risk to running work and evidence | ACCEPT WITH CHANGE | **Adopted ordering:** (1) back up static directories only, under `nice`, with `zstd -9 --long`; (2) let E004/E005 finish; (3) then writer and host changes, behind equivalence tests. Canonical-directory compression only in a user storage session. Reconcile "defer trades" with the main session's untracked `trade_sample.py`, which looks like the bounded trade probe this package recommends. |
| C6 | Over-engineering | ACCEPT WITH CHANGE | **Adopted.** Append-only immutable ID map (not SCD-2) plus a change-history table only for mutable metadata. No hive partitioning or hourly push before Parquet exists. Holm, not LORD. Access log as a convention. |
| — | Archive dependency | — | **Adopted.** Every normalised manifest carries the ID-dictionary version hash, and every backup or capsule includes the dictionary. |
| — | Budget understated | — | **Adopted.** Corrected to ≈22–27 GB/yr flat (§4.2). |
| — | "Offsite" | — | **Adopted.** A USB disk at home is local. The target is one local external copy plus one remote copy, both restore-verified. |
| — | A to B "already triggered" (economics) | — | **Lead disagrees with the economics specialist.** Disk pressure triggers the external disk and compression, not the VM. The VM trigger is the gap log or the minimum-detectable-effect calculation, plus a passed paired trial. |

**Most likely still wrong:**
1. Full-depth L2 bytes per sweep (untested).
2. The 2×/year market-growth assumption (one step, plus unexplained churn).
3. Archive size (±2×).
4. Power inputs.
5. Hetzner VAT, IPv4 pricing and IP acceptance by Polymarket.
6. Backfillability of trades and wallets.

---

## 9. Final decisions, assumptions and open questions

### 9.1 Decisions (lead)
1. **Back up first.** Copy T0 plus `research_lab` (≈0.4 GB) now. Then stream a verified archive of all of `data-dumps/` (≈2 GB) to one local external and one remote private destination, with restore plus sha256 verification at each. Ongoing nightly increments of about 34 MB/day.
2. **Lossless space recovery.** Extend D099 exact-byte compression to all uncompressed directories (≈15 GB freed), in a user storage session. This unblocks D116.
3. **Formats.** New families use per-capture Parquet + zstd with exact decimals, an immutable ID map and a metadata change-history table. DuckDB on the laptop. Postgres for serving only. No time-series database. Existing CSVs are frozen as-is and labelled "lossy-parsed, raw not retained".
4. **Collection.** Complete enumeration at 6h, aligned to 00/06/12/18 UTC, is the sampling frame. Targeted, L2 and trade panels are bounded registered collections drawn from the frame. Event-triggered capture is deferred because of selection-on-outcome risk.
5. **Receipts.** Change-only raw Gamma plus a weekly anchor. Raw L2 inside registered collections.
6. **Governance.** Post-registration confirmation windows; minimum detectable effect per registration; 2–4 concurrent confirmatory tests; Holm within families; committed `trials.jsonl`; full code and environment hashes; per-day inference.
7. **Compute.** Laptop through Stage 1. No GPU, MLflow, Feast, orchestrator or managed time-series database.
8. **Collector host.** Laptop with a gap ledger until a paired trial. Then a small VM (≈€7/month incl. VAT) as canonical collector, switched only between series.
9. **Product.** Ledger + lab notebook now. Descriptive context next. Forecast cards after confirmation. Alerts after a positive economic verdict. Terms of Use reviewed before any commercial use.

### 9.2 Deferred decisions and the measurement that settles each

| Deferred | Settled by |
|---|---|
| L2 frame and cadence (full 6h vs top-10 1h; eligible vs universe) | one `keep_raw` sweep plus a one-day hourly series |
| VM adoption | paired laptop–VM trial; 14-day gap log |
| Trades and wallets | one bounded backfill-availability probe (likely the main session's `trade_sample.py`) |
| Supabase Pro / Render Starter / Vercel Pro | product DB larger than 400 MB sustained; cold starts harming users; any commercial use |
| Stage 2 models | an effect surviving development and validation, with at least 16 independent days |
| Archive size and costs | stream one full capture (`3a4f`, 1.5 GB) through `zstd --long | wc -c` |

### 9.3 Decisions needed from the user
1. **Backup destination(s).**
   - **Recommended:** a 4 TB external HDD (~£120–140) as the local copy, plus a free 10 GB tier on B2 or R2 (a sign-up, $0 at ≈2 GB) as the remote copy.
   - **Zero-cost interim:** any USB stick of 8 GB or more for the ≈2 GB archive.
2. **A storage session** (`AREPO_RETIREMENT_SESSION=1`) to apply exact-byte compression to ≈17.7 GB, after step 1.
3. **Later:** approve ≈€7/month for a collector VM if the trial passes.
4. **Later:** a human reading of the Polymarket Terms of Use before any commercial direction.

### 9.4 Key assumptions
- The universe stays at roughly 0.27–0.55M markets over 3 years.
- Polymarket APIs stay public and unmetered for this read pattern.
- The programme stays a single researcher.
- Prices hold to ±20%.

---

## 10. Staged roadmap for the main AREPO team

**Useful now.** None of these touches running experiments.
1. User decisions 9.3-1 and 9.3-2, then a low-priority backup of static directories, then a verified restore test.
2. Push the 3 unpushed commits; code must not exist only locally.
3. Stage 0 research-lab provenance items (§6): code and environment hashes, `trials.jsonl`, minimum detectable effect fields, per-day tests, deduplicating e003/e004.
4. Add `collector_host`, NTP offset and clamp count to manifests for *future* series. This is metadata only, with no change to values.

**Prepare next.** After E004/E005 are scored:
1. Parquet writer with an exact-decimal ID map, behind an equivalence test. Add pyarrow and duckdb as pinned extras.
2. Change-only raw Gamma receipts plus a weekly anchor.
3. Paired laptop–VM trial.
4. One `keep_raw` L2 sweep plus a hourly shape-autocorrelation day. Then register a bounded L2 development collection or decline it.
5. Bounded trade backfill probe.
6. Product copy fixes and a public ledger page (needs user sign-off for production).
7. Fold this package into Phase 09 as its "measured inputs" section.

**Defer.**
- AWS, managed databases beyond Supabase Free, orchestrators, MLflow, Feast and GPUs.
- 1-minute panels, event-triggered capture and alerts.
- Hive partitioning and automatic object pushes until Parquet exists and a VM is adopted.
- Any destructive retention.

**Migration without breaking evidence:**
- New formats apply only to new collections, starting between registered series.
- Old files are never rewritten; compression is byte-exact and hash-verified.
- Every new writer must reproduce existing values on the same pages before use.
- Experiments never pool across a format or host change unless registered.
- Every step is reversible: Parquet → CSV export exists, object storage is portable, and a VM can be switched back to the laptop.

---

*Supporting files (same folder):*
- `specialist_data_storage.md`
- `specialist_ml_systems.md`
- `specialist_economics.md` (full price table and sources)
- `specialist_product.md`
- `lead_proposal.md`

The challenger critique is reproduced in summary in §8.
