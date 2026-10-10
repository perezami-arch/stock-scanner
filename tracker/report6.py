import json
from fpdf import FPDF
from bidi.algorithm import get_display
D=json.load(open('report_data.json'))
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; FB='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
G=(53,104,84)
class P(FPDF):
    def footer(self):
        self.set_y(-10); self.set_font('D','',7); self.set_text_color(120)
        self.cell(0,5,get_display(f'מעקב סריקות — דוח ניתוח 08.10.2026 · עמוד {self.page_no()} · לא ייעוץ השקעות'),align='C')
pdf=P(orientation='L',unit='mm',format='A4'); pdf.add_font('D','',FONT); pdf.add_font('D','B',FB)
pdf.set_auto_page_break(True,12); pdf.set_margins(10,10,10)
W=277
def para(t,size=9,bold=False,color=(0,0,0),h=4.6):
    pdf.set_font('D','B' if bold else '',size); pdf.set_text_color(*color)
    words=t.split(' '); line=''; lines=[]
    for w in words:
        test=(line+' '+w).strip()
        if pdf.get_string_width(test)>W-2 and line: lines.append(line); line=w
        else: line=test
    if line: lines.append(line)
    for l in lines: pdf.set_x(10); pdf.cell(W,h,get_display(l),align='R',new_x='LMARGIN',new_y='NEXT')
def h1(t): pdf.ln(1); para(t,13,True,G,7)
def fmt(x,p=True):
    if x is None: return '—'
    if isinstance(x,float): return f"{x*100:+.1f}%" if p else f"{x:.2f}"
    return str(x)
def table(head,rows,widths,size=7.5):
    x0=10+W; pdf.set_font('D','B',size); pdf.set_fill_color(*G); pdf.set_text_color(255)
    x=x0
    for h,w in zip(head,widths):
        x-=w; pdf.set_xy(x,pdf.get_y()); pdf.cell(w,8,get_display(h),border=1,align='C',fill=True)
    pdf.ln(8); pdf.set_font('D','',size); pdf.set_text_color(0)
    for k,r in enumerate(rows):
        if pdf.get_y()>190: pdf.add_page()
        pdf.set_fill_color(243,247,245) if k%2 else pdf.set_fill_color(255,255,255)
        x=x0; y=pdf.get_y()
        for v,w in zip(r,widths):
            x-=w; pdf.set_xy(x,y); pdf.cell(w,5.5,get_display(str(v)),border=1,align='C',fill=True)
        pdf.ln(5.5)
