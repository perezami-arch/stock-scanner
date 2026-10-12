import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import pandas as pd, numpy as np, ast
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.formula import ArrayFormula
from stats2 import rows, S, st, SS, TS, H2H, OVL, excl, gk, rows_full
HEAD=ast.literal_eval(open('headers.txt').read())+['סוג טרייד / סורק']
HF=PatternFill('solid',fgColor='356854'); HFont=Font(name='Arial',bold=True,color='FFFFFF',size=10)
STR=PatternFill('solid',fgColor='F3F7F5'); F=Font(name='Arial',size=10)
SRCFILL={'orig':PatternFill('solid',fgColor='EAF1FB'),'ilan':PatternFill('solid',fgColor='FFF7E0'),'grok':PatternFill('solid',fgColor='F1ECF8')}
thin=Side(style='thin',color='356854'); B=Border(left=thin,right=thin,top=thin,bottom=thin)
C=Alignment(horizontal='center',vertical='center',wrap_text=True); R=Alignment(horizontal='right',vertical='top',wrap_text=True,readingOrder=2)
USD='"$"#,##0.00'; PCT='0.00%'; DATE='dd/mm/yyyy'
def mc(x): return '' if x is None else (f"{x/1e12:.3f}T" if x>=1e12 else f"{x/1e9:.2f}B")
order={'orig':0,'ilan':1,'bot':2,'grok':3}
CATO={'near-low':0,'prebreakout':1,'momentum':2}
rows=sorted(rows,key=lambda r:(r['alert_date'] or '9999',order[r['source']],CATO.get(r.get('cat'),9),r.get('rank') or 0,r['ticker']))
wb=Workbook(); ws=wb.active; ws.title='מעקב סריקות'; ws.sheet_view.rightToLeft=True
for j,h in enumerate(HEAD,1):
    c=ws.cell(1,j,h); c.fill=HF; c.font=HFont; c.alignment=C; c.border=B
