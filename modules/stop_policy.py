"""Direction-specific stock stops shared by the tracker, the scanner, and the simulated account.

Two dates, not one:
  * 2026-11-01: stock stops trigger on an intraday touch. Fill is the worse of the stop and the open.
  * 2026-11-07: US stock LONG trailing chandelier becomes 5 x ATR14. SHORT stays 4 x ATR14.
  * Crypto LONG stays a fixed 3 x ATR14 stop on the close. Crypto shorts stay frozen.
A recorded exit is never recomputed. A committed live stop is a floor from 2026-11-07, so 5x cannot loosen it.

A level that is judged against bar j is built only from bars strictly before j.
The level computed from bar j's own close and ATR applies to bar j+1. It is never
applied to bar j's low (long) or high (short).

Touch fill: long exits when Low <= level, short when High >= level.
The fill is the worse of the open and the level (a gap through the stop fills at the open).
The trailing level only ratchets in the trade's favour.
"""
from __future__ import annotations

import datetime as _dt

LEGACY_STOCK_ATR_MULT = {"LONG": 4.0, "SHORT": 4.0}
CURRENT_STOCK_ATR_MULT = {"LONG": 5.0, "SHORT": 4.0}
CRYPTO_LONG_ATR_MULT = 3.0
# 2026-11-01 (PR #10, a008a20): intraday touch, fill = worse of stop and open.
# 2026-11-07: LONG multiplier 4x -> 5x only. Touch does not start on this date.
TOUCH_EFFECTIVE = _dt.date(2026, 11, 1)
LONG_5X_EFFECTIVE = _dt.date(2026, 11, 7)
POLICY_EFFECTIVE = LONG_5X_EFFECTIVE   # multiplier date; not the touch date


def _direction(direction: str) -> str:
    d = str(direction).upper()
    if d not in ("LONG", "SHORT"):
        raise ValueError("direction must be LONG or SHORT")
    return d


def as_date(value):
    """datetime / Timestamp / ISO string -> datetime.date. None stays None."""
    if value is None:
        return None
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    text = str(value).strip()
    if text in ("", "None", "nan", "NaT"):
        return None
    return _dt.date.fromisoformat(text[:10])


def _finite(v) -> bool:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return False
    return v == v and v not in (float("inf"), float("-inf"))


def stock_atr_mult(direction: str, legacy: bool = False, on_date=None, policy_from=None) -> float:
    """ATR multiplier for a US stock trailing stop.

    legacy=True keeps the pre-approval 4x/4x table. A long bar before policy_from (the 5x date,
    2026-11-07) also stays at 4x. Touch is a separate date and does not change this multiplier.
    Shorts are 4x on every date. policy_from=None means the current table, including 5x longs.
    """
    direction = _direction(direction)
    if legacy or (direction == "LONG" and on_date is not None and policy_from is not None and as_date(on_date) < as_date(policy_from)):
        return float(LEGACY_STOCK_ATR_MULT[direction])
    return float(CURRENT_STOCK_ATR_MULT[direction])


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


def _bar_date(dates, j):
    if dates is None:
        return None
    return as_date(dates[j])