pdf.add_page()
para('דוח ניתוח סריקות מניות — בקטסט מול נתוני מחיר אמיתיים',16,True,G,9)
n=D['nsrc']
para(f"הוכן לאילן · 08.10.2026 11:05 שעון ישראל · {D['nrows']} שורות אחרי החרגת MCAP<1.5B ({D['ncounted']} נספרות בסטטיסטיקה אחרי ניקוי {D['NDUP']} כפילויות מדויקות): {n['grok']} מ-GROK automation, {n['gcrypto']} מ-GROK crypto, {n['gpns']} מ-portfolio-news-scan, {n['gxtd']} מ-x-trends-digest, {n['bot']} מבוט v2.8 (כולל סריקות 04.10 ו-07.10), {n['p27']+n['p25']+n['pval']+n['pmom']+n['pcry']} מ-Perplexity (חדש), {n['orig']} מהגיליון המקורי, {n['ilan']} גרפי TradingView · הוחרגו {len(D['excl'])} שורות · מחירים: Yahoo Finance — מניות עד סגירת 07.10 (23:00 שעון ישראל; השוק בארה״ב סגור בזמן העדכון), קריפטו עד 08.10 11:00 שעון ישראל (ימים קלנדריים)",9,False,(80,80,80))
h1('ממצאים עיקריים')
SS=dict((g,s) for g,s in D['SS']); TS=dict((g,s) for g,s in D['TS'])
bt=SS['בוט v2.8 — סה"כ']; gk=SS['GROK automation — סה"כ']; o=SS['גיליון מקורי (יולי–אוג׳) — סה"כ']
hp=lambda x: '—' if x is None else f"{x*100:.0f}%"
h=D['H2H'][0]
CF=dict((g,s) for g,s in D['CONFS'])
cr=SS['GROK crypto — סה"כ']; pn=SS['GROK portfolio-news-scan — סה"כ']; xt=SS['GROK x-trends-digest — סה"כ']; SG=dict((g,s) for g,s in D['S'])
PS=dict((g,s) for g,s in D['P_SUM']['stats']); CRL=SG['GROK crypto — LONG']; CRS=SG['GROK crypto — SHORT']; ALC=TS['קריפטו — סה"כ (כל המקורות)']
for t in [
 f"• בוט v2.8: {bt['tp1']} TP1 מול {bt['stop']} סטופים ({hp(bt['hit'])} הצלחה), ממוצע {fmt(bt['avg_ret'])}, MAE {fmt(bt['mae'])}. GROK automation: {gk['tp1']}/{gk['stop']} ({hp(gk['hit'])}), ממוצע {fmt(gk['avg_ret'])}, MAE {fmt(gk['mae'])}, על {gk['n_data']} סטאפים.",
 f"• GROK crypto (ימים קלנדריים): {cr['tp1']} TP1 מול {cr['stop']} סטופים ({hp(cr['hit'])}), ממוצע {fmt(cr['avg_ret'])}, MAE {fmt(cr['mae'])}, על {cr['n_data']} סטאפים. לונג {CRL['tp1']}/{CRL['stop']} ({hp(CRL['hit'])}, {fmt(CRL['avg_ret'])}); שורט {CRS['tp1']}/{CRS['stop']} ({hp(CRS['hit'])}, {fmt(CRS['avg_ret'])}, MAE {fmt(CRS['mae'])}). כל הקריפטו (כולל portfolio/x-trends): {ALC['tp1']}/{ALC['stop']} ({hp(ALC['hit'])}), ממוצע {fmt(ALC['avg_ret'])}.",
 f"• portfolio-news-scan: {pn['tp1']}/{pn['stop']} ({hp(pn['hit'])}), ממוצע {fmt(pn['avg_ret'])}, MAE {fmt(pn['mae'])}. x-trends-digest: {xt['tp1']}/{xt['stop']} ({hp(xt['hit'])}), ממוצע {fmt(xt['avg_ret'])}, MAE {fmt(xt['mae'])}. ברובם מחיר הטריגר לא תאם לשוק, והכניסה = פתיחה. daily-stock-tracker: אין סטאפים — לא נוספו שורות.",
 f"• בוט לפי סריקה: 4.10 (3 ימים) {SG['בוט — סריקה 04.10']['tp1']}/{SG['בוט — סריקה 04.10']['stop']} ו-{SG['בוט — סריקה 04.10']['open']} פתוחים, ממוצע {fmt(SG['בוט — סריקה 04.10']['avg_ret'])}; 30.09 {SG['בוט — סריקה 30.09']['tp1']}/{SG['בוט — סריקה 30.09']['stop']} ו-{SG['בוט — סריקה 30.09']['open']} פתוחים, ממוצע {fmt(SG['בוט — סריקה 30.09']['avg_ret'])}; 27.09 {SG['בוט — סריקה 27.09']['tp1']}/{SG['בוט — סריקה 27.09']['stop']}; 24.09 {SG['בוט — סריקה 24.09']['tp1']}/{SG['בוט — סריקה 24.09']['stop']}. 7.10 (יום אחד) {SG['בוט — סריקה 07.10']['tp1']}/{SG['בוט — סריקה 07.10']['stop']} ו-{SG['בוט — סריקה 07.10']['open']} פתוחים, ממוצע {fmt(SG['בוט — סריקה 07.10']['avg_ret'])}.",
 f"• ראש בראש 7.9 ({h[1]} ימים): בוט {fmt(h[2]['avg'])} ({h[2]['tp1']}/{h[2]['stop']}) מול Grok {fmt(h[3]['avg'])} ({h[3]['tp1']}/{h[3]['stop']}).",
 f"• לפי סוג ב-Grok automation: 'לפני פריצה' שורט הכי טוב ({TS['לפני פריצה — GROK SHORT']['tp1']}/{TS['לפני פריצה — GROK SHORT']['stop']}, {fmt(TS['לפני פריצה — GROK SHORT']['avg_ret'])}), 'לפני פריצה' לונג הכי חלש ({TS['לפני פריצה — GROK LONG']['tp1']}/{TS['לפני פריצה — GROK LONG']['stop']}, {fmt(TS['לפני פריצה — GROK LONG']['avg_ret'])}). הגיליון המקורי (יולי–אוג׳): {o['tp1']}/{o['stop']}, ממוצע {fmt(o['avg_ret'])}.",
 f"• Perplexity (חדש): v2.7 {PS['Perplexity v2.7 — סה\"כ']['tp1']}/{PS['Perplexity v2.7 — סה\"כ']['stop']} ({hp(PS['Perplexity v2.7 — סה\"כ']['hit'])}), ממוצע {fmt(PS['Perplexity v2.7 — סה\"כ']['avg_ret'])}, MAE {fmt(PS['Perplexity v2.7 — סה\"כ']['mae'])}; value/turnaround {PS['Perplexity value/turnaround — סה\"כ']['tp1']}/{PS['Perplexity value/turnaround — סה\"כ']['stop']}, ממוצע {fmt(PS['Perplexity value/turnaround — סה\"כ']['avg_ret'])}; כל Perplexity: {PS['Perplexity — כל המקורות']['tp1']}/{PS['Perplexity — כל המקורות']['stop']} ({hp(PS['Perplexity — כל המקורות']['hit'])}), ממוצע {fmt(PS['Perplexity — כל המקורות']['avg_ret'])}. {PS['Perplexity — כל המקורות']['untrig']} סטאפים לא הופעלו (הכניסה לא נסחרה) ו-{PS['Perplexity — כל המקורות']['nolev']} בלי סטופ/יעד מספריים. פירוט בעמוד Perplexity.",
 f"• חזרות וסתירות: {D['REP_T']} טיקרים חוזרים; {D['NDUP']} כפילויות מדויקות נספרות פעם אחת. {D['NPAIRS']} זוגות לונג/שורט סותרים ({D['NPAIRS_C']} בקריפטו). Grok automation בסתירה: {hp(CF['GROK — בסתירת כיוון']['hit'])} הצלחה; בלי סתירה: {hp(CF['GROK — בלי סתירה']['hit'])}.",
]: para(t,9.5)
h1('טבלת סיכום')
head=['קבוצה','שורות','עם נתונים','ימים','TP1','סטופ','פתוח','הצלחה','ממוצע','% ברווח','לפי כללים','יום 5','יום 10','MFE','MAE']
mk=lambda L:[[g,s['n'],s['n_data'],s['days'],s['tp1'],s['stop'],s['open'],hp(s['hit']),fmt(s['avg_ret']),hp(s['win_mtm']),fmt(s['avg_rule']),fmt(s['d5']),fmt(s['d10']),fmt(s['mfe']),fmt(s['mae'])] for g,s in L]
table(head,mk(D['S']),[52]+[15.0]*14)
pdf.add_page(); h1('אוטומציות Grok — מה נוסף')
table(['אוטומציה','קבצים','תאריכים','קבצים עם סטאפים','סטאפים','בלשונית','הוחרגו','קריפטו','מניות/מדדים','כניסה=פתיחה','אין נתונים','לא נוספו','סטטוס'],
 [[f"GROK {a['name']}",a['files'],f"{a['first'][8:10]}.{a['first'][5:7]}–{a['last'][8:10]}.{a['last'][5:7]}",a['files_setups'],a['setups'],a['kept'],a['excl'],a['crypto'],a['stocks'],a['fixed'],a['nodata'],a['skipped'],('אין סטאפים (no trade setups)' if not a['setups'] else 'נוסף')] for a in D['AUTO']]+[['GROK automation (3 קטגוריות)',21,'07.09–28.09',21,210,n['grok'],D['nsrcx']['grok'],0,n['grok']+D['nsrcx']['grok'],'—','—','—','כמו קודם']],
 [46,12,22,17,14,14,14,14,17,17,14,14,62],6.8)
