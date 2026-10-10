"""openbb_snapshot.py - daily point-in-time snapshot of free data for Ilan's scanner universe (US stocks >= $1.5B).
EXPERIMENTAL, score weight 0 (out-of-sample-rule-2026-10-08.txt). Consensus, option chains and IBKR borrow data have NO free
history, so those columns are forward-only from the first snapshot.

ONE idempotent command (daily routine ~08:00 Israel, Tue-Sat, after the prior US session):
  /workspace/venv-openbb/bin/python /workspace/openbb_snapshot.py
  -> folder /workspace/openbb-snapshots/<last completed US session date>/ ; if that folder already has a complete meta.json the
     run exits 0 immediately ("already done"). --force re-runs. Other options: --tickers A,B --extra C --budget 540 --workers 6
     --date YYYY-MM-DD (folder override, testing).
Files: summary.csv (one row per ticker; columns obb_* = OpenBB, short_* = FINRA/IBKR/squeeze), earnings_calendar.csv,
  eps_surprises.csv, consensus.csv, short_interest.csv (FINRA, settlement + est. publication + first-seen), darkpool.csv,
  options_summary.csv (CBOE chains compressed to metrics; no raw chains), ib_usa.txt.gz (IBKR raw, when reachable), meta.json.
PIT keys: known-at = snapshot_utc. Short interest keyed to PUBLICATION (settlement + 7 business days, and first-seen snapshot),
  never settlement. Reg SHO short volume: trade dates <= session date, change-only z-scores. Dark pool: FINRA
  initial_published_date. EPS surprises have no announcement timestamp (known-at = snapshot only).
No secrets: only free no-key sources (CBOE, Nasdaq, FINRA, IBKR public FTP).
"""
import os, sys, json, time, argparse, threading, ast, re, glob, gzip, io, datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np, pandas as pd
sys.path.insert(0, '/workspace')
import scanner_short as SH

ROOT = '/workspace/openbb-snapshots'
MCAP_FLOOR_B = 1.5
ET = 'America/New_York'
CALL_TIMEOUT = 45

def last_session(now_utc):
    """Last COMPLETED US session date (ET): today if an NYSE day and >= 16:15 ET, else the previous NYSE day."""
    e = now_utc.tz_convert(ET); d = pd.Timestamp(e.date())
    if SH.is_nyse_day(d) and (e.hour, e.minute) >= (16, 15): return str(d.date())
    return str((d - SH.nyse_bday()).date())

def scanner_universe():
    src = open('/workspace/swing_scan.py').read()
    T = ast.literal_eval(re.search(r"tickers = (\[.*?\])\n", src, re.S).group(1))
    etf = ast.literal_eval(re.search(r"ETF_LIKE = (\{.*?\})\n", src, re.S).group(1))
    T += [x.strip().upper() for x in os.environ.get('SCAN_EXTRA_TICKERS', '').split(',') if x.strip()]
    out = []
    for t in T:
        if t.startswith('^') or t in etf or t in out: continue
        out.append(t)
    return out

def mcap_lookup(tickers):
    m = {}
    for f in sorted(glob.glob('/workspace/scan-runs/*/scan_raw.csv'), reverse=True)[:5]:
        try:
            d = pd.read_csv(f, usecols=['t', 'mcap_b'])
            for t, v in zip(d['t'], d['mcap_b']):
                if t not in m and pd.notna(v): m[t] = float(v)
        except Exception: pass
    return {t: m.get(t) for t in tickers}

class Gate:
    def __init__(self, conc, min_interval):
        self.sem = threading.Semaphore(conc); self.lock = threading.Lock(); self.last = 0.0; self.mi = min_interval
    def __enter__(self):
        self.sem.acquire()
        with self.lock:
            w = self.mi - (time.time() - self.last)
            if w > 0: time.sleep(w)
            self.last = time.time()
    def __exit__(self, *a): self.sem.release()
GATES = {'nasdaq': Gate(2, 0.4), 'cboe': Gate(3, 0.2), 'finra': Gate(2, 0.3)}
_CALLX = ThreadPoolExecutor(12)
_CBOEX = ThreadPoolExecutor(1)   # cboe provider keeps an asyncio.Lock bound to one event loop -> all cboe calls on ONE thread

