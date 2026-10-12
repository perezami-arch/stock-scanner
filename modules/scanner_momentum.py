"""12-1 momentum score component (+ experimental low-vol log) for the live scanner.  Added 2026-10-08.

VALIDATED CODE, REUSED AS-IS (not reimplemented):
  * /workspace/scanner-tool-eval/tools/base.py  -> Momentum121.score  (stocks: close[t-21]/close[t-252]-1, needs >=253 daily
    bars; crypto: calendar 365d/30d on 24h candles, NaN if the t-365d candle is missing by >5 days)
  * /workspace/scanner-tool-eval/tools/base.py  -> LowVol60.score     (minus std of last 60 daily log returns)
  * /workspace/scanner-tool-eval/pit.py         -> history()          (point-in-time cut: US bar visible only after its
    16:00 ET close <= asof; crypto 24h candles rebuilt from hourly bars ending at the last full hour <= asof)
  * ranking = within-asset-class percentile (report.py: groupby(aclass).rank(pct=True)), SHORT flips the direction.
Only the price download lives here; it copies fetch_prices.py (same yfinance calls, auto_adjust, same CSV layout).

SCORING RULES (Ilan, 8.10.2026):
  * momentum_score 0-100 = percentile of momentum_12_1 in its asset class (LONG view; SHORT = 100 - LONG).
  * Weighted component: MOMENTUM_WEIGHT = 10 of the 100-point score. The v2.8 weighted components are scaled x0.90,
    then momentum adds 10 * momentum_score/100. Bonuses/penalties/macro modifier unchanged (combine_score()).
  * Fewer than ~13 months of bars (IPO / new token / thin TASE name) -> momentum_score = 50 (NEUTRAL, = 5 points, the
    median contribution) and missing_history_flag = 'חסרה היסטוריה'. Never dropped.
  * Low-vol 60d is logged (lowvol_60d, lowvol_score) for forward measurement only. Weight 0, it never touches the score.
  * US stocks keep the $1.5B market-cap floor: below it -> excluded_reason='MCAP<1.5B', kept in the output, not ranked/scored.

CLI:
  python scanner_momentum.py --stocks NVDA,LNG --crypto BTC,ETH [--asof 2026-10-11T06:00Z] [--out file.csv]
  python scanner_momentum.py --features /path/features.csv [--ticker-col t]  (merge columns into an existing scan CSV)
"""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, sys, json, argparse, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

EVAL_DIR = (_SCANNER_ROOT + "/scanner-tool-eval")
CACHE_ROOT = (_SCANNER_ROOT + "/scanner-momentum-cache")
MOMENTUM_WEIGHT = 10            # points out of 100
BASE_SCALE = (100 - MOMENTUM_WEIGHT) / 100.0
LOWVOL_WEIGHT = 0               # experimental: logged only
NEUTRAL_SCORE = 50.0
FLAG_MISSING = "חסרה היסטוריה"
FLAG_NODATA = "אין נתוני מחיר"
MCAP_FLOOR_USD = 1.5e9
MIN_GROUP_FOR_SCAN_RANK = 5     # same minimum group size report.py used for per-date RankIC
OUT_COLS = ["ticker", "asset", "asof_utc", "last_bar", "history_bars", "momentum_12_1", "momentum_score",
            "momentum_score_short", "momentum_points", "missing_history_flag", "momentum_rank_basis",
            "lowvol_60d", "lowvol_score", "mcap_b", "excluded_reason"]

_pit = _base = None
def _load_eval(px_dir):
    """Import the researcher's pit + tools.base unchanged, pointed at this scan's price folder."""
    global _pit, _base
    os.environ["PIT_PX_DIR"] = px_dir
    if EVAL_DIR not in sys.path: sys.path.insert(0, EVAL_DIR)
    import pit, tools.base as base
    pit.PX = px_dir; pit._raw.cache_clear()
    _pit, _base = pit, base
    return pit, base

def yahoo_symbol(ticker, asset):
    t = ticker.strip().upper()
    if asset == "crypto":
        for suf in ("USDT", "USDC", "USD"):
            if t.endswith(suf) and not t.endswith("-USD") and len(t) > len(suf): t = t[: -len(suf)]; break
        if not t.endswith("-USD"): t += "-USD"
    return t

