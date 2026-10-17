# PRE-REGISTRATION — multi-degree pivots, Fib/Gann confluence, volume phase, entry timing
Locked 16.10.2026 (IL) BEFORE any backtest was run. Code versions: `modules/scanner_pivots.py` piv-2026-10-16.1,
`modules/scanner_volphase.py` vph-2026-10-16.1. Everything is **weight 0**: logged as `exp_piv_*` / `exp_vph_*` research
columns only; no change to score, selection, entry, stop or target. Any parameter change after this commit = new version,
evaluated only on setups after the change date.

## 1. Pivot engine (point-in-time, no repaint)
- Input: daily bars cut at the alert cutoff (`scanner_geometry.pit_cut`). Last 6 years used.
- Weekly bars: W-FRI (stocks) / W-SUN (crypto) from the cut daily frame; unfinished last week dropped.
- Degrees: **major** = weekly zigzag 3.0×ATR14(weekly); **intermediate** = weekly zigzag 1.5×ATR14(weekly);
  **minor** = daily zigzag 2.0×ATR14(daily) on the last 504 daily bars; **range5y** = weekly 5-year high↔low leg
  (only if neither extreme is on the last 2 weekly bars).
- A pivot is used only if its zigzag confirmation bar ≤ last visible bar. Stored: kind, price, date, confirmation date, degree, tf, size in ATR.

## 2. Projections and confluence
- Legs: last 4 consecutive confirmed pivot pairs per degree (major, intermediate, minor) + range5y leg.
- Levels per leg (p0→p1): retracements 0.382/0.5/0.618/0.786 (p1 − r·(p1−p0)); extensions 1.272/1.618/2.618 (p0 + e·(p1−p0));
  Gann eighths 1/8…7/8 of the leg range.
- Level weight: major 2, intermediate 2, range5y 2, minor 1. Only levels within 24×ATR14(daily) of price.
- Clustering (sorted, greedy): join if within 0.35×ATR of the previous level AND zone width ≤ 1.0×ATR.
- Strength = Σ weights + 0.5 × (# confirmed pivot prices within zone ±0.35 ATR, max 4) + 1 if VP120 POC inside.
  (Elliott-target overlap NOT included in v1.)
- Significant zone: strength ≥ 8. Outputs: nearest significant zone above / below, inside-zone strength, distance in ATR, contributing legs.

## 3. Volume phase
- Bar direction: close vs previous close (tie → close vs open → previous direction). relvol = V / mean(V of previous 20 bars).
- States: BR up & relvol>1, BF up & ≤1, SR down & >1, SF down & ≤1. Shares over 5/10/20 bars, dominant (most frequent,
  tie → larger volume), net volume share, CMF20, OBV slope z(20). Same on finished weekly bars (`w_` prefix).
- Alignment: LONG favoured by BR or SF dominant; SHORT by SR or BF.

## 4. Sample and outcome
- Setups: `scanner-tool-eval/setups_prepared.csv`, `dup_not_counted == False` (832 deduped), stocks + crypto, LONG/SHORT,
  cutoff = `asof_ts`. Prices: Yahoo daily auto-adjusted (fetched 16.10.2026). Setups with < 260 bars before cutoff dropped.
- Outcome (own computation, same for all tests): baseline entry = open of the first bar after the cutoff bar;
  `excess_dir_dN` = dir × (close[entry+N−1]/entry − 1) − dir × same for benchmark (SPY for stocks, BTC-USD for crypto), N = 5, 20.
  Only setups with N forward bars available.

## 5. Feature tests (zone/phase as setup filters)
Flags (each tested vs its complement):
F1 `at_support`: support-side zone (LONG below / SHORT above) within 1.0 ATR or price inside a significant zone.
F2 `blocked`: target-side significant zone within 1.5 ATR.
F3 `support_weekly`: F1 and the zone has a weekly/major/range5y contributor.
F4 `phase_aligned`: daily dom_10 aligned (+1).
F5 `w_phase_aligned`: weekly dom_10 aligned.
F6 `cmf_aligned`: CMF20 × dir > 0.
F7 `timing_combo`: F3 and (daily dom_5 == SF for LONG / BF for SHORT).
Model: excess_dir_dN ~ flag + dir×mom12-1 (PIT, 252→21 bars) + crypto dummy; OLS, SE clustered by alert date.
p_incr = p of the flag coefficient. BH-FDR over 7 flags × 2 horizons; graduate only if q < 0.10 AND same sign in both
date halves (walk-forward) AND sign survives removing the top 5% outcomes (winners-removed) AND ≥ 10 distinct dates per side.

## 6. Entry-timing simulation (simulation only)
- LONG: zone = nearest significant support zone below or containing price at cutoff, with weekly contributor; none → "no zone" (baseline entry).
  Watch bars 1..W after cutoff: armed when low ≤ zone hi and state of that bar ∈ {SF, BF} (pullback, sellers fading or buyers pausing) —
  pre-registered core rule: armed on touch during non-SR bar; trigger = first later (or same) bar that is BR or closes > zone hi
  after being armed. Entry = next bar open. Invalidation: close < zone lo − 0.5 ATR before trigger → skip.
- SHORT mirrored (zone above, rally into zone on BR/BF... mirror: armed on touch during non-BR bar, trigger SR or close < zone lo).
- Stop = closer of (zone lo − 0.25 ATR) and (entry − 4 ATR) for LONG (mirror for SHORT); target = next significant zone ahead (info).
- Variants: **V1 fallback** = no trigger by 5 sessions → enter at open of session 6; **V2 skip** = no trigger by 10 sessions → skip.
- Compare to baseline (next-open entry, stop 4×ATR) on the SAME setups: paired diff of excess_dir_d5/d20 (from each entry),
  R at d20 (close-based, stop hit = intraday touch → −1R), stop-hit rate, skip rate. Paired clustered-by-date t-test; BH within the sim.
- Report honestly even if null.
