# Arepo deployment and activation checklist

Follow in order. Each step: **where**, **what to click/run**, **value** (and whether it is a
**secret**), **expected result**, **common failure**, **fix**. Never paste secrets into any chat;
enter them only in the provider dashboards. Primary architecture: Render (API + cron) + Supabase
(Postgres) + Vercel (frontend). See `docs/final-hosting-decision.md`.

Legend: 🔒 = secret value.

> **Build from a clean environment (final runtime acceptance §6).** The `Cannot find module
> './vendor-chunks/geist.js'` error seen in local dev was stale/corrupt `.next` output, not a code
> fault. Vercel/Render already build fresh, so this cannot occur in deployment. Locally, if a market
> route ever throws a missing-vendor-chunk error, run `npm run dev:clean` (or `rm -rf .next && npm ci
> && npm run build`) — never ship a pre-existing `.next`. `.next/` is gitignored, so it is never
> committed.

## A. Repository

1. **Confirm branch + commit.** Local terminal: `git -C /path/to/astrolabe log -1 --oneline` and
   `git status`. Expected: latest `arepo-final-predeployment-launch-readiness` commit, clean tree.
   Failure: dirty tree → commit/stash. Then run `bash scripts/preflight_deployment.sh` → `PREFLIGHT OK`.
2. **Create a pull request.** GitHub → the repo → "Compare & pull request" for
   `arepo-final-predeployment-launch-readiness` → base `main`. Expected: PR opens, diff is additive.
3. **Merge into `main`.** GitHub → the PR → "Merge pull request" → "Confirm merge". Expected: `main`
   updated. Failure: conflicts → rebase locally, push, retry.
4. **Create a production safety tag.** Terminal: `git checkout main && git pull && git tag
   arepo-edge-research-live && git push --tags`. Expected: tag pushed. (Rollback anchor.)

## B. Database (Supabase)

5. **Create / confirm the Supabase project.** supabase.com → "New project" → name `arepo`, choose a
   region near you, set a strong database password 🔒 (store it in your password manager). Expected:
   project provisions in ~2 min. Failure: org limit → use an existing project.
6. **Get the PostgreSQL URL.** Supabase → Project → **Connect** (or Settings → Database) → **Connection
   string** → **Transaction pooler** (port **6543**). Copy it. Convert to async form:
   `postgresql+asyncpg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres`.
   This whole string is 🔒 `DATABASE_URL`. Common failure: using the direct 5432 URL (fine for
   `pg_dump`, but use the **6543 pooler** for the app).
7. **Configure the database password securely.** Put the password into the URL from step 6 in your
   password manager only. Do not commit it. Expected: you hold `DATABASE_URL` 🔒 ready to paste.
8. **Run the migration (or configure the release command).** Two options: (a) let Render's
   **preDeployCommand** run it automatically (already in `render.yaml`); or (b) run once now from a
   machine with the URL: `DATABASE_URL='<the async url>' python -m astrolabe.storage.migrate_cli
   upgrade`. Expected: `{"from_version":0,"to_version":3,"columns_added":[...]}` then
   `migrate_cli check` → `"current": true`. Failure: connection refused → check the URL/region/password.

## C. Backend (Render)

9. **Create the backend service.** render.com → "New +" → **Blueprint** → connect the GitHub repo →
   Render reads `render.yaml` and proposes the `arepo-api` web service + cron jobs → "Apply".
   Expected: services created. Failure: blueprint not detected → ensure `render.yaml` is on `main`.
10. **Enter backend environment variables.** Render → create an **Environment Group** `arepo-env` and
    attach it to the web service AND every cron. Add (from `docs/FINAL_ENVIRONMENT_VARIABLES.md`):
    `DATABASE_URL` 🔒, `AUTH_SECRET` 🔒 (generate: `python -c "import secrets;print(secrets.token_urlsafe(48))"`),
    `AUTO_MIGRATE=true`, `ENVIRONMENT=production`, `LOG_JSON=true`, `DEFAULT_MODE=live`,
    `AUTH_COOKIE_SECURE=true`, `CORS_ORIGINS=https://arepo.dsheikh.cc`, `APP_BASE_URL=https://arepo.dsheikh.cc`.
    Expected: web service deploys; the **release command migrates the schema** first. Failure: build
    fails → read the log; deploy fails on migration → fix `DATABASE_URL`.
