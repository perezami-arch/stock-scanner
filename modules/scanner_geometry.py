"""EXPERIMENTAL geometry / volume / candle columns for the scanner (added 08.10.2026 at Ilan's request).
LOGGED ONLY - weight 0 in the score, never changes the active stops/targets - until backtested point-in-time
on the researcher's 846 setups.

Pure functions on a daily OHLCV DataFrame (columns Open/High/Low/Close/Volume, DatetimeIndex = bar date / bar start).
Every public function takes `cutoff` and FIRST cuts the frame point-in-time with pit_cut():
  * stock : bar D is visible only if D 16:00 America/New_York <= cutoff (alert before 16:00 ET -> previous close).
  * crypto: bar starting at t (UTC, tz-naive) is visible only if t + 24h <= cutoff (alert minute, or 00:00 UTC when
            only the date is known). Works for Yahoo UTC daily bars and for the researcher's pit.history 24h blocks.
  cutoff=None -> the frame is assumed to be already cut (e.g. scanner_stops.daily_bars output).

Swing anchor = EXACTLY the leg the existing Fib/Elliott code uses (scanner_stops.fib_elliott / half_at_1618):
  2xATR14 zigzag (iaf/sim_fib.py atr14 + zigzag, exec'd unchanged), only pivots CONFIRMED on/before the last visible bar;
  LONG view: end = last confirmed swing HIGH H1, origin = the pivot before it (L0). SHORT view mirrored (last LOW, prior HIGH).

1. FIBONACCI SPIRAL  (exp_spiral_*)
   Plane: x = bars (trading bars for stocks, days for crypto), y = price / u, u = Wilder ATR14 at the bar where H1 was
   CONFIRMED (fixed for the life of the swing, so the spiral does not wobble day to day) -> "1 bar = 1 ATR".
   Spirals are scale-dependent; this ATR normalisation is a convention (documented, not optimised).
   Center = leg end H1, start point = origin L0. Golden spiral r(theta) = r0 * phi^((theta-theta0)/(pi/2)), turning from L0
   through the retracement side (below H1 for LONG, mirrored for SHORT) into the future, 3 full turns.
   Nodes = quarter turns theta0 + k*pi/2. Outputs: arcs crossing the last visible bar (nearest above/below the close),
   distance to the nearest arc in current ATRs, near flag (<= 0.5 ATR), next node in the future (date, price, bars),
   next date the spiral crosses the current close level.
2. GANN BOX  (exp_gann_*)
   Box = origin pivot (i0,p0) -> end pivot (i1,p1), R = p1-p0, D = i1-i0 bars.
   Price levels p0 + R*(m+f): inside the box (m=0) f in {0,1/8..7/8,1/3,2/3}; the box repeated m=-2..+2 with the major
   divisions only (0,1/4,1/3,1/2,2/3,3/4) so tiny boxes do not create a level every few cents.
   Time divisions i0 + D*(m+f), box repeated forward; a fraction is used only if its step is >= 1 bar (eighths need
   D >= 8 bars, quarters D >= 4, thirds D >= 3, halves D >= 2); next division must be >= 1 bar after the last visible bar.
   Also the next whole-box multiple (exp_gann_next_box_date).
   Angles: swing-based scale s = |R|/D price per bar (the box diagonal = 1x1). From the origin in the leg direction and
   from the end pivot against it: 1x1 (s/bar), 1x2 (s/2 per bar = 1 price unit per 2 bars), 2x1 (2s/bar).
   Outputs: nearest box level and nearest angle above/below the close, next time division date, s/ATR ratio.
3. VOLUME PROFILE  (vp*_)
   Daily bars, each bar's volume spread uniformly over [Low, High] (overlap-weighted) into 50 equal price bins.
   Windows: last 60 bars (vp60), last 120 bars (vp120), from the swing origin L0 (vpanc). POC = max bin centre,
   value area 70% grown from the POC by adding the larger adjacent bin, HVN/LVN = local max/min of the [1,2,1]-smoothed
   profile with volume >= mean (HVN) / <= 0.6*mean (LVN); nearest to the close is reported. Distances in current ATR14.
   Optional vp20m: Alpaca 1-minute bars of the last 20 visible daily bars (stocks: regular session 09:30-16:00 ET,
   split-adjusted; crypto: 24h), volume at the typical price, 100 bins; ends at the end of the last visible daily bar.
4. CANDLES  (candle_*)
   body=|C-O|, rng=H-L, up=H-max(O,C), lo=min(O,C)-L, avg_body = mean body of the 10 prior bars.
   Context = 10-bar least-squares slope of Close ending on the bar BEFORE the pattern, x 9 bars / ATR14 (move in ATRs):
   downtrend <= -1.0, uptrend >= +1.0. Volume confirmation: V / mean(V of the 20 prior bars) >= 1.2.
   See CANDLE_RULES below for every rule. Own vectorised pandas (TA-Lib not installed / not used).
5. LIQUIDITY  (liq_*)   (added 08.10 13:55)
   Swing points = 3-bar fractals (High above the 3 bars on each side), confirmed 3 bars later, last 120 bars.
   Pools: UNTAKEN confirmed swing highs (taken = a later High exceeded it by > 0.25 ATR) above the close (buy-side, bsl) / lows below it (sell-side, ssl), clustered when
   adjacent levels are within 0.25 ATR14 (cluster span <= 0.5 ATR) = 'equal highs/lows'. Level = cluster extreme;
   touches, age (bars since the oldest swing), distance in ATR; nearest pool + strongest pool (most touches) within 5 ATR.
   vp_node/hvn flag: an HVN/LVN of the 60/120-bar daily profile within max(0.25 ATR, one bin) of the pool level.
   Standard levels: prior bar high/low (pdh/pdl), last complete week/month before the reference date (pwh/pwl, pmh/pml).
   Sweeps (last 3 bars): High above a pool known the bar before (or the prior bar high) and Close back below it ->
   bearish sweep; mirror for lows -> bullish sweep.
   FVG: bullish if Low[k] - High[k-2] >= 0.1 ATR (zone High[k-2]..Low[k]), bearish mirror; zone shrinks with partial fills,
   dropped when fully filled; nearest open gap above/below the close (last 120 bars).
   Order blocks: displacement bar with body >= 1.5 x ATR14 (prior bar) closing beyond the last confirmed swing high (bull)
   / low (bear) = break of structure; OB = last opposite-colour candle in the 5 bars before it (zone = its Low..High);
   unmitigated = price never traded back into the zone after the displacement; nearest above/below (last 250 bars).
CONFIRMATION DATES (for the backtest to enforce; every object exists only from the CLOSE of its confirmed_at bar):
   exp_anchor_origin/end_confirmed_at = bar on which the 2xATR zigzag confirmed each anchor pivot (spiral, Gann, anchored VP).
   pools: liq_*_first_confirmed_at = first swing of the cluster confirmed (fractal lag 3 bars), liq_*_equal_confirmed_at =
   SECOND swing confirmed (equal highs/lows exist from here), liq_*_confirmed_at = last member confirmed (current touch count).
   sweep = the closed sweep bar; FVG = close of the 3rd bar; order block = close of the displacement (BOS) bar;
   pd/pw/pm = close of the last bar of that day/week/month. All objects are built only from bars <= the last visible bar.
"""
import os, math, json, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

