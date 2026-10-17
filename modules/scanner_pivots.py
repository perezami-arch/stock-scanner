"""Multi-timeframe / multi-degree pivot engine + Fibonacci/Gann confluence zones (EXPERIMENTAL, weight 0).
Built 16.10.2026 for Ilan (room "בניית מודל סורק לשוק ההון"): "חייב לחשב גם מרגליים עליונות".
Parameters are LOCKED in research/pivots/PREREG.md (PARAMS below must match it; a change = new VERSION, tested on new data only).

Point-in-time: every function takes an already-cut daily frame (scanner_geometry.pit_cut) and only uses pivots whose
CONFIRMATION bar is <= the last visible bar (zigzag never repaints a confirmed pivot). Weekly bars are built from the cut
daily frame; an unfinished last week is dropped.

API
    P = pivots(x)                 -> list of dict(kind,price,date,conf_date,degree,tf,size_atr)
    Z = confluence(x, direction)  -> dict with nearest zone above / below (+ all zones), legs that contributed
    cols = pivot_columns(df, cutoff, asset, direction) -> flat exp_piv_* dict (for research_columns)
"""
import os, sys, math, functools
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scanner_geometry as GEO

VERSION = "piv-2026-10-16.1"
PARAMS = dict(
    weekly_years=6, daily_bars=504,
    zz_weekly_intermediate=1.5, zz_weekly_major=3.0, zz_daily_minor=2.0,
    legs_per_degree=4, range_leg_years=5,
    retr=(0.382, 0.5, 0.618, 0.786), ext=(1.272, 1.618, 2.618), gann_eighths=tuple(range(1, 8)),
    weight={"major": 2.0, "intermediate": 2.0, "range5y": 2.0, "minor": 1.0},
    cluster_atr=0.35, pivot_overlap_atr=0.35, poc_bonus=1.0, pivot_bonus=0.5,
    min_strength=8.0, max_zone_atr=8.0, max_zone_width_atr=1.0,
)
NaN = float("nan")

def weekly_bars(x, asset="stock"):
    """W-FRI (stock) / W-SUN (crypto) bars from the cut daily frame; drop the last week if it is not finished."""
    rule = "W-FRI" if asset == "stock" else "W-SUN"
    w = x.resample(rule).agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}).dropna(subset=["Close"])
    if len(w) and len(x):
        last = x.index[-1]; wend = w.index[-1]
        done = (last.weekday() == (4 if asset == "stock" else 6)) or (asset == "stock" and (wend - last).days >= 1 and _no_more_sessions(last, wend))
        if not done: w = w.iloc[:-1]
    return w

def _no_more_sessions(last, wend):
    from pandas.tseries.holiday import USFederalHolidayCalendar
    from pandas.tseries.offsets import CustomBusinessDay
    nxt = last + CustomBusinessDay(n=1, calendar=USFederalHolidayCalendar())
    return nxt > wend

def _zz(fr, z, degree, tf):
    h, l, c = fr.High.values.astype(float), fr.Low.values.astype(float), fr.Close.values.astype(float)
    a = GEO.atr14(h, l, c)
    if len(c) < 20 or not np.isfinite(a[-1]): return []
    out, prev = [], None
    for k, p, i, conf in GEO.zigzag(h, l, a, z):
        if conf > len(h) - 1: continue
        u = a[conf] if np.isfinite(a[conf]) else a[-1]
        out.append(dict(kind=k, price=float(p), i=int(i), date=fr.index[i], conf_date=fr.index[conf], degree=degree, tf=tf,
                        size_atr=(abs(p - prev) / u) if prev is not None and u else NaN))
        prev = p
    return out

def pivots(x, asset="stock"):
    """All confirmed pivots, three degrees. x = cut daily frame (DatetimeIndex, OHLCV)."""
    P = PARAMS
    x = x[x.index >= x.index[-1] - pd.DateOffset(years=P["weekly_years"])] if len(x) else x
    w = weekly_bars(x, asset)
    d = x.iloc[-P["daily_bars"]:]
    return (_zz(w, P["zz_weekly_major"], "major", "W") + _zz(w, P["zz_weekly_intermediate"], "intermediate", "W")
            + _zz(d, P["zz_daily_minor"], "minor", "D")), w

