# Repeats / conflicts / exact-duplicate analysis (added 30.09 per Ilan's request)
import pandas as pd
from collections import defaultdict
CATO={'near-low':0,'prebreakout':1,'momentum':2}
HEB={'LONG':'לונג','SHORT':'שורט',None:'?'}
SRCN={'bot':'בוט v2.8','orig':'גיליון מקורי','ilan':'גרף אילן','grok':'GROK','gcrypto':'GROK crypto','gpns':'GROK portfolio-news','gxtd':'GROK x-trends','p27':'Perplexity v2.7','p25':'Perplexity v2.5','pval':'Perplexity value','pmom':'Perplexity momentum','pcry':'Perplexity crypto'}
fd=lambda k: f"{int(k[8:10])}.{int(k[5:7])}" if k else 'ללא תאריך'
def srcl(r): return SRCN[r['source']]+(f" {r['cat']}" if r.get('cat') else '')
def day1(r):
    return pd.Timestamp(r['alert_date']) if r['alert_date'] else None
def wend(r):
    """last day of the 20-trading-day tracking window"""
    if r.get('ttype')=='קריפטו': return pd.Timestamp(r['alert_date'])+pd.Timedelta(days=19)  # crypto: calendar days
    b=pd.bdate_range(pd.Timestamp(r['alert_date']),periods=20)
    return b[-1]
def resolved_on(r):
    if r['outcome']=='TP1': return r['tp_hit'][0]
    if r['outcome']=='סטופ': return r['stop_hit']
    return None
ORANK={'TP1':2,'פתוח':1,'סטופ':0}
def winner(a,b):
    """a,b opposite direction. returns (text, side) side in LONG/SHORT/None"""
    oa,ob=a['outcome'],b['outcome']
    if oa not in ORANK or ob not in ORANK:
        ca=a['cum'][-1] if a['cum'] else None; cb=b['cum'][-1] if b['cum'] else None
        if ca is not None and cb is not None and oa not in ('טרם התחיל','אין נתונים') and ob not in ('טרם התחיל','אין נתונים'):
            bt=a if ca>=cb else b
            return (f"טרם הוכרע לפי תוצאה ({oa} / {ob}); לפי תשואה: {HEB[bt['dir']]} מוביל",None)
        return ('טרם הוכרע (אין נתונים לאחד הצדדים)',None)
    ra,rb=ORANK[oa],ORANK[ob]
    ca=a['cum'][-1] if a['cum'] else None; cb=b['cum'][-1] if b['cum'] else None
    better=(a if ca>=cb else b) if ca is not None and cb is not None else None
    if ra!=rb:
        w=a if ra>rb else b
        return (f"{HEB[w['dir']]} ({w['outcome']} מול {(b if w is a else a)['outcome']})",w['dir'])
    if oa=='פתוח':
        return (f"שניהם פתוחים; מוביל לפי תשואה: {HEB[better['dir']]}",better['dir'])
    return (f"תיקו — שניהם {oa}; לפי תשואה עד כה: {HEB[better['dir']]}",None)
