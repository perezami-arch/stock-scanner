import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import pandas as pd, numpy as np, ast
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation
from stats import rows, S, st
HEAD=ast.literal_eval(open('headers.txt').read())
assert len(HEAD)==45
MODEL='Chief of Staff bot (v2.8)'
HF=PatternFill('solid',fgColor='356854'); HFont=Font(name='Arial',bold=True,color='FFFFFF',size=10)
STR=PatternFill('solid',fgColor='F3F7F5'); F=Font(name='Arial',size=10)
thin=Side(style='thin',color='356854'); B=Border(left=thin,right=thin,top=thin,bottom=thin)
C=Alignment(horizontal='center',vertical='center'); R=Alignment(horizontal='right',vertical='top',wrap_text=True,readingOrder=2)
USD='"$"#,##0.00'; PCT='0.00%'; DATE='dd/mm/yyyy'
def mc(x): return '' if x is None else (f"{x/1e12:.3f}T" if x>=1e12 else f"{x/1e9:.2f}B")
wb=Workbook(); ws=wb.active; ws.title='מעקב סריקות'
ws.sheet_view.rightToLeft=True
for j,h in enumerate(HEAD,1):
    c=ws.cell(1,j,h); c.fill=HF; c.font=HFont; c.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True); c.border=B
ws.row_dimensions[1].height=32
stale={'PANW':'21.09','HD':'21.09','XOM':'21.09','ABBV':'21.09','SBUX':'21.09','KO':'21.09','NOW':'22.09','ADBE':'22.09','AMD':'22.09','BAC':'22.09'}
import pickle
d=pd.read_pickle('prices2.pkl')
for i,r in enumerate(rows,2):
    t=r['ticker']; o=r['opt']
    notes=list(r['notes'])
    if r['scan']=='2026-09-24':
        c23=float(d[t].loc['2026-09-23','Close'])
        notes.append(f"פער נתונים: מחיר ההתראה הוא סגירת {stale[t]} (הסריקה רצה 24.09 03:30 בלי סגירת 23.09 = ${c23:.2f}, {c23/r['entry']-1:+.2%} מול מחיר ההתראה). יום 1 = 24.09.")
    if t=='GOLD':
        notes.append("אזהרה: לפי Yahoo הטיקר GOLD הוא כעת Gold.com, Inc. (לא Barrick, שעבר לטיקר B) — הסריקה תיארה אותו ככורה זהב; המחירים והנתונים כאן הם של GOLD כפי שבסריקה.")
    if r['ndays']>0 and r['ndays']<20: notes.append(f"נמדדו {r['ndays']} ימי מסחר מתוך 20; שאר הימים טרם התקיימו.")
    vals={1:MODEL,2:pd.Timestamp(r['scan']).to_pydatetime(),5:t,6:r['rep'] or None,7:mc(r['mcap']),8:round(r['atr'],4),9:r['dir'],10:r['entry'],13:r['sl'],15:r['tsl'],
          16:r['tps'][0],17:r['tps'][1],18:r['tps'][2],22:r['hold'],45:' '.join(notes)}
    if o:
        vals.update({3:o[0].to_pydatetime(),4:o[1].to_pydatetime(),11:round(float(o[2]),2),12:round(float(o[3]),2),23:int(o[4])})
    for k,cum in enumerate(r['cum']): vals[24+k]=round(float(cum),4)
    if r['cum']: vals[44]=round(float(r['cum'][-1]),5)
    rw=str(i)
    vals[14]=f'=IF(ISBLANK(M{rw}),"",IFERROR(IF(I{rw}="SHORT",(M{rw}/J{rw})-1,1-(M{rw}/J{rw})),""))'
    for col,src in [(19,'P'),(20,'Q'),(21,'R')]:
        vals[col]=f'=IF(ISBLANK({src}{rw}),"",IFERROR(IF(I{rw}="SHORT",1-({src}{rw}/J{rw}),({src}{rw}/J{rw})-1),""))'
    for j in range(1,46):
        c=ws.cell(i,j,vals.get(j)); c.font=F; c.border=B; c.alignment=C
        if i%2==1: c.fill=STR
        if j in (2,3,4): c.number_format=DATE
        elif j in (10,11,12,13,16,17,18): c.number_format=USD
        elif j in (8,15,14,19,20,21) or 24<=j<=44: c.number_format=PCT
        if j==44: c.number_format='0.000%'
        if j in (45,6): c.alignment=R
    ws.row_dimensions[i].height=90
