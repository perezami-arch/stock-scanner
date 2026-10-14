"""Post-run parity check: vectorbt vs stop_rules.py (the active policy) on NEW scanner trades. Separate from the scan.
Policy (= sim_ratchet 'rt_plain*_c', the approved stops): entry at the OPEN of day 1 (first session >= alert date, or the row's
entry_date) with slippage; stock LONG chandelier 4xATR14 close-based + half out at the first close >= tp_half_1618;
stock SHORT chandelier 4xATR14 close-based; crypto LONG fixed entry - 3xATR14 close-based; no check on day 2 (= sim_ratchet);
costs per side stock 0.02% fee + 0.05% slip, crypto 0.10% + 0.10%. ATR at entry = the row's atr14_wilder (PIT at the scan),
else Wilder ATR14 of the last completed bar before day 1. Stop for bar j uses ATR14 of bar j-1.
  REFERENCE: a bar loop with stop_rules.ChandelierStop (exactly as iaf/sim_ratchet.py).
  ENGINE   : vectorbt Portfolio.from_orders - stop/target bars from a vectorised numpy pass, fills/fees/slippage/P&L by vectorbt.
A trade mismatches if |engine - reference| > 0.01 pp. Open trades are marked to the last close by both.
Stage 1 (system python3): read trades (build7 tracker rows with alert date >= --since, or --trades CSV) + yfinance bars.
Stage 2 (gh-repos-eval/venv-vbt, started automatically): both engines + comparison.
Usage: python3 research_nightly/vbt_parity_new.py --tracker /workspace/scan-tracker-2026-10-12-mom.xlsx [--since 2026-10-12]
       python3 research_nightly/vbt_parity_new.py --trades trades.csv   (ticker, direction, alert_date|entry_date, [asset, atr14_wilder, tp_half_1618])
Output: research-models/vbt_parity/<stamp>/{signals.csv, bars/, parity_trades.csv, parity_summary.json}"""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, sys, json, glob, argparse, subprocess
import numpy as np, pandas as pd
VBT_PY = (_SCANNER_ROOT + "/gh-repos-eval/venv-vbt/bin/python"); IAF = (_SCANNER_ROOT + "/trading-frameworks-eval/iaf")
ROOT = (_SCANNER_ROOT + "/research-models/vbt_parity")
COST = {"stock": dict(fee=0.0002, slip=0.0005), "crypto": dict(fee=0.0010, slip=0.0010)}
TOL = 1e-4

def prep(a):
    sys.path.insert(0, _SCANNER_ROOT); import tool_stats as TS
    if a.trades:
        T = pd.read_csv(a.trades)
    else:
        T = TS.load_tracker(a.tracker); T = T[~T.dup_skip & (T.alert_date >= pd.Timestamp(a.since))]
        if "stop_type" in T.columns and not a.all_rows: T = T[T.stop_type.notna() & ~T.stop_type.astype(str).str.startswith("none")]
    T = T.rename(columns={"t": "ticker"}); T["direction"] = T.direction.astype(str).str.upper(); T = T[T.direction.isin(["LONG", "SHORT"])]
    if "asset" not in T.columns: T["asset"] = np.where(T.ticker.astype(str).str.endswith("-USD"), "crypto", "stock")
    T = T[~((T.asset == "crypto") & (T.direction == "SHORT"))]                   # crypto shorts are frozen
    d0 = pd.to_datetime(T.get("entry_date", T.get("alert_date")), errors="coerce"); T["day1_from"] = d0.dt.normalize()
    T = T[T.day1_from.notna()].reset_index(drop=True)
    out = f"{ROOT}/{pd.Timestamp.now(tz='Asia/Jerusalem'):%Y-%m-%d_%H%M%S}"; os.makedirs(f"{out}/bars", exist_ok=True)
    if T.empty: return out, 0
    import yfinance as yf
    start = (T.day1_from.min() - pd.Timedelta(days=120)).strftime("%Y-%m-%d")
    syms = sorted(set(T.ticker.astype(str).str.upper().str.replace(".", "-")))
    Z = yf.download(syms, start=start, interval="1d", auto_adjust=True, progress=False, group_by="ticker", threads=True)
    now = pd.Timestamp.now(tz="UTC"); sys.path.insert(0, _SCANNER_ROOT); import scanner_geometry as GEO
    for s in syms:
        try:
            x = (Z[s] if isinstance(Z.columns, pd.MultiIndex) else Z).dropna(subset=["Close"])
            asset = "crypto" if s.endswith("-USD") else "stock"
            GEO.pit_cut(x, now, asset).to_csv(f"{out}/bars/{s}.csv")                 # only completed bars
        except Exception: pass
    keep = [c for c in ("ticker", "asset", "direction", "day1_from", "atr14_wilder", "tp_half_1618", "alert_date", "source") if c in T.columns]
    T[keep].to_csv(f"{out}/signals.csv", index=False)
    return out, len(T)