ws.row_dimensions[1].height=32
d=pd.read_pickle('prices_all.pkl')
stale={'PANW':'21.09','HD':'21.09','XOM':'21.09','ABBV':'21.09','SBUX':'21.09','KO':'21.09','NOW':'22.09','ADBE':'22.09','AMD':'22.09','BAC':'22.09'}
for i,r in enumerate(rows,2):
    t=r['ticker']; o=r['opt']; notes=list(r['notes'])
    if r['source']=='bot' and r['alert_date']=='2026-09-24':
        c23=float(d[t].loc['2026-09-23','Close'])
        notes.append(f"פער נתונים: מחיר ההתראה הוא סגירת {stale[t]} (הסריקה רצה 24.09 03:30 בלי סגירת 23.09 = ${c23:.2f}, {c23/r['entry']-1:+.2%} מול מחיר ההתראה). יום 1 = 24.09.")
    if t=='GOLD': notes.append("אזהרה: לפי Yahoo הטיקר GOLD הוא כעת Gold.com, Inc. (לא Barrick, שעבר לטיקר B). הסריקה תיארה אותו ככורה זהב. הנתונים כאן הם של GOLD כמו בסריקה.")
    mcap = r.get('mcap_override') or (r.get('orig_mcap').strip() if isinstance(r.get('orig_mcap'),str) and r.get('orig_mcap').strip() else None) or mc(r['mcap_used'])
    if r['source']=='grok' and r.get('fixed'):
        notes=[n_.replace('פערי פענוח:','פערי פענוח (לפני התיקון):').replace(' לא הוזן מחיר/סטופ/יעד שלא הופיע בטבלה.','') for n_ in notes]
    if r['source']=='grok':
        same=[x for x in gk if x['ticker']==t and x['alert_date']==r['alert_date'] and x is not r]
        for x in same: notes.append(f"כפילות בתוך אותה ריצת Grok: {t} מופיע גם בקטגוריה {x['cat']} ({x['dir']}) באותו תאריך."+(" סתירת כיוון." if x['dir']!=r['dir'] else " אותו כיוון, ונשמרו שתי השורות כי זו המלצה בסורק אחר (לא כפילות מול הגיליון המקורי)."))
        bo=[x for x in rows_full if x['source']=='bot' and x['ticker']==t]
        for x in bo: notes.append(f"מופיע גם בבוט v2.8 ב-{pd.Timestamp(x['alert_date']).strftime('%d.%m')} ({x['dir']})"+(" — כיוון הפוך." if x['dir']!=r['dir'] else "."))
    vals={1:r['model'],2:(pd.Timestamp(r['alert_date']).to_pydatetime() if r['alert_date'] else 'חסר תאריך'),5:t,6:r['rep'] or None,7:mcap,
          8:(round(r['atr'],4) if r['atr'] is not None else None),9:r['dir'],10:r['entry'],13:r['sl'],15:r['tsl'],16:r['tps'][0],17:r['tps'][1],18:r['tps'][2],
          22:r['hold'],45:' '.join(notes),46:r.get('ttype') or None}
    if o: vals.update({3:o[0].to_pydatetime(),4:o[1].to_pydatetime(),11:round(o[2],2),12:round(o[3],2),23:int(o[4])})
    for k,cum in enumerate(r['cum']): vals[24+k]=round(float(cum),4)
    if r['cum']: vals[44]=round(float(r['cum'][-1]),5)
    rw=str(i)
    vals[14]=f'=IF(ISBLANK(M{rw}),"",IFERROR(IF(I{rw}="SHORT",(M{rw}/J{rw})-1,1-(M{rw}/J{rw})),""))'
    for col,src in [(19,'P'),(20,'Q'),(21,'R')]:
        vals[col]=f'=IF(ISBLANK({src}{rw}),"",IFERROR(IF(I{rw}="SHORT",1-({src}{rw}/J{rw}),({src}{rw}/J{rw})-1),""))'
    fill=SRCFILL.get(r['source'], STR if i%2 else None)
    for j in range(1,47):
        c=ws.cell(i,j,vals.get(j)); c.font=F; c.border=B; c.alignment=C
        if fill: c.fill=fill
        if j in (2,3,4): c.number_format=DATE
        elif j in (10,11,12,13,16,17,18): c.number_format=USD
        elif j in (8,15,14,19,20,21) or 24<=j<=44: c.number_format=PCT
        if j==44: c.number_format='0.000%'
        if j in (45,6): c.alignment=R
    ws.row_dimensions[i].height=100
NROWS=len(rows)+1
widths={1:22,2:12,3:13,4:13,5:8,6:30,7:10,8:9,9:8,22:12,23:11,44:11,45:100,46:22}
for j in range(1,47): ws.column_dimensions[L(j)].width=widths.get(j,10)
ws.freeze_panes='F2'
dv=DataValidation(type='list',formula1='"LONG,SHORT"',allow_blank=True); ws.add_data_validation(dv); dv.add(f'I2:I{NROWS}')
ws.auto_filter.ref=f"A1:{L(46)}{NROWS}"

# ---- Summary
sm=wb.create_sheet('סיכום'); sm.sheet_view.rightToLeft=True
def hdr(rr,cols):
    for j,h in enumerate(cols,1):
        c=sm.cell(rr,j,h); c.fill=HF; c.font=HFont; c.alignment=C; c.border=B
    sm.row_dimensions[rr].height=48
def title(rr,txt): sm.cell(rr,1,txt).font=Font(name='Arial',bold=True,size=13,color='356854')
def para(rr,txt,h=40,size=10):
    c=sm.cell(rr,1,txt); c.font=Font(name='Arial',size=size); c.alignment=R; sm.merge_cells(start_row=rr,end_row=rr,start_column=1,end_column=14); sm.row_dimensions[rr].height=h
