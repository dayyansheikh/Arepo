# Polymarket source and field catalogue

Audit date: 19 September 2026. Inventory was assembled before feature prioritisation. The boundary is the official documentation indexes, their REST/stream schemas, documented SDK types, current contract-address registry and inspected public contract source/ABI artifacts. This is a comprehensive **documented-surface inventory**, not a claim that every possible undocumented runtime field or contract extension has been observed.

Eight bounded live API probes returned HTTP 403 from this research environment. The reason was not established; these results do not prove the APIs are unavailable to all clients. No restriction was bypassed. No live WebSocket capture or chain replay was performed. Runtime availability, undocumented fields, historical completeness, actual latency and current bytecode/source equivalence remain explicit audit gaps. The inaccessible standalone Data API v2 schema was substantially recovered from official endpoint documentation, including all 20 listed v2 operations.

## Catalogue files and how to use them

| File | Coverage | Interpretation |
|---|---:|---|
| `catalogues/polymarket_unified_endpoints.csv` | 309 host/method/path records: 223 production-host records and 86 staging-host records | Union of downloaded OpenAPI and inline documentation schemas; includes public, authenticated and transactional operations. Inventory is not execution authority. |
| `catalogues/polymarket_endpoints.csv` | 203 operation records from seven standalone REST schemas | Retains server definitions, parameters, request/response schemas and security declarations. |
| `catalogues/polymarket_documentation_endpoints.csv` | 181 operation occurrences in endpoint pages | Overlaps the standalone schemas; do not add these counts as unique endpoints. |
| `catalogues/polymarket_fields.csv` | 2,771 declared property occurrences | All traversed schema properties, including nested definitions; not all are response fields. |
| `catalogues/polymarket_documentation_fields.csv` | 6,796 property occurrences | Repeated shared schemas remain source-linked; not 6,796 unique public fields. |
| `catalogues/polymarket_schema_references.csv` | 1,848 references | Preserves `$ref` targets instead of infinite recursive expansion. |
| `catalogues/polymarket_streams.csv` | 70 channel/message records | Includes subscription/control and authenticated messages as well as public data messages. |
| `catalogues/polymarket_sdk_types.csv` and `polymarket_sdk_fields.csv` | 28 declared types, 217 field occurrences | Supplements wire schemas with SDK market/sports/RTDS/comment/TWAP types; SDK names can differ from wire names. |
| `catalogues/polymarket_contracts.csv` | 29 currently documented addresses | Includes proxies/implementations, collateral, factories, oracle and deprecated adapter. |
| `catalogues/polymarket_onchain_abi.csv` and `polymarket_onchain_abi_fields.csv` | 140 ABI members, 469 input/output component occurrences | CTF artifacts, legacy NegRisk adapter and UMA optimistic oracle; repeated artifacts remain provenance-linked. |
| `catalogues/polymarket_onchain_interfaces.csv` | 240 interface declarations | Current exchange/collateral/adapters and UMA interface events, functions, errors and structures. |
| `catalogues/polymarket_onchain_declarations.csv` | 17 selected event/structure declarations | Human-traceable core fill, CTF and oracle declarations; use full interface/ABI tables for breadth. |

Field tables record the property name, type/schema, optionality/required status, nullability where declared, description where supplied and the exact parent schema pointer/source. A missing type or description is **unspecified by that source**, not evidence that the field is absent or unimportant. Identifiers, timestamps, units and update semantics should be inherited only from an explicit parent/source contract, never guessed from a plausible name. Flexible maps, arbitrary payload objects, unions and additional properties are preserved in their schemas; they prevent a finite field enumeration from proving a closed runtime schema.

Raw evidence manifests record source URLs, retrieval status, byte counts and SHA-256 hashes. The endpoint-page manifest contains 221 downloaded pages. Source descriptions and schemas must be checked against the pinned copy when documentation changes. This catalogue does not collapse camelCase Gamma/SDK fields into snake_case Data API v2 names without a versioned mapping.

