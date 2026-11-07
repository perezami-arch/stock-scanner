"""17.10 fixes in the positions tracker: (1) the stock trailing stop (long 5xATR14, short 4xATR14) only ratchets in the
trade's favour and never crosses the initial stop; (2) the 1/2 take-profit at Fib 1.618 (stock longs, close-checked) is
recorded in the registry with its date / price and the whole-position (weighted) return.
Run: python -m pytest research/tool_stats_tests/test_stop_ratchet_half.py  (builds a throw-away SCANNER_ROOT with ops/materialize_root.sh)."""
import os, sys, subprocess, tempfile, json
import numpy as np, pandas as pd
import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
ROOT = os.environ.get('TEST_SCANNER_ROOT') or tempfile.mkdtemp(prefix='sroot_')
if not os.path.exists(os.path.join(ROOT, 'scanner_stops.py')):
    subprocess.run(['bash', os.path.join(REPO, 'ops', 'materialize_root.sh'), REPO, ROOT], check=True, capture_output=True)
os.environ['SCANNER_ROOT'] = ROOT
sys.path.insert(0, ROOT)
import scanner_stops as ST          # noqa: E402
# These fixtures are dated before 2026-11-07. Ask for the current rule on every bar;
# the migration default (4x close until that date) is covered in test_stop_intraday_mult.
_stop_status = ST.stop_status
def _current_policy(*a, **k):
    k.setdefault('policy_from', None)
    return _stop_status(*a, **k)
ST.stop_status = _current_policy

def bars(closes, rng, start='2026-08-03', opens=None, highs=None):
    """daily OHLC: close given, high/low = close +/- rng/2 (rng per bar -> controls ATR14)."""
    c = np.asarray(closes, float); r = np.broadcast_to(np.asarray(rng, float), c.shape)
    idx = pd.bdate_range(start, periods=len(c))
    o = c.copy() if opens is None else np.asarray(opens, float)
    h = c + r / 2 if highs is None else np.asarray(highs, float)
    return pd.DataFrame({'Open': o, 'High': np.maximum(h, np.maximum(o, c)), 'Low': np.minimum(c - r / 2, o), 'Close': c, 'Volume': 1e6}, index=idx)

W = 30                                                     # warm-up bars before the entry bar (ATR14 ~ 2)

def _series(x, entry_i, direction, fill, tp=None):
    """stop_status evaluated day by day (as the daily run sees it): one dict per completed bar from the entry bar on."""
    return [ST.stop_status(x.iloc[:j + 1], 'stock', direction, x.index[entry_i], fill, tp_half=tp) for j in range(entry_i, len(x))]

def test_long_never_loosens_on_atr_expansion():
    # +10 in 5 days, then flat closes with a huge range -> ATR14 expands -> the raw chandelier (max close - 4*ATR) falls
    cl = [100] * W + [100, 102, 104, 106, 108, 110] + [110] * 12
    rg = [2] * (W + 6) + [14] * 12
    x = bars(cl, rg); s = _series(x, W, 'LONG', 100.0)
    lv = [d['next_level'] for d in s]; init = s[0]['initial_stop']
    assert all(not d['stopped'] for d in s)
    assert all(b >= a - 1e-9 for a, b in zip(lv, lv[1:])), lv            # monotone up
    assert min(lv) >= init - 1e-9
    assert s[-1]['next_level_raw'] < s[-1]['next_level'] - 1               # the old (plain) rule would have loosened
    assert s[-1]['next_level'] == max(lv)

def test_long_floor_at_initial_stop():
    # no gain and an ATR spike right after entry: raw chandelier < initial stop -> the live stop stays at the initial stop
    cl = [100] * W + [100, 100, 99, 100, 99, 100, 99, 100]
    rg = [2] * W + [12] * 8
    x = bars(cl, rg); s = _series(x, W, 'LONG', 100.0)
    init = s[0]['initial_stop']
    K = ST.RULES[('stock', 'LONG')]['stop_atr_mult']
    assert K == 5.0
    assert abs(init - (100 - K * ST.atr14(x.High.values, x.Low.values, x.Close.values)[W - 1])) < 1e-3
    assert all(d['next_level'] >= init - 1e-9 for d in s)
    assert s[-1]['next_level_raw'] < init and s[-1]['next_level'] == init

def test_short_mirror_never_loosens():
    cl = [100] * W + [100, 98, 96, 94, 92, 90] + [90] * 12
    rg = [2] * (W + 6) + [14] * 12
    x = bars(cl, rg); s = _series(x, W, 'SHORT', 100.0)
    lv = [d['next_level'] for d in s]; init = s[0]['initial_stop']
    assert all(not d['stopped'] for d in s)
    assert all(b <= a + 1e-9 for a, b in zip(lv, lv[1:])), lv            # monotone down
    assert max(lv) <= init + 1e-9 and s[-1]['next_level_raw'] > s[-1]['next_level'] + 1

