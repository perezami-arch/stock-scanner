import json, yfinance as yf, pandas as pd
M=json.load(open('auto/symmap.json')); M.pop('_unmapped')
T=sorted(set(M.values()))
dd=yf.download(T,start='2026-07-01',end='2026-10-04',group_by='ticker',auto_adjust=False,progress=False,threads=True); dd.to_pickle('auto/crypto_daily.pkl')
hh=yf.download(T,start='2026-07-15',end='2026-10-04',interval='1h',group_by='ticker',auto_adjust=False,progress=False,threads=True); hh.to_pickle('auto/crypto_1h.pkl')
info={}
for t in T:
    try:
        i=yf.Ticker(t).info; info[t]=dict(mcap=i.get('marketCap'),last=i.get('regularMarketPrice') or i.get('previousClose'),name=i.get('shortName'))
    except Exception as e: info[t]={'err':str(e)}
json.dump(info,open('auto/crypto_info.json','w'),indent=1)
print(dd.index[-1], hh.index[0], hh.index[-1], len(T))