IAF = "/workspace/trading-frameworks-eval/iaf/"
try:                                                   # same atr14/zigzag the stops + Fib/Elliott code and backtest use
    _s = open(IAF + "sim_fib.py").read(); exec(_s[_s.index("def atr14"):_s.index("def clock")])
    ATR_SOURCE = "iaf/sim_fib.py (exec'd unchanged)"
except Exception:                                      # identical fallback copy so the module stays import-safe
    ATR_SOURCE = "vendored copy of iaf/sim_fib.py"
    def atr14(h, l, c):
        if len(c) < 15: return np.full(len(c), np.nan)
        pc = np.r_[np.nan, c[:-1]]; tr = np.nanmax(np.c_[h - l, np.abs(h - pc), np.abs(l - pc)], axis=1); tr[0] = h[0] - l[0]
        a = np.full(len(c), np.nan); a[13] = tr[:14].mean()
        for i in range(14, len(c)): a[i] = (a[i - 1] * 13 + tr[i]) / 14
        return a
    def zigzag(h, l, a, z):
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

ZZ = 2.0
PHI = (1 + 5 ** 0.5) / 2
NY = "America/New_York"
CACHE = "/workspace/scanner-geometry-cache"
SPIRAL_TURNS = 3; SPIRAL_STEPS_PER_QUARTER = 360; SPIRAL_NEAR_ATR = 0.5; SPIRAL_MAX_AHEAD = 400
GANN_FRACS = sorted(set([k / 8 for k in range(8)] + [1 / 3, 2 / 3]))
GANN_MAJOR = [0, 1 / 4, 1 / 3, 1 / 2, 2 / 3, 3 / 4]
GANN_ANGLES = (("1x1", 1.0), ("1x2", 0.5), ("2x1", 2.0))
VP_BINS = 50; VP_VA = 0.70; VP_WINDOWS = (60, 120); VP_MIN_BARS = 5
TREND_N = 10; TREND_ATR = 1.0; VOL_N = 20; VOL_CONFIRM = 1.2
CANDLE_RULES = {
 "doji": "body <= 0.10*rng",
 "dragonfly_doji": "doji & up <= 0.10*rng & lo >= 0.60*rng (bullish only after a downtrend)",
 "gravestone_doji": "doji & lo <= 0.10*rng & up >= 0.60*rng (bearish only after an uptrend)",
 "hammer": "0.10*rng < body <= 0.35*rng & lo >= 2*body & up <= 0.25*rng & downtrend",
 "hanging_man": "hammer shape & uptrend",
 "inverted_hammer": "0.10*rng < body <= 0.35*rng & up >= 2*body & lo <= 0.25*rng & downtrend",
 "shooting_star": "inverted-hammer shape & uptrend",
 "marubozu_bull / _bear": "body >= 0.90*rng & body >= avg_body, by colour",
 "spinning_top": "0.10*rng < body <= 0.30*rng & up >= body & lo >= body",
 "bullish_engulfing": "prev red, cur green, O <= prevC, C >= prevO, body > prev body, downtrend before",
 "bearish_engulfing": "mirror, uptrend before",
 "bullish_harami": "prev red & prev body >= avg_body, cur body inside prev body & <= 0.5*prev body, downtrend",
 "bearish_harami": "mirror, uptrend",
 "piercing": "prev red & prev body >= avg_body, cur green, O <= prevC, prevC + 0.5*prev body < C < prevO, downtrend",
 "dark_cloud": "prev green & prev body >= avg_body, cur red, O >= prevC, prevO < C < prevC - 0.5*prev body, uptrend",
 "morning_star": "bar-2 red & body >= avg_body, bar-1 body <= 0.5*avg_body, bar0 green & C > midpoint of bar-2 body, downtrend",
 "evening_star": "mirror, uptrend",
 "three_white_soldiers": "3 green, rising closes, each O inside prev body, each body >= 0.5*avg_body, up <= 0.35*rng",
 "three_black_crows": "mirror",
 "tweezer_bottom": "|L - prevL| <= 0.10*ATR14, prev red, cur green, downtrend",
 "tweezer_top": "|H - prevH| <= 0.10*ATR14, prev green, cur red, uptrend",
 "inside_bar": "H <= prevH & L >= prevL & (H < prevH | L > prevL)",
 "outside_bar": "H > prevH & L < prevL",
}
BULL = ["hammer", "inverted_hammer", "bullish_engulfing", "bullish_harami", "piercing", "morning_star",
        "three_white_soldiers", "tweezer_bottom", "marubozu_bull", "dragonfly_doji_down"]
BEAR = ["hanging_man", "shooting_star", "bearish_engulfing", "bearish_harami", "dark_cloud", "evening_star",
        "three_black_crows", "tweezer_top", "marubozu_bear", "gravestone_doji_up"]
NEUTRAL = ["doji", "dragonfly_doji", "gravestone_doji", "spinning_top", "inside_bar", "outside_bar"]
PATTERNS = BULL + BEAR + NEUTRAL

# ------------------------------------------------------------------ point-in-time
def _norm(df):
    x = df.rename(columns=str.title)[["Open", "High", "Low", "Close", "Volume"]].copy()
    idx = pd.DatetimeIndex(x.index)
    if idx.tz is not None: idx = idx.tz_convert("UTC").tz_localize(None)
    x.index = idx
    return x.dropna(subset=["Open", "High", "Low", "Close"]).sort_index()

def bar_end_utc(index, asset):
    """UTC moment each daily bar is complete (stock: 16:00 ET of D; crypto: bar start + 24h)."""
    idx = pd.DatetimeIndex(index)
    if asset == "stock":
        return (idx.normalize() + pd.Timedelta(hours=16)).tz_localize(NY).tz_convert("UTC")
    return (idx + pd.Timedelta(hours=24)).tz_localize("UTC")

def pit_cut(df, cutoff=None, asset="stock"):
    """Only bars complete at `cutoff` (tz-aware; tz-naive = UTC). cutoff=None -> frame returned as is (already cut)."""
    x = _norm(df)
    if cutoff is None: return x
    c = pd.Timestamp(cutoff); c = c.tz_localize("UTC") if c.tzinfo is None else c.tz_convert("UTC")
    return x[bar_end_utc(x.index, asset) <= c]

def _future_date(last, ahead, asset):
    ahead = int(math.ceil(ahead))
    if ahead <= 0: return str(pd.Timestamp(last).date())
    if asset == "crypto": return str((pd.Timestamp(last) + pd.Timedelta(days=ahead)).date())
    from pandas.tseries.holiday import USFederalHolidayCalendar
    from pandas.tseries.offsets import CustomBusinessDay
    return str((pd.Timestamp(last) + CustomBusinessDay(n=ahead, calendar=USFederalHolidayCalendar())).date())

def _r(v, n=4):
    return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), n)

