"""EXPERIMENTAL historical support / resistance levels (08.10.2026, Ilan). LOGGED ONLY - weight 0, never changes score/stops/targets.
Import-safe (no I/O at import). Deterministic. Point-in-time: every frame is cut with scanner_geometry.pit_cut (stock daily bar D
visible only after its 16:00 ET close <= cutoff; intraday bars only if bar end <= cutoff); a fractal pivot exists only from its
confirmation bar (k bars later) - no repainting.

LOOKBACK PER SCAN TYPE (frames built from the visible bars only)
  SWING     : 400 daily + 200 weekly bars           (weekly/monthly = resampled from PIT daily; the current partial week/month
  LONG_TERM : 200 weekly + 120 monthly bars          is included with the days visible so far)
  INTRADAY  : 5-min of the last 10 sessions + 1H of the last 60 sessions (Alpaca, regular session) + 400 daily,
              plus prior-day / prior-week high-low and round numbers. Alpaca intraday history on this box starts ~July 2026:
              shorter windows are used as available and flagged (sr_flag).
METHOD (per timeframe TF)
  pivots    : fractal highs/lows of width k (High[i] = max of High[i-k..i+k]); k = 5m:6, 1H:4, D:3, W:2, M:2. Confirmed at i+k.
  clusters  : pivots sorted by price, greedily merged while within 0.5 x ATR14 of that TF, expressed as % of price (ATR% at the
              last visible bar x pivot price, so old levels at much lower prices are not over-merged); span <= 2x that;
              level = mean member price; touches = members.
  strength  : TF_WEIGHT[tf] x sum over members of  exp(-age_days / HALF_LIFE[scan]) x clip(member bar volume / median TF volume, 0.5, 3)
              TF_WEIGHT: 5m 0.5, 1H 0.75, D 1, W 2, M 3. HALF_LIFE days: INTRADAY 15, SWING 180, LONG_TERM 720.
  merge TFs : levels of different TFs within 0.5 x daily ATR14 merged (strength summed, tf = highest TF, touches summed).
  flip      : the cluster holds both pivot highs and lows; flip_dir 'R->S' if the level is now below price and its older members
              were highs (resistance turned support), 'S->R' mirrored.
  intraday extras: PDH/PDL, PWH/PWL (strength 1.0 x TF weight D), round numbers: step from {1,2.5,5,10,25,50,100,250,500,1000}
              closest to 1 daily ATR, 2 above / 2 below (strength 0.5).
  output    : top TOP_N (5) levels above and below the last close by strength, among levels within MAX_DIST_ATR daily ATR14
              (INTRADAY 4, SWING 8, LONG_TERM 25); nearest support/resistance among them, distance in
              daily ATR14, strength, tf, touches, flip.
"""
import os, math, json, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

CACHE = "/workspace/scanner-levels-cache"
NY = "America/New_York"
TF_K = {"5m": 6, "1H": 4, "D": 3, "W": 2, "M": 2}
TF_WEIGHT = {"5m": 0.5, "1H": 0.75, "D": 1.0, "W": 2.0, "M": 3.0}
TF_RANK = {"5m": 0, "1H": 1, "D": 2, "W": 3, "M": 4}
HALF_LIFE = {"INTRADAY": 15.0, "SWING": 180.0, "LONG_TERM": 720.0}
SPEC = {"SWING": {"D": 400, "W": 200}, "LONG_TERM": {"W": 200, "M": 120}, "INTRADAY": {"5m": 10, "1H": 60, "D": 400}}
CLUSTER_ATR = 0.5; TOP_N = 5
MAX_DIST_ATR = {"INTRADAY": 4.0, "SWING": 8.0, "LONG_TERM": 25.0}   # candidate levels within this many daily ATR14 of the close
ROUND_STEPS = [1, 2.5, 5, 10, 25, 50, 100, 250, 500, 1000]

def _geo():
    import sys; sys.path.insert(0, "/workspace")
    import scanner_geometry as GEO
    return GEO

def _utc(c):
    c = pd.Timestamp(c)
    if c.tzinfo is None: c = c.tz_localize("Asia/Jerusalem")
    return c.tz_convert("UTC")

def _r(v, n=4):
    try:
        v = float(v); return round(v, n) if np.isfinite(v) else None
    except Exception: return None

