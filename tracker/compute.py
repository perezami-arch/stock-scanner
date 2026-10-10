import pandas as pd, numpy as np, json
from setups import SCANS
d=pd.read_pickle('prices2.pkl'); info=json.load(open('info2.json'))
TODAY=pd.Timestamp('2026-09-30')
def fmtd(ts): return ts.strftime('%d/%m/%Y')
def fdot(k): y,m,dd=k.split('-'); return f'{dd}.{m}.{y}'
# repeats
app={}
for k,v in SCANS.items():
    for s in v['setups']: app.setdefault(s[0],[]).append((k,s[1]))
rows=[]
for k,v in SCANS.items():
    for rank,s in enumerate(v['setups'],1):
        t,dirn,entry,sl,tsl,tps,score,hold,trig,trig_txt=s
        df=d[t].dropna(subset=['Close']).copy()
        sgn=1 if dirn=='LONG' else -1
        pre=df[df.index<pd.Timestamp(v['day1'])]
        ref_date=pre.index[-1]  # last completed session before alert
        # ATR14 (Wilder-simple rolling mean of TR) as % of close on ref_date
        h,l,c=df['High'],df['Low'],df['Close']; tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
        atr=tr.rolling(14).mean()
        atr_pct=float(atr.loc[ref_date]/c.loc[ref_date])
        mc=info[t]['mcap']; last=info[t]['last']
        mcap_ref=mc*float(c.loc[ref_date])/last if mc and last else None
        post=df[df.index>=pd.Timestamp(v['day1'])].iloc[:20]
        closes=post['Close'].tolist()
        cum=[sgn*(x/entry-1) for x in closes]
        daily=[]; prev=entry
        for x in closes: daily.append(x/prev-1); prev=x
        # events
        ev=[]; stop_hit=None; tp_hit=[None,None,None]; first=None
        for dt,r in post.iterrows():
            fav = r['High'] if sgn==1 else r['Low']; adv = r['Low'] if sgn==1 else r['High']
            sh = (adv<=sl) if sgn==1 else (adv>=sl)
            if sh and stop_hit is None: stop_hit=dt
            for i,tp in enumerate(tps):
                hit=(fav>=tp) if sgn==1 else (fav<=tp)
                if hit and tp_hit[i] is None: tp_hit[i]=dt
        # trigger activation
        trig_dt=None
        for dt,r in post.iterrows():
            if (sgn==1 and r['High']>=trig) or (sgn==-1 and r['Low']<=trig): trig_dt=dt; break
        # outcome
        if stop_hit is None and tp_hit[0] is None: outcome='פתוח' if len(post) else 'טרם התחיל'
        elif tp_hit[0] is not None and (stop_hit is None or tp_hit[0]<stop_hit): outcome='TP1'
        elif stop_hit is not None and (tp_hit[0] is None or stop_hit<tp_hit[0]): outcome='סטופ'
        else: outcome='עמום (סטופ ו-TP1 באותו יום)'
        # MFE/MAE vs entry
        if len(post):
            mfe = (post['High'].max()/entry-1) if sgn==1 else (1-post['Low'].min()/entry)
            mae = (post['Low'].min()/entry-1) if sgn==1 else (1-post['High'].max()/entry)
        else: mfe=mae=None
        # optimal entry/exit (buy low day i, sell high day j>i ; short: sell high i, cover low j>i)
        opt=None
        if len(post)>=2:
            best=-1e9
            idx=list(post.index)
            for i in range(len(idx)):
                for j in range(i+1,len(idx)):
                    if sgn==1: g=post['High'].iloc[j]/post['Low'].iloc[i]-1; pi,pj=post['Low'].iloc[i],post['High'].iloc[j]
                    else: g=1-post['Low'].iloc[j]/post['High'].iloc[i]; pi,pj=post['High'].iloc[i],post['Low'].iloc[j]
                    if g>best: best=g; opt=(idx[i],idx[j],pi,pj,j-i,g)
        others=[x for x in app[t] if x[0]!=k]
        rep = f"{len(others)} — " + ', '.join(f"{fdot(a)} ({'LONG' if b=='LONG' else 'SHORT'})" for a,b in others) if others else ''
        # rule-based trade result
        if outcome=='TP1': rule=abs(tps[0]/entry-1)
        elif outcome=='סטופ': rule=-abs(1-sl/entry)
        else: rule=cum[-1] if cum else None
        notes=[]
        notes.append(f"#{rank} בסריקה, ציון {score}. טריגר בסריקה: {trig_txt}.")
        if len(post)==0:
            notes.append("הסריקה פורסמה היום (30.9) לפני פתיחת המסחר — אין עדיין נתוני מסחר; ימים 1–20, תאריכים/מחירים אופטימליים ופגיעות נשארו ריקים.")
        else:
            notes.append(f"טריגר {trig:g}: " + (f"הופעל ב-{trig_dt.strftime('%d.%m')}" if trig_dt is not None else f"לא הופעל עד {post.index[-1].strftime('%d.%m')}") + ".")
            notes.append("סטופ " + (f"נפגע ב-{stop_hit.strftime('%d.%m')}" if stop_hit is not None else "לא נפגע") + "; " +
                ", ".join(f"TP{i+1} " + (f"נפגע ב-{x.strftime('%d.%m')}" if x is not None else "לא נפגע") for i,x in enumerate(tp_hit)) +
                f" (נכון לסגירת {post.index[-1].strftime('%d.%m')}, לפי High/Low יומי).")
            notes.append(f"תוצאה: {outcome}. MFE {mfe*100:+.2f}% / MAE {mae*100:+.2f}%.")
        rows.append(dict(scan=k,rank=rank,ticker=t,dir=dirn,entry=entry,sl=sl,tsl=tsl/100,tps=tps,score=score,hold=hold,
            ref_date=ref_date,atr=atr_pct,mcap=mcap_ref,cum=cum,daily=daily,ndays=len(post),last_date=post.index[-1] if len(post) else None,
            stop_hit=stop_hit,tp_hit=tp_hit,trig=trig,trig_dt=trig_dt,outcome=outcome,mfe=mfe,mae=mae,opt=opt,rep=rep,rule=rule,notes=notes,
            name=info[t]['name']))
pd.to_pickle(rows,'rows.pkl')
for r in rows:
    print(r['scan'],r['ticker'],r['dir'],r['ndays'],r['outcome'],None if not r['cum'] else round(r['cum'][-1]*100,2), r['rep'], round(r['atr']*100,2), r['mcap'] and round(r['mcap']/1e9,1), r['opt'] and (r['opt'][0].date(),r['opt'][1].date(),round(r['opt'][5]*100,1)))
