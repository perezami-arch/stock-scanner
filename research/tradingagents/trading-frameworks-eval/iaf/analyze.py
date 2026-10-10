import json, glob, os, numpy as np, pandas as pd
OUT='/workspace/trading-frameworks-eval/iaf/'
D=pd.read_pickle(OUT+'setups_prepared.pkl'); F=pd.read_pickle(OUT+'frames.pkl'); B=pd.read_pickle(OUT+'bench_yf.pkl')
SECMAP={'Technology':'XLK','Financial Services':'XLF','Energy':'XLE','Healthcare':'XLV','Consumer Cyclical':'XLY','Consumer Defensive':'XLP','Industrials':'XLI','Basic Materials':'XLB','Utilities':'XLU','Real Estate':'XLRE','Communication Services':'XLC'}
def grp(r):
    p=str(r.platform)
    if 'original sheet' in p: return 'Original sheet (Grok/Pplx)'
    if r.source=='Grok':
        if r.asset=='crypto': return 'Grok crypto'
        a=str(r.automation)
        return {'momentum':'Grok momentum','near-low':'Grok near-low','prebreakout':'Grok prebreakout','x-trends-digest':'Grok x-trends','portfolio-news-scan':'Grok portfolio-news'}.get(a,'Grok other')
    return r.source
D['group']=D.apply(grp,axis=1)
D=D.merge(pd.read_csv('/workspace/tracker/setups-point-in-time-2026-10-08.csv')[['setup_id','in_hold_no_stop_csv']],on='setup_id',how='left')
D['src_asset']=D.source+' '+D.asset
MAIN=D.in_main & ~D.dup & D.has_data & D.decision_utc.notna()
# ---- benchmark price series (open/close by date)
def bser(t):
    if t in ('BTC-USD','ETH-USD'): x=F[(t,True)]
    else: x=B[t][['Open','Close']].dropna()
    x=x.copy(); x.index=pd.to_datetime(x.index); return x
BS={t:bser(t) for t in ['SPY','BTC-USD','ETH-USD']+list(SECMAP.values())}
def bret(t,e,x):
    s=BS.get(t)
    if s is None: return np.nan
    o=s.Open[s.index>=e]; c=s.Close[s.index<=x]
    if len(o)==0 or len(c)==0: return np.nan
    return c.iloc[-1]/o.iloc[0]-1
def add_bench(T):
    keep=['setup_id','ticker','asset','direction','group','source','src_asset','sector','sector_up','ck_score','below_sma200','automation','in_main','dup','has_data','decision_utc','in_hold_no_stop_csv','platform']
    T=T.drop(columns=[c for c in keep if c in T.columns and c!='setup_id']).merge(D[keep],on='setup_id',how='left')
    T['entry_date']=pd.to_datetime(T.entry_date); T['exit_date']=pd.to_datetime(T.exit_date)
    sg=np.where(T.direction=='SHORT',-1,1)
    for col,fn in [('b_spy',lambda r: bret('SPY',r.entry_date,r.exit_date) if r.asset=='stock' else np.nan),
                   ('b_sector',lambda r: bret(SECMAP.get(r.sector),r.entry_date,r.exit_date) if r.asset=='stock' and SECMAP.get(r.sector) else np.nan),
                   ('b_btc',lambda r: bret('BTC-USD',r.entry_date,r.exit_date) if r.asset=='crypto' else np.nan),
                   ('b_eth',lambda r: bret('ETH-USD',r.entry_date,r.exit_date) if r.asset=='crypto' else np.nan)]:
        T[col]=T.apply(fn,axis=1)
    T['b_basket']=(T.b_btc+T.b_eth)/2
    for b in ['spy','sector','btc','eth','basket']: T['x_'+b]=T.ret_net-sg*T['b_'+b]
    T['ret_pct']=T.ret_net*100
    return T
