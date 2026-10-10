import pandas as pd, numpy as np
R = pd.read_csv("bt_rows.csv")
R = R[R.err.isna()] if "err" in R else R
base = R[(R.excluded.isna()) & (R.dup != True)].copy()           # tracker counting rules: no MCAP<1.5B, no duplicates
base["day"] = base.cutoff_bar
out = []
def boot_diff(a, b, da, db, n=2000, seed=0):
    """day-clustered bootstrap of mean(a)-mean(b)"""
    rng = np.random.default_rng(seed); A = pd.DataFrame({"v": a, "d": da}); B = pd.DataFrame({"v": b, "d": db})
    dA, dB = A.d.unique(), B.d.unique(); ds = []
    gA = {k: g.v.values for k, g in A.groupby("d")}; gB = {k: g.v.values for k, g in B.groupby("d")}
    for _ in range(n):
        sa = np.concatenate([gA[k] for k in rng.choice(dA, len(dA))]); sb = np.concatenate([gB[k] for k in rng.choice(dB, len(dB))])
        ds.append(sa.mean() - sb.mean())
    ds = np.array(ds); return np.mean(ds <= 0) * 2 if np.mean(ds) > 0 else np.mean(ds >= 0) * 2
def cmp(df, flag, metric, label):
    d = df[df[flag].notna() & df[metric].notna()]
    a = d[d[flag].astype(bool)]; b = d[~d[flag].astype(bool)]
    if len(a) < 5 or len(b) < 5: out.append(dict(test=label, flag=flag, metric=metric, n_yes=len(a), n_no=len(b), note="too few")); return
    va, vb = a[metric].astype(float), b[metric].astype(float)
    p = boot_diff(va.values, vb.values, a.day.values, b.day.values)
    out.append(dict(test=label, flag=flag, metric=metric, n_yes=len(a), days_yes=a.day.nunique(), mean_yes=round(va.mean(), 4),
                    n_no=len(b), days_no=b.day.nunique(), mean_no=round(vb.mean(), 4), diff=round(va.mean() - vb.mean(), 4),
                    p_day_boot=round(min(1, p), 3)))
for b_ in (base,):
    b_["stop_hit20_f"] = b_.stop_hit20.map({True: 1.0, False: 0.0})
    b_["tp1_hit"] = b_.out_tp1.map({"target": 1.0, "stop": 0.0, "time": 0.0})
    b_["ch4_stop"] = b_.chand4_stopped.map({True: 1.0, False: 0.0})
    cmp(b_, "stop_beyond_strong", "stop_hit20_f", "S/R H1: tracker stop placed beyond a strong level -> stop hit within 20 bars")
    cmp(b_, "stop_beyond_strong", "x20", "S/R H1: ... -> day-20 excess return")
    cmp(b_, "stop_beyond_strong", "ret_tp1", "S/R H1: ... -> tracker stop/tp1 trade return")
    cmp(b_, "strong_level_before_tp1", "tp1_hit", "S/R H2: strong level between entry and tp1 -> tp1 hit within 20 bars")
    cmp(b_, "strong_level_before_tp1", "x20", "S/R H2: ... -> day-20 excess return")
    for f in ("wave_end_signal", "wave_start_signal", "wz_exhaustion_with", "ww_exhaustion_with", "wz_counter_gt_with", "ww_counter_gt_with", "div_against"):
        cmp(b_, f, "ch4_stop", f"WAVES: {f} -> stopped by 4xATR chandelier (sim_chand chand4_c)")
        cmp(b_, f, "x20", f"WAVES: {f} -> day-20 excess return")
T = pd.DataFrame(out)
# H2 paired: capped target vs tp1 on the setups with a strong level before tp1
c = base[base.strong_level_before_tp1.astype(str).eq("True") & base.ret_cap.notna() & base.ret_tp1.notna()]
d = c.ret_cap - c.ret_tp1
pair = dict(n=len(c), days=c.day.nunique(), mean_tp1=round(c.ret_tp1.mean(), 4), mean_capped=round(c.ret_cap.mean(), 4), mean_diff=round(d.mean(), 4),
            p_day_boot=round(boot_diff(c.ret_cap.values, c.ret_tp1.values, c.day.values, c.day.values), 3) if len(c) >= 5 else None,
            hit_tp1=round((c.out_tp1 == "target").mean(), 3), hit_cap=round((c.out_cap == "target").mean(), 3))
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 90)
print("base N", len(base), "distinct cutoff days", base.day.nunique(), "LONG", (base.direction == "LONG").sum(), "SHORT", (base.direction == "SHORT").sum())
print(T.to_string(index=False)); print("H2 paired capped-vs-tp1:", pair)
for dirn in ("LONG", "SHORT"):
    sub = base[base.direction == dirn]
    print(dirn, "wave_end rate", round(sub.wave_end_signal.astype(str).eq("True").mean(), 3), "stop_beyond_strong rate", round(sub.stop_beyond_strong.astype(str).eq("True").mean(), 3))
T.to_csv("results_table.csv", index=False); pd.Series(pair).to_csv("h2_paired.csv")
