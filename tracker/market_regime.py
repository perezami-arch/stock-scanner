#!/usr/bin/env python
"""Market regime snapshot for Ilan's scanners (Grok near-low / momentum / prebreakout, bot v2.8).
Usage: /workspace/.venv-tracker/bin/python /workspace/tracker/market_regime.py [--history OUT.csv] [--start YYYY-MM-DD] [--no-breadth]
Prints JSON with current values of:
  CNN Fear&Greed (production.dataviz.cnn.io, browser UA), crypto Fear&Greed (alternative.me),
  AAII bull/neutral/bear (aaii.com; scripted requests are blocked by Imperva -> falls back to the cache
  /workspace/tracker/rules/aaii_weekly*.csv, refresh it from https://www.aaii.com/sentimentsurvey/sent_results via WebFetch/browser),
  S5FI/S5TH/S5TW computed from CURRENT S&P 500 members (survivorship-biased; checked vs eoddata 21.9-2.10.2026: |diff|<=0.8pt) + 10-session S5FI direction,
  VIX, VIX/VIX3M, DXY, US10Y (^TNX), US30Y (^TYX) with 30d/180d bp changes, 30Y-10Y, SPY/QQQ vs SMA50/200, sector-ETF trends,
  FRED: DFF, CPIAUCSL YoY, UNRATE, T10Y2Y (needs env FRED_API_KEY; the key is never printed),
  and the v2.8 MACRO SCORE (VIX+S5FI+F&G+AAII+breadth divergence+yield score) with long/short modifiers.
--history writes a daily breadth series (for backtests).
"""
import sys, io, os, glob, json, argparse, datetime as dt
import pandas as pd, numpy as np, requests, yfinance as yf
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36','Referer':'https://edition.cnn.com/','Origin':'https://edition.cnn.com'}
SECTORS={'XLK':'Technology','XLF':'Financials','XLE':'Energy','XLV':'Health Care','XLY':'Cons. Discretionary','XLP':'Cons. Staples','XLI':'Industrials','XLB':'Materials','XLU':'Utilities','XLRE':'Real Estate','XLC':'Communication','SMH':'Semis','IWM':'Small caps'}
def sp500():
    try:
        h=requests.get('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies',headers=UA,timeout=30).text
        return [s.replace('.','-') for s in pd.read_html(io.StringIO(h))[0]['Symbol']],'wikipedia live'
    except Exception as e:
        c=pd.read_csv('/workspace/tracker/rules/sp500_constituents.csv'); return [s.replace('.','-') for s in c['Symbol']],f'cache ({e.__class__.__name__})'
def breadth(start):
    T,src=sp500(); d=yf.download(T,start=start,group_by='ticker',auto_adjust=False,progress=False,threads=True)  # raw closes match official $S5xx better
    C=pd.concat({t:d[t]['Close'] for t in T if t in d.columns.get_level_values(0)},axis=1).dropna(how='all')
    out={}
    for n,k in ((20,'S5TW'),(50,'S5FI'),(200,'S5TH')):
        ma=C.rolling(n,min_periods=n).mean(); valid=ma.notna()&C.notna()
        out[k]=((C>ma)&valid).sum(axis=1)/valid.sum(axis=1)*100
    b=pd.DataFrame(out); b['n_members']=C.notna().sum(axis=1); return b,src
def cnn():
    d=(dt.date.today()-dt.timedelta(days=30)).isoformat()
    j=requests.get(f'https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{d}',headers=UA,timeout=30).json()['fear_and_greed']
    return dict(score=round(j['score'],1),rating=j['rating'],timestamp_utc=j['timestamp'],prev_close=round(j['previous_close'],1),week_ago=round(j['previous_1_week'],1),month_ago=round(j['previous_1_month'],1))
def crypto():
    j=requests.get('https://api.alternative.me/fng/?limit=1',timeout=30).json()['data'][0]
    return dict(value=int(j['value']),rating=j['value_classification'],date_utc=dt.datetime.fromtimestamp(int(j['timestamp']),dt.timezone.utc).date().isoformat())
