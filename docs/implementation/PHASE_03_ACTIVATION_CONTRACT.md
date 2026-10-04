# Phase 3 — actual selection consumption and schedule (D052)

Activation is an immutable read/schedule record, not an enabled collector or research origin.
It consumes one D050 fresh selection under the current exact build, keeps synthetic source
provenance synthetic, and preserves declaration/selection/source journals unchanged.

- One deterministic sibling `fs2_activation_…` per declaration; exclusive creation owns it.
  Never overwrite, resume, reschedule or accept caller-selected clocks/seeds/assignments.
- Before reading selection values, reserve the entire D048/D051 panel allocation plus 32 MiB
  activation output and 128 KiB metadata for every reserved origin and target attempt. Keep
  the 2 GiB free reserve. This conservatively reserves selection space again; no overlap or
  already-small-response discount is used. Future workers must enforce their metadata quotas.
- Freeze build, policy, full reservation and declaration hash before an actual complete
  selection read. Reverify every original source/projection through `read_selection`, then
  match selected row-qualified evidence against the retained projection manifest. Preserve
  exact role weights, selected token/outcome, condition and mapping/rule version. Do not
  duplicate an origin merely because a market has multiple roles.
- Record actual read start/completion and post-fsync acknowledgement; enforce frame interval
  and age both at completion and save. Reject changed declaration, selection or source closure.
  Retain failed/torn attempts, including a save that finishes after freshness expires.
- Freeze a **two-second lead**, then derive the first scheduled boundary from the actual
  activation-facts acknowledgement. Later boundaries add declared cadence. Include the lead
  in the runtime duration reservation. This is a development timing rule, not proven live
  latency. Each intent ID binds panel declaration, cycle, market and token. Up to 1,024 actual
  scheduled slots inherit the declaration's ceiling; unused trigger/control capacity stays
  reserved, never treated as measured controls.
- The writer returns its already-verified facts after save; it does not consume the new lead
  interval by replaying the entire population again. Independent `read_activation` performs
  full source/selection/identity replay at the original clocks, with no current free-space or
  age requirement. Recovery never advances an expired schedule. A later worker must enforce
  due/delay gates before requests and must not trust an externally supplied summary.
- Enforce 16 MiB per artefact, 32 MiB whole output, 64 KiB failure allowance and 600-second
  operation-boundary checks. No hard process-cancellation guarantee is claimed.

Tests cover complete actual read/identity/weight closure; additional origin/target capacity;
exclusive concurrent ownership; caller override refusal; tampered source/declaration/weights/
identity/profile/schedule; actual save delay and stale failure preservation; expired schedule
replay; changed builds; source clocks, artefact/storage/time boundaries. No network or SQL.

Next: actual origin intents and guarded source→read→compute→origin work from this schedule,
then frozen-identity target adaptation. Apply every source, computation and metadata quota.
Collection, SQL/origin admission and accepted-panel flags remain false in this milestone.
