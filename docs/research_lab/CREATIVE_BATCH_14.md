# Creative batch 14 (CB14): Wikipedia edit-burst lead, intra-speech hazard decay

`evidence_role: exploratory_historical` (CB14-W Stage 1; CB14-S Stage 1) / `prospective` (CB14-W Stage 2, a live
collector from a date after the W freeze; CB14-S Stage 2, mention events that start after the S freeze) | status:
**DRAFT (pre-challenger). Nothing frozen, nothing queued, no code.** Drafted 2026-10-18 22:15 UTC+1
(2026-10-18T21:15Z) on parent `2e24605`. Nothing was fetched or written for CB14 beyond the read-only host listings and
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
| 1 | **CB14-W** Wikipedia edit-burst lead (CH123) | in markets on whether a named person will resign, be out, be fired, be removed or be indicted, a burst of edits on the person's English Wikipedia article precedes the market's decisive move by ≥ 5 min while the price is still ≤ 0.75, more often than in placebo windows of the same subject (W1, excess ≥ 0.25); a taker who buys YES at recorded prints after each burst and exits at the 2 h recorded prints earns after fees (W2, ≥ +1.0c per share) | W1 (lead excess), W2 (burst-triggered taker economic) | fresh `h14_wiki`: frozen-query Gamma frame by **listing date**, MediaWiki revision metadata, Data API prints; units in `[2024-01-01, 2026-04-01)`; no historical holdout | prospective: the live collector (recent-changes poll + CLOB `/book` reads at burst + 1, 5, 15, 120 min) from `max(W freeze + 1 d, 2026-10-26T00:00Z)`; W1-rep, W2-rep at recorded asks | q0300, q0302-q0311 |
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
| q0323-q0339 | reserved | - | - |

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
- `battery2.cumulative_count()` (`battery2-count-v1`) = **1,221** on the committed `trials.jsonl` (last changed at
  `647549c`, "trials.jsonl union from host"; the working copy is identical). **The brief's 1,181 is stale:** the host
  union at `647549c` added 40 `flow_screen` lines. The uncommitted `battery2.py` edit in the working tree only adds
  CB13 kinds with rule `EXCLUDE`, so the total is the same with or without it. CB13 reserves 3-8 more. The host union
  step runs before every counting CB14 job and records the post-union value.

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
492 ids) and a frozen coach/athlete title regex, so "head coach fired" markets are excluded and counted. S reuses
CB12-M's sports tag registry and broadcast regex unchanged. Category stays a parameter.

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
    and no CB12-M line may cite S.** S's rules part is hashed before q0252 runs. If q0252's result is committed before
    the S rules part, every S line carries "S rules hashed after CB12-M Stage 1", and the challenger decides whether N
    stays in the primary.
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
  - **`S`**: tag id 100343, CB12-M's sports registry sha256 and broadcast regex, the occasion and member rules, the
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
| W2 | **taker entry at a recorded print**: `e` = the **maximum** YES-terms transaction price in `[b + 60 s, b + 15 min]` (the taker-adverse print after the burst `b`; none → "no entry print", counted); **exit at a recorded print**: `x` = the **minimum** YES-terms transaction price in `[b + 2 h, b + 2 h 30 min]` (none → the last transaction before `b + 2 h 30 min`, labelled "stale exit", counted); taker fee `r·e(1 − e) + r·x(1 − x)`, `r = max(feeSchedule.rate, 0.04)` (politics convention; `feeSchedule` is the current, not the point-in-time, schedule, so the floor 0.04 is a declared conservative rule); size ≤ 100 shares |
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
- **Cluster ways.** **W1:** subject (Wikipedia page id) and ISO week of `D` (one political crisis can move several
  subjects in one week). **W2:** subject; ISO week of `b`; **story day** (UTC day × the set of subjects with a burst
  that day, joined into one cluster when ≥ 2 subjects of one country burst on the same day, by the frame's country
  field). **S1, S2:** event; ISO week of the event. Words of one speech share the speech, and the event way is the unit
  of independence; every S unit of one word shares `Y`, so the **word is weighted 1, split over its units**. p = the max
  over the listed ways.
