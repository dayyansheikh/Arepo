# D120 freeze record

**Status: FROZEN 2026-10-11.** This record freezes the D120 live validation of screen-then-activate
pairing. The protocol is `docs/implementation/d120/D120_PAIRING_PROTOCOL.md`; as for D118, its
text stays byte-identical to the reviewed draft (its header still reads "DRAFT — NOT FROZEN"), and
**this record governs**. The sha256 values below govern.

Freeze commit: `04e71eab5f160d7299ba28c3655fbb66e86db742`

## Frozen design
- Population: temporal ∩ original-frame Gamma liquidity ≥ 1000 (`LIQUIDITY_POPULATION`); category
  policy `all` (declared parameter, no exclusion).
- Strata: time × `fee:<fee_category>` (frozen map `fs2-fee-category-map-v1`) × time-to-close ×
  probability band × liquidity band; drawable only with ≥ 8 dependence groups.
- Dependence groups (attribute, never a stratum field): `fs2-dependence-groups-v2` — union of every
  event id, every `parentEventId`, every series slug, `negRiskMarketID` and the slug-token table
  `fs2-underlying-slug-tokens-v1`, over the complete frame.
- Shape **6 × 12**: 6 drawable strata, 12 screened groups each with a shared claim set (72 screened
  slots), one pair per stratum (≤ 12 origin slots), scheduled arm 0, `activate_screened = False`.
  6 × 16 was not frozen (dry-run assessment age 85.3 s > 80 s).
- Roles fixed at screening (first triggered / first untriggered by seeded hash); binding read,
  recomputed trigger and window for activated members only; state disagreement descriptive only.
- Unchanged D118/D116 policies: `SnapshotTriggerPolicy(1,3,60000)`, `ScreeningPolicy(120,120)`,
  the owned window policy, 60 s horizon ±15 s, runtime concurrency 8.
- Gates and decision (`d120-evaluator-v1`): E0 identity, E1 frozen values, E2 selection and
  group-disjoint screening, E3 screening, E4 binding/window/history, E5 exact role-draw replay and
  no shared dependence group among activated members, E6/E7 origins and targets, E8 audit, E9
  accounting. FAIL → INCONCLUSIVE (< 4 strata with a trigger, or screening coverage < 80%) → PASS
  (fill ≥ 0.8 with ≥ 4 triggers and ≥ 3 group-disjoint complete pairs) →
  PASS WITH LIMITATION `control_scarcity` (fill < 0.8) → PASS WITH LIMITATION
  `pair_member_unobserved_data_reason` (≥ 1 incomplete member, every cause DATA) → FAIL. D116
  classification table sha256 `6c7f273e43d51de7850d656d48b5913a589ec40f4edcd745d876c6e04130cbc4`.

## Review trail
- Opus 5.5 specialist design: `d120/D120_SPECIALIST_DESIGN.md`.
- Fable 5.1 review, proceed with changes, every item adopted: `d120/D120_FABLE_REVIEW.md`.
- Implementation, pinned estimates and dry run: `ed51e6a`, `8b2cfb0`, `3edba22`, `e79111a`.
- Pre-freeze `science-reviewer`: ACCEPT_WITH_CHANGES (seven items); fixed in `da81c9d`
  (`parentEventId` unioned, data-reason branch) and `3f0d25f` (criteria disclosure, plan size,
  audit time, wording, disk).
- Final `science-reviewer`: **ACCEPT** ("freeze may proceed").
- Dependence context: `docs/research_lab/DEPENDENCE_CLUSTERING_ANALYSIS.md` (series chaining,
  league-day dependence); group-disjoint pairs are not independent and Phase 4 clusters by run.

## Plan-size note (reviewer)
At full size the D120 `selection_plan.json` is about 13.7 MB against the 16 MiB artefact limit:
headroom for roughly 19% growth in the zero-inclusion exclusion list. A breach is refused safely by
the selection writer before any draw (no seed is consumed by a sample, no source request is made);
it would be an engineering stop, never a truncation. Offline rebuild measurement: 14,111,195 B
(protocol section 5).

