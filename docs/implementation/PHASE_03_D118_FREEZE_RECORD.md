# D118 freeze record

**Status: FROZEN 2026-10-11.** This record freezes the D118 live control-pairing validation (4 strata × 3 members,
liquidity ≥ $1000 temporal population, runtime concurrency 8, all D116 gates and classification table). The
protocol lives at `docs/implementation/d118/D118_CONTROL_PAIRING_PROTOCOL.md`, because a deny rule blocks
`PHASE_03_*_PROTOCOL.md`. The sha256 values below govern.

Freeze commit: `dad3c0f63dca47b6edabc0f019afd04093ba2bc7`

## Review trail
- Opus 5.5 max specialist diagnosis: `d118/D118_SPECIALIST_DIAGNOSIS.md`.
- Fable 5.1 review: proceed with changes (`d118/D118_FABLE_REVIEW.md`).
- 16-member design aborted before freeze by its dry run (43.09 s > 40 s). 12-member dry runs gave 36.26 s and 36.14 s.
- Opus high review of revision 2: REVISE (minor), with seven items. All were fixed in `837483e`, `68fae32` and `dad3c0f`.
- Opus high verification: **ACCEPT (freezable)**. The two optional low items (launch window drift, untracked code) are also fixed in `dad3c0f`.

## Frozen artefacts (file sha256 at the freeze commit)
| Artefact | sha256 |
|---|---|
| `backend/astrolabe/research_panel/d116_evaluator.py` | `772b984a83f7d984f9d127401d3fe38cd68fcb339bb828f88438176a29893ab9` |
| `backend/astrolabe/research_panel/d118_evaluator.py` | `1647a743b11f6b9f206374faac44a11ab6be8588175d75b579b7e55fc1795b7b` |
| `backend/astrolabe/research_panel/panel_declaration.py` | `9ab71ae0c0411d5941c99ec1270067bd608dc63a76ceffc956908055fc75ba4a` |
| `backend/astrolabe/research_panel/panel_selection.py` | `ecd2ddd5af58d893f3d123a2715161cd693298e93990a0100558175d2fbd9f3b` |
| `backend/scripts/d118_launch.py` | `e017ebc5fd04593ccfcdb66c5319a268e49a196d6c4a003b6708d58c16a3e5e8` |
| `backend/scripts/evaluate_d118.py` | `e799450758a4c5f8a0f97e1472cb484296cba3c80c1256b3853430f5422ce450` |
| `backend/tests/unit/test_d118_launch.py` | `cef36d3aa4e85467cb19caac0c1f3a4c8630ab3f231f8042d5ea87487fd82c11` |
| `backend/tests/unit/test_research_panel_d118_evaluator.py` | `0ff3c7766b9228cd62dc105e31051eef3acaaf8ea0268552c4a0b091bcc9c22b` |
| `backend/tests/unit/test_research_panel_liquidity_population.py` | `f4feecdd606a8a3a951a9ef0e914a0ffc3979b72b0804f44a62c1b1fcdada41b` |
| `docs/implementation/d118/D118_CONTROL_PAIRING_PROTOCOL.md` | `4278d766b80a2dc0d4248031dae159101546bafa87cc0c599dfc6af8669da12a` |

## Launch preconditions (enforced by `backend/scripts/d118_launch.py`)
- The frozen hashes match.
- There has been no code change since the freeze commit, and there are no untracked files under `backend/astrolabe`.
- `8afbdff` is an ancestor of the launch commit.
- The tracked tree is clean.
- Launch happens between HH:46 of an even UTC hour and HH:49 of the following odd hour.
- No collector process is running.
- Free disk is at least the reservation plus 1 GiB.
- The run uses an isolated SQLite database, with AUTO_MIGRATE=false, email off and caffeinate.
- One attempt only.
