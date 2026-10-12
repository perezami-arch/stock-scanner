"""scanner_newsmacro.py - LOGGED-ONLY (experimental, score weight 0) news + rates + AAII columns for Ilan's scanner.
Added 2026-10-08 at Ilan's request (group chat): document per-ticker news; macro = bonds' impact on the stock/sector + AAII.
Nothing here feeds the score. To be backtested point-in-time before any weighting.

Columns per ticker (see /workspace/tracker/schema_new_rows_2026-10-08.json):
  news_cutoff_utc, news_count_7d, news_count_7d_focused (articles tagging <=3 symbols), news_headlines_top3
  ("headline | source | DD.MM.YYYY HH:MM IL" x3, newest focused first), news_last_ts (IL), news_count_cutoff_to_scan
  (articles between the cutoff and the scan moment - known at the alert, NOT in the 7d count), news_flag
  rate_beta_ticker_60d / rate_beta_sector_60d = OLS slope of daily % return on daily change of the 10Y yield (^TNX) in bp,
  x10 => "% move per +10bp" over the last 60 common trading days <= cutoff (min 40 obs); rate_corr_* = correlation
  sector_etf (Yahoo sector -> SPDR), us10y_level, us10y_chg_20d_bp, us2y10y_spread (FRED vintage, else Yahoo), aaii_bull_bear
Point-in-time: US stocks - alert before 16:00 ET cuts at the previous session close (16:00 ET); at/after 16:00 ET on a session
day -> that day's close. Crypto - the alert minute (or 00:00 UTC when only the date is known).
Import-safe (no side effects on import).
"""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, json, glob
import numpy as np, pandas as pd

ET, IL = "America/New_York", "Asia/Jerusalem"
SECTOR_MAP_FILE = (_SCANNER_ROOT + "/scanner-momentum-cache/sector_map.json")
NAME_MAP_FILE = (_SCANNER_ROOT + "/scanner-momentum-cache/name_map.json")      # Yahoo shortName, used only to rank headlines
AAII_GLOB = (_SCANNER_ROOT + "/tracker/rules/aaii_weekly*.csv")          # same cache market_regime.py falls back to
YAHOO_SECTOR_ETF = {"Technology": "XLK", "Financial Services": "XLF", "Energy": "XLE", "Healthcare": "XLV",
                    "Industrials": "XLI", "Consumer Cyclical": "XLY", "Consumer Defensive": "XLP", "Utilities": "XLU",
                    "Basic Materials": "XLB", "Real Estate": "XLRE", "Communication Services": "XLC"}
SPDRS = set(YAHOO_SECTOR_ETF.values())
ETF_SECTOR = {"SMH": "XLK", "XBI": "XLV"}                          # industry ETFs -> parent sector SPDR
NEWS_COLS = ["news_cutoff_utc", "news_count_7d", "news_count_7d_focused", "news_headlines_top3", "news_last_ts",
             "news_count_cutoff_to_scan", "news_flag"]
RATE_COLS = ["sector_etf", "rate_beta_ticker_60d", "rate_corr_ticker_60d", "rate_beta_sector_60d", "rate_corr_sector_60d", "rate_n_obs"]
MACRO_COLS = ["us10y_level", "us10y_chg_20d_bp", "us2y10y_spread", "us2y10y_src", "aaii_bull_bear", "aaii_date"]


# ------------------------------------------------------------------ cutoffs
def stock_cutoff(asof, sessions):
    """asof: tz-aware Timestamp. sessions: iterable of NYSE session dates (e.g. SPY daily bar dates). Returns UTC Timestamp."""
    a = pd.Timestamp(asof).tz_convert(ET)
    S = sorted({pd.Timestamp(s).date() for s in sessions})
    if a.date() in S and a.hour >= 16: d = a.date()
    else:
        prev = [s for s in S if s < a.date()]
        if not prev: raise ValueError("no session before asof")
        d = prev[-1]
    return pd.Timestamp(f"{d} 16:00", tz=ET).tz_convert("UTC")


def crypto_cutoff(asof, date_only=False):
    a = pd.Timestamp(asof).tz_convert("UTC")
    return a.normalize() if date_only else a.floor("min")


