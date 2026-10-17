"""Learning loop (platforms-learning-loop-addendum-2026-10-08.txt). Positions registry, point-in-time technical snapshots,
checkpoint triggers (cost gate), right/wrong scoring with real prices, per-platform scoreboard, weekly versioned prompts.
  * Positions = recommendations of the weekly unified scan (tracker_rows.csv: recon 'תואם', not earnings-blocked). Paper trades and
    trial rows are NEVER positions. Entry = next session open after the scan (PIT; fallback the scan's entry ref).
  * Exit for measurement = the bot's own stop rule (scanner_stops.stop_status, close-checked) or day 20, whichever first.
  * Scoring (verdict vs the direction-adjusted excess return vs SPY/BTC from the decision date to the exit = excess_dir):
      approve / supports / Claude conviction >= 60 / Grok & Jev sentiment with the trade  -> right if excess_dir > 0
      veto / opposes / conviction < 45 / sentiment against the trade                        -> right if excess_dir < 0
      flag / neutral / 45-59 / 0 sentiment                                                  -> no call
      checkpoint_action: hold -> right if the remaining excess_dir > 0; tighten / exit -> right if < 0.
  * Lessons: ONLY from CLOSED positions, built ONCE per ISO week, written to prompts/<platform>_vN.txt + prompts/CHANGELOG.md;
    prompts/active.json says which version each platform uses (ledger column prompt_version) so we can measure if lessons helped.
  * All LLM verdict columns: forward-only from 12.10.2026 (trial / sim rows never counted)."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, sys, json, glob, math, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, _SCANNER_ROOT)
PROMPTS = os.environ.get('LESSONS_PROMPTS_DIR', (_SCANNER_ROOT + '/prompts'))
REGISTRY = (_SCANNER_ROOT + '/scan-runs/positions_registry.csv')
FORWARD_FROM = '2026-10-12'
PLATFORMS = ('grok', 'pplx', 'claude', 'gpt', 'jev')
HORIZON = 20
REG_COLS = ['trade_id', 'trade_key', 'ticker', 'asset', 'direction', 'source_run', 'scan_asof_local', 'cutoff_utc', 'entry_session', 'entry_ref',
            'entry_price', 'entry_fill', 'stop_initial', 'target', 'atr14_at_cutoff', 'levels_file', 'status', 'checkpoints_done', 'last_decision_utc',
            'last_state', 'last_close', 'last_close_date', 'current_stop', 'unrealized_dir', 'exit_date', 'exit_price', 'exit_reason', 'ret_dir',
            'bench_ret', 'excess_dir', 'half_taken', 'is_trial', 'is_sim', 'blocked_by_veto',
            # 17.10: half take-profit (stock longs, Fib 1.618 on close) + whole-position returns (1/2 at half_price, 1/2 at the last close /
            # exit). ret_dir / excess_dir / unrealized_dir stay the FULL-position values (platform right/wrong scoring is unchanged).
            'stop_initial_fill', 'half_date', 'half_price', 'unrealized_dir_weighted', 'ret_dir_weighted', 'excess_dir_weighted']

# ------------------------------------------------------------------ prompt versions
def _active():
    f = f'{PROMPTS}/active.json'
    return json.load(open(f)) if os.path.exists(f) else {}

def active_prompt(platform):
    v = _active().get(platform)
    if not v: return 'v1', ''
    f = f'{PROMPTS}/{platform}_{v}.txt'
    return (v, open(f).read().strip()) if os.path.exists(f) else ('v1', '')

# ------------------------------------------------------------------ registry
def load_registry(path=REGISTRY):
    if not os.path.exists(path): return pd.DataFrame(columns=REG_COLS)
    d = pd.read_csv(path, dtype=object)
    for k in REG_COLS:
        if k not in d: d[k] = None
    return d[REG_COLS]

def save_registry(d, path=REGISTRY):
    os.makedirs(os.path.dirname(path), exist_ok=True); d[REG_COLS].to_csv(path, index=False)

def register_run(run_dir, path=REGISTRY, is_sim=False, veto_blocked=None):
    """add the weekly run's recommendations (tracker_rows.csv recon 'תואם', earnings not blocked). Trial / paper runs refused."""
    if ('_trial' in run_dir or '_paper' in run_dir) and not is_sim: return 0
    tr = f'{run_dir}/tracker_rows.csv'
    if not os.path.exists(tr): return 0
    t = pd.read_csv(tr)
    t = t[(t.recon_status == 'תואם') & ~t.earnings_status.astype(str).str.startswith('נחסם')]
    import scanner_levelsfile as LF
    meta = json.load(open(f'{run_dir}/run_meta.json')); cut = pd.Timestamp(t.cutoff_utc.iloc[0]) if len(t) else None
    sel = json.load(open(f'{run_dir}/selected.json')) if os.path.exists(f'{run_dir}/selected.json') else None
    reg = load_registry(path); new = []
    for _, r in t.iterrows():
        vb = (veto_blocked or {}).get(f"{r.ticker}|{r.direction}")   # 16.10: veto-blocked shorts tracked as paper positions to completion
        if sel is not None and f"{r.ticker}|{r.direction}" not in sel and not vb: continue
        tid = r.setup_id
        if tid in set(reg.trade_id): continue
        L = json.load(open(LF.path(run_dir, {'t': r.ticker, 'direction': r.direction})))
        es = LF.entry_session(cut) if r.asset != 'crypto' else (cut.tz_convert('UTC').normalize() + pd.Timedelta(days=1)).tz_localize(None)
        if os.environ.get('ENTRY_SESSION_OVERRIDE'): es = pd.Timestamp(os.environ['ENTRY_SESSION_OVERRIDE'])   # 12.10: late manual run (cutoff Fri close, entry Tue open)
        new.append({'trade_id': tid, 'trade_key': f"{r.ticker}|{r.direction}|{L['data']['last_bar']}", 'ticker': r.ticker, 'asset': r.asset,
                    'direction': r.direction, 'source_run': run_dir, 'scan_asof_local': meta.get('scan_asof_local'), 'cutoff_utc': str(cut),
                    'entry_session': str(pd.Timestamp(es).date()), 'entry_ref': r.entry, 'stop_initial': r.stop, 'target': r.target,
                    'atr14_at_cutoff': (L.get('technical') or {}).get('atr14_wilder'), 'levels_file': LF.path(run_dir, {'t': r.ticker, 'direction': r.direction}),
                    'status': 'open', 'checkpoints_done': '', 'last_decision_utc': str(cut), 'last_state': json.dumps(snapshot_state(L, None, r.direction)),
                    'is_trial': False, 'is_sim': is_sim, 'blocked_by_veto': vb or ''})
    if new: reg = pd.concat([reg, pd.DataFrame(new)], ignore_index=True); save_registry(reg, path)
    return len(new)

