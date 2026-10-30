# Data rights matrix for AREPO sources (2026-10-11)

**NOT LEGAL ADVICE.** Independent web research by a subagent, quoting the Polymarket Terms of Use effective 2026-08-11. Needs review by the user or counsel before any public, redistributive or commercial use.

**Lead summary:**
- Private research use is low-risk but technically UNCLEAR. Section 4 bars scraping tools and copying material without consent; the API is documented and public.
- The public website (arepolabs.com) showing Polymarket-derived prices and forecasts is UNCLEAR.
- Redistributing raw data, committing it to the public repo, or a paid product is RESTRICTED without a written agreement. The section 4 "Data" clause reaches derived and on-chain data for "Capital Market Clients" (including "financial technology companies") and "market data distributors".
- The UK is a restricted jurisdiction. Restricted users "are only permitted to use the Content Features" and "may not access the Technology Features"; whether read-only API use counts as a Technology Feature is unresolved.
- The current policy (private research, no raw-data redistribution, code and aggregates only) is consistent with this matrix. The 10 questions below are for the user or counsel.
- **Polymarket-v1 DB** (TimeSeventeen, CC BY 4.0, on-chain v1 fills 2022-11-21 to 2026-04-28, includes fee) is an alternative trades source to vgregoire. Drop `winning_outcome_label` and `resolved_at` at load.
- **OpenMarket** is BTC 15-minute only and not better than pmxt.

## AREPO data-rights research (2026-10-11). This is not legal advice.

**Method.** Web research only. Nothing in the repo was modified. polymarket.com/tos is an iframe that loads a Google Doc (`docs.google.com/document/d/1N4aYlRcqaWCeKMID7vUSWJ1UPMvw_v6SP4cOFN8ZxR4`). I exported that doc as text (60 KB) and quote from it. Small scratch copies are in the session scratchpad only.

### 1. Polymarket.com Terms of Use (Adventure One QSS, Inc.; "Effective as of August 11, 2026")
- **The API is covered.** The terms bind anyone "ACCESSING, INTERACTING WITH OR USING THE SITE … (INCLUDING BY CONNECTING VIA AN API…)" (§1).
- **Scraping (§4, prohibited conduct).** You may not "Use any data mining tools, robots, crawlers, or similar data gathering and extraction tools to scrape or otherwise remove data from the Site, any other Interface, or Features". You also may not "Use any manual process to monitor or copy any of the material … without our prior written consent".
- **Distribution (§4).** You may not "Sublicense, sell, or otherwise distribute the Interfaces or Features, or any portion thereof".
- **Data clause (§4).** This is the most important clause for AREPO. It bars access to "any data … directly or through an API, or any other means, **including on-chain**, whether in raw, derived, aggregated, or anonymized form (the 'Data')" by:
  - a "Capital Market Client", defined to include "financial technology companies" and "index calculation"; or
  - "a market data distributor … unless otherwise agreed to in writing by us".
  
  A further clause bars "Sell, resell, sublicense, redistribute, or otherwise commercially exploit the Data to any Capital Market Client or market data distributor".
- **Carve-out (§4).** "the Company reserves the right to grant access to public on-chain infrastructure and the Company's builder program."
- **Ownership and licence (§5.1).** The Company, Blockratize or its licensors "own all right, title, and interest … in and to the Site … Features, including any related content". You get a "personal, limited, revocable, non-exclusive, non-sublicensable, non-transferable license to use, copy, and distribute in connection with such use". That licence is "solely intended to allow you to access, use or otherwise interact with" the Site.
- **Prices and reliance.** Pricing information "does not represent an offer … or any advice" (§2.1). Content is "for informational purposes only" (§2.2).
- **Rate limits.** The terms allow "transaction limits or rate limits ('Limits')" that the Company may change at its discretion. Polymarket's docs (docs.polymarket.com/api-reference/rate-limits) say limits are Cloudflare-throttled, for example Gamma at 4,000 requests per 10 s overall and /markets at 300 per 10 s. I did not verify the CLOB figures. I found no separate API or market-data licence; the builder program is a trading programme.
- **UK user.** The UK is on the list for which "USE … FOR TRADING IS NOT PERMITTED". The terms also say: "If you are in a Restricted Jurisdiction … you are only permitted to use the Content Features" and "may not access the Technology Features". The geoblock doc lists GB as close-only. Reading data is not explicitly barred, but the API may count as a "Technology Feature".
- **Law.** "the laws of Panama", with arbitration.

