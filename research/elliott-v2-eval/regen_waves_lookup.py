"""Regenerate /workspace/tracker/volume_waves_lookup.csv with the >=2-families wave_end/start signal (same PIT cut as bt.py)."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, sys, warnings, pandas as pd
warnings.filterwarnings("ignore"); sys.path.insert(0, _SCANNER_ROOT)
import scanner_geometry as GEO, scanner_waves as SW, scanner_levels as SL
S = pd.read_csv((_SCANNER_ROOT + "/scanner-tool-eval/setups_prepared.csv"))
S = S[(S.asset == "stock") & S.direction.isin(["LONG", "SHORT"]) & S.asof_ts.notna()].copy(); S["cut"] = pd.to_datetime(S.asof_ts, utc=True)
F = {}; out = []
for _, s in S.iterrows():
    f = f"{SL.CACHE}/yahoo_daily/{s.ticker}_20261008.csv"
    if not os.path.exists(f): continue
    if s.ticker not in F: F[s.ticker] = GEO._norm(pd.read_csv(f, parse_dates=["date"]).set_index("date"))
    h = GEO.pit_cut(F[s.ticker], s["cut"], "stock")
    if len(h) < 120: continue
    out.append(dict(setup_id=s.setup_id, ticker=s.ticker, direction=s.direction, cutoff_utc=str(s["cut"]), **SW.waves_columns(h.iloc[-480:], None, "stock", s.direction)))
pd.DataFrame(out).to_csv((_SCANNER_ROOT + "/tracker/volume_waves_lookup.csv"), index=False, encoding="utf-8-sig"); print("rows", len(out))
