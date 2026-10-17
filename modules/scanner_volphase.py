"""4-state volume phase (EXPERIMENTAL, weight 0). Parameters LOCKED in research/pivots/PREREG.md.
Per bar: direction = close vs previous close (tie -> close vs open; still tie -> previous direction);
relvol = V / mean(V of the 20 PREVIOUS bars).  up & relvol>1 -> BR (buyers, rising volume); up & <=1 -> BF (buyers fading);
down & >1 -> SR (sellers rising); down & <=1 -> SF (sellers fading).
Aggregates over 5/10/20 bars, OBV slope (20, z vs 60-bar diff std), CMF20; same on finished weekly bars.
Point-in-time: uses only the cut frame (scanner_geometry.pit_cut)."""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scanner_geometry as GEO

VERSION = "vph-2026-10-16.1"
STATES = ("BR", "BF", "SR", "SF")
WINDOWS = (5, 10, 20)
NaN = float("nan")

def states(x):
    c, o, v = x.Close.values.astype(float), x.Open.values.astype(float), np.nan_to_num(x.Volume.values.astype(float))
    n = len(c); up = np.zeros(n, bool)
    for i in range(n):
        d = c[i] - (c[i - 1] if i else o[i])
        if d == 0: d = c[i] - o[i]
        up[i] = d > 0 if d != 0 else (up[i - 1] if i else True)
    prev = pd.Series(v).shift(1).rolling(20, min_periods=20).mean().values
    rv = np.where(prev > 0, v / np.where(prev > 0, prev, 1), np.nan)
    hi = rv > 1
    st = np.where(up, np.where(hi, "BR", "BF"), np.where(hi, "SR", "SF")).astype(object)
    st[~np.isfinite(rv)] = None
    return pd.Series(st, index=x.index), pd.Series(rv, index=x.index), up

def cmf(x, n=20):
    h, l, c, v = (x[k].values.astype(float) for k in ("High", "Low", "Close", "Volume"))
    rng = h - l; mfm = np.where(rng > 0, ((c - l) - (h - c)) / np.where(rng > 0, rng, 1), 0.0)
    mfv = pd.Series(mfm * v); vs = pd.Series(v).rolling(n).sum()
    return (mfv.rolling(n).sum() / vs.replace(0, np.nan)).values

def obv_slope_z(x, n=20):
    c, v = x.Close.values.astype(float), np.nan_to_num(x.Volume.values.astype(float))
    ob = np.r_[0, np.cumsum(np.sign(np.diff(c)) * v[1:])]
    if len(ob) < max(n, 61): return NaN
    y = ob[-n:]; t = np.arange(n); sl = np.polyfit(t, y, 1)[0]; sd = np.nanstd(np.diff(ob[-61:]))
    return sl / sd if sd else NaN

def summarize(x, prefix=""):
    st, rv, up = states(x); r = {}
    s = st.dropna()
    r[f"{prefix}last"] = s.iloc[-1] if len(s) else None
    v = np.nan_to_num(x.Volume.values.astype(float))
    for w in WINDOWS:
        t = st.iloc[-w:]
        if t.isna().any() or len(t) < w:
            for k in STATES: r[f"{prefix}{k.lower()}_{w}"] = NaN
            r[f"{prefix}dom_{w}"] = None; r[f"{prefix}netvol_{w}"] = NaN; continue
        cnt = t.value_counts()
        for k in STATES: r[f"{prefix}{k.lower()}_{w}"] = round(cnt.get(k, 0) / w, 3)
        # dominant = most frequent; ties broken by volume share of that state
        vv = pd.Series(v[-w:], index=t.index).groupby(t.values).sum()
        r[f"{prefix}dom_{w}"] = max(STATES, key=lambda k: (cnt.get(k, 0), vv.get(k, 0)))
        uu = up[-w:]; tot = v[-w:].sum()
        r[f"{prefix}netvol_{w}"] = round((v[-w:][uu].sum() - v[-w:][~uu].sum()) / tot, 3) if tot else NaN
    cm = cmf(x); r[f"{prefix}cmf20"] = round(float(cm[-1]), 4) if len(cm) and np.isfinite(cm[-1]) else NaN
    oz = obv_slope_z(x); r[f"{prefix}obv_z20"] = round(float(oz), 3) if np.isfinite(oz) else NaN
    return r

def aligned(dom, direction):
    """+1 if the phase favours the trade (LONG: BR or SF ; SHORT: SR or BF), -1 if against, 0 unknown."""
    if dom is None or (isinstance(dom, float)): return 0
    long_ = str(direction).upper() == "LONG"
    good = ("BR", "SF") if long_ else ("SR", "BF")
    return 1 if dom in good else -1

def volphase_columns(df, cutoff=None, asset="stock", direction="LONG"):
    import scanner_pivots as PV
    x = GEO.pit_cut(df, cutoff, asset)
    if len(x) < 25: raise ValueError(f"history too short ({len(x)} bars)")
    r = summarize(x)
    w = PV.weekly_bars(x, asset)
    if len(w) >= 25: r.update(summarize(w, "w_"))
    r["dom10_aligned"] = aligned(r.get("dom_10"), direction)
    r["w_dom10_aligned"] = aligned(r.get("w_dom_10"), direction)
    sg = 1 if str(direction).upper() == "LONG" else -1
    r["cmf20_dir"] = r["cmf20"] * sg if np.isfinite(r.get("cmf20", NaN)) else NaN
    r["version"] = VERSION
    return r

COLS = (["last"] + [f"{k.lower()}_{w}" for w in WINDOWS for k in STATES] + [f"dom_{w}" for w in WINDOWS] + [f"netvol_{w}" for w in WINDOWS]
        + ["cmf20", "obv_z20"])
COLS = COLS + ["w_" + c for c in COLS] + ["dom10_aligned", "w_dom10_aligned", "cmf20_dir", "version"]
