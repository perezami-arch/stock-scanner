"""Liquidity-sweep reversal detector (Ilan, intraday scanner, WEIGHT 0). Spec: /workspace/liq-sweep/RULE.md (frozen). VERSION 1.0.

API
  detect(df, asset='crypto', intraday=True) -> list of event dicts (both directions), causal / point-in-time.
  liq_sweep_columns(df, cutoff=None, asset='crypto', intraday=True) -> dict with TRACKER_KEYS: the sweep that is
      CONFIRMED ON the cutoff bar (E1 entry = that close; E2 = limit at the swept level for the next 5 bars), per direction.
  df: OHLCV DataFrame (open/high/low/close/volume, any case), DatetimeIndex ascending (UTC for crypto; PDH/PDL use UTC days).
"""
import math, numpy as np, pandas as pd
VERSION = "1.0"
P = dict(w=5, L=100, max_reclaim=3, vol_med=20, vol_spike=2.0, stop_buf_atr=0.1, min_risk_atr=0.25, e2_bars=5, maxhold=50,
         fallback_R=2.0)
TRACKER_KEYS = [
    "ls_version", "ls_dir", "ls_sweep",                  # ls_sweep: True iff a sweep is confirmed on this bar (E1 trigger)
    "ls_level", "ls_level_kind", "ls_level_age_bars", "ls_pierce_time", "ls_reclaim_bars", "ls_wick",
    "ls_entry_e1", "ls_e2_limit", "ls_e2_valid_bars", "ls_stop", "ls_risk_pct", "ls_target", "ls_target_kind", "ls_rr",
    "ls_vol_ratio", "ls_vol_spike", "ls_atr14",
    "ls_long_sweep", "ls_short_sweep",                   # both flags always present (a bar can sweep both sides)
]

def atr14(h, l, c):
    n = len(c); a = np.full(n, np.nan)
    if n < 15: return a
    pc = np.r_[np.nan, c[:-1]]; tr = np.nanmax(np.c_[h - l, np.abs(h - pc), np.abs(l - pc)], axis=1); tr[0] = h[0] - l[0]
    a[13] = tr[:14].mean()
    for i in range(14, n): a[i] = (a[i - 1] * 13 + tr[i]) / 14
    return a

