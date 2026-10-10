"""stop_rules — point-in-time ATR stop logic shared by the backtests and the live scanner.

Everything here is causal: a stop level that applies to bar j is computed ONLY from data of bars <= j-1
(the extreme close and ATR14 of the last completed bar). Call order per new daily bar j:

    st = ChandelierStop(direction='LONG', entry_price=fill, atr_at_entry=atr14_of_bar_before_alert,
                        k=4.0, mode='ratchet', tighten_at_R=4.5, k2=3.0)
    st.start(close_of_entry_bar)                 # after the entry bar closes
    ...for every later bar j:
    lvl = st.level(atr_prev=atr14[j-1])          # stop that is live during bar j (uses closes <= j-1)
    if close-based:  exit if close[j] <= lvl (long) / >= lvl (short), fill at close[j]
    if intraday:     exit if low[j] <= lvl (long) / high[j] >= lvl (short), fill at the worse of open[j] and lvl
    else: st.on_close(close[j])                  # update extreme / MFE with the completed bar

Modes
  'plain'   : stop_j = extreme - k*ATR[j-1]               (classic chandelier; can LOOSEN when ATR expands)
  'ratchet' : stop_j = max(stop_{j-1}, extreme - k*ATR[j-1])   (never loosens; mirror min() for shorts)
  'floor'   : stop_j = max(initial_stop, extreme - k*ATR[j-1])  (never below the initial stop, otherwise plain)
  'fixed'   : stop_j = initial_stop (= entry -/+ r_mult*ATR_at_entry), never moves
R = initial stop distance = r_mult * atr_at_entry (default r_mult = k = 4 -> R = 4 ATR).
Tighten-after-profit: once the max favourable CLOSE since entry reaches tighten_at_R * R (measured with closes
<= j-1), the multiplier switches from k to k2 for all later bars (sticky). Usually combined with mode='ratchet'.

`atr_wilder(high, low, close, n=14)` returns Wilder's ATR (first value = mean of the first n true ranges);
value i uses bars <= i only.

Reference results (scanner setups Jul-Oct 2026): see results.md §3.13 in /workspace/trading-frameworks-eval.
"""
from __future__ import annotations
import math
import numpy as np

__all__ = ["atr_wilder", "ChandelierStop", "r_multiple"]


def atr_wilder(high, low, close, n: int = 14) -> np.ndarray:
    h, l, c = (np.asarray(x, dtype=float) for x in (high, low, close))
    out = np.full(len(c), np.nan)
    if len(c) <= n:
        return out
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.c_[h - l, np.abs(h - pc), np.abs(l - pc)], axis=1)
    tr[0] = h[0] - l[0]
    out[n - 1] = tr[:n].mean()
    for i in range(n, len(c)):
        out[i] = (out[i - 1] * (n - 1) + tr[i]) / n
    return out


class ChandelierStop:
    def __init__(self, direction: str, entry_price: float, atr_at_entry: float, k: float = 4.0,
                 mode: str = "ratchet", tighten_at_R: float | None = None, k2: float | None = None,
                 r_mult: float | None = None):
        if direction not in ("LONG", "SHORT"):
            raise ValueError("direction must be LONG or SHORT")
        if mode not in ("plain", "ratchet", "floor", "fixed"):
            raise ValueError("mode must be plain|ratchet|floor|fixed")
        self.sgn = 1 if direction == "LONG" else -1
        self.entry = float(entry_price)
        self.k = float(k)
        self.k2 = None if k2 is None else float(k2)
        self.tighten_at_R = tighten_at_R
        self.mode = mode
        self.R = (self.k if r_mult is None else float(r_mult)) * float(atr_at_entry)   # price distance of 1R
        self.initial_stop = self.entry - self.sgn * self.R
        self.extreme = None          # best close since (and including) the entry bar
        self.stop = None             # last live stop level
        self.tightened = False
        self.mfe_R = 0.0             # max favourable close excursion in R (closes processed so far)

    def start(self, entry_bar_close: float) -> None:
        self.extreme = float(entry_bar_close)
        self._mfe()

    def on_close(self, close: float) -> None:
        c = float(close)
        self.extreme = max(self.extreme, c) if self.sgn == 1 else min(self.extreme, c)
        self._mfe()

    def _mfe(self) -> None:
        if self.R > 0:
            self.mfe_R = max(self.mfe_R, self.sgn * (self.extreme - self.entry) / self.R)
        if (self.tighten_at_R is not None and self.k2 is not None and not self.tightened
                and self.mfe_R >= self.tighten_at_R):
            self.tightened = True

    def level(self, atr_prev: float) -> float:
        """Stop level live during the next bar; atr_prev = ATR14 of the last COMPLETED bar."""
        if self.mode == "fixed":
            self.stop = self.initial_stop
            return self.stop
        k = self.k2 if self.tightened else self.k
        if atr_prev is None or not math.isfinite(atr_prev):
            raw = self.stop if self.stop is not None else self.initial_stop
        else:
            raw = self.extreme - self.sgn * k * float(atr_prev)
        if self.mode == "plain":
            lvl = raw
        elif self.mode == "floor":
            lvl = max(raw, self.initial_stop) if self.sgn == 1 else min(raw, self.initial_stop)
        else:  # ratchet
            if self.stop is None:
                lvl = raw
            else:
                lvl = max(self.stop, raw) if self.sgn == 1 else min(self.stop, raw)
        self.stop = lvl
        return lvl


def r_multiple(ret_frac: float, entry_price: float, R_price: float) -> float:
    """Convert a fractional trade return into R (1R = initial stop distance)."""
    return ret_frac / (R_price / entry_price)
