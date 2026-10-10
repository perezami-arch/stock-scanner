import yfinance as yf, pandas as pd, numpy as np
t='BBAI'
df=yf.download(t,start='2026-06-01',end='2026-10-01',auto_adjust=False,progress=False)
df.columns=[c[0] if isinstance(c,tuple) else c for c in df.columns]
fi=yf.Ticker(t).fast_info
print(df.loc['2026-08-28':'2026-09-10'].round(3)); print(fi.market_cap, fi.last_price)
entry=2.92; post=df[df.index>=pd.Timestamp('2026-09-07')].iloc[:20]
closes=post['Close'].tolist()
cum=[x/entry-1 for x in closes]; daily=[]; p=entry
for x in closes: daily.append(x/p-1); p=x
best=-9;opt=None;idx=list(post.index)
for i in range(len(idx)):
    for j in range(i+1,len(idx)):
        g=post['High'].iloc[j]/post['Low'].iloc[i]-1
        if g>best: best=g; opt=(idx[i],idx[j],post['Low'].iloc[i],post['High'].iloc[j],j-i,g)
h,l,c=df['High'],df['Low'],df['Close']; tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
ref=df[df.index<pd.Timestamp('2026-09-07')].index[-1]
atr=float(tr.rolling(14).mean().loc[ref]/c.loc[ref])
mfe=post['High'].max()/entry-1; mae=post['Low'].min()/entry-1
r=dict(ticker=t,ref=ref,ref_close=float(c.loc[ref]),atr_calc=atr,cum=cum,daily=daily,ndays=len(post),opt=opt,mfe=mfe,mae=mae,
  lo=(post['Low'].idxmin(),post['Low'].min()),hi=(post['High'].idxmax(),post['High'].max()),first=post.index[0],last=post.index[-1],
  mcap_now=fi.market_cap)
pd.to_pickle(r,'ilan_bbai.pkl')
print({k:v for k,v in r.items() if k not in('cum','daily')}); print([round(x*100,2) for x in cum])
