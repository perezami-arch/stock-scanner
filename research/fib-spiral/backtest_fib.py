"""Backtest of the frozen Fib-spiral SHORT rule (RULE.frozen.md). Writes out/events_*.csv, out/results.csv, out/summary.md"""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, sys, json, glob, math, numpy as np, pandas as pd
from multiprocessing import Pool
sys.path.insert(0, (_SCANNER_ROOT + '/fib-spiral'))
import fib_spiral as FS, common_bt as C
OUT = (_SCANNER_ROOT + '/fib-spiral/out'); FD = C.FD
SEED = 20261008
def datasets():
    ds = {'crypto_1h': [(s, f'{FD}/crypto_1h/{s}.parquet', 'crypto', 3600000, 720) for s in C.CRYPTO if os.path.exists(f'{FD}/crypto_1h/{s}.parquet')],
          'stock_1d': [(os.path.basename(p)[:-8], p, 'stock', 86400000, 120) for p in sorted(glob.glob(f'{FD}/stocks/*.parquet')) if not p.endswith('/SPY.parquet')]}
    one = ['PROMUSDT', 'USELESSUSDT'] + [s for s in C.CRYPTO if s not in ('PROMUSDT', 'USELESSUSDT')][:8]
    ds['crypto_1m'] = [(s, f'{_SCANNER_ROOT}/liq-sweep/data/crypto_1m/{s}.parquet', 'crypto', 60000, 43200) for s in one
                       if os.path.exists(f'{_SCANNER_ROOT}/liq-sweep/data/crypto_1m/{s}.parquet')]
    return ds

def run_symbol(args):
    ds, sym, path, asset, bar_ms, W = args
    d = C.load_ohlcv(path)
    if len(d) < 200: return []
    o, h, l, c = (d[k].to_numpy(float) for k in ('open', 'high', 'low', 'close')); ts = d.ts.to_numpy('int64')
    atr = FS.atr14(h, l, c); frac = C.fractal_highs(h); rng = np.random.default_rng(SEED + sum(map(ord, sym)) + len(ds))
    rows = []
    for fans in ('F9', 'F5'):
        ev, _ = FS.find_events(d, asset, fans)
        for e in ev:
            i = e['fs_bar']; entry = e['fs_entry']; stop0 = e['fs_stop']; T = e['fs_T_bars']; mh = math.ceil(FS.P['horizon'] * T)
            risk = (stop0 - entry) / entry; t_in = ts[i] + bar_ms
            base = dict(dataset=ds, symbol=sym, asset=asset, fans=fans, entry_time=pd.Timestamp(t_in, unit='ms', tz='UTC'),
                        entry_date=str(pd.Timestamp(ts[i] if asset == 'stock' else t_in, unit='ms', tz='UTC').date()), A=e['fs_A'], B=e['fs_B'], C=e['fs_C'], D=e['fs_D'],
                        D_time=e['fs_D_time'], T=T, entry=entry, stop=stop0, risk_pct=risk, t1=e['fs_target_t1'], t1_src=e['fs_t1_src'],
                        t1_fallback=e['fs_t1_fallback'], t2=e['fs_target_t2'], t2_src=e['fs_t2_src'], t2_score=e['fs_t2_score'],
                        t2_fallback=e['fs_t2_fallback'], t786=e['fs_target_786'], lines=e['fs_lines'], maxhold=mh)
            # policy (a)
            j, px, kind, te, cen = C.sim_policy_short(o, h, l, c, atr, ts, bar_ms, i, entry, mh, asset)
            cst, fund = C.costs(asset, sym, 'SHORT', t_in, te); net = (entry - px) / entry - cst
            base.update(pol_cost=cst, pol_net=net, pol_R=net / risk, pol_kind=kind, pol_bars=j - i)
            # random draws: valid range
            lo_r = max(60, i - W); hi_r = min(len(c) - 2 - mh, i + W)
            draws = rng.integers(lo_r, hi_r + 1, 10) if hi_r > lo_r else np.array([], int)
            for tg in ('t1', 't2', 't786'):
                tgt = e['fs_target_' + ('786' if tg == 't786' else tg)]
                for tr in (True, False):
                    j, px, kind, te, cen = C.sim_short(o, h, l, c, atr, ts, bar_ms, i, entry, stop0, tgt, mh, tr, frac)
                    cst, fund = C.costs(asset, sym, 'SHORT', t_in, te); net = (entry - px) / entry - cst
                    key = f"{tg}_{'TR' if tr else 'NT'}"
                    base.update({f'{key}_net': net, f'{key}_R': net / risk, f'{key}_kind': kind, f'{key}_bars': j - i, f'{key}_fund': fund, f'{key}_cost': cst,
                                 f'{key}_cens': cen})
                    if tg == 't786': continue
                    tp = (entry - tgt) / entry if tgt == tgt else np.nan; rr = []
                    for r in draws:
                        en = c[r]; st = en * (1 + risk); tt = en * (1 - tp) if tp == tp else None
                        jj, pp, kk, tee, cc = C.sim_short(o, h, l, c, atr, ts, bar_ms, r, en, st, tt, mh, tr, frac)
                        cs2, _ = C.costs(asset, sym, 'SHORT', ts[r] + bar_ms, tee); rr.append(((en - pp) / en - cs2) / risk)
                    base[f'{key}_rand_R'] = float(np.mean(rr)) if rr else np.nan
            rows.append(dict(base))
    return rows

if __name__ == '__main__':
    ds = datasets(); allrows = []
    for name, items in ds.items():
        with Pool(7) as p:
            res = p.map(run_symbol, [(name, *it) for it in items], chunksize=1)
        rows = [r for rr in res for r in rr]; df = pd.DataFrame(rows)
        df.to_csv(f'{OUT}/events_{name}.csv', index=False); print(name, len(items), 'symbols', len(df), 'events', flush=True)
