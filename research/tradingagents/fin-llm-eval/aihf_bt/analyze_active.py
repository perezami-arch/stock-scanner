"""ai-hedge-fund personas (and TradingAgents runs) as approve/veto filters, outcomes under the ACTIVE scanner policy.
Active policy (stocks, close-based, costs 0.02% fee + 0.05% slippage per side, PIT entry = next open after cutoff,
open trades marked at the 2026-10-07 close): LONG = chandelier 4xATR14 + sell 1/2 at Fib 1.618 (sim policy tg_ch_HY2_c);
SHORT = chandelier 4xATR14 (chand4_c). Excess vs SPY = same entry->exit window (shorts: ret + SPY ret).
Verdict: approve = agent signal in the setup's direction; veto = opposite; neutral; abstain = no data / error."""
import json, glob, warnings, numpy as np, pandas as pd
from scipy.stats import mannwhitneyu, wilcoxon
warnings.filterwarnings('ignore')
T = pd.read_csv('/workspace/trading-frameworks-eval/iaf/sim_trades_enriched.csv', low_memory=False)
A = pd.concat([T[(T.policy == 'tg_ch_HY2_c') & (T.direction == 'LONG')], T[(T.policy == 'chand4_c') & (T.direction == 'SHORT')]])
A = A[A.asset == 'stock'][['setup_id', 'ret_net', 'x_spy', 'status', 'entry_date', 'in_main', 'dup', 'direction', 'ticker']]
A = A.rename(columns={'direction': 'dir_sim', 'ticker': 'ticker_sim'})
def stats(g):
    r, x = g.ret * 100, g.x_spy * 100
    return dict(N=len(g), entry_days=g.entry_date.nunique(), mean=r.mean(), median=r.median(), hit=(r > 0).mean() * 100,
                x_spy_mean=x.mean(), x_spy_median=x.median(), open_share=(g.status == 'open@end').mean() * 100)