def stats(g, bench1, bench2=None, bench3=None):
    g=g.dropna(subset=['ret_net'])
    if len(g)==0: return {}
    r=g.ret_net*100
    d=dict(N=len(g),tickers=g.ticker.nunique(),mean=r.mean(),median=r.median(),hit=(r>0).mean()*100)
    for b in [bench1,bench2,bench3]:
        if b: d['x_'+b]=g['x_'+b].mean()*100; d['xmed_'+b]=g['x_'+b].median()*100
    key=('x_'+bench1) if bench1 and g['x_'+bench1].notna().any() else 'ret_net'   # rank tickers by their contribution to the EDGE (excess) when a benchmark exists
    contrib=g.groupby('ticker')[key].sum().sort_values(ascending=False)
    for k in (1,3):
        top=list(contrib.index[:k]); h=g[~g.ticker.isin(top)]
        d[f'mean_wo_top{k}']=h.ret_net.mean()*100 if len(h) else np.nan
        d[f'med_wo_top{k}']=h.ret_net.median()*100 if len(h) else np.nan
        if bench1: d[f'x_{bench1}_wo_top{k}']=h['x_'+bench1].mean()*100 if len(h) else np.nan
        d[f'top{k}']=','.join(f'{t}({int((g.ticker==t).sum())})' for t in top)
    base=d.get('x_'+bench1,d['mean']) if bench1 else d['mean']
    after=[d.get(f'x_{bench1}_wo_top1' if bench1 else 'mean_wo_top1'), d.get(f'x_{bench1}_wo_top3' if bench1 else 'mean_wo_top3')]
    d['flag']=('LUCK (edge gone w/o top tickers)' if base>0 and any(a is not None and a<=0 for a in after) else
               ('no edge vs bench' if base<=0 else 'robust to top-3 removal'))
    return d
def fmt(df,cols):
    out=['| '+' | '.join(cols)+' |','|'+'---|'*len(cols)]
    for _,r in df.iterrows():
        out.append('| '+' | '.join((f'{r[c]:+.1f}' if isinstance(r[c],(float,np.floating)) and c not in ('N','tickers','hit') else (f'{r[c]:.0f}' if isinstance(r[c],(float,np.floating,int,np.integer)) else str(r[c]))) for c in cols)+' |')
    return '\n'.join(out)

# ======================= REPORT =======================
POLS=['hold','fsetup','f8','t5','t8','t12']
PNAME={'hold':'hold, no stop','fsetup':"setup's own stop (fixed)",'f8':'fixed 8%','t5':'trailing 5%','t8':'trailing 8%','t12':'trailing 12%'}
iaf=[]
for f in sorted(glob.glob(OUT+'trades_*_*.csv')):
    a,p=os.path.basename(f)[7:-4].split('_'); t=pd.read_csv(f); t['asset_run']=a; t['policy']=p; iaf.append(t)
IAF=pd.concat(iaf) if iaf else pd.DataFrame()
SIM=pd.read_csv(OUT+'sim_trades.csv')
if os.path.exists(OUT+'sim_fib_trades.csv'): SIM=pd.concat([SIM,pd.read_csv(OUT+'sim_fib_trades.csv')],ignore_index=True)
if os.path.exists(OUT+'sim_targets_trades.csv'): SIM=pd.concat([SIM,pd.read_csv(OUT+'sim_targets_trades.csv')],ignore_index=True)
if os.path.exists(OUT+'sim_struct_trades.csv'): SIM=pd.concat([SIM,pd.read_csv(OUT+'sim_struct_trades.csv')],ignore_index=True)
if os.path.exists(OUT+'sim_chand_trades.csv'): SIM=pd.concat([SIM,pd.read_csv(OUT+'sim_chand_trades.csv')],ignore_index=True)
# IAF trade files lack exit_date for stop exits (closed-trade timestamps are on the compressed clock); take the real exit date
# from the independent replay where both engines produced the identical trade (|diff|<0.01pp), otherwise leave NaN.
_m=IAF.merge(SIM[['setup_id','policy','exit_date','ret_net']].rename(columns={'exit_date':'_sx','ret_net':'_sr'}),on=['setup_id','policy'],how='left')
_m['exit_date']=np.where(_m.exit_date.isna() & ((_m.ret_net-_m._sr).abs()<1e-4), _m._sx, _m.exit_date)
IAF=_m.drop(columns=['_sx','_sr'])
IAF=add_bench(IAF); SIM=add_bench(SIM)
IAFm=IAF[IAF.in_main & ~IAF.dup.astype(bool)]; SIMm=SIM[SIM.in_main & ~SIM.dup.astype(bool)]
md=[]
# 1. IAF vs independent replay agreement
if len(IAF):
    m=IAF.merge(SIM[['setup_id','policy','ret_net','status']],on=['setup_id','policy'],suffixes=('','_sim'))
    m['d']=(m.ret_net-m.ret_net_sim)*100
    ag=m.groupby(['asset_run','policy']).agg(N=('d','size'),identical=('d',lambda x:(x.abs()<0.01).mean()*100),mean_iaf=('ret_net',lambda x:x.mean()*100),mean_sim=('ret_net_sim',lambda x:x.mean()*100),max_abs_diff=('d',lambda x:x.abs().max())).reset_index()
    md.append('### A. IAF event engine vs independent pandas replay (longs, all setups incl. excluded rows)\n'+fmt(ag,['asset_run','policy','N','identical','mean_iaf','mean_sim','max_abs_diff']))
