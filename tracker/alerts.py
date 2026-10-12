"""Unified alert list. To add rows: append to ilan_charts.json (TradingView charts) or SCANS in setups.py, then run: fetch_all.py -> engine.py -> build.py -> report.py"""
import json, openpyxl, datetime as dt
from setups import SCANS
def bot_alerts():
    out=[]
    for k,v in SCANS.items():
        for rank,s in enumerate(v['setups'],1):
            t,dirn,entry,sl,tsl,tps,score,hold,trig,trig_txt=s
            out.append(dict(source='bot',model='Chief of Staff bot (v2.8)',alert_date=k,group=f"סריקת בוט {k[8:10]}.{k[5:7]}",ttype='Elliott/Fibonacci swing (v2.8)',ticker=t,dir=dirn,entry=entry,sl=sl,
              tsl=tsl/100 if tsl is not None else None,tps=tps,hold=hold,score=score,rank=rank,trig=trig,trig_txt=trig_txt,calc_date=v.get('day1') if k in ('2026-10-04','2026-10-07','2026-10-12') else None,
              pre=[f"#{rank} בסריקה, ציון {score}. טריגר בסריקה: {trig_txt}." if score is not None else f"#{rank} בסריקת בוט v2.8 מ-{k[8:10]}.{k[5:7]} (נתונים מסגירת {v['price_date'][8:10]}.{v['price_date'][5:7]}); כניסה/סטופ/יעדים לפי הסריקה, המחיר אומת מול scan_deep_2026-10-04.json. ציון/החזקה/טריגר לא נמסרו — הושארו ריקים."]))
    return out
def orig_alerts(path='orig_readonly.xlsx'):
    ws=openpyxl.load_workbook(path).worksheets[0]; out=[]
    for r in range(4,ws.max_row+1):
        g=lambda c: ws.cell(r,c).value
        model,date,t=g(46),g(45),g(42)
        if not t: continue
        h=g(25); hold=f"{h.day}-{h.month}" if isinstance(h,dt.datetime) else (str(int(h)) if isinstance(h,(int,float)) else h)
        tps=tuple(g(c) for c in (31,30,29))
        out.append(dict(source='orig',model=model,alert_date=date.strftime('%Y-%m-%d') if date else None,group=f"גיליון מקורי ({model})",ttype='שפל שנתי',ticker=t,dir=g(38),
            entry=g(37),sl=g(34),tsl=g(32),tps=tps if any(tps) else (None,None,None),hold=hold,orig_row=r,orig_mcap=g(40),orig_atr=g(39),
            pre=[f"מקור: גיליון 'מניות שפל שנתי' שורה {r} (מודל {model}); הנתונים המקוריים לא שונו, החישוב כאן מחדש ממחירי Yahoo."]+([f"הופעות נוספות לפי הגיליון המקורי: {g(41)}."] if g(41) else [])))
    return out
def ilan_alerts(path='ilan_charts.json', sources=None):
    sources=sources or (bot_alerts()+orig_alerts()); out=[]
    for c in json.load(open(path)):
        d=c.get('dir') or 'LONG'
        cap=c['alert_date']  # capture date of the chart (NOT assumed to be the scan date)
        m=[x for x in sources if x['ticker']==c['ticker'] and x['alert_date'] and x['alert_date']<=cap]
        m.sort(key=lambda x:x['alert_date'])
        src=m[-1] if m else None
        pre=[f"גרף TradingView ששלח אילן ({c['ticker']}, {c.get('timeframe','')}, צולם {c['capture']}): {c.get('chart_note','')}"]
        if src:
            pre.append(f"תאריך הסריקה נלקח מהמקור התואם: {src['group']} — {src['alert_date'][8:10]}.{src['alert_date'][5:7]}.{src['alert_date'][:4]} ({src['dir']}, מחיר התראה {src['entry']})"+(f", שורה {src['orig_row']} בגיליון המקורי" if src.get('orig_row') else "")+". הבקטסט של הסריקה עצמה מופיע בשורה של המקור.")
        else:
            pre.append("לא נמצאה סריקה תואמת במקורות (בוט / גיליון מקורי) — תאריך הסריקה: חסר תאריך.")
        pre.append(f"ימים 1–20 כאן מחושבים ממועד צילום הגרף ({cap[8:10]}.{cap[5:7]}) וממחיר הגרף {c['entry']}, לא ממועד הסריקה.")
        if c.get('dir') is None: pre.append("כיוון לא צוין בגרף — מחושב כלונג"+(f" (במקור התואם הכיוון היה {src['dir']})" if src else "")+"; מבט שורט מופיע בהמשך.")
        out.append(dict(source='ilan',model='Ilan charts (TradingView)',alert_date=src['alert_date'] if src else None,calc_date=cap,
            ttype=(src.get('ttype') if src and src['source']=='orig' else (c.get('ttype') or '')),matched=src['group'] if src else None,
            group='גרפים של אילן (TradingView)',ticker=c['ticker'],dir=d,dir_assumed=c.get('dir') is None,entry=c['entry'],sl=c.get('sl'),tsl=c.get('tsl'),
            tps=tuple(c.get('tps') or (None,None,None)),hold=c.get('hold'),mcap_override=c.get('mcap_chart'),atr_override=c.get('atr_chart_pct'),pre=pre))
    return out
