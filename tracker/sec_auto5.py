# ---- Grok automations tab + gaps for new automation rows + data for the PDF
import os as _os, collections as _co
_AD=json.load(open('auto/grok_auto_parsed.json'))
_DIRS={'crypto':'crypto','portfolio-news-scan':'portfolio-news-scan','x-trends-digest':'x-trends-digest','daily-stock-tracker':'daily-stock-tracker'}
_SK={'crypto':'gcrypto','portfolio-news-scan':'gpns','x-trends-digest':'gxtd'}
AUTO_SUM=[]
_contam=[('grok-crypto-2026-07-17-2.md',s_) for s_ in ('LTC','XRP')]
for nm,dd_ in _DIRS.items():
    fl=sorted(_os.listdir(f'/workspace/grok-outputs/{dd_}'))
    rr=[x for x in _AD['rows'] if x['auto']==nm and (x['file'],x['sym']) not in _contam]
    ns=dict(_AD['nosetup']).get(nm,[]) if isinstance(_AD['nosetup'],dict) else []
    ns=_AD['nosetup'].get(nm,[])
    scr=[f_ for f_,w_ in ns if w_.startswith('לא פלט')]
    sk=[x for x in _AD['skipped'] if x['file'].startswith(f'grok-{nm}')]+([{'file':f_,'rank':None,'head':s_,'why':'העתק של שורה מ-25.09 (הודבק בטעות לקובץ של 17.7) — לא נוסף'} for f_,s_ in _contam] if nm=='crypto' else [])
    k_=_SK.get(nm)
    R_=[r for r in rows_full if r['source']==k_] if k_ else []
    AUTO_SUM.append(dict(name=nm,files=len(fl),first=min(__import__('re').search(r'\d{4}-\d\d-\d\d',f_).group(0) for f_ in fl),last=max(__import__('re').search(r'\d{4}-\d\d-\d\d',f_).group(0) for f_ in fl),files_setups=len({x['file'] for x in rr}),
        setups=len(rr),rows=len(R_),kept=sum(not r['excluded'] for r in R_),excl=sum(r['excluded'] for r in R_),skipped=len(sk),nosetup_files=len(ns),scrapes=len(scr),
        crypto=sum(r.get('ttype')=='קריפטו' for r in R_),stocks=sum(r.get('ttype')!='קריפטו' for r in R_),
        fixed=sum(bool(r.get('fixed')) for r in R_),nodata=sum(r['outcome']=='אין נתונים' for r in R_),
        status=('אין סטאפים (no trade setups) — רק כיוון/ציון/מחיר, בלי סטופ ויעדים; לא נוספו שורות' if not rr else f'{len(rr)} סטאפים עם כיוון, מחיר/טריגר, סטופ ויעד'),
        files_list=sorted({x['file'] for x in rr}),ns_list=ns,sk_list=[[x['file'],x.get('head',''),x['why']] for x in sk]))
at=wb.create_sheet('אוטומציות Grok'); at.sheet_view.rightToLeft=True
at.cell(1,1,'אוטומציות Grok שנאספו ל-/workspace/grok-outputs — מה נוסף לבקטסט').font=Font(name='Arial',bold=True,size=13,color='356854')
AH=['אוטומציה','קבצים','טווח תאריכים','קבצים עם סטאפים','סטאפים שפוענחו','שורות בלשונית הראשית','הוחרגו (MCAP<1.5B)','קריפטו','מניות/מדדים','כניסה = פתיחה','אין נתוני מחיר','שורות שלא נוספו','קבצים בלי סטאפים','מתוכם צילומי ממשק','סטטוס']
for j,h in enumerate(AH,1):
    c=at.cell(3,j,h); c.fill=HF; c.font=HFont; c.alignment=C; c.border=B
for i,a_ in enumerate(AUTO_SUM,4):
    v=[f"GROK {a_['name']}",a_['files'],f"{a_['first'][8:10]}.{a_['first'][5:7]}–{a_['last'][8:10]}.{a_['last'][5:7]}",a_['files_setups'],a_['setups'],a_['kept'],a_['excl'],a_['crypto'],a_['stocks'],a_['fixed'],a_['nodata'],a_['skipped'],a_['nosetup_files'],a_['scrapes'],a_['status']]
    for j,x in enumerate(v,1):
        c=at.cell(i,j,x); c.font=F; c.border=B; c.alignment=R if j==15 else C
at.cell(4+len(AUTO_SUM)+1,1,"הקבוצה הוותיקה 'GROK automation' (near-low / prebreakout / momentum, 21 קבצים 7–28.09) נשארת כמו קודם. לא נמצאו קבצים חדשים שלה לפני 7.9 או אחרי 28.9.").font=Font(name='Arial',italic=True,size=9)
k=4+len(AUTO_SUM)+3
at.cell(k,1,'פירוט קבצים').font=Font(name='Arial',bold=True,size=12,color='356854'); k+=1
for j,h in enumerate(['אוטומציה','קובץ','סטאפים','הערה'],1):
    c=at.cell(k,j,h); c.fill=HF; c.font=HFont; c.alignment=C; c.border=B
