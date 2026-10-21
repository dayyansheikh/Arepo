# Live tests 5 (LT5): five round-11 candidates (J, F, O, H, R), DRAFT pre-registrations

**Status: DRAFT, not registered, nothing counted, no code.** Drafted 2026-10-21 (about 09:00Z) on branch
`feat/live-tests-5` from the research tip `756b15eb`. This is a design-only first commit, as LT3's first commit was. E-numbers
are **not** assigned here. They are assigned at registration from the next free number in the ledger (E025 and E026 are taken;
provisionally E027-E031 in the order J, F, O, H, R, for the tests that survive). Before registration this needs, in order:
1. the census input seal (section 8);
2. a challenger review (`science-reviewer`) of this file, and the fixes;
3. the code (section 9), a freeze check of code against design and the fixes;
4. the counts-only censuses (section 8), which fix k;
5. the size check at >= 2,000 worlds on the code to be pinned;
6. a host dry run with peak RSS measured;
7. the `SPEC_SHA256` and `code_sha256` pins, the ledger entry and the reader's installation.
Until the pin exists, every line a reader writes is `prospective_unregistered` by construction.

This is research tooling. AREPO never trades. No edge, calibration, profitability or tradability claim exists or is implied.
Every count quoted from round 9/10 probes, LT3/LT4 censuses, the cost model, the maker-rewards snapshot or the signal-engine
coverage note is a **counts-only development figure on worn data**. Every MDE here is a **planning estimate** built on stated
assumptions, not a measurement. Nothing here read a price after an origin, an outcome or a P&L. No host, network or
`data-dumps` read was used to write it.

Source ideas: `CREATIVE_HYPOTHESES_2026-10-25.md` (round 11; Fable xhigh) top five, CH180, CH184, CH182, CH181 and CH183, written
to that round's binding rules (its section 0 and 0.1), with three design changes made here and justified in section 7.1:
- CH182's tested term changes sign convention (the round's `G = g x m` contradicts its own mechanism on half the space);
- CH181's mark becomes the trailing 7-day extreme (the round's "lifetime" mark is truncated at AREPO's first capture);
- CH184's neg-risk events and the category level leave the family hierarchy (the sum constraint makes "common" mechanical there).

## 0. Summary

| Handle | Idea | Hypothesis (direction) | Population | Primary | Planning MDE (estimate; k = 5 multiplier 3.388) | Floor |
|---|---|---|---|---|---|---|
| **J** | CH180 jump or grind | Within a market, a traded 2 h move made in **few** print levels relative to its size (a jump) continues more over the next 2 h than one made in **many** levels (a grind) (one-sided, > 0) | all categories (sports split reported), active-frame trade samples + captures | expanding-past demeaned OLS of `c` on 1[jump] over jump and grind units | **about 0.29-0.64c** (borderline; census-gated) | 0.5c |
| **F** | CH184 alone or with the crowd | Within a market, a 2 h move its family did **not** share (idiosyncratic) continues more than one its family shared (common) (one-sided, > 0) | non-sports, complete captures; family = non-neg-risk event, else series | expanding-past demeaned OLS of `c` on 1[idiosyncratic] over the two classes, E015 anatomy held fixed | **about 0.13-0.24c** | 0.5c |
| **O** | CH182 capital-gains overhang, token-weighted | Within a market, the 6 h YES mid change rises with the **active-side overhang** `O = |g| x m` (`g` = mid minus the 24 h YES-terms VWAP of the sampled prints, `m` = YES-token minus NO-token notional share), with `g`, `m` and momentum held fixed (one-sided, > 0) | all categories (sports split reported), trade samples + captures | expanding-past demeaned OLS of `y6` on `zO` | **about 0.15-0.39c per SD; tercile 0.32-0.86c** (borderline; census-gated; may drop) | 0.5c (tercile) |
| **H** | CH181 the high-water mark | Within a market, a mid within 1c of its own trailing 7-day high (low) set >= 3 days earlier drifts **through** the mark over 24 h more than a mid far from both marks (folded; one-sided, > 0) | non-sports, complete captures | expanding-past demeaned OLS of the folded 24 h change `u` on 1[near] over near and far units | **about 0.37-1.0c** (borderline; census-gated; may drop) | 0.5c |
| **R** | CH183 the farmer's choice | In rewarded markets, the slope of the next pass's sweep-mid change on the near-touch depth imbalance **jumps up** inside the one-sided-scoring band at the folded mid 0.90 (one-sided, > 0) | rewarded binary markets, folded mid in [0.84, 0.96), sweep 1 + sidecar | within-market (expanding-past) local-linear RD of `c_sw` on `imb`, `imb x inside` and the running-variable terms; the coefficient on `imb x inside` | **about 0.27-1.1c per SD; x 2 SD 0.55-2.2c** (likely to drop at the census; declared now) | 0.5c (2 SD contrast) |

- **Family:** one Holm family over the k surviving primaries, one-sided, familywise alpha 0.05, separate from E009-E011, LT2
  (E012-E014), LT3 (E015) and LT4 (E020-E022). **k <= 5.** A test whose census gate fails is dropped *before* registration,
  uncounted, and k is the number that survive; k is fixed in the spec (`k_tests`) at registration and never changes. A primary
  that is unavailable or fails its gate enters Holm with p = 1.
- **Dropped or deferred (uncounted; section 7):** CH185 (clip trains: the round's no-trains rule; its arm 2 needs `side`), CH190
  (the makers' vote: its state is LT4 E022's pinned control `dimb` on overlapping origins and the same target; deferred to
  after E022's analysis), CH187 and CH188 (unprobed; maps first), CH186 and CH189 (engine-first, resolution targets).
- **Window (proposed):** whole captures with start in `[REGISTERED_UTC, END_UTC)`, 21 days, `REGISTERED_UTC =
  2026-10-30T00:00:00Z`, `END_UTC = 2026-11-20T00:00:00Z`; single analysis on or after `2026-11-21T12:00:00Z` (section 1.1).
- **Expected outcome, declared now:** at most one or two of H, O, R survive their censuses; J is borderline; F is the
  best-powered. Every taker check is expected to be "not shown" (section 1.10).

## 1. Common rules

### 1.0 Lessons carried over (binding from the first draft)

LT4's lessons **L1-L15** (`LIVE_TESTS_4.md` 1.0) apply unchanged: exact `%.17g` writes and round-trip reads; NaN refusals in a
pinned spec; sealed census inputs re-hashed (refuse on mismatch); a pessimistic planning-MDE gate in every census; a simulated-null
size check at >= 2,000 worlds with the limit 0.05 + 1.645 sqrt(0.0475 / worlds) = 0.058; dry-run guards; spec and code pins on
every frozen line; write-once per-capture series and status files; skip-slot labels where a bounce can sit at the origin;
clustering by event, event x UTC day and UTC day with p the largest; Holm over k counted once; economics never changes a
verdict; no both-class inclusion rule; readers at the pass cadence; an internal run lock. LT4's R1/R2 amendments are adopted as
well: Freedman-Lane gates (LT4 14.1 item 7), the permutable-strata rule with a pre-declared two-day-block fallback (14.1 item 2),
`DE_gate = max(floor, computed)` (15.1 item 4), the series-family exclusion rule (14.2 item 9), the joint late mask for skip
targets (15.1 item 6) and one block-anchor function (16 item 2). The donor gate is not used anywhere (LT3 13.13; LT4 15).

Round 11's eight design rules (`CREATIVE_HYPOTHESES_2026-10-25.md` 0.1) map onto LT5 as follows:

| Round-11 rule | LT5 rule |
|---|---|
| 1. Continuous or labelled states on whole populations; no rare events | every state is defined on every eligible unit; the contrasts are classes or slopes of that state; each census has a projected-count and an MDE gate |
| 2. The state must change within the market | H and R have slow states: dormant units (no price and no state change since k - 1) are excluded; `DE_gate` floors are 5.0 (H, R) and 4.0 (O), against 3.0 for J and F |
| 3. Correlated moderators: Freedman-Lane only, `|corr|` <= 0.5 with the controlled moderators as a census gate | each test lists its correlation gates (section 8); within-market (expanding-past demeaned) correlations bind, pooled ones are printed |
| 4. Sign-free primaries | J, F and H take the sign from the capture's own mid move or the mark; O takes no sign from `side` (the token mix is an `outcome_index` share); R's sign is the imbalance's. `side` enters O only as the control `x6` |
| 5. One value per pass is one value per day | F's family is an event or a series, never the venue or the category (section 7.1); R and H vary within pass and within market |
| 6. Quote anatomy predicts quote targets | F controls E015's anatomy class; J controls E021's freshness and the anatomy geometry; R's target starts at its own sweep (E022's convention); skip-slot mechanism labels are binding labels for J, F, O and H |
| 7. Readers at the pass cadence | J and O extend E021's per-pass reader (trade samples are retired after three days) |
| 8. Probed deaths are final | nothing here revives comment bursts, cross-event baskets, attention surges, ladder breadth, walked orders or trains |

### 1.1 Registration, window, single analysis
- `REGISTERED_UTC` is the first 00:00Z that is **at least 24 h after the LT5 registration commit** (spec pin plus ledger
  entry), **at least 48 h after LT4's `REGISTERED_UTC`**, and **never earlier than 2026-10-30T00:00Z** (round 11's rule). LT5
  registers only after LT4's registration commit. The proposed value is **2026-10-30T00:00Z**. If a commit slips,
  `REGISTERED_UTC` moves to the next qualifying 00:00Z, `END_UTC = REGISTERED_UTC + 21 d` and the analysis date `END_UTC + 36 h`.
  The rule uses no data; a move is recorded in the ledger.
- **Window membership is by capture start**, whole captures in or out. A unit's origin is its own decision time (1.3).
- **Fixed end, no extension.** Round 11 offers a counts-triggered 28-day extension. It is **not adopted**, as LT4 did not
  adopt round 10's: it is one more researcher degree of freedom, and the censuses gate power before registration instead.
  Shortfalls are labelled (*underpowered*, Unavailable), never extended (question 12).