title(1,'סיכום בקטסט סריקות — נתוני מחיר אמיתיים (Yahoo Finance) עד סגירת 29.09.2026')
COLS=['קבוצה','שורות','עם נתוני מסחר','ימים נמדדו (מקס׳)','TP1 לפני סטופ','סטופ לפני TP1','פתוחים','אחוז הצלחה (TP1 מתוך מוכרעים)','TP2 הושג','תשואה ממוצעת (יום אחרון)','% ברווח','תשואה ממוצעת לפי כללים','ממוצע יום 5','ממוצע יום 10','ממוצע יום 20','MFE ממוצע','MAE ממוצע']
KEYS=['n','n_data','days','tp1','stop','open','hit','tp2','avg_ret','win_mtm','avg_rule','d5','d10','d20','mfe','mae']
def stable(rr,groups):
    hdr(rr,COLS)
    for i,(g,s) in enumerate(groups,rr+1):
        v=[g]+[s[k] for k in KEYS]
        for j,x in enumerate(v,1):
            c=sm.cell(i,j,x if x is not None else '—'); c.font=Font(name='Arial',size=10,bold=('סה"כ' in g)); c.border=B; c.alignment=C
            if j in (8,10,11,12,13,14,15,16,17) and x is not None: c.number_format='0.0%'
            if i%2==1: c.fill=STR
    return rr+len(groups)+2
nx=stable(3,S)
para(nx-1,'הערות: סריקת הבוט מ-30.09 פורסמה היום לפני המסחר ואין לה עדיין נתונים. ריצות Grok מ-25.09 ו-28.09 נמדדו על 3 ו-2 ימים בלבד. גרפים של אילן: בלי סטופ ויעדים, התשואה ממועד הצילום בכיוון לונג. כל הקבוצות אחרי החרגת MCAP<1.5B ובלי שורות עם מחיר לא תואם.',30,9)
title(nx+1,'פילוח לפי מקור (אחרי החרגת MCAP<1.5B)'); nx=stable(nx+2,SS)
title(nx+1,'פילוח לפי סוג טרייד (שפל שנתי / לפני פריצה / מומנטום / Elliott v2.8)'); nx=stable(nx+2,TS)
TT=TS
para(nx-1,"כל השורות של Grok נכללות, כולל 32 שבהן מחיר הכניסה = פתיחת יום 1 (מחיר Grok לא תאם לשוק או חסר). שורות בלי סטופ ויעדים נכללות רק בממוצעי התשואה. 'שורות' = כל השורות בקבוצה.",30,9)
title(nx,'ראש בראש: בוט v2.8 מול GROK automation באותם תאריכים / תאריכים סמוכים')
hdr(nx+1,['השוואה','חלון (ימים)','בוט: סטאפים','בוט: ממוצע ביום N','בוט: % ברווח','בוט: TP1/סטופ','Grok: סטאפים','Grok: ממוצע ביום N','Grok: % ברווח','Grok: TP1/סטופ','Grok שפל שנתי','Grok לפני פריצה','Grok מומנטום','טיקרים משותפים'])
k=nx+2
for lab,N,b_,g_,cats,ov in H2H:
    v=[lab,N,b_['n'],b_['avg'],b_['win'],f"{b_['tp1']}/{b_['stop']}",g_['n'],g_['avg'],g_['win'],f"{g_['tp1']}/{g_['stop']}"]+[(f"{cats[c]['avg']*100:+.1f}% (n={cats[c]['n']})" if cats[c]['avg'] is not None else '—') for c in ['near-low','prebreakout','momentum']]+[', '.join(ov) or '—']
    for j,x in enumerate(v,1):
        c=sm.cell(k,j,x); c.font=F; c.border=B; c.alignment=C
        if j in (4,5,8,9) and x is not None: c.number_format='0.0%'
    k+=1
