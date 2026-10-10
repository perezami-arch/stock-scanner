"""Table of the manual 20-setup TradingAgents run (laptop, 2026-10-08 15:19-) vs active-policy outcomes."""
import json, sys, numpy as np, pandas as pd
sys.path.insert(0, '/workspace/ta-calib')
res = [json.loads(l) for l in open(sys.argv[1], encoding='utf-8') if l.strip()]
R = pd.DataFrame(res); R = R[R.finished_at >= '2026-10-08T15:19'].drop_duplicates('setup_id', keep='last')
O = pd.read_csv('/workspace/ta-calib/outcomes_calib.csv')
T = pd.read_csv('/workspace/trading-frameworks-eval/iaf/sim_ratchet_trades.csv')
T['want'] = np.where(T.asset == 'crypto', 'rt_fixed3_c', np.where(T.direction == 'LONG', 'rt_ratchet_h618_c', 'rt_ratchet_c'))
T = T[T.policy == T.want][['setup_id', 'entry_date', 'exit_date', 'status', 'ret_net', 'days']]
IAF = '/workspace/trading-frameworks-eval/iaf/'
F = pd.read_pickle(IAF + 'frames.pkl'); B = pd.read_pickle(IAF + 'bench_yf.pkl')
def bser(t):
    x = F[(t, True)] if t == 'BTC-USD' else B[t][['Open', 'Close']].dropna()
    x = x.copy(); x.index = pd.to_datetime(x.index); return x
BS = {t: bser(t) for t in ('SPY', 'BTC-USD')}
def bret(t, e, x):
    s = BS[t]; o = s.Open[s.index >= pd.Timestamp(e)]; c = s.Close[s.index <= pd.Timestamp(x)]
    return c.iloc[-1] / o.iloc[0] - 1 if len(o) and len(c) else np.nan
POS, NEG = {'Buy', 'Overweight'}, {'Sell', 'Underweight'}
X = R[['setup_id', 'ticker', 'asset', 'direction', 'trade_date', 'decision', 'ok']].merge(T, on='setup_id', how='left')
def stance(r):
    d = str(r.decision)
    if d in POS: return 'agree' if r.direction == 'LONG' else 'oppose'
    if d in NEG: return 'agree' if r.direction == 'SHORT' else 'oppose'
    return 'neutral'
X['stance'] = X.apply(stance, axis=1)
X['bench'] = np.where(X.asset == 'crypto', 'BTC', 'SPY')
X['x_mkt'] = [r.ret_net - (1 if r.direction == 'LONG' else -1) * bret('BTC-USD' if r.asset == 'crypto' else 'SPY', r.entry_date, r.exit_date)
              if pd.notna(r.ret_net) else np.nan for r in X.itertuples()]
X['ret_pct'] = (X.ret_net * 100).round(1); X['x_pct'] = (X.x_mkt * 100).round(1)
X['status'] = X.status.map({'stopped': 'stopped', 'open@end': 'open'}).fillna(X.status)
cols = ['setup_id', 'ticker', 'trade_date', 'direction', 'decision', 'stance', 'ret_pct', 'x_pct', 'bench', 'status', 'days', 'exit_date']
print(X[cols].to_string(index=False))
print()
for s, g in X.groupby('stance'):
    print(f"{s:8s} N={len(g):2d} mean={g.ret_net.mean()*100:+.2f}% median={g.ret_net.median()*100:+.2f}% hit={(g.ret_net>0).mean()*100:.0f}% x_mkt={g.x_mkt.mean()*100:+.2f}%  stopped={int((g.status=='stopped').sum())}")
print(f"ALL      N={len(X)} mean={X.ret_net.mean()*100:+.2f}%  x_mkt={X.x_mkt.mean()*100:+.2f}%")
X[cols].to_csv('/workspace/ta-calib/table20.csv', index=False)
