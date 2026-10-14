"""PIT short-interest / short-volume / squeeze backtest on the 846 main-sheet setups (stocks). EXPERIMENTAL, weight 0.
Writes /workspace/tracker/short_pit_lookup.csv and prints the in-sample tables."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import sys, ast, re, time, json
sys.path.insert(0, _SCANNER_ROOT)
import pandas as pd, numpy as np
import scanner_short as SH
TR = (_SCANNER_ROOT + '/tracker'); t0 = time.time()
S = pd.read_csv(f'{TR}/setups-point-in-time-2026-10-08.csv'); R = pd.read_pickle(f'{TR}/rows_all.pkl')
S['tracker_source'] = [R[int(x[1:]) - 1]['source'] for x in S.setup_id]
M = S[(S.in_main_sheet == True) & (S.asset_class == 'stock') & S.alert_date.notna()].copy()
FL = pd.read_csv(f'{TR}/fundamentals_pit_lookup.csv')[['setup_id', 'fund_shares']]
M = M.merge(FL, on='setup_id', how='left')
src = open((_SCANNER_ROOT + '/swing_scan.py')).read()
LIVE = [t for t in ast.literal_eval(re.search(r"tickers = (\[.*?\])\n", src, re.S).group(1)) if not t.startswith('^')]
ETF = ast.literal_eval(re.search(r"ETF_LIKE = (\{.*?\})\n", src, re.S).group(1))
LIVE = sorted({t for t in LIVE if t not in ETF}); UNIV = sorted(set(LIVE) | set(M.ticker))
P = pd.read_pickle(f'{TR}/prices_all.pkl'); spy = P['SPY']['Close'].dropna(); SESS = list(spy.index)
si = SH.fetch_si(UNIV, start='2025-10-01'); print('SI rows', len(si), 'symbols', si.symbol.nunique(), f'{time.time()-t0:.0f}s', flush=True)
need = [d for d in SESS if d >= pd.Timestamp('2026-03-15')]
for d in need: SH.regsho_day(d)
print('regsho files', sum(SH._RS[pd.Timestamp(d).strftime('%Y%m%d')] is not None for d in need), '/', len(need), f'{time.time()-t0:.0f}s', flush=True)
FLOAT = SH.float_shares(UNIV); print('float known', sum(v is not None for v in FLOAT.values()), '/', len(UNIV), f'{time.time()-t0:.0f}s', flush=True)
rows = []
for x in M.itertuples():
    b = P[x.ticker][['Open', 'High', 'Low', 'Close', 'Volume']].dropna(subset=['Close']) if x.ticker in P.columns.get_level_values(0) else None
    b = b.loc[:pd.Timestamp(x.cutoff_bar_date)] if b is not None else None
    sess = [d for d in SESS if d < pd.Timestamp(x.alert_date)]
    o = SH.short_columns(x.ticker, x.alert_date, b, si, sess, float_sh=FLOAT.get(x.ticker), shares_out=x.fund_shares if pd.notna(x.fund_shares) else None)
    r = R[int(x.setup_id[1:]) - 1]; cum = r['cum'] or []; sg = -1 if x.direction == 'SHORT' else 1
    ex20 = None
    if len(cum) >= 20:
        d1 = pd.Timestamp(x.alert_date); post = spy.index[spy.index >= d1][:20]; pre = spy.index[spy.index < d1]
        if len(post) == 20 and len(pre): ex20 = float(cum[19]) - sg * (float(spy.loc[post[19]]) / float(spy.loc[pre[-1]]) - 1)
    rows.append(dict(setup_id=x.setup_id, tracker_source=x.tracker_source, ticker=x.ticker, direction=x.direction, alert_date=x.alert_date,
                     cutoff_bar_date=x.cutoff_bar_date, dup_not_counted=x.dup_not_counted, excess_dir_d20=ex20, outcome=r['outcome'], mae=r['mae'], **o))
L = pd.DataFrame(rows)
rt = pd.read_csv((_SCANNER_ROOT + '/trading-frameworks-eval/iaf/sim_ratchet_trades.csv')); rt = rt[rt.policy == 'rt_plain_c'][['setup_id', 'status', 'ret_net']]
L = L.merge(rt.rename(columns={'status': 'active_stop_status', 'ret_net': 'active_ret_net'}), on='setup_id', how='left')
L.to_csv(f'{TR}/short_pit_lookup.csv', index=False, encoding='utf-8-sig')
print(f'saved {len(L)} rows {time.time()-t0:.0f}s')
# leak check: SI pub < alert, SVR files < alert by construction
assert (L.short_si_pub_est.dropna() < L.loc[L.short_si_pub_est.notna(), 'alert_date']).all()
X = L[L.dup_not_counted != True]
cov = {c: f"{X[c].notna().mean()*100:.1f}%" for c in ['short_si_shares', 'short_si_pct_float', 'short_si_pct_shout', 'short_si_dtc20', 'short_si_chg_pct', 'short_svr_z20', 'short_svr_z60', 'short_comp_si', 'short_comp_trend', 'short_comp_breakout', 'short_squeeze_candidate']}
print('coverage', json.dumps(cov))
def summ(g, lab):
    e = g.excess_dir_d20.dropna()
    return dict(group=lab, n=len(g), n_d20=len(e), dates=g.alert_date.nunique(), dates_d20=g.loc[g.excess_dir_d20.notna(), 'alert_date'].nunique(),
                mean_ex20=round(e.mean(), 4) if len(e) else None, median_ex20=round(e.median(), 4) if len(e) else None, hit_ex20=round((e > 0).mean(), 3) if len(e) else None,
                stop_tracker=f"{int((g.outcome=='סטופ').sum())}/{int(g.outcome.isin(['סטופ','TP1']).sum())}",
                stop_active=f"{int((g.active_stop_status=='stopped').sum())}/{int(g.active_stop_status.notna().sum())}", mean_mae=round(g.mae.mean(), 4))
out = []
Lg = X[X.direction == 'LONG']; Sg = X[X.direction == 'SHORT']
hs = lambda g: g.short_comp_si == True
bo = lambda g: (g.short_comp_breakout == True) | (g.short_comp_trend == True)
out += [summ(Lg[hs(Lg) & bo(Lg)], 'LONG high-SI + breakout/trend (squeeze_candidate)'), summ(Lg[~(hs(Lg) & bo(Lg))], 'LONG all other'),
        summ(Lg[hs(Lg)], 'LONG high-SI (any)'), summ(Lg[Lg.short_comp_si == False], 'LONG low-SI'),
        summ(Sg[hs(Sg)], 'SHORT high-SI'), summ(Sg[Sg.short_comp_si == False], 'SHORT low-SI'),
        summ(Sg[Sg.short_squeeze_candidate == True], 'SHORT on squeeze_candidate'), summ(Sg[Sg.short_squeeze_candidate != True], 'SHORT other')]
T = pd.DataFrame(out); pd.set_option('display.width', 250); print(T.to_string(index=False))
T.to_csv(f'{TR}/short/short_backtest_in_sample.csv', index=False)
print('comparisons on the same in-sample setups: 4 pairs x 3 metrics (excess d20, tracker stop rate, active stop rate) = 12')
# universe: latest published report as of 2026-10-08
lat = {t: SH.si_at(si, t, '2026-10-09') for t in UNIV}
adv = {t: float(P[t]['Volume'].dropna().iloc[-20:].mean()) for t in UNIV if t in P.columns.get_level_values(0)}
U = []
for t, r in lat.items():
    if r is None: continue
    f = FLOAT.get(t); U.append(dict(t=t, live=t in LIVE, settlement=r['settlement_date'], pub=r['si_pub_est'], si=r['si'],
                                  pct_float=100 * r['si'] / f if f else None, dtc20=r['si'] / adv[t] if adv.get(t) else None, dtc_finra=r['finra_dtc']))
U = pd.DataFrame(U); U.to_csv(f'{TR}/short/universe_si_latest.csv', index=False)
for lab, g in (('universe (live list + all backtest stocks)', U), ('live scan list', U[U.live])):
    print(f"{lab}: {len(g)} with SI; SI%float>=15: {int((g.pct_float>=15).sum())}; dtc20>=5: {int((g.dtc20>=5).sum())}; either: {int(((g.pct_float>=15)|(g.dtc20>=5)).sum())}; settlement {g.settlement.max()} pub {g.pub.max()}")
print(U[(U.pct_float >= 15) | (U.dtc20 >= 5)].sort_values('pct_float', ascending=False).round(2).to_string(index=False))
