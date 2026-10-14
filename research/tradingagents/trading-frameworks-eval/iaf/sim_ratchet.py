"""Ratchet / floor / tighten-after-profit chandelier variants using stop_rules.ChandelierStop (the shared module).
Same setups, PIT entries, costs and calendar as sim_chand.py / sim_targets.py. Close-based ('c': first check at close of
entry-bar+2, entry-bar+1 close included in the extreme) and intraday ('i': checks from bar e+1).
Stock longs: with and without 'sell 1/2 at the 1.618 extension' (same confirmed leg as sim_targets.py; if 1.618 is
already behind the entry the next extension beyond it is used; no leg/target -> stop only).
Records per trade: R (price) = initial stop distance, R-multiple, max favourable close excursion in R (while held and
to 2026-10-07), tightened flag."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import numpy as np, pandas as pd, sys
sys.path.insert(0,(_SCANNER_ROOT + '/trading-frameworks-eval/iaf'))
from stop_rules import atr_wilder, ChandelierStop
OUT=(_SCANNER_ROOT + '/trading-frameworks-eval/iaf/')
s=open(OUT+'sim_fib.py').read(); exec(s[s.index('def zigzag'):s.index('def clock')])
D=pd.read_pickle(OUT+'setups_prepared.pkl'); F=pd.read_pickle(OUT+'frames.pkl')
COST={'stock':dict(fee=0.02, slip=0.05), 'crypto':dict(fee=0.10, slip=0.10)}
def clock(asset):
    if asset=='crypto': cal=pd.date_range('2026-05-01','2026-10-07',freq='D'); opens=cal
    else:
        allidx=sorted(set().union(*[set(x.index) for (t,c),x in F.items() if not c]))
        cal=pd.DatetimeIndex([d for d in allidx if d>=pd.Timestamp('2026-05-01')]); opens=cal+pd.Timedelta(hours=13,minutes=30)
    return cal,np.array(opens,dtype='datetime64[ns]')
VARIANTS=[('plain',dict(mode='plain')),('ratchet',dict(mode='ratchet')),('floor',dict(mode='floor'))]
for X in (2,3,4.5):
    for k2 in (2,3): VARIANTS.append((f'rat_t{X}_k{k2}',dict(mode='ratchet',tighten_at_R=X,k2=k2)))
rows=[]; cache={}
for asset in ('stock','crypto'):
    cal,opens=clock(asset); c=COST[asset]; fee=c['fee']/100; sl=c['slip']/100
    S=D[D.has_data&(D.asset==asset)&D.direction.isin(['LONG','SHORT'])&D.decision_utc.notna()]
    for _,r in S.iterrows():
        k=int(np.searchsorted(opens,np.datetime64(r.decision_utc),side='left'))
        if k>=len(cal)-1: continue
        key=(r.ticker,asset=='crypto')
        if key not in cache:
            raw=F[key].dropna(subset=['Close']); h,l,cc=raw.High.values,raw.Low.values,raw.Close.values
            a=atr_wilder(h,l,cc); piv=zigzag(h,l,a,2.0) if len(a) else []
            Acal=pd.Series(a,index=raw.index).reindex(cal.union(raw.index)).ffill().reindex(cal).values
            cache[key]=(raw.index,a,piv,Acal)
        ridx,a,piv,Acal=cache[key]
        R_=int(np.searchsorted(ridx,pd.Timestamp(r.rule_bar_date),side='right'))-1
        if R_<14 or not np.isfinite(a[R_]): continue
        A=a[R_]
        x=F[key].reindex(cal); x['Close']=x.Close.ffill().bfill()
        for col in ('Open','High','Low'): x[col]=x[col].fillna(x.Close)
        O,H,L,C=x.Open.values,x.High.values,x.Low.values,x.Close.values
        sgn=1 if r.direction=='LONG' else -1; ein=O[k]*(1+sgn*sl)
        # 1.618 target from the confirmed leg (stock longs only)
        tgt=None
        if asset=='stock' and sgn==1:
            known=[p for p in piv if p[3]<=R_]; idx=[j for j,p in enumerate(known) if p[0]=='H']
            if idx and idx[-1]>0:
                e_=known[idx[-1]][1]; o=known[idx[-1]-1][1]; rng=e_-o
                ext=[t for t in [o+f*rng for f in (1.272,1.618,2.618)] if t-ein>0]
                cand=[t for t in ext if t>=o+1.618*rng]
                tgt=cand[0] if cand else None
        mfe_end=max(0.0,sgn*((np.max(C[k:]) if sgn==1 else np.min(C[k:]))-ein))
        var=list(VARIANTS)
        if asset=='crypto': var=[('fixed3',dict(mode='fixed',k=3.0))]+var
        tg_opts=[False,True] if (asset=='stock' and sgn==1) else [False]
        for vname,kw in var:
            for use_t in tg_opts:
                for mode in ('c','i'):
                    kw2=dict(kw); kk=kw2.pop('k',4.0)
                    st=ChandelierStop(r.direction,ein,A,k=kk,**kw2); st.start(C[k])
                    parts=[]; rem=1.0; exk=len(cal)-1; status='open@end'; tq=(tgt is not None) and use_t; hit_t=False
                    for j in range(k+1,len(cal)):
                        if mode=='c' and j==k+1: st.on_close(C[j]); continue
                        lv=st.level(Acal[j-1])
                        if mode=='c':
                            if sgn*(C[j]-lv)<=0: parts.append((rem,C[j])); rem=0; status='stopped'
                            elif tq and C[j]>=tgt: parts.append((0.5,C[j])); rem-=0.5; tq=False; hit_t=True
                        else:
                            if (L[j]<=lv) if sgn==1 else (H[j]>=lv):
                                parts.append((rem,min(O[j],lv) if sgn==1 else max(O[j],lv))); rem=0; status='stopped'
                            elif tq and H[j]>=tgt: parts.append((0.5,max(O[j],tgt))); rem-=0.5; tq=False; hit_t=True
                        if rem<=1e-9: exk=j; break
                        st.on_close(C[j])
                    if rem>1e-9: parts.append((rem,C[-1]))
                    ret=0.0
                    for qq,px in parts:
                        exf=px*(1-sgn*sl)
                        ret+=qq*((exf*(1-fee))/(ein*(1+fee))-1 if sgn==1 else (ein*(1-fee)-exf*(1+fee))/(ein*(1+fee)))
                    Rp=st.R
                    rows.append(dict(setup_id=r.setup_id,asset=asset,direction=r.direction,policy=f'rt_{vname}{"_h618" if use_t else ""}_{mode}',
                        entry_date=cal[k],exit_date=cal[exk],entry_fill=ein,status=status,ret_net=ret,days=int(exk-k),
                        R_pct=Rp/ein*100,R_mult=ret/(Rp/ein),mfe_R_held=st.mfe_R,mfe_R_end=mfe_end/Rp,tightened=st.tightened,
                        has_target=tgt is not None,target_hit=hit_t,final_stop=st.stop))
Rr=pd.DataFrame(rows); Rr.to_csv(OUT+'sim_ratchet_trades.csv',index=False)
print(len(Rr)); print(Rr.groupby(['asset','direction','policy']).agg(N=('ret_net','size'),mean=('ret_net','mean'),R=('R_mult','mean'),stp=('status',lambda s:(s=='stopped').mean()),tight=('tightened','mean')).round(3).to_string())
