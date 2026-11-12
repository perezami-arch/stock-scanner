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
# Pure-rule fixtures below predate Nov 1 and Nov 7. They opt into the current 5x/touch rule.
# Migration tests pass the two dates explicitly.
ST_RAW = ST.stop_status
def _current_policy(*a, **k):
    k.setdefault('policy_from', None)
    k.setdefault('touch_from', None)
    return ST_RAW(*a, **k)
ST.stop_status = _current_policy

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
    x.index = pd.bdate_range('2026-11-09', periods=len(x))
    monkeypatch.setattr(RC, 'get_bars', lambda *a, **k: x)
    path = tmp_path / 'paper.csv'
    rows = []
    for direction in ('LONG', 'SHORT'):
        rows.append({'ticker': 'AAA', 'asset': 'stock', 'direction': direction, 'entry_session': str(x.index[W].date()),
                     'target_level': '', 'stop_atr_mult': '', 'stop': '', 'status': 'pending_entry'})
    old = bars([100] * (W + 3), 2.0)   # entry before the policy date keeps the stop it was opened with
    old.index = pd.bdate_range(end='2026-10-30', periods=len(old))
    rows.append({'ticker': 'OLD', 'asset': 'stock', 'direction': 'LONG', 'entry_session': '2026-10-19',
                 'target_level': '', 'stop_atr_mult': 4.0, 'stop': 92.5, 'status': 'open'})
    pd.DataFrame(rows).to_csv(path, index=False)
    monkeypatch.setattr(RC, 'get_bars', lambda *a, **k: x if a[0] == 'AAA' else old)
    assert RD.update_paper(str(x.index[-1] + pd.Timedelta(hours=30)), path=str(path)) == 3
    out = pd.read_csv(path)
    new_long = out[(out.ticker == 'AAA') & (out.direction == 'LONG')].iloc[0]
    assert float(new_long.stop_atr_mult) == 5.0
    assert float(new_long.stop) == pytest.approx(100 - 5 * _atr(x, W - 1), abs=1e-3)
    assert float(out.loc[(out.ticker == 'AAA') & (out.direction == 'SHORT'), 'stop_atr_mult'].iloc[0]) == 4.0
    kept = out[out.ticker == 'OLD'].iloc[0]
    assert float(kept.stop_atr_mult) == 4.0 and float(kept.stop) == 92.5

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

def _around_policy(last='2026-11-13', n=None, span_policy=True):
    """Business-day frame ending on `last`. Entry bar W is before 2026-11-07."""
    n = n or (W + 20)
    x = bars([100] * n, 2.0)
    x.index = pd.bdate_range(end=last, periods=n)
    assert x.index[W].date() < SPOL.POLICY_EFFECTIVE
    if span_policy:
        assert x.index[-1].date() >= SPOL.POLICY_EFFECTIVE
    return x

def _stamp_last(x, o, h, l, c):
    x.iloc[-1, x.columns.get_loc('Open')] = o
    x.iloc[-1, x.columns.get_loc('High')] = h
    x.iloc[-1, x.columns.get_loc('Low')] = l
    x.iloc[-1, x.columns.get_loc('Close')] = c
    return x

