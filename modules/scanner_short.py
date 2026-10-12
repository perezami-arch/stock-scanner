"""scanner_short.py - EXPERIMENTAL short-interest / short-volume / squeeze columns (score weight 0). Import-safe.
Added 08.10.2026 (Ilan asked about short squeezes). Out-of-sample rule: memory/stock-scanner/out-of-sample-rule-2026-10-08.txt.

Sources (free, no key)
- FINRA consolidated short interest (bi-monthly), FINRA Query API: POST https://api.finra.org/data/group/otcMarket/name/
  consolidatedShortInterest. PIT key = PUBLICATION date, estimated as settlement + 7 business days (FINRA dissemination
  schedule; NYSE holidays skipped). A setup uses only the latest report with est. publication date < alert date.
- FINRA Reg SHO daily short-volume files: https://cdn.finra.org/equity/regsho/daily/CNMSshvol{YYYYMMDD}.txt (consolidated NMS;
  published the evening of the trade date). A setup uses only files with trade date < alert date. Only the CHANGE of the
  short-volume ratio vs the stock's own 20/60-session history is used (z-scores), never the absolute ratio.
- Float: Yahoo floatShares (current snapshot, NOT point-in-time - flagged); shares outstanding PIT from SEC EDGAR via
  scanner_fundamentals (filed < alert date).
- Borrow fee / utilization: Ortex / S3 are paid -> short_borrow_fee_paid is always null. IBKR's public short-stock file
  (ftp3.interactivebrokers.com, user 'shortstock', usa.txt) is fetched by openbb_snapshot.py (forward-only) when FTP is reachable.

Columns (prefix short_ so tool_stats picks them up)
  short_si_settlement, short_si_pub_est, short_si_shares, short_si_chg_pct (vs previous report), short_si_pct_float,
  short_si_pct_shout, short_si_dtc20 (SI / own 20-session avg volume <= cutoff), short_si_dtc_finra,
  short_svr_z20, short_svr_z60 (z of the 5-session mean daily short-volume ratio vs the prior 20/60 sessions), short_svr_trend
  (5-session mean minus 20-session mean, change only), short_comp_si (si%float >= 15 or dtc20 >= 5), short_comp_trend (close >
  SMA50 and 5d avg volume > 20d avg volume), short_comp_breakout (close > highest high of the prior 20 sessions),
  short_comp_borrow (IBKR fee up / availability down, live only, else null), short_squeeze_candidate = comp_si and (trend or
  breakout), short_borrow_fee_paid (null: paid-only data), short_flag (caveats).
"""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, io, json, time, datetime as dt
import numpy as np, pandas as pd

ROOT = (_SCANNER_ROOT + '/short-data')
SI_URL = 'https://api.finra.org/data/group/otcMarket/name/consolidatedShortInterest'
REGSHO_URL = 'https://cdn.finra.org/equity/regsho/daily/CNMSshvol{d}.txt'
UA = 'Ilan Perets scanner perezami@icloud.com'
SI_PCT_MIN, DTC_MIN = 15.0, 5.0
COLS = ['short_si_settlement', 'short_si_pub_est', 'short_si_shares', 'short_si_chg_pct', 'short_si_pct_float', 'short_si_pct_shout',
        'short_si_dtc20', 'short_si_dtc_finra', 'short_svr_z20', 'short_svr_z60', 'short_svr_trend', 'short_comp_si',
        'short_comp_trend', 'short_comp_breakout', 'short_comp_borrow', 'short_squeeze_candidate', 'short_borrow_fee_paid', 'short_flag']

_NYSE = None
def nyse_bday():
    """CustomBusinessDay on NYSE full-day holidays (federal list minus Columbus/Veterans Day, plus Good Friday)."""
    global _NYSE
    if _NYSE is None:
        from pandas.tseries.holiday import (AbstractHolidayCalendar, Holiday, nearest_workday, USMartinLutherKingJr, USPresidentsDay,
                                            GoodFriday, USMemorialDay, USLaborDay, USThanksgivingDay)
        from pandas.tseries.offsets import CustomBusinessDay
        class NYSE(AbstractHolidayCalendar):
            rules = [Holiday('NewYear', month=1, day=1, observance=nearest_workday), USMartinLutherKingJr, USPresidentsDay, GoodFriday,
                     USMemorialDay, Holiday('Juneteenth', month=6, day=19, start_date='2022-01-01', observance=nearest_workday),
                     Holiday('July4', month=7, day=4, observance=nearest_workday), USLaborDay, USThanksgivingDay,
                     Holiday('Christmas', month=12, day=25, observance=nearest_workday)]
        _NYSE = CustomBusinessDay(calendar=NYSE())
    return _NYSE

def is_nyse_day(d):
    d = pd.Timestamp(d).normalize()
    return d.weekday() < 5 and (d - nyse_bday() + nyse_bday()) == d