# 2. exit policies by source x asset, longs, IAF; all vs rule-filtered
def rulepass_long(r):
    if r.automation=='prebreakout': return False
    if r.asset=='stock': return r.sector_up==1
    return True
def rulepass_short(r):
    if r.asset=='crypto': return False
    return (r.ck_score>=3) and (r.below_sma200==1)
def table_policies(T,label,bench):
    out=[]
    for (sa),g in T.groupby('src_asset'):
        for p in POLS:
            gg=g[g.policy==p]
            if len(gg)==0: continue
            s=stats(gg,bench); s.update(group=sa,policy=PNAME[p]); out.append(s)
    return pd.DataFrame(out)
for asset,bench in (('stock','spy'),('crypto','btc')):
    L=IAFm[(IAFm.asset==asset)&(IAFm.direction=='LONG')].copy()
    if len(L)==0: continue
    L['rules']=L.apply(rulepass_long,axis=1)
    for lab,sub in (('ALL longs',L),('rule-filtered longs (no Grok prebreakout'+(', sector ETF uptrend' if asset=='stock' else '')+')',L[L.rules])):
        t=table_policies(sub,lab,bench)
        if len(t): md.append(f'### B. {asset.upper()} LONGS — {lab} — IAF event engine, net of costs\n'+fmt(t,['group','policy','N','mean','median','hit',f'x_{bench}',f'xmed_{bench}','mean_wo_top1','mean_wo_top3',f'x_{bench}_wo_top3','flag']))
# 3. benchmark-relative, hold & trailing 8%, by detailed group (sim covers shorts too; for longs IAF==sim)
for p in ('hold','t8'):
    rows=[]
    for (grp_,asset,dirn),g in SIMm[SIMm.policy==p].groupby(['group','asset','direction']):
        if asset=='stock': s=stats(g,'spy','sector')
        else: s=stats(g,'btc','eth','basket')
        s.update(group=grp_,asset=asset,dir=dirn); rows.append(s)
    t=pd.DataFrame(rows)
    st=t[t.asset=='stock']; cr=t[t.asset=='crypto']
    md.append(f'### C1. STOCKS vs SPY / sector ETF — policy: {PNAME[p]} (same entry->exit window; shorts: excess = ret + bench ret)\n'+fmt(st,['group','dir','N','tickers','mean','median','hit','x_spy','xmed_spy','x_sector','mean_wo_top1','mean_wo_top3','x_spy_wo_top1','x_spy_wo_top3','top1','flag']))
    md.append(f'### C2. CRYPTO vs BTC / ETH / 50-50 basket — policy: {PNAME[p]}\n'+fmt(cr,['group','dir','N','tickers','mean','median','hit','x_btc','xmed_btc','x_eth','x_basket','xmed_basket','mean_wo_top1','mean_wo_top3','x_btc_wo_top1','x_btc_wo_top3','top3','flag']))
