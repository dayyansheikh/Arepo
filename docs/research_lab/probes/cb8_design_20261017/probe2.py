import json, re, urllib.request, urllib.parse, collections, time
from datetime import date, timedelta
BASE="https://gamma-api.polymarket.com/markets"
def get(p):
    req=urllib.request.Request(BASE+"?"+urllib.parse.urlencode(p), headers={"User-Agent":"arepo-research-lab/1"})
    with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read())
pat=re.compile(r"^(.*?) Up or Down on ([A-Z][a-z]+ \d{1,2})\??$")
cnt=collections.Counter(); days=collections.Counter(); desc=collections.Counter(); other=collections.Counter(); capped=0; neg=0
d=date(2026,4,13); end=date(2026,8,10)
while d<end:
    p={"closed":"true","limit":100,"end_date_min":f"{d}T15:55:00Z","end_date_max":f"{d}T16:05:00Z"}
    try: rows=get(p)
    except Exception as e: print(d,"ERR",e); rows=[]
    if len(rows)>=100: capped+=1
    for m in rows:
        q=m.get("question") or ""
        mm=pat.match(q)
        if not mm: other[re.sub(r"\d+","#",q)[:50]]+=1; continue
        cnt[mm.group(1)]+=1; days[str(d)]+=1
        if m.get("negRisk"): neg+=1
        t=(m.get("description") or "")
        desc[("binance" in t.lower(), bool(re.search(r"1[- ]?minute|1m\b", t, re.I)), bool(re.search(r"12:00\s*(PM)?\s*ET", t)), bool(re.search(r"50-50|50/50", t)))]+=1
    d+=timedelta(days=1); time.sleep(0.25)
print("daily-by-asset",dict(cnt)); print("days with >=1",len(days), "min/max per day", min(days.values()) if days else 0, max(days.values()) if days else 0)
print("capped windows",capped,"negRisk",neg); print("desc flags (binance,1min,12:00ET,tie):",dict(desc)); print("other top",other.most_common(6))