para("crypto: 9 שורות בקובץ 17.07-2 הן העתק של 25.09 ולא נוספו. x-trends-digest: הקובץ של 25.09 זהה ל-20.09; 3 קבצים הם צילומי ממשק. daily-stock-tracker: רק כיוון, ציון ומחיר (9 מתוך 24 קבצים הם צילומי ממשק). לא נמצאו קבצי near-low/momentum/prebreakout חדשים לפני 7.9 או אחרי 28.9.",8.3,color=(70,70,70))
h1('סריקת בוט v2.8 — 07.10.2026 (נתונים מסגירת 06.10, יום 1 = 07.10, מבוסס טריגר; נמדדה על יום אחד)')
table(['#','טיקר','כיוון','מחיר','טריגר','סטופ','TP1','TP2','TP3','ציון','סטטוס'],[[i+1,t,d,e,tr,s_,tp[0],tp[1],tp[2],sc,o_] for i,(t,d,e,tr,s_,tp,sc,o_) in enumerate(D['BOT107'])],[10,18,16,20,20,20,20,20,20,14,26],7.5)
h1('סריקת בוט v2.8 — 04.10.2026 (יום 1 = 05.10, נמדדה על 3 ימים)')
table(['#','טיקר','כיוון','כניסה','סטופ','TP1','TP2','TP3','סטטוס (תשואה)'],[[i+1,t,d,e,s_,tp[0],tp[1],tp[2],o_] for i,(t,d,e,s_,tp,o_) in enumerate(D['BOT104'])],[10,20,18,22,22,22,22,22,40],7.5)
h1('קריפטו — הטובים והחלשים (GROK crypto + portfolio/x-trends; Perplexity crypto בעמוד Perplexity)')
table(['טיקר','תאריך','כיוון','תשואה','תוצאה'],[[a,b[8:10]+'.'+b[5:7],c,fmt(d_),e] for a,b,c,d_,e in D['CRY']['top']+D['CRY']['bottom']],[40,25,25,25,40],7.5)
pdf.add_page(); h1('פילוח לפי מקור')
table(head,mk(D['SS']),[52]+[15.0]*14)
h1('פילוח לפי סוג טרייד')
table(head,mk(D['TS']),[62]+[14.3]*14)
pdf.add_page(); h1('ראש בראש: בוט v2.8 מול GROK automation')
table(['השוואה','חלון','בוט n','בוט ממוצע','בוט % ברווח','בוט TP1/סטופ','Grok n','Grok ממוצע','Grok % ברווח','Grok TP1/סטופ','שפל שנתי','לפני פריצה','מומנטום'],
 [[l,N,x['n'],fmt(x['avg']),hp(x['win']),f"{x['tp1']}/{x['stop']}",y['n'],fmt(y['avg']),hp(y['win']),f"{y['tp1']}/{y['stop']}"]+[fmt(c[k]['avg'])+f" (n={c[k]['n']})" for k in ['near-low','prebreakout','momentum']] for l,N,x,y,c,o in D['H2H']],
 [55,12,14,18,18,18,14,18,18,18,25,25,24],7)
