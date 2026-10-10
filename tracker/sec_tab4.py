# ---- new tab: repeats & conflicts
CLS={'a':'כפילות מדויקת','b':'חזרה (אותו כיוון)','c':'סתירת כיוון','d':'היפוך בלי חפיפה','e':'גרף אילן לאותה התראה'}
dt=wb.create_sheet('חזרות וסתירות',1); dt.sheet_view.rightToLeft=True
def dh(rr,cols):
    for j,h in enumerate(cols,1):
        c=dt.cell(rr,j,h); c.fill=HF; c.font=HFont; c.alignment=C; c.border=B
    dt.row_dimensions[rr].height=32
def dtitle(rr,t): dt.cell(rr,1,t).font=Font(name='Arial',bold=True,size=13,color='356854')
dtitle(1,f'חזרות וסתירות — {REP_T} טיקרים שמופיעים יותר מפעם אחת בלשונית הראשית')
c=dt.cell(2,1,f"כפילויות מדויקות: {len(DUPS)} קבוצות (השורה הנוספת 'לא נספר'). טיקרים עם חזרה באותו כיוון: {NB_}. טיקרים עם סתירת כיוון: {NC_}, זוגות סותרים: {NPAIRS} ({SDAY} באותו יום). היפוך בלי חפיפת חלונות: {ND_} טיקרים. גרפי אילן לאותה התראה: {NE_}. מנצחים בזוגות שהוכרעו: לונג {WL}, שורט {WS_}; תיקו {len(WK['tie'])}; שניהם פתוחים {len(WK['open'])}; טרם הוכרע {len(WK['na'])}.")
c.font=Font(name='Arial',size=10); c.alignment=R; dt.merge_cells('A2:O2'); dt.row_dimensions[2].height=36
dtitle(4,'1. כל הקבוצות (שורה לכל הופעה)')
GH2=['טיקר','סיווג הקבוצה','שורה בלשונית הראשית','מקור','קטגוריה / סוג','תאריך התראה','כיוון','מחיר התראה','סטופ','TP1','תוצאה','תשואה (יום אחרון)','ימים','נספר בסטטיסטיקה','חזרות / סתירות']
dh(5,GH2); k=6
GF=[PatternFill('solid',fgColor='F3F7F5'),None]
for gi,g in enumerate(GROUPS):
    lab=', '.join(CLS[x] for x in 'abcde' if x in g['cls'])
    for r in sorted(g['rows'],key=lambda r:(r['alert_date'] or '9999',r['_row'])):
        v=[g['ticker'],lab,r['_row'],SRCD[r['source']],r.get('cat') or r.get('ttype') or '',pd.Timestamp(r['alert_date']).to_pydatetime() if r['alert_date'] else 'חסר תאריך',r['dir'],r['entry'],r['sl'],r['tps'][0] if r['tps'] else None,r['outcome'],r['cum'][-1] if r['cum'] else None,r['ndays'],
           ('לא — כפילות' if r['dup_skip'] else ('לא — גרף אילן (קבוצה נפרדת)' if r['source']=='ilan' else 'כן')),r['dupnote']]
        for j,x in enumerate(v,1):
            c=dt.cell(k,j,x); c.font=F; c.border=B; c.alignment=R if j==15 else C
            if GF[gi%2]: c.fill=GF[gi%2]
            if j==6: c.number_format=DATE
            if j in (8,9,10): c.number_format=USD
            if j==12: c.number_format='0.00%'
            if j==14 and r['dup_skip']: c.fill=PatternFill('solid',fgColor='F8D7DA')
        k+=1
k+=1; dtitle(k,f'2. כפילויות מדויקות ({len(DUPS)}) — אותו מקור, תאריך וכיוון'); k+=1
dh(k,['טיקר','תאריך','מקור','כיוון','שורות','קטגוריות','רמות','תוצאות','תשואות','נספרת שורה']); k+=1
for x in DUPS:
    v=[x['ticker'],fd(x['date']),x['source'],x['dir'],', '.join(map(str,x['rows'])),' + '.join((c_ or 'crypto') for c_ in x['cats']),x['levels'],' / '.join(x['outcomes']),' / '.join(f"{y*100:+.1f}%" for y in x['rets'] if y is not None),x['kept']]
    for j,y in enumerate(v,1):
        c=dt.cell(k,j,y); c.font=F; c.border=B; c.alignment=R if j==7 else C
    dt.row_dimensions[k].height=30; k+=1
