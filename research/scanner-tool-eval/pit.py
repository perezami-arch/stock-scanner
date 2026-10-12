"""Point-in-time (PIT) data layer for scanner-setup evaluation.

Cut rules (the model may only see data that existed at the alert moment `asof`):
  * Stocks (daily bars): bar D is complete at 16:00 America/New_York on D. A bar is visible only if that close
    moment <= asof. If the alert happened before/during the alert_date session, the alert_date bar is excluded
    and history ends at the previous trading day's close.
  * Crypto (24/7): rebuilt 24h candles from hourly bars, ending exactly at the last full hour <= asof.
  * Cutoffs come from the canonical file /workspace/tracker/setups-point-in-time-2026-10-08.csv
    (cutoff_bar_date for US, cutoff_minute_utc for crypto; date-only crypto -> 00:00 UTC of alert day,
    date-only US -> prior session close). Perplexity 'ui_log' (task-list) times are upper bounds logged 5-70 min
    late, so the cutoff is additionally capped at logged time - 70 min.
"""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, functools, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
PX = os.environ.get("PIT_PX_DIR", (_SCANNER_ROOT + "/kronos-eval/tracker_eval/px"))
IL, NY = "Asia/Jerusalem", "America/New_York"

SETUPS_CSV = (_SCANNER_ROOT + "/tracker/setups-point-in-time-2026-10-08.csv")
MAIN_SHEET_PKL = os.path.join(HERE, "_main_sheet.pkl")   # cached read of xlsx sheet 'מעקב סריקות' (read-only)
UI_LOG_BACKOFF = pd.Timedelta(minutes=70)

def load_setups(path=SETUPS_CSV):
    """Canonical PIT setups (read-only). Adds asof_ts (tz-aware UTC moment of the data cutoff), dir_sign,
    and tracker realized returns (direction-adjusted, vs alert price) for main-sheet rows."""
    df = pd.read_csv(path)
    df = df[df["dup_not_counted"] != True].copy()
    df = df[df["cutoff_bar_date"].notna() | df["cutoff_minute_utc"].notna()]
    df["asset"] = np.where(df["asset_class"] == "crypto", "crypto", "stock")
    def asof(r):
        if r["asset"] == "crypto":
            a = pd.Timestamp(r["cutoff_minute_utc"]) if pd.notna(r["cutoff_minute_utc"]) else pd.Timestamp(r["alert_date"]).tz_localize("UTC")
        else:   # given cutoff bar is fully visible: its 16:00 ET close
            a = (pd.Timestamp(r["cutoff_bar_date"]) + pd.Timedelta(hours=16)).tz_localize(NY)
        a = a.tz_convert("UTC")
        if r["time_source"] == "ui_log" and pd.notna(r["alert_time_utc"]):
            # Perplexity task-list times are logged 5-70 min AFTER the real run: cut 70 min before the logged time
            a = min(a, pd.Timestamp(r["alert_time_utc"]).tz_convert("UTC") - UI_LOG_BACKOFF)
        return a
    df["asof_ts"] = pd.to_datetime(df.apply(asof, axis=1), utc=True)
    df["dir_sign"] = np.where(df["direction"] == "SHORT", -1.0, 1.0)
    if os.path.exists(MAIN_SHEET_PKL):
        x = pd.read_pickle(MAIN_SHEET_PKL)
        idx = (df["main_sheet_row"] - 2)        # main_sheet_row is the Excel row (header = row 1)
        ok = df["in_main_sheet"] & idx.notna()
        sub = x.reindex(idx[ok].astype(int).values)
        assert (sub["טיקר"].values == df.loc[ok, "ticker"].values).all(), "main_sheet_row mapping mismatch"
        days = [f"יום {i}" for i in range(1, 21)]
        df.loc[ok, "trk_day5"] = sub["יום 5"].values
        df.loc[ok, "trk_day20"] = sub["יום 20"].values
        df.loc[ok, "trk_total"] = sub['סה"כ תשואה'].values
        df.loc[ok, "trk_ndays"] = sub[days].notna().sum(axis=1).values
    return df

@functools.lru_cache(maxsize=None)
def _raw(ticker, asset):
    if asset == "stock":
        x = pd.read_csv(f"{PX}/stock/{ticker}.csv", parse_dates=["date"]).set_index("date")
        x["close_ts"] = (x.index + pd.Timedelta(hours=16)).tz_localize(NY)
    else:
        x = pd.read_csv(f"{PX}/crypto/{ticker}.csv"); x["ts_utc"] = pd.to_datetime(x["ts_utc"], utc=True); x = x.set_index("ts_utc")
    return x

def history(ticker, asset, asof, lookback=400):
    """Daily OHLCV+amount candles fully completed at `asof` (tz-aware). Index = bar timestamp (tz-naive)."""
    asof = pd.Timestamp(asof)
    x = _raw(ticker, asset)
    if asset == "stock":
        h = x[x["close_ts"] <= asof][["open","high","low","close","volume"]].copy()
    else:
        end = asof.tz_convert("UTC").floor("h")
        hr = x[(x.index + pd.Timedelta(hours=1)) <= end]
        hr = hr[hr.index >= end - pd.Timedelta(days=lookback + 1)]
        k = ((end - hr.index) / pd.Timedelta(hours=24)).astype(int)    # 0 = most recent 24h block
        g = hr.groupby(k.values)
        h = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                          "close": g["close"].last(), "volume": g["volume"].sum()})
        h.index = [(end - pd.Timedelta(hours=24 * (i + 1))).tz_localize(None) for i in h.index]
        h = h.sort_index()
        h = h[g.size().sort_index(ascending=False).values >= 20] if len(h) else h   # drop blocks with big gaps
    h["amount"] = h["close"] * h["volume"]
    h.index = pd.DatetimeIndex(h.index).tz_localize(None) if getattr(h.index, "tz", None) else pd.DatetimeIndex(h.index)
    return h.iloc[-lookback:]

def steps(asset, asof, horizon_days):
    """Calendar horizon -> number of daily bars (stocks: weekdays; crypto: days)."""
    if asset == "crypto": return max(1, int(round(horizon_days)))
    start = pd.Timestamp(asof).tz_convert(NY).normalize().tz_localize(None)
    end = start + pd.Timedelta(days=horizon_days)
    return max(1, len(pd.bdate_range(start + pd.Timedelta(days=1), end)))

def future_dates(asset, last_bar, n):
    if asset == "crypto": return pd.date_range(last_bar + pd.Timedelta(days=1), periods=n, freq="D")
    return pd.bdate_range(last_bar + pd.Timedelta(days=1), periods=n)

def realized_fixed(ticker, asset, asof, n):
    """Return from the last visible close at asof to the close n daily bars later (None if not yet available)."""
    x = _raw(ticker, asset); asof = pd.Timestamp(asof)
    if asset == "stock":
        vis = x[x["close_ts"] <= asof]; fut = x[x["close_ts"] > asof]
        if len(vis) == 0 or len(fut) < n: return None
        return fut["close"].iloc[n - 1] / vis["close"].iloc[-1] - 1
    end = asof.tz_convert("UTC").floor("h")
    p0 = x[(x.index + pd.Timedelta(hours=1)) <= end]["close"]
    tgt = end + pd.Timedelta(days=n)
    p1 = x[(x.index + pd.Timedelta(hours=1)) <= tgt]["close"]
    if len(p0) == 0 or x.index[-1] + pd.Timedelta(hours=1) < tgt: return None
    return p1.iloc[-1] / p0.iloc[-1] - 1
