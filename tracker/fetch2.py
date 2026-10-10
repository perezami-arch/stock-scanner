import yfinance as yf, pandas as pd, json
from setups import SCANS
T=sorted({s[0] for v in SCANS.values() for s in v['setups']})
d=yf.download(T,start='2026-06-01',end='2026-10-01',group_by='ticker',auto_adjust=False,progress=False,threads=True)
d.to_pickle('prices2.pkl')
info={}
for t in T:
    tk=yf.Ticker(t); fi=tk.fast_info
    try: nm=tk.info.get('longName')
    except Exception: nm=None
    info[t]={'mcap':fi.market_cap,'shares':fi.shares,'last':fi.last_price,'name':nm}
json.dump(info,open('info2.json','w'),indent=1,default=str)
for k,v in SCANS.items():
    for s in v['setups']:
        c=d[s[0]]['Close'].dropna()
        m=c[(c.round(2)-s[2]).abs()<0.015]
        print(k,s[0],s[2],[x.date().isoformat() for x in m.index if x<pd.Timestamp(k)+pd.Timedelta(days=1)])
