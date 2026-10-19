# Creative batch 16 (CB16): quoter grain, wake-up prints (large-print silence), the Kalshi-absent map (census only), hedging skew nested behind CB13-R

`evidence_role: prospective` (CB16-Q and CB16-U: both stages run on live host windows that start after the freeze) /
`exploratory_historical` (CB16-K census, counts only; CB16-H on CB13-R's frame) | status: **DRAFT. Design only. Nothing
frozen, nothing queued, no code, no challenger round yet.** Drafted 2026-10-19 10:20 UTC+1 (2026-10-19T09:20Z) on parent
`ca8468c`. **No CB16 quantity has been computed:** no mark-out, slope, contrast, Brier residual, touch outcome or net.
For CB16, only two read-only, counts-only host probes were run (§0.3). Nothing was fetched, written, moved or deleted on
the host.

This file turns four round-7 ideas from `CREATIVE_HYPOTHESES_2026-10-21.md` into declared, falsifiable designs:
- **CH131** (quoter-type footprint) becomes **CB16-Q**.
- **CH132** (wake-up prints) becomes **CB16-U**.
- **CH143** (the Kalshi-absent class map) becomes **CB16-K**. K is a **census only, with no counted test**: its own
  population count already rules out power (§0.3, §CB16-K).
- **CH138** (hedging-premium skew) becomes **CB16-H**. H is **nested behind CB13-R**: it runs only if CB13-R1 advances
  at Stage 1, and only if H's rules part is committed before CB13's R screen (q0282) first runs.

The file follows `CREATIVE_BATCH_15.md` (CB15) and `CREATIVE_BATCH_13.md` (CB13) in structure and rules. "As CB15 §x"
means that rule applies unchanged, including the challenger and freeze-check fixes it inherits from CB13 and CB14. CB4
amendment A-C1 and the CB10 §2.3 small-G rule govern clusters.
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim. AREPO never
  trades. Every P&L is a paper rule at recorded prices (prints and capture touches).
- Test tables bind only once the CB16 declaration hash is committed (`model_specs/cb16_v1.json`). That needs a challenger
  round (§7) and a code-against-design freeze check first. Rules are fixed in `seals/cb16_rules.json`, **hashed per part
  (`common`, `A` for Q and U, `K`, `H`)**. A, K and H therefore bind on their own calendars, and no rule of one part
  changes after another part's read.
- **Lanes.** Q, U and K need **no network**. They run on the `cpu` lane on files already on the Oracle host, or on files
  the running collectors will write. Two jobs touch the network:
  - the exclusion-key increment q0380 (Gamma ids only);
  - the U validity sample q0389 (reported only; Data API).

  Both run on the `net` lane at **priority 5-9, below every CB6-CB15 job**. No CB16 object is bound to `T_seal`, and no
  CB13, CB14 or CB15 job waits for CB16.
- **Queue ids q0380-q0409, one id per job, no letter suffixes.** CB15 §0.1 reserves q0340-q0379, so CB16 starts at
  q0380. Checked at drafting: `queue/jobs/` and `queue/drafts/` hold nothing above q0323. Used: q0380-q0392; **q0393-q0409
  reserved**. Specs are drafts **in this document only** (§4).
- **Naming.** Outputs go under `research_lab/creative_batch16/`. CB16 writes no `history/` root: Q, U and K fetch
  nothing, H reads CB13's roots, and q0389 writes only under `creative_batch16/u_validity/`.

## 0. Summary, selection and scope

| Rank | Family | Hypothesis | Counted tests | Stage 1 data | Stage 2 data | Queue ids |
|---|---|---|---|---|---|---|
| 1 | **CB16-Q** quoter grain (CH131) | Among large taker transactions that fill a resting quote (CB13-T's frozen print-anchored, touch-consistent fill rule), fills whose maker-adverse price `P` is on a **sub-cent grain** ("bot-grain") have a better 2-4 h maker mark-out than **whole-cent** fills ("human-grain") in the same market. The test is a within-market contrast of at least +0.5c per filled share (Q1) | Q1 (within-market grain contrast) | host files only: live-monitor prints and complete-universe captures in **SCREEN_A**, a 14-day live window that starts after the A freeze | the same stores in **REP_A**, the next 14 days: Q1-rep; Q2 (maker round trip at the recorded print and touch, on bot-grain fills) | q0381, q0382, q0384-q0388, q0392 |
| 2 | **CB16-U** wake-up prints, **large-print silence** (CH132) | The longer the silence before a large print, measured against the market's own large-print inter-arrival times over the prior 7 days, the worse the maker's 2-4 h mark-out on that fill (within-market slope ≥ 0.5c per SD of standardised log-silence; U1) | U1 (within-market slope) | as Q (the same fills; silence comes from the monitor stream) | REP_A: U1-rep; U2 (avoided-fill economics of a paper maker that steps aside for 2 h after a wake-up print) | q0381, q0384-q0389, q0392 |
| - | **CB16-K** Kalshi-absent map (CH143) | **Census only (k = 0).** Counts twin labels (strict matcher, loose topic rule, Kalshi-unlistable text rule) by class × volume-decile cell, plus feature-free MDE bounds. No outcome and no price is read | none | the host's `cross_venue/` files (148,384 Polymarket markets; 326,380 Kalshi markets; 958 matches), counts only | none (a counted design waits for a later batch, §CB16-K) | q0383 |
| - | **CB16-H** hedging skew, **nested behind CB13-R** (CH138) | In weekly crypto barrier events, at matched standardised distance and checkpoint, dip rungs are overpriced relative to their touch outcome by at least 2c more than reach rungs (`Δ_Y ≥ 2c`; H1). **Runs only if CB13-R1 advances at Stage 1** | H1 (conditional) | CB13-R's SCREEN units (`h13_touch`, `h13_binance`; R's frozen units, prices and kline outcome) | CB13-R's sealed HOLDOUT, read after CB13 q0283: H1-rep | q0390, q0391, q0392 |

**Counted: 2 fixed (Q1, U1) + up to 6 conditional (Q1-rep, Q2, U1-rep, U2, H1, H1-rep) = 2-8** (§2.5). **k1 = 2**
(family A). H1, if triggered, forms its own one-test Stage-1 family (§2.3), so the A family never changes after a CB13
result. The budget is fixed now, and no CB16 test is added after any CB16 read.

**Honest expectation.**
- **U1** is the only test whose planning MDE lies at or below its floor.
- **Q1** is borderline: planning MDE 0.55-1.1c against a 0.5c floor, with a 1.0c power gate.
- **K** cannot be powered with any feasible data: 92 non-sports events hold a strict Kalshi twin (§0.3).
- **H** will probably never be triggered (CB13-R1 is expected to be "not run (power)"). If it is triggered, it is
  expected to fail its own power gate.

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
| q0390 | `cb16_screen_H` (H1; gate GHP) | H | only if CB13-R1 advanced and H's part was committed before CB13 q0282's first run; after q0282 |
| q0391 | `cb16_rep_H` (H1-rep) | H | only if H1 advanced; after CB13 q0283 |
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

  IF-H1's `dormant` concerns wallets, not markets. The formal check is a `science-reviewer` repo step in challenger
  round 1. If it finds a re-run, U is withdrawn uncounted before its rules bind.
- *K.* CH25 is the sign of the Polymarket-Kalshi level gap on politics. The C1 study, CB5-K, CB12-X, CB15-P and
  E009/E010 use matched pairs for leads, gaps and births, never for calibration by twin presence.
- *H.* CB13-R tests the level confusion (touch versus terminal) and reports reach and dip separately as robustness and
  descriptive strata. CH17 and CH60 concern longshot selling; CH89 the Deribit anchor. No test has measured the reach/dip
  sign asymmetry.

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
   therefore "large-print silence", and it says so in its title. The trade samples record `time_since_last_trade_s` at
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
   path shock. Its honest unit is the asset-week (CB13's window component), and the cross-asset ISO week (G ≈ 74 in
   CB13-R's SCREEN) binds (§CB16-H power).

### 0.3 Feasibility probes (counts only; 2 read-only host probes; 0 keyless GETs; nothing stored)

Both probes ran over `ssh oracle` as `nice -n 19` streaming Python, with the script in `/tmp` (removed after the run).
Peak memory was under 200 MB. Nothing in `~/arepo/run/queue` was touched. **No outcome, resolution, mark-out, forward
price or wallet was read or printed.**

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
| **CH132** wake-up prints | **include (U), counted, same windows as Q** | Host-only. The prior-work pre-check passes (§0.2), and the population is large (G1b). Honest weaknesses: this is large-print silence, not market silence (premise 3). HB1 IX3's opposite sign is a prior against it. Scheduled events wake markets for public reasons, which dilutes the effect but does not bias it |
| **CH143** Kalshi-absent map | **census only (K, k = 0)** | The strict present arm holds 92 non-sports events (G2). The planning MDE is about 4-6 pp against the 1 pp floor (§CB16-K), and at the historical rate of about 90-100 strict non-sports twin events a year, no feasible prospective collection reaches about 360. A counts-only census of a loose topic-twin label, audited, decides whether a counted K is worth designing in a later batch. No outcome is read, so that later design stays blind |
| **CH138** hedging skew | **include (H), conditional on CB13-R1 advancing; rules bound before CB13 q0282** | This nesting is the brief's. Two further reasons: (i) H's standardised distance and matching rest on R's reflection anchor, so H is uninterpretable if that anchor carries no information; (ii) CB13-R's screen writes reach and dip strata on the same units, so H must be bound before them. Honest weakness: the planning MDE is 12c or more against a 2c floor even if triggered (premise 6). No feasible collection fixes this, because the asset-week is the unit (§CB16-H) |
| CH142 series launch window | not in CB16 | Its descriptive arm is host-only, but "first event" needs a `/series` fetch and its anchored arm needs each family's anchor. It is a map, so it goes to a later batch with CH143's topic census |
| CH139, CH134, CH135, CH136 | not in CB16 | Each needs a fresh keyless fetch (`h15_*`), a calendar source or a per-country adapter. The brief asks for host-testable ideas |
| CH133 depth fade | not in CB16 | Sealed stream (E009/E010 to 2026-11-03). Re-entry after their analyses are committed |
| CH137, CH140, CH141 | not in CB16 | Thin populations by round 7's own counts |

**Sports and categories.** `CB16_SPORTS_IN_PRIMARY = false` (a parameter, as in CB8-CB15). Q and U exclude the pinned
CB13 LABELLER's SPORTS-FEED class from the primary and report the sports arm uncounted. A counted sports arm would be a
later registration, never a change to CB16. Every Q and U statistic is also reported, uncounted, by LABELLER class. K
cells are LABELLER class × volume decile. H is crypto by construction (barrier templates), with category fixed by the
template, not chosen.

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Prior use | Role in CB16 | Evidence ceiling |
|---|---|---|---|
| `live_trades/trades-YYYYMMDD.jsonl` (host; live large-trade monitor, cash ≥ $1,000) for `[S_A − 7 d, S_A + 28 d + 8 h)` | collection tooling; CB13-T uses `[10-12, 10-16)` and `[t_j4r_end, 10-26)` | **Q and U units**: fills (CB13-T rule) and large-print silence. Whitelisted fields only (§1.4). The lookback before `S_A` reads `ts` and `condition_id` only | SCREEN_A and REP_A: post-freeze live data (L2 data; Stage-1 screen role on SCREEN_A) |
| `snapshots/<capture>/rows.csv.gz`, `rows_ext.csv.gz` (complete-universe 2 h captures) for the same span | E001-E011, CB1-CB13 | the touch that signs a fill; tick size; mark quotes; labeller sidecar fields | as above |
| `book_sweeps/` (same span) | E003, CB3, CB13 (depth, reported) | Q's reduced shape descriptor, **reported only** | - |
| CB13-T SCREEN fill table (`creative_batch13/`, q0271 output; features only) or the raw `[10-12, 10-16)` files through the pinned CB13 fill functions | CB13-T Stage 1 | **q0382 grain census only** (grain shares, both-grain market counts). Never a Q or U statistic | counts |
| `cross_venue/poly_markets.json`, `kalshi_markets*.jsonl`, `matches_all.json` (host; 2026-10-12; sha256 pinned at q0381) | C1 study, CB5-K, CB12-X, CB13 (H10, labeller writing), CB15-P | **K census**, field-restricted: Polymarket id, question, event id and title, scheduled `endDate`, neg-risk ids, lifetime `volume` (cell variable, hindsight, labelled); Kalshi ticker, title and subtitle text, `close_time`, category, `volume`; match ids. **`outcome_prices`, `closed_time`, Kalshi `result` and `settlement_value` are never parsed** | counts |
| `history/h13_touch`, `history/h13_binance` (CB13-R; SCREEN; HOLDOUT under `holdout/`) | CB13-R | **H units** through CB13-R's frozen unit builder, price rule and kline outcome (R's code, sha256-pinned). HOLDOUT is opened only by q0391, after CB13 q0283 has opened it and the seal hash verifies | L1 (R's frame reused, declared) / L2 (R's sealed HOLDOUT) |
| Data API `/trades` (q0389; public, keyless) | many | all-size silence before a seeded sample of SCREEN_A units: prints before `τ` only, `ts` and price only. **Reported validity line** | - |
| `surprise_live/` (E011), `cross_venue_live/` (E009/E010), `e001/`-`e007/`, `forecasts/`, `flow_screen/`, `trade_samples/`, `cb3_extract/`, `cb3_followup/`; `live_trades/{alerts,outcomes,wallets,stats}.jsonl`, `scores-*.jsonl`, `state.json`; every `h15_*` root | registered experiments, monitor alert stream, other batches | **never opened by any CB16 path** (runner refuses; unit-tested) | - |
| `h1_*` … `h14_*` (except H's read of `h13_touch` / `h13_binance` above), every `creative_batch1..15/` except the CB13-T fill table for q0382 | worn, sealed or batch-owned | **not read**, except id and timestamp columns for exclusion keys through a field-restricted accessor; no `holdout/` path except q0391's | - |

**Reuse disclosure.**
- *Q and U:* SCREEN_A and REP_A do not exist at drafting. They are collected by the running collectors and read under
  a frozen plan. They overlap other batches' live stages in time (§1.3).
- *K:* the files are worn: the C1 pairs drive E009's design, CB5-K, CB12-X and CB15-P. K reads only ids, texts, dates
  and volumes, and writes counts.
- *H:* the SCREEN frame is CB13-R's (L1 reuse). Its outcomes are computed by R's frozen code from Binance klines, never
  from Gamma.

### 1.2 Dates (declared; UTC)

| Name | Value | Meaning |
|---|---|---|
| `T16_draft` | 2026-10-19T09:20Z | this draft; no CB16 quantity computed |
| `T16_A_freeze` | target **2026-11-01T00:00Z** (soft) | part A frozen (`model_specs/cb16_v1.json` part A, pinning the rules and the CB13 functions it calls) |
| `S_A` | `max(2026-11-02T00:00Z, the first 00:00Z at or after T16_A_freeze + 24 h)` | start of SCREEN_A. It depends only on the freeze time, never on data |
| SCREEN_A | fills with venue `τ ∈ [S_A, S_A + 14 d)` | Q and U Stage 1 |
| REP_A | fills with `τ ∈ [S_A + 14 d, S_A + 28 d)` | Q and U Stage 2 (event-disjoint from SCREEN_A; §CB16-Q) |
| U lookback | large prints with `ts ∈ [max(τ − 7 d, 2026-10-26T00:00Z), τ)`; fields `ts`, `condition_id` only | silence standardisation. **The floor 2026-10-26T00:00Z keeps every lookback outside J4-R and CB13-T's HOLDOUT** |
| election-night exclusion | fills with `τ ∈ [2026-11-03T18:00Z, 2026-11-05T00:00Z)` | excluded and counted (CB15-E's object window and a one-off regime). Silence that spans it is measured as usual |
| marks | first complete capture with `received_utc ≥ τ + h`, usable iff `received_utc ≤ τ + h + 2 h` (CB13 §2.2) | realised 2-4 h ("2 h") and 6-8 h ("6 h") |
| `T16_K_census` | after q0380 and q0381 PASS | K is counts only; K units are historical (scheduled `endDate` in `[2025-10-13, 2026-10-01)`) |
| `T16_H_bind` | **before CB13 q0282's first run** (the R screen) | H's rules part must be committed by then. Otherwise H is withdrawn uncounted (§CB16-H) |
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
- **CB13-R and CB16-H.** H reads R's units only through R's frozen code. H's rules must bind before R's screen writes the
  reach/dip strata (`T16_H_bind`). H opens R's HOLDOUT only after CB13 q0283 has verified and opened the seal. No H
  output can stand in for an R result, and no R line cites H.
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
  K reads no outcome. H's outcome is R's kline-computed touch, opened only by q0390 and q0391; the Gamma outcome is never
  opened by H.

### 1.4 Rules files

- `seals/cb16_rules.json` (before q0381), hashed per part:
  - **`common`**: refused roots; seeds; bootstrap and small-G settings; Holm settings (k1 = 2 for family A, 1 for
    family H); disk guards; field whitelists; smoke criteria; the key rule; the pinned sha256 of the CB13 functions and
    the LABELLER Q and U call.
  - **`A`**: windows and `S_A` rule, the election-night exclusion, the fill and touch-consistency rules (CB13-T's, by
    pin), eligibility, the grain rule, the price band, the tick rule, the silence rule, the global monitor-gap detector,
    the wake-up definition, the mark rules, cluster ways, placebo strata, attribution covariates, gates (GQG, GQ, GU,
    GQP, GUP, GAI), Q2 and U2 rules, the REP_A event-disjointness rule, the reported shape descriptor, and the q0389
    sample rule.
  - **`K`**: file sha256s, field lists, the loose topic rule, the unlistable regex, the cell definition, the MDE bounds,
    and the re-entry rule.
  - **`H`**: the trigger, cells, bins, the statistic, ways (R's), the calibration placebo, robustness, GHP and its
    loadings (R's GRP, by pin), and H1-rep minimums.
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
| Q1, U1, H1 (and their reps) | none charged (mechanism contrasts on maker mark-outs; H1 is a calibration contrast). Q1 and U1 are in maker-mark-out units, a mid exit: **upper bounds** for any maker, labelled so |
| Q2 (Stage 2) | CB13-T3's rule on **bot-grain** REP_A fills: maker entry at the recorded print's maker-adverse price `P` (maker fee 0, no rebate); exit as a taker at the recorded adverse touch of the 2-4 h mark capture (bought → `bid_h`; sold → `ask_h`); taker fee `r·x(1 − x)` on the exit, `r` = the sidecar fee rate, `max_if_unknown` (unknown → 0.07); position `min(print size, 100)` shares (CB13 fix D). **Label: "fills like the bots' fills; queue position ignored, so an upper bound"** |
| U2 (Stage 2) | the same round trip on **avoided fills**: REP_A fills in the same market with `τ ∈ (τ_w + 60 s, τ_w + 2 h]` after a wake-up print at `τ_w` (§CB16-U). The protected maker's net on the remaining fills is reported |
| Binding cost robustness | Q2: +0.5c on the exit keeps net > 0. U2: +0.5c on the exit keeps the avoided-fill net ≤ −1.0c |

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
- **H.** CB13 §2.2 (R's `p_t`, `S_t`, `σ_t`, the guarded kline accessor; candles usable at `o + 65 s ≤ t`).
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
- **Ways (H).** CB13-R's four: Gamma event, ISO week of the checkpoint, asset × ISO week, window component.
- **Testability minimums.** Q: ≥ 1,000 eligible fills in markets with both grains, in ≥ 100 such markets and ≥ 60 events.
  U: ≥ 1,000 standardisable units in markets with ≥ 5 units, in ≥ 100 markets and ≥ 60 events. H: CB13-R's GR counts on
  the cell set (≥ 30 window components holding at least one cell). Below these, the test is "not testable
  (population)", counted with p = 1.
- **Stage 1, family A (Q1, U1).** A test advances iff all of these hold:
  - one-sided p < 0.01 (strict);
  - the §2.4 floor;
  - every binding placebo, robustness check and gate;
  - a batch Holm step-down at one-sided α = 0.05 over **k1 = 2** (fixed; the first step is 0.025, so any p < 0.01
    passes).

  BY (q = 0.10 over `battery2.cumulative_count()` at the run) is triage only.
- **Stage 1, family H (H1, if triggered).** A separate one-test family: one-sided p < 0.01 strict, the floor, and every
  binding check. It never enters family A's Holm, so a CB13 result cannot change A's decision rule after the fact.
- **Stage 2.** One CB16-wide strict Holm at one-sided α = 0.05 over every triggered Stage-2 test (≤ 5: Q1-rep, Q2,
  U1-rep, U2, H1-rep), each in its Stage-1 or declared direction. A test that finishes before k2 is known is judged at
  **α/5** (strict). Each test records `checks_ok`, meaning every binding check other than the primary p gate (CB13 fix A).
  The final Holm (q0392) is applied once and can only add passes. Labels:
  - Q1-rep and U1-rep: "later live window replication, event-disjoint (L2)";
  - Q2 and U2: "recorded-touch round trip (L2)";
  - H1-rep: "out-of-time replication on CB13-R's sealed window (L2)".
- **Stage P** is a separate registration for any survivor (§2.9).

### 2.4 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate |
|---|---|---|
| Q1 | mechanism contrast | `β_Q ≥ +0.5c` per filled share (CH131's floor), with the sign: bot-grain fills better for the maker |
| U1 | mechanism slope | `β_U ≥ +0.5c` per SD of standardised log-silence (CH132's floor), with the sign: longer silence worse for the maker |
| Q2 | economic, recorded prints and touches | net ≥ **+0.5c** per filled share after the exit fee |
| U2 | economic (protection value) | avoided-fill net ≤ **−1.0c** per filled share, **and** at least 0.5c below the same markets' other REP_A fills (within market) |
| H1 | calibration contrast | `Δ_Y ≥ +2c` (CH138's floor), and the sign holds in each of the two largest underlyings |
| Q1-rep, U1-rep, H1-rep | as Stage 1 | as Stage 1 |

### 2.5 Counting (M3 rule)

- Kinds **`cb16_test`**, **`cb16_replication`** and **`cb16_descriptive`** (EXCLUDE), mirroring CB15's
  `battery2.KIND_RULES` entries; unknown kinds raise. Descriptive lines cover: the smoke; censuses; gates; the grain
  census; the whole K census; class strata; the sports arms; the shape descriptor; the stale-touch variant; the 6-8 h
  readings; the q0389 validity sample; H's "not triggered" or "withdrawn" record; the price-side skew `Δ_p`.
- **Count lines (`ml_explain` `n_tests`):** `creative_batch_16:Q` **1**, `creative_batch_16:U` **1**, and
  `creative_batch_16:H` **1** (written only if triggered). Replication lines `creative_batch_16:<family>:rep` carry that
  family's triggered tests (Q ≤ 2, U ≤ 2, H ≤ 1).
- **Triggers.** Q1-rep and Q2 iff Q1 advanced. U1-rep and U2 iff U1 advanced. H1 iff CB13-R1 advanced at Stage 1 **and**
  H's part was committed before CB13 q0282's first run. H1-rep iff H1 advanced and CB13 q0283 has opened R's HOLDOUT.
- **Cumulative count:** 1,255 on HEAD at drafting (`battery2-count-v1`), not stable; recorded at each run. **CB16 adds 2
  fixed tests and up to 6 conditional ones. Budget: 2-8.** K adds nothing (no counted test was ever declared). H adds
  nothing unless triggered.
- Tests behind a failed or unknown gate are "not testable" or "not run" (p = 1) and are **still counted**. The gates
  are: the smoke, disjointness, GQG, GQ, GU, GQP, GUP, GAI, GHP, availability, and the Stage-2 minimums. A job waiting
  on exit 75 is "pending" and writes no line.
- **Withdrawals that stay uncounted (declared now).**
  - U is withdrawn if the formal prior-work check finds a re-run before part A is committed.
  - H is withdrawn if CB13 q0282 runs before H's part is committed.

  In both cases no rule had bound and no CB16 outcome had been seen (CB15-L precedent).

### 2.6 Placebos and robustness (common)

As CB15 §2.6: each binding placebo names the alternative it guards against; calibration placebos are judged on p alone;
200 draws; **advance rate ≤ 1.5%**; seeds 16101-16130. Following the CB12-X lesson, **the composition placebo is
primary for Q and U, not secondary.**

Common binding robustness for any advance:
- (i) the §2.1 cost robustness;
- (ii) p and the floor still hold without the top 5 clusters of each way;
- (iii) Q and U: leave-one-day-out (p < 0.05 and the sign); H: each SCREEN half by window end;
- (iv) unavailable units are excluded and counted, never imputed; if the available share is below 60% of eligible
  units, the test is "not testable (availability)".

### 2.7 Pre-freeze census and gates (counts only)

Outcome guards come first, with field-restricted accessors. A unit test asserts that no census path receives a mark
quote, a capture row received after a fill's `τ`, a kline at or after an H unit's `t`, an outcome, or a later price
used as a target. Per-part gates are in §3:
- **Q:** GQG (pre-freeze, q0382), then GQ, GQP and GAI (q0385/q0386);
- **U:** GU, GUP and GAI;
- **K:** the counts-only re-entry rule;
- **H:** GHP.

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

The funnel is: screen (Stage 1 on SCREEN_A, or R's SCREEN for H) → gates, placebos, robustness → replication (Stage 2
on REP_A, or R's HOLDOUT for H) → a separate prospective confirmation (Stage P) → economic validation at recorded prices
with fees, spread and depth.
- **Stage P-Q / P-U** (only if Q2 or U2 passes). Fresh live windows after REP_A. The touch is read **at the print**
  (a CLOB `/book` read triggered by the monitor's receipt; queue position unknown and disclosed), depth is recorded, and
  the grain rule or wake-up rule is frozen from CB16. The economic test is a passive paper maker that quotes beside
  bot-grain books (Q) or steps aside after wake-ups (U), with passive and taker exits both reported. **A protection
  rule is a route only if the protected maker's own net is positive**; every maker cell so far has been negative.
- **Stage P-H** (only if H1-rep passes). Barrier ladders listed after the Stage P freeze; a daily 00:00Z CLOB `/book`
  read of every rung; selling dip-rung YES (buying NO at the recorded ask) when `p − q ≥ 5c`, held to resolution; the
  crypto fee; the tail gate (net reported with and without the worst 5% of weeks, and only the former counts).
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

The composition placebo and the attribution regression exist for these three objections.

**Population (q0384; frozen in part A).** Monitor transactions with `τ` in SCREEN_A, minus the election-night exclusion;
binary markets; LABELLER class not SPORTS-FEED (`CB16_SPORTS_IN_PRIMARY = false`); key drops (§1.3).
- **Fill and side:** CB13-T's frozen rule by pin. A transaction is a unit iff it is touch-consistent with the latest
  complete capture touch (age ≤ 60 min, two-sided, spread ≤ 10c, touch mid in [0.03, 0.97], capture `end_date ≥ τ + 3 h`).
  The maker direction is `d` (maker sold YES: `d = −1`, `P = P_min`; maker bought YES: `d = +1`, `P = P_max`). Inside and
  inconsistent transactions are excluded and counted.
- **Grain arm eligibility:** the touch capture's sidecar `order_price_min_tick_size = 0.001`, and `P ∈ [0.05, 0.95]`
  (premise 1: the tails are on a 0.001 tick for everyone).
- **Grain:** `g = 1` (bot-grain) iff `round(1000·P) mod 10 ≠ 0`; `g = 0` (human-grain) otherwise. `P` is the
  maker-adverse price (the best level the taker lifted), so `g` is the grain of the best resting quote at the print. Only
  that level's grain is used; deeper levels lifted in a sweep are other makers and are not classified.
- **Both-grain markets:** the statistic uses markets with at least one fill of each grain in the window. Single-grain
  markets are counted and reported.

**Mark-out.** `M_h = d·(mid_h − P)` cents per share, as CB13-T, labelled "2-4 h" (primary) or "6-8 h". Wide-mark and
closed-before-mark units are counted and enter the worst case below.

**Q1 (within-market grain contrast).** `β_Q` is the coefficient on `g` in an OLS of `M_2-4h` on `g` with **market fixed
effects**, one unit per fill (unweighted). It is one-sided > 0 with floor +0.5c, and p is the max over the event,
path key × 6 h block, 6 h block and hour-of-day ways. Leave-one-day-out must keep p < 0.05 and the sign.
- **Binding composition placebo (primary).** Permute `g` within strata of (market × touch-spread band {≤ 1c, 1-2c, 2-5c,
  > 5c} × `P` band {[0.05, 0.20), [0.20, 0.80], (0.80, 0.95]} × transaction-size band {< $2.5k, $2.5-10k, ≥ $10k}).
  200 draws, seed 16101, advance rate ≤ 1.5%. *Alternative guarded:* grain proxies the spread state, price level or size
  of the moment, not the quoter.
- **Binding within-market calibration placebo.** Permute `g` within market × UTC hour (200 draws, seed 16102). The
  observed p must exceed the 1.5% advance rate. *Alternative guarded:* within-market dependence makes the clustered p
  anti-conservative.
- **Binding pre-fill placebo.** The same estimator with `M` replaced by the pre-fill move: the capture mid change from
  the capture before the touch capture to the touch capture, signed by `d`. It must not pass p < 0.01. *Alternative
  guarded:* within-market trends that coincide with grain regimes.
- **Attribution (binding for the label "quoter grain").** A market-FE OLS of `M_2-4h` on `g` plus the touch-spread band,
  `P` band, size band, touch-age band {≤ 20, 20-60 min}, time-to-end band {< 1 d, 1-7 d, > 7 d}, reward band
  (`clob_rewards` present or not), 6 h block of day and log capture liquidity. The label "quoter grain" is credited only
  if the `g` coefficient keeps at least half of `β_Q`; otherwise the label is "composition, not grain".
- **Robustness (binding; each keeps the sign):** touch age ≤ 20 min; the 6-8 h mark; the adverse-touch mark (CB13-T)
  with wide-mark and closed-before-mark units at their adverse touch or worst case; excluding transactions ≥ $10,000;
  each maker side; market-weighted means; `P ∈ [0.10, 0.90]`; reward-band markets alone and others alone (each if ≥ 300
  fills); top-5 drops by event and by path key × block.
- **Reported (uncounted):**
  - `β_Q` by LABELLER class and in the sports arm;
  - the stale-touch variant (grain of the capture touch's third decimal; round 7's original arm);
  - the single-grain markets' mean `M` by grain;
  - **a reduced shape descriptor** where a sweep row of age ≤ 2 h exists: the touch size's share of `depth_1c` on the
    lifted side, `depth_5c/depth_1c`, and `n_levels`. Its tercile split of `M`, within market, is reported only (premise
    2), with the sweep coverage share.

**Gate GQG (grain informativeness; q0382; pre-freeze; features only).** On CB13-T's SCREEN fill table (or the pinned
fill functions on the raw `[10-12, 10-16)` files), among eligible non-sports fills, GQG passes iff:
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

**Stage 2 (conditional; q0387, q0388).** REP_A, same frozen rules, **event-disjoint**: REP_A drops every Gamma event
with a SCREEN_A fill, counted. If more than 40% of REP_A fills are dropped, the lines carry "REP_A thinned by event
overlap" and a variant that keeps them is reported. Q1-rep needs the GQ minimums on REP_A, else "not run (power)",
counted.
- **Q1-rep:** the Stage-1 statistic, placebos and robustness.
- **Q2 (economic; triggered by Q1; needs the pooled GAI PASS):** the CB13-T3 round trip (§2.1) on bot-grain REP_A fills,
  one-sided > 0, floor +0.5c, robustness +0.5c on the exit; the worst case (wide-mark and closed-before-mark units at
  the adverse extreme) keeps p < 0.01. This is expected to be hard, because the exit pays a half-spread and a fee against
  the maker's realised spread.

### CB16-U: Wake-up prints, large-print silence (CH132)

**Question.** Within a market, is the maker's 2-4 h mark-out on a large fill worse the longer the market's large-print
stream had been silent before it, measured against that market's own recent inter-arrival times?

**Mechanism.** In a dead book the resting quotes are the oldest on the venue. A taker who wakes the market has usually
read something: a wire, a filing, a sibling market. **Who pays:** whoever is resting. **Against it:**
- HB1 IX3 found flow in quiet markets continuing *less* (−0.17c), the opposite sign;
- scheduled events (game starts, releases, deadlines) wake markets for public reasons;
- this is large-print silence, not all-size silence (premise 3).

**Population (q0384).** Q's units, without the grain-arm eligibility. Any tick and `P` in [0.03, 0.97] (CB13-T's touch
mid rule) qualify. A unit additionally needs:
- **standardisable silence:** at least 5 uncensored prior gaps in the lookback (§2.2), and `τ_prev` present;
- not a **genesis** print: the sidecar `created_at` at least 24 h before `τ` (CH22's object, excluded and counted);
- an uncensored silence (no global monitor gap overlaps `(τ_prev, τ)`).

Markets with at least 5 units in the window enter the statistic.

**State.** `x = ln(s) − ln(median of the market's prior gaps)`. **Wake-up** (for U2 and reports) means
`s ≥ max(1 h, the 90th percentile of the market's prior gaps)`, frozen, with no data-derived threshold. SD(x) is
computed on SCREEN_A units, a feature.

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
- **U1-rep:** the Stage-1 statistic, placebos and robustness.
- **U2 (economic; triggered by U1; needs the pooled GAI PASS):**
  - *Avoided fills:* REP_A fills in a market with `τ ∈ (τ_w + 60 s, τ_w + 2 h]` after a wake-up print at `τ_w` in the
    same market. The 60 s delay stands for a maker that watches the public trade feed. AREPO's own monitor lags
    7-9 min and is not the reaction clock.
  - *Statistic:* the CB13-T3 round-trip net on avoided fills, one-sided < 0, floor ≤ −1.0c per filled share, **and** a
    within-market difference (avoided minus the market's other REP_A fills) ≤ −0.5c with one-sided p < 0.05.
  - *Robustness:* +0.5c on the exit; delays of 5 min and of AREPO's actual receipt lag (`recv_ts`, whitelisted for this
    check only) keep the sign.
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
  - **ABSENT:** neither.
  - **UNLISTABLE** (a reported subset of ABSENT): the frozen regex for Kalshi's restricted contract classes
    (assassination, terrorism, war declaration, invasion, military or air strike, nuclear detonation, coup). An
    UNLISTABLE-regex market labelled PRESENT is a "rule conflict", counted.
- **Cells.** CB13 LABELLER class (title-based; pinned) × lifetime-volume decile (hindsight; labelled). SPORTS-FEED is
  reported separately.
- **Counts written.** Markets and distinct events per label and cell. The number of cells holding both a PRESENT label
  and ABSENT with ≥ 30 events each, for strict and for strict ∪ topic. Key overlaps by source (worn calibration sets
  such as `h2_main`, `h3_power` and the T5 frame) as counts. **Feature-free MDE bounds** per label set, at SD 0.10
  (optimistic) and 0.24 (the maximum under calibration):
  `MDE = 3.80 × SD × sqrt(1/G_present + 1/G_absent)` over eligible cells.
- **Re-entry rule (declared; no CB16 test).** A counted K may be designed in a later batch only if all of these hold:
  - the strict ∪ topic label gives at least 5 eligible cells and an optimistic MDE ≤ 2 pp;
  - a seeded blind audit of 100 PRESENT-TOPIC pairs (`science-reviewer`, titles only, seed 16141) finds at least 90% to
    be genuine same-event twins;
  - the later design names a composition placebo that keeps topic but removes the arbitrage channel. The candidate is
    "topic twins whose Kalshi close is 30 or more days away", which share the confounders but not a same-date contract.

  Otherwise CH143 is recorded as "not testable at the floor with available or feasibly collectable data".

### CB16-H: Hedging-premium skew in barrier ladders (CH138). Nested behind CB13-R

**Gate (binding; declared before any R result).**
1. **Trigger:** CB13-R1 advanced at Stage 1 (CB13 `results_R.json`, verified hash). "Not run (power)", "not testable" or
   a failed R1 means H is **not triggered**: one descriptive line, uncounted.
2. **Binding precondition:** H's rules part is committed before CB13 q0282's first run. Otherwise H is **withdrawn
   uncounted**. The reason is that R's screen writes reach/dip slopes and strata on these units, which would expose H's
   object. Re-entry is then only on a fresh frame (weekly ladders ending on or after 2026-10-01, prospective) under a
   new design.
3. H uses R's frozen units, prices, `q_touch`, σ and outcome code by pin, and changes none of R's rules.

**Question.** At the same checkpoint and the same standardised distance, are dip rungs (downside insurance) more
overpriced relative to their realised touch than reach rungs (upside lottery)?

**Mechanism.** Holders buy "dip to" YES as insurance and speculators buy "reach" YES as lottery tickets. The put skew is
among the most persistent premia in listed options. **Who pays:** insurance buyers. **Against it:**
- the lottery premium (CH17) has the opposite sign;
- a trending sample (premise 6) moves `Δ_Y` by drift alone.

**Cells.** Within an R primary (weekly) event `e` and checkpoint `t`, units are binned by `z = |ln(B/S_t)|/(σ_t√τ)` into
{[0, 0.5), [0.5, 1.0), [1.0, 1.5), [1.5, 2.5)}. A cell needs at least one reach and one dip unit (R's eligibility:
undecided, `p_t ∈ [0.03, 0.97]`, kline-covered).

**H1.** `Δ_Y,c = mean_reach(Y − p_t) − mean_dip(Y − p_t)` per cell. `Δ_Y` is the mean over cells, with each event
weighted 1 and split equally over its cells. It is one-sided > 0, floor 2c, p = max over R's four ways, and the sign
must hold in each of the two largest underlyings.
- **Binding calibration placebo.** One coin per window component swaps the reach/dip labels of all its cells; 200 draws,
  seed 16121.
- **Binding drift robustness.** An OLS of the component-level `Δ_Y` on that component's realised standardised return
  `ln(S_T/S_t)/(σ_t√τ)`, averaged over its cells: the intercept keeps the sign and at least half of `Δ_Y`. *Alternative
  guarded:* an up-trending SCREEN period makes reach rungs touch more often.
- **Robustness (binding; sign):** each SCREEN half by window end; `σ × 0.8` and `σ × 1.2` for the bins; BTC alone; top-5
  drops by event, week and component.
- **Reported (uncounted):** the price-side skew `Δ_p = mean_dip(p − q_touch) − mean_reach(p − q_touch)` per bin (model
  relative; no outcome); and `Δ_Y` by bin and asset.

**Power gate GHP (feature-only; R's GRP machinery by pin).** One latent per (asset, window, direction) with R's declared
loadings and reach/dip opposition, on H's actual cell structure; 500 draws, seed 16122. Then
`MDE_H = 3.80 × max(SD(Δ_Y*), mean SE per way)`. If `MDE_H > 4c` (2 × floor), H1 is "not run (power)", counted.

**Power (planning, honest).** SD(`Δ_Y`) per component is about 0.4-0.5, since the path shock enters both sides with
opposite signs. With about 150-300 components, SE ≈ 0.03; on the cross-asset ISO-week way (G ≈ 74), SE ≈ 0.05. So **MDE_H
≈ 12-20c against a 2c floor**, and **H1 is expected to be "not run (power)" if triggered.**
- More data does not help: weeks are the unit, and the venue lists about 52 weekly ladders per asset a year, with the
  assets moving together.
- A return-adjusted (delta-hedged) statistic could shrink the path variance. It is **not adopted**, because it would
  change CH138's declared primary to chase power. It is recorded for the challenger and for any later design.
- The economic question (selling insurance with a tail gate) belongs to Stage P-H at recorded asks.

**Stage 2 (conditional; q0391).** **H1-rep** on R's sealed HOLDOUT (weekly events ending in `[2026-04-01, 2026-10-01)`,
checkpoints ≥ 2026-04-01), opened only after CB13 q0283 has verified the seal. It needs at least 30 HOLDOUT components
holding a cell, else "not run (power)", counted.

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
  - the pinned CB13 fill functions reproduce, on the SCREEN fill table if q0271 has run, the touch-consistency counts
    of two SCREEN captures, counts only;
  - the K readers: streaming, field-restricted reads of `poly_markets.json`, `kalshi_markets*.jsonl` and
    `matches_all.json` reproduce 148,384 / 326,380 (or the file's own count, recorded) / 958, with the sha256s recorded
    and no outcome field parsed.

  Any failure → the dependent part is "not testable (source)": Q1 and U1 counted once each; for K, a descriptive line.
  The smoke file is write-once. A failed smoke makes the part terminal (CB13 fix B).
- **The U prior-work check** (a `science-reviewer` repo step in challenger round 1, before part A is committed): reads
  `flow_screen.py`, HB1 and HB2 tables, the IF-H1 and `sm_learned_v2` specs, and E007's registration. A finding of
  "re-run" withdraws U uncounted.
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
| q0390 | cpu | 9 | ≤ 20 min, mem 800 | CB13 q0282 | only if R1 advanced and H's part predates q0282 |
| q0391 | cpu | 9 | ≤ 20 min, mem 800 | q0390, CB13 q0283 | only if H1 advanced |
| q0392 | cpu | 9 | < 5 min, mem 300 | every triggered Stage-2 test final | once |

```json
{"id": "q0380_cb16_exclusion_keys", "title": "CB16 exclusion keys with per-key source attribution: CB15 q0340 key file (sha256 pinned) + CB15 frame ids (E race map, P pairs, P Stage-2 pairs) + seal copies; Gamma lookups for missing keys", "family": "creative_batch_16", "priority": 9, "expected_value": "Q/U window check; K overlap counts", "data": ["creative_batch15/exclusion_keys.csv.gz", "history/h15_* (id columns only)", "docs/research_lab/seals/*", "public Gamma (ids)"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0340_cb15_exclusion_keys"], "argv": ["scripts/run_cb16.py", "exclusion-keys", "--rules", "../docs/research_lab/seals/cb16_rules.json", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 1800, "max_retries": 2, "outputs": ["research_lab/creative_batch16/{exclusion_keys.csv.gz,manifest.json}"], "next_action": "q0383", "notes": "DRAFT. Never opens holdout/. A dependency recorded as stopped is absent (recorded)."}
{"id": "q0381_cb16_smoke", "title": "CB16 smoke (cpu, no network): part hashes and CB13 pins; refusals on fixtures; grain parser; monitor-gap detector; silence standardiser; CB13 fill-function reproduction (counts); K streaming readers reproduce file counts with no outcome field parsed", "family": "creative_batch_16", "priority": 9, "expected_value": "go/no-go for parts A and K", "data": ["fixtures", "creative_batch13/ (SCREEN fill table features, if present)", "research_lab/cross_venue/{poly_markets.json,kalshi_markets*.jsonl,matches_all.json} (field-restricted)"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": [], "argv": ["scripts/run_cb16.py", "smoke", "--rules", "../docs/research_lab/seals/cb16_rules.json"], "timeout_s": 900, "max_retries": 1, "outputs": ["research_lab/creative_batch16/smoke.json", "trials.jsonl (cb16_descriptive, or counted not-testable lines once)"], "next_action": "PASS: q0382, q0383", "notes": "DRAFT. Write-once."}
{"id": "q0382_cb16_q_grain_census", "title": "CB16-Q grain census, counts only, features only: eligible non-sports CB13-T SCREEN fills by tick, P band, grain; both-grain market share; gate GQG", "family": "creative_batch_16", "priority": 9, "expected_value": "decides whether the grain arm is informative before the A freeze", "data": ["creative_batch13/ SCREEN fill table (features) or live_trades + snapshots [2026-10-12, 2026-10-16) via pinned CB13 fill functions"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0381_cb16_smoke", "q0271_cb13_t_frame"], "argv": ["scripts/run_cb16.py", "q-grain-census"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch16/census_Q_grain.json", "trials.jsonl (cb16_descriptive or the counted Q1 not-testable line)"], "next_action": "PASS: A freeze check", "notes": "DRAFT. No mark quote or capture after any fill's tau is opened (unit-tested)."}
{"id": "q0383_cb16_k_census", "title": "CB16-K census, counts only, no outcome, no price, no network: strict / topic / absent / unlistable labels; LABELLER class x volume-decile cells; events per label per cell; cells with both labels >= 30 events; key overlaps; feature-free MDE bounds; re-entry verdict", "family": "creative_batch_16", "priority": 9, "expected_value": "the CH143 map inputs and the re-entry decision", "data": ["research_lab/cross_venue/{poly_markets.json,kalshi_markets*.jsonl,matches_all.json,audit_flags.json} (sha256 pinned; field-restricted)", "creative_batch16/exclusion_keys.csv.gz"], "resources": {"mem_mb": 1200, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0380_cb16_exclusion_keys", "q0381_cb16_smoke"], "argv": ["scripts/run_cb16.py", "k-census"], "timeout_s": 4200, "max_retries": 1, "outputs": ["research_lab/creative_batch16/census_K.json", "trials.jsonl (cb16_descriptive)"], "next_action": "record in the ledger; topic audit only if the re-entry counts pass", "notes": "DRAFT. Heavy job under the memory rule: run alone. outcome_prices, closed_time, result, settlement_value never parsed."}
{"id": "q0384_cb16_a_frame_screen", "title": "CB16 SCREEN_A fill table, features only: touch-consistent non-sports transactions (pinned CB13-T rule), grain, tick, silence x and wake-up label, global monitor gaps, genesis and election-night exclusions, reported shape descriptor; no mark", "family": "creative_batch_16", "priority": 9, "expected_value": "Q and U Stage-1 units", "data": ["live_trades/trades-*.jsonl [lookback floor 2026-10-26, S_A + 14 d)", "snapshots/ [S_A - 2 h, S_A + 14 d)", "book_sweeps/ (reported shape)", "creative_batch16/exclusion_keys.csv.gz"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": [], "argv": ["scripts/run_cb16.py", "a-frame", "--window", "screen", "--rules", "../docs/research_lab/seals/cb16_rules.json", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "40", "--budget-min", "35"], "timeout_s": 2700, "max_retries": 2, "outputs": ["research_lab/creative_batch16/a_screen/{fills.csv.gz,manifest.json}"], "next_action": "q0385", "notes": "DRAFT. Refuses before S_A + 14 d + 8 h and without the part-A freeze hash. Restores archived sources byte for byte if needed.", "repeat": {"max_runs": 20, "until_log_regex": "\"status\": \"a_frame_complete\""}}
{"id": "q0385_cb16_census_A", "title": "CB16-A census, counts only: units by label (inside, inconsistent, one-sided, no mark capture yet, censored, genesis, election night, single-grain); gates GQ, GU; power gates GQP and GUP on the pre-fill proxy (SEs only); GAI pair count", "family": "creative_batch_16", "priority": 9, "expected_value": "Q/U gates and MDEs", "data": ["creative_batch16/a_screen/"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0384_cb16_a_frame_screen"], "argv": ["scripts/run_cb16.py", "census", "--family", "A"], "timeout_s": 900, "max_retries": 1, "outputs": ["research_lab/creative_batch16/census_A.json", "trials.jsonl (cb16_descriptive or counted not-run lines)"], "next_action": "q0386", "notes": "DRAFT. No proxy point estimate written (unit-tested)."}
{"id": "q0386_cb16_screen_A", "title": "CB16 Stage 1: Q1 (market-FE grain contrast; composition, calibration and pre-fill placebos; attribution; robustness) and U1 (market-FE silence slope; same structure); GAI; Holm k1 = 2", "family": "creative_batch_16", "priority": 9, "expected_value": "Q1 and U1 verdicts", "data": ["creative_batch16/a_screen/", "snapshots/ (mark captures)"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0385_cb16_census_A"], "argv": ["scripts/run_cb16.py", "screen", "--family", "A"], "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch16/results_A.json", "trials.jsonl (cb16_test + creative_batch_16:Q n_tests=1, creative_batch_16:U n_tests=1)"], "next_action": "advanced: q0387/q0388; ledger", "notes": "DRAFT. Refuses without the A freeze hash, before E011's analysis commit, and before CB3's freeze commit or stop record."}
{"id": "q0387_cb16_a_frame_rep", "title": "CB16 REP_A fill table (features) and raw mark-quote table (bid/ask at mark captures; no mark-out computed), event-disjoint from SCREEN_A; source-file sha256 seal", "family": "creative_batch_16", "priority": 9, "expected_value": "Stage-2 inputs, sealed", "data": ["live_trades/, snapshots/, book_sweeps/ for [S_A + 7 d, S_A + 28 d + 8 h)"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0386_cb16_screen_A"], "argv": ["scripts/run_cb16.py", "a-frame", "--window", "rep", "--rules", "../docs/research_lab/seals/cb16_rules.json", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "40", "--budget-min", "35"], "timeout_s": 2700, "max_retries": 2, "outputs": ["research_lab/creative_batch16/a_rep/", "docs/research_lab/seals/cb16_a_rep_SEAL.json (committed by the coordinator)"], "next_action": "q0388 if triggered", "notes": "DRAFT. Runs whatever Stage 1 found (sealing is outcome-blind).", "repeat": {"max_runs": 20, "until_log_regex": "\"status\": \"a_rep_complete\""}}
{"id": "q0388_cb16_rep_A", "title": "CB16 Stage 2: Q1-rep, Q2 (recorded-touch maker round trip on bot-grain fills), U1-rep, U2 (avoided-fill economics after wake-ups); pooled GAI; early alpha/5", "family": "creative_batch_16", "priority": 9, "expected_value": "Stage-2 verdicts (L2)", "data": ["creative_batch16/a_rep/"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0387_cb16_a_frame_rep"], "argv": ["scripts/run_cb16.py", "rep", "--family", "A"], "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch16/results_A_rep.json", "trials.jsonl (cb16_replication + creative_batch_16:<Q|U>:rep)"], "next_action": "q0392", "notes": "DRAFT. Verifies the REP_A seal hash first. Only triggered tests."}
{"id": "q0389_cb16_u_validity", "title": "CB16-U validity (reported only): Data API trades before tau for a seeded sample of 300 wake-up and 300 non-wake-up SCREEN_A units; all-size silence shares", "family": "creative_batch_16", "priority": 5, "expected_value": "whether large-print silence tracks market silence", "data": ["public Data API", "creative_batch16/a_screen/ (unit ids and tau only)"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "net", "network": "data-api"}, "depends_on": ["q0384_cb16_a_frame_screen"], "argv": ["scripts/run_cb16.py", "u-validity", "--rps", "2", "--seed", "16131", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 2700, "max_retries": 2, "outputs": ["research_lab/creative_batch16/u_validity/", "trials.jsonl (cb16_descriptive)"], "next_action": "label every U line if the wake-up share < 50%", "notes": "DRAFT. side, proxyWallet, names and hashes discarded at parse; prints at or after tau never stored."}
{"id": "q0390_cb16_screen_H", "title": "CB16-H (conditional): H1 within-event reach-minus-dip realised overpricing at matched standardised distance and checkpoint on CB13-R SCREEN units; component label-swap calibration; drift-intercept robustness; GHP (R's GRP latents, SEs only)", "family": "creative_batch_16", "priority": 9, "expected_value": "H1 verdict if CB13-R1 advanced", "data": ["history/h13_touch, history/h13_binance (SCREEN only, via pinned cb13_r code)", "creative_batch13/results_R.json (trigger, hash-verified)"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0282_cb13_screen_R"], "argv": ["scripts/run_cb16.py", "screen", "--family", "H"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch16/results_H.json", "trials.jsonl (cb16_test + creative_batch_16:H n_tests=1, or one cb16_descriptive not-triggered/withdrawn line)"], "next_action": "advanced: q0391 after CB13 q0283", "notes": "DRAFT. Refuses unless H's part commit predates q0282's first run (git order). Never opens holdout/ or Gamma outcomes."}
{"id": "q0391_cb16_rep_H", "title": "CB16-H Stage 2: H1-rep on CB13-R's sealed HOLDOUT (>= 30 components with a cell), after CB13 q0283 verified the seal", "family": "creative_batch_16", "priority": 9, "expected_value": "H Stage-2 verdict (L2)", "data": ["history/h13_touch/holdout, history/h13_binance/holdout (via pinned cb13_r code)"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0390_cb16_screen_H", "q0283_cb13_rep_R"], "argv": ["scripts/run_cb16.py", "rep", "--family", "H"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch16/results_H_rep.json", "trials.jsonl (cb16_replication + creative_batch_16:H:rep)"], "next_action": "q0392", "notes": "DRAFT. Verifies seals/cb13_touch_holdout_SEAL.json first."}
{"id": "q0392_cb16_stage2_final", "title": "CB16 Stage-2 final: one strict Holm (one-sided alpha 0.05) over every triggered CB16 Stage-2 test; adds passes only (checks_ok and (early alpha/5 or Holm reject)); write-once", "family": "creative_batch_16", "priority": 9, "expected_value": "final Stage-2 decisions", "data": ["creative_batch16/results_*_rep.json"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu"}, "depends_on": [], "argv": ["scripts/run_cb16.py", "stage2-final"], "timeout_s": 600, "max_retries": 1, "outputs": ["research_lab/creative_batch16/stage2_final.json"], "next_action": "Stage P registration drafts for survivors", "notes": "DRAFT. Refuses with 'nothing to finalise' if no family triggered."}
```

## 5. Code needed (not written by this document)

- `backend/astrolabe/research_lab/cb16_common.py`. Reuse `cb15_common` / `cb13_common` for: refused roots, disk guards,
  manifests and `*_complete` status, the small-G cluster p engine, strict Holm and `stage2_final`, per-part rules
  hashing, whitelist readers, `restore_from_archive` hooks, and `shared_helper_sources_sha256` (CB13 fix E). New: pinning
  of the CB13 functions Q, U and H call (fill, touch-consistency, marks, LABELLER, R units and GRP), with sha256
  verification.
- `cb16_a.py`: transaction aggregation and the CB13-T fill rule (imported); grain (`round(1000·P) mod 10`), YES-terms
  handling, the tick and band rules; the silence state (`τ_prev`, prior gaps, the lookback floor, the global
  monitor-gap detector, genesis, the wake-up rule); the election-night exclusion; market-FE OLS with multi-way cluster p;
  the stratified permutation placebos; pre-fill placebo; attribution; robustness; GQG, GQ, GU, GQP, GUP (SE-only proxy),
  GAI; Q2 and U2 round trips (CB13-T3 rule imported); the REP_A seal and event-disjointness; the reduced shape
  descriptor (reported); the q0389 Data API client (newest-first paging to the first print before `τ`; forbidden fields
  dropped at parse).
- `cb16_k.py`: streaming field-restricted readers for `poly_markets.json` and `kalshi_markets*.jsonl`; the strict label
  from `matches_all.json` minus r1 conflicts; the loose topic rule with a close-day index (tokeniser and stopwords
  imported from `cross_venue`); the unlistable regex; cells; counts; MDE bounds; the re-entry verdict. No outcome field
  is ever parsed (unit-tested with fixtures carrying them).
- `cb16_h.py`: the trigger (hash-verified R result) and the git-order precondition (H part commit before q0282's first
  run, from the queue log and git); cells, bins, `Δ_Y`, the component label-swap placebo, drift-intercept robustness, GHP
  on R's GRP machinery; H1-rep on HOLDOUT through R's seal check.
- `backend/scripts/run_cb16.py` with the §4 subcommands. It refuses analysis before the part's freeze hash.
- Tests (`test_cb16_a.py`, `test_cb16_k.py`, `test_cb16_h.py`, `test_run_cb16.py`):
  - forbidden-field fixtures and refused roots;
  - window edges: `S_A` from a freeze at 23:59Z versus 00:01Z; the lookback floor; J4-R and CB13-T HOLDOUT refusals;
    the election-night edges;
  - grain edge cases and YES-terms conversion; the tick rule; `P` at exactly 0.05 and 0.95 included, 0.0499 excluded;
  - single-grain markets out of the statistic;
  - the monitor gap at 15 min versus 14 min 59 s; 4 versus 5 prior gaps; genesis at 24 h exactly;
  - the wake-up rule at the 90th percentile and at the 1 h floor;
  - market FE cancelling a per-market constant; the stratified permutation never moving a label across strata;
  - GQP and GUP writing SEs only; GAI at 199 versus 200 pairs;
  - Q2 and U2 fees, position clip and worst case; REP_A event-disjointness;
  - K: an outcome field present in a fixture never parsed; topic rule edges (3 d; 2 words; Jaccard 0.30); the
    unlistable conflict count;
  - H: not-triggered and withdrawn paths (no counted line); trigger only on a verified R advance; cells needing both
    directions;
  - `battery2` kinds; k1 = 2 fixed; H's own family; the Stage-2 early α/5 and the final Holm adding passes only.

## 6. Test budget and compute

| Job | Tests counted | Kind(s) | Decision |
|---|---|---|---|
| Stage 1: Q1, U1 | **2** | `cb16_test` + count lines `:Q` (1), `:U` (1) | p < 0.01 strict, floor, binding placebos and robustness, batch Holm (one-sided α 0.05, k1 = 2 fixed); counted with p = 1 if a smoke, gate or availability check fails |
| Stage 1: H1 (only if CB13-R1 advanced and H bound in time) | ≤ 1 | `cb16_test` + `:H` (1) | its own family: p < 0.01 strict, floor, binding checks, GHP |
| Stage 2: Q1-rep, Q2, U1-rep, U2, H1-rep (each only if triggered) | ≤ 5 | `cb16_replication` + `:<family>:rep` | one CB16-wide strict Holm (early finishers at α/5; the final can only add passes) |
| Smoke, censuses (including all of K), gates, strata, sports arms, shape, validity, H not-triggered/withdrawn records | 0 | `cb16_descriptive` | - |
| **Total** | **2 fixed + ≤ 6 conditional = 2-8** | | value at the run after the host union (1,255 on HEAD at drafting; not stable) |

**Host compute.** Under 3 CPU-hours in all at nice 19:
- Q/U frames: about 170 captures per window, streamed;
- K: one heavy streaming job of about 1 h at 1.2 GB, run alone;
- H: R's units only.

Peak RAM is 1.2 GB (q0383), otherwise ≤ 0.8 GB. **Network:** ≤ about 4,000 requests (q0380, q0389). **Disk:** ≤ 0.15 GB.

**Calendar (all UTC; what must exist by when).**

| By | Deliverable | Owner |
|---|---|---|
| as soon as possible (before CB13 q0282) | challenger round 1 on part H; **`seals/cb16_rules.json` part H committed** (rules only; H code can follow, since it changes no rule) | `science-reviewer`, implementer |
| 2026-10-23 | challenger round 1 on parts A and K, including the U prior-work check; response | `science-reviewer`, orchestrator |
| 2026-10-26 | rules parts `common`, `A`, `K`; q0381 smoke code; q0380 behind CB15 q0340 | implementer, queue |
| 2026-10-28 | q0381 PASS; q0382 (GQG) after CB13 q0271; q0383 (K census) | queue |
| 2026-10-31 | A code (frame, census, screen, rep) with tests; code-against-design freeze check (part A) | implementer, `science-reviewer` |
| **2026-11-01 00:00** | **part A frozen** (target; otherwise `S_A` slides with the freeze, and the window lengths stay fixed) | orchestrator |
| `S_A` + 14 d + 8 h | q0384 → q0385 → q0386 (after E011's analysis and CB3's freeze); q0389 | queue |
| `S_A` + 28 d + 8 h | q0387 (seal), then q0388 if triggered; q0392 | queue |

## 7. Main scientific risks (for the challenger)

1. **Grain is a proxy for quoter type.** Bots quote whole cents too; a person can type 0.555; whole cents are focal
   prices; and sub-cent quoting tracks tight spreads. The composition placebo (permuting within market × spread × price ×
   size strata) is the primary guard, and the attribution regression decides the label. Only the top lifted level is
   classified. The challenger should test whether these strata absorb the spread-state channel, and whether "within
   market" is the right comparison when grain regimes change over a market's life.
2. **Q is borderline-powered** (planning MDE 0.55-1.1c, floor 0.5c, gate 1.0c). GQP may stop it (counted). The 14-day
   window is set by the monitor storage cap, not by power.
3. **U measures large-print silence.** The validity line (q0389) is reported, not a gate. Global-silence gap detection
   could miss partial outages, such as a back-paging lag affecting some markets only. Night hours and scheduled events
   are handled by the composition placebo and a binding robustness. HB1 IX3's opposite sign is a prior against U. U's
   object is close to E011's detector; the guards are the calendar (U screens after E011's one-time analysis) and the
   absence of E011 strata.
4. **Q and U share units and mark-outs**, so their tests are correlated. The Holm step treats them as two tests.
   Q's covariate `g` enters U's attribution, so a joint effect is reported, not credited to both.
5. **The cadence is still 2 h.** The fill is anchored on the print and only signed by a touch up to 60 min old (CB13
   round 1 item 1). Marks are 2-4 h and 6-8 h captures, and GAI checks print/mid agreement. Q2 and U2 are recorded-touch
   round trips with queue position ignored (upper bounds) and are expected to fail. U2 tests protection value only, and
   a route would need the protected maker's own net to be positive (§2.9).
6. **Post-freeze live windows in a crowded calendar.** SCREEN_A and REP_A overlap CB3's Stage 2, E011's window and other
   live stages (collection overlap; CB3's freeze and E011's analysis gate the screens). The election-night exclusion is
   a declared calendar rule. Snapshot retention and the monitor's storage cap are risks to availability, never reasons
   to back-fill.
7. **K is a census, not a test.** The decision not to count K rests on G2's 92 strict non-sports events and on
   feature-free MDE bounds. The topic label's validity is unknown until audited, and lifetime-volume selection affects
   both labels. The challenger should judge whether the re-entry rule (≥ 5 eligible cells, optimistic MDE ≤ 2 pp, ≥ 90%
   audit precision, a date-mismatch composition placebo) is strict enough.
8. **H will probably never run.** It needs CB13-R1 to advance, which CB13 itself expects to be "not run (power)", and its
   rules must bind before CB13 q0282. If H does run, its MDE (about 12-20c) is far above the 2c floor, because the
   asset-week path dominates `Δ_Y` and doubles across reach and dip. A trending SCREEN period could produce a spurious
   "insurance premium"; the drift-intercept robustness binds. The return-adjusted statistic was not adopted, because
   adopting it would change the primary to gain power. Should H be withdrawn uncounted now instead, as with CB15-L, given
   that its planning MDE is about 3-5 times the gate?
9. **Reuse of CB13 code by pin.** If CB13's freeze or later fixes change the pinned functions, CB16 keeps its pins and
   records the divergence; it never silently follows. If CB13-T's labeller audit fails, Q and U use only its SPORTS-FEED
   class (§1.3).

## 8. Next actions

1. **Challenger round 1** (`science-reviewer`): **part H first**, because its rules must bind before CB13 q0282. Then A
   and K, including the formal U prior-work check (§CB16-SM). Open items: the composition strata of Q and U, the
   within-market estimator, `S_A` and the window lengths, the election-night exclusion, the 60 s reaction delay in U2,
   K's census-only status and re-entry rule, H's withdraw-or-keep question (risk 8).
2. Response round, then rules parts `common`, `A`, `K`, `H` (implementer). Part H is committed as soon as its round is
   answered, or H is withdrawn uncounted if CB13 q0282 runs first.
3. A order: q0380 (behind CB15 q0340) → q0381 → q0382 (GQG, after CB13 q0271) → A freeze by 2026-11-01 → SCREEN_A
   collected by the running collectors → q0384 → q0385 → q0386 (after E011's analysis commit and CB3's freeze) → REP_A →
   q0387 → q0388 if triggered → q0392.
4. K: q0383 any time after q0380 and q0381. Ledger line with the counts and the re-entry verdict.
5. H: q0390 only if CB13-R1 advanced and H bound in time; q0391 after CB13 q0283 if H1 advanced.
6. Ledger: one line for this draft (design only, not counted). CB17 adds CB16's frame ids. Checkpoint and plain-English
   dashboard are updated by the orchestrator.