# ------------------------------------------------------------------ bars (same sources as the scan)
def bars(ticker, asset, asof_utc, cache_dir=None):
    asof = pd.Timestamp(asof_utc).tz_convert('UTC')
    if asset == 'crypto':
        import scanner_crypto as SCR
        return SCR.alpaca_daily(ticker, asof)
    import scanner_stops as ST
    px = cache_dir or f"{_SCANNER_ROOT}/scanner-momentum-cache/{asof.strftime('%Y%m%dT%H%MZ')}"
    return ST.daily_bars(ticker, 'stock', asof, px)

def bench(asset, asof_utc, cache_dir=None):
    return bars('BTC' if asset == 'crypto' else 'SPY', asset, asof_utc, cache_dir)

def close_cut(day, asset):
    """UTC moment a daily bar of `day` is complete (stock: 16:00 ET close + 5 min; crypto: next 00:00 UTC)."""
    d = pd.Timestamp(day).normalize()
    if asset == 'crypto': return (d + pd.Timedelta(days=1)).tz_localize('UTC')
    return (d + pd.Timedelta(hours=16, minutes=5)).tz_localize('America/New_York').tz_convert('UTC')

# ------------------------------------------------------------------ technical snapshot state + triggers
def snapshot_state(L, stop_info, direction):
    if not L: return {}
    import scanner_levelsfile as LF
    f = LF.facts_for_prompt(L); te = f.get('technical') or {}; c = te.get('last_close'); vp = f.get('vp120') or {}
    sgn = 1 if direction == 'LONG' else -1
    st = {'last_bar': L['data']['last_bar'], 'close': c,
          'above_sma50': None if not (c and te.get('sma50')) else bool(c > te['sma50']),
          'above_sma200': None if not (c and te.get('sma200')) else bool(c > te['sma200']),
          'elliott_v2': (f.get('elliott_v2') or {}).get('label'), 'elliott_v2_state': (f.get('elliott_v2') or {}).get('state'),
          'elliott_v1_valid': (f.get('elliott_v1') or {}).get('valid'),
          'va120_pos': None if not (c and vp.get('vah') and vp.get('val')) else ('above' if c > vp['vah'] else 'below' if c < vp['val'] else 'inside'),
          'mom_12_1': te.get('mom_12_1'), 'atr14': te.get('atr14_wilder')}
    if stop_info:
        lv = stop_info.get('next_level'); A = te.get('atr14_wilder')
        st.update(stop_level=lv, stopped=bool(stop_info.get('stopped')), half_taken=stop_info.get('half_taken'),
                  near_stop=bool(lv and c and A and sgn * (c - lv) <= 1.0 * A))
    return st

