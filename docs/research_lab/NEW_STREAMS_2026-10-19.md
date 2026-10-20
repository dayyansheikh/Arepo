# New prospective streams (2026-10-19)

Status: **code, tests and a host dry run done; NOT deployed, NOT in cron.** Branch `feat/new-streams`. Data only: these
collectors compute no statistic, read no outcome and never trade. They exist because the data below cannot be fetched later.

## 1. What the host already captures (inventory, 2026-10-19)

| stream (host) | cadence | what it holds | covers |
|---|---|---|---|
| complete-universe snapshot + `rows_ext` sidecar (`arepo_pass.sh`) | 2 h | every open Polymarket market (about 249k rows): touch, last, 1h/1d/1w change, volume, liquidity, `updated_at`; sidecar: fees, tick, `rewards_min_size`, `rewards_max_spread`, `clob_rewards`, OI, `uma_resolution_statuses`, `created_at`, event comment count | rewards programme parameters, comment counts, UMA status, market creation |
| book sweeps, trade samples, flow screen, E011 (`arepo_pass.sh`) | 2 h | CLOB books, sampled trades | Polymarket microstructure |
| live trade monitor (`supervise.sh`) | continuous | large prints, hashed wallets | flow |
| cross-venue live E009/E010 (`supervise.sh`) | 120 s | Kalshi + Polymarket touch for at most `MAX_PAIRS` matched pairs | Kalshi on matched pairs only |
| CB8-H `/holders` (q0162, queue) | daily | top-20 holders, 1,500 + 300 markets, hashed | holder snapshots |
| CB12-O (cron, trading days) | 3/day | CBOE delayed chains + CLOB books for equity strike markets | equity options anchor |
| CB15-E (cron, election night) | 1 min, 11-02..11-06 | books of election markets | election night |
| CB10 / CB13-R / CB8-B (queue, batch) | one-off | Deribit trades, Binance klines (public archives) | crypto references (backfillable) |

Missing and **time-sensitive** (cannot be backfilled): other venues' quotes on the same political questions (PredictIt,
Smarkets), sportsbook line movement, and the Polymarket rule text with the time of each edit. The snapshot's `updated_at`
cannot date an edit: it changed for 116,940 of 246,961 markets between the 18:31Z and 20:31Z captures of 2026-10-19
(18,312 of the 18,904 markets with 24h volume).

Considered and NOT built (backfillable or already covered): Polymarket holders (CB8-H), comment counts / rewards / UMA status
(snapshot sidecar, 2 h), comments and UMA proposal/dispute events (persist via API / Polygon logs), Binance or other crypto
reference prices and derivatives metrics (`data.binance.vision` keeps klines and the 5-min futures `metrics` files, i.e. OI and
long/short ratios), Kalshi universe prices (per-market candlesticks with bid/ask OHLC are served historically), Manifold (full bet
history is public), GDELT (the 15-minute files are archived; `EXTERNAL_NEWS.md`). RSS first-seen headline times are
time-sensitive but low value per request without a topic matcher; left for later.

## 2. Chosen streams

