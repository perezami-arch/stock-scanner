"""scanner_news.py - point-in-time per-ticker news from the Alpaca News API (Benzinga feed), with on-disk cache.

Import-safe: importing this module does nothing (no network, no files, no prints). Keys are read from the env
(ALPACA_API_KEY_ID / ALPACA_API_SECRET_KEY) only when a fetch actually runs, and are never printed or cached.

Main entry point (also reused by the researcher for the historical setups):

    from scanner_news import fetch_news_pit
    arts = fetch_news_pit("NVDA", "2026-10-07T20:00:00Z", lookback_days=7)
    arts       -> list of dicts {id, headline, summary, source, created_at_utc, symbols, url}, newest first,
                  ONLY articles with  cutoff - lookback_days <= created_at < cutoff  (strictly before the cutoff)
    arts.flag  -> None, or a reason the list is empty by construction ("TASE: no Alpaca coverage", "index", "no keys", "api error ...")
    arts.symbol_alpaca, arts.cutoff_utc, arts.window_start_utc -> what was actually queried

Point-in-time rule: the caller passes the cutoff (US stocks: previous close 16:00 ET for alerts before 16:00 ET;
crypto: the alert minute, or 00:00 UTC when only the date is known) - see scanner_newsmacro.stock_cutoff / crypto_cutoff.
A naive cutoff (no tz) is taken as UTC. Filtering is on created_at; a later edit of the headline (updated_at) is not undone.

Symbols: US stocks as on Yahoo (BRK-B -> BRK.B). Crypto: BTC-USD / BTC/USD / BTCUSD -> BTCUSD.
TASE: symbols ending in .TA, or market="TASE" -> empty list with flag (Alpaca has no TASE coverage).
Indices (^VIX, ^TNX ...) -> empty list with flag.

Cache: /workspace/news-cache/<SYMBOL>/<YYYY-MM-DD>.json, one file per COMPLETE UTC day (all articles created that day,
content/images dropped). A day is cached only when it ended >= 6h before the fetch, so partial days are always refetched.
A window needs one paginated API call covering only its missing days. Rate limit: Alpaca free = 200 req/min; we stay <=180.
"""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, json, time, threading
from datetime import datetime, timedelta, timezone

API_URL = "https://data.alpaca.markets/v1beta1/news"
CACHE_DIR = os.environ.get("NEWS_CACHE_DIR", (_SCANNER_ROOT + "/news-cache"))
CACHE_SETTLE_HOURS = 6          # a UTC day is cached only once it ended this long ago
MAX_PAGES = 40                  # 40 x 50 = 2000 articles per window (NVDA ~ 150-250 / week)
FIELDS = ("id", "headline", "summary", "source", "created_at_utc", "symbols", "url")


class NewsResult(list):
    """A list of article dicts plus metadata (.flag, .symbol_alpaca, .cutoff_utc, .window_start_utc)."""
    flag = None; symbol_alpaca = None; cutoff_utc = None; window_start_utc = None


_lock = threading.Lock(); _calls = []
def _throttle(max_per_min=180):
    with _lock:
        now = time.time()
        while _calls and now - _calls[0] > 60: _calls.pop(0)
        if len(_calls) >= max_per_min:
            time.sleep(60 - (now - _calls[0]) + 0.1)
        _calls.append(time.time())


def _utc(x):
    if isinstance(x, str):
        x = datetime.fromisoformat(x.replace("Z", "+00:00"))
    elif hasattr(x, "to_pydatetime"):
        x = x.to_pydatetime()
    if x.tzinfo is None: x = x.replace(tzinfo=timezone.utc)
    return x.astimezone(timezone.utc)


def _iso(d): return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_symbol(symbol, market=None):
    """Returns (alpaca_symbol or None, flag or None)."""
    s = str(symbol).strip().upper()
    if market and str(market).upper() in ("TASE", "TA", "IL"):  return None, "TASE: no Alpaca coverage"
    if s.endswith(".TA"):                                        return None, "TASE: no Alpaca coverage"
    if s.startswith("^"):                                        return None, "index: no news"
    if market and str(market).lower() == "crypto" or s.endswith("-USD") or s.endswith("/USD"):
        base = s.replace("-USD", "").replace("/USD", "")
        base = "".join(ch for ch in base if not ch.isdigit()) if base.startswith("HYPE") else base   # Yahoo HYPE32196-USD
        return base + "USD", None
    return s.replace("-", "."), None


