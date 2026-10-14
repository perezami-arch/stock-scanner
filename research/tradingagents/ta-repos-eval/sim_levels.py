"""Level tests for smartmoneyconcepts and the Elliott repos — mechanics copied verbatim from iaf/sim_geo.py (same setups, calendar,
entry = open of the first bar after the alert + slippage, costs, close-based 'c' and intraday 'i' modes, ACTIVE POLICY baseline:
stock LONG ratchet chandelier 4xATR + 1/2 at Fib 1.618, stock SHORT ratchet chandelier 4xATR, crypto LONG fixed 3xATR).
Only the level dictionary differs (built from out/smc_features.pkl and out/ew_features.pkl, all strictly <= the rule bar):
 smc stops   : S_smcob  = nearest active (unmitigated) smc order block beyond the entry (bull OB bottom for longs) -/+0.5 ATR
               S_smcliq = nearest UNSWEPT smc liquidity level on the stop side -/+0.5 ATR
               S_smcswing = nearest confirmed smc swing low (long) / high (short) beyond the entry -/+0.5 ATR
 smc targets : T_smcliq = nearest unswept smc liquidity level on the target side; T_smcfvg = nearest open smc FVG edge in trade direction
 EW (per repo taew / ewa): S_<r>inv = rule invalidation (w3: wave-1 origin, w5: wave-1 end) -/+0.5 ATR, S_<r>last = end of the last
               completed wave (wave-2 / wave-4 end) -/+0.5 ATR; T_<r> = wave target (w3: w2 + 1.618*w1, w5: w4 + w1)
fix = the level is the only stop; hyb = tighter of level and policy stop. No level beyond entry -> baseline trade, covered=False."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import numpy as np, pandas as pd, sys
sys.path.insert(0,(_SCANNER_ROOT + '/trading-frameworks-eval/iaf'))
from stop_rules import atr_wilder, ChandelierStop
OUT=(_SCANNER_ROOT + '/trading-frameworks-eval/iaf/')
s=open(OUT+'sim_fib.py').read(); exec(s[s.index('def zigzag'):s.index('def clock')])
D=pd.read_pickle(OUT+'setups_prepared.pkl'); F=pd.read_pickle(OUT+'frames.pkl')
SM=pd.read_pickle((_SCANNER_ROOT + '/ta-repos-eval/out/smc_features.pkl')).set_index('setup_id'); EWF=pd.read_pickle((_SCANNER_ROOT + '/ta-repos-eval/out/ew_features.pkl')).set_index('setup_id')
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
        lv={}
        g=SM.loc[r.setup_id] if r.setup_id in SM.index else None
        if g is not None and isinstance(g.get('_liq_above'),list):
            if sgn==1: ob=num(g.get('_ob_below_lo')); back=g['_liq_below']; fwd=g['_liq_above']; sw=g['_swing_lows']; fv=num(g.get('_fvg_above_lo'))
            else:      ob=num(g.get('_ob_above_hi')); back=g['_liq_above']; fwd=g['_liq_below']; sw=g['_swing_highs']; fv=num(g.get('_fvg_below_hi'))
            if ob is not None and sgn*(ein-ob)>0: lv['S_smcob']=ob-sgn*0.5*A
            b=[p for p in back if sgn*(ein-p)>0]; f=[p for p in fwd if sgn*(p-ein)>0]; s_=[p for p in sw if sgn*(ein-p)>0]
            if b: lv['S_smcliq']=(max(b) if sgn==1 else min(b))-sgn*0.5*A
            if s_: lv['S_smcswing']=(max(s_) if sgn==1 else min(s_))-sgn*0.5*A
            if f: lv['T_smcliq']=min(f) if sgn==1 else max(f)
            if fv is not None and sgn*(fv-ein)>0: lv['T_smcfvg']=fv
        e=EWF.loc[r.setup_id] if r.setup_id in EWF.index else None
        for lib in ('taew','ewa'):
            if e is None or e.get(lib+'_state') not in ('w3','w5'): continue
            inv=num(e.get(lib+'_inval')); la=num(e.get(lib+'_last')); tg=num(e.get(lib+'_tgt'))
            if inv is not None and sgn*(ein-inv)>0: lv[f'S_{lib}inv']=inv-sgn*0.5*A
            if la is not None and sgn*(ein-la)>0: lv[f'S_{lib}last']=la-sgn*0.5*A
            if tg is not None and sgn*(tg-ein)>0: lv[f'T_{lib}']=tg
        variants=[('base',None,None,pol_t)]
        for src_ in ('smcob','smcliq','smcswing','taewinv','taewlast','ewainv','ewalast'):
            for how in ('fix','hyb'): variants.append((f'S_{src_}_{how}',lv.get('S_'+src_),how,pol_t))
        for src_ in ('smcliq','smcfvg','taew','ewa'):
            for frac,nm in ((1.0,'full'),(0.5,'half')): variants.append((f'T_{src_}_{nm}',None,None,[(lv['T_'+src_],frac)] if 'T_'+src_ in lv else None))
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
Rr=pd.DataFrame(rows); Rr.to_csv((_SCANNER_ROOT + '/ta-repos-eval/out/sim_levels_trades.csv'),index=False)
# regression vs the scanner policy rows of sim_ratchet_trades.csv
RT=pd.read_csv(OUT+'sim_ratchet_trades.csv'); ok=True
for asset,dirn,src in (('stock','LONG','rt_ratchet_h618'),('stock','SHORT','rt_ratchet'),('crypto','LONG','rt_fixed3')):
    for mode in ('c','i'):
        a_=Rr[(Rr.policy==f'base_{mode}')&(Rr.asset==asset)&(Rr.direction==dirn)]; b_=RT[(RT.policy==f'{src}_{mode}')&(RT.asset==asset)&(RT.direction==dirn)]
        m=a_.merge(b_,on='setup_id',suffixes=('','_o')); d=(m.ret_net-m.ret_net_o).abs()
        print(f'{asset} {dirn} base_{mode} vs {src}_{mode}: N={len(m)}/{len(a_)}/{len(b_)} max|diff|={d.max():.2e}'); ok&=bool((d<=1e-9).all()) and len(m)==len(a_)==len(b_)
print('REGRESSION', 'OK' if ok else 'MISMATCH')
print(Rr.groupby(['asset','direction','policy']).agg(N=('ret_net','size'),cov=('covered','mean'),mean=('ret_net','mean'),dist=('level_dist_atr','median')).round(3).to_string())
