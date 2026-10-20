# Creative batch 17 (CB17): open versus close, the book's own clocks (age and breathing), event mint share; first-day prints as a census

`evidence_role: prospective` (CB17-A, CB17-B, CB17-C: every counted stage runs on live host windows that start after
the rules freeze) / `exploratory_historical` (pre-freeze censuses on the worn CB13-T SCREEN window, counts only) |
status: **DRAFT-REVISED after challenger round 1 (the batch's one challenge and one response, §10). Nothing frozen,
nothing queued, no code.** Drafted 2026-10-19 22:03 UTC+1 (2026-10-19T21:03Z) on parent `2ee87bea`; revised the same
day after the challenger's verdicts (A, B1, B2, C REVISE; E census and q0400-q0403 PROCEED once part `pre` holds the
findings 2 and 7 additions). The revision used no CB17 data and no outcome data.
**2026-10-20: part `pre` committed and q0400-q0403 run (counts only); branch T, A withdrawn uncounted; the filled values
and open questions are in §11 (no rule in §0-§10 changed).**
**No CB17 quantity has been computed:** no mark-out, slope, contrast, continuation, pick-off loss, net or proxy
standard error. Three read-only, counts-only host probes were run for this draft (§0.3; scripts verbatim with sha256 in
§9). Nothing was fetched, written, moved or deleted on the host.

This file turns the round-8 top five of `CREATIVE_HYPOTHESES_2026-10-22.md` (§3) into declared, falsifiable designs:
- **CH144** (open versus close) becomes **CB17-A**, counted (A1).
- **CH146** (book age at the fill) and **CH147** (the sticky touch and the breathing book) become **CB17-B**, counted
  (B1, B2). They share one sweep-level frame.
- **CH150** (mint share / event open interest) becomes **CB17-C**, counted (C1).
- **CH154** (first-day prints) becomes **CB17-E, a census only (k = 0)**: probe P1 found 30 touch-signed non-sports
  first-day fills and 7 markets with both first-day and later fills in four days (§0.3), so no counted test can be
  powered on a 14-day window. A declared re-entry rule keeps it alive for a later batch (§CB17-E).

The file follows `CREATIVE_BATCH_16.md` (CB16) in structure and rules. "As CB16 §x" means that rule applies unchanged,
including the challenger and freeze-check fixes CB16 inherits from CB13-CB15. CB4 amendment A-C1 and the CB10 §2.3
small-G rule govern clusters.
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim. AREPO never
  trades. Every P&L is a paper rule at recorded prices (prints, capture touches and sweep touches).
- Test tables bind only once the CB17 rules file `seals/cb17_rules.json` is committed after an accepting challenger
  round, hashed per part (`pre`, `common`, `A`, `B`, `C`, `E`). Parts bind on their own calendars; no rule of one part
  changes after another part's read.
- **Lanes.** Every CB17 job is on the **`cpu` lane with no network**. Nothing is fetched. This is the round-8 brief:
  the `net` lane is saturated by CB6-CB16, the `cpu` lane is idle. Four features-only census jobs on worn data
  (q0400-q0403) can start as soon as their code and tests exist; none waits for a freeze, a window or another batch.
- **Queue ids q0400-q0429, one id per job, no letter suffixes.** CB16 uses q0380-q0392 and reserves to q0409; this
  draft takes q0400 as instructed, so **CB16's reservation is narrowed to q0393-q0399** (CB16 used none of q0393-q0409;
  checked: `queue/jobs/` holds nothing above q0392). Used: q0400-q0412; q0413-q0429 reserved. Specs are drafts **in this
  document only** (§4); nothing is written to `queue/jobs/` or `queue/drafts/`.
- **Naming.** Outputs go under `research_lab/creative_batch17/`. CB17 writes no `history/` root.

## 0. Summary, selection and scope

| Rank | Family | Hypothesis | Counted tests | Stage 1 data | Stage 2 data | Queue ids |
|---|---|---|---|---|---|---|
| 1 | **CB17-A** open versus close (CH144) | A taker buy of a token opens a position and a taker sell closes one (a sell needs a held token). Within a market and a YES-terms direction, the maker's 2-4 h mark-out on fills against **openers** is worse than on fills against **closers** by ≥ 0.5c per filled share (A1). **Runs only under branch S; under branch T the family is withdrawn uncounted before its part commit (§CB17-A)** | A1 (within market × direction) | monitor transactions and complete-universe captures in **SCREEN_8** (14 days from `S_8`, not before 2026-10-26) | **REP_8** (next 14 days), events with a SCREEN_8 unit dropped: A1-rep; A2 (recorded-touch maker round trip on close fills, an upper bound) | q0400, q0404, q0405, q0407-q0412 |
| 2 | **CB17-B** book age (CH146) and breathing book (CH147) | B1: the 2 h excursion beyond the touch (adverse movement only, not a maker net) is larger in books whose CLOB last-update stamp is ≥ 10 min old than in books updated < 60 s ago, within token, by ≥ 0.5c. B2: with the touch unchanged across a pass's two sweeps, the 2-minute shift of depth 1-5c beneath the touch predicts the signed 2 h mid change, ≥ 0.5c per SD, within token | B1, B2 | book sweeps of **arm-0 events** in SCREEN_8 | sweeps of **arm-1 events** in REP_8 (event-disjoint by a seeded event hash): B1-rep, B2-rep; B1-econ, B2-econ (fill-level within-market differences at recorded prices) | q0401, q0403-q0406, q0408-q0412 |
| 3 | **CB17-C** mint share (CH150) | In a 2 h interval where an event traded, the ratio of its open-interest change to its volume change separates mint, transfer and merge. Within event, a member's interval move continues more after a transfer-heavy interval than after a mint-heavy one, by ≥ 0.5c over the next 2 h (C1) | C1 | captures (rows and sidecar) of arm-0 events in SCREEN_8 | arm-1 events in REP_8: C1-rep; C1-econ (fill-level within-event difference at recorded prices) | q0402, q0404-q0406, q0408-q0412 |
| - | **CB17-E** first-day prints (CH154) | **Census only (k = 0).** Counts first-day transactions and markets with first-day and later prints, and a feature-proxy SE. A declared re-entry rule decides whether a later batch may register a counted test on a fresh window | none | features of SCREEN_8 transactions | none | q0400, q0408 |

**Counted (§2.5), fixed by q0400's outcome-blind branch result before any part commit:**
- **Branch S:** 4 fixed (A1, B1, B2, C1) + up to 8 conditional (A1-rep, A2, B1-rep, B1-econ, B2-rep, B2-econ, C1-rep,
  C1-econ) = **4-12, k1 = 4**.
- **Branch T:** family A withdrawn uncounted before its part commit (CB15-L precedent; §CB17-A): 3 fixed (B1, B2, C1) +
  up to 6 conditional (B1-rep, B1-econ, B2-rep, B2-econ, C1-rep, C1-econ) = **3-9, k1 = 3**.

No CB17 test is added after any CB17 read. E adds nothing (no counted test is declared).

**Honest expectation.**
- **B1, B2 and C1 are powered far below their floors** (planning MDE about 0.05-0.2c against 0.5c). For them the floor
  and the composition checks bind, not power. B1's composition runs *against* its hypothesis (old books sit in quiet
  hours and quiet tokens, which carry less movement), so its likeliest verdict is "not detected"; B2 is near round 8's
  own kill (22% of touch-unchanged pairs have a shifted book beneath, against a 20% kill; P2).
- **A1 depends on how fills are signed** (§CB17-A, branch rule). On the CB13-T touch-consistent rule alone, P1 found 364
  non-sports fills in 44 market × direction cells with both labels in four days; the planning MDE is 1.1-1.7c against
  the 1.0c power gate, so A1 would most likely be "not run (power)". **Under branch T, A is therefore withdrawn
  uncounted before its part commit** (challenger finding 7). If the pre-freeze census q0400 shows the Data API `side`
  agrees with the touch-derived side in at least 97% of resolved non-sports fills overall **and in every touch-age band,
  price band and class with n ≥ 100** (a declared, outcome-blind rule in part `pre`), A1 is signed by `side` on every
  non-sports transaction and its planning MDE falls to about 0.6-0.9c. **Even then, power at a true effect equal to the
  0.5c floor is only about 40%** (disclosed; the floor, not 80% power, is the design target).
- **Every economic test is a maker-protection or upper-bound check.** No taker route in this batch is expected to clear
  the 4.5c median round trip (1.8c in markets with liquidity ≥ $100k) or the monitor's 9-minute median receipt lag;
  taker lines are reported only.

### 0.1 Queue id mapping (one id per job)

| Id | Job | Family | Earliest commit |
|---|---|---|---|
| q0400 | `cb17_pre_census_A` (worn CB13-T SCREEN fills + prints: open/close label counts, both-label cells, **side-agreement branch measurement with per-band agreement**, **strata-ladder informativeness shares**, first-day counts, planning SE on the pre-fill proxy) | A, E | once part `pre`, its code and tests exist |
| q0401 | `cb17_pre_census_B` (worn sweeps `[10-12, 10-16)`: stamp-semantics gate, age histogram, touch-unchanged and shifted-beneath shares, next-pass no-mark share by age bin, **global activity cut points**, **strata-ladder informativeness shares**, CH149 dormancy map, planning SEs on pre-sweep proxies) | B | as q0400 |
| q0402 | `cb17_pre_census_C` (worn captures `[10-12, 10-16)`: OI update rate, units with ≥ 6 prior traded intervals (trailing terciles), within-event IQR of `r`, single / neg-risk splits, **strata-ladder informativeness shares (3-class rule)**, planning SE on the pre-interval proxy) | C | as q0400 |
| q0403 | `cb17_cost_lag_map` (CH155 part: cost at $1,000 and $5,000 from sweep depth bands by class × price band × liquidity; monitor receipt-lag table; enrichment coverage) | all (cost hurdles) | as q0400 |
| q0404 | `cb17_smoke` (part hashes, refusals, parsers, event-arm hash, reproduction of P1-P3 counts on worn files) | all | after rules parts `common`, `A`, `B`, `C`, `E` are committed |
| q0405 | `cb17_exclusion_keys` (`cpu`, no network: CB16 q0380 key file pinned + seal copies; overlap counts) | all | after q0404 PASS and CB16 q0380 (or its stop record) |
| q0406 | `cb17_frame_screen_BC` (SCREEN_8 arm-0 sweep units and event intervals, features only) | B, C | not before `S_8 + 14 d + 8 h` |
| q0407 | `cb17_frame_screen_A` (SCREEN_8 transactions, fill source per branch, labels, E features; no mark; E features only if A was withdrawn) | A, E | not before `S_8 + 14 d + 8 h` |
| q0408 | `cb17_census_8` (gates, incl. the SCREEN_8 signing check GAS under branch S; power gates on proxies, SEs only; E census and re-entry verdict) | all | after q0406 and q0407 |
| q0409 | `cb17_screen_8` (A1, B1, B2, C1 under branch S, Holm k1 = 4; B1, B2, C1 under branch T, Holm k1 = 3) | A, B, C | after q0408, E011's analysis commit, CB3's freeze commit (or stop record) and the code-against-design freeze check |
| q0410 | `cb17_frame_rep` (REP_8 frames, raw mark-quote tables, sha256 seal) | A, B, C | not before `S_8 + 28 d + 8 h`, after q0409 |
| q0411 | `cb17_rep_8` (triggered Stage-2 tests) | A, B, C | only if A1, B1, B2 or C1 advanced; after q0410 |
| q0412 | `cb17_stage2_final` (one CB17-wide strict Holm over triggered Stage-2 tests; write-once) | all | after every triggered Stage-2 test is final |
| q0413-q0429 | reserved | - | - |

### 0.2 Selection and scope

**Ranking rule.** As CB16 §0.2, with this round's brief: (a) host-only, `cpu` lane, no fetch; (b) round-8 rank;
(c) a within-unit contrast with a composition check as the primary design; (d) wallet-free. **No CB17 statistic reads
any wallet field.** The Data API `side` field is read only by q0400 (an agreement count) and, under branch S only, by
part A's frames (§CB17-A).

**What the drafting session read (2026-10-19T18:50-21:00Z).** CLAUDE.md, AGENTS.md; round 8 in full; CB16 in full
(template); CB13 §CB13-T (fill anchor, touch-consistency band, marks, LABELLER, GTI) and the CB13-T census output keys
on the host; `queue/README.md`; `EXECUTION_COSTS.md`; the ledger tail (CB13-T GT failed and q0273 promoted; CB16 code
done, the implementer's composition-placebo flag; CB9-S data side not yet run); `book_sweep.py` (field definitions:
`depth_*_1c/5c` are share sums within 1c / 5c of the best level, inclusive; `book_timestamp` and `book_hash` are the
CLOB's `timestamp` and `hash`); `ext_sidecar.py` (`event_open_interest` = Gamma event `openInterest`, `event_volume` =
event `volume`); round 4's CH79 (side-flag doubts).

**Prior work.**
- *A.* E007, HB1/HB2 and SB2 pooled opens and closes; CH42 and CH94 needed wallets; CH79 / CB9-S audit the `side` flag
  (not run yet). CB13-T split maker mark-outs by resolution class (terminal "not testable (population)", counted).
  CB16-Q (grain) and CB16-U (silence) use the same fills and marks on overlapping days; both enter A1's attribution.
  **Within a market and a YES-terms direction, the open/close label is exactly the traded token** (opens are YES buys
  when YES is bid up and NO buys when it is offered down; closes are NO sells and YES sells respectively). A1 is
  therefore "which token the taker used", which no AREPO test has split.
- *B.* The ML panels' `quote_age_s` and `ml_quote_staleness_h` were Gamma `updated_at` ages (a different field; pooled
  features; no gain on 12.7% book coverage). E003 is the imbalance **level** (inconclusive); B2 is its 2-minute
  **change** beneath an unchanged touch, with E003's level as a covariate. CH133 (withdrawal on the sealed cross-venue
  stream) waits for E009/E010. CB16-Q is the grain of the lifted quote; CH148 (size footprint) is not in CB17.
- *C.* CH26 and CH41 needed wallets; CH09/CH66 are neg-risk mechanics; CB8-H found market-level OI blank. No AREPO test
  has used event OI as a state.

`battery2.cumulative_count()` (`battery2-count-v1`) gives **1,282** on the working tree at drafting (it includes the
uncommitted host union). It is not stable; every counting CB17 job records the value at its run.

**Premises corrected or fixed by the probes (they shape this design).**
1. **Touch-consistent fills are scarce, and both-label cells scarcer** (P1). Of 2,931 CB13-T SCREEN fills, 1,006 are
   non-sports; 971 resolve to one traded token; **676 open, 295 close (30% close)**. Only **44 market × direction cells
   in 34 markets and 26 events hold both labels (364 fills)** in four days. Round 8's "about 11,000 classified
   non-sports prints in 14 days" assumed every print is signed; CB13-T's 60-minute touch-age rule drops 48% of
   transactions (17,816 of 37,106) and the band drops 4,776 more. Hence the branch rule (§CB17-A).
2. **First-day fills almost vanish under touch signing** (P1): non-sports fills by market age `< 6 h` 3, `6-24 h` 27,
   `1-7 d` 114, `> 7 d` 849, unknown 13; **7 markets** with both first-day and later fills. New markets rarely have a
   capture touch under 60 minutes old. CH154 is demoted to a census (E).
3. **`book_timestamp` is a last-update stamp, not a response time** (P2). Within a pass, 65,771 of 65,771 non-sports
   token pairs with an unchanged hash kept the same stamp, and 139,880 of 139,880 with a changed hash changed it. The
   gate stays binding on the fresh window (GBT).
4. **Book ages on 2026-10-15** (P2; non-sports, first sweep of each pass): `< 60 s` 131,318 (64%), `60-600 s` 35,392
   (17%), `600-3600 s` 11,930 (6%), `> 3600 s` 27,071 (13%). Old books (≥ 10 min) are 19% but concentrated: **only
   1,733 of 24,249 tokens had both a fresh and an old sweep on the day.** B1's within-token contrast lives in that
   minority.
5. **The breathing book is near round 8's kill** (P2): of 205,651 two-sided non-sports pairs, the touch was unchanged in
   181,701 (88%), the hash changed beneath an unchanged touch in 115,930, but **the 1-5c band shifted in only 44,896
   (22% of pairs)**: most hash changes are touch-size or deep-level changes. Round 8's kill is 20%. B2 keeps all
   touch-unchanged pairs (zero shifts included) and gates at 20% (GBS).
6. **Event OI is live in the traded intervals** (P3, 2026-10-15, 11 intervals): 16,404 non-sports traded event-intervals,
   **OI changed in 14,271 (87%)** against round 8's 70% kill; single-market 2,280, neg-risk multi 9,470, other multi
   4,654; 9,956 with a member mid move ≥ 0.5c; **1,226 events traded in ≥ 6 of 11 intervals** in one day.
7. **Sweeps carry no title, so the CB13 LABELLER cannot run on B and C units.** B and C use a sidecar-only sports rule
   (fee type, fee category, frozen sports series list) and the first `series_slugs` entry as path key.
8. **The hash-split arm.** B and C units cover nearly every live market, so CB16's "drop REP events seen in SCREEN"
   would leave only events born after SCREEN_8. B and C therefore split events by a seeded hash (arm 0 screens, arm 1
   replicates); A keeps CB16's drop rule because its population is thin.
9. **Capture gaps exist.** The 2026-10-14 captures between 00:31Z and 10:31Z are missing on the host (listing,
   §0.3 P0). Missing captures and sweeps are "unavailable", counted, never back-filled.

### 0.3 Feasibility probes (counts only; 3 read-only probes + header listings; 0 fetches; nothing stored)

Run 2026-10-19 20:56-21:01Z over `ssh oracle`, after the 20:31 collector pass had ended, as `nice -n 19
/home/opc/arepo/.venv/bin/python -I /tmp/<script>`; peak RSS 65-183 MB. **The script texts and their sha256 were fixed
before the run** (sha256 computed locally and on the host before execution, identical; texts verbatim in §9); the
host copies were then removed (verified: none left). Nothing in `~/arepo/run/queue` was touched. **No mark-out,
forward price, outcome, resolution or wallet value was read or printed.**

Disclosed feature exposure:
- P1 decoded each monitor line of `trades-2026101{2..5}.jsonl` in memory (including the forbidden `side`, `wallet_hash`
  and `key`, never accessed) and used `condition_id`, `ts`, `tx16`, `outcome_index`; it read the CB13-T SCREEN fill table
  (`status`, `condition_id`, `market_id`, `event_id`, `label`, `tau`, `tau_last`, `d`) and `created_at` from two
  captures. It printed counts only.
- P2 decoded `best_bid`, `best_ask`, `depth_*`, `book_hash`, `book_timestamp`, `state` of the 24 sweeps of 2026-10-15 to
  test equality and the sign of differences between a pass's two sweeps, in memory; it printed counts only.
- P3 decoded `event_open_interest`, `event_volume`, `fee_type`, `neg_risk_market_id` and `best_bid`/`best_ask` of the
  12 captures of 2026-10-15; mid changes were computed between consecutive captures **k-1 → k only** (the interval
  itself, never a later capture). It printed counts only.
- **P0 header listings** (before the probes): header lines of a capture's `rows.csv.gz` and `rows_ext.csv.gz`, a
  sweep's `rows.csv.gz`, the CB13-T `fills.csv.gz` and `labels.csv.gz`; the key names of one monitor line; the status
  tally of the CB13-T fill table; the CB13-T `census_T.json` key tree with its counts; and, to learn the time formats,
  one fill's `tau`, `tau_last`, `d` and `touch_age_s`, one sweep row's `batch_receipt_utc` and `book_timestamp`, one
  `created_at` and one `received_utc`. These are features of the worn window; no price was printed.

