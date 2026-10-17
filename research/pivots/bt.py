"""Backtest per research/pivots/PREREG.md (run after the PREREG commit). Writes results.csv / RESULTS.md next to this file."""
import os, sys, math, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", "modules"))
import scanner_pivots as PV, scanner_volphase as VP, scanner_geometry as GEO
from scipy import stats
PX = os.environ.get("PIV_PX", "/workspace/pivots-bt/px")
S = pd.read_csv(os.environ.get("PIV_SETUPS", "/workspace/scanner-tool-eval/setups_prepared.csv"))
S = S[(S.dup_not_counted == False) & S.direction.isin(["LONG", "SHORT"]) & S.asof_ts.notna()].copy()
S["cut"] = pd.to_datetime(S.asof_ts, utc=True)
def load(t):
    f = f"{PX}/{t}.csv"
    return GEO._norm(pd.read_csv(f, parse_dates=["date"]).set_index("date")) if os.path.exists(f) else None
BEN = {"stock": load("SPY"), "crypto": load("BTC-USD")}
def fwd_ret(x, i0, n, sg):
    """dir return from open[i0] to close[i0+n-1]"""
    if i0 is None or i0 + n - 1 >= len(x): return np.nan
    return sg * (x.Close.values[i0 + n - 1] / x.Open.values[i0] - 1)
def bench_ret(asset, d0, n, sg):
    b = BEN[asset]; j = b.index.searchsorted(d0)
    return fwd_ret(b, j, n, sg) if j < len(b) else np.nan
def R_d20(x, i0, sg, stop, n=20):
    if i0 is None or i0 + n - 1 >= len(x): return np.nan, np.nan
    e = x.Open.values[i0]; risk = abs(e - stop)
    if risk <= 0: return np.nan, np.nan
    for k in range(i0, i0 + n):
        if (sg > 0 and x.Low.values[k] <= stop) or (sg < 0 and x.High.values[k] >= stop): return -1.0, 1.0
    return sg * (x.Close.values[i0 + n - 1] - e) / risk, 0.0
def mom(h):
    c = h.Close.values
    return c[-22] / c[-253] - 1 if len(c) >= 253 else np.nan

rows = []
for _, s in S.iterrows():
    x = load(s.ticker)
    if x is None: continue
    asset = s.asset; sg = 1 if s.direction == "LONG" else -1
    h = GEO.pit_cut(x, s["cut"], asset)
    if len(h) < 260: continue
    i_b = len(h)                                    # baseline entry bar index in x (first bar after cutoff bar)
    if i_b >= len(x): continue
    try:
        pc = PV.pivot_columns(h, None, asset, s.direction); vc = VP.volphase_columns(h, None, asset, s.direction)
        Z = PV.confluence(h, s.direction, asset)
    except Exception as e:
        continue
    A = Z["A"]; r = dict(setup_id=s.setup_id, ticker=s.ticker, asset=asset, direction=s.direction, sg=sg, date=str(s.alert_date), crypto=int(asset == "crypto"),
                         dmom=sg * mom(h))
    for n in (5, 20):
        a = fwd_ret(x, i_b, n, sg); b = bench_ret(asset, x.index[i_b], n, sg) if not np.isnan(a) else np.nan
        r[f"x{n}"] = a - b
    sd, td = pc["support_zone_dist_atr"], pc["target_zone_dist_atr"]
    sup_zone = (Z["dn"] if sg > 0 else Z["up"]); ins = Z.get("inside")
    r["F1_at_support"] = int((np.isfinite(sd) and sd <= 1.0) or ins is not None)
    r["F2_blocked"] = int(np.isfinite(td) and td <= 1.5)
    zz = ins if ins is not None else (sup_zone if (np.isfinite(sd) and sd <= 1.0) else None)
    r["F3_support_weekly"] = int(zz is not None and zz["weekly"])
    r["F4_phase_aligned"] = int(vc["dom10_aligned"] == 1)
    r["F5_w_phase_aligned"] = int(vc.get("w_dom10_aligned", 0) == 1)
    r["F6_cmf_aligned"] = int(np.isfinite(vc["cmf20_dir"]) and vc["cmf20_dir"] > 0)
    r["F7_timing_combo"] = int(r["F3_support_weekly"] and vc.get("dom_5") == ("SF" if sg > 0 else "BF"))
    # ---------------- entry simulation
    stop_b = x.Open.values[i_b] - sg * 4 * A
    r["R_base"], r["stop_base"] = R_d20(x, i_b, sg, stop_b)
    z = ins if (ins is not None and ins["weekly"]) else (sup_zone if (sup_zone is not None and sup_zone["weekly"]) else None)
    r["has_zone"] = int(z is not None)
    for var, W, fallback in (("V1", 5, True), ("V2", 10, False)):
        ent = None; skip = 0
        if z is None: ent = i_b
        else:
            st, _, _ = VP.states(x.iloc[:i_b + W + 1]); armed = False
            for k in range(i_b, min(i_b + W, len(x))):
                lo, hi, c, s_k = x.Low.values[k], x.High.values[k], x.Close.values[k], st.iloc[k]
                if sg > 0:
                    if not armed and lo <= z["hi"] and s_k != "SR": armed = True
                    if c < z["lo"] - 0.5 * A: skip = 1; break
                    if armed and (s_k == "BR" or c > z["hi"]): ent = k + 1; break
                else:
                    if not armed and hi >= z["lo"] and s_k != "BR": armed = True
                    if c > z["hi"] + 0.5 * A: skip = 1; break
                    if armed and (s_k == "SR" or c < z["lo"]): ent = k + 1; break
            if ent is None and not skip and fallback: ent = i_b + W
        if ent is not None and ent >= len(x): ent = None
        r[f"{var}_skip"] = int(ent is None); r[f"{var}_delay"] = (ent - i_b) if ent is not None else np.nan
        if ent is not None:
            e = x.Open.values[ent]
            zs = (z["lo"] - 0.25 * A) if (z is not None and sg > 0) else ((z["hi"] + 0.25 * A) if z is not None else None)
            st4 = e - sg * 4 * A
            stop = st4 if zs is None else (max(zs, st4) if sg > 0 else min(zs, st4))
            if (sg > 0 and stop >= e) or (sg < 0 and stop <= e): stop = st4
            r[f"{var}_R"], r[f"{var}_stop"] = R_d20(x, ent, sg, stop)
            for n in (5, 20):
                a = fwd_ret(x, ent, n, sg); b = bench_ret(asset, x.index[ent], n, sg) if not np.isnan(a) else np.nan
                r[f"{var}_x{n}"] = a - b
    rows.append(r)
