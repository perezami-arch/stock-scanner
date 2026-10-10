# VA120 under the directional excess convention: historical rerun (08.10.2026)

**Convention (decided by שוק ההון on 08.10):** excess = direction × (stock return − SPY return), with direction = +1 for LONG and −1 for SHORT. For a short this is SPY − stock, the same as comparing it with being short SPY. Horizon: day 20.

## Where the old +5.61% / +2.86% came from
- **Source:** the build7 column `excess_spy_d20` (stock − SPY, applied to shorts as well). The snapshot is in `build7_snapshot_2026-10-08_1623.xlsx`, copied from the build7 test build `/tmp/tracker-test-fund.xlsx`.
- **Population:** stock SHORT rows that have `watch_short_below_va120` from `tracker/watch_short_below_va120_lookup.csv` and a complete day 20. Flag = 1: N=12 (10 tickers, 6 entry dates). Flag = 0: N=13. Duplicates marked "לא נספר" are excluded.
- **Reproduction:** recomputing from the snapshot gives exactly +5.61% vs +2.86%. The 25 rows, with both conventions, are in `va120_directional_rows.csv`.
- **Benchmark:** SPY price-return closes from `tracker/prices_all.pkl`, the same series build7 uses. Base = last close before day 1; day 20 = the 20th session on or after the alert date.

## Result (stock SHORT, same 25 rows)

| | old (build7 `excess_spy_d20`) | **directional (`excess_dir_d20`)** |
|---|---|---|
| N flagged / unflagged | 12 / 13 | 12 / 13 |
| Mean excess, flagged (below VA120) | +5.61% | **+4.37%** |
| Mean excess, unflagged | +2.86% | **+3.02%** |
| Median, flagged / unflagged | +7.63% / −0.06% | +6.04% / +1.15% |
| Hit rate (excess > 0), flagged / unflagged | 83% / 46% | 83% / 62% |
| **Difference (flagged − unflagged)** | +2.75 pp | **+1.35 pp** |
| 95% CI (widest of ticker / date / two-way clustered SE, df = 6) | [−6.5, +12.0] | **[−7.8, +10.5]** |
| p (ticker / date / two-way) | 0.49 / 0.44 / 0.47 | 0.73 / 0.67 / 0.67 |
| **p used (max)** | 0.49 | **0.73** |
| Diff after dropping top-1 / top-3 tickers | +1.8 / +0.4 pp | +0.8 / −1.1 pp |
| Clusters: tickers / dates | 22 / 7 | 22 / 7 |
| BH-FDR q<0.10 | not testable (fewer than 20 per side) | **not testable (fewer than 20 per side)** |
| q if forced into the 246-test family (247 tests) | 0.95 | 0.99 |

**Why the difference narrows:**
- The flagged group is concentrated on 15–16.08 entries, when SPY fell 2% over the following 20 sessions. Under the old convention, subtracting a negative SPY return inflated those shorts.
- The directional convention compares each short with being short SPY, which removes that inflation.
- The flagged-group mean falls 1.2 pp and the gap halves.

**Verdict:**
- No evidence. The difference is positive but far from significant (p=0.73), and it flips sign once the top-3 tickers are dropped.
- The sample is small: 12 flagged rows on 6 dates.
- VA120 stays watch-only at weight 0, under the out-of-sample rule (15 = interim check, 30 = decision).

**Other segment:** the tool_stats "ALL" segment shows 12/15, which adds 2 LONG rows. These receive flag 0 because the lookup CSV has no direction column. Under the directional convention it gives +4.37% vs +2.36%, diff +2.0 pp, CI [−6.6, +10.6], p=0.59. The stock SHORT segment is the meaningful comparison.

## Full historical baseline (tool_stats, 846-row PIT tracker, since 01.07)

**Inputs:**
- Tracker: `scan-tracker-2026-10-08-pit.xlsx`.
- Extras: `research-models/backfill/rc_backfill_setups.csv`, `tracker/watch_short_below_va120_lookup.csv` and `tracker/fundamentals_pit_lookup.csv`.
- No ledger.

| | before (v2026-10-08.1, 16:19) | after (v2026-10-08.2) |
|---|---|---|
| Tests / testable (20+ per side) | 368 / 246 | 368 / 246 |
| FDR survivors (q<0.10) | 0 | **0** |
| Minimum q | 0.821 | 0.831 |
| Strongest test | exp_talib_roc10 >= median, p≈0.010 | exp_talib_roc10 >= median, p=0.0099 (q 0.83) |
| Max change in any diff | | 0.16 pp (N unchanged everywhere) |

**Nothing changes.**
- tool_stats already used the directional convention (`ret − sgn × bench`).
- The only numeric drift comes from the benchmark-source alignment below. Version .1 used yfinance auto-adjusted (total-return) SPY. Version .2 uses `prices_all.pkl` (price-return, identical to build7). They differ by the ~0.25% September SPY dividend for windows that span the ex-date.
- Crypto rows are unchanged.

## Changes to tool_stats.py (v2026-10-08.2; backup `tool_stats.py.bak-2026-10-08-pre-excessdir`)
1. **Column preference at day 20.**
   - The day-20 excess uses the tracker column `excess_dir_d20` where it is filled.
   - Otherwise it falls back to `ret_d20 − sgn × bench_d20`, which is the same formula.
   - A new per-row column, `excess_src_d20`, records which source was used. The meta JSON now carries `excess_d20_source` counts.
   - The Hebrew build7 header "תשואה עודפת מכוונת מול SPY ביום 20 (…)" maps to `excess_dir_d20`.
   - The old `excess_spy_d20` is never used.
2. **Benchmark source.** `tracker/prices_all.pkl` closes are used first, and yfinance only extends past their last date. This makes the fallback numerically identical to build7's `excess_dir_d20`.
3. **Tests.**
   - New `research-models/tests/test_tool_stats_excess.py` covers fallback, column preference, a blank-cell fallback and the header mapping. Run it with plain python; it is also pytest-compatible. All 4 pass.
   - Synthetic-tracker rerun (min_side=5): 29 tests, 28 testable, 0 survivors, p and q identical to 1e-7.

Rerun outputs are in `research-models/tool_stats/rerun_excessdir/{backfill,hist,synth}/`. The current PIT tracker has no `excess_dir_d20` column yet, so all 472 day-20 results in those reruns were computed with the fallback formula.