def aaii():
    try:
        h=requests.get('https://www.aaii.com/sentimentsurvey/sent_results',headers=UA,timeout=30).text
        t=pd.read_html(io.StringIO(h))[0]; r=t.iloc[0]
        b,n_,br=[float(str(r[k]).strip('%')) for k in ('Bullish','Neutral','Bearish')]
        return dict(src='aaii.com live',date=str(r.iloc[0]),bullish=b,neutral=n_,bearish=br,bull_bear_spread=round(b-br,1))
    except Exception as e:
        fs=sorted(glob.glob('/workspace/tracker/rules/aaii_weekly*.csv'))
        c=pd.concat([pd.read_csv(f) for f in fs]).drop_duplicates('reported_date').sort_values('reported_date').iloc[-1]
        age=(dt.date.today()-dt.date.fromisoformat(c.reported_date)).days
        return dict(src=f'cache (live blocked: {e.__class__.__name__}); refresh via WebFetch of aaii.com/sentimentsurvey/sent_results',date=c.reported_date,age_days=age,stale=age>8,bullish=c.bullish,neutral=c.neutral,bearish=c.bearish,bull_bear_spread=round(c.bullish-c.bearish,1))
def fred():
    k=os.environ.get('FRED_API_KEY')
    if not k: return {'status':'skipped: FRED_API_KEY not set'}
    out={}
    for sid,units,lab in (('DFF','lin','DFF fed funds %'),('CPIAUCSL','pc1','CPI YoY %'),('UNRATE','lin','UNRATE %'),('T10Y2Y','lin','T10Y2Y spread %')):
        try:
            j=requests.get('https://api.stlouisfed.org/fred/series/observations',params=dict(series_id=sid,api_key=k,file_type='json',units=units,sort_order='desc',limit=5),timeout=30).json()
            o=[x for x in j['observations'] if x['value']!='.'][0]; out[lab]=dict(value=round(float(o['value']),2),obs_date=o['date'])
        except Exception as e: out[lab]=f'unavailable ({e.__class__.__name__})'
    return out
def hist(t,period='400d'): return yf.Ticker(t).history(period=period,auto_adjust=True)['Close'].dropna()
def chg_bp(s,days):
    ref=s[s.index.tz_localize(None)<=pd.Timestamp(s.index[-1].tz_localize(None))-pd.Timedelta(days=days)]
    return round((s.iloc[-1]-ref.iloc[-1])*100,1) if len(ref) else None
