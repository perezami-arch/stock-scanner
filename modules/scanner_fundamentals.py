"""scanner_fundamentals.py - LOGGED-ONLY (score weight 0) point-in-time fundamentals for Ilan's US stock scanner.
Added 2026-10-08 at Ilan's request (group chat: "סור גם פן פונדמנטלי פי אי וכל מה שנגזר").
Weight is ZERO under memory/stock-scanner/out-of-sample-rule-2026-10-08.txt. Nothing here feeds the score.

Source: SEC EDGAR free APIs (no key). company_tickers.json (ticker -> CIK) + data.sec.gov companyfacts (every fact with
the filing it came from: start/end/val/form/filed/accn). The 'frames' API is NOT used (it returns only the latest version).

Binding PIT rules (research team, 08.10.2026):
 R1  Per fiscal period, use the value with the LATEST 'filed' date STRICTLY BEFORE the alert date (filed < alert_date, never
     the same day, regardless of alert time). 10-K/A, 10-Q/A filed before the alert are allowed.
 R2  Quarterly values by duration only (3-month = 80-100 days); never mix 3-month with YTD. Q4 = FY (~365d, 10-K) - 9M YTD
     (~270d, Q3 10-Q), each picked under R1. For cash-flow items (YTD-only in 10-Qs) Q2 = H1 - Q1, Q3 = 9M - H1 the same way.
 R3  TTM EPS <= 0 -> pe_ttm empty + flag (never negative), excluded from the sector percentile. Same for EV/EBITDA with
     EBITDA <= 0 and PEG with EPS growth <= 0.
 R4  Multiples use the close at the cutoff bar (stocks: alert before 16:00 ET -> previous close) and the share count reported
     in the latest filing satisfying R1 (dei:EntityCommonStockSharesOutstanding, else weighted-average diluted shares).
     If a stock split went ex between that filing and the cutoff (public at the cutoff), shares/EPS are split-adjusted + flag.
 R5  SEC requests: User-Agent with e-mail, <= 8 req/s, cache under /workspace/fundamentals-cache/.

Units: *_ttm/debt/cash/equity in USD; growth, margins, roe, fcf_yield as FRACTIONS (0.12 = 12%); peg = pe / (EPS growth in %).
Import-safe (no network on import).
"""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, json, gzip, time, threading, datetime as dt
import numpy as np, pandas as pd

UA = os.environ.get('SEC_EDGAR_UA', 'Ilan Perets scanner perezami@icloud.com')
CACHE = (_SCANNER_ROOT + '/fundamentals-cache')
MIN_INTERVAL = 0.125          # <= 8 requests / second (SEC limit is 10)
FORMS_Q = {'10-Q', '10-Q/A'}; FORMS_K = {'10-K', '10-K/A', '20-F', '20-F/A', '40-F', '40-F/A', '10-KT', '10-KT/A'}
FORMS = FORMS_Q | FORMS_K
Q_DAYS, H_DAYS, M9_DAYS, FY_DAYS = (80, 100), (160, 195), (245, 290), (340, 380)
Q4_GAP = (80, 120)   # FY end - 9M end (16-week Q4 retailers); the derived Q4 is still FY - 9M (R2)

