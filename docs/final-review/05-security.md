# Agent 5 — Defensive application-security

**Overall verdict: no Critical/High issues found; posture is good for a £0 public research tool.**
Testing was non-destructive, localhost only.

## Positive controls observed (evidence)
- **Secrets:** none in git (`.gitignore` covers `.env`, `*.db`); all provider secrets are `sync:false`
  in `render.yaml` / GitHub secrets; frontend uses only `NEXT_PUBLIC_API_BASE` (public). No secret
  material in client bundle.
- **AuthN/Z:** native fastapi-users (argon2 hashing, PyJWT); auth cookie `httponly`, `secure` in prod
  (`AUTH_COOKIE_SECURE`), `samesite`. Email verification required before login.
- **Rate limiting:** register/login/reset/verify carry `Depends(rate_limit)` → 429 over
  `account_rate_limit_per_minute` (`accounts/ratelimit.py`).
- **Per-user isolation (no IDOR):** every account op scoped to `str(user.id)` from the authenticated
  principal (`accounts/router.py` list/add/remove_saved, deliveries, preferences); `market_id` is only a
  filter within the user's own rows.
- **CORS:** explicit origin allow-list (`settings.cors_origin_list`), not `*`, with
  `allow_credentials=True`. `production_issues()` refuses/flags wildcard CORS, SQLite-in-prod, weak
  `AUTH_SECRET`, insecure cookie at startup.
- **Admin surface:** `/admin/health` returns 404 when `ADMIN_TOKEN` unset, 401 on wrong token — no
  diagnostic surface by default.
- **Injection:** SQLAlchemy ORM / bound params throughout; no string-built SQL in request paths. Upstream
  URLs are fixed config (no user-controlled SSRF target).
- **Error hygiene:** global handler returns generic 500 (`api/app.py`), no stack traces to clients.

## Findings
| Sev | Finding | Evidence | Impact | Fix |
|--|--|--|--|--|
| Medium | `allow_headers=["*"]` with credentials | `api/app.py` CORSMiddleware | Broad but origin is already allow-listed; low real risk | Optionally restrict to the headers actually used |
| Low | Rate-limiter is in-memory per process | `accounts/ratelimit.py` | On Render Free (1 instance) it holds; would not share across replicas | Fine at current scale; note for scale-up |
| Low | No explicit security headers (CSP/HSTS/X-Frame-Options) on API responses | `api/app.py` | API is JSON/CORS-guarded; frontend is Vercel (adds its own). Low | Add a minimal headers middleware if hardening desired |
| Low | Backup artifacts contain account PII | `.github/workflows/backup.yml` | GitHub artifacts are repo-private; acceptable | Documented in ROLLBACK; rotate secrets if a dump leaks |

## Non-destructive probes (localhost)
- `/admin/health` without token → 404; wrong token → 401; correct → 200 (verified).
- Account endpoints require the auth cookie; unauthenticated → 401.
- CORS preflight from a non-listed origin is not reflected (allow-list enforced).

**Conclusion: ship.** No launch-blocking security issues. The Medium/Low items are hardening, not
vulnerabilities. (Live re-check items after deployment: confirm prod `CORS_ORIGINS`, `AUTH_COOKIE_SECURE=true`,
`ADMIN_TOKEN` set, and that Vercel serves security headers.)