def swing_anchor(x, direction="LONG"):
    """The leg scanner_stops.fib_elliott uses. Returns dict(i0,p0,i1,p1,conf1,atr,u) or None. x must already be cut."""
    h, l, c = x.High.values, x.Low.values, x.Close.values
    a = atr14(h, l, c)
    if not len(a) or not np.isfinite(a[-1]): return None
    known = [p for p in zigzag(h, l, a, ZZ) if p[3] <= len(h) - 1]           # confirmed on/before the last visible bar
    end_kind = "H" if direction.upper() == "LONG" else "L"
    idx = [j for j, p in enumerate(known) if p[0] == end_kind]
    if not idx or idx[-1] == 0: return None
    e, o = known[idx[-1]], known[idx[-1] - 1]
    return dict(i0=o[2], p0=float(o[1]), i1=e[2], p1=float(e[1]), conf1=e[3], conf0=o[3], atr=a, A=float(a[-1]),
                u=float(a[e[3]]) if np.isfinite(a[e[3]]) else float(a[-1]), sgn=1 if direction.upper() == "LONG" else -1)

# ------------------------------------------------------------------ 1. Fibonacci spiral
def fib_spiral(df, cutoff=None, asset="stock", direction="LONG", anchor=None):
    x = pit_cut(df, cutoff, asset); r = {}
    an = anchor or swing_anchor(x, direction)
    if an is None: return {"exp_spiral_flag": "no confirmed swing"}
    n = len(x) - 1; close = float(x.Close.iloc[-1]); A, u, sgn = an["A"], an["u"], an["sgn"]
    X0, Y0 = an["i0"] - an["i1"], sgn * (an["p0"] - an["p1"]) / u                 # mirrored so the sweep is always CCW
    r0, th0 = math.hypot(X0, Y0), math.atan2(Y0, X0)
    th = th0 + np.linspace(0, SPIRAL_TURNS * 2 * np.pi, SPIRAL_TURNS * 4 * SPIRAL_STEPS_PER_QUARTER + 1)
    rad = r0 * PHI ** ((th - th0) / (np.pi / 2))
    X = rad * np.cos(th); Y = rad * np.sin(th)
    P = an["p1"] + sgn * Y * u                                                    # back to price
    Xn = n - an["i1"]
    r.update(exp_spiral_center_date=str(x.index[an["i1"]].date()), exp_spiral_center_price=_r(an["p1"]),
             exp_spiral_start_date=str(x.index[an["i0"]].date()), exp_spiral_start_price=_r(an["p0"]),
             exp_spiral_unit_price_per_bar=_r(u), exp_spiral_r0_bars=_r(r0, 2))
    # arcs crossing the last visible bar
    s = np.sign(X - Xn); k = np.where(s[:-1] * s[1:] < 0)[0]
    arcs = [P[i] + (P[i + 1] - P[i]) * (Xn - X[i]) / (X[i + 1] - X[i]) for i in k]
    arcs = sorted(v for v in arcs if v > 0)
    ab = [v for v in arcs if v >= close]; be = [v for v in arcs if v < close]
    r["exp_spiral_arc_above"] = _r(min(ab)) if ab else None
    r["exp_spiral_arc_below"] = _r(max(be)) if be else None
    d = min([abs(v - close) for v in arcs], default=None)
    r["exp_spiral_arc_dist_atr"] = _r(d / A, 2) if d is not None else None
    r["exp_spiral_near_arc"] = bool(d is not None and d / A <= SPIRAL_NEAR_ATR)
    # next quarter-turn node in the future
    q = np.arange(1, SPIRAL_TURNS * 4 + 1); thq = th0 + q * np.pi / 2; rq = r0 * PHI ** q
    Xq = rq * np.cos(thq); Pq = an["p1"] + sgn * rq * np.sin(thq) * u
    fut = [(xq, pq, int(k_)) for xq, pq, k_ in zip(Xq, Pq, q) if xq > Xn + 1e-9 and pq > 0 and xq - Xn <= SPIRAL_MAX_AHEAD]
    if fut:
        xq, pq, k_ = min(fut)
        r.update(exp_spiral_next_node_date=_future_date(x.index[-1], xq - Xn, asset), exp_spiral_next_node_price=_r(pq),
                 exp_spiral_next_node_bars=int(math.ceil(xq - Xn)), exp_spiral_next_node_quarter=k_)
    # next time the spiral crosses the current close (future only)
    sp = np.sign(P - close); k = np.where((sp[:-1] * sp[1:] < 0))[0]
    xc = [X[i] + (X[i + 1] - X[i]) * (close - P[i]) / (P[i + 1] - P[i]) for i in k]
    xc = [v for v in xc if v > Xn and v - Xn <= SPIRAL_MAX_AHEAD]
    if xc:
        r["exp_spiral_next_cross_date"] = _future_date(x.index[-1], min(xc) - Xn, asset)
        r["exp_spiral_next_cross_bars"] = int(math.ceil(min(xc) - Xn))
    return r

# ------------------------------------------------------------------ 2. Gann box + angles
def _frac_label(f):
    for k in range(9):
        if abs(f - k / 8) < 1e-9: return f"{k}/8"
    return "1/3" if abs(f - 1 / 3) < 1e-9 else "2/3"

def _frac_step(f):
    """Granularity of the grid a fraction belongs to (1/8 for eighths not in quarters, etc.)."""
    for den in (2, 3, 4, 8):
        if abs(f * den - round(f * den)) < 1e-9: return 1 / den
    return 1 / 8