def bdays_after(d, n):
    return (pd.Timestamp(d) + n * nyse_bday()).normalize()

# ------------------------------------------------------------------ FINRA short interest
def fetch_si(symbols, start='2025-10-01', end=None, cache=f'{ROOT}/finra_si.csv', max_age_h=12):
    """All reports for `symbols` since `start` (one paged POST per 200 symbols), cached; adds si_pub_est."""
    import requests
    os.makedirs(ROOT, exist_ok=True)
    old = pd.read_csv(cache) if os.path.exists(cache) else pd.DataFrame()
    fresh = os.path.exists(cache) and time.time() - os.path.getmtime(cache) < max_age_h * 3600
    need = sorted(set(symbols) - set(old['symbol'])) if len(old) and fresh else sorted(set(symbols) | (set(old['symbol']) if len(old) else set()))
    rows = []
    F = ['settlementDate', 'symbolCode', 'currentShortPositionQuantity', 'previousShortPositionQuantity', 'averageDailyVolumeQuantity',
         'daysToCoverQuantity', 'changePercent', 'revisionFlag', 'stockSplitFlag']
    from concurrent.futures import ThreadPoolExecutor
    def _chunk(chunk):
        out, off = [], 0
        while True:
            body = {'fields': F, 'domainFilters': [{'fieldName': 'symbolCode', 'values': chunk}], 'limit': 5000, 'offset': off,
                    'dateRangeFilters': [{'fieldName': 'settlementDate', 'startDate': start, 'endDate': end or str(dt.date.today())}]}
            r = requests.post(SI_URL, json=body, headers={'Accept': 'application/json', 'Content-Type': 'application/json', 'User-Agent': UA}, timeout=60)
            r.raise_for_status(); d = r.json() if r.text.strip() else []; out += d
            if len(d) < 5000: return out
            off += 5000
    chunks = [[''.join(ch for ch in s_ if ch.isalnum()) for s_ in need[i:i + 200]] for i in range(0, len(need), 200)]
    with ThreadPoolExecutor(4) as ex: rows = [x for part in ex.map(_chunk, chunks) for x in part]
    if rows:
        n = pd.DataFrame(rows).rename(columns={'symbolCode': 'symbol', 'settlementDate': 'settlement_date', 'currentShortPositionQuantity': 'si',
              'previousShortPositionQuantity': 'si_prev', 'averageDailyVolumeQuantity': 'finra_adv', 'daysToCoverQuantity': 'finra_dtc', 'changePercent': 'chg_pct'})
        _pub = {d: str(bdays_after(d, 7).date()) for d in n['settlement_date'].unique()}
        n['si_pub_est'] = n['settlement_date'].map(_pub)
        old = pd.concat([old[~old['symbol'].isin(n['symbol'].unique())] if len(old) else old, n], ignore_index=True)
        old = old.drop_duplicates(['symbol', 'settlement_date'], keep='last').sort_values(['symbol', 'settlement_date'])
        old.to_csv(cache, index=False)
    if len(old):   # publication estimate always recomputed with the current (NYSE) calendar
        _pub = {d: str(bdays_after(d, 7).date()) for d in old['settlement_date'].unique()}
        old['si_pub_est'] = old['settlement_date'].map(_pub)
    return old

def si_at(si, symbol, alert_date):
    """Latest report with est. publication date < alert date (rule b)."""
    g = si[(si['symbol'] == symbol.replace('-', '').replace('.', '')) & (si['si_pub_est'] < str(alert_date)[:10])]
    return None if g.empty else g.sort_values('settlement_date').iloc[-1]

# ------------------------------------------------------------------ Reg SHO daily short volume
_RS = {}
def regsho_day(d):
    """DataFrame Symbol, ShortVolume, TotalVolume for trade date d (cached; None if no file = holiday/unpublished)."""
    d = pd.Timestamp(d).strftime('%Y%m%d')
    if d in _RS: return _RS[d]
    p = f'{ROOT}/regsho/CNMSshvol{d}.csv.gz'
    if os.path.exists(p): df = pd.read_csv(p)
    else:
        import requests
        r = requests.get(REGSHO_URL.format(d=d), headers={'User-Agent': UA}, timeout=60)
        if r.status_code != 200 or not r.text.startswith('Date'): _RS[d] = None; return None
        df = pd.read_csv(io.StringIO(r.text), sep='|')
        df = df[pd.to_numeric(df['TotalVolume'], errors='coerce').notna()][['Symbol', 'ShortVolume', 'TotalVolume']]
        os.makedirs(os.path.dirname(p), exist_ok=True); df.to_csv(p, index=False, compression='gzip')
    _RS[d] = df.set_index('Symbol')
    return _RS[d]

