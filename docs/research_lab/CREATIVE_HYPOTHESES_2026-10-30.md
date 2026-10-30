# Creative hypotheses, round 16: the price of the quote, the ladder's edge and the dollar weight of a move (2026-10-30)

`evidence_role: none` | status: **IDEAS ONLY, nothing tested, nothing registered.** No edge, calibration, tradability or
profitability claim. AREPO never trades; every "money route" below is a paper rule to be tested on historical data and
then prospectively. Written by the creative-lead pass at the user's request (written 2026-10-23 07:00-07:50Z on parent
`ff2b509b` (`chore/arepo-claude-setup`) in the worktree `feat/creative-r16`; the file carries the round's planned date as
earlier rounds did). Round 1 is `CREATIVE_HYPOTHESES_2026-10-15.md` (CH01-CH34), round 2 `-16.md` (CH35-CH59),
round 3 `-17.md` (CH60-CH78), round 4 `-18.md` (CH79-CH98), round 5 `-19.md` (CH99-CH117), round 6 `-20.md` (CH118-CH130),
round 7 `-21.md` (CH131-CH143), round 8 `-22.md` (CH144-CH155), round 9 `-23.md` (CH156-CH168), round 10 `-24.md`
(CH169-CH179), round 11 `-25.md` (CH180-CH190), round 12 `-26.md` (CH191-CH201), round 13 `-27.md` (CH202-CH211), round 14
`-28.md` (CH212-CH221), round 15 `-29.md` (CH222-CH231); this file starts at **CH232** and repeats none of them. Where an
idea builds on an earlier one, the parent is named and the new mechanism, clock, population or join is stated. Every
number quoted from an AREPO document is a development, census or probe result, not evidence. One file; no code, no queue
specs, no other commits. **No network request, no host probe (no `ssh oracle`) and no `data-dumps` read were used for this
round** (by instruction); every count below is taken from a named AREPO document (`EXPERIMENT_LEDGER.md`'s tail of
2026-10-22/23, `signal_engine/STATUS.md` (10-23 04:05 UTC+1), `signal_engine/NORTH_STAR.md`, `signal_engine/CANDIDATES.md`
(rounds 1-7, the round 12-15 notes, the builder table and the "not candidates" list), `signal_engine/DESIGN_V1.md`
section 3, `LIVE_TESTS_8.md` section 7, `LIVE_TESTS_10.md` sections 5 and 7, `HYPOTHESIS_BATTERY_1.md` (the id table and
its results rows), `EXECUTION_COSTS.md`, `COST_MODEL.md` section 2, `MAKER_REWARDS_STUDY.md`'s rule row, the row and sidecar
column lists in `extract.py` and `ext_sidecar.py`, round 14's sections 0.1-0.2 and round 15's sections 0-5) and is named
as such. Where no count exists the entry is marked **unprobed** and the pre-registration census is the first gate.

## 0. How to read this file

**The brief that binds this round (owner priorities 2026-10-19 and 10-21; orchestrator brief for round 16).** Original
hypotheses about how money could be made lead the programme, and the programme's dominant failure mode is the
pre-registration census: LT5, LT6 and LT7 closed with zero tests, LT8 has lost one of three (CH204, 2026-10-23), and the
recorded killers are too few units a capture, too few distinct events, the block-gate share and an MDE above 0.5c
(round 14's 0.1 table; the CC8 line in the ledger). So this round is **census-first**: every live-test idea states, from a
named count or marked unprobed, its expected units a capture and distinct events over 21 days and an honest survival
prior; anything that cannot plausibly clear about 2,000 units a capture and 500 events is engine-first. It also feeds the
signal engine (NORTH_STAR: champion = momentum + market state; challengers add one family each; scored at every capture)
with families defined on streams the engine already reads. Round 14's design rules 1-11 and round 15's 12-14 **bind here
unchanged**; this round adds three (0.2). Category-agnostic, sports as a parameter (the owner's call). No data-rights
topic is raised. Nothing here reads any registered live test's objects before its analysis.

**What changed since round 15 (from the ledger's 10-22 ~22:20Z to 10-23 ~07:20Z entries, STATUS 10-23 04:05 UTC+1,
CANDIDATES rounds 6-7 and the 07:20Z note, `LIVE_TESTS_10.md`).**
- **LT10 is DESIGN-TEXT FROZEN** on round 15's top three (CH224 the hedged maker's price, CH223 the other venue's makers
  flinch first, CH222 the venue that traded first) at `34b7e22e` (sha256 `1da6c075…`, merged `6f651f7e`), before
  2026-11-03T02:00Z as required; family label `informed (E009, E010)`; census (seal `[10-21, 10-31)`) only after both
  E009's and E010's analysis commits; window proposed 11-10..12-01, analysis after 12-02T12:00Z. The challenger's R1
  (REVISE, 7 must-fix) and re-check (ACCEPT_WITH_FIXES) are applied; the designer's odds that no LT10 test registers
  rose from 0.66 to **0.76** (a judgement). Tokens `kxbook` (to 2026-12-04T00:00Z) and `attrlimit_lt10` are applied in
  `config.EMBARGO` (`0a245fa6`), and the engine's second `xvenue` read root (step O3, `xv_quotes/quotes/`) is live. The
  poller is projected to hit its 2 GiB cap about 11-16; the D-LT10-1 successor (quotes-only, new files, same pairs and
  grid) is the committed route. LT10's recomputed planning MDEs: CH224 0.30c / 0.23c (floor 1.0c, F binding), CH223
  0.47c / 0.26c, CH222 0.63c / 0.44c (fails at the low end; put to the challenger). CF10's family gate (>= 60 pairs in
  >= 30 events, `G_eff` >= 15) is named as the likeliest killer.
- **LT8's captures census CC8 (q0622, 2026-10-23 06:03Z) dropped CH204** (the market's own clock): 3.35 scheduled
  markets a capture against 1,200; projected hot units 6.3 (< 25,200); projected distinct events 119.7 (< 500); cap
  share 0.20 (< 0.40); block-gate share 0.33 (< 0.50); the class MDE not finite. Nothing counted. CH203 and CH202 wait
  for CS8 (q0623, before 2026-10-28T03:30Z). The `sched` token's withdrawal is requested (CANDIDATES ~07:20Z).
- **LT9's census code phase 1 is merged** (`9e482fab`; censuses CR9 / CC9 / CS9, drafts q0640-q0647 unpromoted); its
  seal waits for the 2026-11-02..11-12 span. LT9's declared odds: CH213 0.15, CH214 0.30, CH212 0.30, CH215 0.10.
- **LT7 CLOSED at census with no test**; LT5, LT6, LT7 have zero registered tests; LT4 registered one (E022, window
  10-26..11-16, analysis after 11-17T12:00Z). E026 is registered (its modules frozen to 12-07). E009 / E010's
  `cross_venue_live/` stays sealed to 2026-11-03; E011's `surprise_live/` to 11-10; E015's analysis is 11-15.
- **The engine:** K = 7 (8 with se21; 10 by 11-19); champion `se0_champion_lr_mm`; the first two-day leaderboard shows
  the LightGBM challengers about +0.05 nats over the logistic champion on every direction target (a learner effect; no
  promotion possible before about 11-04); the per-market signal feed (`se-feed-v1`) is live on the owner's /lab (PR
  #28); the embargo table of STATUS (xvenue 11-04; tte and dispgap 11-14; flow 11-16; rewards and hollow 11-18;
  surprise and dormant 11-19; movetype 11-22 (E015); participation 11-25; wallet 12-07; kxbook 12-04; book / book0,
  bandbreak, pool, rwblink 2027-02-14; quietbook, swclock 2027-01-23) binds every family below. The builder asks for
  families with a real prior only, since each raises K.

### 0.1 The census arithmetic, stated once: what a live test needs per capture

The brief's "about 2,000 units a capture" is not a convention; it falls out of round 14's planning formula at the
programme's floors. The table gives the effective count at which the pessimistic MDE equals the floor, and the units a
capture that count implies over 21 days (252 captures) at the planning effective share of 0.8. Every entry below quotes
its own counts against this table.

| Target (SD) | Estimator | `DE_gate` | `n_eff` at the floor | Units a capture (no F) | Units a capture with F (`r_w` 0.2; 0.1 for movers) |
|---|---|---|---|---|---|
| 2 h mid change (4c), floor 0.5c | class contrast, balanced | 31 (whole or rewarded panel, cap 10) | 139,800 in the smaller class | about 690 in the smaller class | about 1,740 |
| 2 h mid change (4c), floor 0.5c | slope at the tercile gap | 31 | 338,300 | about 1,680 | about 4,200 |
| 2 h mid change (4c), floor 0.5c | slope | 6.196 (mover families, E022's) | 67,600 | about 335 | about 745 |
| next \|move\| (3c), floor 0.5c | slope | 31 | 190,300 | about 945 | about 2,350 |
| 2 h spread change (2c), floor 1.0c | class contrast, 1 : 11 (one slot of twelve) | 31 | 4,760 in the event class | about 24 event market-days a capture | about 60 |
| 2 h spread change (2c), floor 1.0c | slope | 31 | 21,100 | about 105 | about 260 |

Two readings steer the round. **The spread is the cheapest honest target in the programme by an order of magnitude**, so
a mechanism whose first trace is a maker's re-quote (a side vacated, a bid retreating under an arbitrageur's selling) can
be tested on a population that would be hopeless for a mid target. And **a mover family at E022's design effect needs
one fifth of the units a whole-panel slope needs**, so a continuous state on every traded mover, read from the rows and
sidecar alone, is the one mid-target design that clears the table with margin. The three live-test candidates are built
on exactly those two facts: two spread-target tests of rule-created discontinuities (CH232, CH233) and one mover-family
mid test (CH234).

### 0.2 Design rules (round 14's 1-11 and round 15's 12-14 bind unchanged; three additions)

15. **The rule-boundary clock.** A state may be the crossing of a *venue-published constant* at which a published rule
    changes a maker's obligation (the liquidity-reward two-sided rule at 0.10 and 0.90), read from the captures' own
    mids at k - 1 and k. The crossing slot is the unit's event and is read on all 12 slots of its market-day (rule 2);
    the first crossing of the market-day is the state and later re-crossings are a declared class, reported; the control
    panel is the same crossing where the rule does not apply (unrewarded markets under LT7's 13.7 carry rule with the
    CLOB feed as adjudicator). The venue's rule page is re-read on the day of the pin and the reading recorded; the
    *sign* the mechanism predicts is fixed from that reading before the census. The tick boundary at 0.04 / 0.96 belongs
    to CH86 and is not a state here (4.0).
