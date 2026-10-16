"""Model credibility on SHORT warnings -> score penalty (scoring v3-shortveto-cred, on top of v2-vix30). Approved by Ilan 16.10.2026 17:16 IL.

WARNINGS (per model, on a SHORT setup, entry decision):
  gpt / grok / pplx : strong = verdict 'veto'; weak = verdict 'flag'
  claude            : strong = direction_view 'opposes' OR conviction <= 40
  jev               : strong = news sentiment >= +0.25 (against the short)
DISCRIMINATION RULE (point-in-time, over all SHORT entry rows of that model in the ledgers up to the scan):
  if the model issues strong-or-weak on > 80% of shorts (min 5 shorts), weak signals do not count (only strong);
  if even strong alone is > 80% of shorts, the model gets no warnings at all (it does not discriminate).
OUTCOME (no lookahead): entry = first session after the scan date (stocks; crypto = next UTC day), entry price = that open.
  excess_dir_dk = sgn*(close_k/open - 1) - sgn*(bench close_k/bench open - 1), sgn = -1, bench SPY (BTC-USD for crypto).
  Uses d20 if its close is before the current scan cutoff date, else d5 if known, else the setup is not counted yet.
  A warning is CORRECT if excess_dir < 0 (the short lost vs the benchmark).
CREDIBILITY: shrunk = (hits + 15) / (n + 30)  (Beta(15,15) prior, strength 30); weight = max(0, shrunk - 0.5) * 2.
  penalty per warning model = PER_MODEL_CAP (10) * weight; total per short capped at TOTAL_CAP (20). Never a bonus.
Counts persist in scan-runs/model_short_cred.json (state branch) and are recomputed on every weekly run."""
import os, re, json, math
import numpy as np, pandas as pd
ROOT = os.environ.get('SCANNER_ROOT', '/workspace')
MODELS = ('gpt', 'grok', 'pplx', 'claude', 'jev')
PRIOR = 15.0; PER_MODEL_CAP = 10.0; TOTAL_CAP = 20.0; NONDISC_SHARE = 0.80; MIN_SHORTS = 5
STATE = f'{ROOT}/scan-runs/model_short_cred.json'
VERSION = 'v3-shortveto-cred (2026-10-16)'

def _num(v):
    try: v = float(v); return v if math.isfinite(v) else None
    except Exception:
        m = re.search(r'([+-]?\d+(?:\.\d+)?)\)?\s*$', str(v)); return float(m.group(1)) if m else None

def signal(model, verdict=None, conviction=None, direction_view=None, jev=None):
    """-> 'strong' | 'weak' | None for one model's output on a SHORT."""
    v = str(verdict or '').strip().lower()
    if model in ('gpt', 'grok', 'pplx'): return 'strong' if v == 'veto' else ('weak' if v == 'flag' else None)
    if model == 'claude':
        c = _num(conviction)
        return 'strong' if (str(direction_view or v).lower() == 'opposes' or (c is not None and c <= 40)) else None
    if model == 'jev':
        s = _num(jev if jev is not None else verdict); return 'strong' if (s is not None and s >= 0.25) else None
    return None

def ledger_shorts(paths=None, before=None):
    paths = paths or [f'{ROOT}/scan-runs/platform_verdicts_ledger.csv', f'{ROOT}/scan-runs/platform_verdicts_ledger_trial.csv']
    L = pd.concat([pd.read_csv(p) for p in paths if os.path.exists(p)], ignore_index=True) if any(os.path.exists(p) for p in paths) else pd.DataFrame()
    if L.empty: return L
    L = L[L.decision_point.astype(str).eq('entry') & L.direction.astype(str).str.upper().eq('SHORT')].copy()
    L['scan_date'] = pd.to_datetime(L.asof_local.astype(str).str[:10], errors='coerce')
    if before is not None: L = L[L.scan_date < pd.Timestamp(before).tz_localize(None).normalize() + pd.Timedelta(days=1)]
    L['sig'] = [signal(str(r.platform).lower(), r.verdict, r.conviction_or_sentiment, None, None) for r in L.itertuples()]
    L['key'] = L.ticker.astype(str) + '|' + L.scan_date.dt.strftime('%Y-%m-%d')
    return L.drop_duplicates(['key', 'platform'], keep='last')

def counted_levels(L, model):
    """discrimination rule -> set of signal levels that count for this model."""
    g = L[L.platform.astype(str).str.lower().eq(model)]; n = g.key.nunique()
    if n < MIN_SHORTS: return {'strong', 'weak'}, n, None, None
    sh_any = g.sig.notna().mean(); sh_strong = g.sig.eq('strong').mean()
    lv = {'strong', 'weak'} if sh_any <= NONDISC_SHARE else ({'strong'} if sh_strong <= NONDISC_SHARE else set())
    return lv, n, round(float(sh_any), 3), round(float(sh_strong), 3)

