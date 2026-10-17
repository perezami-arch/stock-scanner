# Pivots / confluence / volume phase — backtest per PREREG.md

Setups evaluated: {'n': 822, 'n_zone': 705, 'V1_stop': np.float64(0.44386422976501305), 'V2_stop': np.float64(0.512280701754386), 'base_stop': np.float64(0.1256544502617801), 'V2_skip': np.float64(0.4269503546099291), 'V1_triggered': np.float64(0.4666666666666667), 'V2_delay': np.float64(2.0)}

## Feature tests (excess_dir vs SPY/BTC, controls dir×mom12-1 + crypto, clustered by date)

|   h | flag               |   n |   n_flag |   dates_flag |   mean_flag |   mean_rest |    coef |   p_incr |   wf_h1 |   wf_h2 |   coef_no_top5 |      q | graduate   |
|----:|:-------------------|----:|---------:|-------------:|------------:|------------:|--------:|---------:|--------:|--------:|---------------:|-------:|:-----------|
|   5 | F1_at_support      | 822 |      655 |           62 |      0.0051 |      0.0076 | -0.0028 |   0.7908 | -0.0409 |  0.0079 |         0.0069 | 0.9226 | False      |
|   5 | F2_blocked         | 822 |      592 |           62 |      0.0085 |     -0.0019 |  0.0108 |   0.042  |  0.0242 |  0.003  |         0.0058 | 0.2654 | False      |
|   5 | F3_support_weekly  | 822 |      616 |           62 |      0.0055 |      0.0058 | -0.0001 |   0.9954 | -0.0162 |  0.0072 |         0.007  | 0.9954 | False      |
|   5 | F4_phase_aligned   | 822 |      441 |           62 |      0.0111 |     -0.0008 |  0.012  |   0.0577 |  0.0007 |  0.0188 |         0.0028 | 0.2654 | False      |
|   5 | F5_w_phase_aligned | 822 |      404 |           61 |      0.002  |      0.0091 | -0.0073 |   0.1925 | -0.0108 | -0.0059 |        -0.003  | 0.4492 | False      |
|   5 | F6_cmf_aligned     | 822 |      400 |           60 |      0.0091 |      0.0023 |  0.0069 |   0.2748 | -0.0188 |  0.022  |         0.0101 | 0.5359 | False      |
|   5 | F7_timing_combo    | 822 |      149 |           48 |     -0.0042 |      0.0078 | -0.0122 |   0.0339 | -0.0305 | -0.0015 |        -0.0076 | 0.2654 | False      |
|  20 | F1_at_support      | 665 |      542 |           57 |      0.0167 |      0.0191 | -0.0024 |   0.9096 | -0.0544 |  0.0182 |         0.0085 | 0.9795 | False      |
|  20 | F2_blocked         | 665 |      487 |           57 |      0.0222 |      0.0034 |  0.0198 |   0.0758 |  0.0389 | -0.0009 |         0.0095 | 0.2654 | False      |
|  20 | F3_support_weekly  | 665 |      503 |           57 |      0.0208 |      0.0059 |  0.0152 |   0.3844 |  0.0126 |  0.0156 |         0.0166 | 0.5359 | False      |
|  20 | F4_phase_aligned   | 665 |      355 |           57 |      0.0115 |      0.0237 | -0.0123 |   0.4211 | -0.0568 |  0.0243 |        -0.0171 | 0.5359 | False      |
|  20 | F5_w_phase_aligned | 665 |      333 |           56 |      0.0111 |      0.0233 | -0.0122 |   0.3711 | -0.0335 |  0.0035 |        -0.0151 | 0.5359 | False      |
|  20 | F6_cmf_aligned     | 665 |      321 |           55 |      0.0085 |      0.0253 | -0.0169 |   0.1617 | -0.0485 |  0.011  |        -0.0005 | 0.4492 | False      |
|  20 | F7_timing_combo    | 665 |      118 |           39 |      0.0064 |      0.0195 | -0.0136 |   0.4176 | -0.0384 |  0.0053 |        -0.0027 | 0.5359 | False      |

## Entry-timing simulation (setups with a weekly confluence zone; paired vs next-open)

| variant   | metric   |   n |   dates |   timed |   base |    diff |      p |      q |
|:----------|:---------|----:|--------:|--------:|-------:|--------:|-------:|-------:|
| V1        | x5       | 552 |      62 |  0.0038 | 0.0154 | -0.0115 | 0.0003 | 0.0009 |
| V1        | x20      | 383 |      54 |  0.0272 | 0.0342 | -0.007  | 0.1455 | 0.1746 |
| V1        | R        | 383 |      54 |  1.2767 | 0.6297 |  0.647  | 0.0066 | 0.0099 |
| V2        | x5       | 402 |      61 |  0.0008 | 0.0125 | -0.0117 | 0.0001 | 0.0004 |
| V2        | x20      | 285 |      53 |  0.0201 | 0.0248 | -0.0047 | 0.2898 | 0.2898 |
| V2        | R        | 285 |      53 |  1.4711 | 0.6041 |  0.8669 | 0.0027 | 0.0054 |

## Verdict (16.10.2026) — nothing graduates; all columns stay weight 0
- Feature tests: 0/14 pass BH q<0.10 (best: F2 "blocked" d5 p=0.042 q=0.27, sign *opposite* to the hypothesis; F4 phase aligned d5 p=0.058 q=0.27, not stable in WF half 1).
- Zones are not selective: with min strength 8, ~80% of setups sit within 1 ATR of a significant support zone (F1 655/822) → the zone flag barely separates setups. Not re-tuned (would be post-hoc); a v2 must be pre-registered and tested only on new setups.
- Entry timing: waiting for a pullback into a weekly confluence zone + volume-phase trigger is WORSE than next-open on excess return: d5 −1.15pp (V1, q=0.001) / −1.17pp (V2, q<0.001); d20 −0.7/−0.5pp (n.s.). R looks better (+0.65/+0.87R) only because the zone stop is much tighter (stop-hit 44–51% vs 13%) — R is not comparable; do not read it as an edge. V2 skips 43% of setups.
- Known limits: sample = 62 alert dates Jul–Oct 2026 (one regime); in-progress leg (last confirmed pivot → current extreme) is not projected in v1; Elliott overlap not in strength; Yahoo prices.
