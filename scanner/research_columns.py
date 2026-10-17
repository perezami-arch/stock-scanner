"""EXPERIMENTAL research-tool columns for the unified scanner (built 08.10.2026 for Ilan / room "בניית מודל סורק לשוק ההון").
LOGGED ONLY - weight 0 in the score, never changes entry/stop/target. Measured forward from new setups on/after 2026-10-12
(tool_stats.py); a tool earns weight only after it works out-of-sample (15 results = interim check, 30 = decision).

API (same style as scanner_geometry.geometry_columns):
    import research_columns as RC
    RC.reset_budget()                                   # once per scan (total time budget, default 300 s)
    cols = RC.compute_all(df, cutoff, asset, direction)  # one ticker -> {exp_<tool>_*: value, exp_<tool>_status: 'ok'|error}
    rows = RC.compute_many([(key, df, cutoff, asset, direction), ...], workers=2)   # faster for a whole scan
    df   : daily OHLCV, DatetimeIndex = bar date (columns Open/High/Low/Close/Volume, any case)
    cutoff: tz-aware Timestamp (naive = UTC) = the alert / scan moment; None = frame already cut
    asset : 'stock' | 'crypto';  direction: 'LONG' | 'SHORT'
Every tool function has the signature fn(df, cutoff, asset, direction) -> dict and FIRST cuts the frame point-in-time with
scanner_geometry.pit_cut (stock: bar D visible only once D 16:00 ET <= cutoff -> an alert before/during the session sees the
previous close, after the close the alert-day candle; crypto: 24h bar visible once bar start + 24h <= cutoff = alert minute).

Isolation: every tool runs inside try/except (and a per-call time limit). A failing tool fills ALL its columns with NaN and
puts the error into exp_<tool>_status; the scan never crashes. Tools whose libraries are not importable in the calling
interpreter (TA-Lib / pandas-ta / smc / Elliott live in /workspace/ta-repos-eval/venv) run in a persistent worker subprocess
of that venv (data exchanged as plain Python lists via pickle; no network, no secrets).

Tools (prefix -> what, PIT handling):
  exp_talib_   TA-Lib 0.8.1 indicators + all 61 candle patterns on the cut frame (leak test: 0 leaks / 233 outputs).
  exp_pta_     pandas-ta 0.4.71b0 (version pinned; DPO, Ichimoku chikou, ZIGZAG, TOS_STDEVALL and every other blocked
               function raise before running - they read later bars or repaint).
  exp_smc_     smart-money-concepts 0.0.27 through the PIT wrapper of ta-repos-eval/features_smc.py: run on the cut frame only,
               artificial swings on bar 0 / the last bar removed, an FVG/OB/liquidity level is 'open' only if not mitigated
               up to the cutoff.
  exp_taew_    python-taew (MIT), fed only bars <= cutoff (its pivots need 1 later bar -> never on the last cut bar).
  exp_ewa_     ElliottWaveAnalyzer (drstevendev) - NO LICENSE: INTERNAL USE ONLY (never vendor / publish / ship).
               Waves ending on the last bar are treated as in progress.
  exp_ewaves_  ElliottWaves (alessioricco, MIT): argrelextrema(order=7) pivots in the last 7 cut bars are dropped (provisional).
  exp_qlib_    Qlib Alpha158 + LightGBM score. Trained OFFLINE each night (research_nightly/qlib_nightly.py, labels realised
               before the bar), the scan only reads the prediction for (ticker, last visible bar) - stale/missing -> NaN.
  exp_finrl_   FinRL PPO (2048 steps) action for the ticker on the last visible bar, same nightly pattern.
OpenBB (exp_openbb_*) is built separately by the scanner agent (/workspace/openbb_snapshot.py) and is not part of this module.
"""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, sys, io, time, json, math, pickle, struct, signal, threading, contextlib, importlib.util, subprocess, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, _SCANNER_ROOT)
import scanner_geometry as GEO            # read-only use: pit_cut / atr14 (same as the stops + geometry columns)

VERSION = "2026-10-08.1"
TA_VENV = (_SCANNER_ROOT + "/ta-repos-eval/venv/bin/python")
TA_DIR = (_SCANNER_ROOT + "/ta-repos-eval")
MODEL_DIR = (_SCANNER_ROOT + "/research-models")
PANDAS_TA_PIN = "0.4.71b0"
PTA_BLOCKED = {"dpo", "zigzag", "tos_stdevall", "ichimoku_chikou", "chikou", "ics", "hwc", "ha", "jma", "alligator"}
# dpo: centred by default (reads n/2+1 later bars); ichimoku chikou: close shifted back 26 bars (= future close at the row);
# zigzag/tos_stdevall: repaint (computed over the whole series); jma/hwc/ha/alligator: not leak-tested -> blocked by default.
DEFAULT_BUDGET_S = float(os.environ.get("RESEARCH_COLS_BUDGET_S", "300"))
DEFAULT_TIMEOUT_S = float(os.environ.get("RESEARCH_COLS_TOOL_TIMEOUT_S", "20"))
NaN = float("nan")

# ------------------------------------------------------------------ helpers
def _cut(df, cutoff, asset):
    x = GEO.pit_cut(df, cutoff, asset)
    return x.astype({"Open": float, "High": float, "Low": float, "Close": float, "Volume": float})

