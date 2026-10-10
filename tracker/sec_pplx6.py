# ---- Perplexity tab (added 07.10.2026)
import sys as _sys; _sys.path.insert(0,'pplx')
from alerts import _ct
from pplx_setups import RUNS as P_RUNS, parse_all as p_parse, MODEL as P_MODEL
from stats3 import PPS, PPN
_prows,_pskip=p_parse()
px=wb.create_sheet('Perplexity',2); px.sheet_view.rightToLeft=True
def ph(rr,cols,h=36):
    for j,h_ in enumerate(cols,1):
        c=px.cell(rr,j,h_); c.fill=HF; c.font=HFont; c.alignment=C; c.border=B
    px.row_dimensions[rr].height=h
def pt(rr,t): px.cell(rr,1,t).font=Font(name='Arial',bold=True,size=13,color='356854')
def pp(rr,t,h=34,size=9,ncol=18):
    c=px.cell(rr,1,t); c.font=Font(name='Arial',size=size); c.alignment=R; px.merge_cells(start_row=rr,end_row=rr,start_column=1,end_column=ncol); px.row_dimensions[rr].height=h
def pcell(rr,j,x,fmt_=None,bold=False,fill=None):
    c=px.cell(rr,j,x if x is not None else '—'); c.font=Font(name='Arial',size=10,bold=bold); c.border=B; c.alignment=C
    if fmt_ and x is not None and not isinstance(x,str): c.number_format=fmt_
    if fill: c.fill=fill
    return c
PF=[r for r in rows_full if r['source'] in PPS]
pt(1,'Perplexity — סריקות שנוספו ב-07.10.2026 (מקור נפרד, לא מעורבב עם הבוט או Grok)')
pp(2,f"{len(_prows)+len(_pskip)} סטאפים ב-{len(P_RUNS)} הרצות של Perplexity Tasks (12.08–04.10). נקלטו {len(_prows)}; {len(_pskip)} לא נקלטו (הרצת 13.08 החזירה טיקרים מוסתרים XXXX1–XXXX10). מתוכם {sum(r['excluded'] for r in PF)} הוחרגו (MCAP<1.5B ביום ההתראה) ו-{sum(not r['excluded'] for r in PF)} בלשונית הראשית. מקורות: Perplexity v2.7 (ריצות שבועיות 13.9, 20.9, 27.9, 4.10 + ריצת Computer מ-7.9), Perplexity v2.5 (6.9), Perplexity value/turnaround (14–16.8), Perplexity momentum (12.8), Perplexity crypto (12–13.8).",44,10)
pt(4,'1. הרצות')
RH=['ריצה','מקור','תאריך ריצה','שעת ריצה (לפי הפלט / מאומת)','יום 1','קבצים','סטאפים בפלט','נקלטו','בלשונית הראשית','הוחרגו <1.5B','כניסה = מחיר/טריגר מהטבלה','כניסה = פתיחה','עם סטופ+TP1','לא הופעל','TP1','סטופ','פתוח','ממוצע תשואה','הערות']
ph(5,RH); k=6
RNOTE={'T01':"אין מחיר כניסה, סטופ ויעדים בטבלה ('~' בכל העמודות; הציונים מסומנים משוערים). כניסה = פתיחת 05.10, בלי סטופ/יעד — נספר בתשואות בלבד.",
 'T02':"כל העמודות המספריות '~' (גם מחיר נוכחי וציון). כניסה = פתיחת 28.09, בלי סטופ/יעד — נספר בתשואות בלבד.",
 'T03':"רמות מספריות מסומנות '~' (משוער) — נלקחו כמו שהן. עמודת הניקוד מכילה טווח אחזקה ('~10–18 ימי מסחר') — הניקוד חסר. טבלה מ-18.09 16:00 ET.",
 'T04':"רמות מספריות (חלקן '~'). עמודת הניקוד מכילה טווח אחזקה — הניקוד חסר.",
 'C0907':"ריצת Computer, נתונים מסגירת 04.09. CSV + קובץ md זהים בתוכן.",
 'T12':"גרסה v2.5, נתונים מסגירת 04.09. שני קובצי CSV זהים + גרסה מקוצרת (a2) של אותה ריצה — נספרו פעם אחת.",
 'T05':"טבלה איכותית: הרמות מתוארות במילים ('שפל 52 שבועות פחות ~3–5%', 'אזור SMA200'). נקראו רק מספרים מפורשים או ייחוסים מוגדרים (שפל 52ש, SMA200, אמצע טווח 52ש) שחושבו מנתוני Yahoo. כניסה = פתיחה (הטריגר הוא תנאי, לא מחיר), חוץ מ-JPC (שבירת 7.22).",
 'T06':"כנ\"ל. סטופ 'מתחת לשפל 52 שבועות' חושב מ-Yahoo; יעדים מספריים רק ב-STNE ו-XP.",
 'T07':"כנ\"ל. יעדים באחוזים (+15%/+20%) חושבו מהכניסה; סטופים 'מתחת לשפל אחרון' לא מוגדרים — הושארו ריקים.",
 'T08':"הטיקרים מוסתרים בפלט (XXXX1–XXXX10) גם ב-PDF וגם ב-CSV — לא ניתן לבקטסט. לא נקלט.",
 'T10':"כל הרמות איכותיות (MA20, שיא מקומי, פיבו) — אין מספרים. כניסה = פתיחת 13.08, בלי סטופ/יעד.",
 'T09':"BTC/ETH/HYPE עם טריגר מספרי; SOL/LINK/BEAT עם סטופ ויעדים מספריים וטווח כניסה (כניסה = פתיחה). בשורות APR ו-HYPE עמודות ה-CSV מוזזות בעמודה אחת — נקרא לפי התוכן.",
 'T11':"כל הרמות איכותיות — כניסה = פתיחת הנר השעתי הראשון אחרי הריצה, בלי סטופ/יעד. APR ו-CAP לא קיימים ב-Yahoo."}
