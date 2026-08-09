# Account digests

Arepo sends personalised digests from the latest **fresh, complete, stored** Opportunity scan. The
delivery selector uses the same overall ordering and public limit as `/api/scan/opportunities`: it
takes at most the current public top 20, applies the user's delivery-category filter, and stops at
Top 5, 10 or 20. It never lowers a signal threshold or searches beyond that shortlist to fill space.
User-facing category groups are a delivery-only view over the existing normalized category and real
upstream tags; they do not change Arepo's category derivation or research methodology.

## Delivery

`python -m astrolabe.digest.cli run` is one bounded, lease-protected runner. Due boundaries are
fixed UTC windows: every six hours at 00/06/12/18, twice daily at 00/12, daily at 06, and weekly on
Monday at 06. A frequency-independent user/window unique key and a deterministic Resend
idempotency key prevent duplicate history and duplicate external sends. A failed request retries the
same immutable snapshot; an uncertain send is not retried after Resend's 24-hour idempotency window.

The published `arepo-signals-digest` template remains the visual source. Because Resend limits each
string template variable to 2,000 characters, the provider fetches the published shell and expands
the trusted repeated-card markup server-side. Market text is escaped before insertion. All other
variables are escaped by the provider.

External delivery requires both `DIGEST_EMAIL_ENABLED=true` and a configured Resend provider/key.
The GitHub Actions workflow is separate from scan and collection work. The digest renderer must
read the published shell: use a separate full-access `RESEND_TEMPLATE_API_KEY` where possible, while
keeping `RESEND_API_KEY` sending-only. If the send key already has full access, it remains the
fallback; both credentials stay server-side.

## History and evaluation

`digest_deliveries` stores one small header and preference snapshot. `digest_entries` stores only the
signal identity, title/outcome, delivery category, original direction, strength, priority, entry
midpoint, timestamp, and an optional exact `research_entries` reference. Canonical URLs are derived
from the stored market ID rather than duplicated. Sent content is never recalculated from a later
scan.

Evaluation reads only exact prospective research rows and existing forward/resolution observations.
It reports pending, moved as signalled, moved against, unchanged, unavailable, closed before the
horizon, and final resolution separately. It never reconstructs a missing observation.

## Supabase Free estimate

These are conservative PostgreSQL estimates including ordinary row/index overhead, not the much
larger existing research tables:

- preference additions: under 0.5 KB per user;
- digest header: about 0.8–1.2 KB;
- digest entry: about 0.35–0.6 KB, depending mainly on question/identifier length;
- Top 5 / 10 / 20 digest: roughly 3–4 KB / 5–7 KB / 9–13 KB.

At the upper end, one user receiving Top 20 every six hours is roughly 19 MB/year; twice daily is
about 9.5 MB/year, daily 4.7 MB/year, and weekly 0.7 MB/year. Real use is lower when fewer signals
qualify. Existing database-size health warnings remain the capacity guard for the 500 MB Free-plan
cap. Capacity must be managed through user/delivery policy or a database-plan change—never by
deleting frozen research evidence, weakening scan completeness, or rewriting digest history.

Unsubscribe tokens contain no email or user ID and turn off only digest delivery. Verification and
password-reset email remain available.
