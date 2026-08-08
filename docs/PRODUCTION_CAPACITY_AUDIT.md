# Production Capacity Audit

_Phase 1 of the free-production deployment pass (AREPO_FREE_PRODUCTION_DEPLOYMENT_MASTER_PROMPT §7)._
_All numbers are **measured** against the genuine local database `backend/astrolabe.db`
(read-only) and the running process on this machine, on 2026-08-08, unless marked "estimate"._

The purpose of this document is to **quantify** production capacity rather than assert a free tier
"should be enough". The headline conclusion is that indefinite lossless storage on a single 500 MB
free Postgres is **not** guaranteed; the binding driver is permanent research data, not the
high-frequency scan history. Exact numbers and the safe lifetime are below.

---

## 1. Current database

Source file: `backend/astrolabe.db`, **9.77 MB** on disk (SQLite page file incl. indexes/overhead).
Summed textual payload across all tables ≈ **6.76 MB** (the rest is B-tree/index/page overhead).

Row counts and measured payload (bytes = Σ length of each column cast to text; a good proxy for the
per-row cost that carries to Postgres):

| Table | Rows | Payload | Avg bytes/row | Class |
|---|---:|---:|---:|:--:|
| `discovery_signal_snapshots` | 3,200 | 3.98 MB | 1,243 | **C** |
| `research_entries` | 1,442 | 1.71 MB | 1,187 | **A** |
| `microstructure_snapshots` | 2,790 | 0.65 MB | 233 | **C** |
| `research_forward_observations` | 2,884 | 0.39 MB | 134 | **A** |
| `research_preclose_observations` | 60 | 0.008 MB | 130 | **A** |
| `discovery_scan_runs` | 4 | 0.007 MB | 1,653 | A/C* |
| `signal_snapshots` | 3 | — | 823 | B |
| `cohort_entries` | 3 | — | 751 | A |
| `research_cohorts` | 2 | — | 200 | A |
| `weekly_cohorts` | 1 | — | 427 | A |
| `market_resolutions` | 2 | — | 108 | A |
| `evaluation_results` | 3 | — | 60 | A |
| `ranking_audit` | 3 | — | 69 | A |
| `users` | 1 | — | 220 | D |
| `calculation_versions` | 1 | — | 64 | A |
| everything else (alerts, saved_markets, source_health, …) | 0 | — | — | B/D |

\* `discovery_scan_runs` is **C** (operational) for scans that no cohort references, but a scan row
referenced by a frozen cohort (`research_entries.scan_id`) is **A** (frozen provenance) and is never
pruned. See §5.

### Class legend (master prompt §7/§8)
- **A — permanent prospective/research data.** Immutable cohorts, cohort entries, frozen signal
  values/ranks, forward + freeze-to-close + resolution observations, evaluation results, ranking
  audit, calculation versions, cohort-referenced scan provenance. **Never deleted by retention.**
- **B — operational/latest-state data.** Cache/latest snapshots, source health. Overwritten in place.
- **C — high-frequency historical scan/signal data.** `discovery_signal_snapshots`,
  `microstructure_snapshots`. Prunable under the §8 archive-before-delete invariants.
- **D — user/account/alert data.** Users, saved markets, alert prefs/history. Permanent, tiny.

---

## 2. What one complete scan generates (measured)

Two genuine **complete** scans are in the DB (`discovery_scan_runs` id 3 & 4, both
`complete: true`, `union_unique` ≈ 113–114k discovered markets):

| Metric | Scan 3 | Scan 4 |
|---|---:|---:|
| Discovered universe (union unique) | 113,006 | 114,104 |
| **Eligible markets analysed & snapshotted** | **1,456** | 1,382 |
| Directional signals (up/down) | 1,079 (74.1%) | — |
| Wall-clock runtime | **269 s** | **302 s** |
| Snapshot rows written | 1,456 | 1,382 |
| Snapshot payload written | ~1.81 MB | ~1.72 MB |

So **one complete scan ≈ 1,456 rows ≈ 1.81 MB payload** of category-C `discovery_signal_snapshots`
(≈ **2.5–3 MB** in Postgres once row + index overhead is added).

