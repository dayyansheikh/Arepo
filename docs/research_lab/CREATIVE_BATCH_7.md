# Creative batch 7 (CB7): specificity discount, geopolitics longshots, Kalshi-skewed maker (CH67 dropped)

`evidence_role: exploratory_historical` (CH63 Stage 1 on the fresh `h8_text` fetch; CH61 on the fresh `h8_geo` census;
CH73 Stage 1 on the worn C1 cross-venue pairs plus newly fetched prints) / `prospective` (CH63 and CH73 Stage 2, on data
collected after the CB7 freeze) | status: **REVISED after challenger round 1 (ACCEPT_WITH_REQUIRED_CHANGES); not
frozen.** Last updated 2026-10-17 UTC+1 (round-1 response; see §9). Every round-1 change tightens or discloses; no
threshold, floor or gate was relaxed.

This file turns CH63, CH61 and CH73 from `CREATIVE_HYPOTHESES_2026-10-17.md` (round 3, ranks 5, 8 and 4) into declared,
falsifiable tests, and records why CH67 (rank 7) is dropped. It follows `CREATIVE_BATCH_6.md` (CB6) in structure and
rules. Where it says "as CB1 §x", "as CB4 §x" or "as CB6 §x", that rule applies unchanged, with its challenger-round
and freeze-check fixes.
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim. AREPO never
  trades. Every P&L is a paper rule at modelled or recorded prices.
- Test tables bind only once the CB7 declaration hash is committed (`model_specs/cb7_v1.json`, the CB7 freeze). **The
  one exception is the pair of `T_seal`-bound fetches `h8_text` and `h8_geo` and their rules file** (§1.4), fixed by
  this document so that they can run before `T_seal` = 2026-10-22T00:00Z, before any CB7 analysis code exists.
- Queue specs are drafts in `queue/drafts/` (§4). None is in `queue/jobs/`.
- **Queue numbering.** CB7 uses **q0140-q0156, one id per job, no letter suffixes** (q0156, the text-edit audit, was
  added in challenger round 1 from the reserved range); q0157-q0159 stay reserved for CB7 renumbering. No CB7 id shares a numeric prefix with a committed or drafted spec (checked against
  `queue/jobs/` and `queue/drafts/` at drafting).

## 0. Summary, selection and scope

| Rank | Job | Hypothesis | Counted tests | Stage 1 data | Stage 2 data | Queue ids |
|---|---|---|---|---|---|---|
| 1 | **CB7-F** data | shared exclusion keys, smoke probe, `h8_text` and `h8_geo` fetches (**before `T_seal`**) and seals; C1-pair prints; prospective `textorig` table; fresh-pair list | none | n/a | n/a | q0140-q0146, q0151, q0153, q0154 |
| 2 | **CB7-S** specificity discount (CH63) | the more binding conditions a market's rules text carries, the more YES is overpriced at 7 days before the scheduled end (S1); buying NO at the recorded ask in high-condition markets, held to resolution, pays (S2) | S1 (mechanism); S2 (economic, Stage 2 only) | `h8_text`, full sample, single historical stage | prospective `textorig` cohort (origins after the freeze; text as of the origin; recorded asks) | q0147, q0148, q0151, q0152 |
| 3 | **CB7-G** geopolitics longshots (CH61) | YES longshots priced 0.02-0.10 in geopolitics-tagged markets at 30, 14 and 7 days before the scheduled end resolve YES often enough that buying the ask pays (G1) | G1 (economic) | `h8_geo` census | none in CB7 (Stage P only, months) | q0147, q0149 |
| 4 | **CB7-X** Kalshi-skewed maker (CH73) | Polymarket fills on the side Kalshi just moved toward lose money for the resting maker, net of the spread captured, so a maker who steps aside on that side for 20 minutes gains (X1) | X1 (economic) | C1 non-sports pairs (worn) + new Data API prints | fresh pairs matched after E009/E010 end, window from 2026-11-04 | q0146, q0147, q0150, q0153-q0155 |

**Counted: 3 fixed (S1, G1, X1) + up to 3 conditional (S1-rep, S2, X1-rep) = 3-6.** §2.5.

### 0.1 Queue id mapping (one id per job)

| Id | Job | Family | Earliest commit |
|---|---|---|---|
| q0140 | `cb7_smoke` (geopolitics tag id; Data API windowed-print bounds, ordering and coverage; counts only; no CLOB history) | F | after the smoke code exists and `seals/cb7_text_geo_rules.json` is committed |
| q0141 | `cb7_exclusion_keys` (event / neg-risk / series keys of the h1/h2/h3/h5/h5_ladders ids) | F | with q0140 |
| q0142 | `h8_text_fetch` (`T_seal`-bound) | F (S) | after the fetcher freeze check, rules file, q0140 PASS, headroom record |
| q0143 | `h8_geo_fetch` (`T_seal`-bound) | F (G) | as q0142 |
| q0144 | `h8_text_seal` (drops vs h8_tail, h7, h8_geo; listing hash) | F (S) | after `T_seal` and after the h8_tail and h7 seal copies are committed or recorded not run |
| q0145 | `h8_geo_seal` (drops vs h8_tail, h7; listing hash) | F (G) | as q0144 |
| q0146 | `cb7_xv_prints_fetch` (taker prints of the C1 pair Polymarket legs) | F (X) | after `T_seal` (not `T_seal`-bound; keeps the `net` lane free) |
| q0147 | `cb7_census` (S, G, X; counts only) | shared | after q0144, q0145, q0146 |
| q0148 | `cb7_screen_S` (S1, Stage 1) | S | after the CB7 freeze |
| q0149 | `cb7_screen_G` (G1, single historical stage) | G | after the CB7 freeze |
| q0150 | `cb7_screen_X` (X1, Stage 1) | X | after the CB7 freeze |
| q0151 | `cb7_text_rep_fetch` (rolling: prints before each `textorig` origin; outcomes at the end) | F (S) | at the freeze (data collection only; analysis only if S1 advanced) |
| q0152 | `cb7_rep_S` (S1-rep and S2, Stage 2) | S | only if S1 advanced; after `T7_S_out` |
| q0153 | `cb7_xv_pairlist` (fresh pair candidates by the frozen matcher, titles only) | F (X) | only if X1 advanced; at `T7_X_list` |
| q0154 | `cb7_xv_rep_fetch` (Kalshi candles, Polymarket history and prints for the frozen fresh pairs) | F (X) | after `T7_X_rep_end` + 2 h |
| q0155 | `cb7_rep_X` (X1-rep, Stage 2) | X | after q0154 |
| q0156 | `cb7_text_edit_audit` (on-chain initialization text vs current description, 200 seeded `h8_text` units; text-stability gate for S1; round 1) | S | after q0144 and the CB7 freeze; before q0148 |

### 0.2 Selection and scope

**What the drafting session read or computed.** Committed documents and code; `battery2.cumulative_count()` (§2.5);
`scripts/oracle/queue_status.sh` (read-only, host queue state). **One count-only Gamma probe** (2026-10-17T04:5xZ, keyless,
public): the slug `geopolitics` resolves to tag id **100265**; `/markets?tag_id=100265&closed=true` with `end_date` in
`[2025-06-01, 2026-10-11)` returns **6,876 markets in 1,872 events** (17 monthly windows, none capped at the 2,100 offset
limit); 6,863 have outcome labels `["Yes","No"]`; 1,309 are neg-risk members; 1,823 have `endDate − createdAt < 9 d`;
1,038 events have one market and 66 have 20 or more. The probe printed counts only. **No question text, description,
price, trade or outcome price was printed, stored or read.** The 8-markets-per-event cap of §CB7-G was chosen after
seeing that event-size distribution (a count, never an outcome) and is disclosed as such. No other CB7 quantity was
computed.

