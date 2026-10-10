import pandas as pd, numpy as np, json
from scipy.stats import fisher_exact
F=pd.read_pickle('features2.pkl')
F['log_mcap']=np.log10(F.mcap.astype(float))
F['ret3_scan']=F['ret3_to_open'].fillna(F['ret3'])
# ---------- compliance
def comp(f):
    s=f.strategy; d=f.dir; ch={}
    if pd.isna(f.get('rsi14')): return {}, None
    if s=='Grok momentum':
        if d=='LONG':
            ch['|3d move|>=5% up (incl. pre-mkt gap)']=f.ret3_scan>=0.05
            ch['RVOL signal day>=1.2 or 5d vol>=1.2x20d']=(f.vol_vs20>=1.2) or (f.vol5_vs20>=1.2)
            ch['above SMA20']=f.vs_sma20>0
            ch['not >30% above SMA20']=f.vs_sma20<=0.30
            ch['not >100% in 3d']=f.ret3_scan<1.0
        else:
            ch['3d move>=5% either way']=abs(f.ret3_scan)>=0.05
            ch['RVOL>=1.2 (day or 5d)']=(f.vol_vs20>=1.2) or (f.vol5_vs20>=1.2)
            ch['exhaustion: RSI>=65 or >=2ATR above SMA20, or weakness: below SMA20']=(f.rsi14>=65) or (f.ext_sma20_atr>=2) or (f.vs_sma20<0)
    elif s=='Grok near-low':
        if d=='LONG':
            ch['volume/catalyst evidence: RVOL>=1.5 or |gap|>=5% or 5d vol>=1.3x']=(f.vol_vs20>=1.5) or (abs(f.gap_day1_open)>=0.05) or (f.vol5_vs20>=1.3)
            ch['not parabolic: RSI<75']=f.rsi14<75
            ch['not >100% in 3d']=f.ret3_scan<1.0
        else:
            ch['exhaustion: 5d>=+15% or RSI>=70 or gap>=+10%, or breakdown below SMA50']=(f.ret5>=0.15) or (f.rsi14>=70) or (f.gap_day1_open>=0.10) or (f.vs_sma50<0)
            ch['volume evidence: RVOL>=1.5 or 5d vol>=1.3x']=(f.vol_vs20>=1.5) or (f.vol5_vs20>=1.3)
    elif s=='Grok prebreakout':
        ch['price>=$5']=f.close_asof>=5
        ch['avg volume>500k']=f.avgvol20>5e5
        ch['MCAP>$2B']=(f.mcap or 0)>2e9
        ch['near 52w low (<=15% above)']=f.pct_from_52w_low<=0.15
        if d=='LONG': ch['RSI<=40 (oversold/depressed)']=f.rsi14<=40
        else: ch['below SMA50']=f.vs_sma50<0
    elif s=='Bot v2.8':
        ch['price>=$5']=f.close_asof>=5; ch['MCAP>=$1.5B']=(f.mcap or 0)>=1.5e9; ch['ADV>$14M']=f.adv_usd20>14e6
        if d=='LONG':
            ch['not >4xATR above SMA20']=f.ext_sma20_atr<=4
            ch['not fighting 252 bars: >SMA200 or SMA200 rising']=(f.vs_sma200>0) if pd.notna(f.vs_sma200) else True
        else:
            ch['exhaustion (>=2ATR above SMA20 or RSI>=65) or downtrend (<SMA200)']=(f.ext_sma20_atr>=2) or (f.rsi14>=65) or ((f.vs_sma200<0) if pd.notna(f.vs_sma200) else False)
        ch['no earnings within 5 sessions (~7 days)']=not (pd.notna(f.days_to_earn) and f.days_to_earn<=7)
    elif s=='Original sheet (annual low)':
        ch['near 52w low (<=15% above)']=f.pct_from_52w_low<=0.15
    else: return {}, None
    return ch, all(bool(v) for v in ch.values())
C=[];CO=[]
for i,f in F.iterrows():
    ch,ok=comp(f); CO.append(ok); C.append('; '.join(f"{'✓' if v else '✗'} {k}" for k,v in ch.items()))
    for k,v in ch.items(): F.loc[i,'chk: '+k]=int(bool(v))
F['compliant']=[None if o is None else int(o) for o in CO]; F['compliance_detail']=C
# name-based checks (what the label promises)
F['name_near_52w_low_15']=(F.pct_from_52w_low<=0.15).astype('Int64')
F['name_prebreakout']=((F.from_60d_high>=-0.05)&(F.range20_pct<=0.12)).astype('Int64')
F.to_pickle('features3.pkl')
def stats(d):
    res=d[d.status=='resolved']; dat=d[d.ret_rule.notna()&d.status.isin(['resolved','open'])]
    w=int(res.win.sum()); l=len(res)-w
    return dict(n=len(d[d.status.isin(['resolved','open'])]),n_res=len(res),tp1=w,stop=l,win=(w/len(res) if len(res) else None),avg_rule=dat.ret_rule.mean() if len(dat) else None,avg_last=dat.ret_last.mean() if len(dat) else None,small=len(res)<10)
if __name__=='__main__':
    pd.set_option('display.width',250); pd.set_option('display.max_columns',30)
    for (s,d),g in F[F.compliant.notna()].groupby(['strategy','dir']):
        a=stats(g[g.compliant==1]); b=stats(g[g.compliant==0])
        print(f"{s} {d}: compliant {g.compliant.mean():.0%} of {len(g)} | C: {a['tp1']}/{a['stop']} avg {a['avg_rule']} | NC: {b['tp1']}/{b['stop']} avg {b['avg_rule']}")
        cols=[c for c in F.columns if c.startswith('chk: ')]
        print('   ', {c[5:]:round(g[c].mean(),2) for c in cols if g[c].notna().any()})
    print(F.groupby('strategy')[['name_near_52w_low_15','name_prebreakout']].mean())