`microstructure_snapshots` are written by a separate lighter job (233 bytes/row); at its `*/5`
cadence and a handful of tracked tokens it is a second-order contributor (< 1 MB/day) and is pruned
on the same retention path as the signal snapshots.

---

## 3. Storage growth projections

Two independent drivers. **Both** are quantified because they have very different behaviour: C is
bounded by retention (a rolling window, not cumulative); A is genuinely cumulative and is the real
long-term constraint.

### 3A. Category C — high-frequency scan history (bounded by retention)

Per-scan cost ≈ 1.81 MB payload (~2.7 MB with Postgres overhead). Cadence choices:

| Complete-scan cadence | Scans/day | C written/day (payload) | 2-day window | 4-day window |
|---|---:|---:|---:|---:|
| every 5 min (aspirational) | 288 | ~521 MB | ~1.0 GB | ~2.1 GB |
| **every 10 min** (current `render.yaml`) | 144 | ~260 MB | ~521 MB | ~1.0 GB |
| every 15 min (recommended prod) | 96 | ~174 MB | ~347 MB | ~695 MB |
| every 30 min | 48 | ~87 MB | ~174 MB | ~347 MB |

**Because C is a rolling window, it does not grow without bound** — retention (Phase 2) caps it.
The functional retention requirement is small: `snapshots_for_market` reads at most **200 rows/market**
and the deepest trajectory lookback is **6 hours** (`change_6h`; stale after 20 min). A **2-day hot
window fully satisfies every live product surface** (Signal Lab reads only the latest scan;
trajectories need ≤ 6 h; market-detail needs ≤ 200 snapshots/market).

