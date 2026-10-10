"""ELLIOTT / FIB v2 - EXPERIMENTAL (08.10.2026). Runs ALONGSIDE v1 (scanner_stops.fib_elliott), never changes v1 outputs,
score, stops or targets. Columns prefixed ev2_ (weight 0). Import-safe. Main entry: elliott_v2_columns(df, cutoff, asset, direction).

Same building blocks as v1: 2xATR14 zigzag (iaf/sim_fib.py exec'd unchanged, via scanner_geometry), v1 hard rules and target
formulas (scanner_stops.elliott_counts / select_count). What v2 adds:
 1. TENTATIVE PIVOT (lag fix). The extreme since the last confirmed pivot (lowest low after a confirmed high, highest high after a
    confirmed low), using bars <= the last visible bar only. Used only if it is >= TENT_MIN_ATR x ATR14 away from the last confirmed
    pivot. Always flagged provisional: it is NOT a zigzag pivot and is never promoted with later data (the backtest recomputes from
    the cut frame at every cutoff). A count that ends on it says 'Wn in progress' instead of 'Wn done'.
    'beyond target' flags: W3 in progress past P2 + 1.618*(P1-P0) (v1's W3 target); W5 in progress past P4 + (P1-P0) (v1's W5 target).
 2. A-B-C CORRECTIONS (basics). Base = a v1-valid impulse ending at an earlier point (W1 done -> W2 as ABC, W3 done -> W4 as ABC,
    W5 done -> post-impulse ABC). The 2 or 3 points after the base are A, B[, C] (alternating, A against the impulse).
      B/A = |B|/|A| must be 0.236..1.382 (B may exceed the start of A only in an expanded flat).
      zigzag: B/A < 0.9 and C ends beyond the end of A, C/A >= 0.618.  flat: B/A >= 0.9; regular if C/A <= 1.15, expanded above.
      Context rules: W2-ABC never beyond the W1 origin; W4-ABC never into W1 territory (beyond the W1 end).
    Only A-B (no C yet) -> 'C in progress' (type from B/A). A C that ends on the tentative point -> provisional.
    C targets: zigzag C = A (1.0) and 1.618 A from the end of B; flat C = end of A.
 3. BOTH VIEWS: every count is run in the LONG (bullish impulse) and SHORT (bearish impulse) view: ev2_long_*, ev2_short_*.
    ev2_* (no view) = the requested direction's view.
    Primary per view: counts ending at the LATEST point win (tentative if present, else last confirmed pivot); then impulse over
    ABC; then fewest Fib-ratio deviations; then largest span (v1 tie rule).
 4. STALE FIB ANCHOR. v1 leg = last confirmed swing end + the pivot before it. If price later traded beyond the leg ORIGIN (1.0)
    the leg is stale -> re-anchor to the most recent confirmed leg (origin -> end, view direction) whose origin was never
    breached after its end, up to the last visible bar. Old and new anchors are both recorded; no valid leg -> ev2_fib_* blank.
POINT-IN-TIME: everything from pit_cut(df, cutoff) only; confirmed pivot = confirm_idx <= last visible bar.
"""
import json, math, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

TENT_MIN_ATR = 1.0
RET = [0.382, 0.5, 0.618, 0.786]; EXT = [1.272, 1.618]
_mods = {}
def _m():
    if not _mods:
        import sys; sys.path.insert(0, "/workspace")
        import scanner_geometry as GEO, scanner_stops as ST
        _mods.update(GEO=GEO, ST=ST)
    return _mods

def _r(v, n=4):
    try:
        v = float(v); return round(v, n) if np.isfinite(v) else None
    except Exception: return None

def tentative_pivot(x, known, A):
    """(kind, price, idx, None, 'tentative', move_atr, back_atr) or None. Bars <= last visible bar only."""
    if not known: return None
    lp = known[-1]; j = len(x) - 1
    if j <= lp[2]: return None
    seg = x.iloc[lp[2] + 1:]
    if lp[0] == "H": k = int(np.argmin(seg.Low.values)); p = float(seg.Low.values[k]); kind = "L"
    else: k = int(np.argmax(seg.High.values)); p = float(seg.High.values[k]); kind = "H"
    idx = lp[2] + 1 + k; move = abs(p - lp[1]) / A
    if move < TENT_MIN_ATR: return None
    c = float(x.Close.iloc[-1]); back = abs(c - p) / A
    return (kind, p, idx, None, "tentative", move, back)

