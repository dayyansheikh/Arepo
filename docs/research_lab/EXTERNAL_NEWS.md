# External news / attention features (GDELT DOC 2.0) - prototype

Module `backend/astrolabe/research_lab/external_news.py`; pilot `backend/scripts/external_news_pilot.py`.
Family name for later wiring: `ml_external`, feature version `ext-news-gdelt-v1`. Exploratory only: rows carry
`evidence_role` of `exploratory_dev` or `exploratory_historical` (anything else raises). Not wired into
`ml_panel`; no edge claim.

## Query terms
Deterministic from the market question (event title only if the question has no entity): up to two quoted
capitalised phrases (entities) joined by AND, else the two longest non-stopword tokens, plus
`sourcelang:english`. Digits, months, weekdays and generic question words are dropped. The query string is
stored on every record. No per-market tuning.

## Timestamp semantics (verified against the API response shape and docs)
- `artlist` returns `seendate` (`YYYYMMDDTHHMMSSZ`, UTC): when GDELT first saw the article. The publisher's
  publication time is NOT in the DOC API. We use `seendate < t` strictly, which is the conservative PIT clock.
- Timeline modes label a bin by its start; resolution is automatic (7-day spans return day bins). Only bins
  with `start + width <= t` are used, so tone lags by up to a day.
- `startdatetime`/`enddatetime` give historical origins with the same function (set role
  `exploratory_historical`). Caveat: the index is re-processed and its source set and entity matching have
  hindsight; historical rows are a development proxy for what a live collector would have received.

## Features at origin t
`ext_news_n_{1h,6h,24h}`, `ext_news_ratio_{1h,6h,24h}` (window rate over the rate in [t-7d, t-24h)),
`ext_news_tone_mean`, `ext_news_tone_change` (last complete bin minus mean of earlier bins),
`ext_news_n_sources_24h`, `ext_news_hours_since_last` (168 = none in 7 days, censored),
`ext_news_truncated`. Missing is NaN, never 0. artlist is capped at 250 newest records: when a window is not
fully covered, the count and ratios are NaN and `truncated=1`, so busy topics lose exactly the burst signal
they would carry (a known bias of this endpoint; the production path should use the 15-minute raw files).

## Cache and rate limits
Responses cached under `data-dumps/research_lab/external_news/` (content-addressed JSON, 500 MB cap,
no caching beyond it). GDELT asks for 1 request per 5 s; the client spaces requests at 10 s, retries 429s
with exponential backoff (to 300 s) and reports a failed fetch as missing.

## Leakage risks
1. `seendate` can lag publication (crawl delay) - safe direction for PIT, but a live collector sees the same
   lag, so use the same clock live. 2. Index re-processing and dedup can change historical counts. 3. Query
   built from the question reflects the question author's knowledge at creation, not resolution. 4. Text/LLM
   features stay in tier (c).

## Pilot results (snapshot 20261011T203106Z, origin 2026-10-11 20:31Z, role `exploratory_dev`)
First two attempts were 429 from this IP for >1 h; the third worked (6 s spacing, retries on 429).
Only 80 records were written (200 requested; the rest of the sample was not recorded - not investigated).
- **Status:** ok 8, no_articles 38, fetch_failed 34 (HTTP 429 after retries). Coverage of count/last-article
  features 0.57; ratios 0.10; tone 0.06; every count that exists is 0 (n24h > 0 in 0 of 80).
- **Latency:** median 13.5 s per successful request (throttled server); 354 requests, 55 failed; 224 s
  median per market (backoff dominates). 200 markets would take about 12 h at this rate.
- **Index staleness:** all 8 `ok` queries, including "Trump", show the same newest article 37.8 h before the
  origin (Birch query 132 h). The DOC index appears to have been behind by more than a day for this window
  (or throttling returned a stale index), so the "no_articles" cells are not evidence of no news. I could
  not re-probe (still 429 at 05:10Z).
- **Query relevance, 20 spot-checks** (question -> query -> verdict): 15 returned no headline (Solana, Pump.fun,
  Unit, Xerox, XRP, "OpenAI public ticker", "AI charged with a crime", Sauer/Katsas/Bumatay SCOTUS, UK election,
  UK PMs, Tlaxcala, Royal, Pittsburgh snow, Cherki, Google LiveBench: unknown, empty not informative).
  Of the 5 with headlines: Canada inflation -> rice contest, Jerusalem Post column, a mining stock (irrelevant;
  "Canada" is too generic); OpenAI/Humanity's Last Exam -> Anthropic Claude policy story (irrelevant); Birch &
  Swinnerton-Dyer -> "Anticloud ... AI benchmark" press release (irrelevant). 0 of 20 were clearly relevant.
- **Query flaws seen:** "Unit", "Fed", "Lighter" are ambiguous single words; "UK Prime Ministers" and
  "Humanity" are fragments; fallback nouns ("charged crime") are generic. No ML disambiguation by design.

## Verdict
GDELT DOC is not usable as a research feature source from this environment: aggressive throttling (34/80
failed), apparent index lag of >1 day, a 250-record artlist cap, and poor query-to-market relevance. Most
Polymarket questions are long-horizon or numeric-threshold, which do not map to news bursts. Do not wire
`ml_external` news features from this path. If revisited: collect the 15-minute GKG files live with an
entity map frozen before use, and measure index lag first.

## Fallback: Wikipedia pageviews (`fetch_pageviews`, `pageview_features`)
Free REST per-article daily API (verified live: 200 for `Xi_Jinping`, 404 for a non-page). Title is the
extracted entity with underscores (no search); 404 gives NaN, never 0. PIT: day D (stamped `D00`) is used
only if D + 24 h + 12 h lag <= t, so the partial current day is never used and a day published late is
excluded; the 12 h lag is a conservative assumption, not a measured publish time. Features:
`ext_wiki_views_last_day`, `ext_wiki_views_mean_7d` (7 usable days before it), `ext_wiki_ratio_1d_7d`,
`ext_wiki_days_available`. Coverage is limited to markets with a named entity that has an English article
(untested at scale). Daily resolution means no intraday signal. Role must stay exploratory.
