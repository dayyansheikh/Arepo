# LT11 pre-freeze verification (2026-10-23)

`evidence_role: review` | Reviewer: science-reviewer (independent, read-only; filed by the orchestrator). Checked tip `168c765c`, `docs/research_lab/LIVE_TESTS_11.md` sha256 `c96b0351e6d0042ddab1692ab654400714656e6f5ce3374b7c27bdf8de238d36`. Base `80faecf5` sha256 is `69477a63…fb7c9`, which matches the re-check. I checked the fixes against `reviews/LT11_R1_RECHECK_2026-10-23.md:12-17`. Nothing was counted and no data was read.

**Verdict: FREEZE_OK_AFTER 4 mechanical edits** (the freeze commit records the sha256 of the file after these edits)

- **F1-F4 were applied as worded** at lines 936, 942, 1027, 1110-1111 and 228. The diff `80faecf5..168c765c` touches only those lines, the status line (3) and the new 13.x block (1281-1289). The 13.x line numbers are correct.
- **Nothing was loosened.** No gate, threshold, MDE, formula or prior changed. F1 replaces an undefined "covered origins" with a stricter definition: the slot and slot k - 1 must both be complete, plus slots k + 2 and k + 3 for twin pairs.
- **The freeze procedure is consistent** across lines 175-176, 935, 1059-1060, 1094 and 1114. The sha256 goes in the ledger at the freeze, the tokens and CANDIDATES entries are filed at the freeze, and the seal carries the frozen sha256, so it can only be written after the freeze. The status line (3) is accurate.
- **The F3 commits exist:** `c90bbf48` at 13:59:29 +0100 and `522a7e70` at 14:03:42 +0100. The diff of `522a7e70` removes `tl_w2h` and adds `assert "tl_w2h" not in a.columns`.
- **One harmless consequence of F1:** the coverage check is now the same for all three tests, so they become `census_unavailable` together, never one at a time. The rule at 942 is consistent with this.

**Mechanical edits (old -> new):**
1. Line 1145 (section 10 disclosure, which now contradicts F3): "`tl_w2h` not built, 9)" -> "`tl_w2h` coded under a provisional token and removed before deploy, never scored or shown, 9)".
2. Line 1273 (the R1 record): "levels, `tl_w2h` not built)" -> "levels, `tl_w2h` not built; superseded by 13.x F3)".
3. Line 58 (section 0 says "one Holm family", which conflicts with the new rule at 942): "may be re-censused in the ordered lane." -> "may be re-censused in the ordered lane, where it is registered as its own Holm family and never added to a fast-lane family (7)."
4. Line 1282 (the R1 table line numbers after 941 are now off by +1, e.g. "7 table: 968, 969, 970" is now 969-971 and "8.4: 1069-1071" is now 1070-1072): "Line numbers refer to this revision of the file." -> "Line numbers refer to this revision of the file; the R1 table's line numbers above refer to the R1-response revision (sha256 `69477a63…`), and those after line 941 are one higher here."

**Not verified:**
- That `tl_w2h` was never scored in the 4 minutes between the two commits. I only have the commit diffs and messages, not engine logs.
- That "twin pairs" at 936 means the far-future F arm. The term is not defined anywhere else; this was already the case before the fixes.
- Census-time quantities: receipt spans, `volume_num` missingness, and the `T_E015` / `T_E022` dates.
- The venue's reward-rule page.
- The size-check run time.

Orchestrator note: the four edits were applied verbatim; the status line (3) was also updated to name this verification (status text only).