### 2. Polymarket US (QCX; ToS effective 2025-09-25)
§5 says: "licensed to you for personal, non-commercial use in connection with your trading … Redistribution, resale, scraping, bulk downloads, and commercialization of derived works are prohibited unless expressly licensed." This is stricter than the offshore terms. AREPO uses offshore data, so this only matters if AREPO ever touches Polymarket US.

### 3. pmxt archive
- **Who runs it.** The `pmxt-dev` GitHub org / pmxt.dev ("CCXT for prediction markets"). The SDK is MIT-licensed. No legal entity is named.
- **Licence.** The v2 data-overview page says "licensed under … CC BY 4.0". I could not reach that page myself today (archive.pmxt.dev refused the connection), so I am relying on the search snippet. The Joseph3222 Hugging Face mirror and archive.pendulumflow.com both state "PMXT's are CC BY 4.0". The collector repo has no licence and states no Polymarket permission.
- **Stopping.** The Joseph3222 card says "the source archive stopped publishing that morning [2026-08-10] and has not resumed". Pendulumflow lists pmxt v2 coverage as 2026-04-13T19 to 2026-08-09T23. I found no announcement and no reason.
- **Caveat.** pmxt can only license rights it holds. Its redistribution may itself be "market data distributor" activity under Polymarket's §4.

### 4. OpenMarket (arXiv 2607.26245; Gregory Young)
- **Licence.** The paper is CC BY 4.0. The Hugging Face dataset `gregyoung14/openmarket-btc-polymarket` is tagged **apache-2.0** and says nothing about upstream terms. Code is at github.com/gregyoung14/openmarket, tag v0.5.2.
- **Size.** 15.3 GB of parquet, 1.64 B rows. The paper reports 727 M deduplicated rows.
- **Scope.** BTC 15-minute up/down markets plus Binance BTC/USDT only.
- **Coverage conflicts.** The paper says 2026-02-12 to 05-15. The dataset card says 2026-03-14 to 07-01, with a gap from Apr 22 to May 12 "with no recoverable archive data". The card also says it is "in archival shutdown".
- **Clocks.** `source_ts_ms` (venue time) plus `ingest_ts_ms` (collector time). Median lag is 16 ms, there is a ±99 ms offset ambiguity, and the card warns "Collector host clocks can drift."
- **Comparison with pmxt.** Not a better general source for AREPO. It covers one market family, and its author reports a null forecasting result. It is useful only for a crypto lead-lag sub-study. pmxt covers the whole universe.

### 5. Polymarket-v1 Database (arXiv 2606.04217; Qin and Yang)
- **Licence.** The paper is CC BY-SA 4.0. The dataset `TimeSeventeen/Polymarket-v1` is CC BY 4.0: "share and adapt … including commercially". It is "not affiliated with or endorsed by Polymarket".
- **Size and coverage.** 1.20 B on-chain fills from 2022-11-21 to 2026-04-28 (CTF v1), about 49–53 GB of parquet.
- **Fields.**
  - OrderFilled (13 fields), including maker, taker, block_timestamp, price and fee.
  - daily_aligned (24 fields), which adds condition_id, neg_risk, category, market_slug, outcome_label, **winning_outcome_label and resolved_at**. These are label-leak columns: drop them at load.
  - CTF event tables.

### 6. Binance
OpenMarket's Binance rows come from live API capture, so the Binance Terms of Use and API terms govern them; I did not obtain those clauses. Binance's own Vision historical datasets are CC BY-NC-SA 4.0. Their terms say "Commercial licensing is strictly excluded" and bar integration into "commercial financial products … paid subscription newsletters". Expect Binance-derived data to be non-commercial at best.

### On-chain vs API-delivered data
- **On-chain data** (Polygon OrderFilled and CTF events) is publicly replicable. Facts and prices are generally not copyrightable. If you read it from your own RPC or indexer without using Polymarket's interfaces, there is arguably no contract with Polymarket. However, Polymarket's Data clause expressly reaches "on-chain" data for Capital Market Clients and market data distributors.
- **API-delivered data** (Gamma/CLOB books, question text, rules, slugs, descriptions) comes through Polymarket's Interfaces under the ToS. The question and rule text may also be copyright content.
- **Mixed datasets.** vgregoire's API-sourced fields (question, slug, timestamps) stay under the ToS, as does the market metadata in Polymarket-v1.

### RIGHTS MATRIX
Key: A = ALLOWED, AA = ALLOWED-WITH-ATTRIBUTION, U = UNCLEAR, R = RESTRICTED.

