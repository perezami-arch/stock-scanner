import json,urllib.request,time,datetime as dt
Q={'BP':('backpack','2026-09-25'),'U':('union-2','2026-08-04'),'BLORB':('blorb','2026-09-20'),'CAP':('cap-4','2026-08-14'),'APR':('apriori','2026-08-12'),'COW':('cow-protocol','2026-08-15'),'BOBO':('bobo-coin-2','2026-08-09'),'BOBO_b':('bobo-coin','2026-08-09'),'BOBO_c':('bobo','2026-08-09')}
out={}
for s,(cid,d) in Q.items():
    try:
        u=f"https://api.coingecko.com/api/v3/coins/{cid}/market_chart?vs_currency=usd&days=90&interval=daily"
        j=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=30))
        t0=dt.datetime.fromisoformat(d).replace(tzinfo=dt.timezone.utc).timestamp()*1000
        p=[x for x in j['prices'] if x[0]<=t0+86400e3]; m=[x for x in j['market_caps'] if x[0]<=t0+86400e3]
        out[s]=dict(id=cid,date=d,price=p[-1][1] if p else None,mcap=m[-1][1] if m else None)
    except Exception as e: out[s]={'id':cid,'err':str(e)}
    print(s,out[s]); time.sleep(25)
json.dump(out,open('auto/cg_mcap.json','w'),indent=1)
