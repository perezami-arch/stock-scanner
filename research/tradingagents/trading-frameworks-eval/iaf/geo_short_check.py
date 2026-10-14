"""Descriptive follow-up (not in the BH family): do the two short-side survivors add anything to the existing short rule?"""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import numpy as np, pandas as pd
OUT=(_SCANNER_ROOT + '/trading-frameworks-eval/iaf/')
s=open(OUT+'analyze.py').read(); exec(s[:s.index('# ======================= REPORT')]); exec(s[s.index('def rulepass_long'):s.index('def table_policies')])
T=add_bench(pd.read_csv(OUT+'sim_geo_trades.csv')); T=T[T.in_main&~T.dup.astype(bool)&(T.policy=='base_c')&(T.asset=='stock')&(T.direction=='SHORT')]
T=T.merge(pd.read_pickle(OUT+'geo_features.pkl'),on='setup_id'); T['rules']=T.apply(rulepass_short,axis=1)
T['belowVA120']=T.vp120_va_pos=='below VA'; T['fwd_pools']=T.liq_ssl_pools_n.fillna(0)
T['fewpools']=T.fwd_pools<=T.fwd_pools.quantile(0.2)
f=lambda g: f"N={len(g):3d} mean={g.ret_net.mean()*100:+.1f} med={g.ret_net.median()*100:+.1f} xSPY={g.x_spy.mean()*100:+.1f} hit={(g.ret_net>0).mean()*100:.0f} tickers={g.ticker.nunique()} dates={g.entry_date.nunique()}"
print('fwd pools quintile cut:',T.fwd_pools.quantile(0.2))
for lab,m in [('all shorts',T.index==T.index),('rule-filtered (score>=3 & <SMA200)',T.rules),('below VA120',T.belowVA120),('below VA120 & rule',T.belowVA120&T.rules),
              ('below VA120 & NOT rule',T.belowVA120&~T.rules),('rule & NOT below VA120',T.rules&~T.belowVA120),('few fwd pools (Q1)',T.fewpools),('few pools & rule',T.fewpools&T.rules),('rule & not few pools',T.rules&~T.fewpools)]:
    print(f'{lab:40s}',f(T[m]))
print(pd.crosstab(T.rules,T.belowVA120)); print(T[T.belowVA120].groupby('source').size()); print(T[T.belowVA120].entry_date.value_counts().head())
