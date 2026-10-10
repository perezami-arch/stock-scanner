### 3.14 Geometry, volume profile, candles and liquidity zones (`/workspace/scanner_geometry.py`) — PIT backtest on the scanner setups (group follow-up; `iaf/geo_features.py`, `geo_leakcheck.py`, `sim_geo.py`, `geo_analyze.py`, `geo_report.py`; full table N = `iaf/geometry_table.md|csv`)
**Bottom line: expect noise and that is mostly what came out.** 692 comparisons were run in one Benjamini-Hochberg family; 74 had nominal p<0.05 (≈35 expected by chance). After FDR (q<0.10) and every robustness check, **only 2 of 580 filter comparisons survive, both on stock SHORTS and both re-expressing "the stock is already breaking down" — which the existing short rule (score ≥3 & below SMA200) already captures.** No spiral, Gann, candle-pattern or sweep column survives anywhere (best: candles p=0.04, spiral q=0.41, sweeps — 'any sweep in the last 3 bars' on shorts −4.8 pp, q=0.20 — cluster sweeps and prior-candle breaks separately q≥0.5). In the level tests nothing improves on the active policy; liquidity/FVG take-profits and HVN stops on crypto are **robustly worse**. Nothing here gets score weight; the two short-side survivors are candidates to re-check on the setups from 12.10.2026 onward.

**Setup.** Columns = `geometry_columns(df, cutoff, asset, direction)` exactly as written by the teammate (module not modified), computed for 1,040 setups (all rows; tables use the main sheet, no dups). Cutoff = the same information cutoff every earlier table uses (`setups_prepared.info_cutoff_utc`: stocks = rule-bar close, i.e. previous close for pre/intraday alerts and the alert-day bar only for after-close alerts; crypto = alert minute, Perplexity −70 min). Direction view = the setup's direction; liquidity features are re-expressed relative to the trade (*fwd* = target side, e.g. buy-side pools above a long; *back* = stop side). Outcome = the **active policy** trade (stock longs: ratchet chandelier 4×ATR + ½ at Fib 1.618; stock shorts: ratchet chandelier 4×ATR; crypto longs: fixed 3×ATR; close-based; open trades marked at the 2026-10-07 close). `sim_geo.py` reproduces `sim_ratchet_trades.csv` (rt_ratchet_h618 / rt_ratchet / rt_fixed3, c and i) with 0 mismatches (max |diff| 2e-16). Segments: all stock longs (N=242), rule-filtered stock longs (115), Perplexity stock longs (59), Grok stock longs (142), all stock shorts (189), crypto longs (264, Grok 255 + Perplexity 9). Crypto shorts are frozen by the rules and were not tested.

**1. Independent leak check (30 random setups, seed 20261008).** For each setup the columns were computed 4 ways: full history + cutoff; history physically truncated at the rule bar; all bars after the rule bar replaced by random garbage plus 30 extra garbage bars; truncated with cutoff=None. **14,628 column comparisons, 0 mismatches.** 383 `*_confirmed_at` values plus all past-object dates (anchor, spiral, anchored-VP start, sweep, candle bar) and the confirmation dates of every pool used by the level tests: **0 later than the cutoff bar**; last visible bar = rule bar in 30/30. For all 816 main-sheet setups, feeding the module the raw alert time (exact / schedule / UI-log alerts) instead of the tracker cutoff gives the same last visible bar in 100 % of cases (date-only alerts use the conservative tracker cutoff). Verdict: **no look-ahead found**. (Caveat, not a code leak: daily prices are Yahoo dividend-adjusted, as in every earlier table.)