# ---- Ilan TradingView chart rows
IL=pd.read_pickle('ilan_bbai.pkl')
i=len(rows)+2; o=IL['opt']
note=("גרף TradingView ששלח אילן (BBAI, 1D, צולם 06.09.2026 03:52 UTC+3): BigBear.ai Holdings, Technology Services / Packaged Software; מחיר 2.92 (‎−2.01%‎), ATR 0.16 (5.35%), מתחת ל-MA150 יומי, דוחות בעוד 66 יום, ווליום 10.27M מול ממוצע 16.85M; נמוך בטווח הגרף 2.59. "
 "כיוון לא צוין — השורה מחושבת כלונג (הנחה). אין סטופ/יעדים בגרף ולכן SL/TP ריקים. מחיר ההתראה 2.92 = סגירת 04.09 (אומת מול Yahoo, ווליום 10.27M תואם); יום 1 = 08.09 (7.9 Labor Day). "
 f"מבט לונג: {IL['cum'][-1]:+.2%} אחרי {IL['ndays']} ימי מסחר (עד 29.09); שיא {IL['hi'][1]:.2f} ב-{IL['hi'][0].strftime('%d.%m')} (MFE {IL['mfe']:+.2%}), שפל {IL['lo'][1]:.2f} ב-{IL['lo'][0].strftime('%d.%m')} (MAE {IL['mae']:+.2%}) — שבר מתחת לנמוך 2.59 מהגרף. "
 f"מבט שורט: אותה תנועה = {-IL['cum'][-1]:+.2%} (המגמה מתחת ל-MA150 תמכה בשורט). MCAP ו-ATR מהגרף; ATR14 מחושב מ-Yahoo ל-04.09: {IL['atr_calc']:.2%}.")
vals={1:'Ilan charts (TradingView)',2:pd.Timestamp('2026-09-06').to_pydatetime(),5:'BBAI',7:'1.4B',8:0.0535,9:'LONG',10:2.92,45:note,
      3:o[0].to_pydatetime(),4:o[1].to_pydatetime(),11:round(float(o[2]),2),12:round(float(o[3]),2),23:int(o[4])}
for k,cum in enumerate(IL['cum']): vals[24+k]=round(float(cum),4)
vals[44]=round(float(IL['cum'][-1]),5)
rw=str(i)
vals[14]=f'=IF(ISBLANK(M{rw}),"",IFERROR(IF(I{rw}="SHORT",(M{rw}/J{rw})-1,1-(M{rw}/J{rw})),""))'
for col,src in [(19,'P'),(20,'Q'),(21,'R')]:
    vals[col]=f'=IF(ISBLANK({src}{rw}),"",IFERROR(IF(I{rw}="SHORT",1-({src}{rw}/J{rw}),({src}{rw}/J{rw})-1),""))'
ILFILL=PatternFill('solid',fgColor='FFF7E0')
for j in range(1,46):
    c=ws.cell(i,j,vals.get(j)); c.font=F; c.border=B; c.alignment=C; c.fill=ILFILL
    if j in (2,3,4): c.number_format=DATE
    elif j in (10,11,12,13,16,17,18): c.number_format=USD
    elif j in (8,15,14,19,20,21) or 24<=j<=44: c.number_format=PCT
    if j==44: c.number_format='0.000%'
    if j==45: c.alignment=R
