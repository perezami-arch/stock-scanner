# VIX sector-regime (Ilan's contrarian rule) — backtest 16.10.2026. Weight 0, NOT activated.
Locked before run: VIX>30 favour risk-on LONGS; VIX<16 (sens 15) favour defensive LONGS; turn-down = VIX<=0.9*5d max with max>30; fwd 20d;
risk-on/off = PIT 250d corr(ETF ret, dVIX). Significance clustered by VIX episode (block bootstrap, 4000).
## Market level 1999–2026 (sector ETFs, risk-on third minus risk-off third, fwd 20d)
| variant | days | episodes | mean/episode | CI95 | p | BH q |
|---|---|---|---|---|---|---|
| VIX>30 any day | 622 | 35 | +2.37% | [+0.96,+3.88] | <0.001 | 0.000 |
| VIX>30 first cross | 74 | 46 | +1.67% | [+0.22,+3.25] | 0.022 | 0.033 |
| VIX>30 peak & turned down | 325 | 42 | +0.39% | [-1.01,+1.86] | 0.60 | 0.60 |
| VIX<16 defensive minus risk-on | 2571 | 45 | +0.56% | [-0.27,+1.48] | 0.20 | 0.24 |
| VIX<15 (sens) | 2103 | 40 | +1.09% | [+0.25,+1.98] | 0.011 | 0.021 |
| momentum comparison (VIX>SMA20 -> defensive) | 2802 | 133 | -0.85% | [-1.31,-0.40] | 0.001 | (wrong sign) |
Walk-forward by era (VIX>30 on-off): 2000-09 +0.84, 2010-18 +1.04, 2019-26 +2.20 (stable). VIX<16: +1.06 / -0.51 / +0.29 (unstable).
## Setup level (832 historical setups, x20, controls dir*mom12-1 + crypto, clustered by alert date, 49 dates)
VIX range in sample 14.2–20.7 -> VIX>30 leg untestable. VIX<16: coef +4.6pp p_incr 0.075, BH q 0.225 (FAIL); VIX<15: p 0.30; WF halves +5.5pp (p .035) / +3.8pp (p .40).
Stop 3xATR vs 4xATR on risk-on stock longs at VIX<16 (n=137, close-ATR proxy): -0.29pp, p 0.18 -> no benefit.
## Verdict
Not graduated (setup-level q>=0.10; high-VIX leg has no setup data). Proposal (inactive, needs Ilan): scoring v-next "+<=5 pts for risk-on LONGS when VIX>30 (first cross)", re-evaluate when setups with VIX>30 exist. Column exp_vixreg_fit logged at weight 0.
## 19–20 zone (Ilan 16.10, hysteresis: >20 fear on, <19 fear off, 19–20 keep), market level 1999–2026, episode-clustered
| variant | signals | whipsaw (flip back ≤10d) | outcome | p | BH q |
|---|---|---|---|---|---|
| 1-close fear STATE: risk-off minus risk-on fwd20 | 2749 days / 62 ep | 66% of flips | −1.51% (risk-ON outperforms in fear) | <0.001 | 0.000 |
| 2-close fear STATE | 2689 / 45 ep | 46% | −0.79% | 0.12 | 0.36 |
| 1-close event UP through 20 (off−on) | 131 | — | −0.42% | 0.34 | 0.69 |
| 2-close event UP through 20 | 70 | — | +0.23% | 0.69 | 0.69 |
| 1-close event DOWN through 19 (on−off) | 132 | — | −0.25% | 0.61 | 0.69 |
| 2-close event DOWN through 19 | 70 | — | −0.30% | 0.57 | 0.69 |
Setups: only 9 setups (1 date) in the fear zone (1-close), 0 for 2-close → untestable. Columns exp_vix_zone_19_20[_2c], exp_vix_cross_up_20[_2c], exp_vix_cross_down_19[_2c] logged at weight 0.
Reading: the "caution on risk-on longs above 20" direction is NOT supported; data favour the contrarian side (risk-on beats defensive once fear is on), consistent with the VIX>30 result.