# concept -> ordered alternative tags ("taxonomy:tag"); first = preferred
DUR = {
 'rev':   ['us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax', 'us-gaap:Revenues', 'us-gaap:SalesRevenueNet',
           'us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax', 'us-gaap:RevenuesNetOfInterestExpense',
           'us-gaap:SalesRevenueGoodsNet', 'ifrs-full:Revenue', 'ifrs-full:RevenueFromContractsWithCustomers'],
 'cogs':  ['us-gaap:CostOfRevenue', 'us-gaap:CostOfGoodsAndServicesSold', 'us-gaap:CostOfGoodsSold', 'ifrs-full:CostOfSales'],
 'gp':    ['us-gaap:GrossProfit', 'ifrs-full:GrossProfit'],
 'op':    ['us-gaap:OperatingIncomeLoss', 'ifrs-full:ProfitLossFromOperatingActivities'],
 'ni':    ['us-gaap:NetIncomeLoss', 'us-gaap:NetIncomeLossAvailableToCommonStockholdersBasic', 'us-gaap:ProfitLoss',
           'ifrs-full:ProfitLossAttributableToOwnersOfParent', 'ifrs-full:ProfitLoss'],
 'eps':   ['us-gaap:EarningsPerShareDiluted', 'us-gaap:EarningsPerShareBasicAndDiluted', 'ifrs-full:DilutedEarningsLossPerShare'],
 'eps_b': ['us-gaap:EarningsPerShareBasic', 'ifrs-full:BasicEarningsLossPerShare'],
 'da':    ['us-gaap:DepreciationDepletionAndAmortization', 'us-gaap:DepreciationAndAmortization',
           'us-gaap:DepreciationAmortizationAndAccretionNet', 'us-gaap:Depreciation', 'ifrs-full:DepreciationAndAmortisationExpense'],
 'ocf':   ['us-gaap:NetCashProvidedByUsedInOperatingActivities', 'us-gaap:NetCashProvidedByUsedInOperatingActivitiesContinuingOperations',
           'ifrs-full:CashFlowsFromUsedInOperatingActivities'],
 'capex': ['us-gaap:PaymentsToAcquirePropertyPlantAndEquipment', 'us-gaap:PaymentsToAcquireProductiveAssets',
           'us-gaap:PaymentsForCapitalImprovements', 'ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities'],
 'wdil':  ['us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding', 'ifrs-full:AdjustedWeightedAverageShares'],
}
INST = {
 'eq':    ['us-gaap:StockholdersEquity', 'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
           'ifrs-full:EquityAttributableToOwnersOfParent', 'ifrs-full:Equity'],
 'cash':  ['us-gaap:CashAndCashEquivalentsAtCarryingValue', 'us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents',
           'us-gaap:Cash', 'ifrs-full:CashAndCashEquivalents'],
 'ltd_total': ['us-gaap:LongTermDebt', 'us-gaap:DebtAndCapitalLeaseObligations', 'us-gaap:LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities'],
 'ltd_nc': ['us-gaap:LongTermDebtNoncurrent', 'us-gaap:LongTermDebtAndCapitalLeaseObligations', 'ifrs-full:NoncurrentPortionOfNoncurrentBorrowings'],
 'ltd_c':  ['us-gaap:LongTermDebtCurrent', 'us-gaap:DebtCurrent', 'us-gaap:LongTermDebtAndCapitalLeaseObligationsCurrent',
            'ifrs-full:CurrentPortionOfNoncurrentBorrowings'],
 'std':    ['us-gaap:ShortTermBorrowings', 'us-gaap:CommercialPaper', 'ifrs-full:ShorttermBorrowings'],
}
DEI_SHARES = 'dei:EntityCommonStockSharesOutstanding'
# holding-company reorganisations: the ticker's new CIK has only recent filings -> also read the predecessor registrant's facts
PREDECESSOR_CIK = {'XOM': [34088]}     # ExxonMobil Holdings Corp (2115436, 2026) <- Exxon Mobil Corp (34088)

COLS = ['fund_alert_date', 'fund_cutoff_date', 'fund_period_end', 'fund_last_filed', 'fund_data_age_days', 'fund_price',
        'fund_shares', 'fund_shares_src', 'fund_mcap_b', 'eps_ttm', 'revenue_ttm', 'net_income_ttm', 'op_income_ttm',
        'gross_profit_ttm', 'ebitda_ttm', 'fcf_ttm', 'total_debt', 'cash', 'equity',
        'pe_ttm', 'ps_ttm', 'pb', 'ev_ebitda', 'fcf_yield', 'peg', 'rev_growth_yoy', 'eps_growth_yoy',
        'gross_margin', 'op_margin', 'roe', 'debt_to_equity', 'fund_currency', 'fund_flag']
SECTOR_COLS = ['fund_sector_etf', 'pe_sector_pctile', 'pe_sector_n']
LIVE_COLS = ['forward_pe_live', 'next_earnings_date_live']
# tracker (build7) keys + Hebrew headers, all LOGGED ONLY
TRACKER_KEYS = ['pe_ttm', 'ps_ttm', 'pb', 'ev_ebitda', 'fcf_yield', 'peg', 'rev_growth_yoy', 'eps_growth_yoy', 'gross_margin',
                'op_margin', 'roe', 'debt_to_equity', 'pe_sector_pctile', 'eps_ttm', 'fund_mcap_b', 'fund_period_end',
                'fund_last_filed', 'fund_data_age_days', 'fund_flag', 'forward_pe_live', 'next_earnings_date_live']
TRACKER_HEAD = ['מכפיל רווח 12ח', 'מכפיל מכירות 12ח', 'מכפיל הון', 'EV/EBITDA', 'תשואת תזרים חופשי', 'PEG',
                'צמיחת הכנסות שנתית', 'צמיחת רווח למניה שנתית', 'שולי רווח גולמי', 'שולי רווח תפעולי', 'תשואה על ההון',
                'חוב להון', 'אחוזון מכפיל רווח בסקטור', 'רווח למניה 12ח', 'שווי שוק לפי דוח ($B)', 'סוף תקופת הדוח',
                'תאריך הגשת הדוח האחרון', 'גיל הנתון (ימים)', 'הערת נתונים פונדמנטליים', 'מכפיל רווח צפוי (חי בלבד)',
                'מועד הדוח הבא (חי בלבד)']
TRACKER_HEAD = [h + ' (נרשם בלבד)' for h in TRACKER_HEAD]