ws.row_dimensions[i].height=110
NROWS=len(rows)+1
widths={1:22,2:12,3:13,4:13,5:8,6:26,7:10,8:9,9:8,22:12,23:11,44:11,45:95}
for j in range(1,46): ws.column_dimensions[L(j)].width=widths.get(j,10)
ws.freeze_panes='F2'
dv=DataValidation(type='list',formula1='"LONG,SHORT"',allow_blank=True); ws.add_data_validation(dv); dv.add(f'I2:I{NROWS}')
ws.auto_filter.ref=f"A1:{L(45)}{NROWS}"

# ---- Summary sheet
sm=wb.create_sheet('סיכום'); sm.sheet_view.rightToLeft=True
def hdr(rr,cols):
    for j,h in enumerate(cols,1):
        c=sm.cell(rr,j,h); c.fill=HF; c.font=HFont; c.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True); c.border=B
    sm.row_dimensions[rr].height=45
def title(rr,txt):
    c=sm.cell(rr,1,txt); c.font=Font(name='Arial',bold=True,size=13,color='356854')
title(1,'סיכום ביצועי סריקות — Chief of Staff bot (v2.8) | נתוני מחיר עד סגירת 29.09.2026 (Yahoo Finance)')
cols=['קבוצה','סטאפים','עם נתוני מסחר','ימי מסחר נמדדו (מקס׳)','TP1 לפני סטופ','סטופ לפני TP1','פתוחים','אחוז הצלחה (TP1 מתוך מוכרעים)','TP1 מכלל הסטאפים עם נתונים','TP2 הושג','תשואה ממוצעת (סגירה אחרונה)','% ברווח (סגירה אחרונה)','תשואה ממוצעת לפי כללים (TP1/סטופ/פתוח)','MFE ממוצע','MAE ממוצע','טריגר כניסה הופעל']
hdr(3,cols)
for i,(g,s) in enumerate(S,4):
    v=[g,s['n'],s['n_data'],s['days'],s['tp1'],s['stop'],s['open'],s['hit'],s['tp1_all'],s['tp2'],s['avg_ret'],s['win_mtm'],s['avg_rule'],s['mfe'],s['mae'],s['trig']]
    for j,x in enumerate(v,1):
        c=sm.cell(i,j,x if x is not None else 'אין נתונים'); c.font=Font(name='Arial',size=10,bold=(g=='סה"כ')); c.border=B; c.alignment=C
        if j in (8,9,11,12,13,14,15) and x is not None: c.number_format='0.0%'
        if i%2==1: c.fill=STR
r0=4+len(S)+1
sm.cell(r0,1,'הערה: סריקת 30.09 פורסמה היום לפני פתיחת המסחר — אין לה עדיין נתונים והיא לא נכללת בממוצעים. סריקת 27.09 נמדדה על 2 ימי מסחר בלבד, ו-24.09 על 4 — מוקדם להסיק מהן מסקנות.').font=Font(name='Arial',italic=True,size=9)
w=[r for r in rows if r['ndays']>0]; w.sort(key=lambda r:r['cum'][-1],reverse=True)
def tbl(rr,name,items):
    title(rr,name); hdr(rr+1,['סריקה','טיקר','כיוון','ציון','תשואה (סגירה אחרונה)','ימים','תוצאה','MFE','MAE'])
    for k,r in enumerate(items,rr+2):
        v=[pd.Timestamp(r['scan']).strftime('%d.%m.%Y'),r['ticker'],r['dir'],r['score'],r['cum'][-1],r['ndays'],r['outcome'],r['mfe'],r['mae']]
        for j,x in enumerate(v,1):
            c=sm.cell(k,j,x); c.font=F; c.border=B; c.alignment=C
            if j in (5,8,9): c.number_format='0.00%'
    return rr+2+len(items)+1