def _slim(a):
    return {"id": a.get("id"), "headline": a.get("headline"), "summary": a.get("summary"), "source": a.get("source"),
            "created_at_utc": a.get("created_at"), "symbols": a.get("symbols") or [], "url": a.get("url")}


def _api(sym, start, end):
    """All articles for sym with start <= created_at < end (paginated). Raises on hard errors."""
    import requests
    kid, sec = os.environ.get("ALPACA_API_KEY_ID"), os.environ.get("ALPACA_API_SECRET_KEY")
    if not kid or not sec: raise RuntimeError("no keys")
    H = {"APCA-API-KEY-ID": kid, "APCA-API-SECRET-KEY": sec}
    p = dict(symbols=sym, start=_iso(start), end=_iso(end), limit=50, sort="desc", include_content="false")
    out, tok = [], None
    for _ in range(MAX_PAGES):
        if tok: p["page_token"] = tok
        for attempt in range(5):
            _throttle()
            r = requests.get(API_URL, headers=H, params=p, timeout=30)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(min(60, 2 ** attempt * 3)); continue
            break
        if not r.ok: raise RuntimeError(f"api error {r.status_code}")
        j = r.json(); out += [_slim(a) for a in j.get("news", [])]
        tok = j.get("next_page_token")
        if not tok: break
    else:
        raise RuntimeError(f"more than {MAX_PAGES * 50} articles in window")
    return out


def _day_file(sym, day): return os.path.join(CACHE_DIR, sym.replace("/", "_"), f"{day:%Y-%m-%d}.json")


def fetch_news_pit(symbol, cutoff_utc, lookback_days=7, market=None, use_cache=True):
    """Articles about `symbol` created in [cutoff_utc - lookback_days, cutoff_utc), newest first. See module doc."""
    res = NewsResult()
    cutoff = _utc(cutoff_utc); start = cutoff - timedelta(days=lookback_days)
    res.cutoff_utc, res.window_start_utc = _iso(cutoff), _iso(start)
    sym, flag = normalize_symbol(symbol, market)
    res.symbol_alpaca = sym
    if flag: res.flag = flag; return res
    now = datetime.now(timezone.utc)
    d0 = start.replace(hour=0, minute=0, second=0, microsecond=0)
    days = []; d = d0
    while d < cutoff: days.append(d); d += timedelta(days=1)
    have, missing = {}, []
    for d in days:
        f = _day_file(sym, d)
        if use_cache and os.path.exists(f):
            with open(f) as fh: have[d] = json.load(fh)
        else: missing.append(d)
    if missing:
        q0, q1 = max(missing[0], start), min(missing[-1] + timedelta(days=1), cutoff)
        # if the whole missing span lies inside complete days, fetch whole days so they can be cached
        settled = lambda dd: dd + timedelta(days=1, hours=CACHE_SETTLE_HOURS) <= now
        q0 = missing[0] if use_cache else q0
        q1e = missing[-1] + timedelta(days=1)
        if use_cache and settled(missing[-1]): q1 = q1e
        try:
            arts = _api(sym, q0, q1)
        except Exception as e:
            res.flag = str(e) if str(e).startswith(("api error", "no keys", "more than")) else f"api error ({e.__class__.__name__})"
            return res
        by = {d: [] for d in missing}
        for a in arts:
            ad = _utc(a["created_at_utc"]).replace(hour=0, minute=0, second=0, microsecond=0)
            if ad in by: by[ad].append(a)
        for d in missing:
            have[d] = by[d]
            # cache only days fully fetched (whole day inside the query) and settled
            if use_cache and settled(d) and q0 <= d and d + timedelta(days=1) <= q1:
                f = _day_file(sym, d); os.makedirs(os.path.dirname(f), exist_ok=True)
                tmp = f + ".tmp"
                with open(tmp, "w") as fh: json.dump(by[d], fh, ensure_ascii=False)
                os.replace(tmp, f)
    seen = set(); out = []
    for d in days:
        for a in have.get(d, []):
            t = _utc(a["created_at_utc"])
            if start <= t < cutoff and a["id"] not in seen:
                seen.add(a["id"]); out.append(a)
    out.sort(key=lambda a: a["created_at_utc"], reverse=True)
    res.extend(out)
    return res
