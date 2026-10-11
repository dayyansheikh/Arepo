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

## Pilot
See the commit message / ledger note for the run on the latest snapshot (coverage, latency, spot checks).
