import yfinance as yf,pandas as pd,json
d=pd.read_csv('/tmp/st/scanner-tool-eval/setups_prepared.csv')
st=sorted(d[d.asset=='stock'].ticker.unique().tolist())
E2=['XLK','XLY','XLC','XLF','XLI','XLE','XLB','XLU','XLP','XLV','XLRE','SMH','GLD','^VIX','SPY','BTC-USD']
z=yf.download(st+E2,start='2025-01-01',end='2026-10-16',auto_adjust=True,progress=False,threads=False)['Close']
z.to_pickle('close.pkl');print(z.shape, z.columns[z.isna().all()].tolist())
print(sorted(set(json.load(open('/tmp/st/scanner-momentum-cache/sector_map.json')).values())))
print(len(st), len(set(st)-set(json.load(open('/tmp/st/scanner-momentum-cache/sector_map.json')))))
