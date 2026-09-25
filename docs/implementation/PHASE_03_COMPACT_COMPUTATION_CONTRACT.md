# Phase 3 — explicit compact computation reservation (D051)

Implemented and self-reviewed; 20 focused tests and 1,105 full backend tests passed. Current D045 defaults reserve 64 MiB per
computation, including a 32 MiB child source-read journal. The saved complete frame has 107
scheduled strata; one origin and one target per assignment would reserve more storage than
is currently available. Measured-small responses do not themselves reduce enforced quotas.

The separately named `compact-v1` profile uses child read output 4 MiB and per-artefact
2 MiB; parent computation output 8 MiB, including that child, and per-artefact 2 MiB. Preserve
all existing source/request/raw limits, deadlines, failure reserves, free-space reserves,
exact numerics and source/build verification. Default APIs and schemas remain unchanged.
Explicit compact records use new schema versions and exact policy/profile binding. Unknown
profiles, mixed parent/child profiles and rehashed quota changes must fail replay.

Every managed write checks the chosen quota before writing. Reserve the complete chosen
child bound before invoking it. A source/read/compute result that exceeds the compact limit
fails and retains raw and partial evidence; no truncation, retry with a larger profile inside
the same run, or smaller-universe fallback. Readers enforce the historical profile, without
requiring today's disk capacity. Original-code recovery continues to preserve old records.

Panel declarations may explicitly select the compact profile in a new declaration version.
Reserve that exact computation cost for every role and target attempt before selection;
the default reservation remains unchanged. Fresh selection binds the declared profile.
Collector implementation must actually pass it to the computation writer; collection stays
disabled until origin/target integration verifies that linkage. This milestone does not
authorize a new frame or accepted live panel.

Required tests: default compatibility, full guarded synthetic source→read→computation chain,
exact frozen profiles and child linkage, low-disk preflight, actual byte/artefact failures
before excess writes, partial evidence preservation, unknown/profile tampering, original
recovery and exact panel reservation. Full isolated regression and review before commit.
