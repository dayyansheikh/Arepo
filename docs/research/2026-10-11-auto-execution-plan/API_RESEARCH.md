# Polymarket programmatic trading: API and engineering research (2026-10-11)

Independent web research by a subagent. Facts are cited inline; items marked UNVERIFIED need confirmation before implementation. Nothing was signed up for, signed or called with authentication.

## Polymarket programmatic trading: engineering research (2026-10-11)

**Correction to the brief.** The current state now has two layers on top of the 2026-04-28 "CLOB V2" cutover:
- **CLOB V2 / CTF books.** pUSD collateral, CTF Exchange `0xE111180000d2663C0091e4f400237545B87B996B`, NegRisk Exchange `0xe2222d279d744050d28e00520010520000310F59`, EIP-712 domain version **"2"**.
- **Polymarket Protocol V2.** This is new: ExchangeV3 `0xe3333700cA9d93003F00f0F71f8515005F6c00Aa` with domain version **"3"**, a PositionManager ERC-1155 ledger `0x006F54F7…9fEF`, and a Router `0x1212…2600`. It has been in a canary period from Oct 5 to Oct 30, 2026. Net-new markets are *tentatively* moving to it on **Nov 2, 2026**. Existing CTF holdings are not converted.
- **What a bot has to do.** Branch per market on Gamma `version` ("v1" → `clobTokenIds`, "v2" → `positionIds`). Sign with the matching domain, and hold two separate approval sets.
- Sources: https://docs.polymarket.com/migrate/polymarket-v2/overview.md, https://docs.polymarket.com/migrate/polymarket-v2/api-integrations.md, https://crypto.news/polymarket-v2-could-change-how-users-bet-on-events/ (dates come from secondary press and are UNVERIFIED in the official docs).

### 1. Authentication
- **L1:** EIP-712 `ClobAuth` (domain `ClobAuthDomain`, v"1", chainId 137) with headers `POLY_ADDRESS/SIGNATURE/TIMESTAMP/NONCE`. Creds come from `POST /auth/api-key` (create) or `GET /auth/derive-api-key` (derive), which return apiKey/secret/passphrase. https://docs.polymarket.com/trading/wallets-auth.md
- **L2:** headers `POLY_ADDRESS, POLY_SIGNATURE, POLY_TIMESTAMP, POLY_API_KEY, POLY_PASSPHRASE`. The signature is `urlsafeB64(HMAC-SHA256(b64decode(secret), ts+method+path+body))`; query strings are not signed. (same URL)
- **Signature types:** `0` EOA, `1` POLY_PROXY (legacy, Magic/Google), `2` GNOSIS_SAFE (legacy), `3` DEPOSIT_WALLET. Type 3 has been the default for accounts created since May 4, 2026.
  - **Who is maker and signer:** `maker` is the funding wallet (the old "funder" concept). `signer` equals `maker` for EOA and Deposit Wallet, and is the account signer for Proxy and Safe.
  - **EOAs:** usable only "if your EOA is allowlisted for trading". How to get allowlisted is undocumented.
  - https://docs.polymarket.com/trading/wallets-auth.md, https://docs.polymarket.com/trading/place-orders.md
- **Session keys (beta):** a Deposit Wallet owner authorises a separate EOA signer.
  - It "cannot withdraw funds" and can be scoped to `CLOB`, `COMBOSRFQ` or `ALL`.
  - `validUntil` is fixed at now+180 days. Revoking the key cancels its open orders.
  - Setup needs a Builder API key that has been enabled for session-key management (via builder@polymarket.com).
  - The owner cannot see the session key's orders. https://docs.polymarket.com/trading/session-keys.md
- **SDK config:**
  - TS: `createSecureClient({signer, wallet?, apiKey})` with `relayerApiKey` / `builderApiKey`.
  - Python: `AsyncSecureClient.create(private_key, wallet?, api_key)`.
  - Env vars: `SIGNER_PRIVATE_KEY`, `POLYMARKET_WALLET_ADDRESS`, plus relayer/builder keys. (wallets-auth URL)

