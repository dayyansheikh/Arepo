# Final environment variables

Set on the Render web service AND shared with the cron jobs (use a Render Environment Group so all
share the same values). Never commit secret values; enter them in the dashboard.

| Variable | Secret? | Where to get it | Example / value | Used by |
| --- | --- | --- | --- | --- |
| `DATABASE_URL` | **Yes** | Supabase → Project → Database → Connection string → **Transaction pooler (port 6543)**, converted to the async form | `postgresql+asyncpg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres` | API + all crons |
| `AUTH_SECRET` | **Yes** | Generate: `python -c "import secrets;print(secrets.token_urlsafe(48))"` | a 48-char random string | API (auth) |
| `AUTO_MIGRATE` | No | — | `true` (jobs self-migrate; set `false` to rely only on the release command) | API + crons |
| `ENVIRONMENT` | No | — | `production` | API |
| `LOG_JSON` | No | — | `true` (structured logs) | API + crons |
| `DEFAULT_MODE` | No | — | `live` | API |
| `AUTH_COOKIE_SECURE` | No | — | `true` (HTTPS) | API |
| `CORS_ORIGINS` | No | Your Vercel URL(s) | `https://arepo.dsheikh.cc,https://arepo.vercel.app` | API |
| `APP_BASE_URL` | No | Your frontend URL | `https://arepo.dsheikh.cc` | API (email links) |
| `ALERT_EMAIL_ENABLED` | No | — | `false` (unless email alerts are wanted) | alerts cron |
| `ALERT_PROVIDER` | No | — | `resend` | alerts |
| `ALERT_SENDER` | No | A verified Resend sender | `alerts@dsheikh.cc` | alerts |
| `RESEND_API_KEY` | **Yes** | Resend dashboard → API Keys | (secret) | alerts |

Frontend (Vercel) variable:

| Variable | Secret? | Value | Used by |
| --- | --- | --- | --- |
| `NEXT_PUBLIC_API_BASE` | No | `https://arepo-api.onrender.com` (your Render API URL) | frontend build |

Notes:
- Use the **transaction pooler** (6543), not the direct connection (5432): it suits many short-lived
  cron connections and is the mode the asyncpg driver is configured for.
- The migrator and collectors connect to `DATABASE_URL` directly and do not depend on the web
  service being awake.
- No secret is ever exposed to the frontend; the frontend calls only public read routes.
