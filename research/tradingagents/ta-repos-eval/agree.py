"""Agreement tables: TA-Lib candles vs scanner_geometry candles; smc objects vs scanner_geometry liquidity objects; Elliott repos vs our count;
coverage per repo and segment. Universe = the main-sheet, non-duplicate setups with an active-policy trade (same as the tests)."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
O='/workspace/ta-repos-eval/out/'; IAF='/workspace/trading-frameworks-eval/iaf/'
B=pd.read_pickle(O+'analysis_base.pkl'); GF=pd.read_pickle(IAF+'geo_features.pkl')
B=B.merge(GF[[c for c in GF.columns if c.startswith(('candle_','liq_','vp'))]+['setup_id']],on='setup_id',how='left',suffixes=('','_geo'))
def kappa(a,b):
    a=np.asarray(a,bool); b=np.asarray(b,bool); po=(a==b).mean(); pe=a.mean()*b.mean()+(1-a.mean())*(1-b.mean())
    return (po-pe)/(1-pe) if pe<1 else np.nan
out=[]
pairs=[('hammer','cdl_hammer',1),('inverted_hammer','cdl_invertedhammer',1),('bullish_engulfing','cdl_engulfing',1),('bearish_engulfing','cdl_engulfing',-1),
       ('bullish_harami','cdl_harami',1),('bearish_harami','cdl_harami',-1),('piercing','cdl_piercing',1),('dark_cloud','cdl_darkcloudcover',-1),
       ('morning_star','cdl_morningstar',1),('evening_star','cdl_eveningstar',-1),('three_white_soldiers','cdl_3whitesoldiers',1),('three_black_crows','cdl_3blackcrows',-1),
       ('hanging_man','cdl_hangingman',-1),('shooting_star','cdl_shootingstar',-1),('doji','cdl_doji',1),('dragonfly_doji','cdl_dragonflydoji',1),
       ('gravestone_doji','cdl_gravestonedoji',1),('spinning_top','cdl_spinningtop',0),('marubozu_bull','cdl_marubozu',1),('marubozu_bear','cdl_marubozu',-1)]
ok=B.ta_last_bar.notna()&B.candle_bias_last.notna()
for g,t,sgn in pairs:
    a=B.loc[ok,'candle_'+g].fillna(False).astype(bool); v=pd.to_numeric(B.loc[ok,t],errors='coerce').fillna(0)
    b=(v!=0) if sgn==0 else (v*sgn>0) if g not in ('doji','dragonfly_doji','gravestone_doji') else (v!=0)
    out.append(dict(pattern=g,talib=t,N=int(ok.sum()),geo_n=int(a.sum()),talib_n=int(b.sum()),both=int((a&b).sum()),
                    agree_pct=round(((a==b).mean())*100,1),jaccard=round((a&b).sum()/max(1,(a|b).sum()),2),kappa=round(kappa(a,b),2)))
CA=pd.DataFrame(out); CA.to_csv(O+'agree_candles.csv',index=False); print(CA.to_string())
# smc vs scanner_geometry objects (direction-free: above / below the last close)
sm=[]
C=pd.to_numeric(B._C,errors='coerce'); A=pd.to_numeric(B._A,errors='coerce')
def cmp_(name,a,b,da=None,db=None):
    a=a.astype(bool); b=b.astype(bool); d=dict(object=name,N=len(a),smc_pct=round(a.mean()*100,1),geo_pct=round(b.mean()*100,1),agree_pct=round((a==b).mean()*100,1),kappa=round(kappa(a,b),2))
    if da is not None:
        m=da.notna()&db.notna(); d['n_both']=int(m.sum()); d['spearman_dist']=round(da[m].corr(db[m],method='spearman'),2) if m.sum()>10 else np.nan
        d['median_dist_smc_atr']=round(da[m].median(),2); d['median_dist_geo_atr']=round(db[m].median(),2)
    sm.append(d)
okg=B.smc_last_bar.notna()&B.geo_last_bar.notna() if 'geo_last_bar' in B.columns else B.smc_last_bar.notna()
X=B[okg]; C=C[okg]; A=A[okg]
fa=pd.to_numeric(X._fvg_above_lo,errors='coerce'); fb=pd.to_numeric(X._fvg_below_hi,errors='coerce')
ga=pd.to_numeric(X.liq_fvg_above_lo,errors='coerce'); gb=pd.to_numeric(X.liq_fvg_below_hi,errors='coerce')
cmp_('open FVG above price',fa.notna(),ga.notna(),(fa-C)/A,(ga-C)/A); cmp_('open FVG below price',fb.notna(),gb.notna(),(C-fb)/A,(C-gb)/A)
oa=pd.to_numeric(X._ob_above_lo,errors='coerce'); ob=pd.to_numeric(X._ob_below_hi,errors='coerce')
goa=pd.to_numeric(X.liq_ob_above_lo,errors='coerce'); gob=pd.to_numeric(X.liq_ob_below_hi,errors='coerce')
cmp_('active order block above',oa.notna(),goa.notna(),(oa-C)/A,(goa-C)/A); cmp_('active order block below',ob.notna(),gob.notna(),(C-ob)/A,(C-gob)/A)
la=X._liq_above.map(lambda v: min(v) if isinstance(v,list) and v else np.nan); lb=X._liq_below.map(lambda v: max(v) if isinstance(v,list) and v else np.nan)
gla=pd.to_numeric(X.liq_bsl_dist_atr,errors='coerce') if 'liq_bsl_dist_atr' in X else None; glb=pd.to_numeric(X.liq_ssl_dist_atr,errors='coerce') if 'liq_ssl_dist_atr' in X else None
gle=X.liq_bsl_equal.fillna(False).astype(bool) if 'liq_bsl_equal' in X else None; gse=X.liq_ssl_equal.fillna(False).astype(bool) if 'liq_ssl_equal' in X else None
# smc liquidity = >=2 swings within 1% of range -> compare with geo 'equal highs/lows' pool (>=2 touches) nearest
cmp_('liquidity (>=2 equal swing highs) above',la.notna(),gle,(la-C)/A,gla.abs().where(gle))
cmp_('liquidity (>=2 equal swing lows) below',lb.notna(),gse,(C-lb)/A,glb.abs().where(gse))
SA=pd.DataFrame(sm); SA.to_csv(O+'agree_smc_geo.csv',index=False); print(SA.to_string())
# Elliott: coverage per repo x segment and agreement with our count
segs={'All stock LONG':(B.asset=='stock')&(B.direction=='LONG'),'Rule-filtered stock LONG':(B.asset=='stock')&(B.direction=='LONG')&B.rules,
      'All stock SHORT':(B.asset=='stock')&(B.direction=='SHORT'),'Crypto LONG':(B.asset=='crypto')&(B.direction=='LONG')}
oe=B.ours_ew.fillna('none').map({'wave3':'w3','wave5':'w5','wave3_passed':'passed','wave5_passed':'passed','none':'none'}).fillna('none')
cov=[]
for seg,m in segs.items():
    d=dict(segment=seg,N=int(m.sum()))
    for lib in ('taew','ewa','ar'):
        st=B.loc[m,lib+'_state']; d[f'{lib}_any%']=round((st!='none').mean()*100,1)
        for s_ in ('w3','w5','done','abc_done','impulse_seen'):
            if (st==s_).any(): d[f'{lib}_{s_}%']=round((st==s_).mean()*100,1)
    d['ours_any%']=round((oe[m]!='none').mean()*100,1); d['ours_w3%']=round((oe[m]=='w3').mean()*100,1); d['ours_w5%']=round((oe[m]=='w5').mean()*100,1)
    cov.append(d)
CV=pd.DataFrame(cov); CV.to_csv(O+'ew_coverage.csv',index=False); print(CV.T.to_string())
ag=[]
for lib in ('taew','ewa'):
    st=B[lib+'_state'].fillna('none')
    for s_ in ('w3','w5'):
        a=st==s_; b=oe==s_
        ag.append(dict(repo=lib,state=s_,repo_n=int(a.sum()),ours_n=int(b.sum()),both=int((a&b).sum()),kappa=round(kappa(a,b),2),
                       pct_of_repo_also_ours=round((a&b).sum()/max(1,a.sum())*100,1)))
    both=(st.isin(['w3','w5']))&(oe.isin(['w3','w5'])); ag.append(dict(repo=lib,state='same wave label when both count',repo_n=int(both.sum()),both=int((st[both]==oe[both]).sum()),pct_of_repo_also_ours=round((st[both]==oe[both]).mean()*100,1)))
a=B.taew_state.fillna('none'); b=B.ewa_state.fillna('none')
for s_ in ('w3','w5'): ag.append(dict(repo='taew vs ewa',state=s_,repo_n=int((a==s_).sum()),ours_n=int((b==s_).sum()),both=int(((a==s_)&(b==s_)).sum()),kappa=round(kappa(a==s_,b==s_),2)))
AG=pd.DataFrame(ag); AG.to_csv(O+'ew_agreement.csv',index=False); print(AG.to_string())
print(pd.crosstab(B.taew_state.fillna('none'),oe)); print(pd.crosstab(B.ewa_state.fillna('none'),oe))
