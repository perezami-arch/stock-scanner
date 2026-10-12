"""Score every prepared setup with one or more tools. usage: python run_tools.py rw mom121 lowvol chronos2 timesfm kronos-small ...
Writes forecasts/<key>.csv (setup_id, f5, f20, ftot) + forecasts/<key>.meta.json (runtime, peak RAM)."""
import sys, os, json, time, resource, numpy as np, pandas as pd
import tools
from tools.base import REGISTRY
def make(key):
    if key in REGISTRY: return REGISTRY[key]()
    from tools import ts_models as T
    if key.startswith("kronos-"):   # kronos-small or kronos-small-lb128
        parts = key.split("-"); lb = int(parts[2][2:]) if len(parts) > 2 else T.LOOKBACK
        return T.KronosTool(parts[1], lookback=lb)
    return {"chronos2": T.Chronos2Tool, "timesfm": T.TimesFMTool}[key]()
df = pd.read_csv("setups_prepared.csv"); df = df[df.realized_source != "none"]
df["asof_ts"] = pd.to_datetime(df["asof_ts"], utc=True)
os.makedirs("forecasts", exist_ok=True)
for key in sys.argv[1:]:
    t0 = time.time(); tool = make(key); load = time.time() - t0
    out = {"setup_id": df.setup_id.values}
    for col, hz in [("f5", np.full(len(df), 5)), ("f20", np.full(len(df), 20)), ("ftot", df["ntot"].clip(1, 20).fillna(20).astype(int).values)]:
        out[col] = tool.score_batch(list(zip(df.ticker, df.asset, df.asof_ts, hz)))
    pd.DataFrame(out).to_csv(f"forecasts/{key}.csv", index=False)
    meta = {"tool": tool.name, "key": key, "n": len(df), "load_s": round(load, 1), "total_s": round(time.time() - t0, 1),
            "sec_per_series": round(float(np.mean(tool.timing)), 3) if getattr(tool, "timing", None) else None,
            "unique_series": len(getattr(tool, "cache", {})) or None,
            "peak_rss_mb_process": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)}
    json.dump(meta, open(f"forecasts/{key}.meta.json", "w"), indent=2); print(meta, flush=True)
    del tool
