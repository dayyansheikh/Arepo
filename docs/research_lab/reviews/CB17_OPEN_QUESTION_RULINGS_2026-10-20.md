# CB17 open-question rulings before the code freeze, 2026-10-20 ~18:45Z (science-reviewer; saved by the orchestrator)

**Verdict: REVISE (accepted by the orchestrator).** Parts B, C, E are not yet binding (e37643f3 exists only on the
worktree branch; §11.6: parts bind once they land on the working branch after acceptance; no SCREEN_8 data before
2026-10-26), so these outcome-blind, stricter changes stay rules-before-data. Record old and new part shas.

- **O2 T17_rules** = committer UTC time of the commit that lands the final re-hashed parts on the working branch
  (`chore/arepo-claude-setup`); record commit, time and all part shas in `seals/cb17_t17_rules.json` and the ledger.
  Landed by 2026-10-25T00:00Z -> **S_8 = 2026-10-26T00:00Z**. Order: fixes 1-7 (done, 9b335fec), O1/O9/O11, re-hash,
  T17 commit, delta freeze check, code pin, q0404 on the host. Loosens nothing.
- **O9 tick change**: no longer an eligibility exclusion (post-decision information that tracks moves into the extremes:
  selection on the outcome); it becomes an availability status handled like "wide mark" (in the availability
  denominator; binding worst case takes the capture mark first, else the adverse bound). Primary sample stays ST_OK only;
  placebos, composition guard and attribution keep exactly their current index sets (synthetic test asserts it).
  Changes: `cb17_rules_b.py:45`; `cb17_b.py:495,499` (drop `!= ST_TICK`), `:612`, `:711` (ST_TICK into the no-mark set);
  same for 6 h marks; design §CB17-B :609-610 and §11.8 O9. **Part B sha changes.**
- **O11 C one-sided worst case**: symmetric by class: transfer min(p5, touch-C); mint-heavy and merge-heavy
  max(p95, touch-C). Changes `cb17_rules_c.py:128-149,192`, caller in `cb17_c.py`, §CB17-C :775-778. **Part C sha changes.**
- **O12 CB16 key pin**: sha256 copied verbatim from q0380's write-once manifest into q0405's spec and the ledger (never
  hash what is on disk). q0380 not run by S_8: q0405/q0406 stay pending (keys). "Keys absent" only with a committed q0380
  stop record under CB16's rules; neither by 2026-11-09T08:00Z: q0406 waits and the orchestrator decides for CB16.
- **Monitor cap (ruling 7)**: option (a) (8 GiB, byte counts only, outside `config_hash`) acceptable before S_8 with a
  COLLECTION_HOST.md deploy and a 40 GB data-dumps guard check (owner confirmation if it counts as infrastructure);
  fallback (b). The binding risk is `trades-` retention: each daily file must have a sha256-manifested copy before
  deletion (archive-before-delete). *Orchestrator note: the nightly `archive_rotate.py` publishes every file older than 1
  day to the private releases before retention deletes it (e.g. `trades-20261012.jsonl` is in `data-20261015-dsheikh`),
  and fix 1 now exits 75 with a restore instruction; q0413 restores the smoke's worn files.*
- **O1 accept with amendment**: re-entry counts bind on the signable (touch-consistent) population a CH154 test would use;
  counts on all transactions reported only (stricter). **Part E sha changes.**
- **O4, O5, O6 (activity/imbalance by q0401's own arithmetic before any float32 cast), O8, O10: accept.** O3, O7
  informational; pre-register that B1 is expected to come out "uninformative".
- Low: §11 `pre` = ddc0249b vs commit de5c553a "pre c186fdcd -> 31656d5d"; the ledger records the full re-seal chain.
