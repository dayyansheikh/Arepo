# CB7 h_geo fix re-check, 2026-10-28 (science-reviewer, read-only)

Branch `fix/cb7-hgeo` @ `836dc3f9` against `chore/arepo-claude-setup`; ruling `reviews/CB7_HGEO_RULING_2026-10-28.md`.

**Verdict: ACCEPT_WITH_FIXES.** The design is right; Reading 13a changes no threshold, window, mid band or gate (`cb7_census.py:48-49` untouched). Two code paths conflicted with the ruling and had to be fixed before q0147t is promoted.

## Verified
- Capture pins `seals/cb7_hgeo_window_captures.sha256`: same blob (`a23693b5`) on both branches; 144 pins, 36 captures, 4 files each.
- FEE_FIRST drop exact (`history_topics.py:46-47`, `:13-14`); `pairing.fee_category` never returns "geopolitics" (`pairing.py:55-63`).
- Allow-list applied at parse time (`cb7_hgeo_text.py:196-201`); `Limiter` writes nothing; a test plants outcome, price and volume values and checks the bytes on disk. No column records which pass (open/closed) found a market.
- Write-once census: `measure_h_geo` refuses before writing (`cb7_census.py:664` before `:677`); guard `:653` unchanged.
- 53 tests pass; fixtures use producible values. q0147t net lane 400 MB, no deps; q0147c cpu lane, deps q0147t + q0147b's, same argv as q0147b.

## Required fixes (ranked)
1. High: no text at all still produced a "measured" h_geo (variant B binding with `status: ok`, `cb7_census.py:486-497`). Fix: `text_available == 0` -> `unavailable`, `h_geo_binding: None`; state it in Reading 13a.
2. High: a 4xx on a 50-id request marked all 50 unavailable and skipped the closed pass (`cb7_hgeo_text.py:220-224`, `:210`). Fix: retry each id alone in both passes; `unavailable/http_<n>` only for a single-id 4xx; refuse if the session got no 200 at all.
3. Medium: unchecked column reads (`:145-152`). Refuse on missing required columns.
4. Medium: the census must refuse unless the text-table ids equal the candidate set and the manifest `window` / `mid_band` equal `H_GEO_WINDOW` / `H_GEO_MID` (`load_text_table`, `:343-361`).
5. Low: the "cannot happen" comment (`:188`) is wrong; report the candidate-and-FEE_FIRST-elsewhere count in both the text job and the census.
6. Low: record the 50 GiB guard in the Ops note (`CREATIVE_BATCH_7.md:1139`), as q0146.
7. Tests for 1-4.

## Answers to the open questions
1. No text at all: `unavailable`, not a refusal (a refusal aborts S and X). G1 runs but cannot advance.
2. First row per market per capture: keep (declared in Reading 13 before any spread). Before q0147t runs, report markets with more than one row in a capture; if a first row can be the NO token, that needs a ruling, not a quiet change.
3. Gamma 4xx: unavailable only for a single-id reply; retry a batch id by id.
4. Text-table pin: acceptable (manifest sha256 bound to the capture pin file's sha; `census.json` records `text_table_sha256`). After q0147t and before q0147c is promoted, write the manifest sha256 and text sha256 into q0147c's notes and the ledger.
5. Census refuses if in-window capture directories differ from the pinned set: correct; a lost capture needs a new ruling, never a fallback spread.

## Could not verify
Host contents and pin matches; one row per market vs per token and token order; Gamma behaviour for repeated `id` and closed markets; host retention; that no h_geo spread has been looked at (the code computes none before q0147c).

## Applied (experiments autopilot, 2026-10-28)
Fixes 1-7 in `0f6f031c` (172 passed, 1 skipped; pin test passes; ruff clean). Implementer finding on question 2: in this code `rows.csv.gz` has one market-level Gamma row per market with `best_bid`/`best_ask` as the YES quote and no `token_id`; repeated rows are repeat receipts. The first-row report (market-captures, markets with > 1 row, token check if a `token_id` column exists) is added to the candidates report and the census; confirm on the host. q0147c held in `drafts/` until the q0147t pins are recorded.
Host check (2026-10-28): `rows.csv.gz` header has no `token_id` column (market-level rows; `best_bid`/`best_ask` are the YES quote; `clob_token_id_0` present).
