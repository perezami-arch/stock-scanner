"""Crypto leg of the unified scan (08.10.2026). LONGS ONLY, approved crypto rule (scanner_stops RULES): fixed stop = entry - 3xATR14
(Wilder) checked on the daily UTC close, no trailing, NO target. Crypto SHORTS are FROZEN (never output; scanner_stops).
Data: Alpaca crypto daily bars (v1beta3/crypto/us, 1Day, UTC days). Point-in-time: bar D is used only once D+1 00:00 UTC <= cutoff.
Bars are cached per cutoff under <run_dir>/bars/crypto/<SYM>.csv so every downstream module reads the SAME frame (levels JSON).
Selection (deterministic, mirrors the stock LONG filter): close > SMA50 and > SMA200, SMA50 rising (5 bars), close <= SMA20 + 3xATR14;
rank by 12-1 momentum (close[t-21] / close[t-252] - 1, 21-bar skip). Grok is the main sentiment platform for crypto (report order).
Keys: ALPACA_API_KEY_ID / ALPACA_API_SECRET_KEY from env, never printed."""
import os, json, time, hashlib
import numpy as np, pandas as pd, requests

UNIVERSE = os.environ.get('CRYPTO_UNIVERSE', 'BTC,ETH,SOL,XRP,DOGE,AVAX,LINK,LTC,BCH,DOT,UNI,AAVE').split(',')
URL = 'https://data.alpaca.markets/v1beta3/crypto/us/bars'

def alpaca_daily(sym, cutoff_utc, days=600):
    cut = pd.Timestamp(cutoff_utc).tz_convert('UTC')
    h = {'APCA-API-KEY-ID': os.environ.get('ALPACA_API_KEY_ID', ''), 'APCA-API-SECRET-KEY': os.environ.get('ALPACA_API_SECRET_KEY', '')}
    p = {'symbols': f'{sym}/USD', 'timeframe': '1Day', 'start': (cut - pd.Timedelta(days=days)).strftime('%Y-%m-%dT00:00:00Z'),
         'end': cut.strftime('%Y-%m-%dT%H:%M:%SZ'), 'limit': 10000, 'sort': 'asc'}
    rows = []
    for _ in range(10):
        r = requests.get(URL, headers=h, params=p, timeout=30)
        if r.status_code != 200: raise RuntimeError(f'alpaca crypto bars HTTP {r.status_code}')
        d = r.json(); rows += (d.get('bars') or {}).get(f'{sym}/USD') or []
        if not d.get('next_page_token'): break
        p['page_token'] = d['next_page_token']
    if not rows: return None
    x = pd.DataFrame(rows); x['date'] = pd.to_datetime(x['t']).dt.tz_convert('UTC').dt.tz_localize(None).dt.normalize()
    x = x.rename(columns={'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume'}).set_index('date')[['Open', 'High', 'Low', 'Close', 'Volume']]
    x = x[(x.index + pd.Timedelta(days=1)) <= cut.tz_localize(None)]           # PIT: UTC day complete
    return x[~x.index.duplicated(keep='last')]

def alpaca_hourly(sym, cutoff_utc, days=30):
    """Alpaca crypto 1Hour bars (UTC timestamps), only bars COMPLETE at the cutoff (bar start + 1h <= cutoff). Our crypto source
    (Binance/Bybit return 451 from the box). Used by the weight-0 liquidity-sweep view (liq_sweep intraday=True)."""
    cut = pd.Timestamp(cutoff_utc).tz_convert('UTC')
    h = {'APCA-API-KEY-ID': os.environ.get('ALPACA_API_KEY_ID', ''), 'APCA-API-SECRET-KEY': os.environ.get('ALPACA_API_SECRET_KEY', '')}
    p = {'symbols': f'{sym}/USD', 'timeframe': '1Hour', 'start': (cut - pd.Timedelta(days=days)).strftime('%Y-%m-%dT%H:00:00Z'),
         'end': cut.strftime('%Y-%m-%dT%H:%M:%SZ'), 'limit': 10000, 'sort': 'asc'}
    rows = []
    for _ in range(10):
        r = requests.get(URL, headers=h, params=p, timeout=30)
        if r.status_code != 200: raise RuntimeError(f'alpaca crypto 1h bars HTTP {r.status_code}')
        d = r.json(); rows += (d.get('bars') or {}).get(f'{sym}/USD') or []
        if not d.get('next_page_token'): break
        p['page_token'] = d['next_page_token']
    if not rows: return None
    x = pd.DataFrame(rows); x['ts'] = pd.to_datetime(x['t']).dt.tz_convert('UTC').dt.tz_localize(None)
    x = x.rename(columns={'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume'}).set_index('ts')[['Open', 'High', 'Low', 'Close', 'Volume']]
    x = x[(x.index + pd.Timedelta(hours=1)) <= cut.tz_localize(None)]
    return x[~x.index.duplicated(keep='last')]

