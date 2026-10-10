"""§3.14: filter tests + level tests for the scanner_geometry experimental columns, with Benjamini-Hochberg FDR and robustness.
Outcome = the ACTIVE policy trade (sim_geo.py base_c == sim_ratchet rt_ratchet_h618_c / rt_ratchet_c / rt_fixed3_c, close-based).
Primary metric = excess return vs market over the same entry->exit window (x_mkt: SPY for stocks, BTC for crypto; shorts: ret + bench).
Filter test: mean x_mkt (feature present) - mean x_mkt (absent); p from OLS with ticker-clustered SE (t, G-1 df).
Continuous features: Q1 vs rest, Q5 vs rest (segment quintiles) + rank slope (x_mkt on percentile rank, clustered SE).
Level tests: paired per-trade difference (variant - baseline) on covered trades, clustered SE.
Min N >= 20 on each side (filter) / >= 20 covered trades (level). Every executed comparison enters ONE BH family (q = 0.10).
Robust = q < 0.10 AND median difference same sign AND raw-return difference same sign AND sign kept after dropping the top-1 and
top-3 tickers (ranked by their contribution to the difference). q < 0.10 failing any check = LUCK."""
import numpy as np, pandas as pd, warnings, sys
import statsmodels.api as sm
warnings.filterwarnings('ignore')
OUT='/workspace/trading-frameworks-eval/iaf/'
s=open(OUT+'analyze.py').read(); exec(s[:s.index('# ======================= REPORT')])
exec(s[s.index('def rulepass_long'):s.index('def table_policies')])
GT=pd.read_csv(OUT+'sim_geo_trades.csv'); GF=pd.read_pickle(OUT+'geo_features.pkl')
T=add_bench(GT); T=T[T.in_main & ~T.dup.astype(bool)].copy()
T['x_mkt']=np.where(T.asset=='crypto',T.x_btc,T.x_spy)
T['rules']=T.apply(lambda r: rulepass_long(r) if r.direction=='LONG' else rulepass_short(r),axis=1)
T['R_mult']=T.ret_net/(T.R_pct/100)
SEGS=[('All stock LONG',lambda g:(g.asset=='stock')&(g.direction=='LONG')),
      ('Rule-filtered stock LONG',lambda g:(g.asset=='stock')&(g.direction=='LONG')&g.rules),
      ('Perplexity stock LONG',lambda g:(g.asset=='stock')&(g.direction=='LONG')&(g.source=='Perplexity')),
      ('Grok stock LONG',lambda g:(g.asset=='stock')&(g.direction=='LONG')&(g.source=='Grok')),
      ('All stock SHORT',lambda g:(g.asset=='stock')&(g.direction=='SHORT')),
      ('Crypto LONG',lambda g:(g.asset=='crypto')&(g.direction=='LONG'))]
# ------------------------------------------------------------------ derived, direction-aligned features
B=T[T.policy=='base_c'].merge(GF,on='setup_id',how='left')
sg=np.where(B.direction=='LONG',1,-1); L_=sg==1
def pick(lc,sc): return np.where(L_,B[lc],B[sc])
def fnum(a): return pd.to_numeric(pd.Series(a,index=B.index),errors='coerce')
def fbool(a): return pd.Series(a,index=B.index).map(lambda v: (bool(v) if v is not None and not (isinstance(v,float) and np.isnan(v)) else np.nan))
FB={}; FC={}   # boolean / continuous feature columns  (name -> (series, family))
fam=lambda n: 'spiral' if 'spiral' in n else 'gann' if 'gann' in n else 'vp' if n.startswith('vp') else 'candle' if n.startswith('candle') else 'liquidity'
# liquidity: fwd = target side (buy-side pools above for longs), back = stop side
for side,(lc,sc) in {'fwd':('bsl','ssl'),'back':('ssl','bsl')}.items():
    n_=fnum(pick(f'liq_{lc}_pools_n',f'liq_{sc}_pools_n')).fillna(0)
    FB[f'liq_{side}_pool_equal (nearest pool >=2 touches)']=fbool(pick(f'liq_{lc}_equal',f'liq_{sc}_equal')).where(n_>0)
    FB[f'liq_{side}_pool_hvn (nearest pool on an HVN)']=fbool(pick(f'liq_{lc}_hvn',f'liq_{sc}_hvn')).where(n_>0)
    FB[f'liq_{side}_strong_pool (>=2-touch pool within 5 ATR)']=fnum(pick(f'liq_{lc}_strong_touches',f'liq_{sc}_strong_touches')).notna()
    FC[f'liq_{side}_pool_dist_atr']=fnum(pick(f'liq_{lc}_dist_atr',f'liq_{sc}_dist_atr'))
    FC[f'liq_{side}_strong_dist_atr']=fnum(pick(f'liq_{lc}_strong_dist_atr',f'liq_{sc}_strong_dist_atr'))
    FC[f'liq_{side}_pools_n']=n_
