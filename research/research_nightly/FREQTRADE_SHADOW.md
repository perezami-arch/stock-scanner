# Freqtrade as a crypto dry-run shadow - what it would need (08.10.2026)

**Status: documented only, not deployed.** It is not cheap enough to just switch on, and two of its choices belong to Ilan/the scanner agent.
Facts below come from the 08.10 evaluation (`/workspace/gh-repos-eval/freqtrade/`, results.md §7: freqtrade 2026.9, GPL-3.0, $0).

## What a shadow would give
Paper fills on a real exchange order book (spread, fees, rounding) for the scanner's crypto LONG setups. It measures execution realism,
not the policy: the policy itself is already verified by `vbt_parity_new.py` (vectorbt vs stop_rules.py, 405/405 trades, max diff 4e-14 pp).

## Why it cannot mirror the active policy 1:1 (measured on 301 crypto setups)
* Exits: an exit signal on the close of day j fills at the OPEN of j+1; open trades are force-closed at the last candle's open.
  vs our close-based fixed 3xATR stop: 266/279 trades differ by > 0.01 pp (mean +5.2 pp, max 19.6 pp).
* One open position per pair: 22/301 setups could not be placed (BTC 4, ETH 4, SOL 3 ...). Overlapping setups on one coin are lost.
* Intrabar stoploss variant still differs from our intrabar reference on 261/279.
* Crypto only (no stocks); crypto shorts are frozen anyway, so it would shadow crypto LONGs only.

## What it would need
1. **Exchange for public data** (dry-run needs NO API keys): Binance, Kraken, OKX, Bybit or Gate (officially supported). Alpaca is not a
   Freqtrade-supported exchange, so prices would differ slightly from the Alpaca/Yahoo bars the tracker uses. -> decision.
2. **Signal bridge**: a small strategy that reads the scanner's crypto LONG rows (scan_raw / tracker) and enters by `populate_entry_trend`
   from that file, or the REST API `forceenter` called after each scan (needs api_server enabled on localhost with a local password).
3. **Stops**: `custom_stoploss` = entry - 3xATR14 (ATR from the scan row, fixed); `stoploss_on_exchange=false`; timeframe 1d (or 1h
   with a custom_exit on the daily close to get closer to close-based).
4. **A 24/7 process** on the box (`freqtrade trade --dry-run`), venv already at `/workspace/gh-repos-eval/venv-freqtrade`. Like the
   nightly loop it would not survive a box reboot (nohup + a restart script), and it adds load to the shared box.
5. **Logging**: its sqlite trade DB exported daily to a CSV with ticker/alert_date/direction so `tool_stats.py --extra` can join
   `ft_fill_ret` as a column.
Effort: about half a day to build + a week of watching. License: GPL-3.0 - fine for internal use; do not distribute modified code.

## Recommendation
Low priority. If execution realism matters, a cheaper first step is recording the actual Alpaca crypto quote at the alert minute in the
scan (spread + mid) - no new process. Decide (שוק ההון / Ilan): build the shadow now, later, or not at all; and which exchange.