# ------------------------------------------------------------------ news
_NM = None
def _names():
    global _NM
    if _NM is None: _NM = json.load(open(NAME_MAP_FILE)) if os.path.exists(NAME_MAP_FILE) else {}
    return _NM

_CRYPTO_NAMES = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "xrp", "DOGE": "dogecoin", "ADA": "cardano", "HYPE": "hyperliquid"}
def _relevant(a, symbol):
    """Headline names the ticker or the company's first name word (e.g. 'Nvidia', 'Starbucks', 'JPMorgan')."""
    import re
    h = (a.get("headline") or "").lower(); t = str(symbol).upper().replace("-USD", "").replace("/USD", "")
    keys = {t.lower()}
    nm = (_names().get(str(symbol).upper()) or "").split()
    if nm and len(nm[0]) >= 3: keys.add(nm[0].lower().strip(",."))
    if t in _CRYPTO_NAMES: keys.add(_CRYPTO_NAMES[t])
    return any(re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", h) for k in keys)

def _il(ts): return pd.Timestamp(ts).tz_convert(IL).strftime("%d.%m.%Y %H:%M") + " IL"


def news_columns(symbol, cutoff_utc, asof_utc=None, market=None, lookback_days=7):
    """Returns (cols dict, articles list incl. post-cutoff ones marked after_cutoff=True)."""
    import scanner_news as N
    cutoff = pd.Timestamp(cutoff_utc).tz_convert("UTC")
    asof = pd.Timestamp(asof_utc).tz_convert("UTC") if asof_utc is not None else cutoff
    gap = max(0.0, (asof - cutoff).total_seconds() / 86400)
    arts = N.fetch_news_pit(symbol, asof.to_pydatetime(), lookback_days=lookback_days + gap, market=market)
    c = {"news_cutoff_utc": cutoff.strftime("%Y-%m-%d %H:%M"), "news_flag": arts.flag}
    if arts.flag:
        c.update(news_count_7d=None, news_count_7d_focused=None, news_headlines_top3=None, news_last_ts=None, news_count_cutoff_to_scan=None)
        return c, []
    lo = cutoff - pd.Timedelta(days=lookback_days)
    pre = [a for a in arts if lo <= pd.Timestamp(a["created_at_utc"]) < cutoff]
    post = [a for a in arts if pd.Timestamp(a["created_at_utc"]) >= cutoff]
    foc = [a for a in pre if len(a["symbols"]) <= 3]
    rel = [a for a in pre if _relevant(a, symbol)]                     # ranking only: named in headline > focused > rest, newest first
    top = []
    for a in rel + foc + pre:
        if a not in top: top.append(a)
        if len(top) == 3: break
    top.sort(key=lambda a: a["created_at_utc"], reverse=True)
    c.update(news_count_7d=len(pre), news_count_7d_focused=len(foc),
             news_headlines_top3=" || ".join(f"{a['headline']} | {a['source'] or 'n/a'} | {_il(a['created_at_utc'])}" for a in top) or None,
             news_last_ts=_il(pre[0]["created_at_utc"]) if pre else None, news_count_cutoff_to_scan=len(post))
    if not pre: c["news_flag"] = f"no news in {lookback_days}d before cutoff"
    return c, [dict(a, after_cutoff=pd.Timestamp(a["created_at_utc"]) >= cutoff) for a in arts]


# ------------------------------------------------------------------ sectors
def sector_etf_for(tickers, etf_like=()):
    m = json.load(open(SECTOR_MAP_FILE)) if os.path.exists(SECTOR_MAP_FILE) else {}
    import yfinance as yf
    changed, out = False, {}
    for t in tickers:
        if t.startswith("^"): out[t] = None; continue
        if t in SPDRS: out[t] = t; continue
        if t in ETF_SECTOR: out[t] = ETF_SECTOR[t]; continue
        if t in etf_like: out[t] = None; continue
        if t not in m:
            try: inf = yf.Ticker(t).info; m[t] = inf.get("sector"); _names()[t] = inf.get("shortName")
            except Exception: m[t] = None
            changed = True
        out[t] = YAHOO_SECTOR_ETF.get(m[t])
    if changed:
        os.makedirs(os.path.dirname(SECTOR_MAP_FILE), exist_ok=True); json.dump(m, open(SECTOR_MAP_FILE, "w"), indent=0, sort_keys=True)
        json.dump(_names(), open(NAME_MAP_FILE, "w"), indent=0, sort_keys=True, ensure_ascii=False)
    return out


# ------------------------------------------------------------------ rates
def load_closes(symbols, cutoff_utc, days=200):
    """Daily closes with bar date <= cutoff's ET date (stock/bond session bars complete at 16:00 ET)."""
    import yfinance as yf
    cut = pd.Timestamp(cutoff_utc).tz_convert(ET)
    end = (cut.normalize() + pd.Timedelta(days=1)).strftime("%Y-%m-%d"); start = (cut.normalize() - pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    d = yf.download(sorted(set(symbols)), start=start, end=end, auto_adjust=True, progress=False, threads=True)["Close"]
    if isinstance(d, pd.Series): d = d.to_frame(symbols[0])
    d.index = pd.to_datetime(d.index).tz_localize(None)
    return d[d.index <= pd.Timestamp(cut.date())]


def rate_beta(px, tnx, n=60, min_obs=40):
    """(beta % per +10bp, corr, n) of daily % returns on daily 10Y change (bp), last n common days."""
    r = px.dropna().pct_change() * 100; dy = tnx.dropna().diff() * 100
    j = pd.concat([r, dy], axis=1, join="inner").dropna().iloc[-n:]
    if len(j) < min_obs: return None, None, len(j)
    x, y = j.iloc[:, 1].values, j.iloc[:, 0].values
    v = np.var(x, ddof=1)
    if v == 0: return None, None, len(j)
    b = np.cov(x, y, ddof=1)[0, 1] / v
    return round(float(b * 10), 3), round(float(np.corrcoef(x, y)[0, 1]), 3), len(j)


def fred_vintage(series, cutoff_utc):
    """Latest observation dated before the cutoff ET date, as published on/before that date (ALFRED vintage)."""
    k = os.environ.get("FRED_API_KEY")
    if not k: return None
    import requests
    d = pd.Timestamp(cutoff_utc).tz_convert(ET).date().isoformat()
    try:
        j = requests.get("https://api.stlouisfed.org/fred/series/observations", params=dict(series_id=series, api_key=k, file_type="json",
                         realtime_start=d, realtime_end=d, observation_end=d, sort_order="desc", limit=10), timeout=30).json()
        obs = [o for o in j.get("observations", []) if o["value"] != "." and o["date"] < d]
        return (float(obs[0]["value"]), obs[0]["date"]) if obs else None
    except Exception:
        return None


def aaii_pit(cutoff_utc):
    """Latest AAII week released by the cutoff. Survey week ends Wed (reported_date); results are out Thu - counted
    available from Thu 12:00 ET (conservative). Reads the same cache as market_regime.py (aaii.com blocks scripts)."""
    fs = sorted(glob.glob(AAII_GLOB))
    if not fs: return None
    c = pd.concat([pd.read_csv(f) for f in fs]).drop_duplicates("reported_date").sort_values("reported_date")
    cut = pd.Timestamp(cutoff_utc).tz_convert(ET)
    avail = pd.to_datetime(c.reported_date).dt.tz_localize(ET) + pd.Timedelta(days=1, hours=12)
    c = c[avail <= cut]
    if not len(c): return None
    r = c.iloc[-1]; age = (cut.date() - pd.Timestamp(r.reported_date).date()).days
    return dict(date=r.reported_date, bullish=float(r.bullish), neutral=float(r.neutral), bearish=float(r.bearish),
                bull_bear_spread=round(float(r.bullish - r.bearish), 1), age_days=age, stale=age > 8,
                src="cache " + ",".join(os.path.basename(f) for f in fs))


def macro_snapshot(cutoff_utc, closes=None):
    """Run-level logged-only macro readings at the cutoff (bond yields + AAII). closes: DataFrame incl. ^TNX/^TYX/^IRX/2YY=F."""
    cl = closes if closes is not None else load_closes(["^TNX", "^TYX", "^IRX", "2YY=F", "^VIX"], cutoff_utc)
    R = {"cutoff_utc": pd.Timestamp(cutoff_utc).strftime("%Y-%m-%d %H:%M"), "note": "logged only, weight 0"}
    def lvl(t):
        s = cl[t].dropna() if t in cl else pd.Series(dtype=float)
        return (round(float(s.iloc[-1]), 3), str(s.index[-1].date()), s) if len(s) else (None, None, s)
    v, d, s = lvl("^TNX")
    R["US10Y"] = dict(value=v, date=d, chg_20d_bp=round(float(s.iloc[-1] - s.iloc[-21]) * 100, 1) if len(s) > 21 else None,
                      chg_30d_bp=round(float(s.iloc[-1] - s[s.index <= s.index[-1] - pd.Timedelta(days=30)].iloc[-1]) * 100, 1) if len(s) > 30 else None, src="yahoo ^TNX")
    for k, t in (("US30Y", "^TYX"), ("US3M", "^IRX"), ("US2Y_yahoo_2YY=F", "2YY=F"), ("VIX", "^VIX")):
        v2, d2, _ = lvl(t); R[k] = dict(value=v2, date=d2)
    f10, f2 = fred_vintage("DGS10", cutoff_utc), fred_vintage("DGS2", cutoff_utc)
    if f10 and f2 and f10[1] == f2[1]:
        R["us2y10y_spread"] = dict(value=round(f10[0] - f2[0], 3), obs_date=f10[1], src="FRED DGS10-DGS2 (vintage as of cutoff date)", DGS10=f10[0], DGS2=f2[0])
    elif v is not None and R["US2Y_yahoo_2YY=F"]["value"] is not None:
        R["us2y10y_spread"] = dict(value=round(v - R["US2Y_yahoo_2YY=F"]["value"], 3), obs_date=d, src="yahoo ^TNX - 2YY=F (futures-based 2Y, differs from FRED)")
    else: R["us2y10y_spread"] = dict(value=None)
    if R["US30Y"]["value"] and v: R["us10y30y_spread"] = round(R["US30Y"]["value"] - v, 3)
    R["aaii"] = aaii_pit(cutoff_utc) or {"status": "no AAII week available before cutoff"}
    return R


def macro_row(R):
    a = R.get("aaii", {}); s = R.get("us2y10y_spread", {})
    return dict(us10y_level=R["US10Y"]["value"], us10y_chg_20d_bp=R["US10Y"]["chg_20d_bp"], us2y10y_spread=s.get("value"),
                us2y10y_src=(s.get("src") or "").split(" ")[0] or None, aaii_bull_bear=a.get("bull_bear_spread"), aaii_date=a.get("date"))


# ------------------------------------------------------------------ one-call enrichment
def enrich(tickers, asof, outdir, etf_like=(), skip=(), asset="stock", sessions=None, date_only=False, verbose=True):
    """Logged-only news + rate + macro columns for a list of tickers (one asset class). Writes to outdir:
    news_alpaca.json (all articles per ticker, after_cutoff flagged) and macro_regime_pit.json. Returns DataFrame keyed 't'.
    skip: tickers not to query for news (e.g. failing the $1.5B floor) - row kept with news_flag."""
    asof = pd.Timestamp(asof).tz_convert("UTC")
    tickers = [t for t in dict.fromkeys(tickers)]
    if asset == "stock":
        if sessions is None:
            spy = load_closes(["SPY"], asof + pd.Timedelta(days=1), days=30); sessions = spy.dropna(how="all").index
        cutoff = stock_cutoff(asof, sessions)
    else:
        cutoff = crypto_cutoff(asof, date_only)
    sec = sector_etf_for(tickers, etf_like) if asset == "stock" else {t: None for t in tickers}
    syms = [t for t in tickers if not t.startswith("^")] + [e for e in set(sec.values()) if e] + ["^TNX", "^TYX", "^IRX", "2YY=F", "^VIX"]
    if asset == "crypto": syms = ["^TNX", "^TYX", "^IRX", "2YY=F", "^VIX"] + [t if t.endswith("-USD") else t + "-USD" for t in tickers]
    cl = load_closes(syms, cutoff, days=200)
    R = macro_snapshot(cutoff, cl); mrow = macro_row(R)
    tnx = cl["^TNX"]; rows, allnews = [], {}
    for t in tickers:
        row = {"t": t, "sector_etf": sec.get(t)}
        if t.startswith("^"):
            row.update(news_flag="index: no news"); rows.append({**row, **mrow}); continue
        pcol = t if asset == "stock" else (t if t.endswith("-USD") else t + "-USD")
        b, c, n = rate_beta(cl[pcol], tnx) if pcol in cl else (None, None, 0)
        row.update(rate_beta_ticker_60d=b, rate_corr_ticker_60d=c, rate_n_obs=n)
        e = sec.get(t)
        if e and e in cl: row["rate_beta_sector_60d"], row["rate_corr_sector_60d"], _ = rate_beta(cl[e], tnx)
        if t in skip:
            row.update(news_cutoff_utc=cutoff.strftime("%Y-%m-%d %H:%M"), news_flag="skipped (MCAP<1.5B)")
        else:
            nc, arts = news_columns(t, cutoff, asof, market=("crypto" if asset == "crypto" else None)); row.update(nc); allnews[t] = arts
        rows.append({**row, **mrow})
        if verbose: print(f"  news/rates {t:<8} news7d={row.get('news_count_7d')!s:<4} beta10y={row.get('rate_beta_ticker_60d')!s:<7} {row.get('sector_etf') or ''} {row.get('news_flag') or ''}", flush=True)
    os.makedirs(outdir, exist_ok=True)
    meta = dict(asof_utc=asof.strftime("%Y-%m-%d %H:%M"), cutoff_utc=cutoff.strftime("%Y-%m-%d %H:%M"), asset=asset, source="Alpaca News API v1beta1 (Benzinga)",
                rule="news_count_7d/top3/last_ts use only created_at < cutoff; after_cutoff=True articles are between cutoff and scan (known at alert, counted separately)")
    json.dump(dict(meta=meta, news=allnews), open(f"{outdir}/news_alpaca{'_crypto' if asset == 'crypto' else ''}.json", "w"), ensure_ascii=False, indent=1)
    json.dump(R, open(f"{outdir}/macro_regime_pit{'_crypto' if asset == 'crypto' else ''}.json", "w"), ensure_ascii=False, indent=1, default=str)
    df = pd.DataFrame(rows)
    for col in NEWS_COLS + RATE_COLS + MACRO_COLS:
        if col not in df: df[col] = None
    return df[["t"] + NEWS_COLS + RATE_COLS + MACRO_COLS], R, cutoff


def annotate(setups, asof=None, outdir=None):
    """For routine setups (DataFrame with ticker, asset 'stock'|'crypto', optional market='TASE'): returns setups + logged-only columns."""
    asof = pd.Timestamp.now(tz="UTC") if asof is None else pd.Timestamp(asof)
    if asof.tzinfo is None: asof = asof.tz_localize(IL)
    outdir = outdir or f"{_SCANNER_ROOT}/scan-runs/{asof.tz_convert(IL):%Y-%m-%d_%H%M}"
    parts = []
    for asset, g in setups.groupby(setups["asset"].astype(str).str.lower().map(lambda a: "crypto" if a == "crypto" else "stock")):
        tase = g.get("market", pd.Series(index=g.index, dtype=object)).astype(str).str.upper().eq("TASE") | g["ticker"].astype(str).str.upper().str.endswith(".TA")
        us = g[~tase]
        if len(us):
            df, _, _ = enrich(list(us["ticker"]), asof, outdir, asset=asset, verbose=False)
            parts.append(us.merge(df.rename(columns={"t": "ticker"}), on="ticker", how="left"))
        if tase.any(): parts.append(g[tase].assign(news_flag="TASE: no Alpaca coverage"))
    return pd.concat(parts, ignore_index=True) if parts else setups