# FVG / OB (fwd = above for longs)
FB['liq_in_fvg']=fbool(B.liq_in_fvg)
FB['liq_fwd_fvg_exists']=fnum(pick('liq_fvg_above_dist_atr','liq_fvg_below_dist_atr')).notna()
FB['liq_back_fvg_exists']=fnum(pick('liq_fvg_below_dist_atr','liq_fvg_above_dist_atr')).notna()
FB['liq_back_fvg_aligned (bull gap below long / bear gap above short)']=pd.Series(np.where(L_,B.liq_fvg_below_type=='bull',B.liq_fvg_above_type=='bear'),index=B.index)
FC['liq_fwd_fvg_dist_atr']=fnum(pick('liq_fvg_above_dist_atr','liq_fvg_below_dist_atr'))
FC['liq_back_fvg_dist_atr']=fnum(pick('liq_fvg_below_dist_atr','liq_fvg_above_dist_atr'))
FC['liq_fvg_open_n']=fnum(B.liq_fvg_open_n)
FB['liq_back_ob_exists (unmitigated OB on stop side)']=fnum(pick('liq_ob_below_dist_atr','liq_ob_above_dist_atr')).notna()
FB['liq_fwd_ob_exists (unmitigated OB on target side)']=fnum(pick('liq_ob_above_dist_atr','liq_ob_below_dist_atr')).notna()
FC['liq_back_ob_dist_atr']=fnum(pick('liq_ob_below_dist_atr','liq_ob_above_dist_atr'))
FC['liq_ob_open_n']=fnum(B.liq_ob_open_n)
# sweeps split by kind (cluster = 'Nx swing high/low' pool; prior = prior-bar high/low break) and by direction vs the trade
kind=B.liq_sweep_kind.fillna(''); dr=B.liq_sweep_dir.fillna('')
cl=kind.str.contains('swing'); pr=kind.str.contains('prior bar'); al=np.where(L_,dr.str.startswith('bullish'),dr.str.startswith('bearish'))
FB['liq_sweep_any (last 3 bars)']=kind!=''
FB['liq_sweep_cluster (pool swept)']=cl
FB['liq_sweep_prior_bar (prior-candle break)']=pr
FB['liq_sweep_cluster_aligned (bullish sweep for long / bearish for short)']=cl&al
FB['liq_sweep_cluster_against']=cl&~al
FB['liq_sweep_prior_aligned']=pr&al
FB['liq_sweep_prior_against']=pr&~al
# volume profile
for w in ('vp60','vp120','vpanc'):
    pos=B[f'{w}_va_pos']; ok=pos.notna()
    FB[f'{w}_beyond_VA_in_trade_dir']=pd.Series(np.where(L_,pos=='above VA',pos=='below VA'),index=B.index).where(ok)
    FB[f'{w}_inside_VA']=(pos=='inside VA').where(ok)
    FB[f'{w}_behind_VA (against trade dir)']=pd.Series(np.where(L_,pos=='below VA',pos=='above VA'),index=B.index).where(ok)
    FC[f'{w}_poc_dist_atr_signed (+ = beyond POC in trade dir)']=fnum(B[f'{w}_poc_dist_atr'])*sg
    FC[f'{w}_hvn_absdist_atr']=fnum(B[f'{w}_hvn_dist_atr']).abs()
    FC[f'{w}_lvn_absdist_atr']=fnum(B[f'{w}_lvn_dist_atr']).abs()