para(k,"ממוצע ביום N = תשואה מצטברת מותאמת כיוון ביום המסחר ה-N, כש-N הוא החלון המשותף לשני הצדדים. TP1/סטופ = התוצאה על כל החלון הזמין (בוט 24.9 כולל יום נוסף). טיקרים שהופיעו גם בבוט וגם ב-Grok (בכל תאריך): "+', '.join(OVL)+". SNDK 7.9: הבוט המליץ שורט, ו-Grok לונג (מומנטום) — ראו בהערות השורות.",40,9)
nx=k+2
w=[r for r in rows if r['cum'] and r['source']!='ilan' and r['outcome']!='מחיר לא תואם']; w.sort(key=lambda r:r['cum'][-1],reverse=True)
def tbl(rr,name,items):
    title(rr,name); hdr(rr+1,['מקור','תאריך','טיקר','כיוון','סוג','תשואה (יום אחרון)','ימים','תוצאה','MFE','MAE'])
    for k,r in enumerate(items,rr+2):
        v=[r['group'],pd.Timestamp(r['alert_date']).strftime('%d.%m.%Y'),r['ticker'],r['dir'],r.get('ttype'),r['cum'][-1],r['ndays'],r['outcome'],r['mfe'],r['mae']]
        for j,x in enumerate(v,1):
            c=sm.cell(k,j,x); c.font=F; c.border=B; c.alignment=C
            if j in (6,9,10): c.number_format='0.00%'
    return rr+2+len(items)+1
nx=tbl(nx,'8 הטובים ביותר (בוט + גיליון + Grok)',w[:8]); nx=tbl(nx,'8 החלשים ביותר (בוט + גיליון + Grok)',w[::-1][:8])
# Ilan charts table
il=[r for r in rows if r['source']=='ilan']
title(nx,'גרפים של אילן (TradingView) — ביצועים ממועד הצילום'); hdr(nx+1,['טיקר','צולם','תאריך סריקה תואם','מקור תואם','סוג','מחיר בגרף','מבט לונג','מבט שורט','ימים','MFE (לונג)','MAE (לונג)'])
for k,r in enumerate(il,nx+2):
    v=[r['ticker'],pd.Timestamp(r['calc_date']).strftime('%d.%m.%Y'),pd.Timestamp(r['alert_date']).strftime('%d.%m.%Y') if r['alert_date'] else 'חסר תאריך',r.get('matched') or '—',r.get('ttype') or '',r['entry'],
       r['cum'][-1] if r['cum'] else None,-r['cum'][-1] if r['cum'] else None,r['ndays'],r['mfe'],r['mae']]
    for j,x in enumerate(v,1):
        c=sm.cell(k,j,x); c.font=F; c.border=B; c.alignment=C
        if j in (7,8,10,11): c.number_format='0.00%'
        if j==6: c.number_format=USD