def _legs(piv, x, w):
    """last N consecutive confirmed pivot pairs per degree + the 5y weekly high-low range leg."""
    P = PARAMS; legs = []
    for deg in ("major", "intermediate", "minor"):
        q = [p for p in piv if p["degree"] == deg]
        for a, b in list(zip(q[:-1], q[1:]))[-P["legs_per_degree"]:]:
            legs.append(dict(degree=deg, p0=a["price"], p1=b["price"], d0=a["date"], d1=b["date"]))
    if len(w) >= 20:
        ww = w[w.index >= w.index[-1] - pd.DateOffset(years=P["range_leg_years"])]
        ih, il = ww.High.values.argmax(), ww.Low.values.argmin()
        # range leg: only if both extremes are "confirmed" = not on the last 2 weekly bars
        if max(ih, il) <= len(ww) - 3:
            a, b = (il, ih) if il < ih else (ih, il)
            pa = ww.Low.values[a] if a == il else ww.High.values[a]; pb = ww.High.values[b] if b == ih else ww.Low.values[b]
            legs.append(dict(degree="range5y", p0=float(pa), p1=float(pb), d0=ww.index[a], d1=ww.index[b]))
    return legs

def _levels(leg):
    P = PARAMS; p0, p1 = leg["p0"], leg["p1"]; rng = p1 - p0; out = []
    for r in P["retr"]: out.append((p1 - r * rng, f"R{r}"))
    for e in P["ext"]: out.append((p0 + e * rng, f"E{e}"))
    lo, hi = min(p0, p1), max(p0, p1)
    for k in P["gann_eighths"]: out.append((lo + k / 8 * (hi - lo), f"G{k}/8"))
    return out

def confluence(x, direction="LONG", asset="stock"):
    """Cluster all projected levels; returns nearest significant zone above and below the last close."""
    P = PARAMS
    if len(x) < 60: return None
    h, l, c = x.High.values.astype(float), x.Low.values.astype(float), x.Close.values.astype(float)
    A = float(GEO.atr14(h, l, c)[-1]); px = float(c[-1])
    if not np.isfinite(A) or A <= 0: return None
    piv, w = pivots(x, asset)
    legs = _legs(piv, x, w)
    L = []
    for j, lg in enumerate(legs):
        for lv, tag in _levels(lg):
            if lv > 0 and abs(lv - px) <= P["max_zone_atr"] * 3 * A:
                L.append(dict(p=lv, w=P["weight"][lg["degree"]], tag=f"{lg['degree']}:{tag}", deg=lg["degree"]))
    if not L: return dict(A=A, px=px, zones=[], up=None, dn=None, piv=piv, legs=legs)
    L.sort(key=lambda r: r["p"])
    zones, cur = [], [L[0]]
    for r in L[1:]:
        if r["p"] - cur[-1]["p"] <= P["cluster_atr"] * A and r["p"] - cur[0]["p"] <= P["max_zone_width_atr"] * A: cur.append(r)
        else: zones.append(cur); cur = [r]
    zones.append(cur)
    # extras: VP120 POC + prior confirmed pivot prices (S/R) inside the zone
    try:
        tail = x.iloc[-120:]; vp = GEO.profile(tail.Low.values, tail.High.values, tail.Volume.values, close=tail.Close.values)
        poc = vp.get("poc") if isinstance(vp, dict) else None
    except Exception: poc = None
    pp = [p["price"] for p in piv]
    Z = []
    for g in zones:
        lo, hi = g[0]["p"], g[-1]["p"]; s = sum(r["w"] for r in g); tol = P["pivot_overlap_atr"] * A
        n_piv = sum(1 for q in pp if lo - tol <= q <= hi + tol); s += P["pivot_bonus"] * min(n_piv, 4)
        has_poc = poc is not None and lo - tol <= poc <= hi + tol; s += P["poc_bonus"] * has_poc
        degs = sorted({r["deg"] for r in g})
        Z.append(dict(lo=lo, hi=hi, mid=(lo + hi) / 2, strength=round(s, 2), n=len(g), weekly=any(d != "minor" for d in degs),
                      degrees=",".join(degs), legs=";".join(r["tag"] for r in g)[:400], poc=bool(has_poc), n_pivots=n_piv))
    sig = [z for z in Z if z["strength"] >= P["min_strength"]]
    up = min([z for z in sig if z["lo"] > px], key=lambda z: z["lo"] - px, default=None)
    dn = max([z for z in sig if z["hi"] < px], key=lambda z: z["hi"], default=None)
    inz = max([z for z in sig if z["lo"] - 0.1 * A <= px <= z["hi"] + 0.1 * A], key=lambda z: z["strength"], default=None)
    return dict(A=A, px=px, zones=Z, up=up, dn=dn, inside=inz, piv=piv, legs=legs, poc=poc)

