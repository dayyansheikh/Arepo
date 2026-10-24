# Smoke failures of 2026-10-17: CB7 (q0140) and CB8-H (q0160) — diagnosis and v2 proposals

Status: **diagnosis done; v2 proposals need science-reviewer acceptance before any code or queue change.**
Written 2026-10-17 ~09:50Z by the autopilot coordinator. Both original smoke results are write-once and stay on record as
FAIL (`creative_batch7/smoke.json`, `creative_batch8/holders_smoke.json` on the host). No outcome, price, text or wallet
data was read for this diagnosis; every probe below is counts-only over ids, dates, volumes and OI fields.

Precedent: CB6 smoke FAIL (q0135) was a mis-specified smoke pool; v2 kept the thresholds, changed the pool and the seed,
was reviewed and passed (`CREATIVE_BATCH_6.md`, commits b067ac1, f3b9feb).

## 1. CB7 smoke q0140: FAIL because only 2 of 200 candidates were eligible

Result: (a) PASS (slug `geopolitics` resolves to 100265); (b) and (c) FAIL with `n_in_pool = 2`, `n_requested = 2`,
`n_nonempty = 0`. `smoke_verdict` fails (b) and (c) automatically when fewer than 20 markets are smoked.

Cause (`cb7_common.smoke_pool` / `run_smoke`, per `CREATIVE_BATCH_7.md` §CB7-F): 200 candidates are drawn in seed order
from the h1/h2/h3 exclusion samples and only then filtered to `end_at` in 2025 and lifetime volume ≥ $10,000. Counts from
the samples' own recorded fields (host, 2026-10-17):

| sample | ids | end_at in 2025 | end 2025 and volume ≥ 10k |
|---|---|---|---|
| h1_first | 500 | 0 | 0 |
| h2_main | 3,200 | 0 | 0 |
| h3_power | 10,000 | 573 | 205 |

205 of 13,700 ids (1.5 %) qualify, so a 200-id draw expects about 3. The smoke never tested the source: it is a pool
specification error, not a Data API failure (`n_failed_requests = 0`).

**v2 proposal (thresholds and criteria (a)-(c) unchanged):**
- Pool: every exclusion id whose sample row has `end_at` in 2025 and `volume` ≥ 10,000 (≈ 205), ranked by
  sha256(`arepo-cb7-smoke-v2`|id); looked up on Gamma by id (≤ 5 requests, same parse guard) and kept only if Gamma's
  `endDate` is in 2025, `volumeNum` ≥ 10,000 and a condition id exists (the original Gamma-side filter); first 20 in
  seed order are smoked. If fewer than 20 survive, the smoke FAILs as before (no further widening).
- New seed `arepo-cb7-smoke-v2`; smoke version `cb7-smoke-v2`; output `creative_batch7/smoke_v2.json` (write-once);
  the v1 file is never overwritten. q0142/q0143 require the v2 PASS under the same rules hash (or a new rules hash if
  the smoke constants live in the rules file; then the rules file is regenerated in its own commit and the
  fetchers pin it).
- New job id q0140b; T_seal 2026-10-22T00:00Z unchanged; q0142 (~2.4 h) still has ample time.

## 2. CB8-H holders smoke q0160: FAIL because the frame was empty (market OI is never populated)

Result: `frame_size = 0`, `n_requested = 0`, (a) and (b) FAIL, (g) paging FAIL (`deep_offset: no_market`).
`holders_frame` drop counts on the smoke's capture `20261017T063102Z_ae802eac`:
`open_interest_below_min` 280,068, `not_accepting_orders` 107, frame 0.

Cause: the frame requires sidecar `open_interest` ≥ 1,000, but the sidecar column is **blank in all 280,175 rows**.
Gamma `/markets` carries no market-level `openInterest` field at all (probe of 3 live markets, 2026-10-17); only
`/events` has `openInterest` (event-level; blank in 146,010 of 280,175 sidecar rows, ≥ 1,000 for 60,212 base-frame rows in
4,670 events). The design text (`CREATIVE_BATCH_8.md` criterion (e)) assumed a Gamma market `openInterest`. So the smoke
tested nothing about `/holders`.

Market OI is available from the Data API: `GET /oi?market=<cid1>,<cid2>,...` returned 60 of 60 values in one request
(2026-10-17 probe; repeated `market=` params return only one). Base frame (binary, open, accepting, not weather, not
Up/Down) on that capture: 273,201 markets, i.e. about 4,600 `/oi` requests at 60 per request (about 20 min at 4 rps)
per frame build.

