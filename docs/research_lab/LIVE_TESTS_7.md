# Live tests 7 (LT7): six round-12 candidates (CH195, CH191, CH194, CH197, CH193, CH192), DRAFT pre-registrations

**Status: DRAFT, not registered, nothing counted, no code.** Drafted 2026-10-21 on branch `feat/live-tests-7` from the
`chore/arepo-claude-setup` tip `9e00c22d`. This is a design-only first commit, as the first commits of LT3-LT6 were.
E-numbers are **not** assigned here. E026 is the last number used; LT5 provisionally holds E027-E031 and LT6 the next free
numbers for whichever of their tests survive; LT7 takes the next free numbers at its own registration (provisionally in the
order CH195, CH191, CH194, CH197, CH193, CH192 for the tests that survive). Before registration this needs, in order:
1. a challenger review (`science-reviewer`) of this file, the fixes, and a re-check if required;
2. the **design-text freeze commit** (section 1.1) before the earlier of 2026-11-15T12:00Z and `T_E015`;
3. the census input seal (section 7), restored and re-hashed from the data releases;
4. the code (section 8), a freeze check of code against design, and the fixes;
5. the counts-only censuses (section 7), which fix k and every census-fixed spec value;
6. the size check at >= 2,000 worlds on the code to be pinned, through the census-fixed strata (section 1.8);
7. a host dry run with peak RSS measured (section 8.2);
8. LT5's and LT6's registration commits (or their recorded drops), the engine embargo entries of section 9, the
   `SPEC_SHA256` and `code_sha256` pins, the ledger entry and the reader's installation (section 8.4).
Until the pin exists, every line a reader writes is `prospective_unregistered` by construction.

This is research tooling. AREPO never trades. No edge, calibration, profitability or tradability claim exists or is implied.
Every count quoted from round 9-12 probes, LT3/LT4 censuses, the cost model, the maker-rewards snapshot or the signal-engine
coverage note is a **counts-only development figure on worn data**. Every MDE here is a **planning estimate** built on stated
assumptions, not a measurement. Nothing here read a price after an origin, an outcome or a P&L. No host, network,
`data-dumps` or evidence-JSON read was used to write it; one code read (`research_lab/book_sweep.py`, the sweep's depth
definitions) fixed the meaning of the depth fields (section 1.2).

Source ideas: `CREATIVE_HYPOTHESES_2026-10-26.md` (round 12) section 3, ranks 1-6: **CH195** (resistance), **CH191** (grind at
the capture clock), **CH194** (the hour-held move), **CH197** (patient money), **CH193** (absorbed flow) and **CH192** (implied
against realised). Rank 7 (CH196) is a map first and ranks 8-11 (CH198-CH201) are engine-first; none is taken. The design is
written to round 12's rules (its section 0.1), to LT4's lessons L1-L15 and its R1/R2/census/freeze record (sections 14-19), to
LT5's R1, re-check and census-code-check rulings, and to LT6's R1 and re-check rulings. The design changes made here, all
before any data, are listed with reasons in section 6.1. The handles are the CH numbers themselves.

## 0. Summary

| Handle | Idea | Hypothesis (direction) | Population | Primary | Planning MDE (multiplier 3.47; at a quarter of the units) | Floor |
|---|---|---|---|---|---|---|
| **CH195** | resistance | Within a market, a 2 h move that went through **more pre-move depth on the side it hit** (sweep 1 of pass k - 1) persists more from capture k + 1 to k + 3, the unhit side's depth held fixed (one-sided, > 0) | non-sports ex-crypto movers (traded and quote-only), captures + sweep 1 of passes k - 1 and k | expanding-past demeaned OLS of `c_skip` on `zR` with `zR_away` in the model; block Freedman-Lane gate; **away-side falsification is a verdict condition** | 0.26c tercile (0.52c) | 0.5c (tercile) |
| **CH191** | grind at the capture clock | Within a market, a 6 h move made in **three same-signed 2 h steps** (grind) persists more from k + 1 to k + 3 than one made in **one step** (jump) (one-sided, > 0) | non-sports ex-crypto 6 h movers with three observed steps, captures only | expanding-past demeaned OLS of `c_skip` on 1[grind] over grind and jump units; plain Freedman-Lane gate | 0.25c (0.50c) | 0.5c |
| **CH194** | the hour-held move | Within a market, a 2 h move whose Gamma 1 h change shows it happened in the **first hour and held** persists more from k + 1 to k + 3 than one that happened **in the last hour** (one-sided, > 0) | non-sports ex-crypto 2 h movers with `chg_1h` present, captures only | expanding-past demeaned OLS of `c_skip` on 1[held] over held and fresh units; plain Freedman-Lane gate | 0.19c (0.37c) | 0.5c |
| **CH197** | patient money | Within a market, the YES mid change over the 22 h from capture k + 1 rises with the **behind-touch depth imbalance** of the outcome-0 book, the touch imbalance held fixed (one-sided, > 0) | non-sports ex-crypto two-sided books, **one unit per market per UTC day** at the 12:31Z pass | expanding-past demeaned OLS of `y22` on `zimbB` with `zimbT` a control; Freedman-Lane, market strata; **far-future falsification is a verdict condition** | 0.27c tercile (0.53c) | 0.5c (tercile) |
| **CH193** | absorbed flow | Within a market, among **traded non-movers** (Gamma 24 h volume rose, mid did not move), the next 2 h absolute mid move rises with the absorbed net volume (one-sided, > 0), **and more than it rises with the volume of the interval after the target** | non-sports ex-crypto markets with `volume24hr` at k - 1 and k, captures only | expanding-past demeaned OLS of `a = |mid_{k+1} - mid_k|` on `z log1p dV`; plain Freedman-Lane gate; **lead-minus-lag is a verdict condition** | 0.17c tercile (0.34c); F 0.29c | 0.5c (tercile of E|move|) |
| **CH192** | implied against realised | Within a market, the absolute mid move over (k + 1, k + 2] rises with the spread relative to the market's own 24 h realised volatility at k (one-sided, > 0), **and more than with the same ratio read at k + 3** | non-sports ex-crypto two-sided markets, **four units per market per UTC day** (00:31, 06:31, 12:31, 18:31Z), captures only | expanding-past demeaned OLS of `a_s = |mid_{k+2} - mid_{k+1}|` on `zivr`; block Freedman-Lane gate; **lead-minus-lag is a verdict condition** | 0.08c tercile (0.15c); F 0.24c | 0.5c (tercile of E|move|) |

- **Family:** one Holm family over the k surviving primaries, one-sided, familywise alpha 0.05, separate from E009-E011, LT2
  (E012-E014), LT3 (E015), LT4 (E020-E022), LT5, LT6, E025 and E026. **Provisional k <= 6.** A test whose census gate fails is
  dropped *before* registration, uncounted; k is the number that survive, fixed in the spec (`k_tests`) at registration and
  never changed. A primary that is unavailable or fails its gate enters Holm with p = 1.
