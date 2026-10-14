import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import sys, pandas as pd, numpy as np
sys.path.insert(0, (_SCANNER_ROOT + "/sr-waves-eval"))
O = (_SCANNER_ROOT + "/elliott-v2-eval")
B = pd.read_csv((_SCANNER_ROOT + "/sr-waves-eval/bt_rows.csv")); B = B[B.err.isna()] if "err" in B else B
E = pd.read_csv(f"{O}/ev2_rows.csv")
W0 = B[["setup_id", "wave_end_signal"]].rename(columns={"wave_end_signal": "wave_end_old_any"})
D = B[["setup_id", "ticker", "direction", "cutoff_bar", "excluded", "dup", "x20", "stop_hit20", "chand4_stopped", "chand4_ret"]].merge(E, on="setup_id").merge(W0, on="setup_id")
base = D[D.excluded.isna() & (D.dup != True)].copy(); base["day"] = base.cutoff_bar
base["ch4_stop"] = base.chand4_stopped.map({True: 1.0, False: 0.0, "True": 1.0, "False": 0.0})
def boot_p(a, da, b, db, n=2000, seed=0):
    rng = np.random.default_rng(seed); gA = pd.Series(a).groupby(da).apply(np.array).to_dict(); gB = pd.Series(b).groupby(db).apply(np.array).to_dict()
    kA, kB = list(gA), list(gB); ds = []
    for _ in range(n):
        ds.append(np.concatenate([gA[k] for k in rng.choice(kA, len(kA))]).mean() - np.concatenate([gB[k] for k in rng.choice(kB, len(kB))]).mean())
    ds = np.array(ds); return min(1, 2 * (np.mean(ds <= 0) if ds.mean() > 0 else np.mean(ds >= 0)))
L = []
L.append(f"base N={len(base)} days={base.day.nunique()} LONG={int((base.direction=='LONG').sum())} SHORT={int((base.direction=='SHORT').sum())}")
L.append(f"PIT leak check: " + pd.read_csv(f"{O}/pit_leak_check.csv").agg({"identical": "mean", "tentative_in_confirmed": "sum", "tentative_confirmed_later_info": "mean"}).to_string().replace("\n", " | "))
# coverage
v1v = base.v1_valid.astype(str).eq("True"); v2v = base.ev2_state.ne("none")
L.append(f"\nCOVERAGE (trade-direction view): v1 valid {v1v.sum()}/{len(base)} = {v1v.mean():.1%}; v2 any count {v2v.sum()}/{len(base)} = {v2v.mean():.1%}")
L.append("v2 state:\n" + base.ev2_state.value_counts().to_string())
def lt(s):
    if not isinstance(s, str) or s == "no valid count": return "none"
    k = s.split(":")[0].replace(" (provisional)", "").replace(" / beyond target", "")
    for a in ("W2 in progress", "W3 in progress", "W4 in progress", "W5 in progress"): 
        if s.startswith(a): return a + (" /beyond" if "beyond" in s else "")
    if s.startswith("W") and " done" in s: return s.split(" (")[0]
    return k + (" [prov]" if "provisional" in s else "")
base["ev2_type"] = base.ev2_label.map(lt)
L.append("v2 label type:\n" + base.ev2_type.value_counts().to_string())
L.append("v1 valid x v2 state:\n" + pd.crosstab(v1v.map({True: "v1 valid", False: "v1 none"}), base.ev2_state).to_string())
L.append(f"v1 Fib leg stale (v2 re-anchored): stale {base.ev2_fib_stale_v1.astype(str).eq('True').sum()}, re-anchored {base.ev2_fib_reanchored.astype(str).eq('True').sum()} of {len(base)}")
L.append(f"tentative pivot present: {base.ev2_tentative_kind.notna().sum()} of {len(base)}")
# outcomes by state
def grp(col, name):
    g = base.groupby(col).agg(N=("x20", "size"), days=("day", "nunique"), x20_mean=("x20", "mean"), ch4_stop=("ch4_stop", "mean"), ch4_ret=("chand4_ret", "mean"))
    L.append(f"\nOUTCOMES by {name} (x20 = day-20 excess return; ch4 = sim_chand chand4_c):\n" + g.round(4).to_string())
grp("ev2_state", "v2 state"); grp("ev2_type", "v2 label type")
base["v1_valid_s"] = v1v.map({True: "v1 valid", False: "v1 none"}); grp("v1_valid_s", "v1 validity")
# tests: each state vs the rest
L.append("\nTESTS (state vs rest, day-clustered bootstrap, no FDR):")
for col, vals in (("ev2_state", base.ev2_state.unique()), ("v1_valid_s", ["v1 valid"]), ("ev2_beyond_target", [True])):
    for v in vals:
        m = base[col].astype(str).eq(str(v))
        for met in ("x20", "ch4_stop"):
            d = base[base[met].notna()]; mm = d[col].astype(str).eq(str(v))
            if mm.sum() < 10 or (~mm).sum() < 10: continue
            p = boot_p(d[mm][met].values, d[mm].day.values, d[~mm][met].values, d[~mm].day.values)
            L.append(f"  {col}={v} {met}: yes N={mm.sum()} ({d[mm].day.nunique()}d) mean={d[mm][met].mean():.4f} | rest N={(~mm).sum()} mean={d[~mm][met].mean():.4f} | p={p:.3f}")
# waves families
L.append("\nWAVES: old any-reason signal vs new >=2-families signal")
for nm, col in (("old wave_end (any reason)", "wave_end_old_any"), ("new wave_end_signal (>=2 families)", "wave_end_signal"), ("new wave_start_signal (>=2 families)", "wave_start_signal")):
    f = base[col].astype(str).eq("True")
    L.append(f"  {nm}: fires {f.sum()}/{len(base)} = {f.mean():.1%}")
    for met in ("x20", "ch4_stop"):
        d = base[base[met].notna()]; mm = d[col].astype(str).eq("True")
        if mm.sum() >= 10 and (~mm).sum() >= 10:
            p = boot_p(d[mm][met].values, d[mm].day.values, d[~mm][met].values, d[~mm].day.values)
            L.append(f"     {met}: on N={mm.sum()} ({d[mm].day.nunique()}d) {d[mm][met].mean():.4f} vs off N={(~mm).sum()} {d[~mm][met].mean():.4f} p={p:.3f}")
L.append("  wave_end_n distribution:\n" + base.wave_end_n.value_counts().sort_index().to_string())
txt = "\n".join(L); print(txt); open(f"{O}/results.txt", "w").write(txt); base.to_csv(f"{O}/base_merged.csv", index=False)
