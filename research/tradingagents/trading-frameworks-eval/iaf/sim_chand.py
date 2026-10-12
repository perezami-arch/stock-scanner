"""ATR chandelier TRAILING stops, independent replay (same setups / PIT entry / costs / clock as sim.py & sim_fib.py).
ATR14 = Wilder ATR on the ticker's full daily OHLC; value used on day j is ATR as of the PREVIOUS completed bar (j-1),
and the reference extreme is the highest (long) / lowest (short) CLOSE from the entry-day close through j-1.
  long level_j  = max(C[k..j-1]) - K*ATR[j-1];  short level_j = min(C[k..j-1]) + K*ATR[j-1]
'c' close-based (IAF-consistent): first check at close of k+2; exit if C[j] crosses level_j, fill at C[j].
'i' intraday: from bar k+1; exit if Low[j]<=level (long) / High[j]>=level (short); fill at the worse of Open[j] and level.
Open trades are marked to market at the 2026-10-07 close (status 'open@end')."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import numpy as np, pandas as pd
OUT=(_SCANNER_ROOT + '/trading-frameworks-eval/iaf/')
s=open(OUT+'sim_fib.py').read(); exec(s[s.index('def atr14'):s.index('def zigzag')])
D=pd.read_pickle(OUT+'setups_prepared.pkl'); F=pd.read_pickle(OUT+'frames.pkl')
COST={'stock':dict(fee=0.02, slip=0.05), 'crypto':dict(fee=0.10, slip=0.10)}
def clock(asset):
    if asset=='crypto': cal=pd.date_range('2026-05-01','2026-10-07',freq='D'); opens=cal
    else:
        allidx=sorted(set().union(*[set(x.index) for (t,c),x in F.items() if not c]))
        cal=pd.DatetimeIndex([d for d in allidx if d>=pd.Timestamp('2026-05-01')]); opens=cal+pd.Timedelta(hours=13,minutes=30)
    return cal,np.array(opens,dtype='datetime64[ns]')
rows=[]
for asset in ('stock','crypto'):
    cal,opens=clock(asset); c=COST[asset]; fee=c['fee']/100; sl=c['slip']/100
    S=D[D.has_data&(D.asset==asset)&D.direction.isin(['LONG','SHORT'])&D.decision_utc.notna()]
    atr_cache={}
    for _,r in S.iterrows():
        k=int(np.searchsorted(opens,np.datetime64(r.decision_utc),side='left'))
        if k>=len(cal)-1: continue
        key=(r.ticker,asset=='crypto'); raw=F[key].dropna(subset=['Close'])
        if key not in atr_cache:
            a=pd.Series(atr14(raw.High.values,raw.Low.values,raw.Close.values),index=raw.index)
            atr_cache[key]=a.reindex(cal.union(raw.index)).ffill().reindex(cal).values
        A=atr_cache[key]
        if not np.isfinite(A[k-1] if k>0 else np.nan): continue
        x=F[key].reindex(cal); x['Close']=x.Close.ffill().bfill()
        for col in ('Open','High','Low'): x[col]=x[col].fillna(x.Close)
        O,H,L,C=x.Open.values,x.High.values,x.Low.values,x.Close.values
        sgn=1 if r.direction=='LONG' else -1; ein=O[k]*(1+sgn*sl)
        for K in (2,3,4):
            for mode in ('c','i'):
                exit_k=len(cal)-1; ex=C[-1]; status='open@end'; ext=C[k]
                if mode=='c' and k+1<len(cal): ext=max(ext,C[k+1]) if sgn==1 else min(ext,C[k+1])   # include close of e+1 in the extreme (no check on e+1)
                for j in range(k+2 if mode=='c' else k+1, len(cal)):
                    lv=ext-sgn*K*A[j-1]
                    if mode=='c':
                        if sgn*(C[j]-lv)<=0: exit_k=j; ex=C[j]; status='stopped'; break
                    else:
                        if (L[j]<=lv) if sgn==1 else (H[j]>=lv):
                            ex=min(O[j],lv) if sgn==1 else max(O[j],lv); exit_k=j; status='stopped'; break
                    ext=max(ext,C[j]) if sgn==1 else min(ext,C[j])
                exf=ex*(1-sgn*sl)
                ret=(exf*(1-fee))/(ein*(1+fee))-1 if sgn==1 else (ein*(1-fee)-exf*(1+fee))/(ein*(1+fee))
                rows.append(dict(setup_id=r.setup_id,asset=asset,direction=r.direction,policy=f'chand{K}_{mode}',entry_date=cal[k],exit_date=cal[exit_k],
                                 entry_fill=ein,exit_fill=exf,status=status,ret_net=ret,days=int(exit_k-k)))
R=pd.DataFrame(rows); R.to_csv(OUT+'sim_chand_trades.csv',index=False)
print(R.groupby(['asset','direction','policy']).agg(N=('ret_net','size'),mean=('ret_net','mean'),stopped=('status',lambda s:(s=='stopped').mean())).round(4).to_string())
