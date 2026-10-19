# Creative batch 15 (CB15): election-night reporting-order drift (one-night case study; one night is one cluster), the pair at birth, leaderboard incumbency hazard

`evidence_role: prospective` (CB15-E, a single pre-registered night; CB15-P Stage 2, CB15-L Stage 2) /
`exploratory_historical` (CB15-P Stage 1, CB15-L Stage 1) | status: **DRAFT (pre-challenger). Nothing frozen, nothing
queued, no code.** Drafted 2026-10-19 05:16 UTC+1 (2026-10-19T04:16Z) on parent `b21060c`. Nothing was fetched or
written for CB15 beyond the 9 counts-only keyless GETs of §0.3. **No CB15 quantity was computed:** no sign, drift, gap,
birth order, hazard, slope, net or resolution. The C1 birth-order census (a host query) was **not** run; it is job q0347.

This file turns three round-6 ideas from `CREATIVE_HYPOTHESES_2026-10-20.md` into declared, falsifiable tests:
**CH129** (election-night reporting-order drift, 2026-11-03) as **CB15-E**, **CH130** (the pair at birth) as **CB15-P**,
and **CH125** (leaderboard incumbency hazard) as **CB15-L**. It follows `CREATIVE_BATCH_14.md` (CB14) and
`CREATIVE_BATCH_13.md` (CB13) in structure and rules. "As CB14 §x" means that rule applies unchanged, including the
challenger fixes and the CB13-CB10 rules it cites. CB4 amendment A-C1 and the CB10 §2.3 small-G rule govern clusters.
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim. AREPO never
  trades. Every P&L is a paper rule at recorded prices (prints or books).
- Test tables bind once the CB15 declaration hash is committed (`model_specs/cb15_v1.json`), after a `science-reviewer`
  challenger round (§8) and a code-against-design freeze check. Rules (query lists, regexes, maps, windows, sign-table
  recipe, hazard recipe, gap rule, stored fields) are fixed in `seals/cb15_rules.json` before the first CB15 job.
  **Both files are hashed per part (`common`, `E`, `P`, `L`)**, so E can freeze on its calendar without waiting for P
  or L, and no rule of one part changes after another part's read.
- **CB15-E is calendar-forced.** Its rules part, sign table, race map, collector, tests and smoke must exist, and part E
  must be frozen, by **2026-11-01T12:00Z** (§1.2, §6). Otherwise E1 and E2 are "not run (calendar)", counted with p = 1.
- **Lanes.** P and L Stage-1 inputs are keyless public fetches (`net` lane, **priority 5-9, below every CB6-CB14 job**;
  CB14 net is 10-14). **Declared exception:** E's two pre-freeze `net` jobs (q0341 census, q0344 pre-gate; ≤ 700
  requests together, ≤ 15 min) run at **priority 30**, above CB11's 25-29, because the calendar binds; the coordinator
  must accept this (§8). Censuses, gates and screens run on `cpu`. The E collector (q0345), the P birth watcher (q0352)
  and the L poller (q0362) run as cron jobs outside the lanes, as CB14 q0310. **No CB15 object is bound to `T_seal`.**
- **Queue ids q0340-q0379, one id per job, no letter suffixes.** The brief said q0330+, but CB14 §0.1 reserves
  q0323-q0339 (committed), so CB15 starts at q0340. Checked at drafting: nothing at or above q0323 exists under
  `queue/` (CB14 drafts end at q0322). Specs are drafts **in this document only** (§4).
- **Naming.** Roots `history/h15_elect_live` (E), `history/h15_birth` and `history/h15_birth_live` (P), `history/h15_lb`
  and `history/h15_lb_live` (L); outputs under `research_lab/creative_batch15/`.

## 0. Summary, selection and scope

| Rank | Family | Hypothesis | Counted tests | Stage 1 data | Stage 2 data | Queue ids |
|---|---|---|---|---|---|---|
| 1 | **CB15-E** election-night reporting-order drift, **one-night case study; the night is one cluster** (CH129) | in 2026 US general-election races (Senate, Governor, House) listed on Polymarket, a state sign frozen before the night from the state's vote-mode counting order and the documented 2022/2024 direction of the late count predicts the direction of the D-terms mid drift from `t_a` = the state's last poll close + 90 min to `t_a` + 12 h, net of the night's common move (E1, balanced drift ≥ +5c); buying the predicted side at the recorded ask at `t_a` and selling at the recorded bid at `t_b` pays after fees (E2, ≥ +1.0c per share) | E1 (balanced drift), E2 (economic, recorded books) | **prospective, one night**: the E collector (CLOB `POST /books` every 60 s, receipt-timed) on a race map frozen by 2026-11-01T12:00Z | none in CB15 (a pass yields a registration draft for the next general-election night) | q0341-q0346 |
| 2 | **CB15-P** the pair at birth (CH130) | on the audited C1 Kalshi-Polymarket pairs where Kalshi opened ≥ 24 h before Polymarket's first price, the gap `g_d` = Kalshi mid − Polymarket price at `t_d` = first price + 10 min predicts Polymarket's move over the next 24 h (P1, slope ≥ 0.30, and larger than the same pairs' slope 7 days later); buying toward Kalshi at recorded prints when `|g_d| ≥ 5c` and exiting at 24 h pays after fees (P2, ≥ +1.0c per share) | P1 (slope), P2 (economic, recorded prints) | the C1 set's metadata on the host (birth-order census, no fetch) + fresh `h15_birth`: Kalshi 1-minute candlesticks and CLOB `prices-history` around each birth, Data API prints; every unit ends before 2026-10-12 | prospective birth watcher from `max(P freeze + 1 d, 2026-11-04T00:00Z)`: P1-rep, P2-rep at recorded books | q0347-q0353 |
| 3 | **CB15-L** leaderboard incumbency hazard (CH125) | in closed "top AI model at month-end" events, a frozen walk-forward survival model of the public leaderboard's own history (`q` = P(the incumbent still leads at the deadline)) predicts resolution beyond the incumbent's price (L1, slope ≥ 0.30); buying the model side at recorded prints when `|q − p| ≥ 6c` and holding to resolution pays (L2, ≥ +1.0c per share) | L1 (slope), L2 (economic, recorded prints) | **source-gated**: point-in-time leaderboard captures (Wayback; probes P5-P6 found no table in two captures), Gamma frame, CLOB `prices-history`, Data API prints; events end `[2024-07-01, 2026-10-01)` | prospective month-end events with an own poller from `max(L freeze + 1 d, 2026-10-27)`: L1-rep, L2-rep | q0354-q0363 |

**Counted: 6 fixed (E1, E2, P1, P2, L1, L2) + up to 4 conditional (P1-rep, P2-rep, L1-rep, L2-rep) = 6-10** (§2.5). The
budget is fixed now. No CB15 test is added after any CB15 read. **Honest expectation at drafting:** E runs if the
calendar holds, but is powered only for a drift of about 3× its floor (§CB15-E); P probably fails its population gate
(below 40 qualifying pairs is plausible); L probably fails its source gate. Each is still counted (§2.5).

### 0.1 Queue id mapping (one id per job)

| Id | Job | Family | Earliest commit |
|---|---|---|---|
| q0340 | `cb15_exclusion_keys` (CB14 q0302 key file + CB14 frames + seal copies, **with per-key source attribution**) | P, L (E: robustness only) | after CB14 q0302 completes (or its ledger stop record) |
| q0341 | `cb15_e_census` (counts only: active 2026 general-election races on Gamma by office and state; structure; completeness walk) | E | after the `common` + `E` rules parts are committed; **priority 30** |
| q0342 | reserved: GE0, the blind sign table, poll-close table and party map (two independent `science-reviewer` passes; repo step, no queue job) | E | - |
| q0343 | `cb15_smoke_E` (≤ 30 requests) | E | after the E collector and smoke code exist |
| q0344 | `cb15_e_pregate` (gates GEC, GEP; one `/books` pass for band counts) | E | after GE0 is committed and q0343 PASS; **priority 30** |
| q0345 | `cb15_e_live` (cron collector, 2026-11-02T12:00Z to 2026-11-06T00:00Z) | E | after the E freeze; installed by 2026-11-02T00:00Z |
| q0346 | `cb15_screen_E` (E1, E2) | E | after 2026-11-06T00:00Z |
| q0347 | `cb15_p_birth_census` (counts only, no network: birth order on the C1 metadata; gate GPB) | P | after q0340 |
| q0348 | `cb15_smoke_P` (≤ 30 requests) | P | after the P rules part and smoke code exist |
| q0349 | `cb15_p_data` (Gamma metadata, Kalshi candlesticks, CLOB `prices-history`, Data API prints around each birth and at `t_L`) | P | only after q0347 PASS and q0348 PASS |
| q0350 | `cb15_census_P` (counts only; gates GP, GPP) | P | after q0349 |
| q0351 | `cb15_screen_P` (P1, P2) | P | after the P freeze |
| q0352 | `cb15_p_live` (birth watcher, cron) | P | after the P freeze; not before 2026-11-04T00:00Z |
| q0353 | `cb15_rep_P` | P | only if P1 or P2 advanced; after `T15_P2_end` |
| q0354 | `cb15_smoke_L` (≤ 30 requests; source parse on out-of-window captures) | L | after the L rules part and smoke code exist |
| q0355 | `cb15_l_source_census` (counts only: CDX enumeration and parse success per ISO week; **no leader extracted**; gate GLS) | L | after q0354 PASS |
| q0356 | `cb15_l_frame` (Gamma frame, rule booleans, key drops; outcomes to the guarded file) | L | only after q0355 PASS and q0340 |
| q0357 | reserved: GL0, the blind methodology-change list and organisation map (repo step) | L | - |
| q0358 | `cb15_l_history` (qualifying captures parsed into guarded state rows) | L | after q0356 and GL0 |
| q0359 | `cb15_l_prices` (CLOB `prices-history` at checkpoints, Data API prints) | L | after q0358 |
| q0360 | `cb15_census_L` (counts only; gates GL, GLP) | L | after q0359 |
| q0361 | `cb15_screen_L` (L1, L2) | L | after the L freeze |
| q0362 | `cb15_l_live` (daily leaderboard poll + `/book` at checkpoints, cron) | L | after the L freeze, and only if the smoke finds a keyless live source |
| q0363 | `cb15_rep_L` | L | only if L1 or L2 advanced; after `T15_L2_end` |
| q0364-q0379 | reserved | - | - |

### 0.2 Selection and scope

**Ranking rule.** As CB14 §0.2, with this brief: (a) the round-6 "next in line" ideas the brief names (CH129, CH130,
CH125); (b) the calendar first (E cannot wait); (c) side-free and wallet-free designs. **No CB15 statistic reads the
Data API `side` field or any wallet field.**

**What the drafting session read (2026-10-19T03:40-04:16Z).** CLAUDE.md, AGENTS.md; the ledger head (E009/E010 fixed
end 2026-11-03T00:00Z); mission §4; round 6 §0 facts 9, 12, 13, §2 (CH125, CH129, CH130), §3, §4 and §5; CB14 §0-§8
in full; CB13's structure; CB12 §0, §1.1-§1.3 (CB12-X and the C1 reproduction call, the CB12 key union that includes
`matches.json` ids); CB11 §0 (CB11-P frame window); `CROSS_VENUE_STUDY.md` §1-§3 and §10; `CROSS_VENUE_LIVE.md`;
`run_cross_venue.stage_match` (the fields of `matches.json`); `EXECUTION_COSTS.md` line 39.
- Prior work: no AREPO test has an election-night object, a listing-time (birth) object on cross-venue pairs, or a
  leaderboard history. CB12-X (closed: X1 not identifiable) and CB5-K used the C1 pairs near resolution; E010 (live,
  sealed to 2026-11-03) uses the gap at 1 h and 6 h on live pairs.
- `battery2.cumulative_count()` (`battery2-count-v1`) = **1,232** on HEAD. Not stable (the host adds about 55-60 counted
  `flow_screen` lines a day); every counting CB15 job records **the value at its run, after the host union**.

**Seven premises corrected or fixed by the probes and reads (they shape this design).**
1. **The LMArena leaderboard is not in the archived HTML** (P5-P6): two Wayback captures (`/leaderboard`, 2026-01;
   `/leaderboard/text`, 2025-10) hold 0 `<tr>`, 0 `<td>`, no React server payload and no four-digit score. CH125's
   "the Wayback Machine holds it" is doubtful. L is gated on a source census that reads no leader (GLS).
