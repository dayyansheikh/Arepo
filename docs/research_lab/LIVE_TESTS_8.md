# Live tests 8 (LT8): three round-13 candidates (CH203, CH202, CH204), DRAFT pre-registrations

**Status: DRAFT. Challenger R1 (2026-10-22, REVISE, 8 must-fix) is answered in section 13, which governs where earlier text
differs. Not registered, nothing counted, no code, no census run.** Drafted 2026-10-22 on branch `feat/live-tests-8` from the
`chore/arepo-claude-setup` tip `5ffe8229`, a design-only first commit like the first commits of LT3-LT7; the R1 response
applies **only** the review's items (section 13, must-fix 2). E-numbers are **not** assigned here. E026 is the last number used; LT5 and LT6 closed with
every test dropped at census and hold none (re-check fix 4), so the next free numbers pass to LT7 for whichever of its tests
survive, and then to LT8; LT8 takes the next free numbers at its
own registration (provisionally in the order CH203, CH202, CH204 for the tests that survive). If every test drops at its
census, LT8 is not registered (recorded in the ledger; nothing counted). Before registration this needs, in order:
1. a challenger review (`science-reviewer`) of this file, the response, and any re-check;
2. the **design-text freeze commit** (section 1.1) before the earlier of 2026-11-15T12:00Z and `T_E015`;
3. the census input restore and seal (section 7), each once, restored and re-hashed from the data releases;
4. the code (section 8), a freeze check of code against design, and the fixes;
5. the counts-only censuses (section 7), each once, which fix k and every census-fixed spec value;
6. the size check at >= 2,000 worlds on the code to be pinned, through the census-fixed strata (section 1.8);
7. a host dry run with peak RSS measured (section 8.2);
8. **LT7's registration commit (or its recorded drop)**, the `SPEC_SHA256` and `code_sha256` pins, the ledger entry and the
   reader's installation (section 8.4). The engine embargo entries of section 9 are **not** a registration step: they are
   filed and applied when the design is accepted, and in any case before 2026-12-01T00:00Z (section 9).
Until the pin exists, every line a reader writes is `prospective_unregistered` by construction.

This is research tooling. AREPO never trades. No edge, calibration, profitability or tradability claim exists or is implied.
Every count quoted from the round-13 file, LT4/LT5/LT7 censuses or planning, the cost model, the maker-rewards snapshot or the
signal-engine notes is a **counts-only development figure on worn data**. Every MDE here is a **planning estimate** built on
stated assumptions, not a measurement. Nothing here read a price after an origin, an outcome, a target or a P&L. No host,
network, `ssh`, `data-dumps` or evidence-JSON read was used to write it. Two non-data reads fixed definitions: the file list
of the committed seal `seals/lt7_census_inputs.json` (file names, slot assignment and hashes only, to count which sealed
slots exist; section 7) and `research_lab/book_sweep.py`'s field list (`n_bid_levels` / `n_ask_levels` count every level of
the side, not the 5c band; section 2).

Source ideas: `CREATIVE_HYPOTHESES_2026-10-27.md` (round 13) section 3, ranks 1-3: **CH203** (the quiet book), **CH202**
(seven minutes or two hours: the sweep clock, held against fresh) and **CH204** (the market's own clock). Rank 4 (CH205, steam
at the book) is **deferred** for the owner's sports-scope decision; rank 5 (CH206, the reward start) is a **map first** (a
counts-only count of future reward configurations); ranks 6-10 (CH207-CH211) are engine-first and not taken (section 5,
6.2). The design is written to round 13's rules (its section 0.1), to LT4's lessons L1-L15 and its R1/R2/census/freeze record,
to LT5's R1, re-check, census-code-check rulings and census deaths (7.3), to LT6's R1 and re-check rulings, and to LT7's R1,
re-check (13, 13.5) and census-code-check rulings. Every design change from the round's sketches is listed with its reason in
6.1; all were made before any data. The handles are the CH numbers themselves.

## 0. Summary

| Handle | Idea | Hypothesis (direction) | Population | Primary | Planning MDE (DE as stated; multiplier 3.47): slope or class MDE; F-MDE; **max**; at a quarter of the units | Floor |
|---|---|---|---|---|---|---|
| **CH203** | the quiet book | Within a market, the YES mid change from capture k + 1 to k + 3 rises with the **innovation of the 5c depth imbalance** between the sweeps of passes k - 2 and k - 1 (both received before capture k), on a touch that did not move, the imbalance level held fixed (one-sided, > 0) | non-sports ex-crypto eligible two-sided books with a quiet touch, events of <= 10 members; captures + sweep 1 of passes k - 2 and k - 1 | expanding-past demeaned OLS of `y_s` on `zdimb5` with `z imb5_{k-1}` a control; **block Freedman-Lane gate**; **far-future innovation falsification is a verdict condition** | slope 0.35c at the tercile gap (DE 31, `n_eff` 1.0M; 0.25c at 2.0M); F 0.50c at `r_w` 0 (0.56c at 0.2); **max 0.50-0.56c** (quarter 1.0-1.1c); passes F only at `n_eff` >= about 1.0-1.4M | 0.5c (tercile) |
| **CH202** | the sweep clock | Within a market, a 2 h move that the CLOB had **already made by the first sweep of pass k - 1** (held, `early_share >= 0.75`) persists more from k + 1 to k + 3 than one that arrived after it (fresh, `early_share <= 0.25`), the signed Gamma 1 h change held fixed (one-sided, > 0) | non-sports ex-crypto 2 h movers at k with sweep 1 of pass k - 1 two-sided; captures + that sweep | expanding-past demeaned OLS of `c_skip` on 1[held] over held and fresh units; **block Freedman-Lane gate**; binding leak worlds with a noisy, lagged `chg_1h` proxy (R1 must-fix 7); F a reported label | class 0.38c (DE 6.196, low count; 0.29c high); no F (reported label); **max 0.38c** (quarter 0.76c); at its count-gate floor (201,600 held plus fresh) 0.33c raw / 0.37c effective with 15% class shares, 0.52c at the least favourable split the gates allow (R1 must-fix 4) | 0.5c |
| **CH204** | the market's own clock | Within markets whose own |2 h moves| concentrate in one slot of the day (scheduled, 7-day look-back), the |move| over (k + 1, k + 2] is larger when that interval ends in the market's hot slot, the venue's slot-of-day pattern held fixed (one-sided, > 0) | non-sports ex-crypto eligible markets classed scheduled at capture k, events of <= 10 members; captures only (84-slot own look-back) | expanding-past demeaned OLS of `a = |mid_{k+2} - mid_{k+1}|` on `sc_hot` with 11 slot-of-day dummies; **block Freedman-Lane gate**; rotated-schedule F a reported label | class **0.57c** (DE 31, low count; **0.40c** high; 0.66c / 0.47c at DE 41; R1 must-fix 3); no F (reported label); **max 0.57c** (quarter 1.14c); passes 0.5c only with >= about 2,550 hot units a day | 0.5c (class) |

- **Family:** one Holm family over the k surviving primaries, one-sided, familywise alpha 0.05, separate from E009-E011, LT2
  (E012-E014), LT3 (E015), LT4 (E022), LT5, LT6, LT7, E025 and E026. **Provisional k <= 3.** A test whose census gate fails
  is dropped *before* registration, uncounted; k is the number that survive, fixed in the spec (`k_tests`) at registration
  and never changed. A primary that is unavailable or fails its gate enters Holm with p = 1. No replacement test is added
  after a census drop (CH205 cannot join this family later; section 5).
- **Window (proposed):** whole captures with start in `[REGISTERED_UTC, END_UTC)`, 21 days, `REGISTERED_UTC =
  2026-12-30T00:00:00Z`, `END_UTC = 2027-01-20T00:00:00Z`; single analysis on or after **2027-01-21T12:00:00Z**. Keyed to
  LT7's `END_UTC` (proposed 2026-12-29T00:00Z; with LT5 and LT6 both closed, LT7 registers after their recorded drops and
  its window follows only its own rules (a) and (c), the only remaining source of a slide; re-check fix 4) plus 24 h, **never earlier than
  2026-12-30T00:00Z**, and sliding later with LT7 (section 1.1). First origins: CH202 12-30T02:31Z, CH203 12-30T04:31Z, CH204 12-30T00:31Z (section
  1.1).
- **Pin early, run late (round 13 rule 9; LT7's form, tightened).** The design text is frozen **before the earlier of
  2026-11-15T12:00Z and `T_E015`** (planned by 2026-11-10), earlier than the round's 2026-12-07T12:00Z, so that it precedes
  every adjacent analysis except E011's (label only); every test is dropped if its registration is not before `T_LT7`
  (section 1.1). (LT6 closed on 2026-10-22 with every test dropped at census, so the first draft's rule that dropped CH203 if
  the freeze was not before `T_V` is withdrawn; R1 must-fix 1.)
- **Expected outcome, declared now (honest prior odds; re-stated in the R1 response, 13).** Two numbers per test: the odds of
  surviving census, and the odds of then also passing the binding size and mechanical worlds, i.e. of reaching a valid
  verdict. **CH203 is borderline on its F-MDE gate** (0.50c at `r_w` 0 at the low planning count; it passes only if the
  census projects `n_eff` >= about 1.0M at `r_w` 0, 1.24M at 0.2, 1.41M at 0.3); its other risks are the member-cap share,
  the quiet share and the computed whole-panel DE. **It is likely to fail its binding fill-leak world 8** once that world
  carries the `vol_missing` share (at least 0.78; R1 must-fix 8): a fill that leaves no volume trace is the same-signed
  confounder the design cannot separate. Census **0.30**; valid verdict **about 0.10**. **CH202 is borderline** (0.38c at
  the low count; the block-gate share of all movers is untested; the signed 1 h change may inflate `VIF_w`), and its binding
  worlds 3 and 5 now give the model a noisy, lagged `chg_1h` proxy, so the known reversal can leak into the contrast (R1
  must-fix 7). Census **0.25**; valid verdict **about 0.12**. **CH204 is more likely than not to drop** (0.57c at the low
  count; it needs about 2,550 hot units a day; the scheduled share, the event count, the venue-clock and category gates are
  unprobed, and the census days were on summer time while the window is on winter time). Census **0.10**; valid verdict
  **about 0.08** (world 12 is now reported, R1 must-fix 6). **Expected k at census is about 0.65 (0 to 1); the chance that
  every test drops and LT8 is not registered is about one half** (0.70 x 0.75 x 0.90 = 0.47, treating the fates as
  independent, which they are not); **the expected number of tests reaching a valid verdict is about 0.3.** Every taker check
  is expected to be "not shown" (section 1.10).

## 1. Common rules

### 1.0 Lessons carried over (binding from the first draft)

LT4's lessons **L1-L15** (`LIVE_TESTS_4.md` 1.0) and LT7's table of later rulings (`LIVE_TESTS_7.md` 1.0) apply unchanged:
exact `%.17g` writes and round-trip reads; NaN refusals in a pinned spec; sealed census inputs re-hashed (refuse on
mismatch); a pessimistic planning-MDE gate in every census; a simulated size check at >= 2,000 worlds with the limit 0.05 +
1.645 sqrt(0.0475 / worlds) = 0.058; dry-run guards; spec and code pins on every frozen line; write-once per-capture series
and status files; skip targets from capture k + 1; clustering by event, event x UTC day and UTC day with p the largest; Holm
over k counted once; economics never changes a verdict; readers at the pass cadence; an internal run lock; residual-IQR
identification gates; Freedman-Lane gates only with `DE_gate = max(floor, 1 + (m_21 - 1) x 0.02)`; the size check permuting
within the census-fixed strata through the same `strata_of` / `block_anchor` path as the analysis gate; the block
(circular-shift) gate for rolling or persistent states; the liquidity-tier gate; seal completeness and the seal's own slot
assignment; MDE gates taking `max(declared, design)` and carrying `sqrt(max(1, VIF_w))`; memory planned from a measurement
with a ladder; `T_X` keyed conditions; the pinned crypto classifier; the design-text freeze; the lag-slot loader (LT7 R1);
vendoring, not import (LT7 R1 must-fix 10); the F rule and its 0.5c F-MDE cap (LT7 R1 must-fix 7); `r_gate = max(r_w,
r_pool)` (LT7 re-check M2); the block-gate share proxy `ceil(16 x covered_days / 21)` (LT7 re-check M1).

**Census deaths that set LT8's expectations (counts only).** LT5's q0561 (`LIVE_TESTS_5.md` 7.3) dropped F (pessimistic MDE
1.01c > 0.5c, `DE_gate` 10.3 from a projected mean family cluster of 465, all other gates passing), H (counts, look-back
completeness 0.55, market strata 0.0, NaN correlation) and R (crossing share 0.21, design MDE 1.03c, `DE_gate` 11.9); LT5
then closed (2026-10-22 07:35Z, ledger "LT5 closed") with J (MDE 2.16c, 63.7 units a pass, permutable share 0) and O (MDE
0.84c, IQR share 0.44, 372 units a pass) also dropped at census; **these J and O counts have been read** (re-check fix 4)
and changed no LT8 gate. LT4
dropped E020 and E021 at their strata gates and registered E022 alone (DE 6.196, `m_21` 260.8). LT7's own planning expects
k = 0 to 2 of five. The lessons applied here: (i) the MDE gate, not the count gate, is what kills, so every test states the
count at which its MDE gate passes; (ii) a look-back completeness rule must be stated as a unit rule, not discovered at census
(CH204's >= 70 of 84); (iii) whole-panel populations have whole-panel design effects (LT5 F/R's measured 10-12 are below the
round's pessimistic 31-51, which LT8 keeps for planning); (iv) a parser that reads an empty `clob_rewards` as NaN removes the
unrewarded class (LT5 R; LT7 census-code check must-fix 3): LT8 declares an empty `clob_rewards` to be unrewarded (0), unit
tested (section 2).

Round 13's design rules (`CREATIVE_HYPOTHESES_2026-10-27.md` 0.1) map onto LT8 as follows:

| Round-13 rule | LT8 rule |
|---|---|
| 1. Innovations or per-interval labels; levels only as controls; F a label where the state is not level-built | CH203's tested term is an innovation of a book level (F **binding**, 1.9; its F-MDE gate binds at census); CH202's and CH204's tested terms are built from price changes, so their far-future arms are reported labels (LT7's CH191 precedent, R1 answer 2) |
| 2. No sweep state inside its own label window | every sweep state is read from sweep 1 of passes k - 2 and k - 1, both received before capture k started; nothing of pass k's sweeps is a state (sweeps k + 1 and later are targets or the lag-slot F state only) |
| 3. Whole-panel DE 51 / 31 with a declared member cap | CH203 and CH204 (whole-panel) run on events with **<= 10 members** (declared now, 1.4; larger events a reported arm); planning at DE 31 (cap) and 51 (uncapped, the reported arm); CH202 (mover family) at E022's 6.196 without a cap (its <= 10-member arm reported) |
| 4. Direct clocks from host receipts; informed halves named | CH202's clock is the sweep's own `batch_receipt_utc` against capture receipts; its late half is the engine's `b0_gap` (disclosed), and its contrast is informed by E002/E004 (disclosed; the signed `chg_1h` is a primary control, 3) |
| 5. A stream's frame is its population | no LT8 primary reads a keyless stream; CH205 and CH206 are deferred (5) |
| 6-7. External and political frames | none taken |
| 8. Bounded readers | per-capture streaming reader; planning peak <= 650 MB with a ladder (8.2); no panel held in memory beyond the 84-slot mid cache |
| 9. Pin early, name what was seen | the design-text freeze of 1.1 (earlier than the round's date); the `b0_gap` diagnostic and se18's visible broad score disclosed (10) |

### 1.1 Registration, window, single analysis
- `REGISTERED_UTC` is the first 00:00Z that is **(a)** at least 24 h after the LT8 registration commit (spec pin plus ledger
  entry), **(b)** at least 24 h after **LT7's own `END_UTC`** if LT7 is registered, **(c)** never earlier than
  **2026-12-30T00:00Z** (LT7's proposed `END_UTC` 2026-12-29T00:00Z + 24 h). LT8 registers only after LT7's registration
  commit, or its recorded drop (all of its tests dropped at census or the family abandoned, in the ledger). If LT7 is dropped,
  (b) lapses and (c) still holds. The proposed value is **2026-12-30T00:00Z**; `END_UTC = REGISTERED_UTC + 21 d` =
  2027-01-20T00:00Z; analysis date `END_UTC + 36 h` = 2027-01-21T12:00Z. **The family slides later if LT7 slides**; the rule
  uses no data; a move is recorded in the ledger.
- **The chain after LT6's closure (R1 must-fix 1).** LT6 closed on 2026-10-22 with V, D, B and K all dropped at census
  (`LIVE_TESTS_6.md` 6.3; ledger "LT6 closed"), so LT7's rule (b) (24 h after LT6's `END_UTC`) has no object and LT7's window
  now follows its own rules (a) (24 h after LT7's registration commit) and (c) (never before 2026-12-08). LT7 registers only
  after LT5's and LT6's registration commits or recorded drops; **LT5 also closed (2026-10-22 07:35Z, ledger "LT5 closed";
  F, H, R, J and O all dropped at census; re-check fix 4)**, so both conditions are met by recorded drops and the first draft's
  slide risk from LT5 J/O's registration is moot. The only remaining source of a slide is LT7's own rules (a) and (c): a late
  LT7 registration commit moves LT7's `END_UTC` and with it LT8's `REGISTERED_UTC` by rule (b) above. No LT5 or LT6 date
  enters any LT8 rule.
- **Why 24 h after LT7's end is enough (and what is shared).** LT7's last primary and F inputs are CH197's 22 h target and
  k + 13 sweep of its last 12:31Z origin (12-28T12:31Z), ending with the 12-29T14:31Z pass (about 14:40Z). LT8's earliest
  state input (CH203's k - 2 sweep of its first origin) is the 12-30T00:31Z pass, and every LT8 primary state input is a
  capture or sweep at or after `REGISTERED_UTC` (boundary rule below), so no LT8 state, control or target is an LT7 primary,
  F or control input. **Disclosed:** CH204's 84-slot look-back and every own 24 h change read raw captures of
  2026-12-23..12-29, which are LT7 origin and target inputs (as LT7's look-back read LT6's last week); CH204's reported
  out-of-window schedule reads 12-16..12-23; no LT7 store, origin, state or control is read.
- **Boundary (LT7 R1 must-fix 8's form):** CH202's first origin is the first capture whose k - 1 capture and pass k - 1 sweep
  start at or after `REGISTERED_UTC` (proposed 12-30T02:31Z); CH203's first origin is the first capture whose pass k - 2
  sweep starts at or after `REGISTERED_UTC` (proposed 12-30T04:31Z); earlier captures give no unit and are counted
  `lt7_boundary`. CH204's look-back is a look-back, not a state of the prior window; its first origin is 12-30T00:31Z.
- **Design-text freeze (round 13 rule 9; LT6 1.6's and LT7 1.1's protection).** After the challenger's acceptance (R1 and any
  re-check), a commit records the sha256 of this file in the ledger. From then on, the text of a test changes only by
  census-fixed values named in section 7 and by code-freeze-check fixes that change no state, unit, target, estimator, gate,
  threshold or verdict rule. **The freeze must exist before the earlier of 2026-11-15T12:00Z and `T_E015`** (planned by
  2026-11-10). `T_X` = the earlier of X's analysis job start (queue log) and X's analysis commit. Adjacent analyses and the
  consequence if the freeze (or a later text change) is not before them:

  | Test | Adjacent analysis (`T_X`) | Why adjacent | Consequence if the freeze or a text change is not before `T_X` |
  |---|---|---|---|
  | CH202 | E015 (`T_E015`, proposed 2026-11-15T12Z) | E015's anatomy (traded against quote-only) is a CH202 control; a held quote-only move is a re-centring that stayed | label *informed (E015)* |
  | CH202, CH203 | E022 (`T_E022`, proposed 2026-11-17T12Z) | E022 reads sweep depth and post-move hollowness on movers; CH202 shares its population; CH203 reads the same depth fields on non-movers | label *informed (E022)* |
  | CH202 | LT5 J (**dropped at census** 2026-10-22; LT5 closed; never registered, no analysis) | J's one-step against grind at the print clock is a timing-of-the-move question | none: dropped at census, no rule (re-check fix 4) |
  | CH203 | LT6 V (**closed**: dropped at census 2026-10-22, never registered, no analysis) | V's post-move 5c skew and `v_prev` pre-move skew are levels whose change CH203 tests on quiet books | none: no `T_V` exists; the first draft's drop rule is withdrawn (R1 must-fix 1); V's census counts were read and are disclosed (10) |
  | CH202, CH203, CH204 | **LT7** (`T_LT7`, proposed 2026-12-30T12Z) | CH195 reads the same k - 1 sweep on the same movers (CH202); CH197 the behind-touch level and CH195 the depth level (CH203); CH192 the |move| magnitude on the whole panel (CH204) | registration is before `T_LT7` by construction (at least 24 h before 12-30T00Z); if not, **every LT8 test is dropped** |
  | CH204 | E011 (`T_E011`, analysis after 2026-11-11) | E011 scores moves against the market's own volatility | label *informed (E011)* |
  | CH202 | E002, E004 (complete; Confirmed (exploratory, prospective)) | a reversal of about 21% of Gamma's 1 h change at about 5 h predicts that a fresh move continues less (CH202's sign) | label *informed (E002/E004)* always (3); the signed `chg_1h` is a primary control |

- **Why the window starts on 2026-12-30.** (1) CH203's book states and CH202's k - 1 sweep share LT7's reader shape and
  populations (CH195, CH197); an LT8 origin after LT7's last input shares no origin, state, control or target with LT7. (2)
  Host reader slots: LT7's reader stops about as LT8's starts (8.2). (3) LT8 can be frozen in November and pinned in December,
  before LT7's analysis.
- **Daylight-saving time (disclosed; R1 should-fix).** The census days (2026-10-12..10-21) were on US and UK summer time; the
  window is on winter time (the UK changes on 2026-10-25, the US on 2026-11-01). A US 08:30 ET release lands at 12:30Z, one
  minute before the 12:31Z capture, during the census, but at 13:30Z, mid-interval, in the window. CH204's census gates (the
  scheduled share, the distribution of `s*`, the venue-clock gate) are therefore **not representative of the window's slot
  positions**; CH202's held/fresh shares may shift for the same reason. The rule is not changed (it would be a change from
  data the census has not yet produced); the census prints the 12:31Z slot's share of `s*` separately.
- **Year end (disclosed).** The window spans New Year (2026-12-31..2027-01-02) and its first days follow Christmas; volumes may
  be lower than the October census days; CH204's first-week schedules are built from the Christmas week (12-23..12-29), when
  scheduled releases pause. A counts-only weekly line (`ops-stats`) is recorded, never a look. Sensitivities without origins in
  `[2026-12-31T00:00Z, 2027-01-03T00:00Z)` (all tests) and without CH204 origins before 2027-01-06T00:00Z (look-back free of
  12-24..12-26) are reported and never change a verdict.
- **Fixed end, no extension** (LT4-LT7 practice). Shortfalls are labelled (*underpowered*, Unavailable), never extended.
- **One analysis**, once, on or after the analysis date (`run_live_tests8.py analyze` refuses before it; `--out` refuses to
  overwrite). No interim look at any outcome (1.6). **Effective start** = max(`REGISTERED_UTC`, the first capture processed by
  the reader at the pinned commit); the analysis keeps only lines whose `spec_sha` and `code_sha` equal the pins and whose role
  is `prospective_confirmation`.

### 1.2 Streams read (all already written by the host's pass; nothing new is fetched; no new collector)
- **Complete-universe captures** `snapshots/<id>/rows.csv.gz` (every 2 h at :31; `state=complete` only): LT3-LT7's columns
  (`bid`, `ask`, `spread`, `last_trade_price`, `volume24hr`, `liquidity`, `chg_1h/1d/1w`, `end_date`, `event_id`, `neg_risk`,
  `closed`, `active`, `received_utc`), and the manifest's capture start time.
- **Sidecar** `rows_ext.csv.gz`: `fee_type`, `fee_category`, `series_slugs`, `order_price_min_tick_size`, `rewards_min_size`,
  `rewards_max_spread`, `clob_rewards`. A missing sidecar sets `sports = -1` and crypto unknown (excluded, counted).
- **Book sweep 1** `book_sweeps/<id>/` (`series_index` 0) of passes k - 2 and k - 1 (CH203 states), k - 1 (CH202 state), and,
  as targets or sizes-only F states, passes k + 1, k + 2, k + 3 (sweep-mid readings) and k + 5, k + 6 (CH203's lag
  innovation): outcome-0 `best_bid`, `best_ask`, `bid_size_1`, `ask_size_1`, `depth_*_1c`, `depth_*_5c`, `n_bid_levels`,
  `n_ask_levels`, `tick_size`, `book_timestamp`, `batch_receipt_utc`. **Field meaning (`book_sweep.parse_book`):**
  `depth_bid_5c` is the summed size (shares) of all bid levels with price >= best bid - 0.05, inclusive (touch included);
  `n_bid_levels` counts **every** bid level of the book, not the 5c band. One token per market. **Sweep 1, not `book0`'s
  sweep (6.1 item 2):** the engine's `book0` reads the newest complete pass sweep (on the host the pass's second sweep, about
  two minutes after sweep 1); the sealed census inputs hold sweep 1 only, so LT8 reads sweep 1 in census and analysis alike.
  Sweep 1 of a pass starts about 5-7 minutes after its :31 capture (LT7 1.2), so the pass k - 1 sweep is received about 113
  minutes before capture k.
