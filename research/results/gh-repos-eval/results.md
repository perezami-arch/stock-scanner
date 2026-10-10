# Evaluation of 7 professional open-source trading repos for the unified scanner
# Qlib · QuantConnect LEAN · NautilusTrader · vectorbt · OpenBB · FinRL · Freqtrade

Date: 2026-10-08 (times IL). Work dir: `/workspace/gh-repos-eval/` (one venv per repo, everything ran on the box; **nothing was installed on Ilan's laptop**).
Inputs were read-only: `/workspace/scanner-tool-eval/setups_prepared.csv` (same harness that found momentum 12-1), `/workspace/trading-frameworks-eval/iaf/` (`stop_rules.py` policy, `sim_ratchet_trades.csv`), tracker price files. No API key values were printed or stored here.

## סיכום בעברית

**השורה התחתונה: אף אחד משבעת הריפו לא מוסיף יתרון לסורק, וכולם חינמיים לשימוש מקומי.** העלויות מגיעות רק מענן או מגרסאות PRO שאנחנו לא צריכים.

| ריפו | מה זה | פסיקה | רישיון | עלות בפועל |
|---|---|---|---|---|
| Qlib (מיקרוסופט) | מודל דירוג מניות (Alpha158 + LightGBM) | **לוותר** | MIT | $0 |
| FinRL | סוכן למידת חיזוק (PPO) | **לוותר** | MIT | $0 |
| QuantConnect LEAN | מנוע בקטסט/לייב (C#) | **לוותר כמנוע** (שימש לאימות הקוד שלנו) | Apache-2.0 | $0 אם בונים מקוד; ה-CLI דורש מנוי בתשלום (חבילת Researcher ‏$84 לחודש); לייב בענן מ-$84 לחודש |
| NautilusTrader | מנוע בקטסט/לייב (Rust/Python) | **לא עכשיו**; מועמד ראשון אם נעבור למסחר חי אוטומטי | LGPL-3.0 | $0. אין חיבור ל-Alpaca, אז למניות צריך Interactive Brokers. נתונים מ-Databento בתשלום לפי שימוש |
| vectorbt | בקטסט וקטורי מהיר | **לאמץ ככלי מחקר בלבד, משקל 0** | Apache-2.0 + Commons Clause | $0. גרסת PRO ‏$25 לחודש / $240 לשנה / $500 לכל החיים, ולא נחוצה |
| OpenBB (v5) | שכבת נתונים | **לאמץ ככלי נתונים, משקל 0** | Apache-2.0 (מ-v5) | $0 לספקים שבדקנו. FMP, Polygon, Intrinio, Benzinga דורשים מפתח בתשלום. Workspace Lite ‏$2,400 לשנה, לא נחוץ |
| Freqtrade | בוט קריפטו | **לוותר** | GPL-3.0 | $0 (רק עמלות בורסה). קריפטו בלבד, בלי מניות |

**מספרים עיקריים:**
- **Qlib:** בדיקת ההצצה לעתיד נקייה (0 הבדלים מתוך 161,476 ערכים). אבל כמסנן על 442 סטאפים של מניות אין לו יתרון: ספירמן 0.03 (p=0.58), והפרש נשמר מול נפסל ‎-0.1 נק' אחוז. אחרי ניכוי המומנטום, הקשר שלו לתשואה שלילי בכל היעדים. השילובים עם מומנטום שעברו FDR נשענים כולם על המומנטום, וחלשים יותר מהמומנטום לבד.
- **FinRL:** ‏PPO קטן (2k צעדים, ‏256 מניות, 3 קפלים). ההתאמה שלילית (ספירמן ‎-0.06 עד ‎-0.09), שום דבר לא עובר FDR. ריצת 20k צעדים נעצרה באמצע כי המחשב המשותף היה עמוס.
- **מנועים:** ‏LEAN שחזר את `stop_rules.py` ב-788 מתוך 788 עסקאות (הפרש מקסימלי ‎4e-10 נק' אחוז). ‏Nautilus שחזר 787/788 (עסקה אחת ב-0.08 נק' אחוז). ‏vectorbt שחזר 787/788 (0.04 נק' אחוז), אבל רק כשאנחנו מחשבים את הסטופים; הסטופים המובנים שלו לא יודעים לעשות שנדליר על סגירה (439/487 שונים). כלומר הקוד שלנו מאומת ע"י שני מנועים מקצועיים, ואין סיבה להחליף אותו.
- **Freqtrade:** משחזר את הסמנטיקה של עצמו בדיוק, אבל לא את המדיניות שלנו: יציאה בפתיחה הבאה, פוזיציה אחת לכל זוג (22 מ-301 סטאפים נפלו), ובלי מניות.
- **OpenBB:** בלי מפתח מקבלים את לוח הדוחות, הפתעות EPS, קונצנזוס, שורט אינטרסט מ-FINRA (מ-2017), נתוני דארק-פול, שרשראות אופציות מ-CBOE (30/30 טיקרים), VIX, FRED ופמה-פרנץ'. אזהרות: האופציות והקונצנזוס הם תמונת מצב נוכחית בלבד, בלי היסטוריה, אז אי אפשר לבדוק אותם לאחור. לדוחות של Nasdaq אין תאריך הגשה, ולכן הם מסוכנים להצצה לעתיד. שורט אינטרסט צריך לפגר לפי תאריך הפרסום, לא תאריך הסליקה.
- **חומרה:** שום דבר כאן לא צריך GPU. ‏Qlib רץ על CPU (11 אימונים ב-2.3 עד 13.5 דקות), ו-FinRL עם MLP קטן מוגבל ע"י הסימולטור ולא ע"י הכרטיס. ה-RTX 4070 מספיק; 5090 לא ישנה כלום כאן.

---

## TL;DR (English)

* **Signal repos (Qlib, FinRL): no edge on the scanner's stock setups.** 36 tests in one BH-FDR family. The only rows with q<0.10 are "tool + momentum 12-1" averages, and they are carried by momentum: the tool's residual Spearman after removing the momentum rank is ≤0 in every target, and every combo is weaker than momentum alone (Spearman 0.17–0.18 vs 0.23 for momentum on xtot). With date-clustered p-values (per-date RankIC t-test), **nothing survives** (min q=0.40).
* **Engine repos: LEAN and Nautilus reproduce `stop_rules.py` exactly.** LEAN matches 788/788 trades (max diff 4e-10 pp). Nautilus matches 787/788, with the one outlier at 0.078 pp. This is the strongest independent validation of our backtester so far. **Neither is worth adopting as the engine.** Our code is already correct, and both add heavy dependencies: .NET 10 with a 10-minute build, a Rust core, and their own data formats. LEAN's CLI also needs a paid seat.
* **vectorbt:** fills match 787/788 (one at 0.036 pp), but only when our numpy computes the stop bars. Its native stop machinery can't express a close-based ATR chandelier (439/487 trades differ, and one native variant errors). It is very fast: 788 trades in 0.16 s warm, and a 51-backtest k-sweep in 2.3 s that matches the reference exactly. **Adopt as a research/sweep tool, weight 0.**
* **OpenBB v5 (Apache-2.0):** useful free data with no key: earnings calendar, EPS surprise, consensus, FINRA short interest, dark-pool/OTC, CBOE option chains, VIX, FRED, Fama-French, and CFTC. Point-in-time caveats are below. **Adopt as a data tool, weight 0.**
* **Freqtrade:** crypto only. It reproduces its own semantics exactly but structurally can't run our policy: next-open exits, one position per pair, and intrabar stops. **Skip.**
* **Costs: all seven are $0 to run locally.** Paid tiers only cover hosting or convenience, and none is needed (details in §8).

## 0. Setup, data and point-in-time rules

* **Stock setups:** `setups_prepared.csv`. 442 main-sheet setups (493 including the <$1.5B excluded list) have a valid PIT cutoff bar. Pre- and in-session alerts cut at the previous close (`cutoff_bar_date`).
* **Targets:** direction-adjusted, same harness as the momentum 12-1 finding.
  * **xtot:** total excess return vs SPY, last day ≤20.
  * **x20:** day-20 excess vs SPY.
  * **pol:** active-policy net return to 2026-10-07 (chandelier 4×ATR14, longs take half at 1.618; stock costs 0.02% fee + 0.05% slippage per side).
* **Filter test** (`rank_eval.py`): the score is ranked within the evaluated set and direction-signed, and keep = top half. Reported:
  * Spearman and per-date RankIC (dates with ≥5 setups) with t;
  * keep-minus-reject with a date-clustered bootstrap 95% CI;
  * top-minus-bottom tercile;
  * spread after dropping the top-1 and top-3 contributing tickers.
* **Multiple testing:** BH-FDR over all 36 signal tests (`final_signal_eval.py` → `final_signal_eval.csv/.md`), using both the iid Spearman p and the date-clustered per-date-RankIC p.
* **Engine parity set:** `parity/signals.csv` has 788 trades: 278 stock longs, 209 stock shorts and 301 crypto longs. Crypto uses a fixed 3×ATR stop and 0.10% + 0.10% costs. Each engine gets one synthetic instrument per setup, so overlapping setups never net. A trade counts as a mismatch if it differs by more than 0.01 pp from the reference replay (`ref_ret`, identical to `sim_ratchet`).

## 1. Qlib (microsoft/qlib) — signal / ranking

* **Version:** pyqlib 0.9.7, LightGBM 4.7.0. Repo has ~49.2k stars, MIT license, active (pushed 2026-10-08).
* **Model:** the official Alpha158 feature set with the benchmark LightGBM, on our own daily bars for the scanner universe (`qlib/src_csv` → `dump_bin`).
* **Walk-forward:**
  * One retrain per ISO week that contains setup cutoffs (11 fits).
  * Labels are 20-day forward returns. Training ends at `cal[i(cutoff_min) − 20]`, so every label is fully realised before the earliest cutoff of the week.
  * There is a 40-bar validation window and the score is the prediction on the cutoff-date features.
  * Variant A uses early stopping (best_iter is 1–140; the late folds stop almost immediately, so the model is close to a constant).
  * Variant B uses a fixed 200 rounds trained to the last realised label.
  * Runtime on the box (CPU, 3 threads): A 140 s total, B 814 s total.

**Leak check** (`qlib_leakcheck.py` → `qlib_leakcheck.json`):
* Alpha158 features at D were computed three ways: (a) on the full dataset, (b) on data truncated at D, and (c) with every post-D price and volume replaced by random junk.
* Tested at D = 2026-07-20 and 2026-09-23.
* **0 mismatches in 161,476 cells** (4 × ~40.3k). Alpha158 is strictly backward-looking, and the label and training cut prevent target leakage.

**Results, main sheet** (full table: `final_signal_eval.md`; per-variant tables incl. momentum: `qlib/qlib_eval.md`):

| Tool | Target | n | Spearman | p | per-date RankIC (t) | keep−reject pp [95% CI] | top−bottom tercile | q (iid / per-date) |
|---|---|---|---|---|---|---|---|---|
| Qlib A | xtot | 442 | +0.027 | 0.58 | +0.135 (1.97) | −0.13 [−3.40, +2.91] | −1.46 | 0.77 / 0.40 |
| Qlib A | x20 | 141 | −0.045 | 0.60 | −0.113 (−0.98) | −3.28 [−12.2, +4.0] | −3.51 | 0.77 / 0.49 |
| Qlib A | pol | 430 | −0.032 | 0.50 | +0.039 (0.52) | −0.40 [−3.98, +2.80] | −2.52 | 0.72 / 0.71 |
| Qlib B | xtot | 442 | +0.028 | 0.56 | −0.021 (−0.33) | −0.40 [−2.83, +1.98] | −0.74 | 0.77 / 0.84 |
| Qlib B | x20 | 141 | −0.035 | 0.68 | −0.192 (−1.33) | −1.15 [−8.96, +5.82] | −4.62 | 0.82 / 0.44 |
| Qlib B | pol | 430 | −0.014 | 0.78 | −0.061 (−0.95) | −0.54 [−3.76, +2.06] | −1.28 | 0.88 / 0.49 |
| *Momentum 12-1 (reference)* | xtot | 439 | +0.228 | <0.001 | +0.193 (2.96) | +3.05 [+0.06, +5.64] | +5.66 | — |

* **Residual after momentum:** Qlib's residual Spearman, after regressing out the momentum 12-1 rank, is −0.029 / −0.088 / −0.078 (A) and −0.011 / −0.077 / −0.048 (B) for xtot / x20 / pol. All are ≤0 and none is significant.
* **Combos with momentum:** "Qlib + momentum" averages reach q_iid<0.05, e.g. A xtot Spearman 0.171 and B xtot 0.179. But they are below momentum alone (0.228), fail with clustered p (q≥0.40), and lose most of the spread without the top-3 tickers (+1.1 to +1.7 pp).
* **Small-caps included** (main+excl, n=493): same picture. Qlib alone has Spearman 0.04–0.08, all with q≥0.18.

**Verdict: skip.** A generic cross-sectional alpha model trained on ~256 names adds nothing on top of the scanner's own setup selection. It also adds nothing on top of momentum 12-1, which the earlier eval already found.

**Cost:** $0, MIT. Microsoft's hosted Yahoo dataset is no longer the recommended source; we used our own bars. No paid tier exists. A CPU is enough, so no GPU is needed.

## 2. FinRL (AI4Finance-Foundation/FinRL) — RL agent as a signal

* **Version:** finrl 0.3.8 with stable-baselines3 2.9.0 and torch 2.14.1 (CPU). ~16.6k stars, MIT.
* **Setup:** `finrl_wf.py`.
  * The official `StockTradingEnv` runs on the 256 scanner stock tickers, with the stockstats indicators macd, rsi_30, cci_30 and dx_30, 0.07% costs, and a state dimension of 1,537.
  * There are 3 chronological folds over the setup cutoff dates. PPO is trained only on data up to the fold's first cutoff.
  * The trained policy then runs forward deterministically. Each setup is scored by the agent's action for its ticker on the cutoff date.
* **Bounded compute:**
  * A 2,048-step run took 35–60 s per fold.
  * A 20,480-step run was attempted. Fold 0 took 349 s, then the run was stopped because the box was overloaded (see below).
  * A real FinRL run would need 10^6+ steps, which is hours per fold. I did not start one because the small runs show no sign of signal (see below).
* **PIT note:**
  * Indicators are causal, and the training window ends at the fold start.
  * One minor impurity: FinRL's panel requires every ticker on every day, so tickers listed after 2024-01 are back-filled with their first price before listing. That is a flat price, so it carries no return information. Scored dates are always post-listing.

**Results** (main sheet):

| Run | Target | n | Spearman | p | per-date RankIC (t) | keep−reject pp [95% CI] | q (iid / per-date) |
|---|---|---|---|---|---|---|---|
| PPO 2k | xtot | 442 | −0.063 | 0.19 | −0.061 (−1.06) | −1.98 [−4.03, +0.00] | 0.35 / 0.49 |
| PPO 2k | x20 | 141 | −0.165 | 0.05 | −0.229 (−2.34) | −2.80 [−8.50, +3.05] | 0.12 / 0.40 |
| PPO 2k | pol | 431 | −0.023 | 0.63 | −0.016 (−0.28) | −1.28 [−3.23, +0.86] | 0.78 / 0.85 |

The 20,480-step run was **stopped unfinished**. Fold 0 trained in 349 s, but the shared box then ran at a load average of 50–90 on 8 cores, and folds 1–2 got under 2 CPU-minutes in 23 minutes of wall time. Rather than overrun the time budget, I kept only the 2k run. Its scores are in `finrl/finrl_scores_2048.csv`.

* **Residual after momentum** (2k run): −0.062 / −0.174 / −0.025 for xtot / x20 / pol.
* **Main+excl sample:** xtot keep−reject is −3.08 pp, CI [−5.35, −0.62]. The agent is, if anything, anti-predictive.

**Verdict: skip.** **Cost:** $0, MIT. Data is free (yfinance/Alpaca). The RTX 4070 would only speed up the network; the bottleneck is the Python environment step.

## 3. QuantConnect LEAN — engine

* **Version:** Lean master @80e7843 (2026-10-06), built from source with the .NET 10 SDK on the box. Build took 10 min 19 s; the run took 8.5 s. ~21.9k stars, Apache-2.0.
* **Test:** `ActivePolicyParity.cs` computes the chandelier natively in C#.
  * Each setup has a custom-data symbol with an OPEN row and a DAY row.
  * Entry is a market order at the open. Exits are market orders at the close when close ≤ stop.
  * Stops use extreme-close minus 4×ATR_prev, activated from bar k+2. Longs take half at 1.618; crypto uses a fixed 3×ATR stop.
  * Fees and slippage come from LEAN's own models.
* **Result:**
  * **788/788 trades matched** at the 0.01 pp tolerance. Max diff was 3.7e-10 pp on the return formula and 1.5e-5 pp using LEAN's own cash and fee accounting.
  * Stock: 487/487 matched. Crypto: 301/301 matched.
  * Mean return was 13.693% for both LEAN and the reference.
* **Verdict: skip as our engine.** Parity proves `stop_rules.py` is right, so there is nothing to fix. LEAN would add C#/.NET, its own data format, and (for the convenient CLI path) a paid seat.
* **Costs:**
  * Engine: $0 when self-built.
  * LEAN CLI, needed for local live via its brokerage plugins: you must be in a paid-tier organisation. The Researcher pack is $84/month ($888/year), made up of a ~$10 seat plus included nodes.
  * Cloud live: Researcher $84/month includes one L-MICRO live node (node list price $24/month). Team is $168 per user per month with a 2-user minimum.
  * QuantConnect datasets for local use are sold separately.
  * The free plan has no live trading.

## 4. NautilusTrader — engine

* **Version:** nautilus_trader 1.231.0 (pip wheel, Rust core). ~29.7k stars, LGPL-3.0.
* **Test:** `naut_parity.py`. The strategy runs in Python on `BacktestEngine`, with one synthetic `Equity` per setup and two bars per day (an opening bar and the day bar). Market orders, with slippage folded into the taker fee.
* **Result:**
  * **787/788 matched** (all 487 stocks; 300/301 crypto).
  * The single crypto trade is off by 0.078 pp, from the instrument's 6-decimal price precision. At a 0.1 pp tolerance there are 0 mismatches.
  * Setup took 3.2 s and the run 6.9 s for 53k bars.
* **Verdict: not now.** It is the best candidate if the scanner ever moves to automated live execution: Python strategy code, the same code for backtest and live, and fast.
  * **Gap:** there is no Alpaca adapter. The adapters are IB, Databento, Binance, Bybit, OKX, Kraken, Hyperliquid, dYdX, BitMEX, Deribit, Betfair, Polymarket and Tardis. US stocks would therefore go through Interactive Brokers.
* **Costs:**
  * $0 under LGPL.
  * Nautilus Pro and Cloud are "coming soon", with no published price.
  * Databento and Tardis data are paid, usage-based.
  * IB market-data subscriptions run a few $/month, often waived based on commissions.

## 5. vectorbt (open-source 1.1.1) — vectorised engine

* **Version:** ~9.3k stars. License: Apache-2.0 + Commons Clause, which means fair-code: you may not sell it. The open-source line is in maintenance mode.
* **Test:** `vbt_parity.py` and `vbt_native.py`.
  * **A.** Our numpy computes the stop and target bars for all 788 columns, and vectorbt `from_orders` does the fills, fees and P&L.
    * Result: **787/788 matched.** One stock long is off by 0.036 pp.
    * Speed: 12.6 s including numba compilation, **0.16 s warm**.
  * **B.** Native `from_signals` with an `adjust_sl_func_nb` chandelier errors ("Stop value must be 0 or greater").
  * **B′.** The plain native trailing stop on stocks mismatches 439/487 trades (mean 0.15% vs our 1.12%). Its stops trigger intrabar and trail from highs, not from closes.
  * **C.** A k-sweep of 2–6 ATR across all segments ran **51 backtests in 2.26 s**. The k=2/3/4 spot checks matched the reference exactly (0/788 mismatches each).
* **Verdict: adopt as a research tool, weight 0.** Use it for fast parameter sweeps and robustness grids, with stops computed by our own code. Do not use it as the source of truth.
* **Cost:** $0 for open source. vectorbt PRO costs $25/month, $240/year or $500 lifetime (early-contributor pricing, may rise). PRO is not needed.

## 6. OpenBB (Open Data Platform v5) — data layer

* **Version:** openbb 5.0.0, openbb-core 2.0.1.
* **License:** V5 is Apache-2.0. V4 and earlier were AGPL-3.0.
* **Repo:** stewardship moved to the non-profit **OpenBQ** (`openbq-org/OpenBB`, ~74k stars); the Workspace is going to FINOS.

The probe (`openbb/probe.py`, `probe2.py` → `openbb_probe*.json`) used only free/no-key providers and covered 30 scanner tickers.

| Endpoint (provider) | Works free? | Coverage | Beyond Alpaca/EDGAR? | PIT caveat |
|---|---|---|---|---|
| Earnings calendar, historical EPS + surprise %, consensus target/ratings (Nasdaq) | yes | AAPL ok; calendar 38 names/10 days | **yes** (catalyst timing, surprise) | consensus is a current snapshot, no history |
| Quarterly fundamentals (Nasdaq) | yes | 30/30 | partly | **no filing date** → leak risk; use SEC/EDGAR with accepted_date instead |
| Financial statements (SEC) | yes (period='quarterly') | AAPL 8 quarters | no (EDGAR) | statement endpoint has no filing date; join `sec.company_filings.accepted_date` |
| Insider trades Form 4 (SEC) | yes | AAPL 54 rows | no (EDGAR) | filing_date present ✓ |
| Short interest (FINRA, Nasdaq) | yes | FINRA history from 2017-12, latest settlement 2026-09-15 | **yes** | lag by publication (~8 business days after settlement), not settlement date |
| Dark-pool / OTC weekly volume (FINRA) | yes | AAPL 250 rows | **yes** | published with a 2–4 week delay |
| Option chains with OI/IV/greeks (CBOE, Nasdaq) | yes | **30/30** | **yes** | **snapshot only, no history** → cannot backtest; would need daily archiving to build history |
| VIX, Treasury rates, yield curve, FRED (worked without key), Fama-French, OECD CLI, CFTC COT | yes | full | yes (macro/regime) | release-date lags for macro |
| Crypto historical (Nasdaq) | **no** (empty) | — | — | — |

* **What needs paid keys:** the providers not installed here (FMP, Polygon/Massive, Intrinio, Benzinga, Tiingo, Tradier, etc.). FMP, Polygon and Tiingo have limited free tiers; Intrinio and Benzinga are paid.
* **Verdict: adopt as a data tool, weight 0.** The most useful pieces are:
  * the earnings calendar and EPS surprise, as a catalyst column for the scanner;
  * FINRA short interest, lagged to publication;
  * VIX and the yield curve, for regime.
  * If options are wanted, start archiving daily CBOE chains now, because there is no free history.
* **Cost:** $0 for ODP. OpenBB Workspace: Community is free for individuals, Lite is $2,400/year per team, Pro is custom. None of these is needed.

## 7. Freqtrade — crypto bot / engine

* **Version:** freqtrade 2026.9 with ccxt 4.5.85. ~55.1k stars, GPL-3.0. **Crypto only**, via ccxt exchanges; no equities.
* **Test:** `ft_eval2.py` and `ft_eval3.py`. 301 crypto setups were run as daily candles converted from our replay bars (Binance tick-rounded), with a custom `ScannerFixedATR` strategy and 0.2% folded cost per side.

**Results:**
* **Engine vs its own documented semantics:** 0/279 mismatches (max 5e-10 pp). The semantics are: exit signal on close j fills at the open of j+1, and open trades are force-closed at the last candle's open. So the engine is internally exact.
* **vs our reference:**
  * **22/301 setups can't be placed.** Freqtrade allows one open position per pair (BTC 4, ETH 4, SOL 3, …).
  * 266/279 trades differ by more than 0.01 pp (mean +5.2 pp, max 19.6 pp). The causes are next-open fills and the final-candle open exit.
  * The intrabar-stoploss variant still differs from our intrabar reference on 261/279 trades.

**Verdict: skip.** It can't hold overlapping setups on one coin, can't trade stocks, and would need 1m data to enter at the alert minute.

**Cost:** $0 (GPL-3.0); only exchange fees. FreqAI is bundled and free.

## 8. Costs summary

| Repo | License | Local use | Paid tiers (not needed) | Data cost | Cloud |
|---|---|---|---|---|---|
| Qlib | MIT | $0 | none | $0 (own bars) | — |
| FinRL | MIT | $0 | none | $0 (yfinance/Alpaca) | — |
| LEAN | Apache-2.0 | $0 if self-built; CLI needs paid seat | QC Researcher $84/mo ($888/yr); Team $168/user/mo (min 2) | QC datasets sold separately; Alpaca data free | live node from $24/mo, inside paid plan; free plan = no live |
| NautilusTrader | LGPL-3.0 | $0 | Pro/Cloud "coming soon", unpriced | Databento/Tardis usage-based; IB data subs few $/mo | — |
| vectorbt | Apache-2.0 + Commons Clause | $0 | PRO $25/mo, $240/yr, $500 lifetime | $0 | — |
| OpenBB ODP v5 | Apache-2.0 | $0 | Workspace Lite $2,400/yr; Pro custom | free providers tested; FMP/Polygon/Intrinio/Benzinga paid keys | Community free |
| Freqtrade | GPL-3.0 | $0 | none | $0 (exchange APIs) | — |

**Hardware:** everything above ran on the box CPU. Qlib/LightGBM is CPU-bound. FinRL's small MLP is limited by the environment, not the GPU. The engines are CPU-only. Ilan's RTX 4070 8GB and 32GB RAM are more than enough; a 5090 would change nothing here (projection).

## 9. Files

* `qlib/qlib_wf.py`, `qlib_wf_B.py` → `qlib_scores*.csv`, `qlib_fits*.csv`. `qlib_eval.py` → `qlib_eval.md/.csv`. `qlib_leakcheck.py` → `qlib_leakcheck.json`.
* `finrl/finrl_wf.py` → `finrl_scores_2048.csv` and `finrl_meta_2048.json` (the 20k run was stopped, so it has no output).
* `final_eval.py` → `final_signal_eval.csv/.md` (all 36 signal tests with BH-FDR).
* `lean/ActivePolicyParity.cs`, `lean_eval.py` → `lean_results.json`, `lean_parity_trades.csv`; build log in `logs/lean_build*.log`.
* `nautilus/naut_parity.py` → `naut_results.json`. `vbt/vbt_parity.py`, `vbt_native.py`, `vbt_sweep_check.py` → `vbt_*.json`.
* `openbb/probe.py`, `probe2.py` → `openbb_probe.json`, `openbb_probe2.json`. `freqtrade/ft_eval*.py` → `ft_results*.json`.
* `repo_facts.txt` (GitHub stars, forks, license, last push).

## Caveats

* ~3.5 months of setups (Jul–Oct 2026) and 34–36 alert dates. Effects under ~5 pp cannot be detected, and many stock trades in `pol` are still open.
* Qlib/FinRL were tested only as filters on scanner setups, not as standalone stock pickers over the whole market.
* FinRL was deliberately small: 2k PPO steps were evaluated, and the 20k attempt was stopped because of box load. A long run (10^6+ steps) could behave differently, but the 2k agent is slightly anti-predictive, so hours of compute were not justified.
