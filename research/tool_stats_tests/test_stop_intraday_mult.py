"""Direction-specific intraday stops (long 5xATR14, short 4xATR14).

Covers both directions, gap fills, no-entry/no-exit, favourable-only ratchets, legacy 4x vs current
defaults, and the same multiplier in the tracker, the scanner paper ledger, and the simulated-account walk.
A stop built from today's close must not be applied to today's low (long) or high (short).

Run: python -m pytest research/tool_stats_tests/test_stop_ratchet_half.py research/tool_stats_tests/test_stop_intraday_mult.py
"""
import importlib.util, os, sys, subprocess, tempfile
import numpy as np, pandas as pd
import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
ROOT = os.environ.get('TEST_SCANNER_ROOT') or tempfile.mkdtemp(prefix='sroot_')
if not os.path.exists(os.path.join(ROOT, 'scanner_stops.py')) or not os.path.exists(os.path.join(ROOT, 'stop_policy.py')):
    subprocess.run(['bash', os.path.join(REPO, 'ops', 'materialize_root.sh'), REPO, ROOT], check=True, capture_output=True)
os.environ['SCANNER_ROOT'] = ROOT
sys.path.insert(0, ROOT)
import scanner_stops as ST          # noqa: E402
import stop_policy as SPOL          # noqa: E402

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

MM = _load('status_mismatch', os.path.join(REPO, 'ops', 'status_mismatch.py'))
ACCT = _load('recompute_nocrypto', os.path.join(REPO, 'research', 'no-crypto-recompute', 'recompute_nocrypto.py'))

def bars(closes, rng, start='2026-08-03', opens=None, highs=None, lows=None):
    c = np.asarray(closes, float); r = np.broadcast_to(np.asarray(rng, float), c.shape)
    idx = pd.bdate_range(start, periods=len(c))
    o = c.copy() if opens is None else np.asarray(opens, float)
    h = c + r / 2 if highs is None else np.asarray(highs, float)
    lo = c - r / 2 if lows is None else np.asarray(lows, float)
    return pd.DataFrame({'Open': o, 'High': np.maximum(h, np.maximum(o, c)),
                         'Low': np.minimum(lo, np.minimum(o, c)), 'Close': c, 'Volume': 1e6}, index=idx)

W = 30

def _atr(x, i):
    return float(ST.atr14(x.High.values, x.Low.values, x.Close.values)[i])

def test_current_and_legacy_multipliers():
    assert SPOL.CURRENT_STOCK_ATR_MULT == {'LONG': 5.0, 'SHORT': 4.0}
    assert SPOL.LEGACY_STOCK_ATR_MULT == {'LONG': 4.0, 'SHORT': 4.0}
    assert ST.RULES[('stock', 'LONG')]['stop_atr_mult'] == 5.0
    assert ST.RULES[('stock', 'SHORT')]['stop_atr_mult'] == 4.0
    assert ST.RULES[('crypto', 'LONG')]['stop_atr_mult'] == 3.0
    assert SPOL.stop_atr_mult('crypto', 'SHORT') is None
    import run_unified_scan as RU
    assert RU.paper_stop_atr_mult('stock', 'LONG') == 5.0
    assert RU.paper_stop_atr_mult('stock', 'SHORT') == 4.0
    assert RU.paper_stop_atr_mult('crypto', 'LONG') == 3.0

