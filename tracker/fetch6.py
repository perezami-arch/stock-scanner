import yfinance as yf, pandas as pd, json, os
from alerts import all_alerts
A=all_alerts()
T=sorted({a['ticker'] for a in A if a.get('ttype')!='קריפטו'})
d=yf.download(T,start='2025-07-01',end='2026-10-09',group_by='ticker',auto_adjust=False,progress=False,threads=True)
d.to_pickle('prices_all.pkl')
info=json.load(open('info_all.json'))
for t in T:
    if t in info and info[t].get('mcap'): continue
    try:
        fi=yf.Ticker(t).fast_info; info[t]={'mcap':fi.market_cap,'last':fi.last_price,'name':None,'fetched':'2026-10-08'}
    except Exception as e: info[t]={'err':str(e)}
json.dump(info,open('info_all.json','w'),indent=1,default=str)
for t in T:
    df=d[t].dropna(subset=['Close']) if t in d.columns.get_level_values(0) else []
    if len(df)==0: print('NO DATA',t)
print('stocks last',d.index[-1],len(T))
M=json.load(open('auto/symmap.json')); M.pop('_unmapped'); C=sorted(set(M.values()))
dd=yf.download(C,start='2026-07-01',end='2026-10-09',group_by='ticker',auto_adjust=False,progress=False,threads=True); dd.to_pickle('auto/crypto_daily.pkl')
hh=yf.download(C,start='2026-07-15',end='2026-10-09',interval='1h',group_by='ticker',auto_adjust=False,progress=False,threads=True); hh.to_pickle('auto/crypto_1h.pkl')
ci=json.load(open('auto/crypto_info.json'))
for t in C:
    if t in ci and ci[t].get('mcap'): continue
    try:
        i=yf.Ticker(t).info; ci[t]=dict(mcap=i.get('marketCap'),last=i.get('regularMarketPrice') or i.get('previousClose'),name=i.get('shortName'))
    except Exception as e: ci[t]={'err':str(e)}
json.dump(ci,open('auto/crypto_info.json','w'),indent=1)
print('crypto',dd.index[-1],hh.index[-1],len(C))
