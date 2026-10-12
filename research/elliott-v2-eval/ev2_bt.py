"""Quick PIT comparison Elliott v1 vs v2 (+ re-run of waves with the new >=2-families signal) on the tracker setups (stocks).
Same data/cut as sr-waves-eval/bt.py: Yahoo daily cache, scanner_geometry.pit_cut at asof_ts, last 480 PIT bars (scanner-length).
Outcomes are taken from sr-waves-eval/bt_rows.csv (x20, stop_hit20, chand4_c) - not recomputed here.
Also a PIT leak check: zigzag pivots from the cut frame == pivots of the same frame extended 60 bars into the future with
confirm_idx <= cutoff bar; tentative pivot never appears among the cut frame's confirmed pivots."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, sys, json, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore"); sys.path.insert(0, _SCANNER_ROOT)
import scanner_geometry as GEO, scanner_stops as ST, scanner_elliott_v2 as EV2, scanner_waves as SW, scanner_levels as SL
OUT = (_SCANNER_ROOT + "/elliott-v2-eval"); TODAY = "20261008"
S = pd.read_csv((_SCANNER_ROOT + "/scanner-tool-eval/setups_prepared.csv"))
S = S[(S.asset == "stock") & S.direction.isin(["LONG", "SHORT"]) & S.asof_ts.notna()].copy()
S["cut"] = pd.to_datetime(S.asof_ts, utc=True)
FULL = {}
for t in sorted(S.ticker.unique()):
    f = f"{SL.CACHE}/yahoo_daily/{t}_{TODAY}.csv"
    if os.path.exists(f): FULL[t] = GEO._norm(pd.read_csv(f, parse_dates=["date"]).set_index("date"))
rows, look, leak = [], [], []
for _, s in S.iterrows():
    x = FULL.get(s.ticker)
    if x is None: continue
    h = GEO.pit_cut(x, s["cut"], "stock")
    if len(h) < 120: continue
    h = h.iloc[-480:]
    v1 = ST.fib_elliott(h, "stock", s.direction, entry=s.entry)
    an = EV2.elliott_v2_analysis(h, None, "stock", s.direction); c2 = an["cols"]
    wc = SW.waves_columns(h, None, "stock", s.direction)
    # ---- PIT leak check
    i0 = x.index.get_loc(h.index[0]); i1 = x.index.get_loc(h.index[-1]); ext = x.iloc[i0:i1 + 61]
    a_e = GEO.atr14(ext.High.values, ext.Low.values, ext.Close.values)
    zz_e = [p[:4] for p in GEO.zigzag(ext.High.values, ext.Low.values, a_e, GEO.ZZ) if p[3] <= len(h) - 1]
    zz_c = [p[:4] for p in an.get("known", [])]
    same = len(zz_e) == len(zz_c) and all(a[0] == b[0] and abs(a[1] - b[1]) < 1e-9 and a[2] == b[2] and a[3] == b[3] for a, b in zip(zz_e, zz_c))
    tent = an.get("tent"); tent_in_conf = bool(tent and any(p[2] == tent[2] and p[0] == tent[0] for p in zz_c))
    # does the tentative later become a confirmed pivot (informational: future data, NOT used anywhere)?
    later = None
    if tent:
        zz_f = GEO.zigzag(ext.High.values, ext.Low.values, a_e, GEO.ZZ)
        later = any(p[0] == tent[0] and p[2] == tent[2] for p in zz_f)
    leak.append(dict(setup_id=s.setup_id, pivots_cut=len(zz_c), pivots_ext_le_t=len(zz_e), identical=same, tentative_in_confirmed=tent_in_conf,
                     tentative_confirmed_later_info=later))
    look.append(dict(setup_id=s.setup_id, ticker=s.ticker, direction=s.direction, cutoff_utc=str(s["cut"]), **{k: c2.get(k) for k in c2}))
    r = dict(setup_id=s.setup_id, v1_valid=v1.get("elliott_count_valid"), v1_label=v1.get("elliott_wave_label"), v1_fib_origin=v1.get("fib_leg_origin"),
             **{k: c2.get(k) for k in ("ev2_label", "ev2_state", "ev2_kind", "ev2_provisional", "ev2_beyond_target", "ev2_abc_type", "ev2_context",
                                        "ev2_long_state", "ev2_short_state", "ev2_fib_stale_v1", "ev2_fib_reanchored", "ev2_tentative_kind", "ev2_tentative_move_atr")},
             **{k: wc.get(k) for k in ("wave_end_signal", "wave_end_n", "wave_end_any", "wave_end_families", "wave_start_signal", "wave_start_n",
                                        "wave_start_any", "wave_start_families")})
    rows.append(r)
pd.DataFrame(rows).to_csv(f"{OUT}/ev2_rows.csv", index=False)
pd.DataFrame(leak).to_csv(f"{OUT}/pit_leak_check.csv", index=False)
pd.DataFrame(look).to_csv((_SCANNER_ROOT + "/tracker/elliott_v2_lookup.csv"), index=False, encoding="utf-8-sig")
wv = pd.read_csv((_SCANNER_ROOT + "/tracker/volume_waves_lookup.csv"))
print("rows", len(rows), "leak identical", pd.DataFrame(leak).identical.mean(), "tent in confirmed", pd.DataFrame(leak).tentative_in_confirmed.sum())
