"""PIT features at the cutoff from TA-Lib (indicators + all 61 candle patterns) and pandas-ta (indicators TA-Lib lacks).
Every value is computed on the history truncated at the rule bar (leak_ta.py shows none of the columns used here changes when
later bars exist; DPO, Ichimoku chikou, TOS_STDEVALL and ZIGZAG — the columns that do — are NOT used). Raw values are stored;
direction alignment is done in analyze.py."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import sys, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0,(_SCANNER_ROOT + '/ta-repos-eval'))
from common import *
import talib, pandas_ta as ta
from multiprocessing import Pool
CDL=talib.get_function_groups()['Pattern Recognition']
def feat(r):
    out=dict(setup_id=r['setup_id'])
    try:
        x=trunc(hist(r),r)
        if len(x)<60: out['ta_error']='short history'; return out
        o,h,l,c,v=[x[k].values.astype(float) for k in ['Open','High','Low','Close','Volume']]
        A=talib.ATR(h,l,c,14)[-1]; out['atr14']=A; out['close']=c[-1]; out['ta_last_bar']=str(x.index[-1].date()); out['n_bars']=len(x)
        out['rsi14']=talib.RSI(c,14)[-1]
        m,ms,mh=talib.MACD(c,12,26,9); out['macdh_atr']=mh[-1]/A; out['macd_atr']=m[-1]/A
        out['macd_cross_up_3']=bool(np.any((mh[-3:]>0)&(np.r_[mh[-4:-1]]<=0))); out['macd_cross_dn_3']=bool(np.any((mh[-3:]<0)&(np.r_[mh[-4:-1]]>=0)))
        out['adx14']=talib.ADX(h,l,c,14)[-1]; out['di_spread']=talib.PLUS_DI(h,l,c,14)[-1]-talib.MINUS_DI(h,l,c,14)[-1]
        out['cci20']=talib.CCI(h,l,c,20)[-1]; out['mfi14']=talib.MFI(h,l,c,v,14)[-1]
        k,d=talib.STOCH(h,l,c); out['stoch_k']=k[-1]; out['willr14']=talib.WILLR(h,l,c,14)[-1]; out['ultosc']=talib.ULTOSC(h,l,c)[-1]
        out['roc10']=talib.ROC(c,10)[-1]; out['roc20']=talib.ROC(c,20)[-1]
        u,mid,lo=talib.BBANDS(c,20,2,2); out['bb_pctb']=(c[-1]-lo[-1])/(u[-1]-lo[-1]); out['bb_width']=(u[-1]-lo[-1])/mid[-1]*100
        out['natr14']=talib.NATR(h,l,c,14)[-1]
        s50=talib.SMA(c,50); s200=talib.SMA(c,200) if len(c)>=200 else np.full(len(c),np.nan)
        out['dist_sma50_atr']=(c[-1]-s50[-1])/A; out['dist_sma200_atr']=(c[-1]-s200[-1])/A if np.isfinite(s200[-1]) else np.nan
        out['sma50_gt_sma200']=bool(s50[-1]>s200[-1]) if np.isfinite(s200[-1]) else None
        out['aroonosc14']=talib.AROONOSC(h,l,14)[-1]
        ob=talib.OBV(c,v); out['obv_slope20_z']=talib.LINEARREG_SLOPE(ob,20)[-1]/(np.nanstd(np.diff(ob[-61:])) or np.nan)
        out['close_above_sar']=bool(c[-1]>talib.SAR(h,l)[-1])
        out['ht_trendmode']=bool(talib.HT_TRENDMODE(c)[-1]==1)
        out['linreg_slope20_atr']=talib.LINEARREG_SLOPE(c,20)[-1]/A
        for fn in CDL: out['cdl_'+fn[3:].lower()]=int(getattr(talib,fn)(o,h,l,c)[-1])
        # pandas-ta (lower-case OHLCV frame)
        y=x.copy(); y.columns=[q.lower() for q in y.columns]
        st=ta.supertrend(y.high,y.low,y.close,7,3.0); out['pta_supertrend_dir']=float(st['SUPERTd_7_3.0'].iloc[-1])
        sq=ta.squeeze(y.high,y.low,y.close); out['pta_sqz_on']=bool(sq['SQZ_ON'].iloc[-1]==1); out['pta_sqz_mom_atr']=float(sq.iloc[-1,0])/A
        out['pta_chop14']=float(ta.chop(y.high,y.low,y.close,14).iloc[-1])
        vt=ta.vortex(y.high,y.low,y.close,14); out['pta_vortex_diff']=float(vt.iloc[-1,0]-vt.iloc[-1,1])
        out['pta_stc']=float(ta.stc(y.close).iloc[-1,0])
        ich,_=ta.ichimoku(y.high,y.low,y.close,include_chikou=False); top=max(ich['ISA_9'].iloc[-1],ich['ISB_26'].iloc[-1]); bot=min(ich['ISA_9'].iloc[-1],ich['ISB_26'].iloc[-1])
        out['pta_ichi_pos']=1.0 if c[-1]>top else (-1.0 if c[-1]<bot else 0.0) if np.isfinite(top) and np.isfinite(bot) else np.nan
        out['pta_crsi']=float(ta.crsi(y.close).iloc[-1])
        ex=ta.exhc(y.high,y.low,y.close); out['pta_exhc_up']=float(ex.iloc[-1][[q for q in ex.columns if 'UP' in q][0]]); out['pta_exhc_dn']=float(ex.iloc[-1][[q for q in ex.columns if 'DN' in q][0]])
    except Exception as e: out['ta_error']=f'{e.__class__.__name__}: {e}'
    return out
if __name__=='__main__':
    recs=S[['setup_id','ticker','asset','rule_bar_actual']].to_dict('records')
    with Pool(2) as p: res=p.map(feat,recs,chunksize=10)
    X=pd.DataFrame(res); X.to_pickle(OUT+'ta_features.pkl')
    print(X.shape,'errors:',X.get('ta_error',pd.Series(dtype=object)).notna().sum()); print(X.get('ta_error',pd.Series(dtype=object)).value_counts().head())
    print(X.describe().T.head(60).to_string())