def test_long_is_wider_than_legacy_four_and_short_stays_four():
    x = bars([100] * (W + 3), 2.0)
    ed, fill = x.index[W], 100.0
    cur = ST.stop_status(x, 'stock', 'LONG', ed, fill)
    old = ST.stop_status(x, 'stock', 'LONG', ed, fill, atr_mult=4.0)
    assert cur['initial_stop'] < old['initial_stop']          # 5x sits further below the entry
    assert (fill - cur['initial_stop']) / (fill - old['initial_stop']) == pytest.approx(5 / 4, rel=1e-6)
    sh = ST.stop_status(x, 'stock', 'SHORT', ed, fill)
    sh4 = ST.stop_status(x, 'stock', 'SHORT', ed, fill, atr_mult=4.0)
    sh5 = ST.stop_status(x, 'stock', 'SHORT', ed, fill, atr_mult=5.0)
    assert sh['initial_stop'] == sh4['initial_stop']
    assert sh5['initial_stop'] > sh['initial_stop']            # a 5x short would be a wider (higher) stop
    assert sh['initial_stop'] == pytest.approx(fill + 4 * _atr(x, W - 1), abs=1e-3)
    act = ST.active_stop(x, 'stock', 'LONG', entry=fill)
    assert act['stop_atr_mult'] == 5.0
    assert act['initial_stop'] == pytest.approx(fill - 5 * act['atr14_wilder'], abs=1e-2)
    # Fib 1.618 price does not move when the chandelier multiplier does
    h4, h5 = ST.half_at_1618(x, fill, atr_mult=4), ST.half_at_1618(x, fill, atr_mult=5)
    assert h4['tp_half_1618'] == h5['tp_half_1618']
    assert '4xATR' in h4['partial_exit_rule'] and '5xATR' in h5['partial_exit_rule']

def test_no_same_bar_lookahead_long_and_short():
    # Entry bar rallies. The stop computed from THAT close sits through the day's extreme,
    # but the extreme is judged only against the stop that existed before the bar.
    x = bars([100] * (W + 1), 2.0)
    x.iloc[W, x.columns.get_loc('Open')] = 100
    x.iloc[W, x.columns.get_loc('High')] = 160
    x.iloc[W, x.columns.get_loc('Low')] = 95
    x.iloc[W, x.columns.get_loc('Close')] = 160
    pre = ST.stop_status(x, 'stock', 'LONG', x.index[W], 100.0)
    assert pre['stopped'] is False
    assert pre['initial_stop'] < 95 < pre['next_level']        # today's low is inside the NEW stop, outside the old one
    # Next session is stopped by the level this call just published, not by a level rebuilt from the new bar.
    nxt = x.index[-1] + pd.tseries.offsets.BDay(1)
    lv = pre['next_level']
    row = pd.DataFrame({'Open': [lv + 5], 'High': [lv + 6], 'Low': [lv - 1], 'Close': [lv + 4], 'Volume': [1e6]}, index=[nxt])
    full = ST.stop_status(pd.concat([x, row]), 'stock', 'LONG', x.index[W], 100.0)
    assert full['stopped'] and full['stop_date'] == str(nxt.date())
    assert full['exit_price'] == pytest.approx(lv, abs=5e-4)
    assert full['exit_price'] < float(row.Open.iloc[0])
    # Short mirror: collapse today. New tighter stop would tag today's high; the prior stop does not.
    y = bars([100] * (W + 1), 2.0)
    y.iloc[W, y.columns.get_loc('Open')] = 100
    y.iloc[W, y.columns.get_loc('High')] = 105
    y.iloc[W, y.columns.get_loc('Low')] = 40
    y.iloc[W, y.columns.get_loc('Close')] = 40
    pre_s = ST.stop_status(y, 'stock', 'SHORT', y.index[W], 100.0)
    assert pre_s['stopped'] is False
    assert pre_s['next_level'] < 105 < pre_s['initial_stop']
    nxt = y.index[-1] + pd.tseries.offsets.BDay(1)
    lv = pre_s['next_level']
    row = pd.DataFrame({'Open': [lv - 5], 'High': [lv + 1], 'Low': [lv - 6], 'Close': [lv - 4], 'Volume': [1e6]}, index=[nxt])
    full_s = ST.stop_status(pd.concat([y, row]), 'stock', 'SHORT', y.index[W], 100.0)
    assert full_s['stopped'] and full_s['exit_price'] == pytest.approx(lv, abs=5e-4)
    assert full_s['exit_price'] > float(row.Open.iloc[0])