def triggers(prev, cur, trade, jev):
    """cost gate: reasons to call the paid LLM platforms at a day-5/10 checkpoint (else 'skipped - no material change')."""
    t = []
    if jev and (jev.get('n_material') or 0) > 0: t.append(f"Jev: {jev['n_material']} כותרות מהותיות")
    # 10.10 tightened (sim: the old rule fired on 22/23 checkpoints): a low-confidence headline triggers only if Jev still rates it
    # material (>= 2) and relevant; a manipulation-flagged headline always triggers.
    lc = [i for i in (jev or {}).get('for_claude') or [] if i.get('flagged') or (i.get('materiality', 0) >= 2 and i.get('relevant', 0) >= 0.6)]
    if lc: t.append(f"Jev: {len(lc)} כותרות מהותיות בביטחון נמוך/חשודות")
    if cur.get('near_stop'): t.append('קרוב לסטופ (פחות מ-1 ATR)')
    tg = trade.get('target')
    try: tg = float(tg)
    except Exception: tg = None
    if tg and cur.get('close') and ((trade['direction'] == 'LONG' and cur['close'] >= tg) or (trade['direction'] == 'SHORT' and cur['close'] <= tg)):
        t.append('הגיע ליעד Fib 1.618')
    if cur.get('half_taken') and not (prev or {}).get('half_taken'): t.append('חצי מומש ביעד')
    if prev:
        for k, lab in (('above_sma50', 'SMA50'), ('above_sma200', 'SMA200')):
            if prev.get(k) is not None and cur.get(k) is not None and prev[k] != cur[k]: t.append(f"{'איבד' if prev[k] else 'חזר מעל'} {lab}")
        if prev.get('va120_pos') and cur.get('va120_pos') and prev['va120_pos'] != cur['va120_pos']: t.append(f"VA120: {prev['va120_pos']}→{cur['va120_pos']}")
        # Elliott: provisional relabels are noise; trigger only on a CONFIRMED (non-provisional) change of the count
        pe, ce = str(prev.get('elliott_v2') or ''), str(cur.get('elliott_v2') or '')
        if pe and ce and pe != ce and 'provisional' not in ce: t.append(f"ספירת אליוט השתנתה ({pe} → {ce})")
        if prev.get('elliott_v1_valid') and cur.get('elliott_v1_valid') is False: t.append('ספירת אליוט v1 בוטלה')
    return t

# ------------------------------------------------------------------ scoring
def call_of(row):
    """+1 = with the trade, -1 = against, 0 = no call, None = no verdict."""
    p, v = row.get('platform'), str(row.get('verdict') or '').lower()
    cv = row.get('conviction_or_sentiment')
    try: cv = float(cv)
    except Exception: cv = None
    if p == 'claude':
        if cv is None: return None
        return 1 if (cv >= 60 and v != 'opposes') else -1 if (cv < 45 or v == 'opposes') else 0
    if p == 'grok' and cv is not None and row.get('decision_point') != 'entry_x':
        return 1 if cv * (1 if row['direction'] == 'LONG' else -1) > 0 else -1 if cv * (1 if row['direction'] == 'LONG' else -1) < 0 else 0
    if p == 'jev':
        if not v or v in ('nan', 'none'): return None
        s = 1 if v.startswith('חיובי') else -1 if v.startswith('שלילי') else 0
        return s * (1 if row['direction'] == 'LONG' else -1)
    return {'approve': 1, 'veto': -1, 'flag': 0}.get(v)

def _ret_between(x, d0, d1):
    x = x[~x.index.duplicated()]
    i0 = x.index.searchsorted(pd.Timestamp(d0).normalize()); i1 = x.index.searchsorted(pd.Timestamp(d1).normalize())
    if i0 >= len(x) or i1 >= len(x): return None
    return float(x.Close.iloc[i1] / x.Close.iloc[i0] - 1)

