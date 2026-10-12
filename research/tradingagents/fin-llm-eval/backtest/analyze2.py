"""TradingAgents sample: decisions vs realized, market-adjusted, robustness. Writes tracker_backtest.md."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import json, glob, re, datetime as dt, pandas as pd, numpy as np
B=(_SCANNER_ROOT + '/fin-llm-eval/backtest')

def md(df,index=True):
    df=df.reset_index() if index else df
    cols=[str(c) for c in df.columns]
    lines=['| '+' | '.join(cols)+' |','|'+'---|'*len(cols)]
    for _,r in df.iterrows():
        lines.append('| '+' | '.join('' if (isinstance(v,float) and np.isnan(v)) else (f'{v:.2f}' if isinstance(v,float) else str(v)) for v in r.values)+' |')
    return '\n'.join(lines)
P=pd.read_csv((_SCANNER_ROOT + '/scanner-tool-eval/setups_prepared.csv'))[['setup_id','rtot','xtot','x5','x20','xeth_tot','ntot']]
rows=[json.load(open(f)) for f in sorted(glob.glob(f'{B}/runs/*.json'))]
out=[f"# TradingAgents decisions vs realized outcomes — scanner setup sample\n",
     f"_Auto-generated {dt.datetime.now():%Y-%m-%d %H:%M} IL by backtest/analyze2.py. Model: local Qwen2.5-3B-Instruct Q4_K_M via Ollama (7B was OOM-killed on the shared box), all agents; analysts = market (+fundamentals for stocks); 1 debate round, 1 risk round, 500-token cap per call. Sample = backtest/sample_order.csv (stratified by source×direction, wins/losses alternated, crypto and Grok pre-breakout double-weighted), taken in priority order._\n"]
if not rows:
    out.append("No finished setups yet."); open((_SCANNER_ROOT + '/fin-llm-eval/tracker_backtest.md'),'w').write('\n'.join(out)); raise SystemExit
d=pd.DataFrame(rows)
n_all=len(d); fails=d[d.ok!=True]
d=d[d.ok==True].copy().merge(P,on='setup_id',how='left')
def verdict(r):
    dec=str(r.decision).strip().lower()
    bull=dec in('buy','overweight'); bear=dec in('sell','underweight')
    if dec=='hold' or not(bull or bear): return 'neutral(hold)'
    if r.direction=='LONG': return 'agree' if bull else 'disagree'
    return 'agree' if bear else 'disagree'
d['verdict']=d.apply(verdict,axis=1)
d['src']=d.platform.str.replace(r' \(.*\)','',regex=True)
for c in ['rtot','xtot','x5','x20','xeth_tot']: d[c]=d[c]*100
d['win']=d.rtot>0
# leakage scan: any date in agent text later than trade_date?
DATE=re.compile(r'(20\d\d-\d\d-\d\d)')
def late(r):
    txt=' '.join(str(r.get(k,'')) for k in ['market_report','fundamentals_report','bull','bear','final_trade_decision','trader_plan','investment_plan'])
    return sorted({x for x in DATE.findall(txt) if x>r.trade_date})
d['dates_after_cutoff']=d.apply(late,axis=1)
def agg(g):
    return pd.Series(dict(n=len(g),mean_ret=g.rtot.mean(),median_ret=g.rtot.median(),mean_excess=g.xtot.mean(),median_excess=g.xtot.median(),win_rate=g.win.mean()))
def tbl(df): return md(df.round(2))
out.append(f"Finished: {n_all} runs, {len(d)} ok, {len(fails)} failed.  **Small sample — treat everything below as anecdotal, not evidence.**\n")
out.append("Returns are direction-adjusted (a short that fell = positive), in %. `ret` = tracker total return; `excess` = same window vs SPY (stocks) / BTC-USD (crypto) from the cutoff close (scanner-tool-eval/setups_prepared.csv).\n")
out.append("## Per setup\n"); cols=['priority','ticker','asset','direction','src','automation','trade_date','decision','verdict','rtot','xtot','xeth_tot','runtime_s','llm_calls','prompt_tokens','completion_tokens']
out.append(md(d[cols].round(2),index=False))
out.append("\n## By TradingAgents verdict (agree = TA rating in the scanner's direction)\n"); out.append(tbl(d.groupby('verdict').apply(agg)))
dec=d[d.verdict!='neutral(hold)']
if len(dec):
    hit=((dec.verdict=='agree')==dec.win).mean()
    out.append(f"\nHit rate on non-hold verdicts (agree&win or disagree&loss): **{hit:.0%}** (n={len(dec)}); base win rate of sample {d.win.mean():.0%}.")
    if len(d[d.verdict=='agree']) and len(d[d.verdict!='agree']):
        a=d[d.verdict=='agree'].xtot; b=d[d.verdict!='agree'].xtot
        try:
            from scipy.stats import mannwhitneyu
            p=mannwhitneyu(a.dropna(),b.dropna()).pvalue; out.append(f"Mann-Whitney agree vs not-agree on excess return: p={p:.2f}.")
        except Exception: pass
out.append("\n## By source × verdict\n"); out.append(tbl(d.groupby(['src','verdict']).apply(agg)))
out.append("\n## By asset × verdict\n"); out.append(tbl(d.groupby(['asset','verdict']).apply(agg)))
cr=d[d.asset=='crypto']
if len(cr): out.append(f"\nCrypto excess vs ETH-USD: mean {cr.xeth_tot.mean():.2f}%, median {cr.xeth_tot.median():.2f}% (n={cr.xeth_tot.notna().sum()}).")
pb=d[d.automation.astype(str).str.contains('prebreakout')]
if len(pb): out.append("\n## Grok pre-breakout only\n"+tbl(pb.groupby('verdict').apply(agg)))
out.append("\n## Robustness: drop the top tickers (NEAR — Grok crypto, XP — Perplexity, IOVA — main sheet) and the single best ticker\n")
best=d.groupby('ticker').rtot.sum().idxmax() if len(d) else None
for lab,mask in [('all',d.ticker.notna()),('without NEAR/XP/IOVA',~d.ticker.str.upper().str.replace('-USD','').isin(['NEAR','XP','IOVA'])),(f'without best ticker in sample ({best})',d.ticker!=best)]:
    g=d[mask]; out.append(f"\n**{lab}**\n"); out.append(tbl(g.groupby('verdict').apply(agg)))
out.append("\n## Leakage check on agent output\n")
lk=d[d.dates_after_cutoff.str.len()>0]
out.append(f"Setups whose agent text mentions any date after the cutoff: {len(lk)} of {len(d)}." + ('' if lk.empty else '\n'+md(lk[['priority','ticker','trade_date','dates_after_cutoff']],index=False)))
out.append("\n## Runtime (box CPU, contended)\n")
out.append(f"Per setup: mean {d.runtime_s.mean()/60:.1f} min, median {d.runtime_s.median()/60:.1f} min; LLM calls mean {d.llm_calls.mean():.1f}; prompt tokens mean {d.prompt_tokens.mean():.0f}; completion tokens mean {d.completion_tokens.mean():.0f}.")
if len(fails): out.append("\n## Failures\n"+md(fails[['priority','ticker','error']],index=False))
open((_SCANNER_ROOT + '/fin-llm-eval/tracker_backtest.md'),'w').write('\n'.join(out))
d.drop(columns=[c for c in ['market_report','fundamentals_report','bull','bear','final_trade_decision','trader_plan','investment_plan','tb'] if c in d]).to_csv(f'{B}/backtest_results.csv',index=False)
print('written', len(d))
