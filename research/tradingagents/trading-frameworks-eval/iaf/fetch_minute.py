"""First tradable 1-min bar at/after the decision time, from Alpaca market data (keys from env, never printed).
Stocks: SIP feed, regular session only (13:30-20:00 UTC; whole sample Jul-Oct 2026 is EDT). Crypto: v1beta3 us bars.
Writes minute_entries.csv (setup_id, entry_minute_utc, minute_open, minute_close, n_bars_window, note)."""
import os, time, json, requests, pandas as pd, numpy as np
OUT='/workspace/trading-frameworks-eval/iaf/'
H={'APCA-API-KEY-ID':os.environ['ALPACA_API_KEY_ID'],'APCA-API-SECRET-KEY':os.environ['ALPACA_API_SECRET_KEY']}
D=pd.read_pickle(OUT+'setups_prepared.pkl')
S=D[D.has_data & D.decision_utc.notna() & D.direction.isin(['LONG','SHORT']) & D.time_source.isin(['exact','schedule','ui_log'])]
cache=OUT+'minute_entries.csv'
if os.path.exists(cache):
    _c=pd.read_csv(cache); _c=_c[_c.minute_open.notna() | (_c.note=='no bars')]; _c.to_csv(cache,index=False); done=set(_c.setup_id)
else: done=set()
COLS=['setup_id','entry_minute_utc','minute_open','minute_close','lag_min','note']
def flush():
    global rows
    if not rows: return
    new=pd.DataFrame(rows).reindex(columns=COLS)
    old=pd.read_csv(cache).reindex(columns=COLS) if os.path.exists(cache) else pd.DataFrame(columns=COLS)
    pd.concat([old,new]).to_csv(cache,index=False); rows=[]
rows=[]; ses=requests.Session(); ses.headers.update(H)
def get(url,params):
    for a in range(5):
        try: r=ses.get(url,params=params,timeout=60)
        except requests.RequestException: time.sleep(5*(a+1)); continue
        if r.status_code==429: time.sleep(3*(a+1)); continue
        return r
    class _E: status_code=599
    return _E()
for _,r in S.iterrows():
    if r.setup_id in done: continue
    t=pd.Timestamp(r.decision_utc).tz_localize('UTC') if pd.Timestamp(r.decision_utc).tzinfo is None else pd.Timestamp(r.decision_utc)
    note=''
    if r.asset=='stock':
        st=t
        if st.time()<pd.Timestamp('13:30').time(): st=st.normalize()+pd.Timedelta(hours=13,minutes=30)
        elif st.time()>=pd.Timestamp('20:00').time(): st=st.normalize()+pd.Timedelta(days=1,hours=13,minutes=30)
        url='https://data.alpaca.markets/v2/stocks/bars'
        p=dict(symbols=r.ticker,timeframe='1Min',start=st.isoformat().replace('+00:00','Z'),end=min(st+pd.Timedelta(days=5),pd.Timestamp.now(tz='UTC')-pd.Timedelta(minutes=30)).isoformat().replace('+00:00','Z'),feed='sip',limit=2000,adjustment='split',sort='asc')
    else:
        sym=r.ticker.replace('-USD','/USD'); st=t
        url='https://data.alpaca.markets/v1beta3/crypto/us/bars'
        p=dict(symbols=sym,timeframe='1Min',start=st.isoformat().replace('+00:00','Z'),end=min(st+pd.Timedelta(hours=6),pd.Timestamp.now(tz='UTC')-pd.Timedelta(minutes=30)).isoformat().replace('+00:00','Z'),limit=400,sort='asc')
    resp=get(url,p)
    if resp.status_code!=200:
        rows.append(dict(setup_id=r.setup_id,note=f'http {resp.status_code}')); continue
    bars=(resp.json().get('bars') or {})
    b=list(bars.values())[0] if bars else []
    if r.asset=='stock':
        b=[x for x in b if '13:30'<=x['t'][11:16]<'20:00']
    if not b:
        rows.append(dict(setup_id=r.setup_id,note='no bars')); continue
    x=b[0]
    if len(rows)>=40: flush()
    rows.append(dict(setup_id=r.setup_id,entry_minute_utc=x['t'],minute_open=x['o'],minute_close=x['c'],lag_min=(pd.Timestamp(x['t'])-t).total_seconds()/60,note=note))
flush()
M=pd.read_csv(cache); print(len(M),'rows;',M.minute_open.notna().sum(),'with bars;',M.note.value_counts(dropna=False).to_dict())
