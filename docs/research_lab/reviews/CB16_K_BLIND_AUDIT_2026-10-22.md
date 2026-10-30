# CB16-K blind audit of PRESENT-TOPIC pairs (2026-10-22)

**Reviewer:** science-reviewer (blind, read-only; text saved verbatim by the experiments autopilot)
**Verdict:** **FAIL (3 / 100 GENUINE; threshold >= 90)**. CH143 is recorded as "not testable at the floor with available or feasibly collectable data".

## Inputs
- Sample: `creative_batch16/audit_K_sample.json` (host; copied to `/tmp/cb16k_audit/` for the audit). Its `shasum -a 256` is `0d317a11b4fa9b9f73374d7cc23c589238731dc194f2b76c9bf536199875b9e7`, which matches the manifest `sample_sha256`. Header fields: `version` cb16-k-audit-sample-v1, `for_auditor` true, 100 pairs.
- Fields read: pair, polymarket_question, polymarket_item, polymarket_end_date, kalshi_title, kalshi_subtitle, kalshi_close_time. No keys, matches, outcomes or prices were read.
- Rule text: `docs/research_lab/CREATIVE_BATCH_16.md` lines 730-770 (re-entry rule at about 751-760).

## Notes
1. **Input scope.** The sampler job q0393 (`docs/research_lab/queue/jobs/q0393_cb16_k_audit_sample.json`) declared before the draw that the auditor file is "titles and the two 3-day-rule dates only". Subtitles and dates are part of that declared titles-only file.
2. **Gate order.** The ledger records the counts condition as PASSED (40 eligible cells for strict ∪ topic, optimistic MDE 0.48 pp <= 2 pp; FAR-TOPIC >= 30 events in >= 5 eligible cells). This audit is the remaining binding condition.
3. **Pending.** The seed (16141), the stratum (30,176 PRESENT-TOPIC pairs) and n_drawn = 100 must still be checked by someone with key access. This audit cannot verify them. (Manifest, read by the orchestrator without the key side: seed 16141, n_requested 100, n_drawn 100, n_present_topic_pairs 30,176, keys_sha256 0148af7a…, census_K_sha256 aebc528a….)

## Rule (stated before classifying)
- **GENUINE:** both markets concern the same event and ask the same or the complementary question. One market's resolution must settle, or nearly settle, the other's in both directions. Allowed differences: wording, source, or "most seats" versus "win". Example: a Polymarket draw paired with the Kalshi "Winner? / Tie" contract for the same match. Dates must be within 3 days.
- **NOT_TWIN:** a different event, entity, match, chart, threshold or bucket. Also any pair where only a one-way implication holds, such as win versus win by more than 1.5 goals, or an exact score versus over 0.5 goals.
- **UNCLEAR:** same event, but nested criteria (for example, different deadlines) mean neither settles the other in both directions. It counts as not genuine.
- Kalshi temperature titles name no city and use °F buckets. Polymarket's (non-US) °C buckets never correspond to them, so these pairs are NOT_TWIN.

## Classification

