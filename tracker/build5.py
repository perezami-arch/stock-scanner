import pandas as pd, numpy as np, ast
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.formula import ArrayFormula
from stats3 import rows, S, st, SS, TS, H2H, OVL, excl, gk, rows_full, rows_counted, GROUPS, DUPS, PAIRS, CONFS, BA, REP_T, NPAIRS, AFTER, AU
from dups import fd, srcl, SRCN as SRCD, HEB
import json, re
OUTX='/workspace/scan-tracker-2026-10-07.xlsx'
_P='/home/box/agent-data/agents/392ab573-33c2-4c0d-8dc3-6b3991775b0d/attachments/'
CH30b={}
for _l in open('pending_chart_notes.txt').read().splitlines()[1:]:
    _p=_l.split()
    if len(_p)==2: CH30b[_p[0]]=_P+_p[1]

HEAD=ast.literal_eval(open('headers.txt').read())+['סוג טרייד / סורק','חזרות / סתירות']
HF=PatternFill('solid',fgColor='356854'); HFont=Font(name='Arial',bold=True,color='FFFFFF',size=10)
STR=PatternFill('solid',fgColor='F3F7F5'); F=Font(name='Arial',size=10)
SRCFILL={'orig':PatternFill('solid',fgColor='EAF1FB'),'ilan':PatternFill('solid',fgColor='FFF7E0'),'grok':PatternFill('solid',fgColor='F1ECF8'),'gcrypto':PatternFill('solid',fgColor='FDF0E4'),'gpns':PatternFill('solid',fgColor='E6F5F2'),'gxtd':PatternFill('solid',fgColor='FBEAF0'),'p27':PatternFill('solid',fgColor='E8F4FD'),'p25':PatternFill('solid',fgColor='EDF7FB'),'pval':PatternFill('solid',fgColor='F6F2E6'),'pmom':PatternFill('solid',fgColor='EEF0FA'),'pcry':PatternFill('solid',fgColor='FDEDEC')}
thin=Side(style='thin',color='356854'); B=Border(left=thin,right=thin,top=thin,bottom=thin)
C=Alignment(horizontal='center',vertical='center',wrap_text=True); R=Alignment(horizontal='right',vertical='top',wrap_text=True,readingOrder=2)
USD='"$"#,##0.00'; PCT='0.00%'; DATE='dd/mm/yyyy'
def mc(x): return '' if x is None else (f"{x/1e12:.3f}T" if x>=1e12 else f"{x/1e9:.2f}B")
order={'orig':0,'ilan':1,'bot':2,'grok':3,'gcrypto':4,'gpns':5,'gxtd':6,'p27':7,'p25':8,'pval':9,'pmom':10,'pcry':11}
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
        for x in same: notes.append(f"{t} מופיע גם בקטגוריה {x['cat']} ({x['dir']}) באותה ריצת Grok"+(" — סתירת כיוון." if x['dir']!=r['dir'] else " — כפילות מדויקת (אותו מקור, תאריך וכיוון); נספרת פעם אחת בסטטיסטיקה, ראו עמודת 'חזרות / סתירות'."))
        bo=[x for x in rows_full if x['source']=='bot' and x['ticker']==t]
        for x in bo: notes.append(f"מופיע גם בבוט v2.8 ב-{pd.Timestamp(x['alert_date']).strftime('%d.%m')} ({x['dir']})"+(" — כיוון הפוך." if x['dir']!=r['dir'] else "."))
    if t in CH30b: notes.append(f"גרף אימות מאילן (צילום 30.09.2026, לא התראה חדשה). קובץ: {CH30b[t]}")
    vals={1:r['model'],2:(pd.Timestamp(r['alert_date']).to_pydatetime() if r['alert_date'] else 'חסר תאריך'),5:t,6:r['rep'] or None,7:mcap,
          8:(round(r['atr'],4) if r['atr'] is not None else None),9:r['dir'],10:r['entry'],13:r['sl'],15:r['tsl'],16:r['tps'][0],17:r['tps'][1],18:r['tps'][2],
          22:r['hold'],45:' '.join(notes),46:r.get('ttype') or None,47:(('לא נספר — ' if r.get('dup_skip') else '')+r.get('dupnote','')) or None}
    if o: vals.update({3:o[0].to_pydatetime(),4:o[1].to_pydatetime(),11:round(o[2],2),12:round(o[3],2),23:int(o[4])})
    for k,cum in enumerate(r['cum']): vals[24+k]=round(float(cum),4)
    if r['cum']: vals[44]=round(float(r['cum'][-1]),5)
    rw=str(i)
    vals[14]=f'=IF(ISBLANK(M{rw}),"",IFERROR(IF(I{rw}="SHORT",(M{rw}/J{rw})-1,1-(M{rw}/J{rw})),""))'
    for col,src in [(19,'P'),(20,'Q'),(21,'R')]:
        vals[col]=f'=IF(ISBLANK({src}{rw}),"",IFERROR(IF(I{rw}="SHORT",1-({src}{rw}/J{rw}),({src}{rw}/J{rw})-1),""))'
    fill=SRCFILL.get(r['source'], STR if i%2 else None)
    for j in range(1,48):
        c=ws.cell(i,j,vals.get(j)); c.font=F; c.border=B; c.alignment=C
        if fill: c.fill=fill
        if j==47 and r.get('dup_skip'): c.fill=PatternFill('solid',fgColor='F8D7DA')
        elif j==47 and 'סתירה' in (r.get('dupnote') or ''): c.fill=PatternFill('solid',fgColor='FFE8CC')
        if j in (2,3,4): c.number_format=DATE
        elif j in (10,11,12,13,16,17,18): c.number_format=USD
        elif j in (8,15,14,19,20,21) or 24<=j<=44: c.number_format=PCT
        if j==44: c.number_format='0.000%'
        if j in (45,6,47): c.alignment=R
    ws.row_dimensions[i].height=100