## REST source families — inventory, before usefulness

| Family / production host | Operation records | Contents and scope |
|---|---:|---|
| Gamma — `gamma-api.polymarket.com` | 42 | Markets/events by ID/slug/list/keyset; tags and related tags; series; teams/sports/type metadata; search; comments; public profiles; creator/display metadata and descriptions. |
| CLOB — `clob.polymarket.com` | 66 | Books and batched books; side-specific prices, midpoints, spreads and last trades; price histories; tick/fee/negative-risk/market configuration; sampling markets; rewards/rebates; account/order/trade/authentication operations, classified separately. |
| Data API — `data-api.polymarket.com` | 39 | Legacy user activity/positions/trades/holders/value/leaderboards/accounting and current v2 equivalents plus freshness, price history, resolution and user statistics. |
| Relayer — `relayer-v2.polymarket.com` | 7 | Transaction/status, nonce, deployment and relayer-related interfaces; submitting transactions and key management are operational, not public research reads. |
| Combos RFQ — `combos-rfq-api.polymarket.com` | 4 | Combo discovery and quotation/last-look operations; quotes and authenticated gateway details are not assumed publicly readable. |
| Bridge — `bridge.polymarket.com` | 5 | Supported assets, quotations, transaction status and address creation surfaces; list/status documentation can inform collateral lifecycle, but no action endpoint was invoked. |
| Perpetuals — `api.perpetuals.polymarket.com` | 60 | Public instruments/markets/book/trades/price series and authenticated account/order/margin/referral surfaces. Adjacent platform surface, not binary event-contract data. |

