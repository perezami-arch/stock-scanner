"""EXPERIMENTAL volume-wave / divergence columns for the scanner (08.10.2026, Ilan: "מתי גל נגמר ומתי מתחיל").
LOGGED ONLY - weight 0, never changes score/stops/targets - until the researcher's point-in-time FDR backtest.
Import-safe (pure functions, no I/O at import). Main entry: waves_columns(df, cutoff, asset, direction) -> dict
(same calling convention as scanner_geometry.geometry_columns; df = daily OHLCV, cut point-in-time with geometry.pit_cut).

POINT-IN-TIME / NO REPAINTING
  * Zigzag = scanner_stops/geometry 2xATR14 zigzag (iaf/sim_fib.py, exec'd unchanged, same as the Elliott count). A pivot exists
    only from its CONFIRMATION bar (confirm_idx <= last visible bar). Swings between confirmed pivots are final; the swing from the
    last confirmed pivot to the last bar is 'in progress' (its volume/price are realised data, its end is not known yet).
  * Classic Weis wave: close-based, reversal threshold WEIS_REV_PCT % from the running wave extreme close. A wave becomes final
    on the bar the reversal is reached; bars after the extreme are then attributed to the new wave (standard Weis), so the
    LAST wave is provisional. Everything uses only bars <= the last visible bar.
  * Indicator values at a pivot = values ON the pivot bar (computed from bars <= that bar); divergences use only the last two
    CONFIRMED pivots of a kind, so a divergence is known from the confirmation bar of the second pivot (stored in *_confirmed_at).

1. VOLUME WAVES (prefix wz_ = Elliott zigzag swings, ww_ = classic Weis waves). 'with' = waves in the view direction
   (up for LONG, down for SHORT), 'against' = the opposite waves.
   cum volume per wave; flags:
     *_exhaustion_with   : last completed with-wave made a new extreme beyond the previous with-wave's extreme on LESS cum volume
     *_exhaustion_against: same for against-waves (selling exhaustion in a LONG view = a with-wave may start)
     *_effort_result     : last completed wave: cum volume >= EFFORT_HI x median wave volume (last 10) and price move
                           <= RESULT_LO x median wave move -> big effort, small result (which side = *_effort_result_side)
     *_counter_gt_with   : the latest against-wave (in progress or last completed) cum volume > the last completed with-wave
                           (possible start of a wave against the view)
     *_with_gt_counter   : the in-progress with-wave cum volume already > the last completed against-wave (with-wave starting)
   wz_climax_*: volume > CLIMAX_X x mean volume of the 50 prior bars on a reversal bar: (a) the last confirmed pivot bar (+-1 bar),
                (b) the last bar if it is a 20-bar extreme closing in the opposite third of its range.
2. RSI14 (Wilder), CCI20 (iaf/prep.py cci, exec'd unchanged), Connors RSI 3/2/100 (pandas-ta 0.4.71b0 definition, the version
   the researcher's FDR test used: RSI3(close) + RSI2(sign(diff(close))) + percent-rank-100 of pct change, /3).
   Divergences vs the last two confirmed pivots of a kind (H for bearish, L for bullish); they enter the signals only while
   fresh (2nd pivot confirmed <= DIV_MAX_AGE bars ago):
     regular bearish: price higher high, indicator lower high   | regular bullish: price lower low, indicator higher low
     hidden bearish : price lower high, indicator higher high   | hidden bullish : price higher low, indicator lower low
   Elliott context (scanner_stops.elliott_counts/select_count in the view direction):
     W5 done + RSI at P5 weaker than at P3 -> 'w5 divergence vs w3' (classic end-of-impulse); W3 done -> is RSI at P3 the
     strongest of P1/P3 ('w3 RSI strongest', expected in a healthy impulse).
3. wave_end_signal  (the move IN the view direction may be ending) / wave_start_signal (a new wave IN the view direction may be
   starting). v2 (08.10 16:20): reasons are grouped into INDEPENDENT families (volume_exhaustion [zigzag or Weis], effort_result,
   wave_volume_dominance [zigzag or Weis], climax, momentum_divergence [RSI or CCI], elliott_context); *_n = number of families,
   *_signal = *_n >= 2. The old any-reason OR is kept as *_any / *_n_raw for comparison. Weight 0.
"""
import json, math, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

