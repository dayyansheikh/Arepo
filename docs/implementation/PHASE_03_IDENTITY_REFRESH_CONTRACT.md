# Phase 3 selected-market identity refresh

Status: D046 implemented and self-reviewed; 986 full backend tests passed. A two-request live development measurement and independent replay passed; no panel
or origin admission. Exact clocks/hashes/results are in PHASE_03_TARGETED_QUOTE_EVIDENCE.json. The fixed two-request runtime plan is
PHASE_03_IDENTITY_REFRESH_MEASUREMENT.json; execute only after commit/PR update.

## Basis and scope

Official [Get market by id](https://docs.polymarket.com/api-reference/markets/get-market-by-id)
documentation inspected 2026-09-22 specifies GET `/markets/{id}`, an integer path parameter
and a single Market response with string `id`. Lifecycle flags are nullable. This provides
a targeted identity lookup; it does not prove an active order book or independent event.

Implement a distinct `gamma.market` source with a fixed HTTPS host/path template, no query,
authentication, redirects or arbitrary URL. Support canonical nonnegative ASCII decimal
market ID strings of at most 78 digits as an explicit bounded transport subset. Unsupported
IDs remain unresolved; do not alter broad-frame inclusion or silently coerce IDs. Freeze
the exact path parameter in the receipt and validate it again during replay. Response ID
must exactly equal the requested ID before its mapping can be used.

Keep default SourceRun v1 policy unchanged. Add an explicit named policy version for
`gamma.market`, books and trades; freeze it before requests. Verify only one of the exact
known policy documents and its source contracts. No caller-defined source lists or policies.
Existing original-build history remains unchanged; do not weaken build checks to reuse it.

## Ordered work and acceptance

1. Add strict request construction and replay validation for the new path source. Preserve
   legacy request shape and source contract hashes for existing sources.
2. Parse the single-market response with strict target matching and existing exact ordered
   condition/token/outcome mapping. Preserve active/closed/archived/acceptingOrders flags
   explicitly as nullable booleans in a separate lifecycle object; reject malformed values.
   Unknown flags stay unknown. Failed HTTP or malformed responses retain raw evidence.
3. Add explicit SourceRun policy selection and freeze/replay verification. Do not extend
   diagnostic SQL identity import or loosen registry rights/native-clock restrictions.
4. Integrate this source into the quote projector. Reuse strict target parsing, retain
   lifecycle alongside the mapping only for this source, and abstain for closed/inactive/
   archived/not-accepting/unknown lifecycle instead of treating a parseable book as eligibility.
   Preserve old list-source projection semantics and version by build; later origins still
   need their own full eligibility contract. Unknown category is not fabricated.
5. Tests: path/query injection, noncanonical IDs, wrong response identity, malformed or
   nullable lifecycle, retained 404/429/closed responses, default-policy refusal, exact policy
   replay, synthetic receipt/read/computation chain, late identity and immutable evidence.
6. Self-review, focused and full isolated tests, docs, coherent commit and draft PR before
   any actual public read. A later finite measurement must freeze a target and budgets
   before requests and report failures honestly. No production scans or migrations.

## Protected boundaries and next handoff

No SQL admission, origin, trigger/control result or validated edge. Same existing finite
SourceRun and D043/D045 resource caps. No automatic full-universe refresh or selection
redraw; historical assignments remain historical. Next handoff: a tested request-to-quote
path suitable for separately predeclared bounded runtime verification and panel integration.