NROWS=len(rows)+1
widths={1:22,2:12,3:13,4:13,5:8,6:30,7:10,8:9,9:8,22:12,23:11,44:11,45:100,46:22,47:45}
for j in range(1,48): ws.column_dimensions[L(j)].width=widths.get(j,10)
ws.freeze_panes='F2'
dv=DataValidation(type='list',formula1='"LONG,SHORT"',allow_blank=True); ws.add_data_validation(dv); dv.add(f'I2:I{NROWS}')
ws.auto_filter.ref=f"A1:{L(47)}{NROWS}"

# ---- Summary
sm=wb.create_sheet('סיכום'); sm.sheet_view.rightToLeft=True
def hdr(rr,cols):
    for j,h in enumerate(cols,1):
        c=sm.cell(rr,j,h); c.fill=HF; c.font=HFont; c.alignment=C; c.border=B
    sm.row_dimensions[rr].height=48
def title(rr,txt): sm.cell(rr,1,txt).font=Font(name='Arial',bold=True,size=13,color='356854')
def para(rr,txt,h=40,size=10):
    c=sm.cell(rr,1,txt); c.font=Font(name='Arial',size=size); c.alignment=R; sm.merge_cells(start_row=rr,end_row=rr,start_column=1,end_column=14); sm.row_dimensions[rr].height=h
title(1,'סיכום בקטסט סריקות — נתוני מחיר אמיתיים (Yahoo Finance): מניות עד סגירת 06.10.2026, קריפטו עד 07.10.2026 03:00 (ימים קלנדריים) · כולל Perplexity')
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
NDG=sum(1 for x in DUPS if x['source']=='GROK'); NDC=sum(1 for x in DUPS if x['source']!='GROK')
para(nx-1,f"הערות: עודכן 07.10 — כל השורות חושבו מחדש עם מחירים עד סגירת 06.10 (קריפטו עד 07.10 03:00). סריקת הבוט מ-04.10 נמדדה על 2 ימי מסחר (05–06.10). סריקת הבוט מ-07.10 (נתונים מסגירת 06.10, 10 סטאפים מבוססי טריגר) נוספה כ'טרם התחיל' — יום 1 = 07.10. Perplexity נוסף כמקור נפרד (5 תת-מקורות, פירוט בלשונית 'Perplexity'); 'לא הופעל' = מחיר הכניסה מהטבלה לא נסחר בחלון, ולא נספר. קריפטו נמדד בימים קלנדריים, עד 20 חלונות של 24 שעות. גרפים של אילן: בלי סטופ ויעדים, התשואה ממועד הצילום בכיוון לונג. כל הקבוצות אחרי החרגת MCAP<1.5B. כפילויות מדויקות (אותו מקור, תאריך וכיוון) נספרות פעם אחת: {NDG} ב-Grok automation ו-{NDC} ב-GROK crypto; השורה הכפולה מסומנת 'לא נספר'.",40,9)
title(nx+1,'פילוח לפי מקור (אחרי החרגת MCAP<1.5B)'); nx=stable(nx+2,SS)
title(nx+1,'פילוח לפי סוג טרייד (שפל שנתי / לפני פריצה / מומנטום / Elliott v2.8 / קריפטו / מניות ומדדים)'); nx=stable(nx+2,TS)
TT=TS
_fx=[r for r in rows if r['source'] in ('grok','gcrypto','gpns','gxtd') and r.get('fixed')]
para(nx-1,f"כל השורות של Grok נכללות (חוץ מכפילויות מדויקות שסומנו 'לא נספר'), כולל {len(_fx)} שבהן מחיר הכניסה = פתיחה (מחיר Grok לא תאם לשוק או חסר): {sum(r['source']=='grok' for r in _fx)} ב-Grok automation, {sum(r['source']=='gcrypto' for r in _fx)} ב-crypto, {sum(r['source']=='gpns' for r in _fx)} ב-portfolio-news-scan ו-{sum(r['source']=='gxtd' for r in _fx)} ב-x-trends-digest. שורות בלי סטופ ויעדים נכללות רק בממוצעי התשואה. 'שורות' = כל השורות בקבוצה.",30,9)
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
exec(open('sec_dups5.py').read())
w=[r for r in rows_counted if r['cum'] and r['source']!='ilan' and r['outcome'] not in ('מחיר לא תואם','לא הופעל')]; w.sort(key=lambda r:r['cum'][-1],reverse=True)
def tbl(rr,name,items):
    title(rr,name); hdr(rr+1,['מקור','תאריך','טיקר','כיוון','סוג','תשואה (יום אחרון)','ימים','תוצאה','MFE','MAE'])
    for k,r in enumerate(items,rr+2):
        v=[r['group'],pd.Timestamp(r['alert_date']).strftime('%d.%m.%Y'),r['ticker'],r['dir'],r.get('ttype'),r['cum'][-1],r['ndays'],r['outcome'],r['mfe'],r['mae']]
        for j,x in enumerate(v,1):
            c=sm.cell(k,j,x); c.font=F; c.border=B; c.alignment=C
            if j in (6,9,10): c.number_format='0.00%'
    return rr+2+len(items)+1