def analyze(rows):
    """rows: main-tab rows in sheet order (index+2 = sheet row). Sets r['dup_skip'], r['dupnote']."""
    for i,r in enumerate(rows): r['_row']=i+2; r['dup_skip']=False; r['_notes2']=[]; r.pop('_conf',None); r.pop('_rev',None)
    byt=defaultdict(list)
    for r in rows: byt[r['ticker']].append(r)
    groups=[]; dups=[]; pairs=[]
    for t,rs in byt.items():
        if len(rs)<2: continue
        cls=set()
        sc=[r for r in rs if r['source']!='ilan']
        # (a) exact duplicates: same source, same date, same direction
        k=defaultdict(list)
        for r in sc:
            if r['alert_date']: k[(r['source'],r['alert_date'],r['dir'])].append(r)
        for key,xs in k.items():
            if len(xs)<2: continue
            cls.add('a')
            xs.sort(key=lambda r:(CATO.get(r.get('cat'),9),r.get('rank') or 0))
            lab='+'.join(x.get('cat') or (x['file'][-13:-3] if x.get('file') else x['source']) for x in xs)
            keep=xs[0]
            for j,x in enumerate(xs):
                if j==0: x['_notes2'].append(f"כפול ({lab} {fd(key[1])}) — נספר")
                else:
                    x['dup_skip']=True
                    x['_notes2'].append(f"כפול ({lab} {fd(key[1])}) — נספר בשורה {keep['_row']} ({keep.get('cat') or ''})")
            _g=lambda v: '—' if v is None else f"{v:.6g}"
            lv=lambda x: f"{x.get('cat') or x.get('file') or x['source']}: כניסה {_g(x['entry'])}, סטופ {_g(x['sl'])}, TP1 {_g(x['tps'][0] if x['tps'] else None)}"
            dups.append(dict(ticker=t,date=key[1],source=SRCN[key[0]],dir=key[2],rows=[x['_row'] for x in xs],cats=[x.get('cat') for x in xs],
                             levels=' | '.join(lv(x) for x in xs),outcomes=[x['outcome'] for x in xs],rets=[x['cum'][-1] if x['cum'] else None for x in xs],kept=keep['_row']))
        # signals = distinct (source,date,dir) — exact dups merged; ordered by date
        sig={}
        for r in sorted(sc,key=lambda r:(r['alert_date'] or '0000',CATO.get(r.get('cat'),9))):
            sig.setdefault((r['source'],r['alert_date'],r['dir']),[]).append(r)
        sl=list(sig.items())
        # (b) repeats, same direction
        for dr in ('LONG','SHORT'):
            same=[(kk,xs) for kk,xs in sl if kk[2]==dr]
            if len(same)<2: continue
            cls.add('b')
            for n,(kk,xs) in enumerate(same,1):
                for x in xs:
                    if n==1: x['_notes2'].append(f"הופעה #1 ({HEB[dr]}) מתוך {len(same)}; חוזר ב-"+', '.join(fd(k2[1]) for k2,_ in same[1:]))
                    else: x['_notes2'].append(f"חזרה #{n} ({HEB[dr]}); קודם: "+', '.join(f"{fd(k2[1])} {SRCN[k2[0]]}" for k2,_ in same[:n-1]))
        # (c) conflicts: opposite directions, same day or overlapping 20-trading-day windows
        for i1 in range(len(sl)):
            for i2 in range(i1+1,len(sl)):
                (k1,x1),(k2,x2)=sl[i1],sl[i2]
                if k1[2]==k2[2] or not k1[1] or not k2[1]: continue
                early,late=(x1,x2) if k1[1]<=k2[1] else (x2,x1)
                e,l=early[0],late[0]
                same_day=e['alert_date']==l['alert_date']
                overl=same_day or pd.Timestamp(l['alert_date'])<=wend(e)
                if not overl:
                    cls.add('d')
                    for x in late: x.setdefault('_rev',[]).append(f"{HEB[e['dir']]} {fd(e['alert_date'])} ({SRCN[e['source']]})")
                    for x in early: x.setdefault('_rev',[]).append(f"{HEB[l['dir']]} {fd(l['alert_date'])} ({SRCN[l['source']]})")
                    continue
                cls.add('c')
                ro=resolved_on(e)
                act=('אותו יום' if same_day else ('חלון חופף; המוקדם כבר הוכרע ב-'+ro.strftime('%d.%m')+' לפני ההתראה השנייה' if ro is not None and ro<pd.Timestamp(l['alert_date']) else 'חלון חופף; המוקדם עדיין פתוח/פעיל'))
                for x in x1+x2:
                    o=(x2 if x in x1 else x1)[0]
                    x.setdefault('_conf',[]).append(f"{HEB[o['dir']]} {fd(o['alert_date'])} ({srcl(o)})")
                a_=[x for x in x1 if not x['dup_skip']][0]; b_=[x for x in x2 if not x['dup_skip']][0]
                wt,ws=winner(a_,b_)
                pairs.append(dict(ticker=t,a=a_,b=b_,same_day=same_day,act=act,winner=wt,wside=ws))
        for r in sc:
            if r.get('_conf'): r['_notes2'].append(f"סתירה: {HEB[r['dir']]} {fd(r['alert_date'])} מול "+', '.join(dict.fromkeys(r['_conf'])))
            if r.get('_rev'): r['_notes2'].append(f"היפוך כיוון בלי חפיפת חלונות ({HEB[r['dir']]} {fd(r['alert_date'])} מול "+', '.join(dict.fromkeys(r['_rev']))+") — לא נספר כסתירה")
            if not r['alert_date']: r['_notes2'].append("שורה בלי תאריך בגיליון המקורי — לא נכללת בבדיקת חזרות/סתירות")
        # ilan chart rows
        for r in rs:
            if r['source']!='ilan': continue
            m=[x for x in sc if x['alert_date']==r['alert_date'] and x['source']=='orig']
            if m:
                cls.add('e'); o=m[0]
                r['_notes2'].append(f"גרף אילן לאותה התראה בגיליון ({fd(o['alert_date'])}, {HEB[o['dir']]}); הכיוון בגרף = מבט לונג משוער"+(" — לא נספר כסתירה" if o['dir']!='LONG' else ""))
                o['_notes2'].append(f"יש גם גרף אילן לאותה התראה (שורה {r['_row']}); הגרף לא נספר כחזרה")
            else:
                cls.add('e'); r['_notes2'].append("גרף אילן; הטיקר מופיע גם במקור אחר בתאריך אחר — לא נספר כחזרה")
        for r in rs:
            if not r['_notes2']: r['_notes2'].append('טיקר חוזר (ראו לשונית חזרות וסתירות)')
        groups.append(dict(ticker=t,rows=rs,cls=cls))
    for r in rows: r['dupnote']='; '.join(dict.fromkeys(r['_notes2']))
    groups.sort(key=lambda g:g['ticker'])
    return groups,dups,pairs
