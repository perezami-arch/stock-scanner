"""Approve/veto outcome comparison for ai-hedge-fund personas and TradingAgents on the scanner sample.
Outcomes: /workspace/trading-frameworks-eval/iaf/sim_trades_enriched.csv (PIT entry = next open after cutoff, costs incl.,
open trades marked at 2026-10-07 close). Policies: hold (no stop) and chand4_c (active rule: 4xATR14 chandelier, close-based)."""
import json, glob, warnings, pandas as pd, numpy as np
warnings.filterwarnings("ignore")
from scipy.stats import mannwhitneyu
T = pd.read_csv('/workspace/trading-frameworks-eval/iaf/sim_trades_enriched.csv', low_memory=False)
O = T[T.policy == 'hold'][['setup_id', 'ret_net', 'x_spy', 'x_btc', 'status', 'days']].rename(columns={'ret_net': 'hold', 'x_spy': 'hold_x_spy', 'x_btc': 'hold_x_btc'})
C = T[T.policy == 'chand4_c'][['setup_id', 'ret_net', 'status']].rename(columns={'ret_net': 'chand4', 'status': 'chand4_status'})
O = O.merge(C, on='setup_id', how='left')
def fmt(df):
    cols = [str(c) for c in df.columns]; L = ['| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)]
    for _, r in df.iterrows(): L.append('| ' + ' | '.join(f'{v:.2f}' if isinstance(v, float) else str(v) for v in r.values) + ' |')
    return '\n'.join(L)
def agg(g):
    xm = g.hold_x_spy.where(g.asset == 'stock', g.hold_x_btc) if 'asset' in g else g.hold_x_spy
    return pd.Series(dict(n=len(g), hold_mean=100 * g.hold.mean(), hold_median=100 * g.hold.median(), hold_x_mkt=100 * xm.mean(),
                          chand4_mean=100 * g.chand4.mean(), chand4_median=100 * g.chand4.median(), win_rate=100 * (g.hold > 0).mean()))
def report(d, label, name):
    out = [f'### {label}\n']
    d = d.merge(O, on='setup_id', how='left')
    miss = d.hold.isna().sum(); d = d[d.hold.notna()]
    out.append(f'N = {len(d)} with outcomes ({miss} without a simulated trade: no price data / excluded).\n')
    t = d.groupby('verdict').apply(agg).reset_index(); allrow = agg(d); allrow['verdict'] = 'ALL (no filter)'
    t = pd.concat([t, pd.DataFrame([allrow])], ignore_index=True)
    out.append(fmt(t.round(2)))
    a = d[d.verdict == 'approve']; b = d[d.verdict != 'approve']
    if len(a) >= 3 and len(b) >= 3:
        p = mannwhitneyu(a.hold, b.hold).pvalue; p2 = mannwhitneyu(a.chand4.dropna(), b.chand4.dropna()).pvalue
        out.append(f'\nApproved vs not-approved, Mann-Whitney p: hold {p:.2f}, chand4 {p2:.2f}.')
    if len(d) >= 5:
        best = d.groupby('ticker').hold.sum().idxmax(); dd = d[d.ticker != best]
        t2 = dd.groupby('verdict').apply(agg).reset_index()
        out.append(f'\nWithout the best ticker ({best}):\n\n' + fmt(t2.round(2)))
        for side in ['LONG', 'SHORT']:
            s = d[d.direction == side]
            if len(s): out.append(f'\n{side} only:\n\n' + fmt(s.groupby('verdict').apply(agg).reset_index().round(2)))
    return '\n'.join(out), d
def verdict_aihf(r):
    if not r.get('ok') or r.get('abstained'): return 'abstain'
    s = r.get('signal')
    if s == 'neutral': return 'neutral'
    return 'approve' if (s == 'bullish') == (r['direction'] == 'LONG') else 'veto'
sections = []
for p in ['druckenmiller', 'buffett']:
    f = f'/workspace/fin-llm-eval/aihf_bt/{p}.jsonl'
    try: rows = [json.loads(l) for l in open(f)]
    except FileNotFoundError: continue
    d = pd.DataFrame(rows); d['verdict'] = d.apply(verdict_aihf, axis=1); d['asset'] = 'stock'
    lk = int(d.leak.sum()); mx = (d.max_data_date.fillna('') <= d.trade_date).mean()
    txt, dm = report(d, f'ai-hedge-fund `{p}` persona (blind, EDGAR PIT, Qwen2.5-3B)', p)
    ok = d[d.ok & ~d.abstained.fillna(True).astype(bool)]
    sections.append(txt + f'\n\nVerdict counts: {d.verdict.value_counts().to_dict()}. Leak check: {lk} setups used any filing/price dated after the cutoff '
                    f'(every snapshot input dated <= trade_date: {mx:.0%}). Runtime/setup: median {d.runtime_s.median():.0f}s; '
                    f'LLM tokens median prompt {ok.llm_pt.median():.0f}, output {ok.llm_ct.median():.0f}.\n')
rows = [json.load(open(f)) for f in sorted(glob.glob('/workspace/fin-llm-eval/backtest/runs/*.json'))]
if rows:
    d = pd.DataFrame(rows); d = d[d.ok == True]
    def vt(r):
        dec = str(r.decision).strip().lower(); bull = dec in ('buy', 'overweight'); bear = dec in ('sell', 'underweight')
        if not (bull or bear): return 'neutral'
        return 'approve' if bull == (r.direction == 'LONG') else 'veto'
    d['verdict'] = d.apply(vt, axis=1)
    txt, dm = report(d, 'TradingAgents full multi-agent (Qwen2.5-3B, market+fundamentals analysts, 1 debate + 1 risk round)', 'ta')
    sections.append(txt + '\n\nPer setup: ' + '; '.join(f"{r.ticker} {r.direction} -> {r.decision} ({r.runtime_s/60:.0f} min, {r.llm_calls} calls, {r.prompt_tokens} prompt / {r.completion_tokens} output tok)" for r in d.itertuples()) + '\n')
open('/workspace/fin-llm-eval/aihf_bt/filter_results.md', 'w').write('\n\n'.join(sections)); print('\n\n'.join(sections))