def _f(v, n=6):
    """plain float (NaN for None/inf/garbage), rounded"""
    try:
        v = float(v)
        return round(v, n) if math.isfinite(v) else NaN
    except (TypeError, ValueError):
        return NaN

def _b(v):
    if v is None: return NaN
    try:
        if isinstance(v, float) and not math.isfinite(v): return NaN
    except Exception: pass
    return bool(v)

def _sgn(direction): return 1 if str(direction).upper() == "LONG" else -1

@contextlib.contextmanager
def _quiet():
    with contextlib.redirect_stdout(io.StringIO()): yield

# ------------------------------------------------------------------ 1a. TA-Lib
TALIB_IND = ["atr14", "natr14", "rsi14", "macd_atr", "macdh_atr", "macd_cross_up_3", "macd_cross_dn_3", "adx14", "di_spread",
             "cci20", "mfi14", "stoch_k", "willr14", "ultosc", "roc10", "roc20", "bb_pctb", "bb_width", "dist_sma50_atr",
             "dist_sma200_atr", "sma50_gt_sma200", "aroonosc14", "obv_slope20_z", "close_above_sar", "ht_trendmode",
             "linreg_slope20_atr"]
TALIB_CDL = ["cdl_bull_n", "cdl_bear_n", "cdl_net", "cdl_net_dir", "cdl_patterns"]
def tool_talib(df, cutoff, asset, direction):
    import talib
    x = _cut(df, cutoff, asset)
    if len(x) < 60: raise ValueError(f"history too short ({len(x)} bars < 60)")
    o, h, l, c, v = (x[k].values for k in ("Open", "High", "Low", "Close", "Volume"))
    A = talib.ATR(h, l, c, 14)[-1]; r = {}
    r["atr14"] = A; r["natr14"] = talib.NATR(h, l, c, 14)[-1]; r["rsi14"] = talib.RSI(c, 14)[-1]
    m, ms, mh = talib.MACD(c, 12, 26, 9); r["macd_atr"] = m[-1] / A; r["macdh_atr"] = mh[-1] / A
    r["macd_cross_up_3"] = bool(np.any((mh[-3:] > 0) & (mh[-4:-1] <= 0))); r["macd_cross_dn_3"] = bool(np.any((mh[-3:] < 0) & (mh[-4:-1] >= 0)))
    r["adx14"] = talib.ADX(h, l, c, 14)[-1]; r["di_spread"] = talib.PLUS_DI(h, l, c, 14)[-1] - talib.MINUS_DI(h, l, c, 14)[-1]
    r["cci20"] = talib.CCI(h, l, c, 20)[-1]; r["mfi14"] = talib.MFI(h, l, c, v, 14)[-1]
    k, d = talib.STOCH(h, l, c); r["stoch_k"] = k[-1]; r["willr14"] = talib.WILLR(h, l, c, 14)[-1]; r["ultosc"] = talib.ULTOSC(h, l, c)[-1]
    r["roc10"] = talib.ROC(c, 10)[-1]; r["roc20"] = talib.ROC(c, 20)[-1]
    u, mid, lo = talib.BBANDS(c, 20, 2, 2); r["bb_pctb"] = (c[-1] - lo[-1]) / (u[-1] - lo[-1]); r["bb_width"] = (u[-1] - lo[-1]) / mid[-1] * 100
    s50 = talib.SMA(c, 50); s200 = talib.SMA(c, 200) if len(c) >= 200 else np.full(len(c), np.nan)
    r["dist_sma50_atr"] = (c[-1] - s50[-1]) / A; r["dist_sma200_atr"] = (c[-1] - s200[-1]) / A
    r["sma50_gt_sma200"] = bool(s50[-1] > s200[-1]) if np.isfinite(s200[-1]) else NaN
    r["aroonosc14"] = talib.AROONOSC(h, l, 14)[-1]
    ob = talib.OBV(c, v); sd = np.nanstd(np.diff(ob[-61:])); r["obv_slope20_z"] = talib.LINEARREG_SLOPE(ob, 20)[-1] / sd if sd else NaN
    r["close_above_sar"] = bool(c[-1] > talib.SAR(h, l)[-1]); r["ht_trendmode"] = bool(talib.HT_TRENDMODE(c)[-1] == 1)
    r["linreg_slope20_atr"] = talib.LINEARREG_SLOPE(c, 20)[-1] / A
    pats = []; bull = bear = 0
    for fn in talib.get_function_groups()["Pattern Recognition"]:
        val = int(getattr(talib, fn)(o, h, l, c)[-1])
        if val: pats.append(f"{fn[3:].lower()}{'+' if val > 0 else '-'}"); bull += val > 0; bear += val < 0
    r.update(cdl_bull_n=bull, cdl_bear_n=bear, cdl_net=bull - bear, cdl_net_dir=(bull - bear) * _sgn(direction), cdl_patterns=",".join(pats) or None)
    out = {f"exp_talib_{k}": (v if isinstance(v, (bool, str, int)) or v is None else _f(v)) for k, v in r.items()}
    out["exp_talib_last_bar"] = str(x.index[-1].date())
    return out

# ------------------------------------------------------------------ 1b. pandas-ta (pinned, blocklist)
PTA_COLS = ["supertrend_dir", "supertrend_dir_agree", "sqz_on", "sqz_mom_atr", "chop14", "vortex_diff", "stc", "ichi_pos", "crsi",
            "exhc_up", "exhc_dn", "partial"]