- **One analysis**, once, on or after the analysis date (`run_live_tests5.py analyze` refuses before it; `--out` refuses to
  overwrite). No interim look at any outcome (1.6).
- **Effective start** = max(`REGISTERED_UTC`, the first capture processed by the reader at the pinned commit). The analysis
  keeps only lines whose `spec_sha` and `code_sha` equal the pins and whose role is `prospective_confirmation`.

### 1.2 Streams read (all already written by the host's pass; nothing new is fetched; no new collector)
- **Complete-universe captures** `snapshots/<id>/rows.csv.gz` (every 2 h at :31; `state=complete` only): LT3/LT4's columns
  (`bid`, `ask`, `spread`, `last_trade_price`, `volume24hr`, `liquidity`, `chg_1h/1d/1w`, `end_date`, `event_id`,
  `neg_risk`, `neg_risk_market_id`, `closed`, `active`, `received_utc`).
- **Sidecar** `rows_ext.csv.gz`: `fee_type`, `fee_category`, `series_slugs`, `order_price_min_tick_size`, `rewards_min_size`,
  `rewards_max_spread`, `clob_rewards` (R; the daily rate). A missing sidecar sets `sports = -1` (excluded wherever the
  category is needed), counted.
- **Book sweep 1 of the same pass** `book_sweeps/<id>/` (`series_index` 0): outcome-0 and outcome-1 `best_bid`, `best_ask`,
  `bid_size_1`, `ask_size_1`, `depth_*_1c`, `depth_*_5c`, `min_order_size`, `batch_receipt_utc`. R's state and target; J's
  mechanism reading.
- **Active-frame trade sample of the same pass** `trade_samples/<id>/` (`manifest.json`, `trades.csv.gz`): J and O read
  `ts`, `price`, `size`, `outcome_index`, `asset`, and O's control `x6` reads `side` (E007 convention). Wallet fields are never
  read.
- **Not read:** the live large-trade monitor, `cross_venue_live/` (sealed to 2026-11-03), `surprise_live/` (E011), the stores
  `live_tests2/`, `live_tests3/`, `live_tests4/`, CB8-H holders, the CB16/CB17/CB18, E025 and E026 stores, `cb6_extract/`,
  the signal engine's `quotes/`, `features/`, `aux/` and `predictions/`, and Gamma outcome fields of any kind.

### 1.3 Clocks, slots and decision times
- **Slots:** as LT3/LT4 (`grid0 = 2026-10-01T00:31Z`, 2 h, tolerance 30 min, first complete capture of a slot). "k - 1" and
  "k + h" are slots, not file order. Target slots: k + 1 (2 h), k + 3 (6 h), k + 12 (24 h).
