import pandas as pd, numpy as np
from dups import analyze, CATO
rows_full=pd.read_pickle('rows_all.pkl'); rows_all=[r for r in rows_full if not r['excluded']]; excl=[r for r in rows_full if r['excluded']]
order={'orig':0,'ilan':1,'bot':2,'grok':3,'gcrypto':4,'gpns':5,'gxtd':6,'p27':7,'p25':8,'pval':9,'pmom':10,'pcry':11}
PPS=('p27','p25','pval','pmom','pcry')
PPN={'p27':'Perplexity v2.7','p25':'Perplexity v2.5','pval':'Perplexity value/turnaround','pmom':'Perplexity momentum','pcry':'Perplexity crypto'}
rows_all=sorted(rows_all,key=lambda r:(r['alert_date'] or '9999',order[r['source']],CATO.get(r.get('cat'),9),r.get('rank') or 0,r['ticker']))
GROUPS,DUPS,PAIRS=analyze(rows_all)
rows_counted=[r for r in rows_all if not r['dup_skip']]
def st(rs):
    w=[r for r in rs if r['ndays']>0 and r['cum'] and r['outcome'] not in ('מחיר לא תואם','לא הופעל')]
    tp=sum(r['outcome']=='TP1' for r in w); sl=sum(r['outcome']=='סטופ' for r in w); op=sum(r['outcome']=='פתוח' for r in w)
    avg=lambda xs: float(np.mean(xs)) if xs else None
    return dict(n=len(rs),n_data=len(w),days=max([r['ndays'] for r in rs]+[0]),tp1=tp,stop=sl,open=op,
        hit=(tp/(tp+sl) if tp+sl else None), tp1_all=(tp/len(w) if w and any(r['sl'] or r['tps'][0] for r in w) else None),
        tp2=sum(r['tp_hit'][1] is not None and (r['stop_hit'] is None or r['tp_hit'][1]<=r['stop_hit']) for r in w),
        avg_ret=avg([r['cum'][-1] for r in w]), win_mtm=(sum(r['cum'][-1]>0 for r in w)/len(w) if w else None),
        avg_rule=avg([r['rule'] for r in w if r['rule'] is not None]),
        mfe=avg([r['mfe'] for r in w]), mae=avg([r['mae'] for r in w]),
        d5=avg([r['cum'][4] for r in w if len(r['cum'])>=5]), d10=avg([r['cum'][9] for r in w if len(r['cum'])>=10]), d20=avg([r['cum'][19] for r in w if len(r['cum'])>=20]),
        trig=sum(r['trig_dt'] is not None for r in w),untrig=sum(r['outcome']=='לא הופעל' for r in rs),nolev=sum(r['outcome']=='ללא סטופ/יעד' for r in w))