def bars_path(run_dir, sym): return f'{run_dir}/bars/crypto/{sym}.csv'

def load_bars(run_dir, sym):
    f = bars_path(run_dir, sym)
    return pd.read_csv(f, parse_dates=['date']).set_index('date') if os.path.exists(f) else None

def scan(run_dir, cutoff_utc, top=None):
    """-> list of candidate dicts (same keys the platform layer uses) + writes <run_dir>/crypto_scan.csv."""
    import scanner_stops as ST
    top = int(os.environ.get('PLATFORM_TOP_CRYPTO', '3' if top is None else top))
    os.makedirs(f'{run_dir}/bars/crypto', exist_ok=True)
    out = []
    for s in UNIVERSE:
        s = s.strip().upper()
        try:
            x = alpaca_daily(s, cutoff_utc)
        except Exception as e:
            out.append({'t': s, 'asset': 'crypto', 'err': str(e)[:120]}); continue
        if x is None or len(x) < 260: out.append({'t': s, 'asset': 'crypto', 'err': 'no / <260 daily bars on Alpaca'}); continue
        x.to_csv(bars_path(run_dir, s))
        c = x.Close; a = ST.atr14(x.High.values, x.Low.values, c.values); A = float(a[-1])
        sma20, sma50, sma200 = c.rolling(20).mean(), c.rolling(50).mean(), c.rolling(200).mean()
        px = float(c.iloc[-1]); mom = float(c.iloc[-22] / c.iloc[-253] - 1) if len(c) >= 253 else None
        stp = ST.active_stop(x, 'crypto', 'LONG')
        r = {'t': s, 'asset': 'crypto', 'date': str(x.index[-1].date()), 'px': round(px, 6), 'atr14_wilder': round(A, 6),
             'sma20': round(float(sma20.iloc[-1]), 6), 'sma50': round(float(sma50.iloc[-1]), 6), 'sma200': round(float(sma200.iloc[-1]), 6),
             'slope50': 'up' if sma50.iloc[-1] > sma50.iloc[-6] else 'down', 'ext20atr': round((px - float(sma20.iloc[-1])) / A, 2),
             'r5': round(100 * (px / float(c.iloc[-6]) - 1), 2), 'r15': round(100 * (px / float(c.iloc[-16]) - 1), 2),
             'r60': round(100 * (px / float(c.iloc[-61]) - 1), 2), 'momentum_12_1': None if mom is None else round(mom, 4),
             'initial_stop': stp.get('initial_stop'), 'stop_type': stp.get('stop_type'), 'n_bars': len(x),
             'dolvol_alpaca_m': round(float((x.Close * x.Volume).tail(20).mean()) / 1e6, 2)}
        r['trend_ok'] = bool(px > r['sma50'] and px > r['sma200'] and r['slope50'] == 'up' and r['ext20atr'] <= 3)
        out.append(r)
    d = pd.DataFrame(out); d.to_csv(f'{run_dir}/crypto_scan.csv', index=False)
    ok = d[d.get('trend_ok', pd.Series(False, index=d.index)).fillna(False).astype(bool)].sort_values('momentum_12_1', ascending=False).head(max(top, 0))
    cands = []
    for _, r in ok.iterrows():
        cands.append(dict(r.to_dict(), direction='LONG', entry=float(r['px']), stop=float(r['initial_stop']), target=None,
                          target_note='ללא יעד (כלל קריפטו מאושר) - סטופ קבוע 3xATR14 על סגירה יומית UTC', sector_etf='CRYPTO',
                          rank_score=r['momentum_12_1'], rank_basis='momentum_12_1 (crypto LONG)', mcap_b=None))
    return cands, d

def fetch_news(run_dir, syms, cutoff_utc):
    """Alpaca news for the crypto names -> <run_dir>/news_crypto.json (same layout as news_alpaca.json)."""
    import scanner_news as SN
    allnews = {}
    for s in syms:
        try:
            arts = SN.fetch_news_pit(f'{s}-USD', pd.Timestamp(cutoff_utc).to_pydatetime(), lookback_days=7)
            allnews[s] = [dict(a, after_cutoff=False) for a in arts]
        except Exception:
            allnews[s] = []
    json.dump({'meta': {'cutoff_utc': str(cutoff_utc), 'source': 'alpaca v1beta1/news'}, 'news': allnews},
              open(f'{run_dir}/news_crypto.json', 'w'), ensure_ascii=False, indent=1)
    return allnews
