"""Filter + level tests for TA-Lib / pandas-ta / smartmoneyconcepts / Elliott repos, ONE Benjamini-Hochberg family over every executed
comparison, robustness checks — statistics copied from iaf/geo_analyze.py (§3.14) so results are directly comparable.
Outcome = active-policy trade (sim_levels base_c == sim_geo base_c == sim_ratchet policy rows), x_mkt = excess vs SPY (stocks) / BTC (crypto)."""
import sys, numpy as np, pandas as pd, warnings
import statsmodels.api as sm
warnings.filterwarnings('ignore')
IAF='/workspace/trading-frameworks-eval/iaf/'; O='/workspace/ta-repos-eval/out/'
OUT=IAF
s=open(IAF+'analyze.py').read(); exec(s[:s.index('# ======================= REPORT')])
exec(s[s.index('def rulepass_long'):s.index('def table_policies')])
g_=open(IAF+'geo_analyze.py').read(); exec(g_[g_.index('def _fit'):g_.index('B=B.merge(D[')])
GT=pd.read_csv(O+'sim_levels_trades.csv')
T=add_bench(GT); T=T[T.in_main & ~T.dup.astype(bool)].copy()
T['x_mkt']=np.where(T.asset=='crypto',T.x_btc,T.x_spy)
T['rules']=T.apply(lambda r: rulepass_long(r) if r.direction=='LONG' else rulepass_short(r),axis=1)
SEGS=[('All stock LONG',lambda g:(g.asset=='stock')&(g.direction=='LONG')),
      ('Rule-filtered stock LONG',lambda g:(g.asset=='stock')&(g.direction=='LONG')&g.rules),
      ('Perplexity stock LONG',lambda g:(g.asset=='stock')&(g.direction=='LONG')&(g.source=='Perplexity')),
      ('Grok stock LONG',lambda g:(g.asset=='stock')&(g.direction=='LONG')&(g.source=='Grok')),
      ('All stock SHORT',lambda g:(g.asset=='stock')&(g.direction=='SHORT')),
      ('Crypto LONG',lambda g:(g.asset=='crypto')&(g.direction=='LONG'))]
TA=pd.read_pickle(O+'ta_features.pkl'); SM=pd.read_pickle(O+'smc_features.pkl'); EWF=pd.read_pickle(O+'ew_features.pkl')
MOM=pd.read_csv('/workspace/scanner-tool-eval/forecasts/mom121.csv')[['setup_id','f20']].rename(columns={'f20':'mom121'})
OURS=pd.read_csv(IAF+'elliott_coverage.csv')[['setup_id','ew']].rename(columns={'ew':'ours_ew'})
B=T[T.policy=='base_c'].merge(TA,on='setup_id',how='left').merge(SM,on='setup_id',how='left').merge(EWF,on='setup_id',how='left').merge(MOM,on='setup_id',how='left').merge(OURS,on='setup_id',how='left')
B=B.merge(D[['setup_id','vs_sma200']],on='setup_id',how='left')
sg=np.where(B.direction=='LONG',1,-1); L_=sg==1
def num(c): return pd.to_numeric(B[c],errors='coerce')
def S_(a): return pd.Series(a,index=B.index)
FB={}; FC={}; FAM={}
def addb(n,v,fam): FB[n]=v; FAM[n]=fam
def addc(n,v,fam): FC[n]=v; FAM[n]=fam
ok=B.ta_last_bar.notna()
# ---- reference: momentum 12-1 (PIT, scanner-tool-eval)
addc('mom12-1 (aligned: -mom for shorts)',num('mom121')*sg,'reference')
# ---- TA-Lib indicators (aligned so + = with the trade where a direction exists)
for n,v in {'rsi14':(num('rsi14')-50)*sg,'macd_hist_atr':num('macdh_atr')*sg,'macd_line_atr':num('macd_atr')*sg,'adx14':num('adx14'),'di_spread':num('di_spread')*sg,
            'cci20':num('cci20')*sg,'mfi14':(num('mfi14')-50)*sg,'stoch_k':(num('stoch_k')-50)*sg,'willr14':(num('willr14')+50)*sg,'ultosc':(num('ultosc')-50)*sg,
            'roc10':num('roc10')*sg,'roc20':num('roc20')*sg,'bb_pctb':(num('bb_pctb')-0.5)*sg,'bb_width':num('bb_width'),'natr14':num('natr14'),
            'dist_sma50_atr':num('dist_sma50_atr')*sg,'dist_sma200_atr':num('dist_sma200_atr')*sg,'aroonosc14':num('aroonosc14')*sg,
            'obv_slope20_z':num('obv_slope20_z')*sg,'linreg_slope20_atr':num('linreg_slope20_atr')*sg}.items():
    addc('talib '+n+(' (aligned)' if n not in ('adx14','bb_width','natr14') else ''),v,'talib_ind')
