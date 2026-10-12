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