# 4. specific leave-out checks
spec=[('Grok crypto longs w/o NEAR','Grok crypto','LONG','NEAR-USD','btc'),('Perplexity (all, longs) w/o XP','Perplexity','LONG','XP','spy'),('Original sheet longs w/o IOVA','Original sheet (Grok/Pplx)','LONG','IOVA','spy')]
rows=[]
for name,grp_,dirn,tk,b in spec:
    for p in ('hold','t8'):
        g=SIMm[(SIMm.policy==p)&(SIMm.group==grp_)&(SIMm.direction==dirn)] if grp_!='Perplexity' else SIMm[(SIMm.policy==p)&(SIMm.source=='Perplexity')&(SIMm.direction==dirn)&(~SIMm.platform.str.contains('original'))]
        h=g[g.ticker!=tk]
        for lab,x in (('with',g),('without',h)):
            bb='btc' if (x.asset=='crypto').all() else 'spy'
            xs=x['x_'+bb] if (x.asset.nunique()==1) else x.x_spy.fillna(x.x_btc)
            rows.append(dict(check=name,policy=PNAME[p],sample=f'{lab} {tk}',N=len(x),mean=x.ret_net.mean()*100,median=x.ret_net.median()*100,hit=(x.ret_net>0).mean()*100,excess_vs_mkt=xs.mean()*100,excess_median=xs.median()*100))
md.append('### D. Named leave-one-ticker-out checks (excess = vs SPY for stocks, vs BTC for crypto)\n'+fmt(pd.DataFrame(rows),['check','policy','sample','N','mean','median','hit','excess_vs_mkt','excess_median']))
# 5. shorts with/without the team's short rule (sim only)
S_=SIMm[SIMm.direction=='SHORT'].copy(); S_['rules']=S_.apply(rulepass_short,axis=1)
rows=[]
for p in ('hold','fsetup','t8'):
    for (src,asset),g in S_[S_.policy==p].groupby(['source','asset']):
        b='spy' if asset=='stock' else 'btc'
        for lab,x in (('all shorts',g),('score>=3 & <SMA200',g[g.rules]) if asset=='stock' else ('(rule: no crypto shorts)',g.iloc[0:0])):
            if len(x)==0: continue
            s=stats(x,b); s.update(src=src,asset=asset,subset=lab,policy=PNAME[p]); rows.append(s)
md.append('### E. SHORTS (independent replay; IAF v8 cannot short) — excess vs SPY/BTC means short beat shorting the market\n'+fmt(pd.DataFrame(rows),['src','asset','subset','policy','N','mean','median','hit','x_spy','x_btc','mean_wo_top1','x_spy_wo_top1','x_spy_wo_top3','flag']))
# 6. reconcile with team's hold-no-stop numbers (stocks, window subset)
H=SIMm[(SIMm.policy=='hold')&(SIMm.direction=='LONG')&(SIMm.in_hold_no_stop_csv==True)]
rows=[]
for (src,asset),g in H.groupby(['source','asset']):
    s=stats(g,'spy' if asset=='stock' else 'btc'); s.update(src=src,asset=asset); rows.append(s)
md.append("### F. Same setups as the team's hold-no-stop CSV (longs flagged in_hold_no_stop_csv), our PIT entry\n"+fmt(pd.DataFrame(rows),['src','asset','N','mean','median','hit','x_spy','x_btc','mean_wo_top1','mean_wo_top3','x_spy_wo_top3','x_btc_wo_top3','top3','flag']))

