# Phase 3 — frozen identity target adapter (D054)

This is a pure, versioned adapter for the next durable due worker. It does not authenticate
caller data, write an outcome, enable collection or admit a research origin. The worker must
consume verified origin/source/computation journals and record actual read/report clocks.

Accept one observed frozen origin quote, its actual origin time, a two-request target
Gamma-market/book source projection, and its durable quote computation. Recompute the target
projection at its original cutoff; require exact source request identity and full projection
equality. No alternate market/token, caller state override or fresh-mapping backdating.

Preserve the mapping availability from the origin and retain the fresh mapping separately.
Compare market, condition, token, mapping/rule version, outcome index and label, even when
the fresh quote reports closure. Changed identity abstains and cannot censor a valid origin.
Only `market_closed` with matching known identity and fresh identity/receipt evidence maps
to `closed`; unknown/inactive/archived lifecycle stays distinct. Failed book requests bind
the token through verified request metadata, never a missing response field. Preserve source
failures and every quote quality state without a price fallback. Unknown states fail closed.

Target availability is the durable computation acknowledgement, not the earlier raw/parse
receipt. Mapping availability remains the origin's actual old timestamp. Rechecking freshness
at computation acknowledgement may abstain, never refresh old clocks. A delayed earlier
computation continues to block a later quote until its true availability when passed to the
existing first-valid receipt selector. Preserve exact prices/sizes; midpoint comparison is
not executable profit.

Tests: matching fresh identity; every identity dimension and changed rules with closure;
failed book token; all source/lifecycle/numerical/stale states; pending earlier receipt;
first-valid selection; exact decimals; tampered projection/request/lineage/provenance; frozen
identity chronology; delayed durability; bounded input inventory; durable synthetic integration.
Existing target outputs must remain unchanged. Full regression and self-review before commit.