WEIS_REV_PCT = 3.0         # classic Weis reversal threshold, % of price (close-based); documented, not optimised (researcher may sweep)
DIV_MAX_AGE = 20           # a divergence feeds the signals only if its 2nd pivot was confirmed <= 20 bars ago (column always reported)
EFFORT_HI = 1.5; RESULT_LO = 0.67; CLIMAX_X = 2.5; CLIMAX_N = 50; MED_N = 10; MIN_BARS = 60

MIN_FAMILIES = 2           # v2 (08.10 16:20): a signal needs >= 2 INDEPENDENT flag families (the OR of all reasons fired on ~90%)
FAMILY_ORDER = ["volume_exhaustion", "effort_result", "wave_volume_dominance", "climax", "momentum_divergence", "elliott_context"]

def family(reason):
    """Map one reason string to its independent family (zigzag and Weis variants of one idea = one family; RSI and CCI = one)."""
    r = reason.lower()
    if "elliott" in r or r.startswith("w5 "): return "elliott_context"
    if "climax" in r: return "climax"
    if "divergence" in r: return "momentum_divergence"
    if "effort" in r: return "effort_result"
    if "exhaustion" in r: return "volume_exhaustion"
    if "volume >" in r: return "wave_volume_dominance"
    return "other"

def families(reasons):
    f = {family(r) for r in reasons}
    return [k for k in FAMILY_ORDER + ["other"] if k in f]

_mods = {}
def _m():
    if not _mods:
        import sys; sys.path.insert(0, "/workspace")
        import scanner_geometry as GEO
        try:
            import scanner_stops as ST
        except Exception:
            ST = None
        _mods.update(GEO=GEO, ST=ST)
    return _mods

def _r(v, n=4):
    try:
        v = float(v); return round(v, n) if np.isfinite(v) else None
    except Exception: return None

# ------------------------------------------------------------------ indicators
def rsi_wilder(close, n=14):
    d = close.diff(); up = d.clip(lower=0); dn = (-d).clip(lower=0)
    au = up.ewm(alpha=1 / n, adjust=False).mean(); ad = dn.ewm(alpha=1 / n, adjust=False).mean()
    r = 100 * au / (au + ad); r.iloc[:n] = np.nan
    return r

def _rsi_pta(s, n):            # pandas-ta rsi (rma = ewm(alpha=1/n, adjust=False)), used inside Connors RSI
    d = s.diff(); p = d.clip(lower=0); q = d.clip(upper=0)
    pa = p.ewm(alpha=1 / n, adjust=False).mean(); qa = q.ewm(alpha=1 / n, adjust=False).mean()
    return 100 * pa / (pa + qa.abs())

def connors_rsi(close, rsi_n=3, streak_n=2, rank_n=100):
    """pandas-ta 0.4.71b0 crsi (talib off): streak = sign(diff(close)) (that version's 'consecutive_streak')."""
    c = close.astype(float)
    streak = pd.Series(np.r_[0.0, np.sign(np.diff(c.values))], index=c.index)
    pc = c.pct_change().values; pr = np.full(len(c), np.nan)
    if len(c) > rank_n:
        from numpy.lib.stride_tricks import sliding_window_view
        w = sliding_window_view(pc, rank_n + 1); pr[rank_n:] = 100 * np.nanmean(w[:, :-1] < w[:, -1][:, None], axis=1)
    return (_rsi_pta(c, rsi_n) + _rsi_pta(streak, streak_n) + pd.Series(pr, index=c.index)) / 3.0

