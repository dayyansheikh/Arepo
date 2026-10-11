# AREPO — Plain-English Progress

**Last updated:** 2026-10-11 01:56 UTC+1
**Current phase:** Phase 3, final live test **PASSED WITH LIMITATION**. Closure is awaiting an independent check (minutes away). Phase 4 tools and experiments are under way.
**Overall status:** On track. No blocking decisions.
**Current objective:** Confirm the Phase 3 closure, finish the 24-hour E004/E005/E006 collection, and get the data safely into a private offsite repo.

## 1. Where we are
AREPO asks whether information knowable *before* a prediction helps forecast Polymarket price moves better than the
current price and recent momentum.
- **Research machinery:** tonight's single frozen live test (D116) ran the whole final pipeline end to end and passed every engineering check. Once the independent check confirms it, Phase 3 is done.
- **Forecasting:** the first prospective test (E002) **confirmed** a short-term price reversal on unseen data. It is exploratory, not a tradable edge.

## 2. What AREPO can actually do today
- Run the complete research pipeline live in one go, in about 24 minutes:
  - find every market (about 270k);
  - sample fairly;
  - screen;
  - watch order books;
  - freeze predictions;
  - collect outcomes;
  - audit itself with the original code.
- Snapshot all markets every 2 hours, log forecasts *before* outcomes, and score them later.
- Compare models with leakage-safe, fully logged and fingerprinted analyses, with power calculations stating what each test can detect.
- Show all of this on a "Research Lab" page in the app, as an open lab notebook. The page is not deployed.

## 3. What the latest results establish
| Item | Result |
|---|---|
| **D116 (Phase 3 final live test)** | **PASS WITH LIMITATION.** All 10 engineering gates passed with zero engineering problems, and 4 of 8 sampled markets went fully end to end. The other 4 were genuinely unavailable at the source. Limitation: every market whose trigger was assessed triggered, so no comparison "control" market could be paired. This was predeclared as a data outcome, not a bug. |
| **E002** | **Confirmed (exploratory, prospective).** About 21% of the last-hour price move reverses within about 5h (R² +0.027 [+0.005, +0.046]), on 40k markets it had never seen. It even holds in tight-spread markets, but only about 2% of forecasts beat half the spread, so it is **not shown to be tradable**. |
| E003 | Order-book imbalance: no measurable value at about 2 minutes (a useful negative). |
| E004/E005/E006 | Collecting: snapshot 1 of 12 done, then one every 2h. E006 (does the reversal depend on liquidity or time-to-end?) is newly registered after an independent design review. |

## 4. What's happening right now
- An independent reviewer is checking D116's result before Phase 3 is declared closed.
- All research data (about 21 GB) is being compressed into checksummed archives and uploaded to a **private** GitHub repo (`arepo-data`), then verified against GitHub's own checksums.
- E004 snapshot 2 is due about 03:24 UTC+1.

## 5. Issues and risks
| Issue | Why it matters | Blocks progress? | What is being done |
|---|---|---|---|
| The only full backup is in progress | Evidence exists on one disk | No | Private repo upload under way. The SD-card copy is partial and unverified; a physical backup is still recommended |
| Control-market pairing has never formed live (D097 and D116) | One part of the design is untested in real conditions | No | Carried forward as a known limitation; the design for Phase 4 is under review |
| The reversal may be quote noise | It may not be usable | No | E004's spread-crossing check |
| Disk now 22 GiB free (D116 added about 4 GB) | Plenty for now | No | Compression is optional, and only if space drops below about 15 GB |

## 6. Decisions I need from you
**No decisions required from you currently. Autonomous work is continuing.** Backup, website wording and compression are parked, as you asked.

## 7. What's next
1. Close Phase 3 if the independent check agrees, and record the limitation.
2. Finish the 24h collection, then score E004, E005 and E006.
3. Start Phase 4 properly: lock the baseline models and run only the experiments that earn a confirmation slot.

## 8. Scientific reality check
- **Demonstrated:** the full research pipeline works live end to end, and one forecasting pattern held on unseen data.
- **Unproven:** that the pattern is tradable, stable over many days, or anything more than quote noise.
- **Validated edge beyond momentum:** **none.**

Details: [checkpoint](AREPO_V2_CHECKPOINT.md) · [ledger](research_lab/EXPERIMENT_LEDGER.md) · [D116 evidence](implementation/PHASE_03_D116_EVIDENCE.json)
