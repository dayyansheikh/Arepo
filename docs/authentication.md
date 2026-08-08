# Authentication and accounts

Arepo has a free account system that unlocks personalised features (email alerts, saved markets,
preferences, alert history). The public site works fully without an account; accounts are
required only for those personalised features.

## Architecture: native fastapi-users (not Supabase)

Authentication is built into the existing FastAPI + SQLAlchemy-async backend using
[`fastapi-users`](https://fastapi-users.github.io/). See `DECISIONS.md` P3 for the full
rationale. In short: this keeps **one datastore** (the same database the alert engine
foreign-keys into), runs **fully offline** with no external project to create, and still
delegates all password hashing (argon2 via `pwdlib`) and token signing (JWT via `PyJWT`) to
vetted libraries. Supabase was rejected because it would split user data into a second datastore
and could not run before an external project or local Docker was provisioned.

- **Passwords**: hashed with argon2. Plaintext is never stored.
- **Sessions**: a JWT carried in a secure, httpOnly, SameSite=lax cookie.
- **Email verification**: required before login. Verification and password-reset tokens remain
  generated and validated by `fastapi-users`; branded messages are sent through the same
  provider-neutral transport as alerts using stable Resend template aliases.
- **Rate limiting**: a per-IP sliding-window limiter guards the auth endpoints.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/auth/register` | Create an account (JSON `{email, password}`) |
| POST | `/api/auth/verify` | Confirm email (JSON `{token}`) |
| POST | `/api/auth/request-verify-token` | Resend verification (JSON `{email}`) |
| POST | `/api/auth/login` | Sign in (form `username`, `password`); verified only |
| POST | `/api/auth/logout` | Sign out (clears the cookie) |
| POST | `/api/auth/forgot-password` | Request a reset link (JSON `{email}`) |
| POST | `/api/auth/reset-password` | Set a new password (JSON `{token, password}`) |
| GET/PATCH | `/api/users/me` | Read/update the current user |
| GET/PATCH | `/api/account/preferences` | Read/update alert preferences |
| GET/POST | `/api/account/saved` | List / add saved markets |
| DELETE | `/api/account/saved/{market_id}` | Remove a saved market |
| GET | `/api/account/alerts` | The current user's alert delivery history |
| DELETE | `/api/account` | Delete the account and all its data |

## Local development (no external services)

Everything runs offline. With the default console email sink, the verification and reset
**links are printed to the backend server log**, so you can complete sign-up locally without a
mail server. Look for a line like:

```
account email (local console sink, not sent externally) to=you@example.com subject='Confirm your Arepo email' link=https://www.arepolabs.com/verify?token=...
```

Open that link (or call `POST /api/auth/verify` with the token) to verify, then sign in.

## Configuration (environment variables)

Copy `backend/.env.example` to `backend/.env`. Relevant variables:

| Variable | Default | Notes |
| --- | --- | --- |
| `AUTH_SECRET` | dev placeholder | **Set a strong random value in production.** `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `AUTH_COOKIE_NAME` | `arepo_auth` | |
| `AUTH_COOKIE_SECURE` | `false` | Set `true` when served over HTTPS |
| `AUTH_TOKEN_LIFETIME_SECONDS` | `604800` | 7 days |
| `REQUIRE_EMAIL_VERIFICATION` | `true` | Block login until verified |
| `ACCOUNT_RATE_LIMIT_PER_MINUTE` | `10` | Per-IP limit on auth endpoints |
| `AUTH_EMAIL_SENDER` | `Arepo <no-reply@arepolabs.com>` | Verified transactional sender; server-side only |
| `RESEND_TEMPLATE_VERIFY` | `arepo-verify-email` | Published Resend alias or opaque ID; server-side only |
| `RESEND_TEMPLATE_RESET` | `arepo-reset-password` | Published Resend alias or opaque ID; server-side only |
| `RESEND_TEMPLATE_SIGNALS` | `arepo-signals-digest` | Reserved integration point for the future digest |
| `CORS_ORIGINS` | `http://localhost:3000` | Must be an explicit allow-list (credentials are enabled) |

The frontend calls the API with `credentials: "include"`; `CORS_ORIGINS` must therefore list the
exact frontend origin (never `*`).

## Production checklist

1. Set a strong `AUTH_SECRET` (>= 32 bytes). The app logs a warning if the default is used in
   production.
2. Set `AUTH_COOKIE_SECURE=true` and serve over HTTPS.
3. Point `DATABASE_URL` at Postgres (the schema is Postgres-compatible).
4. Configure Resend and publish the verify/reset templates under the expected aliases (see
   `docs/alert-configuration.md`). Until then the console sink logs local-development links but
   sends nothing. Production never logs verification or reset tokens on console fallback.
5. If running multiple processes/instances, front the per-IP rate limiter with a shared limiter
   (Redis or the reverse proxy); the built-in limiter is process-local.

## What still needs the user

Nothing is required to run and test accounts locally. External email delivery (so verification
and alert emails actually reach an inbox) needs the user's own SMTP/provider credentials, which
are never committed. See `docs/alert-configuration.md`.