def score_v28(R):
    """v2.8 MACRO block; '~' (None) indicators score 0."""
    sc={}; v=R.get('VIX',{}).get('value')
    sc['VIX']=0 if v is None else 4 if v>30 else 2 if v>=25 else -2 if v>=19 else 0 if v>=15 else (-4 if v<14.5 else 0)
    b=R.get('breadth',{}); s5=b.get('S5FI')
    sc['S5FI']=0 if s5 is None else 4 if s5<20 else 2 if s5<40 else 0 if s5<=60 else -2 if s5<=75 else -4
    sc['breadth_divergence']=-2 if b.get('S5FI_divergence') else 0
    f=R.get('cnn_fear_greed',{}); f=f.get('score') if isinstance(f,dict) else None
    sc['CNN_FG']=0 if f is None else 4 if f<=9 else 2 if f<=25 else 0 if f<=70 else -2 if f<=85 else -4
    a=R.get('aaii',{}); be,bu=a.get('bearish'),a.get('bullish')
    sc['AAII']=0 if be is None else 4 if be>45 else 2 if be>=35 else -4 if bu>45 else -2 if bu>=35 else 0
    y=R.get('US10Y',{}); c30,c180=y.get('chg_30d_bp'),y.get('chg_180d_bp')
    ys=0 if c30 is None else -4 if c30>50 else -2 if c30>25 else 0 if c30>=-25 else 2 if c30>=-50 else 3
    if c30 is not None and c30<-50 and (v or 0)>25: ys=0
    if ys and c180 is not None: ys=int(round(ys*1.5)) if np.sign(c30)==np.sign(c180) else int(round(ys*0.5))
    sc['yield_10Y']=ys; tot=sum(sc.values())
    return dict(components=sc,MACRO_SCORE=tot,regime='RISK-OFF' if tot>=6 else 'RISK-ON' if tot<=-6 else 'NEUTRAL',long_modifier=max(-15,min(15,tot)),short_modifier=max(-15,min(15,-tot)),
                note='per work-plan v2.8 section 1/1.5; AAII bearish 35-45 scored +2 before bullish rules')
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--history'); ap.add_argument('--start',default='2025-01-01'); ap.add_argument('--no-breadth',action='store_true'); a=ap.parse_args()
    R={'run_time_local':dt.datetime.now().strftime('%Y-%m-%d %H:%M')+' (box local, Asia/Jerusalem)'}
    for k,fn in (('cnn_fear_greed',cnn),('crypto_fear_greed',crypto)):
        try: R[k]=fn()
        except Exception as e: R[k]=f'unavailable ({e.__class__.__name__}) - proxy: VIX + S5FI'
    R['aaii']=aaii(); R['fred']=fred()
    for k,t in [('VIX','^VIX'),('VIX3M','^VIX3M'),('DXY','DX-Y.NYB'),('US10Y','^TNX'),('US30Y','^TYX'),('US2Y(2YY=F)','2YY=F'),('US3M','^IRX')]:
        try:
            s=hist(t,'250d'); R[k]=dict(value=round(float(s.iloc[-1]),3),date=str(s.index[-1].date()))
            if k in('US10Y','US30Y'): R[k].update(chg_30d_bp=chg_bp(s,30),chg_180d_bp=chg_bp(s,180))
            if k=='DXY': R[k]['ret_20d_%']=round((s.iloc[-1]/s.iloc[-21]-1)*100,2)
        except Exception as e: R[k]=f'unavailable ({e.__class__.__name__})'
    try:
        R['VIX/VIX3M (>1 = backwardation/stress)']=round(R['VIX']['value']/R['VIX3M']['value'],3)
        R['30Y-10Y spread %']=round(R['US30Y']['value']-R['US10Y']['value'],3); R['10Y-2Y spread % (yahoo 2YY=F)']=round(R['US10Y']['value']-R['US2Y(2YY=F)']['value'],3)
    except Exception: pass
    for t in ('SPY','QQQ'):
        s=hist(t); R[t]=dict(close=round(float(s.iloc[-1]),2),vs_SMA50=f"{s.iloc[-1]/s.iloc[-50:].mean()-1:+.2%}",vs_SMA200=f"{s.iloc[-1]/s.iloc[-200:].mean()-1:+.2%}",ret_20d=f"{s.iloc[-1]/s.iloc[-21]-1:+.2%}")
    sec={}
    for e,nm in SECTORS.items():
        try:
            s=hist(e,'150d'); m=s.rolling(50).mean(); up=bool(s.iloc[-1]>m.iloc[-1] and m.iloc[-1]>m.iloc[-11])
            sec[e]=dict(name=nm,vs_SMA50=f"{s.iloc[-1]/m.iloc[-1]-1:+.2%}",SMA50_slope_10d=f"{m.iloc[-1]/m.iloc[-11]-1:+.2%}",ret_20d=f"{s.iloc[-1]/s.iloc[-21]-1:+.2%}",uptrend=up)
        except Exception as e: sec[e]=f'unavailable ({e.__class__.__name__})'
    R['sector_etfs (uptrend = above rising SMA50; backtest: longs only in uptrend sectors)']=sec
    if not a.no_breadth:
        start=a.start if a.history else (dt.date.today()-dt.timedelta(days=330)).isoformat()
        b,src=breadth(start); bd=b.dropna(); lr=bd.iloc[-1]; d10=lr.S5FI-bd.S5FI.iloc[-11]
        spx=hist('^GSPC','60d'); near_high=bool(spx.iloc[-1]>=spx.iloc[-20:].max()*0.99)
        R['breadth']=dict(S5TW=round(float(lr.S5TW),1),S5FI=round(float(lr.S5FI),1),S5TH=round(float(lr.S5TH),1),S5FI_10d_change=round(float(d10),1),
            S5FI_direction='rising' if d10>0 else 'falling',S5FI_divergence=bool(d10<0 and near_high),date=str(bd.index[-1].date()),members=int(lr.n_members),
            constituents=src,caveat='current members only (survivorship bias); within ~1pt of official $S5FI/$S5TH/$S5TW on 21.9-2.10.2026 (eoddata)')
        if a.history: b.to_csv(a.history); R['history_file']=a.history
    R['v2.8_macro']=score_v28(R)
    print(json.dumps(R,indent=1,ensure_ascii=False,default=str))
