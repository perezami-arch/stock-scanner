"""Nightly data prep for the Qlib / FinRL research columns (system python3; yfinance, no API keys).
Universe = the 258 names of the earlier Qlib eval (gh-repos-eval/qlib/qlib_data/instruments/all.txt) + the scanner universe
(/workspace/scan_universe.csv) + every ticker of the latest scan_raw.csv (indices '^' dropped).
Bars: yfinance daily, auto_adjust=True, from 2023-01-01. POINT-IN-TIME: every frame is cut with scanner_geometry.pit_cut at
--asof (default now): a US bar D is kept only if D 16:00 ET <= asof. D = the last complete session of SPY. A ticker whose last
kept bar is not D is dropped (stale), so every model sees exactly the same last bar.
Output: research-models/data/<D>/src_csv/<SYM>.csv (date,symbol,open,high,low,close,volume,vwap,factor) + meta.json.
Note: auto-adjusted history is rescaled backwards on splits/dividends (a level change only; returns/features are unaffected)."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, sys, json, glob, argparse, time
import pandas as pd, numpy as np
sys.path.insert(0, _SCANNER_ROOT)
import scanner_geometry as GEO
ROOT = (_SCANNER_ROOT + "/research-models/data")
def universe():
    u = set(pd.read_csv((_SCANNER_ROOT + "/gh-repos-eval/qlib/qlib_data/instruments/all.txt"), sep="\t", header=None)[0].astype(str))
    try: u |= set(pd.read_csv((_SCANNER_ROOT + "/scan_universe.csv")).t.astype(str))
    except Exception: pass
    runs = sorted(glob.glob((_SCANNER_ROOT + "/scan-runs/20*/scan_raw.csv")))
    if runs: u |= set(pd.read_csv(runs[-1]).t.astype(str))
    return sorted(t.upper() for t in u if not t.startswith("^"))
def sym_key(t): return t.upper().replace(".", "_")           # = research_columns lookup key
def yf_sym(t): return t.upper().replace("_", "-").replace(".", "-")
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--asof"); ap.add_argument("--start", default="2023-01-01"); a = ap.parse_args()
    asof = pd.Timestamp(a.asof) if a.asof else pd.Timestamp.now(tz="UTC")
    asof = asof.tz_localize("UTC") if asof.tzinfo is None else asof.tz_convert("UTC")
    import yfinance as yf
    U = universe(); syms = {yf_sym(t): t for t in U}; t0 = time.time()
    end = (asof + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    Z = yf.download(list(syms) + ["SPY"], start=a.start, end=end, interval="1d", auto_adjust=True, progress=False, group_by="ticker", threads=True)
    spy = GEO.pit_cut(Z["SPY"].dropna(how="all"), asof, "stock"); D = spy.index[-1]
    out = f"{ROOT}/{D.date()}/src_csv"; os.makedirs(out, exist_ok=True)
    for f in glob.glob(f"{out}/*.csv"): os.remove(f)
    kept, dropped = [], {}
    for ys, t in syms.items():
        try:
            x = Z[ys].dropna(subset=["Close"])
            if x.empty: dropped[t] = "no data"; continue
            x = GEO.pit_cut(x, asof, "stock")
            if not len(x) or x.index[-1] != D: dropped[t] = f"stale last bar {x.index[-1].date() if len(x) else None}"; continue
            if len(x) < 120: dropped[t] = f"only {len(x)} bars"; continue
            d = pd.DataFrame({"date": x.index.strftime("%Y-%m-%d"), "symbol": sym_key(t), "open": x.Open, "high": x.High, "low": x.Low,
                              "close": x.Close, "volume": x.Volume.astype(float)})
            d["vwap"] = (d.high + d.low + d.close) / 3; d["factor"] = 1.0
            d.to_csv(f"{out}/{sym_key(t)}.csv", index=False); kept.append(sym_key(t))
        except Exception as e: dropped[t] = f"{e.__class__.__name__}"
    meta = dict(asof_utc=str(asof), bar_date=str(D.date()), n_universe=len(U), n_kept=len(kept), dropped=dropped, seconds=round(time.time() - t0, 1))
    json.dump(meta, open(f"{ROOT}/{D.date()}/meta.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in meta.items() if k != "dropped"}), "dropped:", len(dropped)); print(f"{ROOT}/{D.date()}")
if __name__ == "__main__": main()
