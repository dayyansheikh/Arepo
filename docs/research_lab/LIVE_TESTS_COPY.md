# Live test E026: copy skilled wallets with latency — DRAFT pre-registration

Research tooling only. AREPO never trades. A "copy" here is a PAPER position priced from quotes AREPO already captured.
No order is sent, no wallet is called informed or an insider, and nothing here is an edge claim. Wallets are HMAC hashes
(`wallet_sidecar.hash_wallet`, key on the host only). No raw address is read, stored or printed. The skilled-set file
holds hashes only and is never committed.

**Status: DRAFT.** Not registered, nothing counted. Every line written before the spec pin is
`prospective_unregistered` and is never analysed as a confirmation. Order: the pre-window counts-only census (q0544,
section 8.2) fills the numbers marked **CENSUS-GATED** and applies the pre-declared gates (section 7.6) — done
2026-10-21, decision **register_k2**; then the challenger review (section 11); then the freeze and the pins (section 9).

## 0. Summary

- **Question.** Wallets that were skilled in the past (sign-randomisation skill, WS1 P1) stayed skilled out of sample:
  their S2 P&L was +21.7c per dollar at risk, against +3.6c for other eligible wallets. But that is the wallets' own
  P&L at their own trade prices. Can an outsider who sees their trades only later, and pays taker costs, still earn
  from copying them? And is any gain due to the wallets, or just to the kind of trade they make (price level, side)?
- **Design.** Freeze the skilled set before the window from HB1 history only. During the window, every new taker
  trade of a frozen-skilled wallet that AREPO observes in the trade-sample wallet sidecar becomes one paper copy. The
  copy enters at the first complete-universe capture whose start is at or after receipt + L. It is held to resolution.
  Matched controls are trades by non-skilled wallets in the same sample, same side, same price, age and time-to-end
  cells, in other events.
- **Primaries (Holm, k = 2, one-sided, alpha 0.05):**
  - **E026-N:** net copy P&L per dollar of the skilled copies at the primary latency, after conservative taker costs,
    is > 0.
  - **E026-C:** that ratio minus the same ratio of the matched non-skilled controls is > 0.
- **Window (proposed):** signals with receipt in `[2026-10-25T00:00Z, 2026-11-15T00:00Z)` (21 days). Label cutoff
  2026-12-06T00:00Z. Single analysis on or after 2026-12-06T12:00Z.
- **Latencies:** L = 0 (primary: the next capture after receipt, a median 1.8 h after receipt and 6.6 h after the
  trade printed, census section 7.5), 6 h, 24 h.
- **Census gates (fixed before any census number, section 7.6):** G1 copies/events and G2 pairs decide between
  registering k = 2, dropping E026-C before the pin (k = 1), or not registering as designed. G3 (MDE) only labels.
- **Expected outcome.** Probably Inconclusive or Not supported on E026-C. WS1 P2-P4 found that skilled flow adds
  nothing over generic flow, and skill may be bias exploitation (for example selling long shots). E026 tests the
  wallet-level route that WS1 recommended, with costs and latency.

## 1. Basis and hypotheses

### 1.1 Basis (development data only)

- `signal_engine/families/WALLET_SKILL.md` and `wallet_skill_dev_results_2026-10-20.json` (WS1, DEVELOPMENT,
  exploratory_historical, HB1 history, every trade before 2026-10-13):
  - P1 persistence passed (Holm p 0.002). S1 top-decile skilled wallets had `skill_z > 0` in S2 in 71.2% of cases
    (null 59.6%). S2 P&L per dollar: skilled +21.7c [+1.4, +39.6], others +3.6c [-1.7, +8.5].
  - P&L-ranked winners do not persist (52.6% vs 59.7% base).
  - P2-P4 null: skilled net flow adds nothing over generic flow for the 6 h / 24 h mid change or the resolution.
  - Caveat: skill is relative to the trade price. A wallet that exploits a price-level bias counts as skilled.
- `PRIOR_ART_2026-10-19.md` gap 7 (Gómez-Cram, Guo, Jensen and Kung 2026: about 3% of accounts skilled, 44% stay
  skilled; Akey et al.: persistence modest, contested) and gap 1 (informed long-shot buys; copy-latency test H1b).
- `COST_MODEL.md` and `costs.py`: conservative taker fees by category, half-spread, tier impact.

### 1.2 Hypotheses

- **H-N (E026-N).** `R_N = sum(net_i) / sum(stake_i) > 0` over skilled copies in the primary set (section 7.1).
- **H-C (E026-C).** `D = R_skilled - R_control > 0` over matched pairs (section 7.2).
- **Bias reading (secondary, not counted).** If skill is a price-level bias, the controls in the same side x price
  cells earn about the same, so E026-N may pass while E026-C fails. The entry-price bands (long shot / middle /
  favourite of the copied token) and BUY vs SELL signals describe where any gain sits.

### 1.3 What is not claimed

A pass is "Supported (exploratory, prospective)". It is not a trading claim. It does not say a wallet is informed. A
real copy strategy would face worse latency, queue position and size limits than this paper copy.

## 2. Window, registration and dates

| item | proposed value |
|---|---|
| `REGISTERED_UTC` (window start, `t_freeze`) | 2026-10-25T00:00:00Z |
| `END_UTC` | 2026-11-15T00:00:00Z (21 days) |
| `LABEL_CUTOFF_UTC` | 2026-12-06T00:00:00Z (END + 21 d) |
| `ANALYSIS_NOT_BEFORE` | 2026-12-06T12:00:00Z |
| registration commit | at least 24 h before `REGISTERED_UTC` (so before 2026-10-24T00:00Z) |
| census q0544 | must start before 2026-10-22T02:45Z (retention of the 10-18 / 10-19 samples; start blackout) |

**Why 10-25 and not 10-24.** On 2026-10-21 the design has not had a challenger pass. LT3 needed about three days from
census to pin (review, fixes, verification, size check). A start of 10-24 would leave about one day for that. 10-25
leaves about two and a half days. The skill set does not depend on the start date: every HB1 outcome was known by
2026-10-15 (closedTime + 48 h), so freezing at 10-24 or 10-25 gives the same file. The later start costs one day of
signals and buys an honest review. 10-24 is also LT3's start, so the registration steps would compete with LT3's.

