# Creative hypotheses, round 17: the mirror, the fee, the farmed half and the third outcome (2026-10-31)

`evidence_role: none` | status: **IDEAS ONLY, nothing tested, nothing registered.** No edge, calibration, tradability or
profitability claim. AREPO never trades; every "money route" below is a paper rule to be tested on historical data and
then prospectively. Written by the creative-lead pass at the user's request (written 2026-10-23 from 12:50Z on parent
`16b294ae` (`chore/arepo-claude-setup`) in the worktree `feat/creative-r17`; the file carries the round's planned date as
earlier rounds did). Round 1 is `CREATIVE_HYPOTHESES_2026-10-15.md` (CH01-CH34), round 2 `-16.md` (CH35-CH59),
round 3 `-17.md` (CH60-CH78), round 4 `-18.md` (CH79-CH98), round 5 `-19.md` (CH99-CH117), round 6 `-20.md` (CH118-CH130),
round 7 `-21.md` (CH131-CH143), round 8 `-22.md` (CH144-CH155), round 9 `-23.md` (CH156-CH168), round 10 `-24.md`
(CH169-CH179), round 11 `-25.md` (CH180-CH190), round 12 `-26.md` (CH191-CH201), round 13 `-27.md` (CH202-CH211), round 14
`-28.md` (CH212-CH221), round 15 `-29.md` (CH222-CH231), round 16 `-30.md` (CH232-CH241); this file starts at **CH242** and
repeats none of them. Where an idea builds on an earlier one, the parent is named and the new mechanism, clock,
population or join is stated. Every number quoted from an AREPO document is a development, census, map or probe result,
not evidence. One file; no code, no queue specs, no other commits. **No network request, no host probe (no `ssh oracle`)
and no `data-dumps` read were used for this round** (by instruction); every count below is taken from a named AREPO
document (`EXPERIMENT_LEDGER.md`'s tail of 2026-10-22/23 through the LT11 draft entry, `CH240_MAP_2026-10-23.md`,
`LIVE_TESTS_11.md` sections 0 and 7, `signal_engine/STATUS.md` (10-23 13:10 UTC+1), `signal_engine/NORTH_STAR.md`,
`signal_engine/CANDIDATES.md` (the round 12-16 notes, the "not candidates" list, the builder table rows 1-23),
`EXECUTION_COSTS.md`, `COST_MODEL.md` section 2, `NEW_STREAMS_2026-10-19.md` sections 1-2, round 16's sections 0-5, round
15's 0.2 and round 14's 0.2, `LIVE_TESTS_11.md` section 13 read-only in the LT11 worktree, and the `parse_outcome` and
sidecar column code) and is named as such. Where no count exists the entry is marked **unprobed** and the
pre-registration census is the first gate.

## 0. How to read this file

**The brief that binds this round (owner priorities 2026-10-19 and 10-21; orchestrator brief for round 17).** Original
hypotheses about how money could be made lead the programme, and the programme's dominant failure mode is still the
pre-registration census: LT5, LT6, LT7 and now **LT8 closed with zero tests** (CC8 dropped CH204 on 2026-10-23 06:03Z;
CS8 dropped CH203 on units and CH202 on the held share at 07:41Z), and the recorded killers are too few units a capture,
too few distinct events, a held or scheduled share under its line, the block-gate share and an MDE above the floor. So
this round is **census-first** as round 16 was: every live-test idea states, from a named count or marked unprobed, its
expected units a capture and distinct events over 21 days, the binding MDE and an honest survival prior; anything that
cannot plausibly clear about 2,000 units a capture and 500 events on a mid target (about 260 with F on a spread target)
is engine-first, said so in its entry. It also feeds the signal engine (NORTH_STAR: champion = momentum + market state;
challengers add one family each; scored at every capture) with families defined on streams the engine already reads.
Round 14's design rules 1-11, round 15's 12-14 and round 16's 15-17 **bind here unchanged**; this round adds three
(0.2). Category-agnostic, sports as a parameter (the owner's call). No data-rights topic is raised. Nothing here reads
any registered live test's objects before its analysis; nothing here reads LT11's window captures for any census.

**What this round does differently from round 16.** Round 16 mined one fact (a quote's cost is the collateral of its
side) into three live candidates that the CH240 map then counted and an LT11 draft took up. This round looks for
mechanisms in five places the sixteen rounds have walked past: **the same claim quoted in two books** (the two members
of a two-member neg-risk event are one question priced twice, with separate makers and a conversion link; duplicates
and complements across events are the same thing without the link); **the fee as the price of urgency** (a taker pays
`rate x p(1 - p)` only when crossing, a maker never, so in fee markets crossing is a costly signal and in the fee-free
remainder it is not); **the farmed half of a ladder** (the reward programme is per market, so a ladder can have paid
makers on some members and none on the others, and the sum constraint links them); **the venue's third price** (a
market can resolve 50-50, so the cheap side of an ambiguous question is a straddle on ambiguity that its sellers price
as a probability); and **who pays the maker** (the taker's fee, the venue's reward, both or neither, which fixes the
maker's reaction to a print before any print happens). Each gives a dated, side-specific or class-specific prediction;
none is momentum, reversal or imbalance under a new name.

**What changed since round 16 (from the ledger's 10-23 ~03:05Z to the LT11 draft entry, STATUS 10-23 13:10 UTC+1,
CANDIDATES' round-16 note, `CH240_MAP_2026-10-23.md`, `LIVE_TESTS_11.md`).**
- **LT8 is CLOSED with no test.** CC8 (q0622): CH204 3.35 scheduled markets a capture (< 1,200), hot units 6.3, events
  119.7, cap share 0.20, block-gate share 0.33, class MDE not finite. CS8 (q0623): CH203 projected primary units
  431,399 (< 504,000) and quiet covered units 1,763,361 (< 2,520,000), every other gate passed including both MDEs;
  CH202 held share 0.067 (< 0.15), every other gate passed, class MDE 0.44c. Tokens `sched`, `quietbook`, `swclock`
  and `attrlimit_lt8` withdrawn (07:30Z, 08:00Z); `book` / `book0` stay at 2027-02-14 for LT9. LT9's lane: `REGISTERED_UTC`
  never before 2026-12-30T00:00Z. Retention back to 8 days.
- **LT9's census code phase 1 is merged** (9e482fab; CR9 / CC9 / CS9; drafts q0640-q0647 unpromoted; seal waits for
  11-02..11-12). **LT10's code is merged** (code-freeze check, re-check, final verification; drafts q0660-q0667; the
  registered size check q0665 not before 11-04; census only after both E009's and E010's analysis commits on 11-03).
- **The CH240 map ran (q0680, 08:33Z; 83 captures 10-16..10-22; counts only, k = 0):** non-sports ex-crypto per
  capture: traded movers about **1,239** (round 16 planned 580-935), quote-only 2,466, **851 movers with `volume_num`
  missing (83% of sidecar rows have no `volume_num`)**; complete neg-risk event-captures about **1,833** (2 members
  complete 1.00 / 0.97; 3-5 0.85 / 0.65; 6-10 0.88 / 0.67; 11+ 0.30 / 0.14), neg-risk events 1,664 rewarded / 825
  unrewarded with 14,123 / 4,933 member rows, `hb` within 2 ticks of zero on 12.6%; rewarded outward first crossings of
  0.10 / 0.90 about **79** (73 ex-tick), re-crossing share 0.59 at 0.10.
- **LT11 is DRAFTED and reviewed** (`feat/live-tests-11`; the draft ea67cd56 at this worktree's parent; DRAFT, not
  frozen): CH234 (traded-mover continuation on `z(w) x z(|d|)`, `volume_num` missing a counted third class, F binding),
  CH233 (member's next spread on the siblings' bid-sum rise, 3-10 members, ask twin point condition, **2-member and 11+
  events reported arms**), CH232 (rewarded first outward crossings from the causal approach zone `[0.10, 0.14]` /
  `[0.86, 0.90]`). One Holm family, k <= 3; fast lane window 11-18..12-09, analysis on or after 12-10T12:00Z, freeze
  before 11-14T12:00Z and `T_E015`; census seal `[10-28, 11-07)`. The draft's census odds were CH234 0.35, CH233 0.50,
  CH232 0.20 (P(no test) about 0.26); **the challenger's R1 (REVISE, 8 must-fix, 10 should-fix) and its re-check
  (ACCEPT_WITH_FIXES) have since been applied in the LT11 worktree** (read-only here; section 13 of that file): receipt-span,
  F-arm coverage and `G_eff >= 15` gates added, the distinct-event gates unprojected, CH232's count gate raised from 60 to
  67 a capture, and the odds revised to CH234 0.35, CH233 0.40, CH232 0.10, **P(no test) about 0.35**, expected valid
  verdicts about 0.3. Tokens `dollarw`, `nrslack`, `bandside`, `attrlimit_lt11` at the freeze. No LT11 result can satisfy
  the economic check (every maker route gross, every taker cell expected "not shown").
- **The engine:** K = 7 (se21 `hwm`, se22 `dispgap` and se23 `dormant` fit first at the 10-23 refit; se22 / se23 hidden
  to 11-14 / 11-19); champion `se0_champion_lr_mm`; the two-day leaderboard shows the LightGBM challengers about +0.05
  nats over the logistic champion (a learner effect; no promotion before about 11-04); the feed `se-feed-v1` is live on
  /lab; the owner's Lab-board message was answered by eight ntfy pushes. The embargo table (xvenue 11-04; tte and
  dispgap 11-14; flow 11-16; rewards 11-18; surprise and dormant 11-19; movetype 11-22; participation 11-25; wallet
  12-07; kxbook 12-04; book / book0, bandbreak, pool, rwblink 2027-02-14) binds every family below. The builder asks
  for families with a real prior only, since each raises K; `resist` (CH195) is named the most plausible of the freed
  LT7 families.
- **Ops:** q0164c (CB8 exclusion keys; the scratch file left out of the disk budget) and q0116i (MC1 dev run; resume
  identity without the repo-wide `code_sha`) replaced q0164b and q0116h; nothing counted. E022 registered (window
  10-26..11-16); E026's modules frozen to 12-07; E009 / E010's `cross_venue_live/` sealed to 11-03; E011's to 11-10.

### 0.1 The census arithmetic, stated once: what a live test needs per capture

Round 16's 0.1 table binds unchanged (the effective count at which the pessimistic MDE equals the floor, and the units
a capture it implies over 21 days, 252 captures, at the planning effective share 0.8): a 2 h mid class contrast needs
about 690 units a capture in the smaller class (1,740 with F); a whole-panel mid slope about 1,680 (4,200 with F); a
mover-family mid slope at E022's design effect 335 (745 with F); a spread slope about 105 (260 with F); a 1 : 11 spread
class contrast about 24 event market-days a capture (60 with F). Two readings steered round 16 and steer this one: **the
spread is the cheapest honest target by an order of magnitude**, and **a mover family needs one fifth of the units a
whole-panel slope needs.** This round adds one: **a state defined on the twin of the same claim (two books, one
question) has its stratum by construction (event x UTC day, 24 units for a two-member event), its own-book innovation as
the natural control, and the conversion link as the mechanism**, so it is the one new object this round can put on a
spread target at a count the host already bounds (the neg-risk event counts of the CH240 map), and the single live
candidate here that clears the table with margin at the high planning count (CH245). The LT11 draft's census formula
(`DE_gate = max(floor, 1 + (m_21 - 1) x 0.02)`, `m_21` the projected size-weighted mean cluster size by event) gives a
two-member event a design effect near 11 against the planning convention 31, so every MDE below for CH245 is quoted at
both.

### 0.2 Design rules (round 14's 1-11, round 15's 12-14 and round 16's 15-17 bind unchanged; three additions)

18. **The mirror rule (twin-difference states).** A state built from the other book of the *same claim* (the second
    member of a two-member neg-risk event; a duplicate standalone and its member; a complement pair) is defined only on
    capture pairs in which both books are two-sided at k - 1 and k (rule 16 applied to a pair); the tested term is the
    *innovation* of the twin's quantity over (k - 1, k], the *level* of the twin gap and the own-book innovation are
    controls, so the twin must add to what the own book already says; the stratum is event x UTC day; the declared
    placebo is an unrelated pair's innovation at the same slot (the S-world "any innovation anywhere predicts the
    spread"), which must be null in the census-fixed stratum.
19. **The venue's third price.** A resolution may be read as three-valued (1, 0, 0.5) only by engine-first `res_7d`
    features and by counts-only maps; no live primary reads a resolution; a 50-50 resolution is a counted class, never
    folded into YES or NO, and its *rate by rule class* is a map before any feature is built on it.
20. **Fee class is a panel, never a state.** The taker fee rate is a market-level constant (sidecar `fee_schedule`,
    `fees_enabled`; the documented category rates as the fallback); it defines contrast panels, as the unrewarded panel
    does in CH232, never a within-market state; a panel contrast's inference is cluster-robust across events (the
    within-market Freedman-Lane null tests only the within-market term), and its planning MDE is quoted as the class
    contrast of two within-market slopes.