# ------------------------------------------------------------------ SEC access (rate-limited, cached)
_lock = threading.Lock(); _last = [0.0]
def _get(url):
    import requests
    with _lock:
        w = MIN_INTERVAL - (time.time() - _last[0])
        if w > 0: time.sleep(w)
        _last[0] = time.time()
    for k in range(4):
        r = requests.get(url, headers={'User-Agent': UA, 'Accept-Encoding': 'gzip, deflate'}, timeout=60)
        if r.status_code == 429 or r.status_code >= 500: time.sleep(2 * (k + 1)); continue
        return r
    return r

_TMAP = None
def cik_map(max_age_days=7):
    global _TMAP
    if _TMAP is not None: return _TMAP
    os.makedirs(CACHE, exist_ok=True); p = f'{CACHE}/company_tickers.json'
    if not os.path.exists(p) or time.time() - os.path.getmtime(p) > max_age_days * 86400:
        try:
            r = _get('https://www.sec.gov/files/company_tickers.json'); r.raise_for_status(); open(p, 'w').write(r.text)
        except Exception:
            if not os.path.exists(p): raise
    _TMAP = {v['ticker'].upper(): int(v['cik_str']) for v in json.load(open(p)).values()}
    return _TMAP

def cik_for(symbol):
    m = cik_map(); s = symbol.upper()
    return m.get(s) or m.get(s.replace('.', '-')) or m.get(s.replace('-', '.'))

_FACTS = {}
def _cik_facts(cik, max_age_days):
    if cik in _FACTS: return _FACTS[cik]
    p = f'{CACHE}/CIK{cik:010d}.json.gz'
    if not os.path.exists(p) or time.time() - os.path.getmtime(p) > max_age_days * 86400:
        try:
            r = _get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json')
            if r.status_code == 404: _FACTS[cik] = None; return None
            r.raise_for_status(); gzip.open(p, 'wb').write(r.content)
        except Exception:
            if not os.path.exists(p): raise
    j = json.loads(gzip.open(p).read())
    recs = []
    for tax in ('us-gaap', 'ifrs-full', 'dei'):
        for tag, body in j.get('facts', {}).get(tax, {}).items():
            for unit, lst in body.get('units', {}).items():
                for f in lst:
                    recs.append((f'{tax}:{tag}', unit, f.get('start'), f['end'], f['val'], f.get('filed'), f.get('form'), f.get('accn')))
    df = pd.DataFrame(recs, columns=['tag', 'unit', 'start', 'end', 'val', 'filed', 'form', 'accn'])
    df = df[df['filed'].notna()]
    for c in ('start', 'end', 'filed'): df[c] = pd.to_datetime(df[c], errors='coerce')
    df['days'] = (df['end'] - df['start']).dt.days
    df = df[df['form'].isin(FORMS) | df['tag'].str.startswith('dei:')].reset_index(drop=True)
    _FACTS[cik] = df
    return df

def facts_df(symbol, max_age_days=1.0):
    """Long frame of every us-gaap/ifrs-full/dei fact: tag (taxonomy:tag), unit, start, end, val, filed, form, accn.
    Cache: raw gzip json per CIK (refreshed when older than max_age_days; old filings never change, so a newer cache is
    still PIT-safe because every lookup filters by filed < alert_date). Predecessor CIKs (PREDECESSOR_CIK) are appended."""
    cik = cik_for(symbol)
    if cik is None: return None
    parts = [x for x in [_cik_facts(c, max_age_days) for c in [cik] + PREDECESSOR_CIK.get(symbol.upper(), [])] if x is not None]
    if not parts: return None
    return parts[0] if len(parts) == 1 else pd.concat(parts, ignore_index=True)

# ------------------------------------------------------------------ PIT series
_GROUPS = {}
class _View:
    """Facts of one symbol grouped by tag, filtered lazily to filed < alert (R1)."""
    def __init__(self, symbol, F, alert):
        k = (symbol.upper(), id(F))
        if k not in _GROUPS: _GROUPS.clear() if len(_GROUPS) > 64 else None; _GROUPS[k] = {t: g for t, g in F.groupby('tag', sort=False)}
        self.g, self.alert, self._c = _GROUPS[k], alert, {}
    def get(self, tag):
        if tag not in self._c:
            d = self.g.get(tag)
            self._c[tag] = d[d['filed'] < self.alert] if d is not None else None
        d = self._c[tag]
        return d if d is not None and len(d) else None
    def has_financials(self):
        return any(self.get(t) is not None for t in self.g if not t.startswith('dei:'))
def _latest_vintage(d):
    """R1: per (start, end) keep the row with the latest filed date (d is already filtered filed < alert_date)."""
    if d.empty: return d
    d = d.sort_values(['filed', 'accn']).drop_duplicates(['start', 'end'], keep='last')
    return d

def _pick_unit(d):
    if d.empty: return d, None
    last = d.groupby('unit')['end'].max(); top = last[last == last.max()].index.tolist()
    us = [u for u in top if u in ('USD', 'USD/shares', 'shares')]
    u = us[0] if us else top[0]
    return d[d['unit'] == u], u