def score(ledger, registry, asof_utc, cache_dir=None):
    """ledger rows (entry + checkpoints) of CLOSED positions -> right / wrong / no call, using real closes."""
    L = ledger.copy(); reg = registry.set_index('trade_key') if len(registry) else registry
    out = []; bx = {}
    for _, r in L.iterrows():
        k = r.get('trade_key')
        if k not in getattr(reg, 'index', []) or str(reg.loc[k, 'status']) != 'closed': continue
        T = reg.loc[k]; sgn = 1 if T.direction == 'LONG' else -1
        key = (T.ticker, T.asset)
        if key not in bx: bx[key] = (bars(T.ticker, T.asset, asof_utc, cache_dir), bench(T.asset, asof_utc, cache_dir))
        x, b = bx[key]
        d0 = str(r.get('asof_local') or '')[:10] if r.get('decision_point') != 'entry' else T.entry_session
        if x is None or b is None: continue
        rs, rb = _ret_between(x, d0, T.exit_date), _ret_between(b, d0, T.exit_date)
        if rs is None or rb is None: continue
        ex = sgn * (rs - rb)
        c = call_of(r.to_dict())
        right = None if c in (None, 0) else (c * ex > 0)
        a = str(r.get('checkpoint_action') or '').lower(); ar = None
        if a in ('hold', 'tighten', 'exit'): ar = (ex > 0) if a == 'hold' else (ex < 0)
        out.append(dict(r.to_dict(), excess_dir_from_decision=ex, call=c, right=right, action_right=ar, exit_reason=T.exit_reason))
    return pd.DataFrame(out)

def scoreboard(S):
    if S is None or not len(S): return pd.DataFrame()
    rows = []
    for (p, dp), g in S.groupby(['platform', 'decision_point']):
        calls = g[g.right.notna()]
        acts = g[g.action_right.notna()] if 'action_right' in g else g.iloc[0:0]
        rows.append({'platform': p, 'decision_point': dp, 'n_rows': len(g), 'n_calls': len(calls), 'right': int(calls.right.sum()) if len(calls) else 0,
                     'wrong': int((~calls.right.astype(bool)).sum()) if len(calls) else 0, 'no_call': int((g.call == 0).sum()),
                     'hit_rate': round(float(calls.right.mean()), 3) if len(calls) else None,
                     'actions_scored': len(acts), 'actions_right': int(acts.action_right.sum()) if len(acts) else 0,
                     'distinct_entry_days': g.trade_key.astype(str).str.split('|').str[-1].nunique(),
                     'mean_excess_when_with': round(float(g[g.call == 1].excess_dir_from_decision.mean()), 4) if (g.call == 1).any() else None})
    return pd.DataFrame(rows)

# ------------------------------------------------------------------ weekly lessons (closed trades only)
def build_weekly_lessons(S, asof_utc, min_closed=3, force_week=None):
    """once per ISO week: per platform, deterministic patterns of its WRONG calls on closed positions -> prompts/<p>_vN.txt."""
    os.makedirs(PROMPTS, exist_ok=True)
    wk = force_week or pd.Timestamp(asof_utc).strftime('%G-W%V')
    act = _active(); log = []
    state_f = f'{PROMPTS}/weekly_state.json'
    st = json.load(open(state_f)) if os.path.exists(state_f) else {}
    if st.get('last_week') == wk: return {'skipped': f'lessons already built for {wk}'}
    if S is None or not len(S): return {'skipped': 'no closed, scored positions yet'}
    for p in PLATFORMS:
        g = S[(S.platform == p) & S.right.notna()]
        if g.trade_key.nunique() < min_closed: log.append((p, f'only {g.trade_key.nunique()} closed positions (< {min_closed}) - no new version')); continue
        wrong = g[~g.right.astype(bool)]
        lines = [f"- Track record on closed positions so far: {int(g.right.sum())} right / {len(g) - int(g.right.sum())} wrong calls "
                 f"({g.trade_key.nunique()} positions)."]
        for (dirn, dp), gg in wrong.groupby(['direction', 'decision_point']):
            if len(gg) < 2: continue
            side = 'with' if (gg.call == 1).mean() >= 0.5 else 'against'
            ex = gg.exit_reason.value_counts().index[0]
            lines.append(f"- {len(gg)} wrong '{side}-the-trade' calls on {dirn} positions at {dp}; most of these exited by '{ex}'. "
                         f"Be more demanding before calling {side} the trade in this situation.")
        if len(lines) == 1: lines.append('- No repeated error pattern yet (fewer than 2 similar mistakes).')
        cur = act.get(p, 'v1'); nv = f"v{int(cur[1:]) + 1}"
        open(f'{PROMPTS}/{p}_{nv}.txt', 'w').write('\n'.join(lines) + '\n')
        act[p] = nv; log.append((p, f'{cur} -> {nv}: {len(lines) - 1} lesson lines from {g.trade_key.nunique()} closed positions'))
    json.dump(act, open(f'{PROMPTS}/active.json', 'w'), indent=1)
    with open(f'{PROMPTS}/CHANGELOG.md', 'a') as fh:
        fh.write(f"\n## {wk} ({pd.Timestamp(asof_utc).tz_convert('Asia/Jerusalem'):%d.%m.%Y %H:%M} Israel)\n" + ''.join(f'- {p}: {m}\n' for p, m in log))
    st['last_week'] = wk; json.dump(st, open(state_f, 'w'))
    return {'week': wk, 'log': log, 'active': act}
