# D090 fixed one-sided availability diagnostic

Execute once after implementation tests/self-review and this exact script are committed.
No whole-frame request, new sample, origin or target. These are the three fixed D089 failures,
not a representative panel. All remain in the denominator, even if closed, unavailable or
changed by the time of the new request. Nothing can retroactively improve D089.

Six HTTP requests maximum, each64KiB, each source journal1MiB; at most three60-second socket
subscriptions concurrently. Existing socket caps1000frames/16MiB raw/40MiB retained remain.
Book computation16MiB, analysis64MiB and original readers stay bounded. Reserve1GiB for all
three cases plus2GiB free space, no overlap discount. No retries or redraw. Use explicit isolated
SQLite, AUTO_MIGRATE=false and disabled email; process-scoped caffeinate only.

Fresh verified targeted identity and book are required before subscription, even when the
book lacks a side. Compare token, condition, market and targeted mapping version to the fixed
D089 source binding. Record actual read/subscription/receipt/end clocks. Refuse changed/closed
identity and stale data. The old snapshot/history admission and six-of-eight pilot gates remain.

Report all raw/source hashes, one-/two-sided state, decoded receipt coverage, silent gaps,
errors/closure, actual intervals and original-code replay. A received two-sided snapshot may
support an availability diagnostic; it never proves uninterrupted venue history or predictive
value. Never convert a null quote into zero or a held receipt into continuity. No positive
coverage threshold or result-dependent early stopping. Whole-run failures keep partial bytes.
All conclusions apply to these fixed cases at new actual times, not the previous failed pilot.

Use exclusive launcher logs under data-dumps/fs2_one_sided_launch_20261007_1_*; capture command,
script hash, HEAD, clocks and exit even if the script fails. No source edits during execution.

```python
import asyncio,json,shutil,subprocess,time
from pathlib import Path
from astrolabe.feature_store.capture import Budget,_clock
from astrolabe.feature_store.source_run import SourceRun
from astrolabe.research_panel.book_computation import record_book_computation
from astrolabe.research_panel.quote_inputs import QuoteInputPolicy
from astrolabe.research_panel.observation_binding import read_observation_binding
from astrolabe.research_panel.bound_window import WindowBindingPolicy
from astrolabe.research_panel.socket_window import capture_market_socket
from astrolabe.research_panel.socket_analysis import record_socket_analysis
from astrolabe.research_panel.window_reconciliation import WindowReconciliationPolicy
from astrolabe.research_panel.original_reader import read_original_book_computation,read_original_socket_window,read_original_socket_analysis
repo=Path('/Users/DayyanSheikh/Projects/astrolabe')
root=repo/'data-dumps/fs2_one_sided_diagnostic_20261007_1'
items=[{'market_id': '5233594', 'token_id': '98077667723851266764737777347553785196408711705582489371303343543835560555375', 'condition_id': '0xf660fe0fc13a37671829c71fb9995159ec6a7808405a92449cbee7695ccafc35', 'mapping_version': '84ed8bef61ff40677d53b45490290de012528a7d8e52498102ecec37e8506256'}, {'market_id': '5299067', 'token_id': '3676102803406651090688924860420061420346707850876754167420213205930652979159', 'condition_id': '0xd402178e89ba98691804fa583b50f991524692b3306397e5683fb95746301d7f', 'mapping_version': '9960b949377fd07783435c7001cb8e0e1b58015009f1791e70328012376a8318'}, {'market_id': '628957', 'token_id': '113017673827188867377109454527754982157460887938297582871131403025795572613918', 'condition_id': '0x58b0474e74a03480c439d50e13dd0b75146c3596e5a475f95e70035c90cee4ca', 'mapping_version': '477b94f65ceef423831e054f213e0b36d22ce4c848e3b9c7cdd0cb04410ae5ae'}]
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=repo).strip():raise ValueError('clean tracked tree required')
if root.exists():raise FileExistsError(str(root))
required=3*1024**3
if shutil.disk_usage(repo).free<required:raise ValueError('full diagnostic reservation unavailable')
root.mkdir(mode=0o700)
started=_clock()
async def case(index,item):
 source=root/f'fs2_capture_case_{index}'
 pre=root/f'fs2_book_computation_case_{index}'
 sock=root/f'fs2_socket_window_case_{index}'
 analysis=root/f'fs2_socket_analysis_case_{index}'
 run=SourceRun(source,policy_version='receipt-time-selected-market-v1',
   budget=Budget(requests=2,bytes_per_response=65536,total_bytes=131072),retained_bytes=1048576)
 await run.fetch('gamma.market',{'market_id':item['market_id']})
 await run.fetch('clob.book',{'token_id':item['token_id']})
 result={'case':item,'started_at':_clock(),'socket':None,'analysis':None,'refusal':None}
 result['pre']=record_book_computation(source,output_root=pre,policy=QuoteInputPolicy(60,180))
 try:
  binding=read_observation_binding(pre)
 except ValueError as exc:
  result['refusal']={'stage':'binding','exception_type':type(exc).__name__}
 else:
  result['binding']=binding
  if any(binding['identity'][key]!=value for key,value in item.items()):
   result['refusal']={'stage':'identity_changed','exception_type':None}
  else:
   result['socket']=await capture_market_socket(pre,output_root=sock,
     policy=WindowBindingPolicy(60000,180000),duration_ms=60000,binding_mode='observation')
   result['analysis']=record_socket_analysis(sock,output_root=analysis,
     policy=WindowReconciliationPolicy(120000,120000,1000))
 # Audit only after all live sockets finish, to avoid causal-path CPU contention.
 result['finished_at']=_clock()
 return result
async def collect():return await asyncio.gather(*(case(i,item) for i,item in enumerate(items)))
results=asyncio.run(collect())
for i,result in enumerate(results):
 result['recovery']={'pre':read_original_book_computation(root/f'fs2_book_computation_case_{i}',implementation_commit=commit,repository=repo,output_root=root/f'fs2_book_computation_read_case_{i}')}
 if result['socket'] is not None:
  result['recovery']['socket']=read_original_socket_window(root/f'fs2_socket_window_case_{i}',implementation_commit=commit,repository=repo,output_root=root/f'fs2_socket_window_read_case_{i}')
  result['recovery']['analysis']=read_original_socket_analysis(root/f'fs2_socket_analysis_case_{i}',implementation_commit=commit,repository=repo,output_root=root/f'fs2_socket_analysis_read_case_{i}')
report={'implementation_commit':commit,'started_at':started,'completed_at':_clock(),'results':results,
 'accepted_panel':False,'predictive_evidence':False,'reservation_bytes':required}
with (root/'diagnostic_report.json').open('x') as f:json.dump(report,f,sort_keys=True,indent=2)
print(json.dumps({'root':str(root),'completed_at':report['completed_at'],'refusals':[r['refusal'] for r in results]}))
```
