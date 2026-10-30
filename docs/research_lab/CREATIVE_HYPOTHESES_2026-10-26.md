# Creative hypotheses, round 12: whole-panel states that survive the census (2026-10-26)

`evidence_role: none` | status: **IDEAS ONLY, nothing tested, nothing registered.** No edge, calibration, tradability or
profitability claim. AREPO never trades; every "money route" below is a paper rule to be tested on historical data and
then prospectively. Written by the creative-lead pass at the user's request (written 2026-10-21, on parent `fa856ec4`
(`chore/arepo-claude-setup`), worktree `feat/creative-r12`; the file carries the round's planned date as earlier rounds
did). Round 1 is `CREATIVE_HYPOTHESES_2026-10-15.md` (CH01-CH34), round 2 `-16.md` (CH35-CH59), round 3 `-17.md`
(CH60-CH78), round 4 `-18.md` (CH79-CH98), round 5 `-19.md` (CH99-CH117), round 6 `-20.md` (CH118-CH130), round 7 `-21.md`
(CH131-CH143), round 8 `-22.md` (CH144-CH155), round 9 `-23.md` (CH156-CH168), round 10 `-24.md` (CH169-CH179), round 11
`-25.md` (CH180-CH190); this file starts at **CH191** and repeats none of them. Where an idea builds on an earlier one,
the parent is named and the new mechanism, clock, population or join is stated. Every number quoted from an AREPO
document is a development, census or probe result, not evidence. One file; no code, no queue specs, no other commits.
**No network request, no host probe (no `ssh oracle`) and no `data-dumps` read were used for this round** (by
instruction); every count below is taken from a named AREPO document (the ledger's LT4 censuses, LT3's censuses, round
9's probes, the signal-engine design notes, the cost-model calibration, the maker-rewards snapshot, the new-streams dry
run) and is named as such. Where no count exists the entry is marked **unprobed** and the pre-registration census is the
first gate.

## 0. How to read this file

**The brief that binds this round (owner priorities, 2026-10-19, 10-21; orchestrator brief for round 12).** The
binding lesson of the last 48 hours is that ideas die at the pre-registration census, not at the analysis: populations
are too small, strata are not permutable, or the planning MDE misses the floor. So every idea here states, before its
mechanism is argued, (1) a **population arithmetic**: units a day and distinct events in 21 days from a cited AREPO
count, else "unprobed"; (2) a **permutation and cluster structure** that is plausibly permutable within market x UTC
day or market x two-day block strata (>= 4 units in >= 50% of strata, the LT4/LT5/LT6 gate), with the size scenario it
would bind; (3) a **planning MDE** against a cost-aware floor, computed with LT5/LT6's pessimistic formula. The owner
wants original mechanisms (how a taker or a maker could make money after costs, about 5c per dollar round trip for a
taker at the median, maker rewards where relevant), not textbook re-tests; category-agnostic, category as a parameter
(sports inclusion is the owner's later call); and every idea expressed as a point-in-time **signal-engine feature
family** for a challenger (`signal_engine/NORTH_STAR.md`, `DESIGN_V1.md` sections 3, 8, 16, 18). This round's family is
**LT7**, registered after LT6.

**What changed since round 11 (from the ledger entries of 2026-10-20/21, `LIVE_TESTS_4.md` section 17,
`LIVE_TESTS_5.md`, `LIVE_TESTS_6.md`, `CREATIVE_BATCH_18.md` sections 0, 3, 14, `seals/cb18_routing.json`,
`signal_engine/DESIGN_V1.md`, `CANDIDATES.md`, `AREPO_V2_CHECKPOINT.md`).**
- **LT4 is E022 only.** The censuses q0482/q0483 (2026-10-21 17:26Z / 17:38Z; counts only) dropped **E020** (projected
  cancellations 14,028 < 15,000; permutable-strata share 0.055 by market x day / 0.132 by two-day block < 0.50;
  pessimistic MDE 0.526c > 0.5c) and **E021** (strata 0.005 / 0.018; MDE 1.060c, even with 44,919 projected clocked
  units) and passed **E022** (18,517 covered traded non-sports movers in two days, 2,539 events; strata 0.446 / 0.599,
  `perm_stratum = block2`; tercile MDE 0.256c). Registration by 2026-10-25T00:00Z for the 10-26 .. 11-16 window.
- **LT3 is E015 only, REGISTERED 2026-10-21** (window 10-24 .. 11-14, analysis not before 11-15T12Z).
- **LT5 (J, F, O, H, R = CH180, CH184, CH182, CH181, CH183) is DRAFT**, R1 and re-check answered, census code merged,
  seal q0564 and censuses q0561-q0563 due the night of 10-21/22; provisional E027-E031; window 10-30 .. 11-20. Its own
  summary declares H and R "likely to drop", J and O "borderline".
- **LT6 (V, K, D, B = CH190, CH185, CH187, CH188) is DRAFT**, accepted for code (R1 REVISE, re-check incomplete,
  fixed); window 11-16 .. 12-07 keyed to E022's `END_UTC`; D "very likely to drop" (the gamma-rules churn probe saw 3
  changed keys in 25 h).
- **CB13-R, CB14-W, CB15-P, CB18 are closed.** CB13-R: GR basis 0.915 < 0.95, frame completeness 0.782 < 0.98, events
  58 < 60, GRP MDE 0.658c > 0.60 (R1 "not testable (basis)", p = 1). CB14-W: 58 markets < 150, 46 events < 60, 38
  subjects < 40. CB15-P: 37 pairs in 12 events against 60 in 30. CB18 routing (`seals/cb18_routing.json`,
  `cb18-rules-v1`): CB18-S (CH177) RS-0 (GS2, GS4, GS5 fail; planning MDE RS-1 3.64c, RS-2 1.37c), CB18-P (CH172)
  dropped (GP1, GP5, GP6 fail); R, F, M are maps; **k = 0**.
- **SB2-J4-R is VOID** (placebo failure on P3 and P4: regressors built from levels gave a mechanical slope; 5 tests
  counted, no verdict).
- **E026 (copy skilled wallets) REGISTERED 2026-10-21** (k = 2; collection 10-25 .. 11-15; single analysis on or after
  12-06T12Z; five modules and two specs frozen to 12-07). Its census: 2,230 skilled signals a day, 650 events at
  L = 0, two-way design effect 23.9, MDE 0.102 $/$ two-way against a 0.03 floor ("likely Inconclusive").
- **Signal engine:** deployed on the host (per-pass tick); first prospective leaderboard 2026-10-21 15:38Z (one day:
  se1 +0.049 nats over the champion; a pipeline check, not evidence); development walk-forward se1 +0.041, se7 +0.046
  nats on `dir_2h`; aux families `event`, `rewards`, `movetype`, `surprise`, `participation`; `se17_lgbm_mm_900k`
  (+0.0027 nats in development, selected from four); the `regime` family (capture-level activity) was **worse** and was
  dropped; embargo table in DESIGN_V1 section 8 (`book` to 12-09, `flow`/`rewards`/`event`/`movetype` to 11-22,
  `surprise` 11-19, `participation` 11-25, `wallet`/`wallet_skill` 12-07, `vote`/`clips`/`deadline`/`siblings` 12-09).
- **Streams:** the checkpoint's interactive state (2026-10-21 ~09:50Z) records "New streams live: PredictIt, Smarkets,
  ESPN odds, gamma rules, reward params", and DESIGN_V1 section 16 dates the `reward_params` stream from
  2026-10-20T23:20Z; the repo's `scripts/oracle/streams_crontab.txt` is still commented, so the install was by hand.
  Nothing here depends on them as an LT7 primary (section 0.1 lesson 3); they appear as engine-first families.
- **Host:** resize to 2 OCPU / 12 GB scheduled 2026-10-22 02:40Z (one restart; the gap is a deviation, never backfilled).

### 0.1 What round 12 learned from the LT4 censuses, CB13/14/15/18 and J4-R (the design rules of this file)

1. **A count is not a population; recurrence within the market is the gate.** E021 projected 44,919 clocked units and
   died at a strata share of 0.005: a trade-sample unit (2,000 markets a pass, rotating) almost never recurs in the same
   market four times in a day or a two-day block. E020's one-sided quote-only movers (4,566 in two days) recur at 0.055.
   E022's traded movers on the full sweep panel (18,517 in two days) recur at 0.446 / 0.599, barely over the line.
   **Rule: no LT7 primary has a trade-sample unit; every LT7 state is defined on the capture, sweep and sidecar panel,
   where every eligible market yields 12 units a day and a market-day stratum holds up to 12 units by construction.
   Mover populations are the floor of what passes (E022); all-unit populations with a continuous state are the design
   target.** (LT5 J and O carry E021's risk; their censuses were pending when this was written. CH191 is J's fallback.)
2. **The planning MDE dies on effective counts, not raw counts.** E020's `A_eff` 9,712 against a raw 18,070; E021's
   `fresh_eff` 3,885. LT5/LT6 count only units in markets with >= 2 units of the population in the census days and
   inflate by `DE_gate >= 3`, the 1.5 factor and `sqrt(VIF_w)`. **Rule: every MDE here uses that formula (section 0,
   "Planning-MDE arithmetic") and reaches the 0.5c floor with a quarter of the planned units.**
3. **External frames and cross-venue pairs are tens, not thousands.** CB13-R's frame completeness 0.782 and 58 events,
   CB14-W's 58 markets and 46 events, CB15-P's 37 pairs in 12 events. **Rule: nothing here is anchored to an external
   frame; PredictIt (867 keys), Smarkets (677 books), ESPN odds (94 games) and the Kalshi pairs (116) are engine-first
   families at most, never an LT7 primary.**
4. **Field semantics and signed-flow reactions die at the census.** CB18-S: `updated_at` is a tick clock (GS2 fail).
   CB18-P: fades 2,000 short in 28 days (GP1) and the permutable share fails (GP6). **Rule: no idea reads a field whose
   semantics are unknown, and the sign of every primary comes from the capture's own mid move, a fold, or a mechanical
   rule on the capture's own fields; the Data API `side` appears nowhere.**
5. **A placebo whose null is mechanical by construction is a verdict condition, not a diagnostic.** J4-R was VOID
   because P3/P4's regressors were built from levels and the pooled placebo showed a slope of its own. **Rule: every state
   built from levels (a book, a volume, a spread) carries a declared falsification arm whose contrast must be null under
   the mechanical story: the far-future control (the same state read from the interval after the target), the away-side
   control (the unhit side of the book), or the fake mark; it is part of the verdict rule.**
6. **Few clusters leave a passing census underpowered.** E026 passed G1-G3 with 650 events and a two-way design effect
   of 23.9, and its MDE (0.102 $/$) sits far above its floor. **Rule: event counts are stated per idea; the targets are
   populations with thousands of events (E022: 2,539 in two days; J4-R: 33,849 event clusters in five days over the
   whole universe).**
7. **Targets start after the decision time; slow states take daily units; flow moderation needs the block gate.** LT5
   R1 moved J's and O's targets to k + 1, gave H one unit per market per UTC day with market strata, gave O the
   circular-shift Freedman-Lane gate, and added liquidity-tier correlation gates (|corr| <= 0.5 within and pooled). LT6
   R1 added the few-treated-cluster event t, `sqrt(VIF_w)` in every MDE gate and the depletion-asymmetry gate. **Adopted
   wholesale: skip targets (k + 1 to k + 3) for every move-continuation primary; one unit per market-day for 24 h
   targets; the plain Freedman-Lane gate only for per-interval labels and non-rolling states, with the AR(0.9) size
   scenarios binding.**
