"""Prepare point-in-time setup table + OHLCV frames for the IAF backtests.
Read-only use of /workspace/tracker and /workspace/notes-analysis data.
Rule features reimplement the team's definitions from /workspace/notes-analysis/analyze.py
('20 method' checklist ck_score, SMA200, sector ETF uptrend) computed strictly on bars <= cutoff."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import json, numpy as np, pandas as pd
OUT=(_SCANNER_ROOT + '/trading-frameworks-eval/iaf/')
S=pd.read_csv((_SCANNER_ROOT + '/tracker/setups-point-in-time-2026-10-08.csv'))
P=pd.read_pickle((_SCANNER_ROOT + '/tracker/prices_all.pkl')); E=pd.read_pickle((_SCANNER_ROOT + '/notes-analysis/etf.pkl'))
C=pd.read_pickle((_SCANNER_ROOT + '/notes-analysis/crypto_daily_long.pkl'))
SEC=json.load(open((_SCANNER_ROOT + '/notes-analysis/sectors.json')))
for _t,_s in (('CMCSA','Communication Services'),('FISV','Technology')):
    if not (SEC.get(_t) or {}).get('sector'): SEC[_t]={'sector':_s}  # missing in sectors.json; standard Yahoo sectors
SECMAP={'Technology':'XLK','Financial Services':'XLF','Energy':'XLE','Healthcare':'XLV','Consumer Cyclical':'XLY','Consumer Defensive':'XLP','Industrials':'XLI','Basic Materials':'XLB','Utilities':'XLU','Real Estate':'XLRE','Communication Services':'XLC'}
def ser(D,t):
    if t not in D.columns.get_level_values(0): return None
    df=D[t][['Open','High','Low','Close','Volume']].dropna(subset=['Open','Close']).copy(); df.index=pd.to_datetime(df.index); return df
def get(t, crypto):
    if crypto: return ser(C,t)
    x=ser(P,t)
    return x if x is not None else ser(E,t)
def cci(df,n=20):
    tp=(df.High+df.Low+df.Close)/3; m=tp.rolling(n).mean(); md=tp.rolling(n).apply(lambda a: np.mean(np.abs(a-a.mean())),raw=True); return (tp-m)/(0.015*md)
cache={}
def prep(t,crypto):
    k=(t,crypto)
    if k in cache: return cache[k]
    x=get(t,crypto)
    if x is not None:
        x['SMA20']=x.Close.rolling(20).mean(); x['SMA200']=x.Close.rolling(200).mean(); x['CCI']=cci(x)
    cache[k]=x; return x
def feats(x,i,sgn):
    f={}
    if i<25: return f
    c=x.Close; Cc=c.iloc[i]; o,h,l=x.Open.iloc[i],x.High.iloc[i],x.Low.iloc[i]; po,pc=x.Open.iloc[i-1],c.iloc[i-1]
    ret=lambda k: Cc/c.iloc[i-k]-1
    rng=h-l; body=abs(Cc-o); clv=(Cc-l)/rng if rng>0 else 0.5
    eb=int(pc<po and Cc>o and o<=pc and Cc>=po); es=int(pc>po and Cc<o and o>=pc and Cc<=po)
    lo_sh=min(o,Cc)-l; up_sh=h-max(o,Cc)
    ham=int(rng>0 and lo_sh>=2*body and up_sh<=max(body,0.1*rng)); star=int(rng>0 and up_sh>=2*body and lo_sh<=max(body,0.1*rng))
    v=x.Volume; den=v.iloc[i-24:i-4].mean(); vol5_20=v.iloc[i-4:i+1].mean()/den if den>0 else np.nan
    cc=x.CCI.iloc[i]; cchg=x.CCI.iloc[i]-x.CCI.iloc[i-3]
    bull=(Cc>o and clv>=0.5) or eb or ham; bear=(Cc<o and clv<=0.5) or es or star
    ck=[int(sgn*ret(20)>0 and sgn*ret(5)>0), int(bull if sgn==1 else bear),
        int(vol5_20>1 and sgn*ret(5)>0) if not np.isnan(vol5_20) else 0,
        int(sgn*(Cc-x.SMA20.iloc[i])>0), int(abs(cc)<100 and sgn*cchg>0)]
    f['ck_score']=sum(ck); f['asof_close']=Cc
    s200=x.SMA200.iloc[i]; f['below_sma200']=(int(Cc<s200) if not np.isnan(s200) else np.nan); f['vs_sma200']=Cc/s200-1 if not np.isnan(s200) else np.nan
    return f
rows=[]
for _,r in S.iterrows():
    d=dict(setup_id=r.setup_id, in_main=bool(r.in_main_sheet), dup=str(r.dup_not_counted)=='True', platform=r.platform, model=r.model,
           automation=r.automation, ticker=r.ticker, asset=('crypto' if r.asset_class=='crypto' else 'stock'), asset_class=r.asset_class,
           direction=r.direction, entry_alert=r.entry, stop=r.stop, tp1=r.tp1, alert_date=r.alert_date, time_source=r.time_source,
           alert_time_utc=r.alert_time_utc, cutoff_bar_date=r.cutoff_bar_date, cutoff_minute_utc=r.cutoff_minute_utc)
    p=str(r.platform)
    d['source']='Bot' if p.startswith('Bot') else 'Grok' if p.upper().startswith('GROK') else 'Perplexity' if p.startswith('Perplexity') else 'Ilan charts'
    crypto=d['asset']=='crypto'
    x=prep(r.ticker,crypto) if isinstance(r.ticker,str) else None
    d['has_data']=x is not None
    # decision time = earliest moment the alert is certainly known
    if isinstance(r.alert_time_utc,str) and r.time_source in ('exact','schedule','ui_log'):
        dec=pd.Timestamp(r.alert_time_utc.replace('Z','')) 
    else:
        dec=pd.Timestamp(r.alert_date)+pd.Timedelta(hours=23,minutes=59)  # date only: assume end of alert day (no price lookahead)
    d['decision_utc']=dec
    # information cutoff (last complete daily bar usable for rules)
    if crypto:
        cm=r.cutoff_minute_utc if isinstance(r.cutoff_minute_utc,str) else (r.alert_date+'T00:00Z')
        cmt=pd.Timestamp(cm.replace('Z',''))
        if r.time_source=='ui_log': cmt=min(cmt, dec-pd.Timedelta(minutes=70))
        last_bar=(cmt.normalize()-pd.Timedelta(days=1))   # UTC daily bar D completes at D+1 00:00
        d['info_cutoff_utc']=cmt
    else:
        last_bar=pd.Timestamp(r.cutoff_bar_date) if isinstance(r.cutoff_bar_date,str) else pd.Timestamp(r.alert_date)-pd.Timedelta(days=1)
        d['info_cutoff_utc']=last_bar+pd.Timedelta(hours=20)
    d['rule_bar_date']=last_bar
    if x is not None and r.direction in ('LONG','SHORT'):
        sgn=1 if r.direction=='LONG' else -1
        i=int((x.index<=last_bar).sum())-1
        d['rule_bar_actual']=x.index[i] if i>=0 else None
        d.update(feats(x,i,sgn))
        if not crypto:
            sec=SEC.get(r.ticker,{}).get('sector'); d['sector']=sec; etf=SECMAP.get(sec)
            if r.asset_class=='etf': d['sector']='ETF'
            if etf:
                ee=ser(E,etf); ee=ee[ee.index<=last_bar].Close; m50=ee.rolling(50).mean()
                d['sector_etf']=etf
                if len(ee)<61: print('WARN sector short', r.setup_id, r.ticker, last_bar, len(ee)); continue_flag=True
                else: d['sector_up']=int(ee.iloc[-1]>m50.iloc[-1] and m50.iloc[-1]>m50.iloc[-11])
    rows.append(d)
D=pd.DataFrame(rows)
D.to_pickle(OUT+'setups_prepared.pkl'); D.to_csv(OUT+'setups_prepared.csv',index=False)
print(D.shape); print(D.groupby(['in_main','dup','has_data']).size())
m=D[D.in_main & ~D.dup & D.has_data]
print(m.groupby(['source','asset','direction']).size())
print('sector_up null (stocks):', m[(m.asset=='stock')].sector_up.isna().sum(), sorted(set(m[(m.asset=='stock')&m.sector_up.isna()].ticker))[:80])
print('ck_score null:', m.ck_score.isna().sum(), 'below_sma200 null:', m.below_sma200.isna().sum())
# save frames for backtest
frames={}
for (t,cr),x in cache.items():
    if x is not None: frames[(t,cr)]=x[['Open','High','Low','Close','Volume']]
pd.to_pickle(frames, OUT+'frames.pkl')
