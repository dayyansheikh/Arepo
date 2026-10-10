# D114 — bounded integration of opt-in gzip capture

Status: predeclared; launch is gated by committed code/protocol, completed D113 exact-byte
storage proof and the full measured reservation. No source requests before those gates.

D110 remains failed:665.126435s frame interval against600s, no selection/origins. D111's
four fixed cached first-page requests established identical decoded bytes and smaller gzip
wire bodies (47252 versus548290bytes). Cache/connection effects prevent a full-frame timing
claim. D112 implements bounded Gamma-only opt-in decoding with raw wire preserved first,
independent wire/decoded budgets, versioned evidence, strict JSON/numerical handling and
original-code recovery.265 affected pre-final/78 final scoped tests passed (overlapping).
This measured transport change justifies one integration; it does not guarantee acceptance.

Compared with D110, the script changes only exclusive output paths and accept_gzip=True.
All source/sampling/control/observer/freshness/deadline/gate values remain unchanged.
There is no reinterpretation, repair, rerun or redraw of D110/D106 or other failed panels.
A failure stops acquisition and is retained for diagnosis, never relaxed retrospectively.
No predictive/economic/independent-event or final ML dataset claim; Phase3 only.

Reservation:13,308,526,592bytes without overlap discount. Wire and decoded frame caps each
remain3GiB, per-response ceiling unchanged; retained frame cap7GiB. Remeasure after D113
preserves exact closed D110 bytes/metadata/paths and reproduces its original report. No
logical evidence deletion. Launch uses isolated SQLite, AUTO_MIGRATE=false, disabled email,
clean tracked Git state and immutable source. Retain launch script/hash/build, clocks,
stdout/stderr and terminal result. No source edits while collection or original audit runs.

Frozen gates: eight-member reporting; at least6timely observed origins and6eligible completed
histories; at least one observed matched trigger/control pair; valid targets for at least80%
of observed origins; original-code recovery; temporal inventory/exclusion and observer
accounting; raw/causal provenance; actual selected rule/family eligibility review. Socket
silence never establishes continuity. Missing families stay explicit. Passing this execution
does not waive any other Phase3 gate. No production action or Phase4.

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
panel=base/'fs2_panel_gzip_pilot_20261010_1'
p=PanelProtocol(scheduled_slots=8,triggered_slots=8,controls_per_trigger=1,cycles=1,target_attempts=1,
 scheduled_per_stratum=4,triggered_per_stratum=4,cadence_seconds=120,max_origin_delay_seconds=60,
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
 retry_policy=FrameRetryPolicy(),reuse_connections=True,accept_gzip=True)
asyncio.run(run.collect());frame=summary(frame_root)
print(json.dumps({'stage':'frame_complete','at':_clock(),'report':frame}),flush=True)
if frame['state']!='exhausted_consistent':raise ValueError('complete frame required; no selection')
# No assistant turn, schedule or wall-clock fabrication between verified frame and selection.
declare_panel(frame_root,implementation_commit=commit,output_root=panel,
 protocol=p,storage_profile='compact-v1',strata_limit=2,population_policy=TEMPORAL_POPULATION)
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
