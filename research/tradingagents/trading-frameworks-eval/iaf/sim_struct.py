"""Deeper STRUCTURE stops (Elliott / fib leg), no targets: exit only on stop, else mark at 2026-10-07 close.
Strict PIT: ATR14 (Wilder) and the 2xATR14 zigzag are causal (pivot list truncated at any bar == full-run pivots with
confirmation <= that bar; verified 960/960 in sim_fib). Initial structure = pivots CONFIRMED on/before rule_bar_date.
LONG leg = last confirmed swing HIGH H and the confirmed swing LOW L (origin, wave-1 start / last higher-low) before it.
  (a) fib786 : H - 0.786*(H-L) - 0.5*ATR      (b) origin05: L - 0.5*ATR      (c) origin10: L - 1.0*ATR
  (d) strail : starts at (b); on each later bar the stop is raised to (newly confirmed swing-LOW price - 0.5*ATR at its
               confirmation bar) if higher; a pivot is usable only from the bar AFTER its confirmation bar.
SHORT mirrored (swing LOW end, swing HIGH origin, lower-high pivots).  ATR for buffers = ATR as of rule bar for a-c.
If the structure level is not beyond the entry fill (entry already through it), fall back to the next deeper confirmed
pivot beyond entry (same buffer); if none, the setup gets no structure stop for that variant (counted, excluded).
Modes: 'c' close-based (checks from close of e+2, fill at close), 'i' intraday (from e+1, Low/High vs level, fill at
worse of open and level).  Output also atr_pct (ATR/entry) so fixed-ATR/chandelier stop distances can be reported."""
import numpy as np, pandas as pd
OUT='/workspace/trading-frameworks-eval/iaf/'
s=open(OUT+'sim_fib.py').read(); exec(s[s.index('def atr14'):s.index('def clock')])
D=pd.read_pickle(OUT+'setups_prepared.pkl'); F=pd.read_pickle(OUT+'frames.pkl')
COST={'stock':dict(fee=0.02, slip=0.05), 'crypto':dict(fee=0.10, slip=0.10)}
def clock(asset):
    if asset=='crypto': cal=pd.date_range('2026-05-01','2026-10-07',freq='D'); opens=cal
    else:
        allidx=sorted(set().union(*[set(x.index) for (t,c),x in F.items() if not c]))
        cal=pd.DatetimeIndex([d for d in allidx if d>=pd.Timestamp('2026-05-01')]); opens=cal+pd.Timedelta(hours=13,minutes=30)
    return cal,np.array(opens,dtype='datetime64[ns]')
rows=[]; meta=[]; cache={}
for asset in ('stock','crypto'):
    cal,opens=clock(asset); c=COST[asset]; fee=c['fee']/100; sl=c['slip']/100
    S=D[D.has_data&(D.asset==asset)&D.direction.isin(['LONG','SHORT'])&D.decision_utc.notna()]
    for _,r in S.iterrows():
        k=int(np.searchsorted(opens,np.datetime64(r.decision_utc),side='left'))
        if k>=len(cal)-1: continue
        key=(r.ticker,asset=='crypto')
        if key not in cache:
            raw=F[key].dropna(subset=['Close']); h,l,cc=raw.High.values,raw.Low.values,raw.Close.values
            a=atr14(h,l,cc); piv=zigzag(h,l,a,2.0) if len(a) else []
            cache[key]=(raw.index,a,piv)
        ridx,a,piv=cache[key]
        R=int(np.searchsorted(ridx,pd.Timestamp(r.rule_bar_date),side='right'))-1
        if R<14 or not np.isfinite(a[R]): continue
        A=a[R]
        x=F[key].reindex(cal); x['Close']=x.Close.ffill().bfill()
        for col in ('Open','High','Low'): x[col]=x[col].fillna(x.Close)
        O,H,L,C=x.Open.values,x.High.values,x.Low.values,x.Close.values
        sgn=1 if r.direction=='LONG' else -1; ein=O[k]*(1+sgn*sl)
        known=[p for p in piv if p[3]<=R]
        end_kind='H' if sgn==1 else 'L'; org_kind='L' if sgn==1 else 'H'
        idx=[j for j,p in enumerate(known) if p[0]==end_kind]
        meta.append(dict(setup_id=r.setup_id,atr_pct=A/ein*100))
        if not idx or idx[-1]==0: continue
        e_=known[idx[-1]][1]; o=known[idx[-1]-1][1]; rng=e_-o
        origins=[p[1] for p in known if p[0]==org_kind]   # all confirmed same-side pivots (for fallback deeper)
        def beyond(level,buf):
            lv=level-sgn*buf*A
            if sgn*(ein-lv)>0: return lv,0
            deeper=sorted([p for p in origins if sgn*(ein-(p-sgn*buf*A))>0], key=lambda p: -sgn*p)  # nearest deeper first
            return ((deeper[0]-sgn*buf*A),1) if deeper else (None,1)
        init={'fib786':beyond(e_-0.786*rng,0.5),'origin05':beyond(o,0.5),'origin10':beyond(o,1.0)}
        init['strail']=init['origin05']
        # future pivots for the trailing variant, mapped to calendar: usable from first cal bar strictly after confirm date
        fut=[(ridx[p[3]],p[1]-sgn*0.5*a[p[3]]) for p in piv if p[3]>R and p[0]==org_kind and np.isfinite(a[p[3]])]
        for pol,(st0,fb) in init.items():
            if st0 is None: continue
            for mode in ('c','i'):
                stop=st0; exit_k=len(cal)-1; ex=C[-1]; status='open@end'; fi=0; nraise=0
                for j in range(k+1,len(cal)):
                    if pol=='strail':
                        while fi<len(fut) and fut[fi][0]<cal[j]:
                            if sgn*(fut[fi][1]-stop)>0: stop=fut[fi][1]; nraise+=1
                            fi+=1
                    if mode=='c':
                        if j<k+2: continue
                        if sgn*(C[j]-stop)<=0: exit_k=j; ex=C[j]; status='stopped'; break
                    else:
                        if (L[j]<=stop) if sgn==1 else (H[j]>=stop):
                            ex=min(O[j],stop) if sgn==1 else max(O[j],stop); exit_k=j; status='stopped'; break
                exf=ex*(1-sgn*sl)
                ret=(exf*(1-fee))/(ein*(1+fee))-1 if sgn==1 else (ein*(1-fee)-exf*(1+fee))/(ein*(1+fee))
                rows.append(dict(setup_id=r.setup_id,asset=asset,direction=r.direction,policy=f'st_{pol}_{mode}',entry_date=cal[k],exit_date=cal[exit_k],
                                 entry_fill=ein,exit_fill=exf,status=status,ret_net=ret,days=int(exit_k-k),stop_dist=abs(ein-st0)/ein*100,fallback=fb,raises=nraise))
Rr=pd.DataFrame(rows); Rr.to_csv(OUT+'sim_struct_trades.csv',index=False); pd.DataFrame(meta).to_csv(OUT+'struct_atr_pct.csv',index=False)
print(Rr.groupby(['asset','direction','policy']).agg(N=('ret_net','size'),mean=('ret_net','mean'),stopped=('status',lambda s:(s=='stopped').mean()),sd=('stop_dist','median'),fb=('fallback','mean')).round(3).to_string())
