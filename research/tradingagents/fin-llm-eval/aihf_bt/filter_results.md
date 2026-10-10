### ai-hedge-fund `druckenmiller` persona (blind, EDGAR PIT, Qwen2.5-3B)

N = 60 with outcomes (0 without a simulated trade: no price data / excluded).

| verdict | n | hold_mean | hold_median | hold_x_mkt | chand4_mean | chand4_median | win_rate |
|---|---|---|---|---|---|---|---|
| abstain | 9.00 | 5.45 | 4.53 | 5.37 | 5.42 | 4.53 | 88.89 |
| neutral | 45.00 | 0.23 | -0.58 | -0.02 | 0.36 | -0.58 | 44.44 |
| veto | 6.00 | -2.60 | 3.54 | -2.87 | 1.10 | 3.54 | 66.67 |
| ALL (no filter) | 60.00 | 0.73 | 0.42 | 0.50 | 1.19 | 0.42 | 53.33 |

Without the best ticker (SMCI):

| verdict | n | hold_mean | hold_median | hold_x_mkt | chand4_mean | chand4_median | win_rate |
|---|---|---|---|---|---|---|---|
| abstain | 9.00 | 5.45 | 4.53 | 5.37 | 5.42 | 4.53 | 88.89 |
| neutral | 43.00 | -1.27 | -0.70 | -1.42 | -1.14 | -0.70 | 41.86 |
| veto | 6.00 | -2.60 | 3.54 | -2.87 | 1.10 | 3.54 | 66.67 |

LONG only:

| verdict | n | hold_mean | hold_median | hold_x_mkt | chand4_mean | chand4_median | win_rate |
|---|---|---|---|---|---|---|---|
| abstain | 4.00 | 10.45 | 2.18 | 9.48 | 10.45 | 2.18 | 100.00 |
| neutral | 24.00 | 0.05 | -1.41 | -1.60 | 0.71 | -1.41 | 41.67 |
| veto | 3.00 | -7.59 | 4.83 | -9.41 | -0.17 | 4.83 | 66.67 |

SHORT only:

| verdict | n | hold_mean | hold_median | hold_x_mkt | chand4_mean | chand4_median | win_rate |
|---|---|---|---|---|---|---|---|
| abstain | 5.00 | 1.45 | 6.39 | 2.08 | 1.39 | 6.39 | 80.00 |
| neutral | 21.00 | 0.44 | -0.33 | 1.78 | -0.04 | -0.33 | 47.62 |
| veto | 3.00 | 2.38 | 2.24 | 3.67 | 2.38 | 2.24 | 66.67 |

Verdict counts: {'neutral': 45, 'abstain': 9, 'veto': 6}. Leak check: 0 setups used any filing/price dated after the cutoff (every snapshot input dated <= trade_date: 100%). Runtime/setup: median 23s; LLM tokens median prompt 1219, output 122.


### ai-hedge-fund `buffett` persona (blind, EDGAR PIT, Qwen2.5-3B)

N = 60 with outcomes (0 without a simulated trade: no price data / excluded).

| verdict | n | hold_mean | hold_median | hold_x_mkt | chand4_mean | chand4_median | win_rate |
|---|---|---|---|---|---|---|---|
| abstain | 8.00 | 4.97 | 3.36 | 4.68 | 4.94 | 3.36 | 87.50 |
| approve | 1.00 | -0.33 | -0.33 | 0.73 | -0.33 | -0.33 | 0.00 |
| neutral | 51.00 | 0.09 | -0.40 | -0.16 | 0.64 | -0.40 | 49.02 |
| ALL (no filter) | 60.00 | 0.73 | 0.42 | 0.50 | 1.19 | 0.42 | 53.33 |

Without the best ticker (SMCI):

| verdict | n | hold_mean | hold_median | hold_x_mkt | chand4_mean | chand4_median | win_rate |
|---|---|---|---|---|---|---|---|
| abstain | 8.00 | 4.97 | 3.36 | 4.68 | 4.94 | 3.36 | 87.50 |
| approve | 1.00 | -0.33 | -0.33 | 0.73 | -0.33 | -0.33 | 0.00 |
| neutral | 49.00 | -1.24 | -0.58 | -1.39 | -0.67 | -0.58 | 46.94 |

LONG only:

| verdict | n | hold_mean | hold_median | hold_x_mkt | chand4_mean | chand4_median | win_rate |
|---|---|---|---|---|---|---|---|
| abstain | 4.00 | 10.45 | 2.18 | 9.48 | 10.45 | 2.18 | 100.00 |
| neutral | 27.00 | -0.80 | -1.23 | -2.47 | 0.61 | -1.23 | 44.44 |

SHORT only:

| verdict | n | hold_mean | hold_median | hold_x_mkt | chand4_mean | chand4_median | win_rate |
|---|---|---|---|---|---|---|---|
| abstain | 4.00 | -0.50 | 5.46 | -0.13 | -0.58 | 5.46 | 75.00 |
| approve | 1.00 | -0.33 | -0.33 | 0.73 | -0.33 | -0.33 | 0.00 |
| neutral | 24.00 | 1.08 | 1.67 | 2.44 | 0.67 | 1.67 | 54.17 |

Verdict counts: {'neutral': 51, 'abstain': 8, 'approve': 1}. Leak check: 0 setups used any filing/price dated after the cutoff (every snapshot input dated <= trade_date: 100%). Runtime/setup: median 24s; LLM tokens median prompt 1099, output 136.


### TradingAgents full multi-agent (Qwen2.5-3B, market+fundamentals analysts, 1 debate + 1 risk round)

N = 1 with outcomes (0 without a simulated trade: no price data / excluded).

| verdict | n | hold_mean | hold_median | hold_x_mkt | chand4_mean | chand4_median | win_rate |
|---|---|---|---|---|---|---|---|
| approve | 1.00 | 3.32 | 3.32 | 5.04 | 3.32 | 3.32 | 100.00 |
| ALL (no filter) | 1.00 | 3.32 | 3.32 | 5.04 | 3.32 | 3.32 | 100.00 |

Per setup: HD SHORT -> Underweight (28 min, 14 calls, 41085 prompt / 5904 output tok)
