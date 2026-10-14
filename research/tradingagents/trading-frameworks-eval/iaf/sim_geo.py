"""Level tests for the scanner_geometry liquidity / order-block / volume-profile objects (strict PIT: every object comes
from geo_features.pkl, i.e. built only from bars <= the rule bar and confirmed on/before it -> see geo_leakcheck.py).
Same setups, calendar, entry (open of first bar after the alert, + slippage), costs, close-based ('c': first check at close of
entry-bar+2) and intraday ('i': from entry-bar+1, fill at the worse of open and level) mechanics as sim_ratchet.py.
ACTIVE POLICY (baseline, = stop_policy_scanner.csv): stock LONG ratchet chandelier 4xATR + 1/2 at Fib 1.618; stock SHORT ratchet
chandelier 4xATR; crypto LONG fixed 3xATR. Crypto shorts are frozen by the rules -> not simulated.
(a) STOP variants (policy target kept): level = nearest confirmed object BEYOND the entry fill on the stop side, -/+ 0.5*ATR14(rule bar):
    pool = untaken swing-low cluster (long) / swing-high cluster (short), any touch count; ob = unmitigated order block zone low (long) /
    high (short) from liq_ob_below/above; hvn = nearest HVN of the 60/120-bar daily profiles.
    'fix' = that level is the only stop (never moves); 'hyb' = tighter of the level and the policy stop on every bar.
(b) TARGET variants (policy stop kept, REPLACES the 1.618 half for stock longs): nearest untaken swing-high cluster above the entry
    (long; short mirrored) or nearest open FVG edge in the trade direction (liq_fvg_above_lo / liq_fvg_below_hi); full exit or 1/2.
No object beyond entry -> the variant falls back to the baseline trade (covered=False). Comparisons use covered trades only (paired)."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import numpy as np, pandas as pd, sys
sys.path.insert(0,(_SCANNER_ROOT + '/trading-frameworks-eval/iaf'))
from stop_rules import atr_wilder, ChandelierStop
OUT=(_SCANNER_ROOT + '/trading-frameworks-eval/iaf/')
s=open(OUT+'sim_fib.py').read(); exec(s[s.index('def zigzag'):s.index('def clock')])
D=pd.read_pickle(OUT+'setups_prepared.pkl'); F=pd.read_pickle(OUT+'frames.pkl')
GF=pd.read_pickle(OUT+'geo_features.pkl').set_index('setup_id')
COST={'stock':dict(fee=0.02, slip=0.05), 'crypto':dict(fee=0.10, slip=0.10)}
def clock(asset):
    if asset=='crypto': cal=pd.date_range('2026-05-01','2026-10-07',freq='D'); opens=cal
    else:
        allidx=sorted(set().union(*[set(x.index) for (t,c),x in F.items() if not c]))
        cal=pd.DatetimeIndex([d for d in allidx if d>=pd.Timestamp('2026-05-01')]); opens=cal+pd.Timedelta(hours=13,minutes=30)
    return cal,np.array(opens,dtype='datetime64[ns]')
def num(v):
    try: v=float(v); return v if np.isfinite(v) else None
    except (TypeError,ValueError): return None
rows=[]; cache={}
for asset in ('stock','crypto'):
    cal,opens=clock(asset); c=COST[asset]; fee=c['fee']/100; sl=c['slip']/100
    S=D[D.has_data&(D.asset==asset)&D.direction.isin(['LONG','SHORT'])&D.decision_utc.notna()]
    if asset=='crypto': S=S[S.direction=='LONG']
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
        tgt=None
        if asset=='stock' and sgn==1:
            known=[p for p in piv if p[3]<=R_]; idx=[j for j,p in enumerate(known) if p[0]=='H']
            if idx and idx[-1]>0:
                e_=known[idx[-1]][1]; o=known[idx[-1]-1][1]; rng=e_-o
                ext=[t for t in [o+f*rng for f in (1.272,1.618,2.618)] if t-ein>0]
                cand=[t for t in ext if t>=o+1.618*rng]
                tgt=cand[0] if cand else None
        pol_k,pol_mode=(3.0,'fixed') if asset=='crypto' else (4.0,'ratchet')
        pol_t=[(tgt,0.5)] if tgt is not None else []
        g=GF.loc[r.setup_id] if r.setup_id in GF.index else None
        # ---- objects beyond the entry fill
        lv={}
        if g is not None and isinstance(g.get('_poolsL'),list):
            back=[p[0] for p in (g['_poolsL'] if sgn==1 else g['_poolsH'])]; fwd=[p[0] for p in (g['_poolsH'] if sgn==1 else g['_poolsL'])]
            b=[p for p in back if sgn*(ein-p)>0]; f=[p for p in fwd if sgn*(p-ein)>0]
            if b: lv['S_pool']=(max(b) if sgn==1 else min(b))-sgn*0.5*A
            if f: lv['T_pool']=min(f) if sgn==1 else max(f)
            hv=[p for p in g['_hvn'] if sgn*(ein-p)>0]
            if hv: lv['S_hvn']=(max(hv) if sgn==1 else min(hv))-sgn*0.5*A
            ob=num(g.get('liq_ob_below_lo')) if sgn==1 else num(g.get('liq_ob_above_hi'))
            if ob is not None and sgn*(ein-ob)>0: lv['S_ob']=ob-sgn*0.5*A
            fv=num(g.get('liq_fvg_above_lo')) if sgn==1 else num(g.get('liq_fvg_below_hi'))
            if fv is not None and sgn*(fv-ein)>0: lv['T_fvg']=fv
        variants=[('base',None,None,pol_t)]
        for src in ('pool','ob','hvn'):
            for how in ('fix','hyb'): variants.append((f'S_{src}_{how}',lv.get('S_'+src),how,pol_t))
        for src in ('pool','fvg'):
            for frac,nm in ((1.0,'full'),(0.5,'half')): variants.append((f'T_{src}_{nm}',None,None,[(lv['T_'+src],frac)] if 'T_'+src in lv else None))
        for vname,slv,how,tq0 in variants:
            covered=True
            if vname.startswith('S_') and slv is None: covered=False; slv=None; how=None; tq0=pol_t
            if vname.startswith('T_') and tq0 is None: covered=False; tq0=pol_t
            for mode in ('c','i'):
                st=ChandelierStop(r.direction,ein,A,k=pol_k,mode=pol_mode); st.start(C[k])
                parts=[]; rem=1.0; exk=len(cal)-1; status='open@end'; tq=list(tq0); hit=False
                for j in range(k+1,len(cal)):
                    if mode=='c' and j==k+1: st.on_close(C[j]); continue
                    lp=st.level(Acal[j-1])
                    if how=='fix': lvl=slv
                    elif how=='hyb': lvl=max(slv,lp) if sgn==1 else min(slv,lp)
                    else: lvl=lp
                    if mode=='c':
                        if sgn*(C[j]-lvl)<=0: parts.append((rem,C[j])); rem=0; status='stopped'
                        else:
                            while tq and rem>1e-9 and sgn*(C[j]-tq[0][0])>=0:
                                t,fr=tq.pop(0); q=min(fr,rem); parts.append((q,C[j])); rem-=q; hit=True
                            if rem<=1e-9: status='target'
                    else:
                        if (L[j]<=lvl) if sgn==1 else (H[j]>=lvl):
                            parts.append((rem,min(O[j],lvl) if sgn==1 else max(O[j],lvl))); rem=0; status='stopped'
                        else:
                            while tq and rem>1e-9 and sgn*((H[j] if sgn==1 else L[j])-tq[0][0])>=0:
                                t,fr=tq.pop(0); q=min(fr,rem); parts.append((q,max(O[j],t) if sgn==1 else min(O[j],t))); rem-=q; hit=True
                            if rem<=1e-9: status='target'
                    if rem<=1e-9: exk=j; break
                    st.on_close(C[j])
                if rem>1e-9: parts.append((rem,C[-1]))
                ret=0.0
                for qq,px in parts:
                    exf=px*(1-sgn*sl)
                    ret+=qq*((exf*(1-fee))/(ein*(1+fee))-1 if sgn==1 else (ein*(1-fee)-exf*(1+fee))/(ein*(1+fee)))
                lvl_used=slv if vname.startswith('S_') else (tq0[0][0] if (vname.startswith('T_') and covered) else None)
                rows.append(dict(setup_id=r.setup_id,asset=asset,direction=r.direction,policy=f'{vname}_{mode}',variant=vname,mode=mode,covered=covered,
                    entry_date=cal[k],exit_date=cal[exk],entry_fill=ein,status=status,ret_net=ret,days=int(exk-k),
                    R_pct=pol_k*A/ein*100,level=lvl_used,level_dist_atr=(abs(lvl_used-ein)/A if lvl_used is not None else np.nan),target_hit=hit))
Rr=pd.DataFrame(rows); Rr.to_csv(OUT+'sim_geo_trades.csv',index=False)
# regression vs the scanner policy rows of sim_ratchet_trades.csv
RT=pd.read_csv(OUT+'sim_ratchet_trades.csv'); ok=True
for asset,dirn,src in (('stock','LONG','rt_ratchet_h618'),('stock','SHORT','rt_ratchet'),('crypto','LONG','rt_fixed3')):
    for mode in ('c','i'):
        a_=Rr[(Rr.policy==f'base_{mode}')&(Rr.asset==asset)&(Rr.direction==dirn)]; b_=RT[(RT.policy==f'{src}_{mode}')&(RT.asset==asset)&(RT.direction==dirn)]
        m=a_.merge(b_,on='setup_id',suffixes=('','_o')); d=(m.ret_net-m.ret_net_o).abs()
        print(f'{asset} {dirn} base_{mode} vs {src}_{mode}: N={len(m)}/{len(a_)}/{len(b_)} max|diff|={d.max():.2e}'); ok&=bool((d<=1e-9).all()) and len(m)==len(a_)==len(b_)
print('REGRESSION', 'OK' if ok else 'MISMATCH')
print(Rr.groupby(['asset','direction','policy']).agg(N=('ret_net','size'),cov=('covered','mean'),mean=('ret_net','mean'),dist=('level_dist_atr','median')).round(3).to_string())