def _pta(ta, name):
    if name.lower() in PTA_BLOCKED: raise RuntimeError(f"pandas-ta '{name}' is blocked (look-ahead / repaint)")
    return getattr(ta, name)
def tool_pta(df, cutoff, asset, direction):
    with _quiet(): import pandas_ta as ta
    ver = getattr(ta, "version", None) or getattr(ta, "__version__", None)
    if str(ver) != PANDAS_TA_PIN: raise RuntimeError(f"pandas-ta version {ver} != pinned {PANDAS_TA_PIN}")
    x = _cut(df, cutoff, asset)
    if len(x) < 60: raise ValueError(f"history too short ({len(x)} bars < 60)")
    y = x.copy(); y.columns = [q.lower() for q in y.columns]
    A = GEO.atr14(y.high.values, y.low.values, y.close.values)[-1]; c = float(y.close.iloc[-1]); r = {}; errs = []
    def part(name, f):                   # one failing indicator (e.g. None on short history) only blanks its own columns
        try: f()
        except Exception as e: errs.append(f"{name}: {e.__class__.__name__}")
    def _st():
        st = _pta(ta, "supertrend")(y.high, y.low, y.close, 7, 3.0); r["supertrend_dir"] = float(st["SUPERTd_7_3.0"].iloc[-1])
        r["supertrend_dir_agree"] = bool(r["supertrend_dir"] * _sgn(direction) > 0)
    def _sq():
        sq = _pta(ta, "squeeze")(y.high, y.low, y.close); r["sqz_on"] = bool(sq["SQZ_ON"].iloc[-1] == 1); r["sqz_mom_atr"] = float(sq.iloc[-1, 0]) / A
    def _ch(): r["chop14"] = float(_pta(ta, "chop")(y.high, y.low, y.close, 14).iloc[-1])
    def _vx():
        vt = _pta(ta, "vortex")(y.high, y.low, y.close, 14); r["vortex_diff"] = float(vt.iloc[-1, 0] - vt.iloc[-1, 1])
    def _stc(): r["stc"] = float(_pta(ta, "stc")(y.close).iloc[-1, 0])
    def _ich():
        ich, _ = _pta(ta, "ichimoku")(y.high, y.low, y.close, include_chikou=False)
        if any(str(k).startswith("ICS") for k in ich.columns): raise RuntimeError("ichimoku returned chikou (blocked)")
        top = max(ich["ISA_9"].iloc[-1], ich["ISB_26"].iloc[-1]); bot = min(ich["ISA_9"].iloc[-1], ich["ISB_26"].iloc[-1])
        r["ichi_pos"] = (1.0 if c > top else (-1.0 if c < bot else 0.0)) if np.isfinite(top) and np.isfinite(bot) else NaN
    def _crsi(): r["crsi"] = float(_pta(ta, "crsi")(y.close).iloc[-1])
    def _ex():
        ex = _pta(ta, "exhc")(y.high, y.low, y.close)
        r["exhc_up"] = float(ex.iloc[-1][[q for q in ex.columns if "UP" in q][0]]); r["exhc_dn"] = float(ex.iloc[-1][[q for q in ex.columns if "DN" in q][0]])
    for nm, f in (("supertrend", _st), ("squeeze", _sq), ("chop", _ch), ("vortex", _vx), ("stc", _stc), ("ichimoku", _ich), ("crsi", _crsi), ("exhc", _ex)):
        part(nm, f)
    if len(errs) == 8: raise RuntimeError("all pandas-ta indicators failed: " + "; ".join(errs)[:150])
    if errs: r["partial"] = "; ".join(errs)[:200]
    return {f"exp_pta_{k}": (v if isinstance(v, (bool, str)) else _f(v)) for k, v in r.items()}

# ------------------------------------------------------------------ 2a. smart-money-concepts (PIT wrapper)
SMC_COLS = ["last_break_dir", "last_break_kind", "bars_since_break", "breaks_last20_net", "fvg_open_n", "in_fvg", "fvg_above_lo",
            "fvg_above_dist_atr", "fvg_below_hi", "fvg_below_dist_atr", "ob_open_n", "ob_below_lo", "ob_below_hi", "ob_below_dist_atr",
            "ob_above_lo", "ob_above_hi", "ob_above_dist_atr", "liq_open_n", "liq_above_near", "liq_below_near", "swept_last3_bsl",
            "swept_last3_ssl", "ret_dir", "ret_current", "ret_deepest", "artificial_last_swing_removed", "break_agree"]