def test_touch_starts_nov1_and_long_5x_starts_nov7():
    # 2026-10-30: wick through the 4x stop, close holds above it. Close rule does not exit.
    pre = _stamp_last(_around_policy(last='2026-10-30', n=W + 2, span_policy=False), 100, 100, 91, 93)
    entry = pre.index[W]
    before = ST_RAW(pre, 'stock', 'LONG', entry, 100.0, policy_from=SPOL.LONG_5X_EFFECTIVE, touch_from=SPOL.TOUCH_EFFECTIVE)
    assert before['stopped'] is False and before['initial_stop'] == pytest.approx(100 - 4 * _atr(pre, W - 1), abs=1e-3)
    # 2026-11-04: same wick is an intraday touch at 4x, fill = worse of stop and open. 5x would not exit.
    nov4 = _stamp_last(_around_policy(last='2026-11-04', n=W + 2, span_policy=False), 100, 100, 91, 93)
    entry = nov4.index[W]
    touched = ST_RAW(nov4, 'stock', 'LONG', entry, 100.0, policy_from=SPOL.LONG_5X_EFFECTIVE, touch_from=SPOL.TOUCH_EFFECTIVE)
    only_5x = ST_RAW(nov4, 'stock', 'LONG', entry, 100.0, policy_from=None, touch_from=None)
    assert only_5x['stopped'] is False
    assert touched['stopped'] and touched['exit_mode'] == 'touch' and touched['stop_date'] == '2026-11-04'
    assert touched['initial_stop'] == pytest.approx(100 - 4 * _atr(nov4, W - 1), abs=1e-3)
    assert touched['exit_price'] == pytest.approx(touched['initial_stop'], abs=1e-3)
    # Gap on Nov 5 fills at the open, not at the stop. A stored Nov 4/5 fill is not recomputed.
    gap = _stamp_last(_around_policy(last='2026-11-05', n=W + 2, span_policy=False), 80, 85, 70, 82)
    entry = gap.index[W]
    g = ST_RAW(gap, 'stock', 'LONG', entry, 100.0, policy_from=SPOL.LONG_5X_EFFECTIVE, touch_from=SPOL.TOUCH_EFFECTIVE)
    assert g['stopped'] and g['stop_date'] == '2026-11-05' and g['exit_price'] == 80
    kept = ST_RAW(gap, 'stock', 'LONG', entry, 100.0, policy_from=SPOL.LONG_5X_EFFECTIVE, touch_from=SPOL.TOUCH_EFFECTIVE,
                  committed_exit={'date': '2026-11-04', 'price': 80.0})
    assert kept['exit_mode'] == 'committed' and kept['stop_date'] == '2026-11-04' and kept['exit_price'] == 80.0
    assert kept['stopped'] is True

def test_open_long_live_stop_is_not_lowered_on_the_policy_date():
    x = _around_policy()
    entry = x.index[W]
    pure = ST_RAW(x, 'stock', 'LONG', entry, 100.0, policy_from=None, touch_from=None)
    floor = 96.0
    migrated = ST_RAW(x, 'stock', 'LONG', entry, 100.0, policy_from=SPOL.LONG_5X_EFFECTIVE, touch_from=SPOL.TOUCH_EFFECTIVE, floor=floor)
    assert pure['next_level'] < floor
    assert migrated['stopped'] is False
    assert migrated['next_level'] >= floor
    assert migrated['initial_stop'] == pytest.approx(100 - 4 * _atr(x, W - 1), abs=1e-3)
    fresh = bars([100] * (W + 3), 2.0)
    fresh.index = pd.bdate_range('2026-11-09', periods=len(fresh))
    opened = ST_RAW(fresh, 'stock', 'LONG', fresh.index[W], 100.0, policy_from=SPOL.LONG_5X_EFFECTIVE, touch_from=SPOL.TOUCH_EFFECTIVE)
    mid = bars([100] * (W + 3), 2.0)
    mid.index = pd.bdate_range(end='2026-11-06', periods=len(mid))
    assert SPOL.TOUCH_EFFECTIVE <= mid.index[W].date() < SPOL.LONG_5X_EFFECTIVE
    opened_mid = ST_RAW(mid, 'stock', 'LONG', mid.index[W], 100.0, policy_from=SPOL.LONG_5X_EFFECTIVE, touch_from=SPOL.TOUCH_EFFECTIVE)
    assert opened_mid['initial_stop'] == pytest.approx(100 - 4 * _atr(mid, W - 1), abs=1e-3)
    assert opened['initial_stop'] == pytest.approx(100 - 5 * _atr(fresh, W - 1), abs=1e-3)

def test_checkpoints_keep_a_closed_exit_and_the_open_floor(tmp_path, monkeypatch):
    import run_checkpoints as RC, scanner_lessons as SLS
    x = _around_policy(n=W + 12)
    monkeypatch.setattr(RC, 'get_bars', lambda *a, **k: x)
    ST.stop_status = ST_RAW
    try:
        entry = str(x.index[W].date())
        reg = pd.DataFrame([
            {'trade_id': 'OPEN', 'trade_key': 'AAA|LONG|x', 'ticker': 'AAA', 'asset': 'stock', 'direction': 'LONG',
             'entry_session': entry, 'entry_ref': 100, 'status': 'open', 'current_stop': 96.0,
             'checkpoints_done': '', 'is_trial': False, 'is_sim': False},
            {'trade_id': 'SHUT', 'trade_key': 'BBB|LONG|y', 'ticker': 'BBB', 'asset': 'stock', 'direction': 'LONG',
             'entry_session': entry, 'entry_ref': 100, 'status': 'closed', 'exit_date': '2026-10-23', 'exit_price': 91.5,
             'exit_reason': 'סטופ', 'current_stop': 94.0, 'checkpoints_done': '', 'is_trial': False, 'is_sim': False},
        ])
        for k in SLS.REG_COLS:
            if k not in reg: reg[k] = None
        rp = str(tmp_path / 'reg.csv'); SLS.save_registry(reg, rp)
        RC.run(str(x.index[-1] + pd.Timedelta(hours=30)), rp, str(tmp_path / 'ledger.csv'), str(tmp_path / 'cp'), no_models=True)
        got = SLS.load_registry(rp).set_index('trade_id')
        assert got.loc['SHUT', 'status'] == 'closed'
        assert str(got.loc['SHUT', 'exit_date'])[:10] == '2026-10-23' and float(got.loc['SHUT', 'exit_price']) == 91.5
        assert got.loc['OPEN', 'status'] == 'open'
        assert float(got.loc['OPEN', 'current_stop']) >= 96.0
    finally:
        ST.stop_status = _current_policy