### 2. Wallet and funding
- **pUSD:** an ERC-20 with 6 decimals, USDC-backed, at `0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB`.
  - Obtain it with `CollateralOnramp.wrap(USDC.e, to, amount)` (Onramp `0x93070a847efEf7F70739046A929D47a521F5B8ee`); approve the Onramp on USDC.e first.
  - Unwrap with `CollateralOfframp.unwrap` (`0x2957…5854`). Both can be paused (`OnlyUnpaused()`).
  - Bridge deposits are auto-wrapped. https://docs.polymarket.com/concepts/pusd.md, https://docs.polymarket.com/resources/contracts.md
- **Approvals:**
  - pUSD `approve(max)` to the Standard Exchange, the NegRisk Exchange and ExchangeV3.
  - CTF `setApprovalForAll` to the Standard Exchange and the NegRisk Exchange.
  - PositionManager `setApprovalForAll` to ExchangeV3.
  - "Existing CTF permissions do not grant these approvals."
  - After approving, sync the CLOB cache with `GET /balance-allowance/update` (`asset_type` = COLLATERAL / CONDITIONAL / CONDITIONAL-V2).
  - https://docs.polymarket.com/trading/wallets-auth.md
- **Gas:**
  - Deposit, Safe and Proxy wallets are gasless via the Relayer (`https://relayer-v2.polymarket.com/submit`; states `STATE_NEW` → `STATE_CONFIRMED`, with terminal `STATE_FAILED` / `STATE_INVALID`).
  - EOAs pay POL for every onchain action. (same URL)
  - The `/submit` call returns a `transactionID`; poll for the hash. https://docs.polymarket.com/changelog/predictions.md
- **Chain:** Polygon 137.
- **Testnet (Amoy 80002):**
  - The `py-clob-client-v2` config contains Amoy addresses, including an Amoy ExchangeV3 `0x9fE6…0C3D`. https://raw.githubusercontent.com/Polymarket/py-clob-client-v2/main/py_clob_client_v2/config.py, https://pypi.org/project/py_clob_client_v2/
  - The official docs list no Amoy contracts and no sandbox. **A usable Amoy CLOB with markets and pUSD is UNVERIFIED.**

### 3. Order lifecycle
- **Signed struct:** `salt, maker, signer, tokenId, makerAmount, takerAmount, side(0/1), signatureType, timestamp(ms), metadata(bytes32), builder(bytes32)`.
  - `expiration` (GTD, seconds) and `orderType` sit outside the signed struct.
  - Amounts are 6-decimal integers.
  - Domain name is `Polymarket CTF Exchange`. `neg_risk` selects the CTF verifying contract.
  - Deposit Wallet orders use an ERC-7739 `TypedDataSign` wrapper.
  - https://docs.polymarket.com/trading/place-orders.md
- **Precision:** `GET /book` returns `tick_size`, `min_order_size` (e.g. 5), `neg_risk` and `version`.
  - Tick sizes are 0.1, 0.01, 0.005, 0.0025, 0.001 and 0.0001. Size has 2 decimals; amount decimals depend on the tick.
  - Handle `tick_size_change` events. (same URL)
