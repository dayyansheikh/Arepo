# AREPO provenance archive: what it is and how to get it back

**What was moved.** Rows of `discovery_signal_snapshots` for every complete scan that a frozen research cohort references (`research_cohorts.scan_id`), except the latest scan and the latest complete scan. Those two stay in the database because they are live product state.

**What was NOT touched:**
- `discovery_scan_runs` (the scan headers);
- research cohorts, entries, and forward / pre-close / resolution observations;
- users and all other tables.

**Where it is.** A release in the private repo `dayyansheikh/arepo-data` (tag e.g. `provenance-archive-2026-10-12`). It contains:

| File | Contents |
|---|---|
| `<scan_id>.csv.gz` | Every column of every row of that scan, in `id` order (CSV with header) |
| `MANIFEST.tsv` | `scan_id`, row count, `md5(string_agg(row::text, '\n' ORDER BY id))` computed by production Postgres, file sha256 |
| `schema.sql` | Exact production table definitions (`discovery_signal_snapshots`, `discovery_scan_runs`) |
| `discovery_scan_runs.data.sql.gz` | The scan headers at export time |
| `SHA256SUMS` | Checksums of every file. `PRUNE_LOG-*.tsv` is added if and when production was pruned |

**Proof it is lossless.** The workflow downloads the release back, checks every sha256, and restores everything into an empty Postgres. It then recomputes count + md5 per scan and requires equality with the production-computed manifest; identical row text means identical rows. Pruning deletes a scan only if its live rows still match the manifest, checked under a table lock.

## Re-access (one command)

Requirements: `gh` (logged in with read access to `arepo-data`), `psql`/`pg_dump` 17, and a target Postgres.

```bash
TAG=provenance-archive-2026-10-12
gh release download "$TAG" -R dayyansheikh/arepo-data -D arepo-archive && cd arepo-archive && sha256sum -c SHA256SUMS
```

**A. Into a fresh local or scratch database** (analysis without touching production):

```bash
createdb arepo_archive
psql arepo_archive -c "CREATE ROLE anon NOLOGIN" -c "CREATE ROLE authenticated NOLOGIN" 2>/dev/null
psql arepo_archive -v ON_ERROR_STOP=1 -f schema.sql
gunzip -c discovery_scan_runs.data.sql.gz | psql arepo_archive -v ON_ERROR_STOP=1
DATABASE_URL=postgresql:///arepo_archive bash <repo>/backend/scripts/provenance_archive.sh restore .
```

`restore` re-verifies count + md5 per scan and stops on any mismatch.

**B. Back into production** (e.g. if a feature needs the history hot again). This is idempotent: rows are inserted `ON CONFLICT DO NOTHING` and every scan is re-verified. It needs ~600 MB of free quota.

```bash
DATABASE_URL=<session-pooler postgresql:// URL> bash backend/scripts/provenance_archive.sh restore .
DATABASE_URL=... bash backend/scripts/provenance_archive.sh restore . scan-2026...   # one scan only
```

## What changes while archived

- **Research evaluation is unaffected.** Frozen entries carry copied values: forward, pre-close and resolution observations, research status, edge verdict, Replay results and the headline never read these rows.
- **Diagnostic and display surfaces show less:**
  - Replay's "later evolution" panel reports "no later scan stored (older scan history may be archived)" for markets outside the kept scans.
  - Market-detail signal history only covers the kept scans.

  Restoring brings both back exactly.
- **Capability lost while archived** (science review): the database alone cannot rebuild a frozen universe's per-snapshot fields that entries do not copy: `captured_at`, `active`/`eligible`/`exclusion_reason`, `rank_in_bucket`, `shadow_directional`, per-row versions and provenance. `META.tsv` and `COHORT_SCAN_MAP.tsv` record the schema version, column list, kept live scans and cohort→scan mapping. Restore (A or B) brings everything back.
- **Retention invariant 1** (cohort-referenced scans are permanent) now means "permanent: in the database **or** in this verified archive". The scan headers keep the linkage.