11. **Configure health and readiness checks.** Render → the web service → Settings → Health Check Path
    = `/health` (already in `render.yaml`). Expected: service goes "Live" once `/health` returns 200.
12. **Create every scheduled job.** The Blueprint already created 11 cron jobs
    (`docs/FINAL_SCHEDULED_JOBS.md`). Confirm each exists in Render → your services. Failure: a cron
    missing → re-apply the blueprint.
13. **Enter every exact UTC schedule.** These come from `render.yaml`; verify in each cron's Settings:
    microstructure `*/5 * * * *`; research-freeze-6h `5 0,6,12,18 * * *`; research-freeze-daily
    `10 0 * * *`; research-freeze-weekly `15 0 * * 1`; research-forward `*/20 * * * *`; resolve
    `15 */6 * * *`. Expected: schedules shown in UTC. Failure: shown in local time → Render uses UTC;
    the expressions are already UTC.
14. **Configure job secrets.** Attach the `arepo-env` group to every cron so they share `DATABASE_URL`
    🔒 etc. Expected: crons can reach the database. Failure: a cron errors "DATABASE_URL not set" →
    attach the env group.
15. **Run the first manual collector sequence.** Do this just after a 6-hour boundary (e.g. 12:05 UTC).
    In each cron → "Run now", in this order: research-freeze-6h → research-freeze-daily →
    research-freeze-weekly → (wait ≥1 hour) → research-forward. Or use the Render shell:
    `python -m astrolabe.evaluation.research_cli research-freeze --cadence 6h`. Expected JSON:
    `frozen:true`, `universe_size` 40–80, `rejected` absent. Failure: `rejected:true` → upstream
    degraded, retry later; missing-column error → run `migrate_cli upgrade`.
16. **Verify the first real six-hour cohort.** `curl https://<api>/api/research/status` → 
    `cohort_counts_by_cadence.6h >= 1`, `total_frozen_markets > 0`. Failure: 0 → the freeze did not run;
    re-run step 15.
17. **Verify the first real daily cohort.** Same status → `cohort_counts_by_cadence.daily >= 1`.
18. **Verify the first real weekly cohort.** After the Monday 00:15 UTC run (or a manual run) →
    `cohort_counts_by_cadence.weekly >= 1`.
19. **Verify forward observation.** After ≥1 hour, run research-forward → `written > 0`,
    `invalid_predates_freeze:0`. Failure: all invalid → the freeze cut-off was in the past; ensure the
    freeze ran at the boundary (step 15 timing).
20. **Verify synthetic exclusion.** `curl -o /dev/null -w '%{http_code}' https://<api>/api/cohorts/latest`
    → `404` (no real weekly cohort yet) or a real (non-synthetic) cohort later. It must never return the
    synthetic demo. Failure: returns synthetic → open an issue (should be impossible).

## D. Frontend (Vercel)

21. **Create the Vercel project.** vercel.com → "Add New" → "Project" → import the GitHub repo.
22. **Set the frontend root directory.** Vercel → project → Settings → General → Root Directory =
    `frontend`. Expected: Vercel detects Next.js. Failure: build can't find package.json → root dir wrong.
23. **Set the production API variable.** Vercel → Settings → Environment Variables → `NEXT_PUBLIC_API_BASE`
    = `https://<your-render-api>.onrender.com` (not secret). Expected: frontend calls the live API.
24. **Deploy the frontend.** Vercel → "Deploy". Expected: build succeeds (16 routes), site live at the
    Vercel URL. Failure: build error → check the deploy log; type errors were green locally.
25. **Connect the custom domain `arepo.dsheikh.cc`.** Vercel → Settings → Domains → add
    `arepo.dsheikh.cc` → follow the DNS record it shows (CNAME to Vercel) at your DNS provider.
    Expected: domain verifies + HTTPS issued. Failure: DNS not propagated → wait, re-check.
