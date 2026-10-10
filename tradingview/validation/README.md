# Validation of elliott_fib_pit.pine (08.10.2026)

Method: `pine_port.py` is a bar-by-bar transliteration of the Pine script (state machine fed one confirmed bar at a time,
Pine `ta.atr` RMA formula). It shares no code with scanner_stops.py. Compared against /workspace/scan-runs/stops-test/stops_out.csv
and against scanner_stops.py functions. TradingView itself was not run (no TV account/compiler on the box); the .pine file
passes a syntax parse (pynescript), not a TV compile.

| Test | Result |
|---|---|
| A. Same bars as the scanner (cache 20261008T1029Z), last bar 2026-10-07, 17 fields (leg, 4 retracements, 3 extensions, struct stop + fallback, half-take, wave label, deviations, #valid counts, W3/W5 targets) + last 6 pivots with pivot/confirm dates | MU, CVX, NVDA, BTC: 0 mismatches (within the CSV's 4-decimal rounding); pivots identical |
| B. Every one of the last 250 bars, LONG and SHORT, port state vs scanner_stops.fib_elliott / half_at_1618 on truncated history (also proves no lookahead) | 0/2000 bar-mismatches |
| C. Reference stop vs scanner_stops.stop_status, 588 hypothetical entries (stock long/short chandelier 4x, BTC fixed 3x), 430 of them stopped | 588/588 identical level and stopped flag; CVX live row 192.2034 = csv |
| D. History start / ATR seeding: window minus 100/250 bars, Yahoo full history (MU from 1984, CVX 1962, NVDA 1999, BTC 2014) | All identical to stops_out.csv (ATR seeding washes out; zigzag re-syncs) |
| D. Not dividend-adjusted (TradingView default for stocks) | MU ±0.0001, CVX struct stop 193.589 vs 193.5901, NVDA all levels ~+0.12% (leg 215.10->234.76 vs 214.86->234.50); labels unchanged |
| E. BTC on Coinbase daily candles (≈ COINBASE:BTCUSD) instead of Yahoo BTC-USD | Different: an extra L 82,510 (09-28) and H 87,249 (10-02) confirm -> leg 82,510->87,249, wave "no valid count" vs "in_W3", struct stop 80,287 vs 72,780 |

Files: pine_port.py, validate.py (A-C), validate_stops_sweep.py (C), validate_history.py (D), validate_output.txt,
history_output.txt, history_sensitivity.csv, coinbase_btc_daily.csv, sample_alert_payloads.jsonl (Pine-format JSON, json.loads-checked).
