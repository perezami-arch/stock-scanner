# S/R levels + volume waves - quick point-in-time sanity check (08.10.2026)

Not the FDR backtest. The researcher runs that on the 846 setups. All columns stay weight 0.

**Data.** Tracker setups from /workspace/scanner-tool-eval/setups_prepared.csv, US stocks only. The counted base drops MCAP<1.5B
and duplicates: **N = 439 setups (246 LONG, 193 SHORT) on 27 distinct cutoff days.** 489 setups had price data in total.
- History: each setup is cut point-in-time at asof_ts with scanner_geometry.pit_cut. Outcomes use only the bars after the cutoff bar.
- Prices: Yahoo daily, auto_adjust, same as the scanner.
- S/R: scanner_levels.levels_for(..., 'SWING') on the cut history. Waves: scanner_waves.waves_columns on the last 480 cut bars (scanner length).
- "Strong" level = strength >= 0.5 x the strongest of that setup's top levels.
- Stop / target hits: intraday H/L within 20 bars. If stop and target fall in the same bar, the stop counts first.
- Stop-outs for waves use sim_chand_trades.csv chand4_c (the active 4xATR chandelier).
- x20 (day-20 excess return) exists for only 139 of 439 setups.
- p-values come from a day-clustered bootstrap. **No multiple-testing correction** (21 tests): treat p < 0.05 as a hint, not a finding.

## S/R
| test | yes: N (days) / mean | no: N (days) / mean | diff | p |
|---|---|---|---|---|
| Tracker stop placed beyond a strong level -> stop hit <= 20 bars | 139 (23) / 41.7% | 232 (23) / 45.7% | -4.0 pp | 0.66 |
| same -> tracker stop/tp1 trade return | 139 / +0.19% | 232 / +0.93% | -0.73 pp | 0.42 |
| same -> x20 | 44 (10) / +7.3% | 55 (11) / +4.3% | +3.0 pp | 0.65 |
| Strong level between entry and tp1 -> tp1 hit <= 20 bars | 162 (24) / 24.7% | 206 (22) / 34.5% | -9.8 pp | 0.08 |
| same -> x20 | 44 / +5.8% | 55 / +5.5% | +0.4 pp | 1.0 |

**Paired test, capping the target at the strong level before tp1 (cap = level - 0.1 ATR), same 162 setups, 24 days:**
- The cap raises the hit rate from 24.7% to 51.9%.
- But the mean trade return falls from +1.25% to -0.27% (diff -1.52 pp, 95% CI [-2.7, -0.7] pp, day-bootstrap p < 0.001).
- LONG: N=93, +1.66% -> -0.23%. SHORT: N=69, +0.71% -> -0.31%.

Reading:
- A strong level in the way does go with fewer tp1 hits (borderline).
- Taking profit early at that level gave up more than it saved. **Do not cap targets at S/R.**
- Stops placed beyond a strong level showed no measurable benefit.

## Volume waves / divergences (direction view = the setup's direction)
| flag | rate | chand4 stopped yes vs no | p | x20 yes vs no | p |
|---|---|---|---|---|---|
| wave_end_signal (any reason) | ~89% of setups | 16.2% (382) vs 10.6% (47) | 0.41 | +4.9% (129) vs +2.0% (10) | 0.60 |
| wave_start_signal | | 12.7% (315) vs 23.7% (114) | 0.13 | +5.9% (93) vs +2.3% (46) | 0.14 |
| wz_exhaustion_with (zigzag, new extreme on less volume) | | 12.7% (55) vs 16.0% (374) | 0.59 | +1.6% (17) vs +5.1% (122) | 0.62 |
| ww_exhaustion_with (classic Weis 3%) | | 23.1% (78) vs 14.0% (351) | 0.30 | -0.7% (30) vs +6.2% (109) | 0.07 |
| wz_counter_gt_with | | 16.8% (250) vs 14.0% (179) | 0.62 | +4.4% vs +5.2% | 0.74 |
| ww_counter_gt_with | | 14.0% (264) vs 18.2% (165) | 0.57 | +5.0% vs +4.0% | 0.75 |
| fresh RSI/CCI divergence against the trade | | 14.0% (129) vs 16.3% (300) | 0.73 | +5.7% vs +4.3% | 0.63 |

Reading:
- **wave_end_signal as built (OR of many reasons) fires on ~90% of setups, so it can't discriminate.** Use the single flags, or a count threshold (wave_end_n).
- The only hint is classic-Weis with-wave exhaustion: more stop-outs (+9 pp) and worse x20 (-6.9 pp, p = 0.07, N = 30 with x20). It is not significant and has no FDR correction.
- Nothing here justifies weight > 0.

Files: bt.py, analyze.py, bt_rows.csv, results_table.csv, h2_paired.csv.
Lookups: /workspace/tracker/sr_levels_lookup.csv and /workspace/tracker/volume_waves_lookup.csv (489 rows each, keyed by setup_id).