D = pd.DataFrame(rows); D.to_csv(f"{HERE}/results.csv", index=False)

# ---------------- stats
def ols_cl(y, X, g):
    X = np.column_stack([np.ones(len(y)), X]); b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b
    XtXi = np.linalg.pinv(X.T @ X); meat = np.zeros((X.shape[1],) * 2); G = pd.unique(g)
    for gg in G:
        m = g == gg; u = X[m].T @ e[m]; meat += np.outer(u, u)
    nG = len(G); n, k = X.shape; cf = nG / (nG - 1) * (n - 1) / (n - k)
    V = cf * XtXi @ meat @ XtXi; se = np.sqrt(np.diag(V)); t = b / se
    return b, se, 2 * stats.t.sf(np.abs(t), nG - 1)
def bh(p):
    p = np.asarray(p); o = np.argsort(p); q = np.empty(len(p)); m = len(p); prev = 1
    for r_, i in reversed(list(enumerate(o, 1))): prev = min(prev, p[i] * m / r_); q[i] = prev
    return q
FL = [c for c in D.columns if c.startswith("F")]
res = []
dates = sorted(D.date.unique()); half = dates[len(dates) // 2]
for n in (5, 20):
    for f in FL:
        d = D.dropna(subset=[f"x{n}", "dmom"])
        if d[f].nunique() < 2: continue
        b, se, p = ols_cl(d[f"x{n}"].values, d[[f, "dmom", "crypto"]].values.astype(float), d.date.values)
        h1 = d[d.date < half]; h2 = d[d.date >= half]
        def coef(dd):
            try: return ols_cl(dd[f"x{n}"].values, dd[[f, "dmom", "crypto"]].values.astype(float), dd.date.values)[0][1]
            except Exception: return np.nan
        cut = d[f"x{n}"].quantile(0.95); dw = d[d[f"x{n}"] <= cut]
        res.append(dict(h=n, flag=f, n=len(d), n_flag=int(d[f].sum()), dates_flag=d[d[f] == 1].date.nunique(),
                        mean_flag=d[d[f] == 1][f"x{n}"].mean(), mean_rest=d[d[f] == 0][f"x{n}"].mean(), coef=b[1], p_incr=p[1],
                        wf_h1=coef(h1), wf_h2=coef(h2), coef_no_top5=coef(dw)))
R = pd.DataFrame(res); R["q"] = bh(R.p_incr.values)
R["graduate"] = (R.q < 0.10) & (np.sign(R.wf_h1) == np.sign(R.coef)) & (np.sign(R.wf_h2) == np.sign(R.coef)) & (np.sign(R.coef_no_top5) == np.sign(R.coef)) & (R.dates_flag >= 10)
sim = []
for var in ("V1", "V2"):
    for m, base in ((f"{var}_x5", "x5"), (f"{var}_x20", "x20"), (f"{var}_R", "R_base")):
        d = D[(D.has_zone == 1)].dropna(subset=[m, base]); diff = d[m] - d[base]
        g = d.date.values
        b, se, p = ols_cl(diff.values, np.zeros((len(d), 0)), g) if len(d) > 5 else ([np.nan], [np.nan], [np.nan])
        sim.append(dict(variant=var, metric=m.split("_")[1], n=len(d), dates=d.date.nunique(), timed=d[m].mean(), base=d[base].mean(), diff=diff.mean(), p=p[0]))
SIM = pd.DataFrame(sim); SIM["q"] = bh(SIM.p.values)
Z = D[D.has_zone == 1]
extra = dict(n=len(D), n_zone=len(Z), V1_stop=Z.V1_stop.mean(), V2_stop=Z.V2_stop.mean(), base_stop=Z.stop_base.mean(),
             V2_skip=Z.V2_skip.mean(), V1_triggered=(Z.V1_delay < 5).mean(), V2_delay=Z.V2_delay.median())
with open(f"{HERE}/RESULTS.md", "w") as fh:
    fh.write("# Pivots / confluence / volume phase — backtest per PREREG.md\n\n")
    fh.write(f"Setups evaluated: {extra}\n\n## Feature tests (excess_dir vs SPY/BTC, controls dir×mom12-1 + crypto, clustered by date)\n\n")
    fh.write(R.round(4).to_markdown(index=False) + "\n\n## Entry-timing simulation (setups with a weekly confluence zone; paired vs next-open)\n\n")
    fh.write(SIM.round(4).to_markdown(index=False) + "\n")
print(open(f"{HERE}/RESULTS.md").read())
