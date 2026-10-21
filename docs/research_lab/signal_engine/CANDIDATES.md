# Signal engine: candidate families (living list; rewrite entries, keep it short)

Sources of candidates: replicated or advanced effects from the research programme, new data streams and learned
combinations. A candidate becomes a challenger via DESIGN_V1.md §13 (base store) or §16 (auxiliary family). Embargo
first if it isolates a hypothesis under a registered or drafted live test (§8). Status values: `active` (spec
registered and predicting), `next`, `blocked` (reason), `idea`.

| # | family / model | inputs | evidence so far | embargo | status |
|---|---|---|---|---|---|
| 1 | `event` / `se8_lr_event` | aux family from the same capture's binary listing: event size, neg-risk overround and quoted share, normalisation gap, own rank, largest sibling, siblings' Gamma 1 h / 1 d changes | E005 band deviation not supported (closed 2026-10-11); SB2-J5 sibling reversal development only; never tested as a forecast-quality add-on | none (no live test isolates it; E019 dropped uncounted) | **active** (2026-10-21) |
| 2 | `rewards` | `reward_params/<capture>` (CLOB liquidity-reward parameters; capture received before the origin start) | none; E020 draft uses the reward flag as a control / S3 (`LIVE_TESTS_4.md:90,229,243`) | token `rewards` until 2026-11-18 (LT4) before any spec | next. Probed 2026-10-21: collection began 2026-10-20T23:20Z (cron :35 every 2 h, so use the previous reward capture, finished before the origin start); rows keyed by `condition_id` (needs a condition_id -> market_id map), fields `rewards_max_spread`, `rewards_min_size`, `native_daily_rate`, `total_daily_rate`, `rewards_config[]`; ~14.3k markets. Wait for >= 7 days of history before the first fit |
| 3 | `rules` | `stream_gamma_rules` edits (rule/description changes before the origin) | none (stream proposal only, `NEW_STREAMS_2026-10-19.md:46`) | none | idea (sparse; check coverage first) |
| 4 | `xvenue2` | PredictIt / Smarkets mid gaps (`stream_predictit`, `stream_smarkets`) | none (CH114 idea) | under `xvenue` until 2026-11-04 (same hypothesis class as E009/E010) | idea (coverage likely tiny) |
| 5 | `crypto` | spot reference (Binance) distance to strike for crypto ladders | CB13-R (CH118) smoke PASS, analysis pending | check CB13-R status before any spec | blocked (no live spot stream on the host) |
| 6 | learner: LightGBM on champion + event (broad) | base + aux | - | broad: none | idea (add after se8 shows whether the family carries signal; each challenger raises K in the Bonferroni rule) |
| 7 | reversal x liquidity, trade-confirmed reversal (HB1-R, E002/E004/E006) | base | replicated historically | `chg1d_x_liq` until 2026-11-14, `flow` until 2026-11-16 | after the embargo dates |
| 8 | SHAP family attribution for the LightGBM models | fits | - | display only for non-embargoed families | next (dashboard) |
