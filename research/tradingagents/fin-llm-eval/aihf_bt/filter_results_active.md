### ai-hedge-fund `druckenmiller` (blind persona, EDGAR PIT, Qwen2.5-3B on the box)

N = 60 stock setups with an active-policy trade (0 without one). Leak check: 0 setups used data dated after the cutoff. Median runtime 23s/setup on the box CPU; LLM tokens per setup (1 call): median prompt 1219, output 122. Abstained/failed: CLM, INTR, MNDY, PNR, QQQ, SPY, SRAD, STNE, TME.

Verdict counts (approve = agrees with the setup direction, veto = opposes):

| side | approve | neutral | veto | abstain |
|---|---|---|---|---|
| LONG | 0 | 24 | 3 | 4 |
| SHORT | 0 | 21 | 3 | 5 |
| ALL | 0 | 45 | 6 | 9 |

**ALL** (active policy, % per trade):

| group | N | entry_days | mean | median | hit | x_spy_mean | x_spy_median | open_share |
|---|---|---|---|---|---|---|---|---|
| all setups (no filter) | 60 | 17 | 1.48 | 1.01 | 56.67 | 1.35 | 0.73 | 83.33 |
| neutral | 45 | 16 | 0.87 | -0.33 | 48.89 | 0.73 | -0.43 | 82.22 |
| veto | 6 | 6 | 1.10 | 3.54 | 66.67 | 1.10 | 3.82 | 83.33 |
| abstain | 9 | 6 | 4.78 | 4.53 | 88.89 | 4.66 | 4.71 | 88.89 |
| veto filter: keep all but vetoed | 54 | 16 | 1.52 | 0.73 | 55.56 | 1.38 | 0.68 | 83.33 |

p (Mann-Whitney, return): vetoed vs rest 0.57; approved vs rest n/a (<3); neutral vs abstain 0.09. Unfiltered x SPY > 0, Wilcoxon p 0.33.

**LONG** (active policy, % per trade):

| group | N | entry_days | mean | median | hit | x_spy_mean | x_spy_median | open_share |
|---|---|---|---|---|---|---|---|---|
| all setups (no filter) | 31 | 14 | 2.43 | 0.47 | 58.06 | 1.16 | -0.97 | 77.42 |
| neutral | 24 | 13 | 1.66 | -0.18 | 50.00 | 0.35 | -2.20 | 75.00 |
| veto | 3 | 3 | -0.17 | 4.83 | 66.67 | -1.48 | 3.77 | 66.67 |
| abstain | 4 | 3 | 9.01 | 2.24 | 100.00 | 8.04 | 0.95 | 100.00 |
| veto filter: keep all but vetoed | 28 | 13 | 2.71 | 0.42 | 57.14 | 1.45 | -1.01 | 78.57 |

p (Mann-Whitney, return): vetoed vs rest 0.83; approved vs rest n/a (<3); neutral vs abstain 0.10. Unfiltered x SPY > 0, Wilcoxon p 0.82.

**SHORT** (active policy, % per trade):

| group | N | entry_days | mean | median | hit | x_spy_mean | x_spy_median | open_share |
|---|---|---|---|---|---|---|---|---|
| all setups (no filter) | 29 | 13 | 0.46 | 2.24 | 55.17 | 1.56 | 2.73 | 89.66 |
| neutral | 21 | 11 | -0.04 | -0.33 | 47.62 | 1.16 | 1.70 | 90.48 |
| veto | 3 | 3 | 2.38 | 2.24 | 66.67 | 3.67 | 3.88 | 100.00 |
| abstain | 5 | 4 | 1.39 | 6.39 | 80.00 | 1.95 | 6.89 | 80.00 |
| veto filter: keep all but vetoed | 26 | 13 | 0.24 | 1.77 | 53.85 | 1.31 | 2.56 | 88.46 |

p (Mann-Whitney, return): vetoed vs rest 0.87; approved vs rest n/a (<3); neutral vs abstain 0.28. Unfiltered x SPY > 0, Wilcoxon p 0.09.

Directional calls: MU LONG -> veto (+19.0%, x SPY +18.7); MU LONG -> veto (+4.8%, x SPY +3.8); CHTR SHORT -> veto (+7.7%, x SPY +8.8); TSLA SHORT -> veto (-2.8%, x SPY -1.6); LCID LONG -> veto (-24.4%, x SPY -26.9); VRT SHORT -> veto (+2.2%, x SPY +3.9)

### ai-hedge-fund `buffett` (blind persona, EDGAR PIT, Qwen2.5-3B on the box)

N = 60 stock setups with an active-policy trade (0 without one). Leak check: 0 setups used data dated after the cutoff. Median runtime 24s/setup on the box CPU; LLM tokens per setup (1 call): median prompt 1099, output 136. Abstained/failed: CLM, INTR, MNDY, QQQ, SPY, SRAD, STNE, TME.

