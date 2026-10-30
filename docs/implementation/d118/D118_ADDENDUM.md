# D118 addendum: result disclosures and closure review (2026-10-11)

`PHASE_03_D118_EVIDENCE.json` is immutable; this file adds the independent closure review's required disclosures.
**Review verdict (Opus high): ACCEPT WITH DISCLOSURES.** Lift the "live control pairing unvalidated" limitation only within
the protocol's claim scope.

## What the PASS supports
The live same-stratum control-selection and pair-completion path ran end to end **once** (n = 1 run, 2 pairs) on the
population temporal ∩ frame Gamma liquidity ≥ $1000.

The run met every protocol PASS condition:
- E0–E9 pass, with 0 ENGINEERING findings;
- 12/12 complete chains;
- both pairs linked (`matched_trigger_ids` = `trigger_id`), in the same stratum, with targets observed 60.15–60.22 s after origin;
- peak window age at freeze 25.74 s, against the 40 s design criterion and the 60 s code limit;
- launch hashes and timing verified.

## What it does not support
- Any claim about prediction, calibration, prevalence, effect size, independent samples, or control availability rates.
- Any transfer to the D116 temporal population or to the Phase 4 trade-active frame.
- Earlier pilots (D082/D094/D097/D114/D116) keep their outcomes.

## Required disclosures (verbatim from the review)
- **Pair independence:**
  - Pair 1 (2850889/2850890, Knicks/Thunder "make the 2027 NBA Playoffs") is very probably a sibling pair in one Gamma event: the ids and slug stamps are consecutive and the questions are parallel. The receipts carry no `events[]`, so this is unconfirmed.
  - Pair 2 is a different topic and shares no negRiskMarketID; its event is unknown.
  - Every stratum's economic_independence is "unresolved" and event_group is None.
  - Both pairs show the mechanism ran. Neither is an independent observation; there are effectively at most two non-independent pairs.
- **Control availability:** 5 control slots went unfilled (3 in an all-triggered stratum, 1 in each pair stratum). 5 of 7 triggers had no control. Every member also had the scheduled role (arms overlap). The PASS proves the path can run, not that controls are reliably available.
- **Process:** the accepting verification came before commit `dad3c0f`, which tightened preconditions (the launch window and the untracked-code check). That change was frozen without a re-review and the launch followed 21 s after the freeze commit. It only tightens preconditions and the run met them, so the outcome is unaffected. The Opus verification text was not saved separately; its verdict is summarised in the freeze record.