def fmt(rows):
    cols = list(rows[0].keys()); L = ['| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)]
    for r in rows: L.append('| ' + ' | '.join(f'{v:.2f}' if isinstance(v, (float, np.floating)) else str(v) for v in r.values()) + ' |')
    return '\n'.join(L)
def pval(a, b):
    if len(a) < 3 or len(b) < 3: return 'n/a (<3)'
    return f'{mannwhitneyu(a, b).pvalue:.2f}'
def section(d, title, extra=''):
    d = d.merge(A, on='setup_id', how='left'); miss = d.ret_net.isna().sum(); d = d[d.ret_net.notna()].copy(); d['ret'] = d.ret_net
    out = [f'### {title}\n', f'N = {len(d)} stock setups with an active-policy trade ({miss} without one). {extra}\n']
    vc = pd.crosstab(d.direction, d.verdict).reindex(columns=['approve', 'neutral', 'veto', 'abstain'], fill_value=0)
    vc.loc['ALL'] = vc.sum(); out.append('Verdict counts (approve = agrees with the setup direction, veto = opposes):\n')
    out.append(fmt([dict(side=i, **{c: int(vc.loc[i, c]) for c in vc.columns}) for i in vc.index]))
    for side in ['ALL', 'LONG', 'SHORT']:
        s = d if side == 'ALL' else d[d.direction == side]
        if not len(s): continue
        rows = [dict(group='all setups (no filter)', **stats(s))]
        for v in ['approve', 'neutral', 'veto', 'abstain']:
            g = s[s.verdict == v]
            if len(g): rows.append(dict(group=v, **stats(g)))
        kept = s[s.verdict != 'veto']; rows.append(dict(group='veto filter: keep all but vetoed', **stats(kept)))
        out.append(f'\n**{side}** (active policy, % per trade):\n\n' + fmt(rows))
        out.append(f'\np (Mann-Whitney, return): vetoed vs rest {pval(s[s.verdict=="veto"].ret, s[s.verdict!="veto"].ret)}; '
                   f'approved vs rest {pval(s[s.verdict=="approve"].ret, s[s.verdict!="approve"].ret)}; '
                   f'neutral vs abstain {pval(s[s.verdict=="neutral"].ret, s[s.verdict=="abstain"].ret)}. '
                   f'Unfiltered x SPY > 0, Wilcoxon p {wilcoxon(s.x_spy).pvalue:.2f}.' if len(s) >= 6 else '')
    return '\n'.join(out), d
def verdict_aihf(r):
    if not r.get('ok') or r.get('abstained') or r.get('signal') in (None, np.nan): return 'abstain'
    s = r['signal']
    if s == 'neutral': return 'neutral'
    return 'approve' if (s == 'bullish') == (r['direction'] == 'LONG') else 'veto'
secs, V = [], {}
for p in ['druckenmiller', 'buffett']:
    d = pd.DataFrame([json.loads(l) for l in open(f'/workspace/fin-llm-eval/aihf_bt/{p}.jsonl')])
    d['verdict'] = d.apply(verdict_aihf, axis=1)
    ok = d[d.ok & (d.abstained == False)]
    extra = (f'Leak check: {int(d.leak.sum())} setups used data dated after the cutoff. Median runtime {d.runtime_s.median():.0f}s/setup on the box CPU; '
             f'LLM tokens per setup (1 call): median prompt {ok.llm_pt.median():.0f}, output {ok.llm_ct.median():.0f}. '
             f'Abstained/failed: {", ".join(sorted(d[d.verdict=="abstain"].ticker))}.')
    txt, dm = section(d[['setup_id', 'ticker', 'direction', 'verdict', 'confidence']], f'ai-hedge-fund `{p}` (blind persona, EDGAR PIT, Qwen2.5-3B on the box)', extra)
    vt = dm[dm.verdict.isin(['veto', 'approve'])]
    txt += '\n\nDirectional calls: ' + '; '.join(f'{r.ticker} {r.direction} -> {r.verdict} ({r.ret*100:+.1f}%, x SPY {r.x_spy*100:+.1f})' for r in vt.itertuples())
    secs.append(txt); V[p] = d.set_index('setup_id').verdict
# agreement between the two personas
j = pd.concat(V, axis=1).dropna()
secs.append('### Druckenmiller vs Buffett agreement\n\n' + fmt([dict(druckenmiller=i, **{c: int(v) for c, v in r.items()}) for i, r in pd.crosstab(j.druckenmiller, j.buffett).iterrows()]))
# sample vs universe
U = A[(A.in_main == True) & (A.dup == False)].copy(); U['ret'] = U.ret_net
rows = []
for side in ['ALL', 'LONG', 'SHORT']:
    s = U if side == 'ALL' else U[U.dir_sim == side]; rows.append(dict(set=f'all stock setups in the main sheet, {side}', **stats(s)))
secs.append('### Context: the full stock universe under the same policy (the 60 are the first 60 stock rows of the stratified sample)\n\n' + fmt(rows))
# TradingAgents
R = [json.load(open(f)) for f in sorted(glob.glob('/workspace/fin-llm-eval/backtest/runs/*.json'))]
if R:
    d = pd.DataFrame(R)
    def vt(r):
        if not r.get('ok'): return 'abstain'
        dec = str(r.get('decision')).strip().lower(); bull = dec in ('buy', 'overweight'); bear = dec in ('sell', 'underweight')
        if not (bull or bear): return 'neutral'
        return 'approve' if bull == (r['direction'] == 'LONG') else 'veto'
    d['verdict'] = d.apply(vt, axis=1); d = d.merge(A, on='setup_id', how='left')
    secs.append('### TradingAgents completed setups (Qwen2.5-3B on the box; anecdotal only)\n\n' + '\n'.join(
        f'- {r.ticker} {r.direction} ({r.trade_date}): **{r.decision}** -> {r.verdict}; active-policy outcome {r.ret_net*100:+.1f}% (x SPY {r.x_spy*100:+.1f}, {r.status}); '
        f'{r.runtime_s/60:.0f} min, {int(r.llm_calls)} LLM calls, {int(r.prompt_tokens):,} prompt / {int(r.completion_tokens):,} output tokens'
        if r.ok else f'- {r.ticker} {r.direction}: failed ({str(r.error)[:120]})' for r in d.itertuples()))
open('/workspace/fin-llm-eval/aihf_bt/filter_results_active.md', 'w').write('\n\n'.join(secs) + '\n'); print('\n\n'.join(secs))