All four: keyless public endpoints, polite (`rps` per stream, at most one call at a time per stream, retries only on
429/5xx with `Retry-After` honoured, capped backoff, run budget), receipt-timed (`sent_utc` / `recv_utc` per request, sha256 of each
response body in the poll line), change-only append-only JSONL with periodic checkpoints (format: `data_catalogue/README.md`,
"Prospective streams"), idempotent per slot, crash-safe (rows + COMMIT line in one write + fsync; torn tails isolated; state
loss means a full re-write, never a silent skip), disk-guarded (exit 75, nothing written, when root free disk minus the poll's
allowance < 4 GB, `data-dumps` > 40 GiB, or the stream's own cap). Code: `backend/astrolabe/research_lab/streams/`, entry point
`backend/scripts/run_stream.py <stream>`.

| stream | dir | source | slot | what it enables | rate |
|---|---|---|---|---|---|
| `predictit` | `stream_predictit/` | `GET www.predictit.org/api/marketdata/all/` (whole open universe, 1 request) | 1 min, hourly checkpoint | **CH114** fee-adjusted PredictIt anchor (a third, capped US retail crowd); 10-minute lead of PredictIt changes on congressional races; the 2026-11-03 midterms (House-seat ladders, control) | 1,440 req/day |
| `smarkets` | `stream_smarkets/` | `api.smarkets.com/v3`: events (politics, current_affairs), markets, contracts, volumes hourly; `quotes` (top 3 levels) + `last_executed_prices` every slot | 5 min, hourly checkpoint | a real-money UK exchange crowd on the same questions (CH114's cross-venue family, CH25-style level gaps, CH115 horizon staleness); midterm control combos are listed | about 5,400 req/day at 1 rps |
| `espn_odds` | `stream_espn_odds/` | `site.api.espn.com/.../<sport>/<league>/scoreboard`, 12 leagues (NFL, CFB, NBA, WNBA, NCAAM, MLB, NHL, EPL, UCL, La Liga, MLS, UFC) | 10 min, 6 h checkpoint | **CH29** closing-line value: DraftKings moneyline / spread / total with open and current (closing at kick-off) prices vs Polymarket's pre-game price. Sports scope is undecided; this is capture only, category is a later population parameter | 1,728 req/day |
| `gamma_rules` | `stream_gamma_rules/` | `GET gamma-api.polymarket.com/markets?id=..` (50 ids each). Frame (no request): latest complete snapshot, open markets with 24h volume > 0 by volume (about 19k, cap 25k) | hourly: top 3,000; full frame at 00/06/12/18Z; daily hash checkpoint | **CH08** rule-edit events (the time and text diff of a clarification), **CH63** specificity, **CH64** rule-divergence twins, **CH48** regulation-time rule misreads, CB7-S text-stability (q0156 needs the listing-time text) | about 2,800 req/day at 2 rps |

Fields kept per key are listed in each module's docstring; no price-outcome, wallet or Polymarket price field is stored by
`gamma_rules` (rule-bearing fields only: question, description, resolutionSource, dates, outcomes, groupItemTitle, UMA
bond/reward/liveness, resolvedBy, fallback type; event title/description/resolutionSource/dates).

## 3. Measured (host dry run, 2026-10-19 21:55-22:02Z, `/tmp/newstreams`, deleted afterwards)

| stream | polls | requests/poll | response bytes/poll | written: first poll | written: later polls | est. MB/day written |
|---|---|---|---|---|---|---|
| predictit | 7 (1/min) | 1 | 459 kB | 340 kB (867 keys) | 0.75-1.9 kB (0-3 changed contracts) | about 10 (hourly checkpoint 8.2 + per-minute 1.7) |
| smarkets | 2 | 48 (catalogue) / 16 | 760 kB / 237 kB | 598 kB (1,734 keys) | 46 kB (123 changed books of 677) | about 26 |
| espn_odds | 2 | 12 | 1.69 MB | 99 kB (94 games, 76 with odds) | 4.5 kB (1 changed, pre-game evening) | about 2-5 (in-game polls write more) |
| gamma_rules | 1 (top 3,000) | 60 | 19.9 MB | 7.4 MB (3,799 market + event keys; about 1.95 kB/key) | see churn | about 4/day (+ about 40 MB once for the first full frame) |

- 22 calls in all: 12 committed, 10 `slot_done` (repeat calls inside a slot did nothing: idempotency on the host), 0 errors, 0 retries.
- gamma_rules churn probe (read-only, 2026-10-20 22:56Z, about 25 h after the first poll): of the keys seen in both polls, 3 changed
  (all event descriptions), so rule text is stable enough that change-only rows are rare and real; the top-3,000 frame itself turned
  over (2,383 new keys in a day), which is why the full frame is polled every 6 h.
- gamma_rules peak RSS 99 MB, 33 s wall for 60 requests (frame build from a 25 MB `rows.csv.gz` included). The others are well under that.
- **Total about 45 MB/day written** (about 1.4 GB a month before archive compression) against 17.2 GB used of the 45 GiB cap and 56 GB
  free on the host; the stream caps (2-3 GB each) stop any single stream long before the global cap.

## 4. Failure modes

| failure | behaviour |
|---|---|
| network error, 429, 5xx | up to 3 attempts per request (backoff 2 s, 8 s or `Retry-After` <= 60 s); if the poll fails: an `ok: false` poll line with the error and per-request statuses, exit 1; the slot may be retried, never back-filled |
| one ESPN league or some Gamma batches fail | the rest is committed; failures listed in `meta.failed` / `meta.failed_batches` / `meta.missing` |
| API shape change | parse guard: PredictIt with no markets list or zero markets is a failed poll; unknown fields are ignored; absent fields are `null` (missing), never 0 |
| crash mid-write | torn last line is terminated before the next append; rows without a COMMIT line are ignored by readers; slot idempotency is recovered from the day file's COMMIT lines if `state.json` is lost |
| `state.json` corrupt or lost | next commit re-writes every key in full (`state_reset: true`) |
| disk short | exit 75 before any request; nothing written; the cron log line carries the reason |
| overlapping calls | cron `flock -n` per stream and an internal `fcntl` lock: the second call exits 0 `busy` |
| no complete snapshot (gamma_rules) | uses the cached frame from the previous poll; with none, exit 75 (pending) |
| Smarkets universe > 800 open markets | truncated by id order; `meta.catalogue_truncated: true` |
| a venue changes its terms or blocks the host | polls fail visibly in the log; nothing else depends on these streams yet |

Caveats for later analysis: PredictIt `timeStamp` is a naive local-time string kept raw (`src_ts`); Smarkets prices are basis points of
probability and quantities raw API units; ESPN `close` means "current" until the event starts; Gamma `id` queries return only the ids
asked, so an edit to a market outside the frame is seen only once the market enters the frame (its first row is then `new`, not
`changed`: the edit time is unknown, not the row time).

## 5. Deploy steps (coordinator; nothing here is deployed)

1. Merge `feat/new-streams` into the research branch (new files plus small additive edits to `data_catalogue.py`,
   `data_catalogue/README.md`, `RETENTION.md`, `archive_retention.json` `deferred_rules`), then `scripts/oracle/deploy.sh`.
2. On the host, a one-off check per stream:
   `cd ~/arepo/backend && ../.venv/bin/python scripts/run_stream.py predictit` (repeat for `smarkets`, `espn_odds`,
   `gamma_rules --top 3000`); each prints one JSON line with `"status": "committed"`.
3. Install the four lines of `scripts/oracle/streams_crontab.txt` (uncommented) with `crontab -e`, after backing up the crontab
   (`crontab -l > /tmp/crontab.bak.$(date +%s)`). They take no collector lock, do not use the queue lanes and do not touch E009/E010/E011 files.
4. After 24 h: `ls -la ~/arepo/data-dumps/research_lab/stream_*/`, `tail -n 3 ~/arepo_collector/logs/stream-*.log`; expect about 45 MB a day
   in total and no `"exit": 1` runs outside venue outages.
5. After the first nightly archive contains these dirs (03:30Z the day after the first full day), the 14-day `deferred_rules` entries may be
   moved to `rules` under the existing user approval (verified-archived files only).
6. Rollback: comment the lines; the data stays.

No registered experiment reads these streams. Any test that uses them needs its own pre-registration; the first possible window starts
at the install time (the data before that does not exist).
