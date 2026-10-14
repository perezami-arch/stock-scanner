"""Shared inputs for the TA-repos evaluation (read-only use of the tracker / §3.14 artefacts).
Setups = every setup with an active-policy trade in sim_geo_trades.csv (base_c), i.e. the §3.14 universe.
PIT: the last visible bar = rule_bar_actual (the same information cutoff as every earlier table; verified in §3.14)."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
IAF=(_SCANNER_ROOT + '/trading-frameworks-eval/iaf/')
OUT=(_SCANNER_ROOT + '/ta-repos-eval/out/')
D=pd.read_pickle(IAF+'setups_prepared.pkl'); F=pd.read_pickle(IAF+'frames.pkl')
_T=pd.read_csv(IAF+'sim_geo_trades.csv'); _ids=set(_T[_T.policy=='base_c'].setup_id)
S=D[D.setup_id.isin(_ids)].copy()
def hist(r, frames=None):
    frames=F if frames is None else frames
    df=frames[(r['ticker'], r['asset']=='crypto')].dropna(subset=['Close']).astype(float)
    return df
def trunc(df, r):
    return df[df.index<=pd.Timestamp(r['rule_bar_actual'])]
def garbage(df,last,seed=1):
    rng=np.random.default_rng(seed)
    g=df.astype(float).copy(); post=g.index>last; n=int(post.sum())
    base=float(g.Close[g.index<=last].iloc[-1])
    c=base*np.exp(np.cumsum(rng.normal(0,0.2,n))) if n else np.array([])
    g.loc[post,'Close']=c; g.loc[post,'Open']=c*rng.uniform(0.5,1.5,n); g.loc[post,'High']=np.maximum(c,g.loc[post,'Open'])*rng.uniform(1,3,n)
    g.loc[post,'Low']=np.minimum(c,g.loc[post,'Open'])*rng.uniform(0.2,1,n); g.loc[post,'Volume']=rng.uniform(0,1e10,n)
    idx=pd.date_range(g.index[-1]+pd.Timedelta(days=1),periods=30,freq='D')
    e=pd.DataFrame({'Open':base*3,'High':base*10,'Low':base*0.01,'Close':base*0.05,'Volume':1e12},index=idx)
    return pd.concat([g,e])
def atr14(h,l,c):
    pc=np.r_[np.nan,c[:-1]]; tr=np.nanmax(np.c_[h-l,np.abs(h-pc),np.abs(l-pc)],axis=1); tr[0]=h[0]-l[0]
    a=np.full(len(c),np.nan)
    if len(c)<15: return a
    a[13]=tr[:14].mean()
    for i in range(14,len(c)): a[i]=(a[i-1]*13+tr[i])/14
    return a
def leak_sample(n=30, seed=20261008):
    RT=pd.read_csv(IAF+'sim_ratchet_trades.csv'); ids=set(RT.setup_id)
    s=S[S.setup_id.isin(ids) & S.in_main & ~S.dup.astype(bool)]
    return s.sample(n, random_state=seed)
def same(a,b,tol=1e-7):
    if a is None and b is None: return True
    try:
        fa,fb=float(a),float(b)
        if np.isnan(fa) and np.isnan(fb): return True
        return abs(fa-fb)<=tol*max(1,abs(fa))
    except (TypeError,ValueError): return a==b
