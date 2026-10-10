import sys, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, "/workspace"); sys.path.insert(0, "/workspace/tradingview/validation")
import scanner_stops as SS
from validate import load, run, same, TICK
tot = ok = nstop = 0
for t, asset, path in TICK:
    x = load(path, asset)
    for d, sgn in (("LONG", 1), ("SHORT", -1)):
        if asset == "crypto" and d == "SHORT": continue
        for k in range(len(x) - 250, len(x), 3):
            ed = str(x.index[k].date()); epx = float(x.Open.iloc[k])
            mode, K = ("chandelier", 4.0) if asset == "stock" else ("fixed", 3.0)
            p, _ = run(x, sgn=sgn, entry_idx=k, entry_px=epx, mode=mode, K=K)
            ss = SS.stop_status(x, asset, d, ed, epx)
            good = same(p.trail, ss["next_level"]) and bool(p.stopped) == bool(ss["stopped"])
            tot += 1; ok += good; nstop += bool(ss["stopped"])
            if not good: print("DIFF", t, d, ed, p.trail, p.stopped, ss)
print(f"stop sweep: {ok}/{tot} identical (level + stopped flag); {nstop} of them were stopped trades")
