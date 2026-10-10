import pandas as pd, numpy as np
rows=pd.read_pickle('rows.pkl')
def st(rs):
    w=[r for r in rs if r['ndays']>0]
    tp=sum(r['outcome']=='TP1' for r in w); sl=sum(r['outcome']=='סטופ' for r in w); op=sum(r['outcome']=='פתוח' for r in w)
    amb=sum(r['outcome'].startswith('עמום') for r in w)
    avg=lambda xs: float(np.mean(xs)) if xs else None
    return dict(n=len(rs),n_data=len(w),days=max([r['ndays'] for r in rs]) if rs else 0,tp1=tp,stop=sl,open=op,amb=amb,
        hit=(tp/(tp+sl) if tp+sl else None), tp1_all=(tp/len(w) if w else None),
        tp2=sum(r['tp_hit'][1] is not None and (r['stop_hit'] is None or r['tp_hit'][1]<=r['stop_hit']) for r in w),
        avg_ret=avg([r['cum'][-1] for r in w]), avg_rule=avg([r['rule'] for r in w]),
        win_mtm=(sum(r['cum'][-1]>0 for r in w)/len(w) if w else None),
        mfe=avg([r['mfe'] for r in w]), mae=avg([r['mae'] for r in w]), trig=sum(r['trig_dt'] is not None for r in w))
groups=[(f"סריקה {k[8:10]}.{k[5:7]}", [r for r in rows if r['scan']==k]) for k in ['2026-09-07','2026-09-24','2026-09-27','2026-09-30']]
groups+= [('סה"כ', rows), ('LONG (כל הסריקות)', [r for r in rows if r['dir']=='LONG']), ('SHORT (כל הסריקות)', [r for r in rows if r['dir']=='SHORT'])]
S=[(g,st(rs)) for g,rs in groups]
if __name__=='__main__':
    for g,s in S: print(g, {k:(round(v,4) if isinstance(v,float) else v) for k,v in s.items()})
    w=[r for r in rows if r['ndays']>0]
    w.sort(key=lambda r:r['cum'][-1])
    for r in w[:5]+w[-5:]: print(r['scan'],r['ticker'],r['dir'],round(r['cum'][-1]*100,2),r['outcome'],r['score'])
    # score vs outcome for 7.9
    for r in rows:
        if r['scan']=='2026-09-07': print(r['ticker'],r['score'],r['outcome'],round(r['cum'][-1]*100,2),round(r['sl']/r['entry']*100-100,2), r['trig_dt'])
    # 7.9 L vs S
    import collections
