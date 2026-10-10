import pandas as pd, numpy as np
O='/workspace/ta-repos-eval/out/'
def md(df, fl=2):
    df=df.copy()
    for c in df.columns:
        if df[c].dtype.kind=='f': df[c]=df[c].map(lambda v: '' if pd.isna(v) else (f'{v:.3g}' if abs(v)<0.01 and v!=0 else f'{v:.{fl}f}'))
    return df.to_markdown(index=False)
t=pd.read_csv(O+'ta_repos_table.csv')
out={}
# family summary
g=t.groupby(['family','kind']).agg(n=('p','size'),nom=('p',lambda s:(s<0.05).sum()),minp=('p','min'),q10=('q_BH',lambda s:(s<0.10).sum()),robust=('flag',lambda s:(s=='ROBUST').sum() if 'ROBUST' in set(s) else 0)).reset_index()
out['fam']=md(g,3)
out['flags']=t.flag.value_counts().to_dict()
sv=t[t.q_BH<0.10].sort_values('q_BH')
cols=['kind','family','segment','feature','test','N_with','N_without','dates','diff_x','diff_med_x','drop1','drop3','wd','p','p_incr','p_mom','q_BH','effect','flag']
out['surv']=md(sv[cols])
cm=t[(t.p<0.05)&(t.q_BH>=0.10)].sort_values('p').head(30)
out['miss']=md(cm[cols])
lv=t[t.kind!='filter'].sort_values('p')
lcols=['family','segment','feature','N_with','coverage','changed','diff_raw','diff_med_raw','diff_x','target_hit','level_med_atr','p','q_BH','effect','flag']
out['lev']=md(lv[[c for c in lcols if c in lv]].head(22))
ref=t[t.family=='reference'].sort_values('p')
out['ref']=md(ref[cols])
ew=t[t.family.str.startswith('ew')&(t.kind=='filter')].sort_values('p').head(15)
out['ewf']=md(ew[cols])
for f in ['agree_candles','agree_smc_geo','ew_coverage','ew_agreement']:
    out[f]=md(pd.read_csv(O+f+'.csv'))
# leak summaries
lt=pd.read_csv(O+'leak_talib.csv'); a=lt.groupby(['func','col']).agg(F=('F_diff','sum'),J=('J_diff','sum')).reset_index()
out['lt']=(len(a), lt.setup_id.nunique(), md(a[(a.F>0)|(a.J>0)]))
lp=pd.read_csv(O+'leak_pandas_ta.csv'); a=lp.groupby('col').agg(F=('F_diff','sum'),J=('J_diff','sum'),n=('setup_id','nunique')).reset_index()
out['lp']=(len(a), lp.setup_id.nunique(), md(a[(a.F>0)|(a.J>0)]))
ls=pd.read_csv(O+'leak_smc.csv'); a=ls.groupby('func').agg(setups=('setup_id','nunique')).reset_index()
b=ls.groupby(['func','setup_id']).agg(F=('F_diff','any'),J=('J_diff','any'),last=('last_bar_diff','any'),lb=('first_diff_bars_before_cut','max')).reset_index()
c=b.groupby('func').agg(n=('setup_id','size'),F_any=('F','sum'),J_any=('J','sum'),last_bar=('last','sum'),max_bars_back=('lb','max')).reset_index()
out['ls']=md(c)
le=pd.read_csv(O+'leak_ew.csv')
out['le']={k:int(le[k].sum()) for k in ['taew_F_pivot_on_cut_bar','taew_extra_in_F','taew_missing_in_F','ar_raw_provisional','ar_raw_missing','ar_conf_equal','ewa_last_wave_unconfirmed','ewa_chain_changes_with_future','junk_values','junk_mismatch']}
eq=pd.read_csv(O+'leak_ew_equivalence.csv'); out['eq']=(len(eq),int(eq.same9.sum()),int(eq.same_impulses.sum()))
import pickle; pickle.dump(out,open(O+'report_parts.pkl','wb'))
for k,v in out.items(): print('#####',k); print(v if not isinstance(v,tuple) else v[:2]); print(v[2] if isinstance(v,tuple) else '')
