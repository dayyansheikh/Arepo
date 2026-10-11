# Challenger review of the architecture lead proposal (science-reviewer, 2026-10-10 ~22:38 UTC+1)

Recovered verbatim from the subagent transcript after the 2026-10-10 crash; previously only summarised in AREPO_FUTURE_ARCHITECTURE_2026-10-10.md section 8.

**Challenger review of the AREPO architecture proposal (read-only; nothing was run beyond greps, `df` and `ls`)**

**Overall verdict: REVISE.** The direction is sound: back up first, extend `research_lab` rather than rebuild it, defer heavy tooling, and treat the public product as a ledger. But three proposal items don't hold up as written:
- The P6 data-role scheme (C1).
- The P3 storage budget and its "option value" rationale.
- The ordering of collector and format changes against E004/E005, which have no qualifying snapshot yet. `data-dumps/research_lab/snapshots/` holds only the 3 pre-E004 captures.

## C1: ISO-week mod 4 data roles. REJECT as the primary mechanism.

Three reasons:
- **It leaks across block boundaries.** Roles are assigned by calendar week, but labels are pair-defined. A DEV origin late in week 1 has its label window inside SEALED week 3 only after a gap, yet a week-2 VALIDATION origin can have its label in week 3. E001 horizons ran up to 70h (`EXPERIMENT_LEDGER.md:84`). Nothing in the proposal embargoes origins whose label window crosses into another role.
- **It wastes power.** Only 1 week in 4 is SEALED. ML's own estimate of about 16 independent periods for ΔR2=0.01 would then take more than 15 months of calendar time.
- **It duplicates a better rule the programme already uses.** E002, E004 and E005 confirm only on data collected after the freeze commit (`EXPERIMENT_LEDGER.md:124,261,324`). That rule is causal by construction and never "uses up" a vault.

**Change:**
- Confirmation data = origins strictly after the registration commit, inside a window declared at registration, dropping origins whose label crosses the window edge.
- Keep the salted event-holdout hash only for experiments that register an unseen-event question.
- Keep the access log, but as an audit trail. It is a single-user repo with plain CSVs, so a "loader guard" is a convention, not enforcement.
- If interleaving is still wanted later, randomise days by a pre-committed seed, with an embargo of max horizon. This avoids calendar aliasing with month-end resolution clustering.
- The product spec's "interim numbers shown publicly" (specialist_product §5) is acceptable only if the registration forbids early stopping or amendment.

## C2: Power. ACCEPT WITH CHANGE.

**Arithmetic checks out.** I reproduced:
- SE = (0.069 − 0.004)/3.92 = 0.0166 (from `EXPERIMENT_LEDGER.md:220`).
- 14,879 × (0.0166·2.49/0.037)² ≈ 18.6k.
- Paired: (0.0097·2.49/0.01)² × 14,879 ≈ 87k.
- Bonferroni-60: z = 3.14 + 0.84 = 3.98.
- P(≥8 of 11) = 232/2048 = 0.113.

**But the inputs are fragile:**
- **The 0.037 effect is probably inflated by an artefact.** The ledger itself says quote noise alone predicts a negative slope (`:298`). The 1h change and the subsequent dmid share the origin mid's error, so the reversal is partly mechanical errors-in-variables. Genuine-information effects are likely much smaller.
- **The period SD (0.016) comes from n=4.** Its 95% CI spans roughly 0.57–3.7× the point value, so "16 periods" could be about 5 or more than 200.
- **E004's 11 periods are 2h apart, about one day in total** (`:261,301`). That is closer to one or two independent time blocks than 11.

**Implications:**
- Require an MDE (minimum detectable effect) statement in every registration.
- Run at most about 2–4 confirmatory tests at a time.
- Treat ΔR2 below about 0.02 as out of reach until there are months of independent days.
- Two-way event × time clustering is unreliable with under about 20 time clusters. Use period-level (per-day) tests or randomisation inference across days for the time dimension, keeping event clustering within periods.

**Measurement to resolve:** the per-day SD of R2_oos across about 10 or more distinct days, once collected. Also the share of SSE gain contributed by the top 5 events in E001/E004, since SSE-R2 is driven by heavy tails.

## C3: 6h full-depth books. ACCEPT WITH CHANGE (scope, alignment, end date).

**What 6h full depth is good for.**
- It suits cross-sectional book-shape hypotheses at 6h–multi-day horizons, which is E003's own suggested next step (`:253`).
- It is useless for queue or cancel dynamics.