**2. Method.** Filter test = mean x_mkt with the feature − without, per segment; continuous features: lowest quintile vs rest, highest quintile vs rest, and a rank slope (≈ Q5−Q1). Min N 20 on each side (330 candidate comparisons were skipped for N<20 or <5 distinct values and are **not** counted). Sweeps split by `liq_sweep_kind` (pool/cluster sweep vs prior-candle break) and by direction relative to the trade. **p-values are conservative:** the maximum of ticker-clustered, entry-date-clustered and two-way clustered p, because stock setups come from only 22–25 entry dates (the top 5 dates hold 55–60 % of stock trades) — naïve p-values would be far too small. Robust = q<0.10 **and** median difference, raw-return difference, within-entry-date difference, and the difference after dropping the top-1 and top-3 tickers all keep the sign. q<0.10 that fails a check = LUCK.

**Comparisons by family (total 692):**
| kind | family | comparisons | p<0.05 (nominal) | expected by chance | q<0.10 (BH) | ROBUST |
|---|---|---|---|---|---|---|
| filter | candle | 84 | 1 | 4.2 | 0 | 0 |
| filter | gann | 60 | 0 | 3.0 | 0 | 0 |
| filter | liquidity | 218 | 22 | 10.9 | 1 | 1 |
| filter | spiral | 32 | 1 | 1.6 | 0 | 0 |
| filter | vp | 186 | 36 | 9.3 | 1 | 1 |
| level | level | 112 | 14 | 5.6 | 10 | 10 |
| **total** | | **692** | **74** | **34.6** | **12** | **12** |
All 10 robust level-test rows are robustly **worse** than the active policy (crypto targets and HVN stops); none is an improvement.

**Filter comparisons surviving FDR (q<0.10) — total comparisons in the family: 692.** x_mkt in % (excess vs SPY), shorts: ret + SPY return.
| segment | feature | test | N with | N without | x_mkt with | x_mkt without | med x with | med x without | diff x_mkt | diff raw ret | diff within-date | diff 1st half | diff 2nd half | diff w/o top1 | diff w/o top3 | p | q (BH) | p beyond rule inputs | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| All stock SHORT | vp120_beyond_VA_in_trade_dir | with vs without | 38 | 151 | +7.3 | -0.9 | +8.4 | -1.6 | +8.2 | +8.5 | +6.2 | +10.0 | +6.4 | +8.0 | +7.1 | 0.0002 | 0.0150 | 0.0198 | ROBUST |
| All stock SHORT | liq_fwd_pools_n : rank slope (Q5-Q1 equiv.) | rank slope | 189 | 0 | -0.9 | +5.5 | -0.1 | +7.8 | -9.5 | -9.9 | -3.3 | -6.4 | -5.1 | -4.6 | -3.4 | 0.0007 | 0.0453 | 0.0599 | ROBUST |

* **vp120 "beyond value area in trade direction"** for shorts = the close is **below the 120-day volume-profile value area**. 37 of these 38 shorts already pass the short rule (score ≥3 & below SMA200), so it is mostly a stricter version of the rule. Inside the 60 rule-filtered shorts: below VA120 (N=37, 30 tickers, 11 dates) +6.2 % mean / +6.8 % median / +7.3 vs SPY / 81 % hit vs the other 23 rule-passers +1.2 % / +1.6 % / +2.3 vs SPY / 61 % hit (descriptive, not in the FDR family). It also stays significant after controlling for the rule inputs (p≈0.02). This is the only lead worth carrying forward, as a **candidate refinement of the short rule**, to be validated on the new setups.
* **liq_fwd_pools_n** for shorts = number of untaken swing-low pools below the price. Fewer pools (price at or under its recent lows) → better shorts. Same story: a breakdown/momentum proxy; 43 of the 49 shorts with ≤1 such pool already pass the short rule. After controlling for the rule inputs it is no longer significant (p≈0.06).

