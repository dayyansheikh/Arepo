# D094 — one bounded empirical validation of owned observation mode

## Purpose and frozen scope

D092 adds a real capability: the owned panel can observe an identity-bound one-sided/empty
book without claiming a quote/history. Its integration has passed24 tests, including full
original-runtime recovery. Validate that changed path once against public data. The hypothesis
is operational: all valid active pre-bindings can be attempted and retained without fabricating
histories or dropping sampled failures. This is not a rerun of D089 and cannot repair its5/8
result. D090 found no recovery in its one active case, so there is no assumption that sockets
will improve history availability.

Exactly one complete fresh-frame/selection/observer/origin/target attempt. At most eight
unique scheduled markets, four uniformly sampled strata and two members per stratum, exact
stage and conditional control probabilities, a pre-source immutable seed. Same one10s observer
per eligible token and concurrency8/runtime4. No new retries, duplicate observers, stagger,
filtering or stop-on-success rule. On failure, preserve/report and stop this protocol; no second
draw is authorised by it. The entire universe and all unavailable members remain accounted for.

The origin/history6/8, matched observed trigger/control, target80%, full original audit and
per-window reporting gates in PHASE_03_FRESH_WINDOW_PILOT_PROTOCOL.md remain exactly binding.
A two-sided frame after an unavailable pre-book does not supply eligible prior history.
Additional D094 gate: each selected valid active observed/one-sided/empty pre-book has a
persisted observer attempt or explicit authenticated refusal; worker v7/socket v2/coverage v2
must agree. Report observed, one-sided, empty, invalid, disconnected and silent states separately.
Zero native-continuity and no predictive/economic claims. Success is not a final ML dataset.

All D089 time/byte/response/frame/capacity limits remain unchanged. Full7GiB frame + panel/
selection/window/target/original-recovery +2GiB free reserve and34MiB capacity-read overhead
requires13308526592bytes at launch. October8 preflight snapshot13802956KiB free exceeds that;
the executable rechecks before requests. Never delete evidence or use production capacity.

D093's checksum-bound rule review completes the existing-sample family-eligibility review:
France/Spain share retained tournament-winner rules but no pre-origin price binding or complete
outcome set. None of the eight rules matches KNYC station measurements. A source mentioned by
resolution rules is not permission, a verified adapter or a causal information observation.
All unsupported external/related/flow/native-window values stay unavailable. After this fresh
run review its actual rules the same way; do not force a feature merely to pass a gate.

## Execution and stop conditions

Commit this exact script and review before launch. Exclusive wrapper prefix
fs2_observation_pilot_20261008_1; roots derive from the fixed panel name below. Capture actual
HEAD, script hash, launch/result clocks and stdout/stderr. Explicit isolated SQLite, migration
and email disabled; process-scoped caffeinate only. No source edits during run/original audit.
Only current tested existing APIs; no new infrastructure or source adapter. A stale, incomplete,
quota-stopped or failed frame never feeds selection. No assistant-turn boundary between stages.
If gates fail, this run remains failed; do not repeat it, relax thresholds or proceed to Phase4.

```python
import asyncio,json,resource,shutil,subprocess,time,uuid
from pathlib import Path
from astrolabe.feature_store.capture import _clock
from astrolabe.research_panel.frame import FrameBudget,FrameRetryPolicy,GammaFrameRun
from astrolabe.research_panel.frame_cli import summary
from astrolabe.research_panel.panel_declaration import PanelProtocol,declare_panel,reservation
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
panel=base/'fs2_panel_observation_pilot_20261008_1'
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
 protocol=p,storage_profile='compact-v1',strata_limit=4)
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
