"""Active stop rules (approved by Ilan 08.10.2026) + EXPERIMENTAL Fib/Elliott columns for the live scanner.

DEFINITIONS REUSED FROM THE RESEARCHER'S BACKTEST (/workspace/trading-frameworks-eval/results.md 3.10-3.12):
  * atr14()  - Wilder ATR14, and zigzag() - ATR-threshold zigzag with (kind, price, pivot_idx, confirm_idx):
               exec'd unchanged from iaf/sim_fib.py, exactly the way sim_chand/sim_struct/sim_targets load them.
  * cci(), feats() - the existing SHORT rule (ck_score >= 3 AND close < SMA200): exec'd unchanged from iaf/prep.py.
  * chandelier (close mode) = sim_chand.py 'c'; fixed ATR stop = sim_fib.py atr3 'c'; structure stop (c) origin-1.0xATR with
    deeper-pivot fallback = sim_struct.py; extensions / Elliott w3,w5 targets / hybrid 1/2 at 1.618 = sim_targets.py.
  * Point-in-time: stock bars via scanner-tool-eval pit.history (bar visible after its 16:00 ET close <= scan time);
    crypto = Yahoo UTC daily bars (same source as the backtest frames), bar D usable once D+1 00:00 UTC <= scan time.

ACTIVE RULES
  1. US stock LONG : chandelier, intraday touch, 5xATR14 (Ilan: 5x with the 01.11 touch approval; was 4x).
                     The level judged on bar j uses only closes and ATR through j-1. The level computed from bar j's own
                     close is next_level for bar j+1 and is NOT applied to bar j's low. level_j = max(level_{j-1},
                     max(close since entry through j-1) - 5*ATR14[j-1]), starting at the initial stop (17.10: ratchet -
                     never loosens, never below the initial stop). Exit when Low <= level; fill = worse of level and Open.
                     Initial stop = entry - 5*ATR14 (ATR of the last completed bar before the entry).
     + ACTIVE partial exit (v2, 08.10 13:28, unchanged): take 1/2 at the Fib 1.618 extension of the last confirmed 2xATR
                     zigzag leg (sim_targets.py HY2: origin + 1.618*(end-origin); if already behind entry -> the next
                     extension 2.618), close-checked from the entry bar + 2; the rest stays under the 5xATR chandelier.
                     No confirmed swing / no extension beyond entry -> pure chandelier + flag.
  2. US stock SHORT: only if it passes the short rule (ck_score>=3 & close<SMA200). Multiplier stays 4xATR14.
                     level_j = min(level_{j-1}, min(close since entry through j-1) + 4*ATR14[j-1]) (v2: 4x, was 3x),
                     same causal bar: today's close does not tighten today's high. Exit when High >= level; fill = worse
                     of level and Open. Initial = entry + 4*ATR14. Shorts failing the rule get NO stop and short_rule_pass=False.
  3. Crypto LONG   : fixed stop = entry - 3*ATR14, checked on the daily (UTC) close, no trailing, no take-profit target.
  4. Crypto SHORT  : FROZEN. Never output as a setup; written to frozen_crypto_shorts (separate CSV) for measurement only.
EXPERIMENTAL (logged only, never changes the active stop/targets): see fib_elliott().
"""
import os as _sr_os; _SCANNER_ROOT = _sr_os.environ.get('SCANNER_ROOT', '/workspace')  # repo-portable root (default: the box)
import os, sys, json, argparse, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, _SCANNER_ROOT)
import scanner_momentum as SM
import stop_policy as SPOL

IAF = (_SCANNER_ROOT + "/trading-frameworks-eval/iaf/")
_s = open(IAF + "sim_fib.py").read(); exec(_s[_s.index("def atr14"):_s.index("def clock")])           # atr14, zigzag
_p = open(IAF + "prep.py").read()
exec(_p[_p.index("def cci"):_p.index("cache={}")]); exec(_p[_p.index("def feats"):_p.index("rows=[]")])  # cci, feats