nx=nx+2+len(il)+1
bot=[r for r in rows if r['source']=='bot' and r['cum']]
tight=[r for r in bot if abs(1-r['sl']/r['entry'])<r['atr']]; wide=[r for r in bot if r not in tight]
rr1=[abs(r['tps'][0]/r['entry']-1)/abs(1-r['sl']/r['entry']) for r in rows if r['source']=='bot']
sb=dict(S)
TD=dict(TS); SD=dict(SS); g_=SD['GROK automation — סה"כ']; b_=SD['בוט v2.8 — סה"כ']; o_=SD['גיליון מקורי (יולי–אוג׳) — סה"כ']
nfm=sum(r.get('fixed')=='mismatch' for r in gk); nfx=sum(r.get('fixed')=='missing' for r in gk)
pc=lambda x: '—' if x is None else f"{x*100:+.1f}%"
hr=lambda x: '—' if x is None else f"{x*100:.0f}%"
LESSONS=[
 f"1. מקורות (אחרי החרגת MCAP<1.5B). בוט v2.8: {b_['tp1']} TP1 מול {b_['stop']} סטופים ({hr(b_['hit'])} הצלחה), ממוצע {pc(b_['avg_ret'])}. GROK automation: {g_['tp1']} TP1 מול {g_['stop']} סטופים ({hr(g_['hit'])}), ממוצע {pc(g_['avg_ret'])} על {g_['n_data']} סטאפים. גיליון מקורי (יולי–אוג׳, 20 ימים): {o_['tp1']}/{o_['stop']} ({hr(o_['hit'])}), ממוצע {pc(o_['avg_ret'])}. הבוט מדויק יותר ומפסיד פחות (MAE {pc(b_['mae'])} מול {pc(g_['mae'])} ב-Grok), אבל המדגם שלו קטן ({b_['n_data']} מול {g_['n_data']}).",
 f"2. ראש בראש 7.9 (אותו יום 1, 16 ימים): בוט {pc(H2H[0][2]['avg'])} ממוצע ו-{H2H[0][2]['tp1']}/{H2H[0][2]['stop']} TP1/סטופ, מול Grok {pc(H2H[0][3]['avg'])} ו-{H2H[0][3]['tp1']}/{H2H[0][3]['stop']}. ב-24/25.9 וב-27/28.9 החלון קצר מדי (2–3 ימים) להכרעה, והתוצאות קרובות לאפס בשני הצדדים. SNDK ב-7.9: הבוט שורט, Grok לונג.",
 f"3. לפי סוג ב-Grok: 'לפני פריצה' שורט הוא הטוב ביותר ({TD['לפני פריצה — GROK SHORT']['tp1']}/{TD['לפני פריצה — GROK SHORT']['stop']}, ממוצע {pc(TD['לפני פריצה — GROK SHORT']['avg_ret'])}), ו'לפני פריצה' לונג הוא החלש ({TD['לפני פריצה — GROK LONG']['tp1']}/{TD['לפני פריצה — GROK LONG']['stop']}, {pc(TD['לפני פריצה — GROK LONG']['avg_ret'])}). 'מומנטום' לונג: ממוצע {pc(TD['מומנטום — GROK LONG']['avg_ret'])}, אבל {TD['מומנטום — GROK LONG']['stop']} סטופים מול {TD['מומנטום — GROK LONG']['tp1']} TP1. 'מומנטום' שורט הוא המסוכן ביותר: MAE {pc(TD['מומנטום — GROK SHORT']['mae'])}, וב-VICR (14.9) הושג TP1 ואחר כך המניה עלתה ב-47%. שורט נגד מומנטום חם דורש סטופ קשיח ויציאה ב-TP1.",
 f"4. 'שפל שנתי': ב-Grok automation נשארו רק {TD['שפל שנתי — GROK automation']['n']} מתוך 70 אחרי החרגת MCAP (44 היו מיקרו-קאפ), עם {TD['שפל שנתי — GROK automation']['tp1']}/{TD['שפל שנתי — GROK automation']['stop']} וממוצע {pc(TD['שפל שנתי — GROK automation']['avg_ret'])}. הגיליון המקורי ({hr(o_['hit'])} הצלחה, {pc(o_['avg_ret'])}) עדיין הכי רווחי, אבל נמדד על חלון ארוך יותר (20 ימים) ובתקופה אחרת. מומלץ שהסורק יסנן MCAP≥1.5B כבר בשלב הסריקה.",
 f"5. איכות נתונים ב-Grok: ב-{nfm} סטאפים המחיר בטבלה היה רחוק ב-8%–42% ממחיר השוק (בעיקר 'לפני פריצה': APA 24.8 מול 42.8, BIIB 132 מול 220.8, HPQ 21.4 מול 35.5), וב-{nfx} לא היה מחיר (טווח, 'ליד שפל' או רק אחוזים). לפי הנחיית אילן, בכל {nfm+nfx} הכניסה = פתיחת יום 1: סטופ/יעדים באחוזים חושבו מהפתיחה, ורמות מוחלטות שנעשו לא תקפות הותאמו יחסית. הם נכללים עכשיו בסטטיסטיקה, אבל זו כניסה 'מתוקנת' ולא המחיר ש-Grok פרסם. צריך לחייב את Grok לשלוף מחיר סגירה אמיתי ולהחזיר מספרים.",
 "6. סטופים ויעדים ב-Grok: חציון R:R ל-TP1 הוא כ-1.1 (לפני התיקון: 59 מתוך 133 סטאפים עם TP1 קרוב יותר מהסטופ). ב-ALL (25.9) הסטופ המוחלט 228 נשאר כמעט צמוד לפתיחה 228.09 ונפגע ביום 1. במומנטום החציון הוא TP1 +6.2% מול סטופ 6.9%. ב-12 סטאפים (בעיקר מומנטום 14.9: HPE, NTAP, ON, FLEX, HPQ, IESC) יום 1 נפתח בפער מתחת לסטופ, כי המחיר בטבלה היה הסגירה של יום המומנטום. מומלץ להגדיר R:R≥1.5, ולכניסה במומנטום להשתמש בטריגר פריצה ביום המסחר עצמו ולא במחיר הסגירה הקודם.",
 "7. הציון והדירוג לא מנבאים את התוצאה: ב-Grok, ציון 76+ הגיע ל-TP1 ב-26 מתוך 51 מוכרעים (51%) וציון 70–75 ב-10 מתוך 19 (53%). מקומות 1–3: 10 מתוך 23 (43%), מקומות 4–10: 26 מתוך 49 (53%). גם בבוט הציון לא ניבא (JPM ציון 64 הייתה הגרועה). צריך לכייל מחדש את המשקלות.",
 f"8. בוט v2.8, סריקת 7.9: 6 מתוך 10 הגיעו ל-TP1, אבל לפי כללי TP1/סטופ התשואה רק {sb['בוט — סריקה 07.09']['avg_rule']:+.1%} מול {sb['בוט — סריקה 07.09']['avg_ret']:+.1%} בהחזקה. TP1 קרוב מדי, ומומלץ לצאת בחלקים עם טריילינג. בנוסף, סריקת 24.9 רצה על סגירות ישנות (21–22.9), והטיקר GOLD הוא Gold.com (הוחרג, MCAP 1.28B).",
 "9. סתירות בתוך Grok: IREN (7.9) הופיע כמומנטום שורט וגם כשפל-שנתי לונג, ו-TEM (18.9) כמומנטום שורט וגם כשפל-שנתי לונג. SDGR (18.9) הופיע כלונג וגם כשורט 'גידור'. מומלץ לאחד את הקטגוריות לפני הפרסום ולבטל סתירות.",
]
title(nx,'לקחים ומסקנות'); 
for k,t in enumerate(LESSONS,nx+1): para(k,t,48)
nx=nx+len(LESSONS)+2; title(nx,'מתודולוגיה ופערי נתונים')
METH=[
 "מחירים: Yahoo Finance (yfinance), OHLC יומי, עד סגירת 29.09.2026. יום 1 = יום המסחר הראשון בתאריך ההתראה או אחריו (ריצות Grok הן לפני הפתיחה, לפי מחירי 'פרה', ולכן יום 1 = תאריך הריצה; 7.9 היה Labor Day ולכן יום 1 = 08.09). ימים 1–20 = תשואה מצטברת של הסגירה מול מחיר ההתראה, מותאמת לכיוון. פגיעת סטופ/TP לפי High/Low יומי.",
 "GROK automation: 21 קבצים (7, 11, 14, 18, 21, 25 ו-28.09, בכל תאריך 3 קטגוריות), 210 סטאפים. מחיר, סטופ, TP1–3 וכיוון נלקחו מהטבלה; סטופ/יעדים באחוזים הומרו למחיר ביחס למחיר ההתראה. תיקון לפי הנחיית אילן: כשמחיר Grok לא תאם לשוק (מחוץ לטווח יום 1 ±3% וגם רחוק ביותר מ-3% מהסגירה הקודמת) או היה חסר/טווח, מחיר הכניסה = פתיחת יום 1. אחוזים חושבו מחדש מהפתיחה. רמות מוחלטות נשארו אם הן עדיין בצד הנכון של הכניסה, ואחרת כל הרמות המוחלטות הותאמו יחסית לפי המרחק באחוזים ממחיר Grok (או מאמצע הטווח). מסומן בהערות: 'מחיר כניסה = פתיחה, מחיר גרוק: X'.",
 "החרגת MCAP<1.5B: לפי שווי השוק ביום ההתראה. גרפי אילן: הערך בגרף. גיליון מקורי: עמודת MCAP בגיליון. בוט/Grok: שווי נוכחי ב-Yahoo × סגירה ביום שלפני ההתראה / מחיר נוכחי. השורות שהוחרגו נמצאות בלשונית 'הוחרגו - מתחת 1.5B' ולא נכללות בלשונית הראשית או בסטטיסטיקה.",
 "כפילויות: לא נמצאה אף שורה עם אותו טיקר, תאריך ומקור בגיליון המקורי וב-Grok automation (הגיליון: 17.07–06.08, Grok: 07–28.09), ולכן לא נמחקה אף שורה. טיקר שהופיע באותו יום בשתי קטגוריות של Grok נשמר בשתיהן, עם הערה. 'הופעות בהמלצות נוספות' מחושב על פני כל המקורות (בוט, גיליון, Grok לפי קטגוריה).",
 "הכרעה תוך-יומית (כלל 'כניסה קודם'): נגיעת סטופ/יעד נספרת רק אחרי שמחיר ההתראה נסחר. אם מחיר ההתראה לא נסחר כלל ביום 1, הסטופ נספר כרגיל (כמו SNEX/CAT). נבדקו בנרות 1h (5m בתוך 60 הימים האחרונים). HURN: סטופ → פתוח. MNOV (18.9): נגיעת הסטופ ב-09:30 הייתה לפני הכניסה → לא נספרה. TNON (11.9): היעדים נגעו לפני הכניסה, ואחריה סטופ → סטופ. PCLA (11.9): TP1 ב-10:00 לפני הסטופ ב-11:20 → TP1. FEIM ו-GLND: הסטופ היה אחרי הכניסה → סטופ. פירוט ב-overrides.json ובהערות.",
 "גרפי אילן: תאריך הסריקה נלקח רק ממקור תואם שקדם לצילום (06.09 / 23.08). ATKR ו-BTDR לא מופיעים באף ריצת Grok, ולכן נשארים 'חסר תאריך'. BBAI, RXRX ו-SMCI מופיעים ב-Grok רק אחרי הצילום (BBAI/RXRX כשפל שנתי, SMCI כמומנטום שורט), וזה מצוין בהערות. גרפי אימות מ-30.09 (PANW, XOM, WMT, WGS, VLO) נרשמו רק בהערות השורות הקיימות.",
]
for k,t in enumerate(METH,nx+1): para(k,t,44,9)
for j in range(1,18): sm.column_dimensions[L(j)].width=13
sm.column_dimensions['A'].width=34
# ---- raw daily
rd=wb.create_sheet('שינוי יומי (פורמט מקורי)'); rd.sheet_view.rightToLeft=True
H2=['מודל AI','תאריך התראה','טיקר','כיוון','מחיר קפיצת התראה']+[f'יום {k}' for k in range(1,21)]+['סה"כ תשואה','סה"כ (ערך מחושב)']
for j,h in enumerate(H2,1):
    c=rd.cell(1,j,h); c.fill=HF; c.font=HFont; c.alignment=C; c.border=B