**Move rule.** If the registration commit slips, `REGISTERED_UTC` and `t_freeze_utc` move to the first 00:00Z at least
24 h after the commit. END = start + 21 d, cutoff = END + 21 d, analysis = cutoff + 12 h. The move uses no data and is
recorded in the ledger.

**Why 21 days.** The same length as LT2-LT4. The label cutoff 21 days after END lets markets with an end date up to
14 days after entry (section 5.3) resolve, with a week of slack for slow resolutions.

## 3. Frozen skilled set (`copy_skilled.freeze_skillset`, queue draft q0540)

- **Data:** HB1 history panels `h1_first`, `h2_main`, `h3_power` only (trades 2025-04-03 to 2026-10-12, outcomes known
  2025-09-30 to 2026-10-13). No live-test store, no trade sample and no outcome of E009-E025 is read.
- **Rule:** exactly the WS1 construction (`WALLET_SKILL.md` sections 1-2): `wallet_skill_dev.profile_trades`, then
  `wallet_skill.build_profiles_batch(..., t_freeze, n0 = 10, min_pos = 5)`, then `snapshot_frame(top_frac = 0.1)`.
  Eligible = `n_pos >= 5`. Skilled = eligible with `skill_z > 0` and `skill_score` in the top 10% of eligible.
- **Point in time:** a position counts only if its market's outcome was known strictly before `t_freeze`
  (closedTime + 48 h). Truncated markets and post-close prints are excluded.
- **Write-once:** `copy_skilled/skillset/skillset.csv.gz` and `skillset_manifest.json`. The code refuses to rebuild and
  refuses to freeze at or after `t_freeze`. The file's sha256 goes into the spec (`skillset_sha256`) before the pin.
  The recorder refuses a set whose sha256 differs from the pin.
- **Not tuned.** MIN_POS 5, N0 10 and top 10% are the WS1 values, fixed before any WS1 result. They are not changed.
- **Known limits.** Profiles cover only AREPO's sampled history markets (12.7k). Many truly skilled wallets are never
  eligible. Skill is taker skill. The set is not refreshed during the window (a frozen set is the honest test of
  persistence; a refreshed set would mix in-window outcomes).

## 4. Signals and matched controls (`copy_skilled.signals_from_batch`, q0541)

### 4.1 Primary arm: trade-sample wallet sidecar

- Source: each active-frame trade sample (every 2 h) and its `wallets.csv.gz` sidecar (the newest 500 taker trades
  per sampled market, wallet hash, side, outcome, price, size, venue ts).
- Receipt time of a trade = `received_utc` of that market's successful request in the sample manifest.
- **First observation only.** A trade with `ts <=` the request sent time of an earlier processed sample of the same
  market is "seen before" and dropped. So each trade gets the receipt of the first sample that could have shown it.
- **Signal.** The first in-window trade (`ts >= REGISTERED_UTC`) of each (frozen-skilled wallet, market) becomes one
  signal. Later trades of the same wallet in the same market are not copied again. One copy per (wallet, market).
- **Copy direction.** BUY of outcome k -> buy token k. SELL of outcome k -> buy token 1 - k (the complement).
- Samples are processed strictly in start order. An in-progress sample blocks later ones (order defines the first
  observation) for at most 4 h after its start (`IN_PROGRESS_GRACE_S`). A sample still not complete after that, a
  sample of another frame, or one whose files were retired before it was read, gets a write-once
  `signals/<id>.missing.json` marker and is never back-filled. The marker (not the state cache) is the ground truth,
  so a lost cache cannot let a late sample be read out of order. If `state.json` is lost, the per-market
  "last sent" times are rebuilt from the processed samples still on disk (`rebuild_last_sent`, logged); a sample
  whose files were already retired cannot contribute, which can only make a trade look new later (disclosed).
- **Coverage limits (disclosed).** Only sampled markets (about 2,000 per sample). Only the newest 500 trades per
  market: in a busy market, trades between two samples can be missed. Trade age at receipt (receipt minus trade ts)
  in the census: p10 / p50 / p90 0.7 / 4.5 / 16.3 h (section 7.5); older trades are those first seen in a later sample.

### 4.2 Secondary arm: >= $1k live prints

- Source: `live_trades/trades-*.jsonl` (the live trade monitor, receipt `recv_ts`, market from the line's Gamma
  context). One batch per complete UTC hour. Same signal and control rules, separate (wallet, market) sets.
- Descriptive only. It is not part of either primary.

### 4.3 Matched controls

For each skilled signal, up to 3 control trades from the same batch (same receipt clock):

- by a non-skilled wallet (any profile status: eligible-not-skilled, ineligible or unprofiled);
- the first trade of its (wallet, market) in the batch, never used as a control before in the arm;
- same side (BUY / SELL);
- same trade-price bucket (edges 0, .05, .15, .25, .35, .5, .65, .75, .85, .95, 1);
- same trade-age bucket (receipt minus trade ts: < 1 h, 1-3 h, 3-6 h, 6-12 h, 12-24 h, > 24 h);
- same time-to-end bucket (origin Gamma end date minus receipt: < 1 d, 1-3 d, 3-14 d, > 14 d; missing or past end
  gives no control);
- another market and another event.

Ties are broken by `sha256(parent signal id | candidate id)`, so the draw is deterministic and uses no outcome. A
signal with no matching candidate keeps 0 controls; it still counts in E026-N but not in E026-C.

## 5. Entries, latency and exits (`copy_skilled.entries_for_capture`)

### 5.0 Clocks and latency definitions

| name | definition |
|---|---|
| trade ts | the venue timestamp of the copied trade (sidecar `ts`) |
| receipt | `received_utc` of the sample's successful request for that market (first observation, section 4.1) |
| trade age | receipt minus trade ts (what AREPO could not see; matched in the controls) |
| nominal latency L | fixed offset after receipt: 0, 6 h or 24 h; due time = receipt + L |
| entry capture | the first complete capture whose start is `>=` the due time |
| entry delay | entry capture start minus due time (> 6 h puts the copy out of the universe) |
| entry time | the entry row's own `received_utc` (later than the capture start) |
| realised latency | entry time minus trade ts = trade age + (entry time - receipt); reported as quantiles |

No quote, payout or price change dated after the entry time enters the entry decision or the universe flags.

### 5.1 Entry

