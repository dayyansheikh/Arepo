# Creative batch 16 (CB16): quoter grain, wake-up prints (relative large-print silence in active markets), the Kalshi-absent map (census only); hedging skew withdrawn

`evidence_role: prospective` (CB16-Q and CB16-U: both stages run on live host windows that start after the freeze) /
`exploratory_historical` (CB16-K census, counts only) | status: **DRAFT-REVISED after challenger round 1 (Q REVISE,
U REVISE, K ACCEPT with fixes, H WITHDRAWN uncounted; 20 items: 17 adopted, 3 adopted with a stated modification, none
rejected; §9-§10). Design only. Nothing frozen, nothing queued, no code.** Drafted 2026-10-19 10:20 UTC+1
(2026-10-19T09:20Z) on parent `ca8468c` and committed as `f78a396`; round-1 response 2026-10-19 (§10). Every round-1
change tightens, clarifies or withdraws; no floor, threshold, gate, alpha or cap was relaxed.
**No CB16 quantity has been computed:** no mark-out, slope, contrast, Brier residual, touch outcome or net.
For CB16, only two read-only, counts-only host probes were run (§0.3). Nothing was fetched, written, moved or deleted on
the host.

This file turns four round-7 ideas from `CREATIVE_HYPOTHESES_2026-10-21.md` into declared, falsifiable designs:
- **CH131** (quoter-type footprint) becomes **CB16-Q**.
- **CH132** (wake-up prints) becomes **CB16-U**.
- **CH143** (the Kalshi-absent class map) becomes **CB16-K**. K is a **census only, with no counted test**: its own
  population count already rules out power (§0.3, §CB16-K).
- **CH138** (hedging-premium skew) was drafted as **CB16-H**, nested behind CB13-R. **Round 1 withdrew it, uncounted**
  (item 17): no CB13-R result exists, no H rule ever bound, and no H outcome, price or statistic was seen. Only a
  fresh-frame re-entry note remains (§CB16-H).

The file follows `CREATIVE_BATCH_15.md` (CB15) and `CREATIVE_BATCH_13.md` (CB13) in structure and rules. "As CB15 §x"
means that rule applies unchanged, including the challenger and freeze-check fixes it inherits from CB13 and CB14. CB4
amendment A-C1 and the CB10 §2.3 small-G rule govern clusters.
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim. AREPO never
  trades. Every P&L is a paper rule at recorded prices (prints and capture touches).
- Test tables bind only once the CB16 declaration hash is committed (`model_specs/cb16_v1.json`). That needs a challenger
  round (§7) and a code-against-design freeze check first. Rules are fixed in `seals/cb16_rules.json`, **hashed per part
  (`common`, `A` for Q and U, `K`)**. A and K therefore bind on their own calendars, and no rule of one part
  changes after another part's read.
- **Lanes.** Q, U and K need **no network**. They run on the `cpu` lane on files already on the Oracle host, or on files
  the running collectors will write. Two jobs touch the network:
  - the exclusion-key increment q0380 (Gamma ids only);
  - the U validity sample q0389 (reported only; Data API).

  Both run on the `net` lane at **priority 5-9, below every CB6-CB15 job**. No CB16 object is bound to `T_seal`, and no
  CB13, CB14 or CB15 job waits for CB16.
- **Queue ids q0380-q0409, one id per job, no letter suffixes.** CB15 §0.1 reserves q0340-q0379, so CB16 starts at
  q0380. Checked at the round-1 response: `queue/jobs/` and `queue/drafts/` hold CB15's q0340, q0341 and q0343-q0346 and
  nothing above q0346 (round 1 item 19; the draft's "nothing above q0323" was wrong). Used: q0380-q0389 and q0392;
  **q0390 and q0391 (withdrawn H) are retired, never re-used; q0393-q0409 reserved**. Specs are drafts **in this document only** (§4).
- **Naming.** Outputs go under `research_lab/creative_batch16/`. CB16 writes no `history/` root: Q, U and K fetch
  nothing, and q0389 writes only under `creative_batch16/u_validity/`.

## 0. Summary, selection and scope

| Rank | Family | Hypothesis | Counted tests | Stage 1 data | Stage 2 data | Queue ids |
|---|---|---|---|---|---|---|
| 1 | **CB16-Q** quoter grain (CH131) | Among large taker transactions that fill a resting quote (CB13-T's frozen print-anchored, touch-consistent fill rule), fills whose maker-adverse price `P` is on a **sub-cent grain** ("bot-grain") have a better 2-4 h maker mark-out than **whole-cent** fills ("human-grain") in the same market. The test is a within-market contrast of at least +0.5c per filled share (Q1) | Q1 (within-market grain contrast) | host files only: live-monitor prints and complete-universe captures in **SCREEN_A**, a 14-day live window that starts after the A freeze | the same stores in **REP_A**, the next 14 days: Q1-rep; Q2 (maker round trip at the recorded print and touch, on bot-grain fills) | q0381, q0382, q0384-q0388, q0392 |
| 2 | **CB16-U** wake-up prints, **relative large-print silence in active markets** (CH132) | In markets with at least 5 large prints in the prior 7 days, the longer the silence before a large print, measured against the market's own large-print inter-arrival times, the worse the maker's 2-4 h mark-out on that fill (within-market slope ≥ 0.5c per SD of standardised log-silence; U1) | U1 (within-market slope) | as Q (the same fills; silence comes from the monitor stream) | REP_A: U1-rep; U2 (avoided-fill economics of a paper maker that steps aside for 2 h after a wake-up print) | q0381, q0384-q0389, q0392 |
| - | **CB16-K** Kalshi-absent map (CH143) | **Census only (k = 0).** Counts twin labels (strict matcher, loose topic rule, Kalshi-unlistable text rule) by class × volume-decile cell, plus feature-free MDE bounds. No outcome and no price is read | none | the host's `cross_venue/` files (148,384 Polymarket markets; 326,380 Kalshi markets; 958 matches), counts only | none (a counted design waits for a later batch, §CB16-K) | q0383 |
| - | **CB16-H** hedging skew (CH138) | **Withdrawn uncounted in round 1** (item 17): planning MDE 12-20c against a 4c gate, and a trigger on CB13-R1's outcome on the same units is post-selection. Fresh-frame re-entry note only | none | | | q0390, q0391 retired |

**Counted: 2 fixed (Q1, U1) + up to 4 conditional (Q1-rep, Q2, U1-rep, U2) = 2-6** (§2.5). **k1 = 2** (family A). The
change from the draft's 2-8 comes only from the H withdrawal (no H outcome, price or statistic was seen), not from any
power or Holm consideration. The budget is fixed now, and no CB16 test is added after any CB16 read.

**Honest expectation.**
- **U1** is the only test whose planning MDE lies at or below its floor.
- **Q1** is borderline: planning MDE 0.55-1.1c against a 0.5c floor, with a 1.0c power gate.
- **K** cannot be powered with any feasible data: 92 non-sports events hold a strict Kalshi twin (§0.3).
- **H** is withdrawn (round 1 item 17).

### 0.1 Queue id mapping (one id per job)

| Id | Job | Family | Earliest commit |
|---|---|---|---|
| q0380 | `cb16_exclusion_keys` (CB15 q0340 key file + CB15 frames + seal copies, per-key source attribution) | A (window check), K (overlap counts) | after CB15 q0340 completes (or its ledger stop record) |
| q0381 | `cb16_smoke` (`cpu`, **no network**: parts A and K; §CB16-SM) | A, K | after the `common`, `A`, `K` rules parts and smoke code exist |
| q0382 | `cb16_q_grain_census` (counts only, CB13-T SCREEN fill features: grain shares, both-grain markets; gate GQG) | Q | after q0381 PASS and CB13 q0271 complete (or the pinned fill functions on raw SCREEN files) |
| q0383 | `cb16_k_census` (counts only: twin labels, cells, MDE bounds; no outcome, no price) | K | after q0380 and q0381 PASS |
| q0384 | `cb16_a_frame_screen` (SCREEN_A fill table, features only; silence features; no mark) | Q, U | not before `S_A + 14 d + 8 h` |
| q0385 | `cb16_census_A` (counts; gates GQ, GU, GQP, GUP, GAI pre-count; MDEs) | Q, U | after q0384 |
| q0386 | `cb16_screen_A` (Q1, U1; gate GAI) | Q, U | after q0385, the A freeze, E011's one-time analysis commit and CB3's freeze commit (or stop record) |
| q0387 | `cb16_a_frame_rep` (REP_A fill table and raw mark-quote table, features only; sha256-sealed) | Q, U | not before `S_A + 28 d + 8 h` |
| q0388 | `cb16_rep_A` (Q1-rep, Q2, U1-rep, U2) | Q, U | only if Q1 or U1 advanced; after q0387 |
| q0389 | `cb16_u_validity` (`net`, Data API all-size silence on a seeded sample of SCREEN_A units; **reported only**) | U | after q0384 |
| q0390 | retired (withdrawn H; never re-used) | - | - |
| q0391 | retired (withdrawn H; never re-used) | - | - |
| q0392 | `cb16_stage2_final` (one CB16-wide strict Holm over triggered Stage-2 tests; write-once) | all | after every triggered Stage-2 test is final |
| q0393-q0409 | reserved | - | - |

### 0.2 Selection and scope

**Ranking rule.** As CB15 §0.2, with this brief's preferences:
- (a) ideas testable on data already on the collection host, or that its running collectors will write;
- (b) round-7 rank;
- (c) side-free and wallet-free designs.

**No CB16 statistic reads the Data API `side` field or any wallet field.**

**What the drafting session read (2026-10-19T08:50-09:20Z).**
- Instructions and ledger: CLAUDE.md, AGENTS.md; the ledger's governance header and its last 200 lines (CB12-X closed
  not identifiable; the CB13 freeze-check and fix rounds; the CB14 freeze check; the CB15 draft).
- Round 7: §0 (facts 1-12, data labels, hygiene), §2 (CH131, CH132, CH138, CH142, CH143), §3 (ranking, screen sketches,
  registration notes).
- Templates: CB15 §0-§8 in full; CB13 §0-§2 and §3 (CB13-T's fill anchor, mark rules and labeller; CB13-R's units,
  anchor, GRP and power), §7, §9-§11.
- Host and data: `COLLECTION_HOST.md`; `CROSS_VENUE_STUDY.md` §1-§3 (the matcher; the Kalshi universe);
  `run_cross_venue.py` (file names); `flow_screen.py` (F3), the HB1 table (IX3), `detector_specs/FROZEN.json` and
  `if_h1_hist_v1.json` (for the CH132 prior-work check); CB3's dates (`T3_rep_start`).

**Prior work.**
- *Q.* No AREPO test has used the price grain of the resting quote as a state variable. CB13-T splits maker mark-outs
  by resolution class. CH80 is dust at the touch, CH111 the taker's size shape, CH39 the post-print retreat. CB3-B filters
  the maker by print size, life stage and round-trip flow. E003 (book imbalance) was inconclusive.
- *U (CH132's kill criterion is a prior-work check; the drafter's pre-check finds it **not met**).* Three neighbours
  exist, and none conditions a large print's own mark-out on the silence before that print:
  - `flow_screen` F3 adds `log1p(time_since_last_trade_s)` as a feature of a pooled reversal ridge for the next-snapshot
    mid change at trade-sample origins.
  - HB1 IX3 conditions 6 h flow continuation on a quiet market (24 h notional below its own 29-day median). It found
    −0.17c, **opposite** to its theory prior. That sign is disclosed here as a prior against CH132.
  - `sm_learned_v2` (E011) uses `last_trade_age_h` as a detector feature, and the ledger notes that E011 "mostly finds
    quiet markets that then move" (handled in §1.3).
  - **HB1 MS2** (round 1 item 12; `HYPOTHESIS_BATTERY_1.md` lines 143 and 361) tested whether `log1p(hours since last
    trade)` adds to M0v for the **unsigned** 6 h move `|move|` (ΔLL +0.00108, CI [+0.00025, +0.00213]; it failed BY).
    It is a neighbour, not a re-run: an unsigned magnitude model on `h2_main`, not the signed maker mark-out of a print
    conditioned on the silence before it.

  IF-H1's `dormant` concerns wallets, not markets. The formal check was done in challenger round 1 and found no
  re-run (§9 item 12).
- *K.* CH25 is the sign of the Polymarket-Kalshi level gap on politics. The C1 study, CB5-K, CB12-X, CB15-P and
  E009/E010 use matched pairs for leads, gaps and births, never for calibration by twin presence.

`battery2.cumulative_count()` (`battery2-count-v1`) gives **1,255** on HEAD at drafting. It is not stable, so every
counting CB16 job records the value at its run, after the host union.

**Premises corrected or fixed by the probes and reads (they shape this design).**
1. **The grain is informative, and it is read from the print, not from the touch.** In CB13-T's SCREEN window, 36% of
   non-sports enriched prints priced in [0.05, 0.95] sit on a sub-cent grain (1,138 of 3,131), and 32% of unenriched
   prints do (§0.3, G1). CH131's first kill (third decimal 0 in more than 95%) is therefore not met on prints. **The
   maker-adverse price `P` of a touch-consistent transaction is the price of the best resting order the taker lifted**
   (the first level of the sweep). Its grain is the resting quote's grain at the print, exactly. The 2 h capture touch
   (up to 60 min old) is not needed for the grain, only for signing the fill, as in CB13-T. In the tails (outside
   [0.05, 0.95]) every market quotes on the 0.001 tick and 83% of non-sports tail prints are sub-cent, so the tails are
   excluded from Q.
2. **Shape is not observable at the needed detail.** Sweeps carry `bid_size_1`, `ask_size_1`, `depth_*_1c`, `depth_*_5c`
   and `n_*_levels`, not the top-3 level sizes. CB13 H7 found sweeps missing for about half of sports and most crypto
   prints, and a sweep is up to 2 h old. CH131's shape arm (top-3 size CV) cannot be computed, so a reduced shape
   descriptor is **reported only** (§CB16-Q).
3. **Silence is measured on the large-print stream.** The monitor sees only prints of $1k or more. U's silence is
   therefore "large-print silence", and it says so in its title. The ≥ 5 prior-gap rule (§CB16-U) further restricts U to
   markets that are active on that stream, so the title reads "relative large-print silence in active markets" (round 1
   item 9). The trade samples record `time_since_last_trade_s` at
   sampled origins, not at an arbitrary print, so they cannot give the silence before a print. An all-size check is a
   reported Data API sample (q0389).
4. **Q and U Stage 1 cannot use CB13-T's windows.** CB13-T's SCREEN (`[10-12, 10-16)`) is worn by CB13-T and by this
   draft's grain probe, J4-R (`[10-16, 10-21)`) is refused, and CB13-T's HOLDOUT (`[t_j4r_end, 10-26)`) is sealed for T.
   Q and U therefore screen on **SCREEN_A**, a fresh 14-day window that starts after the A freeze, and replicate on the
   next 14 days (**REP_A**). Both windows hold data that do not exist at the freeze. The cost is calendar time, not data.
5. **K's present arm is tiny.** `matches_all.json` holds 958 strict matches, of which 688 are sports. **The 270
   non-sports pairs sit in 92 Polymarket events** (Elections 102 pairs / 41 events, Entertainment 88 / 22, Mentions 43 /
   20, Politics 23 / 5, Science and Technology 9 / 3, Financials 5 / 1; §0.3, G2). The matcher's recall is low by
   design: no macro pair matched even though Kalshi lists those events. CH143's own kill (at least 5 cells holding both
   labels with at least 30 events each) cannot be met with strict labels. The round-7 count table's "A only" was
   optimistic in two ways:
   - The host holds no T−24h price for the historical universe. Captures start 2026-10-10, and the pair series cover
     the 493 selected pairs only.
   - Captures carry no twin label for markets resolving after 2026-10-10.