def grok_alerts():
    import re
    from grok_parse import parse, NUM
    CATN={'near-low':'near-low','prebreakout':'prebreakout','momentum':'momentum'}
    o,_=parse(); out=[]
    for x in o:
        pre=[f"מקור: Grok automation, {x['file']} (קטגוריה {x['cat']}), מקום #{x['rank']}, ציון {x['score']}. כותרת: \"{x['head']}\". טריגר: {x['trig_txt'][:160]}. R:R: {x['rr'][:60]}."]
        sl,tps,entry=x['sl'],list(x['tps']),x['entry']
        conv=[g[5:] for g in x['gaps'] if g.startswith('CONV:')]
        if conv: pre.append(conv[0]+'.')
        gaps=[g for g in x['gaps'] if not g.startswith('CONV:')]
        if gaps: pre.append("פערי פענוח: "+'; '.join(gaps)+". לא הוזן מחיר/סטופ/יעד שלא הופיע בטבלה.")
        if x['approx']: pre.append("המחיר בטבלה מסומן כמשוער (~/≈).")
        tn=re.findall(r'\d+\.\d+|\d{2,}',x['trig_txt'].split(';')[0])
        trig=float(tn[0]) if tn and entry and abs(float(tn[0])/entry-1)<0.5 else None
        out.append(dict(source='grok',model='GROK automation',alert_date=x['date'],group=f"GROK {x['cat']}",ttype=x['ttype'],ticker=x['ticker'],dir=x['dir'] or 'LONG',
            entry=entry,sl=sl,tsl=None,tps=tuple(tps),hold=x['hold'],score=x['score'],rank=x['rank'],cat=x['cat'],trig=trig,trig_txt=x['trig_txt'],pre=pre,parse_gaps=gaps,sl_pct=x['sl_pct'],tp_pct=x['tp_pct'],sl_cell=x['sl_cell'],tp_cell=x['tp_cell'],grok_entry=entry))
    return out
def all_alerts(): return bot_alerts()+orig_alerts()+ilan_alerts()+grok_alerts()
AUTO_SRC={'crypto':'gcrypto','portfolio-news-scan':'gpns','x-trends-digest':'gxtd'}
# rows in grok-crypto-2026-07-17-2.md that are verbatim copies of 25.09 rows (pasted by mistake) — not added
CONTAM={('grok-crypto-2026-07-17-2.md','LTC'),('grok-crypto-2026-07-17-2.md','XRP')}
def auto_alerts():
    D=json.load(open('auto/grok_auto_parsed.json')); M=json.load(open('auto/symmap.json')); UN=M.pop('_unmapped')
    out=[]
    for x in D['rows']:
        if (x['file'],x['sym']) in CONTAM: continue
        cr=x['asset']=='crypto'
        if cr: t=M.get(x['sym']) or f"{x['sym']} (קריפטו)"
        else: t=x['sym']
        pre=[f"מקור: Grok automation '{x['auto']}', קובץ {x['file']}"+(f" (ריצה {x['run']})" if x.get('run',1)>1 else '')+f", מקום #{x['rank']}"+(f", ציון {x['score']}" if x.get('score') is not None else '')+f". כותרת: \"{x['head'][:90]}\"."+(f" טריגר: {x['trig_txt'][:140]}." if x.get('trig_txt') else '')]
        if cr and x['sym'] in M: pre.append(f"סימול Yahoo: {t} (אומת לפי שם ויחס מחיר).")
        if x['gaps']: pre.append("פערי פענוח: "+'; '.join(x['gaps'])+". לא הוזן מחיר/סטופ/יעד שלא הופיע בטבלה.")
        if x['file']=='grok-x-trends-digest-2026-09-25.md': pre.append("הקובץ של 25.09 זהה מילה במילה לקובץ של 20.09 (ככל הנראה פלט חוזר) — השורות נשמרו, ומסומנות ככפולות/חזרות.")
        out.append(dict(source=AUTO_SRC[x['auto']],auto=x['auto'],model=f"GROK {x['auto']}",alert_date=x['date'],group=f"GROK {x['auto']}",
            ttype='קריפטו' if cr else 'מניות/מדדים (Grok)',ticker=t,sym=x['sym'],dir=x['dir'] or 'LONG',entry=x['entry'],sl=x['sl'],tsl=None,tps=tuple(x['tps']),
            hold=x.get('hold'),score=x.get('score'),rank=x['rank'],cat=None,trig=None,trig_txt=x.get('trig_txt'),pre=pre,parse_gaps=x['gaps'],
            sl_pct=x.get('sl_pct'),tp_pct=x.get('tp_pct'),sl_cell=x.get('sl_cell') or '',tp_cell=x.get('tp_cell') or '',grok_entry=x['entry'],file=x['file'],
            unmapped=UN.get(x['sym'],'') if cr else ''))
    return out
