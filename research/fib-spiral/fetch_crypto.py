"""Fetch Binance USDT-M perp 1h OHLCV + funding history via ccxt public endpoints (no keys)."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import ccxt, pandas as pd, time, os, sys, json
OUT = (_SCANNER_ROOT + '/fib-spiral/data')
ex = ccxt.binanceusdm({'enableRateLimit': True, 'timeout': 30000})
mk = ex.load_markets()
START = ex.parse8601('2024-10-01T00:00:00Z')
END = ex.parse8601('2026-10-08T12:00:00Z')   # freeze end of sample (UTC)
tick = ex.fapiPublicGetTicker24hr()
vol = {t['symbol']: float(t['quoteVolume']) for t in tick}
perps = {m['id']: s for s, m in mk.items() if m.get('swap') and m.get('linear') and m['quote'] == 'USDT' and m.get('active')}
ranked = sorted([i for i in perps if i in vol], key=lambda i: -vol[i])
EXCL = {'USDCUSDT', 'FDUSDUSDT', 'BTCDOMUSDT'}
top = [i for i in ranked if i not in EXCL][:100]
for extra in ['PROMUSDT', 'USELESSUSDT']:
    if extra in perps and extra not in top: top.append(extra)
print('n symbols', len(top), 'PROM' , 'PROMUSDT' in perps, 'USELESS', 'USELESSUSDT' in perps, flush=True)
json.dump({'symbols': top, 'vol24h': {i: vol[i] for i in top}, 'start': START, 'end': END}, open(f'{OUT}/universe_crypto.json', 'w'))
def fetch_ohlcv(sym, tf, since, end, path):
    if os.path.exists(path): return
    rows = []; t = since; step = ex.parse_timeframe(tf) * 1000
    while t < end:
        o = ex.fetch_ohlcv(sym, tf, since=t, limit=1500)
        if not o: 
            t += 1500 * step; 
            if t > end: break
            continue
        rows += o; t = o[-1][0] + step
        if len(o) < 2: break
    df = pd.DataFrame(rows, columns=['ts', 'open', 'high', 'low', 'close', 'volume']).drop_duplicates('ts')
    df = df[df.ts < end]
    df.to_parquet(path)
def fetch_funding(sym, since, end, path):
    if os.path.exists(path): return
    rows = []; t = since
    while t < end:
        f = ex.fetch_funding_rate_history(sym, since=t, limit=1000)
        if not f: break
        rows += [(x['timestamp'], x['fundingRate']) for x in f]
        nt = f[-1]['timestamp'] + 1
        if nt <= t or len(f) < 2: break
        t = nt
    df = pd.DataFrame(rows, columns=['ts', 'rate']).drop_duplicates('ts'); df = df[df.ts < end]
    df.to_parquet(path)
import os as _o
SH=int(_o.environ.get('SHARD','0')); NS=int(_o.environ.get('NSHARD','1'))
for i, sid in enumerate(top):
    if i % NS != SH: continue
    s = perps[sid]
    try:
        fetch_ohlcv(s, '1h', START, END, f'{OUT}/crypto_1h/{sid}.parquet')
        fetch_funding(s, START, END, f'{OUT}/funding/{sid}.parquet')
        print(i, sid, 'ok', flush=True)
    except Exception as e:
        print(i, sid, 'ERR', str(e)[:200], flush=True)
# 1m sensitivity sample: PROM, USELESS + 8 liquid names, last 60 days
S1 = ['PROMUSDT', 'USELESSUSDT'] + [x for x in top if x not in ('PROMUSDT', 'USELESSUSDT')][:8]
s1 = END - 60 * 86400 * 1000
for sid in S1:
    if SH != 0: break
    if sid not in perps: continue
    try:
        fetch_ohlcv(perps[sid], '1m', s1, END, f'{OUT}/crypto_1m/{sid}.parquet'); print('1m', sid, 'ok', flush=True)
    except Exception as e: print('1m', sid, 'ERR', str(e)[:200], flush=True)
print('DONE')
