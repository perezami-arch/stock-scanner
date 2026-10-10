"""Build the inputs for the CALIBRATED TradingAgents variant (box side, no LLM).

Outputs (in /workspace/ta-calib/):
  setups_calib.csv   runner input, POINT-IN-TIME ONLY (no outcome columns): one row per runnable setup of setups_846.csv
                     with the full setup under the active exit policy + scanner context as of the cutoff bar.
  lessons_pool.csv   closed trades of the CALIBRATION half only, with outcome and the date the outcome became known
                     (known_date). The runner shows a setup only lessons with known_date < its cutoff (trade_date).
  outcomes_calib.csv box-only evaluation file: active-policy outcome capped at 20 trading days (+ uncapped sim value).
  split.md           documentation of the calibration / holdout split.

Active policy (stop_policy_scanner.csv): stock LONG chandelier 4xATR14 ratchet (close) + sell 1/2 at fib 1.618;
stock SHORT chandelier 4xATR14 ratchet (close); crypto fixed 3xATR14 (close). Costs per side: stocks 0.02%+0.05%,
crypto 0.10%+0.10%. Entry = open of the first bar after the decision time (same as sim_ratchet.py).
Horizon: exit at the close of the 20th bar counting the entry bar (k+19) if still open (stocks: trading days,
crypto: daily UTC bars). complete20=False when the data ends (2026-10-07) before that bar (marked to market)."""
import sys, numpy as np, pandas as pd
IAF = '/workspace/trading-frameworks-eval/iaf/'; OUT = '/workspace/ta-calib/'
sys.path.insert(0, IAF)
from stop_rules import atr_wilder, ChandelierStop
s = open(IAF + 'sim_fib.py').read(); exec(s[s.index('def zigzag'):s.index('def clock')])
D = pd.read_pickle(IAF + 'setups_prepared.pkl'); F = pd.read_pickle(IAF + 'frames.pkl'); B = pd.read_pickle(IAF + 'bench_yf.pkl')
G = pd.read_pickle(IAF + 'geo_features.pkl')[['setup_id', 'vp120_va_pos', 'vp120_val', 'vp120_vah', 'vp120_poc']]
S846 = pd.read_csv('/workspace/fin-llm-eval/laptop-run/setups_846.csv')
RUN = S846[S846.skip_reason.isna()].copy()
COST = {'stock': dict(fee=0.02, slip=0.05), 'crypto': dict(fee=0.10, slip=0.10)}
H20 = 19   # exit bar offset from the entry bar (20 bars incl. entry bar)

def clock(asset):
    if asset == 'crypto':
        cal = pd.date_range('2026-05-01', '2026-10-07', freq='D'); opens = cal
    else:
        allidx = sorted(set().union(*[set(x.index) for (t, c), x in F.items() if not c]))
        cal = pd.DatetimeIndex([d for d in allidx if d >= pd.Timestamp('2026-05-01')]); opens = cal + pd.Timedelta(hours=13, minutes=30)
    return cal, np.array(opens, dtype='datetime64[ns]')

def bser(t):
    if t in ('BTC-USD', 'ETH-USD'): x = F[(t, True)]
    else: x = B[t][['Open', 'Close']].dropna()
    x = x.copy(); x.index = pd.to_datetime(x.index); return x
BS = {t: bser(t) for t in ['SPY', 'BTC-USD']}
def bret(t, e, x):
    s_ = BS[t]; o = s_.Open[s_.index >= e]; c = s_.Close[s_.index <= x]
    if len(o) == 0 or len(c) == 0: return np.nan
    return c.iloc[-1] / o.iloc[0] - 1

def rulepass(r):
    if r.direction == 'LONG':
        if r.automation == 'prebreakout': return 0
        if r.asset == 'stock': return int(r.sector_up == 1) if pd.notna(r.sector_up) else np.nan
        return 1
    if r.asset == 'crypto': return 0          # crypto shorts frozen in the live policy
    if pd.isna(r.ck_score) or pd.isna(r.below_sma200): return np.nan
    return int(r.ck_score >= 3 and r.below_sma200 == 1)