def _dur_series(F, concept, audit=None):
    """Merged duration facts for a concept. Primary tag = the alternative with the most recent period end (tie -> list
    order); periods it lacks are filled from the next alternatives. Returns frame start,end,days,val,filed,form,tag + unit."""
    parts = []; unit = None
    cands = []
    for i, t in enumerate(DUR[concept]):
        d = F.get(t)
        if d is None: continue
        d = d[d['start'].notna()]
        if d.empty: continue
        d, u = _pick_unit(d); d = _latest_vintage(d)
        cands.append((d['end'].max(), -i, t, u, d))
    if not cands: return pd.DataFrame(), None
    cands.sort(key=lambda c: (c[0], c[1]), reverse=True)
    unit = cands[0][3]
    seen = set()
    for _, _, t, u, d in cands:
        if u != unit: continue
        if seen: d = d[[k not in seen for k in zip(d['start'], d['end'])]]
        seen |= set(zip(d['start'], d['end'])); parts.append(d)
    return pd.concat(parts).sort_values('end'), unit

def _inrange(x, rg): return rg[0] <= x <= rg[1]

def _quarters(s):
    """R2: discrete quarters {end: (val, filed, how)} - direct 80-100d facts, else YTD differences with the same start
    (H1-Q1, 9M-H1, FY-9M). Components each carry their own R1 vintage; derived filed = max of components."""
    if s is None or len(s) == 0: return {}
    q = {}
    for r in s.itertuples():
        if _inrange(r.days, Q_DAYS): q[r.end] = (float(r.val), r.filed, 'direct', ((r.tag, r.start, r.end, r.filed, r.form),))
    by_start = {}
    for r in s.itertuples(): by_start.setdefault(r.start, []).append(r)
    for st, lst in by_start.items():
        lst = sorted(lst, key=lambda r: r.end)
        for a in lst:
            for b in lst:
                if b.end <= a.end or b.end in q: continue
                pair = (_inrange(a.days, Q_DAYS) and _inrange(b.days, H_DAYS)) or (_inrange(a.days, H_DAYS) and _inrange(b.days, M9_DAYS)) \
                       or (_inrange(a.days, M9_DAYS) and _inrange(b.days, FY_DAYS))
                gap_ok = _inrange((b.end - a.end).days, Q4_GAP if _inrange(b.days, FY_DAYS) else Q_DAYS)
                if pair and gap_ok:
                    how = 'FY-9M' if _inrange(b.days, FY_DAYS) else ('9M-H1' if _inrange(b.days, M9_DAYS) else 'H1-Q1')
                    q[b.end] = (float(b.val) - float(a.val), max(a.filed, b.filed), how,
                                ((a.tag, a.start, a.end, a.filed, a.form), (b.tag, b.start, b.end, b.filed, b.form)))
    return dict(sorted(q.items()))

def _ttm(q, s, end=None):
    """Sum of 4 contiguous discrete quarters ending at `end` (default latest). Fallback: FY fact ending at `end`."""
    if end is None:
        ends = list(q.keys()) + ([r.end for r in s.itertuples() if _inrange(r.days, FY_DAYS)] if len(s) else [])
        if not ends: return None
        end = max(ends)
    ks = [e for e in q if e <= end][-4:]
    if len(ks) == 4 and ks[-1] == end and all(_inrange((b - a).days, (80, 120)) for a, b in zip(ks, ks[1:])) and (ks[-1] - ks[0]).days <= 300:
        return dict(val=sum(q[k][0] for k in ks), end=end, filed=max(q[k][1] for k in ks), basis='4Q',
                    facts=[f for k in ks for f in q[k][3]])
    if len(s):
        ytd = s[(s['end'] == end) & (s['days'].between(*H_DAYS) | s['days'].between(*M9_DAYS) | s['days'].between(*Q_DAYS))]
        for y in ytd.sort_values('days', ascending=False).itertuples():
            fyp = s[s['days'].between(*FY_DAYS) & ((s['end'] - y.start).dt.days.abs() <= 3)]
            prv = s[((s['days'] - y.days).abs() <= 7) & (((end - s['end']).dt.days - 364).abs() <= 10)]
            if len(fyp) and len(prv):
                a, b = fyp.iloc[-1], prv.iloc[-1]
                return dict(val=float(a['val']) + float(y.val) - float(b['val']), end=end, filed=max(a['filed'], y.filed, b['filed']),
                            basis='FY+YTD-prevYTD', facts=[(a['tag'], a['start'], a['end'], a['filed'], a['form']),
                            (y.tag, y.start, y.end, y.filed, y.form), (b['tag'], b['start'], b['end'], b['filed'], b['form'])])
        fy = s[(s['end'] == end) & s['days'].between(*FY_DAYS)]
        if len(fy):
            r = fy.iloc[-1]
            return dict(val=float(r['val']), end=end, filed=r['filed'], basis='FY',
                        facts=[(r['tag'], r['start'], r['end'], r['filed'], r['form'])])
    return None

