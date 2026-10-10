import sys, numpy as np, pandas as pd
sys.path.insert(0, '/workspace/fib-spiral'); import common_bt as C
OUT = '/workspace/fib-spiral/out'
rows = []; desc = []
for ds in ('crypto_1h', 'stock_1d', 'crypto_1m'):
    E = pd.read_csv(f'{OUT}/events_{ds}.csv')
    for fans in ('F9', 'F5'):
        e = E[E.fans == fans]
        sym, date = e.symbol.values, e.entry_date.values
        # descriptives incl. baselines
        for key in ['t1_TR', 't1_NT', 't2_TR', 't2_NT', 't786_TR', 't786_NT', 'pol']:
            R = e[f'{key}_R'].values; net = e[f'{key}_net'].values; m = C.cmean(R, sym, date)
            kind = e[f'{key}_kind']
            desc.append(dict(dataset=ds, fans=fans, policy=key, N=len(e), n_sym=m.get('n_sym'), n_dates=m.get('n_dates'),
                             hit=float((net > 0).mean()), mean_R=m['mean'], med_R=m['median'], ci_lo=m['lo'], ci_hi=m['hi'], p=m['p'],
                             mean_net_pct=100 * np.nanmean(net), med_net_pct=100 * np.nanmedian(net),
                             stop_rate=float((kind == 'stop').mean()), trail_rate=float((kind == 'trail').mean()),
                             target_rate=float((kind == 'target').mean()), time_rate=float((kind == 'time').mean()),
                             avg_bars=float(e[f'{key}_bars'].mean()), mean_fund_pct=100 * float(e[f'{key}_fund'].mean()) if f'{key}_fund' in e else np.nan,
                             rand_R=float(e[f'{key}_rand_R'].mean()) if f'{key}_rand_R' in e else np.nan,
                             drop1=C.drop_top(R, sym, 1), drop3=C.drop_top(R, sym, 3)))
        for tg in ('t1', 't2'):
            for tr in ('TR', 'NT'):
                key = f'{tg}_{tr}'; R = e[f'{key}_R'].values
                tests = {'abs': R, 'vs_policy_a': R - e['pol_R'].values, 'vs_786_b': R - e[f't786_{tr}_R'].values, 'vs_random_c': R - e[f'{key}_rand_R'].values}
                for tn, y in tests.items():
                    m = C.cmean(y, sym, date); w1, w2, med = C.walk_forward(y, sym, date)
                    rows.append(dict(dataset=ds, fans=fans, target=tg.upper(), trail=tr, test=tn, primary=(ds != 'crypto_1m' and fans == 'F9' and tg == 't1' and tr == 'TR'),
                                     N=m['n'], n_sym=m.get('n_sym'), n_dates=m.get('n_dates'), mean_R=m['mean'], ci_lo=m['lo'], ci_hi=m['hi'], p=m['p'],
                                     drop1=C.drop_top(y, sym, 1), drop3=C.drop_top(y, sym, 3), wf_split=med, wf1_mean=w1['mean'], wf1_p=w1['p'],
                                     wf2_mean=w2['mean'], wf2_p=w2['p']))
T = pd.DataFrame(rows); T['q'] = C.bh(T.p.values)
T['survives'] = (T.q < 0.10)
D = pd.DataFrame(desc)
T.to_csv(f'{OUT}/fdr_tests.csv', index=False); D.to_csv(f'{OUT}/descriptives.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30); pd.set_option('display.max_rows', 200)
print(D.round(3).to_string())
print(T.round(4).to_string())
print('family size', len(T), 'survivors', int(T.survives.sum()))
