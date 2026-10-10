#!/usr/bin/env python3
"""Unified scan (08.10.2026). Weekly full run (Monday 09:00 Israel, all models, 20 candidates) and a daily no-LLM paper mode.

Pipeline (one run folder = one SINGLE SOURCE OF TRUTH, <run_dir>/levels/<T>.json):
 1. swing_scan.py UNCHANGED (subprocess) -> scan_raw.csv (stocks)  [+ scanner_crypto: Alpaca daily bars, LONG only]
 2. full rule pass: every name that passes the rules (stock LONG trend filter, stock SHORT approved short rule, crypto LONG trend filter)
 3. levels JSON per passing name (scanner_levelsfile.build -> scanner_charts.build_levels on the scan's own bars; S/R on the same bars)
 4. earnings gate (ACTIVE, stocks): pre-gate from Yahoo + OpenBB/Nasdaq; post-gate adds Perplexity (earlier date wins) + exception
 5. candidates_full.csv = ALL passing names (rule scores, levels, entry/stop/target, earnings flag)
 6. selection: top N (--candidates, default 20) with the sector cap (--sector-cap, default 2, 0 = off), blocked names replaced by
    the next eligible name (blocked names ranked above the cut are still researched, for the exception check and the ledger)
 7. charts from the levels JSON (scanner_charts.render_from_levels via scanner_levelsfile.render)
 8. platforms (skipped with --no-models): Jev -> Grok (free X cache first; chart image) -> Perplexity (chart image) -> Claude analyst
    (chart image) -> GPT devil's advocate (chart image). Numbers in prompts come only from the levels JSON. Weight 0.
 9. tracker_rows.csv (from the levels JSON), reconciliation (report / tracker / chart index vs levels, 1e-6 rel) -> 'לא תואם' excluded
10. research_columns.csv (research_columns.py, INTEGRATION.md; SHORT view only for short-rule names), tool_stats.py, Hebrew report.
Paper mode (--paper --no-models): steps 1-5 + research columns, folder scan-runs/YYYY-MM-DD_paper, every passing name appended to
scan-runs/paper_trades_ledger.csv (entry = next session open, same stop/target rules). Paper trades are NOT positions: never in the
tracker positions or the reports (the daily report shows a one-line count only).

Usage:
  python3 run_unified_scan.py                              # weekly full run (folder suffix '' = real run, forward ledger)
  python3 run_unified_scan.py --trial                      # same, folder suffix _trial, trial ledger
  python3 run_unified_scan.py --paper --no-models          # daily paper run (08:24 weekday routine), zero LLM calls
  python3 run_unified_scan.py --run-dir DIR [--no-models]  # reuse an existing scan folder
Flags: --candidates 20  --min-score 60 (unified-score floor)  --sector-cap 2 per side (0=off)  --no-crypto  --budget USD  --tracker XLSX
Secrets come only from env; never printed or written.
"""
import os, sys, subprocess, argparse, time, json, glob, math
import pandas as pd, numpy as np
sys.path.insert(0, '/workspace')
PAPER_LEDGER = '/workspace/scan-runs/paper_trades_ledger.csv'

def log(*a): print('[unified]', *a, flush=True)

