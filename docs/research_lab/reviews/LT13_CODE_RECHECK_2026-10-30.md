# LT13 code re-check (science-reviewer, 2026-10-30; read-only, saved by the experiments autopilot)

**Verdict: ACCEPT.** One required step remains before the seal (item 1). Two points should be disclosed.

**Tests:** `pytest -q tests/test_live_tests13*.py` 101 passed. Worktree clean at a3b8e4cf.

1. **Design text verified.** New file sha256 `737f8b15…b2a2`; its first 139,978 bytes (the old file's length) hash to
   `ae594aa1…f738`; the two appended lines match the quoted amendment exactly. **Open:** the real ledger has no line with
   `LT13 DESIGN TEXT AMENDED 13`, so `design_text_error()` refuses on the real ledger (safe direction). The ledger line
   with both hashes must be committed before q0721 (the seal).
2. **MUST 2 verified.** `spread_km1_c` gone from `controls_own` (still built, l. 624); `thin` reads spread at k−1;
   zero-variance controls removed before the rank and reported `zero_variance_dropped`; `loose_spec` no longer edits the
   control list. Probe: n=756, rank 28 = n_cols 28, status ok, 12 zero-variance columns dropped; n=0 returns
   `unavailable`, so the test cannot pass on zero rows. The three spread columns have rank 2 (a genuine identity); with all
   three kept the resolver returns `unavailable`, confirming the defect. Minor: the invariance test uses plain `lstsq`, not
   the production fit path (follows from Frisch-Waugh-Lovell).
3. **MUST 3 verified.** `fee_on` NaN for unknown fee class, excluded and counted (`fee_class_unknown_units`).
4. **SHOULD 4-6 verified.** Census refuses on a code_sha256 mismatch or a seal without one; gate flips cover `ident_top1`,
   `ident_batch`, `corr_zs_*` (one `corr_max` threshold flips all three) and `g_eff`; renames printed under
   `registry.batch_renames`. **Disclose:** the A8 print counts members with no two-sided row at k−1 or k ("closed,
   one-sided or gone"), wider than "closed-member share"; describe it as `batch_members_absent`.
5. **`design_text_error` verified.** Needs the new hash in the file plus one ledger line with the marker and both full
   hashes; refuses otherwise.
6. **Nothing else changed.** Only `controls_own` and `controls_note` changed in `DECLARED` (declaration hash moves, not
   yet pinned anywhere); drafts q0720-q0722 changed prose only; spec JSON only its design hashes.

**Could not verify:** that no census-span data was opened; that the ledger line will be written correctly; `J` rows vs
`bt.bid` alignment for `bc_members_absent` (inferred from code); q0722 memory.
