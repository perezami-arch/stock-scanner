"""tool_stats excess metric: prefers the build7 column excess_dir_d20, falls back to sgn x (ret - bench) when it is missing/blank.
Run: /usr/bin/python3 research-models/tests/test_tool_stats_excess.py   (also pytest-compatible)"""
import sys, os, tempfile
import numpy as np, pandas as pd
sys.path.insert(0, "/workspace")
import tool_stats as TS

def _fake_bench(sym):            # flat 1% per session -> bench_d20 = 1.01**20 - 1 for any alert date
    idx = pd.bdate_range("2026-06-01", "2026-12-31")
    return pd.Series(100 * 1.01 ** np.arange(len(idx)), index=idx)

def _tracker(with_col, blank_one=False):
    rows = []
    for i, (t, d, r20) in enumerate([("AAA", "LONG", 0.10), ("BBB", "SHORT", 0.05), ("CCC", "SHORT", -0.04), ("DDD", "LONG", -0.02)]):
        r = {"ticker": t, "alert_date": "2026-08-03", "direction": d, **{f"cum_d{k}": r20 * k / 20 for k in range(1, 21)}}
        if with_col: r["excess_dir_d20"] = 0.5 + i      # sentinel values, clearly different from the computed ones
        rows.append(r)
    x = pd.DataFrame(rows)
    if with_col and blank_one: x.loc[2, "excess_dir_d20"] = np.nan
    return x

def _outcomes(df):
    orig = TS.bench_series; TS.bench_series = _fake_bench
    try:
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.csv"); df.to_csv(p, index=False)
            return TS.add_outcomes(TS.load_tracker(p))
    finally: TS.bench_series = orig

B20 = 1.01 ** 20 - 1

def test_fallback_directional():
    x = _outcomes(_tracker(False))
    sgn = np.where(x.direction.eq("SHORT"), -1, 1)
    assert np.allclose(x.bench_d20, B20)
    assert np.allclose(x.excess_d20, x.ret_d20 - sgn * B20)          # = sgn x (stock - SPY); short: SPY - stock
    assert (x.excess_src_d20 == "computed").all()
    # short with cum (already direction-adjusted) +5%: stock fell 5% -> excess = 0.05 + B20
    assert abs(x.loc[x.ticker.eq("BBB"), "excess_d20"].item() - (0.05 + B20)) < 1e-12

def test_column_preferred():
    x = _outcomes(_tracker(True))
    assert np.allclose(x.excess_d20, [0.5, 1.5, 2.5, 3.5]) and (x.excess_src_d20 == "excess_dir_d20").all()
    assert np.allclose(x.excess_d10, x.ret_d10 - np.where(x.direction.eq("SHORT"), -1, 1) * (1.01 ** 10 - 1))   # other horizons untouched

def test_blank_cell_falls_back():
    x = _outcomes(_tracker(True, blank_one=True))
    c = x.ticker.eq("CCC")
    assert x.loc[c, "excess_src_d20"].item() == "computed" and abs(x.loc[c, "excess_d20"].item() - (-0.04 + B20)) < 1e-12
    assert (x.loc[~c, "excess_src_d20"] == "excess_dir_d20").all()

def test_hebrew_header_maps():
    assert TS._norm_head("תשואה עודפת מכוונת מול SPY ביום 20 (excess_dir_d20, מדד ראשי)") == "excess_dir_d20"

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f(); print("PASS", n)