16. **Event-join completeness.** A state built from an event's other members (the bid sum, the parent's children) is
    defined only on capture pairs in which every member of the event is present in both captures with a two-sided
    quote; incomplete event-captures are `unavailable`, counted, never filled. The census prints the completeness share
    and drops the test if fewer than 60% of member rows are complete. Events with more than 10 eligible members are a
    reported arm (round 14's rule 7 cap).
17. **Mover-family states vary beyond the move's sign.** A state defined on movers must have within-market-day variance
    beyond `sign(d)` and the level (the VIF gate against `sign(d) x f(p)` controls binds), and where the mechanism needs a
    paid trade the quote-only movers are the built-in twin, labelled `informed (E015)` if the pin follows E015's
    analysis (2026-11-15).

**Hygiene that binds every idea** (round 14's paragraph applies: decision time is the latest input's own receipt; targets
start after it; nothing reads outcome fields except engine-first `res_7d` features; the primary is a within-stratum
contrast or slope by expanding-past demeaned OLS, the Freedman-Lane gate in the census-fixed stratum is binding, the
liquidity-tier correlation gate (|corr| <= 0.5 within and pooled against `log1p liquidity` and `z log rv24`) and the
AR(0.9) scenarios bind, and F in LT7's one-rule form is a verdict condition where its census F-MDE is under the target's
floor). Sports stays a parameter (the sidecar's `fee_type` plus CB17's frozen list); every entry reports its sports arm
uncounted. Nothing here is a maker mark-out object; J4-R's and CB13-T's holdouts are not read.

**Scores.** N novelty (1-5), EV expected value if true (1-5), **L live-ready (1-5):** 5 = a pure reader over the rows or
sidecar the host already writes with the population counted by a named probe; 4 = pure reader, population bounded above
by a named count; 3 = pure reader with an unprobed population, or a matcher or map first; 2 = a stream whose coverage is
unprobed, or a collection change; 1 = fetches or weeks. My judgement, not measurements.

**Planning-MDE arithmetic (round 14's, stated once).** Class contrast: `MDE = 3.47 x SD x sqrt(1/n1_eff + 1/n2_eff) x
sqrt(DE_gate) x 1.5 x sqrt(max(1, VIF_w))`; slope per SD of a continuous state times the tercile gap (about 2.2 SD):
`MDE = 3.47 x SD / sqrt(n_eff) x sqrt(DE_gate) x 1.5 x sqrt(VIF_w) x gap`. `n_eff` = 80% of raw (planning). `DE_gate`: 31
(events capped at <= 10 members), 51 (uncapped; the fine-clock lane), 6.196 (mover families), 3.0 (one game one cluster).
`VIF_w` 1.3 for row and sidecar states, 1.5 for book states. SDs: 2 h change 4c; |2 h move| 3c; spread change 2c; 20-min
Kalshi spread change 1.0c (planning; unprobed). **F-MDE** = `MDE x sqrt(2 / (1 - max(0, r_w)))`, capped at the floor as a
verdict condition. Every MDE is quoted at the low and high planning counts and at a quarter of the low one.

**Structural facts this round relies on (counts only; sources named; no new probe).**
1. Eligible markets a capture 42,161-51,790 (DESIGN_V1 sections 3 and 16, as rounds 13-15 quoted); non-sports about
   30,000 (derived); eligible non-sports on the 10-21 22:31Z capture 18,232 (CH199's narrower filter).
2. **The reward probe (q0601c; round 14 fact 2):** listed (rewarded) non-sports ex-crypto market-captures about
   9,000-10,700 a capture; the field omitted on 62.2% of rows; switching markets 2,112-3,995 a day. The reward rule as
   AREPO's documents record it: score `((v - s) / v)^2 x b`, sampled once a minute, daily UTC epoch, $1 minimum; and
   **"two-sided quoting is required outside [0.10, 0.90]"** (`COST_MODEL.md` section 2 and `MAKER_REWARDS_STUDY.md`'s rule
   row, both quoting the venue's page), while CH71 (round 3) and round 14's rule 11 record the *usual* reading as the
   reverse (two-sided required inside [0.10, 0.90], one-sided scored outside). The disagreement is itself a fact this
   round uses: the obligation changes at the boundary under either reading, and the pin re-reads the page.
3. **Fees and rebates (`COST_MODEL.md` section 2, quoting the venue's pages, retrieved 2026-10-19):** taker fee
   `rate x p x (1 - p)` (politics, finance, tech, mentions 0.04; sports, economics, culture, weather, other 0.05; crypto
   0.07; geopolitics 0; some sports still 0.03); makers never pay; maker rebates funded by the market's taker fees at
   25% (other), 15% (sports), 20% (crypto) of the fee-equivalent; a two-sided maker's fill-weighted mark-out before
   rebates -0.37c [-0.64, -0.10] (`MAKER_REWARDS_STUDY.md`, development). Round trips (`EXECUTION_COSTS.md`, one sweep):
   median 4.5c; politics 3.6c, economics 3.4c, culture 3.6c, finance 4.7c, weather 4.5c, sports 5.2c; by liquidity
   >= 100k 1.8c, 10k-100k 3.1c, 1k-10k 4.7c.
4. **The price grid of the venue (the same sweep, 37,225 tokens, all categories):** mid < 0.05: 8,218 (22%);
   0.05-0.20: 10,597 (28%); 0.20-0.80: 16,158 (43%); 0.80-0.95: 1,485 (4%); >= 0.95: 645 (2%). Half the venue sits
   below 0.20, where a one-cent spread is a large fraction of the cheap side's collateral.
5. **Movers:** 2,750 non-sports 2 h movers an interval (P1b, as `LIVE_TESTS_7.md` quotes it); on a capture 4,244 movers
   with |x| >= 0.01, of which traded 30%, ambiguous 4%, parallel 4.4%, one-sided 5.4% (DESIGN_V1 section 19); about a
   third of 2 h movers have already moved by the time sweep 1 is read (section 21); 48% of movers have never traded
   (CH167).
6. **Row and sidecar fields (code reading, `extract.py` and `ext_sidecar.py`):** every capture row carries `best_bid`,
   `best_ask`, `spread`, `last_trade_price`, `neg_risk`, `neg_risk_market_id`, `neg_risk_other` (the augmented "Other"
   member flag), `event_neg_risk_augmented`, `event_id`; the sidecar carries `event_ids`, **`parent_event_ids` (v3,
   aligned with `event_ids`)**, `series_slugs`, `fee_schedule` (rate, exponent, rebateRate), `fees_enabled`,
   `accepting_orders`, `order_price_min_tick_size`, `volume_num` (cumulative), `event_volume`, `event_liquidity`,
   `event_open_interest`, `event_comment_count`, `rewards_min_size`, `rewards_max_spread`, `clob_rewards`,
   `uma_resolution_statuses`. The engine's `market_state` family holds a neg-risk flag, mid, spread, log liquidity, log
   24 h volume, hours to end, tick, market age, own 24 h realised volatility and the category; `momentum` holds the
   venue's 1 h / 1 d / 1 w changes and the own 2 h / 6 h / 24 h changes (DESIGN_V1 section 3).
7. **The record on neg-risk sums and price levels (development, HB1 and the ledger):** E005 (a member's deviation from
   its arbitrage band predicts repricing beyond the frozen reversal): **not supported, challenger CONFIRMED** (2026-10-11).
   HB1: XM1 (neg-risk sum deviation, 6 h drift) +0.19c, Holm 1.0; XM2 (|sum - 1| adds to |move|) null; XM3 (sum of
   neg-risk siblings' 2 h changes, own 2 h drift) -0.094c [-0.176, -0.026] in the predicted direction, Holm 0.85, not
   a survivor; PX1 (mid <= 0.15, 24 h downward drift) **survived** (+0.48c, replicated); PX5 (1 d momentum continues
   within 0.10 of 0 / 1) +8.66c on discovery in the predicted direction, Holm 0.83, not a survivor; MI4 (2 h reversal
   differs within 0.10 of 0 / 1) Holm 1.0. HB1's neg-risk frame: 30,203 rows in 127 clusters. CANDIDATES "not candidates": neg-risk sums and sibling
   lead-lag; PX2; MI5. The builder's deliberate exception: the `event` family (se8 / se10, visible since
   2026-10-22T12:00Z) holds event size, **neg-risk overround and quoted share, normalisation gap**, own rank, largest
   sibling and siblings' Gamma 1 h / 1 d changes, as levels.
8. The fine clock (round 15 fact 2; LT10 section 7): 70-116 pairs, 144 origins a pair a day; CF10's family gate >= 60
   pairs in >= 30 events with `G_eff` >= 15; `DE_gate` 51; the Kalshi lines carry `k_bid`, `k_ask`, `k_last`, both sizes,
   `k_vol24`; the Polymarket lines the CLOB touch, sizes and `p_book_ts`.
9. The gates a captures census demands (LT8 section 7, as frozen): per-capture unit floors (CH203 >= 10,000 quiet units
   a capture; CH202 >= 800 contrasted a capture; CH204 >= 1,200 scheduled markets a capture), projected distinct events
   >= 500, cap share >= 40%, block-gate share >= 50%, `max(declared, design)` MDE <= 0.5c, within and pooled |corr| <= 0.5
   against the liquidity and volatility tiers, `VIF_w` finite, the venue-clock and category-concentration prints.

**Counts table (what was counted before each idea was written; the source named; `unprobed` where nothing was).**

| ID | Unit | Count on the host | Source |
|---|---|---|---|
| CH232 | rewarded non-sports ex-crypto market x capture whose mid crossed 0.10 or 0.90 between k - 1 and k (first crossing of the market-day), plus the 11 other slots of that market-day | rewarded 9,000-10,700 a capture (probe); the share within 3c of a boundary and the crossing rate **unprobed** (planning 50-150 crossings a capture from fact 4's grid) | fact 2; fact 4 |
| CH233 | neg-risk member x capture in a complete event-capture (rule 16), events capped at 10 members | neg-risk member rows a capture **unprobed** (planning 3,000-10,000 complete rows in 300-1,200 events); HB1's frame 30,203 rows / 127 clusters over its window | fact 6; fact 7 |
| CH234 | non-sports ex-crypto traded 2 h mover x capture (E015's traded class, read from `volume_num`) | 2,750 non-sports movers an interval; traded 30% of a capture's movers (DESIGN_V1 section 19, all categories; planning 30-40%); ex-crypto share **unprobed** (planning 70-85%): **580-935 traded movers a capture** | fact 5 |
| CH235 | every eligible row (level columns); movers (the weight column) | 42,161-51,790 rows; 2,750 non-sports movers | facts 1, 5 |
| CH236 | eligible row with 12 own slots and positive own 24 h volume | 12-slot coverage about 98% (`sp_rv6h` as a proxy); positive-own-volume share **unprobed** (the display's `volume24hr` presence of 22% is a serving fact, not the host's own sum) | round 14 fact 5; DESIGN_V1 section 16 |
| CH237 | eligible row with a non-empty `parent_event_ids` | **unprobed** (the field is v3 of the sidecar; no count exists) | fact 6 |
| CH238 | neg-risk member row (columns) | as CH233 | fact 6 |
| CH239 | eligible non-sports row with a `gamma_rules` text before the origin | 44.7% of 18,232 (CH199's census); class parse rates **unprobed** | CANDIDATES row 17 |
| CH240 | the crossings of 0.10 / 0.90, 0.04 / 0.96 and the neg-risk headroom of 1 per capture, by category and reward status | a map; counts 0 until run | - |
| CH241 | pair x 10-minute origin on E009's stream with a Polymarket spread innovation over `[t - 10, t]` and a Kalshi quote at `t + 20` | 70-116 pairs; the SD of Kalshi's 20-minute spread change **unprobed** | fact 8 |

---

## 1. Map: where money might be, given the costs, the census deaths and the price of a quote

The cost model fixes the frame (2.9c in the most liquid tier, 4.5c at the median touch, 5.2c in sports; makers about
break-even before rebates and rewards; a 3.1% passive fill rate within an hour); the arithmetic of 0.1 fixes the design
(spread targets on dense discontinuities; mover-family mid targets). The reading that steers this round is one fact
about the venue that every earlier round has walked past: **a resting quote costs its poster the collateral of the side
it posts, and that cost is not symmetric.** A YES bid at 0.91 ties up 91c a share; the YES ask at 0.93 is a NO bid at
0.07 and ties up 7c. A maker paid by the minute for quoting (the reward programme) or by the fill (the rebate) maximises
reward per dollar and therefore crowds the cheap side and starves the expensive side; the venue's two-sided rule changes
what that maker *must* do at a published price; a ladder's conversion arbitrage only runs in one direction (CH09) and
hits the bids, not the asks; and a taker who moves a price toward the extreme pays ten times the collateral a share of
the taker who moves it back. Each of those is a dated, mechanical, side-specific prediction on a dense panel, and none
of them is momentum, reversal or imbalance.

| Family | What the host already dates that nobody has read | Money route |
|---|---|---|
| A. The two-sided rule's boundary (CH232) | a rewarded market's mid crossing 0.10 or 0.90; the side the farmers vacate or must fill at that crossing | maker: step aside on the expensive side at an outward crossing (the touch there is about to retreat through you), return at an inward one; the hold-to-resolution buyer of the extreme side enters after the retreat, not before (gross; reported) |
| B. The ladder's edge (CH233) | the event's bid-sum headroom shrinking toward zero: the conversion arbitrageur's selling arrives on every member's bid | maker: lower or pull bids across the event when the headroom closes, re-post after; the thin members' overshoot after the arb's selling is the buyer's entry (reported) |
| C. The dollar weight of a move (CH234, CH235) | whether the trade that moved the price paid 90c or 10c of collateral a share | maker: re-centre fully on dollar-heavy moves, lean against dollar-light ones (gross); taker: follow the heavy, fade the light (reported, 3-5c hurdles) |
| D. Engine-first (CH236-CH239) and the map (CH240) | the age profile of the displayed volume; the parent event's other children; the ladder's headroom columns; the rules' class | engine: forecast quality and `res_7d` calibration; the map counts the crossings before any census |
| E. The reverse fine clock (CH241) | Polymarket's spread innovation against Kalshi's next spread change: who hedges where | the following venue's maker quotes inside after the leading venue tightens (a Kalshi route, outside the Polymarket remit: the owner's call) |

**Data labels.** `A` = on the host now (captures, sidecar, two sweeps, trade samples, the monitor, the E009 / E010 poller's
quotes, the engine's `quotes/`, `features/` and aux tables, the four keyless streams, `reward_params`). `A~` = on the host
but a join has to be written and counted first (the event join, the parent join, the rules parse). `P` = a fetch is
needed (none here). **Sealed and not usable by anything here:** LT2's, LT3's, LT4's (E022's) and LT7's stores, LT8's,
LT9's and LT10's once registered, CB16's and CB17's stores, CB8-H's holders, E009 / E010's `cross_venue_live/` to
2026-11-03, E011's `surprise_live/` to 11-10, E025's and E026's stores and the E026 frozen modules. J4-R `[2026-10-16,
2026-10-21)` and CB13-T's holdout `[2026-10-21, 2026-10-26)` are refused for every maker mark-out object; nothing here is one.

**Windows and registration this round proposes (LT11, "the price of the quote").** An eleventh family on the captures and
sidecar (sealed sweeps as reported secondaries only), registered separately from LT2-LT10 with its own Holm family
(k <= 3): CH232, CH233, CH234.
- **Fast lane.** None of the three reads a state LT8, LT9 or LT10 tests (LT9's band is the reward spread band, CH232's is
  the price; LT8's movers are classified by sweep receipt, CH234's by collateral; LT10 is the fine clock), so they can run
  in the empty captures slot after E015's and E022's windows: **window 2026-11-18T00:00Z .. 2026-12-09T00:00Z**, analysis
  on or after 2026-12-10T12:00Z, **provided the design text is frozen before 2026-11-14T12:00Z** (before `T_E015` 11-15
  and `T_E022` 11-17, so CH234's traded class and CH232's reward control are chosen blind) and the censuses run on a
  fresh seal of 2026-10-28..11-07 (ten days; DST on 11-01 falls inside the census days and is disclosed as LT8 disclosed
  it; the window is on winter time). Overlap with LT2, E011's analysis, E026 and LT10 is overlap only (different
  hypotheses, different states or streams, no pooling).
- **Ordered lane.** If the pin is not before 11-14T12:00Z, `REGISTERED_UTC` = the first 00:00Z at least 24 h after LT9's
  `END_UTC` and after the LT11 registration commit, never before 2027-02-14T00:00Z; 21 days; single analysis >= 36 h
  after the end; a pin after `T_E015` labels CH234 `informed (E015)` and a pin after `T_E022` labels CH232 `informed
  (E022)`.
- **Tokens (filed in CANDIDATES at the freeze, before any isolating challenger):** `bandside` (CH232), `nrslack` (CH233),
  `dollarw` (CH234), each to the later of LT11's analysis commit and the lane's date; an attribution limit on mid x own
  2 h change interactions and on neg-risk bid-sum differences for the champion and the broad models to the same date.
  The `event` family's existing levels are not requested.

## 2. Hypotheses

### A. The two-sided rule's boundary (parents CH71, CH45, CH16, CH19, CH213 / LT9, CH183 / LT5 R, CH116, CH72, LT7's 13.7 ruling; literature: Foucault, Kadan and Kandel 2005 on the cost of a limit order, Glosten and Milgrom 1985, the Telonex case as MAKER_REWARDS cites it)

**CH232. The cheap side's cliff: a resting quote costs the collateral of the side it posts, so at a mid of 0.92 the YES
ask (a 7c NO bid) is cheap and the YES bid (91c) is dear. Inside [0.10, 0.90] the reward rule makes the farmers post
both; at the published boundary the obligation changes, and whichever side the rule frees is the dear side they drop
(or, under the reverse reading, must add). The crossing is dated to a slot by the captures' own mids, it happens on a
rewarded panel of nine to eleven thousand markets with half the venue priced below 0.20, and its first trace is not a
mid but a spread: the dear side's touch retreats within a slot of an outward crossing and returns within a slot of an
inward one, on rewarded markets only. CH71 read the band's two sides as a level discontinuity; this reads the crossing
as an event and the maker's side choice as the mechanism.**
- Mechanism and why it is non-obvious. A limit order's cost is its collateral for as long as it rests (Foucault, Kadan
  and Kandel 2005); a quoter paid per minute of resting size (round 14 rule 11's formula) earns the same score on either
  side but pays 91c for one and 7c for the other, so the dear side is posted only where the rule demands it. The rule's
  boundary is a venue constant; a mid that crosses it changes the *obligation* without any change in the question. Who
  pays: the maker still resting on the dear side when the farmers leave it (the touch retreats through him; he is now
  alone and adversely selected by the next retail print) and the hold-to-resolution buyer who crosses the dear side's
  stale touch just before it widens. Why the crowd misses it: the boundary is read as a reward fact (where farming
  stops), not as a side fact (which quotes disappear).
- Parent and what is new. CH71 (the reward-shadow band): a regression discontinuity on the spread and depth *levels*
  just above against just below 0.90, with a maker route above 0.90. New here: the crossing as the clock (an innovation,
  rule 3), the spread *change* at k + 1 as the target, the side-specific prediction (the dear side's touch, from
  `best_bid` / `best_ask` on the rows and the sealed sweeps' sizes as a reported secondary), the unrewarded control panel
  (the same crossing where no obligation changes), and the two-direction twin (outward against inward crossings). CH213
  (LT9) reads the spread crossing the *reward* band `2v`; this reads the *mid* crossing the price band; the two share the
  rewarded panel and nothing else (disclosed; no time overlap in the fast lane).
- Data join and decision clock (`A`, L 4). Unit: rewarded (LT7's 13.7 `listed_carry24h_v2`, the CLOB `reward_params`
  feed adjudicating) non-sports ex-crypto market x capture on a market-day whose first crossing of 0.10 or 0.90 between
  k - 1 and k is the market-day's event (rule 15); all 12 slots of that market-day are units. State: `xo_k` = 1 on the
  outward-crossing slot (the mid left [0.10, 0.90]), `xi_k` = 1 on the inward slot, 0 on the other slots; `dear_side`
  (the side with collateral > 0.5 at k, mapped to bid or ask); `recross` (a later crossing in the same market-day;
  reported class). Decision time: the row's `received_utc` at k. Controls: the mid at k - 1 and k, the own 2 h change
  and |change|, the spread level at k, `log1p liquidity`, the reward band `v`, tier, `neg_risk`.
- Target and horizon. `ds = spread_{k+1} - spread_k` (the next slot's spread change; SD 2c; floor 1.0c); hypothesis
  under the planning reading (two-sided required inside, one-sided scored outside; the pin fixes it): within market-day,
  E[ds | xo] - E[ds | other slots] > 0 and E[ds | xi] - E[ds | other] < 0, each one-sided; the pre-declared
  *interaction* with the unrewarded crossing panel (the same contrast where the rule does not apply) is the verdict
  condition where its census MDE is under 1.0c, else the control panel is a reported arm. M1: the dear side's touch
  change (`d(best_bid)` where the dear side is the bid; `-d(best_ask)` where it is the ask) at k + 1, signed as the
  mechanism predicts. M2: the mid's change at k + 1 toward the band (the mechanical pull as the dear side retreats;
  reported; a mid target the counts do not reach). M3 (sealed sweeps, reported): the dear side's 1c and 5c depth
  between the passes k and k + 1 against the cheap side's.
- Paper rule and economic check (rule 11: maker-side). Maker: on an outward crossing, cancel the dear side for one slot
  and re-post one slot later (the reward minute lost on one side against the adverse selection avoided when the touch
  retreats; the formula's one-sided share applies where the pin's reading scores one side); on an inward crossing,
  post the dear side at once (alone in the band on that side until the farmers return). Taker (reported, never a
  verdict): the hold-to-resolution buyer of the extreme side waits one slot after an outward crossing (the expected
  saving is the retreat; the hurdle is the 3.6c politics round trip he would not pay on a hold).
- Population arithmetic. Rewarded 9,000-10,700 a capture (probe); crossings a capture **unprobed** (planning 50-150,
  from fact 4's grid: 28% of tokens in 0.05-0.20, the rewarded subset more mid-priced, a share within 3c of a boundary
  and a 5-15% chance of crossing in a slot). 21 days: 10,500-31,500 crossing market-days, 126,000-378,000 units;
  `n1_eff` 8,400-25,200, `n2_eff` 92,400-277,000. Events: thousands (the longshots of politics ladders cross 0.10 most
  often; cap 10, DE 31; a ladder whose favourite moves sends several members across at once, so the honest cluster is
  event x slot and the block gate (event x day strata) is the census's first number).
- Permutation and cluster structure. Rule 2: market x UTC day strata of 12 units; the Freedman-Lane null (given the
  market-day, which slot carried the crossing does not matter for the next spread change) is the hypothesis's
  complement; binding scenarios: LT5 1-2, L10, round 14's S-worlds for the reward field (the null and the switching of
  `clob_rewards`: the control classification follows 13.7), and a declared **S25: a spread that mean-reverts after any
  large |move| regardless of the boundary** (the |change| control and the unrewarded panel must absorb it: the crossing
  must add to the move's size). Clusters: event; `DE_gate` 31.
- Planning MDE (spread target, class contrast 1 : 11). Low: `3.47 x 2c x sqrt(1/8,400 + 1/92,400) x sqrt(31) x 1.5 x
  sqrt(1.3)` = **0.75c**; high **0.44c**; a quarter of the low count 1.51c. The MDE gate (1.0c) passes at >= about 24
  crossings a capture. F: the far-future twin is a crossing over `(k + 2, k + 3]` (planning `r_w` 0.2): F-MDE 1.19c (low;
  over the cap: a reported label) / 0.69c (high: a verdict condition); the kill line at which F binds is about **60
  crossings a capture** (`n1_eff` 11,900). The control-panel interaction: about 1.07c (low) / 0.62c (high); a verdict
  condition at >= about 55 crossings a capture on each panel.
- Confounders and the control. A big move crosses the boundary and widens the spread for the move's own reason (the
  |change| control; S25; the unrewarded panel crosses the same boundary with the same moves and no obligation change);
  the tick regime changes at 0.04 / 0.96, six cents away (CH86's object; units whose mid also crossed a tick boundary in
  the same slot are a declared class, excluded from the primary, counted); the reward field's omission (13.7's carry;
  the feed adjudicates); E022's S2 reward split (the pin before `T_E022`); LT9's panel (no time overlap in the fast
  lane; the states differ).
- Most likely boring explanation. Crossings are too few on the rewarded panel (the farmers' markets are mid-priced) or
  are mostly ladder chatter around 0.10 (re-crossings dominate and the first-crossing rule leaves too little); or the
  venue scores the cheap side only and the farmers never posted the dear side at all, so nothing leaves at the
  crossing and the spread does not move (a clean null that the pin's reading would predict in advance).
- Cheapest census (counts only; the fresh seal; no target read). Crossings a capture by boundary and direction on the
  rewarded and unrewarded panels (kill if < 24 a capture on the rewarded panel); re-crossing share (kill if > 60% of
  crossing market-days have >= 3 crossings); the tick-coincidence share; the block-gate share (event x day strata) >=
  50%; cap share >= 40%; events >= 500; |corr| of `xo` with the liquidity and volatility tiers; `VIF_w`; pessimistic MDE
  <= 1.0c; F-MDE printed; the pin's reading of the rule recorded in the census header.
- Challenger feature: **yes, after 2026-11-18** (`rewards` embargo, E022's S2): columns of the `rewards` family at its
  next spec version (`rw_band_pos` = the mid's signed distance to the nearest boundary, `rw_outside`, `rw_dear_side`,
  `rw_cross_out_2h`, `rw_cross_in_2h`); no new challenger. Token `bandside` if LT11 registers.
- Sports arm: uncounted (sports game markets at 0.90 and above are the hope-premium population of CH23; the rule is the
  same; the fee rate differs).
- Scores: N 4, EV 3, L 4. Parents: CH71 (the band's level discontinuity), CH45 and CH16 (reward geometry), CH19 (the
  cliff at a programme's end), CH213 (the reward-band crossing), CH72 (the fee valley's taker side), CH116 (band-stripped
  imbalance). New: the collateral of a side as the maker's choice variable, the obligation's crossing as the clock, the
  spread as the target, the unrewarded crossing as the control.

### B. The ladder's edge (parents CH09, CH12, CH159, CH163, CH211, E005, HB1 XM1-XM3, the `event` family; literature: the conversion mechanics as CH09 states them, Glosten and Milgrom 1985)

**CH233. The arb's footprint: in a neg-risk event the sum of the members' YES bids cannot stay above one, because selling
YES into every bid and converting the NO set pays the excess at once (CH09's asymmetry: the ask-sum shortfall below one
has no such instant arbitrage and persists as a carry). The arbitrageur's selling lands on every member's bid in the same
minutes, so the dated object is not the mid-sum deviation E005 tested and found nothing in, but the headroom `1 - sum of
bids` closing toward zero and, a slot later, the bids retreating and the spreads widening across the event. The siblings'
bid-sum innovation, excluding the member's own bid, is a state on every complete member-capture; the ask-sum shortfall is
the twin on which the mechanism predicts no footprint.**
- Mechanism and why it is non-obvious. Conversion runs NO -> YES-of-all-others, so an excess of the bid sum over one is a
  riskless round trip that bots take within minutes; the shortfall of the ask sum below one is a hold-to-resolution
  carry that needs capital. The selling that closes the excess hits bids, not asks; the makers whose bids were hit re-post
  lower; the spread of every member widens from the bid side and the mid falls by half the retreat. Who pays: the maker
  whose bid is the one the arbitrageur sells into (he bought at a price the event's own arithmetic says is too high);
  who collects: the arbitrageur, and the buyer who takes the thin members' bids after the retreat has overshot. Why the
  crowd misses it: the headroom is an event-level number no market page shows, and E005's null on mids closed the
  subject for the programme.
- Parent and what is new. CH09 reads the asymmetry as a *level* carry (the full set bought under one); E005 read a
  member's deviation from its arbitrage band as a *mid* repricing (not supported); XM1 / XM2 read the mid-sum deviation
  as a level on drift and |move| (null); XM3 read the siblings' 2 h changes on the member's drift (-0.094c, same sign
  on replication, not a survivor); the `event` family holds the overround, the quoted share and the normalisation gap as
  levels. New here: the *bid-sum* headroom (not the mid sum), its *innovation* excluding the member's own bid (not a
  level), a *spread* target (the arb's footprint, not the mid's repricing), the completeness rule (16), and the ask-sum
  shortfall as the built-in twin. CH159 (ladder breadth) and CH211 (the ladder that travelled) read who re-quoted; this
  reads what the arbitrage forces.
- Data join and decision clock (`A~`, L 4: the event join on `neg_risk_market_id` / `event_id` from the rows is a reader,
  no matcher). Unit: non-sports ex-crypto neg-risk member x capture in a complete event-capture at k - 1 and k (rule 16),
  events capped at 10 eligible members (larger ladders a reported arm). State: `hb_k = 1 - sum_j bid_{j,k}` (the
  event's headroom at k), `dhb_sib_{i,k} = -(sum_{j != i} bid_{j,k} - sum_{j != i} bid_{j,k-1})` (the siblings' bid-sum
  innovation, signed so that a positive value means the headroom *closed* because of the siblings; standardised per
  event by the census's SD), `cross_k` = 1[hb_{k-1} > 0 and hb_k <= 0] (the headroom crossing: the arb's actual trigger;
  rare; M3). Decision time: the latest member row's `received_utc` at k. Controls: `hb_{k-1}` (the level), the member's
  own 2 h change and spread level, its bid share of the event's bid sum, `log1p liquidity`, event size, `neg_risk_other`,
  tier.
- Target and horizon. Primary: `ds_i = spread_{i,k+1} - spread_{i,k}` (SD 2c; floor 1.0c); hypothesis (one-sided):
  within market-day, the slope of `ds_i` on `z dhb_sib` > 0 (the siblings closed the headroom; the member's spread
  widens next). M1: `db_i = bid_{i,k+1} - bid_{i,k}` < 0 on the same state (the bid retreats). M2: the mid change at
  k + 1 (E005's object; reported; `informed (E005)` by the record). M3: the crossing class `cross_k` (E[ds | cross] -
  E[ds | other] > 0; rare; reported unless its count passes the 1 : 11 line of 0.1). **Twin:** the siblings' *ask-sum*
  innovation (`dha_sib`, the shortfall closing) as a second regressor: the mechanism predicts a slope near zero on it;
  the verdict condition is the difference of the two slopes (bid minus ask) where its census MDE is under 1.0c.
- Paper rule and economic check (rule 11: maker-side). Maker: when the siblings' bid sum rises so that the headroom is
  within one tick of zero, lower or cancel the own bid for the next slot (the fill avoided is the one the arbitrageur
  would have given you); re-post after the retreat. The reported buyer's route: after the retreat, the thin members'
  bids sit below the siblings' implied value by the overshoot; a resting bid there is the best fill on the venue
  (gross; no fills counted).
- Population arithmetic. Neg-risk member rows a capture among non-sports ex-crypto eligible: **unprobed**; planning
  3,000-10,000 complete rows (after rule 16 and the cap) in 300-1,200 events a capture; 21 days: 756,000-2,520,000
  units; `n_eff` 605,000-2,016,000; events over 21 days in the thousands (every nominee, leadership, "how many" and
  "who will" ladder on the venue). The headroom crossing (M3) is rare (planning 1-5 a capture; a reported class).
- Permutation and cluster structure. Rule 2 strata (market x UTC day; the state is continuous on every unit); the
  Freedman-Lane null (given the market-day, which slots carried a siblings' headroom closing does not matter for the
  next spread change); binding scenarios: LT5 1-2, L10, a declared **S26: a common event-level shock that moves every
  member's bid and spread in the same slot** (the state is lagged by construction; the own 2 h change is a control; the
  gate must hold on a simulated common shock with no lag) and **S27: a dormant ladder whose only mover is the favourite**
  (the per-event SD gate; the state degenerates to the favourite's move for the longshots, which is a dose, not a
  confound, and is reported by member rank). Clusters: event; `DE_gate` 31 (uncapped ladders 51 in the reported arm).
- Planning MDE (spread slope). Low: `3.47 x 2c / sqrt(605,000) x sqrt(31) x 1.5 x sqrt(1.3) x 2.2` = **0.19c**; high
  **0.10c**; a quarter of the low count 0.37c; all far under 1.0c. F: the twin `dhb_sib` over `(k + 2, k + 3]` (planning
  `r_w` 0.2): 0.30c / 0.16c, **a verdict condition**. The bid-minus-ask slope difference: about 0.27c / 0.15c. Power is
  not the question; the gates are.
- Confounders and the control. The member's own move is part of the event's arithmetic (excluded from the state by
  construction; its own change is a control; VIF against it is the census's number); a common shock that moves all bids
  at once (S26; the lag); ladders whose members are mostly dormant longshots (S27; the per-event SD gate; dormancy of
  CH220's kind is 10.4% of non-sports rows and higher among longshots); the `event` family's visible scores are a
  development look at the *levels* (disclosed; the innovation columns are not built before LT11's freeze); events
  larger than 10 members (the reported arm).
- Most likely boring explanation. The venue's own arbitrage keeps the bid sum so far under one that the headroom never
  closes within a slot (the state is noise around a wide margin: the census's distribution of `hb` says so before any
  test), or the bids that retreat are the farmers' symmetric quotes following the mid, so the spread does not widen,
  it re-centres (M1 moves, the primary does not: a reported two-row table).
- Cheapest census (counts only; the fresh seal; no target read). Neg-risk member rows a capture; complete event-captures
  (kill if < 60% of member rows); events and the cap's loss; the distribution of `hb` (the share of event-captures with
  `hb` within 2 ticks of zero: the state's working range; kill if < 5%); the within-event SD of `dhb_sib` (>= 1 tick in
  >= 50% of events with >= 48 units); the crossing count; |corr| of `z dhb_sib` with the tiers and `VIF_w` against the
  own change; block-gate share >= 50%; pessimistic MDE and F-MDE <= 1.0c.
- Challenger feature: **yes** (CH238 states the columns); the levels already live in `event`; the innovation columns
  are held until LT11's freeze and then carry the `nrslack` token.
- Sports arm: uncounted (sports neg-risk events are the futures ladders: "which team wins the championship").
- Scores: N 4, EV 3, L 4. Parents: CH09 (the asymmetry as a carry), CH12 (dominance pairs), CH159 / CH211 (who re-quoted
  the ladder), CH163 (the ladder's YES premium), E005 and XM1-XM3 (the mid-level record). New: the bid-sum headroom's
  innovation as the state, the spread and bid as targets, the ask-sum shortfall as the twin, the completeness rule.

### C. The dollar weight of a move (parents PX1, PX5, MI4, E015 / CH156, C12, CH193, CH72, CH42; literature: Kyle 1985 on the cost of informed trading, Easley and O'Hara 1987 on trade size, Foucault, Kadan and Kandel 2005)

**CH234. The dollar weight of a move: the trade that moved a price paid the collateral of the side it bought. A move up at
0.90 was bought with 90c a share (YES) or sold by someone holding 90c of inventory; a move down at 0.90 was bought with 10c
a share (NO). The same one-cent move therefore carried nine times the dollars in one direction as in the other, and a
dollar is the cost of being wrong. On every traded mover the weight `w = 0.5 + sign(d) x (p - 0.5)` (the collateral of the
bought side, 0.1 to 0.9) is a continuous state that the champion's momentum (sign and size of `d`) and market state (the
level `p`) hold only as separate main effects; the hypothesis is that continuation at k + 1 rises with `w`, and that it
does not on quote-only movers, where nobody paid anything.**
- Mechanism and why it is non-obvious. Informed traders pay to move prices and uninformed flow is cheap (Kyle 1985);
  on a binary venue the price of a share *is* the collateral, so the dollars behind a move toward the extreme exceed
  the dollars behind the same move toward the centre by the ratio of the two sides. A retail buyer of a 10c longshot
  moves it with pocket money; a buyer of the 90c favourite commits capital. PX1 (longshots drift down over 24 h)
  survived HB1 as a *level* fact; PX5 (1 d momentum continues within 0.10 of 0 / 1) had the same sign and did not
  survive Holm; neither read the move's direction against its level as a dose. Who pays: the maker who re-centres as
  far on a 10c move as on a 90c move (over-reacts to dollar-light flow, under-reacts to dollar-heavy flow); the taker who
  fades a dollar-heavy move. Why the crowd misses it: price-change feeds show cents, not dollars.
- Parent and what is new. PX1 / PX5 / MI4 (HB1: indicator interactions near the extremes, 24 h and 2 h); E015 / CH156
  (the move's anatomy: traded, quote-only, parallel); C12 (move over spread); CH193 (absorbed flow, LT7, closed). New
  here: the continuous dose `w` on every traded mover (no sweep, no sample, no stream), the mechanism (collateral as the
  cost of conviction), the within-market design at E022's design effect with the level drift held as a control, and
  the quote-only twin (the mechanism needs a paid trade).
- Data join and decision clock (`A`, L 5). Unit: non-sports ex-crypto 2 h mover (`|d_k| >= 0.01`, `d_k = mid_k -
  mid_{k-1}`) x capture whose interval was **traded** in E015's sense, read from the sidecar's cumulative `volume_num`
  (`volume_num_k > volume_num_{k-1}`: the whole-panel form round 14's 4.1 names; here a population rule, never the
  tested term, and the fast lane starts after E015's window); the quote-only movers (no volume change) are the twin
  population. State: `w_k = 0.5 + sign(d_k) x (p_{k-1} - 0.5)` (the collateral
  a share of the side whose buying moved the price; equivalently the dollars a share behind the move); its interaction
  with the move's size, `w_k x |d_k|`, is the tested term. Decision time: the row's `received_utc` at k. Controls:
  `|d_k|`, `p_{k-1}` and `sign(d_k) x g(p_{k-1})` with `g` the level drift in four declared price bins (PX1's object,
  absorbed before the state is read), the spread, `log1p liquidity`, `z log rv24`, `volume_num` change (E015's dose),
  tier, hours to end.
- Target and horizon. `c = sign(d_k) x (mid_{k+1} - mid_k)` (continuation in the move's direction; SD 4c; floor 0.5c);
  hypothesis (one-sided): within market-day, the slope of `c` on `z(w x |d|)` > 0 given the controls. M1: `c_skip` (the
  change over `(k + 1, k + 2]`; the lagged-step arm). M2: the same slope on quote-only movers (the twin; the verdict
  condition is traded minus quote-only where its census MDE is under 0.5c). M3 (reported): the slope by the four price
  bins (the dose should hold within bins, not only across them).
- Paper rule and economic check. Maker: re-centre the quote by the full move after a dollar-heavy traded move and by a
  declared fraction after a dollar-light one (gross, no fills; the adverse selection avoided is the continuation of the
  heavy moves). Taker (reported, never a verdict): follow dollar-heavy traded moves of >= 3c to k + 1 against the cost
  model's round trip by tier (3.6c politics; 1.8c at >= 100k); fade dollar-light ones (the same hurdle). Hold-to-
  resolution: the heavy side of a heavy move, held (reported against `res_7d` as a calibration split, engine-first).
- Population arithmetic. 2,750 non-sports movers an interval (P1b); ex-crypto share planning 70-85%; traded share
  30-40% (DESIGN_V1's 30% is all-category): **580-935 traded movers a capture**, 145,500-235,600 in 21 days; `n_eff`
  116,400-188,500. Quote-only twin: about twice that. Events: thousands (movers are spread across the panel); cluster
  = event; `DE_gate` 6.196 (E022's mover family, the 2,539 events in two days E022 counted).
- Permutation and cluster structure. Rule 2 strata (market x UTC day; movers recur within market-day by volatility
  clustering: E022's block2 share 0.599 is the precedent); the Freedman-Lane null (given the market-day, which of its
  traded moves were dollar-heavy does not matter for continuation); binding scenarios: LT5 1-3, L10, **S28: a bounded
  random walk with PX1's level drift and no interaction** (the `sign(d) x g(p)` control must absorb it: the gate must
  return zero on a simulated bounded walk with drift), **S29: continuation that depends on |d| alone** (the |d| control),
  and rule 17's VIF gate against `sign(d) x g(p)`.
- Planning MDE (mid slope, mover family). Low: `3.47 x 4c / sqrt(116,400) x sqrt(6.196) x 1.5 x sqrt(1.3) x 2.2` =
  **0.38c**; high **0.30c**; a quarter of the low count 0.76c. The MDE gate (0.5c) passes at >= about 335 traded movers
  a capture. F: the twin is `w` of the market's move over `(k + 2, k + 3]` (a different mover set; planning `r_w` 0.1):
  F-MDE 0.57c (low; over the cap: a reported label) / 0.45c (high: a verdict condition); F binds at >= about **745
  traded movers a capture** (`n_eff` 150,500). The traded-minus-quote-only difference: about 0.47c (low) / 0.37c (high).
- Confounders and the control. The level drift (PX1; S28; the `sign(d) x g(p)` control, which is `w`'s own shape by
  bin, so the tested term is the *dose within bin* times |d|: the census prints `VIF_w` and the test drops if it exceeds
  2.0); bounded prices (a move toward the extreme has less room: the |d| control and the bins; the S28 world); E015's
  anatomy (the traded class is E015's; the pin before `T_E015` keeps it blind; a later pin is `informed (E015)`); E022's
  traded movers (its window ends 11-16; no overlap in the fast lane; its state is depth against liquidity, not
  collateral); the engine's LightGBM se1 holds mid and the own 2 h change and may have learned the product (a
  development look, disclosed; the attribution limit requested).
- Most likely boring explanation. Within a market-day the level barely moves, so `w` is `sign(d)` times a constant and
  the dose within bin is too thin (the VIF gate kills it before any count); or continuation on traded movers is the
  same at every weight because the venue's informed flow is in the cheap longshot side as often as in the dear
  favourite side (a clean null on a cheap population).
- Cheapest census (counts only; the fresh seal; no target read). Traded and quote-only movers a capture; `w`'s
  within-market-day SD (>= 0.1 in >= 50% of mover market-days with >= 2 traded moves); `VIF_w` of `z(w x |d|)` against
  the controls (<= 2.0); |corr| with the tiers; the block-gate share (market x day strata with >= 2 traded moves) >= 50%;
  events; pessimistic MDE <= 0.5c; F-MDE printed.
- Challenger feature: **yes** (CH235's `tl_w2h`, buildable now from `market_state` and `momentum`; `tl_w_traded` after
  the `movetype` date 11-22); no isolating challenger of the traded x weight interaction before LT11's freeze; token
  `dollarw` if LT11 registers.
- Sports arm: uncounted (game markets move on scores with the same collateral arithmetic; `DE_gate` 3.0 would apply;
  the 5.2c round trip and 1.2c fee are the hurdles; the owner's decision).
- Scores: N 4, EV 3, L 5. Parents: PX1 / PX5 / MI4 (the level and the indicator interactions), E015 / CH156 (anatomy),
  C12 (move over spread), CH193 (absorbed flow), CH72 (the fee's price shape), CH42 (disposition sellers at high prices).
  New: the collateral of the bought side as a continuous dose on every traded mover, with the quote-only twin.

### D. Engine-first families (each with a stated feature definition, clock, expected direction and why the champion or an existing family does not already hold it; each raises K and is built only with a real prior)

**CH235. The collateral tilt (`tilt`): a maker paid per minute or per fill maximises pay per dollar of collateral, so on
every market the cheap side (collateral `min(p, 1 - p)`) is over-supplied and the dear side starved. That makes the venue's
favourite-longshot bias partly mechanical (the cheap bid under a 5c longshot sits deep, the dear ask above it sits thin
and high, the mid is pulled toward the centre), predicts that the bias is larger on rewarded markets than on unrewarded
ones at the same price, and gives the engine four columns the champion holds only as separate main effects.**
- Why engine-first. The level claims (the bias by reward status, the overround of ladders against their rewarded
  longshot share) are maps and `res_7d` calibration splits, not 21-day mid tests (pattern 3); the dated claim is CH234.
- Columns (`A`, L 5; clock: the row's receipt; sidecar fields only). `tl_collat` = `min(p, 1 - p)`; `tl_cheap_side`
  = `sign(p - 0.5)` (which side is cheap: the YES bid below 0.5, the YES ask above); `tl_w2h` = CH234's `w` on movers, NaN
  otherwise; `tl_w_traded` = `w` on traded movers only (**after 2026-11-22**, the `movetype` date); `tl_fee_ps` = the
  schedule's `rate x p x (1 - p)` (the taker's fee a share at the current price; `fees_enabled` 0 gives 0);
  `tl_rebate_ps` = the category's rebate share times `tl_fee_ps` (the maker's rebate a fill); `tl_rew_outside` =
  rewarded x 1[p outside [0.10, 0.90]] (**after 2026-11-18**, the `rewards` date; CH232's level cousin); `tl_spread_collat`
  = spread / `tl_collat` (the half-spread as a return on the cheap side's collateral).
- Expected direction. `dir_2h`: continuation rises with `tl_w2h` (CH234); `res_7d` and calibration: rewarded markets
  priced under 0.10 resolve YES less often than their price says, by more than unrewarded ones (the cheap bid's
  inflation); `tl_fee_ps` moderates momentum (a move at 0.5 in a 0.05 category cost 1.25c a share in fees; one at 0.05
  cost 0.24c).
- Why not already held. `market_state` holds `mid` and the category one-hot; `momentum` the own 2 h change; the logistic
  champion cannot form `sign(d) x (p - 0.5)` or `rate x p(1 - p)`; LightGBM se1 can learn them from the same inputs, which
  is why the family's honest reading is against se1 with the per-family attribution naming the tilt (DESIGN_V1 section
  17) and a logistic isolate `se24_lr_tilt` beside it for the champion's own line. Not in `tte`, `chg1d_x_liq`, `rewards`
  (levels of the programme, not the side), `movetype` (classes, not collateral).
- Embargo: none for `tl_collat`, `tl_cheap_side`, `tl_w2h`, `tl_fee_ps`, `tl_rebate_ps`, `tl_spread_collat`;
  `movetype` (11-22) for `tl_w_traded`; `rewards` (11-18) for `tl_rew_outside`; no isolating challenger of the traded x
  weight term before LT11's freeze (then `dollarw`).
- Map (counts only, no price target): the ladder overround (`event`'s level) against the rewarded share of the ladder's
  members priced under 0.10; the cross-venue gap by price band on E009's sealed stream after 2026-11-03 (Kalshi has the
  same collateral arithmetic and a different maker programme; the gap's sign by band is the tilt theory's cross-venue
  prediction; `informed (E009)` by the record).
- Boring explanation. The bias is the behavioural one the literature already names and is the same on rewarded and
  unrewarded markets; the columns add nothing to se1 beyond what it learned from `mid`.
- Census (counts only): the share of rows with a two-sided quote by price bin and reward status; `tl_w2h` non-NaN
  share (movers); `tl_fee_ps` coverage (the `fee_schedule` presence share).
- Scores: N 3, EV 3, L 5. Parents: CH72 (the fee valley's taker side), CH45 / CH16 (reward geometry), CH163 (the
  ladder's YES premium), PX1. New: collateral as the maker's cost and the mechanical half of the favourite-longshot bias.

**CH236. The predictable demotion (`volage`): the venue's `volume24hr` is a rolling window, so the volume that will leave
it in the next two hours is the volume that entered 24 hours ago, which the host's own `volume_num` series dates to the
slot. The age profile of a market's displayed activity is known one slot ahead: a market whose "hot" number rests on one
print from 23 hours ago is about to look dormant without anything happening, and the champion's `log 24 h volume` cannot
tell it from a market that traded all day.**
- Why engine-first. The object has no sign and its money route is thin (an attention forecast for a maker's fill rate;
  the YES tilt that E017 tested is the directional version and is not re-proposed); the forecast-quality claim is real:
  the engine's activity feature is contaminated by stale prints. Round 13 declined "the volume24hr roll-off as
  yesterday's echo" as a *test* on E015 and CH193 adjacency; this is a column, built after the `movetype` date.
- Columns (`A`, L 4; clock: the row's receipt; 12-slot own look-back, rule 4). From `v_j = volume_num_{k-j+1} -
  volume_num_{k-j}` for `j = 1..12`: `va_ageout` = `v_12 / sum_j v_j` (the share leaving next slot; NaN where the sum
  is 0 or the look-back incomplete), `va_fresh` = `v_1 / sum`, `va_mean_age` = `sum_j j v_j / sum_j v_j` (slots),
  `va_n_active` = the number of the 12 slots with `v_j > 0`, `va_top_share` = `max_j v_j / sum`.
- Expected direction. Magnitude and calibration: at a given `log 24 h volume`, a high `va_ageout` or `va_top_share`
  means the activity was one event, so the next |move| is smaller and the forecast's uncertainty narrower than the
  level implies; `dir_2h`: none; `res_7d`: a label-quality weight (markets whose volume is one stale print are the
  never-traded-again class of CH167).
- Why not already held. `market_state` holds `log 24 h volume` (a level) and `momentum` the own changes; `participation`
  holds the event's 2 h volume change and lifetime volume; `movetype` the 2 h volume change and the traded flag. The
  age profile is a function of twelve lagged volume changes, which no family holds; it is **adjacent to `movetype`**
  (volume changes) and is built **after 2026-11-22** for that reason.
- Boring explanation. Volume is persistent enough that the profile is flat on the markets that matter, and the
  learner's gain is nil.
- Census (counts only): the share of eligible rows with a complete 12-slot look-back and positive own 24 h volume (kill
  if < 15% of non-sports rows); the distribution of `va_ageout` (the share > 0.5).
- Scores: N 2, EV 2, L 4. Parents: CH176 (the front page as a clock), CH193 (absorbed flow), CH24 (category attention),
  CH217 (row quality). New: the forecastable component of the display's activity number.

**CH237. The parent's other children (`parentsib`): the sidecar's v3 `parent_event_ids` nests events under parents (a
contest's state children under its national parent, a season's games under its series). The engine's `event` family stops
at the event; the common factor one level up (the parent's other children moving in the same interval) is a join nobody
has read, cheap to compute from the same capture's rows, and the honest home for the "alone or with the crowd" idea that
LT5 F could not test at a mid target.**
- Why engine-first. LT5 F died on a design effect of 10.3 from family clusters of 465 units at the event level; parent
  clusters are larger still, so no 21-day test is proposed; the engine scores the column against se1 and se10.
- Columns (`A~`, L 4; a reader over `parent_event_ids` and `event_ids`; clock: the latest row's receipt in the capture).
  `ps_has_parent`, `ps_n_child_events` (the parent's event count in the capture), `ps_sib_ev_d2h` (the volume-weighted
  mean own 2 h change of the members of the parent's *other* child events, signed to the market's YES), `ps_sib_ev_abs`
  (the mean |change|), `ps_sib_ev_share_moving` (the share of those members with |change| >= 1c), `ps_parent_vol_chg`
  (the parent's 2 h volume change: **after 2026-11-25**, the `participation` date).
- Expected direction. `dir_2h`: the parent factor's sign (a national swing moves every state child; XM4 tested the
  within-event version of this on non-neg-risk siblings); calibration: the forecast's uncertainty widens when the parent
  is moving.
- Why not already held. `event` holds the event's own siblings; nothing holds the parent; no token covers the parent
  join (`event` was withdrawn 2026-10-22; `participation` covers event volume and liquidity, hence the one deferred
  column).
- Boring explanation. Parents are rare outside the midterm and sports structures (the coverage census says), or the
  parent factor is the category factor the `regime` family already found worthless.
- Census (counts only): rows with a parent (kill if < 5% of non-sports rows); parents and their child counts; the share
  of parent-captures with >= 2 complete children.
- Scores: N 2, EV 2, L 4. Parents: CH184 (alone or with the crowd), CH24 (category attention), XM4, the `event` family.
  New: the parent level as the join.

**CH238. The ladder's headroom columns (`nrslack`): CH233's objects as engine columns, on every neg-risk member row, beside
the levels the `event` family already holds.**
- Columns (`A~`, L 4; the event join; clock: the latest member row's receipt). `nr_headroom` = `1 - sum bid`,
  `nr_shortfall` = `1 - sum ask`, `nr_dheadroom_sib` (CH233's state), `nr_dshortfall_sib` (the twin), `nr_bid_share`
  (the member's bid over the event's bid sum), `nr_fav_d2h` (the favourite's own 2 h change, signed to the member as
  the sum constraint implies), `nr_complete` (rule 16), `nr_is_other` (`neg_risk_other`), `nr_n_members`.
- Expected direction. `dir_2h`: negative on `nr_dheadroom_sib` (the bid retreats; XM3's -0.094c in the predicted
  direction is the mid analogue, not a survivor); `res_7d`: the overround as a calibration correction (the `event`
  family's level, kept).
- Why not already held. `event` holds the overround, the quoted share and the normalisation gap as *levels* and the
  siblings' *Gamma* 1 h / 1 d changes; it holds no bid-sum object and no innovation. Embargo: none today; the innovation
  columns are not built before LT11's freeze and carry `nrslack` if CH233 registers; the levels may be built now as a
  spec version of `event` (K unchanged).
- Scores: N 3, EV 2, L 4. Parents: CH233, CH09, the `event` family, XM3. New: the bid side's arithmetic as columns.

**CH239. The rules' class (`ruleclass`): the `gamma_rules` text covers 44.7% of eligible non-sports markets, and CH228
reads when it last changed. What it *says* is a class the engine can parse once per market and use on the resolution
target: a barrier question ("reach", "at any point", "touch") resolves YES more often than a terminal one at the same
price; an inclusive threshold ("at least", "or more") shifts the strike by a tick; a rule naming several sources resolves
later; a final date in the rules later than `end_date` is a wait the price should carry.**
- Why engine-first. Every object is a level (pattern 3), the coverage is a column's (CH199's lesson), and the targets are
  resolution and calibration, where 21 days give crypto and sports only.
- Columns (`A~`, L 3; a regex parse over the stream's last row before the capture; clock: the stream poll's `recv_utc`;
  pinned by sha256 after the first count). `rc_in_frame`, `rc_barrier` (any-time wording) against `rc_terminal` (on-date
  wording), `rc_threshold` (a parsed number and unit; NaN otherwise), `rc_dir` (above / below), `rc_inclusive`,
  `rc_n_sources` (named sources), `rc_resdate_gap_h` (the rules' final date minus `end_date`, hours), `rc_other_clause`
  (the augmented "Other" wording), `rc_len`.
- Expected direction. `res_7d` and calibration: barrier markets at the same price resolve YES more often (CH118's
  mechanism outside crypto; CB13-R died on basis, not on the class); multi-source rules resolve slower (CH207's
  adjacency); `rc_resdate_gap_h` > 0 markets carry a decided wait (CH01's object as a level).
- Why not already held. `market_state` holds hours to end and the category; CH228's `ruleedit` holds the edit's age,
  `re_text_len`, `re_n_dates` and `re_fallback` (adjacent; the two families share the parse and should be one spec).
  No token covers rule text (CB18-S is closed; `rulesrc` was killed on coverage, not banned).
- Boring explanation. The classes are a category proxy (weather is terminal, politics is occurrence) that the one-hot
  already carries.
- Census (counts only): parse rates per class on the 44.7% (kill a column if < 10% non-NaN of covered rows); audit
  precision on 50 hand-read rules (counts only).
- Scores: N 2, EV 2, L 3. Parents: CH118, CH119, CH63, CH228, CH207, CH01. New: the barrier / terminal / threshold class
  on the whole covered panel as engine columns.

### E. The map and the companion (parents CH232, CH233, CH86, CH224 / LT10, CH166)

**CH240. The boundary map (counts only, k = 0): before any LT11 census, one streaming reader over a fresh ten-day seal
counts, per capture and by category and reward status, the crossings of 0.10 / 0.90 (CH232), of 0.04 / 0.96 (CH86's tick
boundary, for the record), the neg-risk events whose bid sum is within two ticks of one and the headroom crossings
(CH233), and the complete event-captures (rule 16). It is the cheapest census in the programme and decides whether LT11 is
drafted at all.**
- What it counts. Crossings a capture by boundary, direction and panel; re-crossing shares; tick-coincidence; the
  `hb` distribution; complete-event shares by event size; the traded-mover count by price bin (CH234's population);
  nothing read after any origin; no price target. Memory: a per-capture streaming reader, < 300 MB, net lane.
- Why it matters. Round 14's table shows every killer was a count the designer had planned, not measured; this map
  replaces the planning ranges of 0's counts table with measurements before a single design line is written. Kill
  criteria: none (a map); its numbers are the drafts' census thresholds.
- Scores: N 2, EV 3 (as an enabler), L 4.

**CH241. The reverse fine clock: LT10's CH224 tests whether Kalshi's spread innovation leads Polymarket's next spread
change (the hedged Polymarket maker). The same stream carries the reverse: Polymarket's 10-minute spread innovation
against Kalshi's spread change at `t + 20`. The pair of slopes identifies who hedges where (CH166's "the lead is where the
liquidity is" as a *direction*), and a symmetric result is the falsification of the hedge story in favour of the
common-shock world LT10 declares as S22. The money route is the following venue's maker (quote inside after the leading
venue tightens); on Kalshi that is outside the Polymarket remit and the owner's call.**
- Data join and decision clock (`A`, L 4; the fine-clock lane; `informed (LT10, E009, E010)` by construction: a later
  test on the same stream). Unit: pair x 10-minute origin `t` (round 15's rule 12 mirrored: a valid Kalshi quote at `t`
  and `t + 20`, Polymarket lines before `t`). State: `dsP = spreadP_t - spreadP_{t-10}` scaled per pair; controls:
  `dsK` over the same window (CH224's state, as a control), the levels, E009's seven, hour dummies, tier. Target: `dsK'
  = spreadK_{t+20} - spreadK_t` (Kalshi's 20-minute spread change; its SD unprobed; planning 1.0c; Kalshi's tick is 1c
  so the floor is 1.0c). One-sided slope > 0.
- Population arithmetic. LT10's: 200,000-350,000 origins; `n_eff` 160,000-280,000; the CF10 family gate (>= 60 pairs in
  >= 30 events, `G_eff` >= 15) and `DE_gate` 51 apply; planning MDE **0.25c / 0.19c** (a quarter of the low count 0.50c);
  F (`r_w` 0.1) 0.37c / 0.28c: a verdict condition. Honest odds: LT10's family odds (the designer's 0.24 that any LT10
  test registers) bound it; as a companion it runs only if LT10's census passes.
- Money and the owner's call. The route is a Kalshi maker's; AREPO's remit is Polymarket; the entry is kept because the
  *diagnostic* (the asymmetry of the two slopes) is the one reading that tells the hedged-maker story from the common
  shock on the Polymarket side, which no Polymarket-only object can.
- Challenger feature: none for the engine (the engine forecasts Polymarket; `kxbook` covers Kalshi spread changes as
  columns to 12-04 in any case).
- Scores: N 2, EV 2, L 4. Parents: CH224 / LT10, CH166, E009 / E010. New: the direction of the hedge as the object.

---

## 3. Ranked shortlist for LT11, then the engine-first families, then the rest

Rank = census survival (a complete panel, a dense state, an innovation or a crossing, a declared DE, the MDE at the *low*
planning count under the floor, the F-MDE under its cap) x originality x plausibility x money route, with the rules of
round 14's 0.2, round 15's 12-14 and this round's 15-17 as hard constraints. The last column is my prior probability that
the idea passes its own census as written, before any count; a judgement, not a measurement.

| Rank | ID | One line | L | Population arithmetic (source) | Permutation structure | Primary | Planning MDE (quarter); F | Prior odds of surviving census |
|---|---|---|---|---|---|---|---|---|
| 1 | CH234 | The dollar weight of a move: continuation on traded movers rises with the collateral of the bought side | 5 | 580-935 traded movers a capture (P1b 2,750 non-sports x ex-crypto 70-85% x traded 30-40%); 145,500-235,600 in 21 days; DE 6.196 | market x day strata; movers recur (E022's 0.599); FL with S28, S29; the quote-only twin | within market-day, slope of `c` on `z(w x \|d\|)` > 0 given `\|d\|`, `p`, `sign(d) x g(p)` | **0.38c / 0.30c** (quarter 0.76c); F 0.57c label at the low end, verdict at >= 745 a capture | **0.40** (a complete population, no stream, the mover DE; the risks are the VIF against the level-drift control and the F label at the low count) |
| 2 | CH233 | The arb's footprint: the siblings' bid-sum headroom closing widens the member's spread next slot; the ask-sum twin does not | 4 | 3,000-10,000 complete neg-risk member rows a capture in 300-1,200 events (unprobed); 756,000-2,520,000 in 21 days | market x day strata; continuous on every unit; FL with S26, S27; rule 16 | within market-day, slope of `ds` on `z dhb_sib` > 0; verdict on bid minus ask slopes | **0.19c / 0.10c** against 1.0c (quarter 0.37c); F verdict 0.30c / 0.16c | **0.35** (power is not the question; completeness, the working range of `hb` and the VIF against the own move decide; E005's null is on a different object and is disclosed) |
| 3 | CH232 | The cheap side's cliff: an outward crossing of 0.10 / 0.90 on a rewarded market widens the spread from the dear side; the unrewarded crossing does not | 4 | 50-150 crossings a capture (unprobed; fact 4's grid); 10,500-31,500 crossing market-days in 21 days; DE 31 | market x day strata of 12 (rule 2); FL with S25; the inward twin; the control panel | within market-day, E[ds \| xo] - E[ds \| other] > 0 (and < 0 for xi); interaction with the unrewarded panel where affordable | **0.75c / 0.44c** against 1.0c (quarter 1.51c); F 1.19c label at the low end, verdict at >= 60 a capture | **0.25** (the crossing count on the rewarded panel is the whole question; CH240's map answers it before any design) |
| 4 | CH241 | The reverse fine clock: Polymarket's spread innovation and Kalshi's next spread change; who hedges where (Kalshi route; the owner's call) | 4 | LT10's 200,000-350,000 origins; CF10's family gate | pair x day strata of 144; FL with S19, S22 | slope of `dsK'` on `z dsP` > 0 with `dsK` controlled | 0.25c / 0.19c against 1.0c; F verdict | 0.20 (bounded by LT10's family odds) |
| 5 | CH240 | The boundary map (counts only; decides LT11) | 4 | n/a | n/a | n/a | n/a | n/a |
| 6 | CH235 | The collateral tilt (engine-first; `tilt`) | 5 | every row; 2,750 movers a capture | n/a | se1 and a logistic isolate; `res_7d` split by band x reward | engine window | n/a (the `tl_w2h` column needs no census) |
| 7 | CH238 | The ladder's headroom columns (engine-first; `nrslack`) | 4 | neg-risk member rows (unprobed) | n/a | `event` spec version; isolate after LT11's freeze | engine window | n/a (kill if complete rows < 60%) |
| 8 | CH237 | The parent's other children (engine-first; `parentsib`) | 4 | rows with a parent (unprobed) | n/a | against se1 and se10 | engine window | n/a (kill if coverage < 5%) |
| 9 | CH239 | The rules' class (engine-first; `ruleclass`, one spec with `ruleedit`) | 3 | 44.7% of eligible non-sports | n/a | `res_7d` against se1 | engine window | n/a (kill a column under 10% parse) |
| 10 | CH236 | The predictable demotion (engine-first; `volage`, after 11-22) | 4 | rows with 12 slots and own volume (unprobed share) | n/a | magnitude and calibration against se1 | engine window | n/a (kill if coverage < 15%) |

**Top 3 live-test candidates.** CH234 first because it is the one design in the round that clears 0.1's table with
margin at the *low* planning count on a mid target, reads nothing but the rows and the sidecar, and carries its own twin
(the quote-only movers) inside the same population; its honest risk is that within a market-day the collateral weight is
the move's sign times a constant, which the VIF gate will say before any count. CH233 second because power is not in
question and the mechanism predicts a side (the bid), a direction (wider), a twin (the ask sum) and a rare trigger (the
crossing) that one reader counts together; its risk is the working range of the headroom. CH232 third because its count
is the least known thing in the round and the map must measure it first; its mechanism is the most original and its
money route the most concrete. **If the LT11 designer wants k = 3, CH234, CH233 and CH232 are the three (one mover-family
mid slope, one ladder spread slope, one rewarded-panel spread contrast; their dependence is disclosed and Holm handles
it), after CH240's map, with the design text frozen before 2026-11-14T12:00Z for the fast lane.**

**Top 4 engine-first families.** `tilt` (CH235: the strongest prior, PX1 survived and PX5 carried the same sign; one
column buildable today; a logistic isolate beside se1 so the champion's own line is read), `nrslack` (CH238: XM3's sign
on the mid analogue; the levels enter `event` now, the innovations after LT11's freeze), `parentsib` (CH237: a join
nobody has read, one aux table, no token), `ruleclass` (CH239: `res_7d` first, one spec with `ruleedit`). `volage`
(CH236) waits for 11-22 and the builder's judgement on K.

**Pre-registration sketches for the top 3 (written in LT8's and LT10's shape so the designer can lift them; each a
separate primary in one Holm family).**

- **CH234 (the dollar weight of a move).** Unit: non-sports ex-crypto traded 2 h mover x capture (`|d_k| >= 0.01`,
  `volume_num_k > volume_num_{k-1}`); the quote-only movers the twin population. State: `w_k = 0.5 + sign(d_k) x (p_{k-1}
  - 0.5)`; tested term `z(w_k x |d_k|)`. Decision time: the row's `received_utc` at k. Primary: expanding-past
  market-day-demeaned OLS of `c = sign(d_k) x (mid_{k+1} - mid_k)` on the tested term with `|d_k|`, `p_{k-1}`, `sign(d_k)
  x g(p_{k-1})` (four declared bins), spread, `log1p liquidity`, `z log rv24`, the `volume_num` change, tier and hours to
  end as controls; one-sided > 0; material reading top-against-bottom tercile. Targets: `c` at k + 1; M1 `c_skip`; M2
  the quote-only slope (the verdict condition is traded minus quote-only where its census MDE <= 0.5c); M3 by bin.
  Clustering: CR1 on event, two-way event x UTC day and UTC day, p the largest; `DE_gate` 6.196. Planning MDE 0.38c
  (low) / 0.30c (high); F-MDE 0.57c / 0.45c: a reported label at the low planning count, a verdict condition at `n_eff`
  >= 150,500 (declared now). Census (fresh seal 10-28..11-07; counts only): traded movers >= 335 a capture; within-
  market-day SD of `w` >= 0.1 in >= 50% of mover market-days with >= 2 traded moves; `VIF_w` <= 2.0; |corr| <= 0.5 with
  the tiers; block-gate share >= 50%; events >= 500; pessimistic MDE <= 0.5c; F-MDE printed. Verdict condition: as
  declared. Cost hurdle: the taker's follow rule against the cost model's round trip by tier (reported); the maker's
  re-centring rule (gross). Extends: a reader over the rows and sidecar (no sweep). Embargo: `dollarw` new, to the later
  of LT11's analysis commit and the lane's date; an attribution limit on mid x own 2 h change interactions. Disclosure
  at the pin: E015's anatomy is the traded class (blind if pinned before 11-15); LightGBM se1's visible scores are a
  development look at the product.
- **CH233 (the arb's footprint).** Unit: non-sports ex-crypto neg-risk member x capture in a complete event-capture (rule
  16), events capped at 10 eligible members. State: `z dhb_sib` (the siblings' bid-sum innovation, signed so that
  positive closes the headroom), the ask-sum twin `z dha_sib` as a second regressor. Decision time: the latest member
  row's receipt at k. Primary: expanding-past market-day-demeaned OLS of `ds = spread_{k+1} - spread_k` on both with
  `hb_{k-1}`, the own 2 h change, the spread level, the bid share, `log1p liquidity`, event size, `neg_risk_other` and
  tier as controls; one-sided > 0 on the bid term; the verdict condition is bid minus ask where its census MDE <= 1.0c.
  Targets: `ds`; M1 the bid's change (< 0); M2 the mid's change (E005's object; reported); M3 the headroom crossing
  class. Clustering as CH234; `DE_gate` 31 (51 for the uncapped reported arm). Planning MDE 0.19c / 0.10c against 1.0c;
  F-MDE 0.30c / 0.16c: a verdict condition. Census: complete member rows >= 60%; `hb` within 2 ticks of zero on >= 5% of
  event-captures; within-event SD of `dhb_sib` >= 1 tick in >= 50% of events with >= 48 units; `VIF_w` <= 2.0 against the
  own change; |corr| with the tiers <= 0.5; block-gate share >= 50%; events >= 500; pessimistic MDE and F-MDE <= 1.0c.
  Cost hurdle: the maker's pulled bid against the reward minute lost on one side (gross). Extends: an event-join reader
  over the rows. Embargo: `nrslack` new; no isolating challenger of the innovation columns before the freeze; the
  `event` family's levels disclosed as a visible development look.
- **CH232 (the cheap side's cliff).** Unit: rewarded (13.7's carry; the feed adjudicates) non-sports ex-crypto market x
  capture on a market-day with a first crossing of 0.10 or 0.90 between k - 1 and k; all 12 slots. State: `xo_k`, `xi_k`;
  `dear_side`; `recross` (a reported class); tick-coincident crossings excluded and counted. Decision time: the row's
  receipt at k. Primary: expanding-past market-day-demeaned OLS of `ds = spread_{k+1} - spread_k` on `xo` and `xi` with
  the mid at k - 1 and k, the own change and |change|, the spread level, `log1p liquidity`, `v`, tier and `neg_risk` as
  controls; one-sided (> 0 on `xo`, < 0 on `xi`) under the pin's recorded reading of the rule; the unrewarded-panel
  interaction the verdict condition where its census MDE <= 1.0c, else a reported arm. Targets: `ds`; M1 the dear side's
  touch change; M2 the mid toward the band (reported); M3 the sealed sweeps' side depths (reported). Clustering as
  CH234; `DE_gate` 31. Planning MDE 0.75c / 0.44c against 1.0c; F-MDE 1.19c / 0.69c: a label at the low planning count, a
  verdict condition at >= 60 crossings a capture (declared now). Census: crossings >= 24 a capture on the rewarded
  panel; re-crossing share <= 60%; tick coincidence printed; block-gate share >= 50%; cap share >= 40%; events >= 500;
  |corr| and `VIF_w`; pessimistic MDE <= 1.0c; F-MDE printed; the venue page's reading recorded. Cost hurdle: the
  reward minute lost on one side for one slot against the retreat avoided (gross; the formula's one-sided share where
  the reading scores it). Extends: a crossing reader over the rows and the sidecar; the sealed sweeps for M3 only.
  Embargo: `bandside` new; the `rewards` family's band columns after 11-18 only.

**How the families would be registered.**
- **LT11 (CH234, CH233, CH232).** One Holm family, k <= 3, on the captures and sidecar; CH240's map first; the fast lane
  (window 11-18..12-09, pin before 11-14T12:00Z, census on a fresh seal 10-28..11-07) or the ordered lane after LT9;
  tokens `dollarw`, `nrslack`, `bandside` filed at the freeze; the three engine-first column sets built only as levels or
  after the freeze, as each entry states.
- **The companion (CH241).** A later test on LT10's stream, only if LT10's family census passes, `informed (LT10)`, with
  the owner's call on a Kalshi route.
- **Engine-first (CH235-CH239).** Development families under the builder's rules, in the order of the top-4 list; `tilt`
  may start today with its unembargoed columns; `volage` after 11-22.

**What is honest to say about all of them.** Fifteen rounds have read the venue's prices, books, volumes, rewards, rules
and other venues' feeds, and most of what a 2-hourly capture can date has a parent. What this round adds is one fact
about the venue that turns several known levels into dated, side-specific events: a quote's cost is the collateral of its
side, the published rules change what a paid maker must post at known prices, a ladder's arbitrage hits one side of the
book, and a move's dollars depend on which way it went. Each of the three live candidates is built to the table of 0.1
rather than to a mechanism's charm, and the table says the spread is the target a dense discontinuity can afford and the
mover family is the population a mid test can. Nothing here is edge until it has gone through the map, a census, frozen
rules, prospective registration and an economic check at recorded prices; and the first thing that will say whether any
of it is worth a design is CH240's count of crossings, headroom and complete ladders on ten sealed days.

---

## 4. Ideas considered and rejected, and why

### 4.0 Dropped as duplicates or closed (this round's own candidates, each with the record that closes it)

| Candidate this round | Why dropped | The record |
|---|---|---|
| The tick-regime crossing at 0.04 / 0.96 as a spread-target test (the book thins at a known trigger; the mirror of CH232 on the grid rule) | owned | CH86 (tick-change vacuums) states the mechanism and the re-quote route; CH15 the discount; round 14's 4.1 lists the crossing as a rare event; CH240 counts it for the record and CH232 excludes tick-coincident crossings |
| The laggard catch-up in a neg-risk ladder (the non-mover's mid drifts to the siblings' implied value) and the slow sibling on Polymarket's own ladders | closed | round 13's section 4 ("the ladder lead-lag nulls L1-L4, XM1-XM6, E005 not supported, the engine's `event` family"); CH225 is the sports version with the book's joint move as the instrument; CH233 reads the bid side's arithmetic and a spread, not the catch-up |
| The event-level flinch with a spread target (the non-mover's makers widen when siblings move) | money story fails | if the catch-up is null (the record), there is nothing for the widening to protect against; the only version with a mechanism is CH233's (the arbitrage) |
| The sum-breaking move (a member's own move split by whether its siblings offset it) | informed, owned | E005's band deviation; the `event` family's normalisation gap and siblings' changes (visible); HB1 XM3; a LightGBM already holds the pieces |
| The maker-rebate valley (the rebate a fill, `share x rate x p(1 - p)`, flips the maker's fill economics at mid prices) | a level | pattern 3; a column of `tilt` (`tl_rebate_ps`); CH52 / CH53 own the fee history |
| The fee a share the mover paid (`rate x p(1 - p)` at the pre-move price) as a mover state | a level trait of price and category | within market it varies only with `p`; a column of `tilt` (`tl_fee_ps`); CH72 owns the taker's fee valley |
| Holding rewards (4% annualised on eligible markets) as a subsidy to the dear side | collection | `holdingRewardsEnabled` is not a sidecar column (the column list in `ext_sidecar.py`); CH21 owns the speculative version; no collection change proposed |
| The volume24hr roll-off as a test | rejected before | round 13's section 4 ("yesterday's echo"); CH236 is the column, after the `movetype` date |
| The front-page or top-3,000 crossing by 24 h volume | duplicate | CH176; round 15's 4.0 |
| Open-interest innovations (mint, merge, exit) | rejected before | round 14's 4.1 (ambiguous sign); CH150 / CH145 not re-proposed |
| `event_comment_count`, `competitive`, `updated_at` | rejected before | round 13's section 4; `participation` to 11-25 |
| The 0.5 crossing (the cheap side flips) | no discontinuity | the collateral is continuous in `p` and equal at 0.5; only the published rule creates a jump (CH232) |
| The display's rounding step at 0.001 ticks as a retail trigger | unverified display rule; rare | CH37 / CH218 own display triggers; not proposed |
| PredictIt's linked-market sum arbitrage; Smarkets' lay side as the cheap side | frame | CB15-P (37 pairs in 12 events); round 15's 0.1 arithmetic; CH229 / CH230 |
| The dollar weight at the fine clock on E009's pairs | a replication lane, not an idea | the same state on 70-116 pairs after LT10; noted in CH234, not proposed |
| A sports-only dollar-weight test | the owner's parameter | CH234's sports arm is reported uncounted; CH205 / CH225 hold the sports family |
| The resolution-lag map by `end_date` hour for non-sports (CH226's twin) | no price-free decided label; a forbidden-parse field | CH01's problem; `uma_resolution_statuses` awaits CH221's ruling |
| The reward epoch, weekends, the daily payout, farmers' midnight re-allocation | venue clocks | round 13's rule 8; round 14's 4.1 |
| Any sweep, sidecar, rewarded-panel or fine-clock state under a new name that LT8, LT9 or LT10 tests | owned | CH202-CH204, CH212-CH215, CH222-CH224 and their tokens `quietbook`, `swclock`, `bandbreak`, `pool`, `rwblink`, `kxbook`; nothing here reads them |
| Anything wallet-level | sealed / frozen | E026 registered, its modules frozen to 12-07 |

### 4.1 Ideas rejected on the design rules, and why

- **Any whole-panel class state on a mid target with fewer than about 700 units a capture in its smaller class, or any
  whole-panel mid slope under about 1,700 units a capture** (0.1's table): the crossing ideas on a mid target (CH232's
  M2 is reported for that reason), the headroom crossing as a mid primary, the parent factor as a test.
- **Level states as primaries** (the collateral tilt, the rebate valley, the fee a share, the rules' class, the
  overround): pattern 3; each is an engine column or a map here.
- **Rare-event states** (the headroom crossing alone, tick-regime crossings, `accepting_orders` flips, holding-reward
  flags, rule edits): pattern 1; CH233 keeps the crossing as M3 only; CH240 counts the rest.
- **Mover states that are the move's sign times a constant** (rule 17): CH234's VIF gate is the kill line it declares.
- **Event joins without completeness** (rule 16): a bid sum over a partial ladder is a different number at every capture;
  incomplete event-captures are `unavailable`, never filled.
- **E015, E022, LT8, LT9 and LT10 moderators during their windows.** Double counts on overlapping origins; the fast lane
  is defined to avoid them and the pins before `T_E015` and `T_E022` keep CH234 and CH232 blind.
- **Taker routes as primaries anywhere.** 2.9-7.2c hurdles against grosses of a fraction of a cent; every taker route
  here is reported, never a verdict.
- **Maker mark-out objects** (adverse selection judged on fills). J4-R's and CB13-T's holdouts; E025 part B; every maker
  route here is gross, no fills, with the reward formula's arithmetic as the economic check where the market is rewarded.
- **Kalshi-target money as a programme objective.** CH241 is kept as a diagnostic companion with the owner's call named;
  no Polymarket claim rests on it.
- **Decided-but-unresolved carry, longshot ask-selling, round-number walls, tick-regime discounts, reward cliffs,
  holding rewards, genesis, seed anchors, series rolls and base rates, mention baskets, external anchors, barrier
  confusion, quoter grain, wake-up prints, breathing book, mint share, turnover, synchronous prints, exit pressure, cost
  maps, quoted against traded, walked flow, trains, attention surges, breadth, class-conditioned longshots, arrivals and
  cancellations, the age of the move, opens and closes, concentration, hollow liquidity, program against human, last-mid
  proxy, front page, silent edits, races, jump or grind, high-water mark, overhang, alone or with the crowd, the farmer's
  choice, clips, the makers' vote, deadline moves, sibling birth, provenance, overdue, grind at the capture clock, the
  hour-held move, implied against realised, absorbed flow, resistance, patient money, the last-print anchor, calendar
  theta, the resolution-source class, two minutes of quote news, reward yield, the sweep clock, the quiet book, the
  market's own clock, steam, the reward start, desk-set dispute insurance, the minute of the news, the farmer touch, two
  minutes before the origin, the ladder that travelled, the display's omission, the band break, the pool splits, the
  scheduled end, large prints without a sample, row quality, the display's disagreement, the touched book, dormancy, the
  siblings' proposal window, the venue that traded first, the other venue's makers flinch first, the hedged maker's
  price, the slow sibling, the resolver's clock, the entity clock, rule freshness, the published close, the three-venue
  panel, the in-game state.** CH01-CH231: not re-proposed; where an idea touches one, the parent is named and the new
  clock, population, state or join is stated (CH232 on CH71/CH45/CH16/CH19/CH213/CH72/CH116; CH233 on
  CH09/CH12/CH159/CH163/CH211/E005/XM1-XM3; CH234 on PX1/PX5/MI4/E015/CH156/C12/CH193/CH72/CH42; CH235 on
  CH72/CH45/CH16/CH163/PX1; CH236 on CH176/CH193/CH24/CH217; CH237 on CH184/CH24/XM4; CH238 on CH233/CH09/XM3; CH239 on
  CH118/CH119/CH63/CH228/CH207/CH01; CH240 on CH232/CH233/CH86; CH241 on CH224/CH166/E009/E010).

---

## 5. Sources consulted

### 5.1 No host probe, no network, no data-dumps read this round (by instruction); what was read instead
`EXPERIMENT_LEDGER.md` (the tail from the LT8 code merge of 10-22 ~22:20Z to the CC8 entry of 10-23 06:03Z: LT9's draft,
reviews and design-text freeze, the LT7 withdrawals and LT9 round-6 tokens, the `dispgap` / `dormant` builds and
censuses, LT9's census code phase 1, LT10's draft, R1, re-check, freeze and round-7 tokens, the CC8 drop of CH204; the
E005 registry row and its results line; the E004 / E005 / E006 results header); `signal_engine/STATUS.md` (10-23 04:05
UTC+1: the feed, the embargo table, K, the leaderboard, the queue); `signal_engine/NORTH_STAR.md`;
`signal_engine/CANDIDATES.md` (rounds 1-7 of embargo requests and replies, the 10-22 and 10-23 notes, the idea-level
notes for rounds 12-15, the "not candidates" list, the builder table rows 1-23); `signal_engine/DESIGN_V1.md` section 3
(families, columns, clocks and coverage) and the section headings; `LIVE_TESTS_8.md` section 7 (the census gates as
frozen); `LIVE_TESTS_10.md` sections 5 and 7 (deferred ideas; the CF10 / CK10 / CD10 gates); `HYPOTHESIS_BATTERY_1.md`
(the id table rows MI1-MI10, XM1-XM6, PX1-PX6, LQ1-LQ3 and the results rows for MI4, XM1-XM3, PX1, PX5, LQ2);
`EXECUTION_COSTS.md` (the formula sources, the cost distribution by price band, liquidity and category);
`COST_MODEL.md` section 2 (fees, rebates, the two-sided rule as quoted, the history); `MAKER_REWARDS_STUDY.md`'s rule row
and the fill-weighted mark-out line; `backend/astrolabe/research_lab/extract.py` (the row fields: `best_bid`, `best_ask`,
`spread`, `last_trade_price`, `neg_risk`, `neg_risk_market_id`, `neg_risk_other`, `event_neg_risk_augmented`) and
`ext_sidecar.py` (the sidecar columns, `parent_event_ids`, `fee_schedule`, `order_price_min_tick_size`);
`CREATIVE_HYPOTHESES_2026-10-29.md` (round 15 in full: the brief, 0.1-0.2, the facts, CH222-CH231, the shortlist, 4.0-4.1,
5); `CREATIVE_HYPOTHESES_2026-10-28.md` (round 14's 0.1 table, 0.2 rules, facts, 4.1); `-27.md` (round 13's section 4);
`-26.md` (round 12's section 4); the lead paragraphs of CH09, CH12, CH13, CH15, CH19, CH24, CH45, CH46, CH71 (and its test
block), CH72, CH86, CH115, CH145, CH150, CH159, CH163, CH167, CH176, CH193, CH211, CH221, and the lead sentences of
CH01-CH231 from all fifteen rounds (for the duplicates table). Still no host probe, no network and no data-dumps read.
Every count is as the named document states it on 2026-10-23; nothing was recomputed.

### 5.2 External literature (named, not fetched)
Foucault, Kadan and Kandel 2005 (the cost of a resting limit order and the maker's choice of side); Glosten and Milgrom
1985 (the maker's update on trades); Kyle 1985 (the cost of informed trading); Easley and O'Hara 1987 (trade size and
information); Hasbrouck 1991 (the information content of trades, as round 15 cited it); the conversion mechanics of
neg-risk events as CH09 states them from the venue's documentation.
