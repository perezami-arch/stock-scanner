import yfinance as yf, pandas as pd, json, datetime as dt
M=json.load(open('auto/symmap.json')); M.pop('_unmapped',None); C=sorted(set(M.values()))
now=pd.Timestamp.now(tz='Asia/Jerusalem')
m=yf.download(C,period='1d',interval='1m',group_by='ticker',auto_adjust=False,progress=False,threads=True)
out={'fetched_at_il':str(now),'crypto':{}}
for t in C:
    try:
        s=m[t].dropna(subset=['Close'])
        if len(s): out['crypto'][t]={'price':float(s['Close'].iloc[-1]),'ts_il':str(s.index[-1].tz_convert('Asia/Jerusalem'))}
    except Exception as e: pass
d=pd.read_pickle('prices_all.pkl'); c=d.xs('Close',axis=1,level=1)
out['stocks_close_date']=str(c.index[-1].date())
out['stocks']={t:float(c[t].dropna().iloc[-1]) for t in c.columns if c[t].notna().any()}
json.dump(out,open('live_snap_2026-10-08.json','w'),indent=1)
ts=sorted(v['ts_il'] for v in out['crypto'].values())
print(now, len(out['crypto']),'/',len(C), ts[0], ts[-1]); print({k:out['crypto'][k] for k in ['BTC-USD','ETH-USD','SOL-USD'] if k in out['crypto']})
