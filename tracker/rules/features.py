import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import sys; sys.path.insert(0,(_SCANNER_ROOT + '/tracker'))
import pandas as pd, numpy as np, json
from stats3 import rows_counted
H=pd.read_pickle((_SCANNER_ROOT + '/tracker/rules/hist.pkl')); M=json.load(open((_SCANNER_ROOT + '/tracker/rules/meta.json')))
def ser(t):
    df=H[t].dropna(subset=['Close']).copy(); df.index=pd.to_datetime(df.index); return df
def rsi(c,n=14):
    d=c.diff(); up=d.clip(lower=0).ewm(alpha=1/n,adjust=False).mean(); dn=(-d.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean()
    return 100-100/(1+up/dn)
def atr(df,n=14):
    pc=df['Close'].shift(); tr=pd.concat([df['High']-df['Low'],(df['High']-pc).abs(),(df['Low']-pc).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/n,adjust=False).mean()
SPY,QQQ=ser('SPY'),ser('QQQ')
STRAT={'near-low':'Grok near-low','prebreakout':'Grok prebreakout','momentum':'Grok momentum'}
def strat(r):
    if r['source']=='grok': return STRAT[r['cat']]
    return {'bot':'Bot v2.8','orig':'Original sheet (annual low)','ilan':'Ilan charts'}[r['source']]
def mcb(x):
    if x is None: return None
    return '<10B' if x<10e9 else '10-50B' if x<50e9 else '50-200B' if x<200e9 else '>200B'
out=[]
for r in rows_counted:
    t=r['ticker']; f=dict(strategy=strat(r),source=r['source'],ticker=t,alert_date=r['alert_date'],dir=r['dir'],outcome=r['outcome'],
        status=('resolved' if r['outcome'] in('TP1','סטופ') else 'open' if r['outcome']=='פתוח' else 'other'),
        win=(1 if r['outcome']=='TP1' else 0 if r['outcome']=='סטופ' else None),
        ret_rule=r.get('rule'),ret_last=(float(r['cum'][-1]) if r['cum'] else None),ndays=r['ndays'],mfe=r['mfe'],mae=r['mae'],
        entry=r['entry'],sl=r['sl'],tp1=r['tps'][0],score=r.get('score'),rank=r.get('rank'),grok_cat=r.get('cat'),
        conflict=1 if r.get('_conf') else 0,conflict_note='; '.join(r['_conf']) if r.get('_conf') else '',dupnote=r.get('dupnote'),
        mcap=r.get('mcap_used'),row=r.get('_row'))
    f['mcap_bucket']=mcb(f['mcap'])
    m=M.get(t,{}); f['sector']=m.get('sector'); f['industry']=m.get('industry')
    if not r['alert_date'] or t not in H.columns.get_level_values(0): out.append(f); continue
    df=ser(t); A=pd.Timestamp(r['alert_date']); h=df[df.index<A]; nx=df[df.index>=A]
    if len(h)<30: out.append(f); continue
    c=h['Close']; C=c.iloc[-1]; D=h.index[-1]; f['asof']=str(D.date()); f['bars']=len(h)
    n=min(252,len(h)); f['hist_short']=1 if len(h)<252 else 0
    lo52=h['Low'].iloc[-n:].min(); hi52=h['High'].iloc[-n:].max()
    f['pct_from_52w_low']=C/lo52-1; f['pct_from_52w_high']=C/hi52-1
    f['rsi14']=float(rsi(c).iloc[-1])
    for k in (20,50,150,200):
        if len(c)>=k: f[f'vs_sma{k}']=C/c.rolling(k).mean().iloc[-1]-1
    for k in (50,150):
        s=c.rolling(k).mean()
        if len(c)>=k+20: f[f'sma{k}_slope20']=s.iloc[-1]/s.iloc[-21]-1
    v=h['Volume']
    f['vol_vs20']=v.iloc[-1]/v.iloc[-21:-1].mean(); f['vol_vs50']=v.iloc[-1]/v.iloc[-51:-1].mean() if len(v)>51 else None
    f['vol5_vs20']=v.iloc[-5:].mean()/v.iloc[-25:-5].mean(); f['vol5_vs50']=v.iloc[-5:].mean()/v.iloc[-55:-5].mean() if len(v)>55 else None
    a=atr(h).iloc[-1]; f['atr_pct']=a/C; f['atr']=a
    for k in (1,3,5,20,60):
        if len(c)>k: f[f'ret{k}']=C/c.iloc[-1-k]-1
    f['from_20d_high']=C/h['High'].iloc[-20:].max()-1; f['from_20d_low']=C/h['Low'].iloc[-20:].min()-1
    f['from_60d_high']=C/h['High'].iloc[-60:].max()-1; f['from_60d_low']=C/h['Low'].iloc[-60:].min()-1
    f['range20_pct']=(h['High'].iloc[-20:].max()-h['Low'].iloc[-20:].min())/C
    f['range_contraction']=((h['High'].iloc[-10:].max()-h['Low'].iloc[-10:].min())/(h['High'].iloc[-60:].max()-h['Low'].iloc[-60:].min())) if len(h)>=60 else None
    f['ext_sma20_atr']=(C-c.rolling(20).mean().iloc[-1])/a
    f['adv_usd20']=float((c*v).iloc[-20:].mean()); f['avgvol20']=float(v.iloc[-20:].mean()); f['close_asof']=float(C)
    if len(nx):
        O=nx['Open'].iloc[0]; f['gap_day1_open']=O/C-1; f['ret3_to_open']=O/c.iloc[-4]-1 if len(c)>3 else None
    for nm,ix in (('spy',SPY),('qqq',QQQ)):
        hh=ix[ix.index<A]['Close']; f[f'{nm}_above_sma50']=int(hh.iloc[-1]>hh.rolling(50).mean().iloc[-1]); f[f'{nm}_ret5']=hh.iloc[-1]/hh.iloc[-6]-1
    ed=sorted(pd.Timestamp(x) for x in m.get('earn',[]))
    fut=[x for x in ed if x>=A]; past=[x for x in ed if x<A]
    f['days_to_earn']=(fut[0]-A).days if fut else None
    f['days_since_earn']=(A-past[-1]).days if past else None
    f['earn_within_hold']=None
    e,s_,tp=r['entry'],r['sl'],r['tps'][0]
    if e and s_ and tp and abs(e-s_)>0:
        f['rr_tp1']=abs(tp-e)/abs(e-s_); f['stop_atr']=abs(e-s_)/a; f['tp1_atr']=abs(tp-e)/a; f['stop_pct']=abs(e-s_)/e; f['tp1_pct']=abs(tp-e)/e
        f['stop_wrong_side']=int((r['dir']=='LONG' and s_>=e) or (r['dir']=='SHORT' and s_<=e))
    if e: f['entry_vs_asof_close']=e/C-1
    out.append(f)
F=pd.DataFrame(out); F.to_pickle((_SCANNER_ROOT + '/tracker/rules/features.pkl'))
print(F.shape); print(F.groupby(['strategy','dir','status']).size())
print(F[['pct_from_52w_low','rsi14','vol_vs20','rr_tp1','stop_atr','days_to_earn']].describe().T)
