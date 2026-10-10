"""Fib 'spiral' SHORT rule (Ilan, room "בניית מודל סורק לשוק ההון") — reusable, point-in-time-safe implementation.
Spec: /workspace/fib-spiral/RULE.md (frozen 2026-10-08 16:55 IDT). VERSION 1.0.

Main API
  fib_spiral_columns(df, cutoff=None, asset='crypto', direction='SHORT', fans='F9') -> dict of fs_* columns
      df: OHLC DataFrame (columns open/high/low/close, any case), index = bar time (ascending). cutoff: last bar the
      decision may use (timestamp or None = last bar). Only bars <= cutoff are read. LONG = the same rule on the
      price-mirrored series (A high, D lower low) — implemented, NOT backtested.
  find_events(df, asset, fans) -> list of event dicts over the whole history (used by the backtest; each event is the
      exact output fib_spiral_columns would give at its trigger bar — verified by the leak test).
"""
import math
import numpy as np, pandas as pd

VERSION = "1.0"
P = dict(
    zz_atr=3.0,                                   # zigzag reversal threshold (x ATR14)
    fib=(0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.414),
    fans=dict(F9=(8, 4, 3, 2, 1, 1/2, 1/3, 1/4, 1/8), F5=(1, 1/2, 1/3, 1/4, 1/8)),
    circles=(0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.618, 2.618, 3.618, 4.236),
    tzones=(0.382, 0.618, 1.0, 1.382, 1.618, 2.0, 2.382, 2.618),
    horizon=2.618,                                # x T bars (time-zone horizon / max hold)
    rej_lookback=5, stop_buf_atr=0.1, min_risk_atr=0.25,
    t2_tol_atr=0.25, t2_tol_bars=2, min_T=2,
)

def atr14(h, l, c):
    """Wilder ATR14 (same as scanner sim_fib.atr14)."""
    n = len(c); a = np.full(n, np.nan)
    if n < 15: return a
    pc = np.r_[np.nan, c[:-1]]; tr = np.nanmax(np.c_[h - l, np.abs(h - pc), np.abs(l - pc)], axis=1); tr[0] = h[0] - l[0]
    a[13] = tr[:14].mean()
    for i in range(14, n): a[i] = (a[i - 1] * 13 + tr[i]) / 14
    return a

def zigzag(h, l, a, z):
    """Confirmed pivots (kind, price, pivot_idx, confirm_idx) — identical algorithm to scanner sim_fib.zigzag (causal)."""
    piv = []; i0 = 14
    if len(h) <= i0 + 1: return piv
    d = 0; hi = h[i0]; hi_i = i0; lo = l[i0]; lo_i = i0
    for i in range(i0 + 1, len(h)):
        th = z * a[i]
        if d >= 0:
            if h[i] > hi: hi, hi_i = h[i], i
            if d == 0 and l[i] < lo: lo, lo_i = l[i], i
        if d <= 0:
            if l[i] < lo: lo, lo_i = l[i], i
            if d == 0 and h[i] > hi: hi, hi_i = h[i], i
        if d >= 0 and hi - l[i] >= th and hi_i < i and (d == 1 or hi_i > lo_i):
            piv.append(('H', hi, hi_i, i)); d = -1; lo, lo_i = l[i], i; continue
        if d <= 0 and h[i] - lo >= th and lo_i < i and (d == -1 or lo_i > hi_i):
            piv.append(('L', lo, lo_i, i)); d = 1; hi, hi_i = h[i], i; continue
    return piv