- For latency L, the entry is the quote row of the FIRST complete capture whose start is `>= receipt + L`. Never an
  earlier capture. The row's own `received_utc` is kept (it is later than the capture start).
- Latency set (fixed): **L = 0 (primary), 6 h, 24 h.** With 2-hourly captures and samples taken about 8-30 min after a
  capture start, L = 0 means the next capture, about 1.5-2 h after receipt. Realised trade-to-entry latency adds the
  trade age (section 8 gives the measured quantiles).
- Status of the entry row: `two_sided` (0 < bid < ask < 1), `one_sided`, `closed_flag` or `absent` (market not in the
  capture). Only `two_sided` entries can enter the universe.
- Entry delay = capture start minus due time. Delay above 6 h (missed captures) puts the copy out of the universe.

### 5.2 Prices and costs (`copy_skilled_analysis.copy_economics`)

- Copied token j: outcome-0 quote for j = 0; mirrored for j = 1 (`ask_1 = 1 - bid_0`, `bid_1 = 1 - ask_0`).
- Hold to resolution: one taker leg. Per share: half-spread `h`, impact = the tier MEAN of the $100 buy impact in
  `cost_model_calibration_v1.json` by the entry row's Gamma liquidity (`>=100k` 0.15c, `10k-100k` 0.72c, `1k-10k`
  1.37c, `<1k` 1.53c), taker fee `rate x max(pq, pq^exponent)` at `p = ask`, with the conservative fee policy
  (`max(schedule, docs)`, unknown category 7%, fees off only if the market says so). The exponent is the capture's
  `fee_schedule` exponent (1 if missing). For exponent >= 1 the fee is the linear `rate x pq`; for exponent < 1 it is
  the larger scheduled value, never the smaller one.
- `net per share = pay_j - ask_j - impact - fee`; `stake per share = ask_j + impact` (a $100 stake scale).
  For exponent >= 1 (or missing) the cost term equals `costs.cost_check(...).taker_resolution_cost_ps` (pinned by a
  unit test); `test_fee_exponent_is_conservative` pins the exponent rule.

### 5.3 Universe (fixed before any data)

A copy is in the universe if: entry `two_sided`; entry delay <= 6 h; copied-token ask in [0.05, 0.95]; spread <= 0.10;
and the entry row's Gamma end date is at most 14 days after the entry row's receipt (so it can resolve by the cutoff).
The **primary set** caps each skilled wallet at its first 10 universe copies per UTC receipt day (receipt order; per
arm and latency). Controls follow their parent. The uncapped universe is a secondary.

### 5.4 Fixed-horizon exit (secondary)

For each two-sided primary-latency entry, the exit is the first complete capture starting at or after the entry row's
receipt + 24 h. The copy sells at that capture's bid of the copied token (fee and impact charged). This secondary uses
all entry-ok, price-ok copies, also long-dated ones.

## 6. Resolution labels, censoring and missing data

- **Labeller** (`copy_skilled.label_resolutions`, q0542): Gamma `/markets?id=...` GET (public, read-only; only market
  ids leave the host), each market at most once per 20 h, <= 600 requests per pass at 1 request/s. Only final records
  are written (write-once): `resolved` (1/0) or `split_50_50` (pays 0.5). The earliest final record per market fetched
  at or before the label cutoff wins.
- **Proposed change, not yet reviewed (commit c4f3549b, another session):** the labeller does not ask a market whose
  latest recorded Gamma end date is more than one day after the pass (markets without a recorded end date are
  asked), and asks markets in end-date order, ended ones first. It is load control only; it needs the challenger's
  review before the pin (it could delay the first final record of a market that resolves early, before its end date).
  It does not affect the census.
- **Censoring.** A universe copy without a final record by the cutoff is censored. It is excluded from both primaries
  and counted. Sensitivity (not counted): unresolved skilled copies set to pay 0 (`censoring_pessimistic_R`). Labels:
  `censoring-sensitive` if that makes R <= 0 while R > 0; `differential censoring` if the skilled and control censored
  shares differ by more than 5 percentage points.
- **Missing data stays missing.** No sample, no signal. No capture, entry at the next capture (and out of universe if
  that is more than 6 h late). Coverage: if more than 20% of the window's expected 2-hourly samples were not read, the
  result carries `coverage-reduced`. Nothing is imputed or back-filled. A missing capture never gets a quote from
  another source.

## 7. Analysis (`copy_skilled_analysis.analyze`, q0543; runs once)

### 7.1 E026-N

