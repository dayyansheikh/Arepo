# Runbook 2026-10-12: deploy, Data API lockdown, provenance archive

User approvals (2026-10-12): (1) merge + deploy `fix/infra-2026-10-11`; (2) run the lockdown SQL; (3) archive old snapshot history, keeping it restorable. Do these in order. Agents cannot do the merge, the SQL or secret creation: there are no Supabase/Render credentials here, and a repo hook blocks production-branch commands.

## A. Deploy

**How it deploys.**
- Render: `render.yaml` sets `autoDeploy: true` for `arepo-api`. The tracked branch is set in the Render dashboard, not in the yaml; all prior production deploys came from `arepo-free-production-v1`. If no deploy starts within ~2 min of the merge: Render → `arepo-api` → **Manual Deploy → Deploy latest commit**.
- On merge, Render rebuilds automatically. The build ends with `python -m astrolabe.storage.migrate_cli upgrade`, which applies schema v13. The two foreign-key indexes are built `CONCURRENTLY` on tiny tables, in seconds, without blocking writers. Render then starts the new API, about 3–6 min in total.
- GitHub Actions runs workflows from the default branch, so the new collect/backup/digest code and the archive workflow are active from the merge onwards. Vercel (frontend) has no changes.

**User steps (about 3 clicks):**
1. Open https://github.com/dayyansheikh/Arepo/compare/arepo-free-production-v1...fix/infra-2026-10-11
2. Click **Create pull request**, then **Create pull request** again.
3. Click **Merge pull request**, then **Confirm merge**. Note the time.

**Verify (agent):** `scripts/infra/postdeploy_verify.sh <merge time, e.g. 2026-10-12T08:00:00Z>` (on the fix branch). Expected:
- `/health` 200; research status 200 (first call ≤45 s, cached ≤3 s; before the fix it returned 502 at ~21 s);
- replay cohorts 200; markets 200 (cached ≤5 s); `www` 200 and `www/api/status` 200; apex 308;
- after merge, Actions runs succeed, and the next `arepo-collect` takes ~1–2 min instead of ~8 min with `already_present` ≈ 440836;
- storage still "critical" until step C is complete.

**Rollback:**
- Fastest: Render dashboard → `arepo-api` → **Events/Deploys** → the previous deploy → **Rollback**.
- Durable: on GitHub, open the merged PR and click **Revert**, then merge the revert PR.
- Schema v13 is additive: the old code accepts it, and the indexes can stay.

## B. Supabase Data API lockdown

File: `docs/infra/supabase_data_api_lockdown.sql` (on the fix branch, and on the production branch after A).

Steps: Supabase dashboard → project **Arepo_model_1** → **SQL Editor** → **New query** → paste the whole file → **Run**. Expect "Success. No rows returned".

Paste this back for verification (expect `0 | 0 | 0`):

```sql
SELECT
 (SELECT count(*) FROM information_schema.role_table_grants
   WHERE table_schema='public' AND grantee IN ('anon','authenticated')) AS data_api_grants,
 (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE n.nspname='public' AND c.relkind='r' AND NOT c.relrowsecurity) AS tables_without_rls,
 (SELECT count(*) FROM pg_default_acl d JOIN pg_roles r ON r.oid=d.defaclrole
   WHERE r.rolname='postgres' AND d.defaclnamespace='public'::regnamespace
     AND (d.defaclacl::text LIKE '%anon=%' OR d.defaclacl::text LIKE '%authenticated=%')) AS default_grants;
```

Rollback: the commented ROLLBACK block at the end of the same file.

## C. Provenance archive (restorable)

What and why: `docs/infra/PROVENANCE_ARCHIVE.md` explains what moves and how to get it back with one command. Science review: SAFE_WITH_CONDITIONS; the code conditions are implemented.

**C1. One-time secret (user).**
1. GitHub → avatar → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**.
2. Name `arepo-archive`, expiry 7 days.
3. Repository access: **Only select repositories → `dayyansheikh/arepo-data`**.
4. Permissions: **Repository permissions → Contents: Read and write**. Metadata becomes read-only automatically; nothing else.
5. Generate, then copy the token.
6. In the `dayyansheikh/Arepo` repo: **Settings → Secrets and variables → Actions → New repository secret**, name `ARCHIVE_REPO_TOKEN`, paste the token, then **Add secret**.

**C2. Run 1: export + verify, no deletion.**
- Actions → **arepo-provenance-archive** → **Run workflow**, `confirm_prune = no`.
- An agent may also run `gh workflow run arepo-provenance-archive -f confirm_prune=no`.
- Expected log: N scans exported (≈ 60+); release `provenance-archive-2026-10-12` created in `arepo-data`; `sha256sum -c` all OK; `all N archives verified`; `restored … (verified)` for every scan; scratch row total equals the manifest total.
- Then an agent keeps a **second independent copy**: `gh release download provenance-archive-2026-10-12 -R dayyansheikh/arepo-data -D <local backup dir> && (cd <dir> && sha256sum -c SHA256SUMS)`.

**C3. Run 2: prune (user click; after reviewing run 1 and the second copy).**
- Same workflow, `confirm_prune = yes`, same tag.
- It re-downloads, re-verifies and re-restores into scratch, then deletes. Each scan is re-fingerprinted under a lock; the latest scan and the latest complete scan are refused. It then runs `VACUUM FULL` and prints `db_size_mb_after`. Expected: roughly 951 → ~350–400 MB.
- `PRUNE_LOG-<run>.tsv` is attached to the release.

**Rollback / re-access:** `docs/infra/PROVENANCE_ARCHIVE.md` → "Re-access" (B = back into production). This is also `README.md` inside the release.

After C, the agent updates the checkpoint and `PHASE_03_BOUNDED_RETENTION.md` (on the main branch) to record that cohort-referenced snapshot provenance now lives in the verified archive.
