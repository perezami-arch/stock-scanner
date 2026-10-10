"""RULE §8: PIT columns (truncated / full+cutoff / truncated+junk) identical, and identical to full-history detection."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/workspace/fib-spiral'); sys.path.insert(0, '/workspace/liq-sweep')
import common_bt as C, liq_sweep as LS
from backtest_liq import datasets
rng = np.random.default_rng(11); res = []
def nm(dct): return {k: (round(float(v), 9) if isinstance(v, (float, np.floating)) else str(v)) for k, v in dct.items()}
for name, nsym, ncut in (('crypto_1m', 3, 8), ('crypto_15m', 8, 12), ('stock_1d', 12, 12)):
    items = datasets()[name]
    for it in [items[k] for k in rng.choice(len(items), nsym, replace=False)]:
        sym, path, asset, intra = it[0], it[1], it[2], it[3]
        d = C.load_ohlcv(path).drop(columns=['ts']); full = LS.detect(d, asset, intra); byr = {}
        for e in full: byr.setdefault(e['r'], []).append(e)
        cuts = [('event', int(b)) for b in rng.choice(list(byr), ncut, replace=False)] + [('random', int(b)) for b in rng.integers(200, len(d) - 60, ncut)]
        for kind, b in cuts:
            t = d.index[b]
            a1 = LS.liq_sweep_columns(d.iloc[:b + 1], None, asset, intra); a2 = LS.liq_sweep_columns(d, t, asset, intra)
            junk = d.iloc[b + 1:b + 51].copy(); junk[['open', 'high', 'low', 'close']] = d.close.iloc[b] * rng.uniform(0.2, 5, (len(junk), 4))
            a3 = LS.liq_sweep_columns(pd.concat([d.iloc[:b + 1], junk]), t, asset, intra)
            same = nm(a1) == nm(a2) == nm(a3)
            fe = byr.get(b, [])
            match = (a1['ls_sweep'] == bool(fe)) and (a1['ls_short_sweep'] == any(e['dir'] == 'SHORT' for e in fe)) and (a1['ls_long_sweep'] == any(e['dir'] == 'LONG' for e in fe))
            if fe and a1['ls_sweep']:
                e = [x for x in fe if x['dir'] == a1['ls_dir']][0]
                match = match and abs(e['stop'] - a1['ls_stop']) < 1e-12 and abs(e['target'] - a1['ls_target']) < 1e-12 and e['level'] == a1['ls_level']
            res.append(dict(dataset=name, symbol=sym, kind=kind, bar=b, identical=same, matches_full_history=match))
r = pd.DataFrame(res); r.to_csv('/workspace/liq-sweep/out/leak_test.csv', index=False)
print(r.groupby(['dataset', 'kind'])[['identical', 'matches_full_history']].agg(['sum', 'count']))