**Closest misses (nominal p<0.05, fail FDR) — total comparisons: 692.** Listed only so nobody re-discovers them as "signals":
| segment | feature | test | N with | N without | diff x_mkt | diff within-date | diff w/o top3 | p | q (BH) |
|---|---|---|---|---|---|---|---|---|---|
| All stock SHORT | liq_back_pool_dist_atr : rank slope (Q5-Q1 equiv.) | rank slope | 159 | 0 | +12.2 | +5.0 | +5.0 | 0.0021 | 0.1144 |
| All stock SHORT | liq_fvg_open_n : Q5 (highest 20%) vs rest | Q5 vs rest | 38 | 151 | -5.6 | -3.6 | -2.9 | 0.0031 | 0.1514 |
| All stock SHORT | vp60_hvn_absdist_atr : rank slope (Q5-Q1 equiv.) | rank slope | 189 | 0 | +7.5 | +2.5 | +2.7 | 0.0034 | 0.1518 |
| Rule-filtered stock LONG | liq_fwd_fvg_exists | with vs without | 72 | 43 | +7.7 | +3.5 | +4.6 | 0.0039 | 0.1518 |
| Rule-filtered stock LONG | vp120_hvn_absdist_atr : Q5 (highest 20%) vs rest | Q5 vs rest | 23 | 92 | -8.2 | -5.9 | -5.2 | 0.0041 | 0.1518 |
| Rule-filtered stock LONG | vp120_beyond_VA_in_trade_dir | with vs without | 39 | 76 | -7.6 | -3.2 | -4.7 | 0.0042 | 0.1518 |
| Crypto LONG | vp120_poc_dist_atr_signed (+ = beyond POC in trade dir) : Q5 (highest 20%) vs rest | Q5 vs rest | 53 | 211 | -15.6 | -5.1 | -10.4 | 0.0048 | 0.1580 |
| All stock SHORT | vp60_poc_dist_atr_signed (+ = beyond POC in trade dir) : Q5 (highest 20%) vs rest | Q5 vs rest | 38 | 151 | +6.5 | +4.4 | +5.1 | 0.0051 | 0.1604 |
| Rule-filtered stock LONG | vp120_inside_VA | with vs without | 68 | 47 | +8.4 | +5.8 | +5.1 | 0.0064 | 0.1913 |
| All stock SHORT | liq_sweep_any (last 3 bars) | with vs without | 143 | 46 | -4.8 | -5.6 | -3.6 | 0.0073 | 0.2036 |
| All stock SHORT | vpanc_poc_dist_atr_signed (+ = beyond POC in trade dir) : Q5 (highest 20%) vs rest | Q5 vs rest | 38 | 151 | +5.6 | +3.7 | +4.4 | 0.0074 | 0.2036 |
| All stock LONG | vp120_inside_VA | with vs without | 144 | 98 | +5.9 | +4.1 | +4.2 | 0.0081 | 0.2147 |
A consistent but non-significant pattern on stock longs: being **inside** the 60/120-day value area beat being extended above it (rule-filtered longs +7 to +8 pp, all longs +3 to +6 pp; q 0.19–0.37). Plausible (do not chase extended names), but not proven here.