def cci20(x):
    ST = _m()["ST"]
    if ST is not None and hasattr(ST, "cci"): return ST.cci(x)             # iaf/prep.py cci, exec'd unchanged by scanner_stops
    tp = (x.High + x.Low + x.Close) / 3; m = tp.rolling(20).mean()
    md = tp.rolling(20).apply(lambda a: np.mean(np.abs(a - a.mean())), raw=True); return (tp - m) / (0.015 * md)

# ------------------------------------------------------------------ waves
def zigzag_swings(x, known):
    """Swings between consecutive CONFIRMED pivots + the in-progress swing to the last bar.
    Each: dict(dir=+1 up/-1 down, i0, i1, p0, p1, vol, bars, done, conf=confirm idx of the end pivot or None)."""
    v = x.Volume.values.astype(float); c = x.Close.values; out = []
    for a, b in zip(known[:-1], known[1:]):
        out.append(dict(dir=1 if b[0] == "H" else -1, i0=a[2], i1=b[2], p0=float(a[1]), p1=float(b[1]),
                        vol=float(v[a[2] + 1:b[2] + 1].sum()), bars=b[2] - a[2], done=True, conf=b[3]))
    if known:
        lp = known[-1]; j = len(x) - 1
        if j > lp[2]:
            out.append(dict(dir=-1 if lp[0] == "H" else 1, i0=lp[2], i1=j, p0=float(lp[1]), p1=float(c[j]),
                            vol=float(v[lp[2] + 1:].sum()), bars=j - lp[2], done=False, conf=None))
    return out

def weis_waves(x, rev_pct=WEIS_REV_PCT):
    """Classic Weis wave on closes: the wave flips when the close reverses >= rev_pct % from the wave's extreme close.
    Returns waves like zigzag_swings (prices = closes). The last wave is provisional (done=False)."""
    c = x.Close.values.astype(float); v = x.Volume.values.astype(float); n = len(c)
    if n < 3: return []
    waves = []; d = 0; start = 0; ext_i = 0
    for i in range(1, n):
        if d == 0:
            if abs(c[i] / c[start] - 1) * 100 >= rev_pct: d = 1 if c[i] > c[start] else -1; ext_i = i
            elif (c[i] > c[ext_i]) if c[i] > c[start] else (c[i] < c[ext_i]): ext_i = i
            continue
        if (d == 1 and c[i] >= c[ext_i]) or (d == -1 and c[i] <= c[ext_i]): ext_i = i; continue
        if d * (c[ext_i] - c[i]) / c[ext_i] * 100 >= rev_pct:              # reversal confirmed on bar i
            waves.append(dict(dir=d, i0=start, i1=ext_i, p0=c[start], p1=c[ext_i], vol=float(v[start + 1:ext_i + 1].sum()),
                              bars=ext_i - start, done=True, conf=i))
            start = ext_i; d = -d; ext_i = i
    if d != 0:
        waves.append(dict(dir=d, i0=start, i1=n - 1, p0=c[start], p1=c[n - 1], vol=float(v[start + 1:].sum()), bars=n - 1 - start,
                          done=False, conf=None, ext_i=ext_i))
    return waves

