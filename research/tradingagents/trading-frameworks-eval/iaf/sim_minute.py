"""Exact-minute entry variant of sim.py. For setups with exact/schedule/ui_log times, entry = Alpaca 1-min bar open at
the first tradable minute >= decision time (stocks: regular session only), +slippage. Exit machinery identical to sim.py
(daily closes, stop checks from close of entry-day+2, trailing high-water from entry-day close, hold = 2026-10-07 close).
Benchmarks: SPY / sector ETF / BTC / ETH entered at the SAME minute (Alpaca 1-min open), exited at the same daily close."""
import os, requests, numpy as np, pandas as pd, time
OUT='/workspace/trading-frameworks-eval/iaf/'
D=pd.read_pickle(OUT+'setups_prepared.pkl'); F=pd.read_pickle(OUT+'frames.pkl'); B=pd.read_pickle(OUT+'bench_yf.pkl')
M=pd.read_csv(OUT+'minute_entries.csv'); M=M[M.minute_open.notna()]
COST={'stock':dict(fee=0.02, slip=0.05), 'crypto':dict(fee=0.10, slip=0.10)}
POLS={'hold':None,'fsetup':('setup',False),'f8':(8,False),'t5':(5,True),'t8':(8,True),'t12':(12,True)}
SECMAP={'Technology':'XLK','Financial Services':'XLF','Energy':'XLE','Healthcare':'XLV','Consumer Cyclical':'XLY','Consumer Defensive':'XLP','Industrials':'XLI','Basic Materials':'XLB','Utilities':'XLU','Real Estate':'XLRE','Communication Services':'XLC'}
H={'APCA-API-KEY-ID':os.environ['ALPACA_API_KEY_ID'],'APCA-API-SECRET-KEY':os.environ['ALPACA_API_SECRET_KEY']}
X=M.merge(D,on='setup_id'); X['emin']=pd.to_datetime(X.entry_minute_utc,utc=True)
# ---- benchmark minute opens (cached)
bc=OUT+'bench_minute.csv'
need=set()
for _,r in X.iterrows():
    if r.asset=='stock':
        need.add(('SPY',r.entry_minute_utc))
        if SECMAP.get(r.sector): need.add((SECMAP[r.sector],r.entry_minute_utc))
    else: need.add(('BTC/USD',r.entry_minute_utc)); need.add(('ETH/USD',r.entry_minute_utc))
have=pd.read_csv(bc) if os.path.exists(bc) else pd.DataFrame(columns=['sym','minute','open'])
got=set(zip(have.sym,have.minute)); rows=[]
for sym,mn in sorted(need-got):
    t=pd.Timestamp(mn)
    if '/' in sym: url='https://data.alpaca.markets/v1beta3/crypto/us/bars'; p=dict(symbols=sym,timeframe='1Min',start=mn,end=(t+pd.Timedelta(minutes=30)).isoformat().replace('+00:00','Z'),limit=5)
    else: url='https://data.alpaca.markets/v2/stocks/bars'; p=dict(symbols=sym,timeframe='1Min',start=mn,end=(t+pd.Timedelta(minutes=30)).isoformat().replace('+00:00','Z'),limit=5,feed='sip',adjustment='split')
    for a in range(5):
        try: rr=requests.get(url,headers=H,params=p,timeout=60)
        except requests.RequestException: rr=None; time.sleep(5*(a+1)); continue
        if rr.status_code==429: time.sleep(3*(a+1)); continue
        break
    bars=(rr.json().get('bars') or {}) if (rr is not None and rr.status_code==200) else {}
    b=list(bars.values())[0] if bars else []
    rows.append(dict(sym=sym,minute=mn,open=b[0]['o'] if b else np.nan))
have=pd.concat([have,pd.DataFrame(rows)]); have.to_csv(bc,index=False)
BM={(s,m):o for s,m,o in zip(have.sym,have.minute,have.open)}
def bclose(t,day_exit):
    if t in ('BTC-USD','ETH-USD'): s=F[(t,True)].Close
    else: s=B[t].Close.dropna()
    s.index=pd.to_datetime(s.index); s=s[s.index<=day_exit]
    return s.iloc[-1] if len(s) else np.nan
def clock(asset):
    if asset=='crypto': cal=pd.date_range('2026-05-01','2026-10-07',freq='D')
    else:
        allidx=sorted(set().union(*[set(x.index) for (t,c),x in F.items() if not c])); cal=pd.DatetimeIndex([d for d in allidx if d>=pd.Timestamp('2026-05-01')])
    return cal
out=[]
for asset in ('stock','crypto'):
    cal=clock(asset); c=COST[asset]; fee=c['fee']/100; sl=c['slip']/100
    for _,r in X[X.asset==asset].iterrows():
        day=r.emin.tz_convert(None).normalize()
        k=int(np.searchsorted(cal,day,side='left'))
        if k>=len(cal)-1 or cal[k]!=day: continue
        x=F[(r.ticker,asset=='crypto')].reindex(cal); x['Close']=x.Close.ffill().bfill()
        sgn=1 if r.direction=='LONG' else -1; C=x.Close.values
        ein=r.minute_open*(1+sgn*sl)
        for pol,spec in POLS.items():
            exit_k=len(cal)-1; ex=C[-1]; status='open@end'
            if spec is not None:
                p,trail=spec
                level=(None if (pd.isna(r.stop) or sgn*(ein-r.stop)<=0) else r.stop) if p=='setup' else ein*(1-sgn*p/100)
                ext=C[k]
                if level is not None or trail:
                    for j in range(k+2,len(cal)):
                        if trail:
                            lv=ext*(1-sgn*p/100)
                            if sgn*(C[j]-lv)<=0: exit_k=j; ex=C[j]; status='stopped'; break
                            ext=max(ext,C[j]) if sgn==1 else min(ext,C[j])
                        elif sgn*(C[j]-level)<=0: exit_k=j; ex=C[j]; status='stopped'; break
            exf=ex*(1-sgn*sl)
            ret=(exf*(1-fee))/(ein*(1+fee))-1 if sgn==1 else (ein*(1-fee)-exf*(1+fee))/(ein*(1+fee))
            d=dict(setup_id=r.setup_id,asset=asset,direction=r.direction,policy=pol,entry_minute=r.entry_minute_utc,entry_date=cal[k],exit_date=cal[exit_k],entry_fill=ein,status=status,ret_net=ret)
            bl=[('spy','SPY','SPY'),('sector',SECMAP.get(r.sector),SECMAP.get(r.sector))] if asset=='stock' else [('btc','BTC/USD','BTC-USD'),('eth','ETH/USD','ETH-USD')]
            for nm,ms,ds in bl:
                o=BM.get((ms,r.entry_minute_utc),np.nan) if ms else np.nan
                d['b_'+nm]=(bclose(ds,cal[exit_k])/o-1) if ms and np.isfinite(o) else np.nan
            out.append(d)
R=pd.DataFrame(out)
if 'b_btc' in R: R['b_basket']=(R.b_btc+R.b_eth)/2
sg=np.where(R.direction=='SHORT',-1,1)
for b in ['spy','sector','btc','eth','basket']:
    if 'b_'+b in R: R['x_'+b]=R.ret_net-sg*R['b_'+b]
R.to_csv(OUT+'sim_minute_trades.csv',index=False); print(len(R),'rows'); print(R.groupby(['asset','direction','policy']).ret_net.agg(['count','mean','median']).round(4).to_string())