def compute(rows):
    bot=[r for r in rows if r['source']=='bot']; orig=[r for r in rows if r['source']=='orig']; il=[r for r in rows if r['source']=='ilan']
    G=[]
    for k in ['2026-09-07','2026-09-24','2026-09-27','2026-09-30','2026-10-04','2026-10-07']: G.append((f"בוט — סריקה {k[8:10]}.{k[5:7]}",[r for r in bot if r['alert_date']==k]))
    G+=[('בוט — סה"כ',bot),('בוט — LONG',[r for r in bot if r['dir']=='LONG']),('בוט — SHORT',[r for r in bot if r['dir']=='SHORT']),
        ('גיליון מקורי (יולי–אוג׳) — סה"כ',orig),('גיליון מקורי — GROK LONG',[r for r in orig if r['model']=='GROK' and r['dir']=='LONG']),
        ('גיליון מקורי — GROK SHORT',[r for r in orig if r['model']=='GROK' and r['dir']=='SHORT']),('גיליון מקורי — Perplexity',[r for r in orig if r['model']=='Perplexity']),
        ('גרפים של אילן (מבט לונג)',il)]
    gk=[r for r in rows if r['source']=='grok']
    G+=[('GROK automation — סה"כ',gk),('GROK automation — LONG',[r for r in gk if r['dir']=='LONG']),('GROK automation — SHORT',[r for r in gk if r['dir']=='SHORT'])]
    for k in sorted({r['alert_date'] for r in gk}): G.append((f"GROK — ריצה {k[8:10]}.{k[5:7]}",[r for r in gk if r['alert_date']==k]))
    gc=[r for r in rows if r['source']=='gcrypto']; gp=[r for r in rows if r['source']=='gpns']; gx=[r for r in rows if r['source']=='gxtd']
    CR=[r for r in rows if r.get('ttype')=='קריפטו']
    G+=[('GROK crypto — סה"כ',gc),('GROK crypto — LONG',[r for r in gc if r['dir']=='LONG']),('GROK crypto — SHORT',[r for r in gc if r['dir']=='SHORT'])]
    for m,lab in (('2026-07','יולי'),('2026-08','אוגוסט'),('2026-09','ספטמבר'),('2026-10','אוקטובר')):
        x=[r for r in gc if r['alert_date'][:7]==m]
        if x: G.append((f"GROK crypto — {lab}",x))
    G+=[('GROK crypto — כניסה = מחיר Grok',[r for r in gc if not r.get('fixed')]),('GROK crypto — כניסה = פתיחה',[r for r in gc if r.get('fixed')])]
    for nm,x in (('GROK portfolio-news-scan',gp),('GROK x-trends-digest',gx)):
        G+=[(f'{nm} — סה"כ',x),(f'{nm} — LONG',[r for r in x if r['dir']=='LONG']),(f'{nm} — SHORT',[r for r in x if r['dir']=='SHORT'])]
    PG={}
    for k_ in PPS:
        x=[r for r in rows if r['source']==k_]; PG[k_]=x
        G+=[(f'{PPN[k_]} — סה"כ',x),(f'{PPN[k_]} — LONG',[r for r in x if r['dir']=='LONG']),(f'{PPN[k_]} — SHORT',[r for r in x if r['dir']=='SHORT'])]
        if k_ in ('p27','pval','pcry'):
            for d_ in sorted({r['alert_date'] for r in x}): G.append((f"{PPN[k_]} — ריצה {d_[8:10]}.{d_[5:7]}",[r for r in x if r['alert_date']==d_]))
    PALL=[r for r in rows if r['source'] in PPS]
    G+=[('Perplexity — כל המקורות',PALL),('Perplexity — LONG',[r for r in PALL if r['dir']=='LONG']),('Perplexity — SHORT',[r for r in PALL if r['dir']=='SHORT']),
        ('Perplexity v2.7+v2.5 — עם רמות מספריות',[r for r in PALL if r['source'] in ('p27','p25') and r['alert_date'] not in ('2026-09-27','2026-10-04')])]
    S=[(g,st(rs)) for g,rs in G]
    # by source
    SRC=[('בוט v2.8 — סה"כ',bot)]+[(f'{PPN[k_]} — סה"כ',PG[k_]) for k_ in PPS]+[('Perplexity — כל המקורות',PALL),('GROK automation — סה"כ',gk),('GROK crypto — סה"כ',gc),('GROK portfolio-news-scan — סה"כ',gp),('GROK x-trends-digest — סה"כ',gx),('גיליון מקורי (יולי–אוג׳) — סה"כ',orig),('גרפים של אילן (מבט לונג)',il)]
    SS=[(g,st(rs)) for g,rs in SRC]
    TYP=[('Elliott v2.8 (בוט)',bot)]
    for t in ['שפל שנתי','לפני פריצה','מומנטום']:
        x=[r for r in gk if r['ttype']==t]
        TYP+=[(f'{t} — GROK automation',x),(f'{t} — GROK LONG',[r for r in x if r['dir']=='LONG']),(f'{t} — GROK SHORT',[r for r in x if r['dir']=='SHORT'])]
    TYP+=[('שפל שנתי — גיליון מקורי',orig),('שפל שנתי — סה"כ (GROK automation + גיליון)',[r for r in gk if r['ttype']=='שפל שנתי']+orig)]
    ST=[r for r in gp+gx if r.get('ttype')!='קריפטו']; CX=[r for r in gp+gx if r.get('ttype')=='קריפטו']
    TYP+=[('קריפטו — סה"כ (כל המקורות)',CR),('קריפטו — LONG',[r for r in CR if r['dir']=='LONG']),('קריפטו — SHORT',[r for r in CR if r['dir']=='SHORT']),
          ('קריפטו — GROK crypto',gc),('קריפטו — portfolio-news + x-trends',CX),
          ('מניות/מדדים — portfolio-news + x-trends',ST),('מניות/מדדים — GROK portfolio-news-scan',[r for r in gp if r.get('ttype')!='קריפטו']),('מניות/מדדים — GROK x-trends-digest',[r for r in gx if r.get('ttype')!='קריפטו'])]
    TYP+=[('Elliott/Fibonacci — Perplexity v2.7',PG['p27']),('Elliott/Fibonacci — Perplexity v2.5',PG['p25']),('ערך/תפנית ליד שפל שנתי — Perplexity',PG['pval']),('מומנטום — Perplexity',PG['pmom']),('קריפטו — Perplexity',PG['pcry'])]
    TS=[(g,st(rs)) for g,rs in TYP]
    def stN(rs,N):
        w=[r for r in rs if r['ndays']>=N and r['outcome'] not in ('מחיר לא תואם','לא הופעל') and r['cum']]
        def oc(r):
            sh=r['stop_hit']; t1=r['tp_hit'][0]; idx=None
            return r['outcome']
        return dict(n=len(w),avg=(float(np.mean([r['cum'][N-1] for r in w])) if w else None),win=(sum(r['cum'][N-1]>0 for r in w)/len(w) if w else None),
                    tp1=sum(r['outcome']=='TP1' for r in w),stop=sum(r['outcome']=='סטופ' for r in w),mfe=(float(np.mean([r['mfe'] for r in w])) if w else None))
    H2H=[]
    for bd,gd,lab in [('2026-09-07','2026-09-07','7.9 מול 7.9 (אותו תאריך, יום 1 = 08.09)'),('2026-09-24','2026-09-25','בוט 24.9 מול Grok 25.9 (יום 1: 24.09 / 25.09)'),('2026-09-27','2026-09-28','בוט 27.9 מול Grok 28.9 (יום 1 = 28.09 לשניהם)')]:
        b=[r for r in bot if r['alert_date']==bd]; g_=[r for r in gk if r['alert_date']==gd]
        N=min([r['ndays'] for r in b+g_ if r['ndays']>0] or [0])
        if N==0: continue
        H2H.append((lab,N,stN(b,N),stN(g_,N),{c:stN([r for r in g_ if r['cat']==c],N) for c in ['near-low','prebreakout','momentum']},
                    sorted({r['ticker'] for r in b}&{r['ticker'] for r in g_})))
    BT={r['ticker'] for r in bot}
    OVL=sorted({(r['ticker']) for r in gk if r['ticker'] in BT})
    
    # Perplexity vs bot / Grok on the same day-1
    H2P=[]
    for pd_,pk,bd,lab in [('2026-09-07','p27','2026-09-07','Perplexity v2.7 (Computer) 7.9 מול בוט 7.9 (יום 1 = 08.09)'),('2026-09-06','p25','2026-09-07','Perplexity v2.5 6.9 מול בוט 7.9 (יום 1 = 08.09)'),
                          ('2026-09-27','p27','2026-09-27','Perplexity v2.7 27.9 מול בוט 27.9 (יום 1 = 28.09)'),('2026-10-04','p27','2026-10-04','Perplexity v2.7 4.10 מול בוט 4.10 (יום 1 = 05.10)')]:
        p_=[r for r in PG[pk] if r['alert_date']==pd_ and r['outcome'] not in ('לא הופעל',)]; b=[r for r in bot if r['alert_date']==bd]
        N=min([r['ndays'] for r in b+p_ if r['ndays']>0] or [0])
        if N==0: continue
        H2P.append((lab,N,stN(b,N),stN(p_,N),sorted({r['ticker'] for r in b}&{r['ticker'] for r in p_})))
    for pd_,gd,lab in [('2026-09-13','2026-09-14','Perplexity v2.7 13.9 מול Grok 14.9 (יום 1 = 14.09)'),('2026-09-20','2026-09-21','Perplexity v2.7 20.9 מול Grok 21.9 (יום 1 = 21.09)'),('2026-09-27','2026-09-28','Perplexity v2.7 27.9 מול Grok 28.9 (יום 1 = 28.09)')]:
        p_=[r for r in PG['p27'] if r['alert_date']==pd_ and r['outcome']!='לא הופעל']; g_=[r for r in gk if r['alert_date']==gd]
        N=min([r['ndays'] for r in g_+p_ if r['ndays']>0] or [0])
        if N==0: continue
        H2P.append((lab.replace('בוט','Grok'),N,stN(g_,N),stN(p_,N),sorted({r['ticker'] for r in g_}&{r['ticker'] for r in p_})))
    return dict(S=S,SS=SS,TS=TS,H2H=H2H,OVL=OVL,gk=gk,bot=bot,orig=orig,il=il,gc=gc,gp=gp,gx=gx,PG=PG,PALL=PALL,H2P=H2P)
