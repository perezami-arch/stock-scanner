import pandas as pd, numpy as np, json
from scipy.stats import fisher_exact, mannwhitneyu
F=pd.read_pickle('features4.pkl')
FEATS=['pct_from_52w_low','pct_from_52w_high','rsi14','vs_sma20','vs_sma50','vs_sma150','vs_sma200','sma50_slope20','sma150_slope20','vol_vs20','vol_vs50','vol5_vs20','vol5_vs50','atr_pct','ret1','ret3','ret3_scan','ret5','ret20','ret60','from_20d_high','from_20d_low','from_60d_high','from_60d_low','range20_pct','range_contraction','ext_sma20_atr','gap_day1_open','entry_vs_asof_close','spy_ret5','qqq_ret5','days_to_earn','days_since_earn','rr_tp1','stop_atr','tp1_atr','stop_pct','tp1_pct','log_mcap','score','rank','conflict','spy_above_sma50','qqq_above_sma50','sector_above_sma50','sector_vs_sma50','sector_ret20','cnn_fg','crypto_fg','vix','vix_vs_50d','vix_term','dxy_ret20','us10y_chg20_bp','spread_10y_2y','spx_vs_ma125','spy_vs_sma50','spy_vs_sma200','qqq_vs_sma50','s5fi','s5th','s5tw','aaii_bull','aaii_bear','aaii_spread']
REGIME={'cnn_fg','crypto_fg','vix','vix_vs_50d','vix_term','dxy_ret20','us10y_chg20_bp','spread_10y_2y','spx_vs_ma125','spy_vs_sma50','spy_vs_sma200','qqq_vs_sma50','s5fi','s5th','s5tw','aaii_bull','aaii_bear','aaii_spread','spy_ret5','qqq_ret5','spy_above_sma50','qqq_above_sma50'}
def stats(d):
    d=d[d.status.isin(['resolved','open'])]; res=d[d.status=='resolved']; dat=d[d.ret_rule.notna()]
    w=int(res.win.sum()); l=len(res)-w
    return dict(n=len(d),n_res=len(res),tp1=w,stop=l,win=(w/len(res) if len(res) else np.nan),avg_rule=dat.ret_rule.mean() if len(dat) else np.nan,avg_last=dat.ret_last.mean() if len(dat) else np.nan,avg_rule_res=res.ret_rule.mean() if len(res) else np.nan)
def scan(g,minside=3):
    res=g[g.status=='resolved']; out=[]
    for c in FEATS:
        x=res[[c,'win','ret_rule']].dropna()
        if len(x)<6 or x[c].nunique()<2: continue
        W=x[x.win==1][c]; L=x[x.win==0][c]
        try: pmw=mannwhitneyu(W,L).pvalue if len(W)>=2 and len(L)>=2 else np.nan
        except Exception: pmw=np.nan
        best=None
        qs=sorted(set(np.quantile(x[c],np.linspace(0.2,0.8,13)))) if x[c].nunique()>2 else [0.5]
        for q in qs:
            hi=x[x[c]>q]; lo=x[x[c]<=q]
            if len(hi)<minside or len(lo)<minside: continue
            t=[[int(hi.win.sum()),len(hi)-int(hi.win.sum())],[int(lo.win.sum()),len(lo)-int(lo.win.sum())]]
            p=fisher_exact(t)[1]; d_=hi.win.mean()-lo.win.mean()
            if best is None or p<best['p'] or (p==best['p'] and abs(d_)>abs(best['diff'])): best=dict(thr=q,p=p,diff=d_,hi_n=len(hi),hi_win=hi.win.mean(),lo_n=len(lo),lo_win=lo.win.mean(),hi_ret=hi.ret_rule.mean(),lo_ret=lo.ret_rule.mean())
        if best: out.append(dict(feature=c,regime=c in REGIME,n_res=len(x),n_win=len(W),n_loss=len(L),med_win=W.median(),med_loss=L.median(),p_mw=pmw,**best))
    return pd.DataFrame(out).sort_values(['p','diff'],key=lambda s: s if s.name=='p' else -s.abs()) if out else pd.DataFrame()
GROUPS=[(s,d) for s in ['Grok momentum','Grok near-low','Grok prebreakout','Bot v2.8','Original sheet (annual low)'] for d in ['LONG','SHORT']]
if __name__=='__main__':
    pd.set_option('display.width',250); pd.set_option('display.max_columns',20); pd.set_option('display.max_rows',200)
    base={f'{s} {d}':stats(F[(F.strategy==s)&(F.dir==d)]) for s,d in GROUPS}
    print(pd.DataFrame(base).T.round(3))
    extra={'ALL Grok LONG':F[(F.source=='grok')&(F.dir=='LONG')],'ALL Grok SHORT':F[(F.source=='grok')&(F.dir=='SHORT')],'ALL LONG':F[F.dir=='LONG'],'ALL SHORT':F[F.dir=='SHORT']}
    for s,d in GROUPS: extra[f'{s} {d}']=F[(F.strategy==s)&(F.dir==d)]
    for k,g in extra.items():
        r=scan(g)
        if len(r)==0: continue
        print('\n####',k,'resolved',(g.status=='resolved').sum())
        print(r.head(10)[['feature','n_res','med_win','med_loss','thr','hi_n','hi_win','lo_n','lo_win','p','p_mw']].round(3).to_string(index=False))
