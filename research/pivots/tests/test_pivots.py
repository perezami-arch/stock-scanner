import os, sys
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(H, '..', '..', '..', 'modules'), os.path.join(H, '..', '..', '..', 'scanner')]
import numpy as np, pandas as pd
import scanner_pivots as PV, scanner_volphase as VP

def synth(n=1500, seed=1):
    rng = np.random.default_rng(seed); idx = pd.bdate_range('2020-01-01', periods=n)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.015, n)) + 0.3 * np.sin(np.arange(n) / 120))
    o = np.r_[c[0], c[:-1]]; h = np.maximum(o, c) * (1 + rng.uniform(0, .01, n)); l = np.minimum(o, c) * (1 - rng.uniform(0, .01, n))
    return pd.DataFrame(dict(Open=o, High=h, Low=l, Close=c, Volume=rng.uniform(1e6, 3e6, n)), index=idx)

def test_no_repaint_point_in_time():
    x = synth(); a = x.iloc[:1200]; P1, _ = PV.pivots(a); P2, _ = PV.pivots(x.iloc[:1300])
    k = lambda p: (p['degree'], p['date'], p['kind'], round(p['price'], 6))
    s1 = {k(p) for p in P1 if p['degree'] != 'minor'}; s2 = {k(p) for p in P2 if p['degree'] != 'minor'}
    assert all(p['conf_date'] <= a.index[-1] for p in P1)
    assert s1 <= s2 or len(s1 - s2) <= 1     # weekly pivots confirmed earlier never change (6y window start may drop 1)

def test_future_bars_do_not_change_columns():
    x = synth(); cut = x.index[1000] + pd.Timedelta(hours=21)
    r1 = PV.pivot_columns(x.iloc[:1001], None, 'stock', 'LONG')
    r2 = PV.pivot_columns(x, pd.Timestamp(cut).tz_localize('UTC'), 'stock', 'LONG')
    assert r1 == r2 or all((a == b) or (a != a and b != b) for a, b in zip(r1.values(), r2.values()))

def test_degrees_and_zones():
    x = synth(); r = PV.pivot_columns(x, None, 'stock', 'SHORT')
    assert r['n_major'] <= r['n_intermediate'] and r['n_minor'] > 0
    Z = PV.confluence(x, 'LONG')
    if Z['up']: assert Z['up']['lo'] > Z['px'] and Z['up']['strength'] >= PV.PARAMS['min_strength']
    if Z['dn']: assert Z['dn']['hi'] < Z['px']
    assert all(z['hi'] - z['lo'] <= PV.PARAMS['max_zone_width_atr'] * Z['A'] + 1e-9 for z in Z['zones'])

def test_weekly_drops_unfinished_week():
    x = synth(); x = x[x.index.weekday != 4]                 # last bar is never a Friday
    w = PV.weekly_bars(x.iloc[:-1]); assert w.index[-1] < x.index[-2] or x.index[-2].weekday() == 3

def test_volphase_states():
    idx = pd.bdate_range('2024-01-01', periods=30)
    c = np.r_[np.full(21, 100.), 101, 100]; v = np.r_[np.full(21, 1e6), 2e6, 5e5]
    x = pd.DataFrame(dict(Open=c, High=c + 1, Low=c - 1, Close=c, Volume=v), index=idx[:23])
    st, rv, up = VP.states(x); assert st.iloc[-2] == 'BR' and st.iloc[-1] == 'SF'
    assert VP.aligned('SF', 'LONG') == 1 and VP.aligned('SR', 'LONG') == -1 and VP.aligned('BF', 'SHORT') == 1

def test_research_columns_registered():
    import research_columns as RC
    assert 'piv' in RC.REGISTRY and 'vph' in RC.REGISTRY
    out = RC.compute_all(synth(), None, 'stock', 'LONG', tools=['piv', 'vph'])
    assert out['exp_piv_status'] == 'ok' and out['exp_vph_status'] == 'ok', (out['exp_piv_status'], out['exp_vph_status'])

if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'): f(); print('PASS', k)
