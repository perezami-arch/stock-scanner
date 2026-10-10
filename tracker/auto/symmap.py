import json, yfinance as yf, pandas as pd, numpy as np
R=json.load(open('auto/grok_auto_parsed.json'))
cr=[r for r in R['rows'] if r['asset']=='crypto']
syms=sorted({r['sym'] for r in cr})
T=[s+'-USD' for s in syms]
d=yf.download(T,start='2026-07-10',end='2026-10-04',group_by='ticker',auto_adjust=False,progress=False,threads=True)
d.to_pickle('auto/crypto_daily_probe.pkl')
out={}
for s in syms:
    t=s+'-USD'
    try: c=d[t]['Close'].dropna()
    except Exception: c=pd.Series(dtype=float)
    rs=[r for r in cr if r['sym']==s and r['entry']]
    ratios=[]
    for r in rs:
        x=c[c.index<=pd.Timestamp(r['date'])]
        if len(x): ratios.append(r['entry']/x.iloc[-1])
    out[s]=dict(n=len([r for r in cr if r['sym']==s]),bars=len(c),med_ratio=(float(np.median(ratios)) if ratios else None),last=(float(c.iloc[-1]) if len(c) else None))
    print(s,out[s])
json.dump(out,open('auto/symprobe.json','w'),indent=1)