nx=tbl(r0+2,'5 הסטאפים הטובים ביותר',w[:5]); nx=tbl(nx,'5 הסטאפים החלשים ביותר',w[::-1][:5])
# stop vs ATR analysis
tight=[r for r in w if abs(1-r['sl']/r['entry'])<r['atr']]; wide=[r for r in w if abs(1-r['sl']/r['entry'])>=r['atr']]
rr1=[abs(r['tps'][0]/r['entry']-1)/abs(1-r['sl']/r['entry']) for r in rows]
LESSONS=[
 f"1. סריקת 7.9 (היחידה עם ~3 שבועות נתונים): 6 מתוך 10 הגיעו ל-TP1 לפני הסטופ, 4 הגיעו גם ל-TP2; תשואה ממוצעת לפי סגירה אחרונה {S[0][1]['avg_ret']:+.1%}. אבל לפי כללי סטופ/TP1 הממוצע רק {S[0][1]['avg_rule']:+.1%} — כי ה-TP1 קרוב מדי ביחס לסטופ ומגביל רווח בזמן שהמגמה ממשיכה (AMD +27%, META +20%, PANW +17% בסגירה האחרונה).",
 f"2. יחס סיכוי/סיכון ל-TP1 חלש: ב-{sum(x<1 for x in rr1)} מתוך {len(rr1)} סטאפים TP1 קרוב יותר מהסטופ (R:R<1; למשל ABBV 24.9 ‏0.13, META 7.9 ‏0.38, HD 24.9 ‏0.46). מומלץ לחייב R:R≥1.5 ל-TP1 או לפצל יציאה (חלק ב-TP1, השאר עם טריילינג).",
 f"3. סטופ צמוד מ-1×ATR: {len(tight)} סטאפים עם סטופ קטן מה-ATR היומי — {sum(r['outcome']=='סטופ' for r in tight)} נסגרו בסטופ ({sum(r['outcome']=='סטופ' for r in tight)/len(tight):.0%}); מול {len(wide)} עם סטופ ≥ATR — {sum(r['outcome']=='סטופ' for r in wide)} בסטופ ({sum(r['outcome']=='סטופ' for r in wide)/len(wide):.0%}). ההבדל מתון והמדגם קטן, אבל AMD שורט 24.9 (סטופ 0.43 ATR) ו-ADBE (0.32 ATR) נפגעו כבר ביום השני. מומלץ סטופ מינימלי של ~1×ATR14.",
 "4. הציון לא ניבא את התוצאה: בסריקת 7.9 JPM (ציון 64, #2) היה הגרוע ביותר (−6.6%, סטופ ביום השני) בעוד META (57) ו-AMD (60) היו הטובים. כדאי לבדוק כיול של משקלות הציון מול תוצאות בפועל אחרי עוד כמה סריקות.",
 f"5. לונג מול שורט: לונג — {S[5][1]['tp1']} TP1 / {S[5][1]['stop']} סטופ, ממוצע {S[5][1]['avg_ret']:+.1%}; שורט — {S[6][1]['tp1']} TP1 / {S[6][1]['stop']} סטופ, ממוצע {S[6][1]['avg_ret']:+.1%}. המדגם קטן (10 שורטים עם נתונים).",
 "6. איכות נתונים: סריקת 24.9 רצה על סגירות 21–22.9 ולא כללה את סגירת 23.9 (למשל PANW עלתה 5.8% ל-393.30 לפני ההתראה). יש לוודא שהסורק מושך את הסגירה האחרונה לפני הפרסום.",
 "7. זיהוי טיקר: GOLD ב-Yahoo הוא כיום Gold.com, Inc. ולא Barrick (שעבר ל-B). הסורק תיאר אותו ככורה זהב — יש להוסיף בדיקת שם חברה/סקטור לכל טיקר.",
 "8. טיקרים חוזרים (AMD ×3, PANW/ABBV/KO/XOM/PLTR ×2, CRM ו-DE עם היפוך כיוון): AMD עבר מלונג (7.9, +27%) לשורט (24.9) שנסגר בסטופ למחרת — שורט נגד מומנטום חזק ללא טריגר מאושר מסוכן.",
]
title(nx,'גרפים של אילן (TradingView) — לא נכללים בסטטיסטיקת הבוט')
c=sm.cell(nx+1,1,f"BBAI (06.09.2026, 2.92, כיוון לא צוין): מבט לונג {IL['cum'][-1]:+.2%} אחרי {IL['ndays']} ימי מסחר (MFE {IL['mfe']:+.2%}, MAE {IL['mae']:+.2%}); מבט שורט {-IL['cum'][-1]:+.2%}. המניה מתחת ל-MA150 וירדה אל מתחת לנמוך 2.59 מהגרף (שפל 2.64 ב-29.09 — קרוב, לא מתחת; ראה הערה). ")
c.font=F; c.alignment=R; sm.merge_cells(start_row=nx+1,end_row=nx+1,start_column=1,end_column=12); sm.row_dimensions[nx+1].height=36
nx+=3; title(nx,'לקחים ומסקנות לשיפור הסורק')
for k,t in enumerate(LESSONS,nx+1):
    c=sm.cell(k,1,t); c.font=F; c.alignment=R; sm.merge_cells(start_row=k,end_row=k,start_column=1,end_column=12); sm.row_dimensions[k].height=48
