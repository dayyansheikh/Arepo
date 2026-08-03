# Alert configuration

Arepo can send opt-in research email alerts about high-priority Opportunity Board markets.
Sending is **off by default** and provider-neutral: a console sink logs alerts locally and
nothing is sent externally until you explicitly enable and configure a provider. Credentials
are read from environment variables and never hardcoded.

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `ALERT_EMAIL_ENABLED` | `false` | Master switch. External sending only happens when true. |
| `ALERT_PROVIDER` | `console` | `console` (local sink, never sends) or `smtp`. |
| `ALERT_TEST_MODE` | `false` | Build and record alerts but never send externally. |
| `ALERT_RECIPIENT` | *(empty)* | Where alerts go, e.g. `dayyansheikh.work@gmail.com`. |
| `ALERT_SENDER` | `arepo-alerts@localhost` | From address. |
| `ALERT_MIN_STRENGTH` | `0.40` | Minimum signal strength to alert. |
| `ALERT_MIN_CONFIDENCE` | `0.40` | Minimum confidence. |
| `ALERT_MIN_FAMILIES` | `2` | Minimum independent evidence families. |
| `ALERT_MIN_PRIORITY` | `50` | Minimum Research Priority (0-100). |
| `ALERT_COOLDOWN_HOURS` | `12` | Per-market cooldown (deduplication). |
| `ALERT_MAX_RETRIES` | `2` | Send retries on provider failure. |
| `ALERT_SMTP_HOST` / `_PORT` / `_USER` / `_PASSWORD` | *(empty)* / `587` | SMTP details (only when `ALERT_PROVIDER=smtp`). |

External sending requires `ALERT_EMAIL_ENABLED=true`, `ALERT_PROVIDER=smtp`, and a configured
`ALERT_SMTP_HOST` + `ALERT_RECIPIENT`. Without all of these, alerts stay in the console sink.

## Running

- Dry run (test mode, never sends): `python -m astrolabe.alerts.cli dry-run`
- Alert history: `python -m astrolabe.alerts.cli history`

## Eligibility and content

An immediate alert normally requires a minimum strength and confidence, at least two
independent evidence families, adequate liquidity, an acceptable spread, fresh data, a valid
market status and no data-quality failure (all configurable). A per-market cooldown
deduplicates repeats. Each alert gives an honest directional interpretation, states what
caused it, what could invalidate it, what to inspect, and a link to the Arepo analysis, and
ends with a research disclaimer. Alerts never say buy, sell or stake a specific amount, never
promise profit and never give personalised advice.