**Unrecognised constraints.**
- **Banked data can never confirm anything.** Under the prospective rule, banked L2 can only ever be development data. So the "option value" is dev-only, and a few weeks of fresh post-hypothesis collection provides the same.
- **The sweep is not "all books".** `book_sweep.select_tokens` uses `panel.eligibility_mask` (`trade_sample.py` docstring, lines 3–4). That is E001 eligibility: spread ≤ 0.10, mid in [0.02, 0.98], endDate > 3h. It covers about 15.5% of the universe, outcome 0 only, and excludes exactly the wide-book and near-resolution regimes where effects may live.
- **Collecting now then deleting later is destructive retention, which needs separate approval.** So scope it up front.

**Change:**
- Make 6h L2 a registered, bounded development collection with a declared end date.
- Align each sweep to the snapshot and cohort boundary, and record skew.
- Decide explicitly whether the frame is eligible or universal.
- Prefer change-only raw Gamma metadata. Fees, rewards, tick size and category cannot be backfilled, are cheap, and E004 notes fees are absent (`:295`).

**Measurement to resolve:** one sweep with `keep_raw=True` to get the actual gz bytes (the 6 MB figure is untested) and the share of depth beyond 10 levels and beyond 5c. Plus a one-day hourly series to estimate 1h/6h autocorrelation of shape features. Top-10 at 1h may dominate full depth at 6h.

## C4: VM vs laptop comparability. DEFER-PENDING-MEASUREMENT.

Network latency (~100 ms) is negligible against 7–12 min page skew. The real risks are:
- **Different CDN or cache staleness by region or IP.** Stale quotes specifically flatter reversal (`:291`).
- **Different scan duration,** which changes the horizon distribution.
- **Geo or IP rate-limiting.**
- **An unflagged clock.** `collector.py:166-167` silently clamps a backward wall-clock receipt to the previous value. Manifests also record no host or clock source (grep found none).

**Change:**
- Add `collector_host` and an NTP-offset field to the manifest, and count clamp events.
- Never switch hosts inside a registered series. E004/E005 must finish on the loop that started them.
- Experiments may not pool laptop and VM collections unless registered.

**Measurement to resolve:** a paired parallel trial of 2–3 cycles, laptop and VM simultaneously, written outside `snapshots/`. Compare per-market quote equality, the `updated_at` age distribution, scan duration, 429s and peak RSS. The CX23 has 4 GB; measure the collector's peak with `/usr/bin/time -l` first.

## C5: Risk to protected evidence or active work. ACCEPT WITH CHANGE (explicit ordering).

These are real hazards:
1. **Format or field changes before E004 has 12 snapshots.** The P2 Parquet/decimal writer, the ID normalisation and `keep_raw` changes would breach "E001 field set and parsing" (`:127`) and the rule that "no other capture is written to `snapshots/`" (`:287,364`).
2. **A P1 `tar | zstd -19` of all of `data-dumps` during the 2-hourly loop.** CPU contention lengthens scans, which changes skew and horizons. Tarring the live `snapshots/` dir also gives an inconsistent copy.
3. **DATA_ROLES must not reassign E004/E005 confirmation snapshots,** and P6 multiplicity must not relabel E002–E005 verdicts. State that it applies prospectively from E006.
4. **APFS transparent compression of canonical dirs** (`0da4`, `e9d0`) is a protected action. It needs a user session and a before/after per-file sha256 manifest.
5. **Code-hash changes to `compare.py` collide with the main session.** That session has uncommitted, untracked `trade_sample.py`/`sample_trades.py`, a trade-sampling module that P9 ("defer trades") doesn't acknowledge. Reconcile P9 with it; it looks like the bounded probe P9 asks for.

**Change:** the ordering should be:
1. Back up only the static dirs, at `nice` priority with `zstd -9 --long`.
2. Let E004/E005 complete.
3. Then make writer and host changes, after an equivalence test showing the new writer gives the same values as the CSV writer for the same pages.

## C6: Over-engineering. ACCEPT WITH CHANGE.

These are over-engineered:
- **SCD-2 for IDs.** Market→condition/token IDs are immutable, so an append-only `ids` map with an immutability assertion per capture is enough. Reserve SCD-2 for mutable metadata.
- **Hive partitioning and hourly object-storage push** before Parquet even exists. pyarrow and duckdb are not installed.
- **LORD/alpha-investing** for a programme with about 1–5 confirmatory tests a year. A pre-declared α per registration plus Holm within a family, tracked in the ledger, is enough.
- **The loader guard,** as per C1.

Justified and cheap:
- Full-module code hash (confirmed gap: `compare.py:216-220` hashes only `compare.py` and `features.py`).
- An environment lockfile hash in results (missing from the proposal).
- An automatically appended `trials.jsonl`.

## Other material points

