"""Parse other Grok automations (crypto / portfolio-news-scan / x-trends-digest / daily-stock-tracker) into setup rows. Added 04.10.2026."""
import re, glob, os, json
BASE='/workspace/grok-outputs'
AUTOS={'crypto':'GROK crypto','portfolio-news-scan':'GROK portfolio-news-scan','x-trends-digest':'GROK x-trends-digest','daily-stock-tracker':'GROK daily-stock-tracker'}
# run time (UTC hour, minute) from the Grok automation schedule page (IDT = UTC+3)
RUNUTC={'crypto':(8,30),'portfolio-news-scan':(13,30),'x-trends-digest':(9,0),'daily-stock-tracker':(11,0)}
CRYPTO={'BTC','ETH','SOL','XRP','DOGE','ADA','AVAX','BNB','LINK','HYPE','ZEC','UNI','SUI','NEAR','LTC','BCH','XMR','DOT','TRX','ATOM','AAVE','ONDO','LDO','ENA','PEPE','SHIB','BONK','WIF','KAITO','PUMP','DEXE','SNX','CRV','DASH','EOS','THETA','INJ','TAO','ARB','FET','FIL','APT','ALGO','ETHFI','QNT','TRUMP','RAY','KAS','CRO','TUT','CYS','BEAT','AKE','APR','VELVET','TNSR','PIPPIN','CAP','VVV','TIBBIR','HFT','BOBO','DCR','BANK','HNT','PONS','PROM','LSK','FLOCK','BR','BLORB','BP','DEGEN','BOME','COTI','COW','DYM','EUL','FARTCOIN','GEOD','GPS','H','ILV','LIT','ON','POWR','SKUU','SKYAI','SPX','STRK','U','WMTX','ZHIPU','ZRO','ACE','AKT','BICO','CASHCAT','HEIMA','MEMECORE','PI','DOGE','SOL','XRP','ETH','BTC'}
NM={'ביטקוין':'BTC','אתריום':'ETH',"את'ריום":'ETH','סולנה':'SOL','סולאנה':'SOL','ריפל':'XRP','HEIMA':'HEIMA','MemeCore':'M'}
def clean(s):
    return (s or '').replace('\u200e','').replace('\u200f','').replace('‑','-').replace('–','-').replace('−','-').replace('—','-').replace('≈','~').strip()
NUMRE=r'(\d[\d,]*(?:\.\d+)?)(?:\s?([kK])(?![a-zA-Z]))?'
def tokens(s):
    """yield numeric tokens: dict(v, pct, sign, rng, txt, kk) ; skips numbers glued to letters (20EMA, 50DMA, 200W, TP1)"""
    s=clean(s); out=[]
    for m in re.finditer(r'(?<![A-Za-z\d.])([+\-±]?)\s?[~$<>]*\$?'+NUMRE+r'(-~?\$?\d[\d,]*(?:\.\d+)?)?\s*(%)?',s):
        nxt=s[m.end(2):m.end(2)+1]
        if m.group(3) is None and re.match(r'[A-Za-z]',nxt): continue  # 20EMA, 50DMA
        v=float(m.group(2).replace(',','')); 
        if m.group(3): v*=1000
        out.append(dict(v=v,pct=bool(m.group(5)),sign=m.group(1),rng=bool(m.group(4)),txt=m.group(0).strip(),end=m.end(),start=m.start()))
    return out
def colidx(h,keys):
    for i,x in enumerate(h):
        if any(k in x for k in keys): return i
    return None
def table(p):
    rows=[]
    for l in open(p,encoding='utf-8'):
        l=l.rstrip('\n')
        if '\t' in l: c=[x.strip() for x in l.split('\t')]
        elif l.count('|')>5: c=[x.strip() for x in l.strip().strip('|').split('|')]
        else: continue
        if c and c[0]=='monospaced': continue
        rows.append(c)
    return rows
def scale(v,ref):
    """Grok sometimes writes 65.5 for 65.5k inside BTC rows"""
    if v is None or ref is None: return v
    if ref>1000 and v<ref/100 and 0.5<v*1000/ref<2: return v*1000
    return v
def coin_head(h):
    h=clean(h)
    m=re.search(r'\(([A-Z0-9]{1,10})\)',h)
    dm=re.search(r'(לונג|שורט|Long|Short)',h)
    if m: sym=m.group(1)
    else:
        first=re.split(r'[\s,]+',h)[0]
        sym=NM.get(first,first).upper()
    dirn=('LONG' if dm.group(1) in ('לונג','Long') else 'SHORT') if dm else None
    rest=h[dm.end():] if dm else ''
    return sym,dirn,rest
def price_from(rest):
    """first plain number after direction = Grok price; range -> None + text"""
    t=[x for x in tokens(rest.lstrip(', ')) if not x['pct'] and not x['sign']]
    if not t: return None,None
    x=t[0]
    if x['rng']: return None,x['txt']
    return x['v'],None
