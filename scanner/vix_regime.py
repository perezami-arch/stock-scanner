"""VIX sector-regime fit (16.10.2026, Ilan's contrarian rule). EXPERIMENTAL, WEIGHT 0 - not in unified_score.
Locked: VIX>30 -> favour LONGS in risk-on sectors; VIX<16 -> favour LONGS in risk-off sectors; 16-30 neutral (0).
Risk-on/off = point-in-time 250d corr(sector ETF daily return, dVIX) vs the cross-sectional median (crypto -> BTC-USD).
exp_vixreg_fit in {-1,0,+1} (LONG only); exp_vixreg_vix, exp_vixreg_corr = info. Backtest: research/vix-regime/RESULTS.md"""
import numpy as np, pandas as pd
ETFS = ['XLK','XLY','XLC','XLF','XLI','XLE','XLB','XLU','XLP','XLV','XLRE','SMH','GLD','BTC-USD']
VIX_HI, VIX_LO = 30.0, 16.0
_C = {}
def _data(cut):
    k = str(pd.Timestamp(cut).date())
    if k not in _C:
        import yfinance as yf
        z = yf.download(ETFS + ['^VIX'], start=pd.Timestamp(cut) - pd.Timedelta(days=500), end=pd.Timestamp(cut).tz_localize(None) + pd.Timedelta(days=1) if pd.Timestamp(cut).tzinfo else pd.Timestamp(cut) + pd.Timedelta(days=1),
                        auto_adjust=True, progress=False, threads=False)['Close']
        z = z[z['^VIX'].notna()]; z = z[z.index <= pd.Timestamp(k)]
        r = z[ETFS].pct_change(); dv = z['^VIX'].diff()
        c = pd.Series({e: r[e].iloc[-250:].corr(dv.iloc[-250:]) for e in ETFS})
        _C[k] = (float(z['^VIX'].iloc[-1]), c)
    return _C[k]
def fit(c, cut):
    try:
        vix, corr = _data(cut)
        e = 'BTC-USD' if c.get('asset') == 'crypto' else c.get('sector_etf')
        if e not in corr or not np.isfinite(corr[e]): return {'exp_vixreg_vix': vix, 'exp_vixreg_corr': None, 'exp_vixreg_fit': None}
        on = corr[e] < corr.median(); f = 0
        if c.get('direction') == 'LONG':
            if vix > VIX_HI: f = 1 if on else -1
            elif vix < VIX_LO: f = -1 if on else 1
        return {'exp_vixreg_vix': round(vix, 2), 'exp_vixreg_corr': round(float(corr[e]), 3), 'exp_vixreg_fit': f}
    except Exception as ex:
        return {'exp_vixreg_vix': None, 'exp_vixreg_corr': None, 'exp_vixreg_fit': None, 'exp_vixreg_error': str(ex)[:120]}