COLS = ["up_lo", "up_hi", "up_strength", "up_dist_atr", "up_weekly", "up_legs", "dn_lo", "dn_hi", "dn_strength", "dn_dist_atr",
        "dn_weekly", "dn_legs", "in_zone_strength", "target_zone_dist_atr", "support_zone_dist_atr", "support_zone_strength",
        "n_major", "n_intermediate", "n_minor", "major_last_kind", "major_leg_size_atr", "n_zones_sig", "version"]

def pivot_columns(df, cutoff=None, asset="stock", direction="LONG"):
    """flat dict without prefix; research_columns adds exp_piv_. 'support' = zone behind the trade, 'target' = zone ahead."""
    x = GEO.pit_cut(df, cutoff, asset)
    Z = confluence(x, direction, asset)
    if Z is None: raise ValueError(f"history too short ({len(x)} bars)")
    r = {k: NaN for k in COLS}; r["version"] = VERSION; A = Z["A"]; px = Z["px"]
    for side in ("up", "dn"):
        z = Z.get(side)
        if z:
            r.update({f"{side}_lo": round(z["lo"], 4), f"{side}_hi": round(z["hi"], 4), f"{side}_strength": z["strength"],
                      f"{side}_dist_atr": round(((z["lo"] - px) if side == "up" else (px - z["hi"])) / A, 3),
                      f"{side}_weekly": z["weekly"], f"{side}_legs": z["legs"]})
    r["in_zone_strength"] = Z["inside"]["strength"] if Z.get("inside") else 0.0
    long_ = str(direction).upper() == "LONG"
    tgt, sup = ("up", "dn") if long_ else ("dn", "up")
    r["target_zone_dist_atr"] = r[f"{tgt}_dist_atr"]; r["support_zone_dist_atr"] = r[f"{sup}_dist_atr"]; r["support_zone_strength"] = r[f"{sup}_strength"]
    for deg in ("major", "intermediate", "minor"): r[f"n_{deg}"] = sum(1 for p in Z["piv"] if p["degree"] == deg)
    mj = [p for p in Z["piv"] if p["degree"] == "major"]
    if mj: r["major_last_kind"] = mj[-1]["kind"]; r["major_leg_size_atr"] = round(mj[-1]["size_atr"], 2) if np.isfinite(mj[-1]["size_atr"]) else NaN
    r["n_zones_sig"] = sum(1 for z in Z["zones"] if z["strength"] >= PARAMS["min_strength"])
    return r

def major_fib_lines(x, asset="stock"):
    """for chart overlay: [(price, label)] from the latest major weekly leg + 5y range leg (retracements + 1.618)."""
    piv, w = pivots(x, asset); out = []; legs = _legs(piv, x, w)
    for lg in [l for l in legs if l["degree"] == "range5y"] + [l for l in legs if l["degree"] == "major"][-1:]:
        for lv, tag in _levels(lg):
            if tag.startswith("R") or tag == "E1.618": out.append((round(lv, 4), f"{lg['degree']} {tag}"))
    return out
