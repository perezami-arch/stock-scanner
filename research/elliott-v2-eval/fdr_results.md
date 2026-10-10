# בדיקת FDR: אליוט גרסה 2 (scanner_elliott_v2), 08.10.2026

## סיכום בעברית
- **אין דליפה ואין צביעה מחדש.** בדקתי את כל 695 הסטאפים, לא מדגם, בשתי הדרכים: היסטוריה מלאה עם cutoff (כמו הסריקה החיה) וחלון של 480 ברים (כמו הלוקאפ). השוויתי היסטוריה מלאה מול היסטוריה חתוכה ומול נתוני זבל אחרי ה-cutoff. יצאו 0 הבדלים מתוך 288,425 ערכים, בכל העמודות של שתי התצוגות (לונג ושורט). נקודות מפנה מאושרות לא משתנות כשמוסיפים 5, 10 או 20 ברים (0/675, 0/564, 0/382), וגם הספירות שנבנות רק מהן לא משתנות. הפיבוט הזמני אף פעם לא מופיע בתוך הפיבוטים המאושרים (0/695). מה שכן זז, כצפוי, הוא הספירה הזמנית עצמה: בתוספת של 20 ברים המצב זז ב-65% מהמקרים והתווית ב-86%.
- **אף בדיקה לא שרדה FDR.** הרצתי 317 השוואות במשפחה של אליוט v2 לבד: 3 קטעים כפול 4 תוצאות. ל-33 מהן p<0.05, כשבמקרה צפויות כ-16. ה-q הנמוך ביותר הוא 0.44. ב-0 בדיקות q<0.10.
- **אותה תשובה במשפחה המשותפת.** שוק ההון ביקש את העמודות בתוך כל המשפחה, אז איחדתי את 317 הבדיקות עם 940 הבדיקות של הגלים והתמיכה/התנגדות: 1,257 השוואות. גם שם 0 עוברות q<0.10, וה-q הנמוך ביותר עולה מ-0.32 (במשפחת הגלים לבד) ל-0.42.
- **שלושת הרמזים הלא-מתוקנים לא החזיקו.** הם נכנסו מראש למשפחה, לא נבחרו אחרי התוצאות:
  - **מעבר ליעד (beyond target):** במניות במאוחד, ב-46 הסטאפים, שיעור העצירה בסטופ 8.7% מול 17.9%, p=0.091, אבל בלי שום הבדל בתשואה. ב-FDR יש לו רק 4 בדיקות עם N>=20, וה-p הכי טוב הוא 0.25. ה-q במשפחת v2 הוא 0.70, ובמשפחה המשותפת 0.82.
  - **abc_confirmed:** בקריפטו לונג, יום 20, ‎+9.0‎ נק' אחוז, p=0.025, אבל בלי הטיקר המוביל הסימן מתהפך (drop-top-3 = ‎-0.3‎), אז הוא לא יציב. ה-q שלו 0.44 במשפחת v2 ו-0.61 במשותפת. במניות אין לו סימן בכלל (p=0.87).
  - **wave_start_signal עם לפחות 2 משפחות:** במניות במאוחד, יום 20, ‎+0.3%‎ מול ‎+3.9%‎, p=0.15. ב-FDR ה-p הכי טוב הוא 0.23. ה-q שלו 0.69 במשפחת v2 ו-0.82 במשותפת.
- **גם בתיקון רק על 3 הרמזים לבד:** 25 בדיקות, וה-q הנמוך ביותר הוא 0.50. כלומר הם לא עוברים גם כמשפחה קטנה משלהם.
- **הכי קרוב לסף:** מצב abc_provisional בשורטים על מניות, בפוליסי הפעיל, ‎-7.9‎ נק' אחוז (N=23 מול 166, p=0.0056, q=0.44). זה היחיד שעבר גם את בדיקות היציבות וגם את הערך המוסף מעבר לכללים (p_incr=0.029). הוא לא שורד את התיקון, והוא נדיר: 23 מתוך 189 שורטים.
- **מה הוצאתי מהמשפחה כי הוא טאוטולוגי:** הפיבוט הזמני קיים ב-695 מתוך 695 סטאפים, והסוג שלו זהה לחלוטין לעמודת wz_cur_dir שכבר נבדקה (380 "עם הכיוון", 315 "נגד"). ev2_provisional רק אומר שהספירה נגמרת עליו. ev2_long_state ו-ev2_short_state חופפים ל-ev2_state בתצוגת הכיוון, אז נשארה רק תצוגת הכיוון הנגדי.
- **המלצה:** להשאיר את כל עמודות ev2_ כעמודות לוג במשקל 0, ולמדוד קדימה מ-12.10. לא לחסום אף טרייד לפי אף אחת מהן, ולא להשתמש במעבר ליעד, ב-abc_confirmed או ב-wave_start_signal כתנאי כניסה.

