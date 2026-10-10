import sys; sys.path.insert(0,'/workspace/tracker')
import yfinance as yf, pandas as pd, json, os
from concurrent.futures import ThreadPoolExecutor
from stats3 import rows_counted
T={r['ticker'] for r in rows_counted if r['ticker']}|{'SPY','QQQ'}
T=sorted(T); print(len(T))
d=yf.download(T,start='2024-06-01',end='2026-10-01',group_by='ticker',auto_adjust=False,progress=False,threads=True)
d.to_pickle('rules/hist.pkl')
def meta(t):
    out={}
    try:
        tk=yf.Ticker(t)
        try:
            inf=tk.info; out.update(sector=inf.get('sector'),industry=inf.get('industry'),mcap=inf.get('marketCap'),shares=inf.get('sharesOutstanding'),qtype=inf.get('quoteType'),name=inf.get('shortName'))
        except Exception as e: out['info_err']=str(e)[:100]
        try:
            ed=tk.get_earnings_dates(limit=16)
            out['earn']=[str(x.date()) for x in ed.index] if ed is not None else []
        except Exception as e: out['earn_err']=str(e)[:100]
    except Exception as e: out['err']=str(e)[:100]
    return t,out
with ThreadPoolExecutor(8) as ex: M=dict(ex.map(meta,[t for t in T if t not in('SPY','QQQ')]))
json.dump(M,open('rules/meta.json','w'),indent=1,default=str)
for t in T:
    try: n=d[t]['Close'].dropna().shape[0]
    except Exception: n=0
    if n<260: print('SHORT HIST',t,n)
print('earn ok',sum(1 for v in M.values() if v.get('earn')),'sector ok',sum(1 for v in M.values() if v.get('sector')))