addb('talib macd_hist_with_trade',(num('macdh_atr')*sg>0).where(ok),'talib_ind')
addb('talib macd_cross_with_trade_3bars',S_(np.where(L_,B.macd_cross_up_3==True,B.macd_cross_dn_3==True)).where(ok),'talib_ind')
addb('talib sma50_vs_sma200_with_trade',S_(np.where(L_,B.sma50_gt_sma200==True,B.sma50_gt_sma200==False)).where(B.sma50_gt_sma200.notna()),'talib_ind')
addb('talib sar_with_trade',S_(np.where(L_,B.close_above_sar==True,B.close_above_sar==False)).where(ok),'talib_ind')
addb('talib ht_trendmode (trend vs cycle)',(B.ht_trendmode==True).where(ok),'talib_ind')
addb('talib rsi_overbought_with_trade (>70 long / <30 short)',S_(np.where(L_,num('rsi14')>70,num('rsi14')<30)).where(ok),'talib_ind')
addb('talib rsi_oversold_against (<30 long / >70 short)',S_(np.where(L_,num('rsi14')<30,num('rsi14')>70)).where(ok),'talib_ind')
# ---- TA-Lib candles (all 61, last bar), aligned / against + aggregates
cdl=[c for c in B.columns if c.startswith('cdl_')]
V=pd.DataFrame({c:num(c) for c in cdl})
for c in cdl:
    addb(f'talib {c} with trade',(V[c]*sg>0).where(ok),'talib_cdl'); addb(f'talib {c} against trade',(V[c]*sg<0).where(ok),'talib_cdl')
