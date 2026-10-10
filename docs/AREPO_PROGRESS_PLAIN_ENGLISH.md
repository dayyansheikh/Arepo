# AREPO — Plain-English Progress

**Last updated:** 2026-10-10 18:40 UTC
**Current phase:** Phase 3 — Bounded prospective panel (provisional)
**Overall status:** Working through a problem (a storage decision from you is coming up)
**Current objective:** Prove, with one honest live test, that the finished data-collection machinery works end to end, so
that real prediction experiments (Phase 4) can begin.

## 1. Where we are
AREPO is meant to answer one question: does information available *before* a prediction is made help forecast Polymarket
prices better than the market price and recent momentum already do? Answering that has two halves:
1. **Build trustworthy research machinery.** It must find every market, sample fairly, record exactly what was knowable at each moment, and measure what happened next. This is Phases 0-3.
2. **Use it to test predictive ideas** against simple baselines on genuinely new data. This is Phase 4 onwards.

We are near the end of the first half. Nothing in the second half has started. **No predictive value has been shown yet.**

## 2. What has actually been achieved
- **Phases 0-2 are finished:** foundations, a feature store that keeps every number with its source and timestamp, and source/clock rules. They were tested and backed by a real data-collection run.
- **Each part of the Phase 3 machinery has worked live, but in separate runs:**
  - capturing the complete market list (about 273,000 rows in about 7 minutes using compression)
  - fair random sampling
  - recording order-book history before a prediction moment
  - recording prediction moments and later outcomes
  - matching "triggered" markets with comparable "control" markets
- **No single run has done everything at once.** Each trial run (D082, D094, D097, D114) failed at least one of its pre-agreed checks. Those failures stand unchanged.

## 3. What changed since the last update
- An independent review concluded that the earlier "Phase 3 complete" claim was **not scientifically valid**. It stitched together partial successes from different failed runs, which the project's own rules forbid. Phase 3 therefore stays provisional.
- The last software fix lets the market-screening step run for up to 10 minutes instead of 3, which was too short. It is sound and does not change which markets are picked, but it has only been tested in simulation.
- **Lesson learned:** the last trial sampled 2 groups of 4 markets. The groups it happened to draw were too small to supply 8 markets. Sampling 4 groups of 2 fills all 8 slots about 87% of the time, versus about 73% for the old design, measured on the real market structure.
- **New risk found:** each test must finish within one hour of starting to list the markets. Slow steps add up, and nobody had budgeted this. It will now be planned in advance.

## 4. What we're working on now
Preparing **D116**: one live end-to-end test of the final code, from listing every market through recording the outcomes, with an audit at the end. All pass/fail checks carry over unchanged. The only change is the 4 × 2 sampling design described above. If it passes, Phase 3 can close. If it fails, the failure is recorded, diagnosed and a new test designed. It is never retried until it passes.

## 5. Issues and risks
| Issue | Why it matters | Blocks progress? | What is being done |
|---|---|---|---|
| Not enough free disk: about 9.65 GB free, 13.31 GB needed | The test cannot start safely without space reserved for its data | **Yes, for the live run only** | Preparing options for your decision; nothing will be deleted without your approval |
| Raw evidence has no external backup | A disk failure would lose irreplaceable data | Raises the risk of any deletion | Will recommend a backup before any data is retired |
| One-hour freshness limit | A slow but correct run could still fail as "stale" | No; it is planned for | A timeline will be written into the test plan |
| Matched control pair may not occur (in D097 every market triggered) | A fair test may fail on availability, not on bugs | No | Stated honestly in advance; the check will not be weakened |

## 6. Decisions I need to make
| Decision needed | Why it matters | Your recommendation | Urgency |
|---|---|---|---|
| How to get about 4 GB more free disk (external backup first, then approved retirement of old data, or more disk) | Required before the D116 live run | External backup of `data-dumps/`, then free space | Will be needed once the test plan is frozen (soon) |

## 7. What's next
1. Freeze the reviewed D116 test plan. This happens autonomously.
2. Run D116 once storage is resolved. A pass closes Phase 3.
3. Phase 4: test simple baselines (current price, momentum) against richer ideas on new data. This is the first real test of predictive value.

## 8. Scientific reality check
- **Demonstrated:** the individual data-collection steps work on live data, and they are careful about timing and provenance.
- **Unproven:** that the whole final pipeline works in one run, and anything at all about prediction.
- **Validated edge beyond momentum:** **none.**
- **Ready for the next phase?** Not yet. Phase 4 must wait for a passing D116.

Detailed records: [AREPO_V2_CHECKPOINT.md](AREPO_V2_CHECKPOINT.md), [implementation/AREPO_V2_DECISIONS.md](implementation/AREPO_V2_DECISIONS.md).