nx=nx+len(LESSONS)+2; title(nx,'מתודולוגיה ופערי נתונים')
METH=[
 "מחירים: Yahoo Finance (yfinance), מחירי OHLC יומיים לא מתואמים, עד סגירת 29.09.2026. כל מחירי ההתראה בסריקות אומתו מול סגירה אמיתית (7.9←4.9; 24.9←21/22.9; 27.9←25.9; 30.9←29.9).",
 "מחיר קפיצת התראה = 'מחיר' מהסריקה; SL%/TP% מחושבים מולו (אותן נוסחאות כמו בגיליון המקורי). יום 1 = יום המסחר הראשון אחרי פרסום הסריקה (7.9←8.9, 24.9←24.9, 27.9←28.9, 30.9←טרם).",
 "ימים 1–20 = תשואה מצטברת של סגירת היום מול מחיר ההתראה, מותאמת כיוון (בשורט ירידה = רווח). סה\"כ תשואה = הערך ביום האחרון שנמדד. בלשונית 'שינוי יומי' מופיע גם הפורמט של הגיליון המקורי (שינוי יומי גולמי + נוסחת מכפלה).",
 "פגיעת סטופ/TP לפי High/Low תוך-יומי מיום 1. 'TP1 לפני סטופ' = הצלחה. אם שניהם באותו יום — מסומן עמום (לא קרה). תשואה לפי כללים = TP1% אם TP1 ראשון, −SL% אם סטופ ראשון, אחרת תשואה בסגירה אחרונה.",
 "כניסה/יציאה אופטימלית = הזוג הטוב ביותר בדיעבד: לונג — Low של יום i ו-High של יום j>i; שורט — High של יום i ו-Low של יום j>i; בתוך חלון המדידה. טווח אחזקה אופטימלי = j−i ימי מסחר.",
 "ATR (daily) = ממוצע 14 ימים של True Range כאחוז ממחיר הסגירה ביום המסחר האחרון לפני ההתראה. MCAP = שווי שוק נוכחי מ-Yahoo מנורמל למחיר הסגירה באותו יום (הנחה: מספר מניות קבוע).",
 "טריגר: נבדק רק רף הפריצה/שבירה הראשי מכל סריקה (נגיעה תוך-יומית); תנאי נפח/נר/ריטסט לא נבדקו. התוצאות מחושבות ממחיר ההתראה ולא ממחיר הטריגר.",
 "פערים: סריקת 30.9 ללא נתונים (תאי ימים/אופטימלי/תשואה ריקים). 27.9 — 2 ימים, 24.9 — 4 ימים, 7.9 — 16 ימים (ימים 17–20 טרם התקיימו). טווח אחזקה בסריקות הוא בימים קלנדריים/מסחר כפי שנכתב. סריקת בדיקת MU של 7.9 לא נכללה.",
]
for k,t in enumerate(METH,nx+1):
    c=sm.cell(k,1,t); c.font=Font(name='Arial',size=9); c.alignment=R; sm.merge_cells(start_row=k,end_row=k,start_column=1,end_column=12); sm.row_dimensions[k].height=36