def _ttm_prev(q, s, end):
    """TTM ending ~1 year before `end` (period end within 365 +/- 20 days earlier)."""
    cands = sorted(set(list(q.keys()) + ([r.end for r in s.itertuples() if _inrange(r.days, FY_DAYS)] if len(s) else [])))
    cands = [e for e in cands if 345 <= (end - e).days <= 385]
    for e in sorted(cands, key=lambda e: abs((end - e).days - 365)):
        t = _ttm(q, s, e)
        if t: return t
    return None

def _inst(F, concept, at=None):
    """Instant value under R1: latest end (or exactly `at`), latest vintage. Returns (val, end, filed, tag, form, unit)."""
    best = None
    for i, t in enumerate(INST[concept]):
        d = F.get(t)
        if d is None: continue
        d = d[d['start'].isna()]
        if d.empty: continue
        d, u = _pick_unit(d)
        d = d.sort_values(['filed', 'accn']).drop_duplicates(['end'], keep='last')
        if at is not None: d = d[d['end'] == at]
        if d.empty: continue
        r = d.sort_values('end').iloc[-1]
        c = (r['end'], -i, float(r['val']), r['filed'], t, r['form'], u)
        if best is None or (c[0], c[1]) > (best[0], best[1]): best = c
    if best is None: return None
    return dict(val=best[2], end=best[0], filed=best[3], tag=best[4], form=best[5], unit=best[6])

def _wdil(F):
    s, _ = _dur_series(F, 'wdil')
    if not len(s): return None
    s = s.sort_values('end'); qq = s[s['days'].between(*Q_DAYS)]; fy = s[s['days'].between(*FY_DAYS)]
    cand = [x.iloc[-1] for x in (qq, fy) if len(x)]
    if not cand: return None
    r = max(cand, key=lambda r: r['end'])
    return dict(val=float(r['val']), filed=r['filed'], end=r['end'], src='weighted diluted', tag=r['tag'], form=r['form'])

def _shares(F, alert=None):
    """R4: dei cover-page shares from the latest filing (multi-class rows of the same filing summed), else latest weighted-
    average diluted shares. dei is rejected (-> weighted diluted, flagged) if <= 0, filed > 400 days before the alert, or
    outside 0.5-2x the weighted diluted count (one share class only / bad tag)."""
    w = _wdil(F)
    d = F.get(DEI_SHARES)
    if d is not None and len(d):
        last = d.sort_values(['filed', 'end']).iloc[-1]
        g = d[(d['accn'] == last['accn']) & (d['end'] == last['end'])].drop_duplicates(['val'])
        v = float(g['val'].sum())
        ok = v > 0 and (alert is None or (alert - last['filed']).days <= 400) and (w is None or 0.5 <= v / w['val'] <= 2.0)
        if ok: return dict(val=v, filed=last['filed'], end=last['end'], src='dei cover', tag=DEI_SHARES, form=last['form'])
        if w: w = dict(w, src='weighted diluted (dei rejected)')
    return w

# ------------------------------------------------------------------ splits (public at the cutoff)
_SPLITS = {}
def splits(symbol):
    if symbol in _SPLITS: return _SPLITS[symbol]
    p = f'{CACHE}/splits.json'
    db = json.load(open(p)) if os.path.exists(p) else {}
    if symbol not in db:
        try:
            import yfinance as yf
            sp = yf.Ticker(symbol).splits
            db[symbol] = {str(k.date()): float(v) for k, v in sp.items() if float(v) > 0}
        except Exception:
            db[symbol] = {}
        try: json.dump(db, open(p, 'w'))
        except Exception: pass
    _SPLITS[symbol] = {pd.Timestamp(k): v for k, v in db[symbol].items()}
    return _SPLITS[symbol]

def split_factor(symbol, after, upto):
    """Product of split ratios with ex-date in (after, upto]."""
    f = 1.0
    for d, v in splits(symbol).items():
        if after < d <= upto: f *= v
    return f

# ------------------------------------------------------------------ main
def _nan(): return float('nan')
def _safe(a, b):
    try:
        if a is None or b is None or not np.isfinite(a) or not np.isfinite(b) or b == 0: return _nan()
        return float(a) / float(b)
    except Exception: return _nan()

def empty_row(flag, alert_date=None, cutoff_date=None):
    r = {c: None for c in COLS}; r['fund_flag'] = flag
    r['fund_alert_date'] = str(alert_date)[:10] if alert_date is not None else None
    r['fund_cutoff_date'] = str(cutoff_date)[:10] if cutoff_date is not None else None
    return r