def gann_box(df, cutoff=None, asset="stock", direction="LONG", anchor=None):
    x = pit_cut(df, cutoff, asset); r = {}
    an = anchor or swing_anchor(x, direction)
    if an is None: return {"exp_gann_flag": "no confirmed swing"}
    n = len(x) - 1; close = float(x.Close.iloc[-1]); A, sgn = an["A"], an["sgn"]
    i0, p0, i1, p1 = an["i0"], an["p0"], an["i1"], an["p1"]; R = p1 - p0; D = i1 - i0
    if D <= 0 or R == 0: return {"exp_gann_flag": "degenerate swing"}
    lv = []
    for m in range(-2, 3):                                  # the box +/- 2 box heights; eighths inside the box, majors outside
        for f in (GANN_FRACS if m == 0 else GANN_MAJOR):
            v = p0 + R * (m + f); lab = ("box " if m == 0 else f"box{m:+d} ") + _frac_label(f)
            if v > 0: lv.append((v, lab))
    lv.append((p0 + 3 * R, "box+3 0/8")) if p0 + 3 * R > 0 else None
    ab = [t for t in lv if t[0] > close]; be = [t for t in lv if t[0] <= close]
    if ab: v, lab = min(ab); r.update(exp_gann_level_above=_r(v), exp_gann_level_above_lbl=lab, exp_gann_level_above_atr=_r((v - close) / A, 2))
    if be: v, lab = max(be); r.update(exp_gann_level_below=_r(v), exp_gann_level_below_lbl=lab, exp_gann_level_below_atr=_r((close - v) / A, 2))
    s = abs(R) / D
    ang = []
    for nm, m in GANN_ANGLES:
        ang.append((p0 + sgn * m * s * (n - i0), f"{nm} from origin {x.index[i0]:%d.%m.%y}"))
        ang.append((p1 - sgn * m * s * (n - i1), f"{nm} from end {x.index[i1]:%d.%m.%y}"))
    ang = [t for t in ang if t[0] > 0]
    ab = [t for t in ang if t[0] > close]; be = [t for t in ang if t[0] <= close]
    if ab: v, lab = min(ab); r.update(exp_gann_angle_above=_r(v), exp_gann_angle_above_lbl=lab)
    if be: v, lab = max(be); r.update(exp_gann_angle_below=_r(v), exp_gann_angle_below_lbl=lab)
    # time: a division is used only if its step is >= 1 bar (eighths need D >= 8, thirds D >= 3, quarters D >= 4, halves D >= 2)
    fr = [f for f in GANN_FRACS if (f == 0) or (D * _frac_step(f) >= 1)]
    tdiv = sorted((i0 + D * (m + f), f"{'box' if m == 0 else f'box+{m}'} {_frac_label(f)}") for m in range(0, 60) for f in fr)
    tdiv = [t for t in tdiv if t[0] >= n + 1]                 # at least one bar after the last visible bar
    if tdiv:
        t, lab = tdiv[0]
        r.update(exp_gann_next_time_date=_future_date(x.index[-1], t - n, asset), exp_gann_next_time_bars=int(math.ceil(t - n)), exp_gann_next_time_lbl=lab)
    m_ = math.floor((n - i0) / D) + 1; tb = i0 + D * m_
    tb = tb if tb >= n + 1 else tb + D
    r.update(exp_gann_next_box_date=_future_date(x.index[-1], tb - n, asset), exp_gann_next_box_bars=int(math.ceil(tb - n)))
    r.update(exp_gann_box_bars=int(D), exp_gann_box_range=_r(abs(R)), exp_gann_scale_per_bar=_r(s), exp_gann_scale_atr=_r(s / A, 3))
    # Research H3: asset clock from pivots already confirmed in this cut frame.
    # These are completed-bar counts, not calendar days or astronomical degrees.
    r.update(exp_gann_origin_age_bars=int(n - i0), exp_gann_end_age_bars=int(n - i1))
    return r

# ------------------------------------------------------------------ 3. volume profile
def profile(lo, hi, vol, bins=VP_BINS, close=None, price=None):
    """Overlap-weighted profile. lo/hi/vol arrays (price= typical price -> point mass). Returns dict or None."""
    lo = np.asarray(lo, float); hi = np.asarray(hi, float); vol = np.nan_to_num(np.asarray(vol, float))
    if price is not None: lo = hi = np.asarray(price, float)
    pmin, pmax = np.nanmin(lo), np.nanmax(hi)
    if not np.isfinite(pmin) or pmax <= pmin or vol.sum() <= 0: return None
    edges = np.linspace(pmin, pmax, bins + 1); ctr = (edges[:-1] + edges[1:]) / 2
    rng = hi - lo; v = np.zeros(bins)
    pt = rng <= 0
    if pt.any():
        b = np.clip(np.searchsorted(edges, lo[pt], side="right") - 1, 0, bins - 1); np.add.at(v, b, vol[pt])
    if (~pt).any():
        L, H, V, Rg = lo[~pt][:, None], hi[~pt][:, None], vol[~pt][:, None], rng[~pt][:, None]
        ov = np.clip(np.minimum(H, edges[1:][None, :]) - np.maximum(L, edges[:-1][None, :]), 0, None)
        v += (ov / Rg * V).sum(axis=0)
    poc = int(np.argmax(v)); tot = v.sum(); lo_i = hi_i = poc; acc = v[poc]
    while acc < VP_VA * tot and (lo_i > 0 or hi_i < bins - 1):
        up = v[hi_i + 1] if hi_i < bins - 1 else -1; dn = v[lo_i - 1] if lo_i > 0 else -1
        if up >= dn: hi_i += 1; acc += up
        else: lo_i -= 1; acc += dn
    sm = np.convolve(np.r_[v[0], v, v[-1]], [0.25, 0.5, 0.25], mode="valid"); mu = sm.mean()
    hvn = [ctr[i] for i in range(1, bins - 1) if sm[i] >= sm[i - 1] and sm[i] >= sm[i + 1] and sm[i] >= mu]
    lvn = [ctr[i] for i in range(1, bins - 1) if sm[i] <= sm[i - 1] and sm[i] <= sm[i + 1] and sm[i] <= 0.6 * mu]
    return dict(poc=ctr[poc], vah=edges[hi_i + 1], val=edges[lo_i], hvn=hvn, lvn=lvn, bin=edges[1] - edges[0])

def _vp_cols(pre, pr, close, A):
    if pr is None: return {f"{pre}_poc": None}
    pos = "above VA" if close > pr["vah"] else ("below VA" if close < pr["val"] else "inside VA")
    near = lambda L: min(L, key=lambda p: abs(p - close)) if L else None
    h, l = near(pr["hvn"]), near(pr["lvn"])
    return {f"{pre}_poc": _r(pr["poc"]), f"{pre}_vah": _r(pr["vah"]), f"{pre}_val": _r(pr["val"]),
            f"{pre}_poc_dist_atr": _r((close - pr["poc"]) / A, 2), f"{pre}_va_pos": pos,
            f"{pre}_hvn_near": _r(h), f"{pre}_hvn_dist_atr": _r((h - close) / A, 2) if h is not None else None,
            f"{pre}_lvn_near": _r(l), f"{pre}_lvn_dist_atr": _r((l - close) / A, 2) if l is not None else None}

def volume_profile(df, cutoff=None, asset="stock", direction="LONG", anchor=None, intraday=False, symbol=None):
    x = pit_cut(df, cutoff, asset)
    a = atr14(x.High.values, x.Low.values, x.Close.values)
    if not len(a) or not np.isfinite(a[-1]): return {"vp_flag": "history too short"}
    A = float(a[-1]); close = float(x.Close.iloc[-1]); r = {}
    for w in VP_WINDOWS:
        y = x.iloc[-w:]
        r.update(_vp_cols(f"vp{w}", profile(y.Low.values, y.High.values, y.Volume.values), close, A))
        if len(x) < w: r[f"vp{w}_flag"] = f"only {len(x)} bars"
    an = anchor or swing_anchor(x, direction)
    if an is not None and len(x) - an["i0"] >= VP_MIN_BARS:
        y = x.iloc[an["i0"]:]
        r.update(_vp_cols("vpanc", profile(y.Low.values, y.High.values, y.Volume.values), close, A))
        r["vpanc_from"] = str(x.index[an["i0"]].date())
    if intraday and symbol:
        try: r.update(intraday_profile(x, symbol, asset, A))
        except Exception as e: r["vp20m_flag"] = f"intraday failed: {e.__class__.__name__}"
    return r