AFTER=compute(rows_counted); BEFORE=compute(rows_all)
S,SS,TS,H2H,OVL=AFTER['S'],AFTER['SS'],AFTER['TS'],AFTER['H2H'],AFTER['OVL']
rows=rows_all; rows_full=rows_full
AU=[r for r in rows_full if r['source'] in ('gcrypto','gpns','gxtd')]
gk=[r for r in rows_all if r['source']=='grok']   # all Grok rows (incl. uncounted duplicates) for notes / gaps tab
# conflict vs non-conflict (counted scanner rows: bot + Grok + original sheet; charts excluded)
conf_ids={id(p['a']) for p in PAIRS}|{id(p['b']) for p in PAIRS}
scan=[r for r in rows_counted if r['source'] in ('bot','grok','orig','gcrypto','gpns','gxtd')+PPS]
CONF=[('כל הסורקים — בסתירת כיוון',[r for r in scan if id(r) in conf_ids]),('כל הסורקים — בלי סתירה',[r for r in scan if id(r) not in conf_ids]),
      ('GROK — בסתירת כיוון',[r for r in scan if r['source']=='grok' and id(r) in conf_ids]),('GROK — בלי סתירה',[r for r in scan if r['source']=='grok' and id(r) not in conf_ids]),
      ('קריפטו — בסתירת כיוון',[r for r in scan if r.get('ttype')=='קריפטו' and id(r) in conf_ids]),('קריפטו — בלי סתירה',[r for r in scan if r.get('ttype')=='קריפטו' and id(r) not in conf_ids]),
      ('Perplexity — בסתירת כיוון',[r for r in scan if r['source'] in PPS and id(r) in conf_ids]),('Perplexity — בלי סתירה',[r for r in scan if r['source'] in PPS and id(r) not in conf_ids]),
      ('בוט v2.8 — בסתירת כיוון',[r for r in scan if r['source']=='bot' and id(r) in conf_ids]),('בוט v2.8 — בלי סתירה',[r for r in scan if r['source']=='bot' and id(r) not in conf_ids])]
CONFS=[(g,st(x)) for g,x in CONF]
# before/after dedupe
BA_KEYS=['בוט v2.8 — סה"כ','GROK automation — סה"כ','GROK crypto — סה"כ','GROK portfolio-news-scan — סה"כ','GROK x-trends-digest — סה"כ']
def _d(L): return dict(L)
BA=[]
for g in BA_KEYS: BA.append((g,_d(BEFORE['SS'])[g],_d(AFTER['SS'])[g]))
for g in ['GROK automation — LONG','GROK automation — SHORT']: BA.append((g,_d(BEFORE['S'])[g],_d(AFTER['S'])[g]))
for g,_ in TS:
    if 'GROK' in g and 'גיליון' not in g: BA.append((g,_d(BEFORE['TS'])[g],_d(AFTER['TS'])[g]))
REP_T=len(GROUPS)
NPAIRS=len(PAIRS)