8. **Capture-level constants overfit and category-wide states carry nothing.** The engine's `regime` family (about 12
   distinct values a day) was worse than the learner-matched baseline on every target and was dropped; CH158 died the
   same way. **Rule: every engine family here varies per market and per capture; it is read against `se1_lgbm_mm`
   (learner-matched), never only against the champion; nothing is a venue clock.**
9. **Pin early, run late.** LT6 pins V before `T_E022` so that E022's analysis cannot inform it. E015 (11-15) and E022
   (11-17) will be analysed before any LT7 window opens. **Rule: LT7's states, estimators and gates are pinned before
   2026-11-15T12:00Z if the designer wants "fresh"; a pin after that date must disclose which E015/E022 numbers were
   seen, and a state adjacent to theirs (CH194 next to E015's anatomy, CH195 next to E022's depth) is then "informed".**

**Structural facts this round relies on (counts only; sources named; no new probe).**
1. Eligible markets a capture (engine base eligibility: binary, open, active, two-sided, spread <= 0.10, mid in
   [0.02, 0.98], no UMA proposal): 46,448 (2026-10-20 20:31Z), 42,161 and 49,569 (10-21 12:31Z), 51,790 (10-21 14:31Z)
   (DESIGN_V1 sections 3 and 16). Non-sports share of eligible markets: **unprobed** (sports are 31-36% of mover
   populations: E020's 2,015 of 6,581 one-sided, E021's 0.360), so "about two thirds" is a derived planning figure.
2. Movers: 77,732 >= 1c a day over 584,022 eligible market-interval pairs (P1, 2026-10-15); non-sports about 2,750 an
   interval, 60% quote-only, 27% traded, 13% never-traded (P1b); traded non-sports about 8,900 a day; E022's census:
   18,517 sweep-covered traded non-sports movers in two days, 2,539 events, sweep coverage 0.9996.
3. Move anatomy on the engine's clock (10-21 12:31Z, 49,569 eligible, 4,244 movers): traded 30%, ambiguous 4%,
   parallel 4.4%, one-sided 5.4%, spread-change 1.5%; Gamma omits `last_trade_price` on 56% and `volume24hr` on 78%
   of rows; `mt_never` (no last trade at either end) 72% of markets; `mt_db` defined for 92% (DESIGN_V1 section 16).
4. Sweeps: 65,771 tokens a sweep, two sweeps a pass about two minutes apart, sweep 1 about 8 minutes after the capture;
   one token per market; `best_bid/ask`, `*_size_1`, `depth_*_1c/5c`, `n_*_levels`, `book_timestamp`, `tick_size`,
   `min_order_size`; book coverage 98% of eligible markets (round 9; LT4 17.3; DESIGN_V1 section 3). E022's
   `L >= D` superset share 0.913; L/D quantiles 1.09, 2.56, 7.39, 23.7, 74.4 (10/25/50/75/90%).
5. Own-path coverage from the engine's `quotes/` (10-21 12:31Z): `sp_rv6h` 98%, `sp_rv3d` 85%, `sp_rv7d` 78%.
6. Sidecar per capture: `fee_type`, `fee_category`, `order_price_min_tick_size`, `rewards_min_size`,
   `rewards_max_spread`, `clob_rewards`, `created_at`, `uma_resolution_statuses`, `event_*`, `competitive`,
   `series_slugs`, `parent_event_ids`; capture rows: `end_date`, `updated_at`, `neg_risk`, `event_id`, `liquidity`,
   `volume24hr`, `chg_1h/1d/1w`, `last_trade_price`. Rewards: 13,683 rewarded markets (snapshot 2026-10-20); 5.2% of
   markets with a programme on 10-21; one-sided scoring inside [0.10, 0.90], two-sided outside.
7. Event clusters: 33,849 event clusters over 2,581,045 triples in five UTC days (SB2-J4-R run, whole universe); E022's
   2,539 events in two days. LT3's 21-day projection rule: `E_2d + (E_2d - E_day1) x 19`; `E_day1` is not recorded for
   E022, so the 21-day event count is **unprobed** with a lower bound of 2,539.
8. Costs (cost-model-v1, calibration 2026-10-16 to 10-19): a $100 taker round trip 2.9c at >= $100k liquidity, 3.9c at
   10k-100k, 7.2c at 1k-10k; a 5-share touch round trip 4.5c; a passive touch order fills 3.1% of the time within an
   hour and loses 2.38c to adverse selection against a 2 h mark (0.39c at >= $100k); hold-to-resolution removes the
   exit leg. Makers are about break-even before rewards (non-sports fill-weighted -0.37c).
9. Streams (dry run 2026-10-19): PredictIt 867 keys; Smarkets 1,734 keys, 677 books; ESPN 94 games (76 with odds);
   gamma_rules 3,799 keys in the top-3,000 frame, 3 changed keys in 25 h, 2,383 new keys a day; `reward_params` every
   2 h since 10-20T23:20Z. Monitor: 10,522 prints >= $1k on 2026-10-15 (22% non-sports), median 9 minutes late.
10. Engine (development, 10-14 .. 10-20): se1 +0.0408 [0.0401, 0.0416] nats over the champion on `dir_2h`; a 900k-row
    frame adds +0.0021; the LightGBM `res_7d` fits begin once label receipts precede the inner split (about 10-28).

**The reading that steers this round.** Rounds 9-11 read the streams for what they record, name and remember. Round
12 reads them for **what every market shows at every capture**: the shape of its own last six hours (CH191), the hour
inside the interval in which its move happened (CH194), the resting depth its move had to go through (CH195), the book
behind its touch (CH197), the volume it absorbed without moving (CH193), and the uncertainty its makers quote against
the uncertainty its path has shown (CH192). Each is a continuous state on the whole eligible panel, so the strata gate
is met by construction and the census's job becomes the confounder gates. The sign of every signed primary is the
move's own or the book's own; the magnitude primaries (CH192, CH193) are maker-protection objects with a lead-minus-lag
verdict rule. Four engine-first families follow (CH198-CH201).

