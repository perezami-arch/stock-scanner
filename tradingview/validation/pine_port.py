"""Bar-by-bar transliteration of elliott_fib_pit.pine (independent of scanner_stops.py code paths).
Each call to step() = one CONFIRMED bar. ATR = Pine ta.atr (RMA seeded with SMA of first L true ranges, TR[0]=H-L)."""
import math
NaN = float("nan")
W2_R = [0.382, 0.5, 0.618, 0.786]; W3_X = [1.0, 1.272, 1.618, 2.618]; W4_R = [0.236, 0.382, 0.5]; W5_X = [0.618, 1.0, 1.618]
NAMES = {3: "in_W3 (W2 done)", 4: "in_W4 (W3 done)", 5: "in_W5 (W4 done)", 6: "W5_done (correction next)"}
def isna(x): return x is None or (isinstance(x, float) and math.isnan(x))
def f_dev(r, allowed):
    best = None
    for f in allowed:
        d = abs(r - f) / f; best = d if best is None else min(best, d)
    return 0 if best <= 0.10 else 1

class PinePort:
    def __init__(self, sgn=1, atr_len=14, zz=2.0, trail_mult=4.0, entry_idx=None, entry_px=None, mode="chandelier", is_crypto=False):
        self.is_crypto = is_crypto
        self.sgn, self.L, self.zz, self.K = sgn, atr_len, zz, trail_mult
        self.bi = -1; self.prev_close = None; self.trs = []; self.atr = NaN; self.atr_prev = NaN
        self.zd = 0; self.zhi = self.zlo = None; self.zhiI = self.zloI = None
        self.pK, self.pP, self.pI, self.pC = [], [], [], []
        self.out = {}; self.prev_wave = "no ATR (history too short)"
        self.entry_idx, self.entry_px_in, self.mode = entry_idx, entry_px, mode
        self.k = None; self.ext = None; self.trail = NaN; self.stopped = False; self.events = []

    def f_count(self, n, s):
        sz = len(self.pP)
        if sz < n: return (False, 0, NaN, NaN, NaN)
        b = sz - n
        if self.pK[b] == s: return (False, 0, NaN, NaN, NaN)
        q = [s * self.pP[b + i] for i in range(n)]
        w1 = q[1] - q[0]
        if w1 <= 0 or q[2] <= q[0]: return (False, 0, NaN, NaN, NaN)
        devs = f_dev((q[1] - q[2]) / w1, W2_R); w3 = NaN
        if n >= 4:
            w3 = q[3] - q[2]
            if q[3] <= q[1]: return (False, 0, NaN, NaN, NaN)
            devs += f_dev(w3 / w1, W3_X)
        if n >= 5:
            if q[4] <= q[1]: return (False, 0, NaN, NaN, NaN)
            devs += f_dev((q[3] - q[4]) / w3, W4_R)
        if n >= 6:
            w5 = q[5] - q[4]
            if q[5] <= q[3]: return (False, 0, NaN, NaN, NaN)
            if w3 < w1 and w3 < w5: return (False, 0, NaN, NaN, NaN)
            devs += f_dev(w5 / w1, W5_X)
        P = self.pP[b:]
        span = abs(max(P) - min(P))
        tw3 = P[2] + 1.618 * (P[1] - P[0]) if n == 3 else NaN
        tw5 = P[4] + (P[1] - P[0]) if n == 5 else NaN
        return (True, devs, span, tw3, tw5)

    def step(self, o, h, l, c):
        self.bi += 1; bi = self.bi; s = self.sgn
        # ta.atr
        tr = h - l if self.prev_close is None else max(h - l, abs(h - self.prev_close), abs(l - self.prev_close))
        self.prev_close = c; self.atr_prev = self.atr
        if bi < self.L - 1: self.trs.append(tr); self.atr = NaN
        elif bi == self.L - 1: self.trs.append(tr); self.atr = sum(self.trs) / self.L
        else: self.atr = (1.0 / self.L) * tr + (1 - 1.0 / self.L) * self.atr   # Pine rma: alpha*src + (1-alpha)*prev
        A = self.atr
        newPiv = 0
        if bi == 14:
            self.zhi, self.zhiI, self.zlo, self.zloI = h, bi, l, bi
        elif bi > 14:
            th = self.zz * A
            if self.zd >= 0:
                if h > self.zhi: self.zhi, self.zhiI = h, bi
                if self.zd == 0 and l < self.zlo: self.zlo, self.zloI = l, bi
            if self.zd <= 0:
                if l < self.zlo: self.zlo, self.zloI = l, bi
                if self.zd == 0 and h > self.zhi: self.zhi, self.zhiI = h, bi
            if self.zd >= 0 and self.zhi - l >= th and self.zhiI < bi and (self.zd == 1 or self.zhiI > self.zloI):
                self.pK.append(1); self.pP.append(self.zhi); self.pI.append(self.zhiI); self.pC.append(bi)
                self.zd = -1; self.zlo, self.zloI = l, bi; newPiv = 1
            elif self.zd <= 0 and h - self.zlo >= th and self.zloI < bi and (self.zd == -1 or self.zloI > self.zhiI):
                self.pK.append(-1); self.pP.append(self.zlo); self.pI.append(self.zloI); self.pC.append(bi)
                self.zd = 1; self.zhi, self.zhiI = h, bi; newPiv = -1
        o_ = self.out; waveChanged = False
        if not isna(A):
            ref = c; sz = len(self.pP)
            je = -1
            for i in range(sz - 1, -1, -1):
                if self.pK[i] == s: je = i; break
            if je > 0:
                e_, org = self.pP[je], self.pP[je - 1]; rng = e_ - org
                o_.update(leg_o=org, leg_e=e_, r382=e_ - .382 * rng, r500=e_ - .5 * rng, r618=e_ - .618 * rng, r786=e_ - .786 * rng)
                for nm, f in (("x1272", 1.272), ("x1618", 1.618), ("x2618", 2.618)):
                    v = org + f * rng; o_[nm] = v if v > 0 else NaN
                lv = org - s * A; fb = False
                if not (s * (ref - lv) > 0):
                    fb = True; best = None
                    for i in range(sz):
                        if self.pK[i] == -s:
                            p = self.pP[i]
                            if s * (ref - (p - s * A)) > 0 and (best is None or -s * p < -s * best): best = p
                    lv = NaN if best is None else best - s * A
                o_.update(struct=lv, struct_fb=fb)
            else:
                for nm in ("leg_o", "leg_e", "r382", "r500", "r618", "r786", "x1272", "x1618", "x2618", "struct"): o_[nm] = NaN
                o_["struct_fb"] = False
            o_["tp_half"] = NaN
            if s == 1 and je > 0 and not self.is_crypto:
                H1, L0 = self.pP[je], self.pP[je - 1]; t2 = L0 + 1.618 * (H1 - L0); t3 = L0 + 2.618 * (H1 - L0)
                o_["tp_half"] = t2 if t2 - ref > 0 else (t3 if t3 - ref > 0 else NaN)
            bestN = None; cnt = 0
            for n in range(3, 7):
                ok, dv, sp, t3w, t5w = self.f_count(n, s)
                if ok:
                    cnt += 1
                    if bestN is None or dv < bestDev or (dv == bestDev and sp > bestSpan):
                        bestN, bestDev, bestSpan, bT3, bT5 = n, dv, sp, t3w, t5w
            o_.update(n_valid=cnt, wave="no valid count" if bestN is None else NAMES[bestN],
                      wave_dev=None if bestN is None else bestDev, ew3=NaN if bestN is None else bT3, ew5=NaN if bestN is None else bT5)
            waveChanged = o_["wave"] != self.prev_wave; self.prev_wave = o_["wave"]
        # reference stop
        stopEvent = False
        if self.entry_idx is not None:
            if self.k is None:
                if bi >= self.entry_idx:
                    self.k = bi; self.entry_px = self.entry_px_in if self.entry_px_in else o
                    self.ext = c; self.trail = self.entry_px - s * self.K * self.atr_prev
            elif not self.stopped:
                if bi == self.k + 1:
                    self.ext = max(self.ext, c) if s == 1 else min(self.ext, c)
                    if self.mode == "chandelier": self.trail = self.ext - s * self.K * A
                else:
                    if s * (c - self.trail) <= 0: self.stopped = True; stopEvent = True
                    else:
                        self.ext = max(self.ext, c) if s == 1 else min(self.ext, c)
                        if self.mode == "chandelier": self.trail = self.ext - s * self.K * A
        elif not isna(A):
            self.trail = c - s * self.K * A
        o_["trail"] = self.trail; o_["stopped"] = self.stopped
        if newPiv != 0 or waveChanged:
            self.events.append((bi, newPiv, waveChanged, o_.get("wave")))
        return newPiv, waveChanged, stopEvent

def fmt(x):   # Pine str.tostring(x, "0.##########")
    if isna(x): return "null"
    t = f"{x:.10f}".rstrip("0").rstrip("."); return t if t not in ("-0", "") else "0"
def json_msg(o, ticker, exchange, tf, sig, close, bar_ms, secret):
    import json as _j
    q = lambda v: _j.dumps(v)
    return ("{" + f'"ticker":{q(ticker)},"exchange":{q(exchange)},"timeframe":{q(tf)},"signal":{q(sig)},"close":{fmt(close)},'
            f'"bar_time":{bar_ms},"wave_label":{q(o["wave"])},"fib_0382":{fmt(o["r382"])},"fib_05":{fmt(o["r500"])},'
            f'"fib_0618":{fmt(o["r618"])},"fib_0786":{fmt(o["r786"])},"fib_1272":{fmt(o["x1272"])},"fib_1618":{fmt(o["x1618"])},'
            f'"fib_2618":{fmt(o["x2618"])},"struct_stop":{fmt(o["struct"])},"elliott_target_w3":{fmt(o["ew3"])},'
            f'"elliott_target_w5":{fmt(o["ew5"])},"secret":{q(secret)}' + "}")