- Sample: skilled copies, sidecar arm, L = 0, primary set, resolved.
- Statistic: `R_N = sum(net) / sum(stake)` (one share per copy, so this is P&L per dollar staked).
- One-sided p = the max of: event-cluster bootstrap (B = 10,000, seed 20261023), cluster-robust t by event with G - 1
  df, and two-way event x wallet cluster-robust t with min(G) - 1 df. Clusters = event id of the entry row (falls back
  to the signal's event id, then the market id).

### 7.2 E026-C

- Pairs: each primary-set, resolved skilled copy with at least one primary-set, resolved control. Controls are
  averaged within their parent.
- Statistic: `D = R_skilled - R_control` over the pairs. Same p rule (event bootstrap, event t, two-way t).

### 7.2a Dependence and clustering

- **Unit of dependence: the event.** Markets of one Polymarket event resolve together (mutually exclusive outcomes,
  shared news), and several skilled wallets often trade the same event. Every p value and interval is clustered by
  the event of the entry row (fallback: the signal's event id, then the market id). The bootstrap resamples whole
  events.
- **Wallets.** One wallet's copies share its style and information. The two-way event x wallet cluster-robust t
  (`V_event + V_wallet - V_event x wallet`, with `max(V_event, V_wallet)` if that is not positive) enters the p rule,
  and the wallet-day cap (10 primary-set copies per wallet per UTC day) limits one wallet's weight.
- **E026-C.** Pairs are clustered by the skilled copy's event. Controls are always in another event than their
  parent, but two parents' controls can share a control event; that control-side dependence is not in the
  clustering (open question 12). Because each pair's control mean averages up to 3 trades in up to 3 events, it is
  diluted, but not removed.
- **Not independent of LT2-LT4.** Same captures and samples (section 10.2); never pooled.

### 7.3 Family, floors and verdicts

- Holm over {E026-N, E026-C}, k = 2, alpha 0.05, one-sided (> 0).
- Availability floors (fixed): E026-N needs >= 200 copies and >= 40 events; E026-C needs >= 150 pairs and >= 40
  events. Below a floor the test is **Unavailable** (p set to 1 in the Holm step, still counted).
- Verdicts: **Supported (exploratory, prospective)** if Holm p < 0.05 and the estimate > 0. **Not supported (effects
  >= 0.03 $/$ excluded)** if the upper 95% bootstrap bound is below the materiality floor 0.03 per dollar.
  Otherwise **Inconclusive**.
- If E026-N is Supported but E026-C is not, the result carries `bias-consistent`.
- E026-N is already net of costs. There is no separate economics test.

### 7.4 Secondaries (descriptive, not counted)

Latencies 6 h and 24 h (and their control differences); entry-price bands of the copied token (long shot 0.05-0.35,
middle 0.35-0.65, favourite 0.65-0.95; copying a long-shot SELL lands in the favourite band); BUY vs SELL signals;
fee category; the large-print arm; the uncapped universe; the 24 h exit; schedule fee policy; touch-only (no impact);
equal-dollar mean; realised latency quantiles; skill-score terciles. None of them can change a verdict.

### 7.5 Power and MDE (planning only; pre-window counts and entry quotes, no payout read)

The planning census (`run_copy_skilled.py census`, queue draft q0544, section 8.2) replays the recorder on the
pre-window wallet-sidecar samples of `[2026-10-18T04:00Z, 2026-10-21T04:00Z)` (the sidecar exists from the
2026-10-18T04:39Z sample on) with the skill set rebuilt from HB1 history at the census start (the same set q0540 will
freeze: every HB1 outcome was known by 2026-10-15). It never opens a capture starting at or after 2026-10-22T00:00Z,
records no exit quote and fetches no resolution.

- **Rates.** Per day of covered time. Each usable sample (complete sidecar) is credited with the time back to the
  previous usable sample read (the census start for the first). A skipped sample (sidecar incomplete, never
  complete, files retired) does not advance a market's last-sent time, so its trades are first observed, and counted,
  in the next usable sample, exactly as in the window (section 4.1); crediting the gap to that sample keeps the rate
  per covered day. Trailing skipped samples are not credited. Beyond 500 trades per market a long gap loses trades,
  so a gap can only lower the rate. Skipped-sample counts are reported next to the gate result. Latency availability
  uses only batches whose entries are complete within the captures read (batch start + 1 h + L + 6 h <= last capture
  read).
- **Projection.** Primary set at L = 0 (sidecar arm), scaled linearly to 21 days: copies `n`, events, pairs and pair
  events. The event projection is linear and so an upper estimate (repeat events grow more slowly).
- **SD.** `SD = sqrt(mean(ask_j (1 - ask_j)))` over primary-set entries: the per-share outcome SD if prices are
  calibrated at entry.
- **MDE.** `MDE = (z_{1 - 0.05/2} + z_{0.8}) x SD x sqrt(deff / n) / mean stake` (Holm worst case alpha / 2,
  one-sided, power 0.8), in $ per $ staked.
- **Design effects (upper bounds, correlation 1 within a cluster):** `deff_event = sum m_e^2 / n` and the two-way
  bound `deff_2w = deff_event + deff_wallet - deff_event x wallet`. `deff = 1` is the lower bound.
- **E026-C.** `n = pairs`, SD inflated by `sqrt(1 + mean(1 / m))` (m = primary-set controls of the pair, at most 3),
  event design effect.

**MDE table** (filled 2026-10-21 from the committed census `live_tests_copy/census_q0544_2026-10-21.json`, sha256
`90adaea6d9edfaf19f502e56513e8d7a2ca01c27fae90884c6e6163326ec58bf`; counts and entry-quote levels only):

| quantity (21-day projection, sidecar, L = 0, primary set) | census value |
|---|---|
| usable days read; skilled signals per day | 2.882 days (35 samples, 0 skipped); 6,429 skilled signals = 2,230 a day (242 wallets, 3,769 markets) |
| primary-set copies n; events; wallets; top-1 / top-10 wallet share | census 1,294 (449 a day; 2,946 in the universe before the wallet-day cap; one per (wallet, market) is already applied at signal level), 650 events, 160 wallets, 3.0% / 26.9%; **projected n 9,428, events 4,736** |
| pairs; pair events; control SD inflation | census 1,200 pairs, 620 pair events; **projected 8,743 pairs, 4,517 pair events**; inflation 1.199 |
| SD per share; mean stake; mean cost per $ staked | 0.414; 0.571; **0.053** (0.030 per share) |
| deff_event; deff_2w | 3.97 (deff_wallet 21.35, deff_event x wallet 1.38); **23.93** |
| MDE E026-N at deff 1 / deff_event / deff_2w | 0.021 / **0.042** / 0.102 $ per $ |
| MDE E026-C at deff_event | **0.052** $ per $ |
| realised latency quantiles (L = 0, 6 h, 24 h); entry availability | trade-to-entry p10 / p50 / p90: L = 0 2.6 / 6.6 / 18.4 h; L = 6 h 8.6 / 12.6 / 24.3 h; L = 24 h 26.6 / 30.5 / 40.9 h. Receipt-to-entry median 1.8 h. Two-sided entry: L = 0 6,120 / 6,429 (95%); 6 h 5,271 / 6,040 (87%); 24 h 3,041 / 4,279 (71%) |
| gate decision (section 7.6) | G1 pass (9,428 >= 400; 4,736 >= 80), G2 pass (8,743 >= 300; 4,517 >= 80), G3 pass (0.042 <= 0.10): **register_k2** |

Census notes (facts, not design changes):
- **Latency.** The 2-hourly sample first sees a trade a median 4.5 h after it printed (trade age p10 / p50 / p90:
  0.7 / 4.5 / 16.3 h), so the realised trade-to-entry latency at L = 0 is a median 6.6 h, not the 1.5-2 h of the
  receipt-to-entry delay alone. L = 0 means "as soon as AREPO can know", and that is several hours.
- **Power.** The primary p is the maximum of the event bootstrap, the event t and the two-way t (section 7.2), so the
  two-way MDE (0.102 at the correlation-1 upper bound) is the conservative reading; the event MDE (0.042) is what G3
  checks. Both exceed the 0.03 materiality floor, so a "Not supported (effects >= 0.03 excluded)" verdict is unlikely;
  a null will most likely read Inconclusive. G3 passed, so no low-power label is attached.
- **Hurdle.** The mean conservative cost is 5.3c per dollar staked; E026-N needs a gross gain above that.
- **Mix.** Primary-set categories: sports 327, weather 322, other 123, culture 104, politics 102, unknown 83, finance 81,
  crypto 63. BUY share 0.89. Ask bands: long shot 312, middle 417, favourite 565. Median days to end 2.3.
- **Large-print arm (secondary):** 849 skilled signals in 3.0 days, primary set 117 (64 events, 21 wallets; top-1
  share 26.5%), projected 819.
- **Ordering disclosure (gates not blind).** The design session ran an earlier, uncommitted census of the same
  pre-window data. The gates entered the spec at 3dd2d7ef (2026-10-21 08:52Z) and this document at aba32281 (08:56Z).
  The time of the earlier run was not recorded and no artefact of it was found on the host (checked 2026-10-21 ~14:20Z);
  its numbers reached the owner by about 09:40Z (about 1,278 primary-set copies in 2.8 days, about 9,470 projected over
  21 days; MDE E026-N 0.042, E026-C 0.051 at the event bound), so it may have preceded the gates. The committed census
  q0544 ran later (12:22Z) at git commit 7d2eac8b, whose library code hashes equal the reviewed afac80d4 (only the
  runner differs), and is the one the gates were applied to. Every analysis threshold (floors and materiality floor
  since 7bf5c525, wallet-day cap since ce70ee1b) predates any census. So the gates were set with planning numbers in view. They sit far below them (G1 400 copies against about
  9,400 projected; G2 300 pairs against about 8,700), so they could not have been placed to pass narrowly, but the
  challenger should treat them as informed, not blind. This touches only power planning: no payout, exit quote or
  window data was seen.

Benchmark: the WS1 S2 gap (+21.7c vs +3.6c, about 18c per dollar) is the wallets' own P&L at their own price,
without latency or costs. A copy at L = 0 should keep only part of it. The mean conservative cost per dollar from the
census is the hurdle E026-N must clear before any gross gain shows.

### 7.6 Census gates (pre-declared 2026-10-21, before any census number; spec `census_gates`)

Gates are twice the analysis floors (section 7.3), leaving room for censoring (unresolved by the cutoff) and for rate
drift between the census and the window. They are applied once, to the census output, and are never changed after it.

- **G1** projected primary-set copies >= 400 and events >= 80.
- **G2** projected pairs >= 300 and pair events >= 80.
- **G3** planning MDE of E026-N with `deff_event` <= 0.10 $ per $ staked.
- Decision: G1 and G2 pass -> register E026-N and E026-C (k = 2). G1 passes, G2 fails -> E026-C is dropped before the
  pin (k = 1; `TESTS`, Holm k and the trials `n_tests` are changed in the code before the pin and re-reviewed; the drop
  is recorded in the ledger). G1 fails -> not registered as designed; any redesign (longer window, other arm) needs a
  written justification and a new review. G3 never blocks; a G3 failure adds the label
  `low-power (a null is uninformative)` to the registration and to every verdict.
- The gate result is always written: when nothing can be projected (no signal, empty primary set, no covered day)
  the decision is `do_not_register_redesign` with a reason. Gate checks compare unrounded projections.
- The census output (`census.json`, counts and aggregates only, no wallet hash) is committed with its sha256 before the
  challenger review and copied into the spec's `planning` block before the pin.

### 7.7 Economic check

E026-N is the economic check: it is already net of a conservative taker round trip at entry (half-spread, $100-tier
impact, conservative fee) and holds to resolution, so no exit leg is paid. Not modelled, and so disclosed as
optimistic: queue position, fills beyond the captured touch, fill failure between capture and order, stake sizes above
$100, and any copy crowding. Secondaries (descriptive): schedule fee policy, touch-only (no impact), 24 h exit (two
taker legs). A Supported E026-N would still be a paper result for one 21-day window; it is not a trading or profit
claim and would need its own prospective replication with a realistic execution model.

### 7.8 Causality and leakage controls

- Skill set: HB1 history only, outcomes known strictly before `t_freeze` (closedTime + 48 h), frozen write-once before
  the window, sha256 pinned; the recorder refuses another set.
- Signals: first observation only, receipt from the sample manifest, processed in start order; no back-fill.
- Controls: chosen inside the same batch from entry-time fields by a hash order; no outcome or later quote.
- Entries: first capture at or after the due time; universe flags and the wallet-day cap use entry-time fields and
  receipt order only.
- Labels: the earliest final Gamma record fetched by the cutoff; censored copies are counted, not dropped silently.
- Census: pre-window only (no capture at or after 2026-10-22T00:00Z, no exit, no payout); it reads nothing of the
  window and nothing of LT2-LT4's windows.
- No interim look: `status` prints counts only; the analysis refuses before `ANALYSIS_NOT_BEFORE` and on any pin
  mismatch.

### 7.9 Disclosures

- Coverage: sampled markets only (about 2,000 per sample), newest 500 trades per market, 2-hourly cadence (section
  4.1). Skilled wallets trading outside the sample are invisible.
- Population shift: the primaries use markets ending within 14 days of entry; long-dated trades are only in the 24 h
  exit secondary.
- Skill is taker skill measured relative to the trade price; it can be a price-level bias (section 1.2).
- Overlap with WS1 (same HB1 history; WS1 is development) and with LT2-LT4 (same data streams; never pooled).
- The census period (Sunday 10-18 to Wednesday 10-21) is three days; rates may differ in the window. The gates
  carry a factor-2 margin for this.
- Multiple-testing: 2 counted tests in this family (1 if E026-C is dropped by G2); secondaries are never counted.

## 8. Engineering

### 8.1 Code and tests

- `backend/astrolabe/research_lab/copy_skilled.py` (freezer, recorder, labeller; write-once gzip CSV, floats
  `%.17g`, atomic hard-link writes, `fcntl` lock, disk cap 1 GB).
- `backend/astrolabe/research_lab/copy_skilled_analysis.py` (costs, inference, Holm, verdicts, MDE).
- `backend/astrolabe/research_lab/model_specs/copy_skilled_v1.json` (the spec; sha256 pinned at registration).
- `backend/scripts/run_copy_skilled.py` (`freeze`, `run`, `label`, `analyze`, `status`, `census`).
- `backend/tests/unit/test_research_lab_copy_skilled.py` (synthetic data only).
- `battery2.KIND_RULES["copy_skilled"]`: one counted trials line, n_tests = 2.
- Queue drafts (not in `queue/jobs/`): `q0544_copy_census` (first; counts only), `q0540_copy_freeze_skillset`,
  `q0541_copy_collect`, `q0542_copy_label`, `q0543_copy_analyze`.
- The census options `run_once(capture_hi=..., exits=False)` are used by the census only; the registered recorder
  runs with the defaults (all captures, exits recorded).

### 8.2 Planning census and host dry run (q0544; CENSUS-GATED)

The census job is also the host dry run of the recorder code: it reports the history-load peak RSS (the q0540
memory), the recorder's own peak RSS measured in a child process (q0541 runs on the net lane with `mem_mb` 450, so
it must stay below 500 MB), wall times and store bytes. Work dir `data-dumps/research_lab/copy_skilled_census/work`
(deleted at exit), output `copy_skilled_census/census.json`; the real store `copy_skilled/` is never touched.

| item | value |
|---|---|
| history load + profiles: peak RSS, wall | 1,441.6 MB, 51.4 s (host, q0544) |
| recorder (child): peak RSS, wall, samples / captures read | q0544 peak not measured (see below); **q0545: 269.5 MB** (VmHWM, R1 code, one backlog pass of 35 samples / 41 captures); wall 236.5 s (q0544), 251.8 s (q0545); 72 print hours |
| store bytes for the census period (scaled to 21 days vs the 1 GB cap) | 7,069,695 B in 2.88 days, about 51.5 MB per 21 days (5% of the cap) |
| missing / retired samples in the census period | 0 / 0 |
| eligible / skilled wallets in the set | 35,587 / 3,559 |

**Recorder memory: measurement defect found 2026-10-21.** The census reported the recorder child's peak as 1,441.6
MB, exactly the parent's history-load peak. On Linux `ru_maxrss` carries the forking parent's peak across `exec`
(checked on the host: a child of an 800 MB parent reports 811 MB by `ru_maxrss` and 10 MB by `/proc/self/status`
VmHWM). So q0544 did not measure the recorder alone. The runner now reads VmHWM in the child (test with a 600 MB parent
ballast), and the diagnostic re-run **q0545** (same pre-window period, counts only, gates not re-applied; output
`census_q0545_memcheck.json`) measures it before the 2026-10-22T03:30Z retention run. q0541's `mem_mb` (450, net lane,
address-space cap 900 MB) is confirmed or re-sized from that number before the pin; if the recorder needs 500 MB or
more, it cannot use the light-job exemption and the queue entry must say so.

