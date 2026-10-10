# ---- inserted into summary: repeats / conflicts section
def pkind(p):
    w=p['winner']
    return 'na' if w.startswith('טרם') else 'open' if w.startswith('שניהם פתוחים') else 'tie' if w.startswith('תיקו') else 'dec'
WK={k:[p for p in PAIRS if pkind(p)==k] for k in ('dec','open','tie','na')}
WL=sum(p['wside']=='LONG' for p in WK['dec']); WS_=sum(p['wside']=='SHORT' for p in WK['dec'])
OL=sum(p['wside']=='LONG' for p in WK['open']); OS=sum(p['wside']=='SHORT' for p in WK['open'])
NA_=sum('a' in g['cls'] for g in GROUPS); NB_=sum('b' in g['cls'] for g in GROUPS); NC_=sum('c' in g['cls'] for g in GROUPS)
ND_=sum('d' in g['cls'] for g in GROUPS); NE_=sum('e' in g['cls'] for g in GROUPS)
SDAY=sum(p['same_day'] for p in PAIRS)
title(nx,'חזרות, כפילויות וסתירות כיוון (טיקר שהופיע יותר מפעם אחת)')
para(nx+1,f"{REP_T} טיקרים מופיעים יותר מפעם אחת בלשונית הראשית. (א) כפילות מדויקת — אותו מקור, תאריך וכיוון: {len(DUPS)} קבוצות ({NA_} טיקרים), ב-Grok automation כשאותו סטאפ הופיע בשתי קטגוריות באותה ריצה, וב-GROK crypto כשאותו מטבע הופיע בשתי ריצות באותו יום. השורה הנוספת נשארת בגיליון אבל מסומנת 'לא נספר', כך שבסטטיסטיקה נספרות {len(rows_counted)} שורות מתוך {len(rows)}. (ב) חזרה בתאריך מאוחר יותר באותו כיוון: {NB_} טיקרים. (ג) סתירת כיוון — לונג מול שורט באותו יום או בחלונות מעקב חופפים (20 ימי מסחר; בקריפטו 20 ימים קלנדריים): {NC_} טיקרים, {NPAIRS} זוגות ({SDAY} באותו יום). בנוסף: היפוך כיוון בלי חפיפת חלונות (יולי–אוג׳ מול ספט׳) ב-{ND_} טיקרים, וגרפי אילן לאותה התראה ב-{NE_} טיקרים — שניהם לא נספרים כסתירה. פירוט מלא בלשונית 'חזרות וסתירות' ובעמודה 'חזרות / סתירות'.",62,10)
nx+=3
title(nx,'לפני ואחרי ניקוי כפילויות מדויקות (הצלחה = TP1 מול סטופ מתוך המוכרעים)')
hdr(nx+1,['קבוצה','שורות לפני','TP1/סטופ לפני','הצלחה לפני','תשואה ממוצעת לפני','MAE לפני','שורות אחרי','TP1/סטופ אחרי','הצלחה אחרי','תשואה ממוצעת אחרי','MAE אחרי'])
k=nx+2
for g,b,a in BA:
    v=[g,b['n'],f"{b['tp1']}/{b['stop']}",b['hit'],b['avg_ret'],b['mae'],a['n'],f"{a['tp1']}/{a['stop']}",a['hit'],a['avg_ret'],a['mae']]
    for j,x in enumerate(v,1):
        c=sm.cell(k,j,x if x is not None else '—'); c.font=Font(name='Arial',size=10,bold=('סה"כ' in g)); c.border=B; c.alignment=C
        if j in (4,5,6,9,10,11) and x is not None: c.number_format='0.0%'
        if k%2==1: c.fill=STR
    k+=1
