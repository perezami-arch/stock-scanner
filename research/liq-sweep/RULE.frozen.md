# Liquidity-sweep reversal — pre-registered specification (FROZEN)

Frozen: 2026-10-10 19:26 IDT, BEFORE any liquidity-sweep backtest was run. Approved by Ilan for the intraday scanner at WEIGHT 0.
Code: `liq_sweep.py` (`P` = parameters below, VERSION 1.0). Any later change = new version + new RULE file.
Everything is chosen a priori; alternatives are pre-registered variants counted in one BH-FDR family.

## 1. Levels (liquidity)
* Confirmed swing pivots: fractal width **w = 5** (pivot high = high strictly above the 5 bars on each side; confirmed at
  the close of bar k+5). Reason: 5/5 is the common "swing" fractal; 2/2 is noise on 1m.
* A pivot is an active level from its confirmation bar while its age <= **L = 100 bars** and it has never been swept.
* Crypto intraday (1m, 15m) also: previous UTC day high / low (PDH / PDL), active during the current UTC day.
* A level is retired the first time it is pierced (whether the pierce becomes a sweep or a breakout).

## 2. Sweep event (SHORT; LONG is the mirror)
* Pierce bar s: high[s] > level (level active at s-1).
* Reclaim: the first bar r in [s, s+2] with close[r] < level ("closes back inside within 1-3 bars"). If closes stay
  >= level for s..s+2 → breakout, no event.
* Several levels reclaimed on the same bar r → one event, level = the highest such level.
* Wick extreme X = max(high[s..r]).
* Volume flag: vol_ratio = max(volume[s..r]) / median(volume[s-20..s-1]); **spike = vol_ratio > 2.0**.

## 3. Orders
* Stop = X + **0.1·ATR14[r]**; minimum risk 0.25·ATR14[r].
* Target ("next liquidity zone", single pre-defined chain): the nearest active (unswept, confirmed, age <= L) opposite pivot
  below entry (crypto intraday: PDL counts too); if none → nearest untouched bullish FVG below entry within L bars
  (bars k-2,k with low[k] > high[k-2], never traded into since: min(low[k+1..r]) > low[k]; target = low[k]); if none → 2R.
* **E1**: enter at the close of bar r (taker).
* **E2**: limit sell at the swept level, valid for **N = 5** bars (r+1 … r+5). Filled if high >= level (fill = max(level,
  open)). Cancelled if the target or the stop is touched first; if the stop and the level are touched in the same bar →
  filled and stopped (conservative). Maker fill.
* Management: fixed stop and target, no trailing. Within a bar: stop first. Time exit at the close of bar entry + **50**.

## 4. Costs (pre-set)
* Crypto: taker 0.05%/side, maker 0.02%/side (E2 entry, target exits). Slippage only on taker fills, by 24h-volume rank
  (same tiers as fib-spiral): 1–20: 0.03%, 21–60: 0.08%, >60: 0.15%. Funding (Binance history) accrued over the hold.
* Stocks: 0.05%/side slippage on taker fills, 0.02% on limit fills, short borrow 1%/yr.

## 5. Data
* Crypto: Binance USDT-M perps (data.binance.vision public dumps; same crypto universe as fib-spiral, non-crypto perps
  excluded): 15m 2025-10-01 → 2026-10-07 (66 symbols); 1m 2026-07-01 → 2026-10-07 (PROM, USELESS + 28 most liquid).
* Stocks: daily, scanner universe 2019-01-01 → 2026-10-07 (yfinance adjusted).

## 6. Variants (FDR family) and baselines
Dataset {crypto_1m, crypto_15m, stock_1d} × direction {SHORT, LONG} × entry {E1, E2} × filter {ALL, VOLSPIKE} = 24
variants. Tests per variant: (i) mean net R > 0; (ii) paired difference vs random-entry baseline. 48 tests, BH-FDR q < 0.10.
Random baseline: per event 10 random bars of the same symbol within ±1 day (1m) / ±10 days (15m) / ±120 sessions (daily),
same direction, same % stop and % target distances, same costs model and time exit, entry at that bar's close. Seed 20261010.

## 7. Statistics and verdict
Two-way clustered SE (symbol × entry date), p = max(symbol, date, two-way); drop top-1/top-3 symbols; walk-forward split at
median entry date. A variant PASSES only if: N >= 30 from >= 10 entry dates, mean net R > 0 with q < 0.10, q < 0.10 vs
random, positive in both walk-forward halves, and positive after dropping the top-3 symbols.

## 8. Leak test
`liq_sweep_columns(df, cutoff)` identical for truncated df / full df with cutoff / truncated + 50 junk bars; every backtest
event reproduced by the function at its reclaim bar.
