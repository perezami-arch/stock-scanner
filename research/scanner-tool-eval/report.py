"""Metrics + markdown report for scanner setups. usage: python report.py [out.md]
Every tool score is direction-adjusted (SHORT setups flip sign), so 'keep' = tool agrees with the setup's direction."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, sys, json, glob, numpy as np, pandas as pd
from scipy import stats
OUT = sys.argv[1] if len(sys.argv) > 1 else "tracker_eval.md"
rng = np.random.default_rng(0); NB = 1000
df = pd.read_csv("setups_prepared.csv"); df = df[df.realized_source != "none"].copy()
df["aclass"] = np.where(df.asset == "crypto", "crypto", "stock/etf")
# old hold-no-stop CSV return (longs) for the linked rows, joined on ticker+alert_date when unambiguous
old = pd.read_csv((_SCANNER_ROOT + "/tracker/hold-no-stop-longs-2026-10-08.csv"))
old = old.drop_duplicates(["ticker", "alert_date"], keep=False)[["ticker", "alert_date", "return_pct"]]
df = df.merge(old, on=["ticker", "alert_date"], how="left")
df.loc[df["in_hold_no_stop_csv"] != True, "return_pct"] = np.nan
df["rhns"] = df["return_pct"] / 100

TOOLS = {}
for f in sorted(glob.glob("forecasts/*.csv")):
    k = os.path.basename(f)[:-4]; m = json.load(open(f[:-4] + ".meta.json"))
    TOOLS[k] = m["tool"]; df = df.merge(pd.read_csv(f).rename(columns={c: f"{k}__{c}" for c in ["f5", "f20", "ftot"]}), on="setup_id", how="left")
RANK_ONLY = {"mom121", "lowvol"}
TARGETS = [("r5", "f5", "day-5 return"), ("r20", "f20", "day-20 return"), ("rtot", "ftot", "total (last day <=20)"),
           ("x5", "f5", "day-5 EXCESS vs SPY/BTC"), ("x20", "f20", "day-20 EXCESS vs SPY/BTC"), ("xtot", "ftot", "total EXCESS vs SPY/BTC"),
           ("xeth_tot", "ftot", "total EXCESS vs ETH (crypto only)"), ("rhns", "ftot", "old hold-no-stop return_pct (longs)")]

def dir_score(k, fcol, d):
    """Direction-adjusted score. Return-forecast tools: dir_sign * forecast (keep if > 0).
    Rank-only factors: dir_sign * (within-asset-class percentile - 0.5) (keep if in the favourable half)."""
    v = d[f"{k}__{fcol}"]
    if k in RANK_ONLY: v = d.groupby("aclass")[f"{k}__{fcol}"].rank(pct=True) - 0.5
    return d["dir_sign"] * v
def add_composites(d, fcol):
    d = d.copy()
    pr = lambda k: d.groupby("aclass")[f"{k}__{fcol}"].rank(pct=True) - 0.5
    d[f"fac__{fcol}"] = (pr("mom121") + pr("lowvol")) / 2
    for k in [t for t in TOOLS if t not in RANK_ONLY | {"rw"}]:
        d[f"comb_{k}__{fcol}"] = (pr("mom121") + pr("lowvol") + pr(k)) / 3
    return d
def clus_boot(d, fn):
    dates = d["alert_date"].unique(); g = {k: v for k, v in d.groupby("alert_date")}; res = []
    for _ in range(NB):
        s = pd.concat([g[x] for x in rng.choice(dates, len(dates))]); res.append(fn(s))
    return np.nanpercentile(res, [2.5, 97.5])
def evaluate(d, k, fcol, rcol, boot=True):
    x = d[[rcol, "alert_date", "aclass"]].copy(); x["g"] = dir_score(k, fcol, d) if not (k.startswith("fac") or k.startswith("comb")) else d["dir_sign"] * d[f"{k}__{fcol}"]
    x = x.dropna(subset=["g", rcol])
    if len(x) < 8: return None
    rho, p = stats.spearmanr(x["g"], x[rcol]) if x["g"].nunique() > 1 else (np.nan, np.nan)
    keep = x["g"] > 0; kr, rr = x.loc[keep, rcol], x.loc[~keep, rcol]
    diff = kr.mean() - rr.mean() if len(kr) and len(rr) else np.nan
    pw = stats.ttest_ind(kr, rr, equal_var=False).pvalue if len(kr) > 1 and len(rr) > 1 else np.nan
    pdi = [r for _, gg in x.groupby(["alert_date", "aclass"]) if len(gg) >= 5 and gg["g"].nunique() > 1 for r in [stats.spearmanr(gg["g"], gg[rcol])[0]] if not np.isnan(r)]
    out = {"n": len(x), "spearman": rho, "p_spearman(iid)": p, "n_keep": int(keep.sum()), "mean_keep": kr.mean(), "n_reject": int((~keep).sum()),
           "mean_reject": rr.mean(), "keep_minus_reject": diff, "median_keep": kr.median(), "median_reject": rr.median(), "p_welch(iid)": pw,
           "perdate_RankIC": np.mean(pdi) if pdi else np.nan, "n_dates": len(pdi), "t_perdate": np.mean(pdi) / (np.std(pdi, ddof=1) / np.sqrt(len(pdi))) if len(pdi) > 2 else np.nan}
    if boot and x["g"].nunique() > 1:
        lo, hi = clus_boot(x, lambda s: stats.spearmanr(s["g"], s[rcol])[0]); out["spearman_CI95_clustered"] = f"[{lo:+.3f}, {hi:+.3f}]"
        lo, hi = clus_boot(x, lambda s: s.loc[s.g > 0, rcol].mean() - s.loc[s.g <= 0, rcol].mean()); out["diff_CI95_clustered"] = f"[{lo*100:+.2f}, {hi*100:+.2f}]pp"
    return out
def residual_ic(d, k, fcol, rcol):
    x = d.copy(); x["g"] = dir_score(k, fcol, d); x["m"] = dir_score("mom121", fcol, d); x["v"] = dir_score("lowvol", fcol, d)
    x = x.dropna(subset=["g", "m", "v", rcol]); res = []
    for _, gg in x.groupby("aclass"):
        X = np.column_stack([np.ones(len(gg)), gg["m"].rank(), gg["v"].rank()]); y = gg["g"].rank().values
        e = y - X @ np.linalg.lstsq(X, y, rcond=None)[0]; res.append(pd.DataFrame({"e": e, "r": gg[rcol].values, "alert_date": gg["alert_date"].values}))
    z = pd.concat(res); rho, p = stats.spearmanr(z["e"], z["r"])
    lo, hi = clus_boot(z.rename(columns={"e": "g"}), lambda s: stats.spearmanr(s["g"], s["r"])[0])
    return {"n": len(z), "resid_spearman": rho, "p(iid)": p, "CI95_clustered": f"[{lo:+.3f}, {hi:+.3f}]"}

fmtp = lambda v: "" if pd.isna(v) else f"{v*100:+.2f}%"
def table(rows, pctcols=("mean_keep", "mean_reject", "keep_minus_reject", "median_keep", "median_reject", "mean", "median")):
    t = pd.DataFrame(rows)
    for c in t.columns:
        if c in pctcols: t[c] = t[c].map(fmtp)
        elif t[c].dtype.kind == "f": t[c] = t[c].map(lambda v: "" if pd.isna(v) else f"{v:.3f}")
    return t.to_markdown(index=False)

L = ["# Scanner setups: do the time-series models filter them usefully?\n", """
**Method (point-in-time).** Input: `/workspace/tracker/setups-point-in-time-2026-10-08.csv` (canonical, read-only). The 846 main-sheet setups are primary and the 212 excluded (MCAP<$1.5B) are reported separately. `dup_not_counted` rows and rows with no alert date are skipped.
Cutoffs come from the file. US: history ends at the `cutoff_bar_date` close (the prior session for in-session, pre-market or date-only alerts; the 24.09 bot scan uses the given cutoff, though its data_asof_note says it used 22.09 closes). Crypto: 24h candles rebuilt from Yahoo hourly bars, ending at `cutoff_minute_utc` floored to the hour (date-only crypto = 00:00 UTC of the alert day). Perplexity task-list times (`ui_log`, 40 rows) are logged 5-70 min after the run, so the cutoff is capped at logged time minus 70 min. In practice this changed nothing: those stocks were in-session alerts that already used the prior close, and those crypto rows were already at 00:00 UTC.
Each tool forecasts a 20-bar path from up to 400 bars of history. Scores are direction-adjusted: SHORT flips the sign, so **keep = the tool agrees with the setup's direction**. For the rank-only factors, keep = the favourable half within the asset class.
Outcomes are direction-adjusted. Where present, the tracker's own day-5, day-20 and total columns are used (total = last available day ≤20; base = alert price). Rows without them, mainly the excluded set, are computed from prices after the cutoff (base = cutoff close). Excess returns subtract SPY (US) or BTC-USD (crypto) over the same window from the cutoff; there is also a total excess vs ETH for crypto. BTC setups have zero excess vs BTC by construction.
**Significance.** Setups on the same date share market moves, so iid p-values are optimistic. Read the date-clustered bootstrap CIs and the per-date RankIC t-stat (dates × asset class with ≥5 setups). Many tools × targets × subgroups are tested, so expect several nominal p<0.05 by chance.
"""]
main = df[df.in_main_sheet == True]; excl = df[df.in_main_sheet != True]
L.append(f"Setups scored: main sheet {len(main)} (after dropping dup_not_counted and rows with no cutoff/price), excluded MCAP<1.5B {len(excl)}. "
         f"Realized source (main): {main.realized_source.value_counts().to_dict()}; excluded: {excl.realized_source.value_counts().to_dict()}.\n")
order = [k for k in ["rw", "mom121", "lowvol", "chronos2", "timesfm", "kronos-mini", "kronos-small", "kronos-base"] if k in TOOLS]
for rcol, fcol, lab in TARGETS:
    d = add_composites(main, fcol)
    rows = []
    for k in order + ["fac"]:
        if k == "rw":   # baseline: keep everything
            x = d.dropna(subset=[rcol]); rows.append({"tool": "Keep all (random walk)", "n": len(x), "n_keep": len(x), "mean_keep": x[rcol].mean(), "median_keep": x[rcol].median()}); continue
        r = evaluate(d, k, fcol, rcol)
        if r: rows.append({"tool": TOOLS.get(k, "Factors: mom12-1 + low-vol"), **r})
    L.append(f"\n## Main sheet, target = {lab} (all asset classes; ranks within asset class for factors)\n\n" + table(rows) + "\n")
# breakdowns on day-5 and total
for rcol, fcol, lab in [("r5", "f5", "day-5"), ("rtot", "ftot", "total"), ("xtot", "ftot", "total EXCESS vs SPY/BTC")]:
    for by in ["aclass", "model", "time_source", "direction"]:
        rows = []
        for val, g in main.groupby(by):
            if g[rcol].notna().sum() < 15: continue
            gg = add_composites(g, fcol); base = {"group": f"{by}={val}", "n_all": int(g[rcol].notna().sum()), "mean_all": fmtp(g[rcol].mean()), "median_all": fmtp(g[rcol].median())}
            for k in [t for t in order if t != "rw"] + ["fac"]:
                r = evaluate(gg, k, fcol, rcol, boot=False)
                if r: rows.append({**base, "tool": TOOLS.get(k, "Factors"), "spearman": r["spearman"], "n_keep": r["n_keep"], "mean_keep": r["mean_keep"], "mean_reject": r["mean_reject"], "median_keep": r["median_keep"], "median_reject": r["median_reject"], "keep_minus_reject": r["keep_minus_reject"], "p_welch(iid)": r["p_welch(iid)"]})
        L.append(f"\n### Breakdown by {by}, target = {lab}\n\n" + table(rows) + "\n")
# Grok prebreakout focus
pb = main[main.automation == "prebreakout"]
L.append(f"\n## Grok 'before breakout' (prebreakout) setups: n={len(pb)} (directions {pb.direction.value_counts().to_dict()})\n")
for rcol, fcol, lab in TARGETS:
    g = add_composites(pb, fcol); x = g.dropna(subset=[rcol])
    if len(x) < 8: continue
    rows = [{"tool": "All setups (no filter)", "n_keep": len(x), "mean_keep": x[rcol].mean(), "median_keep": x[rcol].median()}]
    for k in [t for t in order if t != "rw"] + ["fac"]:
        r = evaluate(g, k, fcol, rcol, boot=False)
        if r: rows.append({"tool": TOOLS.get(k, "Factors"), "n_keep": r["n_keep"], "mean_keep": r["mean_keep"], "median_keep": r["median_keep"], "n_reject": r["n_reject"], "mean_reject": r["mean_reject"], "median_reject": r["median_reject"], "keep_minus_reject": r["keep_minus_reject"], "p_welch(iid)": r["p_welch(iid)"], "spearman": r["spearman"]})
    L.append(f"\n### prebreakout, target = {lab}\n\n" + table(rows) + "\n")
# incremental over factors
rows = []
for rcol, fcol, lab in TARGETS[:3]:
    d = add_composites(main, fcol)
    f = evaluate(d, "fac", fcol, rcol, boot=False)
    for k in [t for t in order if t not in RANK_ONLY | {"rw"}]:
        ri = residual_ic(d, k, fcol, rcol); c = evaluate(d, f"comb_{k}", fcol, rcol, boot=False)
        rows.append({"target": lab, "model": TOOLS[k], **ri, "factors_spearman": f["spearman"], "combined_spearman": c["spearman"],
                     "factors_keep_minus_reject": fmtp(f["keep_minus_reject"]), "combined_keep_minus_reject": fmtp(c["keep_minus_reject"])})
L.append("\n## Incremental value over momentum 12-1 + low-vol (main sheet)\nresidual = model rank regressed on the two factor ranks within asset class; combined = equal rank-average of mom12-1, low-vol, model.\n\n" + table(rows, ()) + "\n")
# robustness: leave-out named tickers and top-1/top-3 contributing tickers
SUBSETS = [("Main sheet", main, ["IOVA"]), ("Grok crypto", main[main.model == "GROK crypto"], ["NEAR-USD"]),
           ("Perplexity", main[main.platform.str.startswith("Perplexity")], ["XP"])]
rows = []
for rcol, fcol, lab in [("rtot", "ftot", "total"), ("xtot", "ftot", "total EXCESS")]:
    for sname, sub, named in SUBSETS:
        contrib = sub.groupby("ticker")[rcol].sum().sort_values(ascending=False)
        variants = [("all", []), ("without " + "+".join(named), named), (f"drop top-1 ({contrib.index[0]})", list(contrib.index[:1])),
                    (f"drop top-3 ({', '.join(contrib.index[:3])})", list(contrib.index[:3]))]
        for vname, drop in variants:
            v = sub[~sub.ticker.isin(drop)]; vv = add_composites(v, fcol); x = v[rcol].dropna()
            row = {"target": lab, "subset": sname, "variant": vname, "n": len(x), "mean": x.mean(), "median": x.median()}
            for k in [t for t in order if t not in {"rw"}] + ["fac"]:
                r = evaluate(vv, k, fcol, rcol, boot=False)
                row[f"{TOOLS.get(k, 'Factors')} keep-rej"] = fmtp(r["keep_minus_reject"]) if r else ""
            rows.append(row)
L.append("\n## Robustness: leave-out tickers (mean/median of all setups; keep-minus-reject spread per tool)\n\n" + table(rows) + "\n")
# excluded set
rows = []
for rcol, fcol, lab in TARGETS[:3]:
    d = add_composites(excl, fcol)
    for k in [t for t in order if t != "rw"] + ["fac"]:
        r = evaluate(d, k, fcol, rcol, boot=False)
        if r: rows.append({"target": lab, "tool": TOOLS.get(k, "Factors"), "n": r["n"], "spearman": r["spearman"], "mean_keep": r["mean_keep"], "mean_reject": r["mean_reject"], "keep_minus_reject": r["keep_minus_reject"], "p_welch(iid)": r["p_welch(iid)"]})
L.append(f"\n## Excluded setups (MCAP < $1.5B), realized computed from prices (n={len(excl)})\n\n" + table(rows) + "\n")
meta = {k: json.load(open(f"forecasts/{k}.meta.json")) for k in TOOLS}
L.append("\n## Tool runtime on this set\n\n" + pd.DataFrame(meta.values())[["tool", "n", "unique_series", "load_s", "total_s", "sec_per_series", "peak_rss_mb_process"]].to_markdown(index=False) + "\n")
open(OUT, "w").write("\n".join(L)); print("wrote", OUT)