para("טיקרים שהופיעו גם בבוט וגם ב-Grok: "+', '.join(D['OVL'])+". ב-SNDK (7.9) הבוט שורט ו-Grok לונג.",8.5,color=(70,70,70))
h1('הטובים והחלשים (כל המקורות)')
rows=[[a,b[8:10]+'.'+b[5:7],c,d,fmt(e),f] for a,b,c,d,e,f in D['best']+D['worst']]
table(['מקור','תאריך','טיקר','כיוון','תשואה','תוצאה'],rows,[60,25,25,25,25,40])
pdf.add_page(); h1('חזרות, כפילויות וסתירות כיוון')
para(f"{D['REP_T']} טיקרים מופיעים יותר מפעם אחת. (א) כפילות מדויקת (אותו מקור, תאריך וכיוון): {D['NDUP']} קבוצות, ב-Grok automation וב-GROK crypto — השורה הנוספת נשארת בגיליון ומסומנת 'לא נספר'. (ב) חזרה באותו כיוון בתאריך מאוחר: {D['NB']} טיקרים. (ג) סתירת כיוון (לונג מול שורט באותו יום או בחלון מעקב חופף של 20 ימי מסחר; בקריפטו 20 ימים קלנדריים): {D['NC']} טיקרים, {D['NPAIRS']} זוגות ({D['SDAY']} באותו יום). היפוך כיוון בלי חפיפה (יולי–אוג׳ מול ספט׳): {D['ND']} טיקרים; גרפי אילן לאותה התראה: {D['NE']} — שניהם לא נספרים כסתירה.",9)
para(f"מי ניצח: {D['WL']+D['WS']} זוגות הוכרעו לפי תוצאה (לונג {D['WL']}, שורט {D['WS']}); {D['NTIE']} תיקו; {D['NOPEN']} פתוחים בשני הצדדים (מוביל: לונג {D['OL']}, שורט {D['OS']}); {D['NNA']} טרם הוכרעו (לאחד הצדדים אין עדיין נתונים, בעיקר סריקת הבוט 04.10).",9)
h1('לפני / אחרי ניקוי כפילויות')
table(['קבוצה','n לפני','TP1/סטופ לפני','הצלחה לפני','ממוצע לפני','MAE לפני','n אחרי','TP1/סטופ אחרי','הצלחה אחרי','ממוצע אחרי','MAE אחרי'],
 [[g,b['n'],f"{b['tp1']}/{b['stop']}",hp(b['hit']),fmt(b['avg_ret']),fmt(b['mae']),a['n'],f"{a['tp1']}/{a['stop']}",hp(a['hit']),fmt(a['avg_ret']),fmt(a['mae'])] for g,b,a in D['BA']],
 [57]+[22]*10,7)