def _wave_flags(waves, sgn, pre, x):
    r = {}; done = [w for w in waves if w["done"]]
    if not waves: r[f"{pre}_flag"] = "no waves"; return r
    W = [w for w in done if w["dir"] == sgn]; Ag = [w for w in done if w["dir"] == -sgn]
    cur = waves[-1]
    r[f"{pre}_n_waves"] = len(waves)
    r[f"{pre}_cur_dir"] = "with" if cur["dir"] == sgn else "against"
    r[f"{pre}_cur_vol"] = _r(cur["vol"], 0); r[f"{pre}_cur_bars"] = int(cur["bars"]); r[f"{pre}_cur_done"] = bool(cur["done"])
    if W: r[f"{pre}_last_with_vol"] = _r(W[-1]["vol"], 0); r[f"{pre}_last_with_end"] = str(x.index[W[-1]["i1"]].date())
    if Ag: r[f"{pre}_last_against_vol"] = _r(Ag[-1]["vol"], 0); r[f"{pre}_last_against_end"] = str(x.index[Ag[-1]["i1"]].date())
    def exh(L):
        if len(L) < 2: return None
        a, b = L[-2], L[-1]
        return bool(sgn * (b["p1"] - a["p1"]) * L[-1]["dir"] * sgn > 0 and b["vol"] < a["vol"])
    r[f"{pre}_exhaustion_with"] = exh(W)
    r[f"{pre}_exhaustion_against"] = exh(Ag)
    if len(W) >= 2: r[f"{pre}_with_vol_ratio"] = _r(W[-1]["vol"] / W[-2]["vol"], 3) if W[-2]["vol"] else None
    if len(Ag) >= 2: r[f"{pre}_against_vol_ratio"] = _r(Ag[-1]["vol"] / Ag[-2]["vol"], 3) if Ag[-2]["vol"] else None
    if len(done) >= 4:
        med_v = np.median([w["vol"] for w in done[-MED_N:]]); med_m = np.median([abs(w["p1"] - w["p0"]) for w in done[-MED_N:]])
        lw = done[-1]; ef = lw["vol"] / med_v if med_v else np.nan; rs = abs(lw["p1"] - lw["p0"]) / med_m if med_m else np.nan
        r[f"{pre}_last_effort_x"] = _r(ef, 2); r[f"{pre}_last_result_x"] = _r(rs, 2)
        r[f"{pre}_effort_result"] = bool(np.isfinite(ef) and np.isfinite(rs) and ef >= EFFORT_HI and rs <= RESULT_LO)
        r[f"{pre}_effort_result_side"] = ("with" if lw["dir"] == sgn else "against") if r[f"{pre}_effort_result"] else None
    ag_latest = cur if cur["dir"] == -sgn else (Ag[-1] if Ag else None)
    r[f"{pre}_counter_gt_with"] = bool(ag_latest is not None and W and ag_latest["vol"] > W[-1]["vol"] and
                                       (ag_latest is cur or ag_latest["i0"] >= W[-1]["i1"]))
    r[f"{pre}_with_gt_counter"] = bool(cur["dir"] == sgn and not cur["done"] and Ag and cur["vol"] > Ag[-1]["vol"])
    return r

# ------------------------------------------------------------------ divergences
def _div(known, ind, kind, sgn_name):
    """Regular/hidden divergence on the last two confirmed pivots of `kind` ('H' bearish side, 'L' bullish side)."""
    P = [p for p in known if p[0] == kind]
    if len(P) < 2: return None
    a, b = P[-2], P[-1]; ia, ib = ind[a[2]], ind[b[2]]
    if not (np.isfinite(ia) and np.isfinite(ib)): return None
    d = dict(p1=float(a[1]), p2=float(b[1]), i1=a[2], i2=b[2], v1=float(ia), v2=float(ib), conf=b[3], type=None)
    if kind == "H":
        if b[1] > a[1] and ib < ia: d["type"] = "regular_bearish"
        elif b[1] < a[1] and ib > ia: d["type"] = "hidden_bearish"
    else:
        if b[1] < a[1] and ib > ia: d["type"] = "regular_bullish"
        elif b[1] > a[1] and ib < ia: d["type"] = "hidden_bullish"
    return d

def indicator_frame(x):
    return pd.DataFrame({"rsi14": rsi_wilder(x.Close, 14), "cci20": cci20(x), "crsi": connors_rsi(x.Close)}, index=x.index)

