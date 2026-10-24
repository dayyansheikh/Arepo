# Creative batch 14 (CB14): Wikipedia edit-burst lead, intra-speech hazard decay

`evidence_role: exploratory_historical` (CB14-W Stage 1; CB14-S Stage 1) / `prospective` (CB14-W Stage 2, a live
collector from a date after the W freeze; CB14-S Stage 2, mention events that start after the S freeze) | status:
**DRAFT-REVISED after challenger round 1 (CB14-W REVISE, CB14-S REVISE, CH127 deferral accepted; 14 items: 12
adopted, 2 adopted with a stated modification, none rejected; §9-§10). Nothing frozen, nothing queued, no code.**
Drafted 2026-10-18 22:15 UTC+1 (2026-10-18T21:15Z) on parent `2e24605` and committed as `03f7200`; round-1 response
2026-10-18 22:36 UTC+1 (2026-10-18T21:36Z; §10). Every round-1 change tightens or clarifies; no floor, threshold, gate, alpha or cap was relaxed. Nothing was fetched or written for CB14 beyond the read-only host listings and
the 25 counts-only keyless GETs of §0.3. **No CB14 quantity was computed:** no burst, decisive move, lead, mark-out,
net, position model, hazard, slope or resolution.

This file turns two round-6 ideas from `CREATIVE_HYPOTHESES_2026-10-20.md` into declared, falsifiable tests: **CH123**
(Wikipedia edit-stream lead for resign / out-as / fired / indicted markets) as **CB14-W**, and **CH121** (intra-speech
hazard decay for mention baskets) as **CB14-S**. It records why **CH127** (box-office preview multiple) is not a test in
this batch (§0.4). It follows `CREATIVE_BATCH_13.md` (CB13), `CREATIVE_BATCH_12.md` (CB12) and `CREATIVE_BATCH_11.md`
(CB11) in structure and rules. "As CB13 §x" means that rule applies unchanged, including its challenger-round fixes and
the CB12, CB11 and CB10 rules it cites. CB4 amendment A-C1 and the CB10 §2.3 small-G rule govern the time cluster ways.
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim. AREPO never
  trades. Every P&L is a paper rule at recorded or declared prices.
- Test tables bind only once the CB14 declaration hash is committed (`model_specs/cb14_v1.json`, the CB14 freeze). That
  needs a `science-reviewer` challenger round (§8) and a code-against-design freeze check first. The rules (frames,
  query lists, regexes, windows, burst rule, decisive-move rule, alignment rule, position-model recipe, splits,
  exclusion rules, clocks, stored fields) are fixed in `seals/cb14_rules.json` before the first CB14 job (q0300).
  **Both files are hashed per part (`common`, `W`, `S`)**, so W can freeze and screen without waiting for S's nested data,
  and no rule of one part changes after the other part's read (CB11 freeze-check fix B1).
- **Lanes.** Every CB14 Stage-1 input is a keyless public fetch (`net` lane, **priority 10-14, below every CB6-CB13
  job**; CB13 net is 15-19, CB12 20-24, CB11 25-29). CB11's data jobs (q0221-q0229) are queued on the host and hold the
  `net` lane for about 10-15 h, then CB12 and CB13. Censuses, gates and screens run on the `cpu` lane. The W Stage-2
  collector (q0310) runs as a cron job outside the queue lanes, as CB12's q0257. **No CB14 object is bound to the
  2026-10-22T00:00Z `T_seal` lane.**
- **Queue ids q0300-q0339, one id per job, no letter suffixes.** Checked at drafting (`ls queue/jobs queue/drafts`;
  `grep -r q03` over `docs/research_lab/`): nothing at or above q0300 exists. CB13 reserved q0270-q0299. Specs are
  drafts **in this document only** (§4). Nothing is created under `queue/` until code, tests and the freeze check exist.
- **Naming.** Historical fetch roots `history/h14_wiki` (W) and `history/h14_speech` (S); collector root
  `history/h14_wiki_live`; outputs under `research_lab/creative_batch14/`. Round 6 wrote the fetches as `h13_edits` and
  `h13_speech`; CB13 owns the `h13_` prefix, so CB14 uses `h14_`.

## 0. Summary, selection and scope

| Rank | Family | Hypothesis | Counted tests | Stage 1 data | Stage 2 data | Queue ids |
|---|---|---|---|---|---|---|
| 1 | **CB14-W** Wikipedia edit-burst lead (CH123) | in markets on whether a named person will resign, be out, be fired, be removed or be indicted, a burst of edits on the person's English Wikipedia article precedes the **start** of the market's decisive move by ≥ 5 min while the price is still within 5c of its pre-move level, more often than in hot-period placebo windows of the same subject in the 3 days before (W1, excess ≥ 0.25); a taker who buys YES at recorded prints after each burst and exits at the 2 h recorded prints earns after fees (W2, ≥ +1.0c per share) | W1 (lead excess), W2 (burst-triggered taker economic) | fresh `h14_wiki`: frozen-query Gamma frame by **listing date**, MediaWiki revision metadata, Data API prints; units in `[2024-01-01, 2026-04-01)`; no historical holdout | prospective: the live collector (recent-changes poll + CLOB `/book` reads at burst + 1, 5, 15, 120 min) from `max(W freeze + 1 d, 2026-10-26T00:00Z)`; W1-rep, W2-rep at recorded asks | q0300, q0302-q0311 |
| 2 | **CB14-S** intra-speech hazard decay (CH121) | in single-occasion mention events, once the speech runs, the price of an unsaid word falls more slowly than a frozen speaker position model anchored on the word's own start price says it should, so the anchor predicts resolution beyond the in-speech price (S1, slope ≥ 0.30); a paper maker selling unsaid-word YES during the speech, filled only by trade-through prints, earns (S2, ≥ +1.0c per filled share) | S1 (slope), S2 (in-speech maker economic) | fresh `h14_speech`: subset **P** (event ends `[2024-11-01, 2025-06-01)`, disjoint from CB12-M) ∪ subset **N** (event ends `[2025-06-01, 2026-03-01)` = CB12-M's SCREEN window, **read only after CB12-M's Stage-1 result is committed**, §1.3); Roll Call Factbase timestamped transcripts; CLOB 1-minute `prices-history`; Data API prints | out-of-time: mention events starting at or after `max(S freeze + 1 d, 2026-10-27T00:00Z)`, fetched after each ends; **never CB12-M's HOLDOUT** | q0301, q0312-q0322 |
| - | CH127 preview-multiple anchor | not a test: the counts-only census does not support it within this round's request cap (§0.4) | none | | | next batch |

**Counted: 4 fixed (W1, W2, S1, S2) + up to 4 conditional (W1-rep, W2-rep, S1-rep, S2-rep) = 4-8** (§2.5). The budget is
fixed now. No CB14 test is added after any CB14 read.

### 0.1 Queue id mapping (one id per job)