def fundamentals_pit(symbol, cutoff_date, price_at_cutoff, alert_date=None, asset='stock', audit=None, max_age_days=1.0):
    """PIT fundamentals for one US stock.
    cutoff_date: date of the cutoff bar (price_at_cutoff = its close, split-adjusted as of the cutoff, i.e. the real quote).
    alert_date: calendar date of the alert (R1: only filings with filed < alert_date). Default = cutoff_date + 1 day.
    audit: optional list; every fact used is appended as dict(concept, tag, start, end, filed, form) for the look-ahead check."""
    cutoff = pd.Timestamp(str(cutoff_date)[:10])
    alert = pd.Timestamp(str(alert_date)[:10]) if alert_date is not None else cutoff + pd.Timedelta(days=1)
    if asset != 'stock' or str(symbol).endswith('.TA') or str(symbol).upper().endswith('-USD'):
        return empty_row('no EDGAR coverage', alert, cutoff)
    try:
        F0 = facts_df(symbol, max_age_days=max_age_days)
    except Exception as e:
        return empty_row(f'EDGAR fetch failed: {e.__class__.__name__}', alert, cutoff)
    if F0 is None: return empty_row('no EDGAR coverage (no CIK / no XBRL facts)', alert, cutoff)
    F = _View(symbol, F0, alert)                                        # R1 (strict): filed < alert_date
    if not F.has_financials(): return empty_row('no XBRL financial facts filed before the alert', alert, cutoff)
    flags = []; used = []
    def use(concept, facts):
        for f in facts: used.append(dict(concept=concept, tag=f[0], start=f[1], end=f[2], filed=f[3], form=f[4]))
    S, Q, U = {}, {}, {}
    for c in ('rev', 'cogs', 'gp', 'op', 'ni', 'eps', 'da', 'ocf', 'capex'):
        S[c], U[c] = _dur_series(F, c); Q[c] = _quarters(S[c])
    if not len(S['eps']):
        S['eps'], U['eps'] = _dur_series(F, 'eps_b'); Q['eps'] = _quarters(S['eps'])
        if len(S['eps']): flags.append('EPS basic (no diluted tag)')
    # anchor period = latest TTM end of revenue/net income
    T = {}
    anchor = None
    for c in ('ni', 'rev', 'eps'):
        t = _ttm(Q[c], S[c]) if len(S[c]) else None
        if t and (anchor is None or t['end'] > anchor): anchor = t['end']
    if anchor is None: return empty_row('no TTM income data before the alert', alert, cutoff)
    for c in ('rev', 'cogs', 'gp', 'op', 'ni', 'eps', 'da', 'ocf', 'capex'):
        T[c] = _ttm(Q[c], S[c], anchor) if len(S[c]) else None
        if T[c]: use(c, T[c]['facts'])
    if any(T[c] and T[c]['basis'] == 'FY' for c in ('rev', 'ni', 'eps')): flags.append('TTM = fiscal year (no quarterly XBRL)')
    if (alert - anchor).days > 200: flags.append(f'stale: latest TTM period ends {anchor.date()}')
    cur = next((U[c] for c in ('rev', 'ni', 'op') if U[c]), 'USD')
    if T['eps'] is None and T['ni'] is not None:
        w = _wdil(F)
        if w and w['val'] > 0 and abs((w['end'] - anchor).days) <= 5:
            T['eps'] = dict(val=T['ni']['val'] / w['val'], end=anchor, filed=max(T['ni']['filed'], w['filed']), basis='NI/shares', facts=[])
            used.append(dict(concept='eps_from_wdil', tag=w['tag'], start=None, end=w['end'], filed=w['filed'], form=w['form']))
            flags.append('EPS = TTM net income / diluted shares (no EPS tag for the period)')
    v = lambda c: T[c]['val'] if T[c] else None
    rev, ni, op, eps = v('rev'), v('ni'), v('op'), v('eps')
    gp = v('gp')
    if gp is None and rev is not None and v('cogs') is not None: gp = rev - v('cogs'); flags.append('gross profit = rev - cost of revenue')
    ebitda = (op + v('da')) if (op is not None and v('da') is not None) else None
    fcf = (v('ocf') - abs(v('capex'))) if (v('ocf') is not None and v('capex') is not None) else None
    # balance sheet at the latest equity date
    eqd = _inst(F, 'eq'); bs_end = eqd['end'] if eqd else None
    equity = eqd['val'] if eqd else None
    if eqd: used.append(dict(concept='eq', tag=eqd['tag'], start=None, end=eqd['end'], filed=eqd['filed'], form=eqd['form']))
    def inst_at(c):
        x = _inst(F, c, at=bs_end) if bs_end is not None else None
        if x: used.append(dict(concept=c, tag=x['tag'], start=None, end=x['end'], filed=x['filed'], form=x['form']))
        return x['val'] if x else None
    cash = inst_at('cash')
    ltd_t, ltd_nc, ltd_c, std = inst_at('ltd_total'), inst_at('ltd_nc'), inst_at('ltd_c'), inst_at('std')
    if ltd_t is not None: debt = ltd_t + (std or 0.0)
    elif any(x is not None for x in (ltd_nc, ltd_c, std)): debt = (ltd_nc or 0.0) + (ltd_c or 0.0) + (std or 0.0)
    else: debt = None
    if debt is None and bs_end is not None: flags.append('no debt tag (debt treated as missing)')
    # shares (R4)
    sh = _shares(F, alert)
    shares = sh['val'] if sh else None
    if sh: used.append(dict(concept='shares', tag=sh['tag'], start=None, end=sh['end'], filed=sh['filed'], form=sh['form']))
    # splits between the filings and the cutoff (known at the cutoff)
    eps_adj = eps
    if shares is not None:
        f = split_factor(symbol, sh['filed'], cutoff)
        if f != 1.0: shares *= f; flags.append(f'shares split-adjusted x{f:g} (split after filing)')
    if eps is not None and T['eps']:
        f = split_factor(symbol, T['eps']['filed'], cutoff)
        if f != 1.0: eps_adj = eps / f; flags.append(f'EPS split-adjusted /{f:g}')
    px = float(price_at_cutoff) if price_at_cutoff is not None and np.isfinite(float(price_at_cutoff)) else None
    usd = (cur == 'USD')
    if not usd: flags.append(f'reports in {cur}: price multiples not computed')
    inc_forms = {f[4] for c in ('rev', 'ni', 'eps') if T[c] for f in T[c]['facts']}
    if inc_forms and not (inc_forms & (FORMS_Q | {'10-K', '10-K/A', '10-KT', '10-KT/A'})):
        usd = False; flags.append('foreign filer (20-F/40-F, ADR ratio unknown): price multiples not computed')
    mcap = px * shares if (px and shares and usd) else None
    if mcap is None and usd: flags.append('no price or share count: price multiples not computed')
    ev = (mcap + (debt or 0.0) - (cash or 0.0)) if mcap is not None else None
    # ratios (R3)
    pe = _nan(); ps = pb = evx = fy_ = _nan()
    if usd and px and eps_adj is not None:
        if eps_adj > 0: pe = px / eps_adj
        else: flags.append('TTM EPS <= 0: P/E empty')
    if mcap is not None:
        ps = _safe(mcap, rev) if rev and rev > 0 else _nan()
        if equity is not None and equity > 0: pb = mcap / equity
        elif equity is not None: flags.append('equity <= 0: P/B empty')
        if ebitda is not None:
            if ebitda > 0: evx = ev / ebitda
            else: flags.append('EBITDA <= 0: EV/EBITDA empty')
        fy_ = _safe(fcf, mcap) if fcf is not None else _nan()
    # YoY growth (TTM vs TTM a year earlier, same R1 data)
    def growth(c):
        if not T[c]: return _nan()
        p = _ttm_prev(Q[c], S[c], T[c]['end'])
        if not p: return _nan()
        use(c + '_prev', p['facts'])
        if p['val'] <= 0: return _nan()
        return T[c]['val'] / p['val'] - 1.0
    rg, eg = growth('rev'), growth('eps')
    if T['eps'] and np.isnan(eg): flags.append('EPS growth n/a (prior TTM missing or <= 0)')
    peg = _nan()
    if np.isfinite(pe) and np.isfinite(eg):
        if eg > 0: peg = pe / (eg * 100.0)
        else: flags.append('EPS growth <= 0: PEG empty')
    gm = _safe(gp, rev) if rev and rev > 0 else _nan()
    om = _safe(op, rev) if rev and rev > 0 else _nan()
    roe = _safe(ni, equity) if equity is not None and equity > 0 else _nan()
    de = _safe(debt, equity) if (debt is not None and equity is not None and equity > 0) else _nan()
    # bookkeeping
    last_filed = max(u['filed'] for u in used) if used else None
    assert last_filed is None or last_filed < alert, 'look-ahead: fact filed on/after alert date'
    if audit is not None:
        for u in used: audit.append(dict(symbol=symbol, alert_date=alert, **u))
    r4 = lambda x, n=4: (None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), n))
    return {
        'fund_alert_date': str(alert.date()), 'fund_cutoff_date': str(cutoff.date()),
        'fund_period_end': str(anchor.date()), 'fund_last_filed': str(last_filed.date()) if last_filed is not None else None,
        'fund_data_age_days': int((cutoff - last_filed).days) if last_filed is not None else None,
        'fund_price': r4(px, 4), 'fund_shares': r4(shares, 0), 'fund_shares_src': sh['src'] if sh else None,
        'fund_mcap_b': r4(mcap / 1e9 if mcap else None, 3),
        'eps_ttm': r4(eps_adj, 4), 'revenue_ttm': r4(rev, 0), 'net_income_ttm': r4(ni, 0), 'op_income_ttm': r4(op, 0),
        'gross_profit_ttm': r4(gp, 0), 'ebitda_ttm': r4(ebitda, 0), 'fcf_ttm': r4(fcf, 0),
        'total_debt': r4(debt, 0), 'cash': r4(cash, 0), 'equity': r4(equity, 0),
        'pe_ttm': r4(pe, 2), 'ps_ttm': r4(ps, 3), 'pb': r4(pb, 3), 'ev_ebitda': r4(evx, 2), 'fcf_yield': r4(fy_, 5),
        'peg': r4(peg, 3), 'rev_growth_yoy': r4(rg, 5), 'eps_growth_yoy': r4(eg, 5), 'gross_margin': r4(gm, 5),
        'op_margin': r4(om, 5), 'roe': r4(roe, 5), 'debt_to_equity': r4(de, 3), 'fund_currency': cur,
        'fund_flag': '; '.join(dict.fromkeys(flags)) or None,
    }

