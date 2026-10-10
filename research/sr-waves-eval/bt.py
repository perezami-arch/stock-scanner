"""Quick point-in-time sanity backtest of scanner_levels (S/R) and scanner_waves on the tracker setups (stocks).
Setups: /workspace/scanner-tool-eval/setups_prepared.csv (canonical tracker, asof_ts = information cutoff).
Prices: one Yahoo daily download per ticker (auto_adjust, like the scanner); history is PIT-cut at asof_ts with geometry.pit_cut,
forward bars (after the cutoff bar) only for outcomes. Writes lookups to /workspace/tracker/*_lookup.csv and results.md here."""
import os, sys, json, math, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore"); sys.path.insert(0, "/workspace")
import scanner_levels as SL, scanner_waves as SW, scanner_geometry as GEO
OUT = "/workspace/sr-waves-eval"; TODAY = pd.Timestamp("2026-10-08T12:15Z")
S = pd.read_csv("/workspace/scanner-tool-eval/setups_prepared.csv")
S = S[(S.asset == "stock") & S.direction.isin(["LONG", "SHORT"]) & S.asof_ts.notna()].copy()
S["cut"] = pd.to_datetime(S.asof_ts, utc=True)
tick = sorted(S.ticker.unique())
os.makedirs(f"{SL.CACHE}/yahoo_daily", exist_ok=True)
miss = [t for t in tick if not os.path.exists(f"{SL.CACHE}/yahoo_daily/{t}_{TODAY:%Y%m%d}.csv")]
if miss:
    import yfinance as yf
    d = yf.download(miss, start="2014-09-01", end="2026-10-09", group_by="ticker", auto_adjust=True, threads=True, progress=False)
    for t in miss:
        try:
            x = d[t].dropna(subset=["Close"]) if isinstance(d.columns, pd.MultiIndex) else d.dropna(subset=["Close"])
            if len(x): x.index.name = "date"; x[["Open", "High", "Low", "Close", "Volume"]].to_csv(f"{SL.CACHE}/yahoo_daily/{t}_{TODAY:%Y%m%d}.csv")
        except Exception: pass
    for t in miss:                                       # retry singles that failed in the batch
        f = f"{SL.CACHE}/yahoo_daily/{t}_{TODAY:%Y%m%d}.csv"
        if os.path.exists(f): continue
        try:
            x = yf.download(t, start="2014-09-01", end="2026-10-09", auto_adjust=True, progress=False)
            if isinstance(x.columns, pd.MultiIndex): x.columns = x.columns.get_level_values(0)
            if len(x): x.index.name = "date"; x[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"]).to_csv(f)
        except Exception: pass
FULL = {}
for t in tick:
    f = f"{SL.CACHE}/yahoo_daily/{t}_{TODAY:%Y%m%d}.csv"
    if os.path.exists(f): FULL[t] = GEO._norm(pd.read_csv(f, parse_dates=["date"]).set_index("date"))
sim = pd.read_csv("/workspace/trading-frameworks-eval/iaf/sim_chand_trades.csv")
ch4 = sim[sim.policy == "chand4_c"].set_index("setup_id")
rows, srL, wvL = [], [], []
for _, s in S.iterrows():
    x = FULL.get(s.ticker)
    if x is None: rows.append(dict(setup_id=s.setup_id, err="no price")); continue
    h = GEO.pit_cut(x, s["cut"], "stock")
    if len(h) < 120: rows.append(dict(setup_id=s.setup_id, err="<120 bars")); continue
    fwd = x[x.index > h.index[-1]].iloc[:20]
    sg = 1 if s.direction == "LONG" else -1
    r = dict(setup_id=s.setup_id, ticker=s.ticker, direction=s.direction, asof=str(s["cut"]), cutoff_bar=str(h.index[-1].date()),
             entry=s.entry, stop=s.stop, tp1=s.tp1, x20=s.x20, r20=s.r20, excluded=s.excluded_reason, dup=s.dup_not_counted)
    # ---- S/R (SWING)
    lv = SL.levels_for(s.ticker, s["cut"], "SWING", s.direction, daily=h)
    sm = lv["summary"]; srL.append(dict(setup_id=s.setup_id, ticker=s.ticker, direction=s.direction, cutoff_utc=str(s["cut"]), **sm))
    A = sm.get("sr_atr14_d"); L = lv["levels"]
    smax = max([o["strength"] for o in L] + [1e-9])
    strong = [o for o in L if o["strength"] >= 0.5 * smax]
    e, st, tp = (float(v) if pd.notna(v) else None for v in (s.entry, s.stop, s.tp1))
    if e and st and A:
        r["stop_beyond_strong"] = any(min(e, st) < o["price"] < max(e, st) for o in strong)
        r["stop_dist_atr"] = abs(e - st) / A
    if e and tp and A:
        blk = [o for o in strong if min(e, tp) < o["price"] < max(e, tp)]
        r["strong_level_before_tp1"] = bool(blk)
        if blk:
            cap = min(blk, key=lambda o: abs(o["price"] - e))["price"]; r["tp_capped"] = cap - sg * 0.1 * A
    # ---- outcomes on forward bars (entry = tracker entry; stop/target touched intraday; stop first if both in a bar)
    def outcome(tgt):
        if not (e and st) or len(fwd) == 0: return None, None, None
        for i, (_, b) in enumerate(fwd.iterrows()):
            if sg * (b.Low if sg == 1 else b.High) <= sg * st: return "stop", sg * (st / e - 1), i + 1
            if tgt is not None and sg * (b.High if sg == 1 else b.Low) >= sg * tgt: return "target", sg * (tgt / e - 1), i + 1
        return "time", sg * (float(fwd.Close.iloc[-1]) / e - 1), len(fwd)
    r["n_fwd"] = len(fwd)
    r["out_tp1"], r["ret_tp1"], _ = outcome(tp)
    r["out_nostop_hit"] = None
    if "tp_capped" in r: r["out_cap"], r["ret_cap"], _ = outcome(r["tp_capped"])
    o_, ret_, _ = outcome(None); r["stop_hit20"] = (o_ == "stop") if o_ else None
    # ---- waves (scanner-length history: last 480 PIT bars, like the scanner cache)
    wc = SW.waves_columns(h.iloc[-480:], None, "stock", s.direction)
    wvL.append(dict(setup_id=s.setup_id, ticker=s.ticker, direction=s.direction, cutoff_utc=str(s["cut"]), **wc))
    for k in ("wave_end_signal", "wave_start_signal", "wave_end_n", "wave_end_reasons", "wz_exhaustion_with", "ww_exhaustion_with",
              "wz_counter_gt_with", "ww_counter_gt_with", "crsi", "rsi14", "cci20"): r[k] = wc.get(k)
    r["div_against"] = bool(wc.get("wave_end_reasons") and "divergence" in (wc.get("wave_end_reasons") or ""))
    r["chand4_stopped"] = (ch4.loc[s.setup_id, "status"] == "stopped") if s.setup_id in ch4.index else None
    r["chand4_ret"] = ch4.loc[s.setup_id, "ret_net"] if s.setup_id in ch4.index else None
    rows.append(r)
R = pd.DataFrame(rows); R.to_csv(f"{OUT}/bt_rows.csv", index=False)
pd.DataFrame(srL).to_csv("/workspace/tracker/sr_levels_lookup.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(wvL).to_csv("/workspace/tracker/volume_waves_lookup.csv", index=False, encoding="utf-8-sig")
print("rows", len(R), "with data", R.get("err").isna().sum() if "err" in R else len(R))