para(k,"בבוט v2.8, ב-portfolio-news-scan וב-x-trends-digest אין כפילויות מדויקות, ולכן המספרים זהים. ב-Grok automation הוסרו מהספירה 5 שורות: HPQ 14.9 (momentum, נספר ב-prebreakout), VICR 18.9, GNRC 18.9, GRAL 25.9 ו-MRNA 28.9 (momentum, נספרו ב-near-low). כלל השמירה: נספרת הקטגוריה הראשונה בסדר near-low → prebreakout → momentum. ב-GROK crypto הוסרו "+str(sum(1 for x in DUPS if x['source']=='GROK crypto'))+" שורות: אותו מטבע ואותו כיוון בשתי ריצות של 17.07 (נספרת הריצה הראשונה).",36,9)
nx=k+2
title(nx,'סטאפים בסתירת כיוון מול סטאפים בלי סתירה (אחרי ניקוי כפילויות)')
CC=['קבוצה','שורות','עם נתונים','TP1','סטופ','פתוחים','אחוז הצלחה','תשואה ממוצעת','% ברווח','MFE ממוצע','MAE ממוצע']
hdr(nx+1,CC); k=nx+2
for g,x in CONFS:
    v=[g,x['n'],x['n_data'],x['tp1'],x['stop'],x['open'],x['hit'],x['avg_ret'],x['win_mtm'],x['mfe'],x['mae']]
    for j,y in enumerate(v,1):
        c=sm.cell(k,j,y if y is not None else '—'); c.font=F; c.border=B; c.alignment=C
        if j in (7,8,9,10,11) and y is not None: c.number_format='0.0%'
        if k%2==1: c.fill=STR
    k+=1
para(k,f"'בסתירת כיוון' = כל שורה שנמצאת בזוג לונג/שורט על אותו טיקר באותו יום או בחלון מעקב חופף. כל הסורקים = בוט + Grok + הגיליון המקורי (בלי גרפי אילן). מי ניצח ב-{NPAIRS} הזוגות: {len(WK['dec'])} הוכרעו לפי תוצאה (לונג {WL}, שורט {WS_}); {len(WK['tie'])} תיקו (שני הצדדים הגיעו לאותה תוצאה); {len(WK['open'])} עדיין פתוחים בשני הצדדים (מוביל לפי תשואה: לונג {OL}, שורט {OS}); {len(WK['na'])} טרם הוכרעו כי לאחד הצדדים אין עדיין נתונים (בעיקר סריקת הבוט מ-04.10, יום 1 = 05.10). כל הסורקים כולל עכשיו גם את GROK crypto, portfolio-news-scan ו-x-trends-digest.",40,9)
nx=k+2
title(nx,f'זוגות בסתירת כיוון במניות ({len([p for p in PAIRS if p["a"].get("ttype")!="קריפטו"])} מתוך {NPAIRS}; זוגות הקריפטו מפורטים בלשונית חזרות וסתירות) — מי ניצח')
hdr(nx+1,['טיקר','צד א׳: תאריך','צד א׳: מקור','צד א׳: כיוון','צד א׳: תוצאה','צד א׳: תשואה','צד ב׳: תאריך','צד ב׳: מקור','צד ב׳: כיוון','צד ב׳: תוצאה','צד ב׳: תשואה','חפיפה','מנצח'])
k=nx+2
PAIRS_S=[p for p in PAIRS if p['a'].get('ttype')!='קריפטו']
for p in PAIRS_S:
    a,b=p['a'],p['b']
    v=[p['ticker'],fd(a['alert_date']),srcl(a),a['dir'],a['outcome'],a['cum'][-1] if a['cum'] else None,fd(b['alert_date']),srcl(b),b['dir'],b['outcome'],b['cum'][-1] if b['cum'] else None,p['act'],p['winner']]
    for j,y in enumerate(v,1):
        c=sm.cell(k,j,y if y is not None else '—'); c.font=F; c.border=B; c.alignment=C
        if j in (6,11) and y is not None: c.number_format='0.0%'
        if k%2==1: c.fill=STR
    sm.row_dimensions[k].height=30
    k+=1
nx=k+1
