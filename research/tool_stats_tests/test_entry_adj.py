import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'scanner'))
import pandas as pd, entry_adj as E
def closes(rs):   # SPY flat, ETF moves rs over 5 sessions
    idx = pd.bdate_range('2026-10-01', periods=10)
    return lambda cut: pd.DataFrame({'SPY': [100.0] * 10, 'XLY': [100.0] * 9 + [100 * (1 + rs)]}, index=idx)
def C(d, td=None, etf='XLY', a='stock'): return {'direction': d, 'asset': a, 'sector_etf': etf, '_eg': {'td_to_earnings': td}}
def test_earn15_shorts_only():
    E._RS.clear(); assert E.components(C('SHORT', 10), '2026-10-16', closes(0))['exp_adj_penalty_earn'] == 8
    E._RS.clear(); assert E.components(C('SHORT', 16), '2026-10-16', closes(0))['exp_adj_penalty_earn'] == 0
    E._RS.clear(); assert E.components(C('LONG', 10), '2026-10-16', closes(0))['exp_adj_penalty_earn'] == 0
def test_sector_rs_flag_weight0():
    E._RS.clear(); r = E.components(C('SHORT'), '2026-10-17', closes(0.02)); assert r['exp_adj_rs_against'] and r['exp_adj_penalty_rs'] == 0
    E._RS.clear(); assert E.components(C('LONG'), '2026-10-18', closes(0.02))['exp_adj_penalty_rs'] == 0
    E._RS.clear(); r = E.components(C('LONG'), '2026-10-19', closes(-0.02)); assert r['exp_adj_rs_against'] and r['exp_adj_penalty_rs'] == 0
    E._RS.clear(); assert E.components(C('SHORT'), '2026-10-20', closes(0.01))['exp_adj_penalty_rs'] == 0
    E._RS.clear(); assert E.components(C('LONG', a='crypto'), '2026-10-21', closes(-0.05))['exp_adj_penalty_rs'] == 0
def test_short_cap():
    assert E.total_penalty('SHORT', 20, {'exp_adj_penalty_earn': 8, 'exp_adj_penalty_rs': 0}) == 25
    assert E.total_penalty('SHORT', 10, {'exp_adj_penalty_earn': 8}) == 18
    assert E.total_penalty('LONG', 0, {'exp_adj_penalty_rs': 0}) == 0
if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'): f(); print('PASS', k)