def _alpaca_minutes(symbol, asset, start, end):
    """1-minute bars [start, end) from Alpaca (keys from env, never printed/stored). Cached per (symbol, start, end)."""
    import requests
    f = f"{CACHE}/alpaca_1min/{symbol.replace('/', '_')}/{start:%Y%m%dT%H%M}_{end:%Y%m%dT%H%M}.csv.gz"
    if os.path.exists(f): return pd.read_csv(f, parse_dates=["t"])
    kid, sec = os.environ.get("ALPACA_API_KEY_ID"), os.environ.get("ALPACA_API_SECRET_KEY")
    if not kid or not sec: raise RuntimeError("no alpaca keys")
    H = {"APCA-API-KEY-ID": kid, "APCA-API-SECRET-KEY": sec}
    if asset == "crypto":
        url = "https://data.alpaca.markets/v1beta3/crypto/us/bars"; sym = symbol.replace("-USD", "/USD")
        p = dict(symbols=sym, timeframe="1Min", start=start.isoformat(), end=end.isoformat(), limit=10000)
    else:
        url = "https://data.alpaca.markets/v2/stocks/bars"; sym = symbol
        p = dict(symbols=sym, timeframe="1Min", start=start.isoformat(), end=end.isoformat(), limit=10000, adjustment="split", feed="sip")
    out = []; tok = None
    for _ in range(30):
        if tok: p["page_token"] = tok
        q = requests.get(url, headers=H, params=p, timeout=30)
        if q.status_code == 403 and p.get("feed") == "sip": p["feed"] = "iex"; continue
        q.raise_for_status(); j = q.json()
        out += (j.get("bars") or {}).get(sym, []); tok = j.get("next_page_token")
        if not tok: break
    d = pd.DataFrame(out)
    if d.empty: raise RuntimeError("no minute bars")
    d = d.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})[["t", "open", "high", "low", "close", "volume"]]
    d["t"] = pd.to_datetime(d["t"], utc=True); d["feed"] = p.get("feed", "crypto-us")
    os.makedirs(os.path.dirname(f), exist_ok=True); d.to_csv(f, index=False)
    return d

def intraday_profile(x, symbol, asset, A, days=20):
    """vp20m_*: last `days` VISIBLE daily bars, minute volume at the typical price, 100 bins. Ends at the end of the last
    visible daily bar (so it never sees more than the daily frame)."""
    ends = bar_end_utc(x.index[-days:], asset)
    start = (ends[0] - pd.Timedelta(hours=24)) if asset == "crypto" else pd.Timestamp(x.index[-days]).tz_localize(NY).tz_convert("UTC")
    end = ends[-1]
    m = _alpaca_minutes(symbol, asset, start, end)
    m = m[(m["t"] >= start) & (m["t"] + pd.Timedelta(minutes=1) <= end)]
    if asset == "stock":
        tl = m["t"].dt.tz_convert(NY); mins = tl.dt.hour * 60 + tl.dt.minute
        m = m[(mins >= 570) & (mins < 960)]                                        # regular session only
    if len(m) < 100: return {"vp20m_flag": f"only {len(m)} minute bars"}
    tp = (m["high"] + m["low"] + m["close"]) / 3
    pr = profile(None, None, m["volume"].values, bins=100, price=tp.values)
    last = float(m["close"].iloc[-1])
    c = _vp_cols("vp20m", pr, last, A); c.update(vp20m_minutes=int(len(m)), vp20m_feed=str(m["feed"].iloc[0]) if "feed" in m else None,
                                             vp20m_last_px=_r(last))
    for k in ("vp20m_hvn_near", "vp20m_hvn_dist_atr", "vp20m_lvn_near", "vp20m_lvn_dist_atr"): c.pop(k, None)   # minute HVN/LVN too noisy
    return c

# ------------------------------------------------------------------ 4. candles
def candle_frame(df, cutoff=None, asset="stock"):
    """Vectorised pattern booleans for EVERY visible bar (pattern completes on that bar) + context columns."""
    x = pit_cut(df, cutoff, asset)
    O, H, L, C, V = (x[k].astype(float) for k in ("Open", "High", "Low", "Close", "Volume"))
    rng = (H - L).replace(0, np.nan); body = (C - O).abs(); up = H - np.maximum(O, C); lo = np.minimum(O, C) - L
    green, red = C > O, C < O
    A = pd.Series(atr14(H.values, L.values, C.values), index=x.index)
    avgb = body.shift(1).rolling(10).mean()
    # 10-bar least-squares slope of Close, in ATRs over the window
    t = pd.Series(np.arange(len(C), dtype=float), index=x.index)
    cov = (t * C).rolling(TREND_N).mean() - t.rolling(TREND_N).mean() * C.rolling(TREND_N).mean()
    var = t.rolling(TREND_N).var(ddof=0)
    tr = (cov / var) * (TREND_N - 1) / A
    tb = lambda k: tr.shift(k)                     # trend ending on the bar before a k-bar pattern
    dn = lambda k: tb(k) <= -TREND_ATR; upt = lambda k: tb(k) >= TREND_ATR
    pO, pH, pL, pC, pb = O.shift(1), H.shift(1), L.shift(1), C.shift(1), body.shift(1)
    pg, pr_ = green.shift(1, fill_value=False), red.shift(1, fill_value=False)
    f = pd.DataFrame(index=x.index)
    doji = body <= 0.10 * rng
    f["doji"] = doji
    f["dragonfly_doji"] = doji & (up <= 0.10 * rng) & (lo >= 0.60 * rng)
    f["gravestone_doji"] = doji & (lo <= 0.10 * rng) & (up >= 0.60 * rng)
    f["dragonfly_doji_down"] = f["dragonfly_doji"] & dn(1)
    f["gravestone_doji_up"] = f["gravestone_doji"] & upt(1)
    small = (body > 0.10 * rng) & (body <= 0.35 * rng)
    ham = small & (lo >= 2 * body) & (up <= 0.25 * rng)
    inv = small & (up >= 2 * body) & (lo <= 0.25 * rng)
    f["hammer"] = ham & dn(1); f["hanging_man"] = ham & upt(1)
    f["inverted_hammer"] = inv & dn(1); f["shooting_star"] = inv & upt(1)
    maru = (body >= 0.90 * rng) & (body >= avgb)
    f["marubozu_bull"] = maru & green; f["marubozu_bear"] = maru & red
    f["spinning_top"] = (body > 0.10 * rng) & (body <= 0.30 * rng) & (up >= body) & (lo >= body)
    f["bullish_engulfing"] = pr_ & green & (O <= pC) & (C >= pO) & (body > pb) & dn(2)
    f["bearish_engulfing"] = pg & red & (O >= pC) & (C <= pO) & (body > pb) & upt(2)
    f["bullish_harami"] = pr_ & (pb >= avgb) & (np.maximum(O, C) <= pO) & (np.minimum(O, C) >= pC) & (body <= 0.5 * pb) & dn(2)
    f["bearish_harami"] = pg & (pb >= avgb) & (np.maximum(O, C) <= pC) & (np.minimum(O, C) >= pO) & (body <= 0.5 * pb) & upt(2)
    f["piercing"] = pr_ & (pb >= avgb) & green & (O <= pC) & (C > pC + 0.5 * pb) & (C < pO) & dn(2)
    f["dark_cloud"] = pg & (pb >= avgb) & red & (O >= pC) & (C < pC - 0.5 * pb) & (C > pO) & upt(2)
    b2, r2, g2 = body.shift(2), red.shift(2, fill_value=False), green.shift(2, fill_value=False)
    O2, C2, avg2 = O.shift(2), C.shift(2), avgb.shift(2)
    star = pb <= 0.5 * avg2
    f["morning_star"] = r2 & (b2 >= avg2) & star & green & (C > (O2 + C2) / 2) & dn(3)
    f["evening_star"] = g2 & (b2 >= avg2) & star & red & (C < (O2 + C2) / 2) & upt(3)
    def three(col, sgn):
        ok = pd.Series(True, index=x.index)
        for k in range(3):
            Ok, Ck, bk, rk, uk, lk = O.shift(k), C.shift(k), body.shift(k), rng.shift(k), up.shift(k), lo.shift(k)
            ok &= (col.shift(k, fill_value=False)) & (bk >= 0.5 * avgb.shift(k)) & ((uk if sgn > 0 else lk) <= 0.35 * rk)
            if k < 2:
                Op, Cp = O.shift(k + 1), C.shift(k + 1)
                ok &= (sgn * (Ck - Cp) > 0) & (Ok <= np.maximum(Op, Cp)) & (Ok >= np.minimum(Op, Cp))
        return ok
    f["three_white_soldiers"] = three(green, 1); f["three_black_crows"] = three(red, -1)
    f["tweezer_bottom"] = ((L - pL).abs() <= 0.10 * A) & pr_ & green & dn(2)
    f["tweezer_top"] = ((H - pH).abs() <= 0.10 * A) & pg & red & upt(2)
    f["inside_bar"] = (H <= pH) & (L >= pL) & ((H < pH) | (L > pL))
    f["outside_bar"] = (H > pH) & (L < pL)
    f = f.fillna(False).astype(bool)
    f["trend10_atr"] = tr.shift(1)                 # context of a 1-bar pattern on this bar
    f["vol_ratio20"] = V / V.shift(1).rolling(VOL_N).mean()
    return f