net=np.sign(V).sum(axis=1)*sg
addb('talib cdl_any_with_trade',((np.sign(V).mul(sg,axis=0)>0).any(axis=1)).where(ok),'talib_cdl')
addb('talib cdl_any_against_trade',((np.sign(V).mul(sg,axis=0)<0).any(axis=1)).where(ok),'talib_cdl')
addb('talib cdl_net_with_trade (net signal > 0)',(net>0).where(ok),'talib_cdl'); addb('talib cdl_net_against_trade (net < 0)',(net<0).where(ok),'talib_cdl')
# ---- pandas-ta only indicators
okp=B.pta_chop14.notna()
addb('pandas-ta supertrend_with_trade',(num('pta_supertrend_dir')*sg>0).where(okp),'pandas_ta')
addb('pandas-ta squeeze_on (BB inside KC)',(B.pta_sqz_on==True).where(okp),'pandas_ta')
addc('pandas-ta squeeze_mom_atr (aligned)',num('pta_sqz_mom_atr')*sg,'pandas_ta')
addc('pandas-ta chop14',num('pta_chop14'),'pandas_ta')
addc('pandas-ta vortex_diff (aligned)',num('pta_vortex_diff')*sg,'pandas_ta')
addc('pandas-ta stc (aligned)',(num('pta_stc')-50)*sg,'pandas_ta')
addb('pandas-ta ichimoku_beyond_cloud_with_trade',(num('pta_ichi_pos')*sg>0).where(B.pta_ichi_pos.notna()),'pandas_ta')
addb('pandas-ta ichimoku_inside_cloud',(num('pta_ichi_pos')==0).where(B.pta_ichi_pos.notna()),'pandas_ta')
addc('pandas-ta connors_rsi (aligned)',(num('pta_crsi')-50)*sg,'pandas_ta')
ex_w=S_(np.where(L_,num('pta_exhc_up'),num('pta_exhc_dn'))); ex_a=S_(np.where(L_,num('pta_exhc_dn'),num('pta_exhc_up')))
addb('pandas-ta exhaustion_count>=5_with_trade',(ex_w>=5).where(okp),'pandas_ta'); addb('pandas-ta exhaustion_count>=5_against',(ex_a>=5).where(okp),'pandas_ta')
# ---- smartmoneyconcepts (PIT wrapper)
oks=B.smc_last_bar.notna(); A_=num('_A'); C_=num('_C')
addb('smc last_BOS/CHoCH_with_trade',(num('smc_last_break_dir')*sg>0).where(B.smc_last_break_dir.notna()),'smc')
addb('smc last_break_is_CHoCH_with_trade',((B.smc_last_break_kind=='choch')&(num('smc_last_break_dir')*sg>0)).where(B.smc_last_break_dir.notna()),'smc')
addb('smc last_break_is_CHoCH_against',((B.smc_last_break_kind=='choch')&(num('smc_last_break_dir')*sg<0)).where(B.smc_last_break_dir.notna()),'smc')
addc('smc bars_since_last_break',num('smc_bars_since_break'),'smc')
addb('smc net_breaks_last20_with_trade',(num('smc_breaks_last20_net')*sg>0).where(oks),'smc')
addc('smc fvg_open_n',num('smc_fvg_open_n'),'smc'); addc('smc ob_open_n',num('smc_ob_open_n'),'smc')
fa=num('_fvg_above_lo'); fb=num('_fvg_below_hi')
fwd_f=S_(np.where(L_,fa,fb)); back_f=S_(np.where(L_,fb,fa))
addb('smc fwd_open_FVG_exists (target side)',fwd_f.notna().where(oks),'smc'); addb('smc back_open_FVG_exists (stop side)',back_f.notna().where(oks),'smc')
addc('smc fwd_FVG_dist_atr',(fwd_f-C_).abs()/A_,'smc'); addc('smc back_FVG_dist_atr',(back_f-C_).abs()/A_,'smc')
obb=num('_ob_below_hi'); oba=num('_ob_above_lo')
back_o=S_(np.where(L_,obb,oba)); fwd_o=S_(np.where(L_,oba,obb))
addb('smc back_active_OB_exists (bull OB below long)',back_o.notna().where(oks),'smc'); addb('smc fwd_active_OB_exists',fwd_o.notna().where(oks),'smc')
addc('smc back_OB_dist_atr',(back_o-C_).abs()/A_,'smc'); addc('smc back_OB_strength',S_(np.where(L_,num('smc_ob_strength_below'),num('smc_ob_strength_above'))),'smc')
la=B._liq_above.map(lambda v: min(v) if isinstance(v,list) and v else np.nan); lb=B._liq_below.map(lambda v: max(v) if isinstance(v,list) and v else np.nan)
fwd_l=S_(np.where(L_,la,lb)); back_l=S_(np.where(L_,lb,la))
addb('smc fwd_unswept_liquidity_exists',fwd_l.notna().where(oks),'smc'); addb('smc back_unswept_liquidity_exists',back_l.notna().where(oks),'smc')
addb('smc sweep_last3_with_trade (sell-side swept for long)',S_(np.where(L_,B.smc_swept_last3_ssl==True,B.smc_swept_last3_bsl==True)).where(oks),'smc')
addb('smc sweep_last3_against',S_(np.where(L_,B.smc_swept_last3_bsl==True,B.smc_swept_last3_ssl==True)).where(oks),'smc')
addb('smc retracement_leg_with_trade',(num('smc_ret_dir')*sg>0).where(B.smc_ret_dir.notna()),'smc')
addc('smc current_retracement_pct',num('smc_ret_current'),'smc'); addc('smc deepest_retracement_pct',num('smc_ret_deepest'),'smc')
# ---- Elliott repos + our own count
for lib,lab in (('taew','python-taew'),('ewa','ElliottWaveAnalyzer')):
    st=B[lib+'_state']; o=st.notna()
    addb(f'{lab}: in wave 3',(st=='w3').where(o),'ew_'+lib); addb(f'{lab}: in wave 5',(st=='w5').where(o),'ew_'+lib)
    addb(f'{lab}: impulse just completed',(st=='done').where(o),'ew_'+lib); addb(f'{lab}: any valid count',(st!='none').where(o),'ew_'+lib)
