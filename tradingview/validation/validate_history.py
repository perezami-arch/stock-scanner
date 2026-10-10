"""D. Sensitivity to history start / ATR seeding / price adjustment (what differs on TradingView).
Runs the Pine port on (1) full Yahoo history, adjusted (TV with 'adjust for dividends' on ~ Yahoo adjusted),
(2) full history unadjusted for dividends (TV default for stocks), (3) the scanner's 479/700-bar window but starting 100 / 250 bars later."""
import sys, json, numpy as np, pandas as pd, warnings, os; warnings.filterwarnings("ignore")
sys.path.insert(0, "/workspace/tradingview/validation")
from validate import load, run, cmp_final, OUT, TICK, MAP
import yfinance as yf
D = "/workspace/tradingview/validation/yahoo_max"; os.makedirs(D, exist_ok=True)
def ymax(sym, adj):
    f = f"{D}/{sym}_{'adj' if adj else 'raw'}.csv"
    if not os.path.exists(f):
        x = yf.download(sym, period="max", interval="1d", auto_adjust=adj, progress=False)
        if isinstance(x.columns, pd.MultiIndex): x.columns = x.columns.get_level_values(0)
        x.to_csv(f)
    x = pd.read_csv(f, index_col=0, parse_dates=True)
    x = x[x.index <= "2026-10-07"]
    return x[["Open", "High", "Low", "Close"]].dropna(subset=["Close"])
KEY = ["fib_leg_origin", "fib_leg_end", "fib_stop_struct", "tp_half_1618", "elliott_wave_label", "elliott_target_w3"]
rows = []
for t, asset, path in TICK:
    sym = t + "-USD" if asset == "crypto" else t
    base = load(path, asset)
    variants = {"scanner window (479/700 bars)": base,
                "window minus first 100 bars": base.iloc[100:], "window minus first 250 bars": base.iloc[250:],
                "Yahoo full history, adjusted": ymax(sym, True)}
    if asset == "stock": variants["Yahoo full history, NOT dividend-adjusted (TV default)"] = ymax(sym, False)
    for nm, x in variants.items():
        p, snaps = run(x); o = snaps[-1]; d = cmp_final(o, OUT.loc[t])
        a_csv = OUT.loc[t, "atr14_wilder"]
        # ATR of last bar from port
        rows.append(dict(ticker=t, variant=nm, bars=len(x), first_bar=str(x.index[0].date()), atr_last=round(p.atr, 4), atr_csv=a_csv,
                         mismatched_fields=len(d), wave=o["wave"], leg=f"{o['leg_o']:.4f}->{o['leg_e']:.4f}",
                         struct=round(o["struct"], 4), tp_half=round(o["tp_half"], 4) if o["tp_half"] == o["tp_half"] else None,
                         detail="; ".join(f"{c}: csv={v} port={pv if not isinstance(pv, float) else round(pv, 4)}" for c, v, pv in d)))
R = pd.DataFrame(rows); R.to_csv("/workspace/tradingview/validation/history_sensitivity.csv", index=False)
with pd.option_context("display.width", 250, "display.max_colwidth", 140):
    print(R.drop(columns=["detail"]).to_string(index=False))
    for _, r in R[R.mismatched_fields > 0].iterrows(): print(f"\n{r.ticker} | {r.variant}: {r.detail}")
