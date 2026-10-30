# CB13 gate GL (blind labeller audit) records

Round 1 (2026-10-19): sample drawn on the host by `run_cb13.py audit-sample --round 1` (seed 13121, 200 SCREEN markets,
30 sports-adjacent; labeller `1e515bb4…`). An independent science-reviewer saw only `DEFINITIONS.md` and
`labeller_audit_sample_r1.json` (title, slug) and returned `reviewer_labels_r1.json` (sha256 `2dba4619…`; its prose
totals 66/49/85 were mis-stated, the JSON has 62 LOW / 48 NEWS / 90 other). `audit-score --round 1` on the host wrote
`labeller_audit_r1.json`: overall 0.91; LOW 0.98 / 0.90; **NEWS 0.75 of the labeller's / 0.94 of the reviewer's ->
FAIL** (each group needs >= 0.80 both ways). `disagreements_r1.txt` (titles only) was produced after scoring for the one
allowed revision. Round 2 uses a fresh 200 (seed 13122) and a new blind reviewer; a second FAIL makes T1 and T2
"not testable (labeller)", counted.

Round 2 (2026-10-19): sample drawn on the host 09:47Z (`audit-sample --round 2`, seed 13122, 200 SCREEN markets,
labeller `95cde0ab…` after revision 1 of 1; 36 overlap round 1). A new blind science-reviewer saw only `DEFINITIONS.md`
and `labeller_audit_sample_r2.json` (copied to an isolated folder) and returned `reviewer_labels_r2.json` (sha256
`4710f404…`; LOW 60 / NEWS 55 / other 85), committed (727665d) before scoring. `audit-score --round 2` on the host wrote
`labeller_audit_r2.json`: overall 0.97; **LOW 0.98 of the labeller's / 0.93 of the reviewer's; NEWS 0.92 / 0.98 -> PASS**
(status `audit_final`). Pre-declared sensitivity, the 164 markets not in round 1 (computed from the key file, same
rule): overall 0.97; LOW 0.98 / 0.94; NEWS 0.92 / 0.98 -> PASS. Verdicts agree, so **GL passes**. The reviewer's
stated ambiguities: non-match sports topics (Ballon d'Or, managers) labelled other; OpenSea FDV labelled LOW; view counts
and benchmark scores labelled LOW; TIME Person of the Year labelled other; dated model releases labelled NEWS.