for i,r in enumerate(rows,2):
    v=[r['model'],pd.Timestamp(r['alert_date']).to_pydatetime() if r['alert_date'] else 'חסר תאריך',r['ticker'],r['dir'],r['entry']]+[round(float(x),4) for x in r['daily']]+[None]*(20-len(r['daily']))
    for j,x in enumerate(v,1):
        c=rd.cell(i,j,x); c.font=F; c.border=B; c.alignment=C
        if r['source'] in SRCFILL: c.fill=SRCFILL[r['source']]
        c.number_format = DATE if j==2 else USD if j==5 else PCT if j>5 else 'General'
    rg=f"F{i}:Y{i}"
    rd.cell(i,26).value=ArrayFormula(f"Z{i}",f'=IF(COUNT({rg})=0,"",PRODUCT(1+IF(ISNUMBER({rg}),IF(D{i}="SHORT",-{rg},{rg}),0))-1)'); rd.cell(i,26).number_format='0.000%'
    sg=-1 if r['dir']=='SHORT' else 1
    rd.cell(i,27,float(np.prod([1+sg*x for x in r['daily']])-1) if r['daily'] else None).number_format='0.000%'
rd.cell(len(rows)+3,1,'שינוי יומי גולמי של המניה (יום 1 מול מחיר ההתראה, ואחר כך סגירה מול סגירה), לא מותאם לכיוון, כמו בגיליון "מניות שפל שנתי". סה"כ = מכפלה עם היפוך סימן בשורט, כמו בנוסחה המקורית. כשהימים נמדדים מצילום הגרף, זה מצוין בהערות.').font=Font(name='Arial',italic=True,size=9)
for j in range(1,28): rd.column_dimensions[L(j)].width=10
rd.column_dimensions['A'].width=22; rd.freeze_panes='F2'
ex=wb.create_sheet('הוחרגו - מתחת 1.5B'); ex.sheet_view.rightToLeft=True
EH=['טיקר','מקור','תאריך התראה','סוג / קטגוריה','כיוון','MCAP ביום ההתראה','מקור ה-MCAP']
for j,h in enumerate(EH,1):
    c=ex.cell(1,j,h); c.fill=HF; c.font=HFont; c.alignment=C; c.border=B
