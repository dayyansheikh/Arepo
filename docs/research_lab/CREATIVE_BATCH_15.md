# Creative batch 15 (CB15): election-night reporting-order drift (one-night case study; one night is one cluster), the pair at birth

`evidence_role: prospective` (CB15-E, a single pre-registered night; CB15-P Stage 2) / `exploratory_historical`
(CB15-P Stage 1) | status: **DRAFT-REVISED after challenger round 1 (CB15-E REVISE, 4 blocking; CB15-P REVISE, 2
blocking; CB15-L WITHDRAWN uncounted; 11 items: 8 adopted, 3 adopted with a stated modification, none rejected;
§9-§10). Nothing frozen, nothing queued, no code.** Drafted 2026-10-19 05:16 UTC+1 (2026-10-19T04:16Z) on parent
`b21060c` and committed as `2920504`; round-1 response 2026-10-19 05:32 UTC+1 (2026-10-19T04:32Z; §10). Every round-1
change tightens or clarifies; no floor, threshold, gate, alpha or cap was relaxed. Nothing was fetched or written for
CB15 beyond the 9 counts-only keyless GETs of §0.3. **No CB15 quantity was computed:** no sign, drift, gap, birth order,
slope, net or resolution. The C1 birth-order census (a host query) was **not** run; it is job q0347.

This file turns two round-6 ideas from `CREATIVE_HYPOTHESES_2026-10-20.md` into declared, falsifiable tests: **CH129**
(election-night reporting-order drift, 2026-11-03) as **CB15-E** and **CH130** (the pair at birth) as **CB15-P**. It
records why **CH125** (leaderboard incumbency hazard) is not a test in this batch (§0.4; withdrawn uncounted in round 1).
It follows `CREATIVE_BATCH_14.md` (CB14) and `CREATIVE_BATCH_13.md` (CB13) in structure and rules. "As CB14 §x" means
that rule applies unchanged, including the challenger fixes and the CB13-CB10 rules it cites. CB4 amendment A-C1 and the
CB10 §2.3 small-G rule govern clusters.
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim. AREPO never
  trades. Every P&L is a paper rule at recorded prices (prints or books).
- Test tables bind once the CB15 declaration hash is committed (`model_specs/cb15_v1.json`), after the challenger round
  (§9-§10) and a code-against-design freeze check. Rules are fixed in `seals/cb15_rules.json` before the first CB15 job.
  **Both files are hashed per part (`common`, `E`, `P`)**, so E can freeze on its calendar without waiting for P, and
  no rule of one part changes after the other part's read.
- **CB15-E is calendar-forced.** Its rules part, GE0 files, race map, collector, tests and smoke must exist, and part E
  must be frozen, by **2026-11-01T12:00Z** (§1.2, §6). Otherwise E1 and E2 are "not run (calendar)", counted with p = 1.
- **Lanes.** P's Stage-1 inputs are keyless public fetches (`net` lane, **priority 5-9, below every CB6-CB14 job**).
  **Declared exception (round 1 item 4):** E's three pre-freeze `net` jobs (q0341 census, q0343 smoke, q0344 pre-gate;
  ≤ 730 requests together, ≤ 20 min) run at **priority 99**, and the coordinator **holds every other `net` promotion for 2 h
  before each scheduled start** (lanes do not pre-empt; drafts at priorities 32-49 exist). If a hold cannot be placed, the
  coordinator runs the job as a one-shot command with the same argv once the running `net` job ends. Censuses, gates and
  screens run on `cpu`. The E collector (q0345) and the P birth watcher (q0352) run as cron jobs outside the lanes, as
  CB14 q0310. **No CB15 object is bound to `T_seal`.**
- **Queue ids q0340-q0379, one id per job, no letter suffixes.** CB14 §0.1 reserves q0323-q0339, so CB15 starts at
  q0340. Used: q0340-q0353; **q0354-q0379 reserved** (the withdrawn L ids are not re-used by CB15). Specs are drafts
  **in this document only** (§4).
- **Naming.** Roots `history/h15_elect_live` (E), `history/h15_birth` and `history/h15_birth_live` (P); outputs under
  `research_lab/creative_batch15/`; GE0 source archive under `research_lab/creative_batch15/ge0_sources/` (§CB15-E).

## 0. Summary, selection and scope

| Rank | Family | Hypothesis | Counted tests | Stage 1 data | Stage 2 data | Queue ids |
|---|---|---|---|---|---|---|
| 1 | **CB15-E** election-night reporting-order drift, **one-night case study; the night is one cluster** (CH129) | in 2026 US general-election races (Senate, Governor, House) listed on Polymarket, a state sign frozen before the night from the state's vote-mode counting order and the archived 2022/2024 direction of the late count predicts the direction of the D-terms mid drift from `t_a` = the state's last poll close + 90 min to `t_a` + 12 h, **within hourly closing-time strata** (E1, stratified balanced drift ≥ +5c); buying the predicted side at the recorded ask at `t_a` and selling at the recorded bid at `t_b` pays after fees (E2, ≥ +1.0c per share) | E1 (stratified balanced drift), E2 (economic, recorded books) | **prospective, one night**: the E collector (CLOB `POST /books` on the :00/:10 grid, every 60 s in the night window, receipt-timed) on a race map frozen by 2026-11-01T12:00Z | none in CB15 (a pass yields a registration draft for the next general-election night) | q0341-q0346 |
| 2 | **CB15-P** the pair at birth (CH130), **selected on lifetime volume** | on the audited C1 Kalshi-Polymarket pairs where Kalshi opened ≥ 24 h before Polymarket's **first print**, the gap `g_d` = Kalshi mid − Polymarket's last print at `t_d` = first print + 10 min predicts Polymarket's move over the next 24 h (P1, slope ≥ 0.30, and larger than the same pairs' slope 7 days later); buying toward Kalshi at recorded prints when `|g_d| ≥ 5c` and exiting at 24 h pays after fees (P2, ≥ +1.0c per share) | P1 (slope), P2 (economic, recorded prints) | the C1 set's metadata on the host (birth-order census, no fetch) + fresh `h15_birth`: Data API prints from the first print, Kalshi 1-minute candlesticks, CLOB `prices-history` after the first print only; every unit ends before 2026-10-12 | prospective birth watcher from `max(P freeze + 1 d, 2026-11-04T00:00Z)`, causal selection: P1-rep, P2-rep at recorded books; **only P-rep can lead to Stage P** | q0347-q0353 |
| - | CH125 leaderboard incumbency hazard | **not a test (withdrawn uncounted, round 1):** the archived leaderboard pages hold no table, and the planning MDE is above the power gate (§0.4) | none | | | next batch, with a fresh design |

**Counted: 4 fixed (E1, E2, P1, P2) + up to 2 conditional (P1-rep, P2-rep) = 4-6** (§2.5). **k1 = 4.** The change from
the draft's 6 comes only from the L withdrawal (no L outcome, price or leader was seen), not from any power or Holm
consideration. The budget is fixed now. No CB15 test is added after any CB15 read. **Honest expectation:** E runs only
if the calendar holds and both signs share enough closing-time strata (identifiability, §CB15-E); even then it is powered
for about 3× its floor. P probably fails its population gate.

### 0.1 Queue id mapping (one id per job)

| Id | Job | Family | Earliest commit |
|---|---|---|---|
| q0340 | `cb15_exclusion_keys` (CB14 q0302 key file + CB14 frames + seal copies, **with per-key source attribution**) | P (E: robustness only) | after CB14 q0302 completes (or its ledger stop record) |
| q0341 | `cb15_e_census` (counts only: active 2026 general-election races on Gamma by office and state; national control markets; completeness walk) | E | after the `common` + `E` rules parts are committed; **priority 99 + 2 h hold** |
| q0342 | reserved: GE0, the archived sign table, poll-close table, party map and sign × closing-hour cross-table (network-enabled compilers + `science-reviewer` audit; repo step, no queue job) | E | - |
| q0343 | `cb15_smoke_E` (≤ 30 requests; stored bytes per pass; cron pause/resume dry run) | E | after the E collector and smoke code exist; **priority 99 + 2 h hold** |
| q0344 | `cb15_e_pregate` (gates GEI, GEC, GEP; one `/books` pass for band counts) | E | after GE0 is committed and q0343 PASS; **priority 99 + 2 h hold** |
| q0345 | `cb15_e_live` (cron collector, 2026-11-02T12:00Z to 2026-11-06T00:00Z) | E | after the E freeze; installed by 2026-11-02T00:00Z |
| q0346 | `cb15_screen_E` (E1, E2) | E | after 2026-11-06T00:00Z |
| q0347 | `cb15_p_birth_census` (counts only, no network: birth order on the C1 metadata; gate GPB) | P | after q0340 |
| q0348 | `cb15_smoke_P` (≤ 30 requests; reach to the first print) | P | after the P rules part and smoke code exist |
| q0349 | `cb15_p_data` (Gamma metadata incl. lifetime `volume`, Data API prints from the first print, Kalshi candlesticks, `prices-history` after the first print) | P | only after q0347 PASS and q0348 PASS |
| q0350 | `cb15_census_P` (counts only; gates GP, GPP) | P | after q0349 |
| q0351 | `cb15_screen_P` (P1, P2) | P | after the P freeze |
| q0352 | `cb15_p_live` (birth watcher, cron) | P | after the P freeze; not before 2026-11-04T00:00Z |
| q0353 | `cb15_rep_P` | P | only if P1 or P2 advanced; after `T15_P2_end` |
| q0354-q0379 | reserved | - | - |

### 0.2 Selection and scope

**Ranking rule.** As CB14 §0.2, with this brief: (a) the round-6 "next in line" ideas the brief names; (b) the calendar
first (E cannot wait); (c) side-free and wallet-free designs. **No CB15 statistic reads the Data API `side` field or any
wallet field.**

**What the drafting session read (2026-10-19T03:40-04:16Z).** CLAUDE.md, AGENTS.md; the ledger head (E009/E010 fixed
end 2026-11-03T00:00Z); mission §4; round 6 §0 facts 9, 12, 13, §2 (CH125, CH129, CH130), §3-§5; CB14 §0-§8 in full;
CB13's structure; CB12 §0, §1.1-§1.3 (CB12-X, the C1 reproduction call, the CB12 key union that includes `matches.json`
ids); CB11 §0 (CB11-P frame window); `CROSS_VENUE_STUDY.md` §1-§3 and §10; `CROSS_VENUE_LIVE.md`;
`run_cross_venue.stage_match` (the fields of `matches.json`); `EXECUTION_COSTS.md` line 39. Round 1 (§9) added the
queue's current draft priorities (q0085 at 45, q0103b and q0111 at 41, q0164-q0167 at 46-49, q0201-q0205 at 32-34).
- Prior work: no AREPO test has an election-night object or a listing-time (birth) object on cross-venue pairs. CB12-X
  (closed: X1 not identifiable) and CB5-K used the C1 pairs near resolution; E010 (live, sealed to 2026-11-03) uses the
  gap at 1 h and 6 h on live pairs.
- `battery2.cumulative_count()` (`battery2-count-v1`) = **1,232** on HEAD at drafting. Not stable; every counting CB15
  job records **the value at its run, after the host union**.

**Premises corrected or fixed by the probes, reads and round 1 (they shape this design).**
1. **The CLOB batch endpoint works keyless** (P9: `POST /books` returned two books with `bids`, `asks`, `timestamp`,
   `last_trade_price`). A 60-s election-night collector needs one request per ≤ 100 tokens (cap unverified; smoke).
2. **Reporting-percentage feeds are not keyless** (AP is keyed; state feeds vary and were not probed; round 6). E
   anchors its windows on each state's **last official poll-closing time**, not on a reporting share.
3. **House races exist in number** (P7: "House 2026" 457 results). All races of a state share its counting order, so
   **the state is E's unit of inference**.
4. **Closing time confounds the sign (round 1 item 1).** Windows are per state and closing times run 00-06Z; a national
   repricing at one clock time hits some windows and not others, and late-count direction clusters by region (and so by
   time zone). E therefore compares signs **within hourly closing-time strata only**, and checks the drift net of the
   national chamber-control market in logits.
5. **`prices-history` is not a point-in-time record of trades (round 1 item 9).** It is resampled, and before the first
   trade it can be seeded at 0.5, which makes `Δ ≈ g_d` by construction. P's birth, `p_d` and the gap are therefore
   **prints**; `prices-history` is used only after the first print.
6. **The C1 set is selected on lifetime volume (round 1 item 10)** (Polymarket event volume ≥ 20k, Kalshi ≥ 5,000
   contracts, ≥ 200 usable steps near resolution): future information at `t_d`. P1/P2 carry the label "selected on
   lifetime volume"; the P watcher's selection is causal.
7. **`matches.json` holds `k_open` and `p_start`**, so the birth-order census needs no fetch; its `p_end` is
   `closed_time` where present (hindsight) and is **never** read. **CB12's key union includes the C1 ids**, so P drops
   keys by source (§1.3). **CH129's ex-post 2024 audit is dropped** (it reads 2024 race markets inside CB11-P's frame
   window `[2024-07-01, 2026-09-01)` and is hindsight-fitted).

US daylight saving time ends on **2026-11-01**, so Eastern Time is UTC−5 on election night.

### 0.3 Feasibility probes (counts only; 9 keyless GETs; nothing stored)

Run from the Mac (scripts in `/tmp/cb15probe/`, not committed), `User-Agent: arepo-research-probe/1.0 (read-only
counts; https://www.arepolabs.com)`, paced ≥ 1.5 s. **No price, outcome, title, leader name or token id was printed or
stored.** Disclosed exposure: event counts and end-month counts of active election events; Wayback capture counts; HTML
marker counts of two captures **dated inside the withdrawn L window** (2025-10, 2026-01; no table was present, so no
leader was seen; recorded for any later L design, round 1); the key names of two order books. No host probe ran.

| # | Request(s) | Finding |
|---|---|---|
| P1-P2 | Wayback CDX `lmarena.ai/leaderboard*`, 2023-2026, daily collapse (1) | 6,140 capture-days in 2025 and 1,359 in 2026 across all URLs under the prefix |
| P3-P4 | Wayback CDX `huggingface.co/spaces/lmarena-ai/chatbot-arena-leaderboard*` (1) | 123 capture-days in 2024, 275 in 2025 |
| P5 | one capture of `lmarena.ai/leaderboard` (2026-01-14) (1) | 264 KB; 0 `<tr>`, no server-rendered payload, 0 four-digit numbers |
| P6 | CDX of `lmarena.ai/leaderboard/text` 2025-2026 + one capture (2025-10) (2) | 75 capture-days (2025-05 to 2026-01); the capture has 0 `<tr>`, 0 `<td>`, 0 score-like numbers |
| P7 | Gamma `public-search?q=House 2026&events_status=active` (1) | `totalResults` **457**; first page 50 events, 592 markets, 48 ending 2026-11/12 |
| P8 | the same for `Senate 2026`, `Governor 2026` (2) | Senate **142** (50 events, 49 ending 2026-11/12); Governor **116** (50, 50) |
| P9 | CLOB `POST /books` with two token ids from P8 (1) | 200; 2 books; keys `asks, asset_id, bids, hash, last_trade_price, market, min_order_size, neg_risk, tick_size, timestamp` |