SMC_SWING = 10
def tool_smc(df, cutoff, asset, direction):
    with _quiet(): from smartmoneyconcepts import smc
    x = _cut(df, cutoff, asset)
    if len(x) < 60: raise ValueError(f"history too short ({len(x)} bars < 60)")
    o = x.copy(); o.columns = [q.lower() for q in o.columns]; o = o.reset_index(drop=True); n = len(o)
    with _quiet():
        sw = smc.swing_highs_lows(o, swing_length=SMC_SWING).copy()
        art = bool(pd.notna(sw.HighLow.iloc[-1])); sw.iloc[0] = np.nan; sw.iloc[-1] = np.nan     # never-confirmed swings removed
        fv = smc.fvg(o); bc = smc.bos_choch(o, sw, close_break=True); ob = smc.ob(o, sw)
        lq = smc.liquidity(o, sw, range_percent=0.01); rt = smc.retracements(o, sw)
    c = o.close.values; A = GEO.atr14(o.high.values, o.low.values, c)[-1]; C = c[-1]; r = {"artificial_last_swing_removed": art}
    ev = bc.dropna(subset=["BrokenIndex"])
    ev = ev.assign(dir=ev.BOS.fillna(ev.CHOCH), kind=np.where(ev.CHOCH.notna(), "choch", "bos")).sort_values("BrokenIndex")
    ev = ev[ev.BrokenIndex <= n - 1]
    if len(ev):
        e = ev.iloc[-1]; r.update(last_break_dir=float(e.dir), last_break_kind=e.kind, bars_since_break=float(n - 1 - e.BrokenIndex),
                                  breaks_last20_net=float(ev[ev.BrokenIndex >= n - 20].dir.sum()), break_agree=bool(float(e.dir) * _sgn(direction) > 0))
    f = fv.dropna(subset=["FVG"]); f = f[f.MitigatedIndex == 0]
    ab = f[f.Bottom > C]; be = f[f.Top < C]
    r.update(fvg_open_n=len(f), in_fvg=bool(((f.Bottom <= C) & (f.Top >= C)).any()))
    if len(ab): r.update(fvg_above_lo=float(ab.Bottom.min()), fvg_above_dist_atr=(float(ab.Bottom.min()) - C) / A)
    if len(be): r.update(fvg_below_hi=float(be.Top.max()), fvg_below_dist_atr=(C - float(be.Top.max())) / A)
    b = ob.dropna(subset=["OB"]); b = b[b.MitigatedIndex == 0]; r["ob_open_n"] = len(b)
    bull = b[(b.OB == 1) & (b.Top <= C)]; bear = b[(b.OB == -1) & (b.Bottom >= C)]
    if len(bull):
        i = bull.Top.idxmax(); r.update(ob_below_lo=float(bull.loc[i, "Bottom"]), ob_below_hi=float(bull.Top.max()), ob_below_dist_atr=(C - float(bull.Top.max())) / A)
    if len(bear):
        i = bear.Bottom.idxmin(); r.update(ob_above_lo=float(bear.Bottom.min()), ob_above_hi=float(bear.loc[i, "Top"]), ob_above_dist_atr=(float(bear.Bottom.min()) - C) / A)
    q = lq.dropna(subset=["Liquidity"]); op = q[q.Swept == 0]; r["liq_open_n"] = len(op)
    up = op[(op.Liquidity == 1) & (op.Level > C)].Level; dn = op[(op.Liquidity == -1) & (op.Level < C)].Level
    r["liq_above_near"] = float(up.min()) if len(up) else NaN; r["liq_below_near"] = float(dn.max()) if len(dn) else NaN
    rs = q[(q.Swept > 0) & (q.Swept >= n - 3) & (q.Swept <= n - 1)]
    r["swept_last3_bsl"] = bool((rs.Liquidity == 1).any()); r["swept_last3_ssl"] = bool((rs.Liquidity == -1).any())
    r["ret_dir"] = float(rt.Direction.iloc[-1]) if pd.notna(rt.Direction.iloc[-1]) else NaN
    r["ret_current"] = float(rt["CurrentRetracement%"].iloc[-1]); r["ret_deepest"] = float(rt["DeepestRetracement%"].iloc[-1])
    return {f"exp_smc_{k}": (v if isinstance(v, (bool, str)) else _f(v)) for k, v in r.items()}

# ------------------------------------------------------------------ 2b. Elliott repos (ta-repos-eval/ew_libs.py adapters)
EW_COLS = ["state", "tgt", "inval", "last", "tgt_dist_atr", "inval_dist_atr"]
def _ew(name, df, cutoff, asset, direction, drop_last=0):
    if TA_DIR not in sys.path: sys.path.insert(0, TA_DIR)
    with _quiet(): import ew_libs as E
    x = _cut(df, cutoff, asset)
    if len(x) < 60: raise ValueError(f"history too short ({len(x)} bars < 60)")
    fn = {"taew": E.taew_state, "ewa": E.ewa_state, "ewaves": E.ar_state}[name]
    with _quiet(): o = fn(x, _sgn(direction))
    A = GEO.atr14(x.High.values, x.Low.values, x.Close.values)[-1]; C = float(x.Close.iloc[-1]); s = _sgn(direction)
    r = {"state": o.get("state"), "tgt": _f(o.get("tgt")), "inval": _f(o.get("inval")), "last": _f(o.get("last"))}
    r["tgt_dist_atr"] = _f(s * (r["tgt"] - C) / A) if np.isfinite(r["tgt"]) else NaN
    r["inval_dist_atr"] = _f(s * (C - r["inval"]) / A) if np.isfinite(r["inval"]) else NaN
    if "n_patterns" in o: r["n_patterns"] = int(o["n_patterns"])
    return {f"exp_{name}_{k}": v for k, v in r.items()}
def tool_taew(df, cutoff, asset, direction):
    """python-taew on bars <= cutoff only (its pivot needs the next bar -> nothing on the last cut bar)."""
    return _ew("taew", df, cutoff, asset, direction)
def tool_ewa(df, cutoff, asset, direction):
    """ElliottWaveAnalyzer - NO LICENSE, internal use only."""
    r = _ew("ewa", df, cutoff, asset, direction); r["exp_ewa_internal_use_only"] = True; return r
