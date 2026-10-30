# D089 — fresh-frame bounded window pilot after measured verifier repair

Execute once only after D087 software and eight-member synthetic gates pass, self-review and commit, and after this
complete protocol/script is committed. Draft PR16 stays unmerged. This is a fresh sampled
measurement; D082, D085 and D086 are immutable and must not be enriched or rerun. No Phase4 work.

## Fixed scope and causal design

D088 completed successfully but was not consumed before its one-hour limit. Retain it.
Acquire a new complete frame and proceed immediately in the same process, within the frozen
one-hour age limit. Uniformly draw four available strata without replacement,
two scheduled members per stratum, from a newly generated pre-source seed. Keep exact
first-stage and conditional role probabilities, all unknown identities/metadata, missing
controls and source errors. No redraw/retry/resume or selection based on observed outcomes.

One cycle, at most eight unique markets. Same snapshot trigger |imbalance|>=1/3 and60000ms
source-age bound. Screening/observer concurrency8, one10-second subscription per selected
token following its authenticated pre-book. No duplicate observers, artificial staggering
or common-clock fiction. Source requests and original raw numerical inputs remain bounded.
Full window analysis completes before actual owned activation; original audit follows the
last target. Runtime concurrency4 reserves target capacity. Roles overlap markets and do
not add independent samples.

Keep D082's origin60s dispatch/5s save limits,60s target horizon/15s tolerance,60s origin
quote/180s identity age,120s screen/assessment freshness and600s frame interval limit.
New dependency limits are explicit: binding quote60000ms/identity180000ms; window duration
10000ms; history age120000ms/window age60000ms at actual read AND freeze. Receipt diagnostics
hold each observed book for at most1000ms; silence, PONGs or matching endpoints never prove
venue continuity. Analysis endpoint parameters120000ms/120000ms are retained even though
no separate post endpoint is admitted. Irregular two-snapshot history is not a locked model.

At most56 HTTP requests (16 screening,24 origin,16 target) plus eight finite subscriptions;
64KiB/response,1MiB/source journal, existing socket max1000 frames/16MiB raw/40MiB retained
and analysis64MiB total/16MiB artifact caps. Reserve every possible selected window104MiB
in addition to all existing role/origin/target/metadata/recovery costs and2GiB free reserve.
No overlap discount. Failure preserves evidence and stops the attempted run.

## Frozen measurement gates

1. Complete original-code replay preserves numerical values, weights, identities, hashes and
   all actual clocks. Every sampled member and failed slot remains in the denominator.
2. At least6 of8 sampled markets have observed origins within the unchanged dispatch/save
   limits AND eligible pre-origin history at actual freeze. For these histories, require an
   actually sent subscription before its actual window end and before origin read/freeze,
   with terminal interval_ended and close state closed. Early disconnects, quota stops and
   unavailable connections remain evidence but cannot satisfy this completed-window gate.
3. At least one observed trigger and its actually matched observed negative control remain;
   verify their immutable trigger/matched_trigger IDs. All unfilled controls remain explicit.
4. At least4/5 of all origins whose origin state is observed have a valid first-quote target
   within the fixed deadline:5*valid>=4*eligible. History missingness never removes an
   observed origin from this target denominator. Late, closed, changed identity and unavailable are failures.
5. Report every window's actual interval, terminal/closure, raw messages, covered/uncovered
   receipt durations, irregular history ages, origin/target timing, bytes and role coverage.
   Require no positive native-coverage threshold: this measurement discovers the real gaps;
   it does not turn the receipt hold policy into a venue completeness assertion.

Selected related/external relevance must be reviewed against the actual frozen questions.
Do not attach the old KNYC NWS reading to unrelated markets, retrofit grouping, or invent
complete-flow/persistent-depth features. Preserve unavailable families. Successful execution
is not alpha, executable profit, a final ML dataset, or automatic full Phase3 acceptance.
The complete acceptance map and limitations still govern Phase3 exit. D087 retains all per-call
build checks and removes repeated compilation; it passes76 tests and8 synthetic fresh histories/targets.
D085 four unavailable books coincided with fresh closed/non-accepting Gamma state; a new complete
frame addresses lifecycle drift before this new draw. Do not filter the old draw or compare pilot
success rates as predictive skill. The one-hour age rule is prospective and leaves old evidence unchanged. A failed gate requires
evidence review and a separate future protocol, never retrospective threshold relaxation.

## Exclusive execution

Use exclusive wrapper prefix fs2_lifecycle_pilot_20261005_1 and the exact script below.
The old standalone pilot script was never executed. Use the backend interpreter, explicit isolated SQLite, AUTO_MIGRATE=false, disabled email
and process-scoped caffeinate. No startup/migration/scheduler/production actions. Preserve
exclusive launch/stdout/stderr/result logs as data-dumps/fs2_lifecycle_pilot_20261005_1_* with
actual HEAD and clocks. Do not edit source packages during collection or original recovery.
Verify absence of every derived panel/selection/worker/activation/runtime root before writes.


## Additional combined reservation and terminal rules

Freeze one complete end-to-end attempt. Frame request/raw/time/retry/universe limits match
D088; only its new-attempt retained allocation is7GiB, versus the observed3,739,809,659bytes.
This uses the existing tested FrameBudget API, preserves all captured bytes and failed runs,
and changes no live retention. A quota stop cannot satisfy completeness or begin selection.
Reserve7GiB PLUS the complete panel/window/selection/original-recovery reservation (including
its2GiB free reserve) PLUS34MiB capacity-read overhead before requests. No overlap discount.
The same source code/HEAD must remain fixed through all stages; freeze this protocol first.
No assistant or scheduler transition between frame completion, selection, screening or due
collection. Wrapper captures launch/command/script hash, stdout, stderr, exit and actual clocks
using exclusive files, even on failure. No silent whole-attempt retry or resume.
All five measurement gates above remain unchanged. Success is not automatic Phase3 acceptance.

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
panel=base/'fs2_panel_window_pilot_20261005_1'
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
 WindowReconciliationPolicy(120000,120000,1000),OriginWindowPolicy(120000,60000))
r=asyncio.run(run_public_window_pilot(panel,implementation_commit=commit,rule=SnapshotTriggerPolicy(1,3,60000),
 freshness=ScreeningPolicy(120,120),window_policy=windows,concurrency=8,runtime_concurrency=4,repository=repo))
print(json.dumps({'stage':'complete','at':_clock(),'elapsed_ns':str(time.monotonic_ns()-started),
 'peak_resident_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'state':r['state'],
 'role_capacity':r['role_capacity'],'states':r['screening']['states'],'recovery':r['recovery'],
 'runtime':r['runtime'],'retained_bytes_before_report':r['retained_bytes_before_report']}),flush=True)

```