**3. Level tests** (paired vs the active policy on covered trades; close-based shown, intraday in table N — total comparisons in the family: 692). *Stop* = nearest confirmed object beyond the entry −0.5×ATR14 (pool = untaken equal/swing-low cluster, OB = unmitigated order-block zone, HVN = 60/120-bar profile node); `fix` = that level only, `hyb` = the tighter of the level and the policy stop. *Target* = next untaken liquidity pool or open FVG edge in the trade direction, full exit or ½, replacing the 1.618 half on stock longs. No object beyond the entry → the trade stays on the active policy and is not counted.
| segment | variant | N covered | coverage % | level dist (ATR, median) | % trades changed | mean variant | mean policy | median variant | median policy | hit variant | hit policy | x_mkt variant | x_mkt policy | paired diff | diff w/o top3 | p | q (BH) | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| All stock LONG | stop: nearest HVN -0.5ATR (fixed) (close) | 188 | 78 | 1.3 | 37 | +1.4 | +2.8 | -1.1 | +0.5 | 44 | 56 | +0.6 | +1.5 | -1.4 | -0.3 | 0.1000 | 0.5242 | noise |
| All stock LONG | stop: tighter of HVN-0.5ATR and policy stop (close) | 188 | 78 | 1.3 | 36 | +1.4 | +2.8 | -1.1 | +0.5 | 44 | 56 | +0.7 | +1.5 | -1.4 | -0.3 | 0.1081 | 0.5311 | noise |
| All stock LONG | stop: order-block zone -0.5ATR (fixed) (close) | 97 | 40 | 6.6 | 12 | +1.8 | +1.5 | +0.4 | +0.4 | 56 | 56 | +0.3 | +0.1 | +0.3 | -0.2 | 0.5229 | 0.8045 | noise |
| All stock LONG | stop: tighter of OB-0.5ATR and policy stop (close) | 97 | 40 | 6.6 | 3 | +1.3 | +1.5 | +0.3 | +0.4 | 55 | 56 | -0.0 | +0.1 | -0.2 | +0.0 | 0.4456 | 0.7734 | noise |
| All stock LONG | stop: nearest liquidity pool beyond entry -0.5ATR (fixed) (close) | 217 | 90 | 3.0 | 24 | +3.0 | +3.1 | +0.4 | +0.5 | 54 | 56 | +1.7 | +1.8 | -0.1 | +0.4 | 0.7347 | 0.9184 | noise |
| All stock LONG | stop: tighter of pool-0.5ATR and policy stop (close) | 217 | 90 | 3.0 | 16 | +2.7 | +3.1 | +0.1 | +0.5 | 52 | 56 | +1.6 | +1.8 | -0.4 | +0.1 | 0.2377 | 0.6452 | noise |
| All stock LONG | target: next open FVG edge, full exit (close) | 148 | 61 | 0.9 | 50 | +2.1 | +2.7 | +1.9 | +0.6 | 63 | 53 | +1.4 | +1.7 | -0.7 | +0.7 | 0.5223 | 0.8045 | noise |
| All stock LONG | target: next open FVG edge, 1/2 exit (close) | 148 | 61 | 0.9 | 45 | +2.5 | +2.7 | +1.0 | +0.6 | 58 | 53 | +1.5 | +1.7 | -0.2 | +0.3 | 0.6511 | 0.8732 | noise |
| All stock LONG | target: next liquidity pool, full exit (close) | 213 | 88 | 2.3 | 37 | +2.0 | +3.3 | +1.0 | +0.6 | 59 | 55 | +1.1 | +2.1 | -1.3 | -0.4 | 0.0992 | 0.5242 | noise |
| All stock LONG | target: next liquidity pool, 1/2 exit (close) | 213 | 88 | 2.3 | 33 | +2.7 | +3.3 | +0.8 | +0.6 | 58 | 55 | +1.5 | +2.1 | -0.6 | -0.2 | 0.0740 | 0.5079 | noise |
| Rule-filtered stock LONG | stop: nearest HVN -0.5ATR (fixed) (close) | 98 | 85 | 1.4 | 26 | +3.5 | +3.8 | +0.5 | +1.0 | 56 | 61 | +2.5 | +2.4 | -0.3 | +0.1 | 0.3707 | 0.7309 | noise |
| Rule-filtered stock LONG | stop: tighter of HVN-0.5ATR and policy stop (close) | 98 | 85 | 1.4 | 24 | +3.6 | +3.8 | +0.5 | +1.0 | 56 | 61 | +2.6 | +2.4 | -0.2 | +0.1 | 0.4717 | 0.7879 | noise |
| Rule-filtered stock LONG | stop: order-block zone -0.5ATR (fixed) (close) | 55 | 48 | 7.3 | 7 | +1.7 | +1.6 | +0.5 | +0.5 | 62 | 60 | +0.2 | +0.2 | +0.1 | -0.2 | 0.7192 | 0.9166 | noise |
| Rule-filtered stock LONG | stop: nearest liquidity pool beyond entry -0.5ATR (fixed) (close) | 109 | 95 | 3.4 | 17 | +4.4 | +3.9 | +1.4 | +1.0 | 63 | 60 | +3.1 | +2.6 | +0.5 | +0.2 | 0.2174 | 0.6224 | noise |
| Rule-filtered stock LONG | stop: tighter of pool-0.5ATR and policy stop (close) | 109 | 95 | 3.4 | 10 | +4.2 | +3.9 | +1.0 | +1.0 | 60 | 60 | +3.0 | +2.6 | +0.3 | +0.0 | 0.2534 | 0.6591 | noise |
| Rule-filtered stock LONG | target: next open FVG edge, full exit (close) | 60 | 52 | 0.7 | 68 | +5.3 | +7.3 | +4.4 | +3.4 | 80 | 67 | +4.9 | +6.4 | -2.0 | +0.7 | 0.3313 | 0.7030 | noise |
| Rule-filtered stock LONG | target: next open FVG edge, 1/2 exit (close) | 60 | 52 | 0.7 | 58 | +6.6 | +7.3 | +4.5 | +3.4 | 77 | 67 | +5.7 | +6.4 | -0.7 | +0.2 | 0.4017 | 0.7557 | noise |
| Rule-filtered stock LONG | target: next liquidity pool, full exit (close) | 93 | 81 | 1.9 | 42 | +2.7 | +5.4 | +1.1 | +1.1 | 63 | 61 | +1.9 | +4.2 | -2.7 | -0.9 | 0.1018 | 0.5294 | noise |
| Rule-filtered stock LONG | target: next liquidity pool, 1/2 exit (close) | 93 | 81 | 1.9 | 39 | +4.3 | +5.4 | +1.0 | +1.1 | 61 | 61 | +3.1 | +4.2 | -1.1 | -0.4 | 0.0842 | 0.5079 | noise |
| Perplexity stock LONG | stop: nearest HVN -0.5ATR (fixed) (close) | 41 | 69 | 1.3 | 44 | +2.8 | +4.1 | -2.6 | +0.6 | 39 | 54 | +2.6 | +3.3 | -1.3 | -0.0 | 0.1715 | 0.5880 | noise |
| Perplexity stock LONG | stop: tighter of HVN-0.5ATR and policy stop (close) | 41 | 69 | 1.3 | 44 | +2.8 | +4.1 | -2.6 | +0.6 | 39 | 54 | +2.6 | +3.3 | -1.3 | -0.0 | 0.1715 | 0.5880 | noise |
| Perplexity stock LONG | stop: nearest liquidity pool beyond entry -0.5ATR (fixed) (close) | 52 | 88 | 2.7 | 37 | +3.7 | +3.6 | -0.1 | +0.3 | 50 | 52 | +3.3 | +3.1 | +0.1 | -0.9 | 0.9278 | 0.9763 | noise |
| Perplexity stock LONG | stop: tighter of pool-0.5ATR and policy stop (close) | 52 | 88 | 2.7 | 25 | +2.8 | +3.6 | -2.1 | +0.3 | 42 | 52 | +2.6 | +3.1 | -0.8 | +0.8 | 0.4777 | 0.7909 | noise |
| Perplexity stock LONG | target: next open FVG edge, full exit (close) | 42 | 71 | 0.8 | 60 | +4.9 | +6.3 | +4.1 | +0.7 | 74 | 55 | +5.1 | +6.4 | -1.5 | +2.2 | 0.5910 | 0.8381 | noise |
| Perplexity stock LONG | target: next open FVG edge, 1/2 exit (close) | 42 | 71 | 0.8 | 57 | +6.5 | +6.3 | +1.5 | +0.7 | 69 | 55 | +6.5 | +6.4 | +0.1 | -1.1 | 0.8816 | 0.9662 | noise |
| Perplexity stock LONG | target: next liquidity pool, full exit (close) | 53 | 90 | 2.3 | 43 | +2.7 | +5.3 | +1.8 | +0.8 | 60 | 55 | +2.8 | +5.1 | -2.7 | +0.3 | 0.1949 | 0.6001 | noise |
| Perplexity stock LONG | target: next liquidity pool, 1/2 exit (close) | 53 | 90 | 2.3 | 42 | +4.7 | +5.3 | +1.1 | +0.8 | 57 | 55 | +4.5 | +5.1 | -0.7 | +0.1 | 0.2243 | 0.6260 | noise |
| Grok stock LONG | stop: nearest HVN -0.5ATR (fixed) (close) | 111 | 78 | 1.3 | 37 | +1.0 | +2.3 | -1.1 | +0.4 | 45 | 57 | -0.0 | +0.8 | -1.4 | -0.3 | 0.0995 | 0.5242 | noise |
| Grok stock LONG | stop: tighter of HVN-0.5ATR and policy stop (close) | 111 | 78 | 1.3 | 35 | +1.0 | +2.3 | -1.1 | +0.4 | 45 | 57 | +0.0 | +0.8 | -1.3 | -0.2 | 0.1140 | 0.5311 | noise |
| Grok stock LONG | stop: order-block zone -0.5ATR (fixed) (close) | 61 | 43 | 7.0 | 13 | +2.3 | +2.2 | +0.4 | +0.4 | 59 | 61 | +0.7 | +0.7 | +0.1 | -0.4 | 0.8643 | 0.9635 | noise |
| Grok stock LONG | stop: tighter of OB-0.5ATR and policy stop (close) | 61 | 43 | 7.0 | 5 | +1.9 | +2.2 | +0.4 | +0.4 | 59 | 61 | +0.4 | +0.7 | -0.3 | +0.1 | 0.4517 | 0.7748 | noise |
| Grok stock LONG | stop: nearest liquidity pool beyond entry -0.5ATR (fixed) (close) | 125 | 88 | 3.2 | 18 | +2.1 | +2.5 | +0.4 | +0.4 | 54 | 57 | +0.5 | +0.9 | -0.5 | +0.3 | 0.3322 | 0.7030 | noise |
| Grok stock LONG | stop: tighter of pool-0.5ATR and policy stop (close) | 125 | 88 | 3.2 | 13 | +2.1 | +2.5 | +0.4 | +0.4 | 54 | 57 | +0.7 | +0.9 | -0.4 | +0.2 | 0.3436 | 0.7149 | noise |
| Grok stock LONG | target: next open FVG edge, full exit (close) | 86 | 61 | 1.0 | 44 | +0.8 | +0.6 | +0.7 | +0.4 | 57 | 52 | -0.3 | -0.8 | +0.1 | -0.7 | 0.8961 | 0.9689 | noise |
| Grok stock LONG | target: next open FVG edge, 1/2 exit (close) | 86 | 61 | 1.0 | 37 | +0.5 | +0.6 | +0.5 | +0.4 | 52 | 52 | -1.0 | -0.8 | -0.2 | +0.3 | 0.7006 | 0.9045 | noise |
| Grok stock LONG | target: next liquidity pool, full exit (close) | 123 | 87 | 2.4 | 37 | +1.4 | +2.1 | +0.8 | +0.4 | 59 | 56 | +0.2 | +0.6 | -0.7 | +0.0 | 0.2961 | 0.7017 | noise |
| Grok stock LONG | target: next liquidity pool, 1/2 exit (close) | 123 | 87 | 2.4 | 33 | +1.6 | +2.1 | +0.8 | +0.4 | 59 | 56 | +0.1 | +0.6 | -0.5 | -0.0 | 0.2177 | 0.6224 | noise |
| All stock SHORT | stop: nearest HVN -0.5ATR (fixed) (close) | 130 | 69 | 1.2 | 42 | +0.4 | -0.1 | -1.3 | -0.3 | 45 | 49 | +1.5 | +1.2 | +0.6 | -0.2 | 0.4385 | 0.7683 | noise |
| All stock SHORT | stop: tighter of HVN-0.5ATR and policy stop (close) | 130 | 69 | 1.2 | 40 | +0.5 | -0.1 | -1.3 | -0.3 | 45 | 49 | +1.6 | +1.2 | +0.7 | -0.1 | 0.3440 | 0.7149 | noise |
| All stock SHORT | stop: order-block zone -0.5ATR (fixed) (close) | 40 | 21 | 7.9 | 12 | +2.0 | +2.7 | +6.3 | +6.3 | 75 | 75 | +3.1 | +3.8 | -0.7 | +0.4 | 0.4188 | 0.7585 | noise |
| All stock SHORT | stop: nearest liquidity pool beyond entry -0.5ATR (fixed) (close) | 159 | 84 | 2.9 | 31 | -0.7 | -0.8 | -1.8 | -1.6 | 43 | 44 | +0.5 | +0.6 | +0.0 | -0.5 | 0.9536 | 0.9846 | noise |
| All stock SHORT | stop: tighter of pool-0.5ATR and policy stop (close) | 159 | 84 | 2.9 | 25 | -0.4 | -0.8 | -1.8 | -1.6 | 43 | 44 | +0.9 | +0.6 | +0.4 | -0.1 | 0.3378 | 0.7083 | noise |
| All stock SHORT | target: next open FVG edge, full exit (close) | 133 | 70 | 1.1 | 36 | -1.1 | -1.6 | -0.5 | -2.0 | 49 | 38 | -0.3 | -0.2 | +0.5 | -0.0 | 0.2989 | 0.7017 | noise |
| All stock SHORT | target: next open FVG edge, 1/2 exit (close) | 133 | 70 | 1.1 | 36 | -1.4 | -1.6 | -0.8 | -2.0 | 43 | 38 | +0.1 | -0.2 | +0.3 | -0.0 | 0.2989 | 0.7017 | noise |
| All stock SHORT | target: next liquidity pool, full exit (close) | 164 | 87 | 2.6 | 19 | -1.6 | -1.7 | -1.4 | -2.0 | 45 | 39 | -0.6 | -0.3 | +0.1 | -0.4 | 0.8389 | 0.9628 | noise |
| All stock SHORT | target: next liquidity pool, 1/2 exit (close) | 164 | 87 | 2.6 | 19 | -1.6 | -1.7 | -1.7 | -2.0 | 43 | 39 | -0.3 | -0.3 | +0.0 | -0.2 | 0.8389 | 0.9628 | noise |
| Crypto LONG | stop: nearest HVN -0.5ATR (fixed) (close) | 243 | 92 | 1.5 | 31 | +22.5 | +33.0 | +15.5 | +31.1 | 62 | 86 | +8.7 | +13.0 | -10.5 | -5.9 | 0.0046 | 0.1577 | nominal p<0.05 only (fails FDR) |
| Crypto LONG | stop: tighter of HVN-0.5ATR and policy stop (close) | 243 | 92 | 1.5 | 30 | +22.3 | +33.0 | +15.2 | +31.1 | 61 | 86 | +8.5 | +13.0 | -10.7 | -6.3 | 0.0038 | 0.1518 | nominal p<0.05 only (fails FDR) |
| Crypto LONG | stop: order-block zone -0.5ATR (fixed) (close) | 117 | 44 | 5.9 | 9 | +29.1 | +24.2 | +10.8 | +8.6 | 79 | 74 | +17.5 | +13.6 | +4.9 | +0.0 | 0.1878 | 0.5993 | noise |
| Crypto LONG | stop: tighter of OB-0.5ATR and policy stop (close) | 117 | 44 | 5.9 | 2 | +23.6 | +24.2 | +7.9 | +8.6 | 72 | 74 | +13.6 | +13.6 | -0.6 | +0.0 | 0.3360 | 0.7069 | noise |
| Crypto LONG | stop: nearest liquidity pool beyond entry -0.5ATR (fixed) (close) | 262 | 99 | 2.8 | 13 | +30.0 | +33.4 | +28.5 | +31.6 | 81 | 87 | +11.1 | +12.5 | -3.4 | +0.6 | 0.1571 | 0.5662 | noise |
| Crypto LONG | stop: tighter of pool-0.5ATR and policy stop (close) | 262 | 99 | 2.8 | 10 | +29.2 | +33.4 | +28.5 | +31.6 | 79 | 87 | +10.9 | +12.5 | -4.2 | -0.5 | 0.0744 | 0.5079 | noise |
| Crypto LONG | target: next open FVG edge, full exit (close) | 155 | 59 | 1.7 | 98 | +11.3 | +45.9 | +11.6 | +37.0 | 97 | 97 | +3.9 | +17.1 | -34.6 | -26.1 | <0.0001 | 0.0046 | ROBUST |
| Crypto LONG | target: next open FVG edge, 1/2 exit (close) | 155 | 59 | 1.7 | 98 | +28.6 | +45.9 | +27.8 | +37.0 | 97 | 97 | -0.2 | +17.1 | -17.3 | -13.0 | <0.0001 | 0.0046 | ROBUST |
| Crypto LONG | target: next liquidity pool, full exit (close) | 238 | 90 | 1.4 | 91 | +11.4 | +36.8 | +10.5 | +32.9 | 92 | 91 | +3.6 | +13.9 | -25.4 | -24.4 | 0.0002 | 0.0153 | ROBUST |
| Crypto LONG | target: next liquidity pool, 1/2 exit (close) | 238 | 90 | 1.4 | 91 | +24.1 | +36.8 | +24.6 | +32.9 | 91 | 91 | +1.2 | +13.9 | -12.7 | -12.2 | 0.0002 | 0.0153 | ROBUST |