def tool_ewaves(df, cutoff, asset, direction):
    """ElliottWaves: provisional argrelextrema(order=7) pivots in the last 7 cut bars are dropped inside ew_libs.ar_pivots."""
    return _ew("ewaves", df, cutoff, asset, direction)

# ------------------------------------------------------------------ 3/4. Qlib + FinRL: nightly pre-trained, scan = lookup
_PRED_CACHE = {}
def _pred(tool, bar_date):
    """nightly predictions for one bar date (research_nightly/*_nightly.py -> research-models/<tool>/pred_<D>.csv)."""
    k = (tool, bar_date)
    if k not in _PRED_CACHE:
        f = f"{MODEL_DIR}/{tool}/pred_{bar_date}.csv"
        _PRED_CACHE[k] = pd.read_csv(f).set_index("ticker") if os.path.exists(f) else None
    return _PRED_CACHE[k]
def _model_tool(tool, df, cutoff, asset, direction, symbol):
    if asset != "stock": raise ValueError(f"{tool}: stocks only (model universe)")
    if not symbol: raise ValueError(f"{tool}: needs the ticker (pass symbol= or a frame with .attrs['symbol'])")
    x = _cut(df, cutoff, asset); D = str(x.index[-1].date())
    P = _pred(tool, D)
    if P is None: raise FileNotFoundError(f"no nightly {tool} prediction for bar {D} (nightly not run yet?)")
    sym = symbol.replace(".", "_").upper()
    if sym not in P.index: raise KeyError(f"{symbol} not in the {tool} universe for {D}")
    p = P.loc[sym]
    if str(p["bar_date"])[:10] != D: raise ValueError(f"{tool} prediction bar {p['bar_date']} != last visible bar {D}")
    if pd.Timestamp(p["label_end"]) > pd.Timestamp(D) or pd.Timestamp(p["train_end"]) > pd.Timestamp(D): raise ValueError(f"{tool} model uses data after bar {D} (labels to {p['label_end']}) - leak")
    s = _sgn(direction); pct = _f(p["pct"])
    return {f"exp_{tool}_score": _f(p["score"]), f"exp_{tool}_pct": pct, f"exp_{tool}_pct_dir": _f(pct if s == 1 else 100 - pct),
            f"exp_{tool}_bar": D, f"exp_{tool}_train_end": str(p["train_end"])[:10], f"exp_{tool}_label_end": str(p["label_end"])[:10],
            f"exp_{tool}_model": str(p["model_id"])}
def tool_qlib(df, cutoff, asset, direction, symbol=None):
    return _model_tool("qlib", df, cutoff, asset, direction, symbol or df.attrs.get("symbol"))
def tool_finrl(df, cutoff, asset, direction, symbol=None):
    return _model_tool("finrl", df, cutoff, asset, direction, symbol or df.attrs.get("symbol"))
MODEL_COLS = ["score", "pct", "pct_dir", "bar", "train_end", "label_end", "model"]

# ------------------------------------------------------------------ registry
# name -> (function, columns (without prefix), libraries needed, venv python if not importable here, timeout s, note)
# ------------------------------------------------------------------ multi-degree pivots / confluence + volume phase (16.10.2026, weight 0)
# research/pivots/PREREG.md; modules/scanner_pivots.py + modules/scanner_volphase.py. Logged only.
def tool_piv(df, cutoff, asset, direction):
    import scanner_pivots as PV
    return {f"exp_piv_{k}": v for k, v in PV.pivot_columns(df, cutoff, asset, direction).items()}
def tool_vph(df, cutoff, asset, direction):
    import scanner_volphase as VPH
    return {f"exp_vph_{k}": v for k, v in VPH.volphase_columns(df, cutoff, asset, direction).items()}
try:
    import scanner_pivots as _PV, scanner_volphase as _VPH
    PIV_COLS, VPH_COLS = list(_PV.COLS), list(_VPH.COLS)
except Exception:
    PIV_COLS, VPH_COLS = ["version"], ["version"]

