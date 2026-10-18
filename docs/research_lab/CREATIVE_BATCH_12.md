# Creative batch 12 (CB12): mention baskets, earthquake counts, print footprints, horizon staleness, option anchors

`evidence_role: exploratory_historical` (CB12-M, CB12-E, CB12-F, CB12-X Stage 1; CB12-M and CB12-F Stage 2 on sealed
historical holdouts) / `prospective` (CB12-E Stage 2, all of CB12-O, every Stage P) | status: **DRAFT (pre-challenger).
Not frozen; no code; nothing queued.** Drafted 2026-10-18 02:53 UTC+1 (2026-10-18T01:53Z) by the CB12 design pass.
Nothing has been fetched for CB12 beyond the 25 counts-only keyless GETs and one read-only host directory listing in
§0.3. No CB12 quantity has been computed: no price sum, outcome, slope, jump, mark-out, half-life or anchor.

This file turns five round-5 ideas from `CREATIVE_HYPOTHESES_2026-10-19.md` (CH112, CH108 earthquake arm, CH110 +
CH111, CH115, CH99) into declared, falsifiable tests, and records why the other round-5 top-8 ideas (CH100, CH103,
CH106) are not tests in this batch. It follows `CREATIVE_BATCH_11.md` (CB11) and `CREATIVE_BATCH_10.md` (CB10) in
structure and rules. "As CB11 §x" means that rule applies unchanged, including its challenger-round fixes; CB4
amendment A-C1 governs the day cluster way.
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim. AREPO never
  trades. Every P&L is a paper rule at recorded or declared prices.
- Test tables bind only once the CB12 declaration hash is committed (`model_specs/cb12_v1.json`, the CB12 freeze), after
  a `science-reviewer` challenger round (§8) and a code-against-design freeze check. The fetch rules (frames, seeds,
  splits, exclusion rules, clocks, stored fields, model constants) are fixed in `seals/cb12_rules.json` before the first
  CB12 data request (q0241). The declaration is hashed in parts (M, E, F, X, O), so one family can freeze and screen
  without waiting on another's data; no rule of any part changes after another part's read.
- **Designed to run before `T_seal`.** No CB12 object is bound to the 2026-10-22T00:00Z `T_seal` lane. CB12 `net` jobs
  have priority **20-24, below every CB11 job (25-29) and every CB6-CB10 job (≥ 30)**, so they start only when nothing
  of theirs is runnable. CB12-X and every census and seal run on the `cpu` lane. If code or the freeze slips past
  `T_seal`, CB12 jobs queue behind everything else with no rule change. No CB12 historical row lies at or after
  `T12_hist_end` = 2026-10-01T00:00Z (CB12-X: before 2026-10-12, §1.2), so CB12 never touches the J4-R window
  `[10-16, 10-21)` or the E009/E010 registered window `[2026-10-13, 2026-11-03)`.
- **Queue ids q0240-q0269, one id per job, no letter suffixes** (checked free in `queue/jobs/` and `queue/drafts/` at
  drafting: none exists from q0213 upward). Specs are drafts **in this document only** (§4). Nothing is created under
  `queue/` until code, tests and the freeze check exist.
- **Naming.** Round 5 wrote the fetches as `h10_say`, `h10_shape`, `h10_alert`; CB10 already owns the `h10_` prefix
  (`h10_dlad`, `h10_brk`, `h10_sign`), so CB12 uses `h12_say`, `h12_quake`, `h12_prints` and collector roots
  `h12_quake_live`, `h12_opt_live`.

## 0. Summary, selection and scope

| Rank | Family | Hypothesis | Counted tests | Stage 1 data | Stage 2 data | Queue ids |
|---|---|---|---|---|---|---|
| 1 | **CB12-M** mention-basket overpricing (CH112) | in single-occasion "what will X say / mention" events, the sum of the members' YES prices 2 h before the scheduled start exceeds the number of members that resolve YES (M1, ≥ 0.3 words and ≥ 5% of the sum); a maker selling YES across the basket, filled only by trade-through prints before the start, earns after costs (M2) | M1 (basket excess), M2 (maker economic) | fresh `h12_say` (Gamma tag `mention-markets`, CLOB `prices-history`, Data API prints), SCREEN ends `[2025-06-01, 2026-03-01)` | the same fetch, sealed HOLDOUT ends `[2026-03-01, 2026-10-01)` (out-of-time) | q0242, q0243, q0249, q0252, q0256 |
| 2 | **CB12-F** print footprints without wallets (CH110 + CH111, one fetch) | (AL) transactions just above public alert thresholds ($10k, $25k) are followed within 15 min by more same-sign flow (AL1) and a larger same-sign move (AL2) than transactions just below; (SH) flow continuation is carried by non-round-dollar transactions (SH1) and liquidity providers lose less against round-dollar transactions (SH2) | AL1, AL2 (regression discontinuity), SH1 (slope difference), SH2 (mark-out difference) | fresh `h12_prints` (seeded 2,400 markets, newest-first Data API prints aggregated to transactions), SCREEN events | the same fetch, sealed HOLDOUT events | q0246, q0247, q0250, q0254, q0259 |
| 3 | **CB12-E** earthquake running-count anchor (CH108, earthquake arm only) | a frozen USGS-catalogue count model (negative binomial on the declustering-free 1976-2024 rate, plus the count so far) predicts the resolution of Polymarket earthquake markets beyond their price (E1, slope ≥ 0.25) | E1 (slope) | fresh `h12_quake` (Gamma tags `Earthquakes`/`earthquake`, USGS FDSN catalogue, CLOB `prices-history`), ends `[2024-09-01, 2026-10-01)` | prospective: post-freeze earthquake markets (E1-rep) and the economic check at recorded asks (E2) | q0244, q0245, q0249, q0253, q0257, q0258 |
| 4 | **CB12-X** horizon-dependent staleness (CH115; orchestrator addendum) | on the audited C1 Kalshi-Polymarket pairs, the gap half-life is longer when the Polymarket scheduled end is > 30 days away than when it is ≤ 3 days away, by ≥ 60 min (X1) | X1 (half-life contrast) | **files already on the host** (`cross_venue/`, the 2026-10-12 historical study), no fetch | none historical (worn set); Stage P-X on pairs observed after 2026-11-03 only | q0251, q0255 |
| 5 | **CB12-O** option-chain digital anchor (CH99), prospective only | for Polymarket "close above $K" equity markets, the digital read from the keyless CBOE delayed chain predicts resolution beyond the book mid (O1, slope ≥ 0.30), and buying the anchor side at the recorded ask when the gap is ≥ 4c pays after fee (O2) | O1 (slope), O2 (economic) | prospective window 1 (cron collector from the first session after the O freeze) | prospective window 2 | q0260-q0264 |
| - | CB12-F data | smoke, exclusion keys, seals, hidden-book census (CH103, counts only) | none | | | q0240, q0241, q0248, q0265 |

**Counted: 10 fixed (M1, M2, E1, AL1, AL2, SH1, SH2, X1, O1, O2) + up to 10 conditional (M1-rep, M2-rep, E1-rep, E2,
AL1-rep, AL2-rep, SH1-rep, SH2-rep, O1-rep, O2-rep) = 10-20** (§2.5). Budget fixed now; no CB12 test is added after
any CB12 read.

### 0.1 Queue id mapping (one id per job)

| Id | Job | Family | Earliest commit |
|---|---|---|---|
| q0240 | `cb12_smoke` (counts only; §CB12-S) | all | after `seals/cb12_rules.json` and smoke code exist (`cpu` lane, ≤ 60 requests) |
| q0241 | `cb12_exclusion_keys` (CB11 q0221 key file + every set created since + seal copies + C1 pair ids) | M, E, F | after q0240 PASS and CB11 q0221 complete |
| q0242 | `cb12_say_frame` (mention events, occasion rule, members, split, outcomes to the guarded file) | M | after q0241 |
| q0243 | `cb12_say_prices` (`prices-history` per member over `[start − 26 h, start]`; Data API prints; HOLDOUT to `holdout/`) | M | after q0242 |
| q0244 | `cb12_quake_frame` (Gamma tag events, rule parser, USGS catalogue for the model fit and running counts; outcomes to the guarded file) | E | after q0241 |
| q0245 | `cb12_quake_prices` (`prices-history` per market over its life) | E | after q0244 |
| q0246 | `cb12_prints_frame` (Gamma frame, volume strata, seeded 2,400 markets, event split) | F | after q0241 |
| q0247 | `cb12_prints_fetch` (newest-first Data API prints aggregated to transactions; HOLDOUT to `holdout/`) | F | after q0246 |
| q0248 | `cb12_seal` (M and F HOLDOUT listings sha256; seal copies; seal-time drops) | M, F | per family as its fetch completes |
| q0249 | `cb12_census_ME` (counts only; gates GM, GMP, GE, GEP; coverage audits; MDEs) | M, E | after q0243, q0245 and the M seal copy |
| q0250 | `cb12_census_F` (counts only; gates GAL, GSH, GS15, decoding check; coverage audit; MDEs) | F | after q0247 and the F seal copy |
| q0251 | `cb12_x_census` (counts only on host files; gate GX) | X | after q0240 (no network) |
| q0252 | `cb12_screen_M` (M1, M2 Stage 1) | M | after the M freeze |
| q0253 | `cb12_screen_E` (E1 Stage 1) | E | after the E freeze |
| q0254 | `cb12_screen_F` (AL1, AL2, SH1, SH2 Stage 1) | F | after the F freeze |
| q0255 | `cb12_screen_X` (X1) | X | after the X freeze |
| q0256 | `cb12_rep_M` (M1-rep, M2-rep on sealed HOLDOUT) | M | only if M1 or M2 advanced |
| q0257 | `cb12_quake_live` (daily 16:00Z cron outside the queue lanes: open earthquake markets, two CLOB `/book` reads, USGS last 10 days) | E | after the E freeze (collection is unconditional; analysis is not) |
| q0258 | `cb12_rep_E` (E1-rep, E2 on post-freeze resolutions) | E | only if E1 advanced; after `T12_E2_end` + 2 d |
| q0259 | `cb12_rep_F` (AL/SH reps on sealed HOLDOUT events) | F | only if an F test advanced |
| q0260 | `cb12_opt_smoke` (one live checkpoint dry run; no unit kept) | O | after `seals/cb12_opt_rules.json` |
| q0261 | `cb12_opt_live` (cron at 11:00, 13:00, 15:00 ET each trading day; windows 1 and 2) | O | after the O freeze |
| q0262 | `cb12_census_O` (counts only, window 1; gate GO) | O | after window 1 closes |
| q0263 | `cb12_screen_O` (O1, O2 on window 1) | O | after q0262 |
| q0264 | `cb12_rep_O` (O1-rep, O2-rep on window 2) | O | only if O1 or O2 advanced; after window 2 closes |
| q0265 | `cb12_hidden_census` (CH103 counts only: `active=false, closed=false` markets by end year and `acceptingOrders`; whether the capture query includes them; uncounted, a methods note) | - | after q0240 (`net`, ≤ 120 requests) |
| q0266-q0269 | reserved | - | - |

### 0.2 Selection and scope

**Ranking rule.** As CB11 §0.2 (value of information x feasibility within about a week on keyless data), with the
brief's preferences: (a) work that can run on the Oracle host **before** 2026-10-22 (keyless historical fetches on the
`net` lane behind CB11, `cpu`-lane screens on data already held); (b) originality and a plausible money mechanism;
(c) side-free and wallet-free designs (CB9-S has not reported on the Data API `side` field).

**What the drafting session read or computed (2026-10-18T00:50-01:53Z).**
- Committed documents: CLAUDE.md, AGENTS.md, round 5 §0 (counts and facts), §2 (CH99, CH108, CH110-CH112, CH115), §3
  (ranking and screen sketches), §4; CB11 in full (template); CB10 §1-§2.9; CB5 §1.1 and §CB5-K (the precedent for
  reading the C1 pair set); `CROSS_VENUE_STUDY.md` §1, §2, §10; `COLLECTION_HOST.md` (host layout); the ledger tail; the
  queue README; `battery2.KIND_RULES` (CB11 entries).
- Prior-work search: `grep` of `EXPERIMENT_LEDGER.md` and every `CREATIVE_BATCH_*.md` for CH32, CH99, CH108, CH110,
  CH111, CH112, "mention", "say during", "earthquake" finds **no test, census or sample of mention baskets or earthquake
  markets** (mentions appear only as a fee category). No batch has used a print's notional shape or an alert threshold
  as a feature, or the time to a pair's scheduled end as a moderator of the cross-venue half-life. The C1 pair set has
  been read by the cross-venue study (v1, r1) and by CB5-K (hour-of-day moderation of the lead): disclosed in §1.1.
- `battery2.cumulative_count()` on the Mac working tree (`battery2-count-v1`) = **1,156** at 2026-10-18T01:4xZ
  (`trials.jsonl` last committed at `15ec365`; the working copy is modified and not committed). The host union step runs
  before every counting CB12 job and records the post-union value.

### 0.3 Feasibility probes (counts only, 25 keyless GETs + 1 host listing, nothing stored)

Scripts lived in `/tmp/cb12probe/` (not committed); nothing was written in the repo or in data-dumps. All GETs carried
`User-Agent: arepo-research-probe`, paced at ≥ 0.6 s. **No price, outcome, volume, wallet or print value of any market
was printed**, with these disclosed exceptions: event and market counts, member counts, key names, end-date months,
the share of descriptions containing given words, and the decimal-place counts of 12 prints' `size` and `price` in one
**out-of-window** mention market (ends in `[2026-10-01, 2026-10-16)`, outside every CB12 window). The earthquake probes
(rows 6, 10) read the titles and descriptions of in-window earthquake events in aggregate (word shares, title
templates); the mention probes (row 8) counted in-window events in March 2026 and July 2025. Neither read a price or an
outcome, so no in-window date is excluded; the touched aggregates are listed here for the challenger.

