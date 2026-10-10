# Fib "spiral" SHORT rule — pre-registered specification (FROZEN)

Frozen: 2026-10-08 16:55 Asia/Jerusalem (IDT), BEFORE any backtest was run. Author: repo researcher (חוקר ריפו) for room
"בניית מודל סורק לשוק ההון". Source of the rule: Ilan's charts (PROM 1h/1m WEEX, USELESS, PROM drop to 6.19, BTC big chart)
and his answers in the room (08.10): target = "where they cross"; entry = "breaks a line"; stop = "above the rejection candle";
timeframe = same rule on daily for stocks (not intraday).
Every number below was chosen a priori, with the reason given. Nothing is tuned on results. Any alternative that is run is a
pre-registered SENSITIVITY variant and is counted in the BH-FDR family. Code: `fib_spiral.py` (`P` = the parameters below,
`VERSION` = 1.0). Any later change => new version, new RULE file, and the old results stay reported.

## 0. Units
Bars are integers i (1h for crypto, 1d for stocks). ATR = Wilder ATR14. All quantities at a decision bar c use bars <= c only.

## 1. Pivots (confirmed only)
ATR zigzag, identical algorithm to the scanner's `sim_fib.zigzag` (alternating H/L, reversal threshold z x ATR14 of the bar
being tested). **z = 3.0** (the scanner's existing structure/stop scale is 3–4 ATR; 3 keeps 1h legs meaningful without
being so slow that D is confirmed only after the move is over). Each pivot carries (price, pivot bar, confirmation bar);
a pivot exists for decision bar c only if confirmation bar <= c.

## 2. ABCD leg
Four consecutive confirmed pivots L,H,L,H = A,B,C,D with C > A (higher low) and D > B (higher high). No other filter
(no ratio filter on BC/AB — Ilan gave none). H = D - A, T = barD - barA (>= 2 bars), **u = H / T** price per bar (fixed
price/time ratio, LINEAR scale — room agreement). One trade max per D (first trigger only).

## 3. Objects drawn from D
* Fib retracement A→D: f ∈ {0.236, 0.382, 0.5, 0.618, 0.786, 1, 1.272, 1.414}; level(f) = D - f·H.
* Fan lines from D (Gann-fan form, TradingView default set, which is what the PROM charts show: steep lines + 1/1 + shallow
  1/2…1/8): slope k·u down, **k ∈ {8, 4, 3, 2, 1, 1/2, 1/3, 1/4, 1/8}** (F9, primary). Line_k(i) = D - k·u·(i - barD).
  Sensitivity F5: k ∈ {1, 1/2, 1/3, 1/4, 1/8} only (the labels written on the BTC chart).
* Fib circles centred at D in scaled space (x = bars·u, y = price). Unit radius R = |D→A| = sqrt((T·u)^2 + H^2) = H·√2.
  Radii c·R, c ∈ {0.236, 0.382, 0.5, 0.618, 0.786, 1, 1.618, 2.618, 3.618, 4.236} (TradingView Fib-circle defaults).
  Forward crossing of circle c with level f: Δbars = sqrt((cR)^2 - (fH)^2) / u (exists iff cR >= fH).
* Fib time zones from D: barD + z·T, z ∈ {0.382, 0.618, 1, 1.382, 1.618, 2, 2.382, 2.618} (as on the BTC chart).
* Fan × level crossing: Δbars = f·T / k.

## 4. Setup window and entry trigger (Ilan: "breaks a line")
Window = bars i with conf(D) <= i < conf(next pivot after D), and i <= barD + ceil(2.618·T); the window also closes at the
first close > D (invalidated) or close <= A (structure broken). Trigger at bar i = for some fan k:
close[i-1] >= Line_k(i-1) and close[i] < Line_k(i) (a downward CLOSE break of a fan line; bars after D only).
**Entry = close of the trigger bar** (a priori: a close-based break is known exactly at that close; the scanner runs on
closes; next-open would add a gap-fill assumption on 1h crypto that runs 24/7 anyway).

## 5. Stop (Ilan: "above the rejection candle")
Rejection candle = bar with the highest high among bars max(barD+1, i-4) … i (the last 5 bars, after D).
**Stop = that high + 0.1·ATR14[i]** (buffer: 0.1 ATR = one tick-scale cushion, standard). Minimum risk 0.25·ATR14[i]
(if closer, stop = entry + 0.25·ATR). PROM check: Ilan's stop 7.423 is a post-D lower-high, not D itself → consistent.

## 6. Target (Ilan: "where they cross") — two pre-registered variants, both in the FDR family
Candidates = every forward crossing of (fan line k OR circle c) with a fib level f such that level(f) < entry and the
crossing bar is > entry bar and <= barD + ceil(2.618·T) (time-zone horizon).
* **T1 (primary)**: the FIRST crossing below entry = the candidate with the highest price (nearest below entry);
  ties → earliest bar. Target price = level(f). (Note, documented before running: with a 9-line fan almost every level
  has a crossing inside the horizon, so T1 is usually "next fib level below entry".)