def test_account_fill_follows_nov1_and_keeps_recorded_exits():
    # Before Nov 1 the historical account filled at the stop. Nov 4 and Nov 5 use worse-of.
    assert SPOL.account_stop_hit('LONG', 80, 85, 70, 90, '2026-10-30') == 90
    assert SPOL.account_stop_hit('LONG', 80, 85, 70, 90, '2026-11-04') == 80
    assert SPOL.account_stop_hit('LONG', 80, 85, 70, 90, '2026-11-05') == 80
    assert SPOL.account_stop_hit('SHORT', 120, 130, 110, 110, '2026-10-30') == 110
    assert SPOL.account_stop_hit('SHORT', 120, 130, 110, 110, '2026-11-04') == 120
    assert SPOL.account_stop_hit('LONG', 100, 101, 95, 90, '2026-11-09') is None
    recorded = ('2026-11-04', 80.0)
    assert SPOL.apply_account_exit(recorded, 'LONG', 80, 85, 70, 90, '2026-11-04') == recorded
    assert SPOL.apply_account_exit(None, 'LONG', 80, 85, 70, 90, '2026-11-05') == ('2026-11-05', 80.0)

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
    # same status and exit date, different fill
    priced = [dict(base[1], exit_price='10.50'), dict(base[0])]
    pd.DataFrame(base).to_csv(a, index=False); pd.DataFrame(priced).to_csv(b, index=False)
    assert MM.main(str(a), str(b)) == 1

def test_mismatch_skips_paper_and_trial_only_account(tmp_path, monkeypatch):
    import run_daily_report as RD
    tracker = tmp_path / 'positions_registry.csv'
    account = tmp_path / 'account_positions.csv'
    real = {'ticker': 'AAA', 'direction': 'LONG', 'entry_session': '2026-10-19', 'status': 'closed',
            'exit_date': '2026-10-23', 'exit_price': '91.5', 'is_trial': False}
    pd.DataFrame([real]).to_csv(tracker, index=False)
    pd.DataFrame([
        {'ticker': 'AAA', 'direction': 'LONG', 'entry_session': '2026-10-19', 'status': 'closed',
         'exit_date': '2026-10-23', 'exit_price': '91.5', 'book': 'real'},
        {'ticker': 'TRIAL', 'direction': 'SHORT', 'entry_session': '2026-10-19', 'status': 'open',
         'exit_date': '', 'exit_price': '', 'book': 'trial'},
    ]).to_csv(account, index=False)
    assert MM.daily_check(str(tracker), str(account))['ok'] is True
    paper = tmp_path / 'paper_trades_ledger.csv'
    pd.DataFrame([{'ticker': 'ZZ', 'paper_id': 'p', 'is_paper': True, 'status': 'open', 'entry_session': '2026-10-19'}]).to_csv(paper, index=False)
    blocked = MM.daily_check(str(tracker), str(paper))
    assert blocked['compared'] is False and 'paper' in blocked['blocker']
    monkeypatch.setenv('ACCOUNT_POSITIONS', str(tmp_path / 'missing.csv'))
    missing = RD.status_check(str(tracker))
    assert missing['compared'] is False and 'paper' in missing['blocker'].lower()
    text = open(os.path.join(REPO, 'scanner', 'scanner_platforms.py'), encoding='utf-8').read()
    assert '5xATR14 chandelier for stock longs' in text
    assert '4xATR14 chandelier on closes' not in text