st=B['ar_state']; o=st.notna()
addb('ElliottWaves: impulse+ABC completed',(st=='abc_done').where(o),'ew_ar'); addb('ElliottWaves: impulse seen (no ABC yet)',(st=='impulse_seen').where(o),'ew_ar')
addb('ElliottWaves: any valid count',(st!='none').where(o),'ew_ar')
oe=B.ours_ew.fillna('none')
addb('OUR count (sim_fib zigzag): in wave 3 (target ahead)',S_(oe=='wave3'),'ew_ours'); addb('OUR count: in wave 5 (target ahead)',S_(oe=='wave5'),'ew_ours')
addb('OUR count: any count',S_(oe!='none'),'ew_ours')
# ------------------------------------------------------------------ tests (same as geo_analyze, plus a momentum control)
def incr_mom(g,v):
    m=g['mom_al'].astype(float); ok_=m.notna().values
    if ok_.sum()<2*MIN: return (np.nan,np.nan)
    return cl_test(g.x_mkt.values[ok_],np.asarray(v,float)[ok_],g.ticker.values[ok_],g.entry_date.values[ok_],ctrl=m.values[ok_].reshape(-1,1))
B['mom_al']=num('mom121')*sg
rows=[]; skipped=0; MIN=20
for seg,f in SEGS:
    m=f(B).values; g0=B[m]
    feats=[(n,'bool',FB[n][m]) for n in FB]
    for n,v in FC.items():
        v=v[m]; ok_=v.notna()
        if ok_.sum()<2*MIN or v[ok_].nunique()<5: skipped+=3; continue
        q=pd.qcut(v[ok_].rank(method='first'),5,labels=False)
        q1=pd.Series(np.nan,index=v.index); q1[ok_]=(q==0).astype(float); q5=pd.Series(np.nan,index=v.index); q5[ok_]=(q==4).astype(float)
        feats+=[(n+' : Q1 (lowest 20%) vs rest','q1',q1),(n+' : Q5 (highest 20%) vs rest','q5',q5),(n+' : rank slope (Q5-Q1 equiv.)','rank',v)]
    for n,kind_,v in feats:
        base_n=n.split(' : ')[0]; fam_=FAM[base_n]
        ok_=v.notna(); g=g0[ok_.values]; vv=v[ok_]
        if kind_=='rank':
            if len(g)<2*MIN: skipped+=1; continue
            rk=vv.rank(pct=True).values
            b_,p=cl_test(g.x_mkt.values,rk,g.ticker.values,g.entry_date.values); _,p_tk=cl_test(g.x_mkt.values,rk,g.ticker.values)
            braw,_=cl_test(g.ret_net.values,rk,g.ticker.values)
            hi=rk>=0.8; lo=rk<=0.2; med=g.x_mkt[hi].median()-g.x_mkt[lo].median()
            ind=pd.Series(rk>=0.5,index=g.index); dt=drop_top_diff(g,ind,'x_mkt',np.sign(b_) if np.isfinite(b_) else 1)
            wd,h1,h2=extra_checks(g,ind); pi=incr(g,pd.Series(rk,index=g.index),seg); pm=incr_mom(g,rk)
            rows.append(dict(kind='filter',family=fam_,segment=seg,feature=n,test='rank slope',N_with=int(len(g)),N_without=0,dates=g.entry_date.nunique(),
                diff_x=b_*100,diff_med_x=med*100,diff_raw=braw*100,mean_with=g.x_mkt[hi].mean()*100,mean_without=g.x_mkt[lo].mean()*100,
                med_with=g.x_mkt[hi].median()*100,med_without=g.x_mkt[lo].median()*100,hit_with=(g.ret_net[hi]>0).mean()*100,hit_without=(g.ret_net[lo]>0).mean()*100,
                wd=wd,half1=h1,half2=h2,drop1=dt[0]*100,drop3=dt[1]*100,p=p,p_ticker_only=p_tk,p_incr=pi[1],p_mom=pm[1]))
            continue
        ind=pd.Series(vv.astype(bool).values,index=g.index); nw,no=int(ind.sum()),int((~ind).sum())
        if nw<MIN or no<MIN: skipped+=1; continue
        d,p=cl_test(g.x_mkt.values,ind.values.astype(float),g.ticker.values,g.entry_date.values); _,p_tk=cl_test(g.x_mkt.values,ind.values.astype(float),g.ticker.values)
        draw=g.ret_net[ind].mean()-g.ret_net[~ind].mean(); med=g.x_mkt[ind].median()-g.x_mkt[~ind].median()
        dt=drop_top_diff(g,ind,'x_mkt',np.sign(d) if np.isfinite(d) else 1); wd,h1,h2=extra_checks(g,ind); pi=incr(g,ind,seg); pm=incr_mom(g,ind.values.astype(float))
        rows.append(dict(kind='filter',family=fam_,segment=seg,feature=n,test={'bool':'with vs without','q1':'Q1 vs rest','q5':'Q5 vs rest'}[kind_],N_with=nw,N_without=no,
            dates=g.entry_date.nunique(),dates_with=g.entry_date[ind].nunique(),
            diff_x=d*100,diff_med_x=med*100,diff_raw=draw*100,mean_with=g.x_mkt[ind].mean()*100,mean_without=g.x_mkt[~ind].mean()*100,
            med_with=g.x_mkt[ind].median()*100,med_without=g.x_mkt[~ind].median()*100,hit_with=(g.ret_net[ind]>0).mean()*100,hit_without=(g.ret_net[~ind]>0).mean()*100,
            wd=wd,half1=h1,half2=h2,drop1=dt[0]*100,drop3=dt[1]*100,p=p,p_ticker_only=p_tk,p_incr=pi[1],p_mom=pm[1]))
