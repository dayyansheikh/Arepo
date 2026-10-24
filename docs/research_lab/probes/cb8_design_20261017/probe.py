import json, re, urllib.request, collections, time, sys
BASE="https://gamma-api.polymarket.com/markets"
def get(params):
    q="&".join(f"{k}={v}" for k,v in params.items())
    req=urllib.request.Request(BASE+"?"+q, headers={"User-Agent":"arepo-research-lab/1"})
    with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read())
# counts only: daily crypto "Up or Down on <Month> <d>" markets, by asset, end in pmxt window
pat=re.compile(r"^(.*?) Up or Down on ([A-Z][a-z]+ \d{1,2})\??$")
cnt=collections.Counter(); hours=collections.Counter(); desc=collections.Counter(); n=0; other=collections.Counter()
for tag in ["102127"]:
  off=0
  while True:
    rows=get({"tag_id":tag,"closed":"true","end_date_min":"2026-04-13T00:00:00Z","end_date_max":"2026-08-10T00:00:00Z","limit":100,"offset":off})
    if not rows: break
    for m in rows:
        n+=1
        q=m.get("question") or ""
        mm=pat.match(q)
        if not mm:
            other[re.sub(r"\d+","#",q)[:40]]+=1; continue
        cnt[mm.group(1)]+=1
        hours[(m.get("endDate") or "")[11:16]]+=1
        d=m.get("description") or ""
        desc[( "binance" in d.lower(), bool(re.search(r"1[- ]?minute|1m", d, re.I)), "12:00" in d and "ET" in d, "50-50" in d or "50/50" in d)]+=1
    off+=100
    if off>=3000: print("offset cap hit"); break
    time.sleep(0.3)
print("rows",n); print("daily by asset",dict(cnt)); print("endDate HH:MM",dict(hours)); print("desc flags (binance,1min,12:00ET,tie)",dict(desc))
print("other templates top", other.most_common(8))
