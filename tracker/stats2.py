import pandas as pd, numpy as np
rows_full=pd.read_pickle('rows_all.pkl'); rows=[r for r in rows_full if not r['excluded']]; excl=[r for r in rows_full if r['excluded']]
def st(rs):
    w=[r for r in rs if r['ndays']>0 and r['cum'] and r['outcome']!='מחיר לא תואם']
    tp=sum(r['outcome']=='TP1' for r in w); sl=sum(r['outcome']=='סטופ' for r in w); op=sum(r['outcome']=='פתוח' for r in w)
    avg=lambda xs: float(np.mean(xs)) if xs else None
    return dict(n=len(rs),n_data=len(w),days=max([r['ndays'] for r in rs]+[0]),tp1=tp,stop=sl,open=op,
        hit=(tp/(tp+sl) if tp+sl else None), tp1_all=(tp/len(w) if w and any(r['sl'] or r['tps'][0] for r in w) else None),
        tp2=sum(r['tp_hit'][1] is not None and (r['stop_hit'] is None or r['tp_hit'][1]<=r['stop_hit']) for r in w),
        avg_ret=avg([r['cum'][-1] for r in w]), win_mtm=(sum(r['cum'][-1]>0 for r in w)/len(w) if w else None),
        avg_rule=avg([r['rule'] for r in w if r['rule'] is not None]),
        mfe=avg([r['mfe'] for r in w]), mae=avg([r['mae'] for r in w]),
        d5=avg([r['cum'][4] for r in w if len(r['cum'])>=5]), d10=avg([r['cum'][9] for r in w if len(r['cum'])>=10]), d20=avg([r['cum'][19] for r in w if len(r['cum'])>=20]),
        trig=sum(r['trig_dt'] is not None for r in w))
bot=[r for r in rows if r['source']=='bot']; orig=[r for r in rows if r['source']=='orig']; il=[r for r in rows if r['source']=='ilan']
G=[]
for k in ['2026-09-07','2026-09-24','2026-09-27','2026-09-30']: G.append((f"בוט — סריקה {k[8:10]}.{k[5:7]}",[r for r in bot if r['alert_date']==k]))
G+=[('בוט — סה"כ',bot),('בוט — LONG',[r for r in bot if r['dir']=='LONG']),('בוט — SHORT',[r for r in bot if r['dir']=='SHORT']),
    ('גיליון מקורי (יולי–אוג׳) — סה"כ',orig),('גיליון מקורי — GROK LONG',[r for r in orig if r['model']=='GROK' and r['dir']=='LONG']),
    ('גיליון מקורי — GROK SHORT',[r for r in orig if r['model']=='GROK' and r['dir']=='SHORT']),('גיליון מקורי — Perplexity',[r for r in orig if r['model']=='Perplexity']),
    ('גרפים של אילן (מבט לונג)',il)]
gk=[r for r in rows if r['source']=='grok']
G+=[('GROK automation — סה"כ',gk),('GROK automation — LONG',[r for r in gk if r['dir']=='LONG']),('GROK automation — SHORT',[r for r in gk if r['dir']=='SHORT'])]
for k in sorted({r['alert_date'] for r in gk}): G.append((f"GROK — ריצה {k[8:10]}.{k[5:7]}",[r for r in gk if r['alert_date']==k]))
S=[(g,st(rs)) for g,rs in G]
# by source
SRC=[('בוט v2.8 — סה"כ',bot),('GROK automation — סה"כ',gk),('גיליון מקורי (יולי–אוג׳) — סה"כ',orig),('גרפים של אילן (מבט לונג)',il)]
SS=[(g,st(rs)) for g,rs in SRC]
TYP=[('Elliott v2.8 (בוט)',bot)]
for t in ['שפל שנתי','לפני פריצה','מומנטום']:
    x=[r for r in gk if r['ttype']==t]
    TYP+=[(f'{t} — GROK automation',x),(f'{t} — GROK LONG',[r for r in x if r['dir']=='LONG']),(f'{t} — GROK SHORT',[r for r in x if r['dir']=='SHORT'])]
TYP+=[('שפל שנתי — גיליון מקורי',orig),('שפל שנתי — סה"כ (GROK automation + גיליון)',[r for r in gk if r['ttype']=='שפל שנתי']+orig)]
TS=[(g,st(rs)) for g,rs in TYP]
def stN(rs,N):
    w=[r for r in rs if r['ndays']>=N and r['outcome']!='מחיר לא תואם' and r['cum']]
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
if __name__=='__main__':
    for x in H2H: print(x)
    print('OVL',OVL)
    for g,s in S+TS: print(g,{k:(round(v,4) if isinstance(v,float) else v) for k,v in s.items()})
    for r in il: print(r['ticker'],round(r['cum'][-1]*100,2),round(r['mfe']*100,1),round(r['mae']*100,1), r['opt'][0].date(),r['opt'][1].date(),round(r['opt'][5]*100,1))
