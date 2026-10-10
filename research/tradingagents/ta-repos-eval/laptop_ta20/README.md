# TradingAgents x20 on the laptop (2026-10-08 15:19-16:29, Qwen2.5-7B qwen25-ta, RTX 4070 100% GPU)
Setups = the next 20 in nightly priority order (S0013..S0106); results in laptop C:\ta-backtest\results\results.jsonl (nightly skips them).
Outcome = active policy from iaf/sim_ratchet_trades.csv (stock LONG rt_ratchet_h618_c, stock SHORT rt_ratchet_c, crypto LONG rt_fixed3_c;
crypto SHORT has no live policy (frozen) -> rt_fixed3_c shown for reference only). Open trades marked at 2026-10-07 close.
agree = Buy/Overweight on LONG or Sell/Underweight on SHORT; oppose = the reverse; Hold = neutral.
Mean ret: agree 9 +9.9% (median -3.1%, 44% win) | oppose 8 +16.1% (median +2.8%, 100% win) | Hold 3 +0.6%.
Ex crypto shorts: agree 8 +11.8% (median +5.9%) | oppose 6 +5.1% (median +2.8%). N=20 -> anecdotal.
Per-row table: ta20_outcomes.csv
