import re, glob, os, json
CAT={'near-low':'שפל שנתי','prebreakout':'לפני פריצה','momentum':'מומנטום'}
NUM=r'\d[\d,]*(?:\.\d+)?'
def fl(x): return float(x.replace(',',''))
def nums(s): return [fl(m.group(0)) for m in re.finditer(NUM+r'(?!\s*[%xX×])',s) ]
def tok(s):
    s=re.sub(r'(\d)[–-](\d[\d.]*\s*%)',r'\1@\2',s)
    for m in re.finditer(r'(?<![\d.,A-Za-z@])([+\-−±]?)\s?(~?)(\d[\d,]*(?:\.\d+)?)(@[\d.]+)?(\s*%)?',s):
        after=s[m.end():m.end()+6]
        if re.match(r'[\u0590-\u05FF]|\s*(ימים|יום|שבוע)',after) and not m.group(5): continue
        yield dict(sign=m.group(1),pct=bool(m.group(5)),rngpct=bool(m.group(4)),v=fl(m.group(3)),txt=m.group(3),end=m.end())
def colidx(hdr,keys):
    for i,h in enumerate(hdr):
        if any(k in h for k in keys): return i
    return None
def parse():
    out=[]; gaps=[]
    for p in sorted(glob.glob('/workspace/grok-outputs/grok-*.md')):
        fn=os.path.basename(p); m=re.match(r'grok-(\d{4}-\d{2}-\d{2})-(.+)\.md',fn); date,cat=m.group(1),m.group(2)
        tl=[l for l in open(p,encoding='utf-8') if l.startswith('|')]
        hdr=[x.strip() for x in tl[0].strip().strip('|').split('|')]
        I=dict(score=colidx(hdr,['ציון']),trig=colidx(hdr,['טריגר']),sl=colidx(hdr,['סטופ']),tp=colidx(hdr,['יעדי']),rr=colidx(hdr,['R:R']))
        for rank,l in enumerate(tl[2:],1):
            c=[x.strip() for x in l.strip().strip('|').split('|')]
            g=[]
            head=c[0].replace('\u200e','')
            t=re.split(r'[\s,]+',head)[0].strip('*').upper()
            dm=re.search(r'(לונג|שורט|Long|Short)',head)
            dirn=('LONG' if dm.group(1) in ('לונג','Long') else 'SHORT') if dm else None
            if not dirn: g.append('כיוון חסר')
            rest=head[dm.end():] if dm else head
            rest_clean=rest.replace('$','').replace('\u200e','')
            entry=None; approx=bool(re.search(r'[~≈]|בקירוב|הערכה',rest))
            rng=None; toks=list(tok(rest_clean))
            pl=[t_ for t_ in toks if not t_['sign'] and not t_['pct']]
            if pl:
                f0=pl[0]; mm=re.match(r'\s*[–-]\s*~?('+NUM+r')',rest_clean[f0['end']:])
                if mm and not rest_clean[f0['end']:].startswith(' '): rng=f0['txt']+'–'+mm.group(1)
                if rng: g.append(f'מחיר כטווח ({rng}) — לא נקבע מחיר התראה')
                else: entry=f0['v']
            else: g.append('אין מחיר בטבלה')
            sgn=1 if dirn!='SHORT' else -1
            sl=None; tps=[None]*3; conv=[]; sl_pct=None; tp_pct=[None]*3
            sc=c[I['sl']]; stoks=[t_ for t_ in tok(sc) if not t_['rngpct']]
            p=[t_ for t_ in stoks if not t_['pct']]
            if p: sl=p[0]['v']
            else:
                q=[t_ for t_ in stoks if t_['pct']]
                if q and not re.search(r'לואו|שפל|היי',sc): sl_pct=q[0]['v']
                if q and entry is not None and not re.search(r'לואו|שפל|היי',sc): sl=round(entry*(1-sgn*q[0]['v']/100),4); conv.append('סטופ')
            if sl is None: g.append(f'סטופ לא מספרי / לא ניתן להמרה ("{sc[:40]}")')
            tc=c[I['tp']]; parts=[re.sub(r'TP\d\s*=?','',x_) for x_ in tc.split('/')]
            vals=[]; pc=False
            for part in parts[:3]:
                tt=[t_ for t_ in tok(part) if not t_['rngpct']]
                if 'SMA' in part or not tt: vals.append(None); continue
                t0=tt[0]
                if t0['pct']:
                    tp_pct[len(vals)]=t0['v']
                    vals.append(round(entry*(1+sgn*t0['v']/100),4) if entry is not None else None); pc=True
                else:
                    v=t0['v']; fib=(entry is None and v in (0.382,0.5,0.618,0.786,1.272,1.618) and '$' not in part)
                    vals.append(None if fib else (v if (entry is None or abs(v/entry-1)<0.8) else None))
            if pc and entry is not None: conv.append('יעדים')
            tps=vals+[None]*(3-len(vals))
            nt=sum(v is not None for v in tps)
            if nt<3: g.append(f'רק {nt} יעדים מספריים ("{tc[:50]}")')
            if conv: g.append('CONV:'+' ו'.join(conv)+f' הוגדרו באחוזים ("{sc[:30]}" / "{tc[:45]}") והומרו למחיר ביחס למחיר ההתראה')
            try: score=int(re.findall(r'\d+',c[I['score']])[0])
            except Exception: score=None
            trig_txt=c[I['trig']] if I['trig'] is not None else ''
            hm=re.search(r'(\d+)\s*[–-]\s*(\d+)\s*(ימים|שבועות|שבו|ש[׳\']|י[׳\']?)',trig_txt)
            hold=f"{hm.group(1)}-{hm.group(2)} {'ימים' if hm.group(3).startswith('י') else 'שבועות'}" if hm else None
            out.append(dict(date=date,cat=cat,ttype=CAT[cat],rank=rank,ticker=t,dir=dirn,entry=entry,approx=approx,head=head,sl=sl,tps=tuple(tps),score=score,
                            trig_txt=trig_txt,hold=hold,sl_pct=sl_pct,tp_pct=tuple(tp_pct),sl_cell=sc,tp_cell=tc,rr=(c[I['rr']] if I['rr'] is not None and I['rr']<len(c) else ''),file=fn,gaps=g))
            if g: gaps.append((fn,rank,t,g))
    return out,gaps
if __name__=='__main__':
    o,g=parse(); json.dump(o,open('grok_rows.json','w'),ensure_ascii=False,indent=1)
    from collections import Counter; print(len(o),Counter(x['cat'] for x in o))
    for x in g: print(x)
    for x in o:
        if x['file'].endswith('momentum.md') and x['rank']<3: print(x['ticker'],x['dir'],x['entry'],x['sl'],x['tps'],x['hold'],x['score'])