| Idea | Decision | Reason |
|---|---|---|
| **CH63** specificity discount | **include (S), priority** | Text was missing from h2 by a storage choice, not at the venue; a fresh fetch with `description` is cheap if prices come from the same single Data API request as the trade-before-`t` check (1 request per market). Power is the binding constraint (§CB7-S MDE), so Stage 1 uses the whole fresh sample and the replication is a prospective cohort whose text is stored **as of the origin** (removing the current-text leak) and whose asks are recorded |
| **CH61** geopolitics tails | **include (G), single historical stage** | n is not too small (6,876 tagged markets, 1,872 events in 16 months; the idea's 600-900 a year was low). The binding limit is the rare outcome: the MDE is about 3.5-4c on net per share (§CB7-G), i.e. only a YES rate about double the price is detectable. There is no honest within-batch replication (a prospective geopolitics cohort needs months), so G1 must clear the Stage-1 batch Holm before a Stage P registration |
| **CH73** Kalshi-skewed maker | **include (X)** | The C1 pairs (316, audited, `CROSS_VENUE_STUDY.md` §10) carry 1-minute Kalshi candles and 10-minute Polymarket history but no Polymarket prints; prints of the Polymarket legs are a permanent public record (about 8k requests). The pair set is worn for the lead itself (v1, r1, CB5-K), so Stage 1 is L1 at most and **Stage 2 uses fresh pairs whose window starts after E009/E010 end** (2026-11-03), from public post-hoc data only |
| **CH67** sibling-resolution unwind | **dropped** | Cannot be tested honestly in its stated form with AREPO's data (below) |

**Why CH67 is dropped (not weakened).**
1. *Cadence.* The idea's mechanism is "stale asks for minutes to hours after a member flips `closed`". `closed` is seen
   only at the 2-hourly complete captures, so the flip time is known to 0-2 h. The sweeps inside a pass are minutes
   after the *observation*, not after the flip. The minute scale is not observable.
2. *The statistic is mostly mechanical.* A member resolves only after its outcome was public for hours or days (UMA
   proposal plus the 2-hour challenge), so its price was already about 0 or 1 before the flip. After a NO flip the
   sum of open members' asks falls by the dead member's residual ask because the member leaves the sum, whatever the
   other quotes do. After a YES flip the siblings are worthless and the only route is the residual-bid sale that round 3
   itself rejected (§4, "impossible-bucket residual value").
3. *Already screened.* CB1-D tested sum-of-asks states on the same captures (dev 2026-10-11..16): D1 did not advance
   (+0.78 pp, p 0.0156, below the 1 pp floor, without-top-5 +0.15 pp) and D2 was not testable (33 triggers in 8 events).
   Conditioning on a flip makes the state rarer still.
4. *No identified "first-hour move".* If the flip carries no news (point 2), a reversal test reduces to generic quote
   noise reversion, which J4/J4-R already cover.

**Re-entry condition (not designed here).** Exact resolution times from chain logs (the UMA adapter or neg-risk adapter
resolution events via the keyless Polygon RPC reader that CB6-N builds), windowed taker prints of the sibling members in
`[t_res − 6 h, t_res + 6 h]`, and a matched-time control. That is a new declaration with its own census, not a rescue.

**Sports and weather.** Category scope is the user's decision (`CB7_SPORTS_IN_PRIMARY = false`). Sports is a reported,
uncounted stratum in S and X. Weather is excluded everywhere (CB2-W's `h6_weather` and live stage are never touched).
Crypto "Up or Down" is excluded from S (templated rules, no text variation).

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Prior use | Role in CB7 | Evidence ceiling |
|---|---|---|---|
| `history/h8_text` (**new**, q0142; seeded sample of up to 18,000 binary Yes/No markets with scheduled `end_at` in `[2025-04-01, T_fetchT − 7 d]`; Gamma frame **with `description`**, event ids, `negRiskMarketID`, series ids; one windowed taker-print request per market before its origin; outcomes only in `outcomes_guarded.csv.gz`) | none | **CB7-S Stage 1 only.** Whole sample, no split (§CB7-S explains why) | L1 |
| `history/h8_geo` (**new**, q0143; geopolitics tag 100265, every closed or ended-unclosed market with `end_at` in `[2025-06-01, T_fetchG − 7 d]`, life ≥ 9 d, ≤ 8 markets per event after the filters; all tag ids, event title and `fee_category` stored; one windowed taker-print request per origin (price and eligibility; **no CLOB history**); guarded outcomes) | none (the 2026-10-17 count probe read metadata counts only) | **CB7-G only** | L1 |
| `cross_venue/series/*.npz` + `matches.json` (C1: 316 pairs, 183 events, 517,616 usable steps; 149 sports) | cross-venue v1, r1 (20-test BY family twice), E009 design, CB5-K | **CB7-X Stage 1**, read-only. Worn for the lead itself; L1 ceiling | L1 |
| `research_lab/creative_batch7/xv_prints/` (**new**, q0146; taker prints of the 316 Polymarket legs over each pair's study window; no wallet stored) | none | **CB7-X Stage 1 fills** | L1 |
| `cb7_extract/textorig/` (**new** extractor table, pass step from `T7_S_rep_start`; §5.3) plus `creative_batch7/text_rep/` (q0151) | none | **CB7-S Stage 2**: markets whose scheduled end is 7 days after a complete capture, with recorded touch, sidecar fee schedule and `description` fetched in the same pass | L2 (out-of-time, post-freeze) |
| `creative_batch7/xv_rep/` (**new**, q0153/q0154): fresh pairs listed after 2026-11-03 from public metadata, then public Kalshi candles, Polymarket history and prints for `[T7_X_rep_start, T7_X_rep_end)` | none | **CB7-X Stage 2** | L2 (out-of-time, post-freeze) |
| `cross_venue_live/` (E009/E010 poller), `surprise_live/` (E011) | registered experiments | **never read** (runner refuses the roots). No CB7 statistic uses any data timed inside E009/E010's window (to 2026-11-03T00:00Z) on live pairs | - |
| `h2_main`, `h3_power` | worn; h3 retired (Ledger M3) | **not read**; their `sample.csv.gz` market ids (sha256-pinned) feed the exclusion keys only | - |
| `h4_seal`, `h5_cb1`, `h5_cb1_ladders`, `h6_weather`, `h7_cb4_era`, `h7_cb4_series`, `h8_tail` | SB2, CB1, CB2-W, CB4, CB6 | **not read** (runner refuses). Only committed seal copies under `docs/research_lab/seals/` are read, for **market ids only** (exclusion and drop lists) | - |
| `cb1_extract/` .. `cb6_extract/`, `cb3_followup/`, `cb6_followup/` | CB1-CB6 inputs | **not read by any CB7 code path** | - |
| Raw complete captures, sidecar, sweeps (host) | E-series, SB2, CB1-CB6 | read only by the `textorig` pass step (current capture) | - |

### 1.2 Dates (declared; UTC)

| Name | Value | Meaning |
|---|---|---|
| `T7_draft` | 2026-10-17T05:04Z | First draft. No CB7 quantity computed (the geo count probe is §0.2) |
| `T_seal` | 2026-10-22T00:00Z | SB2's h4 seal boundary. `h8_text` and `h8_geo` rows are capped at `min(T_fetch, T_seal)` and each fetch **must be complete before `T_seal`** (no chunk starts at or after it); otherwise `not_run_deadline` (no seal, no analysis, no refetch, cap unchanged; the dependent test is "not run (deadline)", p = 1, counted) |
| `T_fetchT`, `T_fetchG` | request clocks of the two frame walks, pinned in each manifest (expected 2026-10-18..20) | data end and administrative censoring of each fetch |
| `T7_latest_safe` | 2026-10-21T12:00Z | Latest useful host start of either fetch (about 2.4 h and 45 min of work). **No Mac fallback (round 1, item 6):** a fetch not complete at `T_seal` is recorded `not_run_deadline`, honestly, and its test is "not run (deadline)", p = 1, counted |
| `T7_S_rep_start` | **max(2026-10-30T00:00Z, first complete capture ≥ CB7 freeze commit + 2 h, first capture ≥ 2 h after the `textorig` pass step is deployed)**, pinned in a committed file | first CB7-S Stage-2 origin |
| `T7_S_rep_end` | `T7_S_rep_start` + 21 d | last origin (exclusive) |
| `T7_S_out` | `T7_S_rep_end` + 7 d + 14 d | outcome read for Stage 2 (scheduled ends ≤ `T7_S_rep_end` + 7 d, plus 14 d of resolution lag; still unresolved → censored, worst case binding) |
| `T7_X_list` | **max(2026-11-03T06:00Z, CB7 freeze + 24 h)** | fresh-pair candidate listing (q0153), only if X1 advanced. After E009/E010's fixed end |
| `T7_X_rep_start` | first 00:00Z at least 2 h after the audited pair list is committed, and ≥ 2026-11-04T00:00Z | Stage-2 window start; pinned in the committed pair list |
| `T7_X_rep_end` | `T7_X_rep_start` + 21 d | Stage-2 window end |
| J4-R window | 2026-10-16T00:00Z to 2026-10-21T00:00Z (`seals/j4r_window.json`) | no CB7 row lies in it: `h8_text`/`h8_geo` origins are ≤ `T_fetch` − 14 d, C1 pair windows end by 2026-08, and the Stage-2 windows start ≥ 2026-10-30 |

### 1.3 Sealed and untouched data (named)

- **Refused run ids and roots.** `run_cb7.py` refuses `h1_first`, `h2_main`, `h3_power`, `h4_seal`, `h5_cb1`, `h5_cb1_ladders`,
  `h6_weather`, `h7_cb4_era`, `h7_cb4_series`, `h8_tail`, every path under `cb1_extract/` to `cb6_extract/`,
  `cb3_followup/`, `cb6_followup/`, `cross_venue_live/` and `surprise_live/`. (Round 1: `h1_first` added. The only
  files read from h1/h2/h3 are the sha256-pinned `sample.csv.gz` id lists, by q0141.)
- **SEALED-H8T and SEALED-H8G.** `h8_text` and `h8_geo` are fetched and sealed (manifest, per-file sha256, listing
  sha256) before any CB7 analysis. Seal copies `docs/research_lab/seals/h8_text_SEAL.json` and `h8_geo_SEAL.json` are
  committed before q0147. Every reader verifies the listing hash and appends to `ACCESS_LOG.jsonl` (as CB1 SEALED-H5).
  No CB7 path reads `outcomes_guarded.csv.gz` before the CB7 freeze; the census reads no outcome.
- **Event-level disjointness (as CB6 §1.3, round-1 item 5).** One shared exclusion key set (q0141): every Gamma event
  id, `negRiskMarketID` and series id of every market in h1_first, h2_main, h3_power (`sample.csv.gz`) and the h5 and
  h5_ladders seal copies (files and sha256 pins identical to `seals/cb6_tail_rules.json`), looked up by market id (parse
  guard keeps ids and keys only). Frame markets sharing any key are removed **before sampling** in both fetches, counted
  by key type. More than 2% of exclusion ids without metadata → "disjointness unverified": S1 and G1 "not testable",
  p = 1, counted.
- **Drops at seal (fetches are independent).** At seal (after `T_seal`, so every pre-`T_seal` fetch is terminal), by id
  **and** by event / neg-risk / series key (light Gamma lookup by id, ≤ 2 rps, parse guard as above):
  - both: drop markets of `h8_tail` (ids from the committed `seals/h8_tail_SEAL.json`) and of `h7_cb4_era` /
    `h7_cb4_series` (committed seal copies). A run recorded `not_run_deadline` has nothing to drop;
  - `h8_text` only: also drop markets sharing an id or key with the **full `h8_geo` tag frame as walked, before any
    filter or cap** (`h8_geo/frame.csv.gz`; round 1, item 4), so a tagged market removed from `h8_geo` by a filter or
    the cap still cannot enter `h8_text`. `h8_geo` keeps priority because it
    is a census, and `h8_text` already excludes geopolitics by category before sampling.
  Drops are recorded as `DROPPED_*` blocks in the sealed listing (sealed files are never edited) and counted.
  Why at event level: markets of one event share their outcome, so a market-disjoint but event-shared unit is not
  independent evidence, and here it would also reveal CB6-T's sealed HOLDOUT outcomes (CB6-T's population includes
  geopolitics longshots).
- **h4_seal unchanged.** `h8_*` hold no information after `T_fetch < T_seal`. The C1 prints end by 2026-08. Stage-2 data
  lie after `T_seal` in calendar time; they are CB7's own pass-step table and post-hoc public reads of CB7-selected
  markets, never h4 data (as CB4-C, CB5 and CB6, disclosed). No frozen SB2 parameter changes.
- **E009/E010 (CH73).** The historical C1 pairs resolved by 2026-08; E009/E010 pairs were open from 2026-10-13, so the
  two sets share no market-time. CB7-X never opens `cross_venue_live/`. The Stage-2 pair list is built by CB7's own call of
  the frozen matcher on public metadata at `T7_X_list` (after E009/E010's fixed end), and its window starts
  ≥ 2026-11-04T00:00Z, so no CB7 statistic uses any price, quote or print timed inside E009/E010's window. Some fresh
  pairs may be the same markets as E009 pairs; only their post-window data are used. CB7 never loads
  `cross_venue_live.load_verified` or any file under `cross_venue_live/`.
- **CB5-K and the C1 provenance.** C1 membership is not fully outcome-blind (4 hand-dropped pairs were first surfaced by
  the outcome-disagreement list; CB5-K §data). X1 inherits that; X1 with those 4 pairs re-added is reported, not
  counted. CB5-K measures hour moderation of the lead on the same pairs; X1 is a different statistic on new data
  (prints). Neither can change E009/E010.
- **SEALED-P overlaps (disclosed).** CB7-S Stage 2 (origins from about 2026-10-30) overlaps E011's window (to 2026-11-10)
  and CB3/CB4-C/CB5/CB6 live windows in calendar time. CB7 reads none of their tables or outputs; its statistic (rules-text
  slope on calibration) cannot reveal theirs.
- **Results outside data directories.** Every CB7 result goes to `research_lab/creative_batch7/`. Nothing is written in
  `history/h8_text/` or `history/h8_geo/` after their seals except `ACCESS_LOG.jsonl`.

### 1.4 The rules file (committed before q0140-q0143)

`docs/research_lab/seals/cb7_text_geo_rules.json`, with a top-level `rules_sha256` and the hash of the source of every
rule function, holds everything the two fetches and the S/G analyses need that could otherwise be chosen after seeing
data: frame windows and seeds (`arepo-h8-text`, `arepo-h8-geo`, `arepo-cb7-smoke`), strata and weights, the exclusion
files with their sha256 pins (as CB6), key types and the 2% rule, the geopolitics tag (slug `geopolitics`, pinned id
100265; the smoke must resolve the slug to the pinned id), the per-event cap and its seed, the origin rules, the
condition-marker regexes (§CB7-S), the clarification markers and note pattern (identical to CB6's), the continuous-class
list (CB6's `class_c`), the status-quo list and theme map (§CB7-G), price bands and cells, and the tercile cut rule. The
fetchers refuse (exit 2) unless the committed file's hash equals the code's and every exclusion file exists and matches
its pin. **No regex, threshold, window or cut point is computed from, or revised after, any h8_text/h8_geo read**, except
the C cut points, which the fetch computes from the sampled markets' **text only** before any print request (§CB7-S).

## 2. Common rules (deltas from CB1 §2, CB4 §2 and CB6 §2)

### 2.1 Costs

As CB6 §2.1 for vocabulary (`cb1_history.HALF_SPREAD`: 2.05c below 0.05, 1.5c in [0.05, 0.20), 1.1c in [0.20, 0.80),
1.5c in [0.80, 0.95), 1.25c above; `economics.DOCS_CATEGORY_RATE`; `economics.REBATE_SHARE`). CB7 has **no dependency
on `model_specs/cost_regimes_v1.json`**:

| Test | Price and cost rule |
|---|---|
| S1 | mechanism; no cost |
| S2 (Stage 2 only) | buy NO at the **recorded** NO ask `a = 1 − best_bid(YES)` of the origin capture; taker fee `f(a) = r·a·(1 − a)` with `r` from the capture's sidecar `fee_schedule` under `fee_policy="conservative"` (max of schedule and docs table); `net = (1 − Y) − a − f(a)` per share; capital `a + f(a)`; held to resolution |
| G1 | buy YES at the modelled ask `a = min(m + half_spread(m), 0.999)`; **one fee rule, fixed now (round 1, item 5):** `f(a) = r·a·(1 − a)` with `r = economics.DOCS_CATEGORY_RATE[fee_category]` under CB1's conservative policy (geopolitics 0.0, `economics.py:41`; unknown or `other:*` 0.07, at a = 0.05 that is 0.33c), applied to every date. No cost register is read. **Binding spread robustness:** G1 recomputed with `a = m + max(half_spread(m), h_geo)`, where `h_geo` is the median half-spread `(ask − bid)/2` of geopolitics markets (`fee_category == "geopolitics"` or `topic_of == "geopolitics"`) with YES mid in [0.02, 0.10] over the complete captures in `[2026-10-22T00:00Z, 2026-10-25T00:00Z)`, measured by the census (q0147; spreads only, no outcomes); it must keep net > 0 and G1's p threshold |
| X1 | per filled share, the resting maker's mark-out at a recorded print price (below) **plus the rebate the skip forgoes**, `ρ_cat · r_cat · p(1 − p)` for prints on or after 2026-03-30, else 0. Adding the forgone rebate makes X1 harder to pass |
| Binding cost robustness | +0.75c against the route on every modelled or bought leg (S2: on `a`; G1: on `a`); X1: the alternative mark (§CB7-X) instead of a cost shift |

### 2.2 Clocks

As CB1 §2.2 and CB6 §2.2:
- A history price point stamped `s` is usable at `t` iff `s + 600 ≤ t` and it is at most 2 h old.
- Data API prints use the venue `timestamp`; a condition at `t` uses prints with `ts < t`. Truncation as CB1 §2.2: a
  condition is known true, unavailable or false; unavailable units are excluded, counted and enter the declared worst case.
- Kalshi candles are usable at their `end_ts`; the maker reacts at `end_ts + 120 s` (CH73's receipt-equivalent lag,
  the E009 design's 2-minute rule).
- Capture rows use their own `received_utc`.
- `closed_time` / Gamma `closedTime` is never a population condition or an anchor. It is **kept in the frame as a
  status field** (round 1, item 3). "Open at `t`" (S and G): a print in `[t − 7 d, t)` and a print-based price in the
  band. **This does not exclude every resolved market** (the draft's claim was false): a market resolved at `t − 3 d`
  still has prints in `[t − 7 d, t)`. Its last prints usually sit near 0 or 1 and fall outside the band, but not
  always. Hence the binding sensitivity below for S1 and G1, and the census counts units with `closed_time < t`.
- **Scheduled-end look-ahead (disclosed).** `end_at` is Gamma `endDate` read at `T_fetch`. S and G anchor origins on it
  (`end_at − k d`). If Gamma rewrote `endDate` on early resolution, an early-YES market would get origins just before
  its event, biasing G1 **towards** the hypothesis. CB1 found that Gamma keeps the scheduled date (CB1 §6 risk 4). The
  census reports the share of frame markets with `|closed_time − end_at| < 1 h` and with `closed_time < end_at − 7 d`
  (status counts, not outcomes) and the number of eligible units with `closed_time < t` (S: `t7`; G: each `t_k`).
  **S1 and G1 both carry a binding sensitivity** that drops markets with `closed_time < end_at − 2 d` (this removes
  every unit resolved before its origin, since all origins are ≤ `end_at − 7 d`, and every early resolution that a
  rewritten `endDate` could hide); the sign and the p threshold must hold.

### 2.3 Uncertainty and decision rule

As CB6 §2.3: unweighted estimates primary; one-sided p = the max over the declared cluster ways of CR1 (normal z); CI by
2,000-draw cluster bootstrap (seed 717); small-G rule (G ≥ 30 CR1; 15 ≤ G < 30 CR2 with t(G − 1) and Webb wild bootstrap,
9,999 draws; G < 15 in any declared way → "not testable", p = 1, counted); testability otherwise ≥ 100 units and ≥ 30
clusters per way. An "unknown", "unverified" or "inconclusive" gate never counts as met.

- **Stage 1 (S1, X1).** Advance iff one-sided p < 0.01, the §2.4 floor is met, every binding placebo and robustness
  holds (§2.6) and every gate is met. A BY label (q = 0.10 over `battery2.cumulative_count()`) is attached as triage only.
  A Stage-1 batch Holm label (one-sided α = 0.01 over k1 = 3: S1, G1, X1) is reported for S1 and X1.
- **G1 (single historical stage).** Because G1 has no within-batch replication, it is **carried to a Stage P
  registration only if it meets the Stage-1 batch Holm** (one-sided α = 0.01 over S1, G1, X1, k1 = 3), the floor, the
  inverted tail gate and every binding robustness. Otherwise it is "not advanced". A G1 pass is "single-stage historical
  screen, unreplicated (L1)".
- **Stage 2 (S1-rep, S2, X1-rep).** Holm at α = 0.05 one-sided over all CB7 tests reaching Stage 2 (k ≤ 3), each in its
  Stage-1 direction, with k fixed when the last Stage-1 result is final; early finishers are judged against α/k. A pass
  also needs the floor, the binding robustness and the placebos. Labels: S1-rep and X1-rep passes are
  "out-of-time replication on post-freeze data (L2)"; **S2 has no Stage 1**, so an S2 pass is "single stage on
  post-freeze data, recorded asks, unreplicated (L1)", still in the Holm k (as CB6-R2).
- **Stage P** is a separate registration for any survivor (§2.9).

### 2.4 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate |
|---|---|---|
| S1 | mechanism | `β ≥ +1.0c` of YES overpricing per additional condition-marker type |
| S2 | economic | net ≥ +1.0c per share in the high-C group and `R_ann ≥ 10%` |
| G1 | economic | net ≥ +1.0c per share (YES bought at the modelled ask) and `R_ann ≥ 10%`; inverted tail gate (§CB7-G) |
| X1 | economic | mean mark-out of the skipped fills (plus forgone rebate) ≤ −0.5c per share, i.e. stepping aside gains ≥ 0.5c per skipped share |

### 2.5 Counting (M3 rule)

- Every counted test writes one `trials.jsonl` line via `provenance.append_trial`: kinds `cb7_test` (Stage 1 and G1)
  and `cb7_replication` (Stage 2), with `ml_explain` count lines `creative_batch_7:S`, `creative_batch_7:G`,
  `creative_batch_7:X` (`n_tests`). `cb7_descriptive` (EXCLUDE): census, gates, marker prevalences, tercile tables,
  per-month and per-theme tables, sports strata, every reported variant. Placebo lines `evidence_role: "placebo"`, count 0.
- New `battery2.KIND_RULES` entries: `cb7_test`, `cb7_replication` EXCLUDE ("counted by the matching
  `creative_batch_7:*` count line"); `cb7_descriptive` EXCLUDE. Unknown kinds still raise; a unit test runs the counter on
  the real `trials.jsonl`.
- **Cumulative count at drafting.** `battery2.cumulative_count()` on the Mac working tree (rule `battery2-count-v1`)
  returned **1,121** at 2026-10-17T05:00Z (340 `flow_screen`, 494 `ml_explain`). The working tree's `trials.jsonl` carries
  uncommitted lines from another session and the host appends its own, so this is a lower bound. Every counting CB7
  run first runs the host union step (`union_jsonl.py`, as CB6 §2.5) and records the post-union value.
- **CB7 adds 3 fixed tests (S1, G1, X1) and up to 3 conditional ones (S1-rep, S2, X1-rep): 3-6 tests, taking the
  denominator to at least 1,124-1,127.**
- Tests behind a failed or unknown gate (GS, GG, GX, the smoke, disjointness, the `T_seal` deadline) are "not testable"
  or "not run" (p = 1) and **still counted**.

### 2.6 Placebos and robustness

Design rule as CB6 §2.6: every binding placebo names the alternative under which it advances; calibration placebos are
judged on the p threshold alone (floors off; G1 keeps its inverted tail gate, a p-type bound). Seeds 7171-7176.

- **S1 calibrated-null placebo (calibration; binding).** Outcomes redrawn per event exactly as CB6's T1 placebo (one
  uniform per event, comonotone across the event's non-neg-risk markets, neg-risk members on disjoint sub-intervals so at
  most one resolves YES; `Y' = 1{U_e ∈ interval of length m}`); S1 recomputed on 200 draws (seed 7171), floor off;
  **advance rate ≤ 1.5%**. *Alternative guarded:* anti-conservative clustering of a binary outcome repeated within
  events and templated series.
- **S1 marker-shuffle attribution (binding for crediting "specificity").** C permuted across markets within (cb1_topic ×
  description-length decile) cells (decile edges from the frame, text only); S1 recomputed on 200 draws (seed 7172). The
  markers are credited only if the real β exceeds the 98.5th percentile of the shuffled β. *Alternative:* β is carried by
  text length or template, not by the conditions (the permutation keeps C's association with length, so a length-driven
  β is reproduced by the shuffle and the check fails). A failure does not block an advance; the verdict then reads
  "longer rules text, not specific conditions" (attribution only, as CB6's class shuffle, to avoid CB5 failure mode 5).
- **S2 break-even placebo (binding, Stage 2).** Fills kept; `Y' ~ Bern(1 − a − f(a))` per event (mutual exclusion for
  neg-risk members), expected net 0; 200 draws (seed 7173), p only; ≤ 1.5%.
- **G1 break-even placebo (calibration; binding).** `Y' ~ Bern(a + f(a))` per event with neg-risk mutual exclusion,
  expected net 0; the G1 p condition and the inverted tail gate on 200 draws (seed 7174), floor and `R_ann` off; **≤ 1.5%**.
  *Alternative:* the rare-event p value and the event-level bound are anti-conservative at the realised number of YES
  clusters, especially with a few large themes.
- **X1 time-shift calibration placebo (binding).** Per pair, the Kalshi move-event times are shifted circularly within
  the pair's window by an offset drawn uniformly in `[6 h, W − 6 h]` (W = window length; every C1 window is ≥ 200
  ten-minute steps, about 33 h, so the range is non-empty), independently per pair and draw; X1 recomputed on 200 draws
  (seed 7175), p only; **≤ 1.5%**. *Alternative:* fills inside any burst-shaped set of 20-minute windows look adverse
  because of within-window dependence (one future mark shared by many prints), so the clustered p is anti-conservative.
  The shift keeps the burstiness of Kalshi moves and destroys only their timing link to Polymarket.
- **X1 wrong-side attribution (binding for crediting "skew").** X1' = the same statistic on the opposite-side prints in
  the same skip windows. The skew is credited only if `X1' − X1 ≥ |X1| / 2`. *Alternative:* fills on both sides are
  adverse after any Kalshi move (news hours), which would justify a pause, not a skew. A failure leaves an X1 advance
  standing, labelled "post-move fills adverse on both sides: a pause, not a skew".

**Binding robustness for any advance or pass:**
- (i) S2, G1: the +0.75c cost robustness keeps net > 0; X1: the alternative mark (two-sided print midpoint) keeps X1's
  sign and at least half its magnitude;
- (ii) the test still meets its p threshold and floor **without the top 5 event clusters** by absolute contribution, in
  each way (S1: contribution = the event's share of `Σ x̃·g` with `x̃` the cell-demeaned C; G1 and X1: of the net sum).
  For G1 this means a broad effect is required: five winning wars cannot carry it;
- (iii) unweighted and design-weighted (S: `sample_weight`; X: size-weighted) estimates agree in sign;
- (iv) **sign by month**: S1 has β > 0 in at least two thirds of `end_at` months with ≥ 150 units; X1 is negative in at
  least two thirds of months with ≥ 500 skipped prints. For G1 (a rare-event carry, where thin months flip sign by
  construction) sign by calendar quarter is reported, not binding, as CB1 §2.8;
- (v) the declared worst case for censored or unavailable units keeps the estimate on the declared side and the p
  threshold (per test);
- (vi) S1: the estimate restricted to units with a print in the last 24 h before the origin has β's sign and ≥ half its
  magnitude (staleness of print-based prices);
- (vii) S1 and G1: the `closed_time < end_at − 2 d` drop sensitivity of §2.2 (round 1, item 3, extended to S1);
- (viii) X1: latency 300 s instead of 120 s keeps the sign and ≥ half the magnitude;
- (ix) G1: the measured-spread robustness of §2.1 (round 1, item 5);
- (x) G1: the **tag-and-topic subset** (markets carrying tag 100265 **and** with `history_topics.topic_of(question,
  event_title, slug, fee_category) == "geopolitics"`) keeps G1's sign and p threshold (round 1, item 2). *Alternative
  guarded:* the venue's tag sweeps in markets that are not geopolitical discrete events (sports diplomacy, elections,
  economics), so an effect in the tagged set could belong to another category;
- (xi) S1: the **text-stability gate** of §CB7-S (on-chain initialization-text audit) is met.

Reported, not binding: the S tercile contrast, per-marker coefficients, S1 including clarification-marked markets and
including sports, S1 at the 1-day origin (Stage 2 only, where captures give it free), G1 with status-quo questions,
without the top theme, by fee category and by quarter, X1 at 20 minutes and with a 10-minute skip window, X1 with the 4
outcome-surfaced pairs re-added, X1 sports stratum, +1c costs.

### 2.7 Pre-freeze census (q0147; counts only)

An outcome guard drops outcome columns before population code runs (CB1 §2.9); each family gets a field-restricted
accessor; a unit test asserts that no census path receives a target field. **No β, net, mark-out, YES rate or log
loss is computed.**

- **S (h8_text):** frame and sample counts by stratum; key drops by type, unverified share; seal drops (h8_tail, h7,
  h8_geo); clarification-marked share by topic; censored share (status at `T_fetchT`); eligible units by topic × band;
  C distribution and cut points by topic; prevalence of each marker; within-cell SD of C; `|closed_time − end_at|`
  counts and units with `closed_time < t7` (§2.2); **share of descriptions longer than the 4,000 stored characters**
  (markers are computed on the full text, round 1, item 1); **text-only design effect** of S1 (below); the S1 MDE from
  these counts. **Gate GS:** ≥ 3,000 eligible units, ≥ 1,000 event × resolution-week clusters, ≥ 300 series/event
  clusters, within-cell SD of C ≥ 0.5. Fail → S1 "not testable" (counted).
- **G (h8_geo):** frame counts, per-event cap effects, exclusions by reason (continuous class, status quo, Other
  placeholder, keys, seal drops), eligible units by origin and band, event clusters, themes with ≥ 1 unit, expected YES
  `Σ m` (a price, not an outcome); units with `closed_time < t_k`; **tag-only share** (tagged markets whose `topic_of`
  is not geopolitics) and the eligible units in the tag-and-topic subset; `h_geo`, the measured median half-spread of §2.1
  (captures `[2026-10-22T00:00Z, 2026-10-25T00:00Z)`, spreads only). **Gate GG:** ≥ 300 eligible units, ≥ 100 event clusters, ≥ 15 theme clusters and
  `Σ m ≥ 15`. Fail → G1 "not testable" (counted). (The ≥ 10 YES-cluster rule is applied at analysis, §CB7-G.)
- **X (C1 + prints):** pairs and days fetched, capped days, prints per pair; Kalshi move events by sign; prints in S, S'
  and neither (**counts only**); event and date clusters with ≥ 1 S print. **Gate GX:** ≥ 2,000 S prints, ≥ 300 skip
  windows with ≥ 1 S print, ≥ 30 event clusters and ≥ 30 UTC dates with S prints (non-sports). Fail → X1 "not testable".
- **S1 design effect, text only (round 1, should-fix).** `deff_S = 1 + (m̄ − 1)·ρ_C`, with `m̄` the mean units per
  cluster and `ρ_C` the intraclass correlation of the cell-demeaned C within series/event clusters (the larger of the two
  ways). This takes the outcome's within-cluster correlation as 1, an upper bound, and reads no outcome. The S1 MDE is
  recomputed with it.
- MDEs recomputed from these counts (never used to change a floor, window or threshold).

### 2.8 Compute, network, disk and stop rules

- Host: 1 OCPU, about 5.6 GiB RAM shared with the collector. Queue worker as CB6 §2.8 (one job per lane, nice 19,
  `MemAvailable ≥ mem_mb + 1200`, address cap 2 × `mem_mb`, 02:45-05:30 UTC start blackout for `mem_mb ≥ 500`). Never two
  multi-GB jobs at once (none of CB7's is).
- **The `net` lane before `T_seal`.** At drafting (2026-10-17T04:45Z) it holds q0043 (h6, partial after two 2.5-h
  chunks), then the h7 frame and fetch pairs (q0081f/q0081, q0082f/q0082) and CB6's q0120 (`h8_tail`, about 3.5 h, still a
  draft): about 15-20 h of work, all at priority 61. **CB7's `T_seal`-bound jobs:**
  - q0140 smoke (priority 62, about 60 requests, < 5 min) and q0141 exclusion keys (61, about 850 requests, about 6 min);
  - q0142 `h8_text` (61, `--budget-min 85`): about 9k frame requests (5 windows a day over about 555 days, closed and
    ended-unclosed walks) + 18k print requests (1 per sampled market) ≈ **27k requests, about 1.9 h at 4 rps, about
    2.4 h wall (2 chunks)**; output ≤ 0.15 GB; RAM ≤ 0.8 GB (streamed frame, as CB6);
  - q0143 `h8_geo` (61, `--budget-min 85`): about 80 tag-walk requests, then **one windowed taker-print request per
    origin** (about 3,300 markets × about 2.3 origins; price and eligibility from the same request, no CLOB history)
    ≈ **8k requests, about 35 min, about 45 min wall (1 chunk)**; output ≤ 0.05 GB.
  Total ≈ 36k requests, **about 3.2 h wall**. q0140-q0143 sit at 61-62, the top `T_seal`-bound band (round 1, item 6:
  keep them high); with higher ids, q0141-q0143 yield at chunk boundaries to the earlier `T_seal`-bound jobs (ties
  broken by ascending id, `queue_worker.py`), and q0143 follows q0142. Expected host run 2026-10-18..19 if the code is
  ready; the h7/h8_tail fetches refuse above their own data-dumps caps, which may free the lane earlier.
- **No Mac fallback (round 1, item 6).** The Mac runs no background jobs and its data-dumps were retired, so a Mac run
  would breach the data-location and memory-heavy-job rules. If a fetch is not complete before `T_seal`, it is recorded
  `not_run_deadline` and its test "not run (deadline)", p = 1, counted. **The real schedule risk is the code and the
  fetcher freeze check**, so q0140-q0143 come first in §8 and the fetch code is kept to the declared minimum (§5.1).
- **Deadline mechanics** as CB6 q0120: no chunk starts at or after `T_seal`; incomplete at `T_seal` → `NOT_RUN_DEADLINE.json`
  and status `not_run_deadline`.
- **Disk guard.** Host data-dumps was 9.9 GB at 2026-10-17T04:45Z, growing about 0.95 GB a day; 8-day snapshot deletion
  became active on 2026-10-17 and the collector cap is 13 GB (`RETENTION.md`). Every CB7 data job exits 75 (not now) when
  data-dumps size + its output cap > **12.5 GB** (the same fetch cap CB6's `cb6_tail.py` uses). Output caps: `h8_text`
  0.15 GB, `h8_geo` 0.05 GB, C1 prints 0.25 GB, `textorig` 0.03 GB, text Stage-2 prints 0.03 GB, fresh-pair data 0.10 GB
  (total ≤ 0.61 GB). The commit of each data job records the current size and the margin. The precondition never changes
  retention.
- **After `T_seal`:** q0146 (C1 prints, about 8k requests, `net`, priority 45, about 40 min) and the rolling and Stage-2
  fetches at `--rps 2` on `cpu` (q0151) or `net` (q0153, q0154); analysis jobs on `cpu` at 38-40.
- **Network etiquette:** shared `Limiter`, yield to the live collector, 429 and `Retry-After` back-off, stop on repeated
  429, collector-health stop (as CB6). Kalshi requests ≤ 2 rps.
- 10 CPU-hour cap per family. A job failing twice for the same non-transient reason stops and is recorded. A null is "not
  detected at MDE x". **No re-screen of a failed CB7 test** with altered windows, origins, bands, markers, cut points,
  thresholds, lags, horizons or populations, on any data.

### 2.9 Funnel and Stage P

Screen (Stage 1) → selection by gates, placebos and robustness → frozen replication (Stage 2, here **out-of-time on
post-freeze data** for S and X) → separate prospective confirmation (Stage P) → economic validation at recorded prices.
- **S survivor (Stage P-S).** The `textorig` cohort continued under its own registration, S2's recorded-ask rule with
  sweep-checked depth, a fill model for the maker version (NO bids resting in high-C markets) using CB6-C's model if
  adopted. Text is stored at the origin, so the current-text risk does not exist there.
- **G survivor (Stage P-G).** A prospective geopolitics-longshot cohort at the 30/14/7-day origins from the complete
  captures (recorded asks), tag membership and text stored at first sighting; outcomes need months; acceptance needs the
  inverted tail gate at 95% with ≥ 10 YES event clusters.
- **X survivor (Stage P-X).** A receipt-timed Kalshi feed plus a targeted Polymarket book poller on audited pairs, the
  skip rule applied in real time with paper quotes at the recorded touch.

---

## 3. Tests

### CB7-S: Specificity discount (CH63)

**Question.** Holding price band and topic fixed, is YES more overpriced, 7 days before the scheduled end, the more binding
conditions the rules text carries (S1)? If so, does buying NO at the recorded ask in high-condition markets, held to
resolution, pay after costs (S2)?

**Why new / overlap.** No AREPO test has used rules text. CB1-E's genesis text test was untestable (text not stored); CB6-T
uses a six-word class regex over the question, not condition counts, on `h8_tail` (disjoint by event key, §1.3).

**Data (q0142; spec §4).** `h8_text`: frame `frame-v2-random-windows` with **5 random 15-minute windows per day** (seeded
`arepo-h8-text`, drawn independently of any market attribute) over scheduled `end_at` in `[2025-04-01, T_fetchT − 7 d]`,
closed walk and ended-unclosed walk (censored units are kept and counted), capped windows dropped and counted, frame rows
with `description` (first 4,000 characters stored, **plus the full text's character length and sha256**; round 1,
item 1), `event_ids`, `neg_risk_market_id`, `series_ids`, outcome labels, `closed_time` as a status field; outcome
prices only in `outcomes_guarded.csv.gz`. The window is about 18 months; its start was not chosen from any outcome.

**Population (frozen frame, before sampling).** Outcome labels exactly `["Yes", "No"]`; scheduled life
`end_at − created_at ≥ 9 d`; not weather (`fee_category` or `TEMP_RE`); not crypto "Up or Down" (`CB1_UPDOWN_RE`); not
geopolitics (`fee_category == "geopolitics"` or `history_topics.topic_of(...) == "geopolitics"`; reserved for `h8_geo`);
not a neg-risk "Other" or placeholder member; no exclusion id or key. Sports kept as a reported stratum.

**Sample.** Up to **18,000** markets (all if fewer), strata status × `cb1_topic` × `end_at` month, weights non-sports 1.0,
sports 0.25, seed `arepo-h8-text`; `inclusion_prob` and `sample_weight` stored. No price, volume or outcome input.

**Origin and price (one request per market).** `t7 = end_at − 7 d`. One request
`/trades?market=<cid>&start=t7 − 7 d&end=t7 − 1&takerOnly=true&limit=50` (newest first; ordering and bounds verified by the
smoke). From the returned prints, mapped to YES terms (BUY YES at p, or SELL NO at q → YES 1 − q, etc., as CB6-N):
- eligible iff ≥ 1 print in `[t7 − 7 d, t7)` (empty → ineligible; request failure → unavailable, counted);
- **price `m`** = size-weighted VWAP (YES terms) of the prints in `[t7 − 24 h, t7)` if any, else the price of the latest
  print in `[t7 − 7 d, t7)` (staleness recorded; robustness (vi));
- eligible iff `m ∈ [0.05, 0.95]`.
- Disclosed: a print-based price can sit at the bid or the ask; this adds noise of about a half-spread, not a bias
  related to C unless the side mix differs by C (checked by (vi) and reported by C tercile).

**Text features (fixed now; computed by the fetch from frame text only, before any print request, and stored in
`text_features.csv.gz` whose sha256 enters the manifest).** **Every marker and the clarification rule are evaluated on
the FULL description as returned by Gamma, in memory, before the stored copy is truncated to 4,000 characters** (round 1,
item 1: a marker or clarification after character 4,000 must not be missed); `text_features.csv.gz` carries the full
length and sha256 next to M1-M7, C and the clarification flag. Lowercased text unless stated; seven marker types, each
counted present (1) or absent (0):

| Type | Text | Pattern |
|---|---|---|
| M1 must | description | `\bmust\b` |
| M2 official | description | `\bofficial(?:ly|s)?\b` |
| M3 named source | description | `\baccording to\b` |
| M4 conjunction | **question** | `\band\b|&` |
| M5 time-of-day deadline | description | `\b(?:before|by|prior to|no later than)\s+\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)` |
| M6 time zone | description, **case-sensitive** | `\b(?:ET|EST|EDT)\b` |
| M7 named URL | description | `https?://|\bwww\.` |

`C = Σ M_i ∈ {0, …, 7}`. **Declared deviations from the idea text** (made now, before any data): "and" is read in the
question, because in descriptions it is near-universal and could not vary; "before <time>" includes "by", "prior to"
and "no later than", the common forms of the same condition. No other word was added.
- **Clarification rule** as CB6: markers `clarif`, `update:`, `updated`, `additional context`, `edit:` and the dated
  `note:` pattern (identical strings to `seals/cb6_tail_rules.json`); such markets are excluded from S1 and counted;
  S1 including them is reported. Reason: the description is the *current* text and a post-event clarification can
  encode the outcome. Residual risk: an unmarked post-event edit; Stage 2 removes it by storing text at the origin.
- **Cut points (reported tercile contrast and S2's high-C group).** Per `cb1_topic`, over the sampled markets' C (text
  only): `c_L` = the smallest integer with share(C ≤ c_L) ≥ 1/3; `c_H` = the largest integer with share(C ≥ c_H) ≥ 1/3;
  if `c_H ≤ c_L` the topic has no tercile contrast (counted). Written at the fetch, hashed, never revised.

**S1 statistic.** Unit = eligible market (one origin). `g = m − Y` (YES price minus YES payout; Y = 1, 0 or 0.5 for 50-50).
Cells = `cb1_topic` × band, bands `[0.05, 0.25)`, `[0.25, 0.50)`, `[0.50, 0.75)`, `[0.75, 0.95]`.
**β = OLS slope of g on C with cell fixed effects** (unweighted, non-sports, clarification-marked excluded). Test β > 0.
*Why a slope, not the idea's tercile contrast:* with C an integer 0-7 the terciles are tie-heavy and the contrast discards
the middle third; the slope uses every unit and the tercile contrast is reported. This is a declared change.

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **S1** | mechanism | eligible market at `t7` (h8_text; Stage 2: `textorig` unit) | within-cell slope of (price − outcome) on C | > 0 |
| **S2** | economic (Stage 2 only) | `textorig` unit with `C ≥ c_H`, NO bought at the recorded ask | mean net per share | > 0 |

**Clustering.** Event × resolution ISO week of `end_at` (neg-risk members merged; CB1 rule) and series id (event id if
none), which absorbs shared templates. p = max over the two (small-G rule).

**Worst cases (binding).** Censored (not resolved at `T_fetchT`): Y set against the hypothesis (Y = 1 if C is above the
cell median, else 0); β must stay > 0 and keep p < 0.01. Unavailable print requests: same assignment if they would have
been eligible by C alone (they enter with the cell-median price).

**MDE (assumptions; the census replaces them, including a text-only design effect, §2.7).** 18,000 sampled × about 0.9
after seal drops × about 0.31 eligible ≈ 5,000 units; `sd(g | cell)` ≈ 0.39 (mean `m(1 − m)` ≈ 0.15); within-cell
`sd(C)` ≈ 1.2. SE(β) ≈ 0.39 / (1.2 × √5,000) × √deff. With the draft's deff 1.5 the MDE was 1.8c per marker; **round 1
(should-fix): templated series make C strongly clustered, so the working design effect is about 3, SE ≈ 0.80c and
the Stage-1 MDE ≈ 2.5c per marker** (z 2.33 + 0.84), about 5-6c across the extreme terciles. The census's
`deff_S = 1 + (m̄ − 1)·ρ_C` (an upper bound that reads no outcome) replaces this figure. The 1.0c floor is far below the
MDE: Stage 1 detects only a strong discount, which is why it uses the whole sample (a 50/50 SCREEN/HOLDOUT split would
put each block near 3.5c and end-to-end power for a 1.4c effect under 5%). Stage 2: up to 120 units per capture × about
250 captures, about 50% eligible, ≈ 15,000 units; with deff 3, SE ≈ 0.46c, **Stage-2 S1 MDE ≈ 1.5c** (Holm z up to 2.39
+ 0.84). **S2 MDE (round 1, item 7):** the high-C group is about one third of Stage-2 units, ≈ 5,000; per-share net of a
NO buy at mid-range recorded asks has SD ≈ 0.42; design effect ≈ 3 (events and templates); SE ≈ 0.42 × √3 / √5,000 ≈
1.03c; **S2 MDE ≈ 3.3c per share** at the first Holm step (z 2.39 + 0.84), about 3.0c at the last (z 1.96 + 0.84),
against a 1.0c floor. S2 can confirm only a large absolute mispricing in the high-C group.

**Text-stability gate (binding for any S1 advance; round 1, should-fix, declared now, code later).** Gamma's `description`
is the current text. Before q0148 runs, `q0156_cb7_text_edit_audit` draws a seeded subsample (`arepo-cb7-uma-audit`) of
200 eligible, clarification-unmarked `h8_text` units and, for each, reads the text posted on chain at market creation:
the `ancillaryData` of the UMA CTF adapter's question-initialization event for the market's `questionID` (keyless
Polygon RPC; adapter address and event topic pinned from Polymarket's contracts page at implementation, not from
memory). It computes C on the decoded initialization text with the same M1-M7 (M4 on the question within it) and
compares with C on the current description. No outcome, price or print is read.
- **Metric:** the share of audited units whose C differs between the two texts.
- **Gate:** the one-sided 95% Wilson upper bound of that share must be ≤ **0.10**. If more than 20% of the 200 cannot
  be retrieved or decoded, the gate is "unverified" and S1 **cannot advance** (an unverified gate never counts as met).
- The audit is `cb7_descriptive` (not counted) and its result is committed before q0148 runs. It does not change C,
  the population or any threshold; a failed gate only blocks S1's advance, which is then recorded "not advanced (text
  unstable)", still counted.

**Stage 2 (registered only if S1 advanced; data collected from `T7_S_rep_start` regardless, analysis refused otherwise).**
- `textorig` pass step (§5.3): at each complete capture with `received_utc = r`, binary Yes/No markets with
  `end_date ∈ (r + 7 d, r + 7 d + 2 h]` (each market is caught once; a market whose slot falls in a capture gap is
  missing, counted), same type filters as the frame, capture touch mid in `[0.04, 0.96]`; at most 120 per capture by
  seeded hash (`arepo-cb7-textorig|<capture_id>`). Stored: ids, keys, `cb1_topic` inputs, `fee_schedule`, best bid/ask,
  first-sweep sizes where swept, `end_date`, question, and the **`description` fetched by Gamma id in the same pass**
  (≤ 3 requests; missing → unit unavailable, counted). `t7 := r`.
- q0151 (rolling, every 6 h): the S1 print request for each unit at `t7 + 3 h` or later (prints before `t7` are a
  permanent record); outcome lookups (guarded) after `T7_S_out`.
- S1-rep: identical β, cells, bands, markers and clustering on these units; text as of `t7`; clarification markers still
  excluded for comparability.
- **S2:** units with `C ≥ c_H` (the h8_text cut points, frozen at its seal), NO bought at `a = 1 − best_bid(YES)` of the
  origin capture, fee from the capture's sidecar, `net = (1 − Y) − a − f(a)`. Capacity reported (sweep `bid_size_1` of YES
  where swept). Depth-checked subset (sweep `bid_size_1 ≥ 5`) reported. Censored at `T7_S_out` → NO loses (binding).

**What would kill CH63.** GS fails; disjointness unverified; the text-stability gate fails or is unverified; S1 not
detected at MDE; the calibrated-null placebo advances;
the censoring worst case flips β; β holds only with clarification-marked markets or only in sports; the effect fails out of
time (Stage 2); S2 ≤ 0 at recorded asks after fees or the +0.75c robustness.

**Verdict map.** S1 and S1-rep pass with the marker attribution → "rules-text specificity predicts YES overpricing
out of time (L2)"; with S2 → "and a NO buy at recorded asks paid in one post-freeze window (L1)" → Stage P-S. Attribution
fails → "longer rules text, not specific conditions". S1 not detected → CH63 closed at the Stage-1 MDE (not "absent").

**Stop rule.** S1 not advanced → q0152 is not committed; the `textorig` rows are kept (no deletion) and never analysed
for CH63 under this declaration.

### CB7-G: Geopolitics discrete tails (CH61)

**Question.** In geopolitics-tagged binary markets, do YES longshots priced 0.02-0.10 at 30, 14 or 7 days before the scheduled
end resolve YES often enough that buying the ask and holding to resolution pays (G1)?

**Why new / overlap.** CB1-C sold longshots on h2 (all categories; C1 -3.84c). CB6-T asks whether a flagged class of
longshots (rule text, drift, young buyers) is underpriced relative to unflagged ones on `h8_tail`; its population includes
geopolitics longshots, which is why `h8_geo` drops every `h8_tail` market and key (§1.3). G1 is an absolute, single-category
carry, not a contrast.

**Data (q0143).** `h8_geo`: Gamma `/markets?tag_id=100265` (slug `geopolitics`, pinned; the smoke must resolve the slug to
this id) with `closed=true`, and with `closed=false` for markets already past their scheduled end (censored, counted), in
monthly `end_date` windows over `[2025-06-01, T_fetchG − 7 d]`, a window split into halves while capped (still capped at one
day → excluded and counted). **Stored for every walked market (round 1, item 2):** all tag ids returned for the market and
its event, the event title, `fee_category`, question, slug, ids and keys, `created_at`, `end_at`, `closed_time` (status
field) and outcome labels; outcome prices only in `outcomes_guarded.csv.gz`. The full walked frame (`frame.csv.gz`, before
any filter or cap) is kept: it is the set `h8_text`'s seal drops against (§1.3). The start date is the idea text's "since
2025-06", taken without adjustment. **Disclosed:** the
drafting author knows the major geopolitical events of 2025-26 (for example the June 2025 Israel-Iran strikes); no window,
theme or rule was set around any of them, and the theme clustering and the without-top-5-events robustness bind precisely
because one war can dominate.

**Population (frozen, before any print request). Order (round 1, item 4): (1) the filters below, (2) the exclusion-key
drop, (3) the per-event cap on what remains, (4) origins; seal drops (h8_tail, h7) come after, at seal.**
- Outcome labels `["Yes", "No"]`; life `end_at − created_at ≥ 9 d`; not a neg-risk "Other"/placeholder member; no exclusion
  id or key.
- **Continuous class excluded:** question matches CB6's `class_c` list (`\bprice\w*`, `\btemperature\w*`, `\bscore\w*`,
  `\bpoll\w*`). The idea concerns discrete decisions; within geopolitics nearly every other question is a discrete event.
- **Status-quo questions excluded** (YES = "nothing happens"): question matches `\bnot\b`, `\bremain\w*`, `\bstill\b`,
  `\bstay\w*`, `\bsurviv\w*`, `\bcontinu\w*`, `\bwithout\b`. Counted; G1 including them is reported.
- **Per-event cap (applied after the filters and the key drop):** at most 8 of an event's remaining markets (first
  event id), the first 8 in `sha256("arepo-h8-geo|" + market_id)` order; recorded. Reason: 66 events have ≥ 20 members
  (count probe); they are one cluster each and would consume the request budget without adding independent outcomes.
- Expected size: about 5,050 tagged markets with life ≥ 9 d (count probe), about 4,300 after the filters and key drop,
  about 3,300 after the cap, slightly fewer after seal drops (assumption; census replaces). The draft's MDE text implied
  cap-first; the order above is the declared one.

**Origins and units.** `t_k = end_at − k d`, k ∈ {30, 14, 7}, each kept iff `t_k ≥ created_at + 2 d`. **Prices from Data
API prints, not CLOB history (round 1, new information: CB6's fidelity-60 smoke returned < 50% of hourly points for 16 of
20 worn 2025 markets).** One request per origin, `/trades?market=<cid>&start=t_k − 7 d&end=t_k − 1&takerOnly=true&limit=50`,
exactly as S: eligible iff ≥ 1 print in `[t_k − 7 d, t_k)`; `m` = size-weighted YES-terms VWAP of the prints in
`[t_k − 24 h, t_k)`, else the latest print's YES price; eligible iff `m ∈ [0.02, 0.10]`. If more than 2% of origin
requests fail after retries, G1 is "not testable (source)", counted; otherwise failed origins are excluded and counted.
Disclosed: at longshot prices buyers usually lift the ask, so a print-based `m` sits above the mid, and the modelled ask
`m + half_spread(m)` then double-counts part of the spread. Both push G1 **against** the hypothesis. Outcome Y = YES payout
(1, 0, 0.5) from the guarded file.

**G1 statistic.** `net = Y − a − f(a)` per unit (§2.1); **G1 = mean net**, test > 0. `R_ann` with hold from `t_k` to the
resolution mark (censored excluded; floor `max(d, 1)`).

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **G1** | economic | eligible (market, origin) | mean net per share of buying YES at the modelled ask, held to resolution | > 0 |

**Clustering.** (a) Event × resolution ISO week (neg-risk members and all rungs of one event merged); (b) **theme**:
the first match, in this order, over the lowercased question and event title: `ru-ua` (russia, russian, ukrain\*, putin,
zelensky, kyiv, kremlin, crimea, donbas), `il-ps` (israel\*, gaza, hamas, netanyahu, west bank, hostage\*), `iran`
(iran\*, khamenei, tehran, hormuz), `lb-sy-ye` (hezbollah, lebanon, syria\*, assad, houthi\*, yemen\*), `cn-tw` (china,
chinese, taiwan\*, xi jinping, beijing), `kp` (north korea\*, kim jong), `ve` (venezuela\*, maduro), `in-pk` (india\*,
pakistan\*, kashmir); no match → its own cluster (the event key). p = max over (a) and (b) (small-G rule; G_theme < 15 →
not testable). Theme lists are word-boundary regexes in the rules file; no theme was chosen from outcomes.

**Inverted tail gate (binding; the mirror of CB1's tail gate).** `π` = share of units whose YES wins (50-50 counts as
half); `π* = mean(a + f(a))`. The one-sided **lower** bound on `π` (99%; Wilson on `n/deff` with the design effect from
the event-cluster bootstrap) must exceed `π* + 0.005`. **G1 additionally needs ≥ 10 YES event clusters;** fewer → "not
testable" (p = 1, counted; fewer YES events can never make G1 easier).

**Worst cases and sensitivities (binding).** Censored units → Y = 0. The `closed_time < end_at − 2 d` drop (§2.2), the
measured-spread robustness (§2.1) and the **tag-and-topic subset** (§2.6 (x): tagged and `topic_of(question, event title)
== "geopolitics"`) must each keep G1's sign and p threshold.

**MDE (from the count probe plus assumptions; census replaces).** About 3,200 markets × about 2.3 usable origins × about
23% in band with a recent print ≈ 1,700 units in about 900 markets and about 500 event clusters; mean price about 5.5%, so
`Var(net)` ≈ 0.052; design effect ≈ 2.8 (origins × rungs), theme inflation ≈ 1.3. SE ≈ √(0.052 × 2.8 / 1,700) × 1.3 ≈
1.2c. **MDE ≈ 3.5-4c** at one-sided α = 0.01 (z 2.33 + 0.84), and about 4.3c at the batch-Holm first step (z 2.71).
Reading: a longshot at 5c whose true YES rate is 10% gives net ≈ 5c − 1.8c ≈ 3.2c, so **G1 can detect roughly a doubling
of the YES rate over the price, not less.** The ≥ 10 YES-cluster rule is expected to hold (about 35-40 YES events if
prices are calibrated). **This low power is accepted only because q0143 is cheap** (about 8k requests, 45 minutes, ≤ 0.05
GB, no new code beyond the shared print request); a costlier fetch for this power would not be justified (round 1,
should-fix).

**What would kill CH61.** GG fails; G1 not detected at MDE; the break-even placebo advances; the inverted tail gate fails;
the effect needs the top five events or one theme; the censoring or end-date worst case flips it; it does not hold on the
tag-and-topic subset or at the measured spread.

**Verdict map.** G1 meets the batch Holm and every gate → "geopolitics YES longshots paid at modelled asks on 2025-06 to
2026-10 data (single-stage historical screen, L1)" → Stage P-G registration (months). Otherwise → "not detected at MDE ≈ x".

**Stop rule.** None beyond the verdict: G1 has no Stage-2 job in CB7.

### CB7-X: Kalshi-skewed maker (CH73)

**Question.** When Kalshi's mid has moved by at least 1c over 10 minutes, do Polymarket fills over the next 20 minutes on the
side Kalshi moved toward lose money for the resting maker, after the spread the maker captured (X1)? If so, a maker who
pulls that side for 20 minutes gains on each skipped share.

**Why new / overlap.** `CROSS_VENUE_STUDY.md` found the lead (r ≈ 0.26 at 10-20 min on C1) and called it untakeable for a
taker; nothing has measured the *maker's* side, which needs prints. CB5-K measures hour moderation of the lead on the same
pairs (no prints). CB6/CB3 maker tests do not condition on Kalshi.

**Data.**
- C1 pairs reproduced through `run_cross_venue.load_pair_series(cv.POINT_LAG_S)` and `audit_sets(...)["rule"]`
  (read-only; as CB5-K). Primary: **non-sports pairs** (`k_cat ≠ Sports`, 167 pairs); sports reported.
- **Prints (q0146):** for each of the 316 Polymarket legs, over the pair's study window (up to 30 days before the earlier
  resolution, not before either market opened), one request series per UTC day
  `/trades?market=<cid>&start&end&takerOnly=true&limit=1000&offset` (≤ 10 pages); a day that hits the cap is
  **unavailable** (every print of that day excluded, counted). Stored: pair key, `ts`, side mapped to YES terms
  (`+1` = ask-side: taker BUY YES or SELL NO; `−1` = bid-side), YES price, size. **No wallet field is stored.** About 8k
  requests; ≤ 0.25 GB. All rows predate 2026-09, so the fetch is not `T_seal`-bound (rows are still capped at `T_seal`).

**Definitions (fixed now).**
- **Kalshi mid** at minute end `τ`: from the latest 1-minute candle with `end_ts ≤ τ` and age ≤ 5 min, valid if
  `0 < bid < ask < 1` and spread ≤ 10c (the study's rule), mid in `[0.03, 0.97]`.
- **Move event** at `τ`: `ΔK(τ) = mid(τ) − mid(τ − 600 s) ≥ +0.01` (up) or `≤ −0.01` (down), both mids valid.
- **Skip state** of a print at `s`: up-skip if some up event has `τ + 120 ≤ s < τ + 120 + 1,200` (seconds); down-skip
  likewise. A print in both states is excluded (counted).
- **Sets.** S = ask-side prints in up-skip ∪ bid-side prints in down-skip (the fills the skew rule forgoes). S' = the
  opposite sides in the same states. N = prints in neither state.
- **Mark.** `M(u)` = the latest Polymarket history point (`ps`) with stamp ≤ `u − 600` and ≥ `u − 3,600`; unit
  unavailable if none. Usable print only if both venues' prices are in `[0.03, 0.97]` at `s` (study rule).
- **Maker mark-out per share** at horizon 1 h: ask-side `p − M(s + 3,600)`; bid-side `M(s + 3,600) − p`; plus the forgone
  rebate (§2.1).
- **X1** = mean over S of (mark-out + forgone rebate), unweighted per print. Test X1 < 0.
- **Alternative mark (robustness (i)):** the midpoint of the ask-side and bid-side print VWAPs in `[s + 50 min, s + 70 min]`
  (both sides required; else unavailable for this check).

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **X1** | economic | print in S (non-sports C1; Stage 2: fresh pairs) | mean resting-maker mark-out at 1 h plus forgone rebate (cents per share) | < 0 |

**What the statistic is and is not.** Every print fills some resting order at its price; without books, the maker is "any
resting order at that price", not the touch maker specifically (disclosed). The skipped-fill mark-out already nets the
spread the maker earned, so X1 < 0 is exactly "the skip gains". **Binding route gate:** the mean mark-out over N ∪ S'
(the fills the skewed maker keeps) must be ≥ 0 at the point estimate; otherwise the verdict is "skipping helps, but the
maker still loses: no route".

**Clustering.** Polymarket event and UTC date of the print; p = max (small-G rule).

**Worn-data disclosure.** The 10-20 minute lead, the 10-minute change and the C1 audit were all found on these pairs, so
the conditioning rule is in-sample. Stage 1 is "worn pairs, new prints, L1 at most" and **is a gate for Stage 2, not
evidence** (round 1, should-fix). The Stage-2 read on fresh pairs is the first clean test.
- **Lead-implied X1 (reported with Stage 1).** X1 splits exactly into the spread the maker captured,
  `mean_S(side·(p − M(s)))`, and the price drift against the maker, `mean_S(side·(M(s) − M(s + 3,600)))`. The drift part is
  what the known lead implies (Polymarket moving toward Kalshi after the move); the spread part is new. Both are reported,
  so a reader can see whether X1 adds anything beyond the published lead.

**MDE (assumptions; census replaces).** 167 non-sports pairs, about 20 usable days each, about 150 prints a pair-day,
about 15% of prints in S → about 75k S prints in about 10k skip windows and about 95 events. With between-event spread of
event means ≈ 1.5c, SE ≈ 0.15-0.3c, **MDE ≈ 0.5-1.0c**, near the 0.5c floor.

**Stage 2 (registered only if X1 advanced).**
- q0153 at `T7_X_list`: Kalshi open markets and Polymarket open markets via `cross_venue_live.fetch_kalshi_open` /
  `fetch_poly_open` (code reuse only), the frozen matcher `cross_venue.match_markets` with `AUDIT_CONFLICT` and
  `live_conflict` (`LIVE_EXTRA_CONFLICT`), keeping pairs whose earlier scheduled resolution is ≥ `T7_X_rep_start` + 2 d.
  Output: titles, tickers and ids only. A `science-reviewer` title-level audit (no prices) drops mismatches (inversions,
  before vs on, AND vs single, template differences), and the coordinator commits `seals/cb7_xv_pairs.json` (hash) with
  `T7_X_rep_start`. Sports pairs listed but reported only.
- q0154 at `T7_X_rep_end` + 2 h: Kalshi 1-minute candles (`fetch_k_candles`), Polymarket fidelity-10 history and daily
  print pages for `[T7_X_rep_start, T7_X_rep_end)`.
- X1-rep: identical definitions, lag, window, mark, sets, clustering and gates.
- **History-density rule for the mark (declared now, after CB6's history smoke failure).** A pair-day whose Polymarket
  fidelity-10 history has < 50% of the expected points is unavailable (all its prints excluded, counted). If more than 30%
  of pair-days are unavailable, X1-rep is "not testable (source)", counted. The alternative mark (two-sided print midpoint)
  stays a robustness check, never a substitute.

**What would kill CH73.** GX fails; X1 not detected; the time-shift placebo advances; the effect needs the top five events;
the 300-s latency or the alternative mark removes it; X1-rep fails out of time.

**Verdict map.** X1 and X1-rep pass with the wrong-side attribution and the route gate → "a 20-minute Kalshi-skewed step-aside
avoided adverse fills out of time (L2)" → Stage P-X. Attribution fails → "a pause rule, not a skew". Route gate fails →
"protective only, not a route". X1 not detected → CH73 closed at MDE.

**Stop rule.** X1 not advanced → q0153-q0155 are not committed.

### CB7-F: Data jobs

- **Smoke (q0140, counts only, before q0142/q0143 are committed; round 1: no CLOB history anywhere in CB7's
  `T_seal`-bound fetches, after CB6's fidelity-60 smoke failed on 2026-10-17).** Worn smoke markets: 200 candidates drawn
  (seed `arepo-cb7-smoke`) from the h1/h2/h3 exclusion ids, looked up on Gamma by id (≤ 4 requests; parse guard keeps
  `end_at` and `volumeNum` only), keeping those with `end_at` in 2025 and lifetime volume ≥ $10,000; the first 20 in seed
  order are used. Criteria, all fixed before any smoke run:
  - (a) slug `geopolitics` resolves to the pinned id 100265;
  - (b) one `/trades?market&start=end_at − 14 d&end=end_at − 7 d − 1&takerOnly=true&limit=50` request per smoke
    market: **every** returned row satisfies `start ≤ ts ≤ end` and rows are newest-first, over **≥ 10 non-empty**
    responses;
  - (c) **coverage:** ≥ 14 of the 20 return ≥ 1 print. A priori these are markets with ≥ $10k lifetime volume one week
    before their end, so most should trade in a 7-day window; 14/20 tolerates thin or front-loaded markets.
  - Writes `creative_batch7/smoke.json` (counts only, under the rules hash). **On FAIL** of (a), q0143 is not committed;
    of (b) or (c), neither q0142 nor q0143 is committed. A source change is a design change needing review; the deadline
    is not moved, and a fetch not complete before `T_seal` is `not_run_deadline` (S1 and/or G1 "not run", counted).
- **Exclusion keys (q0141).** As CB6 q0120 stage 1 (Gamma lookup by id, ≤ 50 ids per request, `closed=true` retry, parse
  guard ids/keys only). Writes `creative_batch7/exclusion_keys.csv.gz` and `exclusion_report.json`; both fetches pin its
  sha256 in their manifests.
- **`h8_text` fetch (q0142)** and **`h8_geo` fetch (q0143)**: §CB7-S and §CB7-G. Stage order: rules and pins check,
  exclusion-key file check, frame walk (resumable by day or window), filters, key drop, sample (text) or cap (geo), text
  features and cut points (text) or origins (geo) written before any print or price request, then prints / prices,
  resumable by market. Raw wallet addresses never touched (none stored). Rows capped at `min(T_fetch, T_seal)`.
- **Seals (q0144, q0145).** Listing sha256, per-file sha256, request clocks, drop blocks (§1.3), read location, git commit;
  `history_seal_declaration` trial line; `ACCESS_LOG.jsonl`. The coordinator commits the seal copies before q0147.
- **C1 prints (q0146)**, **`textorig` pass step (§5.3)**, **text rolling fetch (q0151)**, **pair list and Stage-2 fetch
  (q0153, q0154)**: as above.

---

## 4. Jobs

Draft specs, one file each, in `docs/research_lab/queue/drafts/` (fields as `queue/README.md`; `argv[0]` under
`backend/scripts/`, `cwd` `backend`). **None is committed to `queue/jobs/`** before its code and tests exist and pass a
`science-reviewer` freeze check; analysis jobs also need the CB7 freeze. q0140-q0143 need only the fetcher freeze check,
the committed rules file and (for q0142/q0143) a q0140 PASS; they may be queued before the CB7 freeze. Each data-job
commit records the data-dumps headroom (§2.8).

| Id | File | Lane | Priority | Size / time | Depends on | Commit when |
|---|---|---|---|---|---|---|
| q0140 | `q0140_cb7_smoke.json` | net | 62 | ~30 req, < 5 min | - | rules file committed, smoke code reviewed |
| q0141 | `q0141_cb7_exclusion_keys.json` | net | 61 | ~850 req, ~6 min, ≤ 0.01 GB | q0140 | with q0140 |
| q0142 | `q0142_h8_text_fetch.json` | net | 61 | ~27k req, ~2.4 h wall (85-min chunks, repeat ≤ 6), ≤ 0.15 GB | q0140, q0141 | fetcher freeze check + smoke PASS; **must finish before `T_seal`** |
| q0143 | `q0143_h8_geo_fetch.json` | net | 61 | ~8k req, ~45 min wall (repeat ≤ 4), ≤ 0.05 GB | q0140, q0141 | as q0142 |
| q0144 | `q0144_h8_text_seal.json` | cpu | 58 | light; ≤ 2 rps key lookups | q0142, q0143 | after `T_seal` and the h8_tail / h7 seal copies (or their `not_run_deadline` records) |
| q0145 | `q0145_h8_geo_seal.json` | cpu | 58 | light | q0143 | as q0144 |
| q0146 | `q0146_cb7_xv_prints_fetch.json` | net | 45 | ~8k req, ~40 min, ≤ 0.25 GB | - | after `T_seal` |
| q0147 | `q0147_cb7_census.json` | cpu | 40 | ≤ 1.2 GB RAM | q0144, q0145, q0146 | after the seal copies are committed |
| q0148 | `q0148_cb7_screen_S.json` | cpu | 38 | ≤ 1.2 GB | q0147, q0156 | after the CB7 freeze and the committed q0156 audit result |
| q0149 | `q0149_cb7_screen_G.json` | cpu | 38 | ≤ 0.8 GB | q0147 | after the CB7 freeze |
| q0150 | `q0150_cb7_screen_X.json` | cpu | 38 | ≤ 1.5 GB | q0147 | after the CB7 freeze |
| q0151 | `q0151_cb7_text_rep_fetch.json` | cpu | 41 | ≤ 15k req over ~6 weeks at 2 rps (rolling every 6 h), ≤ 0.03 GB | - | at the freeze, with the `textorig` pass step |
| q0152 | `q0152_cb7_rep_S.json` | cpu | 38 | ≤ 1.2 GB | q0151, q0148 | only if S1 advanced; refuses before `T7_S_out` |
| q0153 | `q0153_cb7_xv_pairlist.json` | net | 44 | ~6-9k req, ~1 h at 2 rps | q0150 | only if X1 advanced; at `T7_X_list` |
| q0154 | `q0154_cb7_xv_rep_fetch.json` | net | 41 | ~5k req, ≤ 0.10 GB | q0153 | after the pair list is committed; refuses before `T7_X_rep_end` + 2 h |
| q0155 | `q0155_cb7_rep_X.json` | cpu | 38 | ≤ 1.5 GB | q0154 | with q0154 |
| q0156 | `q0156_cb7_text_edit_audit.json` | cpu | 39 | ~200-600 Polygon RPC + ~4 Gamma req at ≤ 2 rps, ≤ 0.01 GB | q0144 | after the CB7 freeze; result committed before q0148 |

## 5. Code needed (not written by this document)

### 5.1 Modules

- `backend/astrolabe/research_lab/cb7_text.py` (CH63 and the `h8_text` fetch)
  - `RULES` (loaded from and hashed against `seals/cb7_text_geo_rules.json`), `markers(question, description)` → M1-M7,
    `condition_count(...)`, `has_clarification(description)` (CB6 strings), `cut_points(frame_C_by_topic)`.
  - Fetch side: `text_fetch(...)` built on `cb6_tail`/`history_backfill` primitives (random-window frame with description,
    streaming partial file, key drop, `draw_sample_cb1`-style stratified sampler with sports weight 0.25, deadline,
    exit-75 headroom, resumable chunks), `t7_prints(cid, t7)` (one request), `t7_price(prints, t7)` (24-h VWAP else
    latest, YES mapping), `text_seal(...)` (drop blocks vs h8_tail, h7, h8_geo).
  - Analysis: `s1_units(...)`, `s1_beta(units)` (cell FE OLS), `s1_test(units, ways)` (small-G),
    `calibrated_null(...)` (reuse CB6's per-event draw), `marker_shuffle(...)`, `censor_worst_case(...)`,
    `staleness_check(...)`, `sign_by_month(...)`, `tercile_table(...)`, `s2_net(units, fee)` (recorded NO ask,
    conservative fee), `breakeven_s2(...)`.
- `backend/astrolabe/research_lab/cb7_geo.py` (CH61 and the `h8_geo` fetch)
  - `geo_walk(tag_id, months)` (split while capped), `geo_filters(...)` (labels, life, `class_c`, status-quo, Other,
    keys), `event_cap(frame, 8, seed)`, `geo_origins(created_at, end_at)`, `theme_of(question, event_title)`.
  - Fetch side: `geo_fetch(...)` (stores all tag ids, event title, `fee_category`, `closed_time`; filters → key drop →
    cap → origins; one windowed print request per origin via the shared `origin_prints` helper; no CLOB history),
    `geo_seal(...)`.
  - Analysis: `g1_units`, `g1_net(units, fee_rule)`, `inverted_tail_gate(...)` (Wilson on n/deff; ≥ 10 YES clusters),
    `breakeven_g1(...)`, `end_date_sensitivity(...)`, `theme_tables(...)`.
- `backend/astrolabe/research_lab/cb7_xv.py` (CH73)
  - `load_c1_pairs()` (imports `run_cross_venue.load_pair_series`, `audit_sets`; read-only), `kalshi_moves(kc, thr,
    lookback, max_age, spread_max)`, `skip_state(ts, events, lag, window)`, `map_side(print)`, `markout(prints, ps, h)`,
    `alt_mark(...)`, `x1_test(...)`, `time_shift_placebo(...)`, `wrong_side(...)`, `route_gate(...)`.
  - Fetch side: `pair_prints_fetch(pairs, day_pages=10)` (capped day → unavailable), `build_pair_list(...)` (calls
    `cross_venue.match_markets`, `audit_conflict`, `cross_venue_live.live_conflict`, `fetch_kalshi_open`,
    `fetch_poly_open`; **never** `load_verified` or any `cross_venue_live/` path), `rep_fetch(...)` (`fetch_k_candles`,
    `history_backfill.fetch_prices` at fidelity 10, daily print pages).
- `backend/astrolabe/research_lab/cb7_declaration.py`: `HYPOTHESES_CB7`, `declaration_sha256()` over every population,
  window, regex, marker, cut rule, theme map, threshold, floor, gate, lag, horizon, seed, date and the source of every
  rule function and UPPER_CASE constant read at call time (as CB5/CB6).
- Shared statistics **imported, not copied**: CB1 `tail_bound` and cluster p / bootstrap / small-G helpers, CB6's
  per-event calibrated-null draw, `cb1_history.half_spread`, `economics.DOCS_CATEGORY_RATE` / `REBATE_SHARE`,
  `history_topics.topic_of`, `history_backfill.cb1_topic` / `CB1_UPDOWN_RE`, `cb2_weather.TEMP_RE`, census guard,
  `provenance.append_trial`.

### 5.2 Runner

`backend/scripts/run_cb7.py {rules,smoke,exclusion-keys,text-fetch,geo-fetch,text-seal,geo-seal,xv-prints,census,
text-edit-audit,screen,text-rep-fetch,replicate,xv-pairlist,xv-rep-fetch,verify-seal} --family S|G|X`.
- Refuses the run ids and roots of §1.3; writes only under `research_lab/creative_batch7/`, `research_lab/cb7_extract/`,
  `history/h8_text/` and `history/h8_geo/` (fetch and seal only).
- `text-fetch` / `geo-fetch` refuse unless the rules hash matches, every exclusion file matches its pin, the exclusion-key
  file exists, `smoke.json` records PASS under the same rules hash, the clock is before `T_seal`; exit 75 on headroom;
  no Mac or standalone mode (round 1, item 6).
- Declaration-hash guard on `census`, `screen`, `replicate`. `replicate --family S` refuses before `T7_S_out` or
  without a committed Stage-1 S results file with S1 advanced; `replicate --family X` refuses before `T7_X_rep_end` + 2 h
  or without the committed pair list. Every counting command runs the `trials.jsonl` union first and records the
  post-union count. Results are never overwritten.

### 5.3 Extractor addition (`creative_batch1.py`, version `cb1-extract-v6`) and pass hook

- Table `cb7_extract/textorig/<capture_id>.csv.gz` (§CB7-S Stage 2 columns), own root and manifest; CB1-CB6 tables
  byte-identical (test).
- Pass hook `run_cb7.py textorig --pass <capture_id>` added to `arepo_pass.sh` after the extractor: Gamma `description`
  lookup by id for that capture's rows (≤ 3 requests), budget 60 s, failure isolated (never affects the pass), rows
  without a description marked unavailable. Deployed at the freeze; no backfill (Stage-2 origins start at
  `T7_S_rep_start`).

### 5.4 Tests (`backend/tests/unit/test_cb7_text.py`, `test_cb7_geo.py`, `test_cb7_xv.py`)

- **Text.** Each marker regex on fixtures (M6 case-sensitive: "ET" yes, "et" no; M4 read on the question only); C counts
  types, not occurrences; clarification strings identical to CB6's rules file; cut points from text only and stable under
  a planted price or outcome change; the price uses only prints with `ts < t7` (a planted print at `t7` is ignored),
  24-h VWAP else latest, YES mapping of NO prints; band edges; cell FE slope recovers a planted slope and gives none on
  a null fixture; the calibrated-null placebo advances about 1% on a no-effect fixture with heavy within-series repetition
  and far more when clustering is wrongly set to the unit; the marker shuffle reproduces β on a length-only fixture
  (attribution fails) and not on a marker fixture; censoring worst case binding; sampling uses no price, volume or
  outcome; geopolitics excluded before sampling; key drops before sampling; > 2% unverified → not testable; fetch refuses
  after `T_seal`, writes `not_run_deadline`, exits 75 above the headroom; outcomes only in the guarded file; seal drops
  by key as well as id.
- **Geo.** Tag-walk window split while capped; status-quo and continuous regexes on fixtures; Other placeholders
  excluded; the per-event cap is seeded by market id only; origins `end − {30, 14, 7} d` with the 2-day listing rule;
  the usable-point rule (9 minutes no, 10 yes; > 2 h old no) also enforces "open"; print checks only for in-band origins;
  theme order on multi-theme fixtures; inverted tail gate (lower bound, ≥ 10 YES clusters, 50-50 as half); break-even
  placebo calibrated; end-date sensitivity drops by `closed_time` only in that sensitivity.
- **XV.** Kalshi validity (spread > 10c invalid, > 5 min old invalid); move events at ±1c over 600 s; skip windows
  `[τ + 120, τ + 1,320)` merged; side mapping (SELL NO = ask-side at `1 − q`); mark uses only points stamped ≤ `u − 600`;
  capped day → all its prints unavailable; time-shift offsets inside `[6 h, W − 6 h]`; on a fixture where Polymarket
  follows Kalshi, S marks out negative and S' positive; on a fixture with symmetric adverse news windows the wrong-side
  attribution fails; no wallet column is written; `build_pair_list` never opens `cross_venue_live/` (path guard test).
- **Runner.** Refusals (run ids, roots, rules hash, pins, smoke, deadline, freeze, Stage-1 file, dates); `KIND_RULES` has
  the CB7 kinds and the counter runs on the real `trials.jsonl`.

## 6. Test budget and compute

| Job | Tests counted | Kind(s) | Family / decision |
|---|---|---|---|
| Stage 1: S1 (h8_text), X1 (C1) | 2 | `cb7_test` + count lines `creative_batch_7:S` (1), `:X` (1) | each p < 0.01; batch-Holm label (α 0.01, k1 3); BY triage |
| G1 (h8_geo, single historical stage) | 1 | `cb7_test` + `creative_batch_7:G` (1) | must meet the Stage-1 batch Holm (α 0.01, k1 3) for Stage P |
| Stage 2: S1-rep, S2, X1-rep (registered only) | ≤ 3 | `cb7_replication` + count lines | one Holm, one-sided α = 0.05, k ≤ 3 |
| Census, gates, tables, strata, variants | 0 | `cb7_descriptive` | - |
| **Total** | **3 fixed + ≤ 3 conditional = 3-6** | | cumulative ≥ 1,121 at drafting → ≥ 1,124-1,127 |

**Host compute.** About 2-3 CPU-hours at nice 19 in total. Peak RAM 1.5 GB (X screen). **Network:** before `T_seal`
about 36k requests (about 3.2 h wall on `net`); after `T_seal` about 8k (C1 prints), ≤ 15k rolling over six weeks
(Stage 2 S), about 11-14k for the fresh pairs. **Disk:** ≤ 0.61 GB across all CB7 outputs.

## 7. Main scientific risks

1. **Calendar (S, G).** Both fetches must finish before `T_seal` on a congested lane and under a data-dumps guard, and
   first the fetch code must pass its freeze check. There is no fallback host; a miss is "not run (deadline)", counted.
   A smoke FAIL on print coverage stops both fetches (CB6's CLOB-history smoke already failed on 2026-10-17).
2. **Power (S, G).** Stage-1 S1 detects about ≥ 2.5c per marker (about 5-6c across terciles; census replaces); S2 about
   3c per share; G1 only about a doubling of the YES rate. Nulls are "not detected at MDE".
3. **Current text (S Stage 1).** Descriptions are current; clarification-marked markets are excluded and unmarked
   post-event edits remain possible. Direction of the remaining bias is unknown (an edit after a surprise can add or remove
   conditions). Stage 2 stores text at the origin.
4. **Print-based prices (S).** Last prints can be stale or sit on one side of the spread; (vi) binds. Templates may make C
   a proxy for market type within a topic; series clustering and the marker shuffle address this, not fully.
5. **Scheduled-end look-ahead (G).** A rewritten `endDate` would favour G1; the census counts and the binding end-date
   sensitivity guard it.
6. **Concentration (G).** One theme can hold most YES outcomes; theme clustering, the small-G rule, the without-top-5
   robustness and the calibrated break-even placebo bind.
7. **Worn pairs and fill realism (X).** The lead was found on C1; Stage 1 is L1 and only the fresh-pair Stage 2 counts as
   evidence. Prints identify fills but not queue position or whether a touch maker was filled; the mark is a history point
   with a timestamp-convention ambiguity of about 10 minutes (immaterial at 1 h, checked by the alternative mark).
8. **Matcher error (X Stage 2).** The live matcher mis-paired 56 of 167 pairs in October; the title audit before any price
   read is mandatory, and residual errors (2-4% historically) dilute X1-rep toward zero, never toward the hypothesis.
9. **Shared calendar (S Stage 2).** E011 and CB3-CB6 live windows overlap; CB7 never opens their files.

## 8. Next actions

1. **Challenger review: done** (round 1, §9; one challenge, one response, no second round). The open questions put to
   the challenger were:
   - S1 as a single historical stage plus an out-of-time prospective Stage 2, instead of a same-calendar SCREEN/HOLDOUT
     split (power argument in §CB7-S): acceptable?
   - The slope primary instead of the idea's tercile contrast; the two declared marker deviations (M4 on the question,
     M5 synonyms): acceptable?
   - Print-based `t7` prices (one request per market) instead of hourly history plus a separate print check: acceptable
     given the staleness robustness?
   - G1 gated by the Stage-1 batch Holm in lieu of a replication; the 8-per-event cap chosen after the count probe; the
     status-quo regex: acceptable?
   - X1's skipped-fill mark-out as the economic statistic, with the route gate on kept fills: is anything missing that
     would let X1 pass when the skew rule does not pay?
2. **Implementer, now (`T_seal`-bound; exactly what q0140-q0143 need, nothing else):**
   - `seals/cb7_text_geo_rules.json`, generated by `run_cb7.py rules` (rules_sha256 + source hash of every rule function;
     exclusion pins identical to CB6's; tag slug/id 100265; seeds; windows; M1-M7; CB6 clarification strings and note
     pattern; `class_c`; status-quo list; theme map; bands; cut rule; cap 8 and its seed; smoke criteria);
   - `cb7_common.py` (or functions in `cb7_text.py`): `origin_prints(cid, t)` (one `/trades` request, `start = t − 7 d`,
     `end = t − 1`, `takerOnly=true`, `limit=50`, YES-terms mapping, no wallet kept) and `origin_price(prints, t)` (24-h
     VWAP else latest; eligibility flag);
   - `run_cb7.py smoke` (§CB7-F (a)-(c), Gamma id lookup for the 200 candidates, counts-only `smoke.json`);
   - `run_cb7.py exclusion-keys` (reuse `cb6_tail.exclusion_keys`; own output path);
   - `run_cb7.py text-fetch` = `cb7_text.text_fetch`: random-window closed and ended-unclosed walks (5 × 15 min a day),
     filters, key drop, stratified sample, **M1-M7 and the clarification flag on the full description in memory**, full
     length and sha256, 4,000-char stored copy, `text_features.csv.gz` and `cut_points.json` before any print request,
     then one `origin_prints` per market at `t7`; guarded outcomes; cap, deadline, exit 75, resumable 85-min chunks;
   - `run_cb7.py geo-fetch` = `cb7_geo.geo_fetch`: tag walk with window splitting, full walked frame kept (all tag ids,
     event title, `fee_category`, `closed_time`), filters → key drop → cap 8 → origins, one `origin_prints` per origin;
     guarded outcomes; cap, deadline, exit 75, resumable;
   - fetch-side tests of §5.4 (markers on text beyond 4,000 characters; length/sha stored; filter → key drop → cap order;
     tags/event title stored; no CLOB-history call in either fetch; deadline; exit 75; no wallet column; outcome guard).
   Reuse `cb6_tail.py` / `history_backfill` primitives rather than copying. Seals (q0144/q0145) can wait until after
   `T_seal`.
3. **Freeze check (fetchers only).** `science-reviewer` checks that code and the rules file against §1.3-§1.4, §CB7-S,
   §CB7-G and §CB7-F; run the smoke. Then commit the rules file and copy q0140-q0143 to `queue/jobs/` (headroom recorded)
   and deploy. No Mac fallback: a fetch not complete before `T_seal` is recorded `not_run_deadline`.
4. **After `T_seal`.** Commit q0144/q0145 once the h8_tail and h7 seal copies (or not-run records) are committed; q0146;
   then implementer for the analysis code (S, G, X screens, `textorig` pass step, Stage-2 fetchers); q0147 census; insert
   counts and gates here; `science-reviewer` freeze check; freeze (`model_specs/cb7_v1.json`); pin `T7_S_rep_start`;
   deploy the `textorig` pass step and q0151; run q0156 (text-edit audit) and commit its result.
5. **After the freeze.** q0148-q0150. Commit q0152 only if S1 advanced; q0153-q0155 only if X1 advanced. G1: Stage P-G
   registration only if it met the batch Holm and every gate.

## 9. Challenger round 1 and response (2026-10-17)

One `science-reviewer` pass on the committed draft `09b2bfc`: **ACCEPT_WITH_REQUIRED_CHANGES**. This is the single
response round; then proceed. Every change tightens or discloses; no threshold, floor or gate was relaxed. The
coordinator also reported that **CB6's `h8_tail` smoke failed on 2026-10-17** (CLOB `prices-history` at fidelity 60 over a
10-day window returned < 50% of expected hourly points for 16 of 20 worn 2025 markets); CB7 responds in item N.

### 9.1 Required changes

| # | Finding | Resolution | Where |
|---|---|---|---|
| 1 | Markers and clarification flag were computed on the stored first 4,000 characters (fetch-blocking) | M1-M7 and the clarification rule run on the **full** description in memory before truncation; full length and sha256 stored per market; census reports the share longer than 4,000 characters | §CB7-S data and text features, §2.7, q0142 |
| 2 | Geopolitics tag may sweep in non-geopolitical markets; tags and event titles not stored (fetch-blocking) | Every tag id, event title and `fee_category` stored for the whole walked frame; **binding** sensitivity (x): G1 must hold on markets both tagged and `topic_of(question, event title) == "geopolitics"`; census reports the tag-only share | §CB7-G data and worst cases, §2.6 (x), §2.7, q0143 |
| 3 | "A resolved market fails these conditions" was false for S (resolved at `t7 − 3 d` still has prints in the window) | Claim withdrawn; `closed_time` kept in both frames as a status field; census counts units with `closed_time < t`; S1 gets the same binding drop sensitivity as G1 (`closed_time < end_at − 2 d`), robustness (vii) | §2.2, §2.6 (vii), §2.7 |
| 4 | Order of the per-event cap and filters unstated; `h8_text`'s seal drop set unstated | Declared order: filters → key drop → cap 8 → origins; seal drops after. `h8_text`'s seal drops use the **full `h8_geo` tag frame as walked, before any filter or cap**. Expected-size text corrected | §CB7-G population, §1.3, q0143, q0144 |
| 5 | Two fee rules for G1 depending on whether a cost register exists when q0149 runs | One rule fixed now: `economics.DOCS_CATEGORY_RATE` under CB1's conservative policy (geopolitics 0.0, `economics.py:41`; unknown 0.07), no register read. Added **binding** spread robustness (ix) with `h_geo`, the median half-spread of geopolitics markets with YES mid in [0.02, 0.10] in complete captures `[2026-10-22, 2026-10-25)` (census; spreads only, no outcomes) | §2.1, §2.6 (ix), §2.7, q0147, q0149 |
| 6 | Mac fallback breaches the data-location and memory-heavy-job rules (no Mac background jobs; Mac data-dumps retired) | **Removed** everywhere (dates, §2.8, runner, specs, next actions). A fetch not complete before `T_seal` is recorded `not_run_deadline`, counted. Fetch priorities kept at the top band (q0140 62, q0141-q0143 61; q0143 raised from 60), and the code + freeze-check schedule is named as the real risk | §1.2, §2.8, §5.2, §7, §8, q0142, q0143 |
| 7 | S2 had no MDE | Declared: high-C group ≈ one third of Stage-2 units ≈ 5,000, SD ≈ 0.42, deff ≈ 3 → **S2 MDE ≈ 3.3c per share** at the first Holm step (about 3.0c at the last), against a 1.0c floor | §CB7-S MDE |
| N | CB6's CLOB fidelity-60 smoke failed | **No CLOB history in any CB7 `T_seal`-bound fetch.** `h8_geo` now prices origins from the same single Data API print request as `h8_text` (8k instead of 12k requests); the disclosed bias of print-based longshot prices runs against G1. The smoke's history criterion is replaced by an a-priori print criterion (bounds and ordering on ≥ 10 non-empty responses; coverage ≥ 14 of 20 worn markets with ≥ $10k volume) with stated FAIL consequences. Stage-2 X, which uses fidelity-10 history for fresh live pairs after `T_seal`, gets a declared density rule (< 50% points → pair-day unavailable; > 30% unavailable → not testable) | §CB7-G origins, §CB7-F smoke, §CB7-X Stage 2, q0140, q0143, q0154 |

### 9.2 Should-changes

| Finding | Resolution |
|---|---|
| S1 design effect 1.5 is optimistic for templated text | Working deff 3 → **Stage-1 S1 MDE ≈ 2.5c per marker** (was 1.8c); Stage-2 S1 MDE ≈ 1.5c (was 1.0c). The census computes a text-only upper-bound `deff_S = 1 + (m̄ − 1)·ρ_C` and the MDE from it (§2.7) |
| X1 Stage 1 on worn pairs is not evidence | Labelled a **gate for Stage 2**; the lead-implied part of X1 (drift) is reported next to the spread part (§CB7-X) |
| G1's low power | Stated as accepted only because q0143 is cheap (§CB7-G MDE) |
| Current-text risk for S needs a check | **Text-stability gate declared now** (§CB7-S; q0156 draft, code later): C on the UMA initialization `ancillaryData` vs C on the current description for 200 seeded units; one-sided 95% Wilson upper bound of the C-changed share ≤ 0.10, else S1 cannot advance; > 20% unretrievable → unverified → cannot advance. Descriptive, not counted; robustness (xi) |
| `h1_first` missing from the runner refusal list | Added (§1.3); only its pinned `sample.csv.gz` id list is read |

### 9.3 Effect on counts and power

k is unchanged: **3 fixed (S1, G1, X1) + up to 3 conditional (S1-rep, S2, X1-rep) = 3-6**; the audit q0156 is
descriptive. MDEs: S1 Stage 1 ≈ 2.5c per marker (was 1.8c), S1 Stage 2 ≈ 1.5c (was 1.0c), S2 ≈ 3.3c (new), G1 ≈ 3.5-4c
(unchanged; prices now print-based), X1 unchanged. Pre-`T_seal` network ≈ 36k requests, ≈ 3.2 h wall (was 40k, 3.7 h).

## 10. Implementation notes (fetch side, 2026-10-17)

Fetch side only (§8 step 2); no analysis, screen, census or `textorig` code exists yet. Nothing was run against the network:
all tests use a fake Gamma/Data API.

**Code.** `backend/astrolabe/research_lab/cb7_common.py` (rules file, `origin_prints`, `origin_price`, smoke, exclusion keys,
resumable chunk machinery on `cb4_data.FetchRun`), `cb7_text.py` (`text_fetch`), `cb7_geo.py` (`geo_fetch`), `cb7_seal.py`
(`seal_cb7`, `verify_cb7`), `backend/scripts/run_cb7.py` (`rules`, `smoke`, `exclusion-keys`, `text-fetch`, `geo-fetch`,
`text-seal`, `geo-seal`, `verify-seal`), tests `backend/tests/unit/test_cb7_fetch.py`. Queue drafts q0140-q0145 now carry the
real argv (checked against the parser and the declaration by a test), lane `net` for q0140-q0143, repeat blocks whose regexes
cover the complete, `not_run_deadline`, `disjointness_unverified`/`source_unverified` and `disk_budget` end states.

**Rules file.** `docs/research_lab/seals/cb7_text_geo_rules.json`, `rules_sha256` =
`28347c13c5e3f62955f9d69da7846cea7629b5877ada63dc5c357e00e55b9583` (`funcs_sha256` `eb2ec6d0...`, plus a per-function source
hash for each of the 29 rule functions). It holds seeds, windows, strata and weights, the pins (identical to CB6's, asserted by
a test), M1-M7 and the clarification strings, `class_c`, the status-quo list, the theme map, bands, the cut rule, the cap, the
smoke criteria and the disk caps. Generated once, in its own commit after the code commit; `verify_rules(require_committed=True)`
passes. Editing any hashed function after this point invalidates the file (a rules file is never rewritten).

**Behaviour as built.**
- Every fetch refuses (exit 2) before any request on: rules hash, a missing or changed pinned exclusion file (all five, including
  `h1_first`), smoke criteria not met under the same rules hash (text needs (b) and (c); geo needs (a), (b) and (c)), a missing
  exclusion-key file or one that does not match its report hash, a refused run id or root, a changed declared argument.
  Exit 75 only for data-dumps headroom (`--data-dumps-cap-gb` default 12.5) or seal sources not yet terminal. A full output cap is
  `disk_budget`, exit 4, sticky.
- `smoke.json` is write-once (exclusive create; exit 2 if present). It holds counts only.
- Every stored row is capped at `min(T_fetch, T_seal)`: prints after the cap are dropped and counted; a market closing after the
  cap is stored as active with blank `closed_time`, `closed_after_cap = 1` and blank guarded outcome. No chunk starts at or after
  `T_seal`; a chunk that reaches it writes `NOT_RUN_DEADLINE.json`.
- Failed print requests raise, are retried with back-off (6 retries, then up to 3 chunk-level attempts) and are counted as
  `print_request_failed`, never as `no_print`. Geo: more than 2% failed origins gives `source_unverified`.
- Memory: the frame walk writes one gzip member per day (text) or month (geo); filters stream; only ids per stratum and the sampled
  rows (pass 2) are held. Prints are appended to a partial member file, converted at completion.

**Deviations and implementation choices (for the freeze check).**
1. *Status-quo variant.* §CB7-G says status-quo questions are excluded and "G1 including them is reported". As built they are removed
   at the fetch (counted in `frame_report.json`), so no prints exist for them and that report cannot be produced from `h8_geo`. **Decision (freeze check): not produced; counts only.**
   Decision for the reviewer: accept (report only the counts) or add a flagged status-quo stratum to the fetch before the rules file
   is used (it would change the rules hash).
2. *Neg-risk "Other"/placeholder rule* is not spelled out in the design. Built as: Gamma `negRiskOther` true, or a neg-risk market
   whose `groupItemTitle` is `other` or `<person|candidate|option|team|player|party|company|country> <letter>`.
3. *Latest print tie rule:* when no print lies in `[t - 24 h, t)`, `m` is the size-weighted price of the prints at the latest timestamp.
   `vwap_truncated` marks a 24-h VWAP built from a full 50-row page that does not reach back 24 h.
4. *Smoke pool:* if fewer than 20 worn markets qualify, (b) and (c) fail. Gamma id lookups use up to 8 requests (closed first, then
   open) rather than 4; the condition id comes from Gamma, not from the sample files. The tag check calls `GET /tags/slug/geopolitics`
   (Gamma, `id` must equal 100265); that endpoint shape has not been exercised yet, so a shape mismatch would FAIL (a) and block q0143.
5. *Frame columns:* `frame.csv.gz` carries the features, `desc_len`, `desc_sha256`, all tag ids, event title, `fee_category` and
   `closed_time`, but not the description text; the 4,000-character copy is in `sample.csv.gz`. M1-M7, C and the clarification flag are
   computed on the full question and description at walk time, before truncation.
6. *Per-event cap* uses the first event id (the market id when none); `capped.csv.gz` lists what the cap removed.
7. *Seal:* `seal_cb7` re-hashes every fetched file against `manifest.json` (refuses on a missing, extra or changed file), then writes
   `drops.csv.gz` with `DROPPED_SEALED_RUNS` (id or key match against the h8_tail and h7 seal copies, Gamma key lookup at <= 2 rps) and,
   for `h8_text`, `DROPPED_GEO_FRAME` (id or key match against the full `h8_geo/frame.csv.gz`). It does not read `h8_geo` outcomes.

**Open items for the freeze check.**
- Run q0140 first; its three criteria decide which fetches may be committed. Check the tag endpoint response in the smoke log.
- Confirm the host data-dumps headroom at commit time and record it in the q0141-q0143 commit messages (§2.8).
- Output cap 0.15 GB for `h8_text`: `frame.csv.gz`, `frame_partial.jsonl.gz` and `sample.csv.gz` (4,000-character text) coexist while the
  frame outputs are built; CB6's analogous cap needed raising once. `disk_budget` is the declared end state if it is too tight.
- Item 1 and item 2 above need a reviewer decision before the rules file is relied on.
- The `net` lane order before `T_seal` (q0043, h7, q0120) is unchanged; q0140-q0143 priorities are 62/61/61/61 as declared.

**Freeze-check fixes (2026-10-17, GO_WITH_CONDITIONS; rules hash unchanged, `verify_rules(require_committed=True)` re-checked).**
- Fix 1: a geo failure never blocks the `h8_text` seal. q0144 no longer depends on q0143; `geo_frame_state` treats a not-run, unverified, `disk_budget` or `source_unverified` `h8_geo`, or a smoke result with criterion (a) false (q0143 refused), as terminal with no frame; the seal still exits 75 while the geo frame is genuinely pending.
- Fix 2: a network failure in the smoke (tag, Gamma or trades request failing after retries, or a non-200 reply from Gamma or trades) writes nothing and exits 75, so the write-once `smoke.json` can only record a real answer.
- Minor 3: `vwap_truncated` (in hashed `origin_price`) is 1 whenever a full 50-row page does not reach back 24 h of the window; it is true for any full page whose oldest print is inside the 7-day window, so analysis must recompute it from `origin_prints.csv.gz`. The hashed code is unchanged.
- Minor 4: only the FIRST event's title is stored (`event_title`); tag ids are stored for all events (`event_tag_ids`), so challenger change 2 is met for tags and the first event's title only.
- Minor 5: the seal's extra-file check ignores `drops*`, so a seal re-run after a crash does not refuse.
- Live check: `GET https://gamma-api.polymarket.com/tags/slug/geopolitics` returned `{"id":"100265","label":"Geopolitics","slug":"geopolitics",...}` at 2026-10-17 ~05:50Z, matching criterion (a)'s parse.

### Smoke v2 (2026-10-17)

**Why.** The q0140 smoke v1 FAILed on a pool specification error, not on the source: 200 candidates were drawn from the
13,700 exclusion ids and only then filtered to `end_at` in 2025 and volume >= $10,000, so 2 markets were smoked
(`n_in_pool` 2, `n_nonempty` 0, 0 of 2 responses non-empty, criterion (a) PASS, 0 failed requests). Details:
`SMOKE_DIAGNOSIS_2026-10-17_CB7_CB8H.md` §1. The v1 result (`creative_batch7/smoke.json`) stays on record and is never
overwritten.

**What changed (pool only; reviewer verdict ACCEPT_WITH_CHANGES, items 1-4 applied).**
1. Pool = h1_first/h2_main/h3_power exclusion ids whose *recorded* sample fields give: `end_epoch` in 2025; life
   (`end_epoch - start_epoch`) >= 14 d; `close_epoch >= end_epoch - 7 d` (the whole `[end - 14 d, end - 7 d)` print window
   lies inside the market's life; a missing `close_epoch` fails); not weather (`fee_category`); not crypto Up/Down. Recorded
   volume is **not** used. Ranked by sha256(`arepo-cb7-smoke-v2`|id); looked up on Gamma by id (same parse guard); kept if
   Gamma `endDate` in 2025, `volumeNum` >= 10,000, a condition id exists, labels are exactly Yes/No and the question is not
   Up/Down (labels are only known from Gamma, so that rule is applied there); the first 20 in seed order are smoked. Fewer
   than 20 survivors: FAIL, no widening. A zero-request host count (2026-10-17) found 33 ids passing the recorded-field
   rules, 26 of them with recorded volume >= 10k.
2. Criteria (a)-(c) and every threshold are unchanged (n 20, min_nonempty 10, min_coverage 14, window `[end - 14 d,
   end - 7 d - 1]`, limit 50, takerOnly).
3. New rules file `seals/cb7_text_geo_rules_v2.json`, `rules_sha256`
   **05bf365cbb885d0183f31da1b032b2337830afaf262c90bfa1f0e9f9061221e9**
   (`rules_version` `cb7-text-geo-rules-v2`; `smoke_pool_v2` and `run_smoke` added to the hashed functions; every v1 hashed
   function is byte-identical, and a test checks the v2 doc differs from v1 only in the smoke block, `seeds.smoke`,
   `rules_version` and the function hashes). The v1 file `seals/cb7_text_geo_rules.json` (28347c13...) is unchanged. Smoke
   version `cb7-smoke-v2`, output `creative_batch7/smoke_v2.json` (write-once). `smoke_ok`, `--require-smoke` and the two
   fetchers (text-fetch, geo-fetch) require a v2 PASS under the v2 rules hash; a v1 result never satisfies the gate.
4. Disclosure, recorded in the smoke output (counts only, no ids): the v1 result (0 of 2 responses non-empty) and the
   number of the first-20 v2 draws that were also probed by the CB7 smoke v1 (re-derived from the v1 pool and filter) or by
   the CB6 smokes (v1 seed `arepo-h8-smoke` and v2 pool draws). The CB6 h8-like probe markets of the diagnosis are not
   reproducible from the repository and are not counted. **A v2 FAIL is final**: no smoke v3, `T_seal` (2026-10-22T00:00Z)
   unchanged, and S1/G1 are then "not run (smoke FAIL)", counted.

**Queue.** Draft `queue/drafts/q0140b_cb7_smoke_v2.json` (net lane, priority 62); drafts q0142/q0143 now pin the v2 rules
file, require `smoke_v2.json` and depend on q0140b and q0141. q0144/q0145 do not pin the rules file. `queue/jobs/` untouched.