- **Order types:**
  - GTC.
  - GTD: expires 60 s early and must be at least 3 min out.
  - FOK and FAK.
  - `postOnly` with GTC or GTD.
  - GTC/GTD BUY is sized in shares; FOK/FAK BUY is sized in collateral. (same; https://docs.polymarket.com/migrate/polymarket-v2/api-integrations.md)
- **Placing orders:** `POST /order`, or `POST /orders` with 1–15 orders.
  - A batch can return per-order errors inside a 200 response.
  - Since Jul 24, 2026, FAK/FOK return `tradeIDs` instead of tx hashes.
  - **No idempotency key is documented.** Uniqueness comes from `salt` + `timestamp`.
  - https://docs.polymarket.com/trading/place-orders.md, https://docs.polymarket.com/trading/matching-engine.md, https://docs.polymarket.com/changelog/predictions.md
- **Cancelling:**
  - `DELETE /order` (single).
  - `DELETE /orders` (batch). The docs give 3,000 IDs, but the Jun 15 changelog says the cap is 1,000. **Conflict; assume 1,000.**
  - `DELETE /cancel-market-orders` (by asset_id or market).
  - `DELETE /cancel-all`.
  - Responses carry `canceled` and `not_canceled{id:reason}`.
- **Reading:** `GET /data/order/{id}`, `GET /data/orders`, `GET /data/trades` (filters `after`/`before`). https://docs.polymarket.com/trading/manage-orders.md
- **Order statuses:** `live`, `matched`, `delayed` and `unmatched`. A delayed order **cannot be cancelled**.
- **Trade statuses:**
  - `MATCHED_NOT_BROADCASTED` → `MATCHED` → `MINED` → `CONFIRMED` (terminal).
  - `RETRYING` (not terminal) and `FAILED` (terminal).
  - Settlement is atomic, so a FAILED trade did not happen.
  - https://docs.polymarket.com/concepts/order-lifecycle.md, https://docs.polymarket.com/trading/realtime-order-updates.md
- **Restarts and restricted modes:**
  - During restarts, order calls return 425 (with Retry-After).
  - For 2 min afterwards the engine is post-only (503 `post_only_mode`).
  - 503 "trading is disabled" means cancel-only or fully disabled.
  - Restarts are announced on Telegram/Discord about 2 days ahead.
  - `GET /auth/ban-status/closed-only` reports whether the account is limited to position-reducing orders.
  - https://docs.polymarket.com/trading/matching-engine.md, https://docs.polymarket.com/trading/manage-orders.md

### 4. Real-time
- **User channel:** `wss://ws-subscriptions-clob.polymarket.com/ws/user`.
  - Auth is `{auth:{apiKey,secret,passphrase}, type:"user", markets?:[conditionIds]}`.
  - Events: `order` (PLACEMENT / UPDATE / CANCELLATION) and `trade` (statuses as above).
  - Keepalive: send `PING` every 10 s.
  - **No sequence numbers and no replay.** After reconnecting, re-read open orders and trades over REST. https://docs.polymarket.com/trading/realtime-order-updates.md
- **Market channel:** `wss://ws-subscriptions-clob.polymarket.com/ws/market`.
  - Subscribe with `assets_ids`.
  - Events: `book`, `price_change`, `last_trade_price`, `tick_size_change`, plus `best_bid_ask`, `new_market` and `market_resolved` when `custom_feature_enabled` is set.
  - Book hashes are optional. Reconnect behaviour is undocumented. https://docs.polymarket.com/market-data/realtime-data.md
- **Heartbeats (dead-man switch):**
  - `POST /v1/heartbeats` with `{"heartbeat_id":""}`, then every 5 s send the latest returned ID.
  - If no valid beat arrives within 10 s, **all open orders for those credentials are cancelled**. The check runs every 5 s, so cancellation can lag by up to 5 s.
  - A stale ID gets a 400 "Invalid Heartbeat ID" that includes the expected ID.
  - REST only; SDK support is "coming soon". https://docs.polymarket.com/trading/manage-orders.md

### 5. Limits
- **How limits work:** they are per IP, enforced by Cloudflare, and **throttled (queued) rather than rejected**. Separate per-signer token buckets exist but are not quantified here (UNVERIFIED). https://docs.polymarket.com/api-reference/rate-limits.md
- **Trading endpoints (burst per 10 s / sustained per 10 min):**

| Endpoint | Burst / 10 s | Sustained / 10 min |
|---|---|---|
| `POST /order` | 5,000 | 120,000 |
| `DELETE /order` | 5,000 | 120,000 |
| `POST /orders` | 2,000 | 21,000 |
| `DELETE /orders` | 2,000 | 15,000 |
| `/cancel-all` | 250 | 6,000 |
| `/cancel-market-orders` | 1,500 | 21,000 |

- **Data endpoints (per 10 s):** `/data/orders` 500, `/data/trades` 500, `/book` 1,500, balance-allowance GET 200 and UPDATE 50, Data API v2 `/v2/positions` 200. Builder tiers can raise limits. (same URL)
- **Batch size:** 15 orders per `POST /orders`.
- **Open orders:** no per-account open-order cap is documented. Order size is limited to balance minus amounts reserved by open orders. https://docs.polymarket.com/concepts/order-lifecycle.md
- **Crypto taker delay:**
  - Changelog: **150 ms since 2026-09-04 14:00 UTC** (it was 50 ms before that).
  - The lifecycle page still says 250 ms (stale). Sports markets have their own delay windows.
  - https://docs.polymarket.com/changelog/predictions.md

### 6. Post-trade
- **Positions:** Data API v2 is at `https://data-api.polymarket.com/v2` (`/v2/positions`, `/v2/activity`, `/v2/trades`). v1 has been frozen since Sep 4. https://docs.polymarket.com/changelog/predictions.md
  - Press reports v1 retiring on Oct 24 (crypto.news; UNVERIFIED).
- **Split, merge and redeem:**
  - V2 markets use the Router: `split(bytes31 cid, amt)`, `merge`, `redeem(cid, outcomeIndex 0/1, amt)`. Approve pUSD to the Router (split) or PositionManager `setApprovalForAll(Router)` (merge/redeem).
  - CTF markets use `CtfCollateralAdapter` `0xAdA1…cE1f` or `NegRiskCtfCollateralAdapter` `0xadA2…eAab`, with the classic `splitPosition` / `redeemPositions` calls and `indexSets [1,2]`.
  - The v1 Neg Risk Adapter `0xd91E…5296` is deprecated; redeems to it ended Jul 17.
  - Redemption has no deadline.
  - Optional AutoRedeemer `0xa120…00af` (operator approval; it does not schedule anything by itself).
  - https://docs.polymarket.com/trading/positions/manage.md, https://docs.polymarket.com/migrate/polymarket-v2/contract-integrations.md
- **Neg-risk conversion:** one NO share converts to one YES share in every other outcome, atomically. V2 does this via Router + NegRiskModule; CTF via the Neg Risk Adapter. Do not trade placeholders or "Other". https://docs.polymarket.com/concepts/negative-risk.md
- **Fees:**
  - **Taker-only, applied at match.** Orders carry no fee field.
  - Formula: `fee = C·feeRate·p(1−p)`. Crypto rate 0.07; sports and most others 0.04–0.05; geopolitics 0. Rounded to 5 dp.
  - BUY fees are added to spend; SELL fees are deducted from proceeds.
  - https://docs.polymarket.com/trading/fees.md, https://docs.polymarket.com/migrate/polymarket-v2/api-integrations.md
- **Maker rebates:**
  - Paid daily in pUSD to the wallet, pro rata by fee-equivalent within each market.
  - The pool is 20% (crypto), 15% (sports) or 25% (others) of taker fees.
  - $1 minimum; no query API is documented.
  - https://docs.polymarket.com/programs/maker-rebates.md

### 7. Tooling
- **Official unified SDKs:** TS `@polymarket/client` and Python `polymarket-client` (Python ≥3.11).
  - They need ≥0.12.0 for Protocol V2; latest is 0.13.0.
  - Rust: unified SDK in progress; `polymarket_client_sdk_v2` 0.7.0 meanwhile, which has no Deposit Wallet or batch client.
  - https://docs.polymarket.com/migrate/polymarket-v2/sdk-integrations.md, https://docs.polymarket.com/changelog/sdks.md, https://docs.polymarket.com/migrate/clob-sdk-to-unified-sdk.md
- **Legacy SDKs:**
  - `@polymarket/clob-client-v2`, `py-clob-client-v2` (1.2.0, Sep 25 2026, supports `position_id`/ExchangeV3), plus the builder-relayer and builder-signing SDKs. All are told to migrate.
  - The pre-V2 `py-clob-client` / `clob-client` do not work against production.
  - https://pypi.org/project/py_clob_client_v2/, https://docs.polymarket.com/migrate/clob-sdk-to-unified-sdk.md
- **Builder code:** a `bytes32` in the signed order, emitted in `OrderFilled`, used for attribution and leaderboards.
  - Builders can add their own fees: taker up to 100 bps, maker up to 50 bps, default 0.
  - Builder keys also unlock relayer access and rate tiers.
  - https://docs.polymarket.com/programs/builders/fees.md, https://docs.polymarket.com/programs/builders/overview.md
- **Third-party frameworks:**
  - **NautilusTrader:** Rust adapter, V2-only, signature types 0–3, GTC/GTD/FOK/IOC→FAK, post-only, 15-order batches. Startup reconciliation fails while settlement is unresolved. Approvals are not automatic. Currently documented in nightly/pre-release builds; Protocol V2/ExchangeV3 is not mentioned (UNVERIFIED). https://nautilustrader.io/docs/nightly/integrations/polymarket/
  - **ccxt:** has a `ccxt.prediction.polymarket` class with create/fetch/cancel; V2 status UNVERIFIED. https://docs.ccxt.com/docs/examples/ts/prediction-polymarket-end-to-end
  - **pmxt:** MIT licence, hosted or self-hosted sidecar, Polymarket `createOrder`; V2/pUSD not mentioned (UNVERIFIED). https://github.com/pmxt-dev/pmxt
  - **Hummingbot:** no official Polymarket connector found. https://hummingbot.org/exchanges/
- **Sandbox / paper trading:** no official sandbox or paper-trading facility is documented (see the Amoy note in section 2).

### 8. Kalshi (possible second venue)
- **Auth:** API key ID plus a per-request signature over `timestamp_ms + METHOD + path` (no query string). RSA-PSS-SHA256 (2048-bit) or Ed25519. Headers `KALSHI-ACCESS-KEY/-TIMESTAMP/-SIGNATURE`. https://docs.kalshi.com/getting_started/api_keys
- **Demo:** `https://external-api.demo.kalshi.co`. Production: `https://external-api.kalshi.com/trade-api/v2`.
- **Orders:** `POST /portfolio/events/orders` with `side` bid/ask on YES, dollar-string prices, fractional `count`.
  - TIF: `fill_or_kill`, `good_till_canceled` (+`expiration_time`), `immediate_or_cancel`.
  - Flags: `post_only`, `reduce_only` (IOC only), `client_order_id`, mandatory self-trade prevention, `cancel_order_on_pause`.
  - Legacy `/portfolio/orders` is deprecated no earlier than May 6, 2026.
  - https://docs.kalshi.com/api-reference/orders/create-order-v2.md

### Most important engineering implications
1. **Branch per market version.** v1/CTF uses `clobTokenIds`, domain "2" and 0xE111/0xe222 by `neg_risk`. v2 uses `positionIds`, domain "3" and ExchangeV3. Read `version`, `tick_size`, `min_order_size` and `neg_risk` from `/book` right before signing. Pin SDK ≥0.12.
2. **Settlement-aware ledger.** Book a fill as *provisional* at MATCHED and as *final* only at CONFIRMED. Reverse anything that goes FAILED. Treat RETRYING and MATCHED_NOT_BROADCASTED as open. Key on `tradeID`, not tx hash.
3. **Build your own idempotency.** No client order ID exists. Persist salt, timestamp and the order hash before submitting. If a submission times out, reconcile via `/data/orders` and `/data/trades` before resending. Inspect every per-order result in batch responses.
4. **Use the heartbeat dead-man switch** (5 s beat, about 10–15 s to cancel) from a process separate from strategy logic. Also run an explicit `cancel-all` on shutdown. Remember that `delayed` orders cannot be cancelled.
5. **WebSockets are not authoritative.** There are no sequence numbers or replay. On every reconnect, rebuild state from REST and then apply stream events. PING every 10 s.
6. **Treat approvals and balances as preflight checks.** Approvals cover three spenders for pUSD and three operator approvals. Refresh with `/balance-allowance/update`, and fail closed if anything is missing (error "not enough balance / allowance").
7. **Prefer a Deposit Wallet with a CLOB-scoped session key.** The key cannot withdraw, expires in at most 180 days and can be revoked, which limits the damage if the bot is compromised. Keep the owner key offline. EOAs need allowlisting plus POL.
8. **Handle restart and restricted modes explicitly.** 425 means back off using Retry-After. Expect a 2-minute post-only window afterwards. 503 "trading is disabled" means pause new orders. Check the closed-only status.
9. **Price fees and delays into decisions.** The taker fee `C·r·p(1−p)` (plus any builder fee) applies at match. Crypto markets have a 150 ms taker delay with re-validation. Rate limits throttle by queueing silently, so measure latency rather than waiting for 429s.
10. **Automate redemption per position system.** Use the Router for v2 and the adapters for CTF. A missing position does not mean the position is flat, because redemptions remove balances without a trade. Treat Amoy as unverified and develop against read-only mainnet plus tiny post-only orders. Note: that last point is a design suggestion, not a documented facility.