for rid,R0 in P_RUNS.items():
    rr=[r for r in PF if r.get('run')==rid]; kept=[r for r in rr if not r['excluded']]
    w_=[r for r in kept if r['cum'] and r['outcome'] not in ('לא הופעל','מחיר לא תואם')]
    nsk=sum(1 for x in _pskip if x['run']==rid)
    v=[rid,P_MODEL[R0['src']],fd(R0['date']),_ct(R0['created']),(fd(R0['day1']) if R0.get('day1') else 'שעה אחרי הריצה (ימים קלנדריים)'),R0['file']+' + '+R0['csv'],
       len(rr)+nsk,len(rr),len(kept),sum(r['excluded'] for r in rr),sum(1 for r in rr if not r.get('fixed') and r['entry'] is not None and r['outcome']!='אין נתונים'),sum(bool(r.get('fixed')) for r in rr),
       sum(1 for r in kept if r['sl'] is not None and r['tps'][0] is not None),sum(r['outcome']=='לא הופעל' for r in kept),sum(r['outcome']=='TP1' for r in kept),sum(r['outcome']=='סטופ' for r in kept),sum(r['outcome']=='פתוח' for r in kept),
       (float(np.mean([r['cum'][-1] for r in w_])) if w_ else None),RNOTE.get(rid,'')]
    for j,x in enumerate(v,1):
        c=pcell(k,j,x,'0.0%' if j==18 else None)
        if j in (6,19): c.alignment=R
    px.row_dimensions[k].height=58; k+=1
k+=1; pt(k,'2. סטטיסטיקה לפי מקור (אחרי החרגת MCAP<1.5B וניקוי כפילויות) — מול בוט v2.8 ו-Grok על אותם נתונים מעודכנים'); k+=1
SH=['קבוצה','שורות','עם נתונים','לא הופעל','ללא סטופ/יעד (תשואות בלבד)','TP1','סטופ','פתוחים','הצלחה TP1/(TP1+סטופ)','תשואה ממוצעת','% ברווח','ממוצע יום 5','ממוצע יום 10','ממוצע יום 20','MFE','MAE']
ph(k,SH,48); k+=1
SD_=dict(S); SSD=dict(SS)
PLIST=[]
for k_ in PPS: PLIST+=[f'{PPN[k_]} — סה"כ',f'{PPN[k_]} — LONG',f'{PPN[k_]} — SHORT']
PLIST+=['Perplexity — כל המקורות','Perplexity — LONG','Perplexity — SHORT','Perplexity v2.7+v2.5 — עם רמות מספריות']
CMP=['בוט v2.8 — סה"כ','בוט — LONG','בוט — SHORT','GROK automation — סה"כ','GROK automation — LONG','GROK automation — SHORT','GROK crypto — סה"כ','GROK portfolio-news-scan — סה"כ','GROK x-trends-digest — סה"כ','גיליון מקורי (יולי–אוג׳) — סה"כ']
CMPF=PatternFill('solid',fgColor='EEEEEE')
for g in PLIST+CMP:
    s_=SD_.get(g) or SSD.get(g)
    if s_ is None: continue
    v=[g,s_['n'],s_['n_data'],s_['untrig'],s_['nolev'],s_['tp1'],s_['stop'],s_['open'],s_['hit'],s_['avg_ret'],s_['win_mtm'],s_['d5'],s_['d10'],s_['d20'],s_['mfe'],s_['mae']]
    for j,x in enumerate(v,1): pcell(k,j,x,'0.0%' if j>=9 else None,bold=('סה"כ' in g or 'כל המקורות' in g),fill=CMPF if g in CMP else None)
    k+=1
