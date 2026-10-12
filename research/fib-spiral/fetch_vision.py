"""Bulk klines from data.binance.vision (public Binance USDT-M dumps; fapi REST became geo-blocked (451) on 10.10)."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import sys, io, zipfile, os, requests, pandas as pd, datetime as dt
from concurrent.futures import ThreadPoolExecutor
B = 'https://data.binance.vision/data/futures/um'
COLS = ['ts', 'open', 'high', 'low', 'close', 'volume']
def get(url):
    r = requests.get(url, timeout=60)
    if r.status_code != 200: return None
    z = zipfile.ZipFile(io.BytesIO(r.content)); f = z.open(z.namelist()[0])
    d = pd.read_csv(f, header=None)
    if not str(d.iloc[0, 0]).isdigit(): d = d.iloc[1:]
    d = d.iloc[:, :6]; d.columns = COLS; return d.astype({'ts': 'int64', 'open': float, 'high': float, 'low': float, 'close': float, 'volume': float})
def fetch(sym, tf, start, end, path):
    """start/end: date; months fully inside via monthly zips, the rest via daily zips."""
    if os.path.exists(path): return 'skip'
    urls = []; d = start.replace(day=1)
    while d <= end:
        nm = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        if nm - dt.timedelta(days=1) <= end and d >= start.replace(day=1):
            urls.append(f'{B}/monthly/klines/{sym}/{tf}/{sym}-{tf}-{d:%Y-%m}.zip')
        else:
            x = max(d, start)
            while x < nm and x <= end:
                urls.append(f'{B}/daily/klines/{sym}/{tf}/{sym}-{tf}-{x:%Y-%m-%d}.zip'); x += dt.timedelta(days=1)
        d = nm
    with ThreadPoolExecutor(8) as ex: parts = [p for p in ex.map(get, urls) if p is not None]
    if not parts: return 'none'
    df = pd.concat(parts).drop_duplicates('ts').sort_values('ts')
    s0 = int(pd.Timestamp(start, tz='UTC').timestamp() * 1000); e0 = int((pd.Timestamp(end, tz='UTC') + pd.Timedelta(days=1)).timestamp() * 1000)
    df = df[(df.ts >= s0) & (df.ts < e0)].reset_index(drop=True); df.to_parquet(path); return len(df)
if __name__ == '__main__':
    import json
    job = sys.argv[1]
    U = json.load(open((_SCANNER_ROOT + '/fib-spiral/data/universe_crypto.json')))['symbols']
    NC = set(json.load(open((_SCANNER_ROOT + '/fib-spiral/data/noncrypto.json'))))
    CR = [s for s in U if s not in NC]
    if job == 'ake':
        print(fetch('AKEUSDT', '1h', dt.date(2024, 10, 1), dt.date(2026, 10, 7), (_SCANNER_ROOT + '/fib-spiral/data/crypto_1h/AKEUSDT.parquet')))
    if job == '15m':
        os.makedirs((_SCANNER_ROOT + '/liq-sweep/data/crypto_15m'), exist_ok=True)
        for s in CR: print(s, fetch(s, '15m', dt.date(2025, 10, 1), dt.date(2026, 10, 7), f'{_SCANNER_ROOT}/liq-sweep/data/crypto_15m/{s}.parquet'), flush=True)
    if job == '1m':
        os.makedirs((_SCANNER_ROOT + '/liq-sweep/data/crypto_1m'), exist_ok=True)
        S1 = ['PROMUSDT', 'USELESSUSDT'] + [s for s in CR if s not in ('PROMUSDT', 'USELESSUSDT')][:28]
        for s in S1: print(s, fetch(s, '1m', dt.date(2026, 7, 1), dt.date(2026, 10, 7), f'{_SCANNER_ROOT}/liq-sweep/data/crypto_1m/{s}.parquet'), flush=True)
    print('DONE')
