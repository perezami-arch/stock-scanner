"""Compute scanner_geometry.geometry_columns() point-in-time for every testable setup (read-only use of
/workspace/scanner_geometry.py, tracker data via setups_prepared.pkl / frames.pkl).
Cutoff = the same information cutoff every other sim uses (setups_prepared.info_cutoff_utc):
  stock  -> rule_bar_date 20:00 UTC (= 16:00 ET, EDT all period) => last visible bar = rule bar (prev close for pre/intraday alerts,
            alert-day bar only for after-close alerts, as in the tracker's cutoff_bar_date)
  crypto -> alert minute (Perplexity ui_log: -70 min) => last visible bar = UTC day before the cutoff day.
Direction view = the setup's direction. Also stores the full lists of untaken liquidity pools (all, not only the nearest)
and the HVN lists of the 60/120-bar daily profiles, for the level tests (built with the module's own functions)."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import sys, numpy as np, pandas as pd
from multiprocessing import Pool
sys.path.insert(0,_SCANNER_ROOT)
import scanner_geometry as G
OUT=(_SCANNER_ROOT + '/trading-frameworks-eval/iaf/')
D=pd.read_pickle(OUT+'setups_prepared.pkl'); F=pd.read_pickle(OUT+'frames.pkl')
S=D[D.has_data & D.direction.isin(['LONG','SHORT']) & D.decision_utc.notna()].copy()
def extras(df,cutoff,asset):
    x=G.pit_cut(df,cutoff,asset)
    if len(x)<40: return {}
    a=G.atr14(x.High.values,x.Low.values,x.Close.values); A=float(a[-1]); j=len(x)-1
    if not np.isfinite(A): return {}
    piv=G.fractal_pivots(x)
    pH=G._pools(x,piv,j,A,'H'); pL=G._pools(x,piv,j,A,'L')
    hv=[]
    for w in G.VP_WINDOWS:
        y=x.iloc[-w:]; pr=G.profile(y.Low.values,y.High.values,y.Volume.values)
        if pr: hv+=pr['hvn']
    return dict(_A=A,_close=float(x.Close.iloc[-1]),_last=x.index[-1],
                _poolsH=[(p['level'],p['touches'],str(x.index[p['conf_last']].date())) for p in pH],
                _poolsL=[(p['level'],p['touches'],str(x.index[p['conf_last']].date())) for p in pL],
                _hvn=sorted(hv))
def work(r):
    crypto=r['asset']=='crypto'; df=F[(r['ticker'],crypto)]
    out=dict(setup_id=r['setup_id'],cutoff=r['info_cutoff_utc'])
    try:
        out.update(G.geometry_columns(df,r['info_cutoff_utc'],r['asset'],r['direction']))
        out.update(extras(df,r['info_cutoff_utc'],r['asset']))
    except Exception as e: out['geo_error']=f'{e.__class__.__name__}: {e}'
    return out
if __name__=='__main__':
    recs=S[['setup_id','ticker','asset','direction','info_cutoff_utc']].to_dict('records')
    with Pool(4) as p: res=p.map(work,recs,chunksize=8)
    X=pd.DataFrame(res); X.to_pickle(OUT+'geo_features.pkl')
    print(X.shape, 'errors:', X.get('geo_error',pd.Series(dtype=object)).notna().sum())
    m=X.merge(S[['setup_id','rule_bar_actual']],on='setup_id')
    print('geo_last_bar != rule_bar_actual:', int((pd.to_datetime(m.geo_last_bar)!=pd.to_datetime(m.rule_bar_actual)).sum()))