REGISTRY = {
    "talib":  dict(fn=tool_talib, cols=TALIB_IND + TALIB_CDL + ["last_bar"], deps=["talib"], venv=TA_VENV, timeout=10, priority=1,
                   note="TA-Lib 0.8.1, BSD; leak test 0/233 outputs"),
    "pta":    dict(fn=tool_pta, cols=PTA_COLS, deps=["pandas_ta", "talib"], venv=TA_VENV, timeout=15, priority=1,
                   note=f"pandas-ta pinned {PANDAS_TA_PIN}, MIT; blocked: DPO, chikou, ZIGZAG, TOS_STDEVALL (+jma/hwc/ha/alligator)"),
    "smc":    dict(fn=tool_smc, cols=SMC_COLS, deps=["smartmoneyconcepts"], venv=TA_VENV, timeout=20, priority=2,
                   note="smart-money-concepts 0.0.27, MIT; PIT wrapper only (raw library repaints)"),
    "taew":   dict(fn=tool_taew, cols=EW_COLS, deps=["taew", "scipy"], venv=TA_VENV, timeout=20, priority=2,
                   note="python-taew, MIT; truncated at cutoff"),
    "ewa":    dict(fn=tool_ewa, cols=EW_COLS + ["internal_use_only"], deps=["models", "scipy"], venv=TA_VENV, timeout=20, priority=2,
                   note="ElliottWaveAnalyzer - NO LICENSE: internal use only"),
    "ewaves": dict(fn=tool_ewaves, cols=EW_COLS + ["n_patterns"], deps=["scipy"], venv=TA_VENV, timeout=20, priority=2,
                   note="ElliottWaves, MIT; last 7 bars' provisional pivots dropped"),
    "qlib":   dict(fn=tool_qlib, cols=MODEL_COLS, deps=[], venv=None, timeout=5, priority=3, needs_symbol=True,
                   note="Qlib Alpha158+LightGBM, MIT; nightly walk-forward, scan = lookup"),
    "finrl":  dict(fn=tool_finrl, cols=MODEL_COLS, deps=[], venv=None, timeout=5, priority=4, needs_symbol=True,
                   note="FinRL PPO 2048 steps, MIT; nightly, scan = lookup"),
    "piv":    dict(fn=tool_piv, cols=PIV_COLS, deps=[], venv=None, timeout=10, priority=2,
                   note="multi-degree pivots + Fib/Gann confluence (PREREG research/pivots), weight 0"),
    "vph":    dict(fn=tool_vph, cols=VPH_COLS, deps=[], venv=None, timeout=5, priority=2,
                   note="4-state volume phase + CMF20/OBV (PREREG research/pivots), weight 0"),
}
DEFAULT_TOOLS = list(REGISTRY)
def tool_columns(tool):
    return [f"exp_{tool}_{c}" for c in REGISTRY[tool]["cols"]] + [f"exp_{tool}_status"]
ALL_COLUMNS = [c for t in REGISTRY for c in tool_columns(t)]
# metadata for tool_stats.py: how each column is turned into a flag ("flag" bool, "signed" +/- aligned with direction, "pct" 0-100,
# "cat" category levels, "info" not tested). Columns not listed are handled by tool_stats heuristics.
COLUMN_META = {
    "exp_talib_macd_cross_up_3": "flag", "exp_talib_macd_cross_dn_3": "flag", "exp_talib_sma50_gt_sma200": "flag",
    "exp_talib_close_above_sar": "flag", "exp_talib_ht_trendmode": "flag", "exp_talib_cdl_net_dir": "signed_dir",
    "exp_talib_cdl_net": "signed", "exp_talib_cdl_bull_n": "count", "exp_talib_cdl_bear_n": "count", "exp_talib_cdl_patterns": "info",
    "exp_talib_last_bar": "info", "exp_talib_atr14": "info",
    "exp_pta_partial": "info", "exp_pta_supertrend_dir": "signed", "exp_pta_supertrend_dir_agree": "flag", "exp_pta_sqz_on": "flag", "exp_pta_ichi_pos": "signed",
    "exp_smc_last_break_dir": "signed", "exp_smc_break_agree": "flag", "exp_smc_in_fvg": "flag", "exp_smc_swept_last3_bsl": "flag",
    "exp_smc_swept_last3_ssl": "flag", "exp_smc_ret_dir": "signed", "exp_smc_last_break_kind": "cat",
    "exp_smc_artificial_last_swing_removed": "info",
    "exp_smc_fvg_above_lo": "info", "exp_smc_fvg_below_hi": "info", "exp_smc_ob_below_lo": "info", "exp_smc_ob_below_hi": "info",
    "exp_smc_ob_above_lo": "info", "exp_smc_ob_above_hi": "info", "exp_smc_liq_above_near": "info", "exp_smc_liq_below_near": "info",
    "exp_ewa_internal_use_only": "info",
}
for _t in ("taew", "ewa", "ewaves"):
    COLUMN_META.update({f"exp_{_t}_state": "cat", f"exp_{_t}_tgt": "info", f"exp_{_t}_inval": "info", f"exp_{_t}_last": "info"})
for _t in ("qlib", "finrl"):
    COLUMN_META.update({f"exp_{_t}_pct_dir": "pct", f"exp_{_t}_pct": "info", f"exp_{_t}_score": "info", f"exp_{_t}_bar": "info",
                        f"exp_{_t}_train_end": "info", f"exp_{_t}_label_end": "info", f"exp_{_t}_model": "info"})
COLUMN_META.update({f"exp_piv_{c}": "info" for c in PIV_COLS} | {f"exp_vph_{c}": "info" for c in VPH_COLS})
COLUMN_META.update({"exp_piv_support_zone_dist_atr": "signed", "exp_piv_in_zone_strength": "info", "exp_vph_dom10_aligned": "signed",
                    "exp_vph_w_dom10_aligned": "signed", "exp_vph_cmf20_dir": "signed"})
for _t in REGISTRY: COLUMN_META[f"exp_{_t}_status"] = "info"

# columns proposed for the tracker (build7 cols after the fundamentals); everything else stays in scan_raw.csv
TRACKER_KEYS = ["exp_talib_rsi14", "exp_talib_adx14", "exp_talib_dist_sma200_atr", "exp_talib_cdl_net_dir", "exp_talib_cdl_patterns",
                "exp_pta_supertrend_dir_agree", "exp_pta_sqz_on", "exp_pta_ichi_pos", "exp_pta_crsi",
                "exp_smc_break_agree", "exp_smc_last_break_kind", "exp_smc_in_fvg", "exp_smc_fvg_above_dist_atr", "exp_smc_fvg_below_dist_atr",
                "exp_smc_swept_last3_bsl", "exp_smc_swept_last3_ssl",
                "exp_taew_state", "exp_taew_tgt", "exp_ewa_state", "exp_ewaves_state",
                "exp_qlib_pct_dir", "exp_finrl_pct_dir"] + [f"exp_{t}_status" for t in REGISTRY]