# ------------------------------------------------------------------ main
def waves_analysis(df, cutoff=None, asset="stock", direction="LONG", rev_pct=WEIS_REV_PCT):
    """Full objects (for charts) + the columns. Returns dict(x, known, wz, ww, ind, divs, best, cols)."""
    GEO = _m()["GEO"]; ST = _m()["ST"]
    x = GEO.pit_cut(df, cutoff, asset); sgn = 1 if direction.upper() == "LONG" else -1
    cols = {"wv_last_bar": str(x.index[-1].date()) if len(x) else None, "wv_direction_view": direction.upper(), "wv_bars": int(len(x))}
    if len(x) < MIN_BARS:
        cols["wv_flag"] = f"history too short (<{MIN_BARS} bars)"; return dict(x=x, cols=cols)
    h, l, c = x.High.values, x.Low.values, x.Close.values
    a = GEO.atr14(h, l, c)
    known = [p for p in GEO.zigzag(h, l, a, GEO.ZZ) if p[3] <= len(h) - 1]
    wz = zigzag_swings(x, known); ww = weis_waves(x, rev_pct)
    cols.update(_wave_flags(wz, sgn, "wz", x)); cols.update(_wave_flags(ww, sgn, "ww", x)); cols["ww_rev_pct"] = rev_pct
    # climax
    v = x.Volume.values.astype(float); av50 = pd.Series(v).shift(1).rolling(CLIMAX_N).mean().values; j = len(x) - 1
    cp = None
    if known:
        lp = known[-1]
        for k in (lp[2] - 1, lp[2], lp[2] + 1):
            if 0 <= k <= j and np.isfinite(av50[k]) and av50[k] > 0 and v[k] / av50[k] > CLIMAX_X:
                cp = dict(kind=lp[0], idx=k, x=v[k] / av50[k]); break
    cols["wz_climax_pivot"] = None if cp is None else ("buying climax at swing high" if cp["kind"] == "H" else "selling climax at swing low")
    cols["wz_climax_pivot_x"] = _r(cp["x"], 2) if cp else None
    cols["wz_climax_pivot_date"] = str(x.index[cp["idx"]].date()) if cp else None
    cols["wz_climax_pivot_confirmed_at"] = str(x.index[known[-1][3]].date()) if cp else None
    lb = None
    if np.isfinite(av50[j]) and av50[j] > 0 and v[j] / av50[j] > CLIMAX_X:
        rng = h[j] - l[j] or 1e-9; loc = (c[j] - l[j]) / rng
        if h[j] >= h[max(0, j - 19):j + 1].max() and loc <= 1 / 3: lb = "buying climax (20-bar high, close in lower third)"
        elif l[j] <= l[max(0, j - 19):j + 1].min() and loc >= 2 / 3: lb = "selling climax (20-bar low, close in upper third)"
    cols["wz_climax_last_bar"] = lb; cols["wz_last_vol_x50"] = _r(v[j] / av50[j], 2) if np.isfinite(av50[j]) and av50[j] else None
    # indicators + divergences
    ind = indicator_frame(x)
    for k in ("rsi14", "cci20", "crsi"): cols[k] = _r(ind[k].iloc[-1], 2)
    divs = {}
    for nm in ("rsi14", "cci20"):
        arr = ind[nm].values
        for kind in ("H", "L"):
            d = _div(known, arr, kind, nm); divs[(nm, kind)] = d
            side = "bear" if kind == "H" else "bull"
            cols[f"div_{nm}_{side}"] = d["type"] if d else None
            cols[f"div_{nm}_{side}_confirmed_at"] = str(x.index[d["conf"]].date()) if d and d["type"] else None
            cols[f"div_{nm}_{side}_age_bars"] = int(j - d["conf"]) if d and d["type"] else None
    # Elliott context (view direction)
    best = None
    if ST is not None:
        best = ST.select_count(ST.elliott_counts(known, sgn))
    rs = ind["rsi14"].values; ctx = []
    if best:
        P = best["pivots"]; cols["wv_elliott_label"] = best["label"]
        if best["n"] == 6:
            r3, r5 = rs[P[3][2]], rs[P[5][2]]
            if np.isfinite(r3) and np.isfinite(r5) and sgn * (r5 - r3) < 0: ctx.append("w5 RSI divergence vs w3 (end of impulse)")
        if best["n"] >= 4:
            r1, r3 = rs[P[1][2]], rs[P[3][2]]
            if np.isfinite(r1) and np.isfinite(r3): cols["wv_w3_rsi_strongest"] = bool(sgn * (r3 - r1) > 0)
    cols["wv_elliott_context"] = "; ".join(ctx) if ctx else None
    # ---- signals (view direction)
    end, start = [], []
    for pre, nm in (("wz", "zigzag"), ("ww", "Weis")):
        if cols.get(f"{pre}_exhaustion_with"): end.append(f"{nm}: new extreme on lower volume (with-wave exhaustion)")
        if cols.get(f"{pre}_exhaustion_against"): start.append(f"{nm}: against-wave exhaustion (lower volume on new extreme)")
        if cols.get(f"{pre}_effort_result"):
            (end if cols.get(f"{pre}_effort_result_side") == "with" else start).append(f"{nm}: effort>result on last {cols.get(f'{pre}_effort_result_side')}-wave")
        if cols.get(f"{pre}_counter_gt_with"): end.append(f"{nm}: against-wave volume > last with-wave")
        if cols.get(f"{pre}_with_gt_counter"): start.append(f"{nm}: in-progress with-wave volume > last against-wave")
    if cp:
        if (cp["kind"] == "H") == (sgn == 1): end.append(cols["wz_climax_pivot"])
        else: start.append(cols["wz_climax_pivot"])
    if lb:
        if lb.startswith("buying") == (sgn == 1): end.append("last bar " + lb)
        else: start.append("last bar " + lb)
    against_side, with_side = ("bear", "bull") if sgn == 1 else ("bull", "bear")
    for nm in ("rsi14", "cci20"):
        da, dw = cols.get(f"div_{nm}_{against_side}"), cols.get(f"div_{nm}_{with_side}")
        fresh = lambda sd: (cols.get(f"div_{nm}_{sd}_age_bars") is not None and cols[f"div_{nm}_{sd}_age_bars"] <= DIV_MAX_AGE)
        if da and fresh(against_side): end.append(f"{nm} {da} divergence")
        if dw and fresh(with_side): start.append(f"{nm} {dw} divergence")
    if ctx: end += ctx
    if best and best["n"] == 3: start.append("Elliott: W2 done (W3 may start)")
    fe_, fs_ = families(end), families(start)
    cols.update(wave_end_any=bool(end), wave_end_n_raw=len(end), wave_end_reasons="; ".join(end) or None,
                wave_start_any=bool(start), wave_start_n_raw=len(start), wave_start_reasons="; ".join(start) or None,
                wave_end_n=len(fe_), wave_end_families=",".join(fe_) or None, wave_end_signal=len(fe_) >= MIN_FAMILIES,
                wave_start_n=len(fs_), wave_start_families=",".join(fs_) or None, wave_start_signal=len(fs_) >= MIN_FAMILIES)
    return dict(x=x, known=known, wz=wz, ww=ww, ind=ind,
                divs=divs, best=best, cols=cols, sgn=sgn)

def waves_columns(df, cutoff=None, asset="stock", direction="LONG"):
    """One dict of EXPERIMENTAL columns for one ticker at one cutoff (logged only, weight 0)."""
    try:
        return waves_analysis(df, cutoff, asset, direction)["cols"]
    except Exception as e:
        return {"wv_flag": f"error {e.__class__.__name__}: {e}"}

TRACKER_KEYS = ["wave_end_signal", "wave_end_n", "wave_end_families", "wave_end_reasons", "wave_start_signal", "wave_start_n",
                "wave_start_families", "wave_start_reasons", "wave_end_any",
                "wz_exhaustion_with", "wz_exhaustion_against", "wz_effort_result", "wz_counter_gt_with", "wz_with_gt_counter",
                "ww_exhaustion_with", "ww_exhaustion_against", "ww_effort_result", "ww_counter_gt_with", "ww_with_gt_counter",
                "wz_climax_pivot", "wz_climax_last_bar", "rsi14", "cci20", "crsi", "div_rsi14_bear", "div_rsi14_bull",
                "div_cci20_bear", "div_cci20_bull", "wv_elliott_context", "wv_w3_rsi_strongest", "wv_last_bar"]
