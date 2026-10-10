"""Independent pandas replay with the SAME timing/cost conventions as run_iaf.py, used to
(1) cross-check IAF's event engine numbers and (2) cover SHORT setups, which IAF v8 cannot simulate.
Conventions: entry = Open of entry bar e (+slippage); stops evaluated on daily closes starting at close of e+2
(mirrors IAF: stop attached after fill is observed, first check one bar later); exit at the triggering close
(-slippage); trailing high-water mark starts at close of bar e; hold = mark-to-market at 2026-10-07 close."""
import numpy as np, pandas as pd
OUT='/workspace/trading-frameworks-eval/iaf/'
D=pd.read_pickle(OUT+'setups_prepared.pkl'); F=pd.read_pickle(OUT+'frames.pkl')
COST={'stock':dict(fee=0.02, slip=0.05), 'crypto':dict(fee=0.10, slip=0.10)}
POLS={'hold':None,'fsetup':('setup',False),'f8':(8,False),'t5':(5,True),'t8':(8,True),'t12':(12,True)}
def clock(asset):
    if asset=='crypto':
        cal=pd.date_range('2026-05-01','2026-10-07',freq='D'); opens=cal
    else:
        allidx=sorted(set().union(*[set(x.index) for (t,c),x in F.items() if not c]))
        cal=pd.DatetimeIndex([d for d in allidx if d>=pd.Timestamp('2026-05-01')]); opens=cal+pd.Timedelta(hours=13,minutes=30)
    return cal, np.array(opens,dtype='datetime64[ns]')
rows=[]
for asset in ('stock','crypto'):
    cal,opens=clock(asset); c=COST[asset]; fee=c['fee']/100; sl=c['slip']/100
    S=D[D.has_data & (D.asset==asset) & D.direction.isin(['LONG','SHORT']) & D.decision_utc.notna()]
    for _,r in S.iterrows():
        k=int(np.searchsorted(opens,np.datetime64(r.decision_utc),side='left'))
        if k>=len(cal)-1: continue
        x=F[(r.ticker,asset=='crypto')].reindex(cal); x['Close']=x.Close.ffill().bfill()
        for col in ('Open','High','Low'): x[col]=x[col].fillna(x.Close)
        sgn=1 if r.direction=='LONG' else -1
        O=x.Open.values; C=x.Close.values
        ein=O[k]*(1+sgn*sl)
        for pol,spec in POLS.items():
            exit_k=len(cal)-1; ex=C[-1]; status='open@end'
            if spec is not None:
                p,trail=spec
                if p=='setup':
                    if pd.isna(r.stop) or sgn*(ein-r.stop)<=0: level=None
                    else: level=r.stop
                else: level=ein*(1-sgn*p/100)
                ext=C[k]
                if level is not None or trail:
                    for j in range(k+2,len(cal)):
                        if trail:
                            lv=ext*(1-sgn*p/100)
                            if sgn*(C[j]-lv)<=0: exit_k=j; ex=C[j]; status='stopped'; break
                            ext=max(ext,C[j]) if sgn==1 else min(ext,C[j])
                        else:
                            if sgn*(C[j]-level)<=0: exit_k=j; ex=C[j]; status='stopped'; break
            exf=ex*(1-sgn*sl)
            if sgn==1: ret=(exf*(1-fee))/(ein*(1+fee))-1
            else: ret=(ein*(1-fee)-exf*(1+fee))/(ein*(1+fee))   # short: proceeds - cover cost, on entry notional (no borrow fee modelled)
            rows.append(dict(setup_id=r.setup_id,asset=asset,direction=r.direction,policy=pol,entry_date=cal[k],exit_date=cal[exit_k],
                             entry_fill=ein,exit_fill=exf,status=status,ret_net=ret,days=int(exit_k-k)))
R=pd.DataFrame(rows); R.to_csv(OUT+'sim_trades.csv',index=False); print(R.groupby(['asset','direction','policy']).ret_net.agg(['count','mean','median']).round(4))
