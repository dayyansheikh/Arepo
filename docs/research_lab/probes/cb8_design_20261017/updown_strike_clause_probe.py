import json, re, urllib.request, urllib.parse, time, collections
from datetime import date, timedelta, datetime
def get(p):
    req=urllib.request.Request("https://gamma-api.polymarket.com/markets?"+urllib.parse.urlencode(p), headers={"User-Agent":"arepo-research-lab/1"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())
Q=re.compile(r"^(Bitcoin|Ethereum|Solana|XRP|Dogecoin|HYPE|BNB) Up or Down on [A-Z][a-z]+ \d{1,2}\??$")
UP=re.compile(r'resolve to "Up" if the "Close" price for the Binance 1 minute candle for ([A-Z]+/USDT) ([A-Z][a-z]{2} \d{1,2} \'\d{2}) 12:00 in the ET timezone \(noon\) is lower than the final "Close" price for the ([A-Z][a-z]{2} \d{1,2} \'\d{2}) 12:00 ET candle')
DN=re.compile(r'resolve to "Down" if the "Close" price for the Binance 1 minute candle for ([A-Z]+/USDT) ([A-Z][a-z]{2} \d{1,2} \'\d{2}) 12:00 in the ET timezone \(noon\) is higher than the final "Close" price for the ([A-Z][a-z]{2} \d{1,2} \'\d{2}) 12:00 ET candle')
def pd(s): return datetime.strptime(s.replace("'", ""), "%b %d %y").date()
c=collections.Counter()
d=date(2026,4,13)
while d<date(2026,8,10):
    off=0
    while True:
        b=get({"closed":"true","limit":100,"offset":off,"end_date_min":f"{d}T15:59:00Z","end_date_max":f"{d}T16:01:00Z"})
        for m in b:
            if not Q.match(m.get("question") or ""): continue
            t=m.get("description") or ""; u=UP.search(t); w=DN.search(t)
            if not (u and w): c["no_match"]+=1; continue
            ok = u.groups()==w.groups() and pd(u.group(2))==d-timedelta(days=1) and pd(u.group(3))==d
            c["ok" if ok else "date_or_mirror_mismatch"]+=1
        if len(b)<100: break
        off+=100; time.sleep(0.2)
    d+=timedelta(days=1); time.sleep(0.2)
print(dict(c))
