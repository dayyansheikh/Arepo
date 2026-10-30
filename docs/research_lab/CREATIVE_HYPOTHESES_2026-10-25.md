# Creative hypotheses, round 11: paths, families, rules and footprints on the streams the host already captures (2026-10-25)

`evidence_role: none` | status: **IDEAS ONLY, nothing tested, nothing registered.** No edge, calibration, tradability or
profitability claim. AREPO never trades; every "money route" below is a paper rule to be tested on historical data and
then prospectively. Written by the creative-lead pass at the user's request (written 2026-10-21 04:46 UTC+1,
2026-10-21T03:46Z, on parent `cee77db6`, worktree `feat/creative-r11`; the file carries the round's planned date as
earlier rounds did; a first attempt on 2026-10-21 died at a usage limit and nothing of it was saved). Round 1 is
`CREATIVE_HYPOTHESES_2026-10-15.md` (CH01-CH34), round 2 `-16.md` (CH35-CH59), round 3 `-17.md` (CH60-CH78), round 4
`-18.md` (CH79-CH98), round 5 `-19.md` (CH99-CH117), round 6 `-20.md` (CH118-CH130), round 7 `-21.md` (CH131-CH143),
round 8 `-22.md` (CH144-CH155), round 9 `-23.md` (CH156-CH168), round 10 `-24.md` (CH169-CH179); this file starts at
**CH180** and repeats none of them. Where an idea builds on an earlier one, the parent is named and the new mechanism,
clock, target or data join is stated. Every number quoted from an AREPO document is a development, census or probe
result, not evidence. One file; no code, no queue specs, no other commits. **No network request, no host probe and no
`data-dumps` read were used for this round** (by instruction); every count below is taken from round 9's probes (P1,
P1b, P2, P2c), LT3's censuses (C1/C3/C4, C2), the cost-model calibration, the maker-rewards development snapshot or the
WS1 development study, and is named as such. Where no probe exists the count is marked **unprobed** and the
pre-registration census is the first gate.

## 0. How to read this file

**The brief that binds this round (owner priorities, 2026-10-19 and 2026-10-21).** The owner wants original ideas
for how money could be made, new mechanisms rather than textbook re-tests, that can become registered prospective live
tests quickly: on streams the host already captures or a light keyless collector; with many independent units a week
across many events; with a pre-declarable decision time, target and cost-aware paper rule; category-agnostic with
category as a parameter. Since 2026-10-21 the owner's permanent North Star is the **signal engine**
(`signal_engine/NORTH_STAR.md`, `DESIGN_V1.md`): a champion (momentum + market state) plus challengers that each add a
feature family, scored prospectively at every capture on `dir_2h`, `dir_6h`, `dir_24h` and `res_7d`. So every idea here
also states whether it can be expressed as a point-in-time feature family for a challenger, and the feature in one
line. This round's family is **LT5**, registered separately from and after LT4.

**What changed since round 10 (from the ledger, LT3/LT4 files, WS1, COST_MODEL, MAKER_REWARDS_STUDY, DESIGN_V1).**
- **LT3 is E015 only.** The C1/C3/C4 census (q0470) dropped E017 (attention-only surges: 829 projected units against
  2,000; planning MDE 1.83c against 1.0c) and E019 (ladder breadth: 189 high-breadth units against 3,000). The C2
  census (q0472, 2026-10-20 23:45Z) dropped E016 (walked share 9.74% against 10%; 59.6% of ">= 4-decimal" rows within
  1e-4 of the grid; 473 rows in the agreement arm against 500) and E018 (H interior 30.8% against 40%; the same 473
  rows). **Rule for this round: no idea relies on attention surges, ladder breadth, walked orders, trains, or any
  signed-flow moderator that needs the agreement arm.** The trade-sample flow data are thin for *signed* constructs
  (5,093,017 signed rows in two days of samples, but the interesting cells are small); sign-free constructs on the same
  rows are not bound by that gate.
- **LT4 is E020-E022** (arrivals vs cancellations, age of the move, hollow liquidity), proposed window 2026-10-26 to
  2026-11-16. E023 (opens vs closes) and E024 (concentration) were dropped before any census because their only valid
  within-unit check, the residualised donor gate, failed a binding size scenario (rejection 0.085 against 0.075 when the
  tested moderator correlates 0.5 with a controlled moderator that has a real effect). **Rule: every contrast here is a
  within-market class contrast or a slope on a state whose |corr| with the controlled moderators is a census gate
  (<= 0.5), with the Freedman-Lane permutation gate (control-residualised target shuffled within strata) as the only
  binding gate.** The donor gate is a non-binding label everywhere now (LT3 §13.13).
- **WS1 (wallet skill):** P1 pass (top-decile sign-randomisation-skilled wallets persist: 71.2% vs 59.7%); P2-P4 null
  (skilled flow adds nothing over generic flow at 6 h, 24 h or resolution). A copy-skilled live test (E026,
  `feat/copy-skilled`) is in design. **Nothing here is a wallet feature or a copy rule.**
- **CB18 (DRAFT, `feat/cb18`)** took round 10's remainder: CH172 (program vs human), CH175 (last-mid proxy), CH176
  (front page, CB18-F), CH177 (silent edits), CH179 (races, descriptive). **Nothing here touches those five.** CH178 is
  out as a double count of E015.
- **Cost model v1** (`COST_MODEL.md`, calibration 2026-10-16 to 10-19): a $100 taker round trip costs 2.9c at >= $100k
  liquidity, 3.9c at 10k-100k, 7.2c at 1k-10k (medians, both fees); a 5-share touch round trip 4.5c; a passive touch
  order fills 3.1% of the time within an hour and loses 2.38c to adverse selection against a 2 h mark (0.39c at
  >= $100k); hold-to-resolution removes the exit leg. **The only cost regime below 1c is passive entry in >= $100k
  markets held to resolution or long horizons, plus fee-free categories.** So every route here is a maker-selection or
  hold-to-resolution object first, and a taker route only where the counted gross would clear 2.9c.
- **Maker rewards** (`MAKER_REWARDS_STUDY.md`): makers are about break-even per contract before rewards (non-sports
  fill-weighted -0.37c [-0.64, -0.10]); the one lead is fills > 30 days before close (+3.13c share-weighted, 1 of about
  40 cells); 13,683 rewarded markets in a 2026-10-20 snapshot; one-sided quotes score inside [0.10, 0.90], two-sided
  quoting is required outside it. E025 (provisional) is the reward-inclusive maker test.
- **Signal engine v1 is BUILT, not deployed:** features store per capture (`quotes/`, `features/`), families
  market_state, momentum, flow, book, xvenue, wallet, tte; targets `dir_2h/6h/24h`, `res_7d` (Gamma by id, receipt-
  timed); promotion rule `se-promotion-v1`; embargo map for families that shadow sealed tests. A new family here means:
  new columns, a new `FEATURES_VERSION`, a spec that isolates the family, and an embargo entry where it overlaps a
  sealed test's construct.
- **New keyless streams** (predictit, smarkets, espn_odds, gamma_rules) were coded and dry-run on 2026-10-19
  (`NEW_STREAMS_2026-10-19.md`); the documents read for this round do not record the cron install, so **nothing here
  depends on them**; they are mentioned only in section 4.

### 0.1 What round 11 learned from rounds 8-10 and the LT2-LT4 censuses

Six of the eight ideas that reached a census from rounds 9-10 died there, and the deaths have a pattern that is now a
set of design rules for this file.
1. **Rare states die; continuous states on the whole population live.** E017 needed a 3x surge (829 units), E019 an
   80% breadth (189), E016 a walked share above 10% (9.74%), E018 an H interior above 40% (30.8%). E015, E020, E021,
   E022 survive because their state is a label or a continuous quantity defined on every mover. **Rule: every state
   here is defined on every unit of a population counted in the thousands a day, and the material contrast is between
   deciles or classes of that state, never a rare event.**
2. **A state must change within the market, or the unit is not informative.** The within-market demeaned contrast gets
   its information from units whose state differs from the market's own mean. Slow states (a market sitting near its
   high for days) contribute less than their row count suggests. **Rule: for slow states the census counts
   state-change units, the planning DE is 3-5, and dormant units (no change in state or price since k-1) are excluded.**
3. **Correlated moderators need a size-valid gate, and the only one that passed is Freedman-Lane.** **Rule: no distant-
   donor gate, |corr| with controlled moderators <= 0.5 as a census gate, binding size scenarios with a correlated
   control.**
4. **Sign-free beats signed.** Three LT4 survivors need no `side`; the four LT3/LT4 drops that needed signed flow died
   at the agreement arm or the donor gate. **Rule: the sign of every primary here comes from the capture's own mid move
   or from a mechanical rule, never from a print's direction; `side` appears only as a control or in a secondary.**
5. **One value per pass is one value per day** (CH158). **Rule: every state varies within pass and within market.**
6. **Quote anatomy predicts quote targets mechanically** (E019, E012, E020 critiques). **Rule: targets start at the
   decision time's own stream (the sweep when the state is read from a sweep), use skip-slot labels where a bounce
   can sit at the origin, and control E015's anatomy class whenever the unit is a mover.**
7. **Readers run at the pass cadence** (trade samples are retired after three days). **Rule: every trade-sample member
   extends E021's per-pass reader.**
8. **Probed deaths are final.** Round 8 probed comment bursts (9 of 22,111 events changed in 2 h, 0 gained five) and
   cross-event equal-notional baskets (7 a day): both dead at the capture cadence and not revived here. Round 7 parked
   deadline extensions because "no count is possible without a capture walk"; the host now writes 12 captures a day,
   so a counts-only census is an afternoon, and that idea is revived below with that disclosure (CH187).

**Structural facts this round relies on (counts only; sources named; no new probe).**
1. Movers: 77,732 >= 1c a day over 584,022 eligible market-interval pairs (P1, 2026-10-15); non-sports about 2,750 an
   interval (60% quote-only, 27% traded, 13% never-traded). Traded non-sports movers about 8,900 a day; one-sided
   quote-only about 6,600; parallel about 3,050 (P1b).
2. Trade samples: 2,000 markets a pass, the newest 500 taker rows each (`ts, side, price, size, outcome_index, asset,
   tx_hash`); 943-1,080 sampled markets a pass have a taker row in the 6 h window (P2/P2c); 78% of rows have a same-
   market neighbour within 300 s; `ts` is venue seconds; every row is one taker order (P2). LT3 C2 counted 21,311
   covered market-samples in 5,303 events over two days (about 10,700 a day).