- **Normalised files need their dictionary to replay.** Normalised snapshots depend on the ID dictionary for replay. Each manifest must carry the dictionary version hash, and every backup or capsule must include it. Otherwise the files can no longer be read on their own.
- **Exactness.** `extract.py:56-75` converts to float with no raw kept, so page sha256s are not re-verifiable. Exact decimals for new families: ACCEPT. Existing CSVs stay as they are, labelled "lossy-parsed, raw not retained".
- **Source rights.** The GitHub repo is public (per the economics specialist; I did not re-check). Backups and object buckets must be private. Retaining raw books or trades is unverified under the ToS, so no public export.
- **Does infrastructure improve reproducibility?** The real gains are code and environment hashes, the trial log and kept raw receipts. Parquet and DuckDB give storage and speed, not reproducibility.
- **"Offsite".** A USB disk at home is not offsite. P1 needs one local external copy plus one remote copy, with restore and hash verification on both.
- **Free-disk headroom.** The proposal omits the specialist's biggest lever: about 15 GB reclaimable losslessly via APFS compression (user decision). Free space is now 11 GiB, against D116's 13.31 GB reservation.
- **Paying more is justified when:**
  - a 14-day laptop log shows more than 1% missed or late slots during a registered series, or
  - an MDE calculation needs at least N independent days that a sleeping laptop can't deliver.

  An external disk is justified now. Above about 80% use, the disk itself is the trigger.

## Arithmetic spot-checks

- **"89% IDs": true only for the columnar zstd representation** (18.3/20.51 MB). Those IDs are about 32 bytes of entropy each (272k × 32 B ≈ 8.7 MB per column), so the 10× gain comes only from cross-file normalisation, not from Parquet.
- **The P3 budget is understated.** 12.5–18 GB/yr counts parsed L2 (6 MB per sweep) but omits:
  - raw L2 gz (7–10 MB per sweep);
  - the change-only raw Gamma store (6.5 MB/day);
  - the weekly anchor (117 MB/week ≈ 16.7 MB/day).

  Corrected: about 61–73 MB/day ≈ 22–27 GB/yr flat.
- **Archive (~2 GB): plausible to ±2×.** Raw is about 42% of capture bytes. 10 GB of raw at 10–15× gives 0.7–1 GB before derivatives. But the samples were 10 contiguous pages. **Measure** by streaming one full capture (`3a4f`, 1.5 GB) to `wc -c`.
- **Cost.** €5.49 + IPv4 ≈ €6, or €7.2 with 20% VAT, a little above "6–7". The economics Base case (300 GB/yr) assumes 15-min sweeps that nobody proposes, and uses the stale 16 MB snapshot. This doesn't change the decision, because compute dominates.
- **Growth: "2×/yr" rests on one step.** The count fell 276,706 → 272,660 in 90 minutes, which is unexplained churn and worth checking for frame stability.

## Minimum defensible infrastructure (next ~3 stages)

1. **Now (E004/E005 running):**
   - No collector changes.
   - Back up static dirs plus capsules, locally and remotely, with restore and hash verification.
   - User decision on lossless APFS compression and an external disk.
   - Full-module code hash, environment lock hash and an auto `trials.jsonl`.
   - MDE (minimum detectable effect) statements in registrations.
2. **After E004/E005 are scored:**
   - Immutable ID map plus per-capture Parquet with exact decimals, behind an equivalence test.
   - Change-only raw Gamma metadata.
   - Host and clock fields in manifests.
   - The post-freeze confirmation-window rule.
   - Per-day period tests.
   - The paired VM trial; adopt the VM only if it passes, and only between series.
3. **First multi-week series:**
   - The VM as canonical collector, with a gap ledger and a dead-man alert.
   - 6h cohort-aligned snapshots.
   - L2 or trades only as bounded registered collections.
   - Laptop analysis via DuckDB.
   - No GPU, orchestrator or MLflow.

## Proposal items most likely to be wrong

1. ISO-week mod-4 roles (boundary leakage, 4× slower confirmation, redundant).
2. P3's 12.5–18 GB/yr budget (more like 22–27), and the 6 MB L2 per-sweep figure.
3. The "option value" of banked L2 (it can only ever be development data) and the "all books" framing (it is the eligible ~15.5%).
4. Power numbers built on an artefact-prone 0.037 and a 4-period SD.
5. SCD-2 for immutable IDs, and LORD.
6. USB counted as "offsite".
7. The implicit assumption that P1/P2/P5 can run alongside E004/E005.

Files cited: `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/EXPERIMENT_LEDGER.md`, `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/compare.py`, `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/collector.py`, `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/extract.py`, `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/trade_sample.py`.

**Not verified:**
- Hetzner VAT treatment for UK customers.
- Polymarket ToS.
- Whether the public repo is public (taken from the economics specialist).
- Actual raw L2 size.
- Archive compression on full captures.
