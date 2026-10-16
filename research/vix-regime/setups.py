import pandas as pd,numpy as np,json
from scipy import stats
S=pd.read_csv('market_spread.csv',index_col=0,parse_dates=True)
for a,b in [('2000','2009'),('2010','2018'),('2019','2026')]:
    x=S[a:b]; print(a,b,'VIX>30 on-off %+.2f (n=%d)'%(x[x.vix>30].spread_on_minus_off.mean()*100,(x.vix>30).sum()),' VIX<16 off-on %+.2f'%(-x[x.vix<16].spread_on_minus_off.mean()*100), ' VIX<15 off-on %+.2f'%(-x[x.vix<15].spread_on_minus_off.mean()*100))
z=pd.read_pickle('close.pkl');z=z[z['^VIX'].notna()];v=z['^VIX']
M={'Technology':'XLK','Consumer Cyclical':'XLY','Communication Services':'XLC','Financial Services':'XLF','Industrials':'XLI','Energy':'XLE','Basic Materials':'XLB','Utilities':'XLU','Consumer Defensive':'XLP','Healthcare':'XLV','Real Estate':'XLRE'}
sm=json.load(open('/tmp/st/scanner-momentum-cache/sector_map.json'))
E=list(M.values())+['SMH','GLD','BTC-USD'];r=z[E].pct_change();dv=v.diff()
C=pd.DataFrame({e:r[e].rolling(250,min_periods=150).corr(dv) for e in E})
d=pd.read_csv('/tmp/st/scanner-tool-eval/setups_prepared.csv');d=d[d.in_main_sheet&~d.dup_not_counted.astype(bool)].copy()
d['etf']=[ 'BTC-USD' if a=='crypto' else ('GLD' if t in('GLD','GOLD') else M.get(sm.get(t)) ) for a,t in zip(d.asset,d.ticker)]
d['t']=pd.to_datetime(d.cutoff_bar_date)
def pit(row):
    c=C.loc[:row.t].iloc[-1]; return pd.Series({'vix':v[:row.t].iloc[-1],'vsma':v[:row.t].iloc[-20:].mean(),'corr':c.get(row.etf,np.nan),'med':c.median()})
d=pd.concat([d,d.apply(pit,axis=1)],axis=1)
d['riskon']=d['corr']<d['med']; d['L']=d.direction.eq('LONG')
y=d.x20; print('setups',len(d),'with sector',d['corr'].notna().sum(),'x20',y.notna().sum())
def cl(xcols,lab,sub):
    s=sub.dropna(subset=['x20']+xcols)
    X=np.column_stack([np.ones(len(s))]+[s[c].astype(float) for c in xcols]); Y=s.x20.values
    b=np.linalg.lstsq(X,Y,rcond=None)[0]; e=Y-X@b; g=s.alert_date.values; XtXi=np.linalg.inv(X.T@X)
    meat=sum(np.outer(X[g==k].T@e[g==k],X[g==k].T@e[g==k]) for k in np.unique(g)); V=XtXi@meat@XtXi
    G=len(np.unique(g)); t=b[1]/np.sqrt(V[1,1]); p=2*stats.t.sf(abs(t),G-1)
    print(f'{lab:55s} n={len(s)} dates={G} coef={b[1]*100:+.2f}pp p_incr={p:.3f}'); return p
d['dmom']=0.0
cs=z.columns
for i,rw in d.iterrows():
    if rw.asset=='stock' and rw.ticker in cs:
        p=z[rw.ticker][:rw.t].dropna()
        if len(p)>252: d.at[i,'dmom']=rw.dir_sign*(p.iloc[-22]/p.iloc[-253]-1)
d['crypto']=d.asset.eq('crypto').astype(float)
P={}
for th in (16,15):
    lo=d.vix<th
    d[f'ilan{th}']=np.where(lo&d.L,np.where(d.riskon,-1,1),0)   # favor defensive longs when VIX<th
    P[f'ilan_lo{th}']=cl([f'ilan{th}','dmom','crypto'],f'Ilan VIX<{th}: defensive long +1 / risk-on long -1',d)
    s=d[lo&d.L&d['corr'].notna()]; print('   longs VIX<%d: defensive x20 %+.2f%% (n=%d) vs risk-on %+.2f%% (n=%d)'%(th,s[~s.riskon].x20.mean()*100,(~s.riskon&s.x20.notna()).sum(),s[s.riskon].x20.mean()*100,(s.riskon&s.x20.notna()).sum()))
d['momv']=np.where(d.vix>d.vsma,1,-1)*np.where(d.riskon,-1,1)*d.dir_sign
P['momentum_cmp']=cl(['momv','dmom','crypto'],'momentum cmp (VIX>SMA20 riskoff)',d)
p=pd.Series(P);print('BH q',(p*len(p)/p.rank()).clip(upper=1).round(3).to_dict())
# walk-forward: halves by date
dd=sorted(d.alert_date.unique()); h=dd[len(dd)//2]
for nm,sub in (('1st half',d[d.alert_date<h]),('2nd half',d[d.alert_date>=h])): cl(['ilan16','dmom','crypto'],'WF '+nm+' ilan16',sub)
# stop tightening: risk-on stock longs VIX<16, close-ATR proxy, 20d, close-based stop
out=[]
for _,rw in d[(d.vix<16)&d.L&d.riskon&d.asset.eq('stock')].iterrows():
    if rw.ticker not in cs: continue
    p=z[rw.ticker].dropna(); pre=p[:rw.t]; post=p[p.index>rw.t].iloc[:20]
    if len(pre)<20 or len(post)<5: continue
    atr=pre.diff().abs().iloc[-14:].mean()*1.25; e=pre.iloc[-1]; res={}
    for k in (3,4):
        st=e-k*atr; hit=post[post<=st]; res[k]=(hit.iloc[0] if len(hit) else post.iloc[-1])/e-1
    out.append(res)
o=pd.DataFrame(out); print('stop 3x vs 4x ATR, risk-on longs VIX<16: n=%d mean 3x %+.2f%% 4x %+.2f%% diff %+.2f pp, p=%.3f'%(len(o),o[3].mean()*100,o[4].mean()*100,(o[3]-o[4]).mean()*100,stats.ttest_1samp(o[3]-o[4],0).pvalue))
d.to_csv('setups_regime.csv',index=False)
