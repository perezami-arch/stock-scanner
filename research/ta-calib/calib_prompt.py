"""Prompt building for the CALIBRATED TradingAgents variant (shared by run_calibrated.py and the box-side checks).
Pure standard library (csv/json), so it runs in the laptop venv and on the box. Nothing here calls an LLM.

Point-in-time: every number shown comes from setups_calib.csv, which holds values computed on bars <= the cutoff bar
(trade_date): stock pre/intra-session alert -> previous close; after-close alert -> alert-day candle; crypto -> last
complete UTC day before the alert minute. Lessons come from lessons_pool.csv (calibration half only) and are shown
only when their outcome was known strictly before the setup's cutoff bar."""
import csv, json, math, re

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["approve", "veto", "neutral"]},
        "p_success": {"type": "number", "minimum": 0, "maximum": 1},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "p_success", "reason"],
}

SCANNER_RULES = """Scanner rules (what our scanner checks; all computed on the cutoff bar):
- ck_score (0-5 checklist, in the trade's direction): 20-day and 5-day momentum agree; last candle confirms; 5/20-day volume ratio > 1 with momentum; close on the right side of SMA20; CCI(20) between -100 and 100 and turning the trade's way.
- Stock LONG rule: the sector ETF is in an uptrend (close > SMA50 and SMA50 higher than 10 days earlier); 'prebreakout' alerts fail the rule.
- Stock SHORT rule: ck_score >= 3 AND close below SMA200. Watch flag (weight 0, under test): close below the 120-day volume-profile value area (VA120).
- Crypto LONG: allowed (not 'prebreakout'). Crypto SHORTS are frozen in the live policy (not traded)."""

def _f(x):
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None

def _fmt(v, nd=2, pct=False):
    v = _f(v)
    if v is None: return "n/a"
    return f"{v*100:+.1f}%" if pct else f"{v:.{nd}f}"

def load_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def yn(v):
    v = _f(v)
    return "n/a" if v is None else ("yes" if v >= 0.5 else "no")

def setup_block(s):
    """The full setup as it would be traded under the active policy (prices as of the cutoff bar)."""
    d = s["direction"]; asset = s["asset"]; k = _f(s.get("policy_k")) or (3.0 if asset == "crypto" else 4.0)
    lines = [f"SETUP UNDER REVIEW: {d} {s['ticker']} ({asset}), alert {s['alert_date']}"
             f"{(' ' + s['alert_time_utc']) if s.get('alert_time_utc') else ''}, source {s.get('source','')}/{s.get('automation','')}.",
             f"Information cutoff: close of {s['trade_date']} (nothing after this bar may be used).",
             f"Reference entry: {_fmt(s.get('entry_ref'))} (cutoff close; the real fill is the next open). Alert's own entry {_fmt(s.get('entry_alert'))}, alert stop {_fmt(s.get('alert_stop'))}, alert target {_fmt(s.get('alert_tp1'))}.",
             f"ATR14 at cutoff: {_fmt(s.get('atr14'))} ({_fmt(s.get('atr14_pct'),1)}% of price).",
             f"Exit policy: {s.get('policy','')}. Initial stop ~{_fmt(s.get('policy_stop_ref'))} = {k:g} x ATR14 = {_fmt(s.get('policy_stop_pct'),1)}% from the reference entry."]
    if _f(s.get("fib1618_target")) is not None:
        lines.append(f"Half-position target (fib 1.618 extension of the last confirmed swing): {_fmt(s.get('fib1618_target'))} = {_fmt(s.get('target_dist_atr'),1)} ATR away.")
    lines.append(("Horizon: 20 daily bars" if asset == "crypto" else "Horizon: 20 trading days") +
                 " (if the stop does not end the trade first, it is closed at the close of day 20, counting the entry day). "
                 "Costs are small (stocks ~0.07%/side, crypto ~0.2%/side).")
    return "\n".join(lines)

def context_block(s):
    d = s["direction"]
    va = s.get("vp120_va_pos") or "n/a"
    lines = ["SCANNER CONTEXT (as of the cutoff bar):",
             f"- ck_score: {_fmt(s.get('ck_score'),0)}/5 (in the {d} direction)",
             f"- below SMA200: {yn(s.get('below_sma200'))}; distance to SMA200: {_fmt(s.get('vs_sma200'), pct=True)}"]
    if s["asset"] == "stock":
        lines.append(f"- sector: {s.get('sector') or 'n/a'} (ETF {s.get('sector_etf') or 'n/a'}), sector ETF uptrend: {yn(s.get('sector_up'))}")
    lines.append(f"- position vs 120-day volume-profile value area: {va}" + (f"; VA120 short watch flag: {yn(s.get('va120_short_flag'))}" if d == "SHORT" else ""))
    lines.append(f"- alert stop distance: {_fmt(s.get('alert_stop_dist_atr'),1)} ATR (policy stop is {_fmt(s.get('policy_k'),0)} ATR); alert entry vs cutoff close: {_fmt(s.get('alert_entry_vs_ref_atr'),1)} ATR")
    rp = _f(s.get("rule_pass"))
    lines.append(f"- passes the scanner rule for this segment: {'n/a' if rp is None else ('YES' if rp >= 0.5 else 'NO')}")
    return "\n".join(lines)

def instrument_addendum(s):
    """Appended to TradingAgents' instrument context, so every agent analyses OUR setup, not a generic buy/sell."""
    return ("\n\n" + setup_block(s) + "\n" + context_block(s) +
            "\nYour job is to judge whether THIS setup (direction, stop, target, 20-day horizon) is worth taking, using only data up to the cutoff.")