| Id | Job | Family | Earliest commit |
|---|---|---|---|
| q0300 | `cb14_smoke_W` (≤ 30 requests; §CB14-SM) | W | after `seals/cb14_rules.json` (common + W) and smoke code exist (`net` lane) |
| q0301 | `cb14_smoke_S` (≤ 30 requests; §CB14-SM) | S | after the S rules part and smoke code exist (`net` lane) |
| q0302 | `cb14_exclusion_keys` (CB13 q0276 key file + every frame since, incl. the CB11-A `h11_attn` frame and entity map, CB12 and CB13 frames, seal copies) | W, S | after q0300 PASS and CB13 q0276, CB11 q0227 complete (or their ledger stop records) |
| q0303 | `cb14_w_frame` (frozen query list on Gamma `public-search`, closed and active, paged to the end; title regex; listing-date rule; members; entity rule + Wikipedia summary; completeness cross-check on a politics-tag walk of two months; audit file of every mapped pair) | W | after q0302 |
| q0304 | reserved: the W map audit (a repo step by a `science-reviewer` agent, gate GW0; no queue job) | W | - |
| q0305 | `cb14_w_pregate` (counts only, no network; gate GWC) | W | after the GW0 audit file is committed |
| q0306 | `cb14_w_revisions` (MediaWiki `prop=revisions` metadata per mapped article; bot-group list) | W | only after q0305 PASS |
| q0307 | `cb14_w_prints` (Data API newest-first prints per mapped market, ≤ 2 pages, aggregated to transactions) | W | after q0306 |
| q0308 | `cb14_census_W` (counts only; gates GW, GWP; MDEs) | W | after q0307 |
| q0309 | `cb14_screen_W` (W1, W2 Stage 1) | W | after the W freeze |
| q0310 | `cb14_w_live` (cron collector outside the queue lanes: recent-changes poll every 60 s, live burst rule, CLOB `/book` at burst + 1, 5, 15, 120 min; daily frame refresh; weekly blind map audit batch) | W | after the W freeze; starts no earlier than 2026-10-26T00:00Z (collection is unconditional; analysis is not) |
| q0311 | `cb14_rep_W` (W1-rep, W2-rep on the live window) | W | only if W1 or W2 advanced; after `T14_W2_end` + 3 d |
| q0312 | `cb14_s_frame` (Gamma tag 100343 one-week end-date walk over `[2024-11-01, 2026-03-01)`; CB12's frozen sports registry and broadcast regex; occasion rule; ≥ 8 members; speaker rule; Factbase record mapping from metadata; **no outcome stored**; audit file) | S | after q0302 |
| q0313 | `cb14_s_fit_fetch` (Factbase timestamped transcripts of primary speakers dated `[2023-01-01, 2024-11-01)`, parsed segments) | S | after q0312 |
| q0314 | `cb14_s_fit` (the frozen position model from fit transcripts only; model file sha256) | S | after q0313; before any S price, print or target transcript is read |
| q0315 | reserved: the S transcript-map audit (repo step, gate GS0; no queue job) | S | - |
| q0316 | `cb14_s_pregate` (counts only, no network; gate GSC on frame and map metadata of P and N) | S | after q0314 and the GS0 audit file |
| q0317 | `cb14_s_data_P` (P only: target transcripts, 1-minute `prices-history`, prints, Gamma outcomes to guarded files) | S | only after q0316 PASS |
| q0318 | `cb14_s_data_N` (N only, same fetch) | S | **only after `T14_S_open`** (CB12-M's Stage-1 result commit or its ledger stop record; §1.2) |
| q0319 | `cb14_census_S` (counts only on P ∪ N; gates GS, GSP, GSP2; MDEs) | S | after q0317 and q0318 |
| q0320 | `cb14_screen_S` (S1, S2 Stage 1 on P ∪ N) | S | after the S freeze |
| q0321 | `cb14_s_stage2_data` (repeat, weekly: post-freeze events, same fetch) | S | after the S freeze; data collection is unconditional |
| q0322 | `cb14_rep_S` (S1-rep, S2-rep) | S | only if S1 or S2 advanced; after `T14_S2_end` |
| q0323 | `cb14_stage2_final` (the CB14-wide strict Stage-2 Holm over every triggered rep; can only add passes; §11 F6) | W, S | after every triggered rep (q0311 / q0322) is final |
| q0324-q0339 | reserved | - | - |

### 0.2 Selection and scope

**Ranking rule.** As CB13 §0.2, with this brief's preferences: (a) round-6 ideas that CB13 deferred to CB14 (CH123,
rank 3; CH121, rank 5; CH127, rank 8); (b) designs that cannot run ahead of, or contaminate, the CB11-CB13 objects they
neighbour (CB11-A's attention family, CB12-M's mention baskets); (c) side-free and wallet-free designs. **No CB14
statistic reads the Data API `side` field or any wallet field.**

**What the drafting session read or computed (2026-10-18T20:45-21:15Z).**
- Committed documents: CLAUDE.md, AGENTS.md; round 6 §0 (facts), §2 (CH121, CH123, CH127), §3 (ranking, screen sketches,
  registration notes); CB13 in full, including §9 (challenger round 1) and §10 (response); CB12 §0-§1.4, §2.1,
  §CB12-M and §11 (freeze-check amendments); CB11 §1.2-§1.4 and §CB11-A; the ledger's smoke entry of 2026-10-18
  21:00-21:30Z (CB12 smoke `m_prices_history` artefact; CB11 smoke parked; pageview lag measured at 69 h); the queue
  README; `seals/j4r_window.json`.
- Prior-work search: no AREPO test has used Wikipedia **edits** (CB11-A uses pageviews only and has not run), the
  personnel / status class as a population, a transcript clock or a within-event survival model. CB12-M (not run)
  tests the **pre-start** basket sum at `start − 2 h` and a pre-start maker; no test has an in-speech checkpoint.
- `battery2.cumulative_count()` (`battery2-count-v1`) = **1,221** on HEAD (1,181 at `647549c~1`; the host union at
  `647549c` added 40 counted `flow_screen` lines). **Correction (round 1 item 14):** the draft said the working copy was
  identical; it is not (it holds 2 extra uncommitted `cb12_descriptive` lines, which count 0). **The count is not
  stable:** the host writes about 55-60 counted `flow_screen` lines a day, so CB14 states no projected total; every
  counting CB14 job records **the value at its run, after the host union**. The uncommitted `battery2.py` edit in the working tree only adds
  CB13 kinds with rule `EXCLUDE`, so the total is the same with or without it.

**Four round-6 premises corrected by the probes (they shape this design).**
1. **A frame by scheduled end misses most decisive events.** Of the 150 closed "out as" events read (probes 2, 7, 8),
   50 have a scheduled end at or after 2026-10: they closed early, so a scheduled-end frame over a past window drops
   them, and a frame over a future window selects them on their outcome. W therefore frames markets by **listing date**
   and keeps open and closed markets alike, censored at the W calendar end (§CB14-W). No status, close time or outcome
   enters eligibility.
2. **1-minute CLOB history is verified for 2025 but not for 2024.** A 2025-06 market returned 360 one-minute rows in
   its last 6 h; a 2024-09 market returned 0 rows at fidelity 1 over 14 days (probes 11-16; this may be the market's own
   inactivity, as in the CB12 smoke's `m0`). W therefore uses **Data API prints**, not `prices-history`. S keeps
   `prices-history` and starts at 2024-11 with an availability rule checked by its smoke.
3. **Factbase timestamps are relative to the video, not the wall clock** (probe 21: segment stamps 00:00:00-01:36:04).
   The speech clock must be aligned to the market clock. S does it causally from the price jumps of words already
   said before the checkpoint (§CB14-S). Scheduled `startTime` is a hindsight label (CB12-M) and not the clock.
4. **The MediaWiki `mw-reverted` tag is applied retroactively** (it marks an edit when a *later* edit reverts it; probe
   9 lists it). A burst filter on it would use the future. The burst rule uses only what is known at save time (the
   reverting edit's own `mw-undo` / `mw-rollback` / `mw-manual-revert` tags and comment).

### 0.3 Feasibility probes (counts only; read-only host listings + 25 keyless GETs; nothing stored)

Host probes ran over `ssh oracle` as `ls`, `du`, `df`, `ps` and `/proc/meminfo` reads. **Nothing was written, moved
or deleted on the host. `~/arepo/run/queue` was not touched or listed.** Keyless GETs ran from the Mac (scripts in
`/tmp/cb14probe/`, not committed), `User-Agent: arepo-research-probe/1.0 (read-only counts; https://www.arepolabs.com)`,
paced at ≥ 1 s. **No price, outcome, resolution, volume or wallet of any market was printed or stored.** Disclosed
feature exposure: probes 1-8 printed event counts, member counts, end years and **name-masked, digit-masked** title
templates of closed W-class events, and the count of closed events whose scheduled end is at or after 2026-10 (an
early-closure aggregate, used only to justify the listing-date frame, premise 1). Probe 17 printed counts, speaker
buckets of titles and description-word counts of P-window mention events (no price, outcome or transcript). Probes
11-16 printed `prices-history` row counts of two top-volume markets ending 2024-09-10 and 2025-06-10 (ids not
printed; if either lies in a CB14 frame, only its row count was seen). Probes 21-24 touched only an October 2026 event,
outside every CB14 window.

| # | Host probe | Finding |
|---|---|---|
| H1 | `ls` of `research_lab/` and `history/`; `du`; `df`; `MemAvailable` | `history/` holds `h1_first` … `h8_text` only: **no `h11_*`, `h12_*` or `h13_*` root exists yet** (CB11-CB13 fetches have not run); `creative_batch11/` holds only `external_ids/`; data-dumps 16 GB; root 89 GB with 58 GB free; MemAvailable about 4,470 MB |
| H2 | `ps` (process names only) | the live large-trade monitor and the cross-venue live poller are running; no CB process was visible at 21:0xZ |

| # | Keyless request(s) | Finding |
|---|---|---|
| 1 | Gamma `/public-search?q=resign&events_status=closed&limit_per_type=100` (1) | 50 of **71** events (`totalResults`), 93 markets, ≤ 16 members; end years 2021 3, 2023 5, 2024 11, 2025 11, 2026 10, 2027 10. Templates "Will N resign by N ##?", "N out as Secretary of N by N ##?", "Will N resign in ####?" |
| 2 | the same, `q=out as` (1) | 50 of **296** events, 94 markets, ≤ 9 members; templates "N out as President by N ##?", "N out as N Leader of N by N ##?", "N out as N President before N" |
| 3 | `q=fired` (1) | 31 of 31 events, 304 markets; includes mention events ("What will N say during N rally?", where "fired" is a word) and sports/staff titles; real "N fired/resigns by N ##?" templates exist |
| 4 | `q=indicted` (1) | 18 of 18 events, 28 markets; 12 of 18 end before 2024-07 (a thin class) |
| 5 | `q=die` (1) | 1,100 results, dominated by entertainment ("Who will die in <show>") and unrelated titles; real-person death markets are a small, separate class (reported only, §CB14-W) |
| 6 | `q=step down` (1) | 2 of 2 events |
| 7-8 | `q=out as` pages 2 and 3 (2) | 100 more events, 162 markets. The 150 "out as" events read, by scheduled end: before 2024-07 **7**, `[2024-07, 2025-07)` **31**, `[2025-07, 2026-04)` **43**, `[2026-04, 2026-10)` **19**, at or after 2026-10 **50** (closed early; premise 1) |
| 9 | MediaWiki `action=query&prop=revisions&titles=Keir Starmer&rvprop=ids|timestamp|user|userid|size|comment|tags|flags&rvlimit=max&rvstart=2026-10-17&rvend=2026-10-01` (1, out of window) | 200; 19 revisions, no continuation; keys `revid, parentid, timestamp, user, userid, size, comment, tags, minor`; **second-level ISO timestamps** (20 characters, `Z`); tags include `mw-reverted` (retroactive, premise 4), `mw-manual-revert`, editor-type tags |
| 10 | MediaWiki `list=allusers&augroup=bot&aulimit=max` (1) | 200; **313** bot-group accounts on one page (no continuation) |
| 11-14 | Gamma `/markets?closed=true&end_date_min/max` for 2024-09-10 and 2025-06-10 (top 20 by volume) and CLOB `prices-history` fidelity 1 over the first market's last 6 h (4) | 2024: **0 rows**; 2025: **360 rows**, steps 33-60 s |
| 15-16 | the 2024 market again, fidelity 1 over its last 14 days (2) | **0 rows** (premise 2) |
| 17 | Gamma `/events?closed=true&tag_id=100343&end_date_min=2025-01-01&end_date_max=2025-06-01&limit=200` (1) | **85 events** (fewer than the limit, so complete), 81 with ≥ 8 members, **1,416 markets**; 62 with `endDate − startTime ≤ 36 h` (60 of them with ≥ 8 members). Speaker bucket of those 60 by title keyword: **Trump 43**, Powell 3, Biden 2, Leavitt 2, debate 2, Musk 1, Vance 1, earnings 1, interview 1, other 4. Description words: "video" 71, "q&a" 42, "transcript" 13 |
| 18 | the same for ends `[2026-10-01, 2026-10-18)` (1, out of window) | 55 events, 54 with ≥ 8 members, 892 markets, 52 occasions; Trump 21, **earnings 10**, podcast 5, MrBeast 1, Vance 1, press briefing 1, other 13 |
| 19 | Roll Call Factbase `wp-json/factbase/v1/search?...&page=1&format=json` (1) | 200; JSON `meta` + `data`, 40 records per page; record keys include `date`, `type`, `record_title`, `factbase_url`, `video_url`, `speaker_id`; types Speech, Interview, Press Briefing, Press Conference, Press Gaggle, Remarks, Vlog; page 1 dates 2026-10-07..16 |
| 20 | the same with `type=Speech` (1) | `records_matched` **977**, 25 pages |
| 21 | one Factbase transcript page (a 2026-10-16 speech) (1) | 200, 2.16 MB HTML; **468 hh:mm:ss segment stamps (232 distinct), last 01:36:04**: segment-level timestamps relative to the video (premise 3) |
| 22 | Gamma `/events?closed=true&tag_id=100343&end_date_min=2026-10-01&end_date_max=2026-10-12` (1, out of window) | 38 events; 15 Trump occasions with ≥ 8 members and `startTime` |
| 23-24 | CLOB `prices-history` fidelity 1 over `[startTime, startTime + 2 h]` for two members of one of them (2) | 120 rows each; 30 and 2 price changes (counts only): **in-speech minute data exist**, activity varies by word |
| 25 | Gamma `/public-search?q=opening weekend&events_status=closed&limit_per_type=100` (1) | 50 of **354** events, 170 markets, ≤ 27 members; end years 2021 9, 2022 7, 2023 19, 2024 4, 2025 1, 2026 8, 2027 2 (**39 of 50 before 2024-07**) |

Request total: **25** GETs (8 + 2 + 4 + 2 + 1 + 1 + 1 + 1 + 1 + 1 + 3), at the cap.

**Population counts used below (planning, not gates).**
- **W.** `totalResults`: "out as" 296, "resign" 71, "fired" 31 (about 20 non-mention), "indicted" 18, "step down" 2;
  union after overlap about 330-380 events, 1.5-2 markets each. With the listing-date frame (listed in
  `[2023-07-01, 2026-03-01)`, observed in `[2024-01-01, 2026-04-01)`), roughly 70-80% have observed life: **about 230-280
  events, 380-500 markets, 150-220 distinct subjects** before key drops. Decisive moves (price-based, §CB14-W) cannot
  be counted without reading prices; the planning figure is **40-80 in 30-60 subjects** (real departures 2024-2026 with
  Polymarket markets), against CH123's own kill at 40.
- **S.** P (ends `[2024-11-01, 2025-06-01)`): probe 17 counts 60 occasion events with ≥ 8 members in January-May 2025,
  43 of them Trump; November-December 2024 is uncounted (planning 5-15). N (CB12-M's SCREEN window): CB12's planning
  figure is about 300 non-sports occasion events; with a Trump share of 50-70% (probes 17, 18) about **150-210 Trump
  events**. P ∪ N primary (Trump, mapped timestamped transcript): **about 190-260 events, 3,000-4,300 word markets**
  (16.7 members per event, probe 17).

### 0.4 Selection decisions

| Idea | Decision | Reason |
|---|---|---|
| **CH123** edit-burst lead | **include (W)** | Keyless, second-level timestamps (probe 9), a named population (probes 1-8), wallet-free and side-free. It is CB11-A's object with the clock that CB11's probes found missing (pageviews publish 48-69 h late; edits are timed at save). Honest weaknesses: decisive moves are rare (planning 40-80), the market-to-article join is a judgement (blind audit GW0), and newest-first print reach can correlate with later activity (binding worst-case check). The money question is W2 (precision is CH123's economic parameter) and its recorded-ask version W2-rep. **Deaths are reported, not tested** (probe 5: the class is small and mixed with entertainment titles; CH123 calls it a distinct, faster class). **CH123's "tune the burst rule on the first half of the frame" is not adopted**: the rule is frozen a priori (§CB14-W), because halving a frame of 40-80 decisive moves would leave neither half testable; grid variants are reported, uncounted |
| **CH121** intra-speech decay | **include (S), P ∪ N, nested after CB12-M** | Probe 17 shows a CB12-M-disjoint window with 60 occasion events (43 Trump), probes 19-21 a keyless timestamped transcript source for the dominant speaker, probes 23-24 in-speech minute prices. P alone (planning about 45-55 usable events) cannot power S1 (MDE about 0.7-0.8 against a 0.30 floor). Adding CB12-M's SCREEN window (N) does, but only nested after CB12-M (§1.3: overlap declared, rules and timing). **Primary speaker set: speakers with ≥ 40 timestamped Factbase transcripts dated before 2024-11-01** (in practice Trump; declared now; others reported). Earnings calls (10 of 52 October occasions, probe 18) have no keyless timestamped transcript and are excluded (counted) |
| **CH127** preview multiple | **next batch, not CB14** | The counts-only census is incomplete at this round's 25-request cap: one search (probe 25) finds 354 closed "opening weekend" events, but 39 of the first 50 end before 2024-07 (the AMM era, where 1-minute and even hourly CLOB history is unverified; premise 2), only 11 end in 2025-2026, and no keyless point-in-time source for Thursday-preview grosses with publication times was probed. CH127's own kill is < 40 films. Re-entry: a counts-only date walk of the box-office tag over 2025-01..2026-09 with `prices-history` availability, plus a verified timestamped preview source, before any design |
| Other round-6 ideas | not considered here | Outside this brief (CH118 and CH128 are CB13; CH119 is CB13's next batch) |

**Sports and categories.** `CB14_SPORTS_IN_PRIMARY = false` (a parameter, as CB8-CB13; sports inclusion is the user's
open decision). W excludes sports by the CB12 frozen sports tag registry (`evidence_cb12/sports_tag_registry_20261018.json`,
492 ids; sha256 `b47b3d20c0bbf71a4e0dc912b0a32533fcd7e796e2c289a4b525774c8857bce6`, committed at `c0cb6ba`) and a frozen coach/athlete title regex, so "head coach fired"
markets are excluded and counted. S reuses CB12-M's sports tag registry (the same sha256) and broadcast regex (sha256 of
its UTF-8 string as in `seals/cb12_rules.json`: `61b45196fef836799064a6277c9bcca9316a7c240e21bfb291c6b25557d6b8c0`) **pinned by hash in part S** (round 1 item 6); a mismatch
at run time is a refusal. Category stays a parameter.

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Prior use | Role in CB14 | Evidence ceiling |
|---|---|---|---|
| `history/h14_wiki` (**new**, q0303/q0306/q0307): frozen-query frame (whitelisted Gamma fields), subject map (page id, canonical title, short description), revision metadata per mapped page (`revid, parentid, timestamp, userid, size`, frozen comment and tag booleans; user names hashed in memory to a per-run salt and discarded, only a bot flag and a distinct-user index kept), prints aggregated to transactions (time, YES-terms VWAP, min and max YES-terms price, size; hash discarded) | none | W1, W2 | L1 (historical) |
| `history/h14_wiki_live` (**new, post-freeze**, q0310): recent-changes poll log (receipt time, `rc_timestamp`, page id, size delta, frozen flags), live bursts, CLOB `/book` reads at burst + 1, 5, 15, 120 min (receipt-timed best bid, best ask and displayed sizes) | none | W1-rep, W2-rep | prospective (L2) |
| `history/h14_speech` (**new**, q0312-q0318, q0321): frame (ids, titles, `startTime`, members, rule booleans, the parsed market term and its rule variants), Factbase record map, **fit transcripts** (`fit/`), **target transcripts** (`guarded_p/`, `guarded_n/`, `guarded_s2/`: per-member first-mention offset and the transcript length, behind a causal accessor), 1-minute `prices-history` over `[startTime − 30 min, startTime + 5 h]`, transactions in that span; Gamma outcomes only in `guarded_*/outcomes_guarded.csv.gz` | none | S1, S2, reps | L1 (P; N nested, labelled) / L2 (Stage 2) |
| `history/h11_attn/` (CB11-A; built by q0227, not yet on the host) | CB11-A | **id columns of the frame (both strata, both splits) and the canonical-title column of the entity map only**, through a field-restricted accessor, for W exclusions and one binding robustness check. `holdout/`, pageviews and transactions are **never opened** | - |
| `history/h12_say/` (CB12-M) | CB12-M | **never opened by any CB14 path**: no frame, price, print, seal or outcome file. N is re-fetched by CB14 (§1.3) | - |
| `history/h13_touch`, `creative_batch13/t_screen`, `t_holdout` (CB13) | CB13 | id columns only, for exclusion keys | - |
| `snapshots/`, `live_trades/`, `book_sweeps/`, `trade_samples/`, `surprise_live/`, `cross_venue_live/`, `e001/`-`e007/`, `forecasts/`, `flow_screen/`, every `cb*_extract/` | live stores, E-series, J4-R, CB1-CB13 | **never opened by any CB14 path** (runner refuses; unit-tested). CB14 reads no AREPO live store at all | - |
| `h1_first`, `h2_main`, `h3_power`, `h4_seal`, `h5_*`, `h6_weather`, `h7_cb4_*`, `h8_*`, `h9_flow`, `h10_*`, `h11_*`, `h12_*`, `h13_*`; every `creative_batch1..13/` | worn, retired, sealed or batch-owned | **not read**, except id columns for exclusion keys through a field-restricted accessor | - |

**Reuse disclosure (W).** No AREPO test has sampled the personnel / status class or read Wikipedia revisions. The
broad h2/h3 panels, the T5 frame (314 politics markets, ends `[2025-10-11, 2026-10-04)`, outcomes seen), the C1 sample
and the CB frames may hold individual W markets; they are removed by key (§1.3).

**Reuse disclosure (S).** P has never been sampled. **N is CB12-M's SCREEN population** (declared overlap, §1.3).
S's statistic (in-speech slope against a clock anchor) has been computed by nobody; CB12-M's M1 is the pre-start
basket sum and M2's fills stop at `startTime`, so no M quantity uses an in-speech price.

### 1.2 Dates (declared; UTC unless ET is stated)

| Name | Value | Meaning |
|---|---|---|
| `T14_draft` | 2026-10-18T21:15Z | this draft; no CB14 quantity computed |
| `T14_hist_end` | 2026-10-01T00:00Z | no CB14 historical row at or after it (S rows end by 2026-03-01 + 36 h; W rows by 2026-04-01) |
| `T14_W_end` | 2026-04-01T00:00Z | **W calendar end** (§1.3, CB11-A disjointness): no W revision, burst, print, decisive move or unit at or after it |
| W frame | markets **listed** (`createdAt`) in `[2023-07-01, 2026-03-01)`, open or closed at fetch | listing-date frame (premise 1); no status, close time or outcome condition |
| W calendar | units with time in `[2024-01-01, T14_W_end)`; revisions fetched from `max(createdAt, 2024-01-01) − 30 d` | the 30-day trailing window of the burst rule needs history before the first unit |
| `T14_W2_start` / `T14_W2_end` | `max(W freeze + 1 d, 2026-10-26T00:00Z)` / the later of `T14_W2_start` + 90 d and the date by which ≥ 300 Stage-2 bursts in ≥ 30 subjects have their 120-min read, never after `T14_W2_cap` = 2027-04-30 | W Stage 2 (live). 10-26 is after CB13-T's HOLDOUT `[t_j4r_end, 2026-10-26)`, whose NEWS class holds W-type markets. The stop counts bursts, never results |
| S fit window | Factbase transcripts dated `[2023-01-01, 2024-11-01)` | position-model fit; no market data |
| S P | event `endDate` in `[2024-11-01, 2025-06-01)` | disjoint from CB12-M (its SCREEN starts 2025-06-01) |
| S N | event `endDate` in `[2025-06-01, 2026-03-01)` | = CB12-M SCREEN; nested |
| `T14_S_open` | the commit of CB12-M's Stage-1 result (`creative_batch12/results_M.json` from q0252, with its trial lines), or the ledger record that CB12-M is stopped or withdrawn without a screen | earliest start of q0318 and of every job that opens N data (§1.3) |
| `T14_S2_start` / `T14_S2_end` | events with `startTime ≥ max(S freeze + 1 d, 2026-10-27T00:00Z)` / the date by which ≥ 100 Stage-2 events with a mapped transcript and ≥ 1 aligned unit have resolved, never after `T14_S2_cap` = 2027-02-28 | S Stage 2. 10-27 is after CB13-T's HOLDOUT window. If < 60 such events by the cap, S1-rep and S2-rep are "not run (power)", counted |
| J4-R window | `[2026-10-16T00:00Z, 2026-10-21T00:00Z)` (`seals/j4r_window.json`) | not touched: CB14 reads no AREPO capture, sweep or print, and every CB14 public row inside the window is outside every CB14 unit window |
| `T_seal` | 2026-10-22T00:00Z | not binding for CB14 |

### 1.3 Sealed and untouched data (named)

- **Refused roots.** `run_cb14.py` refuses every root in the last three rows of §1.1 and the `h12_say` root entirely
  (field-restricted id readers excepted for the roots that allow them). It writes only under
  `research_lab/creative_batch14/`, `history/h14_wiki/`, `history/h14_wiki_live/` and `history/h14_speech/`.
- **CB11-A (attention without news) and CB14-W.** CB11-A's frame is closed binary markets with scheduled end in
  `[2026-04-20, 2026-10-01)`, its attention days are `[2026-04-10, 2026-09-24]`, its transactions `[2026-04-01,
  2026-10-01)`, its pageviews `[2026-01-01, 2026-10-01)`, and its HOLDOUT is an event-hash half of the same calendar
  (sealed by q0230). W is made disjoint three ways. (1) **Calendar:** no W row (revision used in a feature, print,
  burst, decisive move, unit) at or after `T14_W_end` = 2026-04-01, so W shares no transaction or attention day with
  CB11-A. (2) **Keys:** W drops every market id, event id, `negRiskMarketID` and series id in the `h11_attn` frame,
  both strata (`vol_ok` and the non-`vol_ok` stratum) and both splits, whether sampled or not. (3) **Objects:** W never
  opens pageviews, CB11-A transactions or any `holdout/` path; it reads revisions, a different object from pageviews.
  **Residual overlap, disclosed:** a W subject may be a CB11-A entity, and W reads that article's edit history in
  January-March 2026, the months CB11-A uses only for its pageview baseline and 30-day history rule. The census counts W
  subjects whose page id is a canonical title in CB11-A's entity map, and a **binding W robustness check drops them**
  (§CB14-W). No W output defines a CB11-A subgroup, and the CB11-A report may not cite W. If CB11-A is recorded in the
  ledger as stopped without a frame, (2) and the robustness check are vacuous (recorded).
- **CB12-M (mention baskets) and CB14-S: overlap declared, nesting rule.** CB12-M uses mention events with ends in
  `[2025-06-01, 2026-03-01)` (SCREEN) and `[2026-03-01, 2026-10-01)` (HOLDOUT, sealed), at `start − 2 h` and
  `start − 24 h`, with a pre-start maker whose fills stop at `startTime`. CB12-M is not frozen (verify round: M NO_GO
  pending D1-D4; M smoke v2 being prepared) and has not run.
  - **HOLDOUT: never.** No CB14 frame contains an event with `endDate ≥ 2026-03-01` and `< 2026-10-27`, so S never
    fetches, opens or analyses any event in CB12-M's HOLDOUT window, even after CB12-M's Stage 2. CB14 opens no
    `h12_say` file at all (not the frame, prices, prints, seals or outcome files), so no CB12-M outcome file is
    touched. S's Stage 2 is post-freeze events only.
  - **P: disjoint.** Ends before 2025-06-01, a calendar and key set CB12-M never reads. P's data job (q0317) may run as
    soon as the S pre-gate passes. P's outcomes and transcripts are S's own fetch.
  - **N: nested after CB12-M's Stage-1 result.** N is CB12-M's SCREEN window, re-fetched by CB14 (own Gamma frame, own
    transcripts, own in-speech prices and prints, own guarded outcomes). The q0312 frame job stores N's ids, titles,
    times and members only, and discards `outcomePrices` and `umaResolutionStatus(es)` at parse. **Every job that
    fetches or opens N transcripts, prices, prints or outcomes (q0318, and q0319/q0320 for N) refuses before
    `T14_S_open`.**
  - **Why wait for the Stage-1 result, not only for the freeze (decision).** (a) N's target transcripts, in-speech
    prices and outcomes reveal which words were said in CB12-M's SCREEN events. Read before CB12-M's freeze, they would
    unblind a design still being fixed (D1-D4), as CB3's dev window would have unblinded CB3 (CB13 round 1 item 3).
    (b) After the freeze, M1's screen should be the **first** pre-registered read of those outcomes: it is the test
    that CB12 registered on them, and S is a secondary use of the same `Y`. (c) Waiting costs little, because S also
    sits behind CB11-CB13 on the `net` lane and q0252 follows CB12-M's freeze within days. (d) A CB12-M stop record
    lifts the hold (nothing left to protect), as CB13's CB3 rule.
  - **Double-dipping and how S avoids re-testing M1.** On N, M1 and S1 share each word's outcome `Y`. They test
    different objects. M1 asks whether the pre-start **level** is too high (`Σp − ΣY`). S1 asks whether the price
    **under-reacts to the speech clock**, and its anchor `q_t` is built from the word's own start price `π` (§CB14-S).
    A pure start-level bias is carried into `q_t` and absorbed by the intercept, so it does not move the slope. A
    binding attribution check (joint fit with `π − p_lag`) withdraws the label "clock" if the slope is start-price drift.
    S1 is still not independent evidence of M1, or M1 of S1. **No CB14 line pools, cites or conditions on M1 or M2,
    and no CB12-M line may cite S.**
  - **Timing rule, decided now (round 1 item 6).** S's rules part must be hashed and committed before q0252's result
    is committed. **If the S rules part's commit comes after q0252's result commit, N becomes reported-only:** S1 and S2
    then run on P alone (likely "not run (power)", counted), and N's readings are descriptive lines. **After
    `T14_S_open`, no element of part S may change** (frames, maps, model recipe and file, alignment, units, statistics,
    placebos, robustness, gates, floors) except mechanical code fixes that make the code match this document, each
    recorded with a `science-reviewer` sign-off; any other change voids N from the primary (reported-only).
  - **Binding P/N robustness.** S1 must keep its sign on P alone and on N alone, and every S line reports both (§CB14-S).
  - **Exclusion-key deviation (declared).** By the convention of CB12 §1.3 ("CB13 must add CB12's frame ids"), CB14
    would drop CB12-M's SCREEN keys. **S does not drop them for N** (the nesting is the design). It drops every other
    frame's keys, and drops CB12-M's HOLDOUT window by date. W drops all CB12 keys.
- **E009/E010 (`cross_venue_live/`, to 2026-11-03), E011 (`surprise_live/`, window to 2026-11-10, analysed once after
  2026-11-11T13:00Z), E004-E007, the live monitor's alert stream.** No CB14 path opens any of their stores, computes any
  of their quantities or defines any of their subgroups. q0310 (W live) and q0321 (S Stage 2) collect fresh public data
  on their own frames inside those windows; that is collection overlap only, as CB12's collectors. **No CB14 output is
  stratified by E009, E010 or E011 status.**
- **CB13 (T HOLDOUT `[t_j4r_end, 2026-10-26)`, R).** W's live window starts at or after 2026-10-26 and S's Stage 2 at or
  after 2026-10-27, so neither collects in T's sealed window. CB14 adds CB13's frame ids (T SCREEN and HOLDOUT fill
  markets and events; R barrier events) to its keys, as CB13 §1.3 requires.
- **Exclusion keys (q0302).** Union of: (1) CB13 q0276's `exclusion_keys.csv.gz` (sha256 pinned; it unions CB11 q0221's
  file, the C1 sample, the T5 frame, every CB8-CB12 frame and seal copy known at q0276); (2) id columns of every sampled
  or frozen set created since or not in it: the `h11_attn` frame (both strata, both splits), `h11_pol`, `h11_wprints`,
  every `h12_*` frame (W only for `h12_say`; S keeps `h12_say` SCREEN ids, above), `h13_touch`, CB13 T fill markets and
  events; (3) every id in seal copies under `docs/research_lab/seals/` committed by then. Keys = market id, Gamma event
  id, `negRiskMarketID`, series id (looked up on Gamma, ≤ 50 ids per request). A frame not yet built is "absent at
  q0302" (recorded) and re-read by the census (q0308, q0319). If more than 2% of exclusion ids lack metadata,
  disjointness is "unverified" and the affected family is "not testable", counted. **CB15 must add CB14's frame ids.**
- **Series rule (declared deviations, for the challenger).** *W:* full rule (market, event, `negRiskMarketID`, series).
  A subject's date ladder ("X out by March / June / December") is one series, so a prior sample holding one rung drops
  the subject's whole ladder; the census reports the drops and the subjects lost. *S:* CB12-M's market, event and
  **series-date** key (same series, `startTime` within ±1 day), because weekly speaker series would otherwise be
  dropped whole (CB12 §1.3); the full-series counterfactual is reported.
- **Outcome guards.** *W:* W has no resolution target; its targets are prints after the burst. Gamma `outcomePrices`
  and `umaResolutionStatus(es)` go only to `h14_wiki/outcomes_guarded.csv.gz`, opened only by the census for an audit
  count (decisive moves on markets that resolved NO; reported) and never by a test. *S:* **target transcripts are
  outcome-bearing** (they say which words were said and when). They are stored in `guarded_p/`, `guarded_n/` and
  `guarded_s2/`, behind a **causal accessor** that, for a unit at checkpoint `t`, returns only whether the word was said
  before the transcript clock `e_t` and the offsets of words said before `e_t` (what a viewer knew at `t`). The full
  transcript (first-mention offsets after `e_t`, the transcript-based `Y`) is opened only by the screen and rep jobs.
  Gamma outcomes go to `guarded_*/outcomes_guarded.csv.gz`, opened only by q0320 and q0322. In-speech prices after `t`
  are opened only by the screen and rep jobs (census paths read prices before each unit's `t`; unit-tested).
- **No historical holdout for W** (40-80 decisive moves cannot be halved; CB12-E precedent): its replication is
  prospective at recorded asks. **S's replication is out-of-time** on post-freeze events.

### 1.4 Rules files

- `seals/cb14_rules.json` (before q0300), hashed per part:
  - **`common`**: refused roots, seeds, bootstrap, the small-G rule, Holm/BY settings, disk guards, the field
    whitelists, smoke criteria, the user-name hashing rule.
  - **`W`**: the frozen query list (`resign`, `resigns`, `resignation`, `out as`, `out by`, `fired`, `step down`,
    `steps down`, `removed as`, `removed from`, `leave office`, `ousted`, `impeached`, `indicted`, `charged`; closed and
    active; paged until `hasMore` is false), the title regex and the exclusion regexes (mention markets, sports and
    coaches, entertainment "who will die in", deaths as a reported stratum), the listing-date and calendar rules, the
    entity rule (`cb11_a`'s `derive_query` first entity, source sha256 pinned, CB11-A's stop list plus a frozen
    office-word list), the Wikipedia summary type rule (`standard`, canonical title, page id, short description), the
    30-day article-age rule, the bot rule, the burst rule, the decisive-move rule, the trade-market choice rule, entry and
    exit print windows, fee policy, the completeness cross-check months, the live poll and book-read schedule, gates and
    placebo strata.
  - **`S`**: tag id 100343, CB12-M's sports registry sha256 and broadcast-regex sha256 (§0.4), the occasion and member rules, the
    primary speaker rule (≥ 40 Factbase transcripts before 2024-11-01), the Factbase record-mapping rule (speaker, UTC
    date within ±1 day of `startTime`, type map from the event title, title keywords), the term parser and rule-variant
    booleans (plural, possessive, compounds, Q&A included), the transcript matcher and normaliser, the fit window and
    **the position-model recipe** (below), the alignment rule, checkpoints, the price rules, the S2 fill rule, gates.
- `model_specs/cb14_v1.json` (the freeze) is likewise hashed in parts W and S. **Part S also pins the sha256 of the
  fitted position model** (`creative_batch14/s_model.json`, written by q0314 from fit transcripts only, before any S
  price, print or target transcript is read).
- Jobs refuse (exit 2) on a hash mismatch. **No rule is computed from, or revised after, any W print, burst or
  decisive move, or any S price, print, target transcript or outcome.** The entity rule and the transcript-mapping rule
  may each be revised **once** before their family's freeze, and only on their blind audit (GW0, GS0), which sees no
  price, edit or transcript text.
- **Field whitelists.** *Gamma:* as CB13 §1.4 (ids, question, slug, `clobTokenIds`, outcome labels, `startDate`,
  `createdAt`, `endDate`, event `startTime`, `negRisk`, `negRiskMarketID`, event, series and tag ids, `feeSchedule`, the
  `description` sha256 plus frozen flag booleans; for S the parsed term and variant booleans). `outcomePrices`,
  `umaResolutionStatus(es)` and `closedTime` reach only the guarded files; **`closedTime` is never read by any CB14
  statistic, population rule or clock.** *MediaWiki:* `revid, parentid, timestamp, userid, size`, the frozen comment and
  tag booleans; `user` is read in memory only, to set the bot flag and a per-page distinct-user index, and is never
  written. `mw-reverted` is never parsed (premise 4). *Data API:* `timestamp, price, size, outcomeIndex,
  transactionHash` in memory, aggregated by transaction; no hash, wallet, name or `side` is written. *Factbase:* record
  `date`, `type`, `record_title`, `speaker_id`, `factbase_url`; transcript segments as (offset seconds, text) in memory,
  reduced at parse to per-term first-mention offsets and the last offset (fit and target), with no text stored. A unit
  test feeds fixtures carrying every forbidden field and asserts that no parsed row, file or log contains them.

## 2. Common rules (deltas from CB13 §2)

### 2.1 Costs

| Test | Price and cost rule |
|---|---|
| W1, S1 | none charged (lead and forecasting tests) |
| W2 | **taker entry at a recorded print**: `e` = the **maximum** YES-terms transaction price in `[b + 60 s, b + 15 min]` (the taker-adverse print after the burst `b`; none → "no entry print", counted); **exit at a recorded print**: `x` = the **minimum** YES-terms transaction price in `[b + 2 h, b + 2 h 30 min]` (none → the last transaction in `(t_e, b + 2 h 30 min)`, `t_e` the entry print's time, labelled "stale exit", counted; none after the entry print → "no exit", excluded and counted, and priced at the worst case `w*` in the binding reach check; round 1 item 7); taker fee `r·e(1 − e) + r·x(1 − x)`, `r = max(feeSchedule.rate, 0.04)` (politics convention; `feeSchedule` is the current, not the point-in-time, schedule, so the floor 0.04 is a declared conservative rule); **size = min(100 shares, the entry print's size)** (round 1 item 8), unweighted in the primary and size-weighted as reported |
| S2 | **paper maker ask** `a = ceil_tick(max(p_t + 1c, q_t + 2c))` on each unsaid word at in-speech checkpoints with `e_t ≥ 30 min` (1c tick, capped at 0.99); **filled only by trade-through**: the first transaction in `[t, t + 5 min)` with YES-terms price ≥ `a + 1c`; filled size min(100, that transaction's size); one fill per word (the first); maker fee 0, no rebate; held to resolution and **paid on the Gamma resolution** (what the venue paid) |
| W2-rep (Stage 2) | entry at the **recorded best ask** of the `/book` read at `b + 60 s` (receipt-timed from the poll's receipt of the burst-completing edit), size ≤ displayed ask size; exit at the **recorded best bid** of the read at `b + 120 min`; fee as W2 |
| S2-rep (Stage 2) | as S2, on Stage-2 events (prints, trade-through) |
| Binding cost robustness | W2, W2-rep: +1.0c per side keeps net > 0. S2: ask at `ceil_tick(max(p_t + 0.5c, q_t + 1c))` and a 2c trade-through keep net > 0 |

W2 and S2 are at **recorded prints**, not declared quotes (CB13 round 1 item 1: anchor fills on actual prints). Queue
position and displayed depth are unknown historically and disclosed; W2-rep is the recorded-book check.

### 2.2 Clocks

- **Wikipedia revisions.** `timestamp` is the save time (seconds, UTC). A burst completed by the revision at `b` is
  actionable historically from `b + 60 s` (a poller's latency budget); Stage 2 measures the actual poll latency
  (receipt − `rc_timestamp`) and reports it.
- **Data API prints.** `timestamp` (seconds). Prints of one `transactionHash` and condition id are aggregated in memory
  (YES-terms VWAP, min and max YES-terms price, size); the hash is discarded. YES terms as CB13 §2.2.
- **CLOB `prices-history` at fidelity 1 (S).** A point is usable from stamp + 60 s (bucket-end-safe, as CB12 §2.2 at 60
  s). `p_t` = the last usable point before `t` with age ≤ 5 min; `p_lag` = the last usable point before `t − 3 min`,
  a different point from `p_t` (CB10's shared-noise rule). Missing → "unavailable (no price)", counted.
- **Factbase transcript offsets (S).** Seconds from the video's 00:00:00. They are mapped to the wall clock only by
  the causal alignment of §CB14-S. Scheduled `startTime` is used only to bound the fetch window and for `π`'s cut-off.
- **Gamma `startTime`, `createdAt`.** As fetched (hindsight labels, as CB12-M). `closedTime` is never used.

### 2.3 Uncertainty and decision rule

As CB13 §2.3: unweighted primary unless stated; one-sided p = the max over the declared cluster ways; 2,000-draw cluster
bootstrap, **seed 1414**; small-G rule as CB10 §2.3 (G ≥ 30 CR1; 15-29 CR2 with t(G − 1) and the Webb wild bootstrap,
9,999 draws; G < 15 the way leaves the max and its leave-one-cluster-out sign rule binds, as A-C1); top-5 drops;
"unknown" never counts as met.
- **Cluster ways.** **W1:** subject (Wikipedia page id) and ISO week of `D0` (one political crisis can move several
  subjects in one week). **W2:** subject; ISO week of `b`; **story day** (round 1 item 3): the UTC day of `b` × the
  subject's **country**, where country is set by a frozen map from the subject's stored Wikipedia short description
  (a demonym and country-name list → ISO 3166 code, written in part W before any revision or print is read; the first
  match wins, "American" → US, "British" → GB, and so on); a subject whose description matches no entry is its own
  country (a singleton). All W2 units of one country on one UTC day form one cluster. The census reports the share of
  subjects with a mapped country. **S1, S2:** event; ISO week of the event; **normalised term** (round 1 item 5: the
  market's term after the frozen normaliser, e.g. "tariff" / "tariffs" → `tariff`), because one speaker's terms recur
  across many events and share one `Ŝ_w` error. Words of one speech share the speech; every S unit of one word shares
  `Y`, so the **word is weighted 1, split over its units**. p = the max over the listed ways.
- **Testability minimums.** ≥ 100 units and ≥ 30 clusters in the first way, except **W1 (declared deviation, allowed by
  the round-1 ruling only with item 1 adopted): ≥ 40 decisive moves in ≥ 30 subjects and ≥ 15 ISO weeks** (CH123's own
  kill plus the ruling's week minimum; a decisive move is a rare event, and 100 would make W1 untestable by
  construction). Below it, W1 is "not testable (population)", counted with p = 1.
- **Stage 1 (4 tests).** Advance iff one-sided p < 0.01, the §2.4 floor is met, every binding placebo, robustness check
  and gate holds, **and** the test passes a batch Holm step-down at one-sided α = 0.05 over k1 = 4 (fixed; first step
  0.0125, so any p < 0.01 passes; stated for completeness, never withdraws an advance). BY label (q = 0.10 over
  `battery2.cumulative_count()` at the run) is triage only.
- **Stage 2.** One Holm at one-sided α = 0.05 over every CB14 test reaching Stage 2. A test that finishes before k2 is
  known is judged against **α/4** (k = 4, the largest possible Stage-2 count; Holm's first step, never withdrawn), strict
  `<` (CB12 B13). Once every triggered test is final, the full Holm over the actual k2 is applied once and can only add
  passes. Labels: W1-rep, W2-rep "prospective live window, recorded books (L2)"; S1-rep, S2-rep "out-of-time post-freeze
  events (L2)".
- **Stage P** is a separate registration for any survivor (§2.9).

### 2.4 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate |
|---|---|---|
| W1 | lead (mechanism) | `Δ_W1 = mean_D (L_D − π̂_D) ≥ +0.25`: the share of decisive moves with a burst ≥ 5 min before the move's start `D0`, at a state within 5c of the pre-move VWAP, exceeds the same subject's hot-period placebo share by ≥ 25 pp (CH123's "share with lead > 5 min ≥ 25%", taken as an excess over a hot story) |
| W2 | economic, recorded prints | mean net ≥ **+1.0c per share** after both fees (CH123's precision economics: a blind false positive costs about 4-5c) |
| S1 | forecasting | slope `β̂ ≥ 0.30` of `Y − p_t` on `q_t − p_lag` (CH121's floor) |
| S2 | economic, recorded prints | event-weighted mean net ≥ **+1.0c per filled share** (CH121's floor) |
| W2-rep | economic, recorded books | net ≥ +1.0c per share |
| W1-rep, S1-rep, S2-rep | as Stage 1 | as Stage 1 |

### 2.5 Counting (M3 rule)

- Kinds **`cb14_test`** (Stage-1 per-test lines), **`cb14_replication`** (Stage 2) and **`cb14_descriptive`**
  (EXCLUDE). Descriptive lines cover smokes, audits, pre-gates, censuses, gates, the burst-rule grid, precision, the
  lead distribution and false-burst rate (CH123's quantities, reported), deaths, per-class and per-speaker strata, the
  latency measurement, the transcript-Gamma agreement audit, and P-only and N-only readings. Per-test lines count 0
  themselves. **The tests are the `n_tests` of the `ml_explain` count lines** (as CB11-CB13); placebo lines count 0. New
  `battery2.KIND_RULES` entries mirror CB13's; unknown kinds raise.
- **Count lines and `n_tests`:** `creative_batch_14:W` **2** (W1, W2); `creative_batch_14:S` **2** (S1, S2). Replication
  lines `creative_batch_14:<family>:rep` carry `n_tests` = that family's triggered Stage-2 tests (W ≤ 2, S ≤ 2).
- **Triggers.** W1-rep iff W1 advanced; W2-rep iff W2 advanced; S1-rep iff S1 advanced; S2-rep iff S2 advanced.
- **Cumulative count:** 1,221 on HEAD at the round-1 response (`battery2-count-v1`; §0.2), not stable (the host adds
  about 55-60 counted `flow_screen` lines a day). Every counting CB14 job records **the value at its run, after the host
  union**; no projected total is stated (round 1). CB13 reserves 3-8. **CB14 adds 4 fixed tests and up to 4 conditional
  ones. Budget: 4-8.**
- Tests behind a failed or unknown gate (smoke, disjointness, GW0, GWC, GW, GWP, GS0, GSC, GS, GSP, GSP2, availability,
  the Stage-2 population minimums) are "not testable" or "not run" (p = 1) and are **still counted**. A job waiting on
  exit 75 or on `T14_S_open` is "pending" and produces no line. Conditional tests count only if their trigger fires; a
  triggered test that cannot run is counted with p = 1.

### 2.6 Placebos and robustness (common)

Design rule as CB13 §2.6: every binding placebo names the alternative under which the test would advance; calibration
placebos are judged on the p threshold alone (floors off); 200 draws; **advance rate ≤ 1.5%**. Seeds 14101-14120.
Common binding robustness for any advance: (i) the declared cost robustness (§2.1) for economic tests; (ii) the p
threshold and the floor hold without the top 5 clusters of each way; (iii) sign by period (each half of the calendar by
unit time; leave-one-quarter-out sign); (iv) unavailable units are excluded and counted by label, never imputed; a test
whose available share of eligible units is < 60% is "not testable (availability)".

### 2.7 Pre-freeze census and pre-fetch gates (counts only)

Outcome guards first; field-restricted and causal accessors. A unit test asserts that no census path receives a Gamma
outcome, a W print after any unit's decision time used as a target, an S price after `t`, or a target-transcript
offset after `e_t`.
- **W pre-fetch gate GWC (q0305; frame and map only, before ~5,000 requests).** ≥ 150 mapped markets in ≥ 60 events and
  ≥ 40 subjects after key drops, GW0 PASS and frame completeness ≥ 95% (below). Else W1 and W2 "not testable
  (population)", counted, and q0306/q0307 are never committed.
- **W census (q0308).** Frame by query term, class (resign / out-as / fired / removed / indicted; deaths reported),
  listing year and status; key drops by source (and the full-series counterfactual); CB11-A entity overlap count;
  subjects; revisions by subject; article-age failures; bursts by subject, by state band and by the burst-rule grid
  (features: edits only); print reach (the share of each market's observed life covered by its newest-first prints);
  W2 units by label ("no state", "state outside [0.05, 0.60]", "uncovered", "no entry print", "no exit"); decisive moves by
  subject and ISO week (a price-only denominator, never related to bursts here), and those dropped as "no placebo";
  the share of subjects with a mapped country; revisions with hidden user names (revision-deleted names count as
  **unknown**, never as a distinct user; round-1 ruling 4). **Gate GW:** W1 needs ≥ 40 decisive moves in ≥ 30 subjects
  and ≥ 15 ISO weeks; W2 needs ≥ 500 units in ≥ 40 subjects and ≥ 30 ISO weeks; reach coverage of W2-eligible
  burst times ≥ 60%. **Power gate GWP.** W1: `MDE_W1 = (z_0.99 + z_0.80) × 1.2 × 0.5 / √G_min` (the binomial worst case
  over the smaller of the two ways' G); W1 "not run (power)" if `MDE_W1 > 0.50` (2 × floor). W2 (feature-only proxy, as
  CB12 GFP): the same estimator and ways on the **pre-burst round trip** (entry at the max print in `[b − 2 h 15 min,
  b − 2 h]`, exit at the min print in `[b − 15 min, b)`, fees as W2), which has the dependence of the 2 h net and no
  post-burst information; only clustered SEs are written (unit-tested); `MDE = 3.16 × 1.2 × SE`; W2 "not run (power)"
  if `MDE > 2.0c`.
- **S pre-fetch gate GSC (q0316; frame and map metadata of P and N, before ~10,000 requests).** ≥ 100 primary-speaker
  events with a mapped Factbase record across P ∪ N in ≥ 30 ISO weeks, ≥ 25 of them in P, GS0 PASS, the S smoke's
  1-minute availability rule PASS for the P months used. Else S1 and S2 "not testable (population)", counted, and
  q0317/q0318 are never committed.
- **S census (q0319; after q0317 and q0318).** Events by subset, speaker, type (speech, press conference, interview,
  remarks) and month; members; term-parser failures; Q&A-excluded events; transcript mapping and parse failures;
  alignment success and the anchor-count distribution; units by label ("unaligned", "said", "before 10 min", "outside
  [0.03, 0.97]", "no price"); `q_t − p_lag` distribution (features: prices before `t`, causal transcript accessor);
  S2-eligible units and fills (fills are print mechanics, not outcomes). **Gate GS:** ≥ 100 events with ≥ 1 unit in ≥ 30
  ISO weeks; ≥ 1,000 words with units; alignment success ≥ 60% of mapped events. **Power gates.** GSP (S1): one latent
  per word, `Z_w = √0.15·V_week + √0.25·U_event + √0.15·T_term + √0.45·ε_w` (CB12 GMP loadings with a **term factor**
  `T_term` shared by every word of one normalised term, round 1 item 5; the event loading moves from 0.30 to 0.25 and the
  idiosyncratic from 0.55 to 0.45 so the total stays 1), `Y*_w = 1{Φ(Z_w) > 1 − π_w}` with
  `π_w` the word's start price (one value per word, as CB13 GRP); 500 draws (seed 14121); `MDE_S1 = 3.16 × 1.2 ×
  max(SD(β̂*), mean SE per way)` over the event, week and term ways; S1 "not run (power)" if `MDE_S1 > 0.60`. GSP2 (S2): the same latents (with the term factor) calibrated to the
  fill price; `MDE_S2 > 2.0c` → S2 "not run (power)". Both counted.
- MDEs are recomputed from these counts and never used to change a floor, window or threshold.

### 2.8 Compute, network, disk and stop rules

- **Host.** 1 OCPU, about 5.6 GiB RAM shared with the collectors (MemAvailable about 4.5 GB at drafting). Queue rules
  as CB13 §2.8: one job per lane, nice 19, `MemAvailable ≥ mem_mb + 1200`, address cap 2 × `mem_mb`, the 02:45-05:30
  UTC blackout for `mem_mb ≥ 500`. Every reader streams one page, one market or one transcript at a time. `mem_mb` ≤ 600
  everywhere (a Factbase page is about 2 MB of HTML, parsed and reduced one at a time).
- **Network** (`net` lane, priorities 10-14; ≤ 2 rps Polymarket, ≤ 1 rps MediaWiki with `maxlag=5`, ≤ 0.5 rps
  Factbase; descriptive User-Agent everywhere):

  | Job | Work | Requests / wall | Stored (cap) |
  |---|---|---|---|
  | q0300 | W smoke | ≤ 30, < 5 min | 0.001 GB |
  | q0301 | S smoke | ≤ 30, < 5 min | 0.001 GB |
  | q0302 | exclusion keys (increment over CB13 q0276) | ≤ 600 Gamma, ≤ 6 min | ≤ 0.01 GB |
  | q0303 | W frame: 15 query terms × closed/active × pages (about 300), event lookups (≤ 600), Wikipedia summaries (≤ 600 at 1 rps), the politics-tag (id 2) one-day walk over two months (2025-03, 2025-11; ≤ 300) | ≤ 1,800, ≤ 30 min | ≤ 0.01 GB |
  | q0306 | revision metadata, `rvlimit=max` (500 per page), from `max(createdAt, 2024-01-01) − 30 d` to `T14_W_end`, for about 150-220 pages (busy pages about 20-40 pages each), plus the bot list | ≤ 5,000 at 1 rps, ≤ 1.5 h | ≤ 0.03 GB |
  | q0307 | Data API prints, ≤ 2 pages of 10,000 per mapped market (about 400-500) | ≤ 1,000, ≤ 10 min | ≤ 0.02 GB |
  | q0312 | S frame: tag 100343 one-week end-date windows over `[2024-11-01, 2026-03-01)` (about 70 windows, ≤ 3 pages), Factbase search for the mapping (≤ 300 at 0.5 rps) | ≤ 520, ≤ 15 min | ≤ 0.005 GB |
  | q0313 | fit transcripts: Factbase records of primary speakers dated `[2023-01-01, 2024-11-01)` (planning 300-500 pages; about 1 GB transferred, reduced at parse) | ≤ 600 at 0.5 rps, ≤ 25 min | ≤ 0.05 GB |
  | q0317 | P: target transcripts (≤ 80), `prices-history` fidelity 1 over `[startTime − 30 min, startTime + 5 h]` per member (≤ 1,300), prints ≤ 2 pages per member (≤ 2,600), Gamma outcomes (≤ 80) | ≤ 4,100, ≤ 40 min | ≤ 0.05 GB |
  | q0318 | N: the same (≤ 230 transcripts, ≤ 3,900 price requests, ≤ 7,800 print requests) | ≤ 12,000, ≤ 1.8 h | ≤ 0.15 GB |
  | q0321 | S Stage 2: the same per post-freeze event, weekly | ≤ 600 a week | ≤ 0.05 GB total |
  | q0310 | W live: recent-changes poll every 60 s (`list=recentchanges`, namespace 0, `rclimit=500`, `rcstart` overlap and `rccontinue`, gaps logged), `/book` reads (≤ 4 per mapped market per burst), daily Gamma refresh (≤ 60) | about 1,500-2,500 a day | ≤ 0.05 GB total |

  Historical `net` total **≤ about 25,700 requests (planning about 18,000-22,000), about 4-5 h of `net` lane**; if GWC
  or GSC fails, the large fetches (q0306/q0307, q0317/q0318) never run. They queue behind CB11 (about 10-15 h), CB12
  and CB13. **A fetch that has not completed (its `*_complete` status absent) is "pending" and is never analysed
  partially.**
- **Disk guard.** As CB13 §2.8: `--disk-cap-gb` per job, `--data-dumps-cap-gb 40`, exit **75** if data-dumps + cap > 40
  GiB or root free − cap < 4.5 GB. CB14 output caps total **≤ 0.4 GB** (W ≤ 0.1 including the live root; S ≤ 0.3).
  Exit-75 waits are "pending". CB14 never deletes or moves host data.
- **Network etiquette.** As CB12 §2.8 (shared `Limiter`, collector yield, 429 / `Retry-After` back-off, stop on
  repeated 429, collector-health stop). MediaWiki requests carry `maxlag=5` and back off on `maxlag` errors.
- **Stop rules.** 5 CPU-hours per family. A job that fails twice for the same non-transient reason stops and is
  recorded. A null is "not detected at MDE x". **No re-screen of a failed CB14 test** with altered query lists,
  classes, entity or mapping rules, burst or decisive-move rules, windows, entry or exit rules, the position model,
  alignment, checkpoints, cutoffs or populations, on any data.

### 2.9 Funnel and Stage P

Screen (Stage 1) → gates, placebos, robustness → replication (Stage 2: live recorded books for W; post-freeze events
for S) → separate prospective confirmation (Stage P) → economic validation at recorded prices with fees, spread and
depth.
- **Stage P-W.** A fresh live window after `T14_W2_end`, with a frozen map rule (no weekly re-audit), the live burst
  rule and recorded asks and bids; the economic test is W2-rep's rule, with depth.
- **Stage P-S.** Live mention events after `T14_S2_end`: a live caption or transcript clock (the alignment needed no
  hindsight, so it can run live), CLOB `/book` reads every 5 min during the speech, S2's ask rule at recorded books.

---

## 3. Tests

### CB14-W: Wikipedia edit-burst lead for personnel and status markets (CH123)

**Question.** When a named person resigns, is ousted, fired, removed or indicted, does a burst of edits on the person's
English Wikipedia article appear minutes before Polymarket's decisive move, while the price still leaves room to buy?
Does buying after bursts pay after fees, given that most bursts are noise?

**Mechanism.** Editors update articles within minutes of the first wire or official post, and every save is timed to
the second. Polymarket's personnel markets are thin and are watched by few people at off-hours, so they may reprice over
5-60 minutes. CB11-A's pageviews arrive 48-69 h late; edits do not. Who pays: stale asks before the event and holders
who sell into the first move. Why it persists: the market-to-article join is a chore, events are rare per market, and
the edit feed is noisy. **The opposite is as plausible:** the venue's politics traders read the same wires and post
faster than editors, in which case W1 fails (that is the test).

**Prior work.** CH97 / CB11-A (pageviews, not run), CH107 and CH109 (siblings, not tested). No AREPO test has read
revisions. W is not a re-screen of anything.

**Population (q0303; frozen).**
- **Frame.** Gamma `public-search` with the frozen query list (§1.4), `events_status` closed and active, each paged
  until `hasMore` is false; members of matched events whose **question** matches the frozen W title regex
  `(?i)\b(resign(s|ed|ation)?|out as|out by|fired|steps? down|removed (as|from)|leaves? office|ousted|impeach(ed|ment)?|indicted|charged)\b`
  and names one person; binary; `createdAt` in `[2023-07-01, 2026-03-01)`; not sports (registry, coach regex), not a
  mention market (tag 100343 or "say"), not entertainment ("who will die in"); **deaths** ("die", "dies", "pass away")
  form a reported stratum only. Key drops (§1.3). Open and closed markets are both kept; **no status, `closedTime` or
  outcome condition** (premise 1).
- **Frame completeness (binding).** A one-day `end_date` walk of Gamma tag 2 (politics) over 2025-03 and 2025-11
  applies the same title regex; the search frame must contain ≥ 95% of the walk's matching markets, else W is "not
  testable (frame completeness)", counted.
- **Subject map (frozen).** Subject `e` = CB11-A's entity rule on (question, event title) plus a frozen office-word stop
  list ("President", "Prime Minister", "CEO", ...); Wikipedia REST `page/summary/<e>` must return `type = standard`
  (redirects followed); the page id, canonical title and short description are stored. **Article age:** the page's
  first revision must be ≥ 30 days before a unit's time (else "article too new", counted; articles created by the event
  are removed). **Gate GW0 (blind audit):** every mapped (question, canonical title, description) pair is labelled
  "the article is the person the market names / not" by a `science-reviewer` agent, with no edit, price or outcome
  visible; the audit file is committed before q0305. Pairs labelled "not" are dropped (counted); one blind revision of
  the entity rule is allowed if precision < 90%, re-audited on the new pairs; a second failure → W "not testable
  (map)", counted.

**Bursts (frozen a priori; features from revisions only).** For a page, at the save time `b` of a revision:
- in `(b − 10 min, b]` there are **≥ 3 revisions by ≥ 2 distinct non-bot users** (a bot = an account in the bot group
  list fetched by q0306, or a user name matching `(?i)bot\b`), with **Σ|Δsize| ≥ 100 bytes**, not counting revisions
  that are themselves reverts at save time (tags `mw-undo`, `mw-rollback`, `mw-manual-revert`, or a frozen revert
  comment regex); `mw-reverted` is never used (premise 4);
- the 10-minute count is **≥ the 99th percentile** of the page's 10-minute counts (sliding by minute) over `[b − 30 d,
  b − 1 d]` (causal; a page with < 30 d of history in that window is "no baseline", counted);
- a burst starts a 6 h refractory period for that page (one burst per 6 h per subject).
The grid (≥ 4 edits; the 95th percentile; 5-minute window) is **reported, uncounted**.

**Prices (Data API prints, aggregated to transactions).** The **state** of a market at `t` is the YES-terms price of
its last transaction in `[t − 6 h, t)` (none → "no state"). A time is **covered** if the market's newest-first prints
reach back past it (else "uncovered", counted).

**Decisive move (frozen; price only, no outcome; round 1 items 1 and 10).** For a market, `D` = the time of the first
transaction with YES-terms price ≥ 0.90 that is **confirmed** by a second transaction ≥ 0.90 within 30 min, such that the
YES-terms VWAP `V_D` of its transactions in `[D − 24 h, D − 2 h]` is ≤ 0.50 (≥ 1 transaction there; covered). The
**move start** `D0` = the first transaction in `[D − 2 h, D]` with YES-terms price ≥ `V_D + 20c` (it always exists,
because `D` itself qualifies). One `D` per subject per 7 days (the earliest over the subject's markets). Gamma outcomes
are not used to define `D` or `D0` (the census counts, for audit only, how many `D` lie in markets that resolved NO).
The 0.90 crossing `D` is reported only; **every W1 lead is measured from `D0`, the start of the move.**

**W1 (lead from the move's start).** For each decisive move (SCREEN = all W calendar; there is no historical split):
- `L_D = 1` iff a burst `b` of the subject lies in `[D0 − 120 min, D0 − 5 min]`, the market's **state at `b` is ≤ `V_D
  + 5c`** (the price had not started to move when the edits came), and an entry print `e(b)` (max YES-terms price in
  `[b + 60 s, b + 15 min]` in the market of `D`) exists. No print → `L_D = 0` (conservative). A burst after the first
  repricing (state above `V_D + 5c`) never counts as a lead (round 1 main challenge: in 0.30 → 0.70 → 0.92 the draft
  counted a burst at 0.70).
- **Comparator: the hot-period placebo (round 1 item 1, binding as the comparator).** For anchors `τ_k = D0 − 6 h · k`,
  `k = 1 … 11` (so `τ` in `[D0 − 66 h, D0 − 6 h]`, inside `[D − 72 h, D − 6 h]`), the same indicator with `τ_k` in place
  of `D0` and `V(τ_k)` = the VWAP of `[τ_k − 24 h, τ_k − 2 h]` in place of `V_D`; `π̂_D` = its mean over the anchors that
  are covered and after listing (< 3 such anchors → "no placebo", counted). This is the story-is-unfolding period, when
  editing is already elevated, so `Δ_W1` measures what bursts add **beyond a hot story**.
- `Δ_W1 = mean_D (L_D − π̂_D)`; one-sided > 0; floor +0.25; p = max over the subject and ISO-week ways.
- **Binding calibration placebo (subject time shift).** Bursts of each subject are shifted by a uniform random offset
  in `[−60, −30]` days (one per subject per draw; 200 draws, seed 14101) and the statistic recomputed. *Alternative
  guarded:* subjects with busy articles have many bursts, so any 2-hour window of theirs looks "led".
- **Binding robustness.** Each keeps the sign and p < 0.05: lead window `[D0 − 60 min, D0 − 5 min]`; state cap `V_D +
  2c`; **entry window `[b + 3 min, b + 15 min]`** (round 1 item 9: poll latency may exceed 60 s); CB11-A entity subjects
  dropped (§1.3); heads of government and state dropped (frozen list from the subject description); each class with
  ≥ 15 `D` (resign, out-as); each half of the calendar; top-5 subject and week drops.
- **Reported (uncounted).** The draft's fixed-lag comparator (windows shifted by −7, −14, −21, −28 days); a
  **burst-only placebo** that needs no prints (the share of hot-period and fixed-lag windows that contain a burst,
  round 1 item 11); the number of decisive moves dropped as "no placebo" because the market was listed < 18 h before
  `D0` (fast-resolving events, item 11); CH123's lead distribution from the 0.90 crossing (the first burst minus `D`,
  median and share > 5 min, including negative leads), by class and for deaths; the burst-rule grid.

**W2 (burst-triggered taker, recorded prints).** Units: bursts `b` of mapped subjects in the W calendar for which the
subject has a **trade market** `m(b)` = the subject's market with the nearest scheduled end at or after `b + 3 h` whose
state at `b` is in **[0.05, 0.60]** and whose prints cover `[b − 6 h, b + 2 h 30 min]` (frozen choice; other markets
reported). `net(b) = x − e − r·e(1 − e) − r·x(1 − x)` (§2.1). Mean over units (each burst weight 1), one-sided > 0,
floor +1.0c; p = max over subject, ISO-week and story-day ways (§2.3, round 1 item 3).
- **Binding pre-burst placebo.** The same rule at `b − 24 h` (entry and exit windows shifted by 24 h) must not pass
  p < 0.01. *Alternative guarded:* W2 picks volatile subjects and periods in which buying YES paid regardless of the
  burst (a YES-heavy selection of subjects).
- **Binding "before the move" check.** Restricted to units with `|state(b) − state(b − 60 min)| ≤ 5c`, W2 keeps the sign
  and ≥ half. *Alternative guarded:* the burst merely follows a move already under way (momentum), which a reader of
  prices alone would capture.
- **Binding worst-case reach.** p < 0.01 and the floor still hold when every burst that would be a unit but for
  "uncovered", "no entry print" or "no exit" is included at net = `w* = min(−9.3c, m̄₀)` (round 1 item 2), with −9.3c the
  p90 round trip of `EXECUTION_COSTS.md` (line 39) and `m̄₀` the mean net of covered W2 units **without** a ≥ 20c YES-terms
  rise within 2 h (what a false burst costs in this population). *Alternative
  guarded:* newest-first prints reach less far back in markets that later traded heavily, which are the markets where
  the event happened, so dropping uncovered bursts drops pre-event false bursts of YES markets and flatters W2 (CB12
  round 1 item 4).
- **Robustness (binding).** +1.0c per side; exit at `b + 1 h` keeps the sign; state band [0.05, 0.40] keeps the sign;
  **entry window `[b + 3 min, b + 15 min]`** (item 9); CB11-A entity subjects dropped; "stale exit" units dropped; top-5 subject, week and story-day drops; leave-one-quarter-out sign.
- **Reported (uncounted).** Precision (the share of bursts followed by a ≥ 20c YES-terms rise within 2 h), the
  false-burst rate, net by class and state band, capacity (transaction sizes after the burst), the taker NO fade.

**Power (planning; GW and GWP decide).** W1: with 40-80 decisive moves in 30-55 subjects, `MDE_W1 ≈ 3.16 × 1.2 × 0.5 /
√G ≈ 0.26-0.35` against the 0.25 floor, so W1 detects an excess of about 0.3 or more. GW fails below 40 moves (CH123's
own kill), which is a real possibility. W2: if 1,000-3,000 units in about 100-150 subjects, with SD(net) about 8c
(heavy-tailed: most bursts lose the round trip, a few gain 30-60c) and a design effect of about 3, `SE ≈ 0.25-0.45c`
and `MDE_W2 ≈ 0.95-1.7c` against the 1.0c floor. The top-5 subject drop binds hard on a heavy-tailed mean: a W2 carried
by a few resignations fails it, which is the intended reading.

**Stage 2 (conditional; q0310 collects unconditionally from `T14_W2_start`; q0311 analyses).** The frozen query list and
entity rule run daily on active markets; new pairs enter a weekly blind audit batch (units of pairs failing it are
dropped, counted). The poller reads `list=recentchanges` every 60 s with receipt times, applies the frozen burst rule
(trailing baselines bootstrapped from the revisions API at subject entry) with **the Stage-1 bot rule** (the bot-group
list fetched at q0306, frozen, plus the name regex; round 1 item 12), and on a burst reads CLOB `/book` for each of
the subject's mapped markets at `b + 60 s`, 5, 15 and 120 min. **Gap detection (item 12):** each poll requests
`rcstart` = the newest `rc_timestamp` already held minus 120 s (overlap), follows `rccontinue` until exhausted, and
de-duplicates by `rcid`; if a poll fails, or the oldest returned change is newer than the requested start while no
continuation remains, or no successful poll ran for > 5 min, the uncovered interval is logged and every burst whose
10-minute window or 30-day baseline day intersects it is "unavailable (gap)", counted, never filled.
- **W2-rep** (if W2 advanced): W2's unit and state rules (state from the 60 s book's mid in [0.05, 0.60]), entry at the
  recorded best ask at `b + 60 s` (size ≤ displayed), exit at the recorded best bid at `b + 120 min`; needs ≥ 300
  bursts in ≥ 30 subjects by `T14_W2_cap`, else "not run (power)", counted.
- **W1-rep** (if W1 advanced): decisive moves of mapped markets in the live window from post-hoc Data API prints, with
  the live burst log (receipt-timed) as the lead clock; needs ≥ 20 moves in ≥ 15 subjects by the cap (likely "not run
  (power)", counted).
- Reported: poll latency (receipt − `rc_timestamp`), ask life after bursts, depth at the touch.

### CB14-S: Intra-speech hazard decay for mention baskets (CH121)

**Question.** Once a speech is under way, does the price of a word not yet said fall as fast as the speaker's own past
speeches say it should? If the crowd holds unsaid words flat, does a model anchored on each word's start price and the
speech clock predict resolution beyond the in-speech price?

**Mechanism.** Each word is a hazard process on the speech clock. In this speaker's past transcripts, topical words
appear early and others late. Given that a word is unsaid after `e` minutes, the chance it is said by the end falls
with `e` in a word-specific way. Re-pricing 15-35 words every few minutes is tedious, so holders and makers may leave
unsaid words near their start prices until the last minutes. Who pays: holders waiting for "he will get to it" and
makers whose asks ignore the clock. Why it persists: the model needs a transcript archive and a clock.

**Prior work.** CH112 / CB12-M (pre-start basket sum; not run), CH32 (per-word base rates; never tested). No test has
used an in-speech checkpoint. **Overlap with CB12-M is declared and handled in §1.3** (P disjoint; N nested after
CB12-M's Stage-1 result; HOLDOUT never).

**Population (q0312; frozen).** Gamma closed events with tag id 100343, event `endDate` in P ∪ N, ≥ 8 binary members,
`startTime` present, the occasion rule `endDate − startTime ≤ 36 h`, **not sports** (CB12-M's registry and broadcast
regex), key drops (§1.3, with the N deviation), **primary speaker** (the speaker rule of §1.4; a frozen title map from
event title to Factbase `speaker_id`; others reported). Rule booleans parsed from each member's description: Q&A
included (events whose rule excludes Q&A or a section are dropped, counted), plural and possessive forms, compounds.
- **Transcript map (frozen; metadata only).** The event maps to the Factbase record of its speaker whose UTC date is
  within ±1 day of `startTime` and whose type matches the event title's type (speech, rally, address, press conference,
  interview, remarks), with frozen title-keyword tie-breaks; no match or several ties → "unmapped", counted. **Gate GS0
  (blind audit):** a seeded 120-event sample (seed 14122) of (event title, `startTime`, record title, date, type) is
  labelled match / not by a `science-reviewer` agent with no transcript text, price or outcome; precision ≥ 90%, one
  rule revision allowed, else S "not testable (map)", counted.
- **1-minute availability (P months).** The S smoke checks fidelity-1 rows in `[startTime, startTime + 2 h]` for 2
  members of each of 3 out-of-frame mention events per month in 2024-11 … 2025-05 (non-primary-speaker or sports
  events, so not S units). A month with < 4 of 6 members returning rows is dropped from P by rule (counted). The rule
  reads row counts only.

**Position model (q0314; frozen; fit transcripts only).** For each primary speaker, from fit transcripts dated
`[2023-01-01, 2024-11-01)` (Factbase; the same type map), with `L_s` the last offset of speech `s`:
- for a term `w` (the market's term and its rule variants, matched by the frozen normaliser), `S_w(e)` =
  `P(first mention of w > e | w said in s, L_s ≥ e)` over fit speeches, by type class (prepared speech / press
  conference or interview);
- shrinkage: `Ŝ_w(e) = (n_w·S_w(e) + 10·S_pool(e)) / (n_w + 10)`, `n_w` the number of fit speeches with `L_s ≥ e`
  that said `w`, `S_pool` the same quantity pooled over every term of every frame member (term list from frame text
  only); a term never said in the fit speeches uses `S_pool`;
- the model file stores `Ŝ_w` on a 1-minute grid to 180 min per (speaker, type class, term). It is written before any
  S price, print or target transcript is read (q0317/q0318 refuse unless its sha256 is pinned in part S).
- **Anchor.** With `π_w` the word's start price, `q_t = π_w·Ŝ_w(e_t) / (1 − π_w + π_w·Ŝ_w(e_t))` = `P(said by the end
  | unsaid after e_t)` under the prior `π_w`. A start-level bias in `π_w` is inherited by `q_t` (§1.3).

**Clock alignment (frozen; causal; round 1 item 4).** The transcript clock is mapped to the wall clock from the price
jumps of words already said, using **nothing beyond the causal clock**:
- an **anchor candidate** is a member `j` with a jump time `J_j` = the first minute at which its 1-minute price is ≥ 0.85
  while its price 3 minutes earlier was ≤ 0.60, and transcript first-mention offset `o_j`; `δ_j = J_j − o_j`;
- at checkpoint `t`, the anchor set `A_t` and `δ_t` are the **self-consistent fixed point**: start from the candidates
  with `J_j ≤ t − 1 min`; set `δ_t` = the median `δ_j` over the set; keep only anchors with `o_j ≤ e_t = t − δ_t`
  (an anchor's mention must lie inside the causal clock); repeat until the set is stable (≤ 10 iterations; no
  convergence → "unaligned", counted). The unit is aligned iff ≥ 2 anchors of `A_t` lie within 5 min of `δ_t`
  (unit-tested, including a fixture where an anchor's `o_j` falls after `e_t` and must be dropped);
- the transcript clock is `e_t = t − δ_t`; a word is **unsaid at `t` iff it is not said by `e_t`** (first-mention offset
  > `e_t`, or never said). The draft's `e_t + 60 s` margin is removed: it needed offsets in `(e_t, e_t + 60 s]`, where
  `Y = 1` by definition, and it dropped exactly the words about to be said, which are S2's adverse fills (round 1 main
  challenge). The causal accessor returns only offsets ≤ `e_t` (unit-tested). A viewer at `t` knows which words have
  been said, when the speech started, and that it is still running (units need `e_t < L`).
- **Causal price-only exclusion.** A unit whose word's 1-minute price rose by ≥ 15c over `[t − 5 min, t]` is excluded
  ("rising", counted). It reads prices before `t` only. It removes words the room has just heard but the transcript
  clock has not reached.
- **Disclosed bias.** `δ_j` contains the market's reaction lag (the jump follows the mention), so `e_t` runs early by
  a variable amount. A word said between `e_t` and the true clock enters as unsaid with `Y = 1`. For S1 that pushes the
  slope down (a low `q_t` with `Y = 1`), and for S2 it is a real adverse fill that a live maker would also suffer. The
  binding ±2 min check below bounds its effect.
- `π_w` = the word's last usable price before `δ_first − 5 min` (`δ_first` the event's first aligned `δ_t`), i.e.
  before the speech started.
- **Pre-roll (round 1 item 13, reported plus robustness).** The census reports each target transcript's first-segment
  offset and the offset of the first segment attributed to the primary speaker. A robustness check re-bases fit and
  target offsets to the first primary-speaker segment (the model refitted once on re-based fit offsets, hashed with the
  primary model before any S read).

**Units.** (word, 5-minute wall-clock checkpoint `t`) from the first aligned `t` with `e_t ≥ 10 min` (the first minutes'
mentions are information events, not decay), the word unsaid by `e_t`, not "rising", `p_t ∈ [0.03, 0.97]`, `p_lag`
available. **Each word weight 1, split over its units** (`Y` is one value per word). `Y` = the Gamma resolution
(guarded; 0.5 for 50-50; unresolved or voided words scored 0.5 with a binding worst case); the transcript-derived `Y`
is a robustness check.

**S1 (forecasting).** The word-weighted OLS slope `β̂` (with intercept) of `(Y − p_t)` on `(q_t − p_lag)` over P ∪ N
units; one-sided > 0; floor 0.30; p = max over the event, ISO-week and normalised-term ways (§2.3, round 1 item 5).
- **Binding sign-flip calibration.** One coin per event flips the regressor; 200 draws (seed 14102). *Alternative
  guarded:* within-speech dependence (a long speech says many late words) makes the clustered p anti-conservative.
- **Binding clock attribution (joint fit).** A joint OLS of `(Y − p_t)` on `(q_t − p_lag)`, `(π_w − p_lag)` and
  `(p_lag − p_{t−15 min})` must keep the `q_t` coefficient at ≥ half its solo value with one-sided p < 0.05 (max over
  ways). Otherwise S1 cannot advance, and the label is "start-price drift or momentum, not the clock". *Alternative
  guarded:* the anchor predicts only because unsaid words drift down from their start price anyway (the M1 object, or a
  generic in-speech drift).
- **Binding clock-shift check (round 1 item 4).** With `e_t` shifted by −2 min and by +2 min (units, "unsaid" and `q_t`
  recomputed), S1 keeps its sign and one-sided p < 0.05 in both.
- **Robustness (binding; each keeps the sign).** P alone and N alone (the disjoint and nested halves, §1.3);
  transcript-derived `Y`; `e_t ≥ 20 min`; 10-minute checkpoints; shrinkage weight 5 and 20; prepared speeches only;
  events whose first anchor is > 90 min after `startTime` dropped; offsets re-based to the first speaker segment;
  unresolved words at `Y = 1`; top-5 event, week and term drops; each calendar half.
- **Reported (uncounted).** The slope by elapsed band (10-30, 30-60, > 60 min), by type and by start-price band; the
  transcript-Gamma agreement (< 95% → the label "settlement basis"); non-primary speakers; the unconditional mean of
  `Y − p_t` on unsaid words (the level, which is CB12-M's object, reported only for P).

**S2 (in-speech maker, recorded prints).** On every word with an S2-eligible unit (`e_t ≥ 30 min`, unsaid, aligned),
the ask and trade-through fill rule of §2.1; net per filled share `= a − Y`. Statistic: mean over events with ≥ 1 fill
of the event's net per filled share (events without fills counted); one-sided > 0; floor +1.0c; p = max over event,
week and normalised-term ways. S2 fills are in-speech, so they never coincide with CB12-M's M2 fills, which stop at `startTime`.
- **Binding placebo (calibrated at fill).** `Y*` drawn calibrated to the fill-time price with the GSP latents; 200 draws
  (seed 14103). *Alternative guarded:* the trade-through rule selects fills after up-moves, so a maker could look
  profitable on fill mechanics alone (CB12-M M2's placebo).
- **Robustness (binding).** §2.1 cost robustness; worst-case reach (members whose prints do not reach back to `t` are
  filled at `a` for 100 shares iff `Y > 0`, as CB12 A4); **the ±2 min clock shift keeps the sign and p < 0.05**
  (item 4); P alone and N alone keep the sign; top-5 event and term drops.
- **Reported.** The taker variant (buy NO at the min-YES print in `[t, t + 2 min]` when `p_t − q_t ≥ 8c`, fee
  `r·a(1 − a)` with `r = max(feeSchedule.rate, 0.05)`); capacity; the event-level loss distribution.

**Power (planning; GSP and GSP2 decide).** P alone: about 45-55 events, about 800 words, `SE(β̂) ≈ 0.22-0.26`, MDE about
0.7-0.8 (why N is needed). P ∪ N: about 190-260 events, 3,000-4,300 words; with SD(`Y − p_t`) about 0.35, SD(`q_t −
p_lag`) about 0.06-0.10 and an event design effect of about 3, `SE ≈ 0.11-0.16` and **`MDE_S1 ≈ 0.35-0.50`** against
the 0.30 floor. The GSP copula's event factor may raise it; S1 is "not run (power)" above 0.60. S2: about 200 events with
2-6 fills each, SD about 35c per filled share, event design effect 2-3: **`MDE_S2 ≈ 2-3c`** against 1.0c, so GSP2 will
probably stop S2 ("not run (power)", counted), as CB12-M expects of M2.

**Stage 2 (conditional; q0321 collects post-freeze events unconditionally; q0322 analyses).** Events with `startTime ≥
T14_S2_start`, the same frame, map, model (no refit), alignment and rules, keys dropped against every frame including
CB14's own Stage-1 events. **S1-rep** and **S2-rep** need ≥ 100 events with ≥ 1 unit by `T14_S2_end` (≥ 60 by the cap,
else "not run (power)", counted).

### CB14-SM: smokes and data jobs

- **q0300 W smoke** (`net`, ≤ 30 requests). PASS needs: the part hashes; refusals on fixtures (every root of §1.1's
  last three rows, `h12_say`, `h11_attn/holdout`, pageview files, `mw-reverted` parsing, forbidden fields `side`,
  `proxyWallet`, `user` written, `outcomePrices` outside the guarded file, any W row at or after `T14_W_end`);
  `public-search` paging to `hasMore = false` on one query term; the entity rule and summary type on 5 out-of-frame
  subjects (markets listed after 2026-03-01); revisions with `rvstart`/`rvend` bounds and continuation on one busy page
  (out-of-window range); the bot list; Data API prints with 2-page reach on one 2024 and one 2025 out-of-frame market
  (row counts; checks that 2024 prints exist, premise 2); `list=recentchanges` returns `rc_timestamp`, title, sizes and
  tags.
- **q0301 S smoke** (`net`, ≤ 30 requests). PASS needs: the S part hash; refusals (N paths before `T14_S_open` with a
  fixture commit; the causal accessor returning nothing after `e_t`; prices after `t` in census mode); the tag-100343
  walk on one out-of-window week; Factbase search and one out-of-window transcript parsed into (offset, text) with ≥ 100
  stamps; the term parser and matcher on 3 out-of-window events; the 1-minute availability rule on the P months
  (row counts only, §CB14-S).
- Any failure → the dependent family is "not testable (source)", counted. No rule is re-fitted.
- **Audits.** GW0 (every W pair) and GS0 (120 S events) are repo steps by a `science-reviewer` agent with no price,
  edit, transcript text or outcome; their files (`creative_batch14/w_map_audit.json`, `s_map_audit.json`) are committed
  with seeds and ids before the pre-gates.
- Every data job writes a manifest (file sha256, request counts, failures, data-dumps size and margin, free disk) and a
  `*_complete` status.

## 4. Jobs (draft specs; JSON in this document only)

Fields follow `queue/README.md`. `argv[0]` is under `backend/scripts/`, and `cwd` is `backend`. **None is written to
`queue/jobs/` or `queue/drafts/`** before its code and tests exist and pass a `science-reviewer` freeze check. Analysis
jobs also need their family's freeze. All `family` = `creative_batch_14`. Priorities: `net` 10-14 (below CB13's 15-19);
`cpu` 14.

| Id | Lane | Priority | Size / time | Depends on | Commit when |
|---|---|---|---|---|---|
| q0300 | net | 14 | ≤ 30 req, < 5 min, mem 400 | - | common + W rules parts and smoke code reviewed |
| q0301 | net | 14 | ≤ 30 req, < 5 min, mem 400 | - | S rules part and smoke code reviewed |
| q0302 | net | 14 | ≤ 600 req, ≤ 6 min, mem 500 | q0300, CB13 q0276, CB11 q0227 | with q0300's PASS |
| q0303 | net | 13 | ≤ 1,800 req, ≤ 30 min, mem 400 | q0302 | with q0302 |
| q0305 | cpu | 14 | no network, ≤ 10 min, mem 300 | q0303, GW0 file | after GW0 is committed |
| q0306 | net | 12 | ≤ 5,000 req at 1 rps, ≤ 1.5 h, mem 400 | q0305 PASS | only after q0305 PASS |
| q0307 | net | 12 | ≤ 1,000 req, ≤ 10 min, mem 400 | q0306 | with q0306 |
| q0308 | cpu | 14 | ≤ 30 min, mem 600 | q0307 | with q0307 |
| q0309 | cpu | 14 | ≤ 1 CPU-h, mem 600 | q0308, W freeze | after the W freeze |
| q0310 | cron | - | ≤ 2,500 req a day, mem 150 | W freeze | after the W freeze; not before 2026-10-26T00:00Z |
| q0311 | cpu | 14 | ≤ 30 min, mem 500 | q0309, q0310 window end | only if W1 or W2 advanced |
| q0312 | net | 13 | ≤ 520 req, ≤ 15 min, mem 400 | q0301, q0302 | with q0301's PASS |
| q0313 | net | 12 | ≤ 600 req at 0.5 rps, ≤ 25 min, mem 500 | q0312 | with q0312 |
| q0314 | cpu | 14 | no network, ≤ 20 min, mem 500 | q0313 | with q0313; model sha256 pinned in part S before q0317 |
| q0316 | cpu | 14 | no network, ≤ 10 min, mem 300 | q0314, GS0 file | after GS0 is committed |
| q0317 | net | 11 | ≤ 4,100 req, ≤ 40 min, mem 500 | q0316 PASS | only after q0316 PASS |
| q0318 | net | 10 | ≤ 12,000 req, ≤ 1.8 h, mem 500 | q0317, `T14_S_open` | only after `T14_S_open` |
| q0319 | cpu | 14 | ≤ 40 min, mem 600 | q0317, q0318 | after both complete |
| q0320 | cpu | 14 | ≤ 1 CPU-h, mem 600 | q0319, S freeze | after the S freeze |
| q0321 | net | 11 | ≤ 600 req a week, mem 400 | S freeze | after the S freeze |
| q0322 | cpu | 14 | ≤ 40 min, mem 600 | q0320, q0321 window end | only if S1 or S2 advanced |

```json
{"id": "q0300_cb14_smoke_W", "title": "CB14-W smoke (common + W part hashes; refusals: live stores, h12_say, h11_attn/holdout, pageviews, mw-reverted, forbidden fields side/proxyWallet/user/outcomePrices, rows >= T14_W_end; public-search paging to hasMore=false on one term; entity rule + summary type on 5 out-of-frame subjects; revisions bounds + continuation on one busy page out of window; bot list; Data API 2-page reach on one 2024 and one 2025 out-of-frame market; recentchanges fields); counts only", "family": "creative_batch_14", "priority": 14, "expected_value": "go/no-go for every W source", "data": ["public Gamma, Data API", "en.wikipedia.org REST + action API"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api, data-api, en.wikipedia.org"}, "depends_on": [], "argv": ["scripts/run_cb14.py", "smoke", "--part", "W", "--rules", "../docs/research_lab/seals/cb14_rules.json", "--rps", "1"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch14/smoke_W.json", "trials.jsonl (cb14_descriptive)"], "next_action": "PASS: q0302; FAIL: W not testable (source), counted", "notes": "CREATIVE_BATCH_14.md CB14-SM. DRAFT. <= 30 requests."}
{"id": "q0301_cb14_smoke_S", "title": "CB14-S smoke (S part hash; refusals: N paths before T14_S_open, causal accessor after e_t, prices after t in census mode; tag 100343 walk on one out-of-window week; Factbase search + one out-of-window transcript parsed to >= 100 stamps; term parser/matcher on 3 out-of-window events; 1-minute availability rule on P months, row counts only)", "family": "creative_batch_14", "priority": 14, "expected_value": "go/no-go for every S source", "data": ["public Gamma, CLOB prices-history", "rollcall.com factbase"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api, clob, rollcall.com"}, "depends_on": [], "argv": ["scripts/run_cb14.py", "smoke", "--part", "S", "--rules", "../docs/research_lab/seals/cb14_rules.json", "--rps", "1"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch14/smoke_S.json", "trials.jsonl (cb14_descriptive)"], "next_action": "PASS: q0312; FAIL: S not testable (source), counted", "notes": "DRAFT. <= 30 requests; Factbase <= 0.5 rps."}
{"id": "q0302_cb14_exclusion_keys", "title": "CB14 exclusion keys = CB13 q0276 key file + id columns of h11_attn frame (both strata, both splits) and its entity-map canonical titles, h11_pol, h11_wprints, h12_* frames (h12_say SCREEN ids kept for S-N by declared deviation), h13_touch, CB13 T fill markets/events, seal copies; Gamma lookups for missing keys", "family": "creative_batch_14", "priority": 14, "expected_value": "disjointness of W and S", "data": ["creative_batch13/exclusion_keys.csv.gz", "history/h11_attn/{frame,entities}.csv.gz (id and canonical-title columns only)", "history/*/ (id columns only)", "docs/research_lab/seals/*", "public Gamma (ids)"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0300_cb14_smoke_W", "q0276_cb13_exclusion_keys", "q0227_cb11_attn_frame"], "argv": ["scripts/run_cb14.py", "exclusion-keys", "--rules", "../docs/research_lab/seals/cb14_rules.json", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 2400, "max_retries": 2, "outputs": ["research_lab/creative_batch14/{exclusion_keys.csv.gz,attn_entities.csv.gz,manifest.json}"], "next_action": "q0303, q0312", "notes": "DRAFT. A dependency recorded as stopped in the ledger is 'absent' (recorded). Never opens h12_say or any holdout/ path. >2% missing metadata -> unverified (family not testable, counted)."}
{"id": "q0303_cb14_w_frame", "title": "CB14-W frame: Gamma public-search, frozen 15-term query list, closed + active, paged to hasMore=false; W title regex, one-person rule, sports/coach/mention/entertainment exclusions, deaths stratum; createdAt in [2023-07-01, 2026-03-01), no status/closedTime/outcome condition; key drops (full series rule); entity rule + Wikipedia summary (standard, page id, canonical title, description); politics-tag one-day walk over 2025-03 and 2025-11 for completeness; GW0 audit file of every mapped pair; outcomes to the guarded file", "family": "creative_batch_14", "priority": 13, "expected_value": "W population and map", "data": ["public Gamma", "en.wikipedia.org REST page/summary", "creative_batch14/exclusion_keys.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api, en.wikipedia.org"}, "depends_on": ["q0302_cb14_exclusion_keys"], "argv": ["scripts/run_cb14.py", "w-frame", "--rules", "../docs/research_lab/seals/cb14_rules.json", "--rps", "2", "--wiki-rps", "1", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 3600, "max_retries": 2, "outputs": ["history/h14_wiki/{frame.csv.gz,subjects.csv.gz,completeness.json,outcomes_guarded.csv.gz,manifest.json}", "research_lab/creative_batch14/w_map_audit_sample.csv"], "next_action": "commit the GW0 audit (science-reviewer, blind); then q0305", "notes": "DRAFT. No revision or print read."}
{"id": "q0305_cb14_w_pregate", "title": "CB14-W pre-fetch gate GWC, counts only, no network: mapped markets, events, subjects after GW0 drops; frame completeness >= 95%; < 150 markets / 60 events / 40 subjects -> W1, W2 not testable (population), counted, and q0306/q0307 never committed", "family": "creative_batch_14", "priority": 14, "expected_value": "saves about 6,000 requests if W cannot be powered", "data": ["history/h14_wiki/{frame,subjects}.csv.gz", "creative_batch14/w_map_audit.json"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0303_cb14_w_frame"], "argv": ["scripts/run_cb14.py", "pregate", "--family", "W"], "timeout_s": 900, "max_retries": 1, "outputs": ["research_lab/creative_batch14/pregate_W.json", "trials.jsonl (cb14_descriptive or the counted not-testable lines)"], "next_action": "PASS: commit q0306", "notes": "DRAFT."}
{"id": "q0306_cb14_w_revisions", "title": "CB14-W: MediaWiki prop=revisions metadata (revid, parentid, timestamp, userid, size; frozen comment/tag booleans; user read in memory only for the bot flag and distinct-user index) per mapped page from max(createdAt, 2024-01-01) - 30 d to 2026-04-01; bot-group list; first-revision date per page", "family": "creative_batch_14", "priority": 12, "expected_value": "W bursts (features)", "data": ["en.wikipedia.org action API", "history/h14_wiki/subjects.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "en.wikipedia.org"}, "depends_on": ["q0305_cb14_w_pregate"], "argv": ["scripts/run_cb14.py", "w-revisions", "--rules", "../docs/research_lab/seals/cb14_rules.json", "--wiki-rps", "1", "--maxlag", "5", "--disk-cap-gb", "0.03", "--data-dumps-cap-gb", "40", "--budget-min", "100"], "timeout_s": 7200, "max_retries": 2, "outputs": ["history/h14_wiki/{revisions.csv.gz,bots.csv.gz,manifest.json}"], "next_action": "q0307", "notes": "DRAFT. mw-reverted never parsed; no user name written. Resumable; incomplete = pending.", "repeat": {"max_runs": 4, "until_log_regex": "\"status\": \"w_revisions_complete\""}}
{"id": "q0307_cb14_w_prints", "title": "CB14-W: Data API newest-first prints (<= 2 pages of 10,000) per mapped market, aggregated to transactions (time, YES-terms VWAP, min/max price, size; hash discarded); rows before 2026-04-01 kept; covered span recorded", "family": "creative_batch_14", "priority": 12, "expected_value": "W state, entry, exit, decisive moves", "data": ["public Data API", "history/h14_wiki/frame.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "data-api"}, "depends_on": ["q0306_cb14_w_revisions"], "argv": ["scripts/run_cb14.py", "w-prints", "--rules", "../docs/research_lab/seals/cb14_rules.json", "--rps", "2", "--disk-cap-gb", "0.02", "--data-dumps-cap-gb", "40"], "timeout_s": 2400, "max_retries": 2, "outputs": ["history/h14_wiki/{tx.csv.gz,reach.csv.gz,manifest.json}"], "next_action": "q0308", "notes": "DRAFT. No side, wallet or hash stored."}
{"id": "q0308_cb14_census_W", "title": "CB14-W census, counts only: frame by term/class/listing year/status; key drops and full-series counterfactual; CB11-A entity overlap; revisions and bursts by subject, state band and grid (edits only); reach; W2 units by label; decisive moves by subject and week (price-only denominator, never related to bursts); gates GW, GWP (W1 binomial worst case; W2 pre-burst round-trip proxy, SEs only); MDEs", "family": "creative_batch_14", "priority": 14, "expected_value": "W gates and MDEs before the freeze", "data": ["history/h14_wiki/ (outcomes_guarded only for the NO-resolved D audit count)"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0307_cb14_w_prints"], "argv": ["scripts/run_cb14.py", "census", "--family", "W"], "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch14/census_W.json", "trials.jsonl (cb14_descriptive)"], "next_action": "science-reviewer freeze check (W part)", "notes": "DRAFT. No L_D, placebo share, entry-exit net or lead computed. Re-reads absent exclusion frames."}
{"id": "q0309_cb14_screen_W", "title": "CB14-W: W1 (lead from the move start D0 with state <= V_D + 5c, excess over the hot-period placebo [D0-66h, D0-6h]; subject and week ways; subject time-shift calibration; lead-window, state-cap, entry-window [b+3m,b+15m], CB11-A, heads-of-government, class, half, top-5 robustness) and W2 (burst-triggered taker at recorded prints, size min(100, entry print); subject, week, story-day (country map) ways; pre-burst placebo; before-the-move check; worst-case reach at min(-9.3c, false-burst mean); cost, exit, band, stale-exit, top-5, quarter robustness); reported precision, false-burst rate, lead distribution, deaths, grid", "family": "creative_batch_14", "priority": 14, "expected_value": "W verdicts", "data": ["history/h14_wiki/"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0308_cb14_census_W"], "argv": ["scripts/run_cb14.py", "screen", "--family", "W"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch14/results_W.json", "trials.jsonl (cb14_test + creative_batch_14:W n_tests=2)"], "next_action": "advanced: q0311 after the live window", "notes": "DRAFT. Refuses before the W freeze hash and unless GW0, GWC, GW and GWP passed (else counted lines)."}
{"id": "q0310_cb14_w_live", "title": "CB14-W live collector (cron every minute, flock, outside queue lanes): list=recentchanges poll (namespace 0, rclimit 500, receipt time, rcstart overlap 120 s, rccontinue, rcid dedup, gaps logged as unavailable), live burst rule with bootstrapped baselines and the Stage-1 bot rule, CLOB /book at b+60s, 5, 15, 120 min for each mapped market of the subject; daily frozen-query refresh of active markets; weekly blind map-audit batch file", "family": "creative_batch_14", "priority": 0, "expected_value": "W Stage 2 data at recorded books", "data": ["en.wikipedia.org action API", "public CLOB /book", "public Gamma"], "resources": {"mem_mb": 150, "cpu": 1, "lane": "cron", "network": "en.wikipedia.org, clob, gamma-api"}, "depends_on": [], "argv": ["scripts/run_cb14.py", "w-live", "--rules", "../docs/research_lab/seals/cb14_rules.json", "--not-before", "2026-10-26T00:00:00Z", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "40"], "timeout_s": 55, "max_retries": 0, "outputs": ["history/h14_wiki_live/{polls,bursts,books,frame,audit_batches}/"], "next_action": "runs to T14_W2_end; then q0311 if triggered", "notes": "DRAFT. Installed by the coordinator after the W freeze (crontab.txt line, as CB12 q0257). Reads no AREPO store. Stops at T14_W2_cap."}
{"id": "q0311_cb14_rep_W", "title": "CB14-W Stage 2: W2-rep (recorded best ask at b+60s, best bid at b+120 min, fee, +1c robustness; >= 300 bursts in >= 30 subjects) and W1-rep (>= 20 decisive moves in >= 15 subjects, live burst log as the clock); poll latency and ask life reported", "family": "creative_batch_14", "priority": 14, "expected_value": "L2 verdicts", "data": ["history/h14_wiki_live/", "public Data API (post-hoc prints for W1-rep)"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0309_cb14_screen_W"], "argv": ["scripts/run_cb14.py", "rep", "--family", "W"], "timeout_s": 2400, "max_retries": 1, "outputs": ["research_lab/creative_batch14/results_W_rep.json", "trials.jsonl (cb14_replication + creative_batch_14:W:rep)"], "next_action": "pass: Stage P-W registration draft", "notes": "DRAFT. Only triggered tests; alpha/4 if early, full Stage-2 Holm once."}
{"id": "q0312_cb14_s_frame", "title": "CB14-S frame: Gamma tag 100343 one-week end-date walk over [2024-11-01, 2026-03-01); >= 8 binary members, startTime, occasion <= 36 h, CB12-M sports registry + broadcast regex, key drops (S rule; h12_say SCREEN ids kept for N), primary-speaker title map, rule booleans, term parser; Factbase record map (speaker, date +-1 d, type, keywords); subsets P and N; NO outcome stored (outcomePrices/umaResolutionStatus discarded at parse); GS0 audit sample (seed 14122)", "family": "creative_batch_14", "priority": 13, "expected_value": "S population and transcript map", "data": ["public Gamma", "rollcall.com factbase search API", "creative_batch14/exclusion_keys.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api, rollcall.com"}, "depends_on": ["q0301_cb14_smoke_S", "q0302_cb14_exclusion_keys"], "argv": ["scripts/run_cb14.py", "s-frame", "--rules", "../docs/research_lab/seals/cb14_rules.json", "--rps", "2", "--factbase-rps", "0.5", "--disk-cap-gb", "0.005", "--data-dumps-cap-gb", "40"], "timeout_s": 2400, "max_retries": 2, "outputs": ["history/h14_speech/{frame.csv.gz,members.csv.gz,map.csv.gz,manifest.json}", "research_lab/creative_batch14/s_map_audit_sample.csv"], "next_action": "q0313; GS0 audit (science-reviewer, blind)", "notes": "DRAFT. No price, print, transcript text or outcome read. Never opens h12_say."}
{"id": "q0313_cb14_s_fit_fetch", "title": "CB14-S: Factbase timestamped transcripts of primary speakers dated [2023-01-01, 2024-11-01), parsed and reduced at parse to per-term first-mention offsets and last offset (term list from frame text); no text stored", "family": "creative_batch_14", "priority": 12, "expected_value": "position-model inputs", "data": ["rollcall.com factbase", "history/h14_speech/members.csv.gz (terms only)"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "net", "network": "rollcall.com"}, "depends_on": ["q0312_cb14_s_frame"], "argv": ["scripts/run_cb14.py", "s-fit-fetch", "--rules", "../docs/research_lab/seals/cb14_rules.json", "--factbase-rps", "0.5", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "40", "--budget-min", "40"], "timeout_s": 3600, "max_retries": 2, "outputs": ["history/h14_speech/fit/{offsets.csv.gz,manifest.json}"], "next_action": "q0314", "notes": "DRAFT. One page in memory at a time (about 2 MB).", "repeat": {"max_runs": 3, "until_log_regex": "\"status\": \"s_fit_fetch_complete\""}}
{"id": "q0314_cb14_s_fit", "title": "CB14-S: frozen position model S_w(e) by speaker, type class and term from fit offsets only (shrinkage 10 to the pooled curve; 1-minute grid to 180 min); model file sha256 recorded for part S", "family": "creative_batch_14", "priority": 14, "expected_value": "the frozen anchor", "data": ["history/h14_speech/fit/"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0313_cb14_s_fit_fetch"], "argv": ["scripts/run_cb14.py", "s-fit", "--rules", "../docs/research_lab/seals/cb14_rules.json"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch14/s_model.json"], "next_action": "pin the model sha256 in part S (commit); q0316 after GS0", "notes": "DRAFT. Refuses if any h14_speech price, print, guarded or target file exists."}
{"id": "q0316_cb14_s_pregate", "title": "CB14-S pre-fetch gate GSC, counts only, no network: primary-speaker events with a mapped Factbase record across P and N (>= 100, >= 30 ISO weeks, >= 25 in P), GS0 PASS, smoke availability rule; FAIL -> S1, S2 not testable (population), counted, and q0317/q0318 never committed", "family": "creative_batch_14", "priority": 14, "expected_value": "saves about 16,000 requests if S cannot be powered", "data": ["history/h14_speech/{frame,map}.csv.gz", "creative_batch14/s_map_audit.json", "creative_batch14/smoke_S.json"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0314_cb14_s_fit"], "argv": ["scripts/run_cb14.py", "pregate", "--family", "S"], "timeout_s": 900, "max_retries": 1, "outputs": ["research_lab/creative_batch14/pregate_S.json", "trials.jsonl (cb14_descriptive or the counted not-testable lines)"], "next_action": "PASS: commit q0317 (and q0318 for T14_S_open)", "notes": "DRAFT."}
{"id": "q0317_cb14_s_data_P", "title": "CB14-S P: target transcripts (reduced to per-member first-mention offsets and last offset, guarded_p/), CLOB prices-history fidelity 1 over [startTime - 30 min, startTime + 5 h] per member, Data API prints (<= 2 pages) aggregated to transactions in that span, Gamma outcomes to guarded_p/outcomes_guarded.csv.gz", "family": "creative_batch_14", "priority": 11, "expected_value": "S P data", "data": ["rollcall.com factbase", "public CLOB prices-history", "public Data API", "public Gamma"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "net", "network": "rollcall.com, clob, data-api, gamma-api"}, "depends_on": ["q0316_cb14_s_pregate"], "argv": ["scripts/run_cb14.py", "s-data", "--subset", "P", "--rules", "../docs/research_lab/seals/cb14_rules.json", "--rps", "2", "--factbase-rps", "0.5", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "40", "--budget-min", "60"], "timeout_s": 4800, "max_retries": 2, "outputs": ["history/h14_speech/{prices_p.csv.gz,tx_p.csv.gz,guarded_p/,manifest_p.json}"], "next_action": "q0319 (with q0318)", "notes": "DRAFT. Refuses unless the model sha256 is pinned in part S. No side, wallet or hash stored.", "repeat": {"max_runs": 3, "until_log_regex": "\"status\": \"s_data_P_complete\""}}
{"id": "q0318_cb14_s_data_N", "title": "CB14-S N (CB12-M SCREEN window, nested): the same fetch as q0317 into guarded_n/; refuses before T14_S_open (CB12-M Stage-1 result commit or its ledger stop record, verified by commit hash)", "family": "creative_batch_14", "priority": 10, "expected_value": "S N data", "data": ["rollcall.com factbase", "public CLOB prices-history", "public Data API", "public Gamma"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "net", "network": "rollcall.com, clob, data-api, gamma-api"}, "depends_on": ["q0317_cb14_s_data_P"], "argv": ["scripts/run_cb14.py", "s-data", "--subset", "N", "--rules", "../docs/research_lab/seals/cb14_rules.json", "--require-open", "cb12_m_stage1", "--rps", "2", "--factbase-rps", "0.5", "--disk-cap-gb", "0.15", "--data-dumps-cap-gb", "40", "--budget-min", "110"], "timeout_s": 7200, "max_retries": 2, "outputs": ["history/h14_speech/{prices_n.csv.gz,tx_n.csv.gz,guarded_n/,manifest_n.json}"], "next_action": "q0319", "notes": "DRAFT. Exit 75 (pending) before T14_S_open. Never opens h12_say.", "repeat": {"max_runs": 6, "until_log_regex": "\"status\": \"s_data_N_complete\""}}
{"id": "q0319_cb14_census_S", "title": "CB14-S census, counts only on P and N: events by subset/speaker/type/month; parser, Q&A, map, parse failures; alignment success and anchors; units by label; q_t - p_lag distribution (prices before t, causal transcript accessor); S2-eligible units and fills; gates GS, GSP (one latent per word, GMP loadings, seed 14121), GSP2; MDEs", "family": "creative_batch_14", "priority": 14, "expected_value": "S gates and MDEs before the freeze", "data": ["history/h14_speech/ (guarded_* through the causal accessor only; no outcome file)"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0317_cb14_s_data_P", "q0318_cb14_s_data_N"], "argv": ["scripts/run_cb14.py", "census", "--family", "S"], "timeout_s": 2400, "max_retries": 1, "outputs": ["research_lab/creative_batch14/census_S.json", "trials.jsonl (cb14_descriptive)"], "next_action": "science-reviewer freeze check (S part)", "notes": "DRAFT. No Y, slope or net computed."}
{"id": "q0320_cb14_screen_S", "title": "CB14-S: S1 (word-weighted slope of Y - p_t on q_t - p_lag; unsaid iff not said by e_t, fixed-point causal alignment, rising exclusion; event, week and normalised-term ways; +-2 min clock shift binding; event sign-flip calibration; joint clock attribution with pi - p_lag and momentum; P-alone, N-alone, transcript-Y, e>=20, 10-min, shrinkage, prepared-only, late-start, unresolved, top-5, half robustness) and S2 (in-speech maker, trade-through prints, Gamma payoff; calibrated-at-fill placebo; cost, worst-case reach, P/N, top-5 robustness)", "family": "creative_batch_14", "priority": 14, "expected_value": "S verdicts", "data": ["history/h14_speech/ (guarded_p, guarded_n opened here)"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0319_cb14_census_S"], "argv": ["scripts/run_cb14.py", "screen", "--family", "S"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch14/results_S.json", "trials.jsonl (cb14_test + creative_batch_14:S n_tests=2)"], "next_action": "advanced: q0322 after the Stage-2 window", "notes": "DRAFT. Refuses before the S freeze hash and T14_S_open, and unless GS0, GSC, GS, GSP/GSP2 passed (else counted lines)."}
{"id": "q0321_cb14_s_stage2_data", "title": "CB14-S Stage 2: post-freeze mention events (startTime >= max(S freeze + 1 d, 2026-10-27)), same frame, map, model, fetch and guards into guarded_s2/; weekly; stops at T14_S2_end or the cap", "family": "creative_batch_14", "priority": 11, "expected_value": "S Stage 2 data", "data": ["public Gamma, CLOB, Data API", "rollcall.com factbase"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api, clob, data-api, rollcall.com"}, "depends_on": [], "argv": ["scripts/run_cb14.py", "s-stage2-data", "--rules", "../docs/research_lab/seals/cb14_rules.json", "--rps", "2", "--factbase-rps", "0.5", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "40"], "timeout_s": 3600, "max_retries": 2, "outputs": ["history/h14_speech/stage2/", "history/h14_speech/guarded_s2/"], "next_action": "q0322 if triggered", "notes": "DRAFT. Re-queued weekly by the coordinator until the stop rule; the stop counts events, never results.", "repeat": {"max_runs": 20, "until_log_regex": "\"status\": \"s_stage2_window_closed\""}}
{"id": "q0322_cb14_rep_S", "title": "CB14-S Stage 2: S1-rep and S2-rep on post-freeze events (>= 100 events with units by T14_S2_end; < 60 by the cap -> not run (power))", "family": "creative_batch_14", "priority": 14, "expected_value": "L2 verdicts", "data": ["history/h14_speech/{stage2,guarded_s2}/"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0320_cb14_screen_S", "q0321_cb14_s_stage2_data"], "argv": ["scripts/run_cb14.py", "rep", "--family", "S"], "timeout_s": 2400, "max_retries": 1, "outputs": ["research_lab/creative_batch14/results_S_rep.json", "trials.jsonl (cb14_replication + creative_batch_14:S:rep)"], "next_action": "pass: Stage P-S registration draft (recorded books)", "notes": "DRAFT. Only triggered tests."}
```

## 5. Code needed (not written by this document)

- `backend/astrolabe/research_lab/cb14_common.py`: reuse `cb13_common` / `cb12_common` / `cb11_common` for refused roots,
  disk and free-disk guards (cap 40, exit 75), manifests and `*_complete` status, the cluster bootstrap with the small-G
  rule and leave-one-cluster-out, strict Holm/BY helpers, per-part rules hashing, field-whitelist readers, the
  `T14_S_open` check (a committed CB12-M result or ledger stop record, by commit hash).
- `cb14_wiki.py`:
  - the `public-search` pager (to `hasMore = false`), the W regexes and exclusions, the listing-date rule, the
    politics-tag completeness walk;
  - the entity rule (CB11-A's, pinned) with the office-word stop list, the summary client, the article-age rule, the
    GW0 sampler;
  - the revisions client (`rvcontinue`, `maxlag`), the bot rule, in-memory user handling, revert-at-save flags (never
    `mw-reverted`);
  - the burst detector (10-min window, ≥ 3 edits, ≥ 2 users, Σ|Δsize|, causal 99th percentile, 6 h refractory) and grid;
  - the prints client and transaction aggregation; state, coverage, the decisive-move rule, the trade-market choice;
  - W1 (`L_D`, placebo windows, subject time-shift calibration), W2 (entry/exit prints, fees, pre-burst placebo,
    before-the-move check, worst-case reach), GWC, GW, GWP;
  - the live poller (recent-changes, live burst rule with bootstrapped baselines, scheduled `/book` reads, daily
    refresh, weekly audit batches) and W1-rep/W2-rep.
- `cb14_speech.py`:
  - the tag-100343 walker, CB12-M's sports filters (imported, hash-pinned), the occasion and speaker rules, the term
    parser and rule booleans, the Factbase search and record mapper, the GS0 sampler;
  - the Factbase transcript parser (HTML → (offset, text) segments → per-term first-mention offsets and last offset;
    no text kept), the frozen normaliser and matcher;
  - the position-model fit (`S_w(e)`, shrinkage, grid) and the anchor `q_t`;
  - the causal alignment (anchors, `δ_t`, `e_t`), the causal transcript accessor, units and labels;
  - the `prices-history` (fidelity 1, bounded) and prints clients; S1 (word-weighted OLS, sign-flip, joint
    attribution), S2 (ask, trade-through, calibrated-at-fill placebo, worst-case reach), GSC, GS, GSP, GSP2; the P/N
    subset guard; Stage 2.
- `backend/scripts/run_cb14.py` with the §4 subcommands; refuses analysis before the family's freeze hash.
- Tests (`test_cb14_wiki.py`, `test_cb14_speech.py`, `test_run_cb14.py`). They cover:
  - whitelist fixtures with every forbidden field (`side`, `proxyWallet`, `user` written, `mw-reverted`,
    `outcomePrices`, `closedTime`), refused roots (`h12_say`, `h11_attn/holdout`, live stores);
  - W: rows at `T14_W_end − 1 s` accepted and at `T14_W_end` refused; the listing-date rule ignoring status; the
    burst rule at its edges (2 edits; 3 edits by 1 user; a bot; a revert at save; 99 bytes; the percentile computed
    only from `[b − 30 d, b − 1 d]`; the refractory merge); the decisive-move rule (VWAP 0.50 accepted, 0.51 not;
    the 30-min confirmation print; the 7-day dedup); `D0` as the first print ≥ `V_D + 20c` (a 0.30 → 0.70 → 0.92 path
    puts `D0` at the 0.70 print, and a burst at state 0.70 is not a lead); the state cap `V_D + 5c` and "no print → 0";
    the hot-period anchors (11 anchors, < 3 → "no placebo"); the trade-market choice; entry max and exit min prints;
    the stale exit only after the entry print; size min(100, entry print); fees; the worst case `w*`; the story-day
    country map (unmatched description → singleton); revision-deleted user names as unknown; the live poller's
    overlap, continuation and gap rules; GWP writing no point estimate;
  - S: N paths refused before `T14_S_open` (fixture commits present and absent; stop-record branch); the HOLDOUT window
    excluded by date (an event ending 2026-03-01T00:00Z refused); q0314 refusing when price or target files exist; the
    model shrinkage and `q_t` at known values (`Ŝ = 1` → `q = π`; `Ŝ = 0` → `q = 0`); the alignment rule (1 anchor →
    unaligned; 2 anchors 6 min apart → unaligned; anchors after `t − 1 min` ignored; the fixed point dropping an
    anchor whose `o_j > e_t`; non-convergence → unaligned); the causal accessor never returning an offset after
    `e_t`; unsaid iff not said by `e_t` (a word said at `e_t + 30 s` is unsaid at `t`); the "rising" exclusion from
    prices before `t` only; the ±2 min shift; word weights summing to 1; the trade-through fill and one-fill-per-word
    rule; `p_lag` ≠ `p_t`; GSP's one latent per word with the term factor; the part-S hash and registry/regex sha256
    refusals; N reported-only when the part-S commit post-dates q0252's result;
  - `battery2` kinds and k1 = 4 fixed; the α/4 early rule in Stage 2.

## 6. Test budget and compute

| Job | Tests counted | Kind(s) | Decision |
|---|---|---|---|
| Stage 1: W1, W2, S1, S2 | **4** | `cb14_test` + count lines `:W` (2), `:S` (2) | p < 0.01, floor, binding placebos and robustness, batch Holm (one-sided α 0.05, k1 = 4 fixed); counted with p = 1 if a gate, audit or smoke fails |
| Stage 2: W1-rep, W2-rep, S1-rep, S2-rep (each only if triggered) | ≤ 4 | `cb14_replication` + `:<family>:rep` | one Holm over CB14 Stage 2, one-sided α 0.05 (early finishers at α/4) |
| Smokes, audits, pre-gates, census, gates, strata, grids, CH123 descriptives, latency | 0 | `cb14_descriptive` | - |
| **Total** | **4 fixed + ≤ 4 conditional = 4-8** | | the value at the run, recorded after the host union (1,221 on HEAD at the round-1 response; not stable) |

**Host compute.** Under 4 CPU-hours at nice 19 in total. W: burst detection streams one page's revisions at a time
(≤ about 40,000 revisions for the busiest page); the screen bootstraps on a few thousand units. S: the fit reduces about
300-500 transcripts; the screen bootstraps on about 30,000-60,000 word-checkpoint units reduced to word-level
sufficient statistics; GSP's 500 draws. Peak RAM 0.6 GB. **Network.** ≤ about 25,700 historical requests (planning
18,000-22,000; about 4-5 h of `net` lane), ≤ about 7,800 if both pre-gates fail; W live about 1,500-2,500 a day (light);
S Stage 2 ≤ 600 a week. **Disk.** ≤ 0.4 GB.

**Dates (estimates).** Code, rules parts, smokes and the GW0/GS0 audits about 2026-10-20/22. The `net` lane frees after
CB11 (about 10-15 h from 10-18 evening; CB11's smoke is parked, so later), CB12 and CB13, so W's fetches run about
10-23..26 and its screen follows the W freeze. W's live collector starts on or after 10-26 once W is frozen (it may be
frozen and collecting before its Stage-1 screen; collection is unconditional). S's P branch runs alongside; N waits for
`T14_S_open`, which follows CB12-M's freeze and q0252 (CB12-M is at verify-round NO_GO with D1-D4 open), so S's screen
is probably in November. S's Stage 2 closes no earlier than about 100 events after 10-27 (about 2-3 months).

## 7. Main scientific risks (for the challenger)

Revised after round 1; the rulings of §9 are cited.

1. **W is thin where it matters.** Decisive moves are rare (planning 40-80 in 30-55 subjects). The W1 testability
   deviation now needs ≥ 40 moves, ≥ 30 subjects and ≥ 15 ISO weeks (ruling 1), and the lead is measured from the move's
   start `D0` against a hot-period comparator, so W1 is both harder to test and harder to pass than in the draft.
   The listing-date frame is accepted (ruling 1).
2. **The market-to-article join** is audited blind (GW0). One crisis can move several subjects: the story-day way now
   uses a frozen country map from the subject's description (item 3); a subject with no mapped country is its own
   cluster, which under-clusters if many descriptions fail (the census reports the mapped share).
3. **Newest-first print reach.** Every dropped W2 unit is priced at `w* = min(−9.3c, m̄₀)` (item 2), the p90 round trip
   or the observed cost of a false burst, whichever is worse.
4. **Historical edit times versus a live reader.** W acts at `b + 60 s`, with `[b + 3 min, b + 15 min]` as a binding
   entry window (item 9); Stage 2 measures the real latency and logs poll gaps (item 12). Bot flags use the bot-group
   list as fetched (hindsight, minor); revision-deleted user names are unknown, not distinct (ruling 4).
5. **CB11-A disjointness** (calendar, keys, objects, plus the binding entity-subject drop) is sufficient (ruling 5).
6. **S nesting on CB12-M's SCREEN (N).** Waiting for CB12-M's Stage-1 result suffices only with the timing and
   no-change rule of item 6, now in §1.3. S on N is distinct from M1 but not independent evidence (ruling 6).
7. **S's clock.** Alignment is now a self-consistent fixed point inside the causal clock, "unsaid" means not said by
   `e_t`, a price-only "rising" exclusion removes words just heard, and ±2 min shifts are binding (item 4). The
   reaction lag in `δ` still makes `e_t` run early by a variable amount (disclosed; conservative for S1, adverse for S2).
8. **S is effectively a single-speaker test** (accepted as disclosed, ruling 8). Recurring terms share the model's
   error across events, so a normalised-term way and a term factor in GSP/GSP2 are added (item 5).
9. **The position model** (fit on 2023-2024 speeches; shrinkage 10) is accepted as disclosed (ruling 9), with the
   pre-roll re-basing as robustness (item 13).
10. **1-minute history before 2025** is unverified; the smoke's availability rule is accepted (ruling 10).
11. **Fees** are the current `feeSchedule` with a 0.04 floor (accepted, ruling 11).
12. **Transcript versus venue resolution** (accepted, ruling 12).
13. **CH127 is not tested** (§0.4; deferral accepted).

## 8. Next actions

1. Round 1 is answered (§9-§10). Next review: the code-against-design freeze check (`science-reviewer`) once code
   exists. It may reopen any round-1 item. The modifications stay open to it: the hot-period placebo as the W1
   comparator (item 1), the anchor schedule `τ_k` (item 1) and the loading split of the term factor (item 5).
2. Write `seals/cb14_rules.json` (parts `common`, `W`, `S`), the modules and tests of §5 and `run_cb14.py`
   (implementer); then the code-against-design freeze check.
3. W order: q0300 → q0302 (behind CB13 q0276 and CB11 q0227) → q0303 → GW0 audit → q0305 (GWC) → q0306 → q0307 →
   q0308 → W freeze → q0309; q0310 installed after the W freeze, not before 2026-10-26; q0311 if triggered.
4. S order: q0301 → q0312 → GS0 audit → q0313 → q0314 (model hash pinned) → q0316 (GSC) → q0317 (P) → `T14_S_open` →
   q0318 (N) → q0319 → S freeze → q0320; q0321 weekly after the S freeze; q0322 if triggered.
5. The S rules part is committed before CB12-M's q0252 result; if it is not, N is reported-only (§1.3, item 6).
6. CB15 adds CB14's frame ids (W markets and subjects, S events) to its keys. CH127 re-enters with the census of §0.4.
7. Ledger lines for every counted result; checkpoint and plain-English dashboard updated by the orchestrator.

## 9. Challenger review, round 1 (science-reviewer, 2026-10-18)

**Verdicts: CB14-W REVISE, CB14-S REVISE; the CH127 deferral is accepted.** 6 blocking and 8 non-blocking items, plus
rulings on the §7 risks.

**Count.** `cumulative_count()` = 1,221 on HEAD (1,181 at `647549c~1`; +40 `flow_screen` lines from the host union).
The draft's claim that the working copy was identical is false (2 extra uncommitted `cb12_descriptive` lines, which
count 0). The count is not stable (the host writes about 55-60 counted `flow_screen` lines a day), so the projected
1,228-1,237 must go; state the count as "value at run, recorded after the union".

**Main challenge (W).** W1 can pass when the market moved first. `D` was the first print ≥ 0.90 and `L_D` only needed
the entry print ≤ 0.75, so on a 0.30 → 0.70 → 0.92 path a burst after the first repricing counted as a lead. Bursts
cluster around `D` because a story is unfolding, and the fixed −7 … −28 d placebos lie outside that hot period. The
"before the move" guard existed only for W2.

**Main challenge (S).** The unit set used the transcript beyond the causal clock. The accessor revealed only offsets
before `e_t`, yet "unsaid iff first mention > `e_t + 60 s`" needs offsets in `(e_t, e_t + 60 s]`, where `Y = 1` by
definition; it drops words about to be said, which are S2's adverse fills. Anchors could need `o_j` after `e_t`. `δ_j`
includes the market's reaction lag, so `e_t` is biased early by a variable amount.

**Blocking.**
1. **W1 from the move's start.** `D0` = the first transaction ≥ 20c above the VWAP of `[D − 24 h, D − 2 h]`; require
   `state(b) ≤` that VWAP + 5c; the 0.90 crossing is reported only; a binding hot-period placebo on same-subject
   windows in `[D − 72 h, D − 6 h]`.
2. **W2 worst case.** −4.5c is the median round trip; use `min(−9.3c` (the p90, `EXECUTION_COSTS.md` line 39)`, the mean
   net of covered bursts without a ≥ 20c rise)`.
3. **W story-day way.** There is no Gamma country field in the whitelist: define country from a frozen tag-id map or
   the subject's description, or drop the way.
4. **S causal clock.** Unsaid iff not said by `e_t`; only anchors with `o_j ≤ e_t` (self-consistent), unit-tested; a
   causal price-only exclusion when the word's 1-minute price rose ≥ 15c in the last 5 min; binding robustness with
   `e_t` shifted ±2 min (sign kept and p < 0.05) for S1 and S2.
5. **S dependence.** A term recurs across many single-speaker events with a shared `Ŝ_w` error: add a normalised-term
   way to the max and a term factor to GSP/GSP2.
6. **N loophole.** Decide now: if the S rules part is hashed after q0252's result, N becomes reported-only; after
   `T14_S_open` no element of part S may change except mechanical code fixes; pin CB12-M's sports registry and
   broadcast regex by sha256.

**Non-blocking.**
7. W2's stale exit must come after the entry print.
8. Paper size min(100, the entry print's size).
9. A binding entry window `[b + 3 min, b + 15 min]` (poll latency may exceed 60 s).
10. `D` needs confirmation (two prints ≥ 0.90 within 30 min).
11. W1 placebos require prior listing: count the dropped fast-resolving events; report a burst-only placebo that does
    not depend on prints.
12. Live poller: `rccontinue` / `rcstart` gap detection, gaps "unavailable"; Stage 2 uses the same bot rule as Stage 1.
13. S: report the first-segment offset (video pre-roll); robustness with `e` from the first speaker segment.
14. Fix the line-93 claim (the working copy is not identical).

**Rulings on §7 risks.**
- (1) The W1 deviation is allowed with ≥ 30 subjects **and** ≥ 15 ISO weeks, only after item 1; W1 is counted with
  p = 1 if not testable. The listing-date frame is accepted. The early-closure aggregate is disclosed and acceptable.
- (2) See item 3. (3) See item 2.
- (4) Accepted with item 9; revision-deleted user names count as unknown, not distinct.
- (5) The separation from CB11-A is sufficient; no further holdout-entity drop.
- (6) Waiting for Stage 1 is enough only with item 6; S on N is distinct but not independent evidence.
- (7) Not selection on outcome; item 4 is the real problem.
- (8), (9) Accepted as disclosed; add item 5.
- (10) The smoke availability rule is accepted.
- (11), (12) Accepted.

## 10. Response to challenger round 1 (2026-10-18T21:36Z)

No CB14 quantity has been computed, so every change below was made blind. None relaxes a floor, threshold, gate,
alpha or cap; several make tests harder to pass or to run. k stays **4 fixed + ≤ 4 conditional = 4-8**. The cumulative
count is stated as the value at each run, after the host union (1,221 on HEAD now; not stable).

| Item | Decision | Where | What changed |
|---|---|---|---|
| Count | **Adopted** | §0.2, §2.5, §6 | The working-copy claim is corrected (2 extra `cb12_descriptive` lines, count 0); the projected 1,228-1,237 is removed; every counting job records the value at its run, after the union |
| 1 W1 from the move start | **Adopted, with one stated modification** | §0, §2.4, §CB14-W, §4, §5 | `D0` = the first transaction in `[D − 2 h, D]` ≥ `V_D + 20c`; a lead needs a burst in `[D0 − 120 min, D0 − 5 min]` with state ≤ `V_D + 5c` and an entry print; the 0.90 crossing is reported only. **Modification:** the hot-period placebo is not a separate pass/fail check but **the comparator inside `Δ_W1`**: `π̂_D` is the same indicator at 11 anchors `τ_k = D0 − 6 h·k` (`τ` in `[D0 − 66 h, D0 − 6 h]`, inside the requested `[D − 72 h, D − 6 h]`), and the 0.25 floor applies to the excess over that hot rate. Justification: a separate check ("the hot-period statistic must not pass") would still let W1 pass on an excess over the quiet fixed-lag rate whenever the hot-period excess is just below p < 0.01; making the hot rate the baseline answers the main challenge directly (what bursts add beyond an unfolding story) and is stricter. The fixed-lag comparator is reported. The freeze check may revert to the requested form |
| 2 W2 worst case | **Adopted** | §2.1, §CB14-W W2 | Every dropped unit ("uncovered", "no entry print", "no exit") is priced at `w* = min(−9.3c, m̄₀)`, `m̄₀` the mean net of covered units without a ≥ 20c rise within 2 h |
| 3 story-day way | **Adopted (country from the description)** | §2.3, §CB14-W, census, §5 | Country = a frozen demonym / country-name map on the subject's stored Wikipedia short description, written in part W before any read; no match → the subject is its own country (singleton); cluster = UTC day × country. The census reports the mapped share |
| 4 S causal clock | **Adopted** | §CB14-S alignment and units, S1, S2, §5 | Unsaid iff not said by `e_t` (the 60 s margin removed); anchors are the self-consistent fixed point with `o_j ≤ e_t` (≤ 10 iterations, non-convergence → unaligned), unit-tested; the causal "rising" exclusion (≥ 15c over `[t − 5 min, t]`); `e_t` shifted ±2 min is binding for S1 and S2 (sign and p < 0.05). The reaction-lag bias is disclosed (conservative for S1, a real adverse fill for S2) |
| 5 S dependence | **Adopted, with one stated modification** | §2.3, §2.7, S1, S2 | A normalised-term way joins the event and week ways in the max for S1 and S2; GSP and GSP2 carry a term factor `T_term`. **Modification:** the loadings are declared as `√0.15·V_week + √0.25·U_event + √0.15·T_term + √0.45·ε` (the event loading moves 0.30 → 0.25 and the idiosyncratic 0.55 → 0.45, so the total stays 1). Justification: the reviewer asked for a term factor but set no loading; carving it from the idiosyncratic share alone would leave the event share unchanged and the total variance fixed, but a term shared across events is part of what CB12's event loading absorbed for a multi-speaker population, so 0.05 moves from it; the week loading stays CB12's. The freeze check may reset the split. The top-5 drops gain a term way |
| 6 N loophole | **Adopted** | §1.3, §0.4, §1.4, §8 | Decided now: if the S rules part's commit post-dates q0252's result commit, N becomes reported-only and S1/S2 run on P alone. After `T14_S_open` no element of part S may change except mechanical code fixes with a reviewer sign-off; any other change voids N from the primary. CB12-M's sports registry (sha256 `b47b3d20…57bce6`, at `c0cb6ba`) and broadcast regex (sha256 of its UTF-8 string `61b45196…d6b8c0`) are pinned in part S; a mismatch is a refusal |
| 7 stale exit | **Adopted** | §2.1 | The stale exit is the last transaction after the entry print; none → "no exit", excluded, counted and priced at `w*` |
| 8 paper size | **Adopted** | §2.1 | Size = min(100, the entry print's size); size-weighted results reported |
| 9 entry window | **Adopted** | §CB14-W W1, W2, §7 | `[b + 3 min, b + 15 min]` is a binding robustness entry window for W1 (with p < 0.05) and W2 |
| 10 confirmation | **Adopted** | §CB14-W decisive move | `D` needs a second transaction ≥ 0.90 within 30 min |
| 11 placebo and listing | **Adopted** | §CB14-W W1, census | Moves dropped as "no placebo" because the market was listed < 18 h before `D0` are counted; a burst-only placebo (no prints) is reported. The hot-period anchors need ≥ 3 covered, post-listing anchors |
| 12 live poller | **Adopted** | §CB14-W Stage 2, §2.8, q0310 | `rcstart` overlap 120 s, `rccontinue` to exhaustion, `rcid` de-duplication; failed polls, start gaps or > 5 min without a successful poll mark the interval, and bursts touching it are "unavailable (gap)"; Stage 2 uses the frozen Stage-1 bot list plus the name regex |
| 13 pre-roll | **Adopted** | §CB14-S alignment | The census reports first-segment and first primary-speaker-segment offsets; a robustness check re-bases fit and target offsets to the first primary-speaker segment (a second model file, hashed with the first before any S read) |
| 14 line 93 | **Adopted** | §0.2 | Corrected (see Count) |
| Ruling (1) | **Adopted** | §2.3, §2.7 GW | W1 needs ≥ 40 moves, ≥ 30 subjects and ≥ 15 ISO weeks; not testable → p = 1, counted |
| Ruling (4) | **Adopted** | census, §5 | Revision-deleted user names count as unknown, never as a distinct user |
| Ruling (5) | **Adopted** | §7 | No further CB11-A holdout-entity drop; the existing binding entity-subject robustness check stays |
| Ruling (6) | **Adopted** | §1.3, §7 | Stated: S on N is distinct but not independent evidence of M1 |

**Rejected:** none.

## 11. Code-against-design freeze-check fixes (2026-10-19)

The `science-reviewer` code-against-design freeze check of the CB14 code (commit `d50a2ed`, 2026-10-19) found 18 defects. The fixes below
were made blind (no CB14 job has run; no CB14 quantity exists). Every change tightens, clarifies or makes the code match the text above; **no
floor, threshold, gate, alpha, population or cap was relaxed**. Where a fix needed a design choice, the stricter or outcome-blind option was
taken and is declared here ("amends" names the section the row amends). Rules resealed afterwards (`seals/cb14_rules.json`); the new part
shas are in the queue drafts.

| Item | Change | Where |
|---|---|---|
| F1 small-G rule | `cluster_p` now applies §2.3 per way as CB10 `cluster_p_d` / CB13 `cluster_p_block`: G ≥ 30 CR1; 15 ≤ G < 30 CR2 + t(G − 1) + Webb wild; **G < 15 the way leaves the max and its leave-one-cluster-out sign rule binds** (every leave-one-out estimate re-estimated and > 0; `small_g_rules_hold`). The code had made the whole test untestable. Every advance and every binding p-check (W1 class / half / top-5 / variants, W2 sub-checks, S1 / S2 robustness, the S week and term ways, reps) needs the sign rules; calibration placebos are judged on p alone (§2.6). A sub-check with no way of G ≥ 15 has no p and is "not met" | `cb14_common.cluster_p`, `p_pass`; `cb14_w`, `cb14_s` |
| F2 W live baseline | The live baseline bootstrap reads revisions of the live window without the Stage-1 clamp to `T14_W_end` (`fetch_page_revisions(historical=False)`); the clamp stays for q0306 | `cb14_w.fetch_page_revisions`, `bootstrap_baseline` |
| F3 W Stage 2 selection | Each live burst record snapshots its subject's mapped markets, entity and country at the burst; W2-rep uses only that snapshot. Daily frames are kept (`frames/<day>.json`), never overwritten, and every market ever mapped enters a write-only registry (`markets_seen.json`); the post-hoc prints of **every market seen** (closed and resolved ones included) are refreshed daily until the window end + 3 d, and W1-rep's decisive moves come from that registry. Re-check of 515d68d: each refresh merges `oldest_ts` / `truncated` with the earlier fetches (`merge_print_coverage`) instead of overwriting them (power only). No statistic reads the rolling `frame_live.json`. Amends §CB14-W Stage 2 (mechanics only) | `cb14_w.w_live`, `record_markets_seen`, `refresh_live_prints`, `post_close_refresh`, `w2rep_units`, `live_w1_units` |
| F4 N exemption | The S exemption is the market ids of CB12-M's SCREEN frame (`h12_say` root files; its `holdout/` is never opened) that come from **no other direct source** (another id-readable frame or a seal copy), regardless of the CB13 base key file (which already holds them); exempt ids are re-looked-up so the exemption file carries their keys, and an exempt market never lifts an event / neg-risk / series key that a non-exempt row also carries (stricter) | `cb14_common.split_key_sets`, `exempt_rows`, `exclusion_keys` |
| F5 stalls counted | A recorded stall (keys `disjointness_unverified`, a W frame source / budget stall, an S frame disjointness stall, an incomplete Factbase walk, F17) writes **once** a terminal record `terminal_<family>.json` and the family's counted "not testable" lines at that moment (p = 1; §2.5). Every downstream job of that family (fetches, pregate, census, screen, the Stage-2 collectors `w-live` / `s-stage2-data`, `stage2-final`) then ends with exit 0 and counts nothing again (re-check of 515d68d: the smoke too, so a smoke run after q0302 found disjointness unverified never counts S twice); a failed smoke or pre-gate (counted where it fails) is terminal in the same way. No job waits on exit 75 behind a stall | `cb14_common.record_terminal`; `run_cb14._terminal` |
| F6 Stage-2 Holm | Every test result carries `checks_ok` (every binding condition except the primary p gate) and `p_ok`; a rep sets `stage2_early_alpha_ok` (p < α/4, strict) and passes early iff `checks_ok` and that. A new `stage2-final` command (draft **q0323**, from the reserved q0323-q0339 range; after q0309 / q0320, verifies the rules file of every part first; waits with exit 75 while a triggered rep is missing, with an idle heartbeat exit 0 at least every 10 h as q0311 / q0322 do, all three with a `repeat` until their completion status) runs, once every triggered family's rep is final, ONE strict Holm at one-sided α = 0.05 over every triggered Stage-2 test (a triggered test that could not run enters with p = 1); it can only add passes (`checks_ok` still required). The Stage-2 S checks (top-5 drops, worst-case reach) use p < 0.01, as CB13 Stage 2 (stricter than the α/4 the code had) | `cb14_common.stage2_final`, `stage2_k_min`; `run_cb14.cmd_stage2_final`; `cb14_w.finish`, `rep_w`; `cb14_s.s1_screen`, `s2_screen`, `rep_s` |
| F7 W rep window | q0311 refuses to analyse a partial window: it needs the closure record `closed.json` (written by q0310 when the stop rule or the cap closes the window), now ≥ window end + 3 d, and the final post-close print refresh (`prints_final.json`); else exit 75 (pending). Drafts q0311 / q0322 carry `not_before`, `--rules`, `--results-sha256 TODO-COORDINATOR` and `--stage2-k TODO-COORDINATOR` (the runner refuses the token; k2 must lie in [k_min, 4], k_min = this family's triggered tests plus every possibly triggered test of the other family, so α/k2 is never looser than the final step) | `cb14_w.live_window_end`, `rep_w`; `run_cb14._stage2_k`; drafts q0311, q0322 |
| F8 shared helpers | The sha256 of the source of every cross-module helper the CB14 rules call (`small_g_pvalue`, `holm`, `cluster_se_mean`, `top_k_drop_mask`, `placebo_advance_rate`, `leave_one_out_sign`, `aggregate_transactions`, `fetch_prints_paged`, `reach_ok`, the key / id readers and lookups, the manifest and stall helpers, `seal_copy_ids_audited`, ...) is part of **every** part's rules doc (`SHARED_HELPERS`). **Re-check of 515d68d:** the helpers' own helpers are hashed too: `external_closure` follows, transitively, every non-CB14 `astrolabe.*` function or class reachable from the declared roots and from the part's own functions (e.g. `cb2_weather._cluster_sums`, `battery._cr_var_of_sum` under `small_g_pvalue`); per part, so a W change never moves the S hash | `cb14_common.shared_helper_sources`, `external_closure` |
| F9 freeze vs rules | `require_freeze` refuses unless the family's freeze entry pins `rules_sha256` equal to the part sha the job has just verified (part S: also `s_model_sha256` and `s_model_rebased_sha256` equal to the committed model pins, F10). `freeze-part` prints exactly that entry. Applied by `screen`, `rep`, `w-live` and `s-stage2-data` | `cb14_common.require_freeze`; `run_cb14._freeze` |
| F10 model pin | **Amends §1.4 / §CB14-S position model.** The fitted-model sha256 pins are no longer constants of part S (pinning them after q0314 changed the part-S hash and could void N under the §1.3 timing rule). They live in a committed, write-once pin file `seals/cb14_s_model_pin.json` (`s_model_sha256`, `s_model_rebased_sha256`), written by the coordinator after q0314 and before any S price, print or target transcript is read; q0317 / q0318 / q0321 / census / screen / rep refuse while it is missing, uncommitted, unset or differs from the model files; the S freeze entry carries the same two sha256 (§1.4: "Part S [of the freeze] also pins the sha256 of the fitted position model") | `cb14_s.model_pins`, `check_model_pin`; `run_cb14._model_pins` |
| F11 P-only gates | When N is reported-only (§1.3 timing rule), the screen recomputes GS, GSP and GSP2 on P alone (feature-only, no outcome) and a test fails its gate if either the census reading (P ∪ N) or the P-only reading fails it | `cb14_s.gates_s`, `screen_s` |
| F12 S smoke availability | **Amends §CB14-S "1-minute availability".** The declared rule (3 out-of-frame events × 2 members per month over 7 months: 7 lookups + 42 price reads) cannot fit the smoke's 30-request cap. Engineering gate, outcome-blind: **one** out-of-frame event (no speaker keyword, or sports) × 2 members per month (7 + 14 = 21 requests); a month is usable iff **both** members return rows (an **outcome-blind amendment**, not a stricter rule: with per-member availability p, P(2 of 2) = p² can exceed the design's P(≥ 4 of 6), e.g. p = 0.3: 0.09 vs 0.07); a month with no out-of-frame event found is not usable; P keeps usable months only; the smoke criterion passes with ≥ 1 usable month (GSC still needs ≥ 25 P events) | `cb14_s.AVAIL_*`, `smoke_online` |
| F13 S Stage 2 | **Stop rule as §1.2:** q0321 closes the window at the cap or once **≥ 100 Stage-2 events with a mapped transcript and ≥ 1 aligned unit have resolved** (every member resolved on Gamma; counted from resolution flags, never from outcome values); the code's "150 transcripts" is removed. **Outcomes are re-fetched** every pass for every market whose last lookup was unresolved (an unresolved word is never frozen at 0.5); outcome rows are stored only inside the guarded directory (`guarded_*/outcomes_partial.jsonl`), the clean store keeps a resolution flag. **Weekly:** a pass starts at most once per 7 days after the last completed pass (between passes an idle exit 75, with an idle heartbeat exit 0 at least every 10 h, as CB8 q0162); q0321's `repeat` is `max_runs` 600 and ends on `s_stage2_window_closed`. q0322 waits until the window is closed; < 60 resolved events with a unit at the cap → "not run (power)", counted. **Re-check of 515d68d (post-close outcome wait):** because the window closes on a count of resolutions, the latest events are unresolved by construction and resolution timing may depend on the outcome; so after the closing pass (status `s_stage2_window_closed`, the event set is fixed, no event is added) q0321 keeps re-fetching every unresolved member **at most daily for a fixed, pre-declared 14 days** (`S2_OUTCOME_WAIT_D`; mention markets normally resolve within 1-2 days, a UMA dispute round adds about 2-4 days, so 14 days cover two rounds), and the first pass at or after `closed_at + 14 d` writes `s_stage2_outcomes_final`. q0322 analyses **only** after that status (outcomes are never frozen at the closing pass); a word still unresolved at the final lookup follows the design rule (§CB14-S: 0.5 with the binding worst case at 1), and the rep reports how many. q0321's repeat ends on `s_stage2_outcomes_final` or `terminal_not_testable`. Amends §1.2 mechanics only (no threshold changed) | `cb14_s.stage2_post_close`, `S2_OUTCOME_WAIT_D`, `rep_s`; draft q0321 | `cb14_s.s_stage2_data`, `stage2_weekly_gate`, `stage2_progress`, `_fetch_targets`, `rep_s`; draft q0321 |
| F14 W smoke and frame fields | The revisions-paging smoke reads a 30-day out-of-window range at `rvlimit=1`, so any second revision forces a continuation (a full first batch must continue and the continued batch be non-empty). A new smoke criterion `w_search_fields` reports whether `public-search` events carry `tags`, `series`, market `createdAt` and `negRiskMarketID` and checks that the `/events` lookup returns them. q0303 looks up every search event with a W-candidate market that lacks one of those fields (batches of ≤ 50 ids, closed first; **≤ 600 requests**, the §2.8 budget; over budget → a declared source stall, F5) and parses the full event | `cb14_w.event_needs_lookup`, `lookup_events`, `w_frame`, `smoke_online` |
| F15 period checks | S2 gains the §2.6 (iii) binding checks (sign in each calendar half of fill time; leave-one-quarter-out sign); W1 gains the leave-one-quarter-out sign. W2's entry-window `[b + 3 min, b + 15 min]` check is **sign only** as §CB14-W W2 (the code's extra p < 0.05 is removed; p < 0.05 stays W1's rule) | `cb14_s.s2_screen`, `s2_sign`; `cb14_w.w1_test`, `w2_test` |
| F16 exclusion sources | **Amends §1.1 / §1.3 (declared id-only reads).** q0302's id-only readers (id columns only; outcome, pageview and guarded files always refused; a holdout file only when named explicitly) now also read CB11-A's HOLDOUT frame `h11_attn/holdout/frame_hold.csv.gz` (§1.3 (2): both splits), CB13-R's HOLDOUT barrier events `h13_touch/holdout/{events,members}.csv.gz`, and CB13-T's fill markets `creative_batch13/t_screen/fills.csv.gz` and `t_holdout/fills.csv.gz` (§1.3: "CB13 T fill markets and events"). §1.1's "`h12_say` never opened" is corrected: q0302 reads the **id columns** of `h12_say`'s SCREEN `events.csv.gz` / `members.csv.gz` (the N exemption needs them); no other `h12_say` file. Frames absent at q0302 are re-read (ids only) by the S census, screen and rep as by the W census (events hit by them are dropped and counted; `h12_say` never drops an N event) | `cb14_common.ID_READABLE`, `guard_id_file`, `id_source_path`, `frame_ids`; `cb14_s.late_overlap_s` |
| F17 drafts and Factbase walk | q0302 carries `--base-sha256 TODO-COORDINATOR` (the base is CB13 q0276's `creative_batch13/exclusion_keys.csv.gz`, as §1.3, not CB11's file; filled by the coordinator from `sha256sum` on the host once CB13 q0276 has completed; q0276 itself pins CB11 q0221b's final key file, sha256 `c8a1d64b…6d304`) and depends on `q0221b_cb11_exclusion_keys` explicitly (q0221 is superseded) and on `q0227b_cb11_attn_frame` (q0227 failed and is replaced) and a `repeat` ending on `exclusion_keys_complete` or `disjointness_unverified`; its note no longer says it never opens `h12_say` (F16). q0303, q0307 and q0312 get `repeat` blocks ending on completion or a stall status. A Factbase search walk that stops at its 300-page cap before reaching 2023-01-01 is a **declared source stall** ("not testable (source)", counted, F5), never a silently partial record list | drafts; `cb14_s.s_frame` |
| F18 W1-rep minimum | W1-rep's extra "≥ 15 ISO weeks" minimum is dropped: the design's only minimum is ≥ 20 moves in ≥ 15 subjects (the small-G rule of F1 governs the week way) | `cb14_w.w1_rep` |
| `TIMESTAMPED_MIN_STAMPS` | **Declared (implementer's rule):** a parsed Factbase transcript is "timestamped" (status `ok`, usable as a fit or target transcript) iff it has ≥ **20** distinct segment stamps; fewer → `not_timestamped`, counted, never used. Fixed before any transcript read; outcome-blind (stamp counts only) | `cb14_s.TIMESTAMPED_MIN_STAMPS` |

**Open v2 item (re-check of 515d68d).** The smokes do not make the 30-request limit a required criterion (`_requests` is reported, not in `SMOKE_NEEDS`). q0300 / q0301 were already promoted, so making it required, which changes how the smoke decides pass or fail, is left to a smoke v2; the observed request count is in each smoke file.

**Scheduling (declared).** q0311 `not_before` = 2027-01-27T00:00Z (the earliest window end, `T14_W2_start` floor + 90 d, plus 3 d);
q0322 `not_before` = 2026-12-01T00:00Z (a scheduling hint only). Both are gated in code by the closure records (F7, F13), which bind.

## 12. CB14-W pre-fetch gate GWC result (q0305, done 2026-10-21 18:04Z; counts only, no network)

Source: `creative_batch14/pregate_W.json` on the host (rules sha256 W `011abaf5…`, as pinned). **GWC: FAIL (`pass` false).**
Counts against the pre-declared minimums (150 markets, 60 events, 40 subjects):

| Check | Needed | Observed | Result |
|---|---|---|---|
| mapped markets | >= 150 | 58 | fail |
| events | >= 60 | 46 | fail |
| subjects | >= 40 | 38 | fail |
| frame completeness | >= 95% | 1.0 (12 of 12 walk markets found) | pass |
| GW0 audit | complete and passing | complete (56 of 56 labelled, 0 missing); precision 0.6786 (38 of 56 match, rule revision 1); `audit_pass` false | fail |

**Consequence (design §GWC).** W1 and W2 are "not testable (population)", p = 1, **counted 2** (`creative_batch_14:W` count
line, n_tests 2, written 2026-10-21T18:04:03Z, results sha256 `9577d5b7…`). q0306 and q0307 are never committed; q0308 and q0309
have no data to read. No edit-burst, print or outcome data was fetched. CB14-S was already terminal (q0301); CB14 now has no
testable family.
