import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import yfinance as yf
import pandas as pd
import numpy as np
import os, sys
from datetime import datetime, timedelta
# 2026-10-08: 12-1 momentum score component (validated code from /workspace/scanner-tool-eval, see scanner_momentum.py)
sys.path.insert(0, _SCANNER_ROOT)
import scanner_momentum as SM
import scanner_stops as ST   # 2026-10-08: approved active stops + experimental Fib/Elliott columns
import scanner_newsmacro as NM   # 2026-10-08: LOGGED-ONLY news (Alpaca) + 10Y-rate betas + AAII/yields, weight 0
import scanner_geometry as GEO, time   # 2026-10-08: EXPERIMENTAL Fib spiral / Gann / volume profile / candles, weight 0
import scanner_fundamentals as FUND   # 2026-10-08: LOGGED-ONLY PIT fundamentals (SEC EDGAR companyfacts), weight 0
import scanner_short as SHORT   # 2026-10-08: EXPERIMENTAL short interest / Reg SHO short volume / squeeze_candidate, weight 0

tickers = [
    'SPY','QQQ','IWM','XLK','XLF','XLE','XLV','XLY','XLP','XLU','SMH','XBI','XLI','XLB','XLRE',
    'MU','AMD','NVDA','AVGO','KLAC','AMAT','MRVL','INTC','ASML','TSM','LRCX','QCOM','TXN','ADI',
    'TSLA','AAPL','MSFT','META','GOOGL','AMZN','NFLX','SHOP','UBER','ABNB',
    'JPM','BAC','GS','MS','V','MA','C','WFC','BLK','SCHW',
    'XOM','CVX','COP','SLB','EOG','OXY',
    'UNH','LLY','MRK','PFE','ABBV','JNJ','AMGN','ISRG','TMO',
    'HD','COST','WMT','PG','KO','MCD','NKE','SBUX','TGT',
    'FICO','CRM','NOW','PANW','CRWD','PLTR','ORCL','IBM','ADBE','INTU','SNOW',
    'CAT','GE','BA','RTX','DE','URI','HON','MMM','LMT',
    'NEE','SO','DUK','AEP','D','SRE',
    'DIS','CMCSA','T','VZ','NFLX',
    '^VIX','^TNX','^TYX','GLD','TLT','HYG','LQD'
]
# optional extra names for this run, e.g. SCAN_EXTRA_TICKERS=NAVN,MDLN (young names are kept, never silently dropped)
tickers += [x.strip().upper() for x in os.environ.get('SCAN_EXTRA_TICKERS', '').split(',') if x.strip()]
ETF_LIKE = {'SPY','QQQ','IWM','XLK','XLF','XLE','XLV','XLY','XLP','XLU','SMH','XBI','XLI','XLB','XLRE','GLD','TLT','HYG','LQD'}
# unique preserve order
_seen=set(); tickers=[x for x in tickers if not (x in _seen or _seen.add(x))]

# scan moment (UTC). Default = now; SCAN_ASOF=2026-10-11T06:00Z reproduces a past run. All momentum inputs are cut at it.
SCAN_ASOF = pd.Timestamp(os.environ['SCAN_ASOF']) if os.environ.get('SCAN_ASOF') else pd.Timestamp.now(tz='UTC')
if SCAN_ASOF.tzinfo is None: SCAN_ASOF = SCAN_ASOF.tz_localize('Asia/Jerusalem')
SCAN_ASOF = SCAN_ASOF.tz_convert('UTC')
OUTDIR = f"{_SCANNER_ROOT}/scan-runs/{SCAN_ASOF.tz_convert('Asia/Jerusalem').strftime('%Y-%m-%d_%H%M')}"   # dated: old outputs are never overwritten
os.makedirs(OUTDIR, exist_ok=True)
end = datetime(SCAN_ASOF.year, SCAN_ASOF.month, SCAN_ASOF.day) + timedelta(days=1)   # yfinance end is exclusive
start = end - timedelta(days=420)
data = yf.download(tickers, start=start.strftime('%Y-%m-%d'), end=end.strftime('%Y-%m-%d'),
                   group_by='ticker', auto_adjust=True, threads=True, progress=False)