def options_summary(ch):
    o = {}
    if ch is None or len(ch) == 0: return o
    ch = ch.reset_index() if 'expiration' not in ch.columns else ch.copy()
    px = float(pd.to_numeric(ch['underlying_price'], errors='coerce').dropna().iloc[0]) if 'underlying_price' in ch else np.nan
    for c in ('strike', 'open_interest', 'volume', 'implied_volatility', 'delta', 'dte'):
        if c in ch: ch[c] = pd.to_numeric(ch[c], errors='coerce')
    if 'dte' not in ch: ch['dte'] = (pd.to_datetime(ch['expiration']) - pd.Timestamp.now().normalize()).dt.days
    calls, puts = ch[ch['option_type'] == 'call'], ch[ch['option_type'] == 'put']
    o['opt_underlying_px'] = round(px, 4) if np.isfinite(px) else None
    o['opt_n_contracts'] = int(len(ch)); o['opt_n_expiries'] = int(ch['expiration'].nunique())
    cv, pv = calls['volume'].sum(), puts['volume'].sum(); coi, poi = calls['open_interest'].sum(), puts['open_interest'].sum()
    o['opt_call_volume'], o['opt_put_volume'], o['opt_call_oi'], o['opt_put_oi'] = int(cv), int(pv), int(coi), int(poi)
    o['opt_pcr_volume'] = round(pv / cv, 4) if cv > 0 else None
    o['opt_pcr_oi'] = round(poi / coi, 4) if coi > 0 else None
    if np.isfinite(px):
        ntm = ch[(ch['strike'].between(0.95 * px, 1.05 * px)) & (ch['dte'] <= 60)]
        nc, np_ = ntm[ntm['option_type'] == 'call']['open_interest'].sum(), ntm[ntm['option_type'] == 'put']['open_interest'].sum()
        o['opt_ntm_oi_call'], o['opt_ntm_oi_put'] = int(nc), int(np_)
        o['opt_ntm_pcr_oi'] = round(np_ / nc, 4) if nc > 0 else None
        iv = ch[(ch['implied_volatility'] > 0) & (ch['dte'] >= 7)]
        atm = []
        for (e, d), g in iv.groupby(['expiration', 'dte']):
            k = g.iloc[(g['strike'] - px).abs().argsort()[:1]]['strike'].iloc[0]
            v = g[g['strike'] == k]['implied_volatility'].mean()
            if np.isfinite(v): atm.append((int(d), float(v), str(e)[:10]))
        atm.sort()
        if atm:
            lo = [a for a in atm if a[0] <= 30]; hi = [a for a in atm if a[0] >= 30]
            if lo and hi and hi[0][0] != lo[-1][0]:
                a, b = lo[-1], hi[0]; w = (30 - a[0]) / (b[0] - a[0]); o['opt_atm_iv_30d'] = round(a[1] + w * (b[1] - a[1]), 4)
            else:
                n = min(atm, key=lambda a: abs(a[0] - 30)); o['opt_atm_iv_30d'] = round(n[1], 4)
            o['opt_atm_iv_front'] = round(atm[0][1], 4); o['opt_front_expiry'] = atm[0][2]
            e30 = min(atm, key=lambda a: abs(a[0] - 30))[2]
            g = iv[iv['expiration'].astype(str).str[:10] == e30]
            if 'delta' in g and g['delta'].notna().any():
                p = g[(g['option_type'] == 'put') & g['delta'].notna()]; c = g[(g['option_type'] == 'call') & g['delta'].notna()]
                if len(p) and len(c):
                    pv25 = p.iloc[(p['delta'] + 0.25).abs().argsort()[:1]]['implied_volatility'].iloc[0]
                    cv25 = c.iloc[(c['delta'] - 0.25).abs().argsort()[:1]]['implied_volatility'].iloc[0]
                    o['opt_skew_25d'] = round(float(pv25 - cv25), 4); o['opt_skew_expiry'] = e30
    return o

