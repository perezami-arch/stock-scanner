import sys, numpy as np, pandas as pd
sys.path.insert(0, '/workspace/fib-spiral'); import common_bt as C
OUT = '/workspace/liq-sweep/out'; rows = []; desc = []
for ds in ('crypto_1m', 'crypto_15m', 'stock_1d'):
    E = pd.read_csv(f'{OUT}/events_{ds}.csv')
    for dr in ('SHORT', 'LONG'):
        for flt in ('ALL', 'VOLSPIKE'):
            e = E[(E.dir == dr) & ((E.vol_spike == True) if flt == 'VOLSPIKE' else True)]
            for ent in ('E1', 'E2'):
                x = e[e.E2_filled == True] if ent == 'E2' else e
                R = x[f'{ent}_R'].values; net = x[f'{ent}_net'].values; sym, date = x.symbol.values, x.entry_date.values; k = x[f'{ent}_kind']
                m = C.cmean(R, sym, date); w1, w2, med = C.walk_forward(R, sym, date)
                rnd = R - x[f'{ent}_rand_R'].values; mr = C.cmean(rnd, sym, date); v1, v2, _ = C.walk_forward(rnd, sym, date)
                gross = net + x.apply(lambda z: 0, axis=1).values if False else None
                common = dict(dataset=ds, dir=dr, filter=flt, entry=ent, N=m['n'], n_sym=m.get('n_sym'), n_dates=m.get('n_dates'))
                desc.append(dict(**common, fill_rate=float(len(x) / len(e)) if len(e) else np.nan, hit=float((net > 0).mean()), mean_R=m['mean'], med_R=m.get('median'),
                                 mean_net_pct=100 * np.nanmean(net), med_net_pct=100 * np.nanmedian(net), stop_rate=float((k == 'stop').mean()),
                                 target_rate=float((k == 'target').mean()), time_rate=float((k == 'time').mean()), avg_bars=float(x[f'{ent}_bars'].mean()),
                                 med_rr=float(x.rr1.median()), med_risk_pct=100 * float(x.risk1_pct.median()), rand_R=float(np.nanmean(x[f'{ent}_rand_R']))))
                rows.append(dict(**common, test='abs', mean_R=m['mean'], ci_lo=m['lo'], ci_hi=m['hi'], p=m['p'], drop1=C.drop_top(R, sym, 1), drop3=C.drop_top(R, sym, 3),
                                 wf_split=med, wf1_mean=w1['mean'], wf1_p=w1['p'], wf2_mean=w2['mean'], wf2_p=w2['p']))
                rows.append(dict(**common, test='vs_random', mean_R=mr['mean'], ci_lo=mr['lo'], ci_hi=mr['hi'], p=mr['p'], drop1=C.drop_top(rnd, sym, 1), drop3=C.drop_top(rnd, sym, 3),
                                 wf_split=med, wf1_mean=v1['mean'], wf1_p=v1['p'], wf2_mean=v2['mean'], wf2_p=v2['p']))
T = pd.DataFrame(rows); T['q'] = C.bh(T.p.values); T['survives'] = T.q < 0.10
D = pd.DataFrame(desc)
# verdict per variant (RULE §7)
V = []
for key, g in T.groupby(['dataset', 'dir', 'filter', 'entry']):
    a = g[g.test == 'abs'].iloc[0]; b = g[g.test == 'vs_random'].iloc[0]
    ok = (a.N >= 30) and (a.n_dates >= 10) and a.mean_R > 0 and a.q < 0.10 and b.mean_R > 0 and b.q < 0.10 and a.wf1_mean > 0 and a.wf2_mean > 0 and a.drop3 > 0
    V.append(dict(zip(['dataset', 'dir', 'filter', 'entry'], key), passes=bool(ok)))
V = pd.DataFrame(V)
T.to_csv(f'{OUT}/fdr_tests.csv', index=False); D.to_csv(f'{OUT}/descriptives.csv', index=False); V.to_csv(f'{OUT}/verdicts.csv', index=False)
pd.set_option('display.width', 260); pd.set_option('display.max_columns', 40); pd.set_option('display.max_rows', 200)
print(D.round(3).to_string()); print(T.round(4).to_string()); print(V.to_string()); print('family', len(T), 'survivors', int(T.survives.sum()))
