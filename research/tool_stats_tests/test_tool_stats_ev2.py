"""tool_stats auto-detects the Elliott v2 columns (scanner_elliott_v2, 08.10): exp_ev2_* from build7 -> tool 'elliott_v2'; price / text /
tautological ev2 columns are not tested; raw ev2_long_*/ev2_short_* (scan_hooks.csv) -> trade-direction exp_ev2_* (tracker values win).
Run: /usr/bin/python3 research-models/tests/test_tool_stats_ev2.py   (also pytest-compatible)"""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import sys, os, tempfile
import numpy as np, pandas as pd
sys.path.insert(0, _SCANNER_ROOT)
import tool_stats as TS

def _fake_bench(sym):
    idx = pd.bdate_range("2026-06-01", "2026-12-31"); return pd.Series(100 * 1.01 ** np.arange(len(idx)), index=idx)

def _tracker(n=60):
    rng = np.random.default_rng(1); rows = []
    for i in range(n):
        d = "LONG" if i % 2 else "SHORT"; r20 = rng.normal(0, 0.05)
        rows.append({"ticker": f"T{i % 25:02d}", "alert_date": str(pd.Timestamp("2026-07-01") + pd.Timedelta(days=i % 9)), "direction": d,
                     **{f"cum_d{k}": r20 * k / 20 for k in range(1, 21)},
                     "exp_ev2_state": ["abc_confirmed", "abc_provisional", "impulse_provisional", "none"][i % 4],
                     "exp_ev2_kind": ["abc", "abc", "impulse", None][i % 4], "exp_ev2_abc_type": ["zigzag", "flat", None, None][i % 4],
                     "exp_ev2_context": ["W2", "W2", None, None][i % 4], "exp_ev2_beyond_target": [True, False, False, None][i % 4],
                     "exp_ev2_fib_stale_v1": bool(i % 3), "exp_ev2_fib_reanchored": bool(i % 5), "exp_ev2_tentative_move_atr": 2 + (i % 7) * 0.5,
                     "exp_ev2_provisional": True, "exp_ev2_tentative_kind": "L" if d == "LONG" else "H", "exp_ev2_target": 100 + i,
                     "exp_ev2_fib_r618": 50 + i, "exp_ev2_label": f"W2 in progress {i}", "exp_ev2_long_state": "impulse_provisional",
                     "exp_ev2_tentative_price": 99.0 + i, "exp_ev2_last_bar": "2026-06-30"})
    return pd.DataFrame(rows)

def _run(df):
    orig = TS.bench_series; TS.bench_series = _fake_bench
    try:
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.csv"); df.to_csv(p, index=False)
            x = TS.add_outcomes(TS.ev2_trade_view(TS.load_tracker(p)))
            return TS.compute(x, since="2026-06-01", min_side=5)
    finally: TS.bench_series = orig

def test_detects_ev2_columns():
    T = _run(_tracker()); ev = T[T.tool.eq("elliott_v2")]
    got = set(ev.column)
    assert got == {"exp_ev2_state", "exp_ev2_kind", "exp_ev2_abc_type", "exp_ev2_context", "exp_ev2_beyond_target",
                   "exp_ev2_fib_stale_v1", "exp_ev2_fib_reanchored", "exp_ev2_tentative_move_atr"}, got
    assert set(ev[ev.column.eq("exp_ev2_state")].test) >= {"== abc_confirmed", "== abc_provisional", "== none"}
    assert ev[ev.column.eq("exp_ev2_beyond_target")].kind.eq("flag").all()
    assert ev[ev.column.eq("exp_ev2_tentative_move_atr")].kind.eq("num").all()

def test_excluded_columns_not_tested():
    T = _run(_tracker())
    for c in ("exp_ev2_provisional", "exp_ev2_tentative_kind", "exp_ev2_target", "exp_ev2_fib_r618", "exp_ev2_label", "exp_ev2_long_state",
              "exp_ev2_tentative_price", "exp_ev2_last_bar"):
        assert c not in set(T.column), c

def test_trade_view_from_raw_views():
    x = pd.DataFrame({"ticker": ["A", "B", "C"], "direction": ["LONG", "SHORT", "SHORT"],
                      "ev2_long_state": ["impulse_provisional", "abc_confirmed", "none"], "ev2_short_state": ["none", "abc_provisional", "abc_confirmed"],
                      "ev2_state": ["impulse_provisional", "abc_confirmed", "none"],          # LONG view in scan_hooks.csv - must NOT be used for shorts
                      "exp_ev2_state": [None, None, "impulse_confirmed"], "ev2_tentative_move_atr": [2.5, 3.0, 4.0]})
    y = TS.ev2_trade_view(x)
    assert list(y.exp_ev2_state) == ["impulse_provisional", "abc_provisional", "impulse_confirmed"]   # long view / short view / tracker wins
    assert list(y.exp_ev2_tentative_move_atr) == [2.5, 3.0, 4.0]
    assert TS.tool_of("exp_ev2_state") == "elliott_v2" and not TS.INCLUDE_RE.match("ev2_state")       # raw LONG-view column never tested

def test_no_ev2_columns_is_noop():
    x = pd.DataFrame({"ticker": ["A"], "direction": ["LONG"], "exp_foo_x": [1]})
    assert TS.ev2_trade_view(x) is x

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f(); print("PASS", n)