def _impulse_cands(seq, sgn, tent_used):
    ST = _m()["ST"]; out = []
    for c in ST.elliott_counts(seq, sgn):
        prov = tent_used
        lab = {3: "W2", 4: "W3", 5: "W4", 6: "W5"}[c["n"]]
        if prov: label = f"{lab} in progress (provisional)"
        else: label = {3: "W2 done (W3 may start)", 4: "W3 done (in W4)", 5: "W4 done (in W5)", 6: "W5 done (correction next)"}[c["n"]]
        out.append(dict(kind="impulse", n=c["n"], label=label, v1_label=c["label"], provisional=prov, deviations=c["deviations"],
                        span=c["span"], pivots=c["pivots"], w3=c["w3"], w5=c["w5"]))
    return out

def _abc_cands(seq, sgn, tent_used):
    """A-B-C after a base impulse ending at seq[k], k = len-3 (A,B) or len-4 (A,B,C)."""
    ST = _m()["ST"]; out = []
    for m in (2, 3):
        k = len(seq) - 1 - m
        if k < 1: continue
        base_seq = seq[:k + 1]; legs = seq[k:]               # legs[0] = base end, then A end, B end[, C end]
        bases = [c for c in ST.elliott_counts(base_seq, sgn) if c["n"] in (4, 6)]
        p0, p1 = base_seq[k - 1], base_seq[k]                # W1 base (n=2): a with-leg ending at seq[k]
        if sgn * (p1[1] - p0[1]) > 0: bases.append(dict(n=2, pivots=[p0, p1], deviations=0, span=abs(p1[1] - p0[1])))
        for b in bases:
            ctx = {2: "W2", 4: "W4", 6: "post-W5"}[b["n"]]
            S, Ae, Be = legs[0][1], legs[1][1], legs[2][1]
            A_ = Ae - S; B_ = Be - Ae
            if not (sgn * A_ < 0 and sgn * B_ > 0): continue
            rb = abs(B_) / abs(A_)
            if not (0.236 <= rb <= 1.382): continue
            P = b["pivots"]
            pts = [Ae] + ([legs[3][1]] if m == 3 else [])
            if ctx == "W2" and any(sgn * (p - P[0][1]) <= 0 for p in pts): continue            # W2 never beyond W1 origin
            if ctx == "W4" and any(sgn * (p - P[1][1]) <= 0 for p in pts): continue            # W4 never into W1 territory
            if m == 3:
                Ce = legs[3][1]; C_ = Ce - Be; rc = abs(C_) / abs(A_)
                if sgn * C_ >= 0: continue
                if rb < 0.9:
                    if not (sgn * (Ce - Ae) < 0 and rc >= 0.618): continue
                    typ = "zigzag"
                else: typ = "regular flat" if rc <= 1.15 else "expanded flat"
                prov = tent_used
                label = f"{ctx} correction {typ}: C {'in progress (provisional)' if prov else 'done'}"
                if not prov: label += {"W2": " -> W3 may start", "W4": " -> W5 may start", "post-W5": " -> new impulse may start"}[ctx]
                tC = None
            else:
                typ = "zigzag" if rb < 0.9 else "flat"; prov = tent_used
                label = f"{ctx} correction {typ}: B {'in progress (provisional)' if prov else 'done, C in progress'}"
                tC = [Be + A_, Be + 1.618 * A_] if typ == "zigzag" else [Ae]
            out.append(dict(kind="abc", n=b["n"], ctx=ctx, abc_type=typ, label=label, provisional=prov, deviations=b["deviations"],
                            span=b["span"], pivots=P + list(legs[1:]), base_pivots=P, abc_pivots=list(legs[1:]), b_over_a=rb,
                            c_targets=tC, w3=None, w5=None))
    return out

