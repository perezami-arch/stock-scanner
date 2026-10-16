# Interim forward calibration (16.10.2026) — NO weight changes
Setups: 10 trial (source=trial-2026-10-08, models saw NO charts, entry = 09.10 open per agreed rule; levels from trial ledger / charts PDF)
+ 13 weekly 12.10 (charts, entry 13.10 open, incl. crypto UNI/LINK vs BTC). Prices through close 15.10.
Stops/targets on closes, only after entry. Metric: direction-adjusted excess vs SPY/BTC at day 3 (common horizon).
Graduation rule (≥30 OOS results, 8–10 entry days, FDR q<0.10, p_incr, walk-forward) cannot pass with 2 entry days.
tool_stats.ledger_columns(include_trial=True) now keeps trial rows tagged (llm_source, llm_chart_images); default unchanged.