# 7. Grok crypto longs: full period vs the team's "fair window" (decision 2026-08-12..2026-10-04), all exit policies (sim==IAF for longs)
G=SIMm[(SIMm.group=='Grok crypto')&(SIMm.direction=='LONG')].copy()
G['dec']=pd.to_datetime(G.decision_utc,utc=True)
rows=[]
for lab,x in (('full period',G),('fair window 08-12..10-04',G[(G.dec>='2026-08-12')&(G.dec<'2026-10-05')])):
    for p in POLS:
        for nl,xx in (('all',x[x.policy==p]),('w/o NEAR',x[(x.policy==p)&(x.ticker!='NEAR-USD')])):
            if len(xx)==0: continue
            s=stats(xx,'btc','eth','basket'); s.update(window=lab,policy=PNAME[p],sample=nl); rows.append(s)
md.append('### G. Grok crypto LONGS vs BTC / ETH / basket — full period vs team fair window, all exit policies\n'+fmt(pd.DataFrame(rows),['window','policy','sample','N','tickers','mean','median','hit','x_btc','xmed_btc','x_eth','xmed_eth','x_basket','xmed_basket','x_btc_wo_top1','x_btc_wo_top3','top3','flag']))
# 8. whole rule set: unfiltered scanner vs rule-filtered scanner (longs+shorts), per asset and policy
A_=SIMm.copy(); A_['rules']=A_.apply(lambda r: rulepass_long(r) if r.direction=='LONG' else rulepass_short(r),axis=1)
rows=[]
for asset in ('stock','crypto'):
    b='spy' if asset=='stock' else 'btc'
    for p in POLS:
        g=A_[(A_.asset==asset)&(A_.policy==p)]
        for lab,x in (('unfiltered L+S',g),('rule-filtered L+S',g[g.rules]),('unfiltered longs',g[g.direction=='LONG']),('rule-filtered longs',g[(g.direction=='LONG')&g.rules])):
            if len(x)==0: continue
            s=stats(x,b); s.update(asset=asset,policy=PNAME[p],subset=lab); rows.append(s)
md.append('### H. Whole scanner: unfiltered vs rule-filtered (rules: longs no Grok prebreakout + stock sector uptrend; shorts only stocks with score>=3 & <SMA200; no crypto shorts)\n'+fmt(pd.DataFrame(rows),['asset','policy','subset','N','tickers','mean','median','hit','x_'+'spy','x_btc','mean_wo_top1','mean_wo_top3','flag']))

# 9. Fibonacci-structure exits vs ATR stops vs trailing/hold, on the SAME subset (setups that have a confirmed fib leg)
FP=['hold','t8','atr2_c','atr3_c','fib_T1_c','fib_T2_c','fib_T3_c','fib_scale_c','atr2_i','atr3_i','fib_T1_i','fib_T2_i','fib_T3_i','fib_scale_i']
FN={'hold':'hold, no stop','t8':'trailing 8% (close)','atr2_c':'2xATR stop (close)','atr3_c':'3xATR stop (close)','fib_T1_c':'fib stop + 1.272 tgt (close)','fib_T2_c':'fib stop + 1.618 tgt (close)','fib_T3_c':'fib stop + 2.618 tgt (close)','fib_scale_c':'fib stop + 1/3 at each tgt (close)',
    'atr2_i':'2xATR stop (intraday)','atr3_i':'3xATR stop (intraday)','fib_T1_i':'fib stop + 1.272 tgt (intraday)','fib_T2_i':'fib stop + 1.618 tgt (intraday)','fib_T3_i':'fib stop + 2.618 tgt (intraday)','fib_scale_i':'fib stop + 1/3 at each tgt (intraday)'}
fibids=set(SIMm[SIMm.policy=='fib_T1_c'].setup_id)
FX=SIMm[SIMm.setup_id.isin(fibids)].copy()
FX['rules']=FX.apply(lambda r: rulepass_long(r) if r.direction=='LONG' else rulepass_short(r),axis=1)
segs=[('Grok crypto LONG',lambda g:(g.group=='Grok crypto')&(g.direction=='LONG')),
      ('All stock LONG',lambda g:(g.asset=='stock')&(g.direction=='LONG')),
      ('Rule-filtered stock LONG',lambda g:(g.asset=='stock')&(g.direction=='LONG')&g.rules),
      ('Perplexity stock LONG',lambda g:(g.asset=='stock')&(g.direction=='LONG')&(g.source=='Perplexity')),
      ('Grok stock LONG',lambda g:(g.asset=='stock')&(g.direction=='LONG')&(g.source=='Grok')),
      ('Rule-filtered stock SHORT (score>=3 & <SMA200)',lambda g:(g.asset=='stock')&(g.direction=='SHORT')&g.rules),
      ('All stock SHORT',lambda g:(g.asset=='stock')&(g.direction=='SHORT'))]
