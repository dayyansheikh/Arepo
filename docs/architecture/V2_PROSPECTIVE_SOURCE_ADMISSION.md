# Prospective source admission — Phase 2 refinement

Version `fs2-source-run-v1`. This specifies a bounded local measurement interface, not a
deployed collector or a claim of predictive value. Generic caller-supplied prospective
records stay prohibited.

## Primary artefact and clocks

The primary input is the append-only local source journal. SQL is a later materialized
index. A source run durably registers its source contracts, internal measurement policy,
budget and parser build **before** any request. Only responses captured by that run may
enter its source records. Existing diagnostic directories cannot be imported as prospective.
Injected transports always produce synthetic provenance; no provenance parameter exists.

For each response, preserve original raw receipt, raw durability acknowledgement, generic
parse, source-specific parse and its acknowledgement. Then persist the complete source-record
facts (excluding writer-derived recording/availability clocks) and fsync; sample an actual
post-fsync acknowledgement. `recorded_at` and `available_to_model_at` project that acknowledgement
of the primary facts, never the later SQL transaction start. `ingested_at` remains the original
raw durability clock; `parsed_at` is actual source-specific completion. Missing or torn
acknowledgements are refused, never reconstructed with an old time.

Acknowledgement clocks refer to the facts they acknowledge, not to persistence of their own
bytes. Their later durable audit receipt proves that earlier fact durability. They are not
numerical model inputs. Consumers must verify a complete receipt and record their **actual
read/feature computation time** before freezing an origin; they cannot claim that SQL or the
model process read the input at its earlier journal availability. Phase 3 must preserve this
operational receipt and index lag. An offline as-of filter cannot itself establish that a
model actually ran. SQL indexing records its own separate post-commit acknowledgement.

The journal retains the complete numerical/provenance dependency closure. Index loss cannot
erase the authority; archive equivalence is still a separate unfulfilled requirement and
authorises no deletion. Source-run recovery reuses intact durable facts only. A crash before
the final acknowledgement leaves evidence intact but unadmitted.

## Code and source binding

Freeze module-file hashes before package imports and verify them before and after capture,
parse and admission. Bind loaded Python function code to compiled source, including Python
version and relevant library versions in the build manifest. Refuse an on-disk change or
loaded-code mismatch; restart under a new build and new run instead of silently reinterpreting
old captures. Old run verification requires its exact implementation build.

Initial admission is restricted to bounded internal receipt-time measurement of Gamma
identity metadata, CLOB REST snapshots and Data API v2 taker-only trade pages. Source-event
and publication clocks stay unknown where their meaning/unit is not established. Retrieval
of historical trades is prospective knowledge of that response, not proof those trades were
known at their historical event time. Wallet/profile fields in raw responses remain local.
No authenticated operations, bulk redistribution, news text, arbitrary endpoints or paid data.
Access success is evidence of runtime availability, not a licence grant or statistical edge.
Registry rights explicitly constrain this purpose; any broader use needs a new reviewed policy.

## Index and tests

A dedicated local index function accepts only the verified run directory, never record
payloads or a bypass flag. It prepares source registry/observation rows from immutable facts,
runs existing relationship/clock/payload validators and performs exact idempotent inserts.
An index commit gets a separate receipt after successful commit; retry checks existing rows
without changing their primary journal clocks. Production URL/schema checks precede mutation.

Tests must cover pre-request policy durability, synthetic separation, diagnostic-promotion
refusal, code/version changes, raw/parse/facts/ack failures, immutable retry conflicts,
clock regression, cutoff filtering, index failure/recovery, SQLite and PostgreSQL. Model
origins/features/predictions remain outside this source-only interface and must be added
with actual computation/durability evidence in their own phase.

## D046 opt-in targeted identity source

The default receipt-time source policy is unchanged. Explicit
`receipt-time-selected-market-v1` instead permits `gamma.market`, `clob.book` and
`data.v2.trades`. `gamma.market` uses a fixed documented host/path, exact canonical decimal
market ID and no query filters. Preserve raw responses and nullable lifecycle flags; an
ID mismatch is invalid evidence for the requested mapping. Default list-source journals
cannot silently adopt this source. Current-build verification and native-clock/rights
restrictions remain in force. See ../implementation/PHASE_03_IDENTITY_REFRESH_CONTRACT.md.
This does not establish panel eligibility, economic event grouping or origin admission.