def run_scan(suffix, paper=False):
    asof = pd.Timestamp.now(tz='Asia/Jerusalem').floor('min')
    env = dict(os.environ, SCAN_ASOF=asof.strftime('%Y-%m-%dT%H:%M%z'))
    base = f"/workspace/scan-runs/{asof.strftime('%Y-%m-%d_%H%M')}"
    log(f'running swing_scan.py, as-of {asof:%Y-%m-%d %H:%M} (Asia/Jerusalem) -> {base}')
    t0 = time.time(); tmp_log = f'/tmp/swing_scan_{asof:%Y%m%d_%H%M}.log'
    with open(tmp_log, 'w') as fh:
        rc = subprocess.call([sys.executable, '/workspace/swing_scan.py'], stdout=fh, stderr=subprocess.STDOUT, env=env, cwd='/workspace')
    log(f'swing_scan.py exit {rc} in {time.time()-t0:.0f}s')
    if rc != 0 or not os.path.exists(f'{base}/scan_raw.csv'):
        print(open(tmp_log).read()[-3000:]); raise SystemExit('swing_scan.py failed - no report written')
    dst = f"/workspace/scan-runs/{asof:%Y-%m-%d}_paper" if paper else base + suffix
    i = 2; d0 = dst
    while os.path.exists(dst): dst = f'{d0}{i}'; i += 1
    os.rename(base, dst); os.replace(tmp_log, f'{dst}/scan_stdout.log')
    json.dump({'scan_asof_local': str(asof), 'swing_scan_exit': rc, 'scan_seconds': round(time.time()-t0), 'trial': suffix == '_trial',
               'paper': paper}, open(f'{dst}/run_meta.json', 'w'), indent=1)
    return dst

def cutoff_of(run_dir):
    s = pd.read_csv(f'{run_dir}/scan_raw.csv', usecols=['t', 'asof_utc']).dropna()
    return pd.Timestamp(s['asof_utc'].mode().iloc[0]).tz_localize('UTC')

def _num(v):
    try:
        v = float(v); return v if math.isfinite(v) else None
    except Exception: return None

# ------------------------------------------------------------------ unified score (longs and shorts on ONE scale)
# Directional momentum score: the 12-1 momentum percentile within the asset class, 0-100 (scanner_momentum.rank, LONG view),
# flipped for shorts (100 - long percentile = scanner_momentum.momentum_score_short). High = the momentum points the trade's way.
# Both sides use the same number, so a short only ranks above a long when its downside momentum is stronger than that long's
# upside momentum. Crypto uses the same percentile, computed over the crypto scan itself (too few names for the stock percentile).
# Default floor 60: on the validated sample (139 stock setups with a day-20 outcome, 15 distinct entry days, direction-adjusted return)
# names at >=60 beat the rest on hit rate (58.9% vs 51.8%) with the same mean; the gap is carried by the LONG side. Small sample -
# the floor is a flag (--min-score) and is itself measured forward. See the addendum.
MIN_SCORE_DEFAULT = 60.0

def unified_score(c):
    if c.get('asset') == 'crypto':
        v = c.get('momentum_score')
        if v is None: v = c.get('momentum_12_1')   # raw fallback only if the percentile was not computed
        basis = 'momentum_score (12-1 percentile, crypto LONG)' if c.get('momentum_score') is not None else 'momentum_12_1 (crypto LONG, raw fallback)'
    elif c['direction'] == 'SHORT':
        v, basis = c.get('momentum_score_short'), 'momentum_score_short (100 - momentum percentile, SHORT)'
    else:
        v, basis = c.get('momentum_score'), 'momentum_score (12-1 percentile, LONG)'
    try:
        v = float(v); v = v if math.isfinite(v) else None
    except Exception: v = None
    return (round(v, 1) if v is not None else None), basis