rows=[]
for nm,f in segs:
    for p in FP:
        g=FX[(FX.policy==p)]; g=g[f(g)]
        if len(g)==0: continue
        b='btc' if (g.asset=='crypto').all() else 'spy'
        st=stats(g,b); st.update(segment=nm,policy=FN[p],stopped=(g.status=='stopped').mean()*100,target=(g.status=='target').mean()*100,days=g.days.mean()); rows.append(st)
FT=pd.DataFrame(rows); FT['x_mkt']=FT.x_btc.fillna(FT.x_spy) if 'x_btc' in FT else FT.x_spy; FT['x_mkt_wo_top1']=FT.get('x_btc_wo_top1',pd.Series(np.nan,index=FT.index)).fillna(FT.get('x_spy_wo_top1'))
md.append('### I. Fibonacci exits vs ATR stops vs trailing 8% vs hold (same setups with a confirmed zigzag leg; Z=2xATR14 zigzag, 0.5xATR buffer; x_mkt = vs BTC for crypto, vs SPY for stocks)\n'+fmt(FT,['segment','policy','N','tickers','mean','median','hit','x_mkt','mean_wo_top1','x_mkt_wo_top1','top1','stopped','target','days','flag']))

# 10. ATR chandelier TRAILING stops vs hold / fixed ATR / trailing 8%, same setups (those with PIT ATR available)
JP=['hold','t8','atr2_c','atr3_c','chand2_c','chand3_c','chand4_c','atr2_i','atr3_i','chand2_i','chand3_i','chand4_i']
JN={'hold':'hold, no stop','t8':'trailing 8% (close)','atr2_c':'fixed 2xATR (close)','atr3_c':'fixed 3xATR (close)','chand2_c':'chandelier 2xATR (close)','chand3_c':'chandelier 3xATR (close)','chand4_c':'chandelier 4xATR (close)',
    'atr2_i':'fixed 2xATR (intraday)','atr3_i':'fixed 3xATR (intraday)','chand2_i':'chandelier 2xATR (intraday)','chand3_i':'chandelier 3xATR (intraday)','chand4_i':'chandelier 4xATR (intraday)'}
ids=set(SIMm[SIMm.policy=='chand3_c'].setup_id)&set(SIMm[SIMm.policy=='atr2_c'].setup_id)
JX=SIMm[SIMm.setup_id.isin(ids)].copy()
JX['rules']=JX.apply(lambda r: rulepass_long(r) if r.direction=='LONG' else rulepass_short(r),axis=1)
rows=[]
for nm,f in segs:
    for p in JP:
        g=JX[(JX.policy==p)]; g=g[f(g)]
        if len(g)==0: continue
        b='btc' if (g.asset=='crypto').all() else 'spy'
        st=stats(g,b); ex=g[g.status!='open@end']
        st.update(segment=nm,policy=JN[p],exited=len(ex),still_open=int((g.status=='open@end').sum()),stopped=(g.status=='stopped').mean()*100,days=g.days.mean(),days_exited=ex.days.mean() if len(ex) else np.nan,
                  x_mkt=st.get('x_'+b),x_mkt_wo_top1=st.get(f'x_{b}_wo_top1'),x_mkt_wo_top3=st.get(f'x_{b}_wo_top3'))
        rows.append(st)
