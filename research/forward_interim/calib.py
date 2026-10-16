import pandas as pd, numpy as np, re, json
from scipy import stats
import os; S=os.environ.get('SCANNER_ROOT','/workspace')+'/scan-runs/'
px=pd.read_pickle('px.pkl'); LAST=pd.Timestamp('2026-10-15')
YF={'UNI':'UNI7083-USD','LINK':'LINK-USD'}
def jnum(v):
    m=re.search(r'([+-]?\d+(?:\.\d+)?)\)?\s*$',str(v)); return float(m.group(1)) if m else np.nan
def verd(L):
    out={}
    for t,g in L.groupby('ticker'):
        r={}
        for _,z in g.iterrows():
            p=z.platform; v=str(z.verdict).lower()
            if p=='jev': r['jev']=jnum(z.verdict)
            else: r[p]=v
            if p=='claude': r['claude_conv']=z.conviction_or_sentiment
        out[t]=r
    return out
# trial
T=pd.read_csv(S+'platform_verdicts_ledger_trial.csv'); T=T[T.run_dir.str.contains('2026-10-08_1515')]
vt=verd(T); rows=[]
for t,g in T.groupby('ticker',sort=False):
    z=g.iloc[0]; rows.append(dict(source='trial-2026-10-08',chart_images=False,ticker=t,asset='stock',direction=z.direction,entry_date='2026-10-09',stop=z.stop,target=z.target,**vt[t]))
M=pd.read_csv(S+'platform_verdicts_ledger.csv'); vm=verd(M)
R=pd.read_csv(S+'positions_registry.csv')
for _,z in R.iterrows():
    rows.append(dict(source='weekly-2026-10-12',chart_images=True,ticker=z.ticker,asset=z.asset,direction=z.direction,entry_date='2026-10-13',stop=z.stop_initial,target=z.target,registry_entry=z.entry_price,**vm[z.ticker]))
D=pd.DataFrame(rows)
def path(t): 
    d=px[YF.get(t,t)][['Open','High','Low','Close']].dropna(); return d[d.index<=LAST]
res=[]
for _,r in D.iterrows():
    d=path(r.ticker); d=d[d.index>=r.entry_date]; e=d.Open.iloc[0]; sg=1 if r.direction=='LONG' else -1
    b=path('BTC-USD' if r.asset=='crypto' else 'SPY'); b=b[b.index>=r.entry_date]; b=b[b.index.isin(d.index)] if r.asset=='stock' else b
    ex=None; exd=None; why='open'
    for dt,c in d.Close.items():
        if sg*(c-r.stop)<=0: ex,exd,why=c,dt,'stop'; break
        if pd.notna(r.target) and sg*(c-r.target)>=0: ex,exd,why=c,dt,'target'; break
    last=ex if ex is not None else d.Close.iloc[-1]; ldt=exd if exd is not None else d.index[-1]
    ret=sg*(last/e-1); riskpct=abs(e-r.stop)/e
    bret=b.Close[b.index<=ldt].iloc[-1]/b.Open.iloc[0]-1
    k=3; d3=sg*(d.Close.iloc[k-1]/e-1) if len(d)>=k else np.nan; b3=b.Close.iloc[k-1]/b.Open.iloc[0]-1
    mae=(sg*((d.Low if sg>0 else d.High)/e-1)).min()
    res.append(dict(entry=e,last=last,last_date=ldt.date(),status=why,n_days=len(d),ret=ret,R=ret/riskpct,risk_pct=riskpct,bench_ret=bret,
        excess=ret-sg*bret,ret_d3=d3,excess_d3=d3-sg*b3,mae=mae))
D=pd.concat([D,pd.DataFrame(res)],axis=1)
# tools
sgn=np.where(D.direction=='LONG',1,-1)
F={'grok_approve':D.grok.eq('approve'),'grok_veto':D.grok.eq('veto'),'pplx_approve':D.pplx.eq('approve'),'pplx_flag':D.pplx.eq('flag'),
   'claude_supports':D.claude.eq('supports'),'claude_conv>=50':D.claude_conv>=50,'gpt_veto':D.gpt.eq('veto'),
   'jev_agrees_dir':(D.jev*sgn)>0.25,'jev_against_dir':(D.jev*sgn)<-0.25}
def ci(x):
    x=x.dropna(); n=len(x)
    if n<2: return np.nan,np.nan
    h=stats.t.ppf(.975,n-1)*x.std(ddof=1)/np.sqrt(n); return x.mean()-h,x.mean()+h
tab=[]
for seg,mask in [('ALL',D.index==D.index),('trial (no charts)',D.source.str.startswith('trial')),('12.10 (charts)',D.source.str.startswith('weekly'))]:
  for k,f in F.items():
    f=f&mask; u=(~f)&mask; xf=D.excess_d3[f]; xu=D.excess_d3[u]
    lo,hi=ci(xf)
    tab.append(dict(segment=seg,tool=k,n_flag=int(f.sum()),n_unflag=int(u.sum()),entry_days=D.entry_date[f].nunique(),hit_rate=(xf>0).mean() if len(xf) else np.nan,
       mean_excess_d3=xf.mean(),ci95_lo=lo,ci95_hi=hi,mean_excess_unflag=xu.mean(),diff=xf.mean()-xu.mean(),
       p_welch=stats.ttest_ind(xf,xu,equal_var=False).pvalue if len(xf)>1 and len(xu)>1 else np.nan,status='איסוף (<15)' if f.sum()<15 else 'ביניים'))
tab=pd.DataFrame(tab)
D.to_csv('positions_pnl.csv',index=False); tab.to_csv('calibration_interim.csv',index=False)
pd.set_option('display.width',250)
print(D[['source','ticker','direction','entry','stop','target','last','status','n_days','ret','R','excess','excess_d3','registry_entry']].round(4).to_string())
print(tab[tab.segment=='ALL'].round(4).to_string())
print('base all mean excess_d3',D.excess_d3.mean(),'hit',(D.excess_d3>0).mean())
for s,g in D.groupby('source'): print(s,'mean ret',g.ret.mean(),'mean R',g.R.mean(),'excess',g.excess.mean())