| pair | verdict | reason |
|---|---|---|
| 0 | NOT_TWIN | Sao Paulo °C vs unnamed-city °F bucket |
| 1 | NOT_TWIN | different match (Betis-RMA vs RMA-Alaves) |
| 2 | NOT_TWIN | SOL vs S&P 500 |
| 3 | NOT_TWIN | Trump vs Cuomo endorsing |
| 4 | NOT_TWIN | London °C vs unnamed °F |
| 5 | NOT_TWIN | top scorer vs Group H winner |
| 6 | NOT_TWIN | XRP vs temperature |
| 7 | NOT_TWIN | BTC vs S&P |
| 8 | NOT_TWIN | London °C vs unnamed °F |
| 9 | NOT_TWIN | exact score vs over 0.5, one-way |
| 10 | NOT_TWIN | ETH vs natural gas |
| 11 | NOT_TWIN | BTC vs S&P |
| 12 | NOT_TWIN | AfD vs Die Linke |
| 13 | UNCLEAR | same Fed-chair announcement; deadlines Mar 31 vs Feb 15 nested |
| 14 | NOT_TWIN | BTC dip vs Trump mention |
| 15 | GENUINE | BSW most seats vs BSW wins, same election |
| 16 | NOT_TWIN | different Hormuz metric/window |
| 17 | NOT_TWIN | win vs win by >1.5 |
| 18 | NOT_TWIN | Busan °C vs unnamed °F |
| 19 | NOT_TWIN | BTC vs temperature |
| 20 | NOT_TWIN | BTC vs temperature |
| 21 | NOT_TWIN | ETH vs temperature |
| 22 | NOT_TWIN | Paris °C vs unnamed °F |
| 23 | NOT_TWIN | match win vs 1st-half win |
| 24 | NOT_TWIN | BTC vs S&P |
| 25 | NOT_TWIN | NFLX vs S&P |
| 26 | GENUINE | draw = Winner "Tie", same match |
| 27 | NOT_TWIN | HK °C vs unnamed °F |
| 28 | NOT_TWIN | Seoul °C vs unnamed °F |
| 29 | NOT_TWIN | BTC vs temperature |
| 30 | NOT_TWIN | SPD vs Die Linke |
| 31 | NOT_TWIN | rebounds prop vs MIP award |
| 32 | NOT_TWIN | Everton relegation vs Liverpool top 4 |
| 33 | NOT_TWIN | London °C vs unnamed °F |
| 34 | NOT_TWIN | US vs global chart, different show |
| 35 | NOT_TWIN | exact score vs over 0.5, one-way |
| 36 | NOT_TWIN | ETH vs temperature |
| 37 | NOT_TWIN | ETH vs S&P |
| 38 | NOT_TWIN | SOL vs gas prices |
| 39 | NOT_TWIN | different golfer |
| 40 | NOT_TWIN | BTC vs temperature |
| 41 | NOT_TWIN | tweet count vs trillionaire |
| 42 | NOT_TWIN | 0-0 vs Colombia win, one-way |
| 43 | NOT_TWIN | Shanghai °C vs unnamed °F |
| 44 | NOT_TWIN | different scoreline |
| 45 | NOT_TWIN | BTC vs S&P |
| 46 | NOT_TWIN | BTC vs gas prices |
| 47 | NOT_TWIN | BTC vs S&P |
| 48 | NOT_TWIN | BTC vs temperature |
| 49 | NOT_TWIN | ETH vs gas prices |
| 50 | NOT_TWIN | SOL vs temperature |
| 51 | NOT_TWIN | HK °C vs unnamed °F |
| 52 | NOT_TWIN | ETH vs gas prices |
| 53 | NOT_TWIN | tweets vs net worth |
| 54 | NOT_TWIN | BTC vs temperature |
| 55 | NOT_TWIN | SOL vs S&P |
| 56 | NOT_TWIN | BTC reach vs Trump mention |
| 57 | GENUINE | draw = Winner "Tie", same match |
| 58 | NOT_TWIN | BTC vs S&P |
| 59 | NOT_TWIN | tweets vs net worth |
| 60 | NOT_TWIN | different match |
| 61 | NOT_TWIN | ETH vs 30Y yield |
| 62 | NOT_TWIN | tweets vs net worth |
| 63 | NOT_TWIN | scores first vs 1H 1-0, one-way |
| 64 | NOT_TWIN | different person |
| 65 | NOT_TWIN | SOL vs temperature |
| 66 | NOT_TWIN | ETH vs temperature |
| 67 | NOT_TWIN | gold vs S&P |
| 68 | NOT_TWIN | BTC vs S&P |
| 69 | NOT_TWIN | Incheon °C vs unnamed °F |
| 70 | NOT_TWIN | BTC vs S&P |
| 71 | NOT_TWIN | match win vs 1st-half win |
| 72 | NOT_TWIN | Seoul °C vs unnamed °F |
| 73 | NOT_TWIN | HK °C vs unnamed °F |
| 74 | NOT_TWIN | ETH vs S&P |
| 75 | NOT_TWIN | BTC vs temperature |
| 76 | NOT_TWIN | Seoul °C vs unnamed °F |
| 77 | NOT_TWIN | Shanghai °C vs unnamed °F |
| 78 | NOT_TWIN | win vs win by >1.5 |
| 79 | NOT_TWIN | BTTS vs every-quarter market |
| 80 | NOT_TWIN | unbeaten champion vs Argentina |
| 81 | NOT_TWIN | ETH vs gas prices |
| 82 | NOT_TWIN | any medal vs one event, one-way |
| 83 | NOT_TWIN | NYC temperature vs MLS Cup |
| 84 | NOT_TWIN | Seoul °C vs unnamed °F |
| 85 | NOT_TWIN | BTTS vs Liverpool win |
| 86 | NOT_TWIN | missed penalties vs Drake attends |
| 87 | NOT_TWIN | BTC vs S&P |
| 88 | NOT_TWIN | BTC vs S&P |
| 89 | NOT_TWIN | BTC vs temperature |
| 90 | NOT_TWIN | ETH vs 10Y yield |
| 91 | NOT_TWIN | win vs win by >1.5 |
| 92 | NOT_TWIN | insult vs meeting |
| 93 | NOT_TWIN | ETH vs temperature |
| 94 | NOT_TWIN | BTC reach vs Trump mention |
| 95 | NOT_TWIN | BTC vs temperature |
| 96 | NOT_TWIN | 2H BTTS vs Tie |
| 97 | NOT_TWIN | exact score vs advances |
| 98 | NOT_TWIN | HK °C vs unnamed °F |
| 99 | NOT_TWIN | AI model vs song chart |

## Totals
- GENUINE: **3** (pairs 15, 26, 57)
- UNCLEAR: **1** (pair 13)
- NOT_TWIN: **96**

| NOT_TWIN group | pairs |
|---|---|
| Crypto, gold or stock market paired with an unrelated Kalshi index, temperature, gas, yield or Trump-mention market | 43 |
| °C temperature paired with an unnamed-city °F bucket | 17 |
| Same match but only a one-way implication | 13 |
| Same contest, different entity or match | 15 |
| Other unrelated | 8 |

All pairs meet the 3-day date rule. The date rule is not the reason for failure: the text rule pairs markets because they share wording.

## Result against the threshold
GENUINE is 3 of 100. The pre-declared threshold is 90 or more of 100, so this is **FAIL**. Even if UNCLEAR counted as genuine, the total would be 4 of 100. The threshold is unchanged.

The re-entry rule is therefore not met. **CH143 is recorded as "not testable at the floor with available or feasibly collectable data".** The counts PASS cannot make up for this, because the PRESENT-TOPIC label does not identify same-event twins.

## Defects (by severity)
1. **Critical:** the PRESENT-TOPIC text rule matches recurring templates rather than events. "price … between", "maximum temperature" and "win" are the common shared phrases. Any K design using strict ∪ topic would measure noise from mislabelled pairs.
2. **High:** Kalshi temperature titles carry no city, so the titles-only audit cannot find location matches. The pairs fail on unit and bucket mismatch anyway.

## Not verified
- Seed, stratum and draw provenance (pending a reviewer with key access).
- The strict-label (non-topic) pair quality, which was not sampled.
- The ledger's counts PASS, which was taken as settled.
