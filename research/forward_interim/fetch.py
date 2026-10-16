import yfinance as yf, pandas as pd
T=['MU','INTC','MRK','DE','COP','SBUX','CMCSA','NKE','UBER','HON','MRVL','ORCL','XOM','GOOGL','KO','AMGN','T','SPY','BTC-USD','UNI7083-USD','LINK-USD']
z=yf.download(T,start='2026-10-01',interval='1d',auto_adjust=False,progress=False,group_by='ticker')
z.to_pickle('px.pkl')
for t in ['MU','SPY','UNI7083-USD']: print(t, z[t][['Open','High','Low','Close']].round(3).tail(8))
