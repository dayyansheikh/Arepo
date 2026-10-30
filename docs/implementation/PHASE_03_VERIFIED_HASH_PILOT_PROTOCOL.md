# D106 — bounded integration after strict-row hashing optimisation

Status: frozen design, not launched. Full storage reservation and reviewed committed build
are required before any request. This is one prospective execution, not a redraw loop.

D101 is terminal: original verification timed out before selection, with zero origins or
control-design results. Its frame, failure and clocks remain unchanged. D104 now reduces
strict raw-row hashing work without changing bytes, identities or acceptance semantics;
97 affected tests pass. The full offline computation is6.8% faster (226.301→210.875s), with
identical276795-row/2769-attempt summaries. This does not prove the full reader meets300s,
and does not establish hashing as the sole cause of D101's timeout. This integration will
measure the actual unchanged reader/causal gates after the tested change. Stop and preserve
any failure. Do not increase deadlines, change seeds/strata/thresholds or retry to obtain
passing observations. A future action must follow evidence, not a repeated draw.

## Unchanged scientific and operational contract

D100 allocation analysis and D101 frozen contract remain binding:2strata ×4scheduled
candidates (eight total), four triggered per stratum/eight global, one matched control per
trigger. Exact actual inclusion fractions and unknown/underfilled slots are retained.
Complete source discovery remains separate from the future-or-unknown stated-end deep
population. No category/metadata invention or replacement of selected unavailable markets.

Acceptance: eight-member reporting; at least6timely observed origins and6eligible completed
histories; at least one observed matched trigger/control pair; valid targets for at least80%
of observed origins; full original-code recovery; exact temporal inventory/exclusion audit;
observer accounting and raw/provenance checks. Record every actual selected rule and its
related/external eligibility. Unsupported features remain unavailable. This pilot is neither
a final ML dataset nor predictive/economic evidence. Phase4 is excluded.

Timing/bounds:600s maximum frame interval,3600s frame age;1/3best-size imbalance rule;
10s observation-mode subscriptions, concurrency8/runtime4;60s origin delay/5s save;
60s target horizon/15s tolerance. Source freshness, receipt coverage and window policies
below are unchanged. Silence/PONGs do not establish native continuity. No retrospective
clock reconstruction, refreshed old origins or repaired failed histories.

Reservation: full13,308,526,592bytes before collection, no overlap discount;7GiBframe plus
declared panel/window/target/recovery space,2GiBreserve and34MiBcapacity-read overhead.
D105 lossless closed-journal compression may restore physical headroom but cannot change
logical budgets or delete evidence. An insufficient reservation stops this attempt.

## Execution and recovery

Commit this exact script first. Exclusive prefix fs2_verified_hash_pilot_20261009_1, isolated
SQLite with AUTO_MIGRATE=false and email disabled. Record wrapper/script hashes, real clocks,
stdout/stderr/result. The script differs from D101 only in its exclusive path: no numerical
or sampling adjustment. No source edits during collection or original-reader audit. On a
failure, retain the entire run, extract the exact failed gate, and stop acquisition. On
success, audit all unchanged gates and family eligibility before claiming Phase3 completion.

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
panel=base/'fs2_panel_verified_hash_pilot_20261009_1'
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
 retry_policy=FrameRetryPolicy(),reuse_connections=True)
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
