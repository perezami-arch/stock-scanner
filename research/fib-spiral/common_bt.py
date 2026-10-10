"""Shared backtest helpers (fib-spiral & liq-sweep): data loading, costs, exit simulation, clustered stats, BH-FDR."""
import json, os, glob, math, numpy as np, pandas as pd
from scipy import stats as SS
FD = '/workspace/fib-spiral/data'
UNI = json.load(open(f'{FD}/universe_crypto.json'))['symbols']
NONCRYPTO = set(json.load(open(f'{FD}/noncrypto.json')))
CRYPTO = [s for s in UNI if s not in NONCRYPTO]
RANK = {s: i + 1 for i, s in enumerate(UNI)}          # 24h-volume rank on 08.10 (frozen)

def slip_crypto(sym):
    r = RANK.get(sym, 999)
    return 0.0003 if r <= 20 else (0.0008 if r <= 60 else 0.0015)

def load_ohlcv(path):
    d = pd.read_parquet(path)
    if 'ts' in d.columns:
        d.index = pd.to_datetime(d.ts, unit='ms', utc=True); d['ts'] = d['ts'].astype('int64')
    else:
        d.index = pd.to_datetime(d.index).tz_localize('UTC') if d.index.tz is None else d.index
        d['ts'] = d.index.as_unit('ms').asi8.astype('int64')
    d = d[~d.index.duplicated()].sort_index()
    return d[['open', 'high', 'low', 'close', 'volume', 'ts']].dropna(subset=['open', 'high', 'low', 'close'])

_fund = {}
def funding(sym):
    if sym not in _fund:
        p = f'{FD}/funding/{sym}.parquet'
        if os.path.exists(p):
            f = pd.read_parquet(p).sort_values('ts'); _fund[sym] = (f.ts.to_numpy('int64'), np.cumsum(f.rate.to_numpy(float)))
        else: _fund[sym] = None
    return _fund[sym]

def funding_sum(sym, t0, t1):
    """sum of funding rates with timestamp in (t0, t1] (ms). The SHORT receives +sum."""
    f = funding(sym)
    if f is None or t1 <= t0: return 0.0
    ts, cs = f; a = np.searchsorted(ts, t0, 'right'); b = np.searchsorted(ts, t1, 'right')
    if b <= a: return 0.0
    return float(cs[b - 1] - (cs[a - 1] if a > 0 else 0.0))

def costs(asset, sym, side, t_entry, t_exit, fee_in=0.0005, fee_out=0.0005):
    """total cost as a fraction of entry notional (positive = cost); funding sign handled for side ('SHORT'/'LONG')."""
    if asset == 'crypto':
        s = slip_crypto(sym); fs = funding_sum(sym, t_entry, t_exit)
        fund = -fs if side == 'SHORT' else fs          # short receives positive funding -> negative cost
        return fee_in + fee_out + 2 * s + fund, fund
    days = max(0.0, (t_exit - t_entry) / 86400000.0)
    borrow = 0.01 * days / 365 if side == 'SHORT' else 0.0
    return 2 * 0.0005 + borrow, 0.0

def fractal_highs(h, w=2):
    n = len(h); f = np.zeros(n, bool)
    for k in range(w, n - w):
        if h[k] > h[k - w:k].max() and h[k] > h[k + 1:k + w + 1].max(): f[k] = True
    return f

