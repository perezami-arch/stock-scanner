"""Tool interface. A tool answers: given only data visible at `asof_ts`, what return do you expect for `ticker`
over the next `horizon_days` bars (US: trading days; crypto: 24h days)? Higher = more bullish.
Implement `score` (single) or override `score_batch` for efficiency. Return NaN if you cannot score."""
import numpy as np, pandas as pd
import pit

class Tool:
    name = "tool"
    rank_only = False          # True if the score is a ranking signal, not a return forecast (sign is meaningless)
    def score(self, ticker, asset, asof_ts, horizon_days) -> float:
        raise NotImplementedError
    def score_batch(self, reqs):
        """reqs: list of (ticker, asset, asof_ts, horizon_days). Returns list of floats."""
        return [self.score(*r) for r in reqs]

class RandomWalk(Tool):
    name = "Random walk (0)"
    def score(self, ticker, asset, asof_ts, horizon_days): return 0.0

class Momentum121(Tool):
    """12-1 momentum: return from t-12m to t-1m (stocks 252/21 bars; crypto 365/30 days). Point-in-time."""
    name = "Momentum 12-1"; rank_only = True
    def score(self, ticker, asset, asof_ts, horizon_days):
        try: c = pit.history(ticker, asset, asof_ts, lookback=400)["close"]
        except FileNotFoundError: return np.nan
        if asset == "stock":
            return c.iloc[-1 - 21] / c.iloc[-1 - 252] - 1 if len(c) >= 253 else np.nan
        last = c.index[-1]   # crypto: calendar-based (hourly-data gaps can drop a few 24h candles)
        p1, p0 = c[c.index <= last - pd.Timedelta(days=30)], c[c.index <= last - pd.Timedelta(days=365)]
        if len(p0) == 0 or (last - pd.Timedelta(days=365) - p0.index[-1]) > pd.Timedelta(days=5): return np.nan
        return p1.iloc[-1] / p0.iloc[-1] - 1

class LowVol60(Tool):
    """Low volatility: minus the std of the last 60 daily log returns. Point-in-time."""
    name = "Low-vol 60d"; rank_only = True
    def score(self, ticker, asset, asof_ts, horizon_days):
        try: c = pit.history(ticker, asset, asof_ts, lookback=62)["close"]
        except FileNotFoundError: return np.nan
        if len(c) < 61: return np.nan
        return -np.log(c).diff().dropna().iloc[-60:].std()

REGISTRY = {"rw": RandomWalk, "mom121": Momentum121, "lowvol": LowVol60}
