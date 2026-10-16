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
        vx = z['^VIX'].values; zs = {}
        for conf in (1, 2):   # 19-20 zone (Ilan 16.10): >20 = fear on, <19 = fear off, 19-20 keep previous; conf = consecutive closes
            cur, hist = 0, []
            for i in range(len(vx)):
                if i >= conf - 1 and (vx[i - conf + 1:i + 1] > 20).all(): cur = 1
                elif i >= conf - 1 and (vx[i - conf + 1:i + 1] < 19).all(): cur = 0
                hist.append(cur)
            zs[conf] = (hist[-1], hist[-2] if len(hist) > 1 else hist[-1])
        _C[k] = (float(z['^VIX'].iloc[-1]), c, zs, z['^VIX'].iloc[-120:].round(4).tolist())
    return _C[k]
def fit(c, cut):
    try:
        vix, corr, zs, _ = _data(cut)
        zone = {}
        for conf, sfx in ((1, ''), (2, '_2c')):
            now, prev = zs[conf]
            zone.update({f'exp_vix_zone_19_20{sfx}': now, f'exp_vix_cross_up_20{sfx}': bool(now == 1 and prev == 0), f'exp_vix_cross_down_19{sfx}': bool(now == 0 and prev == 1)})
        e = 'BTC-USD' if c.get('asset') == 'crypto' else c.get('sector_etf')
        if e not in corr or not np.isfinite(corr[e]): return {'exp_vixreg_vix': vix, 'exp_vixreg_corr': None, 'exp_vixreg_fit': None, **zone}
        on = corr[e] < corr.median(); f = 0
        if c.get('direction') == 'LONG':
            if vix > VIX_HI: f = 1 if on else -1
            elif vix < VIX_LO: f = -1 if on else 1
        return {'exp_vixreg_vix': round(vix, 2), 'exp_vixreg_corr': round(float(corr[e]), 3), 'exp_vixreg_fit': f, **zone}
    except Exception as ex:
        return {'exp_vixreg_vix': None, 'exp_vixreg_corr': None, 'exp_vixreg_fit': None, 'exp_vixreg_error': str(ex)[:120]}

# ------------------------------------------------------------------ ACTIVE scoring component (scoring model v2, approved by Ilan 16.10.2026 14:58 IL)
VIX30_BONUS = 5.0        # points added to unified_score (score capped at 100)
VIX30_WINDOW = 20        # sessions: the cross day + the next 19 sessions (= the tested 20-day horizon)
def vix30_episode(vix_hist, window=VIX30_WINDOW, level=VIX_HI):
    """vix_hist: daily VIX closes up to and including the cutoff session (point-in-time). Returns (active, sessions_since_cross).
    LOCKED RULE: an episode starts on the FIRST close > 30 after a close <= 30. The bonus is active on that session and the next
    window-1 sessions, whatever VIX does in between. A new first-cross inside an active window does not extend it (no re-arming
    until the window has ended); after the window, the next close>30-after-<=30 starts a new episode."""
    v = [float(x) for x in vix_hist]; start = None; i = 1
    while i < len(v):
        if v[i] > level and v[i - 1] <= level:
            start = i; i += window; continue
        i += 1
    if start is None: return False, None
    since = len(v) - 1 - start
    return since < window, since
def vix30_bonus(c, cut, _data_fn=None):
    """+VIX30_BONUS for LONG setups in a risk-on sector (PIT 250d corr(ETF, dVIX) below the cross-sectional median; crypto -> BTC)
    while a VIX>30 episode is active. Returns dict with the bonus and audit fields."""
    try:
        vix, corr, _, hist = (_data_fn or _data)(cut)
        active, since = vix30_episode(hist)
        e = 'BTC-USD' if c.get('asset') == 'crypto' else c.get('sector_etf')
        on = e in corr and np.isfinite(corr[e]) and corr[e] < corr.median()
        b = VIX30_BONUS if (active and on and c.get('direction') == 'LONG') else 0.0
        return {'vix30_bonus': b, 'vix30_episode_active': bool(active), 'vix30_sessions_since_cross': since, 'vix30_riskon_sector': bool(on), 'vix30_vix': round(vix, 2)}
    except Exception as ex:
        return {'vix30_bonus': 0.0, 'vix30_error': str(ex)[:120]}
