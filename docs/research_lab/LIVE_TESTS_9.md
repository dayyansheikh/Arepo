# Live tests 9 (LT9): three round-14 candidates (CH213, CH214, CH212) and an optional fourth (CH215), DRAFT pre-registrations

**Status: DRAFT, NOT FROZEN. No challenger review yet, not registered, nothing counted, no code, no seal, no census run.**
Drafted 2026-10-22 on branch `feat/live-tests-9` from the `chore/arepo-claude-setup` tip `9079ca39`, a design-only first
commit like the first commits of LT3-LT8. E-numbers are **not** assigned here: LT9 takes the next free numbers at its own
registration, after whatever LT7 and LT8 register (provisionally in the order CH213, CH214, CH212, then CH215 if it enters).
If every test drops at its census, LT9 is not registered (recorded in the ledger; nothing counted). Before registration
this needs, in order:
1. a challenger review (`science-reviewer`, R1) of this file, the response, and any re-check;
2. the **design-text freeze commit** (section 1.1) before the earlier of **2026-11-14T12:00Z** and `T_E015`;
3. the code (section 8), with a freeze check of the census and size-check code against sections 1.8, 1.8.1 and 7;
4. the census input restore and seal (section 7), each once, after the freeze and after the census span has ended;
5. the counts-only censuses (section 7), each once, which fix k, CH215's entry and every census-fixed spec value;
6. the size check at >= 2,000 worlds on the code to be pinned, through the census-fixed strata (section 1.8);
7. a host dry run with peak RSS measured (section 8.2);
8. **LT8's registration commit (or its recorded drop)**, the `SPEC_SHA256` and `code_sha256` pins, the ledger entry, all
   **before `T_LT7`**, and the reader's installation (section 8.4). The engine embargo requests of section 9 are filed at
   design acceptance and in any case before 2026-12-23T00:00Z; they are not a registration step.
Until the pin exists, every line a reader writes is `prospective_unregistered` by construction.

This is research tooling. AREPO never trades. No edge, calibration, profitability or tradability claim exists or is implied.
Every count quoted from the round-14 file, the LT7 reward probes and rulings, LT8 or the cost model is a **counts-only
development figure on worn data**. Every MDE here is a **planning estimate** built on stated assumptions, not a
measurement. Nothing here read a price after an origin, an outcome, a target, a census output or a P&L. No host, network,
`ssh`, `data-dumps` or evidence-JSON read was used to write it (the reads are listed in section 10).

