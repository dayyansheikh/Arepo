# D112 — opt-in bounded gzip transport

Basis: D110 remains failed; D111 observed identical decoded bytes for four cached first-page
requests. Gzip wire47252 versus identity548290bytes,31.7/34.9ms versus158.0/99.7ms. This is
feasibility evidence, not a full-universe timing guarantee. No new panel is authorised by
this document until implementation/tests/review/commit and a separately frozen protocol.

## Contract

- Default identity capture and v1/v2 sessions/receipts remain unchanged. Opt-in gzip is
  restricted to Gamma keyset and requires the existing bounded reused HTTP/1 client.
- New capture session/receipt v3 binds an explicit immutable HTTP payload policy, source,
  Accept-Encoding request header and decoded reservation. Existing connection limits,
  cookie clearing, no redirects/retries, response and time bounds remain.
- raw.bin, raw_bytes and raw_hash ALWAYS refer to exact received HTTP entity-body bytes,
  including gzip when present. Persist raw/receipt/raw_ack before decompression/JSON parsing.
  No hidden httpx decompression or replacement of original encoded bytes.
- Accept only identity fallback or one complete CRC-valid gzip member. Reject truncation,
  concatenated members, trailing bytes, other encodings and expansion beyond the frozen
  per-response decoded limit. No unbounded flush/decompression allocation.
- Wire and decoded totals each have the existing byte ceiling; they are separate counters.
  Receipt records decoded bytes charged before request and the reserved decoded limit
  min(per_response,total_remaining). Successful decoding records exact decoded hash/size;
  failed/unavailable decoding charges the full reservation conservatively, with decoded
  size/hash missing. Never call a budget charge an observed decoded length.
- Parsed v2 records bind decoded size/hash/charge and existing raw hash. Numerical and JSON
  rules remain unchanged. Actual receive/parse/ack clocks retain their existing meanings;
  decompression does not create a venue or historical clock. Crash recovery uses a fresh
  parse clock, never rewrites a partial parse, and retains malformed encoded bytes.
- Read-only verification validates v3 policy/source/header/bounds and decoded evidence.
  Reusable payload helper derives JSON bytes only from a verified capture; old unsupported
  encoded captures remain unsupported. No generic arbitrary payload admission.
- Opt-in frame v5 binds payload policy and independently reconciles decoded counters in
  cursor/ordinal order, exposes wire/decoded costs and retains every failed attempt.
  Identity frame v4 remains unchanged. Exact cursor, scope, identities, row hashes,
  missingness and sequential causal ordering stay enforced.
- Frame facts and selection metadata use the verified decoded payload. No guessed cursors,
  smaller universe, larger API pages, parallel cursor collection or deadline relaxation.
  Old frames still require their original Git implementation. No production/SQL/API change.

## Ordered work / acceptance

1. Add capture policy/decoder, explicit opt-in, receipt/parse evidence and strict verification.
2. Add frame-v5 policy/counters/payload parsing and selection metadata integration.
3. Synthetic tests: legacy/default refusal, exact numeric/cursor/identity equivalence;
   malformed CRC/truncated/trailing/concatenated/unsupported encoding; expansion/per-session
   limits; HTTP/transport/cancellation failure; raw-before-parse crash/torn recovery;
   wire/decoded tampering and changed session/header/source; frame stop/retry budgets;
   full frame/selection/original-reader recovery under committed code.
4. Run affected capture/source/frame/selection/window/original recovery tests and lint;
   self-review no float conversion, silent decode, chronology or budget bypass.
5. Commit and record exact tests/evidence/checkpoint/PR. Only then assess a separately
   predeclared integration with full reservation. No rerun of failed D106/D110.

Canonical field implications are additive at the isolated journal layer: encoded source
bytes and deterministic decoded hashes retain exact numerical provenance. No database
migration, retention change or reinterpretation of legacy records. Synthetic gzip fixtures
are not empirical frame acceptance. Phase3 remains incomplete; Phase4 stays excluded.

## Exact additive journal fields

| Location | Field | Type / semantics |
|---|---|---|
| Session v3 | http_payload_policy | Exact frozen GZIP_HTTP_POLICY object; Gamma keyset only, reused HTTP/1 and bounded single-member gzip. |
| Receipt v3 | request.headers.Accept-Encoding | Literal string gzip; actual response may be identity fallback. |
| Receipt v3 | decoded_budget_before | Exact JSON integer,0..total-1 bytes previously **charged**, including conservative failed-decode reservations; not an observed decoded length. |
| Receipt v3 | decoded_byte_limit | Exact JSON integer,1..4,194,304 bytes; min(response ceiling,remaining charged-byte budget). |
| Parsed v2 | decoded_bytes | Exact integer0..decoded_byte_limit or null; only the actual successful decoded length. |
| Parsed v2 | decoded_hash | Lowercase SHA256 of exact decoded bytes, or null if decoding was not successful/available. |
| Parsed v2 | decoded_budget_charge | Exact integer0..decoded_byte_limit; actual decoded length when known, full reservation otherwise. |
| Frame v5 page | decoded_bytes/hash/budget_charge | Verified copies of the parsed evidence; ordered budget lineage must reconcile. |
| Frame v5 report | decoded_bytes | Sum of known decoded lengths; never substitute it for a complete total when any are unavailable. |
| Frame v5 report | decoded_unavailable_attempts | Integer count of verified attempts with unknown decoded size. |
| Frame v5 report | decoded_budget_charge | Sum of conservative charges, bounded by the session total. |
| Frame v5 report | raw_bytes_semantics | Explicit received HTTP entity-body semantics; gzip raw.bin is encoded. |

All are immutable exclusive-write fields covered by existing payload/ack hashes and the
pinned implementation. No lossy numeric conversion. Encoded bytes have the actual receive
clock; decoding/JSON conversion is available only after parsed acknowledgement. HTTP Date,
Age/cache headers are source metadata, never a reconstructed venue event clock. Missing
fields in old schemas are not backfilled. No SQL migration or production adoption.

Implementation and synthetic acceptance complete:265 pre-final affected tests;78 final scoped
tests, overlapping. Exact evidence in PHASE_03_GZIP_VALIDATION.json. Full empirical integration
is still gated by reservation and a new frozen protocol; no timing improvement is presumed.