def per_ticker(obb, t, deadline, snap_date, raw):
    row = {'ticker': t}; err = {}
    def call(name, gate, f):
        if time.time() > deadline: err[name] = 'skipped (time budget)'; return None
        try:
            with GATES[gate]: df = (_CBOEX if gate == 'cboe' else _CALLX).submit(f).result(timeout=CALL_TIMEOUT)
            return df.reset_index() if df is not None and 'symbol' not in getattr(df, 'columns', []) and getattr(df.index, 'name', None) else df
        except Exception as e:
            m = str(e).strip().splitlines()[-1] if str(e).strip() else ''
            err[name] = (type(e).__name__ + (': ' + m if m else ''))[:160]; return None
    ch = call('options', 'cboe', lambda: obb.cboe.options.chains(t))
    if ch is not None: row.update(options_summary(ch))
    c = call('consensus', 'nasdaq', lambda: obb.nasdaq.equity.estimates.consensus(t))
    if c is not None and len(c):
        r = c.iloc[0].to_dict(); raw['consensus'].append(dict(r, ticker=t))
        for k in ('target_consensus', 'target_high', 'target_low', 'buy_ratings', 'hold_ratings', 'sell_ratings', 'consensus_rating'):
            row['cons_' + k] = r.get(k)
        px = row.get('opt_underlying_px')
        if px and r.get('target_consensus'): row['cons_target_upside'] = round(float(r['target_consensus']) / px - 1, 4)
    e = call('eps_surprise', 'nasdaq', lambda: obb.nasdaq.equity.fundamental.historical_eps(t))
    if e is not None and len(e):
        e = e.copy(); e['ticker'] = t; raw['eps'].append(e)
        e2 = e.dropna(subset=['eps_actual']).sort_values('fiscal_period_ending') if 'fiscal_period_ending' in e else e
        if len(e2):
            l = e2.iloc[-1]
            row.update(eps_last_period_end=str(l.get('fiscal_period_ending'))[:10], eps_last_actual=l.get('eps_actual'),
                       eps_last_estimate=l.get('eps_estimated'), eps_last_surprise_pct=l.get('surprise_percent'),
                       eps_surprise_mean_4q=round(float(pd.to_numeric(e2['surprise_percent'], errors='coerce').tail(4).mean()), 3)
                       if 'surprise_percent' in e2 else None)
    d = call('darkpool', 'finra', lambda: obb.finra.equity.darkpool.otc(t))
    if d is not None and len(d):
        d = d.copy(); d['initial_published_date'] = pd.to_datetime(d['initial_published_date'], errors='coerce')
        d = d[d['initial_published_date'] <= pd.Timestamp(snap_date) + pd.Timedelta(days=1)]
        w = d.groupby('week_start_date').agg(share_quantity=('share_quantity', 'sum'), trade_quantity=('trade_quantity', 'sum'),
                                              total_notional=('total_notional', 'sum'), initial_published_date=('initial_published_date', 'max')).sort_index()
        if len(w):
            raw['dp'].append(w.tail(12).reset_index().assign(ticker=t))
            l = w.iloc[-1]; prev = w['share_quantity'].iloc[-5:-1]
            row.update(dp_week_start=str(pd.Timestamp(w.index[-1]).date()), dp_published=str(l['initial_published_date'].date()),
                       dp_shares=int(l['share_quantity']), dp_trades=int(l['trade_quantity']),
                       dp_notional=float(l['total_notional']) if pd.notna(l['total_notional']) else None,
                       dp_shares_vs_4w=round(float(l['share_quantity'] / prev.mean()), 4) if len(prev) and prev.mean() > 0 else None)
    row['errors'] = '; '.join(f'{k}: {v}' for k, v in err.items()) or None
    return row