def _arrays(df, direction):
    x = df.rename(columns=str.lower)
    o, h, l, c = (x[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    if direction.upper() == "LONG":                     # mirror: a LONG setup is the SHORT rule on -price
        o, h, l, c = -o, -l, -h, -c
    return o, h, l, c

# ---------------------------------------------------------------- geometry
def geometry(A, D, bA, bD, fans):
    H = D - A; T = bD - bA; u = H / T
    return dict(A=A, D=D, bA=bA, bD=bD, H=H, T=T, u=u, R=math.hypot(T * u, H), fans=fans)

def fan_price(g, k, b): return g["D"] - k * g["u"] * (b - g["bD"])

def circle_low(g, c, b):
    """lower branch of circle c at (fractional) bar b; nan where the circle does not reach."""
    dx = (np.asarray(b, float) - g["bD"]) * g["u"]; r = c * g["R"]
    with np.errstate(invalid="ignore"):
        return np.where(np.abs(dx) <= r, g["D"] - np.sqrt(np.maximum(r * r - dx * dx, 0)), np.nan)

def candidates(g, entry, b_entry):
    """forward crossings of fan lines / circles with fib levels below entry, inside the time-zone horizon."""
    out = []; T = g["T"]; H = g["H"]; u = g["u"]; hor = g["bD"] + math.ceil(P["horizon"] * T)
    for f in P["fib"]:
        y = g["D"] - f * H
        if not y < entry: continue
        for k in g["fans"]:
            b = g["bD"] + f * T / k
            if b_entry < b <= hor: out.append((b, y, "fan", k, f))
        for c in P["circles"]:
            r = c * g["R"]
            if r >= f * H:
                b = g["bD"] + math.sqrt(r * r - (f * H) ** 2) / u
                if b_entry < b <= hor: out.append((b, y, "circle", c, f))
    return out

def t2_score(g, b, y, tol_p):
    tb = P["t2_tol_bars"]; grid = np.linspace(b - tb, b + tb, 21); s = 0
    s += sum(abs((g["D"] - f * g["H"]) - y) <= tol_p for f in P["fib"])
    for k in g["fans"]:
        v = fan_price(g, k, grid); s += bool(np.nanmin(np.abs(v - y)) <= tol_p)
    for c in P["circles"]:
        v = circle_low(g, c, grid)
        if np.isfinite(v).any(): s += bool(np.nanmin(np.abs(v - y)) <= tol_p)
    s += sum(abs(g["bD"] + z * g["T"] - b) <= tb for z in P["tzones"])
    return int(s)

def t2_scores(g, cand, tol_p):
    """vectorised T2 score for all candidates (same definition as t2_score)."""
    tb = P["t2_tol_bars"]; b = np.array([x[0] for x in cand], float); y = np.array([x[1] for x in cand], float)
    grid = b[:, None] + np.linspace(-tb, tb, 21)[None, :]
    lv = g["D"] - np.array(P["fib"]) * g["H"]
    s = (np.abs(lv[None, :] - y[:, None]) <= tol_p).sum(1)
    for k in g["fans"]:
        v = g["D"] - k * g["u"] * (grid - g["bD"]); s += (np.min(np.abs(v - y[:, None]), 1) <= tol_p)
    for c in P["circles"]:
        v = circle_low(g, c, grid); dv = np.abs(v - y[:, None]); dv = np.where(np.isfinite(dv), dv, np.inf)
        s += (dv.min(1) <= tol_p)
    tz = g["bD"] + np.array(P["tzones"]) * g["T"]
    s += (np.abs(tz[None, :] - b[:, None]) <= tb).sum(1)
    return s.astype(int)

def targets(g, entry, b_entry, atr_e):
    cand = candidates(g, entry, b_entry)
    res = {}
    if cand:
        t1 = sorted(cand, key=lambda x: (-x[1], x[0]))[0]
        res.update(t1=t1[1], t1_bar=t1[0], t1_src=f"{t1[2]}:{t1[3]:.4g}@fib{t1[4]}", t1_fib=t1[4], t1_fallback=False)
        tol = P["t2_tol_atr"] * atr_e
        scs = t2_scores(g, cand, tol)
        best = sorted(zip(scs.tolist(), cand), key=lambda z: (-z[0], -z[1][1], z[1][0]))[0]
        x = best[1]
        res.update(t2=x[1], t2_bar=x[0], t2_src=f"{x[2]}:{x[3]:.4g}@fib{x[4]}", t2_fib=x[4], t2_score=best[0], t2_fallback=False)
    else:
        y786 = g["D"] - 0.786 * g["H"]; y1 = g["A"]
        fb = y786 if y786 < entry else (y1 if y1 < entry else np.nan)
        for t in ("t1", "t2"):
            res.update({t: fb, f"{t}_bar": np.nan, f"{t}_src": "fallback", f"{t}_fib": (0.786 if fb == y786 else 1.0) if fb == fb else np.nan,
                        f"{t}_fallback": True})
        res["t2_score"] = 0
    y786 = g["D"] - 0.786 * g["H"]
    res["t786"] = y786 if y786 < entry else (g["A"] if g["A"] < entry else np.nan)
    return res

# ---------------------------------------------------------------- setup scan for one D
def _scan_D(piv, j, o, h, l, c, a, last, fans):
    """piv[j] is a high pivot D preceded by L,H,L. Walk the window up to bar `last` (inclusive). Returns
    (setup dict or None, trigger dict or None). PIT: reads bars <= last and pivots confirmed <= last only."""
    if j < 3: return None, None
    (kA, A, bA, cA), (kB, B, bB, cB), (kC, C, bC, cC), (kD, D, bD, cD) = piv[j - 3], piv[j - 2], piv[j - 1], piv[j]
    if not (kA == "L" and kB == "H" and kC == "L" and kD == "H"): return None, None
    if not (C > A and D > B) or bD - bA < P["min_T"] or cD > last: return None, None
    g = geometry(A, D, bA, bD, fans)
    nxt_conf = piv[j + 1][3] if j + 1 < len(piv) else 10 ** 12
    end = min(last, nxt_conf - 1, bD + math.ceil(P["horizon"] * g["T"]))
    setup = dict(g=g, B=B, bB=bB, C=C, bC=bC, conf_D=cD, state="waiting")
    for i in range(cD, end + 1):
        if c[i] > D: setup["state"] = "invalid_above_D"; return setup, None
        if c[i] <= A: setup["state"] = "broken_below_A"; return setup, None
        if i - 1 <= bD: continue
        hit = [k for k in fans if c[i - 1] >= fan_price(g, k, i - 1) and c[i] < fan_price(g, k, i)]
        if hit:
            entry = c[i]; lo = max(bD + 1, i - P["rej_lookback"] + 1); rb = lo + int(np.argmax(h[lo:i + 1]))
            stop = h[rb] + P["stop_buf_atr"] * a[i]
            if stop - entry < P["min_risk_atr"] * a[i]: stop = entry + P["min_risk_atr"] * a[i]
            trg = dict(bar=i, entry=entry, stop=stop, rej_bar=rb, lines=hit, atr=a[i], **targets(g, entry, i, a[i]))
            setup["state"] = "triggered"; return setup, trg
    if end < last: setup["state"] = "expired"
    return setup, None

def find_events(df, asset="crypto", fans="F9", direction="SHORT"):
    o, h, l, c = _arrays(df, direction); a = atr14(h, l, c); piv = zigzag(h, l, a, P["zz_atr"])
    fs = P["fans"][fans]; ev = []
    for j in range(3, len(piv)):
        if piv[j][0] != "H": continue
        s, t = _scan_D(piv, j, o, h, l, c, a, len(c) - 1, fs)
        if t: ev.append(_pack(df, s, t, direction))
    return ev, dict(atr=a, piv=piv, o=o, h=h, l=l, c=c)

def _pack(df, s, t, direction):
    g = s["g"]; sg = -1 if direction.upper() == "LONG" else 1; idx = df.index
    lv = {f: sg * (g["D"] - f * g["H"]) for f in P["fib"]}
    r = dict(fs_version=VERSION, fs_direction=direction.upper(), fs_A=sg * g["A"], fs_B=sg * s["B"], fs_C=sg * s["C"], fs_D=sg * g["D"],
             fs_A_time=idx[g["bA"]], fs_B_time=idx[s["bB"]], fs_C_time=idx[s["bC"]], fs_D_time=idx[g["bD"]],
             fs_D_conf_time=idx[s["conf_D"]], fs_T_bars=g["T"], fs_u=g["u"], fs_state=s["state"],
             fs_levels={f: round(v, 10) for f, v in lv.items()},
             fs_time_zones={z: g["bD"] + z * g["T"] for z in P["tzones"]})
    if t:
        r.update(fs_trigger_time=idx[t["bar"]], fs_bar=t["bar"], fs_entry=sg * t["entry"], fs_stop=sg * t["stop"], fs_rej_time=idx[t["rej_bar"]],
                 fs_lines=",".join(f"{k:.4g}" for k in t["lines"]), fs_atr=t["atr"],
                 fs_target_t1=sg * t["t1"], fs_t1_src=t["t1_src"], fs_t1_fib=t["t1_fib"], fs_t1_bar=t["t1_bar"], fs_t1_fallback=t["t1_fallback"],
                 fs_target_t2=sg * t["t2"], fs_t2_src=t["t2_src"], fs_t2_fib=t["t2_fib"], fs_t2_bar=t["t2_bar"], fs_t2_score=t["t2_score"],
                 fs_t2_fallback=t["t2_fallback"], fs_target_786=sg * t["t786"], fs_bD=g["bD"], fs_bA=g["bA"])
    return r

def fib_spiral_columns(df, cutoff=None, asset="crypto", direction="SHORT", fans="F9"):
    """Point-in-time columns at decision bar `cutoff` (inclusive). fs_trigger=True iff the entry trigger fires ON the
    cutoff bar (the scanner enters at that close). fs_state: none / waiting / triggered(earlier) / expired / invalid."""
    x = df if cutoff is None else df.loc[:cutoff]
    x = x.iloc[:]                                      # never read beyond cutoff
    o, h, l, c = _arrays(x, direction); a = atr14(h, l, c); piv = zigzag(h, l, a, P["zz_atr"]); last = len(c) - 1
    fs = P["fans"][fans]
    out = dict(fs_version=VERSION, fs_direction=direction.upper(), fs_asset=asset, fs_fans=fans, fs_trigger=False, fs_state="none")
    if last < 20: return out
    # the active structure = the latest confirmed high pivot (D) that forms an ABCD
    hs = [j for j in range(len(piv)) if piv[j][0] == "H"]
    for j in reversed(hs):
        s, t = _scan_D(piv, j, o, h, l, c, a, last, fs)
        if s is None: break                            # only the latest confirmed high pivot can be an active D
        r = _pack(x, s, t, direction); out.update(r)
        if t is not None:
            out["fs_trigger"] = bool(t["bar"] == last)
            if t["bar"] != last: out["fs_state"] = "triggered_earlier"
        break
    return out

# columns for the scanner tracker (all weight 0); dict-valued fs_levels / fs_time_zones are info only
TRACKER_KEYS = ["fs_version", "fs_state", "fs_trigger", "fs_A", "fs_B", "fs_C", "fs_D", "fs_D_time", "fs_D_conf_time", "fs_T_bars",
                "fs_entry", "fs_stop", "fs_lines", "fs_target_t1", "fs_t1_src", "fs_target_t2", "fs_t2_src", "fs_t2_score", "fs_target_786"]