def get_df(t):
    if isinstance(data.columns, pd.MultiIndex):
        if t not in data.columns.get_level_values(0):
            return None
        df = data[t].dropna(how='all').copy()
        # drop incomplete last bar (Close NaN)
    else:
        df = data.copy()
    if df is None or df.empty or len(df)<60:
        return None   # <60 bars: no technicals, but the row is still written (see loop) with neutral momentum + flag
    df = df.rename(columns=str.title)
    if 'Close' in df.columns:
        df = df.dropna(subset=['Close'])
    for c in ['Open','High','Low','Close','Volume']:
        if c not in df.columns:
            return None
    return df

def atr(df, n=14):
    h,l,c = df['High'], df['Low'], df['Close']
    prev = c.shift(1)
    tr = pd.concat([(h-l),(h-prev).abs(),(l-prev).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def ema(s,n): return s.ewm(span=n, adjust=False).mean()
def sma(s,n): return s.rolling(n).mean()

def rsi(s,n=14):
    d = s.diff()
    up = d.clip(lower=0).rolling(n).mean()
    dn = (-d.clip(upper=0)).rolling(n).mean()
    rs = up/dn.replace(0,np.nan)
    return 100 - (100/(1+rs))

rows=[]
detailed = {}
for t in tickers:
    df = get_df(t)
    if df is None:
        rows.append({'t':t,'err':'no data / <60 bars'}); continue
    c = df['Close']
    last = float(c.iloc[-1])
    last_date = str(c.index[-1].date())
    a = atr(df)
    atr14 = float(a.iloc[-1]) if pd.notna(a.iloc[-1]) else np.nan
    sma20=float(sma(c,20).iloc[-1]); sma50=float(sma(c,50).iloc[-1])
    sma100=float(sma(c,100).iloc[-1]) if len(c)>=100 else np.nan
    sma200=float(sma(c,200).iloc[-1]) if len(c)>=200 else np.nan
    e9=float(ema(c,9).iloc[-1]); e21=float(ema(c,21).iloc[-1])
    r = float(rsi(c).iloc[-1])
    vol20 = float(df['Volume'].rolling(20).mean().iloc[-1])
    dolvol = last * vol20
    def ret(n):
        if len(c)<=n: return np.nan
        return (last/float(c.iloc[-1-n])-1)*100
    r15=ret(15); r60=ret(60); r252=ret(min(252,len(c)-1)); r5=ret(5)
    ext20 = (last-sma20)/atr14 if atr14 and atr14>0 else np.nan
    ext50 = (last-sma50)/atr14 if atr14 and atr14>0 else np.nan
    v15 = float(df['Volume'].iloc[-15:].mean())
    vratio = v15/vol20 if vol20 else np.nan
    lb = df.iloc[-1]
    rng = float(lb['High']-lb['Low']) or 1e-9
    close_loc = (float(lb['Close'])-float(lb['Low']))/rng
    vol_x = float(lb['Volume'])/vol20 if vol20 else np.nan
    h60=float(df['High'].iloc[-60:].max()); l60=float(df['Low'].iloc[-60:].min())
    h15=float(df['High'].iloc[-15:].max()); l15=float(df['Low'].iloc[-15:].min())
    window=df.iloc[-60:]
    piv_hi_idx = window['High'].idxmax(); piv_lo_idx = window['Low'].idxmin()
    s50 = sma(c,50)
    slope50 = 'up' if float(s50.iloc[-1])>float(s50.iloc[-6]) else ('down' if float(s50.iloc[-1])<float(s50.iloc[-6]) else 'flat')
    s200 = sma(c,200) if len(c)>=200 else None
    slope200 = '~'
    if s200 is not None and pd.notna(s200.iloc[-1]) and pd.notna(s200.iloc[-6]):
        slope200 = 'up' if float(s200.iloc[-1])>float(s200.iloc[-6]) else ('down' if float(s200.iloc[-1])<float(s200.iloc[-6]) else 'flat')
    stack='bull' if e9>e21>sma50 and (np.isnan(sma200) or sma50>sma200) else ('bear' if e9<e21<sma50 else 'mixed')
    mcap=None
    try:
        info = yf.Ticker(t).fast_info
        mcap = getattr(info,'market_cap', None)
    except Exception:
        pass
    # swing pivots for elliott: local extrema
    highs = []
    lows = []
    for i in range(2, len(df)-2):
        if df['High'].iloc[i] == df['High'].iloc[i-2:i+3].max():
            highs.append((str(df.index[i].date()), float(df['High'].iloc[i])))
        if df['Low'].iloc[i] == df['Low'].iloc[i-2:i+3].min():
            lows.append((str(df.index[i].date()), float(df['Low'].iloc[i])))
    recent_highs = highs[-8:]
    recent_lows = lows[-8:]
    # last 15 OHLCV summary
    last15 = df.iloc[-15:][['Open','High','Low','Close','Volume']].copy()
    last15['volx'] = last15['Volume']/vol20
    detailed[t] = {
        'last15': last15.round(2).to_string(),
        'highs': recent_highs,
        'lows': recent_lows,
        'ohlcv_tail': df.iloc[-5:][['Open','High','Low','Close','Volume']].round(2).to_string()
    }
    rows.append({
        't':t,'date':last_date,'px':round(last,2),'atr14':round(atr14,2) if pd.notna(atr14) else None,
        'atr_pct':round(100*atr14/last,2) if pd.notna(atr14) else None,
        'sma20':round(sma20,2),'sma50':round(sma50,2),'sma200':round(sma200,2) if pd.notna(sma200) else None,
        'ema9':round(e9,2),'ema21':round(e21,2),'rsi':round(r,1),
        'ext20atr':round(ext20,2) if pd.notna(ext20) else None,
        'ext50atr':round(ext50,2) if pd.notna(ext50) else None,
        'r5':round(r5,2) if pd.notna(r5) else None,
        'r15':round(r15,2) if pd.notna(r15) else None,
        'r60':round(r60,2) if pd.notna(r60) else None,
        'r252':round(r252,2) if pd.notna(r252) else None,
        'dolvol_m':round(dolvol/1e6,1) if pd.notna(dolvol) else None,
        'mcap_b':round(mcap/1e9,1) if mcap else None,
        'vratio15':round(vratio,2) if pd.notna(vratio) else None,
        'last_volx':round(vol_x,2) if pd.notna(vol_x) else None,
        'close_loc':round(close_loc,2),
        'h60':round(h60,2),'l60':round(l60,2),'h15':round(h15,2),'l15':round(l15,2),
        'slope50':slope50,'slope200':slope200,'stack':stack,
        'hi60d':str(piv_hi_idx.date()),'lo60d':str(piv_lo_idx.date()),
    })

out=pd.DataFrame(rows)
# ---- 12-1 momentum (weighted score component, 10/100) + low-vol 60d (experimental, logged only) ----
print(f'MOMENTUM 12-1: point-in-time cut at {SCAN_ASOF:%Y-%m-%d %H:%M} UTC')
_mc = {r['t']: ('n/a' if r['t'] in ETF_LIKE else (r['mcap_b']*1e9 if r.get('mcap_b') else None)) for r in rows}
mom = SM.compute([(t,'stock') for t in out['t'] if not t.startswith('^')], asof=SCAN_ASOF, mcaps=_mc, verbose=False)
out = out.merge(mom.drop(columns=['asset','mcap_b']).rename(columns={'ticker':'t'}), on='t', how='left')
out['mcap_ok'] = out['t'].isin(ETF_LIKE) | (out['mcap_b'].fillna(0) >= SM.MCAP_FLOOR_USD/1e9)   # $1.5B floor, US stocks
# ---- ACTIVE STOPS (approved 08.10, v2 13:28): LONG view = chandelier 4xATR14 (close) + 1/2 at Fib 1.618; SHORT only if the short rule passes = chandelier 4xATR14.
#      Reference entry = last close until the setup has a trigger price. Experimental Fib/Elliott columns = LONG view, logged only.
_px_dir = f"{SM.CACHE_ROOT}/{SCAN_ASOF.strftime('%Y%m%dT%H%MZ')}"
_st = []
for t in out['t']:
    if t.startswith('^'): continue
    b = ST.daily_bars(t, 'stock', SCAN_ASOF, _px_dir)
    if b is None or len(b) < 15: _st.append({'t': t, 'stop_type': 'no data / <15 bars'}); continue
    L = ST.active_stop(b, 'stock', 'LONG'); S_ = ST.active_stop(b, 'stock', 'SHORT')
    rec = {'t': t, **{k: L[k] for k in ('stop_type','stop_atr_mult','atr14_wilder','stop_entry_ref','initial_stop','initial_stop_pct','tp_half_1618','partial_exit_rule','tp_half_fallback')},
           'short_rule_pass': S_['short_rule_pass'], 'short_ck_score': S_['short_ck_score'], 'below_sma200': S_['below_sma200'],
           'short_stop_type': S_['stop_type'], 'short_stop_atr_mult': S_['stop_atr_mult'], 'short_initial_stop': S_['initial_stop']}
    rec.update(ST.fib_elliott(b, 'stock', 'LONG'))
    _st.append(rec)
out = out.merge(pd.DataFrame(_st), on='t', how='left')
# ---- LOGGED ONLY (08.10, Ilan): per-ticker news before the PIT cutoff + 10Y-rate beta of ticker & sector + AAII/yields. Weight 0, to be backtested.
try:
    _sess = data['SPY'].dropna(how='all').index if isinstance(data.columns, pd.MultiIndex) and 'SPY' in data.columns.get_level_values(0) else None
    _skip = set(out.loc[~out['mcap_ok'].astype(bool), 't'])          # $1.5B floor: no news query for names below it
    _nm, _regime, _cut = NM.enrich(list(out['t']), SCAN_ASOF, OUTDIR, etf_like=ETF_LIKE, skip=_skip, asset='stock', sessions=_sess, verbose=False)
    out = out.merge(_nm, on='t', how='left')
    print(f"\n=== NEWS + RATES + MACRO (logged only, weight 0) - PIT cutoff {_cut:%Y-%m-%d %H:%M} UTC ===")
    print(f"US10Y {_regime['US10Y']['value']} ({_regime['US10Y']['chg_20d_bp']:+} bp 20d) | 2s10s {_regime['us2y10y_spread'].get('value')} | AAII bull-bear {_regime['aaii'].get('bull_bear_spread')} ({_regime['aaii'].get('date')})")
    print(out[~out['t'].str.startswith('^')][['t','news_count_7d','news_count_7d_focused','news_last_ts','sector_etf','rate_beta_ticker_60d','rate_beta_sector_60d','news_flag']].to_string(index=False))
except Exception as _e:   # never break the scan on a logged-only block
    print(f'NEWS/MACRO logged-only block failed: {_e.__class__.__name__}: {_e}')
# ---- EXPERIMENTAL geometry / volume / candles / liquidity (08.10, Ilan): Fib spiral, Gann box+angles, volume profile (60/120/anchor
#      daily + 20d Alpaca 1-min), candle patterns, liquidity pools/sweeps/FVG/order blocks (liq_*, each with confirmed_at). LOGGED ONLY (weight 0). Same PIT daily bars and same confirmed 2xATR swing
#      as the Fib/Elliott columns (scanner_geometry.py). Only US names that pass the $1.5B floor (+ ETFs).
try:
    _gi = os.environ.get('SCAN_GEOM_INTRADAY', '1') == '1'; _gbud = float(os.environ.get('SCAN_GEOM_INTRADAY_BUDGET_S', '300')); _gt0 = time.time()
    _geo = []
    for t, _ok in zip(out['t'], out['mcap_ok']):
        if t.startswith('^'): continue
        if not bool(_ok): _geo.append({'t': t, 'geo_flag': 'MCAP<1.5B / not verified - not computed'}); continue
        b = ST.daily_bars(t, 'stock', SCAN_ASOF, _px_dir)
        if b is None or len(b) < 30: _geo.append({'t': t, 'geo_flag': 'no data / <30 bars'}); continue
        _intr = _gi and (time.time() - _gt0) < _gbud
        _g = GEO.geometry_columns(b, cutoff=SCAN_ASOF, asset='stock', direction='LONG', intraday=_intr, symbol=t)
        if _gi and not _intr: _g['vp20m_flag'] = 'skipped (time budget)'
        _geo.append({'t': t, **_g})
    out = out.merge(pd.DataFrame(_geo), on='t', how='left')
    print(f"\n=== EXPERIMENTAL geometry/volume/candles (logged only, weight 0) - {time.time()-_gt0:.0f}s ===")
    _GC = [c for c in ['t','px','exp_spiral_near_arc','exp_spiral_next_node_date','exp_gann_level_below','exp_gann_level_above','exp_gann_next_time_date','vp60_poc','vp60_va_pos','vp60_poc_dist_atr','vp20m_poc','candle_patterns_last','candle_bias_last','candle_vol_confirmed','liq_bsl_level','liq_bsl_touches','liq_ssl_level','liq_ssl_touches','liq_sweep_last'] if c in out.columns]
    print(out[~out['t'].str.startswith('^')][_GC].to_string(index=False))
except Exception as _e:   # never break the scan on a logged-only block
    print(f'GEOMETRY logged-only block failed: {_e.__class__.__name__}: {_e}')
# ---- WATCH ONLY (08.10, researcher §3.14): stock SHORT that passes the short rule AND close below 120-day VP value-area low.
#      vp120 rolling profile is direction-independent (same VAL for LONG/SHORT view). Weight 0; no effect on score/stops/targets.
try:
    _pass = out['short_rule_pass'].fillna(False).astype(bool)
    _pos = out['vp120_va_pos'] if 'vp120_va_pos' in out.columns else pd.Series([None]*len(out), index=out.index)
    _below = _pos.eq('below VA')
    _fallback = False
    if 'vp120_val' in out.columns:
        _fallback = _pos.isna() | _pos.eq('') | _pos.astype(str).eq('nan')
        _below = _below | (_fallback & out['px'].notna() & out['vp120_val'].notna() & (out['px'] < out['vp120_val']))
    _watch = pd.Series(pd.NA, index=out.index, dtype='Int64')
    _watch.loc[_pass & _below] = 1
    _has_vp = _pos.notna() & ~_pos.astype(str).isin(['nan',''])
    if 'vp120_val' in out.columns: _has_vp = _has_vp | out['vp120_val'].notna()
    _watch.loc[_pass & ~_below & _has_vp] = 0
    # rule-passers with no VP data stay <NA>
    out = out.copy()
    out['watch_short_below_va120'] = _watch
    _w = out[out['watch_short_below_va120'].notna() & ~out['t'].str.startswith('^')]
    print(f"\n=== WATCH short below VA120 (logged only, weight 0) - {int((_w['watch_short_below_va120']==1).sum())} flagged / {len(_w)} short-rule passers ===")
    if len(_w):
        print(_w[['t','px','short_rule_pass','short_ck_score','vp120_val','vp120_va_pos','watch_short_below_va120']].to_string(index=False))
except Exception as _e:
    print(f'WATCH VA120 logged-only block failed: {_e.__class__.__name__}: {_e}')
# ---- LOGGED ONLY (08.10, Ilan: "סור גם פן פונדמנטלי פי אי וכל מה שנגזר"): PIT fundamentals from SEC EDGAR companyfacts.
#      R1 filings with filed < alert date (ET date of the scan); price = close of the last bar complete at the scan (the PIT cutoff);
#      shares as filed. Sector percentile among this scan's US stocks (same sector map as news/rates). *_live = Yahoo snapshot,
#      never backtested. Weight 0 (out-of-sample-rule-2026-10-08.txt). Only names that pass the $1.5B floor.
try:
    _ft0 = time.time(); _alert = SCAN_ASOF.tz_convert('America/New_York').date()
    _fpx, _fcut = {}, {}
    for t, _ok in zip(out['t'], out['mcap_ok']):
        if t.startswith('^') or t in ETF_LIKE or not bool(_ok): continue
        b = ST.daily_bars(t, 'stock', SCAN_ASOF, _px_dir)
        if b is None or not len(b): continue
        _fpx[t] = float(b['Close'].iloc[-1]); _fcut[t] = pd.Timestamp(b.index[-1]).date()
    _fc = max(_fcut.values()) if _fcut else (SCAN_ASOF - pd.Timedelta(days=1)).date()
    _skip = set(out.loc[~out['mcap_ok'].astype(bool), 't'])
    _fd = FUND.enrich_live({t: _fpx.get(t) for t in out['t'] if not t.startswith('^')}, _fc, _alert, etf_like=ETF_LIKE,
                           skip=_skip, live=os.environ.get('SCAN_FUND_LIVE', '1') == '1')
    for t, d_ in _fcut.items():   # per-ticker cutoff (normally identical for all names)
        if d_ != _fc: _fd.loc[_fd['t'] == t, 'fund_cutoff_date'] = str(d_)
    out = out.merge(_fd, on='t', how='left')
    print(f"\n=== FUNDAMENTALS PIT (logged only, weight 0) - filings filed < {_alert}, price = close {_fc} - {time.time()-_ft0:.0f}s ===")
    _FC = [c for c in ['t','px','pe_ttm','pe_sector_pctile','fund_sector_etf','ps_ttm','pb','ev_ebitda','fcf_yield','peg','rev_growth_yoy','eps_growth_yoy','op_margin','roe','debt_to_equity','fund_last_filed','forward_pe_live','next_earnings_date_live','fund_flag'] if c in out.columns]
    print(out[~out['t'].str.startswith('^') & ~out['t'].isin(ETF_LIKE)][_FC].to_string(index=False))
except Exception as _e:   # never break the scan on a logged-only block
    print(f'FUNDAMENTALS logged-only block failed: {_e.__class__.__name__}: {_e}')
# ---- EXPERIMENTAL short data (08.10, Ilan: short squeezes): FINRA SI keyed to est. PUBLICATION date (< alert date), Reg SHO
#      short-volume change z-scores (files < alert date), short_squeeze_candidate = (SI%float>=15 or DTC20>=5) and (close>SMA50 with
#      rising volume, or 20d breakout). Borrow fee is paid-only (null). Weight 0. US names that pass the $1.5B floor only.
try:
    _st0 = time.time(); _sal = str(SCAN_ASOF.tz_convert('America/New_York').date())
    _sn = [t for t, _ok in zip(out['t'], out['mcap_ok']) if bool(_ok) and not t.startswith('^') and t not in ETF_LIKE]
    _si = SHORT.fetch_si(_sn, start=str((SCAN_ASOF - pd.Timedelta(days=200)).date()))
    _sess = [d for d in pd.date_range(end=SCAN_ASOF.tz_convert('America/New_York').date(), periods=96, freq=SHORT.nyse_bday()) if d < pd.Timestamp(_sal)]
    _sess = [d for d in _sess if SHORT.regsho_day(d) is not None]
    _fl = SHORT.float_shares(_sn); _sh = []
    for t in _sn:
        b = ST.daily_bars(t, 'stock', SCAN_ASOF, _px_dir)
        _so = out.loc[out['t'] == t, 'fund_shares'].iloc[0] if 'fund_shares' in out.columns else None
        _sh.append({'t': t, **SHORT.short_columns(t, _sal, b, _si, _sess, float_sh=_fl.get(t), shares_out=_so if pd.notna(_so) else None)})
    out = out.merge(pd.DataFrame(_sh), on='t', how='left')
    print(f"\n=== SHORT DATA / squeeze_candidate (experimental, weight 0) - {time.time()-_st0:.0f}s ===")
    _SC = [c for c in ['t','px','short_si_settlement','short_si_pub_est','short_si_pct_float','short_si_dtc20','short_si_chg_pct','short_svr_z20','short_svr_z60','short_comp_si','short_comp_trend','short_comp_breakout','short_squeeze_candidate'] if c in out.columns]
    print(out[out['t'].isin(_sn)][_SC].to_string(index=False))
except Exception as _e:   # never break the scan on an experimental block
    print(f'SHORT DATA experimental block failed: {_e.__class__.__name__}: {_e}')
out.to_csv(f'{OUTDIR}/scan_raw.csv', index=False, encoding='utf-8-sig')
MCOLS=['t','momentum_12_1','momentum_score','momentum_points','missing_history_flag','lowvol_60d','lowvol_score','excluded_reason']
print('\n=== MOMENTUM 12-1 (score component 10/100; lowvol = experimental, weight 0) ===')
print(out[~out['t'].str.startswith('^')].sort_values('momentum_score',ascending=False)[MCOLS].to_string(index=False))
print('\n=== ACTIVE STOPS (LONG chandelier 4xATR14 close + 1/2 at Fib 1.618; SHORT chandelier 4xATR14 only if short rule passes) + EXPERIMENTAL fib/elliott ===')
SCOLS=['t','px','atr14_wilder','initial_stop','initial_stop_pct','tp_half_1618','tp_half_fallback','short_rule_pass','short_initial_stop','fib_stop_struct','elliott_count_valid','elliott_wave_label','elliott_target_w3','elliott_target_w5']
print(out[~out['t'].str.startswith('^')][SCOLS].to_string(index=False))
out.to_csv(f'{OUTDIR}/scan_raw.csv', index=False, encoding='utf-8-sig')
liq = out[(out['dolvol_m'].fillna(0)>14) & (out['px'].fillna(0)>=5) & out['mcap_ok']].copy()
print('LAST DATES', out['date'].value_counts().head().to_string())
print('\n=== ETFs ===')
cols=['t','date','px','r5','r15','r60','rsi','sma50','slope50','stack','ext20atr']
print(out[out['t'].isin(['SPY','QQQ','IWM','XLK','SMH','XLF','XLE','XLV','XLY','XLP','XLU','^VIX','^TNX','^TYX'])][cols].to_string(index=False))
print('\n=== TOP r15 liquid ===')
print(liq.sort_values('r15',ascending=False).head(25)[['t','px','r5','r15','r60','rsi','ext20atr','stack','dolvol_m','mcap_b','atr14','sma20','sma50','momentum_12_1','momentum_score','missing_history_flag']].to_string(index=False))
print('\n=== BOTTOM r15 liquid ===')
print(liq.sort_values('r15',ascending=True).head(15)[['t','px','r5','r15','r60','rsi','ext20atr','stack','dolvol_m','atr14','short_rule_pass','short_ck_score','short_initial_stop']].to_string(index=False))
print('(SHORT candidates are valid only with short_rule_pass=True: ck_score>=3 and close<SMA200)')
print('\n=== HIGH ext20 ===')
print(liq[liq['ext20atr'].fillna(0)>3].sort_values('ext20atr',ascending=False)[['t','px','ext20atr','rsi','r15','r60','stack','sma20','atr14']].to_string(index=False))
print('\n=== PULLBACK CANDIDATES ===')
pb = liq[(liq['ext50atr'].fillna(99)>-2.5)&(liq['ext50atr'].fillna(-99)<0.8)&(liq['r60'].fillna(-99)>5)&(liq['rsi'].fillna(50)<58)&(liq['mcap_b'].fillna(0)>1.5)]
print(pb.sort_values('r60',ascending=False).head(25)[['t','px','ext50atr','rsi','r15','r60','stack','sma50','atr14','dolvol_m','momentum_12_1','momentum_score','missing_history_flag']].to_string(index=False))

# dump detailed for top candidates
cands = ['MU','AMD','NVDA','AVGO','KLAC','AMAT','MRVL','SNDK','TSLA','META','JPM','BAC','XOM','HD','UNH','LLY','FICO','CRM','ORCL','CAT','GE','AAPL','MSFT','PLTR','CRWD','PANW','COST','WMT','NEE','GS']
with open(f'{OUTDIR}/scan_detail.txt','w') as f:
    for t in cands:
        if t in detailed:
            f.write(f'\n==== {t} ====\n')
            row = out[out['t']==t]
            if len(row):
                f.write(row.to_string(index=False)+'\n')
            f.write('PIVOT HIGHS: '+str(detailed[t]['highs'])+'\n')
            f.write('PIVOT LOWS: '+str(detailed[t]['lows'])+'\n')
            f.write('LAST5:\n'+detailed[t]['ohlcv_tail']+'\n')
            f.write('LAST15:\n'+detailed[t]['last15']+'\n')
print('\nWrote detail for', len([t for t in cands if t in detailed]), 'names ->', OUTDIR)