def test_gap_fill_is_the_worse_of_stop_and_open():
    x = bars([100] * (W + 1), 2.0)
    x.iloc[W, x.columns.get_loc('Open')] = 70
    x.iloc[W, x.columns.get_loc('High')] = 80
    x.iloc[W, x.columns.get_loc('Low')] = 60
    x.iloc[W, x.columns.get_loc('Close')] = 75
    s = ST.stop_status(x, 'stock', 'LONG', x.index[W], 100.0)
    assert s['stopped'] and s['exit_mode'] == 'touch'
    assert s['exit_price'] == 70 and s['exit_price'] < s['initial_stop']
    y = bars([100] * (W + 1), 2.0)
    y.iloc[W, y.columns.get_loc('Open')] = 130
    y.iloc[W, y.columns.get_loc('High')] = 140
    y.iloc[W, y.columns.get_loc('Low')] = 120
    y.iloc[W, y.columns.get_loc('Close')] = 125
    sh = ST.stop_status(y, 'stock', 'SHORT', y.index[W], 100.0)
    assert sh['stopped'] and sh['exit_price'] == 130 and sh['exit_price'] > sh['initial_stop']

def test_entry_trades_before_stop_and_no_entry_means_no_exit():
    x = bars([100] * (W + 1), 2.0)
    x.iloc[W, x.columns.get_loc('Open')] = 100
    x.iloc[W, x.columns.get_loc('High')] = 101
    x.iloc[W, x.columns.get_loc('Low')] = 80
    x.iloc[W, x.columns.get_loc('Close')] = 100
    s = ST.stop_status(x, 'stock', 'LONG', x.index[W], 100.0, tp_half=90)   # target already "through" does not fill before the stop
    assert s['stopped'] and s['stop_date'] == str(x.index[W].date())
    assert s['exit_price'] == pytest.approx(s['initial_stop'], abs=1e-6)
    assert s['exit_price'] > 80                                  # fill is the stop, not the low
    assert s.get('half_taken') is False                          # half stays close-checked and loses to the stop
    # no bar on/after the entry session
    future = x.index[-1] + pd.Timedelta(days=30)
    miss = ST.stop_status(x.iloc[:W], 'stock', 'LONG', future, 100.0)
    assert miss['stopped'] is False and miss.get('exit_price') is None and miss.get('stop_date') is None
    # a crash on the bar BEFORE the entry does not exit the trade
    z = bars([100] * (W + 4), 2.0)
    z.iloc[W, z.columns.get_loc('Low')] = 1
    z.iloc[W, z.columns.get_loc('Close')] = 50
    later = ST.stop_status(z, 'stock', 'SHORT', z.index[W + 1], 100.0)
    assert later['stopped'] is False

def test_ratchet_does_not_loosen_either_direction():
    cl = [100] * W + [100, 104, 108, 112, 116] + [116] * 8
    rg = [2] * (W + 5) + [20] * 8
    for direction, sign in (('LONG', 1), ('SHORT', -1)):
        closes = cl if direction == 'LONG' else [200 - v for v in cl]
        x = bars(closes, rg)
        series = [ST.stop_status(x.iloc[:j + 1], 'stock', direction, x.index[W], 100.0) for j in range(W, len(x))]
        assert all(not d['stopped'] for d in series)
        lv = [d['next_level'] for d in series]
        if direction == 'LONG':
            assert all(b >= a - 1e-9 for a, b in zip(lv, lv[1:]))
            assert series[-1]['next_level_raw'] < series[-1]['next_level'] - 1
        else:
            assert all(b <= a + 1e-9 for a, b in zip(lv, lv[1:]))
            assert series[-1]['next_level_raw'] > series[-1]['next_level'] + 1
        assert sign * (series[-1]['next_level'] - series[0]['initial_stop']) >= -1e-9

