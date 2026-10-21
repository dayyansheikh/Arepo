# Live tests 6 (LT6): four round-11 candidates (V, K, D, B), DRAFT pre-registrations

**Status: DRAFT, not registered, nothing counted, no code.** Drafted 2026-10-21 16:37 UTC+1 (2026-10-21T15:37Z) on branch
`feat/live-tests-6` from the `chore/arepo-claude-setup` tip `f1100cc5`. This is a design-only first commit, as the first
commits of LT3, LT4 and LT5 were. E-numbers are **not** assigned here. E026 is the last number used; LT5 provisionally
holds E027-E031 for whichever of its tests survive; LT6 takes the next free numbers at its own registration (provisionally
in the order V, K, D, B for the tests that survive). Before registration this needs, in order:
1. a challenger review (`science-reviewer`) of this file, and the fixes;
2. the census input seal (section 7), restored and re-hashed from the data releases;
3. the code (section 8), a freeze check of code against design, and the fixes;
4. the counts-only censuses (section 7), which fix k;
5. the size check at >= 2,000 worlds on the code to be pinned (section 1.8);
6. a host dry run with peak RSS measured (section 8.2);
7. LT5's registration commit (LT6 registers after it), the engine embargo entries of section 9, the `SPEC_SHA256` and
   `code_sha256` pins, the ledger entry and the reader's installation (section 8.4).
Until the pin exists, every line a reader writes is `prospective_unregistered` by construction.

**R1 (2026-10-21):** challenger round 1 (`reviews/LT6_CHALLENGER_R1_2026-10-21.md`, REVISE: V, K, D ACCEPT_WITH_CHANGES, B REVISE;
12 required changes) is answered in **section 14**. The changes are applied in sections 0-13 as well; **where any text differs,
section 14 governs.** In short: D and B take the event t on `G_treated - 1` df; B gets a binding volatility-clustering size world,
a clean no-birth class and a crypto gate; every class MDE gate carries `sqrt(max(1, VIF_w))`; V's depletion gate binds on the 1c
touch with a toward-minus-away asymmetry; every E022 condition is keyed to E022's own registration and `END_UTC` (the family slides
with it); D carries "partially seen" unless CB18 withholds its `end_date`-class print (request in the section 14 annex); the census
seal, look-back, memory plan and K's train algorithm are made exact. A short re-check of section 14 is needed before any code.

**R1 re-check (2026-10-21):** `reviews/LT6_R1_RECHECK_2026-10-21.md`, R1_RESPONSE_INCOMPLETE (2 required, text only), answered in
**section 15**: V's freeze condition is keyed to `T_E022`, the earlier of E022's analysis job start and its analysis commit (the
response had loosened it to the commit); the crypto classifier is pinned and B uses the gate only. **Where any text differs,
section 15 governs, then section 14.**

This is research tooling. AREPO never trades. No edge, calibration, profitability or tradability claim exists or is implied.
Every count quoted from round 9/10 probes, LT3/LT4 censuses, the gamma-rules churn probe, the cost model, the maker-rewards
snapshot or the signal-engine coverage note is a **counts-only development figure on worn data**. Every MDE here is a
**planning estimate** built on stated assumptions, not a measurement. Nothing here read a price after an origin, an outcome or
a P&L. No host, network, `data-dumps` or evidence-JSON read was used to write it.

