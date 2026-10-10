"""SINGLE SOURCE OF TRUTH per run (Ilan 08.10 16:20). run_unified_scan.py computes ONCE per candidate
    <run_dir>/levels/<TICKER>.json   (schema levels-1.0, /workspace/levels_schema.json; producer = scanner_charts.build_levels)
holding: data source + cutoff + bar hash, pivots, Elliott v1 + v2 (version tags), Fib anchors/levels (v1, v2), VP120, S/R
(scanner_levels, on the SAME bars), volume waves / RSI / CCI (scanner_waves), entry / stop / target, earnings-block status,
technical snapshot. Everything downstream READS it and never recomputes: charts (scanner_charts.render_from_levels), the Hebrew
report, tracker rows (tracker_rows.csv) and the LLM prompts (facts_for_prompt()).
Bars: stocks = the scan's Yahoo cache (scanner_stops.daily_bars, scanner-momentum-cache/<cutoff>); crypto = the Alpaca daily
frame saved by scanner_crypto under <run_dir>/bars/crypto (the crypto leg's single source).
reconcile(): report / tracker / chart-index numbers vs the levels JSON, tolerance 1e-6 relative -> 'לא תואם' + excluded.
Earnings gate (Ilan 08.10 16:15, ACTIVE for new stock entries): see earnings_gate()."""
import os, sys, json, glob, hashlib, math
import numpy as np, pandas as pd
sys.path.insert(0, '/workspace')
TOL = 1e-6
SCHEMA_EXTRA = 'levelsfile-1.0'
NYSE_HOLIDAYS = {'2026-01-01', '2026-01-19', '2026-02-16', '2026-04-03', '2026-05-25', '2026-06-19', '2026-07-03', '2026-09-07', '2026-11-26',
                 '2026-12-25', '2027-01-01', '2027-01-18', '2027-02-15', '2027-03-26', '2027-05-31', '2027-06-18', '2027-07-05', '2027-09-06',
                 '2027-11-25', '2027-12-24'}
EARN_BLOCK_TD = int(os.environ.get('EARNINGS_BLOCK_TD', '5'))

def _f(v):
    try:
        v = float(v); return v if math.isfinite(v) else None
    except Exception:
        return None

# ------------------------------------------------------------------ bars (one source per asset)
def bars_for(c, run_dir, cut, px_dir):
    import scanner_stops as ST
    if c.get('asset') == 'crypto':
        import scanner_crypto as SCR
        return SCR.load_bars(run_dir, c['t'])
    return ST.daily_bars(c['t'], 'stock', cut, px_dir)

def bar_hash(x):
    return hashlib.sha256(x[['Open', 'High', 'Low', 'Close', 'Volume']].round(6).to_csv().encode()).hexdigest()[:16]

def path(run_dir, c):
    p = f"{run_dir}/levels/{c['t']}.json"
    if os.path.exists(p):
        try:
            if json.load(open(p)).get('direction') != c['direction']: p = f"{run_dir}/levels/{c['t']}_{c['direction'].lower()}.json"
        except Exception: pass
    return p

