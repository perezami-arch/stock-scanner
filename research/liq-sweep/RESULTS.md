# Liquidity-sweep reversal — results (v1.0, frozen RULE.frozen.md sha256 ff1c629…959c3)

Data: crypto 15m 66 symbols 2025-10-01 → 2026-10-07; crypto 1m 30 symbols 2026-07-01 → 2026-10-07 (Binance USDT-M, data.binance.vision);
stocks daily 371, 2019 → 2026-10-07. Events: 1m 167,446 · 15m 129,870 · daily 38,281 (both directions).
Leak test: PASS — 528/528 cutoffs identical (truncated / full+cutoff / junk-appended) and identical to full-history detection.
Implementation note (disclosed): after the first run the E2 R denominator was changed from (stop − fill) to the planned risk
(stop − limit level), because gap fills above the stop produced negative/near-zero risk and meaningless R. Rule, events and fills unchanged.

| dataset | dir | filter | entry | N | hit | mean R [95% CI] | median R | q (abs) | vs random (q) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| crypto_1m | both | all | E1/E2 | 34k–85k | 14–25% | −1.7 … −2.8 | ≈ −2.2 | <0.001 neg | ≈0 | FAIL (risk 0.14% ≪ costs) |
| crypto_15m | SHORT | ALL | E1 | 62,433 | 26% | −0.60 [−0.67, −0.52] | −1.37 | neg | +0.02 (0.47) | FAIL |
| crypto_15m | SHORT | VOLSPIKE | E2 | 23,219 | 18% | −0.51 | −1.36 | neg | +0.09 (0.075) | FAIL |
| crypto_15m | LONG | all | E1/E2 | 26k–67k | 14–28% | −0.52 … −0.81 | | neg | ≈0 | FAIL |
| stock_1d | SHORT | ALL | E1 | 20,276 | 20% | −0.27 [−0.32, −0.22] | −1.04 | neg | +0.02 (0.47) | FAIL |
| stock_1d | SHORT | ALL | E2 | 15,764 | 9% | −0.24 | −1.03 | neg | +0.21 (<0.001) | FAIL (abs < 0) |
| stock_1d | LONG | ALL | E1 | 18,005 | 27% | **+0.15 [+0.07, +0.23]** | −1.03 | 0.0009 | **+0.10 (0.036)** | PASS (fragile) |
| stock_1d | LONG | VOLSPIKE | E1 | 3,745 | 32% | +0.09 | −1.02 | 0.16 | +0.05 (0.47) | FAIL |
| stock_1d | LONG | ALL/VOL | E2 | 2.5k–13k | 12–17% | −0.02 … +0.06 | | n.s. | ≈0 | FAIL |
Full table: out/descriptives.csv, out/fdr_tests.csv (48 tests, BH-FDR), out/verdicts.csv.
Stock LONG E1 caveats: walk-forward +0.12R / +0.18R, drop-top-3 +0.14R, but the mean comes from a fat right tail (pivot targets
4.5R median, winners up to 50R); median −1.03R; capping winners at 5R gives −0.10R; random longs in the same windows +0.05R
(bull market); 2022 negative (−0.17R). ⇒ candidate for weight-0 forward tracking on stocks only, not for sizing.
Volume spike: raises hit rate and R slightly everywhere but never turns a variant positive. E2 (limit on retest) fills 68–78%,
cuts costs, but loses more R in crypto (fills are the ones that come back to the stop).

Files: RULE.frozen.md · liq_sweep.py (detect, liq_sweep_columns, TRACKER_KEYS) · backtest_liq.py · analyze_liq.py · leak_test.py ·
out/events_*.csv · out/descriptives.csv · out/fdr_tests.csv · out/verdicts.csv · out/leak_test.csv
