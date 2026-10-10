# בדיקת FDR: גלי ווליום, דייברג'נסים ותמיכה/התנגדות (scanner_waves / scanner_levels), 08.10.2026

## סיכום בעברית
- **אין דליפה ואין צביעה מחדש.** בדקתי את כל 695 הסטאפים, לא מדגם. השוויתי היסטוריה מלאה מול היסטוריה חתוכה ומול נתוני זבל אחרי ה-cutoff, בכל ספי Weis (2/3/4/5%). יצאו 0 הבדלים מתוך 638,616 ערכים. גם ב-sr_columns, בנתיב האמיתי של המודול: 0 הבדלים. נקודות מפנה מאושרות וגלי Weis שהושלמו לא משתנים כשמוסיפים 5, 10 או 20 ברים. רק הגל האחרון, שנמצא בתהליך, ממשיך להתעדכן, וזה צפוי.
- **אף בדיקה לא שרדה FDR.** הרצתי 940 השוואות במשפחה אחת: 3 קטעים (מניות לונג, מניות שורט, קריפטו לונג) כפול 4 תוצאות (הטרייד בפוליסי הפעיל, ותשואה עודפת אחרי 5, 10 ו-20 יום). ל-63 מהן p<0.05, כשבמקרה צפויות כ-47. ה-q הנמוך ביותר הוא 0.32. ב-0 בדיקות q<0.10.
- **הרמז של Weis לא החזיק.** התשה של Weis קלאסי בכיוון הטרייד שחזרה את הממצא המקדים במניות במאוחד: ‎-0.6%‎ מול ‎+3.4%‎ ביום 20, N=30. בבדיקה לפי קטע, במניות לונג ביום 20 היא נתנה ‎-5.3‎ נק' אחוז (p=0.16), ובפוליסי הפעיל ‎-2.3‎ (p=0.31). בשורטים ובקריפטו אין לה סימן עקבי, וגם בספים 2, 4 ו-5% לא (הספים האלה מכוילים ונספרים במשפחה).
- **הכי קרוב לסף:** Connors RSI ב-Q5 בשורטים על מניות, ‎+6.0‎ נק' אחוז, p=0.0003, q=0.32. זה אותו ממצא שכבר עבר FDR במחקר הריפו של TA. גם הפעם הוא לא מוסיף מעבר לכללים הקיימים: אחרי שליטה בכלל השורט, VA120, SMA200 ומומנטום, p_incr=0.10.
- **wave_end_signal** נדלק על 87–92% מהסטאפים, ולכן אין לו כוח הבחנה. effort>result וקליימקס נדירים מדי, פחות מ-20 בכל צד, ולא נבדקו.
- **המלצה:** להשאיר את כל העמודות כעמודות לוג במשקל 0, ולמדוד קדימה מ-12.10. לא לחסום אף טרייד לפי אף אחת מהן. לא לכייל את סף ה-Weis (נשאר 3%). לא להשתמש ב-wave_end_signal המשולב, אלא ב-wave_end_n ובדגלים הבודדים. לא לחתוך יעדים לפי S/R.

## 1. Data and method
* **Setups:** the 695 testable main-sheet setups (stock LONG 242, stock SHORT 189, crypto LONG 264).
  * They come out of the 846 in_main rows after removing duplicates and setups with no active-policy trade.
  * Crypto shorts are frozen and excluded, the same universe as §3.14 and the TA-repos test.
* **PIT cutoff:** `setups_prepared.info_cutoff_utc`.
  * Stocks pre-session or intraday: the previous close. After the close: the alert-day candle.
  * Crypto: the alert minute.
  * The module's own `pit_cut` gave last bar = `rule_bar_actual` for all 695 setups.
* **History:** stocks use the 12-year Yahoo auto_adjust cache that scanner_levels itself fills (WBD falls back to frames.pkl). Crypto uses frames.pkl.
  * Waves are computed on the last 480 PIT bars, the scanner convention. 480 bars and the full history gave identical columns for 100% of setups.
  * S/R uses `levels_for(..., 'SWING', direction)` on the PIT-cut history. Stocks only.
* **View:** each setup is read in its own direction, so "with" means the trade's direction. Oscillators are aligned so that + = with the trade.
* **Outcomes**, all as excess vs SPY (stocks) or BTC (crypto):
  * The active-policy trade from `sim_ratchet_trades.csv`: stock longs `rt_ratchet_h618_c`, stock shorts `rt_ratchet_c`, crypto `rt_fixed3_c`.
  * Fixed horizons of 5, 10 and 20 bars: open of the entry bar to the close of the h-th bar.
  * 20-day coverage is thin: stock L 87, S 53, crypto 237.
* **Tests (same as §3.14):**
  * Booleans: flagged vs unflagged, with N≥20 on each side.
  * Continuous columns: Q1-vs-rest, Q5-vs-rest and a rank slope.
  * p is the max of the ticker-, entry-date- and two-way-clustered OLS p-values.
  * **New:** a 95% CI from a two-way (ticker × entry-date) Poisson pigeonhole bootstrap with 2000 reps.
  * p_incr controls for the rule pass (short rule for shorts), close beyond VA120 in the trade direction, the SMA200 side, and momentum 12-1.
  * rho_* is the Spearman correlation of the feature with momentum, the rule, VA120 and SMA200.
* **FDR:** one BH family over all 940 executed comparisons, q<0.10.
  * The family includes the Weis 2/4/5% sensitivity, labelled [TUNED].
  * ROBUST means q<0.10 and all of these keep the same sign: median, raw return, within-date, without the top-1 ticker, without the top-3 tickers. The bootstrap CI must also exclude 0.