# ------------------------------------------------------------------ producer
def build(c, run_dir, cut, px_dir):
    import scanner_charts as SC, scanner_levels as SL, scanner_stops as ST
    x = bars_for(c, run_dir, cut, px_dir)
    if x is None or len(x) < 60: raise ValueError(f"{c['t']}: no / too few bars")
    asset = c.get('asset', 'stock')
    L = SC.build_levels(c['t'], cut, c['direction'], asset=asset, px_dir=px_dir, score=c.get('rank_score'), score_basis=c.get('rank_basis'),
                        entry=c.get('entry'), stop=c.get('stop'), target=c.get('target'), target_note=c.get('target_note'), sr=False, waves=True,
                        run_id=os.path.basename(run_dir.rstrip('/')), bars_df=x)
    try:                                       # S/R on the SAME bars (daily=x) instead of scanner_levels' own long download
        lv = SL.levels_for(c['t'], cut, 'SWING', c['direction'], daily=x)
        L['sr'] = {'version': 'scanner_levels v1 (daily=scan bars)', 'scan_type': 'SWING',
                   'levels': [{k: o.get(k) for k in ('price', 'side', 'tf', 'strength', 'touches', 'flip_dir', 'src', 'confirmed_at')} for o in lv['levels']],
                   'nearest': {k: v for k, v in lv['summary'].items() if k != 'sr_levels_json'}}
    except Exception as e:
        L['sr'] = {'version': 'scanner_levels v1', 'levels': [], 'nearest': {'sr_flag': f'error {e.__class__.__name__}'}}
    xc = x                                   # already point-in-time (scan cache / scanner_crypto)
    cl = xc.Close; A = ST.atr14(xc.High.values, xc.Low.values, cl.values)
    sma = lambda n: _f(cl.rolling(n).mean().iloc[-1]) if len(cl) >= n else None
    L['data'].update(bar_hash=bar_hash(xc), first_bar=str(xc.index[0].date()),
                     source=(L['data']['source'] if asset != 'crypto' else 'alpaca crypto daily v1beta3 (UTC days) via scanner_crypto, <run_dir>/bars/crypto'))
    L['technical'] = {'last_close': _f(cl.iloc[-1]), 'atr14_wilder': _f(A[-1]), 'sma20': sma(20), 'sma50': sma(50), 'sma200': sma(200),
                      'mom_12_1': _f(cl.iloc[-22] / cl.iloc[-253] - 1) if len(cl) >= 253 else None,
                      'ret_15d_pct': _f(100 * (cl.iloc[-1] / cl.iloc[-16] - 1)) if len(cl) > 16 else None,
                      'momentum_score_0_100': _f(c.get('momentum_score')), 'short_rule_pass': c.get('short_rule_pass'),
                      'candles_last': c.get('candle_patterns_last')}
    L['earnings'] = {'status': 'n/a (crypto)'} if asset == 'crypto' else {'status': 'pending'}
    if asset == 'crypto':
        L['trade']['target_rule'] = 'none (crypto: fixed 3xATR14 stop on the daily UTC close, no target)'
    # non-level context the models also get (so EVERY number in a prompt comes from this file)
    keys = ['mcap_b', 'sector_etf', 'news_count_7d', 'news_headlines_top3', 'pe_ttm', 'pe_sector_pctile', 'ps_ttm', 'ev_ebitda', 'fcf_yield',
            'rev_growth_yoy', 'eps_growth_yoy', 'op_margin', 'debt_to_equity', 'fund_flag', 'next_earnings_date_live', 'watch_short_below_va120',
            'vp120_va_pos', 'rate_beta_ticker_60d', 'short_ck_score', 'momentum_score', 'momentum_12_1', 'rank_score', 'rank_basis']
    L['context'] = {k: (None if isinstance(c.get(k), float) and not math.isfinite(c.get(k)) else c.get(k)) for k in keys if k in c}
    L['context']['market_regime'] = c.get('_regime')
    L['levelsfile'] = {'version': SCHEMA_EXTRA, 'producer': 'scanner_levelsfile.build -> scanner_charts.build_levels (+ S/R on the same bars)'}
    return L, x

def _jd(o):
    """JSON default: numpy scalars -> native (np.bool_ must stay boolean for levels_schema.json), else str."""
    import numpy as _np
    if isinstance(o, _np.bool_): return bool(o)
    if isinstance(o, _np.integer): return int(o)
    if isinstance(o, _np.floating): return None if not _np.isfinite(o) else float(o)
    return str(o)

def save(L, run_dir, c):
    p = path(run_dir, c); os.makedirs(os.path.dirname(p), exist_ok=True)
    body = {k: v for k, v in L.items() if k != 'content_hash'}
    L['content_hash'] = hashlib.sha256(json.dumps(body, sort_keys=True, default=_jd).encode()).hexdigest()[:16]
    json.dump(L, open(p, 'w'), ensure_ascii=False, indent=1, default=_jd)
    return p

def load(run_dir, c):
    p = path(run_dir, c)
    return json.load(open(p)) if os.path.exists(p) else None

def apply_trade(c, L):
    """downstream copy of the trade numbers = the levels JSON values (identity)."""
    t = L['trade']; c['entry'], c['stop'], c['target'] = t.get('entry'), t.get('stop'), t.get('target'); c['_levels'] = L
    return c

# ------------------------------------------------------------------ waves: families, not the combined flag (chart worker 08.10)
WAVE_FAMILIES = ('volume_exhaustion', 'effort_result', 'wave_volume_dominance', 'climax', 'momentum_divergence', 'elliott_context')