def _nan_cols(tool, status):
    r = {c: NaN for c in tool_columns(tool)}; r[f"exp_{tool}_status"] = status; return r

# ------------------------------------------------------------------ in-process call with a time limit (main thread: SIGALRM)
class ToolTimeout(Exception): pass
def _alarm(sig, frm): raise ToolTimeout()
def _run_local(tool, df, cutoff, asset, direction, symbol=None):
    spec = REGISTRY[tool]; t0 = time.time()
    use_alarm = threading.current_thread() is threading.main_thread() and hasattr(signal, "setitimer")
    try:
        if use_alarm:
            old = signal.signal(signal.SIGALRM, _alarm); signal.setitimer(signal.ITIMER_REAL, spec["timeout"])
        try:
            r = spec["fn"](df, cutoff, asset, direction, symbol=symbol) if spec.get("needs_symbol") else spec["fn"](df, cutoff, asset, direction)
        finally:
            if use_alarm: signal.setitimer(signal.ITIMER_REAL, 0); signal.signal(signal.SIGALRM, old)
        out = {c: NaN for c in tool_columns(tool)}; out.update(r); out[f"exp_{tool}_status"] = "ok"
    except ToolTimeout:
        out = _nan_cols(tool, f"timeout > {spec['timeout']}s")
    except Exception as e:
        out = _nan_cols(tool, f"{e.__class__.__name__}: {str(e)[:200]}")
    return out, time.time() - t0

def _importable(deps):
    if TA_DIR not in sys.path and any(d in ("taew", "models") for d in deps):
        for p in (TA_DIR, f"{TA_DIR}/repos/python-taew", f"{TA_DIR}/repos/ElliottWaveAnalyzer"): sys.path.insert(0, p)
    try: return all(importlib.util.find_spec(d) is not None for d in deps)
    except Exception: return False

# ------------------------------------------------------------------ worker subprocess (other venv)
def _pack(df, cutoff, asset, direction, symbol):
    x = df.rename(columns=str.title)[["Open", "High", "Low", "Close", "Volume"]]
    idx = pd.DatetimeIndex(x.index)
    if idx.tz is not None: idx = idx.tz_convert("UTC").tz_localize(None)
    return dict(idx=[str(i) for i in idx], cols={k: [float(v) for v in x[k].values] for k in x.columns},
                cutoff=None if cutoff is None else str(pd.Timestamp(cutoff)), asset=asset, direction=direction, symbol=symbol)
def _unpack(d):
    df = pd.DataFrame(d["cols"], index=pd.DatetimeIndex(pd.to_datetime(d["idx"])))
    return df, (None if d["cutoff"] is None else pd.Timestamp(d["cutoff"])), d["asset"], d["direction"], d.get("symbol")
def _plain(v):
    if isinstance(v, (np.bool_,)): return bool(v)
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.floating,)): return float(v)
    return v

