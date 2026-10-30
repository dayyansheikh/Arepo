# CB17 delta freeze check (fixes 1-7 + O-rulings), 2026-10-20 ~19:05Z (science-reviewer; saved by the orchestrator)

**Verdict: FIXES** (two medium defects before the code pin). Verified: re-hash reproduces `seals/cb17_rules.json` byte for
byte (pre ddc0249b, common 23437440, B 64e61091, C 3e24af26, E 9b1eba65); no threshold, floor, alpha, Holm, cut point or
count moved (seal diff cdab2fd5..f0ef434d is text and source shas only); T17 record accepted by `win.require_t17`
(S_8 = 2026-10-26T00:00:00Z); 152 tests; O9 (`idx` ST_OK only, `cb17_b.py:593`; ST_TICK in denominator/worst case
`:625,:722`), O11 (`cb17_rules_c.py:135-138,151-152`), O1 (`cb17_e.py:126-127`) as ruled; fixes 2-7 as specified.

1. **Medium:** partial restore passes the worn pin check (`check_worn_pins`, `cb17_smoke.py:~523-534`, refuses only
   unpinned/mismatched files on disk, never missing pinned ones; P2 list built from whatever `20261015T*` dirs exist) ->
   could become a counted irreversible P2 FAIL. Refuse missing pinned keys.
2. **Medium:** a "monitor stopped" day invents values: B2 `prt` from an empty print set = 0 (`cb17_b.py:292`) and enters
   the `no_print_between_sweeps` subset (`:733`); must be unknown. The stopped record (`cb17_win.py:249-258`) needs a
   per-day reason/evidence.
3. **Low:** pins optional and taken from disk (should be copied from release manifests, mandatory for q0404);
   `source_files` requires `rows_ext` for captures without ext (`cb17_jobs.py:472-477`); B frame missing sweep rows raises
   (`cb17_b.py:65,386`) instead of exit 75; B resume does not check manifest code/rules sha; `require_t17` does not check
   `pre`; B2 tick_change reported-count mask; §12.1 still lists O2/O9/O11 open.

Not verified: host P1-P3 reproduction; whether the collector always writes `rows_ext`; `restore_from_archive.py` hash checks.