# ---------------------------------------------------------------- stage 2 (venv-vbt)
def engine(out):
    sys.path.insert(0, IAF); from stop_rules import ChandelierStop, atr_wilder
    import vectorbt as vbt
    S = pd.read_csv(f"{out}/signals.csv", parse_dates=["day1_from"]); rows = []
    for i, r in S.iterrows():
        s = str(r.ticker).upper().replace(".", "-"); f = f"{out}/bars/{s}.csv"; rec = dict(i=i, ticker=r.ticker, asset=r.asset, direction=r.direction)
        if not os.path.exists(f): rows.append({**rec, "error": "no bars"}); continue
        b = pd.read_csv(f, index_col=0, parse_dates=True); O, H, L, C = (b[k].values.astype(float) for k in ("Open", "High", "Low", "Close"))
        A_all = atr_wilder(H, L, C); k = int(np.searchsorted(b.index, r.day1_from, side="left"))
        if k >= len(b) - 1 or k < 15: rows.append({**rec, "error": f"entry bar k={k} of {len(b)} (not enough bars yet)"}); continue
        A = float(r.atr14_wilder) if "atr14_wilder" in S and pd.notna(r.get("atr14_wilder")) else float(A_all[k - 1])
        sgn = 1 if r.direction == "LONG" else -1; fee, sl = COST[r.asset]["fee"], COST[r.asset]["slip"]; ein = O[k] * (1 + sgn * sl)
        fixed = r.asset == "crypto"; K = 3.0 if fixed else 4.0
        tgt = float(r.tp_half_1618) if (r.asset == "stock" and sgn == 1 and "tp_half_1618" in S and pd.notna(r.get("tp_half_1618"))) else np.nan
        if a.synthetic_target_pct and r.asset == "stock" and sgn == 1: tgt = ein * (1 + a.synthetic_target_pct / 100)   # test path only
        if np.isfinite(tgt) and tgt <= ein: tgt = np.nan
        # ---- reference: stop_rules loop (iaf/sim_ratchet.py, close-based)
        st = ChandelierStop(r.direction, ein, A, k=K, mode="fixed" if fixed else "plain"); st.start(C[k])
        parts = []; rem = 1.0; tq = np.isfinite(tgt); exk = len(C) - 1; status = "open"
        for j in range(k + 1, len(C)):
            if j == k + 1: st.on_close(C[j]); continue
            lv = st.level(A_all[j - 1])
            if sgn * (C[j] - lv) <= 0: parts.append((rem, C[j])); rem = 0; status = "stopped"
            elif tq and C[j] >= tgt: parts.append((0.5, C[j])); rem -= 0.5; tq = False
            if rem <= 1e-9: exk = j; break
            st.on_close(C[j])
        if rem > 1e-9: parts.append((rem, C[-1]))
        ref = sum(q * ((px * (1 - sgn * sl) * (1 - fee)) / (ein * (1 + fee)) - 1 if sgn == 1 else (ein * (1 - fee) - px * (1 - sgn * sl) * (1 + fee)) / (ein * (1 + fee))) for q, px in parts)
        # ---- engine: vectorised stop/target bars + vectorbt fills
        idx = np.arange(len(C)); live = idx >= k; Cs = np.where(live, C * sgn, -np.inf)
        ext = np.maximum.accumulate(Cs); extprev = np.r_[-np.inf, ext[:-1]]
        lvl = np.full(len(C), (ein - sgn * K * A) * sgn) if fixed else extprev - K * np.r_[np.nan, A_all[:-1]]
        chk = idx >= k + 2; stop = chk & (Cs <= lvl)
        js = int(stop.argmax()) if stop.any() else -1
        tg = chk & np.isfinite(tgt) & (C >= tgt) & ~stop; jt = int(tg.argmax()) if tg.any() else -1
        if js >= 0 and jt > js: jt = -1
        sh = 1000 / ein; size = np.full(len(C), np.nan); price = np.full(len(C), np.nan)
        size[k] = sgn * sh; price[k] = O[k]; left = 1.0
        if jt >= 0: size[jt] = -sgn * 0.5 * sh; price[jt] = C[jt]; left = 0.5
        jx = js if js >= 0 else len(C) - 1; size[jx] = -sgn * (1.0 if jx == jt else left) * sh; price[jx] = C[jx]   # target on the last bar: one full exit
        pf = vbt.Portfolio.from_orders(close=pd.Series(C, index=b.index), size=pd.Series(size, index=b.index), price=pd.Series(price, index=b.index),
                                       fees=fee, slippage=sl, init_cash=1e9, direction="both", freq="1D")
        pnl = float(pf.trades.records_readable["PnL"].sum()); eng = pnl / (sh * ein * (1 + fee))
        rows.append({**rec, "entry_date": str(b.index[k].date()), "entry_fill": ein, "atr_entry": A, "target": tgt, "ref_status": status,
                     "ref_exit_date": str(b.index[exk].date()), "vbt_exit_date": str(b.index[jx].date()), "ref_ret": ref, "vbt_ret": eng,
                     "diff_pp": (eng - ref) * 100, "mismatch": bool(abs(eng - ref) > TOL), "days": int(exk - k)})
    R = pd.DataFrame(rows); R.to_csv(f"{out}/parity_trades.csv", index=False)
    ok = R[R.get("ref_ret", pd.Series(dtype=float)).notna()] if "ref_ret" in R else R.iloc[0:0]
    summ = dict(trades=len(R), compared=len(ok), mismatches=int(ok.mismatch.sum()) if len(ok) else 0,
                max_abs_diff_pp=float(ok.diff_pp.abs().max()) if len(ok) else None, skipped=int(len(R) - len(ok)),
                by_segment={f"{a_} {d_}": dict(n=len(g), mismatches=int(g.mismatch.sum()), mean_ref_pct=round(g.ref_ret.mean() * 100, 3),
                            mean_vbt_pct=round(g.vbt_ret.mean() * 100, 3)) for (a_, d_), g in ok.groupby(["asset", "direction"])} if len(ok) else {},
                tolerance_pp=TOL * 100, out=out)
    json.dump(summ, open(f"{out}/parity_summary.json", "w"), indent=1); print(json.dumps(summ, indent=1))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tracker"); ap.add_argument("--trades"); ap.add_argument("--since", default="2026-10-12"); ap.add_argument("--engine")
    ap.add_argument("--all-rows", action="store_true", help="also rows without stop_type (old tracker rows)")
    ap.add_argument("--synthetic-target-pct", type=float, default=0, help="TEST ONLY: target = entry*(1+x%%) for stock longs")
    a = ap.parse_args()
    if a.engine: engine(a.engine); sys.exit(0)
    if not (a.tracker or a.trades): ap.error("--tracker or --trades")
    out, n = prep(a); print(f"{n} trades -> {out}", flush=True)
    if n == 0: print(json.dumps(dict(trades=0, note=f"no new trades since {a.since}"))); sys.exit(0)
    extra = ["--synthetic-target-pct", str(a.synthetic_target_pct)] if a.synthetic_target_pct else []
    sys.exit(subprocess.call([VBT_PY, os.path.abspath(__file__), "--engine", out] + extra))