def fetch_ibkr(out):
    """IBKR public short-stock availability (forward-only). Returns (DataFrame or None, status)."""
    import ftplib
    try:
        f = ftplib.FTP('ftp3.interactivebrokers.com', timeout=20); f.login('shortstock', '')
        buf = io.BytesIO(); f.retrbinary('RETR usa.txt', buf.write); f.quit()
    except Exception as e:
        return None, f'unreachable from this machine ({type(e).__name__}: {str(e)[:80]}) - FTP port 21'
    raw = buf.getvalue(); gzip.open(f'{out}/ib_usa.txt.gz', 'wb').write(raw)
    lines = raw.decode('latin-1').splitlines()
    hdr = next((l for l in lines if l.startswith('#SYM')), None)
    if not hdr: return None, 'downloaded but no #SYM header'
    cols = [c.strip('#').strip().lower() for c in hdr.split('|')]
    rows = [l.split('|') for l in lines if l and not l.startswith('#')]
    df = pd.DataFrame([r[:len(cols)] for r in rows], columns=cols)
    df['available'] = pd.to_numeric(df.get('available', pd.Series(dtype=str)).astype(str).str.replace('>', '', regex=False), errors='coerce')
    for c in ('feerate', 'rebaterate'):
        if c in df: df[c] = pd.to_numeric(df[c], errors='coerce')
    return df, f'ok ({len(df)} rows, header {hdr[:60]})'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tickers'); ap.add_argument('--extra'); ap.add_argument('--date'); ap.add_argument('--force', action='store_true')
    ap.add_argument('--budget', type=float, default=540); ap.add_argument('--workers', type=int, default=6)
    a = ap.parse_args()
    t0 = time.time(); now = pd.Timestamp.now(tz='UTC')
    snap_date = a.date or last_session(now)
    out = f'{ROOT}/{snap_date}'
    mp = f'{out}/meta.json'
    if os.path.exists(mp) and not a.force:
        try:
            if json.load(open(mp)).get('complete'): print(f'already done: {out}'); os._exit(0)
        except Exception: pass
    os.makedirs(out, exist_ok=True)
    T = [x.strip().upper() for x in a.tickers.split(',')] if a.tickers else scanner_universe()
    if a.extra: T += [x.strip().upper() for x in a.extra.split(',') if x.strip() and x.strip().upper() not in T]
    mc = mcap_lookup(T)
    excluded = [t for t in T if mc.get(t) is not None and mc[t] < MCAP_FLOOR_B]
    T = [t for t in T if t not in excluded]
    deadline = t0 + a.budget
    notes = {}
    # ---- FINRA short interest (direct Query API) keyed to publication date + first-seen
    alert_next = str((pd.Timestamp(snap_date) + pd.Timedelta(days=1)).date())   # this snapshot serves alerts after the session
    try:
        si = SH.fetch_si(T, start=str((pd.Timestamp(snap_date) - pd.Timedelta(days=200)).date()), cache=f'{out}/_finra_si_cache.csv', max_age_h=0)
        first = {}
        for f in sorted(glob.glob(f'{ROOT}/*/short_interest.csv')):
            if f.startswith(out + '/'): continue
            try:
                s_ = pd.read_csv(f, usecols=['symbol', 'settlement_date', 'si_first_seen'])
                for x in s_.itertuples(): first.setdefault((x.symbol, str(x.settlement_date)[:10]), str(x.si_first_seen)[:10])
            except Exception: pass
        si['si_first_seen'] = [first.get((s, str(d)[:10]), snap_date) for s, d in zip(si['symbol'], si['settlement_date'])]
        si.to_csv(f'{out}/short_interest.csv', index=False)
        os.remove(f'{out}/_finra_si_cache.csv')
    except Exception as e:
        si = None; notes['finra_si'] = f'{type(e).__name__}: {e}'[:200]
    # ---- Reg SHO daily short volume (sessions <= snapshot session)
    try:
        sess = list(pd.date_range(end=snap_date, periods=95, freq=SH.nyse_bday()))
        sess = [d for d in sess if SH.regsho_day(d) is not None and d <= pd.Timestamp(snap_date)]
    except Exception as e:
        sess = []; notes['regsho'] = f'{type(e).__name__}: {e}'[:200]
    # ---- bars + float (Yahoo) for the squeeze price components
    bars = {}
    try:
        import yfinance as yf
        X = yf.download(T, start=str((pd.Timestamp(snap_date) - pd.Timedelta(days=130)).date()),
                        end=str((pd.Timestamp(snap_date) + pd.Timedelta(days=1)).date()), group_by='ticker', auto_adjust=True, progress=False, threads=True)
        for t in T:
            try:
                b = X[t].dropna(subset=['Close']) if isinstance(X.columns, pd.MultiIndex) else X.dropna(subset=['Close'])
                bars[t] = b.rename(columns=str.title).loc[:pd.Timestamp(snap_date)]
            except Exception: pass
        FLOAT = SH.float_shares(T)
    except Exception as e:
        FLOAT = {}; notes['yahoo'] = f'{type(e).__name__}: {e}'[:200]
    # ---- IBKR borrow availability (forward-only) + change vs the previous snapshot
    ib, ib_status = fetch_ibkr(out)
    prev_ib = None
    for f in sorted(glob.glob(f'{ROOT}/*/summary.csv'), reverse=True):
        if f.startswith(out + '/') or os.path.basename(os.path.dirname(f)) >= snap_date: continue
        try:
            p_ = pd.read_csv(f)
            if 'short_ib_fee' in p_ and p_['short_ib_fee'].notna().any(): prev_ib = p_.set_index('ticker'); break
        except Exception: pass
    # ---- OpenBB (CBOE / Nasdaq / FINRA dark pool)
    from openbb import obb
    obb.user.preferences.output_type = 'dataframe'
    t_import = time.time() - t0
    raw = {'consensus': [], 'eps': [], 'dp': []}
    cal_err = None; cal = None
    try:
        with GATES['nasdaq']:
            cal = _CALLX.submit(lambda: obb.nasdaq.equity.calendar.earnings(start_date=alert_next,
                                end_date=str((pd.Timestamp(snap_date) + pd.Timedelta(days=29)).date()))).result(timeout=120)
        cal = cal.reset_index() if 'symbol' not in cal.columns else cal
        cal = cal[cal['symbol'].isin(T)].copy()
    except Exception as e:
        cal_err = (type(e).__name__ + ': ' + str(e))[:200]
    rows = []
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(per_ticker, obb, t, deadline, snap_date, raw): t for t in T}
        for f in as_completed(futs):
            try: rows.append(f.result())
            except Exception as e: rows.append({'ticker': futs[f], 'errors': f'fatal: {type(e).__name__}: {e}'[:200]})
    S = pd.DataFrame(rows)
    if cal is not None and len(cal):
        c = cal.sort_values('report_date').drop_duplicates('symbol')
        c = c.rename(columns={'symbol': 'ticker', 'report_date': 'earn_next_date', 'reporting_time': 'earn_time', 'eps_consensus': 'earn_eps_consensus',
                              'num_estimates': 'earn_num_estimates', 'eps_previous': 'earn_eps_prev_year_q', 'previous_report_date': 'earn_prev_report_date'})
        keep = [k for k in ['ticker', 'earn_next_date', 'earn_time', 'earn_eps_consensus', 'earn_num_estimates', 'earn_eps_prev_year_q', 'earn_prev_report_date'] if k in c]
        S = S.merge(c[keep], on='ticker', how='left'); cal.to_csv(f'{out}/earnings_calendar.csv', index=False)
    S = S.rename(columns={c: 'obb_' + c for c in S.columns if c != 'ticker'})
    # ---- short_* columns
    sh_rows = []
    for t in S['ticker']:
        borrow = None; ibr = {}
        if ib is not None and 'sym' in ib:
            m = ib[ib['sym'] == t.replace('-', ' ').replace('.', ' ')]
            if len(m):
                r = m.iloc[0]; ibr = dict(short_ib_fee=r.get('feerate'), short_ib_rebate=r.get('rebaterate'), short_ib_available=r.get('available'))
                if prev_ib is not None and t in prev_ib.index:
                    pf, pa = prev_ib.loc[t].get('short_ib_fee'), prev_ib.loc[t].get('short_ib_available')
                    if pd.notna(pf) and pd.notna(ibr['short_ib_fee']): ibr['short_ib_fee_chg'] = round(float(ibr['short_ib_fee']) - float(pf), 4)
                    if pd.notna(pa) and pa > 0 and pd.notna(ibr['short_ib_available']): ibr['short_ib_avail_drop_pct'] = round(100 * (1 - float(ibr['short_ib_available']) / float(pa)), 2)
                    borrow = {'short_comp_borrow': bool((ibr.get('short_ib_fee_chg') or 0) >= 1.0 or (ibr.get('short_ib_avail_drop_pct') or 0) >= 30)}
        o = SH.short_columns(t, alert_next, bars.get(t), si, sess, float_sh=FLOAT.get(t), borrow=borrow) if si is not None else {}
        o.update(ibr); o['short_ib_status'] = ib_status; o['ticker'] = t
        sh_rows.append(o)
    S = S.merge(pd.DataFrame(sh_rows), on='ticker', how='left')
    S.insert(1, 'snapshot_date', snap_date); S.insert(2, 'snapshot_utc', now.strftime('%Y-%m-%dT%H:%MZ'))
    S['mcap_b_ref'] = S['ticker'].map(mc)
    S = S.sort_values('ticker'); S.to_csv(f'{out}/summary.csv', index=False)
    if raw['consensus']: pd.DataFrame(raw['consensus']).to_csv(f'{out}/consensus.csv', index=False)
    for k, fn in (('eps', 'eps_surprises.csv'), ('dp', 'darkpool.csv')):
        if raw[k]: pd.concat(raw[k], ignore_index=True).to_csv(f'{out}/{fn}', index=False)
    oc = [c for c in S.columns if c.startswith('obb_opt_')]
    if oc: S[['ticker', 'snapshot_utc'] + oc].to_csv(f'{out}/options_summary.csv', index=False)
    fields = ['obb_earn_next_date', 'obb_eps_last_surprise_pct', 'obb_cons_target_consensus', 'obb_cons_consensus_rating', 'obb_dp_shares',
              'obb_opt_pcr_volume', 'obb_opt_pcr_oi', 'obb_opt_atm_iv_30d', 'obb_opt_skew_25d', 'obb_opt_ntm_oi_call',
              'short_si_shares', 'short_si_pct_float', 'short_si_dtc20', 'short_si_chg_pct', 'short_svr_z20', 'short_svr_z60',
              'short_comp_trend', 'short_comp_breakout', 'short_squeeze_candidate', 'short_ib_fee', 'short_ib_available', 'short_comp_borrow']
    cov = {k: f"{int(S[k].notna().sum()) if k in S else 0}/{len(S)}" for k in fields}
    meta = dict(complete=True, snapshot_date=snap_date, snapshot_utc=now.strftime('%Y-%m-%dT%H:%M:%SZ'), run_seconds=round(time.time() - t0, 1),
                openbb_ready_seconds=round(t_import, 1), universe=len(T), excluded_mcap_below_1_5b=excluded,
                mcap_unknown=[t for t in T if mc.get(t) is None], coverage=cov, calendar_error=cal_err, ibkr_status=ib_status,
                regsho_sessions=len(sess), notes=notes, squeeze_count=int((S.get('short_squeeze_candidate') == True).sum()),
                providers='free/no-key only: cboe (options), nasdaq (calendar, eps, consensus), finra (short interest, Reg SHO, dark pool), IBKR public FTP',
                weight=0, rule='memory/stock-scanner/out-of-sample-rule-2026-10-08.txt',
                errors_sample=S['obb_errors'].dropna().head(15).tolist() if 'obb_errors' in S else [])
    _et = pd.Timestamp(now).tz_convert('America/New_York') if pd.Timestamp(now).tzinfo else pd.Timestamp(now).tz_localize('UTC').tz_convert('America/New_York')
    meta['options_intraday_warning'] = bool(SH.is_nyse_day(pd.Timestamp(_et.date())) and (9, 30) <= (_et.hour, _et.minute) < (16, 15))
    if meta['options_intraday_warning']:
        meta['notes'] = dict(meta['notes'] or {}, options_timing='run during the US session: CBOE volume / IV / skew are for the CURRENT session (often 0 / empty right after the open), not the snapshot_date close - schedule at ~08:00 Israel')
    json.dump(meta, open(mp, 'w'), indent=1, default=str)
    print(json.dumps({k: meta[k] for k in ('snapshot_date', 'run_seconds', 'openbb_ready_seconds', 'universe', 'coverage', 'calendar_error', 'ibkr_status', 'squeeze_count')}, indent=1, default=str))
    print('->', out, flush=True)
    os._exit(0)   # do not wait for timed-out provider threads

if __name__ == '__main__':
    main()
