import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import sys, json, math, numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, _SCANNER_ROOT); sys.path.insert(0, (_SCANNER_ROOT + "/tradingview/validation"))
import scanner_stops as SS
from pine_port import PinePort, isna
CACHE = (_SCANNER_ROOT + "/scanner-momentum-cache/20261008T1029Z")
OUT = pd.read_csv((_SCANNER_ROOT + "/scan-runs/stops-test/stops_out.csv")).set_index("ticker")
TICK = [("MU", "stock", "stock/MU.csv"), ("CVX", "stock", "stock/CVX.csv"), ("NVDA", "stock", "stock/NVDA.csv"), ("BTC", "crypto", "crypto_daily/BTC-USD.csv")]
MAP = dict(fib_leg_origin="leg_o", fib_leg_end="leg_e", fib_r382="r382", fib_r500="r500", fib_r618="r618", fib_r786="r786",
           fib_tp_1272="x1272", fib_tp_1618="x1618", fib_tp_2618="x2618", fib_stop_struct="struct", fib_stop_fallback="struct_fb",
           tp_half_1618="tp_half", elliott_wave_label="wave", elliott_fib_deviations="wave_dev", elliott_n_valid_counts="n_valid",
           elliott_target_w3="ew3", elliott_target_w5="ew5")

def load(path, asset, end="2026-10-07"):
    x = pd.read_csv(f"{CACHE}/{path}", parse_dates=["date"]).set_index("date")
    x = x[x.index <= end]
    return x.rename(columns=str.title)[["Open", "High", "Low", "Close"]].dropna(subset=["Close"])

def run(x, sgn=1, entry_idx=None, entry_px=None, mode="chandelier", K=4.0, upto=None):
    p = PinePort(sgn=sgn, trail_mult=K, entry_idx=entry_idx, entry_px=entry_px, mode=mode)
    snaps = []
    for i, (o, h, l, c) in enumerate(x[["Open", "High", "Low", "Close"]].values):
        p.step(o, h, l, c); snaps.append(dict(p.out))
    return p, snaps

def same(a, b, tol=1e-3):
    if isinstance(a, str) or isinstance(b, str): return str(a) == str(b)
    if isinstance(a, (bool, np.bool_)) or isinstance(b, (bool, np.bool_)): return bool(a) == bool(b)
    if isna(a) and isna(b): return True
    if isna(a) or isna(b): return False
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b))) * 1e-3 + 1e-4

def cmp_final(port_out, row):
    diffs = []
    for csv_c, pk in MAP.items():
        if csv_c == "tp_half_1618" and row["asset"] != "stock": continue     # scanner computes it for stock longs only
        cv = row[csv_c]; pv = port_out.get(pk)
        if csv_c == "elliott_fib_deviations" and pd.isna(cv): cv = None
        if csv_c == "fib_stop_fallback": cv = str(cv) == "True"
        if not same(pv if pv is not None else float("nan"), cv if cv is not None else float("nan")):
            diffs.append((csv_c, cv, pv))
    return diffs

if __name__ == "__main__":
    report = []
    print("=== A. Same bars the scanner used (cache 20261008T1029Z), final bar 2026-10-07 vs stops_out.csv ===")
    for t, asset, path in TICK:
        x = load(path, asset); p, snaps = run(x)
        d = cmp_final(snaps[-1], OUT.loc[t])
        piv = [[("H" if k == 1 else "L"), round(pp, 4), str(x.index[i].date()), str(x.index[cc].date())] for k, pp, i, cc in zip(p.pK, p.pP, p.pI, p.pC)][-6:]
        pv_ok = piv == json.loads(OUT.loc[t, "pivots_confirmed"])
        print(f"{t}: bars={len(x)} fields compared={len(MAP)} mismatches={len(d)} last-6 pivots identical={pv_ok}  wave={snaps[-1]['wave']}")
        for m in d: print("    MISMATCH", m)
        report.append(dict(test="A_same_bars", ticker=t, bars=len(x), mismatches=len(d), pivots_identical=pv_ok))

    print("\n=== B. Every bar of the last 250: port state vs scanner_stops.fib_elliott/half_at_1618 on the truncated history ===")
    for t, asset, path in TICK:
        x = load(path, asset); p, snaps = run(x); bad = 0; nb = 0
        for j in range(len(x) - 250, len(x)):
            xs = x.iloc[:j + 1]
            r = SS.fib_elliott(xs, asset, "LONG"); r.update(SS.half_at_1618(xs, float(xs.Close.iloc[-1])))
            r["asset"] = "stock"   # compare tp_half on every ticker here
            row = pd.Series(r)
            d = cmp_final(snaps[j], row); nb += 1; bad += bool(d)
            if d and bad <= 3: print(f"  {t} {xs.index[-1].date()} {d}")
        # short side too
        pS, snS = run(x, sgn=-1); badS = 0
        for j in range(len(x) - 250, len(x)):
            xs = x.iloc[:j + 1]; r = SS.fib_elliott(xs, asset, "SHORT"); r["asset"] = "crypto"
            d = cmp_final(snS[j], pd.Series(r)); badS += bool(d)
            if d and badS <= 3: print(f"  {t} SHORT {xs.index[-1].date()} {d}")
        print(f"{t}: LONG bars with any mismatch {bad}/{nb};  SHORT bars with any mismatch {badS}/{nb}")
        report.append(dict(test="B_every_bar_250", ticker=t, bars=nb, mismatch_bars_long=bad, mismatch_bars_short=badS))

    print("\n=== C. Reference stop vs scanner_stops.stop_status (hypothetical entries) ===")
    for t, asset, path in TICK:
        x = load(path, asset)
        for ed in ("2026-07-01", "2026-08-14", "2026-09-15", "2026-10-06", "2026-10-07"):
            k = int(np.searchsorted(x.index.values, np.datetime64(pd.Timestamp(ed)), side="left")); epx = float(x.Open.iloc[k])
            mode, K = ("chandelier", 4.0) if asset == "stock" else ("fixed", 3.0)
            p, _ = run(x, entry_idx=k, entry_px=epx, mode=mode, K=K)
            ss = SS.stop_status(x, asset, "LONG", ed, epx)
            ok = same(p.trail, ss["next_level"]) and bool(p.stopped) == bool(ss["stopped"])
            print(f"  {t} entry {ed} @ {epx:.2f} {mode} {K}x: port level={p.trail:.4f} stopped={p.stopped} | scanner next_level={ss['next_level']} stopped={ss['stopped']} -> {'OK' if ok else 'DIFF'}")
            report.append(dict(test="C_stop", ticker=t, entry=ed, ok=ok))
    x = load("stock/CVX.csv", "stock"); k = len(x) - 1
    p, _ = run(x, entry_idx=k, entry_px=208.8); print(f"  CVX live row (entry 2026-10-07 @208.8): port={p.trail:.4f} csv live_next_level={OUT.loc['CVX','live_next_level']}")
    pd.DataFrame(report).to_csv((_SCANNER_ROOT + "/tradingview/validation/validation_summary.csv"), index=False)