## 2. Leak and repaint tests (all 695 setups)
| check | n | mismatches |
|---|---|---|
| waves: A full history vs B truncated (Weis 2/3/4/5%) | 695 setups | 0 |
| waves: C garbage future vs B | 695 setups | 0 |
| waves: D truncated, cutoff=None vs B | 695 setups | 0 |
| waves: value comparisons in total | 638,616 | 0 |
| waves: *_confirmed_at / *_end / *_date after the rule bar; wv_last_bar != rule bar | 695 | 0 |
| repaint +5 bars: confirmed zigzag pivots / completed Weis waves / completed zigzag swings changed | 675 setups | 0 / 0 / 0 |
| repaint +10 bars: confirmed zigzag pivots / completed Weis waves / completed zigzag swings changed | 564 setups | 0 / 0 / 0 |
| repaint +20 bars: confirmed zigzag pivots / completed Weis waves / completed zigzag swings changed | 382 setups | 0 / 0 / 0 |
| levels: sr_columns real path (own long_daily + pit_cut) A full / C garbage / D my cut vs B truncated | 431 stock setups, 36,111 values | 0 / 0 / 0 |
| levels: confirmed_at after the rule bar; sr_last_bar != rule bar | 431 | 0 |

* History-length dependence: the 480-bar window and the full 12-year history agree on 100% of setups for every logged flag and oscillator.
* The provisional (in-progress) Weis wave's extreme moves later in about 61% of cases. That is by design: it is not "completed", and no flag uses its end, only its realised volume so far.
* **No leak found.**

## 3. Results by family
Total comparisons: **940** (63 nominal p<0.05, about 47 expected by chance; q<0.10: **0**; minimum q = 0.316).

| family | n | nominal_p05 | minp | minq | expected_by_chance |
|---|---|---|---|---|---|
| div | 108 | 13 | 0.00243 | 0.455 | +5.40 |
| osc | 104 | 19 | 0.000336 | 0.316 | +5.20 |
| sr | 151 | 10 | 0.00995 | 0.549 | +7.60 |
| waves | 452 | 12 | 0.00182 | 0.455 | +22.60 |
| weis_tuned | 125 | 9 | 0.00639 | 0.549 | +6.20 |

| segment | outcome | n | nominal_p05 | minq |
|---|---|---|---|---|
| crypto LONG | 10d | 74 | 3 | 0.657 |
| crypto LONG | 20d | 70 | 3 | 0.455 |
| crypto LONG | 5d | 74 | 0 | 0.721 |
| crypto LONG | active policy | 74 | 17 | 0.549 |
| stock LONG | 10d | 94 | 2 | 0.549 |
| stock LONG | 20d | 53 | 3 | 0.455 |
| stock LONG | 5d | 96 | 1 | 0.649 |
| stock LONG | active policy | 98 | 6 | 0.549 |
| stock SHORT | 10d | 88 | 10 | 0.455 |
| stock SHORT | 20d | 28 | 1 | 0.664 |
| stock SHORT | 5d | 95 | 8 | 0.549 |
| stock SHORT | active policy | 96 | 9 | 0.316 |