## 1. Data and method
* **Setups:** the 695 testable main-sheet setups (stock LONG 242, stock SHORT 189, crypto LONG 264), the same universe as `sr-waves-eval/fdr` and §3.14. Crypto shorts are frozen and excluded.
* **PIT cutoff:** `setups_prepared.info_cutoff_utc`, cut with `scanner_geometry.pit_cut`. Last bar = `rule_bar_actual` for all 695 setups. Stocks use the 12-year Yahoo auto_adjust cache (WBD falls back to frames.pkl); crypto uses frames.pkl.
* **Window:** the last 480 PIT bars, the scanner convention. The 480-bar window and the full history agree on state, label, beyond-target, ABC type, the stale-v1 flag and the tentative price for 100% of setups, and on the re-anchored flag for 98%.
* **View:** the trade-direction view (`ev2_*`). The opposite view is tested separately. Oscillators and distances are aligned so that + = with the trade.
* **Outcomes**, identical to `sr-waves-eval/fdr/analyze_fdr.py` (its outcome code is exec'd verbatim):
  * the active-policy trade from `sim_ratchet_trades.csv`: stock longs `rt_ratchet_h618_c`, stock shorts `rt_ratchet_c`, crypto `rt_fixed3_c`;
  * fixed horizons of 5, 10 and 20 bars, open of the entry bar to the close of the h-th bar;
  * all as directional excess: direction × (return − SPY for stocks, − BTC for crypto). 20-day coverage is thin: stock L 87, S 53, crypto 237.
* **Tests (same as §3.14):**
  * booleans: flagged vs unflagged, N≥20 on each side;
  * continuous columns: Q1-vs-rest, Q5-vs-rest and a rank slope;
  * p = the max of the ticker-, entry-date- and two-way-clustered OLS p-values;
  * a 95% CI from a two-way (ticker × entry-date) Poisson pigeonhole bootstrap, 2000 reps, and a second CI from the widest of the ticker / date / two-way clustered SEs (the tool_stats convention);
  * p_incr controls for the rule pass (short rule for shorts), close beyond VA120 in the trade direction, the SMA200 side, and momentum 12-1;
  * drop-top-1 and drop-top-3 ticker diffs, median diff, within-date diff.
* **FDR:** BH, q<0.10, reported twice.
  * **Family 1, Elliott v2 alone:** the 317 executed comparisons, the 3 pre-specified hints included. q column `q_ev2`.
  * **Family 2, combined:** those 317 plus the 940 waves/SR comparisons already in `sr-waves-eval/fdr_results.csv` (1,257 in total). q column `q_combined`. The old 940 keep their p-values and are re-queried only.
  * ROBUST means q<0.10 and all of these keep the same sign: median, raw return, within-date, without the top-1 ticker, without the top-3 tickers. Both CIs must also exclude 0.
* **The 3 hints were pre-specified** (שוק ההון's unadjusted results.txt: beyond-target, abc_confirmed, wave_start_signal ≥ 2 families, unadjusted p=0.028) and are marked `[HINT]`. They are inside both families, not a separate one. A hints-only q is reported as a sensitivity, not as the decision.

## 2. Leak and repaint tests (all 695 setups)
| check | n | mismatches |
|---|---|---|
| A full history + cutoff vs B truncated at the rule bar | 695 setups | 0 |
| C garbage future (+30 extreme bars) + cutoff vs B | 695 setups | 0 |
| D truncated, cutoff=None vs B | 695 setups | 0 |
| 480-bar window: real future + cutoff vs the window | 695 setups | 0 |
| 480-bar window: garbage future + cutoff vs the window | 695 setups | 0 |
| value comparisons in total (both views, all columns) | 288,425 | 0 |
| pivot dates, confirm dates and the tentative date after the rule bar; ev2_last_bar != rule bar | 695 | 0 |
| tentative pivot found among the confirmed zigzag pivots | 695 | 0 |
| repaint +5 bars: confirmed pivots changed / confirmed-only counts changed | 675 setups | 0 / 0 |
| repaint +10 bars: confirmed pivots changed / confirmed-only counts changed | 564 setups | 0 / 0 |
| repaint +20 bars: confirmed pivots changed / confirmed-only counts changed | 382 setups | 0 / 0 |

* The tentative pivot is present on **695/695** setups. That is what makes "tentative present" and "W2 in progress" near-tautological: a count ending on it is labelled "in progress" by construction.
* Informational, and expected: after +5 / +10 / +20 bars the state changes in 37% / 52% / 65% of setups and the label in 50% / 70% / 86%. The tentative extreme is later confirmed at the same bar in 32% / 37% / 43%. None of that feeds back into the cutoff reading.
* **No leak found.** `scanner_elliott_v2.py` was used read-only.

## 3. What was excluded from the family, and why
| column | reason |
|---|---|
| ev2_tentative_kind / "tentative pivot present" | present on 695/695; its kind is identical to `wz_cur_dir` (380 with / 315 against), which the waves family already tested |
| ev2_provisional | true exactly when the primary count ends on the tentative pivot, so it restates the label |
| "W2 in progress" (and W4/W5 in progress) | near-tautological given a tentative pivot on every setup; W4/W5 in progress also have N<20 |
| ev2_long_state, ev2_short_state, ev2_long_label, ev2_short_label | the trade-direction one is identical to ev2_state / ev2_label; only the opposite view is tested |
| ev2_target, ev2_fib_origin, ev2_fib_end, ev2_fib_r618, ev2_fib_x1618, ev2_tentative_price | raw price levels; the distances derived from them are tested instead |
| ev2_label, ev2_target_name, ev2_pivots, ev2_last_confirmed, ev2_last_bar, ev2_tentative_date | free text / dates |
| impulse_provisional (aggregate) | dominated by "W2 in progress" (54% / 38% / 50% of it in crypto L / stock L / stock S); "W3 in progress" is tested on its own |

Kept, and pre-specified: beyond-target (55 setups, 46 of them stocks), state = abc_confirmed, wave_start_signal ≥ 2 families. Also kept as real new content: the ABC states and types, the beyond-target split by impulse vs ABC, the stale / re-anchored Fib leg, the opposite view, and the current ≥2-families wave_end signal.

Coverage of the trade-direction view:

| state | crypto LONG | stock LONG | stock SHORT |
|---|---|---|---|
| impulse_provisional | 126 | 85 | 74 |
| abc_provisional | 67 | 46 | 23 |
| none | 33 | 64 | 50 |
| abc_confirmed | 36 | 36 | 30 |
| impulse_confirmed | 2 | 11 | 12 |

## 4. Results
Elliott-v2 family: **317** comparisons (33 nominal p<0.05, about 16 expected by chance; q<0.10: **0**; minimum q = 0.438).
Combined with the 940 waves/SR tests: **1,257** comparisons; q<0.10: **0**; minimum q = 0.423 (was 0.316 inside the waves family alone).

| family | n | nominal_p05 | minp | minq |
|---|---|---|---|---|
| ev2 | 281 | 33 | 0.0034 | 0.438 |
| waves_v2 (≥2 families) | 36 | 0 | 0.159 | 0.639 |

| segment | outcome | n | nominal_p05 | minq |
|---|---|---|---|---|
| crypto LONG | 10d | 31 | 5 | 0.438 |
| crypto LONG | 20d | 30 | 6 | 0.438 |
| crypto LONG | 5d | 31 | 0 | 0.639 |
| crypto LONG | active policy | 31 | 2 | 0.438 |
| stock LONG | 10d | 27 | 0 | 0.438 |
| stock LONG | 20d | 17 | 1 | 0.438 |
| stock LONG | 5d | 29 | 1 | 0.438 |
| stock LONG | active policy | 30 | 1 | 0.438 |
| stock SHORT | 10d | 23 | 7 | 0.438 |
| stock SHORT | 20d | 12 | 0 | 0.459 |
| stock SHORT | 5d | 28 | 5 | 0.438 |
| stock SHORT | active policy | 28 | 5 | 0.438 |

## 5. The three pre-specified hints
Replication in the original framing (pooled, descriptive, **not** a separate family), p = max of the clustered p-values:

| scope | hint | metric | N_with | N_without | mean_with | mean_without | diff | p |
|---|---|---|---|---|---|---|---|---|
| stocks pooled | beyond target | x_h20 | 9 | 131 | +1.9% | +2.6% | -0.7 | 0.841 |
| stocks pooled | beyond target | x_pol | 46 | 385 | +1.2% | +1.3% | -0.1 | 0.952 |
| stocks pooled | beyond target | stopped | 46 | 385 | +8.7% | +17.9% | -9.2 | 0.091 |
| stocks pooled | state = abc_confirmed | x_h20 | 14 | 126 | +2.1% | +2.6% | -0.5 | 0.869 |
| stocks pooled | state = abc_confirmed | x_pol | 66 | 365 | +1.6% | +1.2% | +0.4 | 0.869 |
| stocks pooled | state = abc_confirmed | stopped | 66 | 365 | +7.6% | +18.6% | -11.1 | 0.075 |
| stocks pooled | wave_start_signal (>=2 families) | x_h20 | 54 | 86 | +0.3% | +3.9% | -3.6 | 0.155 |
| stocks pooled | wave_start_signal (>=2 families) | x_pol | 206 | 225 | +0.8% | +1.7% | -0.9 | 0.608 |
| stocks pooled | wave_start_signal (>=2 families) | stopped | 206 | 225 | +16.5% | +17.3% | -0.8 | 0.855 |
| crypto LONG | beyond target | x_h20 | 9 | 228 | +8.9% | +4.0% | +4.9 | 0.447 |
| crypto LONG | beyond target | x_pol | 9 | 255 | +9.9% | +12.7% | -2.8 | 0.697 |
| crypto LONG | beyond target | stopped | 9 | 255 | +0.0% | +5.9% | -5.9 | 0.070 |
| crypto LONG | state = abc_confirmed | x_h20 | 26 | 211 | +12.2% | +3.2% | +9.0 | 0.025 |
| crypto LONG | state = abc_confirmed | x_pol | 36 | 228 | +17.7% | +11.8% | +5.9 | 0.169 |
| crypto LONG | state = abc_confirmed | stopped | 36 | 228 | +2.8% | +6.1% | -3.4 | 0.444 |
| crypto LONG | wave_start_signal (>=2 families) | x_h20 | 136 | 101 | +2.9% | +6.0% | -3.1 | 0.303 |
| crypto LONG | wave_start_signal (>=2 families) | x_pol | 148 | 116 | +10.2% | +15.7% | -5.5 | 0.323 |
| crypto LONG | wave_start_signal (>=2 families) | stopped | 148 | 116 | +4.1% | +7.8% | -3.7 | 0.204 |

* The beyond-target stop-rate hint reproduces in direction (8.7% vs 17.9% stopped, p=0.091) but is not significant once ticker and date clustering are both required, and it has no return effect at all (+1.2% vs +1.3% on the active-policy trade).
* abc_confirmed shows nothing in stocks. Its only nominal result is crypto longs at day 20.
* wave_start_signal ≥ 2 families reproduces the unadjusted sign on pooled stocks at day 20 (+0.3% vs +3.9%) but at p=0.15, not 0.028. The earlier p came from a day-only clustered bootstrap on a different stock-only set (439 tracker setups, 139 with a day-20 result).

Inside the FDR families (best row per hint):

| hint | best segment | outcome | N_with | N_without | diff (pp) | p | q in the v2 family | q combined | q if only the 3 hints | p_incr | drop-top-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| beyond target | stock LONG | 5d | 20 | 212 | -1.46 | 0.249 | 0.70 | 0.82 | 0.73 | 0.32 | +0.29 |
| state = abc_confirmed | crypto LONG | 20d | 26 | 211 | +8.97 | 0.025 | 0.44 | 0.61 | 0.50 | 0.011 | -0.26 |
| wave_start_signal ≥ 2 families | stock SHORT | 20d | 22 | 31 | -4.00 | 0.232 | 0.69 | 0.82 | 0.73 | 0.13 | -0.34 |

* None of the 25 hint rows has q<0.10 in any of the three corrections. The abc_confirmed crypto result also fails robustness: removing the top 3 tickers flips its sign.
* Beyond-target is testable (N≥20 both sides) in only 4 of 12 segment × outcome cells. Splitting it into impulse-beyond-target and ABC-beyond-target drops every cell below 20, so those two rows were skipped.

## 6. Top 20 by p (none passes FDR)
| segment | outcome | feature | N_with | N_without | diff (pp) | ci_lo | ci_hi | wide ci | drop-top-3 | p | q_ev2 | q_combined | p_incr |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| stock SHORT | 10d | number of valid counts (ev2_n_candidates) : Q1 (lowest 20%) vs rest | 28 | 102 | +5.03 | -0.18 | +10.32 | +1.50..+8.55 | +3.29 | 0.0034 | 0.44 | 0.60 | 5.68e-04 |
| stock SHORT | 5d | retracement depth of the (re-anchored) Fib leg : Q1 (lowest 20%) vs rest | 29 | 126 | +4.01 | +0.52 | +9.35 | +1.34..+6.67 | +2.61 | 0.0052 | 0.44 | 0.60 | 0.1041 |
| stock SHORT | 10d | retracement depth of the (re-anchored) Fib leg : rank slope (Q5-Q1 equiv.) | 119 | 0 | -7.38 | -14.92 | +1.33 | -12.80..-1.96 | -1.33 | 0.0052 | 0.44 | 0.60 | 0.7594 |
| stock SHORT | active policy | state = abc_provisional | 23 | 166 | -7.86 | -17.51 | -1.02 | -13.64..-2.08 | -4.37 | 0.0056 | 0.44 | 0.60 | 0.0294 |
| stock SHORT | 10d | retracement depth of the (re-anchored) Fib leg : Q1 (lowest 20%) vs rest | 23 | 96 | +5.23 | +0.03 | +10.66 | +1.30..+9.15 | +3.56 | 0.0123 | 0.44 | 0.60 | 0.2837 |
| crypto LONG | 20d | ABC type zigzag | 77 | 160 | +5.97 | -1.37 | +15.41 | +1.40..+10.55 | +2.57 | 0.0133 | 0.44 | 0.60 | 0.0168 |
| crypto LONG | active policy | retracement depth of the (re-anchored) Fib leg : rank slope (Q5-Q1 equiv.) | 246 | 0 | +23.76 | -5.21 | +53.86 | +5.25..+42.27 | +6.86 | 0.0149 | 0.44 | 0.61 | 0.0574 |
| stock SHORT | active policy | retracement depth of the (re-anchored) Fib leg : rank slope (Q5-Q1 equiv.) | 165 | 0 | -7.25 | -16.35 | +4.63 | -13.14..-1.37 | -1.18 | 0.0163 | 0.44 | 0.61 | 0.4704 |
| stock SHORT | 5d | state = abc_provisional | 22 | 157 | -2.67 | -7.74 | -0.20 | -4.83..-0.51 | -2.56 | 0.0177 | 0.44 | 0.61 | 0.0880 |
| stock SHORT | active policy | number of valid counts (ev2_n_candidates) : Q1 (lowest 20%) vs rest | 38 | 151 | +6.18 | -1.82 | +15.72 | +1.17..+11.19 | +3.71 | 0.0181 | 0.44 | 0.61 | 0.0130 |
| crypto LONG | 10d | Fib leg re-anchored | 81 | 183 | +3.04 | -2.85 | +9.50 | +0.43..+5.65 | +0.18 | 0.0224 | 0.44 | 0.61 | 0.0120 |
| stock SHORT | 10d | tentative pivot: close back from it (ATR) : rank slope (Q5-Q1 equiv.) | 130 | 0 | -6.98 | -18.73 | +0.80 | -13.37..-0.58 | -1.74 | 0.0234 | 0.44 | 0.61 | 0.0124 |
| crypto LONG | 20d | [HINT] state = abc_confirmed | 26 | 211 | +8.97 | -8.25 | +44.60 | +1.21..+16.72 | -0.26 | 0.0247 | 0.44 | 0.61 | 0.0110 |
| crypto LONG | 20d | Fib leg re-anchored | 64 | 173 | +7.23 | -4.82 | +19.17 | +0.94..+13.52 | -0.99 | 0.0267 | 0.44 | 0.61 | 0.0141 |
| stock SHORT | 5d | tentative pivot: close back from it (ATR) : rank slope (Q5-Q1 equiv.) | 179 | 0 | -3.75 | -9.57 | +1.32 | -7.25..-0.26 | -0.64 | 0.0273 | 0.44 | 0.61 | 0.0274 |
| stock LONG | 5d | retracement depth of the (re-anchored) Fib leg : Q1 (lowest 20%) vs rest | 41 | 176 | +2.89 | -0.47 | +8.10 | +0.34..+5.43 | +1.80 | 0.0279 | 0.44 | 0.61 | 0.1022 |
| stock LONG | 20d | retracement depth of the (re-anchored) Fib leg : rank slope (Q5-Q1 equiv.) | 82 | 0 | +14.02 | -7.17 | +39.94 | +0.32..+27.72 | +5.42 | 0.0295 | 0.44 | 0.61 | 0.0988 |
| stock SHORT | active policy | retracement depth of the (re-anchored) Fib leg : Q5 (highest 20%) vs rest | 33 | 132 | -5.64 | -13.42 | +1.48 | -11.00..-0.29 | -2.08 | 0.0311 | 0.44 | 0.61 | 0.4302 |
| crypto LONG | 20d | distance to count target, trade-aligned (ATR) : Q5 (highest 20%) vs rest | 22 | 76 | -7.39 | -19.10 | -0.14 | -14.06..-0.72 | -2.47 | 0.0323 | 0.44 | 0.61 | 0.0538 |
| stock SHORT | 5d | retracement depth of the (re-anchored) Fib leg : rank slope (Q5-Q1 equiv.) | 155 | 0 | -3.80 | -9.72 | +1.82 | -7.44..-0.15 | -0.23 | 0.0345 | 0.44 | 0.61 | 0.4272 |

Six of the 33 nominal rows pass the robustness checks. The only one that also adds value beyond the existing rules is `state = abc_provisional` on stock shorts: -7.9 pp on the active-policy trade (p=0.0056, p_incr=0.029, q=0.44) and -2.7 pp at 5 days (p=0.018, p_incr=0.088). It is the closest thing in this run, and it still does not survive FDR. It is also scarce: 23 of 189 stock shorts.

## 7. Does anything add beyond the existing rules?
* Of the 33 nominal rows (p<0.05), 20 have p_incr≥0.05, so they restate the short rule, VA120, SMA200 or momentum.
* 13 keep p_incr<0.05, but only one of them also passes the robustness checks: abc_provisional on stock shorts (§6). The other 12 fail at least one check. Usually the bootstrap CI crosses 0 (n_candidates Q1 on stock shorts, p_incr=0.0006, q=0.44), or removing the top tickers flips the sign (abc_confirmed crypto 20d, Fib re-anchored crypto 20d).
* The Fib retracement-depth rows mostly re-encode the trend state (median p_incr 0.10, up to 0.76).

## 8. Recommendation
* **All ev2_ columns: weight 0, logged only.** tool_stats now picks them up automatically for the forward measurement from 12.10.
* **Block:** none. Not on beyond-target, not on abc_confirmed, not on wave_start_signal.
* **Do not** treat "W2 in progress" or "tentative pivot present" as a signal. They are on by construction.
* **Keep logging:** ev2_state, ev2_kind, ev2_abc_type, ev2_context, ev2_beyond_target, ev2_fib_stale_v1, ev2_fib_reanchored, ev2_tentative_move_atr, and the ≥2-families wave_end_n / wave_start_n. Revisit abc_provisional on stock shorts once the forward sample is larger.

## 9. tool_stats change
* `tool_stats.py` bumped to 2026-10-08.3 (backup `tool_stats.py.bak-2026-10-08-pre-ev2`).
* `exp_ev2_*` and raw `ev2_*` map to the tool `elliott_v2`, so the build7 tracker columns (Hebrew suffix stripped) are detected with no extra flag.
* Price levels, free-text labels and the tautological columns are `info` and are not tested: target / fib prices, labels, pivot json, last bar, and ev2_provisional, ev2_tentative_kind, ev2_long_state, ev2_short_state.
* Where an extra file carries the raw two-view columns (scan_hooks.csv has `ev2_long_*` / `ev2_short_*` and its plain `ev2_*` is the LONG view), the trade-direction `exp_ev2_*` is built from the matching view. Existing tracker values win. The raw LONG-view `ev2_*` is never tested on its own.
* Tests: `research-models/tests/test_tool_stats_ev2.py` (4 tests) and `test_tool_stats_excess.py` both pass.

## 10. Files (`/workspace/elliott-v2-eval/fdr/`)
* `common_ev2.py` (imports the 695-setup universe from `sr-waves-eval/fdr/common_fdr.py`), `leak_ev2.py` (-> `leak_ev2.csv`, `leak_ev2_mismatches.csv`), `features_ev2.py` (-> `features_ev2.pkl`), `analyze_ev2_fdr.py` (-> `fdr_results.csv`, `old940_requeried.csv`), `hints_replication.py` (-> `hints_replication.csv`).
* Copies: `/workspace/elliott-v2-eval/fdr_results.csv`, this file at `/workspace/elliott-v2-eval/fdr_results.md`.
* `scanner_elliott_v2.py`, `scanner_waves.py` and the waves/SR result files were used read-only. Nothing ran on Ilan's laptop.