k+=1
_cnt=_co.Counter((x['auto'],x['file']) for x in _AD['rows'] if (x['file'],x['sym']) not in _contam)
for nm in _DIRS:
    for f_ in sorted(_os.listdir(f'/workspace/grok-outputs/{_DIRS[nm]}')):
        n_=_cnt.get((nm,f_),0); why=dict(_AD['nosetup'].get(nm,[])).get(f_,'')
        if f_=='grok-x-trends-digest-2026-09-25.md': why='זהה מילה במילה לקובץ של 20.09 — השורות נשמרו ומסומנות ככפולות/חזרות'
        if f_=='grok-crypto-2026-07-17-2.md': why='9 שורות (ONDO, BP, BTC 84,100, LTC, XRP, ETH, SOL, AVAX, LINK) הן העתק של שורות מ-25.09 שהודבקו בטעות — לא נוספו; נוספו רק BTC ו-ETH המקוריים'
        if f_=='grok-x-trends-digest-2026-09-21.md': why=why+' (זהה לצילום של 11.09)'
        for j,x in enumerate([nm,f_,n_,why],1):
            c=at.cell(k,j,x); c.font=F; c.border=B; c.alignment=R if j==4 else C
        k+=1
for j,wd in enumerate([24,36,12,12,12,12,12,9,10,10,10,10,10,10,60],1): at.column_dimensions[L(j)].width=wd
at.column_dimensions['D'].width=60 if False else 12
# gaps for new automation rows (same tab 'פערי Grok')
k=gp.max_row+2
gp.cell(k,1,'אוטומציות Grok נוספות (crypto / portfolio-news-scan / x-trends-digest) — בעמודת "קטגוריה" שם האוטומציה').font=Font(name='Arial',bold=True,size=11,color='356854'); k+=1
for r in sorted(AU,key=lambda r:(r['source'],r['alert_date'],r.get('file',''),r['rank'])):
    iss=[]
    fxn=[n_ for n_ in r['notes'] if n_.startswith('מחיר כניסה = פתיחה')]
    if r.get('fixed'): iss.append(('מחיר לא תואם שוק' if r['fixed']=='mismatch' else 'אין מחיר בטבלה','טופל — כניסה = פתיחה'+(' (הוחרג MCAP)' if r['excluded'] else ', נכלל בסטטיסטיקה'),fxn[0] if fxn else ''))
    if r['outcome']=='אין נתונים': iss.append(('אין נתוני מחיר','פתוח — לא חושב (לא הומצא מחיר)',' '.join(n_ for n_ in r['notes'] if 'Yahoo' in n_)[:300]))
    rest=[g_ for g_ in (r.get('parse_gaps') or []) if not g_.startswith('אין מחיר')]
    if rest: iss.append(('פער פענוח','פתוח — לא הוזן ערך שלא הופיע במקור','; '.join(rest)))
    for a_,st_,b__ in iss:
        for j,x in enumerate([pd.Timestamp(r['alert_date']).to_pydatetime(),r['auto'],r['rank'],r['ticker'],r['dir'],a_,st_,b__],1):
            c=gp.cell(k,j,x); c.font=F; c.border=B; c.alignment=R if j==8 else C
            if st_.startswith('טופל'): c.fill=OKF
            if j==1: c.number_format=DATE
        k+=1
# crypto + bot 4.10 data for PDF
_crk=[r for r in rows_counted if r.get('ttype')=='קריפטו' and r['source']!='pcry']
CRY=dict(n_all=sum(r.get('ttype')=='קריפטו' for r in rows_full),n_excl=sum(r.get('ttype')=='קריפטו' and r['excluded'] for r in rows_full),n_kept=sum(r.get('ttype')=='קריפטו' for r in rows),n_counted=len(_crk),
    nodata=sum(r['outcome']=='אין נתונים' for r in _crk),fixed=sum(bool(r.get('fixed')) for r in _crk),
    top=[[r['ticker'],r['alert_date'],r['dir'],r['cum'][-1],r['outcome']] for r in sorted([r for r in _crk if r['cum']],key=lambda r:-r['cum'][-1])[:5]],
    bottom=[[r['ticker'],r['alert_date'],r['dir'],r['cum'][-1],r['outcome']] for r in sorted([r for r in _crk if r['cum']],key=lambda r:r['cum'][-1])[:5]])
BOT104=[[r['ticker'],r['dir'],r['entry'],r['sl'],list(r['tps']),r['outcome']+(f" ({r['cum'][-1]*100:+.1f}%)" if r['cum'] else '')] for r in rows if r['source']=='bot' and r['alert_date']=='2026-10-04']
BOT107=[[r['ticker'],r['dir'],r['entry'],r.get('trig'),r['sl'],list(r['tps']),r.get('score'),r['outcome']] for r in rows if r['source']=='bot' and r['alert_date']=='2026-10-07']