**v2 proposal (all thresholds unchanged; only the OI source changes):**
- OI source: Data API `/oi`, batched 60 condition ids per request, fetched at frame-build time `t_f` (after the capture,
  before any `/holders` request; `t_f` recorded per market). Market OI ≥ 1,000 is evaluated on this value; the OI
  terciles and the concentration denominator `max(OI, Σ top-20)` use it too. A market whose `/oi` lookup fails after
  retries is dropped and counted (`oi_lookup_failed`); more than 2 % failed lookups fails the smoke and stops a day's
  snapshot (unavailable, not imputed).
- Option B (only if the reviewer prefers fewer requests): prefilter by event OI ≥ 1,000 (exact, since market OI ≤ event
  OI) plus `/oi` for every market whose event OI is blank; this saves only ~25 % of requests, so option A (all base
  markets) is recommended for simplicity and exactness.
- Criterion (e) records `/oi` value, event OI (when single-market) and `Σ top-20` ratios; the "units unverified" rule is
  unchanged.
- Rules file `seals/cb8_holders_rules.json` is regenerated (new rules hash) in its own commit after the code fix; new
  smoke version `cb8-holders-smoke-v2`, output `holders_smoke_v2.json` (write-once), new job id q0160b, new seed for the
  smoke pick. q0162/q0163 keep their 2026-10-21T04:00Z target and require the v2 PASS.
- The fix lands after the CB8 B-family implementer finishes (same files: `cb8_holders.py`, `run_cb8.py`).

## 3. Count of tests
Neither failure is an outcome test; no test count changes. Both v1 FAILs stay on record in the ledger as engineering
failures (pool/input specification), with these probes as the diagnosis.

## 4. Science-reviewer verdict (2026-10-17 ~10:05Z): both ACCEPT_WITH_CHANGES
Diagnoses confirmed (CB7 `smoke_pool` draws before filtering; CB8 sidecar `open_interest` maps Gamma market
`openInterest`, `ext_sidecar.py:33`, never populated). A v2 instead of "not run (source)" is justified by the CB6
precedent, as a recorded design change.

**CB7 required changes:** (1) the pool must also apply life ≥ 14 d and `close_epoch ≥ end − 7 d` (plus not weather / not
Up/Down / Yes-No labels) so the whole `[end − 14 d, end − 7 d)` window is inside the market's life (CB6 v1 lesson); a
zero-request count first (done: **33 ids**, 26 with recorded volume ≥ 10k); fewer than 20 → FAIL, no widening;
(2) no recorded-volume pre-filter, volume ≥ 10k stays on Gamma as v1; (3) new `seals/cb7_text_geo_rules_v2.json`
(v1 untouched), `run_smoke` hashed, test that v2 differs from v1 only in the smoke block, `smoke_ok`/`--require-smoke`
on v2; (4) disclose v1's 0/2, overlap of the first 20 with v1/CB6 smoke markets; a v2 FAIL is final, `T_seal` unchanged,
S1/G1 then "not run (smoke FAIL)", counted.

**CB8-H required changes (option A, not B):** (5) option B is not exact (event OI is capture-time, `/oi` is `t_f`);
(6) `t_f` strictly before the first `/holders` request, stored per batch and asserted; disclose the mixed clocks and
that `c` uses OI at `t_f`; rewrite every "the capture's OI" phrase (rules text, stored fields, "cut points from that
capture" → "from that day's `/oi` frame"); (7) separate `oi_lookup_failed` / `oi_absent` / `oi_nonnumeric`, never imputed;
assert values returned = ids sent per batch; network errors → NotNow (write nothing); the 2 % stop rule is a new
threshold fixed now with a written reason, a stopped day recorded "missed (oi_source)"; (8) criterion (e) also records
`/oi` vs event OI for single-market events; threshold units disclosed as unverified unless they agree; threshold
unchanged; (9) new `cb8_holders_rules_v2.json` (v1 kept), realised frame and stratum sizes disclosed against 1,500 + 300.

**2 % reason (recorded now, before any v2 run):** the same tolerance as the CB6/CB7 exclusion-key rule
(`--max-unverified-key-share 0.02`): small enough that unavailable OI cannot reshape a 1,800-market daily sample by more
than ~36 markets, large enough not to stop a day for a handful of transient misses.