def test_crypto_stays_close_checked_three_atr():
    x = bars([100] * (W + 5), 2.0)
    x.iloc[-1, x.columns.get_loc('Low')] = 10          # intraday pierce must not stop a crypto long
    x.iloc[-1, x.columns.get_loc('Close')] = 100
    s = ST.stop_status(x, 'crypto', 'LONG', x.index[W], 100.0)
    assert s['stopped'] is False
    assert s['next_level'] == pytest.approx(100 - 3 * _atr(x, W - 1), abs=1e-3)

def test_tracker_scanner_and_account_share_the_walk():
    gaps = {'LONG': dict(Open=70, High=80, Low=60, Close=75), 'SHORT': dict(Open=130, High=140, Low=120, Close=125)}
    for direction, px in gaps.items():
        x = bars([100] * (W + 2), 2.0)
        for col, v in px.items():
            x.iloc[W, x.columns.get_loc(col)] = v
        A = ST.atr14(x.High.values, x.Low.values, x.Close.values)
        st = ST.stop_status(x, 'stock', direction, x.index[W], 100.0)
        rep = SPOL.replay_trailing(x.Open.values, x.High.values, x.Low.values, x.Close.values, A, direction, W, 100.0)
        assert rep['mult'] == ST.RULES[('stock', direction)]['stop_atr_mult']
        assert round(rep['initial_stop'], 4) == st['initial_stop']
        assert rep['stopped'] is True and st['stopped'] is True
        assert rep['exit_price'] == st['exit_price'] and rep['stop_index'] == W
    x = bars([100] * (W + 2), 2.0)
    A = ST.atr14(x.High.values, x.Low.values, x.Close.values)
    leg = SPOL.replay_trailing(x.Open.values, x.High.values, x.Low.values, x.Close.values, A, 'LONG', W, 100.0, legacy=True)
    assert leg['mult'] == 4.0
    assert leg['initial_stop'] > ST.stop_status(x, 'stock', 'LONG', x.index[W], 100.0)['initial_stop']

def test_paper_ledger_records_direction_mult(tmp_path, monkeypatch):
    import run_checkpoints as RC, run_daily_report as RD
    x = bars([100] * (W + 3), 2.0)
    monkeypatch.setattr(RC, 'get_bars', lambda *a, **k: x)
    path = tmp_path / 'paper.csv'
    rows = []
    for direction in ('LONG', 'SHORT'):
        rows.append({'ticker': 'AAA', 'asset': 'stock', 'direction': direction, 'entry_session': str(x.index[W].date()),
                     'target_level': '', 'stop_atr_mult': 4.0, 'status': 'pending_entry'})
    pd.DataFrame(rows).to_csv(path, index=False)
    assert RD.update_paper(str(x.index[-1] + pd.Timedelta(hours=30)), path=str(path)) == 2
    out = pd.read_csv(path)
    assert float(out.loc[out.direction == 'LONG', 'stop_atr_mult'].iloc[0]) == 5.0
    assert float(out.loc[out.direction == 'SHORT', 'stop_atr_mult'].iloc[0]) == 4.0
    long_stop = float(out.loc[out.direction == 'LONG', 'stop'].iloc[0])
    assert long_stop == pytest.approx(100 - 5 * _atr(x, W - 1), abs=1e-3)

