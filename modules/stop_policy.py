"""Direction-specific stock stops shared by the tracker, the scanner, and the simulated account.

Current policy (Ilan, with the 01.11.2026 intraday-touch approval):
  * US stock LONG  trailing chandelier = 5 x ATR14
  * US stock SHORT trailing chandelier = 4 x ATR14 (unchanged)
  * Crypto LONG stays a fixed 3 x ATR14 stop on the close. Crypto shorts stay frozen.

A level that is judged against bar j is built only from bars strictly before j.
The level computed from bar j's own close and ATR applies to bar j+1. It is never
applied to bar j's low (long) or high (short).

Touch fill: long exits when Low <= level, short when High >= level.
The fill is the worse of the open and the level (a gap through the stop fills at the open).
The trailing level only ratchets in the trade's favour.
"""
from __future__ import annotations

LEGACY_STOCK_ATR_MULT = {"LONG": 4.0, "SHORT": 4.0}
CURRENT_STOCK_ATR_MULT = {"LONG": 5.0, "SHORT": 4.0}
CRYPTO_LONG_ATR_MULT = 3.0


def _direction(direction: str) -> str:
    d = str(direction).upper()
    if d not in ("LONG", "SHORT"):
        raise ValueError("direction must be LONG or SHORT")
    return d


def _finite(v) -> bool:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return False
    return v == v and v not in (float("inf"), float("-inf"))


def stock_atr_mult(direction: str, legacy: bool = False) -> float:
    """ATR multiplier for a US stock trailing stop. legacy=True keeps the pre-approval 4x/4x table."""
    table = LEGACY_STOCK_ATR_MULT if legacy else CURRENT_STOCK_ATR_MULT
    return float(table[_direction(direction)])


def stop_atr_mult(asset: str, direction: str, legacy: bool = False):
    """Active multiplier for asset+direction. Crypto shorts have no stop (None)."""
    asset = str(asset).lower()
    direction = _direction(direction)
    if asset == "crypto":
        return CRYPTO_LONG_ATR_MULT if direction == "LONG" else None
    return stock_atr_mult(direction, legacy=legacy)


def _mult(direction: str, legacy: bool = False, atr_mult=None) -> float:
    return float(atr_mult) if atr_mult is not None else stock_atr_mult(direction, legacy=legacy)


def initial_stop_price(direction: str, entry_price: float, atr: float, legacy: bool = False, atr_mult=None) -> float:
    """entry -/+ mult * ATR of the last bar completed before the entry."""
    sgn = 1 if _direction(direction) == "LONG" else -1
    return float(entry_price) - sgn * _mult(direction, legacy, atr_mult) * float(atr)


def chandelier_raw(direction: str, extreme_close: float, atr: float, mult: float) -> float:
    sgn = 1 if _direction(direction) == "LONG" else -1
    return float(extreme_close) - sgn * float(mult) * float(atr)


def ratchet(direction: str, previous, raw: float) -> float:
    """Longs keep the higher level, shorts the lower. A missing previous level adopts raw."""
    raw = float(raw)
    if previous is None or not _finite(previous):
        return raw
    previous = float(previous)
    if _direction(direction) == "LONG":
        return max(previous, raw)
    return min(previous, raw)


def trailing_level(direction: str, previous, extreme_close: float, atr: float, legacy: bool = False, atr_mult=None) -> float:
    """Next session's stop from a completed bar. Caller must not use it on that same bar's high/low."""
    mult = _mult(direction, legacy, atr_mult)
    return ratchet(direction, previous, chandelier_raw(direction, extreme_close, atr, mult))


def touch_fill(direction: str, open_, high, low, level):
    """Exit price, or None when the bar does not reach `level`.

    Long: Low <= level, fill = min(open, level). Short: High >= level, fill = max(open, level).
    """
    o, h, l, lv = float(open_), float(high), float(low), float(level)
    if _direction(direction) == "LONG":
        return float(min(o, lv)) if l <= lv else None
    return float(max(o, lv)) if h >= lv else None


def _fold(direction: str, extreme, close: float):
    close = float(close)
    if extreme is None:
        return close
    if _direction(direction) == "LONG":
        return max(float(extreme), close)
    return min(float(extreme), close)


def walk_trailing_stop(opens, highs, lows, closes, atr, direction: str, entry_index: int, initial_stop: float, mult: float) -> dict:
    """Causal trailing touch stop.

    Bar j is judged with the level fixed from bars < j. Bar j's close updates the
    level only for the returned next_level (the following session).
    `entry_index` is the first bar the position can exit on (the entry session).
    Bars before it are ignored: no entry, no exit.
    """
    direction = _direction(direction)
    n = len(closes)
    k = int(entry_index)
    init = float(initial_stop)
    if k < 0 or k >= n:
        return dict(stopped=False, stop_index=None, exit_price=None, initial_stop=init,
                    next_level=init, next_level_raw=init, level_checked=None, note="no entry bar")
    lv = init
    ext = None
    for j in range(k, n):
        if j > k:
            ext = _fold(direction, ext, closes[j - 1])
            if _finite(atr[j - 1]):
                lv = ratchet(direction, lv, chandelier_raw(direction, ext, atr[j - 1], mult))
        hit = touch_fill(direction, opens[j], highs[j], lows[j], lv)
        if hit is not None:
            return dict(stopped=True, stop_index=j, exit_price=hit, initial_stop=init,
                        next_level=lv, next_level_raw=lv, level_checked=lv)
    ext_next = _fold(direction, ext, closes[n - 1])
    if _finite(atr[n - 1]):
        raw = chandelier_raw(direction, ext_next, atr[n - 1], mult)
        nxt = ratchet(direction, lv, raw)
    else:
        raw = nxt = lv
    return dict(stopped=False, stop_index=None, exit_price=None, initial_stop=init,
                next_level=nxt, next_level_raw=raw, level_checked=lv)


def replay_trailing(opens, highs, lows, closes, atr, direction: str, entry_index: int, entry_price: float,
                    legacy: bool = False, atr_mult=None) -> dict:
    """Simulated-account trailing stop for one position. Same walk as the tracker/scanner."""
    direction = _direction(direction)
    mult = _mult(direction, legacy, atr_mult)
    k = int(entry_index)
    if k <= 0 or k >= len(closes) or not _finite(atr[k - 1]):
        return dict(stopped=False, stop_index=None, exit_price=None, initial_stop=None,
                    next_level=None, next_level_raw=None, level_checked=None, mult=mult, note="no entry")
    init = initial_stop_price(direction, entry_price, atr[k - 1], atr_mult=mult)
    out = walk_trailing_stop(opens, highs, lows, closes, atr, direction, k, init, mult)
    out["mult"] = mult
    return out


def dedup_earliest(rows, ticker="ticker", direction="direction", entry_date="entry_date"):
    """One row per ticker+direction: the earliest entry. A missing entry date sorts first (already open).

    Ties keep the earlier row in `rows`. Output order follows the kept rows' original positions.
    """
    best = {}
    for i, r in enumerate(rows):
        key = (str(r[ticker]).upper(), str(r[direction]).upper())
        ed = r[entry_date] if entry_date in r else None
        rank = ("" if ed in (None, "") else str(ed), i)
        prev = best.get(key)
        if prev is None or rank < prev[0]:
            best[key] = (rank, i, r)
    return [best[k][2] for k in sorted(best, key=lambda k: best[k][1])]
