"""Descriptive follow-up (NOT in the FDR family): do the two short-side survivors add anything to the §3.14 lead (close below the
120-day value area) and to the existing short rule?"""
import numpy as np, pandas as pd, statsmodels.api as sm, warnings; warnings.filterwarnings('ignore')
O='out/'; B=pd.read_pickle(O+'analysis_base.pkl'); GF=pd.read_pickle('/workspace/trading-frameworks-eval/iaf/geo_features.pkl')[['setup_id','vp120_va_pos']]
X=B[(B.asset=='stock')&(B.direction=='SHORT')].merge(GF,on='setup_id',how='left')
X['crsi_al']=-(X.pta_crsi-50); X['sma200_al']=-X.dist_sma200_atr
X['crsi_q5']=X.crsi_al>=X.crsi_al.quantile(0.8); X['sma200_q5']=X.sma200_al>=X.sma200_al.quantile(0.8); X['va']=X.vp120_va_pos=='below VA'
print('N shorts',len(X),' rule-pass',int(X.rules.sum()))
print(pd.crosstab(X.crsi_q5,X.va,margins=True)); print(pd.crosstab(X.sma200_q5,X.va,margins=True)); print(pd.crosstab(X.crsi_q5,X.rules,margins=True)); print(pd.crosstab(X.sma200_q5,X.rules,margins=True))
for nm in ('crsi_q5','sma200_q5','va'):
    for lab,g in (('all shorts',X),('rule-pass shorts',X[X.rules])):
        a=g[g[nm]]; b=g[~g[nm]]
        print(f'{lab:17s} {nm:9s} with N={len(a):3d} x={a.x_mkt.mean()*100:+.1f} hit={(a.ret_net>0).mean()*100:.0f}% dates={a.entry_date.nunique()} | without N={len(b):3d} x={b.x_mkt.mean()*100:+.1f}')
def ols(y,cols,g):
    Xm=sm.add_constant(g[cols].astype(float)); m=sm.OLS(g[y].astype(float),Xm).fit(cov_type='cluster',cov_kwds={'groups':pd.factorize(g.entry_date)[0]}); return m.params.round(4).to_dict(),m.pvalues.round(4).to_dict()
print('x_mkt ~ va + crsi_q5 (all shorts, date-clustered):',ols('x_mkt',['va','crsi_q5'],X))
print('x_mkt ~ va + sma200_q5:',ols('x_mkt',['va','sma200_q5'],X))
print('x_mkt ~ va + crsi_q5 (rule-pass):',ols('x_mkt',['va','crsi_q5'],X[X.rules]))