# ------------------------------------------------------------------ data
def long_daily(symbol, cutoff, years=12):
    """Long daily history (Yahoo, auto_adjust like the scanner) cached per symbol and download date, then PIT-cut."""
    GEO = _geo(); cut = _utc(cutoff)
    f = f"{CACHE}/yahoo_daily/{symbol}_{cut:%Y%m%d}.csv"
    if not os.path.exists(f):
        import yfinance as yf
        x = yf.download(symbol, start=(cut - pd.Timedelta(days=365 * years)).strftime("%Y-%m-%d"),
                        end=(cut + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), interval="1d", auto_adjust=True, progress=False)
        if isinstance(x.columns, pd.MultiIndex): x.columns = x.columns.get_level_values(0)
        if x.empty: return None
        os.makedirs(os.path.dirname(f), exist_ok=True); x.index.name = "date"
        x[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"]).to_csv(f)
    x = pd.read_csv(f, parse_dates=["date"]).set_index("date")
    return GEO.pit_cut(x, cut, "stock")

def resample(x, rule):
    g = x.resample(rule, label="left")
    y = pd.DataFrame({"Open": g.Open.first(), "High": g.High.max(), "Low": g.Low.min(), "Close": g.Close.last(), "Volume": g.Volume.sum()})
    return y.dropna(subset=["Close"])

def _alpaca(symbol, tf, start, end):
    """Alpaca stock bars [start, end) (keys from env, never printed/stored), cached. tf: '5Min' | '1Hour'."""
    import requests
    f = f"{CACHE}/alpaca_{tf}/{symbol}/{start:%Y%m%dT%H%M}_{end:%Y%m%dT%H%M}.csv.gz"
    if os.path.exists(f): return pd.read_csv(f, parse_dates=["t"])
    kid, sec = os.environ.get("ALPACA_API_KEY_ID"), os.environ.get("ALPACA_API_SECRET_KEY")
    if not kid or not sec: raise RuntimeError("no alpaca keys")
    H = {"APCA-API-KEY-ID": kid, "APCA-API-SECRET-KEY": sec}
    p = dict(symbols=symbol, timeframe=tf, start=start.isoformat(), end=end.isoformat(), limit=10000, adjustment="split", feed="sip")
    out, tok = [], None
    for _ in range(30):
        if tok: p["page_token"] = tok
        q = requests.get("https://data.alpaca.markets/v2/stocks/bars", headers=H, params=p, timeout=30)
        if q.status_code == 403 and p.get("feed") == "sip": p["feed"] = "iex"; continue
        q.raise_for_status(); j = q.json(); out += (j.get("bars") or {}).get(symbol, []); tok = j.get("next_page_token")
        if not tok: break
    d = pd.DataFrame(out)
    if d.empty: raise RuntimeError("no bars")
    d = d.rename(columns={"o": "Open", "h": "High", "l": "Low", "c": "Close", "v": "Volume"})[["t", "Open", "High", "Low", "Close", "Volume"]]
    d["t"] = pd.to_datetime(d["t"], utc=True); os.makedirs(os.path.dirname(f), exist_ok=True); d.to_csv(f, index=False)
    return d

def intraday_frame(symbol, cutoff, tf, sessions, daily):
    """Regular-session bars of the last `sessions` daily sessions visible at cutoff, only bars ending <= cutoff."""
    cut = _utc(cutoff); mins = {"5Min": 5, "1Hour": 60}[tf]
    days = daily.index[-sessions:]
    start = pd.Timestamp(days[0]).tz_localize(NY).tz_convert("UTC")
    m = _alpaca(symbol, tf, start, cut.floor("h") + pd.Timedelta(hours=1))
    m = m[(m["t"] >= start) & (m["t"] + pd.Timedelta(minutes=mins) <= cut)]
    tl = m["t"].dt.tz_convert(NY); mm = tl.dt.hour * 60 + tl.dt.minute
    m = m[(mm >= 570) & (mm < 960)] if tf == "5Min" else m[(mm >= 540) & (mm < 960)]
    x = m.set_index(m["t"].dt.tz_convert("UTC").dt.tz_localize(None))[["Open", "High", "Low", "Close", "Volume"]]
    return x

# ------------------------------------------------------------------ levels
def fractal_pivots(x, k):
    """[(kind, price, idx, confirm_idx, volume)] - confirmed only (confirm_idx = idx + k <= last bar)."""
    h, l, v = x.High.values, x.Low.values, x.Volume.values.astype(float); n = len(x); out = []
    for i in range(k, n - k):
        if h[i] == h[i - k:i + k + 1].max(): out.append(("H", float(h[i]), i, i + k, v[i]))
        if l[i] == l[i - k:i + k + 1].min(): out.append(("L", float(l[i]), i, i + k, v[i]))
    return out

def tf_levels(x, tf, cutoff, half_life):
    GEO = _geo()
    if x is None or len(x) < 2 * TF_K[tf] + 15: return [], None
    a = GEO.atr14(x.High.values, x.Low.values, x.Close.values); A = float(a[-1])
    if not np.isfinite(A) or A <= 0: return [], None
    piv = sorted(fractal_pivots(x, TF_K[tf]), key=lambda p: p[1])
    medv = float(np.nanmedian(x.Volume.values)) or 1.0; cut = _utc(cutoff).tz_localize(None)
    cl = []; rel = CLUSTER_ATR * A / float(x.Close.iloc[-1])          # 0.5 x ATR as a % of price -> scale-free for old, lower prices
    for p in piv:
        if cl and p[1] - cl[-1][-1][1] <= rel * p[1] and p[1] - cl[-1][0][1] <= 2 * rel * p[1]: cl[-1].append(p)
        else: cl.append([p])
    out = []
    for c in cl:
        s = 0.0
        for p in c:
            age = max(0.0, (cut - pd.Timestamp(x.index[p[2]])).total_seconds() / 86400)
            s += math.exp(-age * math.log(2) / half_life) * float(np.clip((p[4] / medv) if medv else 1.0, 0.5, 3.0))
        kinds = [p[0] for p in sorted(c, key=lambda p: p[2])]
        out.append(dict(price=float(np.mean([p[1] for p in c])), tf=tf, touches=len(c), strength=TF_WEIGHT[tf] * s,
                        kinds=kinds, first=str(pd.Timestamp(x.index[min(p[2] for p in c)]).date()),
                        last=str(pd.Timestamp(x.index[max(p[2] for p in c)]).date()),
                        confirmed_at=str(pd.Timestamp(x.index[max(p[3] for p in c)]).date())))
    return out, A

def _merge(levels, A):
    levels = sorted(levels, key=lambda d: d["price"]); out = []
    for d in levels:
        if out and d["price"] - out[-1]["price"] <= CLUSTER_ATR * A and d.get("src") is None and out[-1].get("src") is None:
            o = out[-1]; w = o["strength"] + d["strength"]
            o["price"] = (o["price"] * o["strength"] + d["price"] * d["strength"]) / w if w else o["price"]
            o["strength"] = w; o["touches"] += d["touches"]; o["kinds"] = o["kinds"] + d["kinds"]
            if TF_RANK[d["tf"]] > TF_RANK[o["tf"]]: o["tf"] = d["tf"]
            o["tfs"] = sorted(set(o.get("tfs", [o["tf"]]) + [d["tf"]]), key=TF_RANK.get)
            o["last"] = max(o["last"], d["last"]); o["confirmed_at"] = max(o["confirmed_at"], d["confirmed_at"])
        else:
            out.append(dict(d, tfs=[d["tf"]]))
    return out

def levels_for(symbol, cutoff, scan_type="SWING", direction="LONG", daily=None):
    """Top S/R levels for one ticker at one cutoff. Returns dict(levels=[...], summary={columns}, flags=[...])."""
    scan_type = scan_type.upper(); cut = _utc(cutoff); hl = HALF_LIFE[scan_type]; spec = SPEC[scan_type]; flags = []
    d = daily if daily is not None else long_daily(symbol, cut)
    if d is None or len(d) < 60: return dict(levels=[], summary={"sr_flag": "no / too little daily history"}, flags=["no data"])
    GEO = _geo()
    aD = GEO.atr14(d.High.values, d.Low.values, d.Close.values); AD = float(aD[-1]); close = float(d.Close.iloc[-1])
    frames = {}
    if "D" in spec: frames["D"] = d.iloc[-spec["D"]:]
    if "W" in spec: frames["W"] = resample(d, "W-FRI").iloc[-spec["W"]:]
    if "M" in spec: frames["M"] = resample(d, "MS").iloc[-spec["M"]:]
    for tf, al in (("5m", "5Min"), ("1H", "1Hour")):
        if tf in spec:
            try:
                fr = intraday_frame(symbol, cut, al, spec[tf], d); frames[tf] = fr
                have = fr.index.normalize().nunique() if len(fr) else 0
                if have < spec[tf]: flags.append(f"{tf}: only {have} of {spec[tf]} sessions available (Alpaca history)")
            except Exception as e: flags.append(f"{tf}: unavailable ({e.__class__.__name__})")
    for tf, n in spec.items():
        if tf in frames and tf in ("D", "W", "M") and len(frames[tf]) < n: flags.append(f"{tf}: only {len(frames[tf])} of {n} bars")
    allv = []
    for tf, fr in frames.items():
        lv, _ = tf_levels(fr, tf, cut, hl); allv += lv
    lv = _merge(allv, AD)
    for o in lv:
        k = o["kinds"]; o["flip"] = ("H" in k and "L" in k)
        side = "support" if o["price"] < close else "resistance"; o["side"] = side
        older = k[: max(1, len(k) // 2)]
        o["flip_dir"] = (("R->S" if side == "support" and older.count("H") >= older.count("L") else
                          "S->R" if side == "resistance" and older.count("L") >= older.count("H") else None) if o["flip"] else None)
        o["flip"] = bool(o["flip_dir"])
    if scan_type == "INTRADAY":
        ex = []
        if len(d) >= 2: ex += [("PDH", float(d.High.iloc[-1])), ("PDL", float(d.Low.iloc[-1]))]
        wk = resample(d, "W-FRI")
        if len(wk) >= 2:
            pw = wk.iloc[-2] if wk.index[-1] + pd.Timedelta(days=6) > d.index[-1] else wk.iloc[-1]
            ex += [("PWH", float(pw.High)), ("PWL", float(pw.Low))]
        for nm, p in ex: lv.append(dict(price=p, tf="D", touches=1, strength=1.0, kinds=[], flip=False, flip_dir=None, src=nm, tfs=["D"],
                                         side="support" if p < close else "resistance", confirmed_at=str(d.index[-1].date())))
        step = min(ROUND_STEPS, key=lambda s: abs(s - AD)); base = math.floor(close / step) * step
        for p in (base - step, base, base + step, base + 2 * step):
            if p > 0 and p != close: lv.append(dict(price=float(p), tf="D", touches=0, strength=0.5, kinds=[], flip=False, flip_dir=None,
                                                    src=f"round {step:g}", tfs=["D"], side="support" if p < close else "resistance"))
    md = MAX_DIST_ATR[scan_type] * AD
    sup = sorted([o for o in lv if close - md <= o["price"] < close], key=lambda o: -o["strength"])[:TOP_N]
    res = sorted([o for o in lv if close < o["price"] <= close + md], key=lambda o: -o["strength"])[:TOP_N]
    top = sorted(sup + res, key=lambda o: o["price"])
    for o in top:
        o["dist_atr"] = _r((o["price"] - close) / AD, 2); o["strength"] = _r(o["strength"], 3); o["price"] = _r(o["price"])
    smax = max([o["strength"] for o in top] + [1e-9])
    S = {"sr_scan_type": scan_type, "sr_last_bar": str(d.index[-1].date()), "sr_close": _r(close), "sr_atr14_d": _r(AD),
         "sr_flag": "; ".join(flags) or None, "sr_n_levels": len(top)}
    for nm, L, key in (("support", sup, lambda o: -o["price"]), ("resistance", res, lambda o: o["price"])):
        if not L: continue
        n_ = sorted(L, key=key)[0]; st = max(L, key=lambda o: o["strength"])
        S.update({f"sr_{nm}": n_["price"], f"sr_{nm}_dist_atr": n_["dist_atr"], f"sr_{nm}_strength": n_["strength"],
                  f"sr_{nm}_strength_rel": _r(n_["strength"] / smax, 3), f"sr_{nm}_tf": n_["tf"], f"sr_{nm}_touches": n_["touches"],
                  f"sr_{nm}_flip": n_["flip_dir"], f"sr_{nm}_confirmed_at": n_.get("confirmed_at"),
                  f"sr_{nm}_strongest": st["price"], f"sr_{nm}_strongest_strength": st["strength"], f"sr_{nm}_strongest_tf": st["tf"]})
    S["sr_levels_json"] = json.dumps([[o["price"], o["side"][0].upper(), o["tf"], o["strength"], o["touches"], o["flip_dir"], o.get("src")] for o in top])
    return dict(levels=top, summary=S, flags=flags)

def sr_columns(symbol, cutoff, scan_type="SWING", direction="LONG"):
    try: return levels_for(symbol, cutoff, scan_type, direction)["summary"]
    except Exception as e: return {"sr_flag": f"error {e.__class__.__name__}: {e}"}

TRACKER_KEYS = ["sr_support", "sr_support_dist_atr", "sr_support_strength", "sr_support_tf", "sr_support_touches", "sr_support_flip",
                "sr_resistance", "sr_resistance_dist_atr", "sr_resistance_strength", "sr_resistance_tf", "sr_resistance_touches",
                "sr_resistance_flip", "sr_support_strongest", "sr_resistance_strongest", "sr_flag", "sr_last_bar"]