| # | Request(s) | Finding |
|---|---|---|
| 1 | USGS FDSN `/count?starttime=1976-01-01&endtime=2025-01-01&minmagnitude=6.5` (sent twice: a printing bug in the first probe script lost its output; same URL, same answer class) | **2,147** M6.5+ events in 49 years (about 43.8 a year, about 3.65 a month). The count endpoint is keyless and instant |
| 2 | USGS `/query?format=geojson&starttime=2026-01-01&endtime=2026-10-01&minmagnitude=7` (sent twice, as row 1) | 11 events; property keys include `mag`, `magType`, `time`, `updated`, `status`, `ids`, `sources`, `place`; all `status = reviewed`, all `magType = mww`. **Only the final revised magnitude and its last-update time are served**: preliminary magnitudes are not reconstructible (§CB12-E PIT rule) |
| 3 | Gamma `/tags/slug/earthquakes`, `/tags/slug/earthquake`, `/tags/slug/mentions` (each sent twice, as row 1) | tag ids **103038** (`Earthquakes`) and **100184** (`earthquake`); `mentions` 404 (the mention tag is `mention-markets`, row 7) |
| 4 | Gamma `/events?closed=true&tag_id=103038&limit=100&offset=0,100` (2) | 99 closed events (second page empty), 651 markets, ≤ 9 members per event, ends 2025-11-30 to 2026-10-17 |
| 5 | Gamma `/public-search?q=say%20during&events_status=closed&limit_per_type=5` (1) | the mention events carry tag **`mention-markets` id 100343** (4 of 5); event keys include **`startTime`**, `startDate`, `endDate`, `eventMetadata`, `negRisk` (no series key in this response: series ids need a lookup, as CB11) |
| 6 | Gamma `/events?closed=true&tag_id=100343&end_date_min=2026-10-01&end_date_max=2026-10-16` (1, out of window) | 51 events, **50 with ≥ 8 members**, 824 markets, ≤ 26 members, 50 with `startTime`. One is a month-long basket ("What companies will Trump mention in September?"): **period baskets exist next to single-occasion ones** (§CB12-M occasion rule) |
| 7 | the same for ends in March 2026 and July 2025 (1 + 1, counts only) | March 2026: **65 events, 63 with ≥ 8 members, 1,472 markets**, ≤ 35 members, 58 with `startTime`. July 2025: 19 events, 17 with ≥ 8, 219 markets, 15 with `startTime`. The population grows through the window: about 300 events in SCREEN and 350 in HOLDOUT is the planning figure (§CB12-M power) |
| 8 | CLOB `prices-history?market=<token>&startTs=<start−3d>&endTs=<start>&fidelity=10` on one out-of-window mention member (1) | 200, **432 rows** (`t`, `p`): explicit bounds work at 10-minute fidelity |
| 9 | Data API `/trades?market=<cid>&limit=1000`, the same with `offset=1000`, and with `filterType=CASH&filterAmount=1000` (3, same market) | 12 prints, 12 distinct transaction hashes; keys include `size`, `price`, `timestamp`, `transactionHash`, `outcomeIndex`, `side`, `proxyWallet` (wallet not printed, never stored by CB12). `size` decimals: 6 integer, 6 fractional (2-5 places); `price` decimals: 8 at 1-2 places, **3 at 6 places** (sub-tick effective prices: the shape classifier must work on transaction notionals, §CB12-F). `offset=1000` returns 0 rows; the cash filter is accepted (0 rows) but **not verified** and is not used |
| 10 | Gamma `/events?closed=true&tag_id=103038&limit=100` and `tag_id=100184` (2) | union **130 events** (37 in both tags); **108 end before 2026-10-01, with 553 markets**. Descriptions: "USGS" in 548/553, "ET"/"Eastern" in 542/553; 486/553 are neg-risk members; 6/553 regional questions. Title templates: weekly "How many M or above earthquakes <date> - <date>?", "How many M or above earthquakes by <date>?", "Another M or above earthquake by...?", "What will the biggest earthquake be on <date>?". Tag 100184 reaches back to 2024-09 (68 events, 310 markets) |
| 11 | CBOE `cdn.cboe.com/api/global/delayed_quotes/options/SPY.json` (1) | **12,630 options, 32 expiries, the first four daily (2026-10-19..22)**; fields `bid`, `ask`, `bid_size`, `ask_size`, `iv`, `delta`, `gamma`, `theo`, `last_trade_time`, `open_interest`; a top-level `timestamp` |
| 12 | Gamma `/public-search?q=close%20above&events_status=active&limit_per_type=50` (1) | 22 events, **12 titled "Will <Name> (<TICKER>) close above ___ end of October?"** with 11-13 strikes each (NVDA, TSLA, MU, MSFT, ...). No daily strike event in the top 50 hits (CB9 probe 4 saw daily ones in June/August): the live O frame is at least month-end ladders, daily ones if the census finds them |
| 13 | `ssh oracle` read-only `ls -la` and `du` of `/home/opc/arepo/data-dumps/research_lab/cross_venue/` (no file opened; orchestrator addendum) | the historical study's files: `series/` (**493** `.npz` pair series), `matches.json` (0.32 MB), `matches_all.json`, `audit_flags.json`, `audit_sample100.json`, `results.json`, `results_r1.json`, `results_r1_attribution.json`, `poly_markets.json` (171 MB, the 2026-10-12 Gamma pull), `kalshi_markets*.jsonl`; 357 MB; **every file dated 2026-10-12** (before E009's 2026-10-13 registration). E009/E010 live state is in the separate `cross_venue_live/` |

Request total: 25 GETs (rows 1-3 count 10 because of the resend; rows 4-12 count 15), under the 30 cap.

### 0.4 Selection decisions