def view_counts(x, known, tent, sgn, A):
    seq_c = list(known); seq_t = list(known) + ([tent] if tent else [])
    cands = []
    for seq, tu in ((seq_t, True), (seq_c, False)) if tent else ((seq_c, False),):
        latest = len(seq) - 1
        for c in _impulse_cands(seq, sgn, tu) + _abc_cands(seq, sgn, tu):
            c["ends_latest"] = tu or not tent                       # counts on the tentative point are the most recent
            cands.append(c)
    cands.sort(key=lambda c: (not c["ends_latest"], c["kind"] != "impulse", c["deviations"], -c["span"]))
    best = cands[0] if cands else None
    r = {"n_candidates": len(cands)}
    if best:
        close = float(x.Close.iloc[-1]); bt = None
        if best["kind"] == "impulse" and best["provisional"]:
            P = [p[1] for p in best["pivots"]]
            if best["n"] == 4:
                t = P[2] + 1.618 * (P[1] - P[0]); bt = sgn * (close - t) > 0; r["target"] = t; r["target_name"] = "W3 1.618"
            elif best["n"] == 6:
                t = P[4] + (P[1] - P[0]); bt = sgn * (close - t) > 0; r["target"] = t; r["target_name"] = "W5 = W1"
        elif best["kind"] == "impulse":
            t = best["w3"] or best["w5"]
            if t: r["target"] = t; r["target_name"] = "W3 1.618" if best["w3"] else "W5 = W1"
        elif best.get("c_targets"):
            r["target"] = best["c_targets"][0]; r["target_name"] = "C = A" if best["abc_type"] == "zigzag" else "C = end of A"
            bt = sgn * (close - best["c_targets"][0]) < 0 if best["abc_type"] == "zigzag" else None
        label = best["label"] + (" / beyond target" if bt else "")
        r.update(label=label, kind=best["kind"], provisional=bool(best["provisional"]), beyond_target=bt, deviations=best["deviations"],
                 abc_type=best.get("abc_type"), context=best.get("ctx"), best=best,
                 pivots=[[p[0], round(float(p[1]), 4), str(x.index[p[2]].date()), str(x.index[p[3]].date()) if p[3] is not None else "tentative"]
                         for p in best["pivots"]])
    return r

def fib_anchor(x, known, sgn, A):
    """v1 leg + stale check + re-anchor (see module doc)."""
    end_k = "H" if sgn == 1 else "L"; idx = [j for j, p in enumerate(known) if p[0] == end_k and j > 0]
    r = {}
    if not idx: return r
    def breached(j):
        o, e = known[j - 1], known[j]; after = x.iloc[e[2] + 1:]
        if not len(after): return False
        return bool((after.Low.min() < o[1]) if sgn == 1 else (after.High.max() > o[1]))
    j1 = idx[-1]; r["v1_origin"] = known[j1 - 1][1]; r["v1_end"] = known[j1][1]; r["v1_origin_date"] = str(x.index[known[j1 - 1][2]].date())
    r["v1_end_date"] = str(x.index[known[j1][2]].date()); r["stale"] = breached(j1)
    use = None
    for j in reversed(idx):
        if not breached(j): use = j; break
    if use is not None:
        o, e = known[use - 1], known[use]
        r.update(origin=o[1], end=e[1], origin_i=o[2], end_i=e[2], origin_date=str(x.index[o[2]].date()), end_date=str(x.index[e[2]].date()),
                 end_confirmed_at=str(x.index[e[3]].date()), reanchored=(use != j1))
        rng = e[1] - o[1]
        for f in RET: r[f"r{int(round(f * 1000)):03d}"] = e[1] - f * rng
        for f in EXT:
            v = o[1] + f * rng; r[f"x{int(round(f * 1000))}"] = v if v > 0 else None
    return r