## 4. Top 30 by p (none passes FDR)
| family | segment | outcome | feature | N_with | N_without | mean_with | mean_without | hit_with | hit_without | diff_x | ci_lo | ci_hi | diff_med_x | drop1 | drop3 | p | p_boot | q_BH | p_incr | rho_mom | rho_rule | rho_va120 | rho_sma200 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| osc | stock SHORT | active policy | Connors RSI 3/2/100 (aligned) : Q5 (highest 20%) vs rest | 38 | 151 | +5.51 | -0.48 | 74 | 37 | +5.99 | +0.13 | +10.86 | +8.81 | +5.63 | +5.07 | 0.000336 | 0.047 | 0.316 | 0.102 | +0.19 | +0.51 | +0.34 | +0.38 | nominal p<0.05 only (fails FDR) |
| waves | stock LONG | 20d | zigzag (Elliott pivots): current wave is in trade direction (wz_cur_dir) | 41 | 46 | -3.63 | +8.30 | 39 | 74 | -11.93 | -25.33 | -2.80 | -13.25 | -11.17 | -9.85 | 0.00182 | 0.0151 | 0.455 | 0.00167 | +0.20 | -0.01 | +0.38 | +0.32 | nominal p<0.05 only (fails FDR) |
| osc | stock SHORT | 10d | Connors RSI 3/2/100 (aligned) : Q5 (highest 20%) vs rest | 29 | 101 | +3.33 | -1.40 | 66 | 40 | +4.72 | -0.28 | +8.88 | +4.41 | +4.20 | +3.08 | 0.00193 | 0.06 | 0.455 | 0.274 | +0.31 | +0.55 | +0.38 | +0.41 | nominal p<0.05 only (fails FDR) |
| div | crypto LONG | 20d | cci20 divergence against trade, any age (last 2 pivots) | 63 | 174 | +0.05 | +5.72 | 81 | 75 | -5.67 | -12.78 | -0.02 | -3.29 | -5.80 | -4.32 | 0.00243 | 0.05 | 0.455 | 0.000903 | +0.01 |  | +0.10 | -0.09 | nominal p<0.05 only (fails FDR) |
| osc | stock SHORT | 10d | rsi14 (aligned: + = with trade) : Q5 (highest 20%) vs rest | 25 | 105 | +4.78 | -1.56 | 80 | 37 | +6.34 | +1.50 | +11.02 | +6.62 | +5.84 | +4.78 | 0.00272 | 0.014 | 0.455 | 0.112 | +0.30 | +0.60 | +0.68 | +0.47 | nominal p<0.05 only (fails FDR) |
| osc | stock SHORT | active policy | rsi14 (aligned: + = with trade) : Q5 (highest 20%) vs rest | 38 | 151 | +6.45 | -0.71 | 79 | 36 | +7.16 | +1.13 | +13.36 | +8.72 | +6.79 | +5.72 | 0.00291 | 0.024 | 0.455 | 0.543 | +0.26 | +0.68 | +0.70 | +0.57 | nominal p<0.05 only (fails FDR) |
| osc | stock SHORT | 10d | rsi14 (aligned: + = with trade) : rank slope (Q5-Q1 equiv.) | 130 | 0 | +4.21 | -1.49 | 74 | 38 | +7.17 | -0.88 | +13.87 | +6.91 | +2.27 | +1.74 | 0.00468 | 0.078 | 0.549 | 0.798 | +0.15 | +0.69 | +0.60 | +0.61 | nominal p<0.05 only (fails FDR) |
| div | crypto LONG | active policy | rsi14 fresh divergence WITH trade (<=20 bars) | 37 | 227 | +1.39 | +14.45 | 81 | 88 | -13.06 | -27.96 | -3.67 | -5.72 | -12.38 | -6.99 | 0.00637 | 0.011 | 0.549 | 0.00311 | -0.02 |  | +0.09 | +0.01 | nominal p<0.05 only (fails FDR) |
| weis_tuned | crypto LONG | active policy | [TUNED] Weis 5%: in-progress with vol > last against | 104 | 160 | +4.94 | +17.61 | 81 | 91 | -12.68 | -27.78 | -0.93 | -9.47 | -11.19 | -6.80 | 0.00639 | 0.034 | 0.549 | 0.00687 | +0.18 |  | +0.20 | +0.14 | nominal p<0.05 only (fails FDR) [TUNED] |
| osc | stock SHORT | 5d | rsi14 (aligned: + = with trade) : Q5 (highest 20%) vs rest | 33 | 146 | +2.35 | -0.59 | 82 | 38 | +2.94 | -0.23 | +6.11 | +3.53 | +2.60 | +2.05 | 0.00747 | 0.07 | 0.549 | 0.224 | +0.26 | +0.65 | +0.71 | +0.54 | nominal p<0.05 only (fails FDR) |
| div | crypto LONG | active policy | cci20 fresh divergence AGAINST trade (<=20 bars) | 61 | 203 | +2.09 | +15.78 | 89 | 87 | -13.69 | -29.36 | -2.02 | -7.30 | -13.07 | -8.45 | 0.00853 | 0.033 | 0.549 | 0.0105 | +0.03 |  | +0.09 | -0.07 | nominal p<0.05 only (fails FDR) |
| osc | crypto LONG | active policy | rsi14 (aligned: + = with trade) : rank slope (Q5-Q1 equiv.) | 264 | 0 | +4.74 | +23.24 | 72 | 98 | -23.40 | -51.48 | -2.37 | -26.68 | -11.81 | -6.44 | 0.00954 | 0.026 | 0.549 | 0.0594 | -0.05 |  | +0.54 | +0.47 | nominal p<0.05 only (fails FDR) |
| osc | crypto LONG | active policy | cci20 (aligned) : rank slope (Q5-Q1 equiv.) | 264 | 0 | +3.68 | +18.62 | 74 | 100 | -20.93 | -47.83 | -2.56 | -16.51 | -8.79 | -6.07 | 0.00973 | 0.025 | 0.549 | 0.0208 | -0.01 |  | +0.30 | +0.28 | nominal p<0.05 only (fails FDR) |
| sr | stock LONG | 10d | S/R: target-side level >= 3 touches | 122 | 41 | +2.68 | -1.09 | 57 | 51 | +3.77 | -0.94 | +8.37 | +2.45 | +3.24 | +2.54 | 0.00995 | 0.1 | 0.549 | 0.0014 | -0.26 | -0.14 | -0.03 | -0.36 | nominal p<0.05 only (fails FDR) |
| div | stock LONG | active policy | cci20 fresh HIDDEN divergence with trade (continuation) | 48 | 194 | -2.65 | +2.76 | 35 | 59 | -5.41 | -11.17 | +1.04 | -2.87 | -4.88 | -3.59 | 0.01 | 0.085 | 0.549 | 0.0136 | +0.08 | +0.09 | +0.26 | +0.13 | nominal p<0.05 only (fails FDR) |
| weis_tuned | crypto LONG | active policy | [TUNED] Weis 2%: against vol > last with | 127 | 137 | +19.25 | +6.47 | 95 | 80 | +12.78 | +2.23 | +29.00 | +7.48 | +9.98 | +6.72 | 0.0102 | 0.014 | 0.549 | 0.00696 | -0.07 |  | -0.20 | -0.15 | nominal p<0.05 only (fails FDR) [TUNED] |
| div | crypto LONG | active policy | any fresh divergence against (rsi14 or cci20) | 82 | 182 | +3.89 | +16.55 | 77 | 92 | -12.67 | -28.52 | -0.10 | -8.34 | -11.95 | -6.26 | 0.0105 | 0.05 | 0.549 | 0.0769 | +0.02 |  | +0.26 | +0.07 | nominal p<0.05 only (fails FDR) |
| div | stock SHORT | 10d | rsi14 divergence against trade, any age (last 2 pivots) | 30 | 100 | +2.40 | -1.16 | 60 | 41 | +3.56 | -0.43 | +8.06 | +2.42 | +3.02 | +1.86 | 0.0111 | 0.087 | 0.549 | 0.0254 | -0.01 | +0.19 | +0.01 | +0.06 | nominal p<0.05 only (fails FDR) |
| div | crypto LONG | 20d | cci20 fresh divergence AGAINST trade (<=20 bars) | 54 | 183 | +0.13 | +5.42 | 80 | 75 | -5.28 | -12.20 | +1.68 | -3.20 | -4.12 | -3.13 | 0.0113 | 0.118 | 0.549 | 0.00767 | -0.02 |  | +0.10 | -0.09 | nominal p<0.05 only (fails FDR) |
| osc | stock SHORT | active policy | rsi14 overbought with trade (>70 long / <30 short) | 20 | 169 | +7.08 | -0.02 | 80 | 40 | +7.10 | -0.33 | +14.98 | +6.72 | +6.44 | +4.44 | 0.0117 | 0.062 | 0.549 | 0.484 | +0.08 | +0.47 | +0.51 | +0.37 | nominal p<0.05 only (fails FDR) |
| div | crypto LONG | active policy | cci20 divergence against trade, any age (last 2 pivots) | 70 | 194 | +2.45 | +16.29 | 89 | 87 | -13.84 | -31.78 | -2.52 | -7.67 | -13.24 | -8.42 | 0.0126 | 0.024 | 0.563 | 0.0159 | +0.06 |  | +0.08 | -0.08 | nominal p<0.05 only (fails FDR) |
| osc | stock SHORT | active policy | rsi14 (aligned: + = with trade) : rank slope (Q5-Q1 equiv.) | 189 | 0 | +6.45 | -0.94 | 79 | 43 | +6.32 | -4.46 | +14.65 | +7.07 | +2.13 | +1.56 | 0.0136 | 0.17 | 0.563 | 0.362 | +0.16 | +0.72 | +0.60 | +0.66 | nominal p<0.05 only (fails FDR) |
| sr | stock LONG | active policy | S/R: stop-side level weekly/monthly | 117 | 120 | -0.91 | +4.56 | 42 | 69 | -5.48 | -13.09 | +1.26 | -3.87 | -4.87 | -3.46 | 0.0138 | 0.103 | 0.563 | 0.0202 | -0.13 | -0.11 | +0.06 | -0.02 | nominal p<0.05 only (fails FDR) |
| waves | stock SHORT | active policy | last-bar volume / 50-bar mean (wz_last_vol_x50) : rank slope (Q5-Q1 equiv.) | 189 | 0 | +4.79 | -1.83 | 68 | 34 | +7.40 | -1.90 | +17.40 | +8.69 | +3.08 | +2.03 | 0.0163 | 0.114 | 0.639 | 0.279 | +0.22 | +0.28 | +0.25 | +0.27 | nominal p<0.05 only (fails FDR) |
| osc | stock SHORT | 10d | cci20 (aligned) : rank slope (Q5-Q1 equiv.) | 130 | 0 | +2.52 | -1.18 | 56 | 38 | +5.63 | -2.18 | +12.03 | +4.10 | +1.61 | +1.06 | 0.0174 | 0.151 | 0.646 | 0.767 | +0.21 | +0.65 | +0.52 | +0.54 | nominal p<0.05 only (fails FDR) |
| sr | stock SHORT | 10d | S/R: nearest stop-side level distance (ATR) : Q5 (highest 20%) vs rest | 29 | 96 | +2.72 | -1.28 | 52 | 44 | +4.00 | -0.47 | +10.08 | +2.44 | +3.31 | +2.21 | 0.018 | 0.089 | 0.646 | 0.103 | +0.15 | +0.15 | +0.19 | +0.06 | nominal p<0.05 only (fails FDR) |
| weis_tuned | stock SHORT | 5d | [TUNED] Weis 4%: in-progress with vol > last against | 50 | 129 | +1.67 | -0.72 | 68 | 37 | +2.39 | -0.99 | +5.70 | +2.69 | +2.13 | +1.65 | 0.0186 | 0.152 | 0.646 | 0.4 | +0.16 | +0.58 | +0.57 | +0.51 | nominal p<0.05 only (fails FDR) [TUNED] |
| weis_tuned | stock SHORT | 5d | [TUNED] Weis 5%: in-progress with vol > last against | 45 | 134 | +1.88 | -0.70 | 73 | 37 | +2.58 | -1.80 | +5.99 | +2.91 | +2.30 | +1.75 | 0.0195 | 0.182 | 0.646 | 0.219 | +0.13 | +0.59 | +0.59 | +0.45 | nominal p<0.05 only (fails FDR) [TUNED] |
| div | crypto LONG | active policy | rsi14 fresh divergence AGAINST trade (<=20 bars) | 66 | 198 | +3.89 | +15.53 | 77 | 90 | -11.64 | -28.60 | +2.21 | -7.48 | -10.75 | -5.34 | 0.0203 | 0.092 | 0.646 | 0.0789 | -0.02 |  | +0.06 | -0.09 | nominal p<0.05 only (fails FDR) |
| osc | crypto LONG | active policy | rsi14 overbought with trade (>70 long / <30 short) | 28 | 236 | +2.18 | +13.86 | 89 | 87 | -11.68 | -28.19 | -3.23 | -3.77 | -9.29 | -7.42 | 0.0208 | 0.011 | 0.646 | 0.259 | -0.00 |  | +0.33 | +0.38 | nominal p<0.05 only (fails FDR) |

