# CB13 gate GL (blind labeller audit) records

Round 1 (2026-10-19): sample drawn on the host by `run_cb13.py audit-sample --round 1` (seed 13121, 200 SCREEN markets,
30 sports-adjacent; labeller `1e515bb4…`). An independent science-reviewer saw only `DEFINITIONS.md` and
`labeller_audit_sample_r1.json` (title, slug) and returned `reviewer_labels_r1.json` (sha256 `2dba4619…`; its prose
totals 66/49/85 were mis-stated, the JSON has 62 LOW / 48 NEWS / 90 other). `audit-score --round 1` on the host wrote
`labeller_audit_r1.json`: overall 0.91; LOW 0.98 / 0.90; **NEWS 0.75 of the labeller's / 0.94 of the reviewer's ->
FAIL** (each group needs >= 0.80 both ways). `disagreements_r1.txt` (titles only) was produced after scoring for the one
allowed revision. Round 2 uses a fresh 200 (seed 13122) and a new blind reviewer; a second FAIL makes T1 and T2
"not testable (labeller)", counted.
