# D116 freeze record

**Status: FROZEN 2026-10-10.** This record freezes the D116 integrated live validation. It is a separate file
because the repository denies edits to every `PHASE_03_*_PROTOCOL.md`, so the protocol text stays byte-identical to
the reviewed draft. Wherever the protocol says "DRAFT — NOT FROZEN", this record governs.

## Frozen artefacts (file sha256 at evaluator commit `8b32471`)
| Artefact | sha256 |
|---|---|
| `docs/implementation/PHASE_03_D116_INTEGRATED_VALIDATION_PROTOCOL.md` | `1b1b81bb124554191197ca280a0c8a7917dfd684b28f4e26681629b02a6fe7c9` |
| `backend/astrolabe/research_panel/d116_evaluator.py` (`d116-evaluator-v3`) | `772b984a83f7d984f9d127401d3fe38cd68fcb339bb828f88438176a29893ab9` |
| `backend/scripts/evaluate_d116.py` | `41eadf25bf1445de6e3d2bd53bc37592ec90cecb40b67b2109cca66ff7f1a4ad` |
| `backend/tests/unit/test_research_panel_d116_evaluator.py` (74 tests pass) | `4a27a4b63bbffe963644f2aea5f9863cb9e78e3903ca7750ae0a7baa05d56248` |
| Classification table (`TABLE_SHA256`) | `6c7f273e43d51de7850d656d48b5913a589ec40f4edcd745d876c6e04130cbc4` |

**Erratum:** the protocol text names the evaluator `d116-evaluator-v2`. The frozen evaluator is
`d116-evaluator-v3`, at the hash above. v3 changes only the version string and the third-review fixes:
- absolute, symlink-safe roots;
- production-parser `invalid` citations;
- socket frame and ordinal integrity.

The protocol's command block already uses the absolute panel path.

## Review trail
Three independent Opus `science-reviewer` passes:
1. Draft: REVISE, seven findings.
2. `bc97720`: REVISE, seven defects.
3. `913d50d`: REVISE, one live false-FAIL defect plus two minor ones.

All findings were fixed in `839f28b` and `8b32471`. The third reviewer stated that the protocol is freezable once those
fixes are made and the hashes recorded. The methodology rests on the user's decision recorded in D115 item 5 and is
not re-opened here.

## Launch preconditions (all required; any miss means do not launch)
1. Clean tracked tree. The launch commit contains this record and descends from `8afbdff`
   (`git merge-base --is-ancestor 8afbdff HEAD`). The artefact hashes above match at launch.
2. Free disk of at least 13,308,526,592 B **plus a 1 GiB margin**, measured by `df` immediately before launch.
   Disk on this machine is volatile (macOS update staging was observed to swing it by about 4 GB). The script's
   own preflight also enforces the reservation.
3. No other AREPO collection is running (no concurrent snapshot or book sweeps).
4. Panel name `fs2_panel_d116_integrated_1`. No root with that name or any derived name exists.
5. Single attempt. The evaluator is run once, with `--launch-commit <launch HEAD>`. No report, or any evaluator
   exception, means FAIL.

## Storage status at freeze
Free space was about 11 GiB, below precondition 2. The planned remedy is exact-byte transparent compression of
six non-protected directories with `backend/scripts/storage_compress_exact.py`. The protect-evidence hook gates
this until the user opens a storage session. External backup of `data-dumps/` is recommended first.