def wave_fields(wv):
    """wave_end_n / wave_start_n (number of INDEPENDENT families) + one boolean per family. The combined wave_end_signal is not used."""
    # the combined wave_end_signal / wave_start_signal are intentionally NOT carried: the count is wave_end_n / wave_start_n
    o = {'wave_end_n': wv.get('wave_end_n'), 'wave_start_n': wv.get('wave_start_n'),
         'wave_end_families': wv.get('wave_end_families'), 'wave_start_families': wv.get('wave_start_families'),
         'wave_end_reasons': wv.get('wave_end_reasons'), 'wave_start_reasons': wv.get('wave_start_reasons'),
         'rsi14': wv.get('rsi14'), 'cci20': wv.get('cci20'), 'crsi': wv.get('crsi')}
    for side in ('end', 'start'):
        fams = set(str(wv.get(f'wave_{side}_families') or '').split(',')) - {''}
        for f in WAVE_FAMILIES: o[f'wave_{side}_fam_{f}'] = (f in fams) if wv.get(f'wave_{side}_n') is not None else None
    return o

# ------------------------------------------------------------------ prompt numbers (ONLY from the levels JSON)
def facts_for_prompt(L):
    if not L: return {}
    e1 = (L.get('elliott') or {}).get('v1') or {}; e2 = ((L.get('elliott') or {}).get('v2') or {}).get('views', {}).get(L['direction'], {})
    f1 = (L.get('fib') or {}).get('v1') or {}; f2 = (L.get('fib') or {}).get('v2') or {}
    sr = (L.get('sr') or {}).get('nearest') or {}; wv = ((L.get('waves') or {}).get('signals')) or {}
    return {'levels_file': {'schema': L.get('schema_version'), 'cutoff_utc': L['data']['cutoff_utc'], 'last_bar': L['data']['last_bar'],
                            'bar_hash': L['data'].get('bar_hash'), 'source': L['data']['source']},
            'trade': {k: L['trade'].get(k) for k in ('entry', 'stop', 'stop_rule', 'target', 'target_rule', 'target_note')},
            'technical': L.get('technical'),
            'elliott_v1': {k: e1.get(k) for k in ('label', 'valid', 'deviations', 'target_w3', 'target_w5')},
            'elliott_v2': {k: e2.get(k) for k in ('label', 'state', 'kind', 'provisional', 'beyond_target', 'target', 'target_name')},
            'fib_v1': {'origin': (f1.get('origin') or {}).get('price'), 'end': (f1.get('end') or {}).get('price'), 'levels': f1.get('levels'), 'stale': f1.get('stale')},
            'fib_v2': {'origin': (f2.get('origin') or {}).get('price'), 'end': (f2.get('end') or {}).get('price'), 'levels': f2.get('levels'), 'reanchored': f2.get('reanchored')},
            'vp120': {k: (L.get('volume_profile') or {}).get(k) for k in ('poc', 'vah', 'val')},
            'sr_nearest': {k: sr.get(k) for k in ('sr_support', 'sr_support_tf', 'sr_support_strength', 'sr_resistance', 'sr_resistance_tf', 'sr_resistance_strength')},
            'waves': wave_fields(wv),
            'earnings': L.get('earnings')}

# ------------------------------------------------------------------ charts (adapter over scanner_charts.render_from_levels)
def render(run_dir, c, x):
    """Thin adapter: scanner_charts.render_run() only draws stock bars and re-reads platform_enrichment.csv, so the unified scan calls
    render_from_levels() directly with the levels file + the same bars (crypto included). No scanner_charts internals edited."""
    import scanner_charts as SC
    png = f"{run_dir}/charts/{c['t']}_{c['direction'].lower()}.png"
    return SC.render_from_levels(path(run_dir, c), x, png, index_path=f'{run_dir}/charts/chart_index.json')

# ------------------------------------------------------------------ earnings gate (ACTIVE, stocks, new entries)
def sessions_between(d0, d1):
    """NYSE sessions in [d0, d1] (inclusive)."""
    if d1 < d0: return 0
    days = pd.bdate_range(d0, d1)
    return int(sum(str(d.date()) not in NYSE_HOLIDAYS for d in days))

def entry_session(cut):
    """first session an entry from this scan can happen: the scan date (ET) if before the 16:00 ET close and a session, else the next."""
    et = pd.Timestamp(cut).tz_convert('America/New_York'); d = et.normalize().tz_localize(None)
    if et.hour >= 16: d += pd.Timedelta(days=1)
    while d.weekday() >= 5 or str(d.date()) in NYSE_HOLIDAYS: d += pd.Timedelta(days=1)
    return d