Verdict counts (approve = agrees with the setup direction, veto = opposes):

| side | approve | neutral | veto | abstain |
|---|---|---|---|---|
| LONG | 0 | 27 | 0 | 4 |
| SHORT | 1 | 24 | 0 | 4 |
| ALL | 1 | 51 | 0 | 8 |

**ALL** (active policy, % per trade):

| group | N | entry_days | mean | median | hit | x_spy_mean | x_spy_median | open_share |
|---|---|---|---|---|---|---|---|---|
| all setups (no filter) | 60 | 17 | 1.48 | 1.01 | 56.67 | 1.35 | 0.73 | 83.33 |
| approve | 1 | 1 | -0.33 | -0.33 | 0.00 | 0.73 | 0.73 | 100.00 |
| neutral | 51 | 17 | 1.09 | 0.38 | 52.94 | 0.97 | 0.42 | 82.35 |
| abstain | 8 | 5 | 4.22 | 3.42 | 87.50 | 3.88 | 2.94 | 87.50 |
| veto filter: keep all but vetoed | 60 | 17 | 1.48 | 1.01 | 56.67 | 1.35 | 0.73 | 83.33 |

p (Mann-Whitney, return): vetoed vs rest n/a (<3); approved vs rest n/a (<3); neutral vs abstain 0.24. Unfiltered x SPY > 0, Wilcoxon p 0.33.

**LONG** (active policy, % per trade):

| group | N | entry_days | mean | median | hit | x_spy_mean | x_spy_median | open_share |
|---|---|---|---|---|---|---|---|---|
| all setups (no filter) | 31 | 14 | 2.43 | 0.47 | 58.06 | 1.16 | -0.97 | 77.42 |
| neutral | 27 | 14 | 1.46 | 0.05 | 51.85 | 0.14 | -2.02 | 74.07 |
| abstain | 4 | 3 | 9.01 | 2.24 | 100.00 | 8.04 | 0.95 | 100.00 |
| veto filter: keep all but vetoed | 31 | 14 | 2.43 | 0.47 | 58.06 | 1.16 | -0.97 | 77.42 |

p (Mann-Whitney, return): vetoed vs rest n/a (<3); approved vs rest n/a (<3); neutral vs abstain 0.14. Unfiltered x SPY > 0, Wilcoxon p 0.82.

**SHORT** (active policy, % per trade):

| group | N | entry_days | mean | median | hit | x_spy_mean | x_spy_median | open_share |
|---|---|---|---|---|---|---|---|---|
| all setups (no filter) | 29 | 13 | 0.46 | 2.24 | 55.17 | 1.56 | 2.73 | 89.66 |
| approve | 1 | 1 | -0.33 | -0.33 | 0.00 | 0.73 | 0.73 | 100.00 |
| neutral | 24 | 11 | 0.67 | 1.67 | 54.17 | 1.90 | 2.56 | 91.67 |
| abstain | 4 | 3 | -0.58 | 5.46 | 75.00 | -0.28 | 5.80 | 75.00 |
| veto filter: keep all but vetoed | 29 | 13 | 0.46 | 2.24 | 55.17 | 1.56 | 2.73 | 89.66 |

p (Mann-Whitney, return): vetoed vs rest n/a (<3); approved vs rest n/a (<3); neutral vs abstain 0.68. Unfiltered x SPY > 0, Wilcoxon p 0.09.

Directional calls: HPQ SHORT -> approve (-0.3%, x SPY +0.7)

### Druckenmiller vs Buffett agreement

| druckenmiller | abstain | approve | neutral |
|---|---|---|---|
| abstain | 8 | 0 | 1 |
| neutral | 0 | 1 | 44 |
| veto | 0 | 0 | 6 |

### Context: the full stock universe under the same policy (the 60 are the first 60 stock rows of the stratified sample)

| set | N | entry_days | mean | median | hit | x_spy_mean | x_spy_median | open_share |
|---|---|---|---|---|---|---|---|---|
| all stock setups in the main sheet, ALL | 431 | 25 | 1.38 | 0.02 | 50.12 | 1.25 | -0.43 | 84.22 |
| all stock setups in the main sheet, LONG | 242 | 25 | 2.95 | 0.44 | 54.55 | 1.66 | -0.97 | 83.06 |
| all stock setups in the main sheet, SHORT | 189 | 22 | -0.63 | -1.24 | 44.44 | 0.72 | -0.14 | 85.71 |

### TradingAgents completed setups (Qwen2.5-3B on the box; anecdotal only)

- HD SHORT (2026-09-23): **Underweight** -> approve; active-policy outcome +3.3% (x SPY +5.0, open@end); 28 min, 14 LLM calls, 41,085 prompt / 5,904 output tokens