class _Worker:
    def __init__(self, python):
        self.python = python; self.p = None; self.lock = threading.Lock()
    def _start(self):
        env = dict(os.environ, PYTHONPATH=f"{TA_DIR}:{TA_DIR}/repos/python-taew:{TA_DIR}/repos/ElliottWaveAnalyzer:/workspace",
                   OMP_NUM_THREADS="1", NUMBA_NUM_THREADS="1")
        for k in list(env):          # no secrets into the worker (it never needs network)
            if any(s in k for s in ("KEY", "SECRET", "TOKEN", "PASSWORD")): env.pop(k)
        self.p = subprocess.Popen([self.python, os.path.abspath(__file__), "--worker"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, env=env, cwd=_SCANNER_ROOT)
    def call(self, tool, payload, timeout):
        with self.lock:
            if self.p is None or self.p.poll() is not None: self._start()
            b = pickle.dumps((tool, payload), protocol=4)
            try:
                self.p.stdin.write(struct.pack(">I", len(b)) + b); self.p.stdin.flush()
                res = [None]
                def rd():
                    try:
                        n = struct.unpack(">I", self.p.stdout.read(4))[0]; res[0] = pickle.loads(self.p.stdout.read(n))
                    except Exception as e: res[0] = e
                th = threading.Thread(target=rd, daemon=True); th.start(); th.join(timeout + 30)   # +30 s: first call imports
                if th.is_alive():
                    self.kill(); return _nan_cols(tool, f"worker timeout > {timeout + 30:.0f}s")
                if isinstance(res[0], Exception):
                    self.kill(); return _nan_cols(tool, f"worker died: {res[0].__class__.__name__}")
                return res[0]
            except Exception as e:
                self.kill(); return _nan_cols(tool, f"worker error: {e.__class__.__name__}: {str(e)[:120]}")
    def kill(self):
        try: self.p.kill()
        except Exception: pass
        self.p = None

def _worker_main():
    out = os.fdopen(os.dup(1), "wb"); os.dup2(2, 1); sys.stdout = sys.stderr      # library prints never reach the protocol pipe
    inp = sys.stdin.buffer
    while True:
        h = inp.read(4)
        if len(h) < 4: break
        tool, payload = pickle.loads(inp.read(struct.unpack(">I", h)[0]))
        df, cutoff, asset, direction, symbol = _unpack(payload)
        r, sec = _run_local(tool, df, cutoff, asset, direction, symbol)
        r = {k: _plain(v) for k, v in r.items()}; r["_sec"] = sec
        b = pickle.dumps(r, protocol=4); out.write(struct.pack(">I", len(b)) + b); out.flush()

_WORKERS = {}
def _worker(python, slot=0):
    k = (python, slot)
    if k not in _WORKERS: _WORKERS[k] = _Worker(python)
    return _WORKERS[k]
def shutdown():
    for w in _WORKERS.values(): w.kill()
    _WORKERS.clear()
import atexit; atexit.register(shutdown)

# ------------------------------------------------------------------ budget + public API
_BUDGET = {"t0": None, "limit": DEFAULT_BUDGET_S}
TIMINGS = {}          # tool -> [seconds per call] (last scan)
def reset_budget(limit=None):
    _BUDGET["t0"] = time.time(); _BUDGET["limit"] = DEFAULT_BUDGET_S if limit is None else float(limit); TIMINGS.clear()
def _over_budget():
    if _BUDGET["t0"] is None: _BUDGET["t0"] = time.time()
    return time.time() - _BUDGET["t0"] > _BUDGET["limit"]

def _route(tool):
    spec = REGISTRY[tool]
    return "local" if (not spec["deps"] or _importable(spec["deps"])) else "worker"

def compute_all(df, cutoff, asset="stock", direction="LONG", tools=None, symbol=None, _slot=0):
    """All research columns for ONE ticker at ONE cutoff. Never raises."""
    out = {"exp_rc_version": VERSION}
    try:
        if symbol is None: symbol = getattr(df, "attrs", {}).get("symbol")
        x = GEO.pit_cut(df, cutoff, asset)              # cut once here (also cut again inside every tool)
        out["exp_rc_last_bar"] = str(x.index[-1].date()) if len(x) else None
    except Exception as e:
        x = None; out["exp_rc_last_bar"] = None; err = f"bad frame: {e.__class__.__name__}: {e}"
    for tool in (tools or DEFAULT_TOOLS):
        if tool not in REGISTRY: out[f"exp_{tool}_status"] = "unknown tool"; continue
        if x is None: out.update(_nan_cols(tool, err)); continue
        if _over_budget(): out.update(_nan_cols(tool, f"skipped (scan time budget {_BUDGET['limit']:.0f}s)")); continue
        try:
            if _route(tool) == "local":
                r, sec = _run_local(tool, x, cutoff, asset, direction, symbol)
            else:
                t0 = time.time()
                r = _worker(REGISTRY[tool]["venv"], _slot).call(tool, _pack(x, cutoff, asset, direction, symbol), REGISTRY[tool]["timeout"])
                r.pop("_sec", None); sec = time.time() - t0
        except Exception as e:   # belt and braces
            r, sec = _nan_cols(tool, f"{e.__class__.__name__}: {str(e)[:200]}"), 0.0
        TIMINGS.setdefault(tool, []).append(sec); out.update(r)
    return out

def compute_many(items, tools=None, workers=2):
    """items: iterable of (key, df, cutoff, asset, direction[, symbol]). Returns list of dicts with 'key'. Never raises.
    workers = parallel worker processes per venv (each thread drives its own worker)."""
    from concurrent.futures import ThreadPoolExecutor
    items = list(items); res = [None] * len(items)
    def job(slot):
        for i in range(slot, len(items), workers):
            it = items[i]; key, df, cutoff, asset, direction = it[:5]; sym = it[5] if len(it) > 5 else (key if isinstance(key, str) else None)
            try: r = compute_all(df, cutoff, asset, direction, tools=tools, symbol=sym, _slot=slot)
            except Exception as e: r = {"exp_rc_error": f"{e.__class__.__name__}: {e}"}
            res[i] = {"key": key, **r}
    with ThreadPoolExecutor(workers) as ex: list(ex.map(job, range(workers)))
    return res

def status_summary(rows):
    """per tool: n ok / n failed / top error strings (for the scan log)."""
    out = {}
    for t in REGISTRY:
        s = pd.Series([r.get(f"exp_{t}_status") for r in rows]).dropna()
        if not len(s): continue
        out[t] = dict(ok=int((s == "ok").sum()), failed=int((s != "ok").sum()), errors=s[s != "ok"].str[:60].value_counts().head(3).to_dict(),
                      sec_mean=round(float(np.mean(TIMINGS.get(t, [0]))), 3), sec_total=round(float(np.sum(TIMINGS.get(t, [0]))), 1))
    return out

if __name__ == "__main__":
    if "--worker" in sys.argv: _worker_main(); sys.exit(0)
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="OHLCV csv with a date column"); ap.add_argument("--cutoff"); ap.add_argument("--asset", default="stock")
    ap.add_argument("--direction", default="LONG"); ap.add_argument("--symbol"); ap.add_argument("--tools")
    a = ap.parse_args()
    d = pd.read_csv(a.csv); d = d.set_index(pd.to_datetime(d.iloc[:, 0])).iloc[:, 1:]
    print(json.dumps(compute_all(d, a.cutoff, a.asset, a.direction, tools=a.tools.split(",") if a.tools else None, symbol=a.symbol),
                     indent=1, ensure_ascii=False, default=str))
