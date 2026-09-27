# Phase 3 — selected external observation boundary (D073)

## Evidence-driven source choice

Research register XNOAA calls for weather observations/forecasts with preserved receipt time,
location, valid time and QC/revisions. Current NWS documentation explicitly describes its API
as open data for any purpose, requires a User-Agent and notes QC-related observation delay up
to 20 minutes. The API also documents missing 24-hour maxima/minima outside the central time
zone. A latest station reading is neither a first release, a forecast nor a daily extreme.

Sources inspected 2026-09-27:
- https://www.weather.gov/documentation/services-web-api (access, rights, delays/known issues)
- https://api.weather.gov/openapi.json (station latest observation, GeoJSON, QuantitativeValue)
- https://www.weather.gov/disclaimer (attribution/no endorsement)
- https://www.coinbase.com/en-gb/legal/market_data (updated August 7, 2026, sections 2–3)

Coinbase is **not admitted**: its current terms restrict automated/AI-system development and
external derived works without express consent. Preserve existing diagnostics unchanged; do
not use them as model inputs or collect new Coinbase data for this programme. This finding
changes the candidate source choice, not historical evidence. No paid licence is sought.

## Implementation contract

Add an explicit opt-in receipt-time policy for `nws.station.observation`, fixed HTTPS host and
latest-observation path with a bounded uppercase station identifier; no caller URL/query/auth.
Default core and targeted Polymarket source policies remain unchanged. Use existing SourceRun
registration, quotas, raw/parse/admission receipts and actual input-read journal. Extend existing
original-code recovery to these input-read facts rather than create another storage system.

Preserve all raw bytes plus typed native quantities, units, min/max range bounds and MADIS QC.
Reported zero, source null and unreported fields are distinct. No implicit unit conversion or
QC acceptance; invalid schema stays invalid. Keep observation timestamp separate from unknown
publication/first availability. Receipt/admission/actual-read clocks are authoritative for
knowledge. Future or missing native timestamps remain flagged/unavailable, never backdated.
Source observation IDs/changed payloads are preserved without asserting first-vintage history.
No market relevance or resolution mapping is inferred from a city or question keyword.

## One public source measurement, frozen before collection

After implementation/tests/review/commit and draft PR update, execute `measure_nws` exactly once
at `data-dumps/fs2_nws_measurement_20260927_1` using that full immutable implementation SHA and
this repository. It verifies both loaded packages against the commit before creating its root.
Station is **KNYC**, selected as a fixed adapter/clock measurement, not a sampled panel member.
No search, fallback station, retry, subscription, continuous collector or SQL mutation.

One GET to `https://api.weather.gov/stations/KNYC/observations/latest`; existing explicit
Arepo User-Agent and explicit application/geo+json Accept header; no authentication, redirects or environment proxy. Request timeout 15s,
whole source budget 30s, raw response/total cap 65,536 bytes, retained source cap 1 MiB.
Reserve 1 MiB source +4 MiB compact actual read +16 MiB original recovery +1 MiB metadata
and 2 GiB free reserve before work. Original verifier timeout 300s, input read 60s. Preserve
partial failures; existing directory is terminal. Both the software tests and public attempt
must retain their actual provenance. No second public attempt merely because the first fails.

The result reports source state/hash, receipt and source/read/recovery availability, retained
bytes and unresolved semantics. A successful request proves only this restricted source path;
it does not satisfy representative pilot, relevant-market linkage, forecast innovation,
continuous numerical windows or Phase 3 completion. Failure yields unavailable data without
reclassification. Numerical data stays local; the repo evidence summary contains hashes,
clocks, source state and limitations.

## Acceptance and next integration

Test exact decimal and unit/QC preservation, invalid station/path/schema, missing/null/zero,
native clock limitations, policy before request, legacy policy refusal, failed responses,
actual source/read clocks, original-Git recovery, changed raw/policy refusal and exclusive roots.
Then measure once. For panel use predeclare and verify station/location/date/metric and rule
source correspondence against actual selected market rules, and register native age/QC/window
eligibility. Unsupported assignments remain not-applicable or unresolved. This is the external
source prerequisite; no forecast feature or Phase 4 model is implemented here.

D073 measured once under `77d6652`: HTTP 200 observed prospective NWS response, actual input read and original-Git recovery passed. Evidence: PHASE_03_NWS_SOURCE_EVIDENCE.json. The fixed KNYC reading has no automatic selected-market relevance and does not complete Phase 3. Do not repeat this measurement. Resume the live checkpoint's numerical-family/origin integration step.
