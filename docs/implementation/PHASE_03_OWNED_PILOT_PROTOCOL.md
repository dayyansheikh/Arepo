# D082 — one bounded public execution pilot

Execute only after D081 integration passes targeted acceptance, is self-reviewed, committed
and represented in draft PR16. Commit this complete protocol/script before any new draw or
request. This measurement tests actual public execution timing, not predictive edge or
complete Phase3 acceptance. Required window/related/external families remain explicit missing
where their evidence is absent. No numerical evidence is deleted or restamped.

## Fixed design

Use the already verified D077 frame (`fs2_capture_f1f8ed0835e544228439115e4c2f8efc`, original
acquisition commit c6f4891661a979ab91755714869288152b8679fb), within its seven-day age limit.
Do not reacquire the frame or rerun D078. Draw four strata uniformly without replacement,
two scheduled markets per stratum, under a newly generated pre-source seed. Retain the full
frame inventory, exact first-stage probabilities, conditional measured-role probabilities,
all scheduled members, missing controls and unknown event grouping. No replacement/redraw.
The frozen trigger remains absolute displayed snapshot imbalance >=1/3 with the existing
60000ms source-age bound. It does not claim persistent imbalance or complete fill flow.

One cycle, at most eight unique markets. Screening concurrency4 (16 requests maximum),
runtime concurrency4 with at most three concurrent origins and reserved target capacity.
No artificial staggering. Up to24 origin requests (Gamma/book/bounded taker-trade page) and
16 target requests (Gamma/book), at most56 total. Controls/triggers overlap scheduled markets;
role counts are not independent sample sizes. No retry, resume, truncation or replacement.

Origins have60s maximum dispatch delay and5s maximum save delay. Horizon60s; one target attempt
at due time,15s tolerance. The15s target allowance is fixed before this first runtime sample:
D078's actual targeted request windows plus computation availability required up to roughly13s;
a5s screen-only placeholder is not a measured viable processing budget. Origin quote/identity
ages remain60s/180s, screen window/assessment ages120s/120s. Frame interval limit600s. Use real
UTC/monotonic clocks at every source/read/compute/freeze/save; never move them after failure.

64KiB per response,1MiB per source journal, compact-v1 computations. Reserve the entire
screening plus all possible role/origin/target/recovery costs, without role-overlap discounts,
plus2GiB free reserve before writes. Verify exclusive absence of panel/selection/worker/
activation/runtime roots. Stop on a violated guard and preserve the failed attempt.

## Frozen execution success gates

1. Complete source/dependency/original-code audit succeeds with exact numerical/clock/weight
   preservation and no changed or future inputs. Every assigned market and failed slot remains.
2. At least6 of the8 selected markets have observed origins within the fixed dispatch/save
   bounds. Any other origins remain explicit abstentions; no denominator substitution.
3. At least one observed triggered member and its observed matched negative control remain.
   Match the control matched_trigger_ids to the triggered assignment trigger_id; both origins
   must be observed. An unrelated observed trigger does not satisfy the pairing gate.
   Missing control slots are retained. No new trigger threshold or retrospective matching.
4. At least4/5 of eligible observed origins have a valid selected target under the unchanged
   first-valid quote/deadline rule. Use exact count comparison `5*valid >= 4*eligible`.
   Identity-changed, late, closed and unavailable targets are not successes.
5. Report timings, source states, retained bytes, actual requests, original audit result and
   unavailable families. Socket continuity, economic independence, selected external relevance
   and complete flow/window eligibility are never inferred from successful snapshot execution.

These gates determine **execution measurement success only**. Even success is not an automatic
Phase3 exit, calibrated forecast, edge result or executable profit. Full Phase3 review must
still address its entire scope. A failed gate informs a separate later protocol after evidence
review; it cannot be repaired by rerunning this attempt or relabelling its origins.

## Exclusive script

Run with the repository backend interpreter, explicit isolated SQLite URL, AUTO_MIGRATE=false
and email disabled. No startup/migration/scheduler entry point is invoked. Use process-scoped
caffeinate while this finite measurement runs. Save exclusive launch/stdout/stderr/result logs
under data-dumps/fs2_owned_pilot_20261003_1_*. Record exact HEAD, result code and actual clocks.

```python
import asyncio,json,shutil,subprocess,time
from pathlib import Path
from astrolabe.feature_store.capture import _clock
from astrolabe.research_panel.panel_declaration import PanelProtocol,declare_panel,reservation
from astrolabe.research_panel.panel_selection import create_panel_selection,selection_root
from astrolabe.research_panel.screening_worker import allocation,run_public_pilot,worker_root
from astrolabe.research_panel.screening import ScreeningPolicy
from astrolabe.research_panel.trigger_computation import SnapshotTriggerPolicy
from astrolabe.research_panel.activation import activation_root
from astrolabe.research_panel.runtime import run_root
repo=Path('/Users/DayyanSheikh/Projects/astrolabe');base=repo/'data-dumps'
frame=json.loads((base/'fs2_frame_refresh_20261003_1_stdout.json').read_text())
launch=json.loads((base/'fs2_frame_refresh_20261003_1_launch.json').read_text())
result=json.loads((base/'fs2_frame_refresh_20261003_1_result.json').read_text())
if result['returncode'] != 0 or frame['state'] != 'exhausted_consistent':raise ValueError('complete refreshed frame required')
panel=base/'fs2_panel_owned_pilot_20261003_1'
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
p=PanelProtocol(scheduled_slots=8,triggered_slots=8,controls_per_trigger=1,cycles=1,target_attempts=1,
 scheduled_per_stratum=2,triggered_per_stratum=2,cadence_seconds=120,max_origin_delay_seconds=60,
 max_origin_save_seconds=5,horizon_seconds=60,tolerance_seconds=15,max_frame_age_seconds=604800,
 max_frame_interval_seconds=600,max_quote_age_seconds=60,max_identity_age_seconds=180,
 source_response_bytes=65536,source_run_retained_bytes=1048576)
reserved=allocation({'reservation':reservation(p,storage_profile='compact-v1')})
free=shutil.disk_usage(repo).free
if free<reserved['required_free_bytes']:raise ValueError('full screening/runtime reservation unavailable')
for root in (panel,selection_root(panel),worker_root(panel),activation_root(panel),run_root(panel)):
 if root.exists():raise FileExistsError(str(root))
print(json.dumps({'stage':'preflight','implementation_commit':commit,'at':_clock(),'free_bytes':free,'reservation':reserved}),flush=True)
started=time.monotonic_ns()
declare_panel(Path(frame['journal_root']),implementation_commit=launch['implementation_commit'],output_root=panel,
 protocol=p,storage_profile='compact-v1',strata_limit=4)
selection=create_panel_selection(panel,repository=repo)
print(json.dumps({'stage':'selection_complete','at':_clock(),'provenance_class':selection['provenance_class']}),flush=True)
r=asyncio.run(run_public_pilot(panel,implementation_commit=commit,rule=SnapshotTriggerPolicy(1,3,60000),
 freshness=ScreeningPolicy(120,120),concurrency=4,runtime_concurrency=4,repository=repo))
print(json.dumps({'stage':'complete','at':_clock(),'elapsed_ns':time.monotonic_ns()-started,'state':r['state'],
 'role_capacity':r['role_capacity'],'states':r['screening']['states'],'recovery':r['recovery'],
 'runtime':r['runtime'],'retained_bytes_before_report':r['retained_bytes_before_report']}),flush=True)

```