- **Decision time per test** (the latest input's own receipt; states use that input and strictly earlier ones only):
  - **J:** the trade sample's receipt in pass k. The state uses capture rows k - 1, k and trade rows with
    `t_{k-1} <= ts < t_k` (`t` = the market row's `received_utc`). As in E021 (LT4 1.3, R2 finding 7), the coverage flag
    depends on rows between `t_k` and the receipt, which are public before the decision time: no leakage; the excluded share
    is reported by class.
  - **F:** capture k's own row receipt `t_k`, **with a sibling look-ahead guard**: a family member's row enters the family
    mean only if its `received_utc <= t_k + 5 s` (the signal engine's event-family guard, DESIGN_V1 16: intra-event receipt
    spread p99 201 s on 2026-10-21). A sibling received later could carry part of the unit's own later move into its class.
    A unit left with fewer than 3 usable siblings is excluded (`guard_loss`, counted).
  - **O:** the trade sample's receipt in pass k; trade rows with `ts < t_k` only; captures k - 12 .. k.
  - **H:** capture k's row receipt; the mark uses captures of slots k - 84 .. k - 1 only.
  - **R:** sweep 1 of pass k (`batch_receipt_utc` of the outcome-0 token); the sidecar and capture of k (minutes earlier);
    **the target starts at that sweep** (E022's convention).
- **Late rule:** as LT4 1.3 (a frozen file is written before its earliest target slot can start, else `.late`, units lost and
  counted; *late-loss* above 2% of a test's origin files).

### 1.4 Shared origin-side eligibility (a move unit at capture k; J and F)
LT4 1.4 items 1-8, applied in order and counted (LT3's `move_join` and `classify`): binary, open and active at k - 1 and k;
two-sided and tight (spread <= 0.10) at both; `mid_k` in [0.02, 0.98]; as-of end unknown or > `t` + 3 h; category by
`cb17_census.is_sports_sidecar` on the sidecar of k; one row per `condition_id`; `|x| >= 0.01`, `x = mid_k - mid_{k-1}`, with
LT3's class and geometry. H and R use their own unit definitions (sections 5, 6) with items 1-3, 5-7.

### 1.5 Missing data and per-capture status (never imputed)
As LT4 1.5: every frozen unit receives exactly one status at every target (`two_sided`, `one_sided`, `closed_flag`, `absent`,
`capture_missing`; sweep targets `two_sided`, `one_sided`, `absent`, `capture_missing`), write-once and online; only
`two_sided` has a target; the attrition rule (|a_1 - a_0| > 2 pp gives *attrition-differential* and Lee-type bounds; for O, H
and R the classes are the upper and lower halves or the contrasted classes) never changes a verdict. A required input missing at
the origin produces no unit and is counted (`sidecar_missing`, `.nosweep`, `.noprev`, sample absent, `hwm_incomplete`). A
missing control or state is NaN (excluded, counted), never 0.

### 1.6 What is not looked at before the analysis date
No mid, move, target, P&L, regression or plot from `live_tests5/` files, or from in-window captures, sweeps or samples, for these
hypotheses. Only `run_live_tests5.py ops-stats` may run (file, line, role, class and status counts; reads no price column,
enforced by a unit test). No change of thresholds, scales, populations, estimators or k after registration; operational fixes
are logged as deviations.

### 1.7 Estimators and inference
- **Expanding-past demeaning** for all five primaries (J4-R; LT2-LT4): every regressor (the tested term and every control)
  minus the mean of the market's strictly earlier units of the same test; target raw; the first unit of each market drops.
- **Standard errors and p (L10):** CR1 on event, two-way event x UTC day of the origin, and UTC day. One-sided
  **p = max(p_event on t with G_event - 1 df, p_two-way normal, p_day on t with G_day - 1 df)**. Where the census top series
  family is not excluded (1.9), the event t also uses `G_series - 1` df if that is smaller (round 11 hygiene). The conservative
  95% CI is the hull of a 2,000-draw event bootstrap and the three Wald intervals. Two-day blocks are a sensitivity for the 6 h
  and 24 h targets.
- **Overlapping targets.** O's 6 h target at consecutive origins overlaps two passes; H's 24 h target overlaps eleven. The event
  x day and day clusters absorb this within a day; two-day blocks are reported; the size check carries binding MA(2) and MA(11)
  scenarios (1.8).

### 1.8 Gates (valid within-unit nulls) and their size
- **Binding gate for every primary: Freedman-Lane permutation** (LT4's `fl_perm_gate`): after expanding-past demeaning, the
  target's residuals from the reduced model (target on the controls) are permuted within strata and the full model is refitted;
  200 draws; passes if `p_perm < 0.05`. Strata: market x UTC day if >= 50% of the test's units sit in permutable strata (>= 4
  units), else market x two-day block if >= 50%, else the test fails its census gate (chosen by counts in the census, fixed in
  the spec as `perm_stratum`).
- A failed gate gives p = 1 in Holm and the label "SE check failed".
- **Size check (L5):** `size-check` runs, once, on the code to be pinned, **nine binding Freedman-Lane scenarios** with no
  effect: (1) binary iid; (2) binary persistent market rates; (3) binary with a control at correlation 0.7; (4) continuous
  persistent; (5) continuous with a control at correlation 0.7; (6) continuous with a control at correlation **0.85** (O: the
  tested term is built from `g` and `m`, which are controls); (7) persistent binary label with an **MA(2)** overlapping target
  (O, and J/F's 6 h mechanism readings); (8) persistent binary label with an **MA(11)** overlapping target (H); (9) an
  **interaction** world for R (a continuous `imb` with a real main effect, a binary `inside` with a real level effect, no jump
  in the slope). 2,000 worlds x 200 draws, seed **20261147**, limit 0.058; any failure blocks the pin, with no rerun, reseed
  or variant.

### 1.9 Verdicts and labels (per primary, after Holm over k)
- **Supported (exploratory, prospective):** Holm-adjusted one-sided p < 0.05, estimate in the predicted direction, gate passed.
- **Contradicted:** the conservative 95% CI lies entirely on the other side of 0. **Inconclusive:** otherwise.
  **Unavailable:** below the test's floor counts, or fewer than 10 UTC days with units.
- **Labels (never change a verdict):** *material* (J, F, H: point estimate >= 0.5c; O: the top-minus-bottom tercile contrast of
  `zO` >= 0.5c; R: the jump times 2 SD of `imb` >= 0.5c); *underpowered*; *attrition-differential*; *late-loss*;
  *coverage-limited* (J: interval-truncated > 2% of traded sampled movers; O: 24 h-truncated > 5%); *series-concentrated* (one
  series family > 50% of a primary's units after the census rule); *sweep-missing*; the per-test mechanism labels.
- **Series-family rule (census-fixed):** if the census top series family holds > 40% of a test's primary population, that family
  is excluded from the primary (`<test>.exclude_family`; `""` = none), and the test's MDE gate is recomputed after the exclusion.

### 1.10 Economics (separate; never changes a verdict)
- Paper taker round trip per share at the recorded touches (sweep 1 of pass k at the decision time, sweep 1 of the target pass at
  exit), fees on both legs from the origin sidecar (`economics.fee_spec`, `resolve_rate(..., "max_if_unknown")`), LT3's
  `paper_taker` and `econ` (event-clustered mean, one-sided p, >= 30 trades in >= 10 events). No depth, queue or latency:
  optimistic.
- **Hurdles from `cost-model-v1`** (`COST_MODEL.md`; development calibration 2026-10-16 to 10-19), reported beside each cell by
  Gamma-liquidity tier: $100 taker round trip about 2.9c at >= $100k, 3.9c at $10k-100k, 7.2c at $1k-10k (medians, both fees);
  a 5-share touch round trip about 4.5c. A passive touch order fills about 3.1% of the time within an hour and loses about 2.38c
  to adverse selection against a 2 h mark (about 0.39c at >= $100k).
- **Maker routes** (the round's primary money route for every test): gross mid-to-mid or sweep-to-sweep move of the favourable
  cell only, "gross, no fills", reported per liquidity tier, with the 0.39c (>= $100k) adverse-selection figure beside it.
- **Declared in advance:** every AREPO taker cost check has failed (E004, E007; 0 of 95 economic cells positive). "Not shown" is
  the expected outcome for every taker cell here.

### 1.11 Overlaps, sealing and counting
- **Within LT5:** J and O read the same trade samples (J: traded movers with >= 3 rows in the interval; O: markets with >= 10
  rows in 24 h; overlapping units, different states and targets). F and H read the same captures (F: non-sports movers in
  families; H: non-sports units near or far from a mark; overlapping units). All in one Holm family; never counted as
  independent confirmations. Pairwise unit overlap shares are printed by the census and reported at analysis.
- **Against registered or drafted live tests (no double count):**

  | LT5 | Closest prior primary | Same data? | Same contrast? | Why not a double count |
  |---|---|---|---|---|
  | J | E021 (LT4; fresh vs settled traded moves, skip target) | yes (traded sampled movers) | no | J's state is the interval's price path (levels per tick moved); E021's state, the last trade's age, is a **control** here, with a census `|corr|` gate |
  | J | E016 (LT3, dropped at census) | samples | no | E016 read order-level walking from 4-decimal prices; J snaps prices to the grid and reads the interval path; no `side` |
  | F | E015 (LT3; parallel quote-only vs traded) | yes (captures) | no | F's classes are defined by the family's move; E015's anatomy is a **control**, with a census `|corr(1[common], 1[parallel])|` gate |
  | F | E019 (LT3, dropped), E005, SB2-J5, L1-L4/XM1-XM6 | captures | no | breadth and lead-lag read siblings' later moves or the share re-quoted; F reads the unit's own continuation given the family's simultaneous move |
  | O | E013, E016, E023 (dropped) | samples | no | O's state is a VWAP gap weighted by the token mix, sign-free; `x6` is a control |
  | H | E002/E004/E006, E012 (LT2) | captures | no | fixed-horizon changes and `chg_1d x liquidity` are **controls**; H's state is the distance to a trailing extreme |
  | R | E022 (LT4; hollowness; `dimb` as a control), E020 (reward flag control) | sweeps, sidecar | no | R's tested term is the jump in the imbalance slope at the 0.90 reward cutoff in rewarded markets; E022's `zh` and `log1p D` are R's controls |
  | R | CB6-R (spread at the 0.90 cutoff) | sidecar, sweeps | no | CB6-R's statistic is the spread (R1) and a touch maker's P&L (R2); R reads the imbalance's predictive slope; `cb6_extract/` is never read |
  | R | E025 (reward-inclusive maker test; provisional) | rewarded markets | no | E025 is a maker P&L test; its store is never read |

- **Signal-engine shadows (disclosed; question 2).** The engine's `se8_lr_event` (not embargoed; scoring since 2026-10-21; first
  fit about 2026-10-27) carries `ev_sib_d2h`, the event siblings' mean own 2 h mid change, beside the champion's own 2 h change.
  On `dir_2h` a logistic model with both terms is a development look at F's decomposition. Recommendation (orchestrator decision):
  add an `event` embargo token until LT5's analysis date **before se8 shows any score**; otherwise F is declared "not fresh" in
  its registration. The flow (to 2026-11-16), book and rewards (to 2026-11-18) tokens must move later to **2026-11-22T00:00Z**
  if J, O or R columns join those families (section 10).
- **Collection overlap (disclosed):** LT2 (to 2026-11-12), LT3 (to 2026-11-14), LT4 (to 2026-11-16), E011 (to 2026-11-10), CB18,
  E025, E026 and the signal engine read the same captures, sweeps and samples. Different hypotheses, no pooling, no store opened
  by another test.
- **Counting (M3):** the analysis adds **k counted tests**, one per surviving primary, kind `live_tests5`
  (`battery2.KIND_RULES["live_tests5"]`, fail-closed). Gate draws, secondaries, mechanism readings, economics, censuses and the
  size check count 0. The cumulative count is recorded at registration and at analysis.

## 2. J: jump or grind (CH180)

- **Hypothesis and mechanism.** A large resting order absorbs flow at one price until it is exhausted and the price then gaps
  (Rosu 2009's patient walls; Barndorff-Nielsen and Shephard's jumps against diffusive variation): the move is pent-up demand
  released and continues. A move made in many small steps is a maker re-pricing on each fill (Avellaneda-Stoikov inventory
  skew): the information was absorbed as it arrived and the price already reflects it. **Direction: D_JG > 0, one-sided.**
- **Unit.** Market x pass k whose market is in the pass's active-frame trade sample (status ok), is a `traded` mover at k (1.4
  with `|x| >= 0.01`) and passes the filters below. All categories (E021's convention: the sample is a 2,000-market subsample of
  the active frame; the non-sports arm alone is underpowered); category is a spec parameter (`j.population`); sports and
  non-sports arms are reported.
- **Origin-side filters (in order, counted):** sample status ok; 1.4 items 1-5, 7, 8; class `traded`; tick known at k - 1 and k
  and equal (sidecar `order_price_min_tick_size`; a change excludes); `steps = round(|x| / tick) >= 3`; interval coverage (the
  page's oldest row of the market at or before `t_{k-1}`, or the page not full; else `interval_truncated`); `n_int >= 3` rows of
  the market with `t_{k-1} <= ts < t_k`.
- **State (frozen).** Each interval row's YES-terms price (`price` if `outcome_index == 0`, else `1 - price`), **snapped to the
  tick grid of k** (an aggregated off-grid print snaps to its nearest level, so a walked order cannot create a level); `levels` =
  number of distinct snapped prices; `g_path = clip((levels - 1) / steps, 0, 1)`. **Jump:** `g_path <= 0.25`; **grind:**
  `g_path >= 0.75`; the interior is reported (S1). Also frozen: `maxstep_share` (largest absolute YES-terms step between
  time-consecutive rows over `|x|`), `n_int`, E021's `age` and `fresh = 1[age <= 900 s]`.
- **Target (exact).** `c = sign(x) * (mid_{k+1} - mid_k)` (Gamma mids, status `two_sided` at k + 1). Horizon 2 h.
- **Primary statistic.** Expanding-past demeaned OLS of `c` on `JP = 1[jump]` over jump and grind units, controls: `log1p n_int`,
  `log |x|`, `fresh`, `log1p age`, geometry dummies (parallel, one-sided, spread-change; same-side-unequal the base), `spread_k`,
  logit `mid_k`, `|mid_k - 0.5|`, `log1p volume24hr_{k-1}`, 1[tick = 0.001], log hours-to-end (+ flag). Inference 1.7; seed
  20261141. Gate: Freedman-Lane, seed 20261241.
- **Mechanism readings (binding label rules).** M1: the sweep target `c_sw = sign(x) * (smid_{k+1} - smid_k)` (sweep 1 of passes k
  and k + 1). If Supported and M1 is below 50% of D_JG or its one-sided p >= 0.05: **Gamma-quote mechanics**. M2: the skip-slot
  persistence `sign(x) * (mid_{k+3} - mid_{k+1})`, joint late mask. If Supported and M2 is not one-sided significant in the same
  direction: **transient (first pass only)**. M3: 1[tick = 0.01] books only; if Supported and M3's estimate is below 50% of D_JG:
  **tick-grid mechanics**.
- **Secondaries (descriptive).** S1 `g_path` as a continuous dose over all qualifying units; S2 `maxstep_share` in place of the
  class; S3 sports and non-sports arms; S4 the 6 h target; S5 the unmoved side's change; S6 counts by class, tick and `n_int`
  band. **Placebo (reported):** the path class of the *next* interval `[t_k, t_{k+1})` against `c` is not a valid null (it is part
  of the target), so the reported placebo is the class of the *previous* interval `[t_{k-2}, t_{k-1})` with the current class
  held fixed; a contrast at least half of D_JG labels *persistent-trait*.
- **Planning MDE (estimate).** P2/P2c bound clocked traded sampled movers at about 1,000 a pass; the >= 3-row, >= 3-tick subset is
  **unprobed**: assume 100-250 a pass (25,200-63,000 in 21 days), jump 30%, grind 35%, 75% surviving the first-unit drop (jump
  5,700-14,200; grind 6,600-16,500). SD of `c` 4c; event DE 2-3; day factor 1.3-1.5. `SE = 4c * sqrt(1/n_J + 1/n_G) *
  sqrt(DE) * day`; **MDE = 3.388 * SE = 0.29-0.40c at 250 a pass, 0.45-0.64c at 100 a pass.** Census-gated; may drop.
- **Floors (Unavailable):** < 2,000 jumps, < 2,000 grinds, < 200 events, < 10 days.
- **Economics.** (a) Reported taker follow of jumps with `|x| >= 0.03`, entry at the sweep-1 touch of pass k, exit at the sweep-1
  touch of pass k + 1 (optimistic by the minutes between sweep 1 and the sample receipt; disclosed), against the cost-model-v1
  tier hurdles. (b) Maker: after a jump, no re-post at the pre-move level for one pass; gross `c` by class, "gross, no fills".
- **Missing data.** Sample absent → no units (counted per pass); status not ok, tick unknown, `interval_truncated`, `n_int < 3`
  → excluded and counted by reason.

## 3. F: alone or with the crowd (CH184)

- **Hypothesis and mechanism.** A member's 2 h move splits into the part its family moved at the same capture and the part it
  moved alone. A family re-centering (one reference repriced across a series or an event's programs) is already priced across
  the family; a move the member made alone came from its own book and is market-specific information that diffuses slowly
  (Hong and Stein 1999; idiosyncratic momentum, Gutierrez and Prinsky 2007; Blitz, Huij and Martens 2011). **Direction: D_IC > 0,
  one-sided.**
- **Unit.** Non-sports market x capture k passing 1.4 with `|x| >= 0.01`, in a family with **>= 3 other members** that pass 1.4
  items 1-3 and 7 at k - 1 and k (any `|x|`, including 0) and the sibling receipt guard (1.3).
- **Family hierarchy (declared now; section 7.1).** (i) The `event_id` if the event is **not** neg-risk and has >= 3 other usable
  members; else (ii) the first `series_slugs` entry if it has >= 3 other usable members at k; else the unit is not formed
  (counted by reason). **Neg-risk events and the fee category are not family levels in the primary.** Neg-risk members can still
  enter through (ii).
- **State (frozen).** `xbar = ` equal-weighted leave-one-out mean of the usable members' `x` (k - 1 to k); `w = clip(xbar / x, -1,
  2)`. **Idiosyncratic:** `|xbar| < 0.25 |x|`; **common:** `w >= 0.75`; the rest (opposite-signed or partial) is reported (S1).
  Also frozen: family level, family size, the liquidity-weighted `xbar_L`, and E015's anatomy class of the unit.
- **Target (exact).** `c = sign(x) * (mid_{k+1} - mid_k)`, status `two_sided` at k + 1. Horizon 2 h.
- **Primary statistic.** Expanding-past demeaned OLS of `c` on `ID = 1[idiosyncratic]` over idiosyncratic and common units,
  controls: E015 anatomy dummies (traded, parallel, one-sided, spread-change; same-side-unequal the base), `log |x|`, `spread_k`,
  logit `mid_k`, `|mid_k - 0.5|`, `log1p volume24hr_{k-1}`, `log` family size, 1[series level], `log1p liquidity_k`. Inference
  1.7; seed 20261142. Gate: Freedman-Lane, seed 20261242.
- **Mechanism readings (binding label rules).** M1 sweep target (as J's M1): **Gamma-quote mechanics**. M2 skip-slot persistence:
  **transient (first pass only)**. M3 the member-relative continuation `c_rel = sign(x - xbar) * ((mid_{k+1} - mid_k) - xbar_{k+1})`
  (`xbar_{k+1}` the same members' mean move k to k + 1): if Supported and M3's one-sided p >= 0.05, label **family catch-up** (the
  contrast is the siblings' later moves, not the unit's own continuation; the rejected lead-lag nulls predict this is small).
- **Placebo (reported, label rule).** A **fake family** per unit: the same number of members drawn (seed 20261342) from eligible
  non-sports markets of the same `fee_category` and Gamma-liquidity tercile at k, outside the unit's event and series; the
  primary re-run with fake classes. If the fake contrast is one-sided significant and at least half of D_IC: **family-free (the
  classes proxy the unit's own move size)**.
- **Secondaries.** S1 the interior class; S2 the liquidity-weighted mean; S3 the neg-risk event level with the event's
  sum-of-mids change as a control (section 7.1); S4 the category level (CH158's object; underpowered by construction); S5 the 6 h
  target; S6 the sports arm; S7 counts by family level, size and class.
- **Planning MDE (estimate).** P1/P1b: about 2,750 non-sports movers an interval, about 693,000 in 21 days. The share with a
  usable non-neg-risk event or series family is **unprobed**: assume 25-45% (173,000-312,000), idiosyncratic 30% and common 30%,
  80% surviving the first-unit drop (41,600-74,800 each). SD 4c, DE 2-3, day 1.3-1.5: **MDE = 0.13-0.24c.** The 0.5c floor binds,
  not power.
- **Floors (Unavailable):** < 5,000 idiosyncratic, < 5,000 common, < 300 events-or-series, < 10 days.
- **Economics.** (a) Reported taker follow of idiosyncratic moves with `|x| >= 0.03` in >= $100k markets, against the 2.9c hurdle.
  (b) Maker: after a common move quote normally, after an idiosyncratic move step aside on its side for one pass; gross `c` by
  class, "gross, no fills".
- **Missing data.** As 1.5; `guard_loss` and family-not-formed are counted by reason and printed by family level.

## 4. O: capital-gains overhang, token-weighted (CH182)

- **Hypothesis and mechanism.** The disposition effect (selling winners early, holding losers) makes the aggregate unrealised gain
  of the active holders, measured as the price minus their turnover-weighted reference price, predict under-reaction and
  continuation (Grinblatt and Han 2005; Frazzini 2006). In a binary market a YES holder's gain is a NO holder's loss, so whose
  disposition binds depends on which token the active population trades. With `g = mid - VWAP` (YES terms) and `m = s_YES -
  s_NO`, the selling of winners is strongest when the active side is in gain: YES-active and `g > 0` (YES held down, rises), or
  NO-active and `g < 0` (NO held down, rises, so YES falls). In a linear model the YES-terms prediction is `y6 = a * g + b * |g|
  * m` with `b > 0`. **Tested term `O = |g| * m`; direction: beta(zO) > 0, one-sided.**
- **Unit.** Market x pass k in the active-frame trade sample (status ok), passing 1.4 items 1-3, 5, 7 at capture k (no move
  required), `mid_k` in [0.05, 0.95], with >= 10 rows in `[t_k - 24 h, t_k)` and **24 h coverage** (page not full, or its oldest
  row of the market at or before `t_k - 24 h`; else `trunc24`, excluded, counted). All categories (sports split reported).
- **State (frozen; rows with `ts < t_k` only).** `VWAP` = size-weighted mean of YES-terms prices over the 24 h rows; `s_YES`,
  `s_NO` = notional shares (size x price of the token) on outcome 0 and outcome 1; `g = mid_k - VWAP` (cents); `m = s_YES - s_NO`;
  `O = |g| * m`; `zO = (O - c_O) / s_O` (census centre and scale). Also frozen: the round's `G = g * m` (S2), `x6` (E007
  convention, 6 h, LT3's `signs`), `n24`.
- **Target (exact).** `y6 = mid_{k+3} - mid_k` (YES terms, status `two_sided` at k + 3). Horizon 6 h.
- **Primary statistic.** Expanding-past demeaned OLS of `y6` on `zO`, controls: `g`, `|g|`, `m`, own mid changes over 2 h, 6 h and
  24 h (`mid_k - mid_{k-1}`, `- mid_{k-3}`, `- mid_{k-12}`; missing → 0 with a flag), Gamma `chg_1d` (+ flag), `x6`, `m * |own 24 h
  change|` (the token-mix-by-move-size term a flow continuation would load on), logit `mid_k`, `|mid_k - 0.5|`, `spread_k`, `log1p
  n24`. Inference 1.7; seed 20261143. Gate: Freedman-Lane, seed 20261243.
- **Mechanism readings (binding label rules).** M1 the skip-slot `mid_{k+3} - mid_{k+1}` with the joint late mask: if Supported and
  not one-sided significant: **transient**. M2 the same model with `O` from rows ending 30 min before `t_k`: if Supported and M2 is
  below 50% of the primary: **possibly mechanical (stale-mid catch-up)**.
- **Secondaries.** S1 the plain overhang slope on `g` (momentum-confounded; reported as such); S2 the round's `G = g * m` (sign
  convention of section 7.1); S3 24 h target; S4 sports and non-sports arms; S5 top-minus-bottom tercile of `zO` (the material
  reading); S6 counts and the 24 h truncation share by `volume24hr` decile.
- **Planning MDE (estimate).** LT3 C2: about 10,700 covered market-samples a day (6 h window); the >= 10-row 24 h subset is
  **unprobed**: assume 5,000-8,000 a day (105,000-168,000 in 21 days), 80% after the first-unit drop. SD of `y6` 5c; slow state,
  DE 3-5; day 1.3-1.5; within-market VIF of `zO` given `g`, `|g|`, `m`, momentum and `m * |change|` assumed 2-4 (unprobed; the census
  measures it). Per SD: `SE = 5c / sqrt(n) * sqrt(DE) * day * sqrt(VIF)`; **MDE = 0.15-0.39c per SD; the tercile contrast (about
  2.2 SD) 0.32-0.86c** against 0.5c. Census-gated; declared now: O may drop.
- **Floors (Unavailable):** < 20,000 covered units, < 500 events, < 10 days.
- **Economics.** (a) Reported taker buy of the gaining active side's token when `|g| >= 0.03` and `|m| >= 0.5` in >= $100k markets,
  6 h hold, against the 2.9c hurdle. (b) Maker: lean toward the side whose active holders are in gain; gross `y6` in the upper and
  lower `zO` terciles, "gross, no fills".
- **Caveats (disclosed).** The token mix of prints is a proxy for the active population (buys and sells on a token both count);
  the VWAP mixes entries and exits (no `side`, by design); `x6` is signed under the E007 convention (93.3% agreement, q0400) and is
  a control only.

## 5. H: the high-water mark (CH181)

- **Hypothesis and mechanism.** Nearness to a salient past high predicts returns because traders anchor on it: they sell at it and
  are slow to bid through it, so news is under-reacted to near the mark (George and Hwang 2004; the mirror at the low). Polymarket's
  chart shows the extreme. **Direction: D_NF > 0, one-sided** (folded: near the high, the mid drifts up; near the low, down).
- **Mark (declared now; section 7.1).** For each market, `hi_{k-1}` and `lo_{k-1}` = the maximum and minimum two-sided Gamma mid
  over the complete captures of slots k - 84 .. k - 1 (the trailing 7 days, 84 slots), with `age_hi`, `age_lo` = slots since the
  extreme was last attained. A unit needs >= 72 of those 84 slots present for the market (else `hwm_incomplete`, counted).
- **Unit.** Non-sports market x capture k: 1.4 items 1-3, 5-7 at k - 1 and k; `mid_k` in [0.05, 0.95]; range `hi_{k-1} - lo_{k-1} >=
  0.05` (common support: a near unit in a flat market is not a retest); **state changed since k - 1** (the mid changed, or `hi` or
  `lo` changed as an old extreme left the window); not a new extreme (`lo_{k-1} <= mid_k <= hi_{k-1}`; new highs and lows are S2).
- **Classes (frozen).** `d_hi = hi_{k-1} - mid_k`, `d_lo = mid_k - lo_{k-1}`. **Near-high:** `d_hi <= 0.01` and `age_hi >= 36`
  (the high was set at least 3 days earlier; a retest, not a fresh high), `s = +1`. **Near-low:** `d_lo <= 0.01`, `age_lo >= 36`,
  `s = -1`. (A unit near both is impossible under the range rule.) **Far:** `d_hi >= 0.05` and `d_lo >= 0.05`; `s` for far units is
  the sign of `mid_k - (hi + lo) / 2` (towards the nearer mark), so near and far share one folding rule. The rest (between 1c and
  5c, or near a fresh mark) is reported.
- **Target (exact).** `u = s * (mid_{k+12} - mid_k)`, status `two_sided` at k + 12. Horizon 24 h.
- **Primary statistic.** Expanding-past demeaned OLS of `u` on `NR = 1[near]` over near and far units, controls (each multiplied by
  `s` where it is directional): logit `mid_k`, `|mid_k - 0.5|`, `s * chg_1d`, `s * chg_1w` (+ flags), `s *` own 24 h change, `s *`
  own 2 h change, `log` range, `log1p` of `min(age_hi, age_lo)`, 1[mark on a 0.05 multiple], `spread_k`, `log1p volume24hr_k`, log
  hours-to-end (+ flag). Inference 1.7 (DE floor 5.0 in planning and the gate); seed 20261144. Gate: Freedman-Lane, seed 20261244.
- **Mechanism readings (binding label rules).** M1 the skip-slot `s * (mid_{k+12} - mid_{k+1})`: if Supported and not one-sided
  significant: **transient (first pass only)**. M2 the 6 h target. M3 near-high and near-low separately (reported; a one-sided
  effect is labelled **one-sided anchor**).
- **Placebo (reported, label rule).** A **fake mark** `hi - 0.03` (and `lo + 0.03`): units within 1c of it, with `d_hi >= 0.02`,
  against far units. If one-sided significant and at least half of D_NF: **level effect, not the mark**.
- **Secondaries.** S1 the 6 h and 24 h targets by liquidity tier; S2 new highs and lows (momentum, not anchoring); S3 the sports arm;
  S4 `captures_at_extreme` (the "newly certain versus long certain" cousin, descriptive); S5 counts by class, age and range band.
- **Planning MDE (estimate).** Eligible about 40,000 markets a capture (engine coverage note), non-sports a part of that; the share
  near a >= 3-day-old 7-day mark with a state change is **unprobed**: assume 400-1,500 non-sports near units a day (8,400-31,500
  in 21 days), 75% after the first-unit drop, far units 8x. SD of `u` 6c; DE 4-6 (24 h overlap at 2 h steps; slow state); day
  1.3-1.5: **MDE = 0.37-0.52c at 1,500 a day, 0.71-1.0c at 400 a day.** Census-gated; declared now: H may drop.
- **Floors (Unavailable):** < 3,000 near, < 10,000 far, < 300 markets with near units, < 10 days.
- **Economics.** (a) Reported taker buy within 1c below a >= 3-day high in >= $100k markets (sell within 1c above a low), 24 h hold,
  against the 2.9c hurdle. (b) Maker: near the high, no asks at the mark; near the low, no bids; gross `u` by class, "gross, no
  fills". (c) Hold-to-resolution passive entry is an engine (`res_7d`) question, not reported here.
- **Missing data.** As 1.5; `hwm_incomplete` counted; a market whose look-back holds a gap of more than 12 consecutive slots is
  excluded for 84 slots after the gap (counted).

## 6. R: the farmer's choice (CH183)

- **Hypothesis and mechanism.** The liquidity-reward programme scores one-sided quotes when the market's midpoint is in [0.10,
  0.90] (at a reduced weight, `Q_one / c` with `c = 3`) and only two-sided quotes outside it (MAKER_REWARDS_STUDY.md 2; CB6-R's
  convention: 0.90 exactly is inside). A resting quote is a free option to informed takers (Copeland and Galai 1983); inside the
  band a farmer can post only the side it expects not to be hit, so the depth asymmetry carries the farmers' view
  (Glosten-Milgrom). Outside the band the rule forces both sides and the asymmetry is inventory or noise. **Direction: the jump in
  the slope of `c_sw` on `imb` at the cutoff, inside minus outside, is > 0 in rewarded markets, one-sided.**
- **Unit.** Binary market x pass k with `clob_rewards` daily rate > 0 in the sidecar of capture k (rewarded); sweep 1 of pass k
  two-sided on outcome 0 with both depths at the chosen band present; tight (sweep spread <= 0.10); folded sweep mid `f = max(smid,
  1 - smid)` in [0.84, 0.96) and `|f - 0.90| >= 0.005` (donut); tick 0.01 at k (the 0.96 regime change is outside the band);
  1.4 items 1, 5, 6 (sports reported), 7; **state changed since pass k - 1** (the imbalance or the sweep mid changed; dormant books
  excluded). Unrewarded markets meeting the same rules form the placebo population.
- **State (frozen).** `D_bid`, `D_ask` = outcome-0 depths within the **chosen band** (5c if the census median `rewards_max_spread`
  of rewarded band units is >= 3c, else 1c; a pre-declared counts rule fixed in the spec as `r.depth_band`); `imb = (D_bid - D_ask)
  / (D_bid + D_ask)`; `inside = 1[f <= 0.90]`; `rf = f - 0.90`.
- **Target (exact).** `c_sw = smid_{k+1} - smid_k` (outcome-0 sweep-1 mids of passes k and k + 1, status `two_sided`). Horizon one
  pass (about 2 h).
- **Primary statistic.** On rewarded units only, expanding-past demeaned OLS of `c_sw` on `imb`, `imb * inside`, `imb * rf`, `imb *
  rf * inside`, `inside`, `rf`, `rf * inside` and controls `spread_sw`, `log1p D` (`D_bid + D_ask`), E022's `zh` (display versus
  executable depth, LT4 4, from the same capture and sweep), logit `smid_k`, `log1p volume24hr_k`. The statistic is the coefficient
  on `imb * inside` (the jump in the imbalance slope at the cutoff). Inference 1.7 (DE floor 5.0); seed 20261145. Gate: Freedman-
  Lane on the term `imb * inside`, seed 20261245.
- **Identification note.** After demeaning, the coefficient compares within-market slopes of units inside the band with those
  outside; markets need not cross the cutoff. The local-linear `imb * rf` terms allow the slope to drift smoothly with price; the
  cutoff is a venue constant.
- **Placebos (reported, label rules).** P1 the same model on unrewarded units: if its jump is one-sided significant in the same
  direction, **rule not identified**. P2 fake cutoffs 0.65, 0.70, 0.75, 0.80 among rewarded units (6c bandwidth, same donut): if two
  or more are one-sided significant, **smooth price effect**. The reader therefore freezes rewarded and unrewarded units with `f` in
  [0.59, 0.96).
- **Secondaries.** S1 the other depth band; S2 the 6 h sweep target; S3 the min-size view (depth at sizes >= `rewards_min_size` is
  not in the sweep; the touch sizes `*_size_1` against `rewards_min_size`, descriptive); S4 the sports arm; S5 counts per side,
  rewarded and unrewarded, by `rewards_max_spread`.
- **Planning MDE (estimate).** Rewarded markets: 13,683 in the maker-rewards snapshot (2026-10-20, all markets) but 5.2% of the
  engine's eligible markets on 2026-10-21 (about 2,400): the figures disagree and the census settles it. Assume 1,500-6,000 rewarded
  band units a day after the filters (31,500-126,000 in 21 days), half on each side, 80% after the first-unit drop. SD of `c_sw`
  3.5c; DE 4-6; day 1.3-1.5; VIF of the interaction 2-4. Per SD of `imb`: **MDE = 0.27-1.1c; the material contrast (about 2 SD)
  0.55-2.2c** against 0.5c. **Declared now: R is the test most likely to drop at its census.** If it drops, no other test replaces it
  (CH190 is deferred for its own reason, 7.2).
- **Floors (Unavailable):** < 3,000 inside, < 3,000 outside, < 150 rewarded markets, < 10 days.
- **Economics.** (a) Reported taker trade with the deep side when `|imb| >= 0.5` inside the band in >= $100k markets, sweep touch to
  sweep touch, against the 2.9c hurdle. (b) Maker: inside the band, join the deep side; gross `c_sw` by `imb` tercile inside and
  outside, "gross, no fills".
- **Missing data.** `.nosweep` as LT4 13.1 item 2 and 14.1 item 11; sidecar missing or reward fields absent → excluded (counted;
  an older sidecar without `clob_rewards` gives no units, never 0).

## 7. Ideas dropped, deferred or narrowed, and why (uncounted)

### 7.1 Design changes to the round-11 sketches (made before any data; each needs the challenger's acceptance)
- **O (CH182): the tested term is `|g| * m`, not `g * m`.** The round's hypothesis is that "the gain continues" for the active side
  in gain. For NO-active units with `g < 0` (NO holders in gain), the NO token should keep rising, so the YES mid falls; the
  round's `G = g * m` is positive there and its primary predicts the YES mid rises. `G` is right on the `g > 0` half and wrong on
  the `g < 0` half. `O = |g| * m` agrees with the mechanism on all four quadrants (section 4). `g`, `|g|` and `m` are controls, so
  the coefficient is the token-mix moderation only; the plain overhang on `g` (S1) is momentum-confounded and not counted. The
  round's `G` is reported as S2.
- **O: `m * |own 24 h change|` added as a control.** Because `g` tracks the recent move, `|g| * m` could proxy "token-mix flow x
  move size", a flow-continuation interaction; the control absorbs it and a census correlation gate checks the remaining variation.
- **O: 24 h coverage required.** The round allowed a truncated page to use its covered window (flagged). A shorter window changes
  the VWAP's meaning by unit; truncated units are excluded and counted, with a *coverage-limited* label above 5%.
- **H (CH181): the trailing 7-day mark replaces the "lifetime" mark.** AREPO's capture series starts on 2026-10-09 for older
  markets, so a lifetime mark is a different object by market age (the round's `age_series` control and stratum). A 7-day mark is
  the same object for every market, matches the chart's one-week view, and can be rebuilt by the reader from raw captures still on
  the host (8-day retention) at install, without reading the engine's stores or any sealed store. The round's fake mark (the high
  excluding the last 14 days) needs 14 days of look-back, which the host does not keep; it is replaced by the 3c-offset fake mark.
- **H: range >= 5c (common support) and the far-unit folding rule.** Without a range floor, a near unit in a flat market is a
  trivial retest; without a fold for far units, near and far would be oriented differently.
- **F (CH184): neg-risk events and the fee category leave the primary hierarchy.** In a neg-risk event the sum constraint makes the
  siblings' leave-one-out mean mechanically opposite in sign to an own-news move, and a "common" move (all members up) is an
  overround shock that arbitrage reverses: the contrast would be positive by mechanics. The category mean is one value per category
  per pass (CH158's death). Both are reported secondaries (S3, S4).
- **F: the sibling receipt guard** (1.3), taken from the engine's event family.
- **J (CH180): print prices snapped to the tick grid** before counting levels, so an aggregated off-grid print (a walked order)
  cannot create a level; and a third mechanism label for 0.01-tick books.
- **R (CH183): the primary is the rewarded-market jump, not a rewarded-minus-unrewarded difference in slopes.** A four-cell
  difference roughly doubles the variance of an already borderline test; the cutoff identifies the jump on its own under
  continuity, and the unrewarded jump is the placebo label P1. **The depth band is census-fixed** (farmers quote within
  `rewards_max_spread`, often wider than 1c).

### 7.2 Round-11 ideas not taken into LT5
- **CH185 (clip trains): dropped.** Clips are a subset of trains (same-market prints at regular gaps), and the round's own rule
  excludes trains; its arm 2 (`rt_share`) needs `side`. The size-identity measure has no probe and no census; a counts map may be
  proposed in a later family.
- **CH190 (the makers' vote): deferred to after E022's analysis (2026-11-17).** Its state `v = sign(x) * imb_5c` from sweep 1 of
  pass k is, up to sign, LT4 E022's pinned control `dimb` (LT4 14.1 item 5), on overlapping traded non-sports movers and with the
  same sweep-to-sweep target. Counting it now would make one coefficient both a nuisance term in E022's model and a primary here on
  shared origins. It is also not an automatic replacement for R (7.1).
- **CH187 (deadline moves) and CH188 (sibling birth): deferred.** Both are unprobed (L 3) and their populations may be tens a day;
  the round itself asks for census maps first. Counts-only maps can be drafted for a later family; no LT5 slot.
- **CH186 (calibration by provenance) and CH189 (overdue by the clock): engine-first.** Their targets are resolutions (`res_7d`);
  a 21-day mid-target version would double-count E015 (CH186) or be underpowered (CH189). They go to the signal engine as challenger
  families with embargo entries where they shadow E015 (section 10).
- **Taker routes as primaries, resolution fetches as primaries:** none (round 11 section 4).

### 7.3 Census drops
None yet. Census drops will be recorded here, with their counts, before the pin.

## 8. Pre-registration censuses (counts only; before registration; worn pre-window data; no target read)

Each census runs once, reads origin-side fields only (no quote at any later capture, sweep or sample, no target, no P&L), prints
counts, and is committed with its sha256 before the registration commit. **Every gate threshold below is stated now, before any
census.** A failed gate drops that test before registration (uncounted); `k_tests` lists the survivors. Input identity (L3): the
census refuses unless every input file it opens is named in a seal with an equal sha256.

**Inputs (all started before 2026-10-22T00:00Z, before the LT2-LT4 windows).**
- **Flow censuses (J: CJ; O: CO):** the **23 sealed active-frame samples of 2026-10-16 and 10-17** (`seals/lt3_census_inputs_C2.json`,
  the files LT3's C2 and LT4's CF read) with their captures and look-back slots k - 12 .. k from the existing capture seal
  `seals/lt4_census_inputs_captures.json` (2026-10-14T22:31Z .. 10-17). No new seal is needed. The restore trees of q0471 and
  q0480 are used if still present; otherwise the same files are restored from the same releases and re-hashed against the same
  seals.
- **Capture censuses (F: CF5; H: CHW; R: CRW):** the complete captures of **UTC 2026-10-20 and 2026-10-21** (rows, sidecar,
  manifest) with H's 84-slot look-back from **2026-10-13T00:31Z**, and sweep 1 of the census passes. New seal
  `seals/lt5_census_inputs_captures.json`, written from the releases' `files.sha256` before any LT5 census runs. These days carry
  the reward fields R needs; the 2026-10-21 02:31 pass never ran (host stall) and that slot stays missing. J4-R's
  `[2026-10-16, 2026-10-21)` refusal covers maker mark-out objects only; nothing here reads a mark-out.

**Projection** = census count x 21 / census days (an estimate). Distinct events: `E_2d + (E_2d - E_day1) x 19` (LT3's rule).
**Effective** counts = units in markets with >= 2 units of the test's population in the census days. **Design effect:**
`DE_gate = max(floor, 1 + (m_21 - 1) x 0.02)` with `m_21` the projected mean cluster size by event (LT4 14.1 item 8, 15.1 item 4);
floors 3.0 (J, F), 4.0 (O), 5.0 (H, R). **MDE gate formula:** `3.388 x SD x sqrt(1/n1_eff + 1/n2_eff) x sqrt(DE_gate) x 1.5`
for class contrasts; `3.388 x SD / sqrt(n_eff) x sqrt(DE_gate) x 1.5 x sqrt(VIF_w) x gap` for slopes (`VIF_w` = the within-market,
expanding-past-demeaned VIF of the tested term on its controls). Correlations marked "within" are on expanding-past-demeaned
values and bind; pooled values are printed.

| Test | Census | Gate (all must hold; NaN fails) | Values fixed into the spec |
|---|---|---|---|
| J | CJ | `ts` second-level (share of interval rows with `ts mod 60 != 0` >= 50%); projected qualifying units (all filters of section 2) >= 120 a pass (>= 30,240 in 21 days); jump and grind each >= 20% of qualifying units; jumps from 0.01-tick books <= 80% of jumps; `interval_truncated` <= 5% of traded sampled movers; within `|corr(1[jump], fresh)|` <= 0.5 and `|corr(1[jump], log1p n_int)|` <= 0.5; permutable share >= 50% (day, else block2); **pessimistic MDE <= 0.5c** (SD 4c) | `perm_stratum`, `exclude_family` |
| F | CF5 | projected idiosyncratic >= 6,300 and common >= 6,300 (>= 300 a day each, primary population after the family rule); within `|corr(1[common], 1[parallel quote-only])|` <= 0.5; common units in crypto series <= 90%; `guard_loss` <= 20% of otherwise-formed units; permutable share >= 50%; **pessimistic MDE <= 0.5c** (SD 4c) | `perm_stratum`, `exclude_family` |
| O | CO | projected covered units >= 600 a pass (>= 151,200 in 21 days); `trunc24` <= 10% of units with >= 10 rows; `|m| > 0.9` in <= 80% of units (else `O` collapses to `|g|` times a constant); within-market IQR of `O` >= 1c in >= 50% of markets with >= 6 units (and >= 30 such markets); within `|corr(zO, z own 24 h change)|` <= 0.5 and within `|corr(zO, z(m * |own 24 h change|))|` <= 0.85; permutable share >= 50%; **pessimistic MDE per SD x tercile gap <= 0.5c** (SD 5c, VIF_w computed) | `c_O`, `s_O`, `zO` tercile cuts and gap, `perm_stratum`, `exclude_family` |
| H | CHW | projected near units >= 8,400 (>= 400 a day) and far >= 42,000 (>= 2,000 a day), non-sports, after the family rule; crypto-series share of near units <= 70%; within-market SD of `d_hi` >= 1c for >= 50% of markets with >= 50 present slots in the look-back and census days; `hwm_incomplete` <= 20% of otherwise-eligible units; within `|corr(1[near], s * own 24 h change)|` <= 0.5; permutable share >= 50%; **pessimistic MDE <= 0.5c** (SD 6c, DE floor 5.0) | `perm_stratum`, `exclude_family` |
| R | CRW | projected rewarded units >= 12,600 inside and >= 12,600 outside (>= 600 a day each); unrewarded >= 6,300 each side (>= 300 a day); within-market IQR of `imb` >= 0.1 in >= 50% of rewarded markets with >= 10 units (and >= 30 such markets); carrier: in >= 30% of rewarded inside units at least one side's depth in the chosen band is >= `rewards_min_size`; permutable share >= 50%; **pessimistic MDE per SD x 2 <= 0.5c** (SD 3.5c, DE floor 5.0, VIF_w computed) | `r.depth_band`, `perm_stratum`, `exclude_family` |

- **Descriptive (no gate):** every census prints the sports split, the top series family's share, the pairwise unit overlap with the
  other LT5 populations, and the class shares by liquidity tier. CF5 prints the family-level split and neg-risk exclusions; CHW
  the near/far split by age and range band; CRW the `rewards_max_spread` distribution and the two rewarded-market counts
  (snapshot-style versus sidecar) that disagree in section 6.

**Census jobs (drafts under `docs/research_lab/queue/drafts/`; README format; ids checked unused across `queue/` on every local
and remote branch on 2026-10-21).**
- `q0560_lt5_census_restore_captures` (lane `net`, 1,200 MB): restore captures 2026-10-13T00:31Z .. 2026-10-21T22:31Z (rows,
  sidecar, manifest) and sweeps of 2026-10-20/21 (rows, manifest) byte for byte from the data releases into a scratch tree
  (release tags to be confirmed against the release list before promotion; the catalogue lists tags only to 2026-10-20). Then
  write and commit `seals/lt5_census_inputs_captures.json` from the releases' `files.sha256`. Disk about 2-3 GB (estimate).
- `q0561_lt5_census_captures` (cpu, 1,500 MB): `census-captures` for CF5, CHW and CRW on the sealed captures and sweeps.
- `q0562_lt5_census_flow` (cpu, 1,200 MB): `census-flow` for CJ and CO on the 23 sealed samples and the LT4 capture seal.
- `q0563_lt5_size_check` (cpu, 400 MB): the section 1.8 size check, once, on the code to be pinned (simulation only).
All four are DRAFT and must not be promoted until the challenger review of this file, the code and the freeze check exist; the
scripts they name do not exist yet. Each counts 0.

## 9. Implementation plan (no code in this commit)

### 9.1 Modules to be written
- `backend/astrolabe/research_lab/live_tests5_base.py`: **vendored, unmodified copies** of the LT3/LT4 functions LT5 uses
  (`classify`, `move_join`, `series_frame`, `category_cols`, `read_series/status/sweep`, `outcome_h/s`, `status_codes`,
  `is_late`, `signs`, `token0_map`, `load_sample`, `project_events`, `block_anchor`, `fl_perm_gate`, `fit`, `verdict`,
  `attach`, `underpowered`, `attrition`, `lee_bounds`, `paper_taker`, `econ`, `gross`, `sim_*` worlds, `bd.holm`,
  `bd.expanding_demean`), with a provenance header naming each source module's sha256 at copy time and a unit test that the
  copies equal those sources at that sha. **Why vendor rather than import (question 9):** LT4 imports LT3 under pinned hashes,
  so any later LT3/LT4 deviation fix would void every LT5 line. LT5 registers after both and must not be voided by their
  maintenance; vendoring keeps the validated code and removes the coupling. The vendored module is in LT5's own hash map.
- `backend/astrolabe/research_lab/live_tests5.py`: the reader. `run_once()` (internal non-blocking flock on
  `live_tests5/run.lock`) finds new complete captures, their pass's sweep 1 and active trade sample, and in order writes,
  write-once (`%.17g`, atomic hard link):
  1. `series/<capture>.csv.gz` and `status/<capture>.csv.gz` (compact: market, event, series key, neg-risk, bid, ask,
     `last_trade_price`, `volume24hr`, `liquidity`, `chg_*`, end date, tick, reward fields, sports flag, receipt);
     `sweeps/<capture>.csv.gz` (outcome-0 sweep-1 quote, sizes, 1c and 5c depths, receipt);
  2. `hwm/<capture>.parquet` (per market: `hi`, `lo`, `age_hi`, `age_lo`, present-slot count over slots k - 84 .. k - 1,
     computed from `series/` only; rebuildable, write-once per capture);
  3. frozen units: `path/frozen/<sample>.csv.gz` (J), `family/frozen/<capture>.csv.gz` (F), `overhang/frozen/<sample>.csv.gz`
     (O), `mark/frozen/<capture>.csv.gz` (H), `rule/frozen/<capture>.csv.gz` (R; `.nosweep` when no complete sweep existed at the
     deadline);
  4. `<kind>/outcomes/<id>.h<j>.csv.gz` and `.s<j>.csv.gz` (status and quote at slots k + 1, k + 3, k + 12; sweep-1 quote of
     passes k + 1, k + 3);
  5. `passes.jsonl`.
  An install-time `backfill-series` subcommand writes `series/` for the 84 slots before `REGISTERED_UTC` from raw captures still
  on the host (lines marked `lookback`, never units). Collection of a kind is switched off when its test is not in `k_tests`
  (LT3 13.16 fix 2).
- `backend/astrolabe/research_lab/live_tests5_analysis.py`: the single analysis (1.7-1.10, Holm over k, counting), the size check
  (1.8).
- `backend/scripts/run_live_tests5.py`: `run`, `backfill-series`, `ops-stats`, `census-captures`, `census-flow`, `size-check`,
  `analyze`.
- Spec `backend/astrolabe/research_lab/model_specs/live_tests5_v1.json`: every constant, k, seeds (estimators 20261141-45, gates
  20261241-45, F's fake family 20261342, size check 20261147), dates, census scales, cuts and rules, the three-module
  `code_sha256` map (`live_tests5.py`, `live_tests5_analysis.py`, `live_tests5_base.py`) and the imported sports-rule hash.
- `battery2.KIND_RULES["live_tests5"]` (fail-closed counting entry).

### 9.2 Resources, collection plan and install
- **No new collector and no network.** A pure reader of the pass's own outputs, at the pass cadence (trade samples are consumed
  online; three-day host retention).
- **Memory (estimate):** per pass two captures' selected columns, one sidecar, one sweep and one trade sample (as LT4), plus H's
  look-back: 84 compact series files of (market code, mid) as float32, about 0.4 MB each, about 4 million rows in memory (under
  100 MB). Target peak < 450 MB; `mem_mb 480` (below the queue's 500 MB blackout exemption). Measured in the host dry run before
  the pin; the design is revised if the peak exceeds 450 MB.
- **CPU:** about 1-3 min per steady-state pass (estimate; family means and the H extreme are group-bys); a 12 h backlog pass
  about 10-15 min (LT3's dry run: 13 min for 40 items).
- **Disk:** about 1.2-1.6 GB over the window plus look-back (estimate; compact series with reward and tick fields, `hwm/`
  parquet about 1 MB a capture); the reader stops writing at 2.0 GB in `live_tests5/` and exits 75 above the data-dumps cap.
- **Install (recommended):** host cron `5-59/20 * * * *` (starts at :05, :25, :45, offset 5 min from LT3's `*/20` and LT4's
  `10-59/20`), own `flock` on `~/arepo/run/live_tests5.lock`, `nice -n 19`, `oom_score_adj 1000`, `ulimit -v 983040`,
  `--max-items 40 --data-dumps-cap-gb 40`. The three LT readers each stay under 480 MB, so their simultaneous peak (in a
  backlog only; steady-state passes take seconds) is under 1.5 GB; the dry run checks MemAvailable beside the collector and the
  engine tick (question 13). A fallback queue reader (lane `net`, `mem_mb 480`,
  repeat; id assigned at install) only if the cron entry is not installed, **never both**. `backfill-series` runs once at install,
  at least 24 h before `REGISTERED_UTC` and before slot `REGISTERED_UTC - 7 d` rotates off the host (8-day retention: by
  `REGISTERED_UTC + 1 d`). Installing is a host change under the standing collection authorisation, done by the orchestrator.

### 9.3 Tests to be written (`backend/tests/unit/test_research_lab_live_tests5.py`, synthetic only)
- J: YES-terms mapping, tick snapping (an off-grid aggregated price does not add a level), `g_path` and classes, `steps >= 3`, tick
  change exclusion, interval coverage and truncation, rows at or after `t_k` ignored.
- F: the hierarchy (non-neg-risk event, then series; neg-risk and category never), leave-one-out mean including zero movers, the
  receipt guard (a sibling received 6 s after the unit is dropped), class thresholds, the fake-family draw is seeded and disjoint.
- O: VWAP, token shares, `O = |g| * m` on all four quadrants (the sign table of 7.1), 24 h coverage, `x6` never used as a state.
- H: the 84-slot extreme and age, `hwm_incomplete`, the range floor, near/far/fold rules, the state-change rule, the fake mark,
  `backfill-series` lines never become units.
- R: folding, donut, tick regime, depth-band rule, `inside` at exactly 0.90, the unrewarded and fake-cutoff populations, the
  older-sidecar case (no units).
- Shared: causality (future captures, sweeps and samples with wild prices leave every frozen line byte-identical); late refusal,
  write-once, `.nosweep`; the dry-run guard; `%.17g` round trip; the run lock; `ops-stats` reads no price column; vendored-code
  provenance; the three-module hash and the joint reader sha; the counting rule equals k; Holm; the p = max rule; the analysis
  refuses before the date, an unpinned, null or NaN spec, or a `k_tests` naming a dropped test; sealed censuses (counts only,
  tampering refused); each MDE gate formula; the size check on small runs with planted effects (each primary detects a planted
  effect, and the R interaction scenario holds size on a small run); an end-to-end synthetic analysis with a reduced `k_tests`.
- At registration: `SPEC_SHA256` and the three module hashes are pinned together.

## 10. Signal-engine mapping (each test as a challenger feature family)

Every family below is point-in-time from the origin capture, its pass's sweep 1 and trade sample, or the engine's own earlier
`quotes/` files (DESIGN_V1 16 causality). Each is an **auxiliary family** (own write-once table, its own version string, new spec
versions; the v1 store is never rewritten). **Embargo first** (DESIGN_V1 8): any challenger that isolates one of these families
must carry its token until LT5's analysis date, proposed **2026-11-22T00:00Z** (moved later if LT5's window moves; never earlier),
from the day LT5's design is accepted, because a non-embargoed leaderboard would be a development look at a registered LT5
hypothesis before its single analysis.

| Test | Family (aux version) | Columns (NaN = missing) | Source and clock | Embargo token -> until |
|---|---|---|---|---|
| J | `tradepath` (`se-aux-tradepath-v1`) | `tp_grind_2h` (`g_path`), `tp_maxstep_share`, `tp_n_int` | the pass's trade sample, rows `ts < t_k` (NaN below 3 rows; coverage 4.3% like flow) | `tradepath` and the existing `flow` token -> 2026-11-22 |
| F | `relmom` (`se-aux-relmom-v1`) | `rm_rel_2h = x - xbar`, `rm_rel_24h`, `rm_common_share_2h = w`, `rm_family_size`, `rm_level` | the capture listing and the previous slot's `quotes/`, with the 5 s sibling guard | `relmom` -> 2026-11-22; **and `event` (se8's `ev_sib_d2h`) -> 2026-11-22, recommended (1.11)** |
| O | `overhang` (`se-aux-overhang-v1`) | `oh_overhang_24h = O`, `oh_vwap_gap_24h = g`, `oh_token_mix_24h = m` | the pass's trade sample, 24 h coverage required | `overhang` and `flow` -> 2026-11-22 |
| H | `path` (`se-aux-path-v1`) | `pa_d_hi_7d`, `pa_d_lo_7d`, `pa_age_hi`, `pa_age_lo`, `pa_range_7d`, `pa_n_new_highs_7d`, `pa_captures_at_extreme` | the engine's own `quotes/` for slots k - 84 .. k - 1 | `path` -> 2026-11-22 |
| R | `rewardbook` (`se-aux-rewardbook-v1`) | `rb_imb_band`, `rb_rewarded`, `rb_inside`, `rb_imb_x_inside`, `rb_minsize_touch` | sweep 1 of the pass and the capture's sidecar | `rewardbook`, `book`, `rewards` -> 2026-11-22 |
| (CH186) | `provenance` (`se-aux-provenance-v1`) | `pv_q7` (quoted share of 7-day absolute moves, E015 labels), `pv_traded_share_24h`, `pv_n_moves_7d` | `quotes/` | `provenance` -> 2026-11-16 (E015's analysis plus a day) |
| (CH189) | `overdue` (`se-aux-overdue-v1`) | `od_hours_overdue`, `od_bydate_template` | the origin row and sidecar | none (no live test) |

The engine's yardstick (log-loss gain on `dir_2h`, `dir_6h`, `dir_24h`, `res_7d` under `se-promotion-v1`) is a different question
from each LT5 primary (a within-market continuation contrast). A Supported LT5 primary makes its family a candidate; an engine gain
never changes an LT5 verdict and an LT5 verdict never promotes a model. Building any of these families is signal-engine work for a
later unit, not part of this draft.

## 11. Disclosures

- **Selection history.** The five tests are round 11's top five (Fable xhigh creative pass, written 2026-10-21 on `cee77db6`),
  written with no host probe from round 9/10 probes, LT3/LT4 census figures, the cost-model calibration, the maker-rewards snapshot,
  WS1 and the engine coverage note. They were ranked by a judgement score. Three sketches were changed here (7.1) before any data.
- **The designer** read the round-11 file, LT2-LT4 designs and responses, the ledger's LT3/LT4/WS1/engine entries, the engine's
  NORTH_STAR, DESIGN_V1 and STATUS, the queue README and LT4's queue drafts. No data, host, outcome, price after an origin or P&L
  was read. No code was written.
- **Closest prior AREPO tests.** J: E021, E016 (dropped), E004/E006, CH20/CH93. F: E015, E019 (dropped), E005, SB2-J5, L1-L4,
  XM1-XM6, CH158 (dropped), se8. O: CH42, E013, E016, E023 (dropped), CB10/CB12 VWAPs. H: E002/E004/E006, E012, HB1 PX1/PX2,
  CH20/CH93. R: E003 (imbalance inconclusive), CB6-R, CH116, E020's reward flag, E022, E025.
- **Mechanics stated up front.** J: tick coarseness makes jumps by construction (tick rules, M3) and a jump's last print can sit at
  the origin (M1, M2). F: common moves are often parallel quote re-centerings (E015's class, controlled and gated), and a lone
  mover's siblings may catch up (M3). O: `g` is mechanically tied to momentum (controls, gates, S1 not counted). H: a one-sided ask
  at the high leaves the mid half a spread below the mark (two-sided tight quotes, 24 h horizon, M1). R: the spread itself jumps at
  the cutoff (CB6-R's object; spread controlled, imbalance in shares).
- **Shared data.** LT2-LT4, E011, CB18, E025, E026 and the engine read the same captures, sweeps and samples. Overlap only.

## 12. Open questions for the challenger review

1. **O's sign (7.1).** Is the correction from `G = g * m` to `O = |g| * m` right, and is the linear model `y6 = a g + b |g| m` the
   right reading of "the active side in gain continues"? Should the primary instead be an active-token target (`sign(m) * y6`
   on the active side's gain) restricted to `|m| >= 0.5`?
2. **F and the engine's se8.** se8 (not embargoed) scores `ev_sib_d2h` beside the own 2 h change on `dir_2h` from about
   2026-10-27. Embargo `event` until LT5's analysis (recommended), or register F as "not fresh"? Does the answer depend on F's
   hierarchy excluding neg-risk events (se8's `ev_sib_d2h` covers every event)?
3. **F's hierarchy.** Is dropping neg-risk events and the category from the primary sound, or should neg-risk members enter with
   the event's sum-of-mids change as a control? Is a 5 s receipt guard enough when the guard selectively removes large events?
4. **J's target.** LT4 R1 moved E021's primary to the skip-slot target because the fresh class is the bounce. J keeps the 2 h `c`
   with `fresh` and `log1p age` as controls and the skip-slot as a binding label. Is that enough, or should J's primary be the
   skip-slot persistence too?
5. **J's classes.** With `steps >= 3`, a 3-tick move is a jump only if every print is at one price. Are the 0.25 / 0.75 cuts and
   the tick snapping acceptable, or should the class be a within-tick-stratum tercile of `g_path` fixed at the census?
6. **H's mark.** Is the trailing 7-day extreme an acceptable replacement for the round's lifetime mark? Is the 3c-offset fake mark
   a meaningful placebo, and is the far-unit fold (toward the nearer mark) right?
7. **H's power and dependence.** The 24 h target overlaps eleven passes; is `DE_gate` floor 5.0 plus the MA(11) scenario and
   two-day blocks adequate, or should H use one unit per market per UTC day (the first near or far unit), trading count for
   independence?
8. **R's estimand.** Rewarded jump with the unrewarded jump as a placebo label, or the four-cell difference in jumps as the
   primary? Is the census-fixed depth band (5c if the median `rewards_max_spread` >= 3c) acceptable, and is the "carrier" gate
   (a side's band depth >= `rewards_min_size` in >= 30% of inside units) a real test that farmers are present?
9. **Vendored code (9.1).** Vendoring LT3/LT4 functions instead of importing them under pinned hashes: acceptable, given that
   LT4's import pins mean a later LT3 deviation fix voids LT4?
10. **Census inputs.** Reusing the LT3 C2 samples (10-16/17) for J and O, and new capture days 10-20/21 for F, H and R (needed for
    H's look-back and R's reward fields): acceptable, or should every LT5 census use one set of days?
11. **Gates.** Are the correlation caps right, in particular O's `|corr(zO, z(m * |change|))| <= 0.85` (looser than 0.5 because
    `O` is built from controls; a binding 0.85 size scenario is added)? Should the J and F correlation gates also cover the
    liquidity tier?
12. **Fixed end.** Round 11 offers a counts-triggered 28-day extension; LT5 keeps LT4's fixed end. Agree?
13. **Three readers.** Is a third 20-minute reader (offset 5 min) safe on the 1 OCPU / 5.6 GB host alongside LT3, LT4, the
    collector and the engine tick, or should LT5's reader run once a pass (`45 1-23/2 * * *`)?
14. **Holm and k.** With R and probably H or O likely to drop, is it acceptable that k is set by census counts alone, with no
    replacement test (CH190 deferred)?

## 13. Draft ledger block (DRAFT, not registered, not counted)

> ## LT5 (five round-11 candidates) — DRAFT pre-registration (not registered, nothing counted, no code)
> - **Design:** `docs/research_lab/LIVE_TESTS_5.md` on `feat/live-tests-5`. Pure reader of streams the host already writes
>   (complete captures, sidecar, sweep 1, active trade samples); no network, no new collector, < 450 MB target, `mem_mb 480`;
>   separate store `live_tests5/`; LT3/LT4 functions vendored (not imported).
> - **J** (CH180) jump minus grind, 2 h continuation, all categories, > 0; MDE about 0.29-0.64c vs 0.5c; census-gated.
> - **F** (CH184) idiosyncratic minus common (non-neg-risk event, else series), 2 h continuation, non-sports, > 0; MDE 0.13-0.24c.
> - **O** (CH182) active-side overhang `|g| x m`, 6 h YES change, all categories, > 0 (sign corrected from the round's `g x m`);
>   tercile MDE 0.32-0.86c; may drop.
> - **H** (CH181) near minus far from a >= 3-day-old 7-day extreme, folded 24 h change, non-sports, > 0; MDE 0.37-1.0c; may drop.
> - **R** (CH183) jump of the imbalance slope at the 0.90 reward cutoff in rewarded markets, sweep-to-sweep, > 0; likely to drop.
> - **Dropped/deferred:** CH185 (trains rule, `side`), CH190 (E022's `dimb` control; after 2026-11-17), CH187/CH188 (maps first),
>   CH186/CH189 (engine-first).
> - **Family:** Holm over k <= 5, one-sided, alpha 0.05; p = max(event t, two-way, day t); Freedman-Lane gates; window proposed
>   `[2026-10-30T00:00Z, 2026-11-20T00:00Z)`, single analysis on or after 2026-11-21T12:00Z; register after LT4.
> - **Status:** DRAFT awaiting the challenger review, code, freeze check, censuses (q0560-q0562), size check (q0563), dry run,
>   pins and registration. Engine: embargo tokens for the LT5 families (and, recommended, `event`) to 2026-11-22 before any
>   isolating challenger shows a score.