for j in range(1,17): sm.column_dimensions[L(j)].width=14
sm.column_dimensions['A'].width=20

# ---- raw daily changes (original convention)
rd=wb.create_sheet('שינוי יומי (פורמט מקורי)'); rd.sheet_view.rightToLeft=True
H2=['תאריך התראה','טיקר','כיוון','מחיר קפיצת התראה']+[f'יום {k}' for k in range(1,21)]+['סה"כ תשואה']
for j,h in enumerate(H2,1):
    c=rd.cell(1,j,h); c.fill=HF; c.font=HFont; c.alignment=C; c.border=B
for i,r in enumerate(rows,2):
    v=[pd.Timestamp(r['scan']).to_pydatetime(),r['ticker'],r['dir'],r['entry']]+[round(float(x),4) for x in r['daily']]+[None]*(20-len(r['daily']))
    for j,x in enumerate(v,1):
        c=rd.cell(i,j,x); c.font=F; c.border=B; c.alignment=C
        c.number_format = DATE if j==1 else USD if j==4 else PCT if j>4 else 'General'
    rg=f"E{i}:X{i}"
    from openpyxl.worksheet.formula import ArrayFormula
    rd.cell(i,25).value=ArrayFormula(f"Y{i}",f'=IF(COUNT({rg})=0,"",PRODUCT(1+IF(ISNUMBER({rg}),IF(C{i}="SHORT",-{rg},{rg}),0))-1)')
    c=rd.cell(i,25)
    c.number_format='0.000%'; c.font=F; c.border=B
    # static value alternative
    import math
    sg=-1 if r['dir']=='SHORT' else 1
    rd.cell(i,26, float(np.prod([1+sg*x for x in r['daily']])-1) if r['daily'] else None).number_format='0.000%'
i=len(rows)+2
v=[pd.Timestamp('2026-09-06').to_pydatetime(),'BBAI (Ilan)','LONG',2.92]+[round(float(x),4) for x in IL['daily']]+[None]*(20-len(IL['daily']))
for j,x in enumerate(v,1):
    c=rd.cell(i,j,x); c.font=F; c.border=B; c.alignment=C; c.fill=ILFILL
    c.number_format = DATE if j==1 else USD if j==4 else PCT if j>4 else 'General'
rg=f"E{i}:X{i}"
rd.cell(i,25).value=ArrayFormula(f"Y{i}",f'=IF(COUNT({rg})=0,"",PRODUCT(1+IF(ISNUMBER({rg}),IF(C{i}="SHORT",-{rg},{rg}),0))-1)'); rd.cell(i,25).number_format='0.000%'
rd.cell(i,26,float(np.prod([1+x for x in IL['daily']])-1)).number_format='0.000%'
rd.cell(1,26,'סה"כ (ערך מחושב)').fill=HF; rd.cell(1,26).font=HFont
rd.cell(len(rows)+4,1,'שינוי יומי גולמי של המניה (יום 1 מול מחיר ההתראה, אחר כך סגירה מול סגירה), לא מותאם כיוון — כמו בגיליון "מניות שפל שנתי". סה"כ = מכפלה עם היפוך סימן לשורט, כמו הנוסחה המקורית.').font=Font(name='Arial',italic=True,size=9)
for j in range(1,27): rd.column_dimensions[L(j)].width=10
rd.freeze_panes='E2'
wb.save((_SCANNER_ROOT + '/scan-tracker-since-2026-09-07.xlsx')); print('saved')
