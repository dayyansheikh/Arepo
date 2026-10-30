# CB9-P empty frame ruling (science-reviewer, 2026-10-30; read-only, saved by the experiments autopilot)

**Verdict: FAITHFUL_EMPTY.** The empty frame is the declared exclusion rule working as written, not a code defect. The
code's automatic label for P is wrong and needs a runner-only label fix.

**(1) Faithful.** Ids and keys only were counted (`pyth_frame/frame_all.csv.gz`, `exclusion_keys.csv.gz`); no prices,
outcomes or `frame_partial`.
- The 1,235 candidates cover 18 tickers and 77 sessions (2026-04-13 to 08-07), matching the declared window; 18 series ids,
  one per ticker, none shared; one event per candidate, no shared events, no `negRiskMarketID`. No generic or cross-ticker
  key exists.
- **222 dropped by id**, all already in the CB8 q0164 key file (none from CB9's own additions; the q0182b composite-id
  mapping plays no part), across 15 of 18 tickers' series.
- **1,013 dropped by key, all on series only.** The other 3 series (GOOGL 10377, TSLA 10375, NVDA 10374) are carried by 37, 8
  and 38 rows of the CB8 key file that are not P candidates.
- `drop_by_keys` (`cb9_common.py:569`) and `key_types_matched` (`cb7_common.py:255`) use event, neg-risk and series keys, as
  CREATIVE_BATCH_9.md §1.3 (l.172-177) declares; no time window, as declared. Disjointness verified (204 of 328,725 ids lack
  metadata, 0.06% < 2%).

**(2) Record.** §2.7 (l.327-329): a GP fail makes the test "not testable", counted; §2.5 (l.280-282): p = 1, counted.
- Ledger: "CB9-P P1, P2: not testable (empty frame). 0 of 1,235 frame-rule markets survive the q0182b exclusion keys
  (e613604a…375f): 222 by id, 1,013 by series key. Prior batches used all 18 equity daily series. Counted, p = 1. No result,
  not a null."
- Trials: a `creative_batch_9:P` line, n_tests 2, p = 1 each. Batch Holm stays k1 = 5 (§11 item 10).
- Not run, not counted (trigger cannot fire): P1-rep, P2-rep, q0195, q0196.
- q0184: an empty `frame.csv.gz` gives zero days (code reading), so it completes with nothing downloaded; either run it
  (unblocks `require_books_final`) or record "not run (empty frame)" with a census skip path for P.
- q0198 (uncounted) and any Stage-2 frame use the same key drops and are likely empty too (not verified).
- CB10 q0201: pin the header-only file as present (sha256 `ab34dd3e…11f9f`); it adds 0 ids. Precedent: the CB8 updown frame
  (0 ids, accepted as vacuous).

**(3) Label defect (runner only).** With zero units `census_p` (`cb9_pyth.py:920-934`) gets an empty coverage audit, so
P1/P2 come out "not testable (source unavailable)" and the screen (`run_cb9.py:480`) copies that into the trials line: a false
cause that blurs unavailable vs not testable. Minimal fix in `run_cb9.py` (outside `rule_funcs()`): when the frame manifest
shows `kept == 0`, label P1/P2 "not testable (empty frame: exclusion keys)", p = 1. No gate, threshold or key changes; no
amendment, but a reviewer check of the diff. Do not edit rules-hashed `cb9_pyth.py`; do not relax, re-key or narrow the
series rule.

**Not verified:** which seal first brought these markets into the CB8 file; q0184's actual exit on an empty frame; q0198 /
Stage-2 frames.