pp(k,"'עם נתונים' = שורות עם ימי מסחר, בלי 'לא הופעל'. 'לא הופעל' = מחיר הכניסה/טריגר מהטבלה לא נסחר בחלון 20 הימים, ולכן לפי הכלל (סטופ/TP נספרים רק אחרי שהכניסה נסחרה) העסקה לא נפתחה — לא נספרת בהצלחה ולא בתשואות. 'ללא סטופ/יעד' = אין סטופ מספרי וגם אין TP1 מספרי (או רק אחד מהם) — נספרת רק בממוצעי התשואה. שורות אפורות = מקורות קיימים להשוואה.",40); k+=2
pt(k,'3. ראש בראש: Perplexity מול בוט v2.8 / GROK automation באותו יום 1 (ממוצע ביום N המשותף)'); k+=1
ph(k,['השוואה','חלון (ימים)','בוט/Grok: סטאפים','בוט/Grok: ממוצע ביום N','בוט/Grok: % ברווח','בוט/Grok: TP1/סטופ','Perplexity: סטאפים','Perplexity: ממוצע ביום N','Perplexity: % ברווח','Perplexity: TP1/סטופ','טיקרים משותפים']); k+=1
for lab,N,b_,p_,ov in AFTER['H2P']:
    v=[lab,N,b_['n'],b_['avg'],b_['win'],f"{b_['tp1']}/{b_['stop']}",p_['n'],p_['avg'],p_['win'],f"{p_['tp1']}/{p_['stop']}",', '.join(ov) or '—']
    for j,x in enumerate(v,1): pcell(k,j,x,'0.0%' if j in (4,5,8,9) else None)
    k+=1
pp(k,"Perplexity בלי שורות 'לא הופעל'. בריצות 27.9 ו-4.10 של Perplexity אין סטופ/יעדים, ולכן TP1/סטופ = 0/0 והשוואה רק לפי תשואה.",24); k+=2
P_PAIRS=[p for p in PAIRS if p['a']['source'] in PPS or p['b']['source'] in PPS]
pt(k,f'4. סתירות לונג/שורט שמערבות את Perplexity ({len(P_PAIRS)} זוגות; בתוך Perplexity ומול בוט / Grok / הגיליון המקורי)'); k+=1
ph(k,['טיקר','צד א׳: תאריך','צד א׳: מקור','צד א׳: כיוון','צד א׳: תוצאה','צד א׳: תשואה','צד ב׳: תאריך','צד ב׳: מקור','צד ב׳: כיוון','צד ב׳: תוצאה','צד ב׳: תשואה','חפיפה','מנצח','סוג']); k+=1
for p in sorted(P_PAIRS,key=lambda p:(p['ticker'],p['a']['alert_date'])):
    a,b=p['a'],p['b']; both=a['source'] in PPS and b['source'] in PPS
    v=[p['ticker'],fd(a['alert_date']),srcl(a),a['dir'],a['outcome'],a['cum'][-1] if a['cum'] else None,fd(b['alert_date']),srcl(b),b['dir'],b['outcome'],b['cum'][-1] if b['cum'] else None,p['act'],p['winner'],'בתוך Perplexity' if both else 'מול מקור אחר']
    for j,x in enumerate(v,1): pcell(k,j,x,'0.0%' if j in (6,11) else None)
    px.row_dimensions[k].height=30; k+=1
k+=1
OPEN_P=[r for r in PF if not r['excluded'] and r['ndays']>0 and r['ndays']<(20) and r['outcome'] in ('פתוח','ללא סטופ/יעד')]
pt(k,f'5. עסקאות Perplexity פתוחות כרגע (בתוך חלון 20 הימים, בלי TP1/סטופ עד סגירת 07.10): {len(OPEN_P)}'); k+=1
ph(k,['מקור','תאריך','טיקר','כיוון','כניסה','סטופ','TP1','ימים שנמדדו','תשואה עד כה','MFE','MAE','סטטוס']); k+=1
for r in sorted(OPEN_P,key=lambda r:(r['alert_date'],r['source'],r.get('rank') or 0)):
    v=[r['model'],fd(r['alert_date']),r['ticker'],r['dir'],r['entry'],r['sl'],r['tps'][0],r['ndays'],r['cum'][-1] if r['cum'] else None,r['mfe'],r['mae'],r['outcome']]
    for j,x in enumerate(v,1): pcell(k,j,x,'0.0%' if j in (9,10,11) else (USD if j in (5,6,7) else None))
    k+=1
