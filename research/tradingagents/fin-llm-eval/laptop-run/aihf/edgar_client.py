"""Point-in-time DataClient for ai-hedge-fund built on SEC EDGAR companyfacts (free, no key)
+ Yahoo daily closes. Replaces the Financial Datasets API (needs a paid/sign-up key).

PIT rules: a fact is used only if its `filed` date <= end_date (as-of), at the vintage current
on that date (latest filing <= as_of for the same period). Market cap at each period = shares
outstanding (as filed) x close on the filing date (<= as_of). Every price/filing date that
enters a snapshot is recorded in self.audit for the leak check.
D/E here = total liabilities / equity (Financial Datasets uses debt/equity) - documented deviation.
"""
from __future__ import annotations
import json, os, time, datetime as dt
from pathlib import Path
import requests, pandas as pd
from hedge_fund.data.models import FinancialMetrics, CompanyFacts

HERE = Path(__file__).resolve().parent
CACHE = HERE.parent / 'results' / 'aihf_cache' / 'sec_edgar'; CACHE.mkdir(parents=True, exist_ok=True)
PX = HERE.parent / 'results' / 'aihf_cache' / 'px'; PX.mkdir(parents=True, exist_ok=True)
UA = os.getenv('SEC_EDGAR_USER_AGENT', 'fin-llm-eval research (contact@example.com)')

def _get(url, name):
    p = CACHE / name
    if p.exists() and time.time() - p.stat().st_mtime < 86400:
        return json.loads(p.read_text())
    r = requests.get(url, headers={'User-Agent': UA}, timeout=30); r.raise_for_status()
    p.write_text(r.text); time.sleep(0.2); return r.json()

def _d(s): return dt.date.fromisoformat(s)

DUR = {'rev': ('RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues', 'SalesRevenueNet', 'RevenueFromContractWithCustomerIncludingAssessedTax'),
       'gp': ('GrossProfit',), 'cogs': ('CostOfRevenue', 'CostOfGoodsAndServicesSold'),
       'op': ('OperatingIncomeLoss',), 'ni': ('NetIncomeLoss', 'ProfitLoss'),
       'ocf': ('NetCashProvidedByUsedInOperatingActivities', 'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations'),
       'capex': ('PaymentsToAcquirePropertyPlantAndEquipment', 'PaymentsToAcquireProductiveAssets')}
