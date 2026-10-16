# LOCKED before running: VIX_HI=30, VIX_LO=16 (sens 15), turn-down = VIX>30 within last 5d max and VIX <= 0.9*max5; horizon 20d;
# PIT class: 250d rolling corr(ETF ret, dVIX) up to t; risk-on = lowest third, risk-off = highest third at t. Clusters = episodes.
import pandas as pd,numpy as np
z=pd.read_pickle('long.pkl');v=z.pop('^VIX');spy=z.pop('SPY');E=[c for c in z.columns]
r=z.pct_change();dv=v.diff()
C=r.rolling(250,min_periods=200).corr(dv) if False else pd.DataFrame({e:r[e].rolling(250,min_periods=200).corr(dv) for e in E})
H=20;fwd=z.shift(-H)/z-1
def spread(t):
    c=C.loc[t].dropna(); f=fwd.loc[t]
    if len(c)<6: return np.nan
    k=len(c)//3; on=c.nsmallest(k).index; off=c.nlargest(k).index
    return f[on].mean()-f[off].mean()     # risk-on minus risk-off
S=pd.Series({t:spread(t) for t in z.index[260:-H]})
vv=v.loc[S.index]; m5=v.rolling(5).max().loc[S.index]
def ep(mask):  # episode id: consecutive-ish days (gap<=10 trading days) of the mask
    idx=np.where(mask.values)[0]; e=np.full(len(mask),-1); k=-1; last=-99
    for i in idx:
        if i-last>10: k+=1
        e[i]=k; last=i
    return pd.Series(e,index=mask.index)
rng=np.random.default_rng(0)
def test(mask,name,sign=1):
    x=S[mask]*sign; e=ep(mask)[mask]; g=x.groupby(e).mean(); n=len(g)
    bs=[g.sample(n,replace=True,random_state=int(rng.integers(1e9))).mean() for _ in range(4000)]
    p=2*min(np.mean(np.array(bs)<=0),np.mean(np.array(bs)>=0))
    yrs={y:round(x[x.index.year==y].mean()*100,2) for y in (2008,2020,2022) if (x.index.year==y).any()}
    print(f"{name:45s} days={mask.sum():5d} episodes={n:3d} mean_ep={g.mean()*100:+.2f}% hit_ep={(g>0).mean():.0%} CI95=[{np.percentile(bs,2.5)*100:+.2f},{np.percentile(bs,97.5)*100:+.2f}] p_boot={p:.3f} {yrs}")
    return p
P={}
first=(vv>30)&(v.shift(1).loc[S.index]<=30)
P['hi_any']=test(vv>30,'VIX>30 any day: riskON-riskOFF fwd20')
P['hi_first']=test(first,'VIX>30 first cross')
P['hi_turn']=test((m5>30)&(vv<=0.9*m5),'VIX>30 peak & turned down >=10%')
P['lo16']=test(vv<16,'VIX<16: riskOFF-riskON fwd20',-1)
P['lo15']=test(vv<15,'VIX<15 (sens): riskOFF-riskON',-1)
P['mom_cmp']=test(vv>v.rolling(20).mean().loc[S.index],'momentum cmp: VIX>SMA20 -> riskOFF-riskON',-1)
p=pd.Series(P).sort_values(); q=(p*len(p)/np.arange(1,len(p)+1))[::-1].cummin()[::-1]; print('BH q:',q.round(3).to_dict())
pd.DataFrame({'spread_on_minus_off':S,'vix':vv}).to_csv('market_spread.csv')
# 19.20 marker (pre-registered by Ilan 16.10)
pv=v.shift(1).loc[S.index]
P2={}
P2['up1920']=test((vv>19.2)&(pv<=19.2),'cross UP 19.20: riskOFF-riskON fwd20',-1)
P2['dn1920']=test((vv<19.2)&(pv>=19.2),'cross DOWN 19.20: riskON-riskOFF fwd20')
P2['above1920']=test(vv>19.2,'VIX>19.20 state: riskOFF-riskON',-1)
p=pd.Series(P2).sort_values(); print('BH q (19.20 family):',(p*len(p)/np.arange(1,len(p)+1))[::-1].cummin()[::-1].round(3).to_dict())
p2=v.shift(2).loc[S.index]
P3={}
P3['up2']=test((vv>19.2)&(pv>19.2)&(p2<=19.2),'2-close UP 19.20: riskOFF-riskON',-1)
P3['dn2']=test((vv<19.2)&(pv<19.2)&(p2>=19.2),'2-close DOWN 19.20: riskON-riskOFF')
vf=v.loc[S.index]
def whip(mask,up):
    idx=np.where(mask.values)[0]; w=0
    for i in idx:
        nxt=vf.iloc[i+1:i+6]; w+= (nxt<19.2).any() if up else (nxt>19.2).any()
    return len(idx),w
for nm,m,u in [('1-close up',(vv>19.2)&(pv<=19.2),1),('2-close up',(vv>19.2)&(pv>19.2)&(p2<=19.2),1),('1-close down',(vv<19.2)&(pv>=19.2),0),('2-close down',(vv<19.2)&(pv<19.2)&(p2>=19.2),0)]:
    n,w=whip(m,u); print(f'{nm}: signals={n} whipsaw(reverse within 5d)={w} ({w/n:.0%})')