- **Not read:** trade samples, the live large-trade monitor, `cross_venue_live/`, `surprise_live/`, the stores
  `live_tests2/` .. `live_tests7/`, CB8-H holders, the CB16-CB18, E025 and E026 stores, the keyless streams (PredictIt,
  Smarkets, ESPN odds, `gamma_rules`), `reward_params`, the signal engine's `quotes/`, `features/`, `aux/` (including `book0`)
  and `predictions/`, and Gamma outcome fields of any kind.

### 1.3 Clocks, slots and decision times
- **Slots:** as LT3-LT7 (`grid0 = 2026-10-01T00:31Z`, 2 h, tolerance 30 min, first complete capture of a slot). "k - j" and
  "k + h" are slots, not file order. A missing slot leaves every quantity that needs it NaN (counted), never interpolated.
  **Slot of day** `sigma(i) = i mod 12` of slot i (0 = 00:31Z, ..., 11 = 22:31Z); an interval `(i - 1, i]` carries the slot of
  its end capture i.
- **Decision time per test** (the latest input's own receipt; states use that input and strictly earlier ones only):
  - **CH203:** capture k's row `received_utc`. States read sweep 1 of passes k - 2 and k - 1 (each required to have
    `batch_receipt_utc` before capture k's start, else no unit, counted `sweep_after_origin`) and capture k. **The target
    starts at capture k + 1.**
  - **CH202:** capture k's row `received_utc`. The state reads capture k - 1, sweep 1 of pass k - 1 (same receipt rule) and
    capture k. **The target starts at capture k + 1.**
  - **CH204:** capture k's row `received_utc`; states from captures k - 84 .. k. **The target is the interval (k + 1, k + 2]**;
    the label refers to that interval's slot of day, a calendar fact known at k.
  - Gamma's own computation time of `chg_1h` is not published; it enters CH202 only as a control (its timing is not a state,
    6.1 item 7).
- **Late rule:** as LT4 1.3 (a frozen file is written before its earliest target slot can start, else `.late`, units lost and
  counted; *late-loss* above 2% of a test's origin files).

### 1.4 Shared origin-side eligibility
LT4 1.4 items 1-7, applied in order and counted (LT3's `move_join` and `classify`, vendored): binary, open and active at
k - 1 and k; two-sided and tight (spread <= 0.10) at both; `mid_k` in [0.02, 0.98] (narrowed per test); as-of end unknown or
> `t` + 7 h (all three tests' primary targets end by k + 3; CH203's lag sweep reaches k + 6 and needs end > `t` + 13 h, else
the unit is in the primary and out of the F arm, counted); category by `cb17_census.is_sports_sidecar` on the sidecar of k
(non-sports primaries; the sports arm reported, uncounted); one row per `condition_id`. **Crypto:** every primary excludes
crypto by the pinned classifier (`fee_category` contains `crypto` after strip and casefold; unknown counted and treated as
crypto); the crypto arm is reported, uncounted. Category is a spec parameter. **Series-family rule (census-fixed):** if the
census top series family holds > 40% of a test's primary population, it is excluded from that primary (`<test>.exclude_family`;
`""` = none) and the MDE gate recomputed. **Member cap (CH203, CH204; round 13 rule 3, declared now):** `n_members(e, k)` =
the number of distinct markets of Gamma event `e` among capture k's complete rows that are binary, open and active (an
origin-side count independent of every test's state; a market without `event_id` is its own event with 1 member); the primary
keeps units with `n_members <= 10`; units in larger events form the reported *ladder arm* (same model, uncounted). CH202 keeps
all event sizes (mover family; its `<= 10` arm reported). **Move units (CH202):** `x = mid_k - mid_{k-1}`, `|x| >= 0.01`,
LT3's class and geometry (traded, quote-only parallel, one-sided, spread-change, same-side-unequal, never-traded, ambiguous) =
**E015's anatomy label**, a control.

### 1.5 Missing data and per-capture status (never imputed)
As LT4 1.5 and LT7 1.5: every frozen unit receives exactly one status at every target slot (`two_sided`, `one_sided`,
`closed_flag`, `absent`, `capture_missing`; sweep targets `two_sided`, `one_sided`, `absent`, `capture_missing`), write-once
and online; only `two_sided` has a target; skip targets use the **joint late mask**. The attrition rule (|a_1 - a_0| > 2 pp
between the contrasted classes or the top and bottom terciles gives *attrition-differential* and Lee-type bounds) never
changes a verdict. A required input missing at the origin produces no unit and is counted (`sidecar_missing`, `.nosweep_km1`,
`.nosweep_km2`, `.noprev`, `lookback_missing`, `sweep_after_origin`). A missing control or state is NaN (excluded, counted),
never 0. **Declared indicator-pair exceptions only:** an unknown `end_date` enters log hours-to-end as 0 with `hte_unknown`;
a missing `chg_1h` (CH202) as 0 with `chg1h_missing`; **a missing `volume24hr` enters `log1p volume24hr` (and CH203's
`dV_prev`) as 0 with `vol_missing` (new for LT8, 6.1 item 10:** DESIGN_V1 16 reports the field present on about 22% of rows,
so excluding units without it would remove most of the whole panel; the missing-indicator method can bias, so every primary
is also re-estimated on units with the field present and reported, never a verdict). A falsification state that is missing
(CH203: sweep k + 5 or k + 6 absent, one-sided, or a 5c depth missing) leaves the unit in the primary and out of the F arm
(counted); it is never imputed.

### 1.6 What is not looked at before the analysis date
No mid, move, target, P&L, regression or plot from `live_tests8/` files, or from in-window captures or sweeps, for these
hypotheses. Only `run_live_tests8.py ops-stats` may run (file, line, role, class and status counts; reads no price column,
enforced by a unit test). No change of thresholds, scales, populations, estimators or k after registration; operational fixes
are logged as deviations. E015's, E022's and LT7's analyses (11-15 .. 12-30) arrive before LT8's window (LT5 and LT6 have no
analysis: both closed at census; re-check fix 4); they change nothing in LT8 after the design-text freeze, and the table of
1.1 decides their consequences. **No LT8 designer, coder or reviewer reads E015's, E022's or LT7's analysis outputs, or LT7's census
outputs beyond counts this file already cites, before the pin** (`SPEC_SHA256`). LT6's census outputs (counts only) **have
been read** in the R1 response (`LIVE_TESTS_6.md` 6.3; disclosed in 10); nothing in LT8 was changed because of them.
- **LT7's census comes before LT8's freeze (R1 must-fix 2; declared now).** LT7's censuses q0602-q0604 have not run at this
  response (no CC7/CS7 output in `seals/`); they count the same sealed files and neighbouring populations (CH195's movers with
  the k - 1 sweep, CH197's books, CH192's whole panel) and are expected before LT8's design-text freeze. Therefore: (i) the R1
  response applies **only** the items of `reviews/LT8_CHALLENGER_R1_2026-10-22.md` (section 13); (ii) after the LT7 census
  commit, **any change to an LT8 gate, filter, planning count or expected fate is labelled *informed (LT7 census)*** on the
  affected test, recorded in the ledger with the reason, and carried to the verdict; (iii) a re-check fix that a reviewer
  requires after that commit carries the same label unless the reviewer records that it is independent of LT7's counts; (iv)
  LT7's census outputs are not opened by an LT8 designer before LT8's freeze except to verify a hash. A read before the
  design-text freeze is treated as a freeze after that analysis (1.1's consequence column).

### 1.7 Estimators and inference
- **Expanding-past demeaning** for all three primaries (J4-R; LT2-LT7): every regressor (the tested term and every control)
  minus the mean of the market's strictly earlier units of the same test; target raw; the first unit of each market drops.
- **Standard errors and p (L10):** CR1 on event (Gamma `event_id`, else the market), two-way event x UTC day of the origin, and
  UTC day. One-sided **p = max(p_event on t with `G_event - 1` df, p_two-way normal, p_day on t with `G_day - 1` df)**.
  **Sparse class (CH202, CH204):** the event t uses `min(G_event, G_minor) - 1` df, `G_minor` = the number of events holding
  at least one unit of the smaller contrasted class (held or fresh for CH202; hot for CH204). The conservative 95% CI is the
  hull of a 2,000-draw event bootstrap and the three Wald intervals. Two-day blocks are a sensitivity (event x two-day block
  CR1) for every test.
- **Overlapping targets and shared shocks.** `c_skip` and `y_s` at consecutive origins overlap by one pass (MA(2) in pass
  steps). CH203's innovations at consecutive origins share one sweep (`imb5_{k-1}` enters `dimb5_k` and `dimb5_{k+1}` with
  opposite signs), so the state is MA(1) by construction. CH202's label at origin k + 2 is built from the interval (k + 1, k +
  2] and the sweep of pass k + 1, which are origin k's own target shocks (as LT7's CH191, R1 must-fix 6): a rolling state in
  LT7's sense. CH204's label is a deterministic function of the slot and of `s*`, which is built from the market's 84 previous
  |moves|, so `s*` is a rolling state and the target of origin k enters the look-back of origin k + 2 onward. All three
  therefore use the block gate (1.8) and the binding worlds of 1.8.1.
- **Both-demeaned sensitivity** (LT6): every primary re-estimated with the target also expanding-past demeaned; reported only.

### 1.8 Gates (valid within-unit nulls) and their size
- **Block (circular-shift) Freedman-Lane gate** (LT5's `block_fl_gate`, vendored unchanged) for **all three primaries**:
  after expanding-past demeaning, within each market the reduced-model residual series (ordered by origin) is circularly
  shifted by an offset drawn from `[s_m, n_m - s_m]`, `s_m = max(4, ceil(n_m / 4))`, and the full model refitted; 200 draws;
  passes if `p_perm < 0.05`; markets with fewer than 16 shiftable rows are excluded from the gate (counted). CH202 shifts the
  market's contrasted (held and fresh) units; CH204 the market's scheduled units. **Why the block gate everywhere:** CH203's
  state is the change of a persistent level (its level enters as a control and the AR(0.9)/AR(0.95) worlds bind); CH202's and
  CH204's labels are rolling (1.7). The plain gate and its strata (`perm_stratum`) are not used by any LT8 test.
- A failed gate on data gives p = 1 in Holm and the label "SE check failed (gate on data)".
- **Size check (L5), after the censuses (k and the census-fixed values fixed first).** `size-check` runs once, on the code to
  be pinned, 2,000 worlds x 200 draws, seed **20261187**, limit 0.058. Every gate scenario evaluates the gate through the same
  `block_fl_gate` path and minimum (16) as the analysis; worlds carry a UTC-day and a two-day-block column (LT4 19 fix 1); a
  world is generated once and evaluated under each binding test. Scenarios (no effect of the tested term in every gate world):

  | # | Scenario (1.8.1) | Gate | Binding for | Statistic |
  |---|---|---|---|---|
  | 1 | binary iid label | block FL | CH202 | gate rejection rate |
  | 2 | binary label, persistent market rates | block FL | CH202 | gate |
  | 3 | **leak world (R1 must-fix 7; re-check fix 1):** binary label correlated 0.7 with the true last-hour change `D60`, which has a real effect of **0.02 per SD** (the first draft's and LT7's world-3 scale); the model sees only a **noisy, lagged `chg_1h` proxy** | block FL | CH202 | gate |
  | 3r | as 3 with the E002-scaled effect `-0.14 x D60` | block FL | **none (reported; re-check fix 1)** | gate rejection rate, reported |
  | 4 | binary Markov label (persistence 0.6), MA(2) target, unbalanced markets | block FL | CH202 | gate |
  | 5 | **one-path stale-display world (CH202):** true martingale price, Gamma display refreshing at random, a sweep reading the true price 7 minutes into the interval, a real display bounce that reverts by k + 1 and a real reversal of the true last-hour change, which the model sees only through the **noisy, lagged last-trade `chg_1h` proxy** (R1 must-fix 7); labels and target from one path | block FL | CH202 | gate |
  | 6 | **CH203 level world:** imbalance level AR(1) rho 0.9 (innovation derived from it), control (the level) with a real effect, MA(2) target | block FL | CH203 | gate |
  | 7 | as 6 with rho 0.95 and longer series | block FL | CH203 | gate |
  | 8 | **CH203 depletion (leak) world:** a taker fill depletes one side without moving the touch; its volume enters the volume control **only where `volume24hr` is present** (missing with the share `p_vm` = max(the CS8 census `vol_missing` share of CH203's primary units, 0.78); R1 must-fix 8); the price follows the fill's sign | block FL | CH203 | gate |
  | 9 | **mechanical world M-Q (CH203):** a slow market drift that the imbalance innovation proxies equally before and after the target | none | CH203 | verdict size |
  | 10 | **CH204 one-path clustering world:** |moves| from one stochastic-volatility path per market, AR(1) log-volatility rho 0.9, a common venue clock (slot multipliers shared by all markets), no market-specific seasonality; `s*`, the scheduled rule and the target from the same path | block FL | CH204 | gate |
  | 11 | as 10 with rho 0.98 (multi-day clustering), t(3) shocks and longer series | block FL | CH204 | gate |
  | 12 | as 10 with a **market-specific slot pattern redrawn every 7 days** at an independent random slot (a schedule that lasts one week) | block FL | **none (reported; R1 must-fix 6)** | gate rejection rate, reported |

  **Verdict size** (scenario 9; round 13 rule 1 and LT7 1.8) = the share of worlds in which CH203's analytic one-sided p (the
  1.7 rule) is < 0.05 **and** its falsification condition F (1.9) holds; the gate is omitted, which can only raise the rate.
  Criterion: <= 0.058 at 2,000 worlds.
- **Also reported, never binding:** a planted-effect power run per test (500 worlds each, effect 0.5c per SD or between classes,
  seeds `20261187 x 100 + 31, 32, 33` for CH203, CH202, CH204), giving the power of gate, analytic p and F together; the
  far-future label rates of CH202 and CH204 in scenarios 4, 5, 10 and 12; **scenario 3r's gate rejection rate** (re-check fix
  1); **scenario 12's gate rejection rate** (decided
  reported now, before any size result exists, R1 must-fix 6: a real schedule that lasts one week satisfies the stated 7-day
  hypothesis, so world 12 is not a null; it is run in table order at its sub-seed and printed, never binding); the share of
  block-gate offsets that are multiples of 12 in CH204's gate on data and in worlds 10-12 (R1 should-fix: such offsets keep the
  slot alignment).