def elliott_v2_analysis(df, cutoff=None, asset="stock", direction="LONG"):
    GEO = _m()["GEO"]; x = GEO.pit_cut(df, cutoff, asset)
    out = {"ev2_last_bar": str(x.index[-1].date()) if len(x) else None, "ev2_direction_view": direction.upper()}
    if len(x) < 30: out["ev2_flag"] = "history too short"; return dict(x=x, cols=out)
    h, l, c = x.High.values, x.Low.values, x.Close.values
    a = GEO.atr14(h, l, c); A = float(a[-1])
    if not np.isfinite(A): out["ev2_flag"] = "no ATR"; return dict(x=x, cols=out)
    known = [p for p in GEO.zigzag(h, l, a, GEO.ZZ) if p[3] <= len(h) - 1]
    tent = tentative_pivot(x, known, A)
    out.update(ev2_tentative_kind=tent[0] if tent else None, ev2_tentative_price=_r(tent[1]) if tent else None,
               ev2_tentative_date=str(x.index[tent[2]].date()) if tent else None, ev2_tentative_move_atr=_r(tent[5], 2) if tent else None,
               ev2_tentative_back_atr=_r(tent[6], 2) if tent else None,
               ev2_last_confirmed=json.dumps([known[-1][0], _r(known[-1][1]), str(x.index[known[-1][2]].date()), str(x.index[known[-1][3]].date())]) if known else None)
    views = {}
    for vn, sg in (("long", 1), ("short", -1)):
        v = view_counts(x, known, tent, sg, A); views[vn] = v
        out[f"ev2_{vn}_label"] = v.get("label", "no valid count"); out[f"ev2_{vn}_kind"] = v.get("kind")
        out[f"ev2_{vn}_provisional"] = v.get("provisional"); out[f"ev2_{vn}_beyond_target"] = v.get("beyond_target")
        out[f"ev2_{vn}_abc_type"] = v.get("abc_type"); out[f"ev2_{vn}_context"] = v.get("context")
        out[f"ev2_{vn}_target"] = _r(v.get("target")); out[f"ev2_{vn}_target_name"] = v.get("target_name")
        out[f"ev2_{vn}_n_candidates"] = v.get("n_candidates", 0); out[f"ev2_{vn}_pivots"] = json.dumps(v["pivots"]) if v.get("pivots") else None
        st = ("none" if not v.get("kind") else f"{v['kind']}_{'provisional' if v.get('provisional') else 'confirmed'}")
        out[f"ev2_{vn}_state"] = st
        fa = fib_anchor(x, known, sg, A); views[vn]["fib"] = fa
        out[f"ev2_{vn}_fib_stale_v1"] = fa.get("stale"); out[f"ev2_{vn}_fib_reanchored"] = fa.get("reanchored")
        out[f"ev2_{vn}_fib_v1_origin"] = _r(fa.get("v1_origin")); out[f"ev2_{vn}_fib_v1_end"] = _r(fa.get("v1_end"))
        out[f"ev2_{vn}_fib_origin"] = _r(fa.get("origin")); out[f"ev2_{vn}_fib_end"] = _r(fa.get("end"))
        out[f"ev2_{vn}_fib_origin_date"] = fa.get("origin_date"); out[f"ev2_{vn}_fib_end_date"] = fa.get("end_date")
        for k in ("r382", "r500", "r618", "r786", "x1272", "x1618"): out[f"ev2_{vn}_fib_{k}"] = _r(fa.get(k))
    d = "long" if direction.upper() == "LONG" else "short"
    for k in list(out):
        if k.startswith(f"ev2_{d}_"): out["ev2_" + k[len(f"ev2_{d}_"):]] = out[k]
    return dict(x=x, known=known, tent=tent, views=views, cols=out, A=A)

def elliott_v2_columns(df, cutoff=None, asset="stock", direction="LONG"):
    """One dict of EXPERIMENTAL v2 columns (weight 0) for one ticker at one cutoff."""
    try: return elliott_v2_analysis(df, cutoff, asset, direction)["cols"]
    except Exception as e: return {"ev2_flag": f"error {e.__class__.__name__}: {e}"}

TRACKER_KEYS = ["ev2_label", "ev2_state", "ev2_kind", "ev2_provisional", "ev2_beyond_target", "ev2_abc_type", "ev2_context",
                "ev2_target", "ev2_target_name", "ev2_long_label", "ev2_short_label", "ev2_long_state", "ev2_short_state",
                "ev2_fib_stale_v1", "ev2_fib_reanchored", "ev2_fib_origin", "ev2_fib_end", "ev2_fib_r618", "ev2_fib_x1618",
                "ev2_tentative_kind", "ev2_tentative_price", "ev2_tentative_date", "ev2_tentative_move_atr", "ev2_last_bar"]
