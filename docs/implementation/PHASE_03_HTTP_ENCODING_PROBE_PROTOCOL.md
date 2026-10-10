# D111 — fixed HTTP representation diagnostic

D110 failed665.126435s against the unchanged600s gate after complete280090-row discovery
and successful original-code audit. No selection, origins or targets. Preserve the failure.
Its recorded request/response intervals total375.543s (D106305.277s); local receipt/persistence
intervals total289.637s (D106337.233s). These are wall intervals, not pure network/CPU attribution;
page counts, server/cache state and payloads differ. Local improvements do not guarantee600s.

Before changing capture/admission, test whether the public endpoint offers gzip and whether
its wire size/time warrants a separately reviewed implementation. Exactly four first-page
requests: identity,gzip,gzip,identity; limit100/closed=false; reused HTTP/1 connection;
no redirects, credentials, pagination or retries. Frozen code below; commit before execution.
Four4MiB wire/decoded caps,20s request/90s total deadline,128MiB free reservation. Record
all responses/errors, exact encoded and decoded bytes/hashes, selected public headers,
request/first-byte/receive/durable clocks. Strict decoded JSON only; bounded CRC/EOF/trailing
checks for gzip. Existing collector/source registry/admission stays unchanged.

Exclusive output data-dumps/fs2_http_encoding_probe_20261010_1 is diagnostic-only and cannot
be admitted as an fs2_capture journal. No universe, sample, causal origin or predictive
claim. Changing live values/cache/connection warmth can confound timings; this is feasibility
evidence, not a throughput guarantee. Do not repeat to select a better result. Decide the
next implementation from all four outcomes, not from speculative infrastructure.

```python
"""Four fixed diagnostic requests; no collector admission or panel creation."""
import asyncio,gzip,hashlib,json,shutil,subprocess,time,zlib
from pathlib import Path
import httpx
from astrolabe.feature_store.capture import _clock,_json_bytes,_strict_json,_write_once
from astrolabe.feature_store.sources import SOURCES
repo=Path('/Users/DayyanSheikh/Projects/astrolabe')
root=repo/'data-dumps/fs2_http_encoding_probe_20261010_1'
source=SOURCES['gamma.markets.keyset'];params=source.params({'limit':100,'closed':'false'})
CAP=4*1048576

def decode(raw,encoding):
 if encoding=='identity':return raw
 if encoding!='gzip':raise ValueError('unsupported encoding')
 decoder=zlib.decompressobj(16+zlib.MAX_WBITS)
 result=decoder.decompress(raw,CAP+1)
 if len(result)>CAP or decoder.unconsumed_tail or not decoder.eof or decoder.unused_data:
  raise ValueError('oversized, incomplete or trailing gzip')
 return result

async def main():
 assert decode(gzip.compress(b'{"x":1.200}'),'gzip')==b'{"x":1.200}'
 for raw in [gzip.compress(b'x')[:-2],gzip.compress(b'x')+b'trailing',gzip.compress(b'x'*(CAP+1))]:
  try:decode(raw,'gzip')
  except ValueError:pass
  else:raise AssertionError('invalid gzip accepted')
 assert shutil.disk_usage(repo).free>=128*1048576
 root.mkdir(mode=0o700,exist_ok=False)
 script=Path(__file__).read_bytes();_write_once(root/'script.py',script)
 policy={'schema':'arepo-http-encoding-diagnostic-v1','admitted':False,'source_id':source.source_id,
  'endpoint':source.endpoint,'params':params,'encodings':['identity','gzip','gzip','identity'],
  'max_wire_bytes_each':CAP,'max_decoded_bytes_each':CAP,'request_deadline_seconds':20,
  'total_deadline_seconds':90,'started':_clock(),'implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
  'script_sha256':hashlib.sha256(script).hexdigest(),'scope':'First page only, repeated fixed diagnostic; not complete frame, research sample or origins. Keep all failures; no retries.'}
 _write_once(root/'policy.json',_json_bytes(policy));results=[]
 async with asyncio.timeout(90):
  async with httpx.AsyncClient(timeout=15,trust_env=False,follow_redirects=False,http2=False,
   limits=httpx.Limits(max_connections=1,max_keepalive_connections=1,keepalive_expiry=30)) as client:
   for i,encoding in enumerate(policy['encodings']):
    folder=root/str(i);folder.mkdir();wire=bytearray();status=None;headers={};first_byte=None;error=None;cancelled=False
    started=_clock()
    try:
     async with asyncio.timeout(20):
      async with client.stream('GET',source.endpoint,params=params,headers={'Accept':'application/json','Accept-Encoding':encoding,'User-Agent':'Arepo-Research-Verification/2.0'}) as response:
       status=response.status_code
       headers={k:response.headers[k] for k in ('content-encoding','content-type','content-length','date','etag','age','cf-cache-status','vary') if k in response.headers}
       async for chunk in response.aiter_raw():
        if first_byte is None:first_byte=_clock()
        remaining=CAP-len(wire);wire.extend(chunk[:remaining])
        if len(chunk)>remaining:raise ValueError('wire budget exceeded')
    except asyncio.CancelledError:error="cancelled";cancelled=True
    except Exception as exc:error=type(exc).__name__
    received=_clock();raw=bytes(wire);_write_once(folder/'wire.bin',raw)
    record={'ordinal':i,'requested_encoding':encoding,'started':started,'first_byte':first_byte,'received':received,'status':status,'headers':headers,'error':error,'wire_bytes':len(raw),'wire_sha256':hashlib.sha256(raw).hexdigest(),'elapsed_ns':int(received['monotonic_ns'])-int(started['monotonic_ns'])}
    if error is None and status==200:
     try:
      decoded=decode(raw,headers.get('content-encoding','identity'));value=_strict_json(decoded)
      _write_once(folder/'decoded.bin',decoded)
      record.update(decoded_bytes=len(decoded),decoded_sha256=hashlib.sha256(decoded).hexdigest(),strict_json_valid=True,market_rows=len(value['markets']))
     except Exception as exc:record['decode_error']=type(exc).__name__
    _write_once(folder/'receipt.json',_json_bytes(record));_write_once(folder/'receipt_ack.json',_json_bytes({'receipt_sha256':hashlib.sha256((folder/'receipt.json').read_bytes()).hexdigest(),'durable_ack':_clock()}));results.append(record)
    if cancelled:raise asyncio.CancelledError
 _write_once(root/'report.json',_json_bytes({'results':results,'completed':_clock(),'admitted':False,'synthetic_decoder_checks_passed':4}))
 print(json.dumps([{k:r.get(k) for k in ('ordinal','requested_encoding','status','headers','wire_bytes','decoded_bytes','elapsed_ns','error','decode_error')} for r in results]))

if __name__=='__main__':asyncio.run(main())
```
