"""Leak / repaint check for TA-Lib, pandas-ta and smartmoneyconcepts (like iaf/geo_leakcheck.py).
For each sampled setup the library is run 3 ways and the values AT THE CUTOFF BAR (TA-Lib / pandas-ta) or on EVERY ROW <= cutoff
(smc, whose events are stamped on past bars) are compared:
  T = history physically truncated at the rule bar (what a live scan sees)
  F = full history to 2026-10-07, read at the rule bar (what a vectorised backtest on the whole series would see)
  J = every bar after the rule bar replaced by random garbage (+30 garbage bars), read at the rule bar
A column whose F or J value differs from T uses bars after the cutoff (look-ahead) or is recomputed/repainted later."""
import sys, json, time, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0,'/workspace/ta-repos-eval')
from common import *
import talib
from talib import abstract
which=sys.argv[1] if len(sys.argv)>1 else 'talib'
samp=leak_sample(30)
def lower(df): x=df.copy(); x.columns=[c.lower() for c in x.columns]; return x
rows=[]
if which=='talib':
    funcs=[f for f in talib.get_functions() if f not in ('MAVP',)]
    for _,r in samp.iterrows():
        df=hist(r); last=pd.Timestamp(r.rule_bar_actual); t=trunc(df,r); j=garbage(df,last)
        V={}
        for lab,x in (('T',t),('F',df),('J',j)):
            inp={k.lower():x[k].values.astype(float) for k in ['Open','High','Low','Close','Volume']}
            pos=int(np.searchsorted(x.index,last,side='right'))-1
            for fn in funcs:
                try: out=abstract.Function(fn)(inp)
                except Exception as e: continue
                outs=out if isinstance(out,list) else [out]
                names=abstract.Function(fn).output_names
                for nm,o in zip(names,outs): V.setdefault((fn,nm),{})[lab]=float(o[pos])
        for (fn,nm),d in V.items():
            rows.append(dict(setup_id=r.setup_id,lib='TA-Lib',func=fn,col=nm,F_diff=not same(d.get('T'),d.get('F')),J_diff=not same(d.get('T'),d.get('J'))))
elif which=='pandas_ta':
    import pandas_ta as ta
    sub=samp.head(int(sys.argv[2]) if len(sys.argv)>2 else 12)
    for _,r in sub.iterrows():
        df=hist(r); last=pd.Timestamp(r.rule_bar_actual); V={}
        for lab,x in (('T',trunc(df,r)),('F',df),('J',garbage(df,last))):
            x=lower(x); x.ta.study("All",cores=0,verbose=False)
            row=x.loc[last]
            for c in x.columns:
                if c in ('open','high','low','close','volume'): continue
                V.setdefault(c,{})[lab]=row[c]
        for c,d in V.items():
            rows.append(dict(setup_id=r.setup_id,lib='pandas-ta',func=c,col=c,F_diff=not same(d.get('T'),d.get('F')),J_diff=not same(d.get('T'),d.get('J')),
                             T_missing='T' not in d))
        print(r.setup_id,'done',flush=True)
elif which=='smc':
    from smartmoneyconcepts import smc
    def run(x):
        o=lower(x).reset_index(drop=True)
        sw=smc.swing_highs_lows(o,swing_length=10)
        res=dict(swing=sw,fvg=smc.fvg(o),bos=smc.bos_choch(o,sw),ob=smc.ob(o,sw),liq=smc.liquidity(o,sw),ret=smc.retracements(o,sw))
        return res
    for _,r in samp.iterrows():
        df=hist(r); last=pd.Timestamp(r.rule_bar_actual); t=trunc(df,r); n=len(t)
        RT=run(t); RF=run(df); RJ=run(garbage(df,last))
        for k in RT:
            a=RT[k].iloc[:n].astype(float); f=RF[k].iloc[:n].astype(float); jj=RJ[k].iloc[:n].astype(float)
            for c in a.columns:
                da=a[c].values; df_=f[c].values; dj=jj[c].values
                eqF=np.array([same(x,y) for x,y in zip(da,df_)]); eqJ=np.array([same(x,y) for x,y in zip(da,dj)])
                rows.append(dict(setup_id=r.setup_id,lib='smartmoneyconcepts',func=k,col=c,F_diff=not eqF.all(),J_diff=not eqJ.all(),
                                 F_rows_diff=int((~eqF).sum()),last_bar_diff=not eqF[-1],last10_diff=int((~eqF[-10:]).sum()),
                                 first_diff_bars_before_cut=int(n-1-np.where(~eqF)[0].min()) if (~eqF).any() else -1))
R=pd.DataFrame(rows); R.to_csv(OUT+f'leak_{which}.csv',index=False)
g=R.groupby(['lib','func','col']).agg(n=('F_diff','size'),F_diff=('F_diff','sum'),J_diff=('J_diff','sum')).reset_index()
print('columns:',len(g),' with any F/J mismatch:',int(((g.F_diff>0)|(g.J_diff>0)).sum()))
print(g[(g.F_diff>0)|(g.J_diff>0)].to_string())