## Frozen artefacts (file sha256 at the freeze commit)
| Artefact | sha256 |
|---|---|
| `backend/astrolabe/research_panel/activation.py` | `387d363f07b755db7c82920944d917e149e5be52748431f5a44f17a28762e554` |
| `backend/astrolabe/research_panel/concurrent_runtime.py` | `d35b94971a7e3c94f99029cad07e748592806681e8d1c5339ea898335b1cdb3b` |
| `backend/astrolabe/research_panel/d116_evaluator.py` | `772b984a83f7d984f9d127401d3fe38cd68fcb339bb828f88438176a29893ab9` |
| `backend/astrolabe/research_panel/d120_evaluator.py` | `bba626fddfe53d36d74b74eb67ec590592644953fe00fc991b0c45c83996c90c` |
| `backend/astrolabe/research_panel/due_worker.py` | `7d976fb30be9c0509242fe7c9afd0c28cd0a86d95d7b9e40582ca80586889219` |
| `backend/astrolabe/research_panel/origin_worker.py` | `6278d947746667f23a3e1dc0e521f83a5edf064461e55c463c998098d0675b84` |
| `backend/astrolabe/research_panel/original_reader.py` | `be23f64cee5812df4d9c03dd0923cfccf51679622e18359cceed474f6e14b370` |
| `backend/astrolabe/research_panel/owned_windows.py` | `7787c2ffe757d9c353d4f2b2e87c06a6798abc9dffe4511a35b83f6379e1c72d` |
| `backend/astrolabe/research_panel/pairing.py` | `9459b41a2285a7d3edfd2d2b5eb9ea98be08363c8fe962b770c55e9941f7abc1` |
| `backend/astrolabe/research_panel/pairing_declaration.py` | `e61d3c323166cd4bcd87b16ec1f664234777f4336b87c6c94ce1e7e3c79640b1` |
| `backend/astrolabe/research_panel/pairing_selection.py` | `3d1b70fd9c2d933bb97521cf5b947db198abf2b7fef80d794899c7e11748ddc4` |
| `backend/astrolabe/research_panel/pairing_worker.py` | `6d0a5303613b71a858dea76da7cde72417b3cb41a3b78fb3c561a025471e5942` |
| `backend/astrolabe/research_panel/panel_declaration.py` | `9ab71ae0c0411d5941c99ec1270067bd608dc63a76ceffc956908055fc75ba4a` |
| `backend/astrolabe/research_panel/panel_selection.py` | `ecd2ddd5af58d893f3d123a2715161cd693298e93990a0100558175d2fbd9f3b` |
| `backend/astrolabe/research_panel/runtime.py` | `17ba240b17b38fe31e2b498ed76cc1b9f596e238bda64a62045723e748717351` |
| `backend/astrolabe/research_panel/sampling.py` | `e9058045403705e8f3e76567bbd877267d0b5d5b49995d93d8deeb50b4d00a7c` |
| `backend/astrolabe/research_panel/screening.py` | `1143051093bf714d35b0ee8838b69a2968bd531fdad894c4006347c8926e4a19` |
| `backend/astrolabe/research_panel/screening_worker.py` | `dec77b51760872c37248f5143a1464dffea2883bb76e734a0ef941faaaf0a84f` |
| `backend/astrolabe/research_panel/selection.py` | `ee24eb1bfa844d1661f530fea9d376b68c6af5c9feb3be0b2dccfcf1c69f256f` |
| `backend/scripts/d120_design_estimates.py` | `8933d3ce80eeb837336c1c5635a73153d8e794e96091250b5c7bc78dcb54d42e` |
| `backend/scripts/d120_launch.py` | `0eab3d11432cba704111c358b7923e6e65e459b2485abc2b9a6dcc4a9763242a` |
| `backend/scripts/d120_window_dry_run.py` | `c9d8ed11e20a6df4c071de8fa9499d10c27f8de1d4b7a46616343277b4437933` |
| `backend/scripts/evaluate_d120.py` | `57e1bf7f477757bae65b911a4b235ab66a5462299a88e26faeaa705145646206` |
| `backend/tests/unit/test_d120_launch.py` | `2ff42153db0b0b0388e94c5c94f73c4cc1b6adf0d8db0c3f7e865a54fbefdc5c` |
| `backend/tests/unit/test_research_panel_d120_pairing.py` | `4708446d015c29269617521b3ceb153b1d1b27d5d956f167e19627636af965d8` |
| `backend/tests/unit/test_research_panel_pairing.py` | `cc337c6ed9d8b036f7355e04c78a4e2ac4e33612edd07e5be4845bbd3f831451` |
| `docs/implementation/d120/D120_DESIGN_ESTIMATES.json` | `6fac7bd9e2851e27a974792691497486c9131f60971042aeac8989a57b869fee` |
| `docs/implementation/d120/D120_DRY_RUN.json` | `f35b7f68a6ac640191192a545e2a20d1a77fcc7791a0374be811bef644741295` |
| `docs/implementation/d120/D120_PAIRING_PROTOCOL.md` | `fe5882f757ecd7e54e479ac6c84fbcc7df6b7713d56dfeab945047299af8b9f0` |

## Launch preconditions (enforced by `backend/scripts/d120_launch.py`)
- Every hash above matches; a missing record, missing or extra row, or unfilled hash fails closed.
- `git diff --quiet 04e71eab5f160d7299ba28c3655fbb66e86db742 HEAD -- backend/astrolabe
  backend/scripts/d120_launch.py backend/scripts/evaluate_d120.py` succeeds, and there are no
  untracked or modified files under `backend/astrolabe` (including `research_lab/`): **no commit
  touching `backend/astrolabe` may land between this freeze and the launch.**
- `8afbdff` is an ancestor of the launch commit; the tracked tree is clean.
- Launch only between HH:46 of an even UTC hour and HH:49 of the next odd hour; no
  `collect_universe_snapshot`, `sweep_books`, `sample_trades` or `run_forecast` process.
- Free disk ≥ 15,382,085,632 B (reservation 14,308,343,808 B + 1 GiB margin).
- No `fs2_panel_d120_pairing_1` root, derived root or `fs2_d120_pairing_1_*` wrapper file exists.
- Isolated SQLite URL, `AUTO_MIGRATE=false`, `DIGEST_EMAIL_ENABLED=false`, `caffeinate -is`.
- One attempt only; the protocol's single `python` block runs verbatim (blocked-cursor frame abort
  with one bounded frame-only re-run is part of it). Evaluate once with `evaluate_d120.py`.