### 0.4 Selection decisions

| Idea | Decision | Reason |
|---|---|---|
| **CH129** election night | **include (E), prospective only, one night** | The only date-boxed object in round 6; keyless books (P9); populations exist (P7-P8). Honest weaknesses, all in the title or the floors: one night is one cluster; sign and closing time are confounded unless both signs share closing-hour strata (premise 4), which may leave E "not run (identifiability)"; professionals price liquid races; the declared power reaches only a drift of about 3× the floor, accepted **only** as a one-night case study with no claim beyond that night (round 1 item 6). The ex-post 2024 audit is dropped (premise 7). Liquid races are kept; the tier is a binding sign check |
| **CH130** pair at birth | **include (P), census-gated, labelled "selected on lifetime volume"** | Metadata on the host (premise 7); Kalshi minute candlesticks are keyless. Honest weaknesses: the C1 set is worn and volume-selected (premise 6); gap convergence is a known C1 result and E010's live object, so P1 must beat the same pairs' later-life slope; non-sports C1 is 167 pairs and CH130's kill (40 Kalshi-first pairs with a ≥ 5c gap) may not be reachable. Historical units end before 2026-10-12 |
| **CH125** leaderboard hazard | **not a test; withdrawn uncounted (round 1), like CB14's CH127** | Archived LMArena pages hold no table (P5-P6), `/leaderboard/text` has 75 capture-days in nine months, the HF dataset API returned 401 in round 6, and the planning MDE (0.6-0.9) is above the power gate's 0.60. No L outcome, price or leader has been seen, so withdrawal before any rule bound is not counted. Re-entry: a verified keyless point-in-time source, found by probes dated **outside** any planned L window (P5-P6 were inside it), and a fresh design |

**Sports and categories.** `CB15_SPORTS_IN_PRIMARY = false` (a parameter, as CB8-CB14). P excludes C1 pairs with
Kalshi category Sports (149 of 316) from the primary and reports them. E contains no sports. Category stays a parameter.

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Prior use | Role in CB15 | Evidence ceiling |
|---|---|---|---|
| `research_lab/creative_batch15/ge0_sources/` (**new, pre-freeze**): every source the GE0 compilers used, archived as fetched (URL, fetch time UTC, sha256, file) | none | the sign table, poll-close table and party map | input |
| `history/h15_elect_live` (**new, post-freeze**, q0345): frozen race map (incl. the national control markets), receipt-timed books (top 5 levels per side, venue `timestamp`, `last_trade_price`) for the YES and NO tokens of every trade and control market, Gamma `liquidity` at the 2026-11-02T12:00Z pass, gap and storage logs | none | E1, E2 | prospective (L2), one night |
| `research_lab/cross_venue/` on the host (`matches.json`, `audit_flags.json`, `audit_sample100.json`, `poly_markets.json`, `series/*.npz`; sha256 pinned) | C1 study v1/r1, CB5-K, CB12-X, E009/E010 design | **pair list only**: the C1 reproduction call (`c1_pairs()`, asserting 316 pairs and 183 events, as CB5-K and CB12-X) and the fields `k_ticker, k_series, k_cat, k_open, k_close, p_market_id, p_event_id, p_start, p_token0` and texts. **No P statistic reads a series value**; `p_end` is never read | pair list |
| `history/h15_birth` (**new**, q0349): Gamma metadata (`createdAt`, `startDate`, `endDate`, ids, `feeSchedule`, lifetime `volume` for the tercile check only), Data API prints from the first print to `t_d + 24 h 30 min` and over `[t_L − 2 h, t_L + 24 h 30 min]` aggregated to transactions, Kalshi 1-minute candlesticks (bid/ask close) over `[t_birth − 6 h, t_d + 25 h]` and `[t_L − 1 h, t_L + 25 h]`, CLOB `prices-history` (fidelity 10) **after `t_birth` only** plus a count of points before it | none | P1, P2 | L1 (selected on lifetime volume) |
| `history/h15_birth_live` (**new, post-freeze**, q0352): new listings matched by the frozen matcher, first-print detection, Kalshi orderbook and CLOB `/book` reads at `t_d` and `t_d + 24 h` | none | P1-rep, P2-rep | L2 |
| `cross_venue_live/` (E009/E010), `surprise_live/` (E011), `snapshots/`, `live_trades/`, `book_sweeps/`, `trade_samples/`, `e001/`-`e007/`, `forecasts/`, `flow_screen/`, every `cb*_extract/` | live stores, E-series, J4-R, CB1-CB14 | **never opened by any CB15 path** (runner refuses; unit-tested) | - |
| `h1_*` … `h14_*`, every `creative_batch1..14/` | worn, sealed or batch-owned | **not read**, except id columns for exclusion keys through a field-restricted accessor; no `holdout/` path is ever opened | - |

**Reuse disclosure.** *E:* no AREPO set holds 2026 general-election markets in a window that intersects E's (live
captures, J4-R and CB13-T fill sets may hold some of the same markets in October; §1.3). *P:* the C1 pairs are worn and
volume-selected; for pairs whose Polymarket life was shorter than 14 days, the C1 series window contains the birth, so
their birth-period prices entered the C1 lead and gap analyses (not this statistic); a binding robustness drops them.

### 1.2 Dates (declared; UTC unless ET is stated; ET = UTC−5 on 2026-11-03)

| Name | Value | Meaning |
|---|---|---|
| `T15_draft` | 2026-10-19T04:16Z | the draft; no CB15 quantity computed |
| `T15_E_freeze` | **2026-11-01T12:00Z, hard** | part E frozen (rules, sign table, poll-close table, party map, cross-table, race map hashes); else E1, E2 "not run (calendar)", counted |
| `T15_E_pre` | 2026-11-02T12:00Z | first collector pass: tier snapshot (`liquidity`); passes on the 10-minute grid (hh:00, :10, … :50) |
| `T15_E_on` / `T15_E_off` | 2026-11-03T22:00Z / 2026-11-04T21:00Z | passes every minute (covers every `t_a` and `t_a + 12 h`) |
| `T15_E_end` | 2026-11-06T00:00Z | 10-minute grid from `T15_E_off`; collector stops |
| `T15_cpu_hold` | `[2026-11-03T21:00Z, 2026-11-04T22:00Z)` | committed cron lines pause `cpu`-lane jobs with `mem_mb ≥ 500` and resume them; dry-run on 2026-11-02 (§2.8) |
| `t_close(state)` | GE0 poll-close table | the state's last official poll-closing time in UTC (the latest across its time zones) |
| closing-hour stratum | `floor(t_close)` to the UTC hour | E's strata (§CB15-E) |
| `t_a`, `t_b` | `t_close + 90 min`, `t_a + 12 h` | E's window per state; every `t_a`, `t_a − 36 h`, `t_a − 24 h`, `t_a + 6 h`, `t_a + 24 h` falls on a scheduled pass (poll closes are on the hour or half hour) |
| `T15_hist_end` | 2026-10-12T00:00Z | every P historical row (`t_d + 24 h 30 min`, `t_L + 24 h 30 min`) is before it; asserted |
| `T15_P2_start` / `T15_P2_end` | `max(P freeze + 1 d, 2026-11-04T00:00Z)` / the date by which ≥ 60 non-sports Kalshi-first births have their 24-h read, never after `T15_P2_cap` = 2027-04-30 | P Stage 2; after E009/E010's end (2026-11-03T00:00Z) and their analysis runs. The stop counts births, never results |
| E009/E010 | `[2026-10-13, 2026-11-03T00:00Z)` | not touched: no CB15 path opens `cross_venue_live/`; P's historical units end before 2026-10-12 and its Stage 2 starts 2026-11-04 |
| E011 | window to 2026-11-10 | E's collection overlaps in time (collection overlap only); **no CB15 output defines an E011 subgroup** |
| J4-R / CB13-T HOLDOUT | `[2026-10-16, 2026-10-21)` / `[t_j4r_end, 2026-10-26)` | no CB15 row inside either |

### 1.3 Sealed and untouched data (named)

- **Refused roots.** `run_cb15.py` refuses every root in the last two rows of §1.1 and writes only under
  `research_lab/creative_batch15/` and the three `h15_*` roots. The C1 files are opened read-only through the pinned
  reproduction call and a field-restricted reader of `matches.json`.
- **E009/E010 and CB15-P.** P's object (the first 24 h after Polymarket's first print, on historical pairs) differs from
  E009's (Kalshi's 10-min change → Polymarket's next 20 min) and E010's (change + gap → 1 h and 6 h, live). P computes
  no statistic on any row at or after 2026-10-12, opens no live store, and starts its watcher after both have ended.
  `t_d` = first print + 10 min keeps the sealed lead's horizon out of the target.
- **CB12-X and CB5-K (same pairs, other objects).** Both are near-resolution measurements on the C1 series. P reads no
  series value. No CB15 line pools, cites or conditions on CB12-X or CB5-K results.
- **CB11-P, CB11-A (sealed HOLDOUTs).** No CB15 path opens any `h11_*` data. P drops every key of the `h11_pol` and
  `h11_attn` frames (both strata, both splits, sampled or not).
- **CB14-W (personnel; live from 2026-10-26), CB14-S (mention events; Stage 2 from 2026-10-27).** CB15 adds CB14's frame
  ids (W markets, events and series; S events of P, N and Stage 2 as built at q0340's run), as CB14 §8 item 6 requires.
- **CB13 (T fills in the J4-R window and HOLDOUT; R barrier events).** Keys added. E reads no October price.
- **Exclusion keys (q0340).** Union of: (1) CB14 q0302's `exclusion_keys.csv.gz` (sha256 pinned; it unions CB13 q0276,
  CB12 q0241, CB11 q0221, the C1 sample, the T5 frame, every CB8-CB14 frame and seal copy known then); (2) id columns of
  CB14's frames built since; (3) every seal copy under `docs/research_lab/seals/` committed by then. Keys = market id,
  Gamma event id, `negRiskMarketID`, series id. **Each key carries its source(s)**; if the inherited file lacks
  attribution, q0340 rebuilds the union from its sources. A frame not yet built is "absent at q0340" (recorded) and
  re-read by the census. More than 2% of ids without metadata → the affected family "not testable (disjointness)",
  counted. **CB16 must add CB15's frame ids (E race map, P pairs, P Stage-2 pairs).**