def openbb_earnings(t, cut):
    root = '/workspace/openbb-snapshots'; best = None
    for d in sorted(glob.glob(f'{root}/2*/earnings_calendar.csv')):
        day = os.path.basename(os.path.dirname(d))[:10]
        try:
            if pd.Timestamp(day) <= pd.Timestamp(cut).tz_convert('America/New_York').tz_localize(None).normalize(): best = d
        except Exception: continue
    if not best: return None
    try:
        e = pd.read_csv(best); e = e[e.ticker.astype(str).str.upper() == t.upper()]
        return None if e.empty else (str(pd.Timestamp(e.earn_next_date.iloc[0]).date()), f'OpenBB/Nasdaq ({os.path.basename(os.path.dirname(best))})')
    except Exception:
        return None

def earnings_sources(c, cut, pplx=None):
    """[(date, source)] of upcoming report dates. Yahoo calendar (scan_raw next_earnings_date_live), OpenBB/Nasdaq calendar snapshot,
    Perplexity (only if it says the date is confirmed and returned sources). EDGAR/Alpaca have no forward earnings calendar."""
    out = []; d0 = entry_session(cut)
    y = c.get('next_earnings_date_live')
    if isinstance(y, str) and len(y) >= 10: out.append((y[:10], 'Yahoo calendar'))
    o = openbb_earnings(c['t'], cut)
    if o: out.append(o)
    if pplx and pplx.get('next_earnings_date') and pplx.get('earnings_date_confirmed') and pplx.get('_sources'):
        out.append((pplx['next_earnings_date'], 'Perplexity (מאושר, עם מקורות)'))
    return [(d, s) for d, s in out if pd.Timestamp(d) >= d0]

def earnings_gate(c, cut, pplx=None, claude=None, gpt=None):
    """ACTIVE rule (Ilan 08.10 16:15): no new stock entry within EARN_BLOCK_TD (5) trading days before the next report.
    td = NYSE sessions from the entry session (scan date, or next session after the close) through the report date, inclusive
    (report tomorrow -> 1 or 2). Sources disagree -> EARLIER date. No source -> 'תאריך דוח לא מאומת' (not blocked, marked).
    Exception only if Perplexity rates the catalyst 'strong' with a specific dated source URL that the API itself returned AND
    Claude conviction >= 70 supporting the direction AND GPT returned a verdict that is not veto -> 'חריגה: קטליזטור חזק'."""
    if c.get('asset') == 'crypto': return {'status': 'n/a (crypto)', 'blocked': False}
    src = earnings_sources(c, cut, pplx)
    if not src: return {'status': 'תאריך דוח לא מאומת', 'blocked': False, 'sources': []}
    d = min(pd.Timestamp(s[0]) for s in src); td = sessions_between(entry_session(cut), d)
    agree = len({s[0] for s in src}) == 1
    g = {'next_earnings': str(d.date()), 'td_to_earnings': td, 'sources': [f'{a} ({b})' for a, b in src], 'sources_agree': agree,
         'entry_session': str(entry_session(cut).date())}
    if td > EARN_BLOCK_TD: return dict(g, status=f'מותר - דוח בעוד {td} ימי מסחר', blocked=False)
    exc = bool(pplx and pplx.get('catalyst_strength') == 'strong' and pplx.get('catalyst_date') and pplx.get('catalyst_source_url')
               and pplx.get('catalyst_source_verified') and claude and claude.get('conviction', 0) >= 70 and claude.get('direction_view') == 'supports'
               and gpt and gpt.get('verdict') in ('approve', 'flag'))
    if exc:
        return dict(g, status='חריגה: קטליזטור חזק', blocked=False, exception=True,
                    exception_reason=f"Perplexity: קטליזטור חזק ({pplx.get('catalyst_date')}, {pplx.get('catalyst_source_url')}); "
                                     f"Claude {claude.get('conviction')} בעד; GPT {gpt.get('verdict')}")
    return dict(g, status='נחסם - דוח בתוך 5 ימי מסחר', blocked=True)