26. **Update backend CORS and base URL.** Render → `arepo-env` → set `CORS_ORIGINS` and `APP_BASE_URL`
    to `https://arepo.dsheikh.cc` (comma-add the Vercel URL if you use both) → redeploy the API.
    Expected: the site can call the API without CORS errors. Failure: CORS error in the browser
    console → the origin is not in `CORS_ORIGINS`.

## E. Optional email (only if auth emails / alerts are wanted)

27. **Configure Resend.** resend.com → verify a sending domain → create an API key 🔒. In `arepo-env`
    set `RESEND_API_KEY` 🔒, `ALERT_SENDER=alerts@dsheikh.cc`, `ALERT_EMAIL_ENABLED=true`. Expected:
    verification/reset emails send. Failure: unverified sender → complete domain verification. (Skip
    this whole section to launch without email; the public product works without accounts.)

## F. Product verification

28. **Test sign-up, verification, reset** (only if email is configured). Visit the site → Sign up →
    check the email link → verify → sign in → reset. Expected: full lifecycle works. Failure: no email
    → check Resend + `ALERT_EMAIL_ENABLED`.
29. **Test Signal Lab.** Open `/signals`. Expected: ranked signals; info popovers stay on-screen; no
    horizontal scrollbar; badge and "Why this fired" clearly separated.
30. **Test Replay research status.** Open `/replay` → "Edge-research status". Expected: the amber "not
    enough evidence yet" banner + real cohort counts by cadence.
31. **Test market routing.** Open `/markets/2694364` and `/markets/2822017`. Expected: both open.
    Failure: 404 on a valid id → check the API base + backend logs.
32. **Test scheduler failure and recovery.** Render → pause the `research-forward` cron for one cycle,
    then resume. Expected: the next run catches up the due observations; no duplicates
    (`invalid_predates_freeze` may appear only for horizons genuinely predating a freeze). Failure:
    backlog never clears → check the cron is enabled and the env group attached.
33. **Confirm operation with the browser closed.** Close all browsers. Wait for the next 6-hour
    boundary (or "Run now"). Then re-open and check `/api/research/status`: a new 6h cohort appeared.
    Expected: evidence grows with no browser open. This is the whole point.

## G. Operations

34. **Set a monitoring routine.** Daily (or via a uptime monitor hitting `/health`): run
    `API_BASE=https://<api> bash scripts/check_research_health.sh` → `HEALTH OK`. Watch
    `collector_recent`, `last_successful_freeze`, `incomplete_cohorts` (must be 0), `degraded_cohorts`.
35. **Configure the backup routine.** Per `docs/FINAL_BACKUP_AND_RETENTION.md`: rely on Supabase daily
    backups; add a weekly `pg_dump` (direct 5432 URL) to off-site storage once on Pro; verify a restore
    quarterly. Never delete frozen cohorts/entries/outcomes/revisions.
36. **Define the rollback procedure.** Per `docs/FINAL_ROLLBACK_PLAN.md`: to stop collection, pause the
    four `arepo-research-*` crons; to roll back code, redeploy the previous Render/Vercel build; never
    drop research tables/columns (the schema is additive and forward-compatible).
37. **Set the first 24-hour review.** Expect: 4 six-hour + 1 daily cohort; 1h/6h/24h observations
    beginning; still `edge_supported:false`. Check `/api/research/status`.
38. **Set the seven-day review.** Expect: ~28 six-hour + 7 daily + 1 weekly cohorts; 24h outcomes for
    day-1 cohorts complete; 7d outcomes beginning; baselines/ablation populate but stay inconclusive.
39. **Set the 30-day research review.** Expect: the 24h evaluable sample likely crosses the predeclared
    minimum (100), enabling the FIRST meaningful ablation/selection read. Note: because Arepo's
    direction equals momentum by construction, a directional edge over momentum cannot appear; the
    decision then is whether the microstructure families or the selection add value, or whether a new
    direction model is warranted (see the final report's "next research decision").

Done. Once A–D are complete and the crons are enabled, Arepo collects real prospective evidence
automatically, with no browser open.