def candle_columns(df, cutoff=None, asset="stock", recent=3):
    f = candle_frame(df, cutoff, asset)
    if len(f) < 25: return {"candle_flag": "history too short"}
    last = f.iloc[-1]; on = [p for p in PATTERNS if bool(last[p])]
    nb = sum(p in BULL for p in on); ns = sum(p in BEAR for p in on)
    bias = "none" if not on else ("bullish" if nb > ns else ("bearish" if ns > nb else ("mixed" if nb else "neutral")))
    tv = last["trend10_atr"]; vr = last["vol_ratio20"]
    x = pit_cut(df, cutoff, asset)
    prior_volume = x.Volume.iloc[-21:-1].astype(float)
    median_volume = float(prior_volume.median())
    current_volume = float(x.Volume.iloc[-1])
    rv_median = (current_volume / median_volume if len(prior_volume) == 20 and
                 np.isfinite(prior_volume).all() and (prior_volume >= 0).all() and median_volume > 0 and
                 np.isfinite(current_volume) and current_volume >= 0 else None)
    r = dict(candle_last_bar=str(f.index[-1].date()), candle_patterns_last=",".join(on) or None, candle_bias_last=bias,
             candle_score_last=nb - ns, candle_trend10_atr=_r(tv, 2),
             candle_context=None if pd.isna(tv) else ("downtrend" if tv <= -TREND_ATR else ("uptrend" if tv >= TREND_ATR else "sideways")),
             candle_vol_ratio20=_r(vr, 2),
             candle_vol_ratio20_median=_r(rv_median, 6),
             candle_vol_confirmed=bool(bias in ("bullish", "bearish") and pd.notna(vr) and vr >= VOL_CONFIRM))
    rec = []
    for i in range(1, min(recent, len(f))):
        row = f.iloc[-1 - i]; ps = [p for p in PATTERNS if bool(row[p]) and p not in NEUTRAL]
        if ps: rec.append(f"{f.index[-1 - i]:%d.%m}:{'+'.join(ps)}")
    r["candle_patterns_prev2"] = "; ".join(rec) or None
    for p in PATTERNS: r[f"candle_{p}"] = bool(last[p])
    return r

# ------------------------------------------------------------------ 5. liquidity zones (liq_*)
LIQ_FRACTAL = 3; LIQ_LOOKBACK = 120; LIQ_TOL_ATR = 0.25; LIQ_SPAN_ATR = 0.5; LIQ_SWEEP_BARS = 3
LIQ_FVG_MIN_ATR = 0.10; LIQ_DISP_ATR = 1.5; LIQ_OB_BACK = 5; LIQ_OB_LOOKBACK = 250; LIQ_NODE_ATR = 0.25

def fractal_pivots(x, n=LIQ_FRACTAL):
    """Swing highs/lows: High (Low) strictly above (below) the n bars on each side. Pivot i is CONFIRMED at bar i+n.
    Returns list of (kind, price, pivot_idx, confirm_idx)."""
    H, L = x.High.values, x.Low.values; out = []
    for i in range(n, len(H) - n):
        if H[i] > H[i - n:i].max() and H[i] > H[i + 1:i + n + 1].max(): out.append(("H", float(H[i]), i, i + n))
        if L[i] < L[i - n:i].min() and L[i] < L[i + 1:i + n + 1].min(): out.append(("L", float(L[i]), i, i + n))
    return out

def _pools(x, piv, j, A, kind):
    """Untaken confirmed swing highs ('H') / lows ('L') as of bar j (confirmed by j; taken = a later High exceeds the swing by
    more than the equal-highs tolerance LIQ_TOL_ATR*ATR, mirrored for lows),
    clustered when adjacent levels are within LIQ_TOL_ATR*ATR and the cluster spans <= LIQ_SPAN_ATR*ATR."""
    H, L = x.High.values, x.Low.values; lv = []; conf = {}
    for k, p, i, c in piv:
        if k != kind or c > j or i < j - LIQ_LOOKBACK: continue
        after = H[i + 1:j + 1] if kind == "H" else L[i + 1:j + 1]
        if len(after) and ((after.max() > p + LIQ_TOL_ATR * A) if kind == "H" else (after.min() < p - LIQ_TOL_ATR * A)): continue   # taken
        lv.append((p, i)); conf[i] = c
    lv.sort(); cl = []
    for p, i in lv:
        if cl and p - cl[-1][-1][0] <= LIQ_TOL_ATR * A and p - cl[-1][0][0] <= LIQ_SPAN_ATR * A: cl[-1].append((p, i))
        else: cl.append([(p, i)])
    out = []
    for c in cl:
        ps = [q[0] for q in c]; idx = [q[1] for q in c]
        cf = sorted(conf[q[1]] for q in c)
        out.append(dict(level=max(ps) if kind == "H" else min(ps), touches=len(c), first=min(idx), last=max(idx), age=j - min(idx),
                        conf_first=cf[0], conf_equal=cf[1] if len(cf) >= 2 else None, conf_last=cf[-1]))
    return out

def _period_hl(x, ref, freq):
    """High/Low of the last COMPLETE period (W/M) strictly before the period containing `ref`."""
    per = x.index.to_period(freq); cur = pd.Timestamp(ref).to_period(freq)
    m = per < cur
    if not m.any(): return None, None, None
    last = per[m].max(); y = x[per == last]
    return float(y.High.max()), float(y.Low.min()), str(y.index[-1].date())     # confirmed at the close of the period's last bar

