"""Post-mortem entry adjustments (scoring v3, approved by Ilan 16.10.2026 17:18 IL). LOCKED thresholds:
  (a) EARNINGS IN HOLDING WINDOW: SHORT with next earnings within EARN_TD (15) trading days of the scan cutoff -> -8 points.
      Longs unchanged (the existing 5-trading-day earnings block stays for all new stock entries).
  (b) SECTOR RELATIVE STRENGTH: RS = sector ETF 5-session return - SPY 5-session return, closes up to the cutoff (point-in-time).
      SHORT with RS > +1.5% / LONG with RS < -1.5% -> flagged only, WEIGHT 0 (independent validation: no effect). Crypto: n/a.
      (a) confirmed by the same validation (-0.75% gap) -> kept at -8.
  Short penalties (model-credibility vetoes + (a) + (b)) are capped together at -25. Names that fall below trade grade are
  paper-tracked to completion (positions registry, blocked_by_veto = reasons).
Columns (measured by tool_stats like other exp_* tools): exp_adj_earn15_short (flag), exp_adj_td_to_earnings, exp_adj_sector_rs5,
exp_adj_rs_against (flag), exp_adj_penalty_earn, exp_adj_penalty_rs."""
import numpy as np, pandas as pd
EARN_TD, EARN_PTS = 15, 8.0
RS_N, RS_TH, RS_PTS = 5, 0.015, 0.0   # 16.10 17:21: independent S&P 2005-2026 validation found no effect -> weight 0 (column tracked only)
SHORT_TOTAL_CAP = 25.0
_RS = {}
def sector_rs(etf, cut, closes_fn=None):
    k = (etf, str(pd.Timestamp(cut).date()))
    if k not in _RS:
        try:
            if closes_fn: z = closes_fn(cut)
            else:
                import yfinance as yf
                c = pd.Timestamp(cut); c = c.tz_convert('UTC').tz_localize(None) if c.tzinfo else c
                z = yf.download([etf, 'SPY'], start=c - pd.Timedelta(days=30), end=c + pd.Timedelta(days=1), auto_adjust=True, progress=False, threads=False)['Close']
                z = z[z.index <= c.normalize() - pd.Timedelta(days=0 if c.hour >= 20 else 1)]   # stock close visible only after 16:00 ET
            z = z.dropna()
            _RS[k] = float(z[etf].iloc[-1] / z[etf].iloc[-1 - RS_N] - (z['SPY'].iloc[-1] / z['SPY'].iloc[-1 - RS_N]))
        except Exception: _RS[k] = None
    return _RS[k]
def components(c, cut, closes_fn=None):
    td = (c.get('_eg') or {}).get('td_to_earnings')
    try: td = int(td)
    except Exception: td = None
    short = c.get('direction') == 'SHORT'
    earn = bool(short and c.get('asset') != 'crypto' and td is not None and 0 <= td <= EARN_TD)
    rs = sector_rs(c['sector_etf'], cut, closes_fn) if (c.get('asset') != 'crypto' and isinstance(c.get('sector_etf'), str)) else None
    against = bool(rs is not None and ((short and rs > RS_TH) or (not short and rs < -RS_TH)))
    return {'exp_adj_td_to_earnings': td, 'exp_adj_earn15_short': earn, 'exp_adj_sector_rs5': None if rs is None else round(rs, 5),
            'exp_adj_rs_against': against, 'exp_adj_penalty_earn': EARN_PTS if earn else 0.0, 'exp_adj_penalty_rs': RS_PTS if against else 0.0}   # = 0 while RS_PTS is 0
def total_penalty(direction, veto_pts, comp):
    p = veto_pts + comp.get('exp_adj_penalty_earn', 0) + comp.get('exp_adj_penalty_rs', 0)
    return round(min(SHORT_TOTAL_CAP, p) if direction == 'SHORT' else p, 2)
