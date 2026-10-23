# Live tests 11 (LT11): the price of the quote (CH234, CH233, CH232), DRAFT pre-registrations

**Status: DRAFT, NOT FROZEN. No challenger review yet (R1 not run), not registered, nothing counted, no code, no seal, no
census run. E-numbers unassigned.** Drafted 2026-10-23 (about 12:30-14:30Z) on branch `feat/live-tests-11` from the
`chore/arepo-claude-setup` tip `2b33d60b`, a design-only first commit like the first commits of LT3-LT10. LT11 takes the next
free E-numbers at its own registration, in the order CH234, CH233, CH232 (round 16's rank order). If every test drops at its
census, LT11 is not registered (recorded in the ledger; nothing counted). Before registration this needs, in order:
1. a challenger review (`science-reviewer`, R1) of this file, a written response, and any re-check;
2. the **design-text freeze commit** (1.1) **before 2026-11-14T12:00:00Z and before `T_E015`** (the fast lane; otherwise the
   ordered lane of 1.1 applies), with the venue's reward-rule page re-read and recorded in the same commit (1.4.2);
3. the code (section 8), with a freeze check of the census and size-check code against sections 1.8, 1.8.1 and 7, on
   synthetic data only;
4. the census inputs' restore and seal (section 7), each once, after the freeze and after the census span has ended;
5. the counts-only census (section 7), once, which fixes k and every census-fixed spec value;
6. the size check at >= 2,000 worlds on the code to be pinned, through the census-fixed values (1.8);
7. a host dry run of the reader with peak RSS measured (8.2);
8. the engine embargo entries of section 9 verified in `config.EMBARGO` and `signal_engine/CANDIDATES.md`; the `SPEC_SHA256`
   and `code_sha256` pins; the ledger entry, at least 24 h before `REGISTERED_UTC` (8.4).
Until the pin exists, every line a reader writes is `prospective_unregistered` by construction.

This is research tooling. AREPO never trades. No edge, calibration, profitability or tradability claim exists or is implied.
Every count quoted from round 16, the CH240 map, the ledger or the cost model is a **counts-only operational or development
figure**. Every MDE here is a **planning estimate** built on stated assumptions, not a measurement. Nothing here read a price
after an origin, an outcome, a target, a prediction line, a census output or a P&L. No host, network, `ssh`, `data-dumps` or
evidence-JSON read was used to write it (reads listed in 10).

**The CH240 map and what it informed (declared up front).** `CH240_MAP_2026-10-23.md` (q0680, captures 2026-10-16..10-23,
counts only, k = 0, uncounted) counted populations, not effects: it read captures k - 1 and k only and **no target, no price
change after an origin and no P&L**. It was read before this file was written, so every gate below that sits near a map
number is *informed by the map*; section 10.1 lists each such choice. The map's span `[10-16, 10-23)` is disjoint from LT11's
census span `[10-28, 11-07)` (7), so every LT11 gate is still declared before its own census on a fresh seal. The map is a
planning input only; nothing in it enters a census, the size check or an analysis.

Source ideas: `CREATIVE_HYPOTHESES_2026-10-30.md` (round 16) section 3, ranks 1-3 and their pre-registration sketches:
**CH234** (the dollar weight of a move), **CH233** (the arb's footprint) and **CH232** (the cheap side's cliff), taken in the
round's own recommendation ("if the LT11 designer wants k = 3, CH234, CH233 and CH232 are the three ... after CH240's map").
The design is written to round 14's rules 1-11, round 15's 12-14 and round 16's 15-17, to LT4's lessons L1-L15 and the later
rulings LT7-LT10 carry (1.0). Every design change from the round's sketches is listed with its reason in section 6; all were
made before any LT11 data, several after the map (marked).

## 0. Summary

| Handle | Idea | Hypothesis (direction) | Population and unit | Primary | Planning MDE: low / high; quarter of low; F-MDE (all planning) | Floor |
|---|---|---|---|---|---|---|
| **CH234** | the dollar weight of a move | Within market, on traded 2 h movers, continuation over (k, k + 1] rises with the **interaction of the move's collateral weight `w` and its size `|d|`** (the dollars behind the move), both main effects, the level drift by price bin and the known-factor block held fixed (one-sided > 0); the quote-only movers' slope is less than half the traded slope (binding point condition) | non-sports ex-crypto market x capture with `|d_k| >= 0.01`, `p_{k-1}` in [0.04, 0.96], **traded** (`volume_num` rose, both values present); quote-only movers the twin; `volume_num` missing or decreasing a **third class, counted, never classed** | expanding-past market-demeaned OLS of `c = sign(d_k) x (mid_{k+1} - mid_k)` on the centred product `xw = z(w) x z(|d|)`; **block Freedman-Lane gate (market)**; **far-future F binding**; twin point condition binding | at the map count less exclusions (900-1,150 a capture), DE 6.196: **0.31c / 0.27c**; quarter 0.61c; **F 0.46c / 0.40c**; at a projected DE 10: 0.39c / 0.34c, **F 0.58c / 0.51c (fails 0.5c)** | 0.5c (2 h mid) |
| **CH233** | the arb's footprint | Within market, a neg-risk member's spread change over (k, k + 1] rises with the **siblings' YES bid-sum rise** over (k - 1, k] (the event's bid headroom `1 - sum of bids` closing because of the other members), the member's own move, the headroom level and the known-factor block held fixed (one-sided > 0); the siblings' **ask-sum** slope is less than half the bid-sum slope (binding point condition) | non-sports ex-crypto neg-risk member x capture in a **complete** event-capture pair (every eligible member two-sided at k - 1 and k), events with **3-10** eligible members (2-member and 11+ events reported arms) | expanding-past market-demeaned OLS of `ds = spread_{k+1} - spread_k` on `z cl_sib`; **event-phase block Freedman-Lane gate (one offset per event)**; **far-future F binding**; ask twin point condition binding | 4,000-8,000 complete member units a capture (planning, from the map's event counts), DE 31: **0.17c / 0.12c**; quarter 0.35c; **F 0.28c / 0.19c**; at DE 51: 0.22c / 0.16c, F 0.35c / 0.25c | 1.0c (spread) |
| **CH232** | the cheap side's cliff | Within market, on rewarded markets whose mid at k - 1 sat in the outward approach zone (`[0.10, 0.14]` or `[0.86, 0.90]`), the spread change over (k, k + 1] is larger after the market-day's **first outward crossing** of 0.10 / 0.90 at (k - 1, k] than after no crossing, the move, its size, the mid's level and the known-factor block held fixed (one-sided > 0); the unrewarded panel's crossing coefficient is less than half the rewarded one (binding point condition) | rewarded (`listed_carry24h_v2`) non-sports ex-crypto market x capture in the approach zone; tick-coincident crossings excluded and counted | expanding-past market-demeaned OLS of `ds` on `xo` with `xr` (later crossings of the same UTC day) as a control; **block Freedman-Lane gate (market)**; **far-future F binding**; panel point condition binding | 50-69 counted crossings and 500-1,000 zone units a capture (planning), DE 31, `VIF_w` 1.3: **0.69c / 0.58c**; quarter 1.38c; **F 1.09c / 0.92c (fails 1.0c at the low end)**; at `VIF_w` 2.5: F 1.51c / 1.27c; at a computed DE of 15 and `VIF_w` 1.3: F 0.76c / 0.64c | 1.0c (spread) |

- **Family:** one Holm family over the k surviving primaries, one-sided, familywise alpha 0.05, separate from E009-E011, LT2
  (E012-E014), LT3 (E015), LT4 (E022), LT5-LT10, E025 and E026. **Provisional k <= 3.** A test whose census gate fails is
  dropped *before* registration, uncounted; k is the number that survive, fixed in the spec (`k_tests`) at registration and
  never changed. A primary that is unavailable or fails its gate enters Holm with p = 1. No replacement test is added after
  a census drop, and a census drop is final in both lanes (1.1).
- **Window (proposed; the fast lane, 1.1):** whole captures with start in `[REGISTERED_UTC, END_UTC)`, 21 days,
  **`REGISTERED_UTC = 2026-11-18T00:00:00Z`**, `END_UTC = 2026-12-09T00:00:00Z`; single analysis on or after
  **2026-12-10T12:00:00Z**. Census on a fresh seal of `[2026-10-28T00:00Z, 2026-11-07T00:00Z)`. The window lies after E015's
  and E022's windows and before LT9's (from 2026-12-30 at the earliest); it overlaps LT10 (fine clock) and E026 (wallets) in
  time only.
- **Freeze early.** Design-text freeze before 2026-11-14T12:00Z and before `T_E015`, so the traded class (E015's anatomy) and
  the reward control (E022's S2 split) are fixed blind to both results. A freeze after either moves LT11 to the ordered lane.
- **Expected outcome, declared now (honest prior odds; the designer's judgement, not measurements).** **CH234** has the
  count (the map's 1,239 traded movers a capture against a count gate of 745) but its binding F-MDE gate sits at the edge:
  it passes at E022's design effect (6.196) and fails at the low planning count at the design effect its larger population
  may compute (7-10, a projection, 2.5); `VIF_w` of the centred product and the differential-missingness gate on `volume_num` are the other
  risks. Census **0.35**. **CH233** has power to spare (F-MDE about a quarter of the floor); the map settled completeness
  (0.85-1.00 of events of 3-10 members on the rewarded panel) and the working range (`hb` within two ticks of zero on 12.6%
  of complete event-captures); the risks left are the correlation and `VIF_w` gates against the member's own move and
  liquidity, and the block-gate share. Census **0.50**. **CH232** has the crossings (79 rewarded outward first crossings a
  capture on the map, 73 ex-tick) but loses some to the causal approach-zone population (6.1 item 1), and its binding F-MDE
  gate fails at the planning DE 31 unless `VIF_w` stays near 1.3 or the computed DE is near 15. Census **0.20**. **Expected
  k at census about 1.05 (0 to 3); the chance that no LT11 test registers is about 0.26** (0.65 x 0.50 x 0.80, treating the
  fates as independent, which they are not: all three read the same captures and sidecars); **the expected number of valid
  verdicts is about 0.4** (binding leak worlds may fail, 1.8). Every taker check is expected to be "not shown" (1.10).
- **No LT11 result can satisfy the programme's economic check** (1.10): every maker route is gross and without fills; every
  taker cell is a cost rule expected "not shown". A Supported LT11 primary is an exploratory prospective finding, never an edge.

## 1. Common rules

### 1.0 Lessons carried over (binding from the first draft)

LT4's lessons **L1-L15** (`LIVE_TESTS_4.md` 1.0), LT7's table of later rulings (`LIVE_TESTS_7.md` 1.0), LT8's, LT9's and
LT10's 1.0 lists apply unchanged where they are not stream-specific: exact `%.17g` writes and round-trip reads; NaN refusals in
a pinned spec; sealed census inputs re-hashed (refuse on mismatch); slots and origins built **from the seal**, never from a
local scan; a pessimistic planning-MDE gate in every census with `max(declared, design)` and `sqrt(max(1, VIF_w))`; a
simulated size check at >= 2,000 worlds with the limit 0.05 + 1.645 sqrt(0.0475 / worlds) = 0.058; dry-run guards; spec and
code pins on every frozen line; write-once per-capture series and status files; clustering by event, event x UTC day and UTC
day with p the largest; Holm over k counted once; economics never changes a verdict; readers at the capture cadence; an
internal run lock; residual-IQR identification gates; Freedman-Lane gates only with `DE_gate = max(floor, 1 + (m_21 - 1) x
0.02)` (`m_21` the projected size-weighted mean cluster size by event); the block (circular-shift) gate for rolling or
persistent states; the liquidity-tier gate; seal completeness and the seal's own slot assignment; memory planned from a
measurement with a ladder; `T_X` keyed conditions; the pinned sports and crypto classifiers; the design-text freeze; the
lag-slot loader for every later-slot census read; vendoring, not import; LT7's one-rule F; `r_gate = max(r_w, r_pool)`; count
gates on gross projected counts with the effective share inside the MDE only (LT9 7); zero-filled correlations refused; the
null taxonomy of `clob_rewards` (LT8); **whether F binds is fixed per test now, by design, never by a census count** (LT9 R1
fix 1); and LT7 13.7's `listed_carry24h_v2` for every reward status (LT9 1.4.1).

**Census deaths that set LT11's expectations (counts only; round 14 0.1, round 16 0, the ledger).** LT5, LT6 and LT7 closed
with no test; LT8 closed with no test on 2026-10-23 (CC8: CH204's scheduled markets 3.35 a capture against 1,200, events 120
against 500, cap and block shares; CS8: CH203's projected units 431,399 against 504,000 with every power gate passed, CH202's
held share 0.067 against 0.15). E022 alone survived (DE 6.196, `m_21` 260.8). The lessons applied here: (i) the MDE gate and
the count gate both kill, so every test states **the count at which its binding gate passes** (0, 2-4) and its count gate is
set at or above that line, never below; (ii) a share gate on a quantity nobody has measured kills as surely as a count (CH202),
so every share gate here is either measured by the map (and the margin stated) or flagged unprobed; (iii) whole-panel
populations have whole-panel design effects, and a population several times E022's computes a larger `m_21` (2.2 projects
it), so DE 6.196 is quoted as the optimistic end for CH234, not the plan; (iv) **a field's semantics are declared before any
count**: `volume_num` presence (2.3), the neg-risk member set (3.2) and the reward-rule reading (1.4.2).

Round 16's design rules (`CREATIVE_HYPOTHESES_2026-10-30.md` 0.2, with rounds 14-15's 1-14) map onto LT11 as follows:

| Rule | LT11 rule |
|---|---|
| 1. Panel-complete units | every unit is a market x capture of the complete captures and their sidecar; no sample, sweep, monitor or external unit in any primary |
| 2. Dense states | CH234's product is continuous on every traded mover; CH233's sibling innovation on every complete member-capture; CH232's crossing is a per-interval event on every approach-zone unit |
| 3. Innovations and crossings, never levels | CH234 the move at (k - 1, k], CH233 the siblings' bid-sum change, CH232 a crossing; the levels (`p`, `hb_{k-1}`, the spread) are controls |
| 4. Look-backs <= 12 slots | `rv24*` and the 24 h change read 12 slots; the carry window `[k-11, k]`; "first crossing of the UTC day" reads only earlier slots of the same day |
| 5. Field semantics first | 2.3 (`volume_num`), 3.2 (members, completeness, the bid of a two-sided row), 4.2 (crossing, tick coincidence), 1.4.1 (reward status) |
| 6. A stream only where it covers its population | captures and sidecars cover every unit; sweeps are read only for CH232's reported M3 |
| 7. DE and the kill line | planning DE 6.196 / 10 (CH234), 31 / 51 (CH233), 31 / 15 (CH232); census `DE_gate = max(floor, computed)`, floors 6.196, 5.0, 5.0; each kill line stated |
| 8. Floors | 0.5c (CH234's 2 h mid), 1.0c (CH233's and CH232's spread targets); the F-MDE cap equals the floor |
| 9. Census on a fresh seal | `[2026-10-28, 2026-11-07)`, disjoint from the map's span (7) |
| 10. Pin early, name what was seen | the CH240 map, the round's planning counts and the `event` family's visible level scores are disclosed (10) |
| 11. Maker-side money routes | every primary route is maker-side, gross, no fills; taker cells reported (1.10) |
| 15. The rule-boundary clock | CH232's crossing is read from the captures' own mids at k - 1 and k; first crossing of the market-day is the state, later crossings a declared class; the rule's page is re-read at the freeze and fixes only the side of M1 (1.4.2, 6.1 item 3) |
| 16. Event-join completeness | CH233 is defined only on complete event-capture pairs; incomplete ones are `unavailable`, counted, never filled; the census drops the test below 60% completeness (3.6) |
| 17. Mover states vary beyond the sign | CH234's tested term is a centred product with both main effects and `sign(d) x bin` controls; `VIF_w` and residual-IQR gates bind (2.6) |

### 1.1 Registration, window, single analysis
- **Fast lane (proposed).** `REGISTERED_UTC` is the first 00:00Z that is **(a)** at least 24 h after the LT11 registration
  commit (spec pin plus ledger entry), **(b)** after `END_UTC` of E022 (2026-11-16T00:00Z, LT4) plus 24 h, and **(c)** never
  earlier than **2026-11-18T00:00Z**. Proposed value **2026-11-18T00:00Z**; `END_UTC = REGISTERED_UTC + 21 d` =
  2026-12-09T00:00Z; analysis date `END_UTC + 36 h` = 2026-12-10T12:00Z. The fast lane requires the design-text freeze before
  **2026-11-14T12:00:00Z and before `T_E015`**, and the registration commit before **2026-11-17T00:00:00Z** (so that (a) holds
  for 11-18). **If the registration commit is not made by 2026-11-17T00:00Z, the fast lane lapses** (recorded) and the ordered
  lane applies; the fast lane never slides day by day, because a later start would overlap LT9's install and the year-end.
- **Ordered lane (fallback, declared now).** If the freeze misses its deadline or the fast lane lapses: `REGISTERED_UTC` = the
  first 00:00Z at least 24 h after LT9's `END_UTC` (if LT9 registers; else after LT9's recorded drop) and after the LT11
  registration commit, never before 2027-01-21T00:00Z; 21 days; single analysis >= 36 h after the end. **The ordered lane
  needs a fresh seal and census** of the 10 UTC days ending at least 4 days before the registration commit, with every gate
  and value rule of section 7 unchanged; if the fast-lane census already ran, its outputs become descriptive, **every test it
  dropped stays dropped** (no second census for a dropped test), and the new census can only drop more. A freeze after
  `T_E015` labels CH234 *informed (E015)*; a freeze after `T_E022` labels CH232 *informed (E022)* (adjacent analyses below).
- **Why the fast lane.** (1) No registered or drafted test reads the captures' crossing, neg-risk sum or collateral states in
  2026-11-18..12-09: E022's window ends 2026-11-16, LT9's starts no earlier than 2026-12-30 (LIVE_TESTS_9.md 1.1 (c')), LT10
  reads the fine-clock stream, E026 the wallet stream. (2) The host's capture-reader slot is free (LT9's reader installs in
  late December). (3) Round 16's rule: an earlier, separately registered family with its own Holm family beats a three-month
  wait, provided the design is frozen blind to the adjacent analyses. **Costs disclosed:** the census span straddles the US
  daylight-saving change (2026-11-01) and the window is on winter time; the window holds US Thanksgiving (2026-11-26); the
  census, size check, dry run and pin must fit in 2026-11-07..11-16 (about nine days) next to E011's and LT2's analyses
  (11-11, 11-13) and E015's (11-15), under the memory-heavy-jobs rule (8.2).
- **Boundary.** A unit's oldest state input is capture k - 1 (CH234's `d_k`, CH233's `cl_sib`, CH232's crossing), so the
  first origin is the first capture whose capture k - 1 starts at or after `REGISTERED_UTC` (proposed 2026-11-18T02:31Z);
  the 00:31Z capture gives no unit and is counted `lt11_boundary`. Look-backs (`rv24*`, the 24 h change, the carry window,
  CH232's earlier-slots-of-the-day rule) may read captures before `REGISTERED_UTC` (counted `pre_window_source`); they are not
  states of any other test's window. The last origin is the last capture starting before `END_UTC`; its targets (k + 1) and
  twins (k + 3) start after `END_UTC` and are read.
- **Design-text freeze.** After the challenger's acceptance (R1 and any re-check), a commit records the sha256 of this file in
  the ledger. From then on the text of a test changes only by census-fixed values named in section 7 and by code-freeze-check
  fixes that change no state, unit, target, estimator, gate, threshold or verdict rule. `T_X` = the earlier of X's analysis job
  start (queue or shell log) and X's analysis commit. Adjacent analyses:

  | Test | Adjacent analysis (`T_X`) | Why adjacent | Consequence |
  |---|---|---|---|
  | CH234 | **E015** (`T_E015`, proposed 2026-11-15T12Z) | E015 tests the move's anatomy (traded, quote-only, parallel); CH234 uses its traded class as a population rule and its quote-only class as the twin | freeze not before `T_E015`: ordered lane and label *informed (E015)*; census-fixed CH234 values committed after `T_E015` (they are mechanical counts): disclosed, no label (ambiguity A3) |
  | CH232 | **E022** (`T_E022`, proposed 2026-11-17T12Z) | E022's S2 splits hollow liquidity by reward status on the same `clob_rewards` field | freeze not before `T_E022`: label *informed (E022)*; the fast-lane pin is before `T_E022` by construction |
  | CH233 | **E005** (complete), HB1 XM1-XM3 (complete), the engine's `event` family (se8 / se10, visible since 2026-10-22T12:00Z) | the neg-risk mid-sum record and visible level scores | disclosed (10); no label (the results were known before this draft) |
  | CH232 | **LT9 CH213** (window from 2026-12-30) | the same rewarded panel and `listed_carry24h_v2` | no time overlap; LT11's analysis (12-10) precedes LT9's pin, LT9's design text is frozen (11fee7a0) and its census runs in mid-November, before any LT11 result; disclosed to LT9 (9) |
  | all | LT10 (window 2026-11-10..12-01), E026 (to 2026-12-07) | time only | different streams; no pooling |

- **Fixed end, no extension** (LT4-LT10 practice). Shortfalls (capture gaps, sidecar outages) are labelled (*underpowered*,
  Unavailable), never extended.
- **One analysis**, once, on or after the analysis date (`run_live_tests11.py analyze` refuses before it; `--out` refuses to
  overwrite). No interim look at any outcome (1.6). **Effective start** = max(`REGISTERED_UTC`, the first capture processed by
  the reader at the pinned commit); the analysis keeps only lines whose `spec_sha` and `code_sha` equal the pins and whose role
  is `prospective_confirmation`.
- **Time of year (disclosed).** The census span (10-28..11-07) holds the US daylight-saving change (11-01; UK changed 10-25);
  the window is on winter time on both sides. The hour-of-day dummies are estimated in the window; the census uses hours only
  for the venue-clock gates (<= 50% of a state's events in one slot of day), which a one-hour shift does not change. US
  Thanksgiving (2026-11-26) is in the window: a sensitivity without origins in `[2026-11-26T00:00Z, 2026-11-28T00:00Z)` is
  reported and never changes a verdict (*holiday-sensitive* label). Reward programmes may be re-rated on 2026-12-01: a
  sensitivity without origins on that UTC day is reported (*month-start-sensitive*).

### 1.2 Streams read (all already written by the host's pass; nothing new is fetched; no new collector)
- **Complete-universe captures** `snapshots/<id>/rows.csv.gz` (every 2 h at :31; `state=complete` only): `bid`, `ask`,
  `spread`, `last_trade_price`, `volume24hr`, `liquidity`, `chg_1h` (and `chg_1d`, `chg_1w` if the header pre-check finds
  them), `end_date`, `event_id`, `neg_risk`, `neg_risk_market_id`, `neg_risk_other`, `event_neg_risk_augmented`, `closed`,
  `active`, `received_utc`, and the manifest's capture start time (field names as `extract.py` writes them; round 16 fact 6).
- **Sidecar** `rows_ext.csv.gz` (`ext_sidecar.py`): `received_utc`, `fee_type`, `fee_category`, `fee_schedule`,
  `fees_enabled`, `series_slugs`, `order_price_min_tick_size`, `rewards_min_size`, `rewards_max_spread`, `clob_rewards`,
  `volume_num`, `accepting_orders`, `event_ids`. A missing sidecar row sets sports, crypto and tick unknown, the reward status
  NaN and `volume_num` missing (counted `sidecar_missing`; 1.5).
- **CLOB reward feed** `reward_params/<capture_id>/` (as LT9 1.2, one feed clock: the last usable feed capture before capture
  k's start): used only for CH232's *CLOB-disagreement* sensitivity and for economics (the CLOB rate), never for a state.
- **Book sweep 1** `book_sweeps/<id>/` (`series_index` 0): read **only** for CH232's reported M3 (the dear and cheap sides'
  1c / 5c depth at passes k and k + 1), never for a state, control, target or gate.
- **Not read:** trade samples, the live large-trade monitor, `cross_venue_live/`, `xv_quotes/`, `surprise_live/`, the stores
  `live_tests2/` .. `live_tests10/`, CB8-H holders, the CB16-CB18, E025 and E026 stores, the keyless streams, the signal
  engine's `quotes/`, `features/`, `aux/` and `predictions/`, the CH240 map's output, and Gamma outcome fields of any kind.

### 1.3 Clocks, slots and decision times
- **Slots:** as LT3-LT9 (`grid0 = 2026-10-01T00:31Z`, 2 h, tolerance 30 min, first complete capture of a slot). "k - j" and
  "k + h" are slots, not file order. A missing slot leaves every quantity that needs it NaN (counted), never interpolated.
  Slot of day `sigma(i) = i mod 12`; the UTC day of a capture is the UTC date of its manifest start.
- **Decision time (all three):** **capture k's last row receipt** (the largest `received_utc` over capture k's complete rows
  and sidecar rows), because CH233's state reads other markets' rows of capture k and the member cap and CH232's panel rule
  read capture k's event membership. States read captures k - 1 and k, their sidecars and the 12-slot look-back. **Targets
  start at capture k + 1.**
- **Late rule:** as LT4 1.3: a frozen file is written before capture k + 1's start, else `.late`, units lost and counted;
  *late-loss* above 2% of a test's origin files.
- **Twins (F) and post-decision readings** read captures k + 2 and k + 3 (twin states) and, for CH232's M3 only, sweep 1 of
  passes k and k + 1. They are readings, never states; the unit builders do not read them (causality test, 8.3).

### 1.4 Shared origin-side eligibility
LT4 1.4 items 1-7, applied in order and counted (LT3's `move_join` and `classify`, vendored), at captures k - 1 and k: binary,
open and active; two-sided at both (bid > 0 and ask < 1 on the row); tight (spread <= 0.10 at both); the mid in the test's band
(CH234: `p_{k-1}` in [0.04, 0.96]; CH233: any; CH232: its approach zone, 4.2). As-of end unknown or > `t` + 3 h; **F-arm
membership** needs the end unknown or > `t` + 7 h (the twin reads capture k + 3); a unit failing it stays in the primary and
is out of the F arm (`f_end_short`). Category by `cb17_census.is_sports_sidecar` (non-sports primaries; the sports arm
reported, uncounted); crypto excluded by the pinned classifier (`fee_category` contains `crypto` after strip and casefold;
unknown counted and treated as crypto); category is a spec parameter (`scope: non_sports_ex_crypto`, the default, fixed at the
freeze unless an owner decision is recorded before it). One row per `condition_id`. **Series-family rule (census-fixed):** if
the census top series family holds > 40% of a test's primary population, it is excluded from that primary
(`<test>.exclude_family`) and the MDE gates recomputed. **Member cap:** `n_members(e, k)` = distinct markets of Gamma event
`e` among capture k's complete rows that are binary, open and active (a market without `event_id` is its own event); CH234
and CH232 keep units with `n_members <= 10` (larger events: the reported *ladder arm*); CH233's member rule is its own (3.2).
**Tick:** `order_price_min_tick_size` equal at k - 1 and k, else the unit is excluded (`tick_changed`, counted); the tick
enters as a control (`1[tick = 0.001]`).

### 1.4.1 Reward status (CH232's panel; a control and an economics input elsewhere)
Every LT11 `rewarded` flag, band `v` (`rewards_max_spread`) and daily rate is **`listed_carry24h_v2` exactly as
`LIVE_TESTS_7.md` 13.7 and its erratum define it**, vendored from `live_tests7.py` (sha256 `e1c5c0c6…`, as LT9 8.1), at
capture k with the 12-slot carry window `[k-11, k]`; nothing after k is read; malformed text or a missing sidecar row is NaN
(excluded, counted, LT8's null taxonomy). **CH232's panel is fixed at the market's first unit** in the window (reward panel
`rewarded = 1`, control panel `rewarded = 0`); later units of the opposite status are excluded (`panel_switched`, counted), as
LT9 CH213. CH234 and CH233 carry `rewarded_k` as a control (NaN excluded and counted).

### 1.4.2 The reward rule's reading (rule 15), fixed before the census
AREPO's documents disagree on the rule: `COST_MODEL.md` 2 and `MAKER_REWARDS_STUDY.md` quote the venue's page as "two-sided
quoting is required outside [0.10, 0.90]" (inside, a one-sided quote also scores at the reduced weight `c = 3.0` sets;
outside, only two-sided quoting scores), while CH71 and round 14's rule 11 record the reverse as the usual reading. **The
primary's sign does not depend on the reading** (6.1 item 3): under the documented reading an outward crossing removes the
score of every one-sided quote on the cheap side, so one-sided farmers leave it or must add the dear side (which costs about
nine times the collateral a share); under the reverse reading it frees the farmers to drop the dear side. In both readings
the cheapest response of a quote-minute maximiser is to withdraw a side, so the predicted spread change at an outward crossing
is **> 0**. **The reading fixes only the side of M1** (which touch retreats): the cheap side under the documented reading, the
dear side under the reverse reading. The venue's page is re-read **in the design-text freeze commit** (not at the pin), the
quoted sentence and its retrieval time recorded in the ledger, and M1's side set from it; if the page states neither reading,
M1 is reported for both sides and is a two-row table. No re-reading after the freeze changes anything.

### 1.5 Missing data and per-capture status (never imputed)
As LT4 1.5 and LT9 1.5: every frozen unit receives exactly one status at every target slot (`two_sided`, `one_sided`,
`closed_flag`, `absent`, `capture_missing`), write-once and online; only `two_sided` has a target. The attrition rule (|a_1 -
a_0| > 2 pp between the contrasted classes or the top and bottom terciles of the tested term gives *attrition-differential*
and Lee-type bounds) never changes a verdict. A required input missing at the origin produces no unit and is counted
(`sidecar_missing`, `reward_unparseable`, `.noprev`, `event_incomplete`, `vnum_unknown`). A missing control or state is NaN
(excluded, counted), never 0. **Declared indicator-pair exceptions only:** an unknown `end_date` enters log hours-to-end as 0
with `hte_unknown`; a missing `volume24hr` enters `log1p volume24hr` as 0 with `vol_missing`; a missing `chg_1h` (or 6 h / 24 h
own change, slot missing) enters as 0 with `mom_missing`; every primary is also re-estimated on units with all of them present
(reported). **`volume_num` is never an indicator-pair exception:** for CH234 it defines the population (2.3); elsewhere it is not
used. A missing F state leaves the unit in the primary and out of the F arm (counted).

### 1.6 What is not looked at before the analysis date
No mid, spread, move, target, P&L, regression or plot from `live_tests11/` files, or from in-window captures, sidecars, sweeps
or feed captures, for these hypotheses. Only `run_live_tests11.py ops-stats` may run (file, line, role, class, panel and status
counts; reads no price, spread, volume or depth column, enforced by a unit test). No change of thresholds, scales, populations,
estimators or k after registration; operational fixes are logged as deviations. **No LT11 designer, coder or reviewer reads
E015's, E022's, LT9's or LT10's analysis outputs before the pin, nor LT9's or LT10's census outputs beyond the counts this file
cites (none), except to verify a hash.** **Census-span data:** no LT11 designer, coder or reviewer opens any capture, sidecar,
sweep or feed capture of the census inputs (the span, its look-back and its three lag slots, section 7) before the seal commit,
except the header pre-check (headers only, no rows) and the restore's byte and sha256 checks; development and tests use
synthetic data or files outside those slots (the CH240 map's span is outside them). After LT9's or LT10's census commit, any
change to an LT11 gate, filter, planning count or expected fate is labelled *informed (LT9 census)* or *informed (LT10
census)* on the affected test and recorded with its reason.

### 1.7 Estimators and inference
- **Sign convention.** Every tested coefficient is predicted > 0 (CH234 `xw`, CH233 `z cl_sib`, CH232 `xo`); every MDE is a
  magnitude.
- **Expanding-past demeaning** (LT2-LT10): every regressor minus the mean of the market's strictly earlier units of the same
  test; target raw; the first unit of each market drops.
- **Known-factor block `K` (every primary; the champion's two families as the captures carry them; DESIGN_V1 section 3).**
  *Market state:* the mid at k (`p_k`), the spread at k, `log1p liquidity`, `log1p volume24hr` (with `vol_missing`), log hours
  to end (with `hte_unknown`), `1[tick = 0.001]`, `z log rv24*` (12 slots), `neg_risk`, `rewarded_k` (CH234, CH233), the
  non-sports `fee_category` dummies, 11 slot-of-day dummies. *Momentum:* the own 2 h change `d_k` (each test's own form), the own
  6 h and 24 h changes (`mid_k - mid_{k-3}`, `mid_k - mid_{k-12}`, with `mom_missing`), the venue's `chg_1h` (and `chg_1d`,
  `chg_1w` if present). Market age is not on the rows and is omitted (listed at the code freeze; ambiguity A9). A Supported
  primary is therefore a statement beyond these columns as the captures carry them, not beyond the engine's fitted models.
- **Standard errors and p (L10):** CR1 on event (Gamma `event_id`, else the market), two-way event x UTC day, and UTC day.
  One-sided **p = max(p_event on t with `G_event - 1` df, p_two-way normal, p_day on t with `G_day - 1` df)**. **Sparse class
  (CH232):** the event t uses `min(G_event, G_minor) - 1` df, `G_minor` the number of events holding at least one counted
  crossing. The conservative 95% CI is the hull of a 2,000-draw event bootstrap and the three Wald intervals.
- **Dependence sensitivities (reported, never the verdict):** event x two-day block CR1; the **fixture-day group**
  (`DEPENDENCE_CLUSTERING_ANALYSIS.md`'s `fixture_day_sidecar`) in place of the event; the market-deduplicated estimate (the
  first unit of each market-day only).
- **Overlapping targets and rolling states.** CH234's `d_{k+1}` is origin k's target move (the state at k + 1 is built from
  the target at k); CH233's sibling bids at k + 1 enter the next unit's state while its member's spread at k + 1 ends the target;
  CH232's crossing at k + 1 reads `mid_{k+1}`, whose quotes also set `spread_{k+1}`. All three are rolling in LT7's sense: the
  block gate (1.8) and a **binding F** (1.9) for all three.
- **Both-demeaned sensitivity** (LT6): every primary re-estimated with the target also expanding-past demeaned; reported only.

### 1.8 Gates (valid within-unit nulls) and their size
- **Block (circular-shift) Freedman-Lane gate** (LT5's `block_fl_gate`, vendored unchanged): after expanding-past demeaning,
  within each stratum the reduced-model residual series (ordered by origin) is circularly shifted by an offset drawn from
  `[s_m, n_m - s_m]`, `s_m = max(4, ceil(n_m / 4))`, and the full model refitted; 200 draws; passes if `p_perm < 0.05`; strata
  with fewer than 16 shiftable rows are excluded from the gate (counted). **Strata:** the market for CH234 and CH232 (CH232
  shifts reward-panel markets only; the control panel enters only the point condition); **the event for CH233, one common
  offset per event applied to every member's series on the event's capture index** (LT10 R1's event-phase form: a sibling
  state shares its event's shocks, so independent member shifts would break the cross-member dependence the null must keep).
- A failed gate on data gives p = 1 in Holm and the label "SE check failed (gate on data)".
- **Size check (L5), after the census (k and the census-fixed values fixed first).** `size-check` runs once, on the code to be
  pinned, 2,000 worlds x 200 draws, seed **20261497**, limit 0.058, every gate scenario through the same `block_fl_gate` path
  and minimum (16) as the analysis; worlds carry a UTC-day and a two-day-block column; a world is generated once and evaluated
  under each binding test. Scenarios (no effect of the tested term in any world):

  | # | Scenario (1.8.1) | Gate | Binding for | Statistic |
  |---|---|---|---|---|
  | 1 | **S28:** a bounded logit random walk with PX1's level drift by price, traded and quote-only movers alike, no dose | block FL | CH234 | gate rejection rate |
  | 2 | **S29:** continuation that depends on `|d|` alone (and on the spread), no dose | block FL | CH234 | gate |
  | 3 | **missing-volume leak:** `volume_num` missing with a probability that rises with a latent activity state which also raises continuation; the model sees only the noisy activity controls | block FL | CH234 | gate |
  | 4 | **volatility clustering:** AR(0.9) log-volatility, movers recur within market-day, continuation scaled by volatility | block FL | CH234 | gate |
  | 5 | **S26:** a common event-level shock that moves every member's bid and spread in the same slot, with no lag effect | event-phase block FL | CH233 | gate |
  | 6 | **S27:** a dormant ladder whose only mover is the favourite; the longshots' spreads mean-revert | event-phase block FL | CH233 | gate |
  | 7 | **event spread contagion:** an event spread factor AR(0.8) shared by members; the model sees the member's own spread level only | event-phase block FL | CH233 | gate |
  | 8 | **liquidity leak (CH233):** members' spread reversion speed rises with a latent liquidity correlated with the siblings' activity; the model sees a noisy liquidity proxy | event-phase block FL | CH233 | gate |
  | 9 | **S25:** a spread that widens with any large `|move|` and reverts, regardless of the boundary, both panels alike | block FL | CH232 | gate |
  | 10 | **smooth level shape:** the spread a smooth, steep function of the mid near 0.10 (wider toward the extreme), no discontinuity | block FL | CH232 | gate |
  | 11 | **tick leak:** a tick change at 0.04 / 0.96 widens spreads; 30% of tick changes are not recorded in the sidecar | block FL | CH232 | gate |
  | 12 | **M-Q (CH234):** a slow drift that raises continuation and the lead and twin products alike | none | CH234 | verdict size |
  | 13 | **M-Q (CH233):** a slow event drift that raises sibling bids before and after the target alike | none | CH233 | verdict size |
  | 14 | **M-Q (CH232):** a slow spread-level drift on rewarded markets that raises crossings before and after alike | none | CH232 | verdict size |

  **Verdict size** (12-14) = the share of worlds in which the test's analytic one-sided p (1.7) is < 0.05 **and** its F and
  point condition (1.9) hold; the gate is omitted, which can only raise the rate. Criterion: <= 0.058.
- **Also reported, never binding:** a planted-effect power run per test (500 worlds each; CH234 0.5c per census tercile gap of
  `xw`, CH233 1.0c per tercile gap of `z cl_sib`, CH232 1.0c between classes; seeds `20261497 x 100 + 41, 42, 43`).
- **Leak worlds (3, 7, 8, 11)** plant a confounder that reaches the model only through an imperfect control; they are binding.
  A rejection rate above 0.058 means the design cannot separate the hypothesis from the confounder at the declared control, and
  the test is "SE check failed (size scenario)". This is the intended consequence, declared now; the parameters are conventions
  (1.8.1), not measurements, and are not tuned after any result. **Expected:** world 3 may fail if the census
  `vnum_unknown` share is high (its rate is taken from the census, 1.8.1); worlds 7 and 11 may fail; the others are expected to pass.
- **Consequence of a failure (as LT5-LT10):** a failing scenario makes **only the tests it is binding for** "SE check failed
  (size scenario)" (1-11) or "SE check failed (mechanical world)" (12-14): p = 1 in Holm, **k unchanged**, no rerun, reseed,
  redesign or variant. `max_retries 1` covers a deterministic crash only. No preliminary run of any scenario at seed 20261497.

### 1.8.1 Simulated worlds (declared now; census inputs only where named)
Common unless stated: units on a 2 h grid, `day = i // 12`, `block2 = day // 2`; 200 draws per world at a fresh sub-seed from
one generator seeded 20261497, scenarios in table order; non-binding runs on generators `20261497 x 100 + n`. Every world fits
the test's primary model with the known-factor block replaced by the simulated controls named. Prices in probability units,
spreads in cents on a 1c tick unless stated.
- **1 (S28):** 400 markets in events of 3, `n_m` uniform on 120..252; latent logit `l_t` random walk with step SD 0.25 and a
  level drift `g(p) = -0.003` a slot for `p < 0.15`, `+0.002` for `p > 0.85`, 0 otherwise (PX1's direction; a convention);
  mid `p_t = logistic(l_t)` rounded to 0.01; movers `|d| >= 0.01`; each mover traded with probability 0.35 independent of
  everything; controls `|d|`, `w`, `sign(d) x bin` (four bins of `p_{k-1}`: < 0.15, 0.15-0.5, 0.5-0.85, >= 0.85) and
  `sign(d) x bin x (p_{k-1} - bin centre)`; no dose.
- **2 (S29):** world 1 without drift, plus continuation `E[c] = 0.15 x |d| - 0.1 x spread` (cents), no dose.
- **3 (missing-volume leak):** world 1 plus a latent activity `a_m,t` AR(1) rho 0.9; continuation `E[c] += 0.3c x a`; traded with
  probability `logistic(-0.6 + 0.8 a)`; `volume_num` missing with probability `logistic(logit(q) - 0.8 a)`, **`q` = the census
  `vnum_unknown` share among CH234's movers** (floor 0.15, a declared convention), so missingness falls with activity; the model
  sees `log1p volume24hr = a + N(0, 0.7^2)` and `z log rv24*` from the simulated moves; no dose beyond `a`.
- **4 (volatility clustering):** world 1 with log-volatility AR(1) rho 0.9 (stationary SD 0.5) scaling the logit step and
  continuation `E[c] = 0.1 x sign(d) x vol_t` (cents per unit of the latent), the model seeing `z log rv24*`; no dose.
- **5 (S26):** 200 events of 3-10 members (uniform), `n` uniform on 120..252 captures; member bids `b_{j,t}` = `b_j + e_t +
  u_{j,t}` with a common event shock `e_t ~ N(0, (1.5c)^2)` iid and member noise; spreads `s_{j,t} = max(1c, round(2c + 1.5 x
  |e_t| / 1c + AR(0.7) noise))` in the same slot; target the member's next spread change; no lag effect of `cl_sib`.
- **6 (S27):** world 5 with one favourite per event carrying all the moves (`e_t` applied to the favourite only, the longshots
  static up to noise) and longshot spreads reflected AR(0.8) around 3c; no effect.
- **7 (contagion):** world 5 plus an event spread factor `f_t` AR(1) rho 0.8 (SD 1c) added to every member's spread; sibling bids
  fall by half of `f_t`'s innovation (a wider spread lowers the bid); the model sees the member's own spread level; no effect
  of `cl_sib` beyond `f`.
- **8 (liquidity leak):** world 5 with member reversion `rho_j = 0.9 - 0.3 Phi(L_j)`, `L_j ~ N(0, 1)`, and the siblings'
  bid-change variance scaled by `exp(0.5 L_e)` (the event mean); the model sees `L_j + N(0, 0.5^2)`; no effect.
- **9 (S25):** 160 rewarded and 160 control markets, `n_m` uniform on 120..252, mids a bounded logit walk started uniformly in
  [0.06, 0.94] with step SD 0.3; spread `s_t = max(1c, round(2c + 3 x |d_t| / 1c x 0.2 + AR(0.8) noise SD 1c))`, reverting;
  approach zone and crossings by 4.2's rules; no boundary effect.
- **10 (smooth level shape):** world 9 with the spread's mean `2c + 4c x exp(-(p - 0.04) / 0.03)` for `p < 0.5` and its mirror
  above, smooth through 0.10 / 0.90, no discontinuity.
- **11 (tick leak):** world 9 with a tick change at 0.04 / 0.96 that widens the spread by 1c for 3 slots; 30% of tick changes
  are not recorded (the unit is not excluded); no boundary effect.
- **12-14 (M-Q):** as LT9 13-14: a drift `mu_t` AR(1) rho 0.99 (stationary SD 0.5c a slot) entering the target and, with loading
  0.3 per SD, both the lead state and the twin (CH234 the product, CH233 `cl_sib`, CH232 the crossing propensity on reward-panel
  markets only); statistic: analytic p < 0.05 and F and the point condition hold.

### 1.9 Verdicts, the falsification condition and labels (per primary, after Holm over k)
- **F rule (LT7's, unchanged).** The **arm model** is the primary model with the far-future twin added, fitted on the units that
  have it, same demeaning, controls and clustering. `Δ = beta(lead) - beta(twin)`. **F holds iff (i) Δ's one-sided p < 0.05
  under the 1.7 rule (not Holm-adjusted; counted 0) and (ii) Δ̂ >= 0.5 x betâ_primary.** An arm with fewer than 50% of the
  primary's units is *falsification unavailable*. **F binds for all three, fixed now by design** (all three states are rolling,
  1.7). Twins: CH234 `xw` of the market's move over (k + 2, k + 3] (computed on every unit with mids at k + 2 and k + 3,
  `w = 0.5` where that move is 0); CH233 `z cl_sib` over (k + 2, k + 3] on complete event-capture pairs; CH232 the market's
  first outward crossing at (k + 2, k + 3] (approach-zone rule at k + 2).
- **Point conditions (binding, fixed now; estimates only, no test, counted 0).** CH234: the quote-only twin model's slope on
  `xw` (same controls, same demeaning) **betâ_quote < 0.5 x betâ_traded**. CH233: the ask-sum twin model (`z ca_sib` in place of
  `z cl_sib`) **betâ_ask < 0.5 x betâ_bid**. CH232: the control panel's crossing coefficient **betâ_ctrl < 0.5 x betâ_rew**.
  Each difference's one-sided p is reported (labels below); none is a significance condition (6.1 item 5).
- **Supported (exploratory, prospective):** Holm-adjusted one-sided p < 0.05, estimate > 0, gate passed, **F holds and the point
  condition holds.** If everything else holds and F fails or is unavailable: **Inconclusive** with *mechanical null not
  excluded* (or *falsification unavailable*); if the point condition fails: **Inconclusive** with *not traded-specific*
  (CH234), *not bid-specific* (CH233) or *not reward-specific* (CH232). Holm p is not changed.
- **Contradicted:** the conservative 95% CI lies entirely below 0. **Inconclusive:** otherwise.
  **Unavailable:** fewer than 20,000 units, fewer than 300 events, or fewer than 10 UTC days with units; CH234 also fewer than
  20,000 quote-only units; CH233 fewer than 100 events with >= 48 units; CH232 fewer than 2,000 counted crossings or 1,000
  control-panel crossings.
- **Labels (never change a verdict):** *material* (the estimate >= the floor at the census tercile gap of the tested term:
  CH234 0.5c, CH233 1.0c; CH232 >= 1.0c between classes); *traded-difference significant* / *bid-difference significant* /
  *panel-difference significant* (the difference's one-sided p < 0.05); *within-bin* (CH234: M3's four bin slopes all > 0);
  *re-centring not widening* (CH233: M1's bid change < 0 with p < 0.05 and the primary not Supported); *side reading
  ambiguous* (CH232, 1.4.2); *informed (X)*; *analytic p oversized in simulation*; *underpowered* (Inconclusive and
  `(t_{G-1, 1-0.05/k} + t_{G-1, 0.8}) x SE_day` above the census MDE); *attrition-differential*; *late-loss*;
  *series-concentrated* (> 50%); *ladder-dominated* (the ladder arm's estimate has the opposite sign); *holiday-sensitive*,
  *month-start-sensitive* (1.1); *volume-missing sensitive* (CH234: the unknown-class arm of 2.3 has an estimate above the traded one, or of the opposite sign);
  *CLOB-disagreement sensitive* (CH232: the refit on units whose carry status and feed listing agree changes sign).
- **MDE multiplier.** `3.47 = t_{20, 1 - 0.05/6} + t_{20, 0.8}` (LT7-LT10's constant), **not lowered** for k <= 3.

### 1.10 Economics (separate; never changes a verdict)
- **Paper taker (reported):** round trip at the recorded capture touches (`bid`, `ask` of the entry capture k and exit capture
  k + 1; no sweep), fees on both legs from the origin sidecar (`economics.fee_spec`, `resolve_rate(..., "max_if_unknown")`),
  LT3's `paper_taker` and `econ` (event-clustered mean, one-sided p, >= 30 trades in >= 10 events). No depth, queue or latency:
  optimistic. Rules: CH234 follow traded moves with `xw` in the top census tercile and `|d| >= 0.03` (and fade the bottom
  tercile); CH233 none (a maker-side mechanism); CH232 the hold-to-resolution buyer of the extreme side entering at k + 1 instead
  of k after an outward crossing, priced at the touches only (the saving is the retreat; no resolution income computed).
- **Hurdles (`cost-model-v1`, `COST_MODEL.md`, development calibration 2026-10-16..19):** $100 taker round trip about 2.9c at
  >= $100k liquidity, 3.9c at $10k-100k, 7.2c at $1k-10k; a 5-share touch round trip about 4.5c (politics 3.6c); a passive touch
  order fills about 3.1% of the time within an hour and loses about 2.38c to adverse selection against a 2 h mark; makers about
  break-even before rewards (non-sports fill-weighted -0.37c).
- **Maker routes (gross, an upper bound, no fills):** CH234 re-centre by the full move after a top-tercile `xw` move and by half
  after a bottom-tercile one (the adverse selection avoided is the continuation difference, reported in cents per share); CH233
  lower the own bid by one tick for one slot when `cl_sib` is in its top census tercile and `hb_k` within two ticks of zero
  (the fill avoided is the bid's subsequent change); CH232 cancel the side M1 names for one slot after an outward crossing (the
  reward minutes lost, at the carry source's rate and the scoring formula `((v - s) / v)^2 x b`, against the retreat avoided).
  No reward is computed as earned.
- **Declared in advance:** every AREPO taker cost check has failed (E004, E007; 0 of 95 economic cells positive). "Not shown" is
  the expected outcome for every taker cell. **No LT11 result can satisfy the programme's economic check** (CLAUDE.md: prospective
  confirmation and an economic check at recorded prices before any edge claim): the maker routes have no fills, queue or realised
  reward income, and the taker cells are expected "not shown". A Supported LT11 primary can at most nominate a later, separately
  registered economic test.

### 1.11 Overlaps, dependence, embargo shadows and counting
- **Within LT11:** a CH233 member can be a CH234 traded mover in the same capture, and a CH232 approach-zone unit can be a CH234
  mover (a crossing is a move); CH234's `|d|` and CH232's crossing share the capture pair. All three are in one Holm family and
  never counted as independent confirmations. The census prints the pairwise unit-overlap shares and, on shared units, the
  within-market correlations of the tested terms (reported).
- **Against registered or drafted tests (no double count; no shared origin):**

  | LT11 | Closest prior | Same data? | Same contrast? | Why not a double count |
  |---|---|---|---|---|
  | CH234 | **E015** (the move's anatomy; LT3) | captures, `volume_num` | no: E015 contrasts anatomy classes; CH234 tests a collateral dose within the traded class, with the quote-only class as a twin | E015's window ends before LT11's; freeze before `T_E015` or the ordered lane with *informed (E015)* |
  | CH234 | **E022** (hollow liquidity on traded movers; LT4) | captures, the traded class | no: E022's state is sweep depth against liquidity; CH234's is collateral | disjoint windows |
  | CH234 | HB1 **PX1** (survived), PX5, MI4 (development) | captures | levels and indicator interactions near the extremes; CH234 controls the level drift by bin and tests the dose | development record disclosed (10) |
  | CH233 | **E005** (not supported), HB1 XM1-XM3, the `event` family (se8 / se10) | captures | no: mid-sum levels and the mid's repricing; CH233 tests the bid-sum innovation on the spread | disclosed (10); `nrslack` token (9) |
  | CH232 | **LT9 CH213** (the reward-band break; window from 2026-12-30), **CH71** (level discontinuity) | the rewarded panel, `listed_carry24h_v2` | no: CH213 reads the spread crossing `2v`; CH232 the mid crossing 0.10 / 0.90 | disjoint windows; LT9 frozen before LT11's design |
  | all | LT10 (fine clock), E009-E011, E025, E026 | no | no | different streams; nothing of E026 is imported |

- **Signal-engine shadows (disclosed; section 9).** CH234's product can be formed by any model given the mid and the own 2 h
  change (LightGBM se1 holds both); the `tilt` family's planned `tl_w2h` is CH234's `w`. CH233's levels live in the `event`
  family (visible); its innovation is not built. CH232's crossing can be formed by a model given the mid at k - 1 and k. LT11 asks
  for the tokens and attribution limits of section 9.
- **Collection overlap (disclosed):** the engine and every earlier test read the same captures and sidecars; LT11's census span
  lies inside E022's window (2026-10-26..11-16) and before E015's analysis (11-15T12Z), and overlaps LT9's census span
  (11-02..11-12) in time; census reads are counts only and no store is opened.
- **Counting (M3):** the analysis adds **k counted tests**, one per surviving primary, kind `live_tests11`
  (`battery2.KIND_RULES["live_tests11"]`, fail-closed). Gate draws, F, point conditions, secondaries, readings, arms, placebos,
  economics, the census, the CH240 map and the size check count 0. The cumulative count is recorded at registration and at
  analysis.

### 1.12 Stop rules
As LT9 1.12: no interim look; the test runs to `END_UTC` whatever the counts; after 7 days, a test whose units run below one
third of its census projection (counts only) gets the ledger note "likely Unavailable" and nothing else changes; any change to a
pinned file after the pin makes the analysis refuse; the reader exits 75 when nothing is new; a failed reader is re-promoted
within 48 h; gaps stay missing and are counted; disk: the reader refuses above 3.0 GB in `live_tests11/` and no retention rule
may cover `live_tests11/` before the analysis is committed; collection of a kind is switched off when its test is not in
`k_tests`.

## 2. CH234: the dollar weight of a move (continuation rises with the collateral behind a traded move)

### 2.1 Hypothesis in plain words
On this venue the price of a share is its collateral. A one-cent move up at 0.90 was bought with about 90c a share (YES), a
one-cent move down at 0.90 with about 10c a share (NO). So the same move in cents carried very different money depending on
its direction against its level, and money is the cost of being wrong (Kyle 1985). The hypothesis: among moves that came with
a trade, the ones that carried more dollars (a heavy weight `w` times a larger size `|d|`) keep going more over the next two
hours than light ones, beyond momentum, the price level's own drift and the market's state; and among moves that came without
any trade (quote-only), where nobody paid, this pattern is absent or much weaker.

### 2.2 Population and unit
- **Unit:** a non-sports ex-crypto market x capture k with `|d_k| >= 0.01`, `d_k = mid_k - mid_{k-1}`, passing 1.4 at k - 1
  and k, `p_{k-1} = mid_{k-1}` in **[0.04, 0.96]** (the 1c-tick regime; the tick boundary itself belongs to CH86), tick unchanged,
  events with `n_members <= 10` (ladder arm reported), and **traded** by 2.3. The **quote-only** movers (2.3) are the twin
  population, built by the same rules. The **unknown** movers (2.3) form a counted, reported arm.
- **Origin and decision clock:** capture k's last row receipt (1.3); every input is from captures k - 1, k and the 12-slot
  look-back. **Target and horizon:** `c = sign(d_k) x (mid_{k+1} - mid_k)` in cents, over (k, k + 1] (2 h); `unavailable`
  unless the unit is `two_sided` at k + 1 (1.5).

### 2.3 `volume_num`: three classes, declared before any count (rule 5; the map's warning)
`volume_num` is the sidecar's cumulative traded volume in USD. For a mover at k, read `v_{k-1}` and `v_k` from the sidecar rows of
captures k - 1 and k (the same `condition_id`):
- **traded:** both finite and `v_k - v_{k-1} > 1e-6`;
- **quote-only:** both finite and `|v_k - v_{k-1}| <= 1e-6`;
- **unknown:** anything else, kept in four counted sub-classes: `vnum_missing_k` (empty, NaN or non-numeric at k),
  `vnum_missing_km1` (at k - 1 only), `vnum_decrease` (`v_k < v_{k-1} - 1e-6`, a data anomaly), `sidecar_missing`.
**Unknown movers are never classed traded or quote-only, never imputed, never re-classed from `volume24hr`, `last_trade_price`
or any other field.** They are excluded from the primary and the twin and fitted alone as a reported arm (uncounted). The CH240
map found `volume_num` empty on 83% of the sidecar rows of one capture (10-22T00:31Z) and about 851 unknown movers a capture
against about 3,705 classed (about 19% of non-sports ex-crypto movers); whether the missingness is capture-level (a sidecar
version or a fetch path) or row-level is **not known**, so the census measures it and gates it (7: the pooled unknown share,
the share of captures that are mostly unknown, and the correlation of being unknown with the tested term and with `w`). The
traded class is a population rule, never the tested term (E015's anatomy is not re-tested here).

### 2.4 State, controls and the primary statistic
- **Weight:** `w_k = 0.5 + sign(d_k) x (p_{k-1} - 0.5)`: the collateral a share of the side whose buying moved the price (in
  [0.04, 0.96] on the population). **Size:** `|d_k|` in probability units, **winsorised at 0.20** (declared convention; counted).
- **Tested term (6.1 item 6):** the centred product `xw_k = z(w_k) x z(|d_k|)`, `z(x) = (x - c_x) / s_x` with the census centre
  `c_x` (mean) and scale `s_x` (SD) over CH234's census traded units, fixed in the spec.
- **Controls:** `|d_k|`; the level drift by bin: `sign(d_k) x 1[bin b]` and `sign(d_k) x 1[bin b] x (p_{k-1} - centre_b)` for the
  four declared bins of `p_{k-1}` (`[0.04, 0.15)`, `[0.15, 0.50)`, `[0.50, 0.85)`, `[0.85, 0.96]`; centres the bin midpoints; the
  0.15 / 0.85 cuts are HB1 PX1's object), which together span `w` itself (so `w`'s main effect is held fixed); the known-factor
  block K (1.7: the level, spread, liquidity, 24 h volume, hours to end, tick, `z log rv24*`, `neg_risk`, `rewarded_k`, category
  and slot dummies, `d_k`, the 6 h and 24 h own changes, `chg_1h`); `n_members`.
- **Primary:** expanding-past market-demeaned OLS of `c` on `xw` with the controls, on traded units; **one-sided H1: beta > 0**;
  inference 1.7; block FL gate in market strata (1.8); F binding with the twin of 1.9; the **quote-only point condition**
  (betâ_quote < 0.5 x betâ_traded, 1.9) binding.
- **Secondaries (reported, uncounted):** M1 `c_skip = sign(d_k) x (mid_{k+2} - mid_{k+1})`; M2 the quote-only slope itself and the
  traded-minus-quote-only difference with its p; M3 the slope within each of the four bins; M4 the round's raw form (the tested term
  `z(w x |d|)` with `|d|`, `p_{k-1}` and `sign(d) x bin` as controls, as round 16 sketched it); the unknown-class arm; the
  ladder arm; the sports arm (uncounted).

### 2.5 Planning counts and MDE (planning only; the map counted the population, never an effect)
- **Counts:** the map's traded movers about **1,239 a capture** (non-sports ex-crypto, all price bins, before LT11's band, tick,
  tightness and cap rules); planning retention 0.73-0.93 gives **900-1,150 traded units a capture** (226,800-289,800 in 21 days;
  `n_eff` 181,400-231,800 at 0.8). Quote-only about 2,466 a capture on the map (planning 1,800-2,300 after the rules). Distinct
  events with a traded mover over the map's 6.92 days: 3,535 (rewarded) and 2,950 (unrewarded).
- **Design effect:** E022's measured 6.196 (`m_21` 260.8 on about 194,000 21-day units) is the optimistic end. A population
  1.2-1.5 times E022's in a comparable set of events projects `m_21` about 300-390 and DE about 7-9; **10 is the pessimistic
  planning end** (a few large ladders dominate a size-weighted mean). The census computes `DE_gate = max(6.196, 1 + (m_21 - 1) x 0.02)`.
- **MDE (slope at the tercile gap 2.2 SD, `VIF_w` 1.3, SD 4c):** DE 6.196: **0.31c (900) / 0.27c (1,150)**, quarter of the low count
  0.61c, **F-MDE (`r_w` 0.1) 0.46c / 0.40c**. DE 10: 0.39c / 0.34c, quarter 0.78c, **F-MDE 0.58c / 0.51c (fails 0.5c)**. At `VIF_w`
  2.0 and DE 6.196: F-MDE 0.56c / 0.50c.
- **Kill lines (F-MDE gate 0.5c, binding):** about **745 traded units a capture at DE 6.196 and `VIF_w` 1.3**; 1,146 at `VIF_w` 2.0;
  1,203 at DE 10; 1,850 at DE 10 and `VIF_w` 2.0. The count gate (7) is set at 745, the most lenient of these, and the F-MDE gate
  itself, computed from the census's own DE, `VIF_w` and `r_gate`, decides.

### 2.6 Confounders and how each is held
- *Level drift* (PX1: longshots drift down; S28): a down move at a low price has a high `w` and a drift that continues it. Held
  by the piecewise-linear `sign(d) x bin` controls (which span `w`) and by the product's `|d|` dose (drift does not scale with
  the move's size); world 1 binding.
- *Size alone* (S29): `|d|` is a control and the product is centred; world 2 binding.
- *Bounded prices:* a move toward an extreme has less room (works against H1); the bins and the band [0.04, 0.96].
- *Momentum and market state:* the known-factor block K (1.7).
- *Selection by missing volume:* the unknown class is excluded and gated (7); world 3 binding with the census's own unknown share.
- *Volatility clustering:* `z log rv24*`; world 4 binding.
- *E015's anatomy and E022's population:* blind freeze (1.1); disjoint windows.
- *The engine's learners* (se1 holds the mid and the own 2 h change and may have learned the product): a development look,
  disclosed; attribution limit and the `dollarw` token requested (9).
- **Most likely boring outcome:** continuation on traded movers is the same at every weight because informed flow sits on the
  cheap longshot side as often as on the dear favourite side (a clean null), or the dose is mostly the drift by bin and the
  residual variation is thin (the residual-IQR and `VIF_w` gates say so before any target).

### 2.7 Data streams, jobs, timing (CH234's share of section 8)
Rows and sidecars of captures k - 3 .. k + 3 (the 24 h change reads k - 12); no sweep, no feed, no new collector. The reader keeps
per market the last 12 mids and the last `volume_num` (a few hundred bytes). Census CC11 (7), size check (1.8), reader and analysis
(8.2). Embargo token `dollarw` (9).

## 3. CH233: the arb's footprint (the siblings' bid-sum rise and the member's next spread)

### 3.1 Hypothesis in plain words
In a neg-risk event (one winner among several markets), the YES bids of all members cannot add up to more than one for long:
selling YES into every bid and converting the NO positions pays the excess at once, and bots do it within minutes. That selling
lands on the bids. So when the other members' bids rise and the event's bid headroom (`1 - sum of bids`) closes, the arbitrage
pressure arrives on every member's bid, and over the next two hours the member's makers re-post lower and its spread widens from
the bid side. The ask side has no such instant arbitrage (buying the whole set below one is a hold-to-resolution carry), so the
same rise in the siblings' asks should not do this.

### 3.2 Members, completeness and the event key (declared before any count; rule 16)
- **Event key:** `neg_risk_market_id` where present and non-empty, else Gamma `event_id` among rows with `neg_risk` true; one key
  per member row (a row with both a key and a conflicting `event_id` is counted `nr_key_conflict` and keyed by
  `neg_risk_market_id`).
- **Eligible members of event e at capture j:** rows of capture j with the key, `neg_risk` true, binary, open and active. Placeholder
  and "Other" members (`neg_risk_other`) are members (they are part of the exhaustive set); `event_neg_risk_augmented` is a control.
- **Complete event-capture pair (k - 1, k):** the eligible member set is identical at k - 1 and k (else `members_changed`), and
  every member is two-sided (bid > 0, ask < 1) at both (else `event_incomplete`). Incomplete pairs give no unit for any member;
  they are counted, never filled, and no member's bid is set to 0 or carried.
- **Size classes:** the primary keeps events with **3-10** eligible members. **2-member events are a reported arm** (6.1 item 7:
  there the siblings' sum is one market, the complement of the member's own price, so the state is the member's own move); events
  with 11+ members are the reported ladder arm (round 14 rule 7). Sports, crypto or unknown category on any member excludes the
  event (counted).

### 3.3 State, controls and the primary statistic
- **Headroom:** `hb_j = 1 - sum_m bid_{m,j}` over the event's eligible members at capture j.
- **State (sign corrected, 6.1 item 8):** `cl_sib_{i,k} = sum_{m != i} (bid_{m,k} - bid_{m,k-1})` in cents: positive when the
  siblings' bids rose, i.e. the headroom closed because of the other members. Tested term `z cl_sib = cl_sib / s_c`, `s_c` the census
  pooled SD of `cl_sib` in the member's size class (3-5 or 6-10 members), fixed in the spec.
- **Twin regressor (separate model):** `ca_sib_{i,k} = sum_{m != i} (ask_{m,k} - ask_{m,k-1})`, scaled the same way (`z ca_sib`).
- **Controls:** `hb_{k-1}`; the member's own bid change and own spread change over (k - 1, k]; its bid share `bid_{i,k} / sum_m
  bid_{m,k}`; the event's mid overround `sum_m mid_{m,k} - 1` (the `event` family's level); `n_members`; `neg_risk_other`;
  `event_neg_risk_augmented`; the known-factor block K (1.7, with `d_k` the member's own 2 h mid change).
- **Primary:** expanding-past market-demeaned OLS of `ds_i = spread_{i,k+1} - spread_{i,k}` (cents; spread = ask - bid on the row)
  on `z cl_sib` with the controls; **one-sided H1: beta > 0**; inference 1.7 (event clusters); **event-phase block FL gate** (1.8);
  F binding (twin `z cl_sib` over (k + 2, k + 3]); the **ask point condition** (betâ_ask < 0.5 x betâ_bid from the twin model with
  `z ca_sib` in place of `z cl_sib`, same controls) binding.
- **Secondaries (reported, uncounted):** M1 the bid's change `bid_{i,k+1} - bid_{i,k}` (predicted < 0); M2 the mid's change (E005's
  object; `informed (E005)` by the record); M3 the headroom crossing class `1[hb_{k-1} > 0 and hb_k <= 0]` (rare: the map's 11.9
  a capture on the rewarded panel); M4 the slope by the member's rank in the event (favourite against the rest; S27's dose); the
  2-member and 11+ arms; the sports arm.

### 3.4 Planning counts and MDE (planning only)
- **Counts (map, non-sports ex-crypto, per capture):** neg-risk events 1,664 (rewarded) / 825 (unrewarded); member rows 14,123 /
  4,933; complete event-captures about 1,833; complete shares by size 2: 1.00 / 0.97, 3-5: 0.85 / 0.65, 6-10: 0.88 / 0.67, 11+:
  0.30 / 0.14; complete (k - 1, k) pairs 1,262 / 563. The map did **not** print member rows by size class, so the primary's units
  are **unprobed**: planning **4,000-8,000 complete member units a capture** in events of 3-10 members (1,008,000-2,016,000 in 21
  days; `n_eff` 806,400-1,612,800). `hb` q05 / q50 / q95: rewarded 0.010 / 0.109 / 0.414, unrewarded 0.009 / 0.029 / 0.797; within
  two ticks of zero on about 12.6% of complete event-captures; within-event SD of the siblings' bid-sum change >= 1 tick in 0.83 /
  0.85 of events with >= 48 units.
- **Design effect:** every member of an event shares its clusters; an event of 3-10 members present for most of the window holds
  700-2,500 units, so planning DE **31** (capped) to **51**; the census computes `DE_gate = max(5.0, 1 + (m_21 - 1) x 0.02)`.
- **MDE (slope at the gap 2.2 SD, `VIF_w` 1.5, SD 2c):** DE 31: **0.17c (4,000) / 0.12c (8,000)**, quarter 0.35c, **F-MDE (`r_w`
  0.2) 0.28c / 0.19c**; DE 51: 0.22c / 0.16c, quarter 0.45c, F-MDE 0.35c / 0.25c. All far under 1.0c: **power is not the question;
  the identification gates are.** The F-MDE gate's kill line is about 500 complete member units a capture at DE 51.

### 3.5 Confounders and how each is held
- *Common event shocks* (S26: news moves every member's bid and spread in the same slot): the state is lagged one slot behind the
  target by construction; the own changes over (k - 1, k] are controls; world 5 binding.
- *Spread contagion across the ladder* (world 7): a widening of siblings' spreads lowers their bids (`cl_sib < 0`) and widens the
  member's next spread (`ds > 0`), which biases **against** H1; a narrowing biases against it too. Binding nonetheless.
- *A siblings' mid rise in general* (not the arbitrage): it raises bids and asks alike, so the ask point condition fails; and the
  own move and the overround are controls.
- *Dormant ladders* (S27; CH220's dormancy is 10.4% of non-sports rows and higher among longshots): the per-event SD gate (7), M4,
  world 6 binding.
- *Liquidity:* the corr gates and world 8 binding.
- *Momentum and market state:* the known-factor block K.
- *The record:* E005 (a member's deviation from its arbitrage band predicting the mid's repricing) was not supported, challenger
  CONFIRMED; XM1-XM3 were nulls or not survivors; the `event` family's level scores are visible to the engine (a development look
  at the levels, disclosed; the innovations are not built, 9).
- **Most likely boring outcome:** the venue's own arbitrage keeps the bid sum far enough below one that a sibling rise never
  presses (a noise state; the working-range gate measures it before any target), or the bids that move are the farmers'
  symmetric quotes following the mid, so the spread re-centres instead of widening (M1 moves, the primary does not; the label
  *re-centring not widening*).

### 3.6 Data streams, jobs, timing
Rows of captures k - 1 .. k + 3 (all members of each neg-risk event; the event join is a reader, no matcher); the sidecar for
category and tick; no sweep, no feed. The reader keeps per event the previous capture's member bids and asks (a few kB per event;
about 2,500 events). Census CC11, size check, reader, analysis (8). Token `nrslack` (9).

## 4. CH232: the cheap side's cliff (a rewarded market's mid crossing out of [0.10, 0.90])

### 4.1 Hypothesis in plain words
A resting quote costs its poster the collateral of its side: at a mid of 0.92 the YES bid ties up about 91c a share, the YES ask
(a NO bid) about 8c. Reward-paid makers therefore crowd the cheap side. The venue's reward rule changes what a maker must post to
score at the published boundary of 0.10 / 0.90. So when a rewarded market's mid crosses out of [0.10, 0.90] for the first time in
a day, some makers have just lost the reason to keep one side posted, and over the next two hours the spread should widen; on
unrewarded markets, where no rule changes at that price, the same crossing should do much less.

### 4.2 Definitions (declared before any count; rule 15)
- **Mid:** `m_j = (bid_j + ask_j) / 2` on capture j's row (Gamma's touch; the venue scores on its own book midpoint; disclosed).
  **Band** `B = [0.10, 0.90]`, closed, comparisons with tolerance 1e-9.
- **Outward approach zone (the primary population, 6.1 item 1):** a rewarded-panel unit at capture k whose `m_{k-1}` lies in
  `[0.10, 0.14]` or `[0.86, 0.90]` (within 0.04 of a boundary, inside `B`; 0.04 is the planning SD of the 2 h mid change, and the
  zone's outer edge stays 0.06 inside the tick boundaries 0.04 / 0.96). Membership uses `m_{k-1}` only.
- **Outward crossing at (k - 1, k]:** `m_{k-1}` in `B` and `m_k` outside `B`. **`xo_k` = 1** if it is the market's first outward
  crossing of either boundary in the UTC day of capture k, reading only earlier slots of that day; **`xr_k` = 1** if it is a later
  outward crossing of the same day (a declared class, entered as its own regressor, so the reference class holds only units that
  did not cross). A unit whose UTC day has a missing earlier slot is excluded (`day_gap`, counted): the first-crossing status is
  not known.
- **Tick-coincident:** the tick changed between k - 1 and k (already excluded by 1.4) or `m_k` is below 0.04 or above 0.96;
  excluded and counted (`tick_coincident`).
- **Dear and cheap sides at k:** below 0.10 the dear side is the YES ask (its NO bid costs about `1 - m`), above 0.90 the YES bid.
  M1's side follows 1.4.2.
- **Panels:** the reward panel (1.4.1, fixed at the market's first unit) is the primary; the control panel (`rewarded = 0`) is fitted
  with the same model for the point condition.

### 4.3 State, controls and the primary statistic
- **State:** `xo_k` (and `xr_k` as a control).
- **Controls:** the move toward the boundary `d_tow_k` (`-d_k` near 0.10, `+d_k` near 0.90) and `|d_k|`; the distance
  `dist_{k-1}` of `m_{k-1}` to its boundary (in [0, 0.04]); an upper-boundary indicator; the spread level at k and the own spread
  change over (k - 1, k]; the band `v` and `log` daily rate of the carry source; the known-factor block K (1.7). Together with
  `dist_{k-1}` and `d_tow_k`, `xo` is a threshold in `m_k`: the design is a local discontinuity in the mid at the boundary,
  identified among units that approached it.
- **Primary:** expanding-past market-demeaned OLS of `ds = spread_{k+1} - spread_k` (cents) on `xo` with the controls, reward panel,
  approach-zone units; **one-sided H1: beta > 0** (6.1 item 3); inference 1.7 with the sparse-class df; block FL gate in market
  strata; F binding (twin: the market's first outward crossing at (k + 2, k + 3], zone rule at k + 2); the **control-panel point
  condition** (betâ_ctrl < 0.5 x betâ_rew) binding.
- **Secondaries (reported, uncounted):** M1 the retreat of the side 1.4.2 names (`-(bid_{k+1} - bid_k)` for the bid,
  `ask_{k+1} - ask_k` for the ask); M2 the mid's change toward the band (a mid target the counts do not reach); M3 sweep 1's 1c and
  5c depths on both sides at passes k and k + 1 (post-decision readings, 1.3); S1 the **inward** twin (zone `[0.06, 0.10)` or
  `(0.90, 0.94]` at k - 1, first inward crossing of the day, predicted < 0); S2 a **pseudo-boundary placebo** at 0.20 / 0.80 (zones
  `[0.20, 0.24]` and `[0.76, 0.80]`, predicted 0); the panel difference's p; the CLOB-disagreement refit; the sports arm.

### 4.4 Planning counts and MDE (planning only)
- **Counts (map, non-sports ex-crypto, per capture; first crossings per market, boundary and UTC day; the map's reward reading was
  the simple non-empty `clob_rewards` at k, not `listed_carry24h_v2`, so the carry panel may be larger):** rewarded outward 66.3 at
  0.10 (61 ex-tick) and 12.4 at 0.90, about **79 (73 ex-tick)**; unrewarded 48.5 and 16.8; inward rewarded 45.0 and 4.4. The share
  that came from inside the 0.04 zone is **unprobed** (planning 0.68-0.95): **50-69 counted reward-panel crossings a capture**;
  control panel about 43-60. Zone units without a crossing are **unprobed** (planning 500-1,000 a capture on the reward panel).
  Distinct events with a rewarded crossing over the map's span: 2,178 (0.10) and 673 (0.90).
- **MDE (class contrast, SD 2c):** DE 31, `VIF_w` 1.3: **0.69c (50; 500) / 0.58c (69; 1,000)**, quarter 1.38c, **F-MDE (`r_w` 0.2)
  1.09c / 0.92c**. `VIF_w` 2.5 (the discontinuity's controls may push it there): 0.96c / 0.80c, F-MDE 1.51c / 1.27c. A computed DE
  of 15 with `VIF_w` 1.3: 0.48c / 0.40c, F-MDE 0.76c / 0.64c. The panel interaction (reported only): 1.01c / 0.85c at DE 31.
- **Kill lines (F-MDE gate 1.0c, binding; 750 zone units a capture):** about **58 counted crossings a capture at DE 31 and `VIF_w`
  1.3**; 121 at `VIF_w` 2.5; 27 at DE 15; 54 at DE 15 and `VIF_w` 2.5. The count gate (7) is **60 a capture** (round 16's own
  verdict line, written before the map), the F-MDE gate decides with the census's DE and `VIF_w`.

### 4.5 Confounders and how each is held
- *Big moves widen spreads anyway* (S25): `|d|`, `d_tow` and the own spread change are controls; the crossing must add a
  discontinuity at the boundary; world 9 binding; the control panel's point condition.
- *The spread's level is steep near the extremes* (a smooth shape): `dist_{k-1}`, the level at k and world 10 binding; S2's
  pseudo-boundary placebo.
- *The tick regime at 0.04 / 0.96* (CH86): the zone stays 0.06 away; tick-coincident units excluded; world 11 binding.
- *Re-crossing chatter* around 0.10 (ladder longshots): `xr` is its own class; the re-crossing gate (7).
- *Reward-field omission:* the carry rule (1.4.1); the CLOB-disagreement refit.
- *E022's S2 and LT9's CH213:* blind freeze, disjoint windows (1.1).
- *Momentum and market state:* the known-factor block K.
- **Most likely boring outcome:** too few first crossings from the zone on the reward panel (the count and F-MDE gates), or the
  farmers never post the dear side at all, so nothing leaves at the crossing (a clean null the documented reading partly predicts).

### 4.6 Data streams, jobs, timing
Rows and sidecars of captures k - 12 .. k + 3 (the earlier slots of the UTC day and the carry window); sweep 1 of passes k and
k + 1 for M3 only; the feed for the CLOB sensitivity and economics. The reader keeps per market the day's crossing flags and the
carry window's texts. Census CC11, size check, reader, analysis (8). Token `bandside` (9).

## 5. Deferred and not taken (each with the reason; none counted)
- **CH235-CH239 (engine-first: `tilt`, `parentsib`, `nrslack` levels, `ruleclass`, `volage`):** not live tests by the round's own
  ranking; they go to the signal engine under its rules, with the embargo limits of section 9 (`tilt`'s `tl_w2h` is CH234's `w`).
- **CH240 (the boundary map):** done (q0680, counts only, k = 0, uncounted); used here as planning input only.
- **CH241 (the reverse fine clock):** not taken. It reads LT10's stream, would be `informed (LT10)` by construction, runs only if
  LT10's family census passes, and its money route is a Kalshi maker's (the owner's call).
- **Sports arms:** every test reports its sports arm, uncounted, pending the owner's sports-scope decision.

## 6. Design changes from the round-16 sketches (made before any LT11 data; each needs the challenger's acceptance)
Items marked **[map]** were made after reading the CH240 map (10.1).
1. **CH232: a causal population.** The round's frame (all 12 slots of a market-day that has a first crossing) selects units by a
   crossing that happens after their own origins: a unit at an earlier slot of the day would be admitted on a later mid, which is
   future information in selection (AGENTS.md research integrity), and its target would often span the crossing itself. Replaced
   by the outward approach zone (4.2), whose membership reads `m_{k-1}` only; the crossing is then a state at k on units already
   admitted. Cost: the zone's units are unprobed and the discontinuity's controls raise `VIF_w` (planning 1.3 to 2.5).
2. **CH232: later crossings of the same day (`xr`) are a regressor class**, not only a reported class, so the reference class
   holds only units that did not cross.
3. **CH232: the primary's sign is fixed now (> 0) for both readings of the rule; the reading fixes only M1's side,** and the venue's
   page is re-read in the freeze commit rather than at the pin (rule 15 asks for the sign before the census; the freeze is the
   earliest commit that can record it). Reason in 1.4.2.
4. **CH232: the inward crossing is a reported secondary (S1)**, not a co-primary: one tested coefficient per test, and the outward
   crossing is the money route (a maker steps aside).
5. **All three: every twin or control comparison is a binding point condition fixed now** (quote-only, ask-sum, control panel),
   not "a verdict condition where its census MDE is under the floor": LT9 R1 fix 1's rule that whether a condition binds is fixed
   by design, never by a census count, applied to these conditions as to F. A point condition costs no power; its one-sided p is
   reported as a label.
6. **CH234: the tested term is the centred product `z(w) x z(|d|)` with `|d|` and a piecewise-linear `sign(d) x bin` drift that
   spans `w`** as controls; the round's raw `z(w x |d|)` is kept as M4. Reason: the raw product loads on both main effects (the
   round's own S28 and S29 worlds exist because of this), and rule 17 asks for variance beyond the sign and the level. Also: `|d|`
   winsorised at 0.20; band `p_{k-1}` in [0.04, 0.96]; bins cut at PX1's 0.15 / 0.85.
7. **CH233: 2-member events are a reported arm [map].** In a 2-member event the siblings' bid sum is the other market, roughly
   the complement of the member's own price, so the state is the member's own move. The reason is arithmetic, but the choice was
   made after seeing the map's completeness by event size (2-member events 1.00 / 0.97 complete), so it is marked.
8. **CH233: sign correction.** The round's `dhb_sib = -(sum_{j != i} bid_{j,k} - sum_{j != i} bid_{j,k-1})` is positive when the
   siblings' bids fell (the headroom opened), while its text says "positive means the headroom closed". LT11 uses `cl_sib` = the
   siblings' bid-sum change (positive = closed), matching the text and the hypothesis.
9. **CH233: the ask-sum twin is a separate model** (point condition), not a second regressor in the primary: the siblings' bid-
   and ask-sum changes move together with the siblings' mids, so in one model the bid coefficient would be identified only by the
   siblings' spread changes.
10. **CH233: the Freedman-Lane gate shifts whole events** (one offset per event), as LT10 R1 required for states shared within an
    event.
11. **All three: F binds unconditionally, fixed now** (rolling states, 1.7). For CH234 the round had "a reported label at the low
    planning count, a verdict condition at `n_eff` >= 150,500": a census-dependent rule, not allowed.
12. **All three: an explicit known-factor block K** (1.7), the champion's market-state and momentum families as the captures carry
    them.
13. **Count gates at the binding kill line [map]:** CH234's traded-unit count gate is 745 a capture (the round's F line), not 335
    (its MDE line); CH232's crossing gate is 60 a capture (the round's verdict line), not 24. Both values were written by the
    round before the map; choosing the higher of the two round values follows lesson (i) of 1.0 and was made after seeing the
    map's counts (1,239 and 79), so it is marked.
14. **CH232: tick coincidence defined** (a tick change, or `m_k` beyond 0.04 / 0.96); **CH232: a missing earlier slot of the day
    excludes the unit** (`day_gap`).
15. **CH234: planning DE 6.196 to 10, not 6.196** (2.5): a population 1.2-1.5 times E022's computes a larger `m_21`.
16. **CH233 and CH232: census `DE_gate` floor 5.0** (LT9's whole-panel floor) against the round's planning DE 31; the planning
    MDEs above are quoted at 31 and 51 (or 15) so the reader sees both ends. Flagged for the challenger (A6).

## 7. Pre-registration census (counts only; before registration; worn pre-window data; no target read)

The census runs once, reads origin-side fields only (no target, no P&L; the only later-slot quantities are the three twins'
states, for `r_gate`, through the **lag-slot loader**, which receives keys and the named fields of captures k + 2 and k + 3 and
returns only the twin term: CH234 the twin `xw`, CH233 the twin `z cl_sib`, CH232 the twin crossing flag; no mid, spread, bid, ask
or volume of a later slot reaches census code, unit test 8.3), prints counts, and is committed with its sha256 before the
registration commit. **Every gate threshold below is stated now, before any census.** A failed gate drops that test before
registration (uncounted); `k_tests` lists the survivors. **Input identity:** the census refuses unless every input file it opens is
named in the LT11 seal with an equal sha256, builds slots and origins from the seal, and refuses if a sealed file in a needed slot
is absent locally.

**Inputs (a fresh seal; rule 9).** Span **`[2026-10-28T00:00Z, 2026-11-07T00:00Z)`**, 10 UTC days, 120 capture slots; the 12 slots
before it (`[2026-10-27T00:00Z, 10-28T00:00Z)`) as look-back only (`rv24*`, the 24 h change, the carry window, the earlier slots of
the day) and the 3 slots after it (twins only, through the loader). Files: complete captures (rows, sidecar, manifest), 135
captures x 3 files, planning 1.0-1.4 GB. No sweep and no feed capture is read by the census.
- **Restore, seal, census: each once.** q0690 accepts host copies that pass a sha256 check against the archive catalogue and
  restores the rest byte for byte from the data releases (snapshot retention is 8-10 days, so the span's first days will have left
  the host by the seal date); it measures bytes first and **stops and asks the owner** if the restore would exceed the host's free
  disk (CLAUDE.md storage stop rule); a file found in neither place is genuinely missing (counted, never substituted). q0691 writes
  `seals/lt11_census_inputs.json` (files, sha256, the seal's own slot assignment and the **frozen LT11 design-text sha256**, so the
  seal is written only after the freeze); the orchestrator commits it before the census runs.
- **Minimum covered days** (covered origins / 12): >= 7.0 for each test (>= 5.0 for twin pairs). Below it every gate of that test
  is NaN and fails.
- **Header pre-check** (before the census code is frozen; headers only, no rows): rows carry `received_utc`, `bid`, `ask`,
  `liquidity`, `volume24hr`, `chg_1h`, `end_date`, `event_id`, `neg_risk`, `neg_risk_market_id`, `neg_risk_other`,
  `event_neg_risk_augmented`; sidecars carry `received_utc`, `fee_category`, `fee_type`, `order_price_min_tick_size`,
  `rewards_min_size`, `rewards_max_spread`, `clob_rewards`, `volume_num`; manifests carry state and times. The pre-check records
  whether `chg_1d` and `chg_1w` exist (K, 1.7). A missing field makes the dependent gate NaN. **Band unit check (CH232):** the median
  `rewards_max_spread` over carry-rewarded rows lies in [0.5, 20] (cents), else every CH232 gate that uses `v` is NaN.

**Projection** = census count x 21 / covered days. **Distinct events:** distinct events over the covered days x 21 / covered days
(pessimistic; LT8's generalised two-day form printed). **Effective counts** = units in markets with >= 2 units of the test's
population in the census days. **Design effect:** `DE_gate = max(floor, 1 + (m_21 - 1) x 0.02)`, `m_21` the projected size-weighted
mean cluster size by event; floors **6.196 (CH234)**, **5.0 (CH233, CH232)**. **MDE gate formulas (multiplier 3.47), each
`max(declared, design)`** with LT8's definitions (*declared* = the closed formula at the census's own effective counts, `DE_gate`,
`sqrt(max(1, VIF_w))`, gap and the declared SD; *design* = `3.47 x 1.5 x SD x se_1` from the census regressors under a working
covariance with unit variance, within-event equicorrelation 0.02 and independence across events; no target read): CH234 and CH233
slopes at the census tercile gap of the tested term; CH232 the class contrast. **F-MDE** = `max(design-based MDE of Δ in the arm
model, MDE x sqrt(2 / (1 - max(0, r_gate))))`, `r_gate = max(r_w, r_pool)` of the lead and twin on census units with both
(within-market on expanding-past demeaned values over markets with >= 3 such units). SDs: `c` 4c, `ds` 2c. **Count gates are on
gross projected counts** (all of the test's filters, no 0.8 factor); the declared MDE uses the measured effective share in place
of planning's 0.8, never on top of it.

| Test | Gate (all must hold; NaN fails) | Map number it sits near (planning only) | Values fixed into the spec |
|---|---|---|---|
| **CH234** | **projected traded units (all 2.2 filters) >= 187,740 (>= 745 a capture)**; projected quote-only units >= 84,420 (>= 335 a capture); **unknown share** (2.3) among eligible movers <= 0.40 (pooled); captures whose movers are > 80% unknown <= 25% of covered captures; within and pooled `|corr(1[unknown], xw)|` <= 0.3 and `|corr(1[unknown], w)|` <= 0.3; projected distinct events with a traded unit >= 500; cap share >= 40% of traded units in events with `n_members <= 10`; **identification:** within-market-day SD of `w` >= 0.1 in >= 50% of mover market-days with >= 2 traded moves, and within-market IQR of the residual of `xw` after OLS on the controls >= 0.25 in >= 50% of markets with >= 6 traded units (>= 30 such markets); `VIF_w(xw)` <= 2.0; within and pooled `|corr(xw, x)|` <= 0.5 for x in {`log1p liquidity`, `z log rv24*`, `d_k`, spread_k}; venue-clock: the most common slot of day holds <= 50% of traded units; block-gate share >= 50% of traded units in markets with >= `ceil(16 x covered_days / 21)` units; `r_gate` <= 0.3; **slope MDE <= 0.5c; F-MDE <= 0.5c** | traded 1,239 a capture before LT11's rules; unknown about 19% of movers; `w`'s SD share 0.70; DE unmeasured | `w` and `|d|` centres and scales; `xw` tercile cuts and gap; `exclude_family`; world 3's `q` (the unknown share) |
| **CH233** | **completeness:** complete member rows >= 60% of eligible member rows in events of 3-10 members (all sizes printed); projected complete member units (3-10 members, all filters) >= 252,000 (>= 1,000 a capture); projected distinct events >= 500 and events with >= 48 units >= 100; **working range:** `hb_k` within two ticks of zero (`hb_k <= 2 x tick`) on >= 5% of complete event-captures; **identification:** within-event SD of `cl_sib` >= 1 tick in >= 50% of events with >= 48 units; `VIF_w(z cl_sib)` <= 2.0; within and pooled `|corr(z cl_sib, x)|` <= 0.5 for x in {`d_k`, own bid change, own spread change, `log1p liquidity`, `z log rv24*`, `hb_{k-1}`}; venue-clock: the most common slot holds <= 50% of units with `|z cl_sib| >= 1`; block-gate share >= 50% of units in events with >= 16 shiftable captures; `r_gate` <= 0.3; **slope MDE <= 1.0c; F-MDE <= 1.0c** | completeness 0.85-1.00 / 0.65-0.97 by size (event-level, not row-level); `hb` near zero 12.6%; SD share 0.83-0.85; units by size unprobed | `s_c` by size class; tercile cuts and gap; `exclude_family` |
| **CH232** | finite reward status on >= 95% of approach-zone units (pre-exclusion); band unit check; **projected counted reward-panel crossings (`xo` = 1, all 4.2 filters) >= 15,120 (>= 60 a capture)**; projected control-panel crossings >= 6,048 (>= 24 a capture); **re-crossing:** <= 60% of reward-panel crossing market-days have >= 3 outward crossings of a boundary (the >= 2 share printed); projected distinct events with a counted crossing >= 500; cap share >= 40%; venue-clock: the most common slot holds <= 50% of counted crossings; within and pooled `|corr(xo, x)|` <= 0.5 for x in {`log1p liquidity`, `z log rv24*`, `|d_k|`}; `VIF_w(xo)` <= 3.0; block-gate share >= 50%; `r_gate` <= 0.3; **class MDE <= 1.0c; F-MDE <= 1.0c**; the 1.4.2 reading recorded in the header (not a gate) | rewarded outward first crossings 79 (73 ex-tick) all origins; zone share unprobed; re-crossing (>= 2) share 0.59 | `exclude_family` |

- **Descriptive (no gate):** sports and crypto splits; the top series family's share; events and their 21-day projections; the
  `n_members` distribution and the cap's loss; pairwise unit overlaps among the three populations; class or tercile shares by
  liquidity tier; `vol_missing`, `mom_missing`, `hte_unknown` shares; the computed DE beside `DE_gate`. **CH234:** the unknown
  sub-class counts by capture (its time profile) and by bin; traded, quote-only and unknown counts by the four bins; `w` and `|d|`
  distributions; the winsorised share. **CH233:** completeness by size class at row and event level; `members_changed` and
  `nr_key_conflict` counts; `hb` quantiles; `corr(z cl_sib, z ca_sib)`; the headroom-crossing count; M4's rank shares. **CH232:**
  crossings by boundary and direction on both panels; `xr`, `day_gap`, `tick_coincident` counts; the zone's share of all outward
  crossings; the zone units without a crossing; the inward (S1) and pseudo-boundary (S2) counts; the carry-versus-simple reward
  reading agreement (the map's reading against `listed_carry24h_v2`, counts only).
- **Order and lane:** one census job (CC11) streams the captures once and evaluates the three gate blocks independently; a test
  whose block fails has its reader kind switched off before the reader's code freeze.
- **Expected census fates (declared now).** CH234: the count passes with margin; the F-MDE gate is the likeliest killer (it needs
  DE near 6.2-8 and `VIF_w` near 1.3), then the unknown-share gates. CH233: the corr gates against the own move and the block-gate
  share are the risk; power is not. CH232: the 60-a-capture crossing gate (the zone share is unprobed) and the F-MDE gate at the
  computed DE and `VIF_w`; **expected to die at census more often than not.**

**Census and later jobs (to be drafted under `docs/research_lab/queue/drafts/` in README format; ids q0690-q0695, checked unused
in the history of every local and remote-tracking ref on 2026-10-23: the q06xx ids in use are q0600-q0604, q0620-q0623,
q0640-q0647, q0660-q0667 and q0680; none is written in this commit).**
- `q0690_lt11_census_restore` (lane `net`, about 1,400 MB disk, `mem_mb` 400): restore the span's files, check sha256s, write the
  restore report; bytes measured first (disk stop rule). `depends_on` the LT11 design-text freeze; `not_before`
  2026-11-07T03:00Z.
- `q0691_lt11_seal` (lane `net`, `mem_mb` 300; after q0690): `run_live_tests11.py seal` writes `lt11_census_inputs.json`.
- `q0692_lt11_census` (lane `net`, `mem_mb` 600, streaming per capture with a two-capture window and per-market 12-slot state; if
  the code-phase dry run measures a peak above 600 MB, lane `cpu`, `mem_mb` 1,200, **exclusive**; after the seal commit).
- `q0693_lt11_size_check` (lane `cpu`, `mem_mb` 800; after the census values are committed, so k is fixed before any size result;
  `max_retries 1` deterministic-crash only).
- `q0694_lt11_reader` (fallback only, never promoted while the cron line of 8.2 exists).
- `q0695_lt11_analysis` (lane `cpu`, `mem_mb` 4,000, **exclusive**, `not_before` the analysis date).
All are DRAFT and must not be promoted before the challenger review, the design-text freeze, the code and its freeze check, and
**never while E011's, LT2's or E015's analysis job, or an LT9 or LT10 census, size-check or analysis job, is running**
(memory-heavy-jobs rule). Each counts 0.

## 8. Implementation plan (no code in this commit)

### 8.1 Modules to be written (engineering list)
- `backend/astrolabe/research_lab/live_tests11_base.py`: vendored, hash-pinned, unmodified copies of the LT3-LT9 pieces LT11 reuses
  (`move_join`, `classify`, the slot grid, LT7's `RewardCarry` with its `_status_array` fix, LT5's `block_fl_gate`, LT3's
  `paper_taker` and `econ`, LT9's lag-slot loader and seal helpers, `cb17_census.is_sports_sidecar`, the crypto classifier); a
  provenance test checks each copy against its source hash. **No E026 frozen file is imported, copied or edited.**
- `backend/astrolabe/research_lab/live_tests11.py`: unit builders (2.2-2.4, 3.2-3.3, 4.2-4.3), the reader (per-capture series,
  write-once statuses, twins and readings online), `ops-stats`, the census (7), the event-phase gate wrapper, the size-check worlds
  (1.8.1), the analysis (1.7-1.10).
- `scripts/research_lab/run_live_tests11.py` (`seal`, `census`, `size-check`, `reader`, `backfill-series`, `ops-stats`, `analyze`).
- `backend/astrolabe/research_lab/model_specs/live_tests11_v1.json` (unpinned until 8.4), `battery2.KIND_RULES["live_tests11"]`.

### 8.2 Resources, collection plan and install
- **No new collector and no network.** A pure reader of the pass's captures and sidecars (sweeps for CH232's M3, the feed for its
  CLOB sensitivity), once a capture.
- **Memory (planning, then a ladder).** LT4's measured host dry run 484-525 MB; LT9's planning 400-600 MB. LT11 holds per market the
  last 12 mids, the last `volume_num`, the day's crossing flags and the carry texts, and per neg-risk event the previous capture's
  member bids and asks: **planning steady 300-450 MB, peak 450-600 MB in a backlog pass.** Ladder, measured by a host dry run with
  the exact install command before the pin: (1) one reader under `ulimit -v 1572864`, accepted if peak RSS <= 650 MB; (2) else two
  readers (CH234 + CH232; CH233) under one shared `flock`, each <= 650 MB; (3) else no pin and LT11 is not registered (recorded).
- **Install route: host cron** `20 */2 * * *` (109 minutes after each :31 capture start, 11 minutes before the next), own `flock`,
  `nice -n 19`, `oom_score_adj 1000`, `ulimit -v 1572864`; the queue draft q0694 is the fallback, **never both**.
- **Concurrency:** LT10's 5-minute reader (< 200 MB) and E026's collector run in the same weeks; no LT9 reader runs before late
  December. Peaks additive at most about 0.9 GB on the host.
- **CPU:** about 1-2 minutes a steady pass (estimate). **Disk:** about 1.5-2.5 GB over the window (CH233's member units dominate);
  the reader refuses above 3.0 GB in `live_tests11/`.
- **Analysis job:** about 1.5-3 million unit rows (CH233 1-2 million); the block gate refits 200 times per test; planning 3-4 GB
  peak, **exclusive**, single run.
- **Host change:** installing the cron line is a host change under the standing collection authorisation, done by the
  orchestrator.

### 8.3 Tests to be written (`backend/tests/unit/test_research_lab_live_tests11.py`, synthetic only)
Causality (no unit builder reads capture k + 1 or later; the decision time is capture k's last receipt); the three `volume_num`
classes with every unknown sub-class, and a test that no other field re-classes an unknown mover; the winsorisation and the
centred product; the approach zone, the first-of-day rule, `xr`, `day_gap` and tick coincidence; the event key, `members_changed`,
`event_incomplete`, the 3-10 size rule and the sign of `cl_sib`; the event-phase gate keeps one offset per event; the lag-slot loader
returns only twin terms; `ops-stats` reads no price, spread, volume or depth column; spec NaN refusal; seal and pin refusals; the
analysis refuses before the analysis date and on a pin mismatch; the size-check worlds generate the declared shapes; the vendored
copies match their source hashes; the E026 pin test stays green.

### 8.4 Registration steps and pins (in order)
1. Challenger R1 on this file; the response and any re-check.
2. **Design-text freeze commit**, its sha256 in the ledger, the venue page's reward-rule sentence and retrieval time recorded
   (1.4.2), **before 2026-11-14T12:00Z and before `T_E015`** (planned by 2026-11-05 so that the code check precedes the seal). At
   the freeze, the embargo requests of section 9 are filed in `signal_engine/CANDIDATES.md`.
3. Code (8.1, 8.3), vendored by hash; a `science-reviewer` freeze check of the census and size-check code against sections 1.8,
   1.8.1 and 7; fixes (none may change frozen text).
4. q0690 restore, q0691 seal, seal committed and pulled on the host (after 2026-11-07T00:00Z).
5. Census q0692 (counts only); drops recorded in the ledger and in a short census-drop note; `k_tests`, scales, cuts and
   `exclude_family` filled with the exact census floats; a freeze record (module hashes, spec hash before the pin, census output
   hash re-verified on the host, spec values checked against the census JSON).
6. Size check q0693 (2,000 worlds x 200 draws, seed 20261497); results recorded per test.
7. Reader freeze check; host dry run with the exact cron command following 8.2's ladder (the step used is recorded).
8. The embargo entries of section 9 verified in `config.EMBARGO` and `signal_engine/CANDIDATES.md` (a missing entry blocks the
   pin); any token or limit made only for a test dropped at census withdrawn with a ledger line.
9. Pins: `SPEC_SHA256`, `code_sha256` map, `code_check` passing; E-numbers assigned from the ledger; the ledger entry is the
   registration commit, **before 2026-11-17T00:00Z** (fast lane) and at least 24 h before `REGISTERED_UTC`.
10. Install the cron line and run `backfill-series` within `[REGISTERED_UTC - 72 h, REGISTERED_UTC - 24 h]`; verify `pinned: true`
    and `nothing_new` before `REGISTERED_UTC`; queue q0695 with `not_before` the analysis date.

**Timetable (fast lane, planning):** R1 and response by 2026-10-30; freeze by 2026-11-05; code and its check 11-01..11-06; restore
and seal 11-07..11-08; census 11-08..11-09; size check 11-09..11-11 (not beside E011's analysis); reader check and dry run
11-12..11-14; embargo verification and pin 11-15..11-16; window 11-18..12-09; analysis on or after 12-10T12:00Z.

## 9. Signal-engine mapping and embargo requests

Every family below is point-in-time from the origin capture and its 12-slot look-back (DESIGN_V1 16 causality) and is an
**auxiliary family** (own write-once table and version string). **Embargo first** (DESIGN_V1 8): any challenger that isolates one
of these families carries its token until **the LT11 date = the later of 2026-12-12T00:00Z and LT11's analysis commit** (the
analysis date 2026-12-10T12:00Z plus about 36 h; in the ordered lane, the later of its analysis date plus 36 h and its analysis
commit). **Timing:** filed in `signal_engine/CANDIDATES.md` **at the design-text freeze** (CANDIDATES' round-16 note: "tokens are
requested only at LT11's freeze") and applied before the registration commit (8.4 step 8). This branch does not edit
`CANDIDATES.md`, engine code or `config.EMBARGO`.

| Test | Family (aux version) | Columns (NaN = missing) | Source and clock | Token -> until |
|---|---|---|---|---|
| CH234 | `dollarw` (`se-aux-dollarw-v1`) | `dw_w`, `dw_xw`, `dw_traded`, `dw_quote_only`, `dw_vnum_unknown`; and **`tilt`'s `tl_w2h` and `tl_w_traded`** (round 16 CH235) | captures k - 1 and k, their sidecars | `dollarw` (new) -> LT11 date |
| CH233 | `nrslack` innovations (`se-aux-nrslack-v1`) | `nr_cl_sib`, `nr_ca_sib`, `nr_dheadroom_sib`, `nr_dshortfall_sib`, `nr_hb_cross` | complete event-capture pairs (k - 1, k) | `nrslack` (new) -> LT11 date; the `event` family's existing levels (overround, quoted share, normalisation gap, headroom levels) **not** requested |
| CH232 | `bandside` (`se-aux-bandside-v1`) | `bs_dist`, `bs_zone_out`, `bs_xo_first`, `bs_xr`, `bs_xi_first`, `bs_dear_side`; and the `rewards` family's planned `rw_cross_out_2h`, `rw_cross_in_2h` | captures k - 1 and k, the UTC day's earlier slots, the carry window | `bandside` (new) -> LT11 date |

**Requests to the signal-engine track.**
- **Pre-freeze hold (now, repeating CANDIDATES' "do not isolate before its freeze"):** no scored family holds `tl_w2h`, a product of
  a collateral weight and a move's size, a neg-risk siblings' bid- or ask-sum change, or a 0.10 / 0.90 crossing indicator before
  LT11's freeze. `tilt`'s other columns (`tl_collat`, `tl_cheap_side`, `tl_fee_ps`, `tl_rebate_ps`) are levels and may be built.
  If `tl_w2h` is scored in any family before the freeze, CH234 carries *informed (tilt)* and the ledger records the first scored
  capture.
- **New tokens `dollarw`, `nrslack`, `bandside`** to the LT11 date, entered at the freeze and before any isolating challenger.
- **New attribution limit `attrlimit_lt11`** (`kind: attribution_limit`) to the LT11 date: no attribution (SHAP or otherwise) of
  the champion, se1 or any broad model on mid x own 2 h change interactions, on neg-risk siblings' bid- or ask-sum differences, or
  on indicators of a mid crossing 0.10 / 0.90, computed or shown before the LT11 date; no LT11 family added to a broad model before
  then (`no_broad_families: ["dollarw", "nrslack", "bandside"]`), or such a model recorded in the ledger as a development look.
- **Not requested:** `rewards` (to the later of 2026-11-18 and E022's analysis commit, unchanged), `movetype` (11-22, unchanged:
  `tl_w_traded` is covered by `dollarw` from the freeze), the `event` family's levels, `tte`, `flow`.
- If a test drops at its census, its token and any limit item made only for it are withdrawn with a ledger line (the round-4
  rule).
- **Note to LT9 (no request):** LT11's analysis (on or after 2026-12-10T12:00Z) precedes LT9's pin (before 2026-12-29); LT9's
  design text is frozen and its census runs in mid-November, so no LT9 value can follow an LT11 result; LT9 may record LT11's
  analysis commit time beside its pin.

The engine's yardstick (log-loss gain under `se-promotion-v2`) is a different question from each LT11 primary. A Supported LT11
primary makes its family a candidate; an engine gain never changes an LT11 verdict and an LT11 verdict never promotes a model.

## 10. Disclosures
- **What was read to write this file:** `CREATIVE_HYPOTHESES_2026-10-30.md` (sections 0-3), `CH240_MAP_2026-10-23.md` (whole, 50
  lines), `LIVE_TESTS_9.md` (sections 0-1, 7, 8.2, 8.4, 9), `LIVE_TESTS_10.md` (header, 0, 1.0-1.1), `LIVE_TESTS_8.md` and
  `LIVE_TESTS_7.md` (the `m_21` definitions), bounded greps of `EXPERIMENT_LEDGER.md` (LT8-LT10, CH240, census entries),
  `signal_engine/CANDIDATES.md` (rounds 7, the LT8 withdrawals, round 16's families), `lab_dashboard/README.md` and `registry.json`
  (the LT7-LT10 entries), `backend/tests/unit/test_lab_clients.py` (registry tests). No host, network, `ssh`, `data-dumps`,
  evidence JSON, census output, prediction, target or P&L.
- **The CH240 map** counted populations on captures 2026-10-16..10-23 (k - 1 and k only); **it read no target, no price change after
  an origin and no P&L**. Its numbers were seen before every gate in this file was written (10.1).
- **Development looks:** HB1's PX1 (survived), PX5 and MI4 (not survivors), XM1-XM3 (nulls or not survivors), E005 (not supported,
  challenger CONFIRMED); the engine's LightGBM se1 (mid and own 2 h change) and the `event` family's level scores (visible since
  2026-10-22T12:00Z) are visible development scores near CH234's and CH233's objects. None reads an LT11 state as defined here.
- **Known before the freeze:** E015 and E022 results are not known at the planned freeze; LT10's and LT9's census outputs are not
  read (1.6).
- **The reward rule's wording** is disputed in AREPO's documents (1.4.2); the design does not depend on the reading for its
  primary.

### 10.1 Values declared now and their planning sources (all before any LT11 census)
| Value | Where | Source | Informed by the CH240 map? |
|---|---|---|---|
| CH234 count gate 745 a capture | 7 | round 16's F line (`n_eff` 150,500) | **yes** (chosen over the round's 335 after seeing 1,239; 6.1 item 13) |
| CH234 unknown-share gates (0.40, 0.80 / 25%, corr 0.3) | 7 | conventions | **yes** (the map's warning that `volume_num` is often missing made a gate necessary; the values are conventions with the map's 19% in view) |
| CH234 `w` SD gate (0.1 in 50%) | 7 | round 16 | the map measured 0.70 against it; value unchanged |
| CH234 band [0.04, 0.96], bins 0.15 / 0.85, winsorisation 0.20 | 2.2, 2.4 | the tick rule, PX1, convention | no |
| CH234 planning DE 6.196-10 | 2.5 | E022's `m_21`, proportional scaling | partly (the map's traded count sets the scaling) |
| CH233 3-10 member rule | 3.2 | arithmetic (6.1 item 7), round 14 rule 7 | **yes** (seen with the map's completeness by size) |
| CH233 completeness 60%, working range 5%, SD gate 50% | 7 | round 16 rule 16 and CH233's census | the map measured them above the lines; values unchanged; the denominator (3-10 members) is **informed** |
| CH233 count gate 1,000 a capture | 7 | twice the F-MDE kill line at DE 51 (LT9 CH214's practice) | no |
| CH232 zone 0.04 | 4.2 | the planning SD of the 2 h mid change | no |
| CH232 crossing gate 60 a capture | 7 | round 16's verdict line | **yes** (chosen over the round's 24 after seeing 79; 6.1 item 13) |
| CH232 re-crossing gate (>= 3 crossings, 60%) | 7 | round 16, unchanged | **yes**: the map measured a different quantity (>= 2 crossings, 0.59); the round's definition is kept and the >= 2 share printed (ambiguity A7) |
| `DE_gate` floors 6.196, 5.0, 5.0 | 7 | E022, LT9 | no |
| Seed 20261497; queue ids q0690-q0695 | 1.8, 7 | unused values | no |

## 11. DESIGN-AMBIGUITY items for the challenger review
- **A1 (CH232, causal frame).** Is the approach-zone population (6.1 item 1) the right replacement for the round's 12-slot
  market-day frame, and is the zone half-width 0.04 acceptable, or should the zone be wider (crossings from farther are lost) or
  the population the whole reward panel with `xo` as a per-capture event (more reference units, a larger DE)?
- **A2 (CH232, reading).** Is a primary sign that holds under both readings of the reward rule (1.4.2) sound, or does the
  documented reading (one-sided farmers must add the dear side to keep scoring) predict narrowing often enough that the sign is
  not fixed by the mechanism? Should the venue page be re-read now, before R1, rather than at the freeze?
- **A3 (CH234, E015).** The fast-lane freeze precedes `T_E015`, but the census-fixed values (centres, scales, cuts) may be committed
  after it. They are mechanical counts; is "disclosed, no label" right, or should CH234 carry *informed (E015)* if any census value
  is committed after `T_E015`?
- **A4 (CH234, F binding).** F binds because `d_{k+1}` is the next unit's state. At the pessimistic DE (10) the F-MDE gate fails at
  the low planning count. The designer rejected an F label plus a point condition (LT10 CH223's form) as a design chosen for power;
  the challenger should rule.
- **A5 (CH234, the tested term).** Is the centred product with both main effects the right reading of "the dollars behind the
  move", or should the primary be the round's raw product (kept as M4), or the traded-minus-quote-only difference in the `w` slope
  (which removes level drift by design but needs both classes' counts)?
- **A6 (DE floors).** CH233 and CH232 plan at DE 31 but gate at `max(5.0, computed)`; a computed DE far below 31 would let CH232
  pass. Is LT9's floor right here, or should the floor be the planning DE?
- **A7 (CH232, re-crossing).** The round's line counts market-days with >= 3 crossings; the map measured >= 2 (0.59). Keeping the
  round's definition is the pre-map choice; the challenger should rule whether it guards the stated risk (ladder chatter), given
  that `xr` already separates re-crossings.
- **A8 (CH233, members).** Are "Other" and placeholder members right as members of the sum; should augmented events
  (`event_neg_risk_augmented`) be a reported arm; is requiring every member two-sided (rather than treating a missing bid as a
  zero contribution) right?
- **A9 (K block).** Market age is not on the rows and is omitted; `chg_1d` / `chg_1w` enter only if the header pre-check finds them.
  Is a control set fixed by a header read acceptable, and is K close enough to the champion's families for the "beyond momentum and
  market state" reading?
- **A10 (CH234, missingness).** If the census shows the unknown class is capture-level (whole captures without `volume_num`), is
  excluding those captures' movers (a time-based selection) acceptable, and is world 3 the right leak world?
- **A11 (CH232, panel point condition).** Is a point condition (control-panel coefficient below half the rewarded one) enough to
  separate the rule's effect from a generic boundary effect, given that the interaction's MDE (about 0.85-1.01c at DE 31) is near
  the floor?
- **A12 (timing).** The fast lane leaves about nine days from the seal to the pin beside E011's, LT2's and E015's analyses. Is the
  lapse rule (no slide; the ordered lane with a fresh census) the right fallback, and should a test dropped by the fast-lane census
  stay dropped in the ordered lane (declared: yes)?
- **A13 (CH233, the record).** E005's null on mids and XM3's not-surviving sibling result are disclosed; does the bid-sum
  innovation on the spread differ enough from them to be a new test rather than a re-test of a closed subject?

## 12. Draft ledger block (DRAFT, not registered, not counted)
```
## LT11 design draft, 2026-10-23 (experiments autopilot; nothing counted)
- Draft docs/research_lab/LIVE_TESTS_11.md on feat/live-tests-11: CH234 (dollar weight of a move), CH233 (neg-risk bid-sum
  headroom and the next spread), CH232 (rewarded first crossings of 0.10 / 0.90). DRAFT, not frozen, R1 not run, not registered.
- Planning inputs from the CH240 map (counts only; no target or P&L read); census on a fresh seal [10-28, 11-07).
- Fast lane: freeze before 11-14T12Z and T_E015; window 11-18..12-09; analysis after 12-10T12Z. Designer's census odds
  0.35 / 0.50 / 0.20; P(no test) about 0.26.
```
