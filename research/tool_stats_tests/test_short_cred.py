import sys, os, json, tempfile
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(H, '..', '..', 'scanner'), os.path.join(H, '..', '..', 'modules')]
import pandas as pd, numpy as np
import short_cred as S
DAYS = pd.bdate_range('2026-09-01', '2026-12-31')
def fake_bars(paths):   # deterministic prices: shorts in 'UP' rise (warning correct), 'DN' fall
    def f(sym, start):
        k = np.arange(len(DAYS)); g = 1.004 if sym.startswith('UP') else (0.996 if sym.startswith('DN') else 1.0)
        p = 100 * g ** k; return pd.DataFrame({'Open': p, 'Close': p}, index=DAYS)
    return f
def ledger(tmp, rows):
    cols = ['ticker', 'asset', 'direction', 'decision_point', 'asof_local', 'platform', 'verdict', 'conviction_or_sentiment']
    p = os.path.join(tmp, 'L.csv'); pd.DataFrame(rows, columns=cols).to_csv(p, index=False); return [p]
def R(t, d, plat, v, c=None): return [t, 'stock', 'SHORT', 'entry', f'{d} 09:00:00+03:00', plat, v, c]
def test_hits_shrink_and_nondiscrimination():
    with tempfile.TemporaryDirectory() as tmp:
        rows = []
        for i, t in enumerate(['UP1', 'UP2', 'DN1', 'DN2', 'DN3', 'DN4']):
            rows += [R(t, '2026-09-07', 'gpt', 'veto' if t.startswith('UP') else 'flag'), R(t, '2026-09-07', 'grok', 'approve'),
                     R(t, '2026-09-07', 'claude', 'neutral', 35 if t == 'DN1' else 50), R(t, '2026-09-07', 'jev', 'x (+0.60)' if t == 'UP1' else 'x (-0.5)')]
        c = S.compute('2026-10-15T06:00:00Z', paths=ledger(tmp, rows), bars_fn=fake_bars(None), save=False)['models']
        assert c['gpt']['levels_counted'] == ['strong'] and c['gpt']['n'] == 2 and c['gpt']['hits'] == 2       # flag on 100% -> only veto counts
        assert abs(c['gpt']['shrunk_hit'] - 17 / 32) < 1e-3 and abs(c['gpt']['penalty_pts'] - 0.62) < 0.01
        assert c['claude']['n'] == 1 and c['claude']['hits'] == 0 and c['claude']['penalty_pts'] == 0          # wrong -> 0, never bonus
        assert c['jev']['n'] == 1 and c['jev']['hits'] == 1 and c['grok']['n'] == 0
def test_no_lookahead():
    with tempfile.TemporaryDirectory() as tmp:
        rows = [R('UP1', '2026-10-12', 'gpt', 'veto')] + [R(f'DN{i}', '2026-10-12', 'gpt', 'approve') for i in range(5)]
        c = S.compute('2026-10-16T06:00:00Z', paths=ledger(tmp, rows), bars_fn=fake_bars(None), save=False)['models']['gpt']
        assert c['n'] == 0                                                         # d5 close (19.10) not yet known on 16.10
        c = S.compute('2026-10-20T06:00:00Z', paths=ledger(tmp, rows), bars_fn=fake_bars(None), save=False)['models']['gpt']
        assert c['n'] == 1 and c['warnings'][0]['h'] == 5
        rows2 = rows + [R('UP9', '2026-10-25', 'gpt', 'veto')]                    # scans after the cutoff are ignored
        c = S.compute('2026-10-20T06:00:00Z', paths=ledger(tmp, rows2), bars_fn=fake_bars(None), save=False)['models']['gpt']
        assert c['n_shorts_seen'] == 6
def test_penalty_caps():
    cred = {'models': {m: {'penalty_pts': 10.0, 'levels_counted': ['strong', 'weak']} for m in S.MODELS}}
    row = {'gpt_verdict': 'veto', 'grok_verdict': 'flag', 'pplx_verdict': 'veto', 'claude_conviction': 30, 'claude_direction_view': 'neutral', 'jev_news_sentiment': 0.9}
    pts, who = S.penalty(cred, row); assert pts == 20 and len(who) == 5
    cred['models']['gpt']['levels_counted'] = ['strong']; pts, who = S.penalty(cred, {'gpt_verdict': 'flag'}); assert pts == 0
def test_veto_blocked_registered_as_paper():
    import scanner_lessons as SLS, scanner_levelsfile as LF
    with tempfile.TemporaryDirectory() as tmp:
        rd = os.path.join(tmp, '2026-10-19_0900'); os.makedirs(rd + '/levels')
        for t, d in (('AAA', 'LONG'), ('BBB', 'SHORT')):
            import glob; src = sorted(glob.glob(os.path.join(H, '..', '..', 'reports', '*', 'daily', '*', 'levels', '*.json')))[0]
            L = json.load(open(src)); L['direction'] = d; json.dump(L, open(LF.path(rd, {'t': t, 'direction': d}), 'w'))
        pd.DataFrame([{'setup_id': f'x|{t}|{d}', 'ticker': t, 'asset': 'stock', 'direction': d, 'entry': 10, 'stop': 12 if d == 'SHORT' else 8, 'target': None,
                       'recon_status': 'תואם', 'earnings_status': 'מותר', 'cutoff_utc': '2026-10-19 06:00:00+00:00'} for t, d in (('AAA', 'LONG'), ('BBB', 'SHORT'))]).to_csv(rd + '/tracker_rows.csv', index=False)
        json.dump({'scan_asof_local': '2026-10-19 09:00:00+03:00'}, open(rd + '/run_meta.json', 'w')); json.dump(['AAA|LONG'], open(rd + '/selected.json', 'w'))
        reg = os.path.join(tmp, 'reg.csv')
        n = SLS.register_run(rd, path=reg, veto_blocked={'BBB|SHORT': 'gpt,jev'}); r = pd.read_csv(reg)
        assert n == 2 and set(r.ticker) == {'AAA', 'BBB'}
        assert r.set_index('ticker').blocked_by_veto.fillna('').to_dict() == {'AAA': '', 'BBB': 'gpt,jev'} and (r.status == 'open').all()
if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'): f(); print('PASS', k)