def sim_short(o, h, l, c, atr, ts, bar_ms, i, entry, stop0, target, maxhold, trail, frac):
    """RULE.md §7. Returns (exit_idx, exit_px, kind, exit_time_ms, censored)."""
    n = len(c); stop = stop0; R = stop0 - entry; be = False; last_frac = None
    end = min(i + maxhold, n - 1)
    for j in range(i + 1, end + 1):
        if trail:
            k = j - 3                                   # fractal at k confirmed at close of k+2 = j-1
            if k > i and frac[k]: last_frac = k
            if be and last_frac is not None: stop = min(stop, h[last_frac] + 0.1 * atr[j - 1])
        if h[j] >= stop:
            gap = o[j] >= stop; px = o[j] if gap else stop
            return j, px, ('stop' if stop >= stop0 - 1e-12 else 'trail'), ts[j] + (0 if gap else bar_ms // 2), False
        if target is not None and target == target and l[j] <= target:
            gap = o[j] <= target; px = o[j] if gap else target
            return j, px, 'target', ts[j] + (0 if gap else bar_ms // 2), False
        if trail and not be and c[j] <= entry - R:
            be = True; stop = min(stop, entry)
        if j == i + maxhold: return j, c[j], 'time', ts[j] + bar_ms, False
    return end, c[end], 'censored', ts[end] + bar_ms, True

def sim_policy_short(o, h, l, c, atr, ts, bar_ms, i, entry, maxhold, asset):
    """baseline (a): crypto fixed stop entry + 3xATR on closes; stocks 4xATR chandelier on closes. No target."""
    n = len(c); end = min(i + maxhold, n - 1); stop = entry + 3 * atr[i]; mn = c[i]
    for j in range(i + 1, end + 1):
        if asset == 'stock':
            lvl = mn + 4 * atr[j - 1]
            if c[j] > lvl: return j, c[j], 'stop', ts[j] + bar_ms, False
            mn = min(mn, c[j])
        elif c[j] >= stop: return j, c[j], 'stop', ts[j] + bar_ms, False
        if j == i + maxhold: return j, c[j], 'time', ts[j] + bar_ms, False
    return end, c[end], 'censored', ts[end] + bar_ms, True

# ---------------------------------------------------------------- stats
def _cv(e, g):
    g = np.asarray(g); u = pd.Series(e).groupby(g).sum().values; G = len(u); n = len(e)
    return (G / max(G - 1, 1)) * (u @ u) / n ** 2, G

def cmean(y, sym, date):
    """mean with clustered SE by symbol, by date and two-way (CGM); p = max of the three (two-sided), like tool_stats."""
    y = np.asarray(y, float); m = np.isfinite(y); y = y[m]; sym = np.asarray(sym)[m]; date = np.asarray(date)[m]
    n = len(y)
    if n < 3: return dict(n=n, mean=np.nan, p=np.nan, lo=np.nan, hi=np.nan)
    mu = y.mean(); e = y - mu
    vs, Gs = _cv(e, sym); vd, Gd = _cv(e, date); vsd, _ = _cv(e, [f'{a}|{b}' for a, b in zip(sym, date)])
    v2 = vs + vd - vsd
    if v2 <= 0: v2 = max(vs, vd)
    ps = []
    for v, G in ((vs, Gs), (vd, Gd), (v2, min(Gs, Gd))):
        df = max(G - 1, 1); t = mu / math.sqrt(v) if v > 0 else np.inf; ps.append(2 * SS.t.sf(abs(t), df))
    df = max(min(Gs, Gd) - 1, 1); tc = SS.t.ppf(0.975, df); se = math.sqrt(v2)
    return dict(n=n, mean=mu, median=float(np.median(y)), p=max(ps), lo=mu - tc * se, hi=mu + tc * se, n_sym=Gs, n_dates=Gd)

def drop_top(y, sym, k):
    s = pd.Series(np.asarray(y, float)).groupby(np.asarray(sym)).sum().sort_values(ascending=False)
    keep = ~np.isin(np.asarray(sym), s.index[:k]); return float(np.nanmean(np.asarray(y, float)[keep])) if keep.any() else np.nan

def bh(p):
    p = np.asarray(p, float); q = np.full(len(p), np.nan); m = np.isfinite(p); pv = p[m]; n = len(pv)
    if n == 0: return q
    o = np.argsort(pv); r = pv[o] * n / (np.arange(n) + 1); r = np.minimum.accumulate(r[::-1])[::-1]
    qq = np.empty(n); qq[o] = np.minimum(r, 1); q[m] = qq; return q

def walk_forward(y, sym, date):
    d = pd.to_datetime(pd.Series(date)); med = d.quantile(0.5)
    a = d <= med; y = np.asarray(y, float)
    r1 = cmean(y[a.values], np.asarray(sym)[a.values], np.asarray(date)[a.values])
    r2 = cmean(y[~a.values], np.asarray(sym)[~a.values], np.asarray(date)[~a.values])
    return r1, r2, str(med.date())