- **Window (proposed):** whole captures with start in `[REGISTERED_UTC, END_UTC)`, 21 days, `REGISTERED_UTC =
  2026-12-08T00:00:00Z`, `END_UTC = 2026-12-29T00:00:00Z`; single analysis on or after **2026-12-30T12:00:00Z**. Keyed to LT6's
  `END_UTC` (proposed 2026-12-07, itself keyed to E022's) and sliding later with it (section 1.1).
- **Pin early, run late (round 12 rule 9).** The design text is frozen **before the earlier of 2026-11-15T12:00Z and `T_E015`**
  (planned by 2026-11-10), before any adjacent registered analysis can exist; CH195 is dropped uncounted if the freeze is not
  before `T_E022`, CH191 if it is not before `T_LT5` (section 1.1).
- **Expected outcome, declared now:** CH195 is the most likely to pass its census (E022's population is the one mover
  population that has passed the strata gate). **CH191 and CH197 are borderline** (CH191: count and quarter MDE; CH197:
  touch/behind correlation and two-day market recurrence). **CH194 is borderline** (the basis gate on Gamma's change fields).
  **CH193 and CH192 are likely to drop** (CH193: the `volume24hr` interval-timing semantic gate and the unprobed count of traded
  non-movers; CH192: the pooled liquidity correlation of a spread-built state and the falsification-feasibility gate, because
  spreads persist). Expected k is 3 or 4. Every taker check is expected to be "not shown" (section 1.10).

## 1. Common rules

### 1.0 Lessons carried over (binding from the first draft)

LT4's lessons **L1-L15** (`LIVE_TESTS_4.md` 1.0) apply unchanged: exact `%.17g` writes and round-trip reads; NaN refusals in a
pinned spec; sealed census inputs re-hashed (refuse on mismatch); a pessimistic planning-MDE gate in every census; a simulated
size check at >= 2,000 worlds with the limit 0.05 + 1.645 sqrt(0.0475 / worlds) = 0.058; dry-run guards; spec and code pins on
every frozen line; write-once per-capture series and status files; skip-slot targets where a bounce can sit at the origin;
clustering by event, event x UTC day and UTC day with p the largest; Holm over k counted once; economics never changes a
verdict; no both-class inclusion rule; readers at the pass cadence; an internal run lock. The later rulings are adopted from
the first draft:

| Source ruling | LT7 rule |
|---|---|
| LT4 R1 finding 2, R2 finding 10, re-check finding 2 | permutable-strata share printed by every census for market x UTC day and market x two-day block; day if >= 50%, else block2 if >= 50%, else the test fails; one `block_anchor` function for census and analysis |
| LT4 R1 finding 4, 17.3, 19 | a **residual-IQR** identification gate for every continuous state (the state's within-market IQR after its main controls), the raw IQR never computed as a gate |
| LT4 R1 findings 7-8, R2 finding 4 | Freedman-Lane gates only; `DE_gate = max(floor, 1 + (m_21 - 1) x 0.02)` with the floor declared per test |
| LT4 19 fix 1 | **the size check permutes within the strata the census fixed, through the same `strata_of` path as the registered gate**, on worlds carrying day and two-day block columns; the size check therefore runs after the censuses |
| LT4 19 freeze record | measured reader peak RSS 484-525 MB (one capture / six captures per run, `ulimit -v 1572864`), install by host cron, the queue draft never promoted while the cron line exists |
| LT5 R1 finding 2 | move-continuation targets start at the first capture after the decision time (`c_skip`, k + 1 to k + 3); 24 h targets from k + 1 (`y22`) |
| LT5 R1 finding 1, re-check 1 | rolling or persistent continuous states use the **block (circular-shift) Freedman-Lane gate**, minimum 16 shiftable units per market; per-interval labels and non-rolling states use the plain gate with binding Markov, MA and AR worlds |
| LT5 R1 ruling 11 | liquidity-tier gate `|corr(tested term, log1p liquidity_k)| <= 0.5`, within and pooled |
| LT5 census-code check 1, 3, 12, 13 | seal completeness and the seal's own slot assignment; MDE gates take `max(declared, design)`; the seal committed before any census |
| LT5 R1 finding 8, LT6 R1 item 11 | memory planned from a measurement (LT4's 484-525 MB and LT3's 534 MB), a declared ladder, each step dry-run measured; no pin on an unmeasured reader |
| LT6 R1 item 1 | where a contrasted class is sparse, the event t uses `G_treated - 1` df (here `G_minor - 1`, section 1.7) |
| LT6 R1 item 5 | every MDE gate carries `sqrt(max(1, VIF_w))`, `VIF_w` computed within market |
| LT6 R1 item 7, re-check R1 | every condition on another test's dates is keyed to that test's own registration and analysis times (`T_X` = the earlier of X's analysis job start, from the queue log, and X's analysis commit); the family slides later with them |
| LT6 R1 re-check R2 | the pinned crypto classifier (`fee_category` contains `crypto` after strip and casefold; unknown counted separately and treated as crypto) |
| LT6 1.6 / 14.6 | a **text freeze** is the real protection against adjacent looks; a later change to a test's text attaches the label that the freeze was meant to prevent |

Round 12's design rules (`CREATIVE_HYPOTHESES_2026-10-26.md` 0.1) map onto LT7 as follows:

| Round-12 rule | LT7 rule |
|---|---|
| 1. No trade-sample unit as a primary | every LT7 unit is a capture, sweep or sidecar unit; the trade samples are read only by CH193's census semantic gate (section 7) |
| 2. Effective counts, `DE_gate`, 1.5 factor, `sqrt(VIF_w)` | every census gate uses that formula (section 7); the multiplier is **3.47** for k <= 6 (section 1.9), not LT4's k = 5 value 3.388 |
| 3. No external frame | none is read |
| 4. No field of unknown semantics; signs from the capture's own move | `side` is read nowhere; Gamma's `chg_1h` (CH194) and `volume24hr` (CH193) each carry a **semantic census gate** before they may be a state; the sweep's depth fields are defined by AREPO's own code (1.2) |
| 5. A level-built state carries a mechanical-null falsification arm that is part of the verdict | **CH195, CH197, CH193, CH192** (book, volume and spread levels) carry a binding falsification condition F (1.9) and a binding mechanical-world size statement (1.8); CH191 and CH194 are built from price **changes**, so their far-future arms are reported labels (6.1, question 2) |
| 6. Event counts stated | every census prints events and the projected 21-day count |
| 7. Skip targets, daily units for 24 h, block gate for flow moderation | adopted (targets per test; CH197 one unit per market-day; CH192 thinned to four units per market-day) |
| 8. No capture-level constants | no venue clock or category-wide state; every state varies per market and per capture |
| 9. Pin early | the design-text freeze of 1.1 |

### 1.1 Registration, window, single analysis
- `REGISTERED_UTC` is the first 00:00Z that is **(a)** at least 24 h after the LT7 registration commit (spec pin plus ledger
  entry), **(b)** at least 24 h after **LT6's own `END_UTC`** if LT6 is registered (so no LT7 origin shares a capture with an
  LT6 origin, and every LT6 22 h target, which ends at most 24 h after LT6's last origin, is complete before LT7's first
  origin), **(c)** never earlier than 2026-12-08T00:00Z. LT7 registers only after LT5's and LT6's registration commits, or
  their recorded drops (all of their tests dropped at census or the family abandoned, in the ledger). The proposed value is
  **2026-12-08T00:00Z**; `END_UTC = REGISTERED_UTC + 21 d` = 2026-12-29T00:00Z; analysis date `END_UTC + 36 h` =
  2026-12-30T12:00Z. **The family slides later if LT6 slides**; the rule uses no data; a move is recorded in the ledger.
- **Design-text freeze (round 12 rule 9; LT6 1.6's protection).** After the challenger's acceptance (R1 and any re-check), a
  commit records the sha256 of this file in the ledger. From then on, the text of a test changes only by census-fixed values
  named in section 7 and by code-freeze-check fixes that change no state, unit, target, estimator, gate, threshold or verdict
  rule. **The freeze must exist before the earlier of 2026-11-15T12:00Z and `T_E015`** (planned by 2026-11-10). Adjacent
  analyses and the consequence if the freeze (or a later text change) is not before them:

  | Test | Adjacent analysis (`T_X`, the earlier of its analysis job start and its analysis commit) | Why adjacent | Consequence if the freeze or a text change is not before `T_X` |
  |---|---|---|---|
  | CH195 | E022 (`T_E022`, proposed 2026-11-17T12Z) | E022's model holds `log1p D_{k-1}` (pre-move total depth) and `dimb` on the same mover population and target family | **CH195 dropped uncounted** (as LT6 V) |
  | CH195 | LT6 V (`T_V`, proposed 2026-12-08T12Z) | V's placebo is the pre-move skew `v_prev`, the share form of CH195's hit-minus-away contrast with the **opposite** predicted sign | registration is before `T_V` by construction (it is at least 24 h before 12-08T00Z); if not, CH195 dropped |
  | CH191 | LT5 J (`T_LT5`, proposed 2026-11-21T12Z), if J registers | J estimates jump against grind at the print clock on `c_skip` | **CH191 dropped uncounted** |
  | CH191, CH194, CH193 | E015 (`T_E015`, proposed 2026-11-15T12Z) | E015's anatomy (traded against quote-only) is a control in all three; CH193's population is E015's complement | label *informed (E015)* |
  | CH197 | LT5 H, R (`T_LT5`), LT6 V (`T_V`) | daily-unit 24 h drift (H); 1c imbalance slopes (R); post-move 5c skew (V) | label *informed (LT5)*; `T_V` as CH195 |
  | CH192 | E011 (`T_E011`, analysis after 2026-11-11) | E011 reads moves against the market's own volatility | label *informed (E011)* |

- **Why the window starts on 2026-12-08.** (1) CH195's and CH197's book states share V's reader and population; LT6's window
  ends 12-07 and its targets by about 12-07T22:31Z, so an LT7 origin from 12-08T00:31Z shares no origin, state or target with
  LT6. (2) Host reader slots: LT6's reader stops as LT7's starts. (3) LT7 can be pinned in November, fresh, and run after every
  adjacent analysis has its own record. Disclosed: LT7's look-back reads raw capture and sweep files of 2026-12-01..12-07, which
  are LT6 origin and target inputs (CH192's 7-day realised volatility, CH191's three steps, every own 24 h change, CH195's
  k - 1 sweep of the 12-08T00:31Z pass); no LT6 store, origin, state or control is read.
- **Year end (disclosed).** The window spans Christmas (2026-12-24..26) and ends before New Year. December volumes may be lower
  than the October census days; a counts-only weekly line (`ops-stats`) is recorded, never a look. A sensitivity without
  origins in `[2026-12-24T00:00Z, 2026-12-27T00:00Z)` is reported and never changes a verdict.
- **Fixed end, no extension** (LT4-LT6 practice). Round 12 proposed a counts-gated 28-day extension; it is not adopted (one
  more degree of freedom). Shortfalls are labelled (*underpowered*, Unavailable), never extended.
- **One analysis**, once, on or after the analysis date (`run_live_tests7.py analyze` refuses before it; `--out` refuses to
  overwrite). No interim look at any outcome (1.6). **Effective start** = max(`REGISTERED_UTC`, the first capture processed
  by the reader at the pinned commit); the analysis keeps only lines whose `spec_sha` and `code_sha` equal the pins and whose
  role is `prospective_confirmation`.

### 1.2 Streams read (all already written by the host's pass; nothing new is fetched; no new collector)
- **Complete-universe captures** `snapshots/<id>/rows.csv.gz` (every 2 h at :31; `state=complete` only): LT3-LT6's columns
  (`bid`, `ask`, `spread`, `last_trade_price`, `volume24hr`, `liquidity`, `chg_1h/1d/1w`, `end_date`, `event_id`, `neg_risk`,
  `closed`, `active`, `received_utc`).
- **Sidecar** `rows_ext.csv.gz`: `fee_type`, `fee_category`, `series_slugs`, `order_price_min_tick_size`, `rewards_min_size`,
  `rewards_max_spread`, `clob_rewards`. A missing sidecar sets `sports = -1` and crypto unknown (excluded, counted).
- **Book sweep 1** `book_sweeps/<id>/` (`series_index` 0) of passes k - 1, k, k + 1, k + 3 (CH195) and of the 12:31Z pass of
  each day and the pass 13 slots later (CH197): outcome-0 `best_bid`, `best_ask`, `bid_size_1`, `ask_size_1`, `depth_*_1c`,
  `depth_*_5c`, `tick_size`, `book_timestamp`, `batch_receipt_utc`. **Field meaning (from `book_sweep.parse_book`):**
  `depth_bid_5c` is the summed size (shares) of all bid levels with price >= best bid - 0.05, inclusive, so it **includes the
  touch level**; `bid_size_1` is the size at the best level only; asks likewise. One token per market (LT4 17.3 disclosure 1).
- **Not read:** trade samples (except the census semantic gate of CH193, on sealed worn samples), the live large-trade
  monitor, `cross_venue_live/`, `surprise_live/`, the stores `live_tests2/` .. `live_tests6/`, CB8-H holders, the CB16-CB18,
  E025 and E026 stores, the keyless streams, the signal engine's `quotes/`, `features/`, `aux/` and `predictions/`, and Gamma
  outcome fields of any kind.

### 1.3 Clocks, slots and decision times
- **Slots:** as LT3-LT6 (`grid0 = 2026-10-01T00:31Z`, 2 h, tolerance 30 min, first complete capture of a slot). "k - j" and
  "k + h" are slots, not file order. A missing slot leaves every quantity that needs it NaN (counted), never interpolated.
- **Decision time per test** (the latest input's own receipt; states use that input and strictly earlier ones only):
  - **CH195:** sweep 1 of pass k (`batch_receipt_utc` of the outcome-0 token). The state reads sweep 1 of pass k - 1; the
    controls read capture k and sweep 1 of pass k. **The target starts at capture k + 1.**
  - **CH191, CH194:** capture k's row `received_utc`; states from captures k - 12 .. k. **Targets start at capture k + 1.**
  - **CH197:** sweep 1 of the 12:31Z pass (pass k); controls from captures k - 12 .. k. **The target starts at capture k + 1.**
  - **CH193:** capture k's row `received_utc`; the state is the change of Gamma's 24 h volume over `(t_{k-1}, t_k]`. The target
    starts at `mid_k`, the decision-time quote, because the state is not a move (round 12 rule 7) and the lag arm is its mirror
    image (section 5); the reasons and the k + 1 alternative are open question 6.
  - **CH192:** capture k's row `received_utc`; states from captures k - 84 .. k. **The target starts at capture k + 1.**
  - Gamma's own computation times of `chg_1h` and `volume24hr` are not published; the row's receipt is their latest possible
    availability. Their semantics are census-gated (section 7).
- **Late rule:** as LT4 1.3 (a frozen file is written before its earliest target slot can start, else `.late`, units lost and
  counted; *late-loss* above 2% of a test's origin files).

### 1.4 Shared origin-side eligibility
LT4 1.4 items 1-7, applied in order and counted (LT3's `move_join` and `classify`, imported): binary, open and active at k - 1
and k; two-sided and tight (spread <= 0.10) at both; `mid_k` in [0.02, 0.98]; as-of end unknown or > `t` + 3 h (> `t` + 27 h
for CH197's 24 h target); category by `cb17_census.is_sports_sidecar` on the sidecar of k (non-sports primaries; the sports arm
reported, uncounted); one row per `condition_id`. **Crypto:** every primary excludes crypto markets by the pinned classifier
(1.0), unknown counted and excluded; the crypto arm is reported, uncounted (6.1 item 7). Category is a spec parameter.
**Series-family rule (census-fixed):** if the census top series family holds > 40% of a test's primary population, it is
excluded from that primary (`<test>.exclude_family`; `""` = none) and the MDE gate recomputed. Move units: `x = mid_k -
mid_{k-1}`, `|x| >= 0.01`, LT3's class and geometry (traded, quote-only parallel, one-sided, spread-change, same-side-unequal,
never-traded, ambiguous) = **E015's anatomy label**, a control wherever a move exists.

### 1.5 Missing data and per-capture status (never imputed)
As LT4 1.5 and LT6 1.5: every frozen unit receives exactly one status at every target slot (`two_sided`, `one_sided`,
`closed_flag`, `absent`, `capture_missing`; sweep targets `two_sided`, `one_sided`, `absent`, `capture_missing`), write-once and
online; only `two_sided` has a target; skip targets use the **joint late mask** (both endpoints two-sided and in time). The
attrition rule (|a_1 - a_0| > 2 pp between the contrasted classes or the top and bottom terciles gives *attrition-differential*
and Lee-type bounds) never changes a verdict. A required input missing at the origin produces no unit and is counted
(`sidecar_missing`, `.nosweep`, `.noprevsweep`, `.noprev`, `lookback_missing`). A missing control or state is NaN (excluded,
counted), never 0. **Declared indicator-pair exceptions only:** an unknown `end_date` enters log hours-to-end as 0 with
`hte_unknown`; a missing Gamma `chg_1d` as 0 with its flag (except where `chg_1d` is part of a gate). A falsification state that
is missing (the lag slot or sweep absent) leaves the unit in the primary and out of the falsification arm (counted).

### 1.6 What is not looked at before the analysis date
No mid, move, target, P&L, regression or plot from `live_tests7/` files, or from in-window captures or sweeps, for these
hypotheses. Only `run_live_tests7.py ops-stats` may run (file, line, role, class and status counts; reads no price column,
enforced by a unit test). No change of thresholds, scales, populations, estimators or k after registration; operational fixes
are logged as deviations. E015's, E022's, LT5's and LT6's analyses (11-15 .. 12-08) arrive before LT7's window; they change
nothing in LT7 after the design-text freeze, and the freshness table of 1.1 decides their consequences. No LT7 designer, coder
or reviewer reads E022's, LT5's or LT6's analysis outputs before the design-text freeze.

### 1.7 Estimators and inference
- **Expanding-past demeaning** for all six primaries (J4-R; LT2-LT6): every regressor (the tested term and every control)
  minus the mean of the market's strictly earlier units of the same test; target raw; the first unit of each market drops.
- **Standard errors and p (L10):** CR1 on event (Gamma `event_id`, else the market), two-way event x UTC day of the origin,
  and UTC day. One-sided **p = max(p_event on t with `G_event - 1` df, p_two-way normal, p_day on t with `G_day - 1` df)**.
  **Sparse class (CH191, CH194):** the event t uses `min(G_event, G_minor) - 1` df, `G_minor` = the number of events holding
  at least one unit of the smaller contrasted class (LT6 R1 item 1's few-treated form). The conservative 95% CI is the hull of a
  2,000-draw event bootstrap and the three Wald intervals. Two-day blocks are a sensitivity (event x two-day block CR1) for
  every test and for CH197's 22 h target in particular.
- **Overlapping targets.** `c_skip` at consecutive origins overlaps by one pass (MA(2) in pass steps); CH191's labels at
  consecutive captures share two of three steps (strong label persistence); CH192's thinned units every 6 h do not overlap
  (target (k + 1, k + 2], next unit's target (k + 4, k + 5]); CH197's daily targets do not overlap; CH193's k-origin targets
  at consecutive non-mover captures share nothing. The size check carries the matching worlds (1.8).
- **Both-demeaned sensitivity** (LT6): every primary re-estimated with the target also expanding-past demeaned; reported only.

### 1.8 Gates (valid within-unit nulls) and their size
- **Plain Freedman-Lane gate** (LT4's `fl_perm_gate`, imported): after expanding-past demeaning, the target's residuals from
  the reduced model (target on the controls) are permuted within the census-fixed stratum and the full model refitted; 200
  draws; passes if `p_perm < 0.05`. Strata: market x UTC day if >= 50% of the test's units (for CH191 and CH194, of its
  **contrasted** units) sit in strata with >= 4 such units, else market x two-day block if >= 50%, else the test fails its census
  gate (`perm_stratum`). **CH197** (daily units) permutes within market (H's convention): the census gate is >= 50% of units in
  markets present on both census days. Used by CH191, CH194, CH193 (per-interval labels or per-interval states) and CH197.
- **Block (circular-shift) Freedman-Lane gate** (LT5's `block_fl_gate`, imported unchanged): within each market the
  reduced-model residual series (ordered by origin) is circularly shifted by an offset drawn from `[s_m, n_m - s_m]`, `s_m =
  max(4, ceil(n_m / 4))`, and the full model refitted; 200 draws; passes if `p_perm < 0.05`; markets with fewer than 16
  shiftable rows are excluded from the gate (counted). Used by **CH195** (a book level of unknown persistence; V's precedent)
  and **CH192** (a rolling state: `rv24` uses 12 slots, `rv7d` 84).
- A failed gate on data gives p = 1 in Holm and the label "SE check failed (gate on data)".
- **Size check (L5), after the censuses (k and `perm_stratum` fixed first).** `size-check` runs once, on the code to be pinned,
  2,000 worlds x 200 draws, seed **20261177**, limit 0.058. **Every gate scenario permutes within the strata the census fixed
  for the test it is binding for, through the same `strata_of` / `block_anchor` path as the analysis gate**, on worlds carrying
  a UTC-day and a two-day-block column (LT4 19 fix 1); a world is generated once and evaluated under each binding test's
  stratum. Scenarios (no effect of the tested term in every gate world):

  | # | Scenario (1.8.1) | Gate | Binding for | Statistic |
  |---|---|---|---|---|
  | 1 | binary iid label | FL | CH191, CH194 | gate rejection rate |
  | 2 | binary label, persistent market rates | FL | CH191, CH194 | gate |
  | 3 | binary label, control at correlation 0.7 with a real effect | FL | CH191, CH194 | gate |
  | 4 | binary Markov label (persistence 0.6), MA(2) target, unbalanced markets | FL | CH191, CH194 | gate |
  | 5 | as 4 with persistence 0.9 (CH191's labels share two of three steps) | FL | CH191, CH194 | gate |
  | 6 | continuous per-interval state iid, control at correlation 0.5 with a real effect, absolute target, unbalanced markets | FL | CH193 | gate |
  | 7 | daily-unit continuous state, day-to-day persistence 0.6, daily target from 12 pass shocks, control at correlation 0.5 with a real effect | FL (market) | CH197 | gate |
  | 8 | as 7 with persistence 0.9 (a farmer's ladder is the same every day) | FL (market) | CH197 | gate |
  | 9 | continuous state AR(1) rho 0, control at correlation 0.5 with a real effect, MA(2) target (LT6 scenario 8) | block FL | CH195 | gate |
  | 10 | as 9 with rho 0.6 | block FL | CH195, CH192 | gate |
  | 11 | as 9 with rho 0.9 | block FL | CH195, CH192 | gate |
  | 12 | as 9 with rho 0.95 (LT5 O's binding world) | block FL | CH192 | gate |
  | 13 | **mechanical world M-B:** total pre-move depth has a real continuation effect, equal on both sides; no hit-side effect | none | CH195 | verdict size |
  | 14 | **mechanical world M-C:** a slow trait drives the 22 h drift and is proxied symmetrically by `imbB` before and after the target | none | CH197 | verdict size |
  | 15 | **mechanical world M-D:** stochastic volatility proxied symmetrically by the interval volume before and after the target | none | CH193 | verdict size |
  | 16 | **mechanical world M-D':** as 15 with a persistent spread-like proxy, CH192's skip target and lag | none | CH192 | verdict size |

  **Verdict size** (scenarios 13-16; round 12 rule 5) = the share of worlds in which the test's analytic one-sided p (the 1.7
  rule) is < 0.05 **and** its falsification condition F (1.9) holds; the gate is omitted, which can only raise the rate
  (conservative and cheaper). It is the rate at which the verdict rule would call a purely mechanical relation Supported at
  single-test level. Criterion: <= 0.058 at 2,000 worlds, as for the gates.
- **Also reported, never binding:** a planted-effect power run per test (500 worlds each, effect 0.5c per SD or between
  classes, seeds `20261177 x 100 + 21 .. 26`), giving the power of gate, analytic p and F together; the far-future label
  rates of CH191 and CH194 in scenarios 4-5.
- **Consequence of a failure (declared now, as LT5/LT6):** a failing scenario makes **only the tests it is binding for** "SE
  check failed (size scenario)" (scenarios 1-12) or "SE check failed (mechanical world)" (13-16): p = 1 in Holm, **k
  unchanged**, no rerun, reseed, redesign or variant. `max_retries 1` covers a deterministic crash only (same code, seed,
  worlds and draws, no output written). No preliminary run of any scenario at seed 20261177 is made.

### 1.8.1 Simulated worlds (declared now; no census input)
Common unless stated: a market's target level `N(0, 0.01)`; unit `i` of a market has `t_row = 7,200 i` s, `day = i // 12`
(daily-unit worlds: `day = i`), `block2 = day // 2` from the same `block_anchor`; events of three markets; 200 draws per world
at a fresh sub-seed from one generator seeded 20261177, scenarios in table order; non-binding runs on generators derived as
`20261177 x 100 + n`.
- **1-3:** LT4's validated worlds (60 markets x 40 units): `sim_move_world` (class rate 0.3, noise SD 0.04); the same with
  market class rates `U(0.1, 0.6)`; `sim_corr_label_world` (label = 1[z > 0], z correlated 0.7 with `c1 ~ N(0, 1)`, `c1`
  effect 0.02).
- **4-5:** LT5 scenario 4's world (60 markets, `n_m` uniform on 6..60), label rate `p_m ~ U(0.15, 0.5)`, persistence 0.6 /
  0.9; pass shocks `u ~ N(0, 0.03)`; `y_i = level + u_{i+1} + u_{i+2} + 0.5 u_{i+3}`; `c1 ~ N(0, 1)`, no effect.
- **6:** 120 markets, `n_m` uniform on 12..120; state `z ~ N(0, 1)` iid; `c1 = 0.5 z + sqrt(0.75) xi`, real effect 0.005 on
  the target; target `y_i = level + |e_i|`, `e ~ N(0, 0.02)` (absolute, skewed); no effect of `z`.
- **7-8:** 200 markets, `n_m` (days) uniform on 6..21; state `z_d` = market level `N(0, 0.5)` + AR(1) across days (rho 0.6 /
  0.9), stationary SD 1; `c1 = 0.5 z + sqrt(0.75) xi` (`xi` AR(1) same rho), real effect 0.02; target `y_d = level + 0.02 c1_d
  + sum_{j=1..11} u_{d,j}`, `u ~ N(0, 0.017)` (22 h from 11 pass shocks); no effect of `z`.
- **9-12:** LT6 scenarios 8-10 exactly (80 markets, `n_m` uniform on 6..60, AR(1) state rho 0 / 0.6 / 0.9, plus rho 0.95 for
  12 with `n_m` uniform on 24..96, control effect 0.02, MA(2) target `u_{i+1} + u_{i+2} + 0.5 u_{i+3}`, `u ~ N(0, 0.03)`);
  block FL, minimum 16.
- **13 (M-B, CH195):** 80 markets, `n_m` uniform on 6..60; per unit the hit-side and away-side log depths `h_i = mu_m + f_i +
  eta_i`, `a_i = mu_m + f_i + xi_i`, `f` AR(1) rho 0.6 SD 1 (the market's time-varying depth), `eta`, `xi` iid `N(0, 0.7^2)`;
  target `y_i = level + 0.01 f_i + u_{i+1} + u_{i+2} + 0.5 u_{i+3}` (liquid moments continue more, equally whichever side was
  hit); model `y` on `z(h)`, `z(a)`; statistic: one-sided p of `z(h)` < 0.05 and F (Δ = beta_h - beta_a) holds.
- **14 (M-C, CH197):** 200 markets, `n_m` (days) uniform on 6..21; latent trait `g_d` AR(1) rho 0.8 SD 1; `imbB_d = 0.5 g_d +
  sqrt(0.75) e_d` (`e` AR(1) rho 0.6); `imbT_d = 0.5 imbB_d + sqrt(0.75) n_d`; target `y_d = level + 0.005 (g_d + g_{d+1}) +
  N(0, 0.06)` (the drift depends on the trait at the start and the end of the target alike); lag state `imbB_{d+1}`;
  statistic as 13 with Δ = beta(imbB_d) - beta(imbB_{d+1}) in the joint model.
- **15 (M-D, CH193):** 120 markets, `n_m` uniform on 24..120; log-volatility `s_t` AR(1) rho 0.95 stationary SD 0.5; pass
  shocks `u_t = 0.012 exp(s_t - 0.25) e_t` (mean variance at the base, LT6 re-check n1); interval volume proxy `z_t = 0.5
  s_t + sqrt(0.75) xi_t`; units are passes with `|u_t| < 0.005` (the non-mover selection); target `|u_{t+1}|`; lag state
  `z_{t+2}`; control `rv24` from the 12 previous simulated shocks; statistic as 13 with Δ = beta(z_t) - beta(z_{t+2}).
- **16 (M-D', CH192):** as 15 with `n_m` uniform on 120..252, spread proxy `z_t = 0.5 s_t + sqrt(0.75) xi_t`, `xi` AR(1) rho
  0.9; units every third pass; target `|u_{t+2}|`; lag state `z_{t+3}`; controls `log rv24` (12 previous shocks) and `log
  rv7d` (84 previous); statistic as 13.

### 1.9 Verdicts, the falsification condition and labels (per primary, after Holm over k)
- **Falsification condition F (CH195, CH197, CH193, CH192; round 12 rule 5; part of the verdict).** The **arm model** is the
  primary model with the test's falsification state added (CH195: the away-side depth, already in the primary model; CH197:
  `zimbB` read at slot k + 13; CH193: `z log1p dV` of the interval (k + 1, k + 2]; CH192: `zivr_lag`, the spread at k + 3 over
  `rv24_k`), fitted on the primary's units that have the falsification state, with the same demeaning, controls and clustering.
  `Δ = beta_tested - beta_falsification` in the arm model, its SE from the arm model's clustered covariance. **F holds iff (i)
  Δ's one-sided p < 0.05 under the 1.7 p = max rule (not Holm-adjusted; counted 0) and (ii) Δ̂ >= 0.5 x betâ_primary.** The
  falsification states are built with the same census centre and scale as the tested state, so Δ is in the primary's units.
  F is computed once, at the analysis; an arm with fewer than 50% of the primary's units is *falsification unavailable*.
- **Supported (exploratory, prospective):** Holm-adjusted one-sided p < 0.05, estimate in the predicted direction, gate passed,
  **and, for the four level-built tests, F holds.** If everything else holds and F fails or is unavailable: **Inconclusive**
  with the label *mechanical null not excluded* (or *falsification unavailable*); Holm p is not changed.
- **Contradicted:** the conservative 95% CI lies entirely on the other side of 0. **Inconclusive:** otherwise.
  **Unavailable:** below the test's floor counts (fewer than 20,000 units, fewer than 300 events, or fewer than 10 UTC days with
  units).
- **Labels (never change a verdict):** *material* (CH195, CH197, CH193, CH192: the top-minus-bottom tercile contrast of the
  tested state >= 0.5c, on the primary's target; CH191, CH194: the class contrast >= 0.5c); *regime, not shape* (CH191, CH194:
  the far-future arm, 2.x, fails the F rule; reported only); *capture-quote specific* (CH195, CH191, CH194: Supported and the
  sweep-mid reading M1 below 50% of the primary or one-sided p >= 0.05); *informed (X)* (1.1); *analytic p oversized in
  simulation* (the planted-power run's null twin, if computed, above its limit); *underpowered* (Inconclusive and `(t_{G-1,
  1-0.05/k} + t_{G-1, 0.8}) x SE_day` above the census MDE); *attrition-differential*; *late-loss*; *sweep-missing* (`.nosweep`
  or `.noprevsweep` > 2% of origin passes); *series-concentrated* (one series family > 50% of a primary's units after the
  census rule); *holiday-sensitive* (the Christmas-excluded estimate changes sign); the per-test mechanism labels.
- **MDE multiplier.** `3.47 = t_{20, 1 - 0.05/6} + t_{20, 0.8}` (about 2.61 + 0.86; computed exactly in code and pinned), the
  provisional k = 6 value; LT4-LT6's 3.388 is the k = 5 value and would be slightly lenient for k = 6. For a smaller census k the
  multiplier is not lowered (conservative).

### 1.10 Economics (separate; never changes a verdict)
- Paper taker round trip per share at the recorded touches (sweep 1 of the entry pass and of the exit pass), fees on both legs
  from the origin sidecar (`economics.fee_spec`, `resolve_rate(..., "max_if_unknown")`), LT3's `paper_taker` and `econ`
  (event-clustered mean, one-sided p, >= 30 trades in >= 10 events). No depth, queue or latency: optimistic.
- **Hurdles (`cost-model-v1`, `COST_MODEL.md`, development calibration 2026-10-16..19):** $100 taker round trip about 2.9c at
  >= $100k Gamma liquidity, 3.9c at $10k-100k, 7.2c at $1k-10k; a 5-share touch round trip about 4.5c. A passive touch order
  fills about 3.1% of the time within an hour and loses about 2.38c to adverse selection against a 2 h mark (about 0.39c at
  >= $100k). Makers are about break-even before rewards (non-sports fill-weighted -0.37c).
- **Maker routes** (the primary money route for every test): signed tests report the gross favourable-cell move per liquidity
  tier, "gross, no fills", beside the 0.39c adverse-selection figure; the magnitude tests (CH193, CH192) report the gross
  absolute move avoided by stepping aside in the top tercile against the bottom, beside the 0.39c and 2.38c figures.
- **Declared in advance:** every AREPO taker cost check has failed (E004, E007; 0 of 95 economic cells positive). "Not shown"
  is the expected outcome for every taker cell. No resolution, hold-to-resolution or reward income is computed (no outcome
  field is read).

### 1.11 Overlaps, dependence, embargo shadows and counting
- **Within LT7:** CH191 and CH194 both read movers (6 h and 2 h; a unit can be in both); CH195 and CH194 share 2 h movers;
  CH197 and CH192 read every two-sided book; CH193's non-movers are disjoint from the mover tests at the same capture. All in
  one Holm family; never counted as independent confirmations. Pairwise unit-overlap shares and, on shared units, the
  within-market correlations of the tested terms are printed by the censuses and reported at analysis.
- **Against registered or drafted tests (no double count; no shared origin):**

  | LT7 | Closest prior | Same data? | Same contrast? | Why not a double count |
  |---|---|---|---|---|
  | CH195 | **E022** (LT4, registered or about to be; hollowness after the move; controls `log1p D_{k-1}` (pre-move total depth) and `dimb`) | the same population family (traded non-sports movers), sweeps, sweep targets | no: E022's state is post-move hollowness; its `log1p D_{k-1}` control is the **sum** of CH195's two sides | disjoint windows (E022 to 11-16); design-text freeze before `T_E022` or CH195 dropped (1.1); `book` and `hollow` tokens; E022's `zh` is a CH195 control |
  | CH195 | **LT6 V** (CH190; window to 12-07; analysis 12-08) | **the same population** (movers with both sweeps) and reader shape | **close:** V's control and placebo `v_prev = sign(x) imb_{k-1}` (5c, shares) is the share form of CH195's hit-minus-away contrast, with V's placebo label reading the **opposite** sign; V's tested term (post-move skew) is not in CH195 | no shared origin (LT7 from 12-08T00:31Z, V's last target sweep about 12-07T04:31Z); CH195 is registered before `T_V` (1.1); `v_prev` is a reported sensitivity control, not a primary control (6.1 item 4); `book` token to LT7's date |
  | CH195 | E003 (complete, exploratory) | historical books | no | unconditional imbalance at minutes |
  | CH191 | **LT5 J** (CH180, jump or grind at the print clock; window 10-30..11-20) | no (trade samples against captures) | **the same question on another clock**, with the opposite expected sign | declared heir if J drops at its census; design-text freeze before `T_LT5` or CH191 dropped (1.1); disjoint windows |
  | CH191, CH194 | E021 (LT4; age of the move; dropped at census, never registered) | samples | the CH194 question on the sample clock | never registered; nothing to double count |
  | CH191, CH194, CH193 | **E015** (LT3, registered; traded against quote-only movers, 2 h `c`; window to 11-14) | captures | no: anatomy is a control here | disjoint windows; *informed (E015)* rule of 1.1; `movetype` token |
  | CH193 | E015's complement (traded non-movers are not E015 units) | captures | no | as above |
  | CH197 | **LT5 H** (24 h daily units; high-water mark), **LT5 R** (1c imbalance slope at the reward cutoff), **LT6 V** (post-move 5c skew), E003 | captures, sweeps | no: CH197's term is the behind-touch imbalance given the touch imbalance, on all books | disjoint windows; *informed (LT5)* rule; `book` token |
  | CH192 | **E011** (surprise detector; window to 11-10) | captures | no: E011's state is a move scaled by volatility; CH192's is the spread scaled by volatility | disjoint windows; *informed (E011)* rule; new `ivr` token |
  | all | E009/E010 (cross-venue), E025, E026 (copy skilled wallets; frozen modules to 12-07) | no | no | different streams; nothing of E026 is imported |

- **Signal-engine shadows (disclosed; section 9).** CH195 and CH197 can be learned by a book-isolating LightGBM that sees the 1c
  and 5c depths per side and the own 2 h change; CH193 by a `movetype`-isolating one (traded flag and the own 2 h change);
  CH192 by any model combining spread with realised volatility; CH191 and CH194 by the **champion** (`se1_lgbm_mm`: market
  state and momentum, including `chg_1h` and lagged changes), which §8 of DESIGN_V1 never embargoes. The champion's aggregate
  log-loss is not a look at a held/fresh or grind/jump contrast; LT7 asks that no attribution of the champion on those
  constructs be computed or shown before LT7's analysis (section 9).
- **Collection overlap (disclosed):** the signal engine and every earlier test read the same captures and sweeps; LT7's window
  overlaps no registered or drafted test's window. No store is opened by another test; no pooling.
- **Counting (M3):** the analysis adds **k counted tests**, one per surviving primary, kind `live_tests7`
  (`battery2.KIND_RULES["live_tests7"]`, fail-closed). Gate draws, F, secondaries, mechanism readings, placebos, economics,
  censuses and the size check count 0. The cumulative count is recorded at registration and at analysis.

### 1.12 Stop rules
As LT6 1.12: no interim look; the test runs to `END_UTC` whatever the counts; after 7 days, a test whose units run below one
third of its census projection (counts only) gets the ledger note "likely Unavailable" and nothing else changes; any change to
a pinned file after the pin makes the analysis refuse (a fix needs a new spec, new E-numbers and a new window); the reader
exits 75 when nothing is new; a failed reader is re-promoted within 48 h; gaps stay missing and are counted; disk: the reader
refuses above 3.0 GB in `live_tests7/` and no retention rule may cover `live_tests7/` before the analysis is committed;
collection of a kind is switched off when its test is not in `k_tests`.

## 2. CH195: resistance (the pre-move depth on the side the move hit)

- **Hypothesis and mechanism.** Kyle's lambda is the price change per dollar of flow; its inverse is the depth the move had to
  consume. A 2 h move that went through a deep resting book on the side it hit either consumed a wall (a taker with conviction)
  or followed a wall withdrawn and re-quoted (a maker's decision); both carry information. The same move through a thin book is
  a small order or a quote re-centring. **Direction: beta(zR) > 0, one-sided, with the away side held fixed.** Who would be
  wrong: the trait reading, in which "deep books continue" only because liquid moments bounce less, whichever side was hit; the
  away side's depth then predicts equally, and F fails.
- **Unit and population.** Non-sports ex-crypto market x pass k that is a mover at capture k (1.4, `|x| >= 0.01`; traded and
  quote-only, anatomy controlled), with sweep 1 of **both** pass k - 1 and pass k two-sided on the outcome-0 token, tight
  (sweep spread <= 0.10), with both 5c depths present at both; `mid_k` in [0.07, 0.93] (the 5c band is not truncated by the
  boundary); **sweep move agreeing in sign:** `sign(smid_k - smid_{k-1}) = sign(x)` (so the hit side is the side the measured
  move consumed; disagreements counted); pass k at or after `REGISTERED_UTC` with its k - 1 inputs after LT6's `END_UTC` + 24 h
  (automatic under 1.1).
- **State (frozen; decision time = sweep 1 of pass k).** Hit side = asks for a rise, bids for a fall (outcome-0 book). Taker
  notional of the 5c band at pass k - 1: `D_hit = depth_hit_5c x touch_hit` (shares times the hit side's touch price at k - 1,
  E022's notional convention), `D_away` likewise on the other side; `R = log1p D_hit`, `R_away = log1p D_away`; `zR`, `zR_away`
  with **one** census centre and scale (pooled over both sides) so their coefficients are comparable. Also frozen: E022's
  `h0 = clip(1 - D0_notional_k / liquidity_k, 0, 1)` on the outcome-0 book of pass k (LT6 V's declared form), `v_prev` (LT6 V's
  definition, sensitivity only), anatomy, `book_timestamp` of both passes.
- **Target (exact).** `c_skip = sign(x) x (mid_{k+3} - mid_{k+1})` (capture mids; joint mask). M1: the sweep skip `c_vskip =
  sign(x) x (smid_{k+3} - smid_{k+1})`. M2 (reported): `c = sign(x) x (mid_{k+1} - mid_k)`.
- **Primary statistic.** Expanding-past demeaned OLS of `c_skip` on `zR` **and `zR_away`**, controls: anatomy dummies (traded,
  parallel, one-sided, spread-change; same-side-unequal the base), `log |x|`, sweep spread at k - 1 and k, `zh0`, logit
  `mid_k`, `|mid_k - 0.5|`, `log1p volume24hr_{k-1}`, `log1p liquidity_k`, own 24 h change `sign(x) x (mid_k - mid_{k-12})`
  (+ flag), 1[tick = 0.001], log hours-to-end (+ flag). Tested coefficient: `zR`. Inference 1.7; seed 20261171. Gate: block FL
  (scenarios 9-11), seed 20261271.
- **Falsification (binding, F).** In the same model, Δ = beta(zR) - beta(zR_away) (1.9). Under the trait reading the two are
  equal. Scenario 13 (M-B) is CH195's verdict-size statement.
- **Mechanism readings.** M1 (*capture-quote specific* label, 1.9); M2 (the first interval; reported); M3 the traded and
  quote-only arms (a quote-only move through a deep book is a wall withdrawn, a traded one a wall consumed; reported).
- **Secondaries (reported).** S1 the 1c depths in place of 5c; S2 the primary with `v_prev` added as a control (V's form; the
  collinearity with the contrast is printed); S3 the 6 h Gamma-mid target from k + 1; S4 the sports and crypto arms; S5 the
  top-minus-bottom tercile contrast of `zR` (the material reading); S6 counts by tercile, anatomy and tick.
- **Planning MDE (estimate).** About 18,500 non-sports movers a day (P1/P1b), of which both-sweep covered, in band, sign-agreeing
  and ex-crypto planning 13,000 (low) a day: 273,000 in 21 days; `n_eff` 80% = 218,000; SD 5c; `DE_gate` 3.0; `VIF_w` 1.5:
  `3.47 x 5c / sqrt(218,000) x sqrt(3) x 1.5 x sqrt(1.5) x 2.2` = **0.26c** at the tercile gap; at a quarter of the units
  **0.52c** (borderline). **F's MDE** (Δ, the two sides correlated at r within market): about `MDE x sqrt(2 / (1 - r))` =
  0.52c at r = 0.5.
- **Floors (Unavailable):** < 20,000 units, < 300 events, < 10 days.
- **Economics.** (a) Reported taker follow of top-tercile `zR` moves with `|x| >= 0.03` in >= $100k markets, entry at the
  sweep-1 touch of pass k + 1, exit at pass k + 3, against 2.9c. (b) Maker: after a top-tercile move post on the move's side,
  after a bottom-tercile move re-post at the pre-move level; gross `c_skip` by tercile, "gross, no fills".
- **Missing data.** `.noprevsweep`, `.nosweep`, outcome-0 token absent, one-sided, depth missing, touch price missing at k - 1,
  sign disagreement: excluded, counted separately.

## 3. CH191: grind at the capture clock

- **Hypothesis and mechanism.** A 6 h move made of three same-signed 2 h steps has been re-priced three times by makers who
  could have faded it and did not: information still diffusing (Hong and Stein 1999). The same move made in one step and two
  flat ones is a jump already absorbed or a quote re-centring whose bounce (E004/E006) is not yet out. At the print clock
  (LT5 J) a one-step move is a wall breaking and is expected to continue; at the capture clock the round expects the opposite.
  **Direction: E[c_skip | grind] - E[c_skip | jump] > 0, one-sided.**
- **Unit and population.** Non-sports ex-crypto market x capture k with the three steps `s_j = mid_{k-j+1} - mid_{k-j}` (j = 1,
  2, 3) all observed (slots k - 3 .. k complete and the market two-sided and tight at each), `x6 = s_1 + s_2 + s_3`, `|x6| >=
  0.02` **and** `|x6| >= 3` ticks (sidecar tick at k), `mid_k` in [0.05, 0.95], 1.4 items 1-7 at k - 1 and k.
- **State (frozen; decision time = capture k).** `pc = max_j |s_j| / sum_j |s_j|`, `sa = |x6| / sum_j |s_j|`. **Grind** = `sa
  >= 0.9` and `pc <= 0.5`; **jump** = `pc >= 0.8`; other (zigzag `sa < 0.6`, the rest) reported, not contrasted. Also frozen:
  the jump's position (j of the largest step), the last step's anatomy (LT3's `classify` on `s_1` if `|s_1| >= 0.01`, else
  "small last step"), the own 24 h change.
- **Target.** `c_skip = sign(x6) x (mid_{k+3} - mid_{k+1})`; M1 the sweep skip; M2 `c = sign(x6) x (mid_{k+1} - mid_k)` (the
  bounce lives there); S 24 h `sign(x6) x (mid_{k+12} - mid_{k+1})`.
- **Primary statistic.** Expanding-past demeaned OLS of `c_skip` on 1[grind] over grind and jump units, controls: last-step
  anatomy dummies, `log |x6|`, spread at k, logit `mid_k`, `|mid_k - 0.5|`, `log1p volume24hr_k`, own 24 h change `sign(x6) x
  (mid_k - mid_{k-12})` (+ flag), `log rv24_k` (1.8 of section 7's definition), 1[tick = 0.001], log hours-to-end (+ flag).
  Inference 1.7 with the `G_minor` df; seed 20261172. Gate: plain FL (scenarios 1-5), seed 20261272.
- **Far-future arm (reported label, not a verdict condition).** The class of the three steps from slot k + 4 to k + 7 (one slot
  after the target ends, the mirror of the past path's one-slot gap), with the same rules; arm model = primary + 1[grind'] +
  1[other'] (+ missing flag); if F's rule fails, label *regime, not shape*. **Why not binding:** CH191's state is built from
  price changes, not levels; under the hypothesis itself (diffusing information is a persistent drift) the later path's shape
  is a symmetric proxy of the same drift, so a time-symmetric arm would falsify the mechanism, not a mechanical artefact
  (question 2). The mechanical threats to a path label are the bounce (the skip target; M2), tick coarseness (the 3-tick rule
  and tick control) and the Gamma quote (M1).
- **Secondaries.** S1 jump at the last step against earlier jumps (reported); S2 `|x6| >= 3c` subset; S3 the sports and crypto
  arms; S4 counts by class, jump position and anatomy.
- **Planning MDE (estimate).** 6 h movers planning 1,500-3,000 a capture (unprobed; bounded by P1b's 2,750 2 h movers an
  interval); at the low end 380,000 in 21 days, jump 30% and grind 25%, effective 80%: `n_1` 91,200, `n_2` 76,000; SD 5c;
  `DE_gate` 3.0; `VIF_w` 1.3: `3.47 x 5c x sqrt(1/91,200 + 1/76,000) x sqrt(3) x 1.5 x sqrt(1.3)` = **0.25c**; at a quarter
  **0.50c** (at the floor). Ex-crypto and the 3-tick rule may cut the count; the census decides.
- **Floors:** < 20,000 contrasted units, < 300 events, < 10 days.
- **Economics.** Taker follow of grinds with `|x6| >= 0.03` in >= $100k markets (entry sweep-1 touch of pass k + 1, exit pass
  k + 3) against 2.9c, reported. Maker: after a jump, re-post at the pre-move level for one pass (gross M2 for jumps); after a
  grind, do not fade (gross `c_skip` for grinds); "gross, no fills".
- **Declared relation to LT5 J.** If J drops at its census, CH191 is its capture-clock heir by declaration, not a redraw of J.
  If J registers, both run on disjoint windows and different clocks; nothing is pooled.

## 4. CH194: the hour-held move

- **Hypothesis and mechanism.** Makers see every order. If a mid that moved in the first hour of the interval still stands at
  the capture, the makers who could have re-centred it back chose not to (a Glosten-Milgrom update accepted); a move made in
  the last hour has not yet been tested and carries its bounce (E004). **Direction: E[c_skip | held] - E[c_skip | fresh] > 0,
  one-sided.**
- **Unit and population.** Non-sports ex-crypto 2 h mover at capture k (1.4, `|x| >= 0.01`) with Gamma `chg_1h` present at k.
- **State (frozen; decision time = capture k).** `f = chg_1h / x` (the share of the 2 h move made in the last hour, on Gamma's
  clock and basis). **Held** = `f` in [-0.25, 0.25]; **fresh** = `f` in [0.75, 1.25]; reverting (`f < -0.25` or `> 1.25`)
  and middling reported, not contrasted. Gamma's change fields are read only if CH194's basis gate passes (section 7).
- **Target.** `c_skip = sign(x) x (mid_{k+3} - mid_{k+1})`; M1 sweep skip; M2 `c` from k; S 24 h.
- **Primary statistic.** Expanding-past demeaned OLS of `c_skip` on 1[held] over held and fresh units, controls: anatomy
  dummies, `log |x|`, spread at k, logit `mid_k`, `|mid_k - 0.5|`, `log1p volume24hr_k`, own 24 h change (+ flag), `log rv24_k`,
  1[tick = 0.001], log hours-to-end (+ flag). Inference 1.7 with the `G_minor` df; seed 20261173. Gate: plain FL (scenarios
  1-5), seed 20261273.
- **Far-future arm (reported label).** The timing class of the move of interval (k + 4, k + 5] (`x' = mid_{k+5} - mid_{k+4}`
  with `|x'| >= 0.01`, `f' = chg_1h_{k+5} / x'`); reasons as CH191.
- **Secondaries.** S1 traded and quote-only arms; S2 `|x| >= 3c`; S3 sports and crypto arms; S4 counts by class and anatomy.
- **Planning MDE (estimate).** About 2,750 non-sports movers an interval (P1b) x 12 x `chg_1h` presence (planning 80%,
  unprobed) = about 26,000 a day, 550,000 in 21 days; held and fresh 35% each (unprobed), effective 80%: 154,000 each; SD 5c;
  `DE_gate` 3.0; `VIF_w` 1.3: `3.47 x 5c x sqrt(2/154,000) x sqrt(3) x 1.5 x sqrt(1.3)` = **0.19c**; at a quarter **0.37c**.
- **Floors:** < 20,000 contrasted units, < 300 events, < 10 days.
- **Economics.** Taker follow of held moves with `|x| >= 0.03` in >= $100k markets against 2.9c, reported. Maker: after a fresh
  move re-post toward the pre-move level for one pass (gross M2 for fresh); after a held move quote at the new level.
- **Disclosed.** The engine's momentum family already holds `chg_1h` and the own 2 h change, so the champion can learn the
  combination (1.11; section 9).

## 5. CH197: patient money (the book behind the touch)

- **Hypothesis and mechanism.** Orders at the touch compete for the next print; orders resting behind it, up to 5c away, wait
  for a better price and are willing to wait (Rosu 2009's patient traders); Cao, Hansch and Wang (2009) find the book beyond the
  touch informative beyond the touch. The patient side's tilt predicts the next day's drift with the touch held fixed.
  **Direction: beta(zimbB) > 0 on the YES mid, one-sided.** Who would be wrong: the trait reading (a slow market-level drift
  that the book reflects before and after alike; F) and the reward-ladder reading (farmers' symmetric ladders behind the touch;
  rewarded controls and arm).
- **Unit and population.** Non-sports ex-crypto two-sided market x UTC day, **at the 12:31Z pass** (capture k of slot 12:31Z
  and sweep 1 of that pass), with `bid_size_1`, `ask_size_1`, both 5c depths present and positive on the outcome-0 book, `mid_k`
  in [0.07, 0.93], sweep spread <= 0.05, 1.4 items 1-7 at k - 1 and k, as-of end > `t_k` + 27 h. A missing 12:31Z capture or
  sweep gives no unit that day (counted). The slot is fixed now (section 6.1 item 5).
- **State (frozen; decision time = sweep 1 of pass k).** Touch sizes `bT = bid_size_1`, `aT = ask_size_1`; behind-touch depth
  `bB = depth_bid_5c - bT`, `aB = depth_ask_5c - aT` (shares; the 5c band includes the touch, 1.2); **`imbT = (bT - aT) / (bT +
  aT)`**, **`imbB = (bB - aB) / (bB + aB)`** (both toward outcome 0 = YES; `bB + aB = 0` excluded, counted); `dis = imbB -
  imbT` (reported); `zimbB`, `zimbT` with census scales.
- **Target.** `y22 = mid_{k+12} - mid_{k+1}` (YES mid, capture k + 1 = 14:31Z to the next day's 12:31Z; joint mask). Mirror M1
  (reported, mechanical at short horizons): `y2 = mid_{k+1} - mid_k` on `zimbT`. S: the 2 h slope `y2` on `zimbB`.
- **Primary statistic.** Expanding-past demeaned OLS of `y22` on `zimbB`, controls: `zimbT`, `log1p` total 5c depth (both
  sides), `zh0` (E022's form on pass k), sweep spread, logit `mid_k`, `|mid_k - 0.5|`, `log1p volume24hr_k`, own 24 h change
  `mid_k - mid_{k-12}` (+ flag), `rewarded` (sidecar `clob_rewards` parsed, LT5 R's parser; unparseable excluded, counted),
  `in_band` (folded mid in the one-sided scoring band [0.10, 0.90] and spread <= `rewards_max_spread`), 1[tick = 0.001], log
  hours-to-end. Inference 1.7 (two-day block sensitivity); seed 20261174. Gate: plain FL within market (scenarios 7-8), seed
  20261274.
- **Falsification (binding, F).** Arm model = primary + `zimbB_lag`, the same imbalance read at sweep 1 of the pass at slot
  k + 13 (14:31Z the next day: one slot after the target ends, the mirror of the lead's one-slot gap before the target starts);
  Δ = beta(zimbB) - beta(zimbB_lag) (1.9). Scenario 14 (M-C) is CH197's verdict-size statement. Disclosed: a move during the
  target reshapes the later book, which biases beta(zimbB_lag) upward when the patient side wins, so F is conservative.
- **Reported placebo (label).** The fake split: the whole-band imbalance `imb5 = (B5 - A5) / (B5 + A5)` in place of `imbB`; if
  its one-sided p < 0.05 and its tercile contrast is at least that of `imbB`, label *total-band imbalance, not the split*.
- **Secondaries.** S1 rewarded against unrewarded books; S2 the `dis` tercile contrast; S3 sports and crypto arms; S4 the 1c
  band form of the touch (`depth_*_1c`) in place of the best level; S5 counts by tercile, reward status and tick.
- **Planning MDE (estimate).** About 40,000 eligible books a capture (98% book coverage, DESIGN_V1), non-sports ex-crypto
  planning 30,000 daily units a day (derived, unprobed), 630,000 in 21 days, effective 80% = 504,000; SD 6c; `DE_gate` 5.0;
  `VIF_w` 1.5: `3.47 x 6c / sqrt(504,000) x sqrt(5) x 1.5 x sqrt(1.5) x 2.2` = **0.27c**; at a quarter **0.53c** (borderline).
  F's MDE at r = 0.6: about 0.60c.
- **Floors:** < 20,000 units, < 300 events, < 10 days.
- **Economics.** Taker: buy the patient side when `dis` is in its top tercile in >= $100k markets, entry at sweep 1 of pass
  k + 1, exit at sweep 1 of pass k + 12, against 2.9c, reported. Maker: lean with the patient side for the day; gross `y22` by
  tercile, "gross, no fills".

## 6. CH193: absorbed flow, and CH192: implied against realised (the two magnitude tests)

### 6.A CH193: absorbed flow
- **Hypothesis and mechanism.** An interval in which Gamma's 24 h volume rose but the mid did not move is flow that a resting
  wall absorbed (Rosu 2009). Absorbed volume is pent-up pressure: the next interval's absolute move is larger. Plain
  volume-volatility clustering (Karpoff 1987) predicts a symmetric relation in time; the claim is the asymmetry: volume
  absorbed **before** the target predicts its absolute move more than volume traded **after** it. **Direction: beta(z log1p dV)
  > 0, one-sided, and F.**
- **Unit and population.** Non-sports ex-crypto market x capture k, 1.4 items 1-7 at k - 1 and k, `volume24hr` present at
  k - 1 and k, **`dV = volume24hr_k - volume24hr_{k-1} > max($10, 1e-4 x volume24hr_{k-1})`** (net new 24 h volume above the
  engine's movetype tolerance), **`|x| < 0.005`** (no mid move). `dV` is a lower bound on the interval's traded notional
  (Gamma's 24 h sum also rolls off the volume of 24 h earlier; disclosed). The semantic gate of section 7 must pass before `dV`
  may be read as the interval's trading.
- **State (frozen; decision time = capture k).** `z log1p dV` (census scale). Also frozen for secondaries: the wall class from
  sweep 1 of pass k (touch size on the side the last print hit, `last_trade_price` equal to the bid or ask at k; **small** if
  <= 2 x `rewards_min_size`, else 2 x `min_order_size` if unrewarded; unassigned counted), sweep depth and `h0`.
- **Target.** `a = |mid_{k+1} - mid_k|` (the k-origin; the state is not a move); S1 `P(a >= 0.01)`; S2 `a_skip = |mid_{k+3}
  - mid_{k+1}|`; S3 the sweep-to-sweep `|smid_{k+1} - smid_k|` with the sweep controls (`log1p D0_k`, `zh0`), decision time
  sweep 1 of pass k.
- **Primary statistic.** Expanding-past demeaned OLS of `a` on `z log1p dV`, controls (capture-side only, so the decision time
  stays at capture k): `log rv24_k`, spread at k, logit `mid_k`, `|mid_k - 0.5|`, `log1p volume24hr_{k-1}`, `log1p liquidity_k`,
  own 24 h change magnitude `|mid_k - mid_{k-12}|` (+ flag), 1[last trade present], 1[tick = 0.001], log hours-to-end (+ flag).
  Inference 1.7; seed 20261175. Gate: plain FL (scenario 6), seed 20261275.
- **Falsification (binding, F; the lag arm).** Arm model = primary + `z log1p dV_lag`, `dV_lag = volume24hr_{k+2} -
  volume24hr_{k+1}` (the interval (k + 1, k + 2], adjacent to the target's end as the lead interval is adjacent to its start;
  the same scale; a negative or missing `dV_lag` enters as `log1p(max(dV_lag, 0))` with a flag). Δ = beta(lead) - beta(lag)
  (1.9). Scenario 15 (M-D) is CH193's verdict-size statement. Disclosed: the lead is selected on no move and the lag interval is
  unrestricted, and a large target move draws reaction volume after it; both raise the lag slope, so F is conservative.
- **Secondaries (reported).** The small-wall interaction `z log1p dV x 1[small wall]` (material label if its tercile-gap point
  estimate >= 0.5c); the signed secondary (the next move's sign agrees with the last print's touch side in the small-wall
  class); S1-S3 above; sports and crypto arms.
- **Planning MDE (estimate).** `volume24hr` present on 22% of rows (DESIGN_V1 16): about 9,000-11,000 of the eligible a
  capture; traded non-movers among them planning 10-20%, **unprobed**: 900-1,800 a capture, 230,000-460,000 in 21 days;
  effective 80% at the low end = 184,000; SD of `a` 3c; `DE_gate` 3.0; `VIF_w` 1.5: `3.47 x 3c / sqrt(184,000) x sqrt(3) x 1.5
  x sqrt(1.5) x 2.2` = **0.17c**; at a quarter **0.34c**; F's MDE at r = 0.3: about 0.29c (quarter 0.58c).
- **Floors:** < 20,000 units, < 300 events, < 10 days.
- **Economics.** Maker: while a small wall on one side absorbs flow, step aside on that side for one pass; gross `a` avoided in
  the top tercile against the bottom, beside 0.39c and 2.38c, "gross, no fills". Taker: none counted; the signed secondary's
  join-the-absorbed-side rule in >= $100k markets after `dV >= $5k` is reported against 2.9c.

### 6.B CH192: implied against realised
- **Hypothesis and mechanism.** A maker's half-spread is her price for the option she writes to informed takers; she sets it
  from what she expects, not from what has happened. The spread relative to the market's own realised volatility is the venue's
  implied-to-realised ratio; where it is high, the makers price more uncertainty than the path has shown, and the next
  interval's absolute move is larger. **Direction: beta(zivr) > 0, one-sided, and F.** Disclosed plainly: with `log rv24` a
  control, the coefficient on `ivr` equals the coefficient on `log spread_k`; the test's distinct content is the
  **lead-minus-lag** asymmetry and the within-market design, not the ratio's algebra.
- **Unit and population.** Non-sports ex-crypto two-sided tight market x capture k at the slots **00:31, 06:31, 12:31 and
  18:31Z** (four units per market per UTC day; thinning declared now: a slow state, less overlap, a bounded analysis),
  1.4 items 1-7 at k - 1 and k; `rv24_k` defined (at least 10 of the 12 two-hour mid changes k - 11 .. k observed) and `rv7d_k`
  defined (at least 60 of 84).
- **State (frozen; decision time = capture k).** `rv24_k = sqrt(mean of the squared observed 2 h mid changes over k - 11 ..
  k)`, floored at half a tick (`rv24* = max(rv24, 0.5 x tick)`, flag `rv_floor`); `rv7d_k` likewise over 84 changes;
  `spread_k = ask_k - bid_k` (capture quotes); **`ivr = log(spread_k / rv24*_k)`**; `zivr` with census scale. **Lag state:**
  `ivr_lag = log(spread_{k+3} / rv24*_k)` (the spread one slot after the target ends over the **same** pre-target volatility,
  so the lag never contains the target step).
- **Target.** `a_s = |mid_{k+2} - mid_{k+1}|` (the interval (k + 1, k + 2], starting at the first capture after the decision);
  S1 `P(a_s >= 0.01)`; S2 the 6 h `|mid_{k+4} - mid_{k+1}|`; M2 (reported) `|mid_{k+1} - mid_k|`, which carries the spread's
  own lag-0 mechanics (6.1 item 1).
- **Primary statistic.** Expanding-past demeaned OLS of `a_s` on `zivr`, controls: `log rv24*_k`, `rv_floor`, `log rv7d_k`,
  `log1p liquidity_k`, logit `mid_k`, `|mid_k - 0.5|`, `log1p volume24hr_k`, 1[spread_k = tick], 1[tick = 0.001], anatomy at k
  (mover classes, else non-mover), `rewarded`, `in_band`, log hours-to-end (+ flag). Inference 1.7; seed 20261176. Gate: block
  FL (scenarios 10-12), seed 20261276.
- **Falsification (binding, F; the lag arm).** Arm model = primary + `zivr_lag`; Δ = beta(zivr) - beta(zivr_lag) (1.9). The lead
  sits 1.5 slots before the target's midpoint and the lag 1.5 slots after it, so a time-reversible spread-volatility process
  gives Δ = 0; a large target move widens later spreads, which raises the lag slope (conservative). Scenario 16 (M-D') is
  CH192's verdict-size statement.
- **Secondaries.** S1-S2 above; S3 rewarded against unrewarded; S4 sports and crypto arms; S5 counts by tercile, tick floor and
  `rv_floor`.
- **Planning MDE (estimate).** Non-sports ex-crypto two-sided eligible planning 30,000 a capture (derived); four slots a day:
  2,520,000 units in 21 days, effective 80% = 2,016,000; SD of `a_s` 3c (pessimistic for the whole panel); `DE_gate` 5.0 (slow
  state); `VIF_w` 2.0: `3.47 x 3c / sqrt(2,016,000) x sqrt(5) x 1.5 x sqrt(2) x 2.2` = **0.08c**; at a quarter **0.15c**; F's
  MDE at r = 0.8: about 0.24c. Powered many times over; the census's job is the confounder and feasibility gates.
- **Floors:** < 20,000 units, < 300 events, < 10 days.
- **Economics.** Maker: do not post inside a book whose `ivr` is in the market's top tercile; gross `a_s` avoided, top against
  bottom tercile, beside 0.39c and 2.38c, "gross, no fills". Taker: none.

## 6.1 Design changes to the round-12 sketches (made before any data; each needs the challenger's acceptance)

1. **CH192's target and lag.** The round's `a = |mid_{k+1} - mid_k|` with a far-future `ivr` has two defects: a wide spread at
   k makes `mid_k` itself noisier, a lag-0 mechanical link to `|mid_{k+1} - mid_k|` that no later spread has; and the round's
   far-future ratio uses the realised volatility of a window that contains the target step. LT7 uses the skip interval
   (k + 1, k + 2] with the lead at k and the lag at k + 3 (symmetric about the target), both over `rv24*_k`. CH192 is thinned to
   four slots a day and `rv24` is floored at half a tick with a flag (otherwise every market static for 24 h drops out).
2. **CH193's primary is capture-only.** The round's wall class needs sweep 1 of pass k, after `mid_k`, so a sweep-based state
   with a k-origin target would let the target start before the decision time (LT4 E022's leakage fix). The wall class and the
   sweep controls move to secondaries; with them go the round's small-wall share gate and the last-print requirement. A
   **semantic gate** on `volume24hr`'s interval timing is added (round 12 rule 4).
3. **CH194's basis gate** is made exact: Gamma's change fields must be on the capture-mid basis (section 7), else CH194 drops.
4. **CH195: `v_prev` is not a primary control.** In logs, `R - R_away` is the pre-move skew whose share form is LT6 V's
   `v_prev`; with both sides and `v_prev` in one model the contrast that F tests would be identified only by the difference
   between a log ratio and a share ratio. `v_prev` is a reported sensitivity (S2) and its correlation with the contrast is
   printed. Added: the sweep sign-agreement rule, notional depths (E022's convention), one common scale for both sides, and the
   liquidity gate applied to the contrast `zR - zR_away` (a depth level is correlated with Gamma's `liquidity` by construction,
   LT4 17.3's L/D quantiles; the contrast is what the verdict rests on).
5. **CH197:** the impatient side is the **best-level size**, not the 1c band (at a 0.01 tick the 1c band holds two levels, at
   0.001 eleven; the best level is tick-invariant); the 1c form is S4. The daily slot is **12:31Z**, fixed now; the reason is a
   file-availability fact (the 00:31Z slot is missing on 2026-10-21 in the sealed census days, LT5 16 host check), not any
   value. The round's min-size share gate is dropped: stored sweeps hold per-band sums, not per-order sizes, so it is not
   computable (rule 4). The far-future arm is binding (F) and the fake split a reported label.
6. **CH191, CH194: the far-future arms are reported labels**, not verdict conditions (sections 3, 4; question 2), and their
   future windows start one slot after the target (k + 4), the mirror of the past window's gap.
7. **Every primary is ex-crypto** (the round asked for ex-crypto where a series family exceeds 50%): crypto up/down ladders
   follow an external reference price, so their path shape, book and spread are set by a different mechanism, and they are a
   large share of mover populations. Declared before any count; the crypto arm is reported; universe completeness is unchanged
   (the arm is collected and reported).
8. **Multiplier 3.47** (k = 6) in every MDE gate; **F-feasibility gates** (section 7); **no 28-day extension**.
9. **F's rule** (Δ one-sided p < 0.05 and Δ̂ >= 0.5 x betâ) in place of the round's two forms (CH195: the away slope's upper
   bound below the primary minus the MDE; CH192/CH193: lead minus lag >= the MDE); one rule for four tests, with a census
   feasibility gate on F's own MDE (question 1).

### 6.2 Ideas not taken into LT7
- **CH196** (last-print anchor): a map first (about 470 units a capture, E020's recurrence class); an E015 moderator after
  E015's analysis commit. Not proposed.
- **CH198-CH201** (theta, resolution-source class, sweep-2 news, reward yield): engine-first families on `res_7d` or `dir_2h`;
  section 9 states none of their tokens.
- Round 12 section 4's rejections stand (trade-sample units, laggards, Amihud, symmetric volume-volatility, venue clocks,
  external frames, rule edits, wallets, tick-rule signing, maker mark-outs, moderators of E015/E022/LT5/LT6 inside their
  windows, resolution-level primaries, taker primaries).

### 6.3 Census drops
None yet. Census drops will be recorded here, with their counts, before the pin.

## 7. Pre-registration censuses (counts only; before registration; worn pre-window data; no target read)

Each census runs once, reads origin-side fields only (no target, no P&L; the only later-slot quantities read are other units'
own origin-side states, for the F-feasibility correlations, never paired into a target; question 12), prints counts, and is
committed with its sha256 before the registration commit. **Every gate threshold below is stated now, before any census.** A
failed gate drops that test before registration (uncounted); `k_tests` lists the survivors. **Input identity:** the census
refuses unless every input file it opens is named in the LT7 seal with an equal sha256, and refuses if a sealed file in a
needed slot is absent (LT5 census-code check 1, 12).

**Inputs (all started before 2026-10-22T00:00Z, before the LT2-LT7 windows; sealed worn days, reused).**
- **CC7 (captures: CH191, CH194, CH193, CH192):** the complete captures (rows, sidecar, manifest) sealed in
  `seals/lt5_census_inputs_captures.json` (captures 2026-10-12T00:31Z .. 10-21T22:31Z; **sha256 to be filled from the committed
  seal**; known missing slots 10-14T00:31..10:31, 10-21T00:31 and 02:31, left missing). Origins: CH191, CH194, CH193 every
  complete slot of 2026-10-15..10-21 whose look-back (k - 3, k - 12) lies in the span; CH192 the four declared slots of
  2026-10-19..10-21 (84-slot look-back from 10-12; `rv7d` NaN below 60 observed changes).
- **CS7 (sweeps: CH195, CH197):** the same seal's sweep 1 from 2026-10-19T22:31Z: CH195 every pass of 2026-10-20 and 10-21 with
  its k - 1 sweep (LT6 CV's days); CH197 the 12:31Z passes of 10-20 and 10-21 (and, for the F-feasibility correlation only, the
  14:31Z sweep of 10-21).
- **CV7 (CH193's semantic gate):** the **23 sealed active-frame samples of 2026-10-16/17** (`seals/lt3_census_inputs_C2.json`)
  with their captures from `seals/lt4_census_inputs_captures.json`.
- **Fallback (LT6 R1 item 9's rule):** fewer sealed slots: use exactly those (the rest genuinely missing, counted); no LT5 seal:
  q0600 hashes the same spans from the data releases' `files.sha256`; slots outside the named spans are never read; no other day
  is substituted. **Minimum covered days** (covered complete slots / 12): CC7 >= 5 (CH192 >= 2), CS7 >= 1.5 for CH195 and
  both 12:31Z passes for CH197, CV7 >= 1.5 sample-days. Below its minimum, every gate of that census is NaN and fails.
- **The LT7 seal.** A restore job copies the needed files byte for byte from the releases and checks every sha256 against the
  source seals; `seals/lt7_census_inputs.json` lists exactly the restored files with equal hashes and the seal's own slot
  assignment; it is committed before any LT7 census runs.
- **Header pre-check** (before the census code is frozen; a header read, no rows): the sealed sweeps carry `bid_size_1`,
  `ask_size_1`, `depth_*_5c`, `tick_size`; the sidecars carry `rewards_min_size`, `rewards_max_spread`, `clob_rewards`; the rows
  carry `chg_1h`, `chg_1d`, `volume24hr`. A missing field makes the dependent gate NaN (that test drops).

**Projection** = census count x 21 / covered days (an estimate; CH192 counts its four slots a day). Distinct events: `E_2d +
(E_2d - E_day1) x 19` for two-day censuses, else distinct events over the covered days x 21 / days. **Effective counts** = units
in markets with >= 2 units of the test's population in the census days (CH197: markets present on both days). **Design
effect:** `DE_gate = max(floor, 1 + (m_21 - 1) x 0.02)`, `m_21` the projected size-weighted mean cluster size by event;
floors 3.0 (CH195, CH191, CH194, CH193), 5.0 (CH197 daily, CH192 slow). **MDE gate formulas (multiplier 3.47):** class (CH191,
CH194) `3.47 x SD x sqrt(1/n1_eff + 1/n2_eff) x sqrt(DE_gate) x 1.5 x sqrt(max(1, VIF_w))`; slope at the census tercile gap
(CH195, CH197, CH193, CH192) `3.47 x SD / sqrt(n_eff) x sqrt(DE_gate) x 1.5 x sqrt(max(1, VIF_w)) x gap`, with **`max(declared,
design)`** (LT5 census-code check 3). `VIF_w` = within-market (expanding-past demeaned) VIF of the tested term on the primary's
controls; a NaN fails. **F-feasibility (four level-built tests):** `r_w` = the within-market correlation of the tested and
falsification states on census units that have both; **F-MDE** = the design-based MDE of Δ in the arm model, with
`max(declared, design)` where the declared form is `MDE x sqrt(2 / (1 - max(0, r_w)))`. Correlations marked "within" are on
expanding-past-demeaned values and bind; pooled values are printed. SDs: `c_skip` 5c, `y22` 6c, `a` and `a_s` 3c.

| Test | Census | Gate (all must hold; NaN fails) | Values fixed into the spec |
|---|---|---|---|
| CH195 | CS7 | both-sweep coverage (two-sided outcome-0 sweeps at k - 1 and k, both 5c depths, touch prices) >= 70% of non-sports ex-crypto movers in band; sweep sign agreement >= 70% of covered movers; projected units (all section 2 filters) >= 42,000 (>= 2,000 a day); **residual IQR:** within-market IQR of the residual of `R` after an OLS on `R_away` >= 0.25 (log units) in >= 50% of markets with >= 6 units, and >= 30 such markets; within `|corr(zR, zR_away)|` <= 0.8; within `|corr(zR - zR_away, zh0)|`, `|corr(zR - zR_away, z log|x|)|`, `|corr(zR - zR_away, 1[traded])|` each <= 0.5; `|corr(zR - zR_away, log1p liquidity_k)|` <= 0.5 within and pooled; block-gate share >= 50% of units in markets with >= 2 units; **slope MDE <= 0.5c**; **F-MDE <= 1.0c** | common centre and scale of `R`/`R_away`; `zR` tercile cuts and gap; `exclude_family` |
| CH191 | CC7 | projected 6 h movers (all section 3 filters) >= 201,600 (>= 800 a capture); grind >= 15% and jump >= 15% of them; within `|corr(1[grind], 1[traded last step])|`, `|corr(1[grind], z signed own 24 h change)|`, `|corr(1[grind], z log|x6|)|` each <= 0.5; `|corr(1[grind], log1p liquidity_k)|` <= 0.5 within and pooled; permutable share of contrasted units >= 50% (day, else block2); **class MDE <= 0.5c** | `perm_stratum`, `exclude_family` |
| CH194 | CC7 | `chg_1h` present for >= 50% of non-sports ex-crypto movers; **basis gate:** among movers with `mid_{k-12}` and `chg_1d` present, the share with `|chg_1d - (mid_k - mid_{k-12})| <= 0.01` >= 70% **and** greater than the share with `|chg_1d - (ltp_k - ltp_{k-12})| <= 0.01` among those with both last trades present (else the fields are not on the mid basis); the share of movers with `|chg_1h| > |x| + 0.01` <= 20%; held >= 20% and fresh >= 20% of movers with `chg_1h`; within `|corr(1[held], 1[quote-only parallel])|`, `|corr(1[held], 1[traded])|`, `|corr(1[held], z log|x|)|` each <= 0.5; liquidity gate within and pooled; permutable share of contrasted units >= 50%; **class MDE <= 0.5c** | `perm_stratum`, `exclude_family` |
| CH197 | CS7 | covered share (all section 5 filters except the market-day) >= 60% of non-sports ex-crypto books in band; projected daily units >= 210,000 (>= 10,000 a day); within `|corr(imbT, imbB)|` <= 0.5; share of markets present on both days with `|imbB_d2 - imbB_d1| >= 0.1` >= 50%; market-strata share (units in markets present on both days) >= 50%; within `|corr(zimbB, z own 24 h change)|` <= 0.5; `|corr(zimbB, log1p liquidity_k)|` <= 0.5 within and pooled; **slope MDE <= 0.5c** (`DE_gate` floor 5.0); **F-MDE <= 1.0c** (`r_w` from the 10-20 units with a 10-21T14:31Z sweep) and within `|corr(imbB_k, imbB_{k+13})|` <= 0.8 | `zimbB`, `zimbT` centres and scales; `zimbB` cuts and gap; `exclude_family` |
| CH193 | CC7 + CV7 | **semantic gate (CV7):** among sampled non-sports traded intervals with complete page coverage of `(t_{k-1}, t_k]` and sample notional > $10, the share with `dV` above the tolerance >= 70%, **and** among sampled markets with complete coverage and no print in the interval, the share with `dV` above the tolerance <= 30%; `volume24hr` present at k - 1 and k for >= 15% of eligible non-sports ex-crypto rows; projected traded non-movers >= 100,800 (>= 400 a capture); within-market IQR of `log1p dV` >= 0.5 in >= 50% of markets with >= 6 units (and >= 30 markets); within `|corr(z log1p dV, z log1p volume24hr_{k-1})|`, `|corr(z log1p dV, z log rv24)|` each <= 0.5; liquidity gate within and pooled; permutable share >= 50%; **slope MDE <= 0.5c**; **F-MDE <= 1.0c** and within `|corr(dV_k, dV_{k+2})|` <= 0.8 | `z log1p dV` centre and scale, cuts and gap; `perm_stratum`; `exclude_family` |
| CH192 | CC7 | projected units >= 210,000 (>= 10,000 a day); `rv_floor` share <= 50%; **residual IQR:** within-market IQR of the residual of `ivr` after an OLS on `log rv24*` and `log rv7d` >= 0.15 in >= 50% of markets with >= 8 units (and >= 30 markets); within `|corr(zivr, z log rv24*)|` <= 0.7; `|corr(zivr, log1p liquidity_k)|` <= 0.5 within and pooled; block-gate share >= 50% of units in markets with >= 2 units; **slope MDE <= 0.5c** (`DE_gate` floor 5.0); **F-MDE <= 1.0c** and within `|corr(ivr_k, ivr_lag)|` <= 0.8 | `zivr` centre and scale, cuts and gap; `exclude_family` |

- **Descriptive (no gate):** every census prints the sports and crypto splits, the top series family's share, the events and the
  projected 21-day events, the pairwise unit overlap with the other LT7 populations and with LT6 V's and LT5 J's population
  definitions on the same days, class or tercile shares by liquidity tier, the per-market unit sums, and the computed DE beside
  `DE_gate`. CH195: the distribution of `R`, `R_away`, the within corr of `zR - zR_away` with `v_prev`, anatomy shares. CH191:
  `pc`, `sa` distributions, jump positions, the lag-7 within-market label autocorrelation (the far-future label's persistence).
  CH194: the `f` distribution, the basis-error quantiles, the share with `chg_1h = 0` by anatomy. CH197: `imbT`, `imbB`, `dis`
  distributions, rewarded share by tercile, the 1c-band form's correlation with the best-level form. CH193: `dV` quantiles, the
  roll-off (negative `dV`) share, wall-class and last-print assignability shares. CH192: `ivr` quantiles, the tick-floor share,
  rewarded share by tercile.
- **Order (cheapest kill first):** CV7 (CH193's semantics), then CC7 (CH194's basis gate first), then CS7. A test whose census
  fails has its reader kind switched off before the reader's code freeze.
- **Expected census fates (declared now).** CH195 likely passes (E022's 18,517 covered traded movers in two days and its 0.599
  block2 share are its floor). CH191 is borderline on the count (unprobed) and the quarter MDE. CH194 is borderline on the basis
  gate. CH197 is borderline on `|corr(imbT, imbB)|` (shared quoters) and two-day recurrence. **CH193 is likely to drop** (the
  semantic gate is the first test of `volume24hr`'s interval timing; 78% of rows lack the field; the non-mover count is
  unprobed). **CH192 is likely to drop** (a spread-built state's pooled correlation with Gamma liquidity, and spread persistence
  at 6 h against the 0.8 feasibility cap).

**Census jobs (to be drafted later under `docs/research_lab/queue/drafts/` in README format; ids from q0600 upward, each
checked unused across `queue/` on every local and remote branch before drafting; none is written in this commit).**
- `q0600_lt7_census_restore` (lane `net`, about 600 MB): restore the source-sealed files of the spans above from the data
  releases, check each sha256 against the three source seals, write the restore report.
- `q0601_lt7_seal` (lane `net`, about 300 MB; after q0600): `run_live_tests7.py seal` writes `lt7_census_inputs.json` (the
  orchestrator commits it).
- `q0602_lt7_census_volsem` (cpu, about 1,000 MB, **exclusive**; after the seal commit): CV7.
- `q0603_lt7_census_captures` (cpu, about 1,500 MB, **exclusive**; after q0602): CC7.
- `q0604_lt7_census_sweeps` (cpu, about 1,200 MB, **exclusive**; after q0603): CS7.
- `q0605_lt7_size_check` (cpu, about 800 MB; after q0602-q0604 and the census values committed, so k and the strata are fixed
  before any size result exists; `max_retries 1` deterministic-crash only).
- `q0606_lt7_reader` (fallback only, never promoted while the cron line of 8.2 exists).
- `q0607_lt7_analysis` (cpu, about 3,000 MB, **exclusive**, `not_before` the analysis date).
All are DRAFT and must not be promoted before the challenger review, the design-text freeze, the code and its freeze check, and
**never while LT5's or LT6's census or size-check jobs are running** (memory-heavy-jobs rule; `depends_on` LT6's q0584 or its
recorded drop). Each counts 0.

## 8. Implementation plan (no code in this commit)

### 8.1 Modules to be written (engineering list)
- **Reuse by import, unmodified** (L7; LT4's precedent), with every imported module's normalised sha256 in LT7's `code_sha256`:
  from `live_tests3`: slot and capture scanners, `series_frame`, `move_join`, `classify`, `category_cols`, `outcome_h/s`,
  `status_codes`, `is_late`, `token0_map`, `project_events`; from `live_tests3_analysis`: `fit`, `verdict`, `attach`,
  `underpowered`, `attrition`, `lee_bounds`, `paper_taker`, `econ`, `gross`; from `live_tests4`: `block_anchor`, `strata_of`,
  `perm_share`, `de_gate`, the E022 sweep frame and `h` helpers; from `live_tests4_analysis`: `fl_perm_gate`, the LT4 worlds; from
  `live_tests5_analysis`: `block_fl_gate`, the LT5 worlds, LT5 R's reward parser (via `maker_rewards.parse_daily_rate`); from
  `bounce_decomp`: `holm`, `expanding_demean`; plus `cb17_census.py`, `economics.py`, `panel.py` as hashed dependencies. **No
  frozen or registered module is edited** (`live_tests3*`, `live_tests4*`, `live_tests5*`, `bounce_decomp`; nothing of E026).
  **Pre-declared consequence:** a change to any imported module after LT7's pin makes LT7 lines unmatchable and LT7 *void*
  (all primaries Unavailable, recorded), never re-pinned on the same window. At registration the ledger records these modules
  as frozen until LT7's analysis date (new behaviour in new files, as E026's frozen set). Vendoring (LT5/LT6's pattern) is the
  alternative (question 9).
- `backend/astrolabe/research_lab/live_tests7.py`: the reader and unit builders (`resist_units`, `path_units7`, `held_units`,
  `patient_units`, `absorbed_units`, `ivr_units`), the falsification-state builders, `rv` from the reader's own series, and the
  counts-only censuses (`census_captures`, `census_sweeps`, `census_volsem`). `run_once()` (internal non-blocking flock on
  `live_tests7/run.lock`) finds new complete captures and their pass's sweep 1 and writes, write-once (`%.17g`, atomic hard
  link): `series/<capture>.csv.gz` and `status/<capture>.csv.gz` (compact: market, event, series key, bid, ask, `volume24hr`,
  `liquidity`, `chg_1h`, `chg_1d`, `last_trade_price`, `end_date`, tick, reward fields, sports and crypto flags, receipt);
  `sweeps/<pass>.csv.gz` (outcome-0 sweep-1 quote, touch sizes, 1c and 5c depths, `book_timestamp`, receipt); a rebuildable
  mid-only cache `midcache/<capture>.parquet` for the 84-slot look-back (never a source of frozen values that the series files
  cannot reproduce); frozen units `<kind>/frozen/<id>.csv.gz` for kinds `resist`, `path`, `held`, `patient`, `absorbed`, `ivr`
  (with `.nosweep`, `.noprevsweep`); outcomes `<kind>/outcomes/<id>.h<j>.csv.gz` and `.s<j>.csv.gz` at the target and
  falsification slots (capture k + 1, k + 2, k + 3, k + 5, k + 7, k + 12; sweeps of passes k + 1, k + 3, k + 12, k + 13); and
  `passes.jsonl`. **Look-back:** at install time `t` in `[REGISTERED_UTC - 72 h, REGISTERED_UTC - 24 h]`, `backfill-series`
  writes `series/`, `sweeps/` and `midcache/` as `lookback` lines for every needed slot from `REGISTERED_UTC - 7 d - 2 h` that
  started before `t` (host originals, captures retained 8 days); the installed reader writes `lookback` lines for everything
  arriving in `[t, REGISTERED_UTC)`; `lookback` lines are never units; a needed slot found by neither is `lookback_missing`
  (counted), never imputed.
- `backend/astrolabe/research_lab/live_tests7_analysis.py`: the single analysis (1.7-1.10, the arm models and F, Holm over k,
  counting) and the size check (1.8, 1.8.1) with the scenario-to-test map (fail-closed on an unknown or missing scenario), the
  gates reading `perm_stratum` from the spec through `strata_of`.
- `backend/scripts/run_live_tests7.py`: `run`, `backfill-series`, `ops-stats`, `seal`, `census-volsem`, `census-captures`,
  `census-sweeps`, `size-check`, `analyze`; censuses accept `--data-dumps-cap-gb` and exit 75 above it; `size-check` refuses
  `--worlds/--draws` without `--dev`; `analyze` refuses before the date, an unpinned, null or NaN spec, or a `k_tests` naming a
  dropped test.
- Spec `backend/astrolabe/research_lab/model_specs/live_tests7_v1.json`: every constant, k, seeds (estimators 20261171-76, gates
  20261271-76, size check 20261177 and its derived seeds), dates, `T_X` rules, census scales, cuts and rules, the crypto
  classifier, the multiplier, the F rule, the `code_sha256` map and the imported sports-rule hash.
- `battery2.KIND_RULES["live_tests7"]` (fail-closed counting entry).

### 8.2 Resources, collection plan and install
- **No new collector and no network.** A pure reader of the pass's own outputs, once a pass.
- **Memory (measured references, then a ladder).** LT4's measured host dry run (`LIVE_TESTS_4.md` 19): **484 MB** peak for one
  capture per run, **525 MB** for six captures in one run; LT3's 534 MB backlog peak. LT7 reads per pass two captures' selected
  columns, a sidecar, two sweeps' outcome-0 rows (65,771 rows each), the 84-slot mid cache (about 50,000 markets x 84 x 16 B,
  about 70 MB) and its targets' quotes. **Planning: peak 550-750 MB in a backlog pass, 400-550 MB steady (estimates).** Ladder,
  each step measured by a host dry run with the exact install command before the pin (no pin on an unmeasured reader):
  1. one reader, `--max-items 2`, column projection, under `ulimit -v 1572864`: accepted if peak RSS <= 800 MB;
  2. else **two readers** (capture-side: CH191, CH194, CH193, CH192; sweep-side: CH195, CH197) serialised by one shared `flock`,
     each `--max-items 2`, accepted if each peaks <= 800 MB;
  3. else no pin and LT7 is not registered (recorded; no further variant).
- **Install route: host cron** (LT4's route, `LIVE_TESTS_4.md` 9.2 and 19): `55 1-23/2 * * *` (84 min after each even-hour
  :31 pass start, after LT6's `:45` line, 36 min before the next slot, which is the earliest freeze deadline), own `flock`,
  `nice -n 19`, `oom_score_adj 1000`, `ulimit -v 1572864`. The queue draft q0606 is the fallback, **never both**. A pass whose
  sweep is not complete at its freeze deadline loses its CH195 and CH197 units as `.late` (counted); its `series/` and
  `sweeps/` lines are still written (write-once) so the next pass's k - 1 inputs survive.
- **Concurrency.** LT6's reader runs until its last targets (about 12-08); LT7's from install (12-05..12-07) for look-back. Two
  readers overlap for about three days, offset by 10 minutes and each under its own flock; peaks are additive at most about
  1.5 GB on the host (planning does not assume the 2 OCPU / 12 GB resize; it holds with it).
- **CPU:** about 1-3 min a steady pass (estimate). **Disk:** about 1.5-2.5 GB over the window (CH192's 2.5 million thinned
  units dominate); the reader stops writing at 3.0 GB in `live_tests7/`.
- **Analysis job:** about 5 million unit rows across six tests; CH192's block gate refits 200 times on about 2.5 million rows;
  planning 2-3 GB peak, **exclusive**, single run.
- **Host change:** installing the cron line is a host change under the standing collection authorisation, done by the
  orchestrator.

### 8.3 Tests to be written (`backend/tests/unit/test_research_lab_live_tests7.py`, synthetic only)
- CH195: hit and away sides for rises and falls; notional from the k - 1 touch; the sign-agreement rule; both-sweep and
  in-band requirements; the common scale; Δ from one fit.
- CH191: steps, `pc`, `sa`, classes at their edges, the 3-tick rule, a missing step slot gives no unit; the future path at
  k + 4 .. k + 7.
- CH194: `f` classes at the edges; the basis gate's two shares; `chg_1h` missing gives no unit.
- CH197: `imbT`, `imbB` from best-level sizes and 5c bands (touch inside the band, 1.2); `bB + aB = 0` excluded; the 12:31Z slot
  only; the lag at k + 13.
- CH193: `dV` and the tolerance; a negative `dV` is no unit; `|x| < 0.005`; the lag `dV` at (k + 1, k + 2]; the semantic gate's
  page-coverage rule.
- CH192: `rv24*` with the half-tick floor and the 10-of-12 rule; `rv7d` 60-of-84; thinning slots; `ivr_lag` uses `rv24*_k`.
- Shared: causality (future captures and sweeps with wild prices leave every frozen line byte-identical); late refusal,
  write-once, dry-run guard, `%.17g` round trip, run lock; `ops-stats` reads no price column; imported-module hashes and the
  void rule; counting equals k; Holm; the p = max rule and the `G_minor` df; F's two conditions and the Inconclusive mapping;
  the analysis refusals; the design-freeze and `T_X` rules (CH195 and CH191 dropped when a freeze is after `T_E022` /
  `T_LT5`; registration refused when not before `T_V`); sealed censuses (counts only, tampering refused, completeness, minimum
  covered days); each MDE and F-MDE gate formula with `max(declared, design)`; **the size check and the gate use identical
  strata for each test** (`test_size_check_and_gate_use_identical_strata`, LT4 19 fix 1); the scenario-to-test map and the
  rule that a failing scenario sets only its own tests to "SE check failed" with k unchanged; `lookback` lines never become
  units; an end-to-end synthetic analysis with a reduced `k_tests`.

### 8.4 Registration steps and pins (in order)
1. Challenger R1 on this file; fixes in a response section; re-check if required.
2. **Design-text freeze commit**, its sha256 in the ledger, before the earlier of 2026-11-15T12:00Z and `T_E015`.
3. q0600 restore, q0601 seal, seal committed and pulled on the host.
4. Code (8.1, 8.3); a `science-reviewer` freeze check of the census and size-check code against sections 1.8, 1.8.1 and 7;
   fixes (none may change frozen text, 1.1).
5. Censuses q0602-q0604 (counts only); drops recorded in 6.3; `k_tests`, scales, cuts, `perm_stratum` and `exclude_family`
   filled with the exact census floats; a freeze record written (LT4 19's form: module hashes, spec hash before the pin, census
   output hashes re-verified on the host, spec values checked against the census JSON).
6. Size check q0605 (2,000 worlds x 200 draws, seed 20261177, the census-fixed strata); results recorded per test.
7. Reader freeze check; host dry run with the exact cron command following 8.2's ladder (the step used is recorded).
8. LT5's and LT6's registration commits (or recorded drops) exist; the engine embargo entries of section 9 are applied in
   `config.EMBARGO` before acceptance.
9. Pins: `SPEC_SHA256`, `code_sha256` map, `code_check` passing; E-numbers assigned from the ledger; the ledger entry is the
   registration commit, at least 24 h before `REGISTERED_UTC` and before `T_V`; the imported modules recorded as frozen to the
   analysis date.
10. Install the cron line and run `backfill-series` within `[REGISTERED_UTC - 72 h, REGISTERED_UTC - 24 h]`; verify `pinned:
    true` and `nothing_new` before `REGISTERED_UTC`; queue q0607 with `not_before` the analysis date.

## 9. Signal-engine mapping and embargo requests

Every family below is point-in-time from the origin capture, its pass's sweep 1, the previous pass's sweep, or the engine's own
earlier `quotes/` (DESIGN_V1 16 causality). Each is an **auxiliary family** (own write-once table and version string). **Embargo
first** (DESIGN_V1 8): any challenger that isolates one of these families carries its token until **2026-12-31T00:00Z** (LT7's
analysis date plus 12 h; later if LT7's window slides; never earlier), from the day LT7's design is accepted. The CANDIDATES
round-12 note already asks the builder not to build an isolating challenger for the six before these dates are fixed.

| Test | Family (aux version) | Columns (NaN = missing) | Source and clock | Token -> until |
|---|---|---|---|---|
| CH195 | `resist` (`se-aux-resist-v1`) | `rs_hit_depth_prev`, `rs_away_depth_prev`, `rs_log_ratio` (hit minus away, signed by the own 2 h change) | sweep 1 of the previous pass, lagged join on stored book columns | `resist` (new) -> 2026-12-31; **`book` -> 2026-12-31 (from 12-09)** |
| CH191 | `capath` (`se-aux-capath-v1`) | `cp_pc_6h`, `cp_sa_6h`, `cp_pc_24h`, `cp_sa_24h`, `cp_nsteps_24h` | the engine's `quotes/` of slots k - 12 .. k | `capath` (new) -> 2026-12-31 |
| CH194 | `mm_fresh` (derived set) | `mm_fresh_share = chg_1h / own 2 h change`, `mm_held` | existing momentum columns | `mm_fresh` (new) -> 2026-12-31 |
| CH197 | `deepbook` (`se-aux-deepbook-v1`) | `db_imb_touch`, `db_imb_behind`, `db_dis`, `db_share_behind` | sweep 1 of the pass (best-level sizes and 5c depths) | `deepbook` (new) -> 2026-12-31; `book` as CH195 |
| CH193 | `absorbed` (derived set) | `mt_absorbed = traded x 1[|own 2 h change| < 0.005]`, `mt_absorbed_logdv`, `bk_touch_minsize_side` | the movetype tolerance on `volume24hr`; sweep 1 for the last column | `absorbed` (new) -> 2026-12-31; **`movetype` -> 2026-12-31 (from 11-22)** |
| CH192 | `ivr` (derived set) | `ivr_24h = log(spread / rv24*)`, `ivr_7d` | `market_state` spread and `ms_rv24`; `sp_rv7d` | `ivr` (new) -> 2026-12-31 |

**Requests to the signal-engine track (this branch does not edit engine code; `config.EMBARGO` is not edited here).**
- **`book` to 2026-12-31T00:00Z** (from 12-09). A book-isolating LightGBM with the 1c and 5c depths per side and the own 2 h
  change can learn CH195's hit-side depth and CH197's behind-touch split on `dir_2h`/`dir_24h`. **Cost, disclosed:** the book
  family stays hidden 22 more days. LT7's acceptance is conditional on this entry.
- **`movetype` to 2026-12-31T00:00Z** (from 11-22). A movetype-isolating model with the traded flag and the own 2 h change can
  learn the absorbed (traded, no move) state through the `flat` class. **Cost:** movetype hidden about 5.5 more weeks. The
  narrower alternative (only the new `absorbed` token, movetype released on 11-22) is open question 15; if CH193 drops at its
  census, this extension is withdrawn with a ledger line.
- New tokens `resist`, `capath`, `mm_fresh`, `deepbook`, `absorbed`, `ivr` to 2026-12-31, entered before any isolating
  challenger is scored. Any feature combining a spread with a realised volatility (a ratio or both in an isolating model built
  for that purpose) carries `ivr`; `surprise` (11-19) is not extended for it.
- **The champion and broad models** are not embargoed under DESIGN_V1 8; CH191 and CH194 are shadowed by the champion's
  momentum inputs. LT7 asks that no attribution (SHAP or otherwise) of the champion or any broad model on `chg_1h` x own 2 h
  change or on lagged-step interactions be computed or shown before 2026-12-31, and that no LT7 family be added to a broad model
  before then, or that such a model be recorded in the ledger as a development look.
- If a test drops at its census, its new token and any extension made only for it are withdrawn with a ledger line (dates move
  earlier only by that withdrawal, never otherwise).

The engine's yardstick (log-loss gain under `se-promotion-v2`) is a different question from each LT7 primary. A Supported LT7
primary makes its family a candidate; an engine gain never changes an LT7 verdict and an LT7 verdict never promotes a model.

## 10. Disclosures

- **Selection history.** The six tests are round 12's ranks 1-6 (creative-lead pass written 2026-10-21 on `fa856ec4`, from
  round 9-11 probes, LT3/LT4 censuses, the cost model, the maker-rewards snapshot, the signal-engine coverage note and the
  new-streams dry run, with no host probe). Every design change (6.1) was made before any data.
- **The designer** read the round-12 file (sections 0, 0.1, 1, 2.A-C, 3, 4), `LIVE_TESTS_6.md` (all sections including R1 and
  the re-check), `LIVE_TESTS_4.md` (sections 1, 4, 8, 9, 13-19), `LIVE_TESTS_5.md` (sections 0, 16, 17), the ledger by bounded
  read (LT3 registration, LT6 draft entries), `signal_engine/DESIGN_V1.md` section 8 and `signal_engine/CANDIDATES.md`
  (embargo rounds 1-3 and the round-12 note), and `research_lab/book_sweep.py` (`parse_book`, the depth definitions). No data,
  host, outcome, price after an origin, P&L, `data-dumps` file or evidence JSON was read. No code was written.
- **Closest prior AREPO tests.** CH195: E022, LT6 V, E003, CH180, CH20/CH93. CH191: LT5 J, E021, E004/E006, E015. CH194: E021,
  CH37, E015, E004. CH197: E003, LT6 V, LT5 R and H, CH116, CH149. CH193: E015, CH20/CH93, CH180, CH147. CH192: CH33, CH43/E011,
  CH147, round 11's rejected spread-widening idea.
- **Mechanics stated up front.** CH195: the depth-level trait (away side, F, M-B), the post-move book (`zh0`), quote-only
  withdrawals (M3). CH191: the bounce (skip target, M2), ticks, the Gamma quote (M1), momentum (24 h control). CH194: Gamma's
  basis (gate), anatomy (gate, controls), the bounce. CH197: microprice at short horizons (the 22 h target from k + 1, mirror
  M1), symmetric traits (F, M-C), reward ladders (controls, S1), boundary truncation (mid band). CH193: volume-volatility
  clustering (F, M-D), `volume24hr` roll-off and timing (semantic gate, `dV > 0` only), boundary. CH192: the spread's own
  lag-0 mechanics (skip target), spread-volatility clustering (F, M-D'), tick floors and reward bands (controls), liquidity
  (gate).
- **F can reject a true but persistent signal.** A time-symmetric arm cannot tell a persistent informative state from a
  persistent trait that the state proxies equally before and after the target; LT7 accepts that cost for the four level-built
  states (round 12 rule 5, J4-R's VOID) and states it here.
- **CH192's ratio** equals `log spread` once `log rv24` is a control (6.B).
- **Shared data.** Every earlier test and the engine read the same captures and sweeps; LT7's window overlaps none of theirs;
  its look-back reads raw files of LT6's last week (1.1).
- **Window.** Results arrive about 2026-12-30, later than a November window would give; the reasons are in 1.1.

## 11. Open questions for the challenger review

1. **F's rule.** Δ one-sided p < 0.05 and Δ̂ >= 0.5 x betâ, estimated in the arm model (falsification state added to the
   primary model), with a census F-MDE <= 1.0c and a within correlation cap of 0.8: right, or should it be round 12's forms
   (CH195: the away slope's upper 95% bound below the primary minus the MDE; CH192/CH193: lead minus lag >= the MDE)? Is 1.0c the
   right F-MDE cap?
2. **CH191 and CH194's far-future arms as labels, not verdict conditions** (their states are built from changes; a time-
   symmetric arm would falsify persistent drift, the mechanism itself). Accept, or bind them as round 12's sketches did?
3. **CH195 and LT6 V.** `v_prev` removed as a primary control (collinear with the contrast); V's placebo reads the same
   quantity with the opposite sign. Are disjoint origins, the design freeze before `T_E022` and registration before `T_V`
   enough, or must CH195 wait for V's analysis?
4. **CH195's liquidity gate on the contrast** `zR - zR_away` rather than on `zR`: acceptable?
5. **CH192's redesign** (skip interval, symmetric lag over `rv24*_k`, half-tick floor, four slots a day): does it remove the
   lag-0 spread mechanics? Should CH192 be kept at all given its expected census fate?
6. **CH193's k-origin target** (the state is not a move; the lag interval is the lead's mirror image) against LT6's "every
   primary target starts at k + 1": keep, or move to `|mid_{k+2} - mid_{k+1}|` with the lag at (k + 2, k + 3]?
7. **CH193's semantic gate** (trade samples against `dV`, 70% / 30%): enough to read `volume24hr` changes as interval trading?
8. **CH194's basis gate** via `chg_1d` against the own 24 h mid change and the last-trade change: a valid test of `chg_1h`'s
   basis?
9. **Import versus vendoring** of the LT3/LT4/LT5 functions (import with pinned hashes and a void rule, those modules recorded as
   frozen to LT7's analysis date), against LT5/LT6's generated vendored copies.
10. **Ex-crypto primaries for all six**, with the crypto arm reported.
11. **CH197's choices:** best-level size as the touch; the 12:31Z slot chosen from a file-availability fact; the min-size gate
    dropped as not computable; the fake split as a label only.
12. **Census reads of later units' origin-side states** for the F-feasibility correlations (never paired into a target):
    acceptable under the "no quote at a later capture" rule?
13. **Mechanical-world verdict-size statements** (scenarios 13-16) as binding: are the worlds the right mechanical twins, and is
    omitting the gate from the statistic acceptable (it can only raise the rate)?
14. **Window over Christmas**, 21 days, no extension, a holiday-excluded sensitivity only: agree?
15. **Engine costs:** `book` to 12-31 and `movetype` to 12-31, or a narrower `absorbed`-only token?
16. **Multiplier 3.47** for k = 6, not lowered for a smaller census k: agree?
17. **The design-text freeze** (before the earlier of 11-15T12Z and `T_E015`) with the per-test consequences of 1.1, and
    registration later (code pinned by early December): is a text freeze plus a code freeze check against it enough, or must
    the full registration precede `T_E015`/`T_E022`?
18. **Holm and k:** k <= 6 set by the censuses alone, no replacement test, with CH192 and CH193 likely to drop: acceptable?

## 12. Draft ledger block (DRAFT, not registered, not counted)

> ## LT7 (six round-12 candidates, ranks 1-6) — DRAFT pre-registration (not registered, nothing counted, no code)
> - **Design:** `docs/research_lab/LIVE_TESTS_7.md` on `feat/live-tests-7`. Pure reader of streams the host already writes
>   (complete captures, sidecar, sweep 1 of passes k - 1 .. k + 13); no network, no new collector; separate store
>   `live_tests7/`; LT3/LT4/LT5 functions imported unmodified with pinned hashes (void rule); memory planned from LT4's measured
>   484-525 MB with a two-step ladder (<= 800 MB each); install by host cron `55 1-23/2 * * *`.
> - **CH195** resistance: slope of `c_skip` (k + 1 to k + 3) on the pre-move hit-side 5c depth (sweep k - 1), away side in the
>   model, non-sports ex-crypto movers, > 0; block Freedman-Lane gate; away-side falsification F binding; tercile MDE 0.26c.
> - **CH191** grind at the capture clock: three same-signed 2 h steps against one-step 6 h moves on `c_skip`, > 0; MDE 0.25c
>   (borderline); LT5 J's capture-clock heir; far-future path a label.
> - **CH194** the hour-held move: `chg_1h / x` held against fresh on `c_skip`, > 0; Gamma-basis gate; MDE 0.19c.
> - **CH197** patient money: 22 h YES change on the behind-touch imbalance, touch imbalance fixed, daily units at 12:31Z, > 0;
>   far-future F binding; tercile MDE 0.27c (borderline).
> - **CH193** absorbed flow: next 2 h |move| of traded non-movers on net new 24 h volume, lead minus lag F binding; semantic
>   gate on `volume24hr`; likely to drop.
> - **CH192** implied against realised: |move| over (k + 1, k + 2] on spread over own 24 h realised volatility, lag at k + 3, F
>   binding; four units per market-day; likely to drop.
> - **Family:** Holm over k <= 6 (census-fixed), one-sided, alpha 0.05; p = max(event t, two-way, day t) (`G_minor - 1` df for
>   the class tests); multiplier 3.47; 16 binding size scenarios (12 gate worlds through the census-fixed strata, 4 mechanical
>   verdict-size worlds), a failure sets only its own tests to p = 1; window proposed `[2026-12-08T00:00Z, 2026-12-29T00:00Z)`
>   keyed to LT6's `END_UTC` + 24 h (slides with it), single analysis on or after 2026-12-30T12:00Z; design-text freeze before
>   the earlier of 2026-11-15T12:00Z and `T_E015` (CH195 dropped if not before `T_E022`, CH191 if not before `T_LT5`);
>   registration after LT5 and LT6, before `T_V`.
> - **Status:** DRAFT awaiting challenger R1, the design-text freeze, restore and seal (q0600-q0601), code and freeze check,
>   censuses (q0602-q0604), size check (q0605), dry run, engine embargo entries (`book` and `movetype` to 2026-12-31; new
>   `resist`, `capath`, `mm_fresh`, `deepbook`, `absorbed`, `ivr`), pins and registration. E-numbers not assigned.