# ------------------------------------------------------------------ sector percentile
def sector_map(tickers, etf_like=()):
    """Same sector source as scanner_newsmacro (Yahoo sector -> SPDR ETF, cached in sector_map.json)."""
    import scanner_newsmacro as NM
    return NM.sector_etf_for(list(tickers), etf_like)

def add_sector_pctile(rows, sectors, peers=None, min_peers=5, mcap_floor_b=1.5):
    """rows: list/DataFrame of fundamentals dicts with 't' (and all at ONE cutoff). peers: optional extra peer rows at the same
    cutoff (the universe). pe_sector_pctile = % of same-sector peers (positive P/E, mcap >= floor) with P/E <= this P/E (0-100).
    Negative/empty P/E (R3) -> empty and not part of the peer set."""
    df = pd.DataFrame(rows).copy()
    U = pd.concat([df, pd.DataFrame(peers)]) if peers is not None and len(peers) else df
    U = U.drop_duplicates('t')
    U = U[pd.to_numeric(U['pe_ttm'], errors='coerce') > 0]
    U = U[pd.to_numeric(U['fund_mcap_b'], errors='coerce').fillna(0) >= mcap_floor_b]
    U = U.assign(sec=U['t'].map(sectors))
    out_p, out_n, out_s = [], [], []
    for r in df.itertuples():
        s = sectors.get(r.t); out_s.append(s)
        pe = pd.to_numeric(getattr(r, 'pe_ttm'), errors='coerce')
        g = U[U['sec'] == s]['pe_ttm'].astype(float) if s else pd.Series(dtype=float)
        if s is None or not (pe > 0) or len(g) < min_peers: out_p.append(None); out_n.append(int(len(g)) if s else None); continue
        out_p.append(round(100.0 * float((g <= pe).sum()) / len(g), 1)); out_n.append(int(len(g)))
    df['fund_sector_etf'] = out_s; df['pe_sector_pctile'] = out_p; df['pe_sector_n'] = out_n
    return df