## 5. Focus flags
Rows that are missing were skipped because N<20 on a side.

| segment | outcome | feature | N_with | N_without | mean_with | mean_without | diff_x | ci_lo | ci_hi | p | q_BH |
|---|---|---|---|---|---|---|---|---|---|---|---|
| crypto LONG | 10d | Connors RSI 3/2/100 (aligned) : Q5 (highest 20%) vs rest | 53 | 211 | +1.10 | +1.90 | -0.79 | -5.59 | +4.67 | 0.612 | 0.976 |
| crypto LONG | 20d | Connors RSI 3/2/100 (aligned) : Q5 (highest 20%) vs rest | 50 | 187 | +1.45 | +4.95 | -3.50 | -11.81 | +4.62 | 0.187 | 0.871 |
| crypto LONG | 5d | Connors RSI 3/2/100 (aligned) : Q5 (highest 20%) vs rest | 53 | 211 | +1.31 | +0.59 | +0.72 | -2.54 | +3.96 | 0.422 | 0.959 |
| crypto LONG | active policy | Connors RSI 3/2/100 (aligned) : Q5 (highest 20%) vs rest | 53 | 211 | +6.27 | +14.21 | -7.94 | -25.26 | +2.82 | 0.111 | 0.745 |
| stock LONG | 10d | Connors RSI 3/2/100 (aligned) : Q5 (highest 20%) vs rest | 36 | 133 | +2.06 | +1.64 | +0.41 | -6.54 | +7.58 | 0.84 | 0.985 |
| stock LONG | 5d | Connors RSI 3/2/100 (aligned) : Q5 (highest 20%) vs rest | 43 | 188 | +0.26 | +0.46 | -0.20 | -6.31 | +5.80 | 0.913 | 0.989 |
| stock LONG | active policy | Connors RSI 3/2/100 (aligned) : Q5 (highest 20%) vs rest | 48 | 193 | +1.74 | +1.78 | -0.04 | -8.15 | +8.19 | 0.985 | 0.998 |
| stock SHORT | 10d | Connors RSI 3/2/100 (aligned) : Q5 (highest 20%) vs rest | 29 | 101 | +3.33 | -1.40 | +4.72 | -0.28 | +8.88 | 0.00193 | 0.455 |
| stock SHORT | 5d | Connors RSI 3/2/100 (aligned) : Q5 (highest 20%) vs rest | 35 | 144 | +1.02 | -0.31 | +1.33 | -2.92 | +6.54 | 0.373 | 0.943 |
| stock SHORT | active policy | Connors RSI 3/2/100 (aligned) : Q5 (highest 20%) vs rest | 38 | 151 | +5.51 | -0.48 | +5.99 | +0.13 | +10.86 | 0.000336 | 0.316 |
| stock LONG | 10d | S/R: strong level between entry and tp1 | 58 | 83 | +1.48 | +2.11 | -0.63 | -5.78 | +5.43 | 0.705 | 0.981 |
| stock LONG | 20d | S/R: strong level between entry and tp1 | 28 | 33 | +4.65 | +1.93 | +2.72 | -12.46 | +29.71 | 0.568 | 0.976 |
| stock LONG | 5d | S/R: strong level between entry and tp1 | 89 | 108 | -0.70 | +1.33 | -2.03 | -5.03 | +0.83 | 0.0231 | 0.649 |
| stock LONG | active policy | S/R: strong level between entry and tp1 | 89 | 113 | +1.80 | +1.08 | +0.72 | -5.29 | +9.34 | 0.718 | 0.981 |
| stock SHORT | 10d | S/R: strong level between entry and tp1 | 48 | 67 | -0.28 | -0.73 | +0.45 | -3.51 | +7.08 | 0.752 | 0.981 |
| stock SHORT | 5d | S/R: strong level between entry and tp1 | 69 | 91 | +1.11 | -1.04 | +2.15 | -0.98 | +5.93 | 0.0461 | 0.696 |
| stock SHORT | active policy | S/R: strong level between entry and tp1 | 70 | 95 | +1.50 | +0.13 | +1.36 | -3.95 | +7.82 | 0.453 | 0.963 |
| stock LONG | 10d | S/R: tracker stop placed beyond a strong level | 53 | 88 | +1.46 | +2.18 | -0.72 | -7.96 | +5.79 | 0.766 | 0.981 |
| stock LONG | 20d | S/R: tracker stop placed beyond a strong level | 25 | 36 | +7.04 | +0.51 | +6.53 | -16.85 | +21.42 | 0.129 | 0.778 |
| stock LONG | 5d | S/R: tracker stop placed beyond a strong level | 70 | 127 | +0.47 | +0.38 | +0.09 | -2.90 | +3.25 | 0.928 | 0.992 |
| stock LONG | active policy | S/R: tracker stop placed beyond a strong level | 72 | 130 | +1.35 | +1.52 | -0.16 | -7.77 | +7.49 | 0.943 | 0.997 |
| stock SHORT | 10d | S/R: tracker stop placed beyond a strong level | 47 | 64 | -0.83 | -0.35 | -0.48 | -6.03 | +4.42 | 0.764 | 0.981 |
| stock SHORT | 5d | S/R: tracker stop placed beyond a strong level | 63 | 93 | +0.25 | -0.26 | +0.51 | -3.02 | +4.13 | 0.625 | 0.976 |
| stock SHORT | active policy | S/R: tracker stop placed beyond a strong level | 64 | 97 | +0.64 | +0.70 | -0.06 | -6.55 | +5.90 | 0.977 | 0.998 |
| crypto LONG | 10d | Weis classic 3%: with-wave exhaustion (ww_exhaustion_with) | 76 | 188 | +1.84 | +1.69 | +0.14 | -7.29 | +3.91 | 0.91 | 0.988 |
| crypto LONG | 20d | Weis classic 3%: with-wave exhaustion (ww_exhaustion_with) | 66 | 171 | +4.68 | +4.03 | +0.65 | -12.29 | +9.84 | 0.801 | 0.981 |
| crypto LONG | 5d | Weis classic 3%: with-wave exhaustion (ww_exhaustion_with) | 76 | 188 | +1.12 | +0.57 | +0.55 | -3.01 | +3.28 | 0.409 | 0.948 |
| crypto LONG | active policy | Weis classic 3%: with-wave exhaustion (ww_exhaustion_with) | 76 | 188 | +9.01 | +14.08 | -5.07 | -23.12 | +14.48 | 0.404 | 0.948 |
| stock LONG | 10d | Weis classic 3%: with-wave exhaustion (ww_exhaustion_with) | 36 | 134 | +0.61 | +1.98 | -1.38 | -7.54 | +6.87 | 0.525 | 0.976 |
| stock LONG | 20d | Weis classic 3%: with-wave exhaustion (ww_exhaustion_with) | 20 | 67 | -1.40 | +3.90 | -5.31 | -15.90 | +6.92 | 0.158 | 0.83 |
| stock LONG | 5d | Weis classic 3%: with-wave exhaustion (ww_exhaustion_with) | 46 | 186 | +1.16 | +0.16 | +1.00 | -2.36 | +5.06 | 0.46 | 0.963 |
| stock LONG | active policy | Weis classic 3%: with-wave exhaustion (ww_exhaustion_with) | 49 | 193 | -0.16 | +2.15 | -2.30 | -9.68 | +5.25 | 0.314 | 0.922 |
| stock SHORT | 5d | Weis classic 3%: with-wave exhaustion (ww_exhaustion_with) | 26 | 153 | -0.08 | -0.05 | -0.03 | -5.94 | +6.07 | 0.987 | 0.998 |
| stock SHORT | active policy | Weis classic 3%: with-wave exhaustion (ww_exhaustion_with) | 29 | 160 | +1.77 | +0.54 | +1.23 | -7.83 | +9.21 | 0.65 | 0.976 |
| crypto LONG | 10d | any fresh divergence against (rsi14 or cci20) | 82 | 182 | +0.99 | +2.07 | -1.09 | -5.75 | +6.82 | 0.568 | 0.976 |
| crypto LONG | 20d | any fresh divergence against (rsi14 or cci20) | 64 | 173 | +1.13 | +5.35 | -4.22 | -12.16 | +7.02 | 0.154 | 0.825 |
| crypto LONG | 5d | any fresh divergence against (rsi14 or cci20) | 82 | 182 | +0.37 | +0.89 | -0.52 | -3.15 | +2.66 | 0.557 | 0.976 |
| crypto LONG | active policy | any fresh divergence against (rsi14 or cci20) | 82 | 182 | +3.89 | +16.55 | -12.67 | -28.52 | -0.10 | 0.0105 | 0.549 |
| stock LONG | 10d | any fresh divergence against (rsi14 or cci20) | 51 | 119 | +2.86 | +1.19 | +1.67 | -3.23 | +8.75 | 0.391 | 0.945 |
| stock LONG | 20d | any fresh divergence against (rsi14 or cci20) | 22 | 65 | +4.59 | +2.04 | +2.55 | -7.94 | +20.44 | 0.53 | 0.976 |
| stock LONG | 5d | any fresh divergence against (rsi14 or cci20) | 78 | 154 | +0.64 | +0.21 | +0.43 | -2.15 | +3.87 | 0.624 | 0.976 |
| stock LONG | active policy | any fresh divergence against (rsi14 or cci20) | 79 | 163 | +3.25 | +0.92 | +2.32 | -3.94 | +11.10 | 0.32 | 0.922 |
| stock SHORT | 10d | any fresh divergence against (rsi14 or cci20) | 37 | 93 | +1.36 | -1.02 | +2.38 | -1.64 | +6.79 | 0.128 | 0.778 |
| stock SHORT | 5d | any fresh divergence against (rsi14 or cci20) | 47 | 132 | -0.29 | +0.03 | -0.32 | -3.39 | +2.79 | 0.704 | 0.981 |
| stock SHORT | active policy | any fresh divergence against (rsi14 or cci20) | 50 | 139 | +1.83 | +0.33 | +1.49 | -4.99 | +7.51 | 0.453 | 0.963 |
| crypto LONG | 10d | wave_end_n >= 2 | 190 | 74 | +1.91 | +1.29 | +0.63 | -5.70 | +4.98 | 0.729 | 0.981 |
| crypto LONG | 20d | wave_end_n >= 2 | 174 | 63 | +5.14 | +1.64 | +3.51 | -3.89 | +11.95 | 0.131 | 0.78 |
| crypto LONG | 5d | wave_end_n >= 2 | 190 | 74 | +0.84 | +0.45 | +0.39 | -3.17 | +3.13 | 0.676 | 0.976 |
| crypto LONG | active policy | wave_end_n >= 2 | 190 | 74 | +13.68 | +9.89 | +3.80 | -5.52 | +18.78 | 0.278 | 0.886 |
| stock LONG | 10d | wave_end_n >= 2 | 117 | 53 | +1.49 | +2.15 | -0.67 | -7.27 | +5.47 | 0.729 | 0.981 |
| stock LONG | 20d | wave_end_n >= 2 | 61 | 26 | +2.67 | +2.71 | -0.03 | -13.86 | +15.10 | 0.994 | 0.999 |
| stock LONG | 5d | wave_end_n >= 2 | 163 | 69 | +0.41 | +0.23 | +0.18 | -3.92 | +4.04 | 0.893 | 0.988 |
| stock LONG | active policy | wave_end_n >= 2 | 166 | 76 | +2.14 | +0.68 | +1.46 | -6.19 | +9.46 | 0.531 | 0.976 |
| stock SHORT | 10d | wave_end_n >= 2 | 71 | 59 | -0.24 | -0.47 | +0.23 | -5.34 | +6.46 | 0.904 | 0.988 |
| stock SHORT | 20d | wave_end_n >= 2 | 33 | 20 | +2.72 | +1.66 | +1.06 | -19.46 | +13.96 | 0.789 | 0.981 |
| stock SHORT | 5d | wave_end_n >= 2 | 104 | 75 | -0.30 | +0.29 | -0.58 | -4.28 | +2.91 | 0.606 | 0.976 |
| stock SHORT | active policy | wave_end_n >= 2 | 110 | 79 | +1.09 | +0.23 | +0.86 | -6.12 | +6.87 | 0.664 | 0.976 |
| crypto LONG | 10d | wave_end_n >= 3 | 56 | 208 | +0.11 | +2.18 | -2.07 | -7.53 | +2.23 | 0.2 | 0.871 |
| crypto LONG | 20d | wave_end_n >= 3 | 43 | 194 | +0.99 | +4.93 | -3.93 | -12.16 | +2.15 | 0.111 | 0.745 |
| crypto LONG | 5d | wave_end_n >= 3 | 56 | 208 | +0.06 | +0.91 | -0.85 | -4.33 | +2.64 | 0.457 | 0.963 |
| crypto LONG | active policy | wave_end_n >= 3 | 56 | 208 | +3.80 | +15.00 | -11.20 | -29.56 | +2.60 | 0.0543 | 0.696 |
| stock LONG | 10d | wave_end_n >= 3 | 60 | 110 | +1.14 | +2.00 | -0.86 | -6.13 | +5.71 | 0.707 | 0.981 |
| stock LONG | 20d | wave_end_n >= 3 | 32 | 55 | +1.72 | +3.24 | -1.52 | -14.26 | +14.79 | 0.768 | 0.981 |
| stock LONG | 5d | wave_end_n >= 3 | 81 | 151 | +0.26 | +0.41 | -0.14 | -3.32 | +3.09 | 0.88 | 0.987 |
| stock LONG | active policy | wave_end_n >= 3 | 82 | 160 | +2.08 | +1.48 | +0.60 | -6.39 | +9.56 | 0.8 | 0.981 |
| stock SHORT | 10d | wave_end_n >= 3 | 32 | 98 | +0.85 | -0.73 | +1.59 | -3.70 | +6.50 | 0.361 | 0.943 |
| stock SHORT | 5d | wave_end_n >= 3 | 45 | 134 | -0.40 | +0.06 | -0.47 | -4.16 | +2.77 | 0.676 | 0.976 |
| stock SHORT | active policy | wave_end_n >= 3 | 51 | 138 | +2.82 | -0.05 | +2.87 | -3.72 | +9.48 | 0.208 | 0.873 |
| crypto LONG | 10d | wave_end_signal (OR of reasons) | 244 | 20 | +2.02 | -1.71 | +3.73 | -1.62 | +10.17 | 0.0315 | 0.657 |
| crypto LONG | 5d | wave_end_signal (OR of reasons) | 244 | 20 | +0.85 | -0.72 | +1.57 | -2.85 | +5.68 | 0.232 | 0.873 |
| crypto LONG | active policy | wave_end_signal (OR of reasons) | 244 | 20 | +12.98 | +8.26 | +4.72 | -9.57 | +21.80 | 0.373 | 0.943 |
| stock LONG | active policy | wave_end_signal (OR of reasons) | 220 | 22 | +1.62 | +2.33 | -0.71 | -12.25 | +12.57 | 0.86 | 0.985 |
| stock SHORT | 5d | wave_end_signal (OR of reasons) | 156 | 23 | +0.03 | -0.65 | +0.68 | -3.37 | +7.95 | 0.66 | 0.976 |
| stock SHORT | active policy | wave_end_signal (OR of reasons) | 164 | 25 | +0.85 | -0.08 | +0.93 | -6.04 | +11.56 | 0.741 | 0.981 |
| crypto LONG | 10d | zigzag (Elliott pivots): with-wave exhaustion (wz_exhaustion_with) | 37 | 227 | +0.76 | +1.90 | -1.14 | -5.74 | +4.04 | 0.387 | 0.945 |
| crypto LONG | 20d | zigzag (Elliott pivots): with-wave exhaustion (wz_exhaustion_with) | 27 | 210 | +4.63 | +4.16 | +0.48 | -15.09 | +20.18 | 0.948 | 0.997 |
| crypto LONG | 5d | zigzag (Elliott pivots): with-wave exhaustion (wz_exhaustion_with) | 37 | 227 | +0.37 | +0.79 | -0.42 | -2.78 | +1.63 | 0.528 | 0.976 |
| crypto LONG | active policy | zigzag (Elliott pivots): with-wave exhaustion (wz_exhaustion_with) | 37 | 227 | +12.07 | +12.71 | -0.64 | -23.69 | +45.84 | 0.963 | 0.998 |
| stock LONG | 10d | zigzag (Elliott pivots): with-wave exhaustion (wz_exhaustion_with) | 29 | 141 | -0.21 | +2.08 | -2.29 | -7.99 | +3.95 | 0.308 | 0.92 |
| stock LONG | 5d | zigzag (Elliott pivots): with-wave exhaustion (wz_exhaustion_with) | 38 | 194 | +0.42 | +0.34 | +0.07 | -3.00 | +3.68 | 0.941 | 0.997 |
| stock LONG | active policy | zigzag (Elliott pivots): with-wave exhaustion (wz_exhaustion_with) | 41 | 201 | +0.97 | +1.83 | -0.86 | -9.29 | +11.36 | 0.798 | 0.981 |

