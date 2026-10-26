import sys, os
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(H, '..', '..', 'scanner')]
import critic_score as C
def test_weights_original():
    assert C.WEIGHTS == {'grok': 1.0, 'pplx': 1.0, 'claude': 1.0, 'gpt': 1.0, 'jev': 0.0}
def test_confirm_cap():
    r = C.score(dict(grok_verdict='approve', pplx_verdict='approve', gpt_verdict='approve', claude_direction_view='supports'))
    assert r['points'] == 2.0 and not r['watch_only']
def test_flags_and_out_of_domain_veto():
    r = C.score(dict(grok_verdict='flag', pplx_verdict='approve', gpt_verdict='veto', claude_direction_view='neutral'))
    assert r['flag_pts'] == -3.0 and r['points'] == -2.0 and r['watch_only']
def test_domain_veto():
    assert C.score(dict(pplx_verdict='veto'), earnings_blocked=True)['deleted']
    r = C.score(dict(pplx_verdict='veto', grok_verdict='veto'))
    assert r['flag_pts'] == -2.0 and not r['deleted'] and not r['watch_only']
def test_claude_opposes_is_flag():
    assert C.score(dict(claude_direction_view='opposes'))['points'] == -1.0
if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'): f(); print('ok', k)
