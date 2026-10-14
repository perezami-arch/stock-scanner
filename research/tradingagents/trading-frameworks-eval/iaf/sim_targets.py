"""4xATR stops + Fibonacci / Elliott profit targets (strict PIT; same 2xATR14 zigzag legs & setups as sim_struct.py).
LONG leg = last confirmed swing HIGH H1 + origin LOW L0 before it (pivots confirmed <= rule bar). Shorts mirrored.
Stops: 'fx' = fixed entry -/+ 4*ATR14(rule bar); 'ch' = chandelier: extreme close since entry -/+ 4*ATR14[j-1].
Targets: extensions L0 + r*(H1-L0), r in 1.272/1.618/2.618 (targets already behind entry skipped -> next; none -> no target).
 T1/T2/T3 = full exit at that target; TS = 1/3 at each of the 3; HY3/HY2 = 1/3 or 1/2 at 1.618, rest under chandelier 4xATR.
Elliott (EW): from the confirmed pivot sequence ending in a same-side-as-origin pivot:
  wave-5 if last 5 pivots L0,H1,L2,H3,L4 satisfy L2>L0, H3>H1, L4>H1 (no overlap): target = L4 + (H1-L0)
  else wave-3 if last 3 pivots L0,H1,L2 satisfy L2>L0: target = L2 + 1.618*(H1-L0)
  else no Elliott count (coverage reported). Target must be beyond entry, otherwise 'passed' (no target).
Modes: 'c' close-based (checks from close of e+2, stop before target on the same close, fills at close);
       'i' intraday (from e+1; stop if Low<=stop first (conservative), fill min(Open,stop); target if High>=tgt, fill max(Open,tgt)).
Also records hold-to-end return so 'money left on the table' after target exits can be measured."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import numpy as np, pandas as pd
OUT=(_SCANNER_ROOT + '/trading-frameworks-eval/iaf/')
s=open(OUT+'sim_fib.py').read(); exec(s[s.index('def atr14'):s.index('def clock')])
D=pd.read_pickle(OUT+'setups_prepared.pkl'); F=pd.read_pickle(OUT+'frames.pkl')
COST={'stock':dict(fee=0.02, slip=0.05), 'crypto':dict(fee=0.10, slip=0.10)}
EXT=[1.272,1.618,2.618]
def clock(asset):
    if asset=='crypto': cal=pd.date_range('2026-05-01','2026-10-07',freq='D'); opens=cal
    else:
        allidx=sorted(set().union(*[set(x.index) for (t,c),x in F.items() if not c]))
        cal=pd.DatetimeIndex([d for d in allidx if d>=pd.Timestamp('2026-05-01')]); opens=cal+pd.Timedelta(hours=13,minutes=30)
    return cal,np.array(opens,dtype='datetime64[ns]')
rows=[]; ew=[]; cache={}
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
            Acal=pd.Series(a,index=raw.index).reindex(cal.union(raw.index)).ffill().reindex(cal).values
            cache[key]=(raw.index,a,piv,Acal)
        ridx,a,piv,Acal=cache[key]
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
        if not idx or idx[-1]==0: continue
        e_=known[idx[-1]][1]; o=known[idx[-1]-1][1]; rng=e_-o
        ext=[t for t in [o+f*rng for f in EXT] if sgn*(t-ein)>0]
        allext=[o+f*rng for f in EXT]
        # Elliott count on the confirmed pivot list (must END with an origin-side pivot = wave-2 or wave-4 end)
        ewt=None; ewk='none'
        if known and known[-1][0]==org_kind:
            P=[p[1] for p in known]
            if len(P)>=5:
                L0,H1,L2,H3,L4=P[-5:]
                if sgn*(L2-L0)>0 and sgn*(H3-H1)>0 and sgn*(L4-H1)>0: ewt=L4+(H1-L0); ewk='wave5'
            if ewt is None and len(P)>=3:
                L0,H1,L2=P[-3:]
                if sgn*(L2-L0)>0: ewt=L2+1.618*(H1-L0); ewk='wave3'
        ew_status=ewk if (ewt is not None and sgn*(ewt-ein)>0) else (ewk+'_passed' if ewt is not None else 'none')
        ew.append(dict(setup_id=r.setup_id,ew=ew_status,ew_target=ewt,ein=ein))
        def tg_for(v):
            if v in ('T1','T2','T3'):
                want=allext[{'T1':0,'T2':1,'T3':2}[v]]
                cand=[t for t in ext if sgn*(t-want)>=0]   # chosen level, or next one further if already passed
                return [(cand[0],1.0)] if cand else []
            if v=='TS': return [(t,1/3) for t in ext] if ext else []
            if v in ('HY3','HY2'):
                cand=[t for t in ext if sgn*(t-allext[1])>=0]
                return [(cand[0],1/3 if v=='HY3' else 1/2)] if cand else []
            if v=='EW': return [(ewt,1.0)] if ew_status in ('wave3','wave5') else []
        combos=[(sv,v) for sv in ('fx','ch') for v in ('T1','T2','T3','TS','EW')]+[('ch','HY3'),('ch','HY2')]
        mark=(C[-1]*(1-sgn*sl)*(1-fee))/(ein*(1+fee))-1 if sgn==1 else (ein*(1-fee)-C[-1]*(1-sgn*sl)*(1+fee))/(ein*(1+fee))
        for sv,v in combos:
            tq=tg_for(v)
            for mode in ('c','i'):
                parts=[]; rem=1.0; q=list(tq); exk=len(cal)-1; status='open@end'; reached=False; first_tgt_k=None
                extc=C[k]; fxl=ein-sgn*4*A
                for j in range(k+1,len(cal)):
                    lv=fxl if sv=='fx' else extc-sgn*4*Acal[j-1]
                    if mode=='c':
                        if j>=k+2:
                            if sgn*(C[j]-lv)<=0: parts.append((rem,C[j])); rem=0; status='stopped'
                            else:
                                while q and rem>1e-9 and sgn*(C[j]-q[0][0])>=0:
                                    t,fr=q.pop(0); qq=min(fr,rem) if len(q) or fr<1 else rem
                                    parts.append((qq,C[j])); rem-=qq; reached=True; first_tgt_k=first_tgt_k or j
                                if rem<=1e-9: status='target'
                    else:
                        if (L[j]<=lv) if sgn==1 else (H[j]>=lv):
                            parts.append((rem,min(O[j],lv) if sgn==1 else max(O[j],lv))); rem=0; status='stopped'
                        else:
                            while q and rem>1e-9 and sgn*((H[j] if sgn==1 else L[j])-q[0][0])>=0:
                                t,fr=q.pop(0); qq=min(fr,rem)
                                parts.append((qq,max(O[j],t) if sgn==1 else min(O[j],t))); rem-=qq; reached=True; first_tgt_k=first_tgt_k or j
                            if rem<=1e-9: status='target'
                    if rem<=1e-9: exk=j; break
                    extc=max(extc,C[j]) if sgn==1 else min(extc,C[j])
                if rem>1e-9: parts.append((rem,C[-1]))
                ret=0.0
                for qq,px in parts:
                    exf=px*(1-sgn*sl)
                    ret+=qq*((exf*(1-fee))/(ein*(1+fee))-1 if sgn==1 else (ein*(1-fee)-exf*(1+fee))/(ein*(1+fee)))
                rows.append(dict(setup_id=r.setup_id,asset=asset,direction=r.direction,policy=f'tg_{sv}_{v}_{mode}',entry_date=cal[k],exit_date=cal[exk],
                                 entry_fill=ein,status=status,ret_net=ret,days=int(exk-k),has_target=bool(tq),reached=reached,mark_ret=mark,
                                 left=(mark-ret) if reached else np.nan))
Rr=pd.DataFrame(rows); Rr.to_csv(OUT+'sim_targets_trades.csv',index=False); E=pd.DataFrame(ew); E.to_csv(OUT+'elliott_coverage.csv',index=False)
print(E.merge(D[['setup_id','asset','direction']],on='setup_id').groupby(['asset','direction']).ew.value_counts().unstack(fill_value=0).to_string())
print(Rr.groupby(['asset','direction','policy']).agg(N=('ret_net','size'),mean=('ret_net','mean'),reached=('reached','mean'),tg=('status',lambda s:(s=='target').mean())).round(3).to_string())
