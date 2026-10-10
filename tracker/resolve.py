import pandas as pd, yfinance as yf, json
R=pd.read_pickle('rows_all.pkl')
for r in R:
    if r['source']!='grok' or not r.get('amb') or r.get('px_ok') is False: continue
    a=[x for x in r['amb'] if 'NOT traded' not in x]
    if not a: continue
    t=r['ticker']; dts=sorted({pd.Timestamp(x.split()[-1]) for x in a if 'same candle' in x} | ({r['stop_hit']} if any('day1' in x for x in a) else set()))
    for dt in dts:
        for iv in ('60m','5m'):
            h=yf.download(t,start=dt.strftime('%Y-%m-%d'),end=(dt+pd.Timedelta(days=1)).strftime('%Y-%m-%d'),interval=iv,progress=False,auto_adjust=False)
            if isinstance(h.columns,pd.MultiIndex): h.columns=h.columns.get_level_values(0)
            print('==',t,r['dir'],r['alert_date'],'entry',r['entry'],'sl',r['sl'],'tp',r['tps'],iv,dt.date(),a)
            if iv=='60m': print(h[['Open','High','Low','Close']].round(3).to_string())
            else:
                sgn=1 if r['dir']=='LONG' else -1
                ev=[]
                for ts,b in h.iterrows():
                    if (b.Low<=r['entry']<=b.High): ev.append((ts.strftime('%H:%M'),'ENTRY'))
                    if (b.Low<=r['sl'] if sgn==1 else b.High>=r['sl']): ev.append((ts.strftime('%H:%M'),'SL'))
                    if (b.High>=r['tps'][0] if sgn==1 else b.Low<=r['tps'][0]): ev.append((ts.strftime('%H:%M'),'TP1'))
                seen=[];[seen.append(e) for e in ev if e[1] not in [s[1] for s in seen]]
                print('5m first events:',seen, 'bars',len(h))
