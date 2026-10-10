"""Independent look-ahead check of scanner_geometry.geometry_columns on 30 random backtest setups (seed 20261008).
For each setup, columns are computed 4 ways and must be IDENTICAL:
  A full price history + cutoff  (what the backtest uses)
  B history physically truncated at the rule bar + cutoff
  C full history, every bar after the rule bar replaced by random garbage (+30 extra garbage bars) + cutoff
  D truncated history, cutoff=None
Then: every *_confirmed_at and every past-object date (anchor/spiral/vpanc/sweep) must be <= the rule bar; geo_last_bar == rule bar.
Also checks the extra pool / HVN lists used by the level tests the same way."""
import sys, numpy as np, pandas as pd, json
sys.path.insert(0,'/workspace'); sys.path.insert(0,'/workspace/trading-frameworks-eval/iaf')
import scanner_geometry as G
from geo_features import extras, D, F
OUT='/workspace/trading-frameworks-eval/iaf/'
RT=pd.read_csv(OUT+'sim_ratchet_trades.csv')
ids=set(RT.setup_id); S=D[D.setup_id.isin(ids) & D.in_main & ~D.dup]
samp=S.sample(30,random_state=20261008)
rng=np.random.default_rng(1)
def same(a,b):
    if a is None and b is None: return True
    if isinstance(a,float) and isinstance(b,float) and np.isnan(a) and np.isnan(b): return True
    if isinstance(a,(float,int,np.floating)) and isinstance(b,(float,int,np.floating)) and not isinstance(a,bool): return abs(float(a)-float(b))<=1e-9*max(1,abs(float(a)))
    if isinstance(a,list) and isinstance(b,list): return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    if isinstance(a,tuple) and isinstance(b,tuple): return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    return a==b
def garbage(df,last):
    g=df.astype(float).copy(); post=g.index>last; n=int(post.sum())
    base=float(g.Close[g.index<=last].iloc[-1])
    c=base*np.exp(np.cumsum(rng.normal(0,0.2,n))) if n else np.array([])
    g.loc[post,'Close']=c; g.loc[post,'Open']=c*rng.uniform(0.5,1.5,n); g.loc[post,'High']=np.maximum(c,g.loc[post,'Open'])*rng.uniform(1,3,n)
    g.loc[post,'Low']=np.minimum(c,g.loc[post,'Open'])*rng.uniform(0.2,1,n); g.loc[post,'Volume']=rng.uniform(0,1e10,n)
    step=pd.Timedelta(days=1); idx=pd.date_range(g.index[-1]+step,periods=30,freq='D')
    e=pd.DataFrame({'Open':base*3,'High':base*10,'Low':base*0.01,'Close':base*0.05,'Volume':1e12},index=idx)
    return pd.concat([g,e])
rows=[]; mism=[]
for _,r in samp.iterrows():
    crypto=r.asset=='crypto'; df=F[(r.ticker,crypto)].dropna(subset=['Close']); last=pd.Timestamp(r.rule_bar_actual); cut=r.info_cutoff_utc
    trunc=df[df.index<=last]; gar=garbage(df,last)
    A=G.geometry_columns(df,cut,r.asset,r.direction); A.update(extras(df,cut,r.asset))
    B=G.geometry_columns(trunc,cut,r.asset,r.direction); B.update(extras(trunc,cut,r.asset))
    C=G.geometry_columns(gar,cut,r.asset,r.direction); C.update(extras(gar,cut,r.asset))
    Dd=G.geometry_columns(trunc,None,r.asset,r.direction); Dd.update(extras(trunc,None,r.asset))
    nm={}
    for lab,Y in (('B_trunc',B),('C_garbage',C),('D_trunc_nocut',Dd)):
        keys=set(A)|set(Y); bad=[k for k in keys if not same(A.get(k),Y.get(k))]
        nm[lab]=len(bad)
        for k in bad: mism.append(dict(setup_id=r.setup_id,ticker=r.ticker,variant=lab,col=k,full=str(A.get(k))[:60],other=str(Y.get(k))[:60]))
    conf=[k for k in A if k.endswith('confirmed_at') and A[k] is not None]
    past=[k for k in ('exp_anchor_origin_date','exp_anchor_end_date','exp_spiral_center_date','exp_spiral_start_date','vpanc_from','liq_sweep_date','candle_last_bar','geo_last_bar') if A.get(k)]
    late=[k for k in conf+past if pd.Timestamp(A[k])>last]
    plate=[p for p in A.get('_poolsH',[])+A.get('_poolsL',[]) if pd.Timestamp(p[2])>last]
    rows.append(dict(setup_id=r.setup_id,ticker=r.ticker,asset=r.asset,direction=r.direction,time_source=r.time_source,rule_bar=str(last.date()),
                     geo_last_bar=A.get('geo_last_bar'),n_cols=len(A),n_confirmed_cols=len(conf),late_dates=len(late)+len(plate),**nm))
R=pd.DataFrame(rows); M=pd.DataFrame(mism)
R.to_csv(OUT+'geo_leakcheck.csv',index=False); M.to_csv(OUT+'geo_leakcheck_mismatches.csv',index=False)
print(R.to_string())
print('total column comparisons:', int(R.n_cols.sum()*3), ' mismatches:', len(M), ' confirmed_at checked:', int(R.n_confirmed_cols.sum()), ' late dates:', int(R.late_dates.sum()),
      ' last-bar != rule bar:', int((R.geo_last_bar!=R.rule_bar).sum()))
if len(M): print(M.groupby(['variant','col']).size().to_string())
# informational: what last bar the module would pick if fed the raw decision time (instead of the tracker's conservative cutoff)
inf=[]
for _,r in S.iterrows():
    crypto=r.asset=='crypto'; df=F[(r.ticker,crypto)].dropna(subset=['Close'])
    x=G.pit_cut(df,r.decision_utc if r.time_source in ('exact','schedule','ui_log') else r.info_cutoff_utc,r.asset)
    inf.append(dict(asset=r.asset,ts=r.time_source,same=len(x)>0 and x.index[-1]==pd.Timestamp(r.rule_bar_actual)))
I=pd.DataFrame(inf); print(I.groupby(['asset','ts']).same.agg(['size','mean']))
