import ccxt, pandas as pd, numpy as np, fib_spiral as FS, os, json
ex = ccxt.binanceusdm({'enableRateLimit': True})
rows=[]; t=ex.parse8601('2026-07-15T00:00:00Z')
while t < ex.parse8601('2026-09-10T00:00:00Z'):
    o = ex.fetch_ohlcv('PROM/USDT:USDT', '1h', since=t, limit=1000); rows+=o; t=o[-1][0]+3600000
d = pd.DataFrame(rows, columns=['ts','open','high','low','close','volume']).drop_duplicates('ts')
d.index = pd.to_datetime(d.ts, unit='ms', utc=True).dt.tz_convert('Asia/Jerusalem'); d = d.drop(columns='ts')
d = d.loc[:'2026-09-09']
o,h,l,c = FS._arrays(d,'SHORT'); a=FS.atr14(h,l,c); piv=FS.zigzag(h,l,a,3.0)
for p in piv:
    if d.index[p[2]] >= pd.Timestamp('2026-08-27', tz='Asia/Jerusalem') and d.index[p[2]] <= pd.Timestamp('2026-09-02', tz='Asia/Jerusalem'):
        print(p[0], round(p[1],3), d.index[p[2]], 'conf', d.index[p[3]])
for fans in ('F9','F5'):
    ev,_ = FS.find_events(d,'crypto',fans)
    for e in ev:
        if pd.Timestamp('2026-08-29', tz='Asia/Jerusalem') <= e['fs_D_time'] <= pd.Timestamp('2026-08-31', tz='Asia/Jerusalem'):
            print(fans, {k:(round(v,3) if isinstance(v,float) else v) for k,v in e.items() if k not in ('fs_levels','fs_time_zones')})
            print({k:round(v,3) for k,v in e['fs_levels'].items()})