**Data labels.** `A` = on the host now, written by the running pass (captures, sidecar, two sweeps, trade samples, the
monitor, the Kalshi poller, the engine's own `quotes/`, `features/` and aux tables). `A*` = recorded as live in the
checkpoint (the five keyless streams) with no count on the host yet. `P` = a fetch is needed (named where light).
**Sealed and not usable by anything here:** LT2's `live_tests2/`, LT3's, LT4's, LT5's and LT6's stores once registered,
CB16's and CB17's stores, CB8-H's holders, E009/E010's `cross_venue_live/` to 2026-11-03, E011's `surprise_live/` to
2026-11-10, E025's and E026's stores and the E026 frozen modules. J4-R `[2026-10-16, 2026-10-21)` and CB13-T's holdout
`[2026-10-21, 2026-10-26)` are refused for every maker mark-out object; nothing here is one.

**Windows and registration this round proposes (LT7).** A seventh live-test family, registered separately from LT2-LT6
and after LT6's registration commit, with its own Holm family (k <= 6): origin window of **21 days from the first
00:00Z at least 24 h after the LT7 registration commit and not before 2026-12-08T00:00Z** (after LT6's proposed
`END_UTC` 12-07, so that CH195's and CH197's book states share no origin with V; the date slides later with LT6's),
single analysis at least 36 h after the end, a pre-declared 28-day extension only if a declared counts-only gate falls
short. The window spans the year-end holidays; the census projects from worn October days and the registration
discloses that December volumes may be lower (a counts-only weekly line, never a look). **Pin early (rule 9):** the
spec's states, estimators and gates by 2026-11-14 if "fresh" is wanted. Collection overlap with E011 (to 11-10), LT2
(to 11-13), LT3 (to 11-14), LT4 (to 11-16), LT5 (to 11-20), LT6 (to 12-07), E025 and E026 (to 11-15) is disclosed and is
overlap only: different hypotheses, no pooling, stores never opened by one another. E-numbers are assigned at
registration (E027-E031 provisionally LT5's, LT6 takes the next free numbers; the next free number is confirmed against
the ledger at registration).

**Hygiene that binds every idea.** Decision time is the latest input's own receipt (`received_utc` of the capture, or
sweep 1's receipt where the state reads a sweep), never a later file; states are computed from that input and strictly
earlier ones; targets are price-based (the complete captures' mids or the sweep mids; J4-R tight at both ends) and start
after the decision time: the **skip continuation** `c_skip = sign(x) x (mid_{k+3} - mid_{k+1})` for move-continuation
primaries (LT5 J, LT6 V, K), `y22 = mid_{k+12} - mid_{k+1}` for 24 h primaries (LT6 D, B), the first interval's own
change only where the state is not a move; nothing reads Gamma outcome fields except the engine-first ideas, which use
the engine's receipt-timed `res_7d`. Clustering is CR1 on event, two-way event x UTC day and UTC day with p the largest,
the event t on `G - 1` (few-treated-cluster form where the treated class is sparse), and an ex-crypto primary where a
series family exceeds 50% of units; **the primary is a within-market contrast or slope estimated by expanding-past
demeaned OLS over all eligible units, the Freedman-Lane permutation gate within the census-fixed stratum is the binding
gate, the liquidity-tier correlation gate (|corr| <= 0.5 within and pooled) and the AR(0.9) size scenarios bind for
every persistent state, and the falsification arm of rule 5 is part of the verdict.** Sports stays a parameter (the
sidecar's `fee_type` plus CB17's frozen sports list; nothing here is sports-only; every idea reports the sports arm
uncounted).

**Scores.** N novelty (1-5), EV expected value if true (1-5), **L live-ready (1-5):** 5 = a pure reader that extends an
existing LT reader by a few columns, population bounded by a named count, census on files already sealed (LT5's capture
and sweep seal, LT4's); 4 = pure reader, population unprobed but bounded above by a named count; 3 = pure reader with an
unprobed and possibly small population, or a map first; 2 = needs a stream whose counts do not exist yet; 1 = needs
fetches, maps or weeks. My judgement, not measurements.

**Planning-MDE arithmetic used throughout (LT5/LT6's pessimistic form, stated once).** Class contrast:
`MDE = 3.388 x SD x sqrt(1/n1_eff + 1/n2_eff) x sqrt(DE_gate) x 1.5 x sqrt(max(1, VIF_w))`; slope per SD of a continuous
state times the tercile gap (about 2.2 SD): `MDE = 3.388 x SD / sqrt(n_eff) x sqrt(DE_gate) x 1.5 x sqrt(VIF_w) x gap`.
`n_eff` = units in markets with >= 2 units of the population (planning: 80% of raw); `DE_gate` = max(3.0, 1 +
(m_21 - 1) x 0.02) for per-interval labels, 4.0 for rolling states, 5.0 for daily units and slow states; `VIF_w` 1.3
for labels, 1.5 for book states (E022's within-market VIF of `zh` was 1.071, pooled 1.607). SDs: skip continuation
5c, 2 h continuation 4c, 24 h change 6c, |2 h move| 3c, sweep-to-sweep 3.5c. **Floors:** 0.5c gross per share in the
favourable class or tercile for a mid target; for a magnitude target, 0.5c of E|move| in the top-against-bottom tercile
(a fifth of the 2.38c median adverse selection a passive touch fill suffers, cost-model-v1). Every MDE below is quoted
at the planning count and at a quarter of it.

**Counts table (what was counted before each idea was written; daily unless stated; the source named).**

| ID | Unit | Count on the host | Source |
|---|---|---|---|
| CH191 | non-sports market x capture with a 6 h move >= 2c and three observed steps | 2 h movers >= 1c about 2,750 an interval non-sports (P1b); the 6 h >= 2c subset **unprobed** (planning 1,500-3,000 a capture) | P1/P1b; DESIGN_V1 section 16 |
| CH192 | eligible two-sided market x capture with `rv24 > 0` | about 42,000-52,000 eligible a capture, `sp_rv6h` 98% (engine coverage); non-sports two thirds (derived) | DESIGN_V1 sections 3, 16 |
| CH193 | non-sports market x capture, `volume24hr` present and changed, \|x\| < 0.5c | `volume24hr` present on 22% of rows; the traded non-mover subset **unprobed** (planning 900-1,800 a capture) | DESIGN_V1 section 16; P1b |
| CH194 | non-sports 2 h mover with `chg_1h` present | about 2,750 an interval (P1b); `chg_1h` presence **unprobed** (the momentum family reads it; planning 80%) | P1b; DESIGN_V1 section 3 |
| CH195 | non-sports mover with sweep 1 at k - 1 and k, both 5c depths on the hit side | about 18,500 a day sweep-covered (P1/P1b; E022's 0.9996 coverage for traded; V's gate >= 70% both sweeps) | P1b; LT4 17.3; LT6 section 7 |
| CH196 | quote-only non-sports mover with `last_trade_price` present | about 11% of movers (parallel + one-sided + spread-change with a last trade), about 470 a capture (10-21 12:31Z) | DESIGN_V1 section 16 (map first) |
| CH197 | eligible two-sided market x UTC day (first complete capture) with both 5c depths and mid in [0.07, 0.93] | about 40,000 a capture with books (98%); daily units about 30,000 non-sports (derived) | DESIGN_V1 section 3; LT5 H's convention |
| CH198-CH201 | engine-first families (resolution or forecast-quality targets) | eligible panel as above; the stream families' coverage **unprobed** | DESIGN_V1; NEW_STREAMS section 3 |

---

## 1. Map: where money might be, given the costs, the nulls and the census deaths

The cost model fixes the frame: a taker needs 2.9c gross in the most liquid tier and 4.5c at the median; a passive fill
costs 2.38c of adverse selection against a 2 h mark but about 0.4c at >= $100k, and nothing on the exit leg if held to
resolution. The census deaths fix the population: only states defined on the capture, sweep and sidecar panel recur
within market often enough to be tested. So the money question for every state below is: **does it move the forecast of
the next 4-24 h mid, or of the resolution, on a population of thousands of markets a capture, and does it tell a maker
which side to post, when to step aside, or when the makers next door know something?** The engine's leaderboard measures
the first half (log-loss gain on `dir_2h`, `dir_6h`, `dir_24h`, `res_7d`); E025 part B measures the second
(signal-conditional fills). Every idea below is written to be read by both.

| Family | What every market shows at every capture and nobody has read | Money route |
|---|---|---|
| A. The shape of the own path at the capture clock (CH191, CH194) | whether the 6 h move came in one step or three; whether the 2 h move happened in the last hour or held for an hour | maker: fade one-step quote shocks, do not fade hour-held or multi-step moves; taker: follow multi-step and hour-held moves >= 3c (reported) |
| B. What the makers quote against what the path shows (CH192, CH193) | the spread relative to the market's own realised volatility; the volume the book absorbed without yielding | maker: do not tighten into a wide-ivr book; step aside on the side of a small wall that is absorbing flow; taker: nothing (unsigned) |
| C. The book the move went through and the book behind the touch (CH195, CH197) | the pre-move resting depth on the side the move hit; the imbalance of the depth behind the touch against the depth at it | maker: post with moves that consumed a deep book, lean with the patient side over 24 h; taker: follow deep-book moves >= 3c (reported) |
| D. Engine-first (CH198-CH201) | the theta a by-date question should lose each day; the class of the resolution source; the two-minute change between the pass's sweeps; the reward yield per posted dollar | HTR passive entry in >= $100k markets by state (`res_7d`); maker competition forecasts |

---

## 2. Hypotheses

### A. The shape of the own path at the capture clock (parents CH180/LT5 J, E021/CH170, E004/E006, E015/CH156, CH181/LT5 H; literature: Hong and Stein 1999, Barndorff-Nielsen and Shephard 2004, Rosu 2009)

**CH191. Grind at the capture clock: a 6 h move made in three same-signed 2 h steps is information still diffusing and
continues; the same move made in one 2 h step and two flat ones is a quote shock that partly bounces. The clock decides
the sign: at the print clock (CH180) a one-step move is a wall breaking and continues; at the capture clock a one-step
move is what E004/E006 found reverting. Sign-free (the move's own), capture-only, defined on every 6 h mover.**
- Mechanism and why it is non-obvious. A move that arrived as three monotone steps two hours apart has been re-priced
  three times by makers who could have faded it and did not: gradual diffusion in progress (Hong and Stein 1999). A move
  that arrived in one interval and then sat still for four hours is either a jump already absorbed or a quote
  re-centering whose bounce component (E004's reversal, "consistent with quote noise") has not yet played out. CH180
  reads the same decomposition inside a 2 h interval from the sample's print levels; it is at risk at the strata gate
  by E021's precedent (same population, 0.005), and its sign comes from a different mechanism (the wall). Nobody has
  read the path concentration across captures. Who pays: the taker who treats a one-step quote shock as news; the maker
  who fades a three-step grind. Why the crowd misses it: the chart shows the 6 h change, not its steps.
- Data join and decision clock (`A`, L 5). Unit: non-sports eligible market x capture k with the three steps
  `s_j = mid_{k-j+1} - mid_{k-j}` (j = 1..3) all observed (no missing slot; the known gaps are counted) and
  `x6 = sum s_j`, `|x6| >= 2c`, two-sided and tight at k - 3 .. k, mid in [0.05, 0.95]. State: path concentration
  `pc = max_j |s_j| / sum_j |s_j|` (1/3 .. 1) and sign agreement `sa = |x6| / sum_j |s_j|` (0 .. 1). Classes: **grind** =
  `sa >= 0.9` and `pc <= 0.5` (three same-signed steps, none dominant); **jump** = `pc >= 0.8` (one step is at least
  80% of the path); **zigzag** = `sa < 0.6` (reported, not counted). Decision time: capture k's receipt. Controls: E015's
  anatomy label of the last step (quoted parallel, one-sided, spread-change, traded, never), `log |x6|`, spread_k,
  logit mid, |mid - 0.5|, `log1p volume24hr`, own 24 h change (so a grind is not just stronger 24 h momentum), `rv24`.
- Target and horizon. `c_skip = sign(x6) x (mid_{k+3} - mid_{k+1})` (LT5 J's form; SD 5c); M2: `c = sign(x6) x
  (mid_{k+1} - mid_k)` reported (the bounce lives there); 24 h secondary. Hypothesis (one-sided): within market,
  E[c_skip | grind] - E[c_skip | jump] > 0.
- Paper rule and economic check. Maker: after a one-step 6 h move, re-post at the pre-move level (the bounce is the
  maker's); after a three-step grind, do not fade. Taker: follow grinds >= 3c in >= $100k markets, 2.9c round trip;
  reported only.
- Population arithmetic. Non-sports 2 h movers about 2,750 an interval (P1b); 6 h movers >= 2c with three observed
  steps plausibly 1,500-3,000 a capture (**unprobed**; overlapping windows make a 6 h mover at k likely a 6 h mover at
  k + 1): 18,000-36,000 a day, 380,000-760,000 in 21 days. Distinct events: E022's two-day count 2,539 is a lower
  bound (the 6 h population is wider); 21-day count unprobed. Jump about 30%, grind about 25% (unprobed).
- Permutation and cluster structure. Label per unit; strata market x UTC day: a 6 h mover recurs in consecutive
  captures (shared steps), so a market that moves once contributes a run of 3-6 units in the day; planning share >= 0.7
  (E022's 0.446 / 0.599 is the mover floor; this population is wider and runs are longer). Binding scenarios: LT5
  1 (iid label), 2 (persistent market rates), 4 (Markov label with an MA(2) overlapping skip target). Clusters: event;
  DE_gate 3.0.
- Planning MDE. At the low end, `n1_eff` 91,000 (jump) against `n2_eff` 76,000 (grind): `3.388 x 5c x sqrt(1/91,000 +
  1/76,000) x sqrt(3) x 1.5 x sqrt(1.3)` = **0.22c**; at a quarter of the units 0.44c (borderline); at the high end
  0.16c.
- Confounders and the control. Stronger momentum (a grind has a larger same-signed 24 h change: controlled, and the
  6 h size is fixed by |x6|); bounce at the origin (the skip target starts at k + 1; M2 reports the first interval);
  E015's anatomy (the last step's class controlled; |corr(1[grind], 1[traded last step])| <= 0.5 as a census gate);
  crypto ladders that grind by construction (ex-crypto primary; series share gate); tick coarseness (a 0.01 book
  cannot grind in half-cents: tick stratum; `|x6| >= 3 ticks`). Placebo (rule 5): the **far-future path** (the shape of
  the three steps after the target, k + 3 .. k + 6) must show no contrast; Freedman-Lane within market x UTC day.
- Cheapest census (counts only; LT5's sealed captures 10-12 .. 10-21). Distribution of `pc`, `sa`; class shares;
  permutable share; corr gates; crypto share; `n_eff`; VIF. Kill if 6 h movers < 800 a capture, if grind or jump is <
  15% of them, if the permutable share < 0.5, or if a corr gate fails.
- Challenger feature: **yes.** `capath` (`se-aux-capath-v1`): `cp_pc_6h`, `cp_sa_6h`, `cp_pc_24h`, `cp_sa_24h`,
  `cp_nsteps_24h` (count of |step| >= 1c in the last 12), from the engine's own `quotes/` of slots k - 12 .. k. Embargo:
  a different source from J's `tradepath`, but the same hypothesis family; embargo `capath` to LT5's analysis date
  (2026-11-22) for safety, and to LT7's own date once registered.
- Scores: N 3, EV 3, L 5. Parents: CH180 / LT5 J (the print-clock decomposition; the fallback relation is declared:
  if J drops at its census for the strata gate, CH191 is its capture-clock heir, not a redraw of J), E004/E006 (the
  one-step reversal), E021/CH170 (the age of the move; dropped at the strata gate), E015 (anatomy as a control).

**CH194. The hour-held move: Gamma's `oneHourPriceChange` and the capture's own 2 h change together say in which hour
the move happened. A move that happened in the first hour and held through the second has survived an hour of quote
scrutiny and is ratified; a move that happened in the last hour has not been tested; a move whose two hours disagree is
already reverting. E021 asked the same question with the trade sample's clock and died at the strata gate (0.005);
every mover carries these two fields.**
- Mechanism and why it is non-obvious. The makers of a market see every order; if a mid that moved an hour ago still
  stands at the capture, the makers who could have re-centred back chose not to (a Glosten-Milgrom update accepted).
  A move in the last hour is a fresh shock whose bounce component (E004) has not yet been taken out. The engine's
  momentum family holds both fields and a learner can combine them; as a *hypothesis* nobody has read the timing of
  the move inside the interval from the capture's own fields. Who pays: the taker who chases the last hour's move; the
  maker who fades an hour-held one. Why the crowd misses it: the UI shows the 1 h change as the mover; the held move is
  the quiet one.
- Data join and decision clock (`A`, L 4). Unit: non-sports 2 h mover at k (LT3 1.4 eligibility, |x| >= 1c) with
  `chg_1h` present at k. State: `fresh = chg_1h / x` (the share of the 2 h move that happened in the last hour).
  Classes: **held** = `fresh` in [-0.25, 0.25] (the move happened in the first hour and did not revert); **fresh** =
  `fresh` in [0.75, 1.25]; **reverting** = `fresh < -0.25` or `> 1.25` (reported, not counted). Decision time: capture
  k's receipt. Controls: E015's anatomy label, `log |x|`, spread, logit mid, |mid - 0.5|, `log1p volume24hr`, own 24 h
  change, `rv24`. Basis caveat (census item): Gamma's 1 h change is computed on Gamma's clock and price basis (CH37
  says a vacuum-displaced mid shows up in it, so it is mid-based); the census reports the share of movers with
  |chg_1h| > |x| + 1c (a basis mismatch) and kills above 20%.
- Target and horizon. `c_skip = sign(x) x (mid_{k+3} - mid_{k+1})`; M2: `c` from k reported; 24 h secondary.
  Hypothesis (one-sided): within market, E[c_skip | held] - E[c_skip | fresh] > 0.
- Paper rule and economic check. Maker: after a fresh move, re-post toward the pre-move level for one pass; after a
  held move, quote at the new level. Taker: follow held moves >= 3c in >= $100k markets, 2.9c; reported.
- Population arithmetic. About 2,750 non-sports movers an interval (P1b) x 12 x `chg_1h` presence (planning 80%,
  **unprobed**) = about 26,000 a day, 550,000 in 21 days; events: E022's 2,539 in two days is the traded subset's
  count; the whole-mover count is larger (unprobed). Held about 35%, fresh about 35% (unprobed).
- Permutation and cluster structure. Label per unit; strata market x UTC day, else block2; planning share 0.5-0.7
  (E022's mover floor 0.446 / 0.599; quote-only movers recur in program-quoted markets and raise it). Binding
  scenarios: LT5 1, 2, 3 (control at corr 0.7 with a real effect: the anatomy label), 4 (MA(2) skip target). DE 3.0.
- Planning MDE. `n1_eff` = `n2_eff` = 154,000: `3.388 x 5c x sqrt(2/154,000) x sqrt(3) x 1.5 x sqrt(1.3)` = **0.14c**;
  at a quarter of the units 0.28c.
- Confounders and the control. Anatomy (a held quote-only move is a program re-centering that stayed: controlled;
  |corr(1[held], 1[parallel])| <= 0.5 gate); momentum (24 h change controlled); bounce (skip target); the basis caveat
  above; crypto (ex-crypto primary). Placebo (rule 5): the **far-future timing** (the hour of the move in the interval
  after the target) must show no contrast; Freedman-Lane within strata.
- Cheapest census (counts only; LT5's sealed captures). `chg_1h` presence among movers; distribution of `fresh`; class
  shares; the basis-mismatch share; permutable share; corr gates. Kill if presence < 50%, if held or fresh < 20%, if
  the mismatch share > 20%, or if a corr gate fails.
- Challenger feature: **yes.** A derived set on existing columns (`mm_fresh_share = chg_1h / own 2 h change`,
  `mm_held = 1[|fresh| <= 0.25]`), no new table, no new source; it isolates no sealed test's construct (E021 is dropped),
  so no embargo beyond LT7's own once registered.
- Scores: N 3, EV 3, L 4. Parents: E021/CH170 (the age of the move; the sample's clock), CH37 (the 1 h change as a
  display artefact; here it is a clock), E015 (anatomy control), E004 (the bounce).

### B. What the makers quote against what the path shows (parents E003, CH33, CH43/E011, E015/CH156, E020/CH169, E022/CH174, CH20/CH93, CH180; literature: Karpoff 1987, Glosten and Milgrom 1985, Easley and O'Hara 1992, Rosu 2009)

**CH192. Implied against realised: the spread is the makers' volatility quote. Where the spread is wide relative to the
market's own realised volatility, the makers price more uncertainty than the path has shown, and they see the order
flow and the calendar that the path does not; the next interval's |move| is larger. Unsigned; a maker-protection and
flat-class object on the whole panel.**
- Mechanism and why it is non-obvious. A maker's half-spread is her price for the option she writes to informed
  takers (Copeland-Galai); she sets it from what she expects, not from what has happened. The ratio of the quoted to
  the realised uncertainty is the venue's version of an implied-to-realised volatility ratio, and in options markets
  the implied side forecasts the realised side beyond the realised side's own persistence. Round 11 rejected "spread
  widening with no trade" as textbook spread-volatility clustering; this is the *level* of the spread against the
  market's own realised volatility, incremental to `rv24` and to the spread's own level, and its money route is a
  maker's. E011's surprise detector (volatility-driven) reads the path; CH43 uses it as a maker's filter; neither reads
  the makers' own quote of uncertainty. Who pays: the maker who tightens into a book her competitors have widened.
- Data join and decision clock (`A`, L 4). Unit: eligible non-sports two-sided market x capture k with `rv24_k > 0`
  (the engine's `ms_rv24`: root mean square of the last 12 two-hour mid changes) and spread_k > 0. State:
  `ivr = log(spread_k / rv24_k)`; `zivr` standardised with census cuts. Decision time: capture k's receipt. Controls:
  `log rv24` (so the coefficient is the implied side's excess), `log spread_k` is **not** a control (it is the state;
  instead `log rv7d` and `log liquidity` hold the market's uncertainty and depth fixed), logit mid, |mid - 0.5|,
  `log1p volume24hr`, tick stratum (a 1-tick spread cannot widen below the tick), E015's anatomy at k, `rewards_max_spread`
  (a farmer's spread sits at the band edge by construction).
- Target and horizon. `a = |mid_{k+1} - mid_k|` (SD 3c) and `P(|move| >= 1c)`; 6 h secondary `a6`. Hypothesis
  (one-sided): within market, the slope of `a` on `zivr` > 0 with `rv24`, `rv7d` and the controls fixed; the material
  reading is the top-against-bottom tercile of `zivr`.
- Paper rule and economic check. Maker: do not post inside a book whose `ivr` is in the market's own top tercile;
  value = avoided adverse selection, "gross, no fills" (E025 part B's object). Taker: none (unsigned). Engine: the
  `flat` class of `dir_2h` / `dir_6h`.
- Population arithmetic. About 42,000-52,000 eligible a capture with `sp_rv6h` 98% coverage (DESIGN_V1); non-sports
  about two thirds (derived): about 30,000 a capture, 360,000 a day. The state is slow (the touch is unchanged within a
  pass in 90% of books; `rv24` changes every capture): effective state-change units planning 30%, about 108,000 a day,
  2.3M in 21 days; events in the tens of thousands (J4-R's 33,849 in five days over the whole universe).
- Permutation and cluster structure. Continuous persistent state; strata market x UTC day (12 units per market-day by
  construction; share about 1). The plain Freedman-Lane gate with LT5 scenarios 7 and 8 (AR(1) state rho 0.6 / 0.9 with
  a real level effect) binding; DE_gate 5.0 (slow state).
- Planning MDE. Slope per SD x tercile gap: `3.388 x 3c / sqrt(2.3M) x sqrt(5) x 1.5 x sqrt(2.0) x 2.2` = **0.07c**;
  at a quarter 0.14c. Powered many times over; the census's job is the confounder gates.
- Confounders and the control. Spread level as a liquidity trait (within-market demeaning removes the trait; `log
  liquidity` and `rv7d` controls; |corr(zivr, log liquidity)| <= 0.5 within and pooled); reward-band spreads (farmers
  post at `rewards_max_spread`: controlled; a rewarded-against-unrewarded secondary); tick floors (stratum); scheduled
  events (a wide spread before a known event is the calendar, not private information: that is part of the
  mechanism, and `hours to end` is a control so the deadline is held fixed). Placebo (rule 5): the **far-future
  `ivr`** (the spread-to-realised ratio of the interval after the target) must show a smaller slope than the lead
  (vol clustering is symmetric in time; the makers' information is not): the verdict is Supported only if
  lead minus lag clears the MDE.
- Cheapest census (counts only; LT5's sealed captures). Distribution of `ivr`; within-market IQR; state-change share;
  corr gates; rewarded share by tercile. Kill if the within-market IQR of `ivr` < 0.3 for half the markets with >= 24
  units, or if a corr gate fails.
- Challenger feature: **yes.** `ivr` and `ivr_7d` as a derived set on existing columns (`market_state` spread and
  `ms_rv24`; `sp_rv7d` from the surprise family): no new table; the `surprise` token (11-19) covers `sp_rv7d`.
- Scores: N 3, EV 3, L 4. Parents: CH33 (pre-event spread cycle), CH43 / E011 (surprise as a maker's filter), CH147
  (the sticky touch), E022 (spread as a control), round 11 section 4 (spread widening, rejected as textbook; this is
  the ratio and the lead-minus-lag design).

**CH193. Absorbed flow: walls that hold and walls that break. An interval in which the 24 h volume rose but the mid did
not move is flow that a resting wall absorbed. If the wall is a reward-sized or inventory quote it will be exhausted and
the price jumps when it breaks; if it is an informed maker's, nothing follows. The size of the wall relative to the
programme's minimum size says which. Sign-free primary (the next |move|), lead-minus-lag verdict.**
- Mechanism and why it is non-obvious. E015 reads movers and splits them by whether trades were behind the move; its
  complement, the traded non-mover, is unread: volume arrived and the touch held. In a limit-order market that is a
  patient order absorbing impatient flow (Rosu 2009); the question is whose patience. A farmer's quote at
  `rewards_min_size` absorbs little and breaks; a large resting order is a view (CH20/CH93 at round numbers; here
  wherever the wall is). CH180 reads the break at the print clock; CH195 reads the depth a move went through; this
  reads the volume that went *into* a book that did not move. Textbook volume-volatility clustering (Karpoff 1987)
  predicts more movement after volume in general; the pent-up claim is the asymmetry in time (rule 5): volume absorbed
  *before* predicts the move, volume absorbed *after* does not. Who pays: the maker who re-posts at the touch while a
  small wall is being eaten; the taker who gives up before it breaks.
- Data join and decision clock (`A`, L 4). Unit: non-sports eligible market x capture k with `volume24hr` present at
  k - 1 and k, `dV = volume24hr_k - volume24hr_{k-1} > max($10, 1e-4 x volume)` (a trade happened; the engine's
  movetype tolerance), `|x| < 0.5c` (no mid move), two-sided and tight at k - 1 and k, `last_trade_price` present
  at k. State: `log1p dV` (the absorbed notional) and the wall class from sweep 1 of pass k: **small wall** = the touch
  size on the side the last print hit (`last == ask_k` -> ask side; `last == bid_k` -> bid side; else unassigned,
  counted) is <= 2 x `rewards_min_size` (or <= 2 x `min_order_size` if unrewarded); **large wall** otherwise. Decision
  time: sweep 1's receipt when the wall class is used, else capture k's receipt. Controls: `rv24`, spread, logit mid,
  |mid - 0.5|, `log1p volume24hr_{k-1}`, `log1p D` (E022's executable depth), `hours to end`.
- Target and horizon. `a = |mid_{k+1} - mid_k|` (the break lives in the first interval) and `P(|move| >= 1c)`; `a_skip`
  (k + 1 to k + 3) secondary. Hypothesis (one-sided): within market, the slope of `a` on `log1p dV` among non-movers >
  0, and larger in the small-wall class. Signed secondary (reported, not counted): the next move's sign agrees with
  the absorbed flow's side (the last print's touch side) in the small-wall class.
- Paper rule and economic check. Maker: while a small wall on one side is absorbing flow, step aside on that side for
  one pass; while a large wall absorbs, quote normally. Taker (secondary, reported): join the absorbed side in
  >= $100k markets after `dV >= $5k` with a small wall; 2.9c.
- Population arithmetic. `volume24hr` present on 22% of rows (DESIGN_V1 section 16): about 9,000-11,000 of 40,000-
  50,000 eligible; traded non-movers among them planning 10-20%, **unprobed**: 900-1,800 a capture, 11,000-22,000 a
  day, 230,000-460,000 in 21 days; events unprobed (thousands: the active markets). Small-wall share unprobed.
- Permutation and cluster structure. Continuous state per interval (a new `dV` every capture; not a rolling window);
  strata market x UTC day: markets with `volume24hr` present are the active ones and recur every capture; planning
  share >= 0.7. Plain Freedman-Lane; LT5 scenarios 1-3 (the control `log1p D` at corr 0.7) binding; DE 3.0.
- Planning MDE. Slope per SD x gap at the low end: `3.388 x 3c / sqrt(184,000) x sqrt(3) x 1.5 x sqrt(1.5) x 2.2` =
  0.16c; the lead-minus-lag contrast doubles the variance: **0.23c**; at a quarter 0.46c (borderline).
- Confounders and the control. Volume-volatility clustering (the far-future `dV`, read from the interval after the
  target, is the lag arm; the verdict needs lead minus lag >= the MDE); the `volume24hr` roll-off (a drop is not a
  trade: `dV > 0` only; the engine's `fell` flag counted); display liquidity (E022's `h` as a control); the boundary
  (|mid - 0.5|); crypto dailies with scheduled prints (ex-crypto primary). Placebo: Freedman-Lane within strata; the
  lag arm above.
- Cheapest census (counts only; LT5's sealed captures and the two sealed sweep days). Traded non-movers a capture;
  `dV` distribution; small-wall share; last-print side assignability; permutable share; corr gates. Kill if traded
  non-movers < 400 a capture, if the small-wall class < 15% or > 85%, or if a corr gate fails.
- Challenger feature: **yes.** A `movetype` interaction set: `mt_absorbed = mt_traded x 1[|x| < 0.005]`,
  `mt_absorbed_logdv`, plus `bk_touch_minsize_side` from sweep 1 (book token to 12-09; `movetype` token to 11-22).
- Scores: N 3, EV 3, L 4. Parents: E015/CH156 (the complement population), CH20/CH93 (walls), CH180 (the break at the
  print clock), E022 (display and depth controls), CH147 (the sticky touch), Karpoff 1987 (the symmetric story this
  design is built to separate from).

### C. The book the move went through and the book behind the touch (parents E003, E022/CH174, CH190/LT6 V, CH183/LT5 R, CH116, CH20/CH93, CH146, CH149, E015; literature: Cao, Hansch and Wang 2009, Cont, Kukanov and Stoikov 2014, Kyle 1985, Rosu 2009)

**CH195. Resistance: a move that went through a deep resting book carried conviction (someone paid to take it all);
the same-sized move through a thin book was noise. The pre-move depth on the side the move hit, read from the previous
pass's sweep, is the move's resistance; moves that overcame more resistance continue. Sign-free (the move's own);
the unhit side's depth is the built-in placebo.**
- Mechanism and why it is non-obvious. Kyle's lambda is the price change per dollar of flow; its inverse, the dollars
  needed to move the price, is what the resting book was before the move. E022 reads the book *after* a traded move
  (hollowness at k, display against executable depth) and asks whether the move was impact; V reads the makers'
  post-move skew; nobody reads what the move had to eat. A move through a thick book either consumed a wall (a taker
  with conviction; CH180's jump at the print clock) or was a wall withdrawn and re-quoted higher (a maker's decision);
  both are information. A move through a thin book is a 5-share order or a quote re-centering. The placebo is exact:
  if "deep books continue" were only "liquid markets bounce less", the depth on the side the move did *not* hit would
  predict the same; the away side isolates the trait. Who pays: the maker who fades a move that just consumed her
  competitors' depth; the taker who chases a move through nothing.
- Data join and decision clock (`A`, L 4). Unit: non-sports mover at capture k (LT3 1.4 eligibility, |x| >= 1c, traded
  or quote-only, anatomy controlled) with sweep 1 of pass k - 1 two-sided and both 5c depths present, and sweep 1 of
  pass k present (for E022's `h` and V's `v` as controls). State: `R = log1p D_hit,k-1` where `D_hit` is the 5c depth
  (taker notional) on the side the move consumed at sweep k - 1 (ask side for an up move, bid side for a down move);
  placebo state `R_away = log1p D_away,k-1`; `zR` with census cuts. Decision time: capture k's receipt (sweep k - 1 is
  two hours old; sweep k is read only for controls, so the decision time becomes sweep k's receipt when they are
  used; both are before the target). Controls: `R_away` (so the coefficient is the hit side's excess over the market's
  depth), E015's anatomy label, `log |x|`, spread at k - 1 and k, logit mid, |mid - 0.5|, `log1p volume24hr`, E022's
  `zh` at k and V's `v_prev` (the pre-move imbalance; `R - R_away` is close to it in logs, so the primary is also
  stated as the slope on `zR` with `R_away` fixed and the correlation with `v_prev` is a census gate), own 24 h change.
- Target and horizon. `c_skip = sign(x) x (mid_{k+3} - mid_{k+1})`; sweep-to-sweep `c_vskip` (V's form) as M1;
  24 h secondary. Hypothesis (one-sided): within market, the slope of `c_skip` on `zR` > 0 with `R_away` and the
  controls fixed; the material reading is the top-against-bottom tercile of `zR`.
- Paper rule and economic check. Maker: after a move that consumed a top-tercile book, post on the move's side (do not
  fade); after a move through a bottom-tercile book, re-post at the pre-move level. Taker: follow moves >= 3c with
  top-tercile resistance in >= $100k markets, 2.9c; reported.
- Population arithmetic. About 18,500 non-sports movers a day all sweep-covered (P1/P1b; E022's traded coverage
  0.9996; V's both-sweep gate >= 70%): planning 13,000-18,500 a day, 270,000-390,000 in 21 days; events: E022's 2,539
  in two days for the traded subset (lower bound). `n_eff` 80%.
- Permutation and cluster structure. Continuous state per unit (the previous book's depth; it is not a rolling
  window); strata market x UTC day if >= 50%, else block2 (E022's 0.446 / 0.599 for traded movers; all movers higher).
  Plain Freedman-Lane; LT5 scenarios 3 (control at corr 0.7: `R_away`), 7 and 8 (AR state) binding; DE 3.0; VIF 1.5.
- Planning MDE. `3.388 x 5c / sqrt(216,000) x sqrt(3) x 1.5 x sqrt(1.5) x 2.2` = **0.26c** at the low end; at a
  quarter 0.52c (borderline); at the high end 0.21c.
- Confounders and the control. Liquidity trait (`R_away` control and the away-side placebo; |corr(zR, log liquidity)|
  <= 0.5 within and pooled); the pre-move imbalance (V's `v_prev`; |corr(zR, z v_prev)| <= 0.5 within as a gate, else
  the test is V's object and drops); hollowness after the move (E022's `zh` control); anatomy (controlled; a
  quote-only move through a deep book is a wall withdrawn, reported by class); the boundary (near 0.95 the ask side's
  5c band is truncated: |mid - 0.5| and mid in [0.07, 0.93]); crypto (ex-crypto primary). Placebo (rule 5): the
  **away-side** slope must be null; Freedman-Lane within strata. Overlap with LT6 V: no shared origin (LT7 starts after
  V's `END_UTC`), the state is a depth level at k - 1 not the post-move skew at k, and the design is pinned before
  V's analysis (`T_V`), as V is before `T_E022`.
- Cheapest census (counts only; LT5's two sealed sweep days with their captures). Distribution of `R`, `R_away`;
  within-market IQR; corr with `v_prev`, `zh`, liquidity; permutable share; both-sweep coverage. Kill if both-sweep
  coverage < 70%, if the within-market IQR of `R` < 0.5 (in logs) for half the markets with >= 6 units, or if a corr
  gate fails.
- Challenger feature: **yes.** `resist` (`se-aux-resist-v1`): `rs_hit_depth_prev`, `rs_away_depth_prev`,
  `rs_log_ratio` (hit minus away, signed by the own 2 h change), from the engine's stored book columns of slot k - 1
  (the book family already holds 5c depth per side, so the table is a lagged join). Embargo: `book` to 12-09 and
  LT7's own date.
- Scores: N 4, EV 3, L 4. Parents: E022/CH174 (post-move hollowness; this is the pre-move book), CH190 / LT6 V (post-
  move skew; `v_prev` is V's control and this test's gate), E003 (unconditional imbalance), CH180 (wall break at the
  print clock), CH20/CH93 (walls at round numbers).

**CH197. Patient money: the depth behind the touch is the patient side's vote, the depth at the touch the impatient
side's. When they disagree, the impatient side wins the next two hours and the patient side the next day. Defined on
every two-sided book at every capture; a 24 h daily-unit primary with the 2 h direction as the reported mirror.**
- Mechanism and why it is non-obvious. Orders resting one tick from the touch are competing for the next print;
  orders resting 2-5c away are waiting for a better price and are willing to wait (Rosu 2009's patient traders);
  Cao, Hansch and Wang (2009) find the book beyond the touch carries information the touch does not. E003 tested the
  1c and 5c imbalances as levels and was inconclusive at minutes; V reads the 5c skew after a move; R reads the 1c skew
  inside the reward band; nobody reads the *disagreement* between the touch and the book behind it, nor the horizon
  split it implies. Who pays: the taker who reads the touch imbalance as the market's view and trades against the
  patient side over a day; the maker who leans with the touch for longer than two hours.
- Data join and decision clock (`A`, L 4). Unit for the primary: eligible non-sports two-sided market x UTC day at the
  day's first complete capture (H's convention), both 1c and 5c depths present on both sides at sweep 1, mid in
  [0.07, 0.93] (so the 5c band is not truncated by the boundary), spread <= 5c. State: `imb1 = (B1 - A1)/(B1 + A1)`,
  `imbB = ((B5 - B1) - (A5 - A1)) / ((B5 - B1) + (A5 - A1))` (the behind-touch imbalance), oriented toward outcome 0;
  `dis = imbB - imb1` (patient minus impatient). Decision time: sweep 1's receipt. Controls: `imb1` (so the coefficient
  on `imbB` is the patient side's excess), `log1p D5` (total 5c depth), E022's `zh`, spread, logit mid, |mid - 0.5|,
  `log1p volume24hr`, own 24 h change, `rewarded` and `rw_in_band` (farmers' quotes at the band edge are "behind the
  touch" by construction: a rewarded-against-unrewarded secondary and the min-size share of the behind-touch depth as
  a census item).
- Target and horizon. Primary: `y22 = mid_{k+12} - mid_{k+1}` (22 h from the next capture; SD 6c) on `zimbB`; mirror
  M1: `y2 = mid_{k+1} - mid_k` on `zimb1` (the impatient side's two hours; reported, mechanical at short horizons);
  secondary: the 2 h slope on `zimbB` (expected smaller than the 24 h one). Hypothesis (one-sided): within market, the
  slope of `y22` on `zimbB` > 0 with `imb1` and the controls fixed.
- Paper rule and economic check. Maker: lean with the patient side for the day (post bids when the book behind is
  bid-heavy), with the touch for the next pass. Taker: buy the patient side when `dis` is in the top tercile in
  >= $100k markets and hold 24 h, 2.9c; HTR where `res_7d` applies; reported.
- Population arithmetic. About 40,000 eligible a capture with books (98%); non-sports two thirds (derived): about
  30,000 daily units a day, 630,000 in 21 days; markets with >= 4 daily units (the market stratum) planning 80%;
  events in the tens of thousands (J4-R's 33,849 in five days).
- Permutation and cluster structure. Daily unit; stratum = market (>= 4 units; H's rule), share planning >= 0.8;
  the state is persistent day to day (a farmer's ladder is the same every day): LT5 scenarios 5 and 6 (per-day
  persistence 0.6 / 0.9, daily targets from 12 pass shocks) binding; DE_gate 5.0; VIF 1.5 (`imb1` is correlated with
  `imbB` through shared quoters; |corr| <= 0.5 within as a gate).
- Planning MDE. `3.388 x 6c / sqrt(504,000) x sqrt(5) x 1.5 x sqrt(1.5) x 2.2` = **0.26c**; at a quarter 0.52c
  (borderline); with state-change units only (half) 0.37c.
- Confounders and the control. The touch imbalance (controlled, and its own 2 h slope is the mirror); reward ladders
  (controlled; secondary; the census reports the min-size share behind the touch and kills above 70%); the boundary
  (mid band); display liquidity (`zh`); momentum (24 h change). Placebo (rule 5): a **fake split** (the imbalance of
  the 5c band read as if 1c were the whole band, i.e. `imb5` in place of `imbB`, which cannot carry the disagreement)
  must not beat `imbB`; the far-future `imbB` (read the day after the target) must show no slope; Freedman-Lane within
  market strata.
- Cheapest census (counts only; LT5's two sealed sweep days). Distribution of `imb1`, `imbB`, `dis`; corr(imb1,
  imbB); min-size share behind the touch; rewarded share; permutable share at the daily unit (markets present on both
  days with books). Kill if |corr(imb1, imbB)| > 0.5 within market, if the min-size share > 70%, or if the within-market
  SD of `imbB` across the two census days is < 0.1 for half the markets.
- Challenger feature: **yes.** `deepbook` (`se-aux-deepbook-v1`): `db_imb_behind`, `db_dis`, `db_share_behind`
  (behind-touch depth over 5c depth), from the engine's stored book columns (the 1c and 5c depths per side are in the
  v1 book family, so this is arithmetic on stored columns). Embargo: `book` to 12-09 and LT7's own date.
- Scores: N 3, EV 3, L 4. Parents: E003 (imbalance levels), CH190 / LT6 V (post-move 5c skew), CH183 / LT5 R (1c skew in
  the band), CH116 (band-stripped imbalance), CH149 (dormant deep ladders, the farmer confound), CH146 (book age).

### Map first (an idea whose population is small by the engine's own coverage count; census before any slot)

**CH196. The last-print anchor: in a quote-only move the makers re-centred away from the last transaction price with
no taker involved; the last print is the only price a counterparty ever paid, and quotes drift back toward it until the
next print re-anchors them. The distance the mid moved beyond the last print, signed by the move, predicts reversion.
Capture-only, no flow; a moderator of E015's quote-only class, so it is pinned only after E015's analysis commit.**
- Why map first. Quote-only movers with a last trade price are about 11% of movers (parallel 4.4% + one-sided 5.4% +
  spread-change 1.5% on 10-21 12:31Z, of 4,244 movers), about 470 a capture all categories, and `mt_never` is 72% of
  markets; the population is E020's size class (2,283 a day) and E020 died at the strata gate (0.055). CB18-P
  (CH172) read the flow reaction to such re-centerings and was dropped (GP1). A counts-only map on LT5's sealed
  captures (quote-only movers with a last print; their recurrence per market-day; the distribution of `a = sign(x) x
  (mid_k - last_k)`) decides whether any slot exists; the expectation, declared now, is that it does not (kill line:
  < 300 non-sports units a day with recurrence >= 0.5).
- If it lives (`A`, L 3): unit = non-sports quote-only mover at k with `last_trade_price` present and unchanged from
  k - 1; state `a` (cents the mid moved past the last print, signed by the move); target `c_skip`; hypothesis within
  market: the slope of `c_skip` on `za` < 0 (reversion toward the print), E015's anatomy sub-class held fixed. Rule 9:
  it is an E015 moderator and is pinned only after 2026-11-15T12Z with the disclosure.
- Challenger feature: `mt_dist_last = (mid - last) x sign(own 2 h change)` on quote-only rows (a `movetype` column;
  `last trade - mid` already exists in `market_state`, so the new part is the sign and the class). `movetype` token to
  11-22.
- Scores: N 2, EV 2, L 3. Parents: E015/CH156 (quote-only moves), CH172 / CB18-P (program versus human; dropped),
  round 11 section 4 ("program overrides human", not proposed; here the anchor is the print, not the program).

### D. Engine-first ideas (resolution-level or forecast-quality objects; a 21-day mid-target version would be underpowered, double-count a sealed test, or need a stream whose counts do not exist)

**CH198. Calendar theta: a "by date" question loses probability every day nothing happens; under a constant hazard
the daily loss is `p(1 - p) / T` for T days left. A market whose price fell by less than its theta over the last three
days, with no traded move, has holders who are not counting the days; the deficit is paid near the deadline. The
text-free template classifier of LT6 D supplies the population; the engine's `res_7d` and the 24 h drift are the
targets.**
- Why engine-first. By-date interior markets are the population LT6 D's census will count; the state changes once a
  day; a 21-day mid-drift test has daily units on a few thousand markets at most (LT6 D's planning MDE 0.43-0.99c on
  its own population), and the claim is calibration (the price is too high for the time left), which `res_7d` reads on
  the rolling window without a window of its own. Prior art gap 2 (YES-optimism / NO-side carry by class) is the
  wide version; CH62, CH105 and CH189 read the deadline itself; D reads a deadline *change*; nobody reads the theta a
  price should have lost while nothing happened.
- State (`A`, L 3 for the engine). `th_theta24 = mid x (1 - mid) / T_days` (the constant-hazard daily decay on the
  by-date template), `th_deficit_3d = (mid_k - mid_{k-36}) + 3 x th_theta24` restricted to markets with no traded move
  in the three days (E015's label), `th_bydate` (D's classifier). Decision time: capture receipt. Targets: `res_7d`
  (calibration gap by deficit tercile; HTR passive NO entry in >= $100k markets reported), 24 h drift (< 0 for YES).
- Census: by-date interior markets a day (D's census CD prints it); kill if < 500 non-sports with T in [3, 60] days.
- Challenger feature: **yes.** `theta` (`se-aux-theta-v1`): the three columns above. Embargo: `deadline` token to
  12-09 (LT6 D's classifier is shared) and `movetype` to 11-22 (the no-traded-move filter).
- Scores: N 3, EV 3, L 3. Parents: CH62, CH105, CH189, CH187 / LT6 D (`theta24` is D's control; here it is the state),
  CH05/CH06 (hazard across rungs), prior-art gap 2.

**CH199. The resolution-source class: the `gamma_rules` stream now stores each market's `resolutionSource` and
`resolvedBy` for the top 3,000 markets hourly and the whole active frame every 6 h. The host of the source URL is a
text-free class (statistics agency, court docket, sports feed, exchange, news consensus, on-chain, none): markets that
resolve on a scheduled public statistic are priced differently from those that resolve on "credible reporting", and
the difference is a calibration gap the engine can read on `res_7d`.**
- Why engine-first. The stream's first registrable window starts at its install (NEW_STREAMS section 5), the class is
  a slow trait (one value per market), and its target is a resolution; CH28 (scheduled-source), CH75 (first print),
  CH87 (reporting-standard premium) and CH63 (specificity) are the text-based parents; this is the host-level class,
  no parsing beyond a URL, on every market the frame covers.
- State (`A*`, L 2: the stream's coverage of the eligible panel is unprobed). `rs_class` one-hot (a fixed host map
  declared before any score), `rs_has_source`, `rs_uma_only` (resolvedBy UMA with no source), joined by market id
  from the latest `gamma_rules` row received before the capture (a market outside the frame is NaN; never filled).
- Census: coverage of eligible markets by class; kill if < 30% of eligible non-sports markets carry a parseable
  source host.
- Challenger feature: **yes.** `rulesrc` (`se-aux-rulesrc-v1`). Embargo: none (no live test reads the source class;
  CB7-S text stability is sealed and reads rule text, not the host).
- Scores: N 2, EV 3, L 2. Parents: CH28, CH63, CH75, CH87, NEW_STREAMS section 2 (CH08/CH63/CH64 as the stream's
  stated uses).

**CH200. Two minutes of quote news: the pass writes two sweeps about two minutes apart and the engine reads only the
first. The change between them (touch, 1c depth, levels) is the most recent quote decision the venue shows, received
before the prediction is written. CH147 read it as a quoter footprint (the touch unchanged in 90% of books); as a
feature it is the latest tick, on 10% of books every pass.**
- Why engine-first. A 2-minute mid change continuing over 2 h is short-horizon momentum (textbook; E002's object);
  the question for the engine is whether the second sweep adds to the first on `dir_2h`, which the leaderboard
  answers without a test. Nothing sealed reads sweep 2 (E015's M1 reads sweep 1; E022 and V read sweep 1).
- State (`A`, L 4). `s2_dmid` (sweep-2 mid minus sweep-1 mid), `s2_d_imb1c`, `s2_changed` (any touch or 1c size
  change), `s2_levels_delta`; NaN where sweep 2 is missing. Decision time: sweep 2's receipt (before the predict step
  of the tick; the engine must write the prediction after sweep 2, which the pass order already guarantees).
- Challenger feature: **yes.** `sweep2` (`se-aux-sweep2-v1`), read against se1 and against `se3_lr_book` once the
  `book` embargo lifts (12-09; the family is book-derived and takes the `book` token).
- Scores: N 2, EV 2, L 4. Parents: CH147 (sticky touch, breathing book), CH178 (two minutes, rejected as an E015
  double count; here no continuation test is proposed), E003.

**CH201. Reward yield per posted dollar: the `reward_params` stream (every 2 h since 2026-10-20T23:20Z) and sweep 1
give, per rewarded market, the daily reward rate against the depth that already sits inside `rewards_max_spread`. The
yield a new quote would earn is the rate divided by the depth it would share; high-yield books attract farmers within
hours and their depth rises, low-yield books lose them. A maker-competition forecast and, through the farmers'
arrival, a spread forecast.**
- Why engine-first. The target is the next pass's in-band depth and spread, not a price; E025 (provisional) owns the
  reward-inclusive maker P&L and CH16/CH45/CH152 own the geometry and shocks; the engine's `rewards` family holds the
  rate and the band but not the yield. A `dir_2h` gain, if any, would come through the spread's effect on the mid's
  noise (bounce), so the family is read on `dir_2h` with that caveat and on the engine's calibration columns.
- State (`A`, L 3). `rw_yield = rate / (depth_in_band + 1)` (dollars a day per dollar posted), `rw_depth_in_band`,
  `rw_yield_rank_cat` (within category, so a venue-wide rate change is not a per-market signal). Decision time: sweep
  1's receipt.
- Challenger feature: **yes.** An extension of `rewards` (`se-aux-rewards-v2`), tokens `rewards` (11-22) and `book`
  (12-09).
- Scores: N 2, EV 2, L 3. Parents: CH16, CH19, CH45, CH152, CH183 / LT5 R, MAKER_REWARDS_STUDY (the +3.13c lead for
  fills > 30 days before close is the only maker-side lead on record), E025.

---

## 3. Ranked top 6 for LT7, then the rest

Rank = census survival (population recurrence, strata share, effective count) x originality x plausibility x money
route, with the rules of section 0.1 as hard constraints. Every LT7 candidate has a continuous or per-interval state
defined on the capture-sweep-sidecar panel, a within-market contrast or slope with the Freedman-Lane gate, a declared
falsification arm that is part of its verdict (rule 5), a counts-only census on files LT5 already sealed, a planning
MDE under 0.5c at a quarter of the planned units or close to it, and a reader that extends an existing LT reader
(E015's for capture states, E022's / V's for sweep states).

| Rank | ID | One line | L | Population arithmetic (source) | Permutation structure | Primary | Planning MDE (quarter) |
|---|---|---|---|---|---|---|---|
| 1 | CH195 | Resistance: the pre-move depth the move went through, away side as placebo | 4 | 13,000-18,500 non-sports movers a day, all sweep-covered (P1/P1b; E022 0.9996); 270,000-390,000 in 21 days; events >= 2,539 per two days (E022) | per-unit level state; market x day, else block2 (E022's 0.446 / 0.599 floor); FL with scenarios 3, 7, 8 | within market, slope of `c_skip` on `zR`, `R_away` fixed | 0.26c (0.52c) |
| 2 | CH191 | Grind at the capture clock: one step or three, from the own mids | 5 | 1,500-3,000 non-sports 6 h movers a capture (unprobed; bounded by P1b's 2,750 2 h movers an interval): 18,000-36,000 a day, 380,000-760,000 in 21 days | per-interval label; market x day (runs of 3-6 units per mover); FL with scenarios 1, 2, 4 | within market, grind minus jump on `c_skip` | 0.22c (0.44c) |
| 3 | CH194 | The hour-held move: `chg_1h` against the own 2 h change | 4 | about 26,000 non-sports movers a day with `chg_1h` (P1b x 12 x 0.8, presence unprobed); 550,000 in 21 days | per-interval label; market x day, else block2; FL with scenarios 1-4 | within market, held minus fresh on `c_skip` | 0.14c (0.28c) |
| 4 | CH197 | Patient money: the book behind the touch against the touch, 24 h daily unit | 4 | about 30,000 non-sports daily units (40,000 books a capture x two thirds, derived); 630,000 in 21 days; events in the tens of thousands (J4-R 33,849 / 5 days) | daily unit; market strata (>= 4 days); FL with scenarios 5, 6 (per-day persistence) | within market, slope of `y22` on `zimbB`, `imb1` fixed | 0.26c (0.52c) |
| 5 | CH193 | Absorbed flow: volume into a book that did not move, lead minus lag | 4 | 900-1,800 traded non-movers a capture (22% `volume24hr` presence x 10-20%, unprobed): 11,000-22,000 a day, 230,000-460,000 in 21 days | per-interval state; market x day (active markets recur); FL with scenarios 1-3 | within market, slope of `a` on `log1p dV`, lead minus lag | 0.23c (0.46c) |
| 6 | CH192 | Implied against realised: the spread as the makers' volatility quote | 4 | about 30,000 non-sports eligible a capture (DESIGN_V1 coverage, derived); 108,000 state-change units a day (planning 30%); 2.3M in 21 days | persistent state; market x day (12 units by construction); FL with scenarios 7, 8; DE 5 | within market, slope of `a` on `zivr`, `rv24` fixed, lead minus lag | 0.07c (0.14c) |
| 7 | CH196 | The last-print anchor (map first; E015 moderator after 11-15) | 3 | about 470 quote-only movers with a last print a capture, all categories (DESIGN_V1 section 16); recurrence unprobed, E020's size class | at risk (E020: 0.055 / 0.132) | slope of `c_skip` on `za` < 0 | map decides |
| 8 | CH198 | Calendar theta on by-date templates (engine-first) | 3 | D's census population; unprobed | daily; market strata | `res_7d` calibration gap; 24 h drift | engine window |
| 9 | CH201 | Reward yield per posted dollar (engine-first) | 3 | 13,683 rewarded markets (snapshot); 5.2% of markets | slow | `dir_2h` with the bounce caveat; depth and spread forecasts | engine window |
| 10 | CH200 | Two minutes of quote news, sweep 2 (engine-first) | 4 | 10% of 65,771 books change within a pass (CH147's probe) | per-pass | `dir_2h` against se1 and se3 | engine window |
| 11 | CH199 | The resolution-source class from `gamma_rules` (engine-first) | 2 | coverage of the eligible panel unprobed (top 3,000 hourly, frame every 6 h) | trait | `res_7d` by class | engine window |

CH195 is first because its population is E022's own (the one mover population that has passed the strata gate) and
its placebo is exact; CH191 and CH194 are second and third because they are capture-only, need no sweep, and inherit
E021's dead question on a population that recurs. CH197, CH193 and CH192 are the whole-panel states with the largest
counts; CH197 is a daily-unit test (H's convention) and the two magnitude tests carry a lead-minus-lag verdict that
costs them power. If the LT7 designer wants k = 4 with the strongest money routes, CH195, CH191, CH194 and CH197 are
the signed four and CH192/CH193 become reported secondaries of a maker-protection arm.

**Pre-registration sketches for the top 6 (LT7 candidates; each a separate primary in one Holm family; written in
LT5/LT6's shape so the designer can lift them).**

- **CH195 (resistance).** Unit: non-sports mover at k (LT3 1.4), sweep 1 of pass k - 1 two-sided with both 5c depths,
  sweep 1 of pass k present. State: `zR` = standardised `log1p D_hit,k-1`; `R_away` the unhit side. Decision time:
  sweep k's receipt (controls) with the state two hours older. Primary: expanding-past market-demeaned OLS of `c_skip`
  on `zR` with `R_away`, anatomy label, `log |x|`, spreads at k - 1 and k, logit mid, |mid - 0.5|, `log1p volume24hr`,
  `zh_k`, `v_prev` and own 24 h change as controls; one-sided > 0; material reading top-against-bottom tercile.
  Targets: `c_skip`; M1 `c_vskip`; 24 h secondary. Clustering: LT6 V's. Planning MDE 0.26c. Census (two sealed sweep
  days): both-sweep coverage >= 70%; within-market IQR of `R` >= 0.5 in >= 50% of markets with >= 6 units; |corr(zR, z
  v_prev)| <= 0.5 within; |corr(zR, log liquidity)| <= 0.5 within and pooled; permutable share >= 50% (day, else block2);
  pessimistic MDE <= 0.5c. Verdict condition: the away-side slope's upper 95% bound below the primary's point estimate
  minus the MDE. Cost hurdle: maker none; taker follow of top-tercile moves >= 3c reported. Extends: V's reader (two
  depth columns of sweep k - 1). Embargo: `book` to 12-09 and LT7's date.
- **CH191 (grind at the capture clock).** Unit: non-sports eligible market x capture, three observed steps, |x6| >= 2c
  and >= 3 ticks, two-sided and tight at k - 3 .. k, mid in [0.05, 0.95]. State: `pc`, `sa`; grind `sa >= 0.9 & pc <=
  0.5`, jump `pc >= 0.8`. Decision time: capture k's receipt. Primary: expanding-past market-demeaned OLS of `c_skip` on
  1[grind] over grind and jump units with the last step's anatomy, `log |x6|`, spread, logit mid, |mid - 0.5|, `log1p
  volume24hr`, own 24 h change, `rv24` and tick stratum as controls; one-sided > 0. Targets: `c_skip`; M2 `c`; 24 h.
  Clustering: LT4 L10 with the ex-crypto rule. Planning MDE 0.22c. Census (LT5's sealed captures): 6 h movers >= 800 a
  capture; grind and jump >= 15% each; |corr(1[grind], 1[traded last step])| <= 0.5 within; |corr(1[grind], log
  liquidity)| <= 0.5 within and pooled; crypto share of grinds <= 70%; permutable share >= 50%; pessimistic MDE <=
  0.5c. Verdict condition: the far-future path contrast null. Extends: E015's reader (three lagged mids). Embargo:
  `capath` to 11-22 and LT7's date. Declared relation: J's capture-clock heir if J drops at the strata gate.
- **CH194 (the hour-held move).** Unit: non-sports mover at k with `chg_1h` present. State: `fresh = chg_1h / x`; held
  [-0.25, 0.25], fresh [0.75, 1.25]. Decision time: capture k's receipt. Primary: expanding-past market-demeaned OLS of
  `c_skip` on 1[held] over held and fresh units with anatomy, `log |x|`, spread, logit mid, |mid - 0.5|, `log1p
  volume24hr`, own 24 h change and `rv24` as controls; one-sided > 0. Targets: `c_skip`; M2 `c`; 24 h. Planning MDE
  0.14c. Census: `chg_1h` presence among movers >= 50%; held and fresh >= 20% each; basis-mismatch share <= 20%;
  |corr(1[held], 1[parallel])| <= 0.5 within; liquidity gate; permutable share >= 50%; pessimistic MDE <= 0.5c. Verdict
  condition: the far-future timing contrast null. Extends: E015's reader (one Gamma field). Embargo: none beyond
  LT7's (E021 is dropped; the momentum family already holds both inputs: disclosed as a derived set).
- **CH197 (patient money).** Unit: non-sports eligible two-sided market x UTC day at the day's first complete capture,
  both 1c and 5c depths on both sides, mid in [0.07, 0.93], spread <= 5c. State: `zimbB` with `imb1` as a control.
  Decision time: sweep 1's receipt. Primary: expanding-past market-demeaned OLS of `y22 = mid_{k+12} - mid_{k+1}` on
  `zimbB` with `imb1`, `log1p D5`, `zh`, spread, logit mid, |mid - 0.5|, `log1p volume24hr`, own 24 h change,
  `rewarded`, `rw_in_band` as controls; one-sided > 0; material reading top-against-bottom tercile. Mirror M1: `y2` on
  `zimb1` (reported). Clustering: LT5 H's (market strata, event CR1). Planning MDE 0.26c. Census: |corr(imb1, imbB)| <=
  0.5 within; min-size share behind the touch <= 70%; within-market SD of `imbB` across census days >= 0.1 in >= 50% of
  markets; market-strata share >= 50% (markets with a unit on both census days); liquidity gate; pessimistic MDE <=
  0.5c with DE 5. Verdict condition: the fake split (`imb5` in place of `imbB`) does not beat `imbB`, and the far-future
  `imbB` shows no slope. Extends: E022's reader (two more depth columns). Embargo: `book` to 12-09 and LT7's date.
- **CH193 (absorbed flow).** Unit: non-sports eligible market x capture, `volume24hr` present at k - 1 and k, `dV` above
  the movetype tolerance, |x| < 0.5c, two-sided and tight, last print present; wall class from sweep 1 of pass k.
  State: `log1p dV`, 1[small wall]. Decision time: sweep 1's receipt. Primary: expanding-past market-demeaned OLS of
  `a = |mid_{k+1} - mid_k|` on `z log1p dV` and its product with 1[small wall], with `rv24`, spread, logit mid, |mid -
  0.5|, `log1p volume24hr_{k-1}`, `log1p D`, `zh`, hours to end as controls; one-sided > 0 on the main slope; the
  small-wall interaction reported as material if its point estimate is >= 0.5c at the tercile gap. Lag arm: the same
  model with `dV` of the interval after the target; verdict Supported only if lead minus lag >= the MDE. Planning MDE
  0.23c. Census: traded non-movers >= 400 a capture; small-wall share in [15%, 85%]; last-print side assignable in >=
  50%; permutable share >= 50%; liquidity gate; pessimistic MDE <= 0.5c. Extends: E015's reader plus one sweep column.
  Embargo: `movetype` to 11-22, `book` to 12-09, LT7's date.
- **CH192 (implied against realised).** Unit: non-sports eligible two-sided market x capture with `rv24 > 0`, spread
  > 0. State: `zivr`. Decision time: capture k's receipt. Primary: expanding-past market-demeaned OLS of `a` on `zivr`
  with `log rv24`, `log rv7d`, `log liquidity`, logit mid, |mid - 0.5|, `log1p volume24hr`, tick stratum, anatomy at
  k, `rewards_max_spread`, hours to end as controls; one-sided > 0; material reading top-against-bottom tercile; the
  lag arm (far-future `ivr`) and the lead-minus-lag verdict as CH193. Clustering: LT4 L10 with DE 5. Planning MDE
  0.07c. Census: within-market IQR of `ivr` >= 0.3 in >= 50% of markets with >= 24 units; state-change share >= 20%;
  |corr(zivr, log liquidity)| <= 0.5 within and pooled; |corr(zivr, z log rv24)| <= 0.7 within; pessimistic MDE <= 0.5c.
  Extends: E015's reader (the spread and twelve lagged mids). Embargo: `surprise` to 11-19 for `rv7d`; LT7's date.

**How the families would be registered.**
- **A. The path at the capture clock (CH191, CH194).** Both counted if their censuses pass, on E015's reader; the
  `capath` family and the `mm_fresh` derived set go to the engine as challengers at once, `capath` under its embargo.
- **B. Makers against the path (CH192, CH193).** Counted as maker-protection primaries with the lead-minus-lag verdict;
  if the designer prefers k = 4, both become reported secondaries and their engine columns are added regardless.
- **C. The book (CH195, CH197).** Counted; origins start after LT6 V's `END_UTC`; pinned before `T_V`; the `resist` and
  `deepbook` families go to the engine under the `book` token (12-09).
- **Map first (CH196).** A counts-only map on LT5's sealed captures; a slot only if the map clears its kill line and
  E015's analysis commit exists.
- **D. Engine-first (CH198-CH201).** Challenger families with the tokens named; CH199 and CH201 need a coverage census
  on the new streams first (the first count on them).

**What is honest to say about all of them.** Round 11's ideas were about what the streams let a reader remember;
three of its five LT5 members are declared "likely to drop" or "borderline" by their own design, and E020 and E021,
with tens of thousands of projected units, died because their units did not recur within the market. Round 12's six
are built around that fact: each state is defined on the whole capture-sweep-sidecar panel or on the mover population
that has already passed the strata gate, each contrast is within market, and each carries a falsification arm whose
null is mechanical by construction. The mechanisms are modest and specific: the clock on which a move's shape is read
decides its sign (CH191 against CH180), an hour of quote scrutiny ratifies a move (CH194), the depth a move consumed
is its conviction (CH195), the book behind the touch is the patient side's vote (CH197), volume absorbed without a
move is a wall being eaten (CH193), and the spread is the makers' own volatility quote (CH192). Nothing here is edge
until it has gone through census, frozen rules, prospective registration and an economic check at recorded prices;
the engine's leaderboard, not this file, is where any of it would first show.

---

## 4. Ideas considered and rejected, and why

- **Any trade-sample unit as an LT7 primary** (print-level path shapes, clip trains, overhang, walked flow, races,
  opens and closes, concentration). E021's strata share 0.005 / 0.018 with 44,919 projected units is the measured fate
  of a 2,000-market rotating sample; LT5 J and O and LT6 K carry the same risk and are already drafted. Not proposed;
  CH191 is the capture-clock heir of CH180 by declaration.
- **The laggard catch-up (the non-mover in a moving family drifts toward the family).** The complement of LT5 F's
  population; the ladder lead-lag nulls (L1-L4, XM1-XM6, E005 not supported) and the engine's `event` family
  (`ev_sib_d2h`, a counted development look) make the prior weak and the construct informed. Not proposed.
- **Amihud-style illiquidity (|move| per dollar of volume over 24 h) as a state.** Textbook, unsigned, a slow trait
  that within-market demeaning mostly removes; CH195 reads the per-move version with a placebo. Not proposed.
- **Volume predicts volatility (the symmetric version).** Karpoff 1987; CH193 is the asymmetric, wall-classed version
  with the lead-minus-lag verdict that separates pent-up pressure from clustering. The plain version is not proposed.
- **Venue-wide and category-wide clocks of any kind** (UTC hour, weekday, reward epoch, category mood, market-wide
  activity). The engine's `regime` family was worse than the baseline and was dropped; CH158 died the same way.
- **Comment-count deltas, `updated_at` semantics, `competitive`, open-interest ratios.** Comments: 9 of 22,111 events
  changed in 2 h (round 8). `updated_at`: a tick clock (CB18-S GS2 fail; 116,940 of 246,961 rows changed in 2 h).
  `competitive` and OI are in `participation` (embargoed to 11-25) and CB17-C. Not proposed.
- **PredictIt, Smarkets, ESPN odds and Kalshi pairs as LT7 populations.** 867 keys, 677 books, 94 games, 116 pairs;
  CB15-P's 37 pairs in 12 events and CB13-R's 58 events are what external frames deliver. Engine-first only (CH199
  uses `gamma_rules`; the `xvenue2` and closing-line families are CANDIDATES rows 4 and CH29, sports scope the owner's
  call). Not proposed as tests.
- **Rule-text edits as events (CH08, CH177, CH63, CH64).** 3 changed keys in 25 h in the churn probe; CB18-S dropped.
  CH199 reads a static class from the same stream, not edits.
- **Wallet features, skilled-wallet toxicity, copy rules, holder snapshots.** E026 is registered and its modules are
  frozen to 12-07; WS1 P2-P4 null; CB8-H sealed. Not proposed.
- **Tick-rule signing of single prints (last trade above or below the mid as the taker's side).** Qin and Yang 2026
  (prior art): the tick rule is 49.8% accurate on these markets; CH193 uses the last print's position *at the touch*
  only to name the wall's side, and only in a reported secondary.
- **Maker mark-out objects** (adverse selection by state, toxicity forecasts judged on fills). J4-R's and CB13-T's
  holdouts refuse the worn days; E025 part B owns signal-conditional fills; CH192's and CH193's maker routes are
  "gross, no fills" by construction.
- **E015, E022, LT5 and LT6 moderators during their windows** (quote-only sub-classes, hollowness interactions, post-
  move skew interactions, path-shape interactions). Double counts on overlapping origins. CH195 and CH197 share V's
  reader but not V's origins or state; CH196 is declared an E015 moderator and waits for E015's analysis commit.
- **Resolution-level LT7 primaries** (calibration by provenance, theta, source class, YES-optimism by class). Over 21
  days only crypto and sports resolve in the thousands and the ex-crypto rule removes them; CH198 and CH199 are
  engine-first on `res_7d` for that reason, with CH175's last-mid proxy as the later registered route.
- **Term-structure momentum (1 h against 1 d against 1 w sign agreement), move over spread, reversal x liquidity.** The
  champion's inputs; C03, C12 and SB2-L1 own them; a LightGBM learns the interactions. Not proposed as mechanisms.
- **The venue's displayed 1 h change as a retail trigger; front-page rank.** CH37, CH176 (census only, needs the
  venue's sort). Not proposed.
- **Spread widening with no trade as a volatility forecast.** Rejected in round 11 as textbook; CH192 is the level
  ratio with the lead-minus-lag verdict and a maker route, declared as the difference.
- **Reward-rate, max-spread and min-size shocks from the `reward_params` stream.** CH152's natural experiments; the
  stream makes them readable at 2 h but the population of shocks is unprobed and likely tens a day. A map, not a test.
- **Taker routes as primaries anywhere.** The cost model's 2.9-7c hurdles against grosses of a fraction of a cent;
  every taker route here is reported, never a verdict.
- **UMA proposal and dispute objects, holding rewards, tick regimes, reward cliffs, series base rates and rolls,
  genesis and first-day prints, seed anchors, mention baskets, external anchors and clocks, barrier confusion, quoter
  grain, wake-up prints, book age, breathing book, mint share, turnover, synchronous prints, exit pressure, cost and
  lag maps, quoted against traded moves, walked flow, trains, attention surges, breadth, class-conditioned longshots,
  arrivals and cancellations, age of the move, opens and closes, concentration, hollow liquidity, program against
  human, last-mid proxy, front page, silent edits, races, jump or grind at the print clock, high-water mark, overhang,
  alone or with the crowd, the farmer's choice, clips, the makers' vote, deadline moves, sibling birth, provenance,
  overdue.** CH01-CH190: not re-proposed; where an idea touches one, the parent is named and the new clock, population,
  state or join is stated (CH191 on CH180/E021/E004; CH192 on CH33/CH43; CH193 on E015/CH20/CH180; CH194 on E021/CH37;
  CH195 on E022/CH190/E003; CH196 on E015/CH172; CH197 on E003/CH190/CH183; CH198 on CH62/CH105/CH189/CH187; CH199 on
  CH28/CH75/CH87; CH200 on CH147/CH178; CH201 on CH16/CH45/CH152/CH183).

---

## 5. Sources consulted

### 5.1 No host probe, no network, no data-dumps read this round (by instruction); what was read instead
The ledger's 2026-10-20/21 entries (LT4 censuses q0482/q0483; CB13-R q0281/q0282; CB14-W q0305; CB15-P q0347; CB18
routing; SB2-J4-R VOID; LT3 registration; E026 census q0544/q0545 and registration 7777ca66; LT5 and LT6 drafts and
reviews; signal-engine entries se14-se17, the first prospective leaderboard and the development walk-forward q0514);
`LIVE_TESTS_4.md` sections 4 and 17; `LIVE_TESTS_5.md` sections 0, 1.8, 7, 8 and 10; `LIVE_TESTS_6.md` sections 0, 6
and 7; `CREATIVE_BATCH_18.md` sections 0, 3 and 14 and `seals/cb18_routing.json`; `signal_engine/NORTH_STAR.md`,
`DESIGN_V1.md` sections 1-19, `CANDIDATES.md`; `COLLECTION_HOST.md`; `NEW_STREAMS_2026-10-19.md`;
`PRIOR_ART_2026-10-19.md` section 1; `AREPO_V2_CHECKPOINT.md` (interactive state and exact next actions, 2026-10-21);
`CREATIVE_HYPOTHESES_2026-10-25.md` (round 11: header, sections 0, 0.1, 3, 4, counts table) and the lead sentences of
CH01-CH179 from rounds 1-10; `scripts/oracle/streams_crontab.txt` and `backend/scripts/collect_reward_params.py`
(docstrings only). The cost-model, maker-rewards and round-9 probe figures are quoted as round 11 quoted them.

### 5.2 External literature (named, not fetched)
Hong and Stein 1999 (gradual information diffusion); Barndorff-Nielsen and Shephard 2004 (jumps against diffusive
variation); Rosu 2009 (patient traders in limit-order markets); Glosten and Milgrom 1985 and Copeland and Galai 1983
(the maker's quote as an option and its update); Easley and O'Hara 1992 (time and the process of security price
adjustment); Karpoff 1987 (the volume-volatility relation); Kyle 1985 (price impact per dollar); Cao, Hansch and Wang
2009 (the information content of an open limit order book beyond the touch); Cont, Kukanov and Stoikov 2014 (order
imbalance and price changes); Amihud 2002 (section 4 only); Qin and Yang 2026 and the other prior-art working papers
as `PRIOR_ART_2026-10-19.md` lists them (section 4 only).
