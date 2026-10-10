import pandas as pd, numpy as np, json
F=pd.read_pickle('features.pkl'); Mx=pd.read_pickle('macro.pkl')
def S(t): s=Mx[t]['Close'].dropna(); s.index=pd.to_datetime(s.index); return s
cnn=json.load(open('cnn_fg.json'))['fear_and_greed_historical']['data']
CNN=pd.Series({pd.Timestamp(int(p['x']),unit='ms').normalize():p['y'] for p in cnn}).sort_index()
cf=json.load(open('crypto_fng.json'))['data']
CF=pd.Series({pd.Timestamp(int(p['timestamp']),unit='s').normalize():int(p['value']) for p in cf}).sort_index()
CF.to_csv('crypto_fng_daily.csv',header=['value'])
CNN.to_csv('cnn_fg_daily.csv',header=['score'])
print('CNN',CNN.index[0].date(),CNN.index[-1].date(),len(CNN),'crypto',CF.index[0].date(),CF.index[-1].date(),len(CF))
SEC={'Technology':'XLK','Financial Services':'XLF','Energy':'XLE','Healthcare':'XLV','Consumer Cyclical':'XLY','Consumer Defensive':'XLP','Industrials':'XLI','Basic Materials':'XLB','Utilities':'XLU','Real Estate':'XLRE','Communication Services':'XLC'}
vix,v3,dxy,tnx,irx,two,spx,spy,qqq=[S(t) for t in ['^VIX','^VIX3M','DX-Y.NYB','^TNX','^IRX','2YY=F','^GSPC','SPY','QQQ']]
def asof(s,A):
    x=s[s.index<A]; return x
rows=[]
for i,f in F.iterrows():
    g={}
    if isinstance(f.alert_date,str):
        A=pd.Timestamp(f.alert_date)
        x=asof(CNN,A); g['cnn_fg']=x.iloc[-1] if len(x) else None; g['cnn_fg_date']=str(x.index[-1].date()) if len(x) else None
        x=asof(CF,A); g['crypto_fg']=x.iloc[-1] if len(x) else None
        x=asof(vix,A); g['vix']=x.iloc[-1]; g['vix_vs_50d']=x.iloc[-1]/x.iloc[-50:].mean()-1
        y=asof(v3,A); g['vix_term']=x.iloc[-1]/y.iloc[-1] if len(y) else None  # >1 = backwardation
        x=asof(dxy,A); g['dxy']=x.iloc[-1]; g['dxy_ret20']=x.iloc[-1]/x.iloc[-21]-1
        t10=asof(tnx,A); t2=asof(two,A); t3m=asof(irx,A)
        g['us10y']=t10.iloc[-1]; g['us2y']=t2.iloc[-1]; g['us3m']=t3m.iloc[-1]; g['spread_10y_2y']=t10.iloc[-1]-t2.iloc[-1]
        g['us10y_chg20_bp']=(t10.iloc[-1]-t10.iloc[-21])*100
        x=asof(spx,A); g['spx_vs_ma125']=x.iloc[-1]/x.iloc[-125:].mean()-1
        for nm,s in (('spy',spy),('qqq',qqq)):
            x=asof(s,A); g[f'{nm}_vs_sma50']=x.iloc[-1]/x.iloc[-50:].mean()-1; g[f'{nm}_vs_sma200']=x.iloc[-1]/x.iloc[-200:].mean()-1
        e=SEC.get(f.sector); g['sector_etf']=e
        if e:
            x=asof(S(e),A); g['sector_above_sma50']=int(x.iloc[-1]>x.iloc[-50:].mean()); g['sector_vs_sma50']=x.iloc[-1]/x.iloc[-50:].mean()-1; g['sector_ret20']=x.iloc[-1]/x.iloc[-21]-1
    rows.append(g)
G=pd.DataFrame(rows,index=F.index); F=pd.concat([F,G],axis=1); F.to_pickle('features2.pkl')
print(F.groupby('alert_date')[['cnn_fg','crypto_fg','vix','vix_term','spread_10y_2y','spy_vs_sma50']].first().tail(20).round(2))
print(F.sector_etf.isna().sum(), F[F.sector_etf.isna()].ticker.tolist())
