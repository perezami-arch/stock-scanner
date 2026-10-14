"""shared loader for research_columns tests: trial-run tickers + PIT daily bars from the scanner cache (no network)."""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import sys; sys.path.insert(0, _SCANNER_ROOT)
import pandas as pd
import scanner_momentum as SM, scanner_stops as ST
TRIAL = (_SCANNER_ROOT + '/scan-runs/2026-10-08_1515_trial')
def trial_asof():
    d = pd.read_csv(f'{TRIAL}/scan_raw.csv'); return pd.Timestamp(d.asof_utc.iloc[0]).tz_localize('UTC'), d
def bars(t, asof):
    px = f"{SM.CACHE_ROOT}/{asof.strftime('%Y%m%dT%H%MZ')}"
    b = ST.daily_bars(t, 'stock', asof, px)
    if b is not None: b.attrs['symbol'] = t
    return b
