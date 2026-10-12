"""PIT lookups for the tracker (weight 0): liquidity sweep (liq-sweep/liq_sweep.py, daily, intraday=False) and fib spiral
(fib-spiral/fib_spiral.py, SHORT view, daily) at each tracker stock setup's cutoff. Same data/cut as elliott-v2-eval/ev2_bt.py
(Yahoo daily cache, scanner_geometry.pit_cut at asof_ts, last 480 PIT bars).
-> /workspace/tracker/liq_sweep_lookup.csv, /workspace/tracker/fib_spiral_lookup.csv (keyed by setup_id)."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, sys, glob, warnings
import pandas as pd
warnings.filterwarnings("ignore")
for p in (_SCANNER_ROOT, (_SCANNER_ROOT + "/liq-sweep"), (_SCANNER_ROOT + "/fib-spiral")): sys.path.insert(0, p)
import scanner_geometry as GEO, scanner_levels as SL, liq_sweep as LS, fib_spiral as FS
S = pd.read_csv((_SCANNER_ROOT + "/scanner-tool-eval/setups_prepared.csv"))
S = S[(S.asset == "stock") & S.direction.isin(["LONG", "SHORT"]) & S.asof_ts.notna()].copy()
S["cut"] = pd.to_datetime(S.asof_ts, utc=True)
FULL = {}
for t in sorted(S.ticker.unique()):
    fs = sorted(glob.glob(f"{SL.CACHE}/yahoo_daily/{t}_*.csv"))
    if fs: FULL[t] = GEO._norm(pd.read_csv(fs[-1], parse_dates=["date"]).set_index("date"))
ls_rows, fs_rows = [], []
for _, s in S.iterrows():
    x = FULL.get(s.ticker)
    if x is None: continue
    h = GEO.pit_cut(x, s["cut"], "stock")
    if len(h) < 120: continue
    h = h.iloc[-480:]
    base = dict(setup_id=s.setup_id, ticker=s.ticker, direction=s.direction, cutoff_utc=str(s["cut"]), last_bar=str(h.index[-1].date()))
    try: ls_rows.append(dict(base, **LS.liq_sweep_columns(h, None, "stock", intraday=False)))
    except Exception as e: ls_rows.append(dict(base, ls_version=LS.VERSION, ls_error=str(e)[:120]))
    try:
        c = FS.fib_spiral_columns(h, None, "stock", "SHORT")
        fs_rows.append(dict(base, **{k: c.get(k) for k in FS.TRACKER_KEYS}))
    except Exception as e: fs_rows.append(dict(base, fs_version=FS.VERSION, fs_error=str(e)[:120]))
pd.DataFrame(ls_rows).to_csv((_SCANNER_ROOT + "/tracker/liq_sweep_lookup.csv"), index=False, encoding="utf-8-sig")
pd.DataFrame(fs_rows).to_csv((_SCANNER_ROOT + "/tracker/fib_spiral_lookup.csv"), index=False, encoding="utf-8-sig")
L, F = pd.DataFrame(ls_rows), pd.DataFrame(fs_rows)
print("liq_sweep rows", len(L), "sweeps on cutoff bar", int(L.get("ls_sweep", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()))
print("fib_spiral rows", len(F), F.get("fs_state", pd.Series(dtype=str)).value_counts().to_dict())
