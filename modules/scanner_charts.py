"""Setup charts for the scanner (08.10.2026, Ilan: "פיבו ואליוט לא רק מתמטי - צריך קשר ויזואלי").
Rendering reads saved scores, stops and targets. The levels producer also supplies the experimental research overlay.
Import-safe (no work at import time).

Every number drawn comes from the SAME point-in-time data and the SAME functions the scanner uses:
  * bars      : scanner_stops.daily_bars(symbol, 'stock', cutoff, px_dir) - the cached Yahoo daily bars of that scan
                (scanner-momentum-cache/<cutoff>), only bars whose 16:00 ET close <= cutoff (pit.history).
  * ATR/zigzag: scanner_stops.atr14 / zigzag (iaf/sim_fib.py exec'd unchanged), ZZ = 2.0 x ATR14, confirmed pivots only.
  * Elliott   : scanner_stops impulse counts (v1); scanner_elliott_v2 also supplies A-B-C and provisional counts (v2).
  * Fib       : scanner_stops.fib_elliott() -> fib_r382..r786, fib_tp_1272/1618 (leg = geometry.swing_anchor()).
  * VP120     : scanner_geometry.volume_profile() -> vp120_poc / vah / val (last 120 daily bars).
  * Stops     : scanner_stops.active_stop() -> initial_stop (entry -/+ 4xATR14), tp_half_1618 (LONG active target).
                Scan output values (platform_enrichment.csv entry/stop/target) are drawn when passed and cross-checked.
  * S/R       : optional, from scanner_levels.levels_for() (experimental, weight 0).
Usage:
  import scanner_charts as SC
  SC.render_setup_chart('MU', '2026-10-08T12:15Z', 'LONG', '/tmp/MU_long.png', score=100.0)
  python3 scanner_charts.py --run-dir /workspace/scan-runs/2026-10-08_1515_trial      # top candidates + charts_he.pdf
"""
import os, sys, json, math, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, "/workspace")

FONT_DIR = "/usr/share/fonts/truetype/sand-box/google/IBM Plex Sans Hebrew"
C_UP, C_DN = "#26a69a", "#ef5350"
C_FIB, C_EXT, C_ZZ, C_EW = "#7e57c2", "#00897b", "#455a64", "#1565c0"
C_ABC = "#ef6c00"
C_POC, C_VA = "#ef6c00", "#ffcc80"
C_ENTRY, C_STOP, C_TGT = "#212121", "#c62828", "#2e7d32"
C_SR_D, C_SR_W, C_SR_M, C_SR_I = "#8d6e63", "#1e88e5", "#6a1b9a", "#f9a825"

_mods = {}
def _m():
    """Lazy imports so `import scanner_charts` never touches data, network or the scanner modules."""
    if not _mods:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager as fm
        for f in ("Regular", "Bold", "Medium"):
            p = f"{FONT_DIR}/IBMPlexSansHebrew-{f}.ttf"
            if os.path.exists(p): fm.fontManager.addfont(p)
        import scanner_stops as ST, scanner_geometry as GEO, scanner_momentum as SM
        _mods.update(plt=plt, ST=ST, GEO=GEO, SM=SM, matplotlib=matplotlib)
    return _mods

LRM = "\u200e"
def ltr(s):
    """Placeholder for LTR runs inside Hebrew captions. LRM marks were tested and scrambled matplotlib's own RTL layout, so the
    run is returned unchanged; captions instead start Latin runs with a letter (e.g. 'ATR14×4', not '4×ATR14')."""
    return s

def heb(s):
    """Hebrew/mixed string for matplotlib. matplotlib >= 3.11 lays out RTL text itself (checked visually on this box:
    applying python-bidi on top double-reverses it); older versions get python-bidi visual ordering, base direction RTL."""
    import matplotlib
    if tuple(int(v) for v in matplotlib.__version__.split(".")[:2]) >= (3, 11): return s
    from bidi.algorithm import get_display
    return get_display(s, base_dir="R")

def _utc(cutoff):
    c = pd.Timestamp(cutoff)
    if c.tzinfo is None: c = c.tz_localize("Asia/Jerusalem")
    return c.tz_convert("UTC")

def _f(v):
    try:
        v = float(v); return v if np.isfinite(v) else None
    except Exception: return None

def _fmt(v):
    return "-" if v is None else (f"{v:,.0f}" if abs(v) >= 10000 else f"{v:,.2f}")

# ------------------------------------------------------------------ 1) PRODUCER: levels dict (levels_schema.json) from scanner functions
def _d(x, i): return str(pd.Timestamp(x.index[i]).date())

