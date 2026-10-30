# D097 — one prospective temporal-population pilot

## Frozen purpose and scope

D096 explicitly defines the future deep-sample population after D094 measured two endpoints
already past before frame acquisition. Its102 targeted synthetic cases pass, including full
owned-runtime/original-code recovery. This protocol measures the new conditional population
once; it neither reruns nor repairs D094. Preserve every prior result and raw discovery row.

Use `scheduled_end_after_selection_declaration_or_unknown_v1`: at the actual selection-policy
declaration clock, exclude mapped members whose stated endDate is at or before that clock.
Keep unknown/invalid dates eligible. Preserve all mapped/unresolved inventories and explicit
zero-inclusion temporal exclusions. All probabilities are conditional on this declared
population. Do not assert actual trading activity from endDate; postponed markets with old
endDate are outside this population and later expiry/incorrect metadata may still fail.
No price/book/outcome-based eligibility, extra margin, sample redraw or stop-on-success.

One complete fresh Gamma frame, four uniformly selected eligible strata, two scheduled members
per stratum, bounded triggered/control roles, one10s observer per eligible sampled token,
concurrency8/runtime4. Existing observation mode retains one-sided/empty states without invented
quotes/history. Internally generated seed is frozen after complete-frame collection and before
selection numerical reads. No assistant gap between frame verification, selection and pilot.

## Unchanged gates and additional population audit

All D089/D094 bounds and gates remain binding:6/8 timely observed origins,6/8 fresh completed
histories, an observed matched trigger/control pair, valid actual targets for at least80% of
observed origins, full original-code audit and all8members/observer attempts accounted for.
Report silent/disconnected/invalid/one-sided/empty/observed states separately. Receipt holds
and PONGs do not prove native continuity. No model, alpha, economic or full-ML-dataset claim.
Review actual selected rules for related/external eligibility and preserve missingness.

Additional gate: declarationv4/selectionv3/planv3 must bind the same population policy/reference;
all raw and mapped inventory counts must reconcile with exclusions and selection-eligible
counts; no selected member may have a past close band at the frozen reference. Replay exact
stage/member/control probabilities and preserve denominator distinctions. Do not retrofit
this policy onto any old frame/selection or reinterpret failed old samples.

## Reservation and execution boundary

Full7GiB frame plus declared selection/panel/window/target/original-recovery reservation,
2GiB reserve and34MiB proof-read overhead requires13308526592bytes. Recheck at launch and
stop before source requests if insufficient. No empirical evidence deletion, paid or production
storage. Exclusive prefix fs2_temporal_pilot_20261008_1; wrapper records actual commit/script
hash/clocks/stdout/stderr. Commit this protocol before launch; no source edits during measurement
or original-code audit. Explicit isolated SQLite, migration/email disabled. A failed/incomplete
frame cannot feed selection. Any gate failure stays failed; stop this finite protocol and
investigate evidence, never repeat it merely to pass. Phase4 cannot begin here.