6. **H's within-event pairing doubles the path noise rather than cancelling it.** One weekly spot path raises the reach
   outcomes and lowers the dip outcomes together, so `Δ_Y = reach(Y − p) − dip(Y − p)` carries roughly twice each side's
   path shock. Its honest unit is the asset-week. This is the main reason H was withdrawn in round 1 (§CB16-H).

### 0.3 Feasibility probes (counts only; 2 read-only host probes; 0 keyless GETs; nothing stored)

Both probes ran over `ssh oracle` as `nice -n 19` streaming Python, with the script in `/tmp`. Peak memory was under
200 MB. Nothing in `~/arepo/run/queue` was touched. **No outcome, resolution, mark-out, forward price or wallet was
read or printed.**

**Audit trail (round 1 item 18).** The drafting session deleted the `/tmp` scripts after running them, so the claim
above was unauditable at `f78a396`. The exact script texts, every run in order (including one empty stub run and one
superseded run with a wrong sports split) and the raw printed counts are now committed in
`docs/research_lab/probes/cb16_design_20261019_probes.txt`. **Residual limitation, stated plainly:** the texts are
reconstructed from the drafting session's own record. The bytes that ran on the host no longer exist and have no hash,
so "no outcome seen" rests on that reconstruction and is not independently verifiable. Both scripts decoded whole
records in memory (including the forbidden `side` and `wallet_*` fields of monitor prints and the hindsight `p_end` of
`matches_all.json`) and printed only counts. Future CB16 probes are committed before they run.

Disclosed feature exposure:
- G1 read the `price`, `ts`, `condition_id`, `tx16` and `ctx_category` of CB13-T SCREEN prints. These are the same
  feature class CB13 H6-H8 had already disclosed. G1 computed the third decimal of each price and the gap since the
  previous large transaction in the same market.
- G2 decoded each `matches_all.json` row in memory and printed only the key names and the counts by `k_cat`. Its `p_end`
  field (hindsight close) was decoded but never read.

| # | Probe | Finding |
|---|---|---|
| G1a | `live_trades/trades-20261012..15.jsonl`, prints with venue `ts` in `[2026-10-12, 2026-10-16)` (CB13-T SCREEN), price grain by `ctx_category` and price band | Non-sports enriched, price in [0.05, 0.95]: **sub-cent 1,138, whole-cent 1,993 (36% sub)**. Non-sports tails: sub 1,628, whole 329. Unenriched (`ctx_category` null), [0.05, 0.95]: sub 1,384, whole 2,941 (32%). Sports (`sports_fees*`), [0.05, 0.95]: sub 4,967, whole 15,265 (25%). Categories: `sports_fees_v3` 25,236, null 6,518, `crypto_fees_v2` 1,251, `politics_fees` 1,139, `sports_fees_nfl_cfb_oct26` 873, `economics_fees` 763, … (prints include 0.01-tick markets, where sub-cent is impossible) |
| G1b | the same prints aggregated by (market, `tx16`); gap to the previous large transaction of the market inside the window | Non-sports enriched: < 1 h 2,291; 1-6 h 811; 6-12 h 273; **≥ 12 h 459**; first in window 1,223. Unenriched: 3,625 / 461 / 126 / **127** / 1,950. Sports: 21,599 / 1,402 / 206 / 195 / 2,869. Wake-ups of at least 12 h number about 150 a day outside sports |
| G2 | `cross_venue/matches_all.json` (key names; counts by `k_cat`; distinct `p_event_id`) and `ls` of `cross_venue/` | 958 pairs; Sports 688 / 284 events; **non-sports 270 pairs / 92 events**. The Kalshi universe files (`kalshi_markets*.jsonl`, about 180 MB) and `poly_markets.json` (171 MB) are on the host. `df`: 57 GB free; data-dumps 16 GB |

### 0.4 Selection decisions