def test_ratchet_triggers_exit_that_plain_rule_missed():
    # after the run-up the ratcheted stop is touched by the last low even though ATR expansion pushed the raw chandelier below that low
    cl = [100] * W + [100, 104, 108, 112, 114, 114, 114, 114, 101]
    rg = [2] * (W + 5) + [16, 16, 16, 16]
    x = bars(cl, rg)
    prev = ST.stop_status(x.iloc[:-1], 'stock', 'LONG', x.index[W], 100.0)
    s = ST.stop_status(x, 'stock', 'LONG', x.index[W], 100.0)
    # the plain chandelier has already loosened below the low; the ratchet is what the low touches
    assert prev['stopped'] is False and prev['next_level_raw'] < float(x.Low.iloc[-1]) < prev['next_level']
    assert s['stopped'] and s['stop_date'] == str(x.index[-1].date()) and s['exit_mode'] == 'touch'
    assert s['stop_close'] == pytest.approx(prev['next_level'], abs=5e-4)
    assert s['stop_close'] < float(x.Open.iloc[-1])

def test_half_take_profit_close_checked_ko_like():
    # KO 13-15.10: entry bar k, k+1 trades above the target intraday but closes below, k+2 closes at 92.00 >= 91.6363
    cl = [86] * W + [90.56, 91.0, 92.00, 92.3]
    hi = [86.5] * W + [91.0, 91.9, 92.4, 92.6]
    x = bars(cl, 1.0, highs=hi); x.iloc[W, x.columns.get_loc('Open')] = 90.56
    s = ST.stop_status(x, 'stock', 'LONG', x.index[W], 90.56, tp_half=91.6363)
    assert s['half_taken'] and s['half_date'] == str(x.index[W + 2].date()) and s['half_price'] == 92.00
    s1 = ST.stop_status(x.iloc[:W + 2], 'stock', 'LONG', x.index[W], 90.56, tp_half=91.6363)
    assert s1['half_taken'] is False and s1['half_date'] is None                      # intraday touch / k+1 close do not count
    w = ST.weighted_return('LONG', 90.56, 92.3, s['half_price'])
    assert abs(w - (0.5 * (92.00 / 90.56 - 1) + 0.5 * (92.3 / 90.56 - 1))) < 1e-12
    assert ST.weighted_return('LONG', 100, 110, None) == pytest.approx(0.10)
    assert ST.weighted_return('SHORT', 100, 90, None) == pytest.approx(0.10)

def test_stop_before_half_means_no_half():
    cl = [100] * W + [100, 100, 80, 120]
    x = bars(cl, 2.0); s = ST.stop_status(x, 'stock', 'LONG', x.index[W], 100.0, tp_half=110)
    assert s['stopped'] and not s['half_taken'] and s['half_price'] is None

def test_crypto_fixed_stop_unchanged():
    cl = [100] * W + [100, 105, 110, 90, 95]
    x = bars(cl, 2.0); A = ST.atr14(x.High.values, x.Low.values, x.Close.values)
    s = ST.stop_status(x, 'crypto', 'LONG', x.index[W], 100.0)
    assert s['next_level'] == round(100 - 3 * A[W - 1], 4)                          # fixed 3xATR, no trailing after the rally
    assert s['stopped'] and s['stop_date'] == str(x.index[W + 3].date()) and s['stop_close'] == 90

def test_registry_records_half_and_weighted_return(tmp_path, monkeypatch):
    """run_checkpoints.run on a 1-position registry (bars + benchmark stubbed, no models, < 5 sessions -> no checkpoint)."""
    import run_checkpoints as RC, scanner_lessons as SLS
    cl = [86] * W + [90.56, 91.0, 92.00, 92.3]
    x = bars(cl, 1.0); x.iloc[W, x.columns.get_loc('Open')] = 90.56
    spy = bars([500] * (W + 4), 2.0)
    monkeypatch.setattr(RC, 'get_bars', lambda *a, **k: x)
    monkeypatch.setattr(SLS, 'bench', lambda *a, **k: spy)
    reg = pd.DataFrame([{'trade_id': 'T1', 'trade_key': 'KO|LONG|x', 'ticker': 'KO', 'asset': 'stock', 'direction': 'LONG',
                         'entry_session': str(x.index[W].date()), 'entry_ref': 88.93, 'stop_initial': 82.9, 'target': 91.6363,
                         'status': 'open', 'checkpoints_done': '', 'is_trial': False, 'is_sim': False}])
    for k in SLS.REG_COLS:
        if k not in reg: reg[k] = None
    rp = str(tmp_path / 'reg.csv'); SLS.save_registry(reg, rp)
    RC.run(str(x.index[-1] + pd.Timedelta(hours=30)), rp, str(tmp_path / 'ledger.csv'), str(tmp_path / 'cp'), no_models=True)
    r = SLS.load_registry(rp).iloc[0]
    assert str(r.half_taken) == 'True' and r.half_date == str(x.index[W + 2].date()) and float(r.half_price) == 92.0
    exp = 0.5 * (92.0 / 90.56 - 1) + 0.5 * (92.3 / 90.56 - 1)
    assert abs(float(r.unrealized_dir_weighted) - round(exp, 5)) < 1e-9
    assert abs(float(r.unrealized_dir) - round(92.3 / 90.56 - 1, 5)) < 1e-9          # full-position value unchanged
    assert float(r.current_stop) >= float(r.stop_initial_fill)

def test_half_after_exit_ignored():
    import run_checkpoints as RC
    assert RC.half_exit({'half_taken': True, 'half_date': '2026-11-20', 'half_price': 95.0}, '2026-11-10') == (None, None)
    assert RC.half_exit({'half_taken': True, 'half_date': '2026-11-05', 'half_price': 95.0}, '2026-11-10') == (95.0, '2026-11-05')
    assert RC.half_exit({'next_level': 1.0}) == (None, None)
