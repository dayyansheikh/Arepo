# Creative hypotheses, round 14: census survival on the streams the host already captures (2026-10-28)

`evidence_role: none` | status: **IDEAS ONLY, nothing tested, nothing registered.** No edge, calibration, tradability or
profitability claim. AREPO never trades; every "money route" below is a paper rule to be tested on historical data and
then prospectively. Written by the creative-lead pass at the user's request (written 2026-10-22, on parent `af960b80`
(`chore/arepo-claude-setup`, merged three times into the worktree `feat/creative-r14`: a first pass drafted the file on
`9d84f608`, a second checked, corrected and completed it on `af960b80`); the file carries the round's planned date as
earlier rounds did). Round 1 is `CREATIVE_HYPOTHESES_2026-10-15.md` (CH01-CH34), round 2 `-16.md` (CH35-CH59),
round 3 `-17.md` (CH60-CH78), round 4 `-18.md` (CH79-CH98), round 5 `-19.md` (CH99-CH117), round 6 `-20.md` (CH118-CH130),
round 7 `-21.md` (CH131-CH143), round 8 `-22.md` (CH144-CH155), round 9 `-23.md` (CH156-CH168), round 10 `-24.md`
(CH169-CH179), round 11 `-25.md` (CH180-CH190), round 12 `-26.md` (CH191-CH201), round 13 `-27.md` (CH202-CH211); this
file starts at **CH212** and repeats none of them. Where an idea builds on an earlier one, the parent is named and the new
mechanism, clock, population or join is stated. Every number quoted from an AREPO document is a development, census or
probe result, not evidence. One file; no code, no queue specs, no other commits. **No network request, no host probe (no
`ssh oracle`) and no `data-dumps` read were used for this round** (by instruction); every count below is taken from a
named AREPO document (the ledger's 2026-10-21 and 10-22 entries, `LIVE_TESTS_4.md` 17, `LIVE_TESTS_5.md` 7.3,
`LIVE_TESTS_6.md` 6.3, `LIVE_TESTS_8.md` 0-1 and 7, `seals/lt7_rewards_probe.json`, the three LT7 reward rulings of
10-22, `seals/cb18_routing.json`, `signal_engine/CANDIDATES.md`, `signal_engine/DESIGN_V1.md` section 3,
`CREATIVE_BATCH_13.md` H3/H8, `MAKER_REWARDS_STUDY.md` section 1, `reward_params_collector.py`'s and `ext_sidecar.py`'s
field lists, `LIVE_TRADE_MONITOR.md`, and round 13's structural facts where they are unchanged) and is named as such.
Where no count exists the entry is marked **unprobed** and the pre-registration census is the first gate.

## 0. How to read this file

**The brief that binds this round (owner priorities 2026-10-19 and 10-21; orchestrator brief for round 14: census
survival).** Since round 13 was written, every test of LT5 (F, H, R, J, O) and LT6 (V, D, B, K) died at its census; LT4
registered one of five; CB13, CB14, CB15 and CB18 closed at census or at pre-gates; LT7's own planning expects 0 to 2 of
five; LT8's author gives its three about one chance in two of all dropping. The brief for this round is therefore not
"more mechanisms" but **mechanisms that pass the gates that have been killing everything**: a large population on a
stream the host already captures completely (the 2-hourly full-universe captures with sidecars and two book sweeps, the
`reward_params` feed every 2 h, the hourly `gamma_rules` frame, PredictIt at 1 min, Smarkets at 5 min, ESPN odds at
10 min, the cross-venue poller, the live trade monitor), strata that are permutable by construction, a planning MDE
under the cost-aware floor at the *low* end of the planning count (LT5/LT6's pessimistic formula at LT7's multiplier and
design effect, with the F-MDE of any falsification arm), a money route after costs (about 5c a dollar round trip for the
median taker; maker rewards where relevant), a signal-engine feature family with a proposed embargo token and date, and a
reader that becomes a light prospective live test quickly (net lane, < 500 MB). Category-agnostic, category as a
parameter (sports inclusion is the owner's call). Two facts are new: LT7's reward probe (`seals/lt7_rewards_probe.json`,
q0601c): `clob_rewards` is null on **62.2%** of sealed non-sports ex-crypto market-captures and **11.8%** of market-days
(30,543 of 258,393) switch between null and listed within a UTC day (counts only); E022 (LT4) and E026 (copy skilled
wallets) are registered. Section 0.1 diagnoses, from the recorded drop reasons, why ideas die; 0.2 turns the diagnosis
into the rules every idea here obeys. This round's family is **LT9**, proposed after LT8.

**What changed since round 13 (from the ledger entries of 2026-10-22 05:30Z to ~17:45Z, `LIVE_TESTS_8.md` sections 0,
1.0, 1.1 and 7, the three LT7 reward reviews of 10-22, `CANDIDATES.md` rounds 5 and the 06:10Z notes, the checkpoint of
10-22 10:45Z).**
- **LT5 is CLOSED with no test** (q0561 06:05Z: F, H, R dropped; q0562 07:35Z: J, O dropped; `LIVE_TESTS_5.md` 7.3) and
  **LT6 is CLOSED with no test** (q0582 06:35Z: D, B, V dropped; q0583 06:50Z: K dropped; `LIVE_TESTS_6.md` 6.3). All
  nine drops are uncounted (before registration). The drop reasons are tabulated in 0.1.
- **E022 (LT4, hollow liquidity, CH174) is REGISTERED** (06:20Z; k = 1; window 2026-10-26..11-16; single analysis not
  before 11-17T12:00Z; the `hollow` token to 11-18 protects it; its S2 secondary is a reward-versus-non-reward split,
  which keeps the `rewards` token to the later of 11-18 and E022's analysis commit).
- **LT8 is DRAFTED and design-text frozen** (07:45Z; `LIVE_TESTS_8.md` at c124db50, sha256 `5e61c20b…`): CH203 (the
  quiet book), CH202 (the sweep clock), CH204 (the market's own clock), one Holm family k <= 3; proposed window
  2026-12-30..2027-01-20, analysis on or after 2027-01-21T12:00Z, pin before the earlier of 2026-11-15T12:00Z and
  `T_E015`. The author's declared odds: census survival 0.30 / 0.25 / 0.10, **expected k about 0.65, about 0.47 that all
  three drop**. CH205 deferred (sports scope), CH206 a map first. Its census-code check (12:40Z) is **FIXES_REQUIRED**
  (slots must be derived from the seal, not the local scan; `in_band` mechanical for every market; count gates on
  pre-exclusion counts; zero-filled correlation gates; re-vendor from the hash LT7's censuses actually run on).
- **LT7's reward field, three rulings in one day.** q0601b fired its `common` rule (null `clob_rewards` 0.60-0.65 every
  day; `[]` never; `rewards_min_size` / `rewards_max_spread` never null) and the challenger ruled **(B) with changes**
  (11:10Z; amendment 13.6, `null_as_unrewarded_v1`; design sha256 `31baf5e5…`). The counts-only probe q0601c then fired
  rule (c) (switching 0.118 > 0.05; `order_min_size` null 0.0012; malformed 0) and the challenger ruled **(C) causal
  listed carry-forward, `listed_carry24h_v2`** (16:10Z; amendment 13.7): about 3k switchers a day is about 30% of the
  about 9.7k listed markets per capture against a stable listed share (0.347-0.384), so **"Gamma leaving the field out
  is the likelier reading"**; `rewarded_k` = 1 if any sealed capture in slots [k - 11, k] listed a programme with rate
  > 0 for day(k); carried units take the source capture's band parameters; no slot after k is read. The carry re-check
  (commit 64acdbc4, design `575eb1dd…`) was FIXES_REQUIRED (F-feasibility pairs on incomplete carry windows; unit counts
  can move through `in_band`; a silent fallback); **the 13.7 erratum applied all three** (f4ff54ec: the pairs use the
  k-only v1 reward and `in_band`; `in_band` enter / drop counts; a refusal without `rew_raw`; design sha256 now
  `8fc83a73…`, code `live_tests7.py` e1c5c0c6). **CV7 (q0602, CH193's semantic gate; it reads no reward field) is done on
  the host** and CC7 (q0603) and CS7 (q0604) are promoted on that code (ae2a4a65); CV7's counts are not yet in
  `LIVE_TESTS_7.md` 6.3 ("None yet") and nothing here reads them. LT7's censuses must finish before 2026-10-28T03:30Z.
  **Not verified by the ruling and open for a census here:** Gamma's semantics of the omission; whether
  `rewards_min_size` / `rewards_max_spread` at null captures equal the listed values; flips across UTC days.
- **Embargo withdrawals and LT8 tokens applied (12:00Z):** `event` released (se8 / se10 visible; first fits ~10-27);
  `rewards` 11-22 -> 11-18 (E022 S2 only); `flow` 11-22 -> 11-16; `vote`, `clips`, `deadline`, `siblings`, `mm_fresh`
  withdrawn; new `quietbook`, `swclock`, `sched` to the later of 2027-01-23T00:00Z and LT8's analysis commit; `book` /
  `book0` 12-31 -> 2027-01-23. The promotion K went 5 -> 7. `se20_lgbm_crypto` (Binance spot reference) is active.
- **E026 is REGISTERED** (10-21 15:20Z; collection 10-25..11-15; analysis on or after 12-06T12:00Z; the five copy-skilled
  modules and two specs are frozen to 12-07). MC1 q0116f timed out at 6 h and is parked. CB16-K's census ran (no test).
  Host 2 OCPU / 12 GB; data-dumps 33 of 40 GB; snapshot retention temporarily 10 days until LT7's q0604, then 8 days.

### 0.1 Why ideas die at census: the recorded drop reasons (counts only; sources named) and the five patterns

**Every census drop and pre-gate closure of the LT and CB programmes since LT4, with its binding gate.**

| Test | Idea | Binding gate(s) as recorded | Source |
|---|---|---|---|
| LT4 E020 | CH169 arrivals and cancellations | strata share 0.055 (day) / 0.132 (block2) < 0.50; projected cancellations 14,028 < 15,000; MDE 0.526c > 0.5c | ledger 10-21 ~18:55Z; `LIVE_TESTS_4.md` 17 |
| LT4 E021 | CH170 the age of the move (trade-sample clock) | strata 0.005 / 0.018; MDE 1.060c | same |
| LT4 E022 | CH174 hollow liquidity | **PASS**: coverage 0.9996, residual-IQR share 0.827 over 301 markets, block2 strata 0.599, tercile MDE 0.256c, DE 6.196 (`m_21` 260.8) | same; registered 10-22 |
| LT5 F | CH184 alone or with the crowd | **only** the pessimistic MDE: 1.01c > 0.5c (DE_gate 10.3 from a projected mean family cluster of 465); every other gate passed (idiosyncratic 104,790, common 8,148, permutable 0.53) | `LIVE_TESTS_5.md` 7.3 |
| LT5 H | CH181 the high-water mark | near 1,082 / far 3,329 projected (< 3,150 / 15,750); `hwm_incomplete` 0.55 (96-slot look-back on a 10-day retention); within-market SD of `d_hi` >= 1c in 0.45 of markets; market-strata share 0.0; NaN correlation | same |
| LT5 R | CH183 the farmer's choice | crossing share 0.21 < 0.25 (904 markets); design MDE 1.03c (DE_gate 11.9); unrewarded cells 0 (an empty-`clob_rewards`-as-NaN parse, disclosed); rewarded inside 299,177 / outside 221,183 passed | same |
| LT5 J | CH180 jump or grind | 63.7 qualifying units a pass < 120; permutable 0.0 / 0.009; MDE 2.16c | same |
| LT5 O | CH182 overhang (token-weighted) | 372 covered units a pass < 600; within-market IQR >= 1c in 0.44 of markets; MDE 0.84c | same |
| LT6 D | CH187 deadline moves | 3 later by-date units in 9.08 days against >= 3,150 (697,757 unchanged) | `LIVE_TESTS_6.md` 6.3 |
| LT6 B | CH188 sibling birth | 0 birth units against >= 630 (616,926 no-birth) | same |
| LT6 V | CH190 the makers' vote | **one gate**: within-market corr(zv, z v_prev) 0.595 > 0.5 (pooled 0.566); projected 331,728, coverage 0.93, tercile MDE 0.35c all passed | same |
| LT6 K | CH185 clips (footprints without wallets) | 13 clip units in 1.92 days (projected 142 against >= 8,400); clip share 0.0066; permutable 0.0 / 0.08; MDE 5.75c | same |
| LT7 CH194 | the hour-held move | withdrawn before registration: Gamma's `chg_1h` timing untestable by any gate; informed by E002/E004 | ledger 10-22 ~00:30Z |
| LT7 (planned) | CH195, CH197, CH193, CH192, CH191 | author's planning at DE 6.196: F-MDE 0.75c / 0.66c for the level states; "every remaining test is likely to drop at census; expected k 0 to 2" | `LIVE_TESTS_7.md` 0 (as round 13 quoted it) |
| LT8 (planned) | CH203, CH202, CH204 | author's odds 0.30 / 0.25 / 0.10; CH203 passes its F-MDE only at `n_eff` >= about 1.0-1.4M; CH204 needs about 2,550 hot units a day | `LIVE_TESTS_8.md` 0 |
| CB13-R | CH118 barrier confusion | basis 0.915 < 0.95; frame completeness 0.782 < 0.98; events 58 < 60; GRP MDE 0.658 > 0.60 | ledger 10-21 ~18:55Z |
| CB14-W | Wikipedia-frame ideas | 58 markets < 150; 46 events < 60; 38 subjects < 40; audit precision 0.679 | same |
| CB15-P | PredictIt pairs | 37 pairs in 12 events against >= 60 in 30 | same |
| CB18-S | CH177 silent edits | GS2, GS4, GS5 fail; planning MDE 3.64c / 1.37c | `seals/cb18_routing.json`; ledger 10-21 ~20:05Z |
| CB18-P | CH172 program against human | GP1, GP5, GP6 fail | same |
| CB8-W1 | worn-pool replay | 5 eligible worn markets of 192 found (20 required): "not testable (source)" | ledger 10-22 ~00:15Z |
| CH199 | the resolution-source class (`gamma_rules`) | frame 44.7% of 18,232 eligible non-sports; parseable host 19.9% < 30% | `CANDIDATES.md` row 17 |
| E026 | copy skilled wallets | registered, but DE 23.9 and an MDE 3x its floor: Inconclusive by design | round 13's fact (E026 census) |

**The five patterns (my reading of the table; each is a design rule in 0.2).**
1. **Rarity.** A state defined by a rare event (an `end_date` edit: 3 in 9 days; a birth: 0; a clip train: 13; a
   boundary crossing: 21% of rewarded units in crossing markets; a cancellation mover: 14,028 projected) gives fewer
   than one unit per market-day, so the market x day stratum is empty (strata 0.0-0.13) and the MDE is 1-6c. **The count
   of units was never the problem where the state is dense (E020 had 14,028; F had 104,790): the problem is units per
   market.**
2. **Sampled streams.** Every trade-sample unit died (E021 0.005, J 63.7 a pass and 0.0, O 372 and 0.44, K 13; CB18-P):
   the rotating 2,000-market active-frame sample gives 60-400 units a pass with no within-market recurrence.
3. **Levels.** The one test that passed every count and MDE gate and still died (V) died on its own persistence
   (corr 0.595 with its lag); the level states LT7 kept pay 2-3x for their falsification arm; H's lifetime extreme is a
   level with a 96-slot look-back that the 10-day retention cannot serve (`hwm_incomplete` 0.55).
4. **Frames.** Every external or cross-venue frame gave tens of events (CB13-R 58, CB14-W 46, CB15-P 12, E026's DE 23.9);
   the one stream frame (`gamma_rules`) covered 45% of its population; the worn pool 5 of 192.
5. **Field semantics and the design effect.** R lost its unrewarded class to a parse; LT7 lost a day to the null (62%)
   and the switching (11.8%) of `clob_rewards`; CH194 died on a venue-computed field; F died on nothing but a DE of 10.3
   from family clusters of 465, with every count and correlation gate passing. **LT8's lesson (i) stands: the MDE gate,
   not the count gate, kills.**

**What survived and why (E022).** A continuous state (`h`) defined on *every* sweep-covered traded mover (coverage
0.9996), with within-market spread (residual-IQR share 0.827), on a population that recurs within market (block2 strata
0.599), in small clusters (DE 6.196), read from two streams the host already captured. Survival is not a property of the
mechanism; it is a property of **where the state lives (a complete panel), how dense it is (every unit), how it moves
(an innovation, not a level) and how it clusters (a declared member cap).** This round builds every idea from those four
properties first and argues its mechanism second.

### 0.2 The design rules of this round (binding; each maps to a pattern of 0.1)

1. **Panel-complete units (patterns 1, 2, 4).** Every LT9 unit is a market x capture on a stream the host captures
   completely at the 2 h cadence: the captures and their sidecar (every eligible market; `ext_sidecar.py` writes
   `received_utc`, `page_index`, `rewards_min_size`, `rewards_max_spread`, `clob_rewards`, `volume_num`, `open_interest`,
   `competitive`, `accepting_orders`, `order_min_size`, `order_price_min_tick_size`, `created_at`, `start_date`,
   `uma_resolution_statuses`, the `event_*` fields on every row), the pass sweeps (`book0` coverage 92-94%, the traded
   subset 0.9996) and the `reward_params` feed (every rewarded market the CLOB serves: 13,661 on 10-20). **No trade-sample
   unit, no monitor print as a unit, no external, text or cross-venue frame as a primary.**
2. **Dense states (pattern 1).** The state is defined on every unit of its panel (a continuous innovation, CH214) or is a
   per-interval event that occurs on a large share of market-days and is read on **all 12 slots** of the market-days on
   which it occurs (CH204's once-per-market-day structure: CH212, CH213), so the market x day stratum holds 12 units by
   construction and the Freedman-Lane null (the slot does not matter given the market-day) is the hypothesis's
   complement. The IQR / within-market-SD identification gate is defined on the market-days where the state occurs.
3. **Innovations and crossings, never levels (pattern 3).** The tested term is a change between two pre-origin
   observations (CH214), a crossing (CH213) or a switch (CH212); the level is a control; the planning `r_w` of the
   far-future twin is <= 0.3; the F-MDE is a verdict condition where it is under the target's floor.
4. **Look-backs <= 12 slots (pattern 3, H).** Nothing here reads more than 24 h of a market's own history (LT7's 13.7
   carry window is exactly 12 slots); nothing needs the 84-slot windows that the retention cannot guarantee.
5. **Field semantics declared before any count (pattern 5).** The CLOB's `reward_params` feed is the programme ledger
   (native and sponsored configurations, rates, start and end dates, the sponsor count, the computed daily totals; served
   every 2 h since 2026-10-20T23:20Z); Gamma's sidecar is the display. `rewarded` as a *control* follows LT7's 13.7
   (`listed_carry24h_v2`); the omission is a *state* only in CH212, which reads it as the display's event and lets the
   CLOB feed adjudicate. The `in_band` definition is mechanical for every market (LT8 census-code fix 2).
6. **A stream only where it covers its own population (pattern 4).** `reward_params` covers every rewarded market; the
   sidecar every row; the sweeps 92-99.96%. The monitor (every taker print >= $1k, universe-wide) covers its population but
   its non-sports ex-crypto population is a few hundred prints a day (CB13 H3/H8), so it is engine-first (CH216) with a
   sports-parameter test option. PredictIt, Smarkets, Kalshi: engine-first by round 13's rule 7, unchanged.
7. **The design effect and the kill line (pattern 5).** Rewarded-panel and whole-panel families plan at DE 31 (events
   capped at <= 10 eligible members; larger ladders a reported arm) and DE 51 (uncapped); sparse print market-days at a
   declared 13; mover families at E022's 6.196; the kill line of every test is stated as **the count at which its MDE gate
   passes**, and an idea whose MDE at the low planning count is over the floor is engine-first, said so in its entry.
8. **Floors.** 0.5c gross per share for a mid or magnitude target; **1.0c (one tick on a 0.01 book) for a spread target**,
   and the F-MDE cap equals the target's floor (CH206's precedent in round 13).
9. **Census on a fresh seal (patterns 2, 4; LT8 fix 1).** LT7's seal (112 captures, 47 sweeps, 10-12..10-21) holds one day
   of `reward_params` (from 10-20T23:20Z), so the rewarded-panel censuses run on a **fresh 10-day seal of the four 2 h
   streams** taken at census time (captures, sidecar, sweep 1 of each pass, `reward_params`), slots derived from the seal;
   CH212's census can run on LT7's seal alone (sidecar fields only) and is the cheapest in the programme. Counts only;
   per-capture streaming reader; < 500 MB; net lane.
10. **Pin early and name what was seen.** q0601b and q0601c are counts-only looks at the reward field's null structure
    (no prices); the three LT7 rulings and LT8's census-code check are disclosed in every entry that reads the field; the
    `b0_gap` diagnostic is disclosed wherever a pre-origin sweep meets an origin mid (none of the LT9 primaries does).
11. **Money routes are maker-side or hold-to-resolution.** The reward programme's scoring rule, as `MAKER_REWARDS_STUDY.md`
    quotes it from the venue's documentation: score `((v - s) / v)^2 x b` per quote (v the market's `rewardsMaxSpread`, s
    the quote's distance from the midpoint, b its size), `Q_min` with c = 3.0, "two-sided only outside [0.10, 0.90]" (the
    study's row wording, quoted as is; the venue's page is re-read at the pin, since the usual reading is the reverse,
    two-sided quotes required while the mid is inside [0.10, 0.90] and one-sided quotes scored outside it; nothing below
    depends on which), sampled once a minute at a random offset, a daily UTC epoch paid at midnight UTC, $1 minimum. A
    displayed touch
    therefore scores iff spread / 2 < v, and a quoter alone in the band takes the whole minute's share. Taker routes are
    reported, never a verdict (2.9c at >= $100k, 4.5c median touch, 7.2c at $1k-10k; sports 5.2c).

**Structural facts this round relies on (counts only; sources named; no new probe).**
1. Eligible markets a capture (engine base eligibility): 42,161-51,790 (DESIGN_V1 sections 3 and 16, as round 13 quoted);
   non-sports about 30,000 (derived); eligible non-sports on the 10-21 22:31Z capture 18,232 (CH199's narrower filter).
2. **The reward probe (q0601c, `seals/lt7_rewards_probe.json`, non-sports ex-crypto market-captures, 10-12..10-21, 112
   sidecars):** rows 2,774,846; listed 1,047,747 (37.8%); null 1,727,099 (62.2%); `[]` never; malformed 0; `order_min_size`
   null 0.12%; listed programmes with zero rate on the day 0. Per day: markets seen >= 2 times 24,819-27,821; **switching
   markets 2,112-3,995 a day** (8.5% on the half-day 10-14, 10.2-15.5% otherwise); listed rows 94,624-117,710 a day (so
   about 9,000-10,700 listed market-captures a capture; the ruling says about 9.7k); rows 273,010-306,464 a day (about
   10.5-11.5 captures). The ruling's reading: Gamma omits the field on some captures of listed markets.
3. Rewards: 13,661 rewarded markets on the CLOB's current feed (10-20; all categories); 13,683 in the maker-rewards
   snapshot; native pool $138k-182k a day; a two-sided minimum quote earns a median $0.05-1.00 a day on about $19 of
   capital under current competition (MAKER_REWARDS section 1, as round 13 fact 6 quoted it). The feed's `start_date` rolls
   forward (ruling 13.6 item 6; the collector's docstring), so "future configurations" are partly rolls (a caveat for
   round 13's CH206 and for CH215 here).
4. Sweeps: 65,771 tokens a sweep, two sweeps a pass; `best_bid/ask`, `*_size_1`, `depth_*_1c/5c`, `n_*_levels`,
   `book_timestamp`, `tick_size`, `min_order_size`, `batch_receipt_utc`, `book_hash`; the touch unchanged in 90% of books
   within a pass (CH147); `book0` lag about 110 minutes, coverage 92-94% (DESIGN_V1 section 22).
5. Row fields: `volume24hr` present on 22% of rows; `last_trade_price` omitted on 56%; `chg_1h/1d/1w` venue-computed;
   `liquidity`, `end_date`, `best_bid/ask` (round 13 fact 4). Sidecar fields: 0.2 rule 1.
6. The monitor (`LIVE_TRADE_MONITOR.md`; CB13 H3/H8): Data API `/trades?takerOnly=true&filterType=CASH&filterAmount=1000`
   every 300 s, universe-wide; each print stored with receipt time, venue time, market, side, outcome, size, price; 7,242
   / 10,380 / 9,971 / 10,522 / 8,836 / 13,621 / 10,642 prints a day 10-12..10-18; about 1,400-2,700 markets and 600-1,100
   events a day; median receipt lag 450-541 s; prints crossing a touch aged <= 60 min over the 7 days: non-sports enriched
   about 2,360 in about 520 events (crypto 1,142; econ and finance 966; politics and geopolitics 2,065; other 530 by the
   H8 age buckets), unenriched about 2,020, sports about 12,700. Market context is fetched for at most 50 markets a cycle.
7. Streams (as round 13 fact 7 quoted the dry run and the modules): PredictIt 867 keys (about 200 markets); Smarkets 1,734
   keys, 677 books; ESPN 94 games, 76 with odds; `gamma_rules` 3,799 keys in the top-3,000 frame plus a 6-hourly full frame
   of open markets with 24 h volume, 2,383 new keys a day; Kalshi 116 pairs. Cadences confirmed by the resize record.
8. Event clusters: 33,849 over 2,581,045 triples in five UTC days (SB2-J4-R); E022's 2,539 in two days.
9. Costs (cost-model-v1, as round 13 fact 9): $100 taker round trip 2.9c at >= $100k, 3.9c at 10k-100k, 7.2c at 1k-10k; a
   5-share touch round trip 4.5c; a passive touch order fills 3.1% of the time within an hour and loses 2.38c to adverse
   selection against a 2 h mark (0.39c at >= $100k); makers about break-even before rewards (non-sports fill-weighted
   -0.37c); sports 5.2c.
10. Engine: se1 +0.041 nats over the champion on `dir_2h` (development); K = 7; `book0` K = 4 origin; `rewards` family
    se9 hidden to 11-18; `event` visible from 10-22T12:00Z; `movetype` and `absorbed` to 12-31 (volume changes and the
    traded flag isolated: CH193); `surprise` to 11-19; `participation` to 11-25 (event volume, liquidity, `competitive`).

**The reading that steers this round.** Round 12 read levels on the whole panel; round 13 read innovations and direct
clocks on the mover and book panels. Round 14 reads **the rewarded panel**, which has three properties no other panel has:
it is captured completely by two independent 2 h feeds (Gamma's display and the CLOB's programme ledger); its makers are
paid by a published formula that makes some of their behaviour *mechanical and dated* (a quote outside `max_spread`
earns nothing; a quoter alone in the band earns everything; a programme that ends stops paying at a stated time); and the
one field that describes it is, by the challenger's own reading, omitted by the venue on a third of the captures of
listed markets, which is itself a per-interval event on 3,000 markets a day. The ideas: the display's omission as a
serving-path clock, adjudicated by the CLOB (CH212); the displayed spread crossing out of the band, against the same
crossing where no band exists (CH213); the farmers' depth arriving behind an unmoved touch, read on the CLOB's book before
the origin (CH214); the programme's scheduled end (CH215, a map). Then the universe-wide print stream the host already
runs (CH216, engine-first), two serving-path and display clocks on the captures (CH217, CH218), two direct book and
dormancy clocks (CH219, CH220) and the proposal clock on the sidecar (CH221, engine-first pending a ruling).

**Data labels.** `A` = on the host now (captures, sidecar, two sweeps, trade samples, the monitor, the Kalshi poller, the
engine's `quotes/`, `features/` and aux tables including `book0`, the five keyless streams, `reward_params`). `A~` = on the
host but a join or matcher has to be written and counted first. `P` = a fetch is needed (none here). **Sealed and not
usable by anything here:** LT2's, LT3's, LT4's (E022's) and LT7's stores and LT8's once registered, CB16's and CB17's
stores, CB8-H's holders, E009/E010's `cross_venue_live/` to 2026-11-03, E011's `surprise_live/` to 2026-11-10, E025's and
E026's stores and the E026 frozen modules. J4-R `[2026-10-16, 2026-10-21)` and CB13-T's holdout `[2026-10-21, 2026-10-26)`
are refused for every maker mark-out object; nothing here is one.

**Windows and registration this round proposes (LT9).** A ninth live-test family, registered separately from LT2-LT8 with
its own Holm family (k <= 4), on two lanes the designer chooses between by capacity, both stated now:
- **Ordered lane.** `REGISTERED_UTC` = the first 00:00Z at least 24 h after the LT9 registration commit, at least 24 h after
  LT8's `END_UTC` if LT8 registers, and never before **2027-01-21T00:00Z**; if LT8 drops entirely at census (recorded),
  LT9 takes LT8's slot (never before 2026-12-30T00:00Z, at least 24 h after LT7's `END_UTC`). 21 days, single analysis at
  least 36 h after the end, no extension. Pin (states, estimators, gates) by **2026-12-07T12:00Z**, before `T_LT7`
  (12-30T12Z) and `T_LT8`; the reward-field states are adjacent to E022's S2 (reward split) and LT7's `rewarded` control,
  so a pin after `T_E022` (11-17T12Z) labels CH212 and CH213 *informed (E022)*.
- **Fast lane (the brief's "quickly").** CH212, CH213 and CH214 read no mover population and no state LT7 or LT8 tests (the
  `rewarded` control is a field, not a hypothesis), so they can run in the empty slot between E022's end and LT7's start:
  window **2026-11-17T00:00Z .. 2026-12-08T00:00Z** (ending exactly at LT7's earliest `REGISTERED_UTC`), analysis on or
  after 2026-12-09T12:00Z, provided the design text is frozen before **2026-11-14T12:00Z** (before `T_E015` and `T_E022`)
  and the censuses run on a fresh seal of 10-24..11-02. Collection overlap with E015, E022, E026 and E011 is overlap only
  (different hypotheses, no pooling, stores never opened). If the pin is not before 11-14T12Z, the ordered lane applies.
- Either lane: the census days and the window should both be on winter time (the fast lane's are; LT8's DST disclosure
  does not recur); year-end disclosures as LT8's if the ordered lane runs over the holidays. E-numbers at registration.

**Hygiene that binds every idea.** Decision time is the latest input's own receipt (the Gamma row's `received_utc` for
capture states; the `reward_params` capture's receipt for programme states; the sweep's `batch_receipt_utc` for `book0`
states, never a sweep of the same pass), states are computed from that input and strictly earlier ones; targets are
price-based (the complete captures' Gamma mids and spreads) and start after the decision time: the next interval's change
`mid_{k+1} - mid_k` or spread change where the state is not a move of the same market (CH212, CH213, CH214), `c_skip` for
move-continuation arms, daily units for slow states; nothing reads Gamma outcome fields except the engine-first ideas,
which use the engine's receipt-timed `res_7d` (CH221 states the one exception it needs a ruling on). Clustering is CR1 on
event, two-way event x UTC day and UTC day with p the largest, the event t on `G - 1` where a class is sparse, and an
ex-crypto primary everywhere (LT7's rule 7, adopted); **the primary is a within-market contrast or slope estimated by
expanding-past demeaned OLS over all eligible units, the Freedman-Lane permutation gate within the census-fixed stratum
(market x UTC day by construction here; block2 where stated) is the binding gate, the liquidity-tier correlation gate
(|corr| <= 0.5 within and pooled) and the AR(0.9) size scenarios bind for every state, and F (one rule: Δ one-sided
p < 0.05 and Δ̂ >= 0.5 x beta-hat, LT7's form) is a verdict condition for every state whose census F-MDE is <= the
target's floor and a reported label otherwise.** Sports stays a parameter (the sidecar's `fee_type` plus CB17's frozen
sports list); every idea reports the sports arm uncounted.

**Scores.** N novelty (1-5), EV expected value if true (1-5), **L live-ready (1-5):** 5 = a pure reader over the sidecar
or the `reward_params` feed (no sweep), population counted by a named probe, census on files already sealed; 4 = pure
reader including `book0`'s sweep, population bounded above by a named count; 3 = pure reader with an unprobed and
possibly small population, or a map first; 2 = a stream whose coverage of the population is unprobed; 1 = fetches or
weeks. My judgement, not measurements.

**Planning-MDE arithmetic used throughout (LT5/LT6's pessimistic form at LT7's constants, stated once).** Class contrast:
`MDE = 3.47 x SD x sqrt(1/n1_eff + 1/n2_eff) x sqrt(DE_gate) x 1.5 x sqrt(max(1, VIF_w))`; slope per SD of a continuous
state times the tercile gap (about 2.2 SD): `MDE = 3.47 x SD / sqrt(n_eff) x sqrt(DE_gate) x 1.5 x sqrt(VIF_w) x gap`.
`n_eff` = units in markets with >= 2 units of the population in the census days (planning: 80% of raw). `DE_gate` =
`max(floor, 1 + (m_21 - 1) x 0.02)`: rewarded-panel and whole-panel families **31** (<= 10-member cap) and **51**
(uncapped); sparse print market-days **13** (declared); mover families E022's 6.196; daily-renewed external frames 3.0.
`VIF_w` 1.3 for labels and sidecar states, 1.5 for book states. SDs: 2 h change 4c (3c in quiet books), |2 h move| 3c,
spread change 2c, 24 h change 6c. **F-MDE** = `MDE x sqrt(2 / (1 - max(0, r_w)))` at the planning `r_w` stated per idea,
capped at the target's floor as a verdict condition (0.5c mid and magnitude; 1.0c spread). Every MDE is quoted at the
low and high planning counts and at a quarter of the low one.

**Counts table (what was counted before each idea was written; daily unless stated; the source named).**

| ID | Unit | Count on the host | Source |
|---|---|---|---|
| CH212 | non-sports ex-crypto market x capture on a market-day with a null/listed switch of `clob_rewards` | **2,112-3,995 switching markets a day** (30,543 market-days in 10 days of 258,393 seen >= 2); about 11 captures each; omitted-while-listed slots per switching market-day **unprobed** (planning 2) | `seals/lt7_rewards_probe.json`; the 13.7 ruling |
| CH213 | Gamma-listed (carry 12 slots) or CLOB-listed non-sports ex-crypto market x capture whose displayed spread crosses 2 x `rewards_max_spread` | about 9,000-10,700 listed markets a capture (probe: listed rows a day over captures a day); crossing share **unprobed** (planning 1-3% a capture: 90-300) | probe fact 2; LT7 `in_band` |
| CH214 | CLOB-rewarded non-sports ex-crypto market x capture with sweeps of passes k - 2 and k - 1 before the origin and an unmoved touch | 9,000-10,000 x `book0` coverage 0.93 x quiet share 0.75: about 6,300-7,000 a capture | facts 2, 4; CH203's quiet filter |
| CH215 | CLOB programme with a scheduled `end_date` within 48 h on a market with > 48 h of life | **unprobed** (the feed's `end_date` field; starts roll forward; planning 10-60 a day; kill line 30) | collector docstring; ruling 13.6 item 6 |
| CH216 | non-sports ex-crypto market-day with >= 1 taker print >= $1k (all 12 slots as units) | about 530 enriched prints a day plus a share of 815 unenriched (CB13 H8 over 7 days); planning 600-1,000 prints in 350-700 markets a day | CB13 H3/H8; `LIVE_TRADE_MONITOR.md` |
| CH217 | every eligible row (optional-field presence count) | `volume24hr` 22% present, `last_trade_price` 44% present, `clob_rewards` 38% present; co-omission **unprobed** | round 13 fact 4; probe |
| CH218 | every eligible row with `chg_1d` and an own 24 h change | own 24 h coverage about 98% of eligible (`sp_rv6h` 98% as a proxy); `chg_1d` presence **unprobed** | DESIGN_V1 section 16 (as round 13 quoted) |
| CH219 | market x capture with two pre-origin sweeps and `book_timestamp` on both | about 28,000 non-sports with `book0` a capture; touched share between passes **unprobed** (10% within a pass: CH147) | DESIGN_V1 section 22; CH147 |
| CH220 | eligible market x capture with 12 own slots | `sp_rv6h` 98% of about 30,000; dormant (12 slots unchanged) share **unprobed** (1,477 books unchanged within 2 h a pass: CH149's count) | DESIGN_V1 section 16; CH149 |
| CH221 | sibling market x capture at the first capture whose sidecar shows a proposal on a member of the same event | **unprobed** (24,071 markets a day leave the listing, all categories: CH167; ex-crypto ex-sports proposals a day unknown) | CH167; `ext_sidecar.py` |

---

## 1. Map: where money might be on the panels that survive the census

The cost model fixes the frame: a taker needs 2.9c gross in the most liquid tier and 4.5c at the median; a passive fill
costs 2.38c of adverse selection against a 2 h mark; makers are about break-even before rewards; the programme pays
$138k-182k a day by a published, per-minute, per-quote formula. The census fixes the population: what recurs every day
on every market of a completely captured panel. So the money question for every state below is: **does an event the
venue's own feeds date (an omission, a crossing of a published band, an arrival of paid depth, a scheduled end, a print
the universe-wide monitor stamped) move the forecast of the next spread, the next move or the next maker yield, on a
population that recurs within market, and does it tell a maker when to be alone in the band, when to leave it, and which
displayed moves are not moves?**

| Family | What the host already dates that nobody has read | Money route |
|---|---|---|
| A. The rewarded panel and its two ledgers (CH212-CH215) | the display's omission of the programme against the CLOB's ledger; the displayed spread leaving the band; paid depth arriving behind an unmoved touch; the programme's scheduled end | maker: be alone in a broken band; leave when the pool splits; leave before the end; quote where the display hides the programme (fewer display-driven competitors); taker: never cross a broken band; trade after arrivals |
| B. The universe-wide print stream (CH216) | the venue time of every >= $1k taker print against the capture clock, on every market, not a 2,000-market sample | maker: widen after a large print; taker: follow fresh large buys in >= $100k markets (reported; sports parameter) |
| C. Serving-path and display clocks (CH217, CH218) | rows the venue served sparsely; the venue's displayed change against the host's own path | engine data quality (which rows and which displayed moves to trust); maker: fade display-driven chasing |
| D. Book and dormancy clocks (CH219, CH220) | the CLOB's own `book_timestamp` innovation; slots since the mid last moved | maker protection: an untouched book is nobody's quote; a dormant market's first move is a re-quote |
| E. The proposal clock (CH221) | the sidecar's resolution status appearing on one member of an event | hold-to-resolution NO on the siblings in the fee valley (reported; ruling needed) |

---

## 2. Hypotheses

### A. The rewarded panel and its two ledgers (parents CH16, CH19, CH45, CH71, CH116, CH152, CH183/LT5 R, CH201, CH203/LT8, CH206, CH209; the LT7 rulings 13.6 and 13.7; literature: Foucault, Kadan and Kandel 2005, Glosten and Milgrom 1985, the Telonex case as MAKER_REWARDS cites it)

**CH212. The display's omission and the two ledgers: on a third of the captures of a listed market, Gamma leaves the
programme field out; the CLOB's `reward_params` feed does not. The omission is a per-interval event on 3,000 markets a
day with an exact clock. If the omitted row comes from a different serving path, the row's other optional fields and its
price are stale too, and the next capture's "move" is partly a catch-up the display owes: a magnitude the host can
forecast, and a displayed move a maker should not chase. If instead the omission is the real listing churn, the farmers
leave at the switch and the spread widens. The CLOB feed and the sidecar's own row structure decide which test is run,
from counts, before any price is read.**
- Mechanism and why it is non-obvious. The challenger's 13.7 ruling reads the switching as Gamma omitting the field
  ("about 3k switchers a day is about 30% of about 9.7k listed markets per capture, against a stable listed share"), and
  solves LT7's problem by carrying the listing forward. That closes the *control* question and opens a *state* question
  nobody has asked: is the omission a property of the row, or only of the field? The sidecar stores, per row, the
  `received_utc`, the `page_index` and the presence of the other optional fields (`volume24hr` on 22% of rows,
  `last_trade_price` on 44%), so the census can tell, without a price, whether omitted rows are served differently
  (a later page, a different receipt offset, more omitted fields). If they are, CH37's artefact (a stale displayed mid
  that the UI's mover list shows as a move) has a per-row flag for the first time, and the money is the maker's: the
  next capture's displayed move after an omitted slot is the display catching up, not news, and the retail flow it
  triggers is flow to fade. If they are not (the field alone blinks), the display reading has no handle and the test is
  dropped by its own gate; the real-churn reading (route B) then needs the CLOB's set to churn in step, which the feed
  counts directly. Who pays: the taker who chases a displayed catch-up; the farmer who quotes a programme the display
  hides (route B's mirror, the map below). Why the crowd misses it: the omission is invisible on the site, and the only
  people who have counted it are LT7's probes.
- Data join and decision clock (`A`, L 5). Unit: non-sports ex-crypto eligible market x capture k on a **switching
  market-day** (at least one null and one listed `clob_rewards` among its captures of that UTC day; the probe's
  definition). State, per slot: `om_k = 1` if `clob_rewards` is null at k while listed at some slot in [k - 11, k - 1]
  (an omission of a listed market, LT7's carry logic read as an event; the ruling's `rewards_null_carried` by lag is
  this flag's census count); `om_k = 0` on the listed slots of the same market-day; the first-of-day slots with no prior
  listing are counted `unknown` and excluded. Decision time: capture k's `received_utc`. Row covariates read at k for
  the census and as controls: `page_index`, `received_utc - capture start`, presence of `volume24hr`,
  `last_trade_price`, `competitive`; the CLOB feed's listing of the market at the last `reward_params` capture before k
  (`clob_listed_k`). Controls: logit mid, |mid - 0.5|, spread, `log1p liquidity`, own 24 h change, `rv24`, tick stratum,
  slot-of-day dummies (11), the `rewarded` control exactly as LT7 13.7 defines it (carried 12 slots).
- Target and horizon. **Route A (the stale path):** `a = |mid_{k+1} - mid_k|` (SD 3c), within market-day; hypothesis
  (one-sided): E[a | om = 1] - E[a | om = 0] > 0 (the catch-up); M2: the signed catch-up `c1 = sign(mid_k - mid_{k-1}) x
  (mid_{k+1} - mid_k)` reported (a stale row understates the (k - 1, k] move and overstates the next). **Route B (real
  churn):** the spread change `s_{k+1} - s_k` in ticks of the market's `order_price_min_tick_size` (SD 2c; floor 1.0c);
  hypothesis: wider after a listed -> null switch where the CLOB feed also dropped the market. The route is **chosen by
  the census from counts** (below), never from prices; the other route is a reported label.
- Paper rule and economic check. Route A: maker, do not re-centre on a displayed move whose previous slot was an omitted
  row (it is the display catching up); fade display-driven flow after it. No taker route (the catch-up is in the display,
  not in the book: nothing to trade). Route B: the first farmer out at a real de-listing keeps the day's earned share and
  avoids quoting for nothing; the yield map (below) says where the display hides a paying programme. Engine: either
  route gives a row-quality weight for the champion's inputs (the North Star's forecast-quality object, CH217's family).
- Population arithmetic. 2,112-3,995 switching markets a day (planning 3,000) x about 11 captures = about 33,000 units a
  day, **690,000 in 21 days**; omitted-while-listed slots per switching market-day planning 2 (the ruling asks for the
  1-versus->= 2 transition count; unprobed): 126,000 omitted slots, 560,000 listed slots. Events: the switching markets'
  events, planning 1,500-3,000 in 21 days (unprobed).
- Permutation and cluster structure. Rule 2: all slots of a switching market-day are units, so the market x UTC day
  stratum holds about 11 units by construction (share 1.0 among full days). The Freedman-Lane null (given the market-day,
  which slots were omitted does not matter) is exactly the complement of either route. Binding scenarios: LT5 1 (iid
  label), 2 (persistent market rates), a declared **S15: a per-capture omission independent of the row, with an AR(0.9)
  |move| process** (the size must be <= 0.058; under this world the omission has no price content, which is the null),
  and LT4 L10's event clusters. **Venue-clock gate (round 13 rule 8):** if more than 50% of omitted slots fall in one
  slot-of-day, the omission is a venue cron and the state is collinear with the slot dummies: dropped. Clusters: event;
  `DE_gate` 31 / 51.
- Planning MDE. Route A class contrast, `n1_eff` 100,000 (omitted), `n2_eff` 450,000: `3.47 x 3c x sqrt(1/100,000 +
  1/450,000) x sqrt(31) x 1.5 x sqrt(1.3)` = **0.35c** (DE 31), 0.44c (DE 51); at a quarter 0.69c / 0.89c. F: the
  far-future omission (slot k + 4's `om`) is near-independent under the artefact reading (planning `r_w` 0.1): F-MDE
  1.49 x 0.35c = **0.52c** (DE 31): at the cap; a verdict condition only if the census `n_eff` is at least 1.1x the
  planning low end, else a reported label. Route B spread contrast, same counts, SD 2c: 0.23c / 0.30c, F 0.34c / 0.44c,
  under the 1.0c floor and cap: F a verdict condition.
- Confounders and the control. The slot of day (controlled by 11 dummies; the venue-clock gate); the market's own
  volatility (controlled); a real programme change coinciding with the omission (route B's object: `clob_listed_k`
  splits it); the carry itself (LT7 13.7 reads the same field as a control on the same captures: an input overlap, not
  a hypothesis overlap, disclosed; LT9's `rewarded` control is 13.7's); E022's S2 (the reward split of hollow liquidity:
  a different question on the same field; `informed (E022)` if pinned after 11-17T12Z); **informed, disclosed (rule 10):**
  the counts of q0601b, q0601c and the 13.7 ruling's reading were seen; no price was.
- Most likely boring explanation. The omission is field-level flakiness of one Gamma serving path with no price content
  (the challenger's own reading): the omitted row's mid is as fresh as any other row's, the co-omission odds ratio is
  about 1 and `page_index` does not differ, so route A's rule fails; and the CLOB feed does not churn in step, so route
  B's fails. Then the census drops the test and only the `rwblink` map remains, which is the design.
- Cheapest census (counts only; **LT7's sealed sidecars alone**, 112 captures, the cheapest census in the programme; or
  the fresh seal). Omitted-while-listed slots per switching market-day (1, 2, >= 3); the slot-of-day distribution of
  omissions; **the route test:** the co-omission odds ratio of `volume24hr` and `last_trade_price` on omitted against
  listed slots within market-day, the `page_index` share difference, the receipt-offset difference; the CLOB-feed churn
  (markets leaving the native feed between consecutive `reward_params` captures, against Gamma's listed -> null switches
  in the same interval; one day on LT7's seal, ten on the fresh one); whether `rewards_min_size` / `rewards_max_spread`
  at omitted slots equal the listed values (the ruling's open question). **Route rule, declared now:** route A if the
  co-omission odds ratio >= 1.5 or the `page_index` share differs by >= 10 pp; route B if the CLOB feed's departures match
  >= 30% of Gamma's listed -> null switches in the same interval; both (two primaries, k += 1) if both hold; **neither:
  dropped as a test, the `rwblink` family built regardless.** Kill also if switching markets < 1,500 a day or the
  venue-clock gate fails.
- Challenger feature: **yes.** `rwblink` (`se-aux-rwblink-v1`): `rb_om` (the omission flag at k), `rb_om_lag` (slots since
  the last omission), `rb_switch_day` (the market-day's switch count so far, slots <= k only), `rb_clob_listed`,
  `rb_disagree` (Gamma-null-window against CLOB-listed, and the reverse), `rb_page`, `rb_recv_offset_s`, from the sidecar
  and the last `reward_params` capture received before the origin. Read against `se1_lgbm_mm` and, once `rewards` lifts
  (11-18), `se9_lr_rewards`. Embargo: `rewards` to the later of 11-18 and E022's analysis commit (the same field) and a
  new token `rwblink` to the later of LT9's analysis commit and the lane's date (ordered lane 2027-02-14T00:00Z; fast
  lane 2026-12-11T00:00Z; filed at LT9's acceptance, later only afterwards).
- **The two-ledger map (counts only, no test; filed with the census).** Per `reward_params` capture, the market sets:
  CLOB-listed and Gamma-listed (carried), CLOB-listed and Gamma-null for the whole window ("hidden programme"), Gamma-listed
  and CLOB-absent ("ghost programme"), parameter mismatches (rate, band); for the hidden class the CLOB daily rate divided by
  the pre-origin in-band depth (`book0`'s band sums) against the agreeing class: the yield a farmer who reads the CLOB
  earns where display-driven quoters are absent. A maker's screen, not a verdict.
- Scores: N 4, EV 3, L 5. Parents: CH37 (the displayed artefact: here a per-row flag), CH152 (rate shocks: here the
  listing's display), CH201 (yield per posted dollar: the map), CH206 (the start: the CLOB's future configurations),
  CH209 (the farmer touch), LT7 13.6 and 13.7 (the control rulings this reads as a state), LT8 census-code fix 7 (the
  null taxonomy: unset / empty / zero / malformed / no sidecar, adopted for the census).

**CH213. The band break: a displayed spread that crosses out of the reward band earns nobody anything from that
minute, and a quoter who re-enters alone takes the whole minute's share. The crossing is a per-interval event on every
rewarded market, dated by the capture, with a published attractor. The spread after a crossing re-tightens faster in a
rewarded market than the same crossing re-tightens in an unrewarded market of the same width, because the venue pays for
the re-entry; the difference is the band's pull, and the first quoter back in is paid for being first.**
- Mechanism and why it is non-obvious. Spreads mean-revert everywhere (a widening is often one maker stepping off, and
  the touch refills); on this venue the reward formula adds a term no other market has: a quote at distance s >= v from
  the midpoint scores 0, so when the displayed spread exceeds 2v every displayed quote is unpaid and every farmer's bot has
  a reason to re-post inside v within minutes (the sampling is once a minute at a random offset: every minute outside the
  band is a minute of the day's rate forgone). CH45 reads the band's geometry as a screen, CH71 the band's edge at 0.90,
  CH116 strips the band's depth, CH209 flags the farmer's touch, CH183 (dropped) the farmer's side; none reads the
  *crossing* as an event with the unrewarded same-width crossing as its control. The control is the point: it separates
  the band's pull from ordinary spread reversion and from E004's mid bounce (which the spread's re-tightening partly is).
  Who pays: the venue (the pool), and the taker who crosses a broken band instead of waiting; the maker who stays out
  while the band refills. Why the crowd misses it: the site shows the spread and the "earn rewards" badge but not the
  band; whether the current spread is inside it is a number nobody displays.
- Data join and decision clock (`A`, L 5). Unit: non-sports ex-crypto eligible market x capture k on a **rewarded panel
  defined by the CLOB's feed** (`clob_listed` at the last `reward_params` capture before k; Gamma's carried listing is the
  sensitivity), plus the **unrewarded control panel** (markets on neither feed over the window). State: `s_k` = Gamma's
  displayed spread at k in ticks and in cents; `v` = `rewards_max_spread` (from the CLOB configuration; Gamma's sidecar as
  the sensitivity; the census prints the units and the two values' agreement); **break** = `s_{k-1} < 2v and s_k >= 2v`
  (the strict crossing: no displayed quote scores); the LT7-style crossing `s_{k-1} <= v < s_k` (`in_band` flipping) is
  the reported variant. For the control panel the same crossing is defined against the *rewarded panel's* `v`
  distribution: each unrewarded market is assigned the band of its matched rewarded market (same category, same liquidity
  tier, same tick stratum; a declared matcher, counted) so that "the same crossing where no band exists" is well defined.
  Decision time: capture k's `received_utc` (the `reward_params` capture is earlier). Controls: `s_{k-1}`, `s_k` (the
  level; the primary is the change), logit mid, |mid - 0.5|, `log1p liquidity`, own 2 h and 24 h changes (the mid bounce),
  `rv24`, tick stratum, `b0_spread` (the CLOB's spread about 110 min before, where present), `rewarded` (13.7's), and
  `ft_both` (CH209's farmer-touch flag, where the sweep is present).
- Target and horizon. `ds = s_{k+1} - s_k` (ticks; SD 2c; floor 1.0c; one-sided < 0 after a break); M1: the share of
  breaks whose spread is back under 2v at k + 1 (a binary form, reported); 6 h secondary. **Primary (the interaction):**
  within market, E[ds | break, rewarded] - E[ds | break, control] < 0 (the band's pull beyond ordinary reversion), with
  the main effect E[ds | break] - E[ds | no break] within the rewarded panel reported.
- Paper rule and economic check. Maker: at a break, post the two-sided minimum inside v at once; the first minute alone in
  the band takes the whole minute's share of the market's daily rate (the quadratic score's denominator is the quoters'
  own scores); the economic check is the configured daily rate of the broken market (from the CLOB feed) times the share
  of the next 120 minutes the census finds the band empty, against 120 minutes of adverse selection at 3.1% an hour x
  2.38c x the minimum size (a development figure: $0.15 on a $19 two-sided minimum, against about 1/12 of a day's rate;
  rates vary by market and the census prints the distribution). Taker: a cost rule (never cross a spread >= 2v in a
  rewarded market; wait one pass), not an edge.
- Population arithmetic. About 9,000-10,700 Gamma-listed non-sports ex-crypto markets a capture (probe), the CLOB's
  non-sports ex-crypto share of 13,661 **unprobed** (planning 8,000-10,000); strict crossings per capture **unprobed**
  (planning 1-3%: 90-300), **1,100-3,600 a day, 23,000-76,000 in 21 days**; `n_eff` 18,000-60,000; non-break rewarded
  units about 2M. Control-panel crossings: the unrewarded panel is larger (about 20,000 non-sports markets a capture), so
  its matched crossings are not the binding count. Events: the rewarded markets' events; the <= 10-member cap declared.
- Permutation and cluster structure. Rule 2's structure: every capture of a rewarded market-day is a unit and the
  crossing is a per-interval label; strata market x UTC day hold 12 units by construction. The crossing's own
  autocorrelation is low by construction (a market cannot cross out again before crossing back): the LT6 V death does
  not apply; the *level* `s_k >= 2v` persists and is a control. Binding scenarios: LT5 5-6 (per-day spread persistence),
  LT6 V's depletion world, a declared **S16: a spread that random-walks with reflection at one tick and no band**
  (ordinary reversion only: the interaction must have size <= 0.058 under it), and a declared **S17: a mid bounce
  (E004's) that re-centres both sides** (the spread's reversion is the bounce; the control panel bounces too). Clusters:
  event; `DE_gate` 31 / 51.
- Planning MDE. Main effect (break against no break, rewarded panel), SD 2c, `n1_eff` 18,000 (low) / 60,000 (high),
  `n2_eff` 2M: `3.47 x 2c x sqrt(1/18,000 + 1/2,000,000) x sqrt(31) x 1.5 x sqrt(1.3)` = **0.50c** (low), 0.27c (high)
  at DE 31; 0.64c / 0.35c at DE 51. **The interaction (primary) is about twice that: 0.99c (low) / 0.55c (high) at DE 31**,
  against the 1.0c floor: borderline at the low end, under at the high end; at a quarter 2.0c / 1.1c. F: the far-future
  crossing (k + 4 -> k + 5) is near-independent (planning `r_w` 0.1): F-MDE 1.49 x the main effect = 0.74c / 0.41c, under
  the 1.0c cap (a verdict condition for the main effect); for the interaction 1.47c / 0.82c: **a verdict condition only at
  the high end**, else a reported label. **Kill line (rule 7):** strict crossings < 100 a capture (about 1,100 a day: the
  count at which the interaction's MDE reaches 1.0c), or the control matcher covering < 70% of breaks.
- Confounders and the control. Ordinary reversion (the control panel and S16); the mid bounce (own 2 h change controlled;
  S17; the control panel); a one-sided widening that is E015's one-sided quote-only move (an anatomy flag as a control;
  the break is defined on the spread, whichever side moved); a programme that ended at the same capture (the CLOB feed's
  listing at k is the panel rule; a departure between k - 1 and k is counted and excluded); the display's omission (CH212:
  `v` is taken from the CLOB feed, which does not blink; Gamma's `rewards_max_spread` is never null and is the sensitivity);
  `in_band`'s LT7 definition (spread <= v) differs from the strict break (spread >= 2v): disclosed; both printed; the
  liquidity gate (|corr(break, log liquidity)| <= 0.5 within and pooled: wide spreads are illiquid markets, so the
  within-market form is the one that can pass; if the pooled form fails, the primary is run within liquidity tier and the
  tiers reported, declared now).
- Most likely boring explanation. Spread reversion after any widening is the same everywhere (one maker steps off, the
  touch refills), so the break's main effect is ordinary reversion (S16) plus the mid bounce (S17) and the interaction
  against the matched unrewarded panel is zero; or the strict crossing is too rare (under 100 a capture) because the
  farmers' bots re-post within the minute and a 2 h capture almost never sees a broken band.
- Cheapest census (counts only; the fresh 10-day seal: sidecar, `reward_params`, captures; no sweep needed for the
  primary). Units of `rewards_max_spread` and its agreement between the two ledgers; the distribution of `s / (2v)` on the
  rewarded panel; strict and LT7-style crossings a capture; the level's persistence (share of broken books still broken at
  k + 1 is a *target* and is not read; the share broken at k - 1 given broken at k - 2 is the state's AR and is read); the
  control matcher's coverage; the liquidity gates; `n_eff`; `m_21`. Kill lines above.
- Challenger feature: **yes.** `bandbreak` (`se-aux-bandbreak-v1`): `bb_s_over_2v`, `bb_break`, `bb_in_band_lt7`,
  `bb_slots_since_break`, `bb_v_clob`, `bb_v_gamma`, `bb_rate_clob` (the daily rate), NaN outside the CLOB-rewarded panel;
  from the sidecar and the last `reward_params` capture before the origin. Read against `se1_lgbm_mm` and `se9_lr_rewards`
  (after 11-18). Embargo: `rewards` (to the later of 11-18 and E022's analysis commit) and a new token `bandbreak` to the
  later of LT9's analysis commit and the lane's date.
- Scores: N 4, EV 4, L 5. Parents: CH45 (band geometry screen), CH71 (the band's edge at 0.90), CH116 (band-stripped
  imbalance), CH183 / LT5 R (the farmer's side; crossing share 0.21 killed it: a boundary of the *price*, not of the
  spread), CH209 (the farmer touch: a control), CH206 (the start: the same "alone in the band" economics at a different
  clock), CH35 and CH86 (vacuums and tick-change vacuums: the same displayed object without the band), E004 (the bounce
  the control panel absorbs), Foucault, Kadan and Kandel 2005 (the cost of immediacy and the refill).

**CH214. The pool splits: paid depth arriving behind an unmoved touch is a new farmer, and a new farmer halves the
incumbent's share of the day's rate. The symmetric in-band depth innovation between the two pre-origin sweeps of a
rewarded book forecasts the spread (competition for the quadratic score pushes both quotes toward the midpoint) and the
incumbent's yield. CH203 reads the asymmetric part of the same innovation as a direction vote; this reads the symmetric
part as the maker's competition clock, on the rewarded panel, with the CLOB's daily rate as the money.**
- Mechanism and why it is non-obvious. Under the venue's formula the pool is split in proportion to each quoter's
  `((v - s) / v)^2 x b`, so an arrival with equal size at the same distance halves the incumbent's share, and the
  incumbent's best response is to move closer to the midpoint (raising `(v - s)` for the same b): competition compresses
  the spread toward one tick. The Telonex case (MAKER_REWARDS section 1 as round 13 quoted it: depth 23x, makers 302 to 639
  after a programme start) is the extreme form; CH206 reads the start; CH201 the yield per posted dollar as a level; CH16
  the reward per unit of adverse selection; CH209 the farmer's touch as a flag. None reads the *arrival* as a within-market
  innovation on every rewarded book every two hours. Round 13 rejected "displayed-liquidity withdrawal as a volatility
  forecast" as textbook; this is the signed opposite (arrival, not withdrawal), its target is the spread and the yield,
  not volatility, and its mechanism is the pool's division, which has no textbook. Who pays: the incumbent farmer who
  does not notice the arrival until the midnight payout; the taker who crosses before the compression. Why the crowd
  misses it: the arrival is visible only in the book's band sums, which the site does not show and the CLOB's rewards
  page does not attribute.
- Data join and decision clock (`A`, L 4). Unit: CLOB-rewarded non-sports ex-crypto eligible market x capture k with the
  last sweeps of passes k - 2 and k - 1 both finished before capture k started (`book0`'s rule applied twice, CH203's
  construction), both two-sided, and **an unmoved touch** (|swmid_{k-1} - swmid_{k-2}| < 0.5c; the band moves with the
  mid, so a moved touch re-bins the sums mechanically) and the same `rewards_max_spread` at both sweeps (from the CLOB
  feed; a band change is CH152's shock and is excluded and counted). State: `D_band` = the sweep's 1c band sums if
  `v <= 1.5c`, else the 5c band sums (a declared proxy: the band is measured from the midpoint, the stored sums from the
  touch; the census prints both and the proxy is fixed before any count); `dD = log(Db_{k-1} + Da_{k-1}) - log(Db_{k-2} +
  Da_{k-2})` (the symmetric innovation); `zdD` standardised within the market's expanding past; secondaries: the per-side
  split (`dDb`, `dDa`: CH203's `dimb` is their difference, disclosed as adjacent), `dlev` (levels arriving), `dgrain`
  (mean size per level: one large arrival is a farmer, many small are retail). Decision time: capture k's `received_utc`
  (the sweeps are about 110 and 230 minutes earlier). Controls: `log D_band_{k-1}` (the level), `s_k`, `b0_spread`,
  `b0_lag_s`, logit mid, |mid - 0.5|, `log1p volume24hr`, the (k - 2, k - 1] `volume_num` change (a fill that ate depth
  is the opposite sign: a conservative confounder), `rv24`, tick stratum, `ft_both`, the CLOB daily rate (`log rate`),
  `rewarded` (13.7's, as a check that the CLOB panel and Gamma's carried listing agree).
- Target and horizon. `ds = s_{k+1} - s_k` (Gamma, ticks; SD 2c in quiet rewarded books, planning 2c; floor 1.0c);
  one-sided: within market, the slope of `ds` on `zdD` < 0 (arrivals compress the spread), the level held fixed. M1: the
  **yield** at the next pass, `y_{k+1} = rate / D_band_{k+1}` (the CLOB rate over the post-origin sweep's band sums, read
  through a sizes-only loader as LT7's lag-slot loader does: the incumbent's share of the pool per dollar posted), slope
  < 0, reported; M2: the engine's flat-class rate (|move| <= DELTA) over the next 6 slots, reported.
- Paper rule and economic check. Maker: hold the quote while `zdD <= 0`; when `zdD` is in its top tercile, either move to
  the touch (the formula's best response) or leave; the economic quantity is the yield's drop in the top tercile against
  the bottom (counts of `rate / D_band` by tercile at k - 1 and k + 1 in the census output, no verdict). Taker: trade
  after arrivals (a cost rule). Gross, no fills modelled (E025 part B owns fills).
- Population arithmetic. 9,000-10,000 CLOB-rewarded non-sports ex-crypto markets a capture x `book0` coverage 0.93 x
  quiet share 0.75 = about **6,300-7,000 a capture, 76,000-84,000 a day, 1.6-1.8M in 21 days**; `n_eff` 1.3-1.4M. Events:
  the rewarded markets' events (politics ladders are rewarded in bulk: the <= 10-member cap matters here more than
  elsewhere; the uncapped arm is reported).
- Permutation and cluster structure. A continuous state on every unit of the rewarded quiet panel: strata market x UTC
  day hold up to 12 units by construction (planning share 0.9 after the quiet and band-unchanged filters). Binding
  scenarios: LT5 7-8 (persistent book states: the level persists, the innovation does not; the AR(0.9) world is run on
  the level and the innovation is derived from it), LT6 V's depletion world, and a declared **S18: farmer bots that
  re-post a constant size every pass** (no innovation: the state's within-market SD is zero and the gate must refuse,
  which the identification gate below enforces). Clusters: event; `DE_gate` 31 / 51.
- Planning MDE. Slope at the tercile gap, SD 2c, `n_eff` 1.3M: `3.47 x 2c / sqrt(1.3M) x sqrt(31) x 1.5 x sqrt(1.5) x
  2.2` = **0.14c** (DE 31), 0.18c (DE 51); at a quarter 0.27c / 0.35c; far under the 1.0c floor. F: the far-future
  innovation (`dD` over sweeps k + 4 -> k + 5, sizes only) has `r_w <= 0` for a mean-reverting level (planning 0): F-MDE
  1.41 x 0.14c = **0.19c / 0.25c: a verdict condition.** **The binding gate is identification, not power (rule 7 and S18):**
  the within-market SD of `dD` must be >= 0.05 (5% of the band's depth) in >= 50% of markets with >= 6 units; if farmers'
  sizes are static the state is empty and the test is dropped at census by that gate. Kill also if quiet rewarded units
  < 3,000 a capture, if the band-changed share > 20%, or if |corr(zdD, log liquidity)| > 0.5.
- Confounders and the control. The level (controlled; VIF(zdD | log D) printed and gated <= 2); a fill (the `volume_num`
  change; opposite sign); a mid move that re-bins the sums (the quiet filter); a band change (excluded); a programme end
  or start inside (k - 2, k] (CH215's object; excluded and counted); CH203's `dimb5` (the asymmetric innovation on the
  same sweeps: **adjacent to LT8**, disclosed; the symmetric and asymmetric parts are orthogonal by construction, and LT9's
  origins either precede LT8's window (fast lane) or follow it (ordered lane); the `quietbook` token is respected: no
  isolating challenger of `pool` is scored before LT8's date); the `b0_gap` diagnostic (not read: no origin mid meets a
  sweep mid here except through `b0_spread`, a control); E022's depth control `bk_depth5c` (a level on movers: a
  different population).
- Most likely boring explanation. Farmers re-post constant sizes every pass (S18), so `dD` is zero within market and the
  identification gate drops the test; or the arrivals that do occur are fills unwinding and refilling (the `volume_num`
  control) rather than new quoters, and the spread does nothing because the touch is already pinned at one tick.
- Cheapest census (counts only; the fresh seal: sweep 1 of each pass, sidecar, `reward_params`). Quiet rewarded share;
  the band proxy's choice counts; the distribution and within-market SD of `dD` (the S18 gate); the band-changed share;
  the VIF and liquidity gates; `r_w` of the lead and lag innovations (sizes only); `n_eff`; `m_21` by event; the yield
  terciles at k - 1 (no target). Kill lines above.
- Challenger feature: **yes.** `pool` (`se-aux-pool-v1`): `pl_dD`, `pl_dDb`, `pl_dDa`, `pl_dlev`, `pl_dgrain`, `pl_yield0`
  (rate over the pre-origin band sums), `pl_quiet`, NaN outside the CLOB-rewarded panel; from `book0`'s sweep, the previous
  pass's last sweep and the last `reward_params` capture before the origin. Read against `se1_lgbm_mm`, `se19_lr_book0`
  (after `book0` lifts) and `se9_lr_rewards` (after 11-18). Embargo: `book0` and `book` to 2027-01-23 (the sweep source),
  `rewards` to 11-18, `quietbook` to the later of 2027-01-23 and LT8's analysis commit (the adjacent LT8 family), and a
  new token `pool` to the later of LT9's analysis commit and the lane's date.
- Scores: N 4, EV 3, L 4. Parents: CH203 / LT8 (the asymmetric innovation on the same sweeps), CH206 (the start), CH201
  (the yield level), CH16 (reward per adverse selection), CH209 (the farmer touch), CH19 (the cliff: the mirror), CH147
  (the breathing book), CH152 (band and rate shocks: excluded here), the Telonex case and the venue's scoring rule as
  MAKER_REWARDS quotes them.

**CH215. The scheduled end (a map first): the CLOB feed serves each programme's `end_date`, so a programme that stops
paying at a stated time is visible days ahead. CH19 reads the cliff after the end; nobody reads the farmers' retreat
before it, which the formula makes rational (the last partial epoch pays pro rata and the incumbents' capital is better
posted elsewhere). The population is unprobed and probably small, because starts roll forward and most programmes may
run to the market's own end; the first count decides whether it is a fourth LT9 test or a column of `rwend`.**
- Why a map first (rule 7). The feed's `start_date` rolls forward (ruling 13.6 item 6); whether `end_date` is a real
  scheduled end distinct from the market's `end_date` is unknown; if ends coincide with market ends the clock is C04's
  time-to-end family (E014, `tte`) and nothing new exists. Planning if it were a test: 10-60 scheduled ends a day on
  markets with > 48 h of life (kill line 30), an event-time before-after per market as CH206's, SD of the daily mean
  spread change 2c, `n_eff` 170-1,000: `3.47 x 2c x sqrt(2 / 170) x sqrt(3) x 1.5 x sqrt(1.3)` = **1.9c** (low) / 0.78c
  (high) against the 1.0c floor: a test only at the high end; F (the fake end on a matched control, `r_w` 0) 2.7c / 1.1c:
  a reported label.
- State (`A`, L 3). `re_h_to_end` (hours to the programme's scheduled end, from the last `reward_params` capture before
  k; NaN without an end within 7 days), `re_distinct` (1 if the programme's end precedes the market's `end_date` by >
  48 h), `re_rate`, `re_sponsored`. Decision time: the feed's receipt. Targets: the spread in ticks and the in-band depth
  (`book0`, sizes only) over the 24 h before the end against the 24-48 h before it; the engine's flat-class rate after
  the end (CH19's cliff, reported).
- Money route. Maker: leave with the pool (post elsewhere for the last epoch); taker: trade before the end (the spread
  widens at the cliff: CH19). Gross.
- Most likely boring explanation. Nearly every programme end coincides with the market's own end (the distinct count
  falls under 30 a day), so the clock is time-to-end (C04 / E014) and the "retreat" is the ordinary pre-resolution
  thinning of every book; the map says so and no test is written.
- Census (counts only; the `reward_params` captures since 10-20, now a dozen a day). Programmes with an `end_date`; ends a
  day; the share distinct from the market's end by > 48 h; the share of ends per UTC day (a venue re-rating is a clock:
  gate <= 30% on one day); control availability. Kill (as a test) if distinct ends < 30 a day; the family is built
  regardless.
- Challenger feature: **yes.** `rwend` (`se-aux-rwend-v1`), the four columns above, NaN without a scheduled end. Embargo:
  `rewards` to 11-18 and a new token `rwend` to the later of LT9's analysis commit and the lane's date.
- Scores: N 3, EV 2, L 3. Parents: CH19 (the cliff: after the end), CH206 (the start), CH152 (rate shocks), CH201 (yield),
  CH98 (redemption-cash days: a different scheduled clock), C04 / E014 (the market's own end).

### B. The universe-wide print stream (parents E007 / C01, CH79, CH132, CH162, CH164, CH170 / E021, CH173, CH193 / LT7, CH154; literature: Easley and O'Hara 1987, Hasbrouck 1991)

**CH216. Large prints without a sample: the live trade monitor has, since 2026-10-12, stored every taker print of at
least $1,000 on every market with its venue time and its receipt, while every flow test in the programme read a rotating
2,000-market sample and died at the strata gate (E021 0.005, J 0.0, K 0.0). The print's venue time against the capture
clock is CH170's "age of the move" with a direct clock on the whole universe; the print's cash against the interval's
`volume_num` change is CH173's concentration on the whole universe; and the once-per-market-day structure makes the
print slot permutable by construction. Engine-first, because the non-sports ex-crypto population is a few hundred prints
a day; an LT9 test if the owner sets sports in, or if the census finds the high end.**
- Why engine-first (rule 6, stated with the arithmetic). CB13 H8 over seven days: non-sports enriched prints crossing a
  touch about 2,360 (politics and geopolitics 2,065, econ and finance 966, other 530, crypto 1,142 by the age buckets),
  unenriched about 2,020, sports about 12,700; H3: 1,400-2,700 markets and 600-1,100 events a day, all categories. The
  non-sports ex-crypto print population is therefore about 530 enriched prints a day plus a share of 290 unenriched a
  day: planning **600-1,000 prints a day in 350-700 markets**. A signed test (buys against sells at print slots on the
  YES-signed next change, SD 4c): `n1_eff = n2_eff` 5,000 (low) / 8,400 (high): `3.47 x 4c x sqrt(2 / 5,000) x sqrt(13) x
  1.5 x sqrt(1.3)` = **1.7c** / 1.3c: three times the 0.5c floor. The magnitude form (all 12 slots of a print market-day as
  units, print slot against the other eleven on `a = |mid_{k+1} - mid_k|`, SD 3c; `n1_eff` 12,600 / 21,000, `n2_eff` 11x):
  **0.60c / 0.46c**: borderline at the high end only. With sports in (about 1,800 crossing prints a day), the magnitude
  form is about 0.3c and the signed form about 1.0c. **Declared now:** CH216 is proposed as an LT9 primary only in its
  magnitude form, only if the owner has set sports in by the pin date or the census projects >= 1,000 non-sports
  ex-crypto prints a day; otherwise it is an engine family and the sports arm is uncounted.
- State (`A`, L 4). Per eligible market x capture k: `pr_n` (prints >= $1k with venue time in (capture k - 1's start,
  capture k's start]), `pr_cash` (their cash), `pr_signed` (buy minus sell cash, signed as YES by `outcome_index`; the
  `side` field is read for this family only, never a wallet field), `pr_age_min` (minutes from the last print's venue
  time to capture k's start: the direct clock), `pr_late_s` (receipt minus venue time: the API's lateness, a venue
  property, reported only), `pr_share` (the prints' cash over the interval's `volume_num` change from the sidecar: the
  lumpiness of the interval's flow, CH173's object on the whole universe; NaN where `volume_num` is unchanged or
  missing), `pr_first_day` (the market's first print ever seen by the monitor: CH154's object). Decision time: capture
  k's `received_utc` (every print read has venue time before the capture's start and receipt before the row's receipt;
  prints received after the row's receipt are the next slot's). The monitor's Gamma context (`ctx_*`, fetched after
  receipt) is never read.
- Money route. Maker: widen for one pass after a large print (the 2.38c adverse selection concentrates after prints:
  CH39's retreat, here with the universe's clock); taker: follow fresh (<= 20 min) large buys in >= $100k markets (2.9c
  round trip; reported; the sports round trip is 5.2c).
- Most likely boring explanation. A large print is just volume, which the sample's flow family (E013 / E014, `flow`)
  and the sidecar's `volume_num` change already carry; its slot has a larger next |move| because the market is active
  that day (the market-day stratum absorbs this, which is why the within-market-day form is the only honest one), and the
  monitor adds a receipt-lagged copy of what the engine already sees.
- Census (counts only; the monitor's day files since 10-12 and the sealed captures). Prints a day by category (the
  parameter), by age bucket at the next capture, by lumpiness; markets and events a day; print market-days with >= 2
  print slots (recurrence); the share of prints whose venue time precedes the capture start (the clock's validity);
  `n_eff` for the magnitude form; `m_21`. Kill (as a test) by the declared rule above.
- Challenger feature: **yes.** `printage` (`se-aux-printage-v1`), the seven columns above, from the monitor's day files
  read before the origin. Read against `se1_lgbm_mm` and `se2_lr_flow` / `se11_lgbm_flow` once `flow` lifts (11-16): the
  question the leaderboard answers is whether the universe's large prints add to the sample's flow. Embargo: `flow` to
  the later of 11-16 and LT2's analysis commit (the same hypothesis class as E013/E014's flow), `movetype` and `absorbed`
  to 12-31 (the `volume_num` change is a volume change: CH193's object), and a new token `printage` to the later of LT9's
  analysis commit and the lane's date.
- Scores: N 3, EV 3 (4 with sports in), L 4. Parents: E007 / C01 (flow continuation on the sample), CH79, CH170 / E021
  (the age of the move; here a direct clock on the universe), CH173 (concentration; here `volume_num`-denominated), CH132
  (wake-up prints), CH162 (trains), CH164 (class-conditioned longshot prints), CH154 (first-day prints), CH193 / LT7
  (absorbed flow: `pr_cash` against no move is its object; disclosed), CH39 (post-print retreat).

### C. Serving-path and display clocks on the captures (parents CH37, CH176, CH194 (withdrawn), CH202, the `regime` family (dropped); DESIGN_V1 sections 21-22)

**CH217. Row quality: the sparse row. Gamma serves `volume24hr` on 22% of rows, `last_trade_price` on 44%, `clob_rewards`
on 38%; the per-row count of optional fields present, its within-market-day innovation and the row's `page_index` and
receipt offset are a serving-path label for every row the engine scores. Not a signal: a weight. The North Star's object
is forecast quality, and a champion that learns on rows the venue served from a stale path learns noise.**
- Why engine-first. The family's value is as a per-row data-quality covariate and a label-quality weight (a 2 h "move"
  measured from a stale row is not a move), which the engine reads directly and no test needs; CH212's census is the
  place where its content is first counted (the co-omission odds ratio), and CH212's route A is the one test of it.
- State (`A`, L 5). `rq_fields` (count of the sidecar's and row's optional fields present at k, out of a declared list of
  eight), `rq_dfields` (the change from k - 1), `rq_page`, `rq_recv_offset_s` (the row's receipt minus the capture's start),
  `rq_sparse` (1 if `rq_fields` is below the market's own median over [k - 11, k - 1]). Decision time: the row's receipt.
- Money route. None directly; the engine's and the maker's data hygiene (a displayed move after a sparse row is suspect:
  CH212's maker rule).
- Most likely boring explanation. Sparsity is a per-market trait (a market with no trades has no `last_trade_price`, no
  `volume24hr` and no programme), constant within market-day; the weight then re-weights markets, not rows, and the
  family is a liquidity proxy the champion already holds.
- Census (counts only; LT7's sealed sidecars and rows). The distribution of `rq_fields`; its within-market-day variance;
  the share of rows sparse; co-omission structure; `page_index` against sparsity. Kill (as a family) if `rq_fields` is
  constant within market-day for > 95% of market-days (then the omissions are per market, not per row, and the family is
  a trait).
- Challenger feature: **yes.** `rowq` (`se-aux-rowq-v1`), the five columns above; also proposed as an optional
  **label-quality weight** (a declared, hashed rule: rows with `rq_sparse = 1` at origin or target get weight 0.5 in a
  challenger's loss; the champion is unchanged; disclosed as a learner change under DESIGN_V1 section 19). Embargo: none
  (no live test reads row sparsity); CH212's `rwblink` token covers the `clob_rewards` component.
- Scores: N 3, EV 2 (as a signal) / 4 (as data quality), L 5. Parents: CH37 (the artefact), CH202 (the stale displayed mid
  as the "early part" reading), the `regime` family (receipt order as a proxy, dropped: this is per row, not venue-wide),
  LT8 census-code fix 7 (the null taxonomy).

**CH218. The display's disagreement: Gamma's `oneDayPriceChange` and `oneWeekPriceChange` are what the site's mover
lists rank on; the host's own 24 h and 7 d changes are what happened at the capture clock. Where they disagree by more
than two ticks, one of the two is stale, and the site is ranking a move that the book has already unmade (or the
reverse). The disagreement is a per-market per-capture number on the whole panel; its sign says whether the display is
ahead of the book or behind it; the engine can read it and a maker can fade the chasing.**
- Why engine-first. Half of CH194 died on `chg_1h`'s untestable semantics (a venue-computed field), and LT7's embargo
  asks for no attribution on `chg_1h` x own 2 h interactions to 12-31; the 1 d and 1 w fields are the same kind of
  object at horizons no registered test reads, but the honest statement is that no gate can test the venue's clock
  either; as an engine column the disagreement is scored on forecast quality alone. CH176 reads the front page as a
  clock (a rank); CH37 the 1 h artefact; this reads the two longer display fields against the host's own path.
- State (`A`, L 5). `dg_1d = chg_1d - own_24h`, `dg_1w = chg_1w - own_7d` (own changes from the engine's `quotes/`; NaN
  where the own look-back is incomplete), `dg_1d_abs_ge2t` (a flag at two ticks), `dg_sign` (display ahead or behind).
  Decision time: the row's receipt.
- Money route. Maker: when the display shows a 1 d move the book has unmade (`dg_1d` large and opposite in sign to the
  own 2 h change), expect display-driven flow in the displayed direction and fade it after the next capture (gross; no
  fills). Taker: none.
- Most likely boring explanation. `oneDayPriceChange` is computed by the venue from a different reference (the last
  trade rather than the mid, or a different clock), so the disagreement is a persistent per-market trait rather than a
  clock, and whatever it carries the champion already holds through `chg_1d` and the own 24 h change as separate inputs.
- Census (counts only). Presence of `chg_1d` / `chg_1w` on eligible rows; the distribution of `dg_1d` in ticks; its
  within-market persistence (if it persists for days it is a trait of the venue's computation, not a clock); the share
  of eligible rows with |dg_1d| >= 2 ticks. Kill (as a family) if that share is < 2%.
- Challenger feature: **yes.** `dispgap` (`se-aux-dispgap-v1`), the four columns above. Read against `se1_lgbm_mm` (which
  already holds `chg_1d` and the own 24 h change separately: the family's question is whether their *difference* carries
  what the two levels do not). Embargo: a new token `dispgap` to the later of 2026-12-31T00:00Z and LT7's analysis commit
  (LT7's `capath` family reads capture-clock step paths and its R1 asked for no lagged-step attribution; the 1 d
  disagreement is adjacent), and no other token.
- Scores: N 3, EV 2, L 5. Parents: CH37 (the 1 h artefact), CH194 (withdrawn: the venue's 1 h clock), CH176 (the front
  page), CH191 / LT7 (capture-clock paths; the `capath` token respected), CH202 (the stale-display reading).

### D. Book and dormancy clocks on the sweeps and captures (parents CH146, CH147, CH149, CH132, CH210, CH203; `bk_age_s` (rejected in round 13))

**CH219. The touched book: the CLOB stamps every book with its own `book_timestamp`. Between the two pre-origin sweeps
(about 230 and 110 minutes before the origin) a book was either updated by someone (the timestamp advanced) or by
nobody. Round 13 rejected `bk_age_s` because it was read from sweep 1 of pass k, inside the label; read from the
previous passes it is a direct clock on who is watching this market, independent of whether the touch or the sizes
changed. A book nobody touched in two hours is nobody's quote: its next move is a jump, its spread a fiction, and a
maker who posts against it is posting against a ghost.**
- Why engine-first. The sign of the next |move| is ambiguous (untouched books are illiquid and rarely move, but when
  they move they jump), so a magnitude primary cannot be declared; the clock's value is as a moderator of every book
  family (`book0`, `quietbook`, `pool`: an innovation of a touched book means something; of an untouched one nothing)
  and as maker protection. CH147 infers touching from size changes within a pass; CH210 reads the two sweeps of pass
  k - 1; this reads the CLOB's own timestamp across passes.
- State (`A`, L 4). `bc_touched` (1 if `book_timestamp_{k-1} > book_timestamp_{k-2}`), `bc_age_s` (sweep k - 1's receipt
  minus its `book_timestamp`), `bc_age_slots` (passes since the timestamp last advanced, capped at 12), `bc_hash_changed`
  (`book_hash` differs between the two sweeps: a second, content-based clock). Decision time: capture k's receipt (both
  sweeps earlier).
- Money route. Maker protection: treat an untouched book's imbalance and depth as no information; do not post inside an
  untouched touch (the first touch will be a re-quote, not a fill). Taker: expect a walk when crossing an untouched touch.
- Most likely boring explanation. An untouched book is an illiquid one: the clock is a liquidity tier the champion
  already has, and the moderation it offers is the same as conditioning on depth.
- Census (counts only; LT7's sealed sweeps, 22 consecutive pass pairs). Touched share between passes; the distribution
  of `bc_age_slots`; agreement of the timestamp and hash clocks; the touched share by liquidity tier. Kill (as a family)
  if the timestamp advances on > 95% or < 5% of books between passes.
- Challenger feature: **yes.** `bookclock` (`se-aux-bookclock-v1`), the four columns above, from `book0`'s sweep and the
  previous pass's last sweep; read as a moderator inside `se19_lr_book0` once `book0` lifts, and against `se1_lgbm_mm`.
  Embargo: `book0` and `book` to 2027-01-23, `quietbook` to the later of 2027-01-23 and LT8's analysis commit, and a new
  token `bookclock` to the later of LT9's analysis commit and the lane's date.
- Scores: N 3, EV 2, L 4. Parents: CH146 (book age at the fill), CH147 (the breathing book), CH210 (two minutes before
  the origin), CH203 / LT8 (the innovation this moderates), `bk_age_s` (rejected inside the label; here pre-origin).

**CH220. Dormancy: slots since the mid last moved, on every market at every capture, from the engine's own `quotes/`
with a 12-slot cap. A market dormant for a day is not a market; its first move is a re-quote with no counterparty, and
the engine's direction classes should expect flat from it. Engine-first: a wake-up's continuation has an ambiguous sign
(an abandoned book re-centred by a bot, or news in a market nobody watched), and the pre-wake-up slots have zero |move|
by construction, so no within-market-day contrast is honest.**
- Why engine-first. Round 13 listed "wake-up prints" and "dormant deep ladders" as not re-proposed; this is their
  per-interval capture-clock form as a feature, not a test, because every contrast it allows is mechanical (stated
  above).
- State (`A`, L 5). `dm_slots` (slots since |mid change| >= 1 tick, capped at 12; NaN with an incomplete look-back),
  `dm_dormant24` (`dm_slots == 12`), `dm_woke` (1 at the first slot after a dormant stretch of >= 6). Decision time: the
  row's receipt.
- Money route. Maker: quote a dormant market at the band edge only (a reward-only posture; no information to lose to);
  taker: none.
- Most likely boring explanation. Dormancy is illiquidity plus a wide tick: the flat class it predicts is already the
  champion's for any market with no 24 h change (an input), so the family adds a cap on a quantity the champion sees.
- Census (counts only; LT5's sealed captures). The dormant share by category and liquidity tier; wake-ups a day. Kill (as
  a family) if the dormant share is < 3% or > 60% of eligible non-sports.
- Challenger feature: **yes.** `dormant` (`se-aux-dormant-v1`), the three columns above. Read against `se1_lgbm_mm` and
  `se15_lgbm_surprise` (after 11-19: the volatility ratios live there). Embargo: `surprise` to 11-19 and no new token.
- Scores: N 2, EV 2, L 5. Parents: CH149 (dormant ladders map), CH132 (wake-up prints), CH204 / LT8 (the own clock; a
  different object: concentration, not silence), C06 / `surprise`.

### E. The proposal clock on the sidecar (parents CH01, CH02, CH03, CH47, CH65, CH67, CH72, CH85, CH104, CH134; the fee valley)

**CH221. The siblings' proposal window: the sidecar stores `uma_resolution_statuses` for every market at every
capture, so the first capture at which a member of a mutually exclusive event shows a proposal is a two-hourly clock on
the whole panel. From that capture every sibling is, in fact, NO; their NO asks below 0.99 are a hold-to-resolution carry
in the fee valley (the taker fee is `rate x p x (1 - p)`, near zero at 0.98), with the dispute rate as the risk. CH02
reads the proposed member's own carry; CH67 the siblings after `closed`; nobody reads the siblings at the proposal. The
field is on CB16's forbidden-parse list as an outcome field, so the challenger must rule whether an origin-side,
receipt-timed read of it is admissible as a clock; until then this is an engine-first map on `res_7d`.**
- Why engine-first pending a ruling. The programme's hygiene bars Gamma outcome fields; a proposal status is public
  information at its time (an on-chain UMA event), but the programme has only ever treated the field as an outcome
  (cb16_common's `FORBIDDEN_PARSE_FIELDS`), so a design that reads it as a state needs an explicit admissibility ruling
  with the field's structure counted first (whether "proposed" is distinguishable from "resolved"; whether the status is
  stamped). Its natural test is also not a within-unit contrast: every sibling moves the same way, and the slope of the
  drop on the pre-proposal price is arithmetic; the money question is a calibration (does the carry's gap exceed the
  overturn rate), which is a `res_7d` object. The engine reads it without a test; a map counts the gap.
- State (`A`, L 3). `sp_proposal_k` (1 at the first capture whose sidecar shows a proposal on any member of the event,
  read at k only, never a later status), `sp_is_proposed` (this market is the proposed member, by the status on its own
  row; the proposed *side* is never read from the field: it is inferred from the member's own mid >= 0.97 or <= 0.03 and
  counted `side_unreadable` otherwise), `sp_sibling_no_ask` (the sibling's displayed NO ask at k), `sp_gap` (0.99 minus
  that ask, the gross carry), `sp_h_since` (hours since the proposal capture, capped at 48).
- Money route. Hold-to-resolution: buy NO on siblings at asks <= 0.97 at the proposal capture (fee near zero in the
  valley; no exit leg); the risk is the dispute and overturn rate (CH47, CH65), which `res_7d` measures by class; the
  gross is `sp_gap`. Maker: none (the siblings' books are abandoned).
- Most likely boring explanation. The siblings' NO asks are already at 0.99 by the proposal capture (makers read the
  on-chain proposal within minutes), so `sp_gap` is zero where it is readable and large only where the book is abandoned
  and no fill is possible; what remains is the dispute lottery (CH47), priced about right.
- Census (counts only; LT7's sealed sidecars). The field's value set and structure; proposals a day by category
  (ex-crypto ex-sports is the question: crypto and sports resolve by the thousands); siblings per proposal; the share of
  siblings with a NO ask <= 0.97 at the proposal capture (a state, read at k); the share of proposals whose side is
  readable from the mid. Kill (as a map) if ex-crypto ex-sports proposals < 20 a day or the field is unstructured.
- Challenger feature: **yes, after the ruling.** `sibprop` (`se-aux-sibprop-v1`), the five columns above, as `res_7d`
  features only. Embargo: a new token `sibprop` to the later of LT9's analysis commit and the lane's date; and `deadline`
  (withdrawn) is not revived.
- Scores: N 3, EV 3, L 3. Parents: CH01 and CH02 (decided and proposal-window carries on the member), CH67 (siblings after
  `closed`), CH47 (the dispute lottery), CH65 (ex-ante dispute), CH85 (whitelisted proposers' clocks), CH104 (the DVM
  reveal lead), CH134 (settlement-labelled carry), CH72 (the fee valley).

---

## 3. Ranked shortlist for LT9, then the rest

Rank = census survival (a complete panel, a dense state, an innovation or crossing, a declared DE, the MDE at the *low*
planning count under the floor, the F-MDE under its cap) x originality x plausibility x money route, with the rules of
0.2 as hard constraints. Every LT9 candidate has a state defined on the rewarded or whole capture panel, read strictly
before the origin, a within-market contrast or slope with the Freedman-Lane gate in strata that hold 12 units by
construction, a falsification arm whose twin is independent by construction, a counts-only census on LT7's seal or on
a fresh 10-day seal of the four 2 h streams, a planning MDE under the floor at the planning count, and a reader that
extends an existing LT reader (E015's for sidecar states, V's / CH203's for sweep states) by a few columns, plus one new
light reader on `reward_params/` (< 50 MB). The last column is my prior probability that the idea passes its own census
as written, before any count; it is a judgement, not a measurement.

| Rank | ID | One line | L | Population arithmetic (source) | Permutation structure | Primary | Planning MDE (quarter); F | Prior odds of surviving census |
|---|---|---|---|---|---|---|---|---|
| 1 | CH213 | The band break: the displayed spread crossing out of the reward band, against the same crossing where no band exists | 5 | 9,000-10,700 listed markets a capture (probe); strict crossings 90-300 a capture (1-3%, unprobed); 23,000-76,000 in 21 days | per-interval crossing on every rewarded market-day; 12 units by construction; FL with S16 (reflection, no band) and S17 (the bounce) | within market, E[ds \| break, rewarded] - E[ds \| break, control] < 0 | main 0.50c / 0.27c; **interaction 0.99c / 0.55c** against 1.0c (quarter 2.0c / 1.1c); F verdict for the main effect (0.74c / 0.41c), for the interaction at the high end | 0.40 (the crossing count and the control matcher are the risks; no persistence gate can kill it) |
| 2 | CH214 | The pool splits: paid depth arriving behind an unmoved touch on the rewarded panel, two pre-origin sweeps | 4 | 6,300-7,000 quiet rewarded books a capture (9,000-10,000 x 0.93 x 0.75); 1.6-1.8M in 21 days | continuous innovation on every unit; 12 units by construction; FL on the level with S18 (static farmer sizes) | within market, slope of `ds` on `zdD` < 0, the level fixed | 0.14c / 0.18c (quarter 0.27c / 0.35c); **F verdict** 0.19c / 0.25c | 0.35 (power is not the question; the S18 identification gate is: farmer sizes may be static) |
| 3 | CH212 | The display's omission and the two ledgers: the per-interval omission of `clob_rewards` on 3,000 markets a day, adjudicated by the CLOB feed | 5 | **2,112-3,995 switching markets a day (counted)**; 690,000 units in 21 days; omitted slots 126,000 (planning) | all slots of a switching market-day; 11 units by construction; FL with S15 (row-independent omission); venue-clock gate | route A: E[a \| om] - E[a \| not] > 0; route B: the spread after a listed -> null switch the CLOB also dropped | A 0.35c / 0.44c (quarter 0.69c); F 0.52c at the cap; B 0.23c / 0.30c, F verdict | 0.30 (the challenger already reads the omission as field-level flakiness; the route rule can kill it from counts, which is the design) |
| 4 | CH215 | The scheduled end: the farmers' retreat before a programme's stated end (map first) | 3 | 10-60 distinct ends a day (unprobed; starts roll forward) | event-time before-after per market; sign-flip FL within market; fake ends on controls | within market, the 24 h mean spread before the end against 24-48 h before, net of controls | 1.9c / 0.78c against 1.0c (quarter 3.8c); F reported | 0.10 (a count decides; most ends may be market ends) |
| 5 | CH216 | Large prints without a sample: the monitor's universe-wide print slots (magnitude form; sports parameter) | 4 | 600-1,000 non-sports ex-crypto prints a day in 350-700 markets (CB13 H3/H8); 12,600-21,000 print slots in 21 days | all 12 slots of a print market-day; FL with LT5 1-2 and L10 | print slot against the other eleven on `a` (magnitude) | 0.60c / 0.46c at DE 13 (quarter 1.2c); F reported | 0.15 ex-sports (0.45 with sports in) |
| 6 | CH217 | Row quality (engine data-quality family; CH212's census counts it) | 5 | every row; sparsity structure unprobed | n/a | `dir_2h` weight and covariate | engine window | n/a (kill if constant within market-day) |
| 7 | CH219 | The touched book (engine-first; a moderator of every book family) | 4 | about 28,000 books with two pre-origin sweeps a capture; touched share unprobed | n/a | moderator inside `se19` | engine window | n/a |
| 8 | CH218 | The display's disagreement (engine-first) | 5 | every row with `chg_1d` and an own 24 h change | n/a | `dir_2h` against se1 | engine window | n/a |
| 9 | CH221 | The siblings' proposal window (engine-first on `res_7d`; admissibility ruling needed; HTR map) | 3 | proposals a day ex-crypto ex-sports unprobed | n/a | `res_7d` calibration; the gap map | engine window | 0.05 as any test |
| 10 | CH220 | Dormancy (engine-first) | 5 | every row with 12 own slots | n/a | `dir_2h` flat class | engine window | n/a |

CH213 is first because it is the one state in this round whose every census gate is met by construction except the
count of crossings, whose falsification twin is independent by the nature of a crossing, whose control (the same
crossing on an unrewarded market) separates it from every textbook reversion, and whose money is the venue's own
formula. CH214 is second because its power is not in question and its risk is a single, honest identification gate
(farmer sizes may not move), with the strongest maker route in the round (the pool's division). CH212 is third because
its population is the only one in the programme counted by a probe before the idea was written, its reader is the
cheapest, and its census *routes* rather than merely gates; it ranks below the two because the challenger has already
read the omission as field-level flakiness, which the route rule may confirm. CH215 is a map whose count decides. CH216
is the strongest census profile the monitor can offer and is a scope call. The engine-first five follow. **If the LT9
designer wants k = 3 with the strongest money routes, CH213, CH214 and CH212 are the three (two spread primaries and a
routed primary; the dependence between CH213 and CH214 on the rewarded panel is disclosed and Holm handles it); CH215
is added only on its count; CH216 only with sports in.**

**Pre-registration sketches for the top 4 (LT9 candidates; each a separate primary in one Holm family; written in
LT8's shape so the designer can lift them).**

- **CH213 (the band break).** Unit: non-sports ex-crypto eligible market x capture on the CLOB-rewarded panel (plus the
  matched unrewarded control panel). State: `break = 1[s_{k-1} < 2v and s_k >= 2v]` on Gamma's displayed spread with `v`
  from the CLOB feed. Decision time: capture k's receipt. Primary: expanding-past market-demeaned OLS of `ds = s_{k+1} -
  s_k` on `break x rewarded` with `break`, `s_{k-1}`, `s_k`, logit mid, |mid - 0.5|, `log1p liquidity`, own 2 h and 24 h
  changes, `rv24`, tick stratum, `b0_spread`, `ft_both`, an E015-style one-sided flag as controls; one-sided < 0. Targets:
  `ds`; M1 the back-under-2v share; 6 h. Clustering: LT4 L10 with the <= 10-member cap (larger ladders reported).
  Planning MDE 0.99c (low) / 0.55c (high) at DE 31. Census (fresh seal: sidecar, `reward_params`, captures): strict
  crossings >= 100 a capture; the two ledgers' `v` agreement printed; the state's AR; matcher coverage >= 70%; liquidity
  gates (within; pooled with the tier fallback declared); permutable share >= 50% (by construction); pessimistic MDE of
  the interaction <= 1.0c; F-MDE printed. Verdict condition: F (the far-future crossing) for the main effect; for the
  interaction if its census F-MDE <= 1.0c. Cost hurdle: the maker's first-minute share against 120 minutes of adverse
  selection (counts only; no verdict). Extends: E015's reader (sidecar and spread columns) plus a new `reward_params`
  reader. Embargo: `rewards` to the later of 11-18 and E022's analysis commit; `bandbreak` to the later of LT9's analysis
  commit and the lane's date.
- **CH214 (the pool splits).** Unit: CLOB-rewarded non-sports ex-crypto market x capture with sweeps of passes k - 2 and
  k - 1 before the origin, two-sided, an unmoved touch and an unchanged band. State: `zdD`. Decision time: capture k's
  receipt. Primary: expanding-past market-demeaned OLS of `ds` on `zdD` with `log D_band_{k-1}`, `s_k`, `b0_spread`,
  `b0_lag_s`, logit mid, |mid - 0.5|, `log1p volume24hr`, the (k - 2, k - 1] `volume_num` change, `rv24`, tick stratum,
  `ft_both`, `log rate` as controls; one-sided < 0; material reading top-against-bottom tercile. Targets: `ds`; M1 the
  yield at k + 1 (sizes only, lag-slot loader); M2 the flat class over 6 slots. Clustering: LT4 L10 with the member cap.
  Planning MDE 0.14c (DE 31), F-MDE 0.19c. Census (fresh seal: sweep 1 of each pass, sidecar, `reward_params`): quiet
  rewarded units >= 3,000 a capture; the within-market SD of `dD` >= 0.05 in >= 50% of markets with >= 6 units (S18);
  band-changed share <= 20%; VIF(zdD | log D) <= 2; liquidity gates; `r_w` (lead, lag; sizes only) <= 0.3; pessimistic MDE
  <= 1.0c; F-MDE <= 1.0c. Verdict condition: F (the far-future innovation); the asymmetric part (`dimb5`) is CH203's and is
  never a column here (a reported orthogonality check only). Extends: V's / CH203's reader (band sums instead of the
  imbalance) plus the `reward_params` reader. Embargo: `book0`, `book`, `quietbook` as applied; `rewards`; `pool` new.
- **CH212 (the omission and the two ledgers).** Unit: non-sports ex-crypto market x capture on a switching market-day.
  State: `om_k`. Decision time: capture k's receipt. Primary (route A): expanding-past market-demeaned OLS of `a =
  |mid_{k+1} - mid_k|` on `om` with 11 slot dummies, logit mid, |mid - 0.5|, spread, `log1p liquidity`, own 24 h change,
  `rv24`, tick stratum, `rewarded` (13.7's) as controls; one-sided > 0. Primary (route B): the same form on `ds` with
  `om x clob_dropped`. The route is fixed by the census's declared rule (co-omission odds ratio >= 1.5 or `page_index`
  share difference >= 10 pp for A; CLOB departures matching >= 30% of Gamma's switches for B; both; neither = dropped).
  Clustering: LT4 L10 with the member cap. Planning MDE 0.35c (A) / 0.23c (B) at DE 31; F 0.52c (A, at the cap) / 0.34c
  (B). Census (LT7's sealed sidecars, or the fresh seal for the CLOB churn): switching markets >= 1,500 a day; the
  venue-clock gate (<= 50% of omissions in one slot); the route counts; the band parameters at omitted slots; `n_eff`.
  Verdict condition: F if the census F-MDE <= the route's floor, else a reported label. Extends: E015's reader (sidecar
  columns only). Embargo: `rewards`; `rwblink` new. Disclosure at the pin: q0601b, q0601c and the 13.6 / 13.7 rulings
  (counts only) were seen; E022's S2 adjacency.
- **CH215 (the scheduled end; map first).** Unit: a CLOB programme end distinct from the market's end by > 48 h x the 24
  captures before it, with a matched control. State: event time. Decision time: the feed's receipt. Primary: the
  within-market 24 h mean spread before the end minus the 24-48 h mean, net of the control's, one-sided > 0 (the
  retreat widens the spread before the cliff). Clustering: event; `DE_gate` 3.0. Planning MDE 1.9c / 0.78c against 1.0c.
  Census (the `reward_params` captures): distinct ends >= 30 a day; controls for >= 70%; the one-day share <= 30%. Verdict
  condition: none beyond Holm (F reported). Extends: a light reader on `reward_params/` and the sidecar (< 50 MB).
  Embargo: `rewards`; `rwend` new.

**How the families would be registered.**
- **A. The rewarded panel (CH212, CH213, CH214, CH215).** CH213 and CH214 counted if their censuses pass; CH212 counted on
  the route its census fixes; CH215 a map whose count decides. One new light reader (`reward_params/`) shared by all four;
  the families `bandbreak`, `pool`, `rwblink`, `rwend` go to the engine under their tokens at once (no isolating challenger
  of `pool` before LT8's date, because of `quietbook`'s adjacency).
- **B. The monitor (CH216).** Counted only with sports in scope or the high-end count, in the magnitude form; the
  `printage` family is built regardless under `flow` / `movetype`.
- **C-E. Engine-first (CH217-CH221).** Challenger families with the tokens named; CH217's weight rule is a learner change
  under DESIGN_V1 section 19; CH221 waits for the admissibility ruling and its structure count.

**What is honest to say about all of them.** The programme has now watched fourteen tests die at census in two days and
one survive, and the survivor's properties are not mysterious: a complete panel, a dense continuous state, an innovation,
small clusters. This round took those properties as the brief and found the one panel that has all four and a published
mechanism on top: the rewarded markets, captured by two feeds, whose makers are paid by a formula that dates their
behaviour. The band break, the pool's division and the display's omission are each an event the host already stamps on
thousands of markets a day, each has a falsification twin that is independent because events do not persist, each is
read from the sidecar and the `reward_params` feed with at most one pre-origin sweep, and each states the single count
that kills it. The rest of the round is honest about not reaching a test: the monitor's non-sports population is a few
hundred prints a day; the proposal clock needs a ruling; the serving-path, display and book clocks are weights and
moderators. Nothing here is edge until it has gone through census, frozen rules, prospective registration and an economic
check at recorded prices; the engine's leaderboard, not this file, is where any of it would first show.

---

## 4. Ideas considered and rejected, and why

### 4.0 Dropped as duplicates or closed (this round's own candidates, each with the record that closes it)

Every idea below was drafted or seriously considered for this round and dropped before writing because an earlier CH, a
closed test, a null or an engine family already owns it. A closed idea is re-proposed only with a genuinely new
mechanism, clock, population or join, and none of these had one.

| Candidate this round | Why dropped | The record |
|---|---|---|
| The exhaustive event's overround innovation (the sum of YES mids or asks across a neg-risk event minus 1; the stale member as the one that did not move while the sum did; a dutch-book paper route) | duplicate and closed | CH09 (CB1-D: "did not advance", under-priced sets +0.78 pp, p 0.016, no advance), CH10, CH11, CH52, CH66, CH81; HB1 null and E005 not supported (`CANDIDATES.md` "Not candidates"); `ev_sum_mid_m1` and `ev_norm_gap` are already engine inputs (`event` family, se8 / se10, visible from 10-22T12:00Z) |
| The series term structure (P(by November) > P(by December) inside one `series_slugs` family) and ladder-against-bucket cross-listings | duplicate; a text parse | round 2's ladder-versus-bucket idea (`sum ask(buckets <= D)`), "series rolls and base rates" (not re-proposed); reading thresholds from titles is a text frame (0.2 rule 6) |
| PredictIt as a bias-corrected twin (the $850 cap and the fee on profits bend its prices toward 0.5) | closed frame | CB15-P closed (37 pairs in 12 events against >= 60 in 30); `xvenue2` under `xvenue` to 11-04; CH208 engine-first |
| Smarkets' lay-side depth or its own overround as a moderator for the matched Polymarket market | closed frame | CB15-P's count; builder row 4 (`xvenue2`: "coverage likely tiny"); round 13 rule 7 |
| ESPN line steam in any form (pre-game, in-play, closing line as a calibration object) | held | CH205 (sports scope, the owner's call); sports a parameter everywhere here |
| A page-boundary crossing in Gamma's ordering as a salience clock | duplicate / dropped | CH176 (the front page); the `regime` family dropped (worse than se1); if the ordering is by volume it is CH193's `volume_num` object |
| `open_interest` innovations (mint share; the quiet exit by merge) | not re-proposed | CH150; the sign is ambiguous; `participation` excludes event OI |
| `event_comment_count` innovations as attention | excluded | the builder excluded it from `participation`; "attention surges" not re-proposed |
| Fee flips (`fees_enabled`, a `fee_schedule` edit) and tick-regime switches as events | rare events | 0.1 pattern 1; CB18-S's fate for edits; "tick-regime discounts" not re-proposed |
| The sponsor's side (sponsored against native programmes) as a signal | a slow trait | columns of `rwend` / `rwblink` only (section 4.1) |
| A print that consumed the displayed touch (print size >= `bid_size_1` at the prior sweep) | duplicate | CH193 absorbed flow (LT7; `absorbed` to 12-31); C09 walked flow |
| The print before or after the pre-origin sweep (CH202's held-versus-fresh clock on prints) | a column, not a test | `printage`'s `pr_age_min`; CH202 is LT8's (`swclock`) |
| A category-level news clock from PredictIt's minute prints or the monitor (breadth of movers) | not re-proposed | "breadth" (rounds 8-9); CH208; the `regime` family dropped |
| The crypto Up / Down window's gap to the Binance-implied probability | built already | `crypto` family se20 (`cr_ud_gap`, `cr_ud_z`); crypto is excluded from every primary (LT7 rule 7) |
| Any sweep-2-minus-sweep-1 state against an origin-k target | declined | CH200 `sweep2` declined 10-22; DESIGN_V1 section 21 |
| The resolution-source host class from `gamma_rules` | killed at census | CH199 `rulesrc`, 19.9% < 30% |
| Silent rule edits; program-against-human fades | closed | CB18-S (CH177), CB18-P (CH172) dropped uncounted |
| A worn-pool replay of maker fills | not testable (source) | CB8-W1, 5 of 192 eligible |
| Wikipedia-frame and barrier-confusion ideas | closed | CB14-W; CB13-R (CH118) |
| The LT4 / LT5 / LT6 drops under any new name (arrivals and cancellations, the age of the move on the sample, jump or grind, overhang, the high-water mark, the farmer's choice, alone or with the crowd, the makers' vote, clips, deadline moves, sibling birth) | closed at census | 0.1's table; a re-proposal needs a new panel, not a new name. CH216 (universe-wide prints, not the sample) and CH213 (the spread's band crossing, not the price's) are the two entries that state a genuinely different population or object, and each says so |
| The hour-held move (`chg_1h` against the own change) | withdrawn | CH194 (an untestable venue clock); CH218 is engine-first for the same reason |
| Anything wallet-level (copying, concentration, footprints by size identity) | sealed / frozen / dropped | E026 registered, its modules frozen to 12-07; CH185 clips dropped at LT6's census |

### 4.1 Ideas rejected on the design rules of 0.2, and why

- **Any trade-sample unit as an LT9 primary** (jump or grind, overhang, clips, walked flow, the age of the move on the
  sample). E021 0.005, J 0.0, O 372 a pass, K 13 units: the measured fate of the rotating sample (0.1 pattern 2). CH216
  reads the universe-wide monitor instead and still does not reach a non-sports test.
- **Any rare-event state** (`end_date` edits, births, rule edits, band or rate re-ratings, tick-regime crossings, the
  spread's first widening after a lock, `accepting_orders` flips, the reward start as a test). D 3 units, B 0, CB18-S,
  CH152's "tens a day": pattern 1. CH215 (the scheduled end) is the one rare-event idea kept, as a map.
- **Level states** (farmer-touch share, yield per posted dollar, in-band depth, the band's slack (CH45), dormancy as a
  level, book age as a level, the hidden-programme class as a test). V's death and LT7's F-MDE: pattern 3. Levels enter
  here as controls and as the two-ledger *map*.
- **Look-backs beyond 12 slots** (high-water marks, 84-slot schedules, 7 d own changes as states). H's `hwm_incomplete`
  0.55: rule 4. CH218 uses the own 7 d change as a comparison column, NaN where incomplete, engine-first.
- **External, text and cross-venue frames as primaries** (PredictIt, Smarkets, Kalshi joins; ESPN beyond CH205; Wikipedia;
  EDGAR; dockets; option chains; `gamma_rules` text traits; the resolution-source class). CB13-R 58 events, CB14-W 46,
  CB15-P 12, CH199 44.7%: pattern 4; round 13's rules 5-7 unchanged.
- **The reward start (CH206) and the hidden-programme yield as tests.** Starts roll forward (13.6 item 6), so the start
  count is a map (LT8's 5.2); the hidden-programme yield is a level (above). Both are columns of CH212's map and `rwend`.
- **The wake-up move as a test.** The pre-wake-up slots have zero |move| by construction, so every within-market-day
  contrast is mechanical; engine-first (CH220).
- **The signed large-print continuation on the universe (CH216's signed form).** 1.3-1.7c at the planning count ex-sports;
  about 1.0c with sports in: never under the floor. The magnitude form is the only census-survivable form and is a scope
  call.
- **Any sweep-1-of-pass-k state against an origin-k target** (`bk_age_s`, CH200, the touch at k). DESIGN_V1 section 21;
  every sweep state here is `book0`'s construction or earlier.
- **The `b0_gap` reversal, the display mid against the CLOB mid at the same pass.** Seen in DESIGN_V1 section 22's
  diagnostic (10-22); informed by construction; not proposed (CH202 discloses it as M2 in LT8).
- **`volume_num`-based "traded this interval" as a test** (E015's anatomy on the whole panel with better coverage). E015
  is registered (analysis 11-15) and CH193 is LT7's (`movetype`, `absorbed` to 12-31): a double count. `volume_num`
  enters only as CH216's denominator and CH214's fill control, under those tokens.
- **The market's `open_interest` innovation (mint share, the quiet exit via merge).** CH150 is not re-proposed; the sign of
  an OI fall without volume is ambiguous (a farmer recycling capital, or a holder closing a hedge); `participation`
  excludes event OI for its own reasons; not proposed.
- **`event_comment_count` innovations as attention.** Excluded from `participation` by the builder; "attention surges" not
  re-proposed; not proposed.
- **Venue clocks** (the midnight UTC reward epoch, weekends, holidays, the daily payout, US market hours). Round 13's rule
  8; CH212 and CH213 carry venue-clock gates that kill them if their events are a cron.
- **`page_index` and receipt order as a venue-wide state.** The `regime` family was dropped (worse than se1); CH217 reads
  them per row, as a quality covariate, engine-first.
- **Gamma's `competitive` field as a state.** Venue-computed, semantics unknown, under `participation` to 11-25.
- **Sponsored against native programmes; the sponsor's side.** A slow trait and a speculative mechanism; columns of
  `rwend` and `rwblink`.
- **Maker mark-out objects** (adverse selection by state judged on fills). J4-R's and CB13-T's holdouts refuse the worn
  days; E025 part B owns signal-conditional fills; every maker route here is gross, no fills, with the reward formula's
  arithmetic as the economic check.
- **E015, E022, LT7 and LT8 moderators during their windows.** Double counts on overlapping origins; CH214's adjacency to
  CH203 is disclosed with the lane rule; CH212's and CH213's adjacency to E022's S2 is disclosed with the pin rule.
- **Taker routes as primaries anywhere.** 2.9-7.2c hurdles against grosses of a fraction of a cent; every taker route here
  is reported, never a verdict.
- **UMA proposal and dispute objects as tests** (CH02, CH03, CH47, CH104). The field is on the forbidden-parse list and
  the natural test is a calibration on `res_7d`: CH221 is engine-first pending a ruling.
- **Decided-but-unresolved carry, longshot ask-selling, round-number walls, tick-regime discounts, reward cliffs, holding
  rewards, genesis, seed anchors, series rolls and base rates, mention baskets, external anchors, barrier confusion,
  quoter grain, wake-up prints, breathing book, mint share, turnover, synchronous prints, exit pressure, cost maps, quoted
  against traded, walked flow, trains, attention surges, breadth, class-conditioned longshots, arrivals and cancellations,
  the age of the move, opens and closes, concentration, hollow liquidity, program against human, last-mid proxy, front
  page, silent edits, races, jump or grind, high-water mark, overhang, alone or with the crowd, the farmer's choice, clips,
  the makers' vote, deadline moves, sibling birth, provenance, overdue, grind at the capture clock, the hour-held move,
  implied against realised, absorbed flow, resistance, patient money, the last-print anchor, calendar theta, the
  resolution-source class, two minutes of quote news, reward yield, the sweep clock, the quiet book, the market's own
  clock, steam, the reward start, desk-set dispute insurance, the minute of the news, the farmer touch, two minutes before
  the origin, the ladder that travelled.** CH01-CH211: not re-proposed; where an idea touches one, the parent is named
  and the new clock, population, state or join is stated (CH212 on CH37/CH152/CH201/CH206/CH209 and LT7's 13.6/13.7;
  CH213 on CH45/CH71/CH116/CH183/CH209/CH206/CH35/CH86/E004; CH214 on CH203/CH206/CH201/CH16/CH209/CH19/CH147/CH152;
  CH215 on CH19/CH206/CH152/CH201/CH98; CH216 on E007/CH79/CH170/CH173/CH132/CH162/CH164/CH154/CH193/CH39; CH217 on
  CH37/CH202 and the `regime` family; CH218 on CH37/CH194/CH176/CH191/CH202; CH219 on CH146/CH147/CH210/CH203; CH220 on
  CH149/CH132/CH204; CH221 on CH01/CH02/CH67/CH47/CH65/CH85/CH104/CH134/CH72).

---

## 5. Sources consulted

### 5.1 No host probe, no network, no data-dumps read this round (by instruction); what was read instead
The ledger's entries from 2026-10-21 ~18:55Z to 10-22 ~16:40Z (the LT4 censuses and E022's registration; the CB13-R,
CB14-W, CB15-P and CB18 closures; CB8-W1's smoke; LT5's seal and censuses and closure; LT6's seal, censuses and closure;
LT7's R1, re-check and design-text freeze, the reward-null ruling and amendment 13.6, the embargo rounds 4 and 5 and the
withdrawals of 12:00Z; LT8's draft, R1, re-check and freeze; the signal engine's `book0`, `crypto` and the book timing
overlap; the host resize; MC1's timeout; CB16-K's census; CB9's gating); `seals/lt7_rewards_probe.json` (every count in
fact 2); `reviews/LT7_REWARD_NULL_RULING_2026-10-22.md`, `reviews/LT7_REWARD_SWITCH_RULING_2026-10-22.md` and
`reviews/LT7_REWARD_CARRY_RECHECK_2026-10-22.md` (the three rulings and the carry's must-fixes);
`reviews/LT8_CENSUS_CODE_CHECK_2026-10-22.md` (the ten fixes adopted as reader rules); `LIVE_TESTS_4.md` 17 (as the ledger
quotes it), `LIVE_TESTS_5.md` 7.3, `LIVE_TESTS_6.md` 6.3, `LIVE_TESTS_8.md` 0, 1.0, 1.1 and 7 (the summary, the carried
lessons, the window and the census inputs); `seals/cb18_routing.json`; `signal_engine/CANDIDATES.md` (rounds 1-5, the
06:10Z notes, the round-13 idea notes, rows 1-20); `signal_engine/DESIGN_V1.md` section 3 (families, coverage);
`signal_engine/NORTH_STAR.md`; `CREATIVE_BATCH_13.md` lines H2, H3 and H8 (the monitor's counts); `LIVE_TRADE_MONITOR.md`
(the endpoint, cycle and stored fields); `MAKER_REWARDS_STUDY.md` section 1 and its scoring-rule row;
`reward_params_collector.py`'s docstring; `ext_sidecar.py`'s column lists; `cb16_common.py`'s forbidden-parse list;
`AREPO_V2_CHECKPOINT.md` (live section and exact next actions, 10-22 10:45Z); `CREATIVE_HYPOTHESES_2026-10-27.md` (round 13:
the whole file; its structural facts 1, 4-10 are re-used where unchanged and named as such); the lead sentences of
CH01-CH211 from all thirteen rounds. The cost-model, maker-rewards, stream and engine figures are quoted as round 13
quoted them where no newer count exists. The second pass (on `af960b80`) also read `ext_sidecar.py`'s `COLUMNS` list (the
event, series, neg-risk and fee fields), `CANDIDATES.md`'s builder status (rows 1-20) and its "Not candidates" list,
`MAKER_REWARDS_STUDY.md` row 53 and its quote rule, `LIVE_TESTS_7.md` 6.3 and 7, `queue/README.md`, `COLLECTION_HOST.md`'s
stream and monitor entries, the ledger's last 400 lines and the commits 3294d997..af960b80 (the 13.7 ruling, its erratum,
CV7 done and CC7 / CS7 promoted), for the duplicates table in 4.0 and the "what changed" list. Still no host probe, no
network and no data-dumps read.

### 5.2 External literature (named, not fetched)
Glosten and Milgrom 1985 (the maker's quote update); Foucault, Kadan and Kandel 2005 (limit-order book dynamics and the
cost of immediacy; the refill after a widening); Easley and O'Hara 1987 (trade size and information); Hasbrouck 1991 (the
information content of trades); Cont, Kukanov and Stoikov 2014 (order-flow imbalance; the symmetric part is CH214's,
the asymmetric CH203's); the Telonex reward case study and the venue's liquidity-rewards documentation as
`MAKER_REWARDS_STUDY.md` cites them (section 1 and the scoring-rule row only).
