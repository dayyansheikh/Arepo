import json,time,httpx
S=[l.strip() for l in open("/tmp/samp.txt")]
cl=httpx.Client(timeout=60,headers={"User-Agent":"arepo-research-lab/1","Accept-Encoding":"gzip"})
OI="https://data-api.polymarket.com/oi"; HO="https://data-api.polymarket.com/holders"
reqs=0
def get(url,params):
    global reqs
    for k in range(4):
        reqs+=1
        r=cl.get(url,params=params)
        if r.status_code==200: time.sleep(0.7); return 200,r.json()
        if r.status_code==400: return 400,None
        time.sleep(10*(k+1))
    return r.status_code,None
oi={}
def oib(ids):
    r=cl.get(OI,params={"market":",".join(ids)}); global reqs; reqs+=1; time.sleep(0.7)
    if r.status_code==200:
        for x in r.json(): oi[x["market"].lower()]=x["value"]
    elif r.status_code==403 and len(ids)>1: oib(ids[:len(ids)//2]); oib(ids[len(ids)//2:])
    else: raise SystemExit(("fail",r.status_code,len(ids)))
for i in range(0,600,15): oib(S[i:i+15])
absent=[c for c in S if c.lower() not in oi]; present=[c for c in S if c.lower() in oi]
small=sorted([c for c in present if oi[c.lower()]<1000],key=lambda c:oi[c.lower()])
print("sampled",len(S),"absent",len(absent),"present",len(present),"present<1000",len(small),"present==0",sum(1 for c in present if oi[c.lower()]==0))
print("smallest present",[round(oi[c.lower()],2) for c in small[:10]])
def hold(c):
    st,d=get(HO,{"market":c,"limit":20})
    if st!=200: return ("http",st)
    rows=pos=0;tot=0.0
    if d is None: return ("null",)
    for t in d:
        for x in t.get("holders",[]):
            rows+=1;a=float(x.get("amount") or 0);tot+=a;pos+=a>0
    return ("ok",rows,pos,round(tot,2))
A=absent[:40]
rA=[hold(c) for c in A]
print("ABSENT holders n",len(A),"http_fail",sum(r[0]!="ok" for r in rA),"empty",sum(r[0]=="ok" and r[1]==0 for r in rA),"with_positive",sum(r[0]=="ok" and r[2]>0 for r in rA),"max_top20_total",max([r[3] for r in rA if r[0]=="ok"] or [0]))
print("ABSENT nonempty detail",[r for r in rA if r[0]=="ok" and r[2]>0][:8])
sA=[get(OI,{"market":c}) for c in A[:15]]
print("ABSENT single /oi n",len(sA),"empty list",sum(s[0]==200 and s[1]==[] for s in sA),"other",[s for s in sA if not(s[0]==200 and s[1]==[])][:3])
P=small[:10]; rP=[hold(c) for c in P]
print("PRESENT small n",len(P),"oi",[round(oi[c.lower()],2) for c in P],"holders",[r[:3] for r in rP])
print("requests",reqs)
json.dump({"absent":A,"present_small":P},open("/tmp/v4_ids.json","w"))
