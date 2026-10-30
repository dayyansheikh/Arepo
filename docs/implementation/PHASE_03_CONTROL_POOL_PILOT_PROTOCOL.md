# D101 — one bounded measurement of within-stratum control support

## D100 design decision and scope

D097 had six triggered and two unavailable candidates, with no negative controls. It remains
failed. The unchanged best-size imbalance threshold is not tuned to create negatives.
This separate prospective design changes sampling allocation from four strata/two members to
two strata/four members, using the existing parameterised planner, same eight-member ceiling,
complete discovery and D096 future-or-unknown stated-end population. No new collector code.

For an eligible stratum with N>=4 members among K>=4 eligible strata, a member's first-stage inclusion
remains8/(K*N), while a specified pair's joint inclusion rises from8/(K*N*(N-1)) to
24/(K*N*(N-1)). Greater within-stratum joint support is relevant to matched comparisons.
Small strata saturate; record actual fractions and never invent slots or substitute a stratum.
Triggered-per-stratum also becomes4, retaining the same global8trigger ceiling and rule.
The conditional control matching and all unfilled slots stay explicit.

This sacrifices breadth and can worsen clustered missingness. It does not uniformly dominate
the old design or guarantee a negative candidate. PHASE_03_CONTROL_DESIGN_SENSITIVITY.json
contains exact hypothetical finite-population calculations and176 exhaustively checked toy
cases, including a heterogeneous counterexample where broader coverage is better. These are
not estimates from D097, pooled pilot prevalence, model validation or predicted success rates.
Choose this one design to measure the identified control-support limitation, not a sequence
of seeds, thresholds or designs searched until one passes. If it fails, stop and preserve it.

## Frozen acceptance and bounds

All D097 gates remain unchanged:6/8 timely observed origins,6/8 eligible completed histories,
at least one observed matched trigger/control pair, valid targets for>=80% of observed origins,
full original-code recovery, explicit temporal population/exclusion audit, observer accounting
and reporting of every sampled member. Fewer than8 actual sampled members are reported as
underfilled and cannot satisfy the complete eight-member reporting gate. No replacements.

Same actual declaration/seed-before-selection-read causality, complete Gamma frame,
endDate exclusions/unknown retention, one10s observation-mode subscription per eligible token,
concurrency8/runtime4,60s horizon/15s tolerance, source/byte/time and receipt-hold limits.
No socket continuity from silence/PONGs, invented history, unrelated external quantities,
threshold relaxation, retrospective correction or final-ML-dataset/predictive/economic claim.
Review every selected rule for actual family eligibility. All old evidence remains unchanged.

Same declared full13308526592byte reservation:7GiBframe, complete panel/window/target/recovery
reservation,2GiBreserve,34MiBcapacity-read overhead. No overlap discount. D099 reduced only
physical allocation of an old journal; logical budgets remain unchanged. Recheck before any
requests. No production/paid storage or evidence deletion. Under-capacity stops this attempt.

## Reviewed execution

D096102 scoped cases, D09224 cases and D087 eight-member runtime/recovery remain accepted.
No implementation changed; repeated regression adds no new validation. Existing bounds accept
2*4scheduled<=8 and4triggered-per-stratum<=8global. Reservation depends on unchanged role
ceilings, not observed overlap. D100 exact design calculations validate the changed allocation.
Commit this exact script before one launch. Exclusive prefix fs2_control_pool_pilot_20261008_1;
retain wrapper hashes/clocks/result/stdout/stderr. No source edits during collection/original
audit. No assistant gap between frame/selection/observations/origins/targets. Explicit isolated
SQLite, migration/email disabled. A stale/incomplete/failed frame cannot feed selection.
Phase3 only; Phase4 begins in a fresh conversation after genuine full acceptance.

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
panel=base/'fs2_panel_control_pool_pilot_20261008_1'
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