SRCN={'bot':'בוט v2.8','orig':'גיליון מקורי','ilan':'גרף אילן','grok':'GROK automation'}
for i,r in enumerate(sorted(excl,key=lambda r:(order[r['source']],r['alert_date'] or '',r['ticker'])),2):
    v=[r['ticker'],SRCN[r['source']],pd.Timestamp(r['alert_date']).to_pydatetime() if r['alert_date'] else 'חסר תאריך',(r.get('ttype') or '')+(f" ({r['cat']})" if r.get('cat') else ''),r['dir'],mc(r['mcap_used']),r['mcap_src']]
    for j,x in enumerate(v,1):
        c=ex.cell(i,j,x); c.font=F; c.border=B; c.alignment=C
        if j==3: c.number_format=DATE
for j,wd in enumerate([9,16,13,24,8,14,60],1): ex.column_dimensions[L(j)].width=wd
ex.cell(len(excl)+3,1,f"סה\"כ {len(excl)} שורות הוחרגו לפי כלל אילן: MCAP מתחת ל-1.5B ביום ההתראה. הן לא מופיעות בלשונית הראשית ולא בסטטיסטיקה.").font=Font(name='Arial',italic=True,size=9)
gp=wb.create_sheet('פערי Grok'); gp.sheet_view.rightToLeft=True
GH=['תאריך','קטגוריה','מקום','טיקר','כיוון','בעיה','סטטוס','פירוט']
for j,h in enumerate(GH,1):
    c=gp.cell(1,j,h); c.fill=HF; c.font=HFont; c.alignment=C; c.border=B
