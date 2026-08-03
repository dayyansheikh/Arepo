# Accounts, data and privacy

This document describes what account data Arepo stores, how it is isolated, and how it is
deleted. It complements `docs/authentication.md` (how sign-in works) and
`docs/alert-configuration.md` (how alerts are sent).

## What is stored

| Table | Data | Why |
| --- | --- | --- |
| `users` | email, argon2 password hash, verification/active flags, `consent_at`, `auth_provider`, `created_at` | Identity and sign-in. Passwords are never stored in plaintext. |
| `alert_preferences` | one row per user: thresholds, categories, short-term/pause/unsubscribe flags | Personalised alert delivery |
| `saved_markets` | markets the user follows (id + question) | The "saved markets" feature |
| `alert_deliveries` | per-user record of alerts (market, subject, status, time) | The user's alert history and per-user dedup/cooldown |
| `account_deletions` | a **non-reversible SHA-256 of the email** + timestamp + reason | Audit that a deletion happened, without keeping the deleted person's data |

No payment data is collected. Accounts are free. Arepo stores only what the personalised
features need.

## Isolation

Every personalised endpoint requires an authenticated session and is scoped to that user's id in
the data-access layer (`accounts/service.py`): a user can only ever read or modify their own
preferences, saved markets and alert history. There is no service-role key exposed to the
browser. The isolation is covered by an explicit cross-user test
(`test_user_data_is_isolated_between_accounts`).

## Consent

Registration records a `consent_at` timestamp. The sign-up form requires the user to confirm
they understand Arepo provides statistical research signals, not financial advice, before an
account is created.

## Alerts and opt-in

Alerts are opt-in and only ever sent to a **verified** email whose preferences have
`email_enabled` on and are not paused or unsubscribed. Users can pause all alerts, unsubscribe
entirely, or set a hard maximum on how often and about what they hear. Alert copy is identical
for every recipient and never personalised financial advice: it never says buy, sell or how much
to stake, and always carries the research disclaimer.

## Deletion

`DELETE /api/account` permanently removes the user and all of their preferences, saved markets
and alert deliveries. Only the non-reversible audit row (hashed email + timestamp) remains, so
the deletion can be evidenced without retaining personal data. Deletion is immediate and covered
by `test_account_deletion_removes_access`.

## Data provenance separation (unchanged by accounts)

Accounts do not touch the strict separation of **prospective**, **reconstructed** and
**synthetic** result sets in Replay/evaluation (see `docs/methodology.md` and
`docs/limitations.md`). User data and market-analysis data are different concerns; the account
tables never feed the signal or evaluation pipelines.