def build_levels(symbol, cutoff, direction, asset="stock", px_dir=None, score=None, score_basis=None, entry=None, stop=None,
                 target=None, target_note=None, sr=True, waves=True, run_id=None, series_bars=300, bars_df=None):
    """Reference producer of the per-ticker levels file. Every number comes from the scanner's own functions on the same PIT bars:
    scanner_stops (atr14/zigzag, fib_elliott v1, elliott_counts, active_stop), scanner_elliott_v2, scanner_geometry.volume_profile,
    scanner_levels.levels_for, scanner_waves.waves_analysis. entry/stop/target: scan output if given, else active_stop()."""
    M = _m(); ST, GEO, SM = M["ST"], M["GEO"], M["SM"]
    import scanner_elliott_v2 as EV2
    cut = _utc(cutoff); direction = direction.upper(); sgn = 1 if direction == "LONG" else -1
    px_dir = px_dir or f"{SM.CACHE_ROOT}/{cut.strftime('%Y%m%dT%H%MZ')}"
    x = bars_df if bars_df is not None else ST.daily_bars(symbol, asset, cut, px_dir)
    if x is None or len(x) < 30: raise ValueError(f"{symbol}: no / too few PIT bars at {cut}")
    x = GEO.pit_cut(x, cut, asset)
    h, l, c = x.High.values, x.Low.values, x.Close.values
    a = ST.atr14(h, l, c); A = float(a[-1])
    known = [p for p in ST.zigzag(h, l, a, ST.ZZ) if p[3] <= len(h) - 1]
    pv = lambda p, lab=None, prov=False: {**({"label": lab} if lab is not None else {}), "kind": p[0], "price": round(float(p[1]), 4),
                                           "date": _d(x, p[2]), "confirmed_at": _d(x, p[3]) if p[3] is not None else None,
                                           **({"provisional": bool(prov)} if lab is not None else {})}
    # v1 (exactly what scan_raw logs, in the requested view)
    fe = ST.fib_elliott(x, asset, direction); counts = ST.elliott_counts(known, sgn); best = ST.select_count(counts)
    v1 = {"version": "v1", "view": direction, "valid": bool(best), "label": best["label"] if best else fe.get("elliott_wave_label"),
          "deviations": best["deviations"] if best else None, "n_valid_counts": len(counts),
          "pivots": [pv(p, str(k)) for k, p in enumerate(best["pivots"])] if best else [],
          "target_w3": _f(fe.get("elliott_target_w3")), "target_w5": _f(fe.get("elliott_target_w5"))}
    # v2
    E = EV2.elliott_v2_analysis(x, None, asset, direction); tent = E.get("tent")
    views = {}
    for vn, VN in (("long", "LONG"), ("short", "SHORT")):
        v = E["views"][vn]; b = v.get("best"); pts = []
        if b:
            if b["kind"] == "impulse": labs = [str(k) for k in range(len(b["pivots"]))]
            else: labs = [str(k) for k in range(len(b["base_pivots"]))] + ["A", "B", "C"][:len(b["abc_pivots"])]
            pts = [pv(p, lab, prov=(p[3] is None)) for p, lab in zip(b["pivots"], labs)]
        views[VN] = {"label": v.get("label", "no valid count"), "state": E["cols"][f"ev2_{vn}_state"], "kind": v.get("kind"),
                     "provisional": v.get("provisional"), "beyond_target": v.get("beyond_target"), "abc_type": v.get("abc_type"),
                     "context": v.get("context"), "target": _f(v.get("target")), "target_name": v.get("target_name"), "pivots": pts}
    def fibd(fa, ver, view):
        if not fa or fa.get("origin" if ver == "v2" else "v1_origin") is None: return None
        if ver == "v1":
            return {"version": "v1", "view": view, "origin": {"price": round(fa["v1_origin"], 4), "date": fa["v1_origin_date"]},
                    "end": {"price": round(fa["v1_end"], 4), "date": fa["v1_end_date"]}, "stale": bool(fa.get("stale")), "reanchored": None,
                    "levels": {k: _f(fe.get(f)) for k, f in (("0.382", "fib_r382"), ("0.5", "fib_r500"), ("0.618", "fib_r618"), ("0.786", "fib_r786"),
                                                             ("1.272", "fib_tp_1272"), ("1.618", "fib_tp_1618"))}}
        return {"version": "v2", "view": view, "origin": {"price": round(fa["origin"], 4), "date": fa["origin_date"]},
                "end": {"price": round(fa["end"], 4), "date": fa["end_date"]}, "stale": False, "reanchored": bool(fa.get("reanchored")),
                "levels": {k: (round(fa[f], 4) if fa.get(f) is not None else None) for k, f in (("0.382", "r382"), ("0.5", "r500"), ("0.618", "r618"),
                                                                                                 ("0.786", "r786"), ("1.272", "x1272"), ("1.618", "x1618"))}}
    fa = E["views"]["long" if sgn == 1 else "short"]["fib"]
    # trade (scan output first)
    stp = ST.active_stop(x, asset, direction); last_close = float(c[-1])
    trade = {"entry": _f(entry) if entry is not None else last_close, "entry_ref": "last_close",
             "stop": _f(stop) if stop is not None else _f(stp.get("initial_stop")), "stop_rule": f"{stp.get('stop_type')} {stp.get('stop_atr_mult')}xATR14",
             "target": _f(target) if target is not None else (_f(stp.get("tp_half_1618")) if direction == "LONG" else None),
             "target_rule": "1/2 at Fib 1.618 (close), rest 4xATR chandelier" if direction == "LONG" else "none (4xATR14 chandelier on close)",
             "target_note": target_note}
    vp = GEO.volume_profile(x, None, asset, direction)
    L = {"schema_version": "levels-1.0", "symbol": symbol, "asset": asset, "direction": direction, "scan_type": "SWING", "run_id": run_id,
         "generated_by": "scanner_charts.build_levels (reference producer)",
         "data": {"source": "yahoo daily (auto_adjust) via scanner-momentum-cache pit.history (scanner_stops.daily_bars)", "px_dir": px_dir,
                  "cutoff_utc": cut.isoformat(), "last_bar": _d(x, -1), "n_bars": int(len(x)), "atr14": round(A, 4)},
         "score": {"value": _f(score), "basis": score_basis},
         "trade": trade,
         "pivots": {"zigzag_atr_mult": float(ST.ZZ), "confirmed": [pv(p) for p in known],
                    "tentative": ({"kind": tent[0], "price": round(tent[1], 4), "date": _d(x, tent[2]), "move_atr": round(tent[5], 2),
                                   "back_atr": round(tent[6], 2)} if tent else None)},
         "elliott": {"v1": v1, "v2": {"version": "v2", "primary_view": direction, "views": views}},
         "fib": {"v1": fibd(fa, "v1", direction), "v2": fibd(fa, "v2", direction)},
         "volume_profile": {"version": "scanner_geometry vp120", "window": 120, "poc": _f(vp.get("vp120_poc")), "vah": _f(vp.get("vp120_vah")),
                            "val": _f(vp.get("vp120_val"))},
         "sr": None, "waves": None}
    if sr:
        try:
            import scanner_levels as SL
            lv = SL.levels_for(symbol, cut, "SWING", direction)
            L["sr"] = {"version": "scanner_levels v1", "scan_type": "SWING",
                       "levels": [{"price": o["price"], "side": o["side"], "tf": o["tf"], "strength": o["strength"], "touches": o.get("touches"),
                                   "flip_dir": o.get("flip_dir"), "src": o.get("src"), "confirmed_at": o.get("confirmed_at")} for o in lv["levels"]],
                       "nearest": {k: v for k, v in lv["summary"].items() if k != "sr_levels_json"}}
        except Exception as e: L["sr"] = {"version": "scanner_levels v1", "levels": [], "nearest": {"sr_flag": f"error {e.__class__.__name__}"}}
    if waves:
        import scanner_waves as SW
        WA = SW.waves_analysis(x, None, asset, direction)
        if "ind" in WA:
            wv = lambda w_, px_: {"dir": "up" if w_["dir"] == 1 else "down", "start_date": _d(x, w_["i0"]), "end_date": _d(x, w_["i1"]),
                                  "start_price": round(float(w_["p0"]), 4), "end_price": round(float(w_["p1"]), 4), "volume": float(w_["vol"]), "done": bool(w_["done"])}
            ind = WA["ind"].iloc[-series_bars:]
            divs = []
            for (nm, kind), d_ in WA["divs"].items():
                if d_ and d_["type"]:
                    divs.append({"indicator": nm, "type": d_["type"], "p1": {"date": _d(x, d_["i1"]), "price": round(d_["p1"], 4), "value": round(d_["v1"], 3)},
                                 "p2": {"date": _d(x, d_["i2"]), "price": round(d_["p2"], 4), "value": round(d_["v2"], 3)}, "confirmed_at": _d(x, d_["conf"])})
            cw = WA["cols"]
            L["waves"] = {"version": "scanner_waves v2 (families>=2)", "rev_pct": cw.get("ww_rev_pct"),
                          "zigzag": [wv(w_, None) for w_ in WA["wz"]], "weis": [wv(w_, None) for w_ in WA["ww"]], "divergences": divs,
                          "signals": {k: cw.get(k) for k in ("wave_end_signal", "wave_end_n", "wave_end_families", "wave_end_reasons",
                                                             "wave_start_signal", "wave_start_n", "wave_start_families", "wave_start_reasons",
                                                             "rsi14", "cci20", "crsi")},
                          "series": {"dates": [str(pd.Timestamp(t).date()) for t in ind.index],
                                     **{k: [None if not np.isfinite(v) else round(float(v), 3) for v in ind[k].values] for k in ("rsi14", "cci20", "crsi")}}}
    return L

