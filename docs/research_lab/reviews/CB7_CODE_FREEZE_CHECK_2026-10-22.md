# CB7 code-against-design freeze check: q0146 (xv-prints) and q0147 (census), 2026-10-22 ~18:00Z

`evidence_role: none`. Reviewer: `science-reviewer` (independent, read-only; saved by the orchestrator, condensed).
Object: d47d0031 (feat/cb7-code) against `CREATIVE_BATCH_7.md` (§1.3-1.4, §2.2, §2.7, §2.8, §CB7-S/G/X, §5.1-5.2, §9).

**Verdicts:** q0146 **GO_WITH_CONDITIONS** (items 1-2). q0147 **FIXES_REQUIRED** (items 3-8; item 9 scheduling).

## Implementer readings
1 ACCEPT (no fall-back to an older candle; record in §10 before the census). 2 ACCEPT ([s-3600, s-600] matches
cross_venue POINT_LAG_S / MAX_AGE_PM_S; causal). 3 ACCEPT (merged windows lower the count: conservative). 4 ACCEPT.
5 ACCEPT. 6 ACCEPT (10th page full = capped; conservative). 7 ACCEPT (no failure-share threshold declared; report failed
and capped days by sports / non-sports). 8 ACCEPT (stricter). 9 ACCEPT. 10 ACCEPT (conservative). 11 ACCEPT (also report
sqrt(mean m(1-m)) over S1, secondary). 12 ACCEPT, not a relaxation (§CB7-G "no match -> its own cluster"; note the theme
gate is near-automatic; GG event clusters as merged events is stricter). 13 ACCEPT with items 6 and 9 (fee_category-only
rule disclosed as narrower than §2.1; max(pooled, per-market median) declared binding). 14 REJECT (item 5).
Declaration-guard substitution REJECTED (item 4). q0146 regex: agree (item 2).

## Clean
No outcome, print-mark or target read in S/G (gzip spy test); field-restricted reads; causal timestamps; gates GS/GG/GX
and Z = 2.33 + 0.84 equal §2.7; seal verification (copy sha vs host, listing hash, ACCESS_LOG; rules v2 05bf365c…);
capped/failed days stay missing.

## Must-fix
1. (q0146, high) Silent truncation if the server caps page size: on the first short page of >= 100 rows, probe
   offset=len(page); if rows return, refuse. Unit test.
2. (q0146) Extend `until_log_regex` to stop on `disk_budget` and `refused`.
3. (q0147, high) Write-once loophole: refuse `--out` outside `cb7_dir` or when any `census*.json` exists there.
4. (q0147) Declaration guard (§5.2): write the sha256 of the cb7_xv definitions block, cb7_census.py and the gate dicts
   into census.json (re-checked at the CB7 freeze and q0150); unit test pinning the constants to the design numbers.
5. (q0147) Keep not-run states distinct (`not_run_deadline`, `disjointness_unverified`, `source_unverified`, committed
   NOT_RUN); unverified/source = "not testable", not "not run".
6. (q0147) h_geo guards: skip and count captures whose sidecar_status is not complete; refuse if no complete captures or
   no geopolitics ids at all (misconfiguration); "unavailable" only when ids exist but no quote passes.
7. (q0147) Move-event grid: iterate every minute end between first and last candle (design), or prove density with a
   test plus a census gap count.
8. (q0147) Sort `kc`/`ps` by timestamp (or assert monotone) before `searchsorted`.
9. (q0147, scheduling) Promote at or after 2026-10-24T01:00Z (48 tempfails x 30 min would fail it otherwise), and before
   host rotation removes the 10-22..10-25 captures (check on the host at promotion).

## Should
Manifest rules_sha256 = verify_rules result; X readiness checked before S/G reads (no ACCESS_LOG entries on tempfail);
count S prints with a usable mark at s+3600 (existence only, no value, gate unchanged); note the 12.5 -> 40 GiB headroom
ops change in §2.8.

## Not verified
Data API limit=1000 honoured / max offset (if < 9000, busy days fail rather than cap); Kalshi candle density; the
"geopolitics" fee_category string in live sidecars; load_c1 memory vs mem_mb 600; tests.