| Idea | Decision | Reason |
|---|---|---|
| **CH131** quoter grain | **include (Q), counted, post-freeze live windows** | Host-only. Premise 1 makes the grain an exact attribute of the lifted quote. It reuses CB13-T's frozen fill and mark rules, so no new fill logic is invented. Honest weaknesses: grain is a noisy proxy for quoter type, since bots also quote whole cents and a person can type 0.555. Grain also co-moves with spread state and price level, so a composition placebo and an attribution regression bind. Power is borderline (§CB16-Q) |
| **CH132** wake-up prints | **include (U), counted, same windows as Q** | Host-only. The prior-work pre-check passes (§0.2; HB1 MS2 disclosed), and the population is large (G1b). Honest weaknesses: this is relative large-print silence in active markets, not market silence, and dead books (CH132's literal object) are mostly excluded by the ≥ 5 prior-gap rule (premise 3; round 1 item 9). HB1 IX3's opposite sign is a prior against it. Scheduled events wake markets for public reasons, which dilutes the effect but does not bias it |
| **CH143** Kalshi-absent map | **census only (K, k = 0)** | The strict present arm holds 92 non-sports events (G2). The planning MDE is about 4-6 pp against the 1 pp floor (§CB16-K), and at the historical rate of about 90-100 strict non-sports twin events a year, no feasible prospective collection reaches about 360. A counts-only census of a loose topic-twin label, audited, decides whether a counted K is worth designing in a later batch. No outcome is read, so that later design stays blind |
| **CH138** hedging skew | **withdrawn uncounted (round 1 item 17)** | Drafted as conditional on CB13-R1. Round 1: the planning MDE (12-20c) is 3-5 times the 4c gate, and triggering on R1's outcome on the same units is post-selection. No R result exists and no H rule bound, so the withdrawal is outcome-blind (CB15-L precedent). Re-entry only on a fresh frame (§CB16-H) |
| CH142 series launch window | not in CB16 | Its descriptive arm is host-only, but "first event" needs a `/series` fetch and its anchored arm needs each family's anchor. It is a map, so it goes to a later batch with CH143's topic census |
| CH139, CH134, CH135, CH136 | not in CB16 | Each needs a fresh keyless fetch (`h15_*`), a calendar source or a per-country adapter. The brief asks for host-testable ideas |
| CH133 depth fade | not in CB16 | Sealed stream (E009/E010 to 2026-11-03). Re-entry after their analyses are committed |
| CH137, CH140, CH141 | not in CB16 | Thin populations by round 7's own counts |

**Sports and categories.** `CB16_SPORTS_IN_PRIMARY = false` (a parameter, as in CB8-CB15). Q and U exclude the pinned
CB13 LABELLER's SPORTS-FEED class from the primary and report the sports arm uncounted. A counted sports arm would be a
later registration, never a change to CB16. Every Q and U statistic is also reported, uncounted, by LABELLER class. K
cells are LABELLER class × volume decile.

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Prior use | Role in CB16 | Evidence ceiling |
|---|---|---|---|
| `live_trades/trades-YYYYMMDD.jsonl` (host; live large-trade monitor, cash ≥ $1,000) for `[S_A − 7 d, S_A + 28 d + 8 h)` | collection tooling; CB13-T uses `[10-12, 10-16)` and `[t_j4r_end, 10-26)` | **Q and U units**: fills (CB13-T rule) and large-print silence. Whitelisted fields only (§1.4). The lookback before `S_A` reads `ts` and `condition_id` only | SCREEN_A and REP_A: post-freeze live data (L2 data; Stage-1 screen role on SCREEN_A) |
| `snapshots/<capture>/rows.csv.gz`, `rows_ext.csv.gz` (complete-universe 2 h captures) for the same span | E001-E011, CB1-CB13 | the touch that signs a fill; tick size; mark quotes; labeller sidecar fields | as above |
| `book_sweeps/` (same span) | E003, CB3, CB13 (depth, reported) | Q's reduced shape descriptor, **reported only** | - |
| CB13-T SCREEN fill table (`creative_batch13/`, q0271 output; features only) or the raw `[10-12, 10-16)` files through the pinned CB13 fill functions | CB13-T Stage 1 | **q0382 grain census only** (grain shares, both-grain market counts). Never a Q or U statistic | counts |
| `cross_venue/poly_markets.json`, `kalshi_markets*.jsonl`, `matches_all.json` (host; 2026-10-12; sha256 pinned at q0381) | C1 study, CB5-K, CB12-X, CB13 (H10, labeller writing), CB15-P | **K census**, field-restricted: Polymarket id, question, event id and title, scheduled `endDate`, neg-risk ids, lifetime `volume` (cell variable, hindsight, labelled); Kalshi ticker, title and subtitle text, `close_time`, category, `volume`; match ids. **`outcome_prices`, `closed_time`, Kalshi `result` and `settlement_value` are never parsed** | counts |
| Data API `/trades` (q0389; public, keyless) | many | all-size silence before a seeded sample of SCREEN_A units: prints before `τ` only, `ts` and price only. **Reported validity line** | - |
| `surprise_live/` (E011), `cross_venue_live/` (E009/E010), `e001/`-`e007/`, `forecasts/`, `flow_screen/`, `trade_samples/`, `cb3_extract/`, `cb3_followup/`; `live_trades/{alerts,outcomes,wallets,stats}.jsonl`, `scores-*.jsonl`, `state.json`; every `h15_*` root | registered experiments, monitor alert stream, other batches | **never opened by any CB16 path** (runner refuses; unit-tested) | - |
| `h1_*` … `h14_*`, every `creative_batch1..15/` except the CB13-T fill table for q0382 | worn, sealed or batch-owned | **not read**, except id and timestamp columns for exclusion keys through a field-restricted accessor; no `holdout/` path | - |

**Reuse disclosure.**
- *Q and U:* SCREEN_A and REP_A do not exist at drafting. They are collected by the running collectors and read under
  a frozen plan. They overlap other batches' live stages in time (§1.3).
- *K:* the files are worn: the C1 pairs drive E009's design, CB5-K, CB12-X and CB15-P. K reads only ids, texts, dates
  and volumes, and writes counts.

### 1.2 Dates (declared; UTC)

| Name | Value | Meaning |
|---|---|---|
| `T16_draft` | 2026-10-19T09:20Z | this draft; no CB16 quantity computed |
| `T16_A_freeze` | target **2026-11-01T00:00Z** (soft) | part A frozen (`model_specs/cb16_v1.json` part A, pinning the rules and the CB13 functions it calls) |
| `S_A` | `max(2026-11-02T00:00Z, the first 00:00Z at or after T16_A_freeze + 24 h)` | start of SCREEN_A. It depends only on the freeze time, never on data |
| SCREEN_A | fills with venue `τ ∈ [S_A, S_A + 14 d)` | Q and U Stage 1 |
| REP_A | fills with `τ ∈ [S_A + 14 d, S_A + 28 d)` | Q and U Stage 2, **event-disjoint from SCREEN_A, binding even if thinned** (round 1 item 20; §CB16-Q). SCREEN_A spans the US election run-up and REP_A the post-election resolution wave, so the politics share (LABELLER SCHEDULED-EVENT and `politics_fees`) is reported per window |
| U lookback | large prints with `ts ∈ [max(τ − 7 d, 2026-10-26T00:00Z), τ)`; fields `ts`, `condition_id` only | silence standardisation. **The floor 2026-10-26T00:00Z keeps every lookback outside J4-R and CB13-T's HOLDOUT** |
| election-night exclusion | fills with `τ ∈ [2026-11-03T18:00Z, 2026-11-05T00:00Z)` | excluded and counted (CB15-E's object window and a one-off regime). Silence that spans it is measured as usual |
| marks | first complete capture with `received_utc ≥ τ + h`, usable iff `received_utc ≤ τ + h + 2 h` (CB13 §2.2) | realised 2-4 h ("2 h") and 6-8 h ("6 h") |
| `T16_K_census` | after q0380 and q0381 PASS | K is counts only; K units are historical (scheduled `endDate` in `[2025-10-13, 2026-10-01)`) |
| E011 | registered window to 2026-11-10; analysed once after 2026-11-11T13:00Z | q0386 refuses before E011's analysis commit (ledger). SCREEN_A ends after 2026-11-15, so this costs no time |
| CB3 Stage 2 | `[T3_rep_start ≥ 2026-10-27, …)` | collection overlap only; q0386 and q0388 require CB3's freeze commit or its ledger stop record (as CB13 `T13_T_rep`) |
| J4-R / CB13-T HOLDOUT | `[2026-10-16, 2026-10-21)` / `[t_j4r_end, 2026-10-26)` | no CB16 path reads any row timed inside either |

### 1.3 Sealed and untouched data (named)

- **Refused roots.** `run_cb16.py` refuses every root in the last two rows of §1.1. It writes only under
  `research_lab/creative_batch16/`. The Q/U readers refuse any print, capture or sweep timed before 2026-10-26T00:00Z,
  except the q0382 census path, which reads CB13-T SCREEN features only. They also refuse any REP_A row unless the
  SCREEN_A result file and `seals/cb16_a_rep_SEAL.json` are committed and their hashes verify.
- **E011 (registered to 2026-11-10; analysed once after 2026-11-11T13:00Z).** SCREEN_A overlaps E011's window, and U's
  object (silence, then the move) is close to what E011's detector finds (quiet markets that then move). **Why U does not
  contaminate E011:**
  - E011's analysis is frozen code, run once, and q0386 runs only after it is committed.
  - U never opens `surprise_live/`, never computes the detector score or surprise labels, and never joins to alert,
    candidate or control status.
  - No U output defines an E011 subgroup, and the E011 report may not cite U.
  - Captures are read-only, so E011's inputs stay bit-identical.
- **E004-E007.** CB16 never opens `e00*/` and never parses `chg_1h`. U's silence is not E007's signed flow.
- **E009/E010.** No CB16 path opens `cross_venue_live/`. K reads only the 2026-10-12 historical files, which were
  written before E009's registration. No K output defines an E009/E010 subgroup.
- **CB13-T.** Its windows are untouched (§1.2). Q and U import CB13-T's fill, touch-consistency and mark functions and
  its LABELLER **by pinned sha256** (whatever the CB13 freeze pins at the time of CB16's rules commit). No CB16 output
  pools with, conditions on or cites a CB13-T result. If CB13-T's GL labeller audit fails, Q and U still use the
  LABELLER's SPORTS-FEED class only (Q and U need no LOW/NEWS split), and the per-class reports carry the label
  "labeller unaudited".
- **CB3 (Stage 2 from at least 2026-10-27).** CB3-B's Stage-2 maker mark-outs are the quantity closest to Q's and U's on
  the same days. CB3 is frozen before its Stage 2, so its tests cannot change. CB16 never opens `cb3_extract/` or
  `cb3_followup/`, and its screens wait for CB3's freeze commit or stop record (§1.2).
- **CB13-R.** No CB16 path opens `h13_touch` or `h13_binance` (H withdrawn, round 1 item 17).
- **CB15 (E collector 2026-11-02..06; P watcher from 2026-11-04).** CB16 reads none of CB15's stores. The
  election-night exclusion removes Q/U fills on CB15-E's night.
- **Other live stages** (CB14-W live from 2026-10-26, CB14-S Stage 2, CB12-E/O live, CB10-D q0210, CB9-P Stage 2,
  CB13-T Stage P if triggered) may collect inside SCREEN_A or REP_A. This is collection overlap only, as CB13 §1.3:
  their markets are not excluded, their stores are never opened, and the census reports how many Q/U fills fall in
  markets those stages name where their frames exist.
- **Exclusion keys (q0380).** Union of:
  - (1) CB15 q0340's `exclusion_keys.csv.gz` (sha256 pinned; source-attributed);
  - (2) CB15 frame ids: the E race map, P pairs and P Stage-2 pairs, as CB15 §1.3 requires;
  - (3) every seal copy under `docs/research_lab/seals/` committed by then.

  Keys are market id, Gamma event id, `negRiskMarketID` and series id. **Q/U rule (as CB13-T):** a market or event id
  is dropped only if it appears in a sealed historical set with a stored timestamp inside SCREEN_A or REP_A. None is
  expected, because live prospective stages are collection overlap; drops are counted by source. **K:** keys are used
  for **overlap counts only** (K computes no statistic). **CB17 must add CB16's frame ids** (SCREEN_A and REP_A fill
  markets and events).
- **Outcome guards.** Q and U have no resolution outcome (mark-outs are price-based; Q2 and U2 exit at a recorded touch).
  K reads no outcome.

### 1.4 Rules files

- `seals/cb16_rules.json` (before q0381), hashed per part:
  - **`common`**: refused roots; seeds; bootstrap and small-G settings; Holm settings (k1 = 2 for family A); disk guards; field whitelists; smoke criteria; the key rule; the pinned sha256 of the CB13 functions and
    the LABELLER Q and U call.
  - **`A`**: windows and `S_A` rule, the election-night exclusion, the fill and touch-consistency rules (CB13-T's, by
    pin), eligibility, the grain rule, the price band, the tick rule, the silence rule, the global monitor-gap detector,
    the wake-up definition, the frozen `SD(x)` carried from SCREEN_A to REP_A, the mark rules, cluster ways, placebo strata, attribution covariates, gates (GQG, GQ, GU,
    GQP, GUP, GAI), Q2 and U2 rules, the REP_A event-disjointness rule, the reported shape descriptor, and the q0389
    sample rule.
  - **`K`**: file sha256s, field lists, the loose topic rule, the unlistable regex, the cell definition, the MDE bounds,
    and the re-entry rule.
- Jobs refuse (exit 2) on a hash mismatch. **No rule is computed from, or revised after, any CB16 mark, outcome or
  statistic.** The q0382 grain census and the q0385 census read features only.
- **Field whitelists.** *Monitor prints:* as CB13 §1.4 (`ts, condition_id, token_id, outcome_index, price, size, cash,
  title, slug, ctx_event_id, ctx_market_id, ctx_category, ctx_fee_type`; `tx16` in memory only). The U lookback reads
  `ts`, `condition_id` and `cash` only. **Not parsed:** `side`, `key`, `recv_ts`, `wallet_*`, every other `ctx_*`.
  *Capture rows and sidecar:* as CB13 §1.4, plus `order_price_min_tick_size` and `clob_rewards` (already whitelisted
  there). *Sweeps:* `token_id`, receipt time, `best_bid`, `best_ask`, `bid_size_1`, `ask_size_1`, `depth_*_1c`,
  `depth_*_5c`, `n_*_levels`. *Data API (q0389):* `timestamp`, `price`, `size`, `conditionId`; `side`, `proxyWallet`,
  name and hash fields are discarded at parse. *K:* §1.1. A unit test feeds fixtures carrying every forbidden field and
  asserts that no parsed row, file or log contains them.

## 2. Common rules (deltas from CB15 §2)

### 2.1 Costs

| Test | Price and cost rule |
|---|---|
| Q1, U1 (and their reps) | none charged (mechanism contrasts on maker mark-outs). Q1 and U1 are in maker-mark-out units, a mid exit: **upper bounds** for any maker, labelled so |
| Q2 (Stage 2) | CB13-T3's rule on **bot-grain** REP_A fills: maker entry at the recorded print's maker-adverse price `P` (maker fee 0, no rebate); exit as a taker at the recorded adverse touch of the 2-4 h mark capture (bought → `bid_h`; sold → `ask_h`); taker fee `r·x(1 − x)` on the exit, `r` = the sidecar fee rate, `max_if_unknown` (unknown → 0.07); position `min(print size, 100)` shares (CB13 fix D). **Label: "fills like the bots' fills; queue position ignored, so an upper bound"** |
| U2 (Stage 2) | the same round trip on **avoided fills**: REP_A fills in the same market with `τ ∈ (τ_w + 60 s, τ_w + 2 h]` after a wake-up print at `τ_w` (§CB16-U). The primary is the **within-market difference** (avoided minus the market's other REP_A fills), which is cost-neutral to any exit cost common to both groups. The protected maker's net on the remaining fills is reported |
| Binding cost robustness | Q2: +0.5c on the exit keeps net > 0. **U2: none** (round 1 item 11: a common exit cost cancels in the primary difference, and the level component already pays the fee, so a +0.5c check would be vacuous) |

There are no historical books without pmxt. Q2 and U2 use recorded prints and recorded capture touches; depth at the
touch is unknown (sweep depth reported where swept). Stage P (§2.9) reads the book at the print.

### 2.2 Clocks

- **Monitor prints.** As CB13 §2.2: the venue `ts` is the fill time `τ`; prints are aggregated by (`tx16`,
  `condition_id`) into transactions with YES-terms VWAP, size and `[P_min, P_max]`. YES terms: a print on outcome index
  1 at `x` is a YES print at `1 − x`; the grain is preserved, because `1 − x` is sub-cent iff `x` is.
- **Capture touch and marks.** As CB13 §2.2 (touch = latest complete capture with `received_utc < τ`, age ≤ 60 min;
  marks at 2-4 h and 6-8 h). Gamma `best_bid`/`best_ask` give the touch. Crossed or one-sided rows are ineligible and
  never repaired.
- **Silence (U).** `τ_prev` = the venue time of the market's previous large transaction on the monitor stream (any
  outcome token of the condition), at or after the lookback floor. `s = τ − τ_prev`. The market's prior gaps are the
  consecutive large-transaction gaps with both ends in `[max(τ − 7 d, 2026-10-26T00:00Z), τ)`.
- **Monitor gaps.** A **global monitor gap** is any 15-minute interval in which the stream holds no print in any market
  (the stream carries 7,000-13,600 prints a day, so such an interval is almost surely an outage). A silence or prior
  gap that overlaps a global monitor gap is "censored (monitor gap)": the unit is excluded and counted, and the gap is
  dropped from the market's prior gaps.
- **Sweeps (reported shape).** The latest sweep row of the token with receipt `< τ` and age ≤ 2 h.
- **Data API (q0389).** `timestamp` (s); prints strictly before `τ` only.
- `closedTime` is never a population condition, origin or feature.

### 2.3 Uncertainty and decision rule

As CB15 §2.3: unweighted primary unless stated; one-sided p is the max over the declared ways; a 2,000-draw cluster
bootstrap with **seed 1616**; the small-G rule (G ≥ 30 CR1; 15-29 CR2 with t(G − 1) and the Webb wild bootstrap, 9,999
draws; G < 15: that way leaves the max and its leave-one-cluster-out sign rule binds, as A-C1). "Unknown" never counts
as met. The 60% availability rule applies (CB13 fix 2).
- **Ways (Q, U).** Gamma event (CR1); **path key × 6-hour block** (CB13 round 1 item 4: the underlying asset for
  PATH-SETTLED markets, else the first sidecar `series_slugs` entry, else the event); **6-hour block** (G = 56 per
  window); **UTC hour of day** (G = 24, CR2; round 7's hour way). UTC day (G = 14) is never in the max, but
  **leave-one-day-out must keep one-sided p < 0.05 and the sign**.
- **Testability minimums.** Q: ≥ 1,000 eligible fills in markets with both grains, in ≥ 100 such markets and ≥ 60 events.
  U: ≥ 1,000 standardisable units in markets with ≥ 5 units, in ≥ 100 markets and ≥ 60 events. Below these, the test is "not testable
  (population)", counted with p = 1.
- **Stage 1, family A (Q1, U1).** A test advances iff all of these hold:
  - one-sided p < 0.01 (strict);
  - the §2.4 floor;
  - every binding placebo, robustness check and gate;
  - a batch Holm step-down at one-sided α = 0.05 over **k1 = 2** (fixed; the first step is 0.025, so any p < 0.01
    passes).

  BY (q = 0.10 over `battery2.cumulative_count()` at the run) is triage only.
- **Stage 2.** One CB16-wide strict Holm at one-sided α = 0.05 over every triggered Stage-2 test (≤ 4: Q1-rep, Q2,
  U1-rep, U2), each in its Stage-1 or declared direction. A test that finishes before k2 is known is judged at **α/4**
  (strict). **U2's p is the max of its two one-sided component p's** (the within-market difference and the avoided-fill
  level; round 1 item 11). Each test records `checks_ok`, meaning every binding check other than the primary p gate (CB13 fix A).
  The final Holm (q0392) is applied once and can only add passes. Labels:
  - Q1-rep and U1-rep: "later live window replication, event-disjoint (L2)";
  - Q2 and U2: "recorded-touch round trip (L2)".
- **Stage P** is a separate registration for any survivor (§2.9).

### 2.4 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate |
|---|---|---|
| Q1 | mechanism contrast | `β_Q ≥ +0.5c` per filled share (CH131's floor), with the sign: bot-grain fills better for the maker |
| U1 | mechanism slope | `β_U ≥ +0.5c` per SD of standardised log-silence (CH132's floor), with the sign: longer silence worse for the maker |
| Q2 | economic, recorded prints and touches | net ≥ **+0.5c** per filled share after the exit fee |
| U2 | economic (protection value) | **primary:** the within-market difference (avoided minus the same markets' other REP_A fills) ≤ **−0.5c** per filled share; **and** the avoided-fill net ≤ **−1.0c** per filled share |
| Q1-rep, U1-rep | as Stage 1 | as Stage 1 |

### 2.5 Counting (M3 rule)

- Kinds **`cb16_test`**, **`cb16_replication`** and **`cb16_descriptive`** (EXCLUDE), mirroring CB15's
  `battery2.KIND_RULES` entries; unknown kinds raise. Descriptive lines cover: the smoke; censuses; gates; the grain
  census; the whole K census; class strata; the sports arms; the shape descriptor; the stale-touch variant; the 6-8 h
  readings; the q0389 validity sample; the Q exclusion-by-grain and U exclusion-by-`x`-tercile tables; the Q mark-out
  decomposition; the per-window politics share; the H withdrawal record.
- **Count lines (`ml_explain` `n_tests`):** `creative_batch_16:Q` **1** and `creative_batch_16:U` **1**. Replication
  lines `creative_batch_16:<family>:rep` carry that family's triggered tests (Q ≤ 2, U ≤ 2).
- **Triggers.** Q1-rep and Q2 iff Q1 advanced. U1-rep and U2 iff U1 advanced.
- **Cumulative count:** 1,255 on HEAD at drafting (`battery2-count-v1`), not stable; recorded at each run. **CB16 adds 2
  fixed tests and up to 4 conditional ones. Budget: 2-6.** K adds nothing (no counted test was ever declared). H adds
  nothing (withdrawn uncounted in round 1; one descriptive line records it).
- Tests behind a failed or unknown gate are "not testable" or "not run" (p = 1) and are **still counted**. The gates
  are: the smoke, disjointness, GQG, GQ, GU, GQP, GUP, GAI, availability, and the Stage-2 minimums. A job waiting
  on exit 75 is "pending" and writes no line.
- **Withdrawals that stay uncounted.**
  - U would be withdrawn if the formal prior-work check found a re-run before part A is committed. Round 1 found none
    (item 12 adds HB1 MS2 as a disclosed neighbour).
  - H **was** withdrawn in round 1 (item 17): no rule had bound, no CB13-R result exists, and no H outcome, price or
    statistic was seen (CB15-L precedent).

### 2.6 Placebos and robustness (common)

As CB15 §2.6: each binding placebo names the alternative it guards against; calibration placebos are judged on p alone;
200 draws; **advance rate ≤ 1.5%**; seeds 16101-16130. Following the CB12-X lesson, **the composition placebo is
primary for Q and U, not secondary.**

Common binding robustness for any advance:
- (i) the §2.1 cost robustness;
- (ii) p and the floor still hold without the top 5 clusters of each way;
- (iii) leave-one-day-out (p < 0.05 and the sign);
- (iv) unavailable units are excluded and counted, never imputed; if the available share is below 60% of eligible
  units, the test is "not testable (availability)".

### 2.7 Pre-freeze census and gates (counts only)

Outcome guards come first, with field-restricted accessors. A unit test asserts that no census path receives a mark
quote, a capture row received after a fill's `τ`, an outcome, or a later price
used as a target. Per-part gates are in §3:
- **Q:** GQG (pre-freeze, q0382), then GQ, GQP and GAI (q0385/q0386);
- **U:** GU, GUP and GAI;
- **K:** the counts-only re-entry rule.

MDEs come from counts and feature-only proxies. They are never used to change a floor, window or threshold.
`MDE = (z_0.99 + z_0.80) × 1.2 × SE = 3.80 × SE`.

### 2.8 Compute, network, disk and stop rules

- **Host.** 1 OCPU, about 5.6 GiB RAM shared with the collectors. Queue rules as CB15 §2.8: one job per lane, nice 19,
  `MemAvailable ≥ mem_mb + 1200`, address cap 2 × `mem_mb`, the 02:45-05:30 UTC blackout for `mem_mb ≥ 500`. Q/U frame
  jobs avoid the collector pass (`:31-:55` of even hours) or yield to the pass lock, as CB13. Readers stream one capture
  or one day file at a time.
  - `mem_mb` is 800 for q0384 and q0387 (one capture's rows with column whitelists, as CB13 q0271).
  - `mem_mb` is **1200 for q0383**: streaming field-restricted readers of the two large JSON files, with Kalshi markets
    indexed by close day. This is a heavy job under the memory rule (never two multi-GB jobs at once), and the
    coordinator schedules it alone.
  - `mem_mb` ≤ 500 elsewhere.
- **Network** (`net` lane; ≤ 2 rps; shared `Limiter`, 429 / `Retry-After` back-off, stop on repeated 429; descriptive
  User-Agent):

  | Job | Work | Requests / wall | Stored (cap) |
  |---|---|---|---|
  | q0380 | exclusion keys (increment over CB15 q0340, attribution) | ≤ 400 Gamma, ≤ 5 min | ≤ 0.01 GB |
  | q0389 | U validity: Data API `/trades` for a seeded sample (seed 16131) of 300 SCREEN_A units with a wake-up label and 300 without, paging newest-first until a print before `τ` is found or 6 pages | ≤ 3,600, ≤ 35 min | ≤ 0.01 GB |

  Every other CB16 job has no network. **Historical `net` total ≤ about 4,000 requests.**
- **Disk guard.** As CB15 §2.8: `--disk-cap-gb`, `--data-dumps-cap-gb 40`, exit **75** if data-dumps + cap > 40 GiB or
  if root free − cap < 4.5 GB. CB16 output caps total **≤ 0.15 GB**. CB16 never deletes or moves host data.
- **Source retention.** If SCREEN_A or REP_A captures, sweeps or trades files are archived and deleted from the host
  under the capsule-first policy before a frame job runs, the job restores them byte for byte with
  `restore_from_archive.py`, verifies the archived hash, and never re-derives a file. q0387 seals the REP_A source
  hashes.
- **Monitor storage cap (disclosed).** `live_trades/` grows about 45 MB a day against the monitor's 3 GB cap, which binds
  around mid-December. REP_A ends near 2026-11-30 if `S_A` = 11-02. If the cap binds earlier, the missing days are
  "unavailable (monitor stopped)", counted, never back-filled. CB16 changes no collector setting.
- **Stop rules.** 3 CPU-hours per family. A job failing twice for the same non-transient reason stops and is recorded.
  A null is "not detected at MDE x". **No re-screen of a failed CB16 test** with altered windows, grain rules, price
  bands, silence rules, wake-up definitions, mark rules, cells, bins, labels or populations, on any data.

### 2.9 Funnel and Stage P

The funnel is: screen (Stage 1 on SCREEN_A) → gates, placebos, robustness → replication (Stage 2 on REP_A) → a separate prospective confirmation (Stage P) → economic validation at recorded prices
with fees, spread and depth.
- **Stage P-Q / P-U** (only if Q2 or U2 passes). Fresh live windows after REP_A. The touch is read **at the print**
  (a CLOB `/book` read triggered by the monitor's receipt; queue position unknown and disclosed), depth is recorded, and
  the grain rule or wake-up rule is frozen from CB16. The economic test is a passive paper maker that quotes beside
  bot-grain books (Q) or steps aside after wake-ups (U), with passive and taker exits both reported. **A protection
  rule is a route only if the protected maker's own net is positive**; every maker cell so far has been negative.
- **K** has no route of its own and no Stage P. Its output is a line in later designs' censuses.

---

## 3. Tests

### CB16-Q: Quoter grain (CH131)

**Question.** When a large taker transaction fills the best resting quote, is the maker's 2-4 h mark-out better when
that quote sat on a sub-cent price (bot-grain) than when it sat on a whole cent (human-grain), within the same market?

**Mechanism.** Reward bots and model makers quote at the finest tick and re-quote in a loop. A person types whole cents
and leaves an order resting until it is lifted. A stale resting order is the one an informed taker lifts, so maker
adverse selection should concentrate on human-grain quotes. The economics studies and SB2-J2 pooled both kinds. **Who
pays:** people resting whole-cent orders. **Against it:**
- bots also quote whole cents;
- sub-cent quoting happens when spreads are tight, and tight spreads carry their own mark-out;
- a whole-cent price is a focal price where many bots also rest.

The composition placebo, the attribution regression, the spread-free mark and the tight-touch stratum exist for these
objections. A fourth objection is mechanical (round 1 item 1): `M = d·(mid_h − P)` contains the realised half-spread
`d·(mid_0 − P)`, and a sub-cent quote usually sits nearer the mid, so bot-grain fills have a mechanically lower `M` by
about 0.1-0.9c, which is the size of the floor. The spread-free mark below must therefore also hold.

**Population (q0384; frozen in part A).** Monitor transactions with `τ` in SCREEN_A, minus the election-night exclusion;
binary markets; LABELLER class not SPORTS-FEED (`CB16_SPORTS_IN_PRIMARY = false`); key drops (§1.3).
- **Fill and side:** CB13-T's frozen rule by pin. A transaction is a unit iff it is touch-consistent with the latest
  complete capture touch (age ≤ 60 min, two-sided, spread ≤ 10c, touch mid in [0.03, 0.97], capture `end_date ≥ τ + 3 h`).
  The maker direction is `d` (maker sold YES: `d = −1`, `P = P_min`; maker bought YES: `d = +1`, `P = P_max`). Inside and
  inconsistent transactions are excluded and counted.
- **Grain arm eligibility:** `order_price_min_tick_size = 0.001` in the sidecar of **both the touch capture and the
  2-4 h mark capture** (round 1 item 5; a tick change in between is "tick change", excluded and counted), and
  `P ∈ [0.05, 0.95]` (premise 1: the tails are on a 0.001 tick for everyone).
- **Grain:** `g = 1` (bot-grain) iff `round(1000·P) mod 10 ≠ 0`; `g = 0` (human-grain) otherwise. `P` is the
  maker-adverse price (the best level the taker lifted), so `g` is the grain of the best resting quote at the print. Only
  that level's grain is used; deeper levels lifted in a sweep are other makers and are not classified.
- **Both-grain markets:** the statistic uses markets with at least one fill of each grain in the window. Single-grain
  markets are counted and reported.
- **Exclusion by grain (round 1 item 3; reported, with a bound).** The touch-consistency rule excludes "inside" and
  "inconsistent with touch" transactions. Sub-cent quotes that improved inside a stale capture spread are excluded as
  "inside" more often, so the exclusion can depend on grain. The census reports inside, inconsistent, one-sided and
  no-mark rates **by grain** (the grain of `P_min` for transactions above the touch mid, of `P_max` below it). A
  **worst-case bound** is also reported: `β_Q,worst` adds each grain's excluded transactions to that grain's mean at
  the adverse quantile of its included `M` (the 10th percentile for bot-grain, the 90th for human-grain), weighted by
  the grain's exclusion rate, within market. If `β_Q,worst ≤ 0`, every Q line carries "grain-dependent exclusion could
  explain the contrast".

**Mark-out.** `M_h = d·(mid_h − P)` cents per share, as CB13-T, labelled "2-4 h" (primary) or "6-8 h". Wide-mark and
closed-before-mark units are counted and enter the worst case below. **Decomposition (reported for every Q line):**
`M_h = d·(mid_h − mid_0) + d·(mid_0 − P)`, where `mid_0` is the touch capture's mid. The first term is the spread-free
mark, the second the realised half-spread against the touch; both are reported by grain.

**Q1 (within-market grain contrast).** `β_Q` is the coefficient on `g` in an OLS of `M_2-4h` on `g` with **market fixed
effects**, one unit per fill (unweighted). It is one-sided > 0 with floor +0.5c, and p is the max over the event,
path key × 6 h block, 6 h block and hour-of-day ways. Leave-one-day-out must keep p < 0.05 and the sign.
- **Binding composition placebo (primary).** Permute `g` within strata of (market × touch-spread band {≤ 1c, 1-2c, 2-5c,
  > 5c} × `P` band {[0.05, 0.20), [0.20, 0.80], (0.80, 0.95]} × transaction-size band {< $2.5k, $2.5-10k, ≥ $10k}).
  200 draws, seed 16101, advance rate ≤ 1.5%. *Alternative guarded:* grain proxies the spread state, price level or size
  of the moment, not the quoter. **Informativeness rule (round 1 item 4):** at least 50% of Q1's fills must lie in
  strata that hold both grains. Otherwise the permutation leaves most labels in place and the placebo would pass by
  default, so the placebo **FAILS** and Q1 cannot advance (counted with its p, labelled "composition placebo
  uninformative").
- **Binding within-market calibration placebo.** Permute `g` within market × UTC hour (200 draws, seed 16102); **advance
  rate ≤ 1.5%** (round 1 item 6). *Alternative guarded:* within-market dependence makes the clustered p
  anti-conservative.
- **Binding pre-fill placebo.** The same estimator with `M` replaced by the pre-fill move: the capture mid change from
  the capture before the touch capture to the touch capture, signed by `d`. It must not pass p < 0.01. *Alternative
  guarded:* within-market trends that coincide with grain regimes.
- **Attribution (binding for the label "quoter grain").** A market-FE OLS of `M_2-4h` on `g` plus the touch-spread band,
  `P` band, size band, touch-age band {≤ 20, 20-60 min}, time-to-end band {< 1 d, 1-7 d, > 7 d}, reward band
  (`clob_rewards` present or not), 6 h block of day, log capture liquidity and **U's standardised silence `x` where
  defined, with a missing-`x` indicator** (round 1 item 7, symmetric with U's attribution). The label "quoter grain" is
  credited only if the `g` coefficient keeps at least half of `β_Q`; otherwise the label is "composition, not grain".
- **Binding spread-free mark (round 1 item 1).** The Q1 estimator with `M` replaced by `d·(mid_h − mid_0)` must keep the
  sign and at least half of `β_Q`, with one-sided p < 0.05 (max over ways). Otherwise Q1 cannot advance, labelled
  "realised half-spread, not adverse selection".
- **Binding tight-touch stratum (round 1 item 2).** The touch spread used in the strata and covariates comes from a
  capture up to 60 min old. Q1's estimator on fills with touch age ≤ 20 min **and** touch spread ≤ 1c must keep the
  sign. If it does not (or the stratum has fewer than 300 fills in both-grain markets: "unknown"), the label is "grain or
  contemporaneous spread state", never "quoter grain".
- **Robustness (binding; each keeps the sign):** touch age ≤ 20 min; the 6-8 h mark; the adverse-touch mark (CB13-T)
  with wide-mark and closed-before-mark units at their adverse touch or worst case; excluding transactions ≥ $10,000;
  each maker side; market-weighted means; `P ∈ [0.10, 0.90]`; reward-band markets alone and others alone (each if ≥ 300
  fills); top-5 drops by event and by path key × block.
- **Reported (uncounted):**
  - `β_Q` by LABELLER class and in the sports arm;
  - the mark-out decomposition by grain; the exclusion-by-grain table and `β_Q,worst`;
  - the stale-touch variant (grain of the capture touch's third decimal; round 7's original arm);
  - the single-grain markets' mean `M` by grain;
  - **a reduced shape descriptor** where a sweep row of age ≤ 2 h exists: the touch size's share of `depth_1c` on the
    lifted side, `depth_5c/depth_1c`, and `n_levels`, with its tercile split of `M` within market and the sweep
    coverage share.

  **The stale-touch variant and the shape tercile split are point estimates only: no p-value is computed or written,
  and neither can ever be promoted to a test, a trigger or a Stage-2 object** (round 1 item 8).

**Gate GQG (grain informativeness; q0382; pre-freeze; features only).** On CB13-T's SCREEN fill table (or the pinned
fill functions on the raw `[10-12, 10-16)` files), among eligible non-sports fills (tick 0.001 at the touch capture;
the mark-capture tick is not read, since marks are not opened), GQG passes iff:
- the sub-cent share is in [5%, 95%] (CH131's first kill, measured on `P`); and
- at least 40% of eligible fills lie in both-grain markets.

FAIL → Q1 "not testable (grain)", counted (part A's rules are committed before q0382), and Q2 is not triggered.

**Gate GQ (q0385).** The §2.3 minimums on SCREEN_A.

**Power gate GQP (feature-only; as CB13 GTP).** Q1's own estimator and ways run on the **pre-fill proxy outcome**. Only
the clustered SEs are written (max over ways); no proxy point estimate is written to any output (unit-tested). If
`MDE_Q = 3.80 × SE > 1.0c` (2 × floor), Q1 is "not run (power)", counted.

**Gate GAI (cadence informativeness; as CB13 GTI, measured from `P`).** It uses SCREEN_A fills that have a later monitor
print in the same market in `[τ + 2 h − 30 min, τ + 2 h + 30 min]`. The sign of `d·(VWAP_later − P)` must agree with
the sign of `d·(mid_2-4h − P)` in more than 70% of pairs where both are nonzero. With at least 200 pairs, FAIL → Q1 and
U1 "not testable (cadence)", counted. With fewer than 200 pairs, every A line carries "cadence informativeness unverified
(n < 200)" at Stage 1. Stage 2 pools SCREEN_A and REP_A pairs, and Q2 and U2 require a pooled PASS.

**Power (planning; GQP decides).**
- Expected fills: about 250-400 touch-consistent non-sports transactions a day, from G1, CB13 H8 and an assumed 50-70%
  touch-consistency share. That gives 3,500-5,600 fills in 14 days, of which about 80% are on a 0.001 tick. The sub-cent
  share is about 0.36 on prints (G1a; higher within 0.001-tick markets). Assume 50-70% of fills sit in both-grain
  markets.
- With SD(`M_2-4h`) ≈ 3c and a design effect of 2-3: `SE(β_Q) ≈ 0.14-0.28c`, so **MDE_Q ≈ 0.55-1.1c** against the 0.5c
  floor and the 1.0c gate.
- **Q1 may be "not run (power)"** (counted). A 14-day window was chosen over 21 days because of the monitor storage cap
  (§2.8), not because of power.

**Stage 2 (conditional; q0387, q0388).** REP_A, same frozen rules, **event-disjoint, binding even if thinned** (round 1
item 20): REP_A drops every Gamma event with a SCREEN_A fill, counted. If more than 40% of REP_A fills are dropped, the
lines carry "REP_A thinned by event overlap". A variant that keeps them is reported only and can never replace the
disjoint result. The politics share of fills is reported for SCREEN_A and REP_A (election run-up versus resolution
wave). Q1-rep needs the GQ minimums on REP_A, else "not run (power)",
counted.
- **Q1-rep:** the Stage-1 statistic, placebos and robustness.
- **Q2 (economic; triggered by Q1; needs the pooled GAI PASS):** the CB13-T3 round trip (§2.1) on bot-grain REP_A fills,
  one-sided > 0, floor +0.5c, robustness +0.5c on the exit; the worst case (wide-mark and closed-before-mark units at
  the adverse extreme) keeps p < 0.01. This is expected to be hard, because the exit pays a half-spread and a fee against
  the maker's realised spread.

### CB16-U: Wake-up prints, relative large-print silence in active markets (CH132)

**Question.** Within a market that is active on the large-print stream (at least 5 large-print gaps in the prior 7 days),
is the maker's 2-4 h mark-out on a large fill worse the longer that stream had been silent before it, measured against
the market's own recent inter-arrival times?

**Scope (round 1 item 9).** CH132's literal object is the dead book woken by a print. The ≥ 5 prior-gap rule needed for
standardisation removes most dead books, so U tests **relative** silence in **active** markets, and its title says so.
The census reports how many silences of at least 12 h the rule drops (on SCREEN_A, and on CB13-T's SCREEN features in
q0382 for comparison with G1b's 459 + 127 ≥ 12 h gaps outside sports). A dead-book design is a different test and is
not registered here.

**Mechanism.** In a dead book the resting quotes are the oldest on the venue. A taker who wakes the market has usually
read something: a wire, a filing, a sibling market. **Who pays:** whoever is resting. **Against it:**
- HB1 IX3 found flow in quiet markets continuing *less* (−0.17c), the opposite sign;
- scheduled events (game starts, releases, deadlines) wake markets for public reasons;
- this is large-print silence, not all-size silence (premise 3);
- HB1 MS2 (hours since last trade → unsigned 6 h move; failed BY) is a disclosed neighbour (§0.2).

**Population (q0384).** Q's units, without the grain-arm eligibility. Any tick and `P` in [0.03, 0.97] (CB13-T's touch
mid rule) qualify. A unit additionally needs:
- **standardisable silence:** at least 5 uncensored prior gaps in the lookback (§2.2), and `τ_prev` present;
- not a **genesis** print: the sidecar `created_at` at least 24 h before `τ` (CH22's object, excluded and counted);
- an uncensored silence (no global monitor gap overlaps `(τ_prev, τ)`).

Markets with at least 5 units in the window enter the statistic.

**State.** `x = ln(s) − ln(median of the market's prior gaps)`. **Wake-up** (for U2 and reports) means
`s ≥ max(1 h, the 90th percentile of the market's prior gaps)`, frozen, with no data-derived threshold. SD(x) is
computed on SCREEN_A units (a feature) and written to the SCREEN_A result file; **U1-rep uses that frozen SCREEN_A
`SD(x)`, never REP_A's** (round 1 item 10).

**U1 (within-market slope).** `β_U = −(the coefficient on x/SD(x))` in a market-FE OLS of `M_2-4h`. It is one-sided > 0
(longer silence, worse maker mark-out), floor +0.5c per SD; ways, leave-one-day-out and top-5 drops as Q1.
- **Binding composition placebo (primary).** Permute `x` within strata of (market × UTC 6 h band of day × touch-spread
  band × size band); 200 draws, seed 16111. *Alternative guarded:* silence proxies night hours, wide books or small
  prints, not information arrival.
- **Binding within-market calibration placebo.** Shuffle `x` within market (round 7's placebo); 200 draws, seed 16112.
- **Binding pre-fill placebo.** As in Q1, with `x` as the regressor. *Alternative guarded:* silent markets drift before
  the print, and the print only follows the drift.
- **Attribution (binding for the label "arrival information").** Market-FE OLS with Q1's covariates plus `g` where
  defined. The `x` coefficient must keep at least half of `β_U`; otherwise the label is "composition, not silence".
- **Robustness (binding; each keeps the sign):**
  - the 6-8 h mark;
  - touch age ≤ 20 min;
  - the adverse-touch mark;
  - excluding SCHEDULED-EVENT-class markets (LABELLER) — guards public wake-ups;
  - `x` from the 3-day lookback instead of the 7-day one;
  - excluding units whose silence spans 00:00-06:00Z;
  - each maker side;
  - excluding transactions ≥ $10,000;
  - top-5 drops.
- **Reported (uncounted):**
  - the wake-up indicator's within-market contrast;
  - `β_U` by LABELLER class and in the sports arm;
  - **exclusion rates by `x` tercile** (round 1 item 13): among standardisable transactions, the inside, inconsistent,
    one-sided, no-mark and censored rates per tercile of `x`, so that a silence-dependent exclusion is visible;
  - the count of ≥ 12 h silences dropped by the ≥ 5 prior-gap rule (item 9);
  - the taker follow at recorded prints (expected to fail the 4.5c round trip, as E007);
  - the q0389 validity line: among sampled wake-ups, the share whose all-size silence is at least 1 h, and among
    sampled non-wake-ups, the share whose all-size silence is under 1 h.

    If the first share is below 50%, every U line carries "large-print silence only; market was trading below $1k".

**Gate GU.** The §2.3 minimums. **Power gate GUP (feature-only).** U1's estimator and ways on the pre-fill proxy, SEs
only. If `MDE_U > 1.0c` per SD, U1 is "not run (power)", counted. **GAI** as in Q.

**Power (planning; GUP decides).** G1b puts about 65% of non-sports transactions in markets that printed within the hour,
so roughly 55-75% of fills should be standardisable, giving about 2,000-4,500 units in 14 days. With SD(`M`) ≈ 3c, a
within-market variance of standardised `x` of about 0.8, and a design effect of 2-3: `SE(β_U) ≈ 0.07-0.13c`, so **MDE_U ≈
0.27-0.49c** against the 0.5c floor. **U1 is the only CB16 test planned to be powered at its floor.**

**Stage 2 (conditional).** REP_A, event-disjoint as Q.
- **U1-rep:** the Stage-1 statistic, placebos and robustness, with `x` scaled by SCREEN_A's frozen `SD(x)`.
- **U2 (economic; triggered by U1; needs the pooled GAI PASS):**
  - *Avoided fills:* REP_A fills in a market with `τ ∈ (τ_w + 60 s, τ_w + 2 h]` after a wake-up print at `τ_w` in the
    same market. The 60 s delay stands for a maker that watches the public trade feed. AREPO's own monitor lags
    7-9 min and is not the reaction clock.
  - *Statistic (round 1 item 11):* **primary** is the within-market difference of the CB13-T3 round-trip net (avoided
    fills minus the market's other REP_A fills), one-sided < 0, floor ≤ −0.5c per filled share. It is cost-neutral to
    any exit cost common to both groups. The **second component** is the avoided-fill net itself, one-sided < 0, floor
    ≤ −1.0c. U2's p is the **max of the two one-sided p's**, and that p enters the Stage-2 Holm.
  - *Robustness:* delays of 5 min and of AREPO's actual receipt lag (`recv_ts`, whitelisted for this check only) keep the
    sign of the primary. The draft's +0.5c exit-cost check is dropped as vacuous.
  - *Reported:* the protected maker's net on the remaining fills. **A pass says that stepping aside avoids losses, not
    that a maker route exists.**

### CB16-K: The Kalshi-absent map (CH143). Census only, no counted test

**Why no counted test.** CH143's statistic is the within-cell difference in the T−24h Brier residual
`(Y − p)² − p(1 − p)` between twin-absent and twin-present markets, with floor 1 pp.
- Under calibration, the residual's variance is `p(1 − p)(1 − 2p)²`, at most 0.056 (SD at most 0.24), and plausibly
  0.10-0.15 SD at T−24h prices.
- The strict present arm has **92 non-sports events** (G2). With an event-level SD of 0.10-0.15, `SE ≈ 1.0-1.6 pp`
  before the within-cell restriction, so **MDE ≈ 4-6 pp** against the 1 pp floor and a 2 pp gate.
- At most one or two cells (Elections) could hold 30 present events, while CH143's kill needs at least 5.
- The historical rate (958 strict matches over 12 months, 270 non-sports) means a prospective causal twin-labeller
  would need years to reach the roughly 360 present non-sports events in eligible cells that an optimistic SD of 0.10
  requires for MDE ≤ 2 pp.

No feasible collection fixes this with strict labels. CB16 therefore records the map's *inputs* (labels and counts) and
reads no outcome and no price, so that any later counted design stays blind.

**Census (q0383; counts only; no network).**
- **Frame.** `poly_markets.json` markets that are binary Yes/No with scheduled `endDate` in `[2025-10-13, 2026-10-01)`
  (inside the Kalshi universe's 12-month close window and before `T_hist_end`). Selection is event volume ≥ $20k, the
  pull's own rule, and is labelled "selected on lifetime volume".
- **Labels (frozen; outcome-free):**
  - **PRESENT-STRICT:** the market id is in `matches_all.json` (the r1 audit conflicts excluded, counted).
  - **PRESENT-TOPIC:** not strict, but some Kalshi market in `kalshi_markets*.jsonl` has `|close_time − endDate| ≤ 3 d`,
    at least 2 shared content words (the matcher's tokeniser and stopwords) and word Jaccard ≥ 0.30.
  - **ABSENT:** neither. **Label noise, disclosed (round 1 item 14):** the Kalshi universe (`CROSS_VENUE_STUDY.md` §2)
    holds only markets in series sharing a content bigram with a Polymarket title. It drops hourly and 15-minute
    series and multivariate combos, and keeps only markets settled within the 12 months before 2026-10-12 with at least
    5,000 contracts. ABSENT therefore means "no liquid, settled, non-multivariate Kalshi twin in a bigram-sharing
    series". Some ABSENT markets have a low-volume, multivariate, unsettled or differently worded Kalshi twin. The label
    is named "ABSENT (liquid-universe)" in every output.
  - **FAR-TOPIC** (a counted subset of ABSENT; round 1 item 15): no strict or topic twin, but some Kalshi market in the
    universe passes the same text rule (≥ 2 shared content words, Jaccard ≥ 0.30) with `30 d ≤ |close_time − endDate| ≤
    180 d`. These are topic twins without a same-date contract, the composition-placebo candidate of the re-entry rule.
    Defined and counted now, in q0383.
  - **UNLISTABLE** (a reported subset of ABSENT): the frozen regex for Kalshi's restricted contract classes
    (assassination, terrorism, war declaration, invasion, military or air strike, nuclear detonation, coup). An
    UNLISTABLE-regex market labelled PRESENT is a "rule conflict", counted.
- **Cells.** CB13 LABELLER class (title-based; pinned) × lifetime-volume decile (hindsight; labelled). SPORTS-FEED is
  reported separately.
- **Counts written.** Markets and distinct events per label and cell (including FAR-TOPIC). The number of cells holding both a PRESENT label
  and ABSENT with ≥ 30 events each, for strict and for strict ∪ topic. Key overlaps by source (worn calibration sets
  such as `h2_main`, `h3_power` and the T5 frame) as counts. **Feature-free MDE bounds** per label set, at SD 0.10
  (optimistic) and 0.24 (the maximum under calibration):
  `MDE = 3.80 × SD × sqrt(1/G_present + 1/G_absent)` over eligible cells.
- **Re-entry rule (declared; no CB16 test).** A counted K may be designed in a later batch only if all of these hold:
  - the strict ∪ topic label gives at least 5 eligible cells and an optimistic MDE ≤ 2 pp;
  - a seeded blind audit of 100 PRESENT-TOPIC pairs (`science-reviewer`, titles only, seed 16141) finds at least 90% to
    be genuine same-event twins;
  - the later design uses a composition placebo that keeps topic but removes the arbitrage channel: the FAR-TOPIC label
    defined above (no contradiction with the 3-day topic rule: FAR-TOPIC is disjoint from PRESENT-TOPIC by
    construction), with FAR-TOPIC counts of at least 30 events in at least 5 of the eligible cells.

  Otherwise CH143 is recorded as "not testable at the floor with available or feasibly collectable data".

### CB16-H: Hedging-premium skew in barrier ladders (CH138). WITHDRAWN uncounted (round 1 item 17)

The draft nested H behind CB13-R: H would run only if CB13-R1 advanced, and its rules had to bind before CB13 q0282.
Round 1 withdrew it for two reasons:
- **Power.** The planning MDE was 12-20c against a 4c gate (2 × the 2c floor), because one weekly spot path enters reach
  and dip outcomes with opposite signs, which doubles the path noise in `Δ_Y` (premise 6). Weeks are the unit, and no
  feasible collection adds enough of them.
- **Post-selection.** A trigger on CB13-R1's outcome, computed on the same units, selects H's sample on a related result.

No CB13-R result exists, no H rule ever bound, and no H outcome, price or statistic was seen, so the withdrawal is
outcome-blind and **uncounted** (CB15-L precedent). One `cb16_descriptive` line records it. q0390 and q0391 are retired.
CB16 opens no CB13-R data.

**Re-entry (note only).** A later batch may register CH138 only on a **fresh frame**: weekly barrier ladders whose rule
windows end on or after 2026-10-01, disjoint by event and window from CB13-R's SCREEN and HOLDOUT. It must use its own
anchor recipe, must not be triggered by any CB13-R result, and must make a power case that addresses the asset-week
unit. A delta-hedged (return-adjusted) statistic may be proposed there, with a written justification and review. Any
economic question goes to recorded asks with a tail gate.

### CB16-SM: smoke and audits

- **q0381 smoke** (`cpu`, **no network**). PASS needs:
  - the part hashes (`common`, `A`, `K`) and the pinned CB13 function and LABELLER sha256s;
  - the refusals on fixtures: J4-R and CB13-T HOLDOUT rows (both edges); rows before 2026-10-26T00:00Z outside q0382;
    REP_A rows before the seal; `surprise_live/`, `cross_venue_live/`, `e00*/`, `trade_samples/`, `cb3_*`, `h15_*`; the
    monitor's `alerts`, `scores`, `outcomes`, `wallets` and `stats` files; every forbidden field (`side`, `wallet_*`,
    `recv_ts` outside U2's check, `ctx_chg_1h`, `chg_1h`, `uma_resolution_statuses`, `outcome_prices`, `closed_time`,
    Kalshi `result` and `settlement_value`);
  - the grain parser on fixtures: 0.535 → sub; 0.53 → whole; 0.53000000001 → whole; the outcome-1 print at 0.465 →
    YES-terms 0.535 → sub;
  - the global monitor-gap detector on fixtures (a 15-minute empty interval censors a spanning silence; 14 min 59 s
    does not);
  - the silence standardiser (4 prior gaps → unstandardisable; 5 → standardisable; the lookback floor);
  - **independent of q0271** (round 1 item 16): on two CB13-T SCREEN captures and the prints between them, read from
    the raw files, the pinned CB13 fill functions and CB16's own independent re-implementation of the touch-consistency
    band produce identical counts (inside, consistent, inconsistent, one-sided). A mismatch, or a missing raw file
    (unless restored byte for byte from the archive), is a FAIL;
  - the K readers: streaming, field-restricted reads of `poly_markets.json`, `kalshi_markets*.jsonl` and
    `matches_all.json` reproduce **exactly 148,384 / 326,380 / 958** (the published counts; any other count is a FAIL),
    with the sha256s recorded and no outcome field parsed.

  Any failure → the dependent part is "not testable (source)": Q1 and U1 counted once each; for K, a descriptive line.
  The smoke file is write-once. A failed smoke makes the part terminal (CB13 fix B).
- **The U prior-work check** (done in challenger round 1): no re-run found. HB1 MS2 is added as a disclosed neighbour
  (item 12).
- **The K topic audit** (only if the re-entry counts pass; titles only; no outcome).
- Every data job writes a manifest (file sha256, counts, failures, data-dumps size and margin, free disk) and a
  `*_complete` status.

## 4. Jobs (draft specs; JSON in this document only)

Fields follow `queue/README.md`; `argv[0]` is under `backend/scripts/` with `cwd` `backend`. **None is written to
`queue/`** before code, tests and a `science-reviewer` freeze check exist. Every job has `family` =
`creative_batch_16`. Priorities: `net` 5-9; `cpu` 9.

| Id | Lane | Priority | Size / time | Depends on | Commit when |
|---|---|---|---|---|---|
| q0380 | net | 9 | ≤ 400 req, ≤ 5 min, mem 500 | CB15 q0340 | with CB15 q0340 complete |
| q0381 | cpu | 9 | no network, < 5 min, mem 400 | - | rules parts `common`, `A`, `K` and smoke code reviewed |
| q0382 | cpu | 9 | no network, ≤ 15 min, mem 800 | q0381 PASS, CB13 q0271 | before the A freeze |
| q0383 | cpu | 9 | no network, ≤ 60 min, mem 1200 (heavy; alone) | q0380, q0381 PASS | any time after both |
| q0384 | cpu | 9 | ≤ 40 min, mem 800 | A freeze | not before `S_A + 14 d + 8 h` |
| q0385 | cpu | 9 | ≤ 15 min, mem 400 | q0384 | with q0384 |
| q0386 | cpu | 9 | ≤ 30 min, mem 500 | q0385, E011 analysis commit, CB3 freeze or stop record | after all three |
| q0387 | cpu | 9 | ≤ 40 min, mem 800 | q0386 result committed | not before `S_A + 28 d + 8 h` |
| q0388 | cpu | 9 | ≤ 30 min, mem 500 | q0387, seal copy | only if Q1 or U1 advanced |
| q0389 | net | 5 | ≤ 3,600 req, ≤ 35 min, mem 300 | q0384 | after q0384 |
| q0392 | cpu | 9 | < 5 min, mem 300 | every triggered Stage-2 test final | once |

```json
{"id": "q0380_cb16_exclusion_keys", "title": "CB16 exclusion keys with per-key source attribution: CB15 q0340 key file (sha256 pinned) + CB15 frame ids (E race map, P pairs, P Stage-2 pairs) + seal copies; Gamma lookups for missing keys", "family": "creative_batch_16", "priority": 9, "expected_value": "Q/U window check; K overlap counts", "data": ["creative_batch15/exclusion_keys.csv.gz", "history/h15_* (id columns only)", "docs/research_lab/seals/*", "public Gamma (ids)"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0340_cb15_exclusion_keys"], "argv": ["scripts/run_cb16.py", "exclusion-keys", "--rules", "../docs/research_lab/seals/cb16_rules.json", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 1800, "max_retries": 2, "outputs": ["research_lab/creative_batch16/{exclusion_keys.csv.gz,manifest.json}"], "next_action": "q0383", "notes": "DRAFT. Never opens holdout/. A dependency recorded as stopped is absent (recorded)."}
{"id": "q0381_cb16_smoke", "title": "CB16 smoke (cpu, no network): part hashes and CB13 pins; refusals on fixtures; grain parser; monitor-gap detector; silence standardiser; CB13 fill-function reproduction (counts); K streaming readers reproduce file counts with no outcome field parsed", "family": "creative_batch_16", "priority": 9, "expected_value": "go/no-go for parts A and K", "data": ["fixtures", "creative_batch13/ (SCREEN fill table features, if present)", "research_lab/cross_venue/{poly_markets.json,kalshi_markets*.jsonl,matches_all.json} (field-restricted)"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": [], "argv": ["scripts/run_cb16.py", "smoke", "--rules", "../docs/research_lab/seals/cb16_rules.json"], "timeout_s": 900, "max_retries": 1, "outputs": ["research_lab/creative_batch16/smoke.json", "trials.jsonl (cb16_descriptive, or counted not-testable lines once)"], "next_action": "PASS: q0382, q0383", "notes": "DRAFT. Write-once."}
{"id": "q0382_cb16_q_grain_census", "title": "CB16-Q grain census, counts only, features only: eligible non-sports CB13-T SCREEN fills by tick, P band, grain; both-grain market share; gate GQG; count of >= 12 h large-print silences the >= 5 prior-gap rule would drop (round 1 item 9)", "family": "creative_batch_16", "priority": 9, "expected_value": "decides whether the grain arm is informative before the A freeze", "data": ["creative_batch13/ SCREEN fill table (features) or live_trades + snapshots [2026-10-12, 2026-10-16) via pinned CB13 fill functions"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0381_cb16_smoke", "q0271_cb13_t_frame"], "argv": ["scripts/run_cb16.py", "q-grain-census"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch16/census_Q_grain.json", "trials.jsonl (cb16_descriptive or the counted Q1 not-testable line)"], "next_action": "PASS: A freeze check", "notes": "DRAFT. No mark quote or capture after any fill's tau is opened (unit-tested)."}
{"id": "q0383_cb16_k_census", "title": "CB16-K census, counts only, no outcome, no price, no network: strict / topic / absent / unlistable labels; LABELLER class x volume-decile cells; events per label per cell; cells with both labels >= 30 events; key overlaps; feature-free MDE bounds; re-entry verdict", "family": "creative_batch_16", "priority": 9, "expected_value": "the CH143 map inputs and the re-entry decision", "data": ["research_lab/cross_venue/{poly_markets.json,kalshi_markets*.jsonl,matches_all.json,audit_flags.json} (sha256 pinned; field-restricted)", "creative_batch16/exclusion_keys.csv.gz"], "resources": {"mem_mb": 1200, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0380_cb16_exclusion_keys", "q0381_cb16_smoke"], "argv": ["scripts/run_cb16.py", "k-census"], "timeout_s": 4200, "max_retries": 1, "outputs": ["research_lab/creative_batch16/census_K.json", "trials.jsonl (cb16_descriptive)"], "next_action": "record in the ledger; topic audit only if the re-entry counts pass", "notes": "DRAFT. Heavy job under the memory rule: run alone. outcome_prices, closed_time, result, settlement_value never parsed."}
{"id": "q0384_cb16_a_frame_screen", "title": "CB16 SCREEN_A fill table, features only: touch-consistent non-sports transactions (pinned CB13-T rule), grain, tick, silence x and wake-up label, global monitor gaps, genesis and election-night exclusions, reported shape descriptor; no mark", "family": "creative_batch_16", "priority": 9, "expected_value": "Q and U Stage-1 units", "data": ["live_trades/trades-*.jsonl [lookback floor 2026-10-26, S_A + 14 d)", "snapshots/ [S_A - 2 h, S_A + 14 d)", "book_sweeps/ (reported shape)", "creative_batch16/exclusion_keys.csv.gz"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": [], "argv": ["scripts/run_cb16.py", "a-frame", "--window", "screen", "--rules", "../docs/research_lab/seals/cb16_rules.json", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "40", "--budget-min", "35"], "timeout_s": 2700, "max_retries": 2, "outputs": ["research_lab/creative_batch16/a_screen/{fills.csv.gz,manifest.json}"], "next_action": "q0385", "notes": "DRAFT. Refuses before S_A + 14 d + 8 h and without the part-A freeze hash. Restores archived sources byte for byte if needed.", "repeat": {"max_runs": 20, "until_log_regex": "\"status\": \"a_frame_complete\""}}
{"id": "q0385_cb16_census_A", "title": "CB16-A census, counts only: units by label (inside, inconsistent, one-sided, no mark capture yet, censored, genesis, election night, single-grain, tick change); exclusion rates by grain and by x tercile; dropped >= 12 h silences; politics share; gates GQ, GU; power gates GQP and GUP on the pre-fill proxy (SEs only); GAI pair count", "family": "creative_batch_16", "priority": 9, "expected_value": "Q/U gates and MDEs", "data": ["creative_batch16/a_screen/"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0384_cb16_a_frame_screen"], "argv": ["scripts/run_cb16.py", "census", "--family", "A"], "timeout_s": 900, "max_retries": 1, "outputs": ["research_lab/creative_batch16/census_A.json", "trials.jsonl (cb16_descriptive or counted not-run lines)"], "next_action": "q0386", "notes": "DRAFT. No proxy point estimate written (unit-tested)."}
{"id": "q0386_cb16_screen_A", "title": "CB16 Stage 1: Q1 (market-FE grain contrast; composition, calibration and pre-fill placebos; attribution; robustness) and U1 (market-FE silence slope; same structure); GAI; Holm k1 = 2", "family": "creative_batch_16", "priority": 9, "expected_value": "Q1 and U1 verdicts", "data": ["creative_batch16/a_screen/", "snapshots/ (mark captures)"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0385_cb16_census_A"], "argv": ["scripts/run_cb16.py", "screen", "--family", "A"], "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch16/results_A.json", "trials.jsonl (cb16_test + creative_batch_16:Q n_tests=1, creative_batch_16:U n_tests=1)"], "next_action": "advanced: q0387/q0388; ledger", "notes": "DRAFT. Refuses without the A freeze hash, before E011's analysis commit, and before CB3's freeze commit or stop record."}
{"id": "q0387_cb16_a_frame_rep", "title": "CB16 REP_A fill table (features) and raw mark-quote table (bid/ask at mark captures; no mark-out computed), event-disjoint from SCREEN_A; source-file sha256 seal", "family": "creative_batch_16", "priority": 9, "expected_value": "Stage-2 inputs, sealed", "data": ["live_trades/, snapshots/, book_sweeps/ for [S_A + 7 d, S_A + 28 d + 8 h)"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0386_cb16_screen_A"], "argv": ["scripts/run_cb16.py", "a-frame", "--window", "rep", "--rules", "../docs/research_lab/seals/cb16_rules.json", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "40", "--budget-min", "35"], "timeout_s": 2700, "max_retries": 2, "outputs": ["research_lab/creative_batch16/a_rep/", "docs/research_lab/seals/cb16_a_rep_SEAL.json (committed by the coordinator)"], "next_action": "q0388 if triggered", "notes": "DRAFT. Runs whatever Stage 1 found (sealing is outcome-blind).", "repeat": {"max_runs": 20, "until_log_regex": "\"status\": \"a_rep_complete\""}}
{"id": "q0388_cb16_rep_A", "title": "CB16 Stage 2: Q1-rep, Q2 (recorded-touch maker round trip on bot-grain fills), U1-rep (SCREEN_A frozen SD(x)), U2 (within-market avoided-fill difference primary, avoided-fill level second); pooled GAI; early alpha/4", "family": "creative_batch_16", "priority": 9, "expected_value": "Stage-2 verdicts (L2)", "data": ["creative_batch16/a_rep/"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0387_cb16_a_frame_rep"], "argv": ["scripts/run_cb16.py", "rep", "--family", "A"], "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch16/results_A_rep.json", "trials.jsonl (cb16_replication + creative_batch_16:<Q|U>:rep)"], "next_action": "q0392", "notes": "DRAFT. Verifies the REP_A seal hash first. Only triggered tests."}
{"id": "q0389_cb16_u_validity", "title": "CB16-U validity (reported only): Data API trades before tau for a seeded sample of 300 wake-up and 300 non-wake-up SCREEN_A units; all-size silence shares", "family": "creative_batch_16", "priority": 5, "expected_value": "whether large-print silence tracks market silence", "data": ["public Data API", "creative_batch16/a_screen/ (unit ids and tau only)"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "net", "network": "data-api"}, "depends_on": ["q0384_cb16_a_frame_screen"], "argv": ["scripts/run_cb16.py", "u-validity", "--rps", "2", "--seed", "16131", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 2700, "max_retries": 2, "outputs": ["research_lab/creative_batch16/u_validity/", "trials.jsonl (cb16_descriptive)"], "next_action": "label every U line if the wake-up share < 50%", "notes": "DRAFT. side, proxyWallet, names and hashes discarded at parse; prints at or after tau never stored."}
{"id": "q0392_cb16_stage2_final", "title": "CB16 Stage-2 final: one strict Holm (one-sided alpha 0.05) over every triggered CB16 Stage-2 test (<= 4; U2 enters with the max of its two component p's); adds passes only (checks_ok and (early alpha/4 or Holm reject)); write-once", "family": "creative_batch_16", "priority": 9, "expected_value": "final Stage-2 decisions", "data": ["creative_batch16/results_*_rep.json"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu"}, "depends_on": [], "argv": ["scripts/run_cb16.py", "stage2-final"], "timeout_s": 600, "max_retries": 1, "outputs": ["research_lab/creative_batch16/stage2_final.json"], "next_action": "Stage P registration drafts for survivors", "notes": "DRAFT. Refuses with 'nothing to finalise' if no family triggered."}
```

## 5. Code needed (not written by this document)

- `backend/astrolabe/research_lab/cb16_common.py`. Reuse `cb15_common` / `cb13_common` for: refused roots, disk guards,
  manifests and `*_complete` status, the small-G cluster p engine, strict Holm and `stage2_final`, per-part rules
  hashing, whitelist readers, `restore_from_archive` hooks, and `shared_helper_sources_sha256` (CB13 fix E). New: pinning
  of the CB13 functions Q and U call (fill, touch-consistency, marks, LABELLER), with sha256 verification.
- `cb16_a.py`: transaction aggregation and the CB13-T fill rule (imported); grain (`round(1000·P) mod 10`), YES-terms
  handling, the tick and band rules; the silence state (`τ_prev`, prior gaps, the lookback floor, the global
  monitor-gap detector, genesis, the wake-up rule); the election-night exclusion; market-FE OLS with multi-way cluster p;
  the stratified permutation placebos with the ≥ 50% both-grain-strata informativeness rule; pre-fill placebo;
  attribution (Q with `x`, U with `g`); the spread-free mark, the mark-out decomposition and the tight-touch stratum; the
  exclusion-by-grain table and `β_Q,worst`; exclusion rates by `x` tercile; the ≥ 12 h dropped-silence count; the
  touch- and mark-capture tick rule; SCREEN_A's frozen `SD(x)` for U1-rep; robustness; GQG, GQ, GU, GQP, GUP (SE-only proxy),
  GAI; Q2 and U2 round trips (CB13-T3 rule imported); the REP_A seal and event-disjointness; the reduced shape
  descriptor (reported); the q0389 Data API client (newest-first paging to the first print before `τ`; forbidden fields
  dropped at parse).
- `cb16_k.py`: streaming field-restricted readers for `poly_markets.json` and `kalshi_markets*.jsonl`; the strict label
  from `matches_all.json` minus r1 conflicts; the loose topic rule with a close-day index (tokeniser and stopwords
  imported from `cross_venue`); the unlistable regex; the FAR-TOPIC label; cells; counts; MDE bounds; the re-entry verdict. No outcome field
  is ever parsed (unit-tested with fixtures carrying them).
- `backend/scripts/run_cb16.py` with the §4 subcommands. It refuses analysis before the part's freeze hash.
- Tests (`test_cb16_a.py`, `test_cb16_k.py`, `test_run_cb16.py`):
  - forbidden-field fixtures and refused roots;
  - window edges: `S_A` from a freeze at 23:59Z versus 00:01Z; the lookback floor; J4-R and CB13-T HOLDOUT refusals;
    the election-night edges;
  - grain edge cases and YES-terms conversion; the tick rule; `P` at exactly 0.05 and 0.95 included, 0.0499 excluded;
  - single-grain markets out of the statistic;
  - the monitor gap at 15 min versus 14 min 59 s; 4 versus 5 prior gaps; genesis at 24 h exactly;
  - the wake-up rule at the 90th percentile and at the 1 h floor;
  - market FE cancelling a per-market constant; the stratified permutation never moving a label across strata;
  - GQP and GUP writing SEs only; GAI at 199 versus 200 pairs;
  - Q2 fees, position clip and worst case; U2's p as the max of its two component p's; REP_A event-disjointness
    binding when thinned; the composition placebo failing at 49% both-grain strata and informative at 50%; a tick
    change between touch and mark capture excluded; U1-rep refusing a REP_A-computed `SD(x)`; the stale-touch and shape
    outputs carrying no p-value;
  - K: an outcome field present in a fixture never parsed; topic rule edges (3 d; 2 words; Jaccard 0.30); FAR-TOPIC
    edges (30 d and 180 d) and its disjointness from PRESENT-TOPIC; the unlistable conflict count; the smoke failing on
    any count other than 148,384 / 326,380 / 958;
  - `battery2` kinds; k1 = 2 fixed; the Stage-2 early α/4 and the final Holm adding passes only.

## 6. Test budget and compute

| Job | Tests counted | Kind(s) | Decision |
|---|---|---|---|
| Stage 1: Q1, U1 | **2** | `cb16_test` + count lines `:Q` (1), `:U` (1) | p < 0.01 strict, floor, binding placebos and robustness, batch Holm (one-sided α 0.05, k1 = 2 fixed); counted with p = 1 if a smoke, gate or availability check fails |
| Stage 2: Q1-rep, Q2, U1-rep, U2 (each only if triggered) | ≤ 4 | `cb16_replication` + `:<family>:rep` | one CB16-wide strict Holm (early finishers at α/4; U2 enters with the max of its two component p's; the final can only add passes) |
| Smoke, censuses (including all of K), gates, strata, sports arms, shape, validity, decomposition and exclusion tables, the H withdrawal record | 0 | `cb16_descriptive` | - |
| **Total** | **2 fixed + ≤ 4 conditional = 2-6** | | value at the run after the host union (1,255 on HEAD at drafting; not stable) |

**Host compute.** Under 3 CPU-hours in all at nice 19:
- Q/U frames: about 170 captures per window, streamed;
- K: one heavy streaming job of about 1 h at 1.2 GB, run alone.

Peak RAM is 1.2 GB (q0383), otherwise ≤ 0.8 GB. **Network:** ≤ about 4,000 requests (q0380, q0389). **Disk:** ≤ 0.15 GB.

**Calendar (all UTC; what must exist by when).**

| By | Deliverable | Owner |
|---|---|---|
| 2026-10-19 | challenger round 1 (done: Q REVISE, U REVISE, K ACCEPT with fixes, H WITHDRAWN) and this response | `science-reviewer`, orchestrator |
| 2026-10-26 | rules parts `common`, `A`, `K`; q0381 smoke code; q0380 behind CB15 q0340 | implementer, queue |
| 2026-10-28 | q0381 PASS; q0382 (GQG) after CB13 q0271; q0383 (K census) | queue |
| 2026-10-31 | A code (frame, census, screen, rep) with tests; code-against-design freeze check (part A) | implementer, `science-reviewer` |
| **2026-11-01 00:00** | **part A frozen** (target; otherwise `S_A` slides with the freeze, and the window lengths stay fixed) | orchestrator |
| `S_A` + 14 d + 8 h | q0384 → q0385 → q0386 (after E011's analysis and CB3's freeze); q0389 | queue |
| `S_A` + 28 d + 8 h | q0387 (seal), then q0388 if triggered; q0392 | queue |

## 7. Main scientific risks (for the challenger)

Revised after round 1; the items of §9 are cited.

1. **Grain is a proxy for quoter type.** Bots quote whole cents too, a person can type 0.555, whole cents are focal
   prices, and sub-cent quoting tracks tight spreads. Guards:
   - the composition placebo, which now fails if fewer than 50% of fills sit in both-grain strata (item 4);
   - the tight-touch stratum (item 2);
   - the attribution regression, now including `x` (item 7).

   "Within market" still assumes grain regimes are comparable over a market's life.
2. **Mechanical half-spread.** `M` contains the realised half-spread, and sub-cent quotes sit nearer the mid (item 1).
   The spread-free mark `d·(mid_h − mid_0)` must hold with at least half of `β_Q`. Its anchor `mid_0` is the capture mid,
   up to 60 min old, so the spread-free mark is noisier than `M` and can lose power.
3. **Grain-dependent exclusion** (item 3). It is visible in the by-grain table and bounded by `β_Q,worst`, but the bound
   is a label, not a gate.
4. **Q is borderline-powered** (planning MDE 0.55-1.1c, floor 0.5c, gate 1.0c). The spread-free mark and the tight-touch
   stratum lower its effective power further. GQP may stop it (counted).
5. **U is relative silence in active markets** (item 9), on the large-print stream. The validity line (q0389) is
   reported, not a gate. Global-silence gap detection could miss partial outages. Exclusion by `x` tercile is reported
   (item 13). HB1 IX3's opposite sign and HB1 MS2 are disclosed neighbours (item 12). U's object is close to E011's
   detector; the guards are the calendar and the absence of E011 strata.
6. **Q and U share units and mark-outs**, so their tests are correlated. Each enters the other's attribution.
7. **The cadence is still 2 h.** GAI checks print/mid agreement. Q2 and U2 are recorded-touch round trips with queue
   position ignored (upper bounds). U2's primary is now the cost-neutral within-market difference (item 11). It tests
   protection value only.
8. **Calendar.** SCREEN_A spans the US election run-up and REP_A the post-election resolution wave (item 20). REP_A's
   event-disjointness binds even if thinned, and the politics share is reported per window. Collection overlap with CB3's
   Stage 2, E011 and other live stages; availability risks (snapshot retention, the monitor cap) are never back-filled.
9. **K is a census, not a test.** ABSENT is "no liquid-universe twin" (item 14). FAR-TOPIC is defined and counted now
   (item 15). The smoke's counts are exact (item 16).
10. **Probe audit trail** (item 18). The probe texts and raw counts are committed, but they are reconstructions, and the
    bytes that ran have no hash.
11. **Reuse of CB13 code by pin.** CB16 keeps its pins and records any divergence. If CB13-T's labeller audit fails, Q
    and U use only its SPORTS-FEED class.

## 8. Next actions

1. Round 1 is answered (§9-§10). Next review: the code-against-design freeze check (`science-reviewer`), part A first;
   it may reopen any round-1 item. Left open to it:
   - the adverse-quantile definition of `β_Q,worst`;
   - the 300-fill minimum of the tight-touch stratum;
   - the ≥ 50% informativeness threshold;
   - the 60 s reaction delay in U2.
2. Implementer: rules parts `common`, `A`, `K` and the q0381 smoke by 2026-10-26; A code with tests by 2026-10-31.
3. A order: q0380 (behind CB15 q0340) → q0381 → q0382 (GQG and the CB13-SCREEN dropped-silence count, after CB13 q0271)
   → A freeze by 2026-11-01 → SCREEN_A collected by the running collectors → q0384 → q0385 → q0386 (after E011's
   analysis commit and CB3's freeze) → REP_A → q0387 → q0388 if triggered → q0392.
4. K: q0383 any time after q0380 and q0381. Ledger line with the counts (including FAR-TOPIC) and the re-entry verdict.
5. Ledger: one descriptive line for the H withdrawal and one for this draft and response (design only, not counted).
   CB17 adds CB16's frame ids. Checkpoint and plain-English dashboard are updated by the orchestrator.

## 9. Challenger review, round 1 (science-reviewer, 2026-10-19)

**Verdicts: overall REVISE. CB16-Q REVISE, CB16-U REVISE, CB16-K ACCEPT with fixes, CB16-H WITHDRAW uncounted now.** 20
items. Line references are to `f78a396`.

*Q.*
1. `M = d·(mid_h − P)` includes the realised half-spread. Sub-cent quotes sit nearer the mid, so `M` is mechanically
   lower by about 0.1-0.9c, roughly the floor. Add a binding robustness on `d·(mid_h − mid_touch)` and report the
   decomposition.
2. The strata take their spread from a touch up to 60 min old. Add a binding stratum (touch age ≤ 20 min and spread ≤ 1c);
   if it fails, the label is "grain or contemporaneous spread state".
3. The touch-consistency rule drops sub-cent quotes inside a stale spread, a grain-dependent exclusion. Report inside and
   inconsistent rates by grain, with a worst-case bound.
4. The placebo cells (market × 4 × 3 × 3) are often single-grain, so the placebo passes by default. Require at least 50%
   of fills in strata with both grains, else the placebo FAILS.
5. Require `order_price_min_tick_size = 0.001` at the touch **and** mark captures.
6. Rewrite the calibration-placebo criterion as "advance rate ≤ 1.5%".
7. Q's attribution should include `x` where defined (U's includes `g`).
8. The stale-touch grain and the shape tercile split are report-only, with no p-values, and never promotable.

*U.*
9. The rule of at least 5 prior gaps in 7 days excludes dead books, CH132's object. Retitle as "relative large-print
   silence in active markets", and report how many ≥ 12 h silences (G1b: 459 + 127) it drops.
10. U1-rep must use SCREEN_A's frozen `SD(x)`, not REP_A's.
11. U2's +0.5c exit-cost robustness is vacuous. Make the within-market difference primary (cost-neutral), drop the cost
    check, and let the Holm use the max of the two p's.
12. Disclose HB1 MS2 (`last_trade_age` → `|move|` 6 h; failed BY). It is not a re-run (unsigned move versus mark-out).
13. Report exclusion rates by `x` tercile.

*K.*
14. Disclose ABSENT label noise from the Kalshi universe filters (multivariate, < 5,000 contracts, settled within 12
    months).
15. The re-entry placebo ("Kalshi close ≥ 30 days away") contradicts the 3-day topic rule. Define the label and count it
    in q0383 now.
16. Remove "or the file's own count". Make the CB13 reproduction check independent of q0271, or failing when q0271 is
    absent.

*H.*
17. **Withdraw uncounted now.** The MDE is 12-20c against a 4c gate. The trigger depends on R1's outcome on the same
    units, which is post-selection. No R result exists, so the withdrawal is outcome-blind (CB15-L precedent). Keep only
    the fresh-frame re-entry note.

*Common.*
18. Probe audit trail: the probe scripts were deleted from `/tmp`. Recreate and commit the exact script text (or sha256)
    and the raw counts; until then "no outcome seen" is unauditable, and the document must say so.
19. Fix "nothing above q0323" (q0340-q0346 exist).
20. SCREEN_A spans the election run-up and REP_A the post-election resolution wave. Declare event-disjoint REP_A binding
    even if thinned, and report the politics share per window.

## 10. Response to challenger round 1 (2026-10-19)

No CB16 quantity has been computed, so every change below was made blind. None relaxes a floor, threshold, gate, alpha
or cap. **k goes from 2 fixed + ≤ 6 conditional (2-8) to 2 fixed + ≤ 4 conditional (2-6)**, only through the H
withdrawal. k1 stays 2. The Stage-2 early rule goes from α/5 to α/4, because the largest possible Stage-2 count fell from
5 to 4; this follows mechanically from the withdrawal and is not a relaxation of any test's rule. The cumulative count is
1,255 at drafting and is unchanged by this response.

| Item | Decision | Where | What changed |
|---|---|---|---|
| 1 half-spread | **Adopted, with one stated modification** | §CB16-Q mechanism, mark-out, Q1 | Binding spread-free mark `d·(mid_h − mid_0)`; the decomposition is reported for every Q line. **Modification (tightening):** the spread-free estimator must keep the sign **and at least half of `β_Q` with one-sided p < 0.05**, not just the sign. A sign-only check would let a mostly mechanical contrast through |
| 2 contemporaneous spread | **Adopted** | Q1 | Binding tight-touch stratum (age ≤ 20 min, spread ≤ 1c). If it fails, or is "unknown" with fewer than 300 fills, the label is "grain or contemporaneous spread state", never "quoter grain" |
| 3 grain-dependent exclusion | **Adopted, with one stated modification** | Q population, reports | Inside, inconsistent, one-sided and no-mark rates by grain. **Modification:** the worst-case bound `β_Q,worst` fills excluded units at their grain's adverse quantile of included `M` (10th for bot-grain, 90th for human-grain), weighted by exclusion rate. It is reported with a label ("grain-dependent exclusion could explain the contrast") rather than gating, because excluded transactions have no reliable side `d`, so any bound rests on an assumed mark-out. A label states that assumption without letting it veto a measured result. The freeze check may make it binding |
| 4 placebo informativeness | **Adopted** | Q1 | At least 50% of fills in both-grain strata, else the composition placebo FAILS and Q1 cannot advance |
| 5 tick at both captures | **Adopted** | Q population, GQG | Tick 0.001 at the touch and 2-4 h mark captures; a change is "tick change", excluded and counted. GQG, which opens no marks, checks the touch capture only |
| 6 placebo wording | **Adopted** | Q1 | "advance rate ≤ 1.5%" |
| 7 symmetric attribution | **Adopted** | Q1 | `x` (with a missing indicator) enters Q's attribution |
| 8 report-only variants | **Adopted** | Q reports | No p-values; never promotable to a test, trigger or Stage-2 object |
| 9 dead books | **Adopted** | title, §0, premise 3, §CB16-U | Retitled "relative large-print silence in active markets"; the dropped ≥ 12 h silences are counted on SCREEN_A (q0385) and on CB13-T SCREEN features (q0382) against G1b's 459 + 127 |
| 10 frozen SD(x) | **Adopted** | U state, U1-rep, rules part A | SCREEN_A's `SD(x)` is written to its result file and used by U1-rep; a REP_A-computed `SD(x)` is refused (unit-tested) |
| 11 U2 cost check | **Adopted** | §2.1, §2.3, §2.4, U2 | The within-market difference is primary (floor ≤ −0.5c); the avoided-fill level (≤ −1.0c) is the second component; U2's p is the max of the two; the +0.5c check is dropped |
| 12 HB1 MS2 | **Adopted** | §0.2, U mechanism | Disclosed as a neighbour (unsigned 6 h move model; failed BY); not a re-run. The formal prior-work check is closed with no re-run |
| 13 exclusion by x | **Adopted** | U reports | Rates by `x` tercile |
| 14 ABSENT noise | **Adopted** | §CB16-K labels | Universe filters disclosed; the label is "ABSENT (liquid-universe)" |
| 15 re-entry placebo | **Adopted** | §CB16-K | FAR-TOPIC (same text rule, `30 d ≤ |Δclose| ≤ 180 d`, disjoint from PRESENT-TOPIC) is defined and counted in q0383; the re-entry rule requires at least 30 FAR-TOPIC events in at least 5 eligible cells |
| 16 smoke counts | **Adopted** | §CB16-SM | Exact 148,384 / 326,380 / 958 or FAIL. The CB13 reproduction is computed from raw files by the pinned functions and an independent re-implementation, never from q0271 output; a missing raw file fails |
| 17 H | **Adopted (withdrawn uncounted)** | header, §0, §0.1, §0.4, §1-§2, §CB16-H, §4-§8 | H removed; q0390 and q0391 retired; part H dropped from the rules; fresh-frame re-entry note kept; one descriptive line |
| 18 probe audit trail | **Adopted, with one stated modification** | §0.3, `probes/cb16_design_20261019_probes.txt` | The script texts, every run in order (including the empty stub run and the superseded wrong-split run) and the raw printed counts are committed. **Modification:** an exact-byte sha256 is impossible, because the host copies were deleted. The texts are reconstructed from the drafting session's record, and §0.3 states that "no outcome seen" therefore rests on that reconstruction and is not independently verifiable. Future CB16 probes are committed before they run |
| 19 queue ids | **Adopted** | header | `queue/` holds q0340, q0341 and q0343-q0346; nothing above q0346 |
| 20 election calendar | **Adopted** | §1.2, Q Stage 2 | Event-disjoint REP_A binds even if thinned; the keep-variant is report-only; the politics share is reported per window |

**Rejected:** none.