k+=1; dtitle(k,f'3. זוגות בסתירת כיוון ({NPAIRS})'); k+=1
dh(k,['טיקר','צד א׳: שורה','צד א׳: תאריך','צד א׳: מקור','צד א׳: כיוון','צד א׳: תוצאה','צד א׳: תשואה','צד ב׳: שורה','צד ב׳: תאריך','צד ב׳: מקור','צד ב׳: כיוון','צד ב׳: תוצאה','צד ב׳: תשואה','חפיפה','מנצח']); k+=1
for p in PAIRS:
    a,b=p['a'],p['b']
    v=[p['ticker'],a['_row'],fd(a['alert_date']),srcl(a),a['dir'],a['outcome'],a['cum'][-1] if a['cum'] else None,b['_row'],fd(b['alert_date']),srcl(b),b['dir'],b['outcome'],b['cum'][-1] if b['cum'] else None,p['act'],p['winner']]
    for j,y in enumerate(v,1):
        c=dt.cell(k,j,y if y is not None else '—'); c.font=F; c.border=B; c.alignment=C
        if j in (7,13) and y is not None: c.number_format='0.0%'
    dt.row_dimensions[k].height=30; k+=1
k+=1
for t in ["הגדרות: כפילות מדויקת = אותו מקור, תאריך וכיוון (נספרת הקטגוריה הראשונה בסדר near-low → prebreakout → momentum). חזרה = אותו טיקר ואותו כיוון בתאריך מאוחר יותר. סתירה = לונג מול שורט באותו יום או כשההתראה המאוחרת בתוך 20 ימי המסחר של המוקדמת. היפוך בלי חפיפה = כיוון הפוך אבל החלונות לא חופפים (גיליון יולי–אוג׳ מול ספטמבר). גרפי אילן הם מבט לונג משוער בלי סטופ/יעדים, ולכן לא נספרים כחזרה או כסתירה.",
          "מנצח: התוצאה הטובה יותר (TP1 > פתוח > סטופ). תוצאה זהה = תיקו, ומצוין מי מוביל לפי התשואה עד כה (התשואות נמדדו על חלונות באורך שונה). סריקת הבוט מ-30.09 עוד לא נסחרה, ולכן זוגות מולה 'טרם הוכרע'."]:
    c=dt.cell(k,1,t); c.font=Font(name='Arial',size=9,italic=True); c.alignment=R; dt.merge_cells(start_row=k,end_row=k,start_column=1,end_column=15); dt.row_dimensions[k].height=40; k+=1
for j,wd in enumerate([8,26,10,14,18,12,8,11,10,10,10,11,7,16,80],1): dt.column_dimensions[L(j)].width=wd
dt.freeze_panes='B6'
# ---- report data for the PDF
_old=json.load(open('report_data.json')) if __import__('os').path.exists('report_data.json') else {}
_best=[[r['group'],r['alert_date'],r['ticker'],r['dir'],r['cum'][-1],r['outcome']] for r in w[:8]]
_worst=[[r['group'],r['alert_date'],r['ticker'],r['dir'],r['cum'][-1],r['outcome']] for r in w[::-1][:8]]
_src={k_:sum(r['source']==k_ for r in rows) for k_ in ('bot','orig','ilan','grok','gcrypto','gpns','gxtd')}
_srcx={k_:sum(r['source']==k_ for r in excl) for k_ in ('bot','orig','ilan','grok','gcrypto','gpns','gxtd')}
_SN={'bot':'בוט','orig':'גיליון','ilan':'גרף אילן','grok':'GROK auto','gcrypto':'GROK crypto','gpns':'GROK pns','gxtd':'GROK xtd'}
_excl=[[r['ticker'],_SN[r['source']],r['alert_date'] or '',(r.get('ttype') or '')+(f" ({r['cat']})" if r.get('cat') else ''),mc(r['mcap_used'])] for r in sorted(excl,key=lambda r:(order[r['source']],r['alert_date'] or '',r['ticker']))]
RD=dict(S=S,SS=SS,TS=TS,H2H=H2H,OVL=OVL,lessons=LESSONS,best=_best,worst=_worst,excl=_excl,nsrcx=_srcx,nrows=len(rows),ncounted=len(rows_counted),nsrc=_src,AUTO=AUTO_SUM,CRY=CRY,BOT104=BOT104,METH=METH,
        BA=BA,CONFS=CONFS,REP_T=REP_T,NPAIRS=NPAIRS,NDUP=len(DUPS),NB=NB_,NC=NC_,ND=ND_,NE=NE_,SDAY=SDAY,WL=WL,WS=WS_,NTIE=len(WK['tie']),NOPEN=len(WK['open']),OL=OL,OS=OS,NNA=len(WK['na']),
        DUPS=[dict(x) for x in DUPS],
        NPAIRS_C=sum(p['a'].get('ttype')=='קריפטו' for p in PAIRS),PAIRS=[[p['ticker'],fd(p['a']['alert_date']),srcl(p['a']),p['a']['dir'],p['a']['outcome'],p['a']['cum'][-1] if p['a']['cum'] else None,fd(p['b']['alert_date']),srcl(p['b']),p['b']['dir'],p['b']['outcome'],p['b']['cum'][-1] if p['b']['cum'] else None,p['act'],p['winner']] for p in PAIRS if p['a'].get('ttype')!='קריפטו'])
json.dump(RD,open('report_data.json','w'),ensure_ascii=False,indent=1,default=str)