## 6. Weis reversal threshold sensitivity [TUNED]
Flagged-minus-unflagged excess (pp) for with-wave exhaustion at each threshold:

| segment | outcome | 2% | 3% | 4% | 5% |
|---|---|---|---|---|---|
| crypto LONG | 10d | +1.35 | +0.14 | -5.00 |  |
| crypto LONG | 20d | +2.43 | +0.65 |  |  |
| crypto LONG | 5d | +0.29 | +0.55 | -1.86 |  |
| crypto LONG | active policy | -1.00 | -5.07 | -4.43 |  |
| stock LONG | 10d | -0.15 | -1.38 | +0.10 | -1.67 |
| stock LONG | 20d |  | -5.31 |  |  |
| stock LONG | 5d | +1.20 | +1.00 | +1.15 | +0.59 |
| stock LONG | active policy | -1.45 | -2.30 | -0.68 | -2.18 |
| stock SHORT | 10d | +0.05 |  |  | -2.19 |
| stock SHORT | 5d | -0.35 | -0.03 | -1.34 | -2.22 |
| stock SHORT | active policy | -0.45 | +1.23 | +1.36 | +0.12 |

Best tuned rows (all in the FDR family):

| segment | outcome | feature | N_with | N_without | diff_x | ci_lo | ci_hi | p | q_BH |
|---|---|---|---|---|---|---|---|---|---|
| crypto LONG | active policy | [TUNED] Weis 5%: in-progress with vol > last against | 104 | 160 | -12.68 | -27.78 | -0.93 | 0.00639 | 0.549 |
| crypto LONG | active policy | [TUNED] Weis 2%: against vol > last with | 127 | 137 | +12.78 | +2.23 | +29.00 | 0.0102 | 0.549 |
| stock SHORT | 5d | [TUNED] Weis 4%: in-progress with vol > last against | 50 | 129 | +2.39 | -0.99 | +5.70 | 0.0186 | 0.646 |
| stock SHORT | 5d | [TUNED] Weis 5%: in-progress with vol > last against | 45 | 134 | +2.58 | -1.80 | +5.99 | 0.0195 | 0.646 |
| crypto LONG | 10d | [TUNED] Weis 4%: with-wave exhaustion | 24 | 240 | -5.00 | -14.52 | +2.57 | 0.0251 | 0.657 |