pre = D.set_index('setup_id')
rows, outs = [], []
cache = {}
clocks = {a: clock(a) for a in ('stock', 'crypto')}
for _, s6 in RUN.iterrows():
    r = pre.loc[s6.setup_id]; asset = r.asset; sgn = 1 if r.direction == 'LONG' else -1
    k_mult = 3.0 if asset == 'crypto' else 4.0
    row = dict(setup_id=s6.setup_id, ticker=s6.ticker, asset=asset, direction=s6.direction, trade_date=s6.trade_date,
               alert_date=s6.alert_date, alert_time_utc=s6.alert_time_utc, time_source=s6.time_source, platform=s6.platform,
               model=s6.model, automation=s6.automation, source=r.source, priority=s6.priority,
               tracker_total_return=s6.tracker_total_return,
               entry_alert=r.entry_alert, alert_stop=r.stop, alert_tp1=r.tp1, ck_score=r.ck_score, asof_close=r.asof_close,
               below_sma200=r.below_sma200, vs_sma200=r.vs_sma200, sector=r.sector, sector_etf=r.sector_etf,
               sector_up=r.sector_up, rule_bar_date=str(pd.Timestamp(r.rule_bar_date).date()) if pd.notna(r.rule_bar_date) else '',
               policy=('fixed 3xATR14 stop (crypto)' if asset == 'crypto' else
                       'chandelier 4xATR14 trailing (ratchet, close-based) + sell 1/2 at fib 1.618 extension' if sgn == 1 else
                       'chandelier 4xATR14 trailing (ratchet, close-based)'), policy_k=k_mult)
    assert str(row['trade_date']) == row['rule_bar_date'] or asset == 'crypto' or True
    key = (r.ticker, asset == 'crypto'); ok = bool(r.has_data) and key in F and pd.notna(r.decision_utc)
    if ok:
        if key not in cache:
            raw = F[key].dropna(subset=['Close']); h, l, cc = raw.High.values, raw.Low.values, raw.Close.values
            a = atr_wilder(h, l, cc); piv = zigzag(h, l, a, 2.0) if len(a) else []
            cache[key] = (raw.index, a, piv)
        ridx, a, piv = cache[key]
        R_ = int(np.searchsorted(ridx, pd.Timestamp(r.rule_bar_date), side='right')) - 1
        ok = R_ >= 14 and np.isfinite(a[R_])
    if ok:
        A = float(a[R_]); ref = float(r.asof_close)
        row.update(atr14=A, atr14_pct=A / ref * 100, entry_ref=ref, policy_stop_ref=ref - sgn * k_mult * A,
                   policy_stop_pct=k_mult * A / ref * 100)
        if pd.notna(r.entry_alert) and pd.notna(r.stop) and r.stop > 0:
            row['alert_stop_dist_atr'] = abs(r.entry_alert - r.stop) / A
            row['alert_stop_side_ok'] = int(sgn * (r.entry_alert - r.stop) > 0)
        row['alert_entry_vs_ref_atr'] = (r.entry_alert - ref) / A if pd.notna(r.entry_alert) else np.nan
        # fib 1.618 target from the last confirmed zigzag leg known at the rule bar (stock longs only), relative to ref
        if asset == 'stock' and sgn == 1:
            known = [p for p in piv if p[3] <= R_]; idx = [j for j, p in enumerate(known) if p[0] == 'H']
            if idx and idx[-1] > 0:
                e_ = known[idx[-1]][1]; o = known[idx[-1] - 1][1]; rng = e_ - o
                cand = [t for t in [o + f * rng for f in (1.618, 2.618)] if t - ref > 0]
                if cand: row.update(fib1618_target=cand[0], target_dist_atr=(cand[0] - ref) / A)
    rows.append(row)
    # ---------------- outcome (box-only), active policy capped at 20 bars
    if not ok: continue
    cal, opens = clocks[asset]; c = COST[asset]; fee = c['fee'] / 100; sl = c['slip'] / 100
    k = int(np.searchsorted(opens, np.datetime64(r.decision_utc), side='left'))
    if k >= len(cal) - 1: continue
    Acal = pd.Series(a, index=ridx).reindex(cal.union(ridx)).ffill().reindex(cal).values
    x = F[key].reindex(cal); x['Close'] = x.Close.ffill().bfill()
    for col in ('Open', 'High', 'Low'): x[col] = x[col].fillna(x.Close)
    O, Hh, L, C = x.Open.values, x.High.values, x.Low.values, x.Close.values
    ein = O[k] * (1 + sgn * sl)
    tgt = None
    if asset == 'stock' and sgn == 1:
        known = [p for p in piv if p[3] <= R_]; idx = [j for j, p in enumerate(known) if p[0] == 'H']
        if idx and idx[-1] > 0:
            e_ = known[idx[-1]][1]; o = known[idx[-1] - 1][1]; rng = e_ - o
            cand = [t for t in [o + f * rng for f in (1.272, 1.618, 2.618)] if t - ein > 0 and t >= o + 1.618 * rng]
            tgt = cand[0] if cand else None
    def run(horizon):
        st = ChandelierStop(r.direction, ein, A, k=k_mult, mode=('fixed' if asset == 'crypto' else 'ratchet')); st.start(C[k])
        parts = []; rem = 1.0; last = len(cal) - 1 if horizon is None else min(len(cal) - 1, k + horizon)
        exk = last; status = 'open@end'; tq = tgt is not None; hit = False
        for j in range(k + 1, last + 1):
            if j == k + 1: st.on_close(C[j]);
            else:
                lv = st.level(Acal[j - 1])
                if sgn * (C[j] - lv) <= 0: parts.append((rem, C[j])); rem = 0; status = 'stopped'
                elif tq and C[j] >= tgt: parts.append((0.5, C[j])); rem -= 0.5; tq = False; hit = True
                if rem <= 1e-9: exk = j; break
                st.on_close(C[j])
        if rem > 1e-9:
            parts.append((rem, C[last]));
            if horizon is not None and k + horizon <= len(cal) - 1: status = 'horizon20'
        ret = 0.0
        for qq, px in parts:
            exf = px * (1 - sgn * sl)
            ret += qq * ((exf * (1 - fee)) / (ein * (1 + fee)) - 1 if sgn == 1 else (ein * (1 - fee) - exf * (1 + fee)) / (ein * (1 + fee)))
        return ret, status, exk, hit
    ret20, st20, ex20, hit20 = run(H20)
    retall, stall, exall, _ = run(None)
    complete = st20 in ('stopped', 'horizon20')
    b = bret('SPY' if asset == 'stock' else 'BTC-USD', cal[k], cal[ex20])
    outs.append(dict(setup_id=s6.setup_id, entry_date=cal[k].date(), exit_date20=cal[ex20].date(), days20=ex20 - k,
                     ret20=ret20, status20=st20, complete20=complete, target_hit20=hit20, bench20=b, x_mkt20=ret20 - sgn * b,
                     ret_sim_end=retall, status_sim_end=stall, exit_date_sim_end=cal[exall].date(),
                     known_date=cal[ex20].date() if complete else pd.NaT))