Source ideas: `CREATIVE_HYPOTHESES_2026-10-25.md` (round 11; Fable xhigh) section 3, ranks 6-9: **CH190** (the makers' vote),
**CH185** (clip trains by size identity), **CH187** (deadline moves) and **CH188** (sibling birth). Ranks 1-5 are LT5
(`LIVE_TESTS_5.md`) and are not duplicated; ranks 10-11 (CH186, CH189) are engine-first and are left out. LT5 section 7.2 gave
a reason for not taking each of the four; section 6.2 answers each reason. The design is written to the round's binding rules
(its section 0 and 0.1), to LT4's lessons L1-L15 and to every LT5 R1 / re-check / census-code-check ruling, with these design
changes justified in section 6.1:
- **V (CH190):** the target starts at the first sweep after the decision pass (k + 1 to k + 3), and the origin window starts
  only after LT4's E022 window has ended, because V's state is E022's pinned control `dimb` with the sign reversed;
- **K (CH185):** arm 2 (`rt_share`, which needs `side`) and the monitor arm are removed; the clip class cut is 0.25, not 0.5;
- **D (CH187):** the target is the 22 h skip change k + 1 to k + 12, and a constant-hazard time-decay control is added;
- **B (CH188):** the primary target is the incumbents' absolute mid move (price-based), not the `volume24hr` change.

## 0. Summary

| Handle | Idea | Hypothesis (direction) | Population | Primary | Planning MDE (estimate; multiplier 3.388) | Floor |
|---|---|---|---|---|---|---|
| **V** | CH190 the makers' vote | Within a market, a 2 h move whose post-move book (sweep 1 of the same pass) is skewed **with** the move persists more from the next pass to the third (k + 1 to k + 3) than one whose book is skewed against it, the pre-move skew held fixed (one-sided, > 0) | non-sports movers (traded and quote-only), captures + sweep 1 of passes k - 1 and k | expanding-past demeaned OLS of the sweep skip continuation `c_vskip` on `zv`; **block (circular-shift) Freedman-Lane gate** | **about 0.08-0.18c per SD; tercile 0.17-0.40c** | 0.5c (tercile) |
| **K** | CH185 clip trains | Within a market, a traded 2 h move with a material share of its interval notional in **clip trains** (>= 3 same-token prints of identical size at near-regular gaps) persists more (k + 1 to k + 3) than one with no clips (one-sided, > 0) | all categories (sports split reported), active-frame trade samples + captures | expanding-past demeaned OLS of `c_skip` on 1[clip] over clip and clip-free units | **about 0.32-1.2c** (borderline; census-gated; may drop) | 0.5c |
| **D** | CH187 deadline moves | Within a market on a by-date template, the YES mid **rises** over the 22 h after the first capture that shows a **later** `end_date`, relative to the market's own drift at captures without a change (one-sided, > 0) | non-sports by-date markets, complete captures | expanding-past demeaned OLS of `y22 = mid_{k+12} - mid_{k+1}` on 1[later] over later and no-change units, time decay held fixed | **about 0.43-0.99c** (very likely to drop at its census; declared now) | 0.5c |
| **B** | CH188 sibling birth | Within a market, an incumbent's absolute mid move over the 22 h after a new market is listed in its event is **larger** than after the same market's other captures (one-sided, > 0) | non-sports incumbents of non-series multi-member events, complete captures + sidecar | expanding-past demeaned OLS of `a22 = |mid_{k+12} - mid_{k+1}|` on 1[birth] over birth and no-birth units | **about 0.33-0.99c** (borderline; census-gated; may drop) | 0.5c |

- **Family:** one Holm family over the k surviving primaries, one-sided, familywise alpha 0.05, separate from E009-E011, LT2
  (E012-E014), LT3 (E015), LT4 (E020-E022), LT5 and E026. **Provisional k <= 4.** A test whose census gate fails is dropped
  *before* registration, uncounted, and k is the number that survive; k is fixed in the spec (`k_tests`) at registration and
  never changes. A primary that is unavailable or fails its gate enters Holm with p = 1.
- **Dropped or left out (uncounted; section 6):** none of the four is dropped for feasibility (each is a pure reader of streams
  the host already writes). Removed arms: K's `rt_share` and monitor arms, D's earlier-move arm as a counted test (reported only),
  B's signed tail arm as a counted test (reported only). CH186 and CH189 stay engine-first.
- **Window (proposed):** whole captures with start in `[REGISTERED_UTC, END_UTC)`, 21 days, `REGISTERED_UTC =
  2026-11-16T00:00:00Z`, `END_UTC = 2026-12-07T00:00:00Z`; single analysis on or after `2026-12-08T12:00:00Z`. **These dates are
  keyed to E022's own `END_UTC` (proposed 2026-11-16; LT4 is still DRAFT) and slide with it** (R1 item 7). V's first origin is the
  first pass whose k - 1 capture and sweep start at or after E022's `END_UTC` (2026-11-16T02:31Z as proposed). Registration commit
  on or after 2026-11-01, after E022's registration (or its recorded drop), at least 24 h before `REGISTERED_UTC` and before `T_E022`, the earlier of E022's analysis job start
  (the queue log's start time) and E022's analysis commit (section 1.1 gives the reasons).
- **Expected outcome, declared now:** V passes its counts (its risks are the correlation and depletion gates); K and B are
  borderline; **D is very likely to drop** (the round's own kill line is 150 later moves a day, and the gamma-rules churn probe
  saw no date change among the keys it polled twice in 25 h, section 4). Expected k is 2 or 3. Every taker check is expected
  to be "not shown" (section 1.10).

## 1. Common rules

### 1.0 Lessons carried over (binding from the first draft)

LT4's lessons **L1-L15** (`LIVE_TESTS_4.md` 1.0) apply unchanged: exact `%.17g` writes and round-trip reads; NaN refusals in a
pinned spec; sealed census inputs re-hashed (refuse on mismatch); a pessimistic planning-MDE gate in every census; a
simulated-null size check at >= 2,000 worlds with the limit 0.05 + 1.645 sqrt(0.0475 / worlds) = 0.058; dry-run guards; spec and
code pins on every frozen line; write-once per-capture series and status files; skip-slot labels where a bounce can sit at the
origin; clustering by event, event x UTC day and UTC day with p the largest; Holm over k counted once; economics never changes
a verdict; no both-class inclusion rule; readers at the pass cadence; an internal run lock. LT4's R1/R2 amendments (Freedman-Lane
gates, the permutable-strata rule with the two-day-block fallback, `DE_gate = max(floor, computed)`, the series-family exclusion
rule, the joint late mask for skip targets, one block-anchor function) apply. **LT5's R1, re-check and census-code-check
rulings are adopted as binding from the first draft:**

| LT5 ruling (section) | LT6 rule |
|---|---|
| R1 finding 2: targets start at the first capture after the decision time | every LT6 primary target starts at slot k + 1 (V: sweep 1 of pass k + 1; K, D, B: capture k + 1); the k-origin targets are reported mechanism readings only |
| R1 finding 1, re-check finding 1-2: flow-moderation and persistent continuous states need the block (circular-shift) Freedman-Lane gate with fully specified binding AR worlds | V (a continuous book state of unknown persistence) uses the block gate, minimum 16 units per market; K, D and B (per-interval binary labels) use the plain gate with binding Markov and overlapping-target worlds (1.8, 1.8.1) |
| R1 finding 1, re-check finding 4: a failing size scenario sets only its own tests to p = 1, k unchanged; two separate labels | adopted (1.8) |
| R1 finding 3: family clustering where the state is a family's | B's state is an event-level listing; its p already uses event clusters (1.7); D's co-labelled event edits likewise |
| R1 ruling 11: liquidity-tier correlation gates | every LT6 test gates `|corr(tested term, log1p liquidity_k)| <= 0.5`, within and pooled |
| R1 finding 8: memory from a measurement; dry-run acceptance | planning from LT3's measured 534 MB peak; a declared three-step ladder, each step dry-run measured (8.2; LT6 R1 item 11) |
| R1 ruling 13: one run a pass, staggered | one run a pass (8.2) |
| census-code check 1, 12, 13: seal completeness, the seal's own slot assignment, the seal committed before any census | adopted (7) |
| census-code check 3 (MDE gates take `max(declared, design)`) | adopted for V; K, D and B use the class formula as declared |
| census-code check 10: vendored-provenance test fails on source drift unless recorded | adopted (8.1) |

Round 11's eight design rules (`CREATIVE_HYPOTHESES_2026-10-25.md` 0.1) map onto LT6 as follows; **two are not met by D and B
and this is disclosed rather than hidden:**

| Round-11 rule | LT6 rule |
|---|---|
| 1. Continuous or labelled states on whole populations; no rare events | V's state is continuous on every mover; K's label is defined on every qualifying traded mover. **D and B are rare-event designs by construction** (an `end_date` change, a sibling listing): the round itself ranked them below its top five for that reason and asked for census maps first. LT6 keeps them only behind counts-only kill lines that are the map (section 7); open question 7 asks the challenger to rule |
| 2. The state must change within the market | V and K vary every pass; D's and B's labels are one-off events within a market, so their contrast is "this capture against the market's own earlier captures" (expanding-past demeaning); DE floors 3.0 plus a co-labelling term (7) |
| 3. Correlated moderators: Freedman-Lane only, `|corr|` <= 0.5 with controlled moderators as a census gate | each test lists its within-market correlation gates (section 7) |
| 4. Sign-free primaries | V and K take the sign from the capture's own mid move; D's sign is the mechanical prediction of a later deadline (YES up); B is unsigned. `side` is never read by any LT6 primary, control or gate except K's census-only unsigned train share, which uses no `side` either |
| 5. One value per pass is one value per day | every state varies within pass and within market (D and B across events within a pass) |
| 6. Quote anatomy predicts quote targets | V controls E015's anatomy class and the pre-move skew and starts its target one pass later; K controls J's path shape and E021's freshness; skip targets everywhere |
| 7. Readers at the pass cadence | K extends E021's / LT5 J's per-pass trade-sample reader (samples are retired after three days) |
| 8. Probed deaths are final | nothing here revives comment bursts, cross-event baskets, attention surges, ladder breadth or walked orders. K is not E018's train measure (section 6.2) |

### 1.1 Registration, window, single analysis
- `REGISTERED_UTC` is the first 00:00Z that is **(a)** at least 24 h after the LT6 registration commit (spec pin plus ledger
  entry), **(b)** at least 48 h after LT5's `REGISTERED_UTC`, **(c)** at or after **E022's own `END_UTC`** if E022 is registered,
  and **(d)** never earlier than 2026-11-16T00:00Z. LT6 registers only after LT5's registration commit **and** after E022's
  registration commit or its recorded drop (LT4 census or review ruling in the ledger); while neither exists, LT6 cannot register,
  because (c) is undefined. The proposed value is **2026-11-16T00:00Z** (E022's proposed `END_UTC`), `END_UTC = REGISTERED_UTC +
  21 d` = 2026-12-07T00:00Z, analysis date `END_UTC + 36 h` = 2026-12-08T12:00Z. **The whole family slides if E022 slides**: a later
  E022 `END_UTC` moves `REGISTERED_UTC`, `END_UTC`, the analysis date and every embargo date of section 9 by the rule. The rule uses
  no data; a move is recorded in the ledger. (R1 item 7.)
- **V's first origin (R1 item 7).** V's units read capture k - 1 and sweep 1 of pass k - 1. **V's first origin is the first pass
  k whose k - 1 capture and k - 1 sweep both start at or after E022's `END_UTC`** (with the proposed dates, pass 2026-11-16T02:31Z;
  the 00:31Z pass is not a V origin and is counted as `e022_boundary`). Disclosed: V's earliest states read raw stream files that
  are E022 *target* inputs (sweep 1 of 11-16T00:31Z is E022's last `c_sw` exit); no E022 origin, state or control is read.
- **V's freeze condition (declared now; keyed to E022).** If E022 is registered, V is registered only if the LT6 registration
  commit exists **before `T_E022`, the earlier of E022's analysis job start (the queue log's start time) and E022's analysis commit** (LT4 proposes
  `2026-11-17T12:00Z` as E022's analysis date; an analysis can run hours before it is committed, so whichever comes first binds;
  R1 re-check required item 1). Reason: E022's analysis estimates the coefficient of `dimb = -v` on 21 days of the same population and target
  family; a V design pinned after that number can exist would have had a development look at its own hypothesis. If the commit is
  later, **V is dropped uncounted** and k is reduced before the pin. If E022 is dropped before its registration, (c) and this
  condition lapse (no shared estimate will exist) and rule (d) alone floors the window.
- **Why registration not before about 2026-11-01, and why the window starts on 11-16.**
  1. LT6 registers after LT5's registration commit (LT5 proposes `REGISTERED_UTC` 2026-10-30), and its census, size-check and
     restore jobs must not compete with LT5's chain (q0560-q0564) for the cpu lane or memory (memory-heavy-jobs rule).
  2. Its own chain (challenger, code, freeze check, seal from releases, censuses, size check, dry run) took LT5 about eight days
     from draft to its planned registration; LT6 has one more restore step because its census days have rotated off the host.
  3. **V's disjointness from E022** (rule (c)) puts V's first origin just after E022's `END_UTC` (2026-11-16T02:31Z as proposed).
  4. **Host reader slots.** The host already runs LT3's (`*/20`, to 11-15), LT4's (to 11-16) and LT5's (to 11-20) readers. A
     window from 11-16 lets LT6's reader take LT3's and LT4's slots as they stop, instead of a fourth concurrent reader.
  5. **The US midterm election (2026-11-03)** and its night exclusion (`[2026-11-03T18:00Z, 2026-11-05T00:00Z)`, CB17/CB18)
     fall wholly before the window, so one extreme week cannot dominate D's deadline edits or B's listings.
  A split window (K, D, B from about 11-04; V from 11-16) was considered and not taken: two windows double the registration
  and analysis bookkeeping and put K, D and B on election week (open question 1).
- **Window membership is by capture start**, whole captures in or out. A unit's origin is its own decision time (1.3).
- **Fixed end, no extension** (LT4, LT5). Shortfalls are labelled (*underpowered*, Unavailable), never extended. US
  Thanksgiving (2026-11-26) is inside the window; it is disclosed, not excluded (declared now); a sensitivity without origins in
  `[2026-11-26T00:00Z, 2026-11-28T00:00Z)` is reported and never changes a verdict (R1 answer 15).
- **One analysis**, once, on or after the analysis date (`run_live_tests6.py analyze` refuses before it; `--out` refuses to
  overwrite). No interim look at any outcome (1.6).
- **Effective start** = max(`REGISTERED_UTC`, the first capture processed by the reader at the pinned commit). The analysis keeps
  only lines whose `spec_sha` and `code_sha` equal the pins and whose role is `prospective_confirmation`.

### 1.2 Streams read (all already written by the host's pass; nothing new is fetched; no new collector)
- **Complete-universe captures** `snapshots/<id>/rows.csv.gz` (every 2 h at :31; `state=complete` only): LT3/LT4/LT5's columns
  (`bid`, `ask`, `spread`, `last_trade_price`, `volume24hr`, `liquidity`, `chg_1h/1d/1w`, `end_date`, `event_id`, `neg_risk`,
  `neg_risk_market_id`, `closed`, `active`, `updated_at`, `received_utc`).
- **Sidecar** `rows_ext.csv.gz`: `fee_type`, `fee_category`, `series_slugs`, `order_price_min_tick_size`, `order_min_size` (K),
  `created_at` (B), `parent_event_ids` (B, reported). A missing sidecar sets `sports = -1` (excluded wherever the category is
  needed), counted.
- **Book sweep 1** `book_sweeps/<id>/` (`series_index` 0) **of passes k - 1, k, k + 1 and k + 3** (V): outcome-0 and outcome-1
  `best_bid`, `best_ask`, `depth_*_1c`, `depth_*_5c`, `book_timestamp`, `batch_receipt_utc`; K's mechanism reading M1.
- **Active-frame trade sample of pass k** `trade_samples/<id>/` (`manifest.json`, `trades.csv.gz`): K reads `ts`, `price`,
  `size`, `outcome_index`, `asset`, `tx_hash`. **`side` and wallet fields are never read.**
- **Not read:** the live large-trade monitor, `cross_venue_live/`, `surprise_live/`, the stores `live_tests2/` .. `live_tests5/`,
  CB8-H holders, the CB16/CB17/CB18, E025 and E026 stores, `cb6_extract/`, the new keyless streams (PredictIt, Smarkets, ESPN
  odds, `stream_gamma_rules/`; their counts are cited only as development figures), the signal engine's `quotes/`, `features/`,
  `aux/` and `predictions/`, and Gamma outcome fields of any kind.

### 1.3 Clocks, slots and decision times
- **Slots:** as LT3-LT5 (`grid0 = 2026-10-01T00:31Z`, 2 h, tolerance 30 min, first complete capture of a slot). "k - 1" and
  "k + h" are slots, not file order. Target slots: k + 1, k + 3, k + 12.
- **Decision time per test** (the latest input's own receipt; states use that input and strictly earlier ones only):
  - **V:** sweep 1 of pass k (`batch_receipt_utc` of the outcome-0 token), minutes after capture k. The state uses captures
    k - 1, k and sweep 1 of passes k - 1 and k. **The target starts at sweep 1 of pass k + 1.**
  - **K:** the trade sample's receipt in pass k (LT5 J's clock: `t_k` = the sample's `origin_utc`, the capture row's receipt;
    `t_{k-1}` = the market's row receipt in capture k - 1). The state uses capture rows k - 1, k, the sidecar of k and trade rows
    with `t_{k-1} <= ts < t_k`. The coverage flag depends on rows between `t_k` and the receipt; they are public before the
    decision time, and **the target starts at slot k + 1**, so they lie before the target window (LT5 R1 finding 2).
  - **D:** capture k's row `received_utc`; the state uses captures k - 12 .. k and the sidecar of k. The edit happened somewhere
    in `[t_{k-1}, t_k)`; **the target starts at slot k + 1**.
  - **B:** capture k's row `received_utc` for the incumbent, **and** the newcomer's row in the same capture (the listing is seen
    in capture k). A newcomer row received more than 5 s after the incumbent's row cannot label it (LT5 F's guard; the unit
    keeps class 0 and the guard loss is counted). **The target starts at slot k + 1.**
- **Late rule:** as LT4 1.3 (a frozen file is written before its earliest target slot can start, else `.late`, units lost and
  counted; *late-loss* above 2% of a test's origin files).

### 1.4 Shared origin-side eligibility
LT4 1.4 items 1-8, applied in order and counted (LT3's `move_join` and `classify`, vendored): binary, open and active at k - 1
and k; two-sided and tight (spread <= 0.10) at both; `mid_k` in [0.02, 0.98]; as-of end unknown or > `t` + 3 h; category by
`cb17_census.is_sports_sidecar` on the sidecar of k; one row per `condition_id`; for move units `|x| >= 0.01`, `x = mid_k -
mid_{k-1}`, with LT3's class and geometry. V and K use items 1-8. **D and B** use items 1-3, 6, 7, `mid_k` in [0.05, 0.95] and an
as-of end > `t_k` + 27 h (their 24 h targets; CB18-S's convention), with their own unit definitions (sections 4, 5).

### 1.5 Missing data and per-capture status (never imputed)
As LT4 1.5 and LT5 1.5: every frozen unit receives exactly one status at every target (`two_sided`, `one_sided`, `closed_flag`,
`absent`, `capture_missing`; sweep targets `two_sided`, `one_sided`, `absent`, `capture_missing`), write-once and online; only
`two_sided` has a target; the attrition rule (|a_1 - a_0| > 2 pp gives *attrition-differential* and Lee-type bounds; for V the
upper and lower terciles) never changes a verdict. A required input missing at the origin produces no unit and is counted
(`sidecar_missing`, `.nosweep`, `.noprev`, `.noprevsweep`, sample absent, `lookback_missing`). A missing control or state is NaN
(excluded, counted), never 0. **Declared indicator-pair exceptions only:** an unknown `end_date` (V, K) enters log hours-to-end as
0 with `hte_unknown`; a missing Gamma `chg_1d` / `chg_1w` as 0 with its flag. The reader's own mid changes are NaN when a slot is
missing.

### 1.6 What is not looked at before the analysis date
No mid, move, target, P&L, regression or plot from `live_tests6/` files, or from in-window captures, sweeps or samples, for these
hypotheses. Only `run_live_tests6.py ops-stats` may run (file, line, role, class and status counts; reads no price column,
enforced by a unit test). No change of thresholds, scales, populations, estimators or k after registration; operational fixes
are logged as deviations. LT4's and LT5's analyses (11-17, 11-21) and CB17/CB18 results that arrive during LT6's window change
nothing in LT6. **CB18 (R1 item 8):** CB18 reads SCREEN_18 files from 2026-11-11T08:00Z, possibly before LT6's pin, and reports an
`end_date`-change class. No LT6 designer, coder or reviewer reads any CB18 output on that class (or CB18-S's results) before LT6's
pin, and **D's text is frozen at the R1-accepted text**: after the R1 re-check accepts it, D changes only by census-fixed values
named in section 7, **and by fixes found by the code freeze check if they are committed before 2026-11-11T08:00Z** (the first
SCREEN_18 read); any change to D's text after that time gives D *partially seen*. Any breach is recorded in the ledger and D
carries *partially seen*. **This text freeze is the real protection** (the same orchestrator may run CB18; R1 re-check note), the
CB18 request of the section 14 annex a second one.

### 1.7 Estimators and inference
- **Expanding-past demeaning** for all four primaries (J4-R; LT2-LT5): every regressor (the tested term and every control) minus
  the mean of the market's strictly earlier units of the same test; target raw; the first unit of each market drops.
- **Standard errors and p (L10):** CR1 on event, two-way event x UTC day of the origin, and UTC day. One-sided
  **p = max(p_event on t with G_event - 1 df, p_two-way normal, p_day on t with G_day - 1 df)**. Where the census top series
  family is not excluded (1.9), the event t also uses `G_series - 1` df if smaller. The conservative 95% CI is the hull of a
  2,000-draw event bootstrap and the three Wald intervals. Two-day blocks are a sensitivity for the 22 h targets (D, B).
- **Few treated clusters (D, B; R1 item 1).** With about 150 events holding a labelled unit, CR1 over all `G_event` clusters
  over-rejects (MacKinnon and Webb 2017: the reference distribution is governed by the treated clusters). For D and B:
  **p = max(p_event on t with `G_treated - 1` df, p_two-way normal, p_day on t with `G_day - 1` df)**, `G_treated` = the number of
  events with at least one labelled unit in the analysis sample (the series-family df rule applies if smaller). The conservative CI
  uses the `G_treated - 1` t quantile for the event interval. The size check reports, in scenarios 6, 7 and 11 at 0.0125 and 0.05,
  **both** the plain CR1 rate (event t on `G_event - 1` df) and this rule's rate (1.8).
- **Co-labelled units (D, B).** An `end_date` edit or a listing often labels several markets of one event in one capture; they
  share the news. The event cluster contains them; the census design effect adds a co-labelling term (7).
- **Washout (D, B; R1 recommended).** A no-change (D) or no-birth (B) unit at slots k + 1 .. k + 11 after a labelled unit of the
  same market is excluded (`washout`, counted): its 22 h target overlaps the labelled event's aftermath, so it is neither a clean
  control nor treated.
- **Both-demeaned sensitivity (R1 recommended).** Every primary is re-estimated with the target also expanding-past demeaned;
  reported, never changes a verdict. The census prints per-market label sums (counts only) so the reliance on markets with one
  labelled unit is visible before registration.
- **Overlapping targets.** V's and K's skip targets (k + 1 to k + 3) at consecutive origins of a market overlap by one pass. D's
  and B's 22 h targets overlap at consecutive captures of a market by up to ten passes (baseline units). The clusters absorb
  within-day overlap; two-day blocks are reported; the size check carries binding MA(2) and MA(10) worlds (1.8).

### 1.8 Gates (valid within-unit nulls) and their size
- **V: block (circular-shift) Freedman-Lane gate** (LT5's `block_fl_gate`, vendored unchanged): within each market the
  reduced-model residual series (ordered by origin) is circularly shifted by an offset drawn uniformly from `[s_m, n_m - s_m]`,
  `s_m = max(4, ceil(n_m / 4))`, and the full model is refitted; 200 draws; passes if `p_perm < 0.05`; markets with `n_m < 16`
  shiftable rows are excluded from the gate (counted; LT5 re-check finding 1). **Why the block gate for a book state:** V's state
  is a continuous slope term whose serial dependence within market is unknown (a standing skew can persist for hours; the sign
  of the move varies, which lowers it), and its target overlaps by one pass. The label permutation broke under exactly this
  combination in LT3's `flowperm_ar0.6` world (0.0590 > 0.058). The plain gate with extra scenarios was the alternative; the
  block gate is the conservative choice and is already written, reviewed and size-checked in LT5's code.
- **K, D, B: Freedman-Lane permutation** (LT4's `fl_perm_gate`, vendored): after expanding-past demeaning, the target's residuals
  from the reduced model are permuted within strata and the full model refitted; 200 draws; passes if `p_perm < 0.05`. Strata:
  market x UTC day if >= 50% of the test's **labelled** units (clip, later, birth) sit in permutable strata (>= 4 units), else
  market x two-day block if >= 50%, else the test fails its census gate (`perm_stratum`, fixed by counts in the census).
- A failed gate on data gives p = 1 in Holm and the label "SE check failed (gate on data)".
- **Size check (L5), after the censuses (k fixed first).** `size-check` runs once, on the code to be pinned, 2,000 worlds x 200
  draws, seed **20261167**, limit 0.058. **Binding scenarios, each mapped to the tests it covers** (no effect in every world):

  | # | Scenario (fully specified in 1.8.1) | Gate | Binding for |
  |---|---|---|---|
  | 1 | binary iid label | FL | K |
  | 2 | binary label, persistent market rates | FL | K |
  | 3 | binary label, control at correlation 0.7 with a real effect | FL | K |
  | 4 | binary Markov label (per-unit persistence 0.6), MA(2) target, unbalanced markets | FL | K |
  | 5 | as 4 with persistence 0.9 (an algorithm running for many hours) | FL | K |
  | 6 | rare event-level label shared by an event's markets at one unit, MA(10) target with an event-level shock, control at correlation 0.5 with a real effect | FL | D |
  | 7 | as 6 with the absolute-value target | FL | B |
  | 8 | continuous state iid, control at correlation 0.5 with a real effect, MA(2) target, unbalanced markets | block FL | V |
  | 9 | as 8 with AR(1) state rho 0.6 | block FL | V |
  | 10 | as 8 with AR(1) state rho 0.9 | block FL | V |
  | 11 | **(R1 item 2)** stochastic volatility, a birth hazard rising with current volatility, the prior-|move| controls in the model, absolute target, no birth effect | FL | B |
  | 12 | *(non-binding, reported; R1 recommended)* label incidence correlated with the market's target level, raw target with demeaned regressors | FL | D, B (reported only) |

  **Also reported, never binding (R1 item 1 and recommended):** in scenarios 6, 7 and 11, the rejection rates at nominal 0.0125 and
  0.05 of **both** the plain CR1 rule (event t on `G_event - 1` df) and the analytic p rule of 1.7 (with `G_treated - 1` df); and a **planted-effect power run** for D and B (scenario 6 with
  a planted later effect of 0.5c and 1.0c; scenario 7 with a planted birth effect of 0.5c and 1.0c; 500 worlds each), giving the
  gate's and the analytic rule's power. A rate above its limit (0.0125 + 1.645 sqrt(0.0125 x 0.9875 / 2,000) = 0.0166; 0.058)
  labels the test *analytic p oversized in simulation* in the analysis; it does not change k, p or a verdict, because the binding
  size statement is the gate's (as in LT3-LT5). Power runs are information only and drop nothing (the census MDE gate is the
  declared power gate). **Seeds (R1 re-check):** binding scenarios 1-11 draw from the one generator seeded 20261167 in table order;
  the non-binding runs use their own generators, derived explicitly from 20261167 so they cannot perturb the binding worlds:
  scenario 12 seed `20261167 x 100 + 12` = 2026116712; the power runs `20261167 x 100 + 21 .. 24` = 2026116721 (D, 0.5c), 2026116722
  (D, 1.0c), 2026116723 (B, 0.5c), 2026116724 (B, 1.0c); the CR1 / `G_treated` rates are computed on the binding worlds themselves.

- **Consequence of a failure (declared now, as LT5 1.8):** a failing scenario makes **only the tests it is binding for** "SE
  check failed (size scenario)": p = 1 in Holm, **k unchanged**, no rerun, reseed, redesign or variant. Other tests and the pin
  are not blocked. `max_retries 1` covers a deterministic crash only (same code, seed, worlds and draws, no output written). No
  preliminary run of any scenario at seed 20261167 is made, so no variant can be chosen by its simulated rate.

### 1.8.1 Simulated worlds (declared now; no census input)
Common unless stated: no effect of the tested term; a market's target level `N(0, 0.01)`; unit `i` of a market has `t_row = 7,200
i` s and `day = i // 12`; 200 draws per world at a fresh sub-seed drawn from one generator seeded 20261167, scenarios in the
table's order.
- **Scenarios 1-3 (K):** LT4's validated worlds, vendored unchanged (60 markets x 40 units; events of three markets): 1 =
  `sim_move_world` (class rate 0.3, noise SD 0.04); 2 = the same with market class rates `U(0.1, 0.6)` and market target levels;
  3 = `sim_corr_label_world` (label = 1[z > 0], z correlated 0.7 with `c1 ~ N(0, 1)`, `c1` effect 0.02, noise SD 0.04). Strata
  market x day, minimum 4.
- **Scenarios 4-5 (K):** LT5 scenario 4's world (60 markets, `n_m` uniform on 6..60, events of three), with label rate `p_m ~
  U(0.05, 0.3)` (clips rarer than jumps) and persistence 0.6 (4) or 0.9 (5): at each unit the label keeps its previous value with
  that probability, else is redrawn Bernoulli(`p_m`); pass shocks `u ~ N(0, 0.03)`; `y_i = level + u_{i+1} + u_{i+2} + 0.5
  u_{i+3}`; `c1 ~ N(0, 1)` with no effect. FL, market x day strata, min 4.
- **Scenario 6 (D):** 240 markets in events of four; `n_m` uniform on 24..120 (two to ten days); per event and unit an edit occurs
  with probability 0.004 and labels **every** market of the event at that unit (so markets have 0, 1 or a few labelled units);
  pass shocks: market `u ~ N(0, 0.0173)` and event `w ~ N(0, 0.01)` (shared by the event's markets); `y_i = level + sum_{j=2..12}
  (u_{i+j} + w_{e, i+j})` (the 22 h skip target at 2 h spacing, MA(10) in unit steps); control `c1 = 0.5 zL + sqrt(0.75) xi` (`zL`
  the standardised label, `xi ~ N(0, 1)`; correlation about 0.5, the census cap) with a real effect 0.02. FL, market x day strata,
  min 4.
- **Scenario 7 (B):** as 6 with label probability 0.006 and target `y_i = level + |sum_{j=2..12} (u_{i+j} + w_{e, i+j})|` (the
  absolute 22 h move; skewed, non-Gaussian), `c1` effect 0.02 on that target.
- **Scenarios 8-10 (V):** 80 markets, `n_m` uniform on 6..60 (18% below 16), events of three; state `z` = market level `N(0, 0.5)`
  + AR(1) with rho 0 / 0.6 / 0.9, stationary SD 1; control `c1 = 0.5 z + sqrt(0.75) xi`, `xi` AR(1) with the same rho, stationary
  SD 1, real effect 0.02; target `y_i = level + 0.02 c1_i + u_{i+1} + u_{i+2} + 0.5 u_{i+3}`, `u ~ N(0, 0.03)` (MA(2), the skip
  target's overlap); no effect of `z`. Block FL as declared, minimum `n_m` 16.
- **Scenario 11 (B; R1 item 2):** as 7 (240 markets in events of four, `n_m` uniform on 24..120), with **stochastic volatility**:
  per market log-volatility `s_t` AR(1), rho 0.95, stationary SD 0.5, plus an event component (half the variance shared by the
  event's markets); market pass shocks `u_t = 0.0173 x exp(s_t - 0.25) x e_t`, `e_t ~ N(0, 1)` (with `Var(s_t) = 0.25`,
  `E[exp(2 (s_t - 0.25))] = 1`, so the `- 0.25` keeps the **mean variance** at the base; corrected by the R1 re-check, where
  `- 0.125` kept only the mean multiplier at 1 and inflated the variance by about 1.28x); event shocks likewise; **birth hazard per event and unit `0.006 x exp(sbar_{e,t})`
  truncated at 0.05**, `sbar` the event's mean `s_t`, so listings come when the event is volatile. The model includes the
  primary's prior-|move| controls computed from the simulated mid path (own `|2 h|`, `|6 h|`, `|24 h|` moves and the event's
  leave-one-out `|2 h|` move); target `|sum_{j=2..12} (u_{i+j} + w_{e,i+j})|`; **no birth effect**. FL, market x day strata,
  min 4 (the permutation does not keep intra-day timing, which is why this world binds). If it fails, B is "SE check failed (size
  scenario)", p = 1, k unchanged.
- **Scenario 12 (non-binding):** as 6, with the market's label probability `0.004 x exp(25 x level_m)` (markets with higher
  target levels are edited more), raw target; rate reported for the raw-target and both-demeaned estimators.
- **Criterion:** rate <= 0.05 + 1.645 sqrt(0.0475 / 2,000) = 0.058 per binding scenario at 2,000 worlds.

### 1.9 Verdicts and labels (per primary, after Holm over k)
- **Supported (exploratory, prospective):** Holm-adjusted one-sided p < 0.05, estimate in the predicted direction, gate passed.
- **Contradicted:** the conservative 95% CI lies entirely on the other side of 0. **Inconclusive:** otherwise.
  **Unavailable:** below the test's floor counts, or fewer than 10 UTC days with units.
- **Labels (never change a verdict):** *material* (V: the top-minus-bottom tercile contrast of `zv` >= 0.5c; K, D: point estimate
  >= 0.5c; **B: point estimate >= 1.0c on the absolute move**, CB18-S's floor for the same kind of target, R1 answer 10; B's
  census MDE gate stays at 0.5c); *partially seen* (D, unless the CB18 request of the section 14 annex is applied before the pin,
  or if any breach of 1.6 is recorded); *analytic p oversized in simulation* (1.8); *underpowered*; *attrition-differential*; *late-loss*;
  *coverage-limited* (K: interval-truncated > 2% of sampled traded movers with >= 4 rows); *series-concentrated* (one series
  family > 50% of a primary's units after the census rule); *sweep-missing*; the per-test mechanism labels.
- **Series-family rule (census-fixed):** if the census top series family holds > 40% of a test's primary population, that family is
  excluded from the primary (`<test>.exclude_family`; `""` = none) and the test's MDE gate is recomputed after the exclusion.

### 1.10 Economics (separate; never changes a verdict)
- Paper taker round trip per share at the recorded touches (sweep 1 of the entry pass and of the exit pass), fees on both legs from
  the origin sidecar (`economics.fee_spec`, `resolve_rate(..., "max_if_unknown")`), LT3's `paper_taker` and `econ`
  (event-clustered mean, one-sided p, >= 30 trades in >= 10 events). No depth, queue or latency: optimistic.
- **Hurdles from `cost-model-v1`** (`COST_MODEL.md`; development calibration 2026-10-16 to 10-19), by Gamma-liquidity tier: $100
  taker round trip about 2.9c at >= $100k, 3.9c at $10k-100k, 7.2c at $1k-10k; a 5-share touch round trip about 4.5c. A passive
  touch order fills about 3.1% of the time within an hour and loses about 2.38c to adverse selection against a 2 h mark (about
  0.39c at >= $100k). Hold to resolution removes the exit leg.
- **Maker routes** (the primary money route for every test): gross move of the favourable cell only, "gross, no fills", per
  liquidity tier, with the 0.39c (>= $100k) adverse-selection figure beside it. Sign-free maker-protection routes (B; D's S3)
  report the gross absolute move and spread change against the same figure.
- **Declared in advance:** every AREPO taker cost check has failed (E004, E007; 0 of 95 economic cells positive). "Not shown" is
  the expected outcome for every taker cell here.

### 1.11 Overlaps, sealing, embargo shadows and counting
- **Within LT6:** V and K both contain traded non-sports movers (V from sweeps, all movers; K from trade samples, all categories);
  D and B read the same captures (by-date markets; incumbents of multi-member events; overlapping units possible). All in one
  Holm family; never counted as independent confirmations. Pairwise unit overlap shares are printed by the census and reported at
  analysis.
- **Against registered or drafted tests (no double count):**

  | LT6 | Closest prior | Same data? | Same contrast? | Why not a double count |
  |---|---|---|---|---|
  | V | **E022** (LT4; hollowness; `dimb = sign(x)(dask5 - dbid5)/(dask5 + dbid5) = -v` is a pinned control) | yes (traded non-sports movers, sweep 1 of pass k, sweep targets) | **the same coefficient if origins were shared** | V's first origin is the first pass whose k - 1 capture and sweep start at or after **E022's** `END_UTC` (1.1), so no E022 origin, state or control is read (its last target sweep is read as a V k - 1 input, disclosed); V is pinned before `T_E022` (1.1) or dropped; E022's `h` is a V control (`zh0`) |
  | V | E020 (LT4; unmoved side after one-sided quote-only moves), E015 (LT3), E021 (LT4) | captures | no | disjoint windows (all end by 11-16); E015's anatomy is a V control |
  | V | LT5 R (imbalance slope jump at the 0.90 reward cutoff) | sweeps | no | R's units are not conditioned on a move and its term is `imb x inside`; overlap 11-16..11-20 only, shares printed |
  | V | LT5 F (family) | captures | no | F's state is the family's simultaneous move; overlap 11-16..11-20 |
  | V | CB17-B2 (breathing book; REP_8 to 11-23) | sweeps 1 and 2 | no | B2 reads the depth shift beneath an unchanged touch between a pass's two sweeps; V reads the post-move skew at sweep 1; overlap 11-16..11-23 |
  | V | E003 (complete, exploratory) | historical books | no | unconditional imbalance at minutes; V is the post-move skew on movers |
  | K | **LT5 J** (jump or grind; to 11-20) | yes (traded sampled movers, interval rows, skip target) | no | J's `g_path` is a K control with a census `|corr|` gate; overlap 11-16..11-20, shares printed |
  | K | E021 (LT4; fresh vs settled; to 11-16) | samples | no | disjoint windows; `fresh`, `log1p age` are K controls |
  | K | E018 (LT3; trains; dropped at census) | samples | no | never registered; its unsigned train share enters K only as a census gate |
  | K | CB18-R (races; map only) | samples | no | k = 0; K excludes gaps under 2 s |
  | D | **CB18-S** (silent edits; SCREEN_18 10-27..11-10, REP_18 11-10..11-24) | captures | no (CB18-S's eligibility requires `end_date` unchanged) | CB18 reports an `end_date`-change class with its unsigned 24 h move, uncounted; REP_18 origins of arm-1 events overlap D's window on 11-16..11-24. LT6 does not read that output before its pin and freezes D's text (1.6); a withholding request to CB18's owner is the section 14 annex; unless applied before the pin, D carries *partially seen* |
  | D | CH189 (engine-first overdue family) | captures | no | overdue extensions are excluded from D's primary and reported (S7) |
  | D | E014 (LT2; flow gain by time to end), engine `tte` | captures | no | the time-to-end level is a D control; D's state is its change |
  | B | LT5 F | captures | no | F's state is siblings' simultaneous moves; B's is a listing; overlap 11-16..11-20 |
  | B | CB17-E (first-day prints, census only), CH22/CH142/CH154 | captures | no | they read the newcomer; the newcomer is never a B unit |

- **Signal-engine shadows (disclosed; section 9).** The engine's targets are directional (`dir_2h/6h/24h`, `res_7d`). V's
  primary (continuation given an aligned skew) is directional and **can be learned by a book-isolating LightGBM model that sees the
  own 2 h change and the 5c imbalance**; the `book` token must therefore cover LT6's analysis date. K's and D's columns are new
  (new tokens). B's primary is an absolute move, which no engine target scores; its signed secondary needs a new token. Broad
  multi-family models and the champion are not embargoed under DESIGN_V1 8 (disclosed as LT5 did).
- **Collection overlap (disclosed):** LT2-LT5, E011, CB17, CB18, E025, E026 and the signal engine read the same captures, sweeps
  and samples. Different hypotheses, no pooling, no store opened by another test.
- **Counting (M3):** the analysis adds **k counted tests**, one per surviving primary, kind `live_tests6`
  (`battery2.KIND_RULES["live_tests6"]`, fail-closed). Gate draws, secondaries, mechanism readings, placebos, economics, censuses
  and the size check count 0. The cumulative count is recorded at registration and at analysis.

### 1.12 Stop rules
- No interim look at prices, targets or P&L; `ops-stats` prints counts only.
- The test runs to `END_UTC` whatever the counts. If, after 7 days, a test's labelled units run below one third of its census
  projection (counts only), the ledger notes "likely Unavailable"; nothing else changes.
- Integrity stop: any change to a pinned file after the pin makes the analysis refuse. A fix then needs a new spec, new E-numbers
  and a new window; old lines keep their outcome. A vendored source changing upstream does not affect LT6 (8.1).
- Operations: the reader exits 75 when nothing is new; a failed reader is re-promoted within 48 h; gaps stay missing and are
  counted; a pass whose inputs were not complete at its freeze deadline is `.late`, never re-read.
- Disk: the reader refuses above 1.5 GB in `live_tests6/` and exits 75 above the data-dumps cap; no retention rule may cover
  `live_tests6/` before the analysis is committed.
- Collection of a kind is switched off when its test is not in `k_tests` (LT3 13.16 fix 2).

## 2. V: the makers' vote (CH190)

- **Hypothesis and mechanism.** A Glosten-Milgrom maker who has just seen the flow (or the reference move) that moved the price
  sets her next quotes where she expects the price to go; depth posted on each side is a costly signal because she will be
  filled there. After a move, depth stacked on the move's side (bids under a rise) says the makers accept the new price; depth
  stacked against it says they expect a fade. In quiet books the skew is inventory and reward geometry (CH116; E003's
  unconditional result was inconclusive), so the vote is read only on movers and only as the **change** from the pre-move skew.
  **Direction: beta(zv) > 0, one-sided.** Who would be wrong: the mechanical reading, in which the skew is the move's own
  footprint (the hit side not yet refilled) and its predictive slope is microprice mechanics that ends within minutes.
- **Unit.** Non-sports market x pass k that is a mover at capture k (1.4 with `|x| >= 0.01`; traded and quote-only), with sweep 1
  of **both** pass k - 1 and pass k two-sided on the outcome-0 token, tight (sweep spread <= 0.10), with both 5c depths present and
  `D0 = depth_bid_5c + depth_ask_5c > 0` at both; Gamma `liquidity_k > 0`; pass k at or after V's first origin (1.1, R1 item 7).
  Category is a spec parameter (`v.population`); the
  sports arm is reported.
- **State (frozen; decision time = sweep 1 of pass k).** `imb_j = (depth_bid_5c - depth_ask_5c) / (depth_bid_5c + depth_ask_5c)` on
  the outcome-0 book of pass j (shares; oriented to outcome 0 = YES); **`v = sign(x) x imb_k`** (aligned skew > 0); `v_prev =
  sign(x) x imb_{k-1}` (the pre-move skew signed by the move, which cannot be a reaction to it); `zv = (v - c_v) / s_v` (census
  centre and scale). Also frozen: `dspread = spread_sw_k - spread_sw_{k-1}`; the toward-side and away-side depth log ratios
  `lt = log((D_toward_k + 1) / (D_toward_{k-1} + 1))`, `la` likewise (toward = asks for a rise, bids for a fall); `h0 = clip(1 -
  D0_notional / liquidity_k, 0, 1)` (E022's hollowness on the outcome-0 book, LT4 4, declared on outcome 0 so that it does not
  depend on LT4's census choice); E015's anatomy class; `book_timestamp` of pass k.
- **Target (exact; LT5 R1 finding 2).** `c_vskip = sign(x) x (smid_{k+3} - smid_{k+1})`, `smid` = sweep-1 outcome-0 mid (joint
  status `two_sided` and in time at passes k + 1 **and** k + 3; joint late mask). Horizon about 4 h, starting at the first sweep
  after the decision pass. Read as persistence: a ratified move keeps going beyond the first pass. E022's own-sweep target `c_sw
  = sign(x)(smid_{k+1} - smid_k)` starts at the state's own book, where an imbalance predicts the next mid mechanically (Cont,
  Kukanov and Stoikov 2014; E003's microprice at minutes); it is reading M2 only.
- **Primary statistic.** Expanding-past demeaned OLS of `c_vskip` on `zv`, controls: `z v_prev`, E015 anatomy dummies (traded,
  parallel, one-sided, spread-change; same-side-unequal the base), `log |x|`, `log1p D0_k`, `log1p D0_{k-1}`, `zh0`, `spread_sw_k`,
  `spread_sw_{k-1}`, logit `mid_k`, `|mid_k - 0.5|`, `log1p volume24hr_{k-1}`, `log1p liquidity_k`, 1[tick = 0.001], log
  hours-to-end (+ flag). Inference 1.7; seed 20261161. Gate: block Freedman-Lane (scenarios 8-10), seed 20261261.
- **Mechanism readings (binding label rules).**
  - M1, the Gamma-mid skip `sign(x)(mid_{k+3} - mid_{k+1})`: if Supported and M1 is below 50% of D_V or its one-sided p >= 0.05,
    label **sweep-stream specific**.
  - M2, the round's own-sweep `c_sw` (reported; carries the microprice mechanics; never changes the verdict).
  - **M3, the depletion decomposition:** the primary with `zv` replaced by `z lt` and `z la` (both demeaned). If Supported and
    only the toward-side term is one-sided significant in the predicted direction (`lt` < 0 predicting continuation), label
    **depletion mechanics (the move's own footprint, not a vote)**.
- **Placebo (reported, label rule).** The pre-move vote: the primary with `z v_prev` as the tested term and `zv` removed. If one-sided
  significant and at least half of D_V, label **standing skew, not a reaction**.
- **Secondaries.** S1 `zv x 1[dspread <= 0]` (the round's "makers confident" moderator); S2 the 1c imbalance in place of 5c; S3 the
  sports arm; S4 traded and quote-only arms; S5 the 6 h Gamma-mid target from k + 1; S6 the top-minus-bottom tercile contrast (the
  material reading); S7 counts by class, tercile, depletion and tick.
- **Planning MDE (estimate).** P1/P1b: about 18,500 non-sports movers a day (traded 8,900, one-sided quote-only 6,600, parallel
  3,050). Assume 60-80% have both sweeps two-sided and tight with both depths and `L > 0` (11,100-14,800 a day; 233,100-310,800 in
  21 days), 75% after the first-unit drop and the joint mask (174,800-233,100). SD of `c_vskip` 5c (4 h sweep skip; E021's M1
  analogue); event DE 2-3; day 1.3-1.5; within-market VIF of `zv` on its controls (mainly `v_prev`) 1.5-3 (unprobed; the census
  measures it). Per SD: `SE = 5c / sqrt(n) x sqrt(DE) x day x sqrt(VIF)`; **MDE = 3.388 x SE = 0.08-0.18c per SD; the tercile
  contrast (about 2.2 SD) 0.17-0.40c** against 0.5c. Powered at every assumed count; the census's job is the confounder gates.
- **Floors (Unavailable):** < 20,000 units, < 300 events, < 10 days.
- **Economics.** (a) Reported taker follow of ratified moves (`zv` top tercile, `|x| >= 0.03`) in >= $100k markets, entry at the
  sweep-1 touch of pass k + 1, exit at the sweep-1 touch of pass k + 3, against the 2.9c hurdle. (b) Maker: lean with the vote
  (post on the aligned side) when `zv` is in the top tercile and the spread did not widen; gross `c_vskip` by tercile, "gross, no
  fills".
- **Missing data.** `.nosweep` (pass k) and `.noprevsweep` (pass k - 1) counted separately; outcome-0 token absent, one-sided, or a
  depth missing at either sweep → excluded (counted); `L` missing or <= 0 → excluded (counted).
- **Disclosed.** The round calls CH190 "the strongest feature in the file and the weakest new mechanism": it is a moderator of
  E003's object and shares E022's reader and controls. Its novelty is the conditioning on the move and the pre-move skew as a
  control; nothing more is claimed.

## 3. K: footprints without wallets, clip trains by size identity (CH185)

- **Hypothesis and mechanism.** TWAP and POV execution algorithms slice a parent order into equal child orders at regular intervals
  (Almgren and Chriss 2001). The parent is larger than what has printed, so the remaining schedule is predictable pressure, and a
  traded move carried by such slices continues. Clips need no wallet and no `side`: they are read from size identity and timing in
  the public prints. **Direction: D_K > 0, one-sided.** Who would be wrong: the coincidence reading (identical round sizes from
  unrelated traders) and the reading in which the algorithm finishes inside the first pass (then nothing is left to continue; this
  design does not test that case, disclosed).
- **Unit.** Market x pass k whose market is in the pass's active-frame trade sample (status ok), is a `traded` mover at k (1.4 with
  `|x| >= 0.01`) and passes the filters below. All categories (E021's and J's convention); `k.population` is a spec parameter;
  sports and non-sports arms are reported.
- **Origin-side filters (in order, counted):** sample status ok; 1.4 items 1-5, 7, 8; class `traded`; sidecar `order_min_size`
  known at k; interval coverage (the page's oldest row of the market at or before `t_{k-1}`, or the page not full; else
  `interval_truncated`); `n_int >= 4` rows of the market with `t_{k-1} <= ts < t_k` and a known outcome.
- **Clip trains (frozen; rows `t_{k-1} <= ts < t_k` only; deterministic algorithm declared now, R1 item 12).** Rows with size
  `<= 2 x order_min_size` are removed first (min-size bots; **the comparison is made in `Decimal`**, `order_min_size` read as text
  from the sidecar and converted with `Decimal`, never via float). The rest are grouped by (`asset`, size key), where the **size
  key** is the `size` field **in its stored form**: `trades.csv.gz` is read with that column as text (`dtype=str`, never parsed as
  float), and the key is `Decimal(text).normalize()` (so `"10"`, `"10.0"` and `"1E+1"` are one key, and no float rounding can
  merge or split sizes); if a source stores `size` as a JSON number, it is parsed with `json.loads(..., parse_float=Decimal)`. Within a group, rows are sorted by (`ts`, `tx_hash`). Then, greedy
  left to right with no overlaps:
  1. start a run at the first unassigned row `i`;
  2. scan `j = i + 1, i + 2, ...`: skip (leave unassigned) a row whose gap to the run's last row is `< 2 s` or whose `tx_hash`
     is already in the run; otherwise, with `g` the gap to the run's last row: if the run has one row, append `j` when the span
     stays `<= 30 min`; if it has two or more rows, append `j` when `g` lies in `[0.5, 1.5] x` the median of the run's current gaps
     (`statistics.median`, which averages the two middle gaps when their number is even)
     **and** the span stays `<= 30 min`; else **close** the run;
  3. a closed run with **>= 3** rows is a clip train and its rows are assigned; the next run starts at the first unassigned row
     after the train's last row. A closed run with fewer rows assigns nothing and the next run starts at `i + 1`.
  Same-second rows are race fingerprints (CB18-R's object). Unit tests cover each branch (8.3).
  `clip_share` = notional (size x token price) share of the interval's rows that lie in clip trains. **Clip:** `clip_share >=
  0.25`; **clip-free:** `clip_share = 0`; the interior is reported (S1). Also frozen: `round_share` (notional share of interval
  rows whose size is a multiple of 10 shares), `minsize_share` (notional share at `<= 2 x order_min_size`), `n_trains`,
  `last_clip_age` (`t_k` minus the last clip row's `ts`), **`H_unsigned`** (E018's M3 unsigned train share on K's own 2 h
  interval rows: notional share of rows with another row of the market within 300 s, any sign; vendored), LT5 J's `g_path` and `maxstep_share` (vendored `path_units` on the same
  rows, tick-snapped, NaN if `steps < 1`), E021's `age` and `fresh = 1[age <= 900 s]`, `n_int`.
- **Target (exact).** `c_skip = sign(x) x (mid_{k+3} - mid_{k+1})` (Gamma mids; joint status `two_sided` and in time at k + 1 and
  k + 3; joint late mask `late1 | late3`). Horizon 4 h, starting at the first capture after the decision time (LT5 R1 finding 2).
- **Primary statistic.** Expanding-past demeaned OLS of `c_skip` on `CL = 1[clip]` over clip and clip-free units, controls: `log1p
  n_int`, `log |x|`, `g_path` (never NaN here: `steps >= 1` because `|x| >= 0.01` and the tick is at most 0.01; a NaN would
  exclude the unit, counted), `maxstep_share`, `fresh`, `log1p age`, `round_share`, **`H_unsigned`** (R1 recommended: a control, not only a census gate),
  geometry dummies, `spread_k`, logit `mid_k`,
  `|mid_k - 0.5|`, `log1p volume24hr_{k-1}`, `log1p liquidity_k`, 1[tick = 0.001], log hours-to-end (+ flag). Inference 1.7; seed
  20261162. Gate: Freedman-Lane (scenarios 1-5), seed 20261262.
- **Mechanism readings (binding label rules).** M1 the sweep skip target `sign(x)(smid_{k+3} - smid_{k+1})`: if Supported and M1 is
  below 50% of D_K or its one-sided p >= 0.05, **Gamma-quote mechanics**. M2 (reported) the 2 h `c = sign(x)(mid_{k+1} - mid_k)`,
  which includes the pre-decision interval. M3 running against finished trains: clip units split by `last_clip_age <= 15 min`; if
  Supported and the running half is not one-sided significant while the finished half is, label **not schedule pressure**.
- **Placebos (reported, label rules).** P1 near-identical sizes: the same train rule on sizes within +/-5% of each other but **not**
  identical (deterministic grouping: rows of one token sorted by size; a group is a maximal run whose largest size is within 5%
  of its smallest, with no two rows of identical size), as a fake class against clip-free units; if
  one-sided significant and at least half of D_K, label **size identity not shown**. P2 the previous interval's class with the
  current class held fixed; at least half of D_K labels **persistent trait**.
- **Secondaries.** S1 `clip_share` as a continuous dose over all qualifying units; S2 the round's cut `clip_share >= 0.5`; S3
  notional clips (identical size x price to the cent) in place of size identity; S4 sports and non-sports arms; S5 the 6 h target
  from k + 1; S6 counts by class, `n_int` band, round-size share and min-size share.
- **Planning MDE (estimate).** P2/P2c bound clocked traded sampled movers at about 1,000 a pass; the >= 4-row, covered subset is
  **unprobed**: assume 150-400 a pass (37,800-100,800 in 21 days); clip 5-15% (unprobed), clip-free 70-85%; 75% surviving the
  first-unit drop and the joint mask (clip 1,420-11,340; clip-free 19,850-64,260). SD of `c_skip` 5c; event DE 2-3; day 1.3-1.5.
  `SE = 5c x sqrt(1/n_C + 1/n_0) x sqrt(DE) x day`; **MDE = 3.388 x SE = 0.32c at the high end, 1.2c at the low end.**
  Census-gated; declared now: K may drop.
- **Floors (Unavailable):** < 2,000 clip units, < 10,000 clip-free, < 200 events, < 10 days.
- **Economics.** (a) Reported taker join of clip-carried moves (`|x| >= 0.03`) in >= $100k markets, entry at the sweep-1 touch of
  pass k + 1, exit at pass k + 3, against the 2.9c hurdle. (b) Maker: while a clip train is running on a token, step aside on the
  side the move came from for one pass; gross `c_skip` by class, "gross, no fills".
- **Missing data.** Sample absent → no units (counted per pass); status not ok, `order_min_size` unknown, `interval_truncated`,
  `n_int < 4` → excluded and counted by reason; rows with unknown outcome excluded from trains and levels and counted.

## 4. D: deadline moves (CH187), census-first

- **Disclosure first.** Round 7 section 4 parked "deadline extensions" because no count was possible without a capture walk and
  the known cases were sports postponements; round 8 repeated it. The host's twelve captures a day make the walk a counts-only
  census on sealed worn captures; the sidecar plus CB17's sports rule separates postponements. **Development prior, disclosed:**
  the gamma-rules churn probe (`NEW_STREAMS_2026-10-19.md`, read-only, 2026-10-20T22:56Z) saw 3 changed keys among those polled
  twice about 25 h apart, all event descriptions, none a date; that frame is the top 3,000 markets by volume, not D's population,
  but it points below the round's kill line. **D is very likely to drop at its census**; it is kept so that the census, not a
  judgement, decides, as LT5 did for H.
- **Hypothesis and mechanism.** On a "by date" question the holder of NO loses value the moment the venue moves the date later
  (more time for the event); no notification is sent and the programs that quote the market may or may not re-centre. If the
  re-pricing is incomplete at the first capture that shows the new date, the YES mid drifts up afterwards. **Direction: D_D > 0,
  one-sided** (later move on a by-date template, YES terms). Who would be wrong: the efficient reading (the first capture already
  carries the new price) and the time-decay reading (below), which the control addresses.
- **Template (declared now, no census choice).** `bydate = 1[the as-of end_date at k - 1, converted to America/New_York, has a
  clock time within 1 minute of 23:59:00 or 00:00:00]` (the venue's by-date convention; DST handled by `zoneinfo`). The census
  prints the time-of-day histogram as a description only; it does not change the classifier. **Parse rules (pinned; R1 answer
  9):** `end_date` is parsed with `datetime.fromisoformat` after a trailing `Z` is replaced by `+00:00`; a naive timestamp is UTC;
  a date-only string or an unparseable value gives no template and no class (excluded, counted, never "unchanged"); two end dates
  are equal when the parsed instants are equal to the second.
- **Unit.** Non-sports market x capture k with 1.4 items 1-3, 6, 7 at k - 1 and k, `mid_k` in [0.05, 0.95], as-of end at k
  > `t_k + 27 h`, and **`bydate = 1`**. Classes: **later** = `end_date_k - end_date_{k-1} >= 1 h`; **no-change** = equal end dates
  (byte-equal after parse). Also excluded from the primary (counted, reported): earlier moves; changes under 1 h; **overdue
  extensions** (old end `<= t_k`, CH189's object, S7); **series roll-overs** (non-empty `series_slugs` and `|delta|` within 1 h of
  1, 7, 30 or 31 days). **Washout (1.7):** no-change units in slots k + 1 .. k + 11 after a later or earlier unit of the same
  market are excluded (counted).
- **State (frozen).** `later`, `delta_h`, the dose `r = delta / (end_old - t_k)` (S1), `updated_at` changed (flag), the change
  interval's move `x = mid_k - mid_{k-1}`, own 24 h change `mid_k - mid_{k-12}` (NaN if the slot is missing; unit excluded,
  counted), and the **time-decay control** `theta24 = 24 x (1 - mid_k) x ln(1 - mid_k) / T_k` (hours; `T_k` the as-of hours to
  end at k, the **new** end for later units). Under a constant hazard `lambda`, `P = 1 - exp(-lambda T)` and the YES drift per hour
  is `(1 - P) ln(1 - P) / T`: a later deadline slows the decay mechanically even when the price is fully updated, which would
  make the contrast positive with no under-reaction. `log T_k` is a control as well. **Disclosed (R1 recommended): `theta24` is a
  survivor-conditional drift.** It is the expected YES drift of a market that has not resolved YES; units whose market resolves or
  closes before k + 12 have no `two_sided` target and leave the sample, so the control describes the drift of the survivors the
  target can see, under an assumed constant hazard. It is a model-based control, not a measurement.
- **Target (exact).** `y22 = mid_{k+12} - mid_{k+1}` (YES terms; joint status `two_sided` and in time at k + 1 and k + 12; joint
  late mask). Horizon 22 h, starting at the first capture after the decision time. The round's 24 h change from `mid_k` with the
  first 2 h move as a control would put a post-decision quantity in the controls; the skip start removes it.
- **Primary statistic.** Expanding-past demeaned OLS of `y22` on `LT = 1[later]` over later and no-change units, controls:
  `theta24`, `log T_k`, `x`, own 24 h change, Gamma `chg_1d` and `chg_1w` (+ flags), logit `mid_k`, `|mid_k - 0.5|`, `spread_k`,
  `log1p volume24hr_k`, `log1p liquidity_k`, 1[neg-risk], `updated_at`-changed flag. Inference 1.7 with the
  `G_treated - 1` event t (R1 item 1); seed 20261163. Gate:
  Freedman-Lane (scenario 6), seed 20261263.
- **Mechanism readings (binding label rules).** M1 the 6 h skip `mid_{k+3} - mid_{k+1}`: if Supported and M1 carries more than the
  whole 22 h effect with the remainder reversing (M1 one-sided significant and `y22 - M1` contradicted), label **transient**. M2
  (reported) the round's `mid_{k+12} - mid_k`.
- **Placebos (reported, label rules).** P1 later moves on **non-bydate** templates (the same model on non-bydate markets): if
  one-sided significant and at least half of D_D, label **not template-specific**. P2 later moves on decided markets (mid > 0.97
  or < 0.03 at k), descriptive.
- **Secondaries.** S0 (R1 answer 8) the primary on later units whose **old end was at least 7 days after `t_k`**, where decay is
  small and `theta24` matters least (reported); S1 the dose `r` among later units; S2 the earlier arm (descriptive, never counted, whatever its count; a
  counts-triggered promotion would be a forking path); S3 maker protection: `|mid_{k+12} - mid_{k+1}|` and the spread change after
  any `end_date` move, **with the maker's own horizon beside it: `|mid_{k+1} - mid_k|` over the widened pass** (R1 recommended;
  it starts at the decision time and is reported only); S4 the `updated_at` co-occurrence split; S5 the sports arm (postponements); S6 counts by class, template,
  category and delta band; S7 overdue extensions (descriptive).
- **Planning MDE (estimate).** Unprobed. At the round's kill line, 150 later by-date interior non-sports moves a day (3,150 in 21
  days), and at 600 a day (12,600); 90% with an earlier unit of the market in the window (2,835-11,340). SD of `y22` 6c; DE 3 (the
  floor; edits are often event-wide, so the census adds a co-labelling term) and day 1.3-1.5: `SE = 6c / sqrt(n_L) x sqrt(DE) x
  day` (no-change units are many, `1/n_0` about 0); **MDE = 3.388 x SE = 0.43c at 600 a day, 0.99c at 150 a day.** Below 0.5c
  only near 600 a day with little co-labelling.
- **Floors (Unavailable):** < 1,500 later units, < 150 events with a later unit, < 10 days.
- **Economics.** (a) Reported taker buy of YES at the sweep-1 ask of pass k + 1 after a later move with `r >= 0.5`, exit at the
  sweep-1 bid of pass k + 12 (or hold to resolution, one leg; the hold arm is reported only where a resolution is in the
  engine's `res_7d` label, never fetched), against the tier hurdles. (b) Maker: widen for one pass after any `end_date` move;
  gross `|y22|` and spread change, "gross, no fills".
- **Missing data.** `.noprev` (capture k - 1) and `lookback_missing` (k - 12) counted; an unparseable `end_date` at either capture
  → excluded (counted), never treated as unchanged.

## 5. B: sibling birth as a salience clock (CH188)

- **Hypothesis and mechanism.** The venue's listing desk adds a market to an existing event (a new candidate, scenario or date)
  because of news. The incumbents' quotes are stale relative to the news that caused the listing; attention and re-pricing follow.
  The listing is dated (`created_at`), text-free and visible only as a new row with the incumbents' `event_id`. **Direction:
  D_B > 0, one-sided** (absolute move). A sign-free maker-protection object (EV 2 in the round). Who would be wrong: the routine
  reading (most listings are scheduled additions with no news content) and the volatility-clustering reading (the listing follows
  a move that would have been followed by more moves anyway; the prior-move controls address it).
- **Birth (frozen at capture k).** A **newcomer** is a market whose row is present in capture k and absent from capture k - 1, with
  sidecar `created_at` in `[t_{k-1}, t_k)` (a market present earlier but newly visible is a **lagged appearance**, reported, not a
  birth). The newcomer's event is **existing** if capture k - 1 holds >= 2 markets with the same `event_id`. The event must be
  **non-recurring**: empty `series_slugs` on the newcomer and on every incumbent (crypto strike additions and dated series
  listings are mechanical). **Crypto (R1 item 4; classifier pinned by the R1 re-check, required item 2).** Crypto births **stay in
  the population**; the census gates them (section 7) and the series-family rule (1.9) applies. **The pinned crypto classifier**
  (used by B's gate and by D's crypto kill line alike; on the newcomer's sidecar row of capture k for B, the unit's for D):
  - `crypto = 1` if the sidecar row exists and its `fee_category`, after `strip()` and `casefold()`, **contains the substring
    `crypto`** (the value set is every such string; it includes the exact value `crypto`);
  - `crypto = 0` if the sidecar row exists, `fee_category` is non-empty after `strip()`, is not one of `nan`, `none`, `null`
    (casefolded), and does not contain `crypto`;
  - **`crypto = unknown`** otherwise: sidecar missing, field absent, empty, `nan` / `none` / `null`, or the market's `sports = -1`.
    Unknown is **counted separately and counted as crypto in the gate's numerator** (never defaulted to non-crypto).
  - **Fail-safe:** the census prints every distinct `fee_category` value of the sealed sidecars with its count; if no value in the
    whole sealed sidecar set contains `crypto`, the classifier is not shown to work, and B's crypto gate and D's crypto kill line
    are NaN and fail. Several newcomers in one event and capture are one birth (`n_born` frozen).
- **Unit.** Non-sports incumbent x capture k: a market of a multi-member, non-recurring event (>= 2 members at k - 1) passing 1.4
  items 1-3, 6, 7 at k - 1 and k, `mid_k` in [0.05, 0.95], as-of end > `t_k + 27 h`, and not itself a newcomer. Classes:
  **birth** = its event has a birth at k and the newcomer row's receipt is within 5 s of the incumbent's (1.3); **no-birth (R1
  item 3)** = no newcomer **and no lagged appearance** in its event at k, **and** not in the washout (slots k + 1 .. k + 11 after a
  birth unit of the same market, 1.7). Everything else (a lagged appearance only, a guard loss, a newcomer with unparseable
  `created_at`, a recurring newcomer in the event, a washout unit) is **excluded and counted by reason**, never class 0.
- **State (frozen).** `birth`, `n_born`, event size at k - 1, neg-risk flag, the incumbent's rank by mid in the event, own absolute
  moves `|mid_k - mid_{k-1}|`, `|mid_k - mid_{k-3}|`, `|mid_k - mid_{k-12}|` (NaN if a slot is missing; unit excluded, counted), the
  event's mean absolute 2 h move over its other incumbents at k (leave-one-out).
- **Target (exact).** `a22 = |mid_{k+12} - mid_{k+1}|` (joint status `two_sided` and in time at k + 1 and k + 12; joint late mask).
  Horizon 22 h, starting at the first capture after the decision time.
- **Primary statistic.** Expanding-past demeaned OLS of `a22` on `BR = 1[birth]` over birth and no-birth units, controls: the three
  own absolute moves, the event's leave-one-out mean absolute 2 h move, `log` event size, 1[neg-risk], logit `mid_k`, `|mid_k -
  0.5|`, `spread_k`, `log1p volume24hr_k`, `log1p liquidity_k`, log hours-to-end, Gamma `chg_1d` (+ flag). Inference 1.7 with the
  `G_treated - 1` event t (R1 item 1); seed 20261164. Gate: Freedman-Lane (scenarios 7 and 11), seed 20261264.
- **Mechanism readings (reported; no label rule).** M1 the 6 h `|mid_{k+3} - mid_{k+1}|`; M2 the first pass `|mid_{k+1} - mid_k|`
  by class (it starts at the decision time and is never a control). Neither changes the verdict.
- **Placebo (reported, label rule).** A **fake birth** per real birth: one capture of the same event drawn (seed 20261364) uniformly
  from the window's captures at least 12 slots from every real birth of that event **and in the same tercile of the event's
  leave-one-out `|2 h|` move as the real birth** (census cuts; R1 answer 11; if none qualifies, no fake birth, counted); its incumbents are relabelled birth and the
  primary is re-run. If one-sided significant and at least half of D_B, label **event-level volatility, not the listing**.
- **Secondaries.** S1 the **signed tail arm** (round's secondary; neg-risk incumbents with `mid_k` in [0.02, 0.10)): YES change
  `mid_{k+12} - mid_{k+1}` on `BR`, predicted < 0, reported only; S2 the 24 h change in `log1p volume24hr` (the round's attention
  arm; a venue field, reported only); S3 the spread change, **with the maker's own horizon beside `a22`: `|mid_{k+1} - mid_k|`
  over the widened pass** (R1 recommended; reported only); S4 the neg-risk and non-neg-risk arms; S5 the sports arm; S6 the dose
  `n_born`; S7 counts of births by category, structure, lagged-appearance share and incumbents per birth.
- **Planning MDE (estimate).** Unprobed. Round 11 guesses 50-200 non-recurring births a day in existing events; the kill line is 30
  a day. Assume 30-200 births a day and about 5 eligible incumbents each (150-1,000 incumbent units a day; 3,150-21,000 in 21 days),
  90% with an earlier unit in the window (2,835-18,900). SD of `a22` 6c (CB18-S's conservative value for a 24 h absolute move); DE 3
  (the floor; the census adds the co-labelling term, about 3 at 5 incumbents per birth); day 1.3-1.5: **MDE = 3.388 x SE = 0.33c at
  the high end, 0.99c at the kill line.** Census-gated; declared now: B may drop.
- **Floors (Unavailable):** < 1,500 birth units, < 100 events with a birth, < 10 days.
- **Material label at 1.0c (R1 answer 10)**, CB18-S's floor for the same kind of target; the census MDE gate stays at 0.5c.
- **Economics.** (a) Maker (the route): widen on incumbents for one pass after a birth; gross `a22`, the widened pass's `|mid_{k+1}
  - mid_k|` and the spread change by class, "gross, no fills", against the 0.39c adverse-selection figure. (b) Reported taker sale of tail members' YES at the sweep-1 bid of
  pass k + 1 after a birth in neg-risk events (S1), exit at pass k + 12, against the tier hurdles.
- **Missing data.** `.noprev` counted; `created_at` missing or unparseable on a newcomer → the newcomer is not a birth and its
  event's incumbents at k are excluded (counted, never class 0); `lookback_missing` counted.

## 6. Ideas dropped, deferred or narrowed, and why (uncounted)

### 6.1 Design changes to the round-11 sketches (made before any data; each needs the challenger's acceptance)
- **V: the target is the sweep skip `c_vskip` (k + 1 to k + 3), not E022's `c_sw`.** The state and `smid_k` come from the same book;
  an imbalance predicts the next mid mechanically at short horizons. LT5 R1 required targets that start after the decision time.
- **V: first origin is the first pass whose k - 1 inputs start at or after E022's `END_UTC` (R1 item 7); the design is pinned before `T_E022` (1.1), or V is dropped.** V's `v` equals
  `-dimb`, E022's pinned control, on the same population, book and target family. On shared origins one coefficient would be both a
  nuisance term in E022 and a primary here (LT5 7.2's reason). Disjoint origins remove the shared data; pinning before E022's
  analysis removes the development look. LT5 deferred CH190 "to after E022's analysis"; this draft reads that deferral as a
  constraint on origins and on the look, and asks the challenger to confirm (question 1).
- **V: the block Freedman-Lane gate** (1.8), the pre-move skew `v_prev` as a control, and the depletion decomposition as a binding
  label (M3) in place of the round's kill rule "hit side still depleted in > 50%" alone (kept as a census gate with a halving
  definition, section 7, because a plain "below its k - 1 level" happens about half the time by noise).
- **V: `h0` on the outcome-0 book** (declared now, not LT4's census-fixed `depth_def`), so V does not depend on another test's
  census.
- **K: arm 2 (`rt_share`) removed** (it needs `side`; LT5 7.2's second reason). **The monitor arm removed** (LT5 does not read the
  monitor; its 9-minute lag and unsigned prints add a stream for a secondary).
- **K: the clip class is `clip_share >= 0.25`, not 0.5** (the round's cut is S2). With at least 4 interval rows, a three-slice
  train is often under half of the interval's notional when other prints are larger; 0.25 keeps "a material share" and roughly
  doubles the clip class at planning shares (section 3). Chosen before any count.
- **K: precise train rule** (exact size, distinct `tx_hash`, gaps >= 2 s, gaps within [0.5, 1.5] x the median, span <= 30 min,
  min-size exclusion from the sidecar's `order_min_size` at k, decision-time safe) and the near-identical-size placebo.
- **K: the target is LT5 J's skip `c_skip`**; the round's `c` from `mid_k` is M2. An algorithm that completes inside the first pass
  is therefore not tested (disclosed in section 3).
- **D: target `y22` from k + 1** (the round's first-2 h control was post-decision); **the constant-hazard `theta24` control**; the
  template classifier fixed now; overdue extensions and roll-overs out of the primary; the earlier arm descriptive only.
- **B: the primary target is `a22` (price-based)**; the round's `volume24hr` change is S2 (hygiene: targets are price-based). The
  "existing event" and "non-recurring" rules, the 5 s newcomer guard and the fake-birth placebo are added.

### 6.2 LT5's reasons for not taking these four, answered
- **CH185 (LT5: "clips are a subset of trains; the round's rule excludes trains; arm 2 needs `side`").** Arm 2 is gone. The round's
  rule ("no idea relies on ... trains") was written after E018's death at the C2 census (H interior 30.8% against 40%), and E018's
  state was a *timing* measure of same-signed neighbours within 300 s, a `side`-signed moderator of 6 h flow. K's state is *size
  identity* with regular gaps, sign-free, on a 2 h move's continuation. K would still be a train object if its class merely
  re-labelled E018's bursts, so the census gates `|corr(1[clip], H_unsigned)| <= 0.5` within market (E018's M3 unsigned train
  share, vendored, census-only). Whether this is enough distance from the rule is open question 4.
- **CH190 (LT5: "deferred to after E022's analysis (2026-11-17)").** Answered in 6.1 (disjoint origins, pinned before the look).
- **CH187, CH188 (LT5: "unprobed; maps first").** Each census below *is* the map: counts only, sealed worn captures, kill lines fixed
  now. If a census fails, its counts are the output (k = 0 for that idea) and are recorded in 6.3.

### 6.3 Census drops
None yet. Census drops will be recorded here, with their counts, before the pin.

## 7. Pre-registration censuses (counts only; before registration; worn pre-window data; no target read)

Each census runs once, reads origin-side fields only (no quote at any later capture, sweep or sample, no target, no P&L), prints
counts, and is committed with its sha256 before the registration commit. **Every gate threshold below is stated now, before any
census.** A failed gate drops that test before registration (uncounted); `k_tests` lists the survivors. Input identity (L3,
LT5 census-code check 1): the census refuses unless every input file it opens is named in the LT6 seal with an equal sha256, and
refuses if a sealed file in a needed slot is absent.

**Inputs (all started before 2026-10-22T00:00Z, before the LT2-LT6 windows; reuse of sealed worn days).**
- **Flow census CK:** the **23 sealed active-frame samples of 2026-10-16 and 10-17** (`seals/lt3_census_inputs_C2.json`, the files
  LT3 C2, LT4 CF and LT5 CJ read) with their captures and sidecars from `seals/lt4_census_inputs_captures.json`.
- **Capture and sweep censuses CV, CD, CB:** the complete captures (rows, sidecar, manifest) and sweep 1 sealed in
  `seals/lt5_census_inputs_captures.json` (**not yet committed at this response: q0564 writes it after 2026-10-21T23:20Z; its sha256
  is to be filled here from the committed seal**, R1 item 9; captures 2026-10-12T00:31Z .. 10-21T22:31Z; sweeps from
  2026-10-19T22:31Z). CV uses the
  passes of UTC 2026-10-20 and 10-21 (each with its pass k - 1 sweep); CD and CB use every pair of consecutive complete slots in the
  sealed span, with the known missing slots (10-14T00:31..10:31; 10-21T00:31 and 02:31) left missing; a pair across a gap is no pair
  (counted). CD's and CB's 12-slot look-back is inside the same span.
- **Fallback if the LT5 seal differs (declared now; R1 item 9).** (i) If the committed LT5 seal covers fewer slots than named
  above, LT6 uses exactly the slots it covers inside the named spans; the rest are genuinely missing (counted). (ii) If no LT5 seal
  is committed (q0564 or its commit fails), LT6's restore job (q0580) hashes the same spans from the data releases' `files.sha256`
  and that becomes the source of `seals/lt6_census_inputs.json`; no other day is substituted in either case. (iii) If the LT5 seal
  covers slots outside the named spans, they are not read.
- **Minimum covered days (R1 item 9; covered days = covered complete slots, or covered consecutive slot pairs for CD/CB, / 12):**
  CV >= 1.5, CK >= 1.5 (sample passes / 12), CD >= 5, CB >= 5. Below its minimum, every gate of that census is NaN and fails (the
  test drops, uncounted).
- **Release coverage (orchestrator fact, recorded here because R1 could not verify it).** Host retention deletes only files that
  are already in a verified data release with an identical sha256, and daily releases continue (`data-20261020` covers
  2026-10-18T04 .. 10-19T02). So a sealed file that has left the host is in a release by construction, unless its archive step
  failed. **Orchestrator action kept:** within 48 h of the LT5 seal commit, check that every file it names is in a release with an
  equal sha256, and archive any that are not before they rotate off.
- **The LT6 seal.** These files are off the host by the time LT6's censuses run. A restore job copies them byte for byte from the
  data releases and checks every sha256 against the source seals; `seals/lt6_census_inputs.json` then lists exactly the files
  restored with equal hashes (selection rule declared now: every file of the source seals in the spans above that a release holds).
  A source-sealed file that no release holds is **genuinely missing**, counted per slot, and never substituted; census days are
  the days actually covered (D and B project from covered interval pairs). The seal is committed before any LT6 census runs.
- **Header pre-check (before the census code is frozen; a header read, no rows):** the sealed sidecars of 10-16/17 carry
  `order_min_size` (K) and those of 10-12..10-21 carry `created_at` (B). If a field is absent, the dependent gate is NaN and fails
  (that test drops, uncounted); no other day is chosen in its place.
- **Disclosed:** J4-R's `[2026-10-16, 2026-10-21)` refusal covers maker mark-out objects only, and CB13-T's HOLDOUT
  `[2026-10-21, 2026-10-26)` is a mark-out holdout; nothing here reads a mark-out.

**Projection** = census count x 21 / census days (an estimate). Distinct events: `E_2d + (E_2d - E_day1) x 19` for two-day censuses
(LT3's rule); for CD and CB, distinct events over the covered days x 21 / days (pessimistic: no recurrence assumed beyond that).
**Effective** counts = labelled units in markets with an earlier unit of the test's population in the census days (V, K: >= 2
units). **Washout and clean classes in projections (R1 re-check):** every projected count, `n2_eff` and `VIF_w` of CD and CB is
computed after the washout of 1.7 and, for CB, the clean no-birth rule of section 5 (excluded units are not class 0). **Design
effect:** `DE_gate = max(3.0, 1 + (m_21 - 1) x 0.02, 1 + (m_co - 1) x 0.5)`, with `m_21` the projected mean
cluster size by event (LT4 14.1 item 8) and **`m_co` the size-weighted mean number of labelled units per event x capture,
`sum m^2 / sum m`** over event x capture cells with at least one labelled unit (D, B; 1 for V and K; R1 answer 12). The co-labelling
term (rho 0.5 for units labelled by the same edit or listing) and the 3.0 floor are declared now. **MDE gate formula (R1 item 5):**
`3.388 x SD x sqrt(1/n1_eff + 1/n2_eff) x sqrt(DE_gate) x 1.5 x sqrt(max(1, VIF_w))` for class contrasts (K, D, B), with `VIF_w`
the within-market (expanding-past demeaned) VIF of the class indicator on the test's controls, computed by the census (as LT5 R1
finding 4); `3.388 x SD / sqrt(n_eff) x sqrt(DE_gate) x 1.5 x sqrt(VIF_w) x gap` for V, with `max(declared, design)` (LT5
census-code check 3). A NaN `VIF_w` fails the gate. **Per-market label sums** (R1 recommended): CK, CD and CB print the
distribution of labelled units per market and the share of labelled units in markets with exactly one (counts only, no gate). Correlations marked
"within" are on expanding-past-demeaned values and bind; pooled values are printed.

| Test | Census | Gate (all must hold; NaN fails) | Values fixed into the spec |
|---|---|---|---|
| V | CV | projected units (all section 2 filters) >= 42,000 (>= 2,000 a day); both-sweep coverage >= 70% of non-sports movers; **depletion at the touch (R1 item 6): among traded units, share(toward-side 1c depth at sweep k below half its level at sweep k - 1) minus share(away-side 1c depth likewise halved) <= 20 pp** (a unit whose toward- or away-side 1c depth at sweep k - 1 is 0 is excluded from both shares and counted, R1 re-check), and (kept from the first draft, both bind) the toward-side 5c halving share <= 50%; the round's original share (toward-side 5c depth below its k - 1 level) is printed; within `|corr(zv, z v_prev)|` <= 0.5; within `|corr(zv, zh0)|` <= 0.5; within `|corr(zv, 1[traded])|` <= 0.5; within `|corr(zv, z log|x|)|` <= 0.5; `|corr(zv, log1p liquidity_k)|` <= 0.5 within and pooled; within-market IQR of `v` >= 0.1 in >= 50% of markets with >= 6 units (and >= 30 such markets); block-gate share: >= 50% of units in markets with >= 2 units in the census days (LT5's proxy for `n_m >= 16` over 21 days); **pessimistic MDE per SD x tercile gap <= 0.5c** (SD 5c, VIF_w computed) | `c_v`, `s_v`, `zv` tercile cuts and gap, `exclude_family` |
| K | CK | `ts` second-level (share of interval rows with `ts mod 60 != 0` >= 50%); `order_min_size` present in >= 90% of qualifying units; projected qualifying units >= 50,400 (>= 200 a pass); clip units >= 3% of qualifying and projected >= 8,400; clip-free projected >= 25,200; **min-size: <= 80% of would-be clip notional at <= 2 x `order_min_size`** (measured before the exclusion); round sizes: <= 70% of clip notional at multiples of 10 shares; `interval_truncated` <= 5% of sampled traded movers with >= 4 rows; within `|corr(1[clip], g_path)|`, `|corr(1[clip], fresh)|`, `|corr(1[clip], log1p n_int)|`, `|corr(1[clip], H_unsigned)|` each <= 0.5; `|corr(1[clip], log1p liquidity_k)|` <= 0.5 within and pooled; permutable share >= 50% (day, else block2); **pessimistic MDE <= 0.5c** (SD 5c, `VIF_w` of `1[clip]` on K's controls including `H_unsigned` and `g_path`) | `perm_stratum`, `exclude_family` |
| D | CD | projected later by-date interior non-sports units (section 4 primary population) >= 3,150 (>= 150 a day; the round's kill line); series roll-overs plus crypto later moves (the pinned classifier of section 5; unknown counted as crypto) <= 70% of all later non-sports interior moves (the round's second kill line); unparseable `end_date` <= 2% of captures; within `|corr(1[later], theta24)|` <= 0.5 and `|corr(1[later], x)|` <= 0.5; `|corr(1[later], log1p liquidity_k)|` <= 0.5 within and pooled; permutable share of later units >= 50%; covered days >= 5; **pessimistic MDE <= 0.5c** (SD 6c, `DE_gate` with size-weighted `m_co`, `VIF_w` of `1[later]` on D's controls including `theta24`) | `perm_stratum`, `exclude_family` |
| B | CB | projected non-recurring non-sports births in existing events >= 630 (>= 30 a day; the round's kill line) and birth units >= 3,150 (>= 150 a day); `created_at` parseable on >= 95% of newcomers; guard loss <= 20% of otherwise-formed birth units; within `|corr(1[birth], own |24 h move|)|` <= 0.5 and `|corr(1[birth], event leave-one-out |2 h move|)|` <= 0.5; `|corr(1[birth], log1p liquidity_k)|` <= 0.5 within and pooled; **crypto births (the pinned classifier of section 5; unknown counted as crypto) <= 70% of births after the non-recurring rule (R1 item 4); crypto births stay in the population**; permutable share of birth units >= 50%; covered days >= 5; **pessimistic MDE <= 0.5c** (SD 6c, `DE_gate` with size-weighted `m_co`, `VIF_w` of `1[birth]` on B's controls) | `perm_stratum`, `exclude_family`, fake-birth tercile cuts |

- **Descriptive (no gate):** every census prints the sports split, the top series family's share, the pairwise unit overlap with the
  other LT6 populations (and, for CK, with LT5 J's population definition on the same samples), and the class shares by liquidity
  tier. CV prints the toward/away halving shares for traded and quote-only movers and the distribution of `v`; CK the distribution
  of `clip_share`, `n_trains`, gap and span histograms; CD the `end_date` change counts by class, template, category and delta band,
  the ET time-of-day histogram, the `updated_at` co-occurrence share, and the earlier, overdue and roll-over counts; CB births by
  category and structure, incumbents per birth, lagged appearances and the tail share.
- **Order (cheapest kill first):** CD and CB (capture-only counts) run first; CK; CV last. A test whose census fails has its reader
  kind switched off before the code freeze of the reader.

**Census jobs (to be drafted under `docs/research_lab/queue/drafts/` in README format; ids provisional, q0580-q0585, to be checked
unused across `queue/` on every local and remote branch before drafting).**
- `q0580_lt6_census_restore` (lane `net`, about 600 MB): restore the source-sealed files of section 7 from the data releases into a
  scratch tree, check each sha256 against `seals/lt5_census_inputs_captures.json`, `seals/lt3_census_inputs_C2.json` and
  `seals/lt4_census_inputs_captures.json`, and write the restore report. Disk about 2.5-3.5 GB (estimate).
- `q0581_lt6_seal` (lane `net`, about 300 MB; after q0580): `run_live_tests6.py seal` writes `lt6_census_inputs.json` from the
  restore report (hashes of exactly the files the censuses open, by LT5's `capture_needs` rule); the orchestrator commits it.
- `q0582_lt6_census_captures` (cpu, about 1,200 MB, **`exclusive: true`**): CD, CB, then CV.
- `q0583_lt6_census_flow` (cpu, about 1,000 MB; depends on q0582): CK.
- `q0584_lt6_size_check` (cpu, 400 MB; depends on q0582 and q0583, so k is fixed before any size result exists; `max_retries 1`
  deterministic-crash retry only).
- `q0585_lt6_reader` (lane `net`, `mem_mb 480` at ladder steps 1-2, 800 at step 3, repeat; `not_before` the install time `t` of
  8.4 step 9): the installed reader (8.2).
All are DRAFT and must not be promoted before the challenger review of this file, the code and its freeze check. Each counts 0.
**Orchestrator action (not this branch; R1 recommended "seal archive within 48 h"):** within 48 h of the LT5 seal commit, confirm
that every file it names is in a data release with an equal sha256 (retention deletes only files already in a verified release, so
this checks the archive step, not retention), and archive byte for byte any that are not. A file found in no release is genuinely
missing for LT6 (counted), never substituted.

## 8. Implementation plan (no code in this commit)

### 8.1 Modules to be written (engineering list)
- `backend/astrolabe/research_lab/live_tests6_base.py`: **generated, unmodified vendored copies** (LT5's `vendor_lt5_base.py`
  pattern) of the LT3/LT4/LT5 functions LT6 uses: slot and capture scanners, `series_frame`, `move_join`, `classify`,
  `category_cols`, loaders, `outcome_h/s`, `status_codes`, `is_late`, `token0_map`, `load_sample`, `project_events`,
  `block_anchor`, `fl_perm_gate`, LT5's `block_fl_gate`, LT5 J's `path_units` (for `g_path`, `maxstep_share`), LT4's E022 depth
  helpers, E018's unsigned train share (census only), `fit`, `verdict`, `attach`, `underpowered`, `attrition`, `lee_bounds`,
  `paper_taker`, `econ`, `gross`, the `sim_*` worlds, `bd.holm`, `bd.expanding_demean`; a provenance header with each source's
  sha256 at copy time; a unit test that fails on source drift unless `vendored_source_drift_accepted` records it. Vendoring is
  done **after LT5's pin**, from LT5's pinned modules, so LT5 maintenance cannot void LT6 lines and vice versa.
- `backend/astrolabe/research_lab/live_tests6.py`: the reader. `run_once()` (internal non-blocking flock on `live_tests6/run.lock`)
  finds new complete captures, their pass's sweep 1 and active trade sample, and in order writes, write-once (`%.17g`, atomic hard
  link):
  1. `series/<capture>.csv.gz` and `status/<capture>.csv.gz` (compact: market, event, series key, neg-risk, bid, ask,
     `volume24hr`, `liquidity`, `chg_*`, `end_date`, `updated_at`, tick, `order_min_size`, `created_at`, sports flag, receipt);
     `sweeps/<pass>.csv.gz` (outcome-0 sweep-1 quote, 1c and 5c depths both sides, `book_timestamp`, receipt), kept for pass k - 1;
  2. `members/<capture>.parquet` (event id -> member set and newcomers, from `series/`; rebuildable);
  3. frozen units: `vote/frozen/<pass>.csv.gz` (V; `.nosweep`, `.noprevsweep`), `clips/frozen/<sample>.csv.gz` (K),
     `deadline/frozen/<capture>.csv.gz` (D; later and no-change by-date units), `birth/frozen/<capture>.csv.gz` (B);
  4. `<kind>/outcomes/<id>.h<j>.csv.gz` and `.s<j>.csv.gz` (status and quote at slots k + 1, k + 3, k + 12; sweep-1 quote of passes
     k + 1, k + 3);
  5. `passes.jsonl`.
  **Look-back (R1 item 10).** The first origins need slots back to `REGISTERED_UTC - 26 h` (D's and B's k - 12; V's k - 1 sweep).
  At install time `t` (within `[REGISTERED_UTC - 72 h, REGISTERED_UTC - 24 h]`, 8.4), `backfill-series` writes `series/` and
  `sweeps/` as `lookback` lines for every needed slot that started before `t` (host originals; all at most 3 days old then); **the
  installed reader writes `lookback` lines for every capture and sweep that arrives in `[t, REGISTERED_UTC)`, as it arrives**.
  `lookback` lines are never units. A needed slot found by neither is `lookback_missing` (counted per slot and per affected unit),
  never imputed or restored from a later file. Labelled events (edits, births) seen in `lookback` lines mark the washout of 1.7
  for the first window units (stricter: a pre-window event can only remove units). A kind not in `k_tests` is switched off.
- `backend/astrolabe/research_lab/live_tests6_analysis.py`: the single analysis (1.7-1.10, Holm over k, counting) and the size check
  (1.8, 1.8.1) with the scenario-to-test map (fail-closed on an unknown or missing scenario).
- `backend/scripts/run_live_tests6.py`: `run`, `backfill-series`, `ops-stats`, `seal`, `census-captures`, `census-flow`,
  `size-check`, `analyze`; censuses accept `--data-dumps-cap-gb` and exit 75 above it; `size-check` refuses `--worlds/--draws`
  without `--dev`.
- Spec `backend/astrolabe/research_lab/model_specs/live_tests6_v1.json`: every constant, k, seeds (estimators 20261161-64, gates
  20261261-64, B's fake birth 20261364, size check 20261167), dates, census scales, cuts and rules, the template classifier, the
  `code_sha256` map (the three LT6 modules plus every hashed dependency, as LT5's eleven files) and the imported sports-rule hash.
- `battery2.KIND_RULES["live_tests6"]` (fail-closed counting entry).

### 8.2 Resources, collection plan and install
- **No new collector and no network.** A pure reader of the pass's own outputs, once a pass.
- **Memory (R1 item 11).** **The planning reference is LT3's measured host peak, 534 MB** (a 40-item backlog pass; 318-343 MB
  steady), not a lighter estimate: LT6 reads per pass at least what LT3 reads (two captures' selected columns, a sidecar, two sweeps'
  outcome-0 rows, one trade sample with the train search, and its targets' quotes). Planning: **peak 450-650 MB in a backlog pass,
  330-450 MB steady** (estimates; the earlier "300-420 MB" is withdrawn). So `mem_mb 480` is **not** assumed to hold; a declared
  ladder decides, each step measured by a host dry run with the exact command before the pin (no pin on an unmeasured reader):
  1. one reader, `--max-items 2` (one pass plus one of catch-up per run, which bounds the backlog), column projection, `ulimit -v
     983040`: accepted if peak RSS <= 450 MB, installed as `q0585` at `mem_mb 480` on the `net` lane;
  2. else **two readers** at the same cadence (sample-side K; capture/sweep-side V, D, B), serialised by one shared `flock` so they
     never run concurrently, each `--max-items 2`: accepted if each peaks <= 450 MB, both at `mem_mb 480`;
  3. **final fallback:** one reader at `mem_mb 800`, `ulimit -v 1572864`, `net` lane. It loses the queue's blackout exemption
     (starts blocked 02:45-05:30Z), so the 02:31Z pass is read after its freeze deadline (04:31Z) every day: about one pass in
     twelve of V and K origins and of D and B captures is lost as `.late`, **counted, never re-read**, and the *late-loss* label
     applies above 2%. This consequence is declared now, so choosing step 3 changes no rule. **The censuses run before the step
     is chosen, so their projections ignore this loss; the late-loss is not re-projected and applies automatically** (counted,
     labelled). **A `.late` pass still writes its `series/` and `sweeps/` lines** (write-once, before any unit work), so the next
     pass's k - 1 inputs survive; only its own units are lost.
  4. **If step 3's dry run also fails, there is no pin and LT6 is not registered** (recorded in the ledger; no further variant).
- **Install (steps 1-2 above): queue job `q0585` on the `net` lane, `mem_mb 480`, repeat, once a pass**, keeping the queue's
  blackout exemption (< 500 MB), so the 02:31 and 04:31 passes are read in time. Reason for the `net` lane: LT3's (a 21-day `cpu` job
  would block every `cpu` job). Alternative: host cron `45 1-23/2 * * *` (74 min after the pass start; after LT5's `:35`), own
  `flock`, `nice -n 19`, `oom_score_adj 1000`. **Never both.** Every freeze deadline (the next slot's start) is then at least 45
  min away; a pass whose sweep or sample is not complete by its deadline loses its V or K units as `.late`.
- **CPU:** about 1-2 min a steady pass (estimate; the train search is a sort and group over at most 2,000 x 500 rows).
- **Disk:** about 0.8-1.2 GB over the window (estimate); the reader stops writing at 1.5 GB in `live_tests6/`.
- **Host change:** installing the job is a host change under the standing collection authorisation, done by the orchestrator. The
  planning figures do not assume the host resize to 2 OCPU / 12 GB (scheduled 2026-10-22); if it is done, they stand.

### 8.3 Tests to be written (`backend/tests/unit/test_research_lab_live_tests6.py`, synthetic only)
- V: orientation of `imb` and `v` for rises and falls; `v_prev` from the k - 1 sweep; toward/away sides; `h0`; both-sweep
  requirement and `.noprevsweep`; the skip target from passes k + 1 and k + 3 with the joint mask.
- K: the declared greedy train algorithm, one test per branch (skip a `< 2 s` row, skip a repeated `tx_hash`, append on the first
  gap, append inside and close outside the running-median band, close on the 30-minute span, restart at `i + 1` after a short run,
  restart after a train, no overlaps); size keys from API strings (`"10"`, `"10.0"`, `"1E+1"` equal; `"10.000001"` not), min-size
  exclusion from `order_min_size`, `clip_share`, rows at or after `t_k` ignored, interval coverage, the near-identical placebo
  grouping, `g_path` equal to LT5 J's on the same rows.
- D: the ET template classifier across the 2026-11-01 DST change, later / no-change / earlier / under-1 h classes, roll-over and
  overdue exclusions, `theta24`, an unparseable or date-only `end_date` never equal, the washout, the old-end >= 7 d subset.
- B: newcomer detection (present at k, absent at k - 1, `created_at` in the interval), lagged appearance, existing and
  non-recurring rules, the 5 s guard, several newcomers as one birth, the no-birth class excluding lagged appearances and washout
  units, the pinned crypto classifier (substring, casefold, unknown cases counted as crypto, the no-`crypto`-value fail-safe), the fake-birth draw is seeded, at least 12 slots from a real birth and in the real birth's
  tercile.
- Shared: causality (future captures, sweeps and samples with wild prices leave every frozen line byte-identical); late refusal,
  write-once; dry-run guard; `%.17g` round trip; run lock; `ops-stats` reads no price column; vendored provenance and drift;
  counting equals k; Holm; the p = max rule and, for D and B, the `G_treated - 1` event t; the both-demeaned sensitivity; the
  analysis refuses before the date, an unpinned, null or NaN spec, or a `k_tests` naming a dropped test; V's registration refused if
  the pin is not before `T_E022`, the earlier of E022's analysis job start (the queue log's start time) and E022's analysis commit (a test for each of the two times), and V's first origin after E022's `END_UTC` (k - 1 inputs); sealed censuses (counts only,
  tampering refused, completeness, minimum covered days); each MDE gate formula with size-weighted `m_co` and `VIF_w`; `lookback`
  lines written by the running reader before `REGISTERED_UTC` never become units; the size check on small runs with planted effects, the
  scenario-to-test map and the rule that a failing scenario sets only its own tests to "SE check failed" with k unchanged; an
  end-to-end synthetic analysis with a reduced `k_tests`.

### 8.4 Registration steps and pins (in order)
1. Challenger R1 on this file; fixes applied in a response section; re-check if required.
2. q0580 restore, q0581 seal, seal committed and pulled on the host.
3. Code (8.1, 8.3); a `science-reviewer` freeze check of the census and size-check code against sections 1.8, 1.8.1 and 7; fixes.
4. Censuses q0582, q0583 (counts only); drops recorded in 6.3; `k_tests`, scales, cuts and `perm_stratum` values filled.
5. Size check q0584 (2,000 worlds x 200 draws, seed 20261167, binding map of 1.8); results recorded per test.
6. Reader freeze check; host dry run with the exact install command, following the memory ladder of 8.2 (the step used is
   recorded).
7. LT5's registration commit exists; **E022's registration commit or its recorded drop exists** (so `REGISTERED_UTC` and V's first
   origin can be computed from E022's `END_UTC`); the engine embargo entries of section 9 are applied in `config.EMBARGO` before
   acceptance; the CB18 request of the section 14 annex is filed with CB18's owner (applied or not, recorded).
8. Pins: `SPEC_SHA256`, `code_sha256` map, `code_check` passing; E-numbers assigned from the ledger; the ledger entry is the
   registration commit, **before `T_E022`, the earlier of E022's analysis job start (the queue log's start time) and E022's analysis commit** (V's condition; else V is dropped first) and at least 24 h before `REGISTERED_UTC`.
9. Install q0585 and run `backfill-series` within `[REGISTERED_UTC - 72 h, REGISTERED_UTC - 24 h]`; verify `pinned: true` and
   `nothing_new` before `REGISTERED_UTC`; queue the analysis job with `not_before` the analysis date.

## 9. Signal-engine mapping and embargo requests

Every family below is point-in-time from the origin capture, its pass's sweeps and trade sample, or the engine's own earlier
`quotes/` files (DESIGN_V1 16 causality). Each is an **auxiliary family** (own write-once table and version string; the v1 store is
never rewritten). **Embargo first** (DESIGN_V1 8): any challenger that isolates one of these families carries its token until LT6's
analysis date, proposed **2026-12-09T00:00Z** (moved later if LT6's window moves; never earlier), from the day LT6's design is
accepted.

| Test | Family (aux version) | Columns (NaN = missing) | Source and clock | Embargo token -> until |
|---|---|---|---|---|
| V | `vote` (`se-aux-vote-v1`) | `vt_vote_5c = sign(own 2 h change) x imb_5c`, `vt_vote_prev_5c`, `vt_dspread_2h`, `vt_toward_lr`, `vt_away_lr` | sweep 1 of the pass and the previous pass | `vote` (new) -> 2026-12-09; **`book` -> 2026-12-09 (from 2026-11-22), required before acceptance** |
| K | `clips` (`se-aux-clips-v1`) | `cl_clip_share_2h`, `cl_n_trains_2h`, `cl_last_clip_age` | the pass's trade sample, rows `ts < t_k` | `clips` (new) -> 2026-12-09 |
| D | `deadline` (`se-aux-deadline-v1`) | `dl_end_date_delta_24h` (hours, signed), `dl_end_date_r`, `dl_bydate_template` | the origin rows and the previous 12 slots | `deadline` (new) -> 2026-12-09 |
| B | `siblings` (`se-aux-siblings-v1`) | `sb_siblings_born_24h`, `sb_event_members_delta_7d` | the capture listing and earlier `quotes/` | `siblings` (new) -> 2026-12-09 |

**Requests to the signal-engine track (this branch does not edit engine code; `config.EMBARGO` is not edited here).**
- `book` to **2026-12-09T00:00Z** (from 2026-11-22, which covers LT5 R and H). Reason: a book-isolating LightGBM model with the own
  2 h change and the 5c imbalance can learn `sign(x) x imb` on `dir_2h`, a development look at V before its analysis. **Cost,
  disclosed:** the engine's `book` family stays hidden 17 days longer. LT6's acceptance is conditional on this entry.
- New tokens `vote`, `clips`, `deadline`, `siblings` to 2026-12-09, entered by whoever first builds an isolating challenger, before
  it is scored.
- **Also (R1 recommended):** any flow-family feature built from print sizes by count (for example repeated-size counts, size
  mode shares) carries `clips` as well as `flow`; any revision of `se5_tte` (or another `tte` model) that adds an `end_date`-change
  or revision column carries `deadline`. **All dates here slide with E022's `END_UTC` (1.1)**, later, never earlier.
- The existing `event` token (2026-11-22, LT5 F) is **not** extended: se8/se10's event features are levels (event size, overround,
  sibling changes), not a membership change, and B's primary target (an absolute move) is not an engine target. B's signed
  secondary is covered by `siblings`.
- The engine-first `overdue` family (CH189) shares D's template classifier; it needs no LT6 token (overdue extensions are outside
  D's primary), disclosed.
- **Disclosed (as LT5):** broad multi-family models and the champion are not embargoed; LT6 asks the engine track not to add an LT6
  family to a broad model before 2026-12-09, or to record such a model in the ledger as a development look.

The engine's yardstick (log-loss gain under `se-promotion-v1`) is a different question from each LT6 primary. A Supported LT6
primary makes its family a candidate; an engine gain never changes an LT6 verdict and an LT6 verdict never promotes a model.

## 10. Disclosures

- **Selection history.** The four tests are round 11's ranks 6-9 (Fable xhigh creative pass, written 2026-10-21 on `cee77db6`, from
  round 9/10 probes, LT3/LT4 census figures, the cost model, the maker-rewards snapshot, WS1 and the engine coverage note, with no
  host probe). LT5 took ranks 1-5 and declined these four with reasons (section 6.2). Every design change here (6.1) was made
  before any data.
- **The designer** read the round-11 file (sections 0, 0.1, 2.D, 3), `LIVE_TESTS_5.md` (all sections including R1, re-check and
  census-code check), `LIVE_TESTS_4.md` (sections 0-1, 4 and the R1 table), `LIVE_TESTS_3.md` (E018), `LIVE_TESTS_COPY.md`
  (sections 10, 13), `CREATIVE_BATCH_18.md` (sections 0 and 4.1), the ledger by bounded grep (E003, E018, E022, LT3/E026
  registrations, CB17/CB18 entries; no entry for CH69, CH111, CH148, CH22, CH67 or any deadline/listing test), the checkpoint's
  next-actions section, `signal_engine/CANDIDATES.md` (embargo section, C11) and `NEW_STREAMS_2026-10-19.md` (gamma-rules lines).
  No data, host, outcome, price after an origin, P&L, `data-dumps` file or evidence JSON was read. No code was written.
- **Closest prior AREPO tests.** V: E003, E022, E020, LT5 R, CB17-B2, CH39, CH92, CH147. K: E018 (dropped), LT5 J, E021, CB18-R,
  round 8's cross-event baskets (dead; a different object). D: round 7's parked item, CB18-S (silent edits; reports an `end_date`
  class), CH08/CH177, CH62/CH189, CH01/CH04. B: CH22/CH142/CH154 (the newcomer), CH67 (the leaver), CH56, CH10/CH11, se8/se10.
- **Mechanics stated up front.** V: depletion of the hit side and microprice (skip target, `v_prev`, M3, depletion gate). K: round-
  dollar coincidences and min-size bots (exact size with regular gaps, min-size exclusion, round-size control and gate, the near-
  identical placebo); more rows mean more chances of a train (`log1p n_int` control and gate). D: time decay (the `theta24`
  control, a model-based assumption of a constant hazard, disclosed as such), co-occurring text edits (`updated_at` flag; the
  gamma-rules stream is not read), event-wide edits (co-labelling DE). B: volatility clustering (prior-move controls, the fake birth),
  routine listings (non-recurring rule), co-labelling (DE).
- **Rare events.** D and B depart from round 11's rule 1 (no rare events); they are kept only behind counts-only kill lines, and
  their inference uses the treated-cluster count (1.7) because few events carry a label.
- **D's `theta24`** is a survivor-conditional, model-based drift (section 4). **D may be *partially seen*** through CB18-S's
  `end_date`-class print (1.6, the section 14 annex).
- **Shared data.** LT2-LT5, E011, CB17, CB18, E025, E026 and the engine read the same captures, sweeps and samples. Overlap only.
- **Window.** LT6's results arrive about 2026-12-08, later than a window starting in early November would give; the reasons are in
  1.1 (V's disjointness, host reader slots, election week).

## 11. Open questions for the challenger review

*(Answered by R1; see section 14.3. Kept as the record.)*

1. **V and E022.** Is temporal disjointness (V's origins at or after LT4's `END_UTC`) plus a pin before E022's analysis (else V
   drops) an adequate reading of LT5's deferral, or must V wait for E022's analysis? Should the whole family wait for 11-16 (one
   window, proposed), or should K, D and B start about 11-04 with V on 11-16 (two windows, election week inside)?
2. **V's target and labels.** Is the sweep skip `c_vskip` enough to remove the microprice mechanics, and is the depletion
   decomposition (M3) the right binding label? Is the census halving rule (toward-side depth below half its k - 1 level in <= 50%
   of traded units) a meaningful kill line?
3. **V's gate.** Block (circular-shift) Freedman-Lane (declared, conservative) or the plain gate with AR scenarios? `v` multiplies
   the imbalance by the move's sign, which should lower its persistence.
4. **K and the trains rule.** With arm 2 removed and a sign-free size-identity state, is K far enough from E018 and round 11's
   "no trains" rule? Is the within-market `|corr(1[clip], H_unsigned)| <= 0.5` gate the right separation check?
5. **K's cut and target.** Is `clip_share >= 0.25` (changed from 0.5, before data, for power) acceptable? The skip target does not
   test algorithms that finish inside the first pass: acceptable as a declared narrowing?
6. **K's train rule.** Exact share size versus notional identity (S3); the 2 s minimum gap; distinct `tx_hash`; the [0.5, 1.5]
   median-gap band; the 30-minute span. Any change should be made now.
7. **D and B against round 11's rule 1.** Keep both as census-first (the census is the map, k = 0 if it fails) or drop them now? The
   gamma-rules churn probe points to D failing.
8. **D's time-decay control.** Is the constant-hazard `theta24` acceptable, or should D instead restrict to markets with at least
   7 days to the old end, where decay is small?
9. **D's template classifier** fixed now (ET 23:59 or 00:00 within a minute) rather than census-fixed from the histogram:
   acceptable?
10. **B's target and floor.** The absolute 22 h move with the LT 0.5c floor, or CB18-S's 1.0c floor for the same kind of target?
11. **B's birth definition** (`created_at` in the interval, existing event with >= 2 members, non-recurring, 5 s guard) and the
    fake-birth placebo: adequate?
12. **Co-labelling design effect** `1 + (m_co - 1) x 0.5` for D and B: is rho 0.5 right, and should the census floor be higher than
    3.0 for these two?
13. **CB18-S overlap.** CB18 reports an `end_date`-change class (unsigned 24 h move) on REP_18 origins (to 11-24) that overlap D's
    window for arm-1 events. Ask CB18 to compute that secondary only on origins before 2026-11-16 (or after LT6's analysis), or
    accept it as a disclosed partial look at D's maker secondary S3 (not D's signed primary)?
14. **Census inputs.** Reusing LT5's sealed capture days (10-12..10-21) and LT3 C2's samples (10-16/17), restored from releases;
    the risk that some files are in no release (then missing, counted). Acceptable, or must every LT6 census use one set of days?
15. **Window length.** 21 days fixed, no extension, Thanksgiving inside: agree?
16. **Reader.** Queue `net` lane at `mem_mb 480` with a 450 MB dry-run acceptance and a pre-declared split, versus cron: agree?
17. **Holm and k.** k <= 4 set by the censuses alone, no replacement test, with D likely and K or B possibly dropping: acceptable?
18. **Engine cost.** Extending `book` to 2026-12-09 keeps the engine's book family hidden 17 more days: acceptable, or should V's
    shadow be handled by a narrower token on the interaction only (which would leave se3-type models visible)?

## 12. Draft ledger block (DRAFT, not registered, not counted)

> ## LT6 (four round-11 candidates, ranks 6-9) — DRAFT pre-registration (not registered, nothing counted, no code)
> - **Design:** `docs/research_lab/LIVE_TESTS_6.md` on `feat/live-tests-6`. Pure reader of streams the host already writes
>   (complete captures, sidecar, sweep 1 of passes k - 1 .. k + 3, active trade samples); no network, no new collector; memory
>   planned from LT3's measured 534 MB peak with a declared three-step ladder (one reader <= 450 MB at `mem_mb 480`; two serialised
>   readers; final fallback `mem_mb 800` with the 02:31Z pass lost as `.late`, counted); separate store `live_tests6/`; LT3-LT5
>   functions vendored after LT5's pin.
> - **V** (CH190) makers' vote: slope of the sweep skip continuation (k + 1 to k + 3) on the post-move aligned 5c skew, pre-move skew
>   held fixed, non-sports movers, > 0; block Freedman-Lane gate; tercile MDE 0.17-0.40c vs 0.5c; first origin after **E022's**
>   `END_UTC` (k - 1 inputs; E022's `dimb` = -v), pinned before `T_E022` (the earlier of E022's analysis job start and its analysis commit) or dropped; depletion gate on the 1c touch
>   (toward minus away halving <= 20 pp).
> - **K** (CH185) clip trains by size identity (declared greedy algorithm, API-string sizes): clip (share >= 0.25) minus clip-free,
>   skip target, all categories, > 0; `H_unsigned` a control; MDE 0.32-1.2c; may drop. Arm 2 (`side`) and the monitor arm removed.
> - **D** (CH187) deadline moves: later `end_date` on by-date templates, 22 h YES change from k + 1, time decay held fixed, washout,
>   > 0; MDE 0.43-0.99c; very likely to drop at its census; *partially seen* unless CB18 withholds its `end_date`-class print.
> - **B** (CH188) sibling birth: incumbents' absolute 22 h move after a non-recurring listing in their event (clean no-birth class,
>   crypto gate, washout), > 0; binding volatility-clustering size world; material label 1.0c; MDE 0.33-0.99c; may drop.
> - **Family:** Holm over k <= 4 (census-fixed), one-sided, alpha 0.05; p = max(event t, two-way, day t), with the event t on
>   `G_treated - 1` df for D and B; Freedman-Lane gates (V: block circular-shift, minimum 16 units per market); size check 11 binding
>   scenarios (one non-binding, plus reported analytic-p rates and planted-effect power), a failure sets only its own tests to p = 1;
>   class MDE gates carry `sqrt(max(1, VIF_w))`; window proposed `[2026-11-16T00:00Z, 2026-12-07T00:00Z)` keyed to E022's `END_UTC`
>   (the family slides with E022), single analysis on or after 2026-12-08T12:00Z; register after LT5 and after E022's registration
>   or drop, from 2026-11-01.
> - **R1 (2026-10-21):** REVISE (V, K, D ACCEPT_WITH_CHANGES; B REVISE; 12 required); answered in section 14; re-check pending.
> - **Status:** DRAFT awaiting the R1 re-check, restore and seal (q0580-q0581; LT5 seal sha256 to be filled), code and freeze check,
>   censuses (q0582-q0583), size check (q0584), dry run, engine embargo entries (`book` to 2026-12-09; new `vote`, `clips`,
>   `deadline`, `siblings`), the CB18 request, pins and registration. E-numbers not assigned (E026 last used).

## 13. Proposed registry entry (stage "designed"; `registry.json` is not edited here)

```json
{
 "id": "LT6",
 "title": "Live tests from round 11, second group (planned)",
 "plain": "A sixth group of up to four live tests from the latest new-ideas round. It asks whether the order book that re-forms after a price move shows which moves will hold, whether repeated identical-size trades (a sign of a trading program slicing a big order) mean a move keeps going, whether a market drifts after the venue quietly pushes its deadline later, and whether a new market listed in an event makes its existing markets move more. Paper rules only; nothing is traded. Counting checks decide which tests go ahead; the deadline test is expected to drop.",
 "batch": "LT6",
 "family": "mixed",
 "stage": "designed",
 "status": "draft",
 "verdict": "pending",
 "effect": null,
 "next": "Short re-check of the answers to the challenger review, then code, counting checks and a size check; registration from 1 Nov 2026; collection planned 16 Nov to 7 Dec 2026 (moves later if a linked earlier test slips), single analysis after 8 Dec 2026",
 "next_date": "2026-11-01",
 "candidate": false,
 "sources": {
  "verdict": "docs/research_lab/LIVE_TESTS_6.md (DRAFT)",
  "next": "docs/research_lab/LIVE_TESTS_6.md sections 1.1, 7, 8.4 and 14"
 },
 "stage_results": {
  "designed": "pending"
 },
 "reached": []
}
```

## 14. Challenger R1 response (2026-10-21; `reviews/LT6_CHALLENGER_R1_2026-10-21.md`, REVISE; governs where any earlier text differs)

Design only, before any census, size run, seal or window data; nothing was chosen from data. **No threshold, floor, alpha, seed or
direction was loosened.** Every change narrows a population, adds a control, a cluster rule, a gate, a scenario, a label or a
disclosure, or makes a rule exact. Where a finding left a choice, the stricter option was taken and the reason is given. The
changes are applied in sections 0-13; where any text differs, this section governs.

### 14.1 Required changes mapped to edits

| # | Finding | Change | Where | Reason for the choice |
|---|---|---|---|---|
| 1 | Few treated clusters (D, B): CR1 over all `G_event` over-rejects with about 150 labelled events | For D and B, **p = max(p_event on t with `G_treated - 1` df, p_two-way, p_day t)**; the event CI uses the same df. The size check **reports** the analytic rule's rejection rate in scenarios 6, 7 and 11 at 0.0125 and 0.05; above its limit the result carries *analytic p oversized in simulation* | 1.7, 1.8, 1.9, 4, 5 | As required; the reported rate is a label, not a second binding size statement (14.3) |
| 2 | B needs a volatility-clustering size world | **Scenario 11 (binding for B):** stochastic volatility (AR 0.95, event-shared component), birth hazard rising with the event's current volatility, the primary's prior-|move| controls in the model, absolute target, no birth effect; failure gives B "SE check failed (size scenario)", p = 1, k unchanged | 1.8, 1.8.1, 5 | The market x day permutation does not keep intra-day timing; the world tests the gate where B is most exposed |
| 3 | B control-class contamination | **No-birth** = no newcomer **and no lagged appearance** in the event at k, and not in the washout; lagged-appearance-only, guard-loss, unparseable-`created_at`, recurring-newcomer and washout units are **excluded and counted by reason**, never class 0 | 5, 8.3 | As required |
| 4 | B crypto exclusion | **A census gate only, with the pinned classifier** (section 5: `fee_category` contains `crypto` after strip and casefold; missing, empty or `sports = -1` is unknown, counted, and counted as crypto; a fail-safe if no sealed value contains `crypto`): crypto births <= 70% of births after the non-recurring rule; **crypto births stay in the population**; the series-family rule still applies (classifier pinned by the R1 re-check) | 5, 7 | The finding offered a category rule or a gate; the first draft of this response cited an undefined "D's rule". The gate with an explicit classifier is taken; unknowns count against the gate |
| 5 | MDE gates omit VIF (K, D, B) | Class gates multiply by **`sqrt(max(1, VIF_w))`**, `VIF_w` the within-market VIF of the class indicator on the test's controls (K with `H_unsigned` and `g_path`; D with `theta24`); a NaN `VIF_w` fails | 7 | As LT5 R1 finding 4 |
| 6 | V depletion kill line | **Binding:** share(toward-side **1c** depth halved, sweep k vs k - 1) minus share(away-side 1c depth halved), among traded movers, **<= 20 pp**. The first draft's toward-side 5c halving <= 50% is **kept as a second binding gate**; the round's original share is printed | 7 | The asymmetry is the mechanical channel; keeping the earlier gate as well can only remove V, never rescue it |
| 7 | V / E022 boundary; LT4 unregistered | **Everything is keyed to E022's own registration and `END_UTC`:** `REGISTERED_UTC >=` E022's `END_UTC`; **V's first origin is the first pass whose k - 1 capture and k - 1 sweep start at or after E022's `END_UTC`** (11-16T02:31Z as proposed; the 00:31Z pass counted as `e022_boundary`); LT6 registers only after E022's registration or its recorded drop; V is pinned **before `T_E022`, the earlier of E022's analysis job start (the queue log's start time) and E022's analysis commit** or dropped (wording fixed by the R1 re-check); **the whole family (window, analysis, embargo dates) slides if E022 slides**; if E022 is dropped, the E022 conditions lapse and the 11-16 floor alone applies | 0, 1.1, 1.11, 2, 8.3, 8.4, 9 | LT4's censuses (q0482/q0483) are only queued; tying LT6 to E022's actual dates is the only rule that stays correct whatever LT4 does |
| 8 | CB18 can look at D | (a) No LT6 designer, coder or reviewer reads CB18's `end_date`-class output (or CB18-S results) before LT6's pin, and **D's text is frozen at the R1-accepted text** (later changes only by census-fixed values); a breach is recorded and labels D. (b) A withholding **change request to CB18's owner** (annex 14.6), filed before the pin, not edited here; **unless it is applied before the pin, D carries *partially seen*** | 1.6, 1.9, 1.11, 8.4, 10, 14.6 | CB18 is another owner's design; LT6 can request, not edit. The label applies to D as a whole (stricter than S3 only) and never changes a verdict |
| 9 | Seal dependency | `seals/lt5_census_inputs_captures.json` is not committed yet (q0564 writes it after 2026-10-21T23:20Z): **its sha256 is to be filled from the committed seal**. **Fallback:** (i) fewer slots: use exactly those inside the named spans; (ii) no LT5 seal: q0580 hashes the same spans from the releases' `files.sha256`; (iii) extra slots: not read; never another day. **Minimum covered days:** CV >= 1.5, CK >= 1.5, CD >= 5, CB >= 5, else that census's gates are NaN and fail. **Release coverage:** retention deletes only files already in a verified release with an identical sha256, and daily releases continue (`data-20261020` covers 10-18T04 .. 10-19T02); the 48 h archive check stays an orchestrator action | 7 | As required |
| 10 | Look-back timing | `backfill-series` covers needed slots that started before the install time `t`; **the installed reader writes `lookback` lines for every capture and sweep arriving in `[t, REGISTERED_UTC)` as it arrives**; a slot found by neither is `lookback_missing` (counted); pre-window labelled events mark the washout | 8.1, 8.3 | As required; the washout use can only remove units |
| 11 | Memory plan | Planning from **LT3's measured 534 MB peak** (450-650 MB backlog, 330-450 MB steady; the 300-420 MB figure withdrawn); a declared ladder, each step dry-run measured: one reader <= 450 MB at `mem_mb 480`; else two readers serialised by one `flock`, each <= 450 MB; **final fallback** one reader at `mem_mb 800`, losing the blackout exemption, so the 02:31Z pass is `.late` every day (about 1 in 12), **counted, never re-read**, *late-loss* above 2% | 8.2, 7 (q0585), 12 | Declaring the consequence now means the step finally used changes no rule |
| 12 | K train rule ambiguous | A **declared deterministic greedy algorithm** (per (asset, size key) group, rows sorted by (`ts`, `tx_hash`); skip `< 2 s` rows and repeated `tx_hash`; the first gap any within the 30-minute span; later gaps within `[0.5, 1.5] x` the running median of the run's gaps; close on a band or span break; a closed run of >= 3 is a train and the next run starts after it; a shorter run restarts at `i + 1`; no overlaps); **sizes compared as `Decimal(API string).normalize()`**; unit tests for every branch | 3, 8.3 | As required |

### 14.2 Recommended items adopted
- **Washout** (D, B): class-0 units in slots k + 1 .. k + 11 after a labelled unit of the same market are excluded, counted (1.7,
  4, 5); pre-window events seen in look-back lines count (8.1).
- **Planted-effect power run** for D and B (0.5c and 1.0c, 500 worlds each), reported, **non-binding** (1.8).
- **Both-demeaned sensitivity** in the analysis, never changes a verdict; **per-market label sums** printed by CK, CD and CB, counts
  only (1.7, 7); **non-binding scenario 12** with label incidence correlated with the market's level (1.8, 1.8.1).
- **`theta24` disclosed** as a survivor-conditional, model-based drift (4, 10).
- **`H_unsigned` as a K control** on K's own 2 h interval rows, kept also as a census gate (3, 7).
- **B's material label at 1.0c** (CB18-S's floor for an absolute 24 h move); the census MDE gate stays at 0.5c (1.9, 5).
- **Size-weighted cluster size** `m_co = sum m^2 / sum m` in the co-labelling DE; the 3.0 floor kept (7).
- **D's old-end >= 7 d reported subset** (S0) (4).
- **Maker horizons:** `|mid_{k+1} - mid_k|` over the widened pass reported beside `y22` (D S3) and `a22` (B S3).
- **Engine:** size-by-count flow features carry `clips`; a `tte` revision column carries `deadline` (9).
- **Seal archive within 48 h** as an orchestrator action (7).
- From the answers: the Thanksgiving-excluded sensitivity (1.1); fake births matched on the event's leave-one-out `|2 h|` tercile
  (5); `end_date` parse rules pinned (4).

### 14.3 Not adopted, or adopted differently, and why
- **The analytic-p rejection rates and the power runs are not binding.** In LT3-LT5 the binding size statement is the gate's. A
  simulated power run that could drop a test after the code exists would be a new power gate chosen late; the census MDE gate is
  the declared one. The rates are reported and attach a label.
- **V's earlier 5c halving gate is kept beside the new 1c asymmetry gate** (the review suggested replacing it). Keeping both is
  stricter.
- **B's crypto rule:** the gate only, with the pinned classifier (section 5); crypto births stay in the population (corrected by the
  R1 re-check: the earlier wording claimed a category rule that was not defined).
- **The 3.388 multiplier is kept** (`t_{20,0.99} + t_{20,0.8}`, LT4 section 2; the k = 5 worst case). For k <= 4 it overstates the
  MDE against about 3.08, so it is conservative.
- **A split window** is not adopted (the review agreed: one window from 11-16, now keyed to E022).
- Nothing else in the review was refused.

### 14.4 Rulings on section 11, adopted
1 one window, keyed to E022 (item 7). 2 skip target kept; M3 stays a binding label; depletion gate per item 6. 3 block gate kept.
4 K is distinct from E018; `H_unsigned` is a control and a gate. 5 `clip_share >= 0.25` kept, 0.5 as S2. 6 exact size by string
(Decimal-normalised), 2 s minimum gap, distinct `tx_hash`, 30-minute span, band per item 12. 7 D and B stay census-first with items
1-4 and 9. 8 `theta24` and `log T` kept; old-end >= 7 d subset added. 9 fixed classifier kept; parse rules pinned. 10 B's census
gate stays 0.5c, its material label 1.0c. 11 adequate after items 3-4; fake births tercile-matched. 12 rho 0.5 kept with the
size-weighted cluster size; floor 3.0 kept. 13 item 8. 14 acceptable with item 9. 15 21 days, no extension; Thanksgiving-excluded
sensitivity only. 16 `net` lane, with the item 11 ladder. 17 k by census alone. 18 `book` extended to 2026-12-09 (slides with
E022).

### 14.5 Not resolved here (for the orchestrator)
- **The LT5 seal's sha256** (q0564, after 2026-10-21T23:20Z) is to be written into section 7 when the seal is committed.
- **E022's status.** LT4's censuses q0482/q0483 run today; E022's registration or drop, and its actual `END_UTC` and analysis
  commit, set LT6's dates and V's freeze condition.
- **The CB18 request** (14.6) must be filed with CB18's owner before LT6's pin; its outcome decides D's *partially seen* label.
- **The engine embargo entries** of section 9 are outside this branch; LT6's acceptance waits for them.
- **Release coverage** of the LT5-sealed files is an orchestrator check within 48 h of the seal commit.
- **Whether scenario 11 holds size for B** is unknown until q0584 runs, after the censuses and the code freeze; no preliminary run
  at seed 20261167 will be made.
- **D remains very likely to drop** at its census, and **B is now harder to keep** (a clean no-birth class, a crypto gate, a VIF
  term in its gate, a binding volatility world). Both are recorded now so that their drops, if they come, are not read as news.

### 14.6 Annex: change request to CB18's owner (filed separately; not an edit of `CREATIVE_BATCH_18.md`)

> **To:** the owner of CB18 (`CREATIVE_BATCH_18.md`, branch `feat/cb18`). **From:** LT6 design (`LIVE_TESTS_6.md`). **Date:**
> 2026-10-21.
>
> **Request.** In CB18-S (section 4.1), the reported `end_date`-change class (any target, move, spread, exit or regression output
> for units whose `end_date` changed between captures k - 1 and k) is **not computed or printed for REP_18 origins at or after
> 2026-11-16T00:00Z** (or LT6's `REGISTERED_UTC`, if later) **until 2026-12-08T12:00Z** (LT6's analysis date, or later if LT6's
> window slides with E022). Counts of such units may be printed. SCREEN_18's `end_date`-class output (origins before 11-10) is not
> affected, but it is not shown to LT6's designer, coder or reviewers before LT6's pin.
>
> **Why.** LT6's D (CH187) tests the YES drift after a later `end_date` on by-date markets. REP_18's arm-1 origins of 11-16 .. 11-24
> overlap D's window; CB18's print on that class would be a development look at D's object (its unsigned maker secondary) before
> D's single analysis.
>
> **Cost to CB18.** One uncounted, reported secondary is delayed by about two weeks on part of REP_18. No CB18 counted test,
> threshold, window, population or verdict changes.
>
> **Record.** CB18 records in its file and in the ledger whether the request was applied, before LT6's pin. **If it is not applied
> before LT6's pin, LT6's D carries the label *partially seen (CB18 `end_date` class)* at analysis**; D's verdict rule is unchanged.

## 15. R1 re-check response (2026-10-21; `reviews/LT6_R1_RECHECK_2026-10-21.md`, R1_RESPONSE_INCOMPLETE; governs where any earlier text differs)

Text only; nothing was chosen from data; nothing was loosened. Both required items and every note are applied in sections 0-14.

| # | Re-check item | Change | Where |
|---|---|---|---|
| R1 | **V's freeze condition was loosened** from "analysis runs" to "analysis commit" | The condition is now, in the same words everywhere: **before `T_E022`, the earlier of E022's analysis job start (the queue log's start time) and E022's analysis commit**. The unit test refuses a pin after either time (one test for each) | 0, 1.1, 1.11, 6.1, 8.3, 8.4 step 8, 12, 14.1 item 7 |
| R2 | **"D's census category rule" was undefined** | **Pinned crypto classifier:** `crypto = 1` when the sidecar `fee_category`, stripped and casefolded, contains `crypto`; `0` when present, non-empty, not `nan`/`none`/`null` and without `crypto`; **unknown** when the sidecar or field is missing, empty, null-like, or `sports = -1`, counted separately and **counted as crypto** in the gate (never defaulted to non-crypto); a fail-safe makes the gates NaN (fail) if no sealed `fee_category` contains `crypto`. Used by B's gate and D's crypto kill line. **B uses the gate only; crypto births stay in the population**; 14.3 corrected | 5, 7, 8.3, 14.1 item 4, 14.3 |
| n1 | Scenario 11 constant | `exp(s_t - 0.25)`, which keeps the mean variance at the base (`Var(s) = 0.25`) | 1.8.1 |
| n2 | Memory ladder | If step 3's dry run fails, no pin and LT6 is not registered; the censuses ignore the 1-in-12 `.late` loss, which applies automatically (counted, labelled, not re-projected); a `.late` pass still writes its `series/` and `sweeps/` lines | 8.2 |
| n3 | D text freeze | Code-freeze-check fixes to D are allowed only if committed before 2026-11-11T08:00Z (the first SCREEN_18 read); any later change to D's text gives *partially seen*; the text freeze is stated as the real protection | 1.6 |
| n4 | Item 1 rates | Both the plain CR1 rate (`G_event - 1`) and the `G_treated - 1` rule's rate are reported | 1.7, 1.8 |
| n5 | K details | `statistics.median` for an even number of gaps; the size key from the stored text (`dtype=str`; `parse_float=Decimal` for a JSON number); the `2 x order_min_size` comparison in `Decimal` | 3 |
| n6 | V 1c asymmetry gate | A unit whose toward- or away-side 1c depth at sweep k - 1 is 0 is excluded from both shares and counted | 7 |
| n7 | Seeds | Scenario 12 seed 2026116712 and power-run seeds 2026116721-24, derived from 20261167 (`x 100 + n`) on separate generators | 1.8 |
| n8 | Washout in projections | CD and CB compute every projected count, `n2_eff` and `VIF_w` after the washout and (CB) the clean no-birth rule | 7 |

**Ready for code once these fixes are accepted**, subject to the open dependencies: the LT5 seal's sha256; E022's registration or
drop, with its `END_UTC` and analysis timing (`T_E022`); the outcome of the CB18 request (14.6); and the engine embargo entries
(section 9).


## 16. Freeze-check fixes (2026-10-21; science-reviewer code freeze check, FREEZE_READY_WITH_FIXES for the census code; governs where earlier text differs)

Declarations made **before any LT6 census was run** (q0582 / q0583 / q0584 had not started), to make the code and the text agree. No
threshold, formula, seed, date, gate, alpha or draw count was changed. Nothing here depends on a census value.

| # | Finding | Fix or disclosed declaration | Sections |
|---|---|---|---|
| 1 | `load_rows6` read `end_date` as a pandas category; `panel._epoch` then fails on pandas 2.3.3 for captures of 50 or more rows | LT6's own loader reads `end_date` as text (LT5's base is untouched) | 7 |
| 2 | B admitted incumbents with an unknown as-of end | 1.4 / 1.5 as written: B requires a **known** end > `t_k` + 27 h; the unknown-end indicator exists only for V and K. Unknown-end incumbents are excluded and counted (`unknown_end_excluded`); `hte_unknown` is removed from B's controls | 1.4, 1.5, 5 |
| 3 | `updated_at` changed was 1 when either value was missing | A missing `updated_at` at k - 1 or k is NaN (1.5: a missing control excludes the unit, counted as `updated_at_missing`); never "changed" | 1.5, 4 |
| 4 | Undeclared counted exclusion: V's depletion gate, zero toward-side 5c depth at sweep k - 1 | **Declared now:** among traded units, the 5c halving share and the printed original share use only units whose toward-side 5c depth at k - 1 is positive and finite; the others are counted (`n_5c` against the traded units). Same convention as the declared 1c rule | 7 (CV) |
| 5 | Undeclared counted exclusion: K requires a known, unchanged, positive tick | **Declared now:** a sampled traded mover whose tick is unknown, not positive, or differs between k - 1 and k is excluded and counted (`tick_unknown_or_changed`) before `steps` is formed, because `steps = round(|x| / tick)` is undefined otherwise | 6, 7 (CK) |
| 6 | The census seal did not compare the LT5 seal's hash | `seal_inputs` compares the sha256 of the LT5 capture seal with the spec's `census_inputs.source_seals.lt5_capture_seal_sha256` and refuses while it is null or unmatched. The value is filled from the committed LT5 seal (still null in the spec) | 7, 14.1 item 9 |
| 7 | CK did not print per-market label sums | CK, CD and CB print the distribution of labelled units per market and the share in markets with exactly one (counts only, no gate) | 7 |
| 8 | The size check permuted within market x day in every scenario, the registered gate uses the census-fixed `perm_stratum` (LT4's defect) | Every Freedman-Lane scenario goes through `strata_of(df, perm_stratum of its binding test, t0)` (worlds start at a UTC midnight, `t0 = 0`, two-day blocks as in LT4's `block_of`); `min_stratum`, `min_n` and `draws` come from the spec. The size check refuses while `k_tests` or the `perm_stratum` of a `k_tests` Freedman-Lane test is null. A scenario whose binding test is not in `k_tests` still runs (the one generator's stream is in table order) on the `day` stratum and has no registered meaning. Non-binding runs use the same strata (s12 on D's, the power runs on their own test's) | 1.8, 1.8.1 |
| 9 | The analysis ran without the size-check result | The spec carries `size_check.result_path` and `size_check.result_sha256` (null until registration, required at pin). `analyze` loads that committed result, verifies its sha256, refuses a dev run, a different worlds / draws / seed, or a result not produced on the pinned code, and applies the "SE check failed (size scenario)" and "analytic p oversized" labels | 1.8 |
| 10 | E022 safeguards failed open | `e022.end_utc` is required at the pin unless E022 is recorded as dropped; `v_first_origin_ok` refuses (False) when `END_UTC` is unknown and E022 is not recorded as dropped (a DRAFT, unpinned spec keeps dry runs working); V's freeze condition (`v_freeze_check`) is enforced at the pinned load and in `code_check`: V stays in `k_tests` only if the LT6 registration commit is strictly before `T_E022`. The commit time is a new required-at-pin field `e022.pin_commit_utc` (V and E022 registered only) | 1.1 |
| 11 | V's anatomy dummies overlapped | One categorical, mutually exclusive: **traded**, else the geometry (parallel, one-sided, spread-change), **same-side-unequal the base**. A traded unit is `traded` regardless of its geometry (my reading of "traded, parallel, one-sided, spread-change; same-side-unequal the base"; K's geometry dummies are unchanged) | 2 |
| 12 | A late pass with no sweep was `.nosweep` | The late rule comes first: a late pass is `.late` whether or not its sweep exists (units lost, counted). A pass that is not late and lacks its sweep is still `.nosweep` / `.noprevsweep` | 1.3, 1.5, 8.2 |
| 13 | Vendored base (8.1) | **Deviation, recorded:** `live_tests6_base.py` (generated vendored copies of the LT3-LT5 functions) is deferred. LT6 imports the LT3, LT4 and LT5 functions it uses by name, and its pinned `code_sha256` map covers LT6's own files and every hashed dependency named in `live_tests6.CODE_FILES` (including the imported LT3-LT5 modules). The effect: LT5 maintenance before LT6's pin would change a hashed dependency and be caught by the pin, not isolated by a copy. Vendoring after LT5's pin remains available and would be a reviewed code change | 8.1 |
| 14 | RSS probe measured a different run | `lt6_rss_probe.py` takes `--max-items`, default 2 (ladder step 1) | 8.2 |
| 15 | K's placebo P1 and secondary S3 were never computed by the reader (trade samples rotate off after about 3 days) | The reader freezes, per K unit, `p1_clip_share`, `p1_n_trains` (the train rule on the near-identical-size grouping, 3) and `s3_clip_share`, `s3_n_trains` (the train rule on `size x price` rounded half-up to the cent, 3), both with the same min-size removal and interval rows only. P2 needs no new field (the previous interval's class is the previous pass's frozen `clip_share`) | 3 |
| 16 | V's sports arm (S3), D's P2 (decided markets) and S5 (sports), B's S1 (signed tail arm) and S5 (sports) were not frozen | The reader freezes them as separate passes of the same builders, labelled `arm` in the frozen lines: `sports` (V, D, B), `decided` (D: `mid_k` < 0.03 or > 0.97), `tail` (B: neg-risk incumbents with `mid_k` in [0.02, 0.10)); constants in the spec block `arms`. The primaries, censuses, the washout and the label slots read `arm == main` only. In a reported arm of B the leave-one-out move is over that arm's own incumbents. Arms never change a verdict | 2, 4, 5 |
