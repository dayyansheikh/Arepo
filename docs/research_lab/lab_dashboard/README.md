# Lab dashboard registry

`registry.json` is the curated, plain-English list of experiments behind the private Lab page. `scripts/lab/lab_host.py`
reads it every 10 minutes and merges it with automatic numbers (queue, disk, tests run, hypotheses, live-test row counts).
Spec: `docs/lab/LAB_DASHBOARD_SPEC.md`.

## What is automatic, what is curated
| Part | Source |
|---|---|
| headline `tests_run`, `tests_over_time` | `docs/research_lab/trials.jsonl` through `battery2.count_line` (rule `battery2-count-v1`) |
| headline `hypotheses`, funnel "Ideas" | unique `CHnn` ids in `CREATIVE_HYPOTHESES_*.md` |
| headline `batches`, funnel "Designed" | `CREATIVE_BATCH_*.md` files; unique `CHnn` ids mentioned in them |
| funnel Screened..Confirmed | count of registry experiments that reached at least that stage |
| `jobs_done`, queue, infra | `run/queue/status.json`, `attempts.jsonl`, `df`, `/proc/meminfo`, collector and `oci-retry` logs |
| `live_tests[].collected` | line counts of the collector files (counts only) |
| `experiments`, `ml`, funnel help text, live-test dates | **this file (curated)** |

## Rules for editing (non-negotiable)
- Plain English, no jargon. 1-2 sentences in `plain`.
- Development results only, labelled "development (historical)" in `effect.note`. **Never** put interim or partial results of a
  live prospective test (E009, E010, E011, any SEALED-P) in this file. Live tests show counts and dates only.
- `stage` is the furthest funnel stage reached. `verdict` values: `not_detected` (below the screen's detectable size),
  `not_testable` (data or rarity), `replicated`, `advanced`, `failed_costs`, `pending`, or `null`. Keep them distinct.
- Every entry has a `sources` object: a key per claim (`verdict`, and `effect` when `effect` is set) holding a doc path plus
  section. Every number in `effect` or `ml` needs its source. If you cannot source a number, leave it out.
- Never invent `ml.feature_weights`. They are family-level ablation deltas from `HISTORICAL_ML_DEV.md` and `EXPERIMENT_LEDGER.md`
  until a SHAP run exists; replace them with real SHAP output and update `feature_weights_note` then.
- "Confirmed edge" stays at zero until a live test AND the cost check have both passed.
- `candidate: true` only for the 3-5 leading items shown as cards.

## How sessions keep it current
Whenever a ledger verdict changes (a new D/E result, a batch freeze, a smoke test, a seal, a queue job finishing that moves an
experiment forward), the session that writes the ledger entry also updates `registry.json` in the same commit: change `stage`,
`status`, `verdict`, `next`, `next_date` and `sources` of the affected entries, add new entries for new batches, and bump
`updated`. The autopilot prompt should include this step. Validate with
`pytest backend/tests/unit/test_lab_clients.py -k registry`. The host picks the file up on its next push; no deploy is needed
beyond the normal repo sync to `~/arepo`.