def _frame(df):
    x = df.rename(columns=str.lower)
    o, h, l, c = (x[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    v = x["volume"].to_numpy(float) if "volume" in x else np.full(len(c), np.nan)
    idx = pd.DatetimeIndex(df.index)
    day = (idx.as_unit("ms").asi8 // 86400000) if len(idx) else np.array([], "int64")
    return o, h, l, c, v, np.asarray(day)

def _detect_short(o, h, l, c, v, atr, day, use_pd):
    """SHORT-frame sweeps of highs (the LONG side is this function on the mirrored series)."""
    w, L = P["w"], P["L"]; n = len(c); ev = []
    highs = []      # dicts: price, k, kind, s (pending start) ; active from conf bar + 1
    lows = []       # dicts: price, k, kind (target candidates), removed when traded through
    pdh = pdl = None
    for i in range(n):
        # (1) new day -> previous UTC day high/low become levels
        if use_pd and i > 0 and day[i] != day[i - 1]:
            j0 = i - 1
            while j0 > 0 and day[j0 - 1] == day[i - 1]: j0 -= 1
            highs = [x for x in highs if x["kind"] != "pdh"]; lows = [x for x in lows if x["kind"] != "pdl"]
            highs.append(dict(price=float(h[j0:i].max()), k=i, kind="pdh", s=None))
            lows.append(dict(price=float(l[j0:i].min()), k=i, kind="pdl"))
        # (2) sweeps of active highs (levels confirmed at <= i-1)
        rec = []
        keep = []
        for x in highs:
            if x["s"] is None:
                if x["kind"] != "pdh" and i - x["k"] > L: continue           # expired
                if h[i] > x["price"]: x["s"] = i
                else: keep.append(x); continue
            if c[i] < x["price"]: rec.append(x)                               # reclaimed -> event candidate, retired
            elif i - x["s"] >= P["max_reclaim"] - 1: pass                     # breakout -> retired
            else: keep.append(x)
        highs = keep
        # (3) lows traded through are no longer liquidity targets
        lows = [x for x in lows if l[i] >= x["price"] and (x["kind"] == "pdl" or i - x["k"] <= L)]
        # (4) event
        if rec and np.isfinite(atr[i]):
            lv = max(rec, key=lambda x: x["price"]); s = lv["s"]; X = float(h[s:i + 1].max()); entry = c[i]
            stop = X + P["stop_buf_atr"] * atr[i]
            if stop - entry < P["min_risk_atr"] * atr[i]: stop = entry + P["min_risk_atr"] * atr[i]
            med = np.nanmedian(v[max(0, s - P["vol_med"]):s]) if s > 0 else np.nan
            vr = float(np.nanmax(v[s:i + 1]) / med) if med and med > 0 and np.isfinite(med) else np.nan
            cand = [x for x in lows if x["price"] < entry]
            if cand:
                t = max(cand, key=lambda x: x["price"]); tgt, tk = t["price"], t["kind"]
            else:
                tgt = None
                for k in range(i, max(2, i - L + 2) - 1, -1):
                    if l[k] > h[k - 2] and l[k] < entry and (k == i or l[k + 1:i + 1].min() > l[k]):
                        tgt = l[k] if tgt is None else max(tgt, l[k])
                tk = "fvg"
                if tgt is None: tgt, tk = entry - P["fallback_R"] * (stop - entry), "fallback_2R"
            ev.append(dict(r=i, s=s, level=lv["price"], level_kind=lv["kind"], level_age=i - lv["k"], wick=X, entry=entry, stop=stop,
                           target=float(tgt), target_kind=tk, vol_ratio=vr, vol_spike=bool(vr > P["vol_spike"]) if vr == vr else False,
                           atr=float(atr[i]), reclaim_bars=i - s + 1))
        # (5) newly confirmed fractal pivots (bar k = i - w), active from i + 1
        k = i - w
        if k >= w:
            if h[k] > h[k - w:k].max() and h[k] > h[k + 1:i + 1].max(): highs.append(dict(price=float(h[k]), k=k, kind="pivot", s=None))
            if l[k] < l[k - w:k].min() and l[k] < l[k + 1:i + 1].min(): lows.append(dict(price=float(l[k]), k=k, kind="pivot"))
    return ev

def detect(df, asset="crypto", intraday=True):
    o, h, l, c, v, day = _frame(df); use_pd = bool(intraday)
    a = atr14(h, l, c)
    out = []
    for e in _detect_short(o, h, l, c, v, a, day, use_pd):
        e["dir"] = "SHORT"; out.append(e)
    am = atr14(-l, -h, -c)                                                   # identical to a (mirror-invariant)
    for e in _detect_short(-o, -l, -h, -c, v, am, day, use_pd):
        for kk in ("level", "wick", "entry", "stop", "target"): e[kk] = -e[kk]
        e["level_kind"] = {"pdh": "pdl", "pivot": "pivot"}[e["level_kind"]]
        e["target_kind"] = {"pdl": "pdh"}.get(e["target_kind"], e["target_kind"])
        e["dir"] = "LONG"; out.append(e)
    idx = df.index
    for e in out: e["time"] = idx[e["r"]]; e["pierce_time"] = idx[e["s"]]
    return sorted(out, key=lambda e: (e["r"], e["dir"]))

def _cols(e):
    risk = abs(e["stop"] - e["entry"])
    return dict(ls_dir=e["dir"], ls_sweep=True, ls_level=e["level"], ls_level_kind=e["level_kind"], ls_level_age_bars=e["level_age"],
                ls_pierce_time=e["pierce_time"], ls_reclaim_bars=e["reclaim_bars"], ls_wick=e["wick"], ls_entry_e1=e["entry"],
                ls_e2_limit=e["level"], ls_e2_valid_bars=P["e2_bars"], ls_stop=e["stop"], ls_risk_pct=risk / e["entry"],
                ls_target=e["target"], ls_target_kind=e["target_kind"], ls_rr=abs(e["entry"] - e["target"]) / risk if risk else np.nan,
                ls_vol_ratio=e["vol_ratio"], ls_vol_spike=e["vol_spike"], ls_atr14=e["atr"])

def liq_sweep_columns(df, cutoff=None, asset="crypto", intraday=True):
    """PIT columns at the cutoff bar. If both sides sweep on the same bar, the primary ls_* block is the side with the
    larger RR; both flags are reported."""
    x = df if cutoff is None else df.loc[:cutoff]
    out = {k: None for k in TRACKER_KEYS}; out.update(ls_version=VERSION, ls_sweep=False, ls_long_sweep=False, ls_short_sweep=False)
    if len(x) < 30: return out
    ev = [e for e in detect(x, asset, intraday) if e["r"] == len(x) - 1]
    if not ev: return out
    cols = [_cols(e) for e in ev]
    out["ls_long_sweep"] = any(e["dir"] == "LONG" for e in ev); out["ls_short_sweep"] = any(e["dir"] == "SHORT" for e in ev)
    out.update(max(cols, key=lambda z: (z["ls_rr"] if z["ls_rr"] == z["ls_rr"] else -1)))
    return out
