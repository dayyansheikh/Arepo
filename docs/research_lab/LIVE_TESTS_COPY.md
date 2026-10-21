# Live test E026: copy skilled wallets with latency — DRAFT pre-registration

Research tooling only. AREPO never trades. A "copy" here is a PAPER position priced from quotes AREPO already captured.
No order is sent, no wallet is called informed or an insider, and nothing here is an edge claim. Wallets are HMAC hashes
(`wallet_sidecar.hash_wallet`, key on the host only). No raw address is read, stored or printed. The skilled-set file
holds hashes only and is never committed.

**Status: DRAFT.** Not registered, nothing counted. Every line written before the spec pin is
`prospective_unregistered` and is never analysed as a confirmation. The challenger review (section 11) comes first.

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
- **Latencies:** L = 0 (primary: the next capture after receipt, in practice about 1.5-2 h later), 6 h, 24 h.
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
  observation). A sample that never completes, or whose files were retired before it was read, is recorded as
  missing (write-once marker) and never back-filled.
- **Coverage limits (disclosed).** Only sampled markets (about 2,000 per sample). Only the newest 500 trades per
  market: in a busy market, trades between two samples can be missed. Trade age at receipt (receipt minus trade ts)
  ranges from minutes to about 2 h, more when trades are older than the previous sample.

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
  (`max(schedule, docs)`, unknown category 7%, fees off only if the market says so).
- `net per share = pay_j - ask_j - impact - fee`; `stake per share = ask_j + impact` (a $100 stake scale).
  The cost term equals `costs.cost_check(...).taker_resolution_cost_ps` (pinned by a unit test).

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

### 7.5 Power and MDE (planning only; development and pre-window counts, no payout read)

The planning census (`run_copy_skilled.py census`, section 8) replays the recorder on pre-window trade samples and
captures (window ending before 2026-10-22T00:00Z) with the same frozen set. It reads counts and entry quotes only.
SD per share = `sqrt(mean(ask (1 - ask)))` over universe entries (the outcome SD if the price is calibrated).
MDE = `(z_{1-0.05/2} + z_{0.8}) x SD x sqrt(deff / n) / mean stake` (Holm worst case alpha / 2, power 0.8). The design
effect uses intra-event correlation 1 (upper bound, `sum m^2 / sum m`) and 1 (lower bound). For E026-C the SD is
inflated by `sqrt(1 + 1/3)` for 3 averaged controls.

MDE table: **to be filled from the census (section 8.2)**.

Benchmark: the WS1 S2 gap (+21.7c vs +3.6c, about 18c per dollar) is the wallets' own P&L at their own price,
without latency or costs. A copy at L = 0 should keep only part of it.

## 8. Engineering

### 8.1 Code and tests

- `backend/astrolabe/research_lab/copy_skilled.py` (freezer, recorder, labeller; write-once gzip CSV, floats
  `%.17g`, atomic hard-link writes, `fcntl` lock, disk cap 1 GB).
- `backend/astrolabe/research_lab/copy_skilled_analysis.py` (costs, inference, Holm, verdicts, MDE).
- `backend/astrolabe/research_lab/model_specs/copy_skilled_v1.json` (the spec; sha256 pinned at registration).
- `backend/scripts/run_copy_skilled.py` (`freeze`, `run`, `label`, `analyze`, `status`, `census`).
- `backend/tests/unit/test_research_lab_copy_skilled.py` (synthetic data only).
- `battery2.KIND_RULES["copy_skilled"]`: one counted trials line, n_tests = 2.
- Queue drafts (not in `queue/jobs/`): `q0540_copy_freeze_skillset`, `q0541_copy_collect`, `q0542_copy_label`,
  `q0543_copy_analyze`.

### 8.2 Planning census and host dry run

To be filled from the read-only host dry run (`/tmp/copyskill`, deleted afterwards).

## 9. Registration steps and pins

1. Challenger review of this document and the code; fixes; re-check.
2. Host dry run of the final code (section 8.2).
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
2. **Primary latency.** L = 0 is "the next 2-hourly capture", so the realised trade-to-entry latency is about 2-4 h.
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
7. **Floors and window.** Are the floors (200 copies / 150 pairs / 40 events) and the 21-day window adequate given
   the census MDE (section 7.5)?
8. **p rule.** p = max(event bootstrap, event t, two-way t). Conservative; acceptable?
9. **Wallet-day cap 10.** Does it control one-wallet domination enough, given the two-way clustering?
10. **Fees.** Conservative policy (max of schedule and docs, 7% if unknown). Should the primary use the schedule
    policy, which is what a taker would pay?
11. **Toxicity use of P1.** Creative round 11 noted skilled-wallet presence as a maker-toxicity signal. Not in scope
    here; should it be a separate design?

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
>   analysis on or after 2026-12-06T12:00Z. Planning MDE: section 7.5.
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