k+=1
pt(k,'6. בעיות פענוח ונתונים'); k+=1
PROB=["הרצת value/turnaround מ-13.08 (T08): הטיקרים מוסתרים (XXXX1–XXXX10) גם ב-PDF וגם ב-CSV — 10 סטאפים לא נקלטו.",
 "הרצות v2.7 מ-27.9 ו-4.10: אין מחיר כניסה, סטופ או יעדים ('~' בכל העמודות; ב-27.9 גם המחיר הנוכחי והציון). נקלטו עם כניסה = פתיחת יום 1, בלי סטופ/יעד — נספרות בתשואות בלבד.",
 "הרצות v2.7 מ-13.9 ו-20.9: עמודת הניקוד מכילה טווח אחזקה במקום ציון — הציון נשאר ריק. רוב הרמות מסומנות '~' (משוער) ונלקחו כמו שהן.",
 "קובצי ה-PDF של value / momentum / crypto חתוכים בצד (העמודות האחרונות לא נכנסו לעמוד), ובעברית הטקסט מבולגן. לכן הרמות נקראו מקובצי ה-CSV של אותן טבלאות; נבדק שאין ב-PDF סטאפים שלא קיימים ב-CSV.",
 "רמות איכותיות (שיא מקומי, התנגדות, MA20, דיסקאונט ל-NAV, 'שפל אחרון') הושארו ריקות. ייחוסים מוגדרים (שפל 52 שבועות, SMA200, אמצע טווח 52 שבועות) חושבו מנתוני Yahoo לפני יום 1, ומצוינים בהערות השורה. טווח (למשל '20–22$') → הגבול הקרוב לכניסה.",
 "כלל סטטיסטיקה: כשיש רק סטופ או רק TP1, שניהם הוסרו לצורך התוצאה (הרמה נשמרת בהערה), כדי לא להטות את אחוז ההצלחה. כך ב-"+str(sum(1 for r in PF if r.get('partial_levels')))+" שורות: "+', '.join(f"{r['ticker'].replace('-USD','').replace('11841','')} {fd(r['alert_date'])}" for r in PF if r.get('partial_levels'))+".",
 "קריפטו: APR ו-CAP לא קיימים ב-Yahoo (אין חישוב) ומתחת 1.5B לפי CoinGecko — הוחרגו. BEAT, VELVET, ARB ו-ENA היו מתחת 1.5B ביום ההתראה — הוחרגו. בשורות APR ו-HYPE (13.8) עמודות ה-CSV מוזזות — נקרא לפי התוכן.",
 "הרצת v2.5 (6.9) הופיעה בשני קובצי CSV זהים ובשתי גרסאות PDF (מלאה ומקוצרת) — נספרה פעם אחת. ריצת ה-Computer מ-7.9 הופיעה כ-CSV וכ-md זהים — נספרה פעם אחת.",
 "בגיליון המקורי יש כבר 2 שורות עם מודל Perplexity (SKHY 17.07 בלי רמות, CMCSA בלי תאריך). הן נשארו תחת 'גיליון מקורי' ולא נכפלו."]
for t in PROB: pp(k,t,30); k+=1
for j,wd in enumerate([34,22,12,14,13,40,10,9,10,10,12,11,11,10,8,8,8,11,70],1): px.column_dimensions[L(j)].width=wd
P_SUM=dict(runs=[[rid,P_MODEL[R0['src']],R0['date'],sum(1 for r in PF if r.get('run')==rid),sum(1 for r in PF if r.get('run')==rid and r['excluded']),sum(1 for x in _pskip if x['run']==rid)] for rid,R0 in P_RUNS.items()],
   stats=[[g,(SD_.get(g) or SSD.get(g))] for g in PLIST+CMP if (SD_.get(g) or SSD.get(g))],H2P=AFTER['H2P'],
   pairs=[[p['ticker'],fd(p['a']['alert_date']),srcl(p['a']),p['a']['dir'],p['a']['outcome'],p['a']['cum'][-1] if p['a']['cum'] else None,fd(p['b']['alert_date']),srcl(p['b']),p['b']['dir'],p['b']['outcome'],p['b']['cum'][-1] if p['b']['cum'] else None,p['winner']] for p in sorted(P_PAIRS,key=lambda p:(p['ticker'],p['a']['alert_date']))],
   open=[[r['model'],r['alert_date'],r['ticker'],r['dir'],r['entry'],r['sl'],r['tps'][0],r['ndays'],r['cum'][-1] if r['cum'] else None,r['outcome']] for r in sorted(OPEN_P,key=lambda r:(r['alert_date'],r['source']))],
   prob=PROB,nparsed=len(_prows),nskip=len(_pskip),nexcl=sum(r['excluded'] for r in PF),nkept=sum(not r['excluded'] for r in PF))
