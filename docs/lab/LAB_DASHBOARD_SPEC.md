# Arepo Lab dashboard (private, owner-only) — spec v1 (2026-10-18)

User request (2026-10-18): a live, password-protected page on arepolabs.com where only the owner can explore every
experiment, see how close the programme is to an edge, how the machine learning is going and what it has learnt
(feature weights), and pause/resume the research queue and the Claude autopilot. Design: live charts, diagrams,
intuitive, visual, not overwhelming, in the existing site style. User approved (2026-10-18): production deploy of this
feature, an additive DB migration, marking the owner's account `is_superuser`, and view + pause/resume controls.

## Architecture
```
Oracle host (research) --signed push every 10 min--> Render API  <--cookie (superuser)-- Vercel /lab page
Mac (autopilot)        --signed push every 30 min--> (lab_snapshots, lab_commands in Supabase)
host/Mac poll signed GET /api/lab/agent/commands, execute whitelisted pause/resume, POST result
```
- No new secrets anywhere. Machines sign requests with Ed25519 private keys that never leave them
  (`~/.arepo/lab/lab_ed25519.pem`). The API holds only the public keys, committed in code (not secret):
  - `host`: `ft3ahXh+cf8gqGCnTFUVpBb8ABGa3SSInrDWIYEqtLg=`
  - `mac`:  `/2RTwa1W3d/5vI8GYrCkUu2eTEE/ZEh+hxufFLnfliA=`
- The browser never talks to the machines. The machines only make outbound HTTPS requests (no inbound port).

## Request signing (machine endpoints)
Headers: `X-Lab-Source: host|mac`, `X-Lab-Timestamp: <unix seconds>`, `X-Lab-Signature: <base64 Ed25519 sig>` over
the UTF-8 string `"{METHOD}\n{PATH}\n{TIMESTAMP}\n{sha256_hex(body_bytes)}"` (PATH without query string; body empty
for GET → sha256 of b""). Reject (401) if: unknown source, |now − ts| > 300 s, bad signature. Body limit 2 MB (413).

## API (FastAPI, prefix `/api/lab`, new router module, `cryptography` for Ed25519)
Machine (signed):
- `POST /api/lab/agent/snapshot` — body is the source's snapshot JSON (`schema` must be `arepo-lab-v1`,
  `source` must equal the header). Upsert into `lab_snapshots` (one row per source). 204.
- `GET /api/lab/agent/commands` — pending commands for that source's targets (host → `queue`, mac → `autopilot`),
  marks them `delivered`. Commands older than 2 h still pending become `expired` and are not returned.
- `POST /api/lab/agent/commands/{id}/result` — `{ok: bool, message: str ≤ 500}` → status `done` / `failed`.
Owner (cookie session, `is_superuser` AND `is_active` AND `is_verified`):
- `GET /api/lab/dashboard` → `{host: {received_at, payload}|null, mac: {received_at, payload}|null,
  commands: [last 20, newest first], server_time}`.
- `POST /api/lab/commands` `{target: "queue"|"autopilot", action: "pause"|"resume"}` → 201 with the command. A newer
  command for a target expires any still-pending one for that target. Max 30 commands/hour (429).
- Unauthenticated → 401; authenticated non-superuser → 404 (do not reveal the page exists).
- Follow the existing cookie-auth/CSRF/CORS conventions of `/api/account`.

## Tables (additive; register in `storage/migrate.py` `_load_all_models`, bump SCHEMA_VERSION with a note)
- `lab_snapshots(source TEXT PK, received_at TIMESTAMPTZ, payload TEXT (JSON), payload_sha256 TEXT, size_bytes INT)`
- `lab_commands(id INT PK autoincrement, target TEXT, action TEXT, status TEXT, created_at, created_by UUID/TEXT,
  delivered_at NULL, finished_at NULL, result TEXT NULL)`. Keep at most the latest 500 rows (prune older on insert).
Supabase Free is 500 MB: snapshots are ≤ 2 MB each, two rows.