2. **`/leaderboard/text` has few captures**: 75 capture-days from 2025-05 to 2026-01 at daily collapse, none after
   2026-01 (P6). Weekly coverage over the frame is unlikely even if a parseable path exists.
3. **The CLOB batch endpoint works keyless** (P9: `POST /books` returned two books with `bids`, `asks`, `timestamp`,
   `last_trade_price`). A 60-s election-night collector needs one request per ≤ 100 tokens (cap unverified; smoke).
4. **Reporting-percentage feeds are not keyless** (AP is keyed; state feeds vary and were not probed; round 6). E
   therefore anchors its windows on each state's **last official poll-closing time**, not on a reporting share.
5. **House races exist in number** (P7: active "House 2026" 457 results; 48 of the first 50 events end in
   November-December 2026; 49 neg-risk). With House races, more states carry a competitive race. Because all races of a
   state share its counting order, **the state is E's unit of inference**, not the race.
6. **`matches.json` holds `k_open` and `p_start`** (read of `run_cross_venue.stage_match`), so the birth-order census
   needs no fetch. Its `p_end` is `closed_time` where present (hindsight) and is **never** used by P.
7. **CB12's key union includes the C1 ids** (`matches.json`, CB12 §1.3), so applying the inherited key file to P would
   drop every C1 pair. P therefore drops keys by source (§1.3). And **CH129's ex-post 2024 audit is dropped**: it reads
   2024 state-race markets inside CB11-P's frame window (`[2024-07-01, 2026-09-01)`) and is hindsight-fitted.

US daylight saving time ends on **2026-11-01**, so Eastern Time is UTC−5 on election night.

### 0.3 Feasibility probes (counts only; 9 keyless GETs; nothing stored)

Run from the Mac (scripts in `/tmp/cb15probe/`, not committed), `User-Agent: arepo-research-probe/1.0 (read-only
counts; https://www.arepolabs.com)`, paced ≥ 1.5 s. **No price, outcome, title, leader name or token id was printed or
stored.** Disclosed exposure: event counts and end-month counts of active election events; Wayback capture counts; HTML
marker counts of two captures; the key names of two order books (contents not printed). No host probe ran.

| # | Request(s) | Finding |
|---|---|---|
| P1-P2 | Wayback CDX `lmarena.ai/leaderboard*`, 2023-2026, status 200, daily collapse (1) | 6,140 capture-days in 2025 and 1,359 in 2026 **across all URLs under the prefix** (per-URL counts not separated) |
| P3-P4 | Wayback CDX `huggingface.co/spaces/lmarena-ai/chatbot-arena-leaderboard*` (1) | 123 capture-days in 2024, 275 in 2025 (a Gradio app; the table is not expected in its HTML) |
| P5 | one capture of `lmarena.ai/leaderboard` (2026-01-14) (1) | 264 KB; 0 `<tr>`, 0 "rank", no `__NEXT_DATA__` / `self.__next_f`, 0 four-digit numbers |
| P6 | CDX of `lmarena.ai/leaderboard/text` 2025-2026 + one capture (2025-10) (2) | 75 capture-days (2025-05 1, 06 3, 07 2, 08 8, 09 3, 10 10, 11 20, 12 20, 2026-01 8); the capture has 0 `<tr>`, 0 `<td>`, 0 score-like numbers |
| P7 | Gamma `public-search?q=House 2026&events_status=active` (1) | `totalResults` **457**; first page 50 events, 592 markets, 48 ending 2026-11/12, 49 neg-risk |
| P8 | the same for `Senate 2026`, `Governor 2026` (2) | Senate **142** (50 events, 588 markets, 49 ending 2026-11/12); Governor **116** (50, 685, 50) |
| P9 | CLOB `POST /books` with two token ids from P8 (1) | 200; 2 books; keys `asks, asset_id, bids, hash, last_trade_price, market, min_order_size, neg_risk, tick_size, timestamp` |

### 0.4 Selection decisions

| Idea | Decision | Reason |
|---|---|---|
| **CH129** election night | **include (E), prospective only, one night** | The only date-boxed object in round 6 that cannot be studied later on the same terms; keyless books (P9); populations exist (P7-P8). Honest weaknesses, all in the title or the floors: one night is one cluster for the national swing (the balanced contrast cancels only its additive part); professionals price liquid races; the frozen sign may be lopsided (most states one way), which GEP turns into "not run (power)"; with the declared drift SD the test detects only a drift near 3× its floor. **The ex-post 2024 audit is dropped** (premise 7). **Liquid races are not dropped** (population); the tier is a binding sign check |
| **CH130** pair at birth | **include (P), census-gated** | Metadata on the host (premise 6); Kalshi minute candlesticks are keyless (cross-venue study §2). Honest weaknesses: the C1 set is worn (C1 study, CB5-K, CB12-X, E009/E010 design); gap convergence is a known C1 result and E010's live object, so P1 must beat the same pairs' later-life slope to carry the label "birth"; non-sports C1 is 167 pairs, and CH130's kill (40 Kalshi-first pairs with a ≥ 5c gap) may not be reachable. Historical units all end before 2026-10-12, so the E009/E010 window is untouched |
| **CH125** leaderboard hazard | **include (L), source-gated first; recommended for deferral if the challenger prefers** | 26 + 4 closed events (round 6 fact 9) make it thin by CH125's own words, and P5-P6 suggest the archive holds no table. The source smoke (q0354) and source census (q0355) are the first L jobs, so nothing else is built if the source fails. Counted by the CB14 convention (a source failure is "not testable (source)", p = 1); **the challenger may rule to withdraw L uncounted before q0354 runs** (§7 item 3) |

**Sports and categories.** `CB15_SPORTS_IN_PRIMARY = false` (a parameter, as CB8-CB14). P excludes C1 pairs with
Kalshi category Sports (149 of 316) from the primary and reports them. E and L contain no sports. Category stays a
parameter.

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Prior use | Role in CB15 | Evidence ceiling |
|---|---|---|---|
| `history/h15_elect_live` (**new, post-freeze**, q0345): frozen race map, receipt-timed books (top 5 levels per side, venue `timestamp`, `last_trade_price`) for the YES and NO tokens of every trade market, Gamma `liquidity` at the 2026-11-02T12:00Z pass, gap log | none | E1, E2 | prospective (L2), one night |
| `research_lab/cross_venue/` on the host (`matches.json`, `audit_flags.json`, `audit_sample100.json`, `poly_markets.json`, `series/*.npz`; sha256 pinned) | C1 study v1/r1, CB5-K, CB12-X, E009/E010 design | **pair list only**: the C1 reproduction call (`c1_pairs()`, asserting 316 pairs and 183 events, as CB5-K and CB12-X) and the fields `k_ticker, k_series, k_cat, k_open, k_close, p_market_id, p_event_id, p_start, p_token0` and texts. **No P statistic reads a series value**; `p_end` is never read | pair list |
| `history/h15_birth` (**new**, q0349): Gamma metadata (`createdAt`, `startDate`, `endDate`, ids, `feeSchedule`), Kalshi 1-minute candlesticks (bid/ask close) over `[t_birth − 6 h, t_d + 25 h]` and `[t_L − 1 h, t_L + 25 h]`, CLOB `prices-history` (fidelity 10) over the same spans, Data API prints aggregated to transactions | none | P1, P2 | L1 |
| `history/h15_birth_live` (**new, post-freeze**, q0352): new listings matched by the frozen matcher, Kalshi orderbook and CLOB `/book` reads at birth + 1, 10, 60 min and + 24 h 10 min | none | P1-rep, P2-rep | L2 |
| `history/h15_lb` (**new**, q0355-q0359): CDX listings and parse flags (census), guarded leaderboard state rows (`guarded_lb/`), Gamma frame, `prices-history` at checkpoints, prints; outcomes only in `outcomes_guarded.csv.gz` | none | L1, L2 | L1 |
| `history/h15_lb_live` (**new, post-freeze**, q0362) | none | L1-rep, L2-rep | L2 |
| `cross_venue_live/` (E009/E010), `surprise_live/` (E011), `snapshots/`, `live_trades/`, `book_sweeps/`, `trade_samples/`, `e001/`-`e007/`, `forecasts/`, `flow_screen/`, every `cb*_extract/` | live stores, E-series, J4-R, CB1-CB14 | **never opened by any CB15 path** (runner refuses; unit-tested) | - |
| `h1_*` … `h14_*`, every `creative_batch1..14/` | worn, sealed or batch-owned | **not read**, except id columns for exclusion keys through a field-restricted accessor; no `holdout/` path is ever opened | - |

**Reuse disclosure.** *E:* no AREPO set holds 2026 general-election markets in a window that intersects E's (live
captures, J4-R and CB13-T fill sets may hold some of the same markets in October; §1.3). *P:* the C1 pairs are worn;
for pairs whose Polymarket life was shorter than 14 days, the C1 series window (the last 14 days before the earlier
resolution) contains the birth, so their birth-period prices entered the C1 lead and gap analyses (not this statistic);
a binding robustness drops them. *L:* no AREPO test has sampled AI-leaderboard markets; CB11-A's frame (ends
`[2026-04-20, 2026-10-01)`) may hold some by entity and is removed by key.

### 1.2 Dates (declared; UTC unless ET is stated; ET = UTC−5 on 2026-11-03)

| Name | Value | Meaning |
|---|---|---|
| `T15_draft` | 2026-10-19T04:16Z | this draft; no CB15 quantity computed |
| `T15_E_freeze` | **2026-11-01T12:00Z, hard** | part E frozen (rules, sign table, poll-close table, party map, race map hashes); else E1, E2 "not run (calendar)", counted |
| `T15_E_pre` | 2026-11-02T12:00Z | first collector pass: tier snapshot (`liquidity`), 10-min book reads begin (pre-night placebo windows) |
| `T15_E_on` / `T15_E_off` | 2026-11-03T22:00Z / 2026-11-04T21:00Z | 60-s book reads (covers every `t_a` and `t_a + 12 h`; Hawaii and Alaska close 05:00-06:00Z) |
| `T15_E_end` | 2026-11-06T00:00Z | 10-min reads from `T15_E_off` to here (for the 24 h robustness); collector stops |
| `t_close(state)` | frozen table (GE0) | the state's last official poll-closing time in UTC (the latest across its time zones) |
| `t_a`, `t_b` | `t_close + 90 min`, `t_a + 12 h` | E's window per state |
| `T15_hist_end` | 2026-10-12T00:00Z | every P historical row (`t_d + 24 h 30 min` and `t_L + 24 h 30 min`) is before it; asserted (C1 pairs all closed before the study date) |
| `T15_P2_start` / `T15_P2_end` | `max(P freeze + 1 d, 2026-11-04T00:00Z)` / the date by which ≥ 60 non-sports Kalshi-first births have their 24-h read, never after `T15_P2_cap` = 2027-04-30 | P Stage 2; after E009/E010's end (2026-11-03T00:00Z) and their analysis runs (02:00Z, 08:00Z). The stop counts births, never results |
| L frame / history | events end `[2024-07-01, 2026-10-01)`; captures `[2023-05-01, 2026-10-01)` | L Stage 1 |
| `T15_L2_start` / `T15_L2_end` | events resolving after `max(L freeze + 1 d, 2026-10-27T00:00Z)` / ≥ 12 events resolved, never after `T15_L2_cap` = 2027-10-31 | L Stage 2 |
| E009/E010 | `[2026-10-13, 2026-11-03T00:00Z)` | not touched: no CB15 path opens `cross_venue_live/`; P's historical units end before 2026-10-12 and its Stage 2 starts 2026-11-04; E collects after 11-02 on its own frame |
| E011 | window to 2026-11-10 | E's collection overlaps in time (collection overlap only, as CB12/CB14 collectors); **no CB15 output defines an E011 subgroup** |
| J4-R | `[2026-10-16, 2026-10-21)` | no CB15 row inside it |
| CB13-T HOLDOUT | `[t_j4r_end, 2026-10-26)` | no CB15 row inside it |

### 1.3 Sealed and untouched data (named)

- **Refused roots.** `run_cb15.py` refuses every root in the last two rows of §1.1 and writes only under
  `research_lab/creative_batch15/` and the five `h15_*` roots. The C1 files are opened read-only through the pinned
  reproduction call and a field-restricted reader of `matches.json`.