ZZ = 2.0                                   # zigzag reversal threshold in ATRs (backtest value)
RET = [0.382, 0.5, 0.618, 0.786]; EXT = [1.272, 1.618, 2.618]
# 01.11.2026 (Ilan): stock stops trigger on an INTRADAY TOUCH (long: Low<=level, short: High>=level), fill = worse of level and Open.
# Long multiplier is 5xATR14; short stays 4xATR14. Both come from stop_policy so the tracker, scanner and account match.
RULES = {("stock", "LONG"):  dict(stop_type="chandelier_touch", stop_atr_mult=SPOL.stock_atr_mult("LONG"), trailing=True),
         ("stock", "SHORT"): dict(stop_type="chandelier_touch", stop_atr_mult=SPOL.stock_atr_mult("SHORT"), trailing=True),   # v2 08.10: 4x (was 3x); not changed with the long 5x
         ("crypto", "LONG"): dict(stop_type="fixed_close", stop_atr_mult=SPOL.CRYPTO_LONG_ATR_MULT, trailing=False)}
FIB_TOL = 0.10                             # a wave ratio "deviates" if it is >10% (relative) away from every allowed Fib ratio
W2_R = [0.382, 0.5, 0.618, 0.786]; W3_X = [1.0, 1.272, 1.618, 2.618]; W4_R = [0.236, 0.382, 0.5]; W5_X = [0.618, 1.0, 1.618]
FIB_NUMS = [5, 8, 13, 21, 34, 55, 89, 144, 233]
STOP_COLS = ["stop_type", "stop_atr_mult", "atr14_wilder", "stop_entry_ref", "initial_stop", "initial_stop_pct", "short_rule_pass",
             "short_ck_score", "below_sma200", "frozen_crypto_short", "tp_half_1618", "partial_exit_rule", "tp_half_fallback"]
EXP_COLS = ["fib_leg_origin", "fib_leg_end", "fib_r382", "fib_r500", "fib_r618", "fib_r786", "fib_stop_struct", "fib_stop_fallback",
            "fib_tp_1272", "fib_tp_1618", "fib_tp_2618", "elliott_count_valid", "elliott_wave_label", "elliott_fib_deviations",
            "elliott_n_valid_counts", "elliott_target_w3", "elliott_target_w5", "fib_time_target_date", "fib_time_anchor",
            "pivots_confirmed"]   # alt_exit_half_at_1618 became ACTIVE (tp_half_1618 / partial_exit_rule) on 08.10

