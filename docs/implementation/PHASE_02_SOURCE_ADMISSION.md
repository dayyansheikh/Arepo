# Phase 2 source admission matrix

Updated 2026-09-20. All current captures are **diagnostics**, not prospective model
inputs. Synthetic tests remain synthetic; importing real diagnostics yields reconstructed
records. Runtime verification establishes access and observed shape, not research validity
or redistribution rights. Native clock ambiguity is retained, never guessed from magnitude.

| Source | Runtime evidence | Clock admission | Identity/coverage limits | Current permitted implementation use |
|---|---|---|---|---|
| Gamma markets | Two preserved market objects, HTTP 200 | Local receipt and durable parse acknowledgements; lifecycle end is not publication time | Ordered outcomes retained; chain/collateral unresolved; source event is not an independent economic event | Local diagnostic identity projection only |
| CLOB REST book | 36 bid / 130 ask levels, HTTP 200 | Receipt/ack clocks; native numeric timestamp retained without inferred unit | Token-scoped snapshot; no historical deltas or continuity claim | Exact diagnostic snapshot |
| Data API v2 trades | Two rows, HTTP 200; cursor reports more available | Receipt/ack clocks; raw native clock retained pending semantic admission | Explicit taker-only scope, bounded page, transaction hash not unique fill ID; no completeness claim | Local diagnostic trades, no flow feature admission |
| CLOB market stream | Quiet-token snapshot plus timeout; active-token snapshot plus four price-change frames | Per-frame receipt/ack clocks; native clocks remain unadmitted | One subscription at a time, bounded duration/frames; no native sequence completeness; rejected delta/reconnect requires fresh snapshot | Exact bounded replay with gaps, no continuous research history |
| Coinbase BTC-USD ticker | Preserved ticker, HTTP 200 | ISO last-trade time distinguished from full quote receipt; no quote-wide publish time invented | Single instrument and observation; no external lead/lag evidence | Reference-source diagnostic only |

Source contract hashes pin protocol/parser declarations. Source-specific parse artefacts also
record implementation hashes and their actual later computation/acknowledgement clocks.
Old artefacts are retained when code changes. The present diagnostic implementation hashes
files at invocation; a long-running prospective process must additionally bind loaded code
to its immutable build and refuse on-disk changes. This is an open admission requirement.

Raw evidence roots and numerical/hash summaries are in PHASE_02_RUNTIME_EVIDENCE.json,
PHASE_02_STREAM_EVIDENCE.json and PHASE_02_ACTIVE_STREAM_EVIDENCE.json. Preserve their
local data-dumps directories. Earlier hash-only preflights do not acquire receipt evidence
retroactively. Tests cover synthetic failures; a tested failure is not an observed outage.

The official documentation links and scope are recorded in PHASE_02_REVIEW.md. No source
has established bulk/commercial redistribution permission in this programme. Current registry
rights scope is source verification only and model-feature admission is false.

## Remaining prospective boundary

Before opening a trusted prospective path, specify whether the model reads durable journal
artefacts or the SQL index. A journal acknowledgement does not establish that a later index
transaction was visible. Likewise, a pre-commit timestamp cannot establish post-commit
availability. Bind the chosen readable artefact, actual acknowledgement, source version,
loaded parser build and predeclared admission policy without a caller Boolean override.

Required tests: torn writes/acknowledgements, recovery and duplicate imports, unavailable
index after durable journal, code-version changes, provenance/rights refusal, clock regression,
and cutoff exclusion until every required artefact is durably available. Keep source-event,
publication, receipt, raw durability, parsing and model-readable durability distinct.
No existing diagnostic may be relabelled prospective. This design and implementation gate
is still open; Phase 2 has not met its exit criteria.