# ------------------------------------------------------------------ live-only extras (NOT for backtest)
def live_extras(symbol):
    """forward_pe_live / next_earnings_date_live from Yahoo (current snapshot only - never use in a backtest). Fail soft."""
    out = {'forward_pe_live': None, 'next_earnings_date_live': None}
    try:
        import yfinance as yf
        tk = yf.Ticker(symbol)
        try:
            fpe = tk.info.get('forwardPE')
            if fpe is not None and np.isfinite(float(fpe)) and float(fpe) > 0: out['forward_pe_live'] = round(float(fpe), 2)
        except Exception: pass
        try:
            cal = tk.calendar
            ed = cal.get('Earnings Date') if isinstance(cal, dict) else (cal.loc['Earnings Date'].iloc[0] if cal is not None and 'Earnings Date' in cal.index else None)
            if isinstance(ed, (list, tuple)): ed = ed[0] if ed else None
            if ed is not None: out['next_earnings_date_live'] = str(pd.Timestamp(ed).date())
        except Exception: pass
    except Exception: pass
    return out

def enrich_live(tickers_px, cutoff_date, alert_date, etf_like=(), skip=(), live=True, verbose=False):
    """Live scan helper. tickers_px: dict ticker -> close at the cutoff bar. Returns DataFrame keyed by 't'."""
    rows = []
    for t, px in tickers_px.items():
        if t.startswith('^'): continue
        if t in etf_like: r = empty_row('ETF - no company fundamentals', alert_date, cutoff_date)
        elif t in skip: r = empty_row('MCAP<1.5B / not verified - not computed', alert_date, cutoff_date)
        else:
            try: r = fundamentals_pit(t, cutoff_date, px, alert_date=alert_date)
            except Exception as e: r = empty_row(f'error: {e.__class__.__name__}: {e}', alert_date, cutoff_date)
        r['t'] = t
        if live and t not in etf_like and t not in skip: r.update(live_extras(t))
        else: r.update({c: None for c in LIVE_COLS})
        rows.append(r)
        if verbose: print(f"  fund {t:<6} pe={r.get('pe_ttm')} flag={r.get('fund_flag')}", flush=True)
    df = pd.DataFrame(rows)
    if df.empty: return df
    sec = sector_map([t for t in df['t'] if t not in etf_like], etf_like)
    return add_sector_pctile(df, sec)