# ------------------------------------------------------------------ one ranking, no fixed long/short split
def select(ok, n, cap, min_score):
    """ok: rule-passing cands with levels. ONE list ranked by unified_score (longs, shorts, crypto together), floor min_score,
    sector cap per side ((asset, direction, sector)), earnings-blocked names skipped and back-filled. Sets c['_sel_note'].
    -> (selected, blocked_researched)."""
    blocked = {(c['t'], c['direction']) for c in ok if (c.get('_eg') or {}).get('blocked')}
    ranked = sorted(ok, key=lambda c: (c.get('unified_score') is None, -(c.get('unified_score') or 0), c['t']))
    sel, blk, cnt = [], [], {}
    for c in ranked:
        sc = c.get('unified_score'); side = (c['asset'], c['direction'])
        sec = c.get('sector_etf') if isinstance(c.get('sector_etf'), str) else f"_{c['t']}"
        if sc is None or sc < min_score: c['_sel_note'] = f'מתחת לסף {min_score:g}'; continue
        if (c['t'], c['direction']) in blocked:
            c['_sel_note'] = 'נחסם - דוח בתוך 5 ימי מסחר'
            if len(blk) < max(2, n // 2): blk.append(c)
            continue
        if cap > 0 and cnt.get((side, sec), 0) >= cap: c['_sel_note'] = f'תקרת סקטור ({cap} לצד)'; continue
        if len(sel) >= n: c['_sel_note'] = f'מחוץ ל-{n} הראשונים'; continue
        sel.append(c); cnt[(side, sec)] = cnt.get((side, sec), 0) + 1; c['_sel_note'] = 'נבחר'
    return sel, blk

# ------------------------------------------------------------------ selection with sector cap + earnings backfill (legacy helper)
def pick(ranked, n, cap, blocked_keys):
    """ranked: list of cands (best first). -> (selected, blocked_researched). Sector cap counts selected names only."""
    sel, blk, cnt = [], [], {}
    if n <= 0: return sel, blk
    for c in ranked:
        s = c.get('sector_etf') if isinstance(c.get('sector_etf'), str) else f"_{c['t']}"
        if cap > 0 and cnt.get(s, 0) >= cap: continue
        if (c['t'], c['direction']) in blocked_keys:
            if len(blk) < max(2, n // 2): blk.append(c)
            continue
        sel.append(c); cnt[s] = cnt.get(s, 0) + 1
        if len(sel) >= n: break
    return sel, blk

def research_columns(run_dir, cut, px_dir, budget_s=300):
    """research_columns.py per /workspace/research_nightly/INTEGRATION.md -> <run_dir>/research_columns.csv keyed by setup_id + direction."""
    try:
        import research_columns as RC, scanner_stops as ST
    except Exception as e:
        log('research_columns skipped (module missing):', e); return None
    try:
        RC.reset_budget(budget_s)
        d = pd.read_csv(f'{run_dir}/scan_raw.csv'); items = []
        srp = d['short_rule_pass'].astype(str).str.lower().eq('true') if 'short_rule_pass' in d else pd.Series(False, index=d.index)
        for t, ok, sp in zip(d['t'], d['mcap_ok'].astype(str).str.lower().eq('true'), srp):
            if str(t).startswith('^') or not ok: continue
            b = ST.daily_bars(t, 'stock', cut, px_dir)
            if b is None or len(b) < 60: continue
            items.append(((t, 'LONG'), b, cut, 'stock', 'LONG', t))
            if sp: items.append(((t, 'SHORT'), b, cut, 'stock', 'SHORT', t))
        rc = RC.compute_many(items, workers=2)
        df = pd.DataFrame(rc); df[['t', 'rc_direction']] = pd.DataFrame(df.pop('key').tolist(), index=df.index)
        run = os.path.basename(run_dir.rstrip('/'))
        df.insert(0, 'setup_id', [f'{run}|{t}|{dr}' for t, dr in zip(df['t'], df['rc_direction'])])
        df.to_csv(f'{run_dir}/research_columns.csv', index=False)
        st = RC.status_summary(rc); log('research_columns:', json.dumps(st, ensure_ascii=False)[:300]); return st
    except Exception as e:
        log(f'research_columns block failed: {e.__class__.__name__}: {e}'); return {'error': str(e)[:200]}

def scan_hooks(run_dir, cut, px_dir):
    """sr-waves-eval/HOOKS.md 'swing_scan.py' snippet, applied HERE on the scan output (swing_scan.py stays untouched):
    per mcap_ok stock: S/R (scanner_levels, on the SAME scan bars = daily=b, single-source rule), volume waves LONG view + SHORT-view
    wave_* (scanner_waves, families), Elliott v2 both views (scanner_elliott_v2). -> <run_dir>/scan_hooks.csv (weight 0)."""
    try:
        import scanner_levels as SRL, scanner_waves as WV, scanner_elliott_v2 as EV2, scanner_stops as ST
    except Exception as e:
        log('scan hooks skipped:', e); return None
    t0 = time.time(); d = pd.read_csv(f'{run_dir}/scan_raw.csv'); out = []
    for t, ok in zip(d['t'], d['mcap_ok'].astype(str).str.lower().eq('true')):
        if str(t).startswith('^') or not ok: continue
        try:
            b = ST.daily_bars(t, 'stock', cut, px_dir)
            if b is None or len(b) < 60: out.append({'t': t, 'wv_flag': 'no data / <60 bars'}); continue
            rec = {'t': t}
            try: rec.update(SRL.levels_for(t, cut, 'SWING', 'LONG', daily=b)['summary'])
            except Exception as e: rec['sr_flag'] = f'error {e.__class__.__name__}'
            rec.update(WV.waves_columns(b, cut, 'stock', 'LONG'))
            rec.update({f'short_{k}': v for k, v in WV.waves_columns(b, cut, 'stock', 'SHORT').items() if k.startswith('wave_')})
            rec.update(EV2.elliott_v2_columns(b, cut, 'stock', 'LONG'))
            out.append(rec)
        except Exception as e:
            out.append({'t': t, 'wv_flag': f'error {e.__class__.__name__}'})
    df = pd.DataFrame(out); df.to_csv(f'{run_dir}/scan_hooks.csv', index=False)
    log(f'scan hooks (S/R + waves + Elliott v2): {len(df)} names in {time.time()-t0:.0f}s')
    return df

def tool_stats(tracker):
    """python3 tool_stats.py <tracker> --extra "scan-runs/*/research_columns.csv" --out research-models/tool_stats -> newest Hebrew md."""
    out = '/workspace/research-models/tool_stats'
    if not os.path.exists('/workspace/tool_stats.py'): return None, 'tool_stats.py missing'
    if not tracker or not os.path.exists(tracker): return None, f'tracker not found: {tracker}'
    t0 = time.time()
    r = subprocess.run([sys.executable, '/workspace/tool_stats.py', tracker, '--extra', '/workspace/scan-runs/*/research_columns.csv', '--out', out],
                       capture_output=True, text=True, timeout=1800)
    mds = [m for m in sorted(glob.glob(f'{out}/tool_stats_*_he.md'), key=os.path.getmtime) if os.path.getmtime(m) >= t0 - 5]
    if r.returncode != 0 or not mds: return None, f'tool_stats exit {r.returncode}: {(r.stderr or r.stdout)[-300:]}'
    return open(mds[-1]).read(), None

def latest_tracker():
    xs = sorted(glob.glob('/workspace/scan-tracker-*.xlsx'), key=os.path.getmtime)
    return xs[-1] if xs else None

# ------------------------------------------------------------------ paper ledger
PAPER_COLS = ['paper_id', 'run_dir', 'scan_asof_local', 'cutoff_utc', 'alert_date', 'ticker', 'asset', 'direction', 'rule_score', 'rule_basis',
              'entry_rule', 'entry_session', 'entry_price', 'atr14_at_cutoff', 'stop_rule', 'stop_atr_mult', 'stop', 'target_level', 'target_rule',
              'earnings_gate', 'watch_short_below_va120', 'momentum_score', 'short_ck_score', 'levels_file', 'status', 'exit_date', 'exit_price',
              'exit_reason'] + [f'cum_d{k}' for k in range(1, 21)] + ['is_paper', 'weight']

def append_paper(run_dir, rows, cut, asof):
    import scanner_levelsfile as LF
    es = LF.entry_session(cut)
    out = []
    for c, L in rows:
        crypto = c.get('asset') == 'crypto'
        out.append({'paper_id': f"{os.path.basename(run_dir)}|{c['t']}|{c['direction']}", 'run_dir': run_dir, 'scan_asof_local': asof,
                    'cutoff_utc': str(cut), 'alert_date': str(pd.Timestamp(asof).date()), 'ticker': c['t'], 'asset': c.get('asset', 'stock'),
                    'direction': c['direction'], 'rule_score': c.get('rank_score'), 'rule_basis': c.get('rank_basis'),
                    'entry_rule': 'next session open' if not crypto else 'next UTC day open', 'entry_session': str(es.date()) if not crypto else
                    str((pd.Timestamp(cut).tz_convert('UTC').normalize() + pd.Timedelta(days=1)).date()), 'entry_price': None,
                    'atr14_at_cutoff': (L.get('technical') or {}).get('atr14_wilder'), 'stop_rule': L['trade'].get('stop_rule'),
                    'stop_atr_mult': 3.0 if crypto else 4.0, 'stop': None,
                    'target_level': L['trade'].get('target') if c['direction'] == 'LONG' and not crypto else None, 'target_rule': L['trade'].get('target_rule'),
                    'earnings_gate': (L.get('earnings') or {}).get('status'), 'watch_short_below_va120': c.get('watch_short_below_va120'),
                    'momentum_score': c.get('momentum_score'), 'short_ck_score': c.get('short_ck_score'), 'levels_file': LF.path(run_dir, c),
                    'status': 'pending_entry', 'is_paper': True, 'weight': 0})
    df = pd.DataFrame(out)
    for k in PAPER_COLS:
        if k not in df: df[k] = None
    df = df[PAPER_COLS]
    if os.path.exists(PAPER_LEDGER):
        old = pd.read_csv(PAPER_LEDGER); df = df[~df.paper_id.isin(old.paper_id)]
    df.to_csv(PAPER_LEDGER, mode='a', header=not os.path.exists(PAPER_LEDGER), index=False)
    return len(df)

# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--run-dir'); ap.add_argument('--scan-only', action='store_true')
    ap.add_argument('--no-models', '--no-platforms', dest='no_models', action='store_true')
    ap.add_argument('--paper', action='store_true'); ap.add_argument('--trial', action='store_true'); ap.add_argument('--suffix', default=None)
    ap.add_argument('--candidates', type=int, default=20); ap.add_argument('--sector-cap', type=int, default=int(os.environ.get('PLATFORM_MAX_PER_SECTOR', '2')))
    ap.add_argument('--min-score', type=float, default=MIN_SCORE_DEFAULT, help='unified-score floor; names below it are not selected (default 60, see addendum)')
    ap.add_argument('--no-crypto', action='store_true')
    ap.add_argument('--budget', type=float, default=None); ap.add_argument('--tracker', default=None)
    ap.add_argument('--no-hooks', action='store_true'); ap.add_argument('--no-research-columns', action='store_true'); ap.add_argument('--no-tool-stats', action='store_true')
    a = ap.parse_args()
    if a.paper and not a.no_models: raise SystemExit('--paper requires --no-models (paper mode never calls an LLM)')
    suffix = a.suffix if a.suffix is not None else ('_trial' if a.trial else '')
    if a.trial: os.environ['PLATFORM_TRIAL'] = '1'
    if a.budget is not None: os.environ['PLATFORM_BUDGET_USD'] = str(a.budget)
    run_dir = a.run_dir or run_scan(suffix, paper=a.paper)
    log('run folder:', run_dir)
    if a.scan_only: return
    import scanner_platforms as SP, scanner_levelsfile as LF
    if a.budget is not None: SP.BUDGET_USD = a.budget
    cut = cutoff_of(run_dir); px_dir = f"/workspace/scanner-momentum-cache/{cut.strftime('%Y%m%dT%H%MZ')}"
    meta = json.load(open(f'{run_dir}/run_meta.json')) if os.path.exists(f'{run_dir}/run_meta.json') else {}
    asof = meta.get('scan_asof_local') or str(cut.tz_convert('Asia/Jerusalem'))
    regime = SP.regime_summary(run_dir)
    # 2. full rule pass (no cap, no top-N)
    SP.MAX_PER_SECTOR = 0
    full = SP.select_candidates(run_dir, n_long=100000, n_short=100000)
    SP.MAX_PER_SECTOR = a.sector_cap
    for c in full: c['asset'] = 'stock'
    crypto = []
    if not a.no_crypto:
        try:
            import scanner_crypto as SCR
            crypto, cdall = SCR.scan(run_dir, cut, top=100)
            for c in crypto: c['asset'] = 'crypto'
            try:   # same percentile scale as stocks (group too small for the stock percentile -> crypto's own distribution)
                import scanner_momentum as SM
                # percentile over the WHOLE crypto universe scanned (crypto_scan.csv), not only the trend-passing coins
                cdf = SM.rank(pd.DataFrame({'ticker': cdall['t'].tolist(), 'asset': 'crypto', 'excluded_reason': None,
                                             'momentum_12_1': pd.to_numeric(cdall['momentum_12_1'], errors='coerce').tolist(), 'lowvol_60d': np.nan,
                                             'asof_utc': None, 'last_bar': None, 'history_bars': None, 'missing_history_flag': None, 'mcap_b': None}))
                ms = dict(zip(cdf['ticker'], cdf['momentum_score']))
                for c in crypto: c['momentum_score'] = _num(ms.get(c['t']))
            except Exception as e:
                log('crypto percentile failed:', e)
        except Exception as e:
            log('crypto leg failed:', e)
    allc = full + crypto
    for c in allc: c['unified_score'], c['rank_basis'] = unified_score(c); c['rank_score'] = c['unified_score']
    log(f'rule pass: {sum(c["direction"]=="LONG" and c["asset"]=="stock" for c in allc)} stock LONG, '
        f'{sum(c["direction"]=="SHORT" for c in allc)} stock SHORT, {len(crypto)} crypto LONG')
    # 3. levels JSON for every passing name + pre-gate
    built = {}
    for c in allc:
        c['_regime'] = regime
        try:
            L, x = LF.build(c, run_dir, cut, px_dir)
            g = LF.earnings_gate(c, cut); L['earnings'] = dict(g, stage='pre (Yahoo + OpenBB; Perplexity not yet asked)')
            LF.save(L, run_dir, c); LF.apply_trade(c, L); c['earnings_gate'] = g['status']; c['_eg'] = g
            built[(c['t'], c['direction'])] = (c, L, x)
        except Exception as e:
            c['levels_error'] = f'{e.__class__.__name__}: {e}'[:200]; log('levels failed', c['t'], c['levels_error'])
    # 5. selection (pure) + candidates_full.csv - every rule-passing name with its score, rank and why it was / was not picked
    ok = [c for c in allc if (c['t'], c['direction']) in built]
    sel, blk = select(ok, a.candidates, a.sector_cap, a.min_score)
    rows = []
    for c in allc:
        L = (built.get((c['t'], c['direction'])) or (None, None))[1]
        f = LF.facts_for_prompt(L) if L else {}
        rows.append({'ticker': c['t'], 'asset': c['asset'], 'direction': c['direction'], 'unified_score': c.get('unified_score'), 'score_rank': None,
                     'passes_min_score': (c.get('unified_score') is not None and c['unified_score'] >= a.min_score), 'min_score': a.min_score,
                     ('would_select' if a.paper else 'selected'): any(c is x for x in sel), 'selection_note': c.get('_sel_note', c.get('levels_error')),
                     'rank_basis': c.get('rank_basis'),
                     'momentum_score': c.get('momentum_score'), 'momentum_12_1': c.get('momentum_12_1'), 'short_ck_score': c.get('short_ck_score'),
                     'short_rule_pass': c.get('short_rule_pass'), 'sector_etf': c.get('sector_etf'), 'mcap_b': c.get('mcap_b'),
                     'entry': c.get('entry'), 'stop': c.get('stop'), 'target': c.get('target'), 'stop_rule': (f.get('trade') or {}).get('stop_rule'),
                     'target_rule': (f.get('trade') or {}).get('target_rule'), 'earnings_block': bool((c.get('_eg') or {}).get('blocked')),
                     'earnings_status': c.get('earnings_gate'), 'next_earnings': (c.get('_eg') or {}).get('next_earnings'),
                     'td_to_earnings': (c.get('_eg') or {}).get('td_to_earnings'), 'elliott_v1': (f.get('elliott_v1') or {}).get('label'),
                     'elliott_v2': (f.get('elliott_v2') or {}).get('label'), 'fib_v1_1618': ((f.get('fib_v1') or {}).get('levels') or {}).get('1.618'),
                     'fib_v2_1618': ((f.get('fib_v2') or {}).get('levels') or {}).get('1.618'), 'vp120_poc': (f.get('vp120') or {}).get('poc'),
                     'vp120_vah': (f.get('vp120') or {}).get('vah'), 'vp120_val': (f.get('vp120') or {}).get('val'),
                     'sr_support': (f.get('sr_nearest') or {}).get('sr_support'), 'sr_resistance': (f.get('sr_nearest') or {}).get('sr_resistance'),
                     **{k: v for k, v in (f.get('waves') or {}).items() if k.startswith('wave_') and not k.endswith('reasons')},
                     'rsi14': (f.get('waves') or {}).get('rsi14'),
                     'cci20': (f.get('waves') or {}).get('cci20'), 'watch_short_below_va120': c.get('watch_short_below_va120'),
                     'bar_hash': (f.get('levels_file') or {}).get('bar_hash'), 'levels_file': LF.path(run_dir, c) if L else None,
                     'levels_error': c.get('levels_error')})
    df = pd.DataFrame(rows).sort_values(['unified_score', 'ticker'], ascending=[False, True], na_position='last').reset_index(drop=True)
    df['score_rank'] = df['unified_score'].rank(ascending=False, method='min').astype('Int64')
    df.to_csv(f'{run_dir}/candidates_full.csv', index=False, encoding='utf-8-sig')
    log(f'candidates_full.csv: {len(rows)} names')
    if not a.no_hooks: scan_hooks(run_dir, cut, px_dir)
    if a.paper:
        n = append_paper(run_dir, [(c, built[(c['t'], c['direction'])][1]) for c in ok], cut, asof)
        log(f'paper: appended {n} rows to {PAPER_LEDGER} (NOT positions)')
        if not a.no_research_columns: research_columns(run_dir, cut, px_dir)
        json.dump({'mode': 'paper', 'n_full': len(rows), 'n_paper_appended': n}, open(f'{run_dir}/paper_summary.json', 'w'), indent=1)
        return
    # 6. selection (computed above): one ranking, no fixed long/short split; may be 20 longs and 0 shorts, or fewer than N
    cands = sel + blk
    ids = {id(c) for c in sel}
    for c in cands: c['_selected'] = id(c) in ids
    selL = [c for c in sel if c['asset'] == 'stock' and c['direction'] == 'LONG']; selS = [c for c in sel if c['direction'] == 'SHORT']
    selC = [c for c in sel if c['asset'] == 'crypto']; blkL = [c for c in blk if c['direction'] == 'LONG']; blkS = [c for c in blk if c['direction'] == 'SHORT']
    n_floor = sum(1 for c in ok if (c.get('unified_score') or -1) >= a.min_score)
    log(f'one ranking, floor {a.min_score:g}: {n_floor}/{len(ok)} at or above the floor -> {len(sel)} selected (N={a.candidates})')
    if selC and not a.no_models:
        try: SCR.fetch_news(run_dir, [c['t'] for c in selC], cut)
        except Exception as e: log('crypto news failed:', e)
    log(f'selected {len(selL)} LONG + {len(selS)} SHORT + {len(selC)} crypto; +{len(blkL)+len(blkS)} earnings-blocked researched')
    # 7. charts from the levels JSON
    ci_path = f'{run_dir}/charts/chart_index.json'
    if os.path.exists(ci_path): os.remove(ci_path)
    items = []
    for c in cands:
        _, L, x = built[(c['t'], c['direction'])]
        try:
            e = LF.render(run_dir, c, x); c['_chart_png'] = e['png']; items.append(dict(e, L=LF.load(run_dir, c)))
        except Exception as ex:
            log('chart failed', c['t'], ex); c['_chart_error'] = str(ex)[:200]
    try:   # HOOKS.md chart hook: charts_he.pdf, built only from the same levels files (render_run itself re-reads stock bars -> adapter)
        import scanner_charts as SC
        if items: SC.build_pdf(run_dir, items, cut)
    except Exception as ex:
        log('charts_he.pdf failed:', ex)
    # 8. platforms
    res = SP.run_platforms(cands, run_dir, enabled=not a.no_models)
    # 4b. post-gate with Perplexity + exception; levels JSON updated (earnings only)
    eg = {}
    for c, r in zip(cands, res['rows']):
        if c['asset'] == 'crypto': eg[c['t']] = c['_eg']; continue
        x_ = res['raw'].get(c['t'], {})
        g = LF.earnings_gate(c, cut, pplx=x_.get('pplx'), claude=x_.get('claude_analyst'), gpt=x_.get('gpt_advocate'))
        L = LF.load(run_dir, c); L['earnings'] = dict(g, stage='final (Yahoo + OpenBB + Perplexity, exception checked)'); LF.save(L, run_dir, c)
        c['_levels'] = L; c['earnings_gate'] = g['status']; c['_eg'] = g; eg[c['t']] = g
    _ledger_gate(SP.ledger_path(run_dir), run_dir, cands)
    # 9. tracker rows + reconciliation
    run = os.path.basename(run_dir.rstrip('/'))
    trows = [LF.tracker_row(LF.load(run_dir, c), f"{run}|{c['t']}|{c['direction']}", str(pd.Timestamp(asof).date())) for c in cands]
    report_numbers = {(c['t'], c['direction']): {'entry': c['entry'], 'stop': c['stop'], 'target': c['target']} for c in cands}
    ci = json.load(open(ci_path)) if os.path.exists(ci_path) else []
    rec = LF.reconcile(run_dir, cands, report_numbers, trows, ci)
    for t_ in trows: t_['recon_status'] = 'תואם' if not rec.get((t_['ticker'], t_['direction'])) else 'לא תואם'
    pd.DataFrame(trows).to_csv(f'{run_dir}/tracker_rows.csv', index=False, encoding='utf-8-sig')
    json.dump({f'{k[0]}|{k[1]}': v for k, v in rec.items()}, open(f'{run_dir}/reconciliation.json', 'w'), ensure_ascii=False, indent=1)
    log('reconciliation:', sum(not v for v in rec.values()), 'תואם /', sum(bool(v) for v in rec.values()), 'לא תואם')
    sel = [f"{c['t']}|{c['direction']}" for c in cands if not rec.get((c['t'], c['direction']))
           and not (c.get('_eg') or {}).get('blocked') and (c.get('_selected') or (c.get('_eg') or {}).get('exception'))]
    json.dump(sel, open(f'{run_dir}/selected.json', 'w'), indent=1)     # = the report's recommendations (positions registry input)
    # 10. research columns + tool_stats + report
    rcs = None if a.no_research_columns else research_columns(run_dir, cut, px_dir)
    ts_md, ts_err = (None, 'skipped') if a.no_tool_stats else tool_stats(a.tracker or latest_tracker())
    res.update(earnings=eg, recon=rec, tool_stats_md=ts_md, tool_stats_err=ts_err, research_status=rcs, n_full=len(rows),
               candidates_n=a.candidates, min_score=a.min_score, sector_cap=a.sector_cap, run_kind='trial' if suffix == '_trial' else 'weekly', cutoff=str(cut))
    import unified_report as UR
    paths = UR.write_report(run_dir, res)
    log('report:', paths)

def _ledger_gate(path, run_dir, cands):
    """write the final earnings-gate status into this run's ledger rows (rows were written before the post-gate)."""
    if not os.path.exists(path): return
    d = pd.read_csv(path, dtype={'earnings_gate': object})
    for c in cands:
        m = (d.run_dir == run_dir) & (d.ticker == c['t']) & (d.direction == c['direction'])
        d.loc[m, 'earnings_gate'] = c.get('earnings_gate')
    d.to_csv(path, index=False)

if __name__ == '__main__':
    main()
