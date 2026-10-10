"""Table M: ratchet / floor / tighten-after-profit chandelier variants (sim_ratchet.py) in % and R units."""
import numpy as np, pandas as pd
OUT='/workspace/trading-frameworks-eval/iaf/'
s=open(OUT+'analyze.py').read(); exec(s[:s.index('# ======================= REPORT')])
exec(s[s.index('def rulepass_long'):s.index('def table_policies')])
SE=pd.read_csv(OUT+'sim_trades_enriched.csv'); SE=SE[SE.in_main & ~SE.dup.astype(bool)]
kid=set(SE.setup_id)
for p in ['st_fib786_c','st_origin05_c','st_origin10_c','atr3_c','chand4_c','tg_ch_T1_c']: kid&=set(SE[SE.policy==p].setup_id)
RT=pd.read_csv(OUT+'sim_ratchet_trades.csv'); RT=RT[RT.setup_id.isin(kid)]
# hold baseline in R (R = 4xATR at entry, nominal)
Rinfo=RT[RT.policy=='rt_plain_c'][['setup_id','R_pct','mfe_R_end']]
H=pd.read_csv(OUT+'sim_trades.csv'); H=H[(H.policy=='hold')&H.setup_id.isin(kid)].merge(Rinfo,on='setup_id')
H['R_mult']=H.ret_net/(H.R_pct/100); H['mfe_R_held']=H.mfe_R_end; H['tightened']=False; H['policy']='hold'
X=pd.concat([RT,H],ignore_index=True); X=add_bench(X); X=X[X.in_main & ~X.dup.astype(bool)]
X['rules']=X.apply(lambda r: rulepass_long(r) if r.direction=='LONG' else rulepass_short(r),axis=1)
segs=[('Grok crypto LONG',lambda g:(g.group=='Grok crypto')&(g.direction=='LONG')),
      ('All stock LONG',lambda g:(g.asset=='stock')&(g.direction=='LONG')),
      ('Rule-filtered stock LONG',lambda g:(g.asset=='stock')&(g.direction=='LONG')&g.rules),
      ('Perplexity stock LONG',lambda g:(g.asset=='stock')&(g.direction=='LONG')&(g.source=='Perplexity')),
      ('Grok stock LONG',lambda g:(g.asset=='stock')&(g.direction=='LONG')&(g.source=='Grok')),
      ('Rule-filtered stock SHORT (score>=3 & <SMA200)',lambda g:(g.asset=='stock')&(g.direction=='SHORT')&g.rules),
      ('All stock SHORT',lambda g:(g.asset=='stock')&(g.direction=='SHORT'))]
VN={'fixed3':'fixed 3xATR (crypto live)','plain':'chandelier 4xATR, no ratchet','ratchet':'RATCHET chandelier 4xATR','floor':'chandelier 4xATR + floor at initial stop'}
for Xr in (2,3,4.5):
    for k2 in (2,3): VN[f'rat_t{Xr}_k{k2}']=f'ratchet + tighten to {k2}xATR after {Xr}R'
def pname(p):
    if p=='hold': return 'hold, no stop'
    b=p[3:-2]; h='_h618' in b; b=b.replace('_h618','')
    return VN[b]+(' + 1/2 at 1.618' if h else '')+(' (close)' if p.endswith('_c') else ' (intraday)')
def maxdd(r):
    eq=np.r_[0,np.cumsum(r)]; return float((np.maximum.accumulate(eq)-eq).max())
rows=[]
for nm,f in segs:
    g0=X[f(X)]
    for p in sorted(g0.policy.unique(), key=lambda p:(p!='hold', p.endswith('_i'), '_h618' in p, ['fixed3','plain','floor','ratchet'].index(p[3:-2].replace('_h618','')) if p!='hold' and p[3:-2].replace('_h618','') in ('fixed3','plain','floor','ratchet') else 9, p)):
        g=g0[g0.policy==p]
        b='btc' if (g.asset=='crypto').all() else 'spy'
        st=stats(g,b); seq=g.sort_values(['entry_date','setup_id']).R_mult.values
        st.update(segment=nm,policy=pname(p),code=p,exited=int((g.status!='open@end').sum()),open_=int((g.status=='open@end').sum()),
            stopped=(g.status=='stopped').mean()*100,x_mkt=st.get('x_'+b),x_mkt_wo_top1=st.get(f'x_{b}_wo_top1'),x_mkt_wo_top3=st.get(f'x_{b}_wo_top3'),
            mean_R=g.R_mult.mean(),med_R=g.R_mult.median(),avg_win_R=g.R_mult[g.R_mult>0].mean(),avg_loss_R=g.R_mult[g.R_mult<=0].mean(),
            maxDD_R=maxdd(seq),sum_R=g.R_mult.sum(),R_med_pct=g.R_pct.median(),
            reach2=(g.mfe_R_held>=2).mean()*100,reach3=(g.mfe_R_held>=3).mean()*100,reach45=(g.mfe_R_held>=4.5).mean()*100,
            ever45=(g.mfe_R_end>=4.5).mean()*100,tightened=g.tightened.mean()*100 if p!='hold' else np.nan,
            n_tight=int(g.tightened.sum()) if p!='hold' else 0,days=g.days.mean())
        rows.append(st)
MT=pd.DataFrame(rows)
cols=['segment','policy','N','exited','open_','stopped','mean','median','hit','x_mkt','mean_wo_top1','mean_wo_top3','x_mkt_wo_top1','x_mkt_wo_top3',
      'R_med_pct','mean_R','med_R','avg_win_R','avg_loss_R','maxDD_R','reach2','reach3','reach45','ever45','n_tight','days','flag']
MT[['code']+cols+['sum_R','tightened','top1','top3']].to_csv(OUT+'ratchet_table.csv',index=False)
def f2(df):
    out=['| '+' | '.join(cols)+' |','|'+'---|'*len(cols)]
    for _,r in df.iterrows():
        v=[]
        for c in cols:
            x=r[c]
            if c in ('N','exited','open_','n_tight'): v.append(f'{int(x)}')
            elif c in ('mean_R','med_R','avg_win_R','avg_loss_R','maxDD_R'): v.append('' if pd.isna(x) else f'{x:+.2f}' if c!='maxDD_R' else f'{x:.1f}')
            elif c in ('stopped','hit','reach2','reach3','reach45','ever45','days','R_med_pct'): v.append('' if pd.isna(x) else f'{x:.0f}' if c!='R_med_pct' else f'{x:.1f}')
            elif isinstance(x,(float,np.floating)): v.append('' if pd.isna(x) else f'{x:+.1f}')
            else: v.append(str(x))
        out.append('| '+' | '.join(v)+' |')
    return '\n'.join(out)
md='### M. Ratchet / floor / tighten-after-profit chandelier (stop_rules.ChandelierStop; same setups as K/L; R = 4xATR14 at entry except fixed 3xATR where R = 3xATR; hold uses nominal R = 4xATR; maxDD_R = max peak-to-trough of the cumulative R of the equal-weight trade sequence in signal (entry-date) order, same order for every policy; reachX = % of trades whose max favourable close while held reached X R; ever45 = % whose best close to 2026-10-07 reached 4.5R regardless of exit; n_tight = trades where the tighten rule fired)\n'+f2(MT)
open(OUT+'ratchet_table.md','w').write(md)
print(len(MT)); print(MT[['segment','code','N','exited','open_','mean','median','hit','x_mkt','x_mkt_wo_top3','mean_R','med_R','maxDD_R','reach2','reach3','reach45','ever45','n_tight']].round(2).to_string())
