"""Perplexity scan runs -> structured setups (added 07.10.2026).
Sources: /workspace/perplexity-outputs (PDF exports + CSV of each run's table). PDFs of the value/crypto/momentum runs are
truncated on the right (columns after 'technical' are cut), so levels come from the CSV export of the same table.
Level policy (Ilan: never invent numbers):
 - numeric levels in the text are used as-is; a range -> the bound nearest to entry (first one), noted.
 - '% from entry' -> sl_pct/tp_pct (computed from the entry actually used).
 - well-defined references on daily data -> computed from Yahoo at the alert date: 52wL (52-week low), sma200, mid52 ((52wH+52wL)/2).
 - qualitative ('local high', 'resistance', 'NAV discount', 'MA20 / trendline' alternatives...) -> blank.
 - stats rule: if after this either the stop or TP1 is missing, both are dropped for outcome purposes (row counts in returns only)."""
import csv, re, json
D='/workspace/perplexity-outputs/'
def num(s):
    if s is None: return None
    s=str(s).replace(',','').replace('$','')
    m=re.search(r'\d+(?:\.\d+)?',s)
    return float(m.group(0)) if m else None
def rd(f): 
    r=list(csv.reader(open(D+f,encoding='utf-8-sig'))); return r[0],r[1:]
DIR=lambda s: 'SHORT' if 'שורט' in s else ('LONG' if 'לונג' in s else None)
RUNS={
 'T01':dict(file='T01_0e9b7612_a1.pdf',csv='----------ATR-1-2-3---0-100.csv',created='2026-10-04 19:10 (12:10 ET לפי הפלט)',date='2026-10-04',day1='2026-10-05',src='p27',kind='v27'),
 'T02':dict(file='T02_566e09c4_a1.pdf',csv='----------ATR-1-2-3---0-100 (1).csv',created='2026-09-27 19:16 (12:16 EDT לפי הפלט)',date='2026-09-27',day1='2026-09-28',src='p27',kind='v27'),
 'T03':dict(file='T03_ceaa3c2b_a1.pdf',csv='----------ATR-1-2-3---0-100 (2).csv',created='2026-09-20 (שעה לא מצוינת; נתונים נכון ל-18.09 16:00 ET)',date='2026-09-20',day1='2026-09-21',src='p27',kind='v27'),
 'T04':dict(file='T04_04d44350_a1.pdf',csv='----------ATR-1-2-3---0-100 (3).csv',created='2026-09-13 19:00 (12:00 ET לפי הפלט)',date='2026-09-13',day1='2026-09-14',src='p27',kind='v27'),
 'C0907':dict(file='סריקת מניות v2.7 - 07 09 2026 (5-14 ימי מסחר).md',csv='----------123---.csv',created='2026-09-07 11:22',date='2026-09-07',day1='2026-09-08',src='p27',kind='c27'),
 'T12':dict(file='T12_8671210d_a1.pdf (+ a2 גרסה קצרה)',csv='----1-2-3--.csv',created='2026-09-06 17:49 (10:49 ET לפי הפלט)',date='2026-09-06',day1='2026-09-08',src='p25',kind='v25'),
 'T05':dict(file='T05_b098e1ac_a1.pdf',csv='TickerLongShort-SectorIndustry-PEFCFYieldDebtEquit.csv',created='2026-08-16 (שעה לא מאומתת)',date='2026-08-16',day1='2026-08-17',src='pval',kind='val'),
 'T06':dict(file='T06_c6b1ff04_a1.pdf',csv='TickerLongShort-SectorIndustry-PEFCFYieldDebtEquit (1).csv',created='2026-08-15 (שעה לא מאומתת)',date='2026-08-15',day1='2026-08-17',src='pval',kind='val'),
 'T07':dict(file='T07_ab35a4b5_a1.pdf',csv='TickerLongShort-SectorIndustry-PEFCFYieldDebtEquit (2).csv',created='2026-08-14 18:06',date='2026-08-14',day1='2026-08-17',src='pval',kind='val'),
 'T08':dict(file='T08_cc2b7701_a1.pdf',csv='TickerLongShort-SectorIndustry-PEFCFYieldDebtEquit (3).csv',created='2026-08-13 (שעה לא מאומתת)',date='2026-08-13',day1='2026-08-14',src='pval',kind='val'),
 'T10':dict(file='T10_e9e40813_a1.pdf',csv='TickerLongShort-SectorNarrativeCatalyst-Distancefr.csv',created='2026-08-12 17:50',date='2026-08-12',day1='2026-08-13',src='pmom',kind='mom'),
 'T09':dict(file='T09_4e85dda5_a1.pdf',csv='CoinLongShort-SectorNarrativeCatalyst-Distancefrom.csv',created='2026-08-13 17:36',date='2026-08-13',src='pcry',kind='cry',run_h_utc=14+36/60),
 'T11':dict(file='T11_7394424c_a1.pdf',csv='CoinLongShort-SectorNarrativeCatalyst-Distancefrom (1).csv',created='2026-08-12 17:48',date='2026-08-12',src='pcry',kind='cry',run_h_utc=14+48/60),
}
MODEL={'p27':'Perplexity v2.7','p25':'Perplexity v2.5','pval':'Perplexity value/turnaround','pmom':'Perplexity momentum','pcry':'Perplexity crypto'}
TTYPE={'p27':'Elliott/Fibonacci swing (Perplexity v2.7)','p25':'Elliott/Fibonacci swing (Perplexity v2.5)','pval':'ערך/תפנית ליד שפל שנתי (Perplexity)','pmom':'מומנטום (Perplexity)','pcry':'קריפטו'}
# manual level specs for the qualitative scans (value / momentum / crypto). keys: entry, sl, tp1, tp2 ; spec: ('abs',x) ('pct',p) ('52wL',p) ('sma200',) ('mid52',)
# 'why' = short note (Hebrew) of how each level was read.
VAL={
 ('T05',1):dict(sl=('52wL',3),tp1=('sma200',),tp2=('mid52',),why="סטופ 'מתחת לשפל 52 שבועות פחות ~3–5%' → 3%; TP1 'אזור ממוצע 200 יום' → SMA200; TP2 'אמצע טווח 52 שבועות'"),
 ('T05',2):dict(sl=('52wL',4),tp1=('mid52',),tp2=('abs',12),why="סטופ 'שפל 52 שבועות פחות ~4%'; TP1 'מרכז טווח 52 שבועות'; TP2 '12–14$' → 12"),
 ('T05',3):dict(sl=('52wL',5),tp1=('mid52',),why="סטופ 'שפל 52 שבועות פחות ~5%'; TP1 'אמצע טווח 52 שבועות'; TP2 איכותי"),
 ('T05',4):dict(sl=('abs',round(14.8*0.96,3)),tp1=('abs',20),tp2=('abs',30),why="סטופ 'שפל 52 שבועות (14.8$) פחות ~4%' → 14.208; TP1 '20–22$' → 20; TP2 '~30$'"),
 ('T05',5):dict(sl=('abs',round(52.73*0.97,3)),tp1=('abs',76),tp2=('abs',85),why="סטופ 'שפל 52 שבועות (52.73$) פחות ~3%' → 51.148; TP1 '~76$'; TP2 '85–90$' → 85"),
 ('T05',6):dict(sl=('52wL',5),why="סטופ 'תמיכת טווח 52 שבועות פחות ~5%'; יעדים איכותיים ('טווח שיאים אחרונים')"),
 ('T05',7):dict(sl=('pct',10),why="סטופ '≈10–15% מעל מחיר הכניסה' → 10%; יעדים איכותיים (דיסקאונט ל-NAV)"),
 ('T05',8):dict(sl=('pct',10),why="סטופ '≈10–12% מעל כניסה' → 10%; יעדים איכותיים (דיסקאונט ל-NAV)"),
 ('T05',9):dict(why="סטופ ויעדים איכותיים (פרמיה/NAV)"),
 ('T05',10):dict(entry=7.22,sl=('abs',8.3),why="טריגר 'שבירת שפל 7.22$' → כניסה 7.22; סטופ 'מעל 8.3$'; יעדים איכותיים (דיסקאונט ל-NAV)"),
 ('T06',1):dict(sl=('52wL',0),tp1=('abs',12),tp2=('abs',15),why="טריגר 'מעל 10–10.5' (טווח) → אין מחיר כניסה; סטופ 'מתחת לשפל 52 שבועות'; TP1 '12–13' → 12; TP2 '15–16' → 15"),
 ('T06',2):dict(sl=('52wL',0),tp1=('abs',18),tp2=('abs',22),why="סטופ 'מתחת ל-52w low'; TP1 '18–20' → 18; TP2 '22–24' → 22"),
 ('T06',3):dict(sl=('52wL',0),why="סטופ 'מתחת לשפל 52 שבועות'; יעדים איכותיים (Mid-Range לפני התיקון)"),
 ('T06',4):dict(sl=('52wL',0),why="סטופ 'מתחת לתמיכה הראשית/שפל 52 שבועות'; יעדים איכותיים (מרכז הטווח)"),
 ('T06',5):dict(sl=('52wL',0),why="סטופ 'מתחת לשפל 52 שבועות'; יעדים איכותיים (NAV)"),
 ('T06',6):dict(sl=('52wL',0),why="סטופ 'מתחת לשפל 52 שבועות'; יעדים איכותיים"),
 ('T06',7):dict(tp1=('pct',15),why="TP1 'ירידה נוספת של 15–20% מהכניסה' → 15%; סטופ איכותי (התנגדות / SMA50/200)"),
 ('T06',8):dict(why="סטופ ויעדים איכותיים"),
 ('T06',9):dict(tp1=('pct',10),why="TP1 'ירידה של 10–15% מהכניסה' → 10%; סטופ איכותי"),
 ('T06',10):dict(tp1=('pct',10),why="TP1 'ירידה של 10–15%' → 10%; סטופ איכותי"),
 ('T07',1):dict(tp1=('pct',15),tp2=('pct',30),why="TP1 '≈־15–20%' → 15%; TP2 '≈־30–40%' → 30%; סטופ איכותי ('10–12% מעל שיא מקומי' — לא ממחיר הכניסה)"),
 ('T07',2):dict(tp1=('pct',15),tp2=('pct',25),why="TP1 '≈־15%'; TP2 '≈־25–30%' → 25%; סטופ איכותי ('8–10% מעל שיא קצר-טווח')"),
 ('T07',3):dict(sl=('52wL',3),tp1=('pct',15),tp2=('pct',30),why="סטופ 'שפל 52 שבועות פחות 3–5%' → 3%; TP1 '≈+15–20%' → 15%; TP2 '≈+30%'"),
 ('T07',4):dict(sl=('52wL',4),tp1=('pct',15),tp2=('pct',30),why="סטופ '4–6% מתחת לשפל 52 שבועות' → 4%; TP1 '≈+15–20%' → 15%; TP2 '≈+30%'"),
 ('T07',5):dict(tp1=('pct',12),why="TP1 '≈+12–15%' → 12%; סטופ '3–5% מתחת לשפל שנבדק מספר פעמים' — לא שפל 52 שבועות מוגדר, הושאר ריק"),
 ('T07',6):dict(tp1=('pct',20),tp2=('pct',30),why="TP1 '≈+20%'; TP2 'מעל +30%'; סטופ '6–8% מתחת לשפל אחרון' — לא מוגדר, הושאר ריק"),
 ('T07',7):dict(sl=('52wL',5),tp1=('pct',15),tp2=('pct',30),why="סטופ '5–7% מתחת לשפל 52 שבועות' → 5%; TP1 '≈+15–20%' → 15%; TP2 '≈+30%'"),
 ('T07',8):dict(tp1=('pct',15),why="TP1 '≈+15%'; סטופ '5–7% מתחת לשפל אחרון' — לא מוגדר, הושאר ריק"),
 ('T07',9):dict(sl=('52wL',6),tp1=('pct',20),why="סטופ '6–8% מתחת לשפל 52 שבועות' → 6%; TP1 '≈+20%'"),
 ('T07',10):dict(tp1=('pct',20),why="TP1 '≈+20%'; סטופ '7–9% מתחת לשפל אחרון' — לא מוגדר, הושאר ריק"),
}
CRY={
 ('T09',1):dict(entry=63000,sl=('abs',60000),tp1=('abs',66000),tp2=('abs',70000),why="טריגר 'פריצה חוזרת של 63K' → 63,000; סטופ 'אזור 60K'; TP1 '66K'; TP2 '70K'"),
 ('T09',2):dict(entry=1850,sl=('abs',1810),tp1=('abs',1950),tp2=('abs',2150),why="טריגר 'מעל אזור 1,850'; סטופ '1,800–1,810' → 1,810; TP1 '1,950–2,000' → 1,950; TP2 '2,150'"),
 ('T09',3):dict(sl=('abs',72),tp1=('abs',85),tp2=('abs',95),why="טריגר 'מעל טווח 78–80' (טווח) → אין מחיר כניסה; סטופ '70–72' → 72; TP1 '85–88' → 85; TP2 '95–100' → 95"),
 ('T09',4):dict(sl=('abs',7.2),tp1=('abs',9.5),tp2=('abs',11),why="טריגר 'סביב 8.8–9' (טווח) → אין מחיר כניסה; סטופ '7–7.2' → 7.2; TP1 '9.5–10' → 9.5; TP2 '11–12' → 11"),
 ('T09',5):dict(why="טריגר, סטופ ויעדים איכותיים"),
 ('T09',6):dict(sl=('abs',0.7),tp1=('abs',1.1),tp2=('abs',1.5),why="טריגר 'אזור 0.75–0.8' (טווח) → אין מחיר כניסה; סטופ '0.7'; TP1 '1.1–1.2' → 1.1; TP2 '1.5'"),
 ('T09',7):dict(why="סטופ איכותי; TP1 '15–20% מהשיא' (לא מהכניסה) — הושאר ריק"),
 ('T09',8):dict(sl=('abs',0.45),tp1=('abs',0.35),tp2=('abs',0.27),why="סטופ 'מעל 0.45–0.46' → 0.45; TP1 '0.32–0.35' → 0.35; TP2 '0.25–0.27' → 0.27 (עמודות ה-CSV מוזזות בשורה זו)"),
 ('T09',9):dict(entry=55,sl=('abs',58),tp1=('abs',52),tp2=('abs',47),why="טריגר 'מתחת ל-Low של 55$' → 55; סטופ '58–60$' → 58; TP1 '50–52$' → 52; TP2 '45–47$' → 47 (עמודות ה-CSV מוזזות)"),
 ('T09',10):dict(tp1=('pct',5),why="TP1 'ירידה של 5–8% מתחת לכניסה' → 5%; סטופ איכותי"),
}
SYMC={'BTC':'BTC','ETH':'ETH','SOL':'SOL','LINK':'LINK','AVAX':'AVAX','BEAT':'BEAT','ZEC':'ZEC','APR':'APR','HYPE':'HYPE','ARB':'ARB','ENA':'ENA','CAP':'CAP','VELVET':'VELVET'}
def sc27(c):
    m=re.match(r'\s*~?\s*(\d{1,3})\s*(\(|$)',c)
    return float(m.group(1)) if m and 'ימי' not in c else None
