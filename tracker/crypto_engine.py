"""Crypto backtest on hourly Yahoo bars, calendar days (crypto trades 24/7).
Day k = 24h window starting at the first full hour after the automation's run time (UTC)."""
import pandas as pd, numpy as np, json, re
H=pd.read_pickle('auto/crypto_1h.pkl'); D=pd.read_pickle('auto/crypto_daily.pkl')
CI=json.load(open('auto/crypto_info.json'))
CUT=pd.Timestamp('2026-10-08 08:00',tz='UTC')
RUNH={'crypto':8.5,'portfolio-news-scan':13.5,'x-trends-digest':9.0}
def loc(ts): return ts.tz_convert('Asia/Jerusalem').tz_localize(None)
def fixlevels(a,entry,ge,sgn):
    sl0,tp0=a['sl'],list(a['tps']); sp,tpp=a.get('sl_pct'),list(a.get('tp_pct') or (None,None,None))
    nsl,ntp=sl0,tp0[:]; how=[]
    if sp is not None: nsl=entry*(1-sgn*sp/100); how.append(f"סטופ {sp:g}% חושב מהכניסה")
    for i in range(3):
        if tpp[i] is not None: ntp[i]=entry*(1+sgn*tpp[i]/100)
    if any(v is not None for v in tpp): how.append("יעדים באחוזים חושבו מהכניסה")
    absl=[('סטופ',nsl,-1)] if sp is None and nsl is not None else []
    absl+=[(f'TP{i+1}',ntp[i],1) for i in range(3) if tpp[i] is None and ntp[i] is not None]
    inval=[n_ for n_,v,side in absl if (sgn*side*(v-entry))<=0]
    if ge is not None and entry!=ge:
        if absl and not inval: how.append("רמות מוחלטות של Grok נשארו (עדיין בצד הנכון של הכניסה החדשה)")
        elif inval:
            if sp is None and nsl is not None: nsl=entry*(nsl/ge)
            for i in range(3):
                if tpp[i] is None and ntp[i] is not None: ntp[i]=entry*(ntp[i]/ge)
            how.append(f"רמות מוחלטות לא תקפות מול הכניסה החדשה ({', '.join(inval)}), ולכן הותאמו יחסית לפתיחה לפי המרחקים באחוזים ממחיר Grok ({ge:g}): סטופ {sl0}→{nsl:.6g}, יעדים {tp0}→{[None if v is None else float(f'{v:.6g}') for v in ntp]}")
            inval=[]
    elif inval:
        how.append(f"רמות בצד הלא נכון של הכניסה ({', '.join(inval)}) ואין מחיר ייחוס לשינוי קנה מידה — הוסרו")
        if 'סטופ' in inval: nsl=None
        ntp=[None if f'TP{i+1}' in inval else ntp[i] for i in range(3)]
    if nsl is None: how.append(f"אין סטופ מספרי (טקסט Grok: \"{(a.get('sl_cell') or '')[:40]}\") — לא הומצא")
    if all(v is None for v in ntp): how.append(f"אין יעדים מספריים (טקסט Grok: \"{(a.get('tp_cell') or '')[:40]}\")")
    return nsl,tuple(ntp),how