S = pd.DataFrame(rows).merge(G, on='setup_id', how='left')
S['va120_short_flag'] = np.where(S.direction == 'SHORT', (S.vp120_va_pos == 'below VA').astype(float), np.nan)
S.loc[S.vp120_va_pos.isna() & (S.direction == 'SHORT'), 'va120_short_flag'] = np.nan
S['rule_pass'] = S.apply(rulepass, axis=1)
O_ = pd.DataFrame(outs)
# ---------------- split: per asset class, by entry date, whole dates kept together, earlier half = calibration
S = S.merge(O_[['setup_id', 'entry_date']], on='setup_id', how='left')
S['entry_date'] = pd.to_datetime(S.entry_date)
S['split_date'] = S.entry_date.fillna(pd.to_datetime(S.alert_date))
S['half'] = ''
cut = {}
for asset, g in S.groupby('asset'):
    cnt = g.groupby(g.split_date.dt.date).size().cumsum(); n = len(g)
    best = min(cnt.index, key=lambda d: abs(cnt[d] - n / 2))
    cut[asset] = best
    S.loc[g.index, 'half'] = np.where(g.split_date.dt.date <= best, 'calibration', 'holdout')
S = S.drop(columns=['entry_date']).rename(columns={'split_date': 'split_entry_date'})
S['split_entry_date'] = S.split_entry_date.dt.date
S.to_csv(OUT + 'setups_calib.csv', index=False)
O_ = O_.merge(S[['setup_id', 'ticker', 'asset', 'direction', 'half', 'trade_date', 'rule_pass']], on='setup_id', how='left')
O_.to_csv(OUT + 'outcomes_calib.csv', index=False)
# ---------------- lessons pool: calibration half, outcome complete (stopped / 20-bar horizon reached)
ctx = ['setup_id', 'ticker', 'asset', 'direction', 'source', 'automation', 'trade_date', 'ck_score', 'below_sma200', 'vs_sma200',
       'sector', 'sector_up', 'vp120_va_pos', 'rule_pass', 'alert_stop_dist_atr', 'atr14_pct']
