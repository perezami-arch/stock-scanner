import yfinance as yf, pandas as pd, json, os
from alerts import all_alerts
T=sorted({a['ticker'] for a in all_alerts() if a.get('ttype')!='קריפטו'})
d=yf.download(T,start='2026-05-01',end='2026-10-03',group_by='ticker',auto_adjust=False,progress=False,threads=True)
d.to_pickle('prices_all.pkl')
info=json.load(open('info_all.json')) if os.path.exists('info_all.json') else {}
for t in T:
    if t in info and info[t].get('mcap'): continue
    try:
        tk=yf.Ticker(t); fi=tk.fast_info; nm=None
        info[t]={'mcap':fi.market_cap,'last':fi.last_price,'name':nm}
    except Exception as e: info[t]={'err':str(e)}
json.dump(info,open('info_all.json','w'),indent=1,default=str)
for t in T:
    df=d[t].dropna(subset=['Close']) if t in d.columns.get_level_values(0) else []
    if len(df)==0: print('NO DATA',t)
