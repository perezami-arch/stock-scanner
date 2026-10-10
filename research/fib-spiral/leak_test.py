"""RULE §12 leak/repaint test."""
import sys, numpy as np, pandas as pd, math
sys.path.insert(0, '/workspace/fib-spiral'); import fib_spiral as FS, common_bt as C
from backtest_fib import datasets
rng = np.random.default_rng(7); ds = datasets(); res = []
def norm(dct):
    return {k: (round(float(v), 9) if isinstance(v, (float, np.floating)) else (str(v) if not isinstance(v, (dict, bool, int, str)) else v)) for k, v in dct.items()}
for name in ('crypto_1h', 'stock_1d', 'crypto_1m'):
    items = ds[name]; ev = pd.read_csv(f'/workspace/fib-spiral/out/events_{name}.csv')
    for it in [items[k] for k in rng.choice(len(items), min(12, len(items)), replace=False)]:
        sym, path, asset, bar_ms, W = it; d = C.load_ohlcv(path).drop(columns=['ts'])
        evs, _ = FS.find_events(d, asset, 'F9')
        cut_ev = [e['fs_bar'] for e in evs]; cut_ev = list(rng.choice(cut_ev, min(15, len(cut_ev)), replace=False)) if cut_ev else []
        cut_rand = list(rng.integers(100, len(d) - 60, 15))
        for kind, cuts in (('event', cut_ev), ('random', cut_rand)):
            for b in cuts:
                b = int(b); t = d.index[b]
                a1 = FS.fib_spiral_columns(d.iloc[:b + 1], None, asset)
                a2 = FS.fib_spiral_columns(d, t, asset)
                junk = d.iloc[b + 1:b + 51].copy()
                if len(junk) == 0: continue
                junk[['open', 'high', 'low', 'close']] = d.close.iloc[b] * rng.uniform(0.2, 5, (len(junk), 4))
                a3 = FS.fib_spiral_columns(pd.concat([d.iloc[:b + 1], junk]), t, asset)
                same = norm(a1) == norm(a2) == norm(a3)
                ok_ev = True
                if kind == 'event':
                    e = [x for x in evs if x['fs_bar'] == b][0]
                    ok_ev = bool(a1['fs_trigger']) and abs(a1['fs_entry'] - e['fs_entry']) < 1e-12 and abs(a1['fs_stop'] - e['fs_stop']) < 1e-12 \
                        and (a1['fs_target_t1'] == e['fs_target_t1'] or (a1['fs_target_t1'] != a1['fs_target_t1'] and e['fs_target_t1'] != e['fs_target_t1'])) \
                        and a1['fs_target_t2'] == e['fs_target_t2'] or (a1['fs_target_t2'] != a1['fs_target_t2'])
                res.append(dict(dataset=name, symbol=sym, kind=kind, bar=b, identical=same, event_reproduced=ok_ev, state=a1['fs_state']))
r = pd.DataFrame(res); r.to_csv('/workspace/fib-spiral/out/leak_test.csv', index=False)
print(r.groupby(['dataset', 'kind'])[['identical', 'event_reproduced']].agg(['sum', 'count']))
print(r.state.value_counts())
