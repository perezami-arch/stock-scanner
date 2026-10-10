"""Elliott-wave state at the cutoff for every setup from 3 GitHub repos (ew_libs.py), fed only bars <= the rule bar."""
import sys, time, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0,'/workspace/ta-repos-eval')
from common import *
import ew_libs as E
from multiprocessing import Pool
def work(r):
    out=dict(setup_id=r['setup_id'])
    x=trunc(hist(r),r); sg=1 if r['direction']=='LONG' else -1
    out['ew_last_bar']=str(x.index[-1].date()) if len(x) else None
    if len(x)<60: return out
    for nm,f in (('taew',E.taew_state),('ewa',E.ewa_state),('ar',E.ar_state)):
        t=time.time()
        try:
            o=f(x,sg)
            for k,v in o.items(): out[f'{nm}_{k}']=v
        except Exception as e: out[f'{nm}_error']=f'{e.__class__.__name__}: {e}'
        out[f'{nm}_sec']=time.time()-t
    return out
if __name__=='__main__':
    recs=S[['setup_id','ticker','asset','direction','rule_bar_actual']].to_dict('records')
    with Pool(2) as p: res=p.map(work,recs,chunksize=5)
    X=pd.DataFrame(res); X.to_pickle(OUT+'ew_features.pkl')
    for nm in ('taew','ewa','ar'):
        print(nm, X[f'{nm}_state'].value_counts(dropna=False).to_dict(), 'errors', X.get(f'{nm}_error',pd.Series(dtype=object)).notna().sum(), 'sec mean/max', round(X[f'{nm}_sec'].mean(),2), round(X[f'{nm}_sec'].max(),1))