Source ideas: `CREATIVE_HYPOTHESES_2026-10-28.md` (round 14) section 3, ranks 1-3: **CH213** (the band break), **CH214** (the
pool splits) and **CH212** (the display's omission and the two ledgers), taken in the round's own recommendation ("if the LT9
designer wants k = 3 ... CH213, CH214 and CH212 ... CH215 is added only on its count"). Rank 4 (**CH215**, the scheduled end)
is written in full here as an **optional fourth** whose entry is decided by its own census counts alone (section 5); ranks
5-10 are not taken (6.2). The design is written to round 14's rules (its section 0.2), to LT4's lessons L1-L15, to LT7's R1,
re-check and reward rulings 13.6 and 13.7 (with its erratum), and to LT8's R1, re-check and census-code-check rulings. Every
design change from the round's sketches is listed with its reason in 6.1; all were made before any data.

## 0. Summary

| Handle | Idea | Hypothesis (direction) | Population | Primary | Planning MDE (DE 31, multiplier 3.47): low / high; at a quarter of the low count; F-MDE | Floor |
|---|---|---|---|---|---|---|
| **CH213** | the band break | Within market, the Gamma spread change over (k, k + 1] after a **strict break** (`s_{k-1} < 2v <= s_k`: no displayed touch scores) is more negative on the reward panel than after the same crossing on the control panel, where the band is assigned by a declared cell rule (one-sided, sign-adjusted > 0) | non-sports ex-crypto eligible markets, mid in [0.10, 0.90], events <= 10 members: reward panel (`rewarded = 1` under `listed_carry24h_v2`) plus control panel (`rewarded = 0`) | expanding-past demeaned OLS of `ds = s_{k+1} - s_k` on `break x rewarded` with `break` and its liquidity, tick and level interactions as controls; **block Freedman-Lane gate** | interaction **1.39c / 0.62c** (DE 51: 1.78c / 0.80c); quarter 2.77c; F 2.06c / 0.93c (F binding only if the census F-MDE <= 1.0c); passes 1.0c only with **>= about 68 strict reward-panel breaks a capture** (and as many control breaks) | 1.0c (spread) |
| **CH214** | the pool splits | Within market, the CLOB spread change from sweep 1 of pass k to sweep 1 of pass k + 1 falls with the **symmetric in-band depth innovation** between the sweeps of passes k - 2 and k - 1 behind an unmoved touch, the depth level held fixed (one-sided, sign-adjusted > 0) | reward-panel (`listed_carry24h_v2`) non-sports ex-crypto books, mid in [0.10, 0.90], events <= 10 members, quiet touch, unchanged band | expanding-past demeaned OLS of `dsw = sws_{k+1} - sws_k` on `zdD`, `log D_{k-1}` and `z dimb5` controls; **block Freedman-Lane gate**; **far-future innovation F binding** | slope **0.28c / 0.19c** (DE 51: 0.36c / 0.25c); quarter 0.56c; F 0.40c (r 0) to 0.47c (r 0.3) / 0.27-0.33c | 1.0c (spread) |
| **CH212** | the display's omission | Within market, on reward-panel rows the CLOB feed confirms, the next Gamma |mid move| over (k, k + 1] is larger when Gamma served row k **without** `clob_rewards` (a carried unit: carry lag >= 1) than when it served the field (route A, one-sided > 0); route B (real churn) as declared, chosen by counts | non-sports ex-crypto eligible reward-panel markets (`listed_carry24h_v2`), mid in [0.05, 0.95], events <= 10 members | expanding-past demeaned OLS of `a = |mid_{k+1} - mid_k|` on `om_k` with 11 slot-of-day dummies and activity controls; **block Freedman-Lane gate**; the route fixed by the census's declared count rule | route A **0.58c / 0.35c** (DE 51: 0.74c / 0.45c); quarter 1.15c; F 0.86c / 0.52c (reported unless the census F-MDE <= 0.5c); passes 0.5c only with **>= about 240 route-A omitted units a capture**; route B 0.61c / 0.31c (floor 1.0c) | 0.5c (A), 1.0c (B) |
| *CH215 (optional)* | the scheduled end | The Gamma spread over the 24 h before a CLOB programme's scheduled end, known >= 48 h ahead and > 48 h before the market's own end, widens against the 24-48 h before it, net of matched controls (one-sided > 0) | programme ends on non-sports ex-crypto markets | event-clustered mean of treated-minus-control before-after differences; sign-flip gate by event | 2.23c (n_eff 170) / 0.92c (n_eff 1,000); F reported; passes 1.0c only with **>= about 51 qualifying ends a day** | 1.0c |

- **Family:** one Holm family over the k surviving primaries, one-sided, familywise alpha 0.05, separate from E009-E011, LT2
  (E012-E014), LT3 (E015), LT4 (E022), LT5, LT6, LT7, LT8, E025 and E026. **Provisional k <= 3; k <= 4 only if CH215 enters
  by its own census rule (section 5).** A test whose census gate fails is dropped *before* registration, uncounted; k is the
  number that survive, fixed in the spec (`k_tests`) at registration and never changed. A primary that is unavailable or
  fails its gate enters Holm with p = 1. No replacement test is added after a census drop.
- **Window (proposed; the ordered lane, 1.1):** whole captures with start in `[REGISTERED_UTC, END_UTC)`, 21 days,
  `REGISTERED_UTC = 2027-01-21T00:00:00Z`, `END_UTC = 2027-02-11T00:00:00Z`; single analysis on or after
  **2027-02-12T12:00:00Z**. Keyed to LT8's `END_UTC` (proposed 2027-01-20T00:00Z) plus 24 h, never earlier than
  2027-01-21T00:00Z while LT8 is registered, and sliding later with LT8. The round's fast lane (2026-11-17..12-08) is
  declined (1.1).
- **Pin early, run late.** Design-text freeze before the earlier of 2026-11-14T12:00Z and `T_E015` (planned by 2026-11-10),
  so that it precedes E015's, E022's, LT7's and LT8's analyses; the registration pin before `T_LT7` or every LT9 test is
  dropped (1.1).
- **Expected outcome, declared now (honest prior odds; the designer's judgement, not measurements).** **CH213** depends on an
  unprobed count: the strict-break share must give about 68 reward-panel breaks a capture after the mid band and the cap; the
  low planning end gives 35; its binding liquidity-leak world 3 may fail. Census **0.35**; valid verdict **about 0.15**.
  **CH214** has power to spare; its risks are the static-farmer identification gate and the binding fill-leak world 8 (the
  same-signed confounder that is expected to remove LT8's CH203 as well). Census **0.35**; valid verdict **about 0.10**.
  **CH212** is decided by its route rule from counts; the challenger's own reading (field-level flakiness) predicts
  "neither", which drops it; if it survives, its binding activity-leak world 11 may fail. Census **0.30**; valid verdict
  **about 0.15**. **CH215** enters with odds about **0.10**. **Expected k at census about 1.0 (0 to 2); the chance that
  CH213, CH214 and CH212 all drop is about 0.30** (0.65 x 0.65 x 0.70, treating the fates as independent, which they are
  not; the three share the reward panel); **the expected number of valid verdicts is about 0.4.** Every taker check is
  expected to be "not shown" (1.10).

## 1. Common rules

### 1.0 Lessons carried over (binding from the first draft)

LT4's lessons **L1-L15** (`LIVE_TESTS_4.md` 1.0), LT7's table of later rulings (`LIVE_TESTS_7.md` 1.0) and LT8's 1.0 list
apply unchanged: exact `%.17g` writes and round-trip reads; NaN refusals in a pinned spec; sealed census inputs re-hashed
(refuse on mismatch); slots and origins built **from the seal**, never from a local scan (LT8 census-code check fix 1); a
pessimistic planning-MDE gate in every census with `max(declared, design)` and `sqrt(max(1, VIF_w))`; a simulated size check
at >= 2,000 worlds with the limit 0.05 + 1.645 sqrt(0.0475 / worlds) = 0.058; dry-run guards; spec and code pins on every
frozen line; write-once per-capture series and status files; clustering by event, event x UTC day and UTC day with p the
largest; Holm over k counted once; economics never changes a verdict; readers at the pass cadence; an internal run lock;
residual-IQR identification gates; Freedman-Lane gates only with `DE_gate = max(floor, 1 + (m_21 - 1) x 0.02)`; the block
(circular-shift) gate for rolling or persistent states; the liquidity-tier gate; seal completeness and the seal's own slot
assignment; memory planned from a measurement with a ladder; `T_X` keyed conditions; the pinned crypto classifier; the
design-text freeze; the lag-slot loader; vendoring, not import; the F rule; `r_gate = max(r_w, r_pool)`; count gates on
**pre-exclusion** counts where stated and zero-filled correlations refused (LT8 census-code check); the null taxonomy of
`clob_rewards` (unset / empty list / zero / malformed / no sidecar; LT8 census-code check fix 7).

**Census deaths that set LT9's expectations (counts only; round 14 0.1).** Since LT4: E020 and E021 (strata), LT5 F (MDE at
`DE_gate` 10.3), H, R (crossing share 0.21, design MDE 1.03c), J, O, LT6 D, B, V (one correlation gate, 0.595), K, the CB13,
CB14, CB15 and CB18 pre-gates; E022 alone survived (coverage 0.9996, residual-IQR share 0.827, block2 strata 0.599, DE
6.196). The lessons applied here: (i) the MDE gate, not the count gate, kills, so every test states **the count at which its
MDE gate passes** (section 0); (ii) a rare state empties the market x day stratum, so CH213's and CH212's states are
per-interval events on every capture of a reward-panel market and CH214's is continuous; (iii) whole-panel populations have
whole-panel design effects (planning DE 31 with a <= 10-member cap, 51 without); (iv) a field's semantics are declared
before any count: **every LT9 reward status follows LT7 13.7's `listed_carry24h_v2`** (1.4.1).

Round 14's design rules (`CREATIVE_HYPOTHESES_2026-10-28.md` 0.2) map onto LT9 as follows:

| Round-14 rule | LT9 rule |
|---|---|
| 1. Panel-complete units | every unit is a market x capture (or, CH214, a market x pass) on the complete captures, their sidecar, sweep 1 of the pass and the `reward_params` feed; no trade-sample, monitor or external frame unit |
| 2. Dense states | CH213's break and CH212's omission are per-interval labels read on every capture of a reward-panel market; CH214's innovation is continuous on every quiet book |
| 3. Innovations and crossings, never levels | CH213 a crossing, CH212 a switch of the field's presence, CH214 an innovation; the levels (`s_k`, `log D_{k-1}`) are controls |
| 4. Look-backs <= 12 slots | the carry window is exactly 12 slots (`[k-11, k]`); the longest state look-back is CH214's sweep of pass k - 2; `rv24*` reads 12 slots |
| 5. Field semantics declared first | `listed_carry24h_v2` for every reward status; CH212 reads the same rule's carry lag as its event (1.4.1); the null taxonomy is LT8's |
| 6. A stream only where it covers its population | `reward_params` (every CLOB-rewarded market) is the adjudicator for CH212 and a sensitivity elsewhere; the monitor is not used |
| 7. DE and the kill line | DE 31 (cap) / 51 (uncapped) for all three; each kill line is the count at which the MDE gate passes (0) |
| 8. Floors | 1.0c for spread targets (CH213, CH214, CH212 route B, CH215), 0.5c for CH212 route A's magnitude; the F-MDE cap equals the floor |
| 9. Census on a fresh seal | a fresh 10-day seal of the four 2 h streams on winter time (section 7) |
| 10. Pin early, name what was seen | the q0601b / q0601c counts and the 13.6 / 13.7 rulings are disclosed in every test (10) |
| 11. Maker-side money routes | every primary route is maker-side, gross, no fills; taker cells reported (1.10) |

### 1.1 Registration, window, single analysis
- `REGISTERED_UTC` is the first 00:00Z that is **(a)** at least 24 h after the LT9 registration commit (spec pin plus ledger
  entry), **(b)** at least 24 h after **LT8's own `END_UTC`** if LT8 is registered, **(c)** never earlier than
  **2027-01-21T00:00Z** while LT8 is registered. LT9 registers only after LT8's registration commit, or its recorded drop
  (all of its tests dropped at census or the family abandoned, in the ledger). **If LT8 drops entirely** (recorded), (b) and
  (c) lapse and are replaced by **(c')**: at least 24 h after LT7's `END_UTC` if LT7 is registered, and never earlier than
  **2026-12-30T00:00Z** (LT9 then takes LT8's proposed slot; round 14's rule, declared now, uses no data). The proposed value
  is **2027-01-21T00:00Z**; `END_UTC = REGISTERED_UTC + 21 d` = 2027-02-11T00:00Z; analysis date `END_UTC + 36 h` =
  2027-02-12T12:00Z. **The family slides later if LT8 slides**; a move is recorded in the ledger.
- **Why 24 h after LT8's end is enough (and what is shared).** LT8's last inputs are CH203's lag sweeps k + 5 and k + 6 and
  its 24 h secondary S1 of its last origin (2027-01-19T22:31Z), ending with the 2027-01-20T22:31Z capture. Every LT9 state
  input (captures k - 1 and k; CH214's sweeps of passes k - 2 and k - 1) is a capture or sweep at or after `REGISTERED_UTC`
  (boundary below), so no LT9 state, control or target is an LT8 primary or F input. **Disclosed:** the 12-slot carry window and `rv24*` of LT9's
  first-day units read raw captures of 2027-01-20, which are LT8 target and S1 inputs (as LT8's look-back read LT7's last
  week); no LT8 store is opened.
- **Boundary (LT7 R1 must-fix 8's form, as LT8).** CH213's and CH212's first origin is the first capture whose capture k - 1
  starts at or after `REGISTERED_UTC` (proposed 2027-01-21T02:31Z: their states read captures k - 1 and k); the 00:31Z capture
  gives no unit and is counted `lt8_boundary`. The 12-slot carry window and `rv24*` are look-backs, not states of the prior
  window (a carry source before `REGISTERED_UTC` is allowed and counted `pre_window_source`). **CH214's first unit** is the first whose pass k - 2 sweep
  starts at or after `REGISTERED_UTC` (proposed: sweeps of the 00:31Z and 02:31Z passes, decision after the 02:31Z pass sweep,
  target sweeps of the 04:31Z and 06:31Z passes); earlier ones give no unit and are counted `lt8_boundary`. CH215's first end
  is the first whose 48 h pre-end span starts at or after `REGISTERED_UTC`.
- **Design-text freeze.** After the challenger's acceptance (R1 and any re-check), a commit records the sha256 of this file in
  the ledger. From then on, the text of a test changes only by census-fixed values named in section 7 and by code-freeze-
  check fixes that change no state, unit, target, estimator, gate, threshold or verdict rule. **The freeze must exist before
  the earlier of 2026-11-14T12:00Z and `T_E015`** (planned by 2026-11-10). `T_X` = the earlier of X's analysis job start
  (queue log) and X's analysis commit. Adjacent analyses and the consequence if the freeze (or a later text change, or the
  pin where stated) is not before them:

  | Test | Adjacent analysis (`T_X`) | Why adjacent | Consequence |
  |---|---|---|---|
  | CH212, CH213, CH214 | **E022** (`T_E022`, proposed 2026-11-17T12Z) | E022's S2 splits hollow liquidity by reward status on the same `clob_rewards` field (k-only); E022 reads sweep depth on movers (CH214 reads depth on quiet reward-panel books) | freeze not before `T_E022`: label *informed (E022)* on all three |
  | CH213 | **E015** (`T_E015`, proposed 2026-11-15T12Z) | E015's anatomy (one-sided, quote-only) is a CH213 control | freeze not before `T_E015`: label *informed (E015)* (the freeze deadline makes this moot by construction) |
  | CH212, CH213, CH214 | **LT7** (`T_LT7`, proposed 2026-12-30T12Z) | CH197 (behind-touch depth with `in_band`) and CH192 (spread state) use the carry rule on the same field; LT7 reports the v1 / v2 reward sensitivities, which bear on CH212's object | **registration (pin) not before `T_LT7`: every LT9 test dropped** |
  | CH214 | **LT8** (`T_LT8`, proposed 2027-01-21T12Z) | CH203 reads the asymmetric part of the same two-sweep innovation | registration is before `T_LT8` by construction (it is before `T_LT7`) |
  | CH215 | E014 (`tte`; complete) and LT8's CH206 map (q0627, counts only) | time-to-end; programme starts on the same feed | none (disclosed in 10) |

- **The fast lane, declined (declared now).** Round 14 proposed a fast lane (window 2026-11-17..12-08, freeze before
  11-14T12Z, census on a 10-24..11-02 seal). It is not used: (1) the brief for LT9 is to run after LT8 unless a stated reason
  allows parallel running, and none is strong enough; (2) its census span straddles both daylight-saving changes (UK
  2026-10-25, US 11-01), which LT8's disclosure warns against; (3) its results (about 12-09) would arrive before LT8's pin and
  during LT7's window, so CH214's result on the symmetric half of CH203's two-sweep innovation, and CH212's on the carry rule's
  object, would inform LT8's registration and LT7's reading of its own carry sensitivity; (4) it would compress code, seal,
  census, size check and dry run into three weeks while LT7's and LT8's code phases use the same host. The cost is about two
  months of delay; disclosed.
- **Why the window starts after LT8.** (1) CH214 shares CH203's sweeps and quiet-book shape; an LT9 unit after LT8's last
  input shares no state, control or target with LT8. (2) Host reader slots: LT8's reader stops as LT9's starts (8.2). (3) LT9
  can be frozen in November and pinned in December, before LT7's analysis.
- **Time of year (disclosed).** The window (2027-01-21..02-11) is on winter time like the census span (2026-11-02..11-12), so
  LT8's daylight-saving disclosure does not recur. It holds no major US or UK holiday; the 2027 Super Bowl falls after it.
  Venue reward programmes may be re-rated at month starts (2027-02-01 is in the window): a counts-only weekly line
  (`ops-stats`) records the reward-panel size, never a look; a sensitivity without origins in `[2027-02-01T00:00Z,
  2027-02-02T00:00Z)` is reported and never changes a verdict.
- **Fixed end, no extension** (LT4-LT8 practice). Shortfalls are labelled (*underpowered*, Unavailable), never extended.
- **One analysis**, once, on or after the analysis date (`run_live_tests9.py analyze` refuses before it; `--out` refuses to
  overwrite). No interim look at any outcome (1.6). **Effective start** = max(`REGISTERED_UTC`, the first capture processed by
  the reader at the pinned commit); the analysis keeps only lines whose `spec_sha` and `code_sha` equal the pins and whose role
  is `prospective_confirmation`.

### 1.2 Streams read (all already written by the host's pass and its existing collectors; nothing new is fetched; no new collector)
- **Complete-universe captures** `snapshots/<id>/rows.csv.gz` (every 2 h at :31; `state=complete` only): `bid`, `ask`,
  `spread`, `last_trade_price`, `volume24hr`, `liquidity`, `chg_1h`, `end_date`, `event_id`, `neg_risk`, `closed`, `active`,
  `received_utc`, and the manifest's capture start time.
- **Sidecar** `rows_ext.csv.gz` (`ext_sidecar.py`): `received_utc`, `page_index`, `fee_type`, `fee_category`, `series_slugs`,
  `order_price_min_tick_size`, `order_min_size`, `rewards_min_size`, `rewards_max_spread`, `clob_rewards`, `volume_num`,
  `competitive`, `accepting_orders`. A missing sidecar row sets sports and crypto unknown and the reward status NaN
  (excluded, counted `sidecar_missing`).
- **Book sweep 1** `book_sweeps/<id>/` (`series_index` 0): outcome-0 `best_bid`, `best_ask`, `bid_size_1`, `ask_size_1`,
  `depth_*_1c`, `depth_*_5c`, `n_bid_levels`, `n_ask_levels`, `tick_size`, `book_timestamp`, `batch_receipt_utc`
  (`book_sweep.parse_book`: `depth_bid_1c` / `_5c` sum all bid levels with price >= best bid - 0.01 / 0.05, touch included).
  CH214 reads passes k - 2 and k - 1 (states), k and k + 1 (targets), k + 2 and k + 3 (sizes-only F state); CH213 and CH212
  read passes k and k + 1 only for post-decision mechanism readings (1.3). Sweep 1, not `book0`'s sweep (LT8 6.1 item 2).
- **CLOB reward feed** `reward_params/<capture_id>/` (`reward_params_collector.py`, cron `35 */2`, since
  2026-10-20T23:20Z; no retention rule covers it): `rows.jsonl.gz` (the native and sponsored records as served: `condition_id`,
  `rewards_config` with `rate_per_day`, start and end dates, `rewards_max_spread`, `rewards_min_size`, sponsored rates) and
  `manifest.json` (state, timings). A capture is usable only if `state=complete`; the **last usable feed capture before a
  decision time** is the latest whose manifest finish time is earlier than it. Field names are confirmed by the header
  pre-check (7); a missing field makes the dependent quantity NaN.
- **Not read:** trade samples, the live large-trade monitor, `cross_venue_live/`, `surprise_live/`, the stores
  `live_tests2/` .. `live_tests8/`, CB8-H holders, the CB16-CB18, E025 and E026 stores, the keyless streams (PredictIt,
  Smarkets, ESPN odds, `gamma_rules`), the signal engine's `quotes/`, `features/`, `aux/` (including `book0`) and
  `predictions/`, and Gamma outcome fields of any kind.

### 1.3 Clocks, slots and decision times
- **Slots:** as LT3-LT8 (`grid0 = 2026-10-01T00:31Z`, 2 h, tolerance 30 min, first complete capture of a slot). "k - j" and
  "k + h" are slots, not file order. A missing slot leaves every quantity that needs it NaN (counted), never interpolated.
  Slot of day `sigma(i) = i mod 12`. Pass j's sweep 1 is the sweep with `series_index` 0 whose batch starts in slot j.
- **Decision time per test** (the latest input's own receipt; states use that input and strictly earlier ones only):
  - **CH213, CH212:** capture k's row `received_utc`. States read captures k - 1 and k, their sidecars and the carry window
    `[k-11, k]`; CH212's CLOB flag reads the last usable feed capture before capture k's start (in practice the one at slot
    k - 1's :35). **Targets start at capture k + 1** (`s_{k+1}`, `mid_{k+1}`).
  - **CH214:** the `batch_receipt_utc` of sweep 1 of pass k - 1 for the unit's outcome-0 token. Eligibility, controls and the
    carry window come from capture k - 1 and earlier (`[k-12, k-1]`); states from sweep 1 of passes k - 2 and k - 1, each
    received before capture k's start. **The target starts at sweep 1 of pass k** (about 113 minutes after the decision).
    (Moved from the round's capture-k decision, 6.1 item 7: a unit frozen at capture k could not be written before sweep k.)
  - **CH215:** the receipt of the first usable feed capture, at least 48 h before the scheduled end, that lists the end.
- **Post-decision mechanism readings.** CH213's and CH212's M1 readings use sweep 1 of pass k, which starts about 5-7 minutes
  after capture k's start and can be received before the frozen file of origin k is written. They are readings, never states:
  the unit builders do not read sweep k (enforced by the causality test, 8.3), and the late rule below does not cover them.
- **Late rule:** as LT4 1.3: a frozen file is written before its earliest primary target slot can start (CH213, CH212:
  capture k + 1's start; CH214: pass k's start), else `.late`, units lost and counted; *late-loss* above 2% of a test's origin
  files.

### 1.4 Shared origin-side eligibility
LT4 1.4 items 1-7, applied in order and counted (LT3's `move_join` and `classify`, vendored), at the unit's eligibility
captures (CH213, CH212: k - 1 and k; CH214: k - 2 and k - 1): binary, open and active; two-sided and tight (spread <= 0.10);
the mid in the test's band (**CH213, CH214: [0.10, 0.90]**, where the venue's two-sided scoring rule is unambiguous; round
14 rule 11's wording is re-read at the pin and nothing depends on it inside this band; **CH212: [0.05, 0.95]**); as-of end
unknown or > `t` + 7 h (CH214's F sweeps reach pass k + 3 and need end > `t` + 9 h, else the unit is in the primary and out
of the F arm, counted); category by `cb17_census.is_sports_sidecar` (non-sports primaries; the sports arm reported,
uncounted); one row per `condition_id`. **Crypto:** every primary excludes crypto by the pinned classifier (`fee_category`
contains `crypto` after strip and casefold; unknown counted and treated as crypto); the crypto arm is reported, uncounted.
Category is a spec parameter. **Series-family rule (census-fixed):** if the census top series family holds > 40% of a test's
primary population, it is excluded from that primary (`<test>.exclude_family`) and the MDE gate recomputed. **Member cap
(all three; round 14 rule 7, declared now):** `n_members(e, j)` = the number of distinct markets of Gamma event `e` among
capture j's complete rows that are binary, open and active (j = k for CH213 and CH212, k - 1 for CH214; a market without
`event_id` is its own event); the primary keeps units with `n_members <= 10`; larger events form the reported *ladder arm*
(same model, uncounted).

### 1.4.1 Reward status: one rule for every LT9 control, and CH212's relation to it
- **The rule.** Every LT9 `rewarded` flag, band `v` (`rewards_max_spread`), minimum size (`rewards_min_size`) and daily rate
  is **`listed_carry24h_v2` exactly as `LIVE_TESTS_7.md` 13.7 and its erratum define it** (spec keys `reward_null_rule:
  listed_carry24h_v2`, `reward_carry_slots: 12`): at eligibility capture j, a null `clob_rewards` gives `rewarded_j = 1` if a
  listed text at any capture in `[j-11, j]` gives a summed daily rate > 0 re-parsed for the UTC day of j; the latest such
  capture is the **source**, whose `rewards_min_size` and `rewards_max_spread` the unit takes; missing slots are skipped and
  counted, never filled; nothing after j is read; listed-but-inactive is 0; malformed text or a missing sidecar row is NaN
  (excluded, counted, with LT8's null taxonomy). The implementation is LT7's `RewardCarry` (with its `_status_array` fix for
  a `null` cell read back as NaN), vendored from `live_tests7.py` sha256
  `e1c5c0c68f7c44d3d5038f9c28324008a4a8132e35f148721a33078d706766a0` (8.1). The **reward panel** of a test is its eligible
  units with `rewarded_j = 1`; the **control panel** (CH213) its units with `rewarded_j = 0`.
- **The carry lag.** For a reward-panel unit, `carry_lag_j` = j minus the source's slot (0 when the field is listed at j;
  LT7's bookkeeping column `rew_carry_lag`).
- **CH212's state is this rule's own bookkeeping, read as an event, not a reclassification.** `om_k = 1[carry_lag_k >= 1]`
  among reward-panel units: Gamma served row k without the field while a listing for the day is in force. Both of CH212's
  classes are `rewarded = 1` under the rule, and CH212 never changes any unit's status. It asks whether the row the display
  served without the field differs in its price path (route A) or coincides with the CLOB feed dropping the market (route
  B). A Supported route A says that omitted rows are stale rows of rewarded markets, which is 13.7's own reading ("Gamma
  leaving the field out of a response"); route B's count measures the frequency of 13.7's alternative reading (a programme
  ending), which the ruling judged less likely. **Neither outcome re-opens LT7's frozen ruling.**
- **The CLOB feed's role.** In CH213 and CH214 the feed is used only for sensitivities (units on which the carry status and
  the feed agree) and for economics (the CLOB's rate); in CH212 it is the adjudicating split (`clob_listed_k`), not a reward
  status. LT9's censuses print the carry-versus-feed agreement (counts only); these counts are descriptive for LT7 and LT8, are
  produced after LT7's censuses and after both designs' freezes, and **never change LT7's or LT8's controls**; a disagreement
  is recorded in the ledger as a note for later designs only.
- **LT8's control differs, disclosed.** LT8's frozen text (sections 1.0 (iv) and 2) parses `clob_rewards` at k only and reads
  an empty field as unrewarded, a v1-equivalent rule written before 13.7. LT9 follows the later ruling; it does not edit,
  reinterpret or depend on LT8's control, and no LT9 quantity enters LT8.

### 1.5 Missing data and per-capture status (never imputed)
As LT4 1.5 and LT8 1.5: every frozen unit receives exactly one status at every target slot (`two_sided`, `one_sided`,
`closed_flag`, `absent`, `capture_missing`; sweep targets `two_sided`, `one_sided`, `absent`, `capture_missing`), write-once
and online; only `two_sided` has a target. The attrition rule (|a_1 - a_0| > 2 pp between the contrasted classes, panels or
the top and bottom terciles gives *attrition-differential* and Lee-type bounds) never changes a verdict. A required input
missing at the origin produces no unit and is counted (`sidecar_missing`, `reward_unparseable`, `.nosweep_km1`,
`.nosweep_km2`, `.noprev`, `sweep_after_origin`, `feed_missing`). A missing control or state is NaN (excluded, counted),
never 0. **Declared indicator-pair exceptions only:** an unknown `end_date` enters log hours-to-end as 0 with `hte_unknown`;
a missing `volume24hr` enters `log1p volume24hr` as 0 with `vol_missing` (LT8 6.1 item 10); a missing `volume_num` change
(CH214's fill control) enters as 0 with `vnum_missing`; every primary is also re-estimated on units with the field present
(reported). A missing F state leaves the unit in the primary and out of the F arm (counted).

### 1.6 What is not looked at before the analysis date
No mid, spread, move, target, P&L, regression or plot from `live_tests9/` files, or from in-window captures, sweeps or feed
captures, for these hypotheses. Only `run_live_tests9.py ops-stats` may run (file, line, role, class, panel and status
counts; reads no price, spread or depth column, enforced by a unit test). No change of thresholds, scales, populations,
estimators or k after registration; operational fixes are logged as deviations. **No LT9 designer, coder or reviewer reads
E015's, E022's, LT7's or LT8's analysis outputs before the pin, nor LT7's or LT8's census outputs (q0602-q0604, q0622-q0623,
q0627) beyond the counts this file already cites (none) except to verify a hash.** After LT7's or LT8's census commit, any
change to an LT9 gate, filter, planning count or expected fate is labelled *informed (LT7 census)* or *informed (LT8 census)*
on the affected test, recorded in the ledger with its reason and carried to the verdict; a re-check fix required after
such a commit carries the label unless the reviewer records that it is independent of those counts.

### 1.7 Estimators and inference
- **Sign convention.** Each test's tested coefficient is multiplied by its predicted sign (`dir` = -1 for CH213 and CH214,
  +1 for CH212 and CH215), so that every one-sided test below is "> 0" in sign-adjusted units and every MDE is a magnitude.
- **Expanding-past demeaning** for CH213, CH214 and CH212 (LT2-LT8): every regressor minus the mean of the market's strictly
  earlier units of the same test; target raw; the first unit of each market drops. CH213's control-panel markets are demeaned
  in their own past exactly as reward-panel markets.
- **Standard errors and p (L10):** CR1 on event (Gamma `event_id`, else the market), two-way event x UTC day of the origin,
  and UTC day. One-sided **p = max(p_event on t with `G_event - 1` df, p_two-way normal, p_day on t with `G_day - 1` df)**.
  **Sparse class (CH213, CH212):** the event t uses `min(G_event, G_minor) - 1` df, `G_minor` = the number of events holding
  at least one unit of the smaller contrasted class (CH213: reward-panel breaks; CH212: omitted units). The conservative 95%
  CI is the hull of a 2,000-draw event bootstrap and the three Wald intervals.
- **Dependence sensitivities (reported, never the verdict):** event x two-day block CR1; the **fixture-day group**
  (`fixture_day_sidecar` of `DEPENDENCE_CLUSTERING_ANALYSIS.md`: event ∪ negRisk ∪ series x UTC end date ∪ underlying x UTC
  end date, computable from the sidecar) as the CR1 cluster in place of the event; the market-deduplicated estimate (the
  **first unit of each market-day** only, a deterministic rule).
- **Overlapping targets and shared shocks.** CH213's `ds` at origin k and its break label at origin k + 1 share `s_{k+1}`
  (the label at k + 1 needs `s_k < 2v`, the target at k ends at `s_{k+1}`): the label at k + 1 is built from origin k's
  target shock, a rolling state in LT7's sense. CH214's innovations at consecutive units share a sweep (MA(1) by
  construction) and its depth level persists. CH212's omission comes in runs. All three therefore use the block gate (1.8).
- **Both-demeaned sensitivity** (LT6): every primary re-estimated with the target also expanding-past demeaned; reported only.

### 1.8 Gates (valid within-unit nulls) and their size
- **Block (circular-shift) Freedman-Lane gate** (LT5's `block_fl_gate`, vendored unchanged) for CH213, CH214 and CH212: after
  expanding-past demeaning, within each market the reduced-model residual series (ordered by origin) is circularly shifted by
  an offset drawn from `[s_m, n_m - s_m]`, `s_m = max(4, ceil(n_m / 4))`, and the full model refitted; 200 draws; passes if
  `p_perm < 0.05`; markets with fewer than 16 shiftable rows are excluded from the gate (counted). CH213 shifts the
  reward-panel and control-panel markets' residuals separately (the interaction is identified across panels; the panel label
  of a market is never shifted). **CH215: sign-flip gate** by event (2,000 draws; each event's treated-minus-control
  difference multiplied by an independent random sign; passes if `p_perm < 0.05`).
- A failed gate on data gives p = 1 in Holm and the label "SE check failed (gate on data)".
- **Size check (L5), after the censuses (k, CH215's entry and the census-fixed values fixed first).** `size-check` runs once,
  on the code to be pinned, 2,000 worlds x 200 draws, seed **20261197**, limit 0.058, every gate scenario through the same
  `block_fl_gate` (or sign-flip) path and minimum (16) as the analysis; worlds carry a UTC-day and a two-day-block column; a
  world is generated once and evaluated under each binding test. Scenarios (no effect of the tested term in every world):

  | # | Scenario (1.8.1) | Gate | Binding for | Statistic |
  |---|---|---|---|---|
  | 1 | **S16:** spreads with ordinary reversion and no band, both panels alike | block FL | CH213 | gate rejection rate |
  | 2 | **S17:** as 1 plus mid jumps whose displayed spread widens and re-centres at the next capture (E004's bounce), both panels | block FL | CH213 | gate |
  | 3 | **liquidity leak:** reversion speed rises with a latent liquidity that is higher on the reward panel; the model sees only a noisy liquidity proxy | block FL | CH213 | gate |
  | 4 | **stale display:** displayed spreads stale with probability 0.15 on control and listed reward-panel rows and 0.30 on omitted reward-panel rows; the model sees `om_k` | block FL | CH213 | gate |
  | 4r | as 4 with listed reward-panel rows stale at 0.20 (an unobserved differential) | block FL | **none (reported)** | gate rejection rate, reported |
  | 5 | **CH214 level world:** log band depth AR(1) rho 0.9, innovation derived from it, the level with a real effect | block FL | CH214 | gate |
  | 6 | as 5 with rho 0.95 and longer series | block FL | CH214 | gate |
  | 7 | **S18 static farmers:** posted sizes constant, `dD` measurement noise only | block FL | CH214 | gate |
  | 8 | **CH214 fill (leak) world:** a taker fill thins the touch without moving it and the spread widens later; the fill control is missing with share `p_vm` | block FL | CH214 | gate |
  | 9 | **S15:** omission iid, independent of the row, with an AR(0.9) log-volatility |move| process | block FL | CH212 | gate |
  | 10 | omission runs (Markov 0.6), market omission rates correlated with market volatility, a venue slot pattern shared by volatility and omission | block FL | CH212 | gate |
  | 11 | **activity leak:** the omission probability rises with the latent volatility state; the model sees only `rv24*` and the last |move| | block FL | CH212 | gate |
  | 12 | CH215 ends with event and end shocks, no effect | sign-flip | CH215 (only if it enters) | gate |
  | 13 | **M-Q (CH214):** a slow drift that the lead and lag innovations proxy equally | none | CH214 | verdict size |
  | 14 | **M-Q (CH213):** a slow drift of the spread level that raises breaks before and after alike | none | CH213 (only if its F is binding) | verdict size |

  **Verdict size** (13, 14) = the share of worlds in which the test's analytic one-sided p (1.7) is < 0.05 **and** its F (1.9)
  holds; the gate is omitted, which can only raise the rate. Criterion: <= 0.058.
- **Also reported, never binding:** a planted-effect power run per test (500 worlds each, effect 1.0c for CH213, CH214 and
  CH215, 0.5c for CH212, per SD or between classes; seeds `20261197 x 100 + 41, 42, 43, 44` for CH213, CH214, CH212, CH215);
  scenario 4r's rate; the far-future label rates of CH213 and CH212 where their F is a label.
- **Leak worlds (3, 4, 8, 11).** In these the confounder reaches the model only through an imperfect control, so the tested
  term carries a real but mechanical partial effect. They are binding: a rejection rate above 0.058 means the design cannot
  separate the hypothesis from the confounder at the declared control, and the test is "SE check failed (size scenario)".
  This is the intended consequence, declared now; their parameters are conventions (1.8.1), not measurements, and are not
  tuned after any result. **Expected:** world 8 is likely to fail at `p_vm >= 0.5` (as LT8 expects of its world 8); worlds 3
  and 11 may fail; world 4 is expected to pass (the stale channel it plants is observed).
- **Consequence of a failure (declared now, as LT5-LT8):** a failing scenario makes **only the tests it is binding for** "SE
  check failed (size scenario)" (1-12) or "SE check failed (mechanical world)" (13, 14): p = 1 in Holm, **k unchanged**, no
  rerun, reseed, redesign or variant. `max_retries 1` covers a deterministic crash only. No preliminary run of any scenario at
  seed 20261197 is made.

### 1.8.1 Simulated worlds (declared now; no census input except `p_vm`)
Common unless stated: unit `i` of a market has `t_row = 7,200 i` s, `day = i // 12`, `block2 = day // 2` from the same
`block_anchor`; events of three markets; 200 draws per world at a fresh sub-seed from one generator seeded 20261197,
scenarios in table order; non-binding runs on generators derived as `20261197 x 100 + n`. Spreads are in cents on a 1c tick
unless stated; 10% of markets carry a 0.1c tick (`1[tick = 0.001]`).
- **1 (S16):** 160 markets (80 reward panel, 80 control), `n_m` uniform on 120..252; latent `x_t` AR(1) rho 0.8, stationary
  SD 3c; displayed spread `s_t = max(1c, round(1c + |x_t|))` (reflection at one tick); a reward-panel market's `v` drawn once
  from {1.5, 2.0, 3.0, 3.5, 4.5}c; each control market assigned the median `v` of reward-panel markets in its tick stratum (the
  cell rule's analogue); break by section 2's rule; target `ds_t = s_{t+1} - s_t`; model and controls as the primary (with
  simulated liquidity `N(0, 1)` equal in distribution across panels); no band effect.
- **2 (S17):** world 1 plus, per capture with probability 0.1, a mid jump `J ~ N(0, (3c)^2)`; at the jump capture one side lags,
  so the displayed spread is `s_t + |J| / 2`, re-centred at t + 1; the own 2 h change enters as the model's control; both
  panels alike.
- **3 (liquidity leak):** world 1 with `rho_m = 0.9 - 0.3 Phi(L_m)`, `L_m ~ N(0, 1)` latent liquidity shifted by **+1.0** on
  the reward panel; the model sees `log1p liquidity = L_m + N(0, 0.5^2)` (fixed per market) and its break interaction; no band
  effect.
- **4 (stale display):** world 1; reward-panel rows omitted with probability 0.25 (`om_t`, seen by the model); a row is stale
  (displays `s_{t-1}`'s true value) with probability 0.15 on control and listed reward-panel rows and 0.30 on omitted rows; the
  next row is fresh; no band effect. **4r:** listed reward-panel rows stale at 0.20 (reported).
- **5-6 (CH214 level):** 80 markets, `n_m` uniform on 24..252 (6: 120..252); `log D_t` AR(1) rho 0.9 (6: 0.95), stationary SD
  0.5 around a market level `N(0, 0.5)`; state `dD_t = log D_{t-1} - log D_{t-2}`; control `log D_{t-1}` with a real effect
  of **-0.3c per unit** on the target; target `dsw_t = sws_{t+1} - sws_t` with `sws` a reflected AR(0.8) spread (SD 2c) plus
  the level effect; no effect of `dD`.
- **7 (S18):** world 5 with posted sizes constant within market: `dD_t ~ N(0, 0.02^2)` iid (measurement noise only), the
  spread independent of it.
- **8 (fill leak, CH214):** world 5 plus, per pass with probability 0.2, a taker fill of size `u = |N(0, 1)|` on a random side
  that lowers `log D` by `0.2 u` without moving the touch, and with probability 0.5 widens the next sweep's spread by `0.5 u`
  ticks (the thinned touch is taken next); the model's fill control is `log1p` of the simulated volume change, **observed only
  where volume is present: per unit, independently, missing with probability `p_vm` = max(the CS9 census `vnum_missing` share
  among CH214's primary units, 0.50)** (0.50 a declared convention; the field's presence is unprobed); a missing unit enters
  as 0 with `vnum_missing` = 1; no effect of `dD` beyond the fill. The fill parameters (0.2, 0.2, 0.5, 0.5) are conventions,
  not measurements.
- **9 (S15):** 100 markets, `n_m` uniform on 120..252; log-volatility `s_t` AR(1) rho 0.9, stationary SD 0.5; `|Δ_t| =
  |0.012 exp(s_t - 0.125) e_t|`, `e ~ N(0, 1)`; `om_t` iid Bernoulli(0.2); target `a_t = |Δ_{t+1}|`; controls `log rv24*`
  (from the last 12 observed `Δ`) and `|Δ_t|`; no effect of `om`.
- **10:** world 9 with `om_t` a two-state Markov chain (persistence 0.6) at a market rate `U(0.05, 0.4)` correlated 0.5 (rank)
  with the market's mean log-volatility; 12 venue slot multipliers `exp(N(0, 0.3^2))` drawn once per world multiply both the
  volatility and the omission odds by slot; the model carries the 11 slot dummies.
- **11 (activity leak):** world 9 with `P(om_t = 1) = logistic(-1.2 + 0.5 z(s_t))`, `z` the within-market standardised latent
  log-volatility; the model sees only `log rv24*` and `|Δ_t|`; no effect of `om` beyond `s_t`.
- **12 (CH215):** 600 ends in 200 events; per end a treated and a control 24-capture path of daily mean spreads with event
  shocks `N(0, (1c)^2)` and end shocks `N(0, (1.5c)^2)`; no effect.
- **13 (M-Q, CH214):** 80 markets, `n_m` uniform on 24..252; a drift `mu_t` AR(1) rho 0.99 (stationary SD 0.5c a pass); lead
  `dD_t = 0.3 mu_{t-1} / sd(mu) + N(0, 1)`, lag at its placement `dD_lag_t = 0.3 mu_{t+3} / sd(mu) + N(0, 1)`; target `dsw_t =
  -(mu_{t+1}) + u_t`, `u ~ N(0, (2c)^2)`; statistic: analytic p < 0.05 and F holds.
- **14 (M-Q, CH213):** world 1 with a drift `mu_t` AR(1) rho 0.99 added to `x_t` on reward-panel markets only (so breaks
  cluster in drifting spells before and after the target alike); statistic: analytic p < 0.05 and F holds (run only if CH213's
  F is binding at census).

### 1.9 Verdicts, the falsification condition and labels (per primary, after Holm over k)
- **F rule (LT7's, unchanged).** The **arm model** is the primary model with the far-future twin added, fitted on the units
  that have it, same demeaning, controls and clustering. `Δ = beta(lead) - beta(twin)` (sign-adjusted). **F holds iff (i) Δ's
  one-sided p < 0.05 under the 1.7 rule (not Holm-adjusted; counted 0) and (ii) Δ̂ >= 0.5 x betâ_primary.** An arm with fewer
  than 50% of the primary's units is *falsification unavailable*. **Whether F binds is fixed at census, before registration,
  from counts only** (spec `f_binding`): CH214's F binds by its census gate (F-MDE <= 1.0c, section 7); CH213's and CH212's F
  binds iff the census F-MDE is <= the test's floor (1.0c; 0.5c for route A), else it is a reported label (*far-future
  not excluded*). Twins: CH213 the strict break of (k + 4, k + 5] and its reward interaction; CH214 the innovation between
  sweeps of passes k + 2 and k + 3 (sizes only); CH212 `om_{k+4}`. CH215 has no F verdict condition (a reported placebo end).
- **Supported (exploratory, prospective):** Holm-adjusted one-sided p < 0.05, estimate in the predicted direction, gate
  passed, **and F holds where it binds.** If everything else holds and a binding F fails or is unavailable: **Inconclusive**
  with the label *mechanical null not excluded* (or *falsification unavailable*); Holm p is not changed.
- **Contradicted:** the conservative 95% CI lies entirely on the other side of 0. **Inconclusive:** otherwise.
  **Unavailable:** fewer than 20,000 units, fewer than 300 events, or fewer than 10 UTC days with units; CH213 also fewer than
  2,000 reward-panel breaks or 2,000 control breaks; CH212 fewer than 2,000 omitted units; CH215 fewer than 200 ends or 100
  events.
- **Labels (never change a verdict):** *material* (the sign-adjusted estimate >= the floor: CH213 and CH214 per tercile or
  class contrast >= 1.0c, CH212 route A >= 0.5c, route B >= 1.0c, CH215 >= 1.0c); *ordinary reversion* (CH213: the main
  effect Supported-level but the interaction not); *capture-quote specific* (CH213: Supported and the sweep reading M1 below
  50% of the primary or p >= 0.05); *omission-driven* (CH213: Supported and the refit on units listed at k below 50% or p >=
  0.05); *not the stale path* (CH212 route A: Supported and the origin-gap reading M1 below 50% or p >= 0.05); *departures,
  not arrivals* (CH214: Supported and the arrival-side slope S2 not negative at p < 0.05); *CLOB-disagreement sensitive* (the
  refit on units whose carry status and feed listing agree changes sign); *informed (X)* (1.1, 1.6); *analytic p oversized
  in simulation*; *underpowered* (Inconclusive and `(t_{G-1, 1-0.05/k} + t_{G-1, 0.8}) x SE_day` above the census MDE);
  *attrition-differential*; *late-loss*; *sweep-missing* (> 2% of origin passes); *series-concentrated* (> 50%);
  *ladder-dominated* (the ladder arm's estimate has the opposite sign); *month-start-sensitive* (1.1's sensitivity changes
  sign).
- **MDE multiplier.** `3.47 = t_{20, 1 - 0.05/6} + t_{20, 0.8}` (LT7's and LT8's constant); for k <= 4 the exact value is
  below it; **not lowered** (conservative; one constant across LT7, LT8 and LT9).

### 1.10 Economics (separate; never changes a verdict)
- Paper taker round trip at the recorded touches (sweep 1 of the entry and exit passes), fees on both legs from the origin
  sidecar (`economics.fee_spec`, `resolve_rate(..., "max_if_unknown")`), LT3's `paper_taker` and `econ` (event-clustered mean,
  one-sided p, >= 30 trades in >= 10 events). No depth, queue or latency: optimistic.
- **Hurdles (`cost-model-v1`, `COST_MODEL.md`, development calibration 2026-10-16..19, as round 14 fact 9 quotes it):** $100
  taker round trip about 2.9c at >= $100k liquidity, 3.9c at $10k-100k, 7.2c at $1k-10k; a 5-share touch round trip about
  4.5c; a passive touch order fills about 3.1% of the time within an hour and loses about 2.38c to adverse selection against
  a 2 h mark (about 0.39c at >= $100k); makers about break-even before rewards (non-sports fill-weighted -0.37c).
- **Reward income (gross, an upper bound, no fills):** the venue's scoring rule as `MAKER_REWARDS_STUDY.md` quotes it (score
  `((v - s) / v)^2 x b` per quote, sampled once a minute, a daily UTC epoch); the daily rate is the carry source's parsed
  rate (sensitivity: the CLOB feed's `rate_per_day`). No reward is computed as earned; only the gross rate per minute of an
  empty band or per dollar of band depth is reported.
- **Declared in advance:** every AREPO taker cost check has failed (E004, E007; 0 of 95 economic cells positive). "Not shown"
  is the expected outcome for every taker cell. No resolution, hold-to-resolution or realised reward income is computed.

### 1.11 Overlaps, dependence, embargo shadows and counting
- **Within LT9:** CH212's population is a subset of the reward panel that CH213 and CH214 also use; CH213 and CH212 share
  captures and the stale-display channel (CH213 carries `om_k` as a control for that reason); CH214's units are quiet books
  whose capture k - 1 may be another test's origin. All in one Holm family; never counted as independent confirmations.
  Pairwise unit-overlap shares and, on shared units, the within-market correlations of the tested terms are printed by the
  censuses and reported.
- **Against registered or drafted tests (no double count; no shared origin):**

  | LT9 | Closest prior | Same data? | Same contrast? | Why not a double count |
  |---|---|---|---|---|
  | CH214 | **LT8 CH203** (the quiet book; window 12-30..01-20) | the same two pre-origin sweeps, the same quiet-touch shape | no: CH203 tests the **asymmetric** change of the 5c imbalance on the YES mid; CH214 the **symmetric** change of in-band depth on the spread. They are not orthogonal by construction (the round's claim is corrected, 6.1 item 9): `z dimb5` is a CH214 control and the census gates their within-market correlation | disjoint windows (LT9 after LT8); `quietbook` respected (no isolating `pool` challenger scored before LT8's date, 9); registration before `T_LT8` |
  | CH212, CH213 | **E022's S2** (reward split of hollow liquidity; analysis 11-17T12Z) | the same `clob_rewards` field (E022 k-only) | no: E022 splits a mover's hollowness by status; CH212 tests the field's omission as an event, CH213 the spread's band crossing | disjoint windows; freeze before `T_E022` or *informed (E022)*; `rewards` token to 11-18 untouched (9) |
  | CH212 | **LT7 13.6 / 13.7** (the reward rulings; CH197, CH192 controls) | the same field and the same carry rule | no: LT7 uses the carry as a control; CH212 reads its carry lag as an event (1.4.1) | LT7's window ends 12-29; pin before `T_LT7` or every test dropped; no LT7 census output read (1.6) |
  | CH213 | **LT7 CH197 / CH192** (`in_band` = spread <= v as a control) and **LT5 R** (CH183, the farmer's side; dropped at census) | the band parameter | no: the strict break `s >= 2v` is a different crossing (LT7's `in_band` flip is reported, section 2); R crossed a price boundary | disjoint windows; R never registered |
  | CH213 | **E015** (anatomy) | captures | no: one-sided widening is a control | *informed (E015)* rule |
  | CH214 | **E022** (post-move hollowness), **LT7 CH195 / CH197** (depth levels on movers and behind the touch) | sweeps | no: levels on other populations | disjoint windows; *informed (E022)* rule |
  | CH215 | **E014** (`tte`, time to the market's end), CH19 (the cliff after an end), **LT8's CH206 map** (q0627, programme starts) | captures, the feed | no: CH215 requires the programme's end to precede the market's by > 48 h | E014 complete; nothing pooled; the map is counts only |
  | all | E009/E010 (cross-venue), E025, E026 (frozen modules to 12-07) | no | no | different streams; nothing of E026 is imported |

- **Signal-engine shadows (disclosed; section 9).** CH213's level `s_k / 2v` can be formed by any model given the spread and
  `rewards_max_spread` (the `rewards` family se9 holds the band; the crossing also needs `s_{k-1}`). CH214's innovation can be
  formed by a model isolating `book0` (pass k - 1) and `book` (pass k), as LT8 found for CH203. CH212's omission is visible
  to any model given the field's history; se9 reads the field at k only and sees an omission as "no programme". LT9 asks for
  the tokens and attribution limits of section 9.
- **Collection overlap (disclosed):** the engine and every earlier test read the same captures, sweeps and feed; LT9's census
  span (2026-11-02..11-12) lies inside E022's window (10-26..11-16) and before E015's analysis (11-15T12Z); census reads are
  counts only and no store is opened. LT9's window overlaps no registered or drafted test's window.
- **Counting (M3):** the analysis adds **k counted tests**, one per surviving primary, kind `live_tests9`
  (`battery2.KIND_RULES["live_tests9"]`, fail-closed). Gate draws, F, secondaries, readings, arms, placebos, economics,
  censuses, the two-ledger map and the size check count 0. The cumulative count is recorded at registration and at analysis.

### 1.12 Stop rules
As LT8 1.12: no interim look; the test runs to `END_UTC` whatever the counts; after 7 days, a test whose units run below one
third of its census projection (counts only) gets the ledger note "likely Unavailable" and nothing else changes; any change to
a pinned file after the pin makes the analysis refuse; the reader exits 75 when nothing is new; a failed reader is re-promoted
within 48 h; gaps stay missing and are counted; disk: the reader refuses above 3.0 GB in `live_tests9/` and no retention rule
may cover `live_tests9/` or the `reward_params/` captures of the window before the analysis is committed; collection of a kind
is switched off when its test is not in `k_tests`.

## 2. CH213: the band break (a displayed spread crossing out of the reward band, against the same crossing where no band exists)

- **Hypothesis and mechanism.** Under the venue's scoring rule a resting quote at distance `s_q` from the midpoint scores
  `((v - s_q) / v)^2 x b` while `s_q < v`, and nothing otherwise; when the displayed spread is at least `2v`, neither touch
  scores and every minute of the day's rate is unclaimed until someone re-enters the band, and the first quoter back alone
  takes the minute's share. Spreads revert everywhere (one maker steps off and the touch refills: Foucault, Kadan and Kandel
  2005); the claim is that on reward-panel markets the reversion after a strict break is **faster than ordinary reversion**,
  measured against the same crossing on markets with no programme. **Direction: within market, E[ds | break, rewarded] -
  E[ds | break, control] < 0 (sign-adjusted > 0), the main effect of the break and its liquidity, tick and level interactions
  held fixed.** Who would be wrong: the ordinary-reversion reading (worlds 1, 3), the bounce reading (world 2, the own 2 h
  change), the stale-display reading (CH212's channel: a stale wide row refreshes; world 4, `om_k`), and the drift reading
  (world 14 where F binds).
- **Unit and population.** Non-sports ex-crypto eligible market x capture k (1.4 at k - 1 and k), mid in [0.10, 0.90],
  `n_members <= 10`, end > `t` + 7 h, sidecar rows present at k - 1 and k with a finite reward status. **Reward panel:**
  `rewarded_k = 1` (1.4.1), with `v` = the source capture's `rewards_max_spread` (cents, as served; `v_price = v / 100`) and the
  same `v` at k - 1 (a band change between the sources of k - 1 and k excludes the unit, counted `band_changed`). **Control
  panel:** `rewarded_k = 0`, with an **assigned band** `v_ctrl(k)` = the median `v` of the reward-panel units of capture k in
  the same cell (sidecar `fee_category` after strip and casefold, liquidity tier `< $1k`, `$1k-10k`, `$10k-100k`, `>= $100k`
  from capture k's `liquidity`, and tick `0.01` or `0.001`) if that cell holds >= 20 reward-panel units, else the median of
  the (tier, tick) cell if it holds >= 20, else the unit is uncovered (counted `ctrl_band_uncovered`). The assignment uses
  capture k only (causal, deterministic). Boundary: first origin 2027-01-21T02:31Z (1.1).
- **State (frozen; decision time = capture k's receipt).** `s_j = ask_j - bid_j` (Gamma, price units); **`break_k = 1[s_{k-1}
  < 2 v_price and s_k >= 2 v_price]`** (the strict crossing: no displayed touch scores at k and both did at k - 1 within the
  band's outer edge); `rew_k` the panel flag; `om_k` (1.4.1; 0 on the control panel); `x_k = s_k / (2 v_price)`. Also frozen
  (secondaries): the LT7-style crossing `inb_flip = 1[s_{k-1} <= v_price < s_k]`, the one-sided widening flag (only one of
  `bid`, `ask` changed between k - 1 and k, E015's anatomy in spread form), the carry lag, the source's rate, the CLOB feed's
  listing and band at the last usable feed capture before k (sensitivities only).
- **Target (exact).** **`ds = s_{k+1} - s_k`** (Gamma; joint mask; in cents). M1 (*capture-quote specific*): the CLOB reading
  `sws_{k+1} - sws_k` (sweep 1 of passes k and k + 1, outcome 0, both two-sided; sweep k must be received after capture k's
  row, else NaN, counted). M2 (reported): `1[s_{k+1} < 2 v_price]` among breaks (back inside the outer edge). S1: the 6 h
  change `s_{k+3} - s_k`.
- **Primary statistic.** Expanding-past demeaned OLS of `ds` on **`break x rew`** over both panels, controls: `break`, `rew`,
  `break x z log1p liquidity_k`, `break x 1[tick = 0.001]`, `break x z log s_k`, `x_{k-1}`, `x_k`, `log s_k`, logit `mid_k`,
  `|mid_k - 0.5|`, `log1p liquidity_k`, the own 2 h change `mid_k - mid_{k-1}` and its absolute value, own 24 h change (+
  flag), `log rv24*_k` and `rv_floor` (LT7 6.B), 1[tick = 0.001], the one-sided widening flag, **`om_k` and `break x om_k`**
  (CH212's stale channel held fixed), log hours-to-end (+ flag), 11 slot-of-day dummies. Tested coefficient: `break x rew`,
  sign-adjusted. Inference 1.7 with the `G_minor` df; seed **20261191**. Gate: block FL (worlds 1-4; 14 if F binds), seed
  **20261291**.
- **Falsification (F; binding only if the census F-MDE <= 1.0c, 1.9).** Twin: `break'` = the strict break of (k + 4, k + 5]
  against the same `v` (or `v_ctrl` of k + 5's cell), and `break' x rew`, read through the lag-slot loader as spreads only.
  Placement: the lead crossing ends at the target's start; a twin adjacent to the target's end would need `s_{k+1}`, the
  target's own endpoint, so the twin is placed three intervals after it (the round's placement). Disclosed: lead and twin are
  not mirror images; F is conservative where a large re-tightening raises later breaks.
- **Mechanism readings.** M1 (CLOB, above); M2; the main effect within the reward panel (reported; *ordinary reversion*
  label); the refit on units listed at k (`om_k = 0`; *omission-driven* label); the agreeing-units refit (carry status and
  feed listing agree; *CLOB-disagreement sensitive*).
- **Secondaries.** S1 6 h; S2 `inb_flip` in place of `break`; S3 the ladder arm; S4 sports and crypto arms; S5 the control
  panel restricted to markets absent from the CLOB feed at the last usable feed capture (purity); S6 counts by tier, tick,
  `v` and panel; S7 the market-deduplicated estimate (1.7).
- **Planning MDE (estimate; every input declared now, sources in 10.1).** Reward panel per capture: carry-rewarded non-sports
  ex-crypto markets **10,000 (low) to 12,000 (high)** x mid band 0.70 x cap 0.50 / 0.70 = **3,500 / 5,880** units a capture;
  strict breaks **1% / 3%** (unprobed): **35 / 176 a capture**, effective 80% over 252 captures: `n_rb` **7,056 / 35,562**;
  reward-panel non-breaks `n_rn` 698,544 / 1,149,846; control breaks planned equal to reward-panel breaks (`n_cb = n_rb`;
  the control panel is larger, about 15,000-20,000 unrewarded non-sports ex-crypto markets a capture, but its band coverage
  and break rate are unprobed) and control non-breaks `n_cn = 2 n_rn`. SD of `ds` 2c; DE **31**; `VIF_w` **2.0** for the
  interaction (a declared convention: it is collinear with `break`). **Interaction:** `3.47 x 2c x sqrt(1/n_rb + 1/n_rn +
  1/n_cb + 1/n_cn) x sqrt(31) x 1.5 x sqrt(2.0)` = **1.39c (low), 0.62c (high)**; DE 51: 1.78c / 0.80c; a quarter of the low
  count 2.77c. The main effect (reported, `VIF_w` 1.3): 0.79c / 0.36c. **The 1.0c gate needs about 68 strict reward-panel
  breaks a capture** (and as many control breaks) at the low panel size. F-MDE (planning `r` 0.1, factor 1.49): 2.06c / 0.93c,
  so F binds only near the high end. **Expected: borderline at census, dropped at the low end** (declared now); prior odds of
  surviving census 0.35, and about 0.15 of also passing the binding liquidity-leak world 3.
- **Floors (Unavailable):** < 20,000 units, < 2,000 reward-panel breaks, < 2,000 control breaks, < 300 events, < 10 days.
- **Economics.** Maker (primary route): at a reward-panel break, post the two-sided minimum inside `v` at once; gross: the
  source's daily rate x 120 / 1,440 (the interval's share of the day, an upper bound of a first-back quoter's take) against
  the passive-fill adverse selection over the interval (3.1% an hour x 2 h x 2.38c x the minimum size), per tier, "gross, no
  fills"; the census prints the rate distribution of broken markets. Taker: a cost rule only (never cross a spread >= 2v on
  the reward panel; wait one pass; S1 reports the 6 h spread).
- **Reader it extends.** LT8's capture reader (series and status files) with the sidecar reward columns and LT7's
  `RewardCarry` window (12 slots of listed texts per market, evicted below k - 11).
- **Missing data.** `sidecar_missing`, `reward_unparseable`, `band_changed`, `ctrl_band_uncovered`, `.noprev`, one-sided at k -
  1 or k: excluded, counted.

## 3. CH214: the pool splits (the symmetric in-band depth arrival behind an unmoved touch)

- **Hypothesis and mechanism.** The pool is split in proportion to each quoter's score, so a new quoter of equal size at the
  same distance halves the incumbent's share, and the incumbent's best response is to quote closer to the midpoint (raising
  `(v - s_q)` for the same size): arrivals of in-band depth compress the spread. The Telonex case (depth 23x and makers 302 to
  639 after a programme start, as `MAKER_REWARDS_STUDY.md` and round 13 quote it) is the extreme form; CH206 reads the start,
  CH201 the yield level, CH209 the farmer's touch as a flag. **Direction: within market, the slope of `dsw` on `zdD` < 0
  (sign-adjusted > 0), the depth level and the asymmetric innovation held fixed.** Who would be wrong: the static-farmer
  reading (sizes never move; world 7 and the identification gate), the level reading (a persistent depth level whose
  innovation is noise; worlds 5-6), the fill reading (a taker fill thins the touch without moving it and the spread widens
  later: **same-signed**, 6.1 item 8; world 8), and the drift reading (world 13, F).
- **Unit and population.** Reward-panel (`rewarded_{k-1} = 1`, 1.4.1) non-sports ex-crypto eligible market at capture k - 1
  (1.4 at k - 2 and k - 1), mid in [0.10, 0.90], `n_members <= 10`, end > `t` + 7 h, with sweep 1 of passes k - 2 and k - 1
  for its outcome-0 token both present, two-sided, tight (sweep spread <= 0.10), both band sums positive, each received before
  capture k's start; **quiet:** `|smid_{k-1} - smid_{k-2}| < 0.005` **and** `|sws_{k-1} - sws_{k-2}| < 0.005` (neither the
  sweep mid nor the sweep spread moved between the passes); **band unchanged:** the carry source's `rewards_max_spread` equal
  at captures k - 2 and k - 1 (else `band_changed`, counted); no programme start or end inside (k - 2, k - 1] by the carry
  status (a status change excludes the unit, counted `status_changed`). Boundary: first unit as 1.1.
- **State (frozen; decision time = sweep k - 1's receipt).** **Band sum** `D_j = depth_bid_1c + depth_ask_1c` of sweep 1 of
  pass j if `v <= 1.5c`, else `depth_bid_5c + depth_ask_5c` (a declared proxy: the band is measured from the midpoint, the
  stored sums from the touch; fixed now, before any count; the census prints both); **`dD = log D_{k-1} - log D_{k-2}`**; `zdD`
  with the census centre and scale (pooled, fixed in the spec; LT8 6.1 item 3's convention). Also frozen: the per-side splits
  `dDb`, `dDa`; `dlev` (whole-book level counts, as LT8's); `dgrain` (band sum per level); `dimb5` exactly as LT8 CH203
  defines it (a control here); `lag_s` = capture k's start minus sweep k - 1's receipt; `yield0 = rate / (D_{k-1} x
  mid-weighted price)` (economics only).
- **Target (exact).** **`dsw = sws_{k+1} - sws_k`** (sweep 1 of passes k and k + 1, outcome 0, both two-sided; cents). M1
  (reported): the Gamma reading `s_{k+1} - s_k`. M2 (reported): the yield at pass k + 1, `rate / D_{k+1}` through the
  sizes-only lag-slot loader (the incumbent's pool share per share posted; slope < 0). S1: `sws_{k+3} - sws_k`.
- **Primary statistic.** Expanding-past demeaned OLS of `dsw` on `zdD`, controls: `log D_{k-1}` (the level), `z dimb5` (the
  asymmetric part, CH203's state), `sws_{k-1}`, `s_{k-1}` (Gamma) and the gap `s_{k-1} - sws_{k-1}`, `lag_s`, logit
  `mid_{k-1}`, `|mid_{k-1} - 0.5|`, `log1p volume24hr_{k-1}` (+ `vol_missing`), the fill control `dvnum = log1p(max(0,
  volume_num_{k-1} - volume_num_{k-2}))` (+ `vnum_missing`), own 24 h change (+ flag), `log rv24*_{k-1}` and `rv_floor`,
  1[tick = 0.001], `ft_both` (CH209's farmer touch at sweep k - 1 against the source's `rewards_min_size`), `log rate` (the
  source's parsed daily rate), `om_{k-1}`, log hours-to-end (+ flag). Tested coefficient: `zdD`, sign-adjusted. Inference
  1.7; seed **20261192**. Gate: block FL (worlds 5-8), seed **20261292**.
- **Falsification (binding, F).** `dD_lag = log D_{k+3} - log D_{k+2}` (sweep 1 of passes k + 2 and k + 3, band sums only,
  through the lag-slot loader; no quiet condition, LT8 13.3's Q3 ruling). Placement: the lead innovation ends one pass before
  the target's first sweep (k - 1 to k); the lag starts one pass after the target's last sweep (k + 1 to k + 2): the mirror
  image. Arm model = primary + `zdD_lag` (same centre and scale); world 13 is CH214's verdict-size statement.
- **Mechanism readings.** M1, M2; the silent arm (units with `dvnum` observed and zero: a depth change with no traded
  volume); the agreeing-units refit (*CLOB-disagreement sensitive*).
- **Secondaries.** S1; **S2 the arrival-side slope** (`max(0, zdD)` and `min(0, zdD)` as separate terms; label *departures,
  not arrivals*); S3 `dlev` and `dgrain` in place of `dD`; S4 the per-side splits; S5 the ladder arm; S6 sports and crypto
  arms; S7 the market-own expanding-past scale of `dD`; S8 the 5c band sums for every unit (the proxy's sensitivity); S9 counts
  by tercile, tick, `v` and tier.
- **Planning MDE (estimate; sources in 10.1).** Carry-rewarded non-sports ex-crypto markets a capture 10,000 / 12,000 x mid
  band 0.70 x cap 0.50 / 0.70 x two-sweep coverage 0.86 x quiet (mid and spread unchanged) **0.60 / 0.75** x band unchanged
  0.95 x target sweeps two-sided 0.90 = **1,544 / 3,242 units a capture**; effective 80% over 252: `n_eff` **311,270 /
  653,600**. SD of `dsw` 2c; DE **31**; `VIF_w` 1.5; tercile gap 2.2: `3.47 x 2c / sqrt(n_eff) x sqrt(31) x 1.5 x sqrt(1.5) x
  2.2` = **0.28c (low), 0.19c (high)**; DE 51: 0.36c / 0.25c; a quarter of the low count 0.56c. **F-MDE** `x sqrt(2 / (1 -
  max(0, r)))`: 0.40c at r = 0, 0.44c at 0.2, 0.47c at 0.3 (low); 0.27-0.33c (high): under the 1.0c cap. **Power is not the
  question; identification and the fill leak are.** Prior odds of surviving census 0.35, and about 0.10 of also passing the
  binding fill-leak world 8.
- **Floors (Unavailable):** < 20,000 units, < 300 events, < 10 days.
- **Economics.** Maker (primary route): hold the quote while `zdD` is in its bottom or middle tercile; in the top tercile move
  to the touch (the formula's best response) or leave; the reported quantity is the drop of `rate / D` from pass k - 1 to pass
  k + 1 by tercile, "gross, no fills". Taker: a cost rule only (trade after arrivals; reported).
- **Reader it extends.** LT8's sweep reader for CH203 (sweep 1 of passes k - 2 and k - 1 joined to capture k - 1), with band
  sums in place of the imbalance and the sizes-only lag join at k + 2, k + 3.
- **Missing data.** `.nosweep_km1`, `.nosweep_km2`, `sweep_after_origin`, outcome-0 token absent, one-sided, a band sum
  missing or zero, not quiet, `band_changed`, `status_changed`: excluded, counted separately.

## 4. CH212: the display's omission and the two ledgers (the carry lag as a serving-path event, adjudicated by the CLOB)

- **Hypothesis and mechanism.** About 3,000 reward-panel markets a day switch between a listed and a null `clob_rewards`
  within a UTC day; LT7's ruling reads this as Gamma leaving the field out of some responses. If an omitted row comes from a
  different serving path, its other optional fields and its price are stale too, and the next capture's displayed move is
  partly the display catching up (CH37's stale displayed mid, with a per-row flag for the first time). **Route A (the stale
  path): within market, E[a | om = 1] - E[a | om = 0] > 0** on units the CLOB feed confirms are rewarded, the slot of day and
  recent activity held fixed. **Route B (real churn): within market, the spread change after an omission that the CLOB feed
  also dropped is wider than after a listed row** (> 0). The route is fixed by the census from counts (below), never from
  prices; the other route is a reported reading. **Scope stated now:** a Supported route A says that the display lags the
  CLOB at omitted rows (a display-quality and row-weighting fact for the engine and a maker's "do not chase" rule); it is not
  a forecast of CLOB prices. Who would be wrong: the flakiness reading (the field alone blinks; world 9, the route rule), the
  cron reading (omissions in one slot; the venue-clock gate, world 10), and the activity reading (omissions mark busy markets;
  world 11).
- **Unit and population.** Non-sports ex-crypto eligible market x capture k (1.4 at k - 1 and k), mid in [0.05, 0.95],
  `n_members <= 10`, end > `t` + 7 h, with `rewarded_k = 1` under 1.4.1. **Route A additionally:** `clob_listed_k = 1` (the
  market is in the CLOB native or sponsored feed at the last usable feed capture before capture k's start; a missing or
  failed feed capture makes the flag NaN and the unit is excluded, counted `feed_missing`); route-A units with
  `clob_listed_k = 0` are counted (`ghost`) and excluded. **Route B:** units with `om_k = 0 and clob_listed_k = 1` (the
  comparison class) and units with `om_k = 1` whose market was in the feed at the last usable capture before capture k - 1's
  start and is absent from the last usable capture before capture k's start (`clob_dropped_k = 1`).
- **State (frozen; decision time = capture k's receipt).** **`om_k = 1[carry_lag_k >= 1]`** (1.4.1); `om_{k-1}` and the slots
  since the last omission (controls); the row's serving-path fields at k: `page_index` normalised by the capture's largest
  page index, `received_utc` minus the capture start, the presence of `volume24hr`, `last_trade_price` and `competitive`
  (census and route-rule inputs, and reported moderators; never the tested term).
- **Target (exact).** **Route A: `a = |mid_{k+1} - mid_k|`** (Gamma; joint mask). **Route B: `ds = s_{k+1} - s_k`** (cents).
  M1 (route A; *not the stale path*): the origin gap `|smid_k - mid_k|` against sweep 1 of pass k (received after capture k's
  row, else NaN); M2 (reported): the signed catch-up `sign(mid_k - mid_{k-1}) x (mid_{k+1} - mid_k)`; S1 the CLOB move
  `|smid_{k+1} - smid_k|`.
- **Primary statistic.** Expanding-past demeaned OLS of the route's target on `om_k` (route A) or on `om_k x clob_dropped_k`
  with `om_k` (route B), controls: **11 slot-of-day dummies**, `|mid_k - mid_{k-1}|` (+ `.noprev` excluded), `om_{k-1}`, logit
  `mid_k`, `|mid_k - 0.5|`, spread at k, `log1p liquidity_k`, `log1p volume24hr_k` (+ `vol_missing`), own 24 h change (+ flag),
  `log rv24*_k` and `rv_floor`, 1[tick = 0.001], log hours-to-end (+ flag). `rewarded` is 1 for every unit by construction and
  enters no model. Tested coefficient: `om_k` (A) or `om_k x clob_dropped_k` (B). Inference 1.7 with the `G_minor` df; seed
  **20261193**. Gate: block FL (worlds 9-11), seed **20261293**.
- **Route rule (declared now; counts only; CC9, section 7).** **Route A** if, on census reward-panel units with
  `clob_listed_k = 1`, the Mantel-Haenszel odds ratio (strata: market x UTC day) of `volume24hr` absent given `om = 1`
  against `om = 0` is >= 1.5, **or** that of `last_trade_price` absent is >= 1.5, **or** the within-market mean difference of
  the normalised page position between `om = 1` and `om = 0` rows is >= 0.10 in absolute value. **Route B** if >= 30% of
  Gamma's listed -> null transitions (listed at k - 1, `om_k = 1`) have `clob_dropped_k = 1`. **Both: route A is the primary
  and route B a reported reading** (6.1 item 3; k stays <= 3 plus CH215). **Neither: CH212 is dropped as a test** (the
  `rwblink` family and the two-ledger map are built regardless). The route enters the spec (`ch212.route`) before
  registration.
- **Falsification (F; binding only if the census F-MDE <= the route's floor, 1.9).** Twin: `om_{k+4}` (the carry-lag flag at
  capture k + 4, by the same rule, read as the field's status only through the lag-slot loader; no price). r is printed; the
  twin is not required independent (omissions come in runs), and r enters the F-MDE.
- **Secondaries.** S1; S2 the route not chosen; S3 omissions by run length (1, 2, >= 3 slots); S4 the ladder arm; S5 sports and
  crypto arms; S6 the serving-path moderators (`page_index`, receipt offset, co-omissions) as interactions, reported; S7 the
  market-deduplicated estimate.
- **Planning MDE (estimate; sources in 10.1).** Switching markets **3,000 / 3,500 a day** (the probe's 2,112-3,995) x omitted
  slots per switching market-day **2 / 3** (unprobed; round 14's planning 2) x mid band 0.85 x cap 0.50 / 0.70 x
  CLOB-confirmed 0.85 / 0.95 (unprobed) = **2,168 / 5,935 omitted route-A units a day**; effective 80% over 21 days: `n1`
  **36,414 / 99,710**; listed comparison units `n2` **160,000 / 450,000** (round 14's 450,000 listed slots on switching days,
  the low end scaled by the band and cap). SD of `a` 3c; DE **31**; `VIF_w` 1.3: `3.47 x 3c x sqrt(1/n1 + 1/n2) x sqrt(31) x
  1.5 x sqrt(1.3)` = **0.58c (low), 0.35c (high)**; DE 51: 0.74c / 0.45c; a quarter 1.15c. **The 0.5c gate needs about 48,300
  effective omitted units (about 240 a capture)** at `n2 = 4.4 n1`. F (planning `r` 0.1): 0.86c / 0.52c: reported at both
  ends unless the census is better. Route B (SD 2c; `n1` = 30% / 50% of the omitted units before the CLOB filter: 12,852 /
  52,479): 0.61c / 0.31c against 1.0c; F 0.90c / 0.45c. **Expected: the route rule decides first;** prior odds of surviving
  census 0.30, and about 0.15 of also passing the binding activity-leak world 11.
- **Floors (Unavailable):** < 20,000 units, < 2,000 omitted (route A) or dropped (route B) units, < 300 events, < 10 days.
- **Economics.** Route A, maker: do not re-centre on a displayed move whose origin row was an omission; gross: the class
  contrast of `a` per tier against 0.39c and 2.38c ("gross, no fills"); no taker route (the catch-up is in the display, not
  the book). Route B, maker: leave at a real de-listing; gross: the spread change and the forgone quoting time, reported.
- **Reader it extends.** LT8's capture reader with LT7's `RewardCarry` (which already keeps the source slot, hence the carry
  lag) and a new light reader of `reward_params/` that writes, per feed capture, the set of listed `condition_id`s with their
  band and rate (write-once, < 50 MB over the window).
- **The two-ledger map (counts only; no test; filed with CC9 and repeated in the window by `ops-stats`).** Per feed capture:
  markets CLOB-listed and carry-rewarded, CLOB-listed and carry-unrewarded for the whole window ("hidden programme"),
  carry-rewarded and CLOB-absent ("ghost"), and band or rate mismatches; no price, spread or depth is read.

## 5. CH215: the scheduled end (optional fourth; enters only by its own census counts)

- **Entry rule (declared now).** CH215 is a primary of LT9's Holm family **if and only if every gate of its census CR9
  (section 7) passes**, read from counts alone at the same census step as the other three and before registration; its
  binding gate is expected to be the MDE gate, which needs **about 51 qualifying ends a day** (the round's kill line of 30 a
  day is also a gate). If any CR9 gate fails or is NaN, CH215 is recorded as "not entered (count)", uncounted, k stays the
  number of CH213, CH214 and CH212 that survive, no other test replaces it, and its text below is moot. CH215 cannot enter
  later. If it enters, k may reach 4, its size scenario 12 becomes binding, and its token is requested (9).
- **Hypothesis and mechanism.** The CLOB feed serves each programme's end, so a programme that stops paying at a stated time
  is visible days ahead; the last partial epoch pays pro rata and incumbents' capital is better posted elsewhere, so makers
  retreat before the end and the spread widens before the cliff (CH19 reads the cliff after it). **Direction: the treated
  before-after spread difference minus the control's > 0.**
- **Unit.** A programme end `e` on a non-sports ex-crypto market: the end time `T_e` (the configuration's end date) is listed
  identically in a usable feed capture received at least 48 h before `T_e` (decision time = that capture's receipt); the
  market's `end_date` (capture at the decision) is > `T_e` + 48 h; the market is eligible (1.4) at the decision capture, mid in
  [0.10, 0.90]. **Intention to treat:** a later change of the end (extended, rolled, cut) keeps the unit at its originally
  listed `T_e`, counted `end_moved`. Controls: up to 3 reward-panel markets in the same (category, tier, tick) cell with no
  listed end within `[T_e - 72 h, T_e + 72 h]` at the decision capture, chosen by the smallest `|log liquidity|` distance
  (ties by `condition_id`), using decision-time fields only.
- **Target.** `Δs_e` = mean Gamma spread over the 12 captures in `[T_e - 24 h, T_e)` minus the mean over the 12 in `[T_e -
  48 h, T_e - 24 h)`, for the treated market minus the mean over its controls (cents; a capture missing on either side is
  skipped and counted; fewer than 8 of 12 on either side drops the end, counted).
- **Primary statistic.** Event-clustered mean of `Δs_e` (CR1 by event; p = max(event t, day t) with `G - 1` df), one-sided;
  seed **20261194**; sign-flip gate by event (world 12), seed **20261294**. Reported placebo: the same difference placed 72 h
  earlier (`[T_e - 96 h, T_e - 72 h)` against `[T_e - 120 h, T_e - 96 h)`); label *placebo not excluded* if its one-sided p <
  0.05 and its mean is at least half the primary's.
- **Planning MDE (estimate).** `3.47 x 2c x sqrt(2 / n_eff) x sqrt(3) x 1.5 x sqrt(1.3)` (DE 3.0, round 14's form): **2.23c at
  `n_eff` 170, 0.92c at 1,000**; the 1.0c gate needs `n_eff` >= about 845, i.e. **about 51 ends a day** over 21 days at 80%
  effective. (Round 14 printed 1.9c / 0.78c; its arithmetic does not reproduce, the recomputed values are stated here.)
  Expected: not entered (prior 0.10).
- **Economics.** Maker: leave with the pool before the last epoch; gross `Δs_e` per tier, reported. Taker: none.
- **Reader.** The `reward_params/` reader of section 4 plus the capture reader.

## 6. Design changes, ideas not taken, census drops

### 6.1 Design changes to the round-14 sketches (made before any data; each needs the challenger's acceptance)

1. **Reward status by `listed_carry24h_v2` everywhere** (CH213's and CH214's panels; CH212's population). The round defined
   CH213's and CH214's panels by the CLOB feed with Gamma's carry as a sensitivity. LT9 swaps them so that one causal rule,
   already ruled on by the challenger and implemented in reviewed code, defines every status, and so that the CH213 and CH214
   censuses do not depend on the feed's coverage; the feed becomes a sensitivity (agreeing units) there (1.4.1).
2. **CH212's population is causal.** The round's unit, "a market x capture on a market-day with a null/listed switch",
   selects origin k on captures later in the same UTC day (a switch after k makes the day eligible): selection on the future.
   LT9 uses all reward-panel units and reads the omission as the carry lag (`om_k = 1[carry_lag_k >= 1]`), which uses only
   `[k-11, k]`; the switching count is a descriptive census print.
3. **CH212's route rule fixes one primary.** The round added a second primary when both route conditions hold (k += 1). LT9
   keeps k <= 3 plus CH215: route A is the primary when both hold (it is the object CH212 is named for), route B reported.
4. **CH212's route A is restricted to CLOB-confirmed units** (`clob_listed_k = 1`), so that an omission there is a display
   event and not a programme end; route B is the CLOB-dropped split. **Activity controls** (`|mid_k - mid_{k-1}|`, `om_{k-1}`,
   `log1p volume24hr`) and the binding activity-leak world 11 are added: an omission that marks busy markets would predict
   |moves| without any staleness.
5. **CH213's control band is a cell median of the same capture** (category x tier x tick, >= 20 reward-panel units, a (tier,
   tick) fallback), not a matched market: deterministic, causal and countable. **Break interactions** with liquidity, tick
   and the spread level, and `om_k` with `break x om_k`, are controls (the interaction must be beyond liquidity-dependent
   reversion and beyond CH212's stale channel); binding worlds 3 and 4 are added to the round's S16 and S17.
6. **CH213's MDE follows the declared chain** (mid band, cap): 1.39c low / 0.62c high, not the round's 0.99c / 0.55c (which
   used the listed count before the band and the cap and doubled the main effect); the count gate is the MDE-derived 70 a
   capture, not the round's 100. The mid band is [0.10, 0.90] for the two reward-rule tests (the scoring rule's two-sided
   region).
7. **CH214's decision time is the receipt of sweep k - 1 and its target is on the sweeps** (`dsw = sws_{k+1} - sws_k`). A
   unit decided at capture k could not be frozen before sweep k (the reader runs about 104 minutes after a capture), and a
   Gamma target from k can carry a display catch-up of a CLOB change already made before k (LT8 6.1 item 1's reasoning). With
   state and target on the CLOB's own book, the object is the book where farmers are scored; Gamma's change is M1.
8. **CH214's fill confounder sign is corrected.** The round called a fill "the opposite sign: a conservative confounder". A
   fill that thins the touch without moving it lowers `dD` and makes the next widening likelier: **the same sign as the
   hypothesis** (as LT8 6.1 item 5 found for CH203). LT9 adds the `dvnum` control, the silent arm, the arrival-side slope S2
   and the binding leak world 8 at `p_vm >= 0.50`.
9. **CH214's quiet filter adds an unchanged sweep spread; `zdD` uses a census scale; `z dimb5` is a control.** The round
   standardised within the market's past (LT8 6.1 item 3's reason for a census scale: the lead and the lag share it) and
   called the symmetric and asymmetric parts "orthogonal by construction"; they are different functions of the same four
   sums and are not orthogonal, so CH203's state is held fixed and the census gates their correlation.
10. **CH214's count gate is 1,000 units a capture** (the round's 3,000 was not derived from its MDE; the declared chain gives
    1,544 at the low end, where the slope MDE is 0.28c). The MDE, identification and leak worlds remain the binding gates.
11. **CH214's F twin is the mirror pair (k + 2, k + 3]** (the round's k + 4 -> k + 5 does not mirror the one-pass gap once the
    target is on sweeps k and k + 1).
12. **CH215:** decision at the first feed capture >= 48 h before the end; intention to treat at the listed end; controls from
    decision-time fields; recomputed MDE (2.23c / 0.92c); the entry rule of section 5.
13. **The block gate for all three primaries**, not the round's market x day plain gate: CH213's label at k + 1 is built from
    origin k's target, CH214's level persists and its innovations share sweeps, CH212's omissions come in runs (1.7).
14. **The ordered lane** (after LT8), not the fast lane (1.1).
15. **Multiplier 3.47** kept; **no extension**; **design-text freeze before the earlier of 2026-11-14T12:00Z and `T_E015`**.

### 6.2 Ideas not taken into LT9
- **CH216** (large prints without a sample; the monitor's universe-wide print slots): non-sports ex-crypto is a few hundred
  prints a day (prior 0.15); it is a scope call (0.45 with sports in), not proposed; the `printage` family is engine-first.
- **Engine-first, not taken:** CH217 (row quality; CH212's census prints its co-omission counts), CH218 (the display's
  disagreement), CH219 (the touched book), CH220 (dormancy), CH221 (the siblings' proposal window; needs an admissibility
  ruling). Round 14 section 4's rejections stand.
- **The `rwblink`, `bandbreak`, `pool` and `rwend` families** are built by the engine track under their tokens regardless of
  the census (9).

### 6.3 Census drops
None yet. Census drops (and CH215's entry or non-entry) will be recorded here, with their counts, before the pin.

## 7. Pre-registration censuses (counts only; before registration; worn pre-window data; no target read)

Each census runs once, reads origin-side fields only (no target, no P&L; the only later-slot quantities read are CH214's lag
sweeps' band sums and CH213's and CH212's twin states, for the F-feasibility correlations, never paired into a target,
through the lag-slot loader), prints counts, and is committed with its sha256 before the registration commit. **Lag-slot
loader:** a census reading a slot later than a unit's decision receives only the keys and the named fields (CH214: the four
1c or 5c depths; CH213: `bid`, `ask` reduced to the spread and compared against `2v` inside the loader, which returns only the
twin break flag; CH212: the `clob_rewards` status only); no mid, last trade, touch size or other price column of a later slot
reaches census code (unit test, 8.3). **Every gate threshold below is stated now, before any census.** A failed gate drops
that test before registration (uncounted); `k_tests` lists the survivors. **Input identity:** the census refuses unless every
input file it opens is named in the LT9 seal with an equal sha256, builds slots and origins from the seal, and refuses if a
sealed file in a needed slot is absent locally.

**Inputs (a fresh seal; round 14 rule 9).** The census span is **`[2026-11-02T00:00Z, 2026-11-12T00:00Z)`**, 10 UTC days,
120 capture slots, all after both 2026 daylight-saving changes (the window is on winter time too) and after LT7's censuses.
Files: complete captures (rows, sidecar, manifest), sweep 1 of each pass, and `reward_params` captures whose start lies in the
span, plus the 12 capture slots and 2 passes before it (`[2026-11-01T00:00Z, 11-02T00:00Z)`) as look-back only (carry window,
`rv24*`, `s_{k-1}`, sweeps k - 2 and k - 1) and the 2 passes after it (CH214's lag sweeps, sizes only). Planned volume: 144
captures x 3 files, 146 sweep directories x 2, about 160 feed captures x 2: about 880 files, planning 1.5-2.0 GB.
- **Restore, seal, census: each once.** q0640 first accepts host copies that pass a sha256 check against the archive
  catalogue, then restores the rest byte for byte from the data releases (snapshot retention is 8-10 days, so the span's first
  days will have left the host by the seal date; `reward_params/` has no retention rule); it measures bytes first and **stops
  and asks the owner** if the restore would exceed the host's free disk (CLAUDE.md storage stop rule); a file found in neither
  place is genuinely missing (counted, never substituted). q0641 writes `seals/lt9_census_inputs.json` (files, sha256, the
  seal's own slot assignment, and the **frozen LT9 design-text sha256**, so the seal is written only after the freeze); the
  orchestrator commits it before any LT9 census runs.
- **Minimum covered days** (covered origins / 12): >= 7.0 for each test (and >= 5.0 for CH214's F pairs). Below it, every gate
  of that test's census is NaN and fails. **Feed completeness** (CR9, CC9): usable feed captures on >= 90% of the span's
  slots, else CH212's route B, CH212's route A (`clob_listed_k`) and CR9 are NaN.
- **Header pre-check** (before the census code is frozen; a header read, no rows): rows carry `received_utc`, `bid`, `ask`,
  `liquidity`, `volume24hr`, `event_id`; sidecars carry `page_index`, `received_utc`, `rewards_min_size`,
  `rewards_max_spread`, `clob_rewards`, `fee_category`, `order_price_min_tick_size`, `volume_num`, `competitive`; sweeps carry
  `depth_*_1c`, `depth_*_5c`, `best_bid`, `best_ask`, `bid_size_1`, `ask_size_1`, `n_*_levels`, `batch_receipt_utc`; feed
  records carry `condition_id`, `rewards_config` (with `rate_per_day` and start and end dates) and the band fields;
  manifests carry state and times. A missing field makes the dependent gate NaN. **Band unit check:** the median
  `rewards_max_spread` over carry-rewarded rows must lie in [0.5, 20] (cents); else every gate that uses `v` is NaN (no unit is
  guessed).

**Projection** = census count x 21 / covered days. **Distinct events:** distinct events over the covered days x 21 / covered
days (pessimistic) and, printed, LT8's generalised two-day form. **Effective counts** = units in markets with >= 2 units of
the test's population in the census days. **Design effect:** `DE_gate = max(floor, 1 + (m_21 - 1) x 0.02)`, floors **5.0**
(CH213, CH214, CH212) and **3.0** (CH215). **MDE gate formulas (multiplier 3.47), each `max(declared, design)`** with LT8's
definitions (*declared* = the closed formula at the census's own counts, `DE_gate`, `VIF_w`, gap and the declared SD;
*design* = `3.47 x 1.5 x SD x se_1` from the census regressors under a working covariance with unit variance, within-event
equicorrelation 0.02 and independence across events; no target read): CH213's interaction as section 2's formula with the
four census cell counts; CH214's slope at the census tercile gap; CH212's class contrast; CH215's event form. **F-MDE** =
`max(design-based MDE of Δ in the arm model, MDE x sqrt(2 / (1 - max(0, r_gate))))`, `r_gate = max(r_w, r_pool)` of the lead
and twin on census units with both (within-market on expanding-past demeaned values over markets with >= 3 such units;
pooled printed). SDs: `ds` and `dsw` 2c, `a` 3c, `Δs_e` 2c.

| Test | Census | Gate (all must hold; NaN fails) | Values fixed into the spec |
|---|---|---|---|
| CH213 | CC9 | finite reward status on >= 95% of non-sports ex-crypto eligible rows in band (pre-exclusion); band unit check; projected reward-panel units (all section 2 filters) >= 504,000 (>= 2,000 a capture) and control-panel units >= 504,000; control band coverage >= 70% of control units; **projected strict breaks >= 17,640 on each panel (>= 70 a capture)**; cap share >= 40% of reward-panel units in events with `n_members <= 10`; venue-clock gate: the most common slot of day holds <= 50% of reward-panel breaks; within `|corr(break x rew, z log1p liquidity)|` <= 0.5 and pooled <= 0.5; within `|corr(break x rew, om_k)|` <= 0.5; `VIF_w(break x rew)` <= 3.0; block-gate share >= 50% of units in markets with >= `ceil(16 x covered_days / 21)` units; **interaction MDE <= 1.0c**; F-MDE printed, `f_binding` = 1[F-MDE <= 1.0c] | control cell medians rule as declared (no value); `f_binding`; `exclude_family` |
| CH214 | CS9 | two-sweep coverage (passes k - 2, k - 1 two-sided on outcome 0, both band sums positive, received before capture k's start) >= 70% of carry-rewarded non-sports ex-crypto eligible markets in band; quiet share >= 50% of covered; band-unchanged share >= 80% of quiet covered; **projected primary units >= 252,000 (>= 1,000 a capture)**; cap share >= 40%; **identification (S18):** within-market IQR of the residual of `dD` after an OLS on `log D_{k-1}` >= 0.05 in >= 50% of markets with >= 6 units, and >= 30 such markets; `VIF_w(zdD)` <= 2.0; within `|corr(zdD, z dimb5)|`, `|corr(zdD, z own 24 h change)|`, `|corr(zdD, dvnum)|`, `|corr(zdD, ft_both)|`, `|corr(zdD, log rate)|` each <= 0.5; `|corr(zdD, log1p liquidity)|` <= 0.5 within and pooled; block-gate share >= 50%; `r_gate` <= 0.3 (on >= 5.0 covered days of pairs, >= 30 markets with >= 3 pairs); **slope MDE <= 1.0c; F-MDE <= 1.0c** | `zdD` (and lag) centre and scale; tercile cuts and gap; `exclude_family`; `p_vm` input (the `vnum_missing` share) |
| CH212 | CC9 | finite reward status as CH213; feed completeness; **switching markets >= 1,500 a day** (market-days with both a null and a listed status; descriptive count used as a gate, the round's kill line); projected route-A omitted units >= 60,480 (>= 240 a capture; route B: projected dropped units >= 15,120, >= 60 a capture); venue-clock gate: the most common slot of day holds <= 50% of omitted units; cap share >= 40%; within `|corr(om, log1p liquidity)|` <= 0.5 and pooled <= 0.5; within `|corr(om, |mid_k - mid_{k-1}|)|` <= 0.5; `VIF_w` of the tested term <= 2.0; block-gate share >= 50%; **the route rule of section 4 gives A or B**; **MDE of the chosen route <= its floor (0.5c A, 1.0c B)**; F-MDE printed, `f_binding` = 1[F-MDE <= floor] | `ch212.route`; `f_binding`; `exclude_family` |
| CH215 | CR9 | feed completeness; **projected qualifying ends >= 630 (>= 30 a day)**; projected distinct events of the ends >= 100; control availability: >= 70% of ends with >= 1 control (>= 3 printed); one-day share: no UTC day holds > 30% of ends; **MDE <= 1.0c** (`DE_gate` floor 3.0) | `ch215.entered` |

- **Descriptive (no gate):** every census prints the sports and crypto splits, the top series family's share, events and their
  21-day projections, the `n_members` distribution and the cap's loss, pairwise unit overlaps with the other LT9 populations
  and with LT8 CH203's and LT7 CH197's population definitions on the same days, class or tercile shares by liquidity tier,
  `vol_missing` and `vnum_missing` shares, and the computed DE beside `DE_gate`. **The reward field (CC9):** the null taxonomy;
  carry counts by lag (`_lag1`, `_lag2_3`, `_lag4_11`), `carried_param_differs`, `rewards_null_window_listed_inactive`; the
  carry-versus-feed agreement table (carry-rewarded x CLOB-listed, by day); the two-ledger map; CH212's route-rule inputs
  (both odds ratios with their strata counts, the page-position difference, the receipt-offset difference, the share of
  transitions with `clob_dropped`); omitted slots per switching market-day (1, 2, >= 3); omissions by slot of day; whether
  `rewards_min_size` / `rewards_max_spread` at omitted rows equal the source's (13.7's open question). **CH213:** the
  distribution of `s / 2v` on each panel; strict and LT7-style crossings a capture; the share broken at k - 1 given broken
  at k - 2 (the state's own persistence; no later slot); cell coverage by cell size; rates of broken markets. **CH214:** both
  band-sum proxies; `dD` distribution and within-market SD; the quiet and band-changed shares; `r_w` and `r_pool`; the yield
  terciles at k - 1 (no target). **CR9:** ends a day, their distance to the market's end, the share listed >= 48 h ahead, the
  share of ends moved between consecutive feed captures, sponsored shares.
- **Order (cheapest kill first):** CR9 (CH215: the feed only, tiny), then CC9 (CH212, CH213: captures, sidecars, feed), then
  CS9 (CH214: sweeps). A test whose census fails has its reader kind switched off before the reader's code freeze.
- **Expected census fates (declared now).** **CH212** is decided first by its route rule; "neither" is the challenger's reading
  and the likeliest single outcome; if it routes to A, its MDE gate needs about 240 omitted units a capture (the low planning
  end gives about 180). **CH213** needs about 70 strict breaks a capture on each panel; the low end gives 35. **CH214** passes
  its power gates easily; its identification (static farmers) and correlation gates are the risk, and after census its binding
  world 8 is expected to remove it. **CH215** is expected not to enter.

**Census jobs (to be drafted later under `docs/research_lab/queue/drafts/` in README format; ids from q0640 upward, checked
unused across `docs/research_lab/queue/` in the history of every local and remote-tracking ref on 2026-10-22: the ids used in
the q06xx range are q0600-q0604 and q0620-q0623, and LT8's text reserves q0624-q0627; none is written in this commit).**
- `q0640_lt9_census_restore` (lane `net`, about 2,000 MB disk, about 400 MB RAM): restore the span's files, check sha256s,
  write the restore report; bytes measured first (disk stop rule). `depends_on` LT8's last census (q0623) or its recorded
  drop, and the LT9 design-text freeze.
- `q0641_lt9_seal` (lane `net`, about 300 MB; after q0640): `run_live_tests9.py seal` writes `lt9_census_inputs.json`.
- `q0642_lt9_census_feed` (cpu, about 300 MB; after the seal commit): CR9 (CH215).
- `q0643_lt9_census_captures` (cpu, about 1,500 MB, **exclusive**; after q0642): CC9 (CH212, CH213), streaming per-capture with
  the 12-slot carry window per market.
- `q0644_lt9_census_sweeps` (cpu, about 1,200 MB, **exclusive**; after q0643): CS9 (CH214).
- `q0645_lt9_size_check` (cpu, about 800 MB; after q0642-q0644 and the census values committed, so k and CH215's entry are
  fixed before any size result exists; `max_retries 1` deterministic-crash only).
- `q0646_lt9_reader` (fallback only, never promoted while the cron line of 8.2 exists).
- `q0647_lt9_analysis` (cpu, about 3,500 MB, **exclusive**, `not_before` the analysis date).
All are DRAFT and must not be promoted before the challenger review, the design-text freeze, the code and its freeze check,
and **never while an LT7 or LT8 census, size-check or analysis job is running** (memory-heavy-jobs rule). Each counts 0.

## 8. Implementation plan (no code in this commit)

### 8.1 Modules to be written (engineering list)
- **Vendored, not imported.** `backend/astrolabe/research_lab/live_tests9_base.py` is **generated** by
  `backend/scripts/vendor_lt9_base.py`: unmodified copies of the LT3/LT4/LT5/LT7/LT8 functions LT9 uses (`series_frame`,
  `move_join`, `classify`, `category_cols`, `status_codes`, `is_late`, `token0_map`, `project_events`, `fit`, `attrition`,
  `lee_bounds`, `paper_taker`, `econ`, `block_anchor`, `de_gate`, `strata_of`, `block_fl_gate`, `holm`, `expanding_demean`,
  LT7's `RewardCarry` and `_status_array`, `rv24*` helper, lag-slot loader and seal reader, and LT8's sweep join and member-cap
  counter), each its source with only module prefixes removed. **Sources by hash:** LT7's from `live_tests7.py` sha256
  `e1c5c0c68f7c44d3d5038f9c28324008a4a8132e35f148721a33078d706766a0` (the carry erratum code, on which CC7 and CS7 are
  promoted) and `live_tests7_base.py` `2e8baa9007f60d4c7d3553932906e8e9bac60aa43f35368ba7f2c1ff498c7e20`; LT8's from the hash
  its census outputs (q0622-q0623) record, or, if they have not run when LT9's code is written, from the census-code-checked
  LT8 commit, re-verified against LT8's census outputs at LT9's freeze check (a mismatch: re-vendor before any LT9 census,
  never after). The vendor script refuses unless the source hashes equal those recorded; a `VENDORED` table records source
  file, source sha256 and normalised-source sha256; a unit test fails on drift unless `vendored_source_drift_accepted`
  records it; another proves no LT9 module imports `live_tests3*` .. `live_tests8*`. No frozen or registered module is edited
  (`live_tests3*` .. `live_tests8*`, `bounce_decomp`, the reward collector; nothing of E026).
- `backend/astrolabe/research_lab/live_tests9.py`: the reader and unit builders (`bandbreak_units`, `pool_units`,
  `rwblink_units`, `rwend_units`), the control-cell band rule, the feed reader (`feed_listed` per feed capture), the twin
  builders, and the counts-only censuses (`census_feed`, `census_captures`, `census_sweeps`). `run_once()` (internal
  non-blocking flock on `live_tests9/run.lock`) writes, write-once (`%.17g`, atomic hard link): `series/<capture>.csv.gz`,
  `status/<capture>.csv.gz`, `sweeps/<pass>.csv.gz`, `feed/<feed_capture>.csv.gz` (listed `condition_id`, band, rate, feed),
  frozen units `<kind>/frozen/<id>.csv.gz` for kinds `bandbreak`, `pool`, `rwblink`, `rwend`, outcomes
  `<kind>/outcomes/<id>.h<j>.csv.gz` and `.s<j>.csv.gz`, and `passes.jsonl`. **Look-back:** at install time `t` in
  `[REGISTERED_UTC - 72 h, REGISTERED_UTC - 24 h]`, `backfill-series` writes `lookback` lines for the 12 capture slots and 2
  passes before `REGISTERED_UTC` and every feed capture of the 26 h before it; `lookback` lines are never units; a slot found by
  neither the host nor a byte-identical release restore is `lookback_missing` (counted). CH215's 48 h pre-end span means its
  first qualifying ends fall about two days into the window (1.1).
- `backend/astrolabe/research_lab/live_tests9_analysis.py`: the single analysis (1.7-1.10, the F arms, the route, CH215's
  entry, Holm over k, counting) and the size check (1.8, 1.8.1) with the scenario-to-test map (fail-closed on an unknown or
  missing scenario; worlds 12 and 14 evaluated only when `ch215.entered` and CH213's `f_binding` say so).
- `backend/scripts/run_live_tests9.py`: `run`, `backfill-series`, `ops-stats`, `seal`, `census-feed`, `census-captures`,
  `census-sweeps`, `size-check`, `analyze`; censuses accept `--data-dumps-cap-gb` and exit 75 above it; `size-check` refuses
  `--worlds/--draws` without `--dev`; `analyze` refuses before the date, an unpinned, null or NaN spec, or a `k_tests` naming a
  dropped test.
- Spec `backend/astrolabe/research_lab/model_specs/live_tests9_v1.json`: every constant, k, `ch212.route`, `ch215.entered`,
  `f_binding`, seeds (estimators 20261191-94, gates 20261291-94, size check 20261197 and its derived seeds), dates, `T_X`
  rules, census scales and cuts, the carry rule keys, the cell rule, the member cap, the crypto classifier, the multiplier, the
  F rule, the `code_sha256` map and the imported sports-rule hash.
- `battery2.KIND_RULES["live_tests9"]` (fail-closed counting entry).

### 8.2 Resources, collection plan and install
- **No new collector and no network.** A pure reader of the pass's outputs and of the existing `reward_params` captures, once
  a pass. The feed reader holds one feed capture (about 14,000 records, under 1 MB compressed) at a time.
- **Memory (measured references, then a ladder).** LT4's measured host dry run 484-525 MB; LT8's planning 450-650 MB with an
  84-slot cache that LT9 does not need. LT9 holds per market the 12-slot carry texts (a few hundred bytes), the previous
  capture's spread and two sweeps' band sums. **Planning: peak 400-600 MB in a backlog pass, 300-450 MB steady (estimates).**
  Ladder, each step measured by a host dry run with the exact install command before the pin: (1) one reader, `--max-items 2`,
  column projection, under `ulimit -v 1572864`, accepted if peak RSS <= 650 MB; (2) else two readers (capture-side: CH213,
  CH212, CH215; sweep-side: CH214 and every sweep reading) serialised by one shared `flock`, each <= 650 MB; (3) else no pin and
  LT9 is not registered (recorded).
- **Install route: host cron** `15 */2 * * *` (104 minutes after each even-hour :31 capture start, after LT8's `5 */2` line,
  16 minutes before the next capture: before every freeze deadline of 1.3), own `flock`, `nice -n 19`, `oom_score_adj 1000`,
  `ulimit -v 1572864`. The queue draft q0646 is the fallback, **never both**.
- **Concurrency.** LT8's reader runs until its last targets (about 2027-01-21T00Z); LT9's from install (01-18..01-20). Two readers
  overlap for about three days, offset by 10 minutes, each under its own flock; peaks additive at most about 1.3 GB on the
  12 GB host.
- **CPU:** about 1-2 min a steady pass (estimate). **Disk:** about 1.5-2.5 GB over the window (CH213's two panels dominate);
  the reader stops writing at 3.0 GB in `live_tests9/`.
- **Analysis job:** about 4-6 million unit rows (CH213's two panels about 3-4 million); the block gate refits 200 times;
  planning 3-4 GB peak, **exclusive**, single run.
- **Host change:** installing the cron line is a host change under the standing collection authorisation, done by the
  orchestrator.

### 8.3 Tests to be written (`backend/tests/unit/test_research_lab_live_tests9.py`, synthetic only)
- **Reward status:** the vendored `RewardCarry` gives LT7's statuses on LT7's own synthetic cases (the 13.7 and erratum
  tests reproduced); a `null` cell read back as NaN is null; the source's band and minimum size are used; listed-inactive is 0;
  malformed and absent are NaN; nothing after the eligibility capture is read; `carry_lag` and `om_k` from it.
- **CH213:** `break` at its edges (`s_{k-1}` just below `2v`, `s_k` exactly `2v`); the control cell rule (>= 20, the fallback,
  uncovered); the cell median uses capture k only; `band_changed`; the interaction design matrix (`break x rew`, its
  interactions, `om_k`, `break x om_k`); the target `s_{k+1} - s_k`; the twin through the loader returns a flag only; the block
  gate never shifts a market's panel label; the boundary.
- **CH214:** band sums by the 1.5c rule; `dD`; the two quiet conditions; `band_changed` and `status_changed`; the decision time
  at sweep k - 1's receipt and the freeze before pass k's start (`.late` otherwise); the target on sweeps k and k + 1; the lag at
  k + 2, k + 3 through the sizes-only loader; `dimb5` equals LT8's definition on a shared fixture; `dvnum` with its flag; the
  boundary (`lt8_boundary`).
- **CH212:** `om_k` from the carry lag; `clob_listed_k` from the last usable feed capture finished before capture k's start (a
  failed feed capture is skipped, a missing one gives NaN); `clob_dropped_k`; the route rule on synthetic counts (A, B, both ->
  A, neither -> dropped); the Mantel-Haenszel odds ratio; the page position; a unit is never selected by a later capture of its
  day (a test plants a switch after k and shows the unit set unchanged).
- **CH215:** the 48 h knowledge rule; intention to treat at a moved end; controls from decision-time fields; the >= 8 of 12 rule;
  the sign-flip gate; `ch215.entered` false makes the analysis ignore every CH215 line and world 12.
- **Lag-slot loader:** a census reading a later slot receives only the named fields; a test plants wild prices in later slots and
  shows that no census output changes; CH213's twin path returns the break flag only.
- **Vendored base:** the `VENDORED` provenance check; no LT9 module imports `live_tests3*` .. `live_tests8*`; copied constants
  equal their sources.
- Shared: causality (future captures, sweeps and feed captures with wild values leave every frozen line byte-identical; sweep k
  with wild prices leaves CH213's and CH212's frozen lines unchanged); late refusal, write-once, dry-run guard, `%.17g` round
  trip, run lock; `ops-stats` reads no price, spread or depth column; the `code_sha256` map; counting equals k; Holm; the p = max
  rule and the `G_minor` df; F's two conditions, `f_binding` and the Inconclusive mapping; the analysis refusals; the
  design-freeze and `T_X` rules (registration refused when not before `T_LT7`); sealed censuses (counts only, slots from the
  seal, tampering refused, completeness, minimum covered days, feed completeness); each MDE and F-MDE gate formula with
  `max(declared, design)`; the band unit check; the scenario-to-test map (a failing scenario sets only its own tests to "SE
  check failed" with k unchanged; worlds 4r and the power runs never bind); `lookback` lines never become units; an end-to-end
  synthetic analysis with a reduced `k_tests`.

### 8.4 Registration steps and pins (in order)
1. Challenger R1 on this file; the response and any re-check. **At acceptance, and in any case before 2026-12-23T00:00Z, the
   engine embargo requests of section 9 are filed in `signal_engine/CANDIDATES.md` and applied** (not a registration step).
2. **Design-text freeze commit**, its sha256 in the ledger, before the earlier of 2026-11-14T12:00Z and `T_E015`.
3. Code (8.1, 8.3), vendored by hash; a `science-reviewer` freeze check of the census and size-check code against sections
   1.4.1, 1.8, 1.8.1 and 7; fixes (none may change frozen text).
4. q0640 restore, q0641 seal, seal committed and pulled on the host (after 2026-11-12T00:00Z, after LT8's last census or its
   recorded drop).
5. Censuses q0642-q0644 (counts only); drops and CH215's entry recorded in 6.3; `k_tests`, `ch212.route`, `ch215.entered`,
   `f_binding`, scales, cuts and `exclude_family` filled with the exact census floats; a freeze record written (module hashes,
   spec hash before the pin, census output hashes re-verified on the host, spec values checked against the census JSON).
6. Size check q0645 (2,000 worlds x 200 draws, seed 20261197); results recorded per test.
7. Reader freeze check; host dry run with the exact cron command following 8.2's ladder (the step used is recorded).
8. LT8's registration commit (or recorded drop) exists; the LT8 copies are re-verified against LT8's census outputs; the embargo
   entries applied at step 1 are verified in `config.EMBARGO` (a missing entry blocks the pin); any token or extension of a test
   dropped at census is withdrawn with a ledger line.
9. Pins: `SPEC_SHA256`, `code_sha256` map, `code_check` passing; E-numbers assigned from the ledger; the ledger entry is the
   registration commit, at least 24 h before `REGISTERED_UTC` and **before `T_LT7`**.
10. Install the cron line and run `backfill-series` within `[REGISTERED_UTC - 72 h, REGISTERED_UTC - 24 h]`; verify `pinned:
    true` and `nothing_new` before `REGISTERED_UTC`; queue q0647 with `not_before` the analysis date.

## 9. Signal-engine mapping and embargo requests

Every family below is point-in-time from the origin capture and its carry window, the sweeps of passes k - 2 and k - 1, or the
last `reward_params` capture before the origin (DESIGN_V1 16 causality). Each is an **auxiliary family** (own write-once table
and version string). **Embargo first** (DESIGN_V1 8): any challenger that isolates one of these families carries its token
until **the later of 2027-02-14T00:00Z and LT9's analysis commit** (the analysis date 2027-02-12T12:00Z plus about 36 h; if
LT9 takes LT8's slot under 1.1 (c'), the later of 2027-01-23T00:00Z and LT9's analysis commit). **Timing:** the requests are
filed in `signal_engine/CANDIDATES.md` and applied **when LT9's design is accepted, and in any case before
2026-12-23T00:00Z** (a month before `book` and `book0` lapse on 2027-01-23). This branch does not edit `CANDIDATES.md`, engine
code or `config.EMBARGO`. In the table, "LT9 date" means the later of 2027-02-14T00:00Z and LT9's analysis commit.

| Test | Family (aux version) | Columns (NaN = missing) | Source and clock | Token -> until |
|---|---|---|---|---|
| CH213 | `bandbreak` (`se-aux-bandbreak-v1`) | `bb_s_over_2v`, `bb_break`, `bb_in_band_lt7`, `bb_slots_since_break`, `bb_v_carry`, `bb_v_clob`, `bb_rate` | captures k - 1 and k, the carry window, the last feed capture before k | `bandbreak` (new) -> LT9 date |
| CH214 | `pool` (`se-aux-pool-v1`) | `pl_dD`, `pl_dDb`, `pl_dDa`, `pl_dlev`, `pl_dgrain`, `pl_yield0`, `pl_quiet` | sweep 1 of passes k - 2 and k - 1 (both before the origin), the carry window | `pool` (new) -> LT9 date; **`book0` and `book` -> LT9 date (from 2027-01-23), only if CH214 survives census**; `quietbook` respected as applied (to the later of 2027-01-23 and LT8's analysis commit) |
| CH212 | `rwblink` (`se-aux-rwblink-v1`) | `rb_om`, `rb_om_lag`, `rb_om_run`, `rb_clob_listed`, `rb_disagree`, `rb_page`, `rb_recv_offset_s` | the sidecar's carry window and the last feed capture before the origin | `rwblink` (new) -> LT9 date |
| CH215 | `rwend` (`se-aux-rwend-v1`) | `re_h_to_end`, `re_distinct`, `re_rate`, `re_sponsored` | the last feed capture before the origin | `rwend` (new) -> LT9 date, **requested only if CH215 enters**; otherwise the family is built without a token |

**Requests to the signal-engine track (this branch does not edit engine code; `config.EMBARGO` is not edited here).**
- **New tokens `bandbreak`, `pool`, `rwblink`** (and `rwend` only on CH215's entry) to the LT9 date, entered at acceptance
  (and before 2026-12-23) and before any isolating challenger is scored. The round-14 families may be built at once under
  these tokens; no isolating `pool` challenger is scored before LT8's `quietbook` date in any case.
- **`book0` and `book` from 2027-01-23 to the LT9 date, conditional on CH214's census.** A model isolating `book0` and `book`
  can form the two-sweep band-sum innovation; cost, disclosed: the book families (se3, se14, se19) stay hidden about 22 more
  days. If CH214 drops at census, this extension is withdrawn with a ledger line.
- **`rewards` is not extended** (it stays at the later of 2026-11-18 and E022's analysis commit). Reason and cost: extending it
  to February would hide se9 for about three more months; se9 reads the field at the origin only (an omission looks to it like
  "no programme") and holds the band but not `s_{k-1}`. In its place, **attribution limits:** no attribution (SHAP or
  otherwise) of the champion, se9 or any broad model on spread x `rewards_max_spread` interactions, on the history of the
  field's presence, or on two-sweep band-sum differences, computed or shown before the LT9 date; no LT9 family added to a broad
  model before then, or such a model recorded in the ledger as a development look. Put to R1 (question 9).
- **Not requested:** `surprise`, `movetype`, `participation` (CH213's one-sided flag and CH212's slot dummies are controls).
- If a test drops at its census, its new token and any extension made only for it are withdrawn with a ledger line (dates move
  earlier only by that withdrawal).

The engine's yardstick (log-loss gain under `se-promotion-v2`) is a different question from each LT9 primary. A Supported LT9
primary makes its family a candidate; an engine gain never changes an LT9 verdict and an LT9 verdict never promotes a model.

## 10. Disclosures

- **Selection history.** The three tests are round 14's ranks 1-3 (creative-lead pass written 2026-10-22 on `af960b80`, from
  the ledger, the LT7 reward probes and rulings, LT8 sections 0-1 and 7, and named documents, with no host probe), taken in the
  round's own recommendation; CH215 is its rank 4 with the round's "added only on its count", made an explicit entry rule.
  Every design change (6.1) was made before any data.
- **The designer** read, on 2026-10-22: `CLAUDE.md`, `AGENTS.md`; `CREATIVE_HYPOTHESES_2026-10-28.md` (sections 0, 0.1, 0.2, the
  structural facts and counts table, 1, 2.A, 3); `LIVE_TESTS_8.md` (all sections, including 13 and 13.6); `LIVE_TESTS_7.md`
  (headings, 1.1, 13.6, 13.7 and its erratum); the ledger by bounded read (the E022 registration through the LT7 13.7 entry and
  the tail); `signal_engine/CANDIDATES.md` and `config.EMBARGO` by bounded grep (`rewards`, `book0`, `quietbook`, `swclock`);
  `reward_params_collector.py`'s docstring and `test_reward_params_collector.py`'s field names; `MAKER_REWARDS_STUDY.md` 6.1;
  `ext_sidecar.py`'s key lists; `DEPENDENCE_CLUSTERING_ANALYSIS.md`'s fixture-day group definitions; the `retention` comment
  of `scripts/oracle/archive_retention.json`; the file names under `seals/` and `reviews/` (no content of any seal); the
  sha256 of `live_tests7.py` and `live_tests7_base.py` in the worktree; the queue-id history across all refs. **Known to the
  designer before drafting:** the q0601b and q0601c counts (null share 0.60-0.65 a day, switching 30,543 of 258,393 market-days,
  2,112-3,995 switching markets a day, listed rows 94,624-117,710 a day) as the round and LT7 13.6 / 13.7 quote them; LT5's, LT6's
  and LT4's census counts as round 14 0.1 tabulates them; LT8's planning figures. **Not read:** any LT7 or LT8 census output (none
  is committed), any E015, E022 or LT7 analysis output, any data, host, outcome, price after an origin, P&L, `data-dumps` file or
  evidence JSON. No threshold was chosen from data.
- **Adjacencies the round names, as designed here.** (1) **CH214 and LT8's CH203 (`quietbook`):** same sweeps, same quiet
  shape, the symmetric against the asymmetric part; not orthogonal by construction (6.1 item 9); disjoint windows; `z dimb5` a
  control and a correlation gate; `quietbook` respected. (2) **CH212 and CH213 and E022's S2 (reward split):** the same field;
  freeze before `T_E022` or *informed (E022)*; the `rewards` token untouched. (3) **CH212 and LT7's carry rule:** CH212's state
  is the rule's carry lag (1.4.1); no reclassification; pin before `T_LT7` or every test dropped.
- **LT8's reward control differs from LT9's** (1.4.1): LT8's frozen k-only parse predates 13.7; LT9 neither edits nor relies on it.
- **The round's figures are not LT9's.** CH213's interaction 0.99c / 0.55c became 1.39c / 0.62c (the band, the cap, the panel
  arithmetic); CH214's 0.14c / 0.18c became 0.28c / 0.19c (the cap, the stricter quiet filter, target coverage); CH212's route
  A 0.35c became 0.58c / 0.35c (the band, the cap, the CLOB filter); CH215's 1.9c / 0.78c became 2.23c / 0.92c (recomputed). The
  prior odds of section 0 are the designer's: census 0.35, 0.35, 0.30, 0.10 (the round's 0.40, 0.35, 0.30, 0.10).
- **F can reject a true but persistent signal** (CH214, and CH213 or CH212 where F binds); accepted (LT7 10, LT8 10).
- **Route A's scope.** A Supported CH212 route A is a fact about the display, not about CLOB prices (section 4).
- **Retention dependency.** The census needs a byte-identical release restore of the span's first days (snapshot retention
  8-10 days); the look-back needs 12 slots at install (8.1). `reward_params/` has no retention rule; no LT9 rule deletes it.
- **Shared data.** Every earlier test and the engine read the same captures, sweeps and feed; LT9's window overlaps none of
  theirs; its first-day look-back reads raw captures that are inputs of LT8's last targets (1.1).
- **Window.** Results arrive about 2027-02-12, after every adjacent analysis; the reasons and the declined fast lane are in 1.1.

### 10.1 Values declared now and their planning sources (all before any census)

| Value | Where | Source |
|---|---|---|
| Carry-rewarded non-sports ex-crypto markets a capture 10,000 / 12,000 | 2, 3, 4 | the probe's 9,000-10,700 listed market-captures a capture and the ruling's ~9.7k (round 14 fact 2; LT7 13.7), plus carried omitted rows (~3,000 switchers a day); planning |
| Unrewarded non-sports ex-crypto markets 15,000-20,000 a capture | 2 | round 14 fact 1 (about 30,000 non-sports eligible) minus the reward panel and crypto; planning |
| Mid-band share 0.70 ([0.10, 0.90]) and 0.85 ([0.05, 0.95]) | 2, 3, 4 | LT8 2's planning 70% for [0.07, 0.93] (optimistic here, disclosed); 0.85 a convention |
| Cap share 0.50 / 0.70 | 2, 3, 4 | LT8 2's planning 50% (unprobed); round 14 notes rewarded ladders, hence the low end |
| Strict-break rate 1% / 3% a capture | 2 | round 14 CH213 (unprobed) |
| Two-sweep coverage 0.86; quiet 0.60 / 0.75; band unchanged 0.95; target sweeps two-sided 0.90 | 3 | `book0` coverage 0.92-0.94 squared (DESIGN_V1 22 via round 14 fact 4); round 14's 0.75 quiet share for the mid alone; round 14's 20% band-change kill line; a convention |
| Switching markets 3,000 / 3,500 a day; omitted slots 2 / 3 per switching market-day; CLOB-confirmed 0.85 / 0.95; route-B share 0.30 / 0.50 | 4 | the probe (2,112-3,995); round 14's planning 2 (unprobed); conventions; the route rule's 30% line |
| Listed comparison units 160,000 / 450,000 | 4 | round 14's 450,000 listed slots on switching days, the low end scaled by band and cap |
| SDs: `ds`, `dsw`, `Δs_e` 2c; `a` 3c | 2-5 | round 14's planning arithmetic (spread change 2c, |2 h move| 3c) |
| `VIF_w` 2.0 (CH213 interaction), 1.5 (CH214), 1.3 (CH212, CH215) | 2-5 | round 14 (1.3 labels, 1.5 book states); 2.0 a declared convention |
| DE 31 / 51, census floors 5.0 and 3.0 | 0, 7 | round 14 rule 7; LT8 7 |
| Floors 1.0c (spread) and 0.5c (magnitude) | 1.9 | round 14 rule 8 |
| Count gates: 70 breaks a capture per panel; 1,000 CH214 units a capture; 240 route-A (60 route-B) units a capture; 30 ends a day | 7 | the counts at which each MDE gate passes at the low panel size (sections 2-5); CH214's a declared floor; CH215's the round's kill line |
| Control cell rule (>= 20 units; tier cuts $1k, $10k, $100k) | 2 | the cost model's liquidity tiers; 20 a convention |
| Route rule (odds ratios >= 1.5; page position >= 0.10; >= 30% matched) | 4 | round 14 CH212's declared rule, made a within-market and Mantel-Haenszel form |
| World parameters (1.8.1) and `p_vm` floor 0.50 | 1.8.1 | conventions, not measurements; LT8's 0.78 floor was for `volume24hr`; `volume_num`'s presence is unprobed |
| Seeds 20261191-94, 20261291-94, 20261197 | 2-5, 1.8 | new (unused in docs and code on 2026-10-22) |
| Census span 2026-11-02..11-12 | 7 | winter time on both sides, after LT7's censuses, before the freeze deadline's seal |

## 11. What the challenger (science-reviewer R1) should attack

1. **CH212's population and route rule.** Is `om_k = 1[carry_lag_k >= 1]` on the carry-rewarded panel the right causal form of
   "a switching market-day"? Is restricting route A to `clob_listed_k = 1` (a feed capture about two hours old) a selection
   on something the omission itself causes? Are the route thresholds (1.5, 0.10, 30%) and "both -> A" defensible before data?
2. **Whether CH212 contradicts LT7 13.7.** 1.4.1 claims it does not (the state is the rule's own carry lag; no status
   changes). Is the carry-versus-feed agreement print a de facto re-test of LT7's control, and is "descriptive, never re-opens
   LT7" enough?
3. **CH213's control panel.** The cell-median band (category x tier x tick at capture k), the >= 20 rule, carry-unrewarded
   controls that may hold hidden programmes (conservative?), and whether `break x` liquidity, tick and level interactions with
   `om_k` controls are enough to make the interaction "beyond ordinary reversion". Should world 3 be binding?
4. **CH213's stale-display channel** (world 4 binding, 4r reported): is an unobserved staleness differential between listed
   reward-panel rows and control rows plausible enough that 4r should bind?
5. **CH214's sweep target and decision time** (6.1 item 7): does moving the decision to sweep k - 1's receipt and the target to
   sweeps k -> k + 1 remove the catch-up threat, and does it change the hypothesis?
6. **CH214's fill confounder** (same-signed; `dvnum`, the silent arm, world 8 at `p_vm >= 0.50`): is 0.50 a defensible floor
   when `volume_num`'s presence is unprobed? Should the primary be the arrival-side slope S2?
7. **CH214's band proxy** (1c sums if `v <= 1.5c`, else 5c) and the `z dimb5` control: does holding CH203's state fixed make
   CH214 a cleaner or a weaker test, and is the correlation gate (<= 0.5) the right adjacency rule?
8. **F binding by census F-MDE** (`f_binding`) for CH213 and CH212: a count-based switch of a verdict condition. LT8 6.1 item 8d
   avoided census-conditional verdict switches; is this one acceptable?
9. **Embargo:** no `rewards` extension, attribution limits instead; `book0` / `book` extended to the LT9 date only if CH214
   survives. Enough?
10. **Window and timing:** the ordered lane with the fast lane declined; the freeze deadline (11-14T12Z) against a census span
    ending 11-12; "every test dropped if the pin is not before `T_LT7`".
11. **CH215's entry rule:** k may grow to 4 from counts alone; is a fourth primary admitted at census a forking path, and is the
    event-time design (intention to treat, decision-time controls) sound?
12. **Arithmetic:** every MDE in sections 0 and 2-5 and the counts at which the gates pass (recomputable from 10.1).

## 12. Open questions for the challenger review

1. CH212: should the omitted class require the field to be listed at k - 1 (a fresh omission) rather than any carry lag >= 1?
2. CH212: is route A's target `|mid_{k+1} - mid_k|` right for a catch-up, or should the signed catch-up (M2) be primary?
3. CH213: strict break `s >= 2v` against LT7's `in_band` flip (S2): which is the right crossing for the scoring rule?
4. CH213: should the main effect within the reward panel (power 0.79c / 0.36c) be the primary and the interaction a label?
5. CH214: target over one pass (`sws_{k+1} - sws_k`) or the skip `sws_{k+3} - sws_{k+1}` (LT8's convention)?
6. CH214: count gate 1,000 units a capture against the round's 3,000; acceptable given that the MDE gate binds?
7. All: the mid band [0.10, 0.90] for the reward-rule tests (the scoring rule's wording is unverified; 0.2 rule 11).
8. All: the member cap <= 10 on the reward panel (rewarded ladders are common); is DE 31 the right planning value?
9. All: the census span 2026-11-02..11-12 (inside E022's window, counts only) and the restore of its first days from releases.
10. The 0.50 floor for world 8's `p_vm`, and worlds 3 and 11's parameters as conventions.
11. CH215: the 48 h knowledge rule and the > 48 h distance from the market's end; DE 3.0.
12. Multiplier 3.47 kept for k <= 4.

## 13. Draft ledger block (DRAFT, not registered, not counted)

> ## LT9 (three round-14 candidates: CH213, CH214, CH212; CH215 optional) — DRAFT pre-registration (not registered, nothing counted, no code)
> - **Design:** `docs/research_lab/LIVE_TESTS_9.md` on `feat/live-tests-9`. Pure reader of streams the host already writes
>   (complete captures, sidecar, sweep 1 of each pass, the existing `reward_params` captures); no network, no new collector;
>   separate store `live_tests9/`; LT3/LT4/LT5/LT7/LT8 functions vendored by hash (LT7's carry code `e1c5c0c6…`).
> - **Reward status:** `listed_carry24h_v2` (LT7 13.7) for every control and panel; CH212's state is the rule's carry lag.
> - **CH213** the band break: Gamma spread change over (k, k + 1] after a strict break (`s_{k-1} < 2v <= s_k`), reward panel
>   against a control panel with a cell-median band; interaction MDE 1.39c / 0.62c (floor 1.0c; needs ~68 breaks a capture).
> - **CH214** the pool splits: CLOB spread change from sweep k to k + 1 on the symmetric in-band depth innovation between
>   sweeps k - 2 and k - 1 behind an unmoved touch; slope MDE 0.28c / 0.19c; F binding; fill leak world likely to fail.
> - **CH212** the omission: route A |mid move| after an omitted row the CLOB confirms (MDE 0.58c / 0.35c, floor 0.5c) or route
>   B (real churn), fixed by a counts-only route rule; "neither" drops it.
> - **CH215** optional fourth, entered only if every CR9 count gate passes (~51 ends a day needed).
> - **Family:** Holm over k <= 3 (4 with CH215), one-sided, alpha 0.05; block FL gates; 14 size scenarios (leak worlds 3, 4, 8,
>   11); window proposed `[2027-01-21T00:00Z, 2027-02-11T00:00Z)` keyed to LT8's `END_UTC` + 24 h, single analysis on or after
>   2027-02-12T12:00Z; freeze before the earlier of 2026-11-14T12:00Z and `T_E015`; pin before `T_LT7` or every test dropped;
>   census on a fresh seal 2026-11-02..11-12 (q0640-q0644). Tokens `bandbreak`, `pool`, `rwblink` (and `rwend` on entry) to the
>   later of 2027-02-14 and LT9's analysis commit; `book0` / `book` extended only if CH214 survives. **E-numbers not assigned.**
