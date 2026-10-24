# D120 addendum: result disclosures and challenger review (2026-10-11)

`PHASE_03_D120_EVIDENCE.json` is immutable; this file adds the challenger review's disclosures.
**Challenger verdict: PASS_WITH_CAVEATS.** The authoritative evaluator outcome is PASS.

## What the PASS supports
D120 was frozen at `04e71ea` (record `ea29ae6`) and launched once at 14:47:17Z from HEAD `47375bc`. It completed at 15:02:08Z with peak RSS about 1.05 GB.
- Evaluator (run once): PASS, authoritative. "fill 6/6 with 6 triggers in scope and 6 group-disjoint complete pairs".
- E0-E9 pass; 0 ENGINEERING findings; 5 DATA_SOURCE (one-sided books at screening); 143 OK.
- Accounting: 71 screened (34 triggered, 32 untriggered, 5 unavailable). 6 triggered and 6 control activated. 12/12 role states agree.
- Launch integrity is clean: frozen paths are equal and the protocol and record hashes match.
- 12 distinct dependence groups. The pairs are weather, politics x2, sports x2 and economics, so the categories are diverse.
- Timing maxima, all within limits: window 28.1 s, binding 2.99 s, assessment 61.4 s, audit about 73.5 s, screening 28.3 s.

## What it does not support
- Effect contrasts, calibration, prediction, prevalence or population claims.
- Any claim of fill reliability or control availability rates.
- Any claim of economic independence between pair members.
- Earlier pilots (D082/D094/D097/D114/D116/D118) keep their outcomes.

## Required disclosures
1. **Economic linkage (moderate caveat).** The economics pair (ECB 2026 rate cut vs Eurozone 2026 inflation 1.6-1.8%) shares an economic driver. Group-disjoint means separate events, not economic independence; the rows show `economic_group_status: unresolved`.
2. **Reliability untested.** One run of six stratum trials says nothing about fill reliability (protocol lines 40-41). The D119 item "reliable, non-sibling pairing" is only partly met: non-sibling at event-group level holds for this run; reliability is untested.
3. **Pairs are not independent observations.** One run; all origins share run-level shocks.
4. **Protocol header.** The frozen protocol header still reads "DRAFT - NOT FROZEN" (line 3). The freeze record governs. The frozen protocol is not edited.
5. **Open item: recovery label.** The audit recovery label `original_state: verified_synthetic_runtime` appears alongside provenance `prospective`. It looks inherited and is unexplained. It needs investigation; it did not affect the evaluator outcome.
