# IF-H2: timing information in deadline ladders (development study)

**Status:** DEVELOPMENT, `exploratory_historical`. Not prospective evidence; no edge, calibration, tradability or
profitability claim; nothing here says anything about any trader. Theory: `INFORMED_FLOW_SIGNAL_THEORY.md` §3 item 9
(`ifx_term`) and §7 (IF-H2). Governance: `FEATURE_DISCOVERY_PROGRAMME.md` §3 (ladder L0-L5, trial logging).
Code: `backend/astrolabe/research_lab/if_h2.py`, runner `backend/scripts/run_if_h2.py`, tests
`backend/tests/test_research_lab_if_h2.py`. Data: `data-dumps/research_lab/if_h2/` (not committed).

## 1. Hypothesis

Markets "X by D1 / D2 / ..." are a cumulative ladder: `v_i = P(X by d_i)`, so `v_1 <= v_2`. Absent news, the near
rung decays relative to the far one. If the near/far ratio rises beyond its hazard-implied decay, someone may know
*when*, and the near-dated YES should drift up (and resolve YES more often than priced).

## 2. Ladder universe (grouper `ladder-grouper-v1`, metadata only)

- Source: Gamma `/events`, walked by event `start_date` in 7-day windows (split while a window hits the offset cap),
  2025-06-01 to 2026-10-10, open and closed, excluding tag 102127 (up-or-down crypto).
- Per event: binary, non-neg-risk markets whose question contains "by" / "before" / "in YYYY" and whose deadline
  parses (from `groupItemTitle` first, then the question; a missing year is the first such date on or after the
  creation day minus one; "before YYYY" = 31 Dec YYYY-1). Deadline = 23:59:59 US Eastern on that day. The market
  `endDate` is **not** used: it is sometimes wrong (e.g. a "by March 31" rung with endDate June 30).
- Rungs are grouped by question stem (date phrase removed); the stem with the most distinct deadlines is the ladder
  if it has >= 2. Duplicate deadlines keep the lowest market id. No price or outcome enters the grouper.
- Cross-event series ladders (one event per rung) are excluded in v1. Neg-risk "which month" events are excluded
  (they are exclusive buckets, not cumulative).
- Survivorship: only events Gamma lists at fetch time with a startDate in the window.

## 3. Causal signal (`ifx_term`, exactly as theory §3 item 9)

Grid: 6h (00/06/12/18 UTC), 2025-09-01 to 2026-10-05. Prices: CLOB `prices-history`, hourly fidelity, 14-day
windows; a point stamped `s` is usable at `t` only if `s + 3600 <= t` and no older than 12h.
At each `t`, near rung = earliest-deadline rung with >= 2 days to its deadline, not closed; far = the next rung.
Both rungs need valid prices at `t` and `t-6h` with `0.02 <= v2 <= 0.97`, `v1 >= 0.005`, `v1 <= v2 + 0.01`
(inconsistent ladders are excluded, E005-type).

- `N = v1/v2`; `h` = constant hazard fitted to `v2` at `t-6h`: `h = -ln(1-v2(t-6h)) / (d2-(t-6h))`.
- `Nc(u) = (1-exp(-h(d1-u))) / (1-exp(-h(d2-u)))`.
- `R = (N(t)-N(t-6h)) - (Nc(t)-Nc(t-6h))`; `z = R / sd(R over the ladder's rows in [t-14d, t))`, >= 8 prior rows.

Not applied historically: the news gate (no news archive is collected) and the stale-quote check (no trades in this
panel). The un-gated signal is tested; a gate could only refine it.

## 4. Development design (written before any outcome was computed)

- **Target (primary):** near-rung drift `y_24h = v1(t+24h) - v1(t)` (last point <= t+24h, within 12h; resolved
  payout if the rung closed earlier). Secondary: `y_168h` (7 days), and resolution excess `payout - v1`
  (descriptive).
- **Baseline M0v (own-market):** logit v1, |v1-0.5|, near-rung change over 1h/6h/1d/1w, realised vol 1d/7d (hourly
  diffs), log days to d1. No trading-activity terms (no trades in this panel). **M0vL** adds the far rung
  (logit v2, far 6h change, log days to d2), so z must beat simply knowing the far rung.
- **Arms:** M0v, M0v+z (clipped z and 1[z >= 2]), M0vL, M0vL+z. OLS, missing values median-imputed with indicators.
- **Walk-forward:** monthly; each test month uses all earlier months (rows with `t + horizon` before the month
  starts, i.e. purged), first 3 months training only. Later months = 2026-05 onwards.
- **Inference:** event-clustered percentile bootstrap (2,000 resamples, seed 20261012).
- **Primary development statistic (decision rule):** on later months, horizon 24h, the mean out-of-sample M0v
  residual drift of the near rung in rows with `z >= 2`; "promising" only if its 95% CI excludes 0 **and is
  positive**, the ΔR² of M0v+z over M0v has a positive CI on later months, and the within-time shuffled-z placebo
  does not show the same. Otherwise the result is recorded as null and no E008 is registered.
- **Cost check:** the gross drift is compared with the median quoted spread of ladder near rungs in AREPO's own
  live snapshots (a round trip pays at least one full spread plus the taker fee).
- One run (`r0`) is planned. Every run is a `trials.jsonl` line (kind `if_h2_ladder_dev`, role `exploratory_dev`).

## 5. Results

Pending.
