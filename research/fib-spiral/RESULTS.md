# Fib-spiral SHORT rule — results (v1.0, rule frozen 2026-10-08 16:55 IDT, RULE.frozen.md sha256 4486345…b97d6)

## Data
* crypto_1h: Binance USDT-M perps, 66 crypto symbols (top-100 by volume + PROM/USELESS, minus 35 TradFi perps — gold/silver/oil/
  stock tokens/ETFs, list in data/noncrypto.json), 2024-10-01 → 2026-10-08, funding history per symbol.
* stock_1d: 371 scanner-universe stocks, 2019-01 → 2026-10-07 (yfinance adjusted).
* crypto_1m (sensitivity): 10 crypto symbols (PROM, USELESS + 8 most liquid), 2026-07-01 → 2026-10-07.
Deviations from the plan (none touch the rule): Binance REST became geo-blocked (451) on 10.10, so AKEUSDT 1h, the 1m data and the
crypto/TradFi split came from data.binance.vision public dumps + a name-based list (exchange metadata was not reachable).

## Leak / repaint test — PASS
957/957 cutoffs identical (truncated vs full+cutoff vs junk-appended); 447/447 backtest events reproduced by fib_spiral_columns at
their trigger bar (out/leak_test.csv).

## PROM sanity (Binance 1h, Ilan's WEEX trade 29–30.08.2026)
Code: A 4.803 (29.08 09:00 IDT), B 7.164, C 5.865, D 7.888 (30.08 05:00) — Ilan: A 4.811, D 7.872 ✔.
D confirmed 13:00 (3×ATR drop); first fan break after that = 1/2 fan at the 17:00 bar → entry 6.929 (Ilan 7.153, earlier, before
the zigzag could confirm D). Stop 7.336 (Ilan 7.423). T1 = T2 = 6.710 (fib 0.382; T1 via the 1/2 fan, T2 via the 0.786 circle,
score 4) — Ilan 5.402 (just under 0.786). Outcome: T1 hit in 5 bars, +2.8% net (+0.47R); a 0.786 target without trailing would have
made +20.8% (+3.5R) in 23 bars. ⇒ The code reproduces the structure; Ilan's deep target is NOT what "first/most-lines crossing" gives.

## Results (net of fees, slippage, funding/borrow; R = net % / initial risk %)
Primary = F9 fans, T1 target, TR trailing.
| dataset | policy | N | hit | mean R [95% CI] | median R | mean net % | stop / target | avg bars |
|---|---|---|---|---|---|---|---|---|
| crypto_1h | T1 TR (primary) | 4727 | 59% | −0.12 [−0.15, −0.09] | +0.06 | −0.28 | 24% / 76% | 4.7 |
| crypto_1h | T2 TR | 4727 | 56% | −0.13 [−0.17, −0.09] | +0.04 | −0.31 | 28% / 69% | 6.2 |
| crypto_1h | (b) fixed 0.786, TR | 4727 | 45% | −0.11 | −0.16 | −0.29 | 47% / 36% | 16.7 |
| crypto_1h | (a) 3×ATR fixed, no target | 4727 | 39% | +0.02 [−0.24, 0.28] | −1.21 | −0.10 | 57% / – | 90 |
| crypto_1h | (c) random shorts, same stop/target | | | −0.14 | | | | |
| stock_1d | T1 TR (primary) | 4063 | 70% | −0.07 [−0.11, −0.035] | +0.14 | −0.45 | 28% / 71% | 4.9 |
| stock_1d | T2 TR | 4063 | 63% | −0.10 [−0.14, −0.06] | +0.11 | −0.64 | 34% / 63% | 6.5 |
| stock_1d | (b) fixed 0.786, TR | 4063 | 40% | −0.18 | −1.01 | −1.46 | 53% / 29% | 15.3 |
| stock_1d | (a) 4×ATR chandelier | 4063 | 31% | −0.44 | −0.81 | −2.97 | 93% / – | 39 |
| stock_1d | (c) random shorts | | | −0.11 | | | | |
| crypto_1m | T1 TR | 8229 | 10% | −1.24 | −0.81 | −0.22 | 28% / 72% | 4.9 |
Gross (before costs) crypto_1h T1 = +0.006R: zero edge, costs (≈0.30%/trade) make it negative. Median RR at entry: T1 0.28, T2 0.35
(T1 lands on fib 0.382 most often — the stop above the rejection candle is ~3× wider than the distance to the first crossing).
1m: risk 0.25% vs costs 0.21% → untradeable.

## FDR (96 tests = 3 datasets × F9/F5 × T1/T2 × TR/NT × {abs, vs a, vs b, vs c})
* "mean R > 0": every variant is significantly NEGATIVE (q < 0.002). Nothing is profitable.
* vs random (c): crypto 1h/1m: no difference (q 0.18–0.65). Stocks F9: +0.04R (q 0.06–0.10), positive in both walk-forward halves.
* vs 0.786 (b): stocks +0.07…+0.23R (q < 0.01); crypto no difference.
* RULE §11 relative verdict formally passes on stock_1d F9 (T1/T2 × TR/NT) and F5-T2-TR — but only as "loses less than a random
  short / the current policy in a rising market". Absolute result −0.07R/−0.45% per trade ⇒ NOT deployable. Weight stays 0.
* TR vs NT: no material difference (most trades exit at the near target before 1R).

## Files
RULE.frozen.md · fib_spiral.py (fib_spiral_columns, find_events, TRACKER_KEYS) · backtest_fib.py · analyze_fib.py · leak_test.py ·
common_bt.py · out/events_*.csv · out/descriptives.csv · out/fdr_tests.csv · out/verdicts.csv · out/leak_test.csv · prom_check.py
