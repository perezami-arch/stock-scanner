# Backtest of open-source TA repos: TA-Lib, pandas-ta, smart-money-concepts and three Elliott Wave repos

Date: 2026-10-08. Work dir: `/workspace/ta-repos-eval/` (own venv; nothing was installed on Ilan's laptop; no overlap with `/workspace/gh-repos-eval`).
Inputs were read-only: `/workspace/tracker/setups-point-in-time-2026-10-08.csv`, `hold-no-stop-longs-2026-10-08.csv`, the PIT cutoffs (`rule_bar_actual`) and the active-policy trades from `/workspace/trading-frameworks-eval` (§3.14). Nothing in those files was modified.

## TL;DR

* **Comparisons run:** 859, all in one BH-FDR family; 894 more were skipped because N<20 on a side.
  * 138 have nominal p<0.05. About 43 would be expected by chance.
  * **7 survive q<0.10, and all 7 pass the robustness checks.**
* **The 3 surviving filters are all on stock shorts:**
  * Connors RSI Q5 (most oversold): +6.7 pp vs SPY, 38 vs 151, q=0.019.
  * Distance below SMA200 in ATR: Q5 +7.7 pp (q=0.061); rank slope +9.8 pp (q=0.047).
  * **None of them adds anything new.** They re-express "already breaking down", which the short rule and the vp120-below-VA lead from §3.14 already capture:
    * SMA200 Q5 overlaps VA-below in 30 of 38 shorts, and 37 of 38 already pass the short rule.
    * Connors RSI adds nothing within rule-passing shorts (p=0.16).
* **The 4 surviving level rules are all crypto longs, and all are worse than the active 3×ATR policy:**
  * smc next-open-FVG target: −20.7 pp per trade raw on a full exit, −10.3 pp on a half exit.
  * python-taew wave target: −18.7 pp full, −9.4 pp half.
  * In this sample these targets cut crypto winners short.
* **No indicator, candle, smc object or Elliott count improves stock longs**, which is the main use case. Momentum 12-1, the reference, did not either.
* **Verdicts:**

| Library | License | Leak/repaint (PIT) | Coverage | Result | Verdict |
|---|---|---|---|---|---|
| TA-Lib 0.8.1 (ta-lib-python) | BSD-2 (wrapper), BSD (C lib) | **Clean.** 0 leaks in 233 output columns × 30 setups. The 3 flagged columns are inf overflow in COSH/EXP/SINH. | 100% | 2 robust short filters (SMA200 distance), redundant with the existing lead. Candles: 0 of 53 nominally significant. | **Adopt only as a calculator** (fast, correct, stable). Score weight 0. |
| pandas-ta 0.4.71b0 | MIT | Mostly clean. **12 of 331 columns use future bars:** DPO (centred by default), Ichimoku chikou, TOS_STDEVALL (7 columns) and ZIGZAG (repaints). Its candle patterns call TA-Lib. | 100% | 1 robust short filter (Connors RSI), redundant. | **Adopt with caveats:** blacklist DPO/chikou/TOS_STDEVALL/ZIGZAG. The original GitHub repo returns 404 now; the PyPI package and pandas-ta.dev site are alive. Score weight 0. |
| smart-money-concepts 0.0.27 | MIT | **Repaints everywhere if run on full data:** a centred swing window, FVG from the next candle, mitigation/sweep indices taken from future bars, an artificial swing on the last bar, and a liquidity range based on the whole series. Usable only through my PIT wrapper (truncate, drop artificial swings, count only objects not mitigated before the cutoff). | ~99% (swings) / 75% (OB) / 55–81% (liq/FVG) | Filters: 0 of 184 survive. Crypto FVG target is **robustly harmful**. Moderate agreement with scanner_geometry on FVGs (κ 0.40–0.61), weak on OBs (κ 0.34–0.40), none on liquidity (κ ≈0.06). | **Skip** for scoring. scanner_geometry already covers FVG and OB. |
| python-taew | MIT | 1-bar look-ahead if run on full data (a pivot on the cutoff bar needs the next bar; 13 of 30). Clean after truncation. | 86–97% "valid count", which is implausibly permissive | Filters: noise. Crypto wave target is **robustly harmful**. κ with our count −0.04. | **Skip.** It also has bugs: no time-order check, a wrong wave-4 rule, and `diff4z` uses x. |
| ElliottWaveAnalyzer (drstevendev) | **No license** (all rights reserved) | Last wave is unconfirmed in 1 of 30 and the chain changes with later bars in 1 of 30; handled by checking completed waves only. | 22–25% stocks, 67% crypto | Filters: noise ("in wave 3" on shorts −5.8 pp, q=0.19). Crypto target −7.3 pp, q=0.15. κ with ours 0.02. | **Skip.** It can't legally be vendored, and its README says the analyzer is "not working atm". |
| ElliottWaves (alessioricco) | MIT | Raw argrelextrema(order=7) repaints: in 9 of 30 setups provisional pivots in the last 7 bars later vanish, and 3 of 30 have pivots that appear only later. After dropping the last 7 bars it matches the full-data result 30/30. | 40–53% | Filters: 0 of 13 nominally significant. | **Skip.** It is a notebook dump and its demo main function is broken. |

Bottom line: **nothing here adds a new edge to the scanner.** TA-Lib and pandas-ta are fine as indicator engines with the blacklist above. smc and all the Elliott repos should stay out of scoring and out of stop/target logic. Every new column stays at weight 0.

## 1. Setup and method

* **Trades:** 695 unique main-sheet trades. Features were computed for 788 setups (2 TA-Lib errors). The segments are the same as §3.14:

| Segment | N |
|---|---|
| All stock longs | 242 |
| Rule-filtered stock longs | 115 |
| Perplexity stock longs | 59 |
| Grok stock longs | 142 |
| All stock shorts | 189 |
| Crypto longs | 264 |

* **Outcome:** the active-policy trade return (`sim_geo_trades.csv`, variant base_c).
  * Stocks use a 4×ATR14 chandelier; longs take half off at the 1.618 extension.
  * Crypto uses a fixed 3×ATR stop.
  * Results are reported as excess vs SPY (stocks) or BTC (crypto).
* **PIT:** every feature is computed only from bars up to `rule_bar_actual`.
  * Shorts are mirrored (p' = K − p, which preserves Fibonacci ratios) so that Elliott and smc logic reads them as longs.
* **Filter tests:** mean x_mkt with vs without the feature. Continuous features get Q1-vs-rest, Q5-vs-rest and a rank slope.
  * p is the maximum of the ticker-, entry-date- and two-way-clustered p-values.
  * p_incr controls for the rule inputs; p_mom controls for momentum 12-1.
* **Level tests:** paired comparison vs the active policy on covered trades, close-based, using the same `sim_geo` engine with only the level dictionary swapped.
  * The regression check against sim_ratchet_trades matched (max difference 2e-16).
  * Stops: fix = the level −0.5 ATR is the only stop; hyb = the tighter of that and the policy stop.
  * Targets: full or half exit.
* **Statistics:** one BH family over all 859 executed comparisons, q<0.10, N≥20 on each side.
  * **ROBUST** means the median, the raw (non-excess) result, the within-date result, and the results without the top-1 and top-3 tickers all keep the same sign.
  * A result that passes FDR but fails these checks is labelled LUCK. There were 0 LUCK results.

## 2. Leak and repaint checks

The three-way test compares three versions at the cutoff: T = history truncated at the cutoff; F = full history, read at the cutoff; J = garbage bars appended after the cutoff. Any F≠T or J≠T at or before the cutoff counts as a leak or repaint.

### TA-Lib (233 output columns × 30 setups)
Columns with any difference:

| func   | col   |   F |   J |
|:-------|:------|----:|----:|
| COSH   | real  |   3 |   3 |
| EXP    | real  |   3 |   3 |
| SINH   | real  |   3 |   3 |

These are inf/overflow in the math transforms, not leaks. **TA-Lib is clean.**

### pandas-ta ("All" study, 331 columns × 12 setups)
Columns that leak or repaint:

| col              |   F |   J |   n |
|:-----------------|----:|----:|----:|
| DPO_20           |   8 |  12 |  12 |
| ICS_26           |   3 |  12 |  12 |
| TOS_STDEVALL_LR  |  12 |  12 |  12 |
| TOS_STDEVALL_L_1 |  12 |  12 |  12 |
| TOS_STDEVALL_L_2 |  12 |  12 |  12 |
| TOS_STDEVALL_L_3 |  12 |  12 |  12 |
| TOS_STDEVALL_U_1 |  12 |  12 |  12 |
| TOS_STDEVALL_U_2 |  12 |  12 |  12 |
| TOS_STDEVALL_U_3 |  12 |  12 |  12 |
| ZIGZAGd_5.0%_10  |   2 |   0 |  12 |
| ZIGZAGs_5.0%_10  |   2 |   0 |  12 |
| ZIGZAGv_5.0%_10  |   2 |   0 |  12 |

None of these was used as a feature. Chikou was excluded from the Ichimoku features.

### smart-money-concepts (30 setups): setups where the output changes when it is run on full data (F) or with junk future bars (J)

| func   |   n |   F_any |   J_any |   last_bar |   max_bars_back |
|:-------|----:|--------:|--------:|-----------:|----------------:|
| bos    |  30 |      16 |      30 |          2 |              55 |
| fvg    |  30 |      22 |      30 |          8 |             226 |
| liq    |  30 |       8 |      30 |          0 |             433 |
| ob     |  30 |      19 |      30 |          1 |             356 |
| ret    |  30 |      16 |      22 |         11 |             423 |
| swing  |  30 |      28 |      30 |         28 |              19 |

* `last_bar` counts setups where smc stamps an artificial swing on the last bar. This happens on 100% of the 787 setups with features, and the wrapper removes it.
* `max_bars_back` is how far before the cutoff the earliest difference appears. The mitigation and sweep indices of objects up to ~430 bars old depend on the future.
* J≠T in every setup because the liquidity range is 1% of the full series' range, and because the mitigated/broken indices are searched forward.
* **Conclusion:** smc on full data is unusable for backtests. The PIT wrapper (`features_smc.py`) fixes this.

### Elliott adapters (30 setups)

| Check | Result |
|---|---|
| python-taew: full series has a pivot on the cutoff bar (1-bar look-ahead) | 13/30 |
| python-taew: pivots missing in F | 0/30 |
| ElliottWaves raw: provisional pivots that later vanish / pivots that appear only later | 9/30 / 3/30 |
| ElliottWaves after dropping the last 7 bars = full series | 30/30 |
| ElliottWaveAnalyzer: last wave unconfirmed / chain changes with future bars | 1/30 / 1/30 |
| Junk-future determinism (all adapters) | 0 mismatches in 1359 values |
| My pruned DFS vs the repo's brute force (ElliottWaves) | 30/30 identical result sets |

## 3. Comparisons by family

| family    | kind   |   n |   nom |     minp |   q10 |   robust |
|:----------|:-------|----:|------:|---------:|------:|---------:|
| ew_ar     | filter |  13 |     0 | 0.159    |     0 |        0 |
| ew_ewa    | filter |   9 |     1 | 0.014    |     0 |        0 |
| ew_ewa    | level  |  18 |     2 | 0.00624  |     0 |        0 |
| ew_ours   | filter |  11 |     1 | 0.019    |     0 |        0 |
| ew_taew   | filter |  17 |     1 | 0.017    |     0 |        0 |
| ew_taew   | level  |  36 |     5 | 0.000331 |     2 |        2 |
| pandas_ta | filter | 106 |    19 | 4.55e-05 |     1 |        1 |
| reference | filter |  16 |     3 | 0.00515  |     0 |        0 |
| smc       | filter | 184 |    15 | 0.00426  |     0 |        0 |
| smc       | level  |  47 |     4 | 6.76e-05 |     2 |        2 |
| talib_cdl | filter |  53 |     0 | 0.071    |     0 |        0 |
| talib_ind | filter | 349 |    87 | 0.00031  |     2 |        2 |

Flags across the whole family: {'noise': 721, 'nominal p<0.05 only (fails FDR)': 131, 'ROBUST': 7}.

## 4. Survivors (q<0.10)

| kind   | family    | segment         | feature                                                     | test                    |   N_with |   N_without |   dates |   diff_x |   diff_med_x |   drop1 |   drop3 |   wd |        p |   p_incr |    p_mom |   q_BH | effect   | flag   |
|:-------|:----------|:----------------|:------------------------------------------------------------|:------------------------|---------:|------------:|--------:|---------:|-------------:|--------:|--------:|-----:|---------:|---------:|---------:|-------:|:---------|:-------|
| level  | smc       | Crypto LONG     | target: smc next open FVG edge, full exit (close)           | paired vs active policy |      215 |           0 |      48 |    -7.17 |         0    |  -18.91 |  -19.16 |      | 6.76e-05 |          |          |   0.02 | worse    | ROBUST |
| filter | pandas_ta | All stock SHORT | pandas-ta connors_rsi (aligned) : Q5 (highest 20%) vs rest  | Q5 vs rest              |       38 |         151 |      22 |     6.66 |         9.02 |    6.32 |    5.81 | 4.93 | 4.55e-05 |  0.00506 | 0.000155 |   0.02 | better   | ROBUST |
| level  | smc       | Crypto LONG     | target: smc next open FVG edge, 1/2 exit (close)            | paired vs active policy |      215 |           0 |      48 |   -10.33 |        -8.57 |   -9.46 |   -9.58 |      | 6.76e-05 |          |          |   0.02 | worse    | ROBUST |
| filter | talib_ind | All stock SHORT | talib dist_sma200_atr (aligned) : rank slope (Q5-Q1 equiv.) | rank slope              |      189 |           0 |      22 |     9.84 |         8.84 |    3.73 |    2.47 | 3.04 | 0.00031  |  0.02    | 0.00112  |   0.05 | better   | ROBUST |
| level  | ew_taew   | Crypto LONG     | target: python-taew wave target, 1/2 exit (close)           | paired vs active policy |      226 |           0 |      51 |    -9.37 |        -8.12 |   -8.49 |   -8.42 |      | 0.000331 |          |          |   0.05 | worse    | ROBUST |
| level  | ew_taew   | Crypto LONG     | target: python-taew wave target, full exit (close)          | paired vs active policy |      226 |           0 |      51 |    -7.15 |         0    |  -16.99 |  -16.85 |      | 0.000331 |          |          |   0.05 | worse    | ROBUST |
| filter | talib_ind | All stock SHORT | talib dist_sma200_atr (aligned) : Q5 (highest 20%) vs rest  | Q5 vs rest              |       38 |         151 |      22 |     7.72 |         9.29 |    7.54 |    6.53 | 6.03 | 0.000496 |  0.03    | 0.00166  |   0.06 | better   | ROBUST |

* **Do the short survivors add anything?** This is a descriptive check (`shorts_check.py`), not part of the FDR family.
  * SMA200-distance Q5 overlaps vp120-below-VA in 30 of 38 shorts, and 37 of 38 already pass the short rule.
  * Connors RSI Q5 overlaps VA-below in 19 of 38 and the rule in 32 of 38. Within rule-passing shorts its effect is not significant (p=0.16, date-clustered).
  * **Verdict:** both re-express "already breaking down" and add nothing beyond the existing lead.
* **For the level survivors, diff_raw is the paired per-trade return difference vs the active policy** (raw, not excess).
  * The FVG and taew targets sit at a median of 3–4 ATR and are hit by 70–87% of trades.
  * Hitting them caps crypto winners that the 3×ATR fixed stop lets run.

## 5. Closest misses (nominal p<0.05, fail FDR); top 30 by p

| kind   | family    | segment                  | feature                                                                   | test                    |   N_with |   N_without |   dates |   diff_x |   diff_med_x |   drop1 |   drop3 |     wd |       p |   p_incr |   p_mom |   q_BH | effect   | flag                            |
|:-------|:----------|:-------------------------|:--------------------------------------------------------------------------|:------------------------|---------:|------------:|--------:|---------:|-------------:|--------:|--------:|-------:|--------:|---------:|--------:|-------:|:---------|:--------------------------------|
| filter | talib_ind | All stock SHORT          | talib ultosc (aligned) : Q5 (highest 20%) vs rest                         | Q5 vs rest              |       38 |         151 |      22 |     6.6  |         9.13 |    6.21 |    5.18 |   5.81 | 0.00198 |  0.06    | 0.00693 |   0.15 | better   | nominal p<0.05 only (fails FDR) |
| filter | talib_ind | All stock SHORT          | talib dist_sma50_atr (aligned) : Q5 (highest 20%) vs rest                 | Q5 vs rest              |       38 |         151 |      22 |     7.31 |         8.82 |    7.11 |    6.1  |   5.37 | 0.00223 |  0.08    | 0.00532 |   0.15 | better   | nominal p<0.05 only (fails FDR) |
| filter | talib_ind | All stock SHORT          | talib adx14 : Q5 (highest 20%) vs rest                                    | Q5 vs rest              |       38 |         151 |      22 |     6.04 |         6.17 |    5.59 |    4.43 |   5.16 | 0.00339 |  0.00275 | 0.00726 |   0.15 | better   | nominal p<0.05 only (fails FDR) |
| filter | pandas_ta | Rule-filtered stock LONG | pandas-ta stc (aligned) : rank slope (Q5-Q1 equiv.)                       | rank slope              |      115 |           0 |      22 |   -12.4  |        -4.92 |   -4.58 |   -2.88 |  -2.08 | 0.00343 |  0.00667 | 0.0034  |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| filter | talib_ind | All stock LONG           | talib adx14 : Q5 (highest 20%) vs rest                                    | Q5 vs rest              |       49 |         193 |      25 |    -6.38 |        -2.37 |   -5.86 |   -4.84 |  -4.69 | 0.00353 |  0.00252 | 0.00388 |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| filter | talib_ind | All stock SHORT          | talib rsi14 (aligned) : Q5 (highest 20%) vs rest                          | Q5 vs rest              |       38 |         151 |      22 |     7.08 |         8.72 |    6.71 |    5.64 |   5.14 | 0.00399 |  0.12    | 0.00903 |   0.15 | better   | nominal p<0.05 only (fails FDR) |
| filter | pandas_ta | All stock SHORT          | pandas-ta squeeze_mom_atr (aligned) : Q5 (highest 20%) vs rest            | Q5 vs rest              |       38 |         151 |      22 |     6.87 |         8.82 |    6.49 |    5.47 |   5.23 | 0.00409 |  0.09    | 0.00731 |   0.15 | better   | nominal p<0.05 only (fails FDR) |
| filter | smc       | Crypto LONG              | smc back_OB_dist_atr : rank slope (Q5-Q1 equiv.)                          | rank slope              |      199 |           0 |      51 |   -22.07 |       -24.52 |  -13.82 |   -6.12 |  -6.78 | 0.00426 |  0.07    | 0.00672 |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| filter | talib_ind | Rule-filtered stock LONG | talib dist_sma50_atr (aligned) : Q5 (highest 20%) vs rest                 | Q5 vs rest              |       23 |          92 |      22 |    -7.59 |        -0.38 |   -6.49 |   -4.59 |  -4.7  | 0.00428 |  0.07    | 0.00444 |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| filter | talib_ind | All stock LONG           | talib natr14 : Q1 (lowest 20%) vs rest                                    | Q1 vs rest              |       49 |         193 |      25 |    -5.21 |        -1.6  |   -4.67 |   -3.68 |  -3.83 | 0.0043  |  0.00545 | 0.00564 |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| filter | smc       | All stock LONG           | smc deepest_retracement_pct : Q5 (highest 20%) vs rest                    | Q5 vs rest              |       49 |         193 |      25 |    -6.38 |        -2.31 |   -5.74 |   -4.65 |  -3.32 | 0.00431 |  0.00219 | 0.00474 |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| level  | ew_taew   | Crypto LONG              | stop: tighter of python-taew last wave end-0.5ATR and policy stop (close) | paired vs active policy |      210 |           0 |      51 |    -4.09 |         0    |   -8.9  |   -6.75 |        | 0.00432 |          |         |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| filter | talib_ind | All stock SHORT          | talib adx14 : rank slope (Q5-Q1 equiv.)                                   | rank slope              |      189 |           0 |      22 |     7.68 |         7.04 |    2.95 |    1.91 |   2.38 | 0.00455 |  0.00884 | 0.01    |   0.15 | better   | nominal p<0.05 only (fails FDR) |
| filter | talib_ind | All stock LONG           | talib bb_width : Q1 (lowest 20%) vs rest                                  | Q1 vs rest              |       49 |         193 |      25 |    -5.9  |        -1.9  |   -5.43 |   -4.41 |  -4.67 | 0.00477 |  0.00921 | 0.00661 |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| filter | talib_ind | All stock SHORT          | talib obv_slope20_z (aligned) : rank slope (Q5-Q1 equiv.)                 | rank slope              |      189 |           0 |      22 |     7.39 |         3.34 |    3.27 |    2.52 |   2.65 | 0.00478 |  0.29    | 0.00436 |   0.15 | better   | nominal p<0.05 only (fails FDR) |
| filter | smc       | All stock LONG           | smc current_retracement_pct : Q5 (highest 20%) vs rest                    | Q5 vs rest              |       49 |         193 |      25 |    -5.79 |        -2.14 |   -5.13 |   -4.02 |  -2.89 | 0.00491 |  0.00411 | 0.00461 |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| level  | smc       | Crypto LONG              | stop: tighter of smc confirmed swing-0.5ATR and policy stop (close)       | paired vs active policy |      262 |           0 |      51 |    -3.27 |         0    |   -6.42 |   -4.44 |        | 0.00492 |          |         |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| filter | reference | All stock SHORT          | mom12-1 (aligned: -mom for shorts) : Q5 (highest 20%) vs rest             | Q5 vs rest              |       38 |         150 |      22 |     7.12 |         8.06 |    5.78 |    4.79 |   5.17 | 0.00515 |  0.02    | 0.01    |   0.15 | better   | nominal p<0.05 only (fails FDR) |
| level  | ew_taew   | Crypto LONG              | stop: python-taew last wave end -0.5ATR (fixed) (close)                   | paired vs active policy |      210 |           0 |      51 |    -3.88 |         0    |   -8.56 |   -6.3  |        | 0.00521 |          |         |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| filter | talib_ind | Crypto LONG              | talib dist_sma50_atr (aligned) : rank slope (Q5-Q1 equiv.)                | rank slope              |      264 |           0 |      51 |   -25.82 |       -23.78 |  -11.32 |   -5.7  |  -4.61 | 0.00526 |  0.02    | 0.00544 |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| filter | talib_ind | Rule-filtered stock LONG | talib macd_line_atr (aligned) : Q5 (highest 20%) vs rest                  | Q5 vs rest              |       23 |          92 |      22 |    -7.22 |        -2    |   -6.23 |   -4.52 |  -4    | 0.00533 |  0.03    | 0.00552 |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| filter | talib_ind | All stock SHORT          | talib ultosc (aligned) : rank slope (Q5-Q1 equiv.)                        | rank slope              |      189 |           0 |      22 |     7.25 |         9.23 |    3.29 |    2.42 |   3.71 | 0.0055  |  0.58    | 0.00772 |   0.15 | better   | nominal p<0.05 only (fails FDR) |
| filter | talib_ind | All stock SHORT          | talib rsi14 (aligned) : rank slope (Q5-Q1 equiv.)                         | rank slope              |      189 |           0 |      22 |     7.22 |         7.07 |    2.6  |    2.05 |   3.47 | 0.00553 |  0.78    | 0.00805 |   0.15 | better   | nominal p<0.05 only (fails FDR) |
| filter | talib_ind | All stock SHORT          | talib di_spread (aligned) : rank slope (Q5-Q1 equiv.)                     | rank slope              |      189 |           0 |      22 |     6.9  |         7.75 |    3.14 |    2.6  |   3.49 | 0.00583 |  0.71    | 0.00771 |   0.15 | better   | nominal p<0.05 only (fails FDR) |
| filter | talib_ind | All stock LONG           | talib adx14 : rank slope (Q5-Q1 equiv.)                                   | rank slope              |      242 |           0 |      25 |   -10.04 |        -4.82 |   -4.67 |   -3.36 |  -5.08 | 0.00592 |  0.00291 | 0.00331 |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| level  | ew_ewa    | Crypto LONG              | target: ElliottWaveAnalyzer wave target, full exit (close)                | paired vs active policy |      127 |           0 |      46 |    -7.26 |         0    |  -10.09 |   -9.39 |        | 0.00624 |          |         |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| level  | ew_ewa    | Crypto LONG              | target: ElliottWaveAnalyzer wave target, 1/2 exit (close)                 | paired vs active policy |      127 |           0 |      46 |    -7.69 |        -7.46 |   -5.04 |   -4.69 |        | 0.00624 |          |         |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| filter | smc       | Crypto LONG              | smc back_OB_dist_atr : Q5 (highest 20%) vs rest                           | Q5 vs rest              |       40 |         159 |      51 |   -16.2  |        -8.76 |  -16.11 |   -8.43 |  -6.4  | 0.00629 |  0.09    | 0.0018  |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| filter | talib_ind | All stock LONG           | talib macd_line_atr (aligned) : Q5 (highest 20%) vs rest                  | Q5 vs rest              |       49 |         193 |      25 |    -5.15 |        -1.47 |   -4.59 |   -3.55 |  -2.86 | 0.00637 |  0.0015  | 0.00564 |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| filter | talib_ind | Crypto LONG              | talib bb_width : Q1 (lowest 20%) vs rest                                  | Q1 vs rest              |       53 |         211 |      51 |   -14.96 |        -8.09 |  -14.17 |   -8.18 | -15.43 | 0.00709 |  0.00168 | 0.00685 |   0.16 | worse    | nominal p<0.05 only (fails FDR) |

These follow the same pattern as §3.14:
* Shorts look better when they are already stretched down: momentum 12-1 Q5, ULTOSC, RSI, ADX, squeeze momentum.
* Stock longs look worse when they are stretched or trending hard: high ADX, MACD, distance above SMA50, high STC.
* Tighter crypto stops do worse.

None is FDR-significant, so none should be used.

## 6. Level tests (top 22 by p; close-based, paired vs active policy)

| family   | segment                  | feature                                                                   |   N_with |   coverage |   changed |   diff_raw |   diff_med_raw |   diff_x |   target_hit |   level_med_atr |        p |   q_BH | effect   | flag                            |
|:---------|:-------------------------|:--------------------------------------------------------------------------|---------:|-----------:|----------:|-----------:|---------------:|---------:|-------------:|----------------:|---------:|-------:|:---------|:--------------------------------|
| smc      | Crypto LONG              | target: smc next open FVG edge, 1/2 exit (close)                          |      215 |      81.44 |     86.98 |     -10.33 |         -10.73 |   -10.33 |        86.98 |            2.98 | 6.76e-05 |   0.02 | worse    | ROBUST                          |
| smc      | Crypto LONG              | target: smc next open FVG edge, full exit (close)                         |      215 |      81.44 |     86.98 |     -20.66 |         -19.95 |    -7.17 |        86.98 |            2.98 | 6.76e-05 |   0.02 | worse    | ROBUST                          |
| ew_taew  | Crypto LONG              | target: python-taew wave target, 1/2 exit (close)                         |      226 |      85.61 |     69.91 |      -9.37 |          -6.6  |    -9.37 |        69.91 |            4.02 | 0.000331 |   0.05 | worse    | ROBUST                          |
| ew_taew  | Crypto LONG              | target: python-taew wave target, full exit (close)                        |      226 |      85.61 |     69.91 |     -18.73 |         -17.92 |    -7.15 |        69.91 |            4.02 | 0.000331 |   0.05 | worse    | ROBUST                          |
| ew_taew  | Crypto LONG              | stop: tighter of python-taew last wave end-0.5ATR and policy stop (close) |      210 |      79.55 |     26.19 |      -9.73 |          -9.08 |    -4.09 |         0    |            1.47 | 0.00432  |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| smc      | Crypto LONG              | stop: tighter of smc confirmed swing-0.5ATR and policy stop (close)       |      262 |      99.24 |     16.79 |      -7.6  |          -5.1  |    -3.27 |         0    |            2.25 | 0.00492  |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| ew_taew  | Crypto LONG              | stop: python-taew last wave end -0.5ATR (fixed) (close)                   |      210 |      79.55 |     28.1  |      -9.45 |          -9.08 |    -3.88 |         0    |            1.47 | 0.00521  |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| ew_ewa   | Crypto LONG              | target: ElliottWaveAnalyzer wave target, full exit (close)                |      127 |      48.11 |     85.04 |     -15.37 |         -11.14 |    -7.26 |        85.04 |            6.23 | 0.00624  |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| ew_ewa   | Crypto LONG              | target: ElliottWaveAnalyzer wave target, 1/2 exit (close)                 |      127 |      48.11 |     85.04 |      -7.69 |          -4.63 |    -7.69 |        85.04 |            6.23 | 0.00624  |   0.15 | worse    | nominal p<0.05 only (fails FDR) |
| ew_taew  | Crypto LONG              | stop: tighter of python-taew invalidation-0.5ATR and policy stop (close)  |      233 |      88.26 |     11.16 |      -4.6  |          -3.02 |    -1.57 |         0    |            3.64 | 0.02     |   0.19 | worse    | nominal p<0.05 only (fails FDR) |
| smc      | Crypto LONG              | stop: smc confirmed swing -0.5ATR (fixed) (close)                         |      262 |      99.24 |     19.47 |      -6.54 |          -4.87 |    -2.83 |         0    |            2.25 | 0.02     |   0.19 | worse    | nominal p<0.05 only (fails FDR) |
| smc      | Crypto LONG              | target: smc next unswept liquidity, full exit (close)                     |      146 |      55.3  |     46.58 |     -10.31 |          -6.49 |    -5.16 |        46.58 |            9.84 | 0.07     |   0.36 | worse    | noise                           |
| smc      | Crypto LONG              | target: smc next unswept liquidity, 1/2 exit (close)                      |      146 |      55.3  |     46.58 |      -5.16 |          -0.53 |    -5.16 |        46.58 |            9.84 | 0.07     |   0.36 | worse    | noise                           |
| ew_ewa   | All stock LONG           | target: ElliottWaveAnalyzer wave target, 1/2 exit (close)                 |       33 |      13.64 |     15.15 |       0.65 |           0    |     0.65 |        18.18 |            6.76 | 0.1      |   0.43 | better   | noise                           |
| ew_taew  | All stock LONG           | target: python-taew wave target, full exit (close)                        |      176 |      72.73 |     23.86 |      -0.9  |          -0.02 |    -0.78 |        14.77 |            3.87 | 0.12     |   0.45 | worse    | noise                           |
| ew_taew  | Rule-filtered stock LONG | stop: python-taew invalidation -0.5ATR (fixed) (close)                    |      101 |      87.83 |     14.85 |       0.32 |           0.35 |     0.24 |        24.75 |            3.86 | 0.13     |   0.46 | better   | noise                           |
| ew_taew  | Crypto LONG              | stop: python-taew invalidation -0.5ATR (fixed) (close)                    |      233 |      88.26 |     15.88 |      -2.61 |          -2.52 |    -0.45 |         0    |            3.64 | 0.14     |   0.46 | worse    | noise                           |
| smc      | All stock LONG           | stop: smc unswept liquidity -0.5ATR (fixed) (close)                       |       70 |      28.93 |     10    |       1    |           0    |     0.88 |        14.29 |           10.28 | 0.14     |   0.46 | better   | noise                           |
| ew_taew  | Rule-filtered stock LONG | target: python-taew wave target, full exit (close)                        |       96 |      83.48 |     30.21 |      -1.18 |          -0.39 |    -1    |        19.79 |            3.43 | 0.15     |   0.46 | worse    | noise                           |
| smc      | All stock SHORT          | stop: smc order block -0.5ATR (fixed) (close)                             |      120 |      63.49 |     13.33 |      -0.85 |           0    |    -0.78 |         0    |            5.6  | 0.15     |   0.46 | worse    | noise                           |
| ew_taew  | All stock LONG           | stop: tighter of python-taew last wave end-0.5ATR and policy stop (close) |      170 |      70.25 |     28.82 |      -0.57 |          -0.97 |    -0.19 |        19.41 |            1.78 | 0.15     |   0.46 | worse    | noise                           |
| smc      | All stock LONG           | stop: tighter of smc confirmed swing-0.5ATR and policy stop (close)       |      227 |      93.8  |     22.03 |      -1.04 |          -0.52 |    -0.73 |        18.06 |            2.59 | 0.16     |   0.47 | worse    | noise                           |

* **No stop or target from smc or any Elliott repo beats the active policy in any segment.**
* On stocks the level rules are noise. On crypto, both tighter stops and earlier targets are worse.

## 7. Reference: momentum 12-1 in the same framework

| kind   | family    | segment                  | feature                                                        | test       |   N_with |   N_without |   dates |   diff_x |   diff_med_x |   drop1 |   drop3 |    wd |       p |   p_incr |   p_mom |   q_BH | effect   | flag                            |
|:-------|:----------|:-------------------------|:---------------------------------------------------------------|:-----------|---------:|------------:|--------:|---------:|-------------:|--------:|--------:|------:|--------:|---------:|--------:|-------:|:---------|:--------------------------------|
| filter | reference | All stock SHORT          | mom12-1 (aligned: -mom for shorts) : Q5 (highest 20%) vs rest  | Q5 vs rest |       38 |         150 |      22 |     7.12 |         8.06 |    5.78 |    4.79 |  5.17 | 0.00515 |     0.02 |    0.01 |   0.15 | better   | nominal p<0.05 only (fails FDR) |
| filter | reference | All stock SHORT          | mom12-1 (aligned: -mom for shorts) : rank slope (Q5-Q1 equiv.) | rank slope |      188 |           0 |      22 |     9.43 |         9.59 |    2.3  |    0.77 |  2.52 | 0.00976 |     0.08 |    0.06 |   0.17 | better   | nominal p<0.05 only (fails FDR) |
| filter | reference | All stock SHORT          | mom12-1 (aligned: -mom for shorts) : Q1 (lowest 20%) vs rest   | Q1 vs rest |       38 |         150 |      22 |    -4.83 |        -1.73 |   -3.41 |   -0.72 | -4.7  | 0.04    |     0.41 |    0.34 |   0.29 | worse    | nominal p<0.05 only (fails FDR) |
| filter | reference | Crypto LONG              | mom12-1 (aligned: -mom for shorts) : Q5 (highest 20%) vs rest  | Q5 vs rest |       53 |         211 |      51 |    16.07 |        -1.82 |    5.76 |  -10.68 | 10.04 | 0.25    |     0.19 |    0.94 |   0.57 | better   | noise                           |
| filter | reference | Grok stock LONG          | mom12-1 (aligned: -mom for shorts) : rank slope (Q5-Q1 equiv.) | rank slope |      141 |           0 |      19 |     6.66 |         3.5  |    3.34 |    2.23 |  3.46 | 0.28    |     0.33 |    0.11 |   0.6  | better   | noise                           |
| filter | reference | Grok stock LONG          | mom12-1 (aligned: -mom for shorts) : Q5 (highest 20%) vs rest  | Q5 vs rest |       28 |         113 |      19 |     3.76 |         4.62 |    2.44 |   -0.77 |  3.72 | 0.36    |     0.55 |    0.14 |   0.65 | better   | noise                           |
| filter | reference | Rule-filtered stock LONG | mom12-1 (aligned: -mom for shorts) : Q1 (lowest 20%) vs rest   | Q1 vs rest |       23 |          92 |      22 |     4.41 |        -1.86 |    0.89 |   -4.43 |  2.46 | 0.39    |     0.52 |    0.4  |   0.67 | better   | noise                           |
| filter | reference | All stock LONG           | mom12-1 (aligned: -mom for shorts) : Q5 (highest 20%) vs rest  | Q5 vs rest |       48 |         193 |      25 |     2.76 |         3.67 |    1.02 |   -1.42 |  2.76 | 0.42    |     0.3  |    0.09 |   0.69 | better   | noise                           |
| filter | reference | Crypto LONG              | mom12-1 (aligned: -mom for shorts) : rank slope (Q5-Q1 equiv.) | rank slope |      264 |           0 |      51 |    11.47 |        -1.15 |   -2.21 |   -7.55 | -0.84 | 0.53    |     0.52 |    0.46 |   0.75 | better   | noise                           |
| filter | reference | Crypto LONG              | mom12-1 (aligned: -mom for shorts) : Q1 (lowest 20%) vs rest   | Q1 vs rest |       53 |         211 |      51 |    -3.89 |        -0.65 |   -1.97 |    4.06 | -0.99 | 0.61    |     0.65 |    0.84 |   0.8  | worse    | noise                           |
| filter | reference | Perplexity stock LONG    | mom12-1 (aligned: -mom for shorts) : rank slope (Q5-Q1 equiv.) | rank slope |       59 |           0 |       7 |    -4.23 |         2.67 |   -1.59 |    3.54 | -0.25 | 0.65    |     0.94 |    0.45 |   0.82 | worse    | noise                           |
| filter | reference | All stock LONG           | mom12-1 (aligned: -mom for shorts) : Q1 (lowest 20%) vs rest   | Q1 vs rest |       49 |         192 |      25 |     1.41 |        -1.97 |   -0.76 |   -5.17 |  0.4  | 0.71    |     0.68 |    0.7  |   0.87 | better   | noise                           |
| filter | reference | Grok stock LONG          | mom12-1 (aligned: -mom for shorts) : Q1 (lowest 20%) vs rest   | Q1 vs rest |       29 |         112 |      19 |     1.31 |         1.16 |   -0.26 |   -3.61 |  0.44 | 0.73    |     0.5  |    0.68 |   0.88 | better   | noise                           |
| filter | reference | Rule-filtered stock LONG | mom12-1 (aligned: -mom for shorts) : rank slope (Q5-Q1 equiv.) | rank slope |      115 |           0 |      22 |    -2.38 |         4.58 |    1.52 |    4.24 |  0.3  | 0.74    |     0.75 |    0.78 |   0.88 | worse    | noise                           |
| filter | reference | All stock LONG           | mom12-1 (aligned: -mom for shorts) : rank slope (Q5-Q1 equiv.) | rank slope |      241 |           0 |      25 |     1.47 |         5.14 |    0.12 |   -0.82 |  2.44 | 0.8     |     0.69 |    0.66 |   0.92 | better   | noise                           |
| filter | reference | Rule-filtered stock LONG | mom12-1 (aligned: -mom for shorts) : Q5 (highest 20%) vs rest  | Q5 vs rest |       23 |          92 |      22 |     0.55 |         2.61 |   -1.64 |   -5.71 | -0.09 | 0.9     |     0.52 |    0.33 |   0.96 | better   | noise                           |

* Momentum 12-1 does not separate stock longs in this sample.
* Its only nominal effect is on shorts (Q5 +7.1 pp, q=0.15), which is the same "breaking down" factor.

## 8. Elliott filters (top 15 by p)

| kind   | family   | segment                  | feature                              | test            |   N_with |   N_without |   dates |   diff_x |   diff_med_x |   drop1 |   drop3 |    wd |    p |   p_incr |   p_mom |   q_BH | effect   | flag                            |
|:-------|:---------|:-------------------------|:-------------------------------------|:----------------|---------:|------------:|--------:|---------:|-------------:|--------:|--------:|------:|-----:|---------:|--------:|-------:|:---------|:--------------------------------|
| filter | ew_ewa   | All stock SHORT          | ElliottWaveAnalyzer: in wave 3       | with vs without |       38 |         151 |      22 |    -5.79 |        -1.6  |   -4.8  |   -2.77 | -4.07 | 0.01 |  0.02    |    0.05 |   0.19 | worse    | nominal p<0.05 only (fails FDR) |
| filter | ew_taew  | All stock SHORT          | python-taew: in wave 3               | with vs without |       67 |         122 |      22 |    -4.46 |        -3.85 |   -3.54 |   -1.95 | -2.36 | 0.02 |  0.00515 |    0.06 |   0.19 | worse    | nominal p<0.05 only (fails FDR) |
| filter | ew_ours  | Rule-filtered stock LONG | OUR count: any count                 | with vs without |       57 |          58 |      22 |    -7.03 |        -2.72 |   -5.51 |   -3.27 | -2.43 | 0.02 |  0.04    |    0.02 |   0.2  | worse    | nominal p<0.05 only (fails FDR) |
| filter | ew_taew  | Rule-filtered stock LONG | python-taew: in wave 5               | with vs without |       48 |          67 |      22 |    -5.83 |        -3.55 |   -4.49 |   -2.46 | -1.92 | 0.07 |  0.06    |    0.07 |   0.36 | worse    | noise                           |
| filter | ew_taew  | All stock SHORT          | python-taew: in wave 5               | with vs without |       60 |         129 |      22 |     3.58 |         4.24 |    2.92 |    2.17 |  2.94 | 0.09 |  0.55    |    0.18 |   0.39 | better   | noise                           |
| filter | ew_ours  | Crypto LONG              | OUR count: any count                 | with vs without |       96 |         168 |      51 |    -6.79 |        -1.35 |   -6.07 |   -1.73 | -4.61 | 0.13 |  0.16    |    0.03 |   0.46 | worse    | noise                           |
| filter | ew_ewa   | All stock SHORT          | ElliottWaveAnalyzer: any valid count | with vs without |       48 |         141 |      22 |    -3.12 |        -0.76 |   -2.23 |   -0.53 | -1.93 | 0.15 |  0.24    |    0.36 |   0.47 | worse    | noise                           |
| filter | ew_ar    | Grok stock LONG          | ElliottWaves: any valid count        | with vs without |       50 |          92 |      19 |     3.83 |         3.48 |    2.86 |    1.24 |  2.86 | 0.16 |  0.33    |    0.15 |   0.47 | better   | noise                           |
| filter | ew_taew  | Grok stock LONG          | python-taew: in wave 3               | with vs without |       58 |          84 |      19 |     3.49 |         0.52 |    2.65 |    1.09 |  2.52 | 0.19 |  0.33    |    0.26 |   0.52 | better   | noise                           |
| filter | ew_taew  | All stock LONG           | python-taew: in wave 3               | with vs without |      100 |         142 |      25 |     3.07 |        -0.19 |    2.13 |    0.76 |  2.18 | 0.24 |  0.18    |    0.25 |   0.56 | better   | noise                           |
| filter | ew_ewa   | All stock LONG           | ElliottWaveAnalyzer: in wave 3       | with vs without |       26 |         216 |      25 |     8.2  |         4.28 |    4.87 |   -1.41 |  2.78 | 0.24 |  0.14    |    0.15 |   0.56 | better   | noise                           |
| filter | ew_ours  | Perplexity stock LONG    | OUR count: any count                 | with vs without |       20 |          39 |       7 |    -5    |         0.84 |   -2.63 |    0.84 | -0.07 | 0.25 |  0.67    |    0.24 |   0.57 | worse    | noise                           |
| filter | ew_taew  | All stock LONG           | python-taew: in wave 5               | with vs without |       86 |         156 |      25 |    -2.62 |         0.06 |   -2.01 |   -1    | -0.61 | 0.25 |  0.18    |    0.24 |   0.57 | worse    | noise                           |
| filter | ew_ours  | All stock LONG           | OUR count: any count                 | with vs without |       83 |         159 |      25 |    -2.02 |         0.33 |   -1.42 |   -0.35 |  0.28 | 0.25 |  0.14    |    0.22 |   0.57 | worse    | noise                           |
| filter | ew_ewa   | Rule-filtered stock LONG | ElliottWaveAnalyzer: any valid count | with vs without |       27 |          88 |      22 |     6.08 |         2.81 |    2.76 |   -1    |  2.44 | 0.27 |  0.34    |    0.26 |   0.59 | better   | noise                           |

## 9. Agreement tables

### TA-Lib candles vs scanner_geometry (695 setups, pattern on the cutoff bar)

| pattern              | talib              |   N |   geo_n |   talib_n |   both |   agree_pct |   jaccard |   kappa |
|:---------------------|:-------------------|----:|--------:|----------:|-------:|------------:|----------:|--------:|
| hammer               | cdl_hammer         | 695 |      12 |        12 |      1 |        96.8 |      0.04 |    0.07 |
| inverted_hammer      | cdl_invertedhammer | 695 |      12 |        13 |      2 |        97   |      0.09 |    0.14 |
| bullish_engulfing    | cdl_engulfing      | 695 |      10 |        31 |     10 |        97   |      0.32 |    0.48 |
| bearish_engulfing    | cdl_engulfing      | 695 |       8 |        31 |      8 |        96.7 |      0.26 |    0.4  |
| bullish_harami       | cdl_harami         | 695 |       4 |        26 |      2 |        96.3 |      0.07 |    0.12 |
| bearish_harami       | cdl_harami         | 695 |       9 |        21 |      9 |        98.3 |      0.43 |    0.59 |
| piercing             | cdl_piercing       | 695 |       2 |         3 |      0 |        99.3 |      0    |   -0    |
| dark_cloud           | cdl_darkcloudcover | 695 |       2 |         0 |      0 |        99.7 |      0    |    0    |
| morning_star         | cdl_morningstar    | 695 |       5 |        13 |      0 |        97.4 |      0    |   -0.01 |
| evening_star         | cdl_eveningstar    | 695 |       4 |         3 |      2 |        99.6 |      0.4  |    0.57 |
| three_white_soldiers | cdl_3whitesoldiers | 695 |       5 |         0 |      0 |        99.3 |      0    |    0    |
| three_black_crows    | cdl_3blackcrows    | 695 |       2 |         0 |      0 |        99.7 |      0    |    0    |
| hanging_man          | cdl_hangingman     | 695 |      11 |        10 |      0 |        97   |      0    |   -0.02 |
| shooting_star        | cdl_shootingstar   | 695 |      11 |         7 |      0 |        97.4 |      0    |   -0.01 |
| doji                 | cdl_doji           | 695 |      62 |        99 |     60 |        94.1 |      0.59 |    0.71 |
| dragonfly_doji       | cdl_dragonflydoji  | 695 |       5 |        16 |      5 |        98.4 |      0.31 |    0.47 |
| gravestone_doji      | cdl_gravestonedoji | 695 |       5 |         7 |      3 |        99.1 |      0.33 |    0.5  |
| spinning_top         | cdl_spinningtop    | 695 |      80 |       136 |     75 |        90.5 |      0.53 |    0.64 |
| marubozu_bull        | cdl_marubozu       | 695 |      35 |        33 |     28 |        98.3 |      0.7  |    0.81 |
| marubozu_bear        | cdl_marubozu       | 695 |       8 |        15 |      7 |        98.7 |      0.44 |    0.6  |

* Agreement is good on simple single-candle shapes: marubozu, doji, spinning top.
* It is poor on context-dependent patterns (hammer, hanging man, shooting star, morning star, piercing). Each implementation defines the "trend" context differently.
* The candles add no edge either way: TA-Lib candles had 0 of 53 nominally significant comparisons, which matches the §3.14 candle result.

### smc vs scanner_geometry

| object                                  |   N |   smc_pct |   geo_pct |   agree_pct |   kappa |   n_both |   spearman_dist |   median_dist_smc_atr |   median_dist_geo_atr |
|:----------------------------------------|----:|----------:|----------:|------------:|--------:|---------:|----------------:|----------------------:|----------------------:|
| open FVG above price                    | 695 |      75.4 |      70.4 |        76.3 |    0.4  |      424 |            0.6  |                  1.71 |                  1.12 |
| open FVG below price                    | 695 |      67.9 |      77.6 |        84.3 |    0.61 |      451 |            0.58 |                  1.78 |                  1.1  |
| active order block above                | 695 |      73.4 |      43.5 |        68.3 |    0.4  |      296 |           -0.09 |                  5.56 |                  5.29 |
| active order block below                | 695 |      73.7 |      38.8 |        63.5 |    0.34 |      264 |            0.15 |                  4.92 |                  5.09 |
| liquidity (>=2 equal swing highs) above | 695 |      27.3 |      20.1 |        66   |    0.07 |       47 |           -0.27 |                  5.53 |                  1.68 |
| liquidity (>=2 equal swing lows) below  | 695 |      33.7 |      16.8 |        62.7 |    0.05 |       46 |            0.51 |                  6.4  |                  2.69 |

smc flags many more order blocks than the module (73% of setups vs 39–44%), and its liquidity pools hardly overlap.

### Elliott coverage (% of setups with each state)

| segment                  |   N |   taew_any% |   taew_w3% |   taew_w5% |   taew_done% |   ewa_any% |   ewa_w3% |   ewa_w5% |   ewa_done% |   ar_any% |   ar_abc_done% |   ar_impulse_seen% |   ours_any% |   ours_w3% |   ours_w5% |
|:-------------------------|----:|------------:|-----------:|-----------:|-------------:|-----------:|----------:|----------:|------------:|----------:|---------------:|-------------------:|------------:|-----------:|-----------:|
| All stock LONG           | 242 |        90.5 |       41.3 |       35.5 |         13.6 |       21.9 |      10.7 |       3.3 |         7.9 |      40.1 |           28.5 |               11.6 |        34.3 |       26.9 |        2.5 |
| Rule-filtered stock LONG | 115 |        93.9 |       46.1 |       41.7 |          6.1 |       23.5 |       8.7 |       4.3 |        10.4 |      50.4 |           33.9 |               16.5 |        49.6 |       38.3 |        2.6 |
| All stock SHORT          | 189 |        85.7 |       35.4 |       31.7 |         18.5 |       25.4 |      20.1 |       1.6 |         3.7 |      42.3 |           33.9 |                8.5 |        30.2 |       22.8 |        0.5 |
| Crypto LONG              | 264 |        96.6 |       56.4 |       33.7 |          6.4 |       67.4 |      46.6 |       3.8 |        17   |      52.7 |           48.9 |                3.8 |        36.4 |       30.7 |        1.1 |

### Elliott agreement with our count

| repo        | state                           |   repo_n |   ours_n |   both |   kappa |   pct_of_repo_also_ours |
|:------------|:--------------------------------|---------:|---------:|-------:|--------:|------------------------:|
| taew        | w3                              |      316 |      189 |     80 |   -0.04 |                    25.3 |
| taew        | w5                              |      235 |       10 |      4 |    0.01 |                     1.7 |
| taew        | same wave label when both count |      194 |          |     84 |         |                    43.3 |
| ewa         | w3                              |      187 |      189 |     54 |    0.02 |                    28.9 |
| ewa         | w5                              |       21 |       10 |      0 |   -0.02 |                     0   |
| ewa         | same wave label when both count |       62 |          |     54 |         |                    87.1 |
| taew vs ewa | w3                              |      316 |      187 |    101 |    0.1  |                         |
| taew vs ewa | w5                              |      235 |       21 |     10 |    0.02 |                         |

* There is essentially no agreement on "in wave 3" between the repos and our count (κ −0.04 to 0.02), or between the repos themselves (κ 0.10).
* Elliott counting is too subjective for these implementations to serve as a shared signal.

## 10. Licenses and code health (checked on GitHub/PyPI 2026-10-08)

* **TA-Lib/ta-lib-python:** BSD-2-Clause, about 12.3k stars, last pushed 2026-09-21. The C library is BSD. Healthy.
* **pandas-ta:** MIT (LICENSE in the installed wheel; © Kevin Johnson). github.com/twopirllc/pandas-ta returns 404. The package lives on PyPI (0.4.71b0) and at pandas-ta.dev. Its maintenance future is uncertain, so pin the version.
* **smart-money-concepts (joshyattridge):** MIT, about 2.1k stars, last pushed 2026-04. Version 0.0.27; alpha-quality API.
* **python-taew (DrEdwardPCB):** MIT, 26 stars, untouched since 2021, buggy.
* **ElliottWaveAnalyzer (drstevendev):** **no license**, 205 stars, last pushed 2024-06.
* **ElliottWaves (alessioricco):** MIT, 42 stars, last pushed 2024-01. Notebook-style code that downloads data and runs at import.
* **PyBacktesting (philippe-ostiguy):** MIT. Skipped because it is a full Elliott/Fibonacci backtest framework built around its own data pipeline, not a library.

## 11. Caveats

* **In-sample, short window:** about 3.5 months of setups, 22–25 stock entry dates and 51 crypto entry dates. Most stock trades are still open, so their outcomes are marked to market.
* **Low power for small effects:** N≥20 per side still means wide confidence intervals. Effects smaller than ~5 pp can't be detected.
* **Implementation choices:** the Elliott adapters are mine (window sizes, recency rules, picking the first valid configuration). A different setup could give different coverage, but the lack of agreement between repos suggests the conclusion would not change.
* **Expected robust results by chance:** across 859 comparisons, with FDR at q<0.10, roughly 10% of the 7 survivors could be false.

## 12. Files

* **Scripts:** `common.py`, `leak_ta.py`, `leak_ew.py`, `features_ta.py`, `features_smc.py`, `ew_libs.py`, `ew_features.py`, `sim_levels.py`, `analyze.py`, `agree.py`, `shorts_check.py`, `report_tables.py`, `report.py`.
* **Outputs in `out/`:**
  * `ta_repos_table.csv` is the full table of 859 comparisons.
  * `leak_*.csv` are the leak tests.
  * `ta_features.pkl`, `smc_features.pkl` and `ew_features.pkl` are the features.
  * `sim_levels_trades.csv` has the level-rule trades.
  * `agree_*.csv`, `ew_coverage.csv` and `ew_agreement.csv` are the agreement tables.
* **Repos:** `repos/`.