Deadline (retention, not design): the 2026-10-18 and early 10-19 sample files are retired by the 2026-10-22T03:30Z
archive run and jobs with `mem_mb` >= 500 cannot start 02:45-05:30Z, so q0544 must start before 2026-10-22T02:45Z. A
later run is still valid: retired samples are recorded missing and are not credited unless a later usable sample
carries their trades (section 7.5 Rates); the skipped counts are printed next to the gates. Promote by about 01:30Z
so that the run (history load plus about 36 samples; wall time not yet measured on the host) finishes before 03:30Z.
A killed attempt leaves a work dir marked by `.copy_skilled_census_work`; the retry removes only a dir carrying that
marker and refuses any other non-empty dir.

## 9. Registration steps and pins

1. Census q0544 (section 8.2; counts only); commit `census.json` and its sha256; fill the CENSUS-GATED values;
   apply the section 7.6 decision.
2. Challenger review of this document and the code; fixes; re-check. A code fix after the census does not need a
   second census unless it changes what the census measures.
3. Freeze job q0540 (before `t_freeze`). Copy the manifest sha256 into `skillset_sha256`.
4. Fill `code_sha256` (sha256 of each file in `CODE_FILES`, with the `SPEC_SHA256 = ...` line normalised).
5. Pin `SPEC_SHA256` in `copy_skilled.py` to the spec file's sha256.
6. Ledger registration commit (at least 24 h before `REGISTERED_UTC`), registry entry, promote q0541 and q0542, then
   q0543 with `not_before`.