**Hygiene that binds every idea** (round 14's paragraph applies: decision time is the latest input's own receipt;
targets start after it; nothing reads outcome fields except engine-first `res_7d` features; the primary is a
within-stratum contrast or slope by expanding-past demeaned OLS, the Freedman-Lane gate in the census-fixed stratum is
binding, the liquidity-tier correlation gate (|corr| <= 0.5 within and pooled against `log1p liquidity` and `z log rv24`)
and the AR(0.9) scenarios bind, and F in LT7's one-rule form is a verdict condition where its census F-MDE is under the
target's floor). Sports stays a parameter (the sidecar's `fee_type` plus CB17's frozen list); every non-sports entry
reports its sports arm uncounted. Nothing here is a maker mark-out object; J4-R's and CB13-T's holdouts are not read.
Nothing here reads LT11's objects (`xw`, `cl_sib`, `xo`, their twins or targets) or LT11's window captures.

**Scores.** N novelty (1-5), EV expected value if true (1-5), **L live-ready (1-5):** 5 = a pure reader over the rows or
sidecar the host already writes with the population counted by a named probe or map; 4 = pure reader, population
bounded above by a named count; 3 = pure reader with an unprobed population, or a matcher or map first; 2 = a stream
whose coverage is unprobed, or a collection change; 1 = fetches or weeks. My judgement, not measurements.

**Planning-MDE arithmetic (round 14's, stated once).** Class contrast: `MDE = 3.47 x SD x sqrt(1/n1_eff + 1/n2_eff) x
sqrt(DE_gate) x 1.5 x sqrt(max(1, VIF_w))`; slope per SD of a continuous state times the tercile gap (about 2.2 SD):
`MDE = 3.47 x SD / sqrt(n_eff) x sqrt(DE_gate) x 1.5 x sqrt(VIF_w) x gap`. `n_eff` = 80% of raw (planning). `DE_gate`: 31
(events capped at <= 10 members), 51 (uncapped; the fine-clock lane), 6.196 (mover families), 3.0 (one game one
cluster), and the LT11 formula's value where the cluster is a two-member event (about 11; floor 5.0). `VIF_w` 1.3 for
row and sidecar states, 1.5 for book states. SDs: 2 h change 4c; |2 h move| 3c; spread change 2c. **F-MDE** = `MDE x
sqrt(2 / (1 - max(0, r_w)))`, capped at the floor as a verdict condition. Every MDE is quoted at the low and high
planning counts and at a quarter of the low one.

**Structural facts this round relies on (counts only; sources named; no new probe).**
1. Eligible markets a capture 42,161-51,790 (DESIGN_V1 sections 3 and 16, as rounds 13-16 quoted); non-sports about
   30,000 (derived); eligible non-sports on the 10-21 22:31Z capture 18,232 (CH199's narrower filter).
2. **The CH240 map (q0680, 10-16..10-22, non-sports ex-crypto, per capture):** neg-risk events 1,664 rewarded / 825
   unrewarded; member rows 14,123 / 4,933 (so about 8.5 / 6.0 members an event on average); complete event-captures
   about 1,833, complete (k - 1, k) pairs 1,262 / 563; completeness by event size as 0 states it (2-member events
   1.00 / 0.97); traded movers 1,239 (rewarded 1,021 / unrewarded 218), quote-only 2,466, `volume_num`-unusable 851.
   **The number of two-member events, the number of ladders with mixed reward status among their members, the number
   of duplicate or complement pairs across events and the fee-rate split of traded movers are all unprobed** (the map
   did not split by these).
3. **The reward probe (q0601c; round 14 fact 2):** rewarded non-sports ex-crypto market-captures about 9,000-10,700 a
   capture; the field omitted on 62.2% of rows; switching markets 2,112-3,995 a day. The reward rule as AREPO's
   documents record it (round 16 fact 2, both readings; the pin re-reads the page) and the programme is **per market**
   (`clob_rewards` on the sidecar row; `reward_params` per market on the CLOB feed), not per event.
4. **Fees and rebates (`COST_MODEL.md` section 2, quoting the venue's pages, retrieved 2026-10-19):** taker fee
   `rate x p x (1 - p)`, takers only (politics, finance, tech, mentions 0.04; sports, economics, culture, weather, other
   0.05; crypto 0.07; **geopolitics 0**; some sports 0.03); "makers are never charged fees"; maker rebates funded by the
   market's taker fees at 25% (other), 15% (sports), 20% (crypto) of the fee-equivalent, paid daily; no taker fees
   before 2026-01-05, crypto only to 03-06, all categories except geopolitics for markets deployed on or after
   2026-03-30 (so **markets deployed before 03-30 and still open are fee-free**: the "fee-free remainder", unprobed);
   per-market `fee_schedule` and `fees_enabled` on the sidecar (`EXECUTION_COSTS.md`: 30,503 sports rows of 248,235 at
   0.03; `feesEnabled = 0` gives 0). Round trips: median 4.5c; politics 3.6c; >= 100k liquidity 1.8c; the "no fees
   (unknown category)" cell 727 tokens at 1.8c.
5. **Resolution (`NEW_STREAMS_2026-10-19.md` section 2; `gamma_rules` fields):** the stream stores, per key, question,
   description, `resolutionSource`, dates, outcomes, `groupItemTitle`, **UMA bond / reward / liveness, `resolvedBy`,
   fallback type**, event title / description / source / dates; the sidecar stores `uma_resolution_statuses`. The
   venue's resolution can be 50-50 (the UMA `P3` value; CH07 names it for postponed games, CH47 for disputes); **the
   count of 50-50 resolutions in AREPO's resolution records, overall and by rule class, is unprobed.** CH199's census:
   44.7% of 18,232 eligible non-sports markets appear in the rules stream; 19.9% carry a parseable source host.
6. **Movers (DESIGN_V1 section 19; LIVE_TESTS_7; the map):** 2,750 non-sports 2 h movers an interval; traded 30%;
   48% of movers have never traded (CH167); the map's 1,239 traded a capture; E015's anatomy (traded, quote-only,
   one-sided, parallel, ambiguous) is sealed to 11-10 and analysed 11-15.
7. **Row and sidecar fields (round 16 fact 6):** `best_bid`, `best_ask`, `spread`, `last_trade_price`, `neg_risk`,
   `neg_risk_market_id`, `neg_risk_other`, `event_neg_risk_augmented`, `event_id`; the sidecar's `event_ids`,
   `parent_event_ids`, `series_slugs`, `fee_schedule`, `fees_enabled`, `accepting_orders`, `order_price_min_tick_size`,
   `volume_num` (83% missing), `event_volume`, `event_liquidity`, `event_open_interest`, `rewards_min_size`,
   `rewards_max_spread`, `clob_rewards`, `uma_resolution_statuses`. The engine's `event` family (visible since
   10-22T12:00Z) holds event size, overround, quoted share, normalisation gap, own rank, largest sibling and the
   siblings' Gamma 1 h / 1 d changes as levels; `market_state` holds the neg-risk flag, mid, spread, liquidity, 24 h
   volume, hours to end, tick, age, rv24 and category.
8. **The record on ladders (round 16 fact 7):** E005 not supported, challenger CONFIRMED; HB1 XM1-XM3 nulls (XM3 -0.094c
   in the predicted direction, Holm 0.85); PX1 survived; CANDIDATES "not candidates": neg-risk sums and sibling
   lead-lag; round 13 closed the ladder lead-lag on mids (L1-L4); CH225 is the sports version with the book's joint
   move as the instrument. **Nothing in the record tests a spread on the twin of the same claim, a spread on the
   unrewarded half of a mixed ladder, or a resolution-rate difference by rule class.**
9. **Streams the host runs (NEW_STREAMS section 1 and 2):** the 2 h captures and sidecar; book sweeps, trade samples,
   the flow screen; the monitor; E009 / E010's 120 s poller; CB8-H holders (sealed); the four keyless streams
   (`predictit` 1 min, `smarkets` 5 min, `espn_odds` 10 min on 12 leagues with DraftKings open / current lines,
   `gamma_rules` hourly top-3,000 plus the 6-hourly frame). Binance klines are fetched per capture by the engine's
   `crypto` family (se20). Nothing here proposes a new collector.
10. **Costs (`EXECUTION_COSTS.md`):** a typical market needs a 4.5-point edge to break even; makers about break-even
    before rebates and rewards (fill-weighted mark-out -0.37c); a passive touch order fills 3.1% of the time within an
    hour; a one-sided position held to resolution avoids the exit half-spread (a different rule, not modelled).

**Counts table (what was counted before each idea was written; the source named; `unprobed` where nothing was).**

| ID | Unit | Count on the host | Source |
|---|---|---|---|
| CH242 | resolved non-sports market with a rules text before its origin, by rule class and `resolvedBy` | 50-50 resolutions **unprobed**; rules coverage 44.7% of eligible non-sports | fact 5 |
| CH243 | non-sports ex-crypto traded 2 h mover x capture, by fee class (rate 0 or `fees_enabled` false, against 0.04 / 0.05) | traded movers 1,239 a capture (map); the fee-free share **unprobed** (planning 8-20%: geopolitics at rate 0 plus the pre-03-30 remainder; the 10-11 sweep's `feesEnabled = 0` cell is 2% of tokens, a floor for the remainder only) | facts 2, 4, 6 |
| CH244 | member x capture in a neg-risk event with >= 1 rewarded and >= 1 unrewarded member (a mixed ladder; the unrewarded members the tested class, the rewarded members the within-event control), complete pair (rule 16) | mixed ladders **unprobed** (the map split events, not members; planning 150-600 mixed events, 300-1,500 unrewarded member units a capture) | facts 2, 3 |
| CH245 | member x capture in a complete two-member non-sports ex-crypto neg-risk event (both books two-sided at k - 1 and k) | two-member events a capture **unprobed** (planning 100-400 events, 200-800 member units; completeness 1.00 / 0.97) | fact 2 |
| CH246 | pair of markets in different events on the same claim (duplicate, complement, or a ladder's cumulative member and a standalone) | **unprobed**; a matcher over `gamma_rules` question text and `groupItemTitle` first (planning tens to a few hundred pairs) | fact 5 |
| CH247 | futures-ladder member of a team playing an elimination game, during the game (sports parameter) | elimination games in a 21-day window **unprobed** (planning 20-80); ESPN covers 12 leagues | fact 9 |
| CH248 | 2 h mover in a two-member event, by whether the own book or the twin's book printed (`volume_num`), with missing a counted class | movers in two-member events **unprobed** (planning 20-120 a capture) | facts 2, 6 |
| CH249 | crypto ladder member below the current spot (the "dip to" / "below" side), after a 24 h spot drawdown (engine; crypto is the owner's parameter) | se20 maps about 4,800 of 5,870 crypto sidecar rows; drawdown days **unprobed** | CANDIDATES row 20 |
| CH250 | every eligible row, by the 2 x 2 of taker-fee class x reward status (who pays the maker) | rewarded 9,000-10,700 a capture; fee-free share **unprobed**; the four cells **unprobed** | facts 3, 4 |
| CH251 | the LT12 population map: two-member events, mixed ladders, fee-free traded movers, duplicate pairs, 50-50 resolutions, the 2 x 2 cells, per capture by category and reward status | a map; counts 0 until run | - |

---

## 1. Map: where money might be, given the costs, the census deaths and the price of a quote

The cost model fixes the frame (2.9c in the most liquid tier, 4.5c at the median touch, 5.2c in sports; makers about
break-even before rebates and rewards; a 3.1% passive fill rate within an hour; every taker cell in the record "not shown");
the arithmetic of 0.1 fixes the design (spread targets on dense discontinuities; mover-family mid targets; the two-member
event as the one new dense object). The record since round 16 fixes the odds: LT5-LT8 closed with zero tests, LT11 is
drafted and reviewed with the designer's own P(no test) at about 0.35, and the three LT11 primaries already own the
cheap side's cliff, the arb's bid-sum footprint and the dollar weight of a move. So this round does not go back to the
rewarded panel's boundary, the ladder's bid sum or the mover's collateral; it reads five facts about the venue that the
sixteen rounds have walked past, each of which turns a known level into a dated, side-specific or class-specific event.

1. **One question, two books.** In a two-member neg-risk event the claim "A" is for sale in A's book (its YES ask) and in
   B's book (B's NO ask, which is `1 - bid_B`), with separate makers and a one-way conversion link (NO_A -> YES_B). Under
   a perfect mirror `bid_B = 1 - ask_A` and `ask_B = 1 - bid_A`, so the two spreads are equal and the bid headroom equals
   the spread. Every departure from the mirror is a disagreement between two books about one claim, and **no instant
   arbitrage closes it**: the bid-sum excess is arbitraged (CH09), the ask-sum shortfall is a carry, but the cross-book
   gap `ask_A + bid_B - 1` is neither; the only things that close it are a maker re-quoting or a taker choosing the
   cheaper book. That is why LT11 could only make the two-member event a reported arm (its bid-sum state degenerates to
   the own move there) and why the object this round tests on it is a *spread*, not a bid sum.
2. **The fee is paid by the crosser only, and only where fees are on.** A taker pays `rate x p(1 - p)` a share to cross;
   a maker never pays; geopolitics is at rate 0 and markets deployed before 2026-03-30 carry no fee at all (fact 4). In a
   fee market a crossing is a costly act, so the crosser is more often someone whose expected gain exceeds the fee; in
   the fee-free remainder crossing is free and noise moves prices as easily as information. The same traded 2 h move
   therefore carries different information by fee panel, a contrast nobody has read (round 10 rejected the *within*-market
   fee gradient; this is the *panel*, rule 20).
3. **The reward is per market, the ladder is per event.** A ladder can have paid makers on some members and none on the
   others, and the sum constraint links them: when the paid half re-centres by the minute, the unpaid half's quotes are
   the stale ones, inside the ladder's own arithmetic. The within-event contrast of the two halves after the same shock is
   the one place the reward programme's effect on a maker's reaction can be read with the event's shock held fixed.
4. **The venue's third price.** A market can resolve 0.5 / 0.5, and the engine's own label drops exactly those markets
   (`calibration.parse_outcome` returns `split_50_50`; the label state is `unavailable_split`, counted daily). So every
   `res_7d` row, including the market-price reference, is scored on a two-valued world while the cheap side's price carries
   `0.5 x P(split)` that no label ever pays. The rate of the third price by rule class is a map nobody has drawn.
5. **Who pays the maker.** The taker's fee funds a rebate per fill (fee markets), the venue's programme pays per minute
   of resting (rewarded markets); a maker is paid by one, both or neither, and that fixes whether he wants to be hit or
   wants to rest, before any print happens. The 2 x 2 is a panel the sidecar already labels on every row.

| Family | What the host already dates that nobody has read | Money route |
|---|---|---|
| A. The mirror (CH245, CH248, CH246) | the other book of the same claim widening while this book has not yet; the twin book's print behind a "quote-only" move; the no-link twin in another event | maker on the thin book: widen when the dense book widens (the stale quote inside the mirror is the one that gets picked off); taker: buy the claim in whichever book is cheaper, and the stale tight quote for one slot after the other book moved (gross; reported) |
| B. The fee (CH243) | whether the move's crosser paid a fee at all (the market's fee panel) | maker: re-centre fully on fee-paid traded moves, lean against fee-free ones (gross); taker: follow fee-paid traded moves (reported; the hurdles of 1.10 apply) |
| C. The farmed half (CH244, CH250) | a ladder shock landing on a member nobody is paid to quote, beside a member somebody is; the 2 x 2 of fee x reward on every row | maker: on an unpaid member of a mixed ladder, pull on the siblings' shock (the arb and the informed flow reach the unpaid quote first); the paid-per-fill maker's re-centring against the paid-per-minute maker's retreat (engine, map) |
| D. The third outcome (CH242) | the 50-50 rate by rule class and `resolvedBy`; the branch the engine's label drops | hold-to-resolution buyer of the cheap side in high-split classes (gross; the branch's value is `0.5 x P(split)` against the entry half-spread); a calibration correction for `res_7d` |
| E. Parameters (CH247 sports, CH249 crypto) | the futures ladder member of a team in an elimination game, against the live line; the dip side of a crypto ladder after a drawdown | engine columns under the owner's two parameters; no test proposed |
| F. The map (CH251) | the counts of two-member events, mixed ladders, fee-free traded movers, duplicate pairs, split resolutions and the 2 x 2 cells | decides whether LT12 is drafted at all |

**Data labels.** `A` = on the host now (captures, sidecar, two sweeps, trade samples, the monitor, the E009 / E010
poller's quotes and the `xv_quotes/` successor once it runs, the engine's `quotes/`, `features/` and aux tables, the
engine's label states, the four keyless streams, `reward_params`). `A~` = on the host but a join has to be written and
counted first (the two-member join on `neg_risk_market_id` / `event_id`, the mixed-ladder split, the fee-panel split from
`fees_enabled` / `fee_schedule`, the rules parse, the duplicate matcher). `P` = a fetch is needed (none here). **Sealed and
not usable by anything here:** LT2's, LT3's, LT4's (E022's) stores, LT9's, LT10's and LT11's once registered (**LT11's
objects `xw`, `cl_sib`, `xo`, their twins and targets, and LT11's window captures 11-18..12-09, are not read by any
census or test here**), CB16's and CB17's stores, CB8-H's holders, E009 / E010's `cross_venue_live/` to 2026-11-03, E011's
`surprise_live/` to 11-10, E025's and E026's stores and the E026 frozen modules. J4-R `[2026-10-16, 2026-10-21)` and
CB13-T's holdout `[2026-10-21, 2026-10-26)` are refused for every maker mark-out object; nothing here is one.

**Windows and registration this round proposes (LT12, "the mirror and the fee").** A twelfth family on the captures and
sidecar, registered separately from LT2-LT11 with its own Holm family (k <= 3): CH245, CH244, CH243, after CH251's map.
- **Fast lane.** None of the three reads a state LT9, LT10 or LT11 tests (LT11's states are the collateral weight, the
  siblings' bid sum on 3-10 member events and the rewarded 0.10 / 0.90 crossing; CH245's is the twin book's spread
  innovation on two-member events, CH244's the member's reward status against the ladder's shock, CH243's the fee panel;
  LT9 is the reward band and the pool, LT10 the fine clock), so they can run in the captures slot after LT11's window and
  before LT9's: **window 2026-12-10T00:00Z .. 2026-12-31T00:00Z**, analysis on or after **2027-01-01T12:00Z**, provided the
  design text is frozen **before 2026-12-10T12:00Z (`T_LT11`)** and before the LT12 seal, and the censuses run on a fresh
  seal of **2026-11-07..11-17** (ten UTC days after LT11's seal `[10-28, 11-07)` and before LT11's window; no DST inside;
  the midterm's resolution days 11-04..11-06 outside it, disclosed, since the two-member panel shrinks when the two-party
  races resolve). A freeze before LT11's census commit (about 11-08..11-12) keeps CH245 blind to LT11's counts of
  two-member completeness; a later freeze labels CH245 and CH244 `informed (LT11 census)`, counts only. The window holds
  the holiday fortnight (lower activity; disclosed; no gate depends on it) and may overlap LT9's first day at most (LT9's
  `REGISTERED_UTC` is never before 12-30; overlap in time only, different streams and states, no pooling); it overlaps
  LT10's successor poller and E026 in time only.
- **Ordered lane.** If the pin is not before `T_LT11`, `REGISTERED_UTC` = the first 00:00Z at least 24 h after LT9's
  `END_UTC` and after the LT12 registration commit, never before 2027-01-22T00:00Z; 21 days; single analysis >= 36 h after
  the end; a pin after `T_LT11` labels CH245 and CH244 `informed (LT11)` (the two-member arm and the mixed-ladder split are
  LT11 descriptives) and every pin after `T_E015` (11-15) labels CH243 `informed (E015)` (the traded class), which is
  certain in both lanes and is said so in its entry.
- **Tokens (filed in CANDIDATES at the freeze, before any isolating challenger):** `mirror` (CH245), `mixedlad` (CH244),
  `feeclass` (CH243), each to the later of LT12's analysis commit and the lane's date (fast lane 2027-01-03T00:00Z); an
  attribution limit `attrlimit_lt12` on twin-spread interactions inside `event` / `nrslack`, on reward-status x shock
  interactions inside `event`, and on fee-class x traded-move interactions inside `tilt` / `movetype`, for the champion and
  the broad models to the same date. The `event` family's existing levels and `tilt`'s `tl_fee_ps` level are not requested.

## 2. Hypotheses

### A. The mirror (parents CH09, CH233 / LT11's two-member arm, CH12, CH163, CH64, CH59, CH224 / LT10, CH166, CH156 / E015, round 13's L1-L4; literature: Hasbrouck 1995 on one security priced in several markets, Glosten and Milgrom 1985, Foucault, Kadan and Kandel 2005, the conversion mechanics as CH09 states them)

**CH245. The mirror: a two-member neg-risk event is one question with two order books, two sets of makers and a one-way
conversion link. Under a perfect mirror `bid_B = 1 - ask_A` and `ask_B = 1 - bid_A`, so the two spreads are equal; a
departure is a disagreement between two books about one claim that no instant arbitrage closes (the bid-sum excess is
arbitraged, the cross-book gap is not). When the dense book's makers widen (news, volatility, a farmer's retreat) and the
thin book's have not, the thin book's unchanged quote now sits *inside* the dense book's mirror: it is the cheapest price
of the claim on the venue, it is picked off, and it widens a slot later. The dated object is the twin's spread innovation
over (k - 1, k]; the prediction is the own spread change over (k, k + 1], larger when the own book is the thin one and
near zero in the other direction; LT11's bid-sum state is degenerate here (its own 6.1 item 7), so the mirror is the one
object a two-member event offers that LT11 does not test.**
- Mechanism and why it is non-obvious. Two books, one claim, two prices (Hasbrouck 1995's setting with the venue's own
  conversion as the link). A maker paid by the minute on the dense book re-centres and widens on its own signals; the thin
  book's maker, unpaid or slower, copies the mirror with a lag or learns of the move by being hit through it (a buyer of
  the claim who sees `ask_A < 1 - bid_B` takes A's ask). Who pays: the thin book's maker, whose stale quote inside the
  widened mirror is the venue's best price for one slot; who collects: the taker who buys the claim in the stale book
  (gross), and the thin maker who widens as soon as the twin does. Why the crowd misses it: a market page shows one
  book; the mirror is a join on `neg_risk_market_id` that nobody draws, and the record (L1-L4, XM1-XM3, E005) closed the
  *mids* of ladders, never the spreads of a pair.
- Parent and what is new. CH09 (the asymmetry as a carry), CH12 (dominance pairs across dates), CH163 (the ladder's YES
  premium) and CH64 / CH59 (twins with different rules or forms) read levels across markets; CH233 / LT11 reads the
  siblings' bid-sum rise on 3-10 member events and reports the two-member event as an arm where "the state is the member's
  own move"; CH224 / LT10 reads the other *venue's* spread innovation at the fine clock. New here: the twin *book's* spread
  innovation as the state (not its bid, not its mid), the own spread change as the target, the thin-against-dense ordering
  as the point condition, the mirror gap level as a control, and an unrelated pair's innovation as the declared placebo
  (rule 18). The conversion link is the mechanism's difference from CH246 (the no-link twin in another event).
- Data join and decision clock (`A~`, L 4: a pair join on `neg_risk_market_id` / `event_id` from the rows; the map's JSON
  holds the by-size event counts the report did not print). Unit: non-sports ex-crypto member x capture in a complete
  two-member event (both books two-sided at k - 1 and k; rule 16 applied to a pair; LT11's receipt-span rule reused:
  the two rows' `received_utc` within 120 s at both captures, else no unit, counted). State: `zs_B = z(spread_{B,k} -
  spread_{B,k-1})` (the twin's spread innovation, standardised per event by the census's SD; positive = the twin widened);
  `thin_A = 1[spread_{A,k-1} > spread_{B,k-1}]` (the own book is the wider one at k - 1; `sym` where equal, a reported
  class). Decision time: the later of the two rows' `received_utc` at k. Controls: `spread_{A,k} - spread_{A,k-1}` (the
  own innovation; what has already followed), the mirror gap levels `g_A = ask_A + bid_B - 1` and `g_B = bid_A + ask_B
  - 1` at k, `spread_{A,k} - spread_{B,k}` (the spread gap level), `hb_k` (CH233's level; a control here, never a state),
  `d_A` and `|d_A|` (the own 2 h change; the twin's mid change is its near-mirror and is not entered twice), `log1p
  liquidity` of both books, `z log rv24` of the own book, reward status of each book (13.7's carry), tier.
- Target and horizon. Primary: `ds_A = spread_{A,k+1} - spread_{A,k}` (SD 2c; floor 1.0c); hypothesis (one-sided): within
  event x UTC day, the slope of `ds_A` on `zs_B` > 0 given the controls. **Binding point condition:** the slope on units
  with `thin_A = 0` (the dense book following the thin one) is less than half the slope on `thin_A = 1` (the thin book
  following the dense one); the difference's MDE is reported. M1: the own dear side's touch change at k + 1 (the side the
  mirror says is stale: the ask where `g_A < 0`, the bid where `g_B < 0`), signed as the mechanism predicts. M2: the
  cross-book gap's own change at k + 1 (`g_A`, `g_B` closing toward zero; the "which book moved" reading). M3 (reported):
  the mid change of A at k + 1 (the lead-lag the record closed on ladders; `informed (L1-L4)` by the record).
- Paper rule and economic check (rule 11: maker-side). Maker on the thin book: widen by the twin's widening for one slot
  as soon as the twin widens (the pick-off avoided is `ds_A`, reported in cents a share, gross, no fills). Taker
  (reported, never a verdict): buy the claim in whichever book is cheaper (`min(ask_A, 1 - bid_B)`: a cost reduction on
  every two-member trade, not a forecast, and the one line of this round that belongs in `COST_MODEL.md` as a route), and
  take the thin book's stale quote in the slot after the dense book widened, against the thin book's own half-spread as
  the hurdle (no exit is modelled: the hold-to-resolution rule of `EXECUTION_COSTS.md`'s caveat).
- Population arithmetic. Two-member non-sports ex-crypto events a capture: **unprobed** (completeness 1.00 / 0.97 on the
  map by size; the by-size counts sit in the map's JSON; planning 100-400 events, 200-800 member units a capture); 21
  days: 50,400-201,600 units; `n_eff` 40,320-161,280. Events over 21 days: hundreds to low thousands (two-horse races,
  head-to-head "A or B" questions, yes / no questions listed as two markets); the midterm's two-party races leave the panel
  on 11-04..11-06, so the December count is the one that matters (CH251 prints both). The pair's 21-day cluster is 504
  units, so the LT11 formula gives `DE_gate` about 11; the planning convention 31 is quoted beside it.
- Permutation and cluster structure. Stratum: event x UTC day (24 units by construction; rule 18); the Freedman-Lane null
  (given the event-day, which slot carried the twin's widening does not matter for the own next spread change) with
  **one offset per event** (both members' state series shifted together, LT11's event-phase form); binding scenarios:
  LT5 1-2, L10, **S30: a common event-level volatility shock that widens both books in the same slot with AR persistence
  and no lag** (the own innovation control must absorb it; the gate must return zero on a simulated common shock),
  **S31: one bot quoting both books from one model with a lag under two hours** (the null world: the census's same-slot
  correlation says how much of the panel this is), and **S32 (rule 18's placebo): an unrelated pair's spread innovation
  at the same slot** (must be null in the census-fixed stratum). Clusters: event; `DE_gate` 11 by the formula, 31 by the
  convention; both quoted.
- Planning MDE (spread slope). At `DE_gate` 11: low `3.47 x 2c / sqrt(40,320) x sqrt(11) x 1.5 x sqrt(1.3) x 2.2` =
  **0.43c**; high **0.22c**; a quarter of the low count 0.86c. At 31: **0.72c / 0.36c**; quarter 1.45c. F: the twin is
  `zs_B` over `(k + 2, k + 3]` (planning `r_w` 0.2): at 11 **0.68c / 0.34c (a verdict condition at both ends)**; at 31
  1.15c (low; over the cap: a reported label) / 0.57c (high: a verdict condition). The point condition (the difference of
  the two orderings' slopes, each on half the units): about twice the slope MDE, 0.86c / 0.43c at 11 and 1.45c / 0.72c at
  31: binding where under 1.0c, else reported with the pooled slope as the primary. Kill lines: the F gate binds at about
  **47 two-member events a capture at DE 11 and 131 at DE 31** (93 / 262 member units); the plain MDE gate at 19 / 52.
- Confounders and the control. The own innovation (if A already widened at k, nothing is left to follow; the control; its
  persistence is S30's world); one bot on both books (S31; the same-slot correlation gate); the liquidity gap between the
  two books (thin books are illiquid books: the |corr| gate of `thin_A` and `zs_B` against `log1p liquidity` within and
  pooled; the tier x state interaction reported); reward status of the two books (the paid book is usually the dense one:
  a control and a reported split, `rewards` embargo for the engine only); LT11's two-member arm (a descriptive on a
  different state in a different window; disclosed; the pin before `T_LT11` keeps the test blind to it); the `event`
  family's visible levels (a development look, disclosed; no twin-spread column exists).
- Most likely boring explanation. Two-member events are quoted by one bot that mirrors within the minute, so the two
  spreads move in the same slot and nothing lags (S31: a clean null the same-slot correlation predicts before any
  test); or the December panel of two-member events is a few dozen head-to-head markets (the count kills it); or the
  thin book is one-sided so often that rule 16 leaves too few complete pairs.
- Cheapest census (counts only; the fresh seal; no target read). Two-member events and complete pair units a capture
  (kill if < 93 member units a capture at the formula's DE, or under the F line at the computed DE); the receipt-span
  retention; the within-event same-slot correlation of the two spread innovations (kill if |corr| >= 0.8 in more than 50%
  of events with >= 24 units); the within-event SD of `zs_B` >= 1 tick in >= 50% of events with >= 48 units; the `thin`
  / `sym` / dense shares; the distribution of `g_A`, `g_B` (the mirror gap: the share within one tick of zero, which is
  the share of the panel the mirror already holds); `VIF_w` of `zs_B` against the own innovation <= 2.0; |corr| with the
  tiers <= 0.5; block-gate share (event x day strata with >= 2 shiftable captures) >= 50%; events >= 500 (unprojected, as
  LT11's R1 ruled); `G_eff` >= 15; pessimistic MDE and F-MDE <= 1.0c at the computed DE; the placebo S32 printed as a
  count of unrelated pairs available.
- Challenger feature: **yes, after LT12's freeze** (token `mirror`): `nr_twin_spread`, `nr_twin_dspread`, `nr_gap_ask`
  (`g_A`), `nr_gap_bid` (`g_B`), `nr_thin`, as a spec version of `nrslack` (CH238) on two-member rows; the levels may
  be built now (no test reads them), the innovation after the freeze. No isolating challenger before the freeze.
- Sports arm: uncounted (head-to-head game markets are mostly single binaries, not two-member events; the match-winner
  events that are two-member neg-risk events are the sports version, under the owner's parameter).
- Scores: N 4, EV 3, L 4. Parents: CH09, CH12, CH163, CH64, CH59, CH233 / LT11 (the arm), CH224 / LT10 (the other
  venue's spread), CH166 (the lead is where the liquidity is). New: the second book of the same claim as the dated
  object, the spread as the target, the thin-against-dense ordering as the condition, the mirror gap as the control, the
  conversion link as the difference from a mere duplicate.

**CH248. Who printed, this book or the other one (`movetype` spec; engine-first): in a two-member event a trade in B's
book moves A's quotes through the mirror without any trade in A, so A's "quote-only" mover (E015's class, CH234's twin
population) splits into *the twin printed* (a paid trade on the same claim, in the other book) and *nobody printed*. The
dollars behind the move were paid; they were paid next door. The engine's `movetype` family reads the own `volume_num`
only and so labels a twin-printed move as quote-only.**
- Why engine-first. The population is small (movers in two-member events; planning 20-120 a capture, unprobed; four
  classes with `volume_num` missing on 83% of sidecar rows, so most are `unknown`), far under the mover-family line of
  335 a capture for a mid slope; and the pin of any test would follow `T_E015` (11-15), so the traded class is informed.
- Columns (`A~`, L 4 after 2026-11-22, the `movetype` date; clock: the later of the two rows' receipts). On every mover
  in a complete two-member pair: `mt_own_printed` (the own `volume_num` rose), `mt_twin_printed` (the twin's rose, the own
  did not), `mt_both`, `mt_neither`, `mt_unknown` (either value missing, keyed by slot, never carried: LT11's MUST 5),
  `mt_twin_dvol` (`log1p` of the twin's volume change), `mt_twin_moved` (the twin's |2 h change| >= 1c).
- Expected direction. `dir_2h`: twin-printed movers continue like own-printed ones and more than nobody-printed ones
  (CH234's mechanism across the mirror: the collateral was paid in the other book); calibration: the quote-only class's
  forecast error shrinks once the twin-printed share is separated.
- Why not already held. `movetype` holds the own traded flag and the own 2 h volume change (C07 / C12); `event` holds
  the siblings' Gamma changes, not their prints; nothing reads the twin's `volume_num`. Adjacent to `movetype` (built
  after 11-22) and to LT11's `dw_quote_only` (not isolated before LT11's freeze; the attribution limit).
- Map (counts only): the four classes among movers in two-member events by reward status (part of CH251).
- Boring explanation. Twin prints are rare (the thin book never trades), or `volume_num` is missing on both rows so
  often that the classes are `unknown` on most movers.
- Census (counts only): movers in complete two-member pairs a capture; the four classes' shares (kill if `twin_printed`
  is under 5% of classified movers).
- Scores: N 3, EV 2, L 4. Parents: CH156 / E015 (anatomy), CH234 / LT11 (the quote-only twin), CH245, CH66 (conversion
  dumps). New: the other book's print as the class of this book's move.

**CH246. The no-link twin (a matcher and a map first; a reported arm of CH245; engine-first columns): the same claim is
listed twice across events without a conversion link, as a standalone binary and a ladder member with the same
`groupItemTitle`, as a cumulative "by D" member and a standalone "by D", or as a two-way race listed as two standalone
binaries. CH245's mechanism needs the link (the pick-off through the mirror); the attention story does not. The pair
without the link is CH245's falsification arm: if the twin's spread innovation predicts the own spread change equally
well without the link, the mirror is quote-copying, not the arbitrage's shadow.**
- Data join (`A~`, L 3: a matcher over `gamma_rules` question text and `groupItemTitle` (44.7% coverage of eligible
  non-sports markets) and the sidecar's `series_slugs`; a stem match after stripping dates, numbers and the venue's
  boilerplate; 50 pairs hand-audited, counts only, precision recorded; the matcher pinned by sha256 before any count).
  Unit: member x capture in a matched pair with both books two-sided at k - 1 and k. State, target, controls: CH245's,
  with `hb` undefined (no event) and the mirror gap replaced by the price gap of the two claims (a level control).
- Why not a live primary. Pairs: **unprobed** (planning tens to a few hundred); at 50 pairs (100 member units a capture)
  the spread slope's planning MDE at DE 11 is 0.61c and its F-MDE 0.96c, which clears 1.0c only from about 50 pairs up; the
  matcher's precision is the first gate; the record (CH64, CH59, CH13) holds the level versions. So: a map and an arm,
  engine columns `tw_has_twin`, `tw_spread_gap`, `tw_twin_dspread`, `tw_mid_gap` inside the `event` family's spec (no
  token; no test reads them), and the arm inside CH245's reader if the count clears 105 member units a capture.
- Money route. The same as CH245's taker line without the conversion: buy the claim in the cheaper listing (a cost
  reduction, not a forecast); the hold-to-resolution carry on the price gap is CH64's level object and is not re-proposed.
- Boring explanation. Duplicates are few, mostly one liquid and one dead listing (CH10's placeholders), so the pair has
  no two-sided thin book to follow.
- Census (counts only): matched pairs and their two-sided share; precision on 50; complete pair units a capture.
- Scores: N 3, EV 2, L 3. Parents: CH64, CH59, CH13, CH163, CH10, CH245. New: the pair without the link as the
  mechanism's control.

### B. The fee as the price of urgency (parents CH72, CH34, CH52, CH53, CH61, round 3's fee-tag twins and zero-fee islands (parked), round 10's fee parabola (rejected), CH156 / E015, CH234 / LT11; literature: Kyle 1985, Glosten and Milgrom 1985, Colliard and Foucault 2012 and Malinova and Park 2015 on trading fees and who crosses)

**CH243. The fee as the price of urgency: a taker pays `rate x p(1 - p)` a share to cross, a maker never, and in the
fee-free remainder (geopolitics at rate 0; markets deployed before 2026-03-30 with fees off) nobody pays anything. A fee
does not stop the informed (their expected gain is cents) and does stop some of the noise (whose expected gain is zero),
so a *crossed* move in a fee market is more often an informed move than the same crossed move in a fee-free market. The
fee is a market-level constant (rule 20: a panel, never a state), so the test is the contrast of two within-market
quantities across panels: the continuation of traded 2 h moves in fee markets against fee-free markets, with the
quote-only movers of both panels (where nobody crossed and nobody paid) as the binding point condition.**
- Mechanism and why it is non-obvious. Colliard and Foucault 2012 and Malinova and Park 2015: a taker fee changes who
  crosses, not only how much crossing costs; on this venue the fee is small against the spread (round 10's arithmetic:
  0.1-1.25c against 1.8-4.5c round trips) but large against a noise trader's expected gain, which is the comparison
  that fixes composition. Who pays: the maker who re-centres as far on a fee-free crossed move as on a fee-paid one; the
  taker who fades a fee-paid move. Why the crowd misses it: the fee is read as a cost (round 3 parked the zero-fee
  islands as "where small taker effects become viable"; round 10 rejected the within-market fee gradient as a limit to
  arbitrage); nobody has read it as a filter on the crosser.
- Parent and what is new. CH72 (the fee valley's farming flow), CH34 (fee-band persistence), CH52 / CH53 (the fee
  history and what flow means after the rollout), CH61 (geopolitics tails as the fee-free category's level), CH156 / E015
  (the traded class), CH234 / LT11 (the collateral behind a traded move; the quote-only twin). New here: the fee *panel*
  as the moderator of the traded-minus-quote-only continuation difference, the fee-free remainder identified from the
  sidecar (`fees_enabled`, `fee_schedule.rate`, `created_at` before 03-30) rather than from the category, and the
  cell-matched control (liquidity tier x category) that the fee-free panel's composition demands.
- Data join and decision clock (`A~`, L 3). Unit: non-sports ex-crypto 2 h mover x capture (`|d_k| >= 0.01`, `p_{k-1}` in
  [0.04, 0.96]), classed traded / quote-only / unknown by the own `volume_num` keyed by slot (LT11's MUST 5; `unknown`
  a counted third class, never classed). Panel: `fee_free` = (`fees_enabled` false) or (`fee_schedule.rate` = 0) at the
  origin sidecar, else `fee_on` (rate 0.04 / 0.05; crypto excluded); `fee_src` records which reading made it (the
  category, the deployment date, the flag). Decision time: the row's `received_utc` at k. Within-market term: `1[traded]`
  on movers (E015's object, `informed (E015)` by the pin's date in both lanes, disclosed as the known factor). Controls:
  `|d_k|`, `p_{k-1}`, `sign(d) x g(p)` (PX1's drift in four bins), spread, `log1p liquidity`, `z log rv24`, the
  `volume_num` change, tier, hours to end, market age (the fee-free remainder is old).
- Target and horizon. `c = sign(d_k) x (mid_{k+1} - mid_k)` (SD 4c; floor 0.5c); hypothesis (one-sided): the within-
  market coefficient of `1[traded]` on `c` is larger on the `fee_on` panel than on the `fee_free` panel (the panel
  contrast of two within-market coefficients; cluster-robust across events, rule 20). **Binding point condition:** on
  quote-only movers alone (nobody crossed), the panel contrast of the continuation intercept is less than half the traded
  contrast. M1: `c_skip` (the lagged step). M2: the same contrast restricted to the pre-03-30 remainder within category
  (geopolitics removed: the category confound's cleanest cell; reported). M3: the contrast by price bin (the fee at 0.5 is
  five times the fee at 0.05; the composition effect should be larger where the fee is larger; reported).
- Paper rule and economic check. Maker: re-centre by the full move after a fee-paid traded move and by a declared
  fraction after a fee-free one (gross; the adverse selection avoided is the continuation difference). Taker (reported,
  never a verdict): follow fee-paid traded moves of >= 3c against the cost model's round trip by tier (note the irony the
  design must state: the follow trade itself pays the fee, 1.0-1.25c at mid prices, on top of the spread). Hold-to-
  resolution: none.
- Population arithmetic. Traded movers 1,239 a capture (the map; rewarded 1,021 / unrewarded 218); the fee-free share
  **unprobed**: the planning range 8-20% gives 100-250 fee-free traded movers a capture, but the 10-11 sweep's
  `feesEnabled = 0` cell is 2% of tokens (727 of 37,225, `EXECUTION_COSTS.md`), which bounds the pre-03-30 remainder from
  below and says nothing about geopolitics' share of traded movers; 21 days: 25,200-63,000 fee-free traded units,
  `n1_eff` 20,160-50,400 against `n2_eff` about 201,600. Quote-only movers 2,466 a capture (both panels). Events: thousands;
  cluster = event; `DE_gate` 6.196 for the within-market term, the panel contrast cluster-robust across events.
- Permutation and cluster structure. Rule 2 strata (market x UTC day); the Freedman-Lane null tests the within-market
  term only (which of a market-day's moves were traded does not matter for continuation); the panel contrast is a
  between-market comparison and its null is the cluster-robust one (rule 20); binding scenarios: LT5 1-3, L10, CH234's S28
  and S29, **S33: a fee-free panel that is older, larger and slower (the remainder's composition) with the same
  continuation per traded move** (the cell-matched control panel, LT9's CH213 form: the fee-on comparison units drawn
  from the same liquidity tier x category x age cells, must return zero), and the VIF gate of rule 17.
- Planning MDE (mid class contrast of two within-market coefficients; the traded indicator carries no gap factor; the
  contrast of two differences carries sqrt(2)). Low: `3.47 x 4c x sqrt(1/20,160 + 1/201,600) x sqrt(6.196) x 1.5 x sqrt(1.3)
  x sqrt(2)` = **0.62c**; high **0.42c**; a quarter of the low count 1.19c. F (movers, `r_w` 0.1): 0.92c / 0.62c, **over the
  cap at both planning ends.** The plain gate (0.5c) passes at >= about **160 fee-free traded movers a capture**; the F
  gate at about 445 (a third of all traded movers: implausible). **By rule 7 this is engine-first**, said so here; the live
  door opens only if CH251's map counts >= 160 fee-free traded movers a capture, and then with F as a reported label (LT9's
  CH212 precedent), which the LT12 designer must accept or decline in writing.
- Confounders and the control. The fee-free panel is a category (geopolitics) plus an age cohort (pre-03-30 deployments:
  the venue's oldest, largest, longest-dated markets, the >= $100k tier), so the raw contrast is a subject-matter and
  liquidity comparison (round 10's objection, now the cell-matched control's job; the |corr| gate of `fee_free` against
  `log1p liquidity` pooled is the census's first number and the one most likely to fail); the maker rebate exists only
  on the fee-on panel (the maker's pay per fill: CH250's axis; a control, `tl_rebate_ps`); E015's traded class (informed
  in both lanes; disclosed); E022's traded movers (its window ends 11-16; no overlap); LightGBM se1 holds the category
  one-hot and may have learned the fee's shape (disclosed; the attribution limit).
- Most likely boring explanation. The fee-free panel is a few dozen old markets and geopolitics, too few and too
  different (the census kills it on count or on the liquidity correlation); or the crossers on this venue are retail in
  both panels and a 1c fee filters nobody (a clean null).
- Cheapest census (counts only; the fresh seal; no target read). Fee-free traded and quote-only movers a capture by
  `fee_src` (kill if < 160 traded); the cell-matched control's coverage (the share of fee-free units with >= 20 fee-on
  units in their tier x category x age cell; kill if < 60%); |corr| of `fee_free` with the tiers pooled <= 0.5; `VIF_w`;
  block-gate share >= 50% on both panels; events >= 500 on the fee-free panel (unprojected); pessimistic MDE <= 0.5c; F-MDE
  printed; the fee reading recorded (schedule against docs, `schedule_below_docs` flags).
- Challenger feature: **yes** (engine-first by default): `tl_fee_free` and `tl_fee_src` as levels in `tilt` now (no test
  reads them), `tl_fee_x_traded` after 2026-11-22 (`movetype`); token `feeclass` only if LT12 takes the live door.
- Sports arm: uncounted (sports at 0.03 / 0.05 with the 15% rebate; no fee-free sports exist, so the arm is the fee-rate
  gradient only; the owner's parameter).
- Scores: N 4, EV 3, L 3. Parents: CH72, CH34, CH52, CH53, CH61, CH156 / E015, CH234 / LT11. New: the fee as a filter on
  the crosser, the fee-free remainder from the sidecar, the panel contrast of a within-market difference.

### C. The farmed half (parents CH16, CH45, CH183, CH209, CH19, CH10, CH39, CH35, CH233 / LT11, E022's S2, XM3; literature: Foucault, Kadan and Kandel 2005, Malinova and Park 2015, Glosten and Milgrom 1985)

**CH244. The farmed half of a ladder: the liquidity programme is per market, the ladder is per event, so a neg-risk event
can have paid makers on some members and none on the others, and the sum constraint links the two halves. When the ladder
is shocked (any sibling moves), the paid half re-centres by the minute because its makers are scored on resting inside
the band; the unpaid half's quotes are the stale ones, inside the ladder's own arithmetic, and are the first the
arbitrageur and the informed buyer reach. The dated prediction is a within-event contrast nobody has read: after the same
shock, the unrewarded members' spreads widen more than the rewarded members' in the same event-day, and all-rewarded and
all-unrewarded ladders, where no contrast exists, are the placebo.**
- Mechanism and why it is non-obvious. A maker paid per minute of resting inside `rewards_max_spread` cannot pull without
  losing the minute, so after a shock he re-centres and stays (CH183, CH209); an unpaid maker on the next rung of the
  same ladder has no such tie and steps back (CH39's retreat), or is hit first because his quote is the one that did not
  move when the ladder's implied value did (the sum constraint). Who pays: the unpaid maker whose stale bid the
  arbitrageur sells into, or whose stale ask the buyer lifts; who collects: the arbitrageur, and the buyer who takes the
  unpaid member's stale ask when the shock moved value toward it. Why the crowd misses it: the reward programme is read
  per market (`clob_rewards` on each row); the *mix* within an event is a join nobody has drawn (the map split events by
  status, not members).
- Parent and what is new. CH16 / CH45 (reward geometry), CH183 (the farmer's choice), CH209 (the farmer touch), CH19 (the
  cliff), CH10 (placeholder members), CH233 / LT11 (the siblings' signed bid-sum rise on the member's spread, all members
  alike), E022's S2 (the reward split of traded movers' depth), XM3 (siblings' changes on the mid). New here: the
  *within-event* contrast of the two reward halves after the same shock (the shock held fixed by the stratum), the
  unsigned event shock as the clock (not the signed bid sum), the spread as the target, and the all-one-status ladders as
  the placebo.
- Data join and decision clock (`A~`, L 3: the event join on `neg_risk_market_id` / `event_id`; the member-level reward
  status from 13.7's carry). Unit: non-sports ex-crypto member x capture in a complete event-capture pair (rule 16) of a
  **mixed** ladder (>= 1 rewarded and >= 1 unrewarded eligible member at k - 1 by `listed_carry24h_v2`, the CLOB feed
  adjudicating), events with 3-10 eligible members (11+ a reported arm; 2-member events excluded: they are CH245's).
  State: `shock_k = 1[max_{j != i} |d_{j,k}| >= 2 x tick_e]` (the largest sibling 2 h move at (k - 1, k] is at least two
  ticks; `shock_size` the continuous version), `unrew_i` (the member's own status; fixed within market, a panel inside the
  event; the tested term is the interaction `shock_k x unrew_i`). Decision time: the latest member row's `received_utc`
  at k. Controls: `shock_size`, the own `d_i` and `|d_i|`, the own spread level, `hb_{k-1}` (CH233's level), the member's
  bid share and rank, `log1p liquidity`, `z log rv24`, event size, `neg_risk_other`, tier, and **tier x shock** (the
  liquidity twin of the tested term: unrewarded members are the illiquid rungs).
- Target and horizon. Primary: `ds_i = spread_{i,k+1} - spread_{i,k}` (SD 2c; floor 1.0c); hypothesis (one-sided): within
  event x UTC day, the coefficient of `shock_k x unrew_i` > 0 given the controls (after a sibling shock the unpaid member's
  spread widens more than the paid member's). **Binding point condition:** the same interaction on the *tier x shock*
  twin (the illiquid-member contrast with status held fixed) is less than half the status contrast. M1: the member's bid
  change at k + 1 (the arb's side), signed. M2: the member's mid change at k + 1 toward the siblings' implied value
  (reported; `informed (L1-L4, E005)` by the record). M3: the traded-shock arm (`shock` read from a sibling's `volume_num`
  rise where present; reported, `unknown` counted). M4 (placebo, reported): the shock's main effect on all-rewarded and
  all-unrewarded ladders (no status contrast exists; the spread's reaction to a shock there is the baseline).
- Paper rule and economic check (rule 11: maker-side). Maker on an unpaid member of a mixed ladder: pull or widen for one
  slot when a sibling moves two ticks or more (the fill avoided is the next slot's bid change; gross, no fills); a paid
  maker has no rule (he stays by design). Taker (reported, never a verdict): the buyer of the unpaid member waits one slot
  after a sibling shock (the retreat is the saving; the hurdle is the rung's own round trip, 4-7c on illiquid rungs,
  which the hold-to-resolution rule avoids on exit only).
- Population arithmetic. Mixed ladders a capture: **unprobed** (the map's 1,664 rewarded / 825 unrewarded events were
  split by event; planning 150-600 mixed events of 3-10 members; unrewarded member units 300-1,500 a capture, rewarded
  members of the same ladders 600-3,000); shock share of event-captures planning 0.30 (unprobed): tested units
  (unrewarded x shock) 90-450 a capture, 18,144-90,720 effective over 21 days against rewarded x shock 36,288-181,440.
  Events over 21 days in the thousands (every nominee, "how many", "who will" ladder with a sponsored favourite and
  unsponsored longshots); cluster = event; `DE_gate` 31 (cap 10).
- Permutation and cluster structure. Stratum: event x UTC day (36-120 units); the Freedman-Lane null (given the
  event-day, which slots carried a shock does not matter for the next spread changes) with one offset per event (the
  shock series is event-level; LT11's event-phase form); the status is a within-event panel, never permuted; binding
  scenarios: LT5 1-2, L10, CH233's S26 (a common shock in the same slot: the state is lagged by construction) and S27 (a
  dormant ladder whose only mover is the favourite: the shock is then the favourite's move and the unpaid rungs are the
  dormant ones, which is a dose, reported by rank), **S34: a liquidity-driven reaction with no status effect** (illiquid
  rungs widen more after any shock whatever pays their maker: the tier x shock control and the point condition must
  absorb it; the gate must return zero on a simulated world where the reaction scales with 1 / liquidity only), and the
  reward field's S-worlds (13.7's carry; the feed adjudicates; a member whose status switches inside the day is a
  counted class, excluded).
- Planning MDE (spread class contrast of the interaction, 1 : 2 within shock slots, times sqrt(2) for the difference of
  differences). Low: `3.47 x 2c x sqrt(1/18,144 + 1/36,288) x sqrt(31) x 1.5 x sqrt(1.3) x sqrt(2)` = **0.85c**; high
  **0.38c**; a quarter of the low count 1.70c. F (the twin is the shock over `(k + 2, k + 3]`; planning `r_w` 0.2): **1.34c
  (low; over the cap: a reported label) / 0.60c (high: a verdict condition)**; F binds at about **540 unrewarded member
  units a capture** at a 0.30 shock share (162 tested units); the plain gate (1.0c) passes at about 217 (65 tested units).
- Confounders and the control. Unpaid rungs are illiquid rungs (the tier x shock control; the point condition; the |corr|
  gate of `unrew` against `log1p liquidity` within event is the census's first number and the likeliest killer); the
  reward field's omission and switching (13.7's carry; switchers excluded and counted); the favourite as the only mover
  (S27; by rank); the ladder's completeness by status (unrewarded members are one-sided more often: 0.65 against 0.85 on
  the map for 3-10 members; rule 16 drops the pair, counted); CH233 / LT11 (a signed state on all members of 3-10 member
  events in a different window; the pin before `T_LT11` keeps this blind to its result; disclosed); the `event` family's
  visible levels (disclosed).
- Most likely boring explanation. Mixed ladders are rare (the venue sponsors whole events, not members: the count kills
  it), or the unpaid members are placeholders (CH10) with no two-sided quote to widen, or the widening is the liquidity
  gradient and nothing else (S34: the point condition fails cleanly).
- Cheapest census (counts only; the fresh seal; no target read). Mixed ladders a capture and their member counts by
  status (kill if unrewarded member units < 217 a capture, or under the F line at the computed DE); completeness by
  status; the shock share of event-captures (kill if < 0.10 or > 0.80); within-event |corr| of `unrew` with `log1p
  liquidity` <= 0.5 (within and pooled); the share of mixed events with both statuses two-sided on >= 24 units; `VIF_w`
  of the interaction against tier x shock <= 2.0; block-gate share >= 50%; events >= 500 (unprojected); `G_eff` >= 15;
  switchers' share printed; pessimistic MDE <= 1.0c; F-MDE printed.
- Challenger feature: **yes, after 2026-11-18** (`rewards`) for the levels (`nr_mixed`, `nr_unrew_share`, `nr_own_unrew`
  inside `nrslack`'s spec) and after LT12's freeze for the interaction (token `mixedlad`).
- Sports arm: uncounted (futures ladders with sponsored favourites and unsponsored longshots are the sports version;
  the owner's parameter).
- Scores: N 4, EV 3, L 3. Parents: CH16, CH45, CH183, CH209, CH19, CH10, CH39, CH233 / LT11, E022's S2, XM3. New: the
  within-event contrast of the two reward halves after one shock, the unsigned shock as the clock, the one-status
  ladders as the placebo.

**CH250. Who pays the maker (`paymaker`; engine-first, with the map and a conditional live door): a maker is paid by the
taker's fee (the rebate per fill, fee markets only), by the venue (the programme per minute of resting, rewarded markets
only), by both or by neither, and the sidecar labels every row with both axes. A maker paid per fill wants to be hit
and re-centres after a print to be hit again; a maker paid per minute wants to rest unhit and steps back after a print;
an unpaid maker steps back furthest. The four cells therefore order the spread's reaction to a traded move before any
print happens.**
- Why engine-first. Three of the four cells are counted only by the map (fee-free rewarded and fee-free unrewarded are
  unprobed and plausibly tiny: the unrewarded traded movers are 218 a capture, and 8-20% of them fee-free is 17-44, under
  the spread-slope line of 105 / 260); the rewarded-against-unrewarded contrast within fee-on markets is E022's S2
  territory (`informed (E022)` after 11-17). So the family is columns and a map, with a live door only if CH251 shows
  every contrasted cell above 105 traded movers a capture (260 with F).
- Columns (`A`, L 3; clock: the row's receipt; sidecar fields only). `pm_fee_on` (`fees_enabled` and rate > 0),
  `pm_rewarded` (13.7's carry; **after 2026-11-18**, the `rewards` date), `pm_cell` (the 2 x 2 one-hot), `pm_rebate_ps`
  (the category's rebate share x `rate x p(1 - p)`: the maker's pay per filled share; `tilt`'s level, reused),
  `pm_minute_ps` (the programme's pay per minute of a minimum quote inside the band, from `rewards_min_size` and
  `rewards_max_spread` at the row's spread, under the scoring rule as quoted; a level), interactions `pm_cell x traded x
  |d|` (**after 2026-11-22**, `movetype`).
- Expected direction. `ds` after a traded move ordered by cell: neither >= reward-only >= both >= fee-only (the unpaid
  maker widens most, the per-fill maker least); `dir_2h`: continuation after a traded move is largest in the fee-only cell
  (the per-fill maker re-centres fully; CH243's panel reading from the maker's side); calibration by cell.
- Why not already held. `rewards` holds the programme's parameters as levels; `tilt` holds `tl_fee_ps` and
  `tl_rebate_ps` as levels; `movetype` the traded flag; nothing holds the cell or its interaction with the move. The
  logistic champion cannot form the product; LightGBM se1 can learn it from the category and the reward flag only after
  11-18, which is why the honest read is against se9 / se1 with the attribution naming the cell.
- Map (counts only; part of CH251): rows, traded movers and quote-only movers a capture by cell, category and tier; the
  rebate-per-fill against the minute-pay distribution by cell (levels; no target).
- Boring explanation. The venue sponsors the fee-on markets (the two axes are one axis: rewarded = fee-on), so the 2 x 2
  is a 2 x 1 and the family is `rewards` under a new name; the census says so before any column is scored.
- Census (counts only): the four cells' row shares (kill the family if the two fee-free cells together are under 3% of
  non-sports rows); traded movers by cell.
- Scores: N 3, EV 3, L 3. Parents: CH16, CH45, CH72, CH183, CH209, CH235 (the tilt's levels), CH243, E022's S2. New: the
  two payers as a 2 x 2 that fixes the maker's reaction before the print.

### D. The third outcome (parents CH07, CH47, CH65, CH03, CH128, CH199, CH207, CH221, CH239; the venue's UMA documentation as CH47 cites it)

**CH242. The venue's third price (`p3`; engine-first with a map first; rule 19): a market can resolve 0.5 / 0.5, and the
engine's own label drops those markets (`parse_outcome` returns `split_50_50`; the state is `unavailable_split`, counted
daily on the leaderboard). The cheap side of an ambiguous question is therefore a straddle on ambiguity: a YES at 0.05 pays
0.50 on a split, ten times its price, and its price should carry `0.5 x P(split)`; its sellers price it as a probability
of YES. Every `res_7d` row, including the market-price reference, is scored on a two-valued world in which that branch is
removed from the label but not from the price, which biases the reference against the cheap side by about half the
split rate of its class. The split rate by rule class and `resolvedBy` is a map nobody has drawn; it is the first line.**
- Why engine-first. Rule 19: no live primary reads a resolution; a split is a counted class, never folded; the rate by
  class is a map before any feature. The economics are a hold-to-resolution carry on a cheap side (a level route) and
  the honest target is `res_7d` calibration, where 21 days give crypto and sports only.
- The map (counts only; `A`; the engine's label store and `parse_outcome` reasons, the resolution fetch's resolved
  records, the `gamma_rules` rows before each market's origin): the split share of resolved non-sports markets overall
  and by category, by CH239's rule class (barrier / terminal / threshold / multi-source), by the presence of a 50-50 or
  cancellation clause in the rules text (round 6 found "50-50" in 14 of 100 closed September markets, all with a
  `gameStartTime`: a sports clause, so the non-sports rate is the open question), by `resolvedBy`, by the UMA bond and
  liveness tier (CH207's classes) and by the fallback type; the cheap side's mid at its last origin before resolution,
  by class (a level count; no P&L); whether AREPO's resolution records distinguish a 0.5 / 0.5 outcome from a missing one
  at all (the first number: if `split_50_50` is never seen because the fetch stops at `umaResolutionStatus != resolved`,
  the map says so).
- Columns (`A~`, L 3; `res_7d` only; clock: the rules poll's `recv_utc` and the resolution records before the origin;
  expanding-past, pinned by sha256 after the first count). `p3_clause` (the rules text carries a split / cancel /
  postpone / "unknown" clause; a parse), `p3_class_rate` (the expanding-past split rate of the market's rule class, from
  resolutions received before the origin only; NaN under 50 resolutions in the class), `p3_branch_value` = `0.5 x
  p3_class_rate` (the branch's value a share), `p3_bond_tier` (CH207's class), `p3_resolver` (`resolvedBy` class).
- Expected direction. `res_7d` and calibration: at a given mid, markets with a split clause or a high-rate class resolve
  YES (as labelled) less often than the mid says, by about half the class's split rate (the mid carries the branch, the
  label drops it); the market-price reference's gain over the model should shrink in those classes once the column is
  held. `dir_2h`: none. A scoring proposal for the builder, not made here: a three-valued `res_7d` reference row (the
  mid against the outcome with 0.5 paid on a split) beside the two-valued one, so the reference is not biased against
  the cheap side; it is a learner / scoring change under DESIGN_V1 section 19 and needs a design note.
- Why not already held. `market_state` holds the category and hours to end; CH228's `ruleedit` the edit's age and
  `re_fallback`; CH239's `ruleclass` the barrier / terminal / threshold classes; nothing holds the split rate or the
  clause, and the label itself cannot (it drops the split). No token covers rule text or resolution classes.
- Money route (gross; the map's arithmetic, not a test). The hold-to-resolution buyer of the cheap side in a high-split
  class: expected value a share `P(split) x (0.5 - p) + P(YES) x (1 - p) - (1 - P(split) - P(YES)) x p - entry
  half-spread`; at p = 0.05 and a 1.5-2c entry half-spread the branch alone covers the cost only where `P(split)` is
  above about 4%, which non-sports classes are unlikely to reach (the map says); the sports postponement clause (CH07)
  is where it may, under the owner's parameter.
- Boring explanation. Splits are a few tenths of a percent of non-sports resolutions, concentrated in a class the
  category one-hot already names (sports postponements), and the reference's bias is a rounding error.
- Census (counts only): the split share of non-sports resolutions in the label store (kill the family if < 0.5% and no
  class >= 3%); the clause parse rate on the 44.7% covered; the class-rate coverage (the share of eligible rows whose
  class has >= 50 resolutions before the origin).
- Sports arm: uncounted (CH07's postponement optionality is the sports version; the clause is a sports clause by round
  6's count).
- Scores: N 3, EV 2, L 3. Parents: CH07, CH47, CH65, CH03, CH128, CH199, CH207, CH221, CH239. New: the split as a third
  price the engine's label drops, the cheap side as a straddle on ambiguity, the rate by class as a map and a `res_7d`
  column, the three-valued reference as a scoring question.

### E. Parameters: the sports and crypto arms (engine-first; the owner's calls)

**CH247. The elimination game and the futures ladder (`gamestate` x futures; engine-first; sports parameter): a futures
ladder member ("Champion: team T") is worth `P(T wins tonight) x P(title | advances)` during an elimination game, and the
game's own probability moves minute by minute on ESPN's board (CH231's `gamestate`, the `espn_odds` stream) while the
futures member's makers re-quote on a slower clock. The live line's change is a dated input the futures member's mid
should follow with a lag, and at the final whistle the loser's member goes to its residual.**
- Why engine-first. Elimination games with a futures ladder member in a 21-day window are few (**unprobed**; planning
  5-30 in December: the CFB playoff's first round, domestic cup ties, the MLB and NHL playoffs are outside the window;
  the NFL's December eliminations are arithmetic across games, not single games); one game is one cluster (`DE_gate`
  3.0) and the mid target needs hundreds of units a capture. The owner's sports decision is pending.
- Columns (`A~`, L 2: the ESPN stream's coverage of elimination games and the team-entity join to the futures event's
  `groupItemTitle` are unprobed; clock: the ESPN poll's `recv_utc` before the capture). On futures ladder members whose
  team is in a live game: `gs_elim_live` (a loss eliminates the team from the futures question: a declared per-competition
  rule table, pinned), `gs_elim_wp` (the live de-vigged moneyline P(team wins), CH231's `gs_wp`), `gs_elim_dwp` (its change
  over the last 20 minutes of polls), `gs_elim_implied` (the member's mid at the previous capture scaled by the live win
  probability over its pre-game value: the mechanical implied value), `gs_elim_gap` (`mid - gs_elim_implied`).
- Expected direction. `dir_2h` and `dir_6h` on futures members during elimination games: the mid follows `gs_elim_dwp`
  (the futures book lags the game book); after the whistle the loser's member's residual decays (CH67's unwind, if the
  venue resolves it early). `res_7d`: not a target (the title resolves months later).
- Why not already held. `gamestate` (CH231) is defined on the *game* markets; `event` holds the futures ladder's own
  siblings, not the game; `steam` (CH205) is the pre-game line move. The futures join is new and sits under the `steam`
  token's owner decision (no isolate before it).
- Money route. The futures member's maker pulls during an elimination game (the stale ask on the losing team is the
  one lifted); the taker's hold-to-resolution NO on the eliminated member pays only if the venue resolves it early
  (CH67; otherwise CH115's lock-up); round 3 recorded the impossible-bucket residual as a CH01 footnote for that reason.
- Boring explanation. The futures ladder's farmers watch the game too and re-centre within the minute; or there are
  five such games in the window.
- Census (counts only): elimination games with a futures member in the span; the join's precision on a hand audit of
  20 (kill if < 90%); the futures members' two-sided share during games.
- Scores: N 3, EV 2, L 2. Parents: CH231, CH205, CH225, CH23, CH67, CH14. New: the game's live probability as the input
  to the *futures* member, the elimination as the clock.

**CH249. The dip side after a drawdown (`crypto` spec; engine-first; crypto parameter): a crypto barrier ladder lists
"dip to $L" and "reach $U" members, and the probability of touching a barrier is about twice the terminal probability
under a driftless walk and far more sensitive to volatility (CH118's confusion, CH138's skew). A sharp 24 h drawdown is a
dated event that raises realised volatility and moves spot toward the dip side; the side x drawdown interaction, which
se20 does not hold, says whether the dip-side members re-price fully in the slot or over the next ones.**
- Why engine-first. Drawdown days in a 21-day window are few (**unprobed**; planning 2-6 at |r24| >= 2 x rv7); crypto is
  the owner's parameter; CB13-R closed the barrier basis as not testable; the 0.07 fee (3.5c median at mid prices) and
  the 4.5c round trip make every taker route dead on arrival; the hold-to-resolution route on a dip-side member is a
  level carry.
- Columns (`A`, L 4; se20's inputs, clock: the capture's kline fetch closed before the capture start). `cr_side` (the
  member's barrier below (-1) or above (+1) spot at the origin; se20's strike map), `cr_dd24_x_side` (the signed 24 h spot
  return x side: positive when spot moved toward the member's barrier), `cr_rv_ratio` (rv 24 h / rv 7 d; the vol jump),
  `cr_barrier_wording` (reach / dip against terminal, from the title template se20 maps, NaN otherwise), `cr_dist_x_rv`
  (log distance to the barrier over rv 24 h: the standardised distance, which is the barrier probability's argument).
- Expected direction. `dir_2h`: after a drawdown the dip-side members' mids continue up for a slot (slow re-pricing of a
  barrier probability when vol jumps); the reach-side members' mids continue down by less (the skew: CH138's hedging
  premium sits on the reach side); `res_7d`: calibration by side and `cr_dist_x_rv`.
- Why not already held. se20 holds the spot returns, rv, the up / down window z and the own beta as *levels and
  returns*; not the side, not the side x return product, not the vol ratio nor the standardised distance. No token.
- Boring explanation. The ladders are quoted by bots with a barrier model, so the re-pricing is complete in the slot;
  or there are two drawdown days and the column has no variance.
- Census (counts only): side-labelled share of the about 4,800 mapped crypto rows (kill if < 50%); drawdown slots in the
  frame; the dip-side members' two-sided share on drawdown days.
- Scores: N 2, EV 2, L 4. Parents: CH118, CH138, CH89, CH30, se20. New: the drawdown as the clock, the side x return
  interaction and the standardised distance as columns.

### F. The map (parents CH240, CH245, CH244, CH243, CH242, CH250)

**CH251. The LT12 population map (counts only, k = 0): before any LT12 census, one streaming reader over a fresh ten-day
seal counts, per capture and by category and reward status, the two-member events and their complete pairs (CH245: the
mirror gaps' distribution, the same-slot correlation of the two spread innovations, the thin / sym / dense shares, the
receipt-span retention), the mixed ladders and their member counts by status (CH244: the shock share, completeness by
status, the within-event status-liquidity correlation), the fee-free traded and quote-only movers by `fee_src` (CH243: the
cell-matched control's coverage), the 2 x 2 cells (CH250), the duplicate pairs the matcher finds (CH246: precision on 50),
the movers of two-member events by who printed (CH248), and, from the label store, the split resolutions by class
(CH242). It is the cheapest census in the programme and decides whether LT12 is drafted at all.**
- What it counts. Populations, retentions and the distributions each design's gates sit on; nothing read after any
  origin; no price target; no P&L. Memory: a per-capture streaming reader with a two-capture window, < 300 MB, net lane;
  the matcher and the label-store read are separate light steps. Span: ten UTC days disjoint from LT11's census seal and
  from LT11's window (the 11-07..11-17 span proposed in section 1, or any later ten days before the LT12 seal), so every
  LT12 gate is still declared before its own census on a fresh seal (LT11's own convention with the CH240 map).
- Why it matters. Round 14's table and this round's section 0 show every killer was a count the designer had planned,
  not measured, and LT8 died on three of them; this map replaces the planning ranges of 0's counts table with
  measurements before a single LT12 design line is written. Kill criteria: none (a map); its numbers are the drafts'
  census thresholds. It also prints the two numbers this round most wants to know and cannot guess: how many two-member
  events the venue carries after the midterm, and how many traded movers pay no fee.
- Scores: N 2, EV 3 (as an enabler), L 4.

## 3. Ranked shortlist for LT12, then the engine-first families, then the rest

Rank = census survival (a complete panel, a dense state, an innovation or a crossing, a declared DE, the MDE at the *low*
planning count under the floor, the F-MDE under its cap) x originality x plausibility x money route, with round 14's
rules 1-11, round 15's 12-14, round 16's 15-17 and this round's 18-20 as hard constraints. The last column is my prior
probability that the idea passes its own census as written, before any count; a judgement, not a measurement.

| Rank | ID | One line | L | Population arithmetic (source) | Permutation structure | Primary | Planning MDE (quarter); F | Prior odds of surviving census |
|---|---|---|---|---|---|---|---|---|
| 1 | CH245 | The mirror: the twin book's spread innovation on a two-member event predicts the own next spread change; the thin book follows the dense one | 4 | 100-400 two-member events, 200-800 member units a capture (unprobed; the map's JSON holds the by-size counts); 50,400-201,600 in 21 days; DE 11 by LT11's formula, 31 by convention | event x day strata of 24 (rule 18); one offset per event; FL with S30-S32; the unrelated-pair placebo | within event-day, slope of `ds_A` on `zs_B` > 0 given the own innovation and the mirror gaps; point condition thin-follows-dense against dense-follows-thin | **0.43c / 0.22c** at DE 11 (quarter 0.86c); 0.72c / 0.36c at DE 31; F 0.68c / 0.34c a verdict at DE 11, 1.15c a label at the low end at DE 31 | **0.30** (the December count of two-member events and the same-slot mirror correlation decide; power is fine at the formula's DE and borderline at the convention's) |
| 2 | CH244 | The farmed half: after a sibling shock the unpaid members of a mixed ladder widen more than the paid ones in the same event-day | 3 | 150-600 mixed ladders of 3-10 members; 300-1,500 unrewarded member units a capture (unprobed); shock share 0.30 (planning); DE 31 | event x day strata; one offset per event; the status never permuted; FL with S26, S27, S34 | within event-day, coefficient of `shock x unrew` on `ds` > 0 given tier x shock; point condition against the tier twin | **0.85c / 0.38c** (quarter 1.70c); F 1.34c a label at the low end, a verdict at >= 540 unrewarded units a capture | **0.20** (mixed ladders may be rare; the status-liquidity correlation gate is the likeliest killer) |
| 3 | CH243 | The fee as the price of urgency: the traded-minus-quote-only continuation is larger on the fee-on panel than on the fee-free one | 3 | 100-250 fee-free traded movers a capture (8-20% of the map's 1,239; the sweep's fee-free cell is 2% of tokens); 25,200-63,000 in 21 days; DE 6.196 within, cluster-robust across | market x day strata; FL on the within-market term only (rule 20); S28, S29, S33 with the cell-matched control | panel contrast of the within-market `1[traded]` coefficient on `c` > 0; point condition on quote-only movers | **0.62c / 0.42c** (quarter 1.19c) against 0.5c; F 0.92c / 0.62c, over the cap at both ends: **engine-first by rule 7**; the live door opens at >= 160 a capture with F a label | **0.10** (conditional on CH251's count; 0 if the door stays shut) |
| 4 | CH251 | The LT12 population map (counts only; decides LT12) | 4 | n/a | n/a | n/a | n/a | n/a |
| 5 | CH242 | The venue's third price (engine-first; `p3`; the split-rate map first) | 3 | resolved non-sports markets; rules coverage 44.7%; the split share unprobed | n/a | `res_7d` calibration against se1 and the market-price reference | engine window | n/a (kill if the split share < 0.5% and no class >= 3%) |
| 6 | CH250 | Who pays the maker (engine-first; `paymaker`; the 2 x 2 map; a conditional live door) | 3 | rewarded 9,000-10,700 a capture; the fee-free cells unprobed | n/a | `ds` after traded moves by cell against se9 / se1 | engine window | n/a (kill if the fee-free cells are < 3% of rows) |
| 7 | CH248 | Who printed, this book or the other (engine-first; `movetype` spec after 11-22) | 4 | movers in two-member events 20-120 a capture (unprobed); `volume_num` missing on 83% of rows | n/a | `dir_2h` by class against se14 / se1 | engine window | n/a (kill if twin-printed < 5% of classified movers) |
| 8 | CH246 | The no-link twin (matcher and map; CH245's falsification arm; `event` spec columns) | 3 | tens to a few hundred pairs (unprobed); precision on 50 | n/a | the arm's slope inside CH245's reader where >= 105 member units a capture | 0.61c; F 0.96c at 50 pairs and DE 11 | n/a (an arm; kill if precision < 90%) |
| 9 | CH249 | The dip side after a drawdown (engine-first; `crypto` spec; crypto parameter) | 4 | about 4,800 mapped crypto rows; drawdown days unprobed | n/a | `dir_2h` and `res_7d` by side against se20 | engine window | n/a (kill if the side-labelled share < 50%) |
| 10 | CH247 | The elimination game and the futures ladder (engine-first; `gamestate` x futures; sports parameter) | 2 | 5-30 elimination games in 21 days (unprobed); 12 ESPN leagues | n/a | `dir_2h` / `dir_6h` on futures members during games | engine window | n/a (the owner's sports decision first) |

**Top 3 live-test candidates.** CH245 first because it is the one design in the round built on a stratum the venue
itself constructs (two books, one question, 24 units an event-day), with the spread as the target, the twin's own
innovation as the state, the pick-off through the mirror as a mechanism that predicts a side and an ordering, and a
placebo (the unrelated pair) and a falsification arm (the no-link twin, CH246) inside the same reader; its honest risk is
that the panel is small after the midterm and quoted by one bot that mirrors within the minute, which the same-slot
correlation will say before any count. CH244 second because the within-event contrast of the two reward halves after one
shock is the cleanest reading of what the programme does to a maker's reaction that the captures allow, and nothing in the
record tests it; its risk is that unpaid rungs are illiquid rungs, so the status contrast is a liquidity contrast unless
the tier twin absorbs it. CH243 third and conditional: the mechanism is the most original of the three (the fee as a
filter on who crosses, not as a cost) and the design clears nothing at the low planning count, so it is engine-first
unless the map finds about 160 fee-free traded movers a capture. **If the LT12 designer wants k <= 3, CH245, CH244 and
(conditionally) CH243 are the three (one pair spread slope, one ladder spread contrast, one fee-panel mid contrast; their
dependence is disclosed: CH245 and CH244 read the same event join and Holm handles it), after CH251's map, with the design
text frozen before `T_LT11` (2026-12-10T12:00Z) for the fast lane.** Expected k at census about 0.6 (0.30 + 0.20 + 0.10);
the chance that no LT12 test registers about 0.50 (0.70 x 0.80 x 0.90, treating the fates as independent, which they are
not). That is the programme's record, stated in advance, not a reason to loosen a gate.

**Top engine-first families.** `p3` (CH242: the split-rate map first, then `res_7d` columns; the one family here that
touches the engine's own label and the market-price reference, so the builder should read it before the first column),
`paymaker` (CH250: the 2 x 2 as columns after 11-18 and 11-22; the map first), the `movetype` spec column `mt_twin_printed`
(CH248, after 11-22), the `event` / `nrslack` spec columns of the mirror (CH245's levels now, the innovation after LT12's
freeze under `mirror`; CH246's `tw_*` as levels), `tilt`'s `tl_fee_free` / `tl_fee_src` (CH243's levels now; the
interaction after 11-22), the `crypto` spec columns of CH249 (the owner's crypto parameter), and `gamestate` x futures
(CH247; the owner's sports parameter; nothing before the `steam` decision). The builder's rule binds: each raises K and is
built only with a real prior; the priors here are the mechanisms, none is a replicated effect.

**Pre-registration sketches for the top 3 (written in LT11's shape so the designer can lift them; each a separate
primary in one Holm family).**

- **CH245 (the mirror).** Unit: non-sports ex-crypto member x capture in a complete two-member neg-risk event (both books
  two-sided at k - 1 and k; the two rows' `received_utc` within 120 s at both captures; sports, crypto or unknown category
  on either member excludes the pair, counted). State: `zs_B = z(spread_{B,k} - spread_{B,k-1})` (per-event census SD);
  `thin_A = 1[spread_{A,k-1} > spread_{B,k-1}]` (`sym` a reported class). Decision time: the later of the two rows'
  `received_utc` at k. Primary: expanding-past event-day-demeaned OLS of `ds_A = spread_{A,k+1} - spread_{A,k}` on `zs_B`
  with `spread_{A,k} - spread_{A,k-1}`, `g_A`, `g_B`, `spread_{A,k} - spread_{B,k}`, `hb_k`, `d_A`, `|d_A|`, `log1p liquidity`
  of both books, `z log rv24`, the two books' reward status and tier as controls; one-sided > 0; material reading
  top-against-bottom tercile. Binding point condition: the slope on `thin_A = 0` units is less than half the slope on
  `thin_A = 1` units (the difference's MDE reported; where it exceeds 1.0c the condition is reported, not binding, and the
  pooled slope stands alone). Targets: `ds_A`; M1 the stale side's touch change; M2 the mirror gaps' closing; M3 the mid
  change (reported; `informed (L1-L4)`). Clustering: CR1 on event, two-way event x UTC day and UTC day, p the largest;
  `DE_gate = max(5.0, 1 + (m_21 - 1) x 0.02)` (about 11; the convention 31 printed beside it). Planning MDE 0.43c (low) /
  0.22c (high) at 11; 0.72c / 0.36c at 31; F-MDE 0.68c / 0.34c at 11 (a verdict condition), 1.15c / 0.57c at 31 (a label
  at the low end; a verdict at `n_eff` >= 52,850, declared now). Census (fresh seal 11-07..11-17; counts only): complete
  pair units >= 93 a capture at the computed DE (the F line at the computed DE printed and binding); receipt-span
  retention >= 60%; same-slot |corr| of the two spread innovations < 0.8 in >= 50% of events with >= 24 units;
  within-event SD of `zs_B` >= 1 tick in >= 50% of events with >= 48 units; `VIF_w` <= 2.0; |corr| <= 0.5 with the tiers;
  block-gate share >= 50%; events >= 500 (unprojected); `G_eff` >= 15; pessimistic MDE and F-MDE <= 1.0c. Verdict
  condition: as declared. Cost hurdle: the thin maker's widening rule (gross); the cheaper-book route recorded as a cost
  line, not a verdict; the stale-quote taker reported against the thin book's half-spread. Extends: a pair reader over the
  rows and sidecar (no sweep). Embargo: `mirror` new, to the later of LT12's analysis commit and the lane's date; an
  attribution limit on twin-spread interactions in `event` / `nrslack`. Disclosure at the pin: LT11's two-member arm (a
  different state; blind if pinned before `T_LT11`); the `event` family's visible levels; the map's by-size counts.
- **CH244 (the farmed half).** Unit: non-sports ex-crypto member x capture in a complete event-capture pair of a mixed
  ladder (>= 1 rewarded and >= 1 unrewarded eligible member at k - 1 by `listed_carry24h_v2`), events of 3-10 eligible
  members (11+ a reported arm; two-member events excluded). State: `shock_k = 1[max_{j != i} |d_{j,k}| >= 2 x tick_e]`,
  `shock_size`, `unrew_i` (fixed within market); tested term `shock_k x unrew_i`. Decision time: the latest member row's
  `received_utc` at k. Primary: expanding-past event-day-demeaned OLS of `ds_i` on the tested term with `shock_k`,
  `shock_size`, `d_i`, `|d_i|`, the spread level, `hb_{k-1}`, bid share, rank, `log1p liquidity`, `z log rv24`, event size,
  `neg_risk_other`, tier and **tier x shock** as controls; one-sided > 0. Binding point condition: the tier x shock
  coefficient's status-free analogue (the illiquid-against-liquid contrast on shock slots) is less than half the status
  contrast. Targets: `ds_i`; M1 the bid change (< 0); M2 the mid toward the implied value (reported); M3 the traded-shock
  arm; M4 the one-status ladders' shock main effect (placebo, reported). Clustering as CH245; `DE_gate` 31 (51 for the
  uncapped arm). Planning MDE 0.85c / 0.38c; F-MDE 1.34c / 0.60c: a label at the low planning count, a verdict at >= 540
  unrewarded member units a capture (declared now). Census: unrewarded member units in mixed ladders >= 217 a capture
  (the F line printed and binding at the computed DE); completeness by status printed; shock share in [0.10, 0.80];
  within-event |corr(unrew, log1p liquidity)| <= 0.5 within and pooled; `VIF_w` <= 2.0; block-gate share >= 50%; events
  >= 500 (unprojected); `G_eff` >= 15; switchers' share printed; pessimistic MDE <= 1.0c; F-MDE printed. Cost hurdle: the
  unpaid maker's pull for one slot against the bid's subsequent change (gross); the waiting buyer reported. Extends: an
  event-join reader over the rows and sidecar with the carry store. Embargo: `mixedlad` new; the status levels inside
  `nrslack` after 11-18 only; an attribution limit on reward-status x shock interactions. Disclosure at the pin: CH233 /
  LT11 (a signed state on the same events in a different window; blind if pinned before `T_LT11`); E022's S2 (`informed
  (E022)` after 11-17, certain in both lanes).
- **CH243 (the fee as the price of urgency; conditional on the map).** Unit: non-sports ex-crypto 2 h mover x capture
  (`|d_k| >= 0.01`, `p_{k-1}` in [0.04, 0.96]) with the class traded / quote-only / unknown by the own `volume_num` keyed
  by slot. Panel: `fee_free` (flag false or rate 0 at the origin sidecar) against `fee_on`; `fee_src` recorded. Decision
  time: the row's `received_utc` at k. Primary: expanding-past market-day-demeaned OLS of `c = sign(d_k) x (mid_{k+1} -
  mid_k)` on `1[traded]` by panel, with `|d_k|`, `p_{k-1}`, `sign(d) x g(p)`, spread, `log1p liquidity`, `z log rv24`, the
  `volume_num` change, tier, hours to end and market age as controls; the tested quantity is the fee-on coefficient minus
  the fee-free coefficient, cluster-robust across events (rule 20), one-sided > 0, the fee-on comparison units drawn from
  the fee-free units' liquidity tier x category x age cells (the cell-matched control). Binding point condition: on
  quote-only movers the panel contrast is less than half the traded contrast. Targets: `c`; M1 `c_skip`; M2 the pre-03-30
  remainder within category; M3 by price bin. Clustering as CH245; `DE_gate` 6.196 within, the panel contrast's
  cluster-robust SE across events. Planning MDE 0.62c / 0.42c against 0.5c; F-MDE 0.92c / 0.62c: over the cap at both
  planning ends, so **the live door opens only if the census counts >= 160 fee-free traded movers a capture and the
  designer accepts F as a reported label in writing**; otherwise engine-first. Census: fee-free traded movers >= 160 a
  capture by `fee_src`; cell coverage >= 60%; pooled |corr(fee_free, log1p liquidity)| <= 0.5; `VIF_w` <= 2.0; block-gate
  share >= 50% on both panels; events >= 500 on the fee-free panel (unprojected); pessimistic MDE <= 0.5c; F-MDE printed.
  Cost hurdle: the maker's differential re-centring (gross); the taker's follow rule reported with its own fee added.
  Extends: a reader over the rows and sidecar. Embargo: `feeclass` only on entry; `tilt`'s `tl_fee_free` level now.
  Disclosure at the pin: E015's traded class (`informed (E015)`, certain in both lanes); round 3's and round 10's
  rejections of the fee's taker and gradient readings; se1's category one-hot as a development look at the fee's shape.

**How the families would be registered.**
- **LT12 (CH245, CH244, CH243 conditional).** One Holm family, k <= 3, on the captures and sidecar; CH251's map first;
  the fast lane (window 12-10..12-31, pin before `T_LT11`, census on a fresh seal 11-07..11-17) or the ordered lane after
  LT9; tokens `mirror`, `mixedlad`, `feeclass` filed at the freeze; the engine-first column sets built only as levels or
  after the freeze, as each entry states.
- **The arms (CH246, CH248).** CH246 inside CH245's reader as a reported arm where its count clears the spread line, with
  the matcher pinned before the census; CH248 an engine column after 11-22, no test.
- **Engine-first (CH242, CH250, CH249, CH247).** Development families under the builder's rules, in the order of the
  top-families paragraph; `p3`'s map before its first column; CH249 and CH247 after the owner's two parameter decisions.

**What is honest to say about all of them.** Sixteen rounds have read the venue's prices, books, volumes, rewards, rules,
fees and other venues' feeds, and most of what a 2-hourly capture can date has a parent. What this round adds is five
facts about the venue's own structure that turn known levels into dated, side-specific or class-specific events: one
question is sometimes two books, a fee is paid only by the one who crosses, the reward is per market inside a per-event
constraint, the resolution has a third value the label drops, and the maker's payer fixes his reaction before the print.
The one object among them that the census arithmetic favours is the two-member event, because the venue builds its
stratum and the spread is the cheapest honest target; the fee idea is the most original and the least affordable, and is
said so. Nothing here is edge until it has gone through the map, a census, frozen rules, prospective registration and an
economic check at recorded prices, and the record says that about half of such families register no test at all; the
first thing that will say whether any of it is worth a design is CH251's count of two-member events, mixed ladders and
fee-free movers on ten sealed days.

## 4. Ideas considered and rejected, and why

### 4.0 Dropped as duplicates or closed (this round's own candidates, each with the record that closes it)

| Candidate this round | Why dropped | The record |
|---|---|---|
| The mirror on *mids* (the twin book's mid innovation predicts the own next mid change in a two-member event) | closed | round 13's section 4 (the ladder lead-lag nulls L1-L4, XM1-XM6, E005 not supported); in a two-member event the twin's mid is the near-complement of the own mid, so the state is the own move (LT11's 6.1 item 7); CH245 reads the spread and keeps the mid as M3 |
| The twin's *bid* innovation on two-member events as a spread state | owned | LT11's CH233 two-member reported arm (`cl_sib` on a 2-member event is the twin's bid change); not re-proposed; CH245's state is the twin's spread innovation, disclosed as adjacent |
| The cross-book gap `ask_A + bid_B - 1` as a state (a mispricing to be closed) | a level | rule 3; it is CH245's control and M2; its distribution is CH251's line and the taker's cheaper-book route is a cost line in `COST_MODEL.md`, not a forecast |
| The bid-sum excess as an instant arbitrage on two-member events | owned | CH09 and CH233 / LT11 (M3's headroom crossing); the map counted 11.9 / 1.0 crossings a capture (rare) |
| The ask-sum shortfall carry on two-member events ("buy both sides under one") | a level carry | CH09; CH12; round 2's ladder pairs; CH115's lock-up |
| The n-member mirror (a member's claim bought as "NO of all the others") | not exact without conversion | buying every other member's NO is not the member's YES except through the NO -> YES-of-others conversion, which is CH09's object; only the two-member case is a true mirror |
| The within-market fee gradient (`rate x p(1 - p)` as a state; predictability peaks at 0.5 in fee categories) | rejected before; a level | round 10's section 4 (the fee parabola); rule 20 (a panel, never a state); `tilt`'s `tl_fee_ps` is the column |
| Zero-fee islands as the place where small taker effects become viable; fee-tag twins (a geopolitics market and a politics market on one headline) | parked before; the taker frame | round 3's section 4 (both parked: the spread still exceeds the effects; the taker route fails by construction); CH243 reads the fee as a filter on the crosser, a different mechanism, and is engine-first by its own arithmetic |
| The fee era as a within-market natural experiment (markets that gained a fee on 2026-03-30 or 07-10) | history, not a 21-day object | CH52 / CH53 own the fee history; no fee change is scheduled inside any LT12 window; `cost_regimes.FEE_ERAS` is the development object |
| The maker rebate per fill as a state (the maker's pay flips at mid prices) | a level | round 16's 4.0; `tilt`'s `tl_rebate_ps`; CH250 holds it as a column of the 2 x 2 |
| The taker-rebate tiers as a payer axis | not observable | CH52; a research account sits in no tier (`COST_MODEL.md` section 2); no sidecar field |
| Holding rewards as a third payer | collection | `holdingRewardsEnabled` is not a sidecar column (round 16's 4.0); CH21 owns the speculative version |
| The reward status *switch* of a sibling as the mixed ladder's clock | owned | CH212 / LT9 (`rwblink`: the omission as a serving-path event), CH206 (the reward start), CH215 (the scheduled end), CH19 (the cliff); CH244's clock is the siblings' move, not the programme's switch |
| The unpaid member's own print and its re-quote (the quote vacuum on an unrewarded rung) | owned | CH39 (post-print quote retreat), CH35 (quote-vacuum re-quoting); E022's S2 reward split of traded movers |
| The laggard's catch-up in a mixed ladder (the unpaid member's mid drifts to the siblings' implied value) | closed | round 13's L1-L4; CH225 (the slow sibling, sports); CH244 keeps the mid as M2 |
| The 50-50 resolution as a live primary (the cheap side's drift into a known split clause) | rule 19 | no live primary reads a resolution; CH07 owns the sports postponement clause; CH47 the dispute lottery; CH65 the ex-ante dispute predictor; CH242 is the map and the `res_7d` column |
| A three-valued `res_7d` label (0.5 paid on a split) | a learner / scoring change | DESIGN_V1 section 19 and the builder's rules; raised in CH242 as a reference-row proposal for the builder, not made here |
| The elimination as early resolution (buy NO on the eliminated futures member) | owned; lock-up | CH67 (sibling-resolution unwind), CH115 (capital lock-up), round 3's impossible-bucket residual (a CH01 footnote) |
| The in-game state on the *game* market | owned | CH231 (`gamestate`), CH23 (hope premium), CH205 (steam), CH225; CH247 is the futures join only |
| The barrier-against-terminal confusion and the reach / dip skew as tests | closed; owned | CB13-R "not testable (basis)"; CH118, CH138, CH89; CH249 is columns under the owner's crypto parameter |
| Series-level duplicates (P(by November) against P(by December) inside one `series_slugs` family) | duplicate; a text parse | round 14's 4.0; CH12; CH59; CH246 keeps only the same-claim pair and hands the matcher a precision gate |
| The mirror at the fine clock (two-member pairs on E009's panel) | unprobed; a replication lane | LT10's pairs are Polymarket-Kalshi matches, not Polymarket twins; noted in CH245, not proposed |
| A sports-only mirror (match-winner events listed as two markets) | the owner's parameter | CH245's sports arm is reported uncounted |
| The reward epoch, the daily payout, weekends | venue clocks | round 13's rule 8; round 14's 4.1 |
| Any state LT9, LT10 or LT11 tests under a new name (the band break, the pool, the omission, the fine-clock spread, the collateral weight, the bid sum, the 0.10 / 0.90 crossing) | owned | CH212-CH215, CH222-CH224, CH232-CH234 and their tokens `bandbreak`, `pool`, `rwblink`, `kxbook`, `dollarw`, `nrslack`, `bandside`; nothing here reads them |
| Anything wallet-level | sealed / frozen | E026 registered, its modules frozen to 12-07 |

### 4.1 Ideas rejected on the design rules, and why

- **Any whole-panel class state on a mid target with fewer than about 700 units a capture in its smaller class, or any
  whole-panel mid slope under about 1,700 units a capture** (0.1's table): the mirror on mids (CH245's M3), the mixed
  ladder's catch-up (CH244's M2), the fee panel's own-level drift, the duplicate pair's mid gap (CH246's level), the
  twin-printed mover's continuation (CH248: 20-120 a capture), the elimination game (CH247), the drawdown's dip side
  (CH249); each is a column, an arm or a map here.
- **Level states as primaries** (the cross-book gap, the mirror's spread gap, the fee a share, the rebate a fill, the
  minute's pay, the split rate, the overround, the mixed ladder's unrewarded share): pattern 3; each is a control, a
  column or a map.
- **Rare-event states** (the headroom crossing, the reward switch, the elimination, the drawdown day, the split
  resolution, the duplicate's listing): pattern 1; counted, never primaries.
- **Panels used as states** (rule 20): the fee class, the reward status and the 2 x 2 cell are market-level constants
  and enter only as panel contrasts of within-market quantities (CH243, CH244's `unrew`, CH250), with cluster-robust
  inference across events and the planning MDE quoted as a contrast of within-market slopes.
- **Twin states without the pair rule** (rule 18): a twin's innovation read on pairs where one book is one-sided is a
  different number at every capture; incomplete pairs are `unavailable`, never filled; the unrelated-pair placebo is
  declared or the idea is not proposed.
- **Three-valued resolutions in live tests** (rule 19): none; CH242 is engine-first and a map.
- **E015, E022, LT9, LT10 and LT11 moderators during their windows.** The fast lane is defined to avoid them; the pins
  before `T_LT11` keep CH245 and CH244 blind to LT11's arm and split; CH243's E015 informedness is certain and is said.
- **Taker routes as primaries anywhere.** 2.9-7.2c hurdles against grosses of a fraction of a cent; the cheaper-book
  route of the mirror is a cost line, not a verdict; every taker route here is reported, never a verdict.
- **Maker mark-out objects** (adverse selection judged on fills). J4-R's and CB13-T's holdouts; E025 part B; every maker
  route here is gross, no fills, with the reward formula's arithmetic as the economic check where the market is rewarded.
- **Kalshi-target money as a programme objective.** None proposed this round; CH241 stays a diagnostic companion of LT10.
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
  panel, the in-game state, the cheap side's cliff, the arb's footprint, the dollar weight of a move, the collateral tilt,
  the predictable demotion, the parent's other children, the ladder's headroom columns, the rules' class, the boundary
  map, the reverse fine clock.** CH01-CH241: not re-proposed; where an idea touches one, the parent is named and the new
  clock, population, state or join is stated (CH242 on CH07/CH47/CH65/CH03/CH128/CH199/CH207/CH221/CH239; CH243 on
  CH72/CH34/CH52/CH53/CH61/CH156/CH234; CH244 on CH16/CH45/CH183/CH209/CH19/CH10/CH39/CH233/XM3; CH245 on
  CH09/CH12/CH163/CH64/CH59/CH233/CH224/CH166; CH246 on CH64/CH59/CH13/CH163/CH10/CH245; CH247 on
  CH231/CH205/CH225/CH23/CH67/CH14; CH248 on CH156/CH234/CH245/CH66; CH249 on CH118/CH138/CH89/CH30; CH250 on
  CH16/CH45/CH72/CH183/CH209/CH235/CH243; CH251 on CH240).

## 5. Sources consulted

### 5.1 No host probe, no network, no data-dumps read this round (by instruction); what was read instead
`EXPERIMENT_LEDGER.md` (the tail from the LT7 census CC7 / CS7 entries of 10-22 through the LT11 design-draft entry of
10-23: LT8's 13.7 amendment, re-checks, seal and censuses CC8 / CS8 and closure, LT9's draft, R1, re-check, freeze and
census code phase 1, the `dispgap` / `dormant` builds and censuses, LT10's draft, R1, re-check, freeze, round-7 tokens,
code phase and merge, the `sched` / `quietbook` / `swclock` withdrawals, the CH240 map entries, the q0164c / q0116i ops
fixes); `CH240_MAP_2026-10-23.md` (in full: the mover bins, the neg-risk completeness by size, the `hb` quantiles, the
crossings); `LIVE_TESTS_11.md` at `16b294ae` (the header, section 0, section 5, the head of section 9, section 7 in full,
the two-member arm wording of 3.2 and 6.1 item 7, section 1.10) and, read-only in the LT11 worktree, its section 13 (the
R1 response table, the recomputed figures and the revised survival priors, the re-check fixes F1-F4);
`signal_engine/STATUS.md` (10-23 13:10 UTC+1: the feed, the embargo table, K, the leaderboard, the next actions);
`signal_engine/NORTH_STAR.md`; `signal_engine/CANDIDATES.md` (the idea-level notes for rounds 12-16, the "not candidates"
list, the builder table rows 1-23 and the 10-23 ~08:00Z reply); `signal_engine/DESIGN_V1.md` (the `res_7d` label row and
the label states of section 3 only); `backend/astrolabe/research_lab/calibration.py` (`parse_outcome`: the `split_50_50`
reason) and `ext_sidecar.py` (`fees_enabled`, `fee_schedule`, `created_at`); `EXECUTION_COSTS.md` (in full: the formula
sources, the cost distribution by price band, liquidity and category, the fee-free cell); `COST_MODEL.md` section 2
(fees, rebates, the two-sided rule as quoted, the history); `NEW_STREAMS_2026-10-19.md` sections 1-2 (the host's streams,
the four keyless streams and their fields); `CREATIVE_HYPOTHESES_2026-10-30.md` (round 16 in full: the brief, 0.1-0.2, the
facts, CH232-CH241, the shortlist and sketches, 4.0-4.1, 5); `-29.md` (round 15's 0.2 rules 12-14 and scoring
paragraphs); `-28.md` (round 14's 0.2 rules 1-11 and facts); `-24.md` (round 10's section 4: the fee parabola); `-17.md`
(round 3's section 4: fee-tag twins, zero-fee islands, the impossible-bucket residual); the lead sentences of CH01-CH241
from all sixteen rounds (for the duplicates table and the parents named), and the lead paragraphs of CH07, CH09, CH10,
CH11, CH12, CH13, CH16, CH23, CH34, CH35, CH39, CH45, CH47, CH52, CH53, CH59, CH61, CH64, CH65, CH66, CH67, CH72, CH115,
CH118, CH128, CH130, CH138, CH156, CH163, CH183, CH199, CH207, CH209, CH221, CH225, CH231. Still no host probe, no network
and no data-dumps read. Every count is as the named document states it on 2026-10-23; nothing was recomputed except the
planning MDEs from round 14's stated formula.

### 5.2 External literature (named, not fetched)
Hasbrouck 1995 (one security, many markets: information shares and the law of one price across books); Glosten and
Milgrom 1985 (the maker's update on trades); Kyle 1985 (the cost of informed trading); Foucault, Kadan and Kandel 2005
(the cost of a resting limit order and the maker's choice of side); Colliard and Foucault 2012 (trading fees and
efficiency in limit order markets: a fee changes who crosses); Malinova and Park 2015 (make / take fees and market
quality: who the subsidy reaches); Spence 1973 (a cost that only some are willing to pay is a signal); the conversion
mechanics of neg-risk events and the UMA 50-50 resolution as CH09 and CH47 state them from the venue's documentation.