## Snapshot schema `arepo-lab-v1` (all fields optional except schema/source/generated_at; UI must tolerate absence)
Host:
```jsonc
{ "schema": "arepo-lab-v1", "source": "host", "generated_at": "ISO",
  "headline": {"confirmed_edges": 0, "tests_run": 1106, "hypotheses": 117, "batches": 12, "live_tests": 3,
               "jobs_done": 73},
  "funnel": [{"stage": "idea|designed|screened|replicated|live_test|cost_check|confirmed", "label": "Ideas",
              "count": 117, "help": "plain sentence"}],
  "experiments": [{"id": "E009", "title": "Kalshi lead", "plain": "1-2 plain sentences", "batch": "CB4|SB2|E|…",
      "family": "cross_venue", "stage": "<funnel stage>", "status": "collecting|queued|running|analysed|closed|waiting",
      "verdict": "not_detected|not_testable|replicated|advanced|failed_costs|pending|null",
      "effect": {"label": "+0.36c", "note": "before costs"} | null, "next": "Analysis after 3 Nov",
      "next_date": "2026-11-03" | null, "candidate": true|false}],
  "live_tests": [{"id": "E009", "title": "…", "collected": 1234, "target": 2000 | null, "unit": "predictions",
                  "analysis_after": "2026-11-03"}],
  "ml": {"status": "parked|running|done|waiting", "status_note": "plain", "learned": ["plain sentence", …],
         "feature_weights": [{"feature": "Order flow × volatility", "family": "flow", "weight": 0.12}],
         "contrasts": [{"label": "Last 24h vs >30 days before close", "value": 0.0188, "lo": 0.0094, "hi": 0.0292,
                        "unit": "nats", "replicated": true}]},
  "tests_over_time": [{"date": "2026-10-12", "cumulative": 906}],
  "queue": {"updated_at": "ISO", "paused": false, "counts": {"done": 73, "queued": 5, …},
            "running": [{"id": "…", "title": "…", "started_at": "ISO", "lane": "cpu"}],
            "recent": [{"at": "ISO", "id": "…", "title": "…", "outcome": "done|error|tempfail|…", "runtime_s": 600}],
            "upcoming": [{"id": "…", "title": "…", "status": "queued|retry_wait|parked", "not_before": "ISO"|null}]},
  "infra": {"disk_free_gb": 59, "disk_total_gb": 89, "mem_available_mb": 4345, "mem_total_mb": 5648,
            "collector_last_ok": "ISO", "collector_ok": true, "data_gb": 15.1, "data_cap_gb": 45,
            "second_server": {"status": "retrying|created", "attempts": 275, "last_try": "ISO"},
            "history": [{"t": "ISO", "disk_free_gb": 59, "mem_available_mb": 4300}]} }
```
Mac: `{ "schema": "arepo-lab-v1", "source": "mac", "generated_at": "ISO", "autopilot": {"paused": false,
"pause_reason": null, "session_alive": true, "started_at": "ISO", "last_outcome": "timeout|usage_limit|…",
"next_allowed": "ISO"|null, "recent": [{"at": "ISO", "outcome": "…", "runtime_s": 18000}]}}`

## Research-integrity rules for the dashboard (non-negotiable)
- Live prospective tests (E009/E010/E011 and any SEALED-P): show collection counts and dates only. Never compute or
  display interim outcome statistics before the registered analysis.
- "How close to an edge" is the funnel stage reached, never a probability or an expected profit.
- Keep `not_detected` (screened, below MDE), `not_testable` (data/rarity) and `failed_costs` visibly distinct.
- Confirmed edges show the true count (0). No profitability, calibration or trading claims. Development results are
  labelled "development (historical)".
- Production never serves fixtures: the page shows an honest empty/stale state when there is no snapshot.

## Frontend (`/lab`, Next.js 14 app router, Tailwind, Recharts, existing design tokens and components)
Calm, visual, not overwhelming; progressive disclosure (details on click/expand). Sections, top to bottom:
1. Header: "Lab" + freshness ("updated 3 min ago", stale warning > 30 min) + compact machine status dots.
2. **Edge pipeline diagram (hero):** the 7 funnel stages left→right (stacked vertically on mobile) with counts; the
   leading candidates drawn as labelled markers in the stage they have reached; "Confirmed edges: 0" honest.
3. **Leading candidates:** 3-5 cards, each with stage progress and countdown to the next milestone.
4. **Experiment explorer:** filter chips (stage, verdict, batch) + search; compact rows; click to expand plain text.
5. **Machine learning:** status pill; "what it has learnt" sentences; horizontal bar chart of feature weights
   (by family colour); contrast chart (point + CI); note "development, historical".
6. **Activity:** tests-over-time area chart; recent job timeline strip (coloured by outcome); live-test collection
   progress bars (counts only).
7. **Machines & controls:** disk/memory gauges + small history sparkline, second-server status, autopilot status;
   Pause/Resume buttons for Queue and Autopilot with confirm step, pending → delivered → done state from `commands`.
Polls `/api/lab/dashboard` every 60 s (pause polling when tab hidden). 401 → redirect to `/signin?next=/lab`;
404 → standard not-found. Not linked from public navigation; `robots` noindex. Accessible, responsive, no horizontal
overflow, respects reduced motion, light/dark as the site does.

