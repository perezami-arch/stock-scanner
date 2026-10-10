import pandas as pd, numpy as np
P=pd.read_csv('hold-no-stop-longs-2026-10-08.csv')
main=P[P.separate.isna()]; sep=P[P.separate.notna()]
GO=['Grok momentum','Grok near-low','Grok prebreakout','Grok crypto','Grok x-trends','Grok portfolio-news']
def summ(x,name):
    if not len(x): return dict(group=name,N=0)
    b=x.sort_values('return_pct')
    f=lambda rr: '; '.join(f"{t} {d[5:7]}/{d[8:10]} {v:+.1f}%" for t,d,v in rr)
    return dict(group=name,N=len(x),avg=x.return_pct.mean(),med=x.return_pct.median(),pos=(x.return_pct>0).mean()*100,
        pnl=x.pnl_usd_per_1000.sum(),days=x.days_held.mean(),spy=x.spy_return_pct.mean(),exc=x.excess_vs_spy_pct.mean(),
        best=f(zip(b.ticker[::-1][:3],b.alert_date[::-1][:3],b.return_pct[::-1][:3])),worst=f(zip(b.ticker[:3],b.alert_date[:3],b.return_pct[:3])))
rows=[summ(main[main.group==g],g) for g in GO]
rows.insert(3,dict(group='Grok daily-stock-tracker',N=0))
G=main[main.group.str.startswith('Grok')]
rows+= [summ(G,'GROK TOTAL'),summ(main[main.group=='Perplexity'],'PERPLEXITY TOTAL'),summ(main[main.group=='Bot v2.8'],'Bot v2.8 (ref, excl. 07.10)'),
        summ(main[main.group.str.startswith('Original')],'Original sheet שפל שנתי (ref)'),summ(sep,'Bot v2.8 scan 07.10 (1 day, separate)')]
pp=main[main.group=='Perplexity']; lo,hi=pp.alert_date.min(),pp.alert_date.max()
Gw=G[(G.alert_date>=lo)&(G.alert_date<=hi)]
rows+=[dict(group=f'--- FAIR WINDOW {lo}..{hi} ---'),summ(Gw,'Grok (window)'),summ(pp,'Perplexity (window)'),
       summ(Gw[Gw.asset=='stock'],'Grok stocks (window)'),summ(pp[pp.asset=='stock'],'Perplexity stocks (window)'),
       summ(Gw[Gw.asset=='crypto'],'Grok crypto-asset (window)'),summ(pp[pp.asset=='crypto'],'Perplexity crypto-asset (window)')]
T=pd.DataFrame(rows); pd.set_option('display.width',250); pd.set_option('display.max_colwidth',80)
print(T[['group','N','avg','med','pos','pnl','days','spy','exc']].round(1).to_string(index=False))
print(T[['group','best','worst']].to_string(index=False))
T.to_csv('hold-no-stop-longs-2026-10-08_summary.csv',index=False,encoding='utf-8-sig')
print('Perplexity runs:',sorted(pp.alert_date.unique())); print('Grok window dates:',sorted(Gw.alert_date.unique()))
print(pp.groupby('source').return_pct.agg(['count','mean','median']).round(2)); print(G.groupby('asset').return_pct.agg(['count','mean','median']).round(2))
