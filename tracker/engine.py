import pandas as pd, numpy as np, json
from alerts import all_alerts
from crypto_engine import run_crypto
GS=('grok','gpns','gxtd')
PP=('p27','p25','pval','pmom','pcry')
GSX=GS+PP
d=pd.read_pickle('prices_all.pkl'); info=json.load(open('info_all.json'))
import os
CG=json.load(open('auto/cg_mcap.json')) if os.path.exists('auto/cg_mcap.json') else {}
OV=json.load(open('overrides.json')) if os.path.exists('overrides.json') else {}
OVA=json.load(open('overrides_auto.json')) if os.path.exists('overrides_auto.json') else {}
OV={**OVA,**OV}  # manual overrides win
_P='/home/box/agent-data/agents/392ab573-33c2-4c0d-8dc3-6b3991775b0d/attachments/'
CHART30={'PANW':f"גרף אימות מאילן (צילום 30.09.2026, לא התראה חדשה): מחיר 388.41, ATR 18.16 (4.67%), מעל ממוצע 150, דוח בעוד 43 ימים. קובץ: {_P}bb12fd67e20dc92b353ddc7325fbfe39ecdf9df49e3c2afae094b7e67a44744c.png",
 'XOM':f"גרף אימות מאילן (צילום 30.09.2026, לא התראה חדשה): מחיר 161.35, ATR 3.63 (2.25%), מעל ממוצע 150, דוח בעוד 23 ימים. קובץ: {_P}5d75397622380e47c005a13fee6789553c4ca651b114b3baa66f5692c879a2e1.png",
 'AMC':f"גרף אימות מאילן (צילום 30.09.2026, לא התראה חדשה): מחיר 3.08, MCAP 2.75B. קובץ: {_P}c7daba98e8e9f634240295e3bdf28a7a167a0501164a1e9807c89820f9df13e7.png",
 'ADBE':f"גרף אימות מאילן (צילום 30.09.2026, לא התראה חדשה): מחיר 233.17, MCAP 90.75B. קובץ: {_P}517959817909ef26512e06414b75b9216ae98047adddc964c9c1f5500b469635.png",
 'ACHR':f"גרף אימות מאילן (צילום 30.09.2026, לא התראה חדשה): מחיר 5.06, MCAP 3.9B. קובץ: {_P}8e90fca00332e97f6b16ac30939986395dbfd0b8cde3144f1cd9c01804c19030.png",
 'ABBV':f"גרף אימות מאילן (צילום 30.09.2026, לא התראה חדשה): מחיר 263.29, MCAP 465.27B. קובץ: {_P}5e44c10bb51f85a34953dc3beb786f59e35e834c91b9a92c215dfd4a66076909.png",
 'WGS':f"גרף אימות מאילן (צילום 30.09.2026, לא התראה חדשה): מחיר 75.79 (‎-11.80% היום), MCAP 2.26B, ATR 6.44 (8.49%), מעל ממוצע 150, דוח בעוד 34 ימים. קובץ: {_P}19c6069dad62e0edc794fb3e7f7375a0b0580c46d4779e5c9aab320b9a75f85c.png",
 'VLO':f"גרף אימות מאילן (צילום 30.09.2026, לא התראה חדשה): מחיר 387.72, MCAP 111.64B, ATR 14.95 (3.86%), מעל ממוצע 150, דוח בעוד 22 ימים. קובץ: {_P}a868e7191d5c431d43110bd25ddaa8b5ebe1ed7dd1e57d903397126a2efbdf5b.png",
 'WMT':f"גרף אימות מאילן (צילום 30.09.2026, לא התראה חדשה): מחיר 106.80, ATR 2.23 (2.09%), מתחת לממוצע 150, דוח בעוד 50 ימים. קובץ: {_P}6fcaf6c23fd3c15a0d294d45f66d20194839ebcf9f6bbd3a653f53abeff90645.png"}