def run_crypto(a,r,notes):
    t=a['ticker']; sgn=1 if a['dir']!='SHORT' else -1
    if t not in CI:
        notes.append("אין נתוני מחיר ב-Yahoo למטבע הזה ("+a.get('unmapped','')+"). לא חושב (לא הומצא מחיר)."); return
    h=H[t].dropna(subset=['Close']); 
    rt=pd.Timestamp(a['alert_date'],tz='UTC')+pd.Timedelta(hours=RUNH[a['auto']] if a.get('auto') else a['run_h_utc'])
    start=rt.floor('h')+pd.Timedelta(hours=1)
    pre=h[h.index<start]
    if not len(pre): notes.append("אין נתוני Yahoo לפני מועד ההתראה."); return
    pc=float(pre['Close'].iloc[-1])
    # ATR14 (daily, calendar) before alert
    dd=D[t].dropna(subset=['Close']); dd=dd[dd.index<pd.Timestamp(a['alert_date'])]
    if len(dd)>=15:
        c=dd['Close']; tr=pd.concat([dd['High']-dd['Low'],(dd['High']-c.shift()).abs(),(dd['Low']-c.shift()).abs()],axis=1).max(axis=1)
        r['atr']=float(tr.rolling(14).mean().iloc[-1]/c.iloc[-1])
    mc,last=CI[t].get('mcap'),CI[t].get('last')
    if mc and last: r['mcap']=mc*pc/last
    wins=[]
    for k in range(20):
        ws,we=start+pd.Timedelta(hours=24*k),start+pd.Timedelta(hours=24*(k+1))
        if we>CUT: break
        w=h[(h.index>=ws)&(h.index<we)]
        if len(w): wins.append((ws,w))
    r['crypto_start']=loc(start)
    if not wins:
        r['outcome']='טרם התחיל'; notes.append(f"חלון היום הראשון (מ-{loc(start):%d.%m %H:%M} שעון ישראל) עוד לא הסתיים עד {loc(CUT):%d.%m %H:%M} — אין עדיין נתונים."); return
    w1=wins[0][1]; o0=float(w1['Open'].iloc[0]); lo0,hi0=float(w1['Low'].min()),float(w1['High'].max())
    ge=a.get('grok_entry'); bad=ge is not None and not (lo0*0.97<=ge<=hi0*1.03 or abs(ge/pc-1)<0.03)
    if a['source']=='pcry' and ge is not None: bad=not (lo0*0.97<=ge<=hi0*1.03 or abs(ge/pc-1)<0.10)
    entry=ge
    if ge is None or bad:
        entry=o0; r['fixed']='mismatch' if bad else 'missing'; r['grok_px_txt']=f"{ge:g}" if ge is not None else 'לא צוין'
        if bad: r['px_dev_orig']=ge/pc-1
        notes.append(f"מחיר כניסה = פתיחה, מחיר גרוק: {r['grok_px_txt']}. הכניסה הוחלפה בפתיחת הנר השעתי הראשון אחרי הריצה ({loc(start):%d.%m %H:%M} שעון ישראל, ${o0:.6g})"+(f", כי מחיר Grok רחוק ב-{ge/pc-1:+.0%} מהמחיר לפני ההתראה (${pc:.6g}) ומחוץ לטווח יום 1." if bad else ", כי ב-Grok לא היה מחיר מספרי."))
    else:
        r['px_ok']=True; r['px_dev']=ge/pc-1
        notes.append(f"בדיקת מחיר: מחיר לפני ההתראה {pc:.6g}, יום 1 טווח {lo0:.6g}–{hi0:.6g} — מחיר Grok {ge:g} תקין.")
    sl,tps,how=fixlevels(a,entry,ge,sgn)
    if how: notes.append('. '.join(how)+'.')
    if a['source']=='pcry' and ((sl is None)!=(tps[0] is None)):
        have=f"סטופ {sl:.6g}" if sl is not None else "יעדים "+'/'.join(f"{v:.6g}" for v in tps if v is not None)
        notes.append(f"כלל סטטיסטיקה (Perplexity): יש רק {have} בלי {'TP1' if sl is not None else 'סטופ'} מספרי — הרמה נשמרת בהערה בלבד, והשורה נספרת בתשואות בלבד (ללא סטופ/יעד).")
        r['partial_levels']=have; sl=None; tps=(None,None,None)
    r['entry']=entry; r['sl']=sl; r['tps']=tps
    allb=pd.concat([w for _,w in wins])
    # entry-first: on day 1 hits count only from the first bar that trades the entry price
    i0=0
    gated=a['source']=='pcry' and not r.get('fixed'); r['_gate_none']=False
    if gated:
        tr_=[i for i,(ix,b) in enumerate(allb.iterrows()) if b['Low']<=entry<=b['High']]
        if tr_: i0=tr_[0]; r['entry_bar']=loc(allb.index[i0]); notes.append(f"כלל כניסה-קודם (Perplexity): מחיר הכניסה {entry:g} נסחר לראשונה ב-{loc(allb.index[i0]):%d.%m %H:%M} שעון ישראל; פגיעות נספרות רק מאז.")
        else: i0=len(allb); r['_gate_none']=True; notes.append(f"כלל כניסה-קודם (Perplexity): מחיר הכניסה {entry:g} לא נסחר בחלון — העסקה לא הופעלה ולא נספרת בסטטיסטיקה.")
    elif not r.get('fixed'):
        tr_=[(i) for i,(ix,b) in enumerate(w1.iterrows()) if b['Low']<=entry<=b['High']]
        if tr_: i0=tr_[0]; r['entry_bar']=loc(w1.index[i0])
        else: notes.append("מחיר Grok לא נסחר בפועל ביום 1 (בטווח 3%) — פגיעות נספרו מתחילת החלון.")
        if i0: notes.append(f"כלל כניסה-קודם: הכניסה נסחרה לראשונה ב-{loc(w1.index[i0]):%d.%m %H:%M}; פגיעות סטופ/יעד לפני כן ביום 1 לא נספרו.")
    bars=allb.iloc[i0:]
    for ix,b in bars.iterrows():
        fav=b['High'] if sgn==1 else b['Low']; adv=b['Low'] if sgn==1 else b['High']
        if sl is not None and r['stop_hit'] is None and ((adv<=sl) if sgn==1 else (adv>=sl)): r['stop_hit']=loc(ix)
        for i,tp in enumerate(tps):
            if tp is not None and r['tp_hit'][i] is None and ((fav>=tp) if sgn==1 else (fav<=tp)): r['tp_hit'][i]=loc(ix)
    closes=[float(w['Close'].iloc[-1]) for _,w in wins]
    r['ndays']=len(wins); r['cum']=[sgn*(x/entry-1) for x in closes]; p=entry
    for x in closes: r['daily'].append(x/p-1); p=x
    sh,t1=r['stop_hit'],r['tp_hit'][0]
    if sl is None and tps[0] is None: r['outcome']='ללא סטופ/יעד'
    elif sh is None and t1 is None: r['outcome']='פתוח'
    elif t1 is not None and (sh is None or t1<sh): r['outcome']='TP1'
    elif sh is not None and (t1 is None or sh<t1): r['outcome']='סטופ'
    else: r['outcome']='עמום'; r['amb']=[f'SL+TP1 same hourly candle {sh}']
    if r['_gate_none']: r['outcome']='לא הופעל'
    if len(bars) and not r['_gate_none']:
        r['mfe']=(bars['High'].max()/entry-1) if sgn==1 else (1-bars['Low'].min()/entry)
        r['mae']=(bars['Low'].min()/entry-1) if sgn==1 else (1-bars['High'].max()/entry)
    if len(wins)>=2:
        best=-1e9; W=[(ws,float(w['High'].max()),float(w['Low'].min())) for ws,w in wins]
        for i in range(len(W)):
            for j in range(i+1,len(W)):
                if sgn==1: g=W[j][1]/W[i][2]-1; pi,pj=W[i][2],W[j][1]
                else: g=1-W[j][2]/W[i][1]; pi,pj=W[i][1],W[j][2]
                if g>best: best=g; r['opt']=(loc(W[i][0]),loc(W[j][0]),pi,pj,j-i,g)
    if r['outcome']=='TP1': r['rule']=abs(tps[0]/entry-1)
    elif r['outcome']=='סטופ': r['rule']=-abs(1-sl/entry)
    elif r['cum'] and r['outcome']!='לא הופעל': r['rule']=r['cum'][-1]
    parts=[]
    if sl is not None: parts.append("סטופ "+(f"נפגע ב-{sh:%d.%m %H:%M}" if sh is not None else "לא נפגע"))
    for i,tp in enumerate(tps):
        if tp is not None: parts.append(f"TP{i+1} "+(f"נפגע ב-{r['tp_hit'][i]:%d.%m %H:%M}" if r['tp_hit'][i] is not None else "לא נפגע"))
    end=loc(wins[-1][0]+pd.Timedelta(hours=24))
    notes.append(("; ".join(parts) if parts else "אין סטופ/יעדים — לא נבדקו פגיעות")+f" (עד {end:%d.%m %H:%M} שעון ישראל, נרות שעתיים, ימים קלנדריים)." )
    notes.append(f"תוצאה: {r['outcome']}."+(f" MFE {r['mfe']:+.2%} / MAE {r['mae']:+.2%}." if r['mfe'] is not None else ''))
    if len(wins)<20: notes.append(f"נמדדו {len(wins)} ימים קלנדריים (חלונות 24 שעות) מתוך 20; השאר טרם הסתיימו.")