The 20 v2 paths are `/v2/activity`, `/v2/activity/combos`, `/v2/approvals`, `/v2/biggest-winners`, `/v2/builders/leaderboard`, `/v2/builders/volume`, `/v2/holders`, `/v2/leaderboard`, `/v2/live-volume`, `/v2/oi`, `/v2/positions`, `/v2/positions/combos`, `/v2/prices-history`, `/v2/resolutions`, `/v2/status`, `/v2/trades`, `/v2/user-pnl`, `/v2/user-stats`, `/v2/user-volume`, and `/v2/value`. Preserve v1/v2 differences rather than silently substituting the latest endpoint in historical pipelines. [Official Data API migration guide](https://docs.polymarket.com/api-reference/data-api/migrating-from-v1).

Inventory includes write endpoints because they appear in the official source schemas; none was called. A POST can be a read-only batch query, while a GET can expose authenticated private account information. Classify by documented semantics and security requirements, not verb alone. In particular, authenticated CLOB account trades must not be conflated with public Data API trades. Authentication-free documentation also does not prove a redistribution licence.

## Field families retained without an early relevance filter

**Identity and descriptions:** native event/market IDs, conditions, questions, outcome/token arrays, slugs, titles, descriptions, resolution sources, tags, related tags, series, teams, creator/profile fields, images and optimised image metadata. Descriptions, labels and imagery may initially appear unhelpful but can identify rule changes, mapping errors or market types. Store them in the catalogue without claiming predictive value.

**Lifecycle and control:** creation/update/start/end times; active/closed/archived/restricted/order-accepting flags; market/sports type; negative risk; enable-order-book and other capability flags; resolution/oracle status, outcome prices and configuration. Timestamp semantics vary: update time is not necessarily first public information time, and end date is not necessarily the underlying event's information time.

**Prices/liquidity/activity:** price/size levels, best bid/ask, midpoint, spread, last trade, rolling volume and liquidity aggregates, changes, history points, reward configuration and fee/tick/minimum-size parameters. Retain source-native units and strings. Liquidity displayed by Gamma is not interchangeable with executable book depth. A history point may be aggregated and should not be treated as a tick or a complete quote path without evidence.

**Trades/positions/wallets:** public wallet/proxy identifiers, side, asset/outcome, price, size, transaction identifiers and times; positions, current/initial values, realised/unrealised metrics where documented, holder sizes, portfolio values, activity types, leaderboard ranks and user statistics. The complete catalogue retains display/profile and builder fields as well as numerical fields. Current wallet statistics are not historical as-of statistics.

**Streams and transport:** event type, topic, market/token IDs, payload and envelope times, sequence/hash where supplied, decimal strings, side, book arrays, price changes, tick transitions, settlement/game state, comments/reactions and subscription/control errors. Never invent a sequence number on a channel that lacks one. Keep reconnect intervals and snapshot reconciliation state in AREPO's own envelope.

## Stream/message inventory

| Surface | Documented messages/topics | Access and reconstruction |
|---|---|---|
| Market WebSocket | `book`, `price_change`, `last_trade_price`, `tick_size_change`; optional `best_bid_ask`, `new_market`, `market_resolved`; subscribe/update/ping/pong controls | Public market stream. Some messages require subscription feature flags. Snapshot/delta and hash semantics must be checked by replay. |
| User WebSocket | Order and trade lifecycle messages, subscriptions and controls | Authenticated own-account information; not a public trader-order feed. |
| Sports | Sports update/result with game identity, score, period, elapsed/status and related fields | Public documented stream. Corrections and game-over timing must be versioned. |
| RTDS crypto | Binance and Chainlink price updates, SDK topics `prices.crypto.binance`, `prices.crypto.chainlink` | Payload and envelope clocks differ. Preserve both and exact values. |
| RTDS TWAP | `prices.crypto.chainlink.twap`, 30- and 60-second windows | Public relay documented; direct Chainlink access uses credentials. |
| RTDS equities | Pyth equity updates and subscription snapshot | Symbol/market hours and snapshot-vs-live status matter. |
| RTDS comments | Creation/removal of comments and reactions | A deleted source record needs a deletion state, not a silent history rewrite. |
| RFQ gateway | Quoter requests/quotes/last-look and controls in schema | Access-controlled workflow; not assumed public order flow. |
| Perpetuals | Book/BBO/trades/klines/tickers/statistics plus private account/order messages | Catalogue retains both; applicability to event contracts is a separate research choice. |

[Official real-time documentation](https://docs.polymarket.com/market-data/realtime-data), [TWAP documentation](https://docs.polymarket.com/market-data/chainlink-twap), [market AsyncAPI](https://docs.polymarket.com/asyncapi.json). SDK topic names above are not asserted to be identical to low-level wire subscription names; use the corresponding raw schema or pinned SDK mapping.

## Pagination, rate limits, history and revisions

Endpoint tables preserve parameter schemas, including limits, offsets/cursors, time ranges, filters and response envelopes. Current v2 uses a `data` envelope and cursor pagination; do not rely on a legacy 10,000-offset ceiling as a complete archive. Exhaust all pages with logged cursor progression, stable ordering/deduplication and coverage checks. Moving datasets can change between pages; a completed traversal is not automatically a consistent snapshot. Historical extent must be measured by endpoint and market, including closed/delisted assets and empty responses.

At retrieval, official IP limits included Gamma general 4,000 requests/10s, markets 300/10s and events 500/10s; Data v2 general 800/10s, trades 300/10s and positions/activity/price history 200/10s; CLOB book 1,500/10s and batch books 500/10s. These are ceilings, not a collection target. Throttling can delay/queue requests and therefore contaminate latency; log it. Shared IP, endpoint and signer limits differ. [Current rate limits](https://docs.polymarket.com/api-reference/rate-limits).

For each source, prospectively measure response age, request latency, missing-page frequency, earliest/latest historical item, revision frequency and undocumented property drift. Re-fetch representative past windows and compare hashes/values to detect revisions. A current aggregate, profile or leaderboard cannot be backdated. No complete historical L2 book archive is established merely by the existence of price-history endpoints.

## Public on-chain and oracle inventory

Use the [current contract registry](https://docs.polymarket.com/resources/contracts) rather than addresses copied from old tutorials. It presently lists Polygon chain 137, CTF Exchange v2, negative-risk exchange, CTF, collateral/ramp adapters, deposit/proxy/Safe factories, combos proxy/implementation pairs and UMA components. `polymarket_contracts.csv` retains all 29 entries, including the explicitly deprecated v1 negative-risk adapter.

Every chain record needs chain ID, block number/hash/time, transaction hash/index, log index/address/topics/data, receipt status and observed confirmation/reorganisation state. Record native integers and token decimals separately. Read-only state calls at historical block numbers can add balances, approvals, payouts, oracle requests and configuration, but require provider archival coverage and block-specific semantics. An address balance today is not its balance at prediction time.

The inspected v2 exchange `OrderFilled` has order hash, maker, taker, side, token ID, maker/taker amounts filled, fee, builder and metadata. It differs from v1 event layouts; a v1 asset-ID decoder is unsafe for v2. `OrdersMatched` and `FeeCharged` add matching/fee information. CTF supplies condition preparation/resolution, split/merge/redemption and ERC-1155 transfers/approvals/balances, with payout numerators/denominator and collection/position mapping. Collateral contracts add transfers, approvals and conversion/ramp state. [Pinned exchange source](https://github.com/Polymarket/ctf-exchange-v2/tree/ccc0596074f4dfd62c944fbca4de252893b82b4b).

UMA adapter and oracle structures cover question IDs, ancillary data, request time, reward token/reward, proposal bond, liveness, proposal/dispute/settled state, proposers/disputers, expiration, proposed/resolved prices, callbacks, pause/reset/manual-resolution states and payout vectors. These are candidates for label integrity and resolution-time research. They do not automatically reveal a pre-event forecasting advantage. [Pinned UMA adapter source](https://github.com/Polymarket/uma-ctf-adapter/tree/8b76cc9e0d46c6f7450a0adb0ddc0f5b0568c9cc).

Unresolved chain coverage: full deployed ABIs for every new combos/perpetuals/factory implementation; proxy upgrade histories; deployment-bytecode matching; protocol-specific token decimals and historical conversion rules; RPC log completeness and reorg behaviour. Inspected source interfaces are not proof that a given deployed contract exposes every declaration. Public mempool visibility is provider-dependent and not established here. Treat indexers/subgraphs as secondary views requiring reconciliation, not canonical sources of event-time availability.

## Usefulness assessment — after the inventory

Prioritise exact identities/rules/clocks first, because all other experiments depend on them. Next use clean book prices/depth, raw trades and context to test incremental repricing. Then add related venues/reference prices and authoritative information. Wallet history requires a historical as-of layer; text requires a publication/receipt and deduplication layer. Incentive, lifecycle, comment, profile, image and builder fields remain catalogued even when their predictive value is unknown.

Do not collect all 223 production operations continuously. A public-data watcher plus a deliberately sampled deep panel is cheaper and scientifically more useful than indiscriminate polling. The Feature Research Register specifies which numerical fields each experiment requires; the feature schema preserves inputs before any later retention decision.

## Catalogue acceptance status

**Complete for this audit:** downloaded-schema enumeration and provenance, documented REST/stream/SDK inventory, v2 discovery, public/private/transactional distinction, contract registry and inspected ABI/interface catalogue, explicit usefulness assessment after inventory.

**Not established:** live response-field closure, WebSocket observation, per-endpoint measured history/latency, undocumented web surfaces, every deployed contract ABI and historical upgrade, commercial redistribution rights. These are a bounded follow-up verification checklist, not fields silently omitted because they seem irrelevant. No catalogue can honestly claim operational exhaustiveness while these access and observation gaps remain.
