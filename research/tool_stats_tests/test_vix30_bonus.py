import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scanner'))
import pandas as pd, vix_regime as V
corr = pd.Series({'XLK': -0.7, 'SMH': -0.75, 'XLY': -0.6, 'XLU': -0.1, 'XLP': -0.15, 'XLV': -0.2, 'GLD': 0.1, 'BTC-USD': -0.4})
def fake(hist): return lambda cut: (hist[-1], corr, {}, hist)
L = lambda sec, d='LONG', a='stock': {'sector_etf': sec, 'direction': d, 'asset': a}
def test_no_episode():
    assert V.vix30_bonus(L('XLK'), None, fake([16.5] * 40))['vix30_bonus'] == 0
def test_cross_day_and_window():
    h = [20] * 20 + [31]; assert V.vix30_episode(h) == (True, 0)
    assert V.vix30_bonus(L('XLK'), None, fake(h))['vix30_bonus'] == 5
    h2 = h + [25] * 19; assert V.vix30_episode(h2) == (True, 19)          # persists 20 sessions even if VIX falls back
    h3 = h + [25] * 20; assert V.vix30_episode(h3) == (False, 20)
def test_no_rearm_inside_window():
    h = [20] * 5 + [31, 29, 32] + [25] * 18; assert V.vix30_episode(h) == (False, 20)   # 2nd cross inside window ignored
def test_new_episode_after_window():
    h = [20] * 5 + [31] + [25] * 25 + [33]; assert V.vix30_episode(h) == (True, 0)
def test_only_riskon_longs():
    h = [20] * 20 + [31]
    assert V.vix30_bonus(L('XLU'), None, fake(h))['vix30_bonus'] == 0
    assert V.vix30_bonus(L('XLK', 'SHORT'), None, fake(h))['vix30_bonus'] == 0
    assert V.vix30_bonus(L(None, a='crypto'), None, fake(h))['vix30_bonus'] == 5
def test_already_above_30_no_first_cross():
    assert V.vix30_episode([35] * 40) == (False, None)
if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'): f(); print('PASS', k)
