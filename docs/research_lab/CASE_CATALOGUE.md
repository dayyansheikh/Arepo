# Case catalogue: reported unusual pre-news trading (held-out set)

**Status:** EXPLORATORY_HISTORICAL, `evidence_role: exploratory_historical`. Every case here is *reported*
unusual pre-news trading taken from public reporting. Nothing in this catalogue is evidence or proof of
insider activity, and AREPO makes no such claim. No private individual is named and no wallet address is
recorded.

Role: HELD-OUT evaluation set for the frozen unusual-flow detector (`UNUSUAL_FLOW_PROGRAMME.md` section 2
and 6). Maduro is the only tuning case and is excluded here. These cases are never used to change the
detector.

## Case-list hash (pinned before reading `UNUSUAL_FLOW_DETECTOR.md`)

`sha256("\n".join(sorted(condition_ids)))` over the 16 markets below:

**`6cea3fc56a1df06abd91da4a0d8fd20b1ba6c983f689dbe08b66999be02e8ebc`**

Pinned 2026-10-12 (commit `8a22818`) by the catalogue agent, which had not opened `UNUSUAL_FLOW_DETECTOR.md`
at that commit. Ordering note: detector batch 1 (`fb593ef`) was committed 72 s before this pin; its author
never saw the case list (the list was not in the repository before `8a22818`). Batch 2 and the FINAL FREEZE
(`692ab61`) came after the pin. Nobel 2026 (`637072`) is in the pinned list but has no panel rows (19 trades). Any case added later goes to the `post_freeze` bucket and is reported separately.

| case_id | market_id | condition_id | slug (truncated) |
|---|---|---|---|
| `nobel_peace_2025` | 560868 | `0x14a3dfeba8b22a32feb0f10763db68bc4d2abeb5bff90e9ae20de53793b35a1d` | `will-mara-corina-machado-win-the-nobel-peace-prize-in-2025` |
| `israel_strikes_iran_jun2025` | 551651 | `0x7f39808829da93cfd189807f13f6d86a0e604835e6f9482d8094fac46b3abaac` | `israel-military-action-against-iran-by-friday-477` |
| `israel_strikes_iran_jun2025` | 532742 | `0xd25ff3223a2233f6cd96a349455ca3237931c64358792f90c5f02d8cc39be38d` | `israel-military-action-against-iran-before-july` |
| `google_year_in_search_2025` | 635246 | `0xea17b1284d10617a57f910b2ea63bdef481b1724a4b899d454ff104bea67b657` | `will-d4vd-be-the-1-searched-person-on-google-this-year` |
| `google_year_in_search_2025` | 635230 | `0xb9b05c3a14c6a7c1c6c00a8c214ed154d4232a885f98ebfd01889204ed252931` | `will-pope-leo-xiv-be-the-1-searched-person-on-google-this-year` |
| `us_strikes_iran_feb2026` | 1198423 | `0x3488f31e6449f9803f99a8b5dd232c7ad883637f1c86e6953305a2ef19c77f20` | `us-strikes-iran-by-february-28-2026-227-967-547-688-589-491-592-418-45` |
| `us_strikes_iran_feb2026` | 1198479 | `0xdc4b9ecbfac2c8e98fe18b35c4578a3c64e34ddfe16b1cf8a98ab3ad9d06c088` | `will-us-or-israel-strike-iran-by-february-28-2026-766` |
| `khamenei_out_feb2026` | 916732 | `0x70909f0ba8256a89c301da58812ae47203df54957a07c7f8b10235e877ad63c2` | `khamenei-out-as-supreme-leader-of-iran-by-march-31` |
| `us_iran_ceasefire_apr2026` | 1706788 | `0x4c5701bcde0b8fb7d7f48c8e9d20245a6caa58c61a77f981fad98f2bfa0b1bc7` | `us-x-iran-ceasefire-by-april-7` |
| `us_iran_ceasefire_apr2026` | 1569627 | `0x773abaa5fe55e5cde51a261f444b7921652a4e059ead6b3be9fe56499c2d4609` | `us-x-iran-ceasefire-by-april-15` |
| `axiom_zachxbt_feb2026` | 1419011 | `0x804bc34275d7d610dea3293c06105e925ebfcd6e454813aa27d59a882d50e86d` | `will-axiom-be-accused-of-insider-trading` |
| `openai_model_dec2025` | 822860 | `0x4df1db0ea210284e2d79a237b9a50f62ca905d60cb05c6f763e94f3b0055d15e` | `will-openai-release-a-new-frontier-model-by-december-13-683` |
| `openai_model_dec2025` | 897817 | `0x4edfcf9fd9889864290d34f1902ef51420989e5922b8208bf46bc0689ce6adbe` | `will-openai-release-a-new-frontier-model-on-december-11` |
| `taylor_swift_engagement_aug2025` | 516906 | `0x89ac32e18929185f5bd0dc00e70337571f546e64ae5cd16dceb6026ac2679c1e` | `taylor-swift-and-travis-kelce-engaged-in-2025` |
| `pope_leo_may2025` | 525015 | `0x14197a2979391a7bb1e6918582334640f309c22c7718f824c9fa1e149302662f` | `will-robert-francis-prevost-be-the-next-pope` |
| `nobel_peace_2026` | 637072 | `0x9d010461e21b5f1cf40cb88ec75b84c326873ae1f1df91a031ff4fd5dfee9423` | `will-navi-pillay-win-the-nobel-peace-prize-in-2026` |

