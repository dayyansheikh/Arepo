# AGENTS.md

## Product

Arepo is a read-only prediction-market research and screening tool built over public Polymarket data. It identifies and explains unusual market behaviour and prospectively evaluates directional signals.

Arepo is not a trading system, betting site, wallet, calibrated forecasting product, proof of insider activity, or evidence of validated predictive alpha. It never places trades or holds exchange credentials.

## Architecture

- Frontend: Next.js 14, React, TypeScript, Tailwind, Recharts and KaTeX in `frontend/`.
- Backend: Python 3.11, FastAPI, async SQLAlchemy, Pydantic and public Polymarket Gamma/CLOB/Data APIs in `backend/`.
- Local storage defaults to SQLite; production uses Supabase Postgres.
- Public pages call the FastAPI API through `NEXT_PUBLIC_API_BASE`.
- Full scans and research collection run outside browser requests.

## Sources of truth

When sources disagree, use this order:

1. Current implementation and tests.
2. `backend/astrolabe/config.py`.
3. `.github/workflows/`, `render.yaml` and `vercel.json`.
4. Recent git history.
5. Current documentation, including `DECISIONS.md` only where consistent with the above.

Stale status, deployment and handoff documents never override current code or configuration. Inspect the relevant implementation, tests, configuration, git history and working-tree state before modifying anything.

## Production

- Production branch: `arepo-free-production-v1`.
- Frontend: Vercel.
- API: Render Free web service.
- Database: Supabase Postgres.
- Scheduled compute: GitHub Actions.
- Email provider: Resend; actual sending behaviour remains controlled by production configuration and user preferences.
- Render hosts the API only; paid Render cron jobs are not part of the current architecture.

Do not work directly on `arepo-free-production-v1` for feature/refactor work unless explicitly instructed. Prefer a dedicated task branch/worktree based on the current production branch, validate there, then review before merge.

Never deploy, trigger jobs, migrate production data, alter infrastructure, change environment variables, or modify external services unless the task explicitly requires it.

## Validation

Backend:

```bash
cd backend
source .venv/bin/activate
pytest
ruff check astrolabe tests scripts
python -m astrolabe.storage.migrate_cli check
```

Frontend:

```bash
cd frontend
npm test
npx tsc --noEmit
npm run lint
npm run build
npm run e2e
```

Run validation proportionate to the change. Do not weaken tests or research safeguards to obtain a pass.

## Research integrity

- Preserve point-in-time causality and provenance.
- Never fabricate or reconstruct prospective observations.
- Never use future information in selection, freezing or evaluation.
- Never tune formulas, thresholds or cohorts to improve reported historical results.
- Keep pending, unavailable, unchanged, closed and evaluated outcomes distinct.
- Do not claim predictive edge without the predeclared prospective evidence.
- Never reduce market-universe completeness merely to improve performance or storage.
- Public display limits must remain separate from the universe actually discovered and analysed.

## Immutable cohorts

- The prospective cohort cadence is 00:00, 06:00, 12:00 and 18:00 UTC.
- Daily and weekly research are derived summaries, not separately frozen cohorts.
- Freeze only from a valid complete scan at or after the causal boundary.
- Preserve scheduled boundary time separately from actual freeze time.
- Freezing must remain idempotent for its cadence and cutoff.
- Never rewrite or delete frozen cohorts, frozen entries or permanent forward/pre-close/resolution observations.
- Repeated markets must be handled with dependence-aware, market-deduplicated analysis rather than inflated sample counts.

## Scheduler

Keep heavy and light work separate:

- Scan workflow: complete-universe refresh followed by causally due cohort freezing.
- Collect workflow: forward observations, pre-close quotes, resolutions and retention.

Maintain separate leases, deadlines, due gates and idempotency. Browser/API requests must not trigger complete-universe scans.

## Database and storage

- Preserve existing values exactly; migrations must not recompute or “repair” historical evidence.
- Schema changes are additive unless an explicitly reviewed migration says otherwise.
- SQLite-to-Postgres imports must remain read-only on the source, idempotent and value-reconciled.
- High-frequency scan and microstructure history may follow bounded retention.
- Frozen research data and permanent observations must never be pruned.
- Supabase Free has a 500 MB database constraint. Monitor warning thresholds and plan archival or tier changes before capacity is exhausted.
- Never trade research integrity or universe completeness for free-tier capacity.
- Archive-before-delete is mandatory whenever cold archival is enabled.

## Authentication and secrets

- Authentication uses `fastapi-users`, Argon2 password hashes and JWTs in HTTP-only cookies.
- Production requires a strong `AUTH_SECRET`, secure cookies and explicit HTTPS CORS origins.
- Enforce verified-email and per-user data isolation rules.
- Never expose database credentials, auth secrets, admin tokens or Resend keys client-side.
- Never commit secrets. Only `NEXT_PUBLIC_*` values intended for browsers may enter frontend bundles.
- Do not print or copy production secrets into logs, documentation, tests or chat.

## UI and brand

- Product name is Arepo; internal Python/database names may remain `astrolabe`.
- Preserve the warm-neutral visual system, restrained red accent, Jost display headings and Geist interface/data typography.
- Keep the interface accessible, responsive and free of horizontal overflow.
- Use one consistent directional-call vocabulary across all surfaces.
- Clearly distinguish signal strength from probability, research priority from expected profit, and live/cached data from replay fixtures.
- Production must never silently serve demo/replay fixtures as live or cached data.

## Repository hygiene

Inspect before editing and preserve unrelated user changes. Do not commit untracked agent prompts, logs, PID files, launcher scripts, overnight-run artifacts or similar orchestration residue unless the task explicitly calls for them.