## Members (owner-only admin, `/lab/members`, added 2026-10-19)
User request: in the Lab, see all members, control password resets, delete accounts, make them admin if needed.
API `/api/lab/admin` (every endpoint uses the same `owner()` dependency: 401 signed out, 404 non-owner, Origin check):
- `GET /users` → `{users: [{id, email, first_name, last_name, is_active, is_verified, is_superuser, created_at,
  data: {alert_preferences, saved_markets, alert_deliveries, digest_deliveries}}], me}`. Never hashes or tokens.
- `POST /users/{id}/password-reset` (fastapi-users `forgot_password`; member gets the normal reset email; 409 if
  suspended), `POST /users/{id}/verification-email` (`request_verify`; 409 if already verified or suspended),
  `POST /users/{id}/verify`, `POST /users/{id}/suspend|restore` (no self-suspend; revoke admin before suspending an
  admin), `POST /users/{id}/admin {grant, confirm_email}` (grant only to active+verified; no self-revoke; never the
  last effective admin), `DELETE /users/{id} {confirm_email}` (not self, not an admin; removes the user plus
  alert_preferences, saved_markets, alert_deliveries, digest_deliveries, digest_entries in one transaction via the
  existing `delete_account`, with an `account_deletions` hash row, reason `owner_admin`).
- `GET /audit` → last 50 `lab_admin_audit` rows. Every successful mutation writes one row in the same transaction.
  On delete, no plain copy of the member's email survives: every audit row naming them (target or actor) is rewritten
  to a mask (`d***@gmail.com`), and the delete row stores the mask plus the same SHA-256 as `account_deletions`.
- Rate limits per owner per rolling hour, counted from the audit log: 20 email actions, 60 actions in total (429).
- Table `lab_admin_audit` (SCHEMA_VERSION 15, RLS on Postgres). `lab_commands.created_by` is left as written.

## Claude activity board (`/lab/claude`, view-only, added 2026-10-21)
User request: see what the headless Claude autopilot sessions are doing. View only (no prompts from the web). No API,
schema or table change: both additions travel inside the existing snapshots (2 MB limit unchanged).
- Mac snapshot adds `activity` (built by `scripts/lab/lab_activity.py` on the research branch, kept ≤ 300 KB):
  `{generated_at, branch, instances: [{name, home, paused, pause_reason, session_alive, started_at, last_outcome,
  last_finished_at, next_allowed, sessions_total, sessions: [{started_at, ended_at, runtime_s, outcome, test?, note?,
  cost_usd?, turns?, duration_ms?, duration_api_ms?, subtype?, terminal_reason?, stop_reason?, is_error?, done?,
  summary?, summary_truncated?, log_state}]}], commits: [{at, sha, subject}], trimmed?, error?}`. Instances are
  `~/.arepo/autopilot` (label `main`, or a one-line `label` file) plus every `~/.arepo/autopilot-<name>`; sessions are
  newest first (last 30); `done` is the closing `AUTOPILOT_DONE` line (≤ 400 chars), `summary` the rest of the result
  (≤ 1,500 chars). Every text field is sanitised on the Mac (secret shapes, credentials in URLs, `password=`-style
  values, long high-entropy strings, literal values of the owner-only files in `~/.arepo`); log paths are never sent.
  `cost_usd` is the CLI's API-equivalent figure; sessions run on the subscription.
- Host snapshot adds `activity.queue` = 48 h tally of queue attempts `{window_h, since, attempts, outcomes,
  distinct_jobs, runtime_h, first_at, last_at}`; the event feed itself reuses `queue.recent` / `queue.running`.
- Page: instance status cards (working / paused / waiting for usage reset / idle), a 48 h session timeline coloured by
  outcome, an expandable session log (markdown-lite rendered as React text, never HTML), the latest commits, and the
  research server tally. Falls back to the legacy `autopilot` block when the Mac sends no `activity`.

## Claude board v2 (`/lab/claude`, added 2026-10-21)
Owner feedback on v1: more intuitive, a plain-English summary per session, a project-wide cost total, and a place to
control and message Claude. Runs of failed sessions (no internet, API errors, usage-limit stops) must fold into one row.

