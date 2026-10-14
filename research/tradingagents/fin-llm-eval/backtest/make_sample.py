"""Stratified sample from the canonical point-in-time setups file (main sheet, not dup)."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import pandas as pd, numpy as np, yfinance as yf
d=pd.read_csv((_SCANNER_ROOT + '/tracker/setups-point-in-time-2026-10-08.csv'))
m=d[(d.in_main_sheet==True)&(d.dup_not_counted!=True)&d.cutoff_bar_date.notna()&d.direction.notna()].copy()
x=pd.read_excel((_SCANNER_ROOT + '/scan-tracker-2026-10-08.xlsx'),sheet_name='מעקב סריקות')
m['xl_idx']=(m.main_sheet_row-2).astype(int)
m['xl_ticker']=m.xl_idx.map(lambda i: x.iloc[i]['טיקר'])
assert (m.xl_ticker==m.ticker).mean()>0.99, (m.xl_ticker!=m.ticker).sum()
m['tracker_total_return']=m.xl_idx.map(lambda i: x.iloc[i]['סה"כ תשואה'])
m['scan_type']=m.xl_idx.map(lambda i: x.iloc[i]['סוג טרייד / סורק'])
# Perplexity task-list (ui_log) times are upper bounds: cap 70 min BEFORE logged time
spy=yf.Ticker('SPY').history(start='2026-07-01',end='2026-10-09'); tdays=sorted(spy.index.strftime('%Y-%m-%d'))
def adj_cutoff(r):
    c=r.cutoff_bar_date
    if r.platform.startswith('Perplexity') and r.time_source=='ui_log' and isinstance(r.alert_time_utc,str):
        t=pd.Timestamp(r.alert_time_utc)-pd.Timedelta(minutes=70)
        if r.market=='US':
            et=t.tz_convert('America/New_York'); day=et.strftime('%Y-%m-%d')
            cand=day if (day in tdays and et.hour>=16) else [d for d in tdays if d<day][-1]
        else:
            cand=(t.normalize()-pd.Timedelta(days=1)).strftime('%Y-%m-%d')  # last complete UTC daily bar
        c=min(c,cand)
    return c
m['trade_date']=m.apply(adj_cutoff,axis=1)
m['pplx_70min_changed']=m.trade_date!=m.cutoff_bar_date
m['win']=m.tracker_total_return>0
m['stratum']=m.model+np.where(m.model=='GROK automation',' '+m.automation.astype(str),'')+' | '+m.direction
m=m[m.tracker_total_return.notna()]
weights={}
for s in m.stratum.unique():
    weights[s]=2 if ('crypto' in s.lower() or 'prebreakout' in s) else 1
groups=sorted(m.stratum.unique())
queues={}
for g in groups:
    sub=m[m.stratum==g]
    w=sub[sub.win].sample(frac=1,random_state=1); l=sub[~sub.win].sample(frac=1,random_state=2)
    seq=[]
    for i in range(max(len(w),len(l))):
        if i<len(w): seq.append(w.iloc[i])
        if i<len(l): seq.append(l.iloc[i])
    queues[g]=seq
order=[]
while any(queues.values()):
    for g in groups:
        for _ in range(weights[g]):
            if queues[g]: order.append(queues[g].pop(0))
s=pd.DataFrame(order)
s['priority']=range(len(s))
s['asset']=np.where(s.market=='crypto 24/7','crypto','stock')
cols=['priority','stratum','setup_id','platform','model','automation','scan_type','ticker','asset','direction','alert_date','alert_time_utc','time_source','cutoff_bar_date','trade_date','pplx_70min_changed','cutoff_rule','data_asof_note','entry','tracker_total_return']
s[cols].to_csv((_SCANNER_ROOT + '/fin-llm-eval/backtest/sample_order.csv'),index=False)
print(len(s), 'changed by 70-min rule:', int(m.pplx_70min_changed.sum()))
h=s.head(48); print(h.stratum.value_counts().to_dict()); print(h.direction.value_counts().to_dict(), h.asset.value_counts().to_dict(), int(h.win.sum()))
print(h[['priority','ticker','model','automation','direction','trade_date','tracker_total_return']].to_string())
