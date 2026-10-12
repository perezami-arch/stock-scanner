"""Fetch prices for every ticker in the PIT setups file. Stocks/ETFs: daily adjusted OHLCV (yfinance). Crypto: hourly bars."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, sys, pandas as pd, yfinance as yf
PX = os.environ.get("PIT_PX_DIR", (_SCANNER_ROOT + "/kronos-eval/tracker_eval/px"))
SETUPS = sys.argv[1] if len(sys.argv) > 1 else (_SCANNER_ROOT + "/tracker/setups-point-in-time-2026-10-08.csv")
END = sys.argv[2] if len(sys.argv) > 2 else "2026-10-09"
p = pd.read_csv(SETUPS)
os.makedirs(f"{PX}/stock", exist_ok=True); os.makedirs(f"{PX}/crypto", exist_ok=True)
bad = []
def get(t, kind):
    f = f"{PX}/{kind}/{t}.csv"
    if os.path.exists(f): return
    kw = dict(start="2023-01-01", interval="1d") if kind == "stock" else dict(start="2024-10-20", interval="1h")
    try: x = yf.download(t, end=END, auto_adjust=True, progress=False, **kw)
    except Exception as e: bad.append((t, str(e)[:60])); return
    if isinstance(x.columns, pd.MultiIndex): x.columns = x.columns.get_level_values(0)
    if x.empty: bad.append((t, "empty")); return
    x = x.rename(columns=str.lower)[["open","high","low","close","volume"]].dropna()
    x.index.name = "date" if kind == "stock" else "ts_utc"; x.to_csv(f)
for t in sorted(p[p.asset_class != "crypto"].ticker.dropna().unique()) + ["SPY"]: get(t, "stock")
for t in sorted(p[p.asset_class == "crypto"].ticker.dropna().unique()):
    if t.endswith("-USD"): get(t, "crypto")
    else: bad.append((t, "no Yahoo symbol"))
print("missing/unmapped:", bad)