- **Testability minimums.** ≥ 100 units and ≥ 30 clusters in the first way, except **W1 (declared deviation): ≥ 40
  decisive moves in ≥ 30 subjects** (CH123's own kill; a decisive move is a rare event, and 100 would make W1
  untestable by construction). The challenger may strike the deviation, in which case W1 is "not testable (population)".
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
| W1 | lead (mechanism) | `Δ_W1 = mean_D (L_D − π̂_D) ≥ +0.25`: the share of decisive moves with a tradable burst lead ≥ 5 min exceeds its same-subject placebo share by ≥ 25 pp (CH123's "share with lead > 5 min ≥ 25%", taken as an excess over chance) |
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
- **Cumulative count: 1,221** (committed `trials.jsonl` at `647549c`, `battery2-count-v1`; §0.2). CB13 adds 3-8.
  **CB14 adds 4 fixed tests and up to 4 conditional ones. Budget: 4-8**, so the cumulative count becomes 1,228-1,237
  after CB13 and CB14, plus whatever CB6-CB13 add first.
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
  W2 units by label ("no state", "state outside [0.05, 0.60]", "uncovered", "no entry print"); decisive moves by
  subject and ISO week (a price-only denominator, never related to bursts here). **Gate GW:** W1 needs ≥ 40 decisive
  moves in ≥ 30 subjects; W2 needs ≥ 500 units in ≥ 40 subjects and ≥ 30 ISO weeks; reach coverage of W2-eligible
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
  per word, `Z_w = √0.15·V_week + √0.30·U_event + √0.55·ε_w` (CB12 GMP loadings), `Y*_w = 1{Φ(Z_w) > 1 − π_w}` with
  `π_w` the word's start price (one value per word, as CB13 GRP); 500 draws (seed 14121); `MDE_S1 = 3.16 × 1.2 ×
  max(SD(β̂*), mean SE per way)`; S1 "not run (power)" if `MDE_S1 > 0.60`. GSP2 (S2): the same latents calibrated to the
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
  | q0310 | W live: recent-changes poll every 60 s (`list=recentchanges`, namespace 0, `rclimit=500`), `/book` reads (≤ 4 per mapped market per burst), daily Gamma refresh (≤ 60) | about 1,500-2,500 a day | ≤ 0.05 GB total |

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

**Decisive move (frozen; price only, no outcome).** For a market, `D` = the time of the first transaction with
YES-terms price ≥ 0.90 such that the YES-terms VWAP of its transactions in `[D − 24 h, D − 2 h]` is ≤ 0.50 (≥ 1
transaction there; covered). One `D` per subject per 7 days (the earliest over the subject's markets). Gamma outcomes
are not used to define `D` (the census counts, for audit only, how many `D` lie in markets that resolved NO).

**W1 (lead).** For each decisive move `D` (SCREEN = all W calendar; there is no historical split):
- `L_D = 1` iff a burst `b` of the subject lies in `[D − 120 min, D − 5 min]` and its entry print `e(b)` (max YES-terms
  price in `[b + 60 s, b + 15 min]` in the market of `D`) exists and is **≤ 0.75** (a tradable lead: the price had not
  yet moved and a print confirms a fill was possible). No print → `L_D = 0` (conservative).
- `π̂_D` = the mean of the same indicator over the four placebo windows shifted by −7, −14, −21 and −28 days (same
  subject, same market, same clock time; a placebo window before listing or uncovered drops out; < 2 placebo windows →
  "no placebo", counted).
- `Δ_W1 = mean_D (L_D − π̂_D)`; one-sided > 0; floor +0.25; p = max over the subject and ISO-week ways.
- **Binding calibration placebo (subject time shift).** Bursts of each subject are shifted by a uniform random offset
  in `[−60, −30]` days (one per subject per draw; 200 draws, seed 14101) and the statistic recomputed. *Alternative
  guarded:* subjects with busy articles have many bursts, so any 2-hour window of theirs looks "led", and the
  same-subject placebo at fixed weekly lags may share a weekly editing rhythm.
- **Binding robustness.** Each keeps the sign and p < 0.05: lead window `[D − 60 min, D − 5 min]`; entry cap 0.60;
  CB11-A entity subjects dropped (§1.3); heads of government and state dropped (frozen list from the subject
  description); each class with ≥ 15 `D` (resign, out-as); each half of the calendar; top-5 subject and week drops.
- **Reported (uncounted).** CH123's lead distribution (the first burst minus the first print ≥ 0.90, median and share
  > 5 min, including negative leads: the market first), by class and for deaths; the burst-rule grid.

**W2 (burst-triggered taker, recorded prints).** Units: bursts `b` of mapped subjects in the W calendar for which the
subject has a **trade market** `m(b)` = the subject's market with the nearest scheduled end at or after `b + 3 h` whose
state at `b` is in **[0.05, 0.60]** and whose prints cover `[b − 6 h, b + 2 h 30 min]` (frozen choice; other markets
reported). `net(b) = x − e − r·e(1 − e) − r·x(1 − x)` (§2.1). Mean over units (each burst weight 1), one-sided > 0,
floor +1.0c; p = max over subject, ISO-week and story-day ways.
- **Binding pre-burst placebo.** The same rule at `b − 24 h` (entry and exit windows shifted by 24 h) must not pass
  p < 0.01. *Alternative guarded:* W2 picks volatile subjects and periods in which buying YES paid regardless of the
  burst (a YES-heavy selection of subjects).
- **Binding "before the move" check.** Restricted to units with `|state(b) − state(b − 60 min)| ≤ 5c`, W2 keeps the sign
  and ≥ half. *Alternative guarded:* the burst merely follows a move already under way (momentum), which a reader of
  prices alone would capture.
- **Binding worst-case reach.** p < 0.01 and the floor still hold when every burst that would be a unit but for
  "uncovered" or "no entry print" is included at net = −4.5c (the median round trip of `EXECUTION_COSTS.md`). *Alternative
  guarded:* newest-first prints reach less far back in markets that later traded heavily, which are the markets where
  the event happened, so dropping uncovered bursts drops pre-event false bursts of YES markets and flatters W2 (CB12
  round 1 item 4).
- **Robustness (binding).** +1.0c per side; exit at `b + 1 h` keeps the sign; state band [0.05, 0.40] keeps the sign;
  CB11-A entity subjects dropped; "stale exit" units dropped; top-5 subject, week and story-day drops; leave-one-quarter-out sign.
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
(trailing baselines bootstrapped from the revisions API at subject entry), and on a burst reads CLOB `/book` for each of
the subject's mapped markets at `b + 60 s`, 5, 15 and 120 min.
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

**Clock alignment (frozen; causal).** The transcript clock is mapped to the wall clock from the price jumps of words
already said:
- an **anchor** is a member `j` with transcript first-mention offset `o_j` and a jump time `J_j` = the first minute at
  which its 1-minute price is ≥ 0.85 while its price 3 minutes earlier was ≤ 0.60; `δ_j = J_j − o_j`;
- at checkpoint `t`, `δ_t` = the median `δ_j` over anchors with `J_j ≤ t − 1 min`, provided ≥ 2 such anchors lie within
  5 min of the median (else the unit is "unaligned", counted);
- the transcript clock is `e_t = t − δ_t`; a word is **unsaid at `t`** iff its first-mention offset is > `e_t + 60 s`
  or it is not said at all. A viewer at `t` knows which words have been said, when the speech started, and that it is
  still running (units need `e_t < L`, the speech not yet over at `t`). The causal accessor never reveals offsets after `e_t`.
- `π_w` = the word's last usable price before `δ_first − 5 min` (`δ_first` the event's first `δ_t`), i.e. before the
  speech started.

**Units.** (word, 5-minute wall-clock checkpoint `t`) from the first aligned `t` with `e_t ≥ 10 min` (the first minutes'
mentions are information events, not decay), the word unsaid, `p_t ∈ [0.03, 0.97]`, `p_lag` available. **Each word
weight 1, split over its units** (`Y` is one value per word). `Y` = the Gamma resolution (guarded; 0.5 for 50-50;
unresolved or voided words scored 0.5 with a binding worst case); the transcript-derived `Y` is a robustness check.

**S1 (forecasting).** The word-weighted OLS slope `β̂` (with intercept) of `(Y − p_t)` on `(q_t − p_lag)` over P ∪ N
units; one-sided > 0; floor 0.30; p = max over the event and ISO-week ways.
- **Binding sign-flip calibration.** One coin per event flips the regressor; 200 draws (seed 14102). *Alternative
  guarded:* within-speech dependence (a long speech says many late words) makes the clustered p anti-conservative.
- **Binding clock attribution (joint fit).** A joint OLS of `(Y − p_t)` on `(q_t − p_lag)`, `(π_w − p_lag)` and
  `(p_lag − p_{t−15 min})` must keep the `q_t` coefficient at ≥ half its solo value with one-sided p < 0.05 (max over
  ways). Otherwise S1 cannot advance, and the label is "start-price drift or momentum, not the clock". *Alternative
  guarded:* the anchor predicts only because unsaid words drift down from their start price anyway (the M1 object, or a
  generic in-speech drift).
- **Robustness (binding; each keeps the sign).** P alone and N alone (the disjoint and nested halves, §1.3);
  transcript-derived `Y`; `e_t ≥ 20 min`; 10-minute checkpoints; shrinkage weight 5 and 20; prepared speeches only;
  events whose first anchor is > 90 min after `startTime` dropped; unresolved words at `Y = 1`; top-5 event and week
  drops; each calendar half.
- **Reported (uncounted).** The slope by elapsed band (10-30, 30-60, > 60 min), by type and by start-price band; the
  transcript-Gamma agreement (< 95% → the label "settlement basis"); non-primary speakers; the unconditional mean of
  `Y − p_t` on unsaid words (the level, which is CB12-M's object, reported only for P).

**S2 (in-speech maker, recorded prints).** On every word with an S2-eligible unit (`e_t ≥ 30 min`, unsaid, aligned),
the ask and trade-through fill rule of §2.1; net per filled share `= a − Y`. Statistic: mean over events with ≥ 1 fill
of the event's net per filled share (events without fills counted); one-sided > 0; floor +1.0c; p = max over event
and week ways. S2 fills are in-speech, so they never coincide with CB12-M's M2 fills, which stop at `startTime`.
- **Binding placebo (calibrated at fill).** `Y*` drawn calibrated to the fill-time price with the GSP latents; 200 draws
  (seed 14103). *Alternative guarded:* the trade-through rule selects fills after up-moves, so a maker could look
  profitable on fill mechanics alone (CB12-M M2's placebo).
- **Robustness (binding).** §2.1 cost robustness; worst-case reach (members whose prints do not reach back to `t` are
  filled at `a` for 100 shares iff `Y > 0`, as CB12 A4); P alone and N alone keep the sign; top-5 event drops.
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
{"id": "q0309_cb14_screen_W", "title": "CB14-W: W1 (lead excess over same-subject placebo windows; subject and week ways; subject time-shift calibration; lead-window, entry-cap, CB11-A, heads-of-government, class, half, top-5 robustness) and W2 (burst-triggered taker at recorded prints; subject, week, story-day ways; pre-burst placebo; before-the-move check; worst-case reach; cost, exit, band, stale-exit, top-5, quarter robustness); reported precision, false-burst rate, lead distribution, deaths, grid", "family": "creative_batch_14", "priority": 14, "expected_value": "W verdicts", "data": ["history/h14_wiki/"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0308_cb14_census_W"], "argv": ["scripts/run_cb14.py", "screen", "--family", "W"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch14/results_W.json", "trials.jsonl (cb14_test + creative_batch_14:W n_tests=2)"], "next_action": "advanced: q0311 after the live window", "notes": "DRAFT. Refuses before the W freeze hash and unless GW0, GWC, GW and GWP passed (else counted lines)."}
{"id": "q0310_cb14_w_live", "title": "CB14-W live collector (cron every minute, flock, outside queue lanes): list=recentchanges poll (namespace 0, rclimit 500, receipt time), live burst rule with bootstrapped baselines, CLOB /book at b+60s, 5, 15, 120 min for each mapped market of the subject; daily frozen-query refresh of active markets; weekly blind map-audit batch file", "family": "creative_batch_14", "priority": 0, "expected_value": "W Stage 2 data at recorded books", "data": ["en.wikipedia.org action API", "public CLOB /book", "public Gamma"], "resources": {"mem_mb": 150, "cpu": 1, "lane": "cron", "network": "en.wikipedia.org, clob, gamma-api"}, "depends_on": [], "argv": ["scripts/run_cb14.py", "w-live", "--rules", "../docs/research_lab/seals/cb14_rules.json", "--not-before", "2026-10-26T00:00:00Z", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "40"], "timeout_s": 55, "max_retries": 0, "outputs": ["history/h14_wiki_live/{polls,bursts,books,frame,audit_batches}/"], "next_action": "runs to T14_W2_end; then q0311 if triggered", "notes": "DRAFT. Installed by the coordinator after the W freeze (crontab.txt line, as CB12 q0257). Reads no AREPO store. Stops at T14_W2_cap."}
{"id": "q0311_cb14_rep_W", "title": "CB14-W Stage 2: W2-rep (recorded best ask at b+60s, best bid at b+120 min, fee, +1c robustness; >= 300 bursts in >= 30 subjects) and W1-rep (>= 20 decisive moves in >= 15 subjects, live burst log as the clock); poll latency and ask life reported", "family": "creative_batch_14", "priority": 14, "expected_value": "L2 verdicts", "data": ["history/h14_wiki_live/", "public Data API (post-hoc prints for W1-rep)"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0309_cb14_screen_W"], "argv": ["scripts/run_cb14.py", "rep", "--family", "W"], "timeout_s": 2400, "max_retries": 1, "outputs": ["research_lab/creative_batch14/results_W_rep.json", "trials.jsonl (cb14_replication + creative_batch_14:W:rep)"], "next_action": "pass: Stage P-W registration draft", "notes": "DRAFT. Only triggered tests; alpha/4 if early, full Stage-2 Holm once."}
{"id": "q0312_cb14_s_frame", "title": "CB14-S frame: Gamma tag 100343 one-week end-date walk over [2024-11-01, 2026-03-01); >= 8 binary members, startTime, occasion <= 36 h, CB12-M sports registry + broadcast regex, key drops (S rule; h12_say SCREEN ids kept for N), primary-speaker title map, rule booleans, term parser; Factbase record map (speaker, date +-1 d, type, keywords); subsets P and N; NO outcome stored (outcomePrices/umaResolutionStatus discarded at parse); GS0 audit sample (seed 14122)", "family": "creative_batch_14", "priority": 13, "expected_value": "S population and transcript map", "data": ["public Gamma", "rollcall.com factbase search API", "creative_batch14/exclusion_keys.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api, rollcall.com"}, "depends_on": ["q0301_cb14_smoke_S", "q0302_cb14_exclusion_keys"], "argv": ["scripts/run_cb14.py", "s-frame", "--rules", "../docs/research_lab/seals/cb14_rules.json", "--rps", "2", "--factbase-rps", "0.5", "--disk-cap-gb", "0.005", "--data-dumps-cap-gb", "40"], "timeout_s": 2400, "max_retries": 2, "outputs": ["history/h14_speech/{frame.csv.gz,members.csv.gz,map.csv.gz,manifest.json}", "research_lab/creative_batch14/s_map_audit_sample.csv"], "next_action": "q0313; GS0 audit (science-reviewer, blind)", "notes": "DRAFT. No price, print, transcript text or outcome read. Never opens h12_say."}
{"id": "q0313_cb14_s_fit_fetch", "title": "CB14-S: Factbase timestamped transcripts of primary speakers dated [2023-01-01, 2024-11-01), parsed and reduced at parse to per-term first-mention offsets and last offset (term list from frame text); no text stored", "family": "creative_batch_14", "priority": 12, "expected_value": "position-model inputs", "data": ["rollcall.com factbase", "history/h14_speech/members.csv.gz (terms only)"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "net", "network": "rollcall.com"}, "depends_on": ["q0312_cb14_s_frame"], "argv": ["scripts/run_cb14.py", "s-fit-fetch", "--rules", "../docs/research_lab/seals/cb14_rules.json", "--factbase-rps", "0.5", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "40", "--budget-min", "40"], "timeout_s": 3600, "max_retries": 2, "outputs": ["history/h14_speech/fit/{offsets.csv.gz,manifest.json}"], "next_action": "q0314", "notes": "DRAFT. One page in memory at a time (about 2 MB).", "repeat": {"max_runs": 3, "until_log_regex": "\"status\": \"s_fit_fetch_complete\""}}
{"id": "q0314_cb14_s_fit", "title": "CB14-S: frozen position model S_w(e) by speaker, type class and term from fit offsets only (shrinkage 10 to the pooled curve; 1-minute grid to 180 min); model file sha256 recorded for part S", "family": "creative_batch_14", "priority": 14, "expected_value": "the frozen anchor", "data": ["history/h14_speech/fit/"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0313_cb14_s_fit_fetch"], "argv": ["scripts/run_cb14.py", "s-fit", "--rules", "../docs/research_lab/seals/cb14_rules.json"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch14/s_model.json"], "next_action": "pin the model sha256 in part S (commit); q0316 after GS0", "notes": "DRAFT. Refuses if any h14_speech price, print, guarded or target file exists."}
{"id": "q0316_cb14_s_pregate", "title": "CB14-S pre-fetch gate GSC, counts only, no network: primary-speaker events with a mapped Factbase record across P and N (>= 100, >= 30 ISO weeks, >= 25 in P), GS0 PASS, smoke availability rule; FAIL -> S1, S2 not testable (population), counted, and q0317/q0318 never committed", "family": "creative_batch_14", "priority": 14, "expected_value": "saves about 16,000 requests if S cannot be powered", "data": ["history/h14_speech/{frame,map}.csv.gz", "creative_batch14/s_map_audit.json", "creative_batch14/smoke_S.json"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0314_cb14_s_fit"], "argv": ["scripts/run_cb14.py", "pregate", "--family", "S"], "timeout_s": 900, "max_retries": 1, "outputs": ["research_lab/creative_batch14/pregate_S.json", "trials.jsonl (cb14_descriptive or the counted not-testable lines)"], "next_action": "PASS: commit q0317 (and q0318 for T14_S_open)", "notes": "DRAFT."}
{"id": "q0317_cb14_s_data_P", "title": "CB14-S P: target transcripts (reduced to per-member first-mention offsets and last offset, guarded_p/), CLOB prices-history fidelity 1 over [startTime - 30 min, startTime + 5 h] per member, Data API prints (<= 2 pages) aggregated to transactions in that span, Gamma outcomes to guarded_p/outcomes_guarded.csv.gz", "family": "creative_batch_14", "priority": 11, "expected_value": "S P data", "data": ["rollcall.com factbase", "public CLOB prices-history", "public Data API", "public Gamma"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "net", "network": "rollcall.com, clob, data-api, gamma-api"}, "depends_on": ["q0316_cb14_s_pregate"], "argv": ["scripts/run_cb14.py", "s-data", "--subset", "P", "--rules", "../docs/research_lab/seals/cb14_rules.json", "--rps", "2", "--factbase-rps", "0.5", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "40", "--budget-min", "60"], "timeout_s": 4800, "max_retries": 2, "outputs": ["history/h14_speech/{prices_p.csv.gz,tx_p.csv.gz,guarded_p/,manifest_p.json}"], "next_action": "q0319 (with q0318)", "notes": "DRAFT. Refuses unless the model sha256 is pinned in part S. No side, wallet or hash stored.", "repeat": {"max_runs": 3, "until_log_regex": "\"status\": \"s_data_P_complete\""}}
{"id": "q0318_cb14_s_data_N", "title": "CB14-S N (CB12-M SCREEN window, nested): the same fetch as q0317 into guarded_n/; refuses before T14_S_open (CB12-M Stage-1 result commit or its ledger stop record, verified by commit hash)", "family": "creative_batch_14", "priority": 10, "expected_value": "S N data", "data": ["rollcall.com factbase", "public CLOB prices-history", "public Data API", "public Gamma"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "net", "network": "rollcall.com, clob, data-api, gamma-api"}, "depends_on": ["q0317_cb14_s_data_P"], "argv": ["scripts/run_cb14.py", "s-data", "--subset", "N", "--rules", "../docs/research_lab/seals/cb14_rules.json", "--require-open", "cb12_m_stage1", "--rps", "2", "--factbase-rps", "0.5", "--disk-cap-gb", "0.15", "--data-dumps-cap-gb", "40", "--budget-min", "110"], "timeout_s": 7200, "max_retries": 2, "outputs": ["history/h14_speech/{prices_n.csv.gz,tx_n.csv.gz,guarded_n/,manifest_n.json}"], "next_action": "q0319", "notes": "DRAFT. Exit 75 (pending) before T14_S_open. Never opens h12_say.", "repeat": {"max_runs": 6, "until_log_regex": "\"status\": \"s_data_N_complete\""}}
{"id": "q0319_cb14_census_S", "title": "CB14-S census, counts only on P and N: events by subset/speaker/type/month; parser, Q&A, map, parse failures; alignment success and anchors; units by label; q_t - p_lag distribution (prices before t, causal transcript accessor); S2-eligible units and fills; gates GS, GSP (one latent per word, GMP loadings, seed 14121), GSP2; MDEs", "family": "creative_batch_14", "priority": 14, "expected_value": "S gates and MDEs before the freeze", "data": ["history/h14_speech/ (guarded_* through the causal accessor only; no outcome file)"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0317_cb14_s_data_P", "q0318_cb14_s_data_N"], "argv": ["scripts/run_cb14.py", "census", "--family", "S"], "timeout_s": 2400, "max_retries": 1, "outputs": ["research_lab/creative_batch14/census_S.json", "trials.jsonl (cb14_descriptive)"], "next_action": "science-reviewer freeze check (S part)", "notes": "DRAFT. No Y, slope or net computed."}
{"id": "q0320_cb14_screen_S", "title": "CB14-S: S1 (word-weighted slope of Y - p_t on q_t - p_lag; event and week ways; event sign-flip calibration; joint clock attribution with pi - p_lag and momentum; P-alone, N-alone, transcript-Y, e>=20, 10-min, shrinkage, prepared-only, late-start, unresolved, top-5, half robustness) and S2 (in-speech maker, trade-through prints, Gamma payoff; calibrated-at-fill placebo; cost, worst-case reach, P/N, top-5 robustness)", "family": "creative_batch_14", "priority": 14, "expected_value": "S verdicts", "data": ["history/h14_speech/ (guarded_p, guarded_n opened here)"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0319_cb14_census_S"], "argv": ["scripts/run_cb14.py", "screen", "--family", "S"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch14/results_S.json", "trials.jsonl (cb14_test + creative_batch_14:S n_tests=2)"], "next_action": "advanced: q0322 after the Stage-2 window", "notes": "DRAFT. Refuses before the S freeze hash and T14_S_open, and unless GS0, GSC, GS, GSP/GSP2 passed (else counted lines)."}
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
    the 7-day dedup); `L_D` entry cap 0.75 and "no print → 0"; placebo windows before listing dropped; the
    trade-market choice; entry max and exit min prints; fees; worst-case reach; GWP writing no point estimate;
  - S: N paths refused before `T14_S_open` (fixture commits present and absent; stop-record branch); the HOLDOUT window
    excluded by date (an event ending 2026-03-01T00:00Z refused); q0314 refusing when price or target files exist; the
    model shrinkage and `q_t` at known values (`Ŝ = 1` → `q = π`; `Ŝ = 0` → `q = 0`); the alignment rule (1 anchor →
    unaligned; 2 anchors 6 min apart → unaligned; anchors after `t − 1 min` ignored); the causal accessor never
    returning an offset after `e_t`; unsaid at `e_t + 60 s`; word weights summing to 1; the trade-through fill and
    one-fill-per-word rule; `p_lag` ≠ `p_t`; GSP's one latent per word;
  - `battery2` kinds and k1 = 4 fixed; the α/4 early rule in Stage 2.

## 6. Test budget and compute

| Job | Tests counted | Kind(s) | Decision |
|---|---|---|---|
| Stage 1: W1, W2, S1, S2 | **4** | `cb14_test` + count lines `:W` (2), `:S` (2) | p < 0.01, floor, binding placebos and robustness, batch Holm (one-sided α 0.05, k1 = 4 fixed); counted with p = 1 if a gate, audit or smoke fails |
| Stage 2: W1-rep, W2-rep, S1-rep, S2-rep (each only if triggered) | ≤ 4 | `cb14_replication` + `:<family>:rep` | one Holm over CB14 Stage 2, one-sided α 0.05 (early finishers at α/4) |
| Smokes, audits, pre-gates, census, gates, strata, grids, CH123 descriptives, latency | 0 | `cb14_descriptive` | - |
| **Total** | **4 fixed + ≤ 4 conditional = 4-8** | | cumulative 1,221 (verified at `647549c`) → with CB13's 3-8 and CB14's 4-8: 1,228-1,237, plus whatever CB6-CB13 add first |

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

1. **W is thin where it matters.** Decisive moves are rare (planning 40-80 in 30-55 subjects); GW may fail at CH123's
   own 40, and W1's testability minimum is a declared deviation (§2.3). The listing-date frame (premise 1) keeps early
   resolutions without selecting on outcome, but it is new in this programme: the challenger should check that no
   eligibility rule reads status, `closedTime` or outcome.
2. **The market-to-article join.** The entity rule is CB11-A's, extended with an office-word stop list; GW0 audits
   every pair blind. Ladders of one subject share one article, and one crisis can move several subjects: the subject,
   ISO-week and story-day ways are meant to carry that. Is the story-day way (by country) defined well enough?
3. **Newest-first print reach** correlates with later activity, so W2's unit set could be selected on the event
   (CB12 round 1 item 4). The binding worst-case reach check prices every dropped burst at −4.5c; is that the right
   worst case?
4. **Historical edit times versus a live reader.** Revisions carry save times, and W assumes action at `b + 60 s`.
   Stage 2 measures the real poll latency. Bot flags use current group membership (hindsight, minor); oversighted
   revisions are invisible (disclosed). `mw-reverted` is excluded as look-ahead (premise 4).
5. **CB11-A disjointness** rests on calendar (W rows end 2026-04-01), keys (the whole `h11_attn` frame) and objects
   (edits, not pageviews), with a binding drop of CB11-A entity subjects. Should W also drop subjects whose articles
   CB11-A's HOLDOUT uses, in calendar months CB11-A uses only for its baseline?
6. **S nesting on CB12-M's SCREEN (N).** The design waits for CB12-M's Stage-1 result, never touches its HOLDOUT or any
   `h12_say` file, and anchors `q_t` on the word's own start price so that M1's level object sits in the intercept.
   `Y` is still shared, so S1 on N is not independent of M1. The challenger may prefer P-only Stage 1 (underpowered,
   MDE about 0.7-0.8) with N as a reported reading, or N as Stage 2 instead of post-freeze events.
7. **S's clock alignment** uses the price jumps of words already said, so it is causal, but alignment may fail more
   often in quiet speeches, which is a selection on activity. Alignment success and its relation to `π` are reported.
   Transcript timestamps are segment-level (about 10-30 s), so the 60 s margin on "unsaid" is narrow.
8. **S is effectively a single-speaker test** (Trump, by the ≥ 40-transcript rule). The speaker cluster way is
   impossible; event and week ways carry the dependence. Results do not generalise to other speakers or to earnings
   calls (excluded: no keyless timestamped transcripts).
9. **The position model** is fitted on 2023-2024 campaign speeches and applied to 2024-2026 events. Presidential
   remarks, press conferences and interviews differ from rallies (type classes help, but only partly). Shrinkage
   weight 10 is a prior choice, with 5 and 20 as binding robustness.
10. **1-minute history before 2025** is unverified (premise 2); the P months may thin by the smoke's availability rule.
11. **Fees** are the current `feeSchedule`, not point-in-time; W2 uses `max(rate, 0.04)`, which may overstate 2024-2025
    costs (conservative).
12. **Transcript versus venue resolution.** S's primary `Y` is the Gamma resolution; the transcript governs only the
    clock and "unsaid". Words the transcript misses but the speaker said would enter as unsaid units with high prices;
    the `[0.03, 0.97]` filter and the agreement audit are the guards.
13. **CH127 is not tested** (§0.4).

## 8. Next actions

1. Challenger round 1 (`science-reviewer`) on this draft; responses as CB13 §9-§10. Points to rule on first: the W1
   testability deviation (§2.3), the listing-date frame (premise 1), the S nesting decision (§1.3) and the clock
   alignment (§CB14-S).
2. Write `seals/cb14_rules.json` (parts `common`, `W`, `S`), the modules and tests of §5 and `run_cb14.py`
   (implementer); then the code-against-design freeze check.
3. W order: q0300 → q0302 (behind CB13 q0276 and CB11 q0227) → q0303 → GW0 audit → q0305 (GWC) → q0306 → q0307 →
   q0308 → W freeze → q0309; q0310 installed after the W freeze, not before 2026-10-26; q0311 if triggered.
4. S order: q0301 → q0312 → GS0 audit → q0313 → q0314 (model hash pinned) → q0316 (GSC) → q0317 (P) → `T14_S_open` →
   q0318 (N) → q0319 → S freeze → q0320; q0321 weekly after the S freeze; q0322 if triggered.
5. The S rules part is committed before CB12-M's q0252 runs (§1.3).
6. CB15 adds CB14's frame ids (W markets and subjects, S events) to its keys. CH127 re-enters with the census of §0.4.
7. Ledger lines for every counted result; checkpoint and plain-English dashboard updated by the orchestrator.