def test_tracker_registry_uses_the_same_initial_stop(tmp_path, monkeypatch):
    import run_checkpoints as RC, scanner_lessons as SLS
    x = bars([100] * (W + 3), 2.0)
    x.iloc[W, x.columns.get_loc('Open')] = 100
    monkeypatch.setattr(RC, 'get_bars', lambda *a, **k: x)
    reg = pd.DataFrame([
        {'trade_id': 'L', 'trade_key': 'AAA|LONG|x', 'ticker': 'AAA', 'asset': 'stock', 'direction': 'LONG',
         'entry_session': str(x.index[W].date()), 'entry_ref': 100, 'stop_initial': 1, 'target': None,
         'status': 'open', 'checkpoints_done': '', 'is_trial': False, 'is_sim': False},
        {'trade_id': 'S', 'trade_key': 'BBB|SHORT|x', 'ticker': 'BBB', 'asset': 'stock', 'direction': 'SHORT',
         'entry_session': str(x.index[W].date()), 'entry_ref': 100, 'stop_initial': 1, 'target': None,
         'status': 'open', 'checkpoints_done': '', 'is_trial': False, 'is_sim': False},
    ])
    for k in SLS.REG_COLS:
        if k not in reg: reg[k] = None
    rp = str(tmp_path / 'reg.csv'); SLS.save_registry(reg, rp)
    RC.run(str(x.index[-1] + pd.Timedelta(hours=30)), rp, str(tmp_path / 'ledger.csv'), str(tmp_path / 'cp'), no_models=True)
    got = SLS.load_registry(rp).set_index('direction')
    assert float(got.loc['LONG', 'stop_initial_fill']) == pytest.approx(100 - 5 * _atr(x, W - 1), abs=1e-3)
    assert float(got.loc['SHORT', 'stop_initial_fill']) == pytest.approx(100 + 4 * _atr(x, W - 1), abs=1e-3)
    assert float(got.loc['LONG', 'current_stop']) + 1e-9 >= float(got.loc['LONG', 'stop_initial_fill'])
    assert float(got.loc['SHORT', 'current_stop']) - 1e-9 <= float(got.loc['SHORT', 'stop_initial_fill'])

def test_account_dedup_keeps_earliest_ticker_direction():
    rows = [
        {'ticker': 'mu', 'direction': 'long', 'entry_date': '2026-10-19', 'id': 'late'},
        {'ticker': 'MU', 'direction': 'LONG', 'entry_date': '2026-10-12', 'id': 'early'},
        {'ticker': 'MU', 'direction': 'LONG', 'entry_date': None, 'id': 'already_open'},
        {'ticker': 'MU', 'direction': 'SHORT', 'entry_date': '2026-10-01', 'id': 'short'},
    ]
    kept = {r['id'] for r in SPOL.dedup_earliest(rows)}
    assert kept == {'already_open', 'short'}
    only = SPOL.dedup_earliest(rows[:2])
    assert [r['id'] for r in only] == ['early']
    book = ACCT.positions()
    keys = [(p[0], p[1]) for p in book]
    assert len(keys) == len(set(keys))
    assert len(book) == len(ACCT.P)

def test_status_mismatch_flags_disagreement(tmp_path, capsys):
    a = tmp_path / 'tracker.csv'; b = tmp_path / 'account.csv'
    base = [
        {'ticker': 'AAA', 'direction': 'LONG', 'entry_session': '2026-10-19', 'status': 'open', 'exit_date': '', 'exit_price': ''},
        {'ticker': 'AAA', 'direction': 'SHORT', 'entry_session': '2026-10-19', 'status': 'closed', 'exit_date': '2026-10-23', 'exit_price': '10'},
    ]
    pd.DataFrame(base).to_csv(a, index=False); pd.DataFrame(base).to_csv(b, index=False)
    assert MM.main(str(a), str(b)) == 0
    bad = [dict(base[0], status='closed', exit_date='2026-10-30'), base[1]]
    pd.DataFrame(bad).to_csv(b, index=False)
    assert MM.main(str(a), str(b)) == 1
    capsys.readouterr()
    # same ticker and session, opposite directions: a long/short swap is a mismatch, not a match
    swapped = [
        dict(base[0], status='closed', exit_date='2026-10-23'),
        dict(base[1], status='open', exit_date=''),
    ]
    pd.DataFrame(base).to_csv(a, index=False); pd.DataFrame(swapped).to_csv(b, index=False)
    assert MM.main(str(a), str(b)) == 1