def _px(v): return f"{v:,.0f}" if abs(v) >= 1000 else f"{v:.2f}"
def _zone(lo, hi, d): return f"{_px(lo)}-{_px(hi)} ({d:%d.%m.%y})"

def liquidity(df, cutoff=None, asset="stock", ref_date=None):
    x = pit_cut(df, cutoff, asset); r = {}
    if len(x) < 40: return {"liq_flag": "history too short"}
    O, H, L, C = (x[k].values.astype(float) for k in ("Open", "High", "Low", "Close"))
    a = atr14(H, L, C); A = float(a[-1]); j = len(x) - 1; close = C[-1]
    if not np.isfinite(A): return {"liq_flag": "no ATR"}
    piv = fractal_pivots(x)
    # HVN/LVN from the daily 60 and 120-bar profiles (same function as vp*)
    nodes = {"HVN": [], "LVN": []}; bw = 0.0
    for w in VP_WINDOWS:
        y = x.iloc[-w:]; pr = profile(y.Low.values, y.High.values, y.Volume.values)
        if pr: nodes["HVN"] += pr["hvn"]; nodes["LVN"] += pr["lvn"]; bw = max(bw, pr["bin"])
    tol = max(LIQ_NODE_ATR * A, bw)
    def node(lvl):
        for k in ("HVN", "LVN"):
            if any(abs(v - lvl) <= tol for v in nodes[k]): return k
        return None
    # 1. pools
    for side, kind, sel in (("bsl", "H", lambda p: p["level"] > close), ("ssl", "L", lambda p: p["level"] < close)):
        P = [p for p in _pools(x, piv, j, A, kind) if sel(p)]
        r[f"liq_{side}_pools_n"] = len(P)
        if not P: continue
        near = min(P, key=lambda p: abs(p["level"] - close))
        within = [p for p in P if abs(p["level"] - close) <= 5 * A]
        strong = max(within, key=lambda p: (p["touches"], -abs(p["level"] - close))) if within else None
        ds = lambda k_: str(x.index[k_].date()) if k_ is not None else None
        r.update({f"liq_{side}_confirmed_at": ds(near["conf_last"]), f"liq_{side}_first_confirmed_at": ds(near["conf_first"]),
                  f"liq_{side}_equal_confirmed_at": ds(near["conf_equal"])})
        r.update({f"liq_{side}_level": _r(near["level"]), f"liq_{side}_touches": near["touches"], f"liq_{side}_age_bars": near["age"],
                  f"liq_{side}_dist_atr": _r(abs(near["level"] - close) / A, 2), f"liq_{side}_equal": near["touches"] >= 2,
                  f"liq_{side}_vp_node": node(near["level"]), f"liq_{side}_hvn": node(near["level"]) == "HVN"})
        if strong and strong["touches"] >= 2:
            r.update({f"liq_{side}_strong_level": _r(strong["level"]), f"liq_{side}_strong_touches": strong["touches"],
                      f"liq_{side}_strong_dist_atr": _r(abs(strong["level"] - close) / A, 2), f"liq_{side}_strong_vp_node": node(strong["level"]),
                      f"liq_{side}_strong_confirmed_at": ds(strong["conf_last"]), f"liq_{side}_strong_equal_confirmed_at": ds(strong["conf_equal"])})
    # standard levels: prior bar (day), prior complete week / month before the reference date
    ref = pd.Timestamp(ref_date) if ref_date is not None else x.index[-1] + pd.Timedelta(days=1)
    r.update(liq_pdh=_r(H[-1]), liq_pdl=_r(L[-1]), liq_pd_confirmed_at=str(x.index[-1].date()))
    for nm, f in (("w", "W"), ("m", "M")):
        hh, ll, cd = _period_hl(x, ref, f); r[f"liq_p{nm}h"] = _r(hh); r[f"liq_p{nm}l"] = _r(ll); r[f"liq_p{nm}_confirmed_at"] = cd
    # 2. sweeps on the last LIQ_SWEEP_BARS bars: wick beyond a pool (as known the bar before) and close back inside
    sw = []
    for jj in range(max(LIQ_FRACTAL + 1, j - LIQ_SWEEP_BARS + 1), j + 1):
        Aj = a[jj - 1] if np.isfinite(a[jj - 1]) else A
        lv_h = [(p["level"], f"{p['touches']}x swing high") for p in _pools(x, piv, jj - 1, Aj, "H")] + [(H[jj - 1], "prior bar high")]
        lv_l = [(p["level"], f"{p['touches']}x swing low") for p in _pools(x, piv, jj - 1, Aj, "L")] + [(L[jj - 1], "prior bar low")]
        hit_h = [t for t in lv_h if H[jj] > t[0] and C[jj] < t[0]]
        hit_l = [t for t in lv_l if L[jj] < t[0] and C[jj] > t[0]]
        if hit_h: lvl, lab = max(hit_h); sw.append((jj, "bearish (buy-side swept)", lvl, lab))
        if hit_l: lvl, lab = min(hit_l); sw.append((jj, "bullish (sell-side swept)", lvl, lab))
    if sw:
        jj, dr, lvl, lab = sw[-1]
        r.update(liq_sweep_date=str(x.index[jj].date()), liq_sweep_confirmed_at=str(x.index[jj].date()), liq_sweep_dir=dr, liq_sweep_level=_r(lvl), liq_sweep_kind=lab,
                 liq_sweep_last=f"{dr}: {lab} {_px(lvl)} on {x.index[jj]:%d.%m.%y}", liq_sweeps_n=len(sw))
    # 3. fair value gaps (3-bar imbalance), still unfilled at the last bar
    gaps = []
    for k in range(max(2, j - LIQ_LOOKBACK), j + 1):
        mn = LIQ_FVG_MIN_ATR * (a[k] if np.isfinite(a[k]) else A)
        if L[k] - H[k - 2] >= mn:                                 # bullish FVG [H[k-2], L[k]]
            lo, hi = H[k - 2], L[k]; fut = L[k + 1:j + 1]
            if len(fut): hi = min(hi, fut.min())
            if hi > lo: gaps.append(("bull", lo, hi, k))
        if L[k - 2] - H[k] >= mn:                                 # bearish FVG [H[k], L[k-2]]
            lo, hi = H[k], L[k - 2]; fut = H[k + 1:j + 1]
            if len(fut): lo = max(lo, fut.max())
            if hi > lo: gaps.append(("bear", lo, hi, k))
    r["liq_fvg_open_n"] = len(gaps)
    ab = [g for g in gaps if g[1] >= close]; be = [g for g in gaps if g[2] <= close]; ins = [g for g in gaps if g[1] < close < g[2]]
    if ab:
        g = min(ab, key=lambda g: g[1]); r.update(liq_fvg_above_confirmed_at=str(x.index[g[3]].date()), liq_fvg_above=_zone(g[1], g[2], x.index[g[3]]), liq_fvg_above_lo=_r(g[1]), liq_fvg_above_hi=_r(g[2]), liq_fvg_above_type=g[0], liq_fvg_above_dist_atr=_r((g[1] - close) / A, 2))
    if be:
        g = max(be, key=lambda g: g[2]); r.update(liq_fvg_below_confirmed_at=str(x.index[g[3]].date()), liq_fvg_below=_zone(g[1], g[2], x.index[g[3]]), liq_fvg_below_lo=_r(g[1]), liq_fvg_below_hi=_r(g[2]), liq_fvg_below_type=g[0], liq_fvg_below_dist_atr=_r((close - g[2]) / A, 2))
    r["liq_in_fvg"] = bool(ins)
    # 4. order blocks: last opposite candle before a displacement bar (body >= 1.5 ATR) that breaks structure
    obs = []
    for d in range(max(LIQ_FRACTAL + 2, j - LIQ_OB_LOOKBACK), j + 1):
        Ad = a[d - 1]
        if not np.isfinite(Ad) or abs(C[d] - O[d]) < LIQ_DISP_ATR * Ad: continue
        known = [p for p in piv if p[3] <= d - 1]
        if C[d] > O[d]:
            sh = [p for p in known if p[0] == "H"]
            if not sh or C[d] <= sh[-1][1]: continue              # must close above the last confirmed swing high (BOS)
            ob = next((k for k in range(d - 1, max(-1, d - 1 - LIQ_OB_BACK), -1) if C[k] < O[k]), None)
            if ob is None: continue
            lo, hi = L[ob], H[ob]
            if d < j and L[d + 1:j + 1].min() <= hi: continue        # mitigated: price came back into the block
            obs.append(("bull", lo, hi, ob, d))
        else:
            sl = [p for p in known if p[0] == "L"]
            if not sl or C[d] >= sl[-1][1]: continue
            ob = next((k for k in range(d - 1, max(-1, d - 1 - LIQ_OB_BACK), -1) if C[k] > O[k]), None)
            if ob is None: continue
            lo, hi = L[ob], H[ob]
            if d < j and H[d + 1:j + 1].max() >= lo: continue
            obs.append(("bear", lo, hi, ob, d))
    r["liq_ob_open_n"] = len(obs)
    ab = [o for o in obs if o[1] >= close]; be = [o for o in obs if o[2] <= close]
    if ab:
        o = min(ab, key=lambda o: o[1]); r.update(liq_ob_above_confirmed_at=str(x.index[o[4]].date()), liq_ob_above=f"{o[0]} " + _zone(o[1], o[2], x.index[o[3]]), liq_ob_above_lo=_r(o[1]), liq_ob_above_hi=_r(o[2]), liq_ob_above_dist_atr=_r((o[1] - close) / A, 2))
    if be:
        o = max(be, key=lambda o: o[2]); r.update(liq_ob_below_confirmed_at=str(x.index[o[4]].date()), liq_ob_below=f"{o[0]} " + _zone(o[1], o[2], x.index[o[3]]), liq_ob_below_lo=_r(o[1]), liq_ob_below_hi=_r(o[2]), liq_ob_below_dist_atr=_r((close - o[2]) / A, 2))
    return r