fdot=lambda k: f"{k[8:10]}.{k[5:7]}.{k[:4]}"
def pmc(x):
    if x is None or x=='': return None
    if isinstance(x,(int,float)): return float(x) if x>1e6 else None
    import re
    m=re.match(r'\s*\$?([\d.,]+)\s*([KMBT])?',str(x).upper())
    if not m: return None
    return float(m.group(1).replace(',',''))*{'K':1e3,'M':1e6,'B':1e9,'T':1e12,None:1}[m.group(2)]
def run():
    A=all_alerts(); app={}
    for a in A:
        if a['alert_date'] and a['source']!='ilan': app.setdefault(a['ticker'],[]).append((a['alert_date'],a['dir'],a['source'],a.get('cat','')))
    SRC={'bot':'בוט v2.8','orig':'גיליון מקורי','ilan':'גרף אילן','grok':'GROK automation','gcrypto':'GROK crypto','gpns':'GROK portfolio-news-scan','gxtd':'GROK x-trends-digest','p27':'Perplexity v2.7','p25':'Perplexity v2.5','pval':'Perplexity value','pmom':'Perplexity momentum','pcry':'Perplexity crypto'}
    rows=[]
    for a in A:
        r=dict(a); t=a['ticker']; notes=list(a['pre'])
        df=d[t].dropna(subset=['Close']).copy() if t in d.columns.get_level_values(0) else pd.DataFrame()
        sgn=1 if a['dir']!='SHORT' else -1; entry=a['entry']; sl=a['sl']; tps=a['tps'] if a['tps'] else (None,None,None)
        r.update(cum=[],daily=[],ndays=0,opt=None,stop_hit=None,tp_hit=[None]*3,trig_dt=None,outcome='אין נתונים',mfe=None,mae=None,rule=None,atr=None,mcap=None)
        others=[x for x in app.get(t,[]) if x[0]!=a['alert_date'] or x[2]!=a['source'] or x[3]!=a.get('cat','')]
        r['rep']=(f"{len(others)} — "+', '.join(f"{fdot(x[0])} ({x[1] or '?'}, {SRC[x[2]]}{(' '+x[3]) if x[3] else ''})" for x in sorted(others))) if others else ''
        if a.get('ttype')=='קריפטו':
            run_crypto(a,r,notes); r['notes']=notes; rows.append(r); continue
        cdate=a.get('calc_date') or a['alert_date']
        if not cdate:
            notes.append("חסר תאריך התראה במקור — לא ניתן לחשב."); r['notes']=notes; rows.append(r); continue
        if df.empty:
            notes.append("אין נתוני מחיר ב-Yahoo."); r['notes']=notes; rows.append(r); continue
        day1=pd.Timestamp(cdate)
        pre=df[df.index<day1]; ref=pre.index[-1] if len(pre) else None
        h,l,c=df['High'],df['Low'],df['Close']; tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1); atr=tr.rolling(14).mean()
        if ref is not None and not np.isnan(atr.loc[ref]): r['atr']=float(atr.loc[ref]/c.loc[ref])
        mc=info[t].get('mcap'); last=info[t].get('last')
        if mc and last and ref is not None: r['mcap']=mc*float(c.loc[ref])/last
        if a.get('atr_override') is not None:
            if r['atr'] is not None: notes.append(f"ATR מהגרף; ATR14 מחושב מ-Yahoo: {r['atr']:.2%}.")
            r['atr']=a['atr_override']
        post=df[df.index>=day1].iloc[:20]
        if a.get('refs') and ref is not None:
            pw=pre.iloc[-252:]; L52=float(pw['Low'].min()); H52=float(pw['High'].max()); S200=float(pre['Close'].iloc[-200:].mean()) if len(pre)>=200 else None
            a=dict(a); tps_=list(a['tps']); dn=[]
            for k_,v_ in a['refs'].items():
                if v_[0]=='52wL': val=L52*(1-v_[1]/100); dn.append(f"{'סטופ' if k_=='sl' else k_.upper()} = שפל 52 שבועות {L52:.2f}"+(f" פחות {v_[1]:g}%" if v_[1] else '')+f" = {val:.2f}")
                elif v_[0]=='sma200': val=S200; dn.append(f"{k_.upper()} = SMA200 = {val:.2f}" if val else f"{k_.upper()} = SMA200 — אין מספיק נתונים")
                elif v_[0]=='mid52': val=(L52+H52)/2; dn.append(f"{k_.upper()} = אמצע טווח 52 שבועות ({L52:.2f}–{H52:.2f}) = {val:.2f}")
                val=round(val,4) if val else None
                if k_=='sl': a['sl']=val
                else: tps_[{'tp1':0,'tp2':1}[k_]]=val
            a['tps']=tuple(tps_); sl=a['sl']; tps=a['tps']; r['sl'],r['tps']=sl,tps
            notes.append(f"רמות שנגזרו מנתוני Yahoo (252 סשנים לפני {pd.Timestamp(day1).strftime('%d.%m')}): "+'; '.join(dn)+".")
        if a['source'] in GSX and len(post) and ref is not None:
            o0=float(post['Open'].iloc[0]); cp=float(c.loc[ref]); lo0,hi0=float(post['Low'].iloc[0]),float(post['High'].iloc[0])
            ge=a.get('grok_entry'); bad=ge is not None and not (lo0*0.97<=ge<=hi0*1.03 or abs(ge/cp-1)<0.03)
            if a['source'] in PP and ge is not None:
                # Perplexity entries are trigger levels (breakout/breakdown/retest), not the current price: validate the table's own current price
                cu=a.get('cur')
                if cu: bad=not (abs(cu/cp-1)<0.03 or lo0*0.97<=cu<=hi0*1.03) or abs(ge/cp-1)>0.15
                else: bad=not (lo0*0.97<=ge<=hi0*1.03 or abs(ge/cp-1)<0.10)
                r['pp_trig_check']=(cu,cp,lo0,hi0,bad)
            if ge is None or bad:
                import re as _re
                rg=[_re.search(r'\(([\d.]+)–([\d.]+)\)',g_) for g_ in a.get('parse_gaps',[])]; rg=[m for m in rg if m]
                refp=ge if ge is not None else ((float(rg[0].group(1))+float(rg[0].group(2)))/2 if rg else None)
                gtxt=(f"{ge:g}" if ge is not None else (f"טווח {rg[0].group(1)}–{rg[0].group(2)}" if rg else "לא צוין"))
                entry=round(o0,4); r['entry']=entry; r['fixed']='mismatch' if bad else 'missing'; r['grok_px_txt']=gtxt
                if bad: r['px_dev_orig']=ge/cp-1
                fx=[f"מחיר כניסה = פתיחה, מחיר גרוק: {gtxt}. לפי הנחיית אילן, מחיר ההתראה הוחלף בפתיחה של {post.index[0].strftime('%d.%m')} (${o0:.2f})"+(f", כי מחיר Grok היה רחוק ב-{ge/cp-1:+.0%} מהסגירה הקודמת (${cp:.2f}) ומחוץ לטווח יום 1." if bad else ", כי ב-Grok לא היה מחיר מספרי.")]
                sl0,tp0=a['sl'],list(a['tps']); sp,tpp=a.get('sl_pct'),list(a.get('tp_pct') or (None,None,None))
                nsl,ntp=sl0,tp0[:]; how=[]
                if sp is not None: nsl=round(entry*(1-sgn*sp/100),4); how.append(f"סטופ {sp:g}% חושב מהפתיחה")
                for i in range(3):
                    if tpp[i] is not None: ntp[i]=round(entry*(1+sgn*tpp[i]/100),4)
                if any(v is not None for v in tpp): how.append("יעדים באחוזים חושבו מהפתיחה")
                absl=[('סטופ',nsl,-1)] if sp is None and nsl is not None else []
                absl+=[(f'TP{i+1}',ntp[i],1) for i in range(3) if tpp[i] is None and ntp[i] is not None]
                inval=[n_ for n_,v,side in absl if (sgn*side*(v-entry))<=0]
                if absl and not inval: how.append("רמות מוחלטות של Grok (סטופ/יעדים) נשארו, כי הן עדיין בצד הנכון של הכניסה החדשה")
                elif inval:
                    if refp:
                        if sp is None and nsl is not None: nsl=round(entry*(nsl/refp),4)
                        for i in range(3):
                            if tpp[i] is None and ntp[i] is not None: ntp[i]=round(entry*(ntp[i]/refp),4)
                        how.append(f"רמות מוחלטות לא תקפות מול הכניסה החדשה ({', '.join(inval)}), ולכן כל הרמות המוחלטות הותאמו יחסית לפתיחה לפי המרחקים באחוזים ממחיר Grok ({refp:g}): סטופ {sl0}→{nsl}, יעדים {tp0}→{ntp}")
                    else:
                        how.append(f"רמות לא תקפות ({', '.join(inval)}) ואין מחיר ייחוס של Grok לשינוי קנה מידה — הוסרו")
                        if 'סטופ' in inval: nsl=None
                        ntp=[None if f'TP{i+1}' in inval else ntp[i] for i in range(3)]
                if nsl is None: how.append(f"אין סטופ מספרי (טקסט Grok: \"{a.get('sl_cell','')[:40]}\")")
                if all(v is None for v in ntp): how.append(f"אין יעדים מספריים (טקסט Grok: \"{a.get('tp_cell','')[:40]}\")")
                sl=nsl; tps=tuple(ntp); r['sl']=sl; r['tps']=tps
                notes.append(fx[0]+" "+'. '.join(how)+".")
                a=dict(a); a['entry']=entry
        if a['source'] in PP and ((sl is None)!=(tps[0] is None)):
            _g=lambda v: f"{v:.4g}"
            have=f"סטופ {_g(sl)}" if sl is not None else "יעדים "+'/'.join(_g(v) for v in tps if v is not None)
            notes.append(f"כלל סטטיסטיקה (Perplexity): יש רק {have} בלי {'TP1' if sl is not None else 'סטופ'} מספרי — הרמה נשמרת בהערה בלבד, והשורה נספרת בתשואות בלבד (ללא סטופ/יעד), כדי לא להטות את אחוז ההצלחה.")
            r['partial_levels']=have; sl=None; tps=(None,None,None); r['sl']=None; r['tps']=tps
        if entry is None:
            notes.append("אין מחיר התראה במקור — ימים 1–20, פגיעות ואופטימלי לא חושבו (לא הומצא מחיר)."+(f" לעיון: סגירת Yahoo ביום המסחר הראשון ({post.index[0].strftime('%d.%m')}) = ${post['Close'].iloc[0]:.2f}." if len(post) else ""))
            r['notes']=notes; rows.append(r); continue
        if a['source'] in ('orig',)+GSX and not r.get('fixed') and ref is not None and len(post):
            r['px_ok']=True
            o0,c0,cp=float(post['Open'].iloc[0]),float(post['Close'].iloc[0]),float(c.loc[ref])
            lo0,hi0=float(post['Low'].iloc[0]),float(post['High'].iloc[0])
            notes.append(f"בדיקת מחיר: סגירה קודמת {cp:.2f}, יום 1 ({post.index[0].strftime('%d.%m')}) פתיחה {o0:.2f} טווח {lo0:.2f}–{hi0:.2f} סגירה {c0:.2f}"+("" if lo0*0.97<=entry<=hi0*1.03 or abs(entry/cp-1)<0.03 else " — מחיר ההתראה רחוק מהטווח, לבדוק")+".")
            r['px_ok']=bool(lo0*0.97<=entry<=hi0*1.03 or abs(entry/cp-1)<0.03); r['px_dev']=entry/cp-1
        closes=post['Close'].tolist(); r['ndays']=len(post)
        r['cum']=[sgn*(x/entry-1) for x in closes]; p=entry
        for x in closes: r['daily'].append(x/p-1); p=x
        ov=OV.get(f"{a['source']}|{t}|{a['alert_date'] or cdate}",{}); r['override']=ov
        skip_sl=set(ov.get('skip_stop_dates',[])); skip_tp=set(ov.get('skip_tp_dates',[]))
        gate=None; gated=a['source'] in PP and not r.get('fixed') and len(post)>0 and ref is not None
        if gated:
            pc_=float(c.loc[ref])
            for dt_,row in post.iterrows():
                if row['Low']<=entry<=row['High'] or pc_<entry<row['Open'] or pc_>entry>row['Open']: gate=dt_; break
                pc_=float(row['Close'])
            r['entry_dt']=gate
        for dt_,row in post.iterrows():
            if gated and (gate is None or dt_<gate): continue
            fav=row['High'] if sgn==1 else row['Low']; adv=row['Low'] if sgn==1 else row['High']
            if sl is not None and r['stop_hit'] is None and dt_.strftime('%Y-%m-%d') not in skip_sl and ((adv<=sl) if sgn==1 else (adv>=sl)): r['stop_hit']=dt_
            for i,tp in enumerate(tps):
                if tp is not None and r['tp_hit'][i] is None and dt_.strftime('%Y-%m-%d') not in skip_tp and ((fav>=tp) if sgn==1 else (fav<=tp)): r['tp_hit'][i]=dt_
            if a.get('trig') is not None and r['trig_dt'] is None and ((sgn==1 and row['High']>=a['trig']) or (sgn==-1 and row['Low']<=a['trig'])): r['trig_dt']=dt_
        if ov.get('same_day_first')=='TP1' and r['tp_hit'][0] is not None and r['stop_hit']==r['tp_hit'][0]:
            pass
        if ov.get('same_day_first')=='SL' and r['stop_hit'] is not None:
            r['tp_hit']=[x if (x is None or x!=r['stop_hit']) else None for x in r['tp_hit']]
        sh,t1=r['stop_hit'],r['tp_hit'][0]
        if r.get('px_ok') is False and a['source'] in GS:
            r['outcome_raw']=None
        if not len(post): r['outcome']='טרם התחיל'
        elif sl is None and tps[0] is None: r['outcome']='ללא סטופ/יעד'
        elif sh is None and t1 is None: r['outcome']='פתוח'
        elif t1 is not None and (sh is None or t1<sh): r['outcome']='TP1'
        elif sh is not None and (t1 is None or sh<t1): r['outcome']='סטופ'
        elif ov.get('same_day_first')=='SL': r['outcome']='סטופ'
        elif ov.get('same_day_first')=='TP1': r['outcome']='TP1'
        else: r['outcome']='עמום'
        if gated and gate is None: r['outcome']='לא הופעל'
        # ambiguity flags for intraday resolution
        r['amb']=[]
        if len(post):
            d1=post.index[0]; o1=float(post['Open'].iloc[0])
            for i,x in enumerate(r['tp_hit']):
                if x is not None and r['stop_hit'] is not None and x==r['stop_hit']: r['amb'].append(f'SL+TP{i+1} same candle {x.date()}')
            if gated and gate is not None and (r['stop_hit']==gate or any(x==gate for x in r['tp_hit'])) and post.loc[gate,'Low']<=entry<=post.loc[gate,'High'] and not (ov.get('resolved')):
                r['amb'].append(f'entry-day hit {gate.date()}: entry traded intraday on a day with a stop/TP touch')
            elif sl is not None and r['stop_hit']==d1 and ((sgn==1 and o1<entry) or (sgn==-1 and o1>entry)) and not ov.get('resolved'):
                tp_same=[i for i,x in enumerate(r['tp_hit']) if x==d1]
                r['amb'].append('day1: opened beyond entry toward stop; alert price traded '+('in range' if post['Low'].iloc[0]<=entry<=post['High'].iloc[0] else 'NOT traded on day 1'))
        pm=post[post.index>=gate] if (gated and gate is not None) else post
        if len(pm) and r['outcome']!='לא הופעל':
            r['mfe']=(pm['High'].max()/entry-1) if sgn==1 else (1-pm['Low'].min()/entry)
            r['mae']=(pm['Low'].min()/entry-1) if sgn==1 else (1-pm['High'].max()/entry)
        if len(post)>=2:
            best=-1e9; idx=list(post.index)
            for i in range(len(idx)):
                for j in range(i+1,len(idx)):
                    if sgn==1: g=post['High'].iloc[j]/post['Low'].iloc[i]-1; pi,pj=post['Low'].iloc[i],post['High'].iloc[j]
                    else: g=1-post['Low'].iloc[j]/post['High'].iloc[i]; pi,pj=post['High'].iloc[i],post['Low'].iloc[j]
                    if g>best: best=g; r['opt']=(idx[i],idx[j],float(pi),float(pj),j-i,g)
        if r.get('px_ok') is False and a['source'] in GS:
            r['outcome_raw']=r['outcome']; r['outcome']='מחיר לא תואם'
            notes.append(f"מחיר ההתראה בטבלת Grok ({entry:g}) רחוק ב-{r['px_dev']:+.0%} מהסגירה הקודמת ב-Yahoo ומחוץ לטווח יום 1. ככל הנראה מחיר שגוי או מיושן. החישוב לפי מחיר ההתראה מוצג לעיון (תוצאה גולמית: {r['outcome_raw']}), אבל השורה לא נכללת בסטטיסטיקה.")
        if r['outcome']=='TP1': r['rule']=abs(tps[0]/entry-1)
        elif r['outcome']=='סטופ': r['rule']=-abs(1-sl/entry)
        elif r['cum'] and r['outcome']!='לא הופעל': r['rule']=r['cum'][-1]
        if not len(post):
            notes.append("ההתראה היום לפני פתיחת המסחר — אין עדיין נתונים; ימים 1–20, אופטימלי ופגיעות ריקים.")
        else:
            if a.get('trig') is not None:
                notes.append(f"טריגר {a['trig']:g}: "+(f"הופעל ב-{r['trig_dt'].strftime('%d.%m')}" if r['trig_dt'] is not None else f"לא הופעל עד {post.index[-1].strftime('%d.%m')}")+".")
            parts=[]
            if sl is not None: parts.append("סטופ "+(f"נפגע ב-{sh.strftime('%d.%m')}" if sh is not None else "לא נפגע"))
            for i,tp in enumerate(tps):
                if tp is not None: parts.append(f"TP{i+1} "+(f"נפגע ב-{r['tp_hit'][i].strftime('%d.%m')}" if r['tp_hit'][i] is not None else "לא נפגע"))
            if parts: notes.append("; ".join(parts)+f" (עד סגירת {post.index[-1].strftime('%d.%m')}, לפי High/Low יומי).")
            else: notes.append("אין סטופ/יעדים במקור — לא נבדקו פגיעות.")
            if gated: notes.append(f"כלל כניסה-קודם (Perplexity): "+(f"מחיר הכניסה {entry:g} נסחר לראשונה ב-{gate.strftime('%d.%m')}; פגיעות סטופ/יעד נספרות רק מאז." if gate is not None else f"מחיר הכניסה {entry:g} לא נסחר עד {post.index[-1].strftime('%d.%m')} — העסקה לא הופעלה, ולכן לא נספרת בסטטיסטיקה (התשואות בימים 1–20 מוצגות לעיון בלבד)."))
            notes.append(f"תוצאה: {r['outcome']}."+(f" MFE {r['mfe']:+.2%} / MAE {r['mae']:+.2%}." if r['mfe'] is not None else ''))
            if a.get('dir_assumed'):
                notes.append(f"מבט לונג: {r['cum'][-1]:+.2%} אחרי {len(post)} ימים; מבט שורט (אותה תנועה): {-r['cum'][-1]:+.2%}. שיא {post['High'].max():.2f} ב-{post['High'].idxmax().strftime('%d.%m')}, שפל {post['Low'].min():.2f} ב-{post['Low'].idxmin().strftime('%d.%m')}.")
            if len(post)<20: notes.append(f"נמדדו {len(post)} ימי מסחר מתוך 20; השאר טרם התקיימו.")
        if ov.get('note'): notes.append(ov['note'])
        if t in CHART30: notes.append(CHART30[t])
        if a['source']=='ilan':
            gk=sorted((x[0],x[1],x[3]) for x in app.get(t,[]) if x[2]=='grok')
            TYP={'near-low':'שפל שנתי','prebreakout':'לפני פריצה','momentum':'מומנטום'}
            if gk: notes.append("אימות סוג מול Grok automation: "+', '.join(f"{fdot(d_)} {TYP[c_]} ({dr})" for d_,dr,c_ in gk)+". כל ההופעות אחרי צילום הגרף, ולכן לא שימשו לקביעת תאריך הסריקה.")
            else: notes.append("המניה לא מופיעה באף אחת מ-21 ריצות Grok automation (7–28.09). "+("תאריך הסריקה נשאר חסר." if not a['alert_date'] else "הסוג לא אומת מול Grok."))
        r['notes']=notes; rows.append(r)
    for r in rows:
        if r['source'] in PP:
            r['notes']=[n.replace('מחיר גרוק','מחיר Perplexity').replace('מחיר Grok','מחיר Perplexity').replace('Grok','Perplexity') if i>0 else n for i,n in enumerate(r['notes'])]
    for r in rows:
        mu,src=None,None
        for k,lab in (('mcap_override','גרף אילן'),('orig_mcap','גיליון מקורי')):
            v=pmc(r.get(k))
            if v: mu,src=v,lab; break
        if mu is None and not r.get('mcap') and info.get(r['ticker'],{}).get('mcap'): r['mcap_now']=info[r['ticker']]['mcap']; mu,src=r['mcap_now'],'Yahoo (שווי נוכחי; אין תאריך התראה)'
        if mu is None and r.get('mcap'): mu,src=r['mcap'],'Yahoo (שווי נוכחי × מחיר סגירה ביום שלפני ההתראה / מחיר נוכחי)'
        if mu is None and r.get('ttype')=='קריפטו' and r['ticker'].endswith('(קריפטו)'):
            cg=CG.get(r['sym'])
            if cg and cg.get('mcap'): mu,src=cg['mcap'],f"CoinGecko ({cg['id']}, שווי ב-{cg['date'][8:10]}.{cg['date'][5:7]})"
        if r.get('ttype')=='קריפטו' and mu is not None and src and src.startswith('Yahoo'): src='Yahoo (שווי נוכחי × מחיר לפני ההתראה / מחיר נוכחי)'
        r['mcap_used'],r['mcap_src']=mu,src
        r['excluded']=bool(mu is not None and mu<1.5e9)
    return rows
if __name__=='__main__':
    rows=run(); pd.to_pickle(rows,'rows_all.pkl')
    for r in rows: print(r['source'],r['alert_date'],r['ticker'],r['dir'],r['ndays'],r['outcome'],r['cum'][-1] if r['cum'] else None, r['notes'][1][:110] if r['source']=='orig' and len(r['notes'])>1 else '')
