"""Summarize TradingAgents results: decision vs realized outcome (direction-adjusted), market-adjusted, robustness.
Usage: python summarize.py [results.jsonl | results_finr1deep.jsonl]"""
import json, os, sys, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
f = os.path.join(HERE, "results", sys.argv[1] if len(sys.argv) > 1 else "results.jsonl")
S = pd.read_csv(os.path.join(HERE, "setups_846.csv"))[["setup_id", "xtot", "xeth_tot", "x5", "x20", "priority"]]
d = pd.DataFrame([json.loads(l) for l in open(f, encoding="utf-8")])
d = d[d.ok == True].drop_duplicates("setup_id", keep="last").merge(S, on="setup_id", how="left")
def verdict(r):
    dec = str(r.decision).strip().lower(); bull = dec in ("buy", "overweight"); bear = dec in ("sell", "underweight")
    if not (bull or bear): return "neutral"
    return "agree" if (bull if r.direction == "LONG" else bear) else "disagree"
d["verdict"] = d.apply(verdict, axis=1)
d["ret"] = pd.to_numeric(d.tracker_total_return, errors="coerce") * 100; d["excess"] = d.xtot * 100; d["excess_eth"] = d.xeth_tot * 100
d["win"] = d.ret > 0; d["src"] = d.platform.str.replace(r" \(.*\)", "", regex=True)
def agg(g): return pd.Series(dict(n=len(g), mean_ret=g.ret.mean(), median_ret=g.ret.median(), mean_excess=g.excess.mean(), median_excess=g.excess.median(), win_rate=g.win.mean()))
pd.set_option("display.width", 200)
print(f"{f}: {len(d)} ok setups\n\nBy verdict:"); print(d.groupby("verdict").apply(agg).round(2))
print("\nBy source x verdict:"); print(d.groupby(["src", "verdict"]).apply(agg).round(2))
print("\nBy asset x verdict:"); print(d.groupby(["asset", "verdict"]).apply(agg).round(2))
cr = d[d.asset == "crypto"]
if len(cr): print(f"\nCrypto excess vs ETH: mean {cr.excess_eth.mean():.2f}% median {cr.excess_eth.median():.2f}%")
top = ~d.ticker.str.upper().str.replace("-USD", "").isin(["NEAR", "XP", "IOVA"])
print("\nWithout NEAR / XP / IOVA:"); print(d[top].groupby("verdict").apply(agg).round(2))
dec = d[d.verdict != "neutral"]
if len(dec): print(f"\nHit rate (agree&win or disagree&loss): {((dec.verdict=='agree')==dec.win).mean():.1%} on n={len(dec)}; base win rate {d.win.mean():.1%}")
other = os.path.join(HERE, "results", "results_finr1deep.jsonl")
if f.endswith("results.jsonl") and os.path.exists(other):
    o = pd.DataFrame([json.loads(l) for l in open(other, encoding="utf-8")]); o = o[o.ok == True].drop_duplicates("setup_id", keep="last")
    m = d.merge(o[["setup_id", "decision"]], on="setup_id", suffixes=("_qwen", "_finr1"))
    print(f"\nQwen vs Fin-R1-deep on {len(m)} identical setups: same decision {(m.decision_qwen.str.lower()==m.decision_finr1.str.lower()).mean():.0%}")
d.to_csv(f.replace(".jsonl", "_flat.csv"), index=False)
print("\nruntime avg s:", round(d.wall_s.mean()), " n=", len(d))
