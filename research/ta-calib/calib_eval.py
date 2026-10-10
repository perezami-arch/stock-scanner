"""Box-side evaluation of the calibrated TradingAgents run (no LLM). Copy results_calib.jsonl from the laptop first.

  python calib_eval.py --results results_calib.jsonl            # status + calibration (theta per asset class)
  python calib_eval.py --results results_calib.jsonl --holdout  # ONE-TIME holdout evaluation with the frozen theta

Protocol (split.md): theta_asset = argmax over a 0.05 grid of avoided loss on the CALIBRATION half, where
avoided loss = sum(-ret20) over vetoed trades (veto <=> p_success < theta), requiring >= 10 vetoed and >= 20 kept;
if no theta has avoided loss > 0 -> theta = 0 (never veto). Calibration needs >= 90% of the half scored.
--holdout: needs >= 90% of the holdout scored; freezes theta into holdout_lock.json; refuses to run again
(--force-reeval exists but breaks the protocol and is recorded in the lock file).
Holdout tests (one BH family, q < 0.10): per asset class and pooled, mean ret20 and mean excess (x_mkt20) of KEPT
minus VETOED trades (filter test, N >= 20 per side) and avoided loss, p = max(ticker-, entry-date-, two-way-
clustered OLS p) as in geo_analyze.py. Robustness: median diff, drop top-1/top-3 tickers. Trades with complete20 =
False (data ended first) are included marked-to-market and also reported separately."""
import argparse, json, os, sys, datetime as dt, numpy as np, pandas as pd
import statsmodels.api as sm
HERE = os.path.dirname(os.path.abspath(__file__))
GRID = np.round(np.arange(0.05, 0.951, 0.05), 2)

def load(path):
    rows = []
    for l in open(path, encoding="utf-8"):
        try: rows.append(json.loads(l))
        except Exception: pass
    R = pd.DataFrame(rows)
    if len(R) == 0: return R
    R = R[R.ok == True].drop_duplicates("setup_id", keep="last")
    return R

def _fit(y, X, g):
    try:
        m = sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": g}, use_t=True); return float(m.params[-1]), float(m.pvalues[-1])
    except Exception: return np.nan, np.nan

def cl_diff(y, ind, tick, dates):
    y = np.asarray(y, float); X = sm.add_constant(np.asarray(ind, float), has_constant="add")
    gt = pd.factorize(tick)[0]; gd = pd.factorize(dates)[0]
    b, p = _fit(y, X, gt); p = max(p, _fit(y, X, gd)[1], _fit(y, X, np.column_stack([gt, gd]))[1])
    return b, p

def avoided(g, th): v = g[g.p_success < th]; return -v.ret20.sum(), len(v), len(g) - len(v)

def choose_theta(g):
    best = (0.0, 0.0)
    for th in GRID:
        a, nv, nk = avoided(g, th)
        if nv >= 10 and nk >= 20 and a > best[1] + 1e-12: best = (float(th), float(a))
    return best