7. From the pin on, lines with receipt in the window are `prospective_confirmation`. The analysis keeps only lines
   with that role, `spec_sha` = the pin and `code_sha` = the pinned recorder hash, and refuses to run if any pinned code
   hash differs.

## 10. Stop rules, overlaps and embargo

### 10.1 Stop rules

- No interim look at prices, P&L or payouts. `status` prints counts only.
- The test runs to END whatever the counts. If skilled signals run below one third of the census rate after 7 days
  (counts only), the ledger notes "likely Unavailable"; nothing else changes.
- Integrity stop: any change to a pinned file after the pin makes the analysis refuse. A fix then needs a new spec,
  a new E-number and a new window. Old lines keep their outcome.
- Operations: the recorder exits 75 when nothing is new; after 48 consecutive tempfails (about a day without new
  samples) the queue marks it failed. Re-promotion resumes; the gap stays missing and is counted.
- Disk: the recorder refuses above 1 GB in `copy_skilled/`. No retention rule may cover `copy_skilled/` before the
  analysis is committed.

### 10.2 Overlaps (disclosed)

E026 reads the same trade samples and captures as LT2-LT4 (E012-E024) and the live-print stream. It never opens their
stores, never reads their outcomes and is never pooled with them. WS1 used the same HB1 history; WS1 was
development and is not confirmed by E026.

### 10.3 Embargo (signal engine, proposed; `config.EMBARGO` is not edited here)

The engine's `wallet_skill` family and any wallet-copy feature measure the same quantity. Proposed: extend the
`wallet_skill` / `wallet` embargo to cover E026 until its analysis is committed:
`{"token": "wallet_skill", "until": "2026-12-07T00:00:00Z", "tests": ["E026-N", "E026-C"]}` (the later of this and the
existing 2026-11-18 E024 embargo applies). Prospective prediction writing may continue; isolated scoring of the family
waits.

## 11. Open questions for the challenger

