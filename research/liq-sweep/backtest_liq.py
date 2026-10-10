"""Backtest of the frozen liquidity-sweep rule (RULE.frozen.md)."""
import os, sys, glob, math, json, numpy as np, pandas as pd
from multiprocessing import Pool
sys.path.insert(0, '/workspace/fib-spiral'); sys.path.insert(0, '/workspace/liq-sweep')
import common_bt as C, liq_sweep as LS
OUT = '/workspace/liq-sweep/out'; SEED = 20261010; MH = LS.P['maxhold']
def datasets():
    return {'crypto_1m': [(s, f'/workspace/liq-sweep/data/crypto_1m/{s}.parquet', 'crypto', True, 60000, 1440) for s in C.CRYPTO if os.path.exists(f'/workspace/liq-sweep/data/crypto_1m/{s}.parquet')],
            'crypto_15m': [(s, f'/workspace/liq-sweep/data/crypto_15m/{s}.parquet', 'crypto', True, 900000, 960) for s in C.CRYPTO if os.path.exists(f'/workspace/liq-sweep/data/crypto_15m/{s}.parquet')],
            'stock_1d': [(os.path.basename(p)[:-8], p, 'stock', False, 86400000, 120) for p in sorted(glob.glob('/workspace/fib-spiral/data/stocks/*.parquet')) if not p.endswith('/SPY.parquet')]}

def fees(asset, sym, maker_in, exit_kind):
    if asset == 'crypto':
        sl = C.slip_crypto(sym); fin = 0.0002 if maker_in else 0.0005 + sl
        fout = 0.0002 if exit_kind == 'target' else 0.0005 + sl
    else:
        fin = 0.0002 if maker_in else 0.0005; fout = 0.0002 if exit_kind == 'target' else 0.0005
    return fin + fout

def carry(asset, sym, side, t0, t1):
    if asset == 'crypto':
        fs = C.funding_sum(sym, t0, t1); return (-fs if side == 'SHORT' else fs)
    return (0.01 * max(0, t1 - t0) / 86400000 / 365) if side == 'SHORT' else 0.0