Page, top to bottom: **Right now** (one sentence per autopilot instance, with the running session's latest progress
text), **Today / this week** digest (counts and one plain line per finished session; failures only counted),
**Costs**, **Send a message / Controls**, the 48 h timeline and the session log (meaningful sessions by default; a
toggle shows failed runs, each run collapsed into one expandable row such as "8 sessions failed: couldn't reach the API
(08:03–11:55)"), and a collapsed "Technical: recent commits" section.

Mac snapshot additions (`scripts/lab/lab_mac.py`, research branch; all optional, the UI tolerates absence):
- `activity.instances[]` gains `key` (command target = home directory name: `autopilot` = experiments,
  `autopilot-signal`, ...), `startable` (a launchd job exists), `current: {text ≤ 300, at}` for a running session (latest
  assistant text from its Claude Code transcript), and sessions gain `plain` (first sentences when there is no
  `AUTOPILOT_DONE` line). Instances with only a `label`/`PAUSE` file are now listed too.
- `costs` (lab_costs.py): API-equivalent cost of every Claude Code transcript in `~/.claude/projects/*astrolabe*`
  (main sessions and `<session>/subagents/*.jsonl`), messages de-duplicated by message id across files (largest value
  of each counter), priced from a table copied from https://platform.claude.com/docs/en/about-claude/pricing (fast
  mode, US-only inference 1.1x, Haiku 5.5 long prompts, web searches; unknown models listed and excluded, never
  guessed). `{total_usd, last_7d_usd, today_usd, by_day, by_model, by_source (interactive | <instance> autopilot |
  other_headless, each split main/subagent), unknown_models, prices, infra (all £0), scan}`. Incremental cache
  `~/.arepo/lab/cost_cache.json` (0600) keyed by file size/mtime with a parsed byte offset. Aggregates only.

API (additive, schema v17):
- `POST /api/lab/commands` targets `queue` or `autopilot(-<name>)` (`^autopilot(-[a-z0-9]{1,24})?$`), actions
  `pause|resume`, plus `start` for autopilot targets (422 otherwise). The mac source receives every autopilot target.
  Each command writes a `claude_command` audit row.
- `POST /api/lab/messages {target, body ≤ 4,000}` (owner + security-key step-up; 20 per rolling 24 h → 429; audit row
  `claude_message_sent`), `POST /api/lab/messages/{id}/cancel` (pending only, else 409; `claude_message_cancelled`).
  Claude-board audit rows never count against the Members action budget.
- Signed (mac): `GET /api/lab/agent/messages` → `{messages: [pending, or fetched > 30 min ago], awaiting_read:
  [delivered, last 30 days]}` (the host always gets empty lists); `POST /api/lab/agent/messages/{id}/status
  {state: delivered|read|failed, message ≤ 500}`. Repeats are harmless; moving backwards is 409.
- `GET /api/lab/dashboard` adds `messages` (last 30, newest first) and `limits`.
- Table `lab_messages(id, target, body, status pending|fetched|delivered|read|failed|cancelled, created_at,
  created_by, fetched_at, delivered_at, read_at, finished_at, result)`, latest 500 kept, RLS on Postgres.

Mac execution (`lab_mac.py`): pause/resume run `autopilot.py pause|resume` with `AREPO_AUTOPILOT_HOME` set to that
instance's home. `start` refuses when the instance is paused, a session is running or `next_allowed` is in the future,
then launches the instance's own launchd command (`autopilot.py tick` with its plist environment, API-key variables
removed) detached in a new session; `autopilot.py` itself re-checks pause, usage limit and the subscription login.
Messages are appended to `<home>/INBOX.md` under a header with the marker `<!-- lab-msg:<id> -->` (idempotent; a body
cannot forge a marker), reported `delivered`, and reported `read` once INBOX.md no longer contains the marker (the
session moves it to `INBOX.done-<time>.md`, as both autopilot prompts instruct).

### Sanitiser
Summaries, progress lines and commit subjects are cleaned on the Mac by fixed pattern rules before upload; no AI is
involved. `scripts/lab/lab_activity.py` `sanitise()` replaces with `[redacted]`: PEM private-key blocks; API-key shapes
(`sk-`/`pk-`/`rk-` incl. `sk-ant-`), GitHub tokens (`ghp_`, `github_pat_`, ...), Slack (`xox?-`), AWS (`AKIA`/`ASIA`),
Google (`AIza`), Resend (`re_`) keys; JWTs; `Bearer` tokens; credentials inside URLs (`scheme://user:pass@`);
`password=`/`secret:`/`token=`/`api_key=`-style assignments; any 32+ character mixed-case-and-digit run; and the literal
contents of the small owner-only files in `~/.arepo` plus the values of secret-named environment variables. Control
characters are stripped, and texts are truncated (session summary ≤ 1,500, DONE line ≤ 400, progress ≤ 300 chars).
Log file paths are never sent.