def walk_trailing_stop(opens, highs, lows, closes, atr, direction: str, entry_index: int, initial_stop: float, mult: float,
                       dates=None, policy_from=None, floor=None, touch: bool = True, touch_from=None) -> dict:
    """Causal trailing stop.

    Bar j is judged with the level fixed from bars < j. Bar j's close updates the
    level only for the returned next_level (the following session).
    `entry_index` is the first bar the position can exit on (the entry session).
    Bars before it are ignored: no entry, no exit.

    `policy_from` is the LONG 5x date (2026-11-07): a long uses 4xATR14 before it and
    `mult` on/after it. `touch_from` is the intraday-touch date (2026-11-01). Earlier
    bars are close-checked. The two dates are independent. `floor` (a committed live
    stop) binds on/after the 5x date and on next_level, so 5x cannot loosen it.
    policy_from=None and touch_from=None apply `mult` and `touch` on every bar.
    """
    direction = _direction(direction)
    n = len(closes)
    k = int(entry_index)
    init = float(initial_stop)
    long_5x = as_date(policy_from) if policy_from is not None else None
    touch_on = as_date(touch_from) if touch_from is not None else None
    if k < 0 or k >= n:
        return dict(stopped=False, stop_index=None, exit_price=None, initial_stop=init,
                    next_level=init, next_level_raw=init, level_checked=None, note="no entry bar", exit_mode=None)

    def mult_j(j):
        day = _bar_date(dates, j)
        if long_5x is not None and day is not None and direction == "LONG" and day < long_5x:
            return float(LEGACY_STOCK_ATR_MULT["LONG"])
        return float(mult)

    def touch_j(j):
        if not touch:
            return False
        day = _bar_date(dates, j)
        if touch_on is None or day is None:
            return True
        return day >= touch_on

    def with_floor(j, level):
        if not _finite(floor):
            return level
        day = _bar_date(dates, j)
        if long_5x is not None and day is not None and day < long_5x:
            return level
        return ratchet(direction, floor, level)

    lv = init
    ext = None
    for j in range(k, n):
        raw = lv
        if j > k:
            ext = _fold(direction, ext, closes[j - 1])
            if _finite(atr[j - 1]):
                raw = chandelier_raw(direction, ext, atr[j - 1], mult_j(j))
                lv = ratchet(direction, lv, raw)
        lv = with_floor(j, lv)
        if touch_j(j):
            hit = touch_fill(direction, opens[j], highs[j], lows[j], lv)
            mode = "touch"
        else:
            sgn = 1 if direction == "LONG" else -1
            hit = float(closes[j]) if sgn * (float(closes[j]) - lv) <= 0 else None
            mode = "close"
        if hit is not None:
            return dict(stopped=True, stop_index=j, exit_price=hit, initial_stop=init,
                        next_level=lv, next_level_raw=raw, level_checked=lv, exit_mode=mode)
    ext_next = _fold(direction, ext, closes[n - 1])
    end_mult = mult_j(n - 1)
    if _finite(atr[n - 1]):
        raw = chandelier_raw(direction, ext_next, atr[n - 1], end_mult)
        nxt = ratchet(direction, lv, raw)
    else:
        raw = nxt = lv
    nxt = with_floor(n - 1, nxt)
    if _finite(floor):
        nxt = ratchet(direction, floor, nxt)   # the published live stop never loosens past the committed floor
    return dict(stopped=False, stop_index=None, exit_price=None, initial_stop=init,
                next_level=nxt, next_level_raw=raw, level_checked=lv, exit_mode=None)


def account_stop_hit(direction: str, open_, high, low, stop, day, touch_from=TOUCH_EFFECTIVE):
    """Exit price for one already-tracked account stop, or None.

    The level is the committed stop. This does not recompute a wider 5x stop.
    Before 2026-11-01 a touch exits at that stop (the pre-touch account fill).
    On/after 2026-11-01 the fill is the worse of the stop and the open. That is the
    touch date, not the 2026-11-07 long-multiplier date.
    """
    if stop is None or not _finite(stop):
        return None
    direction = _direction(direction)
    touched = touch_fill(direction, open_, high, low, stop)
    if touched is None:
        return None
    when = as_date(day)
    start = as_date(touch_from) if touch_from is not None else None
    if start is not None and when is not None and when < start:
        return float(stop)
    return touched


def apply_account_exit(existing, direction, open_, high, low, stop, day):
    """Keep a recorded (date, price) exit. Only an open position can receive a new fill."""
    if existing is not None:
        return existing
    hit = account_stop_hit(direction, open_, high, low, stop, day)
    if hit is None:
        return None
    return (str(as_date(day)), hit)


def replay_trailing(opens, highs, lows, closes, atr, direction: str, entry_index: int, entry_price: float,
                    legacy: bool = False, atr_mult=None, dates=None, policy_from=None, floor=None) -> dict:
    """Simulated-account trailing stop for one position. Same walk as the tracker/scanner.

    policy_from defaults to None here (one multiplier for the whole path). The live account
    book does not rebuild old exits with this function; it keeps committed stops and uses
    apply_account_exit. Pass policy_from=LONG_5X_EFFECTIVE to adopt 5x only from that date.
    """
    direction = _direction(direction)
    k = int(entry_index)
    if dates is not None and k < len(dates):
        mult = stock_atr_mult(direction, legacy=legacy, on_date=dates[k], policy_from=policy_from) if atr_mult is None else float(atr_mult)
    else:
        mult = _mult(direction, legacy, atr_mult)
    if k <= 0 or k >= len(closes) or not _finite(atr[k - 1]):
        return dict(stopped=False, stop_index=None, exit_price=None, initial_stop=None,
                    next_level=None, next_level_raw=None, level_checked=None, mult=mult, note="no entry", exit_mode=None)
    init = initial_stop_price(direction, entry_price, atr[k - 1], atr_mult=mult)
    out = walk_trailing_stop(opens, highs, lows, closes, atr, direction, k, init, mult,
                             dates=dates, policy_from=policy_from, floor=floor, touch=True)
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
