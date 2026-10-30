# CB8-B series-key ruling (science-reviewer, 2026-10-23, read-only)
`evidence_role: review` | Filed verbatim by the orchestrator. Nothing counted.

**Verdict: VARIANT_ALLOWED_WITH_CONDITIONS**

**Basis.**
- The design contradicts itself. It defines B as the daily crypto Up/Down population: an 825-market probe at `CREATIVE_BATCH_8.md:452-455`, and "any h1/h2 ids are dropped by key" at `:104`. The series key at `:139` then removes that population wholesale: 665 of 783 dropped by series key (ledger 4294).
- The series key adds no protection against reuse. Previously seen markets are caught by market id (118 dropped) and by event and neg-risk ids. A series id only links separate daily markets, each with its own outcome.
- q0165 read only ids, question and rule text, keys and counts. The frame holds 0 rows and no prices; outcomes went only to a guarded partial (`cb8_updown.py:919`), which was deleted at finalize (`:1038`). So no price or outcome informs this change. It does touch the rule at `:189` ("no rule revised after any B read"), so it must be declared as a dated amendment, not slipped in as an operations fix.
- The 118 id matches show that earlier pooled samples took in some Up/Down markets: CB1 weighted them ×0.25 (`CREATIVE_BATCH_1.md:914`). Those analyses were pooled and never tested terminal-minute asks. The 665 other markets are separate market-days. Their only link to the 118 is same-day correlation across assets, which the day-cluster way and the day-unit tail gate already handle.
- The SCREEN/HOLDOUT split is a seeded week coin fixed in `cb8_rules.json` (`:124`) and does not depend on the population, so it stays valid. The HOLDOUT seal (`:158-160`) is unaffected because no books exist yet.

**Conditions.**
1. Write a dated amendment in CB8 §1.3 and a new data-rules version (`cb8_rules_v3.json`). For B only, the series key is not applied. Market-id, event-id and neg-risk keys stay. W and H are unchanged. The amendment needs a `science-reviewer` pass before any job runs.
2. Use new job ids (q0165b, then q0166b) and new run directories. q0165 and q0166 stay recorded as "frame empty (series overlap); operational, nothing counted". Do not open, reuse or move any q0165 file. q0165b fetches the Gamma frame again. It may reuse the Binance archives only if their zip sha256 values match q0165's recorded `archives` meta.
3. The q0166b seal-time drops (`:149-152`) use the same key set as condition 1: id, event and neg-risk, without series. They re-read every seal committed by then, including CB9-CB13.
4. q0165b reports the 118 id drops by source pin (h1/h2/h3, h5, CB5, C1, other seals) and the number of distinct days they cover. It also gives a binding-free, descriptive B1 sensitivity that leaves out every day on which an id-dropped Up/Down market settled.
5. Every other part of B stays exactly as frozen: regexes, checkpoints, z rule, cap, gates GB and the 90% coverage audit, MDE, placebos, the day-cluster way, and the Erratum E1 tail-gate margins. `seals/cb8_b_analysis_rules.json` changes only where `data_rules_sha256` must point at v3. Re-freeze `model_specs/cb8_v1.json` with that hash and nothing else.
6. Multiplicity: B1 still counts once in battery2. k1 = 3 and the Stage-2 Holm k ≤ 3 are unchanged. If q0165b is also empty, or GB or the audit fails, B1 is "not testable", counted once (p = 1). There is no further variant.
7. Any B1 result carries this disclosure: "population admitted by a post-count amendment waiving the series key; no price or outcome read before the amendment". The evidence ceiling stays `exploratory_historical` (L1, or L2 at Stage 2).

**q0182.**
Run it exactly as pre-declared (ledger 3730-3731), with the empty q0165 frame pinned. Record the pin as vacuous. Do not re-pin to q0165b and do not wait for it. This is safe because CB9 is disjoint from B by definition: K/D exclude crypto Up/Down (`CREATIVE_BATCH_9.md:636`) and P is Pyth equity Up/Down, a different series and regex. Any committed q0166b HOLDOUT seal reaches CB9 through the q0187 seal-time drops.
Heads-up, not a ruling: CB9-P carries the same series-key risk at q0183. If needed, a counts-only key-overlap check should be declared before q0183 runs.

**Not verified.**
- Which pins the 118 ids come from. The run data is on the Oracle host; nothing is local beyond `h3_power`.
- That nobody read `frame_partial_guarded.jsonl.gz` before it was unlinked.
- The ledger says `holdout/` does not exist, but `finalize_frame` creates it (`cb8_updown.py:1021`). The exact paths need checking on the host.
- The gap between the 825 probe markets and the 783 candidates.
