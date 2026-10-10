import pickle
P=pickle.load(open('out/report_parts.pkl','rb'))
lt,lp=P['lt'],P['lp']; le=P['le']; eq=P['eq']
R=f"""# Backtest of open-source TA repos: TA-Lib, pandas-ta, smart-money-concepts and three Elliott Wave repos

Date: 2026-10-08. Work dir: `/workspace/ta-repos-eval/` (own venv; nothing was installed on Ilan's laptop; no overlap with `/workspace/gh-repos-eval`).
Inputs were read-only: `/workspace/tracker/setups-point-in-time-2026-10-08.csv`, `hold-no-stop-longs-2026-10-08.csv`, the PIT cutoffs (`rule_bar_actual`) and the active-policy trades from `/workspace/trading-frameworks-eval` (§3.14). Nothing in those files was modified.

## TL;DR

* **Comparisons run:** {P['flags']['noise']+P['flags']['nominal p<0.05 only (fails FDR)']+P['flags']['ROBUST']}, all in one BH-FDR family; 894 more were skipped because N<20 on a side.
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
| TA-Lib 0.8.1 (ta-lib-python) | BSD-2 (wrapper), BSD (C lib) | **Clean.** 0 leaks in {lt[0]} output columns × {lt[1]} setups. The 3 flagged columns are inf overflow in COSH/EXP/SINH. | 100% | 2 robust short filters (SMA200 distance), redundant with the existing lead. Candles: 0 of 53 nominally significant. | **Adopt only as a calculator** (fast, correct, stable). Score weight 0. |
| pandas-ta 0.4.71b0 | MIT | Mostly clean. **12 of {lp[0]} columns use future bars:** DPO (centred by default), Ichimoku chikou, TOS_STDEVALL (7 columns) and ZIGZAG (repaints). Its candle patterns call TA-Lib. | 100% | 1 robust short filter (Connors RSI), redundant. | **Adopt with caveats:** blacklist DPO/chikou/TOS_STDEVALL/ZIGZAG. The original GitHub repo returns 404 now; the PyPI package and pandas-ta.dev site are alive. Score weight 0. |
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
* **Statistics:** one BH family over all {P['flags']['noise']+P['flags']['nominal p<0.05 only (fails FDR)']+P['flags']['ROBUST']} executed comparisons, q<0.10, N≥20 on each side.
  * **ROBUST** means the median, the raw (non-excess) result, the within-date result, and the results without the top-1 and top-3 tickers all keep the same sign.
  * A result that passes FDR but fails these checks is labelled LUCK. There were 0 LUCK results.

## 2. Leak and repaint checks

The three-way test compares three versions at the cutoff: T = history truncated at the cutoff; F = full history, read at the cutoff; J = garbage bars appended after the cutoff. Any F≠T or J≠T at or before the cutoff counts as a leak or repaint.

### TA-Lib ({lt[0]} output columns × {lt[1]} setups)
Columns with any difference:

{lt[2]}

These are inf/overflow in the math transforms, not leaks. **TA-Lib is clean.**

### pandas-ta ("All" study, {lp[0]} columns × {lp[1]} setups)
Columns that leak or repaint:

{lp[2]}

None of these was used as a feature. Chikou was excluded from the Ichimoku features.

### smart-money-concepts (30 setups): setups where the output changes when it is run on full data (F) or with junk future bars (J)

{P['ls']}

* `last_bar` counts setups where smc stamps an artificial swing on the last bar. This happens on 100% of the 787 setups with features, and the wrapper removes it.
* `max_bars_back` is how far before the cutoff the earliest difference appears. The mitigation and sweep indices of objects up to ~430 bars old depend on the future.
* J≠T in every setup because the liquidity range is 1% of the full series' range, and because the mitigated/broken indices are searched forward.
* **Conclusion:** smc on full data is unusable for backtests. The PIT wrapper (`features_smc.py`) fixes this.

### Elliott adapters (30 setups)

| Check | Result |
|---|---|
| python-taew: full series has a pivot on the cutoff bar (1-bar look-ahead) | {le['taew_F_pivot_on_cut_bar']}/30 |
| python-taew: pivots missing in F | {le['taew_missing_in_F']}/30 |
| ElliottWaves raw: provisional pivots that later vanish / pivots that appear only later | {le['ar_raw_provisional']}/30 / {le['ar_raw_missing']}/30 |
| ElliottWaves after dropping the last 7 bars = full series | {le['ar_conf_equal']}/30 |
| ElliottWaveAnalyzer: last wave unconfirmed / chain changes with future bars | {le['ewa_last_wave_unconfirmed']}/30 / {le['ewa_chain_changes_with_future']}/30 |
| Junk-future determinism (all adapters) | {le['junk_mismatch']} mismatches in {le['junk_values']} values |
| My pruned DFS vs the repo's brute force (ElliottWaves) | {eq[1]}/{eq[0]} identical result sets |

## 3. Comparisons by family

{P['fam']}

Flags across the whole family: {P['flags']}.

## 4. Survivors (q<0.10)

{P['surv']}

* **Do the short survivors add anything?** This is a descriptive check (`shorts_check.py`), not part of the FDR family.
  * SMA200-distance Q5 overlaps vp120-below-VA in 30 of 38 shorts, and 37 of 38 already pass the short rule.
  * Connors RSI Q5 overlaps VA-below in 19 of 38 and the rule in 32 of 38. Within rule-passing shorts its effect is not significant (p=0.16, date-clustered).
  * **Verdict:** both re-express "already breaking down" and add nothing beyond the existing lead.
* **For the level survivors, diff_raw is the paired per-trade return difference vs the active policy** (raw, not excess).
  * The FVG and taew targets sit at a median of 3–4 ATR and are hit by 70–87% of trades.
  * Hitting them caps crypto winners that the 3×ATR fixed stop lets run.

## 5. Closest misses (nominal p<0.05, fail FDR); top 30 by p

{P['miss']}

These follow the same pattern as §3.14:
* Shorts look better when they are already stretched down: momentum 12-1 Q5, ULTOSC, RSI, ADX, squeeze momentum.
* Stock longs look worse when they are stretched or trending hard: high ADX, MACD, distance above SMA50, high STC.
* Tighter crypto stops do worse.

None is FDR-significant, so none should be used.

## 6. Level tests (top 22 by p; close-based, paired vs active policy)

{P['lev']}

* **No stop or target from smc or any Elliott repo beats the active policy in any segment.**
* On stocks the level rules are noise. On crypto, both tighter stops and earlier targets are worse.

## 7. Reference: momentum 12-1 in the same framework

{P['ref']}

* Momentum 12-1 does not separate stock longs in this sample.
* Its only nominal effect is on shorts (Q5 +7.1 pp, q=0.15), which is the same "breaking down" factor.

## 8. Elliott filters (top 15 by p)

{P['ewf']}

## 9. Agreement tables

### TA-Lib candles vs scanner_geometry (695 setups, pattern on the cutoff bar)

{P['agree_candles']}

* Agreement is good on simple single-candle shapes: marubozu, doji, spinning top.
* It is poor on context-dependent patterns (hammer, hanging man, shooting star, morning star, piercing). Each implementation defines the "trend" context differently.
* The candles add no edge either way: TA-Lib candles had 0 of 53 nominally significant comparisons, which matches the §3.14 candle result.

### smc vs scanner_geometry

{P['agree_smc_geo']}

smc flags many more order blocks than the module (73% of setups vs 39–44%), and its liquidity pools hardly overlap.

### Elliott coverage (% of setups with each state)

{P['ew_coverage']}

### Elliott agreement with our count

{P['ew_agreement']}

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
"""
open('results.md','w').write(R); print(len(R))