# ------------------------------------------------------------------ all columns
def geometry_columns(df, cutoff=None, asset="stock", direction="LONG", intraday=False, symbol=None):
    """One dict of EXPERIMENTAL columns for one ticker at one cutoff (logged only, weight 0)."""
    x = pit_cut(df, cutoff, asset)
    r = {"geo_last_bar": str(x.index[-1].date()) if len(x) else None, "geo_bars": int(len(x)), "geo_direction_view": direction.upper()}
    if len(x) < 30:
        r["geo_flag"] = "history too short (<30 bars)"; return r
    an = swing_anchor(x, direction)
    if an is not None:   # anchor pivots of spiral/Gann/anchored VP and the bar each was CONFIRMED on (2xATR zigzag lag)
        r.update(exp_anchor_origin_date=str(x.index[an["i0"]].date()), exp_anchor_origin_confirmed_at=str(x.index[an["conf0"]].date()),
                 exp_anchor_end_date=str(x.index[an["i1"]].date()), exp_anchor_end_confirmed_at=str(x.index[an["conf1"]].date()))
    for fn in (fib_spiral, gann_box):
        try: r.update(fn(x, None, asset, direction, anchor=an))
        except Exception as e: r[f"{fn.__name__}_error"] = f"{e.__class__.__name__}: {e}"
    try: r.update(volume_profile(x, None, asset, direction, anchor=an, intraday=intraday, symbol=symbol))
    except Exception as e: r["vp_error"] = f"{e.__class__.__name__}: {e}"
    try: r.update(candle_columns(x, None, asset))
    except Exception as e: r["candle_error"] = f"{e.__class__.__name__}: {e}"
    try:
        ref = None
        if cutoff is not None:
            c = pd.Timestamp(cutoff); c = c.tz_localize("UTC") if c.tzinfo is None else c
            ref = c.tz_convert(NY if asset == "stock" else "UTC").tz_localize(None)
        r.update(liquidity(x, None, asset, ref_date=ref))
    except Exception as e: r["liq_error"] = f"{e.__class__.__name__}: {e}"
    if an is None: r["geo_flag"] = "no confirmed 2xATR swing -> spiral/Gann blank"
    return r

# columns carried into the tracker (build7.py cols 78+); everything else stays in scan_raw.csv
TRACKER_KEYS = ["exp_spiral_next_node_date", "exp_spiral_next_node_price", "exp_spiral_next_cross_date", "exp_spiral_near_arc",
                "exp_spiral_arc_dist_atr", "exp_gann_level_above", "exp_gann_level_below", "exp_gann_angle_above", "exp_gann_angle_below",
                "exp_gann_next_time_date", "vp60_poc", "vp60_vah", "vp60_val", "vp60_poc_dist_atr", "vp120_poc", "vp120_poc_dist_atr",
                "vpanc_poc", "vp60_hvn_near", "vp60_lvn_near", "vp20m_poc", "candle_patterns_last", "candle_bias_last",
                "candle_context", "candle_vol_ratio20", "candle_vol_confirmed",
                "liq_bsl_level", "liq_bsl_touches", "liq_bsl_dist_atr", "liq_bsl_hvn", "liq_ssl_level", "liq_ssl_touches", "liq_ssl_dist_atr",
                "liq_ssl_hvn", "liq_sweep_last", "liq_fvg_above", "liq_fvg_below", "liq_ob_above", "liq_ob_below", "liq_pwh", "liq_pwl",
                "exp_anchor_end_confirmed_at", "liq_bsl_confirmed_at", "liq_ssl_confirmed_at", "liq_fvg_above_confirmed_at", "liq_fvg_below_confirmed_at",
                "liq_ob_above_confirmed_at", "liq_ob_below_confirmed_at",
                # 08.10 watch-only (researcher §3.14): short below 120d value area; tracked on new setups from 12.10
                "watch_short_below_va120", "excess_spy_d20"]

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="OHLCV csv with a date column"); ap.add_argument("--cutoff"); ap.add_argument("--asset", default="stock")
    ap.add_argument("--direction", default="LONG")
    a = ap.parse_args()
    d = pd.read_csv(a.csv); d = d.set_index(pd.to_datetime(d.iloc[:, 0])).iloc[:, 1:]
    print(json.dumps(geometry_columns(d, a.cutoff, a.asset, a.direction), indent=1, ensure_ascii=False, default=str))
