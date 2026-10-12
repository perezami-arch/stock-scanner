"""Build setups_prepared.csv: canonical PIT setups + realized outcomes (direction-adjusted).
Realized = tracker's day-5 / day-20 / total (last available day <= 20) columns where present (base = alert price);
otherwise computed from price data after the cutoff (base = cutoff close), flagged realized_source='computed'."""
import numpy as np, pandas as pd, pit
df = pit.load_setups()
def comp(r, n):
    try: v = pit.realized_fixed(r.ticker, r.asset, r.asof_ts, n)
    except FileNotFoundError: return np.nan
    return np.nan if v is None else r.dir_sign * v
def avail(r):   # bars available after cutoff (<= 20)
    try:
        for n in range(20, 0, -1):
            if pit.realized_fixed(r.ticker, r.asset, r.asof_ts, n) is not None: return n
    except FileNotFoundError: pass
    return 0
df["px_day5"] = df.apply(lambda r: comp(r, 5), axis=1)     # own price-based check for every row
df["px_day20"] = df.apply(lambda r: comp(r, 20), axis=1)
df["px_ndays"] = df.apply(avail, axis=1)
df["px_total"] = df.apply(lambda r: comp(r, r.px_ndays) if r.px_ndays > 0 else np.nan, axis=1)
has = df["trk_total"].notna()
df["realized_source"] = np.where(has, "tracker", np.where(df["px_total"].notna(), "computed", "none"))
df["r5"] = df["trk_day5"].where(has, df["px_day5"])
df["r20"] = df["trk_day20"].where(has, df["px_day20"])
df["rtot"] = df["trk_total"].where(has, df["px_total"])
df["ntot"] = df["trk_ndays"].where(has, df["px_ndays"])
df.to_csv("setups_prepared.csv", index=False)
m = df[has]
print("rows", len(df), df.realized_source.value_counts().to_dict())
print("tracker vs own-price day5 corr:", m[["trk_day5", "px_day5"]].corr().iloc[0, 1].round(3), "n", m[["trk_day5","px_day5"]].dropna().shape[0])

# ---- market-adjusted outcomes: excess vs SPY (US) / BTC-USD and ETH-USD (crypto), same window from the cutoff ----
def bench(r, n, sym):
    if pd.isna(n) or n <= 0: return np.nan
    a = "stock" if sym == "SPY" else "crypto"
    try: v = pit.realized_fixed(sym, a, r.asof_ts, int(n))
    except FileNotFoundError: return np.nan
    return np.nan if v is None else v
def raw(r, n):   # undirected own-price return from cutoff close
    return r[f"px_day{n}"] * r.dir_sign if n in (5, 20) else r.px_total * r.dir_sign
for tag, n_of in [("5", lambda r: 5), ("20", lambda r: 20), ("tot", lambda r: r.px_ndays)]:
    b1 = df.apply(lambda r: bench(r, n_of(r), "SPY" if r.asset == "stock" else "BTC-USD"), axis=1)
    rr = df.apply(lambda r: raw(r, 5 if tag == "5" else 20 if tag == "20" else 0), axis=1)
    df[f"x{tag}"] = df.dir_sign * (rr - b1)                      # direction-adjusted excess vs SPY/BTC
    if tag == "tot":
        b2 = df.apply(lambda r: bench(r, n_of(r), "ETH-USD") if r.asset == "crypto" else np.nan, axis=1)
        df["xeth_tot"] = df.dir_sign * (rr - b2)
df.to_csv("setups_prepared.csv", index=False)
print("excess coverage:", df[["x5", "x20", "xtot", "xeth_tot"]].notna().sum().to_dict())
m = df[df.excess_vs_spy_pct.notna()] if "excess_vs_spy_pct" in df else None