| # | Script (sha256 prefix) | Inputs (all worn) | Printed |
|---|---|---|---|
| P1 | `cb17_p1_fills.py` (`e8f84790…`) | CB13-T SCREEN `fills.csv.gz`; `live_trades/trades-2026101{2..5}.jsonl`; `created_at` from captures `20261012T003103Z_2df48d64` and `20261015T223102Z_2eae9aa6` | fills 2,931; token resolved 2,715, ambiguous transaction 216; non-sports 1,006, resolved 971; **open 676, close 295**; by class (open/close): UNSCHEDULED-NEWS 259/158, SCHEDULED-EVENT 297/95, PATH-SETTLED 96/39, PUBLIC-STATISTIC 24/3; sports 1,359/385; non-sports (market, d) cells 440, **with both labels 44, fills 364, markets 34, events 26**; markets with both labels in any direction 66 (537 fills); non-sports fills by market age `< 6 h` 3, `6-24 h` 27, `1-7 d` 114, `> 7 d` 849, unknown 13; **markets with first-day and later fills 7**, with any first-day fill 24 |
| P2 | `cb17_p2_sweeps.py` (`ddedd91c…`) | the 24 sweeps of 2026-10-15 (12 intra-pass pairs); sports set from capture `20261015T063101Z_9c518015` | non-sports token-sweeps (first sweep) 205,711; sports 425,003; two-sided pairs 205,651; **hash same 65,771, of which stamp same 65,771; hash changed 139,880, of which stamp changed 139,880**; touch same 181,701; touch same with hash changed 115,930; **touch same with the 1-5c band shifted 44,896**; age bins (§0.2 premise 4); tokens with both fresh and old sweeps 1,733 of 24,249; next-pass presence 174,705 of 187,190 (93%) |
| P3 | `cb17_p3_oi.py` (`a95ced86…`) | the 12 captures of 2026-10-15 | non-sports event-intervals: traded 16,404, **OI changed 14,271**, not traded 32,488, OI or volume missing 37,516; traded single 2,280, neg-risk multi 9,470, other multi 4,654; traded with a member move ≥ 0.5c 9,956; events traded in ≥ 6 intervals **1,226**, ≥ 3 2,473, any 3,537 |

### 0.4 Selection decisions

| Idea | Decision | Reason |
|---|---|---|
| **CH144** open versus close | **include (A), counted** | Host-only; the label is a structural identity of the venue, wallet-free. Honest weaknesses: touch signing leaves too few both-label cells (premise 1), so A1's power depends on the declared side-agreement branch; a NO holder who exits by buying YES and merging is labelled an opener (attenuates) |
| **CH146** book age | **include (B1), counted** | Host-only; the stamp is a last-update stamp (premise 3). Weaknesses: old books are a minority of tokens (premise 4); age is endogenous to activity, and the composition bias runs against the hypothesis; the paper-maker fill rule only counts adverse crossings, so B1 measures the adverse component, not the maker's net |
| **CH147** breathing book | **include (B2), counted** | Host-only; shares B1's frame. Weakness: the shifted-beneath share (22%) is just above round 8's 20% kill; re-quoting bots may react to past moves (the binding pre-sweep placebo may stop it) |
| **CH150** mint share | **include (C1), counted** | Host-only; OI updates in 87% of traded intervals. Weaknesses: OI in shares against volume in dollars (within-event ranks only); neg-risk conversions move OI without trading; the 2 h capture cadence |
| **CH154** first-day prints | **demoted to a census (E, k = 0)** | Premise 2: 30 touch-signed non-sports first-day fills and 7 both-period markets in four days. Even under branch S the within-market contrast would rest on a few hundred markets at MDE ≥ 1.5c. Its census runs on SCREEN_8 features and decides re-entry |
| CH145 exit pressure | not in CB17 | CH144's companion; its market-state is built from A's label, so it should wait for A1's census and verdict rather than share its window |
| CH148 size footprint | not in CB17 | Round 8 makes it conditional on CB16-Q leaving the maker loss unexplained; CB16-Q has not run. q0401 tabulates age by grain and size class (reported) so the later decision has its inputs |
| CH149 dormant ladders | **map folded into q0401** (k = 0) | A census of four tables; no test |
| CH151 holder turnover | not in CB17 | Borderline MDE (1-1.5c against 1.0c) by round 8's own count; shares C's frame and can follow C's census |
| CH152 reward-rate shocks | not in CB17 | Must first pass its endogeneity (pre-trend) and toggle-frequency gates; a separate census is the right first step, not a counted test sharing B's frame |
| CH153 synchronous prints | not in CB17 | Thin outside sports (1,000-1,500 in 14 days; planning MDE 1.5-2c against 0.5c) |
| CH155 cost and lag map | **folded into q0403** (k = 0) | It is the cost hurdle every economic line here cites |

**Sports and categories.** `CB17_SPORTS_IN_PRIMARY = false` (a parameter, as CB8-CB16). A excludes the pinned CB13
LABELLER's SPORTS-FEED class; B and C exclude markets and events whose sidecar `fee_type` or `fee_category` is a
sports value or whose first `series_slugs` entry is on the frozen sports series list. Every statistic is also reported,
uncounted, for the sports arm, and A by LABELLER class.

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Prior use | Role in CB17 | Evidence ceiling |
|---|---|---|---|
| `live_trades/trades-YYYYMMDD.jsonl` for `[max(lookback floor, S_8 − 7 d), S_8 + 28 d + 8 h)` (lookback floor 2026-10-26T00:00Z; **no row before the floor is ever read**, challenger finding 5) | CB13-T, CB16-Q/U | **A units** (transactions), the fill source of every econ test, E's census. Whitelisted fields only (§1.4) | L2 (post-freeze live window) |
| `snapshots/<capture>/rows.csv.gz`, `rows_ext.csv.gz`, same span | E001-E011, CB1-CB16 | A's touch and marks; **C's units** (event OI, event volume, member mids); B's sports rule and end dates | L2 |
| `book_sweeps/<sweep>/rows.csv.gz`, same span | E003, CB3, CB13, CB16 (reported shape) | **B's units** (both sweeps of each pass) and B's marks | L2 |
| CB13-T SCREEN fill table (`creative_batch13/t_screen/`), monitor files, sweeps and captures of `[2026-10-12, 2026-10-16)` | CB13-T Stage 1 (worn); round-8 and CB17 probes | **pre-freeze censuses only** (q0400-q0403): counts and planning SEs on pre-outcome proxies. Never a counted statistic | counts |
| `surprise_live/` (E011), `cross_venue_live/` (E009/E010), `e001/`-`e007/`, `forecasts/`, `flow_screen/`, `trade_samples/`, `cb3_extract/`, `cb3_followup/`, `creative_batch16/` (CB16 stores), `creative_batch13/t_holdout/` and every `h*` root; `live_trades/{alerts,outcomes,wallets,stats}.jsonl`, `scores-*.jsonl`, `state.json` | registered experiments, other batches | **never opened** (runner refuses; unit-tested) | - |

**Reuse disclosure.** SCREEN_8 and REP_8 do not exist at drafting. They overlap CB16's SCREEN_A/REP_A (from about
2026-11-02), CB3's Stage 2 (from 2026-10-27), CB14-W live (from 2026-10-26), E011 (to 2026-11-10) and other live
stages: collection overlap only (§1.3). **REP_8 overlaps CB16's SCREEN_A and REP_A in time** (disclosed; ruling 8).
**A1's units overlap CB16-Q/U's units on the overlapping days** (a superset of the touch-signed monitor fills under
branch S), so A1 and CB16-Q/U are correlated tests; each is counted in its own batch's Holm family (separate families
per batch, ruling 8). **A1 and CB16-Q/U are never cited as corroborating each other**, whatever their verdicts.

### 1.2 Dates (declared; UTC)