# ------------------------------------------------------------------ tracker rows (from the levels JSON only)
TRACKER_FIELDS = ['setup_id', 'ticker', 'asset', 'direction', 'alert_date', 'cutoff_utc', 'entry', 'stop', 'target', 'stop_rule', 'target_rule',
                  'elliott_v1', 'elliott_v2', 'fib_v1_1618', 'fib_v2_x1618', 'vp120_poc', 'vp120_vah', 'vp120_val', 'sr_support', 'sr_resistance',
                  'earnings_status', 'bar_hash', 'levels_hash', 'recon_status']

def tracker_row(L, setup_id, alert_date):
    f = facts_for_prompt(L)
    return {'setup_id': setup_id, 'ticker': L['symbol'], 'asset': L['asset'], 'direction': L['direction'], 'alert_date': alert_date,
            'cutoff_utc': L['data']['cutoff_utc'], 'entry': L['trade']['entry'], 'stop': L['trade']['stop'], 'target': L['trade']['target'],
            'stop_rule': L['trade'].get('stop_rule'), 'target_rule': L['trade'].get('target_rule'), 'elliott_v1': f['elliott_v1'].get('label'),
            'elliott_v2': f['elliott_v2'].get('label'), 'fib_v1_1618': (f['fib_v1'].get('levels') or {}).get('1.618'),
            'fib_v2_x1618': (f['fib_v2'].get('levels') or {}).get('1.618'), 'vp120_poc': f['vp120']['poc'], 'vp120_vah': f['vp120']['vah'],
            'vp120_val': f['vp120']['val'], 'sr_support': f['sr_nearest'].get('sr_support'), 'sr_resistance': f['sr_nearest'].get('sr_resistance'),
            'earnings_status': (L.get('earnings') or {}).get('status'), 'bar_hash': L['data'].get('bar_hash'), 'levels_hash': L.get('content_hash')}

# ------------------------------------------------------------------ reconciliation
def _cmp(a, b):
    if a is None and b is None: return True
    if isinstance(a, str) or isinstance(b, str): return str(a) == str(b)
    a, b = _f(a), _f(b)
    if a is None or b is None: return a is None and b is None
    return abs(a - b) <= TOL * max(abs(a), abs(b), 1e-12)

def reconcile(run_dir, cands, report_numbers, tracker_rows, chart_index):
    """-> {setup_key: [mismatch strings]}; empty list = תואם. report_numbers: {key: {entry, stop, target}} as printed by the report."""
    ci = {(e.get('symbol'), e.get('direction')): e for e in (chart_index or [])}
    tr = {(r['ticker'], r['direction']): r for r in (tracker_rows or [])}
    out = {}
    for c in cands:
        k = (c['t'], c['direction']); L = load(run_dir, c); bad = []
        if L is None: out[k] = ['levels JSON חסר']; continue
        T = L['trade']; f = facts_for_prompt(L)
        ref = {'entry': T.get('entry'), 'stop': T.get('stop'), 'target': T.get('target')}
        for src, d in (('report', report_numbers.get(k)), ('tracker', tr.get(k))):
            if d is None: bad.append(f'{src}: שורה חסרה'); continue
            for n, v in ref.items():
                if not _cmp(d.get(n), v): bad.append(f'{src}.{n}={d.get(n)} ≠ levels {v}')
        tk = tr.get(k) or {}
        for n, v in (('vp120_poc', f['vp120']['poc']), ('elliott_v1', f['elliott_v1'].get('label')), ('elliott_v2', f['elliott_v2'].get('label'))):
            if tk and not _cmp(tk.get(n), v): bad.append(f'tracker.{n}={tk.get(n)} ≠ levels {v}')
        e = ci.get(k)
        if e is None: bad.append('chart: אין רשומה ב-chart_index')
        else:
            dr = e.get('drawn') or {}
            for n, v in ref.items():
                if dr.get(n) is not None or v is not None:
                    if not _cmp(dr.get(n), v): bad.append(f'chart.{n}={dr.get(n)} ≠ levels {v}')
            for n in ('poc', 'vah', 'val'):
                dv = (dr.get('vp120') or {}).get(n)
                if dv is not None and not _cmp(dv, f['vp120'][n]): bad.append(f'chart.vp120.{n}={dv} ≠ levels {f["vp120"][n]}')
            if e.get('last_bar') != L['data']['last_bar']: bad.append(f"chart.last_bar={e.get('last_bar')} ≠ levels {L['data']['last_bar']}")
        out[k] = bad
    return out
