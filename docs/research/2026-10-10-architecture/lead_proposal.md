# Lead proposal (draft for challenge) — AREPO future architecture

Inputs: specialist_data_storage.md, specialist_ml_systems.md, specialist_economics.md, specialist_product.md (same folder).

Verified by lead: 8 GB RAM / 8 cores laptop; disk 95-96% full, 8.6-11 GiB free (fluctuating); data-dumps 20-21 GB on disk
(~33.5 GB logical); prod scan cron commented out since 2026-08-22 (Supabase hit 935 MB / 500 MB); weekly pg_dump backup
only for prod DB; no offsite copy of research evidence; compact snapshots ~24-27 MB on disk.

## Proposed decisions
P1 Backup before anything else. Critical 0.4 GB (capsules, receipts, manifests, research_lab, EVIDENCE) offsite now;
   then streamed `tar | zstd --long` of all data-dumps (~2 GB est) with restore+hash verification at destination.
   Destination is a user decision (USB/external disk free-of-signup; or B2/R2 free tier = sign-up).
P2 Storage formats: new observation families as Parquet+zstd, one immutable file per capture + sha256 manifest, hive
   partitions family/date/capture_id; token/condition/event IDs moved to SCD dictionary tables (89% of snapshot bytes are
   IDs); prices stored as exact decimal strings/scaled ints, not floats. DuckDB as query engine. SQLite for small ledgers.
   Postgres (Supabase) for product serving only. No time-series DB. Existing csv.gz files untouched.
P3 Raw-receipt policy: keep raw Gamma market objects only when changed + one weekly full raw anchor; keep full-depth raw
   L2 books at 6h aligned to 00/06/12/18 UTC; top-of-book summaries at higher cadence only inside registered experiments.
   Budget ~12.5-18 GB/yr.
P4 Sampling: complete-universe enumeration at 6h (cohort cadence) as the sampling frame; targeted high-cadence panels
   only for a preregistered hypothesis, drawn by documented probability sampling from the frame; event-triggered capture
   deferred (selection-on-outcome risk).
P5 Always-on collector: one small VM (Hetzner CX23 class, ~EUR 6-7/mo incl VAT) becomes canonical collector BEFORE the
   next long prospective series, after a one-day non-canonical trial (rate limits, geo, runtime). Hourly batched Parquet
   push to object storage. Requires user spending approval. Until then: laptop collection with explicit gap ledger.
P6 Research governance (extend research_lab, do not rebuild): full-module code hashing + dirty flag; committed
   trials.jsonl (every run incl. post hoc); data roles assigned at collection time (dev / validation / sealed) with a
   loader guard that releases sealed data only to a REGISTERED frozen spec and logs access; time-block / two-way
   (event x day) clustered bootstrap; multiplicity budget (alpha-spending or LORD) over sealed tests.
P7 Compute: laptop sufficient through next stage with float32/streaming; 16-32 GB VM only for dense panels or GBM
   grids; no GPU; no distributed; no MLflow/Feast/Dagster/W&B before Stage 3.
P8 Product: public = verifiable forecast ledger + open lab notebook; rename "Opportunities", label momentum call as
   baseline; descriptive context pages next; forecast cards only after a prospective confirmation; alerts only after a
   positive Phase 08 economic verdict. Polymarket terms read by a human before any commercial/data-export use.
P9 Defer: AWS, managed TSDB, trades/wallet/1-min panels until a registered hypothesis needs them (one bounded backfill-
   availability probe first), GPU, orchestrators.

## Points I want challenged hardest
C1 ML proposes data roles by ISO-week mod 4. Does calendar blocking confound with regime/time trends, and is a week the
   right block given 6h cohorts and multi-day horizons (label overlap across block boundaries)?
C2 Power: event-clustered SE implies ~7k event clusters for dR2=0.037 and ~87k for 0.01. Is the programme able to
   detect anything realistic, and what does that imply for how many hypotheses should be run at all?
C3 Is 6h full-depth book retention a sufficient "option" for future book features, or does it mislead (features at 6h
   resolution may be useless for minute-scale dynamics)? Is lower-cadence full depth better than higher-cadence top-N?
C4 Does the VM-as-canonical-collector change source timing/latency in ways that break comparability with laptop-era data?
C5 Does anything here risk existing protected evidence, E002/E004/D116, or the main session's work?
C6 Is anything over-engineered for a one-person programme with no validated edge?