Machine-readable registry (events, news times, credibility status, sources):
`docs/research_lab/case_catalogue_registry.json` (written by `backend/scripts/case_catalogue_registry.py`).

## 1. What this catalogue is and is not

- **Is:** a list of public reports of *reported unusual pre-news trading* on prediction markets, with the
  Polymarket market ids, the public trade and price data for 14 days before to 1 day after the news, and a
  held-out run of the five frozen unusual-flow variants on those markets plus quiet-case controls.
- **Is not:** evidence or proof of insider activity, of who traded, or of why. Nothing here labels any
  wallet or person. Wallets exist only as keyed HMAC hashes (`wallet_sidecar`), addresses were held in
  memory for the `/activity` first-trade lookup and never written. Individuals named in the press
  (defendants, traders, employees) are deliberately not named here.
- **Selection and reporting bias (verbatim from `UNUSUAL_FLOW_PROGRAMME.md` section 6):** "Reported cases
  are selected on the outcome (a large move happened), on conspicuousness (someone noticed the flow) and on
  salience (politics, geopolitics, celebrity). Any metric conditioned on them is inflated." Cases are found
  *because someone won* and because a journalist or analyst noticed; flow that was unusual but not followed
  by a win, or a win that nobody wrote about, never enters this list. Case recall is therefore not a
  detection rate, no precision or base rate is computed from it, and no lift is claimed.

## 2. Credibility scale

| status | meaning |
|---|---|
| `charged` | a prosecutor or court document alleges misuse of non-public information (allegation, untested) |
| `official_probe` | the information owner or an authority opened an inquiry; no finding published |
| `alleged` | named on-chain analysts or major outlets describe the pattern as suspected insider activity |
| `speculative` | social-media or minor-outlet speculation; reporting itself notes the evidence is thin |
| `public_or_luck` | contrast case: a long-shot win attributed in reporting to luck or a public-information miss |
| `no_report` | contrast case: comparable market, no report of unusual pre-news activity |

## 3. Cases (Polymarket, with data)

