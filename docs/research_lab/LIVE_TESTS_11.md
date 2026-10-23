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
  it passes at E022's design effect (6.196) and fails at the design effect its larger population may compute (about 10, a
  projection, 2.2); `VIF_w` of the centred product and the differential-missingness gate on `volume_num` are the other
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
  *month-start-sensitive* (1.1); *volume-missing sensitive* (CH234: the Lee-type bounds of 2.3 include 0);
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