3. Sweeps: 65,771 tokens a sweep, two sweeps a pass about two minutes apart, sweep 1 about 8 minutes after the
   capture; `best_bid/ask`, `*_size_1`, `depth_*_1c/5c`, `n_*_levels`, `book_timestamp`, `tick_size`,
   `min_order_size` (round 9; CH147's probe: the touch unchanged within a pass in 90% of books).
4. Sidecar per capture: `fee_type`, `fee_category`, `fees_enabled`, `order_price_min_tick_size`, `rewards_min_size`,
   `rewards_max_spread`, `clob_rewards`, `created_at`, `uma_resolution_statuses`, `event_open_interest`,
   `event_volume`, `event_comment_count`, `series_slugs`, `parent_event_ids`; capture rows carry `end_date`,
   `updated_at`, `neg_risk`, `neg_risk_market_id`, `event_id`, `liquidity`, `volume24hr`, `chg_1h/1d/1w`.
5. Rewards: 13,683 rewarded markets (development snapshot, 2026-10-20); one-sided scoring allowed inside [0.10, 0.90];
   two-sided required outside; sampled once a minute (MAKER_REWARDS §2; CB6-R's convention: 0.90 exactly is inside).
6. Monitor: 10,522 prints >= $1k on 2026-10-15 (22% non-sports), median 9 minutes after venue time; 2,164 non-sports
   prints on 2026-10-16. Unsigned at AREPO's bar (q0400: 93.3% against 97%).
7. Costs: fact set above (cost-model-v1).
8. Engine coverage on 2026-10-20 20:31Z: 46,448 eligible markets; book 98%, flow and wallet 4.3%, xvenue 0.25%.

**The reading that steers this round.** Round 9 read the streams for what they record; round 10 read them for what
they let a reader *name* (an order event, a trade's age, a display). Round 11 reads four things nobody has read:
- **(a) The path.** Every market's capture series has a shape: its own high and low, the volume-weighted price at which
  its recent takers entered, the number of price levels a traded move passed through. The champion's momentum family
  is fixed-horizon changes; the path is a different object, and equity finance has three mechanisms for it (anchoring
  on the high, disposition on the cost basis, jumps versus grinds) that no prediction-market study has tested
  (family A).
- **(b) The family.** A move shared with the market's event, series or category is a different object from a move the
  market made alone; CH158 failed because it read the whole venue once a pass, not each member against its own family
  (family B).
- **(c) The rule.** The liquidity-reward programme pays one-sided quotes inside [0.10, 0.90] and only two-sided quotes
  outside: a venue constant that turns the reward farmers' side choice into a forecast on one side of 0.90 and an
  artefact on the other (family C).
- **(d) The footprint and the record.** Identical sizes at regular intervals are an algorithm without a wallet; the
  makers' post-move skew is their vote; the sidecar's `end_date` moves and sibling births are numeric rule and listing
  events that need no text (family D).

**Data labels.** `A` = on the host now or written by its running collectors (fact set above). `P` = a keyless fetch is
needed (named where light). **Sealed and not usable by anything here:** LT2's `live_tests2/`, LT3's and LT4's stores
once registered, CB16's, CB17's and CB18's stores, CB8-H's holders, E009/E010's `cross_venue_live/` to 2026-11-03,
E011's `surprise_live/` to 2026-11-10, E025's and E026's stores. J4-R `[2026-10-16, 2026-10-21)` is refused for every
maker mark-out object; nothing here is one.

**Windows and registration this round proposes (LT5).** A fifth live-test family, registered separately from LT2-LT4
and after LT4's registration commit, with its own Holm family (k <= 5): origin window of **21 days from the first
00:00Z at least 24 h after the LT5 registration commit and not before 2026-10-30T00:00Z**, a single analysis at least
36 h after the end, a pre-declared 28-day extension only if a declared counts-only gate falls short (read before any
outcome). Collection overlap with LT2 (to 11-12), LT3 (to 11-14), LT4 (to 11-16), E011 (to 11-10), CB18, E025 and
E026 is disclosed and is overlap only: different hypotheses, no pooling, stores never opened by one another. E-numbers
are assigned at registration, not here (E025 and E026 are taken; the next free number is confirmed against the ledger
at registration).

**Hygiene that binds every idea.** Decision time is the latest input's own receipt (`received_utc` of the capture, or
the sweep's or sample's receipt where the state reads one), never a later file; states are computed from that input
and strictly earlier ones; targets are price-based (the next complete captures' mids or the next pass's sweep mid,
J4-R tight at both ends, 2 h / 6 h / 24 h; skip-slot where a taker's own trade or a one-sided quote can sit at the
origin) and never read Gamma outcome fields, except where an idea is explicitly engine-first and uses the engine's
receipt-timed `res_7d` label; clustering is CR1 on event, two-way event x UTC day and UTC day with p the largest, t on
`G_series - 1` and an ex-crypto primary where a series family exceeds 50% of units; **the primary is a within-market
contrast estimated by expanding-past demeaned OLS over all eligible units, with the Freedman-Lane permutation gate as
the binding gate, never a both-class inclusion rule**; sports stays a parameter (the sidecar's `fee_type` plus CB17's
frozen sports list; nothing here is sports-only; every idea reports the sports arm uncounted).

**Scores.** N novelty (1-5), EV expected value if true (1-5), **L live-ready (1-5):** 5 = a pure reader that extends an
existing LT reader by a few columns, population bounded by a named probe, census on worn files; 4 = pure reader,
population unprobed but bounded above by a named probe; 3 = pure reader with an unprobed and possibly small population,
or a parked history; 2 = needs a light `net` collector or a stream whose install is not recorded; 1 = needs fetches,
maps or weeks. My judgement, not measurements.

**Planning-MDE arithmetic used throughout (stated once).** `SE = SD x sqrt(1/n1 + 1/n2) x sqrt(DE)` for a two-class
contrast, `SE = SD / sqrt(n / DE)` per standard deviation of a continuous state, `DE = 1 + (m - 1) rho` for clusters of
mean size `m` and intra-cluster correlation `rho` (event x UTC day clusters hold about 5-15 units; DE 1.5-2.8 for
states that change every interval, 3-5 for slow states, rule 2); MDE = 3.2 x SE (one-sided alpha after Holm k = 5,
0.01, z 2.33, plus z 0.84 for 80% power). SDs: 2 h continuation about 4c, sweep-to-sweep 2 h about 3.5c, 6 h move
about 5c, 24 h move about 6c (rounds 9-10 and LT3/LT4 use the same). The material floor is **0.5c gross per share** in
the favourable class or decile for a mid target; for a resolution target the floor is stated in log-loss (the engine's
promotion rule) and in cents of calibration error.

**Counts table (what was counted before each idea was written; daily unless stated; the probe or census named).**

| ID | Unit | Count on the host | Source |
|---|---|---|---|
| CH180 | sampled traded mover at k with >= 3 taker rows in `[t_{k-1}, t_k)` | <= about 1,000 clocked traded movers a pass (P2 bound); the >= 3-row subset **unprobed** | P2/P2c; E021's census |
| CH181 | eligible market x capture within 1c of a >= 3-day-old own high or low, state changed since k-1 | eligible about 40,000 a capture (engine coverage); near-mark share **unprobed** | DESIGN_V1 §3; P1 |
| CH182 | sampled market x pass with >= 10 rows in the 24 h window | about 10,700 covered market-samples a day (C2); the >= 10-row 24 h subset **unprobed** | LT3 C2; P2/P2c |
| CH183 | rewarded binary market x pass with folded mid in [0.84, 0.96), two-sided | 13,683 rewarded markets (snapshot); band share **unprobed** | MAKER_REWARDS §1; CB6-R |
| CH184 | non-sports mover at k with >= 3 other quoting members in its event, series or category | about 2,750 non-sports movers an interval; family share **unprobed** | P1/P1b |
| CH185 | sampled traded mover at k with >= 4 rows; clip trains by size identity | as CH180; clip share **unprobed** (round 8 fact 7 killed only cross-event 1 s baskets, 7 a day) | P2/P2c; round 8 |
| CH186 | eligible market with >= 7 days of captures; quoted share of its path | about 40,000 a capture; distribution **unprobed** | engine coverage |
| CH187 | non-sports market x capture with `end_date` changed, interior mid | **unprobed** (parked in round 7 for want of a capture walk) | round 7 §4 |
| CH188 | existing member x capture when a sibling first appears in its event | **unprobed**; crypto strike additions expected to dominate (ex-crypto rule) | spec |
| CH189 | market x capture with `t_k > end_date`, interior mid, by-date template | **unprobed** | spec |
| CH190 | mover at k with sweep 1 of pass k, two-sided | about 18,500 non-sports movers a day, all sweep-covered | P1/P1b; round 9 sweep count |

---

## 1. Map: where money might be, given the costs, the nulls and what the streams record

The cost model fixes the frame: a taker needs 2.9c gross in the most liquid tier and 4.5c at the median; a passive
fill costs 2.4c of adverse selection against a 2 h mark but about 0.4c at >= $100k, and nothing on the exit leg if
held to resolution. The replicated predictors (E007's +0.36c flow continuation; the Kalshi 10-20 minute lead) clear
none of the taker hurdles. So the money question for any new state is: **does it move the forecast of the resolution,
or of the 2 h / 24 h mid, in the markets where passive entry costs nothing (>= $100k, fee-free categories), and does it
tell a maker which side to post or when to step aside?** The engine's leaderboard measures the first half (log-loss
gain on `dir_2h` and `res_7d`, by category); E025 part B measures the second (signal-conditional fills). Every idea
below is written to be read by both.

| Family | What the streams record and nobody has read | Money route |
|---|---|---|
| A. The path | the market's own high and low (captures), the recent takers' cost basis weighted by the token they hold (sample rows), the number of price levels a traded move passed through (sample rows + capture pair) | maker: skew toward the mark's side, with the gaining side, away from a broken wall; HTR passive entry in >= $100k markets where the path says the mid is low; taker reported only |
| B. The family | the member's move minus its event's, series' or category's mean move at the same capture | maker: ignore common moves, step aside after idiosyncratic ones; taker follow of idiosyncratic >= 3c moves reported |
| C. The rule | the reward programme's one-sided-inside / two-sided-outside cutoff at 0.10 and 0.90, applied to the sweep's near-touch asymmetry in rewarded markets | maker: inside the band, join the farmers' side; taker reported |
| D. Footprints and the record | identical sizes at regular gaps (an algorithm), the makers' post-move skew (a vote), `end_date` moves and sibling births (numeric rule and listing events) | maker: step aside from a running algorithm, lean with the makers' vote, widen after a deadline move or a sibling birth; taker: deadline-move YES buys and tail-member fades reported |

---

## 2. Hypotheses

### A. The path (parents E002/E004/E006, HB1 PX1/PX2, E015/CH156, E021/CH170, E016/CH161, CH20/CH93, CH42; literature: George and Hwang 2004, Grinblatt and Han 2005, Frazzini 2006, Barndorff-Nielsen and Shephard 2004, Rosu 2009, Avellaneda and Stoikov 2008)

**CH180. Jump or grind: a traded 2 h move made in one step (few distinct print prices relative to the distance moved)
is pent-up demand released through a wall, and continues; the same move made in many small steps (prints at many
levels, each moving the touch) is information absorbed as it arrived, and does not. The path shape is sign-free: the
sign is the move's own, from the capture pair; no `side`, no wallet, no touch-signing.**
- Mechanism and why it is non-obvious. In a limit-order market a large resting order absorbs flow at one price until
  it is exhausted and the price then gaps (Rosu 2009's patient walls; the iceberg-exhaustion pattern in equity
  microstructure; Barndorff-Nielsen and Shephard's jump versus diffusive decomposition). A grind is a reactive maker
  re-pricing on each fill (Avellaneda-Stoikov inventory skew): information is absorbed continuously and the price at
  the end of the interval already reflects it. E015 reads *whether* a move was traded, E021 reads *when* the last trade
  was, E016 read whether single orders walked two levels (and died at 9.74%); nobody reads the *shape of the path
  inside the move*. Who pays: the maker who joins a wall is picked off when it breaks; the taker who chases a grind
  pays a spread for information already in the price. Why the crowd misses it: the chart shows the move, not the
  levels it passed through; the sample's rows do.
- Data join and decision clock (`A`, L 5). Unit: sampled market x pass that is a traded mover at capture k under LT3
  §1.4 eligibility (|x| = |mid_k - mid_{k-1}| >= 1c, `volume24hr` changed, two-sided and tight at k-1 and k, mid in
  [0.02, 0.98], as-of end > t + 3 h) with >= 3 taker rows whose `ts` lies in `[t_{k-1}, t_k)` in the pass's sample
  (coverage rule as E016/E021: the page's oldest row at or before `t_{k-1}`, or the page not full, decided at the
  origin). State: `levels` = number of distinct YES-terms print prices among the interval's rows (outcome-1 prints
  mapped to 1 - price); `steps = |x| / tick` (the sidecar's `order_price_min_tick_size`; units with a tick change in
  the interval excluded; |x| >= 3 ticks required so a 1c move in a 0.01 book is not a jump by construction); grind
  ratio `g = (levels - 1) / steps`, clipped to [0, 1]. Classes: **jump** `g <= 0.25`, **grind** `g >= 0.75`; the
  interior enters the slope secondary only. Decision time: the trade sample's receipt in pass k (minutes after the
  capture; the pass order is snapshot, sweeps, sample). Controls: E015's anatomy label is moot (all traded), E021's
  1[fresh] (age of the last trade), `log1p n_rows`, |x|, spread, logit mid, |mid - 0.5|, lagged volume, tick stratum.
- Target and horizon. `c = sign(x) x (mid_{k+1} - mid_k)` at 2 h (capture k+1 is the first capture after the decision
  time, so the within-pass minutes are skipped by construction); secondary `c6` with the skip-slot label (LT4 L9).
  Hypothesis (one-sided): within market, E[c | jump] - E[c | grind] > 0.
- Paper rule and economic check. Maker: after a jump, do not re-post at the pre-move level for one pass (the wall is
  gone and the continuation is expected); after a grind, quote normally; value = avoided adverse selection, reported as
  "gross, no fills". Taker: follow jumps >= 3c; the gross in the jump class against the cost-model-v1 round trip at the
  recorded touch by liquidity tier (2.9c at >= $100k, 3.9c at 10k-100k, 4.5c at the 5-share median), conservative fee
  policy; reported only, never changes a verdict.
- Units and MDE (3 weeks). Clocked traded movers <= about 1,000 a pass (P2 bound); with >= 3 rows in the interval,
  plausibly 300-600 a pass (unprobed): 76,000-150,000 units in 21 days over all categories, about 40% non-sports. At
  300 a pass, non-sports: 30,000 units, jump 35% (10,600) against grind 40% (12,000): SE = 4c x sqrt(1/10,600 +
  1/12,000) x sqrt(2) = 0.075c, **MDE 0.24c** against the 0.5c floor. At 100 a pass: 0.42c (borderline). The all-
  category primary with sports as a stratum (E021's convention) has about 2.5x the units.
- Confounders and the control. Tick coarseness (0.01 books make jumps by construction: tick stratum, |x| >= 3 ticks,
  census share of jumps from 0.01 books <= 80%); move size and row count (controls); the last trade's age (E021's
  state, controlled; |corr(1[jump], 1[fresh])| <= 0.5 as a census gate); bounce (a jump whose last print sits at the
  origin: the skip-slot `c6` label is binding, the unmoved side's change a reported label); crypto series dominance
  (t on `G_series - 1`, ex-crypto primary if > 50%). Placebo: Freedman-Lane shuffle of the class within market x UTC
  day strata; far-future control (the path shape of an interval that ends after the target, LT2 R1's form) must show
  no contrast.
- Cheapest census (counts only; two worn days of samples; E021's census files). The distribution of `g` over qualifying
  units; the share of units with >= 3 rows. Kill if qualifying units < 120 a pass, if jumps or grinds are each < 20%
  of qualifying units, if > 80% of jumps come from 0.01-tick books, or if |corr(1[jump], 1[fresh])| > 0.5.
- Challenger feature: **yes.** `path_grind_2h = (levels - 1)/steps` and `path_maxstep_share = largest single price step
  between consecutive rows / |x|`, flow-family columns from the pass's sample (NaN below 3 rows). Embargo: shares
  E021's population, not its state; isolated scoring embargoed to 2026-11-17 for safety.
- Scores: N 4, EV 3, L 5. Parents: E021/CH170 (same population and reader), E016/CH161 (the order-level walk; the
  interval path needs no `side` and no 4-decimal rule), CH20/CH93 (walls at round numbers; here the wall is wherever
  it is).

**CH181. The high-water mark: a market within a cent of its own lifetime high (low), set at least three days earlier,
drifts through the mark over the next 24 h, because holders anchor on the salient extreme (the chart's peak), sell at
it and are slow to bid past it; the market's own high is the wall and the under-reaction is the drift. A fixed-horizon
change cannot see this; the path can.**
- Mechanism and why it is non-obvious. George and Hwang (2004) found that nearness to the 52-week high predicts
  returns in equities better than past returns do, and attributed it to anchoring: traders are reluctant to buy above a
  salient reference price, so good news is under-reacted to near the high (and the mirror at the low). A prediction
  market has a sharper version: the price is bounded, the chart on every market page shows the peak, and the resolution
  arrives, so the anchor must give way. No prediction-market study has tested it; AREPO's momentum family is fixed-
  horizon changes (chg 1h/1d/1w, own 2 h/6 h/24 h) and its price-level tests (HB1 PX1/PX2) read the level, not the
  path. Who pays: the holder who sells at the old high to the maker who leans with the break. The FLB is the obvious
  confounder (favourites under-priced near 1): it is a level effect and is controlled by the level.
- Data join and decision clock (`A`, L 4). Captures only. Per market, the expanding maximum and minimum of the two-
  sided mid over the host's capture series (`hi_{k-1}`, `lo_{k-1}`, with the capture index of each, `t_hi`, `t_lo`);
  the series starts at AREPO's first capture of the market (2026-10-09 for pre-existing markets, so the "lifetime" is
  truncated for them: `age_series` is a control and a stratum; markets created after the first capture have the full
  life). State at capture k (decision time: its receipt): `d_hi = hi_{k-1} - mid_k` (>= 0 unless a new high),
  `age_hi = k - t_hi`, and the mirror. Unit: eligible market x capture (LT3 §1.4 eligibility; mid in [0.05, 0.95])
  whose state changed since k-1 (rule 2). Classes: **near** = `d_hi <= 1c` with `age_hi >= 36` captures (3 days: a
  retest, not a fresh high), **far** = `d_hi >= 5c` and `d_lo >= 5c`; the mirror for the low with the sign flipped;
  folded primary `u = s x (mid_{k+12} - mid_k)` with `s = +1` near the high, `-1` near the low. New highs (`mid_k >
  hi_{k-1}`) are a separate secondary class (momentum, not anchoring).
- Target and horizon. 24 h mid change (capture k+12); secondary 6 h; the resolution target is the engine's `res_7d`.
  Hypothesis (one-sided): within market, E[u | near] - E[u | far] > 0.
- Paper rule and economic check. Maker: near the high, do not post asks at the mark (lean with the break); near the
  low, do not post bids at the mark. Taker: buy YES within 1c below a >= 3-day high in >= $100k markets, hold 24 h, 2.9c
  round trip; HTR passive entry (cost about 0 at >= $100k) where `res_7d` is in range; all reported.
- Units and MDE (3 weeks). Eligible about 40,000 a capture; the share within 1c of a >= 3-day mark with a state change
  is unprobed. If 1% of eligible units (400 a capture), 100,000 near units in 21 days against an abundant far class:
  SE = 6c x sqrt(1/100,000 + 1/500,000) x sqrt(4) = 0.042c, **MDE 0.13c**; at a tenth of that (40 a capture, 10,000
  units): 0.13c x 3.2 = 0.42c, borderline. Census gate: >= 400 non-sports near units a day with a state change.
- Confounders and the control. The level (logit mid, |mid - 0.5|, so the FLB is held fixed); momentum (chg 1d/1w and
  own 24 h change held fixed; the >= 3-day age makes "near" a retest); bounce (a one-sided ask at the high leaves the
  mid 0.5c below the mark mechanically: two-sided tight quotes required, the 24 h horizon, the skip-slot label);
  truncated series (`age_series` control and stratum; a sensitivity on markets created after the first capture only);
  round-number marks (CH20/CH93: 1[mark on a 0.05 multiple] as a control); crypto ladders (ex-crypto primary).
  Placebo: Freedman-Lane within market x UTC day; a fake mark (the high of the series excluding the last 14 days) must
  show no contrast.
- Cheapest census (counts only; worn captures, two weeks). Distribution of `d_hi`, `d_lo`, `age_hi`; share of eligible
  units near a >= 3-day mark; share with a state change; share of near units in crypto series. Kill if near units <
  400 a day non-sports, if > 70% are crypto series, or if the within-market SD of `d_hi` is < 1c for half the markets
  with >= 50 captures.
- Challenger feature: **yes.** A new **path** family from the engine's own `quotes/` store: `d_hi`, `d_lo`, `age_hi`,
  `age_lo`, `n_new_highs_7d`, `captures_at_extreme` (consecutive captures with mid >= 0.95 or <= 0.05: the "newly
  certain versus long certain" secondary, the decided-carry family's numeric cousin). No sealed test uses the path, so
  no embargo.
- Scores: N 4, EV 4, L 4. Parents: E002/E004/E006 (reversal of fixed-horizon changes), HB1 PX1/PX2 (level drift),
  CH20/CH93 (round-number walls and breaks), CH42 (disposition sellers at high prices, wallet-level), CH01/CH04/CH134
  (decided carry; the `captures_at_extreme` secondary only).

**CH182. Capital-gains overhang, token-weighted: the gap between the mid and the volume-weighted price at which the
market's recent takers entered is the active holders' unrealised gain; disposition selling by holders in gain caps the
price and the gain continues (Grinblatt and Han 2005); in a two-token market the overhang that matters is weighted by
which token the recent takers hold, so `G = (mid - VWAP) x (s_YES - s_NO)`. Wallet-free, sign-free, from the 500-row
page.**
- Mechanism and why it is non-obvious. Grinblatt and Han show that the disposition effect (selling winners early,
  holding losers) produces under-reaction and that the aggregate unrealised capital gain, measured as the price minus a
  turnover-weighted reference price, predicts returns beyond past returns. In a binary market every holder is long one
  token; YES holders in gain are NO holders in loss. Whose disposition binds depends on who is holding and trading:
  the token mix of the recent prints (`outcome_index`, a field no round has used as a weight; round 10 rejected it as a
  *sign proxy*, which it is not here). `g = mid - VWAP` is positive when recent YES takers are in gain; `s_YES - s_NO`
  says whether the active population is on the YES or the NO token; `G = g x (s_YES - s_NO)` is positive when the
  active side is in gain. Who pays: the holder in gain who sells early to the maker who leans with G. Why the crowd
  misses it: the cost basis of the crowd is nowhere on the screen; the sample's rows carry it.
- Data join and decision clock (`A`, L 5). Unit: sampled market x pass with >= 10 taker rows in `[t_k - 24 h, t_k)`
  under E016/E021's coverage rule (decided at the origin; a page that does not reach 24 h back uses its covered window
  and is flagged). State from rows only: `VWAP` = size-weighted YES-terms price; `s_YES`, `s_NO` = notional shares on
  the two tokens; `g = mid_k - VWAP` (cents); `G = g x (s_YES - s_NO)`. Decision time: the sample's receipt in pass k.
  Controls: own 2 h / 6 h / 24 h mid change, chg 1d, logit mid, |mid - 0.5|, spread, `log1p n_rows`, `g` itself and
  `s_YES - s_NO` itself (so the coefficient on G is the interaction), and the E007-convention net signed share `x6` as
  a control only (its 93.3% agreement disclosed), so a residual G effect is not flow sign.
- Target and horizon. `y6 = mid_{k+3} - mid_k` (6 h, skip-slot label binding); secondary 24 h; the engine's `res_7d`.
  Hypothesis (one-sided): within market, the slope of `y6` on `zG` > 0 with the controls fixed; the material test is
  the top-minus-bottom decile of `zG`.
- Paper rule and economic check. Maker: lean toward the side in gain (post bids under a positive G, asks over a
  negative one). Taker: buy the gaining side when G >= 3c in >= $100k markets, 2.9c round trip; HTR passive entry where
  `res_7d` applies; all reported against cost-model-v1.
- Units and MDE (3 weeks). About 10,700 covered market-samples a day (C2); with >= 10 rows in 24 h plausibly 7,000-
  9,000 (unprobed): 150,000-190,000 units in 21 days, about 40% non-sports. Top and bottom deciles non-sports, 6,000-
  7,600 each: SE = 5c x sqrt(2/6,000) x sqrt(3) = 0.158c, **MDE 0.5c** (at the floor); all categories (15,000-19,000
  per decile): 0.1c x 3.2 = **0.32c**. The per-SD slope MDE is about a third of these. Census gate: >= 600 qualifying
  units a pass.
- Confounders and the control. **Momentum is the main confound:** `g` is mechanically correlated with the recent move
  (the VWAP lags the mid). The primary coefficient is on G with `g`, the token mix and the fixed-horizon changes held
  fixed, so the identifying variation is the token weighting and the volume weighting of the path; census gate
  |corr(zG, z(own 24 h change))| <= 0.5 (|corr| <= 0.7 for `g` alone, reported). The token mix as a sign proxy (65%
  accurate, round 10): `x6` is a control. Truncated pages (busy markets): covered window, flag, sensitivity. Bounce:
  skip-slot. Crypto dominance: ex-crypto primary. Placebo: Freedman-Lane; far-future control (G computed on the rows of
  an interval ending after the target).
- Cheapest census (counts only; two worn days of samples). Distributions of `g`, `s_YES - s_NO`, G; corr(zG, z(own
  24 h change)); within-market IQR of G. Kill if the corr gate fails, if the within-market IQR of G is < 1c for half the
  markets with >= 6 samples, or if `s_YES - s_NO` is degenerate (|.| > 0.9 in > 80% of units: then the weight is a
  constant and G collapses to g).
- Challenger feature: **yes.** `overhang_24h = G`, `vwap_gap_24h = g`, `token_mix_24h = s_YES - s_NO` (flow-family
  columns; sign-free). Embargo: the flow family's isolated scoring is embargoed to 2026-11-18 (E013/E014/E016/E018;
  WS1 §7 item 4); the new columns inherit it.
- Scores: N 4, EV 4, L 5. Parents: CH42 (disposition, wallet-level), CH144/CH171/E023 (opens vs closes: they need
  `side`; this does not), round 10 §4 (NO-token share rejected as a sign; used here as a weight), CB10/CB12 (YES-terms
  VWAP as a transaction aggregator, not a cost basis).

### B. The family (parents CH158, CH159/E019, CH24, rejected ladder lead-lag L1-L4 / XM1-XM6 / E005; literature: Hong and Stein 1999, Gutierrez and Prinsky 2007, Blitz, Huij and Martens 2011)

**CH184. Alone or with the crowd: a member's 2 h move splits into the part its event, series or category moved at the
same capture (a family re-centering: programs tracking one reference, a theme-wide mood) and the part it moved alone.
The idiosyncratic part is market-specific information and continues; the common part has been priced across the
family already and does not. CH158 read the whole venue once a pass and died of 21 degrees of freedom; the member's
residual against its own family varies within pass and within market.**
- Mechanism and why it is non-obvious. In a neg-risk event the sum constraint and shared programs move members
  together; in a series (daily or weekly crypto, weather cities) one reference moves all; in a category a mood moves
  many. A member's move beyond its family's move came from its own book: its own prints, its own order events. Equity
  finance finds idiosyncratic momentum stronger and more persistent than total momentum (Gutierrez and Prinsky 2007;
  Blitz, Huij and Martens 2011), under gradual information diffusion (Hong and Stein 1999). On Polymarket the common
  component is often a program re-centering a family off one input, which E015 reads as "quoted"; the decomposition
  is orthogonal to E015's anatomy and the anatomy is controlled. Who pays: the taker who treats a family re-centering
  as news about one member; the maker who widens on every member after a family move. Why the crowd misses it: the
  movers list ranks members by their own change, never against their siblings'.
- Data join and decision clock (`A`, L 5). Unit: non-sports mover at capture k (LT3 §1.4 eligibility, |x| >= 1c) in a
  family with >= 3 other members two-sided and eligible at k-1 and k. Family hierarchy declared ex ante: the `event_id`
  (or `neg_risk_market_id`) if it has >= 3 other members, else the first `series_slugs` entry, else the `fee_category`.
  Leave-one-out family mean move `xbar_{-i}` (equal-weighted; a liquidity-weighted version secondary); decomposition
  `x = xbar_{-i} + e`; common share `w = xbar_{-i} / x` clipped to [-1, 2]. Classes: **idiosyncratic** `|xbar_{-i}| <
  0.25 |x|`, **common** `w >= 0.75`. Decision time: capture k's receipt. Controls: E015's anatomy label (quoted
  parallel, one-sided, spread-change, traded), |x|, spread, logit mid, |mid - 0.5|, lagged volume, family size,
  `log liquidity`.
- Target and horizon. `c = sign(x) x (mid_{k+1} - mid_k)` at 2 h; secondary `c6` skip-slot and the member-relative
  continuation `c_rel = sign(e) x ((mid_{k+1} - mid_k) - xbar_{k+1,-i})`. Hypothesis (one-sided): within market,
  E[c | idiosyncratic] - E[c | common] > 0, anatomy held fixed.
- Paper rule and economic check. Maker: after a common move, quote normally (it says nothing about this market); after
  an idiosyncratic move >= 3c, step aside on the move's side for one pass. Taker: follow idiosyncratic >= 3c moves in
  >= $100k markets, 2.9c round trip; reported.
- Units and MDE (3 weeks). Non-sports movers about 2,750 an interval; the share in a >= 4-member family is unprobed
  but neg-risk events and series cover a large part of the universe; ex-crypto plausibly 800-1,500 an interval:
  200,000-380,000 units in 21 days; classes 30% each: 60,000 against 60,000 at the low end: SE = 4c x sqrt(2/60,000) x
  sqrt(2.5) = 0.037c, **MDE 0.12c**. Powered at a tenth of that.
- Confounders and the control. E015's anatomy (controlled; |corr(1[common], 1[parallel quoted])| <= 0.5 as a census
  gate, because common moves are often program re-centerings); the laggard story (a member that moved alone may be the
  first mover whose siblings catch up: that is the siblings' continuation, not this unit's; the member-relative
  secondary separates them, and the rejected ladder lead-lag nulls say the sibling catch-up is small); family
  definition (fixed ex ante; a sensitivity with the category removed from the hierarchy); crypto dominance (ex-crypto
  primary); bounce (skip-slot). Placebo: a **fake family** (random eligible markets of the same category and liquidity
  tercile, seeded) must show no contrast; Freedman-Lane within market x UTC day.
- Cheapest census (counts only; two worn days of captures). Share of non-sports movers with a >= 4-member family by
  hierarchy level; class shares; corr with the anatomy label; crypto share. Kill if idiosyncratic ex-crypto units <
  300 a day, if the corr gate fails, or if > 90% of common units are crypto series.
- Challenger feature: **yes.** A **relative momentum** extension of the momentum family: `rel_mom_2h = x - xbar_event`,
  `rel_mom_24h`, `common_share_2h = w`, `family_size`. No sealed test uses it; no embargo.
- Scores: N 3, EV 3, L 5. Parents: CH158 (venue tilt, dropped for 21 df), CH159/E019 (breadth, dropped at census), CH24
  (category attention days), the rejected ladder lead-lag (L1-L4, XM1-XM6, E005 not supported).

### C. The rule (parents CH71/CB6-R, CH116, E003, CH16/CH45; literature: Copeland and Galai 1983, Glosten and Milgrom 1985, Cont, Kukanov and Stoikov 2014)

**CH183. The farmer's choice: inside [0.10, 0.90] the liquidity programme pays one-sided quotes, outside it only two-
sided quotes score (MAKER_REWARDS §2; CB6-R's convention). So inside the band a reward farmer chooses which side to post
and posts the side it expects not to be hit; the near-touch depth asymmetry there is a forecast. Outside the band the
rule forces both sides and the asymmetry is residual. The slope of the next move on the imbalance should jump at the
0.90 (and 0.10) cutoff in rewarded markets and not in unrewarded ones.**
- Mechanism and why it is non-obvious. A resting quote is a free option written to informed takers (Copeland and
  Galai 1983); a farmer's reward is lost when it is filled and the price moves against it. With one-sided scoring
  allowed, the rational farmer writes only the option it thinks will not be exercised, so the farmers' side choice
  aggregates their directional view (a Glosten-Milgrom maker's skew made visible). Where the rule forces two sides the
  asymmetry is inventory or noise. CH116 treats in-band depth as subsidy noise to be stripped; this says the one-
  sidedness of in-band depth is the signal, and the rule's cutoff identifies it with a venue constant, the way CB6-R
  identifies the spread discontinuity at the folded mid 0.90 (CB6-R's statistic is the spread, R1; its R2 is a touch
  maker's P&L in [0.90, 0.96); neither reads the imbalance's predictive content). E003 read the imbalance
  unconditionally at 2-4 minutes and was inconclusive (M8); the rule gives it a population where it should work and one
  where it should not. Who pays: the taker who trades against the farmers' side inside the band.
- Data join and decision clock (`A`, L 4). Unit: rewarded (`clob_rewards` daily rate > 0 in the sidecar at k) binary
  market x pass with folded mid `m = max(mid, 1 - mid)` in [0.84, 0.96) at sweep 1 of pass k (tick change at 0.96
  excluded; CB6-R's donut of 0.5c around 0.90), two-sided and tight. State: `imb = (D_bid - D_ask) / (D_bid + D_ask)` at
  1c depth from the sweep, oriented toward outcome 0 (secondary: at the levels whose size equals `rewards_min_size`,
  the farmers' own quotes); `inside = 1[m <= 0.90]`. Unrewarded markets in the same band are the built-in placebo
  population. Decision time: sweep 1's receipt. Estimator: within-market demeaned local-linear regression of the
  target on `imb`, `imb x inside`, `m - 0.90`, `(m - 0.90) x inside`, with bandwidth 6c and the donut, separately for
  rewarded and unrewarded; the primary statistic is the rewarded `imb x inside` coefficient minus the unrewarded one
  (diff-in-slopes).
- Target and horizon. Sweep-to-sweep 2 h continuation `c_sw` from sweep 1 of pass k to sweep 1 of pass k+1 (E022's
  convention: the target starts at the decision time's own stream), oriented by `imb`'s sign so the statistic is a
  slope; secondary 6 h. Hypothesis (one-sided): the inside-minus-outside slope difference is larger in rewarded than in
  unrewarded markets.
- Paper rule and economic check. Maker: inside the band in rewarded markets, join the deep side (lean with the
  farmers); outside, ignore the asymmetry. Taker: trade with the deep side when |imb| >= 0.5 inside the band in
  >= $100k markets; 2.9c round trip; reported. HTR: favourites at 0.85-0.90 whose farmers post bids only, held to
  resolution (cost about 0 at >= $100k); reported via `res_7d`.
- Units and MDE (3 weeks). 13,683 rewarded markets (snapshot); the share with folded mid in [0.84, 0.96) is unprobed,
  plausibly 1,500-3,000 a capture: 380,000-760,000 row-units in 21 days, but the state is slow (rule 2), so effective
  units are state changes, say 30,000 a side. SE for the slope difference per SD of `imb` = 3.5c / sqrt(30,000 / 4) x
  sqrt(2) = 0.057c, **MDE 0.18c per SD**; the material contrast (|imb| >= 0.5 against <= 0.1, about 2 SD) 0.36c.
  Borderline-adequate; the census recomputes with its own counts.
- Confounders and the control. The level (local-linear in `m`, folded, donut, tick change excluded); CB6-R's own spread
  discontinuity at the cutoff (spread controlled; `imb` in shares, not dollars); hollowness (E022's `zh` and `log1p D`
  as controls, so `imb` is not a thin-book proxy); sports (reported); bounce (sweep-to-sweep target); the farmers'
  quotes not being the marginal depth (census: share of in-band books whose 1c depth is at `rewards_min_size`).
  Placebo: the unrewarded diff-in-slopes (built in), fake cutoffs at 0.60-0.83 (CB6-R's convention), Freedman-Lane.
- Cheapest census (counts only; two worn days of sweeps and sidecars). Rewarded and unrewarded units per side of the
  cutoff; within-market IQR of `imb`; share of in-band books with min-size depth at the touch. Kill if < 600 rewarded
  units a day on either side, if unrewarded units < 300 a day on either side, if the within-market IQR of `imb` is <
  0.1 for half the markets, or if < 30% of in-band rewarded books show min-size quotes at 1c (the farmers are not the
  marginal quoters and the mechanism has no carrier).
- Challenger feature: **yes.** Book-family interaction: `imb_1c x rewarded x in_band`, `rewarded`, `in_band`,
  `minsize_depth_share`. Embargo: E022 uses sweep depth as a control; isolated scoring embargoed to 2026-11-17.
- Scores: N 4, EV 3, L 4. Parents: CH71/CB6-R (spread at the 0.90 cutoff; the spread, not the imbalance), CH116
  (band-stripped imbalance, the opposite premise), E003 (imbalance inconclusive, microprice supported exploratory),
  CH16/CH45 (reward geometry).

### D. Footprints and the record (parents CH69, CH162/E018, CH111/CH148, E003, E022/CH174, CH39, CH92, CH08/CH177, CH07, CH62, CH01/CH04, CH22/CH142/CH154, CH56, CH67; literature: Almgren and Chriss 2001, Glosten and Milgrom 1985)

**CH185. Footprints without wallets: an execution algorithm leaves a signature in the public prints that needs no
wallet, identical sizes at near-regular gaps in one market (clips); the clip share of a traded move's volume marks a
patient parent order that is not finished, and the move continues. A scalper leaves size-matched opposite prints
minutes apart (round trips), noise that reverts.**
- Mechanism and why it is non-obvious. TWAP and POV algorithms slice a parent order into equal child orders at regular
  intervals (Almgren and Chriss 2001); the parent is larger than what has printed, so the remaining schedule is
  predictable pressure. CH69 proposed the footprint by wallet; CH162/E018 read trains by *timing* (same-signed
  neighbours within 300 s) and died at the census (H interior 30.8%); clips read *size identity*, need no sign, and
  are a subset of trains that the timing measure cannot isolate. Round 8 probed cross-event equal-notional baskets
  within 1 s (7 a day, dead) and multi-market transactions (0); same-market clips over minutes were not probed. Who
  pays: the maker who re-posts at the touch while a schedule is running; the taker who fades it.
- Data join and decision clock (`A`, L 4). Unit: sampled traded mover at k with >= 4 rows in `[t_{k-1}, t_k)` (CH180's
  population). A **clip train** = >= 3 rows on the same token with identical `size`, consecutive gaps within +/-50% of
  each other and all within 30 minutes; `clip_share` = notional share of the interval's rows in clip trains. Sizes at
  or below 2 x `min_order_size` excluded (min-size bots); size roundness (CH111/CH148) controlled. Secondary, arm 2:
  `rt_share` = notional share in size-matched opposite-`side` pairs within 30 minutes (uses the sample's Data API
  `side` under the E007 convention as a composition measure, 93.3% disclosed; not an `x6` moderator, so the agreement
  arm does not bind). A monitor arm (universe-wide prints >= $1k, unsigned, same clip rule) is a reported secondary
  population with its 9-minute lag. Decision time: the sample's receipt.
- Target and horizon. `c` at 2 h and `c6` skip-slot. Hypothesis (one-sided): within market, E[c | clip_share >= 0.5] -
  E[c | clip_share = 0] > 0; arm 2 (secondary): E[c | rt_share >= 0.5] < E[c | rt_share = 0].
- Paper rule and economic check. Maker: while a clip train is running on one side, step aside on that side for one
  pass. Taker: join the train's direction (the capture's sign) in >= $100k markets; 2.9c; reported.
- Units and MDE (3 weeks). Qualifying units as CH180 (plausibly 300-600 a pass); clip_share > 0 in 10-20% of them
  (unprobed): 1,200-2,400 clip units a day all categories, 25,000-50,000 in 21 days against about 150,000 without:
  SE = 4c x sqrt(1/25,000 + 1/150,000) x sqrt(2) = 0.039c, **MDE 0.12c**; at a 2% clip share (5,000 units): 0.26c.
- Confounders and the control. Round-dollar coincidences (two $100 orders: the >= 3 rows and regular-gap rules, and
  roundness as a control); min-size bots (excluded); E018's train measure H (adjacent construct; |corr(clip_share, H)|
  <= 0.5 as a census gate; E018 is dropped, so no double count); the last trade's age and the path shape (CH180's `g`
  and E021's 1[fresh] as controls; |corr| gates); bounce; crypto. Placebo: Freedman-Lane; far-future control.
- Cheapest census (counts only; two worn days of samples). Distribution of `clip_share`; share of clips at min size;
  corr with H and `g`. Kill if clip_share > 0 in < 3% of qualifying units, if > 80% of clip notional is at or below 2 x
  min size, or if a corr gate fails.
- Challenger feature: **yes.** `clip_share_6h` (sign-free), `rt_share_6h` (flow family; the flow embargo to
  2026-11-18 applies).
- Scores: N 3, EV 3, L 4. Parents: CH69 (TWAP footprints, wallet-based), CH162/E018 (trains by timing), CH111/CH148
  (roundness), round 8 §4 (cross-event baskets, dead; a different object).

**CH190. The makers' vote: the book that re-forms after a move is the makers' verdict. Depth stacked on the move's
side (bids under a rise) says they accept the new price; depth stacked against it says they want to fade it; the
spread's change through the move is their confidence. Makers see every order; their post-move skew, read once the
touch has refilled, predicts whether the move holds. E003 read the skew in quiet books and found little; after a move
it is a reaction to information, not inventory or reward noise.**
- Mechanism and why it is non-obvious. A Glosten-Milgrom maker who has just seen the flow that moved the price sets
  her next quotes where she expects the price to go; the depth she posts on each side is a costly signal (she will be
  filled there). In quiet books the skew is inventory and reward geometry (CH116's premise), so the unconditional
  E003 result (M8 inconclusive, microprice +0.03 R2 exploratory at minutes) is not a test of the vote. Round 10's E020
  reads the *unmoved side's reaction* to one-sided quote-only moves; E022 reads displayed against executable depth;
  CH39 reads the retreat after a print. The vote is the post-move skew of *both* sides, conditional on the move, on
  every mover. Who pays: the taker who fades a move the makers have ratified; the maker who ratifies alone.
- Data join and decision clock (`A`, L 4). Unit: non-sports mover at k (traded or quoted, LT3 §1.4 eligibility) with
  sweep 1 of pass k (about 8 minutes after the capture) two-sided and tight. State: `v = sign(x) x imb_5c` (aligned
  skew > 0; `imb_5c` from the sweep's 5c depths, oriented toward outcome 0), `dspread = spread_sweep - spread_{k-1}`.
  Decision time: sweep 1's receipt. Controls: the pre-move imbalance at k-1's sweep (so mechanical depletion of the
  hit side is held fixed), E015's anatomy label, |x|, `log1p D` (total 5c depth), E022's `zh` (hollowness, same
  reader), spread, logit mid, |mid - 0.5|, lagged volume.
- Target and horizon. Sweep-to-sweep 2 h continuation `c_sw` (E022's convention); secondary 6 h. Hypothesis (one-
  sided): within market, the slope of `c_sw` on `zv` > 0; secondary: the slope is larger when `dspread <= 0`.
- Paper rule and economic check. Maker: lean with the vote (post on the aligned side) when `|v|` is in the top
  tercile and the spread did not widen. Taker: follow moves the makers ratified in >= $100k markets; 2.9c; reported.
- Units and MDE (3 weeks). About 18,500 non-sports movers a day, all sweep-covered (P1/P1b): 390,000 units in 21 days;
  SE per SD = 3.5c / sqrt(390,000 / 2.5) = 0.009c; the top-minus-bottom decile contrast (about 2.5 SD) **MDE about
  0.07c**. Powered many times over; the census's job is the confounder gates, not the count.
- Confounders and the control. Mechanical depletion (the move consumed one side: controlled by the k-1 imbalance and
  the 8-minute refill delay; a census item reports how often the hit side's 1c depth is still below its k-1 level at
  sweep 1); hollowness (E022's state, controlled; |corr(zv, zh)| <= 0.5 gate); E015's anatomy (controlled); bounce
  (sweep-to-sweep target from the decision time); crypto (ex-crypto primary). Placebo: Freedman-Lane; a *pre-move*
  vote (the k-1 skew signed by the k move, which cannot be a reaction) must show the unconditional E003-size effect
  at most.
- Cheapest census (counts only; two worn days of sweeps). Distribution of `v`; refill share; corr(zv, zh); corr(zv,
  anatomy). Kill if a corr gate fails or if the hit side's depth is still depleted at sweep 1 in > 50% of traded
  movers (then the state is the move's own footprint, not a vote).
- Challenger feature: **yes.** `vote_5c = sign(own 2 h change) x imb_5c`, `dspread_2h` (book x momentum interaction).
  Embargo: shares E022's reader and controls; isolated scoring embargoed to 2026-11-17.
- Scores: N 3, EV 3, L 4. Parents: E003 (unconditional imbalance), E022/CH174 (same population and reader), E020/CH169
  (the unmoved side after one-sided quote moves), CH39 (post-print retreat), CH92 (the maker's own skew rule), CH147.

**CH187. Deadline moves, revived with a census: a change of `end_date` between captures is a numeric, text-free rule
event the venue posts silently. A later deadline on a "by date" question mechanically raises P(YES) (more time for the
event); an earlier deadline on an open market is the venue's tell that the event has already happened. The template is
read from the `end_date` time of day (the by-date template ends at 23:59 ET), no text needed.**
- Disclosure. Round 7 §4 parked "deadline extensions (`endDate` changes between captures impose a mechanical loss on
  NO)" because "no count is possible without a capture walk, and the known cases are sports postponements"; round 8
  repeated the rejection. Both reasons are now answerable from what the host writes: twelve captures a day make the
  capture walk a counts-only census on worn files, and the sidecar's `fee_type` plus CB17's sports list separates
  postponements. The new elements are the numeric template classifier, the dose `r`, the earlier-move arm and the
  census-first design.
- Mechanism and why it is non-obvious. The holder of NO on a "by 31 December" question loses value the moment the
  venue moves the date to 31 January; no notification is sent, the UI shows the new date, and the programs that quote
  the market may or may not re-centre. The under-reaction, if any, is the 24 h drift after the first interval. An
  earlier move on an open interior market is different: the venue shortens the date when the event has occurred or
  the resolution source has published, a numeric cousin of CH01/CH04's decided class. Who pays: the NO holder who does
  not read the date; the YES seller at the old price.
- Data join and decision clock (`A`, L 3). Unit: non-sports market x capture k with `end_date_k != end_date_{k-1}`,
  mid in [0.05, 0.95], two-sided. Classes: **later** (delta > 0) and **earlier**; dose `r = delta / (end_old - t_k)`;
  template `bydate = 1[end_date time of day in the 23:59 ET / 00:00 ET set]` (the census reports the time-of-day
  histogram first). Recurring series whose delta equals the series period are excluded (roll-overs, not edits).
  Decision time: capture k's receipt.
- Target and horizon. 24 h YES mid change `mid_{k+12} - mid_k`, signed by the mechanical prediction (+ for later moves
  on by-date templates); the first 2 h move is a control, and a 22 h skip-slot secondary starts at k+1. Maker-
  protection secondary: 2 h |move| and spread change after any `end_date` move. Hypothesis (one-sided): within market,
  E[mid_{k+12} - mid_k | later, bydate] > 0, increasing in `r`; placebo: later moves on decided markets (mid > 0.97 or
  < 0.03) and on scheduled templates show no signed drift.
- Paper rule and economic check. Taker: buy YES at the ask after a later move with `r >= 0.5` on by-date markets, hold
  24 h or to resolution (politics 3.8c, >= $100k 2.9c round trip; one leg if held); maker: widen for one pass after any
  `end_date` move (edits co-occur with news); all reported.
- Units and MDE (3 weeks). Unprobed. At 150 non-sports later moves a day with interior mids: 3,150 units, SE = 6c /
  sqrt(3,150 / 2) = 0.151c, **MDE 0.48c**; at 600 a day, 0.24c. Census gate: >= 150 a day.
- Confounders and the control. Co-occurring text edits (CH08/CH177, CB18's territory; `updated_at` flags any edit and
  is a control; the gamma_rules stream, if installed, dates the text edit); programs re-centring on the new date in
  the same interval (the 2 h move is a control); sports postponements (excluded); series roll-overs (excluded);
  earlier moves that coincide with the market leaving the listing (the earlier arm is descriptive unless the census
  shows >= 100 a day on still-open markets). Placebo: as above; Freedman-Lane.
- Cheapest census (counts only; two worn weeks of captures). `end_date` changes a day by class, template, category,
  interior share; the time-of-day histogram. Kill if later interior non-sports moves < 150 a day, or if > 70% of them
  are series roll-overs or crypto.
- Challenger feature: **yes.** `end_date_delta_24h` (hours, signed), `end_date_r`, `bydate_template` (market_state).
- Scores: N 3, EV 3, L 3. Parents: round 7 §4 (parked), CH08/CH177 (edits by `updated_at`; here the field itself
  changes), CH07 (postponement clause), CH01/CH04 (decided class; the earlier arm).

**CH188. Sibling birth: the venue's listing desk reacts to news; a new market created inside an existing event (a new
candidate, scenario or strike) is a dated, text-free salience signal for the existing members, whose quotes are stale
relative to the news that caused the listing. Attention and repricing follow within 24 h; in a neg-risk event the
newcomer's seed price must come from somewhere, and it comes from the tail.**
- Mechanism and why it is non-obvious. CH22, CH142 and CH154 read the new market itself (genesis, series launch, first-
  day prints); CH67 reads a sibling leaving (resolution unwind); nobody reads a sibling *arriving* as information about
  the incumbents. The listing is a human decision made on news, timestamped by `created_at`, visible only as a new row
  with the same `event_id`, `neg_risk_market_id` or `parent_event_ids`. The mechanical arm: in a neg-risk event the sum
  constraint means the newcomer's probability is taken from the members most similar to it, which without text can
  only be approximated as the tail (members under 0.05) rather than the leader. Who pays: the tail-member YES holder
  who does not notice the new entrant.
- Data join and decision clock (`A`, L 3). Unit: existing eligible member x capture k when a sibling first appears in
  capture k (`created_at` within `[t_{k-1}, t_k)`; a market present at k and absent at k-1). Decision time: capture k's
  receipt. Classes: the event's members at k against the same members' other captures (within market).
- Target and horizon. Attention arm (primary): the 24 h change in `log volume24hr` and the 24 h |mid move| of the
  incumbents (maker-protection object). Signed arm (secondary, neg-risk only): tail members' 24 h YES change < 0.
  Hypothesis (one-sided): within market, incumbents' 24 h |move| and volume change after a birth exceed the market's
  own baseline.
- Paper rule and economic check. Maker: widen on incumbents for one pass after a sibling birth. Taker (secondary): sell
  tail members' YES at the bid after a birth in neg-risk events; costs at the recorded touch; reported.
- Units and MDE (3 weeks). New markets a day are in the thousands universe-wide, but crypto strike additions are
  routine and mechanical (ex-crypto primary); ex-crypto births in existing events plausibly 50-200 a day, each with
  several incumbents: 1,000-4,000 incumbent units on the signed arm (SD 6c: MDE 0.86c at the low end, 0.42c at the
  high end, census-gated), and the attention arm is powered at any of these counts.
- Confounders and the control. Momentum (the listing follows a move: own 24 h change controlled; the birth's own
  interval excluded from the target by starting at k+1); series births (excluded by `series_slugs`); crypto (ex-crypto);
  the leader's seed price (CH56) as the newcomer's own object, not read here. Placebo: Freedman-Lane; a fake birth
  (a random capture of the same event) must show nothing.
- Cheapest census (counts only; two worn weeks of captures). Births a day by category and structure; incumbents per
  birth; tail share. Kill if ex-crypto births in existing events < 30 a day.
- Challenger feature: **yes.** `siblings_born_24h`, `event_members_delta_7d` (market_state).
- Scores: N 3, EV 2, L 3. Parents: CH22/CH142/CH154 (the newcomer), CH67 (the leaver), CH56 (seed anchor), CH10/CH11
  (placeholder and "Other" decay).

### E. Engine-first ideas (resolution-level; a 21-day mid target would double-count a sealed test or be underpowered)

**CH186. Calibration by provenance: two markets at 0.70 are not the same 0.70. One reached it by quoted re-centerings
(programs tracking a reference or peers), one by traded moves (people paying the spread). The quoted share of a
market's last seven days of moves is a provenance label; program-set prices inherit their reference's calibration,
trade-set prices carry the FLB and attention biases. Provenance predicts the resolution beyond the mid.**
- Why engine-first. E015 tests the *continuation* of quoted against traded moves to 2026-11-14; a 21-day mid-based
  test of the same labels would be a second counted test of E015's hypothesis on overlapping origins (the CH178
  objection). The *level* question (is the price calibrated differently by provenance?) is a different hypothesis with
  a resolution target, and the engine's `res_7d` leaderboard is built for it: the family is added to the champion,
  scored prospectively from the first deploy, judged by `se-promotion-v1` after >= 14 days, with its isolated scoring
  embargoed to 2026-11-16 (E015's analysis date plus a day) so nothing shadows E015.
- State (`A`, L 3 for the engine; 2 as an LT5 primary). `q7 = sum |quote-only 2 h moves| / sum |all 2 h moves|` over
  the last 84 captures, with E015's labels (`volume24hr` unchanged = quote-only); `traded_share_24h`; `n_moves_7d`.
  Decision time: capture receipt. Target: `res_7d` (engine label, Gamma by id, receipt-timed) and, for a later
  registered test, CH175's last-mid proxy for markets ending inside a 28-day window.
- Money route: HTR passive entry in >= $100k markets in the miscalibrated provenance tercile (cost about 0; fill rate
  the open question, E025 part B's object).
- MDE: a resolution contrast at SD 0.45 needs about 10,000 resolving markets a tercile for a 2c calibration gap; only
  crypto and sports deliver that in weeks (ex-crypto rule kills the 21-day version). The engine's rolling 28-day
  leaderboard accumulates it without a window; that is why it is engine-first.
- Census: distribution of `q7`; kill if degenerate (> 80% of eligible markets at 0 or 1).
- Challenger feature: **yes.** `q7`, `traded_share_24h`, `n_moves_7d` (a provenance family from `quotes/`).
- Scores: N 3, EV 3, L 3 (engine) / 2 (LT5). Parents: E015/CH156 (same labels, different target), CH175 (proxy), prior-
  art gap 3 (long-horizon underconfidence).

**CH189. Overdue by the clock: a market whose `end_date` has passed while it stays open with an interior mid is
overdue. On a by-date template the event did not happen by the date and the answer is NO; the interior mid is a YES
premium that decays as the resolution lands. Text-free CH62, with the numeric template classifier and the engine's
resolution label.**
- Why engine-first. Overdue markets are few at any time and persist for days (effective units are markets, not
  captures); a 21-day mid-drift test is underpowered (about 600 markets, MDE about 1c at SD 6c and a large DE), but the
  claimed miscalibration is large (an interior mid on a market that resolves NO), so a resolution-level test over the
  engine's rolling window, or a registered 28-day calibration test with CH175's proxy, is the right shape.
- State (`A`, L 3). `hours_overdue = t_k - end_date` (> 0), `bydate_template` (CH187's classifier), interior mid,
  two-sided, no UMA proposal in the sidecar (the engine's base eligibility already excludes proposed markets, so the
  overdue population is the pre-proposal limbo). Target: `res_7d`; secondary 24 h mid drift (< 0 for YES).
- Money route: the NO carry held to resolution (one leg; cost 1.5-2.5c above 0.80, less at the interior prices where
  the premium sits); maker: post YES asks in overdue by-date markets; reported.
- Census: overdue interior by-date markets a day, their persistence, category mix. Kill if < 20 new a day ex-sports.
- Challenger feature: **yes.** `hours_overdue`, `bydate_template` (market_state).
- Scores: N 2, EV 3, L 3. Parents: CH62 (text-parsed deadline), CH01/CH04 (decided class), CH105 (deadline hour).

---

## 3. Ranked top 5 for LT5, then the rest

Rank = originality x plausibility x time to a registered live test x population per day x money route, with the
rules of section 0.1 as hard constraints. The five LT5 candidates each have a continuation target on a population in
the thousands a day, a within-market contrast or slope with the Freedman-Lane gate, a counts-only census that can kill
it before any outcome is read, a planning MDE under the 0.5c floor at plausible counts, and a reader that extends an
existing LT reader (E021's for the trade-sample members, E015's for the capture members, E022's for the sweep members).

| Rank | ID | One line | L | Daily population (source) | Primary contrast | Planning MDE |
|---|---|---|---|---|---|---|
| 1 | CH180 | Jump or grind: the path shape of a traded move from the sample's print levels, sign-free | 5 | 300-600 qualifying a pass (P2 bound; unprobed) | within market, jump minus grind on `c` | 0.24c (0.42c at a third of the count) |
| 2 | CH184 | Alone or with the crowd: the member's move minus its family's, anatomy held fixed | 5 | 800-1,500 ex-crypto an interval (P1/P1b; family share unprobed) | within market, idiosyncratic minus common on `c` | 0.12c |
| 3 | CH182 | Capital-gains overhang, token-weighted, from the 500-row page | 5 | 7,000-9,000 market-samples a day (C2; unprobed) | within market, slope of `y6` on `zG` with `g`, token mix and momentum fixed | 0.32-0.5c (deciles), per-SD a third of that |
| 4 | CH181 | The high-water mark: within 1c of a >= 3-day own extreme, folded | 4 | near units unprobed (eligible 40,000 a capture) | within market, near minus far on the folded 24 h change | 0.13c (0.42c at a tenth of the count) |
| 5 | CH183 | The farmer's choice: the reward rule's one-sided cutoff as an identification of the imbalance's content | 4 | rewarded in-band units unprobed (13,683 rewarded markets) | diff-in-slopes of `c_sw` on `imb` at 0.90, rewarded minus unrewarded | 0.18c per SD, 0.36c on the material contrast |
| 6 | CH190 | The makers' vote: post-move skew once the touch refilled | 4 | 18,500 non-sports movers a day (P1/P1b) | within market, slope of `c_sw` on `zv` | 0.07c (decile) |
| 7 | CH185 | Footprints without wallets: clip trains by size identity | 4 | 1,200-2,400 clip units a day (unprobed) | within market, clips minus none on `c` | 0.12-0.26c |
| 8 | CH187 | Deadline moves (revived; census-first) | 3 | unprobed (kill line 150 a day) | within market, later by-date moves on the 24 h YES change | 0.24-0.48c |
| 9 | CH188 | Sibling birth as a salience clock for incumbents | 3 | 50-200 ex-crypto births a day (unprobed) | within market, 24 h volume and \|move\| after a birth | attention arm powered; signed arm 0.42-0.86c |
| 10 | CH186 | Calibration by provenance (engine-first) | 3 | 40,000 eligible a capture | `res_7d` log-loss gain, promotion rule | engine window |
| 11 | CH189 | Overdue by the clock (engine-first NO carry) | 3 | unprobed, few and persistent | `res_7d`; 24 h drift secondary | engine window |

CH190 is sixth, not fifth, because it is a moderator of E003's object and shares E022's reader and controls; it is the
strongest *feature* in the file and the weakest *new mechanism*. If the LT5 designer wants k = 5 with the largest
populations, CH190 replaces CH183; the choice is originality against simplicity and I have ranked for originality.

**Pre-registration sketches for the top 5 (LT5 candidates; each a separate primary in one Holm family; written in
LT3/LT4's shape so the designer can lift them).**

- **CH180 (jump or grind).** Unit: sampled market x pass, traded mover at k (LT3 §1.4), >= 3 rows in `[t_{k-1}, t_k)`,
  coverage decided at the origin, |x| >= 3 ticks, no tick change. State: `g = (levels - 1)/steps`; jump `g <= 0.25`,
  grind `g >= 0.75`. Decision time: the sample's receipt. Primary: expanding-past market-demeaned OLS of `c` on
  1[jump] over jump and grind units with `log1p n_rows`, |x|, 1[fresh], spread, logit mid, |mid - 0.5|, lagged
  volume and tick stratum as controls; one-sided > 0. Target: `c` at capture k+1; `c6` skip-slot secondary; the
  unmoved side's change a reported label. Clustering: LT4 L10. Planning MDE 0.24c (SD 4c, 10,600 against 12,000 non-
  sports, DE 2) against 0.5c. Kill-census: qualifying units < 120 a pass; jumps or grinds < 20% each; jumps from
  0.01-tick books > 80%; |corr(1[jump], 1[fresh])| > 0.5. Cost hurdle: maker none; the taker follow of >= 3c jumps
  against cost-model-v1 by tier. Extends: E021's reader (three columns; every pass; three-day retention). Embargo for
  the engine columns to 2026-11-17.
- **CH184 (alone or with the crowd).** Unit: non-sports mover at k with >= 3 other eligible two-sided members at k-1
  and k in the declared family hierarchy (event, else series, else category). State: `xbar_{-i}`, `w`; idiosyncratic
  `|xbar_{-i}| < 0.25|x|`, common `w >= 0.75`. Decision time: capture k's receipt. Primary: expanding-past market-
  demeaned OLS of `c` on 1[idiosyncratic] over the two classes with E015's anatomy label, |x|, spread, logit mid,
  |mid - 0.5|, lagged volume, family size and log liquidity as controls; one-sided > 0. Target: `c` at k+1; `c6`
  skip-slot and `c_rel` secondaries. Clustering: LT4 L10 with t on `G_series - 1` and an ex-crypto primary. Planning
  MDE 0.12c (SD 4c, 60,000 against 60,000, DE 2.5). Kill-census: idiosyncratic ex-crypto units < 300 a day;
  |corr(1[common], 1[parallel quoted])| > 0.5; > 90% of common units crypto. Placebo: the fake-family contrast
  (seeded) and Freedman-Lane. Cost hurdle: maker none; the taker follow of idiosyncratic >= 3c moves reported.
  Extends: E015's reader plus a family join on the capture.
- **CH182 (capital-gains overhang).** Unit: sampled market x pass with >= 10 rows in the 24 h window under the coverage
  rule. State: `g`, `s_YES - s_NO`, `G`. Decision time: the sample's receipt. Primary: expanding-past market-demeaned
  OLS of `y6` on `zG` with `g`, `s_YES - s_NO`, own 2 h / 6 h / 24 h changes, chg 1d, `x6` (control only), logit mid,
  |mid - 0.5|, spread and `log1p n_rows` as controls; one-sided > 0; the material test is the top-minus-bottom decile.
  Target: `y6 = mid_{k+3} - mid_k` with the skip-slot label; 24 h secondary. Clustering: LT4 L10. Planning MDE 0.32c
  all categories, 0.5c non-sports (deciles; SD 5c, DE 3). Kill-census: qualifying units < 600 a pass; |corr(zG, z(own
  24 h change))| > 0.5; within-market IQR of G < 1c for half the markets; token mix degenerate. Cost hurdle: maker
  none; the taker buy of the gaining side at G >= 3c in >= $100k markets reported. Extends: E016/E021's reader (four
  columns). Embargo for the engine columns to 2026-11-18 (flow family).
- **CH181 (the high-water mark).** Unit: eligible market x capture, mid in [0.05, 0.95], state changed since k-1,
  `age_hi >= 36` captures for the near class. State: `d_hi`, `d_lo`, folded sign `s`. Decision time: capture k's
  receipt. Primary: expanding-past market-demeaned OLS of `u = s x (mid_{k+12} - mid_k)` on 1[near] over near and far
  units with logit mid, |mid - 0.5|, chg 1d/1w, own 24 h change, `age_series`, 1[round-number mark], spread and lagged
  volume as controls; one-sided > 0. Target: 24 h; 6 h secondary; `res_7d` in the engine. Clustering: LT4 L10 with the
  ex-crypto rule and DE 4 in planning. Planning MDE 0.13c at 400 near units a capture, 0.42c at 40. Kill-census: near
  units < 400 a day non-sports; > 70% crypto; within-market SD of `d_hi` < 1c for half the markets with >= 50 captures.
  Placebo: the fake mark (series excluding the last 14 days) and Freedman-Lane. Cost hurdle: maker none; the taker
  buy within 1c below a >= 3-day high in >= $100k markets and the HTR passive entry reported. Extends: E015's reader
  plus a per-market running extreme (a small rebuildable state file, write-once per capture).
- **CH183 (the farmer's choice).** Unit: rewarded binary market x pass with folded mid in [0.84, 0.96) at sweep 1,
  two-sided and tight, no tick change; the unrewarded markets in the same band as the placebo population. State:
  `imb` (1c depth), `inside = 1[m <= 0.90]`, donut 0.5c. Decision time: sweep 1's receipt. Primary: within-market
  demeaned local-linear regression of `c_sw` on `imb`, `imb x inside`, `m - 0.90`, `(m - 0.90) x inside`, with spread,
  `log1p D`, `zh`, logit mid and lagged volume as controls, bandwidth 6c, rewarded and unrewarded separately; the
  statistic is the rewarded `imb x inside` coefficient minus the unrewarded one, one-sided > 0. Target: sweep-to-sweep
  2 h (E022's convention); 6 h secondary. Clustering: LT4 L10 with DE 4 in planning. Planning MDE 0.18c per SD, 0.36c
  on the material contrast. Kill-census: < 600 rewarded units a day on either side of the cutoff; < 300 unrewarded;
  within-market IQR of `imb` < 0.1 for half the markets; < 30% of in-band rewarded books with min-size depth at 1c.
  Placebo: fake cutoffs 0.60-0.83, the unrewarded diff-in-slopes, Freedman-Lane. Cost hurdle: maker none; the taker
  trade with the deep side at |imb| >= 0.5 inside the band reported. Extends: E022's reader (sweep 1 + sidecar join)
  with the folded-band selection and the RD estimator. Embargo for the engine columns to 2026-11-17.

**How the families would be registered.**
- **A. The path (CH180, CH181, CH182).** All three counted if their censuses pass; CH180 and CH182 on E021's reader,
  CH181 on E015's. The path family goes to the engine as a challenger at once (no sealed test uses it), the flow-
  derived columns under the flow embargo.
- **B. The family (CH184).** Counted; the relative-momentum columns go to the engine at once.
- **C. The rule (CH183).** Counted if the census shows the farmers are the marginal quoters in the band; else dropped
  uncounted and the imbalance interaction is a reported engine column only.
- **D. Footprints and the record (CH185, CH187, CH188, CH190).** CH190 counted only if CH183 drops (k <= 5); CH185
  counted in LT6 or as a sixth test if the designer accepts k = 6 at the Holm cost; CH187 and CH188 census-gated maps
  first, counted in a later family if their counts clear the kill lines.
- **E. Engine-first (CH186, CH189).** Challenger families now, with embargoes; registered calibration tests only with
  CH175's proxy over 28 days or more.

**What is honest to say about all of them.** Round 10's facts were about what the streams let a reader name; round
11's are about what the streams let a reader *remember*: a market's own high, its takers' cost basis, the levels a move
passed through, its family's move at the same minute, the rule that governs the quotes on one side of 0.90, the sizes
an algorithm repeats, the date the venue moved. Each of the top five is a within-market contrast or slope on a
population of thousands a day, built to the eight rules of section 0.1, with a sign that comes from the mid or from a
mechanical rule, never from a print's direction. Three of the five transplant a mechanism with a named equity-finance
pedigree (anchoring on the high, disposition on the cost basis, idiosyncratic momentum) to a venue where none has
been tested and where the resolution forces the anchor to give way; one (CH180) reads a decomposition no study of
these markets has made; one (CH183) uses a venue constant to turn an inconclusive object (the imbalance) into a
testable one. Nothing here is edge until it has gone through census, frozen rules, prospective registration and an
economic check at recorded prices; the engine's leaderboard, not this file, is where any of it would first show.

---

## 4. Ideas considered and rejected, and why

- **Talk before money (event `commentCount` deltas as a retail clock, comments-to-volume as the retail share).**
  Round 8 probed it: 22,111 events, 1,217 with any comment, 9 changed in 2 h, 0 gained five (fact 3). Dead at the
  capture cadence; the level is a trait in CH155's class table. Not revived.
- **Cross-event equal-notional baskets within seconds (wallet-free CH95) and multi-market transactions.** Round 8 fact
  7: 7 a day and 0 of 10,380. Dead. CH185 reads same-market clips over minutes, a different object.
- **Partition dependence in non-neg-risk multi-member events (members priced as if exclusive when several can win).**
  Textbook (Sonnemann, Camerer, Fox and Langer 2013 document it in prediction markets); CH112 owns the mention-basket
  case and CH117 the logical form (text). A cheap engine column (`n_members_non_negrisk`, `sum_of_member_mids`) is
  worth adding; not an original mechanism.
- **Fee-screened flow (the taker fee `rate x p(1 - p)` screens out marginal takers, so flow is more informative where
  the fee is highest).** A signed-flow moderator (the E016/E018/E023/E024 class: agreement arm, donor gate); round 10
  rejected the fee parabola as a limit to arbitrage and the fee is category-determined. Not proposed.
- **Volume surprise as a continuation moderator (the interval's volume against the market's own profile).** Textbook
  volume-momentum (Lee and Swaminathan 2000); E017's continuous cousin with the same mechanism. Not proposed.
- **Spread widening with no trade as a volatility forecast (both makers step back before news).** Spread-volatility
  clustering is textbook; CH33, CH35/CH36, CH147 and E020's cancellation class own the pieces. Not proposed.
- **Quote wake-ups (the first mid move after >= 12 h of unchanged quotes).** A moderator of E015's classes (dormancy x
  anatomy) during E015's window: the CH178 objection. CH132 owns the print version. Not proposed.
- **Program overrides human (the quote moves away from the last print).** The mirror of CH172, which CB18 owns. Not
  proposed.
- **E015's contrast on the sweep clock, any E015 moderator, any E020-E022 moderator.** Double counts of sealed or
  drafted tests on overlapping origins. Not proposed; CH190 shares E022's reader but tests a different state and is
  ranked below the top five for that reason.
- **Ladder lead-lag, focal-member rotation, sum-of-mids deviation.** Null or not supported (L1-L4, XM1-XM6, E005,
  SB2-J5). CH184 controls the anatomy and uses the member-relative target so it is not a lead-lag test.
- **Venue-wide clocks of any kind** (hour of day, UTC reward epoch, weekend, category-day mood, redemption days). One
  value per pass is one value per day (CH158's death). CH184 is the per-unit answer.
- **Own-hours profile (a market's move outside its usual trading hours).** Ambiguous sign (thin liquidity overshoot
  against foreign news), and CH18/CH58 own the hours objects. Not proposed.
- **Touch-clearing prints (a print at least as large as the touch's displayed size).** Needs the sweep's size at the
  print's minute, which the 2 h sweep cannot give; the E016 census (walked 9.74%) suggests a thin cell. Not proposed.
- **Maker reactivity as a stand-alone state (mean price step between consecutive prints).** Folded into CH180 as the
  `path_maxstep_share` secondary; alone it is Kyle's lambda with a new name.
- **Wallet features of any kind, skilled-wallet presence as maker toxicity, copy rules.** WS1 P2-P4 null; E026 (copy-
  skilled) is in design and the owner asked not to duplicate it; rounds 1-10 rejected wallet routes for reasons that
  hold. The toxicity use of P1 is noted for E026's designer, not proposed here.
- **Holder-side asymmetry (top-20 YES holders against NO holders from CB8-H).** CB8-H's store is sealed for its window;
  a holder feature besides. Not proposed.
- **Cross-venue ideas on the sealed stream before 2026-11-04** (CH165, CH166 stand as round 9 left them), **anything
  that reads E011's alerts before 2026-11-11, LT2's, LT3's or LT4's stores, CB16's, CB17's, CB18's, E025's or E026's.**
  Stores stay closed.
- **The four new keyless streams (PredictIt, Smarkets, ESPN odds, Gamma rules).** PredictIt and Smarkets price a few
  hundred political questions in a few dozen events (dependence by construction; CH114, CH25 and CH115 own the
  anchors); ESPN odds is sports-only (CH29 owns it; the scope decision is the user's); Gamma rules dates text edits
  (CH08, CH63, CH64 and CB18's CH177 own them). Their install is not recorded in the documents read. Not proposed.
- **UMA proposal and dispute objects, holding rewards, tick regimes, reward cliffs and shocks, series base rates and
  rolls, genesis and first-day prints, seed anchors, mention baskets, external anchors and clocks, barrier confusion,
  quoter grain, wake-up prints, book age, breathing book, mint share, turnover, synchronous prints, exit pressure,
  cost and lag maps, quoted versus traded moves, walked flow, trains, attention surges, breadth, class-conditioned
  longshots, arrivals and cancellations, age of the move, opens and closes, concentration, hollow liquidity, program
  versus human, last-mid proxy, front page, silent edits, races.** CH01-CH179: not re-proposed; where an idea touches
  one, the parent is named and the new field, clock, target or join is stated (CH180 on E021/E016; CH181 on E002-E006
  and CH20/CH93; CH182 on CH42 and CH144; CH183 on CH71/CB6-R and CH116; CH184 on CH158/CH159; CH185 on CH69/CH162;
  CH186 on E015/CH175; CH187 on round 7's parked item and CH08; CH188 on CH22/CH67; CH189 on CH62; CH190 on E003/E022).
- **Resolution-fetch arms as LT5 primaries.** Still needs-fetch for pure readers; the engine's `res_7d` label and
  CH175's proxy are the two sanctioned routes, used only by the engine-first ideas (CH186, CH189) and as secondaries.
- **Taker routes as primaries anywhere.** The cost model's 2.9-7c hurdles against grosses of a fraction of a cent;
  every taker route here is reported, never a verdict.

---

## 5. Sources consulted

### 5.1 No host probe, no network, no data-dumps read this round (by instruction); what was read instead
Round 9's probes (P1, P1b, P2, P2c) and round 10's counts table as quoted there; LT3's census results (C1/C3/C4
q0470, C2 q0472) as recorded in `LIVE_TESTS_3.md` §7.6 and the ledger; LT4's planning MDEs and lessons L1-L15
(`LIVE_TESTS_4.md` §0, §1.0, §7); the cost-model calibration (`COST_MODEL.md` §4, 2026-10-16 to 10-19); the maker-
rewards development snapshot (`MAKER_REWARDS_STUDY.md` §1, §6.2); the WS1 development results
(`signal_engine/families/WALLET_SKILL.md` §6); the engine's coverage numbers (`signal_engine/DESIGN_V1.md` §3).

### 5.2 AREPO documents read (cited inline by name)
`CREATIVE_HYPOTHESES_2026-10-24.md` (header, §0.1, counts table, §3, §4; idea lead sentences of all ten earlier rounds),
`NEW_STREAMS_2026-10-19.md`, `COLLECTION_HOST.md`, `LIVE_TESTS_2.md` §0, `LIVE_TESTS_3.md` §0 and §7, `LIVE_TESTS_4.md`
§0, §1.0 and §7, `EXPERIMENT_LEDGER.md` (the most recent entries: LT3 censuses and rulings, LT4 R1/R2, WS1, CB12, CB14-W,
CB17, CB18, E010 rule, E011 deviation), `COST_MODEL.md`, `MAKER_REWARDS_STUDY.md` §1-2 and §6.2,
`signal_engine/NORTH_STAR.md`, `signal_engine/DESIGN_V1.md` §1-8, `signal_engine/families/WALLET_SKILL.md`,
`PRIOR_ART_2026-10-19.md` §1 (top 10 gaps), `CREATIVE_BATCH_6.md` (CB6-R design lines), `CREATIVE_HYPOTHESES_2026-10-19.md`
(CH116), `CREATIVE_HYPOTHESES_2026-10-21.md` §4 and `-22.md` §4 (the parked and probed items), `LIVE_TRADE_MONITOR.md`
(fields), `AREPO_V2_CHECKPOINT.md` (live section; E026 and new-streams status).

### 5.3 External literature (named, not fetched)
George and Hwang 2004 (the 52-week high and momentum); Grinblatt and Han 2005 (disposition effect and the capital-
gains overhang); Frazzini 2006 (disposition and under-reaction to news); Barndorff-Nielsen and Shephard 2004 (jumps
against diffusive variation); Rosu 2009 (dynamic limit-order markets, patient traders); Avellaneda and Stoikov 2008
(inventory skew); Almgren and Chriss 2001 (optimal execution schedules); Copeland and Galai 1983 (the quote as a free
option); Glosten and Milgrom 1985 (the informed maker's quotes); Cont, Kukanov and Stoikov 2014 (order imbalance and
price changes); Hong and Stein 1999 (gradual information diffusion); Gutierrez and Prinsky 2007 and Blitz, Huij and
Martens 2011 (idiosyncratic momentum); Sonnemann, Camerer, Fox and Langer 2013 (partition dependence in prediction
markets; §4 only); Lee and Swaminathan 2000 (volume and momentum; §4 only).
