# Calibrated TradingAgents - calibration / holdout split (built 2026-10-08 16:17)

Universe: the 832 runnable setups of setups_846.csv (846 minus 11 dup_not_counted and 3 without a cutoff).
Split per asset class by ENTRY DATE (open of the first bar after the decision time, as in sim_ratchet.py;
alert date when there is no simulated trade), whole entry dates kept on one side, earlier half = calibration:
- stocks: calibration = entry date <= 2026-09-16  (219 setups), holdout = later (224)
- crypto: calibration = entry date <= 2026-08-14  (198 setups), holdout = later (191)
Per asset class because a single global date would put most crypto in calibration and most stocks in holdout
(median entry: crypto 2026-08-14, stocks 2026-09-16).

Outcome: active policy, capped at 20 bars (close of the 20th bar incl. the entry bar), net of costs; excess = vs SPY
(stocks) / BTC (crypto) over the same entry->exit window (shorts: ret + bench ret). complete20=False -> data ended
2026-10-07 first (marked to market) - reported separately.
Few-shot lessons: only calibration-half trades whose outcome was known (stop hit or 20th bar closed) strictly
BEFORE the setup's cutoff bar (trade_date); max 6, deterministic (same asset+direction first, most recent, balanced
winners/losers).
Threshold: veto if p_success < theta; theta per asset class = argmax of avoided loss (sum of -ret20 over vetoed
trades) on the calibration half; holdout evaluated ONCE with that theta (calib_eval.py writes holdout_lock.json),
BH-FDR q<0.10 over all holdout comparisons, p = max(ticker-clustered, date-clustered, two-way) as in geo_analyze.py.
Real decision only on new setups from 2026-10-12.

Known limits (2026-10-08):
- Price data ends 2026-10-07. 98.6% of the stock HOLDOUT trades (entries after 09-16) have not reached day 20 yet and
  are marked to market; crypto holdout ~30%. Re-run build_calib_data.py on refreshed prices before the one-time
  holdout evaluation (all stock holdout trades reach day 20 around 2026-11-04).
- Few-shot coverage: the earliest setups have no closed trade known before their cutoff: 0 lessons for 103 of 198
  crypto and 25 of 219 stock calibration setups (1 lesson for 51 / 13 more); every holdout setup gets 6.
- The scanner rules shown to the model were themselves derived from analyses of these same alerts (unavoidable;
  they are the scanner's live rules). No backtest statistics from the 846 setups are put in the prompt.
- Sector names come from today's Yahoo profile (same input the scanner's sector rule uses).