INST = {'eq': ('StockholdersEquity', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'),
        'liab': ('Liabilities',), 'ca': ('AssetsCurrent',), 'cl': ('LiabilitiesCurrent',)}
FORMS = {'10-Q', '10-K', '10-Q/A', '10-K/A'}

class EdgarClient:
    def __init__(self):
        self.tickers = {v['ticker'].upper(): str(v['cik_str']).zfill(10) for v in _get('https://www.sec.gov/files/company_tickers.json', 'company_tickers.json').values()}
        self.audit = []
    def _facts(self, ticker):
        cik = self.tickers.get(ticker.upper().replace('.', '-'))
        if not cik: return None
        return _get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json', f'CIK{cik}.json')
    def _series(self, facts, tags, as_of, instant=False):
        """Values at the latest vintage filed <= as_of; date = FIRST filing (when it became public)."""
        g = facts.get('facts', {}).get('us-gaap', {})
        cands = []
        for t in tags:
            if t not in g: continue
            units = g[t]['units']; u = units.get('USD') or next(iter(units.values()))
            rows = [f for f in u if f.get('form') in FORMS and f.get('filed') and _d(f['filed']) <= as_of]
            if rows: cands.append((max(f['end'] for f in rows), -tags.index(t), rows))
        for _, _, rows in sorted(cands, key=lambda c: (c[0], c[1]), reverse=True)[:1]:
            out = {}
            for f in sorted(rows, key=lambda f: f['filed']):
                key = f['end'] if instant else (f['start'], f['end'])
                first = out[key][1] if key in out else f['filed']
                out[key] = (f['val'], first)
            if out: return out
        return {}
    def _quarters(self, s):
        """Discrete quarters: direct 60-115d facts, else differences of year-to-date facts sharing a start."""
        q = {}
        for (st, en), v in s.items():
            if 60 <= (_d(en) - _d(st)).days <= 115: q[en] = v
        by_start = {}
        for (st, en), v in s.items(): by_start.setdefault(st, []).append((en, v))
        for st, lst in by_start.items():
            lst.sort()
            for (e0, v0), (e1, v1) in zip(lst, lst[1:]):
                if e1 not in q and 60 <= (_d(e1) - _d(e0)).days <= 115 and (_d(e1) - _d(st)).days <= 400:
                    q[e1] = (v1[0] - v0[0], v1[1])
        return dict(sorted(q.items()))
    def _ttm(self, q, end):
        ends = [e for e in q if e <= end][-4:]
        if len(ends) < 4 or (_d(ends[-1]) - _d(ends[0])).days > 300 or ends[-1] != end: return None
        return sum(q[e][0] for e in ends)
    def _close(self, ticker, day, as_of):
        p = PX / f'{ticker}.csv'
        if not p.exists():
            import yfinance as yf   # installed with TradingAgents in the same venv
            h = yf.Ticker(ticker).history(start='2018-01-01', end='2026-10-09', auto_adjust=False)
            if h.empty: return None
            h.index = h.index.strftime('%Y-%m-%d'); h[['Close', 'Stock Splits']].to_csv(p)
        h = pd.read_csv(p, index_col=0)
        sp = h['Stock Splits'].replace(0, 1.0)
        hh = h[h.index <= min(day, as_of.isoformat())]
        if hh.empty: return None
        d0 = hh.index[-1]
        raw = float(hh.Close.iloc[-1]) * float(sp[sp.index > d0].prod())   # undo Yahoo's split adjustment -> price that traded
        self.audit.append((ticker, 'price', d0, as_of.isoformat())); return raw
    def _split_factor(self, ticker, after, as_of):
        p = PX / f'{ticker}.csv'
        if not p.exists(): return 1.0
        h = pd.read_csv(p, index_col=0); sp = h['Stock Splits'].replace(0, 1.0)
        return float(sp[(sp.index > after) & (sp.index <= as_of.isoformat())].prod())
    def get_financial_metrics(self, ticker, end_date, period='ttm', limit=10):
        as_of = _d(end_date); facts = self._facts(ticker)
        if not facts: return []
        Q = {k: self._quarters(self._series(facts, tags, as_of)) for k, tags in DUR.items()}
        I = {k: self._series(facts, tags, as_of, instant=True) for k, tags in INST.items()}
        sh = {}
        for f in facts.get('facts', {}).get('dei', {}).get('EntityCommonStockSharesOutstanding', {}).get('units', {}).get('shares', []):
            if f.get('filed') and _d(f['filed']) <= as_of: sh[f['filed']] = f['val']
        rows = []
        for end in sorted(Q['ni'].keys(), reverse=True):
            rev, ni = self._ttm(Q['rev'], end), self._ttm(Q['ni'], end)
            if ni is None: continue
            filed = Q['ni'][end][1]
            gp = self._ttm(Q['gp'], end)
            if gp is None and rev is not None and self._ttm(Q['cogs'], end) is not None: gp = rev - self._ttm(Q['cogs'], end)
            op = self._ttm(Q['op'], end); ocf = self._ttm(Q['ocf'], end); cx = self._ttm(Q['capex'], end)
            eq = I['eq'].get(end, (None,))[0]; li = I['liab'].get(end, (None,))[0]
            ca = I['ca'].get(end, (None,))[0]; cl = I['cl'].get(end, (None,))[0]
            shs = [v for f, v in sorted(sh.items()) if f <= filed]; shares = shs[-1] if shs else None
            px = self._close(ticker, filed, as_of) if shares else None
            mc = px * shares if (px and shares) else None
            if shares: shares = shares * self._split_factor(ticker, filed, as_of)   # per-share on as_of share basis (splits known by as_of)
            prev = [e for e in Q['rev'] if e < end]; rev_prev = None
            if len(prev) >= 4: rev_prev = self._ttm(Q['rev'], prev[-4])
            self.audit.append((ticker, 'filing', filed, as_of.isoformat()))
            div = lambda a, b: (a / b) if (a is not None and b not in (None, 0)) else None
            rows.append(FinancialMetrics(ticker=ticker, report_period=end, period='ttm', currency='USD', filing_date=filed,
                market_cap=mc, price_to_earnings_ratio=div(mc, ni) if ni and ni > 0 else None,
                return_on_equity=div(ni, eq), gross_margin=div(gp, rev), operating_margin=div(op, rev), net_margin=div(ni, rev),
                debt_to_equity=div(li, eq), current_ratio=div(ca, cl),
                revenue_growth=(rev / rev_prev - 1) if (rev and rev_prev) else None,
                earnings_per_share=div(ni, shares), book_value_per_share=div(eq, shares),
                free_cash_flow_per_share=div((ocf - cx) if (ocf is not None and cx is not None) else ocf, shares)))
            if len(rows) >= limit: break
        return rows
    def get_company_facts(self, ticker):
        return None   # sector/industry withheld (latest-only metadata); blind prompts drop it anyway
    def get_prices(self, *a, **k): raise NotImplementedError
    def get_news(self, *a, **k): return []
    def get_insider_trades(self, *a, **k): return []
    def get_earnings(self, *a, **k): return None
