"""Daily bars for the scanner universe (tracker/prices_all.pkl tickers + scan_universe*.csv) via yfinance, 2019-01-01..2026-10-07."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import pandas as pd, yfinance as yf, os
OUT = (_SCANNER_ROOT + '/fib-spiral/data/stocks')
p = pd.read_pickle((_SCANNER_ROOT + '/tracker/prices_all.pkl'))
tick = set(p.columns.get_level_values(0).unique())
for f in [(_SCANNER_ROOT + '/scan_universe.csv'), (_SCANNER_ROOT + '/scan_universe_2026-10-04.csv')]:
    tick |= set(pd.read_csv(f)['t'].astype(str))
tick = sorted(t for t in tick if t and not t.endswith('-USD') and t not in ('SPY',)) + ['SPY']
print('n', len(tick), flush=True)
for i in range(0, len(tick), 40):
    ch = [t for t in tick[i:i+40] if not os.path.exists(f'{OUT}/{t}.parquet')]
    if not ch: continue
    d = yf.download(ch, start='2019-01-01', end='2026-10-08', auto_adjust=True, group_by='ticker', progress=False, threads=True)
    for t in ch:
        try:
            x = d[t].dropna(how='all')
            if len(x) > 300:
                x.columns = [c.lower() for c in x.columns]; x.to_parquet(f'{OUT}/{t}.parquet')
        except Exception as e: print(t, 'ERR', e)
    print(i, flush=True)
print('DONE')
