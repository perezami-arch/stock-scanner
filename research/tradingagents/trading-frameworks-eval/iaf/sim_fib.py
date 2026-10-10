"""Fibonacci-structure exits vs ATR stops, same setups / PIT cutoffs / entry / costs as sim.py.
PIT: ATR14 (Wilder) and ATR-threshold zigzag are computed ONLY on bars <= rule_bar_date (last bar complete
at the info cutoff, i.e. the bar before the alert). A pivot is usable only if its CONFIRMATION bar (the bar on
which price had reversed from the extreme by >= Z*ATR14) is <= rule_bar_date. Unconfirmed current extremes ignored.
Leg: LONG  -> most recent confirmed swing HIGH H and the confirmed swing LOW L immediately before it (impulse L->H).
     SHORT -> most recent confirmed swing LOW and the swing HIGH before it (impulse H->L).
Stop: the first retracement (0.382/0.5/0.618/0.786) beyond the entry fill, minus (plus for shorts) BUF*ATR;
      if entry is already beyond 0.786 -> the swing origin (1.0) -/+ BUF*ATR.
Targets: extensions 1.272 / 1.618 / 2.618 of the leg measured from its origin (L + r*(H-L)); targets already
      behind the entry are skipped (next one used); none left -> no target (stop or mark-to-market at end).
Variants: fib_T1/T2/T3 = full exit at that target; fib_scale = 1/3 off at each target (stop unchanged).
          atr2/atr3 = fixed stop at entry -/+ k*ATR14 (ATR as of the rule bar), no target.
Two execution modes: 'c' = close-based like IAF (checks start at close of e+2, fill at that close);
          'i' = intraday OHLC (from bar e+1: stop if Low<=stop fills at min(Open,stop); target if High>=target
          fills at max(Open,target); if both in one bar the STOP is assumed first = conservative)."""
import numpy as np, pandas as pd, sys
OUT='/workspace/trading-frameworks-eval/iaf/'
D=pd.read_pickle(OUT+'setups_prepared.pkl'); F=pd.read_pickle(OUT+'frames.pkl')
COST={'stock':dict(fee=0.02, slip=0.05), 'crypto':dict(fee=0.10, slip=0.10)}
Z=float(sys.argv[1]) if len(sys.argv)>1 else 2.0   # zigzag reversal threshold in ATRs
BUF=0.5; RET=[0.382,0.5,0.618,0.786]; EXT=[1.272,1.618,2.618]
def atr14(h,l,c):
    if len(c)<15: return np.full(len(c),np.nan)
    pc=np.r_[np.nan,c[:-1]]; tr=np.nanmax(np.c_[h-l,np.abs(h-pc),np.abs(l-pc)],axis=1); tr[0]=h[0]-l[0]
    a=np.full(len(c),np.nan)
    if len(c)<15: return a
    a[13]=tr[:14].mean()
    for i in range(14,len(c)): a[i]=(a[i-1]*13+tr[i])/14
    return a
def zigzag(h,l,a,z):
    """returns list of (kind, price, pivot_idx, confirm_idx); kind 'H' or 'L'. Only confirmed pivots."""
    piv=[]; i0=14
    if len(h)<=i0+1: return piv
    d=0; hi=h[i0]; hi_i=i0; lo=l[i0]; lo_i=i0
    for i in range(i0+1,len(h)):
        th=z*a[i]
        if d>=0:
            if h[i]>hi: hi,hi_i=h[i],i
            if d==0 and l[i]<lo: lo,lo_i=l[i],i
        if d<=0:
            if l[i]<lo: lo,lo_i=l[i],i
            if d==0 and h[i]>hi: hi,hi_i=h[i],i
        if d>=0 and hi-l[i]>=th and hi_i<i and (d==1 or hi_i>lo_i):
            piv.append(('H',hi,hi_i,i)); d=-1; lo,lo_i=l[i],i; continue
        if d<=0 and h[i]-lo>=th and lo_i<i and (d==-1 or lo_i>hi_i):
            piv.append(('L',lo,lo_i,i)); d=1; hi,hi_i=h[i],i; continue
    return piv
def clock(asset):
    if asset=='crypto': cal=pd.date_range('2026-05-01','2026-10-07',freq='D'); opens=cal
    else:
        allidx=sorted(set().union(*[set(x.index) for (t,c),x in F.items() if not c]))
        cal=pd.DatetimeIndex([d for d in allidx if d>=pd.Timestamp('2026-05-01')]); opens=cal+pd.Timedelta(hours=13,minutes=30)
    return cal,np.array(opens,dtype='datetime64[ns]')