FT=pd.DataFrame(rows)
# ------------------------------------------------------------------ level tests (paired vs the active policy on covered trades)
VN={}
for src_,lab in (('smcob','smc order block'),('smcliq','smc unswept liquidity'),('smcswing','smc confirmed swing'),('taewinv','python-taew invalidation'),('taewlast','python-taew last wave end'),('ewainv','ElliottWaveAnalyzer invalidation'),('ewalast','ElliottWaveAnalyzer last wave end')):
    VN[f'S_{src_}_fix']=f'stop: {lab} -0.5ATR (fixed)'; VN[f'S_{src_}_hyb']=f'stop: tighter of {lab}-0.5ATR and policy stop'
for src_,lab in (('smcliq','smc next unswept liquidity'),('smcfvg','smc next open FVG edge'),('taew','python-taew wave target'),('ewa','ElliottWaveAnalyzer wave target')):
    VN[f'T_{src_}_full']=f'target: {lab}, full exit'; VN[f'T_{src_}_half']=f'target: {lab}, 1/2 exit'
FAMV=lambda vn: 'smc' if 'smc' in vn else ('ew_taew' if 'taew' in vn else 'ew_ewa')
base=T[T.variant=='base'][['setup_id','mode','ret_net','x_mkt','status']].rename(columns={'ret_net':'b_ret','x_mkt':'b_x','status':'b_status'})
Vt=T[T.variant!='base'].merge(base,on=['setup_id','mode'])
lev=[]
for seg,f in SEGS:
    for (vn,mode),g in Vt[f(Vt)].groupby(['variant','mode']):
        if mode!='c': continue          # close-based = the headline mechanics (as §3.14); intraday kept in sim_levels_trades.csv
        allg=g; g=g[g.covered]
        if len(g)<MIN: skipped+=1; continue
        d=(g.ret_net-g.b_ret); dx=(g.x_mkt-g.b_x)
        mu,p=cl_mean(d.values,g.ticker.values,g.entry_date.values); _,p_tk=cl_mean(d.values,g.ticker.values)
        c=d.groupby(g.ticker).sum().sort_values(ascending=(mu<0)); dr=[d[~g.ticker.isin(list(c.index[:k]))].mean()*100 for k in (1,3)]
        lev.append(dict(kind='level',family=FAMV(vn),segment=seg,feature=VN[vn]+' (close)',code=vn,test='paired vs active policy',N_with=len(g),N_without=0,coverage=len(g)/len(allg)*100,
            dates=g.entry_date.nunique(),diff_x=dx.mean()*100,diff_med_x=dx.median()*100,diff_raw=mu*100,diff_med_raw=(g.ret_net.median()-g.b_ret.median())*100,
            changed=(d.abs()>1e-9).mean()*100,mean_with=g.ret_net.mean()*100,mean_without=g.b_ret.mean()*100,med_with=g.ret_net.median()*100,med_without=g.b_ret.median()*100,
            hit_with=(g.ret_net>0).mean()*100,hit_without=(g.b_ret>0).mean()*100,x_with=g.x_mkt.mean()*100,x_without=g.b_x.mean()*100,
            target_hit=g.target_hit.mean()*100,level_med_atr=g.level_dist_atr.median(),drop1=dr[0],drop3=dr[1],p=p,p_ticker_only=p_tk))