- **Leak worlds (3, 5, 8; R1 must-fix 7 and 8).** In these worlds the confounder's information reaches the model only through
  an imperfect control (a lagged, noisy `chg_1h` proxy; a volume control missing on most units), so the tested term carries a
  real but **mechanical** partial effect. They stay binding gate worlds: a rejection rate above 0.058 means the design cannot
  separate the hypothesis from the confounder at the declared control, and the test is "SE check failed (size scenario)". This
  is the intended consequence, declared now; their effect sizes and timings are the first draft's (3: 0.02 per SD; 5: 0.21 at
  two named passes; 8: the fill parameters), restored by the re-check (fixes 1-2), and are not tuned; only the proxy and the
  `vol_missing` share are new (R1 must-fix 7, 8). **Expected:** world 8 at `p_vm >= 0.78` is likely to fail (a planning calculation with no simulation run puts
  the leaked slope near 0.004 per unit of `dimb` against a standard error near 0.002 at the world's size); worlds 3 and 5 may
  fail.
- **Consequence of a failure (declared now, as LT5-LT7):** a failing scenario makes **only the tests it is binding for** "SE
  check failed (size scenario)" (1-8, 10-11) or "SE check failed (mechanical world)" (9): p = 1 in Holm, **k unchanged**, no
  rerun, reseed, redesign or variant. `max_retries 1` covers a deterministic crash only (same code, seed, worlds and draws, no
  output written). No preliminary run of any scenario at seed 20261187 is made.

### 1.8.1 Simulated worlds (declared now; no census input)
Common unless stated: a market's target level `N(0, 0.01)`; unit `i` of a market has `t_row = 7,200 i` s, `day = i // 12`,
`block2 = day // 2` from the same `block_anchor`; events of three markets; 200 draws per world at a fresh sub-seed from one
generator seeded 20261187, scenarios in table order; non-binding runs on generators derived as `20261187 x 100 + n`.
- **1, 2, 4:** LT7 scenarios 1, 2 and 4 exactly (LT4's `sim_move_world`, market rates `U(0.1, 0.6)`, LT5 scenario 4's Markov
  world), evaluated under the block FL gate, minimum 16.
- **The `chg_1h` proxy (worlds 3 and 5; R1 must-fix 7).** Gamma computes `chg_1h` on an unpublished clock and basis, so the
  binding worlds never give the model the true last-hour change `D60` (the true price change over the last 60 minutes before
  the capture). Per unit: a lag `L ~ U(0, 60)` minutes; trades arrive as a Poisson process with a market rate `lambda_m ~
  U(0.5, 6)` per hour; the last-trade price `p_lt(tau)` is the true price at the last trade at or before `tau` (the previous
  value if none); **`chg1h_obs = p_lt(t - L) - p_lt(t - L - 60 min)`** (exactly 0 when neither window end has a new trade, as
  Gamma's exact zeros); missing with probability 0.1 (then 0 with `chg1h_missing`, as 1.5). The real effect acts on the true
  `D60`, at each world's own scale and timing (3 and 5 below). The 0-60 minute lag and the trade rates are neutral conventions
  (the field's documented semantics are unknown; the rate range spans thin to active non-sports markets), recorded in the
  world's spec.
- **3 (leak, generic; R1 must-fix 7; re-check fix 1):** LT7 scenario 3's market layout (60 markets x 40 units,
  `sim_corr_label_world`) with the control re-specified: `D60_i ~ N(0, (0.012 sqrt(1/2))^2)`; label `1[z > 0]`, `z` correlated
  0.7 with `D60`; target `y_i = level - 0.02 x D60_i / sd(D60) + noise` (**the first draft's and LT7's effect of 0.02 per SD,
  kept**; noise SD 0.04 as LT7's world); the model's control is `chg1h_obs` built by the proxy rule above from a two-point
  path (the true price at `t - L - 60` and `t - L` drawn as a Brownian bridge consistent with `D60`, trades by the Poisson
  rule); no effect of the label beyond `D60`. Binding.
- **3r (reported only; re-check fix 1):** world 3 with the E002-scaled effect `y_i = level - 0.14 x D60_i + noise` (two thirds
  of E002's 0.21, the share inside a three-pass skip window; about 0.0012 per SD of `D60`); its gate rejection rate is printed
  and changes nothing. (The R1 response had put this weaker scale into binding world 3 without R1 asking; the re-check found
  that a loosening and it is withdrawn from the binding set.)
- **5 (one-path stale display, CH202):** 120 markets, `n_m` (passes) uniform on 120..252; log-volatility `s_t` AR(1) rho 0.95
  stationary SD 0.5; within each 2 h interval the true price `p` moves by two shocks, `u^a_t` over the first 7 minutes and
  `u^b_t` over the remaining 113, variances in the ratio 7 : 113 with total variance `(0.012 exp(s_t - 0.25))^2` (LT7 world
  15's scale); the sweep reads `p` at minute 7; the Gamma mid `m_t = p_t + b_t` with probability `pi_m` and `m_{t-1}`
  otherwise, `pi_m ~ U(0.4, 1.0)` (LT7 world 19's borrowed range), where `b_t = -0.3 u^b_t` is a display bounce that is
  absent at t + 1 (E004's bounce, removed by the skip target); the true path is simulated at 1-minute resolution inside each
  interval (the two shocks above split into minutes with variance proportional to time), and **the first draft's real reversal
  of 0.21 of the true last-hour change `D60` at the next two passes** (re-check fix 2) is applied to `p`, **named explicitly:
  passes t + 2 and t + 3**, i.e. `-0.105 x D60` added to the true price change of each of the intervals (t + 1, t + 2] and
  (t + 2, t + 3], so that all of it lies inside the skip target `m_{t+3} - m_{t+1}` (the reading of "the next two passes"
  under which the leak inside the target is not lowered, the re-check's reason for fix 2; the alternative reading, passes
  t + 1 and t + 2, would put only half inside the target); **the model's control is `sign(x) x chg1h_obs` built by the proxy
  rule above from the simulated 1-minute path and trades** (the first draft's exact true change is withdrawn, R1 must-fix 7);
  units are passes with `|m_t - m_{t-1}| >= 0.01`; labels `early_share`, held, fresh by section 3's rules; target
  `sign(x)(m_{t+3} - m_{t+1})`; controls `log |x|`, `sign(x) chg1h_obs` (+ missing flag), `log rv24*`. No effect of the label
  beyond the true `D60` reversal and the display bounce.
- **6-7 (CH203 level worlds):** 80 markets, `n_m` uniform on 24..252 (7: 120..252); `imb_t` AR(1) rho 0.9 (7: 0.95),
  stationary SD 0.3 around a market level `N(0, 0.2)`; state `dimb_t = imb_{t-1} - imb_{t-2}`; control `imb_{t-1}` with a
  real effect 0.01 per unit on the target; target `y_t = level + 0.01 imb_{t-1} + u_{t+1} + u_{t+2} + 0.5 u_{t+3}`, `u ~ N(0,
  0.02)`; no effect of `dimb`.
- **8 (depletion, CH203):** as 6, plus per pass a taker fill with probability 0.2 of size `|N(0, 1)|` on a random side, which
  lowers that side's depth (shifting `imb` by `-0.1 sign x size` for a bid-side fill) and raises a simulated volume change
  `dV` by `size`; the target receives `0.005 x signed fill` (of the fill in (t - 2, t - 1]); the model's controls are the
  volume-sign control `sign(fill) x log1p dV` and `dV_prev = log1p dV`, **observed only where volume is present: per unit,
  independently, `volume24hr` is missing with probability `p_vm` = max(the CS8 census `vol_missing` share among CH203's
  primary units, 0.78)** (R1 must-fix 8; 0.78 = DESIGN_V1's share of rows without the field), and a missing unit enters both
  controls as 0 with `vol_missing` = 1 (1.5's rule); no effect of `dimb` beyond the fill. The fill parameters (probability
  0.2, imbalance shift 0.1 per unit size, target effect 0.005) are the first draft's conventions, not measurements, and are
  **not changed** in the R1 response (changing them after learning that the world is likely to fail would be tuning).
- **9 (M-Q, CH203):** 80 markets, `n_m` uniform on 24..252; a market drift `mu_t` AR(1) rho 0.99 (in 2 h steps; a multi-day
  trend) stationary SD 0.004 per pass; lead state `dimb_t = 0.3 mu_{t-1} / sd(mu) + N(0, 1)`, lag state `dimb_lag_t = 0.3
  mu_{t+5} / sd(mu) + N(0, 1)` (both proxy the drift equally; the lag at the arm's own placement); target `y_t = mu_{t+1} +
  mu_{t+2} + u_{t+1} + u_{t+2} + 0.5 u_{t+3}`, `u ~ N(0, 0.02)`; model `y` on `dimb` with `imb_{t-1}` (an AR(0.9) nuisance
  level) as control; statistic: CH203's analytic one-sided p < 0.05 and F (Δ = beta(dimb) - beta(dimb_lag) in the arm model)
  holds.
- **10 (CH204 clustering, no seasonality):** 150 markets, `n_m` uniform on 120..336 passes; `s_t` AR(1) rho 0.9 stationary SD
  0.6; venue multipliers `v_sigma` for the 12 slots drawn once per world from `exp(N(0, 0.3^2))`, shared by all markets;
  `|Δ_t| = |0.012 v_{sigma(t)} exp(s_t - 0.36) e_t|`, `e ~ N(0, 1)`; for each pass the 84 previous `|Δ|`, `m_s`, `sc_conc`,
  `s*` and the scheduled rule of section 4 (with the >= 1c day rule replaced by >= 0.5 x the world's median |Δ|, so that the
  rule fires in simulated data; recorded in the world's spec); units are scheduled passes; target `|Δ_{t+2}|`; controls 11
  slot dummies of `sigma(t + 2)`, `log rv24*`, `log rv7d`; no market-specific seasonality.
- **11:** as 10 with rho 0.98, `e` from t(3) scaled to unit variance, `n_m` uniform on 168..336.
- **12 (non-persistent schedule):** as 10 plus, for each market and each consecutive block of 84 passes, a random slot `r`
  whose `|Δ|` is multiplied by 2.5 during that block only, the blocks' phase drawn per market; the target week's slot is
  independent of the look-back week's. **Status decided now (R1 must-fix 6): reported, never binding.** Where the look-back and
  target fall in the same block, `sc_hot` predicts by construction, and a schedule that lasts one week satisfies the stated
  7-day hypothesis, so world 12 is not a null; binding it could label a true effect "SE check failed". Its rejection rate is
  printed beside the binding results and changes nothing.

### 1.9 Verdicts, the falsification condition and labels (per primary, after Holm over k)
- **Falsification condition F (CH203; LT7's rule, unchanged).** The **arm model** is the primary model with `zdimb5_lag`
  added (the innovation between sweep 1 of passes k + 5 and k + 6, 2.F), fitted on the primary's units that have it, with the
  same demeaning, controls and clustering. `Δ = beta(zdimb5) - beta(zdimb5_lag)`, its SE from the arm model's clustered
  covariance. **F holds iff (i) Δ's one-sided p < 0.05 under the 1.7 p = max rule (not Holm-adjusted; counted 0) and (ii) Δ̂ >=
  0.5 x betâ_primary.** The lag state is built with the same census centre and scale as the lead. An arm with fewer than 50%
  of the primary's units is *falsification unavailable*.
- **Supported (exploratory, prospective):** Holm-adjusted one-sided p < 0.05, estimate in the predicted direction, gate
  passed, **and, for CH203, F holds.** If everything else holds for CH203 and F fails or is unavailable: **Inconclusive** with
  the label *mechanical null not excluded* (or *falsification unavailable*); Holm p is not changed.
- **Contradicted:** the conservative 95% CI lies entirely on the other side of 0. **Inconclusive:** otherwise.
  **Unavailable:** below the test's floor counts (fewer than 20,000 units, fewer than 300 events, or fewer than 10 UTC days
  with units; CH204 also fewer than 2,000 hot units; CH202 fewer than 2,000 units of either class).
- **Labels (never change a verdict):** *material* (CH203: the top-minus-bottom tercile contrast of `zdimb5` >= 0.5c on `y_s`;
  CH202 and CH204: the class contrast >= 0.5c); *regime, not timing* (CH202: the far-future split arm, section 3, fails the F
  rule); *rotation not excluded* (CH204: the rotated-schedule arm, section 4, fails the F rule); *not beyond yesterday*
  (CH204: Supported and the M2 reading with yesterday's same-slot |move| as a control below 50% of the primary or one-sided p
  >= 0.05); *capture-quote specific* (all three: Supported and the sweep-mid reading M1 below 50% of the primary or one-sided
  p >= 0.05); *touch innovation, not the band* (CH203's fake split); *flow, not silent* (CH203: Supported and the silent arm,
  units with no `volume24hr` rise over (k - 2, k - 1], below 50% of the primary or p >= 0.05); *informed (X)* (1.1; always
  *informed (E002/E004)* and *informed (b0_gap diagnostic)* for CH202, 3); *analytic p oversized in simulation*;
  *underpowered* (Inconclusive and `(t_{G-1, 1-0.05/k} + t_{G-1, 0.8}) x SE_day` above the census MDE); *attrition-
  differential*; *late-loss*; *sweep-missing* (`.nosweep_km1` or `.nosweep_km2` > 2% of origin passes); *series-concentrated*
  (one series family > 50% of a primary's units after the census rule); *ladder-dominated* (the ladder arm's estimate has the
  opposite sign); *holiday-sensitive* (a 1.1 holiday-excluded estimate changes sign).
- **MDE multiplier.** `3.47 = t_{20, 1 - 0.05/6} + t_{20, 0.8}` (exact 3.4725, LT7's constant). For k <= 3 the exact value
  is 3.145; **the multiplier is not lowered** (conservative; one constant across LT7 and LT8).

### 1.10 Economics (separate; never changes a verdict)
- Paper taker round trip per share at the recorded touches (sweep 1 of the entry pass and of the exit pass), fees on both legs
  from the origin sidecar (`economics.fee_spec`, `resolve_rate(..., "max_if_unknown")`), LT3's `paper_taker` and `econ`
  (event-clustered mean, one-sided p, >= 30 trades in >= 10 events). No depth, queue or latency: optimistic.
- **Hurdles (`cost-model-v1`, `COST_MODEL.md`, development calibration 2026-10-16..19):** $100 taker round trip about 2.9c at
  >= $100k Gamma liquidity, 3.9c at $10k-100k, 7.2c at $1k-10k; a 5-share touch round trip about 4.5c. A passive touch order
  fills about 3.1% of the time within an hour and loses about 2.38c to adverse selection against a 2 h mark (about 0.39c at >=
  $100k). Makers are about break-even before rewards (non-sports fill-weighted -0.37c).
- **Maker routes** (the primary money route for every test, "gross, no fills"): CH203 the favourable-tercile `y_s` per
  liquidity tier against 0.39c; CH202 the fresh class's M2 bounce (the move a re-posting maker recovers) and the held class's
  `c_skip` (the move a fading maker loses), per tier, against 0.39c and 2.38c; CH204 the gross |move| avoided by stepping
  aside at the hot slot (hot minus cold `a`) against 0.39c and 2.38c, plus the share of the week's |move| that falls in the
  hot slot (a maker's per-hour adverse-selection multiplier, reported).
- **Declared in advance:** every AREPO taker cost check has failed (E004, E007; 0 of 95 economic cells positive). "Not shown" is
  the expected outcome for every taker cell. No resolution, hold-to-resolution or reward income is computed (no outcome field
  is read).

### 1.11 Overlaps, dependence, embargo shadows and counting
- **Within LT8:** CH202's movers and CH203's quiet books are disjoint at the same capture (a CH202 unit has `|mid_k -
  mid_{k-1}| >= 0.01`; a CH203 unit has `|mid_k - smid_{k-1}| < 0.005` and `|smid_{k-1} - smid_{k-2}| < 0.005`, and may still
  have moved in Gamma's mid over (k - 1, k] only if Gamma's k - 1 mid was off the sweep: counted, the overlap printed); CH204's
  scheduled markets overlap both. All in one Holm family; never counted as independent confirmations. Pairwise unit-overlap
  shares and, on shared units, the within-market correlations of the tested terms are printed by the censuses and reported.
- **Against registered or drafted tests (no double count; no shared origin):**

  | LT8 | Closest prior | Same data? | Same contrast? | Why not a double count |
  |---|---|---|---|---|
  | CH203 | **LT7 CH197** (behind-touch imbalance level at 12:31Z; window to 12-29) | sweeps, the 5c depths | no: CH197's state is the level of the behind-touch split; CH203's is the change of the whole-band imbalance over two pre-origin sweeps, with the level a control | disjoint windows; registration before `T_LT7` or every test dropped (1.1); `book`, `book0`, `deepbook`, `quietbook` tokens |
  | CH203 | **LT6 V** (post-move 5c skew; `v_prev` pre-move skew) | sweeps | no: V's units are movers after the move; CH203's are quiet books before the origin | **V closed at census (2026-10-22; within corr(zv, z v_prev) 0.595 > 0.5), never registered**: nothing to double count; no drop rule (R1 must-fix 1) |
  | CH203 | **LT7 CH195** (pre-move hit-side depth), **E022** (post-move hollowness) | sweeps, depth fields | no: levels on movers | disjoint windows; *informed (E022)* rule |
  | CH203 | E020 (dropped at census; arrivals and cancellations at the touch of one-sided movers), E003 (complete; unconditional minute imbalance), ML-r4_book (development; pmxt book family `descriptive_only`) | books | no | nothing registered to double count; ML-r4_book disclosed (10) |
  | CH202 | **LT7 CH195** (same movers, same k - 1 sweep, its depth) and **CH191** (path shape over three steps) | captures, sweeps | no: CH195 reads the sweep's depth, CH202 its mid against the capture mids; CH191 reads the step path at the capture clock | disjoint windows; registration before `T_LT7`; `swclock` token |
  | CH202 | **CH194** (LT7; withdrawn before registration, uncounted) | captures | **the same question** (held against fresh) on another clock (Gamma's `chg_1h` there; host receipts here) | never registered; CH202 is its declared heir with the direct timing gate R1 asked for and with `sign(x) chg_1h` as a control, the redesign R1 named |
  | CH202 | **E002, E004** (complete; reversal of about 21% of Gamma's 1 h change at about 5 h) | captures | no, but **informing** (1.1) | completed; nothing pooled; *informed (E002/E004)*; the signed `chg_1h` control (a venue-computed proxy of unknown clock) and the binding leak worlds 3 and 5, which give the model only a noisy, lagged proxy (R1 must-fix 7), decide whether the channel is separated |
  | CH202 | **E015** (anatomy), **E022** (movers), **LT5 J** (jump or grind at the print clock; **dropped at census**, LT5 closed), E021 (age of the move; dropped at census) | captures; samples (J, E021) | no | disjoint windows; *informed (X)* rules for E015 and E022; J and E021 dropped at census, no rule (re-check fix 4) |
  | CH202 | the engine's `b0_gap` diagnostic (DESIGN_V1 22: correlation -0.04 to -0.16 with the 2 h label move) | `book0` sweep against the origin mid | **half of the state** (`late` is `b0_gap` up to sign and the sweep used) | disclosed; it is the M2 reading's content, not the primary's skip contrast; *informed (b0_gap diagnostic)* always |
  | CH204 | **LT7 CH192** (|move| over (k + 1, k + 2] on spread over realised volatility), **E011** (moves scaled by own volatility), CH57 (weather model runs; idea), the engine's `surprise` (UTC hour and weekday) and dropped `regime` family | captures | no: CH204's term is a per-market own slot, with the venue's slot pattern held fixed | disjoint windows; *informed (E011)*; registration before `T_LT7`; `sched` token |
  | all | E009/E010 (cross-venue), E025, E026 (frozen modules to 12-07) | no | no | different streams; nothing of E026 is imported |

- **Signal-engine shadows (disclosed; section 9).** CH203 can be learned by a book-isolating model that sees `book0` (pass k - 1)
  and `book` (pass k) together: their difference is the innovation over (k - 1, k], adjacent to CH203's (k - 2, k - 1]. CH202's
  late part is `b0_gap`, held by the **visible broad** `se18_lgbm_all_b0` and by the embargoed `se19_lr_book0`. CH204 can be
  learned by any model given per-market slot histories; the champion (`se1_lgbm_mm`) holds no slot-of-day input. LT8 asks
  for the embargo extensions and attribution limits of section 9.
- **Collection overlap (disclosed):** the signal engine and every earlier test read the same captures and sweeps; LT8's window
  overlaps no registered or drafted test's window. No store is opened by another test; no pooling.
- **Counting (M3):** the analysis adds **k counted tests**, one per surviving primary, kind `live_tests8`
  (`battery2.KIND_RULES["live_tests8"]`, fail-closed). Gate draws, F, secondaries, mechanism readings, arms, placebos,
  economics, censuses, the CH206 map and the size check count 0. The cumulative count is recorded at registration and at
  analysis.

### 1.12 Stop rules
As LT7 1.12: no interim look; the test runs to `END_UTC` whatever the counts; after 7 days, a test whose units run below one
third of its census projection (counts only) gets the ledger note "likely Unavailable" and nothing else changes; any change to
a pinned file after the pin makes the analysis refuse (a fix needs a new spec, new E-numbers and a new window); the reader exits
75 when nothing is new; a failed reader is re-promoted within 48 h; gaps stay missing and are counted; disk: the reader refuses
above 3.0 GB in `live_tests8/` and no retention rule may cover `live_tests8/` before the analysis is committed; collection of a
kind is switched off when its test is not in `k_tests`.

## 2. CH203: the quiet book (the imbalance innovation behind an unmoved touch)

- **Hypothesis and mechanism.** Informed traders whose information is long-lived prefer resting orders (Kaniel and Liu 2006;
  Rosu 2009); makers who fear one side withdraw levels from it. Both leave a trace in the book **while the touch stays put**:
  depth arriving on one side, levels leaving the other. The change of the 5c imbalance between two sweeps two hours apart,
  both before the origin, with the touch and the displayed mid unchanged, is that trace; its level is what every earlier book
  study read (V, CH195, CH197, E003). Order-flow imbalance moves prices at high frequency (Cont, Kukanov and Stoikov 2014); the
  claim here is its silent, pre-origin, two-hour form on the whole panel. **Direction: beta(zdimb5) > 0 on the YES mid,
  one-sided, the level `imb5_{k-1}` held fixed.** Who would be wrong: the trend reading (a slow market drift that a drifting
  book reflects before and after the target alike; F, M-Q), the farmer reading (mechanical re-posts by reward farmers that
  move depth with the band; reward controls), and the fill reading (a taker fill that ate one side without moving the touch;
  only partly controlled: the volume control exists on a minority of units, the silent arm is reported and the binding leak
  world 8 decides; R1 must-fix 8).
- **Unit and population.** Non-sports ex-crypto eligible market x capture k (1.4 at k - 1 and k), with sweep 1 of passes
  k - 2 and k - 1 for its outcome-0 token both present, two-sided, tight (sweep spread <= 0.10), both 5c depths positive at
  both, each received before capture k's start (1.3); **quiet:** `|smid_{k-1} - smid_{k-2}| < 0.005` and `|mid_k -
  smid_{k-1}| < 0.005` (the sweep mid did not move between the passes, and the origin's Gamma mid has not left it); `mid_k` in
  [0.07, 0.93] (the 5c band is not truncated by the boundary; LT7 CH195's band); `n_members <= 10` (1.4); end > `t` + 7 h.
  Boundary: first origin 12-30T04:31Z (1.1).
- **State (frozen; decision time = capture k's receipt).** `imb5_j = (B5_j - A5_j) / (B5_j + A5_j)`, `B5`, `A5` the
  outcome-0 `depth_bid_5c`, `depth_ask_5c` (shares) of sweep 1 of pass j; **`dimb5 = imb5_{k-1} - imb5_{k-2}`**; `zdimb5` with
  the census centre and scale (pooled, fixed in the spec). Also frozen (secondaries): `dimb1` (the same with `bid_size_1`,
  `ask_size_1`), `dlev = (nb_{k-1} - nb_{k-2}) - (na_{k-1} - na_{k-2})` with `nb`, `na` = `n_bid_levels`, `n_ask_levels`
  (whole-book level counts, 1.2), `dgrain_b`, `dgrain_a` (the change of `depth_*_5c / n_*_levels`, a coarse per-level size;
  the band's own level count is not stored), the notional form `dimb5_n` (depths times their touch prices), `lag_s = t_start(k)
  - receipt(sweep k - 1)`.
- **Target (exact).** **`y_s = mid_{k+3} - mid_{k+1}`** (YES capture mids; joint mask; 6.1 item 1). M1 (*capture-quote
  specific*): the sweep-mid `smid_{k+3} - smid_{k+1}`. M2 (reported; the round's target, which can carry a stale-mid catch-up
  at k): `c2 = mid_{k+1} - mid_k`. S1: 24 h `mid_{k+12} - mid_{k+1}`.
- **Primary statistic.** Expanding-past demeaned OLS of `y_s` on `zdimb5`, controls: `z imb5_{k-1}` (the level), `log1p
  (B5 + A5)_{k-1}`, `dlogD5 = log1p (B5 + A5)_{k-1} - log1p (B5 + A5)_{k-2}`, sweep spread at k - 1, `lag_s`, logit `mid_k`,
  `|mid_k - 0.5|`, `log1p volume24hr_k` (+ `vol_missing`), the signed prior volume `dV_prev = log1p(max(0, volume24hr_{k-1} -
  volume24hr_{k-2}))` (+ `vol_missing`), own 24 h change `mid_k - mid_{k-12}` (+ flag), `log rv24*_k` and `rv_floor` (LT7
  6.B's definition), 1[tick = 0.001], log hours-to-end (+ flag), `rewarded` (sidecar `clob_rewards` parsed by LT5 R's parser,
  **an empty field = unrewarded, 0**; unparseable excluded, counted), `in_band` (LT7 CH197's definition), `ft_both` (the farmer
  touch: rewarded and both `bid_size_1` and `ask_size_1` of sweep k - 1 <= 1.05 x `rewards_min_size`; CH209's flag, 0 when
  unrewarded), `rw_changed` (1 if the sidecar's `clob_rewards` string differs between captures k - 2 and k; the round's
  `reward_params` rate-change flag replaced, 6.1 item 4). Tested coefficient: `zdimb5`. Inference 1.7; seed **20261181**.
  Gate: block FL (scenarios 6-8), seed **20261281**.
- **Falsification (binding, F).** `dimb5_lag = imb5_{k+6} - imb5_{k+5}` (sweep 1 of passes k + 5 and k + 6, both 5c depths,
  **sizes only through the lag-slot loader**; no quiet condition, no price). Placement: the lead innovation ends about 3 h 53
  min before the target starts (sweep k - 1 to capture k + 1); the lag starts about the same span after the target ends
  (capture k + 3 to sweep k + 5 is about 4 h 7 min), the nearest sweep pair to the mirror image. Arm model = primary +
  `zdimb5_lag` (same centre and scale); Δ = beta(zdimb5) - beta(zdimb5_lag) (1.9). Scenario 9 (M-Q) is CH203's verdict-size
  statement. Disclosed: the lead is selected on a quiet touch and the lag is not; a large target move reshapes the later book
  toward the move's side, which raises beta(zdimb5_lag) when the building side wins, so F is conservative.
- **Mechanism readings.** M1 (*capture-quote specific*); M2 (the first interval, reported); M3 **the silent arm** (units with
  `volume24hr` present at k - 2 and k - 1 and `volume24hr_{k-1} - volume24hr_{k-2} <= max($10, 1e-4 x volume24hr_{k-2})`, the
  engine's movetype tolerance: a book change with no traded volume; label *flow, not silent*). **Corrected from the round
  (6.1 item 5):** a taker fill that eats one side without moving the touch changes `dimb5` with the **same** sign as the
  hypothesis (a sell fill thins the bid and predicts a fall), so it is a same-signed confounder, not a conservative one.
  **It is not addressed for most units (R1 must-fix 8):** Gamma omits `volume24hr` on about 78% of rows (DESIGN_V1 16), so
  `dV_prev` is effectively absent (0 with `vol_missing`) for most of the primary, and the silent arm M3 can only be formed on
  the minority with the field. The binding leak world 8 carries the census `vol_missing` share (or 0.78 if larger); if it
  fails, CH203 is "SE check failed (size scenario)", which is the honest outcome when silent book building cannot be told
  from fills that leave no volume trace. The census prints `vol_missing` against a missing `last_trade_price` (section 7).
- **Reported placebo (label).** The fake split: `zdimb1` in place of `zdimb5`; if its one-sided p < 0.05 and its tercile
  contrast is at least that of `zdimb5`, label *touch innovation, not the band*.
- **Secondaries.** S1 24 h; S2 `dlev` and `dgrain` in place of `dimb5`; S3 the notional form; S4 the ladder arm (events > 10
  members); S5 sports and crypto arms; S6 rewarded against unrewarded and `ft_both` splits; S7 the market's own expanding-past
  scale of `dimb5` in place of the census scale; S8 counts by tercile, tick and reward status.
- **Planning MDE (estimate).** About 21,000 quiet non-sports books with a pre-origin sweep a capture (round 13: 28,000 with
  `book0` x 0.75; the sweep-1 coverage is the census's count): 5.3M in 21 days; ex-crypto (planning 80%) 4.2M; mid band
  [0.07, 0.93] (planning 70%) 3.0M; `n_members <= 10` (planning 50%, **unprobed**) 1.5M; effective 80% = **1.2M**; planning
  range `n_eff` **1.0M (low) to 2.0M (high)**. SD of `y_s` 4.5c (quiet books' 2 h SD 3c x sqrt(2) = 4.2c, rounded up; LT7's
  movers' skip SD is 5c); `DE` **31** (the member cap; round rule 3); `VIF_w` 1.5; gap 2.2: `3.47 x 4.5c / sqrt(n_eff) x
  sqrt(31) x 1.5 x sqrt(1.5) x 2.2` = **0.35c at 1.0M, 0.25c at 2.0M**, 0.70c at a quarter of the low count; at DE 51 (the
  uncapped reading) 0.45c / 0.32c. **F's MDE** `MDE x sqrt(2 / (1 - max(0, r)))`: **0.50c at r = 0** and 0.56c at r = 0.2
  (low count); 0.35c / 0.39c (high count). F meets the 0.5c cap only if `n_eff` >= about 0.99M at r = 0, 1.24M at r = 0.2,
  1.41M at r = 0.3. For comparison, the round's 0.16c used the k-origin target (SD 3c), `n_eff` 3.4M and DE 51; the changes are
  in 6.1 items 1 and 9. **Expected: borderline on the F-MDE gate** (declared now); prior odds of surviving census 0.30, and
  about 0.10 of also passing the binding leak world 8 at `p_vm >= 0.78` (R1 must-fix 8).
- **Floors (Unavailable):** < 20,000 units, < 300 events, < 10 days.
- **Economics.** Maker (primary route): lean the quote toward the building side (post one tick higher on a side whose
  `dimb5` is in the top tercile) and step off the thinning side for one pass; gross `y_s` by tercile and liquidity tier, "gross,
  no fills", against 0.39c (>= $100k) and 2.38c. Taker (reported): buy the building side in the top tercile in >= $100k
  markets, entry at the sweep-1 touch of pass k + 1, exit at pass k + 3, against 2.9c; expected "not shown".
- **Reader it extends.** LT7's sweep reader for CH195 (outcome-0 sweep-1 join of pass k - 1 to capture k), with one more sweep
  (k - 2) kept in the reader's own `sweeps/` series and the sizes-only lag join at k + 5, k + 6.
- **Missing data.** `.nosweep_km1`, `.nosweep_km2`, `sweep_after_origin`, outcome-0 token absent, one-sided, a 5c depth
  missing or zero, not quiet: excluded, counted separately.

## 3. CH202: seven minutes or two hours (the sweep clock splits the move)

- **Hypothesis and mechanism.** A mid that the CLOB had already reached seven minutes after capture k - 1, and that the
  capture shows unchanged at k, has stood for about 113 minutes in front of every maker who could have faded it (a
  Glosten-Milgrom update accepted); a move that arrived late in the interval has not been tested and carries the re-centring
  bounce E004 measured. **Direction: E[c_skip | held] - E[c_skip | fresh] > 0, one-sided, the signed Gamma 1 h change held
  fixed.** A second reading predicts the same sign: the early part is partly Gamma's display catching up with a CLOB that had
  already moved (CH37's stale displayed mid in reverse), which is not news and has nothing to bounce. The test does not
  separate the two readings (the maker's rule is the same); scenario 5 asks whether a stale display, a martingale true price
  and the known reversal, seen by the model only through a **noisy, lagged `chg_1h` proxy** (R1 must-fix 7), give the gate
  a contrast; if they do, CH202 is "SE check failed" and "beyond the reversal" is not supported. **Informed, declared now:** (1) E002/E004
  (a reversal of about 21% of Gamma's 1 h change at about 5 h) predict that a fresh move, whose late part sits in the last
  hour, continues less: CH202 carries *informed (E002/E004)* and **`sign(x) x chg_1h_k` is a primary control**, so the tested
  contrast is the content beyond that reversal (the redesign R1 named for CH194); (2) `late` is, up to sign and the sweep
  used, the engine's `b0_gap`, whose correlation with the 2 h label move (-0.04 to -0.16, a reversal over k -> k + 1) was seen
  in DESIGN_V1 22's diagnostic: that is M2's content; the primary is the skip contrast, which nothing has read (*informed
  (b0_gap diagnostic)*).
- **Unit and population.** Non-sports ex-crypto 2 h mover at capture k (1.4 at k - 1 and k; `x = mid_k - mid_{k-1}`, `|x| >=
  0.01`; 6.1 item 7 keeps LT3/LT7's mover threshold and reports the round's `|x| >= 2` ticks as S2), with sweep 1 of pass
  k - 1 present for the outcome-0 token, two-sided, tight (sweep spread <= 0.10) and received before capture k's start;
  `mid_k` in [0.05, 0.95]; end > `t` + 7 h; all event sizes. Boundary: first origin 12-30T02:31Z (1.1).
- **State (frozen; decision time = capture k's receipt).** `smid_{k-1}` = the sweep mid of pass k - 1's sweep 1; `early =
  sign(x) x (smid_{k-1} - mid_{k-1})`, `late = sign(x) x (mid_k - smid_{k-1})` (so `early + late = |x|`), `early_share = early
  / |x|`, clipped to [-0.5, 1.5]. Classes: **held** = `early_share >= 0.75`; **fresh** = `early_share <= 0.25`; **mixed** =
  the rest (reported, not contrasted). Also frozen: `lag_s = t_start(k) - receipt(sweep k - 1)`, `lag_g = receipt(sweep k - 1)
  - received_utc` of the market's row at capture k - 1 (the row-to-sweep gap; the stale-row reading), anatomy of the move,
  `chg_1h_k`, the own 24 h change.
- **Target.** **`c_skip = sign(x) x (mid_{k+3} - mid_{k+1})`** (joint mask). M1 (*capture-quote specific*): the sweep skip
  `sign(x) x (smid_{k+3} - smid_{k+1})`. M2 (reported; the bounce and `b0_gap`'s object): `c1 = sign(x) x (mid_{k+1} - mid_k)`.
  S1 24 h `sign(x) x (mid_{k+12} - mid_{k+1})`.
- **Primary statistic.** Expanding-past demeaned OLS of `c_skip` on 1[held] over held and fresh units, controls: anatomy
  dummies (traded, parallel, one-sided, spread-change; same-side-unequal the base), `log |x|`, `sign(x) x chg_1h_k` (+
  `chg1h_missing`), spread at k, sweep spread at k - 1, `lag_s`, logit `mid_k`, `|mid_k - 0.5|`, `log1p volume24hr_k` (+
  `vol_missing`), own 24 h change `sign(x) x (mid_k - mid_{k-12})` (+ flag), `log rv24*_k` and `rv_floor`, 1[tick = 0.001],
  log hours-to-end (+ flag). Inference 1.7 with the `G_minor` df; seed **20261182**. **Gate: block FL** (scenarios 1-5), seed
  **20261282**.
- **Far-future arm (reported label, not a verdict condition).** The class of the move over (k + 4, k + 5] (one interval after
  the target ends, the mirror of the lead's one-interval gap before the target), by the same rules with sweep 1 of pass k + 4,
  where that interval is a mover (any sign); arm model = primary + 1[held'] + 1[fresh'] + 1[mixed'] (no mover' the base; +
  missing flag); if F's rule fails, label *regime, not timing*. **Why not binding:** the state is built from price changes and
  a sweep mid (LT7's CH191 ruling), and under the hypothesis a market whose moves are absorbed early is a persistent trait
  of its makers, which a time-symmetric arm would falsify; the mechanical threats are the bounce (skip target, M2), the stale
  display (scenario 5, M1), the known reversal (the `chg_1h` control, scenario 3) and ticks (S2).
- **Secondaries.** S1 24 h; S2 `|x| >= 2` ticks subset (the round's rule); S3 the continuous form (`c_skip` on `early` and
  `late` in cents over all movers, the slope difference); S4 traded and quote-only arms; S5 the `<= 10`-member arm; S6 sports
  and crypto arms; S7 units with `lag_g` <= 10 minutes (Gamma rows fresh at k - 1; the stale-row share printed); S8 counts by
  class, anatomy and tick.
- **Planning MDE (estimate).** Non-sports movers: LT7's planning range 18,500 a day (P1/P1b, all movers) to 33,000 (P1b's
  2,750 an interval x 12); ex-crypto, sweep-covered (0.93), in band: **13,000 a day (low; LT7 CH195's figure) to 23,000
  (high)**; 273,000 to 483,000 in 21 days; held 25%, fresh 55% (planning; round 13 from DESIGN_V1 21's "a third had moved by
  the sweep"); effective 80%. Low: `n_1` 54,600, `n_2` 120,100: `3.47 x 5c x sqrt(1/54,600 + 1/120,100) x sqrt(6.196) x 1.5
  x sqrt(1.3)` = **0.38c**; at a quarter **0.76c**; high **0.29c**. **At the count-gate floor (R1 must-fix 4; the first
  draft's 0.67c treated 201,600 as all movers, but the gate counts 201,600 held plus fresh units):** with held and fresh each
  15% of movers (100,800 each, 672,000 movers) the MDE is **0.33c on the raw counts** (the reviewer's figure) and **0.37c at
  the planning 80% effective share** (`n_1 = n_2` = 80,640), the form every other figure here uses; the least favourable split
  the gates still allow (no mixed units: 201,600 movers, held at its 15% minimum, 30,240, fresh 171,360; 80% effective) gives
  **0.52c**. The gate is unchanged: the census MDE gate is computed on the census's own class counts, whatever the split.
  `VIF_w` 1.3 is planning; the signed `chg_1h` control can raise it (the census computes it and the MDE carries
  `sqrt(VIF_w)`). **Expected: borderline at census** (declared now); prior odds of surviving census 0.25, and about 0.12 of
  also passing the binding leak worlds 3 and 5 (R1 must-fix 7).
- **Floors:** < 20,000 contrasted units, < 2,000 of either class, < 300 events, < 10 days.
- **Economics.** Maker: after a fresh move re-post toward the pre-move level for one pass (gross M2 for fresh units); after a
  held move quote at the new level (gross `c_skip` for held units), per tier, "gross, no fills", against 0.39c and 2.38c.
  Taker (reported): follow held moves with `|x| >= 0.03` in >= $100k markets, entry at the sweep-1 touch of pass k + 1, exit
  at pass k + 3, against 2.9c; expected "not shown".
- **Reader it extends.** LT7's CH195 join (capture k mover with the pass k - 1 sweep) and LT3/E015's `move_join` and
  `classify`; one sweep mid per mover.

## 4. CH204: the market's own clock (hot slot against cold slots)

- **Hypothesis and mechanism.** Scheduled information arrival concentrates moves and widens spreads around the schedule
  (Easley and O'Hara 1992; Chae 2005). On this venue a market's schedule (a data release, a model run, a court or vote
  calendar) is visible only to someone who watched that market for a week at a fixed cadence, which is what the pass does.
  A market whose |moves| over the last 7 days concentrate in one slot of the day has a schedule; at that slot its next move is
  larger than at its other slots, beyond the venue's own clock. **Direction: E[a | hot] - E[a | cold] > 0, one-sided, within
  scheduled markets, the venue's slot-of-day pattern held fixed.** Who would be wrong: the venue-clock reading (every market is
  busier at the same UTC hours; slot dummies, the venue-clock gate, scenario 10), the clustering reading (a burst in the last
  week picks a chance slot; the block gate, scenarios 10-11), and the chance-schedule reading (a slot that was hot for one
  week only; scenario 12, the out-of-window schedule).
- **Unit and population.** Non-sports ex-crypto eligible market x capture k (1.4 at k - 1 and k), with at least **70 of the
  84** two-hour changes `Δ_i = mid_i - mid_{i-1}`, i = k - 83 .. k, observed (both captures present and two-sided; else
  `lookback_missing`, counted), classed **scheduled** at k (below), `mid_k` in [0.05, 0.95], `n_members <= 10`, end > `t` +
  7 h. One unit per scheduled market per capture (all 12 slots of the day are units; one is hot).
- **State (frozen; decision time = capture k's receipt).** From the observed `|Δ_i|`, i = k - 83 .. k: `m_s` = the mean
  `|Δ_i|` over intervals with `sigma(i) = s` (s = 0..11; NaN if fewer than 5 of 7 observed, and then the market is not
  scheduled); `sc_conc = max_s m_s / sum_s m_s` (1/12 .. 1); `s* = argmax_s m_s` (ties: not scheduled, counted); the 7
  rolling days d = 1..7 (intervals k - 12d + 1 .. k - 12(d - 1); each holds every slot once); a day **counts** if its largest
  observed `|Δ_i|` is >= 0.01; the day's argmax slot (ties: no argmax that day). **Scheduled** = `sc_conc >= 0.35` **and** the
  day's argmax equals `s*` on >= 4 of the 7 days (a rule declared now, the round's, not fitted). **`sc_hot = 1[sigma(k + 2) =
  s*]`** (the target interval's end slot is the hot slot). Also frozen: `sc_rot = 1[sigma(k + 2) = (s* + 6) mod 12]`, `s*`,
  `sc_conc`, the hot slot's mean `|Δ|`, yesterday's same-slot `|Δ_{k-10}|` (the interval ending 24 h before the target's end),
  the out-of-window `s*_2` from days 8-14 (intervals k - 167 .. k - 84; reported only, NaN when unavailable, 8.1).
- **Target.** **`a = |mid_{k+2} - mid_{k+1}|`** (the interval (k + 1, k + 2]; 6.1 item 8). M1 (*capture-quote specific*): the
  sweep-mid `|smid_{k+2} - smid_{k+1}|`. S1: the spread at k + 2 minus the market's mean spread over the look-back (do makers
  widen into the hot slot; reported). S2: the signed `c_skip` of hot-slot moves against cold-slot moves (sign undeclared;
  reported). S3: `P(a >= 0.01)`.
- **Primary statistic.** Expanding-past demeaned OLS of `a` on `sc_hot` over scheduled units, controls: **11 slot-of-day
  dummies of `sigma(k + 2)`** (the venue clock, 6.1 item 8), `log rv24*_k` and `rv_floor`, `log rv7d*_k` (the 84 changes,
  half-tick floor), spread at k, logit `mid_k`, `|mid_k - 0.5|`, `log1p volume24hr_k` (+ `vol_missing`), log hours-to-end (+
  flag), the market's quote-only share of its look-back movers (E015's anatomy share over the week), 1[tick = 0.001]. Inference
  1.7 with the `G_minor` df; seed **20261183**. **Gate: block FL** (binding scenarios 10-11; 12 reported, R1 must-fix 6), seed **20261283**.
- **Falsification arms (reported labels, not verdict conditions).** (1) **Rotated schedule:** arm model = primary + `sc_rot`;
  if F's rule (Δ = beta(sc_hot) - beta(sc_rot)) fails, label *rotation not excluded*. With the slot dummies in the model, the
  rotation tests whether the specific slot matters beyond any fixed slot. `r_w` of `sc_hot` and `sc_rot` is -1/11 by
  construction. (2) **Not beyond yesterday (M2):** the primary with yesterday's same-slot `|Δ_{k-10}|` added (label *not
  beyond yesterday*). (3) **Out-of-window schedule:** the primary with `s*_2` in place of `s*` where defined (a schedule that
  persists predicts from the week before; reported). **Why not binding:** the state is built from price changes (LT7's CH191
  ruling); the mechanical threats (venue clock, clustering) are controlled and carried by the binding gate worlds 10-11, not
  by a time-symmetric arm; chance one-week schedules are world 12, reported (R1 must-fix 6).
- **Secondaries.** S1-S3 above; S4 per-category arms (sidecar `fee_category`) when one category holds > 50% of scheduled units;
  S5 the ladder arm (> 10 members); S6 sports and crypto arms; S7 counts by `s*`, `sc_conc` tercile and category; **S8 (R1
  should-fix) the category-clock arm:** the primary with the 11 slot dummies replaced by slot x `fee_category` dummies (a
  category's own clock held fixed; categories with < 1,000 scheduled units pooled as "other"), reported; **S9** the share of
  the block gate's drawn offsets that are multiples of 12 (offsets that keep the slot alignment), reported.
- **Planning MDE (estimate).** Markets with >= 70 of 84 changes: about 23,000 non-sports a capture (round 13: `sp_rv7d`
  coverage 78% of 30,000); scheduled **10-20%, unprobed**: 2,300-4,600 a capture; `n_members <= 10` and ex-crypto within that
  (planning 0.85, since crypto dailies were excluded from the round's share): hot units 2,000-3,900 a day, 41,000-82,000 in 21
  days, cold units eleven times as many; effective 80%. **Recomputed from this chain (R1 must-fix 3; the first draft used the
  round's `n_1` 38,600 / 77,300, which omit the 0.85 cap-and-crypto factor):** low: 1,955 hot units a day x 21 x 0.8 = `n_1`
  **32,844**, `n_2` = 11 x `n_1` = **361,284**; high: 3,900 x 21 x 0.8 = **65,520**, `n_2` **720,720**. SD of `a` 3c; DE **31**
  (the cap); `VIF_w` 1.3: `3.47 x 3c x sqrt(1/32,844 + 1/361,284) x sqrt(31) x 1.5 x sqrt(1.3)` = **0.57c** (low), **0.40c**
  (high); at DE 41 (8-member ladders without the cap's benefit) 0.66c / 0.47c; at a quarter of the units 1.14c / 0.81c. The
  0.5c gate needs `n_1` >= about 42,900 effective, i.e. **>= about 2,550 hot units a day** (about 3,000 scheduled markets a
  capture at the 0.85 factor). **Expected: more likely than not to drop at census** (the low end exceeds 0.5c; the scheduled
  share, events, venue-clock and category gates are unprobed; the census days were on summer time, 1.1; declared now); prior
  odds of surviving census **0.10** (first draft 0.15).
- **Floors:** < 20,000 units, < 2,000 hot units, < 300 events, < 10 days.
- **Economics.** Maker (primary route): in a scheduled market, pull or widen for the hot slot and re-post after it; gross `a`
  avoided (hot minus cold) per tier against 0.39c and 2.38c, and the hot slot's share of the week's |move|, "gross, no fills".
  Taker: none counted; a cost rule only (S1: the spread at the hot slot, reported).
- **Reader it extends.** LT7's CH192 reader (its 84-slot mid cache, `midcache/`, built from the reader's own `series/`), with
  per-market slot sums kept in the cache's row; no engine `quotes/` read (6.1 item 8).

## 5. Deferred: CH205 (steam at the book) and CH206 (the reward start)

### 5.1 CH205: deferred for the owner's sports-scope decision (not proposed; never counted)
CH205 is sports-only by construction (ESPN's moneyline move against Polymarket's pre-game price). Category scope is an open
owner decision (sports inclusion undecided); AREPO's designs stay category-agnostic with category as a parameter. CH205 also
needs a 42-day window to reach its own MDE (0.57c / 0.40c at 42 days against 0.81c / 0.57c at 21; round 13 section 2.C), a
matcher that is a map first (coverage and precision unprobed), and a stream (`stream_espn_odds/`) no LT has read. It is
therefore **not in this Holm family** and cannot join it later (k is fixed by LT8's censuses alone). If the owner sets sports
in scope, CH205 would be drafted as its own family (a separate design file, its own censuses on the ESPN day files and a
matcher audit, its own window of 42 days) with `steam` as its token; no `steam` embargo is requested now (nothing is drafted).
Recorded as "not proposed (scope)".

### 5.2 CH206: a map first (counts only; uncounted; not a test)
CH206's population is the whole question: no count of future reward configurations exists (`reward_params_collector.py`
counts native and sponsored programmes per capture, 13,661 rewarded markets on 10-20, but not future starts). Proposed: one
counts-only **map job** (queue draft q0627, section 7) over the `reward_params` captures since 2026-10-20T23:20Z, which reads
configuration ids, market ids, `start_date`, `end_date`, rates, sponsor counts and receipt times, and **no price, spread, depth
or Gamma field**: future configurations per capture; starts a day on markets older than 24 h at the start (market age from
the sidecar's `created_at` on the nearest earlier complete capture; a market not in the sidecar is counted as unknown age);
the share of starts on the most common UTC day; the rate and band distribution of new programmes; the number of distinct
events among the started markets. The round's kill lines (>= 30 starts a day on existing markets; controls for >= 70%; the
one-day share <= 30%) decide whether a later family drafts CH206; the map is not a census of a registered design, changes
nothing in LT8, and counts 0. A spread target is not read by the map. The `rwstart` token is not requested now.

## 6. Design changes, ideas not taken, census drops

### 6.1 Design changes to the round-13 sketches (made before any data; each needs the challenger's acceptance)

1. **CH203's target starts at k + 1.** The round's `c2 = mid_{k+1} - mid_k` starts at the origin quote. A Gamma mid that is
   stale at k (the CLOB moved after sweep k - 1 and the display has not followed) carries a catch-up in (k, k + 1] whose sign
   the pre-origin book may predict; that is a forecast of an already-public CLOB move, not of the next one (LT5 R1 finding 2;
   LT7 R1 must-fix 2's reasoning for CH193). LT8 uses **`y_s = mid_{k+3} - mid_{k+1}`** (the skip interval of `c_skip`, YES
   signed); the round's `c2` is M2, reported. Cost: SD 4.5c instead of 3c, so the planning MDE rises by 1.5x (disclosed in 2).
2. **Sweep 1, not `book0`'s sweep.** The round's states use `book0`'s construction (the newest complete pass sweep, on the
   host the pass's second sweep). The committed census inputs hold sweep 1 only (`lt7_census_inputs.json`: 47 sweep
   directories, one per pass), and the census must count the object the analysis reads; LT8 reads sweep 1 (`series_index` 0)
   of passes k - 2 and k - 1, received before capture k's start. `book0`'s coverage figure (92-94%) is therefore not LT8's;
   the census counts sweep-1 coverage.
3. **CH203 in shares with a census scale; a residual-IQR gate.** The round's notional depths and "standardised within the
   expanding past of the market" are replaced by shares (V's and CH197's convention; the quiet filter keeps the touch price
   nearly fixed, so notional and share forms differ little; the notional form is S3) and one census centre and scale (so the
   lag state shares the lead's scale and F's Δ is in the primary's units; the market-own scale is S7). The round's "within-
   market SD >= 0.05" gate is replaced by LT7's residual-IQR form (the state's within-market IQR after its level), the
   programme's rule for continuous states.
4. **CH203's reward controls from the sidecar only.** The round's `reward_params` rate-change flag would read a stream that no
   census input seals; it is replaced by `rw_changed` (the sidecar's `clob_rewards` string differs between captures k - 2 and
   k). CH209's farmer touch is used as the control `ft_both`, defined from sweep k - 1 and the sidecar's `rewards_min_size`.
   An empty `clob_rewards` is unrewarded (LT5 R's parse artefact, 1.0).
5. **CH203's fill confounder sign corrected.** The round called taker-fill depletion "the opposite sign of the building story
   and therefore conservative"; it is **same-signed** (a sell fill thins the bid; a buy fill thins the ask; both predict the
   fill's direction). LT8 adds `dV_prev` as a control, the silent arm M3 with its label and the binding depletion world 8;
   R1 must-fix 8: with `volume24hr` absent on about 78% of rows these only partly control it, and world 8 carries the
   census `vol_missing` share (at least 0.78).
6. **CH203's gate is the block gate**, not the round's market x day plain gate: the tested term is the change of a persistent
   level and adjacent innovations share a sweep (1.7). The round's `r_w <= 0.3` kill line is kept and applied to
   `r_gate = max(r_w, r_pool)` (LT7 re-check M2), stricter than LT7's 0.8 cap.
7. **CH202:** (a) the mover threshold is LT3/LT7's `|x| >= 0.01`, not the round's `>= 1c and >= 2 ticks` (at the 0.01 tick
   most books have, two ticks is 2c, which would halve the population; the share is defined at the mid's half-tick resolution,
   so a 1c move still splits into held, mixed and fresh); the round's rule is S2. (b) **`sign(x) x chg_1h_k` is a primary
   control** and *informed (E002/E004)* is declared: the known reversal predicts the contrast's sign (LT7 R1 must-fix 4 on
   CH194), so the test is of content beyond it; `chg_1h`'s timing is not a state (R1 must-fix 5 on CH194). (c) **Block gate**
   and the one-path stale-display world 5, not the round's plain gate: the label at origin k + 2 is built from origin k's
   target shocks (LT7 R1 must-fix 6 on CH191). (d) The count gate is LT7 CH191's 800 a capture, not the round's 1,500 kill
   line (the MDE gate is the binding feasibility criterion and carries the count; at 1,500 the low planning count would fail a
   count gate while passing the MDE gate). (e) A row-to-sweep gap `lag_g` is frozen and its <= 10-minute subset reported (the
   round's stale-row print, made a reading).
8. **CH204:** (a) **the target interval is (k + 1, k + 2] and the label refers to its slot** (the round's `|mid_{k+1} -
   mid_k|` with `1[slot(k) = s*]` mixed the origin's slot with the next interval's); the schedule is known days ahead, so
   nothing is lost and every primary target starts at k + 1 (LT5/LT7 convention). (b) **H0: δ <= 0** with a *material* label at
   0.5c, not the round's shifted null δ <= 0.5c (the family's convention; the MDE gate carries the floor). (c) **11
   slot-of-day dummies** are controls (the venue clock held fixed; round rule 8 forbids it as a state, not as a control). (d)
   The rotated schedule is a **reported label** (the state is built from price changes, LT7's CH191 ruling), not the round's
   census-conditional verdict switch, which would make the verdict rule depend on a census count. (e) The look-back comes from
   LT8's own mid cache of raw captures, not the engine's `quotes/` (no engine store is an LT input, LT7 1.2). (f) Days are
   rolling 12-interval blocks ending at k; a day counts only if its largest |move| is >= 1c; ties are not scheduled.
9. **Member cap <= 10 for CH203 and CH204**, declared now with its counting rule (1.4); CH202 keeps all event sizes (mover
   family, E022's DE). The planning MDE of CH203 includes the cap's loss of units (planning 50%). **Corrected (R1 must-fix 3):**
   the first draft's claim that CH204's MDE included its 0.85 cap-and-crypto factor was false (it used the round's `n_1`);
   section 4 now carries the factor (`n_1` 32,844 / 65,520; MDE 0.57c / 0.40c).
10. **`volume24hr` missing as an indicator pair** (1.5), a declared exception LT7 did not make: DESIGN_V1 16 reports the field
    on about 22% of rows, and dropping units without it would remove most of CH203's and CH204's whole-panel populations; the
    present-only re-estimate is reported.
11. **Multiplier 3.47** (LT7's k = 6 constant) kept for k <= 3 (exact 3.145), conservative; **no 28- or 42-day extension**;
    **design-text freeze before the earlier of 2026-11-15T12:00Z and `T_E015`**, earlier than the round's 2026-12-07T12:00Z.

### 6.2 Ideas not taken into LT8
- **CH205** (steam at the book): deferred for the owner's sports decision; needs 42 days and a matcher map (5.1).
- **CH206** (the reward start): a counts-only map first (5.2, q0627).
- **Engine-first, not taken (round 13 section 2.D; tokens as the round states them, none requested here):** CH207
  (`umaparams`, desk-set dispute insurance; the `gamma_rules` frame covers 44.7% of eligible non-sports, trait states, targets on
  `res_7d`); CH208 (`xvenue2` timing extension; tens of events, rule 7); CH209 (`farmer`; a slow trait, used here only as
  CH203's control `ft_both`, which reads the same fields); CH210 (`sweep2_0`, two minutes of pass k - 1 book news; weak by
  construction); CH211 (`requote`, the ladder that travelled; an E015 moderator until 11-15 and a `movetype` shadow to 12-31).
- Round 13 section 4's rejections stand (trade-sample units, sweep states inside their label window, level states with a
  far-future F, `chg_1h` timing states, rule edits, `gamma_rules` whole-panel fields, cross-venue gaps, in-play ESPN, unsigned
  liquidity withdrawal, the late crowd, venue clocks, wallets, maker mark-outs, moderators of E015/E022/LT5/LT6/LT7 inside
  their windows, resolution-level primaries, taker primaries, the `b0_gap` reversal as a test).

### 6.3 Census drops
None yet. Census drops will be recorded here, with their counts, before the pin.

## 7. Pre-registration censuses (counts only; before registration; worn pre-window data; no target read)

Each census runs once, reads origin-side fields only (no target, no P&L; the only later-slot quantities read are CH203's lag
sweeps' two 5c depths for the F-feasibility correlation, never paired into a target, through the lag-slot loader), prints
counts, and is committed with its sha256 before the registration commit. **Lag-slot loader (LT7 R1):** a census reading a sweep
later than a unit's origin receives only the keys and `depth_bid_5c`, `depth_ask_5c`; no bid, ask, mid, size at the touch, last
trade or other price column of a later slot reaches census code (unit test, 8.3). CH204's census reads `sigma(k + 2)` (a
calendar fact) and nothing of capture k + 1 or k + 2. **Every gate threshold below is stated now, before any census.** A failed
gate drops that test before registration (uncounted); `k_tests` lists the survivors. **Input identity:** the census refuses
unless every input file it opens is named in the LT8 seal with an equal sha256, and refuses if a sealed file in a needed slot
is absent.

**Inputs (all started before 2026-10-22T00:00Z; files already sealed by LT7, whose sources are LT5's capture seal and the LT3
and LT4 seals).**
- **Source seal:** `seals/lt7_census_inputs.json`, **sha256 `117e9b458931b7493f6b34e36ce68e7e4898c544fb5aa360956ea106de204137`**
  (written 2026-10-22T05:48Z, design text 840f4500…, 499 files), whose own sources are `lt5_census_inputs_captures.json`
  (`fcd88926147051cba07d2094393d350faa7244828131e52bc9ee9b15bd108752`), `lt4_census_inputs_captures.json` (`6030d261…`) and
  `lt3_census_inputs_C2.json` (`2dec7e33…`). LT8 uses its **112 sealed captures** (rows, sidecar, manifest; slots
  2026-10-12T00:31Z .. 10-21T22:31Z; the 8 missing slots 10-14T00:31..10:31Z, 10-21T00:31Z and 02:31Z left missing) and its
  **47 sealed sweep-1 passes** (block A 10-14T22:37Z .. 10-16T22:37Z, 24 passes, the 10-15T22:31Z pass absent; block B
  10-19T22:36Z .. 10-21T22:38Z, 23 passes, 10-21T00:31Z and 02:31Z absent). Its 69 trade-sample files are not used.
- **CS8 (sweeps and captures: CH203, CH202).** Origins, derived from the seal's file list (no row read; the census's own slot
  assignment decides): **CH203 41** (sweeps k - 2 and k - 1 and captures k - 1 and k sealed; covered days 3.42), of which **23**
  also have the lag sweeps k + 5 and k + 6 sealed (the F-feasibility pairs); **CH202 45** (sweep k - 1 and captures k - 1, k;
  3.75 days).
- **CC8 (captures: CH204).** Origins with >= 70 of 84 changes observable from the sealed captures: **40** (10-18T10:31Z ..
  10-21T22:31Z; 3.33 days). No sweep is read.
- **Fallback (LT6 R1 item 9's rule):** fewer sealed slots restored: use exactly those (the rest genuinely missing, counted); no
  other day is substituted; slots outside the named spans are never read. **Minimum covered days** (covered origins / 12): CS8
  >= 2.5 for each test and >= 1.5 for the F pairs; CC8 >= 2.5; **and (R1 should-fix, Q14) at least 1.0 covered day (>= 12
  origins) of each CS8 test in each sweep block**, A (10-14T22..10-16T22, Thursday to Saturday) and B (10-19T22..10-21T22,
  Tuesday to Wednesday): from the seal's file list CH203 has 22 origins in A and 19 in B, CH202 24 and 21. Below any minimum,
  every gate of that test's census is NaN and fails. **The F pairs are not put under the per-block rule:** they split 13 / 10
  (1.08 / 0.83 days) by the same file list, so a per-block 1.0-day rule on pairs would drop CH203 by construction before any
  count; their pooled minimum (1.5 days; 23 pairs, 1.92 days) stays, the per-block split is printed, and the choice is put to
  the re-check (13).
- **Restore, seal, census: each once.** q0620 first accepts **host copies** of the needed files that pass the sha256 check
  against the LT7 seal (R1 should-fix), then restores the rest byte for byte from the data releases and checks every sha256
  against the LT7 seal (refuse on any mismatch); the needed set is **430 files** (112 captures x 3, 47 sweeps x 2); **whether the
  releases hold all 430 is not confirmed** (R1 "not verified"): a file found in neither place is genuinely missing and the
  fallback above applies (counted, never substituted). It measures bytes before writing and **stops and asks the owner** if the
  restore would exceed the host's free disk (CLAUDE.md storage stop rule). q0621 writes `seals/lt8_census_inputs.json`, listing
  exactly the restored or accepted files with equal hashes, the source seal's sha256, **LT7's 159-entry `slots` map reproduced
  exactly** (a mismatch refuses; R1 should-fix) and the **frozen LT8 design-text sha256** (so the seal is written only after
  the design-text freeze); the orchestrator commits it **before any LT8 census runs**. No restore, seal or census is re-run; a
  deterministic crash is the only retry (`max_retries 1`, no output written).
- **Header pre-check** (before the census code is frozen; a header read, no rows): the sealed sweeps carry `depth_bid_5c`,
  `depth_ask_5c`, `bid_size_1`, `ask_size_1`, `best_bid`, `best_ask`, `tick_size`, `n_bid_levels`, `n_ask_levels`,
  `batch_receipt_utc`; the rows carry `received_utc`, `chg_1h`, `volume24hr`, `event_id`; the sidecars carry
  `rewards_min_size`, `rewards_max_spread`, `clob_rewards`, `fee_category`, `order_price_min_tick_size`; the manifests carry the
  capture start time. A missing field makes the dependent gate NaN (that test drops); a missing level count only removes
  CH203's S2.

**Projection** = census count x 21 / covered days (an estimate). **Distinct events:** distinct events over the covered days x
21 / covered days (a pessimistic projection: recurrence is not extrapolated) and, printed, `E_all + (E_all - E_day1) x (21 -
covered_days)` (LT7's two-day form generalised). **Effective counts** = units in markets with >= 2 units of the test's
population in the census days. **Design effect:** `DE_gate = max(floor, 1 + (m_21 - 1) x 0.02)`, `m_21` the projected
size-weighted mean cluster size by event; floors **3.0 (CH202)**, **5.0 (CH203, CH204; whole panel)**. **MDE gate formulas
(multiplier 3.47):** class (CH202, CH204) `3.47 x SD x sqrt(1/n1_eff + 1/n2_eff) x sqrt(DE_gate) x 1.5 x sqrt(max(1,
VIF_w))`; slope at the census tercile gap (CH203) `3.47 x SD / sqrt(n_eff) x sqrt(DE_gate) x 1.5 x sqrt(max(1, VIF_w)) x gap`;
each with **`max(declared, design)`**. **Definitions (R1 should-fix):** *declared* = the closed formula above evaluated with
the census's own `n_eff` (or `n1_eff`, `n2_eff`), `DE_gate`, `VIF_w` and tercile gap and the declared target SD; *design* =
`3.47 x 1.5 x SD x se_1` (x the tercile gap for a slope), where `se_1` is the standard error of the tested coefficient in the
primary model fitted on the census units' actual expanding-past-demeaned regressors (controls included), computed from the
regressors alone under a working covariance with unit variance, within-event equicorrelation 0.02 (the `DE_gate` formula's
intraclass value) and independence across events; no target is read. For F, the same with Δ in the arm model. The gate takes
the larger of the two. `VIF_w` = within-market (expanding-past demeaned) VIF of the tested term on the
primary's controls; a NaN fails. **CH203 F-feasibility:** `r_w` = the within-market correlation of `dimb5` and `dimb5_lag` on
census units that have both, each expanding-past demeaned over the market's such units (the first drops), markets with >= 3
such units; `r_pool` the pooled correlation on the same units; **`r_gate = max(r_w, r_pool)`**; **F-MDE** = `max(design-based
MDE of Δ in the arm model, slope MDE x sqrt(2 / (1 - max(0, r_gate))))`. SDs: `y_s` 4.5c, `c_skip` 5c, `a` 3c. Correlations
marked "within" are on expanding-past-demeaned values and bind; pooled values are printed.

| Test | Census | Gate (all must hold; NaN fails) | Values fixed into the spec |
|---|---|---|---|
| CH203 | CS8 | sweep-1 coverage (passes k - 2 and k - 1 two-sided on outcome 0, both 5c depths positive, both received before capture k's start) >= 70% of non-sports ex-crypto eligible markets in band; share received before the origin >= 95% of covered; **quiet share** >= 50% of covered; projected quiet covered units (before the band and the cap) >= 2,520,000 (>= 10,000 a capture; the round's kill line); projected primary units (all section 2 filters, the cap included) >= 504,000 (>= 2,000 a capture); **cap share:** units in events with `n_members <= 10` >= 40% of quiet covered units in band; **residual IQR:** within-market IQR of the residual of `dimb5` after an OLS on `imb5_{k-1}` >= 0.05 in >= 50% of markets with >= 6 units, and >= 30 such markets; `VIF_w(zdimb5)` <= 2.0; within `|corr(zdimb5, z own 24 h change)|`, `|corr(zdimb5, dlogD5)|`, `|corr(zdimb5, ft_both)|`, `|corr(zdimb5, z dV_prev)|` each <= 0.5; `|corr(zdimb5, log1p liquidity_k)|` <= 0.5 within and pooled; block-gate share >= 50% of units in markets with >= `ceil(16 x covered_days / 21)` units in the census days (3 for 3.42 days); `r_gate` <= 0.3 (on >= 1.5 covered days of pairs, >= 30 markets with >= 3 pairs); **slope MDE <= 0.5c** (`DE_gate` floor 5.0); **F-MDE <= 0.5c** | `zdimb5` (and lag) centre and scale; `z imb5` centre and scale; `zdimb5` tercile cuts and gap; `exclude_family` |
| CH202 | CS8 | sweep k - 1 coverage (two-sided outcome-0, tight, received before capture k's start) >= 70% of non-sports ex-crypto movers in band; projected contrasted units (held + fresh, all section 3 filters) >= 201,600 (>= 800 a capture); held >= 15% and fresh >= 15% of movers; within `|corr(1[held], 1[parallel])|`, `|corr(1[held], 1[traded])|`, `|corr(1[held], z log |x|)|`, `|corr(1[held], z signed own 24 h change)|` each <= 0.5; within `|corr(1[held], z sign(x) chg_1h)|` <= 0.8 (the reversal channel is a control; its collinearity enters through `VIF_w`); `chg_1h` present (not missing) on >= 50% of movers; `|corr(1[held], log1p liquidity_k)|` <= 0.5 within and pooled; **block-gate share** >= 50% of contrasted units in markets with >= `ceil(16 x covered_days / 21)` contrasted units in the census days (3 for 3.75 days); **class MDE <= 0.5c** (`DE_gate` floor 3.0) | `exclude_family` |
| CH204 | CC8 | >= 70-of-84 coverage >= 60% of non-sports ex-crypto eligible markets in band; **scheduled markets** >= 1,200 a capture (the round's kill line; mean over census origins); projected hot units >= 25,200 (>= 1,200 a day); projected distinct events of scheduled markets >= 500; cap share >= 40% of scheduled units in events with `n_members <= 10`; **venue-clock gate:** the most common `s*` holds <= 50% of scheduled markets (rule 8: otherwise it is a venue clock and the test is dead); **category gate:** the most common sidecar `fee_category` (strip, casefold; empty = "unknown") holds <= 70% of scheduled units (> 50% triggers the per-category arms, S4, no gate); within `|corr(sc_hot, z log rv24*)|` <= 0.5; `|corr(sc_hot, log1p liquidity_k)|` <= 0.5 within and pooled; block-gate share >= 50% of units in markets with >= `ceil(16 x covered_days / 21)` scheduled units in the census days (3 for 3.33 days); **class MDE <= 0.5c** (`DE_gate` floor 5.0) | `exclude_family` |

- **Descriptive (no gate):** every census prints the sports and crypto splits, the top series family's share, the events and
  the projected 21-day events (both forms), the `n_members` distribution and the cap's loss, the pairwise unit overlap with the
  other LT8 populations and with LT7 CH195's, CH197's and CH192's population definitions on the same days, class or tercile
  shares by liquidity tier, per-market unit sums, `vol_missing` shares **and the 2 x 2 table of `vol_missing` against a missing
  `last_trade_price` (R1 must-fix 8)**, and the computed DE beside `DE_gate`. CS8 also prints **the `vol_missing` share among
  CH203's primary units**, which sets world 8's `p_vm` (1.8.1). CH203:
  distributions of `imb5`, `dimb5`, `dimb1`, `dlev`, `lag_s`; the silent-arm share; `ft_both` and rewarded shares; the number of
  lag pairs per market behind `r_w`; `r_w` and `r_pool` both. CH202: `early_share` distribution (and its mass at 0, 0.5 and 1
  for 1c moves), class shares by anatomy and tick, the `|x| >= 2` ticks share, the `lag_g` distribution and its > 10-minute
  share (the stale-row print), `chg_1h` missing and exact-zero shares. CH204: `sc_conc` distribution, the scheduled share, the
  distribution of `s*` over the 12 slots, category shares, the share of scheduled markets still scheduled with the same `s*`
  12 origins later (counts only, where the census span allows), the hot slot's mean |move| share, and the 12:31Z slot's share
  of `s*` separately (the DST disclosure of 1.1: the census days were on summer time).
- **Order (cheapest kill first):** CC8 (CH204: captures only, the likeliest kill), then CS8 (CH203, CH202). A test whose census
  fails has its reader kind switched off before the reader's code freeze.
- **Expected census fates (declared now).** **CH203** passes its coverage, quiet and identification gates on the round's
  arithmetic; it is **borderline on the F-MDE gate** (it needs `n_eff` >= about 1.0-1.4M after the cap and the band) and at
  risk on the cap share and the computed DE. **CH202** is borderline on its class MDE at the low count and untested on the
  block-gate share of all movers and on `VIF_w` with the `chg_1h` control; CH202 also needs >= 12 origins in each sweep block
  (24 / 21 on the file list). **CH204** is likely to drop (its MDE at the low count, 0.57c, exceeds 0.5c; it needs about 2,550
  hot units a day; scheduled count, events, venue clock and category concentration are unprobed and measured on summer time).
  After census, the binding leak worlds (1.8) are expected to remove CH203 (world 8) and possibly CH202 (worlds 3, 5).

**Census jobs (to be drafted later under `docs/research_lab/queue/drafts/` in README format; ids from q0620 upward, checked
unused across `docs/research_lab/queue/` in the history of every local and remote-tracking ref on 2026-10-22: the highest id
used is q0604, LT7 also cites q0605-q0607 as text; none is written in this commit).**
- `q0620_lt8_census_restore` (lane `net`, about 600 MB): restore the LT7-sealed captures and sweeps named above from the data
  releases, check each sha256 against `lt7_census_inputs.json`, write the restore report; bytes measured first (disk stop
  rule).
- `q0621_lt8_seal` (lane `net`, about 300 MB; after q0620): `run_live_tests8.py seal` writes `lt8_census_inputs.json` (the
  orchestrator commits it).
- `q0622_lt8_census_captures` (cpu, about 1,500 MB, **exclusive**; after the seal commit): CC8 (CH204), streaming per-market
  slot accumulators (no per-run series cache; the q0561 lesson).
- `q0623_lt8_census_sweeps` (cpu, about 1,200 MB, **exclusive**; after q0622): CS8 (CH203, CH202).
- `q0624_lt8_size_check` (cpu, about 800 MB; after q0622-q0623 and the census values committed, so k is fixed before any size
  result exists; `max_retries 1` deterministic-crash only).
- `q0625_lt8_reader` (fallback only, never promoted while the cron line of 8.2 exists).
- `q0626_lt8_analysis` (cpu, about 3,000 MB, **exclusive**, `not_before` the analysis date).
- `q0627_ch206_reward_start_map` (lane `net`, about 300 MB; counts only; the map of 5.2; independent of LT8's pins; counts 0).
All are DRAFT and must not be promoted before the challenger review, the design-text freeze, the code and its freeze check,
and **never while an LT5, LT6 or LT7 census or size-check job is running** (memory-heavy-jobs rule; q0620 `depends_on` LT7's
q0604 or its recorded drop, so the LT8 censuses follow LT7's). Each counts 0.

## 8. Implementation plan (no code in this commit)

### 8.1 Modules to be written (engineering list)
- **Vendored, not imported (LT7 R1 must-fix 10's form).** `backend/astrolabe/research_lab/live_tests8_base.py` is **generated**
  by `backend/scripts/vendor_lt8_base.py`: unmodified copies of the LT3/LT4/LT5/LT7 functions LT8 uses, each its source with
  only the module prefixes removed (`series_frame`, `move_join`, `classify`, `category_cols`, `status_codes`, `is_late`,
  `token0_map`, `project_events`, `fit`, `attrition`, `lee_bounds`, `paper_taker`, `econ`, `block_anchor`, `de_gate`,
  `strata_of`, `block_fl_gate`, `holm`, `expanding_demean`, LT5 R's reward parser, LT7's `rv24*` helper, lag-slot loader and
  mid cache, each where it exists under that name; a missing name is written as new LT8 code, reviewed at the freeze check).
  **Source of the LT7 copies (R1 must-fix 5; option chosen: vendor from the LT7 census code that wrote LT7's seal).** The LT7
  functions (lag-slot loader, mid cache, `rv24*` helper, seal reader) are copied from `backend/astrolabe/research_lab/live_tests7.py`
  sha256 `232c22fb4c3b40e14d828429e052b8eceeaea6732d604c16a693510d9e5ce902` and `live_tests7_base.py` sha256
  `2e8baa9007f60d4c7d3553932906e8e9bac60aa43f35368ba7f2c1ff498c7e20`. **What these hashes are (re-check fix 3):** the census-code
  check (`reviews/LT7_CENSUS_CODE_CHECK_2026-10-22.md`, FIXES_OK_WITH_NOTES) checked `live_tests7.py` sha256 `755fa7d2…`
  (699b9ee9, merged as dde3c3c4); **232c22fb… is that code plus the seal-audit fix 74c7f5ac** (05:45:56Z, reviewed OK_TO_RUN),
  and the seal written at 05:48:25Z recorded these **post-fix** hashes as its `code_sha256` (they equal the files at the
  `chore/arepo-claude-setup` tip); `live_tests7_base.py` 2e8baa90… is the same at every one of these commits. 74c7f5ac touches
  only the seal-input helpers (the helper after `_find` and `seal_inputs`), **not the lag-slot loader or the mid cache that
  LT8 copies**, so the functions LT8 copies are byte-identical in substance to the census-code-checked version. **Rule:** the vendor script refuses unless the source files' sha256 equal
  the `code_sha256` that LT7's own census outputs (q0602-q0604) record for those modules; if LT7's censuses have not run when
  LT8's code is written, it uses the seal's recorded hashes above, and the LT8 freeze check re-verifies them against LT7's
  census outputs once they exist (a mismatch: LT8 re-vendors from the hash LT7's census actually ran, before any LT8 census;
  never after). Commit id and source hashes are recorded in `VENDORED`. **Why this option, not "wait for LT7's pin":** LT7's
  pin is due only by about 2026-12-07; waiting would push LT8's censuses, size check, code freeze and dry run into
  2026-12-07 .. 12-28, three weeks for six sequential steps; this code (census-code-checked, plus a reviewed seal-audit fix
  outside the copied functions) is the code that will have counted the very sealed files LT8 reads, so copying it is the
  closest object; later LT7 edits (before or after LT7's pin) cannot change LT8's copies (drift is recorded in
  `vendored_source_drift_accepted`, never adopted silently). The first draft's "only after LT7's pin" clause is withdrawn.
  LT5's functions (`block_fl_gate`, the reward parser) are still copied from LT5's code by hash although LT5 closed at census
  (re-check fix 4), and LT3/LT4 functions from their registered sources, as before. A
  `VENDORED` table records each copy's source file, source sha256 and normalised-source sha256; a unit test fails on source
  drift unless the spec's `vendored_source_drift_accepted` records it (empty at the pin); another proves no LT8 module imports
  `live_tests3*` .. `live_tests7*`. **The empty-`clob_rewards` rule** (unrewarded = 0) is new LT8 code, not a vendored copy,
  and is unit tested. No frozen or registered module is edited (`live_tests3*` .. `live_tests7*`, `bounce_decomp`; nothing of
  E026).
- `backend/astrolabe/research_lab/live_tests8.py`: the reader and unit builders (`quiet_units`, `swclock_units`,
  `sched_units`), the lag-state builder, the slot accumulators, and the counts-only censuses (`census_captures`,
  `census_sweeps`). `run_once()` (internal non-blocking flock on `live_tests8/run.lock`) finds new complete captures and the
  sweep 1 of each pass and writes, write-once (`%.17g`, atomic hard link): `series/<capture>.csv.gz` and
  `status/<capture>.csv.gz` (market, event, `n_members`, series key, bid, ask, `volume24hr`, `liquidity`, `chg_1h`,
  `chg_1d`, `last_trade_price`, `end_date`, tick, reward fields, sports and crypto flags, receipt, capture start);
  `sweeps/<pass>.csv.gz` (outcome-0 sweep-1 quote, touch sizes, 1c and 5c depths, level counts, `book_timestamp`, receipt);
  a rebuildable mid-only cache `midcache/<capture>.parquet` for the 84-slot look-back and the 168-slot out-of-window reading
  (never a source of frozen values that the series files cannot reproduce); frozen units `<kind>/frozen/<id>.csv.gz` for kinds
  `quiet`, `swclock`, `sched` (with `.nosweep_km1`, `.nosweep_km2`, `.late`); outcomes `<kind>/outcomes/<id>.h<j>.csv.gz` and
  `.s<j>.csv.gz` at capture k + 1 .. k + 5 and k + 12 and sweeps of passes k + 1 .. k + 6; and `passes.jsonl`. **Look-back:**
  at install time `t` in `[REGISTERED_UTC - 72 h, REGISTERED_UTC - 24 h]`, `backfill-series` writes `series/`, `sweeps/` and
  `midcache/` as `lookback` lines for every needed slot from `REGISTERED_UTC - 7 d - 2 h` that started before `t`; the
  installed reader writes `lookback` lines for everything arriving in `[t, REGISTERED_UTC)`; `lookback` lines are never units;
  a needed slot found by neither is `lookback_missing` (counted), never imputed. **Retention dependency (LT7 8.1's rule):** the
  look-back depends on the host keeping captures and sweeps for **at least 8 days** at `t`; the retention in force is recorded
  at install; if it is shorter, missing look-back slots are restored byte for byte from the data releases with their sha256
  checked against the releases' `files.sha256`, else `lookback_missing` (CH204's early units drop, counted). CH204's
  out-of-window reading (days 8-14) is reported only and is NaN where neither the releases nor the reader's own series hold it.
- `backend/astrolabe/research_lab/live_tests8_analysis.py`: the single analysis (1.7-1.10, CH203's arm model and F, CH202's and
  CH204's arms, Holm over k, counting) and the size check (1.8, 1.8.1) with the scenario-to-test map (fail-closed on an unknown
  or missing scenario).
- `backend/scripts/run_live_tests8.py`: `run`, `backfill-series`, `ops-stats`, `seal`, `census-captures`, `census-sweeps`,
  `size-check`, `analyze`; censuses accept `--data-dumps-cap-gb` and exit 75 above it; `size-check` refuses `--worlds/--draws`
  without `--dev`; `analyze` refuses before the date, an unpinned, null or NaN spec, or a `k_tests` naming a dropped test.
- Spec `backend/astrolabe/research_lab/model_specs/live_tests8_v1.json`: every constant, k, seeds (estimators 20261181-83, gates
  20261281-83, size check 20261187 and its derived seeds), dates, `T_X` rules, census scales, cuts and rules, the member cap,
  the crypto classifier, the multiplier, the F rule, the `code_sha256` map and the imported sports-rule hash.
- `battery2.KIND_RULES["live_tests8"]` (fail-closed counting entry).

### 8.2 Resources, collection plan and install
- **No new collector and no network.** A pure reader of the pass's own outputs, once a pass.
- **Memory (measured references, then a ladder).** LT4's measured host dry run: **484 MB** (one capture per run), **525 MB**
  (six); LT3's 534 MB backlog peak; LT7's planning 550-750 MB for a reader with an 84-slot mid cache. LT8 reads per pass one
  capture's selected columns, a sidecar, one sweep's outcome-0 rows (65,771 rows), the 84-slot mid cache (about 70 MB) plus
  per-market slot sums (12 floats per market), and its targets' quotes. **Planning: peak 450-650 MB in a backlog pass, 350-500
  MB steady (estimates).** Ladder, each step measured by a host dry run with the exact install command before the pin:
  1. one reader, `--max-items 2`, column projection, under `ulimit -v 1572864`: accepted if peak RSS <= 650 MB;
  2. else **two readers** (capture-side: CH204, CH202's capture joins; sweep-side: CH203, CH202's sweep join and every
     sweep target) serialised by one shared `flock`, each `--max-items 2`, accepted if each peaks <= 650 MB;
  3. else no pin and LT8 is not registered (recorded; no further variant).
- **Install route: host cron** (LT4/LT7's route): `5 */2 * * *` (94 minutes after each even-hour :31 pass start, after LT7's
  `:55` line, 26 minutes before the next slot, the earliest freeze deadline), own `flock`, `nice -n 19`, `oom_score_adj 1000`,
  `ulimit -v 1572864`. The queue draft q0625 is the fallback, **never both**. LT8 needs no sweep of pass k for any state, so a
  late sweep loses only targets (counted), never units.
- **Concurrency.** LT7's reader runs until its last targets (about 12-29T15Z); LT8's from install (12-27..12-29) for look-back.
  Two readers overlap for about two days, offset by 10 minutes, each under its own flock; peaks are additive at most about
  1.4 GB on the 12 GB host.
- **CPU:** about 1-3 min a steady pass (estimate). **Disk:** about 1.5-2.5 GB over the window (CH203's whole-panel units
  dominate; CH204's scheduled panel next); the reader stops writing at 3.0 GB in `live_tests8/`.
- **Analysis job:** about 3-4 million unit rows across three tests; CH203's block gate refits 200 times on about 1-2 million
  rows; planning 2-3 GB peak, **exclusive**, single run.
- **Host change:** installing the cron line is a host change under the standing collection authorisation, done by the
  orchestrator.

### 8.3 Tests to be written (`backend/tests/unit/test_research_lab_live_tests8.py`, synthetic only)
- CH203: `imb5` and `dimb5` from sweep 1 of passes k - 2 and k - 1; a sweep received after capture k's start gives no unit
  (`sweep_after_origin`); the two quiet conditions at their edges; the mid band; the member cap and its counting rule (an event
  of 11 members goes to the ladder arm; a market without `event_id` has 1 member); the census scale shared by lead and lag; the
  lag at k + 5, k + 6 through the sizes-only loader; a missing lag leaves the unit in the primary and out of the arm; the
  empty-`clob_rewards` rule; `ft_both`; `rw_changed`; the silent-arm rule; the target `mid_{k+3} - mid_{k+1}` (a planted move in
  (k, k + 1] leaves it unchanged); **the boundary: 12-30T00:31Z and 02:31Z give no unit (`lt7_boundary`) and 04:31Z is the
  first origin; the rule follows `REGISTERED_UTC` if it slides**.
- CH202: `early`, `late`, `early_share` and the clip; classes at their edges (0.25, 0.75); 1c moves at half-tick resolution;
  `|x| >= 0.01` (the 2-tick subset as S2 only); the sweep receipt rule; `lag_g`; the `chg_1h` control with its missing flag;
  the block gate shifts only held and fresh units; the far-future mover' arm at k + 4 -> k + 5; the boundary (first origin
  12-30T02:31Z).
- CH204: the 84 changes and the >= 70 rule; `m_s` with the >= 5 of 7 rule; `sc_conc`; `s*` and ties; rolling days; the >= 1c
  day rule; the >= 4 of 7 argmax rule; `sc_hot` on `sigma(k + 2)`; `sc_rot`; yesterday's same-slot `|Δ_{k-10}|`; the 11 slot
  dummies; `rv7d*`; a missing look-back slot gives `lookback_missing`, never imputed; the out-of-window `s*_2` NaN when
  unavailable.
- **Lag-slot loader:** a census reading a later sweep receives only the keys and the two 5c depths; a test plants wild prices
  and touch sizes in the later slots and shows that no census output changes and that no other column is reachable; CH204's
  census reads no capture after k.
- **R1 items:** world 12 is in the size check's reported list and absent from the binding map (a failing world 12 changes no
  test's status); worlds 3 and 5 hand the model `chg1h_obs` from the proxy rule (the true `D60` is unreachable from the model's
  inputs; exact zeros and the missing flag occur); world 8 reads `p_vm` from the committed CS8 output and refuses a value below
  0.78; the CS8 per-block minimum (>= 12 origins in each sweep block) makes every gate of that test NaN when not met; the seal
  refuses unless its `slots` map equals LT7's 159 entries and it records the frozen LT8 design hash; the vendor script refuses
  unless the LT7 source hashes equal the LT7 census-code hashes (8.1).
- **Vendored base:** the `VENDORED` provenance check; no LT8 module imports `live_tests3*` .. `live_tests7*`; copied constants
  equal their sources.
- Shared: causality (future captures and sweeps with wild prices leave every frozen line byte-identical); late refusal,
  write-once, dry-run guard, `%.17g` round trip, run lock; `ops-stats` reads no price column; the `code_sha256` map; counting
  equals k; Holm; the p = max rule and the `G_minor` df; F's two conditions and the Inconclusive mapping; the analysis refusals;
  the design-freeze and `T_X` rules (registration refused when not before `T_LT7`; no `T_V` rule, R1 must-fix 1); sealed censuses (counts only, tampering refused, completeness, minimum covered days); each MDE and F-MDE gate
  formula with `max(declared, design)` and the 0.5c F-MDE cap; the end-date filter; the scenario-to-test map (scenarios 1-12;
  a failing scenario sets only its own tests to "SE check failed" with k unchanged); `lookback` lines never become units; an
  end-to-end synthetic analysis with a reduced `k_tests`.

### 8.4 Registration steps and pins (in order)
1. Challenger R1 on this file; the response and any re-check. **At acceptance, and in any case before 2026-12-01T00:00Z, the
   engine embargo requests of section 9 are filed in `signal_engine/CANDIDATES.md` and applied** (not a registration step).
2. **Design-text freeze commit**, its sha256 in the ledger, before the earlier of 2026-11-15T12:00Z and `T_E015`.
3. q0620 restore, q0621 seal, seal committed and pulled on the host (after LT7's last census, q0604, or its recorded drop).
4. Code (8.1, 8.3), with the LT7 copies vendored from the hashes LT7's seal recorded (the census-code-checked code plus the
   seal-audit fix 74c7f5ac; 8.1); a `science-reviewer`
   freeze check of the census and size-check code against sections 1.8, 1.8.1 and 7;
   fixes (none may change frozen text, 1.1).
5. Censuses q0622-q0623 (counts only); drops recorded in 6.3; `k_tests`, scales, cuts and `exclude_family` filled with the exact
   census floats; a freeze record written (module hashes, spec hash before the pin, census output hashes re-verified on the
   host, spec values checked against the census JSON).
6. Size check q0624 (2,000 worlds x 200 draws, seed 20261187); results recorded per test.
7. Reader freeze check; host dry run with the exact cron command following 8.2's ladder (the step used is recorded).
8. LT7's registration commit (or recorded drop) exists; the LT7 copies in `live_tests8_base.py` are those vendored at step 4
   from the hashes LT7's seal recorded (8.1, R1 must-fix 5, re-check fix 3), re-verified against LT7's census outputs; the embargo entries
   applied at step 1 are verified in `config.EMBARGO` (a missing entry blocks the pin); any token or extension of a test
   dropped at census is withdrawn with a ledger line. If LT8's window slides, the config entries are extended before their
   current date to the later of 2027-01-23T00:00Z and LT8's analysis commit.
9. Pins: `SPEC_SHA256`, `code_sha256` map, `code_check` passing; E-numbers assigned from the ledger; the ledger entry is the
   registration commit, at least 24 h before `REGISTERED_UTC` and before `T_LT7`.
10. Record the host's capture and sweep retention (>= 8 days needed, 8.1); install the cron line and run `backfill-series`
    within `[REGISTERED_UTC - 72 h, REGISTERED_UTC - 24 h]`; verify `pinned: true` and `nothing_new` before `REGISTERED_UTC`;
    queue q0626 with `not_before` the analysis date.

## 9. Signal-engine mapping and embargo requests

Every family below is point-in-time from the origin capture, the sweeps of passes k - 2 and k - 1, or the engine's own earlier
`quotes/` (DESIGN_V1 16 causality). Each is an **auxiliary family** (own write-once table and version string). **Embargo
first** (DESIGN_V1 8): any challenger that isolates one of these families carries its token until **the later of
2027-01-23T00:00Z and LT8's analysis commit** (LT8's analysis date 2027-01-21T12:00Z plus about 36 h; never earlier). **Timing:**
the requests are filed in `signal_engine/CANDIDATES.md` and applied **when LT8's design is accepted, and in any case before
2026-12-01T00:00Z** (a month before `book` and `book0` lapse on 12-31), whether or not acceptance has come by then; they are not
a registration step. The round-13 note already in `CANDIDATES.md` asks the builder not to build an isolating challenger for
`quietbook`, `swclock` or `sched` before LT8 fixes its dates; this file fixes them. This branch does not edit
`CANDIDATES.md`, engine code or `config.EMBARGO`. In the table, "2027-01-23" means the later of 2027-01-23T00:00Z and LT8's
analysis commit.

| Test | Family (aux version) | Columns (NaN = missing) | Source and clock | Token -> until |
|---|---|---|---|---|
| CH203 | `quietbook` (`se-aux-quietbook-v1`) | `qb_dimb5`, `qb_dimb1`, `qb_dlev`, `qb_dgrain_b`, `qb_dgrain_a`, `qb_quiet` | sweep 1 of passes k - 2 and k - 1 (both before the origin), the origin's Gamma mid | `quietbook` (new) -> 2027-01-23; **`book0` and `book` -> 2027-01-23 (from 12-31)** |
| CH202 | `swclock` (`se-aux-swclock-v1`) | `sw_early_c`, `sw_late_c`, `sw_early_share`, `sw_held`, `sw_fresh`, `sw_early_share_6h` | sweep 1 of pass k - 1 against captures k - 1 and k | `swclock` (new) -> 2027-01-23; `book0` as CH203 (`b0_gap` is the late part) |
| CH204 | `sched` (`se-aux-sched-v1`) | `sc_conc7d`, `sc_hot_next`, `sc_slots_to_hot`, `sc_hot_absmove7d`, `sc_scheduled` | the engine's `quotes/` of slots k - 84 .. k | `sched` (new) -> 2027-01-23 |

**Requests to the signal-engine track (this branch does not edit engine code; `config.EMBARGO` is not edited here).**
- **New tokens `quietbook`, `swclock`, `sched`** to the later of 2027-01-23T00:00Z and LT8's analysis commit, entered at
  acceptance (and before 12-01) and before any isolating challenger is scored.
- **`book0` and `book` from 2026-12-31 to the later of 2027-01-23T00:00Z and LT8's analysis commit.** A model isolating
  `book0` (pass k - 1) and `book` (pass k) can form their difference, the book innovation over (k - 1, k], adjacent to
  CH203's (k - 2, k - 1]; `se19_lr_book0` isolates `b0_gap`, which is CH202's late part. **Cost, disclosed:** the book families
  stay hidden about 23 more days (se18's visible broad score is unaffected; its `book0` family attribution stays hidden). If
  CH203 and CH202 both drop at census, this extension is withdrawn with a ledger line; if only one drops, it stays.
- **Attribution limits.** No attribution (SHAP or otherwise) of the champion, `se18_lgbm_all_b0` or any broad model on
  `b0_gap` x own 2 h change interactions, on two-sweep book differences, or on per-market slot-of-day interactions, computed or
  shown before the later of 2027-01-23T00:00Z and LT8's analysis commit; no LT8 family added to a broad model before then, or
  such a model recorded in the ledger as a development look. **Disclosed now:** `se18_lgbm_all_b0` is broad, visible and
  promotion-eligible and holds `b0_gap`; its aggregate score is a development look at half of CH202's state (10).
- **LT6-V lapses from the `book` and `book0` test lists (R1 must-fix 1).** LT6 V was dropped at census and is never
  registered, so its entry in those tokens' `tests` lists (`config.EMBARGO`) no longer protects anything; the tokens' dates are
  set by LT7 CH195/CH197 (12-31) and, if this request is applied, by LT8. Removing the stale entry is the builder's edit.
- **Not requested:** `surprise` (UTC hour and weekday, to 11-19) is not extended for CH204 (it holds no per-market slot
  history; question 12); `movetype` (12-31) is not extended for CH202 (anatomy is a control, not the tested term); `rewards`
  (11-22) is not extended for CH203 (reward fields are controls); `steam` and `rwstart` are not requested (5).
- If a test drops at its census, its new token and any extension made only for it are withdrawn with a ledger line (dates move
  earlier only by that withdrawal, never otherwise).

The engine's yardstick (log-loss gain under `se-promotion-v2`) is a different question from each LT8 primary. A Supported LT8
primary makes its family a candidate; an engine gain never changes an LT8 verdict and an LT8 verdict never promotes a model.

## 10. Disclosures

- **Selection history.** The three tests are round 13's ranks 1-3 (creative-lead pass written 2026-10-22 on `82e4295e`, from
  the ledger, LT7's planning, DESIGN_V1 21-22, CANDIDATES and stream docstrings, with no host probe), taken in the round's own
  recommendation ("if the LT8 designer wants k = 3 ... CH203, CH202 and CH204"). Every design change (6.1) was made before any
  data.
- **The designer** read, on 2026-10-22: `CREATIVE_HYPOTHESES_2026-10-27.md` (sections 0, 0.1, the structural facts and counts
  table, 1, 2.A-2.D, 3, 4, 5); `LIVE_TESTS_7.md` (all sections including 13 and 13.5); `LIVE_TESTS_5.md` (section headers and
  7.3); the ledger by bounded read (lines 3440-3577: the LT5/LT6/LT7 seal, census and freeze entries, the book timing overlap,
  `book0`, the resize, LT5's census drops, E022's registration); `signal_engine/CANDIDATES.md` (embargo round 4, the 10-22
  notes, the round-13 and builder-status `book0` lines); `COLLECTION_HOST.md` (retention and growth lines); the file list,
  hashes and slot assignment of `seals/lt7_census_inputs.json` (no data); `book_sweep.py`'s field list. **Known to the
  designer before drafting:** DESIGN_V1 22's `b0_gap` diagnostic (correlations -0.04 to -0.16 with the 2 h label move;
  `b0_spread` +0.09 to +0.15 with a move larger than DELTA), quoted by round 13; LT5's census counts (F, H, R); LT7's planning
  figures; ML-r4_book's family-level result (`descriptive_only` for the pmxt book family). No data, host, outcome, price after
  an origin, P&L, `data-dumps` file, evidence JSON or analysis output was read; no threshold was chosen from data.
- **Closest prior AREPO tests.** CH203: LT7 CH197 and CH195, LT6 V, E022, E020, E003, ML-r4_book, CH169, CH133, CH147, CH116.
  CH202: CH194 (withdrawn), E002/E004/E006 (the confirmed reversal; informing), E015, E021, LT5 J, LT7 CH191 and CH195, CH37,
  the `b0_gap` diagnostic. CH204: LT7 CH192, E011, CH57, CH33, CH28, CH18, round 11's rejected own-hours profile, the engine's
  `surprise` and dropped `regime` families.
- **Mechanics stated up front.** CH203: the level (control; VIF gate), the trend (F, M-Q), farmer re-posts (reward controls,
  `ft_both`, `rw_changed`), fill depletion (same-signed; only partly controlled because `volume24hr` is missing on about 78% of rows; `dV_prev`, M3,
  the binding leak world 8 at `p_vm >= 0.78`), the stale Gamma mid (target from k + 1, M1),
  boundary truncation (mid band). CH202: the bounce (skip target, M2), the known reversal (`chg_1h` control, scenario 3), the
  stale display (scenario 5, M1, `lag_g`), anatomy (controls), ticks (S2), shared shocks between labels and targets (block
  gate). CH204: the venue clock (slot dummies, venue-clock gate, scenario 10), clustering (block gate, scenarios 10-11), chance
  schedules (scenario 12, out-of-window reading), category clocks (category gate, S4), the year-end schedule break (1.1).
- **F can reject a true but persistent signal** (CH203): a time-symmetric arm cannot tell a persistent informative innovation
  from a slow trend that the innovation proxies equally before and after; LT8 accepts that cost (LT7 10).
- **The round's figures are not LT8's.** CH203's 0.16c (round) became 0.35c (LT8) through the k + 1 target, the member cap,
  the mid band and ex-crypto losses; CH202's 0.26c became 0.38c at LT7's lower mover count; CH204's 0.52c (round, DE 31)
  became 0.57c once its own 0.85 factor is applied to the hot count (R1 must-fix 3). The prior odds of section 0 are the
  designer's: census survival 0.30, 0.25, 0.10 (the round's 0.35, 0.30, 0.20), and about 0.10, 0.12, 0.08 for a valid verdict
  after the binding worlds (13).
- **LT6's census counts were read (R1 must-fix 1).** In the R1 response the designer read `LIVE_TESTS_6.md` 6.3 at the
  `chore/arepo-claude-setup` tip: V dropped on within-market |corr(zv, z v_prev)| = 0.595 (pooled 0.566) > 0.5 with every
  other gate passing (projected 331,728 units, both-sweep coverage 0.93, block recurrence 0.93, tercile MDE 0.35c at `DE_gate`
  7.2); D on 3 later units; B on no birth unit; K on 13 clip units. These are counts on neighbouring book populations (V's
  movers with the pass k - 1 and k sweeps). **No LT8 gate, threshold or planning figure was changed because of them; in
  particular CH203's `VIF_w <= 2.0` gate stays exactly as drafted** (the reviewer's rule). The LT6-V entries in the `book` and
  `book0` tokens' test lists lapse with V (`config.EMBARGO`); the tokens' dates are unchanged by that (section 9).
- **Retention dependency.** The look-back needs the host's capture and sweep retention to be at least 8 days at install, or a
  byte-identical restore from the data releases (8.1).
- **Shared data.** Every earlier test and the engine read the same captures and sweeps; LT8's window overlaps none of theirs;
  CH204's look-back reads raw files of LT7's last week and LT8's first states read raw files that are inputs of LT7's reported
  24 h secondaries (1.1).
- **Window.** Results arrive about 2027-01-21, after every adjacent analysis; the reasons are in 1.1.

## 11. Open questions for the challenger review

*(Answered by R1, 2026-10-22; the rulings and the resulting changes are in section 13.3. The questions are kept as asked.)*

1. **CH203's target at k + 1** (`y_s = mid_{k+3} - mid_{k+1}`, SD 4.5c, 1.5x the planning MDE) against the round's `c2 = mid_{k+1}
   - mid_k`: is the stale-Gamma-mid catch-up a real threat for a pre-origin book state on quiet books, or should `c2` with a
   binding sweep-mid label be the primary?
2. **Sweep 1 instead of `book0`'s sweep** (6.1 item 2): acceptable, given the sealed census holds sweep 1 only?
3. **CH203's F placement** (lag innovation between sweeps k + 5 and k + 6, the nearest sweep pair to the mirror of the lead's
   gap) and the binding F for an innovation: is M-Q the right mechanical twin? Should the lag be required quiet too?
4. **CH203's fill confounder** (same-signed; `dV_prev` control, silent arm M3, world 8): is a label enough, or should the
   primary be the silent arm (it loses the units without `volume24hr`, about 78% of rows)?
5. **`volume24hr` missing as an indicator pair** (1.5, 6.1 item 10), a declared exception LT7 did not make: accept, or exclude
   the field as a control in whole-panel tests?
6. **CH202's `sign(x) x chg_1h` control:** does it remove enough of the E002/E004 channel for the contrast to be "beyond the
   reversal"? Is the `|corr| <= 0.8` gate with `VIF_w` in the MDE the right identification rule, and is scenario 5 the right
   stale-display world?
7. **CH202's mover threshold** `|x| >= 0.01` (the round's 2 ticks reported) and the 800-a-capture count gate in place of the
   round's 1,500 kill line: acceptable before data, given that the MDE gate binds?
8. **CH202 and CH204 F as reported labels** (built from price changes; LT7's CH191 ruling): accept, or bind CH204's rotation?
9. **CH204 scenario 12** (a schedule redrawn every 7 days): a null world at all? If the block gate rejects in it at more than
   0.058, CH204 would be "SE check failed" for a world in which `sc_hot` predicts by construction within a week; drop it,
   keep it binding, or make it reported?
10. **CH204's slot dummies** as controls, the venue-clock gate (<= 50% in one slot) and the category gate (<= 70%): enough to
    separate a market's own clock from the venue's and a category's?
11. **The member cap <= 10** for CH203 and CH204 (round rule 3) and its counting rule (binary open active markets of the event in
    capture k): right? Should CH202 carry it too?
12. **Embargo:** `book0` and `book` to the later of 2027-01-23T00:00Z and LT8's analysis commit (about 23 more days hidden), and
    no `surprise` extension for CH204: agree?
13. **The design-text freeze before the earlier of 11-15T12Z and `T_E015`** (earlier than the round's 12-07) with the
    consequences of 1.1 (CH203 dropped if after `T_V`; every test dropped if registration is not before `T_LT7`): enough, or must
    CH202 also drop if its freeze follows `T_E015` (it uses E015's anatomy only as a control)?
14. **Census inputs:** the LT7-sealed captures and sweep-1 passes (41 / 45 / 40 origins over 3.3-3.75 days, 23 F pairs for
    CH203): enough for the F-feasibility correlation (>= 1.5 covered days of pairs)? Should the census require both sealed
    sweep blocks?
15. **The window over New Year** (2026-12-30 .. 2027-01-20), 21 days, no extension, holiday-excluded sensitivities only, and
    CH204's first-week schedules built from the Christmas week: agree, or should CH204's first origin wait until 2027-01-06?
16. **Multiplier 3.47** kept for k <= 3 (exact 3.145): agree?
17. **CH205 and CH206:** is "not proposed (scope)" for CH205 and a separate counts-only map (q0627) for CH206 the right handling,
    and may the map run before LT8's freeze without informing LT8 (it reads no price and no LT8 population)?

## 12. Draft ledger block (DRAFT, not registered, not counted)

> ## LT8 (three round-13 candidates: CH203, CH202, CH204) — DRAFT pre-registration (not registered, nothing counted, no code)
> - **Design:** `docs/research_lab/LIVE_TESTS_8.md` on `feat/live-tests-8`. Pure reader of streams the host already writes
>   (complete captures, sidecar, sweep 1 of passes k - 2 .. k + 6); no network, no new collector; separate store
>   `live_tests8/`; LT3/LT4/LT5/LT7 functions **vendored** into a generated `live_tests8_base.py` (LT7's from the hashes
>   recorded by LT7's seal, 232c22fb… / 2e8baa90…: the census-code-checked 755fa7d2… plus the seal-audit fix 74c7f5ac, which
>   touches only seal-input helpers, not the copied loader or mid cache; R1 must-fix 5, re-check fix 3);
>   memory planned from LT4's measured 484-525 MB with a two-step ladder (<= 650 MB each); install by host cron `5 */2 * * *`;
>   look-back needs >= 8 days of host retention or a byte-identical release restore.
> - **CH203** the quiet book: YES change over (k + 1, k + 3] on the 5c-imbalance innovation between sweep 1 of passes k - 2 and
>   k - 1 (both before the origin) behind an unmoved touch, the level fixed, > 0; events <= 10 members; block Freedman-Lane
>   gate; far-future innovation F binding (sweeps k + 5, k + 6, sizes only); planning slope MDE 0.35c, F-MDE 0.50c at `r_w` 0
>   (DE 31, `n_eff` 1.0M); borderline on its F-MDE gate; likely to fail its binding fill-leak world 8 (`vol_missing` >= 0.78).
> - **CH202** the sweep clock: held (the CLOB had >= 75% of the 2 h move at pass k - 1's first sweep) against fresh (<= 25%) on
>   `c_skip`, > 0, the signed Gamma 1 h change a control; block gate with a one-path stale-display world; class MDE 0.38c
>   (0.37c at its count floor with 15% class shares, 80% effective; 0.52c at the least favourable split); binding leak worlds
>   with a noisy, lagged `chg_1h` proxy; *informed (E002/E004)* and *informed (b0_gap diagnostic)*; CH194's declared heir; borderline.
> - **CH204** the market's own clock: |move| over (k + 1, k + 2] at the market's own hot slot (7-day look-back, scheduled rule
>   declared) against its cold slots, 11 slot-of-day dummies held fixed, > 0; events <= 10 members; block gate; rotation and
>   out-of-window readings reported; class MDE 0.57c (low, DE 31; 0.40c high; R1 must-fix 3); world 12 reported; likely to drop.
> - **Family:** Holm over **k <= 3** (census-fixed; expected 0 to 1; if 0, LT8 is not registered), one-sided, alpha 0.05;
>   p = max(event t, two-way, day t) (`G_minor - 1` df for CH202 and CH204); multiplier 3.47 (not lowered); F-MDE cap 0.5c;
>   11 binding size scenarios (10 gate worlds, of which 3, 5 and 8 are leak worlds with a noisy lagged `chg_1h` proxy or the
>   census `vol_missing` share >= 0.78; 1 mechanical verdict-size world) and worlds 3r and 12 reported, a failure sets only its own
>   tests to p = 1;
>   window proposed `[2026-12-30T00:00Z, 2027-01-20T00:00Z)` keyed to LT7's `END_UTC` + 24 h (slides with it; never before
>   12-30), single analysis on or after 2027-01-21T12:00Z; design-text freeze before the earlier of 2026-11-15T12:00Z and
>   `T_E015` (LT6 closed, so no `T_V` rule); no read of E015/E022/LT5/LT7 outputs before the pin (LT6's census counts read
>   and disclosed); after LT7's census commit any LT8 change is *informed (LT7 census)*; registration after
>   LT7's registration commit (or drop) and before `T_LT7`. Census inputs: the LT7-sealed captures and sweeps (seal
>   117e9b45…), restored, sealed and counted once each (q0620-q0623).
> - **Deferred:** CH205 (sports scope; not proposed); CH206 a counts-only map (q0627; counts 0); CH207-CH211 engine-first.
> - **Status:** DRAFT; challenger R1 REVISE (2026-10-22) answered in section 13 (only the review's items applied; any later
>   change after LT7's census commit labelled *informed (LT7 census)*); awaiting the R1 re-check, the design-text freeze, restore and seal (q0620-q0621), code and freeze check,
>   censuses (q0622-q0623), size check (q0624), dry run, pins and registration. Engine embargo requests (new `quietbook`,
>   `swclock`, `sched`; `book0` and `book` from 12-31 to the later of 2027-01-23T00:00Z and LT8's analysis commit) to be filed
>   in `CANDIDATES.md` at acceptance and in any case before 2026-12-01. **E-numbers not assigned.**

## 13. Response to challenger R1 (2026-10-22; reviews/LT8_CHALLENGER_R1_2026-10-22.md, REVISE)

Text only, before any LT8 census, seal, size run or window data, and **before LT7's censuses q0602-q0604 have run** (no CC7/CS7
output exists in `seals/`); nothing was chosen from data and no E015, E022, LT5, LT7 output was read. New context read for the
response: the review record (9f99504d), `LIVE_TESTS_6.md` 6.3 at the `chore/arepo-claude-setup` tip (LT6 closed; counts
disclosed in 10), `config.EMBARGO`'s `book` / `book0` entries, and the sha256 of `live_tests7.py` / `live_tests7_base.py` at
699b9ee9, dde3c3c4 and the chore tip (for must-fix 5). **No threshold, floor, alpha, seed, date or direction was loosened,
with one qualification (re-check fix 3): as first written, this response re-scaled binding world 3's effect (0.02 per SD to
about 0.0012 per SD) and spread world 5's reversal over three passes, which R1 did not ask for and which weakened two binding
worlds; the re-check found both, and they are restored (13.6, fixes 1-2).** With that restoration, nothing is loosened.
Every change removes a moot rule, corrects arithmetic, adds a disclosure, a print, a reported arm or a minimum, makes a world
more realistic, or fixes an order of steps. The changes are applied in sections 0-12; where any text differs, this section
governs.

**Scope declaration (must-fix 2).** This response applies **only** the items of the R1 record. LT7's censuses count the same
sealed files and neighbouring populations and are expected before LT8's design-text freeze; **after the LT7 census commit,
any change to an LT8 gate, filter, planning count or expected fate is labelled *informed (LT7 census)*** on the affected
test, recorded in the ledger with its reason, and carried to the verdict (1.6).

### 13.1 Must-fix items

| # | Item | What changed | Where |
|---|---|---|---|
| 1 | LT6 closed; the `T_V` drop rule is moot | The rule dropping CH203 if the freeze is not before `T_V` is withdrawn everywhere; the 1.1 table row now records V as closed with no rule; a new 1.1 bullet rewrites the chain (LT7's window follows its own rules (a) and (c); after LT5's closure (re-check fix 4) these are the only remaining slide risk; the R1 text's "LT5 J/O registration" risk is moot); the LT6-V entries in the `book` / `book0` test lists lapse (dates unchanged); LT6's census counts, including V's within-market correlation 0.595 (pooled 0.566), are disclosed as read; **CH203's `VIF_w <= 2.0` gate is unchanged** | header, 0, 1.1, 1.6, 1.11, 8.3, 9, 10, 12 |
| 2 | LT7's census will precede LT8's freeze | Declared: the response applies only this review's items; after LT7's census commit any change to a gate, filter, planning count or expected fate is labelled *informed (LT7 census)*, re-check fixes included unless the reviewer records independence; LT7 census outputs are opened before LT8's freeze only to verify a hash | header, 1.6, 12, 13 |
| 3 | CH204's MDE did not follow its chain | `n_1` = 1,955 x 21 x 0.8 = **32,844** (high 65,520), `n_2` = 11 x `n_1`; MDE **0.57c low, 0.40c high** (DE 31), 0.66c / 0.47c at DE 41, quarter 1.14c / 0.81c (computed: 0.571, 0.404, 0.657, 0.465, 1.143, 0.809); the 0.5c gate needs about 2,550 hot units a day; 6.1 item 9's false claim corrected; prior odds of surviving census 0.15 -> **0.10** | 0, 4, 6.1, 10, 12 |
| 4 | CH202's floor MDE used the wrong count | The gate counts 201,600 **held plus fresh**: with 15% class shares (100,800 each) the MDE is **0.33c raw** (the reviewer's figure; computed 0.329) and **0.37c at the 80% effective share** used everywhere else (0.368); shown also: the least favourable split the gates allow (held 30,240, fresh 171,360, no mixed) **0.52c** (0.515). Gate unchanged | 0, 3, 12 |
| 5 | Vendoring order contradicted the census step | **Option chosen: vendor from the LT7 census code that wrote LT7's seal** (`live_tests7.py` 232c22fb…, `live_tests7_base.py` 2e8baa90…, the post-fix hashes the seal recorded at 05:48:25Z and the chore tip's: the census-code-checked `live_tests7.py` 755fa7d2… plus the seal-audit fix 74c7f5ac, reviewed OK_TO_RUN, which touches only the seal-input helpers and not the loader or mid cache LT8 copies; `live_tests7_base.py` unchanged throughout; re-check fix 3), the vendor script refusing unless the source hashes equal those LT7's census outputs record; the "only after LT7's pin" clause withdrawn. Justification: waiting for LT7's pin (about 12-07) would compress six sequential LT8 steps into three weeks before 12-28, while this code is the reviewed code that will have counted the same sealed files; later LT7 edits cannot reach LT8's copies (drift recorded, never adopted) | 8.1, 8.3, 8.4, 12 |
| 6 | World 12 is not a null | **Decided now, before any size result: world 12 is reported, never binding**; the failure-consequence list is 1-8 and 10-11; CH204's text now names worlds 10-11 as its binding gate worlds | 0, 1.8, 1.8.1, 4, 8.3, 12 |
| 7 | Worlds 3 and 5 gave the control the exact last-hour change | A **noisy, lagged last-trade proxy** `chg1h_obs = p_lt(t - L) - p_lt(t - L - 60 min)`, `L ~ U(0, 60)` min, Poisson trades at `lambda_m ~ U(0.5, 6)` per hour, exact zeros, 10% missing, is the only control the model sees in both worlds; the effect acts on the true `D60`; **after the re-check (fixes 1-2):** binding world 3 keeps the first draft's 0.02 per SD of `D60` (the E002-scaled `0.14 x D60` is the reported world 3r) and world 5 keeps the first draft's reversal of 0.21 at the next two passes, named t + 2 and t + 3 (all inside the skip target); both stay binding as **leak worlds**; CH202's valid-verdict odds about 0.12 | 0, 1.8, 1.8.1, 1.11, 3, 12 |
| 8 | CH203's fill confounder was called "addressed" | Text now says it is only partly controlled (`volume24hr` absent on about 78% of rows); **world 8 carries `p_vm` = max(the CS8 census `vol_missing` share of CH203's primary units, 0.78)**; the census prints the `vol_missing` x missing `last_trade_price` table and the primary's `vol_missing` share; world 8's fill parameters are kept as drafted (not tuned) and the world is expected to fail, so CH203's valid-verdict odds are about 0.10 | 0, 1.8, 1.8.1, 2, 6.1, 7, 10, 12 |

### 13.2 Should-fix items

| Item | What changed | Where |
|---|---|---|
| Daylight-saving time | Disclosed: census days on US/UK summer time, window on winter time (a US 08:30 ET release moves from 12:30Z to 13:30Z); CH204's census gates are not representative of the window's slot positions; the census prints the 12:31Z slot's share of `s*`; no rule changed | 1.1, 4, 7 |
| The LT8 seal | Reproduces LT7's 159-entry `slots` map exactly (refuses otherwise), records the frozen LT8 design-text sha256, accepts host copies that pass the hash check; the 430-file need and the unconfirmed release coverage stated, with the existing fallback | 7, 8.3 |
| Q14: per-block minimum | Each CS8 test needs >= 1.0 covered day (>= 12 origins) in each sweep block (CH203 22 / 19, CH202 24 / 21 from the file list). **Not applied to CH203's F pairs** (13 / 10, i.e. 1.08 / 0.83 days), because a per-block rule on pairs would drop CH203 by construction before any count; the pooled 1.5-day pair minimum stays and the split is printed. **Put to the re-check:** if the reviewer reads the should-fix as covering pairs, CH203 is dropped uncounted on the file list alone | 7 |
| CH204 category arm; offsets | S8: slot x `fee_category` dummies arm (categories < 1,000 scheduled units pooled), reported; S9 and 1.8: the share of block-gate offsets that are multiples of 12, on data and in worlds 10-12, reported | 1.8, 4 |
| Define "declared" | *declared* = the closed formula at the census's own counts, `DE_gate`, `VIF_w`, gap and the declared SD; *design* = `3.47 x 1.5 x SD x se_1` from the census regressors under a working covariance (unit variance, within-event equicorrelation 0.02, independence across events), no target read; the gate takes the larger | 7 |

### 13.3 Rulings on section 11, as applied
Q1: target from k + 1 kept. Q2: sweep 1 accepted. Q3: lag placement kept; the lag is **not** required quiet. Q4, Q5: accepted
with must-fix 8. Q6: the 0.8 correlation gate kept; must-fix 7 applied. Q7: the 1c threshold and the 800-a-capture gate kept;
text fixed (must-fix 4). Q8: labels accepted. Q9: must-fix 6 (world 12 reported). Q10: partly; the category arm added (S8).
Q11: cap kept for CH203 and CH204; no cap for CH202. Q12: the embargo requests stand, conditional on the census (a test
dropped at census withdraws its token and any extension made only for it, 9). Q13: no drop rule for CH202. Q14: should-fix
above. Q15: dates kept. Q16: multiplier kept. Q17: CH205 not proposed and CH206 a separate map (q0627) accepted; q0620-q0627
are unused in any ref.

### 13.4 Odds re-stated (the designer's judgement; not measurements)

| Test | Survive census (first draft -> R1) | Then pass the binding worlds | Valid verdict | Main reason for the change |
|---|---|---|---|---|
| CH203 | 0.30 -> 0.30 | about 0.35 | **about 0.10** | world 8 at `p_vm >= 0.78` is likely to fail (must-fix 8) |
| CH202 | 0.25 -> 0.25 | about 0.50 | **about 0.12** | worlds 3 and 5 with the noisy lagged proxy may fail (must-fix 7) |
| CH204 | 0.15 -> **0.10** | about 0.80 | **about 0.08** | MDE 0.57c at the low count (must-fix 3); DST; world 12 now reported |

Expected k at census about 0.65 (0 to 1); the chance that every test drops at census about 0.47; the expected number of
tests reaching a valid verdict about 0.3.

### 13.5 Values newly declared here (each with its neutral source)

| Value | Where | Source |
|---|---|---|
| `chg_1h` proxy lag `L ~ U(0, 60)` min, trade rate `lambda_m ~ U(0.5, 6)` per hour, missing 0.1 | 1.8.1 | the reviewer's "up to 60 min" lag; a thin-to-active non-sports range (a convention; no AREPO measurement of Gamma's `chg_1h` basis exists); 0.1 a convention |
| World 5: reversal 0.21 x `D60` at passes t + 2 and t + 3 (0.105 each); world 3: 0.02 per SD of `D60`; world 3r (reported): 0.14 x `D60` | 1.8.1 | the first draft's world 5 and LT7's world 3 scales (re-check fixes 1-2); E002/E004's about 21% at about 5 h for 3r |
| World 8 `p_vm` = max(census share, 0.78) | 1.8.1 | the reviewer's rule; DESIGN_V1 16's 78% |
| Per-block minimum >= 12 origins in each sweep block | 7 | the reviewer's 1.0 covered day |
| Design MDE working covariance, within-event equicorrelation 0.02 | 7 | the `DE_gate` formula's intraclass value |
| CH204 S8: categories < 1,000 scheduled units pooled | 4 | a convention for a reported arm (no gate) |

### 13.6 Re-check fixes (2026-10-22; `reviews/LT8_R1_RECHECK_2026-10-22.md`, ACCEPT_WITH_FIXES; governs where earlier text differs)

Text only; exactly the re-check's four remaining fixes, nothing else. They are made before the LT7 census commit (no
CC7/CS7/CV7 output in `seals/`), and the reviewer records them as independent of it, so they are **not** *informed (LT7
census)*. No gate changed.

| # | Re-check item | What changed | Where |
|---|---|---|---|
| 1 | World 3's effect was re-scaled without R1 asking (a loosening of a binding world) | Binding world 3 keeps **0.02 per SD of the true `D60`**, seen through `chg1h_obs`; the E002-scaled `-0.14 x D60` version is added as **reported world 3r** (never binding) | 1.8, 1.8.1, 12, 13.1, 13.5 |
| 2 | World 5's reversal timing changed (three passes, 0.14 inside the target) | Back to the first draft's **0.21 of `D60` at the next two passes, named: t + 2 and t + 3** (`-0.105 x D60` in each of (t + 1, t + 2] and (t + 2, t + 3]), all inside the skip target; this reading is chosen because the re-check's reason is that the in-target leak must not be lowered (the other reading, t + 1 and t + 2, would put half outside); the orchestrator may overrule the reading before the freeze | 1.8.1, 13.1, 13.5 |
| 3 | "Freeze-checked" was wrong for 232c22fb… | 8.1, 8.4, 12 and 13.1 now say: the census-code check covered `live_tests7.py` 755fa7d2… (699b9ee9 / dde3c3c4); 232c22fb… is that code plus the seal-audit fix 74c7f5ac (OK_TO_RUN review), recorded post-fix by the seal at 05:48:25Z; `live_tests7_base.py` 2e8baa90… is unchanged throughout; 74c7f5ac touches only the seal-input helpers, not the loader or mid cache LT8 copies. Section 13's "nothing loosened" is qualified (the R1 text weakened worlds 3 and 5; restored by fixes 1-2) | 8.1, 8.4, 12, 13 |
| 4 | LT5 closed (2026-10-22 07:35Z, ledger "LT5 closed") | The "LT5 J/O registration" slide risk is moot: LT7 registers after the recorded drops of both LT5 and LT6, so only LT7's own rules (a) and (c) remain; LT5 J as an adjacent test lapses ("dropped at census, no rule"); E-numbers pass to LT7 and then LT8 (LT5 holds none); LT5 has no analysis before LT8's window; J's and O's census counts (J MDE 2.16c, 63.7 units a pass, permutable share 0; O MDE 0.84c, IQR share 0.44, 372 units a pass) are disclosed as read; no gate changes; LT5's vendored functions (`block_fl_gate`, the reward parser) are still copied from LT5's code by hash | header, 0, 1.0, 1.1, 1.6, 1.11, 8.1, 13.1 |

**Ready for the orchestrator's check and the design-text freeze.**

### 13.7 Reward-null rule `listed_carry24h_v2` (from LT7 13.7 and its erratum) (2026-10-22; `reviews/LT8_CENSUS_CODE_FIX_RECHECK_2026-10-22.md`, R2; governs where earlier text differs)

Amendment after the design-text freeze (sha256 `5e61c20b1282cef79c7caee68f08dceb506f845bc1a1325fe2fb9335c955cf48`, now a declared
predecessor), made before the LT8 seal and before every LT8 census, from counts only. The frozen premise of 1.0 (iv), that an empty
`clob_rewards` means no programme, is refuted by LT7's counts-only probe (`seals/lt7_rewards_probe.json`, sha256 263413f2…; no price,
target or outcome read): 30,543 of 258,393 market-days switch between null and non-null `clob_rewards` within a UTC day (0.118), against
a stable listed share, so Gamma leaving the field out is the likelier reading (LIVE_TESTS_7.md 13.7). As frozen, LT8 read a null as 0,
which is LT7's rejected option (A): `rewarded` and `ft_both` mislabel captures where Gamma left the field out, and `rw_changed` fires on
null-to-listed switches, so it flags Gamma omitting the field, not a rate change. These terms feed three CH203 gates:
`corr(zdimb5, ft_both)`, `VIF_w` and the design-MDE `se_1`. CH202 and CH204 read no reward field and are unchanged.

**Rule `listed_carry24h_v2` (replaces 1.0 (iv)'s null-as-unrewarded reading for CH203; spec keys `reward_null_rule:
listed_carry24h_v2`, `reward_carry_slots: 12`).** For a CH203 unit at origin capture k whose sidecar row is present:

- **(a) `rewarded`:** LT7 13.7's rule, word for word. If `clob_rewards` at k is null, `rewarded_k = 1` if a LISTED `clob_rewards` text at
  any sealed capture in the causal window of 12 slots `[k-11, k]` gives a summed daily rate > 0 when **re-parsed for the UTC day of k**
  (the capture's own day is never used for an earlier text); the latest such capture is the **source**. Cross-day windows are allowed;
  the re-parse for day(k) keeps a programme that ended before day(k) from counting. A slot of the window with no sealed capture is
  skipped and counted, never filled (`reward_window_slots_missing`, once per origin). No slot later than k is read, stored or counted.
  A unit with no positive listed text in the window is `rewarded = 0` with the origin capture's parameters. Here a LISTED text is one
  LT8's parser (1.0 (iv)) accepts as a JSON list of valid allocations (rewarded, zero-rate or an empty list); the store holds, per slot
  <= k, every sidecar row's listed text (market_id -> raw string, with that capture's `rewards_min_size` / `rewards_max_spread`), not
  only the markets two-sided at that slot, and is evicted below k-11. The re-parse uses the vendored LT7 code (`RewardCarry`,
  `maker_rewards.parse_daily_rate`), which gives LT8's rate on every text LT8's parser lists (unit tested).
- **(b) Carried units:** take `rew_maxspread` (for `in_band`) and `rewards_min_size` (for `ft_both`) from the source capture. The sweep
  k-1 touch sizes and spread stay as they are; every other control is the origin capture's.
- **(c) `rw_changed`:** compare E(k) with E(k-2). E(s) is the capture's own listed text at s; else the latest listed text in `[k-11, s]`;
  else empty. The NaN rule is unchanged (NaN, excluded and counted, when capture k or k-2 has no sidecar row for the market). Reading of
  "own listed text": a non-null cell at s keeps its own text; a malformed own text (excluded at k anyway) or a sidecar without the column
  keeps its own v1 value at s and is never replaced by a carried text; only a null cell takes a carried one.
- **(d) F pairs:** use the carry at origin k. CS8 already loads `[k-12, k]` for every CH203 origin, so every carry window of an F-pair
  origin is loaded and no v1 fallback is needed (unlike LT7's CH197, whose pair windows were not all sealed). A test confirms this.
- **(e) Unchanged:** a listed text at k is parsed at k as before; a malformed text or an absent sidecar row (or column) stays NaN
  (excluded, counted); no earlier malformed text is read as listed. Gates, thresholds, formulas and MDE inputs are unchanged. As in LT7's
  13.7 erratum (1), units are kept only if `rewarded` and `in_band` are finite and `in_band` uses the source capture's
  `rewards_max_spread`, so a unit can enter or drop through the carry; both are counted and the gates read the units as they stand.

**Counts (as LT7; census output, descriptive).** `rewards_null_carried` and by lag in slots (`_lag1`, `_lag2_3`, `_lag4_11`);
`rewards_null_as_zero` (null at k with no listed capture in the window); `rewards_null_window_listed_inactive` (listed in the window,
none positive for day(k): unrewarded); `carried_param_differs` (source `rewards_min_size` / `rewards_max_spread` differ from the k
capture's); `in_band_known_only_via_carry` and `in_band_lost_via_carry`; `reward_window_slots_missing`; `reward_switch_markets_1` /
`_ge2` and the market-deduplicated `reward_switch_distinct_markets`; and a v1 x v2 table for `rw_changed` (v1 = the k-only comparison
of the frozen text). The v1 values of `ft_both`, `VIF_w` and the slope MDE (v1 `rewarded`, `in_band`, `ft_both` and `rw_changed` on the
v2 unit set) are reported as **descriptive only**: never the verdict, never a gate input.

**Spec and tests.** Spec keys `reward_null_rule: listed_carry24h_v2` and `reward_carry_slots: 12` (both in the sealed spec blocks); the
census refuses a spec without them; re-pinned. Tests: no slot after k is read; cross-day re-parse; a gap; null-like text read back as
NaN (LT7's bug); the effective-text rule for `rw_changed`; F pairs use the carry at k.

**Disclosure.** A deviation after the text freeze (5e61c20b… is the declared predecessor). It comes before the LT8 seal and every LT8
census; its only input was probe counts (LT7's `lt7_rewards_probe.json` and LIVE_TESTS_7.md 13.7). At this amendment's commit no LT7
census output is committed (`seals/` holds no CC7, CS7 or CV7 output), so it is not labelled *informed (LT7 census)*; CV7's host output
was read for its recorded code hash only (re-check R1), not for any count.