def fetch(sym, asset, asof, px_dir):
    """Same download as scanner-tool-eval/fetch_prices.py, windowed to the scan asof. Returns error str or None."""
    import yfinance as yf
    kind = "stock" if asset == "stock" else "crypto"
    os.makedirs(f"{px_dir}/{kind}", exist_ok=True)
    f = f"{px_dir}/{kind}/{sym}.csv"
    if os.path.exists(f): return None
    end = (asof.tz_convert("UTC") + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    if kind == "stock": kw = dict(start=(asof - pd.Timedelta(days=700)).strftime("%Y-%m-%d"), interval="1d")
    else:               kw = dict(start=(asof - pd.Timedelta(days=420)).strftime("%Y-%m-%d"), interval="1h")  # Yahoo 1h <= 730d
    try: x = yf.download(sym, end=end, auto_adjust=True, progress=False, **kw)
    except Exception as e: return str(e)[:80]
    if isinstance(x.columns, pd.MultiIndex): x.columns = x.columns.get_level_values(0)
    if x.empty: return "empty"
    x = x.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna()
    x.index.name = "date" if kind == "stock" else "ts_utc"; x.to_csv(f)
    return None

def market_cap(sym):
    try:
        import yfinance as yf
        return getattr(yf.Ticker(sym).fast_info, "market_cap", None)
    except Exception: return None

def _reference_pcts():
    """Fallback ranking basis for tiny groups: the 828+ validated setups' own momentum distribution (forecasts/mom121.csv)."""
    try:
        m = pd.read_csv(f"{EVAL_DIR}/forecasts/mom121.csv")[["setup_id", "f20"]]
        s = pd.read_csv(f"{EVAL_DIR}/setups_prepared.csv", usecols=["setup_id", "asset"])
        d = m.merge(s, on="setup_id").dropna(subset=["f20"])
        return {a: np.sort(g["f20"].values) for a, g in d.groupby("asset")}
    except Exception: return {}

def compute(items, asof=None, px_dir=None, check_mcap=True, verbose=True, mcaps=None):
    """items: list of (ticker, asset) with asset in {'stock','crypto'}. asof: scan moment (default now, UTC).
    mcaps: optional {ticker: market cap USD | None (unknown) | 'n/a' (ETF/index, floor not applicable)} to skip re-fetching.
    Returns DataFrame with OUT_COLS. Every ticker comes back as a row (never dropped)."""
    asof = pd.Timestamp.now(tz="UTC") if asof is None else pd.Timestamp(asof)
    if asof.tzinfo is None: asof = asof.tz_localize("Asia/Jerusalem")
    asof = asof.tz_convert("UTC")
    px_dir = px_dir or f"{CACHE_ROOT}/{asof.strftime('%Y%m%dT%H%MZ')}"
    pit, base = _load_eval(px_dir)
    mom, lv = base.Momentum121(), base.LowVol60()
    rows = []
    for tk, asset in items:
        asset = "crypto" if str(asset).lower() == "crypto" else "stock"
        sym = yahoo_symbol(tk, asset)
        err = fetch(sym, asset, asof, px_dir)
        r = dict(ticker=tk, asset=asset, asof_utc=asof.strftime("%Y-%m-%d %H:%M"), last_bar=None, history_bars=0,
                 momentum_12_1=np.nan, lowvol_60d=np.nan, mcap_b=None, excluded_reason=None, missing_history_flag=None)
        if err:
            r["missing_history_flag"] = FLAG_NODATA; r["fetch_error"] = err
        else:
            h = pit.history(sym, asset, asof, lookback=400)          # PIT-cut bars, exactly what Momentum121 sees
            r["history_bars"] = int(len(h)); r["last_bar"] = str(h.index[-1].date()) if len(h) else None
            r["momentum_12_1"] = mom.score(sym, asset, asof, 20)     # horizon is ignored by this tool
            r["lowvol_60d"] = lv.score(sym, asset, asof, 20)
            if pd.isna(r["momentum_12_1"]): r["missing_history_flag"] = FLAG_MISSING
        if asset == "stock" and mcaps is not None and tk in mcaps and mcaps[tk] == "n/a":
            pass                                                      # ETF / index: the $1.5B floor is for stocks
        elif asset == "stock" and (check_mcap or (mcaps is not None and tk in mcaps)):
            mc = mcaps[tk] if (mcaps is not None and tk in mcaps) else market_cap(sym)
            r["mcap_b"] = round(mc / 1e9, 2) if mc else None
            if mc is not None and mc < MCAP_FLOOR_USD: r["excluded_reason"] = "MCAP<1.5B"
            elif mc is None: r["excluded_reason"] = "MCAP ~ (לא אומת)"
        rows.append(r)
        if verbose: print(f"  {tk:<10} {asset:<6} bars={r['history_bars']:<4} mom={r['momentum_12_1']!s:<22} {r['missing_history_flag'] or ''} {r['excluded_reason'] or ''}", flush=True)
    df = pd.DataFrame(rows)
    return rank(df)

def rank(df):
    """Percentile within asset class among eligible names with a valid momentum (report.py logic). Neutral for missing."""
    ref = None
    df["momentum_score"] = np.nan; df["lowvol_score"] = np.nan; df["momentum_rank_basis"] = None
    elig = df["excluded_reason"].isna() | (df["excluded_reason"] == "MCAP ~ (לא אומת)")
    for a, g in df[elig].groupby("asset"):
        ok = g["momentum_12_1"].notna()
        if ok.sum() >= MIN_GROUP_FOR_SCAN_RANK:
            df.loc[g[ok].index, "momentum_score"] = 100 * g.loc[ok, "momentum_12_1"].rank(pct=True)
            df.loc[g[ok].index, "momentum_rank_basis"] = f"scan:{a} n={int(ok.sum())}"
        elif ok.any():                                    # too few names to rank inside the scan
            ref = ref if ref is not None else _reference_pcts()
            dist = ref.get(a)
            if dist is not None and len(dist):
                df.loc[g[ok].index, "momentum_score"] = [100 * np.searchsorted(dist, v, side="right") / len(dist) for v in g.loc[ok, "momentum_12_1"]]
                df.loc[g[ok].index, "momentum_rank_basis"] = f"validated-sample:{a} n={len(dist)}"
        lok = g["lowvol_60d"].notna()
        if lok.sum() >= 2: df.loc[g[lok].index, "lowvol_score"] = 100 * g.loc[lok, "lowvol_60d"].rank(pct=True)
    miss = df["momentum_12_1"].isna() & elig
    df.loc[miss, "momentum_score"] = NEUTRAL_SCORE
    df.loc[miss, "momentum_rank_basis"] = "neutral"
    df["momentum_score"] = df["momentum_score"].round(1)
    df["momentum_score_short"] = (100 - df["momentum_score"]).round(1)
    df["momentum_points"] = (MOMENTUM_WEIGHT * df["momentum_score"] / 100).round(2)
    df["lowvol_score"] = df["lowvol_score"].round(1)
    df["momentum_12_1"] = df["momentum_12_1"].astype(float).round(4)
    df["lowvol_60d"] = df["lowvol_60d"].astype(float).round(5)
    return df[OUT_COLS + [c for c in df.columns if c not in OUT_COLS]]

def direction_score(row, direction):
    """momentum_score for a setup's direction (LONG view, or flipped for SHORT). Neutral stays 50."""
    return row["momentum_score_short"] if str(direction).upper().startswith("S") else row["momentum_score"]

def combine_score(base_weighted_0_100, momentum_score, bonuses=0.0, penalties=0.0, macro_modifier=0.0, cap=100.0):
    """v2.8 order of calculation with momentum inserted as a weighted component:
    1) weighted components: 0.90 x (v2.8 components, sum 100) + 10 x momentum_score/100
    2) + bonuses  3) - penalties  4) + macro modifier (+/-15, applied once)  5) floor 0, cap 100 (or the 60/65 caps)."""
    ms = NEUTRAL_SCORE if momentum_score is None or pd.isna(momentum_score) else momentum_score
    s = BASE_SCALE * base_weighted_0_100 + MOMENTUM_WEIGHT * ms / 100.0
    s = s + bonuses - penalties + max(-15.0, min(15.0, macro_modifier))
    return round(max(0.0, min(cap, s)), 1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stocks", default=""); ap.add_argument("--crypto", default="")
    ap.add_argument("--features"); ap.add_argument("--ticker-col", default="t")
    ap.add_argument("--asof"); ap.add_argument("--out"); ap.add_argument("--no-mcap", action="store_true")
    a = ap.parse_args()
    if a.features:
        F = pd.read_csv(a.features)
        items = [(t, "crypto" if str(t).upper().endswith(("-USD", "USDT")) else "stock") for t in F[a.ticker_col]]
        M = compute(items, a.asof, check_mcap=not a.no_mcap)
        out = F.merge(M.rename(columns={"ticker": a.ticker_col}).drop(columns=["asset"]), on=a.ticker_col, how="left")
        dst = a.out or a.features.replace(".csv", "_momentum.csv")
    else:
        items = [(t, "stock") for t in a.stocks.split(",") if t] + [(t, "crypto") for t in a.crypto.split(",") if t]
        out = compute(items, a.asof, check_mcap=not a.no_mcap); dst = a.out
    if dst:
        os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
        out.to_csv(dst, index=False, encoding="utf-8-sig"); print("wrote", dst)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(out[[c for c in OUT_COLS if c in out.columns]].to_string(index=False))

if __name__ == "__main__":
    main()