# spiral / gann
FB['exp_spiral_near_arc (<=0.5 ATR)']=fbool(B.exp_spiral_near_arc).where(B.exp_spiral_center_price.notna())
FC['exp_spiral_arc_dist_atr']=fnum(B.exp_spiral_arc_dist_atr)
FC['exp_spiral_next_node_bars']=fnum(B.exp_spiral_next_node_bars)
FC['exp_gann_level_fwd_atr']=fnum(pick('exp_gann_level_above_atr','exp_gann_level_below_atr'))
FC['exp_gann_level_back_atr']=fnum(pick('exp_gann_level_below_atr','exp_gann_level_above_atr'))
FC['exp_gann_scale_atr (swing slope, ATR/bar)']=fnum(B.exp_gann_scale_atr)
FC['exp_gann_next_time_bars']=fnum(B.exp_gann_next_time_bars)
FB['exp_gann_time_div_within_3_bars']=(fnum(B.exp_gann_next_time_bars)<=3).where(B.exp_gann_next_time_bars.notna())
FB['exp_gann_box_level_within_0.5ATR']=((fnum(B.exp_gann_level_above_atr)<=0.5)|(fnum(B.exp_gann_level_below_atr)<=0.5)).where(B.exp_gann_box_range.notna())
# candles
bias=B.candle_bias_last
FB['candle_bias_aligned (bullish for long / bearish for short)']=pd.Series(np.where(L_,bias=='bullish',bias=='bearish'),index=B.index).where(bias.notna())
FB['candle_bias_against']=pd.Series(np.where(L_,bias=='bearish',bias=='bullish'),index=B.index).where(bias.notna())
FB['candle_any_pattern_last_bar']=(B.candle_patterns_last.notna()).where(bias.notna())
FB['candle_vol_confirmed_aligned']=(fbool(B.candle_vol_confirmed).fillna(False).astype(bool)&FB['candle_bias_aligned (bullish for long / bearish for short)'].fillna(False).astype(bool)).where(bias.notna())
ctx=B.candle_context
FB['candle_context_with_trade (uptrend for long)']=pd.Series(np.where(L_,ctx=='uptrend',ctx=='downtrend'),index=B.index).where(ctx.notna())
FB['candle_context_against_trade']=pd.Series(np.where(L_,ctx=='downtrend',ctx=='uptrend'),index=B.index).where(ctx.notna())
FB['candle_context_sideways']=(ctx=='sideways').where(ctx.notna())
for c in [c for c in B.columns if c.startswith('candle_') and c[7:] in ('hammer','inverted_hammer','bullish_engulfing','bullish_harami','piercing','morning_star','three_white_soldiers','tweezer_bottom','marubozu_bull','dragonfly_doji_down','hanging_man','shooting_star','bearish_engulfing','bearish_harami','dark_cloud','evening_star','three_black_crows','tweezer_top','marubozu_bear','gravestone_doji_up','doji','dragonfly_doji','gravestone_doji','spinning_top','inside_bar','outside_bar')]:
    FB[c]=fbool(B[c]).where(bias.notna())
FC['candle_trend10_atr_signed (+ = with trade)']=fnum(B.candle_trend10_atr)*sg
FC['candle_vol_ratio20']=fnum(B.candle_vol_ratio20)
FC['candle_score_last_signed']=fnum(B.candle_score_last)*sg
# ------------------------------------------------------------------ tests
def _fit(y,X,G_):
    try:
        m=sm.OLS(y,X).fit(cov_type='cluster',cov_kwds={'groups':G_},use_t=True); return float(m.params[1 if X.shape[1]>1 else 0]),float(m.pvalues[1 if X.shape[1]>1 else 0])
    except Exception: return np.nan,np.nan
def cl_test(y,xv,grp,dates=None,ctrl=None):
    """slope of y on xv (+controls). p = MAX of the ticker-clustered, entry-date-clustered and two-way clustered p-values
    (conservative: stock setups come from only ~22-25 entry dates, and two-way SEs can be unstable with few clusters)."""
    y=np.asarray(y,float); X=np.asarray(xv,float).reshape(len(y),-1)
    if ctrl is not None: X=np.column_stack([X,ctrl])
    X=sm.add_constant(X,has_constant='add'); gt=pd.factorize(grp)[0]
    b,p=_fit(y,X,gt)
    if dates is not None:
        gd=pd.factorize(dates)[0]; p=max(p,_fit(y,X,gd)[1],_fit(y,X,np.column_stack([gt,gd]))[1])
    return b,p