h1('סתירת כיוון מול בלי סתירה (אחרי ניקוי)')
table(['קבוצה','שורות','עם נתונים','TP1','סטופ','פתוח','הצלחה','ממוצע','% ברווח','MFE','MAE'],
 [[g,x['n'],x['n_data'],x['tp1'],x['stop'],x['open'],hp(x['hit']),fmt(x['avg_ret']),hp(x['win_mtm']),fmt(x['mfe']),fmt(x['mae'])] for g,x in D['CONFS']],
 [57]+[22]*10,7.5)
pdf.add_page(); h1(f"זוגות בסתירת כיוון במניות בלי Perplexity ({len(D['PAIRS'])} מתוך {D['NPAIRS']}; זוגות הקריפטו בלשונית 'חזרות וסתירות', וזוגות Perplexity בעמוד Perplexity) — מי ניצח")
table(['טיקר','א: תאריך','א: מקור','א: כיוון','א: תוצאה','א: תשואה','ב: תאריך','ב: מקור','ב: כיוון','ב: תוצאה','ב: תשואה','מנצח'],
 [[p[0],p[1],p[2],p[3],p[4],fmt(p[5]),p[6],p[7],p[8],p[9],fmt(p[10]),p[12]] for p in D['PAIRS']],
 [13,14,30,14,17,16,14,30,14,17,16,82],6.5)
para("תשואה = תשואה מצטברת מותאמת כיוון עד סגירת 07.10 (החלונות באורך שונה). מנצח = התוצאה הטובה יותר (TP1 > פתוח > סטופ); בתוצאה זהה — תיקו, עם המוביל לפי תשואה. פירוט מלא, כולל שורות הגיליון וסוג החפיפה, בלשונית 'חזרות וסתירות'.",8,color=(70,70,70))
h1('כפילויות מדויקות')
table(['טיקר','תאריך','כיוון','קטגוריות','תוצאות','נספרת שורה'],[[x['ticker'],x['date'][8:10]+'.'+x['date'][5:7],x['dir'],' + '.join((c or 'crypto') for c in x['cats']),' / '.join(x['outcomes']),x['kept']] for x in D['DUPS']],[25,25,20,60,50,30],7.5)
pdf.add_page(); h1('Perplexity — מקור חדש (07.10.2026)')
PSm=D['P_SUM']
para(f"{PSm['nparsed']+PSm['nskip']} סטאפים ב-13 הרצות של Perplexity Tasks (12.08–04.10). נקלטו {PSm['nparsed']}; {PSm['nskip']} לא נקלטו (הרצת value מ-13.08 החזירה טיקרים מוסתרים XXXX). {PSm['nexcl']} הוחרגו (MCAP<1.5B), {PSm['nkept']} בלשונית הראשית. תאריך התראה = תאריך הריצה; יום 1 = יום המסחר הבא (קריפטו: מהשעה שאחרי הריצה, ימים קלנדריים). כניסה = המחיר/טריגר מהטבלה, ואם אין — פתיחת יום 1. סטופ/TP נספרים רק אחרי שהכניסה נסחרה; לא נסחרה → 'לא הופעל'. חסר סטופ או TP1 → תשואות בלבד.",8.8)
table(['ריצה','מקור','תאריך','נקלטו','הוחרגו','לא נקלטו'],[[r[0],r[1],r[2][8:10]+'.'+r[2][5:7],r[3],r[4],r[5]] for r in PSm['runs']],[25,60,25,20,20,20],7.5)
h1('סטטיסטיקה לפי מקור — Perplexity מול בוט ו-Grok (נתונים מעודכנים)')
table(['קבוצה','שורות','עם נתונים','לא הופעל','בלי רמות','TP1','סטופ','פתוח','הצלחה','ממוצע','% ברווח','MFE','MAE'],
 [[g,x['n'],x['n_data'],x['untrig'],x['nolev'],x['tp1'],x['stop'],x['open'],hp(x['hit']),fmt(x['avg_ret']),hp(x['win_mtm']),fmt(x['mfe']),fmt(x['mae'])] for g,x in PSm['stats']],[62]+[16.5]*12,6.8)
