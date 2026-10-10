import yfinance as yf, pandas as pd, json
T=['PANW','JPM','AVGO','AMD','ABBV','CRM','META','WMT','DE','SNDK','NOW','HD','XOM','ADBE','SBUX','KO','BAC','VLO','GOLD','CVX','FCX','MET','GILD','TMO','PLTR','CRWD','NEM','SHOP','MRK','AMGN','COIN']
d=yf.download(T,start='2026-07-01',end='2026-10-01',group_by='ticker',auto_adjust=False,progress=False,threads=True)
d.to_pickle('tracker/prices.pkl')
for t in T:
    df=d[t].dropna(how='all')
    print(t,len(df),df.index.min().date() if len(df) else None,df.index.max().date() if len(df) else None, df['Close'].iloc[-1] if len(df) else None)
info={}
for t in T:
    try:
        fi=yf.Ticker(t).fast_info
        info[t]={'mcap':fi.get('marketCap') if hasattr(fi,'get') else fi.market_cap}
    except Exception as e:
        info[t]={'err':str(e)}
json.dump(info,open('tracker/info.json','w'),indent=1,default=str)
print(info)