| Name | Value | Meaning |
|---|---|---|
| `T17_draft` | 2026-10-19T21:03Z | this draft; no CB17 quantity computed |
| `T17_rules` | target **2026-10-24T12:00Z** (soft) | commit of `seals/cb17_rules.json` parts `common`, `A` (branch S only; under branch T A is withdrawn uncounted and part A is never committed), `B`, `C`, `E` after the round-1 response is accepted and q0400-q0402 have selected the strata levels. Part A records the branch (§CB17-A) |
| `S_8` | `max(2026-10-26T00:00Z, the first 00:00Z at or after T17_rules + 24 h)` | start of SCREEN_8; depends only on the rules commit time, never on data |
| SCREEN_8 | decision times in `[S_8, S_8 + 14 d)` | Stage 1, all families |
| REP_8 | decision times in `[S_8 + 14 d, S_8 + 28 d)` | Stage 2. B and C: arm-1 events only. A: every Gamma event with a SCREEN_8 unit dropped, **binding even if thinned** (label "REP_8 thinned by event overlap" above 40%) |
| event arm (B, C) | `arm(e) = int(sha256("cb17-arm-v1|" + event_id).hexdigest()[0], 16) mod 2`; `event_id` = Gamma event id, else the market id | arm 0 → SCREEN_8 units, arm 1 → REP_8 units. Disjoint by construction; fixed before data |
| `T17_code` | **target: before `S_8`** (preferred, ruling 6); at the latest before the first read of any SCREEN_8 row (q0406/q0407); never before an accepting code-against-design freeze check | **Declared deviation from CB16** (whose part A was frozen with code before `S_A`), **accepted by the challenger with conditions (ruling 6):** (i) no agent working on CB17 (designer, implementer, reviewer, or the orchestrator acting for CB17) opens any SCREEN_8 or REP_8 raw file before q0406 runs; other registered jobs' automated reads under their own rules are not CB17 reads; the ledger carries a signed attestation at the code freeze and again with q0406's commit; (ii) the freeze check re-runs q0404's exact reproduction of P1-P3 against the frozen code (a different count fails the freeze); (iii) if the code is frozen after `S_8`, the ledger records the gap and the attestation covers it. Rationale: runner refusals make window rows unreadable before `S_8 + 14 d + 8 h`; the conditions close the human-read route |
| election-night exclusion | decision time or mark time in `[2026-11-03T18:00Z, 2026-11-05T00:00Z)` | excluded and counted (CB15-E's night) |
| marks | A: as CB13 §2.2 (first complete capture with `received_utc ≥ τ + h`, usable iff `≤ τ + h + 2 h`; "2-4 h", "6-8 h"). B: the token's first sweep of the first pass with receipt in `[t + 110 min, t + 130 min]` ("2 h"), and `[t + 350, t + 370 min]` ("6 h", robustness); a missing mark is "no mark", counted by state bin, bounded in a binding worst case (§CB17-B). C: the next consecutive complete capture `k + 1` (gap 100-140 min); a missing or ineligible `k + 1` quote is "unavailable (mark)", never an eligibility condition (§CB17-C) | realised horizons stated in every table |
| capture time | a capture's `received_utc` is stamped per page (`ext_sidecar.py` `ext_row`); **a capture's time is the `received_utc` of its last page** (the maximum), for every CB17 use (A's touch age and marks, C's decision time and gaps, E's market age) | finding 8 |
| lookback floor | 2026-10-26T00:00Z | no CB17 window path reads a row timed before it (keeps J4-R `[10-16, 10-21)` and CB13-T HOLDOUT `[t_j4r_end, 10-26)` untouched). **Every window reader refuses pre-floor rows**, including the lookbacks of q0406 (sweeps from `S_8 − 2 h`, captures from `S_8 − 6 h`), q0407 (captures from `S_8 − 3 h`) and q0410; a unit whose rule needs a pre-floor row (A's touch capture or pre-fill capture; B's previous-pass activity, `L_pre`, `Δm_pre`; C's `k − 1`, `k − 2` or trailing intervals) is **"unavailable (lookback floor)", counted by family and label/state**, never back-filled (finding 5). With `S_8` = the floor, this affects only the first hours of SCREEN_8 |
| E011 | registered to 2026-11-10; analysed once after 2026-11-11T13:00Z | q0409 refuses before E011's analysis commit (SCREEN_8 ends 2026-11-09, so this costs about two days) |
| CB3 Stage 2 | `[T3_rep_start ≥ 2026-10-27, …)` | q0409 and q0411 require CB3's freeze commit or its ledger stop record |

If `S_8` slides, both windows slide with it; lengths stay fixed. With `S_8` = 2026-10-26, SCREEN_8 ends 2026-11-09
and REP_8 ends 2026-11-23.

### 1.3 Sealed and untouched data (named)

- **Refused roots** (§1.1 last row). `run_cb17.py` writes only under `research_lab/creative_batch17/`. Window readers
  refuse any row timed before the lookback floor (except the q0400-q0403 census paths, which read only the worn
  `[2026-10-12, 2026-10-16)` files and never a row timed after 2026-10-16T00:00Z), and refuse REP_8 rows until the
  SCREEN_8 result file and `seals/cb17_rep_SEAL.json` are committed and verify.
- **E011.** C's object (a 2 h move and its continuation) and B's (a move through a stale touch) are close to what E011's
  detector finds. CB17 never opens `surprise_live/`, never computes a detector score or label, defines no E011
  subgroup, runs its screen only after E011's analysis commit, and reads captures read-only.
- **E004-E007.** Never opened; `chg_1h`, `chg_1d`, `chg_1w` never parsed. A's label is not E007's signed flow (A1 is
  within direction).
- **E009/E010.** `cross_venue_live/` never opened.
- **CB13-T.** Its windows are untouched; the census q0400 reads the SCREEN fill table (worn). A imports CB13-T's fill,
  touch-consistency, mark and LABELLER functions **by pinned sha256**; no CB17 output pools with or cites a CB13-T
  result. CB13-T's HOLDOUT `[t_j4r_end, 10-26)` stays sealed for T (it is never claimed by CB17 although T is terminal:
  no redraws).
- **CB16.** CB17 never opens `creative_batch16/`. A1's attribution recomputes CB16's grain `g` and silence `x` from
  CB16's pinned functions on CB17's own units. No CB17 output defines a CB16 subgroup.
- **CB3, CB14, CB12-E/O, CB10-D, CB9-P, CB15-P**: collection overlap only; stores never opened; the census reports how
  many CB17 units fall in markets those stages name where their frames exist.
- **Exclusion keys (q0405, no network).** CB16 q0380's `exclusion_keys.csv.gz` (sha256 pinned; source-attributed) and
  every seal copy under `docs/research_lab/seals/` by then. A market or event is dropped only if it appears in a sealed
  historical set with a stored timestamp inside SCREEN_8 or REP_8 (none expected); drops are counted by source. CB16's
  frame ids are added as overlap counts once CB16 q0384 exists (CB16 §1.3's note to CB17); live frames are collection
  overlap, not drops.
- **Outcome guards.** No CB17 path reads a resolution outcome. Marks are price-based; econ tests exit at a recorded
  touch. `uma_resolution_statuses`, `outcome_prices` and `closed_time` are never parsed.

### 1.4 Rules files and whitelists

- `seals/cb17_rules.json`, hashed per part:
  - **`pre`** (committed with q0400-q0403's code, **before q0400 runs**; required by the challenger before any
    pre-census code): worn-window paths and dates and the census paths' refusal of any row at or after 2026-10-16T00:00Z;
    field whitelists for the censuses; **the side-agreement branch rule with its per-band criteria and the A-withdrawal
    rule under branch T** (§CB17-A; finding 7); **the strata ladders of A, B1, B2 and C, the informativeness definitions
    (including C's three-class rule) and the level-selection rule** (§2.6; finding 2); **B's global activity cut-point
    recipe and C's trailing-tercile rule** (finding 6); the planning-SE recipe (SEs only); the cost-map size grid.
  - **`common`**: refused roots, the lookback floor, the J4-R pin, seeds, cluster ways, the small-G rule, Holm/BY
    settings, disk guards, whitelists, smoke criteria, the key rule, the event-arm hash, the composition-check rule
    (§2.6), pinned sha256 of the CB13 and CB16 functions called.
  - **`A`** (branch S only): the branch outcome, fill source, label rule, eligibility, marks, ways, the selected strata
    level, covariates, gates (incl. GAS), the d-balanced estimate, A2.
  - **`B`**: eligibility, age bins, the 2 h excursion beyond the touch, the shift state and its frozen SD, the frozen
    activity cut points, marks and the no-mark worst case, the selected strata levels, gates, econ rules.
  - **`C`**: interval rule (k − 1 and k only), `r`, trailing tercile classes, continuation and the unavailable-mark worst
    case, the selected strata level, gates, econ rule.
  - **`E`**: first-day rule, census counts, re-entry rule.
- **Order.** Part `pre` is committed first; q0400-q0403 run; then parts `common`, `A` (branch S only), `B`, `C`, `E`
  are committed with the branch and the selected strata levels written in. Nothing in a later part is chosen from a
  mark, an outcome or a statistic; the strata levels and the branch are chosen from features by rules fixed in `pre`.
- Jobs refuse (exit 2) on a hash mismatch. **No rule is computed from, or revised after, any CB17 mark, outcome or
  statistic.**
- **Whitelists.** *Monitor prints:* as CB16 §1.4 (`ts, condition_id, token_id, outcome_index, price, size, cash, title,
  slug, ctx_event_id, ctx_market_id, ctx_category, ctx_fee_type`; `tx16` in memory only). **`side`**: parsed only by
  q0400 (agreement count) and, under branch S only, by q0407 and q0410. **`recv_ts`**: q0403 only. Never: `key`,
  `wallet_*`, other `ctx_*`. *Captures:* `capture_id, received_utc, market_id, condition_id, event_id, closed, active,
  binary, best_bid, best_ask, liquidity, volume24hr, end_date, clob_token_id_0, neg_risk, neg_risk_market_id`.
  *Sidecar:* `market_id, event_id, fee_type, fee_category, fee_schedule, order_price_min_tick_size, clob_rewards`
  (presence and `rewardsDailyRate` only), `created_at, event_open_interest, event_volume, series_slugs,
  neg_risk_market_id, accepting_orders`. *Sweeps:* every `ROW_COLUMNS` field except `batch_index`. A unit test feeds
  fixtures carrying every forbidden field and asserts none reaches a parsed row, file or log.

## 2. Common rules (deltas from CB16 §2)

### 2.1 Costs

| Test | Price and cost rule |
|---|---|
| A1, B1, B2, C1 and their reps | none charged (mechanism contrasts in mark-out or move units); A1's and B1's levels are **upper bounds** for any maker, labelled so |
| A2 | CB13-T3's rule on REP_8 **close-labelled** fills: maker entry at the maker-adverse price `P` (fee 0, no rebate); exit as a taker at the adverse touch of the 2-4 h mark capture; taker fee `r·x(1 − x)` with `r` the sidecar rate, `max_if_unknown` (0.07); position `min(size, 100)` shares. **Label: "upper bound; the close label is known only after the fill, so this is not an implementable quoting rule"** |
| B1-econ, B2-econ, C1-econ | the same round trip on REP_8 fills from the fill source (§CB17-A), as **within-market (B) or within-event (C) differences** between the flagged group and the rest, which are cost-neutral to any exit cost common to both groups (CB16 U2's rule). A second component is the flagged group's net level, reported |
| Binding cost robustness | A2: +0.5c on the exit keeps net > 0. Differences: none (vacuous, CB16 round 1 item 11) |
| Reported taker lines | taker follow (B2, C1) or fade (A) at the recorded ask/bid of the first capture after `decision + 9 min` (the monitor's median receipt lag; A) or of the decision capture (B, C), exit at the adverse touch 2-4 h later, fee as above; compared with q0403's cost at size and with the 4.5c / 1.8c hurdles. Never counted. *q0403 cited in §11.4 (cell rule O4; measured median lag 8 min)* |

### 2.2 Clocks

- **Monitor transactions (A, econ fills).** As CB16 §2.2: venue `ts` = `τ`; prints aggregated by (`tx16`,
  `condition_id`); YES terms; a transaction with prints on both outcome indices is "mixed token", excluded and counted.
- **Captures.** The decision touch is the latest complete capture with `received_utc < τ` (A: age ≤ 60 min under
  branch T, ≤ 135 min under branch S); crossed or one-sided rows are ineligible, never repaired.
- **Sweeps (B).** The decision time `t` of a pass is the **second** sweep's `batch_receipt_utc` for that token (B2) or
  the first sweep's (B1). Book age `a = batch_receipt_utc − book_timestamp/1000` (seconds); `a < −5 s` is "clock
  anomaly", excluded and counted. A pass's two sweeps are the two consecutive sweep directories whose start stamps are
  < 30 min apart; a token pair more than 5 min apart is "split pass", excluded.
- **Event intervals (C).** Consecutive complete captures `k − 1`, `k` with gap in [100, 140] min between their last-page
  `received_utc` values; the decision time is **the `received_utc` of capture `k`'s last page** (finding 8); every
  eligibility rule, state and stratum uses captures `≤ k` only. Capture `k + 1` is read only for the target (the mark)
  and its availability.
- `closedTime` is never a population condition, origin or feature.

### 2.3 Uncertainty and decision rule

As CB16 §2.3: unweighted primary; one-sided p = the max over the declared ways; analytic multi-way CR1 for the primary
and a 2,000-draw cluster bootstrap (**seed 1717**) for A (B and C use analytic CR1 only; their bootstrap is reported,
because 1-2 M rows × 2,000 draws exceeds the 3 CPU-hour budget); the small-G rule (G ≥ 30 CR1; 15-29 CR2 with
t(G − 1) and the Webb wild bootstrap, 9,999 draws; G < 15 leaves the max and the leave-one-cluster-out sign rule
binds). "Unknown" never counts as met. The 60% availability rule applies.
- **Ways.** Gamma event (CR1); **path key × 6-hour block** (A: CB13's path key; B, C: the first `series_slugs` entry,
  else the event); **6-hour block** (G = 56); **UTC hour of day** (G = 24, CR2; B and C only, where night composition
  is a live threat). **UTC day** (G = 14) never enters the max; **leave-one-day-out must keep one-sided p < 0.05 and
  the sign.**
- **Stage 1 (A1, B1, B2, C1).** A test advances iff: one-sided p < 0.01 (strict); the §2.4 floor; every binding
  composition check, placebo, robustness and gate; and a batch Holm step-down at one-sided α = 0.05 over **k1 = 4
  under branch S, k1 = 3 under branch T** (fixed at the part commits; first step 0.0125 or 0.0167, so any p < 0.01
  passes). BY (q = 0.10 over the cumulative count at the run) is triage
  only.
- **Stage 2.** One CB17-wide strict Holm at one-sided α = 0.05 over every triggered Stage-2 test (≤ 8 under branch S,
  ≤ 6 under branch T), each in its declared direction. A test finishing before k2 is known is judged at **α/8** (strict;
  kept at α/8 under branch T too, which is stricter than α/6). Two-component econ tests
  enter with the max of their component p's. `checks_ok` is recorded per test (CB13 fix A). The final Holm (q0412) is
  applied once and can only add passes. Labels: reps "later live window replication, event-disjoint (L2)"; econ
  "recorded-touch round trip (L2)".

### 2.4 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate (with the sign) |
|---|---|---|
| A1 | mechanism contrast | `β_A ≥ +0.5c` per filled share: close fills better for the maker than open fills |
| B1 | mechanism contrast (adverse movement only) | `β_B1 ≥ +0.5c` of 2 h excursion beyond the touch per touch quote pair: old books worse |
| B2 | mechanism slope | `β_B2 ≥ +0.5c` of signed 2 h mid change per SD of the shift state |
| C1 | mechanism contrast | `β_C ≥ +0.5c` of 2 h continuation: transfer-heavy intervals continue more than mint-heavy |
| A2 | economic level | close-fill net ≥ **+0.5c** per filled share after the exit fee |
| B1-econ, B2-econ, C1-econ | economic (protection value) | **primary:** flagged-minus-rest difference of the round-trip net ≤ **−0.5c** per filled share; **second component:** the flagged group's net ≤ **−1.0c** |
| reps | as Stage 1 | as Stage 1 |

**Why these floors.** 0.5c is round 8's floor for every top-five idea and CB16's for Q and U: it is about a third of the
median maker half-spread (`EXECUTION_COSTS.md`: median spread 2.2-4.1c by price band) and about a quarter of the
liquid-market round trip (1.8c). Below it, no protection or quoting rule changes a maker's net materially.

### 2.5 Counting (M3 rule)

- Kinds **`cb17_test`**, **`cb17_replication`** and **`cb17_descriptive`** (EXCLUDE), mirroring CB16's
  `battery2.KIND_RULES` entries; unknown kinds raise. Descriptive lines: the pre-censuses (q0400-q0403), the smoke,
  censuses, gates, the branch decision, the E census and re-entry verdict, class strata, sports arms, reported variants,
  the CH149 and CH155 maps, taker lines.
- **Count lines (`ml_explain` `n_tests`):** `creative_batch_17:A` **1** (branch S only), `creative_batch_17:B` **2**,
  `creative_batch_17:C` **1**. Replication lines `creative_batch_17:<family>:rep` carry triggered tests (A ≤ 2, B ≤ 4,
  C ≤ 2).
- **Triggers.** A1-rep and A2 iff A1 advanced. B1-rep and B1-econ iff B1 advanced; B2-rep and B2-econ iff B2 advanced.
  C1-rep and C1-econ iff C1 advanced.
- **Budget: branch S 4 fixed + ≤ 8 conditional = 4-12 (k1 = 4); branch T 3 fixed + ≤ 6 conditional = 3-9 (k1 = 3).**
  Tests behind a failed or unknown gate are "not testable (...)" or "not run (...)" with p = 1 and **still counted**.
  Gates: the smoke, disjointness, GBT, GBA, GBS, GCU, GC, GA, **GAS (signing)**, the power gates GAP, GB1P, GB2P, GCP,
  GAI, availability, **composition-check informativeness** and the Stage-2 minimums. A job waiting on exit 75 is
  "pending" and writes no line.
- **Withdrawals that stay uncounted.** A family may be withdrawn uncounted only before its rules part is committed and
  only on reasons that use no CB17 window data (CB15-L precedent). After the commit, every declared test is counted.
  **Declared withdrawal (finding 7):** if q0400 selects branch T, family A is withdrawn uncounted at that point (the
  reason is q0400's worn-data agreement measurement and the branch-T planning MDE, both outcome-blind); part A is never
  committed, q0407 builds E's features only, and the ledger records the withdrawal before any other part is committed.

### 2.6 Composition checks, placebos and robustness (common; a declared change from CB16)

**The change and its justification.** CB16 as drafted made a stratified permutation placebo primary: permute the label
within fine strata and require each permuted test to fail p < 0.01, with an advance rate ≤ 1.5%. The CB16 implementer
flagged (ledger, CB16 code entry) that this placebo **retains part of a true effect**: when strata are finer than the
fixed effects, single-label strata keep their labels under permutation, so the permuted estimator still carries part of
the effect, and the placebo failed exactly when the label mattered. **CB16 §11 (freeze-check amendment, 2026-10-19)
amended it** into a within-strata permutation test on the coefficient: the placebo holds iff at most 3 of 200 permuted
coefficients (1.5%) reach the observed coefficient (a permuted coefficient that cannot be computed counts as reaching
it), with Q's ≥ 50% informativeness rule kept; and CB16's calibration placebo is judged on p < 0.01 alone. CB17 adopts
CB16 §11 as amended and adds an estimator-based guard (ruling 1 keeps both):
1. **Composition guard (binding; two parts, both must hold).**
   (a) *Composition-conditional estimator.* Re-estimate the family's statistic with fixed effects for (unit × stratum),
   so the label is compared only within strata. It must keep the sign and at least half of the primary point estimate,
   with one-sided p < 0.05 (max over ways).
   (b) *Within-strata permutation test (CB16 §11 item 2's rule).* The label (or continuous state) is permuted within
   (unit × stratum) cells, 200 draws (seed per family), the same estimator and sign as the primary; the guard **holds
   iff at most 3 of the 200 permuted coefficients reach the observed coefficient**; a permuted coefficient that cannot be
   computed counts as reaching it.
   **Informativeness** (both parts): at least 50% of the units in the denominator must lie in informative (unit ×
   stratum) cells; otherwise the guard is "uninformative" and the test cannot advance (counted with its p). Definitions,
   fixed in part `pre`: *binary labels (A, B1):* numerator = units in cells holding both labels, denominator = all units
   of the test; *continuous state (B2):* numerator = units in cells with ≥ 2 units and `x` not constant in the cell,
   denominator = all B2 units; *C's three classes:* the tested contrast is transfer versus mint-heavy, so numerator =
   transfer and mint-heavy units in cells holding at least one transfer and one mint-heavy unit, denominator = all
   transfer and mint-heavy units (merge-heavy units stay in the estimator and are reported, not in the share).
   *Alternative guarded:* the contrast comes from the strata's composition (spread, price, hour, activity, size) rather
   than the label.
2. **Calibration placebo (binding).** The label (or state) is **circularly shifted within the unit** (A: market × d;
   B: token; C: event), with units ordered by decision time and the offset drawn uniformly from {1, …, n − 1} (n the
   unit's count; units with n < 2 are left as they are), 200 draws (seed per family). The circular shift keeps the
   label's own autocorrelation (one-at-a-time shuffles destroy it; finding 3). **Each draw is judged on one-sided p <
   0.01 alone** (no floor; CB16 §11 item 1's rule), and the advance rate must be ≤ 1.5% (at most 3 of 200).
   *Alternative guarded:* within-unit dependence makes the clustered p anti-conservative.

**Strata ladders and level selection (fixed in part `pre`; finding 2).** The draft strata (level 0) give 72-144 cells per
unit against about 12 units per unit for A, so the 50% rule would fail by construction. Each family declares a ladder of
coarser levels, defined now, without data:

| Family | Level 0 (draft) | Level 1 | Level 2 (coarsest) |
|---|---|---|---|
| A (per market × d) | `P` band (3) × size band (3) × UTC 6 h band (4) × spread band (4) = 144 | `P` band (3) × spread {≤ 2c, > 2c} = 6 | `P` band (3) |
| B1 (per token) | UTC 6 h band × spread band (4) × activity tercile × reward programme = 96 | activity tercile × UTC 12 h band {00-12, 12-24} × spread {≤ 2c, > 2c} = 12 | activity tercile (3) |
| B2 (per token) | UTC 6 h band × spread band (4) × activity tercile × imbalance tercile = 144 | activity tercile × imbalance tercile = 9 | imbalance tercile (3) |
| C (per event) | UTC 6 h band × `|Δm_int|` band (3) × trailing `dV` tercile × moving members {1, ≥ 2} = 72 | `|Δm_int|` band (3) × trailing `dV` 2-band (below / above the event's trailing median) = 6 | `|Δm_int|` {0.5-1c, > 1c} = 2 |

**Selection rule.** q0400 (A, on the population of the branch it selects), q0401 (B1, B2) and q0402 (C) compute the
informativeness share at every level on worn data (features only: labels, states and strata; no mark). The **finest
level whose worn-data share is ≥ 60%** is written into the family's part (the 10-point margin over the window's 50% rule
covers window differences; 14 window days accumulate more within-unit variety than 4 worn days). If no level reaches
60%, level 2 is written and the window's 50% rule binds as declared. The selected level never changes after the part
commit; q0408 reports the window share at the selected level. Coarsening is outcome-blind and is not a loosening of
any threshold: the 50% rule, the half-effect rule and the 3-of-200 rule are unchanged.

This tightens rather than relaxes: the composition guard is an estimator that must keep half the effect **and** a
permutation test with CB16's amended rule, not a placebo that can be passed by default.

Also binding for every advance, as CB16 §2.6: (i) §2.1 cost robustness; (ii) p and the floor hold without the top 5
clusters of each way; (iii) leave-one-day-out (p < 0.05 and the sign); (iv) unavailable units excluded and counted,
never imputed; available share < 60% of eligible → "not testable (availability)". Seeds 17101-17140.

### 2.7 Pre-freeze censuses and window gates (counts only)

Outcome guards come first, with field-restricted accessors; a unit test asserts no census path receives a mark quote,
a capture or sweep received after a unit's decision time, an outcome, or a later price used as a target.
- **Pre-freeze (worn `[2026-10-12, 2026-10-16)`; q0400-q0403):** counts and **planning SEs** on the declared pre-outcome
  proxies (§3), SEs only. They inform the challenger; **they can never change a floor, window, threshold or gate**,
  with three declared exceptions, each a feature-only rule fixed in part `pre` before q0400 runs: q0400's side-agreement
  measurement selects A's fill source, or withdraws A uncounted under branch T (§CB17-A); q0400-q0402 select each
  family's strata level (§2.6); q0401 fixes B's global activity cut points (§CB17-B).
- **Window gates (q0408):** per family (§3). Power gates run each test's own estimator and ways on its pre-outcome proxy
  and write **only the clustered SE** (max over ways); no proxy point estimate is written (unit-tested).
- `MDE = (z_0.99 + z_0.80) × 1.2 × SE = 3.80 × SE`. **Power rule (every Stage-1 test): MDE > 1.0c (2 × floor) → "not
  run (power)", counted.**

### 2.8 Compute, network, disk and stop rules

- **Host.** 1 OCPU; about 3.2-3.4 GB `MemAvailable` at drafting. Queue rules as CB16 §2.8: one job per lane, nice 19,
  `MemAvailable ≥ mem_mb + 1200`, address cap 2 × `mem_mb`, the 02:45-05:30 UTC blackout for `mem_mb ≥ 500`; frame and
  census jobs yield to the collector pass (`:31-:55` of even hours). Readers stream one capture, sweep or day file at a
  time (P2/P3 measured 65-183 MB per day of data).
- **`mem_mb`:** q0400-q0403 500-800; q0406 1000 (two arm-0 frames, about 1.4 M B rows and about 80 k C rows, float32);
  q0407 800; q0409 and q0411 1200 (token-FE regressions on about 1.4 M rows plus permutation draws); others ≤ 500. **Every
  job is ≤ 1.2 GB**, under the 1.5 GB guidance; q0409 and q0411 are heavy under the memory rule and run alone.
- **Network:** none. **Disk guard:** as CB16 (`--disk-cap-gb`, `--data-dumps-cap-gb 40`, exit 75); CB17 output caps
  total **≤ 0.3 GB**. CB17 never deletes or moves host data. Archived sources are restored byte for byte, hash-checked.
- **Monitor storage cap (disclosed risk; ruling 7).** `live_trades/` held 372 MB on 2026-10-19 and grows about 65 MB a
  day (`scores-*` files are 76% of it) against the monitor's 3 GB total stop cap (`TOTAL_CAP_BYTES` in
  `live_trade_monitor.py`, measured as `du` of the whole `live_trades/` root): the cap binds **about 2026-11-25 to
  11-29**, two to six days after REP_8's last needed row (2026-11-23T08:00Z) and inside CB16's REP_A (to about
  11-30). Missing days are "unavailable (monitor stopped)", counted, never back-filled. CB17 changes no collector
  setting; **the orchestrator decides before `S_8`** (§10, ruling 7 response: raise the cap as an ops change; REP_8 is
  not shortened).
- **Stop rules.** 3 CPU-hours per family; a job failing twice for the same non-transient reason stops and is recorded.
  A null is "not detected at MDE x". **No re-screen of a failed CB17 test** with altered windows, arms, bins, labels,
  strata, horizons or populations, on any data.

### 2.9 Funnel and Stage P

Screen (SCREEN_8) → gates, composition checks, placebos, robustness → replication and economic check (REP_8) → a
separate prospective confirmation (Stage P) → economic validation at recorded prices with fees, spread and depth.
- **Stage P-A** (only if A2 passes): a market-state rule (CH145's closing share), not a fill-level selection, read live
  at the print with a CLOB `/book` read; passive and taker exits reported.
- **Stage P-B** (only if B1-econ or B2-econ passes): a paper maker that quotes only into fresh books (B1) or pulls the
  side the mass left (B2), with fills read from the book at print time; queue position unknown and disclosed.
- **Stage P-C** (only if C1-econ passes): a maker that widens in the pass after a transfer-heavy interval.
- **A protection rule is a route only if the protected maker's own net is positive**; every maker cell so far has been
  negative (`EXECUTION_COSTS.md`; ECON-95: 0 of 95 cells).

---

## 3. Tests

### CB17-A: Open versus close (CH144)

**Question.** Within a market and a YES-terms direction, is the maker's 2-4 h mark-out worse on large taker
transactions that open a position (the taker bought the traded token) than on those that close one (the taker sold it)?

**Mechanism.** On Polymarket a taker can only sell a token it holds, so a taker sell is a close and a taker buy an
open. Pan and Poteshman (2006) found that newly opened option positions carry the information and closes do not;
here the venue's structure supplies the open/close split for free. **Who pays:** the maker who treats both alike.
**Against it:** a NO holder can exit by buying YES and merging (labelled open; attenuates); closes cluster near 0.9+
as winners cash out (price band), which the within-cell design and the strata absorb; opens and closes may differ in
size and hour; and within a cell the label is the traded token, so any token-specific microstructure (a NO-book
liquidity difference) is confounded with it (the composition-conditional strata include the capture spread band, and
"each direction" is a binding robustness).

**Fill source and the branch rule (fixed in part `pre` before q0400 runs; outcome-blind; decided by q0400 before any
part A commit; finding 7 and ruling 2).**
- **Branch T (default).** CB13-T's frozen touch-consistent rule by pin: a transaction is a unit iff consistent with a
  latest complete capture touch of age ≤ 60 min, two-sided, spread ≤ 10c, touch mid in [0.03, 0.97], capture
  `end_date ≥ τ + 3 h`. `d` and `P` as CB13-T. The taker bought the traded token iff (`outcome_index = 0` and `d = −1`)
  or (`outcome_index = 1` and `d = +1`). **Under branch T, family A is withdrawn uncounted before its part commit**
  (planning MDE 1.1-1.7c against the 1.0c power gate; CB15-L precedent; §2.5). A's definitions here stay on record.
- **Branch S.** Taken **iff** q0400 shows, on the worn CB13-T SCREEN non-sports fills that resolve to one token and one
  transaction (P1: 971), that the Data API `side` (taker side) agrees with the touch-derived taker side (i) in at least
  97% of fills overall with a Wilson 95% lower bound ≥ 0.95 and n ≥ 800 (0.97 is CH79's own "near-truth" band), **and
  (ii) in at least 97% within every one of the following cells that holds n ≥ 100 fills: touch-age band {0-20 min,
  20-60 min}; `P` band {[0.03, 0.20), [0.20, 0.80], (0.80, 0.97]}; LABELLER class** (cells with n < 100 are reported
  only). Then every non-sports transaction with a single token and a single `side` is a unit: `side = BUY` → open;
  YES-terms taker direction from `side` and the token; `d` its negative; `P` the maker-adverse price within the
  transaction; touch eligibility as branch T except touch age ≤ 135 min (the touch is used for eligibility and the
  spread-free mark only, not for signing). The touch-consistent subset is a **binding robustness** (sign kept).
- **GAS (signing gate, binding, branch S only; q0408).** On SCREEN_8's touch-consistent subset (CB13-T's rule by pin),
  the same agreement rule as (i) and (ii) must hold (`side` and the touch-derived side are both features; no mark is
  read); else A1 "not testable (signing)", counted.
- If q0400 has not run when the other parts are committed, branch T binds (A withdrawn). The branch is written into the
  ledger and, under S, into part A; it cannot change afterwards. CB9-S's later S0 verdict is reported next to every A
  line and changes nothing.

**Population (q0407; frozen in part A).** Fill-source units with `τ` in SCREEN_8, minus the election-night exclusion and
key drops; binary markets; LABELLER class not SPORTS-FEED; single token; `P ∈ [0.03, 0.97]`. Mixed-token,
ambiguous-transaction, inside, inconsistent and one-sided units are excluded and counted **by label** where a label
exists (so label-dependent exclusion is visible). The statistic uses (market, `d`) cells holding both labels; other
cells are counted and reported.

**Mark-out.** `M_h = d·(mid_h − P)` cents per share (CB13-T), "2-4 h" primary, "6-8 h" robustness. Decomposition
reported for every A line: spread-free `d·(mid_h − mid_0)` plus realised half-spread `d·(mid_0 − P)`.

**A1.** `β_A = −(coefficient on open)` in an OLS of `M_2-4h` on `open` with **(market × d) fixed effects**, one unit per
transaction. One-sided > 0, floor +0.5c; p = max over the event, path key × 6 h block, 6 h block ways; leave-one-day-out.
- **Composition guard (binding; §2.6, both parts).** Strata at the level selected by q0400 from the ladder: level 0 `P`
  band {[0.03, 0.20), [0.20, 0.80], (0.80, 0.97]} × size band {< $2.5k, $2.5-10k, ≥ $10k} × UTC 6 h band × capture
  spread band {≤ 1c, 1-2c, 2-5c, > 5c}; level 1 `P` band × spread {≤ 2c, > 2c}; level 2 `P` band; seed 17101.
- **Calibration placebo (binding; §2.6).** Circular shift of `open` within (market × d), units ordered by `τ`; 200
  draws, seed 17102; each draw judged on p < 0.01 alone; advance rate ≤ 1.5%.
- **d-balanced estimate (binding; ruling 3).** `β_A^bal = (β_A,d=+1 + β_A,d=−1) / 2`, the equal-weight average of the
  coefficients estimated separately on the d = +1 and d = −1 cells; it must keep the sign of `β_A` (and is reported with
  its CR1 p). *Guards:* one direction (for example YES bid up near resolution) carrying the whole contrast.
- **Pre-fill placebo (binding).** `M` replaced by the pre-fill move (capture before the touch capture → touch capture,
  signed by `d`); must not pass p < 0.01. *Guards:* closes and opens arrive in different trends.
- **Spread-free mark (binding; CB16 round 1 item 1).** The estimator on `d·(mid_h − mid_0)` keeps the sign and at least
  half of `β_A`, one-sided p < 0.05.
- **Attribution (binding for the label "open/close").** Market × d FE OLS with `open` plus `P` band, size band, touch
  age band, time-to-end band, reward programme present, LABELLER class, log liquidity, 6 h block, CB16's grain `g`
  (where the tick is 0.001) and silence `x` (where standardisable), each with a missing indicator. `open` keeps at least
  half of `β_A`, else "composition, not open/close".
- **Robustness (binding; each keeps the sign):** the 6-8 h mark; touch age ≤ 20 min; the adverse-touch mark with
  wide-mark and closed-before-mark units at their adverse touch or worst case; excluding ≥ $10k; each `d`; `P ∈ [0.10,
  0.90]`; market-weighted means; top-5 drops; under branch S, the touch-consistent subset.
- **Reported (uncounted):** `β_A` by LABELLER class and in the sports arm; label shares by class and price band; the
  exclusion-by-label table; the taker fade of large closes (§2.1).

**Gates.** **GAS (signing; above).** **GA:** ≥ 1,000 units in both-label (market, d) cells, in ≥ 100 such cells and ≥
60 events; else "not testable (population)". **GAP (power):** A1's estimator and ways on the pre-fill proxy, SEs only; MDE > 1.0c → "not run
(power)". **GAI** (cadence; as CB16 GAI, measured from `P`): with ≥ 200 pairs, sign agreement ≤ 70% → "not testable
(cadence)"; with < 200, every A line carries "cadence informativeness unverified".

**Power (planning; GAP decides).** σ_eff per unit ≈ 4.9c, implied by CB13-T's GTP (SE 0.45c at 163 vs 427 fills).
- *Branch T:* P1 gives 364 both-cell fills in four days; cells accumulate over 14 days, so about 1,200-1,800 both-cell
  fills (30% close) in about 60-100 events: `SE ≈ 0.3-0.45c`, **MDE ≈ 1.1-1.7c > 1.0c gate → A is withdrawn
  uncounted under branch T** (§2.5).
- *Branch S:* CB13-T's census counts 7,045 non-sports transactions in four days (37,106 minus 30,061 sports-fee); after
  eligibility about 4,000-4,500, so about 14,000-16,000 in 14 days, of which perhaps 50-60% in both-label cells: `SE ≈
  0.16-0.24c`, **MDE ≈ 0.6-0.9c**. **Power at a true effect equal to the 0.5c floor is about 40%** (finding 8;
  disclosed): a "not detected" verdict at the floor is weak evidence of absence.

**Stage 2 (q0410, q0411; triggered by A1).** REP_8 with SCREEN_8 events dropped (binding even if thinned). Minimum: the
GA counts on REP_8, else "not run (power)", counted.
- **A1-rep:** the Stage-1 statistic and every binding check.
- **A2 (economic upper bound):** the CB13-T3 round trip on close-labelled REP_8 fills (§2.1), one-sided > 0, floor
  +0.5c, +0.5c exit robustness; the worst case keeps p < 0.01. Needs the pooled SCREEN + REP GAI PASS. **A pass
  justifies only a Stage-P registration of a market-state rule; it is not a route.**

### CB17-B: The book's own clocks (CH146 book age, CH147 breathing book)

**Shared frame (q0406).** Units are (token, pass) for outcome-0 tokens in the sweep universe (binary markets, end
unknown or > 3 h away), in **arm-0 events**, non-sports by the sidecar rule, with decision time in SCREEN_8. Common
eligibility: two-sided books at the decision sweep and the mark sweep; decision spread ≤ 10c; decision mid in [0.03,
0.97]; sidecar `end_date ≥ t + 4 h`. Mark availability (statuses, not eligibility; O9 ruling 2026-10-20): the mark sweep
exists (else "no mark"); mark spread ≤ 10c (else "wide mark"); `tick_size` equal at decision and mark (else "tick
change", the same treatment as "wide mark": counted in the availability denominator, never in the primary sample, and in
the binding worst case, which takes the capture mark first, else the adverse bound). Placebos, the composition guard,
attribution, the census and the 6 h / capture-mark robustness keep exactly their previous index sets (units without a
tick change). Exclusions are counted
by state bin.
- **No-mark handling (finding 4).** Eligibility uses the decision sweep and earlier rows only; a token absent from the
  mark pass, or one-sided there, is "no mark" (an availability outcome, not an eligibility rule). q0401 reports the
  next-pass no-mark share by age bin on worn data and q0408 by age bin (B1) and by `x` sign and `|x|` quintile (B2) on
  SCREEN_8; no mark value is read for either. **Binding worst-case bound:** each test is re-estimated with no-mark and
  wide-mark units filled first by the capture mark (CB13 rule, first complete capture with last-page `received_utc ≥
  t + 2 h`, usable iff ≤ `t + 4 h`) and, where none exists, at the bound adverse to the hypothesis: B1 old units `L = 0`
  (the minimum, since `L ≥ 0`) and fresh units the 95th percentile of available fresh-bin `L`; B2 units with `x > 0`
  get the 5th percentile and `x < 0` the 95th percentile of available `Δm` (`x = 0` units get 0). The estimate must
  keep the sign.
- **Activity (finding 6).** A unit's activity is the pre-decision `|Δm|` from the previous pass's first sweep to the
  decision sweep. Its tercile cut points are **global and frozen in part B from q0401's worn non-sports units**, never
  recomputed on SCREEN_8 or REP_8 (the window terciles would pool later units' pre-decision moves, which overlap earlier
  units' targets).

#### B1: book age (CH146)

**Question.** Is a resting touch that nobody has updated for at least ten minutes crossed by the next 2 h of price
movement more than a touch updated within the last minute, in the same token?

**Mechanism.** A limit order is a free option (Copeland and Galai 1983); its value to a picker-off grows with the time
since its writer last looked (Foucault 1999). The CLOB's `book_timestamp` says how long the displayed book has stood.
**Against it:** old books occur when nobody trades or re-quotes, i.e. in quiet tokens and hours, which carry *less*
subsequent movement; "fresh" partly means "bot heartbeat". The within-token design, the activity strata and the
attribution regression address these; the composition bias runs against the hypothesis.

**State.** First sweep of the pass: `old` iff `a ≥ 600 s`; `fresh` iff `a < 60 s`; `60 s ≤ a < 600 s` is reported only.

**Target: the 2 h excursion beyond the touch** (renamed from "pick-off loss"; finding 8 and ruling 4). With `b0, a0`
the decision touch and `m_h` the 2 h mark-sweep mid: `L = 100·[max(0, m_h − a0) + max(0, b0 − m_h)]` cents. It is the
adverse movement a paper quote resting at each side of the touch would face if filled only when the mark crosses it; the
unfilled quote and any spread earned on uninformed fills are not observable. **B1 is labelled "adverse movement only";
it is not a maker net and not a maker loss. B1-econ is the only maker-relevant line of B1.**

**B1.** `β_B1` = coefficient on `old` in an OLS of `L` on `old` with **token FE**, on units in the old or fresh bins.
One-sided > 0, floor +0.5c; ways event, path key × 6 h block, 6 h block, UTC hour; leave-one-day-out.
- **Composition guard (binding; §2.6, both parts).** Strata at the level selected by q0401: level 0 UTC 6 h band ×
  decision spread band {≤ 1c, 1-2c, 2-5c, > 5c} × activity tercile (global frozen cut points, above) × reward programme
  present; level 1 activity tercile × UTC 12 h band × spread {≤ 2c, > 2c}; level 2 activity tercile; seed 17111.
- **Calibration placebo (binding; §2.6).** Circular shift of old/fresh within token over its passes in time order; 200
  draws, seed 17112; each draw judged on p < 0.01 alone; advance rate ≤ 1.5%.
- **Pre-period placebo (binding).** `L_pre` from the touch two passes earlier and the mid one pass earlier, regressed
  on today's `old`; must not pass p < 0.01 in the hypothesised direction. *Guards:* persistent volatility states that
  coincide with old books.
- **Attribution (binding for the label "book age").** Token-FE OLS with `old` plus spread band, activity, log
  liquidity, `volume24hr` band, reward programme present, `n_*_levels` band, UTC 6 h band, decision mid band, "hash
  changed since the previous pass", and the touch quotes' grain (sub-cent or not). `old` keeps at least half of `β_B1`.
- **Robustness (binding; each keeps the sign):** the no-mark worst-case bound (above); the capture mark (CB13 rule)
  instead of the sweep mark; the old cut at 300 s and at 1,800 s (fresh fixed); excluding `a > 3,600 s`; the ask-crossing and bid-crossing components separately;
  the relative loss `L / (a0 − b0)`; decision mid in [0.10, 0.90]; the 6 h mark; top-5 drops; leave-one-day-out.
- **Reported (uncounted):** the full age-bin table by class, hour and liquidity; the cross-tab of age by touch grain and
  touch-size roundness (CH148's inputs); the sports arm.

**Gates.** **GBT (stamp semantics):** on SCREEN_8 intra-pass pairs, hash unchanged ⇒ stamp unchanged in ≥ 99%, and
hash changed ⇒ stamp changed in ≥ 95%; else B1 "not testable (field semantics)" (P2: 100% and 100% on worn data).
**GBA (population):** old and fresh each ≥ 5% of eligible units; ≥ 1,000 arm-0 tokens holding both bins; ≥ 300 events
among them; else "not testable (population)". **GB1P (power):** B1's estimator on `L_pre` (§above), SEs only; MDE >
1.0c → "not run (power)".

**Power (planning).** P2: about 17,000 non-sports tokens per sweep, 12 passes a day, 81% in the old or fresh bins, but
only 7% of tokens mix both bins in one day (more over 14 days). Arm 0 over 14 days: roughly 100,000-300,000 units in
mixing tokens across several thousand events. With SD(L) ≈ 1-3c and heavy within-token dependence, `SE ≈ 0.02-0.05c`,
**MDE ≈ 0.1-0.2c**. The floor binds, not power.

**Stage 2 (triggered by B1).** Arm-1 events in REP_8, same frozen rules (the same global activity cut points frozen
in part B; nothing is recomputed on REP_8).
- **B1-rep:** the Stage-1 statistic and every binding check.
- **B1-econ (fill-level protection value).** REP_8 fills from the fill source in arm-1 non-sports markets whose token
  had a sweep with receipt in `[τ − 30 min, τ)`: within-market difference of the CB13-T3 round-trip net between fills
  into old (`a ≥ 600 s` at that sweep) and fresh (`a < 60 s`) books; primary one-sided < 0, floor ≤ −0.5c; second
  component the old-book fills' net ≤ −1.0c; p = the max. Minimum ≥ 300 fills per bin in ≥ 60 events, else "not run
  (power)", counted. Under branch T this minimum is very unlikely to be met (planning ~130 fills per bin). *Hurdles and
  the q0403 context: §11.4.*

#### B2: the sticky touch and the breathing book (CH147)

**Question.** When a token's touch is identical across a pass's two sweeps (about two minutes apart), does the shift of
depth 1-5c beneath it predict the signed mid change over the next 2 h?

**Mechanism.** Bots re-centre their ladders beneath the touch when their fair value moves; a stale touch order does
not follow. Mass leaving one side beneath an unchanged touch marks the side about to be lifted. **Against it:** trades
between the sweeps change depth without re-quoting; heartbeat resizing; bots may simply react to past moves (then the
forward effect is momentum).

**State.** For units with identical `best_bid` and `best_ask` in both sweeps of the pass:
`s = [(A5 − A1) − (B5 − B1)]_2 − [(A5 − A1) − (B5 − B1)]_1` (shares; `A5 = depth_ask_5c` etc.), scaled by the first
sweep's total 5c depth `D1 = depth_bid_5c + depth_ask_5c`: `x = −s / D1`, clipped to [−1, 1] (positive `x` predicts an up
move). Units with `s = 0` stay in (`x = 0`). `SD_x` is the pooled SD over SCREEN_8 units, a feature, written to the
SCREEN_8 result file and **frozen for REP_8**.

**Target.** `Δm = 100·(m_h − m_0)` cents, `m_0` the decision mid (identical across the two sweeps), `m_h` the 2 h
mark-sweep mid.

**B2.** `β_B2` = coefficient on `x / SD_x` in an OLS of `Δm` with **token FE**. One-sided > 0, floor +0.5c per SD; ways
and leave-one-day-out as B1.
- **Composition guard (binding; §2.6, both parts).** Strata at the level selected by q0401: level 0 UTC 6 h band ×
  spread band × activity tercile × E003 imbalance-level tercile `(B5 − A5)/D1` at sweep 2; level 1 activity tercile ×
  imbalance tercile; level 2 imbalance tercile. The imbalance tercile cut points are global, frozen in part B from
  q0401's worn units (as activity); seed 17121.
- **Calibration placebo (binding; §2.6).** Circular shift of `x` within token over its passes in time order; 200 draws,
  seed 17122; each draw judged on p < 0.01 alone; advance rate ≤ 1.5%.
- **Pre-sweep placebo (binding; kept binding by ruling 5).** `Δm_pre` (previous pass's first-sweep mid → `m_0`) on `x`:
  must not pass p < 0.01 in the hypothesised direction. *Guards:* re-quoting follows a move already under way and
  momentum does the rest. If bots react to past moves, B2 fails here by design: a state explained by the past move is
  not a forward signal.
- **Attribution (binding for the label "breathing book").** Token-FE OLS with `x` plus `Δm_pre`, the imbalance level,
  spread band, `n_*_levels` change, touch-size change, activity and UTC 6 h band; `x` keeps at least half of `β_B2`.
- **Robustness (binding; each keeps the sign):** the no-mark worst-case bound (shared frame, above); units with `s ≠ 0`
  only; units with no monitor print in the market
  between the two sweeps; units with unchanged touch sizes; the capture mark; the 6 h mark; top-5 drops;
  leave-one-day-out. **Concentration label:** if the top 5 events carry > 30% of `Σ x²`, every B2 line carries
  "concentrated".
- **Reported:** the slope on the `n_*_levels` change as an alternative state; the taker follow at the decision ask/bid
  (§2.1).

**Gates.** **GBS (population):** among eligible touch-unchanged pairs, `s ≠ 0` in ≥ 20% (round 8's kill; P2: 22-25% on
worn data); ≥ 50,000 units with `s ≠ 0` in ≥ 300 events; else "not testable (population)". **GB2P (power):** B2's
estimator on `Δm_pre`, SEs only; MDE > 1.0c per SD → "not run (power)".

**Power (planning).** P2: about 15,000 touch-unchanged non-sports pairs per pass, a quarter with `s ≠ 0`. Arm 0 over 14
days: about 1.2 M units, about 300,000 with `s ≠ 0`. With SD(Δm) ≈ 2c and event clustering, `SE ≈ 0.01-0.03c`, **MDE
≈ 0.05-0.1c per SD**. The floor binds.

**Stage 2 (triggered by B2).** Arm-1 REP_8 units; `SD_x` frozen from SCREEN_8.
- **B2-rep:** the Stage-1 statistic and every binding check.
- **B2-econ.** REP_8 fills from the fill source in arm-1 non-sports markets with `τ ∈ (t, t + 2 h]` after a pass where
  the token had `|x| ≥ SD_x`: "abandoned-side" fills are those where the maker sold YES when `x > 0` or bought YES when
  `x < 0`. Within-market difference of the round-trip net (abandoned minus the market's other REP_8 fills), one-sided
  < 0, floor ≤ −0.5c; second component the abandoned-side net ≤ −1.0c; p = the max. Minimum ≥ 300 abandoned-side fills
  in ≥ 60 events, else "not run (power)". *Hurdles and the q0403 context: §11.4.*

### CB17-C: Mint share (CH150)

**Question.** Within an event, does a member's 2 h move continue more after an interval whose open-interest change was
small relative to its volume (transfer-heavy) than after one where open interest grew fast relative to volume
(mint-heavy)?

**Mechanism.** On a binary CLOB with mint and merge, a buy matched with a complementary buy creates a share pair (OI
up), a sell matched with a complementary sell destroys one (OI down), and a buy matched with a sell transfers one (OI
flat). In futures markets OI changes separate hedging from speculative demand (Bessembinder and Seguin 1993) and
predict returns (Hong and Yogo 2012). A transfer-heavy move is one informed side meeting existing holders (continues);
a mint-heavy move is two new opinions (no net information). **Against it:** OI is in shares and volume in dollars (only
within-event ranks are meaningful); neg-risk conversions move OI without trades; OI may lag volume; 2 h cadence.

**Units (q0406). Eligibility uses captures `k − 1` and `k` only (finding 1).** (event, interval `k`) for non-sports
**arm-0** events in SCREEN_8: captures `k − 1`, `k` consecutive and complete (§2.2); `event_open_interest` and
`event_volume` present in both; `dV = vol_k − vol_{k−1} > 0`; no member with `closed` true in captures `k − 1` or `k`,
and no member with `end_date ≤` (capture `k`'s time + 3 h) ("member closing", excluded and counted; `end_date` is known
at `k`); at least one **qualifying member**: eligible mids (two-sided, spread ≤ 10c, mid in [0.03, 0.97]) at `k − 1` and
`k`, and `|Δm_int| = |m_k − m_{k−1}| ≥ 0.5c`. Nothing about capture `k + 1` enters eligibility.

**State.** `r = (OI_k − OI_{k−1}) / dV`. **Classes by trailing terciles (primary; finding 6):** the cut points are the
event's terciles of `r` over its own traded intervals with decision time in `[lookback floor, k)` (earlier SCREEN_8
intervals; for REP_8, the arm-1 event's earlier intervals inside q0410's read window `[S_8 + 7 d, k)`, read as
features), at least 6 prior (fewer → "thin history", excluded and counted): **mint-heavy** = above the upper cut,
**transfer** = between, **merge-heavy** = below the lower cut. `r_k` itself, `r_{k+1}` and later intervals never enter
the cut points. The event's trailing `dV` tercile (a stratum) uses the same prior intervals.

**Target and its availability.** For each qualifying member `j`: `C_j = sign(Δm_int,j) × 100 × (m_{j,k+1} − m_{j,k})`
cents, with `m_{j,k+1}` the mid at capture `k + 1` (consecutive, gap 100-140 min). The mark is **available** iff capture
`k + 1` exists in that gap and member `j`'s row there is two-sided with spread ≤ 10c, mid in [0.03, 0.97] and
`closed` false. Otherwise member `j` is **"unavailable (mark)"**, counted by class and by reason (capture missing,
member closed, one-sided, wide, extreme mid); it is never an exclusion rule. The unit value is the mean over qualifying
members with an available mark; a unit with none is "unavailable (mark)", counted by class; the 60% availability rule
applies. **Binding worst-case robustness:** every unavailable member is filled at the bound adverse to the hypothesis
(transfer units `min(p5 of available member C, touch-C)`; mint-heavy and merge-heavy units `max(p95, touch-C)`, where
touch-C is the continuation at the one-sided `k + 1` touch adverse to the hypothesis: adverse to continuation for
transfer, favourable to continuation for mint and merge; O11 ruling 2026-10-20), and the
estimate must keep the sign.

**C1.** `β_C` = coefficient on `transfer` in an OLS of `C` on `transfer` and `merge` indicators (mint-heavy baseline)
with **event FE**. One-sided > 0, floor +0.5c; ways event, path key × 6 h block, 6 h block, UTC hour; leave-one-day-out.
- **Composition guard (binding; §2.6, both parts; three-class informativeness rule).** Strata at the level selected by
  q0402: level 0 UTC 6 h band × `|Δm_int|` band {0.5-1c, 1-3c, > 3c} × the event's trailing `dV` tercile × moving
  members {1, ≥ 2}; level 1 `|Δm_int|` band × trailing `dV` 2-band; level 2 `|Δm_int|` {0.5-1c, > 1c}; seed 17131.
- **Calibration placebo (binding; §2.6).** Circular shift of the class within event over its intervals in time order;
  200 draws, seed 17132; each draw judged on p < 0.01 alone; advance rate ≤ 1.5%.
- **Pre-interval placebo (binding).** `C_pre = sign(Δm_int) × (m_{k−1} − m_{k−2})` on the classes; must not pass p < 0.01
  in the hypothesised direction. *Guards:* transfer intervals occurring inside trends.
- **Attribution (binding for the label "mint share").** Event-FE OLS with the classes plus `C_pre`, `|Δm_int|` band,
  `dV` tercile, mean member spread, log event liquidity, moving members, UTC 6 h band; `transfer` keeps at least half
  of `β_C`.
- **Robustness (binding; each keeps the sign):** the unavailable-mark worst case (above); the OI-lag variant `r_lag =
  (OI_k − OI_{k−1}) / (vol_{k−1} − vol_{k−2})` (both known at `k`); whole-window terciles **leaving intervals `k` and
  `k + 1` out** (features only; the former primary, now a robustness); single-market events alone; non-neg-risk events
  alone; the 4 h continuation (`k + 2`); excluding the top 1% of `dV`; top-5 drops; leave-one-day-out.
- **Reported:** merge-heavy minus mint-heavy; the sign-only class (`dOI = 0` vs `> 0`); neg-risk events alone; the
  taker follow of transfer-interval moves (§2.1).

**Gates.** **GCU (field liveness):** OI changed in ≥ 70% of traded non-sports event-intervals in SCREEN_8 (P3: 87% on
worn data); else "not testable (field)". **GC (population):** ≥ 600 arm-0 events with at least one unit that has ≥ 6
prior traded intervals, and ≥ 10,000 such units; else "not testable (population)". **GCP (power):** C1's estimator on `C_pre`, SEs only; MDE > 1.0c → "not run
(power)".

**Power (planning).** P3: about 1,500 traded non-sports event-intervals per 2 h, 61% with a member move ≥ 0.5c; arm 0
over 14 days ≈ 75,000 units in perhaps 1,500-2,500 events; trailing terciles drop each event's first six traded
intervals (perhaps 10-20% of units; q0402 counts it on worn data). With SD(C) ≈ 2-3c and design effect about 3,
`SE(β_C) ≈ 0.03-0.06c`, **MDE ≈ 0.15-0.25c**. The floor binds.

**Stage 2 (triggered by C1).** Arm-1 REP_8 units, same frozen rules.
- **C1-rep:** the Stage-1 statistic and every binding check.
- **C1-econ.** REP_8 fills from the fill source in arm-1 events with `τ` in (capture `k`, capture `k + 1`] after a
  classified interval: within-event difference of the round-trip net (fills after transfer intervals minus fills
  after mint-heavy intervals), one-sided < 0, floor ≤ −0.5c; second component the after-transfer net ≤ −1.0c; p = the
  max. Minimum ≥ 300 fills per class in ≥ 60 events, else "not run (power)". *Hurdles and the q0403 context: §11.4.*

### CB17-E: First-day prints (CH154). Census only, no counted test

**Why no counted test.** P1: under touch signing, 30 non-sports first-day fills in four days and 7 markets with both
first-day and later fills; about 100-150 first-day fills and 25-40 both-period markets in 14 days. The within-market
contrast round 8 proposed would have an MDE of several cents against a 0.5c floor. Under branch S the count rises
(round 8 saw 778 enriched first-day prints a day, 59% sports), but the both-period market count, not prints, sets the
power, and first-day spreads are wide, so the mechanical half-spread (CB16 round 1 item 1) is largest exactly here.

**Census (q0408, on SCREEN_8 features; q0400 on worn data).** First-day = market age at `τ` under 24 h, from the
sidecar `created_at` of the latest capture before `τ` or, for markets not yet captured, the first capture after `τ`
(a static attribute). Counts: first-day transactions by fill source, class, sports and hour; markets and events with
both first-day and later (1-7 d) transactions; the share unsignable for lack of a touch; a feature-proxy SE of the
within-market contrast on the pre-fill proxy (SE only).

**Re-entry rule (declared).** A later batch may register a counted CH154 test on a **fresh** window only if the SCREEN_8
census shows ≥ 400 non-sports first-day transactions in ≥ 150 markets that also print on days 2-7, and a proxy MDE ≤
1.0c, and the design makes the spread-free mark binding. Otherwise CH154 is recorded as "not testable at the floor with
host data". **O1 ruling (2026-10-20):** the counts bind on the signable (touch-consistent) population a CH154 test would
use, as does the MDE; the counts on all non-sports transactions are reported only.

### CB17-SM: smoke and audits

- **q0404 smoke** (`cpu`, no network). PASS needs: the part hashes and the pinned CB13 and CB16 function sha256s;
  refusals on fixtures (rows before the lookback floor outside the census paths, **including the q0406/q0407/q0410
  lookback reads at `S_8 − 2 h`, `S_8 − 3 h` and `S_8 − 6 h` when `S_8` = the floor, with the dependent unit labelled
  "unavailable (lookback floor)" and counted** (finding 5); J4-R and CB13-T HOLDOUT rows; census-path rows at or after
  2026-10-16T00:00Z; REP_8 rows before the seal; every refused root of §1.1; every forbidden field, including `side`
  outside q0400 and branch-S A frames and `recv_ts` outside q0403); the event-arm hash on fixed fixture ids (both arms
  present, deterministic); the open/close label on the four token × direction fixtures; the age parser (epoch ms; −5 s
  clock-anomaly edge; 60 s and 600 s edges); the shift state on fixtures (touch change → not a unit; `s = 0` kept); the
  interval rule (gap 99 versus 100 min; `dV = 0` not traded; member closed at `k` excluded; **member closed or
  one-sided at `k + 1` → "unavailable (mark)", not excluded**; capture time = last page's `received_utc`); the
  trailing-tercile rule (cut points never include `r_k` or later; 5 versus 6 prior intervals); the B no-mark label;
  the strata-level selection on fixtures (60% edge); **reproduction of P1, P2 and P3's printed counts exactly from the
  worn files** (a different count is a FAIL and is investigated, not adjusted). The code-against-design freeze check
  re-runs this reproduction against the frozen code (ruling 6).
- A failed smoke makes the dependent part terminal "not testable (source)", counted once per declared test.
- Every data job writes a manifest (file sha256s, counts, failures, data-dumps size and margin, free disk) and a
  `*_complete` status.

## 4. Jobs (draft specs; JSON in this document only)

Fields follow `queue/README.md`; `argv[0]` is under `backend/scripts/`, `cwd` `backend`. **None is written to `queue/`**
before code, tests and (for window jobs) a `science-reviewer` freeze check exist. `family` = `creative_batch_17`.
Priority 9 throughout (below every CB6-CB16 job); the pre-censuses may be raised to fill the idle `cpu` lane, an ops
decision that changes no design.

| Id | Lane | Priority | Size / time | Depends on | Commit when |
|---|---|---|---|---|---|
| q0400 | cpu | 9 | ≤ 20 min, mem 600 | - | part `pre` (with the finding 2 and 7 additions) + code + tests reviewed; **can run then** |
| q0401 | cpu | 9 | ≤ 35 min, mem 800 | - | as q0400 |
| q0402 | cpu | 9 | ≤ 45 min, mem 600 | - | as q0400 |
| q0403 | cpu | 9 | ≤ 30 min, mem 500 | - | as q0400 |
| q0404 | cpu | 9 | ≤ 15 min, mem 500 | - | rules parts `common`, `A` (branch S only), `B`, `C`, `E` committed |
| q0405 | cpu | 9 | ≤ 5 min, mem 300 | q0404, CB16 q0380 | after both (or q0380's stop record) |
| q0406 | cpu | 9 | ≤ 60 min per run (budgeted), mem 1000 | q0404, q0405 | not before `S_8 + 14 d + 8 h`; with the ledger attestation (ruling 6) |
| q0407 | cpu | 9 | ≤ 40 min, mem 800 | q0404, q0405 | not before `S_8 + 14 d + 8 h`; E features only if A was withdrawn |
| q0408 | cpu | 9 | ≤ 30 min, mem 600 | q0406, q0407 | with them |
| q0409 | cpu | 9 | ≤ 120 min per run (budgeted), mem 1200, alone | q0408, E011 analysis commit, CB3 freeze or stop record, freeze check | after all |
| q0410 | cpu | 9 | ≤ 60 min per run, mem 1000 | q0409 result committed | not before `S_8 + 28 d + 8 h` |
| q0411 | cpu | 9 | ≤ 120 min per run, mem 1200, alone | q0410, seal copy | only if a Stage-1 test advanced |
| q0412 | cpu | 9 | < 5 min, mem 300 | every triggered Stage-2 test final | once |

```json
{"id": "q0400_cb17_pre_census_A", "title": "CB17 pre-census A/E (counts only, worn CB13-T SCREEN [2026-10-12,10-16)): open/close label from token x d on CB13-T fills; both-label (market,d) cells, markets, events; label by class and price band; side-agreement branch measurement (Data API side vs touch-derived taker side: overall share, Wilson bound, and per touch-age band {0-20, 20-60 min}, P band and LABELLER class with n >= 100) -> branch S, or branch T and A withdrawn uncounted, per part pre; composition-guard informativeness share at strata levels 0/1/2 on the selected branch population (features only) -> selected level; non-sports transactions eligible under branch S; first-day counts (E); planning SE of A1 on the pre-fill proxy under both branches (SEs only)", "family": "creative_batch_17", "priority": 9, "expected_value": "A's fill source and planning MDE; E population", "data": ["creative_batch13/t_screen/{fills,labels}.csv.gz (features)", "live_trades/trades-2026101{2..5}.jsonl (whitelist + side)", "snapshots/ [2026-10-11T22Z, 2026-10-16) (whitelist; no capture after a unit's tau except created_at)"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu"}, "depends_on": [], "argv": ["scripts/run_cb17.py", "pre-census", "--family", "A", "--rules", "../docs/research_lab/seals/cb17_rules.json", "--part", "pre", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch17/pre_census_A.json", "trials.jsonl (cb17_descriptive)"], "next_action": "branch S: record the branch and strata level in rules part A before its commit; branch T: ledger withdrawal of A (uncounted)", "notes": "DRAFT. Counts and SEs only; no M, no mark capture opened (unit-tested). side read for the agreement count only."}
{"id": "q0401_cb17_pre_census_B", "title": "CB17 pre-census B (counts only, worn sweeps [2026-10-12,10-16)): GBT stamp semantics; age bins by class/hour/liquidity; tokens and events mixing old and fresh; touch-unchanged, hash-changed-beneath and shifted-1-5c shares (GBS inputs); next-pass no-mark share by age bin; global activity and imbalance tercile cut points (features; frozen into part B); composition-guard informativeness shares at strata levels 0/1/2 for B1 and B2 -> selected levels; CH149 dormancy map (hash unchanged 2/4/6 h by levels, hour, reward programme); age x grain x size-roundness cross-tab (CH148 inputs); planning SEs of B1 on L_pre and B2 on dm_pre (SEs only)", "family": "creative_batch_17", "priority": 9, "expected_value": "B gates and planning MDEs before the freeze", "data": ["book_sweeps/ [2026-10-12, 2026-10-16) (whitelist)", "snapshots/ rows_ext [same] (sports rule, end_date)"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": [], "argv": ["scripts/run_cb17.py", "pre-census", "--family", "B", "--rules", "../docs/research_lab/seals/cb17_rules.json", "--part", "pre", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 2400, "max_retries": 1, "outputs": ["research_lab/creative_batch17/pre_census_B.json", "trials.jsonl (cb17_descriptive)"], "next_action": "write cut points and selected levels into part B before its commit", "notes": "DRAFT. Pre-decision quantities only; no sweep or capture after a unit's decision time is used as a target; the no-mark share is a presence count only (no mark value read)."}
{"id": "q0402_cb17_pre_census_C", "title": "CB17 pre-census C (counts only, worn captures [2026-10-12,10-16)): traded non-sports event-intervals; OI-changed share (GCU input); units with >= 6 prior traded intervals (trailing terciles) and events holding them; within-event IQR of r; single / neg-risk / other splits; member-move share; member-closing exclusions (k-1, k only); composition-guard informativeness shares at strata levels 0/1/2 (3-class rule: transfer and mint-heavy units in cells holding both) -> selected level; planning SE of C1 on C_pre (SEs only)", "family": "creative_batch_17", "priority": 9, "expected_value": "C gates and planning MDE before the freeze", "data": ["snapshots/ [2026-10-12, 2026-10-16) rows + rows_ext (whitelist)"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu"}, "depends_on": [], "argv": ["scripts/run_cb17.py", "pre-census", "--family", "C", "--rules", "../docs/research_lab/seals/cb17_rules.json", "--part", "pre", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 3000, "max_retries": 1, "outputs": ["research_lab/creative_batch17/pre_census_C.json", "trials.jsonl (cb17_descriptive)"], "next_action": "write the selected level into part C before its commit", "notes": "DRAFT. Eligibility, classes, strata and C_pre use captures <= k only; no k+1 row is read."}
{"id": "q0403_cb17_cost_lag_map", "title": "CB17 cost and lag map (CH155 part; descriptive): executable round trip at $1,000 and $5,000 from depth_*_1c/5c bands and the sidecar fee by fee category x price band x liquidity band on worn sweeps; monitor receipt lag (recv_ts - ts) by class, hour and day with the 5-min polling component; share of prints with lag > 2 h; enrichment coverage", "family": "creative_batch_17", "priority": 9, "expected_value": "the cost hurdle every CB17 econ and taker line cites", "data": ["book_sweeps/ [2026-10-12, 2026-10-16)", "snapshots/ rows_ext [same] (fee fields)", "live_trades/trades-2026101{2..5}.jsonl (whitelist + recv_ts)"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "cpu"}, "depends_on": [], "argv": ["scripts/run_cb17.py", "cost-lag-map", "--rules", "../docs/research_lab/seals/cb17_rules.json", "--part", "pre"], "timeout_s": 2400, "max_retries": 1, "outputs": ["research_lab/creative_batch17/cost_lag_map.json", "trials.jsonl (cb17_descriptive)"], "next_action": "cite in sections 2.1 and 3", "notes": "DRAFT. Depth-band walk is an upper bound on cost (EXECUTION_COSTS execution model)."}
{"id": "q0404_cb17_smoke", "title": "CB17 smoke (cpu, no network): part hashes and CB13/CB16 pins; refusals on fixtures; arm hash; open/close label fixtures; age, shift and interval parsers; exact reproduction of probes P1-P3 counts on worn files", "family": "creative_batch_17", "priority": 9, "expected_value": "go/no-go for every CB17 window job", "data": ["fixtures", "worn files of probes P1-P3"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "cpu"}, "depends_on": [], "argv": ["scripts/run_cb17.py", "smoke", "--rules", "../docs/research_lab/seals/cb17_rules.json"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch17/smoke.json", "trials.jsonl (cb17_descriptive, or counted not-testable lines once)"], "next_action": "PASS: q0405; window jobs after S_8 + 14 d + 8 h", "notes": "DRAFT. Write-once."}
{"id": "q0405_cb17_exclusion_keys", "title": "CB17 exclusion keys (cpu, no network): CB16 q0380 key file (sha256 pinned, source-attributed) + seal copies; overlap counts with CB16 frame ids when they exist", "family": "creative_batch_17", "priority": 9, "expected_value": "window key check", "data": ["creative_batch16/exclusion_keys.csv.gz (ids only)", "docs/research_lab/seals/*"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0404_cb17_smoke", "q0380_cb16_exclusion_keys"], "argv": ["scripts/run_cb17.py", "exclusion-keys", "--rules", "../docs/research_lab/seals/cb17_rules.json"], "timeout_s": 600, "max_retries": 1, "outputs": ["research_lab/creative_batch17/{exclusion_keys.csv.gz,manifest.json}"], "next_action": "q0406, q0407", "notes": "DRAFT. Reads only id and timestamp columns of the CB16 key file (the one exception to the creative_batch16/ refusal, field-restricted). A stopped dependency is recorded as absent."}
{"id": "q0406_cb17_frame_screen_BC", "title": "CB17 SCREEN_8 frames (features only): B token-pass units of arm-0 non-sports events (age, shift state x, touch, eligibility labels, mark-sweep availability flag; no mark value) and C event-interval units (r, classes, member moves k-1->k, eligibility; no k+1 value)", "family": "creative_batch_17", "priority": 9, "expected_value": "B and C Stage-1 units", "data": ["book_sweeps/ [max(2026-10-26T00:00Z, S_8 - 2 h), S_8 + 14 d)", "snapshots/ [max(2026-10-26T00:00Z, S_8 - 6 h), S_8 + 14 d)", "creative_batch17/exclusion_keys.csv.gz"], "resources": {"mem_mb": 1000, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0404_cb17_smoke", "q0405_cb17_exclusion_keys"], "argv": ["scripts/run_cb17.py", "frame", "--families", "B,C", "--window", "screen", "--rules", "../docs/research_lab/seals/cb17_rules.json", "--disk-cap-gb", "0.1", "--data-dumps-cap-gb", "40", "--budget-min", "55"], "timeout_s": 3600, "max_retries": 2, "outputs": ["research_lab/creative_batch17/screen/{b_units.parquet,c_units.parquet,manifest.json}"], "next_action": "q0408", "notes": "DRAFT. Refuses before S_8 + 14 d + 8 h, without the part hashes, the code pin and the ledger attestation; refuses any row before the lookback floor (dependent units unavailable (lookback floor), counted); restores archived sources byte for byte.", "repeat": {"max_runs": 20, "until_log_regex": "\"status\": \"frame_bc_complete\""}}
{"id": "q0407_cb17_frame_screen_A", "title": "CB17 SCREEN_8 transaction frame (features only; under branch T, E features only): fill source per the part-A branch, open/close label, d, P, eligibility and exclusion labels by label, CB16 g and x via pinned functions, E first-day features; no mark", "family": "creative_batch_17", "priority": 9, "expected_value": "A Stage-1 units; E census input; econ fill-source definition", "data": ["live_trades/trades-*.jsonl [2026-10-26, S_8 + 14 d) (whitelist; side only under branch S)", "snapshots/ [max(2026-10-26T00:00Z, S_8 - 3 h), S_8 + 14 d)", "creative_batch17/exclusion_keys.csv.gz"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0404_cb17_smoke", "q0405_cb17_exclusion_keys"], "argv": ["scripts/run_cb17.py", "frame", "--families", "A,E", "--window", "screen", "--rules", "../docs/research_lab/seals/cb17_rules.json", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "40", "--budget-min", "35"], "timeout_s": 2700, "max_retries": 2, "outputs": ["research_lab/creative_batch17/screen/{a_units.csv.gz,manifest.json}"], "next_action": "q0408", "notes": "DRAFT. Refuses before S_8 + 14 d + 8 h and any row before the lookback floor (dependent units unavailable (lookback floor), counted).", "repeat": {"max_runs": 20, "until_log_regex": "\"status\": \"frame_a_complete\""}}
{"id": "q0408_cb17_census_8", "title": "CB17 SCREEN_8 census (counts only): units by label and exclusion; gates GA, GAS (branch S: side vs touch agreement on the touch-consistent subset, overall and per band), GBT, GBA, GBS, GCU, GC; power gates GAP, GB1P, GB2P, GCP on pre-outcome proxies (SEs only); GAI pair count; composition-guard informativeness shares at the selected levels; B no-mark shares by age bin and x band; C unavailable-mark shares by class; lookback-floor unavailability counts; E census and re-entry verdict; politics share; overlap counts", "family": "creative_batch_17", "priority": 9, "expected_value": "gates and MDEs", "data": ["creative_batch17/screen/"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0406_cb17_frame_screen_BC", "q0407_cb17_frame_screen_A"], "argv": ["scripts/run_cb17.py", "census", "--window", "screen"], "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch17/census_8.json", "trials.jsonl (cb17_descriptive or counted not-testable / not-run lines)"], "next_action": "q0409", "notes": "DRAFT. No proxy point estimate written (unit-tested)."}
{"id": "q0409_cb17_screen_8", "title": "CB17 Stage 1: A1 (market x d FE open/close contrast; branch S only), B1 (token FE old-vs-fresh 2 h excursion beyond the touch, adverse movement only), B2 (token FE slope on the breathing-book shift), C1 (event FE transfer-vs-mint continuation); composition guards (conditional estimator + 3-of-200 within-strata permutation), circular-shift calibration placebos (p < 0.01 alone), pre-period placebos, attribution, d-balanced estimate (A), worst-case mark bounds, robustness; GAI; Holm k1 = 4 (branch S) or 3 (branch T)", "family": "creative_batch_17", "priority": 9, "expected_value": "A1, B1, B2, C1 verdicts", "data": ["creative_batch17/screen/", "snapshots/ and book_sweeps/ (mark rows only, SCREEN_8 + 8 h)"], "resources": {"mem_mb": 1200, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0408_cb17_census_8"], "argv": ["scripts/run_cb17.py", "screen", "--budget-min", "110"], "timeout_s": 7200, "max_retries": 1, "outputs": ["research_lab/creative_batch17/results_8.json", "trials.jsonl (cb17_test + creative_batch_17:A n_tests=1 under branch S only, :B n_tests=2, :C n_tests=1)"], "next_action": "advanced: q0410/q0411; ledger", "notes": "DRAFT. Heavy: run alone. Refuses without the code pin, before E011's analysis commit and before CB3's freeze commit or stop record.", "repeat": {"max_runs": 6, "until_log_regex": "\"status\": \"screen_complete\""}}
{"id": "q0410_cb17_frame_rep", "title": "CB17 REP_8 frames (features) and raw mark-quote tables (no mark-out computed): B/C arm-1 units; A units with SCREEN_8 events dropped (counted); econ fill-source tables; source sha256 seal", "family": "creative_batch_17", "priority": 9, "expected_value": "Stage-2 inputs, sealed", "data": ["live_trades/, snapshots/, book_sweeps/ for [S_8 + 7 d, S_8 + 28 d + 8 h)"], "resources": {"mem_mb": 1000, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0409_cb17_screen_8"], "argv": ["scripts/run_cb17.py", "frame", "--families", "A,B,C", "--window", "rep", "--rules", "../docs/research_lab/seals/cb17_rules.json", "--disk-cap-gb", "0.15", "--data-dumps-cap-gb", "40", "--budget-min", "55"], "timeout_s": 3600, "max_retries": 2, "outputs": ["research_lab/creative_batch17/rep/", "docs/research_lab/seals/cb17_rep_SEAL.json (committed by the coordinator)"], "next_action": "q0411 if triggered", "notes": "DRAFT. Runs whatever Stage 1 found (sealing is outcome-blind).", "repeat": {"max_runs": 20, "until_log_regex": "\"status\": \"frame_rep_complete\""}}
{"id": "q0411_cb17_rep_8", "title": "CB17 Stage 2 (triggered only): A1-rep, A2; B1-rep, B1-econ; B2-rep (SCREEN_8 frozen SD_x), B2-econ; C1-rep, C1-econ; pooled GAI; early alpha/8", "family": "creative_batch_17", "priority": 9, "expected_value": "Stage-2 verdicts (L2)", "data": ["creative_batch17/rep/"], "resources": {"mem_mb": 1200, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0410_cb17_frame_rep"], "argv": ["scripts/run_cb17.py", "rep", "--budget-min", "110"], "timeout_s": 7200, "max_retries": 1, "outputs": ["research_lab/creative_batch17/results_rep.json", "trials.jsonl (cb17_replication + creative_batch_17:<family>:rep)"], "next_action": "q0412", "notes": "DRAFT. Verifies the REP seal first. Heavy: run alone.", "repeat": {"max_runs": 6, "until_log_regex": "\"status\": \"rep_complete\""}}
{"id": "q0412_cb17_stage2_final", "title": "CB17 Stage-2 final: one strict Holm (one-sided alpha 0.05) over every triggered CB17 Stage-2 test (<= 8 under branch S, <= 6 under branch T; econ tests enter with the max of their component p's); adds passes only; write-once", "family": "creative_batch_17", "priority": 9, "expected_value": "final Stage-2 decisions", "data": ["creative_batch17/results_rep.json"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu"}, "depends_on": [], "argv": ["scripts/run_cb17.py", "stage2-final"], "timeout_s": 600, "max_retries": 1, "outputs": ["research_lab/creative_batch17/stage2_final.json"], "next_action": "Stage P registration drafts for survivors", "notes": "DRAFT. Refuses with 'nothing to finalise' if no family triggered."}
```

## 5. Code needed (not written by this document)

- `backend/astrolabe/research_lab/cb17_common.py`: reuse `cb16_common` / `cb13_common` (refused roots, disk guards,
  manifests, the small-G cluster p engine, Holm and `stage2_final`, per-part hashing, whitelist readers, restore hooks);
  new: the event-arm hash, the composition-conditional estimator with randomisation inference and the informativeness
  share, a memory-lean multi-way CR1 for FE regressions on ≈ 1.5 M rows (demeaning; float32), the SE-only power gate.
- `cb17_pre.py`: the four pre-censuses (q0400-q0403), including the side-agreement measurement and the branch writer.
- `cb17_a.py`: fill source by branch (CB13-T functions by pin; the side-signed alternative), the label, eligibility,
  marks and decomposition, A1 and its checks, A2.
- `cb17_b.py`: sweep pairing, age, the 2 h excursion beyond the touch, global activity and imbalance cut points, the shift state, marks and the no-mark worst case, B1/B2 and checks, B1-econ/B2-econ.
- `cb17_c.py`: interval construction (k − 1, k only), `r`, terciles (trailing primary; whole-window leave-k,k+1-out robustness), continuation and the unavailable-mark worst case, C1 and checks, C1-econ.
- `cb17_e.py`: first-day features, census, re-entry verdict.
- `backend/scripts/run_cb17.py` with the §4 subcommands; tests `test_cb17_*.py` covering: forbidden fields and refused
  roots; window and lookback edges; the arm hash; the label truth table; age edges; touch-change exclusion; `s = 0` kept;
  interval gap edges, `dV = 0`, member closing at `k` versus unavailable mark at `k + 1`; trailing tercile cut points
  from prior features only; global activity cut points frozen; the lookback-floor refusal and its unavailability label;
  FE estimators cancelling a per-unit constant; the composition-conditional estimator returning 0 on a
  pure-composition fixture and recovering a planted within-stratum effect (the case CB16's original placebo
  mishandled); the 3-of-200 permutation rule at its boundaries (CB16 §11 item 3's fixtures); the informativeness share
  per family including C's three-class rule; the strata-level selection at the 60% edge; the circular-shift calibration
  placebo's null mean under an autocorrelated label and a planted effect; the side-agreement rule with a failing band at
  n = 100 and a band at n = 99 (reported only); the d-balanced estimate; the no-mark and unavailable-mark worst cases;
  power gates writing SEs only; GAI at 199/200 pairs; econ minimums; `SD_x` frozen for REP; battery2 kinds; k1 = 4 or
  3 by branch.

## 6. Test budget and compute

| Job | Tests counted | Kind(s) | Decision |
|---|---|---|---|
| Stage 1: A1 (branch S only), B1, B2, C1 | **4 (S) / 3 (T)** | `cb17_test` + `:A` (1, S only), `:B` (2), `:C` (1) | p < 0.01 strict, floor, binding checks, Holm (one-sided α 0.05, k1 = 4 or 3); counted with p = 1 if a gate fails |
| Stage 2: A1-rep, A2 (S only), B1-rep, B1-econ, B2-rep, B2-econ, C1-rep, C1-econ (each only if triggered) | ≤ 8 (S) / ≤ 6 (T) | `cb17_replication` + `:<family>:rep` | one CB17-wide strict Holm (early finishers at α/8; econ tests enter with the max of their component p's) |
| Pre-censuses, smoke, census, gates, E census, CH149/CH155 maps, strata, sports arms, taker lines; A withdrawn under T | 0 | `cb17_descriptive` | - |
| **Total** | **branch S: 4 fixed + ≤ 8 conditional = 4-12; branch T: 3 fixed + ≤ 6 conditional = 3-9** | | cumulative count recorded at each run (1,282 on the working tree at drafting) |

**Host compute.** About 6-8 CPU-hours in all at nice 19, inside 3 CPU-hours per family: pre-censuses about 2 h (four
worn days of sweeps and captures); SCREEN and REP frames about 1 h each; the screen about 2 h (B's permutations on
≈ 1.4 M rows dominate). Peak RAM 1.2 GB (q0409, q0411; alone). **Network: none. Disk: ≤ 0.3 GB.**

**Calendar (all UTC).**

| By | Deliverable | Owner |
|---|---|---|
| 2026-10-19 | challenger round 1 and this response (§10); done | `science-reviewer`, designer |
| 2026-10-22 | part `pre` (with the finding 2 and 7 additions) committed, then q0400-q0403 code and tests; the four pre-censuses run on the idle `cpu` lane | implementer, queue |
| **2026-10-24 12:00** | **branch recorded (A withdrawn under T); strata levels and cut points written; rules parts `common`, `A` (S only), `B`, `C`, `E` committed** (target) → `S_8` = 2026-10-26 | orchestrator |
| **before `S_8`** | **monitor cap decision (ruling 7; §10)** | orchestrator / owner |
| before `S_8` (preferred), 2026-11-08 at the latest | window code with tests; code-against-design freeze check re-running P1-P3; q0404 PASS; q0405; ledger attestation | implementer, `science-reviewer` |
| `S_8` + 14 d + 8 h (2026-11-09T08:00Z) | q0406, q0407 → q0408 | queue |
| after 2026-11-11T13:00Z and CB3's freeze | q0409 (Stage 1) | queue |
| `S_8` + 28 d + 8 h (2026-11-23T08:00Z) | q0410 (seal), q0411 if triggered, q0412 | queue |

## 7. Main scientific risks (for the challenger)

*Kept as drafted for the record. The challenger's findings and rulings on these risks, and the responses, are in §10;
where §10 and this list differ, §10 and the revised design text govern.*

1. **The composition-check change (§2.6).** CB17 replaces CB16's "stratified permutation placebo must stay quiet" with
   a composition-conditional estimator (unit × stratum FE, keep ≥ half, randomisation p < 0.05) plus a within-unit
   calibration placebo. Is the replacement at least as strict against composition, and are the strata adequate?
2. **A's branch rule.** Using q0400's agreement measured on touch-consistent fills to validate `side` for *all*
   transactions extrapolates: `side` could be right where the touch can sign and wrong elsewhere (CH79's
   complementary-match concern). Is 0.97 with a 0.95 Wilson bound the right gate, and should the branch also require
   CB9-S S0? Under branch T, A1 is probably "not run (power)".
3. **A's label is the traded token within a direction.** Token-specific microstructure (NO-book depth, UI defaults)
   is confounded with open/close; the merge exit mislabels some closes.
4. **B1 measures only the adverse component.** The crossing-fill rule makes `L ≥ 0` by construction; quiet-hour
   composition pushes against the hypothesis, so a null is weakly informative and a positive is only as strong as the
   attribution. The sweep mark is about 2 h after the decision and only covers tokens still swept (93% next-pass
   presence on worn data).
5. **B2 near its kill, and the pre-sweep placebo may be over-strict.** Only 22% of pairs shift beneath an unchanged
   touch. If bots re-quote in reaction to past moves, the binding pre-sweep placebo can stop B2 even when the
   attribution regression would credit it.
6. **C's units.** OI in shares versus volume in dollars; within-event terciles use the whole window's intervals (a
   feature, but not point-in-time; the trailing-tercile robustness is the causal version); neg-risk conversions;
   multi-member events average members; the OI field's update lag (the lag variant).
7. **Event-arm split for B and C** halves each window's units (harmless for power) and makes REP a different set of
   events in a later window: a replication of the mechanism, not of the same markets.
8. **Correlated tests and windows.** A1 shares units with CB16-Q/U on overlapping days; B1 and B2 share B's frame; E011,
   CB3 and CB16 overlap in time (collection only). The election-night exclusion is the only regime cut; SCREEN_8 spans
   the US election run-up.
9. **Rules-before-data, code-before-read** (§1.2 `T17_code`) is a declared deviation from CB16's "frozen with code"
   timing, chosen so that `S_8` can be 2026-10-26.
10. **Availability.** Capture gaps (10-14 00:31-10:31 missing on the host), the monitor's 3 GB cap (late November to
    early December at the recent rate), and archive-and-delete of sources before the frame jobs (restore byte for byte).
11. **Econ tests are thin under branch T** (B1-econ about 130 fills per bin) and every econ test is a protection value or
    an upper bound; none is a route.
12. **Probe audit.** P1-P3 texts and sha256 were fixed before the run and are verbatim in §9; the P0 header listings
    exposed a few feature values (listed in §0.3), no price.

## 8. Next actions

1. Challenger round 1 is done and answered (§10). Under the programme rule (one challenge, one response), the
   orchestrator now decides proceed / revise / reject on this revision; no second challenge round.
2. Implementer: **part `pre` first** (contents in §10, "Part `pre` before q0400-q0403 code"), then q0400-q0403 code and
   tests (they need no freeze and no window; the `cpu` lane is idle). Then the window code, frozen before `S_8` if
   possible and by 2026-11-08 at the latest, with a code-against-design freeze check that re-runs P1-P3.
3. Orchestrator: after q0400, record the branch (under T, ledger the uncounted withdrawal of A); write the selected
   strata levels and cut points into parts A (S only), B and C; commit rules parts by 2026-10-24T12:00Z (else `S_8`
   slides); **decide the monitor cap before `S_8`** (§10, ruling 7); ledger lines for this revision (design only, not
   counted), for each pre-census and for the ruling-6 attestations.
4. CB16's reservation is narrowed to q0393-q0399 by this draft (§0.1); the CB16 document is not edited here.

## 9. Probe scripts (verbatim; the bytes that ran)

sha256 (identical locally and on the host before the run):
`e8f84790696a85c238539af57705091578926c286d70ed0e5456d475a11f57df  cb17_p1_fills.py`,
`ddedd91c2419c7e51d4c586794fa7bbf48c887bcd31afd09bae6f75d7f97b805  cb17_p2_sweeps.py`,
`a95ced868801a737ce715f9034583d0c6e3126ab12c6c192d933c3fca61c61b9  cb17_p3_oi.py`. The root path is split as
`"data-" + "dumps"` only to pass a local editor hook; it resolves to `/home/opc/arepo/data-dumps/research_lab`.

```python
# CB17 probe P1 (counts only): CB13-T SCREEN fill table (features) joined to monitor prints for the traded token
# (outcome_index) and to capture created_at for market age. Prints counts only. No mark, outcome, side or wallet read.
import csv, gzip, json
from collections import Counter, defaultdict
from datetime import datetime
R = "/home/opc/arepo/data-" + "dumps/research_lab"
def ep(s):
    try: return float(s)
    except ValueError: return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
fills = []
with gzip.open(R + "/creative_batch13/t_screen/fills.csv.gz", "rt") as f:
    for r in csv.DictReader(f):
        if r["status"] == "fill":
            fills.append((r["condition_id"], r["market_id"], r["event_id"], r["label"], int(ep(r["tau"])),
                          int(ep(r["tau_last"])), int(float(r["d"]))))
need = {x[0] for x in fills}
pr = defaultdict(set)  # (condition_id, ts) -> {(tx16, outcome_index)}
for day in ("12", "13", "14", "15"):
    with open(R + "/live_trades/trades-202610%s.jsonl" % day) as f:
        for line in f:
            try: d = json.loads(line)
            except Exception: continue
            c = d.get("condition_id")
            if c in need and d.get("ts") is not None:
                pr[(c, int(float(d["ts"])))].add((d.get("tx16"), d.get("outcome_index")))
created = {}
for cap in ("20261012T003103Z_2df48d64", "20261015T223102Z_2eae9aa6"):
    with gzip.open(R + "/snapshots/%s/rows_ext.csv.gz" % cap, "rt") as f:
        for r in csv.DictReader(f):
            if r["created_at"]: created.setdefault(r["market_id"], ep(r["created_at"]))
res = Counter(); lab = {}
for i, (c, m, e, cl, t0, t1, d) in enumerate(fills):
    s = set()
    for t in range(t0, t1 + 1): s |= pr.get((c, t), set())
    txs = {a for a, _ in s}; ois = {b for _, b in s}
    if not s: res["no_print"] += 1; continue
    if len(txs) > 1: res["ambiguous_tx"] += 1; continue
    if len(ois) != 1 or list(ois)[0] not in (0, 1): res["mixed_or_unknown_token"] += 1; continue
    oi = list(ois)[0]; res["resolved"] += 1
    lab[i] = "open" if (oi == 0 and d == -1) or (oi == 1 and d == 1) else "close"
print("fills", len(fills), "token resolution", dict(res))
ns = [i for i, x in enumerate(fills) if x[3] != "SPORTS-FEED"]
print("non-sports fills", len(ns), "resolved", sum(1 for i in ns if i in lab))
print("non-sports label", dict(Counter(lab[i] for i in ns if i in lab)))
print("non-sports label x class", dict(Counter((fills[i][3], lab[i]) for i in ns if i in lab)))
print("sports label", dict(Counter(lab[i] for i, x in enumerate(fills) if x[3] == "SPORTS-FEED" and i in lab)))
cell = defaultdict(Counter)
for i in ns:
    if i in lab: cell[(fills[i][1], fills[i][6])][lab[i]] += 1
both = set(k for k, v in cell.items() if v["open"] and v["close"])
print("non-sports (market,d) cells", len(cell), "with both labels", len(both),
      "fills in both-label cells", sum(sum(cell[k].values()) for k in both),
      "markets", len({k[0] for k in both}),
      "events", len({fills[i][2] for i in ns if i in lab and (fills[i][1], fills[i][6]) in both}))
mk = defaultdict(Counter)
for i in ns:
    if i in lab: mk[fills[i][1]][lab[i]] += 1
mb = [m for m, v in mk.items() if v["open"] and v["close"]]
print("non-sports markets with both labels (any d)", len(mb), "fills in them", sum(sum(mk[m].values()) for m in mb))
age = Counter(); am = defaultdict(set)
for i in ns:
    c, m, e, cl, t0, t1, d = fills[i]
    if m not in created: age["unknown"] += 1; continue
    h = (t0 - created[m]) / 3600.0
    b = "neg" if h < 0 else "<6h" if h < 6 else "6-24h" if h < 24 else "1-7d" if h < 168 else ">7d"
    age[b] += 1; am[m].add("first" if h < 24 else "later")
print("non-sports fills by market age", dict(age))
fb = [m for m, s in am.items() if s == {"first", "later"}]
print("non-sports markets with first-day and later fills", len(fb), "markets with any first-day fill",
      sum(1 for s in am.values() if "first" in s))
```

```python
# CB17 probe P2 (counts only): 2026-10-15 sweeps. book_timestamp semantics (hash unchanged => stamp unchanged),
# book-age histogram (non-sports), touch-unchanged / hash-changed / shifted-beneath shares, next-pass token presence.
# best_bid/best_ask/depth values are compared in memory only; nothing but counts is printed.
import csv, gzip, os
from collections import Counter, defaultdict
from datetime import datetime
R = "/home/opc/arepo/data-" + "dumps/research_lab"
def ep(s): return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
sports = set()
with gzip.open(R + "/snapshots/20261015T063101Z_9c518015/rows_ext.csv.gz", "rt") as f:
    for r in csv.DictReader(f):
        if (r["fee_type"] or "").startswith("sports"): sports.add(r["market_id"])
sw = sorted(d for d in os.listdir(R + "/book_sweeps") if d.startswith("20261015T"))
def load(s):
    out = {}
    with gzip.open(R + "/book_sweeps/%s/rows.csv.gz" % s, "rt") as f:
        for r in csv.DictReader(f):
            out[r["token_id"]] = (r["market_id"], r["batch_receipt_utc"], r["book_timestamp"], r["book_hash"],
                                  r["best_bid"], r["best_ask"], r["depth_bid_1c"], r["depth_bid_5c"],
                                  r["depth_ask_1c"], r["depth_ask_5c"], r["state"])
    return out
def sid_t(s): return datetime.strptime(s[:16], "%Y%m%dT%H%M%SZ").timestamp()
t0 = [sid_t(s) for s in sw]
pairs = [(i, i + 1) for i in range(len(sw) - 1) if t0[i + 1] - t0[i] < 1800]
print("sweeps", len(sw), "intra-pass pairs", len(pairs))
c = Counter(); age = Counter(); per_tok = defaultdict(set); first = []
for i, j in pairs:
    A = load(sw[i]); B = load(sw[j]); first.append(set(tk for tk, a in A.items() if a[0] not in sports))
    for tk, a in A.items():
        if a[0] in sports: c["sports_tok"] += 1; continue
        c["ns_tok"] += 1
        try: ag = ep(a[1]) - float(a[2]) / 1000.0
        except (ValueError, TypeError): age["unparseable"] += 1; ag = None
        if ag is not None:
            b = "neg<-5s" if ag < -5 else "<60s" if ag < 60 else "60-600s" if ag < 600 else "600-3600s" if ag < 3600 else ">3600s"
            age[b] += 1
            if b == "<60s": per_tok[tk].add("fresh")
            if b in ("600-3600s", ">3600s"): per_tok[tk].add("old")
        b2 = B.get(tk)
        if b2 is None: c["ns_missing_in_2"] += 1; continue
        if a[10] != "two_sided" or b2[10] != "two_sided": c["ns_not_two_sided"] += 1; continue
        c["ns_pair"] += 1
        sh = a[3] == b2[3]; st = a[2] == b2[2]; tu = a[4] == b2[4] and a[5] == b2[5]
        c["hash_same"] += sh; c["hash_same_stamp_same"] += sh and st; c["hash_diff"] += not sh
        c["hash_diff_stamp_diff"] += (not sh) and (not st); c["touch_same"] += tu
        c["touch_same_hash_diff"] += tu and not sh
        if tu:
            try:
                sa = (float(b2[9]) - float(b2[8])) - (float(a[9]) - float(a[8]))
                sb = (float(b2[7]) - float(b2[6])) - (float(a[7]) - float(a[6]))
                c["touch_same_shift_nonzero"] += (sa - sb) != 0
            except (ValueError, TypeError): c["touch_same_shift_unparseable"] += 1
    A = None; B = None
print("counts", dict(c))
print("non-sports age bins (first sweep of each pass)", dict(age))
print("non-sports tokens with both fresh and old sweeps on the day", sum(1 for s in per_tok.values() if s == {"fresh", "old"}),
      "tokens seen", len(per_tok))
avail = Counter()
for k in range(len(first) - 1):
    avail["ns_tok_pass"] += len(first[k]); avail["next_pass_present"] += len(first[k] & first[k + 1])
print("next-pass presence (non-sports token in next pass first sweep)", dict(avail))
```

```python
# CB17 probe P3 (counts only): 2026-10-15 captures. Event OI update rate in traded intervals; events with >= 6 traded
# intervals; single / multi / neg-risk; intervals with a member mid move >= 0.5c (mids at k-1 and k only; no later
# capture is read for any interval). Prints counts only.
import csv, gzip, os
from collections import Counter, defaultdict
R = "/home/opc/arepo/data-" + "dumps/research_lab"
caps = sorted(d for d in os.listdir(R + "/snapshots") if d.startswith("20261015T"))
def num(x):
    try: return float(x) if x not in ("", "None") else None
    except ValueError: return None
def load(cap):
    ev = {}; mem = defaultdict(list); sp = set(); nr = set()
    with gzip.open(R + "/snapshots/%s/rows_ext.csv.gz" % cap, "rt") as f:
        for r in csv.DictReader(f):
            e = r["event_id"]
            if not e: continue
            ev[e] = (num(r["event_open_interest"]), num(r["event_volume"]))
            mem[e].append(r["market_id"])
            if (r["fee_type"] or "").startswith("sports"): sp.add(e)
            if r["neg_risk_market_id"]: nr.add(e)
    mid = {}
    with gzip.open(R + "/snapshots/%s/rows.csv.gz" % cap, "rt") as f:
        for r in csv.DictReader(f):
            b, a = num(r["best_bid"]), num(r["best_ask"])
            if b is not None and a is not None and 0 < b < a < 1 and a - b <= 0.10: mid[r["market_id"]] = (a + b) / 2
    return ev, mem, sp, nr, mid
c = Counter(); traded = Counter(); prev = None
for cap in caps:
    cur = load(cap)
    if prev is not None:
        ev0, _, _, _, mid0 = prev; ev1, mem1, sp1, nr1, mid1 = cur
        for e, (oi1, v1) in ev1.items():
            if e in sp1 or e not in ev0: continue
            oi0, v0 = ev0[e]
            if None in (oi0, oi1, v0, v1): c["ns_missing_oi_or_vol"] += 1; continue
            if v1 - v0 <= 0: c["ns_not_traded"] += 1; continue
            c["ns_traded"] += 1; traded[e] += 1
            c["oi_changed"] += oi1 != oi0
            k = "single" if len(mem1[e]) == 1 else "multi_nr" if e in nr1 else "multi_other"
            c["traded_" + k] += 1
            mv = any(m in mid0 and m in mid1 and abs(mid1[m] - mid0[m]) >= 0.005 for m in mem1[e])
            c["traded_with_member_move"] += mv
    prev = cur
print("captures", len(caps), "intervals", len(caps) - 1)
print("non-sports event-intervals", dict(c))
print("non-sports events traded in >= 6 intervals", sum(1 for v in traded.values() if v >= 6),
      ">= 3", sum(1 for v in traded.values() if v >= 3), "any", len(traded))
```

## 10. Challenger round 1 and response

The batch's one challenge (`science-reviewer`, 2026-10-19, on `a00c4ef`) and the designer's one response (programme
rule: one challenge, one response, then the orchestrator decides proceed / revise / reject). Line numbers in the
findings refer to `a00c4ef`. **Verdicts:** A, B1, B2 and C REVISE; E census and q0400-q0403 PROCEED once part `pre`
holds the finding 2 and 7 additions. **The response used no CB17 window data and no outcome data**; every change is
outcome-blind, and none loosens a floor, alpha, gate, threshold or the cumulative count (the coarser strata are chosen by
a feature-only rule fixed before q0400; the 50%, half-effect and 3-of-200 rules are unchanged or stricter).

### 10.1 Findings

| # | Sev. | Finding (summary) | Response | Where applied |
|---|---|---|---|---|
| 1 | HIGH | C eligibility required two-sided `k + 1` mids in [0.03, 0.97] and no member closed through `k + 1`: selection on the outcome | **Adopted.** Eligibility uses `k − 1` and `k` only (closed flag at `k − 1`, `k`; `end_date` known at `k`, ≤ `k` + 3 h excluded). A missing, closed, one-sided, wide or extreme `k + 1` quote is "unavailable (mark)", counted by class and reason, under the 60% availability rule, with a **binding worst-case robustness** (unavailable members at the bound adverse to the hypothesis; sign kept) | §1.2 marks; §2.2; §CB17-C units, target, robustness; q0402/q0406 notes; smoke; §5 |
| 2 | HIGH | Composition strata far too fine (A 144 per market × d cell against about 12 units; B 96; C 72): the 50% both-label rule fails by construction; C's three-class "both labels" undefined | **Adopted.** Each family declares a three-level strata ladder now (§2.6 table). q0400-q0402 report the informativeness share at every level on worn data (features only) and the **finest level with ≥ 60%** is written into the family's part before its commit (else level 2, with the window's 50% rule binding). Denominators declared: binary labels, all units; B2, units in cells with ≥ 2 units and non-constant `x`; **C: transfer and mint-heavy units in cells holding at least one of each, over all transfer and mint-heavy units** (merge-heavy reported) | §1.4 `pre`; §2.6; §2.7; §CB17-A/B/C composition guards; q0400-q0402, q0408 |
| 3 | HIGH/MED | Calibration placebo judged on "p < 0.01 and the floor" is vacuous at SE 0.02-0.05c against a 0.5c floor; CB16 §11 judges p alone; one-at-a-time within-unit shuffles destroy the label's autocorrelation | **Adopted.** Each draw is judged on one-sided p < 0.01 alone (CB16 §11 item 1); advance rate ≤ 1.5% (≤ 3 of 200). The label is **circularly shifted within the unit** in time order (offset uniform on {1, …, n − 1}), one of the challenger's two options; chosen over whole-day blocks because it also works for units observed on one or two days | §2.6 item 2; §CB17-A/B/C calibration placebos; §5 |
| 4 | MED | B's 2 h mark: 93% of tokens swept next pass; drop-outs become "no mark" | **Modified.** No-mark share reported by age bin (q0401 worn; q0408 window) and by `x` sign and `|x|` quintile for B2; **binding worst-case bound** for B1 and B2. *Modification:* a no-mark unit first takes the recorded capture mark (CB13 rule) where one exists, and only units with no recorded price take the adverse bound (B1: old `L = 0`, fresh the 95th percentile; B2: 5th / 95th percentile of `Δm` against the sign of `x`). *Reason:* a recorded capture mid is an observed price, not an imputation; bounding observed prices would discard data without guarding anything. The pure capture-mark variant stays a separate binding robustness | §CB17-B shared frame, B1/B2 robustness; q0401, q0408 |
| 5 | MED | q0406 (from `S_8 − 2 h`), q0407 (from `S_8 − 3 h`) and §1.1 (from `S_8 − 7 d`) read inside CB13-T's sealed HOLDOUT `[t_j4r_end, 10-26)` | **Adopted.** Every window reader refuses pre-floor rows; read windows start at `max(floor, ·)`; units needing a pre-floor row are "unavailable (lookback floor)", counted by family and label/state; smoke fixtures at `S_8 − 2/3/6 h` | §1.1; §1.2 lookback floor; q0406/q0407 specs; smoke |
| 6 | MED (B: LOW) | C's whole-window tercile cut points include `r_{k+1}` (and later); B1's activity terciles pool later units' pre-decision moves, which overlap earlier units' targets | **Adopted.** C: **trailing terciles primary** (prior intervals in `[floor, k)`, ≥ 6 prior, else "thin history"); the trailing `dV` stratum likewise; whole-window terciles **leaving `k` and `k + 1` out** become a binding robustness. GC re-stated on units with ≥ 6 prior intervals; power restated (MDE 0.15-0.25c). B: activity and imbalance tercile cut points are **global, frozen in part B from q0401's worn units**, never recomputed on SCREEN_8 or REP_8 | §CB17-B; §CB17-C state, strata, robustness, gates, power; q0401/q0402 |
| 7 | MED | Branch S gate too coarse; no window check of signing; spending a counted test under branch T | **Adopted.** Branch S also needs ≥ 97% agreement in every touch-age band {0-20, 20-60 min}, `P` band and LABELLER class with n ≥ 100; **GAS** re-checks the same rule on SCREEN_8's touch-consistent subset at q0408 (else A1 "not testable (signing)", counted); **under branch T, A is withdrawn uncounted before its part commit** (CB15-L precedent). The rule is fixed in part `pre` before q0400 (ruling 2) | §0; §1.4; §2.5; §CB17-A; q0400, q0407-q0409 |
| 8 | LOW | (a) C decision time should be the capture's last page `received_utc` (`ext_sidecar.py` `ext_row` stamps per page); (b) rename B1's target; (c) branch-S power at the 0.5c floor about 40% | **Adopted.** (a) capture time = last page's `received_utc` for every CB17 use; (b) "2 h excursion beyond the touch", labelled adverse movement only; (c) disclosed in §0 and §CB17-A power | §1.2; §2.2; §2.4; §CB17-B; §0; §CB17-A |

**Count: 7 adopted, 1 modified (finding 4), 0 rejected.**

### 10.2 Rulings

| # | Ruling | Response | Where applied |
|---|---|---|---|
| 1 | Keep the composition-conditional estimator **and** add CB16 §11's rule (holds only if ≤ 3 of 200 permuted coefficients reach the observed); describe CB16 as amended | **Adopted.** The composition guard has two binding parts: the conditional estimator (sign, half, p < 0.05) and the within-strata permutation test with CB16 §11's 3-of-200 rule, which replaces the draft's weaker "randomisation p < 0.05". §2.6 now describes CB16 as drafted and as amended by §11 | §2.6; §CB17-A/B/C; q0409 |
| 2 | Side-rule switch acceptable if fixed in part `pre` before q0400 | **Adopted** | §1.4; §CB17-A |
| 3 | Add a binding d-balanced estimate (equal-weight average of the two d coefficients) keeping the sign | **Adopted** | §CB17-A |
| 4 | B1 labelled adverse movement only; B1-econ the only maker-relevant line | **Adopted** | §0; §2.4; §CB17-B; q0409 |
| 5 | Keep B2's pre-sweep placebo binding | **Adopted** (unchanged; text now says a state explained by the past move is not a forward signal) | §CB17-B B2 |
| 6 | Code frozen before first read accepted with conditions: no agent opens SCREEN_8/REP_8 files before q0406 (ledger attestation); the freeze check re-runs P1-P3 reproduction against frozen code; preferably freeze code before `S_8` | **Adopted.** Target code freeze before `S_8`; attestations at the code freeze and with q0406's commit (q0406 refuses without it); P1-P3 reproduction in the freeze check | §1.2 `T17_code`; smoke; §6 calendar; q0406 |
| 7 | `live_trades/` holds 372 MB, grows about 65 MB/day (`scores-*` 76%); the 3 GB cap is reached about 11-25 to 11-29 against REP_8's end 11-23T08:00Z: decide before `S_8` | **Answered with a proposal for the orchestrator** (10.3). No host or collector setting is changed by this document | §2.8; §6 calendar; §8 |
| 8 | Separate Holm families per batch OK; A1 and CB16-Q/U never cited as corroborating; REP_8 overlaps CB16 SCREEN_A/REP_A (disclose) | **Adopted** | §1.1 reuse disclosure |

### 10.3 Monitor cap: proposal for the orchestrator (ruling 7; outcome-blind)

**What the cap is.** `TOTAL_CAP_BYTES = 3 GiB` in `live_trade_monitor.py`, checked as `du` of the whole `live_trades/`
root each cycle; at the cap the monitor raises `CapReached` and stops (exit 3). A separate **300 MB per-day cap**
pauses writing for the rest of a UTC day. The total cap is a storage budget set when the monitor ran on the Mac; the
per-day cap is the runaway guard. `total_cap_bytes` is **not** in `MonitorConfig.config_hash()`, so changing it does not
change the monitor's scientific configuration identity.

**Options.**
- **(a) Recommended: raise the total cap to 8 GiB before `S_8`**, as a reviewed one-line code change to the default
  deployed by the usual `COLLECTION_HOST.md` deploy and rollback path. The 300 MB/day runaway guard stays. With about
  56 GB free on the host, this uses at most about 5 GB more and moves the cap to roughly February 2027 at 65-75 MB/day,
  covering REP_8 and CB16's REP_A with wide margin. It is an ops change on the collection host (not production, no
  data deleted); the orchestrator should confirm, before deploying, that the extra growth keeps `data-dumps/` under the
  40 GB `--data-dumps-cap-gb` guard used by CB jobs (else those jobs would exit 75), and should treat it as an owner
  decision if it judges the change to be an infrastructure change under CLAUDE.md. The decision uses byte counts only.
- **(b) Fallback if (a) is not taken: change nothing and keep REP_8 at 14 days.** The projected cap date falls after
  REP_8's last needed row (2026-11-23T08:00Z) by about two to six days; any stopped day is "unavailable (monitor
  stopped)", counted, never back-filled; A2 and the econ minimums decide availability as declared. CB16's REP_A tail
  would be lost (CB16's disclosure). The orchestrator re-measures `du` weekly and records it in the ledger.
- **(c) Not recommended: shorten REP_8.** It is a design change with no scientific reason, costs Stage-2 power and is
  unnecessary at the projected rate.
- **(d) Not recommended: compress or move `scores-*` files.** The monitor's trailing-percentile alert rule reads
  `scores-*.jsonl` from `live_trades/`, so this alters a running collector's inputs, and it touches the retention
  policy.

CB17 never reads `scores-*` (refused root), so (a) and (b) leave every CB17 rule unchanged.

### 10.4 Part `pre` before q0400-q0403 code (exact content)

Part `pre` of `seals/cb17_rules.json` must hold, before any q0400-q0403 code is written:
1. **Worn inputs:** the paths and dates of q0400-q0403 (CB13-T SCREEN `fills.csv.gz`/`labels.csv.gz`; monitor
   `trades-2026101{2..5}.jsonl`; sweeps and captures of `[2026-10-12, 2026-10-16)` plus the `created_at` captures of P1)
   and the census paths' refusal of any row at or after 2026-10-16T00:00Z; the census field whitelists (`side` for
   q0400's agreement count only; `recv_ts` for q0403 only).
2. **Branch rule (finding 7):** overall agreement ≥ 97% with Wilson 95% lower bound ≥ 0.95 and n ≥ 800, and ≥ 97% in
   every touch-age band {0-20, 20-60 min}, `P` band {[0.03, 0.20), [0.20, 0.80], (0.80, 0.97]} and LABELLER class with
   n ≥ 100 (others reported); pass → branch S; fail or not run → branch T and **A withdrawn uncounted** before any
   part commit; the GAS rule (same criteria on SCREEN_8's touch-consistent subset).
3. **Strata ladders and selection (finding 2):** the §2.6 ladder table for A, B1, B2 and C; the informativeness
   definitions (binary; continuous; C's three-class numerator and denominator); the selection rule (finest level with
   worn-data share ≥ 60%, else level 2); A's share computed on the selected branch's population.
4. **Feature cut points (finding 6):** B's global activity and imbalance tercile recipe on q0401's worn non-sports
   units (pre-decision quantities only); C's trailing-tercile rule (≥ 6 prior traded intervals, `r_k` and later
   excluded) and the trailing `dV` stratum, as q0402 computes them.
5. **Planning SEs:** the SE-only recipe on the pre-outcome proxies (A pre-fill move; B `L_pre`, `Δm_pre`; C `C_pre`),
   `MDE = 3.80 × SE`, no proxy point estimate written.
6. **Cost map:** q0403's size grid ($1,000, $5,000), depth bands and fee rule.

With these six items committed, E's census and q0400-q0403 PROCEED per the challenger's verdict.

### 10.5 New k

- **Branch S:** 4 fixed (A1, B1, B2, C1) + ≤ 8 conditional = **4-12; k1 = 4**.
- **Branch T:** A withdrawn uncounted; 3 fixed (B1, B2, C1) + ≤ 6 conditional = **3-9; k1 = 3**.
- The branch is decided by q0400 (features only) before any part commit; Stage-2 early finishers stay at α/8 in both.

**Status after this response: DRAFT-REVISED. Nothing frozen, nothing queued, no code.**

## 11. Post-pre-census record (2026-10-20; values filled from q0400-q0403)

Written 2026-10-20 07:30 UTC+1 (06:30Z) by the implementer from the four write-once pre-census results on the host
(`research_lab/creative_batch17/`), copied off the host as counts-only JSON and read in full. No outcome, mark, guarded,
SCREEN_8 or REP_8 file was opened (none exists). **Nothing in §0-§10 is changed:** no floor, alpha, gate, threshold,
window or formula. This section fills only what the design said the pre-censuses would fill (the branch, the strata
levels, B's frozen cut points, C's level and trailing-tercile inputs, the cost-lag map citations) and records, as open
questions (§11.8), every point where the design left a choice open. Numbers are verbatim from the named files; derived
shares are labelled "derived".

| Job | Result file | sha256 | Part `pre` | Status |
|---|---|---|---|---|
| q0400 | `pre_census_A.json` | `9deedcf5a1aeb0e370796457cab3f933d8e4c6b59e6a5de302c9a70e82ec38cf` | `ddc0249b…` | `pre_census_A_complete`, P1 reproduced |
| q0401 | `pre_census_B.json` | `c3b8ae1b0f8d0bb7b54126193371e479c9175078591ebd46bb990d36ef063a1a` | `ddc0249b…` | `pre_census_B_complete` |
| q0402 | `pre_census_C.json` | `442e99da3a7f806b05a76fa9de4e6a52bb8ded5516ff1ae2c67092a46812797d` | `ddc0249b…` | `pre_census_C_complete` |
| q0403 | `cost_lag_map.json` | `43f28e02068094c9b7e45903f04525e44a30e4d1864c9077ccdbf5540eb629bf` | `ddc0249b…` | `cost_lag_map_complete` |

Part `pre` = `ddc0249b23eedf8cfe50b2b60e94378264804ca4791c82c01cf3993df54df6a7` in every file (verified against the code
at this commit).

### 11.1 Branch T; CB17-A withdrawn uncounted

- **P1 reproduced** (every count equal): fills 2,931; token-resolved 2,715; ambiguous transaction 216; non-sports 1,006;
  non-sports resolved 971; open 676; close 295. The both-label cells also match P1: 440 non-sports (market, d) cells, 44
  with both labels, 364 fills, 34 markets, 26 events.
- **Side agreement** (§CB17-A branch rule, part `pre`): overall **906 / 971 = 93.3%**, Wilson 95% lower bound
  **0.915571** (n = 971 ≥ 800 holds; 97% and 0.95 fail). Every binding cell (n ≥ 100) also fails 97%: touch age 0-20 min
  367/382, 20-60 min 539/589; `P` [0.03, 0.20) 347/361, [0.20, 0.80] 386/431, (0.80, 0.97] 159/165; PATH-SETTLED
  121/135, SCHEDULED-EVENT 362/392, UNSCHEDULED-NEWS 397/417. Reported only (n < 100): PUBLIC-STATISTIC 26/27.
- **Consequence, as pre-declared (§2.5, §10.5):** branch **T**. **Family A is withdrawn uncounted** before any part
  commit. Part `A` is never committed: `seals/cb17_rules.json` keeps part `A` at `part_declared: false` with the reason
  "withdrawn uncounted (branch T)". **k = 3 fixed (B1, B2, C1) + up to 6 conditional (B1-rep, B1-econ, B2-rep,
  B2-econ, C1-rep, C1-econ) = 3-9; k1 = 3** (Holm first step 0.05/3 = 0.0167, so any p < 0.01 passes it). Stage-2
  early finishers stay at α/8. Count lines: `creative_batch_17:B` (2) and `creative_batch_17:C` (1) only. GAS, A1,
  A1-rep and A2 never run. **No window job parses `side`** (q0407 and q0410 read no `side` under branch T). q0407 builds
  E's features only. The econ fill source (B1-econ, B2-econ, C1-econ; REP_8) is CB13-T's frozen touch-consistent rule
  by pin.
- Reported, not used: A1 planning MDE under T **2.197c** (SE 0.578245, n 954; over the 1.0c power gate, as §CB17-A
  expected) and under S 0.888c (SE 0.233566, n 3,139); A's strata level on both populations would have been level 1
  (T 0.9835, S 0.9734). The side-signed population held 3,158 eligible units of 7,368 non-sports transactions.

### 11.2 CB17-B: frozen cut points and selected levels (q0401)

| Quantity (written into part `B`) | Value (verbatim) | Source and rule |
|---|---|---|
| Activity tercile cut points (cents) | `[0.0, 0.10000000149011612]` | `cut_points.activity_terciles_c`; 545,355 worn non-sports eligible units (`B_ACTIVITY_RECIPE`) |
| Imbalance tercile cut points | `[-0.021718762814998627, 0.4006465971469879]` | `cut_points.imbalance_terciles`; 481,657 touch-unchanged units (`B_IMBALANCE_RECIPE`) |
| Tercile assignment | value ≤ lower cut → 0; ≤ upper cut → 1; else 2 | part `pre` `TERCILE_QUANTILES` / `tercile_of` |
| **B1 strata level** | **2** (activity tercile) | fallback: shares level 0 0.0297, level 1 0.0528, level 2 0.0863 (denominator 460,737); no level reaches 60%, so level 2 is written and the window's 50% rule binds as declared |
| **B2 strata level** | **1** (activity tercile × imbalance tercile) | shares level 0 0.3342, level 1 **0.6030**, level 2 0.6734 (denominator 481,657) |

- **Float32 note.** q0401 stored both features as float32, so the cut points are float32 values: the upper activity
  cut is float32(0.1) = 0.10000000149011612. Activity tercile 0 is therefore exactly "no mid change since the previous
  pass", tercile 1 a change of at most 0.1c, tercile 2 more than 0.1c (the terciles are unequal because of ties at 0).
  The window code casts both features to float32 before comparing, to classify exactly as the census did (open
  question O6).
- `SD_x` on worn data is 0.08671511, **reported only**: §CB17-B freezes `SD_x` from SCREEN_8 for REP_8 (unchanged).
- Worn-data gate inputs (reported; the window gates q0408 decide): GBT hash unchanged ⇒ stamp unchanged 157,435 of
  157,435, hash changed ⇒ stamp changed 387,912 of 387,912. GBS: shifted beneath an unchanged touch 139,716 of 481,657
  (29.0% ≥ 20%). GBA inputs: age bins `< 60 s` 443,397, `60-600 s` 112,176, `600-3600 s` 44,152, `> 3600 s` 87,477;
  4,828 of 36,277 tokens and 3,191 events hold both a fresh and an old book.
- Next-pass no-mark (presence only, no price read): absent at the 2 h pass, derived as absent / (present + absent):
  `< 60 s` 6.0%, `60-600 s` 6.5%, `600-3600 s` 10.7%, `> 3600 s` 6.5%; plus "no pass in window" counts 21,119 / 4,782 /
  2,697 / 3,961 (the census window's tail).
- Planning SEs (SE only): B1 on `L_pre` **0.020547c** (MDE 0.0781c, n 413,693); B2 on `Δm_pre` **0.004544c per SD**
  (MDE 0.0173c, n 481,657). Both are far under the 1.0c power gate; the floor binds, as §CB17-B said.
- **Risk flag (no rule change).** B1's coarsest level reaches 8.6% on worn data against the window's 50%
  informativeness rule. Unless 14 window days raise it about six-fold, B1's composition guard will be "uninformative"
  and B1 cannot advance (still counted, with its p). A "not advanced" B1 for that reason says nothing about book age
  (O3).

### 11.3 CB17-C: selected level and trailing-tercile inputs (q0402)

- **C strata level: 2** (`|Δm_int|` {0.5-1c, > 1c}); shares level 0 0.1160, level 1 0.5001, level 2 **0.7773**
  (denominator 12,420 transfer and mint-heavy units; 7,470 merge-heavy units reported, outside the share).
- **Trailing-tercile inputs** (the rule is part `pre`'s: event's own terciles of `r` over ≥ 6 earlier traded intervals,
  `r_k` and later excluded): eligible units 32,365; thin history 12,475 (derived 38.5%); units with ≥ 6 prior
  intervals **19,890** in **2,419** events; classes transfer 5,822, mint-heavy 6,598, merge-heavy 7,470; within-event IQR
  of `r` quartiles `[0.416914, 0.69639397, 1.12773782]`. **No number from q0402 is carried into part C except the
  level:** the trailing cut points are per event and in-window (`[lookback floor, k)`), as declared.
- Worn-data gate inputs (reported): GCU OI changed in 49,841 of 57,425 traded non-sports event-intervals (86.8% ≥ 70%).
  GC inputs 2,419 events (≥ 600) and 19,890 units (≥ 10,000) in four worn days. Eligible splits: single 2,038, neg-risk
  multi 19,834, other multi 10,493.
- Thin history was 38.5% on four days, against the planning guess of 10-20% on 14 days; trailing history in SCREEN_8
  starts at the lookback floor, so the first SCREEN_8 days will be thinner than average (q0408 reports it).
- Planning SE (SE only): C1 on `C_pre` **0.060217c** (MDE 0.2288c, n 18,613), under the 1.0c gate.

### 11.4 Cost and lag map (q0403) cited in §2.1 and §3

- **Recipe** (an upper bound, part `pre` `COST_RECIPE`): entry at the ask walked to the far edge of the lowest depth
  band holding the position (ask + 1c or ask + 5c, else "not executable within 5c"), exit at the bid walked the same way,
  plus the taker fee `r·p(1 − p)` on both legs; first sweep of each of 42 passes; 246 cells (fee category × `P` band ×
  liquidity band {< $10k, $10-100k, ≥ $100k} × size {$1,000, $5,000}).
- **Executable within 5c** (derived sums over non-sports cells): at $1,000, 3.7% of books with liquidity < $10k, 13.5%
  at $10-100k, 92.5% at ≥ $100k; at $5,000, 0.4%, 3.8% and 64.4%.
- **Median round trip at $1,000, mid in [0.20, 0.80]** (cents per share; executable books / books), by liquidity band
  < $10k | $10-100k | ≥ $100k: politics 4.7 (385/15,456) | 4.9 (5,768/50,926) | 4.8 (2,101/2,152); crypto 6.4
  (6,197/137,340) | 10.0 (1,931/6,007) | 6.3 (42/42); finance 12.7 | 8.5 | 12.0 (8/24); economics 9.4 | 8.6 | 5.0;
  tech 8.7 | 4.9 | 4.5; culture 7.4 | 6.4 | -. Every cell is in the file; this table is a reading aid.
- **Monitor receipt lag** (`recv_ts − ts`, 37,598 prints): median **480 s** (p25 360, p75 720, p90 14,160); share
  > 300 s 77.6%, > 540 s 35.6%, > 2 h 13.1%; class medians 480-540 s; a 0-300 s polling component is included.
- **§2.1 (reported taker lines).** Each reported taker line (B2's follow and C1's follow at the decision ask/bid; A's
  fade is withdrawn) is printed next to the q0403 cell of its units (sidecar fee category × decision-mid `P` band ×
  liquidity band) at $1,000 and $5,000 (median, p75, share of books not executable within 5c) and next to the 4.5c /
  1.8c hurdles. Uncounted; no q0403 number enters any decision (O4). The "decision + 9 min" lag rule of §2.1 belongs to
  A's withdrawn fade; q0403's measured median is 8 min. Nothing changes.
- **§3 (econ hurdles).** B1-econ, B2-econ and C1-econ stay as declared: within-market (B) or within-event (C)
  differences of CB13-T3's recorded-touch round trip (fee from the sidecar rate, `max_if_unknown` 0.07, position
  `min(size, 100)`), cost-neutral to an exit cost common to both groups; hurdles are the §2.4 floors (difference
  ≤ −0.5c; flagged net ≤ −1.0c; p = the max). q0403 does not enter them. For context, each econ line also prints the
  q0403 cells of its fills: a 0.5c protection value is small against 4-13c executable round trips at $1,000 outside the
  most liquid books. Under branch T the econ fills are CB13-T touch-consistent fills; B1-econ's 300-fill minimum is very
  unlikely to be met (§CB17-B: planning about 130 per bin).

### 11.5 CB17-E inputs (q0400; reported, the rule is unchanged)

Touch-consistent (branch T) fills by market age: `< 6 h` 2, `6-24 h` 26, `1-7 d` 106, `> 7 d` 811, unknown 12; **7
markets** with first-day and later fills. All non-sports transactions with market age < 24 h: **200** in four days.
Side-signed population (not selected): 17 / 85 / 364 / 2,262 / 430 and 15 markets. Proxy SE on the pre-fill move: T
0.103191 (MDE 0.3921c, n 944, carried by the 7 both-period markets), S 0.57255 (MDE 2.1757c). Under the re-entry rule
(§CB17-E) a later CH154 test needs ≥ 400 first-day transactions in ≥ 150 markets that also print on days 2-7; four worn
days had 200 transactions and, among signable fills, 7 such markets. The counts bind on the signable population (O1
ruling, §11.8).

### 11.6 Rules parts

| Part | Status | Modules hashed | sha256 |
|---|---|---|---|
| `pre` | declared (committed before q0400) | `cb17_common`, `cb17_pre`, `cb17_census` | `ddc0249b23eedf8cfe50b2b60e94378264804ca4791c82c01cf3993df54df6a7` |
| `common` | declared (this rules commit) | `cb17_common`, `cb17_wcommon` | `2343744082bcb664ac06f18f967c166aae09c216e9437045d7aa07aa77ef8c9f` |
| `A` | **withdrawn uncounted (branch T); never declared** | - | - |
| `B` | declared (this rules commit) | `cb17_common`, `cb17_rules_b` | `64e61091574ec4406b6f235f48f37ab2d0bf8b41bf89bfbeace9153186c96a10` |
| `C` | declared (this rules commit) | `cb17_common`, `cb17_rules_c` | `3e24af26db1c827b6ff8dadc5bc63743a4cd03280d510211edf0ad87137b2647` |
| `E` | declared (this rules commit) | `cb17_common`, `cb17_rules_e` | `9b1eba65e5de9de0f67e31f9d7dccf6f012ef8ee37895a603aaa5a6103067412` |

| **O-rulings re-hash** (2026-10-20) | `pre` unchanged; `common` unchanged | `B`: `fd9ce65606ed94d90ecc9a364bf6f6ad99754ae3a8f77e1aa778f723ef28c4aa` -> `64e61091574ec4406b6f235f48f37ab2d0bf8b41bf89bfbeace9153186c96a10` (O9); `C`: `68bd50a2c33db7a50ae2a3efb411a629d7b251355784de50ed5433e59e4bf632` -> `3e24af26db1c827b6ff8dadc5bc63743a4cd03280d510211edf0ad87137b2647` (O11); `E`: `337382d63da11f724743b1969dff878ff6e92f536f245953a455bb2037301418` -> `9b1eba65e5de9de0f67e31f9d7dccf6f012ef8ee37895a603aaa5a6103067412` (O1 amended) | `seals/cb17_rules.json` regenerated with `run_cb17.py rules` (`c17.write_rules`, the tool that sealed it in e37643f3) after removing the unbound file; the table above shows the new shas |

**Pre-registered expectation (O3, O7; stated before any SCREEN_8 row exists).** B1's composition guard is expected to come out "uninformative"
(worn informativeness 8.6% against the 50% window rule); B1 is counted as declared and the verdict is expected in the ledger. B2's level-1 informativeness
margin (60.3% against the 60% selection margin) is informational. No rule changes in either case.

The parts bind once they land on the working branch after the orchestrator's acceptance (O2). Every window job
verifies `pre`, `common` and its family part (exit 2 on a mismatch).

### 11.7 Implementation notes that bear on the record

- **`cb17_common.py` is frozen under part `pre`** (every UPPER_CASE constant and non-machinery function is hashed), so
  §5's "cb17_common additions" live in a new module, `cb17_wcommon.py`, hashed by part `common` together with
  `cb17_common` (unchanged). Only the part-staging switches and the unhashed rules machinery of `cb17_common.py` change;
  a unit test asserts part `pre` still hashes to `ddc0249b…`.
- **Rules before code (§1.2 `T17_rules` versus `T17_code`).** Parts `common`, `B`, `C`, `E` hash the declarations:
  constants, the `declared()` text and small pure definition functions (event arm, age, state, target, class, worst-case
  bounds, gates). The window code (readers, frames, estimators, runner) is pinned separately at the code freeze by a
  code pin (`seals/cb17_code_freeze.json`), which q0406-q0412 require with the ruling-6 attestation. A code fix found in
  the freeze check therefore never changes a rules part.
- **`T17_rules`** is the time the parts become binding. `S_8 = max(2026-10-26T00:00Z, the first 00:00Z at or after
  T17_rules + 24 h)`, so any `T17_rules` up to 2026-10-25T00:00Z gives `S_8 = 2026-10-26T00:00Z`. The orchestrator
  records it in `seals/cb17_t17_rules.json` (O2).

### 11.8 Open questions for the orchestrator (nothing below was chosen silently)

- **Rulings 2026-10-20 (science-reviewer `CB17_OPEN_QUESTION_RULINGS_2026-10-20.md`, accepted by the orchestrator; outcome-blind and
  stricter, so rules-before-data; parts re-hashed, see the "O-rulings re-hash" row in §11.6):** O1 amended (re-entry counts bind on the signable
  population, all-transaction counts reported only); O9 (tick change is an availability status handled like "wide mark", primary sample ST_OK only, binding
  worst case takes the capture mark first, else the adverse bound; placebos, composition guard and attribution keep their exact index sets); O11
  (symmetric by class: transfer `min(p5, touch-C)`, mint-heavy and merge-heavy `max(p95, touch-C)`); O12 (the CB16 key pin is the sha256 copied verbatim from
  q0380's write-once manifest into q0405's spec and the ledger, never hashed from disk; without it q0405/q0406 stay pending (keys); "keys absent" only with a
  committed q0380 stop record under CB16's rules); O4, O5, O6, O8, O10 accepted; O3 and O7 informational. O2 is decided by the orchestrator (T17_rules = committer
  time of the commit that lands the final re-hashed parts on the working branch). The questions below keep their original text.
- **O1 (E re-entry population under branch T).** §CB17-E counts "first-day transactions" and "markets that also print on
  days 2-7" and asks for "a proxy MDE ≤ 1.0c". Read literally, the counts use all non-sports monitor transactions (no
  sign needed) and the MDE the signable (touch-consistent) fills (a sign is needed). Part E declares that literal
  reading and reports both counts on both populations; override before the part E commit if the touch-consistent
  population should bind the counts too. k = 0 either way.
- **O2 (`T17_rules`).** Is it the commit of the parts on the working branch (the merge), or this worktree commit? It
  moves `S_8` only if the parts land after 2026-10-25T00:00Z.
- **O3 (B1 informativeness).** 8.6% on worn data against the 50% window rule (§11.2). No change proposed; the rule
  stands and B1 is counted. Flagged so the expected "uninformative" verdict is anticipated in the ledger.
- **O4 (taker-line cost cell).** §2.1 says taker lines are "compared with q0403's cost at size" without naming the cell.
  Part `common` declares the unit's sidecar fee category × decision-mid `P` band × liquidity band, at $1,000 and $5,000,
  reported only.
- **O5 (module split).** `cb17_wcommon` in place of edits to the frozen `cb17_common`, and the rules/code split above.
- **O6 (float32 features).** B's activity and imbalance are cast to float32 before the frozen cut points are applied, to
  reproduce q0401's classification exactly.
- **O7 (B2 level margin).** B2's level 1 share is 0.6030, 0.3 points over the 60% selection margin. Informational; the
  rule is mechanical and the window's 50% rule binds as declared.
- **O8 (wild-bootstrap seed).** §2.3 names seed 1717 for A's cluster bootstrap and no seed for the Webb wild bootstrap
  of the small-G rule (the UTC-hour way, G = 24, is CR2 + wild). Part `common` declares 1717 for it (CB16 used its 1616
  for both).
- **O9 (B tick change).** §CB17-B lists "`tick_size` equal at decision and mark (else 'tick change', counted)" as
  eligibility, but the mark sweep is post-decision, the kind of selection finding 1 removed from C; a tick change
  happens when the price crosses into the extremes. Implemented as declared (excluded, counted by state bin). Should
  tick-change units instead join the no-mark / wide-mark worst-case bound?
- **O10 (econ tie rules).** B1-econ: the token's latest sweep in `[τ − 30 min, τ)` gives the book age (the design says
  "a sweep"). B2-econ: the most recent pass with `t < τ ≤ t + 2 h` and `|x| ≥ SD_x` defines the abandoned side (the
  design says "after a pass"). Declared in part `B`.
- **O11 (C one-sided worst case).** §CB17-C uses "the touch adverse to continuation" for every class. For transfer units
  that is hypothesis-adverse; for mint- and merge-heavy units (where high continuation is hypothesis-adverse) it is
  rarely "more adverse" than the 95th percentile. Implemented literally; confirm or name the favourable touch for them.
- **O12 (CB16 key file).** CB16 q0380 has not run (no `exclusion_keys.csv.gz` on the host), so its sha256 cannot be
  pinned in part `common`. Part `common` declares the pin as the sha256 in q0380's manifest, set in q0405's job spec
  (CB16's q0380 `--base-sha256` precedent); q0405 refuses while unset and records a q0380 stop record as "keys absent".

## 12. Window code record

Window code for q0404-q0412 (branch T: family A withdrawn uncounted, no A frame; B, C and the E census live; Holm k1 = 3). No rule, threshold, cut
point, alpha, Holm family or count was changed; all window code is pinned by the code freeze (`run_cb17.py code-pin`), not by a rules part.

- **Modules:** `cb17_win.py` (readers with time floors, code pin, freeze/T17/results-copy gates, FE/cluster engine, guards, write-once outputs), `cb17_b.py`,
  `cb17_c.py`, `cb17_e.py` (frames), `cb17_smoke.py` (q0404 fixture checks and exact P1-P3 reproduction), `cb17_jobs.py` (q0404-q0412 job logic),
  `scripts/run_cb17.py` (subcommands `smoke`, `exclusion-keys`, `frame`, `census`, `screen`, `rep`, `stage2-final`, `code-pin`).
- **Tests:** `tests/unit/test_research_lab_cb17_win.py`, `_jobs.py`, `_probe_ports.py`, with `tests/cb17_wsynth.py` (synthetic worlds only; no host,
  SCREEN_8 or REP_8 file was opened or fetched).
- **Refusals covered:** not-before gates (exit 75, nothing written), A withdrawn, unset pins (`TODO-COORDINATOR`), missing smoke, ruling-6 attestation,
  stale code pin, rules-part mismatch, declared disk/data-dumps caps, test hooks outside `--allow-uncommitted-rules`, write-once results, REP rows closed
  until the committed results copy exists, counts-only census.
- **Queue drafts:** `queue/drafts/q0404-q0412_cb17_*.json`, argv parsed by the runner; DRAFT, not in `queue/jobs/`; q0406/q0407 `not_before` 2026-11-09T08:00Z,
  q0410 2026-11-23T08:00Z (recompute if S_8 slides). q0407's file name keeps "A" but the job is the E screen frame.
- **Open questions for the freeze check:** the pin tokens `TODO-COORDINATOR` (q0405 base sha, q0411 results sha) are refused until pinned; the code-freeze
  and T17 records must be committed by the coordinator; the q0407 draft id naming; O1-O8 above stand unchanged.

### 12.1 Freeze-check fixes (2026-10-20, `CB17_WINDOW_FREEZE_CHECK_2026-10-20.md`, fixes 1-7)

Mechanical only; no rule, threshold, cut point or count changed (`cb17_wcommon` and the rules parts are untouched, so the part shas stand; only the code pin moves).

1. A missing monitor day file, or a complete capture / declared sweep whose row files are gone, is exit 75 ("restore byte for byte, hash-checked, restore_from_archive.py"), never skipped, unless a
   committed `seals/cb17_monitor_stopped.json` (`{"stopped_days": ["YYYYMMDD", ...]}`) covers that day (monitor days only). The REP seal's source table covers every declared day / capture / sweep file.
2. q0404 is gated on the committed code-freeze record (`gate(attest=False)`) and stores `code_sha256`; every later frame job refuses a `smoke.json` of other code.
3. `b0`, `a0` are float64. 4. Unknown is never met: a robustness variant that is `None` and an untestable pre-period placebo are "not met" (`win.robust_met`, `win.placebo_holds`).
5. The econ event minimum counts events among flagged fills only. 6. q0406 writes the B frame with its own manifest status (`frame_b_complete`) before C; a budget stop resumes at C.
7. Every job enforces `--disk-cap-gb` allowance and the 0.3 GB `creative_batch17` total (frame outputs are checked against their cap before the manifest); q0412 verifies the rules parts, the code pin and the T17 record.
   Disclosure: a calibration draw that cannot be computed counts as "not advancing" (p = 1, CB16's `placebo_advance_rate` precedent, `cb17_wcommon.calibration_placebo`); this is the declared rule and is unchanged.

Smoke inputs: `smoke --worn-sha256 FILE` refuses (exit 2) unless every worn file is pinned and matches (keys are archive-relative: `live_trades/trades-YYYYMMDD.jsonl`, `snapshots/<capture>/rows[_ext].csv.gz`,
`book_sweeps/<sweep>/rows.csv.gz`, `creative_batch13/t_screen/fills.csv.gz`); `worn-manifest` prints that map; `--snapshot-root` / `--live-trades-root` point the smoke and `worn-manifest` at a byte-for-byte
restore tree (directories must be named `snapshots` / `live_trades`; the pin check applies to whatever root is used). Tests: `tests/unit/test_research_lab_cb17_fixes.py`.

Open, unchanged and not decided here: O2, O9, O11, O12 and the monitor storage cap (ruling 7); O1, O4, O5, O6, O8, O10 await explicit acceptance.
