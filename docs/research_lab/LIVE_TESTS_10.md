# Live tests 10 (LT10): the fine-clock family on E009's stream (CH224, CH223, CH222), DRAFT pre-registrations

**Status: DRAFT, NOT FROZEN. No challenger review yet (R1 not run). Not registered, nothing counted, no code, no seal, no
census run. E-numbers unassigned.** Label of the whole family, fixed now: **`informed (E009, E010)`** (registration follows
E009's and E010's single analyses, whose results will be known; section 1.1).
Drafted 2026-10-23 (about 03:00-05:00Z) on branch `feat/live-tests-10` from the `chore/arepo-claude-setup` tip `c23b5a52`, a
design-only first commit like the first commits of LT3-LT9. LT10 takes the next free E-numbers at its own registration, in
the order CH224, CH223, CH222 (round 15's rank order). If every test drops at its census, LT10 is not registered (recorded in
the ledger; nothing counted). Before registration this needs, in order:
1. a challenger review (`science-reviewer`, R1) of this file, the response, and any re-check;
2. the **design-text freeze commit** (section 1.1) **before 2026-11-03T02:00:00Z** (E009's earliest analysis time) and before
   `T_E009`; a freeze after either drops the whole family (1.1);
3. the code (section 8), with a freeze check of the census and size-check code against sections 1.8, 1.8.1 and 7, on
   synthetic data only (it can run before 2026-11-03);
4. the **collection decision D-LT10-1** (section 8.2: the quote stream must keep running after E009's window, and the
   poller's 2 GiB cap must not stop it), executed by the orchestrator at E010's analysis commit;
5. the census inputs' restore (sidecars only, if needed) and seal (section 7), each once, **after E010's analysis commit**;
6. the counts-only censuses (section 7), each once, cheapest kill first, which fix k and every census-fixed spec value;
7. the size check at >= 2,000 worlds on the code to be pinned, through the census-fixed strata (section 1.8);
8. a reader dry run on the post-window quote stream with peak RSS measured, and a five-day stream burn-in (section 8.2);
9. the engine embargo entries of section 9 verified in `config.EMBARGO` and `signal_engine/CANDIDATES.md`; the `SPEC_SHA256`
   and `code_sha256` pins; the ledger entry, at least 24 h before `REGISTERED_UTC` (section 8.4).
Until the pin exists, every line a reader writes is `prospective_unregistered` by construction.

This is research tooling. AREPO never trades. No edge, calibration, profitability or tradability claim exists or is implied.
Every count quoted from round 15, the E009/E010 ledger entries, `CROSS_VENUE_LIVE.md`, the readiness audit or the cost model
is a **counts-only operational or development figure**. Every MDE here is a **planning estimate** built on stated
assumptions, not a measurement. Nothing here read a price after an origin, an outcome, a target, a prediction line, a census
output or a P&L. No host, network, `ssh`, `data-dumps` or evidence-JSON read was used to write it (reads listed in 10).

Source ideas: `CREATIVE_HYPOTHESES_2026-10-29.md` (round 15) section 3, ranks 1-3 and their pre-registration sketches:
**CH224** (the hedged maker's price), **CH223** (the other venue's makers flinch first) and **CH222** (the venue that traded
first), taken in the round's own recommendation ("if the LT10 designer wants k = 3, CH224, CH223 and CH222 are the three ...
registered after E010's analysis and only if the poller still runs"). Ranks 4-10 are not taken (section 5). The design is
written to round 14's rules 1-11 and round 15's additions 12-14 (round 15 section 0.2), to LT4's lessons L1-L15 and the later
rulings LT7-LT9 carry (1.0). Every design change from the round's sketches is listed with its reason in 6.1; all were made
before any data.

## 0. Summary

| Handle | Idea | Hypothesis (direction) | Population | Primary | Planning MDE (DE 51, multiplier 3.47, overlap factor 1.1): low / high; at a quarter of the low count; F-MDE | Floor |
|---|---|---|---|---|---|---|
| **CH224** | the hedged maker's price | Within pair, Polymarket's spread change over the next 20 minutes rises with Kalshi's spread innovation over the 10-minute state window `(s0, t]`, the two venues' spread levels, Polymarket's own concurrent spread change and E009's seven features held fixed (one-sided > 0: Kalshi tightened, Polymarket tightens next) | every eligible pair x 10-minute origin (non-sports ex-crypto by default) on the stream's 120 s polls | expanding-past pair-demeaned OLS of `dsP = sP(t + 20 min) - sP(t)` on `zdsK = (sK(t) - sK(s0)) / scale_K`; **block Freedman-Lane gate in pair x UTC day strata; far-future F binding** | slope (at the census gap of 2.2 SD) **0.30c / 0.23c**; quarter 0.60c; **F 0.45c / 0.35c (binding)**; the F-MDE gate passes 1.0c from about 30,650 counted units (21 days) | 1.0c (spread) |
| **CH223** | the other venue's makers flinch first | Within pair, on origins where Kalshi's mid did **not** move and Kalshi showed no trade over `(s0, t]`, Polymarket's next 20-minute \|mid move\| is larger when Kalshi's makers withdrew (spread widened >= 2c, or a touch size fell >= 50% at an unchanged touch price) than when they did not (one-sided > 0) | quiet untraded pair x origins; withdrawal origins against no-withdrawal origins | expanding-past pair-demeaned OLS of `a = \|mP(t + 20) - mP(t)\|` on `pull`; realised-volatility and liquidity controls; **block FL gate in pair x UTC day strata; binding volatility-leak world; F a reported label (fixed now)** | class contrast **0.47c / 0.26c**; quarter 0.95c (fails 0.5c); F (label) 0.75c / 0.42c; the MDE gate passes 0.5c from about **2,913 counted withdrawals in 21 days (about 139 a day)** | 0.5c (magnitude) |
| **CH222** | the venue that traded first | Within pair, among origins where Kalshi's mid moved (`\|dk1\| >= 0.5c`, E009's own object), Polymarket's 20-minute move in the direction of Kalshi's move is larger when Kalshi's `last_price` changed in the window (a traded move) than when it did not and Kalshi's 24 h volume did not rise (a quote-only move), E009's seven features sign-adjusted and held fixed (one-sided > 0) | Kalshi-move pair x origins; traded against quote-only | expanding-past pair-demeaned OLS of `c = sign(dk1) x (mP(t + 20) - mP(t))` on `traded`; activity interactions; **block FL gate in pair x two-day-block strata; binding activity-leak world; F a reported label (fixed now)** | class contrast **0.63c (fails 0.5c) / 0.44c**; quarter 1.25c; F (label) 0.93c / 0.66c; the MDE gate passes 0.5c only from about **9,650 counted traded moves in 21 days (about 460 a day)** | 0.5c (20-min mid) |

- **Family:** one Holm family over the k surviving primaries, one-sided, familywise alpha 0.05, separate from E009-E011, LT2
  (E012-E014), LT3 (E015), LT4 (E022), LT5-LT9, E025 and E026. **Provisional k <= 3.** A test whose census gate fails is
  dropped *before* registration, uncounted; k is the number that survive, fixed in the spec (`k_tests`) at registration and
  never changed. A primary that is unavailable or fails its gate enters Holm with p = 1. No replacement test is added after a
  census drop. **The family-wide census (CF10, section 7) drops all three at once** if the pair list holds fewer than 60
  eligible pairs or fewer than 30 events on the census days (round 15's gate, adopted from CB15-P).
- **Window (proposed; the earliest the data and the governance allow, 1.1):** 10-minute origins `t` in
  `[REGISTERED_UTC + 70 min, END_UTC)`, 21 days, **`REGISTERED_UTC = 2026-11-10T00:00:00Z`**, `END_UTC = 2026-12-01T00:00:00Z`;
  single analysis on or after **2026-12-02T12:00:00Z**. It cannot start earlier: the stream is sealed to LT10 until E010's
  analysis commit (after 2026-11-03T08:00Z), and the census, size check, reader dry run, pin and a five-day burn-in of the
  continued stream must fit between that commit and the start (1.1). Never before 2026-11-10T00:00Z; slides later with any
  step; **not registered at all if `REGISTERED_UTC` would fall after 2026-11-30T00:00Z** (the census would be a month stale).
- **Freeze early, census after E010.** Design-text freeze before 2026-11-03T02:00Z, so that the states, estimators, gates and
  thresholds are fixed before any E009 or E010 result exists. The census reads only origin-side fields of the stream's worn
  days `[2026-10-21, 2026-10-31)` and runs only after E010's analysis commit; no LT10 process opens a prediction, outcome or
  analysis file of E009 or E010 at any time (1.6). **LT10's registration does not depend on E009's or E010's verdicts**
  (declared now): only the collection decision and the census gates decide it.
- **Collection dependency (declared; section 8.2).** E009's poller has a hard 2 GiB cap on its directory (`CapReached`, exit
  3; the supervisor does not restart it). The readiness audit's projection (425 MB on 10-19, about 60 MB a day) puts the cap
  at about **2026-11-16**, inside the proposed window. LT10 therefore needs a light collector change at E010's analysis commit
  (decision **D-LT10-1**, for the orchestrator; recommended route: a quotes-only successor poller in new files, same pair
  refresh, same endpoints, same 120 s grid, same line schema, its own directory). No new external service; no owner decision
  unless the host's free disk is insufficient (CLAUDE.md storage stop rule). Without it, LT10 is not registered.
- **Expected outcome, declared now (honest prior odds; the designer's judgement, not measurements).** The **family census**
  is the first risk: E009's pilot saw about 70 pairs in 22 events with complete features (27 events after the hand-verified
  refresh), the engine's 10-20 check 116 pairs; ex-sports and ex-crypto the event count is unprobed and may sit below 30.
  CF10 passes with odds about **0.40**. Given CF10: **CH224** 0.60 (its risks are a Kalshi spread that rarely changes and a
  Polymarket spread pinned at one tick or at the reward band); **CH223** 0.45 (the withdrawal share and the bot-refresh and
  hour gates; its MDE gate needs about 2,913 counted withdrawals against 3,257 at the low planning end); **CH222** 0.30 (its MDE
  fails the floor at the low planning end and needs about 9,650 traded moves). **Expected k at census about 0.5 (0 to 3); the
  chance that no LT10 test registers is about 0.66; the expected number of valid verdicts is about 0.25** (CH223's
  volatility-leak world and CH222's activity-leak world are binding and may fail). Every taker check is expected to be "not
  shown" (1.10).
- **No LT10 result can satisfy the programme's economic check** (1.10): every maker route is gross and without fills; every
  taker cell is a cost rule expected "not shown". A Supported LT10 primary is an exploratory prospective finding, never an edge.

## 1. Common rules

### 1.0 Lessons carried over (binding from the first draft)

LT4's lessons **L1-L15** (`LIVE_TESTS_4.md` 1.0), LT7's table of later rulings (`LIVE_TESTS_7.md` 1.0), LT8's 1.0 list and LT9's
1.0 list apply unchanged where they are not capture-specific: exact `%.17g` writes and round-trip reads; NaN refusals in a
pinned spec; sealed census inputs re-hashed (refuse on mismatch); origins built **from the seal**, never from a local scan; a
pessimistic planning-MDE gate in every census with `max(declared, design)` and `sqrt(max(1, VIF_w))`; a simulated size check at
>= 2,000 worlds with the limit 0.05 + 1.645 sqrt(0.0475 / worlds) = 0.058; dry-run guards; spec and code pins on every frozen
line; write-once frozen and outcome files; clustering by event, event x UTC day and UTC day with p the largest; Holm over k
counted once; economics never changes a verdict; an internal run lock; residual-variation identification gates; the block
(circular-shift) Freedman-Lane gate for serially dependent units; the liquidity correlation gate; seal completeness; memory
planned from a measurement with a ladder; `T_X` keyed conditions; the pinned sports and crypto classifiers; the design-text
freeze; a field-projecting lag loader for every later-poll census read; vendoring, not import; LT7's one-rule F; `r_gate =
max(r_w, r_pool)`; count gates on gross projected counts with the effective share inside the MDE only (LT9 7); zero-filled
correlations refused; **whether F binds is fixed per test now, by design, never by a census count** (LT9 R1 fix 1).

**Census deaths that set LT10's expectations (counts only; round 14 0.1, round 15 0, LT9 0).** Since LT4: E020 and E021
(strata), LT5 F, H, R, J, O, LT6 D, B, V, K, LT7 (all five, closed at census 10-23), the CB13, CB14, CB15 and CB18 pre-gates;
E022 alone survived; LT9's CH213 is expected to die at its own F-MDE gate. The lessons applied here: (i) the MDE gate, not the
count gate, kills, so every test states **the count at which its MDE gate passes** (section 0); (ii) a rare state empties its
stratum, so CH224's state is continuous on every unit, CH223's minority class is a per-interval event on 88% of origins, and
CH222's thin strata are widened to two-day blocks (6.1 item 6); (iii) a whole-panel population has a whole-panel design
effect: DE 51 at planning and a census `DE_gate` that can only raise it (7); (iv) **a field's semantics are declared before
any count** (1.2: `k_last`, the touch sizes, `k_vol24` and the receipt stamps, exactly as `cross_venue_live.py` stores them);
(v) **the capture clock cannot test a cross-venue idea** (round 15 0.1: a capture-clock class contrast needs >= 1,100 pairs),
so LT10 lives on the 10-minute grid of the one fine-clock panel with Polymarket on it.

Round 15's design rules (`CREATIVE_HYPOTHESES_2026-10-29.md` 0.2, with round 14's 1-11) map onto LT10 as follows:

| Rule | LT10 rule |
|---|---|
| 1. Panel-complete units | every unit is an active pair x 10-minute grid origin of the poller's stream; no sample, monitor or external frame unit |
| 2. Dense states | CH224's innovation is defined on every unit; CH223's withdrawal is a per-interval event on every quiet untraded origin; CH222's traded flag on every Kalshi-move origin |
| 3. Innovations and crossings, never levels | all three states are changes over `(s0, t]`; the levels (`sK(s0)`, `sP(s0)`, the ratio, E009's `lvl`) are controls |
| 4. Look-backs <= 12 slots | the longest look-back is 64 minutes (E009's 60-minute feature and `rv60`) |
| 5. Field semantics declared first | 1.2; the purity rule for "untraded" and "quote-only" (`k_last` and `k_vol24`) is declared before any count (6.1 item 3) |
| 6. A stream only where it covers its population | the poller's stream covers every pair it lists by construction; PredictIt and Smarkets twins are not used (5.1) |
| 7. DE and the kill line | DE 51 (uncapped; round 15 rule 13) with a census `DE_gate = max(51, design)` (7); each kill line is the count at which the MDE gate passes (0) |
| 8. Floors | 1.0c for CH224's spread target; 0.5c for CH223's magnitude and CH222's 20-minute mid target (rule 14); the F-MDE cap equals the floor |
| 9. Census on a fresh seal | a seal of the stream's worn days `[2026-10-21, 2026-10-31)`, written after E010's analysis commit (7) |
| 10. Pin early, name what was seen | the E009 pilot quantiles, the 10-20 pair count and the readiness projections are disclosed (10); E009's and E010's results will be seen before the pin (`informed`) |
| 11. Maker-side money routes | every primary route is maker-side, gross, no fills; taker cells reported (1.10) |
| 12. Fine-clock units | pair x 10-minute origin; the state reads Kalshi lines in `(s0, t]`; the target is Polymarket's mid or spread from poll t to the poll at t + 20 min (E009's +-120 s tolerance), `unavailable` otherwise, never filled (1.3) |
| 13. Fine-clock dependence | clusters are Polymarket events; planning `DE_gate` 51; S19 (lag through the level) binding for all three; `VIF_w` 1.5 for book states (1.8) |
| 14. The fine-clock floor | 0.5c on a 20-minute mid target, 1.0c on a spread target; taker routes reported, never a verdict (1.9, 1.10) |

### 1.1 Registration, window, single analysis
- **`REGISTERED_UTC`** is the first 00:00Z that is **(a)** at least 24 h after the LT10 registration commit (spec pin plus
  ledger entry), **(b)** at least 24 h after **E010's analysis commit** (and so after E009's), **(c)** at least five days after
  the start of the continued quote stream under D-LT10-1 (the burn-in of 8.2), and **(d)** never earlier than
  **2026-11-10T00:00Z**. Proposed value **2026-11-10T00:00Z**; `END_UTC = REGISTERED_UTC + 21 d` = 2026-12-01T00:00Z; analysis
  date `END_UTC + 36 h` = 2026-12-02T12:00Z. The family slides later if any of (a)-(c) slides; a move is recorded in the ledger.
  **Staleness stop:** if `REGISTERED_UTC` would fall after 2026-11-30T00:00Z, LT10 is not registered (recorded; nothing
  counted): the census span ends 2026-10-31 and the pair list turns over daily, so a census older than a month does not
  describe the window's population.
- **Why this is the earliest window.** (1) The stream is sealed to every non-E009/E010 reader until E010's analysis commit (round
  15 0.1; the ledger's E009/E010 stopping rules; `xvenue` embargo to 2026-11-04), so no LT10 census can run before about
  2026-11-03T09:00Z. (2) After it: the sidecar restore and seal (hours), three small censuses (hours; < 300 MB), the census
  values into the spec, the size check (planning 6-12 h single-core), a reader dry run on the continued stream, the embargo
  verification and the pin, and the 24 h rule: five to six days at a normal pace under the memory-heavy-jobs rule (E011's
  analysis after 2026-11-11 and LT2's after 2026-11-13 are the nearby heavy jobs). (3) The continued stream (D-LT10-1) needs a
  counts-only burn-in of five days before its lines can count, so that a defective successor is caught before the window. (4)
  The round's own floor is 2026-11-10T00:00Z. A faster lane (a start on 2026-11-06 or 11-07) was considered and declined: it
  would compress the size check and the burn-in into two days for a gain of three or four days.
- **Why not a later lane.** LT10 shares no stream with LT8 or LT9 (captures, sweeps, the reward feed); the host's reader slots
  are not contended (LT10's reader is a light 5-minute cron, < 200 MB); and delaying lets the pair list drift away from the
  census span. The window overlaps E022 (to 2026-11-16), E026 (to 2026-12-07), and the analyses of E011, LT2 and E015 in time
  only (different hypotheses, different streams, no pooling; 1.11).
- **Boundary.** A unit's oldest input is the poll E009's 60-minute lookup uses (in `[t - 3,840 s, t - 3,600 s]`); `rv60` reads
  `[t - 3,600 s, t]`. The first origin is therefore the first 10-minute grid point with `t - 3,840 s >= REGISTERED_UTC`
  (proposed 2026-11-10T01:10Z); earlier origins give no unit and are counted `lt10_boundary`. The last origin is the last grid
  point before `END_UTC`; its targets (+20 min; CH222's M1 +60 min) and twins (to +40 min) fall after `END_UTC` and are read.
- **Design-text freeze.** After the challenger's acceptance (R1 and any re-check), a commit records the sha256 of this file in
  the ledger. From then on, the text of a test changes only by census-fixed values named in section 7 and by code-freeze-check
  fixes that change no state, unit, target, estimator, gate, threshold or verdict rule. **The freeze must exist before
  2026-11-03T02:00:00Z and before `T_E009`.** `T_X` = the earlier of X's analysis job start (queue or shell log) and X's
  analysis commit. **If the freeze is not before `T_E009`, LT10 is not registered** (recorded; nothing counted): the freeze is
  the proof that the three states were chosen without E009's result, and a design frozen after it would be a design chosen
  with the result in view. A later family could re-propose the ideas under a new LT number with that disclosure. Adjacent
  analyses:

  | Test | Adjacent analysis (`T_X`) | Why adjacent | Consequence |
  |---|---|---|---|
  | all three | **E009** (`T_E009`, not before 2026-11-03T02:00Z) | E009 tests the pooled Kalshi 10-minute lead on the same stream; CH222 splits it by cause, CH223 conditions on its absence, CH224 reads the same books' spreads | freeze not before `T_E009`: **LT10 not registered**; freeze before it: label *informed (E009)* regardless (the result is known at the pin) |
  | all three | **E010** (`T_E010`, not before 2026-11-03T08:00Z) | the same stream and features at 1 h and 6 h; CH222's M1 is E010's 1 h horizon | the census and the seal wait for E010's analysis commit (else the census waits); label *informed (E010)* |
  | CH224, CH223 | engine `se4_lr_xvenue`, `se13_lgbm_xvenue` (hidden to 2026-11-04) | Kalshi spread level and Kalshi-minus-Gamma gap at the capture clock | no LT10 text changes after 2026-11-04 except census values and code-check fixes; any other change carries *informed (se4/se13)* |
  | CH223 | E022 (`T_E022`, proposed 2026-11-17T12Z) | E022 reads Polymarket sweep depth on movers (CH133's object is in E022's lineage) | none: different stream and venue; disclosed (1.11) |

- **Fixed end, no extension** (LT4-LT9 practice). Shortfalls (stream outages, cap stops) are labelled (*underpowered*,
  Unavailable), never extended.
- **One analysis**, once, on or after the analysis date (`run_live_tests10.py analyze` refuses before it; `--out` refuses to
  overwrite). No interim look at any outcome (1.6). **Effective start** = max(`REGISTERED_UTC`, the first poll cycle processed by
  the reader at the pinned commit); the analysis keeps only lines whose `spec_sha` and `code_sha` equal the pins and whose role
  is `prospective_confirmation`.
- **Time of year (disclosed).** The window (2026-11-10..12-01) is on winter time on both sides of the Atlantic; the census span
  (10-21..10-31) is on US summer time (UK changed on 10-25), so the UTC hour of US trading activity moves by one hour between
  census and window. The hour dummies are estimated in the window; the census uses hours only for the venue-clock gates (<= 50%
  of a state's events in one UTC hour), which a one-hour shift does not change. US Thanksgiving (2026-11-26) and the following
  day are in the window: a sensitivity without origins in `[2026-11-26T00:00Z, 2026-11-28T00:00Z)` is reported and never
  changes a verdict (*holiday-sensitive* label).

### 1.2 Streams read (all already written by existing collectors; nothing new is fetched by LT10's reader)
- **The fine-clock quote stream** (`cross_venue_live.py`, `Poller.cycle`; `CROSS_VENUE_LIVE.md`): every 120 s on the UTC grid,
  one JSON line per active or retired pair in `quotes/YYYYMMDD.jsonl` (gzipped after 2 days), with `t` (the scheduled poll time,
  integer seconds), `pid` (`<kalshi ticker>|<Gamma market id>`), Kalshi `k_bid`, `k_ask` (`yes_bid_dollars`, `yes_ask_dollars`),
  **`k_last`** (`last_price_dollars`), **`k_bid_sz`, `k_ask_sz`** (`yes_bid_size_fp`, `yes_ask_size_fp`: the touch sizes),
  `k_status`, **`k_vol24`** (`volume_24h_fp`, a rolling 24 h volume), **`k_recv`** (receipt of the Kalshi request batch), Polymarket
  CLOB `p_bid`, `p_ask`, `p_bid_sz`, `p_ask_sz` (the executable touch and its sizes), `p_last`, `p_book_ts` (the book's own
  timestamp), `p_tick`, `p_min_size`, **`p_recv`**, and the derived `k_mid`, `p_mid` (E009's `two_sided_mid`: 0 < bid < ask < 1
  and spread <= 10c, else NaN). A failed request leaves that venue's fields NaN or absent for the cycle (NaN, never filled).
  **E009-era files** (`data-dumps/research_lab/cross_venue_live/quotes/`) are read by the census only (sealed days, 7); **window
  files** are read from the continued stream's directory fixed by D-LT10-1 (8.2: recommended `xv_quotes/quotes/`, the same
  schema plus a trailing writer key `src`).
- **Pair records** `pairs/pairs_<YYYYMMDDTHHMMSSZ>.json` (the daily refresh; one file per refresh, never overwritten): per pair
  `pid`, `k_ticker`, `p_market_id`, **`p_event_id`** (the cluster), `k_event`, `token0`, `k_close`, `p_end`, `k_vol24`, `p_vol24`,
  `fee_rate`, `fee_src`, `hand_verified`. The record **in force at t** is the latest refresh file whose `refreshed_utc` is earlier
  than t; a pair absent from it is retired at t (excluded, counted `retired`), even while the poller still polls it (6 h 20 min).
- **Capture sidecar** `snapshots/<id>/rows_ext.csv.gz` (`ext_sidecar.py`; keys `market_id`, `condition_id`): `fee_type`,
  `fee_category`, `series_slugs`, read once per UTC day from **the last complete capture whose start is before the day's 00:00Z**,
  for the category rule (1.4) and the `condition_id` join (economics only). No price column of the sidecar or of the capture is
  read.
- **CLOB reward feed** `reward_params/<capture_id>/` (economics only, 1.10): the last usable feed capture before the UTC day,
  joined by `condition_id`; counts and gross rates only.
- **Not read, ever:** `predictions.jsonl`, `outcomes.jsonl`, `predictions_e010.jsonl`, `outcomes_e010.jsonl`, any E009/E010
  analysis output, the `/home/opc/arepo_val/` validation copy, the gap-fill merged root, `cross_venue/` (historical study),
  trade samples, sweeps, the live trade monitor, `surprise_live/`, the stores `live_tests2/` .. `live_tests9/`, CB8-H holders,
  the CB16-CB18, E025 and E026 stores, the keyless streams (PredictIt, Smarkets, ESPN, `gamma_rules`), and the signal engine's
  `quotes/`, `features/`, `aux/` and `predictions/`. A path allow-list in the reader and the census refuses any other path
  (unit test, 8.3).

### 1.3 Clocks, windows and decision times
- **Origins:** the 10-minute grid (`t % 600 == 0`, E009's `OUTCOME_GRID_S`); 144 a pair-day. Consecutive origins' 20-minute
  targets overlap by 10 minutes (an MA(1) target by construction; 1.7, 1.8).
- **The state window.** `s0(t)` = the poll E009's lookup uses for its 10-minute lag: the latest poll in `[t - 840 s, t - 600 s]`
  with valid two-sided mids on both venues (E009's `lookup(hist, t, 600)`). The window is `W(t) = (s0, t]`; "in the window"
  means over the consecutive Kalshi-valid polls from `s0` to `t` inclusive. A window with fewer than 4 Kalshi-valid polls
  (endpoints included) gives no unit (`window_gap`, counted). `dk1 = mK(t) - mK(s0)` is E009's own feature.
- **Decision time** = `max(k_recv(t), p_recv(t))`, the receipt of the latest line used (poll t's Kalshi batch, then its CLOB
  batch). E009's late rule applies: if either receipt is more than 60 s after `t`, no unit (`late_origin`, counted). States,
  controls and eligibility read poll t and earlier polls only.
- **Targets** start at poll t's Polymarket mid and spread and end at **the poll at exactly t + 1,200 s, else the nearest within
  +-120 s** whose `p_recv` is at most 60 s after its own `t` (E009's `OUTCOME_TOL_S` and `MAX_RECV_LAG_S`); CH222's M1 at t + 3,600
  s by the same rule. Status per unit and horizon, write-once: `two_sided`, `one_sided`, `absent`, `late`, `poll_missing`; only
  `two_sided` has a target. The tolerance can never place a target endpoint before the poll scheduled at t + 1,080 s.
- **Far-future twin windows** `(t + 1,800 s, t + 2,400 s]`: Kalshi fields only, from the polls at t + 1,800 s and t + 2,400 s
  (each +-120 s, Kalshi-valid) and the polls between them, read through the Kalshi-only lag loader (1.6, 7).
- **Late rule (the freeze).** A unit's frozen line must be written (fsync'd, write time recorded) **before t + 1,080 s**, the
  earliest instant a target endpoint poll can be scheduled; else the unit is `.late` (lost, counted); *late-loss* above 2% of a
  test's origins is a label. The reader runs every 5 minutes (8.2), so a normal unit is frozen 1-6 minutes after its origin.

### 1.4 Shared origin-side eligibility
Applied in order and counted, at origin t:
1. **Pair active:** the pair is in the record in force at t (1.2), not retired; its `p_event_id` is the unit's event.
2. **Category (spec parameter `scope`; default `non_sports_ex_crypto`):** sports by the pinned sidecar rule
   (`cb17_census.is_sports_sidecar(fee_type, fee_category, series_slugs)`), crypto by the pinned classifier (`fee_category`
   contains `crypto` after strip and casefold), both on the day's sidecar row of the pair's `p_market_id`. A pair without a
   sidecar row that day is `category_unknown`, excluded from every primary and counted (treated as sports and crypto for the
   default scope). The sports arm and the crypto arm are reported, uncounted. Each census runs once and
   computes every gate under both scopes (`non_sports_ex_crypto` and `ex_crypto`) in the same run; the default decides unless the
   owner puts sports in scope before the pin, in which case the same run's `ex_crypto` values decide (declared now; the gates and
   thresholds do not change); after the pin the scope never changes.
3. **Poll t valid:** both venues two-sided by E009's rule, both mids in E009's `MID_RANGE` [0.03, 0.97], `k_status` in {`active`,
   `open`}, both receipts within 60 s of t.
4. **E009's seven features complete** at t (`r1, r6, lvl, lvl2, gap, dk1, dk6`, E009's `features`, vendored).
5. **Window complete** (1.3): `s0` exists and the window holds >= 4 Kalshi-valid polls.
6. **Volatility inputs:** `rv60_P` and `rv60_K` (the square root of the sum of squared consecutive 120 s mid changes over the
   valid polls in `[t - 3,600 s, t]`) each from >= 20 valid polls, else `rv_short` (excluded, counted).
7. **Ends:** the pair record's `p_end` and `k_close` are unknown or later than t + 2 h (so no target or twin crosses a
   resolution); unknown is counted.
8. **Event concentration (census-fixed):** if the census's top Polymarket event holds > 40% of the primary-eligible origins,
   it is excluded from every primary (`exclude_event`, spec key) and reported as an arm; the census gates are recomputed without
   it (7).
9. **Spread censoring (disclosed):** E009's two-sided rule treats a spread above 10c as no quote, so an origin whose Kalshi or
   Polymarket spread passed 10c at t or s0 is not a unit (counted `spread_censored`). This truncates the largest widenings out of
   CH223's and CH224's populations; the census prints the share.
Each test then applies its own population filter (sections 2-4).

### 1.5 Missing data and per-origin status (never imputed)
Every pair x grid origin of the window receives exactly one origin status, write-once (`unit`, `lt10_boundary`, `retired`,
`category_unknown`, `poll_missing`, `one_sided_k`, `one_sided_p`, `out_of_range`, `late_origin`, `features_incomplete`,
`window_gap`, `rv_short`, `end_soon`, `spread_censored`, `excluded_event`, and the test filters' own codes), and every unit
one target status per horizon (1.3). Only `two_sided` has a target. The attrition rule (|a_1 - a_0| > 2 pp between the
contrasted classes, or between the top and bottom terciles of CH224's state, gives *attrition-differential* and Lee-type bounds)
never changes a verdict. A missing control or state is NaN (excluded, counted), never 0. **Declared indicator-pair exceptions
only:** `k_vol24` missing at either end of a window step enters CH222's and CH223's purity rules as "unknown" with the flag
`vol_unknown` = 1 (6.1 item 3), and `log1p k_vol24` enters as 0 with the same flag; every primary is also re-estimated on units
with the field present (reported). A missing F state leaves the unit in the primary and out of the F arm (counted). Stream
outages (poller down, request failures) stay missing; no other venue, poller or validation copy fills them.

### 1.6 What is not looked at before the analysis date
- No mid, spread, move, target, P&L, regression or plot from `live_tests10/` files, or from in-window quote lines, for these
  hypotheses. Only `run_live_tests10.py ops-stats` may run (file, line, unit, class and status counts, and the successor
  poller's request and receipt-lag counts; reads no price, spread or size column, enforced by a unit test).
- No change of thresholds, scales, populations, estimators or k after registration; operational fixes are logged as
  deviations.
- **E009 and E010.** No LT10 designer, coder or reviewer opens any E009/E010 prediction, outcome, `--ops-stats` output beyond
  what the ledger already quotes, analysis output or interim statistic **before the design-text freeze**. After their analysis
  commits, their verdict lines in the ledger are public and LT10 carries *informed (E009, E010)*; the census and the reader still
  never open `predictions*.jsonl`, `outcomes*.jsonl` or any analysis output (the path allow-list, 1.2).
- **Census-span data.** No LT10 designer, coder or reviewer opens any quote, pair or sidecar file of the census span (its
  look-back and its lag polls included, 7) before the seal commit, except the restore's byte and sha256 checks. Development
  and tests use synthetic data only (no real quote file before the seal; the field list comes from the code, 1.2).
- **Census origin-side rule.** The census computes, for each origin, only quantities from poll t and earlier polls, plus the
  Kalshi-only twin states through the lag loader; it forms no difference between a Polymarket field at an origin and any later
  Polymarket poll, and it reads no Polymarket field of a poll later than the last origin of its span (enforced by structure and
  by a unit test that alters every Polymarket field after each origin and shows that origin's census contributions unchanged,
  8.3).
- **Engine.** No LT10 designer, coder or reviewer reads the scores of `se4_lr_xvenue` or `se13_lgbm_xvenue` (visible from
  2026-11-04) before the pin; a text change after 2026-11-04 other than census values and code-check fixes carries *informed
  (se4/se13)*.

### 1.7 Estimators and inference
- **Sign convention.** All three hypotheses are "> 0" as written (`dir = +1`); every MDE is a magnitude.
- **Expanding-past demeaning** (LT2-LT9): every regressor minus the mean of the pair's strictly earlier units of the same test;
  target raw; the first unit of each pair drops. Pairs re-listed after retirement keep their history (same `pid`).
- **Standard errors and p (L10):** CR1 on Polymarket event (`p_event_id` of the record in force), two-way event x UTC day of the
  origin, and UTC day. One-sided **p = max(p_event on t with `G_event - 1` df, p_two-way normal, p_day on t with `G_day - 1`
  df)**. **Sparse class (CH223, CH222):** the event t uses `min(G_event, G_minor) - 1` df, `G_minor` = the number of events
  holding at least one unit of the smaller contrasted class. The conservative 95% CI is the hull of a 2,000-draw event
  bootstrap and the three Wald intervals.
- **Overlapping targets and shared shocks.** Adjacent origins of a pair share 10 minutes of target (MA(1)); pairs of one event
  share news at the same poll; Kalshi's state at origin t + 20 min can include the trade or quote reaction to the same news that
  moved Polymarket over (t, t + 20 min]. The event cluster carries the first two; the F twin (placed after the target's end)
  and the block gate (1.8) carry the persistence.
- **Dependence sensitivities (reported, never the verdict):** event x two-day block CR1; the pair as the cluster; the
  pair-deduplicated estimate (the first unit of each pair x UTC hour only, a deterministic rule); non-overlapping origins only
  (`t % 1,200 == 0`, E009's primary grid).
- **Both-demeaned sensitivity** (LT6): each primary re-estimated with the target also expanding-past demeaned; reported only.

### 1.8 Gates (valid within-unit nulls) and their size
- **Block (circular-shift) Freedman-Lane gate** (LT5's `block_fl_gate`, vendored unchanged): after expanding-past demeaning,
  within each stratum the reduced-model residual series (ordered by origin) is circularly shifted by an offset drawn from
  `[s, n - s]`, `s = max(4, ceil(n / 4))`, and the full model refitted; 200 draws; passes if `p_perm < 0.05`; strata with fewer
  than 16 rows are excluded from the gate (counted). **Strata:** pair x UTC day for CH224 and CH223 (144 origins by
  construction, round 15 rule 12); **pair x two-day block** (`block2 = floor((t - block_anchor) / 172,800 s)`, `block_anchor =
  REGISTERED_UTC`) for CH222, whose units are the 10-12% of origins with a Kalshi move (6.1 item 6). The circular shift keeps
  the residuals' serial dependence (overlapping targets, volatility clustering), which a plain within-stratum permutation would
  break.
- A failed gate on data gives p = 1 in Holm and the label "SE check failed (gate on data)".
- **Size check (L5), after the censuses (k and the census-fixed values fixed first).** `size-check` runs once, on the code to
  be pinned, 2,000 worlds x 200 draws, seed **20261397**, limit 0.058, every gate scenario through the same `block_fl_gate` path,
  strata and minimum (16) as the analysis; a world is generated once and evaluated under each binding test. Scenarios (no
  effect of the tested term in every world):

  | # | Scenario (1.8.1) | Gate | Binding for | Statistic |
  |---|---|---|---|---|
  | 1 | **W1 null:** common efficient price, simultaneous venue updates, overlapping targets, event jumps | block FL | CH224, CH223, CH222 | gate rejection rate |
  | 2 | **W2 common volatility:** W1 with an event-level AR(0.9) log-volatility scaling both venues, trades and size changes | block FL | CH224, CH223, CH222 | gate |
  | 3 | **W3 = S19:** Polymarket's mid follows Kalshi's level with a two-poll lag; trades and quote revisions carry no information beyond the level | block FL | CH224, CH223, CH222 | gate |
  | 4 | **W4 = S20:** W3 with Kalshi's `last_price` refreshed on a venue cadence unrelated to moves | block FL | CH222 | gate |
  | 5 | **W5 activity leak:** W3 with a latent activity that raises both the trade probability and the speed of Polymarket's catch-up; the model sees noisy `rv60` proxies only | block FL | CH222 | gate |
  | 6 | **W6 = S21:** W1 with Kalshi touch sizes re-posted by a bot on a fixed cadence with no information | block FL | CH223 | gate |
  | 7 | **W7 volatility leak:** W2 with the withdrawal probability rising with the latent event volatility; the model sees `rv60_P`, `rv60_K` only | block FL | CH223 | gate |
  | 8 | **W8 = S22:** Polymarket's spread mean-reverts on its own with a one-tick floor; Kalshi's spread is a reflected random walk; independent | block FL | CH224 | gate |
  | 9 | **W9 M-Q (CH224):** a slow common spread drift that the lead and the twin innovations proxy equally | none | CH224 | verdict size |

  **Verdict size** (9) = the share of worlds in which the test's analytic one-sided p (1.7) is < 0.05 **and** its F (1.9) holds;
  the gate is omitted, which can only raise the rate. Criterion: <= 0.058.
- **Also reported, never binding:** a planted-effect power run per test (500 worlds each: CH224 1.0c per 2.2 SD of `zdsK`;
  CH223 0.5c between classes; CH222 0.5c between classes; seeds `20261397 x 100 + 41, 42, 43`); W1-W3 rates for each test's F
  arm; the CH223 and CH222 far-future label rates.
- **Leak worlds (5, 7).** The confounder reaches the model only through an imperfect control, so the tested term carries a
  real but mechanical partial effect. They are binding: a rejection rate above 0.058 means the design cannot separate the
  hypothesis from the confounder at the declared controls, and the test is "SE check failed (size scenario)". This is the
  intended consequence, declared now; their parameters are conventions (1.8.1), not measurements, and are not tuned after any
  result. **Expected:** world 7 is likely to fail at its parameters (a withdrawal that marks volatile minutes predicts |moves|
  through volatility clustering, and two 60-minute realised-volatility controls absorb it only partly); world 5 may fail.
- **Consequence of a failure (declared now, as LT5-LT9):** a failing scenario makes **only the tests it is binding for** "SE
  check failed (size scenario)" (1-8) or "SE check failed (mechanical world)" (9): p = 1 in Holm, **k unchanged**, no rerun,
  reseed, redesign or variant. `max_retries 1` covers a deterministic crash only. No preliminary run of any scenario at seed
  20261397 is made.

### 1.8.1 Simulated worlds (declared now; no census input except the census-fixed strata rules)
Common unless stated: **30 events, 60 pairs** (12 events of one pair, 9 of two, 6 of three, 3 of four); **7 UTC days**; polls every
120 s (720 a pair-day), origins every 600 s (144 a pair-day); every unit passes the eligibility of 1.4 unless a world says
otherwise; 200 draws per world at a fresh sub-seed from one generator seeded 20261397, scenarios in table order; non-binding
runs on generators derived as `20261397 x 100 + n`. Prices in cents on a 1c tick (10% of pairs on a 0.1c Polymarket tick).
Every world fits each binding test's primary model of sections 2-4 with every declared control computed from the simulated
polls exactly as the reader computes it (windows, `s0`, `rv60`, E009's features).
- **W1 (null):** a latent efficient price per pair `x_p` (random walk, per-poll innovation SD 0.15c, plus event jumps: per poll
  per event probability 0.002, size `N(0, (2c)^2)`, hitting every pair of the event); each venue's mid = `x` plus a venue
  AR(0.5) noise of SD 0.3c, rounded to the venue tick, **updated simultaneously on both venues (no lead)**; each venue's spread a
  reflected AR(1) on ticks (rho 0.9, mean 2 ticks, floor 1 tick); touch sizes log-normal AR(0.9) (SD 0.5); Kalshi trades
  Bernoulli(0.05) a poll, a trade setting `k_last` to the touch on a random side and adding `|N(0, 1)| x 100` to `k_vol24`;
  `k_vol24` decays by 1/720 of its value a poll (the rolling window).
- **W2 (common volatility):** W1 with an event log-volatility `v_e` AR(1) per poll (rho 0.9 per 10 minutes, stationary SD 0.5)
  multiplying both venues' innovation SDs, the trade probability (logit +0.5 per SD) and the size-change SD.
- **W3 (S19):** W1 with **Kalshi's mid = `x_t` and Polymarket's mid = `x_{t-2}`** (two polls, 240 s), so Polymarket follows
  Kalshi's level; Polymarket's book re-centres with one side lagging one poll (its displayed spread widens by `|Δx| / 2` for one
  poll after each move); trades and quote revisions on Kalshi independent of the lagged component's size.
- **W4 (S20):** W3 with `k_last` additionally reset to the current Kalshi mid at every 15th poll and at the first poll of 30% of
  UTC hours (a venue cron), independent of moves.
- **W5 (activity leak):** W3 with a pair activity `a_p` (AR(1), rho 0.95 per 10 minutes, SD 1) that raises the trade probability
  (logit +1.0 per SD) and sets Polymarket's lag to **one poll when `a_p > 0` and three polls otherwise**; the model sees `rv60_P`
  and `rv60_K` (which `a_p` does not enter) and its declared `|dk1| x` volatility interactions only.
- **W6 (S21):** W1 with Kalshi's touch sizes reset by a bot every 5 polls on a fixed phase per pair (the size falls to 30% at the
  reset and refills over two polls), independent of every price.
- **W7 (volatility leak):** W2 with the probability that a quiet untraded window contains a withdrawal (a spread widening of two
  ticks or a size fall to 40% at an unchanged touch) equal to `logistic(-3.4 + 0.8 z(v_e))`; the model sees `rv60_P` and `rv60_K`
  from the simulated polls.
- **W8 (S22):** W1 with Polymarket's spread an AR(1) on ticks with rho 0.7 per 10 minutes, floor one tick, and Kalshi's spread a
  reflected random walk on ticks in [1, 10] ticks with a step probability of 0.1 a poll; independent of each other and of mids.
- **W9 (M-Q, CH224):** W1 plus a common slow spread drift `d_t` (AR(1), rho 0.999 a poll, stationary SD 0.5 tick) added to both
  venues' spreads before rounding; the lead `zdsK` and the twin both carry the drift's increments; statistic: analytic p < 0.05
  and F holds.

### 1.9 Verdicts, the falsification condition and labels (per primary, after Holm over k)
- **F rule (LT7's, unchanged).** The **arm model** is the primary model with the far-future twin added, fitted on the units that
  have it, same demeaning, controls and clustering. `Δ = beta(lead) - beta(twin)`. **F holds iff (i) Δ's one-sided p < 0.05
  under the 1.7 rule (not Holm-adjusted; counted 0) and (ii) Δ̂ >= 0.5 x betâ_primary.** An arm with fewer than 50% of the
  primary's units is *falsification unavailable*. **Whether F binds is fixed now, by design:** **CH224's F binds** (its census
  F-MDE gate <= 1.0c, 7); **CH223's and CH222's F are reported labels** (*far-future not excluded*), never verdict conditions.
  Reasons: CH224's innovation is a difference of a persistent level (Kalshi's spread), so a slow drift of both spreads can
  make it predict mechanically (world 9); CH223's and CH222's states are per-interval events whose planning F-MDEs (0.75c,
  0.93c at the low end) exceed their 0.5c caps at both or one planning end, and their mechanical channels (volatility and
  activity clustering) are carried instead by binding leak worlds 7 and 5, as LT9's CH212 (6.1 item 7). Twins: CH224 `zdsK'`,
  Kalshi's spread change from the poll at t + 1,800 s to the poll at t + 2,400 s, on the same census scale; CH223 `pull'`, the
  withdrawal flag over `(t + 1,800 s, t + 2,400 s]` (spread widening >= 2c or a size fall >= 50% at an unchanged touch, no
  mid or trade condition); CH222 `traded'`, 1[`k_last` changed over `(t + 1,800 s, t + 2,400 s]`].
- **Disclosed: F conflates a reverse-direction lead with drift.** If Polymarket's spread changes lead Kalshi's, CH224's twin
  picks it up and F fails; the label then reads *mechanical or reverse lead not excluded*. Conservative by construction.
- **Supported (exploratory, prospective):** Holm-adjusted one-sided p < 0.05, estimate in the predicted direction, gate passed,
  **and F holds (CH224).** If everything else holds and CH224's F fails or is unavailable: **Inconclusive** with the label
  *mechanical null not excluded* (or *falsification unavailable*); Holm p is not changed.
- **Contradicted:** the conservative 95% CI lies entirely on the other side of 0. **Inconclusive:** otherwise.
  **Unavailable:** fewer than 30 events with units, or fewer than 10 UTC days with units; CH224 also fewer than 30,000 units;
  CH223 fewer than 1,500 withdrawal units or 30,000 no-withdrawal units; CH222 fewer than 2,000 traded or 2,000 quote-only units.
- **Labels (never change a verdict):** *material* (CH224: the sign-adjusted slope x 2.2 census SDs of `zdsK` >= 1.0c; CH223 and
  CH222: the class contrast >= 0.5c); *informed (E009, E010)* (always); *informed (se4/se13)* (1.6); *far-future not excluded*
  (CH223, CH222: the F rule fails or is unavailable); *floor-driven* (CH224: the refit on units with Polymarket's spread at t of
  >= 2 ticks has the opposite sign or p >= 0.05 while the primary is Supported); *reward-band-sensitive* (CH224: the refit on
  pairs not listed in the reward feed changes sign); *mismatch-sensitive* (the refit on hand-verified pairs only changes sign);
  *event-concentrated* (one event holds > 50% of units); *quote-only dominated* (CH222: Supported but the traded-class mean of `c`
  is below the quote-only class's in the raw, uncontrolled means); *bot-cadence* (CH223: Supported but the refit without the
  most common minute-of-hour of each pair's withdrawals (the modal `t mod 3,600` value, one of six on the 10-minute grid) changes sign); *analytic p
  oversized in simulation*; *underpowered* (Inconclusive and `(t_{G-1, 1-0.05/k} + t_{G-1, 0.8}) x SE_day` above the census MDE);
  *attrition-differential*; *late-loss*; *stream-gap* (the stream missed > 10% of the window's 120 s cycles); *holiday-sensitive*
  (1.1).
- **MDE multiplier.** `3.47 = t_{20, 1 - 0.05/6} + t_{20, 0.8}` (LT7-LT9's constant); for k <= 3 the exact value is below it; **not
  lowered** (conservative; one constant across LT7-LT10).

### 1.10 Economics (separate; never changes a verdict)
- **Taker (reported only).** E009's frozen executable rule (spec `cross_venue_live_v1.json`, sha256 `e63f20cc...6e2b`;
  `trade = |M1_20| > ask - bid + taker fees`, direction `sign(M1_20)`, entry at Polymarket's touch at t, exit at the touch at t + 20 min,
  `economics.taker_fee` on both legs at the pair record's `fee_rate`), computed by LT10's analysis from the frozen coefficients and
  the unit's own features (not from E009's prediction files) on: CH222's traded moves, its quote-only moves, and all its moves.
  LT3's `econ` (event-clustered mean, one-sided p, >= 30 trades in >= 10 events). No depth, queue or latency: optimistic.
- **Maker (gross, no fills, reported only).** CH224: after a Kalshi tightening of >= 1 tick, a one-tick-improved Polymarket quote
  on each side for 20 minutes, marked against Polymarket's mid at t + 20 min (the adverse-selection proxy per share). CH223: the
  class difference in `|mP(t + 20) - mP(t)|` times the touch size at t (the adverse selection a maker who steps aside avoids, per
  quote). CH222: the class difference in `c` (what a maker re-centring only on traded moves would gain against one re-centring on
  every move). On the rewarded subset (pairs whose `condition_id` the day's feed lists), the gross reward rate per 20 minutes as
  `MAKER_REWARDS_STUDY.md` quotes the scoring rule (an upper bound; no reward is computed as earned).
- **Hurdles (`cost-model-v1`, `COST_MODEL.md`, as round 15 fact 4 and round 14 fact 9 quote it):** $100 taker round trip about
  2.9c at >= $100k liquidity, 3.9c at $10k-100k, 7.2c at $1k-10k; a 5-share touch round trip about 4.5c; a passive touch order
  fills about 1.7-3.1% of the time within an hour; makers about break-even before rewards.
- **Declared in advance:** every AREPO taker cost check has failed (E004, E007; 0 of 95 economic cells positive), and the E009
  pilot's trade rule fired 0 times (median Polymarket spread 1c). "Not shown" is the expected outcome for every taker cell. No
  resolution, hold-to-resolution or realised reward income is computed.
- **No LT10 result can satisfy the programme's economic check.** The programme requires prospective confirmation **and** an
  economic check before any edge claim (CLAUDE.md). LT10's maker readings are gross, without fills, queue or realised rewards,
  and its taker cells are cost rules expected "not shown"; none of them is an economic check in that sense, whatever the
  verdicts. A Supported LT10 primary can at most nominate a later, separately registered economic test.

### 1.11 Overlaps, dependence, embargo shadows and counting
- **Within LT10:** CH222's units (Kalshi moved, `|dk1| >= 0.5c`) and CH223's units (Kalshi's mid did not move, `|dk1| < 0.001c`,
  and no trade signal) are **disjoint by construction**; CH224's units are all eligible origins and contain both. All three share
  pairs, events, the stream and E009's controls. One Holm family; never counted as independent confirmations. The census prints
  the pairwise unit overlaps and, on shared units, the within-pair correlations of the tested terms (CH224's `zdsK` with
  CH222's `traded` and CH223's `pull`).
- **Against registered or drafted tests (no double count; no shared window):**

  | LT10 | Closest prior | Same data? | Same contrast? | Why not a double count |
  |---|---|---|---|---|
  | all three | **E009** (frozen lead model: Kalshi's 10-minute change -> Polymarket's 20-minute mid; relative MSE gain; window 10-13..11-03) | the same stream; LT10's census reads E009-era days, its window the continued stream after E009's end | no: CH222 splits E009's `dk1` by its cause (traded or quote-only) and holds `dk1` fixed; CH223 tests origins where `dk1 = 0`; CH224 has a spread target | disjoint windows; freeze before `T_E009` or not registered; *informed (E009)*; nothing pooled; E009's frozen spec enters only as an economic rule |
  | CH222 (M1 at +60 min) | **E010** (1 h and 6 h, cleaned-set model) | the same stream | no | disjoint windows; *informed (E010)* |
  | CH224, CH223 | engine **`se4_lr_xvenue`, `se13_lgbm_xvenue`** (`xvenue`: has-pair, Kalshi-minus-Gamma mid, Kalshi spread level, quote age, at the capture clock) | the same quote lines as inputs | no: levels at the capture start against a 2 h direction label; LT10's states are 10-minute innovations and events on the fine clock | `kxbook` token and attribution limits (9); `xvenue` not extended (9) |
  | CH223 | **CH133** (Polymarket's own depth fade; idea) and **E022** (hollow liquidity on movers; window to 11-16) | no (sweeps of Polymarket's book) | no: the *other* venue's withdrawal | different stream and venue; E022's window overlaps LT10's first week in time only |
  | CH224 | **LT9 CH213 / CH214** (Polymarket's band break and depth arrival at the capture clock), CH166 (idea) | no | no | different streams; LT9's window starts 2027-01-21 |
  | all | E011, E026 (frozen modules to 12-07), LT2, E015, E025 | no | no | different streams; nothing of E026 is imported |

- **Signal-engine shadows (disclosed; section 9).** The engine's `xvenue` family reads the same quote lines at each capture's
  start; a model given two consecutive capture-time Kalshi spreads cannot form a 10-minute innovation (captures are 2 h apart),
  so the existing isolates do not shadow LT10. The round's proposed `kx_*` columns would; LT10 asks for the `kxbook` token and
  attribution limits of section 9 before any such column is built.
- **Collection overlap (disclosed):** the engine reads the same quote stream; under D-LT10-1's recommended route the engine's
  `XV_QUOTES_ROOT` needs a second read root (an engine change, section 9), and E009/E010's directory stops growing at the
  handover (its canonical evidence becomes byte-stable).
- **Counting (M3):** the analysis adds **k counted tests**, one per surviving primary, kind `live_tests10`
  (`battery2.KIND_RULES["live_tests10"]`, fail-closed). Gate draws, F, secondaries, readings, arms, economics, censuses and the
  size check count 0. The cumulative count is recorded at registration and at analysis.

### 1.12 Stop rules
As LT9 1.12: no interim look; the test runs to `END_UTC` whatever the counts; after 7 days, a test whose units run below one third
of its census projection (counts only) gets the ledger note "likely Unavailable" and nothing else changes; any change to a pinned
file after the pin makes the analysis refuse; the reader exits 75 when nothing is new; a failed reader is re-promoted within 48 h;
gaps stay missing and are counted. **Stream stops:** if the continued stream stops (cap, crash, host) the window is not extended;
a stop longer than 24 h gets a ledger note and a restart under the same code (the restart record names the first cycle after
it); a stop of the stream during the burn-in moves `REGISTERED_UTC` under 1.1 (c). Disk: the reader refuses above 1.5 GB in
`live_tests10/`; no retention rule may cover `live_tests10/`, the continued stream's directory or `cross_venue_live/` before LT10's
analysis is committed; reader kinds of a test not in `k_tests` are switched off before the reader's code freeze.

## 2. CH224: the hedged maker's price (Kalshi's spread innovation and Polymarket's next spread change)

- **Hypothesis and mechanism.** If some makers quote both venues and hedge fills on the other, Polymarket's spread on a paired
  question is bounded by Kalshi's spread plus the hedge's cost, and the binding constraint moves when Kalshi's spread moves: when
  Kalshi's spread tightens the hedge is cheaper and hedged quotes can step inside Polymarket's touch; when it widens they leave.
  The level relation (CH166, CH115) is not tested here; the **innovation** relation, which says *when* to be inside, is.
  **Direction: within pair, the slope of `dsP` on `zdsK` > 0** (Kalshi tightened, Polymarket tightens next; Kalshi widened,
  Polymarket widens next), the levels, Polymarket's own concurrent change and E009's features held fixed. Who would be wrong:
  the reward-band reading (Polymarket's spread on the pairs is set by reward farmers at `rewards_max_spread` and ignores Kalshi:
  a clean null; the *reward-band-sensitive* label), the common-shock reading (a public shock widens both venues within the same
  window: Polymarket's own concurrent change is a control; what remains is Polymarket's lag, which is the maker route either way),
  the lag-through-the-level reading (world 3: a Kalshi move eats a level and widens Kalshi's spread while Polymarket's lagging
  re-centre widens Polymarket's spread later; `|dk1|`, `traded` and E009's features are controls), the reversion reading (world
  8), and the drift reading (world 9 and the binding F).
- **Unit and population.** Every eligible pair x origin (1.4) with valid two-sided books on both venues at `s0` and at t (both
  inside 1.4's rules). No further filter. Boundary 1.1.
- **State (frozen; decision time 1.3).** `sK(u) = k_ask(u) - k_bid(u)`, `sP(u) = p_ask(u) - p_bid(u)` (price units);
  **`dsK = sK(t) - sK(s0)`**; **`zdsK = dsK / scale_K`**, `scale_K` = the census's pooled SD of `dsK` over CH224's census units
  (a constant; 6.1 item 4). Also frozen: `sK(s0)`, `sP(s0)`, `ratio = sP(s0) / sK(s0)`, `dsP_own = sP(t) - sP(s0)`,
  `floorP = 1[sP(t) <= p_tick + 1e-9]`, `floorK = 1[sK(s0) <= 0.01 + 1e-9]`, `traded` (CH222's flag: `k_last` changed in the
  window), `tightK = 1[dsK <= -0.01 + 1e-9]`, `wideK = 1[dsK >= 0.01 - 1e-9]`, the reward listing of the day (economics only).
- **Target (exact).** **`dsP = sP(t + 20 min) - sP(t)`** (1.3's endpoint rule; both polls two-sided; in cents). M1 (asymmetry,
  reported): the model with `zdsK+ = max(0, zdsK)` and `zdsK- = min(0, zdsK)` in place of `zdsK`. M2 (reported): the change in
  log Polymarket touch size (both sides summed) over the same 20 minutes (do quotes arrive, or only re-price?). S1: `dsP` at
  +10 min.
- **Primary statistic.** Expanding-past pair-demeaned OLS of `dsP` on **`zdsK`**, controls: `sK(s0)`, `ratio`, `sP(s0)`,
  `dsP_own`, `floorP`, `floorK`, `traded`, `|dk1|`, E009's seven (`r1, r6, lvl, lvl2, gap, dk1, dk6`), `rv60_P`, `rv60_K`,
  `log1p` of each venue's two touch sizes at t, `log1p k_vol24(t)` (+ `vol_unknown`), 23 UTC hour dummies. Tested coefficient:
  `zdsK`. Inference 1.7; seed **20261301**. Gate: block FL in pair x UTC day strata (size worlds 1, 2, 3, 8; verdict-size world 9),
  seed **20261391**.
- **Falsification (F; binding; census gate F-MDE <= 1.0c, section 7).** Twin `zdsK'` (1.9), read through the Kalshi-only lag
  loader; F-arm units need both twin polls Kalshi-valid. Placement: the lead window ends at the target's start; the twin starts 10
  minutes after the target's end, so it shares no poll with the target.
- **Mechanism readings.** M1, M2; the slope within units with `floorP = 0` (*floor-driven*); the slope on pairs not listed in the
  day's reward feed (*reward-band-sensitive*); the hand-verified refit (*mismatch-sensitive*).
- **Secondaries.** S1 (+10 min); S2 the sports and crypto arms; S3 the excluded-event arm; S4 the non-overlapping grid (1.7); S5
  the pair-deduplicated estimate; S6 counts by tick, by `floorP` and `floorK`, and by reward listing.
- **Planning MDE (estimate; every input declared now, sources in 10.1).** Pairs after the feature, category and validity filters
  **60 (low) / 100 (high)**; 144 origins a pair-day x valid share 0.85 x 21 days = **154,224 / 257,040** units; `n_eff` (0.8)
  **123,379 / 205,632**. SD of `dsP` 1.0c (planning, unprobed); DE 51; `VIF_w` 1.5 (book state); tercile gap 2.2 SD; **overlap
  factor `OF` 1.1** (`OF = 1 + max(0, rho_x1)`, `rho_x1` the within-pair lag-1 autocorrelation of the tested term across
  consecutive origins, planning 0.1: with adjacent targets correlated 0.5 by the 10-minute overlap, the slope's variance is
  inflated by `1 + 2 x 0.5 x rho_x1`). `MDE = 3.47 x 1.0c / sqrt(n_eff) x sqrt(51) x 1.5 x sqrt(1.5) x 2.2 x sqrt(1.1)` = **0.299c
  (low), 0.232c (high)**; a quarter of the low count 0.598c. **F-MDE (binding, planning `r` 0.1, factor `sqrt(2 / 0.9)` = 1.4907):
  0.446c / 0.345c.** Kill lines in counted units over 21 days (the planning 0.8 inside): the MDE gate passes 1.0c from `n_eff`
  11,034 (about **13,800** units), the F-MDE gate from `n_eff` 24,520 (about **30,650** units). Power is not the risk; the
  identification gates of section 7 are (a Kalshi spread that rarely changes on the pairs, a Polymarket spread at one tick).
  Prior odds of surviving census given CF10: 0.60.
- **Floors (Unavailable):** < 30,000 units, < 30 events, < 10 UTC days.
- **Economics.** Maker (primary route, gross): after `tightK = 1` with `|dk1| < 0.001c`, post one tick inside Polymarket's touch on
  each side for 20 minutes; after `wideK = 1`, leave (1.10). No taker route (a spread target).
- **Reader it extends.** None: LT10's new reader (8.1) builds every test's units from one pass over the quote lines.
- **Missing data.** 1.5's statuses; `twin_missing` (in the primary, out of the F arm), counted.

## 3. CH223: the other venue's makers flinch first (a Kalshi withdrawal with no Kalshi move and no trade)

- **Hypothesis and mechanism.** Cancellations lead price changes (Cont, Kukanov and Stoikov 2014: order-flow imbalance includes
  cancellations). A maker who learns something cancels or widens before re-quoting. When Kalshi's makers widen or pull their touch
  size **while Kalshi's mid has not moved and no Kalshi trade has printed**, the withdrawal is the earliest public trace of pending
  information on either venue; if Kalshi's makers are better informed on a question (E009's lead says they often are), the size of
  Polymarket's next move is larger. **Direction: within pair, on quiet untraded origins, E[a | pull] - E[a | no pull] > 0.** Who
  would be wrong: the volatility reading (withdrawals happen in volatile minutes and |moves| cluster: world 7, the `rv60` controls,
  and the reported F twin), the bot-refresh reading (Kalshi sizes are re-posted on a cadence: world 6, the autocorrelation, hour and minute-of-hour gates,
  the *bot-cadence* label), the trade reading (a partial fill thins the touch without moving the price: excluded by the
  purity rule, counted `traded_pull`), and the same-news reading (Polymarket's makers see the same public news within the same 10
  minutes, so the |move| after a withdrawal is no larger: a clean null).
- **Unit and population.** Eligible origins (1.4) with **`|dk1| < 0.001c`** (Kalshi's mid did not move over the window; with a 1c
  tick this is `dk1 = 0`) and **no trade signal in the window**: `k_last` unchanged at every consecutive window step and `k_vol24`
  not increased at any step where it is finite at both ends (a step with `k_vol24` missing at either end leaves the unit in, flagged
  `vol_unknown`). Quiet origins with a trade signal are excluded and counted (`traded_quiet`; the withdrawals among them
  `traded_pull`, reported as an arm). Origins with `0.001c <= |dk1| < 0.5c` (sub-penny moves) belong to neither CH223 nor CH222
  (`small_move`, counted).
- **State (frozen; decision time 1.3).** **`pull = 1[sK(t) - sK(s0) >= 0.02 - 1e-9 or (k_bid(t) = k_bid(s0) and k_bid_sz(t) <=
  0.5 x k_bid_sz(s0)) or (k_ask(t) = k_ask(s0) and k_ask_sz(t) <= 0.5 x k_ask_sz(s0))]`** (a widening of >= 2c, or a touch-size
  fall of >= 50% at an unchanged touch price, endpoints of the window). `pull_side` = -1 if only the bid side's size fell (the
  buyers left: Polymarket expected down), +1 if only the ask side's, 0 otherwise (both, or a widening alone). A size of 0 or NaN at
  `s0` on a side leaves that side's size condition false (counted `size_zero`).
- **Target (exact).** **`a = |mP(t + 20 min) - mP(t)|`** (1.3; in cents). M1 (signed, reported, a taker route only): `c_pull =
  pull_side x (mP(t + 20) - mP(t))` on withdrawals with `pull_side != 0`. M2 (reported): Polymarket's spread change `dsP` over the
  same 20 minutes (does Polymarket's maker follow?). S1: `a` at +10 min.
- **Primary statistic.** Expanding-past pair-demeaned OLS of `a` on **`pull`**, controls: E009's seven, `|r1|`, `|r6|`, `|dk6|`,
  `|gap|`, `rv60_P`, `rv60_K`, `sP(t)`, `sK(s0)`, `floorP`, `floorK`, `log1p` of each venue's two touch sizes at `s0`, `log1p
  k_vol24(t)` (+ `vol_unknown`), 23 UTC hour dummies. Tested coefficient: `pull`. Inference 1.7 with the `G_minor` df; seed
  **20261302**. Gate: block FL in pair x UTC day strata (size worlds 1, 2, 3, 6, 7), seed **20261392**.
- **Falsification (F; a reported label, fixed now; 1.9).** Twin `pull'` over `(t + 1,800 s, t + 2,400 s]` (Kalshi fields only).
  Its F-MDE is printed by the census and the label *far-future not excluded* reported; it never changes the verdict.
- **Mechanism readings.** M1, M2; the refit on withdrawals by kind (widening only, size fall only); the refit excluding each pair's
  modal withdrawal minute-of-hour (*bot-cadence*); the `traded_pull` arm (withdrawals with a trade signal, reported).
- **Secondaries.** S1 (+10 min); S2 sports and crypto arms; S3 the excluded-event arm; S4 the non-overlapping grid; S5 the
  pair-deduplicated estimate; S6 counts by withdrawal kind, side and hour.
- **Planning MDE.** Units: quiet share **0.88** of eligible origins (`dk1` non-zero on 12% in E009's pilot) = **135,717 / 226,195**;
  withdrawal share among quiet origins **3% (low) / 6% (high)** (round 15, unprobed) times a declared purity retention **0.8** (the
  share of withdrawals without a trade signal; unprobed): withdrawal units **3,257 / 10,857**, no-withdrawal units **131,646 /
  212,623**; `n_eff` (0.8) 2,606 / 105,316 and 8,686 / 170,099. SD of `a` 0.5c (planning); DE 51; `VIF_w` 1.5; `OF` 1.1. `MDE = 3.47
  x 0.5c x sqrt(1/n1_eff + 1/n2_eff) x sqrt(51) x 1.5 x sqrt(1.5) x sqrt(1.1)` = **0.473c (low), 0.263c (high)**; a quarter of the
  low count 0.947c (fails 0.5c). F-MDE (planning `r` 0.2, factor `sqrt(2 / 0.8)` = 1.5811; a label): 0.749c / 0.415c. **Kill
  line:** the MDE gate passes 0.5c from withdrawal `n_eff` about 2,330, i.e. about **2,913 counted withdrawals in 21 days (about
  139 a day across the panel)**, against 3,257 at the low planning end: little margin. Prior odds of surviving census given CF10:
  0.45; of also passing world 7, about 0.4 of that.
- **Floors (Unavailable):** < 1,500 withdrawal units, < 30,000 no-withdrawal units, < 30 events, < 10 UTC days.
- **Economics.** Maker (primary route, gross): widen or step aside on Polymarket for 20 minutes when Kalshi's makers withdraw; the
  adverse selection avoided against the reward minutes lost on the rewarded subset (1.10). Taker: M1 only, reported.
- **Missing data.** 1.5's statuses; `traded_quiet`, `traded_pull`, `small_move`, `size_zero`, `twin_missing`, counted.

## 4. CH222: the venue that traded first (Kalshi's traded moves against its quote-only moves)

- **Hypothesis and mechanism.** A Kalshi mid changes for two reasons its own feed can tell apart: someone traded through the touch
  (`last_price` changed in the window) or Kalshi's makers re-quoted without being paid (`last_price` unchanged, no volume added).
  Trades carry the information content of prices (Hasbrouck 1991); makers update on trades (Glosten and Milgrom 1985); a
  quote-only revision is Kalshi's makers reacting to something public that Polymarket's makers can see too. **Direction: within
  pair, among Kalshi-move origins, E[c | traded] - E[c | quote-only] > 0**, E009's features sign-adjusted and `|dk1|` held fixed.
  Who would be wrong: the activity reading (trades happen when the pair is active and Polymarket catches up faster then: world 5,
  the `|dk1| x rv60` interactions), the cadence reading (Kalshi's `last_price` field updates on a venue cron: world 4, the hour
  gate), the size reading (traded moves are larger: `|dk1|` and `|dk6|` are controls), the shared-news reading (Polymarket's makers
  watch Kalshi's mid, not its tape, so the cause adds nothing: a clean null that says E009's `dk1` is the whole story).
- **Unit and population.** Eligible origins (1.4) with **`|dk1| >= 0.5c`** (any Kalshi mid move of at least half a 1c tick: E009's
  own object, `dk1 != 0` on a 1c tick; 6.1 item 2). **Classes:** `traded = 1` if `k_last` changed at any consecutive window step
  (both values finite); **quote-only** (`traded = 0`) if `k_last` is unchanged at every step **and** `k_vol24` increased at no step
  where it is finite at both ends (`vol_unknown` flags units with any such step missing); **ambiguous** (`k_last` unchanged but
  `k_vol24` increased: a trade at the previous last price) is excluded and counted (`ambiguous_trade`; reported as an arm).
- **State (frozen; decision time 1.3).** `traded`; `s = sign(dk1)`; `trade_steps` (the number of window steps at which `k_last`
  changed, 1-6; a dose, secondary); `vol_unknown`.
- **Target (exact).** **`c = s x (mP(t + 20 min) - mP(t))`** (1.3; in cents). M1: `c` at +60 min (E010's 1 h horizon; reported).
  M2: the slope of `c` on `trade_steps` within traded moves (reported). S1: `c` at +10 min.
- **Primary statistic.** Expanding-past pair-demeaned OLS of `c` on **`traded`**, controls (sign-adjusted where directional):
  `s x r1`, `s x r6`, `s x gap`, `s x dk6`, `|dk1|`, `lvl`, `lvl2`, `s x lvl`, `|dk1| x z rv60_P`, `|dk1| x z rv60_K`
  (`z` the census's pooled centre and scale), `rv60_P`, `rv60_K`, `sP(t)`, `sK(t)`, `log1p` of each venue's two touch sizes at t,
  `log1p k_vol24(t)` and `vol_unknown`, 23 UTC hour dummies. Tested coefficient: `traded`. Inference 1.7 with the `G_minor` df; seed
  **20261303**. Gate: block FL in **pair x two-day-block** strata (size worlds 1, 2, 3, 4, 5), seed **20261393**.
- **Falsification (F; a reported label, fixed now; 1.9).** Twin `traded'` = 1[`k_last` changed over `(t + 1,800 s, t + 2,400 s]`]
  (Kalshi fields only); the label *far-future not excluded* is reported; it never changes the verdict.
- **Mechanism readings.** M1, M2; the raw class means (*quote-only dominated*); the `ambiguous_trade` arm; the refit with
  `vol_unknown = 0` units only.
- **Secondaries.** S1 (+10 min); S2 sports and crypto arms; S3 the excluded-event arm; S4 `|dk1| >= 1c` only (the round's
  threshold, reported); S5 the pair-deduplicated estimate; S6 counts by class, `trade_steps` and hour.
- **Planning MDE.** Units: Kalshi-move share **10% (low) / 12% (high)** of eligible origins (E009's pilot: `dk1` non-zero on 12%)
  = **15,422 / 30,845**; traded share 0.40 (round 15, unprobed), quote-only 0.55, ambiguous 0.05 (a declared convention):
  traded **6,169 / 12,338**, quote-only **8,482 / 16,965**; `n_eff` (0.8) 4,935 / 6,786 and 9,870 / 13,572. SD of `c` 0.7c
  (planning); DE 51; `VIF_w` 1.5; `OF` 1.1. `MDE = 3.47 x 0.7c x sqrt(1/n1_eff + 1/n2_eff) x sqrt(51) x 1.5 x sqrt(1.5) x
  sqrt(1.1)` = **0.625c (low; fails 0.5c), 0.442c (high)**; a quarter of the low count 1.251c. F-MDE (planning `r` 0.1; a label):
  0.932c / 0.659c. **Kill line:** the MDE gate passes 0.5c from traded `n_eff` about 7,718 at the planning class ratio (quote-only
  = 1.375 x traded), i.e. about **9,650 counted traded moves in 21 days (about 460 a day)**, between the low (6,169) and high
  (12,338) planning ends. Prior odds of surviving census given CF10: 0.30; of also passing world 5, about 0.35 of that.
- **Floors (Unavailable):** < 2,000 traded units, < 2,000 quote-only units, < 30 events, < 10 UTC days.
- **Economics.** Maker (primary route, gross): re-centre the Polymarket quote on Kalshi's traded moves and hold it through
  quote-only moves (the class difference in `c`). Taker (reported): E009's frozen rule on traded moves against quote-only and all
  moves (1.10).
- **Missing data.** 1.5's statuses; `ambiguous_trade`, `small_move`, `twin_missing`, counted.

## 5. Deferred and not taken (each with the reason; none counted)

### 5.1 CH230 (the three-venue fine-clock map): not taken; a later decision
CH230 would add matched PredictIt and Smarkets contracts to the poller's pair list (a pair-list change to an existing collector,
after E010's analysis; round 15 calls it an owner decision). It is not needed for LT10 (Kalshi alone carries the three states),
its population is unprobed (planning 100-300 contracts in 10-40 events), and adding pairs mid-way would change the stream between
census and window. **LT10 runs on Kalshi pairs only; any pair-list extension must wait until LT10's `END_UTC` + 2 h** (declared
now: the D-LT10-1 successor polls exactly the E009 pair-refresh rule). The Smarkets and PredictIt twins of CH222-CH224 are not
computed.

### 5.2 CH225 and CH226 (the sports arm): deferred for the owner's sports-scope decision
Both are sports-only by construction (ESPN's board against Polymarket's game markets), need CH205's 42-day rule and a matcher
that is a map first, and read a stream (`stream_espn_odds/`) no LT has read. They are not in this Holm family and cannot join it
(k is fixed by LT10's censuses alone). If the owner sets sports in scope, they would be drafted as their own family with CH205
(`steam` token requested then). LT10 itself keeps sports as a parameter (1.4 item 2): the owner's decision before the pin changes
LT10's scope, not its design.

### 5.3 CH227-CH229, CH231 (engine-first): not tests
The entity clock (`xent`), rule freshness (`ruleedit`), the published close and capture-clock shadows (`xvenue2` columns) and the
in-game state (`gamestate`) are engine columns at the capture clock, where round 15 0.1 shows no cross-venue test reaches its MDE.
LT10 requests no token for them; the engine track builds them under its own rules (each raises K).

## 6. Design changes, census drops

### 6.1 Design changes to the round-15 sketches (made before any data; each needs the challenger's acceptance)

1. **Origins, overlap and the MDE.** The round counted 144 origins a pair-day and also cited "non-overlapping origins per horizon
   as E009's `_design`", which would give 72. LT10 keeps all 144 (the 10-minute grid, where every Kalshi window is distinct) and
   carries the 10-minute target overlap in three places: the overlap factor `OF` in every planning and census MDE, the MA(1)
   term of the census's design-based MDE (section 7), and the block (circular-shift) gate, which keeps serial dependence. The
   non-overlapping grid is a reported sensitivity.
2. **CH222's move threshold is E009's object (`|dk1| >= 0.5c`), not `|dk1| >= 1c`.** The round's arithmetic applied the pilot's
   non-zero share (12%) to a >= 1c threshold, but the ledger's pilot quantiles (median 0, 90th percentile 0.5c, 99th 2c) put the
   >= 1c share below 10% and plausibly at 3-6%, where the MDE exceeds 0.9c even at the high planning end. With a 1c tick the
   elementary Kalshi quote event is a one-side, one-tick change (0.5c of mid), which is exactly what E009's `dk1` pools; the
   round's threshold is kept as secondary S4. The pilot quantiles were known to the designer (ledger E009 entry); no other count
   was used.
3. **Purity rules (declared before any count).** CH222's quote-only class and CH223's quiet population require `k_last` unchanged
   at every window step **and** no `k_vol24` increase where finite (a trade at the previous last price leaves `k_last` unchanged),
   with `ambiguous_trade` and `traded_quiet` excluded and counted. The round's CH223 allowed a trade-driven size fall without a mid
   move inside the withdrawal class; that is the trade channel CH222 owns, so the two populations are now disjoint by construction
   (Kalshi moved / Kalshi still and untraded). CH223's quiet condition is `dk1 = 0` (not the round's `|dk1| < 1c`, which included
   one-tick moves belonging to CH222 after item 2).
4. **CH224's scale is one pooled census constant, not the per-pair census SD.** Pairs enter the list daily; a pair first listed in
   the window has no census SD, and a per-pair SD of a mostly-zero state is unstable. A pooled constant makes the test equivalent
   to raw cents and only sets the material scale.
5. **CH224's identification gate replaces the round's "per-pair SD of `dsK` >= 1c in >= 50% of pairs".** With a 1c tick and a
   change share p, the SD of a +-1c state is `sqrt(p) x 1c`, below 1c for every p < 1: the round's gate would kill CH224 by
   arithmetic whatever the mechanism. The replacement asks for what identification needs: `dsK != 0` on >= 10% of units (the
   round's own kill line), on >= 5% of origins in >= 50% of pairs with >= 500 units and >= 30 such pairs, and both signs present
   (each >= 25% of the non-zero changes) (section 7).
6. **CH222's gate strata are pair x two-day block** (round 15 rule 12 says pair x UTC day): its units are 10-12% of origins, about
   12-15 a pair-day, below the gate's 16-row minimum, so pair-day strata would leave most units out of the gate. Two-day blocks hold
   about 24-29 units at the planning shares.
7. **F roles fixed by design, not by census counts** (LT9 R1 fix 1). The round made CH223's F a verdict condition "if the census
   shows >= 7,500 pull origins" and CH222's "if `n1_eff` >= 16,000"; both are count-switched verdict conditions, which LT8 and LT9
   ruled out. LT10 fixes CH224's F as binding and CH223's and CH222's as labels, and makes their mechanical channels binding as
   leak worlds 7 and 5 instead (CH212's pattern in LT9).
8. **Volatility and activity controls added** (`rv60_P`, `rv60_K`; for CH222 the sign-adjusted E009 features and `|dk1| x z rv60`
   interactions; for CH223 the absolute E009 features). The round's controls were E009's seven, the spreads and sizes, hour dummies
   and a tier; a |move| target and a traded/quote split each have a volatility or activity confounder that the seven raw features
   do not carry.
9. **"Tier" replaced by time-varying liquidity controls** (log touch sizes on both venues and `log1p k_vol24`): the quote lines carry
   no Gamma liquidity, and a pair-level tier is removed by the pair demeaning.
10. **Census span `[2026-10-21, 2026-10-31)`, not the whole worn span `[10-13, 11-03)`**: ten days (as LT8 and LT9) that avoid the
    canonical gaps of 10-13, the 10-14 outage and its validation-copy gap-fill (an E009/E010-specific rule), and end before the US
    daylight-saving change of 11-01; the counts-only rule is unchanged.
11. **`DE_gate` for the fine clock** (section 7): `max(51, 1 + (m_w - 1) x 0.0016667)`, where the ICC 0.0016667 = 0.02 x 252 / 3,024
    holds the capture-clock convention's 21-day cluster share per pair constant (0.02 at 252 units a pair is 0.00167 at 3,024).
    Round 15 declared 51 as a capped convention and noted that LT9's formula at 0.02 would be far larger; this makes the census
    able to raise DE above 51 when one event dominates, never lower it.
12. **Collection made an explicit dependency with a decision** (8.2): the round named the poller's continuation "unprobed"; the
    readiness audit's 2 GiB-cap projection (about 2026-11-16) makes a change necessary, not optional.
13. **Registration does not depend on E009's or E010's verdicts**, and a freeze after `T_E009` drops the family (1.1): both declared
    now so that knowing E009's result cannot select whether or how LT10 runs.
14. **Multiplier 3.47 kept; no extension; a staleness stop** (`REGISTERED_UTC` after 2026-11-30 -> not registered).

### 6.2 Census drops
None yet. Census drops (including a family-wide CF10 drop) will be recorded here, with their counts, before the pin.

## 7. Pre-registration censuses (counts only; before registration; worn pre-window data; no target read)

Each census runs once, reads origin-side fields only (no target, no P&L, no prediction or outcome file; 1.6), prints counts, and is
committed with its sha256 before the registration commit. **Kalshi-only lag loader:** a census reading a poll later than a unit's
origin (the F twins only) receives only the keys and `k_bid`, `k_ask`, `k_last`, `k_bid_sz`, `k_ask_sz`, `k_vol24`, `k_status`,
`k_recv` of that poll; no Polymarket field of a later poll reaches census code (unit test, 8.3). **Every gate threshold below is
stated now, before any census.** A failed gate drops that test before registration (uncounted); a failed CF10 gate drops all
three; `k_tests` lists the survivors. **Input identity:** the census refuses unless every input file it opens is named in the LT10
seal with an equal sha256, builds origins from the seal, and refuses if a sealed file is absent.

**Inputs (a seal; round 14 rule 9).** The census span is **`[2026-10-21T00:00Z, 2026-10-31T00:00Z)`**, 10 UTC days, 1,440 grid
origins a pair. Files: E009-era `cross_venue_live/quotes/20261020.jsonl.gz` (look-back from 2026-10-20T22:56Z only) through
`20261031.jsonl.gz` (twin polls to 2026-10-31T00:32Z only, Kalshi fields; the loader stops there); every `pairs/pairs_*.json` whose
`refreshed_utc` lies in `[2026-10-19T00:00Z, 2026-10-31T00:00Z)` (the records in force); the `rows_ext.csv.gz` sidecar (category
columns and keys only) of the last complete capture before each census day's 00:00Z (10 files, captures of 10-20 to 10-29). The quote and
pair files have no retention rule on the host; the earliest sidecars (about 10-20..10-24) will have left the host (snapshot retention 10 days)
by the seal date and are restored byte for byte from the data releases. Planned volume: about 12 quote files (planning 150-400 MB
in all), about 12 pair files, 10 sidecars: well under 1 GB.
- **Restore, seal, census: each once, after E010's analysis commit.** q0660 accepts host copies that pass a sha256 check against
  the archive catalogue and restores the missing sidecars from the releases; it measures bytes first and stops and asks the owner
  if the restore would exceed the host's free disk; a file found in neither place is genuinely missing (counted, never
  substituted). q0661 writes `seals/lt10_census_inputs.json` (files, sha256, the frozen LT10 design-text sha256, and E010's
  analysis commit hash, so the seal is provably written after both); the orchestrator commits it before any LT10 census runs.
- **Minimum covered days** (covered origins of active pairs / (144 x active pairs), summed over days) >= 7.0 for every census.
  Below it, every gate is NaN and fails.
- **Field presence (first stage of CF10; no gate on values):** the shares of Kalshi-valid lines with `k_last`, `k_bid_sz`,
  `k_ask_sz`, `k_vol24`, `k_recv` finite, and of Polymarket-valid lines with `p_bid_sz`, `p_ask_sz`, `p_recv` finite, each must be
  >= 95%, else the dependent tests' gates are NaN and fail (`k_last` -> CH222 and CH223; sizes -> CH223; `k_vol24` -> printed only,
  the `vol_unknown` rule covers it).

**Projection** = census count x 21 / covered days. **Distinct events** over the covered days (pessimistic; never projected upward).
**Effective counts** = units of the test in pairs with >= 20 units of the test over the census days. **Design effect:** `DE_gate =
max(51, 1 + (m_w - 1) x 0.0016667)`, `m_w = Σ_e m_e^2 / Σ_e m_e`, `m_e` the projected 21-day units of the test in event e (6.1 item
11). **Overlap factor:** `OF = 1 + max(0, rho_x1)`, `rho_x1` the within-pair lag-1 autocorrelation of the tested term over
consecutive grid origins of the test's units (expanding-past demeaned; pairs with >= 20 units). **MDE gate formulas (multiplier
3.47), each `max(declared, design)`:** *declared* = the closed formula of sections 2-4 at the census's projected effective counts,
`DE_gate`, `VIF_w` (census, with `max(1, .)`), `OF` and the declared SD; *design* = `3.47 x 1.5 x SD x se_1` from the census
regressors under a working covariance with unit variance, correlation 0.5 between a pair's adjacent grid origins (the target
overlap), 0.5 between units of one event at the same origin, 0.0016667 between any other two units of one event, and independence
across events, scaled to 21 days; no target is read. **F-MDE** = `max(design-based MDE of Δ in the arm model, MDE x sqrt(2 / (1 -
max(0, r_gate))))`, `r_gate = max(r_w, r_pool)` of the lead and twin on census units with both (within-pair on expanding-past
demeaned values over pairs with >= 20 such units; pooled printed). SDs: `dsP` 1.0c, `a` 0.5c, `c` 0.7c. **Count gates are on gross
projected counts** (all filters, x 21 / covered days, no 0.8); the declared MDE uses the measured effective share in place of 0.8
(LT9 7).

**Order (cheapest kill first; each stage runs only for the tests still alive):** **CF10** (the family: pair files and line validity
only; seconds) -> **CK10** (Kalshi-side state shares; no Polymarket field beyond validity) -> **CD10** (design gates with the
Polymarket origin-side controls).

| Census | Test | Gate (all must hold; NaN fails) | Values fixed into the spec |
|---|---|---|---|
| **CF10** | family (all three) | minimum covered days >= 7.0; field presence (above); **distinct primary-eligible pairs (scope default; each with >= 144 eligible origins over the census days) >= 60**; **distinct Polymarket events of those pairs >= 30**; `late_origin` share <= 10% of pair x grid origins; event concentration: if the top event holds > 40% of eligible origins it is excluded (`exclude_event`) and the two count gates are re-applied without it | `exclude_event`; `scope` as in force |
| **CK10** | CH224 | share of units with `dsK != 0` >= 10%; among pairs with >= 500 units, >= 50% have `dsK != 0` on >= 5% of their units, and >= 30 such pairs; tightenings and widenings each >= 25% of non-zero `dsK`; venue clock: the most common UTC hour holds <= 50% of non-zero `dsK`; `r_gate` (of `zdsK`, `zdsK'`) <= 0.3 on >= 30 pairs | `scale_K` (pooled SD of `dsK`, cents); `rho_x1` |
| **CK10** | CH223 | projected quiet untraded units >= 50,000; withdrawal share among them in [1%, 15%]; **projected withdrawal units >= 2,920 (about 139 a day)**; `traded_pull` share of all quiet withdrawals printed; venue clock: the most common UTC hour holds <= 50% of withdrawals; **bot cadence:** within-pair lag-1 autocorrelation of `pull` < 0.5, and the modal minute-of-hour (`t mod 3,600`, six values on the 10-minute grid) holds <= 50% of that pair's withdrawals in >= 50% of pairs with >= 10 withdrawals (a 10-minute bot cadence shows as autocorrelation, an hourly one as a modal minute); >= 30 pairs with >= 10 withdrawals | `rho_x1` |
| **CK10** | CH222 | **projected traded units >= 9,650 and projected quote-only units >= 9,650**; traded share among Kalshi moves in [15%, 85%]; `ambiguous_trade` share <= 25% of Kalshi moves; venue clock: the most common UTC hour holds <= 50% of traded flags; within-pair SD of `traded` >= 0.2 in >= 50% of pairs with >= 20 moves, and >= 30 such pairs | `rho_x1` |
| **CD10** | CH224 | `VIF_w(zdsK)` <= 2.0; within-pair `\|corr(zdsK, x)\|` <= 0.5 for x in {`\|dk1\|`, `traded`, `dsP_own`, log Polymarket touch size, `rv60_K`}, and pooled `\|corr(zdsK, log Polymarket touch size)\|` <= 0.5; block-gate share >= 50% of units in pair-day strata with >= 16 units; **slope MDE <= 1.0c; F-MDE <= 1.0c (binding)** | `DE_gate`; `OF` |
| **CD10** | CH223 | `VIF_w(pull)` <= 2.0; within-pair `\|corr(pull, x)\|` <= 0.5 for x in {`rv60_K`, `rv60_P`, log Kalshi touch size, `sK(s0)`}, pooled `\|corr(pull, rv60_K)\|` <= 0.5; block-gate share >= 50%; **MDE <= 0.5c**; F-MDE printed (a label) | `DE_gate`; `OF` |
| **CD10** | CH222 | `VIF_w(traded)` <= 2.0; within-pair `\|corr(traded, x)\|` <= 0.5 for x in {`\|dk1\|`, `rv60_K`, `rv60_P`, log Kalshi touch size}, pooled `\|corr(traded, \|dk1\|)\|` <= 0.5; block-gate share >= 50% of units in pair x two-day-block strata with >= 16 units; **MDE <= 0.5c**; F-MDE printed (a label) | `DE_gate`; `OF`; the `rv60` centres and scales for the `\|dk1\| x z rv60` controls |

- **Descriptive (no gate):** every census prints the scope splits (sports, crypto, unknown; for the owner's sports decision, the
  with-sports CF10 counts as an uncounted print), pairs and events a day, hand-verified shares, pair turnover a day, the event
  size distribution and the top event's share, retired-pair polls, `spread_censored`, `window_gap`, `rv_short` and `end_soon`
  shares, receipt-lag quantiles, `k_vol24` presence, the pairwise unit overlaps and tested-term correlations of 1.11, and the
  computed DE beside `DE_gate`. **CH224:** the distribution of `dsK` in ticks, `floorP` and `floorK` shares, the within-pair AR(1)
  of Polymarket's spread on origins (for world 8), the rewarded-pair share of the day's feed. **CH223:** withdrawals by kind and
  side, `traded_pull`, `size_zero`, the minute-of-hour histogram. **CH222:** moves by size, `trade_steps`, `ambiguous_trade`, the class
  shares by hour.
- **Expected census fates (declared now).** **CF10** is the likeliest killer: E009's pilot had 22-27 events, its planning 40
  (25-60), and the default scope removes sports game props, which the daily refresh adds. **CH224** then fails only on a Kalshi
  spread that rarely changes or on its VIF and correlation gates (`traded` and `|dk1|` correlate with `dsK` because a trade that
  clears a level widens the spread). **CH223** has little margin on its count gate (2,920 against 3,257 at the low end) and must
  clear the bot-cadence gates. **CH222** needs the high planning end (about 460 traded moves a day).

**Census jobs (to be drafted later under `docs/research_lab/queue/drafts/` in README format; ids q0660-q0667, checked unused across
`docs/research_lab/queue/` in every local and remote-tracking ref on 2026-10-23: the q06xx ids used are q0600-q0604 (with q0601b,
q0601c) and q0620-q0623 and q0640-q0647; none is written in this commit).**
- `q0660_lt10_census_restore` (lane `net`, about 300 MB disk, about 200 MB RAM): verify the span's quote and pair files on the host
  by sha256 against the archive catalogue where catalogued; restore the missing sidecars; bytes first (disk stop rule).
  `depends_on` the LT10 design-text freeze and E010's analysis commit (a ledger line naming it).
- `q0661_lt10_seal` (lane `net`, about 200 MB; after q0660): `run_live_tests10.py seal` writes `lt10_census_inputs.json`.
- `q0662_lt10_census_family` (cpu, about 200 MB; after the seal commit): CF10.
- `q0663_lt10_census_kalshi` (cpu, about 250 MB; after q0662, only if CF10 passed): CK10, streaming per day file.
- `q0664_lt10_census_design` (cpu, about 300 MB; after q0663, only for survivors): CD10.
- `q0665_lt10_size_check` (cpu, about 800 MB; after the census values are committed, so k is fixed before any size result exists;
  `max_retries 1` deterministic-crash only; planning 6-12 h; not concurrent with E011's or LT2's analysis).
- `q0666_lt10_reader` (fallback only, never promoted while the cron line of 8.2 exists).
- `q0667_lt10_analysis` (cpu, about 2,500 MB, **exclusive**, `not_before` the analysis date).
All are DRAFT and must not be promoted before the challenger review, the design-text freeze, the code and its freeze check, and
**never while another census, size-check or analysis job of the memory-heavy class is running**. Each counts 0.

## 8. Implementation plan (no code in this commit)

### 8.1 Modules to be written (engineering list)
- **Vendored, not imported.** `backend/astrolabe/research_lab/live_tests10_base.py` is **generated** by
  `backend/scripts/vendor_lt10_base.py`: unmodified copies of E009's `two_sided_mid`, `in_range`, `lookup`, `features`,
  `round_trip_cost`, `predict` and the constants they use (`MAX_SPREAD`, `MID_RANGE`, `LOOKBACK_TOL_S`, `OUTCOME_TOL_S`,
  `MAX_RECV_LAG_S`, `FEATURES`) from `cross_venue_live.py` sha256
  `eac14e68dc7a9d60610d9ea5d2edfdc39be73afd0192d6b41cd3d5459e5ef581` (last changed at `9beda37`, E010's registration), and LT3/LT4/
  LT5/LT9's `fit`, `attrition`, `lee_bounds`, `paper_taker`, `econ`, `de_gate`, `block_fl_gate`, `holm`, `expanding_demean`, the
  seal reader and the sports and crypto classifiers (`cb17_census.is_sports_sidecar` and its frozen lists), each by recorded hash.
  The vendor script refuses unless the source hashes equal those recorded; a `VENDORED` table records source file, source sha256
  and normalised-source sha256; a unit test fails on drift; another proves no LT10 module imports `cross_venue_live*`,
  `live_tests3*` .. `live_tests9*`. No frozen or registered module is edited (`cross_venue_live.py`, `cross_venue_live_e010.py`,
  `cross_venue.py`, `live_tests3*` .. `live_tests9*`; nothing of E026).
- `backend/astrolabe/research_lab/live_tests10.py`: the streaming quote reader (per pair, a 66-minute ring of polls), the pair-record
  and sidecar resolvers, the unit builders (`hedge_units`, `flinch_units`, `traded_units`), the Kalshi-only twin builder, the target
  writer and the counts-only censuses (`census_family`, `census_kalshi`, `census_design`). `run_once()` (internal non-blocking
  flock on `live_tests10/run.lock`) reads only new complete lines (an incomplete trailing line is left for the next run) and writes,
  write-once (`%.17g`, atomic hard link): `status/<YYYYMMDD>/<HHMM>.csv.gz` (origin statuses), frozen units
  `<kind>/frozen/<YYYYMMDD>/<HHMM>.csv.gz` with their write time, targets `<kind>/outcomes/<YYYYMMDD>/<HHMM>.h<min>.csv.gz`,
  twins `<kind>/twins/<YYYYMMDD>/<HHMM>.csv.gz`, and `runs.jsonl`.
- `backend/astrolabe/research_lab/live_tests10_analysis.py`: the single analysis (1.7-1.10, the F arms, Holm over k, counting) and
  the size check (1.8, 1.8.1) with the scenario-to-test map (fail-closed on an unknown or missing scenario).
- `backend/scripts/run_live_tests10.py`: `run`, `ops-stats`, `seal`, `census-family`, `census-kalshi`, `census-design`,
  `size-check`, `analyze`; censuses accept `--data-dumps-cap-gb` and exit 75 above it; `size-check` refuses `--worlds/--draws`
  without `--dev`; `analyze` refuses before the date, an unpinned, null or NaN spec, or a `k_tests` naming a dropped test.
- **Only under D-LT10-1 route 1 (8.2):** `backend/astrolabe/research_lab/xv_quotes_poller.py` and
  `backend/scripts/run_xv_quotes_poller.py`: a quotes-only successor of E009's poller, generated in its fetch, parse, pair-refresh
  and matching parts from `cross_venue_live.py` and `cross_venue.py` (sha256
  `5264083948a77679189f14471290c2f84bf71dac01fc9632cb0633fdb59ace99`) by the same vendoring rule, reading the hand verdicts
  `cross_venue_live_verified.json` at sha256 `1d6f942a...c54c` (E009's frozen file) and `LIVE_EXTRA_CONFLICT` unchanged; same
  `CYCLE_S` 120, `MAX_PAIRS` 200, `CHUNK` 100, `RETIRE_KEEP_S` 6 h 20 min, `REFRESH_EVERY_S` 86,400, pacing and backoff; no
  predictions, no outcomes; quote lines with E009's schema plus a trailing `"src": "xv_quotes_v1"`; its own cap (3.0 GB on its
  directory, exit 3); RSS budget 200 MB. Tests: the line schema equals E009's on a recorded synthetic cycle; the refresh rule
  selects the same pairs as `select_live_pairs` on a fixture; no prediction or outcome file is written.
- Spec `backend/astrolabe/research_lab/model_specs/live_tests10_v1.json`: every constant, k, `scope`, `exclude_event`, the fixed F
  roles (CH224 binding, CH223 and CH222 labels; no census-set key), seeds (estimators 20261301-03, gates 20261391-93, size check
  20261397 and its derived seeds), dates, `T_X` rules, `scale_K`, the `rv60` centres and scales, `rho_x1` and `OF` per test,
  `DE_gate` per test, the stream root of the window (D-LT10-1), the `code_sha256` map, the vendored hashes and E009's frozen spec
  hash (economics).
- `battery2.KIND_RULES["live_tests10"]` (fail-closed counting entry).

### 8.2 Resources, collection plan and install
- **LT10's reader fetches nothing.** A pure reader of the quote lines, the pair records, one sidecar a day and one feed capture a
  day.
- **D-LT10-1: the quote stream after E009's window (a decision for the orchestrator; required for registration).**
  - **Facts.** The poller (`run_cross_venue_live.py`, supervised by `scripts/oracle/supervise.sh` under cron `@reboot` and `*/5`)
    has no end date in code; E009's and E010's windows end 2026-11-03T00:00Z and their analyses follow. Its hard cap is
    `TOTAL_CAP_BYTES = 2 * 1024**3` on its whole directory (predictions, outcomes, E010 lines and quotes; `CapReached`, exit 3),
    and the supervisor does not restart a monitor whose last exit code was 3 (`COLLECTION_HOST.md`). The readiness audit
    (`LIVE_TESTS_READINESS_2026-10-19.md` R3) measured 425 MB on 10-19 growing about 60 MB a day and projected about 1.3 GB on
    11-03; at that rate the cap is reached about **2026-11-16** (a projection, not re-measured; no host read was made for this
    draft). The engine's `xvenue` family reads the same `quotes/` directory live (`signal_engine/config.py` `XV_QUOTES_ROOT`).
  - **Requirement.** The same pair refresh, endpoints, 120 s UTC grid and line schema must run without a planned interruption from
    E010's analysis commit through `END_UTC + 2 h`, with disk headroom >= 1.5 x the projected need, and E009/E010's canonical
    directory must not be edited (CLAUDE.md: canonical runs in `data-dumps/` are never edited).
  - **Route 1 (recommended): a quotes-only successor in a new directory.** At a 120 s boundary after E010's analysis commit (and
    after the gap-fill merge the analyses use), the orchestrator disables E009's poller (`run/cross-venue-live.disabled`, last
    cycle recorded) and starts `run_xv_quotes_poller.py` (8.1) under a new `supervise.sh` entry `xv-quotes`, writing
    `data-dumps/research_lab/xv_quotes/` (`quotes/`, `pairs/`, `pairs_current.json`, `runs.jsonl`). The missed cycles of the
    handover are counted and stay missing. Why: E009/E010's directory becomes byte-stable at their analyses; the successor writes
    no predictions or outcomes (about 38 MB a day saved); its quotes alone are about 30 MB a day raw before the 2-day gzip (the
    compressed size is unprobed), so 3.0 GB covers the window with a wide margin. Cost: the engine needs a second read root for
    `xvenue` (`XV_QUOTES_ROOT` -> both directories, an engine-track change requested in 9; column definitions unchanged); until it
    is made, the engine's `xvenue` columns are NaN for captures after the handover (missing, not filled). Request rate unchanged
    (4 requests per 120 s; one daily refresh of about 2,700 pages at <= 0.9 requests a second); the same keyless public endpoints;
    **no new external service**.
  - **Route 2 (not recommended): raise the cap of E009's poller** (an edit to `cross_venue_live.py` after E010's analysis, logged
    as a deviation). It keeps the engine path but writes new files, including about 38 MB a day of unused prediction and outcome
    lines, into a completed experiment's canonical directory, and changes a module LT10 vendors from (the vendor hash would then be
    re-recorded before LT10's code freeze).
  - **Route 3: no change.** The poller stops at its cap about 11-16: LT10 is not registered (recorded; nothing counted).
  - **Who decides.** A light change to an existing keyless collector under the standing collection authorisation: the
    orchestrator's decision, recorded in the ledger with the route, the handover cycle and a `du` and free-disk reading. **It goes
    to the owner only** if the host's free disk cannot hold the projected need with the 1.5 x margin (CLAUDE.md storage stop rule)
    or if any deletion of E009/E010 files from the host would be needed (data retirement); neither is expected.
  - **Burn-in (counts only, five days before `REGISTERED_UTC`).** `run_live_tests10.py ops-stats --stream` prints per day: cycles
    run against 720, pairs per cycle, Kalshi and CLOB request success shares, both-valid share, receipt-lag quantiles, refresh
    completions; it reads no price, spread or size. Acceptance (declared now; operational, not a design gate): >= 95% of cycles run,
    request success >= 95% on each venue, median receipt lag <= 20 s, one refresh a day. A failure is fixed operationally and the
    burn-in restarts, moving `REGISTERED_UTC` under 1.1 (c).
- **Memory (planning, then a ladder).** The reader holds per active pair a 66-minute ring of polls (33 lines) and today's pair
  record: **planning peak 120-200 MB** (E009's poller is 115-132 MB with feature history). Ladder, measured by a host dry run with
  the exact install command before the pin: (1) one reader under `ulimit -v 1048576`, accepted if peak RSS <= 300 MB; (2) else no
  pin (recorded). The censuses stream one day file at a time (<= 300 MB).
- **Install route: host cron** `3-58/5 * * * *` (every 5 minutes, offset from the even-minute polls), own `flock`, `nice -n 19`,
  `oom_score_adj 1000`, `ulimit -v 1048576`. The queue draft q0666 is the fallback, **never both**.
- **CPU:** seconds a run. **Disk:** about 0.3-0.6 GB over the window (three kinds, about 150,000-260,000 origins); the reader stops
  writing at 1.5 GB in `live_tests10/`.
- **Analysis job:** about 0.3 million unit rows per kind at most; the block gate refits 200 times; planning 1.5-2.5 GB peak,
  **exclusive**, single run.
- **Host change:** the reader's cron line and (route 1) the successor's `supervise.sh` entry are host changes under the standing
  collection authorisation, done by the orchestrator, each with a ledger line.

### 8.3 Tests to be written (`backend/tests/unit/test_research_lab_live_tests10.py`, synthetic only)
- **Windows and clocks:** `s0` equals E009's `lookup(hist, t, 600)` on fixtures; `window_gap` below 4 polls; the decision time is
  `max(k_recv, p_recv)` of poll t; `late_origin` at a receipt 61 s after t; the target endpoint rule (exact poll, nearest within
  +-120 s, receipt lag, statuses) and that no endpoint is scheduled before t + 1,080 s; the freeze deadline and `.late`.
- **Eligibility:** the pair record in force (a refresh after t is not used; a retired pair gives `retired`); the category rule on
  sidecar fixtures (sports, crypto, unknown); the ends rule; `spread_censored`; `rv_short`; the boundary (`lt10_boundary` for
  t - 3,840 s < `REGISTERED_UTC`); `exclude_event`.
- **CH224:** `dsK`, `zdsK` with the pooled scale; `floorP`, `floorK`, `tightK`, `wideK`; the design matrix; the twin through the
  Kalshi-only loader; the block gate's pair x day strata.
- **CH223:** the quiet condition at `dk1 = 0`; the purity rule (`k_last` change at an intermediate step excludes; a `k_vol24`
  increase excludes; a missing `k_vol24` step flags `vol_unknown`); `pull` at its edges (widening of exactly 2c; size exactly 50%;
  a size fall with a changed touch price is not a pull); `pull_side`; `size_zero`; the minute-of-hour print.
- **CH222:** `|dk1| >= 0.5c` at its edge; the three classes (traded, quote-only, ambiguous); `trade_steps`; the sign-adjusted
  controls; the two-day-block strata.
- **Disjointness:** no origin is both a CH222 and a CH223 unit (property test over random streams).
- **Causality:** altering every quote line after an origin (both venues) leaves that origin's frozen line byte-identical;
  altering Polymarket fields after each census origin leaves every census output unchanged except later origins' own
  contributions; the Kalshi-only loader returns no Polymarket field (a test plants wild Polymarket values in later polls).
- **Paths:** the allow-list refuses `predictions*.jsonl`, `outcomes*.jsonl`, the validation copy and every store of 1.2's "not
  read" list; `ops-stats` reads no price, spread or size column.
- **Vendored base:** the `VENDORED` provenance check; no LT10 module imports `cross_venue_live*` or `live_tests3*` ..
  `live_tests9*`; copied constants equal their sources; E009's `features` reproduces recorded synthetic values.
- Shared: write-once, dry-run guard, `%.17g` round trip, run lock, incomplete trailing lines skipped; the `code_sha256` map;
  counting equals k; Holm; the p = max rule and the `G_minor` df; F's two conditions, the fixed F roles (no spec key can switch
  them) and the Inconclusive mapping; the analysis refusals; the design-freeze, `T_E009` and staleness rules (registration refused
  when the freeze is not before `T_E009` or `REGISTERED_UTC` > 2026-11-30); sealed censuses (counts only, origins from the seal,
  tampering refused, completeness, minimum covered days, the stage order and early exit); each MDE and F-MDE gate formula with
  `max(declared, design)`, `DE_gate` and `OF`; the scenario-to-test map (a failing scenario sets only its own tests to "SE check
  failed" with k unchanged; the power runs never bind); an end-to-end synthetic analysis with a reduced `k_tests`.

### 8.4 Registration steps and pins (in order)
1. Challenger R1 on this file; the response and any re-check. **At acceptance, and in any case before 2026-11-04T00:00Z, the engine
   embargo requests of section 9 are filed in `signal_engine/CANDIDATES.md` and applied by the engine track** (not a registration
   step; before `xvenue` lapses, so no `kx_*` column can be built unembargoed).
2. **Design-text freeze commit**, its sha256 in the ledger, before 2026-11-03T02:00Z and before `T_E009`.
3. Code (8.1, 8.3), vendored by hash; a `science-reviewer` freeze check of the census and size-check code against 1.8, 1.8.1 and 7;
   fixes (none may change frozen text). The successor poller (route 1) is code-checked in the same pass.
4. E010's analysis commit exists (ledger). D-LT10-1 executed and recorded (route, handover cycle, `du`, free disk); the burn-in
   starts.
5. q0660 restore, q0661 seal, seal committed and pulled on the host.
6. Censuses q0662-q0664 (counts only, stage order); drops recorded in 6.2; `k_tests`, `scope`, `exclude_event`, `scale_K`, the
   `rv60` centres and scales, `rho_x1`, `OF` and `DE_gate` filled with the exact census floats; a freeze record written (module
   hashes, spec hash before the pin, census output hashes re-verified on the host, spec values checked against the census JSON).
7. Size check q0665 (2,000 worlds x 200 draws, seed 20261397); results recorded per test.
8. Reader freeze check; host dry run with the exact cron command on the continued stream (the ladder step used is recorded); the
   burn-in's acceptance recorded.
9. The embargo entries of step 1, **including the attribution limits of section 9**, verified in `config.EMBARGO` and
   `signal_engine/CANDIDATES.md` (a missing entry blocks the pin); any token of a test dropped at census withdrawn with a ledger line.
10. Pins: `SPEC_SHA256`, `code_sha256` map, `code_check` passing; E-numbers assigned from the ledger; the ledger entry is the
    registration commit, at least 24 h before `REGISTERED_UTC`.
11. Install the reader's cron line before `REGISTERED_UTC`; verify `pinned: true` and that origins before the boundary are counted
    `lt10_boundary`; queue q0667 with `not_before` the analysis date.

## 9. Signal-engine mapping and embargo requests

Every column below is point-in-time from the last quote lines received before the capture start (DESIGN_V1 section 3's `xvenue`
clock: quote age <= 30 min) and the Kalshi lines of the 10-minute window before them. Each would extend the existing `xvenue`
isolates (`se4_lr_xvenue`, `se13_lgbm_xvenue`) at a new spec version, as round 15 proposes (coverage 0.25% of eligible rows: no new
challenger, no K cost). **Embargo first** (DESIGN_V1 8): "LT10 date" below means **the later of 2026-12-04T00:00Z and LT10's
analysis commit** (analysis date 2026-12-02T12:00Z plus about 36 h; it moves later with `REGISTERED_UTC`). This branch does not
edit `CANDIDATES.md`, engine code or `config.EMBARGO`.

| Test | Columns (NaN = missing) | Source and clock | Token -> until |
|---|---|---|---|
| CH224 | `kx_spread_chg_10m`, `kx_spread_ratio` | the last Kalshi and CLOB lines before the capture start and Kalshi's line about 10 minutes earlier | `kxbook` (new) -> LT10 date |
| CH223 | `kx_pull_10m`, `kx_pull_side` | as above | `kxbook` -> LT10 date |
| CH222 | `kx_last_chg_10m`, `kx_dk1_traded`, `kx_dk1_quote`, `kx_trade_steps` | as above | `kxbook` -> LT10 date |

**Requests to the signal-engine track.**
- **New token `kxbook`** to the LT10 date, entered at design acceptance and in any case **before 2026-11-04T00:00Z** (when `xvenue`
  lapses and the isolates could be extended). It covers any model whose spec isolates, or adds to a broad model, any column that reads
  Kalshi's within-window book changes (last-price changes, touch-size changes, spread changes, and the traded/quote-only split of a
  Kalshi mid change). `se4` and `se13` at their current spec versions are **not** covered (they hold levels only); a new version that
  adds any `kx_*` column is.
- **Attribution limits `attrlimit_lt10`** (kind `attribution_limit`, to the LT10 date): no attribution (SHAP or otherwise) of the
  champion, `se4`, `se13` or any broad model on Kalshi within-window changes or on interactions of Kalshi's spread with Polymarket's
  spread, computed or shown before the LT10 date. Entered by the engine track in `config.EMBARGO` and `CANDIDATES.md`; 8.4 step 9
  verifies both.
- **`xvenue` is not extended.** Reason and cost: its columns are capture-time levels (has-pair, gap, Kalshi spread, quote age)
  against a 2 h direction label; they cannot form a 10-minute innovation or event, and E009's own result (which `xvenue` mirrors) is
  known at LT10's pin anyway (*informed (E009)*). Extending it would hide `se4` and `se13` for another month for no LT10 protection.
- **Second read root for `xvenue` (only under D-LT10-1 route 1):** `XV_QUOTES_ROOT` reads `cross_venue_live/quotes/` and
  `xv_quotes/quotes/` (the same schema; the successor's lines carry `src`). An engine-track change; it changes no column definition.
- **Not requested:** `steam` (5.2), `xvenue2` (round 15 CANDIDATES row 4, under `xvenue`), `surprise`, `movetype`.
- If every LT10 test drops at its census, `kxbook` and `attrlimit_lt10` are withdrawn with a ledger line (the withdrawn entry keeps
  its record, as `config.EMBARGO`'s comment requires).

The engine's yardstick (log-loss gain under `se-promotion-v2`) is a different question from each LT10 primary. A Supported LT10
primary makes its columns a candidate; an engine gain never changes an LT10 verdict and an LT10 verdict never promotes a model.

## 10. Disclosures

- **Selection history.** The three tests are round 15's ranks 1-3 (creative-lead pass written 2026-10-23 on `66bbc2fd`, from the
  ledger, `CROSS_VENUE_LIVE.md`, the engine status and named documents, with no host probe), taken in the round's own
  recommendation. Every design change (6.1) was made before any data.
- **The designer** read, on 2026-10-23: `CLAUDE.md`, `AGENTS.md`; `CREATIVE_HYPOTHESES_2026-10-29.md` (sections 0, 0.1, 0.2, 1, 2.A
  and 3, and the section headings); `LIVE_TESTS_9.md` (sections 0, 1.0-1.12, 2, 6-13) and `LIVE_TESTS_8.md` (headings, 5); the
  ledger by bounded read (the E009 and E010 entries, the 10-14 host-move deviation, the 10-13 gaps entry, line hits for the 10-22
  resize record and CB16-K's heading); `CROSS_VENUE_LIVE.md` (whole, 108 lines); `cross_venue_live.py` (constants, `parse_*`,
  `two_sided_mid`, `features`, `make_prediction`, `select_live_pairs`, `refresh_pairs`, `Poller.load_pairs` to `cycle`,
  `gzip_old_quotes`); `cross_venue.py` (two constants by grep); `COLLECTION_HOST.md` (layout, jobs, the supervisor's cap rule,
  the rotation notes); `scripts/oracle/archive_retention.json` (rules) and `crontab.txt` (the archive-active line);
  `LIVE_TESTS_READINESS_2026-10-19.md` (two line hits: the 228 MB predictions file and risk R3); `data_catalogue/RETENTION.md` (one
  line hit); `signal_engine/config.py` (`XV_QUOTES_ROOT`, the `EMBARGO` tokens); `signal_engine/features.py` (the `xvenue` reader's
  signature and docstring); `signal_engine/CANDIDATES.md` and `STATUS.md` (bounded grep: `xvenue`, `kxbook`, Kalshi);
  `ext_sidecar.py` (key list); `cb17_census.is_sports_sidecar`; the sha256 of `cross_venue_live.py`, `cross_venue.py` and the hand
  verdicts file in the worktree; the queue-id and seed history across all refs. **Known to the designer before drafting:** the E009
  pilot's operational counts as the ledger quotes them (about 70 pairs / 22 events with complete features, 27 events after the
  refresh, `dk1` non-zero on 12% of origins, |dk1| median 0, 90th percentile 0.5c, 99th 2c, median Polymarket spread 1c, 0 trade-rule
  firings, 96% of pair-polls two-sided on both venues); the engine's 116 pairs (`xvenue` 0.25% of 46,448 eligible rows); the readiness
  audit's 425 MB and 60 MB a day. **Not read:** any quote, pair, prediction, outcome or analysis file of E009 or E010, any
  `--ops-stats` output, any census output, any data, host, outcome, price after an origin, P&L, `data-dumps` file or evidence JSON.
  No threshold was chosen from data.
- **`informed (E009, E010)` is unavoidable and declared.** LT10 registers after both analyses. The freeze before `T_E009` and the
  rule that registration does not depend on their verdicts are the protections (1.1); the census values are rule-fixed, not chosen.
- **The census reads E009's registered window.** Its span `[10-21, 10-31)` lies inside E009's and E010's windows; it runs only after
  E010's analysis commit, reads origin-side fields and Kalshi-only twins, and opens no prediction or outcome file (1.6). The window's
  data are disjoint from E009's.
- **The round's figures are not LT10's.** CH224's 0.25c / 0.19c became 0.30c / 0.23c (pairs after the category filter 60 / 100, the
  valid share 0.85, `OF` 1.1); CH223's 0.33c / 0.18c became 0.47c / 0.26c (the purity retention 0.8, the pairs); CH222's 0.47c /
  0.36c became 0.63c / 0.44c (the pairs, the move shares 10% / 12% at the new threshold, the ambiguous class, `OF`). The prior odds
  of section 0 are the designer's (CF10 0.40; CH224 0.60, CH223 0.45, CH222 0.30 given CF10; the round's 0.45, 0.35, 0.30 had no
  family gate).
- **F can reject a true but persistent signal, and a reverse lead** (CH224, where F binds by design); accepted (LT7-LT9 10).
- **Spread censoring.** E009's 10c two-sided rule removes the largest widenings from CH223 and CH224 (1.4 item 9).
- **Mismatched pairs.** Title-level matching; about 2% of historical matches were wrong and live pairs without a hand verdict may
  include mismatches, which bias every LT10 contrast towards 0 (E009 non-claims); the hand-verified refit is a label.
- **Retention dependency.** The census needs a byte-identical restore of the earliest sidecars (about five) (snapshot retention 10 days); the quote
  and pair files have no retention rule; no LT10 rule deletes anything.
- **Shared data.** The engine reads the same quote stream; LT10's window overlaps E022, E026 and the analyses of E011, LT2 and E015
  in time only.
- **Window.** Results arrive about 2026-12-02, after E009, E010, E011, LT2, E015 and E022 and before E026's analysis; the reasons for
  the start date are in 1.1.

### 10.1 Values declared now and their planning sources (all before any census)

| Value | Where | Source |
|---|---|---|
| Pairs in the primary population 60 / 100 | 2-4 | E009's pilot (about 70 with complete features) and the engine's 10-20 count (116), each x a declared non-sports ex-crypto share 0.85 (unprobed) |
| Valid-origin share 0.85 | 2-4 | E009's pilot (96% two-sided pair-polls) less features, window, `rv60`, late and target losses; a convention |
| Kalshi-move share 10% / 12%; quiet share 0.88 | 3, 4 | E009's pilot (`dk1` non-zero on 12% of origins); 10% a convention |
| Withdrawal share 3% / 6%; purity retention 0.8 | 3 | round 15 CH223 (unprobed); 0.8 a convention |
| Traded share 0.40; quote-only 0.55; ambiguous 0.05 | 4 | round 15 CH222 (unprobed); 0.05 a convention |
| SDs: `dsP` 1.0c, `a` 0.5c, `c` 0.7c | 2-4 | round 15 0.2 (planning; unprobed); the census reads no target, so they stay planning values |
| DE 51; census `DE_gate = max(51, 1 + (m_w - 1) x 0.0016667)` | 0, 7 | round 15 rule 13; 6.1 item 11 |
| `VIF_w` 1.5; gap 2.2 SD; `OF` 1.1 (planning `rho_x1` 0.1) | 2-4 | round 14 / 15 conventions; 6.1 item 1 |
| `n_eff` share 0.8 | 2-4 | round 14's planning convention |
| F planning `r` 0.1 (CH224, CH222), 0.2 (CH223) | 2-4 | round 15 |
| Floors 1.0c (spread), 0.5c (magnitude, 20-minute mid) | 1.9 | round 15 rule 14 |
| Count gates: CH224 31,000 units (the F-MDE kill line, rounded up); CH223 2,920 withdrawals and 50,000 quiet units; CH222 9,650 traded and 9,650 quote-only | 7 | the counts at which each MDE (CH224: F-MDE) gate passes at the planning class ratios; gross projected counts, no 0.8 (LT9 7) |
| CF10: >= 60 pairs, >= 30 events | 7 | round 15 (CB15-P's gate, adopted) |
| CK10 CH224 gates (10%; 5% in >= 50% of pairs with >= 500 units; >= 30 pairs; each sign >= 25%) | 7 | round 15's 10% kill line; the rest conventions replacing the round's SD gate (6.1 item 5) |
| CK10 CH223 gates ([1%, 15%]; AR < 0.5; minute-of-hour share <= 50%) | 7 | round 15 CH223; the minute-of-hour gate a convention for S21 |
| CK10 CH222 gates ([15%, 85%]; SD >= 0.2; ambiguous <= 25%) | 7 | round 15 CH222; 25% a convention |
| Venue-clock gate <= 50% in one UTC hour | 7 | round 13 rule 8 |
| Event exclusion > 40% | 1.4, 7 | LT9's series-family rule, applied to events |
| Late rule t + 1,080 s; reader every 5 minutes | 1.3, 8.2 | E009's +-120 s endpoint tolerance; a convention |
| World parameters (1.8.1) | 1.8.1 | conventions, not measurements |
| Seeds 20261301-03, 20261391-93, 20261397 | 2-4, 1.8 | new (unused in docs and code across all refs on 2026-10-23) |
| Census span 2026-10-21..10-31 | 7 | 6.1 item 10 |
| Window 2026-11-10..12-01; staleness stop 2026-11-30 | 1.1 | 1.1's reasons; the stop a convention |

## 11. What the challenger (science-reviewer R1) should attack

1. **Independence from E009/E010.** Is a freeze before `T_E009`, a census on E009's window after both analyses (origin-side only,
   Kalshi-only twins), and "registration does not depend on their verdicts" enough? Should the census instead wait for post-11-03
   data from the continued stream (no E009-era read at all, at the cost of a start about 11-17 and a census on a five-day-old
   successor)?
2. **CH222's threshold change** (6.1 item 2) from `|dk1| >= 1c` to `>= 0.5c`, justified by the ledger's pilot quantiles: a design
   choice informed by E009-era counts, or a correction of the round's arithmetic?
3. **The purity rules** (6.1 item 3): is `k_vol24` (a rolling 24 h volume whose update latency is unprobed) a sound trade screen, and
   is `vol_unknown` as a flag rather than an exclusion right?
4. **F roles.** CH224 binding; CH223 and CH222 labels with binding leak worlds 7 and 5. Should CH223's F bind (its |move| target and
   volatility clustering), accepting a likely census death at the low planning end (F-MDE 0.75c)?
5. **Overlap handling** (6.1 item 1): all 144 origins with `OF`, the MA(1) design covariance and the block gate, against E009's
   non-overlapping 72. Is `OF = 1 + rho_x1` (from adjacent-target correlation 0.5) a sound planning inflation?
6. **`DE_gate` for the fine clock** (6.1 item 11): the 0.0016667 ICC scaling and the floor 51.
7. **CH224's identification gate** (6.1 item 5) replacing the round's SD gate; the pooled scale (item 4); the one-tick floors.
8. **CH223's withdrawal definition:** endpoints only (a withdrawal that is re-posted within the window is missed); 2c widening and
   50% size fall; the autocorrelation and minute-of-hour gates for bot refreshes.
9. **Collection (8.2):** route 1 (a successor in a new directory, the engine's second root) against route 2; whether the burn-in
   acceptance is enough to call the window's stream the census's stream.
10. **Window and timing (1.1):** 2026-11-10 as the earliest start; the staleness stop; Thanksgiving.
11. **Arithmetic:** every MDE and kill line in sections 0 and 2-4 (recomputable from 10.1).

## 12. Open questions for the challenger review

1. Should CH224's primary be restricted to units with Polymarket's spread above one tick (room to tighten), with the full population
   as a sensitivity, rather than the reverse?
2. CH223: is `|mP(t + 20) - mP(t)|` the right primary, or Polymarket's own spread change (M2), which is what a maker who "follows"
   would show?
3. CH222: is +20 minutes right for a traded/quote-only split, or should +10 minutes (the round's alternative alignment, E009's 10-min
   secondary) be primary?
4. Should the family gate require >= 30 events on a daily-average basis rather than distinct events over the census days?
5. The default scope: with sports excluded the family may die at CF10; is the with-sports CF10 print (uncounted) the right input for
   the owner's decision, or should LT10 wait for that decision?
6. The hand-verified pairs only as the primary (cleaner matches, fewer events) or as a label (as drafted)?
7. Hour dummies (23) as controls in every primary: enough for the venue clocks, or should strata be pair x UTC day x hour block?
8. Multiplier 3.47 kept for k <= 3.

## 13. Draft ledger block (DRAFT, not registered, not counted)

> ## LT10 (the fine-clock family: CH224, CH223, CH222) — DRAFT pre-registration (not registered, nothing counted, no code)
> - **Design:** `docs/research_lab/LIVE_TESTS_10.md` on `feat/live-tests-10`. Pure reader of E009's fine-clock quote stream (Kalshi
>   and Polymarket CLOB touch every 120 s for up to 200 matched pairs) and its continuation; separate store `live_tests10/`; E009's
>   feature and validity code vendored by hash (`cross_venue_live.py` `eac14e68…`). Label `informed (E009, E010)`.
> - **CH224** the hedged maker's price: Polymarket's 20-minute spread change on Kalshi's 10-minute spread innovation, levels and
>   Polymarket's own change held fixed; slope MDE 0.30c / 0.23c (floor 1.0c); F binding (0.45c / 0.35c).
> - **CH223** the other venue's makers flinch first: Polymarket's next 20-minute |move| after a Kalshi withdrawal (>= 2c widening or a
>   >= 50% touch-size fall) with no Kalshi mid move and no trade; MDE 0.47c / 0.26c (floor 0.5c; needs about 2,913 withdrawals);
>   F a label; binding volatility-leak world.
> - **CH222** the venue that traded first: Polymarket's 20-minute move in Kalshi's direction after a traded against a quote-only
>   Kalshi move (`|dk1| >= 0.5c`); MDE 0.63c / 0.44c (floor 0.5c; needs about 9,650 traded moves); F a label; binding activity-leak
>   world.
> - **Family:** Holm over k <= 3, one-sided, alpha 0.05; block FL gates (pair x day; CH222 pair x two-day block); 9 size scenarios
>   (S19-S22, two leak worlds, one mechanical world); window proposed `[2026-11-10T00:00Z, 2026-12-01T00:00Z)`, single analysis on
>   or after 2026-12-02T12:00Z; freeze before 2026-11-03T02:00Z and `T_E009` or not registered; census after E010's analysis commit
>   on a seal of `[2026-10-21, 2026-10-31)` (q0660-q0664; family gate >= 60 pairs in >= 30 events first); registration independent
>   of E009's and E010's verdicts; not registered if the start would fall after 2026-11-30.
> - **Collection decision D-LT10-1 (orchestrator):** the poller's 2 GiB cap is projected to stop it about 2026-11-16; recommended a
>   quotes-only successor in `xv_quotes/` at E010's analysis commit (no new external service), with a five-day burn-in.
> - **Embargo:** new `kxbook` and `attrlimit_lt10` to the later of 2026-12-04 and LT10's analysis commit, filed before 2026-11-04;
>   `xvenue` not extended. **E-numbers not assigned.**