* **Stocks: no level rule beats the 4×ATR chandelier.** Pool stops (median 2.7–3.4 ATR from entry vs 4 ATR) change 10–37 % of trades and move the mean by −0.8 to +0.5 pp. HVN stops (≈1.2–1.4 ATR) change 25–44 %, cost 0.2–1.4 pp on longs and cut the hit rate (e.g. all longs 56 → 44 %); on shorts +0.6 pp, noise. OB stops sit ≈6.5–8 ATR away and rarely bind (±0.7 pp). Liquidity / FVG targets raise the hit rate (all longs 53–55 → 58–63 %, rule-filtered 61–67 → 61–80 %) but lower the mean by up to 2.7 pp on longs — the same trade-off as the Fib targets in §3.12; on shorts they change ≤0.5 pp. No stock level difference survives FDR (best q ≈0.3).
* **Crypto: liquidity / FVG targets are robustly harmful.** The nearest pool / FVG sits only ≈1.4–1.7 ATR above entry, so 90–98 % of trades exit early: −13 to −20 pp per covered trade for ½ exits, −25 to −40 pp for full exits (q ≤0.02, robust to dropping the top-3 coins). HVN stops (≈1.5 ATR) are also worse (−10.5 pp close, −13.5 pp intraday; robust at q 0.05 intraday). Pool stops: −3.4 pp, not significant. OB stops: +4.9 pp on 117 trades, p 0.19, noise.

**What this means for the scanner**
* Keep every geometry / volume-profile / candle / liquidity column at **weight 0** (logging only). Spiral, Gann, all 26 candle patterns and the sweep columns (either kind) show nothing.
* **Do not** use liquidity pools, FVGs, order blocks or HVNs as stops or take-profits instead of the active policy; for crypto they are clearly worse.
* The only thing to watch on new setups from 12.10.2026: **stock shorts whose close is below the 120-day value area** (vp120_va_pos = "below VA"), as a possible tightening of the existing short rule. Needs ≈30 closed new trades before any weight.
* Caveats: in-sample, ≈3½ months, 22–25 stock entry dates, most stock trades still open (marked 2026-10-07); clustering-robust p-values are themselves approximate with this few dates.
