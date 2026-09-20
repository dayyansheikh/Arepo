# External-source register

Sources were assessed after the Polymarket inventory. Public visibility does not by itself grant bulk collection, commercial use or redistribution rights. Cost and access entries are research findings, not subscriptions or approvals.

## XKALSHI — Related prediction venue

[Primary documentation](https://docs.kalshi.com/getting_started/quick_start_market_data).

**Fields:** Market/event metadata, rules, books, trades and history

**Access rights:** Public market-data REST documented; WebSocket/auth and redistribution requirements checked separately

**Timestamp contract:** Request-time and source timestamps; preserve historical rules

**Latency history:** Live availability to measure; historical completeness differs by endpoint

**Candidate use:** Cross-venue lead and disagreement; H36

**Quality confounders:** Rule equivalence, fee/currency/expiry and clock alignment

**Cost:** No data fee assumed for documented public REST; historical/redistribution access unpriced

**Priority:** P1

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XBETFAIR — Related betting venue

[Primary documentation](https://developer.betfair.com/).

**Fields:** Exchange prices, volumes, sports/event mapping; historical data products

**Access rights:** Account/app licence and commercial terms apply; not assumed anonymous

**Timestamp contract:** Streaming receipt time, delay status and event/rule versions

**Latency history:** Live versus delayed access must be explicitly established

**Candidate use:** Cross-venue sports information; optional extension H36/H58

**Quality confounders:** Commission, suspension/in-play delay, different settlement and selections

**Cost:** Vendor/licence quote required; no purchase made

**Priority:** P2

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XCOIN — Underlying crypto market

[Primary documentation](https://docs.cdp.coinbase.com/exchange/websocket-feed/overview).

**Fields:** Trades, order books, sequence and market status

**Access rights:** Public feed documented; use market-data terms

**Timestamp contract:** Source event and receipt clocks; sequence gaps

**Latency history:** Low-latency candidate; actual AREPO lag unmeasured

**Candidate use:** External lead, volatility and market-wide context; H14/H44

**Quality confounders:** USD vs USDT, oracle price vs exchange price, venue outages

**Cost:** Public feed transport plus collection/storage; redistribution review

**Priority:** P1

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XDERIBIT — Crypto derivatives

[Primary documentation](https://docs.deribit.com/).

**Fields:** Options/futures market data, volatility and funding candidates

**Access rights:** Public data endpoints documented; conditions/redistribution require review

**Timestamp contract:** Source/receipt time, instrument expiry and quote staleness

**Latency history:** Continuous market-data candidate; historical depth not assumed

**Candidate use:** Implied uncertainty and threshold-model baseline

**Quality confounders:** Smile fitting, thin options, expiry and collateral mismatch

**Cost:** Public access where documented; archive/data licensing unpriced

**Priority:** P2

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XCME — Rates/commodities/indices

[Primary documentation](https://www.cmegroup.com/market-data.html).

**Fields:** Futures/options prices, term structure, implied rates

**Access rights:** Licensed exchange data; display availability is not a redistribution licence

**Timestamp contract:** Exchange timestamp, delay entitlement, contract roll

**Latency history:** Delay and historical entitlement depend on purchased product

**Candidate use:** Macro/commodity external-market lead

**Quality confounders:** Delayed webpages cannot establish fast edge; roll and calendar effects

**Cost:** Quote required; defer until event experiment justifies spend

**Priority:** P2

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XFRED — Macro data vintages

[Primary documentation](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html).

**Fields:** Series observations, real-time/vintage dates, release linkage

**Access rights:** API key; series-specific rights can differ

**Timestamp contract:** Vintage/realtime interval; dates alone not intraday publication evidence

**Latency history:** Suitable for vintage-aware slow tests; minute tests need direct release receipt

**Candidate use:** H45/H46; avoid revised-data leakage

**Quality confounders:** Consensus forecasts not supplied automatically; series revisions

**Cost:** Public API access with conditions; collection costs

**Priority:** P1

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XBLS — Official economic releases

[Primary documentation](https://www.bls.gov/developers/).

**Fields:** Published statistical series and release content

**Access rights:** Public API; registration/limits vary by access tier

**Timestamp contract:** Freeze first release and subsequent revisions; archive receipt time

**Latency history:** Release website and API may update at different times

**Candidate use:** Macro surprise and revision; H45/H46

**Quality confounders:** Post-release expectation and revised actual leakage

**Cost:** Public source; quota-aware collection

**Priority:** P1

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XFED — Official central-bank information

[Primary documentation](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm).

**Fields:** Meeting calendar, statements, minutes and projections

**Access rights:** Public documents; inspect reuse conditions

**Timestamp contract:** Scheduled release versus first available/received content

**Latency history:** Sparse scheduled events; accumulation takes time

**Candidate use:** Official stance/surprise and narrative changes; H19/H45

**Quality confounders:** Minutes published later than decision; speech vs policy action

**Cost:** Public source; extraction and audit costs

**Priority:** P1

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XEIA — Official energy data

[Primary documentation](https://www.eia.gov/opendata/documentation.php).

**Fields:** Energy series, categories, schedules and metadata via API v2

**Access rights:** Free API key documented

**Timestamp contract:** Observation period vs release/vintage/receipt distinguished

**Latency history:** API history does not by itself prove first-release values

**Candidate use:** Energy release surprises and revisions; H45/H46

**Quality confounders:** Unit conversion, revision and publication lag

**Cost:** Free key; processing costs

**Priority:** P2

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XSEC — Company disclosures

[Primary documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).

**Fields:** Submissions, filing accession/acceptance, company facts/XBRL

**Access rights:** Public fair-access API; identify client; <=10 requests/sec across machines per SEC policy

**Timestamp contract:** Acceptance time, earlier press releases, first receipt and amendments

**Latency history:** Near-release candidate; actual latency measured prospectively

**Candidate use:** Filing novelty and numeric surprises; H48

**Quality confounders:** Restatements, XBRL taxonomy/units, earlier dissemination

**Cost:** Public source; parsing/audit costs

**Priority:** P1

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XPARLIAMENT — Official public statements and records

[Primary documentation](https://developer.parliament.uk/).

**Fields:** Bills, votes, written statements and parliamentary feeds

**Access rights:** Public APIs; endpoint-specific terms

**Timestamp contract:** First published/received record; later corrections versioned

**Latency history:** Publication can lag real-world event

**Candidate use:** Official claim detection; H19

**Quality confounders:** Political rhetoric versus operative legal event; person/entity ambiguity

**Cost:** Public endpoints; modest collection costs

**Priority:** P2

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XNOAA — Weather observations and forecasts

[Primary documentation](https://www.weather.gov/documentation/services-web-api).

**Fields:** Forecasts, alerts, station observations, issue/valid times

**Access rights:** Open data; User-Agent required; unpublished reasonable rate limits

**Timestamp contract:** Issued forecast vintages, valid time, station measurement and receipt

**Latency history:** NWS documents some observation delays up to 20 minutes; do not assume real-time

**Candidate use:** Weather forecast innovation; H47

**Quality confounders:** Station/location/day rules, QC revisions, deterministic versus probabilistic forecast

**Cost:** API free; archive and alignment costs

**Priority:** P1

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XNEWS — News discovery

[Primary documentation](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/).

**Fields:** Article URLs, metadata and search discovery; GDELT event records separately

**Access rights:** API availability does not license full article storage or redistribution

**Timestamp contract:** First discoverability/receipt and publisher time separate

**Latency history:** Historical discovery not guaranteed complete or publication-causal

**Candidate use:** News novelty/acceleration/corroboration; H16/H17/H20

**Quality confounders:** Syndication, coverage bias, timezone and publisher edits

**Cost:** Discovery may be low-cost; publisher rights/feeds extra

**Priority:** P1

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XX — Social posts

[Primary documentation](https://docs.x.com/x-api/getting-started/pricing).

**Fields:** Posts, author IDs, relation/engagement metadata within purchased access

**Access rights:** Paid API and developer terms; no assumption of unrestricted public scraping

**Timestamp contract:** Post creation, first receipt, edit and engagement snapshot times

**Latency history:** Coverage and latency depend on endpoint/credits; archive rights checked

**Candidate use:** Social acceleration and wallet interaction; H18/H21

**Quality confounders:** Bots, reposts, sampling, revised engagement, licensing

**Cost:** Current documented post-read unit $0.005; 100,000 billable posts about $500 before other units

**Priority:** P2

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XTRUTH — Political social source

[Primary documentation](https://help.truthsocial.com/legal/terms-of-service/).

**Fields:** Public statements/posts of relevant accounts if lawfully obtained

**Access rights:** Terms restrict unauthorised automated collection; approved/licensed access required

**Timestamp contract:** Original publication, edits and independently logged first availability

**Latency history:** No unrestricted stable public research API established in this audit

**Candidate use:** Official-person statement stream candidate; H19

**Quality confounders:** Quoted reposts, deletions, account attribution and access restrictions

**Cost:** Unpriced; defer automated collection until authorised source exists

**Priority:** P3

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XREDDIT — Community discussion

[Primary documentation](https://redditinc.com/policies/data-api-terms).

**Fields:** Public discussions/comments through authorised API

**Access rights:** Commercial use and access can require agreement; deletion/retention obligations reviewed

**Timestamp contract:** Created/edited/deleted and receipt times

**Latency history:** Historical completeness/limits require access confirmation

**Candidate use:** Attention/disagreement, lower-priority extension H18/H51

**Quality confounders:** Selection, bots, upvote revisions, community event mismatch

**Cost:** Commercial terms/quote required; no free assumption

**Priority:** P3

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XTRENDS — Search attention

[Primary documentation](https://developers.google.com/search/apis/trends).

**Fields:** Official Trends API alpha for search-interest series

**Access rights:** Early-access application; access not established

**Timestamp contract:** Time bucket, sampling/revision and receipt metadata

**Latency history:** Not assumed minute-level or universally accessible

**Candidate use:** H49; compare open attention alternatives first

**Quality confounders:** Rescaling, sampled history, language/geography, look-ahead aggregate

**Cost:** Availability/cost unconfirmed; no project dependency until admitted

**Priority:** P3

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XWIKI — Open attention proxy

[Primary documentation](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/documentation/getting-started.html).

**Fields:** Pageviews and other Wikimedia aggregate analytics

**Access rights:** Open API; applicable attribution/usage terms checked per dataset

**Timestamp contract:** Aggregation period and first available response

**Latency history:** Appropriate horizon determined by publication lag

**Candidate use:** H50; cheap attention benchmark

**Quality confounders:** Bots, ambiguous entity pages, redirects and aggregation

**Cost:** Public API; processing cost

**Priority:** P2

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## PRTDS — Reference prices and public comments

[Primary documentation](https://docs.polymarket.com/market-data/realtime-data).

**Fields:** Binance/Chainlink crypto; Pyth equities; comments/reactions; public sports/market streams

**Access rights:** Public topics documented; authenticated streams classified separately

**Timestamp contract:** Envelope and payload timestamps, exact decimal strings, SDK/wire version

**Latency history:** Forward stream; reconnect/gap handling needed

**Candidate use:** Rule-aware external lead and comment tests

**Quality confounders:** Relay delay; venue price not identical to oracle outcome

**Cost:** Documented public access; source redistribution terms still matter

**Priority:** P1

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## PTWAP — Resolution reference

[Primary documentation](https://docs.polymarket.com/market-data/chainlink-twap).

**Fields:** 30s/60s Chainlink TWAP via RTDS; direct Data Streams alternative

**Access rights:** RTDS no credentials documented; direct standard/sponsored credentials

**Timestamp contract:** Observation timestamp, window seconds, receipt; preserve fixed-point decimal

**Latency history:** Current updates; historic causal replay not established

**Candidate use:** H44; exact settlement reference mapping

**Quality confounders:** Do not use spot when outcome uses TWAP; cutoff matters

**Cost:** Public relay; direct provider terms/price separate

**Priority:** P1

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XPMXT — Third-party historical archive

[Primary documentation](https://archive.pmxt.dev/).

**Fields:** Public hourly Parquet dump files across prediction venues

**Access rights:** Project advertises CC BY 4.0 archive; verify each release/underlying rights

**Timestamp contract:** Archive publication and actual contained event/receive clocks

**Latency history:** Hourly files do not imply hourly-only sampling; coverage audit needed

**Candidate use:** Historical data-quality and mechanism development

**Quality confounders:** Unknown completeness, schema changes, timestamps, venue mappings

**Cost:** Archive advertised free; compute/download costs

**Priority:** P1

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XOPENMARKET — Research dataset

[Primary documentation](https://github.com/gregyoung14/openmarket).

**Fields:** Synchronised PM/Binance records and benchmark definitions

**Access rights:** Repository/data licences must be checked separately

**Timestamp contract:** Explicit clock alignment data and versioned manifests

**Latency history:** Historical crypto sample, not prospective AREPO data

**Candidate use:** Negative benchmark, synchronisation research; H14/H44

**Quality confounders:** Protocol era, market selection and simulated execution assumptions

**Cost:** Research download/compute; not a production feed

**Priority:** P1

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XCTF — Public blockchain and oracle

[Primary documentation](https://docs.polymarket.com/resources/contracts).

**Fields:** Exchange fills, CTF balances/splits/merges/redemptions, UMA states and contract versions

**Access rights:** Public chain access; RPC/archive provider limits and source-code licence separate

**Timestamp contract:** Block/log/transaction order, receipt/confirmation time and reorg state

**Latency history:** Historical logs available in principle; archival states may cost more

**Candidate use:** Wallet history, mapping, oracle delay and reconciliation

**Quality confounders:** Address != person; match != settlement; v1/v2 decoder mismatch

**Cost:** RPC usage/storage estimate required; no key or paid plan purchased

**Priority:** P1

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.

## XOFFICIAL_DOMAIN — Market-specific source of truth

[Primary documentation](https://docs.polymarket.com/concepts/resolution).

**Fields:** Resolution-rule-linked official websites, election authorities, sports bodies, court/company releases

**Access rights:** Verify each named source and its licence/API separately

**Timestamp contract:** Claim occurrence, official publication, receipt and resolution times

**Latency history:** Coverage varies; not assumed obtainable from one universal API

**Candidate use:** Authoritative event engine and final labels

**Quality confounders:** Rule interpretation, revisions, conflicting authorities and ambiguity

**Cost:** Per-source cost/rights unresolved until a concrete market is selected

**Priority:** P1

**Verification:** Primary documentation inspected 2026-09-19; no production feed started; performance and commercial entitlement not tested.