| Activity | Polymarket API | pmxt | vgregoire (on-chain, CC BY) | trentmkelly (CC BY; API snapshots) | OpenMarket | Polymarket-v1 DB |
|---|---|---|---|---|---|---|
| Private research collection/use | U, low risk (§4 anti-scraping vs documented public API and "Limits"; personal licence §5.1) | AA | AA | AA | A (Apache; Binance non-commercial expected) | AA |
| Long-term raw storage | U (no retention clause; "monitor or copy" needs consent) | AA | AA | AA | A | AA |
| Public derived stats/charts | U (personal licence; Data clause only restricts Capital Market Client / market data distributor recipients) | AA (U upstream) | AA | AA (U upstream) | U (Binance-derived) | AA |
| Public forecasts (own output) | U, lower risk | AA | AA | AA | U | AA |
| Redistribute raw/derived datasets | R (§4 "otherwise distribute … any portion"; becoming a "market data distributor") | U (CC BY yes; Polymarket upstream R) | AA for on-chain columns; U for API metadata | U | U (Binance R-likely) | AA for on-chain; U for metadata |
| Paid product | R without written agreement (operator may be a "financial technology company" / Capital Market Client) | U to R (upstream) | AA on-chain; U metadata | U to R | R-likely (Binance) | AA on-chain; U metadata |
| Raw data committed to public GitHub | R (equals redistribution) | U | AA (on-chain only) | U | U | AA (on-chain only) |

Code, methods and aggregate findings without raw rows are lowest-risk everywhere. The current "private only, no raw redistribution" policy is consistent with this matrix.

### Questions for a human or counsel
1. Does calling Polymarket's documented public REST/WS endpoints count as using "robots, crawlers … to scrape or otherwise remove data" (§4)? Is long-term retention "copy[ing] … material" needing written consent?
2. Is a UK resident's read-only API use a permitted "Content Feature", or a barred "Technology Feature"?
3. Would AREPO (or its operator), as a public site or paid product, be a "financial technology company" (Capital Market Client) or a "market data distributor"? If so, AREPO needs a written agreement with Adventure One QSS. Should one be requested now (integrity@polymarket.com was the only contact found)?
4. Can the Data clause's "including on-chain" bind someone who reads Polygon directly and never accepts the ToS?
5. Is publishing derived statistics, charts or forecasts "distribut[ing] … any portion" of the Features or Data?
6. Does reproducing market question and rule text on arepolabs.com infringe copyright? What would quotation or linking limits look like?
7. Are pmxt's, trentmkelly's and the vgregoire metadata's CC BY grants effective, given the upstream ToS (licensor's title)? Is there exposure from using a source collected in possible breach?
8. Under UK law, does Polymarket or anyone else hold database right in these compilations (Polymarket is a Panama/US entity)? Does Panama governing law plus arbitration change the practical risk?
9. Do Binance's API terms apply to OpenMarket's Binance rows? Its Apache-2.0 tag is likely over-broad.
10. Can anyone confirm pmxt's operator, its terms page (unreachable today), and why it stopped on 2026-08-10?

### Sources
- polymarket.com/tos (Google Doc 1N4aYlRc…)
- docs.polymarket.com/api-reference/geoblock and /rate-limits
- polymarket.us/tos (Google Doc pub 2PACX-1vQ-86JK…)
- archive.pmxt.dev/docs/v2-data-overview (search snippet only)
- huggingface.co/datasets/Joseph3222/polymarket-orderbook
- archive.pendulumflow.com
- github.com/pmxt-dev/pmxt and /polymarket-orderbook-collector
- arxiv.org/abs/2607.26245 and huggingface.co/datasets/gregyoung14/openmarket-btc-polymarket
- arxiv.org/abs/2606.04217 and huggingface.co/datasets/TimeSeventeen/Polymarket-v1
- data.binance.vision/Binance_Vision-Terms_of_Use.pdf
- Earlier repo notes: docs/research/2026-10-11-historical-data/HANDOFF.md and report_b_sources.md

Not legal advice. Have counsel review before any public, redistributive or commercial use.

---
**Provenance of the quoted terms.** The text was exported 2026-10-11 from the Google Doc behind polymarket.com/tos ("Effective as of August 11, 2026"), sha256 `0506de1ebf824b1827dfef90828f0e78f45d9defa63241ac91f1ed2c0ee2847d`. Polymarket US ToS export sha256 `dbda1fa6d8e4c1af037003f16348cc2cc13ff85038463e5df347266601724c52`. Neither text is committed: it is third-party copyright and this repo is public. Re-export and compare the hash before relying on any quote.