- **E009/E010 and CB15-P.** P's object (the first 24 h after Polymarket's first price, on historical pairs) differs from
  E009's (Kalshi's 10-min change → Polymarket's next 20 min) and E010's (change + gap → 1 h and 6 h, live). P computes
  no statistic on any row at or after 2026-10-12, opens no live store, and starts its watcher after both have ended.
  P's binding 10-minute exclusion (`t_d` = first price + 10 min) keeps the sealed lead's horizon out of the target.
- **CB12-X and CB5-K (same pairs, other objects).** Both are near-resolution measurements on the C1 series. P reads no
  series value; its later-life comparator at `t_L` uses P's own fresh fetch. No CB15 line pools, cites or conditions
  on CB12-X or CB5-K results.
- **CB11-P, CB11-A (sealed HOLDOUTs).** No CB15 path opens any `h11_*` data. P and L drop every key of the `h11_pol`
  and `h11_attn` frames (both strata, both splits, sampled or not). The 2024 election-night audit of CH129 is dropped
  (premise 7).
- **CB14-W (personnel; live from 2026-10-26), CB14-S (mention events; Stage 2 from 2026-10-27).** CB15 adds CB14's frame
  ids (W markets, events and series; S events of P, N and Stage 2 as built by q0340's run), as CB14 §8 item 6 requires.
  E's election races are not personnel or mention markets; overlap is checked by key (robustness).
- **CB13 (T fills in the J4-R window and HOLDOUT; R barrier events).** Keys added. E reads no October price.
- **Exclusion keys (q0340).** Union of: (1) CB14 q0302's `exclusion_keys.csv.gz` (sha256 pinned; it unions CB13 q0276,
  CB12 q0241, CB11 q0221, the C1 sample, the T5 frame, every CB8-CB14 frame and seal copy known then); (2) id columns of
  CB14's frames built since (`h14_wiki` frame and live frame, `h14_speech` P, N and Stage-2 events); (3) every seal
  copy under `docs/research_lab/seals/` committed by then. Keys = market id, Gamma event id, `negRiskMarketID`, series
  id. **Each key carries its source(s)**; if the inherited file lacks attribution, q0340 rebuilds the union from its
  sources. A frame not yet built is "absent at q0340" (recorded) and re-read by the census. More than 2% of ids without
  metadata → the affected family "not testable (disjointness)", counted. **CB16 must add CB15's frame ids.**
