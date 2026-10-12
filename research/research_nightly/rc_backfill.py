"""Backfill research_columns on the historical tracker setups (IN-SAMPLE baseline only; the decision uses setups from 12.10).
Setups: tracker/setups-point-in-time-2026-10-08.csv (cutoff_minute_utc = the PIT cutoff of each alert; read-only).
Bars: iaf/frames.pkl (daily, through 2026-10-07; research_columns cuts each frame at the cutoff itself).
Output: research-models/backfill/rc_backfill_setups.csv keyed by (ticker, alert_date, direction) -> usable as tool_stats --extra."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import sys, os, time, pandas as pd
sys.path.insert(0, _SCANNER_ROOT)
import research_columns as RC
OUT = (_SCANNER_ROOT + '/research-models/backfill'); os.makedirs(OUT, exist_ok=True)
S = pd.read_csv((_SCANNER_ROOT + '/tracker/setups-point-in-time-2026-10-08.csv'))
S = S[S.direction.isin(['LONG', 'SHORT']) & (S.cutoff_minute_utc.notna() | S.cutoff_bar_date.notna())].drop_duplicates(['ticker', 'alert_date', 'direction'])
F = pd.read_pickle((_SCANNER_ROOT + '/trading-frameworks-eval/iaf/frames.pkl'))
tools = [t for t in RC.REGISTRY if t not in ('qlib', 'finrl')]
items = []
for r in S.itertuples():
    cr = r.asset_class == 'crypto'; k = (r.ticker, cr)
    if k not in F: continue
    df = F[k].dropna(subset=['Close']).astype(float)
    if pd.notna(r.cutoff_minute_utc):
        c = pd.Timestamp(r.cutoff_minute_utc); c = c.tz_localize('UTC') if c.tzinfo is None else c
    else:   # stocks/ETFs: the cutoff bar itself is the last visible bar -> its 16:00 ET close
        c = (pd.Timestamp(r.cutoff_bar_date) + pd.Timedelta(hours=16)).tz_localize('America/New_York')
    items.append(((r.ticker, str(r.alert_date)[:10], r.direction), df, c, 'crypto' if cr else 'stock', r.direction, r.ticker))
print('setups', len(S), 'with frames', len(items), flush=True)
RC.reset_budget(7200); t0 = time.time()
rows = RC.compute_many(items, tools=tools, workers=int(os.environ.get('W', '2')))
X = pd.DataFrame(rows); X[['ticker', 'alert_date', 'direction']] = pd.DataFrame(X.pop('key').tolist(), index=X.index)
X.to_csv(f'{OUT}/rc_backfill_setups.csv', index=False)
print('done', round(time.time() - t0), 's', RC.status_summary(rows))