# ---------------------------------------------------------------- data (point-in-time)
def daily_bars(ticker, asset, asof, px_dir):
    """Daily OHLCV with only bars complete at `asof`. Columns Open/High/Low/Close/Volume (backtest frame layout)."""
    asof = pd.Timestamp(asof).tz_convert("UTC")
    sym = SM.yahoo_symbol(ticker, asset)
    if asset == "stock":
        pit, _ = SM._load_eval(px_dir)
        if SM.fetch(sym, "stock", asof, px_dir): return None
        h = pit.history(sym, "stock", asof, lookback=10000)
    else:
        import yfinance as yf
        f = f"{px_dir}/crypto_daily/{sym}.csv"; os.makedirs(os.path.dirname(f), exist_ok=True)
        if not os.path.exists(f):
            try: x = yf.download(sym, start=(asof - pd.Timedelta(days=700)).strftime("%Y-%m-%d"),
                                 end=(asof + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), interval="1d", auto_adjust=True, progress=False)
            except Exception: return None
            if isinstance(x.columns, pd.MultiIndex): x.columns = x.columns.get_level_values(0)
            if x.empty: return None
            x.index.name = "date"; x.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna().to_csv(f)
        h = pd.read_csv(f, parse_dates=["date"]).set_index("date")
        h = h[(h.index + pd.Timedelta(days=1)) <= asof.tz_localize(None)]       # UTC day D complete at D+1 00:00
    if h is None or len(h) == 0: return None
    h = h.rename(columns=str.title)[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
    return h

# ---------------------------------------------------------------- active stops
def short_rule(x):
    """Existing short rule from iaf/prep.py + analyze.py: ck_score >= 3 and close < SMA200 (on the last completed bar)."""
    x = x.copy(); x["SMA20"] = x.Close.rolling(20).mean(); x["SMA200"] = x.Close.rolling(200).mean(); x["CCI"] = cci(x)
    f = feats(x, len(x) - 1, -1)
    ck, b200 = f.get("ck_score"), f.get("below_sma200")
    ok = (ck is not None and ck >= 3) and (b200 == 1)
    return bool(ok), ck, (None if b200 is None or (isinstance(b200, float) and np.isnan(b200)) else int(b200))

def active_stop(x, asset, direction, entry=None, atr_mult=None):
    """Initial active stop for a new setup. entry=None -> last close is the reference (scan output before a trigger exists).
    atr_mult overrides the policy table (legacy 4x longs). It does not change the Fib 1.618 half-target price."""
    direction = direction.upper(); r = {c: None for c in STOP_COLS}; r["frozen_crypto_short"] = False
    a = atr14(x.High.values, x.Low.values, x.Close.values); A = a[-1] if len(a) else np.nan
    r["atr14_wilder"] = round(float(A), 4) if np.isfinite(A) else None
    ref = float(entry) if entry is not None and pd.notna(entry) else float(x.Close.iloc[-1])
    r["stop_entry_ref"] = "entry" if entry is not None and pd.notna(entry) else "last_close"
    if asset == "crypto" and direction == "SHORT":
        r["frozen_crypto_short"] = True; r["stop_type"] = "FROZEN (crypto short)"; return r
    if asset == "stock" and direction == "SHORT":
        ok, ck, b = short_rule(x); r.update(short_rule_pass=ok, short_ck_score=ck, below_sma200=b)
        if not ok: r["stop_type"] = "none (short rule failed)"; return r
    rule = dict(RULES[(asset, direction)])
    if atr_mult is not None: rule["stop_atr_mult"] = float(atr_mult)
    r["stop_type"] = rule["stop_type"]; r["stop_atr_mult"] = rule["stop_atr_mult"]
    if asset == "stock" and direction == "LONG": r.update(half_at_1618(x, ref, a, atr_mult=rule["stop_atr_mult"]))
    if np.isfinite(A):
        st = SPOL.initial_stop_price(direction, ref, A, atr_mult=rule["stop_atr_mult"])
        r["initial_stop"] = round(float(st), 4); r["initial_stop_pct"] = round(float(abs(ref - st) / ref * 100), 2)
    return r

def half_at_1618(x, ref, a=None, atr_mult=None):
    """ACTIVE for US stock longs (sim_targets.py variant HY2). Leg = last confirmed swing HIGH H1 + its origin LOW L0 (2xATR zigzag,
    pivots confirmed on/before the last completed bar). allext = L0 + r*(H1-L0), r in 1.272/1.618/2.618; target = the first
    extension >= the 1.618 level that is still beyond the entry; none -> pure chandelier (flagged). The 1.618 price does not
    depend on the stop multiplier; the text names whichever chandelier the remainder sits under."""
    ktxt = f"{(RULES[('stock', 'LONG')]['stop_atr_mult'] if atr_mult is None else float(atr_mult)):g}"
    h, l, c = x.High.values, x.Low.values, x.Close.values
    a = atr14(h, l, c) if a is None else a
    known = [p for p in (zigzag(h, l, a, ZZ) if len(a) else []) if p[3] <= len(h) - 1]
    idx = [j for j, p in enumerate(known) if p[0] == "H"]
    if not idx or idx[-1] == 0:
        return dict(tp_half_1618=None, tp_half_fallback=True, partial_exit_rule=f"FALLBACK: no confirmed swing -> 100% under {ktxt}xATR chandelier")
    H1, L0 = known[idx[-1]][1], known[idx[-1] - 1][1]; allext = [L0 + f * (H1 - L0) for f in EXT]
    ext = [t for t in allext if t - ref > 0]; cand = [t for t in ext if t - allext[1] >= 0]
    if not cand:
        return dict(tp_half_1618=None, tp_half_fallback=True, partial_exit_rule=f"FALLBACK: 1.618/2.618 already behind entry -> 100% under {ktxt}xATR chandelier")
    lvl = "1.618" if cand[0] == allext[1] else "2.618 (1.618 already behind entry)"
    return dict(tp_half_1618=round(float(cand[0]), 4), tp_half_fallback=False,
                partial_exit_rule=f"1/2 at Fib {lvl} = {cand[0]:.2f} on close; rest under {ktxt}xATR chandelier")

def _ratchet(sgn, prev, raw):
    """never loosen: longs keep the higher of the previous live level and the new chandelier value, shorts the lower."""
    return SPOL.ratchet("LONG" if sgn == 1 else "SHORT", prev, raw)

def _touch(sgn, o, h, l, lv):
    """Intraday-touch exit price or None: long hit if Low<=lv, short if High>=lv; fill = worse of lv and the bar Open (gap)."""
    return SPOL.touch_fill("LONG" if sgn == 1 else "SHORT", o, h, l, lv)

def _half_until(x, C, k, end, sgn, tp_half, half):
    """Close-checked 1/2 at Fib, from the entry bar + 2 up to but not including a same-bar stop. The target price is unchanged."""
    for j in range(k + 2, end):
        if half["half_taken"]: break
        if sgn * (C[j] - float(tp_half)) >= 0:
            half.update(half_taken=True, half_date=str(x.index[j].date()), half_price=float(C[j]))

def stop_status(x, asset, direction, entry_date, entry_price, tp_half=None, atr_mult=None):
    """Live monitoring of an open trade.
    entry bar k = first bar on/after entry_date. No bar on/after entry_date -> no exit (the entry has not traded).
    Crypto fixed stop: first check at the close of k+2; a low that does not close through the stop does not exit.
    Stock trailing stop: level_j = ratchet(level_{j-1}, extreme close through j-1 -/+ K*ATR14[j-1]), K = 5 long / 4 short,
    starting from the initial stop (entry -/+ K*ATR14 of the bar before the entry bar). It only moves in the trade's favour.
    atr_mult overrides K (legacy longs used 4). The raw chandelier is next_level_raw.
    Stock touch (01.11): from the entry bar, long Low / short High vs the level known BEFORE that bar.
    Fill = worse of level and Open. The level built from today's close is next_level for the next session only.
    Stock longs with tp_half: 1/2 at the first close >= tp_half from k+2, and only if the stop did not exit first.
    Returns dict(next_level, initial_stop, stopped, stop_date, stop_close[, half_taken, half_date, half_price]).
    next_level applies to the NEXT session, never to the bar it was calculated from."""
    direction = direction.upper(); sgn = 1 if direction == "LONG" else -1
    rule = RULES.get((asset, direction))
    if rule is None: return dict(next_level=None, stopped=None, note="no active rule (frozen / failed short rule)")
    rule = dict(rule)
    if atr_mult is not None: rule["stop_atr_mult"] = float(atr_mult)
    H, L, C = x.High.values, x.Low.values, x.Close.values; A = atr14(H, L, C); K = float(rule["stop_atr_mult"])
    k = int(np.searchsorted(x.index.values, np.datetime64(pd.Timestamp(entry_date)), side="left"))
    Arule = A[k - 1] if 0 < k <= len(C) else (A[-1] if len(A) else np.nan)
    init = float(SPOL.initial_stop_price(direction, entry_price, Arule, atr_mult=K)) if np.isfinite(Arule) else float("nan")
    has_tp = tp_half is not None and pd.notna(tp_half)
    half = dict(half_taken=False, half_date=None, half_price=None) if has_tp else {}
    if k >= len(C):                              # entry session has not traded
        return dict(next_level=None if not np.isfinite(init) else round(init, 4), initial_stop=None if not np.isfinite(init) else round(init, 4),
                    stopped=False, note="no entry bar yet", **half)
    if not rule["trailing"]:
        if k >= len(C) - 1:                      # fixed stop: no completed close after the entry bar yet
            return dict(next_level=round(init, 4), initial_stop=round(init, 4), stopped=False, note="initial stop (no close after entry bar yet)", **half)
        lv = init
        for j in range(k + 2, len(C)):
            if sgn * (C[j] - lv) <= 0: return dict(next_level=round(lv, 4), initial_stop=round(init, 4), stopped=True, stop_date=str(x.index[j].date()), stop_close=float(C[j]))
        return dict(next_level=round(lv, 4), initial_stop=round(init, 4), stopped=False)
    touch = str(rule["stop_type"]).endswith("_touch")
    O = x.Open.values
    if touch:
        # Shared with the simulated account. Today's close cannot stop today's bar.
        w = SPOL.walk_trailing_stop(O, H, L, C, A, direction, k, init, K)
        if has_tp: _half_until(x, C, k, w["stop_index"] if w["stopped"] else len(C), sgn, tp_half, half)
        if w["stopped"]:
            hit = w["exit_price"]
            return dict(next_level=round(float(w["level_checked"]), 4), initial_stop=round(init, 4), stopped=True,
                        stop_date=str(x.index[w["stop_index"]].date()), stop_close=hit, exit_price=hit, exit_mode="touch", **half)
        return dict(next_level=round(float(w["next_level"]), 4), next_level_raw=round(float(w["next_level_raw"]), 4),
                    initial_stop=round(init, 4), stopped=False, **half)
    if k >= len(C) - 1:                          # close-checked trailing: nothing to check until the bar after entry
        return dict(next_level=round(init, 4), initial_stop=round(init, 4), stopped=False, note="initial stop (no close after entry bar yet)", **half)
    lv = init
    ext = C[k]
    if k + 1 < len(C): ext = max(ext, C[k + 1]) if sgn == 1 else min(ext, C[k + 1])
    for j in range(k + 2, len(C)):
        if np.isfinite(A[j - 1]): lv = _ratchet(sgn, lv, ext - sgn * K * A[j - 1])
        if sgn * (C[j] - lv) <= 0:
            return dict(next_level=round(lv, 4), initial_stop=round(init, 4), stopped=True, stop_date=str(x.index[j].date()),
                        stop_close=float(C[j]), exit_price=float(C[j]), exit_mode="close", **half)
        if has_tp and not half["half_taken"] and sgn * (C[j] - tp_half) >= 0:
            half.update(half_taken=True, half_date=str(x.index[j].date()), half_price=float(C[j]))
        ext = max(ext, C[j]) if sgn == 1 else min(ext, C[j])
    raw = float(ext - sgn * K * A[-1])
    nxt = _ratchet(sgn, lv, raw) if np.isfinite(raw) else lv
    return dict(next_level=round(float(nxt), 4), next_level_raw=round(raw, 4), initial_stop=round(init, 4), stopped=False, **half)

def weighted_return(direction, fill, price, half_price=None):
    """direction-adjusted return of the whole position: 1/2 at half_price (if the half exit was taken) + 1/2 at price."""
    sgn = 1 if str(direction).upper() == "LONG" else -1
    full = sgn * (float(price) / float(fill) - 1)
    if half_price is None or not np.isfinite(float(half_price)): return full
    return 0.5 * sgn * (float(half_price) / float(fill) - 1) + 0.5 * full

# ---------------------------------------------------------------- experimental Fib / Elliott
def _dev(ratio, allowed):
    return 0 if min(abs(ratio - f) / f for f in allowed) <= FIB_TOL else 1

def elliott_counts(known, sgn):
    """All impulse counts (direction sgn) that END on the last confirmed pivot and pass the hard Elliott rules.
    Invalid counts are dropped. Ratios checked: w2/w1, w3/w1, w4/w3, w5/w1 (only those that exist)."""
    if len(known) < 3: return []
    u = [sgn * p[1] for p in known]; kinds = [p[0] for p in known]; up_kind = "H" if sgn == 1 else "L"
    out = []
    for n, label in ((3, "in_W3 (W2 done)"), (4, "in_W4 (W3 done)"), (5, "in_W5 (W4 done)"), (6, "W5_done (correction next)")):
        if len(u) < n: continue
        q = u[-n:]; ks = kinds[-n:]
        if ks[0] == up_kind: continue                            # a bullish count must start at a low (mirrored for shorts)
        w1 = q[1] - q[0]
        if w1 <= 0 or q[2] <= q[0]: continue                     # rule: wave 2 never retraces beyond the start of wave 1
        devs = [_dev((q[1] - q[2]) / w1, W2_R)]
        if n >= 4:
            w3 = q[3] - q[2]
            if q[3] <= q[1]: continue                            # wave 3 must exceed the end of wave 1
            devs.append(_dev(w3 / w1, W3_X))
        if n >= 5:
            if q[4] <= q[1]: continue                            # rule: wave 4 never overlaps wave 1
            devs.append(_dev((q[3] - q[4]) / w3, W4_R))
        if n >= 6:
            w5 = q[5] - q[4]
            if q[5] <= q[3]: continue                            # no truncated 5th accepted
            if w3 < w1 and w3 < w5: continue                     # rule: wave 3 is never the shortest of 1/3/5
            devs.append(_dev(w5 / w1, W5_X))
        P = [p[1] for p in known[-n:]]
        tw3 = P[2] + 1.618 * (P[1] - P[0]) if n == 3 else None   # sim_targets: wave-3 target = L2 + 1.618*(H1-L0)
        tw5 = P[4] + (P[1] - P[0]) if n == 5 else None           # sim_targets: wave-5 target = L4 + (H1-L0)
        out.append(dict(label=label, n=n, deviations=int(sum(devs)), span=abs(max(P) - min(P)), pivots=known[-n:], w3=tw3, w5=tw5))
    return out

def select_count(counts):
    """Fixed rule: fewest Fibonacci-ratio deviations; tie -> the count covering the largest swings (price span)."""
    return sorted(counts, key=lambda c: (c["deviations"], -c["span"]))[0] if counts else None

def fib_time_date(x, anchor_idx, asset):
    last = len(x) - 1
    for f in FIB_NUMS:
        if anchor_idx + f > last:
            ahead = anchor_idx + f - last
            if asset == "crypto": return str((x.index[-1] + pd.Timedelta(days=ahead)).date())
            from pandas.tseries.holiday import USFederalHolidayCalendar
            from pandas.tseries.offsets import CustomBusinessDay
            return str((x.index[-1] + CustomBusinessDay(n=ahead, calendar=USFederalHolidayCalendar())).date())
    return None

def fib_elliott(x, asset, direction, entry=None):
    """EXPERIMENTAL columns. Pivots: 2xATR14 zigzag on bars <= scan cutoff; each pivot carries its confirmation date and only
    confirmed pivots exist (causal, verified 960/960 by the researcher). Leg = last confirmed swing end + its origin (sim_fib).
    fib_stop_struct = leg origin - 1.0*ATR14 (sim_struct variant c, checked on close; deeper pivot if entry already through it).
    fib_tp_* = origin + r*(end-origin). Elliott count chosen by select_count(). Never feeds the active stop."""
    direction = direction.upper(); sgn = 1 if direction == "LONG" else -1
    r = {c: None for c in EXP_COLS}; r["elliott_count_valid"] = False; r["elliott_wave_label"] = "no valid count"
    h, l, c = x.High.values, x.Low.values, x.Close.values
    a = atr14(h, l, c); A = a[-1] if len(a) else np.nan
    if not np.isfinite(A): r["elliott_wave_label"] = "no ATR (history too short)"; return r
    known = [p for p in zigzag(h, l, a, ZZ) if p[3] <= len(h) - 1]
    r["pivots_confirmed"] = json.dumps([[p[0], round(float(p[1]), 4), str(x.index[p[2]].date()), str(x.index[p[3]].date())] for p in known[-6:]])
    ref = float(entry) if entry is not None and pd.notna(entry) else float(c[-1])
    end_kind = "H" if sgn == 1 else "L"; org_kind = "L" if sgn == 1 else "H"
    idx = [j for j, p in enumerate(known) if p[0] == end_kind]
    if idx and idx[-1] > 0:
        e_, o = known[idx[-1]][1], known[idx[-1] - 1][1]; rng = e_ - o
        r.update(fib_leg_origin=round(o, 4), fib_leg_end=round(e_, 4))
        for f, nm in zip(RET, ("fib_r382", "fib_r500", "fib_r618", "fib_r786")): r[nm] = round(e_ - f * rng, 4)
        allext = [o + f * rng for f in EXT]
        for v, nm in zip(allext, ("fib_tp_1272", "fib_tp_1618", "fib_tp_2618")): r[nm] = round(v, 4) if v > 0 else None   # <=0 = impossible price
        lv = o - sgn * 1.0 * A; fb = 0                                              # sim_struct (c) + fallback
        if not sgn * (ref - lv) > 0:
            origins = [p[1] for p in known if p[0] == org_kind]
            deeper = sorted([p for p in origins if sgn * (ref - (p - sgn * A)) > 0], key=lambda p: -sgn * p)
            lv, fb = ((deeper[0] - sgn * A), 1) if deeper else (None, 1)
        r["fib_stop_struct"] = round(lv, 4) if lv is not None else None; r["fib_stop_fallback"] = bool(fb)
        anchor = known[idx[-1] - 1][2]; r["fib_time_anchor"] = "fib leg origin"
    else:
        anchor = None
    counts = elliott_counts(known, sgn); best = select_count(counts); r["elliott_n_valid_counts"] = len(counts)
    if best:
        r.update(elliott_count_valid=True, elliott_wave_label=best["label"], elliott_fib_deviations=best["deviations"],
                 elliott_target_w3=round(best["w3"], 4) if best["w3"] else None, elliott_target_w5=round(best["w5"], 4) if best["w5"] else None)
        anchor = best["pivots"][0][2]; r["fib_time_anchor"] = "elliott wave-1 origin"
    if anchor is not None: r["fib_time_target_date"] = fib_time_date(x, anchor, asset)
    return r

# ---------------------------------------------------------------- batch
def annotate(setups, asof=None, px_dir=None, frozen_out=None):
    """setups: DataFrame with ticker, asset ('stock'|'crypto'), direction (LONG|SHORT), optional entry, entry_date, mcap_b.
    Returns (active_df, frozen_df). Crypto shorts never appear in active_df. US stocks < $1.5B mcap are excluded (logged)."""
    asof = pd.Timestamp.now(tz="UTC") if asof is None else pd.Timestamp(asof)
    if asof.tzinfo is None: asof = asof.tz_localize("Asia/Jerusalem")
    asof = asof.tz_convert("UTC"); px_dir = px_dir or f"{SM.CACHE_ROOT}/{asof.strftime('%Y%m%dT%H%MZ')}"
    rows, frozen = [], []
    for _, s in setups.iterrows():
        asset = "crypto" if str(s["asset"]).lower() == "crypto" else "stock"; d = str(s["direction"]).upper()
        base = dict(s); base.update(asset=asset, direction=d, asof_utc=asof.strftime("%Y-%m-%d %H:%M"))
        x = daily_bars(s["ticker"], asset, asof, px_dir)
        if x is None or len(x) < 15:
            base.update(stop_type="no data / <15 bars"); (frozen if (asset == "crypto" and d == "SHORT") else rows).append(base); continue
        base["last_bar"] = str(x.index[-1].date()); base["history_bars"] = len(x)
        entry = s.get("entry") if "entry" in s else None
        st = active_stop(x, asset, d, entry); base.update(st); base.update(fib_elliott(x, asset, d, entry))
        if asset == "stock":                                                         # $1.5B floor (US stocks)
            mc = float(s["mcap_b"]) * 1e9 if ("mcap_b" in s and pd.notna(s.get("mcap_b"))) else SM.market_cap(SM.yahoo_symbol(s["ticker"], "stock"))
            base["mcap_b"] = round(mc / 1e9, 2) if mc else None
            if mc is None: base["excluded_reason"] = "MCAP ~ (לא אומת)"
            elif mc < SM.MCAP_FLOOR_USD: base["excluded_reason"] = "MCAP<1.5B"
        if "entry_date" in s and pd.notna(s.get("entry_date")) and entry is not None and pd.notna(entry):
            ss = stop_status(x, asset, d, s["entry_date"], float(entry), st.get("tp_half_1618")); base.update({f"live_{k}": v for k, v in ss.items()})
        (frozen if st["frozen_crypto_short"] else rows).append(base)
    A, F = pd.DataFrame(rows), pd.DataFrame(frozen)
    if frozen_out is not None and len(F):
        os.makedirs(os.path.dirname(frozen_out), exist_ok=True)
        F.to_csv(frozen_out, mode="a", header=not os.path.exists(frozen_out), index=False, encoding="utf-8-sig")
    return A, F

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--setups", required=True, help="CSV: ticker,asset,direction[,entry,entry_date,mcap_b]")
    ap.add_argument("--asof"); ap.add_argument("--out")
    ap.add_argument("--frozen-out", default=(_SCANNER_ROOT + "/scan-runs/frozen_crypto_shorts.csv"))
    a = ap.parse_args()
    A, F = annotate(pd.read_csv(a.setups), a.asof, frozen_out=a.frozen_out)
    if a.out: os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True); A.to_csv(a.out, index=False, encoding="utf-8-sig"); print("wrote", a.out)
    with pd.option_context("display.width", 300, "display.max_columns", 60, "display.max_colwidth", 60):
        print(A.drop(columns=["pivots_confirmed"], errors="ignore").T.to_string())
        if len(F): print(f"\nFROZEN crypto shorts (logged to {a.frozen_out}, not output as setups):\n", F[["ticker", "direction", "asof_utc"]].to_string(index=False))

if __name__ == "__main__":
    main()