| Idea | Decision | Reason |
|---|---|---|
| **CH112** mention-basket overpricing | **include (M), priority** | Fully keyless, outcome-light (Polymarket's own resolutions), a large and growing population (probes 6-7: 50-65 events a month with ≥ 8 members in 2026), events are natural independent units, and the money route is a zero-fee maker. No AREPO test has touched the class |
| **CH110 + CH111** footprints | **include (F), one fetch** | Round 5 §3 asks for them to be declared together on one side-free fetch. Both are wallet-free and side-free, both are new measurements of the flow mix that killed every flow carry (E007, HB1), and the fetch fills about 3 h of the idle `net` lane |
| **CH108** earthquake arm | **include (E), Stage 1 historical, Stage 2 prospective** | The only statistic-resolved class with a complete keyless outcome path (USGS) and an exact external prior; 553 markets in 108 events (probe 10). Honest weakness: every market shares one global quake process, so the effective clusters are calendar weeks; a feature-only power gate (GEP) decides before any outcome is read. E2 (economic) moves to Stage 2 at recorded asks because 553 markets cannot power a historical net (MDE about 15c) |
| **CH115** horizon staleness | **include (X), `cpu` lane, per the orchestrator addendum** | Clean on the conditions set: the 316-pair history is on the host (probe 13), every file predates the E009/E010 window, the live root is never opened, and no fetch is needed. Disclosed: the set is worn (§1.1), so X1 has no historical replication; Stage P-X waits until 2026-11-03. The CH115 second line (2 h captures' `oneHourPriceChange` autocorrelation by horizon) is **dropped**: it reads the live complete-universe captures, which E011 and the J4-R window use |
| **CH99** option-chain anchor | **include (O), prospective only** | Round 5's rank 1 and the only professional-counterparty anchor with a verified keyless feed (probe 11). The chain has no keyless history, so O is two prospective windows with a frozen plan. Probe 12 found month-end strike ladders live now; the census counts daily ones |
| CH100 extended-hours anchor | dropped from CB12 | Its window `[2026-08-11, 2026-10-01)` sits beside CB9-P's sealed Pyth Up/Down frame and Stage-2 sessions on the same markets and underlyings; a disjointness argument needs CB9-P's final session list. Re-entry: CB13, after CB9-P's Stage-2 session list is committed |
| CH103 hidden long-dated books | **counts only (q0265, uncounted)** | A census, not a test. It doubles as a universe-completeness check for the capture job (round 5 fact 1), so it is worth 120 requests now; any test on hidden rungs is a later registration |
| CH106 hazard calendars | dropped from CB12 | Needs archived calendars with point-in-time publication stamps for three sources; no keyless archive was verified in this round's probes. Re-entry: CB13 with a verified archive |
| CH108 measles, Rotten Tomatoes, App Store arms | dropped from CB12 | Measles needs CDC first-print tables by publication date (not probed); RT and App Store are 8-week prospective pollers that add collection load for small classes |

**Sports and categories.** `CB12_SPORTS_IN_PRIMARY = false` (a parameter, as CB8-CB11). M and E are non-sports by
construction. F excludes sports, crypto, weather, Pyth dailies, crypto strike ladders, Up/Down markets (tags plus
`CB1_UPDOWN_RE`), and the mention-markets and earthquake tags (so F is key-disjoint from M and E by rule). X keeps the
C1 set's categories (149 of 316 pairs are sports); its primary is all C1 pairs as round 5 states, with sports and
elections as binding strata (§CB12-X). O is equities. Category stays a parameter.

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Prior use | Role in CB12 | Evidence ceiling |
|---|---|---|---|
| `history/h12_say` (**new**, q0242/q0243): mention events and members (whitelisted fields), per-member `prices-history` over `[start − 26 h, start]`, transactions in `[start − 26 h, start)` and the first transaction at or after `start` (for the early-start check); outcomes only in `outcomes_guarded.csv.gz` | none | M1, M2 | L1 / L2 (sealed later ends) |
| `history/h12_quake` (**new**, q0244/q0245): earthquake events and members, parsed rule windows, `prices-history` over each market's life; USGS catalogue M ≥ 4.5 `[2000-01-01, 2026-10-01)` and M ≥ 6.0 `[1976-01-01, 2026-10-01)` (time, lat, lon, mag, magType, status, updated); Gamma outcomes only in `outcomes_guarded.csv.gz` | none | E1 | L1 |
| `history/h12_quake_live` (**new, post-freeze**, q0257): open earthquake markets, two receipt-timed CLOB `/book` reads per member per day, USGS events of the last 10 days | none | E1-rep, E2 | L2 (out-of-time, prospective) |
| `history/h12_prints` (**new**, q0246/q0247): seeded 2,400 markets, newest-first prints aggregated by transaction hash at fetch (time, YES-terms VWAP, size, notional, fee-adjusted notional, fill count, max-fill notional; hash discarded) in `[2026-04-01, 2026-10-01)` | none | AL1, AL2, SH1, SH2 | L1 / L2 (sealed holdout events) |
| `cross_venue/` on the host (series `.npz`, `matches.json`, `audit_flags.json`, `audit_sample100.json`, `poly_markets.json` read for `endDate` only; sha256 pinned in the rules file) | cross-venue v1 (48 lines) and r1 (34 lines), CB5-K (hour moderation), E009's coefficients (v1 fit) | **X1 population and series** | L1, **worn set, new moderator** (labelled in every X line) |
| `history/h12_opt_live` (**new, post-freeze**, q0261): Gamma strike frame, CBOE chain per underlying, two CLOB `/book` reads per member, Yahoo daily bars after settlement | none | O1, O2, O1-rep, O2-rep | prospective (window 1 Stage 1; window 2 Stage 2) |
| `cross_venue_live/` (E009/E010 poller) | E009, E010 (registered `[2026-10-13, 2026-11-03)`, no interim looks) | **never opened by any CB12 path**; Stage P-X may use it only after both E009 and E010 final analyses are committed and the owner signs off | - |
| `h1_first`, `h2_main`, `h3_power`; `h4_seal`, `h5_cb1`, `h5_cb1_ladders`, `h6_weather`, `h7_cb4_*`, `h8_*`, `h9_flow`, `h10_sign`, `h10_dlad`, `h10_brk`, `h11_wprints`, `h11_pol`, `h11_attn`, CB5, CB8, CB9 data | worn, retired, sealed or batch-owned | **not read** (runner refuses), except id columns for exclusion keys through a field-restricted accessor | - |
| `snapshots/`, `trade_samples/`, `live_trades/`, `book_sweeps/`, `surprise_live/`, every `cb*_extract/` table | live stores, E-series, CB1-CB11 | **never read by any CB12 Stage 1 or Stage 2 path** (Stage P may name them in its own registration) | - |

**Reuse disclosure (X).** The C1 set is the most-read historical object in the programme: the cross-venue study found
the lead and the pooled half-life (66 min, CI 48-86) on it, and CB5-K reads it for hour-of-day moderation. Nobody has
cut the half-life by time to the scheduled end (grep of `CROSS_VENUE_STUDY.md` and CB5: the study's "horizons" are
forecast horizons of 10 min, 1 h and 6 h, not time to resolution). X1 is therefore a new statistic on worn data,
labelled **"L1, worn set, new moderator"**; it has no sealed historical holdout, and its only replication route is the
post-2026-11-03 live stream (Stage P-X). C1 membership inherits CB5-K's disclosed caveat: 4 hand drops were first
surfaced by the outcome-disagreement list, although each is identifiable from its title.

**Reuse disclosure (M, E, F).** None of the three populations has been sampled by an AREPO test (prior-work search,
§0.2). The broad h2/h3 panels and CB7-CB11 frames may contain individual mention, earthquake or print-sample markets;
they are removed by key (§1.3). The C1 set holds 18 mention pairs: their Polymarket markets and events join the M, E and
F exclusion keys.

### 1.2 Dates (declared; UTC unless ET is stated)

| Name | Value | Meaning |
|---|---|---|
| `T12_draft` | 2026-10-18T01:53Z | this draft; no CB12 quantity computed |
| `T12_hist_end` | 2026-10-01T00:00Z | no historical M, E or F row (scheduled end, print, price point, catalogue event used in a feature, resolution) at or after it |
| `T12_X_end` | 2026-10-12T00:00Z | X reads only steps before it (the study's files were written on 2026-10-12; every C1 pair resolved before); the runner refuses any step at or after it and any input whose mtime is at or after 2026-10-13T00:00Z |
| `T_seal` | 2026-10-22T00:00Z | not binding for CB12; CB12 `net` jobs yield to every CB11 and `T_seal`-bound job |
| M SCREEN / HOLDOUT | event `endDate` in `[2025-06-01, 2026-03-01)` / `[2026-03-01, 2026-10-01)`, sealed | out-of-time split |
| M origins | `t = startTime − 2 h` (primary), `t24 = startTime − 24 h` (robustness) | `startTime` = the event's scheduled start as fetched (hindsight label, §CB12-M) |
| E window | market `endDate` in `[2024-09-01, 2026-10-01)`; model fit on catalogue events before 2024-09-01 | Stage 1 |
| E checkpoints | 16:00Z daily (12:00 ET in EDT, 11:00 ET in EST) | §CB12-E |
| `T12_E2_start` / `T12_E2_end` | the first earthquake market listed ≥ 1 day after the E freeze / `T12_E2_start` + 56 days of scheduled ends | E Stage 2; `T12_E2_collect_max` = `T12_E2_start` + 90 days (else E1-rep, E2 "not run (collection)", counted) |
| F window | transactions in `[2026-04-01, 2026-10-01)`; markets with scheduled end in `[2026-04-08, 2026-10-01)` | same calendar as CB9-K/D, CB10-B, CB11-A (markets disjoint by key) |
| F split | Gamma event SCREEN/HOLDOUT 50/50 by seeded hash `arepo-cb12-prints-split` | at frame time, before any print read |
| X horizon bins | `τ = endDate_PM − t`: short `τ ≤ 3 d`, mid `(3 d, 30 d]`, long `τ > 30 d` | declared now, no data-dependent cut |
| O window 1 | settlement dates from the first trading session ≥ 1 day after the O freeze until 60 (underlying, settlement date) clusters with ≥ 1 tight unit have settled, or 2027-01-31, whichever first | O Stage 1 (prospective); the stop counts clusters, never results |
| O window 2 | the next window by the same rule (cap 2027-05-31) | O Stage 2 |
| O checkpoints | 11:00, 13:00, 15:00 America/New_York on regular US trading days | DST-aware; settlement on the 16:00 ET close |

### 1.3 Sealed and untouched data (named)

- **Refused roots.** `run_cb12.py` refuses every root in the last three rows of §1.1 (field-restricted id readers
  excepted). It writes only under `research_lab/creative_batch12/` and `history/h12_*`. The X loader opens only the
  sha256-pinned files of `cross_venue/` listed in §1.1 and refuses any path containing `cross_venue_live`.
- **Exclusion keys (q0241).** Union of: (1) CB11 q0221's `exclusion_keys.csv.gz` (sha256 pinned; q0241 depends on its
  completion); (2) id columns of every sampled or frozen set created since or not in it: `h9_flow`, `h10_sign`,
  `h10_dlad`, `h10_brk`, `h11_wprints` samples, `h11_pol`, `h11_attn` (both strata), CB8 and CB9 frames on the host;
  (3) every id in seal copies under `docs/research_lab/seals/` committed by then; (4) the C1 pairs' Polymarket market
  ids and event ids (`matches.json`, ids only; for M, E and F). Keys = market id, Gamma event id, `negRiskMarketID`,
  series id (looked up on Gamma, ≤ 50 ids per request, where a source lacks them). A frame not yet built is "absent at
  q0241" (recorded) and re-read at the seal-time drops (q0248, and the census for E). If more than 2% of exclusion ids
  lack metadata, disjointness is "unverified" and the affected family is "not testable", counted. **CB11's later
  builds and CB13 must add CB12's frame ids.**
- **Series rule (declared deviations, for the challenger).** M: each mention event is its own occasion with its own
  outcomes, and speaker series (weekly Trump speeches, earnings calls) would be dropped whole by the series-key rule if
  any prior sample ever held one event. M therefore drops by market id, event id and a **series-date key** (same series,
  `startTime` within ±1 day), as CB10-D; the census reports the drops the full series rule would have made. E: every
  earthquake market shares the global quake process, so the dependence that matters is time overlap, not series. E
  drops any event whose rule window **overlaps** the window of any excluded earthquake event (stricter than the series
  rule), counted by source; if more than 30% of E events are dropped, E1 is labelled "population thinned by
  exclusions". F uses the full rule (market, event, `negRiskMarketID`, series).
- **SEALED-M, SEALED-F.** HOLDOUT rows are written to `holdout/` subdirectories with listing sha256s; seal copies
  `seals/cb12_say_holdout_SEAL.json`, `seals/cb12_prints_holdout_SEAL.json` committed by q0248 before the matching
  census. The census reads HOLDOUT file and unit counts only. No CB12 path opens a HOLDOUT file before the family's
  Stage-1 result is committed and its rep is triggered.
- **E has no historical holdout** (108 events cannot be split without halving a cluster-limited power); its replication
  is out-of-time and prospective (E1-rep), with the economic check at recorded asks (E2). X has none (worn set). O's
  windows are prospective by construction.
- **Outcome guards.** M: Gamma `outcomePrices` and `umaResolutionStatus(es)` → `h12_say/outcomes_guarded.csv.gz`,
  opened only by q0252/q0256. E: the Gamma outcome → `h12_quake/outcomes_guarded.csv.gz`, opened only by q0253 (the
  agreement audit) and q0258 (E2 pays what the venue paid); **E1's primary outcome is computed from the USGS catalogue
  by the frozen rule parser, never read from Gamma** (CB9-P's guard). The catalogue's events after each market's
  checkpoint are, for the census, behind the same accessor: the census sees catalogue events only before each unit's
  `t − 72 h`. F has no outcome (print-based targets). X has no outcome (gap dynamics). O: the Yahoo settlement close and
  the Gamma outcome → `h12_opt_live/outcomes_guarded/`, opened only by q0263/q0264.

### 1.4 Rules files

- `seals/cb12_rules.json` (before q0240/q0241) fixes: the M frame rule (tag id 100343, member minimum, occasion rule,
  windows, split, origins, tightness and fill rules, costs); the E frame rule (tag ids 103038 and 100184, title templates
  and the rule-window parser regexes written from out-of-window events only, the catalogue queries, the model and its
  fitting window, checkpoints, PIT rules); the F frame rule (exclusions, volume strata, sample sizes, seeds, split), the
  transaction aggregation, shape grids and fee branch, impact-sign rule, AL cutoffs, bandwidth, donut and placebo
  cutoffs, SH targets; X's input sha256s, the C1 reproduction call, bins and estimator; census gates; smoke criteria;
  seeds. `seals/cb12_opt_rules.json` (before q0260) fixes O's frame regex, rule-text flags, underlying map, anchor rule,
  exclusions, checkpoints, tightness, edge threshold, window rules and costs.
- Fetchers refuse (exit 2) on a hash mismatch. **No rule is computed from, or revised after, any M, E, F, X or O read.**
- No wallet field is read or stored by any CB12 job (no HMAC key is needed). **No statistic reads `side`.**
- **Field whitelists (as CB11 §1.4).** Gamma parsers keep only `id, conditionId, question, slug, clobTokenIds, outcomes
  (labels), startDate, createdAt, endDate, negRisk, negRiskMarketID`, event ids, event `startTime`, series ids, tag ids,
  `feeSchedule`, and the sha256 of `description` plus frozen flag booleans (E additionally stores the parsed rule window
  and threshold, not the text); F stores a volume-stratum label computed in memory from `volumeNum` (the number is not
  stored); `outcomePrices`, `umaResolutionStatus(es)` and `closedTime` reach only the guarded files (`closedTime` for
  hold lengths only). Data API parsers keep `timestamp, price, size, outcomeIndex, transactionHash` in memory, aggregate,
  and write no hash, wallet, name or side. A unit test feeds fixtures carrying every forbidden field and asserts that no
  parsed row, file or log contains them.

## 2. Common rules (deltas from CB11 §2)

### 2.1 Costs

| Test | Price and cost rule |
|---|---|
| M1, E1, AL1, AL2, SH1, X1, O1 | none (calibration, forecasting, discontinuity, mechanism and dynamics tests) |
| M2 | resting maker ask at `a_i = p_i(t) + 1.5c` (half of the 3.0c round-4 median spread) on every available member; **filled only by trade-through**: the first transaction in `[t, startTime)` with YES-terms price ≥ `a_i + 1c`; filled size = min(100 shares, that transaction's size); maker fee 0, no rebate; held to resolution |
| SH2 | none charged (the mark-out *is* the liquidity provider's gross; makers pay no fee); reported net of the 15-25% rebate is not used |
| E2 (Stage 2) | buy the model-favoured token at the **recorded** best ask of the first book read at the checkpoint, size ≤ the displayed ask size; taker fee `r·a(1 − a)`, `r = max(feeSchedule.rate, 0.05)`; held to resolution |
| O2 | buy the anchor-favoured token at the **recorded** best ask (YES ask, or NO at `1 − YES bid`) of the first book read; size ≤ displayed size at the touch; fee `r·a(1 − a)`, `r = max(feeSchedule.rate, 0.04)`; held to settlement |
| Binding cost robustness | M2: quote at `p + 1.0c` (closer to mid, more adverse selection) and trade-through of 2c each keep net > 0; E2, O2: +0.5c on the ask keeps net > 0 |

M2 uses declared, not recorded, quotes (no historical books without pmxt): it is a "modelled-cost economic check (L1)";
recorded books enter in Stage P-M (§2.9). E2 and O2 are at recorded asks.

### 2.2 Clocks

- **CLOB `prices-history`.** A point is known from stamp + 600 s; the price at `t` is the last point with stamp + 600 s
  < `t` and age ≤ 24 h, else "unavailable (no price)" (CB11 §2.2).
- **Data API prints.** Venue `timestamp` (s), aggregated by transaction hash at fetch into one row per (market,
  transaction): YES-terms VWAP (outcome-1 prints mapped to `1 − price`), total size, notional `Σ size x price` (USDC, in
  the traded token's terms), fee-adjusted notional (§CB12-F), fill count, max-fill notional, time. A condition at `t`
  uses transactions with time < `t`.
- **USGS catalogue.** Event origin `time` (ms). Magnitudes are final revised values (probe 2). **A catalogue event is
  usable at `t` only if its origin time is < `t − 72 h`** (declared: magnitudes are typically reviewed within days; the
  final value of a quake younger than 72 h is a disclosed residual look-ahead), and units with any catalogue event of
  magnitude within ±0.3 of the market's threshold in `[t − 72 h, t)` are "ambiguous recent quake" (excluded, counted).
- **CLOB `/book` (E Stage 2, O).** Receipt time; two reads per token per checkpoint, the second ≥ 60 s after the first;
  crossed books ineligible, never repaired. **CBOE chain:** the response's top-level `timestamp`; the unit requires
  chain timestamp < the first book's receipt time (the 15-minute delay makes the anchor conservative).
- **Cross-venue series (X).** As the study and CB5-K: Polymarket point usable at stamp + 600 s, Kalshi candle mid with
  spread ≤ 10c, both prices in [3%, 97%], 10-minute grid, nothing interpolated.
- `closedTime` is never a population condition, origin or feature (hold lengths only, guarded).

### 2.3 Uncertainty and decision rule

As CB11 §2.3 (unweighted primary; one-sided p = max over declared cluster ways; 2,000-draw cluster bootstrap, **seed
1212**; small-G rule as CB10 §2.3; A-C1 day way; top-5 drops; ≥ 100 units and ≥ 30 clusters for testability; "unknown"
never counts as met). Cluster ways: **M** speaker key (Gamma series id, else the frozen speaker regex on the title) and
ISO week of `startTime` (events are the units); **E** Gamma event and ISO week of the checkpoint (one quake moves every
open market); **F** Gamma event and UTC day; **X** Polymarket event and calendar month of the earlier resolution;
**O** (underlying, settlement date) and settlement date.
- **Stage 1 (10 tests).** Advance iff one-sided p < 0.01, the §2.4 floor is met, every binding placebo, robustness
  check and gate holds, **and the test passes a batch Holm step-down at one-sided α = 0.05 over k1 = 10 (fixed)**
  (binding; stricter than CB11's label-only Holm, as the brief asks). Tests that finish before the last Stage-1 result
  (every family but O) are judged at α/k1 = 0.005 when they finish; the full Holm is applied when O1/O2 are final, and
  can only add advances that were then confirmed by their own reps' trigger rule (it never removes a finished
  family's rep once triggered). BY label (q = 0.10 over `battery2.cumulative_count()` at the run) triage only.
- **Stage 2 (reps).** One Holm at one-sided α = 0.05 over every CB12 test reaching Stage 2, each in its Stage-1
  direction (E2 and O2 in their declared direction, net > 0); k fixed when the last Stage-1 result is final; early
  finishers judged at α/k. Labels: M1-rep, M2-rep "out-of-time replication on a sealed later window (L2)"; AL/SH reps
  "sealed same-calendar holdout replication (L2)"; E1-rep "out-of-time prospective replication (L2)", E2 "prospective
  economic check at recorded asks (L2)"; O reps "second prospective window (L2)".
- **Stage P** is a separate registration for any survivor (§2.9).

### 2.4 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate |
|---|---|---|
| M1 | basket calibration | `D̄ = mean_e(S_e − N_e) ≥ 0.3` words **and** `D̄ / mean_e(S_e) ≥ 0.05` (CH112's kill rule) |
| M2 | economic | net ≥ +0.5c per filled share **and** the route gate: Σ net over all intended quotes (unfilled = 0, per 100 intended shares) > 0 |
| E1 | forecasting | slope `β̂ ≥ 0.25` of `Y − p_t` on `q − p_reg` |
| E2 (Stage 2) | economic | net ≥ +1.0c per share after fee |
| AL1 | discontinuity | jump in `log(1 + follow-on same-sign notional, 15 min)` ≥ +0.10 (about +10%) |
| AL2 | discontinuity | jump in the 15-min impact-signed move ≥ +0.5c |
| SH1 | mechanism contrast | `β_NR − β_R ≥ +0.15c` per SD of flow (2 h move) |
| SH2 | mechanism contrast | mark-out(R) − mark-out(NR) ≥ +0.5c per share (60 min) |
| X1 | dynamics contrast | `HL_long − HL_short ≥ +60 min` |
| O1 | forecasting | slope `β̂ ≥ 0.30` of `Y − m2` on `q − m1` (§CB12-O) |
| O2 | economic | net ≥ +1.0c per share after fee |

### 2.5 Counting (M3 rule)

- Kinds **`cb12_test`** (Stage 1 per-test lines), **`cb12_replication`** (Stage 2, including E2), **`cb12_descriptive`**
  (EXCLUDE: smoke, census, gates, strata, variants, the CH103 hidden-book census, the per-word calibration slope, the
  taker basket variant, period baskets, the earthquake class strata, the Gamma-outcome agreement audit, F's shape
  shares by era, X's mid tercile and lag cross-correlations, O's flat-vol anchor). Per-test lines count 0 themselves;
  **the tests are the `n_tests` of the `ml_explain` count lines** (as CB11), placebo lines count 0. New
  `battery2.KIND_RULES` entries mirror CB11's; unknown kinds raise.
- **Count lines and `n_tests`:** `creative_batch_12:M` **2** (M1, M2); `creative_batch_12:E` **1** (E1);
  `creative_batch_12:F` **4** (AL1, AL2, SH1, SH2); `creative_batch_12:X` **1** (X1); `creative_batch_12:O` **2** (O1,
  O2). Replication lines `creative_batch_12:<family>:rep` carry `n_tests` = the number of that family's reps actually
  triggered (M ≤ 2, E ≤ 2 (E1-rep, E2), F ≤ 4, O ≤ 2, X 0).
- **Cumulative count: 1,156** (Mac working tree, `battery2-count-v1`, 2026-10-18T01:4xZ; host-unioned value recorded by
  every counting job).
- **CB12 adds 10 fixed tests and up to 10 conditional ones.** Budget: **10-20**.
- Tests behind a failed or unknown gate (smoke, disjointness, GM, GMP, GE, GEP, GAL, GSH, GS15, GX, GO, decoding,
  coverage audits, availability) are "not testable" or "not run" (p = 1) and are **still counted**. A job waiting on
  exit 75 is "pending" and produces no line. Conditional tests count only if their trigger fires; a triggered test that
  cannot run is counted with p = 1.

### 2.6 Placebos and robustness (common)

Design rule as CB11 §2.6: every binding placebo names the alternative under which the test would advance; calibration
placebos are judged on the p threshold alone (floors off); 200 draws; **advance rate ≤ 1.5%**. Seeds 12101-12120.
Family placebos, attributions and robustness checks are in §3. Common binding robustness for any advance: (i) the
declared cost robustness (§2.1) for economic tests; (ii) p threshold and floor hold without the top 5 clusters of each
way; (iii) sign by period (M: each SCREEN half; E: each calendar half of the window; F: ≥ two thirds of months with ≥
200 units; X: each of the C1 window's thirds by step date; O: each half of window 1 by settlement date); (iv)
unavailable units are excluded and counted by label, never imputed; a test whose available share of eligible units is
< 60% is "not testable (availability)".

### 2.7 Pre-freeze census (counts only; q0249 for M and E, q0250 for F, q0251 for X, q0262 for O)

Outcome guards first; field-restricted accessors; a unit test asserts that no census path receives an outcome, a
catalogue event at or after any unit's `t − 72 h`, a later price used as a target, a mark-out, a follow-on flow count
or a gap-dynamics statistic. Features (prices at `t`, `q`, notionals, shapes, impact signs, horizons) and unit counts may
be computed.
- **M.** Events by month, occasion vs period baskets, members, members listed by `t`, available members (≥ 90% rule),
  key drops by source (and full-series-rule drops), speaker keys, ISO weeks, `S_t` distribution (feature). **Gate GM:**
  ≥ 150 SCREEN occasion events in ≥ 15 speaker keys and ≥ 30 ISO weeks. **Coverage audit:** ≥ 90% of eligible members
  have a `prices-history` point at `t` (source availability) and ≥ 90% of SCREEN members have prints reachable back to
  `t24`. **Power gate GMP (feature-only):** simulated outcomes `Y*_i = 1{Φ(Z_i) < p_i}`, `Z_i = √0.3·V_e + √0.7·ε_i`
  (declared), 500 draws (seed 12121); `MDE_M1 = (z_0.99 + z_0.80) x 1.2 x max(SD(D̄*), mean speaker-way SE, mean
  week-way SE)`. **If `MDE_M1 > 1.0` word, M1 and M2 are "not run (power)", counted.**
- **E.** Events and markets by class (count buckets, "another by", daily maximum) and month; rule-parser failures;
  "ambiguous recent quake" units; key and overlap drops; eligible (market, checkpoint) units by label ("not listed",
  "unavailable (no price)", "no separate earlier point", "parser failure"); `q` and `q − p_reg` distributions (features).
  **Gate GE:** ≥ 300 markets with units in ≥ 60 events and ≥ 40 ISO weeks; parser failures ≤ 20% of markets (else E1
  "not testable (rule parser)"). **Power gate GEP (feature-only, as CB10 GDP):** per event one uniform `U_e` (a Gaussian
  copula on a shared ISO-week factor, ρ = 0.3 declared) selects the simulated winning bucket (or date rung) from the
  cumulative normalised prices at the event's first checkpoint; 500 draws (seed 12122); `MDE_E1 = (z_0.99 + z_0.80) x
  1.2 x SD(β̂*)`. **If `MDE_E1 > 1.0`, E1 is "not run (power)", counted; E1-rep and E2 are not triggered.**
- **F.** Frame by stratum and category; key drops; markets fully covered (newest-first cap not reached before
  2026-04-01) by stratum; transactions; signed share; shape classes (R, Q, B, N) by stratum, price band and fee era
  (feature). **Decoding check** from the smoke (§CB12-S). **Gate GAL:** ≥ 4,000 SCREEN transactions within ±$2,000 of
  $10,000 and ≥ 1,000 within ±$2,000 of $25,000 (donuts removed, signed, follow-up covered), in ≥ 200 events and ≥ 60
  UTC days. **Gate GS15 (CH111 kill):** round-dollar transactions ≥ 15% of signed SCREEN transactions; else SH1 and SH2
  "not testable (no round-dollar mass)". **Gate GSH:** ≥ 20,000 SCREEN market-hours with both flows defined in ≥ 300
  events and ≥ 60 days, and ≥ 20,000 signed R transactions with a 60-min mark available. **Coverage audit:** ≥ 50% of
  SCREEN markets fully covered **and** the full-coverage subset passes GAL/GSH at half their minimums (needed for the
  binding full-coverage robustness, §CB12-F); FAIL → the family is "not testable (source limited)".
- **X.** Pairs, events and usable steps by horizon bin, category and PM-volume tercile; pairs with `endDate`
  disagreeing with Kalshi's scheduled close by > 7 days (the edit flag); steps with τ undefined. **Gate GX:** short and
  long bins each with ≥ 30 pairs, ≥ 20 events and ≥ 20,000 usable consecutive step pairs; else X1 "not testable (horizon
  range)". The C1 window is the last 30 days before the earlier resolution, so the long bin exists only through pairs
  whose scheduled end lies beyond their actual resolution (futures resolved early, eliminations): GX may fail, and that
  is reported as such.
- **O** (q0262, after window 1). Units by underlying, settlement date, checkpoint, anchor type (direct call-spread
  digital vs `Φ(d2)`), tightness, exclusions. **Gate GO:** ≥ 1,000 tight units, ≥ 40 (underlying, settlement) clusters,
  ≥ 10 tight units per session on average (CH99 kill).
- MDEs are recomputed from these counts and never used to change a floor, window or threshold.

### 2.8 Compute, network, disk and stop rules

- **Host.** 1 OCPU, about 5.6 GiB RAM shared with the collectors. Queue rules as CB11 §2.8 (one job per lane, nice 19,
  `MemAvailable ≥ mem_mb + 1200`, address cap 2 x `mem_mb`, 02:45-05:30 UTC blackout for `mem_mb ≥ 500`). **No pmxt
  ingress.** Every reader streams one market (or pair) at a time. `mem_mb` ≤ 900 everywhere; **900 is justified** for
  q0250/q0254 (F census and screen hold per-cluster sufficient statistics for about 6-12 million transactions plus 200
  permutation draws as cluster-level arrays) and q0251/q0255 (the X loader extracts `endDate` for 316 ids from the
  171 MB `poly_markets.json` with a streaming parser, never a full `json.load`, which would need about 1.5 GB).
- **Network** (`net` lane, priorities 20-24; ≤ 2 rps Polymarket, ≤ 1 rps USGS, CBOE and Yahoo):

  | Job | Work | Requests / wall | Stored (cap) |
  |---|---|---|---|
  | q0240 | smoke (`cpu` lane) | ≤ 60, < 5 min (+ ≤ 60 public Polygon JSON-RPC receipt reads for the decoding check) | 0.001 GB |
  | q0241 | exclusion keys (increment over CB11 q0221) | ≤ 600 Gamma, ≤ 6 min | ≤ 0.01 GB |
  | q0242 | M frame: tag 100343, monthly `end_date` windows over 16 months, ≤ 2 pages each, + series lookups | ≤ 150, ≤ 3 min | ≤ 0.005 GB |
  | q0243 | M prices and prints: about 9,000 occasion-basket members (planning figure from probes 6-7) x 1 `prices-history` request + ≤ 2 Data API pages each | ≤ 28,000, about 3.9 h | ≤ 0.08 GB |
  | q0244 | E frame (≤ 10 Gamma) + USGS (M ≥ 6.0 1976-2026 in ≤ 5 requests; M ≥ 4.5 2000-2026 in ≤ 20 requests of ≤ 20,000 rows) | ≤ 40, ≤ 2 min | ≤ 0.03 GB |
  | q0245 | E prices: 553 markets x ≤ 3 bounded `prices-history` requests (14-day chunks for long markets, fidelity 60) | ≤ 2,000, ≤ 20 min | ≤ 0.01 GB |
  | q0246 | F frame: one-day `end_date` windows over 176 days, paged | ≤ 1,200, ≤ 12 min | ≤ 0.005 GB |
  | q0247 | F prints: 2,400 markets, newest-first pages of 1,000 until the oldest is before 2026-04-01 or the 20,000-print cap | ≤ 24,000, about 2.5-3.5 h | ≤ 0.5 GB |
  | q0265 | CH103 census | ≤ 120 Gamma, ≤ 2 min | 0.001 GB |
  | q0257 | E live (cron, daily, outside the lanes) | ≤ 200 per day (≤ 5 Gamma, ≤ 2 x 80 `/book`, 1 USGS), ≤ 3 min at 1 rps, mem ≤ 300 | ≤ 0.01 GB total |
  | q0261 | O live (cron, 3 x per trading day, outside the lanes) | ≤ 450 per checkpoint (≤ 5 Gamma, ≤ 20 CBOE, ≤ 2 x 200 `/book`; Yahoo daily bars after settlement), ≤ 5 min at 2 rps, mem ≤ 300 | ≤ 0.3 GB per window |

  Historical `net` total **≤ about 56,000 requests, about 7-8 h of `net` lane at 2 rps**, behind CB11's about 10-11 h.
  The two crons add at most 2 rps for ≤ 5 minutes per checkpoint to whatever `net` job is running (disclosed overlap,
  as CB10 q0210). **A fetch that has not completed (its `*_complete` status absent) is "pending" and is never analysed
  partially**: the census and every screen refuse on an incomplete manifest.
- **Disk guard.** Every CB12 data job declares `--disk-cap-gb` (its output cap) and `--data-dumps-cap-gb 40`, and exits
  **75** if data-dumps + its cap > 40 GiB **or** root free disk − its cap < 4.5 GB. Historical CB12 output caps total
  **≤ 0.65 GB**; the two live roots ≤ 0.65 GB more over their lifetimes. Exit-75 waits are "pending" (CB10 §2.8 rule:
  `retry_wait`, re-queue under a new id after 48 tempfails; never "not run"). Only time-critical live checkpoints turn a
  disk refusal into a counted "unavailable (host disk)" unit.
- **Network etiquette.** Shared `Limiter` per process, collector yield (`live_pass_or_lock()`), 429 / `Retry-After`
  back-off, stop on repeated 429, collector-health stop. USGS, CBOE and Yahoo carry a descriptive User-Agent at ≤ 1 rps.
- **Stop rules.** 5 CPU-hours per family. A job that fails twice for the same non-transient reason stops and is
  recorded. A null is "not detected at MDE x". **No re-screen of a failed CB12 test** with altered origins, occasion
  rules, quote offsets, fill rules, models, catalogue rules, cutoffs, bandwidths, donuts, grids, horizons, bins,
  anchors, thresholds, windows or populations, on any data.

### 2.9 Funnel and Stage P

Screen (Stage 1) → gates, placebos, robustness → replication (Stage 2: sealed historical holdout for M and F;
out-of-time prospective for E; a second prospective window for O; none for X) → separate prospective confirmation
(Stage P) → economic validation at recorded prices with fees, spread and depth.
- **Stage P-M.** Mention events listed after the Stage P freeze; the M2 maker on **recorded** books (a CLOB `/book` read
  of every member at `t` with the touch and depth stored; quotes join the recorded ask, fills by later trade-through
  prints, queue position unknown and disclosed).
- **Stage P-F.** AL on the live large-trade monitor's prints (≥ $1k, 5-minute cadence, `A` since October) after the
  freeze, with the 2 h outcome; SH as a maker presence filter on book-sweep-recorded touches. Economic: a paper maker
  fade after broadcast prints at recorded books, depth recorded.
- **Stage P-E** = E2 itself (recorded asks), then a fresh window if it passes.
- **Stage P-X.** Pairs from the `cross_venue_live/` stream observed **after 2026-11-03T00:00Z only**, and only after
  both E009 and E010 final analyses are committed and their owner signs off; the X1 statistic with the same bins.
- **Stage P-O** = window 2 (O reps) and then a depth-aware fresh window.

---

## 3. Tests

### CB12-M: Mention-basket overpricing (CH112)

**Question.** In "what will X say / mention" events, does the sum of the members' YES prices two hours before the
scheduled start exceed the number of members that resolve YES, by enough for a basket maker to earn?

**Mechanism.** Each word is a cheap lottery ticket; longshot preference and salience lift each price, and the basket's
expected count is never traded as one object, so the sum reveals the tilt. The venue picks plausible words (which works
*against* the hypothesis). Who pays: retail buyers of word tickets. Why it persists: the basket view needs a join across
up to 35 markets, each thin.

**Prior work.** CH32 (per-word transcript base rates) was never tested. Longshot results elsewhere (C1 calibration: no
favourite-longshot pattern at 1 d) do not cover this class. M is not a re-screen of anything.

**Population (q0242; frozen).** Gamma closed events with tag id 100343 (`mention-markets`), event `endDate` in M SCREEN ∪
M HOLDOUT, ≥ 8 binary members, `startTime` present, key drops (M rule, §1.3). **Occasion rule (primary):** `endDate −
startTime ≤ 36 h` (a single speech, call, broadcast or game); **period baskets** (longer windows, probe 6) are counted
and reported uncounted, with no prices fetched. **No resolution-status filter**: status and outcomes are guarded; a
clean outcome vector gives `Y ∈ {0, 1}`, 50-50 gives 0.5, unresolved, voided or unclean members are scored 0.5 in the
primary (counted) with a binding worst-case check.
- **Start-time hindsight.** `startTime` is the value as fetched and may have been edited after a reschedule. Every M line
  carries **"L1, hindsight start time"**. Flag `start_edit` (frozen): `startTime` later than `endDate`, or `createdAt`
  later than `startTime − 26 h`, or the first transaction at or after `startTime` more than 6 h later (the occasion
  probably moved). A binding robustness check excludes flagged events. Stage P-M anchors on the start time recorded at
  `t`.

**Units.** An event `e` at `t = startTime − 2 h`. Members listed by `t − 1 h` (`createdAt`); members listed later are
dropped from both sums (counted); an event with < 8 listed members is excluded (counted). `p_i` = the member's
`prices-history` price at `t` (§2.2); the event is **available** iff ≥ 90% of its listed members have `p_i`; `S_e = Σ
p_i` and `N_e = Σ Y_i` over the same available members.

**M1 (basket calibration).** `D_e = S_e − N_e`; `D̄` = mean over SCREEN events (each event weight 1); one-sided > 0;
floors per §2.4.
- **Binding calibration placebo.** `Y*` from the GMP copula (`Z_i = √0.3·V_e + √0.7·ε_i`); 200 draws (seed 12101).
  *Alternative guarded:* within-event dependence (a long, on-message speech says many words) makes the clustered p
  anti-conservative.
- **Robustness (binding).** `t24` keeps the sign; **print-based sum** (each member's last transaction in `[t − 24 h, t)`,
  falling back to `p_i` where none; fallback share reported) keeps the sign and ≥ half; each SCREEN half keeps the sign;
  excluding `start_edit` events keeps p < 0.01 and the floor; unclean members scored `Y = 1` (worst case) keeps the sign;
  top-5 speaker and week drops.
- **Reported (uncounted).** The per-word calibration slope of `Y − p` on `p` (round 5's secondary); `D̄` by member price
  band (< 0.3, 0.3-0.6, > 0.6) with the label "longshot-carried" if the < 0.3 band holds ≥ 80% of `D̄`; splits by series
  age (CH51), speaker and basket size; period baskets (counts only).

**M2 (maker economic).** On every available member of every SCREEN event, a resting ask at `a_i = p_i + 1.5c` (§2.1),
capped at 0.99; filled iff a transaction with YES-terms price ≥ `a_i + 1c` occurs in `[t, startTime)` (trade-through;
fills stop at the scheduled start, so no in-speech fill); filled size min(100, that transaction's size). Net per filled
share `= a_i − Y_i`. Statistic: mean over events with ≥ 1 fill of the event's net per filled share (events without
fills counted); one-sided > 0; floors per §2.4.
- **Binding placebo (calibrated at fill).** `Y*_i` drawn calibrated to the **fill-time price** (the YES-terms price of
  the filling transaction) with the GMP copula; 200 draws (seed 12102). *Alternative guarded:* the trade-through fill
  rule selects fills after up-moves, so a maker could look profitable on mechanics alone; under "prices at fill time are
  calibrated" the maker's expected net is ≤ −1c and the placebo must not advance.
- **Robustness (binding).** §2.1 cost robustness; top-5 drops; `start_edit` exclusion; worst-case unclean `Y = 1`.
- **Reported.** The taker version (buy NO on each member at `1 − p_i + 1.5c` plus fee `0.04·a(1 − a)`); capacity (filled
  shares per event); the event-level loss distribution (the risk is a long speech).

**Power.** With about 300 SCREEN occasion events, SD(D) about 2 words (round 5) and a design effect of 1.5, `MDE_M1 ≈
3.17 x 2 x √(1.5/300) ≈ 0.45` words: the 0.3-word floor is below the MDE, so M1 detects about 0.45 words or more
(about 9% of a 5-word mean sum). M2: about 300 events x 5-10 fills, SD about 35c per filled share, event-clustered
design effect 2-3: MDE about 2-3c, so M2 detects only a large maker margin.

**Stage 2 (conditional).** M1-rep, M2-rep on the sealed HOLDOUT ends `[2026-03-01, 2026-10-01)`, same rules.

### CB12-F: Print footprints without wallets (CH110 + CH111, one fetch)

**Question.** (AL) Do transactions just above public alert thresholds draw copy flow and a larger continuation than
transactions just below? (SH) Is the numeric shape of a transaction (round-dollar vs not) a wallet-free origin
classifier that separates informed from uninformed flow?

**Mechanism.** AL: a $10,200 print is pushed to phones and copy apps; a $9,800 print is not; information is continuous
in size, so a jump at the cutoff isolates the broadcast. SH: the interface takes dollar amounts, so retail transactions
have round-dollar notionals and fractional shares, while programmatic orders have round shares and fractional
notionals; if the small flow-continuation effect (E007, HB1) is carried by non-round flow, a maker who steps aside when
non-round flow is heavy avoids most adverse selection. Both are side-free: the sign of a transaction is its price
impact.

**Prior work.** CH55 (copying by leaderboard wallet), CH37 (movers-list flow), CH93/CB10-B (round *price* levels), CH41
(farmer share by wallet tier), FL5 (small trades), CH69 (TWAP clips). No test has used notional shape or a notional
cutoff. Neither family re-tests the unconditional continuation (reported only).

**Population (q0246; frozen).** Gamma closed binary markets, scheduled end in `[2026-04-08, 2026-10-01)`, life
overlapping `[2026-04-01, 2026-10-01)` by ≥ 7 days, not sports, crypto, weather, Pyth dailies, strike ladders, Up/Down,
mention-markets or earthquake tags, key drops (full rule), ≤ 3 per event, `volumeNum ≥ $10k` (end-of-life volume: a
disclosed look-ahead in selection, as CB10-B and CB11-A, shared by every arm). **Strata (sampling only):** `[10k, 100k)`
700, `[100k, 1M)` 800, `≥ 1M` 900 markets, seeded (`arepo-cb12-prints-sample`); event split before any print read.
Statistics are unweighted across strata; stratum results are reported.

**Prints (q0247).** Newest-first `/trades` pages of 1,000 until a page's oldest print is before 2026-04-01 or the
20,000-print cap; transactions kept in the window; covered span recorded; a market is **fully covered** if the cap was
not hit before 2026-04-01 or before its first print.
- **Impact sign.** `s_τ = sign(v_τ − v_prev)`, `v_prev` = the previous transaction's YES-terms VWAP in the same market
  within 6 h; `s_τ = 0` or no predecessor → "unsigned" (excluded from signed statistics, counted). Prints inside the
  spread that did not move the price are thereby excluded (round 5's guard).
- **Truncation (disclosed).** For a market that hits the cap, a transaction is observed only if fewer than 20,000 prints
  followed it, which is selection on later activity. The selection is smooth in notional (so it cannot create a jump at
  $10k) and common to both shape classes at the same time, but it is not ignorable: every F advance must survive the
  binding **full-coverage-only** robustness check.

**AL (CH110).** Cutoffs `c ∈ {$10,000, $25,000}` (declared now from round 5; feed thresholds could not be verified
keylessly, a stated risk). Units: signed SCREEN transactions with notional `x ∈ [c − 2,000, c + 2,000]`, excluding the
donut `|x − c| < 50` (exactly-round notionals are CH111's retail mass), with ≥ 2 h of covered follow-up and the market
open ≥ 2 h after. Running variable `x` (transaction notional); local-linear fits on each side with a triangular kernel
and bandwidth $2,000; the two cutoffs' jumps are averaged with weights proportional to their in-band unit counts
(frozen at the census, counts only).
- **AL1 (copy flow).** Outcome `F15 = log(1 + Σ notional of transactions in (τ, τ + 15 min] with s = s_τ)`; jump at the
  cutoff, one-sided > 0; floor 0.10.
- **AL2 (continuation).** Outcome `R15 = 100 · s_τ · (P(τ + 15 min) − v_τ)` cents, `P(s)` = the last transaction price at
  or before `s`; jump one-sided > 0; floor 0.5c.
- **Binding placebo cutoffs.** The same estimator at $8,000, $12,000, $20,000, $30,000. **AL1/AL2 advance only if no
  placebo cutoff passes p < 0.01 in the positive direction and the real jump exceeds the largest placebo jump by ≥ half
  its floor.** *Alternative guarded:* a smooth nonlinearity in size, or heaping, mistaken for a threshold.
- **Binding calibration placebo.** Within each event, outcomes are permuted across in-band transactions; 200 draws
  (seeds 12103, 12104). *Alternative guarded:* within-event and within-day dependence makes the clustered RD p
  anti-conservative.
- **Robustness (binding).** Bandwidths $1,000 and $3,000 keep the sign; donut ±$200 keeps the sign; excluding
  transactions within $1 of a multiple of $100 keeps the sign; max-fill notional as the running variable keeps the sign;
  full-coverage markets only keeps the sign and ≥ half; each cutoff alone keeps the sign. Reported: the 2 h outcome; the
  follow-on transaction count; the jump by stratum.

**SH (CH111).** Shape classes per transaction, frozen: **R** round-dollar: the notional, in **either** the gross branch
(`Σ size x price`) or the fee-adjusted branch (gross + `r · Σ size x price x (1 − price)`, `r` = the market's
`feeSchedule.rate` at frame time, 0 if absent), within $0.01 of the grid {1, 2, 5, 10, 20, 25, 50, 100, 250, 500, 1,000}
or of a multiple of $100 above 1,000; **Q** round-share: total size within 0.01 of a multiple of 10 up to 100 or of 50
above; **B** both (excluded from both flows; the hour keeps its other transactions); **N** neither. **NR = Q ∪ N.** Fee
era = the market's `feeSchedule` present vs absent at frame time (reported; a binding check below).
- **SH1 (continuation by shape).** Unit = SCREEN market-hour `h` (UTC) with ≥ 1 signed transaction in the covered span.
  `F_k(h) = Σ_{τ ∈ h, class k} s_τ x notional_τ` for k ∈ {R, NR}. Base `P_b` = VWAP of transactions in `[h_end, h_end +
  10 min)`, else the first transaction in `[h_end, h_end + 60 min)`, else unavailable (a follower's entry, and no
  transaction of hour `h` sets it); target `M2h = 100 · (P(h_end + 2 h) − P_b)` cents with `P(s)` = VWAP in `[s − 30 min,
  s)`, else the last transaction before `s`. OLS `M2h = a + β_R z(F_R) + β_NR z(F_NR) + e` (z over SCREEN units).
  `Δβ = β_NR − β_R`, one-sided > 0; floor 0.15c.
- **SH2 (liquidity-provider mark-out by shape).** Unit = signed SCREEN transaction of class R or NR with a 60-min mark.
  `m_τ = −100 · s_τ · (P(τ + 60 min) − v_τ)` cents per share (the passive counterparty's gross). `Δm = mean_R(m) −
  mean_NR(m)`, one-sided > 0; floor 0.5c.
- **Binding placebo (both).** Within each market-day, shape labels are permuted across signed transactions (class shares
  kept); 200 draws (seeds 12105, 12106). *Alternative guarded:* within-market dependence and composition make the
  clustered p anti-conservative.
- **Attribution (binding for the label "origin, not size").** Round-dollar transactions are smaller. `Δβ` and `Δm`
  recomputed within notional quintiles (pooled over quintiles with in-quintile weights) must keep the sign and ≥ half;
  otherwise the advance stands with the label "a size effect, not shape".
- **Robustness (binding).** 6 h horizon (SH1) and 15 min mark (SH2) keep the sign; per-$1,000 slopes (SH1) and
  share-weighted means (SH2) keep the sign; each fee era keeps the sign; gross-branch-only classification keeps the sign;
  full-coverage markets only keeps the sign and ≥ half; top-5 drops; month rule.
- **Reported.** Shape shares by stratum, category, price band, hour and fee era; the unconditional continuation slope.

**Power.** AL: with about 4,000 in-band SCREEN transactions at $10k, SD(R15) about 2.5c, a local-linear variance
inflation of about 4 and a design effect of 1.3, the jump SE is about 0.29c and `MDE_AL2 ≈ 0.9c` (above the 0.5c
floor). AL1 has no prior SD; the census reports it. SH1: round 5's estimate (about 150,000 transactions) gives an MDE
of about 0.15c per SD, equal to the floor. SH2: with ≥ 20,000 R transactions, SD(m) about 3c and a design effect of 3,
`MDE_SH2 ≈ 3.17 x 3 x √(3/20,000 + 3/60,000) ≈ 0.13c`.

**Stage 2 (conditional).** Each advanced F test on the sealed HOLDOUT events, same rules.

### CB12-E: Earthquake running-count anchor (CH108, earthquake arm)

**Question.** Does a frozen catalogue model of earthquake counts predict how Polymarket earthquake markets resolve,
beyond their price?

**Mechanism.** The answer is a statistical function of a public catalogue: a long-run rate, an overdispersion, and the
count so far. The crowd may forget the base rate (underpricing YES where the model probability is high) or overreact
after a salient quake. Who pays: buyers after headlines. Why it persists: the join needs a catalogue model nobody on the
venue runs.

**Prior work.** None in AREPO (prior-work search). CH28 (scheduled sources) and CH75 (first print) are related ideas,
not tests of this class.

**Population (q0244; frozen).** Gamma closed events with tag 103038 or 100184 (union by event id), market `endDate` in
the E window, binary members whose question matches one of three frozen classes and whose description passes the frozen
rule parser (USGS named, magnitude threshold, ET window):
- **E-a count buckets:** "How many M or above earthquakes <window>?" (members are count buckets of one neg-risk event);
- **E-b threshold dates:** "Another M or above earthquake by <date>?" (members are date rungs);
- **E-c daily maximum:** "What will the biggest earthquake be on <date>?" (members are magnitude buckets).
Regional questions (6 of 553, probe 10) and unparsed rules are excluded (counted). Overlap drops (§1.3).

**Model (frozen; fitted only on catalogue events before 2024-09-01).** For magnitude threshold `m ∈ {6.0, 6.5, 7.0, 7.5,
8.0}`: monthly (30-day, non-overlapping) global counts 1976-01-01..2024-09-01 give the rate `λ_m` per day and a
negative-binomial size `k_m` by the method of moments (no declustering: the overdispersion carries the aftershock
clustering, which is what the markets count). For a remaining time `τ` days, `N_rem ~ NegBin(mean λ_m τ, size k_m τ/30)`
(variance-to-mean ratio held constant across horizons, a declared approximation). The count so far `c_t` = catalogue
events with magnitude ≥ `m`, origin inside the rule window and before `t − 72 h` (§2.2). Then:
- E-a: `q` (bucket) `= P(c_t + N_rem ∈ bucket)` with `τ` = window end − (`t − 72 h`);
- E-b: `q = 1 − P(N_rem = 0)` (a rung whose window already holds a usable event is "decided", excluded from E1, counted);
- E-c: `q` = the empirical probability that the ET-day maximum magnitude falls in the bucket, from ET days
  2000-01-01..2024-09-01 (M ≥ 4.5 catalogue; days with no M ≥ 4.5 event fall in the lowest bucket); checkpoints only
  before the day starts.

**Units.** (market, checkpoint) at 16:00Z daily while the market is listed (`createdAt` ≤ `t − 1 h`), at least 6 h
before its window end (E-c: before its day begins), not "ambiguous recent quake". Price `p_t` = `prices-history` price
at `t`; **`p_reg`** = the price at `t − 6 h` (a separate, earlier point; both by the §2.2 rule; CB10's shared-noise
design). Outcome `Y` = the catalogue answer to the frozen rule, computed by the parser from the guarded catalogue
accessor (never the Gamma field). Each market weight 1 across its checkpoints.

**E1 (forecasting).** OLS slope of `Y − p_t` on `q − p_reg`, market-weighted; one-sided > 0; floor 0.25.
- **Binding sign-flip calibration.** The sign of `q − p_reg` flipped by one coin per ISO week of the checkpoint (shared
  by every unit of the week; the event way uses one coin per event); 200 draws (seed 12107). *Alternative guarded:* one
  global process makes every open market move together, so the clustered p can be anti-conservative.
- **Binding independent-price placebo.** `q` replaced by `p_alt` = the price at `t − 48 h`. E1 credits the model only if
  the `p_alt` slope fails the p threshold **and** `β̂(q) − β̂(p_alt) ≥ 0.25`. *Alternative guarded:* a microstructure
  artefact of comparing a price with its own past.
- **Robustness (binding).** Top-5 event and week drops; each class (E-a; E-b and E-c pooled) keeps the sign; excluding
  checkpoints within 30 days after any M ≥ 7.5 event keeps the sign; each calendar half keeps the sign; the Gamma
  outcome (guarded; opened only here) in place of the catalogue outcome keeps the sign and ≥ half; 72 h → 7 d catalogue
  lag keeps the sign.
- **Reported.** Catalogue-vs-Gamma outcome agreement (< 97% → the label "rule ambiguity" on every E line); E1 by class
  and threshold; a Poisson (no overdispersion) variant.

**Power.** About 553 markets, 108 events, about 70 ISO weeks. With SD(Y − p) about 0.35, SD(q − p) about 0.07 and an
effective sample of 300-550 markets, the slope SE is about 0.2-0.3 and the MDE about 0.6-0.9, far above the 0.25 floor:
**E1 can detect only a large mispricing, and GEP (threshold 1.0) may stop it before it runs.** This is stated now.

**Stage 2 (conditional on an E1 advance; collection unconditional).** q0257 collects from the E freeze: daily at
16:00Z, the Gamma frame of open earthquake events, two `/book` reads per member (§2.2), the USGS events of the last 10
days (for `c_t` with the same 72 h rule; magnitudes as served at the read, which is now point-in-time). **E1-rep:** the
E1 statistic with `p_t` = the second book's mid and `p_reg` = the first read's mid 6 h earlier... (the previous day's
second read is too old; `p_reg` = the mid of the first read at the same checkpoint, a separate measurement ≥ 60 s
earlier, disclosed as weaker than the 6 h rule), on markets whose windows end in `[T12_E2_start, T12_E2_end)`. **E2:**
at each market's first checkpoint with `|q − a| ≥ 8c` on the favoured side (`a` = that side's recorded ask), buy at `a`
(depth recorded, size ≤ displayed), fee `r·a(1 − a)`, hold to resolution, payoff from the Gamma outcome (what pays);
net per share ≥ 1.0c; robustness +0.5c. If E1 does not advance, the collected data are not analysed (recorded).

### CB12-X: Horizon-dependent staleness on the audited pairs (CH115)

**Question.** Does the cross-venue gap close more slowly when the Polymarket market's scheduled end is far away?

**Mechanism.** Correcting a 3c gap in a market that resolves in a year earns under 3% a year; in a two-day market it is
hundreds of percent. If capital lock-up binds, the gap half-life rises with time to resolution. X is a hunting rule:
it tells every anchor route where the lead lasts long enough to act at AREPO's cadence.

**Prior work and reuse.** The pooled half-life (66 min) and the lead are known on this set; CB5-K reads it for hour
moderation. The horizon cut is new (§1.1). **Label: "L1, worn set, new moderator".**

**Population (q0251; frozen).** The C1 set reproduced in code exactly as CB5-K does (`run_cross_venue.load_pair_series
(cv.POINT_LAG_S)` and `audit_sets(...)["rule"]`; source sha256 pinned): 316 pairs, 183 events, 517,616 usable steps,
the study's window (up to 30 days before the earlier resolution) and alignment (§2.2). Horizon `τ(t) = endDate_PM − t`,
`endDate_PM` from `matches.json` if present, else from `poly_markets.json` by streaming field-restricted read (ids and
`endDate` only). Edit flag: `|endDate_PM − Kalshi scheduled close| > 7 d` (Kalshi field from the pinned
`kalshi_markets*.jsonl`, field-restricted). Bins per §1.2.

**Statistic.** Per pair, demeaned gap `g̃_t = g_t − mean_pair(g)`, `g = p_K − p_PM` (round 5: demeaned per pair, so a
persistent level gap is not read as staleness; the demeaning uses the pair's whole window, which is acceptable for a
dynamics descriptive with no trading rule and is applied identically in every bin; a causal variant is a robustness
check). Pooled AR(1) on consecutive usable step pairs within bin b: `g̃_{t+1} = ρ_b g̃_t + e`; `HL_b = 10 min x ln 2 /
(−ln ρ_b)` (`ρ_b ≥ 1` → `HL_b = ∞`, reported, and the bootstrap uses the capped `HL = 7 d`). Each step pair is assigned
the bin of its first step.

**X1.** `HL_long − HL_short`, one-sided > 0; floor 60 min; p = max over the event and resolution-month ways.
- **Binding horizon-offset placebo.** For each pair, `δ = endDate_PM − t_res` (scheduled end minus the earlier actual
  resolution); `δ` is permuted across pairs within category; `τ` is recomputed as `(t_res − t) + δ_perm`; X1
  recomputed; 200 draws (seed 12108). *Alternative guarded:* the contrast is life-cycle (closeness to the actual
  resolution, which the window construction ties to every step) or category composition, not scheduled horizon. **If
  scheduled horizon and life-cycle are collinear in C1, this placebo advances and X1 cannot advance: that outcome is
  "not identifiable", by design.**
- **Robustness (binding).** Within Sports and within Elections separately (each with ≥ 10 pairs in both bins) the sign
  holds; within ≥ 2 of 3 PM-volume terciles (end-of-life volume from `poly_markets.json`; a look-ahead stratum,
  disclosed) the sign holds; causal demeaning (rolling 3-day past mean) keeps the sign and ≥ half; steps with `|g| ≥ 3c`
  keep the sign; excluding edit-flagged pairs keeps the sign; top-5 event drops.
- **Reported (uncounted).** `HL_mid`; lag-1 to lag-12 cross-correlations by bin; gap size by bin and category; the
  Polymarket adjustment share by bin.

**Power.** Not estimable before the census (the long bin's size is unknown; GX decides). The pooled HL's CI (48-86 min
on 183 events) suggests a per-bin SE of 30-50 min and a contrast MDE of 130-200 min: X1 detects only the hours-scale
staleness CH115 predicts, not a modest gradient.

**E009/E010 guard.** X reads only the 2026-10-12 historical files (probe 13), never `cross_venue_live/`, and no step at
or after `T12_X_end`; it changes nothing in E009's frozen coefficients or E010's registration and makes no interim look.

### CB12-O: Option-chain digital anchor for equity strike markets (CH99), prospective only

**Question.** Does the digital probability implied by the listed option chain predict how Polymarket "close above $K"
equity markets resolve, beyond their book mid, and does buying the anchor side when they disagree by ≥ 4c pay?

**Mechanism.** The strike market's fair value is a digital option; listed options price exactly that with professional
makers; the Polymarket crowd does not. Who pays: buyers of "close above" lottery tickets after a morning move.

**Prior work.** CB10-D (Deribit anchor for crypto ladders) and CB9-P (lognormal from hourly bars on Up/Down dailies) are
the parents; strike markets are in no batch. O reads no CB9 or CB10 data. O's units share underlyings and sessions with
CB9-P's Stage-2 sessions: an O result and a CB9-P result are **not independent evidence** about equity dailies.

**Population (frozen in `seals/cb12_opt_rules.json` before q0260).** At each checkpoint, open Gamma events whose title
matches `^Will .+ \(([A-Z.]{1,6})\) close above ___ (on .+|end of [A-Z][a-z]+)\?$` (and the daily variant the smoke
records), members binary with a parsed strike `K` and settlement date `d`, rule text flags frozen from the smoke's live
read (named price source: Pyth or the official exchange close; final regular-session close; exactly-equal clause),
underlying with a CBOE chain (`<TICKER>.json`; indices `_SPX`/`_NDX` where named).

**Anchor (frozen).** If a listed expiry equals `d`: `q = (C(K_lo) − C(K_hi)) / (K_hi − K_lo)` from call mids (both bid
and ask > 0) at the adjacent listed strikes bracketing `K`, clipped to [0, 1]; otherwise `q = Φ(d2)` with the iv
interpolated linearly in strike at `K` from the nearest expiry ≥ `d`, spot = the chain's underlying price, `r = 0`, time
= remaining regular-session hours to `d`'s close / (252 x 6.5). Exclusions (counted): `q < 0.05` or `> 0.95`; either
option's spread > 10% of its mid; an ex-dividend date in `(t, d]` (from the chain's own data if present, else unknown →
excluded); earnings flagged from Nasdaq's public earnings calendar if the smoke verifies it keyless, else "earnings not
identified" and the primary includes all (disclosed).

**Units.** (market, checkpoint); chain read first, then two `/book` reads ≥ 60 s apart; **tight** iff both touches
present and spread ≤ 4.5c in the first read. `m1`, `m2` = the mids of the first and second reads. Outcome `Y` = sign of
the settlement-date close vs `K` from the public daily bar (Yahoo chart, fetched ≥ 1 day after `d`; equal = 0.5),
guarded; agreement with the Gamma outcome reported (< 97% → the label "settlement basis").

**O1 (forecasting).** OLS slope of `Y − m2` on `q − m1` over tight window-1 units (each (underlying, settlement) cluster
weight 1); one-sided > 0; floor 0.30. Using two separate book reads keeps the target's and the regressor's book noise
apart (CB10's shared-noise rule; persistent quotes make the reads correlated, disclosed).
- **Binding sign-flip calibration.** One coin per settlement date flips `q − m1`; 200 draws (seed 12109).
- **Attribution (binding for the label "option-implied").** `q_RV` = the same digital with σ = 20-day realised vol of
  daily closes (Yahoo bars before `t`); joint OLS; credit only if the coefficient on `q − m1` keeps ≥ half its solo
  value; if `cor(q − m1, q_RV − m1) > 0.9` at the census, the label is "not identifiable".
- **Robustness (binding).** Direct-digital units only keep the sign; each checkpoint time keeps the sign; excluding
  earnings units (if identified) keeps the sign; top-5 drops.

**O2 (economic).** At each market's first tight checkpoint with `q − a_YES ≥ 4c` (buy YES at `a_YES`) or `(1 − q) −
a_NO ≥ 4c` (buy NO at `a_NO = 1 − b_YES`), size ≤ displayed touch size, fee, hold to settlement: `net = Y_k − a − fee`;
one-sided > 0; floor 1.0c; robustness +0.5c. **Binding placebo:** the same rule with `q` replaced by `m_prev` (the mid
two hours earlier) must not pass p < 0.01 (*alternative guarded:* a reversal of the book mid, not the option
information, drives the net).

**Power.** Probe 12 shows about 12 underlyings x 11-13 strikes on month-end ladders; each (underlying, settlement) is
one outcome draw, so window 1 runs to 60 clusters (about 3-4 months if only month-end ladders exist; weeks if daily
strike events are listed). With 60 clusters, SD(Y − m) about 0.45 and SD(q − m) about 0.08, the slope MDE is about 0.5;
the 0.30 floor is below it.

**Stage 2 (conditional).** O1-rep, O2-rep on window 2.

### CB12-S and data jobs

- **q0240 smoke** (PASS needs): rules hash; the guarded accessors and refusals (fixtures: HOLDOUT, `cross_venue_live`,
  steps ≥ `T12_X_end`, catalogue events at or after `t − 72 h` in a census path); Gamma tag 100343 paging on two
  out-of-window weeks (2025-05) stable on repeat, `startTime` present; the frozen E title classes and rule parser on 3
  out-of-window earthquake events (ends after 2026-10-01), parse success recorded; USGS count and query (1976 rate
  query returns ≤ 20,000 rows); `prices-history` with explicit bounds on 2 out-of-window markets; Data API newest-first
  reach on 2 out-of-window markets; **decoding check (F):** 50 seeded transactions from out-of-window markets (after
  2026-10-01): Data API aggregated notional vs the on-chain `OrderFilled` USDC amounts from `eth_getTransactionReceipt`
  on a public Polygon RPC (hashes in memory only); PASS iff ≥ 80% agree within $0.01 under the gross or the fee-adjusted
  branch (the share per branch recorded); FAIL → SH1 and SH2 "not testable (decoding)", AL unaffected; the X input
  sha256s and the C1 reproduction (316 pairs, 183 events, 517,616 steps exactly). Any other failure → the dependent
  family "not testable (source)", counted; no rule is re-fitted.
- **q0260 O smoke** (one live checkpoint): Gamma frame regex hits, rule-text flags, CBOE chain per underlying with
  `timestamp`, `/book` reads, Nasdaq earnings calendar keyless check; no unit kept.
- Every data job writes a manifest (file sha256, request counts, failures, data-dumps size and margin, free disk) and a
  `*_complete` status.

## 4. Jobs (draft specs; JSON in this document only)

Fields follow `queue/README.md`; `argv[0]` is under `backend/scripts/`, `cwd` is `backend`. **None is written to
`queue/jobs/` or `queue/drafts/`** before its code and tests exist and pass a `science-reviewer` freeze check;
analysis jobs also need their family's freeze. All `family` = `creative_batch_12`. Priorities: `net` 20-24 (below
CB11's 25-29); `cpu` 20-24.

| Id | Lane | Priority | Size / time | Depends on | Commit when |
|---|---|---|---|---|---|
| q0240 | cpu | 24 | ≤ 60 req + ≤ 60 RPC at ≤ 1 rps, < 10 min, mem 300 | - | rules file + smoke code reviewed |
| q0241 | net | 24 | ≤ 600 req, ≤ 6 min, mem 500 | q0240, CB11 q0221 | with q0240's PASS |
| q0242 | net | 23 | ≤ 150 req, ≤ 3 min, mem 300 | q0241 | with q0241 |
| q0243 | net | 23 | ≤ 28,000 req, about 3.9 h, mem 400 | q0242 | with q0242 |
| q0244 | net | 23 | ≤ 40 req, ≤ 2 min, mem 400 | q0241 | with q0241 |
| q0245 | net | 23 | ≤ 2,000 req, ≤ 20 min, mem 300 | q0244 | with q0244 |
| q0246 | net | 22 | ≤ 1,200 req, ≤ 12 min, mem 300 | q0241 | with q0241 |
| q0247 | net | 22 | ≤ 24,000 req, about 2.5-3.5 h, mem 500 | q0246 | with q0246 |
| q0265 | net | 20 | ≤ 120 req, ≤ 2 min, mem 200 | q0240 | any time after q0240 |
| q0251 | cpu | 24 | no network, ≤ 30 min, mem 900 | q0240 | with q0240 (can run while CB11 holds the `net` lane) |
| q0248 | cpu | 22 | light, mem 300 | q0243 (M), q0247 (F) | per family as its fetch completes |
| q0249 | cpu | 22 | ≤ 30 min, mem 600 | q0243, q0245, q0248 (M seal) | after the M seal copy is committed |
| q0250 | cpu | 22 | ≤ 45 min, mem 900 | q0247, q0248 (F seal) | after the F seal copy is committed |
| q0252-q0255 | cpu | 21 | M ≤ 20 min, E ≤ 30 min, F ≤ 2 CPU-h, X ≤ 1 CPU-h; mem ≤ 900 | census of the family | after the family's freeze |
| q0256, q0259 | cpu | 20 | ≤ 1 CPU-h each | q0252 / q0254 | only if the family's Stage 1 advanced |
| q0257 | cron | - | ≤ 200 req/day, ≤ 3 min | E freeze | with the E freeze (orchestrator installs the cron line) |
| q0258 | cpu | 20 | ≤ 20 min | q0253 advance, `T12_E2_end` + 2 d | only if E1 advanced |
| q0260 | cpu | 21 | ≤ 450 req, one checkpoint, mem 300 | O rules file | O rules + smoke code reviewed |
| q0261 | cron | - | ≤ 450 req per checkpoint, ≤ 5 min | O freeze | with the O freeze (orchestrator installs the cron line) |
| q0262-q0264 | cpu | 20 | ≤ 20 min each | window 1 / window 2 close | per §0.1 |

```json
{"id": "q0240_cb12_smoke", "title": "CB12: smoke (rules hash; guarded accessors and refusals incl. cross_venue_live and T12_X_end fixtures; Gamma tag 100343 paging on 2 out-of-window weeks with startTime; E title classes + rule parser on 3 out-of-window earthquake events; USGS count/query; prices-history bounds on 2 out-of-window markets; Data API reach on 2; F decoding check on 50 out-of-window transactions vs Polygon receipts (gross or fee-adjusted branch, >= 80%); X input sha256s and exact C1 reproduction 316/183/517,616); counts only", "family": "creative_batch_12", "priority": 24, "expected_value": "go/no-go for every CB12 source", "data": ["public Gamma, CLOB prices-history, Data API", "USGS FDSN", "public Polygon JSON-RPC (receipts by hash)", "research_lab/cross_venue/ (pinned files, read-only)"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu", "network": "gamma-api, clob, data-api, earthquake.usgs.gov, polygon rpc"}, "depends_on": [], "argv": ["scripts/run_cb12.py", "smoke", "--rules", "../docs/research_lab/seals/cb12_rules.json", "--rps", "1"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch12/smoke.json", "trials.jsonl (cb12_descriptive)"], "next_action": "PASS: q0241, q0251, q0265; FAIL: dependent family not testable (source), counted", "notes": "CREATIVE_BATCH_12.md CB12-S. DRAFT. <= 60 requests + <= 60 RPC reads. No hash, wallet or side stored."}
{"id": "q0241_cb12_exclusion_keys", "title": "CB12: exclusion keys = CB11 q0221 key file + id columns of h9_flow, h10_sign, h10_dlad, h10_brk, h11_wprints, h11_pol, h11_attn, CB8/CB9 frames + seal copies + C1 pair Polymarket market/event ids; Gamma lookups for missing event/negRisk/series keys", "family": "creative_batch_12", "priority": 24, "expected_value": "disjointness of M, E and F", "data": ["creative_batch11/exclusion_keys.csv.gz", "history/*/ (id columns only)", "docs/research_lab/seals/*", "research_lab/cross_venue/matches.json (ids only)", "public Gamma (ids)"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0240_cb12_smoke", "q0221_cb11_exclusion_keys"], "argv": ["scripts/run_cb12.py", "exclusion-keys", "--rules", "../docs/research_lab/seals/cb12_rules.json", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 2400, "max_retries": 2, "outputs": ["research_lab/creative_batch12/exclusion_keys.csv.gz", "manifest.json (absent_at_q0241 list)"], "next_action": "q0242, q0244, q0246", "notes": "DRAFT. >2% missing metadata -> disjointness unverified (family not testable, counted). Exit 75 on headroom = pending."}
{"id": "q0242_cb12_say_frame", "title": "CB12-M: Gamma closed events tag_id=100343, endDate [2025-06-01,2026-10-01), >= 8 binary members, startTime present; occasion rule (endDate - startTime <= 36 h) vs period baskets (counted only); M key rule (market, event, series-date +-1 d); start_edit flags; out-of-time split at 2026-03-01; outcomes and umaResolutionStatus to the guarded file", "family": "creative_batch_12", "priority": 23, "expected_value": "M population, flags and split", "data": ["public Gamma", "creative_batch12/exclusion_keys.csv.gz"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0241_cb12_exclusion_keys"], "argv": ["scripts/run_cb12.py", "say-frame", "--rules", "../docs/research_lab/seals/cb12_rules.json", "--rps", "2", "--disk-cap-gb", "0.005", "--data-dumps-cap-gb", "40"], "timeout_s": 1800, "max_retries": 2, "outputs": ["history/h12_say/{events.csv.gz,members.csv.gz,split.json,flags.csv.gz,outcomes_guarded.csv.gz,manifest.json}"], "next_action": "q0243", "notes": "DRAFT. No price read. Capped windows split until uncapped (counted)."}
{"id": "q0243_cb12_say_prices", "title": "CB12-M: per occasion member, CLOB prices-history [startTime-26h, startTime] fidelity 10 (prices at t-2h and t-24h by the stamp+600s rule); Data API newest-first prints (<= 2 pages) aggregated to transactions in [startTime-26h, startTime) plus the first transaction at/after startTime; HOLDOUT rows to holdout/", "family": "creative_batch_12", "priority": 23, "expected_value": "M1/M2 inputs", "data": ["public CLOB prices-history, Data API", "history/h12_say/members.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "clob, data-api"}, "depends_on": ["q0242_cb12_say_frame"], "argv": ["scripts/run_cb12.py", "say-prices", "--rules", "../docs/research_lab/seals/cb12_rules.json", "--rps", "2", "--disk-cap-gb", "0.08", "--data-dumps-cap-gb", "40", "--budget-min", "110"], "timeout_s": 7200, "max_retries": 2, "outputs": ["history/h12_say/{screen,holdout}/{prices.csv.gz,tx.csv.gz}", "manifest.json"], "next_action": "q0248 (M seal)", "notes": "DRAFT. <= 28,000 requests (about 3.9 h). No outcome read. Resumable; incomplete = pending, never analysed partially.", "repeat": {"max_runs": 4, "until_log_regex": "\"status\": \"say_prices_complete\""}}
{"id": "q0244_cb12_quake_frame", "title": "CB12-E: Gamma closed events tag 103038 or 100184 (union), endDate [2024-09-01,2026-10-01); frozen title classes E-a/E-b/E-c and rule parser (window, threshold, USGS, ET); overlap exclusion; USGS catalogue M>=6.0 1976-2026 and M>=4.5 2000-2026 (time, lat, lon, mag, magType, status, updated); Gamma outcomes to the guarded file; catalogue behind the guarded accessor for census paths", "family": "creative_batch_12", "priority": 23, "expected_value": "E population, model inputs", "data": ["public Gamma", "USGS FDSN event API", "creative_batch12/exclusion_keys.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api, earthquake.usgs.gov"}, "depends_on": ["q0241_cb12_exclusion_keys"], "argv": ["scripts/run_cb12.py", "quake-frame", "--rules", "../docs/research_lab/seals/cb12_rules.json", "--rps", "2", "--usgs-rps", "1", "--disk-cap-gb", "0.03", "--data-dumps-cap-gb", "40"], "timeout_s": 1800, "max_retries": 2, "outputs": ["history/h12_quake/{events.csv.gz,members.csv.gz,rules_parsed.csv.gz,catalogue.csv.gz,outcomes_guarded.csv.gz,manifest.json}"], "next_action": "q0245", "notes": "DRAFT. Model constants are fitted later from catalogue rows before 2024-09-01 only (unit test). No price read."}
{"id": "q0245_cb12_quake_prices", "title": "CB12-E: CLOB prices-history per earthquake member over its listed life (fidelity 60, <= 14-day bounded chunks), for p_t, p_reg (t-6h) and p_alt (t-48h) at daily 16:00Z checkpoints", "family": "creative_batch_12", "priority": 23, "expected_value": "E1 prices", "data": ["public CLOB prices-history", "history/h12_quake/members.csv.gz"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "net", "network": "clob"}, "depends_on": ["q0244_cb12_quake_frame"], "argv": ["scripts/run_cb12.py", "quake-prices", "--rules", "../docs/research_lab/seals/cb12_rules.json", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 2400, "max_retries": 2, "outputs": ["history/h12_quake/prices.csv.gz", "manifest.json"], "next_action": "q0249", "notes": "DRAFT. <= 2,000 requests.", "repeat": {"max_runs": 2, "until_log_regex": "\"status\": \"quake_prices_complete\""}}
{"id": "q0246_cb12_prints_frame", "title": "CB12-F: Gamma closed binary markets, scheduled end [2026-04-08,2026-10-01), life overlap >= 7 d, not sports/crypto/weather/Pyth/ladders/Up-Down/mention/earthquake tags, full key drops, <= 3 per event, volume strata [10k,100k) 700 / [100k,1M) 800 / >=1M 900 seeded (arepo-cb12-prints-sample); event split SCREEN/HOLDOUT (arepo-cb12-prints-split)", "family": "creative_batch_12", "priority": 22, "expected_value": "F population and split", "data": ["public Gamma", "creative_batch12/exclusion_keys.csv.gz"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0241_cb12_exclusion_keys"], "argv": ["scripts/run_cb12.py", "prints-frame", "--rules", "../docs/research_lab/seals/cb12_rules.json", "--rps", "2", "--disk-cap-gb", "0.005", "--data-dumps-cap-gb", "40"], "timeout_s": 2400, "max_retries": 2, "outputs": ["history/h12_prints/{frame.csv.gz,split.json,manifest.json}"], "next_action": "q0247", "notes": "DRAFT. volumeNum used in memory for the stratum label only, never stored. No outcome field parsed."}
{"id": "q0247_cb12_prints_fetch", "title": "CB12-F: Data API newest-first prints (pages of 1000 until oldest < 2026-04-01 or the 20,000 cap) for 2,400 markets, aggregated by transaction hash to (time, YES-terms VWAP, size, notional, fee-adjusted notional, n_fills, max-fill notional) in [2026-04-01,2026-10-01); covered span and full-coverage flag; HOLDOUT to holdout/", "family": "creative_batch_12", "priority": 22, "expected_value": "AL/SH transactions", "data": ["public Data API", "history/h12_prints/frame.csv.gz"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "net", "network": "data-api"}, "depends_on": ["q0246_cb12_prints_frame"], "argv": ["scripts/run_cb12.py", "prints-fetch", "--rules", "../docs/research_lab/seals/cb12_rules.json", "--rps", "2", "--disk-cap-gb", "0.5", "--data-dumps-cap-gb", "40", "--budget-min", "110"], "timeout_s": 7200, "max_retries": 2, "outputs": ["history/h12_prints/{screen,holdout}/tx.csv.gz", "manifest.json"], "next_action": "q0248 (F seal)", "notes": "DRAFT. <= 24,000 requests (about 2.5-3.5 h). No side, wallet, name or hash stored. Incomplete = pending.", "repeat": {"max_runs": 3, "until_log_regex": "\"status\": \"prints_fetch_complete\""}}
{"id": "q0248_cb12_seal", "title": "CB12: HOLDOUT listings sha256 for M (h12_say/holdout) and F (h12_prints/holdout) as each fetch completes; seal-time drops vs every seal copy and frame committed by now (incl. CB11 frames absent at q0241); seal copies seals/cb12_{say,prints}_holdout_SEAL.json", "family": "creative_batch_12", "priority": 22, "expected_value": "sealed holdouts", "data": ["history/h12_say/holdout/", "history/h12_prints/holdout/"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0243_cb12_say_prices"], "argv": ["scripts/run_cb12.py", "seal", "--family", "auto"], "timeout_s": 1800, "max_retries": 2, "outputs": ["research_lab/creative_batch12/holdout_SEAL_<family>.json"], "next_action": "commit the seal copies; q0249 (M, E) / q0250 (F)", "notes": "DRAFT. Exits 75 (pending) for a family still fetching and re-runs. Sealed files never edited; drops recorded as DROPPED_* blocks.", "repeat": {"max_runs": 6, "until_log_regex": "\"status\": \"seal_all_complete\""}}
{"id": "q0249_cb12_census_ME", "title": "CB12-M and CB12-E census, counts only (M: events, occasion/period, members, availability, flags, key drops incl. full-series counterfactual, GM, coverage audit, GMP power gate; E: classes, parser failures, ambiguous-quake units, overlap drops, labels, GE, GEP power gate; MDEs)", "family": "creative_batch_12", "priority": 22, "expected_value": "M and E gates and MDEs before the freeze", "data": ["history/h12_say/screen (no guarded file; HOLDOUT counts only)", "history/h12_quake (catalogue via the t-72h accessor only)"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0243_cb12_say_prices", "q0245_cb12_quake_prices", "q0248_cb12_seal"], "argv": ["scripts/run_cb12.py", "census", "--family", "M,E"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch12/census_ME.json", "trials.jsonl (cb12_descriptive)"], "next_action": "science-reviewer freeze check (M, E parts)", "notes": "DRAFT. No outcome, D, slope or net computed. Refuses on an incomplete manifest."}
{"id": "q0250_cb12_census_F", "title": "CB12-F census, counts only (strata, coverage, signed share, shape classes by stratum/band/era, decoding result, GAL, GS15, GSH, coverage audit incl. full-coverage subset, AL cutoff weights; MDEs)", "family": "creative_batch_12", "priority": 22, "expected_value": "F gates and MDEs before the freeze", "data": ["history/h12_prints/screen (HOLDOUT counts only)"], "resources": {"mem_mb": 900, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0247_cb12_prints_fetch", "q0248_cb12_seal"], "argv": ["scripts/run_cb12.py", "census", "--family", "F"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch12/census_F.json", "trials.jsonl (cb12_descriptive)"], "next_action": "science-reviewer freeze check (F part)", "notes": "DRAFT. No follow-on flow, later price, jump, slope or mark-out computed. mem 900 justified (section 2.8)."}
{"id": "q0251_cb12_x_census", "title": "CB12-X census, counts only, on host files (C1 reproduction; endDate by streaming field-restricted read; edit flag; usable consecutive step pairs by horizon bin x category x PM-volume tercile; GX)", "family": "creative_batch_12", "priority": 24, "expected_value": "X gate before the freeze", "data": ["research_lab/cross_venue/{series/*.npz,matches.json,audit_flags.json,audit_sample100.json,poly_markets.json,kalshi_markets*.jsonl} (pinned, read-only)"], "resources": {"mem_mb": 900, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0240_cb12_smoke"], "argv": ["scripts/run_cb12.py", "census", "--family", "X"], "timeout_s": 2400, "max_retries": 1, "outputs": ["research_lab/creative_batch12/census_X.json", "trials.jsonl (cb12_descriptive)"], "next_action": "science-reviewer freeze check (X part)", "notes": "DRAFT. Refuses cross_venue_live and any step >= 2026-10-12T00:00Z. No gap, rho or half-life computed."}
{"id": "q0252_cb12_screen_M", "title": "CB12-M: M1 (basket excess; calibrated-outcome copula placebo; t-24h, print-sum, halves, start_edit, worst-case robustness) and M2 (trade-through maker; fill-time calibrated placebo; cost robustness) on SCREEN events; batch Holm k1=10 at alpha/k1 if early", "family": "creative_batch_12", "priority": 21, "expected_value": "M verdicts", "data": ["history/h12_say/screen + outcomes_guarded (opened here)"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0249_cb12_census_ME"], "argv": ["scripts/run_cb12.py", "screen", "--family", "M"], "timeout_s": 2400, "max_retries": 1, "outputs": ["research_lab/creative_batch12/results_M.json", "trials.jsonl (cb12_test + creative_batch_12:M n_tests=2)"], "next_action": "advanced: commit q0256", "notes": "DRAFT. Refuses before the M freeze hash and on any HOLDOUT row; refuses unless GM, GMP and the coverage audit passed (else writes the counted lines). Every line labelled 'L1, hindsight start time'."}
{"id": "q0253_cb12_screen_E", "title": "CB12-E: E1 (slope of Y-p_t on q-p_reg, catalogue outcome; week sign-flip placebo; p_alt independent-price placebo; class, aftershock, halves, Gamma-outcome, 7-day-lag robustness; agreement audit)", "family": "creative_batch_12", "priority": 21, "expected_value": "E1 verdict", "data": ["history/h12_quake + outcomes_guarded (opened here)"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0249_cb12_census_ME"], "argv": ["scripts/run_cb12.py", "screen", "--family", "E"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch12/results_E.json", "trials.jsonl (cb12_test + creative_batch_12:E n_tests=1)"], "next_action": "advanced: arm q0258 for T12_E2_end", "notes": "DRAFT. Refuses unless GE and GEP passed (else counted not-run/not-testable line)."}
{"id": "q0254_cb12_screen_F", "title": "CB12-F: AL1, AL2 (stacked local-linear RD at $10k/$25k, donut, placebo cutoffs, within-event permutation; bandwidth, donut, round-100, max-fill, full-coverage robustness) and SH1, SH2 (shape slope and mark-out differences; label permutation; size-quintile attribution; era, branch, horizon, full-coverage robustness) on SCREEN events", "family": "creative_batch_12", "priority": 21, "expected_value": "F verdicts", "data": ["history/h12_prints/screen"], "resources": {"mem_mb": 900, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0250_cb12_census_F"], "argv": ["scripts/run_cb12.py", "screen", "--family", "F"], "timeout_s": 7200, "max_retries": 1, "outputs": ["research_lab/creative_batch12/results_F.json", "trials.jsonl (cb12_test + creative_batch_12:F n_tests=4)"], "next_action": "advanced: commit q0259", "notes": "DRAFT. Refuses to open holdout/; refuses unless GAL / GS15 / GSH / decoding / coverage passed per test (else counted lines)."}
{"id": "q0255_cb12_screen_X", "title": "CB12-X: X1 (HL_long - HL_short on pair-demeaned gaps; horizon-offset placebo within category; sports/elections strata, volume terciles, causal demeaning, |g|>=3c, edit-flag, top-5 robustness); label 'L1, worn set, new moderator'", "family": "creative_batch_12", "priority": 21, "expected_value": "X1 verdict", "data": ["research_lab/cross_venue/ (pinned, read-only)"], "resources": {"mem_mb": 900, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0251_cb12_x_census"], "argv": ["scripts/run_cb12.py", "screen", "--family", "X"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch12/results_X.json", "trials.jsonl (cb12_test + creative_batch_12:X n_tests=1)"], "next_action": "advanced: draft Stage P-X (after 2026-11-03 and E009/E010 final analyses only)", "notes": "DRAFT. Refuses cross_venue_live; refuses unless GX passed."}
{"id": "q0256_cb12_rep_M", "title": "CB12-M: M1-rep and/or M2-rep on sealed HOLDOUT ends [2026-03-01,2026-10-01)", "family": "creative_batch_12", "priority": 20, "expected_value": "L2 verdicts", "data": ["history/h12_say/holdout + outcomes_guarded"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0252_cb12_screen_M"], "argv": ["scripts/run_cb12.py", "rep", "--family", "M"], "timeout_s": 2400, "max_retries": 1, "outputs": ["research_lab/creative_batch12/results_M_rep.json", "trials.jsonl (cb12_replication + creative_batch_12:M:rep)"], "next_action": "pass: Stage P-M registration draft", "notes": "DRAFT. Only for advanced tests; verifies the seal hash first."}
{"id": "q0257_cb12_quake_live", "title": "CB12-E Stage 2 collector (cron 16:00Z daily, outside the queue lanes): Gamma frame of open earthquake events (tags 103038/100184), two receipt-timed CLOB /book reads per member >= 60 s apart, USGS events of the last 10 days as served at the read", "family": "creative_batch_12", "priority": 0, "expected_value": "E1-rep and E2 inputs", "data": ["public Gamma, CLOB /book", "USGS FDSN"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cron", "network": "gamma-api, clob, earthquake.usgs.gov"}, "depends_on": [], "argv": ["scripts/run_cb12.py", "quake-live", "--rules", "../docs/research_lab/seals/cb12_rules.json", "--rps", "1", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 600, "max_retries": 0, "outputs": ["history/h12_quake_live/<date>.json.gz"], "next_action": "runs until T12_E2_collect_max", "notes": "DRAFT. Installed by the orchestrator as one crontab line after the E freeze; collection unconditional, analysis only if E1 advanced. A missed day is 'unavailable (collection)', never back-filled."}
{"id": "q0258_cb12_rep_E", "title": "CB12-E: E1-rep (out-of-time prospective, recorded mids) and E2 (economic at recorded asks, |q - a| >= 8c, depth recorded, held to resolution) on windows ending [T12_E2_start, T12_E2_end)", "family": "creative_batch_12", "priority": 20, "expected_value": "L2 verdicts", "data": ["history/h12_quake_live", "Gamma outcomes after resolution (guarded)"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0253_cb12_screen_E"], "argv": ["scripts/run_cb12.py", "rep", "--family", "E"], "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch12/results_E_rep.json", "trials.jsonl (cb12_replication + creative_batch_12:E:rep)"], "next_action": "pass: Stage P-E fresh window", "notes": "DRAFT. Only if E1 advanced; after T12_E2_end + 2 d."}
{"id": "q0259_cb12_rep_F", "title": "CB12-F: advanced AL/SH tests on sealed HOLDOUT events, same rules", "family": "creative_batch_12", "priority": 20, "expected_value": "L2 verdicts", "data": ["history/h12_prints/holdout"], "resources": {"mem_mb": 900, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0254_cb12_screen_F"], "argv": ["scripts/run_cb12.py", "rep", "--family", "F"], "timeout_s": 7200, "max_retries": 1, "outputs": ["research_lab/creative_batch12/results_F_rep.json", "trials.jsonl (cb12_replication + creative_batch_12:F:rep)"], "next_action": "pass: Stage P-F registration draft", "notes": "DRAFT. Verifies the seal hash first."}
{"id": "q0260_cb12_opt_smoke", "title": "CB12-O smoke (one live checkpoint during a regular session): strike-frame regex hits and rule-text flags, CBOE chain per underlying with timestamp, two /book reads per member, Nasdaq earnings calendar keyless check; no unit kept", "family": "creative_batch_12", "priority": 21, "expected_value": "go/no-go for O", "data": ["public Gamma, CLOB /book", "cdn.cboe.com delayed quotes", "Yahoo chart", "Nasdaq earnings calendar"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu", "network": "gamma-api, clob, cdn.cboe.com, query1.finance.yahoo.com, api.nasdaq.com"}, "depends_on": [], "argv": ["scripts/run_cb12.py", "opt-smoke", "--rules", "../docs/research_lab/seals/cb12_opt_rules.json", "--rps", "2"], "timeout_s": 900, "max_retries": 1, "outputs": ["research_lab/creative_batch12/opt_smoke.json", "trials.jsonl (cb12_descriptive)"], "next_action": "PASS: O freeze, then q0261; FAIL: O not testable (source), counted", "notes": "DRAFT. Must run between 13:30 and 20:00Z on a trading day."}
{"id": "q0261_cb12_opt_live", "title": "CB12-O collector (cron 11:00/13:00/15:00 ET trading days, outside the queue lanes): Gamma strike frame, CBOE chain per underlying, two /book reads per member >= 60 s apart; Yahoo daily bar per underlying after each settlement; windows 1 and 2 by the cluster-count rule", "family": "creative_batch_12", "priority": 0, "expected_value": "O1/O2 and rep inputs", "data": ["public Gamma, CLOB /book", "cdn.cboe.com", "Yahoo chart"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cron", "network": "gamma-api, clob, cdn.cboe.com, query1.finance.yahoo.com"}, "depends_on": [], "argv": ["scripts/run_cb12.py", "opt-live", "--rules", "../docs/research_lab/seals/cb12_opt_rules.json", "--rps", "2", "--disk-cap-gb", "0.3", "--data-dumps-cap-gb", "40"], "timeout_s": 600, "max_retries": 0, "outputs": ["history/h12_opt_live/<window>/<date>_<checkpoint>.json.gz"], "next_action": "window 1 closes -> q0262", "notes": "DRAFT. Installed by the orchestrator after the O freeze. A missed checkpoint is 'unavailable (collection)', never back-filled."}
{"id": "q0262_cb12_census_O", "title": "CB12-O census (window 1), counts only: units by underlying/settlement/checkpoint/anchor type/tightness/exclusions, GO, cor(q-m1, q_RV-m1)", "family": "creative_batch_12", "priority": 20, "expected_value": "O gate", "data": ["history/h12_opt_live/w1 (no guarded file)"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": [], "argv": ["scripts/run_cb12.py", "census", "--family", "O"], "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch12/census_O.json", "trials.jsonl (cb12_descriptive)"], "next_action": "q0263", "notes": "DRAFT. After window 1 closes and every settlement bar is fetched."}
{"id": "q0263_cb12_screen_O", "title": "CB12-O: O1 (slope of Y-m2 on q-m1; settlement-date sign-flip; realised-vol attribution; direct-digital, checkpoint, earnings robustness) and O2 (anchor side at recorded ask, 4c filter, depth, fee; m_prev placebo; +0.5c) on window 1", "family": "creative_batch_12", "priority": 20, "expected_value": "O verdicts", "data": ["history/h12_opt_live/w1 + outcomes_guarded (opened here)"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0262_cb12_census_O"], "argv": ["scripts/run_cb12.py", "screen", "--family", "O"], "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch12/results_O.json", "trials.jsonl (cb12_test + creative_batch_12:O n_tests=2)"], "next_action": "full batch Holm (k1=10); advanced: q0264 after window 2", "notes": "DRAFT. Refuses unless GO passed."}
{"id": "q0264_cb12_rep_O", "title": "CB12-O: O1-rep and/or O2-rep on window 2", "family": "creative_batch_12", "priority": 20, "expected_value": "L2 verdicts", "data": ["history/h12_opt_live/w2 + outcomes_guarded"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0263_cb12_screen_O"], "argv": ["scripts/run_cb12.py", "rep", "--family", "O"], "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch12/results_O_rep.json", "trials.jsonl (cb12_replication + creative_batch_12:O:rep)"], "next_action": "pass: Stage P-O depth-aware window", "notes": "DRAFT."}
{"id": "q0265_cb12_hidden_census", "title": "CB12 (CH103) hidden-book census, counts only: Gamma markets with active=false and closed=false by end year, acceptingOrders share, event attachment; whether the complete-universe capture query includes them (query string check, no capture read)", "family": "creative_batch_12", "priority": 20, "expected_value": "universe-completeness methods note", "data": ["public Gamma"], "resources": {"mem_mb": 200, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0240_cb12_smoke"], "argv": ["scripts/run_cb12.py", "hidden-census", "--rps", "2", "--disk-cap-gb", "0.001", "--data-dumps-cap-gb", "40"], "timeout_s": 900, "max_retries": 1, "outputs": ["research_lab/creative_batch12/hidden_census.json", "trials.jsonl (cb12_descriptive)"], "next_action": "methods note to the orchestrator; any hidden-rung test is a later registration", "notes": "DRAFT. Uncounted. No price, volume or outcome stored."}
```

## 5. Code needed (not written by this document)

- `backend/astrolabe/research_lab/cb12_common.py`: reuse `cb11_common` (refused roots, disk and free-disk guards with
  cap 40, exit 75, manifests, `*_complete` status, cluster bootstrap with the small-G rule, Holm/BY helpers); the
  transaction aggregator (hash → row, hash discarded) shared by M and F; the `prices-history` point rule.
- `cb12_say.py`: tag-100343 walker (monthly windows, split-until-uncapped), occasion rule, `start_edit` flags, series-date
  key, member listing rule, availability, `S_e`/`N_e`, M1, the GMP copula and placebo, M2 trade-through maker and the
  fill-time calibrated placebo, print-sum robustness.
- `cb12_quake.py`: tag-union frame, frozen title classes and description parser (window, threshold, ET clock), overlap
  exclusion, USGS client (paging by time chunks ≤ 20,000 rows), model fit restricted to events before 2024-09-01, the
  72 h usability rule and the ambiguous-quake exclusion, `q` for E-a/E-b/E-c, the catalogue outcome evaluator, E1 with
  `p_reg`/`p_alt`, the GEP simulation, the live collector and E1-rep/E2.
- `cb12_prints.py`: frame and strata, newest-first fetch with the full-coverage flag, impact sign, AL stacked local-linear
  RD (triangular kernel, donut, placebo cutoffs, permutation), SH classifier (two branches, grids, B exclusion), SH1/SH2,
  label permutation, size-quintile attribution, fee-era split; cluster-level sufficient statistics to keep RAM ≤ 900 MB.
- `cb12_xhor.py`: C1 reproduction via `run_cross_venue.load_pair_series`/`audit_sets` (no fork of the definitions), a
  streaming field-restricted `endDate` extractor for `poly_markets.json`, the Kalshi scheduled-close reader, bins,
  demeaning (whole-window and causal), pooled AR(1) per bin, HL, the horizon-offset placebo, strata.
- `cb12_opt.py`: strike-frame regex and rule flags, CBOE chain client, the direct-digital and `Φ(d2)` anchors with the
  exclusions, two-read book capture, Yahoo settlement and realised-vol reader, O1/O2, window rules.
- `backend/scripts/run_cb12.py` with the subcommands of §4; refuses analysis before the family's freeze hash.
- Tests (`test_cb12_say.py`, `test_cb12_quake.py`, `test_cb12_prints.py`, `test_cb12_xhor.py`, `test_cb12_opt.py`,
  `test_run_cb12.py`): whitelist fixtures with every forbidden field; HOLDOUT, `cross_venue_live` and `T12_X_end`
  refusals; no census path receives an outcome, a catalogue event at or after `t − 72 h`, a later price or a gap
  statistic; the `prices-history` stamp + 600 s boundary; the occasion rule at 36 h; the 90% availability rule; the
  trade-through boundary (`≥ a + 1c` fills, `a + 0.99c` does not; fills at `startTime` excluded); the model fit refuses
  catalogue rows at or after 2024-09-01; E-b "decided" rung; DST for 16:00Z and the O checkpoints across 2026-11-01;
  the donut and bandwidth edges; the shape grid at $0.01 in both branches and the B class at price 0.50; impact sign at
  equal prices; `ρ ≥ 1` → HL cap; the C1 counts 316/183/517,616; `battery2` kinds and k1 = 10 fixed.

## 6. Test budget and compute

| Job | Tests counted | Kind(s) | Decision |
|---|---|---|---|
| Stage 1: M1, M2, E1, AL1, AL2, SH1, SH2, X1, O1, O2 | **10** | `cb12_test` + count lines `:M` (2), `:E` (1), `:F` (4), `:X` (1), `:O` (2) | p < 0.01, floor, binding placebos and robustness, **and batch Holm (one-sided α 0.05, k1 = 10 fixed; early finishers at 0.005)**; counted with p = 1 if a gate, audit or smoke check fails |
| Stage 2: M1-rep, M2-rep, E1-rep, E2, AL1-rep, AL2-rep, SH1-rep, SH2-rep, O1-rep, O2-rep (each only if triggered) | ≤ 10 | `cb12_replication` + `:<family>:rep` | one Holm over CB12 Stage 2, one-sided α 0.05 |
| Smoke, census, gates, strata, variants, descriptives, CH103 census | 0 | `cb12_descriptive` | - |
| **Total** | **10 fixed + ≤ 10 conditional = 10-20** | | cumulative 1,156 → ≥ 1,166-1,176 plus CB6-CB11 |

**Host compute.** Under 6 CPU-hours at nice 19 in total (F screen about 2 h with 200-draw permutations on cluster-level
arrays; X about 1 h with 2,000 bootstrap and 200 placebo draws on sufficient statistics; E about 30 min; M about 20 min;
censuses about 2 h); peak RAM 0.9 GB. **Network.** ≤ about 56,000 historical requests (about 7-8 h of `net` lane at 2
rps), plus the E cron (≤ 200 a day for about 3 months) and the O cron (≤ 1,350 a trading day for 2 windows).
**Disk.** ≤ 0.65 GB historical + ≤ 0.65 GB live.

**Dates (estimates).** Code and the freeze check about 2026-10-18/19. **Runnable before `T_seal` on the host:** q0240
and q0251 (`cpu`) as soon as code lands; X can freeze on its census alone and screen on the `cpu` lane on about 10-19,
while CB11 holds the `net` lane. The CB12 `net` jobs (about 7-8 h) follow CB11's (about 10-11 h) on about 10-19..21; if
the lane stays free, M, E and F censuses and screens land before 10-22, otherwise after the `T_seal`-bound jobs, with no
rule change. O and E Stage 2 are prospective and start at their freezes (O needs a weekday session for its smoke; the
first possible O session is Monday 10-19 or later).

## 7. Main scientific risks (for the challenger)

1. **E is cluster-limited by nature.** One global quake process drives every market; effective clusters are calendar
   weeks (about 70), and the MDE (about 0.6-0.9) is far above the 0.25 floor. GEP may stop E1 (counted). The catalogue
   serves only final magnitudes, so the 72 h lag and the ambiguous-quake exclusion are the PIT guard; a quake revised
   across a threshold more than 72 h after its origin would leak. The negative-binomial horizon scaling is an
   approximation, frozen.
2. **M's start time and fill model.** `startTime` is a hindsight field (labelled; flagged edits excluded in a binding
   check). M2's quotes are declared, not recorded (L1); the trade-through rule and the fill-time calibrated placebo are
   meant to stop a mechanical maker profit, and the challenger should test whether they do. Period baskets are left out
   by rule, not by result.
3. **F's thresholds and truncation.** The $10k/$25k cutoffs are declared, not verified against any feed; if the feeds
   use other values, AL is a null by construction. The newest-first 20,000-print cap selects older transactions on
   later activity; the binding full-coverage check is the guard, and the coverage audit's 50% full-coverage threshold is
   a new number (not CB10's 90% whole-life audit, which this population cannot meet in the top stratum): **this is the
   point most open to challenge.** SH's classifier depends on the fee arithmetic (the decoding check gates it).
   AL and SH share transactions, so they are not independent evidence.
4. **F's look-ahead.** The end-of-life volume floor and strata select markets that became active (as CB10-B, CB11-A),
   shared by every arm.
5. **X is worn and possibly unidentifiable.** The C1 set has been analysed three times; the 30-day window ties horizon to
   life-cycle, and the horizon-offset placebo will block X1 if the two are collinear. The long bin exists only through
   early-resolving futures, which are mostly sports and elections (binding strata). No historical replication exists.
6. **O is slow and shares underlyings with CB9-P.** Window 1 may take three months if only month-end ladders exist; one
   (underlying, settlement) is one outcome draw. The chain is 15 minutes delayed (conservative), dividends and earnings
   are handled by exclusion, and settlement basis (Pyth vs exchange close) is audited. O and CB9-P results are not
   independent.
7. **Binding Holm with k1 = 10.** Early finishers face p < 0.005; a family can fail Holm with p between 0.005 and 0.01
   that CB11's rule would have advanced. This is deliberate (the brief asks for Holm within batch) and is fixed now.
8. **Queue.** CB12 `net` jobs yield to CB11 and every `T_seal`-bound job; M, E and F may slip past 10-22 with no rule
   change. The two crons are new host load (≤ 2 rps for ≤ 5 minutes per checkpoint) and need the orchestrator to
   install them.

## 8. Next actions

1. **Challenger review** (`science-reviewer`, high effort) of this draft: M, E, F, X and O separately; the probes table;
   the deviations (series-date and overlap keys, the 50% full-coverage audit, binding Holm, E's prospective-only Stage 2,
   X's worn-set label).
2. Write `seals/cb12_rules.json`, `seals/cb12_opt_rules.json`, the modules and tests of §5 and `run_cb12.py`
   (implementer); the code-against-design freeze check (`science-reviewer`).
3. Commit q0240 and q0251 first (both `cpu`; X can freeze and screen before `T_seal`), then q0241-q0247 and q0265 behind
   CB11; seals q0248; censuses q0249/q0250; per-family freezes of `model_specs/cb12_v1.json`; screens; conditional jobs
   by the stated triggers. O: rules, q0260 on a weekday session, freeze, cron q0261. E: cron q0257 at the E freeze.
4. CB11's later builds and CB13 add CB12's frame ids to their exclusion keys (note for their owners).
5. Ledger lines for every counted result; checkpoint and plain-English dashboard updated by the orchestrator.