JT=pd.DataFrame(rows)
md.append('### J. ATR chandelier TRAILING stops (highest close since entry - k*ATR14; ATR & extreme as of previous bar) vs hold / fixed ATR / trailing 8% (same setups; x_mkt = vs SPY stocks, vs BTC crypto; open trades marked at 2026-10-07 close)\n'+fmt(JT,['segment','policy','N','exited','still_open','stopped','mean','median','hit','x_mkt','mean_wo_top1','mean_wo_top3','x_mkt_wo_top1','x_mkt_wo_top3','days','days_exited','flag']))
JT.to_csv(OUT+'chandelier_table.csv',index=False)

# 11. Deeper STRUCTURE stops (no targets) vs hold / fixed 3xATR / chandelier 4xATR — same setups (all variants available)
KP=['hold','atr3_c','chand4_c','st_fib786_c','st_origin05_c','st_origin10_c','st_strail_c','atr3_i','chand4_i','st_fib786_i','st_origin05_i','st_origin10_i','st_strail_i']
KN={'hold':'hold, no stop','atr3_c':'fixed 3xATR (close)','chand4_c':'chandelier 4xATR (close)','st_fib786_c':'(a) below 0.786 - 0.5ATR (close)','st_origin05_c':'(b) below swing origin - 0.5ATR (close)','st_origin10_c':'(c) below swing origin - 1.0ATR (close)','st_strail_c':'(d) structure trail, confirmed higher-lows (close)',
    'atr3_i':'fixed 3xATR (intraday)','chand4_i':'chandelier 4xATR (intraday)','st_fib786_i':'(a) below 0.786 - 0.5ATR (intraday)','st_origin05_i':'(b) below swing origin - 0.5ATR (intraday)','st_origin10_i':'(c) below swing origin - 1.0ATR (intraday)','st_strail_i':'(d) structure trail, confirmed higher-lows (intraday)'}
AP=pd.read_csv(OUT+'struct_atr_pct.csv').drop_duplicates('setup_id').set_index('setup_id').atr_pct
kid=set(SIMm.setup_id)
for p in ['st_fib786_c','st_origin05_c','st_origin10_c','atr3_c','chand4_c']: kid&=set(SIMm[SIMm.policy==p].setup_id)
KX=SIMm[SIMm.setup_id.isin(kid)].copy()
KX['rules']=KX.apply(lambda r: rulepass_long(r) if r.direction=='LONG' else rulepass_short(r),axis=1)
KX['sd']=KX.stop_dist if 'stop_dist' in KX else np.nan
KX.loc[KX.policy.str.startswith('atr3'),'sd']=3*KX.setup_id.map(AP); KX.loc[KX.policy.str.startswith('chand4'),'sd']=4*KX.setup_id.map(AP)
rows=[]
for nm,f in segs:
    for p in KP:
        g=KX[(KX.policy==p)]; g=g[f(g)]
        if len(g)==0: continue
        b='btc' if (g.asset=='crypto').all() else 'spy'
        st=stats(g,b)
        st.update(segment=nm,policy=KN[p],exited=int((g.status!='open@end').sum()),still_open=int((g.status=='open@end').sum()),stopped=(g.status=='stopped').mean()*100,
                  stop_med=g.sd.median(),stop_p25=g.sd.quantile(.25),days=g.days.mean(),fallback=(g.fallback.mean()*100 if 'fallback' in g and g.fallback.notna().any() else np.nan),
                  x_mkt=st.get('x_'+b),x_mkt_wo_top1=st.get(f'x_{b}_wo_top1'),x_mkt_wo_top3=st.get(f'x_{b}_wo_top3'))
        rows.append(st)
KT=pd.DataFrame(rows); KT.to_csv(OUT+'structure_table.csv',index=False)
md.append('### K. Deeper STRUCTURE stops, no targets (strict PIT 2xATR14 zigzag; leg = last confirmed swing high + its origin low; mirrored for shorts) vs hold / fixed 3xATR / chandelier 4xATR (same setups; stop_med/p25 = initial stop distance % of entry; fallback% = structure level already breached at entry, next deeper confirmed pivot used)\n'+fmt(KT,['segment','policy','N','exited','still_open','stopped','stop_med','stop_p25','mean','median','hit','x_mkt','mean_wo_top1','mean_wo_top3','x_mkt_wo_top1','x_mkt_wo_top3','days','fallback','flag']))