def all_alerts(): return bot_alerts()+orig_alerts()+ilan_alerts()+grok_alerts()+auto_alerts()
PPLX_SRC=('p27','p25','pval','pmom','pcry')
def _ct(c):
    d=c[8:10]+'.'+c[5:7]; r=c[11:].strip()
    if r[:1].isdigit():
        x=r[5:].strip().strip('()'); return (d+' '+r[:5]+' שעון ישראל'+(' = '+x if x else '')).strip()
    return (d+(', '+r.strip('()') if r else '')).strip()

def pplx_alerts():
    import sys; sys.path.insert(0,'pplx')
    from pplx_setups import parse_all
    M=json.load(open('auto/symmap.json')); UN=M.pop('_unmapped')
    rows,_=parse_all(); out=[]
    RL={'T01':'ריצה שבועית','T02':'ריצה שבועית','T03':'ריצה שבועית','T04':'ריצה שבועית','C0907':'ריצת Computer','T12':'ריצה','T05':'ריצה','T06':'ריצה','T07':'ריצה','T10':'ריצה','T09':'ריצה','T11':'ריצה'}
    for x in rows:
        cr=x['source']=='pcry'
        t=(M.get(x['ticker']) or f"{x['ticker']} (קריפטו)") if cr else x['ticker']
        sp=x.get('spec') or {}
        sl,tps,slp,tpp,refs=x['sl'],list(x['tps']),None,[None,None,None],{}
        for k,i in (('sl',None),('tp1',0),('tp2',1)):
            v=sp.get(k)
            if not v: continue
            if v[0]=='abs':
                if k=='sl': sl=v[1]
                else: tps[i]=v[1]
            elif v[0]=='pct':
                if k=='sl': slp=v[1]
                else: tpp[i]=v[1]
            else: refs[k]=v
        dd=f"{x['alert_date'][8:10]}.{x['alert_date'][5:7]}"
        pre=[f"מקור: Perplexity Tasks — {x['model']}, {RL[x['run']]} {dd} (נוצרה {_ct(x['created'])}), מקום #{x['rank']}"+(f", ציון {x['score']:g}" if x['score'] is not None else '')+f". קבצים: {x['file']} + {x['csvf']}."]
        if x.get('cur') is not None: pre.append(f"מחיר נוכחי בטבלה: {x['cur']:g}.")
        if x.get('trig_txt'): pre.append(f"טריגר/כניסה בטבלה: \"{x['trig_txt'][:150]}\".")
        if x.get('why'): pre.append("קריאת רמות: "+x['why']+".")
        if x['gaps']: pre.append("פערי פענוח: "+'; '.join(x['gaps'])+". לא הוזן מספר שלא הופיע בפלט.")
        if x['source'] in ('p27','p25') and x['entry'] is not None: pre.append("כניסה/סטופ/יעדים — המספרים מהטבלה, כמו שהם.")
        out.append(dict(source=x['source'],model=x['model'],alert_date=x['alert_date'],calc_date=x.get('calc_date'),group=f"{x['model']} {dd}",ttype=x['ttype'],
            ticker=t,sym=x['ticker'],dir=x['dir'],entry=x['entry'],sl=sl,tsl=None,tps=tuple(tps),hold=x.get('hold'),score=x['score'],rank=x['rank'],cat=None,trig=None,
            trig_txt=x.get('trig_txt'),pre=pre,parse_gaps=[],sl_pct=slp,tp_pct=tpp,sl_cell=sp and x.get('why','') or '',tp_cell='',grok_entry=x['entry'],file=x['file'],
            refs=refs,run=x['run'],cur=x.get('cur'),auto=None,run_h_utc=x.get('run_h_utc'),unmapped=UN.get(x['ticker'],'') if cr else ''))
    return out
def all_alerts(): return bot_alerts()+orig_alerts()+ilan_alerts()+grok_alerts()+auto_alerts()+pplx_alerts()