def drop_top(g, ind, col):
    w, o = g[ind], g[~ind]; out = []
    c = (w.groupby("ticker")[col].sum() / max(len(w), 1)).sub(o.groupby("ticker")[col].sum() / max(len(o), 1), fill_value=0)
    sign = np.sign(w[col].mean() - o[col].mean()) or 1
    for k in (1, 3):
        top = list((c * sign).sort_values(ascending=False).index[:k]); h = g[~g.ticker.isin(top)]; hi = ind[~g.ticker.isin(top)]
        out.append(h[hi][col].mean() - h[~hi][col].mean() if hi.sum() and (~hi).sum() else np.nan)
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--results", default=os.path.join(HERE, "results_calib.jsonl"))
    ap.add_argument("--holdout", action="store_true"); ap.add_argument("--force-reeval", action="store_true")
    a = ap.parse_args()
    O = pd.read_csv(os.path.join(HERE, "outcomes_calib.csv")); S = pd.read_csv(os.path.join(HERE, "setups_calib.csv"))
    R = load(a.results)
    print(f"scored: {len(R)} of {len(S)}  ({R.half.value_counts().to_dict() if len(R) else {}})")
    if len(R) == 0: return
    X = R[["setup_id", "verdict", "p_success", "parse_ok", "decision"]].merge(O, on="setup_id", how="inner")
    X = X[X.p_success.notna()]
    print("parse_ok:", int(R.parse_ok.fillna(False).sum()), "verdicts:", R.verdict.value_counts(dropna=False).to_dict())
    lockf = os.path.join(HERE, "holdout_lock.json"); lock = json.load(open(lockf)) if os.path.exists(lockf) else None
    th = {}
    for asset in ("stock", "crypto"):
        g = X[(X.asset == asset) & (X.half == "calibration")]; n_half = int(((S.asset == asset) & (S.half == "calibration")).sum())
        cov = len(g) / max(n_half, 1)
        t, av = choose_theta(g) if len(g) else (0.0, 0.0)
        th[asset] = t
        print(f"[calibration] {asset}: scored {len(g)}/{n_half} ({cov:.0%}); theta={t} avoided={av*100:.1f} pct-pts summed"
              f"{'' if cov >= 0.9 else '  (PROVISIONAL: <90% scored)'}")
        if len(g):
            for v in ("approve", "neutral", "veto"):
                gv = g[g.verdict == v]
                if len(gv): print(f"     verdict={v:8s} N={len(gv):3d} mean ret20={gv.ret20.mean()*100:+.2f}% hit={(gv.ret20>0).mean()*100:.0f}% x_mkt={gv.x_mkt20.mean()*100:+.2f}%")
    if not a.holdout:
        if lock: print("holdout already evaluated:", lock.get("evaluated_at"), "theta", lock.get("theta"))
        return
    if lock and not a.force_reeval:
        print("REFUSED: holdout was already evaluated once at", lock["evaluated_at"], "with theta", lock["theta"]); return
    for asset in ("stock", "crypto"):
        n_c = int(((S.asset == asset) & (S.half == "calibration")).sum()); n_h = int(((S.asset == asset) & (S.half == "holdout")).sum())
        sc_c = int(((X.asset == asset) & (X.half == "calibration")).sum()); sc_h = int(((X.asset == asset) & (X.half == "holdout")).sum())
        if sc_c < 0.9 * n_c or sc_h < 0.9 * n_h:
            print(f"NOT YET: {asset} calibration {sc_c}/{n_c}, holdout {sc_h}/{n_h} scored (need 90% of each)"); return
    H = X[X.half == "holdout"].copy(); H["veto"] = H.apply(lambda r: r.p_success < th[r.asset], axis=1)
    rows = []
    for seg, g in (("stock", H[H.asset == "stock"]), ("crypto", H[H.asset == "crypto"]), ("pooled", H)):
        kept = ~g.veto
        for col in ("ret20", "x_mkt20"):
            d = dict(segment=seg, metric=col, theta=json.dumps(th) if seg == "pooled" else th[seg], N=len(g), N_veto=int(g.veto.sum()),
                     N_kept=int(kept.sum()), avoided_loss_pts=-g[g.veto].ret20.sum() * 100 if col == "ret20" else np.nan,
                     mean_kept=g[kept][col].mean() * 100, mean_veto=g[g.veto][col].mean() * 100, mean_all=g[col].mean() * 100,
                     med_diff=(g[kept][col].median() - g[g.veto][col].median()) * 100,
                     incomplete_share=(~g.complete20).mean())
            if kept.sum() >= 20 and g.veto.sum() >= 20:
                b, p = cl_diff(g[col].values, kept.values, g.ticker.values, g.entry_date.values)
                d.update(diff=b * 100, p=p); dr = drop_top(g, kept, col); d.update(drop1=dr[0] * 100, drop3=dr[1] * 100)
            else:
                d.update(diff=(d["mean_kept"] - d["mean_veto"]) if g.veto.sum() else np.nan, p=np.nan, note="N<20 on a side: no test")
            rows.append(d)
    T = pd.DataFrame(rows); m = T.p.notna(); M = int(m.sum())
    if M:
        pv = T.loc[m, "p"].values; o = np.argsort(pv); q = pv[o] * M / np.arange(1, M + 1); q = np.minimum.accumulate(q[::-1])[::-1]
        qq = np.empty(M); qq[o] = np.minimum(q, 1); T.loc[m, "q_BH"] = qq
    T["n_comparisons"] = M
    out = os.path.join(HERE, "holdout_eval.csv"); T.to_csv(out, index=False); print(T.round(3).to_string())
    json.dump(dict(evaluated_at=dt.datetime.now().isoformat(timespec="seconds"), theta=th, forced=bool(lock and a.force_reeval),
                   n_holdout=len(H), results_file=os.path.abspath(a.results)), open(lockf, "w"), indent=1)
    print("holdout evaluated and locked ->", lockf, out)

if __name__ == "__main__":
    main()