1. **SELL signals.** A skilled wallet's SELL may close a position opened before the window (taking profit), not state
   a view. Copying it buys the complement. Should the primary be BUY-only, with SELLs secondary? (Current: both, with
   BUY vs SELL as a secondary.)
2. **Primary latency.** L = 0 is "the next 2-hourly capture"; the census realised trade-to-entry latency is a median
   6.6 h (p10 2.6 h, p90 18.4 h), mostly the trade's age when the sample first sees it.
   Is that the right primary, or should the primary be 6 h (more robust to capture timing)? There is no faster quote
   stream for the full universe.
3. **Short-dated universe.** Only markets ending within 14 days of entry are in the primaries (they can resolve before
   the cutoff). Skilled wallets may trade long-dated markets more. Is the population shift acceptable, with the 24 h
   exit as the all-dated secondary?
4. **Controls.** Controls are any non-skilled wallet (mostly unprofiled). Should they be restricted to
   eligible-not-skilled wallets, which would separate "skill" from "being a frequent profiled trader" but cut the pool?
5. **One copy per (wallet, market).** Is the first in-window trade the right unit, given WS1 measured skill on whole
   positions (all trades in a market)?
6. **Frozen HB1-only set.** The set uses only HB1 history (12.7k markets, last trade 2026-10-12). Live sidecar outcomes
   since then are not used. Is a frozen, older set the right test of persistence, or should a set frozen from HB1 plus
   live outcomes known before `t_freeze` be used (more wallets, more engineering, more leakage surface)?
7. **Floors, gates and window.** Are the floors (200 copies / 150 pairs / 40 events), the gates at twice the floors
   (section 7.6) and the 21-day window adequate given the census MDE (section 7.5)? Should G3 (MDE <= 0.10) block
   instead of only labelling?
8. **p rule.** p = max(event bootstrap, event t, two-way t). Conservative; acceptable?
9. **Wallet-day cap 10.** Does it control one-wallet domination enough, given the two-way clustering?
10. **Fees.** Conservative policy (max of schedule and docs, 7% if unknown). Should the primary use the schedule
    policy, which is what a taker would pay?
11. **Toxicity use of P1.** Creative round 11 noted skilled-wallet presence as a maker-toxicity signal. Not in scope
    here; should it be a separate design?
12. **Control-side event dependence (E026-C).** Pairs are clustered by the skilled copy's event only. Two pairs whose
    controls sit in the same event are dependent through it. Options: cluster on the connected components of the
    (skilled event, control event) graph (may collapse into few large components), a three-way variance, or accept
    the dilution argument (section 7.2a). Which?
13. **Census representativeness.** Three days (Sunday to Wednesday) feed a linear 21-day projection. Is the factor-2
    gate margin enough, or should the projection use the lowest single census day?

## 12. Draft ledger block (DRAFT, not registered, not counted)

> ## E026 — Copy skilled wallets with latency: DRAFT pre-registration (not registered, nothing counted)
> - **Design:** `docs/research_lab/LIVE_TESTS_COPY.md`. Code `copy_skilled.py`, `copy_skilled_analysis.py`,
>   `run_copy_skilled.py`; spec `model_specs/copy_skilled_v1.json` (sha pinned at registration); queue drafts q0540
>   (freeze), q0541 (recorder, net lane), q0542 (labeller, net lane), q0543 (analysis, not before 2026-12-06T12:00Z).
> - **Basis:** WS1 P1 persistence (DEVELOPMENT; S2 P&L per dollar of S1-skilled wallets +21.7c vs +3.6c); WS1 P2-P4 null
>   (skilled flow adds nothing over generic flow); prior-art gaps 1 and 7.
> - **E026-N:** net P&L per dollar of paper copies of frozen-skilled wallets' new taker trades (wallet sidecar), entered
>   at the first capture at or after receipt (L = 0), held to resolution, conservative taker costs; > 0.
> - **E026-C:** E026-N minus the same ratio of matched non-skilled controls (same sample, side, price, age and
>   time-to-end cells, other event); > 0.
> - **Family:** Holm k = 2, one-sided, alpha 0.05; p = max(event bootstrap, event t, two-way event x wallet t).
>   Counted tests 2. Window: receipts `[2026-10-25T00:00Z, 2026-11-15T00:00Z)`; label cutoff 2026-12-06T00:00Z; single
>   analysis on or after 2026-12-06T12:00Z. Planning MDE: section 7.5 (CENSUS-GATED); census gates section 7.6
>   (fixed before the census; decision recorded here before the pin).
> - **Status:** DRAFT; awaiting challenger review. No line is `prospective_confirmation` until the spec sha is pinned.

## 13. Proposed registry entry (stage "designed"; `registry.json` is not edited here)

```json
{
 "id": "E026",
 "title": "Copy skilled wallets with latency (live test)",
 "plain": "A live check of whether copying wallets that were skilled in the past still pays after the delay before AREPO sees their trades and after taker costs, and whether they beat ordinary traders making the same kind of trade. Paper copies only; nothing is traded.",
 "batch": "COPY",
 "family": "wallet",
 "stage": "designed",
 "status": "draft",
 "verdict": "pending",
 "effect": null,
 "next": "Challenger review of the design; if accepted, registration before 24 Oct 2026, collection 25 Oct to 15 Nov 2026, single analysis after 6 Dec 2026",
 "next_date": "2026-10-23",
 "candidate": false,
 "sources": {
  "verdict": "docs/research_lab/LIVE_TESTS_COPY.md (DRAFT)",
  "next": "docs/research_lab/LIVE_TESTS_COPY.md sections 2 and 9"
 },
 "stage_results": {
  "designed": "pending"
 },
 "reached": []
}
```

## 14. Challenger R1 response (2026-10-21; governs where any earlier text differs)

Review: `reviews/E026_CHALLENGER_R1_2026-10-21.md`, **ACCEPT_WITH_FIXES**. Code fixes in d11ba0a0 (52 tests pass,
1 skipped while the spec is a draft). `register_k2` stands: every analysis threshold predates any census, and the gates
pass by more than 20x. No floor, materiality floor, gate, alpha, latency, window date or wallet-day cap was changed.

1. **Negative verdict (7.3).** "Not supported (effects >= 0.03 excluded)" now uses the widest upper bound, max(event
   bootstrap 97.5%, R + t_0.975 x se_event, R + t_0.975 x se_twoway), plus for E026-C the combined-event bootstrap and t
   of item 8. So the negative verdict is read at least as conservatively as the positive one.