def parse_stop(sc,entry):
    sc=clean(sc); t=tokens(sc)
    ab=[x for x in t if not x['pct'] and not x['sign']]
    if ab and not ab[0]['rng']: return scale(ab[0]['v'],entry),None,None
    if ab and ab[0]['rng']: return None,None,f'סטופ כטווח ("{sc[:50]}")'
    pc=[x for x in t if x['pct']]
    if pc:
        if pc[0]['rng'] or re.search(r'high|שיא|low|שפל|היי|לואו|swing|ATH',sc,re.I): return None,None,f'סטופ באחוזים משיא/שפל או טווח, לא מהכניסה ("{sc[:50]}")'
        return None,pc[0]['v'],None
    return None,None,f'סטופ לא מספרי ("{sc[:50]}")'
def parse_tps(tc,entry,n=3):
    tc=clean(tc)
    if re.search(r'TP\d',tc):
        parts=[p for p in re.split(r'TP\d\s*:?',tc)[1:]]
    else:
        parts=re.split(r'\s*/\s*',tc)
    vals=[None]*3; pct=[None]*3; gaps=[]
    for i,p in enumerate(parts[:3]):
        t=tokens(p)
        if not t: gaps.append(f'TP{i+1} לא מספרי'); continue
        ab=[x for x in t if not x['pct'] and not x['sign']]
        pc=[x for x in t if x['pct']]
        if ab and not ab[0]['rng']: vals[i]=scale(ab[0]['v'],entry)  # explicit level (e.g. "(66k)") wins
        elif pc and not pc[0]['rng']: pct[i]=pc[0]['v']
        else: gaps.append(f'TP{i+1} כטווח ("{p.strip()[:30]}")')
    return vals,pct,gaps
def parse_crypto():
    out=[]; skipped=[]
    for p in sorted(glob.glob(f'{BASE}/crypto/*.md')):
        fn=os.path.basename(p); date=re.search(r'(\d{4}-\d{2}-\d{2})',fn).group(1)
        run=re.search(r'\d{4}-\d{2}-\d{2}-(\d)\.md',fn); run=int(run.group(1)) if run else 1
        R=table(p); h=R[0]
        if fn=='grok-crypto-2026-07-17-2.md':
            later={tuple(c) for c in table(f'{BASE}/crypto/grok-crypto-2026-09-25.md')}
        else: later=set()
        I=dict(trig=colidx(h,['טריגר']),sl=colidx(h,['סטופ']),tp=colidx(h,['יעדי','יעד']),score=colidx(h,['ציון']),hold=colidx(h,['סוג העסקה']))
        for rank,c in enumerate(R[1:],1):
            if tuple(c) in later:
                skipped.append(dict(file=fn,rank=rank,head=clean(c[0])[:40],why='השורה זהה מילה במילה לשורה בקובץ grok-crypto-2026-09-25.md (מחירי סוף ספטמבר, למשל BTC 84,100) — הודבקה בטעות לקובץ של 17.7, לא נוספה'))
                continue
            if len(c)!=len(h):
                skipped.append(dict(file=fn,rank=rank,head=clean(c[0])[:40],why=f'שורה לא מיושרת לכותרת ({len(c)} עמודות מול {len(h)}); התוכן זהה לשורה בקובץ grok-crypto-2026-09-25.md — לא נוסף (כנראה הודבק בטעות לקובץ של 17.7)'))
                continue
            sym,dirn,rest=coin_head(c[0])
            entry,rng=price_from(rest)
            g=[]
            if rng: g.append(f'מחיר כטווח ({rng.replace("-","–").replace("~","")})')
            elif entry is None: g.append('אין מחיר בטבלה')
            sl,slp,sg=parse_stop(c[I['sl']],entry)
            if sg: g.append(sg)
            tps,tpp,tg=parse_tps(c[I['tp']],entry); g+=tg
            try: score=int(re.findall(r'\d+',c[I['score']])[0])
            except Exception: score=None
            trig=c[I['trig']] if I['trig'] is not None else ''
            hm=re.search(r'(\d+)\s*-\s*(\d+)\s*(ימים|יום|י[׳\']?|d|שבועות)',clean(trig)+' '+(clean(c[I['hold']]) if I['hold'] is not None else ''))
            hold=f"{hm.group(1)}-{hm.group(2)} {'שבועות' if hm.group(3)=='שבועות' else 'ימים'}" if hm else None
            out.append(dict(auto='crypto',date=date,run=run,rank=rank,sym=sym,dir=dirn,entry=entry,sl=sl,sl_pct=slp,tps=tps,tp_pct=tpp,score=score,trig_txt=clean(trig),hold=hold,
                            head=clean(c[0]),sl_cell=clean(c[I['sl']]),tp_cell=clean(c[I['tp']]),file=fn,gaps=g,asset='crypto'))
    return out,skipped