- **Key rule per family (declared deviations, for the challenger).**
  - *P:* drops keys from every source **except** those whose only source is the C1 set (`matches.json`, CB5-K,
    CB12-X, the C1 sample as used by E009's design): the C1 set is P's population (premise 7), as CB14-S kept CB12-M's
    SCREEN ids for N. Full series rule for the other sources; the census reports drops and the no-drop counterfactual.
  - *L:* market, event, `negRiskMarketID` and **series-month** (same series, same resolution month) instead of the whole
    series, because "top model at month-end" events form one monthly series and one prior rung would drop them all
    (CB14-S's series-date precedent); the full-series counterfactual is reported.
  - *E:* **calendar disjointness, keys as binding robustness.** E reads only books in `[2026-11-02T12:00Z,
    2026-11-06T00:00Z)` and no Gamma outcome. A prior sample holding a 2026 race market read it in October or earlier,
    for a different object. Dropping by key could remove the most-watched races for reasons unrelated to E. The census
    reports the key-overlap count, and a binding E robustness drops those markets (sign check).
- **Outcome guards.** *E:* no Gamma outcome is fetched; `outcomePrices`, `umaResolutionStatus(es)` and `closedTime`
  are discarded at parse. The target is a price. *P:* the same (no outcome); prices after `t_d` (and after `t_L`) are
  opened only by the screen and rep jobs; the census and GPP read them only through the SE-only proxy (§2.7). *L:*
  Gamma outcomes go only to `h15_lb/outcomes_guarded.csv.gz` (opened by q0361 and q0363). **Leaderboard captures are
  outcome-bearing** (a month-end capture reveals `Y`): parsed rows live in `guarded_lb/` behind a **causal accessor**
  that returns, for a unit at `t`, only captures with capture time ≤ `t − 1 h`. The source census stores a parse flag
  and row count per capture, never a model, organisation or score.

### 1.4 Rules files

- `seals/cb15_rules.json` (before q0341), hashed per part:
  - **`common`**: refused roots, seeds, bootstrap and small-G settings, Holm/BY settings, disk guards, field whitelists,
    smoke criteria, the source-attribution key rule.
  - **`E`**: the frozen query list (`Senate`, `Governor`, `House`, `congressional district`, `midterm`, each with
    `2026`, `events_status=active`, paged to `hasMore = false`), a politics-tag (id 2) completeness walk of active events
    ending `[2026-11-03, 2027-01-31]`, the race regex (state name or postal code + office + optional district), the
    general-election rule (description names 3 November 2026; primaries, runoffs and other-date specials excluded),
    the trade-market rule (§CB15-E), the two-party rule, the **sign-table recipe** and its compiler instructions, the
    poll-close table schema, the tier rule, windows, book-read rules, fee policy, gates, placebo windows, the collector
    schedule. The sign table, poll-close table, party map and race map are **files hashed into part E at the freeze**.
  - **`P`**: the C1 reproduction call and file sha256s, the field list, the Kalshi-first rule, the first-price rule, the
    gap rule, `t_d`, `t_L`, the entry and exit print windows, the frozen matcher (`cross_venue.match_markets`, the r1
    `audit_conflict` rule; source sha256 pinned) for Stage 2, gates.
  - **`L`**: the query list (`best AI model`, `top AI model`, `AI model end of`, `Chatbot Arena`, `LMArena`), the
    rank-1 regex (second-best, coding, vision and other arenas reported only), rule booleans (style control on/off,
    text arena, tie-break, snapshot time), the CDX path list and parser, the capture-qualification rule, the hazard
    recipe, checkpoints, gates. The methodology-change list and organisation map (GL0) are hashed into part L.
- Jobs refuse (exit 2) on a hash mismatch. **No rule is computed from, or revised after, any E book, P price or print,
  L price, print, capture state or outcome.** After `T15_E_on`, no element of part E may change; a defect found then
  makes the affected units "unavailable", counted.
- **Field whitelists.** *Gamma:* as CB14 §1.4, plus `liquidity` for E at the `T15_E_pre` pass only. *CLOB `/books`:*
  `asset_id`, `market`, `timestamp`, top 5 levels per side (price, size), `tick_size`, `neg_risk`, `last_trade_price`;
  `hash` discarded. *Kalshi:* `ticker`, `event_ticker`, `series_ticker`, `open_time`, `close_time`, `rules_primary`
  sha256 plus `is_provisional` and `can_close_early`; candlesticks `end_period_ts`, `yes_bid.close`, `yes_ask.close`,
  `volume`; **`result` and `settlement_value` are discarded at parse**. *Wayback:* CDX `timestamp, original, mimetype,
  statuscode, digest`; bodies reduced at parse to rows (rank, model, organisation, score, view flags) written only to
  `guarded_lb/`. *Data API:* as CB14 (no hash, wallet, name or `side` written). A unit test feeds fixtures carrying every
  forbidden field and asserts that no parsed row, file or log contains them.

## 2. Common rules (deltas from CB14 §2)

### 2.1 Costs

| Test | Price and cost rule |
|---|---|
| E1, P1, L1 | none charged (forecasting tests) |
| E2 | **recorded books**: entry at the best ask of the predicted-side token (D YES for `s = +1`, D NO for `s = −1`) in the first successful read with receipt ≥ `t_a` (≤ 2 min later, else "unavailable (gap)"); exit at that token's best bid in the first read with receipt ≥ `t_b` (≤ 5 min); size min(100, displayed best-ask size); fee `r·e(1 − e) + r·x(1 − x)`, `r = max(feeSchedule.rate, 0.04)` (politics; `feeSchedule` is current, not point-in-time, so the floor is a conservative rule) |
| P2 | **recorded prints**: toward Kalshi (YES if `g_d ≥ 5c`, NO if `g_d ≤ −5c`); entry at the taker-adverse print in `[t_d + 60 s, t_d + 60 min]` (max YES-terms price when buying YES; min when buying NO, paying 1 − price); exit at the adverse print in `[t_d + 24 h, t_d + 24 h 30 min]` (min when long YES; max when long NO); none → the last print in `(t_e, t_d + 24 h 30 min)` ("stale exit", counted), none after entry → "no exit" (excluded, counted, priced at `w*` in the reach check); size min(100, entry print size); fee as E2 |
| L2 | **recorded prints**: the model side (YES if `q − p ≥ 6c`, NO if `p − q ≥ 6c`) at the taker-adverse print in `[t + 60 s, t + 60 min]`; held to resolution, paid on the Gamma resolution; entry fee `r·e(1 − e)`, `r = max(feeSchedule.rate, 0.04)` |
| P2-rep, L2-rep | recorded best ask at the read ≥ `t` (≤ 2 min); P2-rep exits at the recorded best bid at `t_d + 24 h`; L2-rep holds to resolution |
| Binding cost robustness | +1.0c per side (E2, P2, P2-rep); +1.0c on entry (L2, L2-rep) |

### 2.2 Clocks

- **CLOB books (E, Stage 2 of P and L).** Receipt time (host clock, NTP-checked by the smoke) is the clock; the venue
  `timestamp` is stored and its lag reported.
- **CLOB `prices-history` at fidelity 10 (P, L).** A point is usable from stamp + 600 s (bucket-end-safe); `p(t)` = the
  last usable point before `t` with age ≤ 2 h (P) or ≤ 6 h (L); else "no price", counted.
- **Kalshi candlesticks (P).** A 1-minute bar is usable from its `end_period_ts`; the Kalshi mid at `t` = (bid close +
  ask close)/2 of the last usable bar with both sides, age ≤ 60 min, spread ≤ 10c; else "no Kalshi quote", counted.
- **Wayback captures (L).** The 14-digit capture time is when the page was public as captured; usable from capture + 1 h.
- **Poll-closing times (E).** Official times in the frozen table; `t_a` is a scheduled clock, not a reported one.
- **Gamma `createdAt`, `startDate`, `endDate`; Kalshi `open_time`.** As fetched. `closedTime` and `p_end` are never used.

### 2.3 Uncertainty and decision rule

As CB14 §2.3: unweighted primary unless stated; one-sided p = the max over the declared ways; 2,000-draw cluster
bootstrap, **seed 1515**; the small-G rule (G ≥ 30 CR1; 15-29 CR2 with t(G − 1) and the Webb wild bootstrap, 9,999
draws; G < 15: the way leaves the max and its leave-one-cluster-out sign rule binds, as A-C1); "unknown" never counts
as met.
- **Ways.** **E1, E2:** the state is the unit; p = the **state-label permutation** (the sign labels permuted across
  eligible states with group sizes fixed; 9,999 draws, seed 15101; p = (1 + #{T* ≥ T}) / 10,000). The night is one
  cluster for everything common to all states; the balanced contrast removes its additive part only (title). **P1,
  P2:** Polymarket event; ISO week of the birth. **L1, L2:** resolution month; incumbent organisation (an incumbency
  error is shared across months; G is likely < 15, so its leave-one-organisation-out sign rule binds).
- **Testability minimums (declared deviations from 100 units / 30 clusters, each from the hypothesis's own kill).**
  E: ≥ 16 eligible states with ≥ 7 per sign on the night. P1: ≥ 60 pairs in ≥ 30 events. P2: ≥ 40 pairs with `|g_d| ≥
  5c` in ≥ 25 events (CH130's kill). L1: ≥ 20 events, ≥ 60 units, ≥ 15 resolution months (CH125's kill). L2: ≥ 30 units
  in ≥ 12 events. Below → "not testable (population)", counted with p = 1.
- **Stage 1 (6 tests).** Advance iff one-sided p < 0.01, the §2.4 floor holds, every binding placebo, robustness check
  and gate holds, **and** the test passes a batch Holm step-down at one-sided α = 0.05 over **k1 = 6** (fixed; first step
  0.0083, so Holm can bind for p in [0.0083, 0.01)). BY (q = 0.10 over `battery2.cumulative_count()` at the run) is triage.
  E's tests are prospective but enter the same batch Holm (conservative).
- **Stage 2.** One Holm at one-sided α = 0.05 over every CB15 test reaching Stage 2 (P, L only); a test that finishes
  before k2 is known is judged against α/4, strict `<`; the full Holm is applied once at the end and can only add passes.
- **Stage P** is a separate registration for any survivor (§2.9).

### 2.4 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate |
|---|---|---|
| E1 | prospective drift | `T_E1` ≥ **+5c** (balanced mean D-terms drift in the predicted direction; CH129's kill) and balanced sign share ≥ 0.60 (CH129's kill; binding) |
| E2 | economic, recorded books | balanced mean net ≥ **+1.0c per share** |
| P1 | forecasting | slope ≥ **0.30** (CH130), and birth slope − later-life slope > 0 (binding, §CB15-P) |
| P2 | economic, recorded prints | event-weighted mean net ≥ **+1.0c per share** |
| L1 | forecasting | slope ≥ **0.30** (CH125) |
| L2 | economic, recorded prints | event-weighted mean net ≥ **+1.0c per share** |
| P1-rep, P2-rep, L1-rep, L2-rep | as Stage 1, at recorded books | as Stage 1 |

### 2.5 Counting (M3 rule)

- Kinds **`cb15_test`**, **`cb15_replication`** and **`cb15_descriptive`** (EXCLUDE), mirroring CB14's
  `battery2.KIND_RULES` entries; unknown kinds raise. Descriptive lines: smokes, audits (GE0, GL0), pre-gates,
  censuses, gates, strata, tiers, the reported sign share, liquid and second-tier readings, Polymarket-first pairs,
  sports pairs, gap-closure shares, latency and gap logs.
- **Count lines (`ml_explain` `n_tests`).** `creative_batch_15:E` **2**, `creative_batch_15:P` **2**,
  `creative_batch_15:L` **2**; replication lines `creative_batch_15:<P|L>:rep` carry the family's triggered tests (≤ 2).
- **Triggers.** P1-rep iff P1 advanced; P2-rep iff P2 advanced; L1-rep iff L1 advanced; L2-rep iff L2 advanced. E has no
  Stage 2 in CB15.
- **Cumulative count:** 1,232 on HEAD at drafting (`battery2-count-v1`), not stable; recorded at each run. **CB15 adds
  6 fixed tests and up to 4 conditional ones. Budget: 6-10.**
- Tests behind a failed or unknown gate (smokes, disjointness, GE0, GEC, GEP, GE, GPB, GP, GPP, GLS, GL0, GL, GLP,
  availability, the calendar deadline, Stage-2 minimums) are "not testable", "not run" or "not run (calendar)" (p = 1)
  and are **still counted**. A job waiting on exit 75 is "pending" and writes no line.

### 2.6 Placebos and robustness (common)

As CB14 §2.6: each binding placebo names its alternative; calibration placebos are judged on p alone; 200 draws;
**advance rate ≤ 1.5%**; seeds 15101-15130. Common binding robustness for any advance: (i) the §2.1 cost robustness;
(ii) p and the floor without the top 5 clusters of each way (E: without the top 2 states of each sign, and every
leave-one-state-out keeps the sign); (iii) sign by period (P, L: each calendar half and leave-one-quarter-out); (iv)
unavailable units excluded and counted, never imputed; available share < 60% of eligible → "not testable
(availability)".

### 2.7 Pre-freeze census and pre-fetch gates (counts only)

Outcome guards first; field-restricted and causal accessors; a unit test asserts that no census path receives a Gamma
outcome (L), a price after a unit's decision time (P, L), a capture after `t − 1 h` (L), or an E book after `T15_E_on`.
Per-family gates are in §3: **E** GE0 → GEC → GEP (pre-night) and GE (on the night); **P** GPB (no network) → GP, GPP;
**L** GLS (source, no leader) → GL0 → GL, GLP. MDEs come from counts and declared or feature-only quantities, and are
never used to change a floor, window or threshold.

### 2.8 Compute, network, disk and stop rules

- **Host.** 1 OCPU, about 5.6 GiB RAM shared with the collectors (MemAvailable about 4.5 GB in CB14's probe). Queue rules
  as CB14 §2.8: one job per lane, nice 19, `MemAvailable ≥ mem_mb + 1200`, address cap 2 × `mem_mb`, the 02:45-05:30 UTC
  blackout for `mem_mb ≥ 500`; `mem_mb` ≤ 600 everywhere; streaming one page, pair or capture at a time. **Election
  night:** the coordinator holds `cpu`-lane jobs with `mem_mb ≥ 500` during `[T15_E_on, T15_E_off)`; the E collector runs
  at nice 5, `mem_mb` 200.
- **Network** (`net` lane; **one `net` job at a time at ≤ 2 rps Polymarket**; ≤ 1 rps Kalshi; ≤ 0.5 rps Wayback;
  descriptive User-Agent; shared `Limiter`, 429 / `Retry-After` back-off, stop on repeated 429):

  | Job | Work | Requests / wall | Stored (cap) |
  |---|---|---|---|
  | q0340 | exclusion keys (increment over CB14 q0302, attribution) | ≤ 600 Gamma, ≤ 6 min | ≤ 0.01 GB |
  | q0341 | E census: 5 queries × pages (≤ 120), event lookups (≤ 400), politics-tag walk (≤ 100) | ≤ 620, ≤ 10 min | ≤ 0.005 GB |
  | q0343 | E smoke | ≤ 30, < 5 min | 0.001 GB |
  | q0344 | E pre-gate: race-map refresh (≤ 60), one `/books` pass (≤ 15 batches) | ≤ 80, ≤ 3 min | ≤ 0.002 GB |
  | q0345 | E collector: `/books` batches of ≤ 100 tokens (≤ 1,000 tokens → ≤ 10 per pass) every 10 min from `T15_E_pre`, every 60 s in `[T15_E_on, T15_E_off)`; Gamma map refresh every 6 h | about 15,000 over the window; ≤ 0.17 rps peak | ≤ 0.3 GB |
  | q0348 | P smoke | ≤ 30 | 0.001 GB |
  | q0349 | P data: per Kalshi-first pair, Gamma (1), Kalshi candlesticks (2), `prices-history` (2), prints (≤ 4); ≤ 150 pairs | ≤ 1,400, ≤ 30 min | ≤ 0.03 GB |
  | q0352 | P watcher: Gamma new listings hourly, Kalshi open markets by `min_created_ts` (smoke-verified) hourly, orderbook and `/book` reads at birth + 1, 10, 60 min, + 24 h 10 min | ≤ 3,000 a day | ≤ 0.05 GB total |
  | q0354 | L smoke | ≤ 30 | 0.001 GB |
  | q0355 | L source census: CDX listings for the frozen path list (≤ 60) + qualification parse of ≤ 1 capture per ISO week (≤ 200) | ≤ 260 at 0.5 rps, ≤ 10 min | ≤ 0.005 GB |
  | q0356 | L frame: 5 queries × closed pages, event lookups | ≤ 300, ≤ 5 min | ≤ 0.005 GB |
  | q0358 | L history: qualifying captures, ≤ 2 per ISO week | ≤ 400 at 0.5 rps, ≤ 15 min | ≤ 0.05 GB |
  | q0359 | L prices: `prices-history` per traded market over `[T − 22 d, T]` (≤ 200), prints ≤ 2 pages (≤ 400) | ≤ 600, ≤ 6 min | ≤ 0.02 GB |
  | q0362 | L poller: daily leaderboard fetch (if keyless) + `/book` at checkpoints | ≤ 100 a day | ≤ 0.01 GB |

  Historical `net` total ≤ about 3,900 requests (about 1 h of `net` lane); if GPB or GLS fails, the large P and L
  fetches never run. A fetch without its `*_complete` status is "pending" and never analysed partially.
- **Disk guard.** As CB14 §2.8: `--disk-cap-gb` per job, `--data-dumps-cap-gb 40`, exit **75** if data-dumps + cap > 40
  GiB or root free − cap < 4.5 GB. CB15 output caps total **≤ 0.5 GB** (E ≤ 0.3, P ≤ 0.1, L ≤ 0.1). CB15 never deletes
  or moves host data.
- **Stop rules.** 3 CPU-hours per family. A job failing twice for the same non-transient reason stops and is recorded.
  A null is "not detected at MDE x". **No re-screen of a failed CB15 test** with altered sign tables, maps, windows,
  gap rules, hazard recipes, checkpoints, entry or exit rules or populations, on any data.

### 2.9 Funnel and Stage P

Screen (Stage 1) → gates, placebos, robustness → replication (Stage 2: recorded books on new births or month-ends) →
separate prospective confirmation (Stage P) → economic validation at recorded prices with fees, spread and depth.
- **E** is a one-night prospective case study: an advance is not confirmation and has no Stage 2 here. It yields only a
  registration draft for the next general-election night (2028-11-07) with a fresh blind sign table, recorded books and
  the same statistics; runoff and special-election nights may be registered by a later batch.
- **Stage P-P.** A fresh watcher window after `T15_P2_end`, frozen matcher and audit, recorded books with depth.
- **Stage P-L.** Month-end events after `T15_L2_end`, frozen recipe, recorded books.

---

## 3. Tests

### CB15-E: Election-night reporting-order drift, 3 November 2026 (CH129). One-night case study; the night is one cluster

**Question.** In states where the late count is known in advance to move toward one party (because of the order in
which vote modes and counties report), does the Polymarket price of that state's races drift toward that party over the
first 12 hours of the count by more than in states where the late count moves the other way?

**Mechanism.** Early partials carry the votes counted first (mail and early ballots in some states, election-day ballots
in others; large urban counties early or late). A crowd that reads early margins at face value overprices the early
leader where later votes lean the other way. Who pays: buyers of the early-leading side 1-3 hours after polls close in
races whose later reporting leans the other way. Why it might persist: it does not in liquid races, where professionals
model the count; the hypothesis is about the second tier. **The opposite is as plausible:** the crowd already prices the
shift (2024 liquid races), and E1 fails (that is the test).

**Race map (q0341 census → GE0 → q0344; frozen at `T15_E_freeze`).**
- Frame: Gamma `public-search` with the frozen query list, active events, paged to `hasMore = false`; events whose
  title matches the race regex and whose description names the 3 November 2026 general election; members binary.
  **Completeness (binding):** the politics-tag walk's matching events must be ≥ 95% inside the search frame, else E
  "not testable (frame completeness)", counted.
- **Trade market per race (frozen).** (a) a party market or party member ("Democrat", "Democratic"); else (b) the
  candidate member whose party is D in the GE0 party map. **Two-party rule:** the two highest-priced members at the
  q0344 read are one D and one R (else "not two-party", excluded and counted; independents and single-party races
  drop here). D-terms price = the D YES token's mid (best bid + best ask)/2. Markets listed after the freeze are
  excluded ("post-freeze listing", counted).
- **Tier (frozen rule).** At `T15_E_pre`, the top third of eligible trade markets by Gamma `liquidity` are "liquid";
  the rest are "second tier".

**Sign table (GE0; blind, before the freeze).** Two independent `science-reviewer` passes (separate sessions), each
given the state list and the recipe only. For each state with a mapped race: (1) the 2026 counting and reporting order
of vote modes (when mail and early ballots may be processed and counted, whether they are reported before or after
election-day ballots, late-arriving ballots, central-count urban counties), from state law and election-office guides
and NCSL's "When Absentee/Mail Ballot Processing and Counting Can Begin" table; (2) the direction of the D share's
change between early returns and the final count in the **2022 and 2024** general elections, each with a cited public
source. `s = +1` (late count toward D) or `−1` (toward R) only if (1) and both years of (2) agree; else `s = 0` (no
prediction; excluded, counted). **No 2026 poll, forecast, price or 2026 news is consulted.** States where the two passes
disagree get `s = 0`; agreement (Cohen's κ) is reported. The poll-close table (`t_close` per state) and the party map
are compiled in the same passes. All four files are committed with sources and hashed into part E.

**Units and target.** A race is eligible on the night if its state has `s ≠ 0`, its D-terms mid at `t_a` lies in
**[0.10, 0.90]** with spread ≤ 10c ("decided" and "wide" excluded, counted), and reads exist at `t_a` (≤ 2 min) and
`t_b` (≤ 5 min; spread ≤ 20c, else "wide at `t_b`", excluded and counted). `drift_r = mid_r(t_b) − mid_r(t_a)` in D
terms. **State value** `d_g` = the mean over its eligible races (each state weight 1, whatever its number of House
races).

**E1 (balanced drift).** `T_E1 = ½ · mean_{s=+1} d_g − ½ · mean_{s=−1} d_g`; one-sided > 0; floor +5c; p = the
state-label permutation (§2.3). A common move of all races (a national swing) adds the same `c` to every `d_g` and
cancels in `T_E1`; an interaction of the swing with the sign does not, which is why one night is one cluster.
- **Binding sign share.** The balanced share (mean over the two sign groups of the share of states whose `d_g` has the
  predicted sign) ≥ 0.60 (CH129's kill).
- **Binding pre-night placebo.** The same statistic on `[t_a − 36 h, t_a − 24 h]` (10-min reads) must not reach
  p < 0.01. *Alternative guarded:* states of one sign were already drifting (news, polls) before any vote was counted.
- **Binding robustness** (each keeps the sign; the first two also p < 0.05): `t_a` = `t_close` + 60 min and + 150 min;
  `t_b = t_a + 6 h`; `t_b = t_a + 24 h` (sign only); Senate and Governor races only (if ≥ 4 states per sign); second
  tier only; key-overlap markets dropped (§1.3); every leave-one-state-out; top-2 states per sign dropped.
- **Reported (uncounted).** The race-level sign share; liquid versus second tier; drift by hour since `t_close`; spread
  and depth through the count; decided and wide shares; κ of the sign passes; the unbalanced mean `mean_g s_g · d_g`.

**E2 (economic, recorded books).** Each eligible race: buy the predicted side at `t_a`, sell at `t_b` (§2.1). State
value = mean race net; balanced over the sign groups as E1; one-sided > 0; floor +1.0c; p = the permutation.
- **Binding.** +1.0c per side; "no depth" races (displayed best-ask size < 10 shares) included at `−9.3c` (the p90 round
  trip of `EXECUTION_COSTS.md`) keep the sign; exit at `t_a + 6 h` keeps the sign.
- **Reported.** Capacity (displayed depth at the touch), size-weighted net, the tier split.

**Gates.** **GEC (q0344; counts only):** ≥ 25 races with a mapped two-party trade market and `s ≠ 0`, D-terms mid in
[0.10, 0.90] at the q0344 read, in ≥ 16 states with ≥ 8 states per sign. **GEP (power, pre-night):** `MDE_E1 = (z_0.99 +
z_0.80) · ½ · σ_d · √(1/n₊ + 1/n₋)` with the **declared** `σ_d = 20c` (round 6: "gaps of 10-30c during the count"; no
night data can enter it) and the GEC state counts; E1 and E2 "not run (power)" if `MDE_E1 > 15c` (**3× the floor, a
declared deviation from CB14's 2×**: with ≤ 50 states 2× is unreachable; justified as a one-night case study whose pass
only motivates a re-registration; for the challenger). With 9 states per sign, `MDE_E1 ≈ 14.9c`; with 8, 15.8c (not
run). **GE (on the night, q0346):** ≥ 16 eligible states with ≥ 7 per sign, else "not testable (population)".

**Honest reading.** E detects a balanced drift near 15c, not 5c. A null says "not detected at MDE x on one night"; a pass
is a single-night case study. Neither is evidence beyond that night.

### CB15-P: The pair at birth (CH130)

**Question.** When Kalshi has been trading a question for at least a day before Polymarket's first price, does
Polymarket's opening level lag Kalshi's standing price, and does the gap close over Polymarket's first day by more than
the same pair's gaps close later in life?

**Mechanism.** Polymarket's first prints come from the seeding trader and the first retail, while Kalshi's price has had
days of trading. Who pays: Polymarket's first-day counterparties. Why it might persist: the matcher is work and the
first hours are thin. **Against it:** the first-hour spread (5-10c) may exceed the gap, and generic convergence (C1's
80-minute half-life) may explain any slope (hence the binding later-life contrast).

**Population (q0347, no network; frozen).** The C1 set by the pinned reproduction call (316 pairs, 183 events);
non-sports by Kalshi category (sports reported); key drops by source (§1.3). **Kalshi-first (census proxy):** `p_start
− k_open ≥ 24 h` from `matches.json`. **Kalshi-first (binding, q0349):** `t_birth − k_open ≥ 24 h`, where `t_birth` =
the usable time of the first `prices-history` point of `p_token0` in `[min(createdAt, p_start) − 1 d, p_start + 7 d]`
(none → "no birth price", counted). Pairs with Kalshi `is_provisional` or `can_close_early` differing from the
Polymarket rule booleans are excluded (counted; CH64's twins). Pairs whose scheduled Gamma `endDate` is before `t_d +
25 h` are excluded (scheduled, never `closedTime`).

**Units.** One per pair: `t_d = t_birth + 10 min` (the sealed lead's 10-minute horizon is excluded from the target);
`p_d = p(t_d)`; `k_d` = Kalshi mid at `t_d` (§2.2); `g_d = k_d − p_d` (Kalshi Yes = Polymarket Yes by the matcher).
Target `Δ = p(t_d + 24 h) − p_d`. Later-life comparator at `t_L = t_d + 7 d` (if the scheduled end is after `t_L + 25
h`): `g_L`, `Δ_L` by the same rules. Each event weight 1, split over its pairs.

**P1 (forecasting).** The event-weighted OLS slope (with intercept) of `Δ` on `g_d`; one-sided > 0; floor 0.30; p = max
over the event and birth-week ways.
- **Binding birth contrast.** On pairs with both units, `β_birth − β_later > 0` with one-sided p < 0.05 (paired
  event-cluster bootstrap). *Alternative guarded:* generic gap convergence (the C1 result, E010's live object) carries
  the slope; without the contrast the label "birth" is withdrawn and P1 cannot advance.
- **Binding opening-print control.** A joint fit of `Δ` on `g_d`, `(p_d − 0.5)` and `(p_d − p(t_birth))` keeps the `g_d`
  coefficient ≥ half its solo value with one-sided p < 0.05. *Alternative guarded:* seeded opening prices near 0.50
  revert regardless of Kalshi.
- **Binding calibration placebo.** `g_d` shuffled across pairs within the birth month (200 draws, seed 15111).
  *Alternative guarded:* a common post-listing drift aligned with the gap's sign distribution.
- **Robustness (binding; sign).** Pairs whose C1 series window covers `[t_birth, t_d + 24 h]` dropped (worn birth
  prices); Kalshi-first ≥ 72 h; `t_d = t_birth + 30 min`; Elections pairs alone and the rest alone (if ≥ 20 each);
  top-5 event and week drops; each half by birth date.
- **Reported.** The share of `|g(t_birth)|` closed by `t_d` (CH130's 10-minute kill, reported: a large share means the
  object is the sealed lead's); Polymarket-first pairs; sports pairs; slope by category.

**P2 (economic, recorded prints).** Units with `|g_d| ≥ 5c`; §2.1; event-weighted mean net; one-sided > 0; floor
+1.0c; p = max over ways.
- **Binding worst-case reach.** Units lost to "uncovered" (newest-first prints do not reach `t_d`), "no entry print"
  or "no exit" are included at `w* = −9.3c`; p < 0.01 and the floor still hold. *Alternative guarded:* reach is shorter
  for markets that later traded heavily.
- **Robustness (binding).** +1.0c per side; entry window `[t_d + 3 min, t_d + 60 min]`; exit at `t_d + 12 h` (sign);
  stale exits dropped; top-5 drops.
- **Reported.** The same rule at `t_L` (generic convergence economics; not a placebo); capacity; fill sizes.

**Gates.** **GPB (q0347, metadata only):** ≥ 60 non-sports Kalshi-first pairs (proxy) in ≥ 30 events after key drops;
else P1, P2 "not testable (population)", counted, and q0349 is never committed. **GP (q0350):** the §2.3 minimums.
**GPP (power, SE-only proxy):** P1: the slope's clustered SE with `g_d` as regressor and `Δ_L` as a stand-in target
(later life, no birth information); only SEs written (unit-tested); `MDE_P1 = 3.16 × 1.2 × SE`; "not run (power)" if
`> 0.60`. P2: the P2 rule at `t_L`, SEs only; `MDE > 2.0c` → "not run (power)".

**Planning (honest).** Non-sports C1 is 167 pairs. With a Kalshi-first share of 30-60% and a ≥ 5c gap in 25-50% of
those, P2's units are 13-50: **P2 likely fails GP**. P1 may reach 50-100 pairs in 30-60 events.

**Stage 2 (conditional analysis; q0352 collects unconditionally from `T15_P2_start`).** Hourly: Gamma listings created
in the last 2 h (non-sports), matched to open Kalshi markets by the frozen matcher (r1 conflict rule), Kalshi `open_time
≤ t_birth − 24 h`; a weekly blind title audit batch (`science-reviewer`; failing pairs dropped, counted). Reads at
`t_birth` + 1, 10, 60 min and `t_d + 24 h` (+ ≤ 10 min): Polymarket `/book`, Kalshi `orderbook`. **P1-rep** (mids
from books; ≥ 60 pairs); **P2-rep** (recorded best ask at `t_d`, best bid at `t_d + 24 h`; ≥ 40 units with `|g_d| ≥
5c`) by `T15_P2_cap`, else "not run (power)", counted. The watcher never reads `cross_venue_live/`.

### CB15-L: Leaderboard incumbency hazard for "top AI model at month-end" events (CH125)

**Question.** Does a survival model of the public leaderboard's own history (how long a leader usually stays on top)
predict whether the current leader is still on top at the month-end deadline, beyond the market's price?

**Mechanism.** The leaderboard changes in batches; displacement has a hazard shape (release, short lead, consolidation).
The crowd prices the incumbent on recency and rumours. Who pays: buyers of a rumoured challenger with days left, and
incumbent holders who sell on any release headline. **Against it:** labs' release timing is private information held by
part of the crowd, which makes the crowd *better* than any hazard (the test is one-sided for the model; the reverse is
reported).

**Source gate first (q0354 smoke, q0355 census).** Candidate paths (frozen list): Wayback captures of
`lmarena.ai/leaderboard*`, `lmarena.ai/?leaderboard`, `chat.lmsys.org/?leaderboard`,
`huggingface.co/spaces/lmarena-ai/*` and `huggingface.co/spaces/lmsys/*`, any mimetype; and any keyless dated public
copy of the table the smoke finds (a dataset or repository with commit times). A capture **qualifies** if the frozen
parser finds ≥ 10 ranked text-arena rows with model, organisation and score. **GLS:** ≥ 1 qualifying capture in ≥ 80% of
ISO weeks over `[2024-01-01, 2026-10-01)` and in every ISO week that holds a unit's checkpoint; else L1, L2 "not
testable (source)", counted, and q0356-q0361 are never committed. The census writes per capture only a qualification
flag and a row count. **Probes P5-P6 predict a GLS failure.**

**Frame (q0356).** Gamma `public-search` with the frozen query list, closed events with `endDate` in `[2024-07-01,
2026-10-01)`; rank-1 questions only (frozen regex); members company-level or model-level; rule booleans (style control,
arena, tie-break, snapshot time); key drops (§1.3, series-month rule). **GL0 (blind, repo step):** a methodology-change
list compiled from the operator's dated public posts (no market data, no leader identity used) and an organisation map
(model → organisation); both hashed into part L. Units in a methodology-change month are excluded (counted); spells
crossing a change are censored at it.

**Model (frozen recipe; walk-forward, no fitted constants).** At `t`, from captures with capture time ≤ `t − 1 h` (the
causal accessor): the leader (organisation for company-level events, model for model-level) and the history of
leadership spells, a change dated at the first capture showing the new leader. Kaplan-Meier on spell durations (days;
completed spells plus the current spell right-censored), `q = Ŝ(a + d) / Ŝ(a)`, `a` = current spell age, `d` = days to
the event's snapshot time. ≥ 8 completed spells before `t`, else "no model" (counted). CH125's release-calendar covariate
is **not used** (no causal public source; disclosed).

**Units.** Event × checkpoint `t ∈ {T − 21, 14, 7, 2 d}` (12:00Z), the leader at `t` has a member market listed before
`t`, `p` = its YES price (§2.2) in [0.03, 0.97]. `Y` = Gamma resolution (guarded). Each event weight 1, split over its
checkpoints.

**L1 (forecasting).** The event-weighted OLS slope of `(Y − p)` on `(q − p)`; one-sided > 0; floor 0.30; p = max over the
resolution-month way, with the organisation way's leave-one-out sign rule binding (§2.3).
- **Binding calibration placebo.** `q` permuted across events within checkpoint lead (200 draws, seed 15121).
  *Alternative guarded:* a period effect (incumbents underpriced in one era) shared by `q` and `Y − p`.
- **Binding joint fit.** Adding `(p − p_{t−7 d})` and the raw spell age keeps the `q` coefficient ≥ half with one-sided
  p < 0.05. *Alternative guarded:* momentum or a plain "older leaders stay" rule.
- **Robustness (binding; sign).** Company-level events only; checkpoints `T − 7` and `T − 2` only; spells ≥ 12; top-5
  month drops; each half.

**L2 (economic, recorded prints).** Units with `|q − p| ≥ 6c`; §2.1; event-weighted mean net; floor +1.0c; worst-case
reach at `w* = −9.3c` binding; +1.0c entry robustness.

**Gates.** **GL (q0360):** the §2.3 minimums. **GLP:** one latent per event calibrated to `p` with a month factor
(loadings 0.3 / 0.7; 500 draws, seed 15122); `MDE_L1 = 3.16 × 1.2 × max(SD(β̂*), mean SE)`; "not run (power)" if
`> 0.60`; GLP2 for L2 at 2.0c. **Planning:** 26-30 events and about 100 units give `MDE_L1` of about 0.6-0.9: **L1 likely
fails GLP even if GLS passes.**

**Stage 2 (conditional).** Only if the smoke finds a keyless live source: daily poll of the leaderboard data,
`/book` reads at the four checkpoints of each month-end event resolving after `T15_L2_start`; L1-rep and L2-rep need ≥ 12
events by `T15_L2_cap`, else "not run (power)", counted.

### CB15-SM: smokes and audits

- **q0343 E smoke** (≤ 30 requests): part hashes; refusals (live stores, `h11_*` holdouts, forbidden fields `side`,
  `proxyWallet`, `outcomePrices`, `closedTime`, any E read before `T15_E_pre` in collector mode); Gamma paging to
  `hasMore = false` on one query; `POST /books` with 100 out-of-frame tokens (non-election politics markets) returns
  100 books; receipt-time clock offset ≤ 1 s against an NTP source; gap logging on a forced failure; disk guard.
- **q0348 P smoke** (≤ 30): the C1 reproduction call asserts 316 / 183 and the pinned sha256s; Kalshi minute
  candlesticks on one out-of-frame settled market (historical endpoint) and one open market; `prices-history` fidelity
  10 at the birth of one out-of-frame market; Data API reach on one; Kalshi `/markets` with `min_created_ts`; `result`
  discarded.
- **q0354 L smoke** (≤ 30): CDX on the path list; the parser on ≥ 5 captures **dated after 2026-10-01** (outside every L
  window) and on one candidate dated copy; a keyless live source for Stage 2 (yes / no).
- Any failure → the dependent family "not testable (source)", counted. **GE0, GL0** and the P Stage-2 title audits are
  repo steps by `science-reviewer` agents with no price, book or outcome visible; their files are committed before the
  dependent gate.

## 4. Jobs (draft specs; JSON in this document only)

Fields follow `queue/README.md`; `argv[0]` under `backend/scripts/`, `cwd` `backend`; **none is written to `queue/`**
before code, tests and a `science-reviewer` freeze check exist. All `family` = `creative_batch_15`. Priorities: E
pre-freeze `net` jobs 30 (declared exception); P and L `net` 5-9; `cpu` 9.

| Id | Lane | Priority | Size / time | Depends on | Commit when |
|---|---|---|---|---|---|
| q0340 | net | 9 | ≤ 600 req, ≤ 6 min, mem 500 | CB14 q0302 | with CB14 q0302 complete |
| q0341 | net | 30 | ≤ 620 req, ≤ 10 min, mem 300 | - | `common` + `E` parts committed (target 2026-10-21) |
| q0343 | net | 30 | ≤ 30 req, < 5 min, mem 300 | - | collector + smoke code reviewed (target 10-26) |
| q0344 | net | 30 | ≤ 80 req, ≤ 3 min, mem 300 | q0341, q0343, GE0 file | GE0 committed (target 10-29) |
| q0345 | cron | - | ≤ 0.17 rps, mem 200 | E freeze | installed by 2026-11-02T00:00Z |
| q0346 | cpu | 9 | ≤ 20 min, mem 400 | q0345 end | after 2026-11-06T00:00Z |
| q0347 | cpu | 9 | no network, ≤ 5 min, mem 300 | q0340 | with q0340 |
| q0348 | net | 9 | ≤ 30 req, < 5 min, mem 300 | - | P rules part and smoke code reviewed |
| q0349 | net | 8 | ≤ 1,400 req, ≤ 30 min, mem 400 | q0347 PASS, q0348 PASS | only after both |
| q0350 | cpu | 9 | ≤ 15 min, mem 400 | q0349 | with q0349 |
| q0351 | cpu | 9 | ≤ 30 min, mem 400 | q0350, P freeze | after the P freeze |
| q0352 | cron | - | ≤ 3,000 req a day, mem 150 | P freeze | not before 2026-11-04T00:00Z |
| q0353 | cpu | 9 | ≤ 20 min, mem 400 | q0351, `T15_P2_end` | only if P1 or P2 advanced |
| q0354 | net | 7 | ≤ 30 req, < 5 min, mem 300 | - | L rules part and smoke code reviewed |
| q0355 | net | 6 | ≤ 260 req at 0.5 rps, ≤ 10 min, mem 400 | q0354 PASS | with q0354 PASS |
| q0356 | net | 6 | ≤ 300 req, ≤ 5 min, mem 300 | q0355 PASS, q0340 | only after GLS PASS |
| q0358 | net | 5 | ≤ 400 req at 0.5 rps, ≤ 15 min, mem 400 | q0356, GL0 file | after GL0 |
| q0359 | net | 5 | ≤ 600 req, ≤ 6 min, mem 400 | q0358 | with q0358 |
| q0360 | cpu | 9 | ≤ 15 min, mem 400 | q0359 | with q0359 |
| q0361 | cpu | 9 | ≤ 20 min, mem 400 | q0360, L freeze | after the L freeze |
| q0362 | cron | - | ≤ 100 req a day, mem 150 | L freeze, smoke live-source yes | after the L freeze |
| q0363 | cpu | 9 | ≤ 20 min, mem 400 | q0361, `T15_L2_end` | only if L1 or L2 advanced |

```json
{"id": "q0340_cb15_exclusion_keys", "title": "CB15 exclusion keys with per-key source attribution: CB14 q0302 key file (sha256 pinned) + id columns of CB14 frames built since (h14_wiki frame and live frame, h14_speech P/N/Stage-2 events) + seal copies; Gamma lookups for missing keys; rebuild from sources if attribution is absent", "family": "creative_batch_15", "priority": 9, "expected_value": "disjointness for P and L; E robustness keys", "data": ["creative_batch14/exclusion_keys.csv.gz", "history/h14_*/ (id columns only)", "docs/research_lab/seals/*", "public Gamma (ids)"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0302_cb14_exclusion_keys"], "argv": ["scripts/run_cb15.py", "exclusion-keys", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 2400, "max_retries": 2, "outputs": ["research_lab/creative_batch15/{exclusion_keys.csv.gz,manifest.json}"], "next_action": "q0347, q0356", "notes": "DRAFT. Never opens any holdout/ path. A dependency recorded as stopped is absent (recorded). >2% missing metadata -> unverified (family not testable, counted)."}
{"id": "q0341_cb15_e_census", "title": "CB15-E census, counts only: active 2026 general-election races (Senate, Governor, House) by frozen query list paged to hasMore=false; race regex, general-election rule, member structure, party/candidate market type; politics-tag completeness walk; no price, no outcome", "family": "creative_batch_15", "priority": 30, "expected_value": "E race and state counts for GE0 and GEC", "data": ["public Gamma"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": [], "argv": ["scripts/run_cb15.py", "e-census", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--rps", "2", "--disk-cap-gb", "0.005", "--data-dumps-cap-gb", "40"], "timeout_s": 1200, "max_retries": 2, "outputs": ["history/h15_elect_live/frame_census.csv.gz", "research_lab/creative_batch15/census_E.json", "trials.jsonl (cb15_descriptive)"], "next_action": "GE0 (two blind science-reviewer passes): sign table, poll-close table, party map", "notes": "DRAFT. Calendar exception: priority 30, <= 620 requests. outcomePrices/umaResolutionStatus/closedTime discarded at parse."}
{"id": "q0343_cb15_smoke_E", "title": "CB15-E smoke: part hashes; refusals (live stores, holdouts, forbidden fields, collector reads before T15_E_pre); Gamma paging; POST /books with 100 out-of-frame tokens; receipt clock vs NTP <= 1 s; forced-failure gap log; disk guard", "family": "creative_batch_15", "priority": 30, "expected_value": "go/no-go for the election-night collector", "data": ["public Gamma", "public CLOB /books"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "net", "network": "gamma-api, clob"}, "depends_on": [], "argv": ["scripts/run_cb15.py", "smoke", "--part", "E", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--rps", "1"], "timeout_s": 900, "max_retries": 1, "outputs": ["research_lab/creative_batch15/smoke_E.json", "trials.jsonl (cb15_descriptive)"], "next_action": "PASS: q0344; FAIL: E not testable (source), counted", "notes": "DRAFT. <= 30 requests."}
{"id": "q0344_cb15_e_pregate", "title": "CB15-E pre-gate: race-map refresh, two-party rule, one /books pass (D-terms mid band counts only), key-overlap count; gates GEC (>= 25 races, >= 16 states, >= 8 states per sign) and GEP (declared sigma 20c, MDE <= 15c); writes the race map for the freeze", "family": "creative_batch_15", "priority": 30, "expected_value": "E go/no-go before the freeze", "data": ["public Gamma", "public CLOB /books", "creative_batch15/{sign_table,poll_close,party_map}.json", "creative_batch15/exclusion_keys.csv.gz (if present)"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "net", "network": "gamma-api, clob"}, "depends_on": ["q0341_cb15_e_census", "q0343_cb15_smoke_E"], "argv": ["scripts/run_cb15.py", "pregate", "--family", "E", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--rps", "1"], "timeout_s": 900, "max_retries": 1, "outputs": ["history/h15_elect_live/race_map.csv", "research_lab/creative_batch15/pregate_E.json", "trials.jsonl (cb15_descriptive or counted not-run lines)"], "next_action": "PASS: E freeze (part E, race-map sha256) by 2026-11-01T12:00Z", "notes": "DRAFT. Band labels only; no mid stored."}
{"id": "q0345_cb15_e_live", "title": "CB15-E collector (cron every minute, flock, outside lanes): POST /books batches <= 100 tokens for YES and NO tokens of every frozen trade market; every 10 min from 2026-11-02T12:00Z, every 60 s in [2026-11-03T22:00Z, 2026-11-04T21:00Z), every 10 min to 2026-11-06T00:00Z; tier snapshot (liquidity) at the first pass; Gamma map refresh every 6 h; receipt times; gaps logged as unavailable", "family": "creative_batch_15", "priority": 0, "expected_value": "the one night of E data at recorded books", "data": ["public CLOB /books", "public Gamma"], "resources": {"mem_mb": 200, "cpu": 1, "lane": "cron", "network": "clob, gamma-api"}, "depends_on": [], "argv": ["scripts/run_cb15.py", "e-live", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--not-before", "2026-11-02T12:00:00Z", "--until", "2026-11-06T00:00:00Z", "--disk-cap-gb", "0.3", "--data-dumps-cap-gb", "40"], "timeout_s": 55, "max_retries": 0, "outputs": ["history/h15_elect_live/{books,tier,gaps,manifest}/"], "next_action": "q0346 after 2026-11-06T00:00Z", "notes": "DRAFT. Installed by the coordinator after the E freeze, by 2026-11-02T00:00Z (crontab line, as CB14 q0310). nice 5. Reads no AREPO store. Refuses if part E is not frozen."}
{"id": "q0346_cb15_screen_E", "title": "CB15-E: E1 (balanced D-terms drift t_a -> t_a+12h by state sign; state-label permutation 9,999 draws seed 15101; sign share >= 0.60; pre-night placebo; t_a/t_b, Senate+Governor, second-tier, key-overlap, leave-one-state-out robustness) and E2 (recorded best ask at t_a, best bid at t_b, fee, +1c, no-depth worst case); gate GE", "family": "creative_batch_15", "priority": 9, "expected_value": "E case-study verdicts (one night)", "data": ["history/h15_elect_live/"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0345_cb15_e_live"], "argv": ["scripts/run_cb15.py", "screen", "--family", "E"], "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch15/results_E.json", "trials.jsonl (cb15_test + creative_batch_15:E n_tests=2)"], "next_action": "ledger; a pass yields a 2028 registration draft only", "notes": "DRAFT. Refuses before 2026-11-06T00:00Z and without the part-E freeze hash; writes the counted not-run (calendar) lines if part E was never frozen."}
{"id": "q0347_cb15_p_birth_census", "title": "CB15-P birth-order census, counts only, no network: C1 reproduction call (316/183), matches.json fields k_open, p_start, k_cat, ids; non-sports; key drops by source; Kalshi-first proxy (p_start - k_open >= 24 h) by lead bin and category; gate GPB (>= 60 pairs, >= 30 events)", "family": "creative_batch_15", "priority": 9, "expected_value": "decides whether CH130 has a population", "data": ["research_lab/cross_venue/{matches.json,audit_flags.json,audit_sample100.json} (sha256 pinned; fields listed)", "research_lab/cross_venue/series/ (pair list reproduction only)", "creative_batch15/exclusion_keys.csv.gz"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0340_cb15_exclusion_keys"], "argv": ["scripts/run_cb15.py", "p-birth-census"], "timeout_s": 600, "max_retries": 1, "outputs": ["research_lab/creative_batch15/census_P_birth.json", "trials.jsonl (cb15_descriptive or counted not-testable lines)"], "next_action": "PASS: commit q0349 after q0348", "notes": "DRAFT. No series value used in any statistic; p_end never read; refuses any cross_venue_live path."}
{"id": "q0348_cb15_smoke_P", "title": "CB15-P smoke: C1 reproduction asserts and sha256s; Kalshi 1-minute candlesticks (historical and live endpoints) on out-of-frame markets; prices-history fidelity 10 at an out-of-frame birth; Data API reach; Kalshi /markets min_created_ts; result field discarded", "family": "creative_batch_15", "priority": 9, "expected_value": "go/no-go for P sources", "data": ["public Kalshi markets and candlesticks", "public CLOB prices-history", "public Data API"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "net", "network": "kalshi, clob, data-api"}, "depends_on": [], "argv": ["scripts/run_cb15.py", "smoke", "--part", "P", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--rps", "1"], "timeout_s": 900, "max_retries": 1, "outputs": ["research_lab/creative_batch15/smoke_P.json", "trials.jsonl (cb15_descriptive)"], "next_action": "PASS: q0349 (with q0347 PASS)", "notes": "DRAFT. <= 30 requests; Kalshi <= 1 rps."}
{"id": "q0349_cb15_p_data", "title": "CB15-P data per Kalshi-first proxy pair: Gamma metadata (createdAt, startDate, endDate, feeSchedule, rule booleans), Kalshi 1-minute candlesticks over [t_birth-6h, t_d+25h] and [t_L-1h, t_L+25h], CLOB prices-history fidelity 10 over the same spans, Data API prints (<= 2 pages each) aggregated to transactions; rows >= 2026-10-12 refused", "family": "creative_batch_15", "priority": 8, "expected_value": "P gaps, targets and prints", "data": ["public Gamma, Kalshi, CLOB, Data API", "research_lab/creative_batch15/census_P_birth.json"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api, kalshi, clob, data-api"}, "depends_on": ["q0347_cb15_p_birth_census", "q0348_cb15_smoke_P"], "argv": ["scripts/run_cb15.py", "p-data", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--rps", "2", "--kalshi-rps", "1", "--disk-cap-gb", "0.03", "--data-dumps-cap-gb", "40", "--budget-min", "40"], "timeout_s": 3600, "max_retries": 2, "outputs": ["history/h15_birth/{meta.csv.gz,kalshi.csv.gz,prices.csv.gz,tx.csv.gz,manifest.json}"], "next_action": "q0350", "notes": "DRAFT. No outcome, side, wallet or hash stored. Resumable; incomplete = pending.", "repeat": {"max_runs": 3, "until_log_regex": "\"status\": \"p_data_complete\""}}
{"id": "q0350_cb15_census_P", "title": "CB15-P census, counts only: binding Kalshi-first, rule-boolean drops, units by label (no birth price, no Kalshi quote, no target price, ends early), g_d distribution (features at t_d), |g_d| >= 5c count, reach; gates GP and GPP (SE-only proxy at t_L); MDEs", "family": "creative_batch_15", "priority": 9, "expected_value": "P gates and MDEs before the freeze", "data": ["history/h15_birth/ (prices after t_d only through the SE-only proxy)"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0349_cb15_p_data"], "argv": ["scripts/run_cb15.py", "census", "--family", "P"], "timeout_s": 900, "max_retries": 1, "outputs": ["research_lab/creative_batch15/census_P.json", "trials.jsonl (cb15_descriptive)"], "next_action": "science-reviewer freeze check (part P)", "notes": "DRAFT. No slope, Delta or net written."}
{"id": "q0351_cb15_screen_P", "title": "CB15-P: P1 (event-weighted slope of 24h move on g_d; birth-minus-later contrast; opening-print joint fit; within-month shuffle calibration; worn-window, 72h, 30-min, category, top-5, half robustness) and P2 (toward-Kalshi taker at recorded prints, |g_d| >= 5c; worst-case reach -9.3c; cost, entry, exit, stale robustness)", "family": "creative_batch_15", "priority": 9, "expected_value": "P verdicts", "data": ["history/h15_birth/"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0350_cb15_census_P"], "argv": ["scripts/run_cb15.py", "screen", "--family", "P"], "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch15/results_P.json", "trials.jsonl (cb15_test + creative_batch_15:P n_tests=2)"], "next_action": "advanced: q0353 after T15_P2_end", "notes": "DRAFT. Refuses before the P freeze hash and unless GPB, GP, GPP passed (else counted lines)."}
{"id": "q0352_cb15_p_live", "title": "CB15-P birth watcher (cron hourly, outside lanes): Gamma listings created in the last 2 h (non-sports), Kalshi open markets by min_created_ts, frozen matcher + r1 conflict rule, Kalshi open_time <= t_birth - 24 h; Polymarket /book and Kalshi orderbook at birth + 1, 10, 60 min and t_d + 24 h; weekly blind title-audit batch", "family": "creative_batch_15", "priority": 0, "expected_value": "P Stage 2 data at recorded books", "data": ["public Gamma, CLOB /book", "public Kalshi markets and orderbook"], "resources": {"mem_mb": 150, "cpu": 1, "lane": "cron", "network": "gamma-api, clob, kalshi"}, "depends_on": [], "argv": ["scripts/run_cb15.py", "p-live", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--not-before", "2026-11-04T00:00:00Z", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "40"], "timeout_s": 3000, "max_retries": 0, "outputs": ["history/h15_birth_live/{listings,pairs,books,audit_batches}/"], "next_action": "runs to T15_P2_end or the cap; q0353 if triggered", "notes": "DRAFT. Never reads cross_venue_live/. Stops at T15_P2_cap = 2027-04-30; the stop counts births, never results."}
{"id": "q0353_cb15_rep_P", "title": "CB15-P Stage 2: P1-rep (book mids; >= 60 pairs) and P2-rep (recorded best ask at t_d, best bid at t_d + 24 h; >= 40 units with |g_d| >= 5c); +1c robustness", "family": "creative_batch_15", "priority": 9, "expected_value": "L2 verdicts", "data": ["history/h15_birth_live/"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0351_cb15_screen_P", "q0352_cb15_p_live"], "argv": ["scripts/run_cb15.py", "rep", "--family", "P"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch15/results_P_rep.json", "trials.jsonl (cb15_replication + creative_batch_15:P:rep)"], "next_action": "pass: Stage P-P registration draft", "notes": "DRAFT. Only triggered tests; alpha/4 if early."}
{"id": "q0354_cb15_smoke_L", "title": "CB15-L source smoke: CDX on the frozen path list; parser on >= 5 captures dated after 2026-10-01 and one candidate dated copy; keyless live source for Stage 2 (yes/no); refusals and forbidden fields", "family": "creative_batch_15", "priority": 7, "expected_value": "go/no-go for the leaderboard source", "data": ["web.archive.org CDX and captures", "candidate public copies"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "net", "network": "web.archive.org"}, "depends_on": [], "argv": ["scripts/run_cb15.py", "smoke", "--part", "L", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--rps", "0.5"], "timeout_s": 900, "max_retries": 1, "outputs": ["research_lab/creative_batch15/smoke_L.json", "trials.jsonl (cb15_descriptive)"], "next_action": "PASS: q0355; FAIL: L not testable (source), counted", "notes": "DRAFT. Only out-of-window captures parsed."}
{"id": "q0355_cb15_l_source_census", "title": "CB15-L source census, counts only: CDX listings of the frozen paths over [2023-05-01, 2026-10-01); qualification parse of <= 1 capture per ISO week (flag and row count only; no model, organisation or score kept); gate GLS (>= 80% of weeks)", "family": "creative_batch_15", "priority": 6, "expected_value": "decides whether CH125 has a source", "data": ["web.archive.org CDX and captures"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "web.archive.org"}, "depends_on": ["q0354_cb15_smoke_L"], "argv": ["scripts/run_cb15.py", "l-source-census", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--rps", "0.5", "--disk-cap-gb", "0.005", "--data-dumps-cap-gb", "40"], "timeout_s": 1800, "max_retries": 2, "outputs": ["history/h15_lb/cdx.csv.gz", "research_lab/creative_batch15/census_L_source.json", "trials.jsonl (cb15_descriptive or counted not-testable lines)"], "next_action": "PASS: q0356; FAIL: L1, L2 not testable (source), counted", "notes": "DRAFT. Leader identity never extracted."}
{"id": "q0356_cb15_l_frame", "title": "CB15-L frame: Gamma public-search frozen query list, closed, endDate [2024-07-01, 2026-10-01); rank-1 regex; company/model level; rule booleans; key drops (series-month rule); outcomes to the guarded file", "family": "creative_batch_15", "priority": 6, "expected_value": "L population", "data": ["public Gamma", "creative_batch15/exclusion_keys.csv.gz"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0355_cb15_l_source_census", "q0340_cb15_exclusion_keys"], "argv": ["scripts/run_cb15.py", "l-frame", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--rps", "2", "--disk-cap-gb", "0.005", "--data-dumps-cap-gb", "40"], "timeout_s": 1200, "max_retries": 2, "outputs": ["history/h15_lb/{frame.csv.gz,outcomes_guarded.csv.gz,manifest.json}"], "next_action": "GL0 (blind methodology list and organisation map); q0358", "notes": "DRAFT. No price read."}
{"id": "q0358_cb15_l_history", "title": "CB15-L history: qualifying captures (<= 2 per ISO week) parsed to rows (rank, model, organisation, score, view flags) into guarded_lb/ behind the causal accessor (capture time <= t - 1 h)", "family": "creative_batch_15", "priority": 5, "expected_value": "hazard inputs", "data": ["web.archive.org captures", "history/h15_lb/cdx.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "web.archive.org"}, "depends_on": ["q0356_cb15_l_frame"], "argv": ["scripts/run_cb15.py", "l-history", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--rps", "0.5", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "40"], "timeout_s": 2400, "max_retries": 2, "outputs": ["history/h15_lb/guarded_lb/", "history/h15_lb/manifest_history.json"], "next_action": "q0359", "notes": "DRAFT. Refuses before the GL0 files are committed."}
{"id": "q0359_cb15_l_prices", "title": "CB15-L prices: CLOB prices-history fidelity 10 over [T - 22 d, T] per member market that is the leader at any checkpoint (causal accessor), Data API prints <= 2 pages, aggregated to transactions", "family": "creative_batch_15", "priority": 5, "expected_value": "L p, entry prints", "data": ["public CLOB, Data API", "history/h15_lb/frame.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "clob, data-api"}, "depends_on": ["q0358_cb15_l_history"], "argv": ["scripts/run_cb15.py", "l-prices", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--rps", "2", "--disk-cap-gb", "0.02", "--data-dumps-cap-gb", "40"], "timeout_s": 1200, "max_retries": 2, "outputs": ["history/h15_lb/{prices.csv.gz,tx.csv.gz,manifest_prices.json}"], "next_action": "q0360", "notes": "DRAFT."}
{"id": "q0360_cb15_census_L", "title": "CB15-L census, counts only: events by level and month; methodology-month drops; spells before each t (accessor); units by label; q - p distribution (features at t); gates GL, GLP (event latent with month factor, seed 15122), GLP2; MDEs", "family": "creative_batch_15", "priority": 9, "expected_value": "L gates and MDEs before the freeze", "data": ["history/h15_lb/ (no outcome file; guarded_lb via the accessor)"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0359_cb15_l_prices"], "argv": ["scripts/run_cb15.py", "census", "--family", "L"], "timeout_s": 900, "max_retries": 1, "outputs": ["research_lab/creative_batch15/census_L.json", "trials.jsonl (cb15_descriptive)"], "next_action": "science-reviewer freeze check (part L)", "notes": "DRAFT. No Y, slope or net computed."}
{"id": "q0361_cb15_screen_L", "title": "CB15-L: L1 (event-weighted slope of Y - p on q - p; month way, organisation leave-one-out; within-lead permutation; joint fit with momentum and spell age; company-only, late-checkpoint, spells >= 12, top-5, half robustness) and L2 (model side at recorded prints, |q - p| >= 6c, held to resolution; worst-case reach; +1c)", "family": "creative_batch_15", "priority": 9, "expected_value": "L verdicts", "data": ["history/h15_lb/ (outcomes_guarded opened here)"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0360_cb15_census_L"], "argv": ["scripts/run_cb15.py", "screen", "--family", "L"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch15/results_L.json", "trials.jsonl (cb15_test + creative_batch_15:L n_tests=2)"], "next_action": "advanced: q0363 after T15_L2_end", "notes": "DRAFT. Refuses before the L freeze hash and unless GLS, GL0, GL, GLP passed (else counted lines)."}
{"id": "q0362_cb15_l_live", "title": "CB15-L poller (cron daily, outside lanes): keyless leaderboard data (if the smoke found one), /book at T - 21, 14, 7, 2 d for members of month-end events resolving after T15_L2_start", "family": "creative_batch_15", "priority": 0, "expected_value": "L Stage 2 data", "data": ["leaderboard live source (smoke-verified)", "public CLOB /book", "public Gamma"], "resources": {"mem_mb": 150, "cpu": 1, "lane": "cron", "network": "clob, gamma-api, leaderboard"}, "depends_on": [], "argv": ["scripts/run_cb15.py", "l-live", "--rules", "../docs/research_lab/seals/cb15_rules.json", "--not-before", "2026-10-27T00:00:00Z", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 600, "max_retries": 0, "outputs": ["history/h15_lb_live/"], "next_action": "q0363 if triggered", "notes": "DRAFT. Installed only after the L freeze and a positive live-source smoke. Stops at T15_L2_cap = 2027-10-31."}
{"id": "q0363_cb15_rep_L", "title": "CB15-L Stage 2: L1-rep and L2-rep at recorded books (>= 12 events by the cap)", "family": "creative_batch_15", "priority": 9, "expected_value": "L2 verdicts", "data": ["history/h15_lb_live/"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0361_cb15_screen_L", "q0362_cb15_l_live"], "argv": ["scripts/run_cb15.py", "rep", "--family", "L"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch15/results_L_rep.json", "trials.jsonl (cb15_replication + creative_batch_15:L:rep)"], "next_action": "pass: Stage P-L registration draft", "notes": "DRAFT. Only triggered tests."}
```

## 5. Code needed (not written by this document)

- `backend/astrolabe/research_lab/cb15_common.py`: reuse `cb14_common` / `cb13_common` for refused roots, disk guards
  (cap 40, exit 75), manifests and `*_complete` status, the cluster bootstrap with the small-G rule, Holm/BY helpers,
  per-part rules hashing, whitelist readers; new: the source-attributed key union and per-family key rules, the
  state-label permutation.
- `cb15_e.py` (**first; calendar**): the census pager and race regex; the trade-market and two-party rules; the GE0
  file schemas and loaders (sign table, poll-close table, party map; hash checks); the collector (`POST /books`
  batching, schedule by window, receipt clock, gap log, flock, map refresh, tier snapshot); unit construction (`t_a`,
  `t_b`, reads within 2 / 5 min, band and spread labels); E1 (state values, balanced contrast, permutation, sign share,
  pre-night placebo, robustness), E2; GEC, GEP, GE.
- `cb15_p.py`: the C1 reproduction call (import `cb5_declaration.c1_pairs` or equivalent, sha256-pinned), the
  `matches.json` field reader, the birth-order census; Kalshi candlestick and `prices-history` clients with the usable
  rules; `t_birth`, `t_d`, `t_L`, `g_d`, `Δ`; P1 (slope, birth contrast, joint fit, shuffle), P2 (prints, fees, reach);
  GPB, GP, GPP (SE-only); the Stage-2 watcher (matcher import, `min_created_ts`, book schedule, audit batches).
- `cb15_l.py`: CDX client and capture parser (qualification flag mode for the census; row mode for history), the causal
  accessor, the spell builder and KM conditional survival, units; L1 (slope, permutation, joint fit), L2; GLS, GL,
  GLP; the Stage-2 poller (only if a live source exists).
- `backend/scripts/run_cb15.py` with the §4 subcommands; refuses analysis before the family's freeze hash.
- Tests (`test_cb15_e.py`, `test_cb15_p.py`, `test_cb15_l.py`, `test_run_cb15.py`): forbidden-field fixtures (`side`,
  `proxyWallet`, `outcomePrices`, `closedTime`, Kalshi `result`), refused roots (`cross_venue_live`, `surprise_live`,
  `h11_*/holdout`); E: the two-party rule, `s = 0` exclusion, the band and spread edges (0.10 accepted, 0.0999 not),
  reads at 2 min accepted and 2 min 1 s not, state weighting (a state with 10 House races weighs 1), the balanced
  contrast cancelling an added constant exactly, the permutation keeping group sizes, GEP at 9 versus 8 states per
  sign, refusal before `T15_E_pre` and after `T15_E_end`, the not-run (calendar) path; P: key drops by source (a
  C1-only key kept, a C1 + CB11-P key dropped), Kalshi-first at 24 h exactly, `p_end` never read, rows at 2026-10-12
  refused, the usable-stamp rule, a Kalshi bar with one side missing, the birth contrast on a synthetic generic-convergence
  set failing, entry max and exit min prints, `w*`; L: the accessor never returning a capture after `t − 1 h`, KM with
  censoring at a methodology change, `q` at known spell tables, < 8 spells → "no model", the census writing no leader
  field; `battery2` kinds and k1 = 6 fixed; α/4 early rule.

## 6. Test budget and compute

| Job | Tests counted | Kind(s) | Decision |
|---|---|---|---|
| Stage 1: E1, E2, P1, P2, L1, L2 | **6** | `cb15_test` + count lines `:E` (2), `:P` (2), `:L` (2) | p < 0.01, floor, binding placebos and robustness, batch Holm (one-sided α 0.05, k1 = 6 fixed); counted with p = 1 if a gate, audit, smoke or the E calendar fails |
| Stage 2: P1-rep, P2-rep, L1-rep, L2-rep (each only if triggered) | ≤ 4 | `cb15_replication` + `:<P|L>:rep` | one Holm over CB15 Stage 2 (early finishers at α/4) |
| Smokes, audits, pre-gates, censuses, strata, sign share, tiers | 0 | `cb15_descriptive` | - |
| **Total** | **6 fixed + ≤ 4 conditional = 6-10** | | value at the run after the host union (1,232 on HEAD at drafting; not stable) |

**Host compute.** Under 2 CPU-hours at nice 19 in total (E: about 1,000 tokens × 1,400 reads reduced per state; P: ≤ 150
pairs; L: ≤ 200 captures). Peak RAM 0.4 GB (collector 0.2 GB). **Network.** ≤ about 3,900 historical requests (≈ 1 h of
`net` lane); E collector about 15,000 requests over 3.5 days at ≤ 0.17 rps; P watcher ≤ 3,000 a day; L poller ≤ 100 a
day. **Disk.** ≤ 0.5 GB.

**CH129 calendar (what must exist by when; all UTC).**

| By | Deliverable | Owner |
|---|---|---|
| 2026-10-20 | challenger round 1 on CB15, part E first | `science-reviewer` |
| 2026-10-21 12:00 | `seals/cb15_rules.json` parts `common` + `E` committed; q0341 code and tests; q0341 queued at priority 30 | implementer, coordinator |
| 2026-10-23 | GE0: sign table, poll-close table, party map (two blind passes, reconciled, sources cited) committed | `science-reviewer` × 2 |
| 2026-10-26 | collector and E analysis code with tests; q0343 smoke PASS | implementer |
| 2026-10-29 | code-against-design freeze check (part E); q0344 PASS (GEC, GEP) | `science-reviewer`, queue |
| **2026-11-01 12:00** | **part E frozen** (`model_specs/cb15_v1.json` part E, pinning rules, sign table, poll-close, party map and race map sha256) | orchestrator |
| 2026-11-02 00:00 | q0345 installed in the host crontab; dry pass; watchdog check | coordinator |
| 2026-11-02 12:00 | first pass (tier snapshot), 10-min reads | collector |
| 2026-11-03 22:00 - 11-04 21:00 | 60-s reads; `cpu` jobs ≥ 500 MB held | collector, coordinator |
| 2026-11-06 00:00 | collector stops; q0346 runs | queue |

A missed row before the freeze is recovered only if the freeze still lands by 11-01T12:00Z; otherwise E is "not run
(calendar)", counted. P and L have no calendar binding and follow CB11-CB14 on the `net` lane.

## 7. Main scientific risks (for the challenger)

1. **E is one night.** The balanced contrast removes an additive national swing but not a swing that interacts with
   the sign (for example, a swing concentrated in mail votes). Inference treats states as exchangeable under a
   permutation; they are not independent draws of a programme. With the declared `σ_d = 20c`, E detects about 15c, not
   5c, and GEP's 3×-floor rule is a declared deviation. The sign table may be lopsided, which stops E at GEP.
2. **E's sign table is judgement.** Two blind passes and a strict agreement rule reduce, but do not remove, compiler
   bias. Sources for the 2022/2024 direction may be thin for some states (→ `s = 0`). The window is wall-clock from poll
   close, not reporting share (premise 4), so states that report slowly contribute less drift by construction (it
   lowers power; it does not bias the sign). Liquid races are kept; professionals may price the shift.
3. **L's source probably does not exist.** Archived LMArena pages hold no table (P5-P6), `/leaderboard/text` has few
   captures, and the HF dataset returned 401 in round 6. Even with a source, 26-30 events and few organisations give an
   MDE near 0.6-0.9 against 0.30. **Recommendation:** the challenger may withdraw L uncounted before q0354 runs, as CB14
   deferred CH127; otherwise L is counted and probably closes "not testable (source)".
4. **P is thin and worn.** Non-sports C1 is 167 pairs; P2 likely fails GP. Gap convergence is known (C1 r1, E010), so P1
   carries the "birth" label only through the binding later-life contrast. P keeps C1-only keys by declared deviation
   (premise 7). Birth prices of short-lived pairs were inside the C1 series (binding drop). `t_birth` from the first
   10-minute point may lag the true first print by up to 10 minutes, and Data API reach to the birth hour is uncertain
   for heavily traded markets (worst-case binding).
5. **E's key rule** (calendar disjointness, keys as a robustness check) departs from the full key rule; justified in
   §1.3.
6. **Collector risk on the night.** One host, 1 OCPU, shared with live collectors; gaps are logged and units become
   "unavailable" (never filled). The `/books` batch cap is unverified above 2 tokens (smoke).
7. **Fees** use the current `feeSchedule` with a 0.04 floor (as CB14).

## 8. Next actions

1. `science-reviewer` challenger round 1 on this draft, **part E first** (calendar). Open items for it: the 3× GEP rule,
   the E key rule, the P key-by-source deviation, the testability-minimum deviations (§2.3), whether to withdraw L
   uncounted before q0354, the priority-30 exception for q0341/q0344 (the coordinator must accept it).
2. Implementer: `seals/cb15_rules.json` parts `common` + `E`, `cb15_e.py` census path and tests by 2026-10-21; then the
   collector and E analysis by 2026-10-26 (§6 calendar). P and L code after E's freeze.
3. GE0 by 2026-10-23 (two blind `science-reviewer` passes).
4. E order: q0341 → GE0 → q0343 → q0344 → **E freeze by 2026-11-01T12:00Z** → q0345 installed by 11-02T00:00Z → q0346
   after 11-06T00:00Z.
5. P order: q0340 (behind CB14 q0302) → q0347 (GPB) → q0348 → q0349 → q0350 → P freeze → q0351; q0352 from 2026-11-04;
   q0353 if triggered.
6. L order (if not withdrawn): q0354 → q0355 (GLS) → q0356 → GL0 → q0358 → q0359 → q0360 → L freeze → q0361; q0362 only
   with a live source; q0363 if triggered.
7. CB16 adds CB15's frame ids. Ledger lines for every counted result; checkpoint and plain-English dashboard updated by
   the orchestrator.