def cl_mean(d,grp,dates=None):
    y=np.asarray(d,float); X=np.ones((len(y),1)); gt=pd.factorize(grp)[0]
    b,p=_fit(y,X,gt)
    if dates is not None:
        gd=pd.factorize(dates)[0]; p=max(p,_fit(y,X,gd)[1],_fit(y,X,np.column_stack([gt,gd]))[1])
    return b,p
def drop_top_diff(g,ind,col,sign):
    """contribution of ticker t to mean(with)-mean(without); drop top-k by sign*contribution, recompute."""
    w=g[ind]; o=g[~ind]; nw,no=len(w),len(o)
    c=(w.groupby('ticker')[col].sum()/nw).sub(o.groupby('ticker')[col].sum()/no,fill_value=0)
    out=[]
    for k in (1,3):
        top=list((c*sign).sort_values(ascending=False).index[:k]); h=g[~g.ticker.isin(top)]; hi=ind[~g.ticker.isin(top)]
        out.append((h[hi][col].mean()-h[~hi][col].mean()) if hi.sum()>0 and (~hi).sum()>0 else np.nan)
    return out
def extra_checks(g,ind):
    """within-entry-date difference (x_mkt demeaned by same-entry-date cohort) and the difference in each half of the period."""
    xd=g.x_mkt-g.groupby('entry_date').x_mkt.transform('mean')
    wd=(xd[ind].mean()-xd[~ind].mean())*100
    md=g.entry_date.sort_values().iloc[len(g)//2]; out=[]
    for h in (g.entry_date<md, g.entry_date>=md):
        a,b=ind&h,(~ind)&h
        out.append((g.x_mkt[a].mean()-g.x_mkt[b].mean())*100 if a.sum()>=5 and b.sum()>=5 else np.nan)
    return wd,out[0],out[1]
def incr(g,ind,seg):
    """does the feature add anything beyond the existing rule inputs (20-method score, SMA200 position, sector uptrend)?"""
    cols=['ck_score','vs_sma200']+(['sector_up'] if 'stock' in seg else [])
    C_=g[cols].astype(float); ok=C_.notna().all(axis=1).values
    if ok.sum()<2*MIN: return (np.nan,np.nan)
    return cl_test(g.x_mkt.values[ok],ind.values.astype(float)[ok],g.ticker.values[ok],g.entry_date.values[ok],ctrl=C_.values[ok])
B=B.merge(D[['setup_id','vs_sma200']],on='setup_id',how='left') if 'vs_sma200' not in B.columns else B
rows=[]; skipped=0
MIN=20
for seg,f in SEGS:
    m=f(B).values; g0=B[m]
    feats=[(n,'bool',FB[n][m]) for n in FB]
    for n,v in FC.items():
        v=v[m]; ok=v.notna()
        if ok.sum()<2*MIN or v[ok].nunique()<5: skipped+=3; continue
        q=pd.qcut(v[ok].rank(method='first'),5,labels=False)
        q1=pd.Series(np.nan,index=v.index); q1[ok]=(q==0).astype(float); q5=pd.Series(np.nan,index=v.index); q5[ok]=(q==4).astype(float)
        feats+= [(n+' : Q1 (lowest 20%) vs rest','q1',q1),(n+' : Q5 (highest 20%) vs rest','q5',q5),(n+' : rank slope (Q5-Q1 equiv.)','rank',v)]
    for n,kind_,v in feats:
        ok=v.notna(); g=g0[ok.values]; vv=v[ok]
        if kind_=='rank':
            if len(g)<2*MIN: skipped+=1; continue
            rk=vv.rank(pct=True).values
            b_,p=cl_test(g.x_mkt.values,rk,g.ticker.values,g.entry_date.values); _,p_tk=cl_test(g.x_mkt.values,rk,g.ticker.values)
            braw,_=cl_test(g.ret_net.values,rk,g.ticker.values)
            hi=rk>=0.8; lo=rk<=0.2
            med=g.x_mkt[hi].median()-g.x_mkt[lo].median()
            ind=pd.Series(rk>=0.5,index=g.index)
            dt=drop_top_diff(g,ind,'x_mkt',np.sign(b_) if np.isfinite(b_) else 1)
            wd,h1,h2=extra_checks(g,ind); pi=incr(g,pd.Series(rk,index=g.index),seg)
            rows.append(dict(wd=wd,half1=h1,half2=h2,p_ticker_only=p_tk,p_incr=pi[1],diff_incr=pi[0]*100,family=fam(n),segment=seg,feature=n,test='rank slope',N_with=int(len(g)),N_without=0,
                diff_x=b_*100,diff_med_x=med*100,diff_raw=braw*100,mean_with=g.x_mkt[hi].mean()*100,mean_without=g.x_mkt[lo].mean()*100,
                med_with=g.x_mkt[hi].median()*100,med_without=g.x_mkt[lo].median()*100,raw_with=g.ret_net[hi].mean()*100,raw_without=g.ret_net[lo].mean()*100,
                hit_with=(g.ret_net[hi]>0).mean()*100,hit_without=(g.ret_net[lo]>0).mean()*100,
                drop1=dt[0]*100,drop3=dt[1]*100,p=p,rho=pd.Series(rk).corr(pd.Series(g.x_mkt.values),method='spearman')))
            continue
        ind=pd.Series(vv.astype(bool).values,index=g.index)
        nw,no=int(ind.sum()),int((~ind).sum())
        if nw<MIN or no<MIN: skipped+=1; continue
        d,p=cl_test(g.x_mkt.values,ind.values.astype(float),g.ticker.values,g.entry_date.values); _,p_tk=cl_test(g.x_mkt.values,ind.values.astype(float),g.ticker.values)
        draw=g.ret_net[ind].mean()-g.ret_net[~ind].mean()
        med=g.x_mkt[ind].median()-g.x_mkt[~ind].median()
        dt=drop_top_diff(g,ind,'x_mkt',np.sign(d) if np.isfinite(d) else 1)
        wd,h1,h2=extra_checks(g,ind); pi=incr(g,ind,seg)
        rows.append(dict(wd=wd,half1=h1,half2=h2,p_ticker_only=p_tk,p_incr=pi[1],diff_incr=pi[0]*100,family=fam(n),segment=seg,feature=n,test={'bool':'with vs without','q1':'Q1 vs rest','q5':'Q5 vs rest'}[kind_],N_with=nw,N_without=no,
            diff_x=d*100,diff_med_x=med*100,diff_raw=draw*100,mean_with=g.x_mkt[ind].mean()*100,mean_without=g.x_mkt[~ind].mean()*100,
            med_with=g.x_mkt[ind].median()*100,med_without=g.x_mkt[~ind].median()*100,raw_with=g.ret_net[ind].mean()*100,raw_without=g.ret_net[~ind].mean()*100,
            hit_with=(g.ret_net[ind]>0).mean()*100,hit_without=(g.ret_net[~ind]>0).mean()*100,drop1=dt[0]*100,drop3=dt[1]*100,p=p))
FT=pd.DataFrame(rows); FT['kind']='filter'
# ------------------------------------------------------------------ level tests (paired vs baseline on covered trades)
LV=[]; lev_rows=[]
base=T[T.variant=='base'][['setup_id','mode','ret_net','x_mkt','status','R_pct']].rename(columns={'ret_net':'b_ret','x_mkt':'b_x','status':'b_status'})
VN={'S_pool_fix':'stop: nearest liquidity pool beyond entry -0.5ATR (fixed)','S_pool_hyb':'stop: tighter of pool-0.5ATR and policy stop',
    'S_ob_fix':'stop: order-block zone -0.5ATR (fixed)','S_ob_hyb':'stop: tighter of OB-0.5ATR and policy stop',
    'S_hvn_fix':'stop: nearest HVN -0.5ATR (fixed)','S_hvn_hyb':'stop: tighter of HVN-0.5ATR and policy stop',
    'T_pool_full':'target: next liquidity pool, full exit','T_pool_half':'target: next liquidity pool, 1/2 exit',
    'T_fvg_full':'target: next open FVG edge, full exit','T_fvg_half':'target: next open FVG edge, 1/2 exit'}
V=T[T.variant!='base'].merge(base,on=['setup_id','mode'])
for seg,f in SEGS:
    for (vn,mode),g in V[f(V)].groupby(['variant','mode']):
        g=g[g.covered]
        if len(g)<MIN: skipped+=1; continue
        d=(g.ret_net-g.b_ret); dx=(g.x_mkt-g.b_x)
        mu,p=cl_mean(d.values,g.ticker.values,g.entry_date.values); _,p_tk=cl_mean(d.values,g.ticker.values)
        c=d.groupby(g.ticker).sum().sort_values(ascending=(mu<0)); dr=[]
        for k in (1,3): dr.append(d[~g.ticker.isin(list(c.index[:k]))].mean()*100)
        lev_rows.append(dict(family='level',kind='level',segment=seg,feature=VN[vn]+(' (close)' if mode=='c' else ' (intraday)'),code=f'{vn}_{mode}',test='paired vs active policy',
            N_with=len(g),N_without=0,coverage=len(g)/len(V[f(V)&(V.variant==vn)&(V['mode']==mode)])*100,
            diff_x=dx.mean()*100,diff_med_x=dx.median()*100,diff_raw=mu*100,diff_med_raw=(g.ret_net.median()-g.b_ret.median())*100,med_paired=d.median()*100,p_ticker_only=p_tk,changed=(d.abs()>1e-9).mean()*100,
            mean_with=g.ret_net.mean()*100,mean_without=g.b_ret.mean()*100,med_with=g.ret_net.median()*100,med_without=g.b_ret.median()*100,
            raw_with=g.ret_net.mean()*100,raw_without=g.b_ret.mean()*100,hit_with=(g.ret_net>0).mean()*100,hit_without=(g.b_ret>0).mean()*100,
            x_with=g.x_mkt.mean()*100,x_without=g.b_x.mean()*100,stopped_with=(g.status=='stopped').mean()*100,stopped_without=(g.b_status=='stopped').mean()*100,
            target_hit=g.target_hit.mean()*100,level_med_atr=g.level_dist_atr.median(),
            drop1=dr[0],drop3=dr[1],p=p))
LT=pd.DataFrame(lev_rows)
ALL=pd.concat([FT,LT],ignore_index=True)
# ------------------------------------------------------------------ BH FDR over every executed comparison
ALL=ALL[ALL.p.notna()].reset_index(drop=True)
M=len(ALL); o=np.argsort(ALL.p.values); pr=ALL.p.values[o]; q=pr*M/np.arange(1,M+1); q=np.minimum.accumulate(q[::-1])[::-1]
ALL.loc[o,'q_BH']=np.minimum(q,1)
eff=np.where(ALL.kind=='level',ALL.diff_raw,ALL.diff_x)
medd=np.where(ALL.kind=='level',ALL.diff_med_raw,ALL.diff_med_x)
oth=np.where(ALL.kind=='level',ALL.diff_x,ALL.diff_raw)
sgn_=np.sign(eff)
wdok=np.where(ALL.kind=='level',True,np.sign(ALL.wd.fillna(0))==sgn_)
rob=(np.sign(medd)==sgn_)&(np.sign(oth)==sgn_)&(np.sign(ALL.drop1)==sgn_)&(np.sign(ALL.drop3)==sgn_)&wdok
ALL['effect']=np.where(sgn_>0,'better','worse')
ALL['checks_pass']=rob
ALL['flag']=np.where(ALL.q_BH<0.10,np.where(rob,'ROBUST','LUCK (fails robustness)'),np.where(ALL.p<0.05,'nominal p<0.05 only (fails FDR)','noise'))
ALL['n_comparisons']=M
ALL.to_csv(OUT+'geometry_table.csv',index=False)
print('comparisons executed:',M,' skipped (N<20 or too few values):',skipped)
print('nominal p<0.05:',int((ALL.p<0.05).sum()),' expected by chance ~',round(0.05*M,1),'  q<0.10:',int((ALL.q_BH<0.10).sum()),'  q<0.20:',int((ALL.q_BH<0.20).sum()))
print(ALL.groupby(['kind','family']).agg(n=('p','size'),nom=('p',lambda x:(x<0.05).sum()),minp=('p','min'),minq=('q_BH','min')).to_string())
print(ALL.sort_values('p').head(45)[['segment','feature','test','N_with','N_without','diff_x','diff_med_x','diff_raw','wd','half1','half2','drop3','p_ticker_only','p','q_BH','p_incr','flag']].round(4).to_string())
pd.to_pickle(dict(ALL=ALL,M=M,skipped=skipped),OUT+'geo_results.pkl')