* **T2**: the candidate where the MOST objects meet. Score = number of distinct objects passing within tolerance of the
  point (bar b, price y): fib levels with |level - y| <= 0.25·ATR14[entry]; fan lines / circles whose price at some bar in
  [b-2, b+2] is within 0.25·ATR; time zones within ±2 bars of b. Max score wins; ties → nearest (highest price), then earliest.
* Fallback if no candidate: level 0.786 if below entry, else level 1.0, else no target (stop/time exit only). Flagged.
If Ilan later picks T1 or T2, that one is reported as primary — without re-tuning anything.

## 7. Management / exit
Simulated from bar entry+1. Order inside a bar (conservative): stop first, then target.
* Stop fill = max(stop, open) (gap through stop fills at the open); target fill = min(target, open) (limit).
* **TR (primary)**: once a bar CLOSES with profit >= 1R (R = stop0 - entry), from the next bar stop = min(stop, entry)
  (breakeven); afterwards stop = min(stop, last confirmed fractal high + 0.1·ATR14) where a fractal high is a bar after
  entry with high > highs of the 2 bars on each side (confirmed 2 bars later). Stop only moves down.
  (Mirrors USELESS: stop locked in profit above the last lower high.)
* **NT (sensitivity)**: no trailing, fixed stop.
* Time exit: close of bar entry + ceil(2.618·T) (the last time zone length). Trades still open at data end: closed at the
  last close, flagged censored (kept).

## 8. Costs (pre-set)
* Crypto (Binance USDT-M perps): taker fee 0.05%/side; slippage per side by 24h-volume rank: rank 1–20: 0.03%,
  21–60: 0.08%, >60 (small caps, incl. PROM/USELESS): 0.15%. Funding: the short receives +rate (pays if negative) at every
  funding timestamp in (entry time, exit time]. Applied to % return; R = net % / initial risk %.
* Stocks: fee 0; slippage 0.05%/side; borrow 1%/year pro-rata on calendar days held.

## 9. Data
* Crypto 1h: Binance USDT-M perps, top 100 by 24h quote volume on 08.10.2026 (+PROMUSDT, USELESSUSDT), 2024-10-01 →
  2026-10-08 12:00 UTC, ccxt public. Non-crypto perps (gold/silver/stock tokens) excluded from the crypto set.
  1m: 60 days, PROM, USELESS + 8 most liquid (sensitivity only).
* Stocks daily: scanner universe (tracker/prices_all.pkl tickers ∪ scan_universe*.csv), yfinance adjusted, 2019-01-01 → 2026-10-07.
  (Survivorship bias: today's universe — noted, affects baselines equally.)

## 10. Baselines on the SAME entries
(a) Current active policy, no target, same time exit: crypto fixed stop entry + 3×ATR14, close-based; stocks 4×ATR14
    chandelier on closes (level_j = min close since entry through j-1 + 4·ATR14[j-1]).
(b) Fixed 0.786 target (1.0 if 0.786 >= entry), same stop/trailing as the rule.
(c) Random short entries: for every event, 10 random bars of the same symbol within ±30 days (crypto) / ±120 sessions
    (stocks), same % stop distance, same % target distance, same management and time exit (market-beta check). Seed 20261008.

## 11. Statistics
Unit = trade, outcome = net R (also net %). Mean with two-way clustered SE (symbol × entry date), p = max(symbol-, date-,
two-way) like tool_stats.py. Tests per variant: (i) mean net R > 0; paired differences vs (a), (b), (c).
Drop top-1 / top-3 symbols (by summed R). Walk-forward: split at the median entry date — first half vs second half
(no parameters are fitted, so this is a stability check: the edge must keep its sign and be positive in the second half).
BH-FDR q < 0.10 over ALL tests of ALL variants and datasets (crypto 1h, stocks 1d, crypto 1m), including T1/T2, TR/NT, F9/F5.
Verdict "passes" only if: N >= 30 from >= 10 distinct entry dates, q < 0.10 vs random (c) AND vs policy (a), positive in
both walk-forward halves, and survives drop-top-3.

## 12. Leak / repaint test
`fib_spiral_columns(df, cutoff)` must return identical output for (i) df truncated at cutoff, (ii) full df with cutoff,
(iii) truncated df + 50 junk bars appended. Plus: every backtest event reproduced by calling the function at its trigger bar.

## 13. Clarifications added at freeze time (still before any backtest run)
* Baseline R is measured in the RULE's initial risk unit (stop0 - entry) so paired differences are like-for-like; net %
  is reported alongside.
* "Non-crypto perps" = Binance markets whose `underlyingType` is not COIN or whose `underlyingSubType` contains
  TradFi / commodity / stock-like tags (e.g. XAUUSDT, stock tokens). Decided from exchange metadata, not from results.
* Equal-time bars: crypto entry time = bar open + 1h (close); exits inside a bar are timestamped open + 30 min, gap exits at
  the open, time exits at the close — used only for funding accrual.
