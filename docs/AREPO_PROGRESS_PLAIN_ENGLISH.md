# AREPO — Plain-English Progress

**Last updated:** 2026-10-10 20:31 UTC
**Current phase:** Phase 3 finishing (provisional). Phase 4 forecasting tools and first experiments are under way (Track A).
**Overall status:** Needs my decision (storage) before the final Phase 3 live test. Everything else is continuing autonomously.
**Current objective:** Run the frozen D116 live test once disk space allows. Meanwhile, finish tonight's two forecasting
experiments (E002, E003).

## 1. Where we are
AREPO asks whether information available *before* a prediction helps forecast Polymarket price moves better than the
current price and recent momentum. There are two halves:
- **The research machinery** is built. Its final live test (D116) is now fully designed, independently checked three times, and frozen.
- **The forecasting experiments** have started. Everything there is still exploratory, with no proven edge.

## 2. What AREPO can actually do today
- Snapshot every live Polymarket market (about 276,000) in about 7 minutes, stored compactly (16 MB).
- Read the order books of all ~43,000 actively quoted markets in about 80 seconds.
- Turn snapshots into honest point-in-time datasets: features come only from before the prediction, and outcomes only from after.
- Fit simple models, test them walk-forward (always on later data), log forecasts *before* outcomes exist, and score them later.
- Judge the D116 live test automatically. A checker classifies every outcome by fixed rules (224 cases), so a software bug cannot pass as "the market had no data".

## 3. What changed since the last update
- **D116 is frozen.** Three independent reviews found and closed real loopholes, including one bug that would have failed a perfectly good live run.
- **E001 (past data):** about 30% of a market's last-hour price move reverses by the next snapshot. This held in all four test periods. It is exploratory only.
- **E003, first half:** order-book imbalance on its own explained almost nothing over the next ~80 seconds in the development data. Only about 10% of prices move at all in that time. The independent test is still to come.
- The disk scare was transient: about 4 GB was briefly taken by macOS update staging. AREPO's new data is only about 140 MB.

## 4. What we're working on now
- **E002:** the first truly prospective test of the reversal pattern. Forecasts are already logged; the outcome snapshot arrives about 22:36 UTC.
- **E003:** the second, independent round of order-book data is being collected (about 20:50 UTC), then scored once against the frozen models.

## 5. Issues and risks
| Issue | Why it matters | Blocks progress? | What is being done |
|---|---|---|---|
| Disk: about 11 GiB free; D116 needs about 13.3 GB plus a 1 GB margin | The live test cannot start | **Yes, D116 only** | Lossless compression could free about 4 GB (needs your OK) |
| No external backup of raw research evidence | A disk failure would lose it | No, but it raises risk | Recommend a backup of `data-dumps/` (20 GB) |
| The reversal pattern may be quote noise | Might not be usable in practice | No | E002, plus spread/liquidity breakdowns |
| D116 may end "pass with limitation" (no matched pair) | Likely with 2 markets per group | No | Disclosed in advance; Phase 3 can still close |

## 6. Decisions I need from you
| Decision needed | Why it matters | My recommendation | Urgency |
|---|---|---|---|
| Free about 4 GB by lossless compression of 6 old data folders (same bytes, nothing deleted, verified before swap) | D116 cannot launch without the space | Yes. Ideally back up `data-dumps/` to an external drive first. Then restart Claude with `AREPO_RETIREMENT_SESSION=1` so the safety hook allows it, or run `backend/scripts/storage_compress_exact.py` yourself on the folders listed in the checkpoint | Now; D116 is otherwise ready |

## 7. What's next
1. Score E003 (tonight) and E002 (after about 22:36 UTC), and record the results honestly whatever they show.
2. Once storage is resolved: run D116 once. A pass closes Phase 3.
3. Grow the forecasting side: more feature families (order-flow, related markets), regularised and boosted models on the same walk-forward framework, and a regular snapshot-and-forecast loop.

## 8. Scientific reality check
- **Demonstrated:** the data machinery works stage by stage. The forecasting framework runs end to end without leaking future data.
- **Unproven:** the whole final pipeline in a single live run, and any signal on unseen future data.
- **Validated edge beyond momentum:** **none yet.**
- **Next phase?** Phase 4 findings stay exploratory until D116 passes. Tool building continues meanwhile.

Details: [AREPO_V2_CHECKPOINT.md](AREPO_V2_CHECKPOINT.md), [D116 freeze record](implementation/PHASE_03_D116_FREEZE_RECORD.md),
[experiment ledger](research_lab/EXPERIMENT_LEDGER.md).