At full row width the C window is heavy: a 2-day window at 10-min cadence (~521 MB) alone exceeds the
500 MB Supabase cap. This is why the recommended production cadence for the **complete** scan is
**≈ 15 min** (still frequent; also realistic given GitHub Actions' 5–30 min scheduling jitter), which
keeps a comfortable 2-day C window at ~347 MB — and why retention maintenance is mandatory, not
optional.

### 3B. Category A — permanent research data (cumulative; the real constraint)

Each **cohort freeze copies the complete eligible universe** into `research_entries` (measured:
cohort 2 = 1,382 entries × 1,187 bytes ≈ 1.64 MB) plus forward/preclose observations accumulated over
its life (up to 4 forward horizons × entries + freeze-to-close quotes).

The current schedule freezes cohorts at **6h (×4/day) + daily (×1) + weekly**, i.e. **~5 full-universe
cohorts/day**. Measured/estimated permanent growth:

| Component | Per day (est.) |
|---|---:|
| Cohort entries: 5 × 1,400 × 1,187 B | ~8.3 MB |
| Forward observations: 5 × 1,400 × 4 horizons × 134 B (accruing) | ~3.7 MB |
| Preclose + resolutions + audit | ~0.5 MB |
| **Permanent total** | **~12 MB/day** |

| Horizon | Permanent A (≈12 MB/day) | Cumulative incl. ~350 MB C window |
|---|---:|---:|
| 1 day | 12 MB | ~360 MB |
| 1 week | 84 MB | ~430 MB |
| 1 month | ~360 MB | **~700 MB → over 500 MB cap** |
| 3 months | ~1.1 GB | ~1.4 GB |
| 6 months | ~2.2 GB | ~2.5 GB |
| 1 year | ~4.3 GB | ~4.7 GB |

**Binding conclusion:** on a single 500 MB free Postgres, with the current ~5 full-universe
cohorts/day, the **safe lossless lifetime is ≈ 3–5 weeks** before the permanent research data alone
approaches the cap. The dominant driver is **full-universe cohort freezes**, not the scan history.

### Levers to extend the free lifetime (see Phase 2 decision)
1. **Reduce cohort-freeze cadence** to daily + weekly (~2/day) → permanent ~5 MB/day → **~3 months**.
2. **Cold-archive** old cohorts to compressed JSONL/Parquet (gzip on frozen research is ~5–8×) in a
   free object store (Cloudflare R2 free = 10 GB) with archive-before-delete + checksums → effectively
   **indefinite** at £0 for years.
3. **Upgrade Postgres**: Supabase Pro = 8 GB for $25/mo → ~18 months before the next tier.

None of these deletes or alters frozen research; option 1 changes only how *often* new cohorts are
created (a research-cadence decision), and option 2 is lossless (recoverable, checksummed).

---

## 4. Memory / runtime (measured)

| Operation | Runtime | Peak RSS |
|---|---|---|
| Idle FastAPI app import | ~1.0 s | **87 MB** |
| + numpy/pandas signal stack loaded | — | **122 MB** |
| Representative API request (serve persisted scan) | single-digit ms (cached read) | ~120–150 MB (est.) |
| **Complete discovery scan** (≈113k discovered → 1,456 enriched) | **269–302 s** measured | **~250–400 MB (est.)** — holds the discovered-universe index in memory + enrich buffer |
| Cohort freeze from a complete scan | seconds (reads one scan's rows) | ~130–160 MB (est.) |
| Due-forward collection | seconds–minutes (bounded by due entries × upstream calls) | ~130–160 MB (est.) |

### Implication for compute placement (Phase 6)
- **Render Free web service = 512 MB RAM.** The idle/serving API (87–150 MB) fits comfortably.
- The **complete scan's estimated 250–400 MB peak approaches Render's 512 MB ceiling** and its 269–302 s
  runtime exceeds a comfortable request budget. Running heavy scans **inside Render is risky**
  (OOM/timeout). This is independent evidence for the intended topology: **heavy scheduled scans run on
  GitHub Actions runners (7 GB RAM, no request timeout); Render only serves persisted complete
  results**; both share the same Postgres. A normal user request never triggers a universe rebuild.

---

## 5. Free-tier facts that constrain the design (verified 2026-08-08)

- **Supabase Free:** 500 MB database, 1 GB file storage, 5 GB egress/mo, 50k MAU, unlimited API
  requests. **Projects pause after 7 days with no API requests** (data retained; manual resume). The
  scheduled tick and the Render API both hit Postgres regularly, so the project will not pause in
  normal operation — but a genuinely idle week would pause it, which the health check must surface.
- **GitHub Actions:** standard runners are **free and unlimited for _public_ repositories**; private
  repos on the Free plan get 2,000 min/month. At ~6 min/complete-scan, a 15-min cadence uses
  ~576 min/day ≈ 17k min/month — **far over the 2,000-min private budget**. → The £0 scheduled-compute
  path **requires the repository to be public** (or a paid Actions plan). Cron has a 5-min minimum and
  **5–30 min jitter**, so the scheduler must be delay-tolerant and idempotent, never assume exact-second
  execution.
- **Cloudflare R2 (candidate cold archive):** 10 GB storage + 1M Class-A + 10M Class-B ops/month free,
  **no egress fees**. Enough to hold years of compressed frozen research.

---

## 6. Indexes

Schema is created from ORM metadata via `create_all` + the additive migrator; indexes are declared on
the ORM models (PK indexes plus scan_id / market_id / entry_id lookups the read paths use). No
SQLite-only column types are used, so the same DDL compiles for Postgres (verified by the
`ddl_preview` portability path in `storage/migrate.py`). Postgres will additionally benefit from
composite indexes on the hot read predicates — see Phase 3 notes.

---

## 7. Summary of measured inputs (for the storage decision)

- Complete scan: **1,456 eligible / ~113k discovered, 269–302 s, ~1.81 MB category-C payload**.
- Category-C growth is **bounded by retention** (2-day hot window fully preserves functionality).
- Category-A (permanent research) grows **~12 MB/day** at the current ~5 full-universe cohorts/day —
  the **real** long-term driver.
- Single 500 MB free Postgres safe lossless lifetime ≈ **3–5 weeks** as-is; **~3 months** at 2
  cohorts/day; **indefinite** with a compressed R2 cold archive (archive-before-delete).
- Idle/serving API fits Render Free (512 MB); the **complete scan does not comfortably** → run it on
  GitHub Actions, not inside Render.