CRY_STOCKLIKE={'BTC','ETH','SOL','XRP','DOGE'}
def parse_table_auto(auto):
    out=[]; nosetup=[]
    for p in sorted(glob.glob(f'{BASE}/{auto}/*.md')):
        fn=os.path.basename(p); date=re.search(r'(\d{4}-\d{2}-\d{2})',fn).group(1)
        R=table(p)
        if not R: nosetup.append((fn,'לא פלט ריצה (צילום ממשק Grok / "Loading conversation")')); continue
        h=R[0]
        I=dict(t=colidx(h,['טיקר','נכס','סימול']),d=colidx(h,['כיוון']),trig=colidx(h,['טריגר']),sl=colidx(h,['סטופ']),tp=colidx(h,['יעד']),score=colidx(h,['ציון','סקור']),risk=colidx(h,['סיכון/יעד']))
        if I['sl'] is None and I['risk'] is None:
            nosetup.append((fn,'אין עמודות סטופ/יעד — רק כיוון וציון')); continue
        for rank,c in enumerate(R[1:],1):
            t=clean(c[I['t']]).upper(); d=clean(c[I['d']])
            dirn='LONG' if re.search(r'לונג|Long',d,re.I) else 'SHORT' if re.search(r'שורט|Short',d,re.I) else None
            g=[]; trig=clean(c[I['trig']]) if I['trig'] is not None else ''
            tt=[x for x in tokens(trig) if not x['pct']]
            entry=tt[0]['v'] if tt and not tt[0]['rng'] else None
            if entry is None: g.append('אין מחיר כניסה מספרי (טריגר: "'+trig[:40]+'")' if trig else 'אין מחיר כניסה בטבלה')
            if I['risk'] is not None:   # "SL 78k / TP 92k"
                cell=clean(c[I['risk']]); ms=re.search(r'SL\s*([\d.,]+\s*[kK]?)',cell); mt=re.search(r'TP\s*([\d.,]+\s*[kK]?)',cell)
                sl=tokens(ms.group(1))[0]['v'] if ms else None; tp1=tokens(mt.group(1))[0]['v'] if mt else None; slp=None; tpp=None; slc,tpc=cell,cell
            elif I['tp'] is not None and I['tp']==I['sl']:
                sl=tp1=slp=tpp=None
            else:
                slc=clean(c[I['sl']]); tpc=clean(c[I['tp']])
                if '/' in tpc and 'סטופ' in h[I['tp']]:   # "יעד/סטופ" column
                    a,b=tpc.split('/')[:2]; tpc,slc=a,b
                sl,slp,sg=parse_stop(slc,entry)
                if sg: g.append(sg)
                tv,tp_p,tg=parse_tps(tpc,entry); tp1=tv[0]; tpp=tp_p[0]; g+=[x for x in tg if x.startswith('TP1')]
            if I['tp'] is not None and 'סטופ' in h[I['tp']] and (I['sl'] is None or I['sl']==I['tp']):
                tpc0=clean(c[I['tp']]); a,b=(tpc0.split('/')+[''])[:2]
                tv,tp_p,tg=parse_tps(a,entry); tp1=tv[0]; tpp=tp_p[0]
                sl,slp,sg=parse_stop(b,entry); slc,tpc=b,a
                if sg: g.append(sg)
            if sl is not None and entry is not None: sl=scale(sl,entry)
            if tp1 is not None and entry is not None: tp1=scale(tp1,entry)
            try: score=int(re.findall(r'\d+',c[I['score']])[0])
            except Exception: score=None
            g.append('יעד יחיד בטבלה (TP2/TP3 לא קיימים במקור)')
            out.append(dict(auto=auto,date=date,run=1,rank=rank,sym=t,dir=dirn,entry=entry,sl=sl,sl_pct=slp,tps=[tp1,None,None],tp_pct=[tpp,None,None],score=score,trig_txt=trig,hold=None,
                            head=f"{t} {d} · טריגר: {trig}",sl_cell=slc,tp_cell=tpc,file=fn,gaps=g,asset=('crypto' if t in CRY_STOCKLIKE else 'stock')))
    return out,nosetup
def parse_all():
    cr,sk=parse_crypto()
    res=dict(rows=cr,skipped=sk,nosetup={})
    for a in ('portfolio-news-scan','x-trends-digest','daily-stock-tracker'):
        o,ns=parse_table_auto(a); res['rows']+=o; res['nosetup'][a]=ns
    return res
if __name__=='__main__':
    R=parse_all(); json.dump(R,open('auto/grok_auto_parsed.json','w'),ensure_ascii=False,indent=1)
    from collections import Counter
    print(Counter(r['auto'] for r in R['rows'])); print(len(R['skipped']),'skipped')
    for k,v in R['nosetup'].items(): print(k,len(v),Counter(x[1][:20] for x in v))