2. **Counting (7.3, 9).** q0543 runs with `--trials ../docs/research_lab/trials.jsonl`. With no data, the analysis
   returns both tests **Unavailable** (p = 1) inside a Holm block with k = 2, so the counted trials line is always
   well formed.
3. **Pins (5, 9).** The cost-impact table (`cost_model_calibration_v1.json`) is pinned by sha256 in the spec
   (`impact_table_sha256`), and the analysis refuses on mismatch. A pinned spec is refused if `skillset_sha256`, any
   `code_sha256` entry or `impact_table_sha256` is missing. Entries and resolutions are filtered by `spec_sha` /
   `code_sha` like signals.
4. **Frozen shared modules.** `wallet_skill.py`, `wallet_skill_dev.py`, `costs.py` and the impact table are frozen
   from the pin until 2026-12-07. A unit test asserts every pinned hash (skipped while DRAFT), so any edit fails the
   suite. The analysis q0543 runs from a worktree at the pinned commit. The registration adds this note to the ledger
   and to CLAUDE.md / AGENTS.md.
5. **Memory (6, 8.2).** The labeller and analysis read only the columns they need. The recorder no longer rebuilds
   every (signal, latency) pair per capture; only pending rows are materialised and the list is kept incrementally
   (each due item always gets a line, `absent` if the market is missing). Measured on a synthetic store 7.3x the census
   (188k signals, 738k entry / exit rows, 57k resolutions; Mac `ru_maxrss` in a fresh child): recorder 353 MB
   (capture-only pass) to 448 MB (pass with one 240k-row sample) -> q0541 `mem_mb` 480, `as_cap_mb` 4000; labeller
   302 MB -> q0542 `mem_mb` 400, `as_cap_mb` 4000; analysis (B = 10,000) 1,222 MB -> q0543 `mem_mb` 1500, `as_cap_mb`
   6000. The q0541 margin is about 9%; q0545 measures the recorder on the host (VmHWM) before the pin, and a backlog
   pass of up to 40 samples is not yet measured.
6. **End-date gate (6).** The labeller's end-date gate is switched off from the label cutoff - 7 days (every due
   market is asked). Each pass writes a `label_pass` line to `passes.jsonl` with due, gated, due-unasked and asked
   counts, so throughput censoring can be audited.
7. **Operations (10.1).** q0541 `not_before` = 2026-10-25T00:00Z and q0542 `not_before` = 2026-10-25T06:00Z, so
   neither runs into 48 tempfails before the window opens. If either shows `failed`, it is re-promoted within 48 h
   (sample retention is 3 days); the gap stays missing and is counted.
8. **Control-side event dependence (7.2, Q12).** For E026-C each pair's linearised score is split into a skilled piece
   (the skilled copy's event) and control pieces (each control's event, weight 1/m), summed by event regardless of
   side. The cluster-robust t on those combined events (G - 1 df) and the matching event bootstrap join the max-p rule
   and the upper bound of item 1.
9. **Matching (4.x, Q1).** The control matching cell gains `prior_visible`: the wallet has a strictly earlier trade in
   the same market among the sample's raw rows, computed before the seen-before filter (causal: only rows at or before
   the receipt). A skilled first-seen open is matched to a control first-seen open, and an add / close to an add /
   close. A control whose event id is empty is never accepted as "another event". These change control and pair counts
   relative to the census (G2 passed by 29x; disclosed, no second census needed for the gates).
10. **Document.** Corrected in fb65c56f (trade age, latency, census commit, ordering disclosure).

Recommended items done: freeze checks (eligible / skilled = 35,587 / 3,559 and max known outcome ts before
2026-10-18T04:00Z, from spec `skill.expected`; the freeze refuses before writing on a mismatch and records the checks in
the manifest); `uma_status` counts in the analysis output; descriptive secondaries (E026-C censoring bounds,
leave-top-skilled-wallet-out R, eligible-not-skilled control subset). Not done: the overlapping-capture guard (whether captures
can overlap is not yet verified; passed to the R1 re-check). The primary is
equal-share (copies weighted by price); the equal-dollar ($100 per copy) mean is a secondary. Disclosed: the
receipt-order wallet-day cap removes 56% of universe copies and favours early-UTC samples for high-volume wallets.

**R1 re-check** (`reviews/E026_R1_RECHECK_2026-10-21.md`): **R1_FIXES_OK_WITH_NOTES**, no required item. Applied after it:
- every recorder and labeller pass checks the running code against the pinned `code_sha256` and fails loudly
  (`COPY_SKILLED_CODE_MISMATCH`, non-zero exit) instead of writing rows the analysis would drop;
- a capture that is not complete yet and started less than 4 h ago blocks every later capture in the recorder, so an
  entry always lands on the first capture starting at or after its due time even if captures ever overlapped (today
  they cannot: `arepo_pass.sh` holds the collector `flock`);
- the "frozen until 2026-12-07" note for the pinned shared modules goes into the ledger, CLAUDE.md and AGENTS.md with
  the registration commit.
Disclosed (not fixed): `prior_visible` sees only the current sample's rows, so a control wallet whose earlier trade in the
market fell out of the sample can be matched as a first-seen open; rows dropped by trade normalisation do not count as
prior trades.

**q0545 memory re-check (2026-10-21 15:14Z, counts only):** `live_tests_copy/census_q0545_memcheck_2026-10-21.json`,
sha256 `24a50571acb8d09367fa23ec6da0f7d1d469eeb7519dbd5262710af0d682ed7c` (equal on the host). Recorder peak **269.5 MB**
(VmHWM) for a single pass over the whole 35-sample, 41-capture census backlog, so q0541 `mem_mb` 480 holds (the Mac
synthetic 7.3x-store pass peaked at 448 MB). Reproduction: skill set (35,587 / 3,559), 6,429 skilled signals and the L = 0
primary set (1,294 copies, 650 events, 160 wallets) equal q0544 exactly. By design (R1 fix 9 and the empty-event rule)
controls moved 18,543 -> 17,751 and primary pairs 1,200 -> 1,167 (620 -> 616 pair events; projected 8,503 pairs, MDE
E026-C 0.053). The gate decision is not re-applied; it would be unchanged.
