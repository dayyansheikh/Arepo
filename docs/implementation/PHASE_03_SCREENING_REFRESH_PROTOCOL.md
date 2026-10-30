# D078 — prospective screening after the identity-policy correction

Freeze this design before reading or drawing from the D077 refreshed frame. Do not execute
until the protocol is committed, draft PR updated and D077 has ended successfully with an
exhausted-consistent frame. Use D077's recorded implementation commit and generated root;
no other frame or replacement attempt may be substituted automatically.

The population is exactly the complete refreshed Gamma interval, with all unknown fields,
source exclusions and category missingness retained. It is not an atomic market snapshot.
Use the same D075 two-stage sampling counts and numerical rule: uniformly four strata,
two scheduled members each, no more than eight screens/sixteen requests, threshold absolute
snapshot imbalance1/3, one conditional control per positive where its stratum permits.
Generate a new durable seed before reading values. Never choose a new draw because of the
observed pool, unavailable books, changed identities, closure or failed requests.

PanelProtocol and source/freshness bounds are unchanged from D075:
scheduled_slots8, triggered_slots8, controls_per_trigger1, cycles1, target_attempts1,
scheduled_per_stratum2, triggered_per_stratum2, cadence_seconds120,
max_origin_delay_seconds60, max_origin_save_seconds5, horizon_seconds60, tolerance_seconds5,
max_frame_age_seconds604800, max_frame_interval_seconds600, max_quote_age_seconds60,
max_identity_age_seconds180, source_response_bytes65536, source_run_retained_bytes1048576;
strata_limit4, storage_profile compact-v1. ScreeningPolicy(120,120), concurrency4,
SnapshotTriggerPolicy(1,3,60000). If frame interval exceeds600s, stop this design without
extending its limit after inspection. Reserve complete screening/source/future-runtime/
recovery cost plus2GiB before declaration; existing allocation and runtime checks apply.

Only protocol change: call run_public_screening with explicit
identity_policy='fs2-gamma-identity-comparison-v1'. Worker v3 and screening v2 bind it before
requests. Exact core equality can coexist with unavailable current event membership.
No old event ID is filled into a current observation; no economic independence is inferred.
Every other identity change and unavailable mapping remains rejected. Full original-code
screening recovery still runs. All inputs, positive/negative/unavailable states, weights,
missing-control counts, raw bytes, source clocks and recovery costs must be preserved.

Exclusive panel root: data-dumps/fs2_panel_screening_refresh_20261003_1. Selection and worker
use their deterministic sibling paths. Use exclusive launch/result logs. The implementation
commit must match the actual loaded code before requests. No injected transport, credentials,
retry, replacement source, activation, origin, SQL, production scan or Phase4 work.

This measurement tests the correction on new public observations. It does not revise D075,
and does not satisfy the full Phase3 origin/window/target pilot. Preserve one-sided control
pools and failed attempts without retuning. Before a live pilot, integrate the new identity
semantics explicitly into origin/target contracts and move full audit recovery off its
critical observation path without weakening causality or freshness checks.

## Frozen execution script

Execute once from the repository with PYTHONPATH=backend and isolated SQLite/email-disabled environment, after the frame result is accepted. Save exclusive stdout/stderr logs.

```python
import asyncio,json,shutil,subprocess,time
from pathlib import Path
from astrolabe.feature_store.capture import _clock
from astrolabe.research_panel.panel_declaration import PanelProtocol,declare_panel,reservation
from astrolabe.research_panel.panel_selection import create_panel_selection,selection_root
from astrolabe.research_panel.screening_worker import allocation,run_public_screening,worker_root
from astrolabe.research_panel.screening import ScreeningPolicy,IDENTITY_POLICY
from astrolabe.research_panel.trigger_computation import SnapshotTriggerPolicy
repo=Path('/Users/DayyanSheikh/Projects/astrolabe');base=repo/'data-dumps'
frame=json.loads((base/'fs2_frame_refresh_20261003_1_stdout.json').read_text())
launch=json.loads((base/'fs2_frame_refresh_20261003_1_launch.json').read_text())
result=json.loads((base/'fs2_frame_refresh_20261003_1_result.json').read_text())
if result['returncode'] != 0 or frame['state'] != 'exhausted_consistent':raise ValueError('complete refreshed frame required')
panel=base/'fs2_panel_screening_refresh_20261003_1'
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
p=PanelProtocol(scheduled_slots=8,triggered_slots=8,controls_per_trigger=1,cycles=1,target_attempts=1,
 scheduled_per_stratum=2,triggered_per_stratum=2,cadence_seconds=120,max_origin_delay_seconds=60,
 max_origin_save_seconds=5,horizon_seconds=60,tolerance_seconds=5,max_frame_age_seconds=604800,
 max_frame_interval_seconds=600,max_quote_age_seconds=60,max_identity_age_seconds=180,
 source_response_bytes=65536,source_run_retained_bytes=1048576)
reserved=allocation({'reservation':reservation(p,storage_profile='compact-v1')})
free=shutil.disk_usage(repo).free
if free<reserved['required_free_bytes']:raise ValueError('full screening/runtime reservation unavailable')
for root in (panel,selection_root(panel),worker_root(panel)):
 if root.exists():raise FileExistsError(str(root))
print(json.dumps({'stage':'preflight','implementation_commit':commit,'at':_clock(),'free_bytes':free,'reservation':reserved}),flush=True)
started=time.monotonic_ns()
declare_panel(Path(frame['journal_root']),implementation_commit=launch['implementation_commit'],output_root=panel,
 protocol=p,storage_profile='compact-v1',strata_limit=4)
selection=create_panel_selection(panel,repository=repo)
print(json.dumps({'stage':'selection_complete','at':_clock(),'provenance_class':selection['provenance_class']}),flush=True)
r=asyncio.run(run_public_screening(panel,implementation_commit=commit,rule=SnapshotTriggerPolicy(1,3,60000),
 freshness=ScreeningPolicy(120,120),concurrency=4,repository=repo,identity_policy=IDENTITY_POLICY))
print(json.dumps({'stage':'complete','at':_clock(),'elapsed_ns':time.monotonic_ns()-started,'state':r['state'],
 'role_capacity':r['role_capacity'],'states':r['screening']['states'],'recovery':r['recovery'],
 'retained_bytes_before_report':r['retained_bytes_before_report']}),flush=True)
```