def validate_levels(L):
    """Light check against levels_schema.json required fields (jsonschema not installed). Returns list of problems."""
    probs = []
    for k in ("schema_version", "symbol", "asset", "direction", "data", "trade", "pivots", "elliott", "fib"):
        if k not in L: probs.append(f"missing {k}")
    if L.get("schema_version") != "levels-1.0": probs.append("schema_version != levels-1.0")
    for k in ("source", "cutoff_utc", "last_bar"):
        if k not in (L.get("data") or {}): probs.append(f"missing data.{k}")
    for k in ("entry", "stop", "target"):
        if k not in (L.get("trade") or {}): probs.append(f"missing trade.{k}")
    e = L.get("elliott") or {}
    if (e.get("v1") or {}).get("version") != "v1" or (e.get("v2") or {}).get("version") != "v2": probs.append("elliott version tags")
    return probs

# ------------------------------------------------------------------ 2) RENDERER: draws ONLY numbers from the levels dict
def render_from_levels(levels, bars_df, out_png, bars=130, max_bars=250, dpi=130, index_path=None):
    """Chart purely from a levels dict / JSON path (levels_schema.json). bars_df = daily OHLCV for candles + volume only; it is cut at
    data.last_bar. No level is recomputed. Returns the chart-index entry (every number drawn); appended to index_path if given."""
    M = _m(); plt = M["plt"]; GEO = M["GEO"]
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    L = json.load(open(levels)) if isinstance(levels, str) else levels
    probs = validate_levels(L)
    if probs: raise ValueError(f"levels file invalid: {probs}")
    symbol, direction = L["symbol"], L["direction"]; sgn = 1 if direction == "LONG" else -1
    x = GEO._norm(bars_df); x = x[x.index <= pd.Timestamp(L["data"]["last_bar"])]
    if not len(x) or str(x.index[-1].date()) != L["data"]["last_bar"]:
        raise ValueError(f"bars_df does not end at data.last_bar {L['data']['last_bar']}")
    pos = {str(t.date()): i for i, t in enumerate(x.index)}
    P_ = lambda d: pos.get(d)
    drawn = {"entry": None, "stop": None, "target": None, "fib_v2": {}, "fib_v1": {}, "vp120": {}, "sr": [], "elliott_v2": [],
             "elliott_v2_other_view": None, "elliott_v1": [], "tentative": None, "zigzag_pivots": 0, "waves_zigzag": [], "waves_weis": [],
             "divergences": [], "off_chart": [], "notes": []}
    notes, off_chart = drawn["notes"], drawn["off_chart"]
    n_all = len(x); T = L["trade"]; ev1 = L["elliott"]["v1"]; ev2v = L["elliott"]["v2"]["views"].get(direction) or {}
    other = "SHORT" if direction == "LONG" else "LONG"; ev2o = L["elliott"]["v2"]["views"].get(other) or {}
    f1, f2 = L["fib"].get("v1"), L["fib"].get("v2")
    need = [n_all - bars]
    for pts in (ev2v.get("pivots") or [], ev1.get("pivots") or []):
        if pts and P_(pts[0]["date"]) is not None: need.append(P_(pts[0]["date"]) - 5)
    for f in (f2,):
        if f and f.get("origin") and P_(f["origin"]["date"]) is not None: need.append(P_(f["origin"]["date"]) - 5)
    i_start = max(0, min(need), n_all - max_bars)
    w = x.iloc[i_start:]; N = len(w); off = i_start
    X = lambda d: (P_(d) - off) if P_(d) is not None else None
    pad = max(28, int(N * 0.17)); xr = N - 1 + pad
    WV = L.get("waves") or None; has_series = bool(WV and WV.get("series") and WV["series"].get("dates"))
    if WV:
        fig = plt.figure(figsize=(15, 13.2), dpi=dpi)
        gs = fig.add_gridspec(5, 1, height_ratios=[4.2, 0.85, 1.0, 0.85, 0.85], hspace=0.05, left=0.055, right=0.86, top=0.93, bottom=0.095)
        ax = fig.add_subplot(gs[0]); av = fig.add_subplot(gs[1], sharex=ax)
        aw = fig.add_subplot(gs[2], sharex=ax); ar = fig.add_subplot(gs[3], sharex=ax); ac = fig.add_subplot(gs[4], sharex=ax); bottom_ax = ac
    else:
        fig = plt.figure(figsize=(15, 9.2), dpi=dpi)
        gs = fig.add_gridspec(2, 1, height_ratios=[4.2, 1], hspace=0.04, left=0.055, right=0.86, top=0.90, bottom=0.105)
        ax = fig.add_subplot(gs[0]); av = fig.add_subplot(gs[1], sharex=ax); bottom_ax = av
    plt.rcParams["font.family"] = "IBM Plex Sans Hebrew"
    o, hi, lo, cl, vol = (w[k].values for k in ("Open", "High", "Low", "Close", "Volume"))
    xs = np.arange(N); up = cl >= o; col = np.where(up, C_UP, C_DN)
    ax.vlines(xs, lo, hi, color=col, linewidth=0.8, zorder=3)
    ax.bar(xs, np.maximum(np.abs(cl - o), (hi.max() - lo.min()) * 0.0008), bottom=np.minimum(o, cl), width=0.65, color=col, edgecolor=col, linewidth=0.4, zorder=4)
    av.bar(xs, vol, width=0.7, color=col, alpha=0.55)
    av.plot(xs, pd.Series(vol).rolling(20).mean().values, color="#424242", lw=0.9)
    av.set_ylabel("Volume", fontsize=8); av.tick_params(labelsize=7)
    vfmt = M["matplotlib"].ticker.FuncFormatter(lambda v, _: f"{v/1e6:.0f}M" if v >= 1e6 else f"{v/1e3:.0f}K")
    av.yaxis.set_major_formatter(vfmt)
    ymin_c, ymax_c = float(lo.min()), float(hi.max()); span_c = ymax_c - ymin_c
    inrange = lambda v, k=0.45: v is not None and (ymin_c - k * span_c) <= v <= (ymax_c + k * span_c)
    labels_right = []
    # VP120
    VP = L.get("volume_profile") or {}
    poc, vah, val = VP.get("poc"), VP.get("vah"), VP.get("val")
    if poc is not None:
        x0 = max(0, N - int(VP.get("window") or 120)) - 0.5
        ax.fill_between([x0, N - 0.5], val, vah, color=C_VA, alpha=0.22, zorder=1, lw=0)
        ax.plot([x0, xr], [poc, poc], color=C_POC, lw=1.6, alpha=0.9, zorder=2)
        for v_ in (vah, val): ax.plot([x0, N - 0.5], [v_, v_], color=C_POC, lw=0.7, ls=":", zorder=2)
        labels_right += [(poc, f"VP120 POC {_fmt(poc)}", C_POC), (vah, f"VAH {_fmt(vah)}", C_POC), (val, f"VAL {_fmt(val)}", C_POC)]
        drawn["vp120"] = {"poc": poc, "vah": vah, "val": val}
    # S/R
    SR = (L.get("sr") or {}).get("levels") or []
    if SR:
        smax = max([s_.get("strength") or 0 for s_ in SR] + [1e-9])
        for s_ in SR:
            p = s_.get("price")
            if not inrange(p, 0.25): off_chart.append(f"SR {p}"); continue
            tf = s_.get("tf", "D"); c_ = {"W": C_SR_W, "M": C_SR_M, "D": C_SR_D}.get(tf, C_SR_I)
            ax.plot([-0.5, N - 0.5], [p, p], color=c_, lw=0.8 + 3.2 * (s_.get("strength") or 0) / smax, alpha=0.35, zorder=1.5, solid_capstyle="butt")
            labels_right.append((p, f"{'S' if s_.get('side') == 'support' else 'R'}-{tf} {_fmt(p)}{' flip' if s_.get('flip_dir') else ''} ({(s_.get('strength') or 0):.1f})", c_))
            drawn["sr"].append({"price": p, "tf": tf, "strength": s_.get("strength"), "side": s_.get("side")})
    # zigzag (confirmed) + tentative (dashed, provisional)
    conf = L["pivots"]["confirmed"]; vis = [p for p in conf if P_(p["date"]) is not None and P_(p["date"]) >= i_start]
    prev = [p for p in conf if P_(p["date"]) is not None and P_(p["date"]) < i_start]
    pts = ([prev[-1]] if prev else []) + vis; drawn["zigzag_pivots"] = len(vis)
    if pts:
        ax.plot([X(p["date"]) for p in pts], [p["price"] for p in pts], color=C_ZZ, lw=1.1, alpha=0.75, zorder=5)
        ax.scatter([X(p["date"]) for p in vis], [p["price"] for p in vis], s=14, color=C_ZZ, zorder=6)
    tent = L["pivots"].get("tentative"); last_close = float(cl[-1])
    if conf:
        lp = conf[-1]
        if tent and X(tent["date"]) is not None:
            ax.plot([X(lp["date"]), X(tent["date"])], [lp["price"], tent["price"]], color=C_ZZ, lw=1.3, ls="--", alpha=0.8, zorder=5)
            ax.scatter([X(tent["date"])], [tent["price"]], s=40, facecolors="white", edgecolors=C_ZZ, linewidths=1.3, zorder=7)
            ax.annotate("provisional", (X(tent["date"]), tent["price"]), xytext=(0, -14 if tent["kind"] == "L" else 10), textcoords="offset points",
                        fontsize=7, color="#546e7a", ha="center", style="italic")
            ax.plot([X(tent["date"]), N - 1], [tent["price"], last_close], color=C_ZZ, lw=0.8, ls=":", alpha=0.6, zorder=5)
            drawn["tentative"] = {"kind": tent["kind"], "price": tent["price"], "date": tent["date"]}
        elif X(lp["date"]) is not None:
            ax.plot([X(lp["date"]), N - 1], [lp["price"], last_close], color=C_ZZ, lw=1.0, ls="--", alpha=0.6, zorder=5)
    # Fib: v2 labelled; v1 faint when it differs (stale)
    def fib_lines(f, labelled, tag):
        if not f or not f.get("origin"): return
        o_, e_ = f["origin"]["price"], f["end"]["price"]; xo, xe = X(f["origin"]["date"]), X(f["end"]["date"])
        out = {"origin": o_, "end": e_}
        if xo is not None and xe is not None:
            ax.plot([xo, xe], [o_, e_], color=C_FIB if labelled else "#b0bec5", lw=1.4 if labelled else 1.0, ls="-.", alpha=0.85 if labelled else 0.6, zorder=6)
        xf = (xe if xe is not None else 0) - 0.5
        lv = [("0 (end)", e_), ("1 (origin)", o_)] + [(k, v) for k, v in (f.get("levels") or {}).items()]
        for nm, v in lv:
            if v is None: continue
            isext = nm in ("1.272", "1.618")
            if not inrange(v): off_chart.append(f"Fib {tag} {nm} {_fmt(v)}"); continue
            if labelled:
                c_ = C_EXT if isext else C_FIB
                ax.plot([xf, xr], [v, v], color=c_, lw=1.0 if isext else 1.1, ls="--" if isext else (":" if nm.startswith(("0 (", "1 (")) else "-"), alpha=0.9, zorder=2)
                labels_right.append((v, f"Fib{'' if tag == 'v1' else ' v2'} {('ext ' if isext else '') + nm}  {_fmt(v)}", c_))
            elif nm == "1 (origin)":
                ax.plot([xf, N - 0.5], [v, v], color="#b0bec5", lw=0.9, ls=":", zorder=2)
                labels_right.append((v, f"v1 Fib 1.0 (broken) {_fmt(v)}", "#90a4ae"))
            out[nm] = v
        drawn["fib_" + tag] = out
    if f2 and f1 and f2.get("reanchored"):
        fib_lines(f2, True, "v2"); fib_lines(f1, False, "v1")
        notes.append(f"Fib v1 leg stale (origin {_fmt(f1['origin']['price'])} broken) -> v2 re-anchored {f2['origin']['date']}..{f2['end']['date']}")
    elif f2:
        fib_lines(f2, True, "v1" if not f2.get("reanchored") else "v2")
    elif f1:
        fib_lines(f1, True, "v1")
        if f1.get("stale"): notes.append("Fib v1 leg stale and no valid v2 anchor")
    else: notes.append("no Fib anchor")
    # entry / stop / target
    xs0 = max(0, N - 30) - 0.5
    for key, nm, v, c_, lw in (("entry", "ENTRY (last close)", T.get("entry"), C_ENTRY, 1.6), ("stop", "STOP 4xATR14", T.get("stop"), C_STOP, 2.0),
                                ("target", "TARGET (1/2 at Fib 1.618)" if direction == "LONG" else "TARGET", T.get("target"), C_TGT, 2.0)):
        if v is None: continue
        if not inrange(v, 0.8): off_chart.append(f"{nm} {_fmt(v)}"); continue
        ax.plot([xs0, xr], [v, v], color=c_, lw=lw, zorder=7); labels_right.append((v, f"{nm}  {_fmt(v)}", c_)); drawn[key] = v
    if direction == "SHORT" and T.get("target") is None: notes.append("SHORT: no fixed target - 4xATR14 chandelier on close (approved rule)")
    ys = [ymin_c, ymax_c] + [v for v, _, _ in labels_right]
    ylo, yhi = min(ys), max(ys); m_ = (yhi - ylo) * 0.04
    ax.set_ylim(ylo - m_ * 3.2, yhi + m_ * 2.4); ax.set_xlim(-1, xr)
    yspan = ax.get_ylim()[1] - ax.get_ylim()[0]
    # Elliott v2 (strong) + v1 (light, shifted)
    for p in ev1.get("pivots") or []:
        xp = X(p["date"])
        if xp is None: continue
        yy = p["price"] + (0.085 if p["kind"] == "H" else -0.085) * yspan
        ax.annotate(p["label"], (xp, p["price"]), xytext=(xp + 2.2, yy), ha="center", va="center", fontsize=8, color="white", zorder=8,
                    bbox=dict(boxstyle="circle,pad=0.2", fc="#b0bec5", ec="white", lw=0.8), arrowprops=dict(arrowstyle="-", color="#b0bec5", lw=0.6))
        drawn["elliott_v1"].append({"label": p["label"], "date": p["date"], "price": p["price"]})
    for p in ev2v.get("pivots") or []:
        xp = X(p["date"])
        if xp is None: continue
        isabc = p["label"] in ("A", "B", "C"); prov = bool(p.get("provisional"))
        fc = (C_ABC if isabc else C_EW) if not prov else "white"; tc = "white" if not prov else (C_ABC if isabc else C_EW)
        yy = p["price"] + (0.045 if p["kind"] == "H" else -0.045) * yspan
        ax.annotate(p["label"] + ("?" if prov else ""), (xp, p["price"]), xytext=(xp, yy), ha="center", va="center", fontsize=11.5, fontweight="bold",
                    color=tc, zorder=9, bbox=dict(boxstyle="circle,pad=0.25", fc=fc, ec=(C_ABC if isabc else C_EW), lw=1.3, ls="--" if prov else "-"),
                    arrowprops=dict(arrowstyle="-", color=C_ABC if isabc else C_EW, lw=0.8, ls="--" if prov else "-"))
        drawn["elliott_v2"].append({"label": p["label"], "date": p["date"], "price": p["price"], "provisional": prov})
    t2 = ev2v.get("label") or "no valid count"
    ew_txt = (f"Elliott v2 ({direction} view): {t2}" + (f"  |  target {ev2v.get('target_name')} {_fmt(ev2v.get('target'))}" if ev2v.get("target") is not None else "")
              + f"\nElliott v2 ({other} view): {ev2o.get('label') or 'no valid count'}"
              + f"\nElliott v1 (scanner, {ev1.get('view')} view, grey): {ev1.get('label')}"
              + "\nblue = impulse 0-5 (0 = wave-1 origin), orange = A-B-C, dashed '?' = provisional (tentative pivot, not confirmed)")
    drawn["elliott_v2_label"] = t2; drawn["elliott_v2_other_view"] = ev2o.get("label"); drawn["elliott_v1_label"] = ev1.get("label")
    ax.text(0.008, 0.015, ew_txt, transform=ax.transAxes, fontsize=7.9, color=C_EW if ev2v.get("pivots") else "#b71c1c", va="bottom", zorder=12,
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=C_EW, alpha=0.92))
    # right labels
    labels_right.sort(key=lambda t: t[0]); yr = ax.get_ylim(); gap = (yr[1] - yr[0]) * 0.026; placed = []
    for v, t, c_ in labels_right: placed.append(v if not placed or v - placed[-1] >= gap else placed[-1] + gap)
    shift = max(0.0, placed[-1] - yr[1] + gap * 0.5) if placed else 0
    for (v, t, c_), y_ in zip(labels_right, placed):
        ax.annotate(t, (N - 0.5 + pad * 0.02, v), xytext=(N - 1 + pad, y_ - shift), fontsize=7.6, color=c_, va="center", ha="left",
                    annotation_clip=False, arrowprops=dict(arrowstyle="-", color=c_, lw=0.5, alpha=0.6))
    ax.grid(alpha=0.18); av.grid(alpha=0.15); ax.tick_params(labelsize=8, labelbottom=False)
    ax.set_ylabel("Price (USD, split/div-adjusted)", fontsize=8)
    ax.axvline(N - 0.5, color="#9e9e9e", lw=0.8, ls=":", zorder=1); ax.text(N - 0.6, yr[1], " cutoff ", fontsize=7, color="#757575", ha="right", va="top")
    # waves / indicators
    if WV:
        for wz in WV.get("zigzag") or []:
            a0, a1 = P_(wz["start_date"]), P_(wz["end_date"])
            if a0 is None or a1 is None or a1 < off: continue
            idx = np.arange(max(a0 + 1, off), a1 + 1); allv = x.Volume.values[a0 + 1:a1 + 1].astype(float)
            cum = np.cumsum(allv)[-len(idx):] if len(idx) else []
            c_ = C_UP if wz["dir"] == "up" else C_DN
            if len(idx): aw.bar(idx - off, cum, width=0.85, color=c_, alpha=0.55 if wz["done"] else 0.3, edgecolor="none")
            aw.text(a1 - off, wz["volume"], f"{wz['volume']/1e6:.0f}M" if wz["volume"] >= 1e6 else f"{wz['volume']/1e3:.0f}K", fontsize=6.6,
                    ha="center", va="bottom", color=c_, fontweight="bold" if wz["done"] else "normal")
            drawn["waves_zigzag"].append({"end_date": wz["end_date"], "volume": wz["volume"], "done": wz["done"]})
        for ww in WV.get("weis") or []:
            a1 = P_(ww["end_date"])
            if a1 is not None and a1 >= off and ww["done"]:
                aw.scatter([a1 - off], [ww["volume"]], marker="_", s=60, color="#424242", lw=1.2, zorder=5)
                drawn["waves_weis"].append({"end_date": ww["end_date"], "volume": ww["volume"]})
        aw.set_ylim(0, aw.get_ylim()[1] * 1.18); aw.set_ylabel("Weis vol\nwaves", fontsize=7.5); aw.tick_params(labelsize=6.5); aw.grid(alpha=0.15)
        aw.yaxis.set_major_formatter(vfmt)
        sg = WV.get("signals") or {}
        aw.text(0.005, 0.97, f"zigzag waves (bars = cum. volume per swing; '-' = classic Weis {WV.get('rev_pct')}% totals)   "
                f"WAVE END: {'YES' if sg.get('wave_end_signal') else 'no'} ({sg.get('wave_end_n')} families)   "
                f"WAVE START: {'YES' if sg.get('wave_start_signal') else 'no'} ({sg.get('wave_start_n')} families)",
                transform=aw.transAxes, fontsize=7, va="top", color="#37474f", bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
        k_ = 0
        for nm, key, fam in (("END", "wave_end_reasons", "wave_end_families"), ("START", "wave_start_reasons", "wave_start_families")):
            if sg.get(key):
                fig.text(0.055, 0.058 - k_ * 0.013, f"wave {nm} [{sg.get(fam) or ''}]: {sg[key]}"[:235], fontsize=7.0, color=C_DN if nm == "END" else C_UP); k_ += 1
        if has_series:
            S_ = WV["series"]; xi = np.array([P_(d) - off if P_(d) is not None else np.nan for d in S_["dates"]], float)
            arr = lambda k: np.array([np.nan if v is None else v for v in S_.get(k) or []], float)
            m = xi >= 0
            ar.plot(xi[m], arr("rsi14")[m], color="#5e35b1", lw=1.1, label="RSI14 (Wilder)")
            if S_.get("crsi"): ar.plot(xi[m], arr("crsi")[m], color="#9e9e9e", lw=0.7, alpha=0.8, label="Connors RSI 3/2/100")
            for y_ in (30, 70): ar.axhline(y_, color="#bdbdbd", lw=0.7, ls="--")
            ar.set_ylim(0, 100); ar.legend(loc="upper left", fontsize=6.3, ncol=2, framealpha=0.7)
            ac.plot(xi[m], arr("cci20")[m], color="#00838f", lw=1.0)
            for y_ in (-100, 100): ac.axhline(y_, color="#bdbdbd", lw=0.7, ls="--")
            ac.axhline(0, color="#e0e0e0", lw=0.6)
        else:
            for a_ in (ar, ac): a_.text(0.5, 0.5, "indicator series not in levels file", transform=a_.transAxes, ha="center", fontsize=8, color="#9e9e9e")
        ar.set_ylabel("RSI", fontsize=7.5); ac.set_ylabel("CCI", fontsize=7.5)
        for a_ in (ar, ac): a_.tick_params(labelsize=6.5); a_.grid(alpha=0.15)
        for d_ in WV.get("divergences") or []:
            x1, x2 = X(d_["p1"]["date"]), X(d_["p2"]["date"])
            if x1 is None or x2 is None or x1 < 0: continue
            bear = "bear" in d_["type"]; c_ = C_DN if bear else C_UP; ls = "-" if d_["type"].startswith("regular") else "--"
            axi = ar if d_["indicator"] == "rsi14" else ac
            axi.plot([x1, x2], [d_["p1"]["value"], d_["p2"]["value"]], color=c_, lw=1.6, ls=ls, zorder=6)
            axi.text(x2 + 0.5, d_["p2"]["value"], d_["type"].replace("_", " "), fontsize=6.3, color=c_, va="center")
            ax.plot([x1, x2], [d_["p1"]["price"], d_["p2"]["price"]], color=c_, lw=1.3, ls=ls, alpha=0.8, zorder=8)
            drawn["divergences"].append({"indicator": d_["indicator"], "type": d_["type"], "p1": d_["p1"], "p2": d_["p2"]})
        for a_ in (aw, ar, ac): a_.axvline(N - 0.5, color="#9e9e9e", lw=0.8, ls=":")
    step = max(1, N // 12); ticks = list(range(0, N, step))
    for a_ in fig.axes:
        if a_ is not bottom_ax: a_.tick_params(labelbottom=False)
    bottom_ax.set_xticks(ticks); bottom_ax.set_xticklabels([w.index[i].strftime("%d.%m.%y") for i in ticks], fontsize=7.5)
    # title
    dcol = C_UP if direction == "LONG" else C_DN; sc_ = (L.get("score") or {}).get("value"); basis = (L.get("score") or {}).get("basis")
    ty, sy = (0.968, 0.945) if WV else (0.955, 0.918)
    fig.text(0.055, ty, symbol, fontsize=22, fontweight="bold", va="center")
    fig.text(0.055 + 0.012 * max(3, len(symbol)) + 0.02, ty, f" {direction} ", fontsize=13, fontweight="bold", color="white", va="center",
             bbox=dict(boxstyle="round,pad=0.3", fc=dcol, ec=dcol))
    cut_il = pd.Timestamp(L["data"]["cutoff_utc"]).tz_convert("Asia/Jerusalem")
    fig.text(0.215, ty, f"score {_fmt(sc_) if sc_ is not None else '-'}" + (f" ({basis})" if basis else "") +
             f"   |   last bar {pd.Timestamp(L['data']['last_bar']):%d.%m.%Y}   |   scan cutoff {cut_il:%d.%m.%Y %H:%M} IL   |   ATR14 {_fmt(L['data'].get('atr14'))}",
             fontsize=10, va="center", color="#37474f")
    research = L.get('research_score') or {}
    score_note = (f"Experimental research: {research.get('effective_research_weight', 0):.1%} effective; "
                  f"delta {research.get('delta_points', 0):+.2f}; unvalidated." if research else
                  "No weighted research overlay in this snapshot.")
    fig.text(0.055, sy, f"Drawn from {L['schema_version']}; bars through {L['data']['last_bar']}. " + score_note,
             fontsize=7.6, va="center", color="#616161")
    foot = ([f"off chart: {'; '.join(off_chart)}"] if off_chart else []) + (["; ".join(notes)] if notes else [])
    if foot: fig.text(0.055, 0.03 if WV else 0.008, "  |  ".join(foot)[:260], fontsize=7.3, color="#6d4c41")
    hs = [Line2D([], [], color=C_ZZ, lw=1.1, label="2xATR zigzag"), Line2D([], [], color=C_ZZ, lw=1.1, ls="--", label="tentative (provisional)"),
          Line2D([], [], color=C_FIB, lw=1, label="Fib retracement"), Line2D([], [], color=C_EXT, lw=1, ls="--", label="Fib extension"),
          Line2D([], [], color=C_POC, lw=1.6, label="VP120 POC"), Patch(color=C_VA, alpha=0.4, label="VP120 value area"),
          Line2D([], [], color=C_STOP, lw=2, label="stop"), Line2D([], [], color=C_TGT, lw=2, label="target")]
    if SR: hs += [Line2D([], [], color=C_SR_D, lw=2.5, alpha=0.5, label="S/R daily"), Line2D([], [], color=C_SR_W, lw=2.5, alpha=0.5, label="S/R weekly")]
    fig.legend(handles=hs, loc="lower center", bbox_to_anchor=(0.46, 0.004 if WV else 0.022), fontsize=7.2, ncol=len(hs), frameon=False)
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    fig.savefig(out_png, dpi=dpi); plt.close(fig)
    entry = {"symbol": symbol, "direction": direction, "png": out_png, "levels_schema": L["schema_version"], "levels_generated_by": L.get("generated_by"),
             "levels_file": levels if isinstance(levels, str) else None, "cutoff_utc": L["data"]["cutoff_utc"], "last_bar": L["data"]["last_bar"],
             "window": [str(w.index[0].date()), str(w.index[-1].date())], "drawn": drawn}
    if index_path:
        idx = json.load(open(index_path)) if os.path.exists(index_path) else []
        idx = [e for e in idx if not (e.get("symbol") == symbol and e.get("direction") == direction)] + [entry]
        json.dump(idx, open(index_path, "w"), ensure_ascii=False, indent=1, default=str)
    return entry

def render_setup_chart(symbol, cutoff, direction, out_png, levels_out=None, index_path=None, **kw):
    """Convenience: build_levels() (scanner functions) -> optional JSON -> render_from_levels() (pure drawing)."""
    M = _m(); ST, SM = M["ST"], M["SM"]
    cut = _utc(cutoff); asset = kw.get("asset", "stock")
    px_dir = kw.get("px_dir") or f"{SM.CACHE_ROOT}/{cut.strftime('%Y%m%dT%H%MZ')}"
    bars = ST.daily_bars(symbol, asset, cut, px_dir)
    L = build_levels(symbol, cut, direction, bars_df=bars, **{k: v for k, v in kw.items() if k in (
        "asset", "px_dir", "score", "score_basis", "entry", "stop", "target", "target_note", "sr", "waves", "run_id")})
    if levels_out:
        os.makedirs(os.path.dirname(os.path.abspath(levels_out)), exist_ok=True)
        json.dump(L, open(levels_out, "w"), ensure_ascii=False, indent=1, default=str)
    return render_from_levels(levels_out or L, bars, out_png, index_path=index_path), L

# ------------------------------------------------------------------ batch for a scan run
def run_cutoff(run_dir):
    s = pd.read_csv(f"{run_dir}/scan_raw.csv", usecols=["t", "asof_utc"]).dropna()
    return pd.Timestamp(s["asof_utc"].mode().iloc[0]).tz_localize("UTC")

def render_run(run_dir, n=None, sr=True, pdf=True):
    """Charts for the candidates the platform layer used. If <run_dir>/levels/<T>.json exists (unified-scan output) it is drawn as is;
    otherwise the reference producer writes <run_dir>/charts/levels_built/<T>_<dir>.json and that file is drawn."""
    M = _m(); ST, SM = M["ST"], M["SM"]
    cut = _utc(run_cutoff(run_dir)); px_dir = f"{SM.CACHE_ROOT}/{cut.strftime('%Y%m%dT%H%MZ')}"
    p = pd.read_csv(f"{run_dir}/platform_enrichment.csv")
    if n: p = p.head(n)
    index_path = f"{run_dir}/charts/chart_index.json"
    if os.path.exists(index_path): os.remove(index_path)
    items = []
    for _, r in p.iterrows():
        t, d = r["t"], str(r["direction"]).upper(); png = f"{run_dir}/charts/{t}_{d.lower()}.png"
        bars = ST.daily_bars(t, "stock", cut, px_dir)
        ext = f"{run_dir}/levels/{t}.json"
        if os.path.exists(ext) and json.load(open(ext)).get("direction") == d:
            lf = ext
        else:
            lf = f"{run_dir}/charts/levels_built/{t}_{d.lower()}.json"
            basis = str(r.get("rank_basis", "")).split(" (")[0].split(",")[-1].strip() or None
            L = build_levels(t, cut, d, bars_df=bars, score=r.get("rank_score"), score_basis=basis, entry=r.get("entry"), stop=r.get("stop"),
                             target=r.get("target") if pd.notna(r.get("target")) else None, target_note=r.get("target_note"), sr=sr,
                             run_id=os.path.basename(run_dir.rstrip("/")))
            os.makedirs(os.path.dirname(lf), exist_ok=True); json.dump(L, open(lf, "w"), ensure_ascii=False, indent=1, default=str)
        e = render_from_levels(lf, bars, png, index_path=index_path)
        items.append(dict(e, L=json.load(open(lf))))
        dv = e["drawn"]
        print(f"{t:6s} {d:5s} v2={dv['elliott_v2_label']} | other={dv['elliott_v2_other_view']} | v1={dv['elliott_v1_label']} | notes={dv['notes']}", flush=True)
    if pdf: build_pdf(run_dir, items, cut)
    return items

def build_pdf(run_dir, items, cut):
    """One chart per A4-portrait page + Hebrew caption built ONLY from the levels file of that chart (bidi checked visually)."""
    M = _m(); plt = M["plt"]
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.image as mpimg
    plt.rcParams["font.family"] = "IBM Plex Sans Hebrew"
    pdf_path = f"{run_dir}/charts_he.pdf"; cut_il = cut.tz_convert("Asia/Jerusalem")
    dir_he = {"LONG": "לונג", "SHORT": "שורט"}; tfh = {"D": "יומי", "W": "שבועי", "M": "חודשי"}; yn = lambda b: "כן" if b else "לא"
    with PdfPages(pdf_path) as pdf:
        fig = plt.figure(figsize=(11.69, 8.27))
        Lg = [("גרפי סטאפים - ריצת ניסיון", 24, "bold"),
              (f"חיתוך הסריקה: {cut_il:%d.%m.%Y %H:%M} (שעון ישראל) · נר אחרון: {items[0]['last_bar'] if items else '-'}", 13, "normal"),
              ("", 10, "normal"), ("מה רואים בכל גרף", 15, "bold"),
              ("• נרות יומיים עד רגע החיתוך בלבד, ומתחת - נפח מסחר. כל הרמות מצוירות מקובץ הרמות של הסריקה, בלי חישוב מחדש.", 12, "normal"),
              ("• קו אפור: נקודות המפנה של ה-zigzag (סף ATR×2) שאושרו. קו מקווקו ועיגול חלול: נקודת מפנה זמנית שעוד לא אושרה (provisional).", 12, "normal"),
              ("• עיגולים כחולים 0-5: ספירת אליוט v2 (0 = תחילת גל 1). כתום A-B-C: גל תיקון. סימן '?' ומסגרת מקווקוות = זמני.", 12, "normal"),
              ("• עיגולים אפורים קטנים: הספירה הישנה (v1) של הסורק, להשוואה.", 12, "normal"),
              ("• סגול: רמות פיבונאצ'י 0.382-0.786; ירוק-כהה מקווקו: הרחבות 1.272/1.618. אם הרגל הישנה נשברה - עיגון מחדש (v2).", 12, "normal"),
              ("• כתום: POC של פרופיל הנפח ל-120 יום, והרצועה הבהירה = אזור הערך (VAL-VAH).", 12, "normal"),
              ("• שחור = כניסה (סגירה אחרונה), אדום = סטופ ATR14×4, ירוק = יעד (חצי ב-Fib 1.618, לונג בלבד). בשורט אין יעד קבוע.", 12, "normal"),
              ("• קווים רחבים שקופים: תמיכה/התנגדות היסטורית - חום = יומי, כחול = שבועי. קו עבה יותר = רמה חזקה יותר.", 12, "normal"),
              ("• פאנל גלי נפח (Weis), ופאנלים של RSI14, Connors RSI ו-CCI20 עם קווי דיברגנס (אדום = דובי, ירוק = שורי).", 12, "normal"),
              ("• סימן סוף/תחילת גל נדלק רק כשיש לפחות 2 משפחות סימנים בלתי תלויות.", 12, "normal"),
              ("", 10, "normal"),
              ("הניקוד כולל שכבת מחקר אם נשמרה בריצה; המשקל והתרומה מופיעים בכל גרף. המשקולות ניסיוניות.", 12, "bold")]
        y = 0.92
        for t, fs, fw in Lg:
            fig.text(0.94, y, heb(t), ha="right", va="top", fontsize=fs, fontweight=fw); y -= 0.042 if fs < 20 else 0.065
        pdf.savefig(fig); plt.close(fig)
        for it in items:
            L = it["L"]; T = L["trade"]; d = L["direction"]; dv = it["drawn"]
            fig = plt.figure(figsize=(8.27, 11.69))
            img = mpimg.imread(it["png"]); ar_ = img.shape[0] / img.shape[1]; wd = 0.98; ht = wd * ar_ * 8.27 / 11.69
            axi = fig.add_axes([0.01, 0.985 - ht, wd, ht]); axi.imshow(img); axi.axis("off")
            sc = (L.get("score") or {}).get("value")
            tgt = (f"{_fmt(T['target'])} (חצי ביעד Fib 1.618 על סגירה, השאר בשנדלייר ATR×4)" if T.get("target") is not None
                   else "אין יעד קבוע - שנדלייר ATR14×4 על סגירה")
            v2 = L["elliott"]["v2"]["views"]; oth = "SHORT" if d == "LONG" else "LONG"
            vp = L.get("volume_profile") or {}
            lines = [f"מניה {L['symbol']} · {dir_he.get(d, d)} · ציון {_fmt(sc) if sc is not None else '-'}",
                     f"כניסה (סגירה אחרונה): {_fmt(T.get('entry'))}   ·   סטופ ATR14×4: {_fmt(T.get('stop'))}   ·   יעד: {tgt}",
                     f"אליוט v2 (מבט {dir_he[d]}): {(v2.get(d) or {}).get('label', 'אין ספירה תקפה')}",
                     f"אליוט v2 (מבט {dir_he[oth]}): {(v2.get(oth) or {}).get('label', 'אין ספירה תקפה')}",
                     f"אליוט v1 (הספירה הנוכחית של הסורק): {L['elliott']['v1'].get('label')}",
                     f"נקודת השליטה בפרופיל הנפח (POC) ל-120 יום: {_fmt(vp.get('poc'))} (אזור ערך {_fmt(vp.get('val'))} - {_fmt(vp.get('vah'))})"]
            rs = L.get('research_score') or {}
            if rs:
                lines.insert(1, f"מחקר ניסיוני: בסיס {_fmt(rs.get('baseline_score'))} · שינוי {_fmt(rs.get('delta_points'))} נקודות · משקל בפועל {rs.get('effective_research_weight', 0):.1%}")
            f1, f2 = L["fib"].get("v1"), L["fib"].get("v2")
            if f2 and f2.get("reanchored"):
                lines.append(f"פיבונאצ'י: הרגל הישנה נשברה (מוצא {_fmt(f1['origin']['price'])}) - עוגן חדש {_fmt(f2['origin']['price'])} עד {_fmt(f2['end']['price'])}")
            s_ = ((L.get("sr") or {}).get("nearest")) or {}
            if s_.get("sr_support") is not None or s_.get("sr_resistance") is not None:
                def _lv(side):
                    p_ = _f(s_.get(f"sr_{side}"))
                    if p_ is None: return "אין"
                    fl = " (היפוך)" if s_.get(f"sr_{side}_flip") else ""
                    return f"{_fmt(p_)} ({tfh.get(s_.get(f'sr_{side}_tf'), s_.get(f'sr_{side}_tf'))}, {abs(_f(s_.get(f'sr_{side}_dist_atr')) or 0):.2f} ATR, חוזק {s_.get(f'sr_{side}_strength')}){fl}"
                lines.append(f"תמיכה קרובה: {_lv('support')}   ·   התנגדות קרובה: {_lv('resistance')}")
            sg = ((L.get("waves") or {}).get("signals")) or {}
            if sg:
                lines.append(f"גלי נפח: סוף גל בכיוון העסקה - {yn(sg.get('wave_end_signal'))} ({sg.get('wave_end_n')} משפחות) · תחילת גל - "
                             f"{yn(sg.get('wave_start_signal'))} ({sg.get('wave_start_n')} משפחות)   ·   RSI14 {sg.get('rsi14')} · CCI20 {sg.get('cci20')} · Connors RSI {sg.get('crsi')}")
            for k, t in enumerate(lines):
                fig.text(0.96, 0.985 - ht - 0.02 - k * 0.028, heb(t), ha="right", va="top", fontsize=14 if k == 0 else 9.2, fontweight="bold" if k == 0 else "normal")
            pdf.savefig(fig); plt.close(fig)
    print("PDF ->", pdf_path)
    return pdf_path

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", required=True); ap.add_argument("--n", type=int); ap.add_argument("--no-sr", action="store_true", help="skip scanner_levels S/R")
    a = ap.parse_args()
    render_run(a.run_dir, a.n, sr=not a.no_sr)
