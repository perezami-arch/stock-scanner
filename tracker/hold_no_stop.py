"""Hold-to-now, no stops/targets, LONG only. Entry = tracker entry; count only if entry traded within the 20-period window."""
import pandas as pd, numpy as np, json
R=pd.read_pickle('rows_all.pkl')
D=pd.read_pickle('prices_all.pkl'); H=pd.read_pickle('auto/crypto_1h.pkl')
S=json.load(open('live_snap_2026-10-08.json'))
IL='Asia/Jerusalem'
STOCK_EXIT_TS=pd.Timestamp('2026-10-07 16:00',tz='America/New_York').tz_convert(IL)
spy=D['SPY'].dropna(subset=['Close']); SPY_EXIT=float(spy['Close'].iloc[-1]); assert spy.index[-1]==pd.Timestamp('2026-10-07')
PP=('p27','p25','pval','pmom','pcry')
def group(r):
    s=r['source']
    if s=='grok': return 'Grok '+r['cat']
    return {'gcrypto':'Grok crypto','gxtd':'Grok x-trends','gpns':'Grok portfolio-news','bot':'Bot v2.8','orig':'Original sheet (שפל שנתי)'}.get(s,'Perplexity' if s in PP else None)
def spy_ref(ts_il, stock):
    """SPY price at entry: stocks -> SPY open of entry day; crypto -> SPY open if entry falls in that day's US session, else last SPY close before entry."""
    if stock: return float(spy.loc[ts_il.normalize().tz_localize(None),'Open'])
    t=ts_il.tz_convert('America/New_York'); day=pd.Timestamp(t.date())
    if day in spy.index and t.time()>=pd.Timestamp('09:30').time() and t.time()<pd.Timestamp('16:00').time(): return float(spy.loc[day,'Open'])
    prev=spy[spy.index<day] if t.time()<pd.Timestamp('16:00').time() or day not in spy.index else spy[spy.index<=day]
    return float(prev['Close'].iloc[-1])
out=[]; skipped=[]
seen=set()
for r in R:
    g=group(r)
    if g is None or r['dir']!='LONG' or r['excluded']: continue
    key=(r['source'],r.get('cat'),r['ticker'],r['alert_date'])
    base=dict(group=g,source=r['source'],automation=r.get('cat') or r.get('auto') or '',ticker=r['ticker'],alert_date=r['alert_date'],tracker_outcome=r['outcome'])
    if key in seen: skipped.append({**base,'reason':'duplicate (same source/ticker/alert date)'}); continue
    seen.add(key)
    entry=r['entry']
    if entry is None: skipped.append({**base,'reason':'no entry price'}); continue
    crypto=r.get('ttype')=='קריפטו'
    if crypto:
        t=r['ticker']
        if t not in H.columns.get_level_values(0) or t not in S['crypto'] or r.get('crypto_start') is None: skipped.append({**base,'reason':'no Yahoo crypto data'}); continue
        h=H[t].dropna(subset=['Close']); st=pd.Timestamp(r['crypto_start']).tz_localize(IL).tz_convert('UTC')
        w=h[(h.index>=st)&(h.index<st+pd.Timedelta(hours=480))]
        if r.get('fixed'): gate=w.index[0] if len(w) else None; how='first hourly open (tracker)'
        else:
            gate=None; pc=float(h[h.index<st]['Close'].iloc[-1]) if len(h[h.index<st]) else None
            for ts,b in w.iterrows():
                if b['Low']<=entry<=b['High'] or (pc is not None and (pc<entry<b['Open'] or pc>entry>b['Open'])): gate=ts; break
                pc=float(b['Close'])
            how='alert price traded'
        if gate is None: skipped.append({**base,'reason':'entry never traded within 20x24h window' if len(w) else 'not started'}); continue
        ex=S['crypto'][t]['price']; ex_ts=pd.Timestamp(S['crypto'][t]['ts_il']); en_ts=gate.tz_convert(IL)
        sref=spy_ref(en_ts,False)
    else:
        t=r['ticker']
        if t not in D.columns.get_level_values(0): skipped.append({**base,'reason':'no Yahoo data'}); continue
        df=D[t].dropna(subset=['Close']); day1=pd.Timestamp(r.get('calc_date') or r['alert_date'])
        post=df[df.index>=day1]; pre=df[df.index<day1]
        if not len(post): skipped.append({**base,'reason':'not started'}); continue
        if df.index[-1]<pd.Timestamp('2026-10-07'): skipped.append({**base,'reason':f'no price after {df.index[-1].date()} (delisted/stale)'}); continue
        w=post.iloc[:20]
        if r.get('fixed'): gate=w.index[0]; how='day-1 open (tracker)'
        else:
            gate=None; pc=float(pre['Close'].iloc[-1]) if len(pre) else None
            for ts,b in w.iterrows():
                if b['Low']<=entry<=b['High'] or (pc is not None and (pc<entry<b['Open'] or pc>entry>b['Open'])): gate=ts; break
                pc=float(b['Close'])
            how='alert price traded'
        if gate is None: skipped.append({**base,'reason':'entry never traded within 20 trading days'}); continue
        ex=float(df['Close'].iloc[-1]); ex_ts=STOCK_EXIT_TS
        en_ts=pd.Timestamp(gate.date()).tz_localize('America/New_York')+pd.Timedelta(hours=9.5); en_ts=en_ts.tz_convert(IL)
        sref=spy_ref(pd.Timestamp(gate.date()).tz_localize(IL),True)
    ret=ex/entry-1; sret=SPY_EXIT/sref-1
    out.append({**base,'asset':'crypto' if crypto else 'stock','entry_price':entry,'entry_basis':how,'entry_time_il':en_ts.strftime('%Y-%m-%d %H:%M'),
        'exit_price':ex,'exit_time_il':ex_ts.strftime('%Y-%m-%d %H:%M'),'days_held':round((ex_ts-en_ts).total_seconds()/86400,2),
        'return_pct':round(ret*100,4),'pnl_usd_per_1000':round(1000*ret,2),'spy_entry':round(sref,4),'spy_exit':round(SPY_EXIT,4),
        'spy_return_pct':round(sret*100,4),'excess_vs_spy_pct':round((ret-sret)*100,4)})
P=pd.DataFrame(out); K=pd.DataFrame(skipped)
P['separate']=np.where((P.source=='bot')&(P.alert_date=='2026-10-07'),'bot 07.10 (1 day) - listed separately','')
P.to_csv('hold-no-stop-longs-2026-10-08.csv',index=False,encoding='utf-8-sig')
K.to_csv('hold-no-stop-longs-2026-10-08_excluded.csv',index=False,encoding='utf-8-sig')
print(len(P),'positions;',len(K),'skipped'); print(K.groupby(['group','reason']).size())