def _bars(sym, start):
    import yfinance as yf
    z = yf.download(sym, start=str(start.date()), interval='1d', auto_adjust=False, progress=False, threads=False)
    if isinstance(z.columns, pd.MultiIndex): z.columns = z.columns.get_level_values(0)
    z.index = pd.to_datetime(z.index).tz_localize(None); return z[['Open', 'Close']].dropna()

def outcome(ticker, asset, scan_date, cutoff, bars_fn=_bars):
    """direction-adjusted excess of the short (d20 if known before cutoff, else d5) -> (excess, horizon) or (None, None)."""
    sym = {'crypto': f'{ticker}-USD'}.get(asset, ticker); bsym = 'BTC-USD' if asset == 'crypto' else 'SPY'
    x = bars_fn(sym, scan_date); b = bars_fn(bsym, scan_date)
    cut_day = pd.Timestamp(cutoff).tz_localize(None).normalize() if pd.Timestamp(cutoff).tzinfo else pd.Timestamp(cutoff).normalize()
    x = x[(x.index > scan_date) & (x.index < cut_day)]; b = b[b.index.isin(x.index)]
    for k in (20, 5):
        if len(x) >= k and len(b) >= k:
            r = -(x.Close.iloc[k - 1] / x.Open.iloc[0] - 1); rb = -(b.Close.iloc[k - 1] / b.Open.iloc[0] - 1)
            return float(r - rb), k
    return None, None

def compute(cutoff, paths=None, bars_fn=_bars, save=True):
    L = ledger_shorts(paths, before=cutoff)
    out = {'version': VERSION, 'cutoff': str(cutoff), 'models': {}}
    if L.empty: return out
    oc = {}
    for key, g in L.groupby('key'):
        r = g.iloc[0]; oc[key] = outcome(r.ticker, str(r.asset), r.scan_date, cutoff, bars_fn)
    for m in MODELS:
        lv, n_sh, sh_any, sh_st = counted_levels(L, m)
        g = L[L.platform.astype(str).str.lower().eq(m) & L.sig.isin(lv)]
        res = [(k, oc[k]) for k in g.key if oc.get(k, (None,))[0] is not None]
        n = len(res); hits = sum(1 for _, (e, _h) in res if e < 0)
        shrunk = (hits + PRIOR) / (n + 2 * PRIOR); w = max(0.0, shrunk - 0.5) * 2
        out['models'][m] = {'n_shorts_seen': int(n_sh), 'share_any_warning': sh_any, 'share_strong': sh_st, 'levels_counted': sorted(lv),
                            'n': n, 'hits': hits, 'shrunk_hit': round(shrunk, 4), 'weight': round(w, 4), 'penalty_pts': round(PER_MODEL_CAP * w, 2),
                            'warnings': [{'key': k, 'excess_dir': round(e, 4), 'h': h, 'correct': e < 0} for k, (e, h) in res]}
    if save:
        os.makedirs(os.path.dirname(STATE), exist_ok=True); json.dump(out, open(STATE, 'w'), indent=1)
    return out

def penalty(cred, row):
    """row: platform outputs of ONE short (keys gpt_verdict, grok_verdict, pplx_verdict, claude_conviction, claude_direction_view,
    jev_news_sentiment). -> (points, [models])"""
    pts, who = 0.0, []
    for m in MODELS:
        c = (cred.get('models') or {}).get(m)
        if not c or not c.get('penalty_pts'): continue
        s = signal(m, row.get(f'{m}_verdict'), row.get('claude_conviction'), row.get('claude_direction_view'), row.get('jev_news_sentiment'))
        if s and s in c['levels_counted']: pts += c['penalty_pts']; who.append(m)
    return min(TOTAL_CAP, round(pts, 2)), who

def markdown(cred):
    rows = ['| מודל | אזהרות שנמדדו | צדקו | שיעור מכווץ | משקל | קנס לאזהרה | רמות שנספרות | % שורטים עם אזהרה |', '|---|---|---|---|---|---|---|---|']
    for m, c in (cred.get('models') or {}).items():
        rows.append(f"| {m} | {c['n']} | {c['hits']} | {c['shrunk_hit']:.3f} | {c['weight']:.3f} | -{c['penalty_pts']:.2f} | {','.join(c['levels_counted']) or 'אין (לא מבחין)'} | {c['share_any_warning']} |")
    return f"### אמינות המודלים באזהרות על שורטים ({VERSION})\n" + '\n'.join(rows) + '\n'
