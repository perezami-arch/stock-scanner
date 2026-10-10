import yfinance as yf, pandas as pd
T=['^VIX','^VIX3M','DX-Y.NYB','^TNX','^IRX','2YY=F','^GSPC','SPY','QQQ','XLK','XLF','XLE','XLV','XLY','XLP','XLI','XLB','XLU','XLRE','XLC']
d=yf.download(T,start='2025-01-01',end='2026-10-01',group_by='ticker',auto_adjust=False,progress=False)
d.to_pickle('macro.pkl')
for t in T:
    s=d[t]['Close'].dropna(); print(t,len(s),s.index[-1].date() if len(s) else None, s.iloc[-1] if len(s) else None)
