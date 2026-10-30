# Live large-trade monitor (2026-10-12)

Research only, local, read-only. It never trades and holds no credentials. Nothing here claims alpha, and no
alert is a label of insider or informed trading.

## Why
Held-out cases (Nobel 2025, strikes) show reported pre-news flow in the final hours. AREPO's 2-hourly samples are
too coarse and the frozen detectors alerted 36-52 h early. A prospective test needs near-real-time capture of
large prints.

## What runs
`backend/scripts/run_live_trade_monitor.py` (module `astrolabe/research_lab/live_trade_monitor.py`), a foreground
loop. `--once` runs one cycle, `--max-cycles N` stops after N, `--outcomes` runs the separate outcome pass.

Each cycle (default 300 s):
1. Data API `/trades?takerOnly=true&filterType=CASH&filterAmount=1000`, newest first, paged until the page is older
   than the previous watermark minus 120 s, then de-duplicated by an HMAC key of tx|asset|side|size|price|wallet.
   `takerOnly=true` is the default (maker legs double count one trade; they belong to design N3). Configurable.
2. Each print is stored with its receipt time, venue time, market, side, outcome, size, price and an HMAC wallet hash.
3. Wallet: causal first-trade time from `/activity` (`end = ts - 1`, 1 request, cached forever in `wallets.jsonl`;
   "no earlier trade" stores the print's own time and flags `first_inferred_from_null`). Profile creation date is
   fetched only for wallets younger than 7 days. Largest prints get lookups first (40 per cycle; the rest are flagged
   `wallet_lookup: deferred`, never back-filled into old lines).
4. Market context from Gamma (`/markets?condition_ids=`), cached 5 min: mid, spread, liquidity, volume24h, end date,
   1h change, category (`feeType`, else a slug prefix; weak). `snapshot_ts` is stored; with slow cycles it can lag receipt.
   At most 50 markets (by total cash) are enriched and scored per cycle; the others are stored with `skipped_budget`.
5. Features from the market's newest 500 taker trades via `flow_features.compute_flow_features`, anchored at
   `trade ts + 1`, then `detector_eval.normalise_panel(source='live')` and `score_rule` for every rule in
   `detector_specs/FROZEN.json` (hash verified on load). Deviations from the history definitions are listed in the
   module docstring (`large_trade_rel` live approximation with `ltr_window_h`; `new_wallet_share_l` is NaN).
   IF-H1 is NOT run: `FROZEN_IF_H1.json` does not exist yet (checked at start-up, `Monitor.if_h1_frozen`).
6. Alerts: `alertable` and `score >= 2.0` (fixed constant, `config_hash` written into each line, never tuned on
   outcomes), at most 5 per rule per cycle. Each alert gets a matched control from the same cycle: random (seeded by the
   alert id) same-category print, other market, other wallet, cash within 0.5x-2x, wallet first trade at least 7 days
   old. No candidate gives a `control_unavailable` line. All go to the append-only `alerts.jsonl` before any outcome.

Outcomes (`--outcomes`, run later, read-only on `alerts.jsonl`): CLOB `prices-history` of the outcome-0 token nearest
(+/-15 min) to receipt + 1/6/24/72 h, and resolution from Gamma (`closed`, prices 0/1). Lines go to `outcomes.jsonl`
with status `evaluated`, `unavailable` (only 6 h after due) or `resolved`; pending items write nothing.

## Storage and limits
`data-dumps/research_lab/live_trades/` (git-ignored): `trades-YYYYMMDD.jsonl` (daily), `alerts.jsonl`,
`outcomes.jsonl`, `wallets.jsonl`, `stats.jsonl`, `state.json`. Day cap 300 MB (pauses writing until the next UTC day),
total cap 3 GB (logs and exits with code 3). Rate 0.8 req/s, exponential back-off on 429/5xx via `history_backfill.Limiter`.
No raw address is written or logged; exceptions are logged by type only.

## launchd template (NOT installed; installing needs the user's approval)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.arepo.live-trade-monitor</string>
  <key>ProgramArguments</key><array>
    <string>/Users/DayyanSheikh/Projects/astrolabe/backend/.venv/bin/python</string>
    <string>/Users/DayyanSheikh/Projects/astrolabe/backend/scripts/run_live_trade_monitor.py</string>
  </array>
  <key>WorkingDirectory</key><string>/Users/DayyanSheikh/Projects/astrolabe/backend</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
  <key>ThrottleInterval</key><integer>60</integer>
  <key>StandardErrorPath</key><string>/Users/DayyanSheikh/Library/Logs/arepo-live-trade-monitor.err</string>
  <key>StandardOutPath</key><string>/Users/DayyanSheikh/Library/Logs/arepo-live-trade-monitor.out</string>
</dict></plist>
```
A second job (daily) should run `run_live_trade_monitor.py --outcomes`. The cap exit (code 3) is "unsuccessful", so
KeepAlive would restart it; remove KeepAlive or check disk before enabling.

## Status
Collection tooling only, evidence role `prospective_unregistered`. A scored prospective test needs the registration
in `UNUSUAL_FLOW_PROGRAMME.md` section 7 (rule hashes, primary metric, MDE, stopping rule, Holm, control recipe above).

## Pilot (2026-10-12, 04:51-06:43 UTC, 24 cycles, takerOnly=true, >= $1,000)
| Stat | Value |
|---|---|
| Prints stored | 805 (498 in the first cycle: 10-min bootstrap backlog; steady state about 13 per cycle, about 160/h) |
| Wallets looked up | 173 (cap 40 per cycle; the first cycle used all 40) |
| Alerts | 188 (about 100/h, inflated by the backlog cycle; 5 rules x cap 5 per cycle), 71 matched controls, 117 `control_unavailable` |
| Requests | 654 total (about 0.1/s average, 0 HTTP 429); steady cycles 20-30 requests, 25 s |
| Peak RSS | 116 MB |
| Disk | about 2.9 MB for 2 h (about 35 MB/day), far below the 300 MB/day cap |
| Raw addresses | none: the regex for 40-hex addresses (bounded) matches nothing in outputs or logs. An early run logged httpx URLs (which carry addresses) to stderr; those logs were deleted and httpx logging is now silenced (test added). |

Alert volume is high for a screening list because the fixed floor (score >= 2.0) is low for live single-print rows.
It is a pre-declared constant, not to be tuned on outcomes; a registration should set the alert budget before scoring.
The `control_unavailable` rate (62% of alerts) is mostly missing same-category non-fresh wallets in the cycle pool and
weak category labels (`feeType` often absent, slug prefix used). A registered design must address control availability.

## Outcome writer status
`run_live_trade_monitor.py --outcomes` ran once on the pilot alerts: 177 outcome lines written (+1h and +6h price
points), 1,055 items pending (not yet due or beyond the 200-request budget per pass), 0 errors, 0 resolutions.
Alert lines were not modified (tested). Run the pass repeatedly (daily or hourly) until all horizons are filled.

## Revision 2 (alert budget and controls)
- The fixed score floor is gone. A trade alerts when a rule's score passes the **trailing 99th percentile** of that rule's
  alertable scores from the previous 7 days, using only earlier cycles (this cycle is added afterwards). Fewer than 200
  trailing scores: no threshold, no alert. Until 7 days of score history exist, alerts are written with `warmup: true`
  and counted separately (`alerts_warmup`). Cap of 5 per rule per cycle stays as a safety.
- Every scored trade is appended to `scores-YYYYMMDD.jsonl` (features and per-rule score, even if not alertable), so
  any budget can be recomputed later. History and the control pool are rebuilt from disk at start.
- Controls come from all scored trades received in the previous 24 h (and this cycle), same category, other market and
  wallet, wallet first trade at least 7 days old, within +/-24 h of the alert trade, size band 2x, widened to 4x then
  10x if empty. Each control line (and each `control_unavailable`) carries `control_selection` with the rule, band used,
  pool and candidate counts.
- Pilot 2 (06:51-07:46 UTC, 12 cycles): 269 prints (about 270/h), 104 wallet lookups, 365 requests, 0 HTTP 429, RSS 112 MB,
  **0 alerts** because the fresh history never reached 200 scores per rule. Alert rate and control coverage need a longer
  burn-in. Offline replay of the control rule over the 1,084 enriched prints: a control was found for 750 of 841 prints
  with a known wallet age (89%).