- **Key rule per family (declared deviations; accepted in round 1, item 11).**
  - *P:* drops keys from every source **except** those whose only source is the C1 set (`matches.json`, CB5-K, CB12-X,
    the C1 sample as used by E009's design): the C1 set is P's population, as CB14-S kept CB12-M's SCREEN ids for N.
    Full series rule for the other sources; the census reports drops and the no-drop counterfactual.
  - *E:* **calendar disjointness, keys as binding robustness.** E reads only books in `[2026-11-02T12:00Z,
    2026-11-06T00:00Z)` and no Gamma outcome. A prior sample holding a 2026 race market read it in October or earlier,
    for a different object. The census reports the key-overlap count, and a binding E robustness drops those markets.
- **Outcome guards.** *E:* no Gamma outcome is fetched; `outcomePrices`, `umaResolutionStatus(es)` and `closedTime`
  are discarded at parse. The target is a price. *P:* the same (no outcome); prints and prices after `t_d` (and after
  `t_L`) are opened only by the screen and rep jobs; the census and GPP read them only through the SE-only proxy;
  lifetime `volume` is opened only by the tercile check in the screen.

### 1.4 Rules files

- `seals/cb15_rules.json` (before q0341), hashed per part:
  - **`common`**: refused roots, seeds, bootstrap and small-G settings, Holm settings (k1 = 4), disk guards, field
    whitelists, smoke criteria, the source-attributed key rule.
  - **`E`**: the frozen query list (`Senate`, `Governor`, `House`, `congressional district`, `midterm`, each with `2026`,
    `events_status=active`, paged to `hasMore = false`), the politics-tag (id 2) completeness walk of active events ending
    `[2026-11-03, 2027-01-31]`, the race regex, the general-election rule (description names 3 November 2026;
    primaries, runoffs and other-date specials excluded), the trade-market, two-party and control-market rules, the GE0
    recipe, compiler instructions and archive format, the stratum rule, the tier rule, windows, the pass grid, the read
    and one-sided-book rules, fee policy, gates, placebo windows, the collector schedule, the cron pause/resume lines and
    the storage-degradation rule. The GE0 files (sign table, poll-close table, party map, cross-table, source manifest)
    and the race map are **hashed into part E at the freeze**.
  - **`P`**: the C1 reproduction call and file sha256s, the field list, the Kalshi-first rule, the first-print rule, the
    print-based price rule, `t_d`, `t_L`, the gap rule, the entry and exit print windows, the volume-tercile rule, the
    frozen matcher (`cross_venue.match_markets`, the r1 `audit_conflict` rule; source sha256 pinned) for Stage 2, gates.
- Jobs refuse (exit 2) on a hash mismatch. **No rule is computed from, or revised after, any E book or P print or
  price.** After `T15_E_on`, no element of part E may change; a defect found then makes the affected units
  "unavailable", counted.
- **Field whitelists.** *Gamma:* as CB14 §1.4, plus `liquidity` for E at the `T15_E_pre` pass only and lifetime `volume`
  for P (tercile check only). *CLOB `/books`:* `asset_id`, `market`, `timestamp`, top 5 levels per side (price, size),
  `tick_size`, `neg_risk`, `last_trade_price`; `hash` discarded. *Kalshi:* `ticker`, `event_ticker`, `series_ticker`,
  `open_time`, `close_time`, `rules_primary` sha256 plus `is_provisional` and `can_close_early`; candlesticks
  `end_period_ts`, `yes_bid.close`, `yes_ask.close`, `volume`; **`result` and `settlement_value` are discarded at
  parse**. *Data API:* as CB14 (no hash, wallet, name or `side` written). A unit test feeds fixtures carrying every
  forbidden field and asserts that no parsed row, file or log contains them.

## 2. Common rules (deltas from CB14 §2)

### 2.1 Costs

| Test | Price and cost rule |
|---|---|
| E1, P1 | none charged (forecasting tests) |
| E2 | **recorded books**: entry at the best ask of the predicted-side token (D YES for `s = +1`, D NO for `s = −1`) in the first successful read with receipt ≥ `t_a` (≤ 2 min later, else "unavailable (gap)"); exit at that token's **best bid** in the first read with receipt ≥ `t_b` (≤ 5 min); **no bid at `t_b` → the unit is priced at `w* = −9.3c`** (round 1 item 2; the p90 round trip of `EXECUTION_COSTS.md`); size min(100, displayed best-ask size); fee `r·e(1 − e) + r·x(1 − x)`, `r = max(feeSchedule.rate, 0.04)` (politics; current, not point-in-time, so the floor is conservative) |
| P2 | **recorded prints**: toward Kalshi (YES if `g_d ≥ 5c`, NO if `g_d ≤ −5c`); entry at the taker-adverse print in `[t_d + 60 s, t_d + 60 min]` (max YES-terms price when buying YES; min when buying NO, paying 1 − price); exit at the adverse print in `[t_d + 24 h, t_d + 24 h 30 min]` (min when long YES; max when long NO); none → the last print in `(t_e, t_d + 24 h 30 min)` ("stale exit", counted); none after entry → "no exit" (excluded, counted, priced at `w*` in the reach check); size min(100, entry print size); fee as E2 |
| P2-rep | recorded best ask at the read ≥ `t_d` (≤ 2 min); recorded best bid at `t_d + 24 h` (no bid → `w*`) |
| Binding cost robustness | +1.0c per side (E2, P2, P2-rep) |

### 2.2 Clocks

- **CLOB books (E; P Stage 2).** Receipt time (host clock, NTP-checked by the smoke) is the clock; the venue `timestamp`
  is stored and its lag reported. Passes start on the grid of §1.2; a read "at `t`" is the first successful read with
  receipt ≥ `t` within 2 min (5 min for `t_b`).
- **Data API prints (P).** `timestamp` (seconds), aggregated by transaction in memory (YES-terms VWAP, min, max, size;
  hash discarded). `t_birth` = the time of the market's **first** transaction; `p(t)` = the YES-terms VWAP of the last
  transaction at or before `t` with age ≤ 2 h (else "no print").
- **CLOB `prices-history` at fidelity 10 (P).** Used only for points stamped after `t_birth`, usable from stamp + 600 s;
  only as a labelled fallback for target prices (§CB15-P). Points before `t_birth` are counted, never used.
- **Kalshi candlesticks (P).** A 1-minute bar is usable from its `end_period_ts`; the Kalshi mid at `t` = (bid close +
  ask close)/2 of the last usable bar with both sides, age ≤ 60 min, spread ≤ 10c; else "no Kalshi quote", counted.
- **Poll-closing times (E).** Official times in the GE0 table; `t_a` is a scheduled clock, not a reported one.
- **Gamma `createdAt`, `startDate`, `endDate`; Kalshi `open_time`.** As fetched. `closedTime` and `p_end` are never used.

### 2.3 Uncertainty and decision rule

As CB14 §2.3: unweighted primary unless stated; one-sided p = the max over the declared ways; 2,000-draw cluster
bootstrap, **seed 1515**; the small-G rule (G ≥ 30 CR1; 15-29 CR2 with t(G − 1) and the Webb wild bootstrap, 9,999
draws; G < 15: the way leaves the max and its leave-one-cluster-out sign rule binds, as A-C1); "unknown" never counts
as met.
- **Ways.** **E1, E2:** the state is the unit; p = the **state-label permutation within closing-hour strata** (sign
  labels permuted among a stratum's eligible states, group sizes per stratum fixed; 9,999 draws, seed 15101; p = (1 +
  #{T* ≥ T}) / 10,000). The night is one cluster for everything common to all states. **P1, P2:** Polymarket event; ISO
  week of the birth.
- **Testability minimums (declared deviations from 100 units / 30 clusters, each from the hypothesis's own kill).**
  E: ≥ 16 eligible states in identified strata with ≥ 7 per sign on the night. P1: ≥ 60 pairs in ≥ 30 events. P2: ≥ 40
  pairs with `|g_d| ≥ 5c` in ≥ 25 events (CH130's kill). Below → "not testable (population)", counted with p = 1.
- **Stage 1 (4 tests).** Advance iff one-sided p < 0.01 (strict), the §2.4 floor holds, every binding placebo,
  robustness check and gate holds, and the test passes a batch Holm step-down at one-sided α = 0.05 over **k1 = 4**
  (fixed; first step 0.0125, so any p < 0.01 passes). **E finishes first (2026-11-06) and is judged when it runs at
  `p < min(0.01, α/k1)` = 0.01, strict; that verdict is never withdrawn, and the final Holm can only add passes**
  (round 1 item 7). BY (q = 0.10 over `battery2.cumulative_count()` at the run) is triage.
- **Stage 2.** One Holm at one-sided α = 0.05 over P's triggered tests (≤ 2); a test finishing before k2 is known is
  judged against α/2, strict; the full Holm is applied once at the end and can only add passes.
- **Stage P** is a separate registration for any survivor (§2.9).

### 2.4 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate |
|---|---|---|
| E1 | prospective drift | `T_E1` ≥ **+5c** (stratified balanced D-terms drift in the predicted direction; CH129's kill) and the stratified balanced sign share ≥ 0.60 (CH129's kill; binding) |
| E2 | economic, recorded books | stratified balanced mean net ≥ **+1.0c per share** |
| P1 | forecasting | slope ≥ **0.30** (CH130), and birth slope − later-life slope > 0 (binding, §CB15-P) |
| P2 | economic, recorded prints | event-weighted mean net ≥ **+1.0c per share** |
| P1-rep, P2-rep | as Stage 1, at recorded books | as Stage 1 |

### 2.5 Counting (M3 rule)

- Kinds **`cb15_test`**, **`cb15_replication`** and **`cb15_descriptive`** (EXCLUDE), mirroring CB14's
  `battery2.KIND_RULES` entries; unknown kinds raise. Descriptive lines: smokes, GE0 and its audit, pre-gates,
  censuses, gates, strata, tiers, the race-level sign share, liquid and second-tier readings, Polymarket-first pairs,
  sports pairs, seeded-history shares, gap-closure shares, latency, gap and storage logs; the L withdrawal record.
- **Count lines (`ml_explain` `n_tests`).** `creative_batch_15:E` **2**, `creative_batch_15:P` **2**; replication line
  `creative_batch_15:P:rep` carries P's triggered tests (≤ 2).
- **Triggers.** P1-rep iff P1 advanced; P2-rep iff P2 advanced. E has no Stage 2 in CB15.
- **Cumulative count:** 1,232 on HEAD at drafting (`battery2-count-v1`), not stable; recorded at each run. **CB15 adds
  4 fixed tests and up to 2 conditional ones. Budget: 4-6.** CH125 adds nothing (withdrawn before any rule bound; one
  descriptive line records it).
- Tests behind a failed or unknown gate (smokes, disjointness, GE0, GEI, GEC, GEP, GE, GPB, GP, GPP, availability, the
  E calendar deadline, Stage-2 minimums) are "not testable", "not run", "not run (identifiability)" or "not run
  (calendar)" (p = 1) and are **still counted**. A job waiting on exit 75 is "pending" and writes no line.

### 2.6 Placebos and robustness (common)

As CB14 §2.6: each binding placebo names its alternative; calibration placebos are judged on p alone; 200 draws;
**advance rate ≤ 1.5%**; seeds 15101-15130. Common binding robustness for any advance: (i) the §2.1 cost robustness;
(ii) p and the floor without the top 5 clusters of each way (E: without the top 2 states of each sign, and every
leave-one-state-out keeps the sign); (iii) P: each calendar half and leave-one-quarter-out sign; (iv) unavailable units
excluded and counted, never imputed; available share < 60% of eligible → "not testable (availability)".

### 2.7 Pre-freeze census and pre-fetch gates (counts only)

Outcome guards first; field-restricted accessors; a unit test asserts that no census path receives a Gamma outcome, a
P print or price after a unit's decision time, or an E book after `T15_E_on`. Per-family gates are in §3: **E** GE0 →
GEI → GEC → GEP (pre-night) and GE (on the night); **P** GPB (no network) → GP, GPP. MDEs come from counts and declared
or feature-only quantities, and are never used to change a floor, window or threshold.

### 2.8 Compute, network, disk and stop rules

- **Host.** 1 OCPU, about 5.6 GiB RAM shared with the collectors. Queue rules as CB14 §2.8: one job per lane, nice 19,
  `MemAvailable ≥ mem_mb + 1200`, address cap 2 × `mem_mb`, the 02:45-05:30 UTC blackout for `mem_mb ≥ 500`; `mem_mb` ≤
  600 everywhere; streaming one page or pair at a time.
- **Election-night protection (round 1 items 4 and 8).** Two cron lines, committed with the collector in the host
  crontab file: at `T15_cpu_hold` start they pause the promotion of `cpu`-lane jobs with `mem_mb ≥ 500` (the runner's
  lane-pause flag; if the runner has none, the flag check is added with the collector and unit-tested), and at its end
  they resume it. **Dry run on 2026-11-02**: pause at 12:00Z, verify that a held job is not promoted, resume at 12:10Z,
  verify promotion; logged in the ledger. The E collector runs at nice 5, `mem_mb` 200.
- **Network** (`net` lane; **one `net` job at a time at ≤ 2 rps Polymarket**; ≤ 1 rps Kalshi; descriptive User-Agent;
  shared `Limiter`, 429 / `Retry-After` back-off, stop on repeated 429):

  | Job | Work | Requests / wall | Stored (cap) |
  |---|---|---|---|
  | q0340 | exclusion keys (increment over CB14 q0302, attribution) | ≤ 600 Gamma, ≤ 6 min | ≤ 0.01 GB |
  | q0341 | E census: 5 queries × pages (≤ 120), event lookups (≤ 400), politics-tag walk (≤ 100) | ≤ 620, ≤ 10 min | ≤ 0.005 GB |
  | q0343 | E smoke (incl. one full-size `/books` pass of about 1,000 out-of-frame tokens to measure stored bytes per pass) | ≤ 30, < 5 min | 0.002 GB |
  | q0344 | E pre-gate: race-map refresh (≤ 60), one `/books` pass (≤ 15 batches) | ≤ 80, ≤ 3 min | ≤ 0.002 GB |
  | q0345 | E collector: `/books` batches of ≤ 100 tokens (≤ 1,000 tokens → ≤ 10 per pass) on the grid of §1.2; Gamma map refresh every 6 h | about 15,000 over the window; ≤ 0.17 rps peak | cap = 3 × (smoke bytes per pass × scheduled passes), at least 1.0 GB |
  | q0348 | P smoke | ≤ 30 | 0.001 GB |
  | q0349 | P data: per Kalshi-first pair, Gamma (1), prints from the first print (≤ 6 pages or a bounded query), Kalshi candlesticks (2), `prices-history` (2); ≤ 150 pairs | ≤ 1,800, ≤ 35 min | ≤ 0.05 GB |
  | q0352 | P watcher: Gamma new listings hourly, Kalshi open markets by `min_created_ts` hourly, Data API first-print polls every 5 min per new pair, orderbook and `/book` reads at `t_d` and `t_d + 24 h` | ≤ 3,500 a day | ≤ 0.05 GB total |

  Historical `net` total ≤ about 3,200 requests (under 1 h of `net` lane); if GPB fails, q0349 never runs. A fetch
  without its `*_complete` status is "pending" and never analysed partially.
- **Disk guard.** As CB14 §2.8 for every job except the E collector inside `[T15_E_pre, T15_E_end)`: `--disk-cap-gb`,
  `--data-dumps-cap-gb 40`, exit **75** if data-dumps + cap > 40 GiB or root free − cap < 4.5 GB. **The E collector has no
  exit-75 path on the night (round 1 item 8):** the cap is sized from the smoke's measured bytes per pass with a 3×
  margin; a pre-night check on 2026-11-02 requires data-dumps + cap ≤ 40 GiB and root free ≥ cap + 10 GB (else the
  coordinator resolves it before `T15_E_on` without deleting data); if the projection is exceeded during the window,
  the collector **degrades to the top level per side** and logs it; it stops only if root free falls below 2 GB (host
  protection; the remaining units are "unavailable", counted). CB15 output caps total ≤ 1.2 GB. CB15 never deletes or
  moves host data.
- **Stop rules.** 3 CPU-hours per family. A job failing twice for the same non-transient reason stops and is recorded.
  A null is "not detected at MDE x". **No re-screen of a failed CB15 test** with altered sign tables, strata, maps,
  windows, gap rules, checkpoints, entry or exit rules or populations, on any data.

### 2.9 Funnel and Stage P

Screen (Stage 1) → gates, placebos, robustness → replication (Stage 2: recorded books on new births) → separate
prospective confirmation (Stage P) → economic validation at recorded prices with fees, spread and depth.
- **E** is a one-night prospective case study: an advance is not confirmation, carries no claim beyond that night, and
  has no Stage 2 here. It yields only a registration draft for the next general-election night (2028-11-07) with a
  fresh archived sign table, recorded books and the same statistics; runoff and special-election nights may be
  registered by a later batch.
- **Stage P-P.** Only P-rep (causal selection) can lead to it (round 1 item 10): a fresh watcher window after
  `T15_P2_end`, frozen matcher and audit, recorded books with depth.

---

## 3. Tests

### CB15-E: Election-night reporting-order drift, 3 November 2026 (CH129). One-night case study; the night is one cluster

**Question.** Within states whose polls close in the same hour, do the races of states where the late count is known in
advance to move toward one party drift toward that party over the first 12 hours of the count by more than the races of
states where the late count moves the other way?

**Mechanism.** Early partials carry the votes counted first (mail and early ballots in some states, election-day ballots
in others; large urban counties early or late). A crowd that reads early margins at face value overprices the early
leader where later votes lean the other way. Who pays: buyers of the early-leading side 1-3 hours after polls close.
Why it might persist: it does not in liquid races, where professionals model the count; the hypothesis is about the
second tier. **The opposite is as plausible:** the crowd already prices the shift, and E1 fails (that is the test).

**Race map (q0341 census → q0344; frozen at `T15_E_freeze`).**
- Frame: Gamma `public-search` with the frozen query list, active events, paged to `hasMore = false`; events whose
  title matches the race regex and whose description names the 3 November 2026 general election; members binary.
  **Completeness (binding):** the politics-tag walk's matching events must be ≥ 95% inside the search frame, else E
  "not testable (frame completeness)", counted.
- **Trade market per race (frozen).** (a) a party market or party member ("Democrat", "Democratic"); else (b) the
  candidate member whose party is D in the GE0 party map. **Two-party rule:** the two highest-priced members at the
  q0344 read are one D and one R (else "not two-party", excluded and counted). D-terms price = the D YES token's mid.
  Markets listed after the freeze are excluded ("post-freeze listing", counted).
- **Control markets (frozen).** The D member of the national "party control of the Senate" and "of the House" markets
  (q0341 identifies them; frozen in the race map). A missing control market makes the net-of-control check "unknown",
  so E1 cannot advance.
- **Tier (frozen rule).** At `T15_E_pre`, the top third of eligible trade markets by Gamma `liquidity` are "liquid"; the
  rest are "second tier".

**GE0: the sign table, poll-close table, party map and cross-table (archived; before the freeze; round 1 item 3).**
- **Compilers.** Two independent **network-enabled** agent passes (separate sessions; not the read-only
  `science-reviewer`), each given the recipe only and compiling **all 50 states plus DC now**, without waiting for
  q0341. Every source used is fetched and archived into `ge0_sources/` with its URL, fetch time (UTC) and sha256; the
  table cites each fact by archive sha256. **A state without an archived source for every input gets `s = 0`.**
- **Recipe.** For each state: (1) the 2026 counting and reporting order of vote modes (when mail and early ballots may
  be processed and counted, whether they are reported before or after election-day ballots, late-arriving ballots,
  central-count urban counties), from state law, election-office guides and NCSL's "When Absentee/Mail Ballot Processing
  and Counting Can Begin" table; (2) the direction of the D share's change between early returns and the final count in
  the **2022 and 2024** general elections. `s = +1` (late count toward D) or `−1` (toward R) only if (1) and both years
  of (2) agree; else `s = 0`. **No 2026 poll, forecast, price or 2026 news may be fetched or used.** States where the two
  passes disagree get `s = 0`; agreement (Cohen's κ) is reported. The poll-close table (`t_close`, official source
  archived) and the party map (candidate → party for mapped races, archived source) are compiled the same way.
- **Audit.** A `science-reviewer` pass (read-only, on the archive) checks that every entry cites an archived file that
  supports it and that no archived file is a 2026 poll, forecast or market page; unsupported entries become `s = 0`.
- **Disclosure.** The compilers' model memory may contain 2026 information (polls, forecasts, early-vote reporting).
  The archive rule constrains what is cited, not what the compiler knows; residual compiler bias is a stated risk (§7).
- **Cross-table (published before the freeze, no prices).** Counts of `s = +1`, `−1`, `0` by closing-hour stratum, for
  all 51 jurisdictions and, after q0344's map, for mapped states; committed with GE0.

**Units and target.** A race is eligible on the night if its state has `s ≠ 0`, its D-terms mid at `t_a` lies in
**[0.10, 0.90]** with spread ≤ 10c ("decided" and "wide" excluded, counted; both are pre-entry states), and reads exist at
`t_a` (≤ 2 min) and `t_b` (≤ 5 min). **No exclusion uses the state at `t_b`** (round 1 item 2). The mid at `t_b` is
(best bid + best ask)/2 whatever the spread; a one-sided book uses the missing side's bound (no ask → 1; no bid → 0).
`drift_r = mid_r(t_b) − mid_r(t_a)` in D terms. **State value** `d_g` = the mean over its eligible races (each state
weight 1, whatever its number of House races).

**Strata and identifiability (round 1 item 1).** Stratum `h` = the UTC hour of `t_close`. A stratum is **identified** if
it holds ≥ 1 eligible state of each sign. Only identified strata enter E1 and E2.

**E1 (stratified balanced drift).** `T_E1 = Σ_h w_h · (½ · mean_{s=+1, h} d_g − ½ · mean_{s=−1, h} d_g)`, with `w_h =
m_h / Σ m_h` and `m_h = n₊ₕ n₋ₕ / (n₊ₕ + n₋ₕ)`; one-sided > 0; floor +5c; p = the within-stratum permutation (§2.3). A
repricing common to all races at one clock time hits the states of one stratum at nearly the same window, and cancels in
the within-stratum contrast; a swing that interacts with the sign does not, which is why one night is one cluster.
- **Binding sign share.** The stratified balanced share (the `w_h`-weighted mean over identified strata of the mean over
  the two sign groups of the share of states whose `d_g` has the predicted sign) ≥ 0.60 (CH129's kill).
- **Binding net-of-control check (logits).** `z_r = [logit mid_r(t_b) − logit mid_r(t_a)] − [logit c_r(t_b) − logit
  c_r(t_a)]`, mids clamped to [0.01, 0.99], `c_r` = the D-terms mid of the race's chamber-control market (Senate races
  → Senate control; House races → House control; Governor races → the mean of the two control drifts), read on the same
  clock window; state means of `z`, the same stratified statistic and permutation: positive with one-sided p < 0.05.
  *Alternative guarded:* a national repricing (in logits, not additive in price) aligned with the sign mix.
- **Binding pre-night placebo.** The same statistic on `[t_a − 36 h, t_a − 24 h]` (grid reads) must not reach p < 0.01.
  *Alternative guarded:* states of one sign were already drifting before any vote was counted.
- **Binding robustness** (each keeps the sign; the first two also p < 0.05): `t_a` = `t_close` + 60 min and + 150 min;
  `t_b = t_a + 6 h`; `t_b = t_a + 24 h` (sign only); Senate and Governor races only (if ≥ 4 states per sign remain);
  second tier only; key-overlap markets dropped (§1.3); every leave-one-state-out; top-2 states per sign dropped.
- **Reported (uncounted).** The unstratified balanced contrast; the race-level sign share; liquid versus second tier;
  drift by hour since `t_close`; spread and depth through the count; one-sided-book shares at `t_b`; decided and wide
  shares; κ of the GE0 passes; the unbalanced mean `mean_g s_g · d_g`.

**E2 (economic, recorded books).** Each eligible race: buy the predicted side at `t_a`, sell at the recorded best bid at
`t_b` (no bid → `w*`; §2.1). State value = mean race net; the same strata, weights and permutation as E1; one-sided > 0;
floor +1.0c.
- **Binding.** +1.0c per side; "no depth" races (displayed best-ask size < 10 shares) included at `w*` keep the sign;
  exit at `t_a + 6 h` keeps the sign.
- **Reported.** Capacity (displayed depth at the touch), size-weighted net, the tier split.

**Gates.**
- **GEI (identifiability; GE0 cross-table and q0344, no prices):** the identified strata of mapped states must carry
  the GEC counts below; else E1 and E2 "not run (identifiability)", counted.
- **GEC (q0344; counts only):** within identified strata, ≥ 25 races with a mapped two-party trade market and `s ≠ 0`,
  D-terms mid in [0.10, 0.90] at the q0344 read, in ≥ 16 states with **≥ 9 states per sign** (round 1 item 6).
- **GEP (power, pre-night):** `MDE_E1 = (z_0.99 + z_0.80) · ½ · σ_d / √(Σ_h m_h)` with the **declared** `σ_d = 20c` (round
  6: "gaps of 10-30c during the count"; no night data can enter it) and the GEC counts; E1 and E2 "not run (power)" if
  `MDE_E1 > 15c`. **The 3×-floor rule is a declared deviation from CB14's 2×, accepted only for a one-night case study
  with no claim beyond that night** (round 1 item 6). With 9 states per sign in one stratum, `MDE_E1 ≈ 14.9c`; spreading
  them over strata lowers `Σ m_h` and raises the MDE.
- **GE (on the night, q0346):** ≥ 16 eligible states in identified strata with ≥ 7 per sign, else "not testable
  (population)", counted.

**Honest reading.** E detects a stratified drift near 15c at best, not 5c, and stratification may leave too few
identified strata to run at all. A null says "not detected at MDE x on one night"; a pass is a single-night case study.
Neither is evidence beyond that night.

### CB15-P: The pair at birth (CH130). Selected on lifetime volume

**Question.** When Kalshi has been trading a question for at least a day before Polymarket's first print, does
Polymarket's opening level lag Kalshi's standing price, and does the gap close over Polymarket's first day by more than
the same pair's gaps close later in life?

**Mechanism.** Polymarket's first prints come from the seeding trader and the first retail, while Kalshi's price has had
days of trading. Who pays: Polymarket's first-day counterparties. **Against it:** the first-hour spread (5-10c) may
exceed the gap, and generic convergence (C1's 80-minute half-life) may explain any slope (hence the binding later-life
contrast).

**Population (q0347, no network; frozen).** The C1 set by the pinned reproduction call (316 pairs, 183 events);
non-sports by Kalshi category (sports reported); key drops by source (§1.3). **Selection label (round 1 item 10):** the
C1 universe was selected on lifetime volume and near-resolution activity (premise 6); P1 and P2 are labelled
"selected on lifetime volume", and only P-rep, whose selection is causal, can lead to Stage P. **Kalshi-first (census
proxy):** `p_start − k_open ≥ 24 h` from `matches.json`. **Kalshi-first (binding, q0349):** `t_birth − k_open ≥ 24 h`.
Pairs whose Kalshi `is_provisional` or `can_close_early` differ from the Polymarket rule booleans are excluded (counted).
Pairs whose scheduled Gamma `endDate` is before `t_d + 25 h` are excluded (scheduled, never `closedTime`).

**Birth and prices (round 1 item 9).** `t_birth` = the time of the market's **first Data API transaction** (reached by a
bounded or oldest-first query if the smoke verifies one, else by newest-first paging up to 6 pages); a market whose
prints do not reach its first transaction is "no birth print (uncovered)", counted. `p(t)` = the YES-terms VWAP of the
last transaction at or before `t` with age ≤ 2 h (§2.2). `prices-history` is used only after `t_birth`.
- **Reported (binding as disclosure):** the share of pairs with `prices-history` points before `t_birth`, and the share
  whose first `prices-history` point is 0.50 ± 0.005 (the seeded-history artefact).

**Units.** One per pair: `t_d = t_birth + 10 min`; `p_d` = the last print at or before `t_d` (the first print itself if
none since); `k_d` = Kalshi mid at `t_d` (§2.2); `g_d = k_d − p_d` (Kalshi Yes = Polymarket Yes by the matcher). Target
`Δ = p(t_d + 24 h) − p_d`; if no print lies in `[t_d + 22 h, t_d + 24 h]`, the usable `prices-history` point at `t_d +
24 h` (after `t_birth`) is used and the unit is labelled "history target"; neither → "no target", counted. Later-life
comparator at `t_L = t_d + 7 d` (if the scheduled end is after `t_L + 25 h`): `g_L`, `Δ_L` by the same rules. Each
event weight 1, split over its pairs.

**P1 (forecasting).** The event-weighted OLS slope (with intercept) of `Δ` on `g_d`; one-sided > 0; floor 0.30; p = max
over the event and birth-week ways. Label: "selected on lifetime volume".
- **Binding birth contrast.** On pairs with both units, `β_birth − β_later > 0` with one-sided p < 0.05 (paired
  event-cluster bootstrap). *Alternative guarded:* generic gap convergence (the C1 result, E010's live object).
- **Binding opening-print control.** A joint fit of `Δ` on `g_d`, `(p_d − 0.5)` and `(p_d − p(t_birth))` keeps the `g_d`
  coefficient ≥ half its solo value with one-sided p < 0.05. *Alternative guarded:* opening prints near 0.50 revert
  regardless of Kalshi.
- **Binding volume check (round 1 item 10).** The slope keeps its sign in the lowest tercile of Polymarket lifetime
  `volume` among P1 units; a tercile with < 15 units is "unknown", so P1 cannot advance. *Alternative guarded:* the
  effect exists only in markets that later became large, which a trader at `t_d` cannot select.
- **Binding calibration placebo.** `g_d` shuffled across pairs within the birth month (200 draws, seed 15111).
- **Robustness (binding; sign).** "History target" units dropped; pairs whose C1 series window covers `[t_birth, t_d +
  24 h]` dropped (worn birth prices); Kalshi-first ≥ 72 h; `t_d = t_birth + 30 min`; Elections pairs alone and the rest
  alone (if ≥ 20 each); top-5 event and week drops; each half by birth date.
- **Reported.** The share of `|g(t_birth)|` closed by `t_d` (CH130's 10-minute kill, reported); Polymarket-first pairs;
  sports pairs; slope by category and by volume tercile.

**P2 (economic, recorded prints).** Units with `|g_d| ≥ 5c`; §2.1; event-weighted mean net; one-sided > 0; floor
+1.0c; p = max over ways. Label: "selected on lifetime volume".
- **Binding worst-case reach.** Units lost to "uncovered", "no entry print" or "no exit" are included at `w* = −9.3c`;
  p < 0.01 and the floor still hold.
- **Binding volume check.** The mean net keeps its sign in the lowest volume tercile (< 15 units → "unknown").
- **Robustness (binding).** +1.0c per side; entry window `[t_d + 3 min, t_d + 60 min]`; exit at `t_d + 12 h` (sign);
  stale exits dropped; top-5 drops.
- **Reported.** The same rule at `t_L` (generic convergence economics; not a placebo); capacity; fill sizes.

**Gates.** **GPB (q0347, metadata only):** ≥ 60 non-sports Kalshi-first pairs (proxy) in ≥ 30 events after key drops;
else P1, P2 "not testable (population)", counted, and q0349 is never committed. **GP (q0350):** the §2.3 minimums
after the birth-print rule. **GPP (power, SE-only proxy):** P1: the slope's clustered SE with `g_d` as regressor and
`Δ_L` as a stand-in target; only SEs written (unit-tested); `MDE_P1 = 3.16 × 1.2 × SE`; "not run (power)" if `> 0.60`.
P2: the P2 rule at `t_L`, SEs only; `MDE > 2.0c` → "not run (power)".

**Planning (honest).** Non-sports C1 is 167 pairs. With a Kalshi-first share of 30-60%, a ≥ 5c gap in 25-50% of those
and some losses to "no birth print", P2's units are about 10-50: **P2 likely fails GP**. P1 may reach 40-100 pairs.

**Stage 2 (conditional analysis; q0352 collects unconditionally from `T15_P2_start`; causal selection, no volume
filter).** Hourly: Gamma listings created in the last 2 h (non-sports), matched to open Kalshi markets by the frozen
matcher (r1 conflict rule), Kalshi `open_time ≤` listing time − 24 h; a weekly blind title audit batch
(`science-reviewer`; failing pairs dropped, counted). For each matched pair the Data API is polled every 5 min until the
first print; `t_birth` = that print's time (detection later than `t_birth + 10 min` → "late detection", counted).
Reads at `t_d` and `t_d + 24 h`: Polymarket `/book`, Kalshi `orderbook`. **P1-rep** (book mids; ≥ 60 pairs); **P2-rep**
(recorded best ask at `t_d`, best bid at `t_d + 24 h`; ≥ 40 units with `|g_d| ≥ 5c`) by `T15_P2_cap`, else "not run
(power)", counted. The watcher never reads `cross_venue_live/`.

### CB15-SM: smokes and audits

- **q0343 E smoke** (≤ 30 requests): part hashes; refusals (live stores, `h11_*` holdouts, forbidden fields `side`,
  `proxyWallet`, `outcomePrices`, `closedTime`, collector reads before `T15_E_pre`); Gamma paging to `hasMore = false` on
  one query; `POST /books` with 100 out-of-frame tokens returns 100 books; **one full-size pass of about 1,000
  out-of-frame tokens with its stored bytes measured** (round 1 item 8; the cap of q0345 is set from it before the
  freeze); receipt-time clock offset ≤ 1 s against an NTP source; gap logging on a forced failure; the storage
  degradation path on a forced projection; the cron pause/resume lines on a test flag.
- **q0348 P smoke** (≤ 30): the C1 reproduction call asserts 316 / 183 and the pinned sha256s; reach to the **first
  transaction** of one out-of-frame 2025 market (bounded or oldest-first query, else page count); Kalshi minute
  candlesticks on one out-of-frame settled market (historical endpoint) and one open market; Kalshi `/markets` with
  `min_created_ts`; `result` discarded.
- Any failure → the dependent family "not testable (source)", counted. **GE0** (with its archive and audit) and the P
  Stage-2 title audits are repo steps; their files are committed before the dependent gate.

## 4. Jobs (draft specs; JSON in this document only)

Fields follow `queue/README.md`; `argv[0]` under `backend/scripts/`, `cwd` `backend`; **none is written to `queue/`**
before code, tests and a `science-reviewer` freeze check exist. All `family` = `creative_batch_15`. Priorities: E
pre-freeze `net` jobs **99 with a 2-h `net` promotion hold** (declared exception, round 1 item 4); P `net` 5-9; `cpu` 9.

| Id | Lane | Priority | Size / time | Depends on | Commit when |
|---|---|---|---|---|---|
| q0340 | net | 9 | ≤ 600 req, ≤ 6 min, mem 500 | CB14 q0302 | with CB14 q0302 complete |
| q0341 | net | 99 | ≤ 620 req, ≤ 10 min, mem 300 | - | `common` + `E` parts committed (target 2026-10-21); 2-h hold before |
| q0343 | net | 99 | ≤ 30 req, < 5 min, mem 300 | - | collector + smoke code reviewed (target 10-26); 2-h hold before |
| q0344 | net | 99 | ≤ 80 req, ≤ 3 min, mem 300 | q0341, q0343, GE0 files | GE0 committed (target 10-29); 2-h hold before |
| q0345 | cron | - | ≤ 0.17 rps, mem 200 | E freeze | installed by 2026-11-02T00:00Z |
| q0346 | cpu | 9 | ≤ 20 min, mem 400 | q0345 end | after 2026-11-06T00:00Z |
| q0347 | cpu | 9 | no network, ≤ 5 min, mem 300 | q0340 | with q0340 |
| q0348 | net | 9 | ≤ 30 req, < 5 min, mem 300 | - | P rules part and smoke code reviewed |
| q0349 | net | 8 | ≤ 1,800 req, ≤ 35 min, mem 400 | q0347 PASS, q0348 PASS | only after both |
| q0350 | cpu | 9 | ≤ 15 min, mem 400 | q0349 | with q0349 |
| q0351 | cpu | 9 | ≤ 30 min, mem 400 | q0350, P freeze | after the P freeze |
| q0352 | cron | - | ≤ 3,500 req a day, mem 150 | P freeze | not before 2026-11-04T00:00Z |
| q0353 | cpu | 9 | ≤ 20 min, mem 400 | q0351, `T15_P2_end` | only if P1 or P2 advanced |

```json
{"id": "q0340_cb15_exclusion_keys", "title": "CB15 exclusion keys with per-key source attribution: CB14 q0302 key file (sha256 pinned) + id columns of CB14 frames built since (h14_wiki frame and live frame, h14_speech P/N/Stage-2 events) + seal copies; Gamma lookups for missing keys; rebuild from sources if attribution is absent", "family": "creative_batch_15", "priority": 9, "expected_value": "disjointness for P; E robustness keys", "data": ["creative_batch14/exclusion_keys.csv.gz", "history/h14_*/ (id columns only)", "docs/research_lab/seals/*", "public Gamma (ids)"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0302_cb14_exclusion_keys"], "argv": ["scripts/run_cb15.py", "exclusion-keys", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 2400, "max_retries": 2, "outputs": ["research_lab/creative_batch15/{exclusion_keys.csv.gz,manifest.json}"], "next_action": "q0347", "notes": "DRAFT-REVISED. Never opens any holdout/ path. A dependency recorded as stopped is absent (recorded). >2% missing metadata -> unverified (family not testable, counted)."}
{"id": "q0341_cb15_e_census", "title": "CB15-E census, counts only: active 2026 general-election races (Senate, Governor, House) by frozen query list paged to hasMore=false; race regex, general-election rule, member structure, party/candidate market type; national Senate and House control markets; politics-tag completeness walk; no price, no outcome", "family": "creative_batch_15", "priority": 99, "expected_value": "E race and state counts for GEI and GEC", "data": ["public Gamma"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": [], "argv": ["scripts/run_cb15.py", "e-census", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--rps", "2", "--disk-cap-gb", "0.005", "--data-dumps-cap-gb", "40"], "timeout_s": 1200, "max_retries": 2, "outputs": ["history/h15_elect_live/frame_census.csv.gz", "research_lab/creative_batch15/census_E.json", "trials.jsonl (cb15_descriptive)"], "next_action": "q0343; GE0 runs in parallel (all 51 jurisdictions)", "notes": "DRAFT-REVISED. Calendar exception: priority 99 with a 2-h net promotion hold by the coordinator (or a one-shot command after the running net job). outcomePrices/umaResolutionStatus/closedTime discarded at parse."}
{"id": "q0343_cb15_smoke_E", "title": "CB15-E smoke: part hashes; refusals (live stores, holdouts, forbidden fields, collector reads before T15_E_pre); Gamma paging; POST /books with 100 out-of-frame tokens; one full-size pass of about 1,000 out-of-frame tokens with stored bytes measured (sets the q0345 cap); receipt clock vs NTP <= 1 s; forced-failure gap log; storage degradation path; cron pause/resume on a test flag", "family": "creative_batch_15", "priority": 99, "expected_value": "go/no-go and storage sizing for the election-night collector", "data": ["public Gamma", "public CLOB /books"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "net", "network": "gamma-api, clob"}, "depends_on": [], "argv": ["scripts/run_cb15.py", "smoke", "--part", "E", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--rps", "1"], "timeout_s": 900, "max_retries": 1, "outputs": ["research_lab/creative_batch15/smoke_E.json", "trials.jsonl (cb15_descriptive)"], "next_action": "PASS: set the q0345 cap (3x measured), q0344; FAIL: E not testable (source), counted", "notes": "DRAFT-REVISED. <= 30 requests. 2-h net promotion hold before."}
{"id": "q0344_cb15_e_pregate", "title": "CB15-E pre-gate: race-map refresh, two-party rule, control markets, one /books pass (D-terms mid band counts only), key-overlap count; sign x closing-hour cross-table of mapped states; gates GEI (identified strata), GEC (>= 25 races, >= 16 states, >= 9 states per sign, within identified strata) and GEP (declared sigma 20c, stratified MDE <= 15c); writes the race map for the freeze", "family": "creative_batch_15", "priority": 99, "expected_value": "E go/no-go before the freeze", "data": ["public Gamma", "public CLOB /books", "creative_batch15/{sign_table,poll_close,party_map,cross_table}.json", "creative_batch15/exclusion_keys.csv.gz (if present)"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "net", "network": "gamma-api, clob"}, "depends_on": ["q0341_cb15_e_census", "q0343_cb15_smoke_E"], "argv": ["scripts/run_cb15.py", "pregate", "--family", "E", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--rps", "1"], "timeout_s": 900, "max_retries": 1, "outputs": ["history/h15_elect_live/race_map.csv", "research_lab/creative_batch15/pregate_E.json", "trials.jsonl (cb15_descriptive or counted not-run lines)"], "next_action": "PASS: E freeze (part E, GE0 and race-map sha256) by 2026-11-01T12:00Z", "notes": "DRAFT-REVISED. Band labels only; no mid stored. 2-h net promotion hold before."}
{"id": "q0345_cb15_e_live", "title": "CB15-E collector (cron every minute, flock, outside lanes): POST /books batches <= 100 tokens for YES and NO tokens of every frozen trade and control market; passes on the 10-minute grid (hh:00, :10, ...) from 2026-11-02T12:00Z, every minute in [2026-11-03T22:00Z, 2026-11-04T21:00Z), 10-minute grid to 2026-11-06T00:00Z; tier snapshot (liquidity) at the first pass; Gamma map refresh every 6 h; receipt times; gaps logged as unavailable; no exit-75 path in the window (degrade to top level on projection overrun; stop only below 2 GB root free)", "family": "creative_batch_15", "priority": 0, "expected_value": "the one night of E data at recorded books", "data": ["public CLOB /books", "public Gamma"], "resources": {"mem_mb": 200, "cpu": 1, "lane": "cron", "network": "clob, gamma-api"}, "depends_on": [], "argv": ["scripts/run_cb15.py", "e-live", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--not-before", "2026-11-02T12:00:00Z", "--until", "2026-11-06T00:00:00Z", "--disk-cap-gb", "SMOKE_SIZED_MIN_1.0", "--data-dumps-cap-gb", "40", "--no-exit75-in-window"], "timeout_s": 55, "max_retries": 0, "outputs": ["history/h15_elect_live/{books,tier,gaps,storage,manifest}/"], "next_action": "q0346 after 2026-11-06T00:00Z", "notes": "DRAFT-REVISED. Installed by the coordinator after the E freeze, by 2026-11-02T00:00Z (crontab line, as CB14 q0310), with the cpu pause/resume lines for [2026-11-03T21:00Z, 2026-11-04T22:00Z) dry-run on 2026-11-02. nice 5. The disk cap placeholder is replaced by 3x the smoke-measured size (>= 1.0 GB) before the freeze. Reads no AREPO store. Refuses if part E is not frozen."}
{"id": "q0346_cb15_screen_E", "title": "CB15-E: E1 (stratified balanced D-terms drift t_a -> t_a+12h by state sign within closing-hour strata; within-stratum permutation 9,999 draws seed 15101; sign share >= 0.60; net-of-control logit check; pre-night placebo; t_a/t_b, Senate+Governor, second-tier, key-overlap, leave-one-state-out robustness) and E2 (recorded best ask at t_a, best bid at t_b, no bid -> -9.3c, fee, +1c, no-depth worst case); gates GEI and GE; judged at p < 0.01 strict when it runs", "family": "creative_batch_15", "priority": 9, "expected_value": "E case-study verdicts (one night)", "data": ["history/h15_elect_live/"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0345_cb15_e_live"], "argv": ["scripts/run_cb15.py", "screen", "--family", "E"], "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch15/results_E.json", "trials.jsonl (cb15_test + creative_batch_15:E n_tests=2)"], "next_action": "ledger; a pass yields a 2028 registration draft only", "notes": "DRAFT-REVISED. Refuses before 2026-11-06T00:00Z and without the part-E freeze hash; writes the counted not-run (calendar) lines if part E was never frozen."}
{"id": "q0347_cb15_p_birth_census", "title": "CB15-P birth-order census, counts only, no network: C1 reproduction call (316/183), matches.json fields k_open, p_start, k_cat, ids; non-sports; key drops by source; Kalshi-first proxy (p_start - k_open >= 24 h) by lead bin and category; gate GPB (>= 60 pairs, >= 30 events)", "family": "creative_batch_15", "priority": 9, "expected_value": "decides whether CH130 has a population", "data": ["research_lab/cross_venue/{matches.json,audit_flags.json,audit_sample100.json} (sha256 pinned; fields listed)", "research_lab/cross_venue/series/ (pair list reproduction only)", "creative_batch15/exclusion_keys.csv.gz"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0340_cb15_exclusion_keys"], "argv": ["scripts/run_cb15.py", "p-birth-census"], "timeout_s": 600, "max_retries": 1, "outputs": ["research_lab/creative_batch15/census_P_birth.json", "trials.jsonl (cb15_descriptive or counted not-testable lines)"], "next_action": "PASS: commit q0349 after q0348", "notes": "DRAFT-REVISED. No series value used in any statistic; p_end never read; refuses any cross_venue_live path."}
{"id": "q0348_cb15_smoke_P", "title": "CB15-P smoke: C1 reproduction asserts and sha256s; reach to the first Data API transaction of an out-of-frame 2025 market (bounded or oldest-first query, else page count); Kalshi 1-minute candlesticks (historical and live endpoints); Kalshi /markets min_created_ts; result field discarded", "family": "creative_batch_15", "priority": 9, "expected_value": "go/no-go for P sources", "data": ["public Data API", "public Kalshi markets and candlesticks"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "net", "network": "data-api, kalshi"}, "depends_on": [], "argv": ["scripts/run_cb15.py", "smoke", "--part", "P", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--rps", "1"], "timeout_s": 900, "max_retries": 1, "outputs": ["research_lab/creative_batch15/smoke_P.json", "trials.jsonl (cb15_descriptive)"], "next_action": "PASS: q0349 (with q0347 PASS)", "notes": "DRAFT-REVISED. <= 30 requests; Kalshi <= 1 rps."}
{"id": "q0349_cb15_p_data", "title": "CB15-P data per Kalshi-first proxy pair: Gamma metadata (createdAt, startDate, endDate, feeSchedule, rule booleans, lifetime volume for the tercile check), Data API prints from the first transaction to t_d + 24 h 30 min and around t_L (aggregated to transactions), Kalshi 1-minute candlesticks over [t_birth-6h, t_d+25h] and [t_L-1h, t_L+25h], CLOB prices-history fidelity 10 after t_birth only plus a count of earlier points; rows >= 2026-10-12 refused", "family": "creative_batch_15", "priority": 8, "expected_value": "P births, gaps, targets and prints", "data": ["public Gamma, Kalshi, CLOB, Data API", "research_lab/creative_batch15/census_P_birth.json"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api, kalshi, clob, data-api"}, "depends_on": ["q0347_cb15_p_birth_census", "q0348_cb15_smoke_P"], "argv": ["scripts/run_cb15.py", "p-data", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--rps", "2", "--kalshi-rps", "1", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "40", "--budget-min", "45"], "timeout_s": 3600, "max_retries": 2, "outputs": ["history/h15_birth/{meta.csv.gz,tx.csv.gz,kalshi.csv.gz,prices.csv.gz,manifest.json}"], "next_action": "q0350", "notes": "DRAFT-REVISED. No outcome, side, wallet or hash stored. Resumable; incomplete = pending.", "repeat": {"max_runs": 3, "until_log_regex": "\"status\": \"p_data_complete\""}}
{"id": "q0350_cb15_census_P", "title": "CB15-P census, counts only: binding Kalshi-first from the first print, rule-boolean drops, units by label (no birth print, no Kalshi quote, no target, history target, ends early), seeded-history shares, g_d distribution (features at t_d), |g_d| >= 5c count, reach; gates GP and GPP (SE-only proxy at t_L); MDEs", "family": "creative_batch_15", "priority": 9, "expected_value": "P gates and MDEs before the freeze", "data": ["history/h15_birth/ (prints and prices after t_d only through the SE-only proxy; volume not opened)"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0349_cb15_p_data"], "argv": ["scripts/run_cb15.py", "census", "--family", "P"], "timeout_s": 900, "max_retries": 1, "outputs": ["research_lab/creative_batch15/census_P.json", "trials.jsonl (cb15_descriptive)"], "next_action": "science-reviewer freeze check (part P)", "notes": "DRAFT-REVISED. No slope, Delta or net written."}
{"id": "q0351_cb15_screen_P", "title": "CB15-P (selected on lifetime volume): P1 (event-weighted slope of the 24h print move on g_d; birth-minus-later contrast; opening-print joint fit; lowest-volume-tercile sign; within-month shuffle calibration; history-target, worn-window, 72h, 30-min, category, top-5, half robustness) and P2 (toward-Kalshi taker at recorded prints, |g_d| >= 5c; worst-case reach -9.3c; lowest-tercile sign; cost, entry, exit, stale robustness)", "family": "creative_batch_15", "priority": 9, "expected_value": "P verdicts", "data": ["history/h15_birth/"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0350_cb15_census_P"], "argv": ["scripts/run_cb15.py", "screen", "--family", "P"], "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch15/results_P.json", "trials.jsonl (cb15_test + creative_batch_15:P n_tests=2)"], "next_action": "advanced: q0353 after T15_P2_end", "notes": "DRAFT-REVISED. Refuses before the P freeze hash and unless GPB, GP, GPP passed (else counted lines)."}
{"id": "q0352_cb15_p_live", "title": "CB15-P birth watcher (cron hourly, outside lanes; causal selection, no volume filter): Gamma listings created in the last 2 h (non-sports), Kalshi open markets by min_created_ts, frozen matcher + r1 conflict rule, Kalshi open_time <= listing - 24 h; Data API first-print polls every 5 min; Polymarket /book and Kalshi orderbook at t_d and t_d + 24 h; weekly blind title-audit batch", "family": "creative_batch_15", "priority": 0, "expected_value": "P Stage 2 data at recorded books", "data": ["public Gamma, Data API, CLOB /book", "public Kalshi markets and orderbook"], "resources": {"mem_mb": 150, "cpu": 1, "lane": "cron", "network": "gamma-api, data-api, clob, kalshi"}, "depends_on": [], "argv": ["scripts/run_cb15.py", "p-live", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--not-before", "2026-11-04T00:00:00Z", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "40"], "timeout_s": 3000, "max_retries": 0, "outputs": ["history/h15_birth_live/{listings,pairs,first_prints,books,audit_batches}/"], "next_action": "runs to T15_P2_end or the cap; q0353 if triggered", "notes": "DRAFT-REVISED. Never reads cross_venue_live/. Stops at T15_P2_cap = 2027-04-30; the stop counts births, never results."}
{"id": "q0353_cb15_rep_P", "title": "CB15-P Stage 2: P1-rep (book mids; >= 60 pairs) and P2-rep (recorded best ask at t_d, best bid at t_d + 24 h, no bid -> -9.3c; >= 40 units with |g_d| >= 5c); +1c robustness", "family": "creative_batch_15", "priority": 9, "expected_value": "P Stage-2 verdicts (evidence level L2, causal selection)", "data": ["history/h15_birth_live/"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0351_cb15_screen_P", "q0352_cb15_p_live"], "argv": ["scripts/run_cb15.py", "rep", "--family", "P"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch15/results_P_rep.json", "trials.jsonl (cb15_replication + creative_batch_15:P:rep)"], "next_action": "pass: Stage P-P registration draft", "notes": "DRAFT-REVISED. Only triggered tests; alpha/2 if early, full Stage-2 Holm once."}
```

## 5. Code needed (not written by this document)

- `backend/astrolabe/research_lab/cb15_common.py`: reuse `cb14_common` / `cb13_common` for refused roots, disk guards,
  manifests and `*_complete` status, the cluster bootstrap with the small-G rule, Holm helpers (k1 = 4; E's early rule),
  per-part rules hashing, whitelist readers; new: the source-attributed key union and per-family key rules, the
  within-stratum state-label permutation.
- `cb15_e.py` (**first; calendar**): the census pager, race regex and control-market rule; the trade-market and
  two-party rules; GE0 file schemas, archive manifest and hash checks, the cross-table; the collector (`POST /books`
  batching, the pass grid, receipt clock, gap log, flock, map refresh, tier snapshot, storage projection and
  degradation, no exit 75 in the window); the `cpu` pause/resume flag and cron lines; units (`t_a`, `t_b`, reads within
  2 / 5 min, band and spread labels at `t_a`, the one-sided-book rule at `t_b`); strata and identifiability; E1 (stratified
  contrast, permutation, sign share, net-of-control logits, pre-night placebo, robustness), E2; GEI, GEC, GEP, GE.
- `cb15_p.py`: the C1 reproduction call (import `cb5_declaration.c1_pairs` or equivalent, sha256-pinned), the
  `matches.json` field reader, the birth-order census; the first-transaction reach (bounded, oldest-first or paged),
  print aggregation and the print-based `p(t)`; Kalshi candlestick and post-birth `prices-history` clients; `t_birth`,
  `t_d`, `t_L`, `g_d`, `Δ`; P1 (slope, birth contrast, joint fit, volume tercile, shuffle), P2 (prints, fees, reach,
  tercile); GPB, GP, GPP (SE-only); the Stage-2 watcher (matcher import, `min_created_ts`, first-print polling, book
  schedule, audit batches).
- `backend/scripts/run_cb15.py` with the §4 subcommands; refuses analysis before the family's freeze hash.
- Tests (`test_cb15_e.py`, `test_cb15_p.py`, `test_run_cb15.py`): forbidden-field fixtures (`side`, `proxyWallet`,
  `outcomePrices`, `closedTime`, Kalshi `result`), refused roots (`cross_venue_live`, `surprise_live`, `h11_*/holdout`);
  E: the two-party rule, `s = 0` without an archived source, the band and spread edges at `t_a` (0.10 accepted, 0.0999
  not), **no exclusion at `t_b`** (a 40c spread kept; no bid → mid uses 0; E2 no bid → `w*`), reads at 2 min accepted
  and 2 min 1 s not, the grid placing `t_a − 36 h`, `t_a − 24 h`, `t_a + 24 h` on reads, state weighting, strata
  (a stratum with one sign only dropped; `w_h`; the contrast cancelling a constant added to every state of a stratum;
  the permutation never moving a label across strata), the logit clamp, GEC at 9 versus 8 per sign, GEP stratified,
  the not-run (identifiability) and (calendar) paths, refusal before `T15_E_pre` and after `T15_E_end`, the no-exit-75
  path and degradation, the pause/resume flag; P: key drops by source (a C1-only key kept, a C1 + CB11-P key dropped),
  `t_birth` from the first transaction (a `prices-history` point at 0.50 before it ignored), "no birth print", `p_d` as
  the last print at or before `t_d`, the history-target label, Kalshi-first at 24 h exactly, `p_end` never read, rows at
  2026-10-12 refused, the tercile check with 14 units → unknown, entry max and exit min prints, `w*`; `battery2` kinds
  and k1 = 4 fixed; E's early judgement at 0.01 strict; α/2 early rule in Stage 2.

## 6. Test budget and compute

| Job | Tests counted | Kind(s) | Decision |
|---|---|---|---|
| Stage 1: E1, E2, P1, P2 | **4** | `cb15_test` + count lines `:E` (2), `:P` (2) | p < 0.01 strict, floor, binding placebos and robustness, batch Holm (one-sided α 0.05, k1 = 4 fixed; E judged when it runs, never withdrawn); counted with p = 1 if a gate, audit, smoke, identifiability or the E calendar fails |
| Stage 2: P1-rep, P2-rep (each only if triggered) | ≤ 2 | `cb15_replication` + `:P:rep` | one Holm over CB15 Stage 2 (early finishers at α/2) |
| Smokes, GE0, audits, pre-gates, censuses, strata, sign share, tiers, the L withdrawal | 0 | `cb15_descriptive` | - |
| **Total** | **4 fixed + ≤ 2 conditional = 4-6** | | value at the run after the host union (1,232 on HEAD at drafting; not stable) |

**Host compute.** Under 1.5 CPU-hours at nice 19 (E: about 1,000 tokens × 1,600 passes reduced per state; P: ≤ 150
pairs). Peak RAM 0.4 GB (collector 0.2 GB). **Network.** ≤ about 3,200 historical requests; E collector about 15,000
requests over 3.5 days at ≤ 0.17 rps; P watcher ≤ 3,500 a day. **Disk.** ≤ 1.2 GB (E's cap set from the smoke).

**CH129 calendar (what must exist by when; all UTC).**

| By | Deliverable | Owner |
|---|---|---|
| 2026-10-20 | GE0 compilation starts for all 50 states + DC (two network-enabled passes, archive) | orchestrator (agents with network) |
| 2026-10-21 12:00 | `seals/cb15_rules.json` parts `common` + `E` committed; q0341 code and tests; q0341 at priority 99 with a 2-h hold | implementer, coordinator |
| 2026-10-23 | GE0 committed: sign table, poll-close table, party map, cross-table, archive manifest; `science-reviewer` archive audit | compilers, `science-reviewer` |
| 2026-10-26 | collector, cron pause/resume lines and E analysis code with tests; q0343 smoke PASS (bytes per pass measured; q0345 cap set) | implementer, queue |
| 2026-10-29 | code-against-design freeze check (part E); q0344 PASS (GEI, GEC, GEP) | `science-reviewer`, queue |
| **2026-11-01 12:00** | **part E frozen** (`model_specs/cb15_v1.json` part E, pinning rules, GE0 files and race map sha256) | orchestrator |
| 2026-11-02 00:00 | q0345 installed with the pause/resume lines; dry pass | coordinator |
| 2026-11-02 12:00 | first pass (tier snapshot); `cpu` pause/resume dry run (12:00-12:10Z); pre-night disk check | collector, coordinator |
| 2026-11-03 21:00 - 11-04 22:00 | `cpu` hold active; every-minute passes 22:00-21:00 | cron, collector |
| 2026-11-06 00:00 | collector stops; q0346 runs | queue |

A missed row before the freeze is recovered only if the freeze still lands by 11-01T12:00Z; otherwise E is "not run
(calendar)", counted. P has no calendar binding and follows CB11-CB14 on the `net` lane.

## 7. Main scientific risks (for the challenger)

Revised after round 1; the items of §9 are cited.

1. **E is one night.** Stratifying by closing hour removes a repricing that is common at a clock time within a stratum
   (item 1), and the net-of-control logit check binds; a swing that interacts with the sign (for example, a swing
   concentrated in mail votes) still does not cancel. Inference treats the states of a stratum as exchangeable. Power
   reaches about 15c at best, and the identified strata may be too few (then "not run (identifiability)", counted).
2. **E's sign table is judgement.** Archived sources, two network-enabled passes, an agreement rule and a read-only
   archive audit reduce compiler bias (item 3); the compilers' model memory may hold 2026 information, which the archive
   rule cannot remove (disclosed). The window is wall-clock from poll close (premise 2), so slow-reporting states
   contribute less drift (power, not sign). Liquid races are kept; professionals may price the shift.
3. **P is thin, worn and volume-selected.** Non-sports C1 is 167 pairs; P2 likely fails GP; losses to "no birth print"
   reduce it further (item 9). Gap convergence is known (C1 r1, E010), so P1 carries the label "birth" only through the
   later-life contrast; the volume tercile check binds and only P-rep can lead to Stage P (item 10). P keeps C1-only
   keys by declared deviation (accepted, item 11).
4. **E's key rule** (calendar disjointness, keys as a robustness check) departs from the full key rule (accepted, item
   11).
5. **Collector risk on the night.** One host, 1 OCPU, shared with live collectors; the `cpu` hold, the smoke-sized cap,
   degradation instead of exit 75, and gap logging (items 4, 8). The `/books` batch cap is unverified above 2 tokens
   (smoke).
6. **Fees** use the current `feeSchedule` with a 0.04 floor (as CB14).
7. **CH125 is not tested** (withdrawn uncounted; §0.4).

## 8. Next actions

1. Round 1 is answered (§9-§10). Next review: the code-against-design freeze check (`science-reviewer`), part E first;
   it may reopen any round-1 item. Open to it: the stratum weights `w_h`, the one-sided-book rule at `t_b`, the
   history-target fallback in P.
2. Orchestrator: start GE0 now (two network-enabled compiler passes over 50 states + DC, archived), then the archive audit.
3. Implementer: `seals/cb15_rules.json` parts `common` + `E` and the q0341 path by 2026-10-21; collector, cron lines and E
   analysis by 2026-10-26 (§6). P code after E's freeze.
4. Coordinator: accept the priority-99 exception and place the 2-h `net` holds before q0341, q0343 and q0344; install
   q0345 and the pause/resume lines by 2026-11-02T00:00Z; dry run on 2026-11-02.
5. E order: q0341 → GE0 → q0343 → q0344 → **E freeze by 2026-11-01T12:00Z** → q0345 → q0346 after 11-06T00:00Z.
6. P order: q0340 (behind CB14 q0302) → q0347 (GPB) → q0348 → q0349 → q0350 → P freeze → q0351; q0352 from 2026-11-04;
   q0353 if triggered.
7. Ledger: one descriptive line for the CH125 withdrawal; lines for every counted result. CB16 adds CB15's frame ids.
   Checkpoint and plain-English dashboard updated by the orchestrator.

## 9. Challenger review, round 1 (science-reviewer, 2026-10-19)

**Verdicts: CB15-E REVISE (4 blocking), CB15-P REVISE (2 blocking), CB15-L WITHDRAW uncounted.** Recorded as received
via the coordinator.

| Item | Family | Blocking | Finding and required change |
|---|---|---|---|
| 1 | E | yes | A national swing does not cancel: windows are per state (`t_close + 90 min`; closes run 00-06Z), so a national repricing hits some windows and not others, and late-count sign clusters by region, confounding sign with closing time; the logit shift is not additive in price. Publish the GE0 sign × closing-time-bin cross-table before the freeze (no prices); compute `T_E1` within hourly closing-time strata with permutation within strata only; if surviving strata fall below GEC, E is "not run (identifiability)", counted; add a binding check of drift net of the national House/Senate control market over the same clock window, in logits |
| 2 | E | yes | Excluding races with spread > 20c at `t_b` selects on the post-entry state. E1 uses the mid; E2 exits at the recorded best bid, and no bid prices the unit at `w* = −9.3c` |
| 3 | E | yes | Read-only reviewers have no network, so their citations could be invented from memory. Require a network-enabled compiler that archives each source (URL, fetch time, sha256) into GE0; a state without an archived source gets `s = 0`; compile all 50 states + DC now; disclose that model memory may contain 2026 information |
| 4 | E | yes | Priority 30 does not protect the calendar (drafts at 32-49 exist; lanes do not pre-empt). Run q0341/q0343/q0344 at priority 99 with the coordinator holding `net` promotions for 2 h before each, or as one-shot commands. The `cpu` hold has no mechanism: commit cron pause/resume lines covering `[11-03T21Z, 11-04T22Z]` and dry-run them on 11-02 |
| 5 | E | no | Put passes on the :00/:10 grid so `t_a − 36 h`, `t_a − 24 h` and `t_a + 24 h` fall on a read |
| 6 | E | no | GEC must be ≥ 9 per sign (at 8 the MDE is 15.8c and GEP fails anyway). Accept the 3× floor only as declared for a one-night case study, with no claim beyond that night |
| 7 | E | no | E is judged at α/k1, strictly, when it runs; the final Holm can only add passes |
| 8 | E | no | Measure stored size per pass (~1,000 tokens) in the smoke before the freeze; an exit 75 at the 0.3 GB cap on the night would stop the collector with no restart, so size the cap with margin and use no exit-75 path on the night |
| 9 | P | yes | `t_birth` = the first Data API print; `p_d` = the last print at or before `t_d`; no print → "no birth print", counted. `prices-history` only after the first print (resampled, not point-in-time; can be seeded at 0.5 before the first trade, making `Δ ≈ g_d` by construction). Report the share of pairs affected |
| 10 | P | yes | The C1 population is selected on lifetime volume (future information). Either rebuild the frame causally at `t_d`, or label P1/P2 "selected on lifetime volume", add a binding check that the sign holds in the lowest volume tercile, and state that only P-rep (causal selection) can lead to Stage P |
| 11 | P | no | q0353's `expected_value` typo ("L2 verdicts"). The P key deviation and the q0340/q0352 timing are accepted |
| L | L | - | WITHDRAW uncounted: no L outcome, price or leader has been seen; the archived pages hold no table; the planning MDE is above GLP. Record like CB14's CH127 "not a test". P5-P6 fetched captures dated inside L's window (one more reason to restart cleanly later). After the withdrawal, k = 4 fixed + ≤ 2 conditional; fix k1 = 4 now and record that the change comes from the withdrawal, not from Holm power |

## 10. Response to challenger round 1 (2026-10-19T04:32Z)

One response round. **8 adopted, 3 adopted with a stated modification, none rejected; L withdrawn.** No floor,
threshold, gate, alpha or cap was relaxed.

| Item | Response | Where |
|---|---|---|
| 1 | **Adopted, with a stated modification (the stratum weights).** Strata = the UTC hour of `t_close`; only strata with both signs are identified; `T_E1` combines within-stratum balanced contrasts with weights `m_h = n₊ₕn₋ₕ/(n₊ₕ + n₋ₕ)` (the inverse-variance weight of a two-group contrast; the reviewer named no weight); permutation within strata; GEI makes too few identified strata "not run (identifiability)", counted; the cross-table is committed with GE0 before the freeze; the binding net-of-control check uses the chamber-control market of each race (Governor races: the mean of both), in logits with a [0.01, 0.99] clamp, and is "unknown" (blocking) if a control market is unmapped. GEP uses the stratified variance | §0.2 premise 4, §CB15-E, §2.3 |
| 2 | **Adopted.** No exclusion at `t_b`; E1 uses the mid whatever the spread, with a one-sided book using the missing side's bound (no ask → 1, no bid → 0), which is the price bound rather than a selection; E2 exits at the recorded best bid, no bid → `w*` | §CB15-E, §2.1 |
| 3 | **Adopted, with a stated modification.** Two independent **network-enabled** compiler passes (not the read-only reviewer) over 50 states + DC, starting now; every source archived (URL, fetch time, sha256, file); no archived source → `s = 0`; disagreement → `s = 0`. **Added:** a read-only `science-reviewer` audit of the archive (support and no-2026-source check), which the reviewer can do without network. Memory disclosure in §CB15-E and §7 | §CB15-E, §1.1 |
| 4 | **Adopted.** Priority 99 with a 2-h `net` promotion hold before q0341, q0343 and q0344, or a one-shot command after the running `net` job if the hold cannot be placed; committed cron pause/resume lines for `[2026-11-03T21:00Z, 2026-11-04T22:00Z)` (a lane-pause flag, added and unit-tested if the runner lacks one), dry-run on 2026-11-02 | header, §1.2, §2.8, §4, §6 |
| 5 | **Adopted.** Passes on the 10-minute grid (hh:00, :10, …) outside the night window and every minute inside it; poll closes fall on the hour or half hour, so every declared offset of `t_a` lands on a pass | §1.2 |
| 6 | **Adopted.** GEC ≥ 9 states per sign (within identified strata); the 3× floor stands only as declared for a one-night case study with no claim beyond that night | §CB15-E, §0.4, §2.9 |
| 7 | **Adopted.** E is judged when it runs at `p < min(0.01, α/k1)` = 0.01, strict (with k1 = 4, α/k1 = 0.0125); never withdrawn; the final Holm can only add passes | §2.3 |
| 8 | **Adopted.** The smoke measures stored bytes for one ~1,000-token pass; the q0345 cap is 3× the projected total (≥ 1.0 GB), set before the freeze; no exit-75 path inside the window (degrade to the top level on projection overrun; stop only below 2 GB root free); a pre-night disk check on 11-02 | §2.8, §CB15-SM, §4 |
| 9 | **Adopted, with a stated modification (target fallback).** `t_birth` = first Data API transaction; `p_d` = last print at or before `t_d`; "no birth print" counted; `prices-history` only after `t_birth`; the seeded-history shares are reported. **Modification:** where no print lies in `[t_d + 22 h, t_d + 24 h]`, the post-birth `prices-history` point is used as a labelled "history target", and a binding robustness drops those units (the target, unlike the gap, cannot be seeded once trading has begun; dropping them outright would select on later inactivity) | §CB15-P, §2.2 |
| 10 | **Adopted (the label option).** A causal rebuild at `t_d` is not possible from the C1 universe, which was built from closed markets by volume; P1 and P2 are labelled "selected on lifetime volume", the lowest-volume-tercile sign check binds for both (< 15 units → unknown → no advance), and only P-rep (causal selection, no volume filter) can lead to Stage P | §0.2 premise 6, §CB15-P, §2.9 |
| 11 | **Adopted.** q0353's `expected_value` now reads "P Stage-2 verdicts (evidence level L2, causal selection)" | §4 |
| L | **Adopted.** CH125 withdrawn uncounted and recorded as "not a test" (§0.4); its jobs (former q0354-q0363) are removed and their ids stay reserved; the P5-P6 exposure is recorded in §0.3. **k = 4 fixed + ≤ 2 conditional = 4-6; k1 = 4 fixed now; the change comes from the withdrawal, not from Holm power.** Stage-2 early finishers are judged at α/2 (the largest possible Stage-2 k) | §0, §0.4, §2.3, §2.5, §6 |

## 11. Pre-data amendments after the part-E code-against-design freeze check (2026-10-19)

Written before any E book was collected (q0341 counts only ran; no price read). Each item tightens or clarifies; no floor, threshold, gate, alpha or cap changed. Part E resealed
(`seals/cb15_rules.json`: common `13c70322…` unchanged, E `10ab88e7…`, P `198b7fab…` unchanged).

| Fix | Amendment | Where |
|---|---|---|
| 1 (HIGH) | **Called / closed races are not dropped at `t_b`.** A missing read at `t_b` is a closure (not a collector gap) only with evidence logged by the collector after the token's last successful read: a successful `/books` batch that omitted the token, or a map refresh showing the market unlisted or inactive, by `t_b + 5 min`. Then the last read before closure stands: the mid by the one-sided rule (E1), and for E2 the exit at that read's best bid (none → `w*`). Counted as "closed before t_b (last read)". Closure evidence before `t_a` is a counted pre-entry state ("closed before t_a"). Without evidence a missing read stays "unavailable (gap)". The control markets use the same rule. Absent tokens are logged in full (no truncation). | `cb15_e.race_unit`, `read_or_closed`, `closure_evidence` |
| 2 (HIGH) | The collector's Gamma calls (tier snapshot, map refresh) run after the pass is recorded, with no retries and a 10-s timeout; each attempt is marked before it runs (refresh every 6 h even after a failure; tier retried at most every 10 min). | `e_live`, `gamma_markets` |
| 3 (HIGH) | q0343 smoke: a transient `/books` fault (transport, 408, 429, 5xx after the one retry) or an NTP failure is "pending" (exit 75), never a counted FAIL; out-of-frame tokens come only from order-book markets accepting orders; a family with a terminal record is never smoked again. | `smoke_online`, `out_of_frame_tokens`, `run_cb15 smoke` |
| 4 (HIGH, ops) | **Deploy freeze:** from the part-E freeze to 2026-11-06T00:00Z no deploy may change `cb15_common.py`, `cb15_e.py` or any shared-helper module hashed into common (cb2_weather, cb6_tail, cb8_books, cb8_common, cb9_common, cb10_common, cb12_common): `e-live` re-verifies these hashes every minute and refuses on a change. A watchdog (`run_cb15.py e-watchdog`, cron every 5 min) alerts through the notifier (`breakage`, deduped hourly) when the heartbeat is missing or older than 3 min inside `[T15_E_pre, T15_E_end)` and when a cpu-lane job with `mem_mb ≥ 500` runs inside `T15_cpu_hold`. A refused invocation writes `last_refusal.json` and leaves the heartbeat stale. | `cron_lines`, `run_cb15 e-watchdog` |
| 4b (ops) | The cpu hold blocks promotion only, so it is **placed at 2026-11-03T15:00Z** (6 h before `T15_cpu_hold` starts) and released at 2026-11-04T22:00Z; the 11-02 dry run is unchanged. | `T15_CPU_HOLD_PLACE` |
| 5 (MED) | The tier snapshot is taken only in `[T15_E_pre, T15_E_on)`; a snapshot stamped at or after `T15_E_on` is never used (tiers then unknown: the second-tier robustness cannot hold). | `tier_snapshot`, `load_screen_inputs` |
| 6 (MED) | A race with more than one member naming Democrat(ic) has no trade market ("ambiguous D party members", excluded and counted). This also changes the counts-only `trade_type` column of the q0341 census for such events (no other census field). | `trade_market` |
| 7 (MED) | An untestable pre-night placebo is unknown and never counts as met (§2.3): E1 cannot advance. | `e1_test` |
| 8 (LOW-MED) | The calendar check uses the first commit of `model_specs/cb15_v1.json` that carries the **pinned race-map sha256 value**. | `e_freeze_commit_time` |
| 9 (LOW, declared) | (a) A single-member party market (YES = D) passes the two-party rule, labelled `single_party_market` and reported. (b) If a chamber has ≠ 1 control-market candidate, the coordinator may name one D member market id from the q0341 census before the freeze (`--control-senate`/`--control-house`; no price read; recorded in `pregate_E.json`). (c) Tiers are computed over all mapped trade markets of the frozen race map (not over the races eligible on the night). | §CB15-E |
| 10 (LOW) | The pre-gate writes the race map under a temporary name and renames it only after `pregate_E.json` is written; screen E verifies the rules hash before its time gate; E2 reports the states dropped for lacking one side's net. | `run_cb15`, `e2_test` |

## 11b. Pre-data amendments after the part-P code-against-design freeze check (2026-10-19, science-reviewer REVISE)

Written before any P statistic, print, price or book was read (q0347 has not run; the watcher has not started). Each item makes the code match the design, or declares a deviation with its reason; no floor, threshold, gate, alpha, cap or population rule was loosened. Part P resealed (`seals/cb15_rules.json`: common `13c70322…` and E `10ab88e7…` unchanged; P `198b7fab…` replaced, new sha in the file).

| Fix | Amendment | Where |
|---|---|---|
| P-1 (HIGH) | **A Stage-2 read counts only if `due <= receipt <= due + lag`** (lag 2 min for the `t_d` read, 5 min for the 24-h read; `receipt` taken after the response; `due` recomputed from the birth). The watcher checks the window against the clock at the read, retries a failed HTTP read inside the window, and **never stores a failed read** (any leg non-200 or a transport error). A failed or missed read is "unavailable (read)", a stored empty / wide book at `t_d` is "no two-sided quote at t_d" (separate labels). Declared: a Polymarket `/book` **404 (no order book) is an empty book**, a recorded read; Kalshi must answer 200. | `read_books`, `p_live`, `valid_reads`, `rep_units` |
| P-2 (HIGH) | **Scheduling.** The watcher (cron every minute, flock, 55-s timeout) does the reads first, then first-print polls of ELIGIBLE pairs only (not sports, not Polymarket-first, not audit-conflict, not rule-boolean-different), then the hourly Gamma listing scan against the Kalshi cache. The Kalshi cache (full daily, `min_created_ts` hourly) moves to its own job `p-cache` (q0354: own flock, hourly cron, 3,000-s timeout, resumable by cursor, atomic cache replace only when a job completes; starts one day before `T15_P2_start`, public open-market list only). A missing or older-than-4-h cache skips the scan and is logged (the 2-h lookback re-covers). The 3,500/day cap is shared; scans, polls and the cache stop 300 requests before it so the reads keep priority; the cache's own share is 1,800. | `p_live`, `p_cache`, `run_cb15 p-cache` |
| P-3 (HIGH) | **P1-rep target.** The 24-h Polymarket mid uses the one-sided-bound rule of CB15-E (no ask -> 1, no bid -> 0, whatever the spread), so no unit is dropped after entry. Units are still dropped before entry (no two-sided Polymarket and Kalshi quote at `t_d`, counted). The section 2.6 (iv) availability gate (< 60% of eligible -> "not testable (availability)") is added to P1-rep and, likewise, to P2-rep (available = units with a recorded ask at `t_d`, eligible = units with `|g_d| >= 5c`). | `mid_one_sided`, `rep_units`, `rep_p` |
| P-4 (HIGH) | **Top-5 cluster drops** (event and week, Stage 1 and rep) hold only if the one-sided p of the kept units is < 0.01 AND the estimate is at or above the floor (section 2.6 ii), as CB14-S. | `sign_checks` |
| P-5 (MED-HIGH) | **Non-200 candles / prices-history leave the pair pending.** The shared `cross_venue.fetch_k_candles` and `history_backfill.fetch_prices` skip a non-200 silently; they are unchanged (other batches depend on them). q0349 uses status-aware copies inside `cb15_p` (hashed with part P, with their chunk sizes and the sha256 of the shared `parse_k_candles`): any non-200 raises, the pair is not written finished (`attempts.jsonl` records the request statuses), the run ends "in progress" and never completes with a pending pair. | `fetch_k_candles_checked`, `fetch_prices_checked`, `p_data` |
| P-6 (MED) | **Rule-boolean exclusion applied.** Polymarket is declared to have `is_provisional = can_close_early = False`; a pair whose Kalshi flag is true (q0349: the C1 universe rows; live: the Kalshi market record) is excluded and counted ("rule booleans differ"); a missing flag is not an exclusion (counted as unknown). | `rule_booleans_differ`, `unit_features`, `match_new` |
| P-7 (MED) | **Key rule.** q0347 re-reads the frames recorded "absent at q0340" (id columns only) and adds their ids as sources; q0349 checks ALL keys of each pair (market id, Gamma event ids, `negRiskMarketID`, series ids, all from the Gamma market record via `gamma_meta`) with the per-source P rule (a C1-only key is kept). A pair with a dropped key is labelled "key drop" and is not a unit. | `reread_absent_frames`, `gamma_meta`, `p_data`, `unit_features` |
| P-8 (MED) | **Matcher.** `match_markets` runs against the full Kalshi open-market cache (C1 mutual best as frozen); each pair's own lead is checked afterwards (`kalshi_first`), not by pre-filtering Kalshi markets opened less than 24 h before the listing. | `match_new` |
| P-9 (MED) | **Stop rule** counts only usable births: eligible, not late, both reads in their windows. | `births_with_24h_read` |
| P-10 (MED) | The P1 availability denominator includes the "no Kalshi quote" units. | `p1_test` |
| P-11 (MED) | Duplicate reads: the first in-window read per pair and read is used. | `valid_reads` |
| P-12 (MED) | Host load: the disk guard runs at most hourly; the 0.05 GB live-directory cap is enforced (over it: no new pair is taken, reads continue, logged hourly); each listing is logged once. | `run_cb15 _hourly_disk_check`, `p_live` |
| P-13 (LOW, declared) | (a) The rep requires both venues' quotes at `t_d` to be two-sided with spread <= 10c (the Kalshi rule of section 2.2 applied to Polymarket; a wider book is "no two-sided quote at t_d", counted). (b) The top-5 drop is skipped for a way with fewer than 15 clusters (its leave-one-cluster-out sign rule binds; CB10 small-G rule, section 2.3) and leave-one-quarter-out is skipped with a single calendar quarter (the halves bind); both are recorded in the result. (c) Cadence: the watcher runs every minute with a 55-s timeout (the reads need minute resolution inside 2- and 5-minute windows) instead of hourly with a 3,000-s timeout; the hourly work is the listing scan, the 3,000-s timeout belongs to the cache job. Kalshi load: the watcher's calls are sparse and the cache runs at <= 0.5 rps, so the combined Kalshi rate stays <= 1 rps. | `sign_checks`, `rep_units`, `declared` |
| P-14 (LOW) | The census reports the print-target, history-target and no-target counts (presence only; no price or change leaves the function) and the rule-boolean, key-drop and unknown counts. | `target_availability`, `census_p` |
| P-15 (LOW, ops) | `mem_mb` of q0347 and q0348 is 900 (the C1 reproduction call ran at 900 elsewhere), which supersedes the "`mem_mb` <= 600 everywhere" line of section 2.8 for these two jobs (queue rules unchanged: `MemAvailable >= mem_mb + 1200`, the 02:45-05:30 UTC blackout for `mem_mb >= 500`); q0352 and q0354 are 300. | drafts q0347, q0348, q0352, q0354 |

### 11b-2. Further pre-data amendments after the P-1..P-15 re-check (2026-10-19 ~14:45Z, science-reviewer ACCEPT_WITH_FIXES)

Still before any P statistic, print, price or book was read (q0347, q0349 and q0352 have not run). No floor, threshold, gate, alpha or population rule was loosened; every item narrows what may be called a unit or makes an operational limit binding. Part P resealed again (common `13c70322…` and E `10ab88e7…` unchanged).

| Fix | Amendment | Why | Where |
|---|---|---|---|
| P-16 (MED-HIGH) | **Scheduled-end exclusion in Stage 2.** The listing's `endDate` is stored at the match (`end_sched`). At the first-print detection a pair with `endDate < t_birth + 10 min + 25 h` is "ends early (scheduled)": no reads are made, it is counted, and it is outside the availability denominators (the Stage-1 rule of section 2.2 applied to Stage 2). A missing `endDate` is not an exclusion (counted "scheduled end unknown"). A Polymarket `/book` 404 at the 24-h read is **not** an empty book: the unit is "unavailable (no order book at 24 h)", stays in the availability denominators (P1: eligible; P2: the `|g_d| >= 5c` set), has `delta = NaN` and enters neither estimate. The P-1 rule that a 404 is an empty book is kept for the `t_d` read only. Uses only the listing's endDate (never `closedTime`). | A market that closes before the 24-h read returns 404; reading that as an empty book invented a mid from the one-sided-bound rule. | `p_live`, `rep_units`, `rep_p2_net`, `read_books` |
| P-17 (MED) | **Terminal "unavailable (source)" rule for q0349.** A pair with >= 3 failed attempts in 3 separate runs, first to last >= 15 min apart, becomes "unavailable (source)": a finished record (no data), counted in the labels and the manifest (`unavailable_source`), in the P1 availability denominator (eligible, unavailable), and in P2 at the worst-case reach `w*`; it is never a unit. Applied at the start of the next invocation from `attempts.jsonl` (one record per failed attempt with the run id), so the run can complete. Same item: a 404 on the frozen Kalshi candle endpoint (live vs historical split) is tried ONCE on the other endpoint and accepted only if every candle has the fields the frozen parser reads; otherwise the chunk fails. Declared before any failure was observed. | q0349 never finished if one pair always failed (non-200 leaves the pair pending forever). | `p_data`, `fetch_k_candles_checked`, `unit_features`, `p1_test`, `p2_units` |
| P-18 (LOW-MED) | **Only the legs the analysis uses are required.** `t_d`: Polymarket YES and Kalshi (plus NO when `g_d <= -5c`); 24 h: YES (plus NO when the `t_d` read put P2 on NO). Kalshi is not read at 24 h (nothing uses it), so a failed unused leg can no longer drop a unit. | A failed unused Kalshi leg at 24 h dropped the unit. | `read_books`, `p2_side` |
| P-19 (MED) | **Kalshi cache disk accounting.** The cache lives in its own subfolder (`kcache`) with its own cap (0.25 GB, set before any size was observed). The cache job stops paging over that cap (old cache stays; logged). The watcher holds the live files to the 0.05 GB live cap and the TOTAL (live files + cache folder) to live cap + cache cap, so the cache is counted. The q0348 smoke adds `p_kalshi_open_cache` (<= 3 pages, counts and bytes only, projected size at the page cap against the cap). | The cap did not count the cache, which can be the largest file. | `p_cache`, `p_live`, `cache_size_probe` |
| P-19b | The shared daily request count is written after every page (cache) and every request batch (watcher), and re-read before every check. | Concurrent jobs held a count from run start. | `p_cache`, `p_live` |
| P-20 (declared; needs ruling) | **Polymarket rule booleans declared UNKNOWN, not False** (Polymarket exposes no such field at listing and its markets can resolve early). The design is silent for unknown; conservative choice: exclude every pair whose Kalshi flag is true, keep pairs whose Kalshi flags are false or missing; the residual mismatch is bounded by P-16 and the 24-h availability label. Code behaviour is unchanged from P-6; only the declaration text differs. **Science ruling still open** (see ledger). | The P-6 assumption `can_close_early = False` for Polymarket had a weak factual basis. | `rule_booleans_differ`, `POLY_RULE_BOOLEANS` |
| P-21 (LOW, declared) | The mutual-best step of the matcher is over the new listings (Kalshi side: the full cache), not the whole Polymarket universe. | Wording only: states what P-8 already did. | `match_new` |
| P-22 (LOW) | (a) **Daily cap:** a read needs room for all its legs (<= 3 requests), so the 3,500 cap is not overshot by a read. (b) **Kalshi rate:** watcher 0.5 rps + cache 0.5 rps = 1 rps combined (the watcher default was 1 rps, giving 1.5), enforced per command by the runner. (c) **Cron:** the crontab lines carry `timeout 55` (q0352) and `timeout 3000` (q0354) in addition to flock. (d) The shared `disk_check.json` is replaced atomically (a torn stamp means "check now"). | Re-check LOW items. | `p_live`, `run_cb15.py` |
| P-23 (MED) | **Run gap and `max_runs` for q0349.** The queue worker re-starts a repeat run immediately, so the P-17 "3 runs >= 15 min apart" could not be guaranteed and was unreachable within `max_runs: 4`. (a) `p-data` records the end of every run that leaves failed pairs (`run_stamp.json`) and a run starting < 15 min later exits 75 (worker: `retry_wait` 30 min; not a run, not an attempt, 48-tempfail cap far away). (b) `repeat.max_runs` 4 -> 8: 3 failing runs + 1 labelling run (the label is applied at the start of the next run) + 4 spare runs in case a budget-limited early run delays a pair's first attempt. Thresholds unchanged. | The terminal rule was unreachable in practice. | `p_data`, `cmd_p_data`, q0349 |
| P-24 (LOW-MED) | **Empty fallback reply.** The other-endpoint candle fallback (P-17) needs a NON-EMPTY `candlesticks` list with the parser's fields (`all()` of an empty list is True). An empty or missing reply fails the chunk: the pair is pending and, by P-17, "unavailable (source)", never "no Kalshi quote". | An empty reply was silently accepted as "no candles". | `fetch_k_candles_checked` |
| P-25 (LOW-MED, declared before q0348's output is read) | **Cache cap binds.** The 0.25 GB Kalshi cache cap is NOT changed after any size is seen; the smoke's `within_cap` projection is informative only. If the projection (or the folder) exceeds the cap the cap binds: the cache stops adding pages (stale), this is logged, scans skipped for a stale cache are counted (`cache_cap_scans_skipped`), and new listings with no cached match (they would need an uncached Kalshi read) are counted `unavailable (source: cache cap)` (`cache_cap_unavailable`), never read. | Pre-declares the consequence of a size observation. | `p_cache`, `p_live`, `cache_size_probe` |
| P-26 (LOW) | **NO-side 404 at 24 h drops the unit from P2 only.** P1 uses the YES side only (P-18); a NO-book 404 now sets `unavailable_24h_p2` (label "unavailable (no NO order book at 24 h; P2 only)"): the unit stays in the P2 denominator with no estimate and stays in P1. A YES 404 is unchanged (P-16). | Dropping the unit from P1 contradicted P-18. | `rep_units`, `rep_p2_net` |
| P-27 (ruling on P-20) | **Polymarket early-close flags are UNKNOWN and disclosed.** The Kalshi true-flag exclusion (causal, from the Kalshi record at the match) is kept, label renamed "Kalshi early-close/provisional flag (excluded)". No unit is excluded or labelled by when the Polymarket market actually closed (post-t0, outcome-linked). Early-closing units stay in the denominators (live: "unavailable (no order book at 24 h)"; Stage 1: "no target"); a count may be reported descriptively, never as a gate. Disclosure: Stage 1 reads Gamma `endDate` after the fact and it may have been edited to the actual close date (the P-16 scheduled-end exclusion in Stage 1 uses that value; in Stage 2 it is the value stored at the match). | Closes the open P-20 ruling without using outcome-linked closing times. | `rule_booleans_differ`, label, rules `p6_ruling` |
| P-28 (LOW, pre-data confirmation fixes) | **Cache-cap accounting made complete and exclusive.** (1) While the Kalshi cache is stale over its cap and listing matching is skipped, the Polymarket new listings (ids and listing time, no prices) are still logged (`listings.jsonl`, flag `cache_cap_stale`) and counted (`cache_cap_listings_unmatched`), so the affected count is known. (2) `cache_cap_unavailable` is renamed `cache_cap_unavailable_upper_bound`: it also counts new listings that have no Kalshi counterpart, so it is an upper bound only. When the cap binds it ends enrolment of new pairs; that is a time-dependent rule (it depends on cache size and calendar time), never outcome-dependent. (3) `rep_p` (Stage-2 report) now carries the cap counters (`cache_cap`: scans skipped, listings unmatched, unavailable upper bound), previously only in state.json. (4) A NO-book 404 at 24 h is labelled once, as "ok (P1 only; NO book unavailable at 24 h)" (replacing the double count under "ok" and the P2-only unavailable label); the label counts now sum to the unit total (tested). No gate, threshold or formula changed. | Closes the four LOW items of the science-reviewer confirmation of 88f404a before any data is read. | `cache_cap_rule`, `NO_BOOK_24H_P2` label, rules |
| (docs) | q0348's notes no longer say "DRAFT, not in queue/jobs" (it is in `queue/jobs`, held by `not_before`, which the coordinator lifts); a disk test now checks the total-cap rule on its own. P resealed 6ac3b610 -> 7d856416 (common 13c70322, E 10ab88e7 unchanged). | Stale text. | q0348 notes, `test_total_cap_rule_on_its_own...` |

## 12. CB15-P birth-order census result (q0347, done 2026-10-21 18:06Z; counts only, no network)

Gate GPB: **FAIL.** 37 Kalshi-first pairs (proxy `p_start - k_open >= 24 h`, non-sports, after key drops) in 12 events, against the
minimum of 60 pairs in 30 events. Terminal record `terminal_P.json` (written 2026-10-21T18:06:22Z): status
`terminal_not_testable`, label "not testable (population)", reason "GPB: 37 pairs in 12 events", `counted` true, tests P1, P2.

**Consequence (design §Gates).** P1 and P2 are "not testable (population)", p = 1, **counted 2** (`creative_batch_15:P` count line,
n_tests 2, written 2026-10-21T18:06:22Z, results sha256 `db558cb4…`). q0349 is never committed, so q0350 and q0351 have nothing
to read, and the part-P freeze, the birth watcher (q0352), the cache (q0354) and q0353 are not installed. Nothing was fetched
for P beyond the C1 metadata and the 10-request smoke (q0348). CB15-E was already terminal (26 of 511 races).