nx=tbl(nx,'8 הטובים ביותר (בוט + גיליון + Grok + Perplexity)',w[:8]); nx=tbl(nx,'8 החלשים ביותר (בוט + גיליון + Grok + Perplexity)',w[::-1][:8])
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
c_=SD['GROK crypto — סה"כ']; p_=SD['GROK portfolio-news-scan — סה"כ']; x_=SD['GROK x-trends-digest — סה"כ']; SD_C=dict(S)
NPC=sum(p['a'].get('ttype')=='קריפטו' for p in PAIRS); CRY_EX=sum(r.get('ttype')=='קריפטו' for r in excl)
_A=[r for r in rows if r['source'] in ('gpns','gxtd')]; NA_=len(_A); FXA=sum(bool(r.get('fixed')) for r in _A)
hr=lambda x: '—' if x is None else f"{x*100:.0f}%"
LESSONS=[
 f"1. מקורות (אחרי החרגת MCAP<1.5B וניקוי כפילויות). בוט v2.8: {b_['tp1']} TP1 מול {b_['stop']} סטופים ({hr(b_['hit'])} הצלחה), ממוצע {pc(b_['avg_ret'])}, MAE {pc(b_['mae'])} — הכי מעט נזק בדרך, אבל מדגם קטן ({b_['n_data']} עם נתונים). GROK automation: {g_['tp1']}/{g_['stop']} ({hr(g_['hit'])}), ממוצע {pc(g_['avg_ret'])}, MAE {pc(g_['mae'])} על {g_['n_data']}. GROK crypto: {c_['tp1']}/{c_['stop']} ({hr(c_['hit'])}), ממוצע {pc(c_['avg_ret'])}, MAE {pc(c_['mae'])} על {c_['n_data']}. portfolio-news-scan: {p_['tp1']}/{p_['stop']} ({hr(p_['hit'])}), ממוצע {pc(p_['avg_ret'])}. x-trends-digest: {x_['tp1']}/{x_['stop']} ({hr(x_['hit'])}), ממוצע {pc(x_['avg_ret'])}. גיליון מקורי (יולי–אוג׳): {o_['tp1']}/{o_['stop']} ({hr(o_['hit'])}), ממוצע {pc(o_['avg_ret'])}.",
 f"2. ראש בראש 7.9 (אותו יום 1, {H2H[0][1]} ימים): בוט {pc(H2H[0][2]['avg'])} ממוצע ו-{H2H[0][2]['tp1']}/{H2H[0][2]['stop']} TP1/סטופ, מול Grok {pc(H2H[0][3]['avg'])} ו-{H2H[0][3]['tp1']}/{H2H[0][3]['stop']}. ב-24/25.9 ({H2H[1][1]} ימים): בוט {pc(H2H[1][2]['avg'])} ({H2H[1][2]['tp1']}/{H2H[1][2]['stop']}) מול Grok {pc(H2H[1][3]['avg'])} ({H2H[1][3]['tp1']}/{H2H[1][3]['stop']}). ב-27/28.9 ({H2H[2][1]} ימים): בוט {pc(H2H[2][2]['avg'])} ({H2H[2][2]['tp1']}/{H2H[2][2]['stop']}) מול Grok {pc(H2H[2][3]['avg'])} ({H2H[2][3]['tp1']}/{H2H[2][3]['stop']}). החלונות עדיין קצרים. SNDK ב-7.9: הבוט שורט, Grok לונג.",
 f"3. לפי סוג ב-Grok: 'לפני פריצה' שורט הוא הטוב ביותר ({TD['לפני פריצה — GROK SHORT']['tp1']}/{TD['לפני פריצה — GROK SHORT']['stop']}, ממוצע {pc(TD['לפני פריצה — GROK SHORT']['avg_ret'])}), ו'לפני פריצה' לונג הוא החלש ({TD['לפני פריצה — GROK LONG']['tp1']}/{TD['לפני פריצה — GROK LONG']['stop']}, {pc(TD['לפני פריצה — GROK LONG']['avg_ret'])}). 'מומנטום' לונג: ממוצע {pc(TD['מומנטום — GROK LONG']['avg_ret'])}, אבל {TD['מומנטום — GROK LONG']['stop']} סטופים מול {TD['מומנטום — GROK LONG']['tp1']} TP1. 'מומנטום' שורט הוא המסוכן ביותר: MAE {pc(TD['מומנטום — GROK SHORT']['mae'])}, וב-VICR (14.9) הושג TP1 ואחר כך המניה עלתה ב-47%. שורט נגד מומנטום חם דורש סטופ קשיח ויציאה ב-TP1.",
 f"4. 'שפל שנתי': ב-Grok automation נשארו רק {TD['שפל שנתי — GROK automation']['n']} מתוך 70 אחרי החרגת MCAP (44 היו מיקרו-קאפ), עם {TD['שפל שנתי — GROK automation']['tp1']}/{TD['שפל שנתי — GROK automation']['stop']} וממוצע {pc(TD['שפל שנתי — GROK automation']['avg_ret'])}. הגיליון המקורי ({hr(o_['hit'])} הצלחה, {pc(o_['avg_ret'])}) עדיין הכי רווחי, אבל נמדד על חלון ארוך יותר (20 ימים) ובתקופה אחרת. מומלץ שהסורק יסנן MCAP≥1.5B כבר בשלב הסריקה.",
 f"5. איכות נתונים ב-Grok: ב-{nfm} סטאפים המחיר בטבלה היה רחוק ב-8%–42% ממחיר השוק (בעיקר 'לפני פריצה': APA 24.8 מול 42.8, BIIB 132 מול 220.8, HPQ 21.4 מול 35.5), וב-{nfx} לא היה מחיר (טווח, 'ליד שפל' או רק אחוזים). לפי הנחיית אילן, בכל {nfm+nfx} הכניסה = פתיחת יום 1: סטופ/יעדים באחוזים חושבו מהפתיחה, ורמות מוחלטות שנעשו לא תקפות הותאמו יחסית. הם נכללים עכשיו בסטטיסטיקה, אבל זו כניסה 'מתוקנת' ולא המחיר ש-Grok פרסם. צריך לחייב את Grok לשלוף מחיר סגירה אמיתי ולהחזיר מספרים.",
 "6. סטופים ויעדים ב-Grok: חציון R:R ל-TP1 הוא כ-1.1 (לפני התיקון: 59 מתוך 133 סטאפים עם TP1 קרוב יותר מהסטופ). ב-ALL (25.9) הסטופ המוחלט 228 נשאר כמעט צמוד לפתיחה 228.09 ונפגע ביום 1. במומנטום החציון הוא TP1 +6.2% מול סטופ 6.9%. ב-12 סטאפים (בעיקר מומנטום 14.9: HPE, NTAP, ON, FLEX, HPQ, IESC) יום 1 נפתח בפער מתחת לסטופ, כי המחיר בטבלה היה הסגירה של יום המומנטום. מומלץ להגדיר R:R≥1.5, ולכניסה במומנטום להשתמש בטריגר פריצה ביום המסחר עצמו ולא במחיר הסגירה הקודם.",
 (lambda R: (lambda f: f"7. הציון והדירוג לא מנבאים את התוצאה (Grok, אחרי ניקוי כפילויות): ציון 76+ הגיע ל-TP1 ב-{f(lambda r:(r.get('score') or 0)>=76)} מוכרעים, ציון 70–75 ב-{f(lambda r:70<=(r.get('score') or 0)<76)}. מקומות 1–3: {f(lambda r:(r.get('rank') or 99)<=3)}, מקומות 4–10: {f(lambda r:4<=(r.get('rank') or 99)<=10)}. גם בבוט הציון לא ניבא (JPM ציון 64 הייתה הגרועה). צריך לכייל מחדש את המשקלות.")(lambda c: (lambda x: f"{sum(r['outcome']=='TP1' for r in x)} מתוך {len(x)} ({sum(r['outcome']=='TP1' for r in x)/len(x):.0%})")([r for r in R if c(r) and r['outcome'] in ('TP1','סטופ')])))(AFTER['gk']),
 f"8. בוט v2.8 לפי סריקה: 7.9 — {sb['בוט — סריקה 07.09']['tp1']}/{sb['בוט — סריקה 07.09']['stop']} TP1/סטופ, אבל לפי כללי TP1/סטופ התשואה רק {pc(sb['בוט — סריקה 07.09']['avg_rule'])} מול {pc(sb['בוט — סריקה 07.09']['avg_ret'])} בהחזקה (TP1 קרוב מדי; מומלץ לצאת בחלקים עם טריילינג). 24.9 — {sb['בוט — סריקה 24.09']['tp1']}/{sb['בוט — סריקה 24.09']['stop']}, ממוצע {pc(sb['בוט — סריקה 24.09']['avg_ret'])} (רצה על סגירות ישנות 21–22.9). 27.9 — {sb['בוט — סריקה 27.09']['tp1']}/{sb['בוט — סריקה 27.09']['stop']} ו-{sb['בוט — סריקה 27.09']['open']} פתוחים, ממוצע {pc(sb['בוט — סריקה 27.09']['avg_ret'])}. 30.9 — {sb['בוט — סריקה 30.09']['tp1']}/{sb['בוט — סריקה 30.09']['stop']} ו-{sb['בוט — סריקה 30.09']['open']} פתוחים, ממוצע {pc(sb['בוט — סריקה 30.09']['avg_ret'])}. 4.10 (2 ימים) — {sb['בוט — סריקה 04.10']['tp1']}/{sb['בוט — סריקה 04.10']['stop']} ו-{sb['בוט — סריקה 04.10']['open']} פתוחים, ממוצע {pc(sb['בוט — סריקה 04.10']['avg_ret'])}. 7.10 — 10 סטאפים מבוססי טריגר (DIS, LNG, CVX, TGT, CDNS, HUBB, FOXA, KEYS, MPC, P) נוספו כ'טרם התחיל'. הטיקר GOLD (27.9) הוא Gold.com והוחרג (MCAP 1.28B).",
 f"9. חזרות וסתירות: {REP_T} טיקרים הופיעו יותר מפעם אחת, ו-{NPAIRS} זוגות לונג/שורט סותרים ({NPC} מהם בקריפטו — בעיקר BTC, ETH, SOL ו-HYPE, כי crypto ו-x-trends-digest מחליפים כיוון כל כמה ימים). במניות: SNDK 7.9 בוט שורט מול Grok לונג, IREN 7.9, TEM 18.9 ו-SDGR 18.9 בתוך Grok. ב-Grok automation סטאפים בסתירה הצליחו פחות: {hr(dict(CONFS)['GROK — בסתירת כיוון']['hit'])} הצלחה וממוצע {pc(dict(CONFS)['GROK — בסתירת כיוון']['avg_ret'])}, מול {hr(dict(CONFS)['GROK — בלי סתירה']['hit'])} ו-{pc(dict(CONFS)['GROK — בלי סתירה']['avg_ret'])} בלי סתירה. בזוגות שהוכרעו לפי תוצאה ניצח השורט {WS_} פעמים והלונג {WL}. מומלץ שהסורקים יאחדו קטגוריות, יבטלו סטאפ הפוך לסטאפ פעיל על אותו נכס, ויסמנו חזרות.",
 f"10. קריפטו (GROK crypto, 17.07–27.09, ימים קלנדריים): {c_['tp1']} TP1 מול {c_['stop']} סטופים ({hr(c_['hit'])}), ממוצע {pc(c_['avg_ret'])}, MAE {pc(c_['mae'])}. הפער בין הכיוונים גדול: לונג {SD_C['GROK crypto — LONG']['tp1']}/{SD_C['GROK crypto — LONG']['stop']} ({hr(SD_C['GROK crypto — LONG']['hit'])}), ממוצע {pc(SD_C['GROK crypto — LONG']['avg_ret'])}; שורט {SD_C['GROK crypto — SHORT']['tp1']}/{SD_C['GROK crypto — SHORT']['stop']} ({hr(SD_C['GROK crypto — SHORT']['hit'])}), ממוצע {pc(SD_C['GROK crypto — SHORT']['avg_ret'])} ו-MAE {pc(SD_C['GROK crypto — SHORT']['mae'])}. השורטים היו בעיקר נגד מטבעות בפאמפ (ZEC, QNT, UNI, BCH), שהמשיכו לעלות עשרות אחוזים, והלונגים נהנו משוק עולה (BTC מ-~63K ב-17.7 ל-~85K). לפי חודש: יולי {hr(SD_C['GROK crypto — יולי']['hit'])}, אוגוסט {hr(SD_C['GROK crypto — אוגוסט']['hit'])}, ספטמבר {hr(SD_C['GROK crypto — ספטמבר']['hit'])}. {CRY_EX} שורות קריפטו הוחרגו (מטבעות קטנים מתחת 1.5B). מומלץ לא לשרט פאמפ בלי אישור היפוך, ולהגביל את הסטופ ל-ATR.",
 f"11. portfolio-news-scan ו-x-trends-digest: אלה בעיקר דוחות סנטימנט/חדשות עם טבלת 'טריגר + יעד/סטופ', ורוב רמות המחיר שלהם לא תואמות לשוק (למשל SPY 560 / 6600 כשהוא ~770, NVDA 120–140 כשהיא ~230, BTC 95K כשהוא ~85K). לכן {FXA} מתוך {NA_} הסטאפים חושבו מפתיחה עם רמות מותאמות. התוצאה חלשה: portfolio-news-scan {p_['tp1']}/{p_['stop']} ({hr(p_['hit'])}), x-trends-digest {x_['tp1']}/{x_['stop']} ({hr(x_['hit'])}); השורטים ב-x-trends הם החלשים ({SD_C['GROK x-trends-digest — SHORT']['tp1']}/{SD_C['GROK x-trends-digest — SHORT']['stop']}, ממוצע {pc(SD_C['GROK x-trends-digest — SHORT']['avg_ret'])}). daily-stock-tracker לא נותן סטאפים (רק כיוון וציון, ולפעמים לונג ושורט על אותו טיקר), ולכן לא נוסף. מומלץ לחייב את שלוש האוטומציות לשלוף מחיר אמיתי לפני קביעת רמות.",

]
PPS_=('p27','p25','pval','pmom','pcry')
_PP=[r for r in rows_counted if r['source'] in ('p27','p25','pval','pmom','pcry')]
_UT=[r for r in _PP if r['outcome']=='לא הופעל' and r['cum']]
_ut_txt=', '.join(f"{r['ticker'].replace('-USD','').replace('32196','')} {fd(r['alert_date'])} {('לונג' if r['dir']=='LONG' else 'שורט')} {r['cum'][-1]*100:+.0f}%" for r in sorted(_UT,key=lambda r:-r['cum'][-1]))
_PN=[r for r in _PP if r['source'] in ('p27','p25') and r['sl'] is not None]
_g=lambda n: SD_C[n]
_ps=lambda n: f"{_g(n)['tp1']}/{_g(n)['stop']} ({hr(_g(n)['hit'])}), ממוצע {pc(_g(n)['avg_ret'])}, MAE {pc(_g(n)['mae'])}"
_PPAIRS=[p for p in PAIRS if p['a']['source'] in PPS_ or p['b']['source'] in PPS_]
_pin=[p for p in _PPAIRS if p['a']['source'] in PPS_ and p['b']['source'] in PPS_]; _pbot=[p for p in _PPAIRS if 'bot' in (p['a']['source'],p['b']['source'])]
LESSONS+=[
 f"12. Perplexity — מקור חדש (111 סטאפים בלשונית אחרי החרגה). v2.7: {_ps('Perplexity v2.7 — סה\"כ')}; v2.5 (6.9): {_ps('Perplexity v2.5 — סה\"כ')}; value/turnaround: {_ps('Perplexity value/turnaround — סה\"כ')}; momentum (בלי רמות): ממוצע {pc(_g('Perplexity momentum — סה\"כ')['avg_ret'])}, MAE {pc(_g('Perplexity momentum — סה\"כ')['mae'])}; crypto: {_ps('Perplexity crypto — סה\"כ')}. לשם השוואה על אותם נתונים: בוט v2.8 {_ps('בוט — סה\"כ')}, GROK automation {_ps('GROK automation — סה\"כ')}. הסטאפים המספריים של v2.7+v2.5 ({_g('Perplexity v2.7+v2.5 — עם רמות מספריות')['n']}): {_ps('Perplexity v2.7+v2.5 — עם רמות מספריות')} — דומה ל-Grok automation וחלש מהבוט בתשואה וב-MAE.",
 f"13. איכות הפלט של Perplexity יורדת: בריצות השבועיות של 27.9 ו-4.10 אין אף מחיר כניסה, סטופ או יעד ('~' בכל העמודות), וב-13.9/20.9 עמודת הניקוד מכילה טווח אחזקה. גם value/momentum/crypto מתארים רמות במילים ('שיא מקומי', 'מתחת לשפל אחרון'): {SD_C['Perplexity — כל המקורות']['nolev']} מתוך {SD_C['Perplexity — כל המקורות']['n_data']} השורות עם נתונים נספרו בתשואות בלבד. הרצת value מ-13.08 החזירה טיקרים מוסתרים (XXXX). מומלץ לחייב בפרומפט מספרים מפורשים (כניסה, סטופ, TP1) ולבדוק שהעמודות לא ריקות לפני שליחת הסריקה.",
 f"14. כלל 'כניסה קודם' משנה את התמונה ב-Perplexity: {len(_UT)} סטאפים לא הופעלו כי מחיר הכניסה/טריגר לא נסחר בחלון ({_ut_txt}). בלונגים של ריטסט (NVDA ו-MRVL 20.9, ETH 13.8) המחיר כבר היה מעל הכניסה ולא חזר — פספוס של מהלכים גדולים; בלונגים של פריצה (CDE 6.9, JPM ו-AMZN 7.9) ובשורטים של שבירה (META 13.9/20.9, HYPE) הטריגר שלא הופעל חסך הפסד. מומלץ: בלונג 'ריטסט' להגדיר גם כניסה חלופית (למשל פריצה של שיא יום 1), ולהשאיר את תנאי הפריצה/שבירה.",
 f"15. לונג מול שורט ב-Perplexity: לונג {_ps('Perplexity — LONG')}; שורט {_ps('Perplexity — SHORT')}. השורטים נגד מגה-קאפ טכנולוגי בשוק עולה נכשלו (NVDA ו-MSFT 13.9, TSLA 20.9, SPY 13.9 — סטופ; שורט ZEC בקריפטו {pc(next((r['cum'][-1] for r in _PP if r['ticker']=='ZEC-USD'),None))}). אותה תבנית כמו בבוט (שורט {pc(SD_C['בוט — SHORT']['avg_ret'])}) וב-Grok. בנוסף, v2.7 החליף כיוון על אותן מניות משבוע לשבוע (META: לונג 7.9 → שורט 13.9 ו-20.9 → לונג 27.9; NVDA: לונג 7.9 → שורט 13.9 → לונג 20.9 → שורט 27.9), ו-value הפך כיוון ב-PAGS, GOF ו-STNE בתוך 3 ימים.",
 f"16. סתירות עם מקורות אחרים: {len(_PPAIRS)} זוגות לונג/שורט מערבים את Perplexity — {len(_pin)} בתוך Perplexity, {len(_pbot)} מול הבוט (META, NVDA, MSFT, AMD, AVGO — בכולם Perplexity שורט והבוט לונג; MSFT 13.9: Perplexity סטופ מול TP1 בבוט; AVGO 6.9: השורט של Perplexity פתוח מול סטופ בלונג של הבוט), והשאר מול Grok (בעיקר x-trends ו-crypto). ההמלצה: לא להחזיק במקביל כיוונים הפוכים, ולתת עדיפות לסטאפ עם רמות מספריות ו-MAE נמוך (כרגע — הבוט).",
]
title(nx,'לקחים ומסקנות'); 
for k,t in enumerate(LESSONS,nx+1): para(k,t,48)
nx=nx+len(LESSONS)+2; title(nx,'מתודולוגיה ופערי נתונים')
METH=[
 "מחירים: Yahoo Finance (yfinance), OHLC יומי, מניות עד סגירת 06.10.2026 (עודכן 07.10; כל השורות חושבו מחדש). יום 1 = יום המסחר הראשון בתאריך ההתראה או אחריו (ריצות Grok הן לפני הפתיחה, לפי מחירי 'פרה', ולכן יום 1 = תאריך הריצה; 7.9 היה Labor Day ולכן יום 1 = 08.09). ימים 1–20 = תשואה מצטברת של הסגירה מול מחיר ההתראה, מותאמת לכיוון. פגיעת סטופ/TP לפי High/Low יומי.",
 "GROK automation: 21 קבצים (7, 11, 14, 18, 21, 25 ו-28.09, בכל תאריך 3 קטגוריות), 210 סטאפים. מחיר, סטופ, TP1–3 וכיוון נלקחו מהטבלה; סטופ/יעדים באחוזים הומרו למחיר ביחס למחיר ההתראה. תיקון לפי הנחיית אילן: כשמחיר Grok לא תאם לשוק (מחוץ לטווח יום 1 ±3% וגם רחוק ביותר מ-3% מהסגירה הקודמת) או היה חסר/טווח, מחיר הכניסה = פתיחת יום 1. אחוזים חושבו מחדש מהפתיחה. רמות מוחלטות נשארו אם הן עדיין בצד הנכון של הכניסה, ואחרת כל הרמות המוחלטות הותאמו יחסית לפי המרחק באחוזים ממחיר Grok (או מאמצע הטווח). מסומן בהערות: 'מחיר כניסה = פתיחה, מחיר גרוק: X'.",
 "החרגת MCAP<1.5B: לפי שווי השוק ביום ההתראה. גרפי אילן: הערך בגרף. גיליון מקורי: עמודת MCAP בגיליון. בוט/Grok: שווי נוכחי ב-Yahoo × סגירה ביום שלפני ההתראה / מחיר נוכחי. השורות שהוחרגו נמצאות בלשונית 'הוחרגו - מתחת 1.5B' ולא נכללות בלשונית הראשית או בסטטיסטיקה.",
 "חזרות וכפילויות (עודכן 30.09): (א) כפילות מדויקת = אותו מקור, אותו תאריך ואותו כיוון (אותו סטאפ בשתי קטגוריות Grok באותה ריצה; הרמות יכולות להיות קרובות אך לא זהות). השורה נשארת בגיליון, אבל נספרת פעם אחת — נספרת הקטגוריה הראשונה בסדר near-low → prebreakout → momentum, והשנייה מסומנת 'לא נספר'. (ב) חזרה = אותו טיקר ואותו כיוון בתאריך מאוחר יותר (כל חזרה נספרת כסטאפ עצמאי). (ג) סתירה = לונג מול שורט על אותו טיקר באותו יום, או כשההתראה המאוחרת נופלת בתוך חלון 20 ימי המסחר של המוקדמת (גם אם המוקדמת כבר הוכרעה — מצוין בטבלה). מנצח = התוצאה הטובה יותר (TP1 > פתוח > סטופ); בתוצאה זהה — תיקו, עם ציון מי מוביל לפי התשואה. גרפי אילן (מבט לונג משוער, בלי סטופ ויעדים) לא נספרים כחזרה או כסתירה. אין כפילות מדויקת בין הגיליון המקורי ל-Grok automation (תקופות שונות).",
 "הכרעה תוך-יומית (כלל 'כניסה קודם'): נגיעת סטופ/יעד נספרת רק אחרי שמחיר ההתראה נסחר. אם מחיר ההתראה לא נסחר כלל ביום 1, הסטופ נספר כרגיל (כמו SNEX/CAT). נבדקו בנרות 1h (5m בתוך 60 הימים האחרונים). HURN: סטופ → פתוח. MNOV (18.9): נגיעת הסטופ ב-09:30 הייתה לפני הכניסה → לא נספרה. TNON (11.9): היעדים נגעו לפני הכניסה, ואחריה סטופ → סטופ. PCLA (11.9): TP1 ב-10:00 לפני הסטופ ב-11:20 → TP1. FEIM ו-GLND: הסטופ היה אחרי הכניסה → סטופ. פירוט ב-overrides.json ובהערות.",
 "גרפי אילן: תאריך הסריקה נלקח רק ממקור תואם שקדם לצילום (06.09 / 23.08). ATKR ו-BTDR לא מופיעים באף ריצת Grok, ולכן נשארים 'חסר תאריך'. BBAI, RXRX ו-SMCI מופיעים ב-Grok רק אחרי הצילום (BBAI/RXRX כשפל שנתי, SMCI כמומנטום שורט), וזה מצוין בהערות. גרפי אימות מ-30.09 (PANW, XOM, WMT, WGS, VLO, ואחר כך סדרה נוספת של 18 גרפים) נרשמו רק בהערות השורות הקיימות, עם נתיב הקובץ — בלי שורות חדשות.",
 "קריפטו (נוסף 04.10): קריפטו נסחר 7 ימים בשבוע, ולכן הימים נספרים כימים קלנדריים ולא ימי מסחר. יום 1 = 24 השעות שמתחילות בשעה העגולה הראשונה אחרי שעת הריצה של האוטומציה (crypto 08:30 UTC, x-trends-digest 09:00 UTC, portfolio-news-scan 13:30 UTC; ל-17.07 יש שלוש ריצות באותו יום, כולן לפי 08:30). עד 20 חלונות של 24 שעות; רק חלונות שהסתיימו עד 04.10.2026 03:00 שעון ישראל נספרים. פגיעות סטופ/יעד לפי נרות שעתיים של Yahoo (High/Low), סגירת כל יום = סגירת הנר האחרון בחלון. סימולי Yahoo (BTC-USD, ETH-USD, ובמטבעות עם שם כפול סימול עם מזהה, למשל HYPE32196-USD) אומתו לפי שם ויחס מחיר. APR, BOBO, BLORB, BP, CAP, U ו-COW לא נמצאו ב-Yahoo בוודאות, ולכן אין להם חישוב ('אין נתוני מחיר'); כשנמצא שווי ב-CoinGecko מתחת 1.5B, השורה הוחרגה.",
 "כלל כניסה ו-MCAP בקריפטו: כמו במניות — מחיר Grok צריך להיות בטווח יום 1 ±3% או במרחק עד 3% מהמחיר שלפני ההתראה; אחרת (או כשאין מחיר) הכניסה = פתיחת הנר השעתי הראשון ('מחיר כניסה = פתיחה, מחיר גרוק: X'), אחוזים חושבו מהכניסה ורמות מוחלטות שנעשו לא תקפות הותאמו יחסית. כלל 'כניסה קודם': ביום 1, נגיעת סטופ/יעד נספרת רק מהנר השעתי שבו מחיר Grok נסחר; אם המחיר לא נסחר ביום 1 — נספר מתחילת החלון. MCAP = שווי נוכחי ב-Yahoo × מחיר לפני ההתראה / מחיר נוכחי; כלל 1.5B חל על כל המטבעות (המטבעות הגדולים עוברים אותו בכל מקרה), ומטבעות קטנים מתחת 1.5B הוחרגו. ZHIPU-USD ו-SKUU-USD הם חוזי פרפטואל על מניות (Zhipu, ETF ממונף על SK Hynix) בלי MCAP ב-Yahoo — נשארו בלי החרגה, עם הערה.",
 "אוטומציות Grok נוספות (נוסף 04.10): crypto (50 קבצים, 17.07–27.09 — הקובץ הראשון מ-17.7 ולא 20.7), portfolio-news-scan (24, 06–29.09), x-trends-digest (25, 06–30.09), daily-stock-tracker (24, 06–29.09). נוספו רק סטאפים עם נכס, כיוון, מחיר/טריגר, סטופ ויעד. portfolio-news-scan: רק ב-4 קבצים (07, 27, 28, 29.09) יש עמודות טריגר ויעד/סטופ. x-trends-digest: 9 קבצים עם סטאפים; הקובץ של 25.09 זהה ל-20.09. daily-stock-tracker: אין סטאפים (רק כיוון, ציון ומחיר) — לא נוספו שורות. 9 קבצי daily-stock-tracker ו-3 של x-trends-digest הם צילומי ממשק ('Loading conversation') ולא פלט ריצה. בקובץ grok-crypto-2026-07-17-2.md הודבקו בטעות 9 שורות מ-25.09 (BTC 84,100 וכו') — הן לא נוספו. ב-portfolio-news-scan/x-trends-digest יש רק יעד אחד (TP1). פירוט מלא בלשונית 'אוטומציות Grok'.",
 "סריקת בוט v2.8 מ-04.10.2026 (נתונים מסגירת 02.10): 10 סטאפים (SHOP, NFLX, NVDA, PANW, HD, MSFT, BAC, GS, CMCSA, META). מחירי הכניסה תואמים בדיוק ל-scan_deep_2026-10-04.json; סטופ ו-TP1–3 לפי הסריקה. ציון, החזקה וטריגר לא נמסרו — הושארו ריקים. יום 1 = 05.10, ולכן טרם התחיל. סריקת 30.09 כבר הייתה בגיליון ועודכנה עם 3 ימי מסחר. (עדכון 07.10: נמדדה על 2 ימי מסחר, 05–06.10.)",
 "סריקת בוט v2.8 מ-07.10.2026 09:04 IDT (נתונים מסגירת 06.10): 10 סטאפים מבוססי טריגר — DIS, LNG, CVX, TGT, FOXA (לונג), CDNS, HUBB, KEYS, MPC, P (שורט). מחיר = סגירת 06.10, טריגר כניסה, סטופ, טריילינג %, TP1–3, ציון ותקופת החזקה מהסריקה. יום 1 = 07.10 — טרם התחיל. הטריגר נבדק (הופעל/לא הופעל) בהערות, כמו בסריקות קודמות.",
 "Perplexity (נוסף 07.10): 13 הרצות מ-Perplexity Tasks (PDF + CSV לכל הרצה). מקורות: Perplexity v2.7 (שבועי 13.9, 20.9, 27.9, 4.10 + ריצת Computer 7.9), Perplexity v2.5 (6.9), value/turnaround (14–16.8; 13.8 מוסתר), momentum (12.8), crypto (12–13.8). תאריך התראה = תאריך הריצה; יום 1 = יום המסחר הבא אחרי הריצה (ריצות סוף השבוע → שני; 6.9/7.9 → 08.09; 14.8 רצה תוך כדי מסחר → 17.08; 12.8 → 13.08). קריפטו: יום 1 = 24 השעות מהשעה העגולה הראשונה אחרי שעת הריצה (13.8 17:36, 12.8 17:48 שעון ישראל), ימים קלנדריים.",
 "Perplexity — כניסה ורמות: מחיר הכניסה/טריגר מהטבלה נלקח כמו שהוא (ב-v2.7/v2.5 המחיר הנוכחי בטבלה תאם בדיוק לסגירה הקודמת ב-Yahoo). כשאין מחיר ('~', תנאי מילולי או טווח) — כניסה = פתיחת יום 1, מסומן 'מחיר כניסה = פתיחה, מחיר Perplexity: …'. כלל 'כניסה קודם' על כל החלון: סטופ/TP נספרים רק מהיום שבו מחיר הכניסה נסחר (כולל פער פתיחה דרכו); לא נסחר בכלל → 'לא הופעל', לא נספר. רמות: מספרים מפורשים; טווח → הגבול הקרוב לכניסה; אחוזים מהכניסה; שפל 52 שבועות / SMA200 / אמצע טווח 52 שבועות חושבו מ-Yahoo; רמות איכותיות הושארו ריקות. אם חסר סטופ או TP1 — שניהם הוסרו לצורך התוצאה והשורה נספרת בתשואות בלבד. MCAP<1.5B הוחרג (גם במטבעות). פירוט בלשונית 'Perplexity'."
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
SRCN={'bot':'בוט v2.8','orig':'גיליון מקורי','ilan':'גרף אילן','grok':'GROK automation','gcrypto':'GROK crypto','gpns':'GROK portfolio-news-scan','gxtd':'GROK x-trends-digest','p27':'Perplexity v2.7','p25':'Perplexity v2.5','pval':'Perplexity value/turnaround','pmom':'Perplexity momentum','pcry':'Perplexity crypto'}
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
exec(open('sec_auto5.py').read())
exec(open('sec_pplx.py').read())
exec(open('sec_tab5.py').read())
wb.save(OUTX); print('saved',len(rows))