def sim_fixed(o, h, l, c, ts, bar_ms, i, entry, stop, target):
    """short frame, fixed stop/target, stop first, time exit at i+MH."""
    n = len(c); end = min(i + MH, n - 1)
    for j in range(i + 1, end + 1):
        if h[j] >= stop:
            g = o[j] >= stop; return j, (o[j] if g else stop), 'stop', ts[j] + (0 if g else bar_ms // 2)
        if l[j] <= target:
            g = o[j] <= target; return j, (o[j] if g else target), 'target', ts[j] + (0 if g else bar_ms // 2)
        if j == i + MH: return j, c[j], 'time', ts[j] + bar_ms
    return end, c[end], 'censored', ts[end] + bar_ms

def sim_e2(o, h, l, c, ts, bar_ms, r, level, stop, target):
    n = len(c)
    for j in range(r + 1, min(r + LS.P['e2_bars'], n - 1) + 1):
        if h[j] >= level:
            px = max(level, o[j])
            if h[j] >= stop:
                g = o[j] >= stop; return j, px, j, (o[j] if g else stop), 'stop', ts[j] + bar_ms // 2
            jj, xp, kind, te = sim_fixed(o, h, l, c, ts, bar_ms, j, px, stop, target)
            return j, px, jj, xp, kind, te
        if l[j] <= target: return None
    return None

def run_symbol(args):
    ds, sym, path, asset, intraday, bar_ms, W = args
    d = C.load_ohlcv(path)
    if len(d) < 300: return []
    ev = LS.detect(d.drop(columns=['ts']), asset, intraday)
    O, H, Lo, Cl = (d[k].to_numpy(float) for k in ('open', 'high', 'low', 'close')); ts = d.ts.to_numpy('int64')
    fr = {'SHORT': (O, H, Lo, Cl), 'LONG': (-O, -Lo, -H, -Cl)}
    rng = np.random.default_rng(SEED + sum(map(ord, sym)) + len(ds)); rows = []
    for e in ev:
        sg = 1 if e['dir'] == 'SHORT' else -1; o, h, l, c = fr[e['dir']]
        r = e['r']; en, st, tg, lv = sg * e['entry'], sg * e['stop'], sg * e['target'], sg * e['level']
        risk1 = (st - en) / abs(en); tgp = (en - tg) / abs(en)
        base = dict(dataset=ds, symbol=sym, dir=e['dir'], time=e['time'], entry_date=str(pd.Timestamp(ts[r] if asset == 'stock' else ts[r] + bar_ms, unit='ms', tz='UTC').date()),
                    level=e['level'], level_kind=e['level_kind'], entry=e['entry'], stop=e['stop'], target=e['target'], target_kind=e['target_kind'],
                    vol_ratio=e['vol_ratio'], vol_spike=e['vol_spike'], reclaim_bars=e['reclaim_bars'], risk1_pct=risk1, rr1=tgp / risk1 if risk1 > 0 else np.nan)
        # E1
        j, xp, kind, te = sim_fixed(o, h, l, c, ts, bar_ms, r, en, st, tg)
        t0 = ts[r] + bar_ms; net = (en - xp) / abs(en) - fees(asset, sym, False, kind) + carry(asset, sym, e['dir'], t0, te)
        base.update(E1_net=net, E1_R=net / risk1, E1_kind=kind, E1_bars=j - r)
        # E2
        x = sim_e2(o, h, l, c, ts, bar_ms, r, lv, st, tg)
        if x is None: base.update(E2_filled=False, E2_net=np.nan, E2_R=np.nan, E2_kind='nofill', E2_bars=np.nan, risk2_pct=np.nan)
        else:
            jf, px, jj, xp2, k2, te2 = x; risk2 = (st - lv) / abs(lv)   # planned risk at order placement (limit -> stop)
            net2 = (px - xp2) / abs(px) - fees(asset, sym, True, k2) + carry(asset, sym, e['dir'], ts[jf] + bar_ms // 2, te2)
            base.update(E2_filled=True, E2_net=net2, E2_R=net2 / risk2 if risk2 > 0 else np.nan, E2_kind=k2, E2_bars=jj - jf, risk2_pct=risk2)
        # random baseline (same % stop / target distances, entry at close)
        lo_r = max(60, r - W); hi_r = min(len(Cl) - 2 - MH, r + W)
        draws = rng.integers(lo_r, hi_r + 1, 10) if hi_r > lo_r else []
        for E, rk, mk in (('E1', risk1, False), ('E2', base.get('risk2_pct', np.nan), True)):
            if not (rk == rk) or rk <= 0: base[f'{E}_rand_R'] = np.nan; continue
            tp = tgp if E == 'E1' else (abs(lv) - abs(tg)) / abs(lv) * (1 if e['dir'] == 'SHORT' else 1)
            if E == 'E2': tp = (base['risk2_pct'] and ((sg * e['level']) - tg) / abs(sg * e['level']))
            rr = []
            for q in draws:
                q = int(q); e0 = c[q]; s0 = e0 + rk * abs(e0); t_ = e0 - tp * abs(e0)
                jj, xp3, k3, te3 = sim_fixed(o, h, l, c, ts, bar_ms, q, e0, s0, t_)
                n3 = (e0 - xp3) / abs(e0) - fees(asset, sym, mk, k3) + carry(asset, sym, e['dir'], ts[q] + bar_ms, te3); rr.append(n3 / rk)
            base[f'{E}_rand_R'] = float(np.mean(rr)) if rr else np.nan
        rows.append(base)
    return rows

if __name__ == '__main__':
    for name, items in datasets().items():
        with Pool(7) as p: res = p.map(run_symbol, [(name, *it) for it in items], chunksize=1)
        df = pd.DataFrame([r for rr in res for r in rr]); df.to_csv(f'{OUT}/events_{name}.csv', index=False)
        print(name, len(items), 'symbols', len(df), 'events', flush=True)