No threshold survives FDR, and the signs flip across thresholds and segments. **Keep 3% and don't tune.**

## 7. Replication of the preliminary hint (pooled stocks, descriptive, not in the family)
| outcome | N_with | mean_with | N_without | mean_without | diff_x | p |
|---|---|---|---|---|---|---|
| 20d | 30 | -0.62 | 110 | +3.41 | -4.02 | 0.186 |
| 10d | 55 | -0.07 | 245 | +1.01 | -1.08 | 0.604 |
| active policy | 78 | +0.56 | 353 | +1.42 | -0.86 | 0.647 |

* The pooled number reproduces the preliminary N=30 result in direction.
* Split by direction with clustered SEs and corrected for 940 comparisons, it is noise.

## 8. Does anything add beyond the existing rules?
* The closest result is Connors RSI Q5 on stock shorts. It re-expresses "already breaking down", the same factor the short rule, VA120-below and SMA200 already capture: p_incr=0.10, rho with the rule +0.51, with VA120 +0.34.
* The wave and divergence flags correlate only weakly with momentum (|rho| ≤ 0.34 everywhere).
* With the rule, VA120 and SMA200 the overlap is moderate: |rho| < 0.35 for 59%, 91% and 89% of rows, with a maximum of about 0.6. Several flags partly re-encode the trend state.
* Either way, they carry no FDR-significant return effect, so there is nothing incremental to claim.

## 9. Recommendation
* **All columns: weight 0 and logged only.** Measure them forward from 12.10 with the tool_stats module.
* **Block:** none.
* **Skip / do not use:**
  * the OR-combined `wave_end_signal`, which fires on 87–92%;
  * a tuned Weis threshold;
  * S/R target capping (see results.md).
* **Keep logging:**
  * `wave_end_n`, `ww_/wz_exhaustion_with`, `ww_/wz_counter_gt_with`;
  * fresh RSI/CCI divergences against/with the trade;
  * crsi;
  * the S/R distances.
* **Too rare to test yet:** `*_effort_result`, the climax flags and `wv_elliott_context` (N<20). Revisit them once forward data accumulates.

## 10. Files (`/workspace/sr-waves-eval/fdr/`)
* `common_fdr.py`, `features.py` (PIT features to `features.pkl`), `leak.py` (to `leak_waves_levels.csv`, `leak_mismatches.csv`), `analyze_fdr.py` (to `../fdr_results.csv`, a copy of `fdr_results.csv`), `report.py`.
* `analysis_base.pkl` / `outcomes.pkl` hold the merged data.
* The modules `/workspace/scanner_waves.py` and `/workspace/scanner_levels.py` were used read-only, with no changes.