def svr_series(symbol, sessions):
    """Daily short-volume ratio for the given trade dates (NaN where missing)."""
    out = {}
    for d in sessions:
        f = regsho_day(d)
        if f is None or symbol not in f.index: continue
        x = f.loc[symbol]; tv = float(x['TotalVolume'])
        if tv > 0: out[pd.Timestamp(d)] = float(x['ShortVolume']) / tv
    return pd.Series(out, dtype=float).sort_index()

def svr_features(symbol, sessions_before_alert):
    """sessions_before_alert: trade dates < alert date (ascending). Change-only metrics."""
    s = svr_series(symbol.replace('-', '.'), list(sessions_before_alert)[-65:])
    o = {'short_svr_z20': None, 'short_svr_z60': None, 'short_svr_trend': None}
    if len(s) < 25: return o
    r5 = s.iloc[-5:].mean()
    for n, k in ((20, 'short_svr_z20'), (60, 'short_svr_z60')):
        base = s.iloc[-5 - n:-5]
        if len(base) >= max(15, n // 2) and base.std() > 0: o[k] = round(float((r5 - base.mean()) / base.std()), 3)
    o['short_svr_trend'] = round(float(r5 - s.iloc[-20:].mean()), 4)
    return o

# ------------------------------------------------------------------ price components
def price_components(bars):
    """bars: daily OHLCV up to the cutoff bar (inclusive). Returns comp_trend, comp_breakout, adv20."""
    o = {'short_comp_trend': None, 'short_comp_breakout': None, '_adv20': None}
    if bars is None or len(bars) < 55: return o
    c, v, h = bars['Close'].astype(float), bars['Volume'].astype(float), bars['High'].astype(float)
    sma50 = c.rolling(50).mean().iloc[-1]
    o['short_comp_trend'] = bool(c.iloc[-1] > sma50 and v.iloc[-5:].mean() > v.iloc[-20:].mean())
    o['short_comp_breakout'] = bool(c.iloc[-1] > h.iloc[-21:-1].max())
    o['_adv20'] = float(v.iloc[-20:].mean())
    return o

# ------------------------------------------------------------------ float (Yahoo, current)
def float_shares(symbols, cache=f'{ROOT}/yahoo_float.json', max_age_days=7):
    db = json.load(open(cache)) if os.path.exists(cache) else {}
    if os.path.exists(cache) and time.time() - os.path.getmtime(cache) > max_age_days * 86400: db = {}
    miss = [s for s in symbols if s not in db]
    if miss:
        import yfinance as yf
        for s in miss:
            try: db[s] = yf.Ticker(s).info.get('floatShares')
            except Exception: db[s] = None
        os.makedirs(ROOT, exist_ok=True); json.dump(db, open(cache, 'w'))
    return db

# ------------------------------------------------------------------ combine
def short_columns(symbol, alert_date, bars, si_df, sessions_before_alert, float_sh=None, shares_out=None, borrow=None):
    """All short_* columns for one US stock at one alert (PIT). bars = daily OHLCV up to the cutoff bar."""
    o = {k: None for k in COLS}; flags = ['short_borrow_fee_paid: null - borrow fee/utilization are paid-only (Ortex/S3)']
    pc = price_components(bars); adv20 = pc.pop('_adv20'); o.update(pc)
    r = si_at(si_df, symbol, alert_date) if si_df is not None else None
    if r is not None:
        o.update(short_si_settlement=str(r['settlement_date'])[:10], short_si_pub_est=str(r['si_pub_est'])[:10], short_si_shares=int(r['si']),
                 short_si_dtc_finra=r.get('finra_dtc'))
        if pd.notna(r.get('si_prev')) and r['si_prev'] > 0: o['short_si_chg_pct'] = round(100 * (r['si'] / r['si_prev'] - 1), 2)
        if float_sh: o['short_si_pct_float'] = round(100 * r['si'] / float_sh, 2); flags.append('float = Yahoo current (not PIT)')
        if shares_out: o['short_si_pct_shout'] = round(100 * r['si'] / shares_out, 2)
        if adv20: o['short_si_dtc20'] = round(r['si'] / adv20, 2)
    else: flags.append('no FINRA SI report published before the alert')
    o.update(svr_features(symbol, sessions_before_alert))
    pct = o['short_si_pct_float'] if o['short_si_pct_float'] is not None else o['short_si_pct_shout']
    if pct is not None or o['short_si_dtc20'] is not None:
        o['short_comp_si'] = bool((pct is not None and pct >= SI_PCT_MIN) or (o['short_si_dtc20'] is not None and o['short_si_dtc20'] >= DTC_MIN))
    if borrow:
        o['short_comp_borrow'] = borrow.get('short_comp_borrow')
    if o['short_comp_si'] is not None and (o['short_comp_trend'] is not None or o['short_comp_breakout'] is not None):
        o['short_squeeze_candidate'] = bool(o['short_comp_si'] and (bool(o['short_comp_trend']) or bool(o['short_comp_breakout'])))
    o['short_flag'] = '; '.join(flags)
    return o