LT=pd.DataFrame(lev)
ALL=pd.concat([FT,LT],ignore_index=True); ALL=ALL[ALL.p.notna()].reset_index(drop=True)
M=len(ALL); o=np.argsort(ALL.p.values); pr=ALL.p.values[o]; q=pr*M/np.arange(1,M+1); q=np.minimum.accumulate(q[::-1])[::-1]; ALL.loc[o,'q_BH']=np.minimum(q,1)
eff=np.where(ALL.kind=='level',ALL.diff_raw,ALL.diff_x); medd=np.where(ALL.kind=='level',ALL.diff_med_raw,ALL.diff_med_x); oth=np.where(ALL.kind=='level',ALL.diff_x,ALL.diff_raw)
sgn_=np.sign(eff); wdok=np.where(ALL.kind=='level',True,np.sign(ALL.wd.fillna(0))==sgn_)
rob=(np.sign(medd)==sgn_)&(np.sign(oth)==sgn_)&(np.sign(ALL.drop1)==sgn_)&(np.sign(ALL.drop3)==sgn_)&wdok
ALL['effect']=np.where(sgn_>0,'better','worse'); ALL['checks_pass']=rob
ALL['flag']=np.where(ALL.q_BH<0.10,np.where(rob,'ROBUST','LUCK (fails robustness)'),np.where(ALL.p<0.05,'nominal p<0.05 only (fails FDR)','noise'))
ALL['n_comparisons']=M
ALL.to_csv(O+'ta_repos_table.csv',index=False); B.to_pickle(O+'analysis_base.pkl')
print('comparisons executed:',M,' skipped (N<20 / too few values):',skipped)
print('nominal p<0.05:',int((ALL.p<0.05).sum()),' expected ~',round(0.05*M,1),' q<0.10:',int((ALL.q_BH<0.10).sum()),' robust:',int((ALL.flag=='ROBUST').sum()))
print(ALL.groupby(['kind','family']).agg(n=('p','size'),nom=('p',lambda x:(x<0.05).sum()),minp=('p','min'),minq=('q_BH','min'),q10=('q_BH',lambda x:(x<0.1).sum()),robust=('flag',lambda x:(x=='ROBUST').sum())).to_string())
print(ALL.sort_values('p').head(40)[['segment','feature','test','N_with','N_without','diff_x','diff_med_x','diff_raw','wd','drop3','p','q_BH','p_incr','p_mom','flag']].round(4).to_string())