k=2
OKF=PatternFill('solid',fgColor='E6F4EA')
for r in sorted(gk,key=lambda r:(r['alert_date'],CATO[r['cat']],r['rank'])):
    iss=[]
    fxn=[n_ for n_ in r['notes'] if n_.startswith('מחיר כניסה = פתיחה')]
    if r.get('fixed'):
        iss.append(('מחיר לא תואם שוק' if r['fixed']=='mismatch' else 'אין מחיר / טווח','טופל — כניסה = פתיחת יום 1, נכלל בסטטיסטיקה',fxn[0] if fxn else ''))
    rest=[g_ for g_ in (r.get('parse_gaps') or []) if not (r.get('fixed') and (g_.startswith('מחיר כטווח') or g_.startswith('אין מחיר')))]
    if r.get('fixed'):
        rest=[g_ for g_ in rest if not ((g_.startswith('סטופ') and r['sl'] is not None) or (g_.startswith('רק') and all(v is not None for v in r['tps'])))]
    if rest: iss.append(('פער פענוח','פתוח — לא הוזן ערך שלא הופיע במקור','; '.join(rest)))
    for a_,st_,b__ in iss:
        for j,x in enumerate([pd.Timestamp(r['alert_date']).to_pydatetime(),r['cat'],r['rank'],r['ticker'],r['dir'],a_,st_,b__],1):
            c=gp.cell(k,j,x); c.font=F; c.border=B; c.alignment=R if j==8 else C
            if st_.startswith('טופל'): c.fill=OKF
            if j==1: c.number_format=DATE
        k+=1
for j,wd in enumerate([12,12,6,8,8,18,30,90],1): gp.column_dimensions[L(j)].width=wd
wb.save((_SCANNER_ROOT + '/scan-tracker-since-2026-09-07.xlsx')); print('saved',len(rows))