# 12. 4xATR stops + Fib / Elliott profit targets vs hold / fixed 3xATR / chandelier 4xATR (same setups as table K)
LV={'T1':'1.272 ext full','T2':'1.618 ext full','T3':'2.618 ext full','TS':'1/3 at each ext','EW':'Elliott w3/w5 target','HY3':'1/3 at 1.618, rest chandelier','HY2':'1/2 at 1.618, rest chandelier'}
LP=[]; LN={}
for mode,mn in (('c','close'),('i','intraday')):
    for b0,b1 in (('hold','hold, no stop'),('atr3','fixed 3xATR, no target'),('chand4','chandelier 4xATR, no target')):
        pp=b0 if b0=='hold' else f'{b0}_{mode}'
        if pp in LP: continue
        LP.append(pp); LN[pp]=b1+('' if b0=='hold' else f' ({mn})')
    for sv,svn in (('fx','fixed 4xATR'),('ch','chandelier 4xATR')):
        for v in ('T1','T2','T3','TS','EW','HY3','HY2'):
            if sv=='fx' and v.startswith('HY'): continue
            pp=f'tg_{sv}_{v}_{mode}'; LP.append(pp); LN[pp]=f'{svn} + {LV[v]} ({mn})'
lid=kid & set(SIMm[SIMm.policy=='tg_ch_T1_c'].setup_id)
LX=SIMm[SIMm.setup_id.isin(lid)].copy()
LX['rules']=LX.apply(lambda r: rulepass_long(r) if r.direction=='LONG' else rulepass_short(r),axis=1)
rows=[]
for nm,f in segs:
    for p in LP:
        g=LX[(LX.policy==p)]; g=g[f(g)]
        if len(g)==0: continue
        b='btc' if (g.asset=='crypto').all() else 'spy'
        st=stats(g,b); istg=p.startswith('tg_')
        rch=g[g.reached==True] if istg else g.iloc[0:0]
        st.update(segment=nm,policy=LN[p],stop_x=int((g.status=='stopped').sum()),target_x=int((g.status=='target').sum()),open_=int((g.status=='open@end').sum()),
                  has_tgt=(g.has_target.mean()*100 if istg else np.nan),reached_pct=(g.reached.mean()*100 if istg else np.nan),
                  kept_going=((rch.mark_ret>rch.ret_net).mean()*100 if len(rch) else np.nan),left_pp=(rch.left.mean()*100 if len(rch) else np.nan),
                  days=g.days.mean(),x_mkt=st.get('x_'+b),x_mkt_wo_top1=st.get(f'x_{b}_wo_top1'),x_mkt_wo_top3=st.get(f'x_{b}_wo_top3'))
        rows.append(st)
LT=pd.DataFrame(rows); LT.to_csv(OUT+'targets_table.csv',index=False)
md.append('### L. 4xATR stops + Fibonacci / Elliott profit targets (strict PIT, same legs/setups as K) vs hold / fixed 3xATR / chandelier 4xATR. stop_x/target_x/open_ = trades whose final exit was stop / target / still open (marked 2026-10-07); has_tgt = % with a valid target beyond entry; reached = % that touched (first) target; kept_going = % of target-reached trades where holding the whole position to 2026-10-07 would have been worth more; left_pp = avg pp given up vs holding, over target-reached trades\n'+fmt(LT,['segment','policy','N','stop_x','target_x','open_','has_tgt','reached_pct','kept_going','left_pp','mean','median','hit','x_mkt','mean_wo_top1','mean_wo_top3','x_mkt_wo_top1','x_mkt_wo_top3','days','flag']))
open(OUT+'analysis_tables.md','w').write('\n\n'.join(md))
IAF.to_csv(OUT+'iaf_trades_enriched.csv',index=False); SIM.to_csv(OUT+'sim_trades_enriched.csv',index=False)
print('\n\n'.join(md))