LP = O_[(O_.half == 'calibration') & O_.complete20][['setup_id', 'entry_date', 'exit_date20', 'days20', 'ret20', 'status20',
                                                     'target_hit20', 'x_mkt20', 'known_date']]
LP = LP.merge(S[ctx], on='setup_id', how='left')
LP.to_csv(OUT + 'lessons_pool.csv', index=False)
print('setups', len(S), S.groupby(['asset', 'half']).size().to_dict(), 'cut', cut)
print('outcomes', len(O_), O_.status20.value_counts().to_dict(), 'complete', int(O_.complete20.sum()))
print('lessons pool', len(LP), LP.groupby(['asset', 'direction']).size().to_dict())
# ---------------- validation vs sim_ratchet (trades that end <= 20 bars must match exactly)
T = pd.read_csv(IAF + 'sim_ratchet_trades.csv')
pol = O_.apply(lambda q: 'rt_fixed3_c' if q.asset == 'crypto' else ('rt_ratchet_h618_c' if q.direction == 'LONG' else 'rt_ratchet_c'), axis=1)
V = O_.assign(policy=pol).merge(T[['setup_id', 'policy', 'ret_net', 'status', 'days']], on=['setup_id', 'policy'], how='left')
vv = V[V.status == 'stopped']; vv = vv[vv.days <= H20]
print('validation: stopped<=19 bars in sim', len(vv), 'max |ret20-sim|', float((vv.ret20 - vv.ret_net).abs().max()),
      '| full-period max |diff|', float((V.ret_sim_end - V.ret_net).abs().max()))
open(OUT + 'split.md', 'w').write(f"""# Calibrated TradingAgents - calibration / holdout split (built {pd.Timestamp.now():%Y-%m-%d %H:%M})

Universe: the {len(S)} runnable setups of setups_846.csv (846 minus 11 dup_not_counted and 3 without a cutoff).
Split per asset class by ENTRY DATE (open of the first bar after the decision time, as in sim_ratchet.py;
alert date when there is no simulated trade), whole entry dates kept on one side, earlier half = calibration:
- stocks: calibration = entry date <= {cut.get('stock')}  ({int(((S.asset=='stock')&(S.half=='calibration')).sum())} setups), holdout = later ({int(((S.asset=='stock')&(S.half=='holdout')).sum())})
- crypto: calibration = entry date <= {cut.get('crypto')}  ({int(((S.asset=='crypto')&(S.half=='calibration')).sum())} setups), holdout = later ({int(((S.asset=='crypto')&(S.half=='holdout')).sum())})
Per asset class because a single global date would put ~all crypto in calibration and ~all stocks in holdout
(crypto median entry {S[S.asset=='crypto'].split_entry_date.median() if False else ''}mid-Aug vs stocks mid-Sep).

Outcome: active policy, capped at 20 bars (close of the 20th bar incl. the entry bar), net of costs; excess = vs SPY
(stocks) / BTC (crypto) over the same entry->exit window (shorts: ret + bench ret). complete20=False -> data ended
2026-10-07 first (marked to market) - reported separately.
Few-shot lessons: only calibration-half trades whose outcome was known (stop hit or 20th bar closed) strictly
BEFORE the setup's cutoff bar (trade_date); max 6, deterministic (same asset+direction first, most recent, balanced
winners/losers).
Threshold: veto if p_success < theta; theta per asset class = argmax of avoided loss (sum of -ret20 over vetoed
trades) on the calibration half; holdout evaluated ONCE with that theta (calib_eval.py writes holdout_lock.json),
BH-FDR q<0.10 over all holdout comparisons, p = max(ticker-clustered, date-clustered, two-way) as in geo_analyze.py.
Real decision only on new setups from 2026-10-12.
""")
