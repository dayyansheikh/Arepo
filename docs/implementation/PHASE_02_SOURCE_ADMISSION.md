# Phase 2 source admission matrix

Updated 2026-09-20; Phase 2 accepted for the bounded scope below. A new source-only run under
implementation `54be417` verifies three core sources. Earlier diagnostics remain reconstructed;
injected transports remain synthetic. Runtime access is neither redistribution permission nor
predictive evidence. Native clock ambiguity is preserved.

| Source | Runtime evidence | Admitted clock/use | Identity/coverage limits |
|---|---|---|---|
| Gamma markets | Two-market diagnostics and a new predeclared HTTP 200 response | New SourceRun receipt-time internal measurement; exact ordered identity primitives | Chain/collateral unresolved; source event is not economic independence |
| CLOB REST book | Exact diagnostic depth; new predeclared HTTP 200 snapshot | New SourceRun receipt-time snapshot | Native numeric clock unit unadmitted; token-scoped snapshot, no prior deltas |
| Data API v2 trades | Bounded diagnostic pages and new predeclared HTTP 200 page | New SourceRun receipt-time knowledge of returned taker-only rows | Historical event-time availability unproved; cursor may have more data; tx hash not fill ID; no complete-flow admission |
| CLOB market stream | Quiet snapshot/timeout, active snapshot/four changes | Diagnostic only; not a prospective model input | Bounded one-token stream, no native sequence completeness; gaps require fresh snapshot |
| Coinbase BTC-USD ticker | HTTP 200 diagnostic | Diagnostic only; not a prospective model input | Last-trade ISO time differs from whole quote receipt; single instrument/sample |

Source contracts pin protocol/parser declarations. New SourceRun also pins the loaded
implementation and internal measurement policy before collection; file changes or loaded-code
mismatch refuse admission. Existing diagnostic import remains a separate reconstructed path.
The new restricted source policy admits bounded local receipt-time measurement and excludes
redistribution, authenticated operations, paid sources, historical availability inference and
arbitrary derived models. It does not claim a commercial licence.

See the four PHASE_02_*EVIDENCE.json files for hashes and original local roots. Preserve raw
journals and the exact code build. Missing chain namespaces, native clock units, fill identity
and complete histories cannot be reconstructed from successful requests. Synthetic fault
coverage is not an observed upstream outage.

## Durable admission and consumer obligations

[The normative admission refinement](../architecture/V2_PROSPECTIVE_SOURCE_ADMISSION.md)
selects the journal as primary input authority. SQL records preserve journal fact clocks and
have an additional post-commit index receipt. A pre-commit transaction time never proves
durable source or index availability. Actual model reads and feature computation must be
captured separately before an origin is frozen. Offline as-of filtering does not establish
that a model ran.

The dedicated source index verifies run/policy/build, immutable raw/parse/admission receipts,
causal clocks and source relationships. It accepts a run directory, not arbitrary prospective
payloads. Missing/torn artefacts refuse admission without repair. Generic origin/feature/
prediction writes remain closed until their own trusted paths are implemented.

This meets Phase 2's core-source acceptance with explicit scope and exclusions. Phase 3 must
freeze a suitable frame/protocol and either admit additional source families through tested
paths or retain their missingness/ineligibility; it cannot treat diagnostic or sparse coverage
as complete prospective information.
