import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import pandas as pd, numpy as np
OUT=(_SCANNER_ROOT + '/trading-frameworks-eval/iaf/')
R=pd.read_csv(OUT+'sim_minute_trades.csv'); S=pd.read_csv(OUT+'sim_trades_enriched.csv',low_memory=False)
S=S[S.in_main.astype(bool) & ~S.dup.astype(bool)]
meta=S[S.policy=='hold'][['setup_id','ticker','group','source','asset','direction','entry_date']].rename(columns={'entry_date':'d_entry_date'})
m=R.merge(meta,on=['setup_id','asset','direction'])
m=m.merge(S[['setup_id','policy','ret_net','x_spy','x_btc','x_basket']].rename(columns={'ret_net':'d_ret','x_spy':'d_x_spy','x_btc':'d_x_btc','x_basket':'d_x_basket'}),on=['setup_id','policy'])
m['moved']=pd.to_datetime(m.entry_date)!=pd.to_datetime(m.d_entry_date)
m['intraday']=~m.entry_minute.str.contains('T13:30:00') if True else None
m.loc[m.asset=='crypto','intraday']=True
def st(g,col,xcol):
    r=g[col]*100; x=g[xcol]*100
    contrib=g.groupby('ticker')[xcol].sum().sort_values(ascending=False)
    h=g[~g.ticker.isin(contrib.index[:1])]
    return f"{r.mean():+.1f} / {r.median():+.1f} / {(r>0).mean()*100:.0f}% / {x.mean():+.1f} (w/o top1 {h[xcol].mean()*100:+.1f})"
rows=[]
for p in ('hold','t8','fsetup'):
    for (src,a,d),g in m[m.policy==p].groupby(['source','asset','direction']):
        b='spy' if a=='stock' else 'btc'
        for lab,gg in (('all timed',g),('entry changed',g[g.intraday])):
            if len(gg)<3: continue
            rows.append(dict(policy=p,source=src,asset=a,dir=d,subset=lab,N=len(gg),
                daily=st(gg,'d_ret','d_x_'+b), minute=st(gg,'ret_net','x_'+b),
                d_mean=(gg.ret_net-gg.d_ret).mean()*100, d_med=(gg.ret_net-gg.d_ret).median()*100))
T=pd.DataFrame(rows)
hdr='| policy | source | asset | dir | subset | N | DAILY-cutoff mean / median / hit / x_mkt (w/o top1) | EXACT-MINUTE mean / median / hit / x_mkt (w/o top1) | Δmean pp | Δmedian pp |\n|---|---|---|---|---|---|---|---|---|---|\n'
md=hdr+'\n'.join(f"| {r.policy} | {r.source} | {r.asset} | {r.dir} | {r.subset} | {r.N} | {r.daily} | {r.minute} | {r.d_mean:+.2f} | {r.d_med:+.2f} |" for r in T.itertuples())
cov=f"Timed setups (exact/schedule/ui_log) in main non-dup population with a minute entry: {m[m.policy=='hold'].shape[0]}; of which entry moved vs daily version: stocks {int(m[(m.policy=='hold')&(m.asset=='stock')].intraday.sum())}, crypto {int(m[(m.policy=='hold')&(m.asset=='crypto')].shape[0])} (all crypto timed entries move from next 00:00 UTC to the alert minute)."
open(OUT+'minute_vs_daily.md','w').write(cov+'\n\n'+md); print(cov); print(md)