def select_lessons(s, pool, n=6):
    """Deterministic few-shot selection: outcome known strictly before the setup's cutoff bar, calibration half only
    (pool already restricted), never the setup itself. Same asset+direction first, then same asset, then any;
    most recent first; balanced winners / losers."""
    cut = s["trade_date"]
    av = [p for p in pool if p["setup_id"] != s["setup_id"] and p.get("known_date") and p["known_date"] < cut]
    av.sort(key=lambda p: (p["known_date"], p["setup_id"]), reverse=True)
    tiers = [[p for p in av if p["asset"] == s["asset"] and p["direction"] == s["direction"]],
             [p for p in av if p["asset"] == s["asset"] and p["direction"] != s["direction"]],
             [p for p in av if p["asset"] != s["asset"]]]
    out = []; half = n // 2
    for want_win in (True, False):
        got = 0
        for t in tiers:
            for p in t:
                if got >= half: break
                if p in out: continue
                if ((_f(p["ret20"]) or 0) > 0) == want_win: out.append(p); got += 1
    if len(out) < n:                                   # fill if one side was short
        for t in tiers:
            for p in t:
                if len(out) >= n: break
                if p not in out: out.append(p)
    out.sort(key=lambda p: p["known_date"])
    return out

def lessons_block(lessons):
    if not lessons:
        return "CLOSED-TRADE LESSONS: none known before this cutoff."
    L = ["CLOSED-TRADE LESSONS (earlier scanner setups whose result was already known before this cutoff; same exit policy):"]
    for p in lessons:
        st = {"stopped": "stopped out", "horizon20": "closed at day 20"}.get(p.get("status20"), p.get("status20"))
        tgt = " (half taken at 1.618)" if str(p.get("target_hit20")) == "True" else ""
        L.append(f"- {p['direction']} {p['ticker']} ({p['asset']}), cutoff {p['trade_date']}: ck_score {_fmt(p.get('ck_score'),0)}, "
                 f"below SMA200 {yn(p.get('below_sma200'))}, sector uptrend {yn(p.get('sector_up')) if p['asset']=='stock' else 'n/a'}, "
                 f"VA120 {p.get('vp120_va_pos') or 'n/a'}, rule pass {yn(p.get('rule_pass'))} -> {st}{tgt} after {p.get('days20')} days, "
                 f"net {_fmt(p.get('ret20'), pct=True)}, vs {'SPY' if p['asset']=='stock' else 'BTC'} {_fmt(p.get('x_mkt20'), pct=True)}")
    L.append("Use these as calibration of how often setups like this work, not as rules.")
    return "\n".join(L)

def _cut(x, n):
    x = str(x or "").strip()
    return x if len(x) <= n else x[:n] + " ..."

def judge_messages(s, lessons, ta):
    """ta: dict with final_rating, final_trade_decision, investment_plan, trader_plan, bull, bear."""
    system = ("You are the final risk gate of a swing-trading scanner. The direction, stop, target and horizon are fixed by the "
              "scanner; you decide only whether to TAKE this exact trade. Use only information up to the stated cutoff. "
              "Answer with JSON only: {\"verdict\": \"approve\"|\"veto\"|\"neutral\", \"p_success\": number 0-1, \"reason\": short text}. "
              "p_success = probability that the trade ends with a positive net return under this exit policy within the 20-day horizon. "
              "approve = take it; veto = skip it (expected loss or poor reward/risk); neutral = no edge either way. "
              "Be calibrated: many scanner setups lose money, so do not default to approve; veto when the evidence against the trade is stronger.")
    user = "\n\n".join([
        setup_block(s), context_block(s), SCANNER_RULES, lessons_block(lessons),
        "ANALYST TEAM OUTPUT (TradingAgents, same cutoff):\n"
        f"- Portfolio manager rating (generic 5-tier, about the stock, not the setup): {ta.get('final_rating') or 'n/a'}\n"
        f"- Portfolio manager decision: {_cut(ta.get('final_trade_decision'), 1800)}\n"
        f"- Research manager plan: {_cut(ta.get('investment_plan'), 1200)}\n"
        f"- Trader plan: {_cut(ta.get('trader_plan'), 800)}\n"
        f"- Bull case (end): {_cut(ta.get('bull'), 700)}\n"
        f"- Bear case (end): {_cut(ta.get('bear'), 700)}",
        f"Decide for the {s['direction']} setup above. Return the JSON object only."])
    return system, user

def parse_judge(text):
    """Tolerant JSON parse. Returns dict(verdict, p_success, reason, parse_ok)."""
    t = (text or "").strip()
    m = re.search(r"\{.*\}", t, re.S)
    obj = None
    if m:
        try: obj = json.loads(m.group(0))
        except Exception: obj = None
    if obj is None:
        v = re.search(r"\b(approve|veto|neutral)\b", t, re.I); p = re.search(r"p_success\"?\s*[:=]\s*([0-9.]+)", t)
        obj = {"verdict": v.group(1).lower() if v else None, "p_success": float(p.group(1)) if p else None, "reason": t[:300]}
        ok = False
    else:
        ok = True
    v = str(obj.get("verdict", "")).strip().lower()
    if v not in ("approve", "veto", "neutral"): v = None; ok = False
    p = _f(obj.get("p_success"))
    if p is not None and p > 1 and p <= 100: p = p / 100.0
    if p is None or not (0 <= p <= 1): p = None; ok = False
    return dict(verdict=v, p_success=p, reason=str(obj.get("reason", ""))[:600], parse_ok=ok)
