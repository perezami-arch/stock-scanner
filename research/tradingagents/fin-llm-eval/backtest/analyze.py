import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import json, glob, pandas as pd, numpy as np
rows=[json.load(open(f)) for f in sorted(glob.glob((_SCANNER_ROOT + '/fin-llm-eval/backtest/runs/*.json')))]
d=pd.DataFrame(rows)
print('runs:',len(d),'ok:',int(d.ok.sum()))
if 'error' in d: print(d[d.ok!=True][['priority','ticker','error']].to_string())
d=d[d.ok==True].copy()
def verdict(r):
    dec=str(r.decision).strip().lower()
    bull=dec in('buy','overweight'); bear=dec in('sell','underweight')
    if dec=='hold': return 'flag'
    if r.direction=='LONG': return 'approve' if bull else ('veto' if bear else 'flag')
    return 'approve' if bear else ('veto' if bull else 'flag')
d['verdict']=d.apply(verdict,axis=1)
d['ret']=d.tracker_total_return*100; d['win']=d.ret>0
d['platform_s']=d.platform.str.replace(r' \(.*\)','',regex=True)
print(d[['priority','ticker','asset','direction','model','automation','trade_date','decision','verdict','ret','runtime_s','llm_calls','prompt_tokens','completion_tokens']].to_string())
print('\nby verdict'); print(d.groupby('verdict').agg(n=('ret','size'),avg_ret=('ret','mean'),med_ret=('ret','median'),win_rate=('win','mean')).round(2))
print('\nby decision'); print(d.decision.value_counts())
print('\nby platform x verdict'); print(d.groupby(['platform_s','verdict']).agg(n=('ret','size'),avg_ret=('ret','mean'),win_rate=('win','mean')).round(2))
print('\nby direction x verdict'); print(d.groupby(['direction','verdict']).agg(n=('ret','size'),avg_ret=('ret','mean'),win_rate=('win','mean')).round(2))
print('\nby asset x verdict'); print(d.groupby(['asset','verdict']).agg(n=('ret','size'),avg_ret=('ret','mean'),win_rate=('win','mean')).round(2))
appr=d.verdict=='approve'
# "hit rate": approve on winners or veto on losers
dec=d[d.verdict!='flag']
if len(dec): print('\nhit rate (approve&win or veto&loss) on non-flag:', round(((dec.verdict=='approve')==dec.win).mean(),3), 'n=',len(dec))
print('base win rate of sample:', round(d.win.mean(),3), 'avg ret', round(d.ret.mean(),2))
print('\nruntime s: mean',d.runtime_s.mean().round(0),'median',d.runtime_s.median(),' calls mean',d.llm_calls.mean(),' prompt tok mean',d.prompt_tokens.mean().round(0),' compl tok mean',d.completion_tokens.mean().round(0))
d.drop(columns=[c for c in ['market_report','fundamentals_report','bull','bear','final_trade_decision','trader_plan','investment_plan'] if c in d]).to_csv((_SCANNER_ROOT + '/fin-llm-eval/backtest/backtest_results.csv'),index=False)