| case_id | domain | event and news time (UTC) | what was reported (no names, no addresses) | status | sources |
|---|---|---|---|---|---|
| `nobel_peace_2025` | awards | 2025 Nobel Peace Prize to M. C. Machado; announced 2025-10-10 09:00 (11:00 Oslo) | Accounts opened shortly before, with no prior history, bought the eventual winner at single-digit odds in the ~11 h before the announcement; price reported moving from ~4% to ~73%; two or three accounts made ~$90k combined. Nobel Institute opened a leak review | official_probe | [Bloomberg](https://www.bloomberg.com/news/articles/2025-10-10/unusual-bets-on-nobel-peace-prize-winner-prompt-probe-into-leaks), [The Block](https://www.theblock.co/post/374199/officials-probe-polymarket-over-suspicious-trades-predicting-nobel-peace-prize-winner-reports), [Decrypt](https://decrypt.co/343840/nobel-peace-prize-organizers-intestigating-polymarket-insider-trades), [Protos](https://protos.com/polymarket-traders-accused-of-insider-trading-nobel-peace-prize/), [Cointelegraph](https://cointelegraph.com/news/nobel-peace-prize-polymarket-investigation) |
| `israel_strikes_iran_jun2025` | war / geopolitics | Israel's opening strikes on Iran, 2025-06-13 ~00:00 (±1 h) | An Israeli indictment (Feb 2026) alleges a reservist passed strike-timing information to a civilian who bet on Polymarket; ~$150-163k won (figures differ). Exact markets and trade times are under court restriction; the two markets here are the obvious candidates, not confirmed ones | charged | [Times of Israel](https://www.timesofisrael.com/israeli-air-force-major-charged-with-using-classified-info-to-place-bets-on-polymarket/), [The Block](https://www.theblock.co/post/389575/israeli-defense-reservist-civilian-indicted-over-alleged-insider-betting-on-polymarket-reports), [JNS](https://www.jns.org/israelis-indicted-on-charges-of-gambling-using-classified-information/) |
| `google_year_in_search_2025` | search rankings | Google 2025 Year in Search published 2025-12-04 (registry time 05:00, ±6 h; the d4vd market jumped 0.38 → 0.92 at ~03:12, see section 5) | One account won ~$1M across Year-in-Search markets (22 of 23 calls), incl. a 0.2% long shot (d4vd #1 person) and "No" on favourites (e.g. Pope Leo XIV); US federal charges (May 2026) allege use of confidential company data | charged | [The Defiant](https://thedefiant.io/news/defi/polymarket-users-suspect-insider-trading-after-google-trend-markets-crown-surprise-winner), [Crypto Economy](https://crypto-economy.com/insider-trading-fears-emerge-after-1m-polymarket-win-on-google-search-activity/), [Android Authority](https://androidauthority.com/google-employee-accused-of-insider-trading-3672044/), [Euronews](https://de.euronews.com/2026/05/28/google-ingenieur-wegen-angeblichen-polymarket-insiderhandels-uber-12-mio-dollar-angeklagt) |
| `us_strikes_iran_feb2026` | war / geopolitics | US-Israeli strikes on Iran, 2026-02-28 ~06:15 (±2 h) | Bubblemaps: six wallets created in February, mostly funded within 24 h, bought "US strikes Iran by Feb 28" hours before the strikes; ~$1.0-1.2M combined profit (estimates differ) | alleged | [The Block](https://www.theblock.co/post/391650/fresh-accounts-netted-1-million-on-polymarket-hours-before-us-airstrikes-on-iran-bubblemaps), [Forbes](https://www.forbes.com/sites/boazsobrado/2026/03/02/fresh-wallets-made-12m-on-polymarket-hours-before-iran-airstrikes/), [Cointelegraph/Bubblemaps](https://cointelegraph.com/news/bubblemaps-polymarket-cluster-win-military-bets), [Al Jazeera](https://aljazeera.com/news/2026/3/25/large-polymarket-wall-street-bets-on-trumps-war-news-under-scrutiny) |
| `khamenei_out_feb2026` | war / geopolitics | Strike that killed Iran's Supreme Leader, first news 2026-02-28 ~06:15 (±3 h); death confirmed later | One account reportedly made ~$553k on Khamenei markets with a trade ~71 min before news of the initial strike; Polysights flagged new-wallet "Khamenei out" buying in mid-January; resolution disputed | alleged | [NPR/KJZZ](https://www.kjzz.org/npr-top-stories/2026-03-01/prediction-market-trader-magamyman-made-553-000-on-death-of-irans-supreme-leader), [Bloomberg Law](https://news.bgov.com/securities-law/polymarket-bettors-in-limbo-as-khameneis-time-of-death-debated), [Business Today](https://www.businesstoday.in/latest/trends/story/500-million-betting-frenzy-crypto-bets-on-khameneis-fate-puts-trump-linked-polymarket-under-lens-518841-2026-03-02) |
| `us_iran_ceasefire_apr2026` | war / geopolitics | US-Iran two-week ceasefire posted 2026-04-07 ~22:30 (±2 h) | AP/Dune: at least 50 wallets made their first-ever Polymarket trades as sizeable "Yes" bets before the post; one wallet created that morning bought ~$72k at ~8.8c. Market later marked disputed; a US senator demanded answers | alleged | [AP via WTOP](https://wtop.com/national/2026/04/newly-created-polymarket-accounts-bet-big-on-us-iran-ceasefire-in-hours-before-trumps-announcement/), [Senate office](https://www.blumenthal.senate.gov/newsroom/press/release/blumenthal-demands-answers-from-polymarket-following-suspicious-bets-on-ceasefire), [NPR/KUOW](https://www.kuow.org/stories/well-timed-bets-on-polymarket-tied-to-the-iran-war-draw-calls-for-investigations-from-lawmakers) |
| `axiom_zachxbt_feb2026` | corporate / crypto | An on-chain investigator's exposé names Axiom, 2026-02-26 ~13:00 (±1 h; the release-hour market resolved 8-9 am, ET assumed) | ~$40M market on which company would be exposed; at least 12 wallets, several fresh, bought the eventual answer at low odds (one at ~13.8%); ~$1M+ combined profit | alleged | [CoinDesk](https://www.coindesk.com/markets/2026/02/27/polymarket-bettors-appear-to-have-insider-traded-on-a-market-designed-to-catch-insider-traders), [Cointelegraph](https://cointelegraph.com/news/suspected-insider-1-2m-zachxbt-axiom-expose), [Decrypt](https://decrypt.co/359223/y-combinator-backed-axiom-employees-accused-insider-trading-zachxbt) |
| `openai_model_dec2025` | corporate / tech | GPT-5.2 release, 2025-12-11 ~18:00 (±6 h) | Several accounts bought "new frontier model by Dec 13" in the week before; four accounts gained ~$13k combined. Small; no insider link confirmed; the market priced a release days earlier (public expectation) | speculative | [Tiger Brokers news](https://www.itiger.com/news/1128153844), [Yahoo Finance](https://finance.yahoo.com/news/one-polymarket-user-made-more-164427975.html) |
| `taylor_swift_engagement_aug2025` | entertainment | Swift-Kelce engagement post, 2025-08-26 ~16:00 (±3 h) | A small account bought "Yes" within ~15 h of the post (~$2k stake, ~$3k profit) and reportedly moved the price ~25% → ~45%; identity speculation unconfirmed, a fact-check called the leak claim speculative | speculative | [AOL](https://www.aol.com/polymarket-trader-made-50k-betting-174743223.html), [BeInCrypto](https://beincrypto.com/taylor-swift-polymarket-engagement-guitarist/), [CasinoBeats](https://casinobeats.com/2025/08/28/taylor-swift-engagement-foretold-by-prediction-market-price-changes-on-polymarket-kalshi/) |
| `pope_leo_may2025` | announcements | Cardinal Prevost elected, white smoke 2025-05-08 16:07 | Contrast: a 1-2% long shot; one account turned ~$1k into ~$64k. Reported as a market miss; the conclave is sealed | public_or_luck | [CNN](https://edition.cnn.com/2025/05/09/business/online-betting-markets-failed-pope), [CNBC via NBC](https://www.nbcdfw.com/news/business/money-report/online-bettors-spent-over-40-million-gambling-on-the-identity-of-the-next-pope-one-winner-made-52000-on-a-longshot/3837659/) |
| `nobel_peace_2026` | awards | 2026 Nobel Peace Prize, 2026-10-09 09:00 | Contrast: same market family as 2025, no reported unusual activity (only a sponsored piece calling it ordinary). The winner's market had 19 trades in the window | no_report | [TIME partner content (sponsored)](https://time.com/partner-content/prediction-markets/nobel-peace-prize-betting-surges-after-last-years-suspected-breach/) |

## 4. Reported cases kept out of the data (and why)

| item | venue | what was reported | why no data here |
|---|---|---|---|
| Maduro removal / capture (Jan 2026) | Polymarket | New wallets bet on Maduro's removal hours before his capture; a US soldier was later charged | Detector **tuning** case (`CASE_STUDY_MADURO.md`); excluded from every held-out table |
| Video editor on a large YouTube channel (Feb 2026) | Kalshi | Kalshi fined and suspended an editor for statistically anomalous trading on the channel's markets, and reported it to the CFTC ([NPR](https://www.npr.org/2026/02/25/nx-s1-5726050/kalshi-insider-trading-enforcement-actions), [Axios](https://axios.com/2026/02/25/kalshi-insider-trading-suspension)) | Kalshi: no public per-trade wallet data. Confirmed platform enforcement |
| Candidate betting on his own race (Feb 2026) | Kalshi | Kalshi banned a former candidate who bet ~$200 on himself ([The Block](https://www.theblock.co/post/391287/mrbeast-editor-and-former-california-24-year-old-gubernatorial-candidate-fined-by-kalshi-for-insider-trading)) | Kalshi; trivial size |
| Gemini 3 Flash release date (Dec 2025) | Polymarket | Same account as the Year-in-Search case reportedly won ~$150k on an early release | Market not resolved to an id within the session; speculative; same-actor duplicate of a charged case |
| Nine-account military cluster; ACDC "Orcas" (152 wallets, ~$8M) | Polymarket | Aggregate on-chain studies of military markets ([Reuters via Al-Monitor](https://al-monitor.com/originals/2026/08/exclusive-more-150-polymarket-wallets-may-have-traded-military-secrets-research), [ACDC](https://acdatacollective.org/?p=1688)) | Aggregate studies, not single events; their headline markets (Feb 28 strikes, Khamenei, ceasefire) are already cases above |
| Bloomberg review of ~34,000 Polysights flags (Aug 2025-Jun 2026) | Polymarket | 57% of flagged wallets <24 h old; ~$200M flagged volume in H1 2026; Polymarket referred ~100 wallets | Aggregate; context for base rates only |
| 2024 US election "French whale" | Polymarket | ~$80M won on Trump; the trader said he relied on commissioned "neighbour" polls ([CBS](https://www.cbsnews.com/news/french-whale-made-over-80-million-on-polymarket-betting-on-trump-election-win-60-minutes/), [The Block](https://www.theblock.co/post/324996/french-polymarket-whale-us-election-profit-france-ban)) | Contrast (private research, not a pre-news event); months-long position, no news time |
| OpenAI browser launch (Oct 2025) | Polymarket | One unverified claim of new wallets betting before launch | Could not verify a primary source; not catalogued |

## 5. Data (Part 2)

Under `data-dumps/research_lab/case_studies/<case_id>/` (not in git; 15 MB total, cap 1 GB): `prices_<id>.csv.gz`
(CLOB prices-history, token 0, 10-min fidelity), `trades_<id>.csv.gz` (**every** Data API taker trade in
[news-14d, news+1d], paged with the `start`/`end` window that `/trades` honours, via
`event_study.fetch_trades_full`; 0 incomplete windows in every market, so coverage is complete),
`manifest.json`, `controls.json` + `controls/`; shared `first_trade_cache.jsonl` (causal `/activity` first
Polymarket trade per wallet hash, end = the wallet's first trade in the market; up to 1,500 wallets per case
market by pre-news notional, 200 per control market). Pulled 2026-10-12, ~16k + control requests at ≤ 4 req/s,
always yielding to `arepo_pass.sh`. Code: `backend/astrolabe/research_lab/case_catalogue.py`, runner
`backend/scripts/run_case_catalogue.py` (`pull`, `controls`, `panel`, `timeline`, `evaluate`), tests
`backend/tests/unit/test_research_lab_case_catalogue.py`. Every output carries `evidence_role:
exploratory_historical`; trials are logged in `trials.jsonl` (kinds `history_case_timeline` x11,
`history_case_controls`, `detector_eval` x5 with dataset `case_catalogue:case_panel`).

**News-time caveats.** News times were fixed in the registry before any data were read. Two are weak: the
Year-in-Search publication time (registry 05:00 ±6 h; the d4vd market jumped 0.38 → 0.92 at about 03:12, so the
public release was probably ~2 h earlier) and the OpenAI release (the "by Dec 13" market was ≥ 0.9 about 60 h
before the launch: a release was publicly expected). Re-anchoring every case at min(registry time, first
token-0 price ≥ 0.9) leaves every detector result below unchanged (all pre-news alerts are 36-52 h early).
For the Israel case the markets are plausible candidates; the indictment does not name them.

## 6. Descriptive per-case timelines (not the detector)

Rule `unusual-desc-v1` (declared in `case_catalogue.UNUSUAL_RULE` before any case was scored): an hour is
unusual if its notional has robust z ≥ 4 against the market's own previous 168 hours **and** one of new-wallet
notional z ≥ 4, single trade ≥ 50% of trailing-24h notional, or top wallet ≥ 50% of the hour. "Background" is
the same rule's flag rate over [news-14d, news-72h); the binomial p asks how surprising the pre-news count is
given that rate (hours are not independent, so p is descriptive). In thin markets single small trades flag,
so the *first* flag is often early noise; the *largest* pre-news hour is the more informative column.

| case | market (id) | trades in window | background: flag rate (hours scored) | flagged pre-news hours vs expected (binomial p) | first flag: lead h, price | largest pre-news hour: lead h, USDC, price | price 1h pre-news → news+6h | market first ≥ 0.9, h vs news |
|---|---|---|---|---|---|---|---|---|
| `nobel_peace_2025` | Will María Corina Machado win the Nobel Peace Prize in  (560868) | 3599 | 0.060 (216) | 18/72 vs 4.3 (p=2e-07) | 71.0, 0.007 | 11.0, 32668, 0.108 | 0.673 → 1.000 | 0.2 |
| `israel_strikes_iran_jun2025` | Israel military action against Iran by Friday? (551651) | 2146 | 0.000 (216) | 24/72 vs 0.0 (p=0) | 28.0, 0.075 | 27.0, 12377, 0.245 | 0.310 → 1.000 | 0.2 |
| `israel_strikes_iran_jun2025` | Israel military action against Iran before July? (532742) | 4807 | 0.079 (216) | 19/72 vs 5.7 (p=2e-06) | 62.0, 0.230 | 30.0, 58581, 0.460 | 0.630 → 1.000 | 0.0 |
| `google_year_in_search_2025` | Will d4vd be the #1 searched person on Google this year (635246) | 5257 | 0.153 (216) | 15/72 vs 11.0 (p=0.1) | 56.0, 0.095 | 2.0, 537595, 0.997 | 0.985 → 0.998 | -1.7 |
| `google_year_in_search_2025` | Will Pope Leo XIV be the #1 searched person on Google t (635230) | 6603 | 0.074 (216) | 8/72 vs 5.3 (p=0.2) | 56.0, 0.485 | 2.0, 1091714, 0.003 | 0.004 → 0.001 | – |
| `us_strikes_iran_feb2026` | US strikes Iran by February 28, 2026? (1198423) | 60802 | 0.023 (216) | 5/71 vs 1.6 (p=0.02) | 36.2, 0.095 | 3.2, 737997, 0.135 | 0.225 → 1.000 | 0.8 |
| `us_strikes_iran_feb2026` | Will US or Israel strike Iran by February 28, 2026? (1198479) | 8928 | 0.051 (216) | 7/71 vs 3.6 (p=0.07) | 52.2, 0.105 | 13.2, 55827, 0.175 | 0.260 → 1.000 | 0.3 |
| `khamenei_out_feb2026` | Khamenei out as Supreme Leader of Iran by March 31? (916732) | 38306 | 0.042 (216) | 3/71 vs 3.0 (p=0.6) | 46.2, 0.175 | 12.2, 114362, 0.195 | 0.255 → 0.755 | 13.4 |
| `us_iran_ceasefire_apr2026` | US x Iran ceasefire by April 7? (1706788) | 54734 | 0.065 (216) | 8/71 vs 4.6 (p=0.09) | 63.5, 0.009 | 1.5, 883920, 0.281 | 0.281 → 0.997 | 0.7 |
| `us_iran_ceasefire_apr2026` | US x Iran ceasefire by April 15? (1569627) | 33105 | 0.042 (216) | 2/71 vs 3.0 (p=0.8) | 2.5, 0.335 | 1.5, 333916, 0.560 | 0.560 → 0.998 | 0.7 |
| `axiom_zachxbt_feb2026` | Will Axiom be accused of insider trading? (1419011) | 12556 | 0.000 (216) | 43/72 vs 0.0 (p=0) | 68.0, 0.450 | 67.0, 1189, 0.065 | 0.275 → 1.000 | 0.8 |
| `openai_model_dec2025` | Will OpenAI release a new frontier model by December 13 (822860) | 3663 | 0.153 (216) | 10/72 vs 11.0 (p=0.7) | 72.0, 0.755 | 67.0, 10026, 0.755 | 0.963 → 1.000 | -60.0 |
| `openai_model_dec2025` | Will OpenAI release a new frontier model on December 11 (897817) | 4379 | 0.000 (216) | 49/72 vs 0.0 (p=0) | 65.0, 0.115 | 55.0, 820, 0.465 | 0.915 → 0.999 | -13.5 |
| `taylor_swift_engagement_aug2025` | Taylor Swift and Travis Kelce engaged in 2025? (516906) | 163 | 0.023 (216) | 7/72 vs 1.7 (p=0.001) | 23.0, 0.245 | 21.0, 549, 0.350 | 0.415 → 1.000 | 1.2 |
| `pope_leo_may2025` | Will Robert Francis Prevost be the next pope? (525015) | 5709 | 0.042 (216) | 17/71 vs 3.0 (p=4e-09) | 71.1, 0.015 | 25.1, 2414, 0.021 | 0.018 → 1.000 | 1.2 |
| `nobel_peace_2026` | Will Navi Pillay win the Nobel Peace Prize in 2026? (637072) | 19 | 0.000 (216) | 0/72 vs 0.0 (p=1) | –, – | 72.0, 0, – | – → – | 0.5 |

Reading the timelines:
- **Nobel 2025:** the clearest case. Thin market (price ~1%) until the hour 11 h before the announcement, when
  k traded and the price went 0.02 → 0.11; the next 10 hours carried -150k per hour and the price sat at
  ~0.67-0.70 before the announcement. Pre-news flagged hours 18 vs 4.3 expected.
- **Israel strikes (Jun 2025):** the "before July" market had heavy flow and prices 0.46-0.63 for 30 h before
  the strikes, in a period of public escalation; the "by Friday" market was created ~1.3 days earlier.
- **Year in Search:** the d4vd market rose from ~0.05 at news-72h to ~0.09-0.38 over the following days, then
  jumped at ~03:12 on 4 Dec (probable publication); the largest hours are the publication itself.
- **Feb 2026 strikes / Khamenei / Apr 2026 ceasefire:** very liquid markets (/bin/zsh.7-0.9M in the largest hour);
  flow before news is large in absolute terms but only mildly unusual against these markets' own busy
  baselines (flagged hours close to expectation), which is where per-wallet analyses (fresh wallets) found
  their signal, not in market-level totals.
- **Axiom:** the market price drifted from ~0.07 to ~0.27 over the last three days with many flagged hours
  (background rate 0 because the market is young; the expected count is not informative).
- **Taylor Swift:** tiny market; a few hundred dollars per hour from 23 h before the post moved the price 0.24 →
  0.41, matching the reported ~25% → ~45% move.
- **Pope (contrast):** 17 flagged hours vs 3 expected in a very thin long-shot market: the descriptive rule
  also fires on a case reported as luck, a reminder that it measures unusual *activity*, not information.

## 7. Held-out detector evaluation (Part 3)

Five frozen variants (`FROZEN.json`, FINAL FREEZE `692ab61`), engine `detector-eval-v1`, run once each through
`HeldOutHarness().evaluate(rule_id, case_panel, evidence_role="exploratory_historical",
dataset="case_catalogue:case_panel", cfg=EvalConfig(case_mode=True))`. Precision and base rates are refused
by design. Panel: `case_studies/case_panel.csv.gz` (sha256 `154e7fc6...f5af52`), 4,048 rows on the 2 h grid,
44 markets (15 case markets in 10 cases, 19 quiet_move, 10 quiet_nomove), built with
`history_backfill.origin_frame`/`attach_labels` and `detector_eval.normalise_panel(df, "history")`.
`new_wallet_share_l` uses first-seen = min(first appearance in the panel's own trades, `/activity` first
trade for the top-200 pre-tau-notional wallets of every market, cases and controls alike).

**Quiet-case controls** (`case_catalogue.CONTROL_RULE`, `case-controls-v1`, declared before any alert):
same fee category and lifetime-volume band, closing within ±15 d, same price band at tau-72h, seeded hash
order, no relaxation. Large shortfall: 29 of the 110 intended controls. Most candidates are short-lived
markets with no price 72 h before tau, and two cases (Israel, Axiom) have no defined price band because their
market did not exist 72 h before the news.

| case | case band (p at news-72h) | category / liquidity band | pool | examined | quiet_move | quiet_nomove | main rejection reasons |
|---|---|---|---|---|---|---|---|
| `nobel_peace_2025` | 3 (0.007) | unknown / vol_ge_1e5 | 2440 | 120 | 0 | 5 | no price at tau-72h: 86, price band mismatch: 26, same event as a chosen control: 3 |
| `israel_strikes_iran_jun2025` | None (–) | unknown / vol_ge_1e5 | 1173 | 120 | 0 | 0 | no price at tau-72h: 81, price band mismatch: 39 |
| `google_year_in_search_2025` | 3 (0.05) | unknown / vol_ge_1e5 | 4357 | 120 | 2 | 4 | no price at tau-72h: 97, price band mismatch: 17, same event as a chosen control: 1 |
| `us_strikes_iran_feb2026` | 2 (0.105) | unknown / vol_ge_1e5 | 3353 | 120 | 5 | 2 | no price at tau-72h: 83, price band mismatch: 27 |
| `khamenei_out_feb2026` | 2 (0.185) | unknown / vol_ge_1e5 | 3346 | 120 | 3 | 0 | no price at tau-72h: 88, price band mismatch: 29 |
| `us_iran_ceasefire_apr2026` | 3 (0.013) | unknown / vol_ge_1e5 | 1457 | 120 | 0 | 5 | no price at tau-72h: 50, price band mismatch: 43, same event as a chosen control: 10 |
| `axiom_zachxbt_feb2026` | None (–) | unknown / vol_ge_1e5 | 3651 | 120 | 0 | 0 | no price at tau-72h: 91, price band mismatch: 29 |
| `openai_model_dec2025` | 2 (0.815) | unknown / vol_ge_1e5 | 4597 | 120 | 2 | 0 | no price at tau-72h: 104, price band mismatch: 14 |
| `taylor_swift_engagement_aug2025` | 2 (0.24) | unknown / vol_ge_1e5 | 1483 | 120 | 3 | 0 | no price at tau-72h: 97, price band mismatch: 20, same event as a chosen control: 1 |
| `pope_leo_may2025` | 3 (0.015) | unknown / vol_ge_1e5 | 1035 | 92 | 5 | 5 | no price at tau-72h: 43, price band mismatch: 16, same event as a chosen control: 2 |
| `nobel_peace_2026` | None (–) | culture / vol_1e4_1e5 | 27 | 27 | 0 | 0 | no price at tau-72h: 21, price band mismatch: 6 |

**Per variant** (alert = top 1% of alertable rows of the whole case panel, as declared):

| case | market | resolved token-0 price | price news+6h | convex_longshot | imb_burst | large_trade | new_wallet_conc | pressure_no_resp |
|---|---|---|---|---|---|---|---|---|
| `nobel_peace_2025` | Will María Corina Machado win the Nobel Peace Prize in  (560868) | 1 | 0.9995 | – | – | – | – | – |
| `israel_strikes_iran_jun2025` | Israel military action against Iran by Friday? (551651) | 1 | 0.9995 | – | – | – | – | – |
| `israel_strikes_iran_jun2025` | Israel military action against Iran before July? (532742) | 1 | 0.9995 | – | – | – | – | – |
| `google_year_in_search_2025` | Will d4vd be the #1 searched person on Google this year (635246) | 1 | 0.9975 | alert outside [news-72h, news) | – | **fired** lead 45.0 h at 0.090 (with outcome) | – | – |
| `google_year_in_search_2025` | Will Pope Leo XIV be the #1 searched person on Google t (635230) | 0 | 0.001 | – | – | **fired** lead 39.0 h at 0.500 (against outcome) | alert outside [news-72h, news) | – |
| `us_strikes_iran_feb2026` | US strikes Iran by February 28, 2026? (1198423) | 1 | 0.9995 | – | – | alert outside [news-72h, news) | – | – |
| `us_strikes_iran_feb2026` | Will US or Israel strike Iran by February 28, 2026? (1198479) | 1 | 0.9995 | **fired** lead 36.2 h at 0.135 (with outcome) | – | **fired** lead 36.2 h at 0.135 (with outcome) | – | – |
| `khamenei_out_feb2026` | Khamenei out as Supreme Leader of Iran by March 31? (916732) | 1 | 0.755 | **fired** lead 52.2 h at 0.185 (with outcome) | – | **fired** lead 52.2 h at 0.185 (with outcome) | alert outside [news-72h, news) | – |
| `us_iran_ceasefire_apr2026` | US x Iran ceasefire by April 7? (1706788) | 1 | 0.9965 | – | – | alert outside [news-72h, news) | – | – |
| `us_iran_ceasefire_apr2026` | US x Iran ceasefire by April 15? (1569627) | 1 | 0.9975 | – | – | alert outside [news-72h, news) | – | – |
| `axiom_zachxbt_feb2026` | Will Axiom be accused of insider trading? (1419011) | 1 | 0.9995 | – | – | – | – | – |
| `openai_model_dec2025` | Will OpenAI release a new frontier model by December 13 (822860) | 1 | 0.9995 | – | – | – | – | – |
| `openai_model_dec2025` | Will OpenAI release a new frontier model on December 11 (897817) | 1 | 0.9985 | – | – | – | – | – |
| `taylor_swift_engagement_aug2025` | Taylor Swift and Travis Kelce engaged in 2025? (516906) | 1 | 0.9995 | – | **fired** lead 46.0 h at 0.240 (with outcome) | – | – | – |
| `pope_leo_may2025` | Will Robert Francis Prevost be the next pope? (525015) | 1 | 0.9995 | – | – | – | – | – |
| `nobel_peace_2026` | Will Navi Pillay win the Nobel Peace Prize in 2026? (637072) | 1 | None | no rows | no rows | no rows | no rows | no rows |

| variant | alertable rows | alert rows (top 1%) | case markets alerted pre-news (72 h) | cases (of 10 with rows) alerted pre-news | lead h (min/median/max) | any-alert rate: case | quiet_move | quiet_nomove |
|---|---|---|---|---|---|---|---|---|
| `uf_convex_longshot_v1` | 817 | 8 | 2/15 | 2 (khamenei_out_feb2026, us_strikes_iran_feb2026) | 36.2 / 44.2 / 52.2 | 3/15 | 3/19 | 0/10 |
| `uf_imbalance_burst_v1` | 2292 | 22 | 1/15 | 1 (taylor_swift_engagement_aug2025) | 46.0 / 46.0 / 46.0 | 1/15 | 11/19 | 1/10 |
| `uf_large_trade_v1` | 2856 | 28 | 4/15 | 3 (google_year_in_search_2025, khamenei_out_feb2026, us_strikes_iran_feb2026) | 36.2 / 42.0 / 52.2 | 7/15 | 1/19 | 1/10 |
| `uf_new_wallet_concentration_v1` | 2292 | 22 | 0/15 | 0 (none) | – | 2/15 | 2/19 | 3/10 |
| `uf_pressure_no_response_v1` | 2292 | 22 | 0/15 | 0 (none) | – | 0/15 | 9/19 | 2/10 |

**Summary.** Union over the five variants: 4 of the 10 cases with panel rows had at least one alert in the 72 h
before the news (Year in Search, Feb 2026 strikes, Khamenei, Taylor Swift), all 36-52 h early; none of the
alerts fell in the final 36 h, where the reported flows (Nobel -11 h, Feb strikes and Khamenei "hours before",
ceasefire "hours before") actually were. The 24 h price change after each pre-news alert was small (+0.03 to
-0.02): the alerts did not mark the move. One of the five pre-news alerts (Year in Search, Pope Leo XIV "Yes",
mid 0.50) pointed against the eventual outcome. Per-variant pre-news case rate: `large_trade` 3/10,
`convex_longshot` 2/10, `imbalance_burst` 1/10, `new_wallet_concentration` 0/10, `pressure_no_response`
0/10. Against controls (any alert in the window): `large_trade` alerted 7/15 case markets vs 1/19 quiet_move and
1/10 quiet_nomove; `imbalance_burst` and `pressure_no_response` alerted far more often on quiet large-move
markets (11/19, 9/19) than on cases (1/15, 0/15). The two contrast cases (Pope, Nobel 2026) had no alerts.
Feb strikes and Khamenei overlap in time and topic (dependent); the effective number of independent cases is
below 10.

**Held-out hit rate:** best single variant 3/10 cases (`large_trade_v1`), any variant 4/10, with leads of
36-52 h; the reported last-hours flow was missed by every variant at the declared budget.

## 8. Caveats

1. **Selection and reporting bias** (section 1). Every case was chosen because a large, conspicuous move
   happened and was written about. Recall here is conditional on that and is not a detection rate.
2. **Tiny n and dependence.** 10 cases with rows, three Iran-war markets within six weeks; 29 controls instead
   of 110. Nothing here is significant or testable under the programme's 30-episode / 10-cluster floor.
3. **Market-level features cannot see per-wallet patterns.** The reports are about specific fresh wallets
   sizing into long shots; at a top-1% budget across a mixed panel, the busiest Iran-war markets dominate the
   ranking and thin markets' single prints dominate `large_trade`.
4. **News times** are approximate for Year in Search, OpenAI, Feb 28 strikes and Axiom (section 5).
5. **Wallet age** is "first seen in panel or first Polymarket trade for top wallets", not a full wallet
   history; wallets beyond the top 200 per market are aged only by their in-panel appearance.
6. **No conclusion about any person or wallet.** "Reported unusual pre-news trading" throughout; allegations
   and charges are untested.