rows=[]; info=[]
for asset in ('stock','crypto'):
    cal,opens=clock(asset); c=COST[asset]; fee=c['fee']/100; sl=c['slip']/100
    S=D[D.has_data&(D.asset==asset)&D.direction.isin(['LONG','SHORT'])&D.decision_utc.notna()]
    for _,r in S.iterrows():
        k=int(np.searchsorted(opens,np.datetime64(r.decision_utc),side='left'))
        if k>=len(cal)-1: continue
        raw=F[(r.ticker,asset=='crypto')]
        hist=raw[raw.index<=pd.Timestamp(r.rule_bar_date)].dropna(subset=['Close'])
        x=raw.reindex(cal); x['Close']=x.Close.ffill().bfill()
        for col in ('Open','High','Low'): x[col]=x[col].fillna(x.Close)
        sgn=1 if r.direction=='LONG' else -1
        O,H,L,C=x.Open.values,x.High.values,x.Low.values,x.Close.values
        ein=O[k]*(1+sgn*sl)
        h_,l_,c_=hist.High.values,hist.Low.values,hist.Close.values
        a=atr14(h_,l_,c_); A=a[-1] if len(a) else np.nan
        piv=zigzag(h_,l_,a,Z) if len(a) else []
        piv=[p for p in piv if p[3]<=len(h_)-1]          # confirmation bar <= rule bar (true by construction; kept explicit)
        leg=None
        want='H' if sgn==1 else 'L'
        idx=[j for j,p in enumerate(piv) if p[0]==want]
        if idx and idx[-1]>0:
            end=piv[idx[-1]]; org=piv[idx[-1]-1]; leg=(org[1],end[1])   # (origin price, end price)
        levels={}
        if np.isfinite(A):
            levels['atr2']=(ein-sgn*2*A,[]); levels['atr3']=(ein-sgn*3*A,[])
        if leg and np.isfinite(A):
            o,e_=leg; rng=e_-o            # long: o=L,e_=H (rng>0); short: o=H,e_=L (rng<0)
            rets=[e_-f*rng for f in RET]+[o]
            beyond=[lv for lv in rets if sgn*(ein-lv)>0]
            stop=(beyond[0] if beyond else o)-sgn*BUF*A
            tg=[o+f*rng for f in EXT]; tg=[t for t in tg if sgn*(t-ein)>0]
            for nm,ti in (('fib_T1',0),('fib_T2',1),('fib_T3',2)):
                levels[nm]=(stop,[tg[min(ti,len(tg)-1)]] if tg else [])
            levels['fib_scale']=(stop,tg)
            info.append(dict(setup_id=r.setup_id,leg_origin=o,leg_end=e_,stop=stop,targets=tg,atr=A,ein=ein,stop_dist_pct=abs(ein-stop)/ein*100))
        for pol,(stop,tgs) in levels.items():
            for mode in ('c','i'):
                parts=[]; rem=1.0; tq=list(tgs); frac=(1/len(tgs)) if (pol=='fib_scale' and tgs) else 1.0
                exit_k=len(cal)-1; status='open@end'
                j0=k+2 if mode=='c' else k+1
                for j in range(j0,len(cal)):
                    if mode=='c':
                        if sgn*(C[j]-stop)<=0: parts.append((rem,C[j])); rem=0; status='stopped'
                        else:
                            while tq and rem>1e-9 and sgn*(C[j]-tq[0])>=0:
                                q=min(frac,rem) if pol=='fib_scale' else rem; parts.append((q,C[j])); rem-=q; tq.pop(0); status='target'
                    else:
                        if sgn*(L[j] if sgn==1 else H[j]) <= sgn*stop:
                            fill=min(O[j],stop) if sgn==1 else max(O[j],stop); parts.append((rem,fill)); rem=0; status='stopped'
                        else:
                            while tq and rem>1e-9 and sgn*((H[j] if sgn==1 else L[j])-tq[0])>=0:
                                fill=max(O[j],tq[0]) if sgn==1 else min(O[j],tq[0])
                                q=min(frac,rem) if pol=='fib_scale' else rem; parts.append((q,fill)); rem-=q; tq.pop(0); status='target'
                    if rem<=1e-9: exit_k=j; break
                if rem>1e-9: parts.append((rem,C[-1]))
                ret=0.0
                for q,px in parts:
                    exf=px*(1-sgn*sl)
                    rr=(exf*(1-fee))/(ein*(1+fee))-1 if sgn==1 else (ein*(1-fee)-exf*(1+fee))/(ein*(1+fee))
                    ret+=q*rr
                rows.append(dict(setup_id=r.setup_id,asset=asset,direction=r.direction,policy=f'{pol}_{mode}',entry_date=cal[k],exit_date=cal[exit_k],
                                 entry_fill=ein,exit_fill=np.nan,status=status,ret_net=ret,days=int(exit_k-k)))
R=pd.DataFrame(rows); R.to_csv(OUT+'sim_fib_trades.csv',index=False); pd.DataFrame(info).to_csv(OUT+'fib_structure.csv',index=False)
print('setups with ATR:',R[R.policy=='atr2_c'].shape[0],' with fib leg:',R[R.policy=='fib_T1_c'].shape[0])
print(R.groupby(['asset','direction','policy']).ret_net.agg(['count','mean','median']).round(4).to_string())