```python
import asyncio,json,resource,shutil,subprocess,time,uuid
from pathlib import Path
from astrolabe.feature_store.capture import _clock
from astrolabe.research_panel.frame import FrameBudget,FrameRetryPolicy,GammaFrameRun
from astrolabe.research_panel.frame_cli import summary
from astrolabe.research_panel.panel_declaration import PanelProtocol,declare_panel,reservation,TEMPORAL_POPULATION
from astrolabe.research_panel.panel_selection import create_panel_selection,selection_root
from astrolabe.research_panel.screening_worker import allocation,run_public_window_pilot,worker_root
from astrolabe.research_panel.screening import ScreeningPolicy
from astrolabe.research_panel.trigger_computation import SnapshotTriggerPolicy
from astrolabe.research_panel.activation import activation_root
from astrolabe.research_panel.runtime import run_root
from astrolabe.research_panel.owned_windows import OwnedWindowPolicy
from astrolabe.research_panel.bound_window import WindowBindingPolicy
from astrolabe.research_panel.origin_window import OriginWindowPolicy
from astrolabe.research_panel.window_reconciliation import WindowReconciliationPolicy
repo=Path('/Users/DayyanSheikh/Projects/astrolabe');base=repo/'data-dumps'
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=repo).strip():raise ValueError('clean tracked tree required')
panel=base/'fs2_panel_temporal_pilot_20261008_1'
p=PanelProtocol(scheduled_slots=8,triggered_slots=8,controls_per_trigger=1,cycles=1,target_attempts=1,
 scheduled_per_stratum=2,triggered_per_stratum=2,cadence_seconds=120,max_origin_delay_seconds=60,
 max_origin_save_seconds=5,horizon_seconds=60,tolerance_seconds=15,max_frame_age_seconds=3600,
 max_frame_interval_seconds=600,max_quote_age_seconds=60,max_identity_age_seconds=180,
 source_response_bytes=65536,source_run_retained_bytes=1048576)
reserved=allocation({'reservation':reservation(p,storage_profile='compact-v1')},windows=True)
budget=FrameBudget(requests=4000,total_bytes=3221225472,retained_bytes=7*1024**3)
# No overlap discount between old and new frame, selection, windows, roles or targets.
# Existing data is already reflected in free space. Add capacity-proof read journal space.
required=budget.retained_bytes+reserved['required_free_bytes']+34*1048576
free=shutil.disk_usage(repo).free
if free<required:raise ValueError('complete frame plus panel reservation unavailable')
for root in (panel,selection_root(panel),worker_root(panel),activation_root(panel),run_root(panel)):
 if root.exists():raise FileExistsError(str(root))
print(json.dumps({'stage':'preflight','implementation_commit':commit,'at':_clock(),'free_bytes':free,'required_free_bytes':required,'panel_reservation':reserved,'frame_retained_limit':budget.retained_bytes}),flush=True)
started=time.monotonic_ns();frame_root=base/('fs2_capture_'+uuid.uuid4().hex)
print(json.dumps({'stage':'frame_owned','root':str(frame_root),'at':_clock()}),flush=True)
run=GammaFrameRun(frame_root,limit=100,budget=budget,
 measurement_root=base/'fs2_capture_c63c72a0fe194f47824ccc862b0619cd',
 request_capacity_root=base/'fs2_capture_3a4f80db7fa94d248fc16e1397af4c71',
 request_capacity_commit='726cec27ff6eeb4c10b01dd0ebde84b9804d3fb0',
 retry_policy=FrameRetryPolicy(),reuse_connections=True)
asyncio.run(run.collect());frame=summary(frame_root)
print(json.dumps({'stage':'frame_complete','at':_clock(),'report':frame}),flush=True)
if frame['state']!='exhausted_consistent':raise ValueError('complete frame required; no selection')
# No assistant turn, schedule or wall-clock fabrication between verified frame and selection.
declare_panel(frame_root,implementation_commit=commit,output_root=panel,
 protocol=p,storage_profile='compact-v1',strata_limit=4,population_policy=TEMPORAL_POPULATION)
selection=create_panel_selection(panel,repository=repo)
print(json.dumps({'stage':'selection_complete','at':_clock(),'provenance_class':selection['provenance_class']}),flush=True)
windows=OwnedWindowPolicy(10000,WindowBindingPolicy(60000,180000),
 WindowReconciliationPolicy(120000,120000,1000),OriginWindowPolicy(120000,60000),binding_mode='observation')
r=asyncio.run(run_public_window_pilot(panel,implementation_commit=commit,rule=SnapshotTriggerPolicy(1,3,60000),
 freshness=ScreeningPolicy(120,120),window_policy=windows,concurrency=8,runtime_concurrency=4,repository=repo))
print(json.dumps({'stage':'complete','at':_clock(),'elapsed_ns':str(time.monotonic_ns()-started),
 'peak_resident_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'state':r['state'],
 'role_capacity':r['role_capacity'],'states':r['screening']['states'],'recovery':r['recovery'],
 'runtime':r['runtime'],'retained_bytes_before_report':r['retained_bytes_before_report']}),flush=True)


```