def parse_all():
    out=[]; skipped=[]
    for rid,R in RUNS.items():
        h,rows=rd(R['csv'])
        for i,x in enumerate(rows,1):
            base=dict(run=rid,file=R['file'],csvf=R['csv'],created=R['created'],alert_date=R['date'],calc_date=R.get('day1'),source=R['src'],model=MODEL[R['src']],ttype=TTYPE[R['src']],rank=i,
                      sl_pct=None,tp_pct=[None,None,None],refs={},gaps=[],why='',score=None,hold=None,trig_txt='',cur=None)
            k=R['kind']
            if k in ('v27',):
                t=re.sub(r'[^A-Z.]','',x[1]); d=DIR(x[3]); base.update(ticker=t,dir=d,cur=num(x[4]),entry=num(x[5]) if '~'!=x[5].strip() else None,
                    sl=num(x[9]) if x[9].strip()!='~' else None,tps=[num(x[c]) if x[c].strip()!='~' else None for c in (11,12,13)],
                    score=sc27(x[16]),hold=x[15][:60],trig_txt=x[5][:160],tsl_txt=x[10][:60])
                if base['score'] is None: base['gaps'].append("ניקוד חסר בפלט (העמודה ריקה/'~' או מכילה טווח אחזקה: '%s')"%x[16][:30])
                elif '~' in x[16]: base['gaps'].append(f"ציון מסומן משוער: '{x[16][:40]}'")
                if base['entry'] is None: base['gaps'].append("אין מחיר כניסה בטבלה ('~')")
                if base['sl'] is None and all(v is None for v in base['tps']): base['gaps'].append("אין סטופ ויעדים בטבלה ('~')")
                if x[5].strip().startswith('~') and base['entry'] is not None: base['gaps'].append('מחיר הכניסה מסומן כמשוער (~)')
            elif k=='c27':
                t=x[0].strip(); d=DIR(x[1]); tp=[num(v) for v in x[10].split('/')]
                base.update(ticker=t,dir=d,cur=num(x[3]),entry=num(x[4]),sl=num(x[8]),tps=(tp+[None]*3)[:3],score=num(x[13]),hold=x[12][:60],trig_txt=x[4],tsl_txt=x[9])
            elif k=='v25':
                t=x[0].split(':')[-1].strip(); d=DIR(x[1]); base.update(ticker=t,dir=d,entry=num(x[2]),sl=num(x[3]),tps=[num(x[4]),num(x[5]),num(x[6])],score=num(x[8]),tsl_txt=x[7])
                base['cur']={'CDE':21.24,'SMCI':39.59,'AEHR':86.26,'NVDA':230.36,'MU':1016.59,'TSLA':354.08,'AVGO':357.90,'NFLX':78.25,'PCG':14.30,'AAL':13.13}.get(t)
            elif k in ('val','mom'):
                t=re.match(r'\s*([A-Z0-9]+)',x[0]).group(1); d=DIR(x[0])
                if t.startswith('XXXX'):
                    skipped.append(dict(run=rid,rank=i,ticker=t,dir=d,why="הטיקר מוסתר בפלט ('XXXX%d') — ההרצה החזירה סטאפים אנונימיים בלי סימול; אין אפשרות לבקטסט"%i)); continue
                sp=VAL.get((rid,i),{}); base.update(ticker=t,dir=d,entry=sp.get('entry'),sl=None,tps=[None,None,None],score=num(x[5] if k=='val' else x[4]),
                    hold=(x[6] if k=='val' else x[5])[:70],trig_txt=(x[7] if k=='val' else x[7])[:160],why=sp.get('why',''),spec=sp)
                if k=='mom': base['why']="כל רמות הכניסה/סטופ/יעד בסריקה איכותיות (MA20, שיא מקומי, Low של יום השיא, פיבו) — אין מספרים; כניסה = פתיחת יום 1, בלי סטופ/יעד"
            elif k=='cry':
                sym=re.match(r'\s*([A-Z]+)',x[0]).group(1); d=DIR(x[0]); sp=CRY.get((rid,i),{})
                sc_c=next((c for c in (4,5) if re.match(r'\s*\d{2}\b',x[c])),4); sh=sc_c-4
                if sh: base['gaps'].append('עמודות ה-CSV מוזזות בעמודה אחת בשורה זו — נקרא לפי התוכן')
                base.update(ticker=sym,sym=sym,dir=d,entry=sp.get('entry'),sl=None,tps=[None,None,None],score=num(x[sc_c]),hold=x[5+sh][:70],trig_txt=x[6+sh][:160],
                    why=sp.get('why') or ("טריגר, סטופ ויעדים איכותיים (שיא 4ש, EMA20/50, שפל טווח) — אין מספרים" if rid=='T11' else ''),spec=sp,run_h_utc=R['run_h_utc'])
            out.append(base)
    return out,skipped
if __name__=='__main__':
    o,s=parse_all()
    for r in o: print(r['run'],r['rank'],r['source'],r['ticker'],r['dir'],r.get('cur'),r['entry'],r['sl'],r['tps'],r['score'],r.get('spec',{}).get('sl'),r.get('spec',{}).get('tp1'),r['gaps'])
    print(len(o),'skipped',len(s))
    json.dump(dict(rows=o,skipped=s),open('/workspace/tracker/pplx/pplx_parsed.json','w'),ensure_ascii=False,indent=1)
