"""Test research_columns on the trial-run tickers (runtime, status/NaN counts) + leak test.
Leak test: for each tool, values at cutoff C computed on (F) the full frame (bars after C present) with cutoff=C,
(T) the frame physically truncated at the last visible bar, (J) every bar after C replaced by random junk + 30 junk bars.
Any F!=T or J!=T is a leak / repaint."""
import sys, time, json, numpy as np, pandas as pd
sys.path.insert(0, '/workspace'); sys.path.insert(0, '/workspace/research_nightly')
import rc_test_util as U, research_columns as RC, scanner_geometry as GEO
OUT = '/workspace/research-models/tests'; import os; os.makedirs(OUT, exist_ok=True)
asof, D = U.trial_asof()
TK = [t for t in D.t if not t.startswith('^')]
mode = sys.argv[1] if len(sys.argv) > 1 else 'all'
workers = int(os.environ.get('W', '2'))
if mode in ('all', 'run'):
    frames = {t: U.bars(t, asof) for t in TK}
    items = []
    for _, r in D[~D.t.str.startswith('^')].iterrows():
        items.append((r.t, frames[r.t], asof, 'stock', 'LONG'))
    for _, r in D[D.short_rule_pass.fillna(False).astype(bool) & ~D.t.str.startswith('^')].iterrows():
        items.append((r.t + '|SHORT', frames[r.t], asof, 'stock', 'SHORT', r.t))
    RC.reset_budget(600); t0 = time.time()
    rows = RC.compute_many(items, workers=workers); tot = time.time() - t0
    X = pd.DataFrame(rows); X.to_csv(f'{OUT}/trial_research_columns.csv', index=False)
    summ = RC.status_summary(rows)
    nan = {t: round(float(X[[c for c in RC.tool_columns(t) if c in X and not c.endswith('_status')]].isna().mean().mean()), 3) for t in RC.REGISTRY}
    res = dict(n_items=len(items), n_tickers=len(TK), workers=workers, total_s=round(tot, 1), per_tool=summ, nan_share=nan)
    json.dump(res, open(f'{OUT}/trial_summary.json', 'w'), indent=1, default=str); print(json.dumps(res, indent=1, default=str), flush=True)
if mode in ('all', 'leak'):
    rng = np.random.default_rng(7)
    def junk(df, c):
        g = df.astype(float).copy(); post = GEO.bar_end_utc(g.index, 'stock') > c; n = int(post.sum())
        base = float(g.Close[~post].iloc[-1]); cc = base * np.exp(np.cumsum(rng.normal(0, 0.2, n)))
        g.loc[post, 'Close'] = cc; g.loc[post, 'Open'] = cc * rng.uniform(.5, 1.5, n); g.loc[post, 'High'] = np.maximum(cc, g.loc[post, 'Open']) * rng.uniform(1, 3, n)
        g.loc[post, 'Low'] = np.minimum(cc, g.loc[post, 'Open']) * rng.uniform(.2, 1, n); g.loc[post, 'Volume'] = rng.uniform(0, 1e10, n)
        idx = pd.bdate_range(g.index[-1] + pd.Timedelta(days=1), periods=30)
        e = pd.DataFrame({'Open': base * 3, 'High': base * 10, 'Low': base * .01, 'Close': base * .05, 'Volume': 1e12}, index=idx)
        return pd.concat([g, e])
    CUTS = [pd.Timestamp('2026-09-15 14:00', tz='UTC'),   # intra-session -> previous close (09-14)
            pd.Timestamp('2026-09-29 21:30', tz='UTC')]   # after the close -> alert-day candle (09-29) allowed
    LT = list(rng.choice(TK, 16, replace=False))
    tools = [t for t in RC.REGISTRY if t not in ('qlib', 'finrl')]
    rows = []; RC.reset_budget(3600)
    for t in LT:
        full = U.bars(t, asof)
        for c in CUTS:
            for dr in ('LONG', 'SHORT'):
                cut = GEO.pit_cut(full, c, 'stock')
                F = RC.compute_all(full, c, 'stock', dr, tools=tools, symbol=t)
                T = RC.compute_all(cut, None, 'stock', dr, tools=tools, symbol=t)
                J = RC.compute_all(junk(full, c), c, 'stock', dr, tools=tools, symbol=t)
                for k in T:
                    if k.endswith('_status') or k.startswith('exp_rc_'): continue
                    tool = k.split('_')[1]
                    same = lambda a, b: (a == b) or (isinstance(a, float) and isinstance(b, float) and ((np.isnan(a) and np.isnan(b)) or abs(a - b) <= 1e-7 * max(1, abs(a))))
                    rows.append(dict(ticker=t, cutoff=str(c), direction=dr, tool=tool, col=k, last_bar=T['exp_rc_last_bar'],
                                     T_status=T.get(f'exp_{tool}_status'), F_diff=not same(F.get(k), T.get(k)), J_diff=not same(J.get(k), T.get(k))))
    L = pd.DataFrame(rows); L.to_csv(f'{OUT}/leak_test.csv', index=False)
    s = L.groupby('tool').agg(values=('col', 'size'), ok_status=('T_status', lambda s: int((s == 'ok').sum())), F_leaks=('F_diff', 'sum'), J_leaks=('J_diff', 'sum'))
    print(s.to_string()); print('cols with diffs:', L[L.F_diff | L.J_diff].col.value_counts().head(20).to_dict())
    print('last bars by cutoff:', L.groupby('cutoff').last_bar.unique().to_dict())
    s.to_csv(f'{OUT}/leak_test_summary.csv')