pdf.add_page(); h1('ראש בראש: Perplexity מול בוט / Grok באותו יום 1')
table(['השוואה','חלון','בוט/Grok n','ממוצע','% ברווח','TP1/סטופ','Perplexity n','ממוצע','% ברווח','TP1/סטופ','משותפים'],
 [[l,N,x['n'],fmt(x['avg']),hp(x['win']),f"{x['tp1']}/{x['stop']}",y['n'],fmt(y['avg']),hp(y['win']),f"{y['tp1']}/{y['stop']}",', '.join(o) or '—'] for l,N,x,y,o in PSm['H2P']],[78,12,18,18,18,18,20,18,18,18,22],7)
h1(f"עסקאות Perplexity פתוחות כרגע ({len(PSm['open'])})")
table(['מקור','תאריך','טיקר','כיוון','כניסה','סטופ','TP1','ימים','תשואה','סטטוס'],[[o[0],o[1][8:10]+'.'+o[1][5:7],o[2],o[3],f"{o[4]:.2f}",('—' if o[5] is None else f"{o[5]:g}"),('—' if o[6] is None else f"{o[6]:g}"),o[7],fmt(o[8]),o[9]] for o in PSm['open']],[40,20,20,18,22,20,20,14,20,30],7)
_pp=[p for p in PSm['pairs'] if not ('crypto' in p[2] and 'crypto' in p[7]) and not ('x-trends' in p[2] or 'x-trends' in p[7] or 'portfolio' in p[2] or 'portfolio' in p[7])]
pdf.add_page(); h1(f"סתירות לונג/שורט עם Perplexity — {len(PSm['pairs'])} זוגות; כאן {len(_pp)} מול בוט / Grok automation / בתוך Perplexity (השאר מול x-trends, portfolio ו-crypto בלשונית Perplexity)")
table(['טיקר','א: תאריך','א: מקור','א: כיוון','א: תוצאה','א: תשואה','ב: תאריך','ב: מקור','ב: כיוון','ב: תוצאה','ב: תשואה','מנצח'],
 [[p[0].replace('-USD',''),p[1],p[2],p[3],p[4],fmt(p[5]),p[6],p[7],p[8],p[9],fmt(p[10]),p[11]] for p in _pp],[16,13,30,14,20,15,13,30,14,20,15,77],6.3)
h1('בעיות פענוח')
for t in PSm['prob']: para('• '+t,8.3,color=(70,70,70))
pdf.add_page(); h1('מסקנות והמלצות לשיפור')
for t in D['lessons']: para(t,9.2); pdf.ln(0.8)
pdf.add_page(); h1('הוחרגו — MCAP מתחת ל-1.5B')
ex=D['excl']; half=(len(ex)+1)//2
table(['טיקר','מקור','תאריך','סוג','MCAP','','טיקר','מקור','תאריך','סוג','MCAP'],[ (ex[i]+['']+(ex[i+half] if i+half<len(ex) else ['']*5)) for i in range(half)],[18,22,24,34,18,4,18,22,24,34,18],6.5)
h1('מתודולוגיה ופערים')
for t in D['METH']: para(t,8.3,color=(70,70,70))
pdf.output('/workspace/scan-tracker-report-2026-10-08.pdf'); print('pdf ok')
