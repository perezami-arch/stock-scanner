# Trading-frameworks evaluation — Investing Algorithm Framework (IAF) & AgenticTrading
*Box run, 2026-10-08 (times IL / UTC+3). Everything below was actually run unless marked **NOT RUN**. All returns are net of costs (stocks 2 bp fee + 5 bp slippage per side; crypto 10 bp + 10 bp), $1,000 per setup, no leverage, no borrow fee on shorts.*

## 0. TL;DR

| Project | Verdict | One-liner |
|---|---|---|
| **IAF (investing-algorithm-framework)** | **MAYBE → adopt with caveats** (as backtest/report backbone, *not* as the PIT layer) | The event engine reproduced our independent replay exactly on 3,480 of 3,486 long trades (6 explained differences), and costs, trailing stops and the MCP server work. But its daily-bar semantics **leak future data by default** (same-bar close visible + fill at that bar's open; off-grid timestamps resolve to the *next* window). It is only safe behind our own point-in-time clock. v8 (stable) **cannot short**. v9 alpha can (verified), and adds Study/BacktestWindow/Monte Carlo/Veto. |
| **IAF MCP server** | **ADOPT (small, useful)** | 31 read-only analysis tools over saved backtests (plus a notes store), JSON-RPC over stdio, no extra deps. Bug: `investing-algorithm-framework mcp -d DIR` crashes in 8.10.0. Workaround: `python -m investing_algorithm_framework.cli.mcp_server -d DIR`. |
| **AgenticTrading (Open-Finance-Lab)** | **SKIP as the veto layer; MAYBE as a leaderboard/arena** | A large FastAPI "trading lab" (leaderboards, baselines, paper/Robinhood, many LLM gateways, about 5.6k tests). Ran it rule-based on vnpy-simulated data and on **real Alpaca bars** (paper keys). LLM runs need a signed-in local user **and** an LLM key (none present). Hourly US equities, $3,000 capital cap, 14-day window cap. Not built to replay our setups point-in-time. |
| **TradingAgents (TauricResearch)** | **Better base for approve/flag/veto** | Mature (≈110k★), bull/bear debate + risk manager, full reasoning-state logs, PIT date guards on data paths, OpenAI-compatible backend URL (so Ollama works). |

**What the backtests say about the scanner** (main sheet, PIT entries, benchmarked over identical windows; full tables in §3 and the appendix):
* **Grok crypto longs.** Hold-no-stop gives **+36.9 % mean / +32.1 % median, 93 % hit (N=255, 19 coins)**, but only **+14.7 % mean / +4.7 % median vs BTC**, +11.8 vs ETH, and **+13.3 mean / +2.7 median vs a 50/50 BTC-ETH basket**. 90 of the 255 trades are BTC or ETH themselves (≈0 excess). 46 are SOL (+18 vs BTC). The 119 alt trades: +24 mean / +10.8 median vs BTC. That is not beta-adjusted, so it is partly high-beta exposure in a rising market. **Without NEAR: +12.7 vs BTC → robust to NEAR.** In the team's "fair window" (08-12..10-04) it is +21.9 % raw (team: +23.2 %) but only **+8.8 mean / +1.1 median vs BTC**, and with an 8 % trailing stop the edge is **luck-flagged** (gone without the top 3 coins). Most of the headline return is the crypto market move.
* **Perplexity stock longs.** +5.9 % mean, +5.0 vs SPY. **LUCK-flagged**: without XP the excess drops to +3.9 (hold) and **0.0 with a trailing 8 %**. Without the top 3 tickers (XP, INTR, STNE) it is ≈0.
* **Original sheet longs.** **+4.3 vs SPY with IOVA → −1.4 without IOVA → luck.**
* **Grok stock longs, unfiltered.** **No edge vs SPY** (−0.1). The **momentum** sub-group is the one robust long group (+4.6 %, +3.1 vs SPY, survives top-3 removal). **Prebreakout longs are negative** (−3.3 %, −4.9 vs SPY), so the "no prebreakout" rule is confirmed.
* **Rule set.** Longs: no Grok prebreakout + sector-ETF uptrend. Shorts: stocks only, "20-method" score ≥ 3 and below SMA200. No crypto shorts. Whole stock book, hold: **unfiltered +1.4 % (N=433, +1.1 vs SPY) → filtered +4.5 % (N=175, +3.9 vs SPY, 66 % hit, robust to top-3 removal)**. Caveat: these rules were derived from this same history (in-sample).
* **Shorts.** Grok stock shorts that pass the rule: **+5.3 % mean / +7.3 % median, 76 % hit, +6.9 vs SPY, robust (N=33)**. All Grok stock shorts: −1.3 %. Grok crypto shorts: −22.6 % → **"no crypto shorts" confirmed**.
* **Exits.** For crypto longs, tight trailing stops destroy most of the edge (hold +36.9 → trailing 5 % +11.0 → trailing 8 % +18.2). Wide ATR stops keep most of it (3×ATR +33.1, 2×ATR +29.0). **Fibonacci-structure exits were the worst family everywhere except stock shorts** (e.g. Grok crypto +7.6 to +15.2 %; Perplexity stock longs ≈0 %). They stop out about 50 % of stock longs and cap the winners.
* **Exact-minute entries (Alpaca 1-min).** See §3.9.
* **ATR chandelier trailing stops (§3.10).** Highest close − k×ATR14 (shorts mirrored), point-in-time. k=2 is no better than a trailing 8 % (40–60 % of stock trades stopped, luck flags). **k=4 on stocks matches hold and fixed 3×ATR** (rule-filtered longs +5.3–5.5 %, +4.0–4.3 vs SPY, robust; only 15–20 % exited). k=3–4 on rule-filtered shorts gives +4.5 %, +5.6 vs SPY. On Grok crypto every trailing variant costs return vs hold (k=4: +32.7 vs +36.9).
* **Deeper Elliott/fib structure stops (§3.11).** Stops below the 0.786 retracement, below the swing origin (−0.5 or −1.0×ATR), or trailed under each newly confirmed higher-low **do not beat a plain ATR stop**. Their median width is similar (≈12–16 %), but a quarter of setups get a 2–5 % stop because entries sit right above the structure level. They stop out about twice as many trades and are much worse with intraday execution (levels get wicked). Only 'swing origin − 1.0×ATR, checked on closes' ties fixed 3×ATR.
* **4×ATR stop + Fib/Elliott targets (§3.12).** On **crypto**, extension targets are costly: >80 % of trades that hit 1.272/1.618 kept going, about 22–24 pp left per trade, and the mean falls from +36.8 to +14.6–17.1 %. Only the Elliott wave-3/5 target (+32.7 %, covers ~30 % of setups) or 2.618 come close to hold. On **stocks**, a 1.272/1.618 target raises the median and hit rate (e.g. all longs median +0.4 → +1.2, hit 55 → 62 % with intraday fills at 1.618). It keeps the mean about the same (+4.2 vs +4.0) and turns Grok stock longs from luck into robust. It hurts Perplexity, whose edge is a few big runners.
* **Ratchet / floor / tighten-after-profit on the 4×ATR chandelier (§3.13).** On stocks the ratchet equals the plain chandelier (it changes 1–8 trades per segment, ±0.2 pp) and the floor never binds. On Grok crypto the ratchet costs 2.4 pp, and the live fixed 3×ATR beats every variant. **Tightening at 4.5R effectively never triggers:** 3 of 228 stock longs and 0 of 173 shorts reach it, and it changed 0 stock outcomes. At 2–3R it hurts crypto (−4 to −6 pp). In R, rule-filtered stock longs earn ≈+0.25R per trade (maxDD 3.3R vs 6.6R hold), and rule-filtered shorts earn +0.52R (maxDD 1.8R). The shared stop code is in `iaf/stop_rules.py`.
* **Geometry / volume profile / candles / liquidity zones (§3.14).** 692 comparisons run with Benjamini-Hochberg FDR and conservative clustered p-values; the leak check was clean (0 mismatches). **Essentially noise.** Spiral, Gann, all candle patterns and sweeps show nothing. Only 2 filters survive, both on stock shorts and both proxies for "already breaking down" that the short rule already captures. The best lead: close below the 120-day value area, +8 pp vs SPY, 37 of 38 already pass the rule; it is a candidate to validate from 12.10. As stops or targets, liquidity pools, FVGs, order blocks and HVNs never beat the active policy; on crypto, liquidity/FVG targets cost 13–40 pp per trade. Every column stays at weight 0.

## 1. Environment & inputs
* Box: 8 cores / 16 GB, shared with two other eval jobs and an Ollama instance (load ≈ 14–15). IAF runs used `POLARS_MAX_THREADS=2`, sequentially (IAF's SQLite state is not safe across concurrent processes; see §2.3). Ollama was not touched.
* Venvs: `venv-iaf8` (IAF **8.10.0**, latest PyPI stable), `venv-iaf9` (**9.0.0a20** pre-release), `venv-agentic` (AgenticTrading `requirements.txt` + `requirements-vnpy.txt`).
* Input: `/workspace/tracker/setups-point-in-time-2026-10-08.csv` (read-only, not modified): 1,058 rows = **846 main + 212 excluded (mcap)**.
  * Main: 11 `dup_not_counted` dropped → 835. 3 rows with no alert date (S0091, S0099, S0100) and crypto rows with no price data are untestable. **832 main setups with data**; LONG/SHORT setups used = Bot stock 35L/24S, Grok crypto 255L/120S, Grok stock 143L/129S, Ilan 13L, Perplexity crypto 9L/2S, Perplexity stock 60L/41S.
  * Excluded: 200 testable, reported separately (§3.8).
* Prices: tracker `prices_all.pkl`, notes-analysis `crypto_daily_long.pkl`, `etf.pkl`; benchmarks SPY, 11 sector SPDRs, BTC-USD, ETH-USD. New in this round: Alpaca 1-min bars (SIP stocks, US crypto) for exact-minute entries.

## 2. IAF — verification, features, point-in-time behaviour

### 2.1 Repo facts (GitHub API, 2026-10-08)
| | IAF | AgenticTrading | TradingAgents |
|---|---|---|---|
| Repo | coding-kitties/investing-algorithm-framework | Open-Finance-Lab/AgenticTrading | TauricResearch/TradingAgents |
| Stars / forks | **2,161 / 310** | **768 / 157** | **110,203 / 21,192** |
| Last push | 2026-09-30 18:44 IL (main = `9.0.0a22`, commit f8e82c7) | 2026-10-08 06:03 IL (commit bdccc9a, 2026-10-07) | 2026-10-04 00:30 IL (v0.6.0) |
| License | **Apache-2.0** | **OpenMDW-1.0** (GitHub shows NOASSERTION) | Apache-2.0 |
| Open issues | 80 | 117 | 94 |
| PyPI stable | 8.10.0 (9.x only as alphas) | n/a | — |

### 2.2 Feature matrix — what we need vs v8 / v9 (checked by import + run)
| Need | v8.10.0 (stable) | v9.0.0a20 (alpha) |
|---|---|---|
| Event-driven backtest, daily bars, many symbols | ✅ (used for 3,486 trades) | ✅ |
| **Short selling** | ❌ no `create_short_order`; event engine long-only | ✅ `context.create_short_order/create_cover_order`. **Verified**: synthetic short at 300 with trailing 8 % → covered at 260.59 when close crossed min(240)×1.08 (`v9probe/short_probe.py`) |
| bps cost models | ✅ `FixedBasisPointsSlippage`, `PercentageCommission` via `SimulationBlotter`. ⚠️ `TradingCost` on the market is **silently ignored**, because a default blotter is auto-installed; you must call `set_blotter(...)` | ✅ same + `ExecutionConfig` |
| Fixed / trailing stops | ✅ `context.add_stop_loss(trade, percentage, trailing, sell_percentage)`. ⚠️ % anchored to the *estimated* `open_price`, evaluated on close, fills at trigger close; float drift → "sell percentages exceed 100" / "amount larger than open position" (worked around) | ✅ |
| Walk-forward | ⚠️ only a helper `generate_rolling_backtest_windows` | ✅ `Study` + `BacktestWindow(train_range, test_range, warmup_days, gap_days, step_days)` |
| Monte Carlo | ❌ | ✅ `App.run_monte_carlo_test` (**NOT RUN**) |
| Veto / ScoreCard / DecisionTrace | ❌ | ✅ present (not exercised) |
| MCP server | ✅ 31 tools (CLI entry bug, §2.6) | ✅ same tool count |
| API stability | stable | **breaking**: `run_backtest(strategy=…, study=Study(...), run_configuration=BacktestRunConfiguration(...))`; strategies need `schedule=Schedule.every(...)`; old `backtest_date_range=` kwarg removed |

### 2.3 Point-in-time findings (important)
Probes: `iaf/semantics_test.py`, `semantics_test2.py`.
1. **Same-bar lookahead.** On a daily bar labelled *t*, the strategy sees that bar's **close**, and a market order created then **fills at the Open of the first candle with label ≥ t**, i.e. the same bar's open. The fill is earlier than the information used to make the decision.
2. **Future-window fallback.** `PandasOHLCVDataProvider` returns sliding windows keyed by bar timestamp. For an index time that is not on a bar boundary, it falls back to the **next (future) window**.
3. Stops/trailing stops trigger on the close and fill at that close (no intrabar / gap modelling). `Trade.open_price` is the *estimate*, not the fill.
4. The SQLite state under `resources/` sits next to the script. Two concurrent IAF processes from one directory corrupted it ("readonly database", "Error updating object"), so runs must be serialised or use separate directories.

**Workaround used (works):** a gap-free compressed clock (base 2030-01-01 + k days), close-labelled bars, orders submitted at the entry-bar label, and every decision taken from our pre-computed PIT table (features use only bars ≤ the info cut-off; Perplexity ui_log times cut 70 min earlier; date-only rows decided at 23:59 UTC of the alert date → next bar open; Grok crypto date-only rows enter at the next 00:00 UTC open). With this, IAF is only an execution/accounting engine. Verdict: **usable, but not PIT-safe by default**. Anyone writing a "natural" IAF strategy for the scanner would get optimistic results.

### 2.4 Engine agreement (IAF v8 event engine vs independent pandas replay, longs, all 12 asset×policy runs)
| asset | policy | N | identical (<0.01 pp) | mean IAF | mean replay |
|---|---|---|---|---|---|
| crypto | hold / f8 / t5 / t8 / t12 | 301 each | 100 % | +38.4 / +28.3 / +10.5 / +17.4 / +24.2 | same |
| crypto | setup stop | 301 | 99.3 % | +26.4 | +26.4 |
| stock | hold / t5 / t8 / t12 | 280 each | 100 % | +1.0 / +0.4 / +0.5 / +1.0 | same |
| stock | f8 | 280 | 99.6 % | +0.9 | +0.9 |
| stock | setup stop | 280 | 98.9 % | +1.3 | +1.3 |
Residual differences: CUE, GRPN (setup stop above the entry-bar close, which IAF's percentage-from-estimated-open stop cannot express) and NTAP (precision).

### 2.5 Speed
IAF v8 event runs on this loaded box: stocks 280 trades / 177 symbols / 58 iterations in **56–69 s**; crypto 301 trades / 37 symbols / 83 iterations in **47–95 s**, plus ≈10–20 s startup. The independent pandas replay does all 1,027 setups × 6 policies in seconds, and the fib/ATR replay (14 variants) in ≈8 s. IAF's engine is fine for a nightly batch but not for a quick parameter sweep. v9's vector engine and Rust backends were not benchmarked (**NOT RUN**).

### 2.6 MCP server (run)
* Saved one IAF backtest (`iaf/saved_backtests`, stock t8, 40 setups) and drove the server over stdio JSON-RPC (`mcp/mcp_client.py`; transcript `mcp/mcp_session.json`). serverInfo `backtest-analysis 1.0.0`, capability `tools`, plus the prompt `backtest-analysis`.
* **31 tools:** list_strategies, get_strategy_details, rank_strategies, compare_strategies, get_full_analysis, get_trading_activity, get_trades, get_orders, get_positions, get_equity_curve, get_drawdown_series, get_monthly_returns, get_yearly_returns, get_rolling_sharpe, get_symbol_breakdown, get_return_scenarios, get_correlation_matrix, get_window_coverage, get_portfolio_snapshots, create/list/get/update/delete_note, filter_strategies, get_strategy_metadata, list_tags, get_strategies_by_tag, get_scaled_trades, get_stop_loss_take_profit_activity, get_scaling_activity.
* Calls returned markdown tables (strategy overview, symbol breakdown, a stop-loss activity table with 9 trailing-stop triggers).
* **Bug:** `investing-algorithm-framework mcp -d DIR` exits with `unrecognized arguments: mcp`, because the inner argparse re-parses argv. Workaround: `python -m investing_algorithm_framework.cli.mcp_server -d DIR`.
* **Limits for us:** read-only analytics of *saved IAF backtests*. It shows our compressed-clock dates (2030-…), metrics such as Sharpe/CAGR are meaningless for a $1k-per-setup replay, and open trades show 0 P&L. Useful for letting a bot answer "which symbols/stops drove this run?" over IAF bundles, not for scanner rules or benchmarks.

## 3. Scanner rules backtest (PIT)
Engines: longs through the **IAF v8 event engine** (= replay, §2.4). Shorts, benchmarks, fib/ATR and minute entries through the **independent replay** (`iaf/sim.py`, `sim_fib.py`, `sim_minute.py`), because IAF v8 cannot short. Hold = marked to market at the 2026-10-07 close. Stops checked on daily closes from the close of entry-bar + 2, mirroring IAF. Excess = trade return − benchmark return over the **same entry→exit window**; for shorts, excess = ret + bench ret.
**Robustness:** every row has mean, median, hit rate, and drop-top-1 / drop-top-3 tickers, where tickers are ranked by their contribution to the excess. **LUCK** = positive excess that goes ≤ 0 without the top 1 or top 3 tickers.

### 3.1 Named leave-one-ticker-out checks (requested)
| check | policy | sample | N | mean | median | hit | excess (mean) | excess (median) |
|---|---|---|---|---|---|---|---|---|
| Grok crypto longs vs **BTC** | hold | with NEAR | 255 | +36.9 | +32.1 | 93 | +14.7 | +4.7 |
| | hold | **without NEAR** | 250 | +34.9 | +32.0 | 92 | **+12.7** | +4.6 |
| | trailing 8 % | with / without NEAR | 255 / 250 | +18.2 / +18.1 | +22.9 / +24.6 | 76 / 77 | +3.6 / +3.4 | −0.4 / −0.4 |
| Perplexity longs (all) vs SPY/BTC | hold | with XP | 68 | +11.2 | +1.8 | 65 | +6.3 | +0.9 |
| | hold | **without XP** | 66 | +8.9 | +1.8 | 64 | **+3.9** | +0.7 |
| | trailing 8 % | with / without XP | 68 / 66 | +6.0 / +3.6 | +0.3 / −0.1 | 51 / 50 | +2.5 / **0.0** | −0.5 |
| Original sheet longs vs SPY | hold | with IOVA | 17 | +8.0 | −4.1 | 47 | +4.3 | −4.5 |
| | hold | **without IOVA** | 16 | +2.5 | −4.2 | 44 | **−1.4** → LUCK | −4.7 |
| | trailing 8 % | with / without IOVA | 17 / 16 | +3.4 / +2.2 | +0.8 / −1.6 | 53 / 50 | +2.8 / +1.5 | +1.2 / −1.0 |
Verdicts: NEAR is **not** what drives Grok crypto (robust, but the excess median is small). XP removes ≈40 % of Perplexity's hold excess and all of it with stops (**luck-driven**). IOVA is the entire original-sheet edge (**luck**).

### 3.2 Crypto vs BTC / ETH / 50-50 basket (hold, no stop)
| group | dir | N | coins | mean | median | hit | x BTC (mean/med) | x ETH | x basket (mean/med) | x BTC w/o top1 / top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Grok crypto | LONG | 255 | 19 | +36.9 | +32.1 | 93 | +14.7 / +4.7 | +11.8 | +13.3 / +2.7 | +14.0 / +8.6 | robust |
| Grok crypto | SHORT | 120 | 30 | −22.6 | −10.9 | 28 | −9.1 / −0.4 | −9.0 | −9.1 / −2.3 | — | no edge |
| Perplexity | LONG | 9 | 5 | +46.1 | +49.7 | 100 | +14.4 / +18.1 | +9.3 | +11.9 / +15.6 | +12.4 / +2.0 | robust (tiny N) |
| Perplexity | SHORT | 2 | 2 | −111.0 | — | 0 | −79.3 | — | — | — | no edge |

Grok crypto long composition (hold): BTC/ETH 90 trades, +22.1 % raw, **+0.8 vs BTC / −0.6 vs basket**. SOL 46 trades, +39.7 %, +18.2 vs BTC. Alts (16 coins) 119 trades, +47.0 % raw, **+24.0 mean / +10.8 median vs BTC**. Under trailing 8 % the alts drop to +3.7 mean / −1.4 median vs BTC. The same-window BTC return averaged **+22.1 %**, ETH +25.1 %.

**Grok crypto longs by window and exit (vs BTC; full table G in appendix):**
| window | policy | N | mean | median | hit | x BTC mean / med | x ETH | x basket | x BTC w/o top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|
| full | hold | 255 | +36.9 | +32.1 | 93 | +14.7 / +4.7 | +11.8 | +13.3 | +8.6 | robust |
| full | setup stop | 255 | +25.6 | +25.1 | 70 | +9.6 / +0.8 | +7.7 | +8.7 | +5.0 | robust |
| full | trailing 8 % | 255 | +18.2 | +22.9 | 76 | +3.6 / −0.4 | +0.7 | +2.2 | +0.8 | robust (thin) |
| full | trailing 12 % | 255 | +25.3 | +26.8 | 82 | +8.3 / +2.4 | +4.9 | +6.6 | +2.7 | robust |
| fair window 08-12..10-04 | hold | 117 | +21.9 | +14.2 | 84 | +8.8 / +1.1 | +9.9 | +9.3 | +4.1 | robust |
| fair window | trailing 8 % | 117 | +12.3 | +7.7 | 74 | +2.2 / −0.4 | +2.3 | +2.3 | −0.3 | **LUCK** |
(The team's "~+23 %" is this fair-window hold number. Their file measured crypto excess **vs SPY**, which overstates the value added.)

### 3.3 Stocks vs SPY / sector ETF (hold, no stop)
| group | dir | N | tickers | mean | median | hit | x SPY (mean/med) | x sector | x SPY w/o top1 / top3 | top1 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Bot | LONG | 30 | 24 | +2.3 | +0.3 | 53 | +1.0 / −1.0 | +1.4 | −0.0 / −1.6 | AMD | **LUCK** |
| Bot | SHORT | 19 | 15 | +0.0 | +0.8 | 58 | +1.3 / +1.9 | +1.7 | +0.6 / −0.1 | CRM | **LUCK** |
| Grok momentum | LONG | 40 | 30 | +4.6 | +4.5 | 70 | +3.1 / +2.9 | +0.3 | +1.9 / +0.0 | ALAB | robust (borderline) |
| Grok momentum | SHORT | 25 | 18 | −4.4 | −3.3 | 40 | −2.8 | −1.1 | | | no edge |
| Grok near-low | LONG | 14 | 12 | +0.4 | −1.8 | 43 | −1.2 | +0.8 | | | no edge |
| Grok near-low | SHORT | 12 | 12 | +5.0 | +6.7 | 75 | +6.4 / +8.5 | +5.7 | +5.5 / +3.4 | RH | robust |
| Grok portfolio-news | LONG/SHORT | 12/21 | | +0.3 / −2.5 | | 50/29 | −0.9 / −1.3 | | | | no edge |
| **Grok prebreakout** | **LONG** | 42 | 31 | **−3.3** | −3.2 | 33 | **−4.9** / −4.6 | −1.9 | | | no edge (avoid) |
| Grok prebreakout | SHORT | 27 | 23 | +5.7 | +6.5 | 70 | +7.1 / +8.5 | +5.1 | +6.4 / +5.5 | WHR | robust |
| Grok x-trends | LONG | 19 | 8 | +3.1 | +0.4 | 74 | +1.4 / −1.2 | −0.7 | −1.1 / −2.2 | AMD | **LUCK** |
| Grok x-trends | SHORT | 34 | 6 | −5.2 | −5.2 | 12 | −3.3 | −3.6 | | | no edge |
| Ilan charts | LONG | 11 | 11 | +11.3 | +2.7 | 55 | +8.4 / −2.3 | +5.6 | +5.0 / −2.5 | SMCI | **LUCK** |
| Original sheet | LONG | 17 | 17 | +8.0 | −4.1 | 47 | +4.3 / −4.5 | +4.4 | −1.4 / −7.0 | IOVA | **LUCK** |
| Original sheet | SHORT | 10 | 10 | −4.0 | +0.7 | 50 | −1.0 | −3.8 | | | no edge |
| Perplexity | LONG | 59 | 42 | +5.8 | +1.7 | 59 | +5.0 / +0.6 | +6.2 | +2.2 / −0.4 | XP | **LUCK** |
| Perplexity | SHORT | 41 | 31 | −0.7 | −0.7 | 49 | +0.3 | +0.3 | | | LUCK/none |
Reconciliation with the team's hold-no-stop file (same setups, our PIT entry): Perplexity stocks **+6.7 %** (team +6.9 %), Grok stocks +1.2 % (team +1.1 %), Bot +1.6 % (team +2.2 %), Grok crypto +38.0 % (team +39.4 %).

### 3.4 Rule filters — whole scanner (replay; table H)
| asset | policy | subset | N | mean | median | hit | excess | w/o top1 / top3 (raw mean) | flag |
|---|---|---|---|---|---|---|---|---|---|
| stock | hold | unfiltered L+S | 433 | +1.4 | +0.0 | 50 | +1.1 vs SPY | +1.0 / +0.5 | robust |
| stock | hold | **rule-filtered L+S** | 175 | **+4.5** | +2.2 | 66 | **+3.9** | +3.6 / +2.5 | robust |
| stock | trailing 8 % | unfiltered L+S | 433 | +0.6 | −0.7 | 46 | +0.6 | +0.2 / −0.1 | LUCK |
| stock | trailing 8 % | rule-filtered L+S | 175 | +3.4 | +0.8 | 59 | +3.2 | +2.5 / +2.0 | robust |
| stock | hold | unfiltered longs → filtered longs | 244 → 115 | +3.2 → +5.0 | +0.4 → +1.1 | 55 → 63 | +1.7 → +3.5 | | robust |
| crypto | hold | unfiltered L+S → filtered (= longs only) | 386 → 264 | +17.8 → +37.2 | +20.5 → +32.4 | 72 → 93 | +6.8 → +14.7 vs BTC | | robust |
Per-source IAF tables (all vs rule-filtered longs × 6 exits) are in the appendix (table B). Among filtered stock longs, Grok gets +3.6 % (hold) and trailing 8 % is robust (+3.7 %, +2.4 vs SPY); Perplexity gets +8.1 % but is LUCK under most exits. For crypto the long filter changes nothing (no prebreakout crypto); the gain comes entirely from dropping shorts.
⚠️ The rules come from the team's analysis of this same history, so these are **in-sample**. The walk-forward split (v9 `BacktestWindow`) is the right next test.

### 3.5 Shorts (replay; IAF v8 cannot short)
| src | asset | subset | N | mean | median | hit | x SPY / BTC | w/o top1 x | flag |
|---|---|---|---|---|---|---|---|---|---|
| Grok | stock | all shorts | 129 | −1.3 | −1.8 | 41 | +0.4 | −0.0 | LUCK |
| Grok | stock | **score ≥ 3 & < SMA200** | 33 | **+5.3** | +7.3 | 76 | **+6.9** | +6.3 (top3: +5.6) | **robust** |
| Perplexity | stock | all / rule | 41 / 20 | −0.7 / +1.8 | −0.7 / +6.6 | 49 / 70 | +0.3 / +2.4 | / +1.2 (top3 −0.7) | LUCK |
| Bot | stock | all / rule | 19 / 7 | +0.0 / +0.5 | | 58 / 71 | +1.3 / +1.7 | | rule: robust but N=7 |
| Grok | crypto | all shorts | 120 | −22.6 | −10.9 | 28 | −9.1 vs BTC | | no edge → **no crypto shorts** |
With a trailing 8 %, the rule-filtered Grok stock shorts are still +4.1 % (+5.3 vs SPY, robust).

### 3.6 Exit policies (IAF event engine, longs; full grid in the appendix, table B)
| group | hold | setup stop | fixed 8 % | trail 5 % | trail 8 % | trail 12 % |
|---|---|---|---|---|---|---|
| Grok crypto (255) mean / x BTC | +36.9 / +14.7 | +25.6 / +9.7 | +28.2 / +10.1 | +11.0 / +2.4 | +18.2 / +3.6 | +25.3 / +8.3 |
| Grok stock (143) mean / x SPY | +1.7 / −0.1 | +1.6 / +0.3 | +1.1 / −0.1 | +0.7 / −0.2 | +1.2 / +0.0 | +1.6 / +0.3 |
| Grok stock **rule-filtered** (58) | +3.6 / +1.7 | +3.9 / +2.4 | +4.2 / +2.7 | +3.0 / +1.9 | +3.7 / +2.4 (robust) | +4.6 / +3.1 |
| Perplexity stock (60) | +5.9 / +5.0 L | +5.4 / +4.9 L | +4.4 / +4.2 L | +2.4 / +2.7 L | +2.1 / +2.2 L | +3.2 / +2.9 L |
| Bot stock (30) | +2.3 / +1.0 L | +1.9 / +1.1 L | +2.3 / +1.0 L | +1.7 / +0.7 L | +2.3 / +1.0 L | +2.3 / +1.0 L |
(L = luck-flagged.) A trailing stop on longs **does not help** in this sample. It costs 15–25 pp on crypto. On stocks it is neutral at best, and helps only when combined with the rule filter.

### 3.7 Fibonacci-structure exits vs ATR stops (new; `iaf/sim_fib.py`, table I)
**Design**
* ATR14 (Wilder) and an ATR zigzag (reversal ≥ **2×ATR14**) are computed **only on bars ≤ rule_bar_date**, the last bar complete at the info cut-off, i.e. the bar before the alert.
* A pivot is usable only if its **confirmation bar** (where price reversed by the threshold) is ≤ that bar.
* Causality test: 960 truncation checks found pivots identical to the full-history run up to each cut-off, **0 mismatches**.
* **Leg.** Long: last confirmed swing high and the swing low before it. Short: mirrored.
* **Stop:** the first retracement (0.382 / 0.5 / 0.618 / 0.786) beyond the entry, plus a **0.5×ATR** buffer. If the entry is already past 0.786, the swing origin is used.
* **Targets:** 1.272 / 1.618 / 2.618 extensions of the leg. Targets already passed are skipped. Variants: T1, T2 or T3 full exit, or 1/3 at each.
* **Baselines:** fixed 2×ATR and 3×ATR stops, trailing 8 %, hold.
* Two execution modes: close-based (IAF-consistent) and intraday OHLC (stop-first if both hit in one bar; gaps fill at the open).
* 1,025 of 1,027 setups had a usable leg. Median stop distance: 6.4 % (stock longs), 4.8 % (crypto longs).

**Results** (close-based; intraday is similar, see appendix)
| segment | hold | trail 8 % | 2×ATR | 3×ATR | fib+1.272 | fib+1.618 | fib+2.618 | fib ⅓ each |
|---|---|---|---|---|---|---|---|---|
| Grok crypto LONG (255): mean / median / hit | +36.9 / +32.1 / 93 | +18.2 / +22.9 / 76 | +29.0 / +28.7 / 77 | **+33.1 / +31.1 / 87** | +7.6 / +7.9 / 68 | +9.4 / +10.6 / 65 | +15.2 / +12.2 / 64 | +10.7 / +11.3 / 67 |
| … x BTC (w/o top1) | +14.7 (+14.0) | +3.6 (+2.5) | +11.0 (+9.8) | +12.6 (+11.3) | +2.6 (+1.8) | +2.8 (+2.0) | +3.7 (+3.2) | −0.9 |
| All stock LONG (242) mean / median / hit | +3.2 / +0.4 / 54 L | +1.6 / 0.0 / 51 L | +2.5 / 0.0 / 51 L | **+3.5 / +0.3 / 53 robust** | +1.2 / −1.0 / 45 L | +1.2 / −1.2 / 43 L | +1.4 / −1.2 / 42 L | +1.3 / −1.1 / 44 L |
| Rule-filtered stock LONG (115) | +5.0 / +1.1 / 63 | +3.4 / +0.4 / 57 | +5.1 / +1.0 / 62 | **+5.5 / +1.1 / 63** | +2.5 / +1.0 / 57 | +3.0 / +0.3 / 54 | +2.6 / +0.3 / 53 | +2.7 / +0.5 / 55 |
| Perplexity stock LONG (59) | +5.8 L | +2.2 L | +6.0 robust | +6.3 robust | +0.2 L | +0.3 L | +0.5 L | +0.3 L |
| Rule-filtered stock SHORT (60) | +3.6 / +6.3 / 73 | +3.4 / +3.1 / 62 | +4.2 / +6.3 / 72 | +4.3 / +6.3 / 73 | +3.3 / +2.9 / **78** | +3.9 / +3.9 / 77 | **+4.5** / +5.4 / 77 | +3.9 / +3.8 / 77 |
Takeaways:
* Fib exits stop out **≈45–60 %** of stock longs and ≈30–40 % of crypto longs, and cap winners. On longs they are the worst family.
* A **wide ATR stop (3×ATR)** is the best stop: it keeps 90 %+ of hold's return with 6–15 % stop-outs, and on Perplexity it turns a luck-flagged result into a robust one.
* On rule-filtered shorts the fib targets slightly raise the hit rate (77–78 %) at a similar mean. That is the only place they are competitive.

### 3.8 Excluded-for-mcap rows (212; 200 testable) — shown separately, not in any table above
| policy | src | asset | dir | N | mean | median | hit | excess (mean / median) |
|---|---|---|---|---|---|---|---|---|
| hold | Grok | crypto | LONG | 28 | +46.0 | +35.7 | 96 | +17.9 / +7.0 vs BTC |
| hold | Grok | crypto | SHORT | 115 | −7.3 | +12.9 | 57 | +18.2 / +30.6 vs BTC |
| hold | Grok | stock | LONG | 30 | −16.5 | −15.4 | 20 | −18.0 / −17.1 vs SPY |
| hold | Grok | stock | SHORT | 18 | +25.3 | +22.6 | 94 | +27.0 / +24.8 |
| hold | Perplexity | crypto | L / S | 3 / 3 | +74.7 / +11.3 | | | |
| hold | Ilan / Bot | stock | LONG | 2 / 1 | −18.5 / −5.8 | | | |
| trailing 8 % | Grok | crypto | LONG / SHORT | 28 / 115 | +4.1 / +4.0 | −4.0 / −0.4 | 39 / 49 | −4.4 / +9.2 vs BTC |
| trailing 8 % | Grok | stock | LONG / SHORT | 30 / 18 | −8.6 / +6.0 | | 20 / 72 | −8.8 / +6.8 |
Small-cap Grok stock longs are clearly bad (−16.5 %), which supports the mcap exclusion. Small-cap stock shorts look good but N=18.

### 3.9 Exact-minute entries with Alpaca 1-min bars vs the daily-cut-off version (new; `iaf/fetch_minute.py`, `sim_minute.py`, `compare_minute.py`, full table `iaf/minute_vs_daily.md`)
**Method**
* For every LONG/SHORT setup with an *exact / schedule / ui_log* time: **585 setups → 525 with a minute bar**. The 60 without are Grok-crypto alts Alpaca doesn't list (e.g. BNB, ENA, DASH, HYPE, ARB): 36 "no bars" + 24 HTTP 400 bad-symbol.
* Entry = open of the **first 1-min bar ≥ decision time**. Stocks: SIP feed, regular session only (pre-/after-market alerts → next 09:30 ET open). Crypto: Alpaca US crypto.
* Prices are split-adjusted only. A first pass with `adjustment=all` (dividend-adjusted) biased dividend payers by up to −2.8 % and was discarded.
* Benchmarks (SPY, sector ETF, BTC, ETH) are entered at the **same minute**. Exit machinery is unchanged.

**Coverage** (main non-dup population): 464 timed setups. **The entry actually moves for only 20 stock setups** (Perplexity's intraday ui_log/exact alerts). Every Bot alert (10:10 UTC) and every Grok stock alert was pre-market, so the minute entry equals the daily-open entry. All 99 timed crypto setups with data move: entry shifts from the next 00:00 UTC open to the alert minute (median lag 0 min).

**Results (hold; Δ = minute − daily)**
| subset | N | daily: mean / median / hit / excess | minute: mean / median / hit / excess | Δ mean / Δ median (pp) |
|---|---|---|---|---|
| Grok crypto LONG (timed, with Alpaca data) | 54 | +4.5 / +3.5 / 67 % / +0.6 vs BTC | +4.9 / +3.9 / 69 % / +0.9 | +0.38 / −0.02 |
| Grok crypto SHORT | 36 | −2.6 / −2.0 / 42 % / +1.0 | −2.5 / −2.1 / 42 % / +0.9 | +0.07 / +0.06 |
| Perplexity crypto LONG | 9 | +46.1 / +49.7 / 100 % / +14.4 | +45.5 / +50.3 / 100 % / +14.5 | −0.58 / −0.69 |
| Perplexity stock LONG, entry changed (intraday alerts) | 14 | +3.2 / −0.0 / 50 % / +3.0 vs SPY | +2.4 / −1.2 / 50 % / +2.1 | **−0.81 / −1.32** |
| Perplexity stock SHORT, entry changed | 6 | −11.1 / −10.2 / 33 % | −10.3 / −10.3 / 33 % | +0.78 / −0.12 |
| Grok stock L/S, Bot L/S | 127/119, 30/19 | identical (pre-market alerts) | identical | ≈0 (−0.13 Grok L: split-only vs daily-file price rounding) |
Under trailing 8 % / setup stop the deltas are similar (≤ ±0.6 pp, except Perplexity intraday shorts at +1.3 pp, N=6).

**Conclusion:** the daily-cut-off approximation is **not** distorting the results. Exact-minute entries change group means by < 1 pp, and no robustness flag moves materially. The one consistent sign: Perplexity intraday stock longs entered at the alert minute do ≈1 pp *worse* than the next-open entry (the alert price tends to fade), N=14. Caveat: the minute test covers only the timed subset. The big Grok-crypto "date-only" block (17.07–23.08, 255 → 54 timed long rows with data) stays on the conservative next-00:00 entry. Data note: QRVO has a single daily bar (2026-09-14) in the tracker price file.

### 3.10 ATR chandelier TRAILING stops (Ilan's follow-up; `iaf/sim_chand.py`, full table J in appendix / `iaf/chandelier_table.md`)
*Revision 13:15 IL: a small fix. The close-based variant now includes the entry-bar+1 close in the running high/low, as the definition says. Close-based chandelier rows moved by ≤ 0.4 pp; conclusions unchanged.*
**Design (independent replay, same setups, PIT entries and costs as above)**
* Long stop level on day j = **highest close from the entry-day close through j−1, minus k×ATR14[j−1]**. Shorts mirror it: lowest close + k×ATR14.
* ATR14 is Wilder's ATR on the ticker's daily OHLC. The day-j level uses only bars ≤ j−1, so it is point-in-time and updated daily with no lookahead.
* k = 2, 3, 4.
* Two execution modes:
  * **Close-based:** IAF-consistent; first check at the close of entry-bar+2, exit at that close.
  * **Intraday:** from bar e+1, the bar's Low/High is checked against the level; fill at the worse of the open (gap) and the level.
* Compared on the same setups with hold, fixed 2×/3×ATR (from entry) and trailing 8 %.
* **Open trades.** Hold never exits. For stop policies, "exited" = stopped out; everything else is still open and **marked at the 2026-10-07 close**.
  * Stock setups were held only ≈17–20 trading days on average, so the stops were tested only briefly.
  * For k=3–4, 70–90 % of trades are still open, so the results lean heavily on the mark-to-market.

**Key rows** (x_mkt = vs SPY for stocks, vs BTC for crypto; w/o top1/top3 = mean excess after dropping the top 1/3 tickers by excess contribution; L = luck-flagged)
| segment | policy | N | exited / open | mean | median | hit | x_mkt | x w/o top1 / top3 | avg days (exited) | flag |
|---|---|---|---|---|---|---|---|---|---|---|
| **All stock LONG** | hold | 242 | 0 / 242 | +3.2 | +0.4 | 54 | +1.6 | +0.9 / −0.0 | 19.1 | L |
| | trailing 8 % | 242 | 103 / 139 | +1.6 | +0.0 | 51 | +0.7 | +0.0 / −0.5 | 11.5 (11.4) | L |
| | fixed 3×ATR | 242 | 34 / 208 | +3.5 | +0.3 | 53 | +2.2 | +1.5 / +0.6 | 17.2 | robust |
| | chandelier 2× (close / intraday) | 242 | 112/130 · 136/106 | +1.9 · +1.4 | −0.6 · −1.2 | 47 · 42 | +1.1 · +0.8 | +0.4/−0.3 · +0.1/−0.5 | 11.8 · 10.1 | L · L |
| | chandelier 3× (close / intraday) | 242 | 67/175 · 76/166 | +2.9 · +2.8 | +0.0 · −0.2 | 50 · 50 | +1.7 · +1.7 | +1.0/+0.1 · +1.0/+0.2 | 15.6 · 14.7 | robust (thin) |
| | **chandelier 4× (close / intraday)** | 242 | 41/201 · 47/195 | +3.2 · +3.4 | +0.3 · +0.3 | 53 · 53 | +1.9 · +2.1 | +1.2/+0.3 · +1.4/+0.5 | 17.0 · 16.7 | robust |
| **Rule-filtered stock LONG** | hold | 115 | 0 / 115 | +5.0 | +1.1 | 63 | +3.5 | +2.1 / +0.3 | 19.8 | robust |
| | trailing 8 % | 115 | 51 / 64 | +3.4 | +0.4 | 57 | +2.6 | +1.1 / +0.4 | 11.9 | robust |
| | fixed 3×ATR | 115 | 12 / 103 | +5.5 | +1.1 | 63 | +4.1 | +2.7 / +0.9 | 17.9 | robust |
| | chandelier 2× (close / intraday) | 115 | 49/66 · 60/55 | +4.3 · +3.6 | +0.6 · +0.4 | 59 · 53 | +3.4 · +2.9 | +2.0/+0.7 · +1.5/+0.7 | 12.4 · 10.8 | robust |
| | chandelier 3× (close / intraday) | 115 | 31/84 · 36/79 | +4.5 · +4.3 | +0.4 · +0.4 | 57 · 57 | +3.4 · +3.2 | +2.0/+0.5 · +1.8/+0.5 | 16.0 · 14.5 | robust |
| | **chandelier 4× (close / intraday)** | 115 | 19/96 · 21/94 | +5.3 · +5.5 | +0.6 · +0.6 | 60 · 60 | +4.0 · +4.3 | +2.6/+0.8 · +2.8/+1.1 | 17.8 · 17.4 | robust |
| **Perplexity stock LONG** | hold | 59 | 0 / 59 | +5.8 | +1.7 | 59 | +5.0 | +2.2 / −0.4 | 23.7 | L |
| | trailing 8 % | 59 | 32 / 27 | +2.2 | −1.2 | 44 | +2.3 | −0.6 / −1.7 | 13.9 | L |
| | fixed 3×ATR | 59 | 12 / 47 | +6.3 | +1.1 | 56 | +5.9 | +3.2 / +0.6 | 20.2 | robust |
| | chandelier 2× / 3× (close) | 59 | 37/22 · 26/33 | +2.7 · +3.4 | −1.2 · −1.6 | 42 · 44 | +2.9 · +3.3 | +0.0/−1.2 · +0.4/−0.9 | 13.3 · 17.5 | L · L |
| | chandelier 4× (close / intraday) | 59 | 17/42 · 19/40 | +5.7 · +6.0 | +0.6 · +0.6 | 53 · 53 | +5.3 · +5.7 | +2.5/−0.1 · +2.9/+0.4 | 19.9 · 19.4 | L · robust |
| **Grok stock LONG** | hold | 142 | 0 / 142 | +1.6 | +0.1 | 52 | −0.2 | −0.9 / −1.7 | 17.1 | no edge |
| | trailing 8 % | 142 | 60 / 82 | +1.1 | +0.2 | 52 | −0.0 | −0.4 / −1.0 | 10.8 | no edge |
| | chandelier 2× / 3× / 4× (close) | 142 | 60/82 · 34/108 · 20/122 | +1.8 · +2.3 · +1.9 | −0.2 · +0.3 · +0.2 | 49 · 53 · 53 | +0.5 · +0.8 · +0.3 | ≤ +0.1 / < 0 | 11.4 · 14.5 · 15.4 | L (all) |
| **Rule-filtered stock SHORT** | hold | 60 | 0 / 60 | +3.6 | +6.3 | 73 | +4.8 | +4.6 / +3.9 | 19.0 | robust |
| | trailing 8 % | 60 | 21 / 39 | +3.4 | +3.1 | 62 | +4.2 | +3.9 / +3.1 | 13.8 | robust |
| | fixed 3×ATR | 60 | 4 / 56 | +4.3 | +6.3 | 73 | +5.4 | +5.2 / +4.5 | 18.0 | robust |
| | chandelier 2× (close / intraday) | 60 | 20/40 · 23/37 | +4.0 · +3.9 | +3.0 · +2.6 | 68 · 67 | +4.8 · +4.7 | +4.6/+3.9 · +4.4/+3.7 | 14.0 · 12.3 | robust |
| | chandelier 3× (close / intraday) | 60 | 9/51 · 12/48 | +4.4 · +4.1 | +6.3 · +5.5 | 73 · 68 | +5.5 · +5.1 | +5.3/+4.6 · +4.9/+4.2 | 16.7 · 16.1 | robust |
| | **chandelier 4× (close / intraday)** | 60 | 4/56 · 5/55 | **+4.5** · +4.4 | +6.3 · +6.3 | 73 · 73 | **+5.6** · +5.5 | +5.4/+4.7 · +5.3/+4.6 | 17.9 · 17.4 | robust |
| **All stock SHORT** | hold | 189 | 0 / 189 | −1.0 | −1.2 | 44 | +0.5 | +0.2 / −0.1 | 16.2 | L |
| | chandelier 2× / 3× / 4× (close) | 189 | 99/90 · 46/143 · 27/162 | −0.7 · −0.6 · −0.6 | −2.0 · −1.6 · −1.2 | 39 · 44 · 44 | +0.5 · +0.7 · +0.7 | +0.2/−0.1 · +0.4/+0.1 · +0.4/+0.1 | 10.8 · 13.7 · 15.0 | L · thin · thin |
| **Grok crypto LONG** | hold | 255 | 0 / 255 | +36.9 | +32.1 | 93 | +14.7 | +14.0 / +8.6 | 53.3 | robust |
| | trailing 8 % | 255 | 140 / 115 | +18.2 | +22.9 | 76 | +3.6 | +2.5 / +0.8 | 32.0 | robust (thin) |
| | fixed 3×ATR | 255 | 15 / 240 | +33.1 | +31.1 | 87 | +12.6 | +11.3 / +6.5 | 50.2 | robust |
| | chandelier 2× (close / intraday) | 255 | 218/37 · 222/33 | +15.9 · +15.6 | +12.4 · +10.8 | 67 · 64 | +4.8 · +4.9 | +3.5/+1.4 · +3.5/+1.6 | 26.8 · 23.9 | robust (thin) |
| | chandelier 3× (close / intraday) | 255 | 74/181 · 114/141 | +27.2 · +22.2 | +27.5 · +22.8 | 79 · 76 | +10.0 · +7.4 | +8.2/+3.3 · +5.7/+3.0 | 43.3 · 38.0 | robust |
| | **chandelier 4× (close / intraday)** | 255 | 19/236 · 45/210 | +32.7 · +29.3 | +30.5 · +28.5 | 85 · 82 | +12.8 · +10.9 | +11.6/+6.9 · +9.3/+4.4 | 49.2 · 46.3 | robust |

**Reading it**
* The chandelier is monotonic in k: wider is better everywhere in this sample.
* **2×ATR behaves like (or worse than) trailing 8 %.** It stops out 40–60 % of stock trades and 85 %+ of crypto longs, and it luck-flags Perplexity and all-stock longs.
* **4×ATR (stocks) ≈ fixed 3×ATR ≈ hold**: it keeps 95–110 % of hold's mean, stops out only 15–20 % of stock trades, and is robust to top-3 removal on all stock longs, rule-filtered longs and rule-filtered shorts.
* On rule-filtered shorts, chandelier 4× close-based is the best row in the table: +4.5 % mean, +5.6 vs SPY, 73 % hit (3×: +4.4 %, +5.5). It is marginally better than hold.
* Intraday execution is a bit worse than close-based at k=2–3 (more whipsaw) and about the same at k=4.
* For Grok crypto longs, every trailing variant gives up return vs hold. 4× close is the least costly: −4.2 pp mean, x BTC +12.8 vs +14.7.
* **Caveat:** at k=4 only 15–20 % of trades exited. The sample period (Jul–Oct 2026, a mostly rising market) cannot show the protection a trailing stop gives in a sharp sell-off. These are still in-sample results.

### 3.11 Deeper Elliott / fib STRUCTURE stops, no targets (Ilan's follow-up; `iaf/sim_struct.py`, full table K in appendix / `iaf/structure_table.md`)
**Design (strict PIT, independent replay, same entries and costs)**
* **Leg.** 2×ATR14 zigzag; a pivot exists only from its **confirmation bar**. The setup's leg uses only pivots confirmed on or before the bar before the alert. Long leg = last confirmed swing high H plus its origin low L (wave-1 start / last confirmed higher-low). Shorts are mirrored.
* **Stops**
  * **(a)** below the 0.786 retracement − 0.5×ATR.
  * **(b)** below the swing origin − 0.5×ATR.
  * **(c)** below the swing origin − 1.0×ATR.
  * **(d)** structure trail: starts at (b); the stop moves up to each newly confirmed higher-low − 0.5×ATR (ATR as of that pivot's confirmation bar). It is usable only from the bar after confirmation.
* **No targets.** Exit only on the stop; otherwise marked at the 2026-10-07 close.
* **Fallback.** If price at entry is already through the structure level, the next deeper confirmed pivot is used. That happened for 3–26 % of setups (column `fallback`).
* **Comparisons.** Hold, fixed 3×ATR and chandelier 4×ATR on the **same setups**. These are setups with a usable leg, so N is slightly smaller than in §3.10 (e.g. all stock longs 228 vs 242).
* **Stop distance** = initial stop % below/above the entry fill.

**Key rows** (close-based unless noted; x_mkt = vs SPY for stocks, vs BTC for crypto)
| segment | policy | N | exited / open | stop dist median (p25) | mean | median | hit | x_mkt | x w/o top1 / top3 | avg days | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **All stock LONG** | hold | 228 | 0/228 | — | +3.7 | +0.5 | 56 | +2.2 | +1.4 / +0.5 | 19.2 | robust |
| | fixed 3×ATR | 228 | 28/200 | 12.6 (7.7) | **+4.0** | +0.4 | 55 | **+2.6** | +1.9 / +0.9 | 17.5 | robust |
| | chandelier 4×ATR | 228 | 36/192 | 16.8 (10.3) | +3.7 | +0.4 | 55 | +2.4 | +1.7 / +0.7 | 17.2 | robust |
| | (a) 0.786 − 0.5ATR | 228 | 75/153 | 8.4 (**2.1**) | +2.5 | −0.7 | 46 | +1.6 | +0.8 / +0.0 | 13.3 | robust (thin) |
| | (b) origin − 0.5ATR | 228 | 64/164 | 11.7 (3.9) | +2.3 | −0.5 | 48 | +1.3 | +0.6 / −0.3 | 14.3 | LUCK |
| | (c) origin − 1.0ATR | 228 | 49/179 | 13.1 (5.2) | +3.7 | +0.1 | 51 | +2.6 | +1.8 / +0.9 | 15.4 | robust |
| | (d) structure trail | 228 | 69/159 | 11.7 (3.9) | +2.6 | −0.5 | 48 | +1.6 | +0.8 / −0.0 | 14.1 | LUCK |
| | (c) intraday / (d) intraday | 228 | 68/160 · 85/143 | | +2.1 · +1.8 | −0.6 | 46 · 45 | +1.1 · +0.9 | +0.6/−0.3 · +0.5/−0.1 | | LUCK · LUCK |
| **Rule-filtered stock LONG** | hold | 115 | 0/115 | — | +5.0 | +1.1 | 63 | +3.5 | +2.1 / +0.3 | 19.8 | robust |
| | fixed 3×ATR | 115 | 12/103 | 13.0 (8.3) | **+5.5** | +1.1 | 63 | **+4.1** | +2.7 / +0.9 | 17.9 | robust |
| | chandelier 4×ATR | 115 | 19/96 | 17.3 (11.1) | +5.3 | +0.6 | 60 | +4.0 | +2.6 / +0.8 | 17.8 | robust |
| | (a) / (b) | 115 | 28/87 · 23/92 | 11.3 (3.2) · 16.2 (5.2) | +4.2 · +4.3 | +0.4 | 55 · 57 | +3.2 · +3.1 | +1.7/+0.4 · +1.7/+0.1 | ≈15 | robust |
| | (c) origin − 1.0ATR | 115 | 20/95 | 18.2 (6.6) | +5.2 | +0.6 | 59 | +4.1 | +2.7 / +0.9 | 15.4 | robust |
| | (d) structure trail | 115 | 27/88 | 16.2 (5.2) | +4.6 | +0.4 | 57 | +3.4 | +2.0 / +0.5 | 15.6 | robust |
| | (a)–(c) intraday | 115 | 28–37 exited | | +2.0 to +2.6 | ≈0 | 49–52 | +1.1 to +1.5 | ≤ +0.7 / < 0 | | LUCK |
| **Perplexity stock LONG** | hold | 57 | 0/57 | — | +6.7 | +1.7 | 61 | +5.8 | +2.9 / +0.3 | 23.2 | robust |
| | fixed 3×ATR | 57 | 10/47 | 12.3 (8.6) | +7.1 | +1.2 | 58 | +6.6 | +3.7 / +1.2 | 20.6 | robust |
| | (a) / (b) / (d) | 57 | 23–25 exited (≈42 %) | 4.1–8.4 (0.6–2.3) | +3.5 to +3.9 | −1.3 | 40–42 | +3.3 to +3.7 | ≤ +0.8 / < 0 | ≈15 | LUCK |
| | (c) origin − 1.0ATR (close) | 57 | 12/45 | 12.0 (4.5) | **+7.5** | +1.7 | 60 | **+6.9** | +4.1 / +1.5 | 18.8 | robust |
| | (c) origin − 1.0ATR (**intraday**) | 57 | 23/34 | 12.0 (4.5) | +1.1 | −1.7 | 40 | +0.7 | +0.1 / −1.1 | 16.1 | **LUCK** |
| **Grok stock LONG** | hold / 3×ATR / ch4 | 131 | | | +2.0 / +2.2 / +2.3 | ≈+0.3 | 54–55 | +0.2 / +0.6 / +0.7 | < 0 w/o top3 | | LUCK |
| | (a)–(d) | 131 | 26–39 exited | 10–16 (3–6) | +1.5 to +1.8 | ≈0 | 48–50 | +0.2 to +0.5 | < 0 | | LUCK |
| **Rule-filtered stock SHORT** | hold | 60 | 0/60 | — | +3.6 | +6.3 | 73 | +4.8 | +4.6 / +3.9 | 19.0 | robust |
| | fixed 3×ATR / chandelier 4×ATR | 60 | 4/56 · 4/56 | 10.7 · 14.3 | +4.3 · **+4.5** | +6.3 | 73 | +5.4 · **+5.6** | +5.2/+4.5 · +5.4/+4.7 | ≈18 | robust |
| | (a) / (b) / (c) / (d) | 60 | 6 · 5 · 4 · 8 exited | 21–26 (12–17) | +3.3 / +3.5 / +3.9 / +3.3 | +5.5 to +6.3 | 70–73 | +4.4 / +4.6 / +5.1 / +4.3 | all > +3 | ≈17.5 | robust |
| **All stock SHORT** | hold | 173 | 0/173 | — | −0.9 | −1.2 | 46 | +0.5 | +0.2 / −0.1 | 16.8 | LUCK |
| | fixed 3×ATR | 173 | 32/141 | 10.7 | −0.5 | −1.2 | 46 | +0.8 | +0.5 / +0.2 | 15.2 | robust (thin) |
| | (a) / (b) / (d) | 173 | 62–73 exited (36–42 %) | 7.7–10.2 (2.1–2.9) | −1.0 to −1.1 | ≈ −1.5 | 41–43 | ≈ 0 | < 0 | ≈13.5 | LUCK |
| | (c) origin − 1.0ATR | 173 | 44/129 | 12.1 (3.3) | −0.5 | −1.2 | 45 | +0.7 | +0.4 / +0.1 | 14.4 | robust (thin) |
| **Grok crypto LONG** | hold | 254 | 0/254 | — | **+36.8** | +32.0 | 93 | **+14.8** | +14.0 / +8.6 | 53.3 | robust |
| | fixed 3×ATR / chandelier 4×ATR | 254 | 15 · 19 exited | 10.5 · 13.9 | +33.1 · +32.7 | ≈+31 | 87 · 85 | +12.6 · +12.8 | ≥ +11 / +6.5 | ≈50 | robust |
| | (a) 0.786 − 0.5ATR | 254 | 35/219 | 10.4 (5.4) | +29.2 | +28.0 | 79 | +11.0 | +10.2 / +6.2 | 45.1 | robust |
| | (b) / (c) | 254 | 25 · 15 exited | 14.4 · 16.3 | +30.3 · +32.7 | +28.5 · +29.8 | 83 · 87 | +11.3 · +12.3 | ≈ +10–11 / +6.4 | ≈48 | robust |
| | (d) structure trail (close / intraday) | 254 | 42/212 · 107/147 | 14.4 | +27.6 · +21.8 | +27.3 · +15.6 | 77 · 69 | +10.2 · +7.6 | +7.9/+5.4 · +5.3/+2.5 | 43.8 · 37.6 | robust |

**Why deeper structure stops don't help here**
* **The median distance is similar to 3×ATR (≈12–16 % vs ≈12.6 %), but the distribution is very uneven.** A quarter of setups get a stop only **2–5 %** away, because the scanner often fires right after a pullback, so the entry sits just above the 0.786 level or the swing origin. Those tight stops are the ones that get hit.
* **Structure stops trigger about twice as often as an ATR stop of similar median width.** For example, all stock longs: (b) stopped 28 % of trades vs 12 % for 3×ATR.
* **Structure levels are wicked intraday.** Every structure variant is clearly worse in intraday mode than close-based (rule-filtered longs: +5.2 → +2.5; Perplexity (c): +7.5 → +1.1). Swing lows act as liquidity magnets: price trades through them and recovers.
* **The structure trail (d) never beat its static version (b) by much,** and intraday it was among the worst variants (crypto +21.8 vs hold +36.8).
* **Only variant (c), the swing origin − 1.0×ATR on closes, matches the ATR stops.** It roughly ties 3×ATR (all stock longs +3.7 vs +4.0; rule-filtered +5.2 vs +5.5; Perplexity +7.5 vs +7.1) while stopping out more trades (21 % vs 12 %).
* On rule-filtered shorts every structure stop is very wide (21–26 % above entry), barely triggers, and lands slightly *below* hold and the ATR stops.
* **Caveat:** most trades are still open (marked at 2026-10-07), holding periods are short (≈13–20 trading days for stocks), the market mostly rose, and everything is in-sample.

### 3.12 4×ATR stop + Fibonacci / Elliott profit targets (Ilan's follow-up; `iaf/sim_targets.py`, full table L in appendix / `iaf/targets_table.md`)
**Design (strict PIT; same 2×ATR14 zigzag legs and same setups as §3.11)**
* **Stops:**
  * (i) fixed 4×ATR14 from entry (ATR as of the bar before the alert);
  * (ii) chandelier 4×ATR = highest close since entry − 4×ATR14[j−1]. Shorts are mirrored.
* **Targets** from the confirmed leg (origin L0 → swing end H1): extensions L0 + r·(H1−L0), r = 1.272 / 1.618 / 2.618. If a target is already behind the entry, the next one is used; if none is left, there is no target.
* **Exit variants:**
  * full exit at a single target;
  * 1/3 at each of the three targets;
  * **hybrids:** 1/3 or 1/2 off at 1.618, the rest under the 4×ATR chandelier.
* **Elliott target**, using only confirmed pivots, with the count required to end on a confirmed wave-2 or wave-4 pivot:
  * **wave-5** = L4 + (H1−L0), when the last 5 pivots satisfy L2 > L0, H3 > H1 and no wave-4/wave-1 overlap (L4 > H1);
  * otherwise **wave-3** = L2 + 1.618·(H1−L0), when L2 > L0.
  * **Coverage** (main sheet):
    * stock longs: 71/242 have a usable count (65 wave-3, 6 wave-5), 12 were already past the target at entry, and 159 (66 %) have no valid count;
    * stock shorts: 44/189;
    * Grok/Perplexity crypto longs: 84/264.
  * Setups without a count simply run under the stop.
* **Execution:**
  * close-based: checks start at the close of entry-bar+2; the stop is checked before targets; fills at the close;
  * intraday: from bar e+1; if the stop and target both trade in one bar, the stop is assumed first; targets fill at the better of the open and the target, like a resting limit order.
* **Columns:**
  * `stop/target/open` = how each trade finally ended (still-open trades are marked at the 2026-10-07 close);
  * **reached** = % of trades that touched their (first) target;
  * **kept going** = % of target-reached trades where simply holding the whole position to 2026-10-07 would have been worth more;
  * **left** = average pp given up versus holding, over target-reached trades (negative = the target exit beat holding).

**Key rows** (x_mkt = vs SPY for stocks, vs BTC for crypto; the flag uses dropping the top 1/3 tickers by excess)
| segment | policy | stop / target / open | reached | kept going / left (pp) | mean | median | hit | x_mkt | x w/o top1 / top3 | days | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Grok crypto LONG (254)** | hold | 0/0/254 | — | — | **+36.8** | +32.0 | 93 | **+14.8** | +14.0 / +8.6 | 53 | robust |
| | fixed 3×ATR / chandelier 4×, no target | 15/0/239 · 19/0/235 | — | — | +33.1 · +32.7 | +31.1 · +30.3 | 87 · 85 | +12.6 · +12.8 | +11.3/+6.5 · +11.6/+6.9 | ≈50 | robust |
| | fixed 4× + 1.272 (close) | 4/226/24 | 89 % | 83 % / **+24.1** | +14.6 | +13.5 | 94 | +4.8 | +4.0 / +2.9 | 16 | robust |
| | fixed 4× + 1.618 (close) | 4/215/35 | 85 % | 83 % / +22.3 | +17.1 | +14.9 | 93 | +5.7 | +4.8 / +3.7 | 19 | robust |
| | fixed 4× + 2.618 (close) | 4/182/68 | 72 % | 60 % / +10.8 | +28.3 | +26.1 | 91 | +9.5 | +8.2 / +7.1 | 29 | robust |
| | 1/3 at each (fixed 4×, close) | 4/160/90 | 89 % | 78 % / +17.2 | +20.7 | +19.4 | 92 | +1.6 | +0.8 / −0.5 | 32 | **LUCK** |
| | **Elliott w3/w5 (fixed 4×, close)** | 4/63/187 | 25 % | 68 % / +13.6 | +32.7 | +28.9 | 91 | +13.5 | +12.6 / +8.4 | 43 | robust |
| | hybrid ⅓ / ½ at 1.618 + chandelier (close) | 19/0/235 | 80 % | 84 % / +7.6 · +11.3 | +26.9 · +24.0 | +25.2 · +22.7 | 87 · 88 | +7.0 · +4.2 | +6.3/+3.0 · +2.9/+0.9 | 49 | robust |
| **All stock LONG (228)** | hold | 0/0/228 | — | — | +3.7 | +0.5 | 56 | +2.2 | +1.4 / +0.5 | 19 | robust |
| | fixed 3×ATR, no target (close / intraday) | 28/0/200 · 31/0/197 | — | — | +4.0 · +4.0 | +0.4 | 55 | +2.6 · +2.7 | +1.9/+0.9 · +2.0/+1.0 | 17 | robust |
| | fixed 4× + 1.272 (close) | 17/74/137 | 33 % | 42 % / +1.9 | +3.3 | **+1.3** | **60** | +2.1 | +1.7 / +1.0 | 14 | robust |
| | fixed 4× + 1.618 (close / **intraday**) | 18/47/163 · 21/61/146 | 21 · 27 % | 57 % / +2.3 · 46 % / **−1.2** | +3.4 · **+4.2** | +1.0 · **+1.2** | 59 · **62** | +2.2 · **+3.0** | +1.8/+1.1 · **+2.6/+1.9** | 15 · 14 | robust |
| | Elliott (fixed 4×, close) | 18/17/193 | 8 % | 47 % / +0.6 | +3.9 | +0.6 | 57 | +2.5 | +1.8 / +0.9 | 18 | robust |
| | hybrid ½ at 1.618 + chandelier (close / intraday) | 36/0/192 · 40/0/188 | 20 · 26 % | 61 % / +1.1 · 48 % / −1.0 | +3.4 · +3.8 | +0.6 | 57 | +2.1 · +2.6 | +1.7/+0.8 · +2.2/+1.3 | 17 | robust |
| **Rule-filtered stock LONG (115)** | hold | 0/0/115 | — | — | +5.0 | +1.1 | 63 | +3.5 | +2.1 / +0.3 | 20 | robust |
| | fixed 3×ATR, no target | 12/0/103 | — | — | **+5.5** | +1.1 | 63 | **+4.1** | +2.7 / +0.9 | 18 | robust |
| | fixed 4× + 1.272 (close) | 10/48/57 | 42 % | 42 % / +3.2 | +4.0 | **+2.0** | **67** | +3.0 | +2.3 / +1.3 | 15 | robust |
| | fixed 4× + 1.618 (close / intraday) | 10/32/73 · 12/40/63 | 28 · 35 % | 53 % / +3.8 · 45 % / +1.1 | +4.3 · +4.9 | +1.8 · +2.0 | 66 · 68 | +3.2 · +3.9 | +2.6/+1.5 · +3.2/+1.9 | 16 · 14 | robust |
| | Elliott (chandelier 4×, close / intraday) | 18/14/83 · 20/16/79 | 12 · 14 % | 50 % / +1.1 · +0.8 | +5.3 · **+5.5** | +1.3 · +1.1 | 63 | +4.2 · **+4.5** | +2.8/+1.0 · +3.1/+1.3 | 17 · 16 | robust |
| | hybrid ½ at 1.618 + chandelier (intraday) | 21/0/94 | 35 % | 48 % / +0.2 | +5.2 | +1.6 | 60 | +4.0 | **+3.2 / +1.9** | 17 | robust |
| **Perplexity stock LONG (57)** | hold / fixed 3×ATR | 0/0/57 · 10/0/47 | — | — | +6.7 · **+7.1** | +1.7 · +1.2 | 61 · 58 | +5.8 · **+6.6** | +2.9/+0.3 · +3.7/+1.2 | ≈21 | robust |
| | fixed 4× + 1.618 / 2.618 (close) | 7/10/40 · 7/6/44 | 18 · 11 % | 70 % / +15.2 · 83 % / +19.8 | +4.4 · +4.9 | +1.7 | 61 | +3.9 · +4.3 | +2.7/+1.4 · +2.7/+1.1 | 19–21 | robust |
| | Elliott (fixed 4×, close / intraday) | 7/4/46 · 8/4/45 | 7 % | 75 % / +2.8 · +4.1 | +6.8 · +6.9 | +1.7 | 61 | +6.2 · +6.3 | +3.4/+0.8 · +3.5/+0.9 | 20 | robust |
| | hybrid ⅓ at 1.618 + chandelier (close) | 15/0/42 | 16 % | 89 % / +6.7 | +5.5 | +0.6 | 54 | +5.1 | +3.0 / +0.6 | 20 | robust |
| **Grok stock LONG (131)** | hold / fixed 3×ATR / chandelier 4× | — | — | — | +2.0 / +2.2 / +2.3 | +0.3 / +0.3 / +0.4 | 54–55 | +0.2 / +0.6 / +0.7 | < 0 w/o top1 | | **LUCK** |
| | fixed 4× + 1.272 (close) | 9/46/76 | 35 % | 41 % / **−1.1** | +2.5 | **+1.3** | **60** | +1.1 | +0.8 / **+0.1** | 12 | **robust** |
| | fixed 4× + 1.618 (intraday) | 11/38/82 | 29 % | 42 % / **−5.7** | **+3.7** | +1.0 | **63** | **+2.4** | **+1.8 / +1.0** | 12 | **robust** |
| | Elliott (both stops) | 10/10/111 | 8 % | 40 % / −0.1 | +2.1 to +2.4 | +0.4 | 55–57 | +0.5 to +1.0 | < 0 w/o top3 | 15 | LUCK |
| **Rule-filtered stock SHORT (60)** | hold | 0/0/60 | — | — | +3.6 | +6.3 | 73 | +4.8 | +4.6 / +3.9 | 19 | robust |
| | chandelier 4× / fixed 3×ATR, no target | 4/0/56 | — | — | **+4.5** · +4.3 | +6.3 | 73 | **+5.6** · +5.4 | +5.4/+4.7 · +5.2/+4.5 | 18 | robust |
| | 4× + 1.272 (close) | 2/27/31 | 45 % | 70 % / +0.3 | +3.5 | +3.2 | **80** | +3.9 | +3.6 / +3.2 | 11 | robust |
| | 4× + 2.618 (close) | 2/11/47 | 18 % | 45 % / **−5.1** | +4.6 · +4.7 | +6.3 | 78 | +5.5 · +5.6 | +5.3/+4.6 · +5.4/+4.7 | 16 | robust |
| | Elliott (chandelier 4×, close) | 2/11/47 | 18 % | 82 % / −1.8 | +4.4 | +4.5 | 77 | +5.3 | +5.1 / +4.5 | 15 | robust |
| **All stock SHORT (173)** | hold / fixed 3×ATR | 0/0/173 · 32/0/141 | — | — | −0.9 · −0.5 | −1.2 | 46 | +0.5 · +0.8 | +0.2/−0.1 · +0.5/+0.2 | 15–17 | LUCK · robust (thin) |
| | 4× + 1.618 (intraday, chandelier) | 26/36/111 | 21 % | 61 % / −1.4 | −0.2 | **+0.6** | 51 | +0.7 | +0.5 / +0.2 | 11 | robust (thin) |

**What it shows**
* **Crypto longs: targets are expensive.**
  * About 85 % of Grok crypto longs reach the 1.272 or 1.618 extension, and **over 80 % of those kept going**. A full exit at 1.272 gives up **~24 pp per trade** and cuts the mean from +36.8 % to +14.6 % (excess vs BTC from +14.8 to +4.8).
  * Only the far 2.618 target (+28.3 %) or the **Elliott wave-3/5 target** (+32.7 %, x BTC +13.5, robust; it only exists for 25–31 % of setups) come close to hold or the plain ATR stops.
  * The 1/3-at-each-target ladder is the worst: luck-flagged, with the excess vs BTC ≈0.
* **Stock longs: targets trade mean for consistency.**
  * A 1.272 or 1.618 target lifts the **median** (all longs +0.4 → +1.0–1.3; rule-filtered +1.1 → +1.8–2.0) and the hit rate (55 → 59–67 %), but usually trims the mean slightly.
  * With **intraday limit-style fills**, fixed 4×ATR + 1.618 is the best all-stock-long row: +4.2 % vs +4.0 %, median +1.2, hit 62 %, x SPY +3.0, and it survives dropping the top 3 (+1.9).
  * It is also the only exit that turns **Grok stock longs** from luck-flagged into robust (+3.7 %, x SPY +2.4, still +1.0 without the top 3). There the target sold strength that later reversed (left on table −5.7 pp, i.e. the exit *beat* holding).
* **Perplexity: targets hurt.** Its gains come from a few big runners (70–83 % of target hits kept going, giving up 15–20 pp each). Best: no target (3×ATR) or the rare Elliott target.
* **Rule-filtered stock longs: roughly equal.** Best mean / excess: Elliott + chandelier intraday (+5.5 %, +4.5) or plain 3×ATR (+5.5 %, +4.1). Best robustness: the ½-at-1.618 hybrid intraday (x w/o top3 +1.9 vs +0.9).
* **Rule-filtered shorts:** 1.272 targets raise the hit rate to 80 % but lower the mean (+3.5 vs +4.5). A 2.618 or Elliott target ≈ no target. The **chandelier 4× with no target** stays best on mean (+4.5 %, +5.6 vs SPY).
* **Hybrids** (½ or ⅓ at 1.618, rest under the chandelier) land between the full-target and no-target versions. They never beat the best no-target stop on mean, but on stocks they are as robust or more robust.
* **Caveat (as before):** most trades are still open at 2026-10-07; holding periods are short; the market mostly rose; everything is in-sample. Intraday target fills assume a resting limit order at the target.

### 3.13 Ratchet, floor and tighten-after-profit on the 4×ATR chandelier (group follow-up; `iaf/stop_rules.py`, `iaf/sim_ratchet.py`, full table M in appendix / `iaf/ratchet_table.md|csv`)
**Live scanner policies tested against:** stock longs = chandelier 4×ATR (close) + sell ½ at fib 1.618; stock shorts = chandelier 4×ATR (close); crypto longs = fixed 3×ATR.

**Design.** Strict PIT, same setups as §3.11–3.12 (Grok crypto longs N=254, all stock longs 228, rule-filtered 115, Perplexity 57, Grok 131, rule-filtered shorts 60, all shorts 173). Same costs, entry fills and calendar.
* All stop logic now lives in **`iaf/stop_rules.py`** (`ChandelierStop`, `atr_wilder`, `r_multiple`), and the replay calls it directly.
* **Regression check** (`iaf/check_stop_rules.py`): with `mode='plain'` it reproduces chandelier 4×ATR (§3.10), the ½-at-1.618 hybrid (§3.12) and fixed 3×ATR exactly (0 mismatches on 1,027 / 278 / 540 trades). The scanner can call the same code.
* **Stop level for bar j** uses only the extreme close through j−1 and ATR14[j−1].
  * *plain* = extreme − 4×ATR (can loosen when ATR expands).
  * **RATCHET** = max(previous stop, extreme − 4×ATR); shorts use min.
  * *floor* = max(entry − 4×ATR₀, extreme − 4×ATR).
  * **Tighten** = ratchet, plus the multiplier switches 4 → k2 (sticky) once the best close since entry reaches X·R. R = 4×ATR14 at the rule bar, so 4.5R = 18 ATR.
* **Execution.** Close-based is primary (fill at the close). Intraday is secondary (fill at the worse of the open and the stop).
* **R units.** Each trade's net return ÷ (R / entry). R = 3×ATR for fixed 3×ATR. Hold uses a nominal R = 4×ATR. Expectancy per trade in R = mean R.
* **maxDD_R** = largest peak-to-trough drop in the cumulative R of the equal-weight trade sequence, in signal order, using the same order for every policy.
* Median R as % of entry: stocks ≈ 16–17 % (longs) and ≈ 14 % (shorts); Grok crypto ≈ 14 % (10.5 % for 3×ATR).

**How many trades ever reached X R (best close while held; in brackets, regardless of exit, to 2026-10-07):**

| segment | N | ≥2R | ≥3R | ≥4.5R | 4.5R tighten changed the outcome of |
|---|---|---|---|---|---|
| Grok crypto LONG | 254 | 162 (64 %) | 143 (56 %) | 47 (18.5 %) [66 = 26 %] | 1 trade with k2=3 (+0.01 pp); 12 with k2=2 (−0.56 pp) |
| All stock LONG | 228 | 8 (3.5 %) | 3 (1.3 %) | 3 (1.3 %) [3] | 0 with k2=3; 1 with k2=2 (≈0.00 pp) |
| Rule-filtered stock LONG | 115 | 7 (6.1 %) | 3 (2.6 %) | 3 (2.6 %) | 0 / 1 |
| Perplexity stock LONG | 57 | 4 | 2 | 2 | 0 / 0 |
| Grok stock LONG | 131 | 3 | 1 | 1 | 0 / 1 |
| Rule-filtered stock SHORT | 60 | 6 (10 %) | 2 (3.3 %) | **0** | never fires |
| All stock SHORT | 173 | 6 (3.5 %) | 2 (1.2 %) | **0** | never fires |

**Key rows (close-based unless noted).** x_mkt is vs SPY for stocks and vs BTC for crypto. "Exited/open" counts trades exited vs still open, marked at the 2026-10-07 close.

| segment | policy | exited/open | mean % | median % | hit % | x_mkt | x_mkt w/o top3 | mean R | median R | maxDD R |
|---|---|---|---|---|---|---|---|---|---|---|
| Grok crypto LONG | hold | 0/254 | +36.8 | +32.1 | 93 | +14.8 | +8.6 | +2.54 | +2.65 | 3.6 |
| Grok crypto LONG | **fixed 3×ATR (live)** | 15/239 | **+33.1** | +31.1 | 87 | **+12.6** | +6.5 | +3.13 (R=3ATR) | +3.49 | 4.7 |
| Grok crypto LONG | chandelier 4×ATR, plain | 19/235 | +32.7 | +30.3 | 85 | +12.8 | +6.9 | +2.32 | +2.62 | 3.6 |
| Grok crypto LONG | **RATCHET** chandelier 4×ATR | 39/215 | +30.3 | +29.5 | 85 | +11.4 | +5.0 | +2.14 | +2.40 | 3.6 |
| Grok crypto LONG | floor | 20/234 | +32.6 | +30.3 | 85 | +12.8 | +6.8 | +2.31 | +2.62 | 3.6 |
| Grok crypto LONG | ratchet + tighten 2R→k2 | 176/78 | +24.0 | +21.5 | 85 | +8.5 | +4.2 | +1.67 | +1.89 | 3.6 |
| Grok crypto LONG | ratchet + tighten 3R→k3 | 55/199 | +30.1 | +28.6 | 85 | +11.4 | +5.0 | +2.12 | +2.40 | 3.6 |
| Grok crypto LONG | ratchet + tighten **4.5R→k3** | 47/207 | +30.3 | +29.5 | 85 | +11.4 | +5.0 | +2.14 | +2.41 | 3.6 |
| All stock LONG | hold | 0/228 | +3.72 | +0.45 | 56 | +2.2 | +0.5 | +0.14 | +0.04 | 6.2 |
| All stock LONG | chandelier 4×ATR, plain (no tgt) | 36/192 | +3.71 | +0.42 | 55 | +2.4 | +0.7 | +0.15 | +0.03 | 5.8 |
| All stock LONG | **RATCHET** (no tgt) | 38/190 | +3.71 | +0.42 | 55 | +2.4 | +0.7 | +0.15 | +0.03 | 5.6 |
| All stock LONG | ratchet + tighten 2R→k2 (no tgt) | 41/187 | +3.83 | +0.42 | 55 | +2.6 | +0.9 | +0.16 | +0.03 | 5.7 |
| All stock LONG | **live: ½ at 1.618 + plain chandelier** | 36/192 | +3.44 | +0.55 | 57 | +2.1 | +0.8 | +0.12 | +0.05 | 6.1 |
| All stock LONG | ½ at 1.618 + **ratchet** | 38/190 | +3.43 | +0.55 | 57 | +2.1 | +0.9 | +0.12 | +0.05 | 6.0 |
| All stock LONG | ½ at 1.618 + ratchet + tighten 4.5R→k3 | 38/190 | +3.43 | +0.55 | 57 | +2.1 | +0.9 | +0.12 | +0.05 | 6.0 |
| All stock LONG | ½ at 1.618 + ratchet (intraday) | 42/186 | +3.88 | +0.62 | 57 | +2.6 | +1.4 | +0.15 | +0.06 | 5.7 |
| Rule-filtered stock LONG | hold | 0/115 | +5.03 | +1.10 | 63 | +3.5 | +0.3 | +0.21 | +0.07 | 6.6 |
| Rule-filtered stock LONG | plain chandelier (no tgt) | 19/96 | +5.32 | +0.63 | 60 | +4.0 | +0.8 | +0.25 | +0.05 | 3.3 |
| Rule-filtered stock LONG | **RATCHET** (no tgt) | 20/95 | +5.32 | +0.63 | 60 | +4.1 | +0.9 | +0.25 | +0.05 | 3.3 |
| Rule-filtered stock LONG | ratchet + tighten 2R→k2 (no tgt) | 23/92 | +5.57 | +0.63 | 60 | +4.4 | +1.2 | +0.26 | +0.05 | 3.3 |
| Rule-filtered stock LONG | **live: ½ at 1.618 + plain** | 19/96 | +4.72 | +1.02 | 61 | +3.4 | +1.3 | +0.20 | +0.07 | 3.4 |
| Rule-filtered stock LONG | ½ at 1.618 + **ratchet** | 20/95 | +4.72 | +1.02 | 61 | +3.5 | +1.3 | +0.20 | +0.07 | 3.4 |
| Rule-filtered stock LONG | ½ at 1.618 + ratchet + tighten 2R→k2 | 23/92 | +4.85 | +1.02 | 61 | +3.6 | +1.5 | +0.20 | +0.07 | 3.3 |
| Perplexity stock LONG | plain / **ratchet** (no tgt) | 15/42 | +6.38 / +6.38 | +0.63 | 54 | +5.9 / +6.0 | +0.4 / +0.5 | +0.32 | +0.05 | 3.3 |
| Perplexity stock LONG | live ½ at 1.618 + plain / + ratchet | 15/42 | +5.11 / +5.11 | +0.63 | 54 | +4.7 / +4.7 | +0.7 / +0.8 | +0.22 | +0.05 | 3.3 |
| Grok stock LONG | plain / **ratchet** (no tgt) | 18/113 · 19/112 | +2.26 / +2.28 | +0.38 | 55 | +0.7 / +0.7 | −0.9 (LUCK) | +0.07 | +0.03 | 7.4 / 7.3 |
| Grok stock LONG | live ½ at 1.618 + plain / + ratchet | 18/113 · 19/112 | +2.38 / +2.40 | +0.47 | 57 | +0.8 / +0.8 | −0.3 (LUCK) | +0.07 | +0.04 | 7.5 / 7.3 |
| Rule-filtered stock SHORT | hold | 0/60 | +3.60 | +6.34 | 73 | +4.8 | +3.9 | +0.46 | +0.32 | 3.7 |
| Rule-filtered stock SHORT | **live: plain chandelier 4×ATR** | 4/56 | +4.46 | +6.34 | 73 | +5.6 | +4.7 | +0.52 | +0.32 | 2.0 |
| Rule-filtered stock SHORT | **RATCHET** | 7/53 | +4.30 | +6.34 | 73 | +5.4 | +4.5 | +0.52 | +0.32 | 1.8 |
| Rule-filtered stock SHORT | ratchet (intraday) | 7/53 | +4.51 | +6.34 | 73 | +5.6 | +4.8 | +0.53 | +0.32 | 1.2 |
| All stock SHORT | live plain / **ratchet** | 27/146 · 30/143 | −0.51 / −0.49 | −1.22 | 46 | +0.8 / +0.8 | +0.2 | −0.01 / −0.00 | −0.10 / −0.12 | 23.4 / 22.9 |

For shorts, the tighten variants equal the ratchet when checked on closes (≤0.01 pp). With intraday checks, 2R→k2 costs 0.4 pp on rule-filtered shorts (4.51 → 4.13).

**What it shows**
* **Ratchet vs non-ratchet is a non-event on stocks.** The two differ only when ATR expands enough to pull the plain chandelier *down*. That changed 5 of 228 stock longs (−0.01 pp), 3 of 60 rule-filtered shorts (−0.16 pp) and 8 of 173 shorts (+0.02 pp). Mean, median, R and drawdown are equal within noise.
* **Ratchet hurts Grok crypto.** It changed 22 of 254 trades and cost 2.4 pp (+32.7 → +30.3 %). In crypto, ATR expands in rallies, the plain stop loosens with it, and that slack keeps winners alive through volatile pullbacks. The ratchet removes that slack.
* **The floor almost never binds:** it changed 0–6 trades per segment. A 4×ATR chandelier rarely sits below entry − 4×ATR.
* **Tighten-after-profit is fine only where it rarely fires.**
  * On stocks, 2R→k2 is the "best" variant: +0.08 to +0.25 pp, with maxDD unchanged. That comes from **5 changed trades**, so it is noise rather than evidence.
  * On Grok crypto, where 64 % of trades reach 2R, tightening to k2=2 at 2R cuts the mean by **6.3 pp** (+30.3 → +24.0) and at 3R by 4.0 pp.
* **In R terms**, the stock-long edge is small: about 0.15R per trade (0.25R rule-filtered, 0.20R with the ½-at-1.618 target), with a median of ≈0.05R. That is because 1R ≈ 17 % of price.
  * The chandelier mainly cuts drawdown: rule-filtered longs **3.3R vs 6.6R** for hold; rule-filtered shorts **1.8–2.0R vs 3.7R**.
  * Rule-filtered shorts are the best R profile here: +0.52R mean, +0.32R median, 73 % hit, maxDD 1.8R.
  * Crypto fixed 3×ATR gives the highest mean % (+33.1) of all stop variants.
* **4.5R is not a usable threshold.**
  * Stocks: it was reached by 3 of 228 longs and 0 of 173 shorts, and **changed zero outcomes** with k2=3 (one with k2=2).
  * Crypto: 26 % of trades eventually get there, but by then the 4×ATR ratchet is already close behind. Tightening changes 1 trade (k2=3) or 12 trades (k2=2, −0.56 pp).
  * In practice it never triggers on stocks and does nothing useful on crypto.
* **Caveats.** All open trades are marked at 2026-10-07: only about 7–30 % of stock trades and 6–18 % of crypto trades have actually exited (excluding the early-tighten crypto variants), so the stop variants have barely been tested yet. Everything here is in-sample.

**Verdict.**
* **Ratchet:** adopt it on stocks if you like the property that a stop never moves down. It is safer operationally and costs nothing measurable here (identical results ±0.2 pp, slightly lower R drawdown on shorts). **Do not ratchet the crypto chandelier.** Better still, keep the live crypto fixed 3×ATR, which beat every ratchet/tighten variant (+33.1 % vs +30.3 % or less).
* **Floor:** irrelevant.
* **Tighten after 4.5R:** effectively never triggers (≈1 % of stock trades reach it and it changed 0 stock outcomes), so it is harmless but useless. Lower thresholds (2–3R) only matter on crypto, where they clearly hurt (−4 to −6 pp).
* **What to run:** keep the live policies, use `ChandelierStop(mode='ratchet')` for stocks via the shared module, and drop the tighten rule. If Ilan wants a tighten rule anyway, 2R→k2 on stocks is the only variant that wasn't worse. It rests on 5 trades, so treat it as unproven.

**Reusable files.**
* `iaf/stop_rules.py`: the importable module, documented in its docstring; `ChandelierStop(direction, entry, atr_prev_bar, k=4, mode='ratchet'|'plain'|'floor'|'fixed', tighten_at_R=None, k2=None)`.
* `iaf/stop_policy_scanner.csv`: per-segment recommended call.
* `iaf/ratchet_table.csv`: all 207 segment × policy rows, % and R metrics.
* `iaf/sim_ratchet_trades.csv`: per-trade results, including R%, R-multiple, MFE in R, tightened flag and final stop.


### 3.14 Geometry, volume profile, candles and liquidity zones (`/workspace/scanner_geometry.py`) — PIT backtest on the scanner setups (group follow-up; `iaf/geo_features.py`, `geo_leakcheck.py`, `sim_geo.py`, `geo_analyze.py`, `geo_report.py`; full table N = `iaf/geometry_table.md|csv`)
**Bottom line: expect noise and that is mostly what came out.** 692 comparisons were run in one Benjamini-Hochberg family; 74 had nominal p<0.05 (≈35 expected by chance). After FDR (q<0.10) and every robustness check, **only 2 of 580 filter comparisons survive, both on stock SHORTS and both re-expressing "the stock is already breaking down" — which the existing short rule (score ≥3 & below SMA200) already captures.** No spiral, Gann, candle-pattern or sweep column survives anywhere (best: candles p=0.04, spiral q=0.41, sweeps — 'any sweep in the last 3 bars' on shorts −4.8 pp, q=0.20 — cluster sweeps and prior-candle breaks separately q≥0.5). In the level tests nothing improves on the active policy; liquidity/FVG take-profits and HVN stops on crypto are **robustly worse**. Nothing here gets score weight; the two short-side survivors are candidates to re-check on the setups from 12.10.2026 onward.

**Setup.** Columns = `geometry_columns(df, cutoff, asset, direction)` exactly as written by the teammate (module not modified), computed for 1,040 setups (all rows; tables use the main sheet, no dups). Cutoff = the same information cutoff every earlier table uses (`setups_prepared.info_cutoff_utc`: stocks = rule-bar close, i.e. previous close for pre/intraday alerts and the alert-day bar only for after-close alerts; crypto = alert minute, Perplexity −70 min). Direction view = the setup's direction; liquidity features are re-expressed relative to the trade (*fwd* = target side, e.g. buy-side pools above a long; *back* = stop side). Outcome = the **active policy** trade (stock longs: ratchet chandelier 4×ATR + ½ at Fib 1.618; stock shorts: ratchet chandelier 4×ATR; crypto longs: fixed 3×ATR; close-based; open trades marked at the 2026-10-07 close). `sim_geo.py` reproduces `sim_ratchet_trades.csv` (rt_ratchet_h618 / rt_ratchet / rt_fixed3, c and i) with 0 mismatches (max |diff| 2e-16). Segments: all stock longs (N=242), rule-filtered stock longs (115), Perplexity stock longs (59), Grok stock longs (142), all stock shorts (189), crypto longs (264, Grok 255 + Perplexity 9). Crypto shorts are frozen by the rules and were not tested.

**1. Independent leak check (30 random setups, seed 20261008).** For each setup the columns were computed 4 ways: full history + cutoff; history physically truncated at the rule bar; all bars after the rule bar replaced by random garbage plus 30 extra garbage bars; truncated with cutoff=None. **14,628 column comparisons, 0 mismatches.** 383 `*_confirmed_at` values plus all past-object dates (anchor, spiral, anchored-VP start, sweep, candle bar) and the confirmation dates of every pool used by the level tests: **0 later than the cutoff bar**; last visible bar = rule bar in 30/30. For all 816 main-sheet setups, feeding the module the raw alert time (exact / schedule / UI-log alerts) instead of the tracker cutoff gives the same last visible bar in 100 % of cases (date-only alerts use the conservative tracker cutoff). Verdict: **no look-ahead found**. (Caveat, not a code leak: daily prices are Yahoo dividend-adjusted, as in every earlier table.)

**2. Method.** Filter test = mean x_mkt with the feature − without, per segment; continuous features: lowest quintile vs rest, highest quintile vs rest, and a rank slope (≈ Q5−Q1). Min N 20 on each side (330 candidate comparisons were skipped for N<20 or <5 distinct values and are **not** counted). Sweeps split by `liq_sweep_kind` (pool/cluster sweep vs prior-candle break) and by direction relative to the trade. **p-values are conservative:** the maximum of ticker-clustered, entry-date-clustered and two-way clustered p, because stock setups come from only 22–25 entry dates (the top 5 dates hold 55–60 % of stock trades) — naïve p-values would be far too small. Robust = q<0.10 **and** median difference, raw-return difference, within-entry-date difference, and the difference after dropping the top-1 and top-3 tickers all keep the sign. q<0.10 that fails a check = LUCK.

**Comparisons by family (total 692):**
| kind | family | comparisons | p<0.05 (nominal) | expected by chance | q<0.10 (BH) | ROBUST |
|---|---|---|---|---|---|---|
| filter | candle | 84 | 1 | 4.2 | 0 | 0 |
| filter | gann | 60 | 0 | 3.0 | 0 | 0 |
| filter | liquidity | 218 | 22 | 10.9 | 1 | 1 |
| filter | spiral | 32 | 1 | 1.6 | 0 | 0 |
| filter | vp | 186 | 36 | 9.3 | 1 | 1 |
| level | level | 112 | 14 | 5.6 | 10 | 10 |
| **total** | | **692** | **74** | **34.6** | **12** | **12** |
All 10 robust level-test rows are robustly **worse** than the active policy (crypto targets and HVN stops); none is an improvement.

**Filter comparisons surviving FDR (q<0.10) — total comparisons in the family: 692.** x_mkt in % (excess vs SPY), shorts: ret + SPY return.
| segment | feature | test | N with | N without | x_mkt with | x_mkt without | med x with | med x without | diff x_mkt | diff raw ret | diff within-date | diff 1st half | diff 2nd half | diff w/o top1 | diff w/o top3 | p | q (BH) | p beyond rule inputs | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| All stock SHORT | vp120_beyond_VA_in_trade_dir | with vs without | 38 | 151 | +7.3 | -0.9 | +8.4 | -1.6 | +8.2 | +8.5 | +6.2 | +10.0 | +6.4 | +8.0 | +7.1 | 0.0002 | 0.0150 | 0.0198 | ROBUST |
| All stock SHORT | liq_fwd_pools_n : rank slope (Q5-Q1 equiv.) | rank slope | 189 | 0 | -0.9 | +5.5 | -0.1 | +7.8 | -9.5 | -9.9 | -3.3 | -6.4 | -5.1 | -4.6 | -3.4 | 0.0007 | 0.0453 | 0.0599 | ROBUST |

* **vp120 "beyond value area in trade direction"** for shorts = the close is **below the 120-day volume-profile value area**. 37 of these 38 shorts already pass the short rule (score ≥3 & below SMA200), so it is mostly a stricter version of the rule. Inside the 60 rule-filtered shorts: below VA120 (N=37, 30 tickers, 11 dates) +6.2 % mean / +6.8 % median / +7.3 vs SPY / 81 % hit vs the other 23 rule-passers +1.2 % / +1.6 % / +2.3 vs SPY / 61 % hit (descriptive, not in the FDR family). It also stays significant after controlling for the rule inputs (p≈0.02). This is the only lead worth carrying forward, as a **candidate refinement of the short rule**, to be validated on the new setups.
* **liq_fwd_pools_n** for shorts = number of untaken swing-low pools below the price. Fewer pools (price at or under its recent lows) → better shorts. Same story: a breakdown/momentum proxy; 43 of the 49 shorts with ≤1 such pool already pass the short rule. After controlling for the rule inputs it is no longer significant (p≈0.06).

**Closest misses (nominal p<0.05, fail FDR) — total comparisons: 692.** Listed only so nobody re-discovers them as "signals":
| segment | feature | test | N with | N without | diff x_mkt | diff within-date | diff w/o top3 | p | q (BH) |
|---|---|---|---|---|---|---|---|---|---|
| All stock SHORT | liq_back_pool_dist_atr : rank slope (Q5-Q1 equiv.) | rank slope | 159 | 0 | +12.2 | +5.0 | +5.0 | 0.0021 | 0.1144 |
| All stock SHORT | liq_fvg_open_n : Q5 (highest 20%) vs rest | Q5 vs rest | 38 | 151 | -5.6 | -3.6 | -2.9 | 0.0031 | 0.1514 |
| All stock SHORT | vp60_hvn_absdist_atr : rank slope (Q5-Q1 equiv.) | rank slope | 189 | 0 | +7.5 | +2.5 | +2.7 | 0.0034 | 0.1518 |
| Rule-filtered stock LONG | liq_fwd_fvg_exists | with vs without | 72 | 43 | +7.7 | +3.5 | +4.6 | 0.0039 | 0.1518 |
| Rule-filtered stock LONG | vp120_hvn_absdist_atr : Q5 (highest 20%) vs rest | Q5 vs rest | 23 | 92 | -8.2 | -5.9 | -5.2 | 0.0041 | 0.1518 |
| Rule-filtered stock LONG | vp120_beyond_VA_in_trade_dir | with vs without | 39 | 76 | -7.6 | -3.2 | -4.7 | 0.0042 | 0.1518 |
| Crypto LONG | vp120_poc_dist_atr_signed (+ = beyond POC in trade dir) : Q5 (highest 20%) vs rest | Q5 vs rest | 53 | 211 | -15.6 | -5.1 | -10.4 | 0.0048 | 0.1580 |
| All stock SHORT | vp60_poc_dist_atr_signed (+ = beyond POC in trade dir) : Q5 (highest 20%) vs rest | Q5 vs rest | 38 | 151 | +6.5 | +4.4 | +5.1 | 0.0051 | 0.1604 |
| Rule-filtered stock LONG | vp120_inside_VA | with vs without | 68 | 47 | +8.4 | +5.8 | +5.1 | 0.0064 | 0.1913 |
| All stock SHORT | liq_sweep_any (last 3 bars) | with vs without | 143 | 46 | -4.8 | -5.6 | -3.6 | 0.0073 | 0.2036 |
| All stock SHORT | vpanc_poc_dist_atr_signed (+ = beyond POC in trade dir) : Q5 (highest 20%) vs rest | Q5 vs rest | 38 | 151 | +5.6 | +3.7 | +4.4 | 0.0074 | 0.2036 |
| All stock LONG | vp120_inside_VA | with vs without | 144 | 98 | +5.9 | +4.1 | +4.2 | 0.0081 | 0.2147 |
A consistent but non-significant pattern on stock longs: being **inside** the 60/120-day value area beat being extended above it (rule-filtered longs +7 to +8 pp, all longs +3 to +6 pp; q 0.19–0.37). Plausible (do not chase extended names), but not proven here.

**3. Level tests** (paired vs the active policy on covered trades; close-based shown, intraday in table N — total comparisons in the family: 692). *Stop* = nearest confirmed object beyond the entry −0.5×ATR14 (pool = untaken equal/swing-low cluster, OB = unmitigated order-block zone, HVN = 60/120-bar profile node); `fix` = that level only, `hyb` = the tighter of the level and the policy stop. *Target* = next untaken liquidity pool or open FVG edge in the trade direction, full exit or ½, replacing the 1.618 half on stock longs. No object beyond the entry → the trade stays on the active policy and is not counted.
| segment | variant | N covered | coverage % | level dist (ATR, median) | % trades changed | mean variant | mean policy | median variant | median policy | hit variant | hit policy | x_mkt variant | x_mkt policy | paired diff | diff w/o top3 | p | q (BH) | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| All stock LONG | stop: nearest HVN -0.5ATR (fixed) (close) | 188 | 78 | 1.3 | 37 | +1.4 | +2.8 | -1.1 | +0.5 | 44 | 56 | +0.6 | +1.5 | -1.4 | -0.3 | 0.1000 | 0.5242 | noise |
| All stock LONG | stop: tighter of HVN-0.5ATR and policy stop (close) | 188 | 78 | 1.3 | 36 | +1.4 | +2.8 | -1.1 | +0.5 | 44 | 56 | +0.7 | +1.5 | -1.4 | -0.3 | 0.1081 | 0.5311 | noise |
| All stock LONG | stop: order-block zone -0.5ATR (fixed) (close) | 97 | 40 | 6.6 | 12 | +1.8 | +1.5 | +0.4 | +0.4 | 56 | 56 | +0.3 | +0.1 | +0.3 | -0.2 | 0.5229 | 0.8045 | noise |
| All stock LONG | stop: tighter of OB-0.5ATR and policy stop (close) | 97 | 40 | 6.6 | 3 | +1.3 | +1.5 | +0.3 | +0.4 | 55 | 56 | -0.0 | +0.1 | -0.2 | +0.0 | 0.4456 | 0.7734 | noise |
| All stock LONG | stop: nearest liquidity pool beyond entry -0.5ATR (fixed) (close) | 217 | 90 | 3.0 | 24 | +3.0 | +3.1 | +0.4 | +0.5 | 54 | 56 | +1.7 | +1.8 | -0.1 | +0.4 | 0.7347 | 0.9184 | noise |
| All stock LONG | stop: tighter of pool-0.5ATR and policy stop (close) | 217 | 90 | 3.0 | 16 | +2.7 | +3.1 | +0.1 | +0.5 | 52 | 56 | +1.6 | +1.8 | -0.4 | +0.1 | 0.2377 | 0.6452 | noise |
| All stock LONG | target: next open FVG edge, full exit (close) | 148 | 61 | 0.9 | 50 | +2.1 | +2.7 | +1.9 | +0.6 | 63 | 53 | +1.4 | +1.7 | -0.7 | +0.7 | 0.5223 | 0.8045 | noise |
| All stock LONG | target: next open FVG edge, 1/2 exit (close) | 148 | 61 | 0.9 | 45 | +2.5 | +2.7 | +1.0 | +0.6 | 58 | 53 | +1.5 | +1.7 | -0.2 | +0.3 | 0.6511 | 0.8732 | noise |
| All stock LONG | target: next liquidity pool, full exit (close) | 213 | 88 | 2.3 | 37 | +2.0 | +3.3 | +1.0 | +0.6 | 59 | 55 | +1.1 | +2.1 | -1.3 | -0.4 | 0.0992 | 0.5242 | noise |
| All stock LONG | target: next liquidity pool, 1/2 exit (close) | 213 | 88 | 2.3 | 33 | +2.7 | +3.3 | +0.8 | +0.6 | 58 | 55 | +1.5 | +2.1 | -0.6 | -0.2 | 0.0740 | 0.5079 | noise |
| Rule-filtered stock LONG | stop: nearest HVN -0.5ATR (fixed) (close) | 98 | 85 | 1.4 | 26 | +3.5 | +3.8 | +0.5 | +1.0 | 56 | 61 | +2.5 | +2.4 | -0.3 | +0.1 | 0.3707 | 0.7309 | noise |
| Rule-filtered stock LONG | stop: tighter of HVN-0.5ATR and policy stop (close) | 98 | 85 | 1.4 | 24 | +3.6 | +3.8 | +0.5 | +1.0 | 56 | 61 | +2.6 | +2.4 | -0.2 | +0.1 | 0.4717 | 0.7879 | noise |
| Rule-filtered stock LONG | stop: order-block zone -0.5ATR (fixed) (close) | 55 | 48 | 7.3 | 7 | +1.7 | +1.6 | +0.5 | +0.5 | 62 | 60 | +0.2 | +0.2 | +0.1 | -0.2 | 0.7192 | 0.9166 | noise |
| Rule-filtered stock LONG | stop: nearest liquidity pool beyond entry -0.5ATR (fixed) (close) | 109 | 95 | 3.4 | 17 | +4.4 | +3.9 | +1.4 | +1.0 | 63 | 60 | +3.1 | +2.6 | +0.5 | +0.2 | 0.2174 | 0.6224 | noise |
| Rule-filtered stock LONG | stop: tighter of pool-0.5ATR and policy stop (close) | 109 | 95 | 3.4 | 10 | +4.2 | +3.9 | +1.0 | +1.0 | 60 | 60 | +3.0 | +2.6 | +0.3 | +0.0 | 0.2534 | 0.6591 | noise |
| Rule-filtered stock LONG | target: next open FVG edge, full exit (close) | 60 | 52 | 0.7 | 68 | +5.3 | +7.3 | +4.4 | +3.4 | 80 | 67 | +4.9 | +6.4 | -2.0 | +0.7 | 0.3313 | 0.7030 | noise |
| Rule-filtered stock LONG | target: next open FVG edge, 1/2 exit (close) | 60 | 52 | 0.7 | 58 | +6.6 | +7.3 | +4.5 | +3.4 | 77 | 67 | +5.7 | +6.4 | -0.7 | +0.2 | 0.4017 | 0.7557 | noise |
| Rule-filtered stock LONG | target: next liquidity pool, full exit (close) | 93 | 81 | 1.9 | 42 | +2.7 | +5.4 | +1.1 | +1.1 | 63 | 61 | +1.9 | +4.2 | -2.7 | -0.9 | 0.1018 | 0.5294 | noise |
| Rule-filtered stock LONG | target: next liquidity pool, 1/2 exit (close) | 93 | 81 | 1.9 | 39 | +4.3 | +5.4 | +1.0 | +1.1 | 61 | 61 | +3.1 | +4.2 | -1.1 | -0.4 | 0.0842 | 0.5079 | noise |
| Perplexity stock LONG | stop: nearest HVN -0.5ATR (fixed) (close) | 41 | 69 | 1.3 | 44 | +2.8 | +4.1 | -2.6 | +0.6 | 39 | 54 | +2.6 | +3.3 | -1.3 | -0.0 | 0.1715 | 0.5880 | noise |
| Perplexity stock LONG | stop: tighter of HVN-0.5ATR and policy stop (close) | 41 | 69 | 1.3 | 44 | +2.8 | +4.1 | -2.6 | +0.6 | 39 | 54 | +2.6 | +3.3 | -1.3 | -0.0 | 0.1715 | 0.5880 | noise |
| Perplexity stock LONG | stop: nearest liquidity pool beyond entry -0.5ATR (fixed) (close) | 52 | 88 | 2.7 | 37 | +3.7 | +3.6 | -0.1 | +0.3 | 50 | 52 | +3.3 | +3.1 | +0.1 | -0.9 | 0.9278 | 0.9763 | noise |
| Perplexity stock LONG | stop: tighter of pool-0.5ATR and policy stop (close) | 52 | 88 | 2.7 | 25 | +2.8 | +3.6 | -2.1 | +0.3 | 42 | 52 | +2.6 | +3.1 | -0.8 | +0.8 | 0.4777 | 0.7909 | noise |
| Perplexity stock LONG | target: next open FVG edge, full exit (close) | 42 | 71 | 0.8 | 60 | +4.9 | +6.3 | +4.1 | +0.7 | 74 | 55 | +5.1 | +6.4 | -1.5 | +2.2 | 0.5910 | 0.8381 | noise |
| Perplexity stock LONG | target: next open FVG edge, 1/2 exit (close) | 42 | 71 | 0.8 | 57 | +6.5 | +6.3 | +1.5 | +0.7 | 69 | 55 | +6.5 | +6.4 | +0.1 | -1.1 | 0.8816 | 0.9662 | noise |
| Perplexity stock LONG | target: next liquidity pool, full exit (close) | 53 | 90 | 2.3 | 43 | +2.7 | +5.3 | +1.8 | +0.8 | 60 | 55 | +2.8 | +5.1 | -2.7 | +0.3 | 0.1949 | 0.6001 | noise |
| Perplexity stock LONG | target: next liquidity pool, 1/2 exit (close) | 53 | 90 | 2.3 | 42 | +4.7 | +5.3 | +1.1 | +0.8 | 57 | 55 | +4.5 | +5.1 | -0.7 | +0.1 | 0.2243 | 0.6260 | noise |
| Grok stock LONG | stop: nearest HVN -0.5ATR (fixed) (close) | 111 | 78 | 1.3 | 37 | +1.0 | +2.3 | -1.1 | +0.4 | 45 | 57 | -0.0 | +0.8 | -1.4 | -0.3 | 0.0995 | 0.5242 | noise |
| Grok stock LONG | stop: tighter of HVN-0.5ATR and policy stop (close) | 111 | 78 | 1.3 | 35 | +1.0 | +2.3 | -1.1 | +0.4 | 45 | 57 | +0.0 | +0.8 | -1.3 | -0.2 | 0.1140 | 0.5311 | noise |
| Grok stock LONG | stop: order-block zone -0.5ATR (fixed) (close) | 61 | 43 | 7.0 | 13 | +2.3 | +2.2 | +0.4 | +0.4 | 59 | 61 | +0.7 | +0.7 | +0.1 | -0.4 | 0.8643 | 0.9635 | noise |
| Grok stock LONG | stop: tighter of OB-0.5ATR and policy stop (close) | 61 | 43 | 7.0 | 5 | +1.9 | +2.2 | +0.4 | +0.4 | 59 | 61 | +0.4 | +0.7 | -0.3 | +0.1 | 0.4517 | 0.7748 | noise |
| Grok stock LONG | stop: nearest liquidity pool beyond entry -0.5ATR (fixed) (close) | 125 | 88 | 3.2 | 18 | +2.1 | +2.5 | +0.4 | +0.4 | 54 | 57 | +0.5 | +0.9 | -0.5 | +0.3 | 0.3322 | 0.7030 | noise |
| Grok stock LONG | stop: tighter of pool-0.5ATR and policy stop (close) | 125 | 88 | 3.2 | 13 | +2.1 | +2.5 | +0.4 | +0.4 | 54 | 57 | +0.7 | +0.9 | -0.4 | +0.2 | 0.3436 | 0.7149 | noise |
| Grok stock LONG | target: next open FVG edge, full exit (close) | 86 | 61 | 1.0 | 44 | +0.8 | +0.6 | +0.7 | +0.4 | 57 | 52 | -0.3 | -0.8 | +0.1 | -0.7 | 0.8961 | 0.9689 | noise |
| Grok stock LONG | target: next open FVG edge, 1/2 exit (close) | 86 | 61 | 1.0 | 37 | +0.5 | +0.6 | +0.5 | +0.4 | 52 | 52 | -1.0 | -0.8 | -0.2 | +0.3 | 0.7006 | 0.9045 | noise |
| Grok stock LONG | target: next liquidity pool, full exit (close) | 123 | 87 | 2.4 | 37 | +1.4 | +2.1 | +0.8 | +0.4 | 59 | 56 | +0.2 | +0.6 | -0.7 | +0.0 | 0.2961 | 0.7017 | noise |
| Grok stock LONG | target: next liquidity pool, 1/2 exit (close) | 123 | 87 | 2.4 | 33 | +1.6 | +2.1 | +0.8 | +0.4 | 59 | 56 | +0.1 | +0.6 | -0.5 | -0.0 | 0.2177 | 0.6224 | noise |
| All stock SHORT | stop: nearest HVN -0.5ATR (fixed) (close) | 130 | 69 | 1.2 | 42 | +0.4 | -0.1 | -1.3 | -0.3 | 45 | 49 | +1.5 | +1.2 | +0.6 | -0.2 | 0.4385 | 0.7683 | noise |
| All stock SHORT | stop: tighter of HVN-0.5ATR and policy stop (close) | 130 | 69 | 1.2 | 40 | +0.5 | -0.1 | -1.3 | -0.3 | 45 | 49 | +1.6 | +1.2 | +0.7 | -0.1 | 0.3440 | 0.7149 | noise |
| All stock SHORT | stop: order-block zone -0.5ATR (fixed) (close) | 40 | 21 | 7.9 | 12 | +2.0 | +2.7 | +6.3 | +6.3 | 75 | 75 | +3.1 | +3.8 | -0.7 | +0.4 | 0.4188 | 0.7585 | noise |
| All stock SHORT | stop: nearest liquidity pool beyond entry -0.5ATR (fixed) (close) | 159 | 84 | 2.9 | 31 | -0.7 | -0.8 | -1.8 | -1.6 | 43 | 44 | +0.5 | +0.6 | +0.0 | -0.5 | 0.9536 | 0.9846 | noise |
| All stock SHORT | stop: tighter of pool-0.5ATR and policy stop (close) | 159 | 84 | 2.9 | 25 | -0.4 | -0.8 | -1.8 | -1.6 | 43 | 44 | +0.9 | +0.6 | +0.4 | -0.1 | 0.3378 | 0.7083 | noise |
| All stock SHORT | target: next open FVG edge, full exit (close) | 133 | 70 | 1.1 | 36 | -1.1 | -1.6 | -0.5 | -2.0 | 49 | 38 | -0.3 | -0.2 | +0.5 | -0.0 | 0.2989 | 0.7017 | noise |
| All stock SHORT | target: next open FVG edge, 1/2 exit (close) | 133 | 70 | 1.1 | 36 | -1.4 | -1.6 | -0.8 | -2.0 | 43 | 38 | +0.1 | -0.2 | +0.3 | -0.0 | 0.2989 | 0.7017 | noise |
| All stock SHORT | target: next liquidity pool, full exit (close) | 164 | 87 | 2.6 | 19 | -1.6 | -1.7 | -1.4 | -2.0 | 45 | 39 | -0.6 | -0.3 | +0.1 | -0.4 | 0.8389 | 0.9628 | noise |
| All stock SHORT | target: next liquidity pool, 1/2 exit (close) | 164 | 87 | 2.6 | 19 | -1.6 | -1.7 | -1.7 | -2.0 | 43 | 39 | -0.3 | -0.3 | +0.0 | -0.2 | 0.8389 | 0.9628 | noise |
| Crypto LONG | stop: nearest HVN -0.5ATR (fixed) (close) | 243 | 92 | 1.5 | 31 | +22.5 | +33.0 | +15.5 | +31.1 | 62 | 86 | +8.7 | +13.0 | -10.5 | -5.9 | 0.0046 | 0.1577 | nominal p<0.05 only (fails FDR) |
| Crypto LONG | stop: tighter of HVN-0.5ATR and policy stop (close) | 243 | 92 | 1.5 | 30 | +22.3 | +33.0 | +15.2 | +31.1 | 61 | 86 | +8.5 | +13.0 | -10.7 | -6.3 | 0.0038 | 0.1518 | nominal p<0.05 only (fails FDR) |
| Crypto LONG | stop: order-block zone -0.5ATR (fixed) (close) | 117 | 44 | 5.9 | 9 | +29.1 | +24.2 | +10.8 | +8.6 | 79 | 74 | +17.5 | +13.6 | +4.9 | +0.0 | 0.1878 | 0.5993 | noise |
| Crypto LONG | stop: tighter of OB-0.5ATR and policy stop (close) | 117 | 44 | 5.9 | 2 | +23.6 | +24.2 | +7.9 | +8.6 | 72 | 74 | +13.6 | +13.6 | -0.6 | +0.0 | 0.3360 | 0.7069 | noise |
| Crypto LONG | stop: nearest liquidity pool beyond entry -0.5ATR (fixed) (close) | 262 | 99 | 2.8 | 13 | +30.0 | +33.4 | +28.5 | +31.6 | 81 | 87 | +11.1 | +12.5 | -3.4 | +0.6 | 0.1571 | 0.5662 | noise |
| Crypto LONG | stop: tighter of pool-0.5ATR and policy stop (close) | 262 | 99 | 2.8 | 10 | +29.2 | +33.4 | +28.5 | +31.6 | 79 | 87 | +10.9 | +12.5 | -4.2 | -0.5 | 0.0744 | 0.5079 | noise |
| Crypto LONG | target: next open FVG edge, full exit (close) | 155 | 59 | 1.7 | 98 | +11.3 | +45.9 | +11.6 | +37.0 | 97 | 97 | +3.9 | +17.1 | -34.6 | -26.1 | <0.0001 | 0.0046 | ROBUST |
| Crypto LONG | target: next open FVG edge, 1/2 exit (close) | 155 | 59 | 1.7 | 98 | +28.6 | +45.9 | +27.8 | +37.0 | 97 | 97 | -0.2 | +17.1 | -17.3 | -13.0 | <0.0001 | 0.0046 | ROBUST |
| Crypto LONG | target: next liquidity pool, full exit (close) | 238 | 90 | 1.4 | 91 | +11.4 | +36.8 | +10.5 | +32.9 | 92 | 91 | +3.6 | +13.9 | -25.4 | -24.4 | 0.0002 | 0.0153 | ROBUST |
| Crypto LONG | target: next liquidity pool, 1/2 exit (close) | 238 | 90 | 1.4 | 91 | +24.1 | +36.8 | +24.6 | +32.9 | 91 | 91 | +1.2 | +13.9 | -12.7 | -12.2 | 0.0002 | 0.0153 | ROBUST |

* **Stocks: no level rule beats the 4×ATR chandelier.** Pool stops (median 2.7–3.4 ATR from entry vs 4 ATR) change 10–37 % of trades and move the mean by −0.8 to +0.5 pp. HVN stops (≈1.2–1.4 ATR) change 25–44 %, cost 0.2–1.4 pp on longs and cut the hit rate (e.g. all longs 56 → 44 %); on shorts +0.6 pp, noise. OB stops sit ≈6.5–8 ATR away and rarely bind (±0.7 pp). Liquidity / FVG targets raise the hit rate (all longs 53–55 → 58–63 %, rule-filtered 61–67 → 61–80 %) but lower the mean by up to 2.7 pp on longs — the same trade-off as the Fib targets in §3.12; on shorts they change ≤0.5 pp. No stock level difference survives FDR (best q ≈0.3).
* **Crypto: liquidity / FVG targets are robustly harmful.** The nearest pool / FVG sits only ≈1.4–1.7 ATR above entry, so 90–98 % of trades exit early: −13 to −20 pp per covered trade for ½ exits, −25 to −40 pp for full exits (q ≤0.02, robust to dropping the top-3 coins). HVN stops (≈1.5 ATR) are also worse (−10.5 pp close, −13.5 pp intraday; robust at q 0.05 intraday). Pool stops: −3.4 pp, not significant. OB stops: +4.9 pp on 117 trades, p 0.19, noise.

**What this means for the scanner**
* Keep every geometry / volume-profile / candle / liquidity column at **weight 0** (logging only). Spiral, Gann, all 26 candle patterns and the sweep columns (either kind) show nothing.
* **Do not** use liquidity pools, FVGs, order blocks or HVNs as stops or take-profits instead of the active policy; for crypto they are clearly worse.
* The only thing to watch on new setups from 12.10.2026: **stock shorts whose close is below the 120-day value area** (vp120_va_pos = "below VA"), as a possible tightening of the existing short rule. Needs ≈30 closed new trades before any weight.
* Caveats: in-sample, ≈3½ months, 22–25 stock entry dates, most stock trades still open (marked 2026-10-07); clustering-robust p-values are themselves approximate with this few dates.


## 4. AgenticTrading (Open-Finance-Lab) — hands-on
**Architecture (as cloned, commit bdccc9a):**
* `dashboard/backend` is a FastAPI app with SQLite/Postgres. It covers backtests, a **leaderboard with baselines** (buy-and-hold, equal-weight, DJIA/index, mean-variance, LLM agents), a contest window designed against in-window lookahead, a **paper-trading** router (`/paper/account|positions|trades|portfolio-history|start-session`) through `AlpacaPaperTradingClient`, and Robinhood live (forced off by `ROBINHOOD_EXECUTE=false`).
* Data: an Alpaca bars cache, a **vn.py simulated data** source, and iFinD A-shares.
* LLM gateways: OpenAI, Anthropic, DeepSeek, CommonStack, OpenRouter (base URL overridable), plus an `openai_compatible` adapter. There is also an AI-Hedge-Fund bridge and a TradingAgents adapter (T+1, one US stock, long-only, Alpaca hourly bars).
* `orchestration/FinAgents` holds the older multi-agent pools (alpha/risk/portfolio/memory, with a neo4j memory option).
* Engine fills at **next-bar open** (documented lookahead-free). There are about 5.6k backend tests (**NOT RUN**).
* There is an **external-agent API** (`/api/v1/backtest/...`) where an outside agent submits `{action, symbol, confidence, reasoning, stop_loss_price, take_profit_price}` per step. That is the natural hook if we wanted our scanner on their leaderboard.

**Runs**
| run | data | result |
|---|---|---|
| Smoke test, no keys (`run_local_safe.sh`) | vnpy simulation, 2026-03-16..03-27, DJIA-30 | Agent 0 trades (0.0 %), buy-and-hold −1.86 %, DJIA −3.06 %. Rule-based, so the LLM is forced off on simulated data |
| **With Alpaca paper keys** (mapped `ALPACA_API_KEY_ID→ALPACA_API_KEY`, `ALPACA_API_SECRET_KEY→ALPACA_SECRET_KEY` at server start only, never printed or stored; all LLM keys blanked; Robinhood off) | **real Alpaca 60-min bars**, 2026-09-14..09-25, 10 scanner tickers (AMD, PANW, META, INTC, SOFI, PLTR, HOOD, F, PFE, KO), capital $3,000 (API maximum) | Rule-based agent **−0.10 %** (2 trades, Sharpe −2.6), buy-and-hold **+2.71 %**, DJIA index **−1.00 %**. 70 decision steps, `decision_provenance=rule_based` |
| Paper account (read-only) | Alpaca paper API via `/paper/account`, `/positions`, `/trades` | Connected: equity $100,000, cash $100,000, buying power $400,000, 0 positions. **I did not call `/paper/start-session` or place any order** |
| LLM backtest | — | **Blocked:** `"model is required when decision_source='llm'"`, then `"Sign in before running an LLM backtest."` LLM runs need a signed-in local user **and** a provider key |

**Keys and what they unlock** (none of the LLM keys are in env; nothing invented):
| key | unlocks | status |
|---|---|---|
| `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` | real US bars (hourly), paper account views, paper sessions | **available now** (from `ALPACA_API_KEY_ID`/`ALPACA_API_SECRET_KEY`); used |
| one of `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`, `COMMONSTACK_API_KEY` | LLM agents/pipelines, LLM leaderboard entries | **missing**. Plus a local signed-in user is required |
| `FINGPT_API_KEY` | news sentiment agent | missing |
| Financial Datasets key | AI-Hedge-Fund bridge | missing |
| Robinhood credentials | live trading | not wanted (forced off) |
**Local LLM:** pointing `OPENROUTER_BASE_URL` or the `openai_compatible` adapter at Ollama's `/v1` looks plausible from the code, but was **NOT tested end-to-end** (it also needs the sign-in step; Ollama was left untouched, no models pulled).

**Fit for our scanner:**
* Constraints: hourly US equities; $3k capital cap; 14-day window cap on the run API; no replay of an external list of time-stamped setups with our PIT cut-offs; no crypto in the default universe; shorts not part of the default rule agent.
* Useful: a public-style **arena** (leaderboard vs baselines) and a fully logged per-decision reasoning trail if we run LLM agents.

## 5. AgenticTrading vs TradingAgents as an approve / flag / veto layer
| criterion | AgenticTrading | TradingAgents |
|---|---|---|
| Maturity | 768★, very active (daily commits), big surface area (dashboard, billing, Discord, Robinhood) → many moving parts; custom licence (OpenMDW-1.0) | ≈110k★, v0.6.0, focused library, Apache-2.0 |
| Decision structure | rule/LLM agent or sub-agent pipeline; risk step records a `reasoning` per order | analysts → **bull vs bear debate** → trader → **risk-manager debate** → final; maps directly onto approve/flag/veto |
| Reasoning logs | per-order `reasoning`/`rationale` and run evidence stored in its DB | full per-ticker/date state logs of every analyst report and debate turn |
| Leaderboard vs baselines | **yes** (buy-and-hold, equal-weight, index, mean-variance, LLM agents) | no built-in leaderboard |
| Point-in-time data | next-bar-open fills; contest window built to avoid in-window lookahead; but bars are its own Alpaca hourly cache, not our setup timestamps | **date-window guards on every dated data path** (`dataflows/date_window.py`): pass the alert's cut-off date and tools only see data ≤ it |
| Local / OpenAI-compatible LLM | gateway adapters; needs sign-in + key handling | `backend_url` / `TRADINGAGENTS_LLM_BACKEND_URL` → Ollama `/v1` directly |
| Effort to bolt onto the scanner | high (run its server; adapt to its universe and limits) | low-moderate (call `propagate(ticker, cutoff_date)` per setup and map the final decision + risk verdict to approve/flag/veto) |
**Recommendation:** use **TradingAgents** for the veto layer, with its date guard set to each setup's `info_cutoff_utc`, a local Ollama model for cost, and the reasoning logs stored next to each setup. Use AgenticTrading at most as an optional **arena**: submit the scanner's decisions through its external-agent API to get leaderboard-style comparisons against its baselines.

## 6. Recommendations & how they plug into the scanner
1. **IAF: MAYBE / adopt with caveats.**
   * Keep **our PIT layer** (`iaf/prep.py` decision table + compressed close-labelled clock) as the source of truth, and use IAF v8 only as the accounting/stop/cost engine plus report/MCP generator.
   * Write `set_blotter(SimulationBlotter(FixedBasisPointsSlippage, PercentageCommission))` explicitly.
   * Serialise runs (one SQLite per working directory).
   * Shorts, Monte Carlo and walk-forward need **v9** (shorts verified on a synthetic series). Pilot v9 only once it leaves alpha (API still breaking: `Study`/`run_configuration`), and re-run the same agreement check (§2.4) on v9 before trusting it.
   * Until then, the plain pandas replay (`iaf/sim.py`) is faster and already covers shorts and benchmarks.
2. **IAF MCP: adopt** for bot queries over saved IAF bundles (use the `python -m …mcp_server` entry). Keep scanner-level analytics (benchmarks, LOTO, luck flags) in our own `analyze.py` tables, because the MCP has none of that.
3. **AgenticTrading: skip** as the veto base. Optional arena via the external-agent API.
4. **Scanner rules, supported by this data (in-sample):**
   * Keep **no prebreakout longs**, **no crypto shorts**, and **shorts only with score ≥ 3 & < SMA200** (the most robust result here).
   * Keep the **sector-uptrend filter** for stock longs.
   * **Drop the % trailing stop on longs.** If a trailing stop is wanted for stocks, use a **chandelier at k≈4×ATR14** (or a fixed 3×ATR); never k=2. For Grok crypto longs, hold or a fixed 3×ATR. **Elliott/fib structure stops are not worth it**; if used at all, only the swing origin − 1.0×ATR checked on daily closes, never intraday. **Profit targets:** none on crypto (at most the Elliott wave-3/5 target where a valid count exists). For stocks, an optional resting 1.618 limit (full, or ½ with the rest under a 4×ATR chandelier) if Ilan prefers a higher hit rate and median over the occasional big runner. Not for Perplexity-style catalyst names.
   * **Stop mechanics (§3.13):** run stops through `iaf/stop_rules.ChandelierStop`. Use `mode='ratchet'` for stock longs and shorts (same results, and the stop never loosens). Keep crypto on fixed 3×ATR, with no crypto ratchet. Drop the 4.5R tighten rule: it never fires on stocks.
   * **Don't adopt Fibonacci exits**.
   * Report crypto longs **vs BTC/basket**, not vs SPY. The true value-add is ≈+3 to +15 pp mean (≈+1 to +5 pp median), not the +23 to +37 % headline.
   * Treat Perplexity stock longs, the original sheet, Bot and Ilan as **luck-driven until more samples arrive**.
5. **Next:** a walk-forward split (train ≤ Aug, test Sep–Oct); beta-adjusted crypto excess; borrow costs for shorts; re-run the exact-minute test as more intraday alerts accrue.

## 7. NOT run / limitations (plain)
* AgenticTrading **LLM** backtests: no LLM key in env, and a local sign-in is required. Not done. **No paper orders/sessions were started** (only read-only account views). The backend test suite was not run.
* IAF v9 Monte Carlo, vector engine, Veto/ScoreCard, and walk-forward on real data: not run (only the v9 short probe).
* IAF v8 cannot short: shorts come from the independent replay.
* Untestable rows: 3 main rows without an alert date; main crypto rows without price data; 60 timed crypto setups without Alpaca minute data.
* No borrow fees; daily-close stop evaluation (except the "intraday" fib/ATR variant); no beta adjustment; rules evaluated in-sample.
* Ollama: untouched, no models pulled. Tracker files: read-only.

## 8. Paths (all under `/workspace/trading-frameworks-eval/`)
* Report: `results.md` (this file).
* Full tables: `iaf/analysis_tables.md`, `iaf/minute_vs_daily.md`, `iaf/excluded_table.md`.
* Trades: `iaf/trades_{stock,crypto}_{hold,fsetup,f8,t5,t8,t12}.csv` (IAF), `iaf/sim_trades*.csv`, `iaf/sim_fib_trades.csv`, `iaf/fib_structure.csv`, `iaf/sim_minute_trades.csv`, `iaf/minute_entries.csv`, `iaf/bench_minute.csv`; enriched `iaf/iaf_trades_enriched.csv`, `iaf/sim_trades_enriched.csv`.
* Code: `iaf/prep.py`, `run_iaf.py`, `run_iaf_save.py`, `sim.py`, `sim_fib.py`, `sim_chand.py` (trades → `iaf/sim_chand_trades.csv`, table → `iaf/chandelier_table.md|csv`), `sim_struct.py` (trades → `iaf/sim_struct_trades.csv`, table → `iaf/structure_table.md|csv`), `sim_targets.py` (trades → `iaf/sim_targets_trades.csv`, Elliott coverage → `iaf/elliott_coverage.csv`, table → `iaf/targets_table.md|csv`), `stop_rules.py` (shared stop module) + `sim_ratchet.py` (trades → `iaf/sim_ratchet_trades.csv`) + `analyze_ratchet.py` (table → `iaf/ratchet_table.md|csv`) + `check_stop_rules.py` (regression check) + `stop_policy_scanner.csv`, `fetch_minute.py`, `sim_minute.py`, `analyze.py`, `compare_minute.py`, `semantics_test*.py`; `v9probe/short_probe.py`; `mcp/mcp_client.py` + `mcp/mcp_session.json`; saved IAF bundle `iaf/saved_backtests/`.
* AgenticTrading: `agentic-repo/`, `atl-runs.json` (vnpy), `atl-runs-alpaca.json` (Alpaca run), `atl-server*.log`. Servers stopped.
* Geometry (§3.14): `iaf/geo_features.py` (→ `iaf/geo_features.pkl`), `geo_leakcheck.py` (→ `geo_leakcheck.csv`, `geo_leakcheck_mismatches.csv`), `sim_geo.py` (→ `sim_geo_trades.csv`), `geo_analyze.py` (→ `geometry_table.csv`, `geo_results.pkl`), `geo_report.py` (→ `geometry_table.md`, `geo_section.md`), `geo_short_check.py` (descriptive short-rule overlap). Run with `venv-geo/bin/python`.
* Venvs: `venv-iaf8`, `venv-iaf9`, `venv-agentic`, `venv-geo` (pandas 3.0.6 / numpy 2.5.3 + scipy, statsmodels, pyarrow; used for §3.14).

---
## Appendix — full analysis tables (generated by `iaf/analyze.py`)
### A. IAF event engine vs independent pandas replay (longs, all setups incl. excluded rows)
| asset_run | policy | N | identical | mean_iaf | mean_sim | max_abs_diff |
|---|---|---|---|---|---|---|
| crypto | f8 | 301 | +100.0 | +28.3 | +28.3 | +0.0 |
| crypto | fsetup | 301 | +99.3 | +26.4 | +26.4 | +0.9 |
| crypto | hold | 301 | +100.0 | +38.4 | +38.4 | +0.0 |
| crypto | t12 | 301 | +100.0 | +24.2 | +24.2 | +0.0 |
| crypto | t5 | 301 | +100.0 | +10.5 | +10.5 | +0.0 |
| crypto | t8 | 301 | +100.0 | +17.4 | +17.4 | +0.0 |
| stock | f8 | 280 | +99.6 | +0.9 | +0.9 | +11.0 |
| stock | fsetup | 280 | +98.9 | +1.3 | +1.3 | +22.8 |
| stock | hold | 280 | +100.0 | +1.0 | +1.0 | +0.0 |
| stock | t12 | 280 | +100.0 | +1.0 | +1.0 | +0.0 |
| stock | t5 | 280 | +100.0 | +0.4 | +0.4 | +0.0 |
| stock | t8 | 280 | +100.0 | +0.5 | +0.5 | +0.0 |

### B. STOCK LONGS — ALL longs — IAF event engine, net of costs
| group | policy | N | mean | median | hit | x_spy | xmed_spy | mean_wo_top1 | mean_wo_top3 | x_spy_wo_top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Bot stock | hold, no stop | 30 | +2.3 | +0.3 | 53 | +1.0 | -1.0 | +1.3 | -0.3 | -1.6 | LUCK (edge gone w/o top tickers) |
| Bot stock | setup's own stop (fixed) | 30 | +1.9 | -0.2 | 50 | +1.1 | -1.0 | +0.9 | -0.7 | -1.5 | LUCK (edge gone w/o top tickers) |
| Bot stock | fixed 8% | 30 | +2.3 | +0.3 | 53 | +1.0 | -1.0 | +1.3 | -0.3 | -1.6 | LUCK (edge gone w/o top tickers) |
| Bot stock | trailing 5% | 30 | +1.7 | -0.8 | 47 | +0.7 | -1.9 | +0.6 | -1.0 | -2.0 | LUCK (edge gone w/o top tickers) |
| Bot stock | trailing 8% | 30 | +2.3 | +0.3 | 53 | +1.0 | -1.0 | +1.3 | -0.3 | -1.6 | LUCK (edge gone w/o top tickers) |
| Bot stock | trailing 12% | 30 | +2.3 | +0.3 | 53 | +1.0 | -1.0 | +1.3 | -0.3 | -1.6 | LUCK (edge gone w/o top tickers) |
| Grok stock | hold, no stop | 143 | +1.7 | +0.1 | 52 | -0.1 | -1.2 | +1.0 | +0.2 | -1.6 | no edge vs bench |
| Grok stock | setup's own stop (fixed) | 143 | +1.6 | +0.0 | 51 | +0.3 | -1.4 | +1.0 | +0.3 | -1.0 | LUCK (edge gone w/o top tickers) |
| Grok stock | fixed 8% | 143 | +1.1 | -0.2 | 49 | -0.1 | -2.0 | +0.4 | -0.3 | -1.5 | no edge vs bench |
| Grok stock | trailing 5% | 143 | +0.7 | -0.2 | 48 | -0.2 | -1.6 | +0.4 | -0.2 | -1.1 | no edge vs bench |
| Grok stock | trailing 8% | 143 | +1.2 | +0.3 | 52 | +0.0 | -1.2 | +0.8 | +0.2 | -0.9 | LUCK (edge gone w/o top tickers) |
| Grok stock | trailing 12% | 143 | +1.6 | +0.1 | 52 | +0.3 | -1.4 | +1.0 | +0.3 | -1.1 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | hold, no stop | 11 | +11.3 | +2.7 | 55 | +8.4 | -2.3 | +7.7 | -0.4 | -2.5 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | setup's own stop (fixed) | 11 | +11.3 | +2.7 | 55 | +8.4 | -2.3 | +7.7 | -0.4 | -2.5 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | fixed 8% | 11 | +4.0 | -8.7 | 45 | +2.4 | -7.2 | -0.2 | -7.5 | -8.4 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | trailing 5% | 11 | +3.1 | +1.5 | 73 | +1.7 | +1.9 | +1.4 | -0.9 | -2.2 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | trailing 8% | 11 | +2.3 | +0.8 | 64 | +1.2 | +1.9 | +1.0 | -1.2 | -2.1 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | trailing 12% | 11 | +3.5 | +0.8 | 55 | +2.0 | +1.9 | +0.4 | -3.5 | -4.5 | LUCK (edge gone w/o top tickers) |
| Perplexity stock | hold, no stop | 60 | +5.9 | +1.7 | 60 | +5.0 | +0.7 | +3.2 | +0.7 | -0.3 | LUCK (edge gone w/o top tickers) |
| Perplexity stock | setup's own stop (fixed) | 60 | +5.4 | +0.6 | 53 | +4.9 | -0.5 | +2.6 | +0.1 | -0.4 | LUCK (edge gone w/o top tickers) |
| Perplexity stock | fixed 8% | 60 | +4.4 | -0.2 | 48 | +4.2 | -2.0 | +1.6 | -1.1 | -1.3 | LUCK (edge gone w/o top tickers) |
| Perplexity stock | trailing 5% | 60 | +2.4 | -0.2 | 48 | +2.7 | -1.0 | -0.4 | -1.1 | -0.9 | LUCK (edge gone w/o top tickers) |
| Perplexity stock | trailing 8% | 60 | +2.1 | -1.2 | 43 | +2.2 | -0.6 | -0.8 | -1.9 | -1.8 | LUCK (edge gone w/o top tickers) |
| Perplexity stock | trailing 12% | 60 | +3.2 | -0.2 | 48 | +2.9 | -2.0 | +0.3 | -1.1 | -1.3 | LUCK (edge gone w/o top tickers) |

### B. STOCK LONGS — rule-filtered longs (no Grok prebreakout, sector ETF uptrend) — IAF event engine, net of costs
| group | policy | N | mean | median | hit | x_spy | xmed_spy | mean_wo_top1 | mean_wo_top3 | x_spy_wo_top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Bot stock | hold, no stop | 17 | +1.7 | +0.4 | 59 | +0.4 | -0.8 | +0.7 | -0.4 | -1.8 | LUCK (edge gone w/o top tickers) |
| Bot stock | setup's own stop (fixed) | 17 | +1.7 | +0.4 | 59 | +0.8 | -0.5 | +0.8 | -0.3 | -1.3 | LUCK (edge gone w/o top tickers) |
| Bot stock | fixed 8% | 17 | +1.7 | +0.4 | 59 | +0.4 | -0.8 | +0.7 | -0.4 | -1.8 | LUCK (edge gone w/o top tickers) |
| Bot stock | trailing 5% | 17 | +1.3 | +0.4 | 59 | +0.3 | -0.8 | +0.4 | -0.8 | -1.9 | LUCK (edge gone w/o top tickers) |
| Bot stock | trailing 8% | 17 | +1.7 | +0.4 | 59 | +0.4 | -0.8 | +0.7 | -0.4 | -1.8 | LUCK (edge gone w/o top tickers) |
| Bot stock | trailing 12% | 17 | +1.7 | +0.4 | 59 | +0.4 | -0.8 | +0.7 | -0.4 | -1.8 | LUCK (edge gone w/o top tickers) |
| Grok stock | hold, no stop | 58 | +3.6 | +1.1 | 66 | +1.7 | -0.3 | +2.0 | +0.6 | -1.4 | LUCK (edge gone w/o top tickers) |
| Grok stock | setup's own stop (fixed) | 58 | +3.9 | +1.1 | 66 | +2.4 | -0.3 | +2.3 | +0.9 | -0.6 | LUCK (edge gone w/o top tickers) |
| Grok stock | fixed 8% | 58 | +4.2 | +1.1 | 66 | +2.7 | -0.3 | +2.6 | +1.2 | -0.2 | LUCK (edge gone w/o top tickers) |
| Grok stock | trailing 5% | 58 | +3.0 | +1.0 | 60 | +1.9 | -0.4 | +2.3 | +1.3 | +0.2 | robust to top-3 removal |
| Grok stock | trailing 8% | 58 | +3.7 | +1.1 | 66 | +2.4 | -0.3 | +2.9 | +1.6 | +0.4 | robust to top-3 removal |
| Grok stock | trailing 12% | 58 | +4.6 | +1.1 | 66 | +3.1 | -0.3 | +2.9 | +1.3 | -0.1 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | hold, no stop | 4 | +12.3 | +4.6 | 75 | +7.3 | -0.1 | +1.1 | -5.8 | -11.4 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | setup's own stop (fixed) | 4 | +12.3 | +4.6 | 75 | +7.3 | -0.1 | +1.1 | -5.8 | -11.4 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | fixed 8% | 4 | +11.3 | +4.6 | 75 | +6.9 | -0.1 | -0.2 | -9.8 | -12.7 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | trailing 5% | 4 | +3.6 | +5.5 | 75 | +0.0 | +1.1 | +0.4 | -9.8 | -12.7 | LUCK (edge gone w/o top tickers) |
| Ilan charts stock | trailing 8% | 4 | +2.7 | +4.9 | 75 | -0.6 | +0.8 | +0.0 | -9.8 | -12.7 | no edge vs bench |
| Ilan charts stock | trailing 12% | 4 | +1.7 | +2.3 | 50 | -2.2 | -1.5 | -0.4 | -5.8 | -11.4 | no edge vs bench |
| Perplexity stock | hold, no stop | 36 | +8.1 | +1.8 | 58 | +7.4 | +1.6 | +3.5 | -0.8 | -1.5 | LUCK (edge gone w/o top tickers) |
| Perplexity stock | setup's own stop (fixed) | 36 | +8.9 | +1.8 | 58 | +8.5 | +1.6 | +4.4 | +0.2 | -0.2 | LUCK (edge gone w/o top tickers) |
| Perplexity stock | fixed 8% | 36 | +8.1 | +0.6 | 53 | +8.0 | -0.6 | +3.5 | -0.8 | -0.8 | LUCK (edge gone w/o top tickers) |
| Perplexity stock | trailing 5% | 36 | +5.6 | +0.6 | 56 | +6.0 | +0.6 | +0.9 | -0.1 | +0.2 | robust to top-3 removal |
| Perplexity stock | trailing 8% | 36 | +3.9 | -1.6 | 42 | +4.4 | -0.6 | -0.8 | -2.1 | -1.7 | LUCK (edge gone w/o top tickers) |
| Perplexity stock | trailing 12% | 36 | +4.9 | -3.4 | 42 | +4.8 | -2.7 | +0.2 | -1.5 | -1.5 | LUCK (edge gone w/o top tickers) |

### B. CRYPTO LONGS — ALL longs — IAF event engine, net of costs
| group | policy | N | mean | median | hit | x_btc | xmed_btc | mean_wo_top1 | mean_wo_top3 | x_btc_wo_top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Grok crypto | hold, no stop | 255 | +36.9 | +32.1 | 93 | +14.7 | +4.7 | +36.3 | +30.8 | +8.6 | robust to top-3 removal |
| Grok crypto | setup's own stop (fixed) | 255 | +25.6 | +25.1 | 70 | +9.7 | +0.8 | +23.7 | +19.6 | +5.0 | robust to top-3 removal |
| Grok crypto | fixed 8% | 255 | +28.2 | +28.7 | 78 | +10.1 | +2.8 | +26.1 | +21.9 | +4.9 | robust to top-3 removal |
| Grok crypto | trailing 5% | 255 | +11.0 | +6.1 | 58 | +2.4 | -0.4 | +9.3 | +8.3 | +0.0 | robust to top-3 removal |
| Grok crypto | trailing 8% | 255 | +18.2 | +22.9 | 76 | +3.6 | -0.4 | +17.1 | +15.9 | +0.8 | robust to top-3 removal |
| Grok crypto | trailing 12% | 255 | +25.3 | +26.8 | 82 | +8.3 | +2.4 | +22.2 | +18.8 | +2.7 | robust to top-3 removal |
| Perplexity crypto | hold, no stop | 9 | +46.1 | +49.7 | 100 | +14.4 | +18.1 | +44.1 | +33.7 | +2.0 | robust to top-3 removal |
| Perplexity crypto | setup's own stop (fixed) | 9 | +46.1 | +49.7 | 100 | +14.4 | +18.1 | +44.1 | +33.7 | +2.0 | robust to top-3 removal |
| Perplexity crypto | fixed 8% | 9 | +46.1 | +49.7 | 100 | +14.4 | +18.1 | +44.1 | +33.7 | +2.0 | robust to top-3 removal |
| Perplexity crypto | trailing 5% | 9 | +25.7 | +26.8 | 100 | +3.9 | +5.7 | +23.4 | +17.9 | -3.9 | LUCK (edge gone w/o top tickers) |
| Perplexity crypto | trailing 8% | 9 | +30.6 | +31.9 | 100 | +3.9 | +4.8 | +29.6 | +24.0 | -4.6 | LUCK (edge gone w/o top tickers) |
| Perplexity crypto | trailing 12% | 9 | +41.4 | +36.1 | 100 | +12.1 | +7.9 | +38.0 | +33.7 | +2.0 | robust to top-3 removal |

### B. CRYPTO LONGS — rule-filtered longs (no Grok prebreakout) — IAF event engine, net of costs
| group | policy | N | mean | median | hit | x_btc | xmed_btc | mean_wo_top1 | mean_wo_top3 | x_btc_wo_top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Grok crypto | hold, no stop | 255 | +36.9 | +32.1 | 93 | +14.7 | +4.7 | +36.3 | +30.8 | +8.6 | robust to top-3 removal |
| Grok crypto | setup's own stop (fixed) | 255 | +25.6 | +25.1 | 70 | +9.7 | +0.8 | +23.7 | +19.6 | +5.0 | robust to top-3 removal |
| Grok crypto | fixed 8% | 255 | +28.2 | +28.7 | 78 | +10.1 | +2.8 | +26.1 | +21.9 | +4.9 | robust to top-3 removal |
| Grok crypto | trailing 5% | 255 | +11.0 | +6.1 | 58 | +2.4 | -0.4 | +9.3 | +8.3 | +0.0 | robust to top-3 removal |
| Grok crypto | trailing 8% | 255 | +18.2 | +22.9 | 76 | +3.6 | -0.4 | +17.1 | +15.9 | +0.8 | robust to top-3 removal |
| Grok crypto | trailing 12% | 255 | +25.3 | +26.8 | 82 | +8.3 | +2.4 | +22.2 | +18.8 | +2.7 | robust to top-3 removal |
| Perplexity crypto | hold, no stop | 9 | +46.1 | +49.7 | 100 | +14.4 | +18.1 | +44.1 | +33.7 | +2.0 | robust to top-3 removal |
| Perplexity crypto | setup's own stop (fixed) | 9 | +46.1 | +49.7 | 100 | +14.4 | +18.1 | +44.1 | +33.7 | +2.0 | robust to top-3 removal |
| Perplexity crypto | fixed 8% | 9 | +46.1 | +49.7 | 100 | +14.4 | +18.1 | +44.1 | +33.7 | +2.0 | robust to top-3 removal |
| Perplexity crypto | trailing 5% | 9 | +25.7 | +26.8 | 100 | +3.9 | +5.7 | +23.4 | +17.9 | -3.9 | LUCK (edge gone w/o top tickers) |
| Perplexity crypto | trailing 8% | 9 | +30.6 | +31.9 | 100 | +3.9 | +4.8 | +29.6 | +24.0 | -4.6 | LUCK (edge gone w/o top tickers) |
| Perplexity crypto | trailing 12% | 9 | +41.4 | +36.1 | 100 | +12.1 | +7.9 | +38.0 | +33.7 | +2.0 | robust to top-3 removal |

### C1. STOCKS vs SPY / sector ETF — policy: hold, no stop (same entry->exit window; shorts: excess = ret + bench ret)
| group | dir | N | tickers | mean | median | hit | x_spy | xmed_spy | x_sector | mean_wo_top1 | mean_wo_top3 | x_spy_wo_top1 | x_spy_wo_top3 | top1 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Bot | LONG | 30 | 24 | +2.3 | +0.3 | 53 | +1.0 | -1.0 | +1.4 | +1.3 | -0.3 | -0.0 | -1.6 | AMD(1) | LUCK (edge gone w/o top tickers) |
| Bot | SHORT | 19 | 15 | +0.0 | +0.8 | 58 | +1.3 | +1.9 | +1.7 | -0.6 | -1.4 | +0.6 | -0.1 | CRM(1) | LUCK (edge gone w/o top tickers) |
| Grok momentum | LONG | 40 | 30 | +4.6 | +4.5 | 70 | +3.1 | +2.9 | +0.3 | +3.4 | +1.5 | +1.9 | +0.0 | ALAB(4) | robust to top-3 removal |
| Grok momentum | SHORT | 25 | 18 | -4.4 | -3.3 | 40 | -2.8 | -2.1 | -1.1 | -5.2 | -6.8 | -3.6 | -5.2 | IREN(1) | no edge vs bench |
| Grok near-low | LONG | 14 | 12 | +0.4 | -1.8 | 43 | -1.2 | -3.8 | +0.8 | -4.2 | -8.9 | -5.8 | -10.5 | RXRX(3) | no edge vs bench |
| Grok near-low | SHORT | 12 | 12 | +5.0 | +6.7 | 75 | +6.4 | +8.5 | +5.7 | +4.1 | +2.1 | +5.5 | +3.4 | RH(1) | robust to top-3 removal |
| Grok portfolio-news | LONG | 12 | 9 | +0.3 | +0.3 | 50 | -0.9 | -1.0 | -0.2 | -0.2 | -1.1 | -1.4 | -2.3 | TSLA(1) | no edge vs bench |
| Grok portfolio-news | SHORT | 21 | 11 | -2.5 | -2.8 | 29 | -1.3 | -1.6 | -0.4 | -3.1 | -4.5 | -1.9 | -3.4 | COIN(1) | no edge vs bench |
| Grok prebreakout | LONG | 42 | 31 | -3.3 | -3.2 | 33 | -4.9 | -4.6 | -1.9 | -3.8 | -4.7 | -5.4 | -6.3 | PBR(1) | no edge vs bench |
| Grok prebreakout | SHORT | 27 | 23 | +5.7 | +6.5 | 70 | +7.1 | +8.5 | +5.1 | +4.9 | +4.0 | +6.4 | +5.5 | WHR(1) | robust to top-3 removal |
| Grok x-trends | LONG | 19 | 8 | +3.1 | +0.4 | 74 | +1.4 | -1.2 | -0.7 | +0.7 | -0.4 | -1.1 | -2.2 | AMD(4) | LUCK (edge gone w/o top tickers) |
| Grok x-trends | SHORT | 34 | 6 | -5.2 | -5.2 | 12 | -3.3 | -2.8 | -3.6 | -5.8 | -6.9 | -4.0 | -5.1 | SPY(6) | no edge vs bench |
| Ilan charts | LONG | 11 | 11 | +11.3 | +2.7 | 55 | +8.4 | -2.3 | +5.6 | +7.7 | -0.4 | +5.0 | -2.5 | SMCI(1) | LUCK (edge gone w/o top tickers) |
| Original sheet (Grok/Pplx) | LONG | 17 | 17 | +8.0 | -4.1 | 47 | +4.3 | -4.5 | +4.4 | +2.5 | -3.1 | -1.4 | -7.0 | IOVA(1) | LUCK (edge gone w/o top tickers) |
| Original sheet (Grok/Pplx) | SHORT | 10 | 10 | -4.0 | +0.7 | 50 | -1.0 | +3.4 | -3.8 | -10.1 | -17.7 | -7.3 | -14.9 | LCID(1) | no edge vs bench |
| Perplexity | LONG | 59 | 42 | +5.8 | +1.7 | 59 | +5.0 | +0.6 | +6.2 | +3.1 | +0.5 | +2.2 | -0.4 | XP(2) | LUCK (edge gone w/o top tickers) |
| Perplexity | SHORT | 41 | 31 | -0.7 | -0.7 | 49 | +0.3 | +1.6 | +0.3 | -1.3 | -2.3 | -0.3 | -1.3 | HE(1) | LUCK (edge gone w/o top tickers) |

### C2. CRYPTO vs BTC / ETH / 50-50 basket — policy: hold, no stop
| group | dir | N | tickers | mean | median | hit | x_btc | xmed_btc | x_eth | x_basket | xmed_basket | mean_wo_top1 | mean_wo_top3 | x_btc_wo_top1 | x_btc_wo_top3 | top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Grok crypto | LONG | 255 | 19 | +36.9 | +32.1 | 93 | +14.7 | +4.7 | +11.8 | +13.3 | +2.7 | +36.3 | +30.8 | +14.0 | +8.6 | SOL-USD(46),ZEC-USD(5),NEAR-USD(5) | robust to top-3 removal |
| Grok crypto | SHORT | 120 | 30 | -22.6 | -10.9 | 28 | -9.1 | -0.4 | -9.0 | -9.1 | -2.3 | -24.6 | -27.8 | -11.3 | -14.6 | DEXE-USD(2),BEAT38837-USD(1),DOGE-USD(13) | no edge vs bench |
| Perplexity | LONG | 9 | 5 | +46.1 | +49.7 | 100 | +14.4 | +18.1 | +9.3 | +11.9 | +15.6 | +44.1 | +33.7 | +12.4 | +2.0 | SOL-USD(2),LINK-USD(2),AVAX-USD(1) | robust to top-3 removal |
| Perplexity | SHORT | 2 | 2 | -111.0 | -111.0 | 0 | -79.3 | -79.3 | -74.4 | -76.9 | -76.9 | -166.6 | +nan | -135.0 | +nan | HYPE32196-USD(1),ZEC-USD(1) | no edge vs bench |

### C1. STOCKS vs SPY / sector ETF — policy: trailing 8% (same entry->exit window; shorts: excess = ret + bench ret)
| group | dir | N | tickers | mean | median | hit | x_spy | xmed_spy | x_sector | mean_wo_top1 | mean_wo_top3 | x_spy_wo_top1 | x_spy_wo_top3 | top1 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Bot | LONG | 30 | 24 | +2.3 | +0.3 | 53 | +1.0 | -1.0 | +1.4 | +1.3 | -0.3 | -0.0 | -1.6 | AMD(1) | LUCK (edge gone w/o top tickers) |
| Bot | SHORT | 19 | 15 | -0.2 | +0.2 | 53 | +0.9 | +1.8 | +1.2 | -0.9 | -1.7 | +0.3 | -0.6 | CRM(1) | LUCK (edge gone w/o top tickers) |
| Grok momentum | LONG | 40 | 30 | +3.3 | +4.1 | 68 | +2.3 | +2.6 | +0.3 | +2.3 | +1.1 | +1.4 | +0.2 | HPE(2) | robust to top-3 removal |
| Grok momentum | SHORT | 25 | 18 | -3.6 | -4.6 | 28 | -3.2 | -3.3 | -2.2 | -4.2 | -4.7 | -3.8 | -4.3 | MGM(1) | no edge vs bench |
| Grok near-low | LONG | 14 | 12 | +1.6 | -1.0 | 43 | +0.5 | -3.4 | +1.4 | -1.1 | -5.1 | -2.1 | -5.9 | RXRX(3) | LUCK (edge gone w/o top tickers) |
| Grok near-low | SHORT | 12 | 12 | +0.2 | +0.3 | 50 | +0.9 | +1.4 | +0.1 | -1.2 | -4.2 | -0.6 | -3.5 | RH(1) | LUCK (edge gone w/o top tickers) |
| Grok portfolio-news | LONG | 12 | 9 | +0.3 | +0.3 | 50 | -0.9 | -1.0 | -0.2 | -0.2 | -1.1 | -1.4 | -2.3 | TSLA(1) | no edge vs bench |
| Grok portfolio-news | SHORT | 21 | 11 | -1.3 | -2.8 | 33 | -0.3 | -1.6 | +0.5 | -1.9 | -3.1 | -0.8 | -2.1 | COIN(1) | no edge vs bench |
| Grok prebreakout | LONG | 42 | 31 | -2.7 | -3.2 | 31 | -3.9 | -4.5 | -1.2 | -3.2 | -4.0 | -4.4 | -5.2 | PBR(1) | no edge vs bench |
| Grok prebreakout | SHORT | 27 | 23 | +4.6 | +6.4 | 67 | +5.9 | +8.4 | +4.0 | +3.8 | +2.7 | +5.1 | +4.0 | WHR(1) | robust to top-3 removal |
| Grok x-trends | LONG | 19 | 8 | +3.1 | +0.4 | 74 | +1.4 | -1.2 | -0.7 | +0.7 | -0.4 | -1.1 | -2.2 | AMD(4) | LUCK (edge gone w/o top tickers) |
| Grok x-trends | SHORT | 34 | 6 | -4.5 | -5.2 | 12 | -2.9 | -2.8 | -3.0 | -5.1 | -5.9 | -3.5 | -4.6 | SPY(6) | no edge vs bench |
| Ilan charts | LONG | 11 | 11 | +2.3 | +0.8 | 64 | +1.2 | +1.9 | +1.5 | +1.0 | -1.2 | +0.1 | -2.1 | AI(1) | LUCK (edge gone w/o top tickers) |
| Original sheet (Grok/Pplx) | LONG | 17 | 17 | +3.4 | +0.8 | 53 | +2.8 | +1.2 | +2.3 | +0.5 | -2.2 | +0.1 | -2.5 | WGS(1) | LUCK (edge gone w/o top tickers) |
| Original sheet (Grok/Pplx) | SHORT | 10 | 10 | +2.9 | +1.5 | 50 | +4.2 | +3.1 | +3.3 | -2.4 | -4.3 | -1.5 | -3.6 | LCID(1) | LUCK (edge gone w/o top tickers) |
| Perplexity | LONG | 59 | 42 | +2.2 | -1.2 | 44 | +2.3 | -0.5 | +3.7 | -0.7 | -1.8 | -0.6 | -1.7 | XP(2) | LUCK (edge gone w/o top tickers) |
| Perplexity | SHORT | 41 | 31 | -0.2 | -2.5 | 41 | +0.4 | -1.0 | -0.7 | -0.8 | -1.7 | -0.2 | -1.1 | HE(1) | LUCK (edge gone w/o top tickers) |

### C2. CRYPTO vs BTC / ETH / 50-50 basket — policy: trailing 8%
| group | dir | N | tickers | mean | median | hit | x_btc | xmed_btc | x_eth | x_basket | xmed_basket | mean_wo_top1 | mean_wo_top3 | x_btc_wo_top1 | x_btc_wo_top3 | top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Grok crypto | LONG | 255 | 19 | +18.2 | +22.9 | 76 | +3.6 | -0.4 | +0.7 | +2.2 | +1.1 | +17.1 | +15.9 | +2.5 | +0.8 | SOL-USD(46),HYPE32196-USD(15),LINK-USD(23) | robust to top-3 removal |
| Grok crypto | SHORT | 120 | 30 | -2.1 | -3.9 | 35 | +1.3 | -0.4 | +2.2 | +1.7 | -0.2 | -3.6 | -4.4 | -0.2 | -1.0 | DEXE-USD(2),BEAT38837-USD(1),XRP-USD(5) | LUCK (edge gone w/o top tickers) |
| Perplexity | LONG | 9 | 5 | +30.6 | +31.9 | 100 | +3.9 | +4.8 | -2.2 | +0.9 | +2.1 | +29.6 | +24.0 | +2.0 | -4.6 | LINK-USD(2),SOL-USD(2),ETH-USD(2) | LUCK (edge gone w/o top tickers) |
| Perplexity | SHORT | 2 | 2 | -18.7 | -18.7 | 0 | -9.4 | -9.4 | +0.8 | -4.3 | -4.3 | -21.8 | +nan | -12.6 | +nan | ZEC-USD(1),HYPE32196-USD(1) | no edge vs bench |

### D. Named leave-one-ticker-out checks (excess = vs SPY for stocks, vs BTC for crypto)
| check | policy | sample | N | mean | median | hit | excess_vs_mkt | excess_median |
|---|---|---|---|---|---|---|---|---|
| Grok crypto longs w/o NEAR | hold, no stop | with NEAR-USD | 255 | +36.9 | +32.1 | 93 | +14.7 | +4.7 |
| Grok crypto longs w/o NEAR | hold, no stop | without NEAR-USD | 250 | +34.9 | +32.0 | 92 | +12.7 | +4.6 |
| Grok crypto longs w/o NEAR | trailing 8% | with NEAR-USD | 255 | +18.2 | +22.9 | 76 | +3.6 | -0.4 |
| Grok crypto longs w/o NEAR | trailing 8% | without NEAR-USD | 250 | +18.1 | +24.6 | 77 | +3.4 | -0.4 |
| Perplexity (all, longs) w/o XP | hold, no stop | with XP | 68 | +11.2 | +1.8 | 65 | +6.3 | +0.9 |
| Perplexity (all, longs) w/o XP | hold, no stop | without XP | 66 | +8.9 | +1.8 | 64 | +3.9 | +0.7 |
| Perplexity (all, longs) w/o XP | trailing 8% | with XP | 68 | +6.0 | +0.3 | 51 | +2.5 | -0.5 |
| Perplexity (all, longs) w/o XP | trailing 8% | without XP | 66 | +3.6 | -0.1 | 50 | +0.0 | -0.5 |
| Original sheet longs w/o IOVA | hold, no stop | with IOVA | 17 | +8.0 | -4.1 | 47 | +4.3 | -4.5 |
| Original sheet longs w/o IOVA | hold, no stop | without IOVA | 16 | +2.5 | -4.2 | 44 | -1.4 | -4.7 |
| Original sheet longs w/o IOVA | trailing 8% | with IOVA | 17 | +3.4 | +0.8 | 53 | +2.8 | +1.2 |
| Original sheet longs w/o IOVA | trailing 8% | without IOVA | 16 | +2.2 | -1.6 | 50 | +1.5 | -1.0 |

### E. SHORTS (independent replay; IAF v8 cannot short) — excess vs SPY/BTC means short beat shorting the market
| src | asset | subset | policy | N | mean | median | hit | x_spy | x_btc | mean_wo_top1 | x_spy_wo_top1 | x_spy_wo_top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Bot | stock | all shorts | hold, no stop | 19 | +0.0 | +0.8 | 58 | +1.3 | +nan | -0.6 | +0.6 | -0.1 | LUCK (edge gone w/o top tickers) |
| Bot | stock | score>=3 & <SMA200 | hold, no stop | 7 | +0.5 | +0.8 | 71 | +1.7 | +nan | +0.2 | +1.4 | +0.2 | robust to top-3 removal |
| Grok | crypto | all shorts | hold, no stop | 120 | -22.6 | -10.9 | 28 | +nan | -9.1 | -24.6 | +nan | +nan | no edge vs bench |
| Grok | stock | all shorts | hold, no stop | 129 | -1.3 | -1.8 | 41 | +0.4 | +nan | -1.7 | -0.0 | -0.5 | LUCK (edge gone w/o top tickers) |
| Grok | stock | score>=3 & <SMA200 | hold, no stop | 33 | +5.3 | +7.3 | 76 | +6.9 | +nan | +4.7 | +6.3 | +5.6 | robust to top-3 removal |
| Perplexity | crypto | all shorts | hold, no stop | 2 | -111.0 | -111.0 | 0 | +nan | -79.3 | -166.6 | +nan | +nan | no edge vs bench |
| Perplexity | stock | all shorts | hold, no stop | 41 | -0.7 | -0.7 | 49 | +0.3 | +nan | -1.3 | -0.3 | -1.3 | LUCK (edge gone w/o top tickers) |
| Perplexity | stock | score>=3 & <SMA200 | hold, no stop | 20 | +1.8 | +6.6 | 70 | +2.4 | +nan | +0.6 | +1.2 | -0.7 | LUCK (edge gone w/o top tickers) |
| Bot | stock | all shorts | setup's own stop (fixed) | 19 | -0.9 | -0.9 | 47 | +0.2 | +nan | -1.6 | -0.5 | -1.6 | LUCK (edge gone w/o top tickers) |
| Bot | stock | score>=3 & <SMA200 | setup's own stop (fixed) | 7 | +0.5 | +0.8 | 71 | +1.7 | +nan | +0.2 | +1.4 | +0.2 | robust to top-3 removal |
| Grok | crypto | all shorts | setup's own stop (fixed) | 120 | -10.7 | -10.0 | 20 | +nan | -2.8 | -12.5 | +nan | +nan | no edge vs bench |
| Grok | stock | all shorts | setup's own stop (fixed) | 129 | -0.9 | -2.5 | 36 | +0.3 | +nan | -1.4 | -0.1 | -0.6 | LUCK (edge gone w/o top tickers) |
| Grok | stock | score>=3 & <SMA200 | setup's own stop (fixed) | 33 | +5.1 | +7.3 | 73 | +6.5 | +nan | +4.5 | +5.9 | +5.1 | robust to top-3 removal |
| Perplexity | crypto | all shorts | setup's own stop (fixed) | 2 | -85.2 | -85.2 | 0 | +nan | -68.5 | -166.6 | +nan | +nan | no edge vs bench |
| Perplexity | stock | all shorts | setup's own stop (fixed) | 41 | -0.5 | -0.7 | 49 | +0.3 | +nan | -1.1 | -0.3 | -1.3 | LUCK (edge gone w/o top tickers) |
| Perplexity | stock | score>=3 & <SMA200 | setup's own stop (fixed) | 20 | +2.0 | +6.6 | 70 | +2.6 | +nan | +0.8 | +1.4 | -0.5 | LUCK (edge gone w/o top tickers) |
| Bot | stock | all shorts | trailing 8% | 19 | -0.2 | +0.2 | 53 | +0.9 | +nan | -0.9 | +0.3 | -0.6 | LUCK (edge gone w/o top tickers) |
| Bot | stock | score>=3 & <SMA200 | trailing 8% | 7 | +0.5 | +0.8 | 71 | +1.7 | +nan | +0.2 | +1.4 | +0.2 | robust to top-3 removal |
| Grok | crypto | all shorts | trailing 8% | 120 | -2.1 | -3.9 | 35 | +nan | +1.3 | -3.6 | +nan | +nan | LUCK (edge gone w/o top tickers) |
| Grok | stock | all shorts | trailing 8% | 129 | -0.9 | -2.5 | 36 | +0.2 | +nan | -1.3 | -0.2 | -0.6 | LUCK (edge gone w/o top tickers) |
| Grok | stock | score>=3 & <SMA200 | trailing 8% | 33 | +4.1 | +6.3 | 64 | +5.3 | +nan | +3.5 | +4.6 | +3.7 | robust to top-3 removal |
| Perplexity | crypto | all shorts | trailing 8% | 2 | -18.7 | -18.7 | 0 | +nan | -9.4 | -21.8 | +nan | +nan | no edge vs bench |
| Perplexity | stock | all shorts | trailing 8% | 41 | -0.2 | -2.5 | 41 | +0.4 | +nan | -0.8 | -0.2 | -1.1 | LUCK (edge gone w/o top tickers) |
| Perplexity | stock | score>=3 & <SMA200 | trailing 8% | 20 | +3.2 | +4.5 | 55 | +3.3 | +nan | +2.1 | +2.2 | +0.5 | robust to top-3 removal |

### F. Same setups as the team's hold-no-stop CSV (longs flagged in_hold_no_stop_csv), our PIT entry
| src | asset | N | mean | median | hit | x_spy | x_btc | mean_wo_top1 | mean_wo_top3 | x_spy_wo_top3 | x_btc_wo_top3 | top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Bot | stock | 25 | +1.6 | +0.1 | 52 | +0.4 | +nan | +0.6 | -0.6 | -1.9 | +nan | PANW(3),META(2),VLO(1) | LUCK (edge gone w/o top tickers) |
| Grok | crypto | 240 | +38.0 | +32.6 | 93 | +nan | +15.4 | +37.6 | +31.6 | +nan | +9.1 | SOL-USD(46),ZEC-USD(5),NEAR-USD(4) | robust to top-3 removal |
| Grok | stock | 139 | +1.2 | +0.1 | 52 | -0.6 | +nan | +0.5 | -0.3 | -2.1 | +nan | IOVA(1),RXRX(3),AMD(4) | no edge vs bench |
| Perplexity | crypto | 8 | +47.4 | +51.2 | 100 | +nan | +15.7 | +45.4 | +32.9 | +nan | +1.3 | SOL-USD(2),LINK-USD(2),AVAX-USD(1) | robust to top-3 removal |
| Perplexity | stock | 53 | +6.7 | +1.7 | 58 | +5.9 | +nan | +3.6 | +0.8 | -0.1 | +nan | XP(2),INTR(3),STNE(2) | LUCK (edge gone w/o top tickers) |

### G. Grok crypto LONGS vs BTC / ETH / basket — full period vs team fair window, all exit policies
| window | policy | sample | N | tickers | mean | median | hit | x_btc | xmed_btc | x_eth | xmed_eth | x_basket | xmed_basket | x_btc_wo_top1 | x_btc_wo_top3 | top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full period | hold, no stop | all | 255 | 19 | +36.9 | +32.1 | 93 | +14.7 | +4.7 | +11.8 | +3.3 | +13.3 | +2.7 | +14.0 | +8.6 | SOL-USD(46),ZEC-USD(5),NEAR-USD(5) | robust to top-3 removal |
| full period | hold, no stop | w/o NEAR | 250 | 18 | +34.9 | +32.0 | 92 | +12.7 | +4.6 | +9.7 | +2.7 | +11.2 | +2.4 | +11.5 | +6.4 | SOL-USD(46),ZEC-USD(5),UNI7083-USD(8) | robust to top-3 removal |
| full period | setup's own stop (fixed) | all | 255 | 19 | +25.6 | +25.1 | 70 | +9.6 | +0.8 | +7.7 | -0.4 | +8.7 | +1.6 | +8.3 | +5.0 | SOL-USD(46),NEAR-USD(5),LINK-USD(23) | robust to top-3 removal |
| full period | setup's own stop (fixed) | w/o NEAR | 250 | 18 | +24.0 | +24.7 | 70 | +8.0 | +0.4 | +6.1 | -0.4 | +7.1 | +1.5 | +6.3 | +3.7 | SOL-USD(46),LINK-USD(23),ZEC-USD(5) | robust to top-3 removal |
| full period | fixed 8% | all | 255 | 19 | +28.2 | +28.7 | 78 | +10.1 | +2.8 | +7.8 | -0.4 | +8.9 | +1.9 | +8.4 | +4.9 | SOL-USD(46),ZEC-USD(5),LINK-USD(23) | robust to top-3 removal |
| full period | fixed 8% | w/o NEAR | 250 | 18 | +27.5 | +28.8 | 78 | +9.1 | +2.8 | +6.8 | -0.4 | +8.0 | +1.9 | +7.3 | +3.4 | SOL-USD(46),ZEC-USD(5),LINK-USD(23) | robust to top-3 removal |
| full period | trailing 5% | all | 255 | 19 | +11.0 | +6.1 | 58 | +2.4 | -0.4 | -0.3 | -0.5 | +1.1 | -1.0 | +1.3 | +0.0 | SOL-USD(46),ETH-USD(44),UNI7083-USD(8) | robust to top-3 removal |
| full period | trailing 5% | w/o NEAR | 250 | 18 | +11.1 | +6.1 | 59 | +2.5 | -0.4 | -0.2 | -0.5 | +1.2 | -1.0 | +1.4 | +0.1 | SOL-USD(46),ETH-USD(44),UNI7083-USD(8) | robust to top-3 removal |
| full period | trailing 8% | all | 255 | 19 | +18.2 | +22.9 | 76 | +3.6 | -0.4 | +0.7 | -0.5 | +2.2 | +1.1 | +2.5 | +0.8 | SOL-USD(46),HYPE32196-USD(15),LINK-USD(23) | robust to top-3 removal |
| full period | trailing 8% | w/o NEAR | 250 | 18 | +18.1 | +24.6 | 77 | +3.4 | -0.4 | +0.5 | -0.5 | +1.9 | +1.1 | +2.2 | +0.4 | SOL-USD(46),HYPE32196-USD(15),LINK-USD(23) | robust to top-3 removal |
| full period | trailing 12% | all | 255 | 19 | +25.3 | +26.8 | 82 | +8.3 | +2.4 | +4.9 | -0.4 | +6.6 | +1.6 | +6.1 | +2.7 | SOL-USD(46),NEAR-USD(5),ZEC-USD(5) | robust to top-3 removal |
| full period | trailing 12% | w/o NEAR | 250 | 18 | +24.1 | +26.7 | 82 | +7.0 | +2.2 | +3.6 | -0.4 | +5.3 | +1.6 | +4.4 | +1.8 | SOL-USD(46),ZEC-USD(5),AVAX-USD(6) | robust to top-3 removal |
| fair window 08-12..10-04 | hold, no stop | all | 117 | 15 | +21.9 | +14.2 | 84 | +8.8 | +1.1 | +9.9 | +3.8 | +9.3 | +2.1 | +6.4 | +4.1 | NEAR-USD(3),SOL-USD(22),UNI7083-USD(3) | robust to top-3 removal |
| fair window 08-12..10-04 | hold, no stop | w/o NEAR | 114 | 14 | +19.4 | +14.1 | 83 | +6.4 | +0.4 | +7.5 | +3.5 | +6.9 | +2.0 | +5.5 | +3.0 | SOL-USD(22),UNI7083-USD(3),AAVE-USD(4) | robust to top-3 removal |
| fair window 08-12..10-04 | setup's own stop (fixed) | all | 117 | 15 | +20.2 | +13.9 | 77 | +7.8 | -0.4 | +8.7 | +2.8 | +8.3 | +1.9 | +5.4 | +3.0 | NEAR-USD(3),SOL-USD(22),UNI7083-USD(3) | robust to top-3 removal |
| fair window 08-12..10-04 | setup's own stop (fixed) | w/o NEAR | 114 | 14 | +17.8 | +10.9 | 76 | +5.4 | -0.4 | +6.3 | +2.7 | +5.8 | +1.7 | +4.5 | +2.3 | SOL-USD(22),UNI7083-USD(3),LINK-USD(13) | robust to top-3 removal |
| fair window 08-12..10-04 | fixed 8% | all | 117 | 15 | +20.2 | +13.9 | 78 | +7.7 | -0.4 | +8.6 | +3.3 | +8.1 | +1.9 | +5.2 | +2.7 | NEAR-USD(3),SOL-USD(22),UNI7083-USD(3) | robust to top-3 removal |
| fair window 08-12..10-04 | fixed 8% | w/o NEAR | 114 | 14 | +17.8 | +11.3 | 77 | +5.2 | -0.4 | +6.2 | +2.7 | +5.7 | +1.7 | +4.2 | +2.0 | SOL-USD(22),UNI7083-USD(3),LINK-USD(13) | robust to top-3 removal |
| fair window 08-12..10-04 | trailing 5% | all | 117 | 15 | +9.3 | +5.4 | 63 | +1.9 | -0.4 | +1.2 | -0.4 | +1.5 | +0.0 | +0.8 | -0.4 | UNI7083-USD(3),SOL-USD(22),HYPE32196-USD(5) | LUCK (edge gone w/o top tickers) |
| fair window 08-12..10-04 | trailing 5% | w/o NEAR | 114 | 14 | +9.3 | +5.3 | 63 | +1.9 | -0.4 | +1.2 | -0.4 | +1.6 | +0.0 | +0.8 | -0.4 | UNI7083-USD(3),SOL-USD(22),HYPE32196-USD(5) | LUCK (edge gone w/o top tickers) |
| fair window 08-12..10-04 | trailing 8% | all | 117 | 15 | +12.3 | +7.7 | 74 | +2.2 | -0.4 | +2.3 | -0.4 | +2.3 | +0.5 | +1.4 | -0.3 | UNI7083-USD(3),SOL-USD(22),NEAR-USD(3) | LUCK (edge gone w/o top tickers) |
| fair window 08-12..10-04 | trailing 8% | w/o NEAR | 114 | 14 | +11.5 | +6.9 | 74 | +1.5 | -0.4 | +1.6 | -0.4 | +1.5 | +0.4 | +0.6 | -0.9 | UNI7083-USD(3),SOL-USD(22),LINK-USD(13) | LUCK (edge gone w/o top tickers) |
| fair window 08-12..10-04 | trailing 12% | all | 117 | 15 | +16.5 | +8.7 | 77 | +5.3 | -0.4 | +5.6 | +0.6 | +5.5 | +1.1 | +3.2 | +0.6 | NEAR-USD(3),SOL-USD(22),UNI7083-USD(3) | robust to top-3 removal |
| fair window 08-12..10-04 | trailing 12% | w/o NEAR | 114 | 14 | +14.3 | +8.4 | 76 | +3.2 | -0.4 | +3.6 | +0.1 | +3.4 | +1.1 | +1.6 | -0.3 | SOL-USD(22),UNI7083-USD(3),AVAX-USD(3) | LUCK (edge gone w/o top tickers) |

### H. Whole scanner: unfiltered vs rule-filtered (rules: longs no Grok prebreakout + stock sector uptrend; shorts only stocks with score>=3 & <SMA200; no crypto shorts)
| asset | policy | subset | N | tickers | mean | median | hit | x_spy | x_btc | mean_wo_top1 | mean_wo_top3 | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| stock | hold, no stop | unfiltered L+S | 433 | 210 | +1.4 | +0.0 | 50 | +1.1 | +nan | +1.0 | +0.5 | robust to top-3 removal |
| stock | hold, no stop | rule-filtered L+S | 175 | 117 | +4.5 | +2.2 | 66 | +3.9 | +nan | +3.6 | +2.5 | robust to top-3 removal |
| stock | hold, no stop | unfiltered longs | 244 | 153 | +3.2 | +0.4 | 55 | +1.7 | +nan | +2.5 | +1.6 | robust to top-3 removal |
| stock | hold, no stop | rule-filtered longs | 115 | 70 | +5.0 | +1.1 | 63 | +3.5 | +nan | +3.6 | +1.9 | robust to top-3 removal |
| stock | setup's own stop (fixed) | unfiltered L+S | 433 | 210 | +1.3 | -1.0 | 46 | +1.2 | +nan | +0.9 | +0.4 | robust to top-3 removal |
| stock | setup's own stop (fixed) | rule-filtered L+S | 175 | 117 | +4.8 | +2.1 | 66 | +4.4 | +nan | +3.9 | +2.7 | robust to top-3 removal |
| stock | setup's own stop (fixed) | unfiltered longs | 244 | 153 | +2.9 | +0.1 | 51 | +1.8 | +nan | +2.3 | +1.3 | robust to top-3 removal |
| stock | setup's own stop (fixed) | rule-filtered longs | 115 | 70 | +5.4 | +1.1 | 63 | +4.2 | +nan | +4.0 | +2.3 | robust to top-3 removal |
| stock | fixed 8% | unfiltered L+S | 433 | 210 | +0.9 | -1.1 | 46 | +0.9 | +nan | +0.5 | +0.1 | robust to top-3 removal |
| stock | fixed 8% | rule-filtered L+S | 175 | 117 | +4.7 | +1.8 | 64 | +4.3 | +nan | +3.8 | +2.6 | robust to top-3 removal |
| stock | fixed 8% | unfiltered longs | 244 | 153 | +2.2 | -0.2 | 49 | +1.2 | +nan | +1.5 | +0.6 | LUCK (edge gone w/o top tickers) |
| stock | fixed 8% | rule-filtered longs | 115 | 70 | +5.3 | +1.0 | 61 | +4.2 | +nan | +3.9 | +2.1 | robust to top-3 removal |
| stock | trailing 5% | unfiltered L+S | 433 | 210 | +0.4 | -0.9 | 45 | +0.4 | +nan | +0.0 | -0.2 | LUCK (edge gone w/o top tickers) |
| stock | trailing 5% | rule-filtered L+S | 175 | 117 | +3.5 | +1.1 | 60 | +3.2 | +nan | +2.5 | +2.2 | robust to top-3 removal |
| stock | trailing 5% | unfiltered longs | 244 | 153 | +1.3 | -0.2 | 49 | +0.7 | +nan | +0.7 | +0.1 | LUCK (edge gone w/o top tickers) |
| stock | trailing 5% | rule-filtered longs | 115 | 70 | +3.6 | +0.6 | 59 | +2.9 | +nan | +2.1 | +1.5 | robust to top-3 removal |
| stock | trailing 8% | unfiltered L+S | 433 | 210 | +0.6 | -0.7 | 46 | +0.6 | +nan | +0.2 | -0.1 | LUCK (edge gone w/o top tickers) |
| stock | trailing 8% | rule-filtered L+S | 175 | 117 | +3.4 | +0.8 | 59 | +3.2 | +nan | +2.5 | +2.0 | robust to top-3 removal |
| stock | trailing 8% | unfiltered longs | 244 | 153 | +1.6 | +0.0 | 51 | +0.7 | +nan | +0.9 | +0.3 | LUCK (edge gone w/o top tickers) |
| stock | trailing 8% | rule-filtered longs | 115 | 70 | +3.4 | +0.4 | 57 | +2.6 | +nan | +2.0 | +1.2 | robust to top-3 removal |
| stock | trailing 12% | unfiltered L+S | 433 | 210 | +0.9 | -0.8 | 47 | +0.8 | +nan | +0.5 | +0.2 | robust to top-3 removal |
| stock | trailing 12% | rule-filtered L+S | 175 | 117 | +4.1 | +1.4 | 61 | +3.7 | +nan | +3.1 | +2.2 | robust to top-3 removal |
| stock | trailing 12% | unfiltered longs | 244 | 153 | +2.2 | +0.1 | 51 | +1.1 | +nan | +1.5 | +0.6 | LUCK (edge gone w/o top tickers) |
| stock | trailing 12% | rule-filtered longs | 115 | 70 | +4.1 | +0.4 | 57 | +3.0 | +nan | +2.7 | +1.2 | robust to top-3 removal |
| crypto | hold, no stop | unfiltered L+S | 386 | 32 | +17.8 | +20.5 | 72 | +nan | +6.8 | +15.3 | +12.5 | robust to top-3 removal |
| crypto | hold, no stop | rule-filtered L+S | 264 | 19 | +37.2 | +32.4 | 93 | +nan | +14.7 | +36.5 | +31.2 | robust to top-3 removal |
| crypto | hold, no stop | unfiltered longs | 264 | 19 | +37.2 | +32.4 | 93 | +nan | +14.7 | +36.5 | +31.2 | robust to top-3 removal |
| crypto | hold, no stop | rule-filtered longs | 264 | 19 | +37.2 | +32.4 | 93 | +nan | +14.7 | +36.5 | +31.2 | robust to top-3 removal |
| crypto | setup's own stop (fixed) | unfiltered L+S | 386 | 32 | +14.2 | +3.5 | 55 | +nan | +5.5 | +11.7 | +8.9 | robust to top-3 removal |
| crypto | setup's own stop (fixed) | rule-filtered L+S | 264 | 19 | +26.3 | +27.4 | 71 | +nan | +9.8 | +24.4 | +20.2 | robust to top-3 removal |
| crypto | setup's own stop (fixed) | unfiltered longs | 264 | 19 | +26.3 | +27.4 | 71 | +nan | +9.8 | +24.4 | +20.2 | robust to top-3 removal |
| crypto | setup's own stop (fixed) | rule-filtered longs | 264 | 19 | +26.3 | +27.4 | 71 | +nan | +9.8 | +24.4 | +20.2 | robust to top-3 removal |
| crypto | fixed 8% | unfiltered L+S | 386 | 32 | +17.4 | +7.8 | 60 | +nan | +6.9 | +14.9 | +12.6 | robust to top-3 removal |
| crypto | fixed 8% | rule-filtered L+S | 264 | 19 | +28.9 | +29.5 | 78 | +nan | +10.2 | +26.7 | +22.4 | robust to top-3 removal |
| crypto | fixed 8% | unfiltered longs | 264 | 19 | +28.9 | +29.5 | 78 | +nan | +10.2 | +26.7 | +22.4 | robust to top-3 removal |
| crypto | fixed 8% | rule-filtered longs | 264 | 19 | +28.9 | +29.5 | 78 | +nan | +10.2 | +26.7 | +22.4 | robust to top-3 removal |
| crypto | trailing 5% | unfiltered L+S | 386 | 32 | +7.5 | +1.3 | 52 | +nan | +2.1 | +6.2 | +4.9 | robust to top-3 removal |
| crypto | trailing 5% | rule-filtered L+S | 264 | 19 | +11.5 | +8.0 | 60 | +nan | +2.4 | +9.8 | +8.8 | robust to top-3 removal |
| crypto | trailing 5% | unfiltered longs | 264 | 19 | +11.5 | +8.0 | 60 | +nan | +2.4 | +9.8 | +8.8 | robust to top-3 removal |
| crypto | trailing 5% | rule-filtered longs | 264 | 19 | +11.5 | +8.0 | 60 | +nan | +2.4 | +9.8 | +8.8 | robust to top-3 removal |
| crypto | trailing 8% | unfiltered L+S | 386 | 32 | +12.0 | +6.5 | 64 | +nan | +2.8 | +10.8 | +9.5 | robust to top-3 removal |
| crypto | trailing 8% | rule-filtered L+S | 264 | 19 | +18.6 | +25.2 | 77 | +nan | +3.6 | +17.5 | +16.2 | robust to top-3 removal |
| crypto | trailing 8% | unfiltered longs | 264 | 19 | +18.6 | +25.2 | 77 | +nan | +3.6 | +17.5 | +16.2 | robust to top-3 removal |
| crypto | trailing 8% | rule-filtered longs | 264 | 19 | +18.6 | +25.2 | 77 | +nan | +3.6 | +17.5 | +16.2 | robust to top-3 removal |
| crypto | trailing 12% | unfiltered L+S | 386 | 32 | +15.9 | +8.3 | 65 | +nan | +5.6 | +13.0 | +11.8 | robust to top-3 removal |
| crypto | trailing 12% | rule-filtered L+S | 264 | 19 | +25.9 | +28.1 | 82 | +nan | +8.4 | +22.7 | +19.5 | robust to top-3 removal |
| crypto | trailing 12% | unfiltered longs | 264 | 19 | +25.9 | +28.1 | 82 | +nan | +8.4 | +22.7 | +19.5 | robust to top-3 removal |
| crypto | trailing 12% | rule-filtered longs | 264 | 19 | +25.9 | +28.1 | 82 | +nan | +8.4 | +22.7 | +19.5 | robust to top-3 removal |

### I. Fibonacci exits vs ATR stops vs trailing 8% vs hold (same setups with a confirmed zigzag leg; Z=2xATR14 zigzag, 0.5xATR buffer; x_mkt = vs BTC for crypto, vs SPY for stocks)
| segment | policy | N | tickers | mean | median | hit | x_mkt | mean_wo_top1 | x_mkt_wo_top1 | top1 | stopped | target | days | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Grok crypto LONG | hold, no stop | 255 | 19 | +36.9 | +32.1 | 93 | +14.7 | +36.3 | +14.0 | SOL-USD(46) | +0.0 | +0.0 | +53.3 | robust to top-3 removal |
| Grok crypto LONG | trailing 8% (close) | 255 | 19 | +18.2 | +22.9 | 76 | +3.6 | +17.1 | +2.5 | SOL-USD(46) | +54.9 | +0.0 | +32.0 | robust to top-3 removal |
| Grok crypto LONG | 2xATR stop (close) | 255 | 19 | +29.0 | +28.7 | 77 | +11.0 | +27.3 | +9.8 | SOL-USD(46) | +15.3 | +0.0 | +44.7 | robust to top-3 removal |
| Grok crypto LONG | 3xATR stop (close) | 255 | 19 | +33.1 | +31.1 | 87 | +12.6 | +31.7 | +11.3 | SOL-USD(46) | +5.9 | +0.0 | +50.2 | robust to top-3 removal |
| Grok crypto LONG | fib stop + 1.272 tgt (close) | 255 | 19 | +7.6 | +7.9 | 68 | +2.6 | +7.0 | +1.8 | LINK-USD(23) | +29.8 | +62.4 | +10.2 | robust to top-3 removal |
| Grok crypto LONG | fib stop + 1.618 tgt (close) | 255 | 19 | +9.4 | +10.6 | 65 | +2.8 | +8.5 | +2.0 | LINK-USD(23) | +30.2 | +54.9 | +13.1 | robust to top-3 removal |
| Grok crypto LONG | fib stop + 2.618 tgt (close) | 255 | 19 | +15.2 | +12.2 | 64 | +3.7 | +13.1 | +3.2 | ETH-USD(44) | +30.6 | +47.1 | +19.2 | robust to top-3 removal |
| Grok crypto LONG | fib stop + 1/3 at each tgt (close) | 255 | 19 | +10.7 | +11.3 | 67 | -0.9 | +10.4 | -1.2 | AAVE-USD(4) | +30.6 | +61.6 | +19.2 | no edge vs bench |
| Grok crypto LONG | 2xATR stop (intraday) | 255 | 19 | +27.4 | +28.1 | 75 | +10.2 | +25.6 | +8.8 | SOL-USD(46) | +18.0 | +0.0 | +42.8 | robust to top-3 removal |
| Grok crypto LONG | 3xATR stop (intraday) | 255 | 19 | +32.6 | +31.0 | 85 | +12.4 | +31.0 | +11.1 | SOL-USD(46) | +7.5 | +0.0 | +49.4 | robust to top-3 removal |
| Grok crypto LONG | fib stop + 1.272 tgt (intraday) | 255 | 19 | +3.6 | +2.3 | 62 | +0.3 | +3.1 | -0.3 | LINK-USD(23) | +39.2 | +56.5 | +7.6 | LUCK (edge gone w/o top tickers) |
| Grok crypto LONG | fib stop + 1.618 tgt (intraday) | 255 | 19 | +5.7 | +3.8 | 56 | +1.2 | +4.7 | +0.4 | LINK-USD(23) | +41.6 | +47.5 | +10.6 | LUCK (edge gone w/o top tickers) |
| Grok crypto LONG | fib stop + 2.618 tgt (intraday) | 255 | 19 | +10.2 | +2.4 | 55 | +1.7 | +9.0 | +1.1 | LINK-USD(23) | +42.4 | +41.6 | +14.6 | robust to top-3 removal |
| Grok crypto LONG | fib stop + 1/3 at each tgt (intraday) | 255 | 19 | +6.4 | +4.0 | 58 | -2.1 | +6.2 | -2.4 | UNI7083-USD(8) | +42.4 | +53.3 | +14.6 | no edge vs bench |
| All stock LONG | hold, no stop | 242 | 151 | +3.2 | +0.4 | 54 | +1.6 | +2.5 | +0.9 | XP(2) | +0.0 | +0.0 | +19.1 | LUCK (edge gone w/o top tickers) |
| All stock LONG | trailing 8% (close) | 242 | 151 | +1.6 | +0.0 | 51 | +0.7 | +0.9 | +0.0 | XP(2) | +42.6 | +0.0 | +11.5 | LUCK (edge gone w/o top tickers) |
| All stock LONG | 2xATR stop (close) | 242 | 151 | +2.5 | +0.0 | 51 | +1.4 | +1.8 | +0.7 | XP(2) | +26.9 | +0.0 | +15.0 | LUCK (edge gone w/o top tickers) |
| All stock LONG | 3xATR stop (close) | 242 | 151 | +3.5 | +0.3 | 53 | +2.2 | +2.8 | +1.5 | XP(2) | +14.0 | +0.0 | +17.2 | robust to top-3 removal |
| All stock LONG | fib stop + 1.272 tgt (close) | 242 | 151 | +1.2 | -1.0 | 45 | +0.9 | +0.7 | +0.4 | RXRX(4) | +48.3 | +25.2 | +7.7 | LUCK (edge gone w/o top tickers) |
| All stock LONG | fib stop + 1.618 tgt (close) | 242 | 151 | +1.2 | -1.2 | 43 | +0.8 | +0.8 | +0.4 | RXRX(4) | +48.8 | +11.2 | +9.0 | LUCK (edge gone w/o top tickers) |
| All stock LONG | fib stop + 2.618 tgt (close) | 242 | 151 | +1.4 | -1.2 | 42 | +0.9 | +0.9 | +0.4 | RXRX(4) | +49.2 | +5.0 | +10.1 | LUCK (edge gone w/o top tickers) |
| All stock LONG | fib stop + 1/3 at each tgt (close) | 242 | 151 | +1.3 | -1.1 | 44 | +0.8 | +0.8 | +0.4 | RXRX(4) | +49.2 | +24.4 | +10.1 | LUCK (edge gone w/o top tickers) |
| All stock LONG | 2xATR stop (intraday) | 242 | 151 | +2.6 | +0.0 | 50 | +1.7 | +1.9 | +1.0 | XP(2) | +31.4 | +0.0 | +14.0 | robust to top-3 removal |
| All stock LONG | 3xATR stop (intraday) | 242 | 151 | +3.5 | +0.3 | 53 | +2.3 | +2.9 | +1.6 | XP(2) | +15.3 | +0.0 | +16.9 | robust to top-3 removal |
| All stock LONG | fib stop + 1.272 tgt (intraday) | 242 | 151 | +1.4 | -0.5 | 47 | +1.1 | +1.1 | +0.8 | RXRX(4) | +51.7 | +30.2 | +5.9 | robust to top-3 removal |
| All stock LONG | fib stop + 1.618 tgt (intraday) | 242 | 151 | +2.0 | -0.8 | 44 | +1.6 | +1.6 | +1.1 | RXRX(4) | +52.9 | +15.3 | +7.1 | robust to top-3 removal |
| All stock LONG | fib stop + 2.618 tgt (intraday) | 242 | 151 | +1.7 | -1.0 | 42 | +1.2 | +1.3 | +0.8 | RXRX(4) | +53.7 | +7.4 | +8.4 | robust to top-3 removal |
| All stock LONG | fib stop + 1/3 at each tgt (intraday) | 242 | 151 | +1.8 | -0.8 | 43 | +1.2 | +1.3 | +0.8 | RXRX(4) | +53.7 | +28.1 | +8.4 | robust to top-3 removal |
| Rule-filtered stock LONG | hold, no stop | 115 | 70 | +5.0 | +1.1 | 63 | +3.5 | +3.6 | +2.1 | XP(2) | +0.0 | +0.0 | +19.8 | robust to top-3 removal |
| Rule-filtered stock LONG | trailing 8% (close) | 115 | 70 | +3.4 | +0.4 | 57 | +2.6 | +2.0 | +1.1 | XP(2) | +44.3 | +0.0 | +11.9 | robust to top-3 removal |
| Rule-filtered stock LONG | 2xATR stop (close) | 115 | 70 | +5.1 | +1.0 | 62 | +3.9 | +3.7 | +2.5 | XP(2) | +20.0 | +0.0 | +15.8 | robust to top-3 removal |
| Rule-filtered stock LONG | 3xATR stop (close) | 115 | 70 | +5.5 | +1.1 | 63 | +4.1 | +4.1 | +2.7 | XP(2) | +10.4 | +0.0 | +17.9 | robust to top-3 removal |
| Rule-filtered stock LONG | fib stop + 1.272 tgt (close) | 115 | 70 | +2.5 | +1.0 | 57 | +2.0 | +1.8 | +1.3 | RXRX(3) | +30.4 | +36.5 | +9.6 | robust to top-3 removal |
| Rule-filtered stock LONG | fib stop + 1.618 tgt (close) | 115 | 70 | +3.0 | +0.3 | 54 | +2.4 | +2.4 | +1.8 | WGS(1) | +30.4 | +15.7 | +11.1 | robust to top-3 removal |
| Rule-filtered stock LONG | fib stop + 2.618 tgt (close) | 115 | 70 | +2.6 | +0.3 | 53 | +1.9 | +2.0 | +1.3 | RXRX(3) | +31.3 | +7.0 | +12.1 | robust to top-3 removal |
| Rule-filtered stock LONG | fib stop + 1/3 at each tgt (close) | 115 | 70 | +2.7 | +0.5 | 55 | +1.9 | +2.1 | +1.4 | RXRX(3) | +31.3 | +35.7 | +12.1 | robust to top-3 removal |
| Rule-filtered stock LONG | 2xATR stop (intraday) | 115 | 70 | +5.2 | +1.0 | 62 | +4.1 | +3.8 | +2.7 | XP(2) | +25.2 | +0.0 | +15.1 | robust to top-3 removal |
| Rule-filtered stock LONG | 3xATR stop (intraday) | 115 | 70 | +5.5 | +1.1 | 63 | +4.2 | +4.1 | +2.8 | XP(2) | +12.2 | +0.0 | +17.4 | robust to top-3 removal |
| Rule-filtered stock LONG | fib stop + 1.272 tgt (intraday) | 115 | 70 | +2.2 | +0.5 | 55 | +1.8 | +1.8 | +1.3 | VICR(3) | +38.3 | +43.5 | +7.2 | robust to top-3 removal |
| Rule-filtered stock LONG | fib stop + 1.618 tgt (intraday) | 115 | 70 | +3.2 | +0.0 | 50 | +2.6 | +2.3 | +1.8 | RXRX(3) | +38.3 | +19.1 | +9.2 | robust to top-3 removal |
| Rule-filtered stock LONG | fib stop + 2.618 tgt (intraday) | 115 | 70 | +2.4 | -0.2 | 49 | +1.6 | +1.8 | +1.1 | RXRX(3) | +39.1 | +7.0 | +10.2 | robust to top-3 removal |
| Rule-filtered stock LONG | fib stop + 1/3 at each tgt (intraday) | 115 | 70 | +2.6 | +0.0 | 50 | +1.9 | +2.0 | +1.3 | RXRX(3) | +39.1 | +42.6 | +10.2 | robust to top-3 removal |
| Perplexity stock LONG | hold, no stop | 59 | 42 | +5.8 | +1.7 | 59 | +5.0 | +3.1 | +2.2 | XP(2) | +0.0 | +0.0 | +23.7 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | trailing 8% (close) | 59 | 42 | +2.2 | -1.2 | 44 | +2.3 | -0.7 | -0.6 | XP(2) | +54.2 | +0.0 | +13.9 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | 2xATR stop (close) | 59 | 42 | +6.0 | +0.6 | 53 | +5.6 | +3.2 | +2.8 | XP(2) | +27.1 | +0.0 | +18.8 | robust to top-3 removal |
| Perplexity stock LONG | 3xATR stop (close) | 59 | 42 | +6.3 | +1.1 | 56 | +5.9 | +3.6 | +3.2 | XP(2) | +20.3 | +0.0 | +20.2 | robust to top-3 removal |
| Perplexity stock LONG | fib stop + 1.272 tgt (close) | 59 | 42 | +0.2 | -2.1 | 34 | +0.4 | -0.5 | -0.3 | MRVL(2) | +57.6 | +13.6 | +10.4 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | fib stop + 1.618 tgt (close) | 59 | 42 | +0.3 | -2.1 | 34 | +0.5 | -0.4 | -0.1 | MRVL(2) | +57.6 | +6.8 | +10.8 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | fib stop + 2.618 tgt (close) | 59 | 42 | +0.5 | -2.3 | 32 | +0.7 | -0.4 | -0.3 | XP(2) | +59.3 | +5.1 | +11.3 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | fib stop + 1/3 at each tgt (close) | 59 | 42 | +0.3 | -2.1 | 34 | +0.5 | -0.3 | -0.1 | XP(2) | +59.3 | +11.9 | +11.3 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | 2xATR stop (intraday) | 59 | 42 | +6.2 | +0.6 | 53 | +5.9 | +3.4 | +3.1 | XP(2) | +32.2 | +0.0 | +18.0 | robust to top-3 removal |
| Perplexity stock LONG | 3xATR stop (intraday) | 59 | 42 | +6.3 | +1.1 | 56 | +5.9 | +3.6 | +3.1 | XP(2) | +22.0 | +0.0 | +19.9 | robust to top-3 removal |
| Perplexity stock LONG | fib stop + 1.272 tgt (intraday) | 59 | 42 | +0.2 | -1.6 | 29 | +0.4 | -0.4 | -0.2 | MRVL(2) | +64.4 | +13.6 | +7.9 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | fib stop + 1.618 tgt (intraday) | 59 | 42 | +0.5 | -1.6 | 29 | +0.6 | -0.2 | +0.0 | MRVL(2) | +64.4 | +5.1 | +8.3 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | fib stop + 2.618 tgt (intraday) | 59 | 42 | -0.1 | -1.6 | 25 | +0.1 | -0.8 | -0.6 | MRVL(2) | +66.1 | +1.7 | +8.6 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | fib stop + 1/3 at each tgt (intraday) | 59 | 42 | +0.2 | -1.6 | 27 | +0.3 | -0.5 | -0.2 | MRVL(2) | +66.1 | +11.9 | +8.6 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | hold, no stop | 142 | 96 | +1.6 | +0.1 | 52 | -0.2 | +0.9 | -0.9 | IOVA(1) | +0.0 | +0.0 | +17.1 | no edge vs bench |
| Grok stock LONG | trailing 8% (close) | 142 | 96 | +1.1 | +0.2 | 52 | -0.0 | +0.8 | -0.4 | WGS(1) | +42.3 | +0.0 | +10.8 | no edge vs bench |
| Grok stock LONG | 2xATR stop (close) | 142 | 96 | +1.0 | -0.1 | 50 | -0.2 | +0.4 | -0.9 | IOVA(1) | +29.6 | +0.0 | +13.0 | no edge vs bench |
| Grok stock LONG | 3xATR stop (close) | 142 | 96 | +1.9 | +0.1 | 52 | +0.4 | +1.3 | -0.3 | IOVA(1) | +14.1 | +0.0 | +15.5 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fib stop + 1.272 tgt (close) | 142 | 96 | +1.0 | -0.4 | 48 | +0.6 | +0.7 | +0.2 | VICR(3) | +45.1 | +29.6 | +6.8 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fib stop + 1.618 tgt (close) | 142 | 96 | +1.2 | -0.9 | 44 | +0.6 | +0.7 | +0.1 | WGS(1) | +45.8 | +13.4 | +8.5 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fib stop + 2.618 tgt (close) | 142 | 96 | +1.1 | -0.9 | 44 | +0.4 | +0.6 | -0.1 | RXRX(3) | +45.8 | +4.9 | +9.8 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fib stop + 1/3 at each tgt (close) | 142 | 96 | +1.1 | -0.8 | 46 | +0.4 | +0.7 | -0.0 | RXRX(3) | +45.8 | +28.9 | +9.8 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | 2xATR stop (intraday) | 142 | 96 | +1.2 | -0.1 | 50 | +0.0 | +0.6 | -0.6 | IOVA(1) | +32.4 | +0.0 | +12.0 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | 3xATR stop (intraday) | 142 | 96 | +2.0 | +0.1 | 52 | +0.5 | +1.4 | -0.2 | IOVA(1) | +15.5 | +0.0 | +15.2 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fib stop + 1.272 tgt (intraday) | 142 | 96 | +1.6 | +0.3 | 55 | +1.1 | +1.2 | +0.7 | VICR(3) | +46.5 | +35.9 | +5.3 | robust to top-3 removal |
| Grok stock LONG | fib stop + 1.618 tgt (intraday) | 142 | 96 | +2.4 | +0.0 | 50 | +1.7 | +1.9 | +1.3 | WGS(1) | +47.9 | +17.6 | +7.1 | robust to top-3 removal |
| Grok stock LONG | fib stop + 2.618 tgt (intraday) | 142 | 96 | +2.0 | -0.1 | 49 | +1.2 | +1.6 | +0.8 | RXRX(3) | +48.6 | +9.2 | +8.6 | robust to top-3 removal |
| Grok stock LONG | fib stop + 1/3 at each tgt (intraday) | 142 | 96 | +2.0 | -0.0 | 50 | +1.2 | +1.7 | +0.9 | RXRX(3) | +48.6 | +33.8 | +8.6 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | hold, no stop | 60 | 49 | +3.6 | +6.3 | 73 | +4.8 | +3.4 | +4.6 | LULU(3) | +0.0 | +0.0 | +19.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | trailing 8% (close) | 60 | 49 | +3.4 | +3.1 | 62 | +4.2 | +3.1 | +3.9 | WHR(1) | +35.0 | +0.0 | +13.8 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | 2xATR stop (close) | 60 | 49 | +4.2 | +6.3 | 72 | +5.2 | +4.0 | +5.0 | LULU(3) | +11.7 | +0.0 | +17.6 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | 3xATR stop (close) | 60 | 49 | +4.3 | +6.3 | 73 | +5.4 | +4.1 | +5.2 | LULU(3) | +6.7 | +0.0 | +18.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fib stop + 1.272 tgt (close) | 60 | 49 | +3.3 | +2.9 | 78 | +3.6 | +3.0 | +3.3 | LULU(3) | +10.0 | +43.3 | +10.2 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fib stop + 1.618 tgt (close) | 60 | 49 | +3.9 | +3.9 | 77 | +4.4 | +3.7 | +4.2 | LULU(3) | +10.0 | +31.7 | +12.4 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fib stop + 2.618 tgt (close) | 60 | 49 | +4.5 | +5.4 | 77 | +5.3 | +4.3 | +5.1 | LULU(3) | +10.0 | +18.3 | +15.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fib stop + 1/3 at each tgt (close) | 60 | 49 | +3.9 | +3.8 | 77 | +4.6 | +3.7 | +4.4 | LULU(3) | +10.0 | +43.3 | +15.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | 2xATR stop (intraday) | 60 | 49 | +4.0 | +6.3 | 72 | +5.0 | +3.8 | +4.8 | LULU(3) | +16.7 | +0.0 | +16.2 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | 3xATR stop (intraday) | 60 | 49 | +4.5 | +6.3 | 73 | +5.6 | +4.4 | +5.5 | LULU(3) | +6.7 | +0.0 | +17.6 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fib stop + 1.272 tgt (intraday) | 60 | 49 | +3.0 | +2.5 | 77 | +3.2 | +2.8 | +2.9 | LULU(3) | +15.0 | +46.7 | +8.3 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fib stop + 1.618 tgt (intraday) | 60 | 49 | +3.1 | +3.2 | 73 | +3.6 | +2.9 | +3.3 | LULU(3) | +16.7 | +31.7 | +10.9 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fib stop + 2.618 tgt (intraday) | 60 | 49 | +3.9 | +4.0 | 73 | +4.6 | +3.7 | +4.3 | LULU(3) | +16.7 | +23.3 | +12.9 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fib stop + 1/3 at each tgt (intraday) | 60 | 49 | +3.4 | +3.5 | 73 | +4.1 | +3.2 | +3.8 | LULU(3) | +16.7 | +45.0 | +12.9 | robust to top-3 removal |
| All stock SHORT | hold, no stop | 189 | 101 | -1.0 | -1.2 | 44 | +0.5 | -1.3 | +0.2 | LCID(1) | +0.0 | +0.0 | +16.2 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | trailing 8% (close) | 189 | 101 | -0.7 | -2.0 | 39 | +0.3 | -0.9 | +0.0 | LCID(1) | +37.0 | +0.0 | +10.9 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | 2xATR stop (close) | 189 | 101 | -0.5 | -1.8 | 43 | +0.8 | -0.7 | +0.5 | LCID(1) | +28.6 | +0.0 | +13.2 | robust to top-3 removal |
| All stock SHORT | 3xATR stop (close) | 189 | 101 | -0.7 | -1.2 | 44 | +0.6 | -1.0 | +0.3 | LCID(1) | +17.5 | +0.0 | +14.7 | robust to top-3 removal |
| All stock SHORT | fib stop + 1.272 tgt (close) | 189 | 101 | +0.0 | +0.0 | 50 | +0.4 | -0.1 | +0.2 | LCID(1) | +55.6 | +19.6 | +6.9 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fib stop + 1.618 tgt (close) | 189 | 101 | -0.0 | -0.6 | 48 | +0.5 | -0.2 | +0.3 | LCID(1) | +57.1 | +13.2 | +8.1 | robust to top-3 removal |
| All stock SHORT | fib stop + 2.618 tgt (close) | 189 | 101 | +0.3 | -0.6 | 48 | +0.9 | -0.0 | +0.6 | LCID(1) | +57.1 | +7.4 | +9.4 | robust to top-3 removal |
| All stock SHORT | fib stop + 1/3 at each tgt (close) | 189 | 101 | +0.1 | -0.3 | 48 | +0.8 | -0.1 | +0.6 | LCID(1) | +57.1 | +18.0 | +9.4 | robust to top-3 removal |
| All stock SHORT | 2xATR stop (intraday) | 189 | 101 | -0.3 | -1.8 | 42 | +0.9 | -0.6 | +0.6 | LCID(1) | +37.0 | +0.0 | +12.4 | robust to top-3 removal |
| All stock SHORT | 3xATR stop (intraday) | 189 | 101 | -0.4 | -1.2 | 44 | +0.9 | -0.7 | +0.6 | LCID(1) | +20.1 | +0.0 | +14.4 | robust to top-3 removal |
| All stock SHORT | fib stop + 1.272 tgt (intraday) | 189 | 101 | -0.1 | -0.4 | 47 | +0.2 | -0.2 | +0.1 | LULU(3) | +59.3 | +21.7 | +5.0 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fib stop + 1.618 tgt (intraday) | 189 | 101 | -0.3 | -0.5 | 45 | +0.1 | -0.4 | -0.0 | LULU(3) | +60.8 | +15.3 | +6.4 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fib stop + 2.618 tgt (intraday) | 189 | 101 | -0.1 | -0.7 | 42 | +0.4 | -0.2 | +0.3 | PATH(2) | +63.5 | +10.1 | +7.2 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fib stop + 1/3 at each tgt (intraday) | 189 | 101 | -0.1 | -0.5 | 46 | +0.4 | -0.2 | +0.3 | LULU(3) | +63.5 | +17.5 | +7.2 | robust to top-3 removal |

### J. ATR chandelier TRAILING stops (highest close since entry - k*ATR14; ATR & extreme as of previous bar) vs hold / fixed ATR / trailing 8% (same setups; x_mkt = vs SPY stocks, vs BTC crypto; open trades marked at 2026-10-07 close)
| segment | policy | N | exited | still_open | stopped | mean | median | hit | x_mkt | mean_wo_top1 | mean_wo_top3 | x_mkt_wo_top1 | x_mkt_wo_top3 | days | days_exited | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Grok crypto LONG | hold, no stop | 255 | 0 | 255 | +0.0 | +36.9 | +32.1 | 93 | +14.7 | +36.3 | +30.8 | +14.0 | +8.6 | +53.3 | +nan | robust to top-3 removal |
| Grok crypto LONG | trailing 8% (close) | 255 | 140 | 115 | +54.9 | +18.2 | +22.9 | 76 | +3.6 | +17.1 | +15.9 | +2.5 | +0.8 | +32.0 | +19.0 | robust to top-3 removal |
| Grok crypto LONG | fixed 2xATR (close) | 255 | 39 | 216 | +15.3 | +29.0 | +28.7 | 77 | +11.0 | +27.3 | +23.0 | +9.8 | +5.5 | +44.7 | +10.4 | robust to top-3 removal |
| Grok crypto LONG | fixed 3xATR (close) | 255 | 15 | 240 | +5.9 | +33.1 | +31.1 | 87 | +12.6 | +31.7 | +26.8 | +11.3 | +6.5 | +50.2 | +12.3 | robust to top-3 removal |
| Grok crypto LONG | chandelier 2xATR (close) | 255 | 218 | 37 | +85.5 | +15.9 | +12.4 | 67 | +4.8 | +14.5 | +12.5 | +3.5 | +1.4 | +26.8 | +28.2 | robust to top-3 removal |
| Grok crypto LONG | chandelier 3xATR (close) | 255 | 74 | 181 | +29.0 | +27.2 | +27.5 | 79 | +10.0 | +24.5 | +19.2 | +8.2 | +3.3 | +43.3 | +25.7 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR (close) | 255 | 19 | 236 | +7.5 | +32.7 | +30.5 | 85 | +12.8 | +31.2 | +26.3 | +11.6 | +6.9 | +49.2 | +19.4 | robust to top-3 removal |
| Grok crypto LONG | fixed 2xATR (intraday) | 255 | 46 | 209 | +18.0 | +27.4 | +28.1 | 75 | +10.2 | +25.6 | +21.4 | +8.8 | +5.3 | +42.8 | +8.6 | robust to top-3 removal |
| Grok crypto LONG | fixed 3xATR (intraday) | 255 | 19 | 236 | +7.5 | +32.6 | +31.0 | 85 | +12.4 | +31.0 | +26.1 | +11.1 | +6.3 | +49.4 | +12.2 | robust to top-3 removal |
| Grok crypto LONG | chandelier 2xATR (intraday) | 255 | 222 | 33 | +87.1 | +15.6 | +10.8 | 64 | +4.9 | +14.1 | +12.3 | +3.5 | +1.6 | +23.9 | +24.9 | robust to top-3 removal |
| Grok crypto LONG | chandelier 3xATR (intraday) | 255 | 114 | 141 | +44.7 | +22.2 | +22.8 | 76 | +7.4 | +20.2 | +18.0 | +5.7 | +3.0 | +38.0 | +27.3 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR (intraday) | 255 | 45 | 210 | +17.6 | +29.3 | +28.5 | 82 | +10.9 | +27.0 | +21.9 | +9.3 | +4.4 | +46.3 | +26.8 | robust to top-3 removal |
| All stock LONG | hold, no stop | 242 | 0 | 242 | +0.0 | +3.2 | +0.4 | 54 | +1.6 | +2.5 | +1.5 | +0.9 | -0.0 | +19.1 | +nan | LUCK (edge gone w/o top tickers) |
| All stock LONG | trailing 8% (close) | 242 | 103 | 139 | +42.6 | +1.6 | +0.0 | 51 | +0.7 | +0.9 | +0.3 | +0.0 | -0.5 | +11.5 | +11.4 | LUCK (edge gone w/o top tickers) |
| All stock LONG | fixed 2xATR (close) | 242 | 65 | 177 | +26.9 | +2.5 | +0.0 | 51 | +1.4 | +1.8 | +0.9 | +0.7 | -0.2 | +15.0 | +10.0 | LUCK (edge gone w/o top tickers) |
| All stock LONG | fixed 3xATR (close) | 242 | 34 | 208 | +14.0 | +3.5 | +0.3 | 53 | +2.2 | +2.8 | +1.9 | +1.5 | +0.6 | +17.2 | +11.9 | robust to top-3 removal |
| All stock LONG | chandelier 2xATR (close) | 242 | 112 | 130 | +46.3 | +1.9 | -0.6 | 47 | +1.1 | +1.2 | +0.5 | +0.4 | -0.3 | +11.8 | +12.0 | LUCK (edge gone w/o top tickers) |
| All stock LONG | chandelier 3xATR (close) | 242 | 67 | 175 | +27.7 | +2.9 | +0.0 | 50 | +1.7 | +2.2 | +1.2 | +1.0 | +0.1 | +15.6 | +18.0 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR (close) | 242 | 41 | 201 | +16.9 | +3.2 | +0.3 | 53 | +1.9 | +2.5 | +1.6 | +1.2 | +0.3 | +17.0 | +20.6 | robust to top-3 removal |
| All stock LONG | fixed 2xATR (intraday) | 242 | 76 | 166 | +31.4 | +2.6 | +0.0 | 50 | +1.7 | +1.9 | +1.1 | +1.0 | +0.1 | +14.0 | +7.4 | robust to top-3 removal |
| All stock LONG | fixed 3xATR (intraday) | 242 | 37 | 205 | +15.3 | +3.5 | +0.3 | 53 | +2.3 | +2.9 | +1.9 | +1.6 | +0.7 | +16.9 | +10.1 | robust to top-3 removal |
| All stock LONG | chandelier 2xATR (intraday) | 242 | 136 | 106 | +56.2 | +1.4 | -1.2 | 42 | +0.8 | +0.7 | +0.1 | +0.1 | -0.5 | +10.1 | +10.3 | LUCK (edge gone w/o top tickers) |
| All stock LONG | chandelier 3xATR (intraday) | 242 | 76 | 166 | +31.4 | +2.8 | -0.2 | 50 | +1.7 | +2.1 | +1.2 | +1.0 | +0.2 | +14.7 | +16.0 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR (intraday) | 242 | 47 | 195 | +19.4 | +3.4 | +0.3 | 53 | +2.1 | +2.7 | +1.7 | +1.4 | +0.5 | +16.7 | +18.3 | robust to top-3 removal |
| Rule-filtered stock LONG | hold, no stop | 115 | 0 | 115 | +0.0 | +5.0 | +1.1 | 63 | +3.5 | +3.6 | +1.9 | +2.1 | +0.3 | +19.8 | +nan | robust to top-3 removal |
| Rule-filtered stock LONG | trailing 8% (close) | 115 | 51 | 64 | +44.3 | +3.4 | +0.4 | 57 | +2.6 | +2.0 | +1.2 | +1.1 | +0.4 | +11.9 | +13.3 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 2xATR (close) | 115 | 23 | 92 | +20.0 | +5.1 | +1.0 | 62 | +3.9 | +3.7 | +2.0 | +2.5 | +0.7 | +15.8 | +10.7 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 3xATR (close) | 115 | 12 | 103 | +10.4 | +5.5 | +1.1 | 63 | +4.1 | +4.1 | +2.3 | +2.7 | +0.9 | +17.9 | +15.8 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 2xATR (close) | 115 | 49 | 66 | +42.6 | +4.3 | +0.6 | 59 | +3.4 | +2.9 | +1.6 | +2.0 | +0.7 | +12.4 | +14.8 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 3xATR (close) | 115 | 31 | 84 | +27.0 | +4.5 | +0.4 | 57 | +3.4 | +3.1 | +1.6 | +2.0 | +0.5 | +16.0 | +22.3 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR (close) | 115 | 19 | 96 | +16.5 | +5.3 | +0.6 | 60 | +4.0 | +3.9 | +2.2 | +2.6 | +0.8 | +17.7 | +25.0 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 2xATR (intraday) | 115 | 29 | 86 | +25.2 | +5.2 | +1.0 | 62 | +4.1 | +3.8 | +2.0 | +2.7 | +0.9 | +15.1 | +8.4 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 3xATR (intraday) | 115 | 14 | 101 | +12.2 | +5.5 | +1.1 | 63 | +4.2 | +4.1 | +2.4 | +2.8 | +1.0 | +17.4 | +12.3 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 2xATR (intraday) | 115 | 60 | 55 | +52.2 | +3.6 | +0.4 | 53 | +2.9 | +2.2 | +1.4 | +1.5 | +0.7 | +10.8 | +12.3 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 3xATR (intraday) | 115 | 36 | 79 | +31.3 | +4.3 | +0.4 | 57 | +3.2 | +2.8 | +1.5 | +1.8 | +0.5 | +14.5 | +19.2 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR (intraday) | 115 | 21 | 94 | +18.3 | +5.5 | +0.6 | 60 | +4.3 | +4.1 | +2.3 | +2.8 | +1.1 | +17.4 | +22.4 | robust to top-3 removal |
| Perplexity stock LONG | hold, no stop | 59 | 0 | 59 | +0.0 | +5.8 | +1.7 | 59 | +5.0 | +3.1 | +0.5 | +2.2 | -0.4 | +23.7 | +nan | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | trailing 8% (close) | 59 | 32 | 27 | +54.2 | +2.2 | -1.2 | 44 | +2.3 | -0.7 | -1.8 | -0.6 | -1.7 | +13.9 | +13.7 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | fixed 2xATR (close) | 59 | 16 | 43 | +27.1 | +6.0 | +0.6 | 53 | +5.6 | +3.2 | +0.7 | +2.8 | +0.2 | +18.8 | +8.8 | robust to top-3 removal |
| Perplexity stock LONG | fixed 3xATR (close) | 59 | 12 | 47 | +20.3 | +6.3 | +1.1 | 56 | +5.9 | +3.6 | +1.1 | +3.2 | +0.6 | +20.2 | +11.9 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 2xATR (close) | 59 | 37 | 22 | +62.7 | +2.7 | -1.2 | 42 | +2.9 | -0.2 | -1.5 | +0.0 | -1.2 | +13.3 | +12.8 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | chandelier 3xATR (close) | 59 | 26 | 33 | +44.1 | +3.4 | -1.6 | 44 | +3.3 | +0.6 | -0.7 | +0.4 | -0.9 | +17.5 | +18.1 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | chandelier 4xATR (close) | 59 | 17 | 42 | +28.8 | +5.7 | +0.6 | 53 | +5.3 | +2.9 | +0.3 | +2.5 | -0.1 | +19.9 | +21.4 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | fixed 2xATR (intraday) | 59 | 19 | 40 | +32.2 | +6.2 | +0.6 | 53 | +5.9 | +3.4 | +0.9 | +3.1 | +0.6 | +18.0 | +7.2 | robust to top-3 removal |
| Perplexity stock LONG | fixed 3xATR (intraday) | 59 | 13 | 46 | +22.0 | +6.3 | +1.1 | 56 | +5.9 | +3.6 | +1.0 | +3.1 | +0.6 | +19.9 | +10.9 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 2xATR (intraday) | 59 | 41 | 18 | +69.5 | +2.3 | -1.3 | 37 | +2.7 | -0.6 | -1.8 | -0.2 | -1.3 | +11.2 | +10.8 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | chandelier 3xATR (intraday) | 59 | 27 | 32 | +45.8 | +3.2 | -0.2 | 47 | +3.0 | +0.3 | -1.0 | +0.1 | -1.1 | +16.6 | +16.9 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | chandelier 4xATR (intraday) | 59 | 19 | 40 | +32.2 | +6.0 | +0.6 | 53 | +5.7 | +3.2 | +0.7 | +2.9 | +0.4 | +19.4 | +19.0 | robust to top-3 removal |
| Grok stock LONG | hold, no stop | 142 | 0 | 142 | +0.0 | +1.6 | +0.1 | 52 | -0.2 | +0.9 | +0.1 | -0.9 | -1.7 | +17.1 | +nan | no edge vs bench |
| Grok stock LONG | trailing 8% (close) | 142 | 60 | 82 | +42.3 | +1.1 | +0.2 | 52 | -0.0 | +0.8 | +0.1 | -0.4 | -1.0 | +10.8 | +9.9 | no edge vs bench |
| Grok stock LONG | fixed 2xATR (close) | 142 | 42 | 100 | +29.6 | +1.0 | -0.1 | 50 | -0.2 | +0.4 | -0.4 | -0.9 | -1.6 | +13.0 | +10.1 | no edge vs bench |
| Grok stock LONG | fixed 3xATR (close) | 142 | 20 | 122 | +14.1 | +1.9 | +0.1 | 52 | +0.4 | +1.3 | +0.5 | -0.3 | -1.1 | +15.5 | +11.8 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 2xATR (close) | 142 | 60 | 82 | +42.3 | +1.8 | -0.2 | 49 | +0.5 | +1.1 | +0.4 | -0.1 | -0.8 | +11.4 | +11.0 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 3xATR (close) | 142 | 34 | 108 | +23.9 | +2.3 | +0.3 | 53 | +0.8 | +1.6 | +0.9 | +0.1 | -0.6 | +14.5 | +16.4 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR (close) | 142 | 20 | 122 | +14.1 | +1.9 | +0.2 | 53 | +0.3 | +1.2 | +0.5 | -0.3 | -1.1 | +15.4 | +19.1 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 2xATR (intraday) | 142 | 46 | 96 | +32.4 | +1.2 | -0.1 | 50 | +0.0 | +0.6 | -0.2 | -0.6 | -1.4 | +12.0 | +7.3 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 3xATR (intraday) | 142 | 22 | 120 | +15.5 | +2.0 | +0.1 | 52 | +0.5 | +1.4 | +0.6 | -0.2 | -0.9 | +15.2 | +10.0 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 2xATR (intraday) | 142 | 77 | 65 | +54.2 | +1.1 | -1.2 | 43 | +0.1 | +0.7 | -0.0 | -0.3 | -0.9 | +9.9 | +9.7 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 3xATR (intraday) | 142 | 40 | 102 | +28.2 | +2.3 | +0.0 | 51 | +0.9 | +1.7 | +0.9 | +0.2 | -0.5 | +13.5 | +13.6 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR (intraday) | 142 | 24 | 118 | +16.9 | +2.0 | +0.3 | 53 | +0.5 | +1.4 | +0.6 | -0.2 | -0.9 | +15.1 | +16.9 | LUCK (edge gone w/o top tickers) |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | hold, no stop | 60 | 0 | 60 | +0.0 | +3.6 | +6.3 | 73 | +4.8 | +3.4 | +2.7 | +4.6 | +3.9 | +19.0 | +nan | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | trailing 8% (close) | 60 | 21 | 39 | +35.0 | +3.4 | +3.1 | 62 | +4.2 | +3.1 | +2.3 | +3.9 | +3.1 | +13.8 | +9.7 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 2xATR (close) | 60 | 7 | 53 | +11.7 | +4.2 | +6.3 | 72 | +5.2 | +4.0 | +3.3 | +5.0 | +4.3 | +17.6 | +17.1 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 3xATR (close) | 60 | 4 | 56 | +6.7 | +4.3 | +6.3 | 73 | +5.4 | +4.1 | +3.4 | +5.2 | +4.5 | +18.0 | +22.8 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 2xATR (close) | 60 | 20 | 40 | +33.3 | +4.0 | +3.0 | 68 | +4.8 | +3.8 | +3.1 | +4.6 | +3.9 | +14.0 | +13.6 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 3xATR (close) | 60 | 9 | 51 | +15.0 | +4.4 | +6.3 | 73 | +5.5 | +4.2 | +3.6 | +5.3 | +4.6 | +16.7 | +15.4 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR (close) | 60 | 4 | 56 | +6.7 | +4.5 | +6.3 | 73 | +5.6 | +4.3 | +3.6 | +5.4 | +4.7 | +17.9 | +22.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 2xATR (intraday) | 60 | 10 | 50 | +16.7 | +4.0 | +6.3 | 72 | +5.0 | +3.8 | +3.1 | +4.8 | +4.1 | +16.2 | +12.1 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 3xATR (intraday) | 60 | 4 | 56 | +6.7 | +4.5 | +6.3 | 73 | +5.6 | +4.4 | +3.7 | +5.5 | +4.8 | +17.6 | +17.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 2xATR (intraday) | 60 | 23 | 37 | +38.3 | +3.9 | +2.6 | 67 | +4.7 | +3.7 | +3.0 | +4.4 | +3.7 | +12.3 | +11.4 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 3xATR (intraday) | 60 | 12 | 48 | +20.0 | +4.1 | +5.5 | 68 | +5.1 | +3.9 | +3.3 | +4.9 | +4.2 | +16.1 | +15.4 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR (intraday) | 60 | 5 | 55 | +8.3 | +4.4 | +6.3 | 73 | +5.5 | +4.2 | +3.6 | +5.3 | +4.6 | +17.4 | +20.6 | robust to top-3 removal |
| All stock SHORT | hold, no stop | 189 | 0 | 189 | +0.0 | -1.0 | -1.2 | 44 | +0.5 | -1.3 | -1.6 | +0.2 | -0.1 | +16.2 | +nan | LUCK (edge gone w/o top tickers) |
| All stock SHORT | trailing 8% (close) | 189 | 70 | 119 | +37.0 | -0.7 | -2.0 | 39 | +0.3 | -0.9 | -1.2 | +0.0 | -0.3 | +10.9 | +8.4 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fixed 2xATR (close) | 189 | 54 | 135 | +28.6 | -0.5 | -1.8 | 43 | +0.8 | -0.7 | -1.0 | +0.5 | +0.2 | +13.2 | +8.2 | robust to top-3 removal |
| All stock SHORT | fixed 3xATR (close) | 189 | 33 | 156 | +17.5 | -0.7 | -1.2 | 44 | +0.6 | -1.0 | -1.3 | +0.3 | +0.1 | +14.7 | +12.9 | robust to top-3 removal |
| All stock SHORT | chandelier 2xATR (close) | 189 | 99 | 90 | +52.4 | -0.7 | -2.0 | 39 | +0.5 | -0.9 | -1.2 | +0.2 | -0.1 | +10.8 | +9.9 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | chandelier 3xATR (close) | 189 | 46 | 143 | +24.3 | -0.6 | -1.6 | 44 | +0.7 | -0.8 | -1.1 | +0.4 | +0.1 | +13.7 | +14.3 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR (close) | 189 | 27 | 162 | +14.3 | -0.6 | -1.2 | 44 | +0.7 | -0.9 | -1.2 | +0.4 | +0.1 | +15.0 | +16.8 | robust to top-3 removal |
| All stock SHORT | fixed 2xATR (intraday) | 189 | 70 | 119 | +37.0 | -0.3 | -1.8 | 42 | +0.9 | -0.6 | -0.9 | +0.6 | +0.3 | +12.4 | +7.2 | robust to top-3 removal |
| All stock SHORT | fixed 3xATR (intraday) | 189 | 38 | 151 | +20.1 | -0.4 | -1.2 | 44 | +0.9 | -0.7 | -0.9 | +0.6 | +0.4 | +14.4 | +10.6 | robust to top-3 removal |
| All stock SHORT | chandelier 2xATR (intraday) | 189 | 115 | 74 | +60.8 | -0.7 | -1.8 | 38 | +0.3 | -0.9 | -1.2 | +0.0 | -0.3 | +9.5 | +8.1 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | chandelier 3xATR (intraday) | 189 | 56 | 133 | +29.6 | -0.5 | -1.8 | 41 | +0.7 | -0.8 | -1.1 | +0.4 | +0.1 | +12.6 | +11.4 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR (intraday) | 189 | 36 | 153 | +19.0 | -0.5 | -1.3 | 45 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | +14.5 | +16.1 | robust to top-3 removal |

### K. Deeper STRUCTURE stops, no targets (strict PIT 2xATR14 zigzag; leg = last confirmed swing high + its origin low; mirrored for shorts) vs hold / fixed 3xATR / chandelier 4xATR (same setups; stop_med/p25 = initial stop distance % of entry; fallback% = structure level already breached at entry, next deeper confirmed pivot used)
| segment | policy | N | exited | still_open | stopped | stop_med | stop_p25 | mean | median | hit | x_mkt | mean_wo_top1 | mean_wo_top3 | x_mkt_wo_top1 | x_mkt_wo_top3 | days | fallback | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Grok crypto LONG | hold, no stop | 254 | 0 | 254 | +0.0 | +nan | +nan | +36.8 | +32.0 | 93 | +14.8 | +36.2 | +30.7 | +14.0 | +8.6 | +53.3 | +nan | robust to top-3 removal |
| Grok crypto LONG | fixed 3xATR (close) | 254 | 15 | 239 | +5.9 | +10.5 | +8.5 | +33.1 | +31.1 | 87 | +12.6 | +31.6 | +26.8 | +11.3 | +6.5 | +50.2 | +nan | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR (close) | 254 | 19 | 235 | +7.5 | +13.9 | +11.3 | +32.7 | +30.3 | 85 | +12.8 | +31.1 | +26.2 | +11.6 | +6.8 | +49.1 | +nan | robust to top-3 removal |
| Grok crypto LONG | (a) below 0.786 - 0.5ATR (close) | 254 | 35 | 219 | +13.8 | +10.4 | +5.4 | +29.2 | +28.0 | 79 | +11.0 | +28.6 | +23.9 | +10.2 | +6.2 | +45.1 | +7.9 | robust to top-3 removal |
| Grok crypto LONG | (b) below swing origin - 0.5ATR (close) | 254 | 25 | 229 | +9.8 | +14.4 | +6.9 | +30.3 | +28.5 | 83 | +11.3 | +29.4 | +24.8 | +10.3 | +6.3 | +47.1 | +3.9 | robust to top-3 removal |
| Grok crypto LONG | (c) below swing origin - 1.0ATR (close) | 254 | 15 | 239 | +5.9 | +16.3 | +8.9 | +32.7 | +29.8 | 87 | +12.3 | +31.1 | +26.4 | +11.1 | +6.5 | +49.6 | +2.8 | robust to top-3 removal |
| Grok crypto LONG | (d) structure trail, confirmed higher-lows (close) | 254 | 42 | 212 | +16.5 | +14.4 | +6.9 | +27.6 | +27.3 | 77 | +10.2 | +25.0 | +22.5 | +7.9 | +5.4 | +43.8 | +3.9 | robust to top-3 removal |
| Grok crypto LONG | fixed 3xATR (intraday) | 254 | 19 | 235 | +7.5 | +10.5 | +8.5 | +32.5 | +30.9 | 85 | +12.4 | +31.0 | +26.0 | +11.1 | +6.3 | +49.4 | +nan | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR (intraday) | 254 | 45 | 209 | +17.7 | +13.9 | +11.3 | +29.2 | +28.5 | 82 | +10.9 | +26.9 | +21.8 | +9.2 | +4.4 | +46.3 | +nan | robust to top-3 removal |
| Grok crypto LONG | (a) below 0.786 - 0.5ATR (intraday) | 254 | 41 | 213 | +16.1 | +10.4 | +5.4 | +27.5 | +27.3 | 76 | +9.8 | +25.0 | +22.6 | +7.5 | +5.1 | +43.8 | +7.9 | robust to top-3 removal |
| Grok crypto LONG | (b) below swing origin - 0.5ATR (intraday) | 254 | 34 | 220 | +13.4 | +14.4 | +6.9 | +29.2 | +28.1 | 79 | +11.0 | +28.7 | +24.1 | +10.2 | +6.3 | +45.6 | +3.9 | robust to top-3 removal |
| Grok crypto LONG | (c) below swing origin - 1.0ATR (intraday) | 254 | 21 | 233 | +8.3 | +16.3 | +8.9 | +31.3 | +28.8 | 84 | +11.7 | +30.9 | +26.2 | +11.0 | +6.4 | +48.1 | +2.8 | robust to top-3 removal |
| Grok crypto LONG | (d) structure trail, confirmed higher-lows (intraday) | 254 | 107 | 147 | +42.1 | +14.4 | +6.9 | +21.8 | +15.6 | 69 | +7.6 | +19.2 | +16.5 | +5.3 | +2.5 | +37.6 | +3.9 | robust to top-3 removal |
| All stock LONG | hold, no stop | 228 | 0 | 228 | +0.0 | +nan | +nan | +3.7 | +0.5 | 56 | +2.2 | +3.0 | +2.0 | +1.4 | +0.5 | +19.2 | +nan | robust to top-3 removal |
| All stock LONG | fixed 3xATR (close) | 228 | 28 | 200 | +12.3 | +12.6 | +7.7 | +4.0 | +0.4 | 55 | +2.6 | +3.2 | +2.3 | +1.9 | +0.9 | +17.5 | +nan | robust to top-3 removal |
| All stock LONG | chandelier 4xATR (close) | 228 | 36 | 192 | +15.8 | +16.8 | +10.3 | +3.7 | +0.4 | 55 | +2.4 | +3.0 | +2.0 | +1.7 | +0.7 | +17.2 | +nan | robust to top-3 removal |
| All stock LONG | (a) below 0.786 - 0.5ATR (close) | 228 | 75 | 153 | +32.9 | +8.4 | +2.1 | +2.5 | -0.7 | 46 | +1.6 | +1.7 | +0.9 | +0.8 | +0.0 | +13.3 | +24.1 | robust to top-3 removal |
| All stock LONG | (b) below swing origin - 0.5ATR (close) | 228 | 64 | 164 | +28.1 | +11.7 | +3.9 | +2.3 | -0.5 | 48 | +1.3 | +1.6 | +0.7 | +0.6 | -0.3 | +14.3 | +14.9 | LUCK (edge gone w/o top tickers) |
| All stock LONG | (c) below swing origin - 1.0ATR (close) | 228 | 49 | 179 | +21.5 | +13.1 | +5.2 | +3.7 | +0.1 | 51 | +2.6 | +3.0 | +2.0 | +1.8 | +0.9 | +15.4 | +10.1 | robust to top-3 removal |
| All stock LONG | (d) structure trail, confirmed higher-lows (close) | 228 | 69 | 159 | +30.3 | +11.7 | +3.9 | +2.6 | -0.5 | 48 | +1.6 | +1.8 | +0.9 | +0.8 | -0.0 | +14.1 | +14.9 | LUCK (edge gone w/o top tickers) |
| All stock LONG | fixed 3xATR (intraday) | 228 | 31 | 197 | +13.6 | +12.6 | +7.7 | +4.0 | +0.4 | 55 | +2.7 | +3.3 | +2.3 | +2.0 | +1.0 | +17.1 | +nan | robust to top-3 removal |
| All stock LONG | chandelier 4xATR (intraday) | 228 | 40 | 188 | +17.5 | +16.8 | +10.3 | +3.8 | +0.4 | 55 | +2.6 | +3.1 | +2.1 | +1.8 | +0.9 | +16.9 | +nan | robust to top-3 removal |
| All stock LONG | (a) below 0.786 - 0.5ATR (intraday) | 228 | 91 | 137 | +39.9 | +8.4 | +2.1 | +1.4 | -0.8 | 41 | +0.7 | +1.0 | +0.4 | +0.2 | -0.3 | +11.0 | +24.1 | LUCK (edge gone w/o top tickers) |
| All stock LONG | (b) below swing origin - 0.5ATR (intraday) | 228 | 79 | 149 | +34.6 | +11.7 | +3.9 | +1.6 | -0.8 | 45 | +0.7 | +1.2 | +0.5 | +0.3 | -0.4 | +12.5 | +14.9 | LUCK (edge gone w/o top tickers) |
| All stock LONG | (c) below swing origin - 1.0ATR (intraday) | 228 | 68 | 160 | +29.8 | +13.1 | +5.2 | +2.1 | -0.6 | 46 | +1.1 | +1.6 | +0.7 | +0.6 | -0.3 | +14.0 | +10.1 | LUCK (edge gone w/o top tickers) |
| All stock LONG | (d) structure trail, confirmed higher-lows (intraday) | 228 | 85 | 143 | +37.3 | +11.7 | +3.9 | +1.8 | -0.6 | 45 | +0.9 | +1.4 | +0.8 | +0.5 | -0.1 | +12.3 | +14.9 | LUCK (edge gone w/o top tickers) |
| Rule-filtered stock LONG | hold, no stop | 115 | 0 | 115 | +0.0 | +nan | +nan | +5.0 | +1.1 | 63 | +3.5 | +3.6 | +1.9 | +2.1 | +0.3 | +19.8 | +nan | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 3xATR (close) | 115 | 12 | 103 | +10.4 | +13.0 | +8.3 | +5.5 | +1.1 | 63 | +4.1 | +4.1 | +2.3 | +2.7 | +0.9 | +17.9 | +nan | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR (close) | 115 | 19 | 96 | +16.5 | +17.3 | +11.1 | +5.3 | +0.6 | 60 | +4.0 | +3.9 | +2.2 | +2.6 | +0.8 | +17.7 | +nan | robust to top-3 removal |
| Rule-filtered stock LONG | (a) below 0.786 - 0.5ATR (close) | 115 | 28 | 87 | +24.3 | +11.3 | +3.2 | +4.2 | +0.4 | 55 | +3.2 | +2.8 | +1.4 | +1.7 | +0.4 | +14.7 | +14.8 | robust to top-3 removal |
| Rule-filtered stock LONG | (b) below swing origin - 0.5ATR (close) | 115 | 23 | 92 | +20.0 | +16.2 | +5.2 | +4.3 | +0.4 | 57 | +3.1 | +2.9 | +1.4 | +1.7 | +0.1 | +15.7 | +6.1 | robust to top-3 removal |
| Rule-filtered stock LONG | (c) below swing origin - 1.0ATR (close) | 115 | 20 | 95 | +17.4 | +18.2 | +6.6 | +5.2 | +0.6 | 59 | +4.1 | +3.8 | +2.1 | +2.7 | +0.9 | +15.4 | +3.5 | robust to top-3 removal |
| Rule-filtered stock LONG | (d) structure trail, confirmed higher-lows (close) | 115 | 27 | 88 | +23.5 | +16.2 | +5.2 | +4.6 | +0.4 | 57 | +3.4 | +3.2 | +1.7 | +2.0 | +0.5 | +15.6 | +6.1 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 3xATR (intraday) | 115 | 14 | 101 | +12.2 | +13.0 | +8.3 | +5.5 | +1.1 | 63 | +4.2 | +4.1 | +2.4 | +2.8 | +1.0 | +17.4 | +nan | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR (intraday) | 115 | 21 | 94 | +18.3 | +17.3 | +11.1 | +5.5 | +0.6 | 60 | +4.3 | +4.1 | +2.3 | +2.8 | +1.1 | +17.4 | +nan | robust to top-3 removal |
| Rule-filtered stock LONG | (a) below 0.786 - 0.5ATR (intraday) | 115 | 37 | 78 | +32.2 | +11.3 | +3.2 | +2.0 | -0.1 | 49 | +1.1 | +1.2 | +0.5 | +0.3 | -0.4 | +11.1 | +14.8 | LUCK (edge gone w/o top tickers) |
| Rule-filtered stock LONG | (b) below swing origin - 0.5ATR (intraday) | 115 | 30 | 85 | +26.1 | +16.2 | +5.2 | +2.6 | +0.1 | 52 | +1.5 | +1.7 | +0.9 | +0.7 | -0.2 | +13.2 | +6.1 | LUCK (edge gone w/o top tickers) |
| Rule-filtered stock LONG | (c) below swing origin - 1.0ATR (intraday) | 115 | 28 | 87 | +24.3 | +18.2 | +6.6 | +2.5 | +0.1 | 52 | +1.4 | +1.6 | +0.4 | +0.6 | -0.6 | +13.8 | +3.5 | LUCK (edge gone w/o top tickers) |
| Rule-filtered stock LONG | (d) structure trail, confirmed higher-lows (intraday) | 115 | 35 | 80 | +30.4 | +16.2 | +5.2 | +2.7 | +0.1 | 52 | +1.7 | +1.9 | +1.3 | +0.9 | +0.3 | +12.8 | +6.1 | robust to top-3 removal |
| Perplexity stock LONG | hold, no stop | 57 | 0 | 57 | +0.0 | +nan | +nan | +6.7 | +1.7 | 61 | +5.8 | +3.8 | +1.2 | +2.9 | +0.3 | +23.2 | +nan | robust to top-3 removal |
| Perplexity stock LONG | fixed 3xATR (close) | 57 | 10 | 47 | +17.5 | +12.3 | +8.6 | +7.1 | +1.2 | 58 | +6.6 | +4.2 | +1.7 | +3.7 | +1.2 | +20.6 | +nan | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR (close) | 57 | 15 | 42 | +26.3 | +16.4 | +11.5 | +6.4 | +0.6 | 54 | +5.9 | +3.5 | +0.9 | +3.1 | +0.4 | +20.2 | +nan | robust to top-3 removal |
| Perplexity stock LONG | (a) below 0.786 - 0.5ATR (close) | 57 | 25 | 32 | +43.9 | +4.1 | +0.6 | +3.5 | -1.3 | 40 | +3.3 | +0.6 | -0.7 | +0.4 | -0.9 | +14.2 | +26.3 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | (b) below swing origin - 0.5ATR (close) | 57 | 23 | 34 | +40.4 | +8.4 | +2.3 | +3.7 | -1.3 | 42 | +3.5 | +0.8 | -0.6 | +0.5 | -0.8 | +15.4 | +8.8 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | (c) below swing origin - 1.0ATR (close) | 57 | 12 | 45 | +21.1 | +12.0 | +4.5 | +7.5 | +1.7 | 60 | +6.9 | +4.6 | +2.1 | +4.1 | +1.5 | +18.8 | +8.8 | robust to top-3 removal |
| Perplexity stock LONG | (d) structure trail, confirmed higher-lows (close) | 57 | 24 | 33 | +42.1 | +8.4 | +2.3 | +3.9 | -1.3 | 42 | +3.7 | +1.0 | -0.3 | +0.8 | -0.5 | +15.2 | +8.8 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | fixed 3xATR (intraday) | 57 | 11 | 46 | +19.3 | +12.3 | +8.6 | +7.1 | +1.2 | 58 | +6.6 | +4.2 | +1.7 | +3.7 | +1.2 | +20.2 | +nan | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR (intraday) | 57 | 17 | 40 | +29.8 | +16.4 | +11.5 | +6.5 | +0.6 | 54 | +6.1 | +3.6 | +1.0 | +3.3 | +0.6 | +19.7 | +nan | robust to top-3 removal |
| Perplexity stock LONG | (a) below 0.786 - 0.5ATR (intraday) | 57 | 28 | 29 | +49.1 | +4.1 | +0.6 | +1.0 | -0.7 | 37 | +0.8 | +0.4 | -0.7 | +0.2 | -0.8 | +10.6 | +26.3 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | (b) below swing origin - 0.5ATR (intraday) | 57 | 27 | 30 | +47.4 | +8.4 | +2.3 | +0.4 | -1.3 | 37 | +0.1 | -0.3 | -1.4 | -0.5 | -1.6 | +11.8 | +8.8 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | (c) below swing origin - 1.0ATR (intraday) | 57 | 23 | 34 | +40.4 | +12.0 | +4.5 | +1.1 | -1.7 | 40 | +0.7 | +0.4 | -0.8 | +0.1 | -1.1 | +16.1 | +8.8 | LUCK (edge gone w/o top tickers) |
| Perplexity stock LONG | (d) structure trail, confirmed higher-lows (intraday) | 57 | 28 | 29 | +49.1 | +8.4 | +2.3 | +0.6 | -0.9 | 37 | +0.4 | -0.0 | -1.1 | -0.2 | -1.2 | +11.7 | +8.8 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | hold, no stop | 131 | 0 | 131 | +0.0 | +nan | +nan | +2.0 | +0.3 | 54 | +0.2 | +1.2 | +0.4 | -0.6 | -1.5 | +17.4 | +nan | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 3xATR (close) | 131 | 16 | 115 | +12.2 | +12.9 | +8.2 | +2.2 | +0.3 | 54 | +0.6 | +1.5 | +0.7 | -0.1 | -1.0 | +16.0 | +nan | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR (close) | 131 | 18 | 113 | +13.7 | +17.3 | +10.9 | +2.3 | +0.4 | 55 | +0.7 | +1.5 | +0.7 | -0.1 | -0.9 | +15.7 | +nan | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | (a) below 0.786 - 0.5ATR (close) | 131 | 39 | 92 | +29.8 | +10.2 | +2.9 | +1.6 | -0.2 | 48 | +0.5 | +0.9 | +0.1 | -0.2 | -0.9 | +12.4 | +21.4 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | (b) below swing origin - 0.5ATR (close) | 131 | 30 | 101 | +22.9 | +13.3 | +5.0 | +1.5 | +0.0 | 50 | +0.2 | +0.7 | -0.2 | -0.6 | -1.4 | +13.6 | +16.0 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | (c) below swing origin - 1.0ATR (close) | 131 | 26 | 105 | +19.8 | +16.1 | +6.3 | +1.8 | -0.2 | 50 | +0.4 | +1.1 | +0.2 | -0.3 | -1.2 | +14.3 | +11.5 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | (d) structure trail, confirmed higher-lows (close) | 131 | 34 | 97 | +26.0 | +13.3 | +5.0 | +1.8 | +0.0 | 50 | +0.5 | +1.0 | +0.2 | -0.2 | -1.1 | +13.3 | +16.0 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 3xATR (intraday) | 131 | 18 | 113 | +13.7 | +12.9 | +8.2 | +2.3 | +0.3 | 54 | +0.8 | +1.6 | +0.8 | +0.0 | -0.8 | +15.6 | +nan | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR (intraday) | 131 | 20 | 111 | +15.3 | +17.3 | +10.9 | +2.4 | +0.4 | 55 | +0.8 | +1.7 | +0.9 | +0.1 | -0.7 | +15.4 | +nan | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | (a) below 0.786 - 0.5ATR (intraday) | 131 | 48 | 83 | +36.6 | +10.2 | +2.9 | +1.3 | -0.7 | 43 | +0.4 | +0.6 | -0.2 | -0.4 | -1.1 | +10.9 | +21.4 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | (b) below swing origin - 0.5ATR (intraday) | 131 | 38 | 93 | +29.0 | +13.3 | +5.0 | +1.7 | -0.2 | 48 | +0.6 | +1.0 | +0.1 | -0.2 | -1.0 | +12.6 | +16.0 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | (c) below swing origin - 1.0ATR (intraday) | 131 | 32 | 99 | +24.4 | +16.1 | +6.3 | +1.9 | -0.2 | 49 | +0.6 | +1.2 | +0.3 | -0.1 | -1.0 | +13.3 | +11.5 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | (d) structure trail, confirmed higher-lows (intraday) | 131 | 42 | 89 | +32.1 | +13.3 | +5.0 | +2.2 | -0.2 | 48 | +1.1 | +1.4 | +0.6 | +0.3 | -0.5 | +12.3 | +16.0 | LUCK (edge gone w/o top tickers) |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | hold, no stop | 60 | 0 | 60 | +0.0 | +nan | +nan | +3.6 | +6.3 | 73 | +4.8 | +3.4 | +2.7 | +4.6 | +3.9 | +19.0 | +nan | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 3xATR (close) | 60 | 4 | 56 | +6.7 | +10.7 | +8.1 | +4.3 | +6.3 | 73 | +5.4 | +4.1 | +3.4 | +5.2 | +4.5 | +18.0 | +nan | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR (close) | 60 | 4 | 56 | +6.7 | +14.3 | +10.7 | +4.5 | +6.3 | 73 | +5.6 | +4.3 | +3.6 | +5.4 | +4.7 | +17.9 | +nan | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | (a) below 0.786 - 0.5ATR (close) | 60 | 6 | 54 | +10.0 | +21.5 | +12.2 | +3.3 | +5.5 | 70 | +4.4 | +3.1 | +2.3 | +4.1 | +3.4 | +17.4 | +5.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | (b) below swing origin - 0.5ATR (close) | 60 | 5 | 55 | +8.3 | +24.3 | +15.3 | +3.5 | +6.3 | 72 | +4.6 | +3.3 | +2.6 | +4.4 | +3.7 | +17.7 | +1.7 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | (c) below swing origin - 1.0ATR (close) | 60 | 4 | 56 | +6.7 | +26.4 | +16.6 | +3.9 | +6.3 | 73 | +5.1 | +3.7 | +3.0 | +4.9 | +4.2 | +17.9 | +0.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | (d) structure trail, confirmed higher-lows (close) | 60 | 8 | 52 | +13.3 | +24.3 | +15.3 | +3.3 | +6.3 | 72 | +4.3 | +3.0 | +2.3 | +4.1 | +3.4 | +17.1 | +1.7 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 3xATR (intraday) | 60 | 4 | 56 | +6.7 | +10.7 | +8.1 | +4.5 | +6.3 | 73 | +5.6 | +4.4 | +3.7 | +5.5 | +4.8 | +17.6 | +nan | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR (intraday) | 60 | 5 | 55 | +8.3 | +14.3 | +10.7 | +4.4 | +6.3 | 73 | +5.5 | +4.2 | +3.6 | +5.3 | +4.6 | +17.4 | +nan | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | (a) below 0.786 - 0.5ATR (intraday) | 60 | 8 | 52 | +13.3 | +21.5 | +12.2 | +3.4 | +4.6 | 68 | +4.4 | +3.2 | +2.4 | +4.2 | +3.4 | +17.1 | +5.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | (b) below swing origin - 0.5ATR (intraday) | 60 | 8 | 52 | +13.3 | +24.3 | +15.3 | +3.2 | +4.6 | 68 | +4.2 | +2.9 | +2.2 | +3.9 | +3.2 | +17.2 | +1.7 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | (c) below swing origin - 1.0ATR (intraday) | 60 | 6 | 54 | +10.0 | +26.4 | +16.6 | +3.6 | +5.5 | 70 | +4.7 | +3.4 | +2.6 | +4.4 | +3.7 | +17.5 | +0.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | (d) structure trail, confirmed higher-lows (intraday) | 60 | 11 | 49 | +18.3 | +24.3 | +15.3 | +2.9 | +4.0 | 67 | +3.9 | +2.6 | +1.9 | +3.6 | +2.9 | +16.5 | +1.7 | robust to top-3 removal |
| All stock SHORT | hold, no stop | 173 | 0 | 173 | +0.0 | +nan | +nan | -0.9 | -1.2 | 46 | +0.5 | -1.2 | -1.5 | +0.2 | -0.1 | +16.8 | +nan | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fixed 3xATR (close) | 173 | 32 | 141 | +18.5 | +10.7 | +8.0 | -0.5 | -1.2 | 46 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | +15.2 | +nan | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR (close) | 173 | 27 | 146 | +15.6 | +14.3 | +10.7 | -0.5 | -1.2 | 46 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | +15.5 | +nan | robust to top-3 removal |
| All stock SHORT | (a) below 0.786 - 0.5ATR (close) | 173 | 68 | 105 | +39.3 | +7.7 | +2.1 | -1.0 | -1.4 | 41 | +0.1 | -1.3 | -1.6 | -0.2 | -0.5 | +13.2 | +26.0 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | (b) below swing origin - 0.5ATR (close) | 173 | 62 | 111 | +35.8 | +10.2 | +2.9 | -1.1 | -1.5 | 43 | +0.1 | -1.4 | -1.7 | -0.2 | -0.5 | +13.9 | +18.5 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | (c) below swing origin - 1.0ATR (close) | 173 | 44 | 129 | +25.4 | +12.1 | +3.3 | -0.5 | -1.2 | 45 | +0.7 | -0.8 | -1.1 | +0.4 | +0.1 | +14.4 | +15.6 | robust to top-3 removal |
| All stock SHORT | (d) structure trail, confirmed higher-lows (close) | 173 | 73 | 100 | +42.2 | +10.2 | +2.9 | -1.1 | -1.8 | 42 | +0.0 | -1.4 | -1.7 | -0.3 | -0.6 | +13.1 | +18.5 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fixed 3xATR (intraday) | 173 | 36 | 137 | +20.8 | +10.7 | +8.0 | -0.1 | -1.2 | 46 | +1.2 | -0.4 | -0.7 | +0.9 | +0.6 | +14.8 | +nan | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR (intraday) | 173 | 35 | 138 | +20.2 | +14.3 | +10.7 | -0.3 | -1.2 | 46 | +1.1 | -0.6 | -0.9 | +0.8 | +0.5 | +14.9 | +nan | robust to top-3 removal |
| All stock SHORT | (a) below 0.786 - 0.5ATR (intraday) | 173 | 79 | 94 | +45.7 | +7.7 | +2.1 | -0.8 | -1.2 | 37 | +0.1 | -1.0 | -1.3 | -0.1 | -0.4 | +11.6 | +26.0 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | (b) below swing origin - 0.5ATR (intraday) | 173 | 74 | 99 | +42.8 | +10.2 | +2.9 | -1.2 | -1.8 | 38 | -0.2 | -1.3 | -1.6 | -0.3 | -0.6 | +12.7 | +18.5 | no edge vs bench |
| All stock SHORT | (c) below swing origin - 1.0ATR (intraday) | 173 | 68 | 105 | +39.3 | +12.1 | +3.3 | -0.6 | -1.6 | 42 | +0.5 | -0.9 | -1.2 | +0.2 | -0.1 | +13.5 | +15.6 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | (d) structure trail, confirmed higher-lows (intraday) | 173 | 83 | 90 | +48.0 | +10.2 | +2.9 | -1.1 | -1.8 | 38 | -0.2 | -1.3 | -1.6 | -0.3 | -0.6 | +12.0 | +18.5 | no edge vs bench |

### L. 4xATR stops + Fibonacci / Elliott profit targets (strict PIT, same legs/setups as K) vs hold / fixed 3xATR / chandelier 4xATR. stop_x/target_x/open_ = trades whose final exit was stop / target / still open (marked 2026-10-07); has_tgt = % with a valid target beyond entry; reached = % that touched (first) target; kept_going = % of target-reached trades where holding the whole position to 2026-10-07 would have been worth more; left_pp = avg pp given up vs holding, over target-reached trades
| segment | policy | N | stop_x | target_x | open_ | has_tgt | reached_pct | kept_going | left_pp | mean | median | hit | x_mkt | mean_wo_top1 | mean_wo_top3 | x_mkt_wo_top1 | x_mkt_wo_top3 | days | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Grok crypto LONG | hold, no stop | 254 | 0 | 0 | 254 | +nan | +nan | +nan | +nan | +36.8 | +32.0 | 93 | +14.8 | +36.2 | +30.7 | +14.0 | +8.6 | +53.3 | robust to top-3 removal |
| Grok crypto LONG | fixed 3xATR, no target (close) | 254 | 15 | 0 | 239 | +nan | +nan | +nan | +nan | +33.1 | +31.1 | 87 | +12.6 | +31.6 | +26.8 | +11.3 | +6.5 | +50.2 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR, no target (close) | 254 | 19 | 0 | 235 | +nan | +nan | +nan | +nan | +32.7 | +30.3 | 85 | +12.8 | +31.1 | +26.2 | +11.6 | +6.8 | +49.1 | robust to top-3 removal |
| Grok crypto LONG | fixed 4xATR + 1.272 ext full (close) | 254 | 4 | 226 | 24 | +96.9 | +89.0 | +83.2 | +24.1 | +14.6 | +13.5 | 94 | +4.8 | +13.4 | +14.0 | +4.0 | +2.9 | +15.8 | robust to top-3 removal |
| Grok crypto LONG | fixed 4xATR + 1.618 ext full (close) | 254 | 4 | 215 | 35 | +96.9 | +84.6 | +83.3 | +22.3 | +17.1 | +14.9 | 93 | +5.7 | +15.9 | +15.8 | +4.8 | +3.7 | +18.6 | robust to top-3 removal |
| Grok crypto LONG | fixed 4xATR + 2.618 ext full (close) | 254 | 4 | 182 | 68 | +96.9 | +71.7 | +60.4 | +10.8 | +28.3 | +26.1 | 91 | +9.5 | +26.4 | +26.0 | +8.2 | +7.1 | +29.2 | robust to top-3 removal |
| Grok crypto LONG | fixed 4xATR + 1/3 at each ext (close) | 254 | 4 | 160 | 90 | +96.9 | +89.0 | +77.9 | +17.2 | +20.7 | +19.4 | 92 | +1.6 | +19.4 | +17.9 | +0.8 | -0.5 | +32.2 | LUCK (edge gone w/o top tickers) |
| Grok crypto LONG | fixed 4xATR + Elliott w3/w5 target (close) | 254 | 4 | 63 | 187 | +30.7 | +24.8 | +68.3 | +13.6 | +32.7 | +28.9 | 91 | +13.5 | +31.3 | +26.9 | +12.6 | +8.4 | +43.3 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 1.272 ext full (close) | 254 | 14 | 216 | 24 | +96.9 | +85.0 | +81.9 | +24.1 | +13.5 | +13.2 | 90 | +4.5 | +12.2 | +12.2 | +3.8 | +2.5 | +14.7 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 1.618 ext full (close) | 254 | 16 | 202 | 36 | +96.9 | +79.5 | +83.7 | +22.1 | +15.4 | +14.1 | 88 | +5.2 | +14.1 | +13.1 | +4.4 | +3.1 | +17.2 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 2.618 ext full (close) | 254 | 19 | 167 | 68 | +96.9 | +65.7 | +62.3 | +11.4 | +25.2 | +21.4 | 85 | +8.1 | +23.1 | +21.9 | +6.7 | +5.2 | +27.3 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 1/3 at each ext (close) | 254 | 19 | 146 | 89 | +96.9 | +85.0 | +78.7 | +17.9 | +18.7 | +17.8 | 87 | +1.2 | +17.2 | +16.1 | +0.4 | -0.9 | +30.2 | LUCK (edge gone w/o top tickers) |
| Grok crypto LONG | chandelier 4xATR + Elliott w3/w5 target (close) | 254 | 17 | 55 | 182 | +30.7 | +21.7 | +74.5 | +14.0 | +29.9 | +27.3 | 86 | +12.3 | +27.9 | +24.3 | +11.0 | +7.5 | +41.1 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 1/3 at 1.618, rest chandelier (close) | 254 | 19 | 0 | 235 | +96.9 | +79.5 | +84.2 | +7.6 | +26.9 | +25.2 | 87 | +7.0 | +25.8 | +22.4 | +6.3 | +3.0 | +49.1 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 1/2 at 1.618, rest chandelier (close) | 254 | 19 | 0 | 235 | +96.9 | +79.5 | +84.2 | +11.3 | +24.0 | +22.7 | 88 | +4.2 | +22.5 | +19.8 | +2.9 | +0.9 | +49.1 | robust to top-3 removal |
| Grok crypto LONG | fixed 3xATR, no target (intraday) | 254 | 19 | 0 | 235 | +nan | +nan | +nan | +nan | +32.5 | +30.9 | 85 | +12.4 | +31.0 | +26.0 | +11.1 | +6.3 | +49.4 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR, no target (intraday) | 254 | 45 | 0 | 209 | +nan | +nan | +nan | +nan | +29.2 | +28.5 | 82 | +10.9 | +26.9 | +21.8 | +9.2 | +4.4 | +46.3 | robust to top-3 removal |
| Grok crypto LONG | fixed 4xATR + 1.272 ext full (intraday) | 254 | 5 | 235 | 14 | +96.9 | +92.5 | +81.7 | +28.2 | +9.9 | +7.9 | 96 | +1.4 | +9.9 | +8.4 | +0.7 | -0.2 | +13.6 | LUCK (edge gone w/o top tickers) |
| Grok crypto LONG | fixed 4xATR + 1.618 ext full (intraday) | 254 | 5 | 223 | 26 | +96.9 | +87.8 | +82.1 | +24.9 | +14.0 | +11.4 | 94 | +3.5 | +12.7 | +12.3 | +2.6 | +1.4 | +17.1 | robust to top-3 removal |
| Grok crypto LONG | fixed 4xATR + 2.618 ext full (intraday) | 254 | 5 | 190 | 59 | +96.9 | +74.8 | +74.7 | +14.8 | +24.8 | +23.6 | 92 | +7.3 | +22.9 | +21.9 | +6.1 | +4.7 | +26.7 | robust to top-3 removal |
| Grok crypto LONG | fixed 4xATR + 1/3 at each ext (intraday) | 254 | 5 | 162 | 87 | +96.9 | +92.5 | +77.0 | +20.4 | +17.1 | +14.7 | 92 | -0.8 | +15.7 | +14.4 | -1.6 | -2.7 | +30.0 | no edge vs bench |
| Grok crypto LONG | fixed 4xATR + Elliott w3/w5 target (intraday) | 254 | 5 | 63 | 186 | +30.7 | +24.8 | +71.4 | +19.7 | +31.0 | +28.0 | 91 | +12.3 | +29.3 | +24.9 | +11.2 | +6.9 | +42.6 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 1.272 ext full (intraday) | 254 | 15 | 224 | 15 | +96.9 | +88.2 | +80.8 | +28.0 | +9.0 | +7.4 | 93 | +1.1 | +9.0 | +7.4 | +0.5 | -0.5 | +13.2 | LUCK (edge gone w/o top tickers) |
| Grok crypto LONG | chandelier 4xATR + 1.618 ext full (intraday) | 254 | 21 | 206 | 27 | +96.9 | +81.1 | +80.6 | +25.0 | +12.3 | +10.7 | 89 | +3.2 | +10.9 | +9.8 | +2.2 | +0.9 | +15.9 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 2.618 ext full (intraday) | 254 | 25 | 170 | 59 | +96.9 | +66.9 | +76.5 | +15.5 | +21.5 | +19.0 | 85 | +5.7 | +19.4 | +17.3 | +4.5 | +2.6 | +24.8 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 1/3 at each ext (intraday) | 254 | 30 | 143 | 81 | +96.9 | +88.2 | +78.1 | +21.4 | +14.8 | +13.0 | 85 | -1.0 | +13.3 | +12.2 | -1.8 | -2.8 | +27.5 | no edge vs bench |
| Grok crypto LONG | chandelier 4xATR + Elliott w3/w5 target (intraday) | 254 | 37 | 55 | 162 | +30.7 | +21.7 | +74.5 | +19.7 | +25.8 | +22.0 | 83 | +9.7 | +23.0 | +19.1 | +8.0 | +4.3 | +38.3 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 1/3 at 1.618, rest chandelier (intraday) | 254 | 45 | 0 | 209 | +96.9 | +81.1 | +81.1 | +11.1 | +23.6 | +23.0 | 84 | +5.2 | +21.7 | +18.4 | +3.6 | +1.0 | +46.3 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + 1/2 at 1.618, rest chandelier (intraday) | 254 | 45 | 0 | 209 | +96.9 | +81.1 | +81.1 | +14.6 | +20.7 | +19.7 | 86 | +2.4 | +19.2 | +15.8 | +1.1 | -1.0 | +46.3 | LUCK (edge gone w/o top tickers) |
| All stock LONG | hold, no stop | 228 | 0 | 0 | 228 | +nan | +nan | +nan | +nan | +3.7 | +0.5 | 56 | +2.2 | +3.0 | +2.0 | +1.4 | +0.5 | +19.2 | robust to top-3 removal |
| All stock LONG | fixed 3xATR, no target (close) | 228 | 28 | 0 | 200 | +nan | +nan | +nan | +nan | +4.0 | +0.4 | 55 | +2.6 | +3.2 | +2.3 | +1.9 | +0.9 | +17.5 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR, no target (close) | 228 | 36 | 0 | 192 | +nan | +nan | +nan | +nan | +3.7 | +0.4 | 55 | +2.4 | +3.0 | +2.0 | +1.7 | +0.7 | +17.2 | robust to top-3 removal |
| All stock LONG | fixed 4xATR + 1.272 ext full (close) | 228 | 17 | 74 | 137 | +98.7 | +32.5 | +41.9 | +1.9 | +3.3 | +1.3 | 60 | +2.1 | +2.8 | +2.1 | +1.7 | +1.0 | +14.1 | robust to top-3 removal |
| All stock LONG | fixed 4xATR + 1.618 ext full (close) | 228 | 18 | 47 | 163 | +98.7 | +20.6 | +57.4 | +2.3 | +3.4 | +1.0 | 59 | +2.2 | +3.0 | +2.3 | +1.8 | +1.1 | +15.3 | robust to top-3 removal |
| All stock LONG | fixed 4xATR + 2.618 ext full (close) | 228 | 18 | 16 | 194 | +98.7 | +7.0 | +43.8 | +4.7 | +3.6 | +0.5 | 57 | +2.2 | +3.1 | +2.1 | +1.7 | +0.7 | +17.5 | robust to top-3 removal |
| All stock LONG | fixed 4xATR + 1/3 at each ext (close) | 228 | 18 | 10 | 200 | +98.7 | +32.5 | +39.2 | +1.3 | +3.5 | +0.7 | 58 | +2.0 | +3.0 | +2.2 | +1.6 | +0.8 | +17.9 | robust to top-3 removal |
| All stock LONG | fixed 4xATR + Elliott w3/w5 target (close) | 228 | 18 | 17 | 193 | +31.1 | +7.5 | +47.1 | +0.6 | +3.9 | +0.6 | 57 | +2.5 | +3.1 | +2.2 | +1.8 | +0.9 | +17.7 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 1.272 ext full (close) | 228 | 28 | 73 | 127 | +98.7 | +32.0 | +42.5 | +2.0 | +2.9 | +1.1 | 59 | +1.8 | +2.5 | +1.8 | +1.4 | +0.7 | +13.5 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 1.618 ext full (close) | 228 | 29 | 46 | 153 | +98.7 | +20.2 | +58.7 | +2.5 | +3.2 | +0.6 | 58 | +2.0 | +2.7 | +2.0 | +1.6 | +0.9 | +14.6 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 2.618 ext full (close) | 228 | 35 | 16 | 177 | +98.7 | +7.0 | +43.8 | +4.7 | +3.3 | +0.4 | 55 | +2.0 | +2.8 | +1.8 | +1.6 | +0.6 | +16.4 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 1/3 at each ext (close) | 228 | 35 | 10 | 183 | +98.7 | +32.0 | +41.1 | +1.3 | +3.2 | +0.6 | 56 | +1.9 | +2.7 | +1.9 | +1.4 | +0.6 | +16.8 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + Elliott w3/w5 target (close) | 228 | 35 | 17 | 176 | +31.1 | +7.5 | +47.1 | +0.6 | +3.8 | +0.5 | 57 | +2.5 | +3.0 | +2.1 | +1.8 | +0.9 | +16.5 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 1/3 at 1.618, rest chandelier (close) | 228 | 36 | 0 | 192 | +98.7 | +20.2 | +60.9 | +0.6 | +3.5 | +0.5 | 55 | +2.2 | +3.0 | +2.1 | +1.7 | +0.8 | +17.2 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 1/2 at 1.618, rest chandelier (close) | 228 | 36 | 0 | 192 | +98.7 | +20.2 | +60.9 | +1.1 | +3.4 | +0.6 | 57 | +2.1 | +3.0 | +2.1 | +1.7 | +0.8 | +17.2 | robust to top-3 removal |
| All stock LONG | fixed 3xATR, no target (intraday) | 228 | 31 | 0 | 197 | +nan | +nan | +nan | +nan | +4.0 | +0.4 | 55 | +2.7 | +3.3 | +2.3 | +2.0 | +1.0 | +17.1 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR, no target (intraday) | 228 | 40 | 0 | 188 | +nan | +nan | +nan | +nan | +3.8 | +0.4 | 55 | +2.6 | +3.1 | +2.1 | +1.8 | +0.9 | +16.9 | robust to top-3 removal |
| All stock LONG | fixed 4xATR + 1.272 ext full (intraday) | 228 | 21 | 94 | 113 | +98.7 | +41.2 | +52.1 | +1.6 | +3.2 | +1.3 | 64 | +2.2 | +2.8 | +2.2 | +1.8 | +1.3 | +12.5 | robust to top-3 removal |
| All stock LONG | fixed 4xATR + 1.618 ext full (intraday) | 228 | 21 | 61 | 146 | +98.7 | +26.8 | +45.9 | -1.2 | +4.2 | +1.2 | 62 | +3.0 | +3.7 | +3.0 | +2.6 | +1.9 | +14.2 | robust to top-3 removal |
| All stock LONG | fixed 4xATR + 2.618 ext full (intraday) | 228 | 23 | 24 | 181 | +98.7 | +10.5 | +29.2 | +1.7 | +3.7 | +0.6 | 58 | +2.4 | +3.2 | +2.3 | +1.9 | +1.0 | +16.6 | robust to top-3 removal |
| All stock LONG | fixed 4xATR + 1/3 at each ext (intraday) | 228 | 23 | 14 | 191 | +98.7 | +41.2 | +45.7 | +0.6 | +3.6 | +1.1 | 60 | +2.3 | +3.2 | +2.4 | +1.9 | +1.1 | +17.4 | robust to top-3 removal |
| All stock LONG | fixed 4xATR + Elliott w3/w5 target (intraday) | 228 | 23 | 17 | 188 | +31.1 | +7.5 | +52.9 | +1.5 | +3.8 | +0.6 | 57 | +2.5 | +3.1 | +2.1 | +1.7 | +0.8 | +17.0 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 1.272 ext full (intraday) | 228 | 29 | 94 | 105 | +98.7 | +41.2 | +52.1 | +1.6 | +3.0 | +1.2 | 62 | +2.0 | +2.6 | +2.0 | +1.7 | +1.1 | +12.2 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 1.618 ext full (intraday) | 228 | 31 | 60 | 137 | +98.7 | +26.3 | +46.7 | -1.2 | +3.9 | +1.0 | 60 | +2.8 | +3.4 | +2.6 | +2.4 | +1.6 | +13.8 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 2.618 ext full (intraday) | 228 | 37 | 24 | 167 | +98.7 | +10.5 | +29.2 | +1.7 | +3.6 | +0.5 | 57 | +2.4 | +3.1 | +2.2 | +1.9 | +1.0 | +15.8 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 1/3 at each ext (intraday) | 228 | 39 | 14 | 175 | +98.7 | +41.2 | +47.9 | +0.6 | +3.4 | +0.8 | 58 | +2.2 | +3.0 | +2.2 | +1.8 | +1.0 | +16.4 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + Elliott w3/w5 target (intraday) | 228 | 38 | 19 | 171 | +31.1 | +8.3 | +47.4 | +0.7 | +3.9 | +0.6 | 57 | +2.7 | +3.1 | +2.2 | +2.0 | +1.1 | +16.0 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 1/3 at 1.618, rest chandelier (intraday) | 228 | 40 | 0 | 188 | +98.7 | +26.3 | +48.3 | -1.0 | +3.8 | +0.5 | 55 | +2.6 | +3.3 | +2.4 | +2.1 | +1.2 | +16.9 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + 1/2 at 1.618, rest chandelier (intraday) | 228 | 40 | 0 | 188 | +98.7 | +26.3 | +48.3 | -1.0 | +3.8 | +0.6 | 57 | +2.6 | +3.4 | +2.5 | +2.2 | +1.3 | +16.9 | robust to top-3 removal |
| Rule-filtered stock LONG | hold, no stop | 115 | 0 | 0 | 115 | +nan | +nan | +nan | +nan | +5.0 | +1.1 | 63 | +3.5 | +3.6 | +1.9 | +2.1 | +0.3 | +19.8 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 3xATR, no target (close) | 115 | 12 | 0 | 103 | +nan | +nan | +nan | +nan | +5.5 | +1.1 | 63 | +4.1 | +4.1 | +2.3 | +2.7 | +0.9 | +17.9 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR, no target (close) | 115 | 19 | 0 | 96 | +nan | +nan | +nan | +nan | +5.3 | +0.6 | 60 | +4.0 | +3.9 | +2.2 | +2.6 | +0.8 | +17.7 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 4xATR + 1.272 ext full (close) | 115 | 10 | 48 | 57 | +98.3 | +41.7 | +41.7 | +3.2 | +4.0 | +2.0 | 67 | +3.0 | +3.3 | +2.3 | +2.3 | +1.3 | +14.5 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 4xATR + 1.618 ext full (close) | 115 | 10 | 32 | 73 | +98.3 | +27.8 | +53.1 | +3.8 | +4.3 | +1.8 | 66 | +3.2 | +3.7 | +2.6 | +2.6 | +1.5 | +15.6 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 4xATR + 2.618 ext full (close) | 115 | 10 | 12 | 93 | +98.3 | +10.4 | +50.0 | +8.2 | +4.5 | +1.4 | 64 | +3.1 | +3.7 | +2.4 | +2.3 | +1.1 | +17.5 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 4xATR + 1/3 at each ext (close) | 115 | 10 | 8 | 97 | +98.3 | +41.7 | +37.5 | +2.3 | +4.4 | +1.8 | 63 | +3.0 | +3.7 | +2.6 | +2.4 | +1.3 | +17.9 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 4xATR + Elliott w3/w5 target (close) | 115 | 10 | 14 | 91 | +40.9 | +12.2 | +50.0 | +1.1 | +5.2 | +1.4 | 64 | +3.9 | +3.8 | +2.0 | +2.5 | +0.7 | +17.6 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 1.272 ext full (close) | 115 | 15 | 48 | 52 | +98.3 | +41.7 | +41.7 | +3.2 | +3.8 | +2.0 | 64 | +2.9 | +3.1 | +2.1 | +2.2 | +1.2 | +13.9 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 1.618 ext full (close) | 115 | 15 | 32 | 68 | +98.3 | +27.8 | +53.1 | +3.8 | +4.1 | +1.5 | 63 | +3.1 | +3.6 | +2.4 | +2.5 | +1.4 | +15.0 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 2.618 ext full (close) | 115 | 18 | 12 | 85 | +98.3 | +10.4 | +50.0 | +8.2 | +4.3 | +1.0 | 61 | +3.1 | +3.5 | +2.3 | +2.3 | +1.1 | +16.5 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 1/3 at each ext (close) | 115 | 18 | 8 | 89 | +98.3 | +41.7 | +39.6 | +2.3 | +4.2 | +1.4 | 61 | +3.0 | +3.6 | +2.5 | +2.3 | +1.2 | +17.0 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + Elliott w3/w5 target (close) | 115 | 18 | 14 | 83 | +40.9 | +12.2 | +50.0 | +1.1 | +5.3 | +1.3 | 63 | +4.2 | +3.9 | +2.2 | +2.8 | +1.0 | +16.7 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 1/3 at 1.618, rest chandelier (close) | 115 | 19 | 0 | 96 | +98.3 | +27.8 | +56.2 | +0.9 | +4.9 | +1.0 | 60 | +3.6 | +3.9 | +2.5 | +2.6 | +1.2 | +17.7 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 1/2 at 1.618, rest chandelier (close) | 115 | 19 | 0 | 96 | +98.3 | +27.8 | +56.2 | +1.6 | +4.7 | +1.0 | 61 | +3.4 | +3.9 | +2.6 | +2.6 | +1.3 | +17.7 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 3xATR, no target (intraday) | 115 | 14 | 0 | 101 | +nan | +nan | +nan | +nan | +5.5 | +1.1 | 63 | +4.2 | +4.1 | +2.4 | +2.8 | +1.0 | +17.4 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR, no target (intraday) | 115 | 21 | 0 | 94 | +nan | +nan | +nan | +nan | +5.5 | +0.6 | 60 | +4.3 | +4.1 | +2.3 | +2.8 | +1.1 | +17.4 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 4xATR + 1.272 ext full (intraday) | 115 | 12 | 59 | 44 | +98.3 | +51.3 | +52.5 | +3.6 | +3.4 | +1.9 | 70 | +2.5 | +3.0 | +2.1 | +2.0 | +1.1 | +12.4 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 4xATR + 1.618 ext full (intraday) | 115 | 12 | 40 | 63 | +98.3 | +34.8 | +45.0 | +1.1 | +4.9 | +2.0 | 68 | +3.9 | +4.3 | +3.0 | +3.2 | +1.9 | +14.4 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 4xATR + 2.618 ext full (intraday) | 115 | 12 | 14 | 89 | +98.3 | +12.2 | +42.9 | +8.4 | +4.2 | +1.8 | 64 | +3.0 | +3.6 | +2.4 | +2.3 | +1.1 | +16.6 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 4xATR + 1/3 at each ext (intraday) | 115 | 12 | 9 | 94 | +98.3 | +51.3 | +45.8 | +2.2 | +4.2 | +1.8 | 65 | +2.8 | +3.6 | +2.6 | +2.3 | +1.2 | +17.1 | robust to top-3 removal |
| Rule-filtered stock LONG | fixed 4xATR + Elliott w3/w5 target (intraday) | 115 | 12 | 14 | 89 | +40.9 | +12.2 | +57.1 | +1.9 | +5.0 | +1.8 | 63 | +3.8 | +3.6 | +1.9 | +2.4 | +0.6 | +16.6 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 1.272 ext full (intraday) | 115 | 17 | 59 | 39 | +98.3 | +51.3 | +52.5 | +3.6 | +3.4 | +1.9 | 67 | +2.6 | +2.9 | +2.1 | +2.1 | +1.2 | +12.2 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 1.618 ext full (intraday) | 115 | 17 | 40 | 58 | +98.3 | +34.8 | +45.0 | +1.1 | +4.9 | +2.0 | 65 | +3.9 | +4.2 | +3.0 | +3.3 | +2.0 | +14.2 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 2.618 ext full (intraday) | 115 | 20 | 14 | 81 | +98.3 | +12.2 | +42.9 | +8.4 | +4.3 | +1.0 | 61 | +3.2 | +3.7 | +2.5 | +2.5 | +1.4 | +16.1 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 1/3 at each ext (intraday) | 115 | 20 | 9 | 86 | +98.3 | +51.3 | +47.5 | +2.1 | +4.2 | +1.5 | 62 | +3.0 | +3.6 | +2.6 | +2.4 | +1.4 | +16.5 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + Elliott w3/w5 target (intraday) | 115 | 20 | 16 | 79 | +40.9 | +13.9 | +50.0 | +0.8 | +5.5 | +1.1 | 63 | +4.5 | +4.1 | +2.4 | +3.1 | +1.3 | +16.0 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 1/3 at 1.618, rest chandelier (intraday) | 115 | 21 | 0 | 94 | +98.3 | +34.8 | +47.5 | -0.1 | +5.3 | +1.5 | 60 | +4.1 | +4.3 | +3.0 | +3.1 | +1.7 | +17.4 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + 1/2 at 1.618, rest chandelier (intraday) | 115 | 21 | 0 | 94 | +98.3 | +34.8 | +47.5 | +0.2 | +5.2 | +1.6 | 60 | +4.0 | +4.4 | +3.1 | +3.2 | +1.9 | +17.4 | robust to top-3 removal |
| Perplexity stock LONG | hold, no stop | 57 | 0 | 0 | 57 | +nan | +nan | +nan | +nan | +6.7 | +1.7 | 61 | +5.8 | +3.8 | +1.2 | +2.9 | +0.3 | +23.2 | robust to top-3 removal |
| Perplexity stock LONG | fixed 3xATR, no target (close) | 57 | 10 | 0 | 47 | +nan | +nan | +nan | +nan | +7.1 | +1.2 | 58 | +6.6 | +4.2 | +1.7 | +3.7 | +1.2 | +20.6 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR, no target (close) | 57 | 15 | 0 | 42 | +nan | +nan | +nan | +nan | +6.4 | +0.6 | 54 | +5.9 | +3.5 | +0.9 | +3.1 | +0.4 | +20.2 | robust to top-3 removal |
| Perplexity stock LONG | fixed 4xATR + 1.272 ext full (close) | 57 | 7 | 16 | 34 | +98.2 | +28.1 | +43.8 | +10.0 | +4.2 | +1.8 | 61 | +3.7 | +3.1 | +1.8 | +2.6 | +1.2 | +18.7 | robust to top-3 removal |
| Perplexity stock LONG | fixed 4xATR + 1.618 ext full (close) | 57 | 7 | 10 | 40 | +98.2 | +17.5 | +70.0 | +15.2 | +4.4 | +1.7 | 61 | +3.9 | +3.2 | +2.0 | +2.7 | +1.4 | +19.3 | robust to top-3 removal |
| Perplexity stock LONG | fixed 4xATR + 2.618 ext full (close) | 57 | 7 | 6 | 44 | +98.2 | +10.5 | +83.3 | +19.8 | +4.9 | +1.7 | 61 | +4.3 | +3.4 | +1.8 | +2.7 | +1.1 | +20.7 | robust to top-3 removal |
| Perplexity stock LONG | fixed 4xATR + 1/3 at each ext (close) | 57 | 7 | 6 | 44 | +98.2 | +28.1 | +43.8 | +9.0 | +4.5 | +1.8 | 61 | +3.9 | +3.2 | +2.0 | +2.6 | +1.3 | +20.7 | robust to top-3 removal |
| Perplexity stock LONG | fixed 4xATR + Elliott w3/w5 target (close) | 57 | 7 | 4 | 46 | +29.8 | +7.0 | +75.0 | +2.8 | +6.8 | +1.7 | 61 | +6.2 | +4.0 | +1.4 | +3.4 | +0.8 | +20.6 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 1.272 ext full (close) | 57 | 13 | 15 | 29 | +98.2 | +26.3 | +46.7 | +11.0 | +3.7 | +0.8 | 56 | +3.3 | +2.5 | +1.2 | +2.2 | +0.8 | +17.8 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 1.618 ext full (close) | 57 | 13 | 9 | 35 | +98.2 | +15.8 | +77.8 | +17.4 | +3.8 | +0.8 | 56 | +3.5 | +2.7 | +1.4 | +2.3 | +1.0 | +18.3 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 2.618 ext full (close) | 57 | 15 | 6 | 36 | +98.2 | +10.5 | +83.3 | +19.8 | +4.3 | +0.6 | 54 | +3.9 | +2.7 | +1.1 | +2.3 | +0.6 | +19.2 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 1/3 at each ext (close) | 57 | 15 | 6 | 36 | +98.2 | +26.3 | +53.3 | +10.1 | +3.9 | +0.8 | 56 | +3.6 | +2.6 | +1.4 | +2.2 | +0.9 | +19.2 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + Elliott w3/w5 target (close) | 57 | 14 | 4 | 39 | +29.8 | +7.0 | +75.0 | +2.8 | +6.5 | +0.8 | 56 | +6.1 | +3.7 | +1.1 | +3.2 | +0.6 | +19.5 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 1/3 at 1.618, rest chandelier (close) | 57 | 15 | 0 | 42 | +98.2 | +15.8 | +88.9 | +6.7 | +5.5 | +0.6 | 54 | +5.1 | +3.5 | +1.1 | +3.0 | +0.6 | +20.2 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 1/2 at 1.618, rest chandelier (close) | 57 | 15 | 0 | 42 | +98.2 | +15.8 | +88.9 | +9.4 | +5.1 | +0.6 | 54 | +4.7 | +3.5 | +1.2 | +3.0 | +0.7 | +20.2 | robust to top-3 removal |
| Perplexity stock LONG | fixed 3xATR, no target (intraday) | 57 | 11 | 0 | 46 | +nan | +nan | +nan | +nan | +7.1 | +1.2 | 58 | +6.6 | +4.2 | +1.7 | +3.7 | +1.2 | +20.2 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR, no target (intraday) | 57 | 17 | 0 | 40 | +nan | +nan | +nan | +nan | +6.5 | +0.6 | 54 | +6.1 | +3.6 | +1.0 | +3.3 | +0.6 | +19.7 | robust to top-3 removal |
| Perplexity stock LONG | fixed 4xATR + 1.272 ext full (intraday) | 57 | 8 | 20 | 29 | +98.2 | +35.1 | +75.0 | +10.0 | +3.6 | +1.8 | 63 | +3.3 | +2.9 | +1.7 | +2.5 | +1.2 | +16.9 | robust to top-3 removal |
| Perplexity stock LONG | fixed 4xATR + 1.618 ext full (intraday) | 57 | 8 | 11 | 38 | +98.2 | +19.3 | +63.6 | +12.7 | +4.7 | +1.8 | 63 | +4.2 | +3.7 | +2.4 | +3.1 | +1.9 | +19.0 | robust to top-3 removal |
| Perplexity stock LONG | fixed 4xATR + 2.618 ext full (intraday) | 57 | 8 | 6 | 43 | +98.2 | +10.5 | +83.3 | +24.2 | +4.6 | +1.7 | 61 | +4.1 | +3.3 | +1.9 | +2.7 | +1.2 | +20.5 | robust to top-3 removal |
| Perplexity stock LONG | fixed 4xATR + 1/3 at each ext (intraday) | 57 | 8 | 6 | 43 | +98.2 | +35.1 | +70.0 | +8.1 | +4.3 | +1.8 | 63 | +3.8 | +3.3 | +2.1 | +2.7 | +1.4 | +20.5 | robust to top-3 removal |
| Perplexity stock LONG | fixed 4xATR + Elliott w3/w5 target (intraday) | 57 | 8 | 4 | 45 | +29.8 | +7.0 | +75.0 | +4.1 | +6.9 | +1.7 | 61 | +6.3 | +4.0 | +1.5 | +3.5 | +0.9 | +20.0 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 1.272 ext full (intraday) | 57 | 14 | 20 | 23 | +98.2 | +35.1 | +75.0 | +10.0 | +3.5 | +1.2 | 58 | +3.3 | +2.8 | +1.5 | +2.6 | +1.3 | +15.7 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 1.618 ext full (intraday) | 57 | 15 | 10 | 32 | +98.2 | +17.5 | +70.0 | +14.1 | +4.2 | +1.1 | 58 | +3.9 | +3.1 | +1.8 | +2.8 | +1.6 | +17.7 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 2.618 ext full (intraday) | 57 | 17 | 6 | 34 | +98.2 | +10.5 | +83.3 | +24.2 | +3.9 | +0.6 | 54 | +3.7 | +2.6 | +1.1 | +2.3 | +0.8 | +18.6 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 1/3 at each ext (intraday) | 57 | 17 | 6 | 34 | +98.2 | +35.1 | +75.0 | +8.9 | +3.8 | +1.1 | 56 | +3.6 | +2.8 | +1.6 | +2.6 | +1.2 | +18.6 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + Elliott w3/w5 target (intraday) | 57 | 16 | 4 | 37 | +29.8 | +7.0 | +75.0 | +4.1 | +6.5 | +0.9 | 56 | +6.2 | +3.6 | +1.0 | +3.3 | +0.7 | +18.5 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 1/3 at 1.618, rest chandelier (intraday) | 57 | 17 | 0 | 40 | +98.2 | +17.5 | +80.0 | +5.4 | +5.7 | +0.6 | 54 | +5.4 | +3.7 | +1.3 | +3.3 | +1.0 | +19.7 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + 1/2 at 1.618, rest chandelier (intraday) | 57 | 17 | 0 | 40 | +98.2 | +17.5 | +80.0 | +7.6 | +5.3 | +0.9 | 56 | +5.0 | +3.7 | +1.5 | +3.4 | +1.1 | +19.7 | robust to top-3 removal |
| Grok stock LONG | hold, no stop | 131 | 0 | 0 | 131 | +nan | +nan | +nan | +nan | +2.0 | +0.3 | 54 | +0.2 | +1.2 | +0.4 | -0.6 | -1.5 | +17.4 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 3xATR, no target (close) | 131 | 16 | 0 | 115 | +nan | +nan | +nan | +nan | +2.2 | +0.3 | 54 | +0.6 | +1.5 | +0.7 | -0.1 | -1.0 | +16.0 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR, no target (close) | 131 | 18 | 0 | 113 | +nan | +nan | +nan | +nan | +2.3 | +0.4 | 55 | +0.7 | +1.5 | +0.7 | -0.1 | -0.9 | +15.7 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 4xATR + 1.272 ext full (close) | 131 | 9 | 46 | 76 | +98.5 | +35.1 | +41.3 | -1.1 | +2.5 | +1.3 | 60 | +1.1 | +2.2 | +1.5 | +0.8 | +0.1 | +12.1 | robust to top-3 removal |
| Grok stock LONG | fixed 4xATR + 1.618 ext full (close) | 131 | 10 | 30 | 91 | +98.5 | +22.9 | +50.0 | -2.1 | +2.6 | +0.6 | 59 | +1.1 | +2.1 | +1.3 | +0.6 | -0.2 | +13.6 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 4xATR + 2.618 ext full (close) | 131 | 10 | 8 | 113 | +98.5 | +6.1 | +12.5 | -5.8 | +2.5 | +0.4 | 56 | +0.8 | +1.9 | +1.1 | +0.2 | -0.6 | +16.1 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 4xATR + 1/3 at each ext (close) | 131 | 10 | 3 | 118 | +98.5 | +35.1 | +37.0 | -1.4 | +2.6 | +0.6 | 56 | +0.9 | +2.2 | +1.5 | +0.5 | -0.3 | +16.5 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 4xATR + Elliott w3/w5 target (close) | 131 | 10 | 10 | 111 | +33.6 | +7.6 | +40.0 | -0.1 | +2.1 | +0.4 | 56 | +0.5 | +1.4 | +0.6 | -0.2 | -1.1 | +16.1 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + 1.272 ext full (close) | 131 | 13 | 46 | 72 | +98.5 | +35.1 | +41.3 | -1.1 | +2.2 | +1.3 | 60 | +1.0 | +1.9 | +1.2 | +0.6 | -0.1 | +11.6 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + 1.618 ext full (close) | 131 | 14 | 30 | 87 | +98.5 | +22.9 | +50.0 | -2.1 | +2.5 | +0.6 | 59 | +1.1 | +2.0 | +1.2 | +0.6 | -0.2 | +13.0 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + 2.618 ext full (close) | 131 | 17 | 8 | 106 | +98.5 | +6.1 | +12.5 | -5.8 | +2.5 | +0.4 | 56 | +0.9 | +1.9 | +1.1 | +0.4 | -0.5 | +15.1 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + 1/3 at each ext (close) | 131 | 17 | 3 | 111 | +98.5 | +35.1 | +37.0 | -1.8 | +2.5 | +0.6 | 56 | +0.9 | +2.1 | +1.3 | +0.5 | -0.3 | +15.5 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + Elliott w3/w5 target (close) | 131 | 18 | 10 | 103 | +33.6 | +7.6 | +40.0 | -0.1 | +2.3 | +0.4 | 56 | +0.8 | +1.5 | +0.7 | +0.1 | -0.8 | +14.9 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + 1/3 at 1.618, rest chandelier (close) | 131 | 18 | 0 | 113 | +98.5 | +22.9 | +50.0 | -1.4 | +2.3 | +0.4 | 56 | +0.7 | +1.8 | +1.1 | +0.2 | -0.5 | +15.7 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + 1/2 at 1.618, rest chandelier (close) | 131 | 18 | 0 | 113 | +98.5 | +22.9 | +50.0 | -1.6 | +2.4 | +0.5 | 57 | +0.8 | +2.0 | +1.3 | +0.4 | -0.3 | +15.7 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 3xATR, no target (intraday) | 131 | 18 | 0 | 113 | +nan | +nan | +nan | +nan | +2.3 | +0.3 | 54 | +0.8 | +1.6 | +0.8 | +0.0 | -0.8 | +15.6 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR, no target (intraday) | 131 | 20 | 0 | 111 | +nan | +nan | +nan | +nan | +2.4 | +0.4 | 55 | +0.8 | +1.7 | +0.9 | +0.1 | -0.7 | +15.4 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 4xATR + 1.272 ext full (intraday) | 131 | 11 | 58 | 62 | +98.5 | +44.3 | +43.1 | -1.5 | +2.7 | +1.2 | 66 | +1.5 | +2.3 | +1.7 | +1.1 | +0.5 | +10.6 | robust to top-3 removal |
| Grok stock LONG | fixed 4xATR + 1.618 ext full (intraday) | 131 | 11 | 38 | 82 | +98.5 | +29.0 | +42.1 | -5.7 | +3.7 | +1.0 | 63 | +2.4 | +3.1 | +2.3 | +1.8 | +1.0 | +12.3 | robust to top-3 removal |
| Grok stock LONG | fixed 4xATR + 2.618 ext full (intraday) | 131 | 13 | 14 | 104 | +98.5 | +10.7 | +7.1 | -6.6 | +2.8 | +0.4 | 57 | +1.2 | +2.4 | +1.6 | +0.8 | -0.0 | +15.1 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | fixed 4xATR + 1/3 at each ext (intraday) | 131 | 13 | 6 | 112 | +98.5 | +44.3 | +37.9 | -1.9 | +2.9 | +0.7 | 60 | +1.3 | +2.6 | +1.9 | +0.9 | +0.2 | +15.9 | robust to top-3 removal |
| Grok stock LONG | fixed 4xATR + Elliott w3/w5 target (intraday) | 131 | 13 | 10 | 108 | +33.6 | +7.6 | +50.0 | +0.7 | +2.0 | +0.4 | 55 | +0.5 | +1.3 | +0.5 | -0.2 | -1.1 | +15.5 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + 1.272 ext full (intraday) | 131 | 13 | 58 | 60 | +98.5 | +44.3 | +43.1 | -1.5 | +2.6 | +1.2 | 65 | +1.4 | +2.1 | +1.5 | +0.9 | +0.3 | +10.4 | robust to top-3 removal |
| Grok stock LONG | chandelier 4xATR + 1.618 ext full (intraday) | 131 | 14 | 38 | 79 | +98.5 | +29.0 | +42.1 | -5.7 | +3.5 | +1.0 | 62 | +2.2 | +2.9 | +2.1 | +1.6 | +0.8 | +12.1 | robust to top-3 removal |
| Grok stock LONG | chandelier 4xATR + 2.618 ext full (intraday) | 131 | 18 | 14 | 99 | +98.5 | +10.7 | +7.1 | -6.6 | +3.0 | +0.4 | 57 | +1.5 | +2.6 | +1.8 | +1.1 | +0.3 | +14.6 | robust to top-3 removal |
| Grok stock LONG | chandelier 4xATR + 1/3 at each ext (intraday) | 131 | 19 | 6 | 106 | +98.5 | +44.3 | +39.7 | -2.2 | +2.8 | +0.7 | 59 | +1.3 | +2.5 | +1.8 | +0.9 | +0.2 | +15.2 | robust to top-3 removal |
| Grok stock LONG | chandelier 4xATR + Elliott w3/w5 target (intraday) | 131 | 19 | 11 | 101 | +33.6 | +8.4 | +45.5 | +0.0 | +2.4 | +0.4 | 57 | +1.0 | +1.7 | +0.9 | +0.3 | -0.6 | +14.6 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + 1/3 at 1.618, rest chandelier (intraday) | 131 | 20 | 0 | 111 | +98.5 | +29.0 | +42.1 | -3.2 | +2.8 | +0.4 | 56 | +1.2 | +2.3 | +1.5 | +0.7 | -0.0 | +15.4 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + 1/2 at 1.618, rest chandelier (intraday) | 131 | 20 | 0 | 111 | +98.5 | +29.0 | +42.1 | -3.8 | +2.9 | +0.5 | 56 | +1.4 | +2.6 | +1.8 | +1.0 | +0.3 | +15.4 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | hold, no stop | 60 | 0 | 0 | 60 | +nan | +nan | +nan | +nan | +3.6 | +6.3 | 73 | +4.8 | +3.4 | +2.7 | +4.6 | +3.9 | +19.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 3xATR, no target (close) | 60 | 4 | 0 | 56 | +nan | +nan | +nan | +nan | +4.3 | +6.3 | 73 | +5.4 | +4.1 | +3.4 | +5.2 | +4.5 | +18.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR, no target (close) | 60 | 4 | 0 | 56 | +nan | +nan | +nan | +nan | +4.5 | +6.3 | 73 | +5.6 | +4.3 | +3.6 | +5.4 | +4.7 | +17.9 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 4xATR + 1.272 ext full (close) | 60 | 2 | 27 | 31 | +80.0 | +45.0 | +70.4 | +0.3 | +3.5 | +3.2 | 80 | +3.9 | +3.3 | +2.9 | +3.6 | +3.2 | +11.3 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 4xATR + 1.618 ext full (close) | 60 | 2 | 22 | 36 | +80.0 | +36.7 | +72.7 | -0.6 | +3.9 | +3.9 | 78 | +4.4 | +3.7 | +3.2 | +4.2 | +3.7 | +12.8 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 4xATR + 2.618 ext full (close) | 60 | 2 | 11 | 47 | +80.0 | +18.3 | +45.5 | -5.1 | +4.6 | +6.3 | 78 | +5.5 | +4.4 | +3.7 | +5.3 | +4.6 | +16.2 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 4xATR + 1/3 at each ext (close) | 60 | 4 | 3 | 53 | +80.0 | +45.0 | +70.4 | +0.1 | +3.6 | +4.7 | 73 | +4.6 | +3.4 | +2.8 | +4.4 | +3.8 | +17.3 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 4xATR + Elliott w3/w5 target (close) | 60 | 2 | 11 | 47 | +41.7 | +18.3 | +81.8 | -1.8 | +4.3 | +4.5 | 77 | +5.2 | +4.1 | +3.4 | +5.0 | +4.3 | +14.7 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 1.272 ext full (close) | 60 | 2 | 27 | 31 | +80.0 | +45.0 | +70.4 | +0.3 | +3.6 | +3.2 | 80 | +4.0 | +3.4 | +2.9 | +3.7 | +3.2 | +11.2 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 1.618 ext full (close) | 60 | 2 | 22 | 36 | +80.0 | +36.7 | +72.7 | -0.6 | +3.9 | +3.9 | 78 | +4.5 | +3.7 | +3.2 | +4.3 | +3.8 | +12.8 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 2.618 ext full (close) | 60 | 2 | 11 | 47 | +80.0 | +18.3 | +45.5 | -5.1 | +4.7 | +6.3 | 78 | +5.6 | +4.5 | +3.7 | +5.4 | +4.7 | +16.1 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 1/3 at each ext (close) | 60 | 4 | 3 | 53 | +80.0 | +45.0 | +70.4 | -0.3 | +3.8 | +4.7 | 73 | +4.9 | +3.6 | +3.1 | +4.7 | +4.1 | +17.1 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + Elliott w3/w5 target (close) | 60 | 2 | 11 | 47 | +41.7 | +18.3 | +81.8 | -1.8 | +4.4 | +4.5 | 77 | +5.3 | +4.3 | +3.6 | +5.1 | +4.5 | +14.6 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 1/3 at 1.618, rest chandelier (close) | 60 | 4 | 0 | 56 | +80.0 | +36.7 | +72.7 | -1.5 | +4.3 | +5.9 | 73 | +5.4 | +4.1 | +3.4 | +5.2 | +4.5 | +17.9 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 1/2 at 1.618, rest chandelier (close) | 60 | 4 | 0 | 56 | +80.0 | +36.7 | +72.7 | -1.3 | +4.2 | +5.5 | 75 | +5.3 | +4.0 | +3.3 | +5.1 | +4.4 | +17.9 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 3xATR, no target (intraday) | 60 | 4 | 0 | 56 | +nan | +nan | +nan | +nan | +4.5 | +6.3 | 73 | +5.6 | +4.4 | +3.7 | +5.5 | +4.8 | +17.6 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR, no target (intraday) | 60 | 5 | 0 | 55 | +nan | +nan | +nan | +nan | +4.4 | +6.3 | 73 | +5.5 | +4.2 | +3.6 | +5.3 | +4.6 | +17.4 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 4xATR + 1.272 ext full (intraday) | 60 | 2 | 30 | 28 | +80.0 | +50.0 | +66.7 | +0.5 | +3.5 | +3.0 | 82 | +3.8 | +3.3 | +2.8 | +3.6 | +3.1 | +9.8 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 4xATR + 1.618 ext full (intraday) | 60 | 2 | 24 | 34 | +80.0 | +40.0 | +75.0 | -0.2 | +3.8 | +3.5 | 80 | +4.3 | +3.6 | +3.2 | +4.1 | +3.6 | +11.3 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 4xATR + 2.618 ext full (intraday) | 60 | 2 | 14 | 44 | +80.0 | +23.3 | +42.9 | -3.5 | +4.6 | +6.2 | 78 | +5.4 | +4.4 | +3.7 | +5.2 | +4.5 | +15.0 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 4xATR + 1/3 at each ext (intraday) | 60 | 4 | 5 | 51 | +80.0 | +50.0 | +66.7 | +0.3 | +3.6 | +4.7 | 75 | +4.6 | +3.4 | +2.9 | +4.4 | +3.8 | +16.6 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | fixed 4xATR + Elliott w3/w5 target (intraday) | 60 | 2 | 14 | 44 | +41.7 | +23.3 | +64.3 | -1.6 | +4.4 | +4.3 | 77 | +5.3 | +4.2 | +3.5 | +5.1 | +4.4 | +14.2 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 1.272 ext full (intraday) | 60 | 2 | 30 | 28 | +80.0 | +50.0 | +66.7 | +0.5 | +3.6 | +3.0 | 82 | +3.9 | +3.4 | +3.0 | +3.7 | +3.2 | +9.8 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 1.618 ext full (intraday) | 60 | 2 | 24 | 34 | +80.0 | +40.0 | +75.0 | -0.2 | +4.0 | +3.5 | 80 | +4.4 | +3.8 | +3.4 | +4.2 | +3.7 | +11.3 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 2.618 ext full (intraday) | 60 | 3 | 14 | 43 | +80.0 | +23.3 | +42.9 | -3.5 | +4.4 | +6.2 | 78 | +5.2 | +4.2 | +3.5 | +5.0 | +4.2 | +14.5 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 1/3 at each ext (intraday) | 60 | 5 | 5 | 50 | +80.0 | +50.0 | +70.0 | +0.3 | +3.7 | +4.7 | 73 | +4.7 | +3.5 | +3.0 | +4.5 | +3.9 | +15.9 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + Elliott w3/w5 target (intraday) | 60 | 3 | 14 | 43 | +41.7 | +23.3 | +64.3 | -1.6 | +4.3 | +4.3 | 77 | +5.1 | +4.1 | +3.4 | +4.9 | +4.2 | +13.6 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 1/3 at 1.618, rest chandelier (intraday) | 60 | 5 | 0 | 55 | +80.0 | +40.0 | +79.2 | -1.0 | +4.3 | +5.9 | 73 | +5.3 | +4.1 | +3.4 | +5.2 | +4.5 | +17.4 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + 1/2 at 1.618, rest chandelier (intraday) | 60 | 5 | 0 | 55 | +80.0 | +40.0 | +79.2 | -0.8 | +4.2 | +5.4 | 75 | +5.3 | +4.0 | +3.3 | +5.1 | +4.4 | +17.4 | robust to top-3 removal |
| All stock SHORT | hold, no stop | 173 | 0 | 0 | 173 | +nan | +nan | +nan | +nan | -0.9 | -1.2 | 46 | +0.5 | -1.2 | -1.5 | +0.2 | -0.1 | +16.8 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fixed 3xATR, no target (close) | 173 | 32 | 0 | 141 | +nan | +nan | +nan | +nan | -0.5 | -1.2 | 46 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | +15.2 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR, no target (close) | 173 | 27 | 0 | 146 | +nan | +nan | +nan | +nan | -0.5 | -1.2 | 46 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | +15.5 | robust to top-3 removal |
| All stock SHORT | fixed 4xATR + 1.272 ext full (close) | 173 | 19 | 38 | 116 | +93.1 | +22.0 | +63.2 | -0.5 | -0.8 | +0.2 | 50 | +0.1 | -1.0 | -1.3 | -0.1 | -0.4 | +11.7 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fixed 4xATR + 1.618 ext full (close) | 173 | 19 | 29 | 125 | +93.1 | +16.8 | +69.0 | -1.7 | -0.6 | -0.7 | 48 | +0.4 | -0.9 | -1.2 | +0.2 | -0.1 | +12.7 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fixed 4xATR + 2.618 ext full (close) | 173 | 19 | 14 | 140 | +93.1 | +8.1 | +50.0 | -3.7 | -0.6 | -0.7 | 47 | +0.6 | -0.9 | -1.2 | +0.3 | +0.0 | +14.7 | robust to top-3 removal |
| All stock SHORT | fixed 4xATR + 1/3 at each ext (close) | 173 | 21 | 3 | 149 | +93.1 | +22.0 | +63.2 | -0.0 | -0.9 | -0.9 | 46 | +0.4 | -1.2 | -1.5 | +0.2 | -0.1 | +15.4 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fixed 4xATR + Elliott w3/w5 target (close) | 173 | 19 | 11 | 143 | +25.4 | +6.4 | +81.8 | -1.8 | -0.7 | -0.9 | 47 | +0.6 | -1.0 | -1.3 | +0.3 | -0.0 | +14.5 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | chandelier 4xATR + 1.272 ext full (close) | 173 | 24 | 38 | 111 | +93.1 | +22.0 | +63.2 | -0.5 | -0.8 | +0.2 | 50 | +0.2 | -0.9 | -1.2 | -0.0 | -0.3 | +11.6 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | chandelier 4xATR + 1.618 ext full (close) | 173 | 24 | 29 | 120 | +93.1 | +16.8 | +69.0 | -1.7 | -0.6 | -0.5 | 48 | +0.5 | -0.8 | -1.1 | +0.2 | -0.1 | +12.6 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | chandelier 4xATR + 2.618 ext full (close) | 173 | 25 | 14 | 134 | +93.1 | +8.1 | +50.0 | -3.7 | -0.5 | -0.7 | 47 | +0.8 | -0.8 | -1.1 | +0.5 | +0.1 | +14.5 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + 1/3 at each ext (close) | 173 | 27 | 3 | 143 | +93.1 | +22.0 | +63.2 | -0.6 | -0.7 | -0.9 | 46 | +0.6 | -1.0 | -1.3 | +0.3 | +0.0 | +15.2 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + Elliott w3/w5 target (close) | 173 | 25 | 11 | 137 | +25.4 | +6.4 | +81.8 | -1.8 | -0.5 | -0.9 | 47 | +0.7 | -0.8 | -1.1 | +0.4 | +0.1 | +14.3 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + 1/3 at 1.618, rest chandelier (close) | 173 | 27 | 0 | 146 | +93.1 | +16.8 | +69.0 | -2.0 | -0.5 | -1.2 | 46 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | +15.5 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + 1/2 at 1.618, rest chandelier (close) | 173 | 27 | 0 | 146 | +93.1 | +16.8 | +69.0 | -1.9 | -0.5 | -0.9 | 47 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | +15.5 | robust to top-3 removal |
| All stock SHORT | fixed 3xATR, no target (intraday) | 173 | 36 | 0 | 137 | +nan | +nan | +nan | +nan | -0.1 | -1.2 | 46 | +1.2 | -0.4 | -0.7 | +0.9 | +0.6 | +14.8 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR, no target (intraday) | 173 | 35 | 0 | 138 | +nan | +nan | +nan | +nan | -0.3 | -1.2 | 46 | +1.1 | -0.6 | -0.9 | +0.8 | +0.5 | +14.9 | robust to top-3 removal |
| All stock SHORT | fixed 4xATR + 1.272 ext full (intraday) | 173 | 21 | 44 | 108 | +93.1 | +25.4 | +59.1 | -0.3 | -0.6 | +0.5 | 52 | +0.3 | -0.8 | -1.1 | +0.1 | -0.2 | +10.8 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | fixed 4xATR + 1.618 ext full (intraday) | 173 | 21 | 36 | 116 | +93.1 | +20.8 | +61.1 | -1.4 | -0.4 | +0.6 | 51 | +0.5 | -0.6 | -0.9 | +0.3 | +0.0 | +11.7 | robust to top-3 removal |
| All stock SHORT | fixed 4xATR + 2.618 ext full (intraday) | 173 | 21 | 19 | 133 | +93.1 | +11.0 | +42.1 | -3.0 | -0.4 | -0.7 | 47 | +0.9 | -0.7 | -1.0 | +0.5 | +0.2 | +14.2 | robust to top-3 removal |
| All stock SHORT | fixed 4xATR + 1/3 at each ext (intraday) | 173 | 23 | 6 | 144 | +93.1 | +25.4 | +56.8 | -0.1 | -0.7 | -0.4 | 47 | +0.6 | -0.9 | -1.2 | +0.4 | +0.1 | +15.1 | robust to top-3 removal |
| All stock SHORT | fixed 4xATR + Elliott w3/w5 target (intraday) | 173 | 21 | 14 | 138 | +25.4 | +8.1 | +64.3 | -1.6 | -0.5 | -0.9 | 47 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | +14.3 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + 1.272 ext full (intraday) | 173 | 25 | 44 | 104 | +93.1 | +25.4 | +59.1 | -0.3 | -0.4 | +0.5 | 53 | +0.4 | -0.6 | -0.9 | +0.2 | -0.1 | +10.6 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | chandelier 4xATR + 1.618 ext full (intraday) | 173 | 26 | 36 | 111 | +93.1 | +20.8 | +61.1 | -1.4 | -0.2 | +0.6 | 51 | +0.7 | -0.4 | -0.7 | +0.5 | +0.2 | +11.4 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + 2.618 ext full (intraday) | 173 | 33 | 19 | 121 | +93.1 | +11.0 | +42.1 | -3.0 | -0.2 | -0.7 | 48 | +1.0 | -0.5 | -0.9 | +0.7 | +0.3 | +13.6 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + 1/3 at each ext (intraday) | 173 | 35 | 6 | 132 | +93.1 | +25.4 | +61.4 | -0.4 | -0.4 | -0.5 | 47 | +0.8 | -0.7 | -1.0 | +0.6 | +0.3 | +14.4 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + Elliott w3/w5 target (intraday) | 173 | 33 | 14 | 126 | +25.4 | +8.1 | +64.3 | -1.6 | -0.3 | -0.9 | 47 | +0.9 | -0.6 | -0.9 | +0.6 | +0.3 | +13.6 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + 1/3 at 1.618, rest chandelier (intraday) | 173 | 35 | 0 | 138 | +93.1 | +20.8 | +66.7 | -1.3 | -0.2 | -0.9 | 46 | +1.1 | -0.5 | -0.8 | +0.8 | +0.5 | +14.9 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + 1/2 at 1.618, rest chandelier (intraday) | 173 | 35 | 0 | 138 | +93.1 | +20.8 | +66.7 | -1.4 | -0.2 | -0.7 | 48 | +1.1 | -0.5 | -0.8 | +0.8 | +0.5 | +14.9 | robust to top-3 removal |

### M. Ratchet / floor / tighten-after-profit chandelier (stop_rules.ChandelierStop; same setups as K/L; R = 4xATR14 at entry except fixed 3xATR where R = 3xATR; hold uses nominal R = 4xATR; maxDD_R = max peak-to-trough of the cumulative R of the equal-weight trade sequence in signal (entry-date) order, same order for every policy; reachX = % of trades whose max favourable close while held reached X R; ever45 = % whose best close to 2026-10-07 reached 4.5R regardless of exit; n_tight = trades where the tighten rule fired)
| segment | policy | N | exited | open_ | stopped | mean | median | hit | x_mkt | mean_wo_top1 | mean_wo_top3 | x_mkt_wo_top1 | x_mkt_wo_top3 | R_med_pct | mean_R | med_R | avg_win_R | avg_loss_R | maxDD_R | reach2 | reach3 | reach45 | ever45 | n_tight | days | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Grok crypto LONG | hold, no stop | 254 | 0 | 254 | 0 | +36.8 | +32.0 | 93 | +14.8 | +36.2 | +30.7 | +14.0 | +8.6 | 13.9 | +2.54 | +2.65 | +2.76 | -0.22 | 3.6 | 70 | 62 | 26 | 26 | 0 | 53 | robust to top-3 removal |
| Grok crypto LONG | fixed 3xATR (crypto live) (close) | 254 | 15 | 239 | 6 | +33.1 | +31.1 | 87 | +12.6 | +31.6 | +26.8 | +11.3 | +6.5 | 10.5 | +3.13 | +3.49 | +3.72 | -0.65 | 4.7 | 70 | 65 | 50 | 52 | 0 | 50 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR, no ratchet (close) | 254 | 19 | 235 | 7 | +32.7 | +30.3 | 85 | +12.8 | +31.1 | +26.2 | +11.6 | +6.8 | 13.9 | +2.32 | +2.62 | +2.80 | -0.44 | 3.6 | 65 | 58 | 24 | 26 | 0 | 49 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + floor at initial stop (close) | 254 | 20 | 234 | 8 | +32.6 | +30.3 | 85 | +12.8 | +31.1 | +26.1 | +11.6 | +6.8 | 13.9 | +2.31 | +2.62 | +2.82 | -0.45 | 3.6 | 65 | 58 | 24 | 26 | 0 | 49 | robust to top-3 removal |
| Grok crypto LONG | RATCHET chandelier 4xATR (close) | 254 | 39 | 215 | 15 | +30.3 | +29.5 | 85 | +11.3 | +28.2 | +23.2 | +9.8 | +5.0 | 13.9 | +2.14 | +2.40 | +2.61 | -0.44 | 3.6 | 64 | 56 | 19 | 26 | 0 | 47 | robust to top-3 removal |
| Grok crypto LONG | ratchet + tighten to 2xATR after 2R (close) | 254 | 176 | 78 | 69 | +24.0 | +21.5 | 85 | +8.5 | +22.3 | +19.7 | +6.9 | +4.2 | 13.9 | +1.67 | +1.89 | +2.06 | -0.44 | 3.6 | 64 | 43 | 6 | 26 | 162 | 35 | robust to top-3 removal |
| Grok crypto LONG | ratchet + tighten to 3xATR after 2R (close) | 254 | 60 | 194 | 24 | +29.7 | +28.5 | 85 | +11.1 | +27.5 | +22.4 | +9.5 | +4.7 | 13.9 | +2.10 | +2.35 | +2.56 | -0.44 | 3.6 | 64 | 55 | 18 | 26 | 162 | 46 | robust to top-3 removal |
| Grok crypto LONG | ratchet + tighten to 2xATR after 3R (close) | 254 | 138 | 116 | 54 | +26.3 | +27.4 | 85 | +9.2 | +26.1 | +22.1 | +8.9 | +4.8 | 13.9 | +1.84 | +2.35 | +2.25 | -0.44 | 3.6 | 64 | 56 | 6 | 26 | 143 | 39 | robust to top-3 removal |
| Grok crypto LONG | ratchet + tighten to 3xATR after 3R (close) | 254 | 55 | 199 | 22 | +30.1 | +28.6 | 85 | +11.4 | +28.0 | +22.9 | +9.9 | +5.0 | 13.9 | +2.12 | +2.40 | +2.58 | -0.44 | 3.6 | 64 | 56 | 19 | 26 | 143 | 47 | robust to top-3 removal |
| Grok crypto LONG | ratchet + tighten to 2xATR after 4.5R (close) | 254 | 53 | 201 | 21 | +29.7 | +29.5 | 85 | +10.9 | +27.5 | +23.3 | +9.3 | +5.1 | 13.9 | +2.11 | +2.41 | +2.57 | -0.44 | 3.6 | 64 | 56 | 19 | 26 | 47 | 47 | robust to top-3 removal |
| Grok crypto LONG | ratchet + tighten to 3xATR after 4.5R (close) | 254 | 47 | 207 | 19 | +30.3 | +29.5 | 85 | +11.4 | +28.2 | +23.2 | +9.8 | +5.0 | 13.9 | +2.14 | +2.41 | +2.61 | -0.44 | 3.6 | 64 | 56 | 19 | 26 | 47 | 47 | robust to top-3 removal |
| Grok crypto LONG | fixed 3xATR (crypto live) (intraday) | 254 | 19 | 235 | 7 | +32.5 | +30.9 | 85 | +12.4 | +31.0 | +26.0 | +11.1 | +6.3 | 10.5 | +3.08 | +3.48 | +3.74 | -0.66 | 4.7 | 69 | 65 | 49 | 52 | 0 | 49 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR, no ratchet (intraday) | 254 | 45 | 209 | 18 | +29.2 | +28.5 | 82 | +10.9 | +26.9 | +21.8 | +9.2 | +4.4 | 13.9 | +2.05 | +2.33 | +2.59 | -0.43 | 3.6 | 62 | 54 | 18 | 26 | 0 | 46 | robust to top-3 removal |
| Grok crypto LONG | chandelier 4xATR + floor at initial stop (intraday) | 254 | 47 | 207 | 19 | +29.0 | +28.5 | 81 | +10.7 | +26.6 | +21.5 | +9.1 | +4.2 | 13.9 | +2.04 | +2.33 | +2.61 | -0.46 | 3.6 | 62 | 54 | 18 | 26 | 0 | 46 | robust to top-3 removal |
| Grok crypto LONG | RATCHET chandelier 4xATR (intraday) | 254 | 46 | 208 | 18 | +29.2 | +28.5 | 83 | +10.9 | +26.9 | +21.8 | +9.3 | +4.4 | 13.9 | +2.06 | +2.33 | +2.57 | -0.45 | 3.6 | 62 | 54 | 18 | 26 | 0 | 46 | robust to top-3 removal |
| Grok crypto LONG | ratchet + tighten to 2xATR after 2R (intraday) | 254 | 180 | 74 | 71 | +23.0 | +19.9 | 83 | +7.9 | +21.2 | +18.7 | +6.3 | +3.8 | 13.9 | +1.59 | +1.78 | +2.01 | -0.45 | 3.6 | 62 | 37 | 5 | 26 | 157 | 33 | robust to top-3 removal |
| Grok crypto LONG | ratchet + tighten to 3xATR after 2R (intraday) | 254 | 122 | 132 | 48 | +24.8 | +18.9 | 83 | +9.4 | +22.3 | +20.3 | +7.2 | +4.7 | 13.9 | +1.66 | +1.66 | +2.09 | -0.45 | 3.6 | 62 | 44 | 8 | 26 | 157 | 40 | robust to top-3 removal |
| Grok crypto LONG | ratchet + tighten to 2xATR after 3R (intraday) | 254 | 142 | 112 | 56 | +25.3 | +27.0 | 83 | +8.7 | +24.9 | +21.2 | +8.2 | +4.4 | 13.9 | +1.77 | +2.36 | +2.22 | -0.45 | 3.6 | 62 | 54 | 6 | 26 | 137 | 38 | robust to top-3 removal |
| Grok crypto LONG | ratchet + tighten to 3xATR after 3R (intraday) | 254 | 90 | 164 | 35 | +26.6 | +26.6 | 83 | +9.8 | +24.1 | +21.9 | +7.5 | +4.9 | 13.9 | +1.81 | +2.19 | +2.27 | -0.45 | 3.6 | 62 | 54 | 8 | 26 | 137 | 43 | robust to top-3 removal |
| Grok crypto LONG | ratchet + tighten to 2xATR after 4.5R (intraday) | 254 | 65 | 189 | 26 | +28.5 | +28.5 | 83 | +10.3 | +26.0 | +22.0 | +8.5 | +4.6 | 13.9 | +2.02 | +2.33 | +2.52 | -0.45 | 3.6 | 62 | 54 | 18 | 26 | 46 | 45 | robust to top-3 removal |
| Grok crypto LONG | ratchet + tighten to 3xATR after 4.5R (intraday) | 254 | 54 | 200 | 21 | +29.3 | +28.5 | 83 | +11.0 | +27.0 | +22.0 | +9.4 | +4.6 | 13.9 | +2.06 | +2.33 | +2.57 | -0.45 | 3.6 | 62 | 54 | 18 | 26 | 46 | 46 | robust to top-3 removal |
| All stock LONG | hold, no stop | 228 | 0 | 228 | 0 | +3.7 | +0.5 | 56 | +2.2 | +3.0 | +2.0 | +1.4 | +0.5 | 16.8 | +0.14 | +0.04 | +0.63 | -0.49 | 6.2 | 4 | 1 | 1 | 1 | 0 | 19 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR, no ratchet (close) | 228 | 36 | 192 | 16 | +3.7 | +0.4 | 55 | +2.4 | +3.0 | +2.0 | +1.7 | +0.7 | 16.8 | +0.15 | +0.03 | +0.64 | -0.44 | 5.8 | 4 | 1 | 1 | 1 | 0 | 17 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + floor at initial stop (close) | 228 | 37 | 191 | 16 | +3.7 | +0.4 | 55 | +2.4 | +3.0 | +2.0 | +1.7 | +0.7 | 16.8 | +0.15 | +0.03 | +0.64 | -0.44 | 5.6 | 4 | 1 | 1 | 1 | 0 | 17 | robust to top-3 removal |
| All stock LONG | RATCHET chandelier 4xATR (close) | 228 | 38 | 190 | 17 | +3.7 | +0.4 | 55 | +2.4 | +3.0 | +2.0 | +1.7 | +0.7 | 16.8 | +0.15 | +0.03 | +0.64 | -0.44 | 5.6 | 4 | 1 | 1 | 1 | 0 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 2xATR after 2R (close) | 228 | 41 | 187 | 18 | +3.8 | +0.4 | 55 | +2.6 | +3.1 | +2.1 | +1.8 | +0.9 | 16.8 | +0.16 | +0.03 | +0.65 | -0.44 | 5.7 | 4 | 1 | 1 | 1 | 8 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 3xATR after 2R (close) | 228 | 38 | 190 | 17 | +3.8 | +0.4 | 55 | +2.5 | +3.1 | +2.1 | +1.8 | +0.8 | 16.8 | +0.15 | +0.03 | +0.64 | -0.44 | 5.6 | 4 | 1 | 1 | 1 | 8 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 2xATR after 3R (close) | 228 | 39 | 189 | 17 | +3.7 | +0.4 | 55 | +2.4 | +3.0 | +2.0 | +1.7 | +0.7 | 16.8 | +0.15 | +0.03 | +0.64 | -0.44 | 5.6 | 4 | 1 | 1 | 1 | 3 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 3xATR after 3R (close) | 228 | 38 | 190 | 17 | +3.7 | +0.4 | 55 | +2.4 | +3.0 | +2.0 | +1.7 | +0.7 | 16.8 | +0.15 | +0.03 | +0.64 | -0.44 | 5.6 | 4 | 1 | 1 | 1 | 3 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 2xATR after 4.5R (close) | 228 | 39 | 189 | 17 | +3.7 | +0.4 | 55 | +2.4 | +3.0 | +2.0 | +1.7 | +0.7 | 16.8 | +0.15 | +0.03 | +0.64 | -0.44 | 5.6 | 4 | 1 | 1 | 1 | 3 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 3xATR after 4.5R (close) | 228 | 38 | 190 | 17 | +3.7 | +0.4 | 55 | +2.4 | +3.0 | +2.0 | +1.7 | +0.7 | 16.8 | +0.15 | +0.03 | +0.64 | -0.44 | 5.6 | 4 | 1 | 1 | 1 | 3 | 17 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR, no ratchet + 1/2 at 1.618 (close) | 228 | 36 | 192 | 16 | +3.4 | +0.6 | 57 | +2.1 | +3.0 | +2.1 | +1.7 | +0.8 | 16.8 | +0.12 | +0.05 | +0.55 | -0.44 | 6.1 | 4 | 1 | 1 | 1 | 0 | 17 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + floor at initial stop + 1/2 at 1.618 (close) | 228 | 37 | 191 | 16 | +3.4 | +0.6 | 57 | +2.1 | +3.0 | +2.1 | +1.7 | +0.9 | 16.8 | +0.13 | +0.05 | +0.55 | -0.43 | 6.0 | 4 | 1 | 1 | 1 | 0 | 17 | robust to top-3 removal |
| All stock LONG | RATCHET chandelier 4xATR + 1/2 at 1.618 (close) | 228 | 38 | 190 | 17 | +3.4 | +0.6 | 57 | +2.1 | +3.0 | +2.1 | +1.7 | +0.8 | 16.8 | +0.12 | +0.05 | +0.55 | -0.44 | 6.0 | 4 | 1 | 1 | 1 | 0 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 2xATR after 2R + 1/2 at 1.618 (close) | 228 | 41 | 187 | 18 | +3.5 | +0.6 | 57 | +2.2 | +3.0 | +2.2 | +1.8 | +0.9 | 16.8 | +0.13 | +0.05 | +0.56 | -0.44 | 6.1 | 4 | 1 | 1 | 1 | 8 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 3xATR after 2R + 1/2 at 1.618 (close) | 228 | 38 | 190 | 17 | +3.5 | +0.6 | 57 | +2.2 | +3.0 | +2.2 | +1.7 | +0.9 | 16.8 | +0.13 | +0.05 | +0.56 | -0.44 | 6.0 | 4 | 1 | 1 | 1 | 8 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 2xATR after 3R + 1/2 at 1.618 (close) | 228 | 39 | 189 | 17 | +3.4 | +0.6 | 57 | +2.1 | +3.0 | +2.1 | +1.7 | +0.8 | 16.8 | +0.12 | +0.05 | +0.55 | -0.44 | 6.0 | 4 | 1 | 1 | 1 | 3 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 3xATR after 3R + 1/2 at 1.618 (close) | 228 | 38 | 190 | 17 | +3.4 | +0.6 | 57 | +2.1 | +3.0 | +2.1 | +1.7 | +0.8 | 16.8 | +0.12 | +0.05 | +0.55 | -0.44 | 6.0 | 4 | 1 | 1 | 1 | 3 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 2xATR after 4.5R + 1/2 at 1.618 (close) | 228 | 39 | 189 | 17 | +3.4 | +0.6 | 57 | +2.1 | +3.0 | +2.1 | +1.7 | +0.8 | 16.8 | +0.12 | +0.05 | +0.55 | -0.44 | 6.0 | 4 | 1 | 1 | 1 | 3 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 3xATR after 4.5R + 1/2 at 1.618 (close) | 228 | 38 | 190 | 17 | +3.4 | +0.6 | 57 | +2.1 | +3.0 | +2.1 | +1.7 | +0.8 | 16.8 | +0.12 | +0.05 | +0.55 | -0.44 | 6.0 | 4 | 1 | 1 | 1 | 3 | 17 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR, no ratchet (intraday) | 228 | 40 | 188 | 18 | +3.8 | +0.4 | 55 | +2.6 | +3.1 | +2.1 | +1.8 | +0.9 | 16.8 | +0.16 | +0.03 | +0.64 | -0.43 | 5.8 | 4 | 1 | 1 | 1 | 0 | 17 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + floor at initial stop (intraday) | 228 | 43 | 185 | 19 | +3.8 | +0.4 | 55 | +2.5 | +3.0 | +2.1 | +1.8 | +0.8 | 16.8 | +0.16 | +0.03 | +0.64 | -0.43 | 5.8 | 4 | 1 | 1 | 1 | 0 | 16 | robust to top-3 removal |
| All stock LONG | RATCHET chandelier 4xATR (intraday) | 228 | 42 | 186 | 18 | +3.9 | +0.4 | 55 | +2.6 | +3.1 | +2.2 | +1.9 | +0.9 | 16.8 | +0.16 | +0.03 | +0.64 | -0.42 | 5.6 | 4 | 1 | 1 | 1 | 0 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 2xATR after 2R (intraday) | 228 | 45 | 183 | 20 | +4.0 | +0.4 | 55 | +2.7 | +3.3 | +2.3 | +2.0 | +1.1 | 16.8 | +0.17 | +0.03 | +0.65 | -0.42 | 5.6 | 4 | 1 | 1 | 1 | 8 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 3xATR after 2R (intraday) | 228 | 43 | 185 | 19 | +3.9 | +0.4 | 55 | +2.6 | +3.1 | +2.2 | +1.9 | +0.9 | 16.8 | +0.16 | +0.03 | +0.64 | -0.42 | 5.6 | 4 | 1 | 1 | 1 | 8 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 2xATR after 3R (intraday) | 228 | 43 | 185 | 19 | +3.9 | +0.4 | 55 | +2.6 | +3.1 | +2.2 | +1.9 | +0.9 | 16.8 | +0.16 | +0.03 | +0.64 | -0.42 | 5.6 | 4 | 1 | 1 | 1 | 3 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 3xATR after 3R (intraday) | 228 | 43 | 185 | 19 | +3.8 | +0.4 | 55 | +2.6 | +3.1 | +2.1 | +1.8 | +0.9 | 16.8 | +0.16 | +0.03 | +0.64 | -0.42 | 5.6 | 4 | 1 | 1 | 1 | 3 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 2xATR after 4.5R (intraday) | 228 | 43 | 185 | 19 | +3.9 | +0.4 | 55 | +2.6 | +3.1 | +2.2 | +1.9 | +0.9 | 16.8 | +0.16 | +0.03 | +0.64 | -0.42 | 5.6 | 4 | 1 | 1 | 1 | 3 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 3xATR after 4.5R (intraday) | 228 | 43 | 185 | 19 | +3.8 | +0.4 | 55 | +2.6 | +3.1 | +2.1 | +1.8 | +0.9 | 16.8 | +0.16 | +0.03 | +0.64 | -0.42 | 5.6 | 4 | 1 | 1 | 1 | 3 | 17 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR, no ratchet + 1/2 at 1.618 (intraday) | 228 | 40 | 188 | 18 | +3.8 | +0.6 | 57 | +2.6 | +3.4 | +2.5 | +2.2 | +1.3 | 16.8 | +0.14 | +0.06 | +0.56 | -0.40 | 6.0 | 4 | 1 | 1 | 1 | 0 | 17 | robust to top-3 removal |
| All stock LONG | chandelier 4xATR + floor at initial stop + 1/2 at 1.618 (intraday) | 228 | 43 | 185 | 19 | +3.8 | +0.6 | 57 | +2.6 | +3.3 | +2.5 | +2.1 | +1.3 | 16.8 | +0.14 | +0.06 | +0.56 | -0.40 | 6.0 | 4 | 1 | 1 | 1 | 0 | 16 | robust to top-3 removal |
| All stock LONG | RATCHET chandelier 4xATR + 1/2 at 1.618 (intraday) | 228 | 42 | 186 | 18 | +3.9 | +0.6 | 57 | +2.6 | +3.4 | +2.6 | +2.2 | +1.4 | 16.8 | +0.15 | +0.06 | +0.56 | -0.40 | 5.7 | 4 | 1 | 1 | 1 | 0 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 2xATR after 2R + 1/2 at 1.618 (intraday) | 228 | 45 | 183 | 20 | +3.9 | +0.6 | 57 | +2.7 | +3.5 | +2.6 | +2.3 | +1.4 | 16.8 | +0.15 | +0.06 | +0.57 | -0.40 | 5.7 | 4 | 1 | 1 | 1 | 8 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 3xATR after 2R + 1/2 at 1.618 (intraday) | 228 | 43 | 185 | 19 | +3.9 | +0.6 | 57 | +2.6 | +3.4 | +2.6 | +2.2 | +1.4 | 16.8 | +0.15 | +0.06 | +0.56 | -0.40 | 5.7 | 4 | 1 | 1 | 1 | 8 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 2xATR after 3R + 1/2 at 1.618 (intraday) | 228 | 43 | 185 | 19 | +3.9 | +0.6 | 57 | +2.6 | +3.4 | +2.6 | +2.2 | +1.4 | 16.8 | +0.15 | +0.06 | +0.56 | -0.40 | 5.7 | 4 | 1 | 1 | 1 | 3 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 3xATR after 3R + 1/2 at 1.618 (intraday) | 228 | 43 | 185 | 19 | +3.9 | +0.6 | 57 | +2.6 | +3.4 | +2.5 | +2.2 | +1.3 | 16.8 | +0.15 | +0.06 | +0.56 | -0.40 | 5.7 | 4 | 1 | 1 | 1 | 3 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 2xATR after 4.5R + 1/2 at 1.618 (intraday) | 228 | 43 | 185 | 19 | +3.9 | +0.6 | 57 | +2.6 | +3.4 | +2.6 | +2.2 | +1.4 | 16.8 | +0.15 | +0.06 | +0.56 | -0.40 | 5.7 | 4 | 1 | 1 | 1 | 3 | 17 | robust to top-3 removal |
| All stock LONG | ratchet + tighten to 3xATR after 4.5R + 1/2 at 1.618 (intraday) | 228 | 43 | 185 | 19 | +3.9 | +0.6 | 57 | +2.6 | +3.4 | +2.5 | +2.2 | +1.3 | 16.8 | +0.15 | +0.06 | +0.56 | -0.40 | 5.7 | 4 | 1 | 1 | 1 | 3 | 17 | robust to top-3 removal |
| Rule-filtered stock LONG | hold, no stop | 115 | 0 | 115 | 0 | +5.0 | +1.1 | 63 | +3.5 | +3.6 | +1.9 | +2.1 | +0.3 | 17.3 | +0.21 | +0.07 | +0.68 | -0.57 | 6.6 | 6 | 3 | 3 | 3 | 0 | 20 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR, no ratchet (close) | 115 | 19 | 96 | 17 | +5.3 | +0.6 | 60 | +4.0 | +3.9 | +2.2 | +2.6 | +0.8 | 17.3 | +0.25 | +0.05 | +0.72 | -0.46 | 3.3 | 6 | 3 | 3 | 3 | 0 | 18 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + floor at initial stop (close) | 115 | 20 | 95 | 17 | +5.3 | +0.6 | 60 | +4.1 | +3.9 | +2.2 | +2.6 | +0.9 | 17.3 | +0.25 | +0.05 | +0.72 | -0.46 | 3.3 | 6 | 3 | 3 | 3 | 0 | 18 | robust to top-3 removal |
| Rule-filtered stock LONG | RATCHET chandelier 4xATR (close) | 115 | 20 | 95 | 17 | +5.3 | +0.6 | 60 | +4.1 | +3.9 | +2.2 | +2.6 | +0.9 | 17.3 | +0.25 | +0.05 | +0.72 | -0.46 | 3.3 | 6 | 3 | 3 | 3 | 0 | 18 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 2xATR after 2R (close) | 115 | 23 | 92 | 20 | +5.6 | +0.6 | 60 | +4.3 | +4.2 | +2.4 | +2.9 | +1.2 | 17.3 | +0.26 | +0.05 | +0.74 | -0.46 | 3.3 | 6 | 3 | 3 | 3 | 7 | 17 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 3xATR after 2R (close) | 115 | 20 | 95 | 17 | +5.5 | +0.6 | 60 | +4.2 | +4.0 | +2.3 | +2.8 | +1.0 | 17.3 | +0.26 | +0.05 | +0.73 | -0.46 | 3.3 | 6 | 3 | 3 | 3 | 7 | 18 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 2xATR after 3R (close) | 115 | 21 | 94 | 18 | +5.3 | +0.6 | 60 | +4.1 | +3.9 | +2.2 | +2.6 | +0.9 | 17.3 | +0.25 | +0.05 | +0.72 | -0.46 | 3.3 | 6 | 3 | 3 | 3 | 3 | 18 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 3xATR after 3R (close) | 115 | 20 | 95 | 17 | +5.3 | +0.6 | 60 | +4.1 | +3.9 | +2.2 | +2.6 | +0.9 | 17.3 | +0.25 | +0.05 | +0.72 | -0.46 | 3.3 | 6 | 3 | 3 | 3 | 3 | 18 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 2xATR after 4.5R (close) | 115 | 21 | 94 | 18 | +5.3 | +0.6 | 60 | +4.1 | +3.9 | +2.2 | +2.6 | +0.9 | 17.3 | +0.25 | +0.05 | +0.72 | -0.46 | 3.3 | 6 | 3 | 3 | 3 | 3 | 18 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 3xATR after 4.5R (close) | 115 | 20 | 95 | 17 | +5.3 | +0.6 | 60 | +4.1 | +3.9 | +2.2 | +2.6 | +0.9 | 17.3 | +0.25 | +0.05 | +0.72 | -0.46 | 3.3 | 6 | 3 | 3 | 3 | 3 | 18 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR, no ratchet + 1/2 at 1.618 (close) | 115 | 19 | 96 | 17 | +4.7 | +1.0 | 61 | +3.4 | +3.9 | +2.6 | +2.6 | +1.3 | 17.3 | +0.20 | +0.07 | +0.61 | -0.44 | 3.4 | 6 | 3 | 3 | 3 | 0 | 18 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + floor at initial stop + 1/2 at 1.618 (close) | 115 | 20 | 95 | 17 | +4.7 | +1.0 | 61 | +3.5 | +3.9 | +2.6 | +2.7 | +1.3 | 17.3 | +0.20 | +0.07 | +0.61 | -0.44 | 3.4 | 6 | 3 | 3 | 3 | 0 | 18 | robust to top-3 removal |
| Rule-filtered stock LONG | RATCHET chandelier 4xATR + 1/2 at 1.618 (close) | 115 | 20 | 95 | 17 | +4.7 | +1.0 | 61 | +3.5 | +3.9 | +2.6 | +2.7 | +1.3 | 17.3 | +0.20 | +0.07 | +0.61 | -0.44 | 3.4 | 6 | 3 | 3 | 3 | 0 | 18 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 2xATR after 2R + 1/2 at 1.618 (close) | 115 | 23 | 92 | 20 | +4.8 | +1.0 | 61 | +3.6 | +4.1 | +2.8 | +2.8 | +1.5 | 17.3 | +0.20 | +0.07 | +0.61 | -0.44 | 3.3 | 6 | 3 | 3 | 3 | 7 | 17 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 3xATR after 2R + 1/2 at 1.618 (close) | 115 | 20 | 95 | 17 | +4.8 | +1.0 | 61 | +3.5 | +4.0 | +2.7 | +2.7 | +1.4 | 17.3 | +0.20 | +0.07 | +0.61 | -0.44 | 3.4 | 6 | 3 | 3 | 3 | 7 | 18 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 2xATR after 3R + 1/2 at 1.618 (close) | 115 | 21 | 94 | 18 | +4.7 | +1.0 | 61 | +3.5 | +3.9 | +2.6 | +2.7 | +1.3 | 17.3 | +0.20 | +0.07 | +0.61 | -0.44 | 3.4 | 6 | 3 | 3 | 3 | 3 | 18 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 3xATR after 3R + 1/2 at 1.618 (close) | 115 | 20 | 95 | 17 | +4.7 | +1.0 | 61 | +3.5 | +3.9 | +2.6 | +2.7 | +1.3 | 17.3 | +0.20 | +0.07 | +0.61 | -0.44 | 3.4 | 6 | 3 | 3 | 3 | 3 | 18 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 2xATR after 4.5R + 1/2 at 1.618 (close) | 115 | 21 | 94 | 18 | +4.7 | +1.0 | 61 | +3.5 | +3.9 | +2.6 | +2.7 | +1.3 | 17.3 | +0.20 | +0.07 | +0.61 | -0.44 | 3.4 | 6 | 3 | 3 | 3 | 3 | 18 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 3xATR after 4.5R + 1/2 at 1.618 (close) | 115 | 20 | 95 | 17 | +4.7 | +1.0 | 61 | +3.5 | +3.9 | +2.6 | +2.7 | +1.3 | 17.3 | +0.20 | +0.07 | +0.61 | -0.44 | 3.4 | 6 | 3 | 3 | 3 | 3 | 18 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR, no ratchet (intraday) | 115 | 21 | 94 | 18 | +5.5 | +0.6 | 60 | +4.3 | +4.1 | +2.3 | +2.8 | +1.1 | 17.3 | +0.26 | +0.05 | +0.73 | -0.44 | 3.5 | 6 | 3 | 3 | 3 | 0 | 17 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + floor at initial stop (intraday) | 115 | 23 | 92 | 20 | +5.4 | +0.6 | 60 | +4.2 | +4.0 | +2.3 | +2.8 | +1.0 | 17.3 | +0.26 | +0.05 | +0.73 | -0.44 | 3.3 | 6 | 3 | 3 | 3 | 0 | 17 | robust to top-3 removal |
| Rule-filtered stock LONG | RATCHET chandelier 4xATR (intraday) | 115 | 22 | 93 | 19 | +5.6 | +0.6 | 60 | +4.4 | +4.2 | +2.4 | +2.9 | +1.2 | 17.3 | +0.27 | +0.05 | +0.73 | -0.42 | 3.3 | 6 | 3 | 3 | 3 | 0 | 17 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 2xATR after 2R (intraday) | 115 | 25 | 90 | 22 | +5.8 | +0.6 | 60 | +4.6 | +4.4 | +2.7 | +3.2 | +1.4 | 17.3 | +0.28 | +0.05 | +0.75 | -0.42 | 3.3 | 6 | 3 | 3 | 3 | 7 | 17 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 3xATR after 2R (intraday) | 115 | 23 | 92 | 20 | +5.6 | +0.6 | 60 | +4.4 | +4.2 | +2.5 | +3.0 | +1.3 | 17.3 | +0.27 | +0.05 | +0.73 | -0.42 | 3.3 | 6 | 3 | 3 | 3 | 7 | 17 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 2xATR after 3R (intraday) | 115 | 23 | 92 | 20 | +5.6 | +0.6 | 60 | +4.4 | +4.2 | +2.4 | +3.0 | +1.2 | 17.3 | +0.27 | +0.05 | +0.73 | -0.42 | 3.3 | 6 | 3 | 3 | 3 | 3 | 17 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 3xATR after 3R (intraday) | 115 | 23 | 92 | 20 | +5.5 | +0.6 | 60 | +4.3 | +4.1 | +2.4 | +2.9 | +1.2 | 17.3 | +0.27 | +0.05 | +0.72 | -0.42 | 3.3 | 6 | 3 | 3 | 3 | 3 | 17 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 2xATR after 4.5R (intraday) | 115 | 23 | 92 | 20 | +5.6 | +0.6 | 60 | +4.4 | +4.2 | +2.4 | +3.0 | +1.2 | 17.3 | +0.27 | +0.05 | +0.73 | -0.42 | 3.3 | 6 | 3 | 3 | 3 | 3 | 17 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 3xATR after 4.5R (intraday) | 115 | 23 | 92 | 20 | +5.5 | +0.6 | 60 | +4.3 | +4.1 | +2.4 | +2.9 | +1.2 | 17.3 | +0.27 | +0.05 | +0.72 | -0.42 | 3.3 | 6 | 3 | 3 | 3 | 3 | 17 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR, no ratchet + 1/2 at 1.618 (intraday) | 115 | 21 | 94 | 18 | +5.2 | +1.6 | 60 | +4.0 | +4.4 | +3.1 | +3.2 | +1.9 | 17.3 | +0.22 | +0.12 | +0.63 | -0.39 | 3.7 | 6 | 3 | 3 | 3 | 0 | 17 | robust to top-3 removal |
| Rule-filtered stock LONG | chandelier 4xATR + floor at initial stop + 1/2 at 1.618 (intraday) | 115 | 23 | 92 | 20 | +5.1 | +1.6 | 60 | +3.9 | +4.3 | +3.0 | +3.1 | +1.8 | 17.3 | +0.22 | +0.12 | +0.63 | -0.40 | 3.3 | 6 | 3 | 3 | 3 | 0 | 17 | robust to top-3 removal |
| Rule-filtered stock LONG | RATCHET chandelier 4xATR + 1/2 at 1.618 (intraday) | 115 | 22 | 93 | 19 | +5.2 | +1.6 | 60 | +4.0 | +4.5 | +3.2 | +3.2 | +1.9 | 17.3 | +0.23 | +0.12 | +0.63 | -0.38 | 3.3 | 6 | 3 | 3 | 3 | 0 | 17 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 2xATR after 2R + 1/2 at 1.618 (intraday) | 115 | 25 | 90 | 22 | +5.4 | +1.6 | 60 | +4.2 | +4.6 | +3.3 | +3.4 | +2.1 | 17.3 | +0.23 | +0.12 | +0.64 | -0.38 | 3.3 | 6 | 3 | 3 | 3 | 7 | 17 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 3xATR after 2R + 1/2 at 1.618 (intraday) | 115 | 23 | 92 | 20 | +5.3 | +1.6 | 60 | +4.0 | +4.5 | +3.2 | +3.2 | +1.9 | 17.3 | +0.23 | +0.12 | +0.63 | -0.38 | 3.3 | 6 | 3 | 3 | 3 | 7 | 17 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 2xATR after 3R + 1/2 at 1.618 (intraday) | 115 | 23 | 92 | 20 | +5.3 | +1.6 | 60 | +4.0 | +4.5 | +3.2 | +3.2 | +1.9 | 17.3 | +0.23 | +0.12 | +0.63 | -0.38 | 3.3 | 6 | 3 | 3 | 3 | 3 | 17 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 3xATR after 3R + 1/2 at 1.618 (intraday) | 115 | 23 | 92 | 20 | +5.2 | +1.6 | 60 | +4.0 | +4.4 | +3.1 | +3.2 | +1.9 | 17.3 | +0.22 | +0.12 | +0.63 | -0.38 | 3.3 | 6 | 3 | 3 | 3 | 3 | 17 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 2xATR after 4.5R + 1/2 at 1.618 (intraday) | 115 | 23 | 92 | 20 | +5.3 | +1.6 | 60 | +4.0 | +4.5 | +3.2 | +3.2 | +1.9 | 17.3 | +0.23 | +0.12 | +0.63 | -0.38 | 3.3 | 6 | 3 | 3 | 3 | 3 | 17 | robust to top-3 removal |
| Rule-filtered stock LONG | ratchet + tighten to 3xATR after 4.5R + 1/2 at 1.618 (intraday) | 115 | 23 | 92 | 20 | +5.2 | +1.6 | 60 | +4.0 | +4.4 | +3.1 | +3.2 | +1.9 | 17.3 | +0.22 | +0.12 | +0.63 | -0.38 | 3.3 | 6 | 3 | 3 | 3 | 3 | 17 | robust to top-3 removal |
| Perplexity stock LONG | hold, no stop | 57 | 0 | 57 | 0 | +6.7 | +1.7 | 61 | +5.8 | +3.8 | +1.2 | +2.9 | +0.3 | 16.4 | +0.29 | +0.10 | +0.93 | -0.72 | 6.0 | 7 | 4 | 4 | 4 | 0 | 23 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR, no ratchet (close) | 57 | 15 | 42 | 26 | +6.4 | +0.6 | 54 | +5.9 | +3.5 | +0.9 | +3.1 | +0.4 | 16.4 | +0.32 | +0.05 | +1.00 | -0.50 | 3.3 | 7 | 4 | 4 | 4 | 0 | 20 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + floor at initial stop (close) | 57 | 15 | 42 | 26 | +6.4 | +0.6 | 54 | +6.0 | +3.5 | +0.9 | +3.1 | +0.5 | 16.4 | +0.32 | +0.05 | +1.00 | -0.50 | 3.3 | 7 | 4 | 4 | 4 | 0 | 20 | robust to top-3 removal |
| Perplexity stock LONG | RATCHET chandelier 4xATR (close) | 57 | 15 | 42 | 26 | +6.4 | +0.6 | 54 | +6.0 | +3.5 | +0.9 | +3.1 | +0.5 | 16.4 | +0.32 | +0.05 | +1.00 | -0.50 | 3.3 | 7 | 4 | 4 | 4 | 0 | 20 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 2xATR after 2R (close) | 57 | 16 | 41 | 28 | +6.5 | +0.6 | 54 | +6.1 | +3.6 | +1.0 | +3.2 | +0.6 | 16.4 | +0.32 | +0.05 | +1.01 | -0.50 | 3.3 | 7 | 4 | 4 | 4 | 4 | 20 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 3xATR after 2R (close) | 57 | 15 | 42 | 26 | +6.4 | +0.6 | 54 | +6.0 | +3.5 | +0.9 | +3.1 | +0.5 | 16.4 | +0.32 | +0.05 | +1.00 | -0.50 | 3.3 | 7 | 4 | 4 | 4 | 4 | 20 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 2xATR after 3R (close) | 57 | 15 | 42 | 26 | +6.4 | +0.6 | 54 | +6.0 | +3.5 | +0.9 | +3.1 | +0.5 | 16.4 | +0.32 | +0.05 | +1.00 | -0.50 | 3.3 | 7 | 4 | 4 | 4 | 2 | 20 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 3xATR after 3R (close) | 57 | 15 | 42 | 26 | +6.4 | +0.6 | 54 | +6.0 | +3.5 | +0.9 | +3.1 | +0.5 | 16.4 | +0.32 | +0.05 | +1.00 | -0.50 | 3.3 | 7 | 4 | 4 | 4 | 2 | 20 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 2xATR after 4.5R (close) | 57 | 15 | 42 | 26 | +6.4 | +0.6 | 54 | +6.0 | +3.5 | +0.9 | +3.1 | +0.5 | 16.4 | +0.32 | +0.05 | +1.00 | -0.50 | 3.3 | 7 | 4 | 4 | 4 | 2 | 20 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 3xATR after 4.5R (close) | 57 | 15 | 42 | 26 | +6.4 | +0.6 | 54 | +6.0 | +3.5 | +0.9 | +3.1 | +0.5 | 16.4 | +0.32 | +0.05 | +1.00 | -0.50 | 3.3 | 7 | 4 | 4 | 4 | 2 | 20 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR, no ratchet + 1/2 at 1.618 (close) | 57 | 15 | 42 | 26 | +5.1 | +0.6 | 54 | +4.7 | +3.5 | +1.2 | +3.0 | +0.7 | 16.4 | +0.22 | +0.05 | +0.81 | -0.48 | 3.3 | 7 | 4 | 4 | 4 | 0 | 20 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + floor at initial stop + 1/2 at 1.618 (close) | 57 | 15 | 42 | 26 | +5.1 | +0.6 | 54 | +4.7 | +3.5 | +1.2 | +3.1 | +0.8 | 16.4 | +0.22 | +0.05 | +0.81 | -0.49 | 3.3 | 7 | 4 | 4 | 4 | 0 | 20 | robust to top-3 removal |
| Perplexity stock LONG | RATCHET chandelier 4xATR + 1/2 at 1.618 (close) | 57 | 15 | 42 | 26 | +5.1 | +0.6 | 54 | +4.7 | +3.5 | +1.2 | +3.1 | +0.8 | 16.4 | +0.22 | +0.05 | +0.81 | -0.49 | 3.3 | 7 | 4 | 4 | 4 | 0 | 20 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 2xATR after 2R + 1/2 at 1.618 (close) | 57 | 16 | 41 | 28 | +5.1 | +0.6 | 54 | +4.8 | +3.5 | +1.3 | +3.2 | +0.9 | 16.4 | +0.22 | +0.05 | +0.81 | -0.49 | 3.3 | 7 | 4 | 4 | 4 | 4 | 20 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 3xATR after 2R + 1/2 at 1.618 (close) | 57 | 15 | 42 | 26 | +5.1 | +0.6 | 54 | +4.7 | +3.5 | +1.2 | +3.1 | +0.8 | 16.4 | +0.22 | +0.05 | +0.81 | -0.49 | 3.3 | 7 | 4 | 4 | 4 | 4 | 20 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 2xATR after 3R + 1/2 at 1.618 (close) | 57 | 15 | 42 | 26 | +5.1 | +0.6 | 54 | +4.7 | +3.5 | +1.2 | +3.1 | +0.8 | 16.4 | +0.22 | +0.05 | +0.81 | -0.49 | 3.3 | 7 | 4 | 4 | 4 | 2 | 20 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 3xATR after 3R + 1/2 at 1.618 (close) | 57 | 15 | 42 | 26 | +5.1 | +0.6 | 54 | +4.7 | +3.5 | +1.2 | +3.1 | +0.8 | 16.4 | +0.22 | +0.05 | +0.81 | -0.49 | 3.3 | 7 | 4 | 4 | 4 | 2 | 20 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 2xATR after 4.5R + 1/2 at 1.618 (close) | 57 | 15 | 42 | 26 | +5.1 | +0.6 | 54 | +4.7 | +3.5 | +1.2 | +3.1 | +0.8 | 16.4 | +0.22 | +0.05 | +0.81 | -0.49 | 3.3 | 7 | 4 | 4 | 4 | 2 | 20 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 3xATR after 4.5R + 1/2 at 1.618 (close) | 57 | 15 | 42 | 26 | +5.1 | +0.6 | 54 | +4.7 | +3.5 | +1.2 | +3.1 | +0.8 | 16.4 | +0.22 | +0.05 | +0.81 | -0.49 | 3.3 | 7 | 4 | 4 | 4 | 2 | 20 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR, no ratchet (intraday) | 57 | 17 | 40 | 30 | +6.5 | +0.6 | 54 | +6.1 | +3.6 | +1.0 | +3.3 | +0.6 | 16.4 | +0.33 | +0.06 | +1.00 | -0.48 | 2.4 | 7 | 4 | 4 | 4 | 0 | 20 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + floor at initial stop (intraday) | 57 | 17 | 40 | 30 | +6.5 | +0.6 | 54 | +6.2 | +3.7 | +1.1 | +3.3 | +0.7 | 16.4 | +0.34 | +0.06 | +1.00 | -0.45 | 2.0 | 7 | 4 | 4 | 4 | 0 | 20 | robust to top-3 removal |
| Perplexity stock LONG | RATCHET chandelier 4xATR (intraday) | 57 | 17 | 40 | 30 | +6.5 | +0.6 | 54 | +6.2 | +3.7 | +1.1 | +3.3 | +0.7 | 16.4 | +0.34 | +0.06 | +1.00 | -0.46 | 2.3 | 7 | 4 | 4 | 4 | 0 | 20 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 2xATR after 2R (intraday) | 57 | 18 | 39 | 32 | +6.7 | +0.6 | 54 | +6.4 | +3.8 | +1.2 | +3.5 | +0.9 | 16.4 | +0.35 | +0.06 | +1.02 | -0.46 | 2.3 | 7 | 4 | 4 | 4 | 4 | 19 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 3xATR after 2R (intraday) | 57 | 17 | 40 | 30 | +6.6 | +0.6 | 54 | +6.2 | +3.7 | +1.1 | +3.4 | +0.8 | 16.4 | +0.34 | +0.06 | +1.01 | -0.46 | 2.3 | 7 | 4 | 4 | 4 | 4 | 19 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 2xATR after 3R (intraday) | 57 | 17 | 40 | 30 | +6.5 | +0.6 | 54 | +6.2 | +3.7 | +1.1 | +3.3 | +0.7 | 16.4 | +0.34 | +0.06 | +1.00 | -0.46 | 2.3 | 7 | 4 | 4 | 4 | 2 | 20 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 3xATR after 3R (intraday) | 57 | 17 | 40 | 30 | +6.5 | +0.6 | 54 | +6.2 | +3.7 | +1.1 | +3.3 | +0.7 | 16.4 | +0.34 | +0.06 | +1.00 | -0.46 | 2.3 | 7 | 4 | 4 | 4 | 2 | 20 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 2xATR after 4.5R (intraday) | 57 | 17 | 40 | 30 | +6.5 | +0.6 | 54 | +6.2 | +3.7 | +1.1 | +3.3 | +0.7 | 16.4 | +0.34 | +0.06 | +1.00 | -0.46 | 2.3 | 7 | 4 | 4 | 4 | 2 | 20 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 3xATR after 4.5R (intraday) | 57 | 17 | 40 | 30 | +6.5 | +0.6 | 54 | +6.2 | +3.7 | +1.1 | +3.3 | +0.7 | 16.4 | +0.34 | +0.06 | +1.00 | -0.46 | 2.3 | 7 | 4 | 4 | 4 | 2 | 20 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR, no ratchet + 1/2 at 1.618 (intraday) | 57 | 17 | 40 | 30 | +5.3 | +0.9 | 56 | +5.0 | +3.7 | +1.5 | +3.4 | +1.1 | 16.4 | +0.24 | +0.07 | +0.79 | -0.46 | 2.4 | 7 | 4 | 4 | 4 | 0 | 20 | robust to top-3 removal |
| Perplexity stock LONG | chandelier 4xATR + floor at initial stop + 1/2 at 1.618 (intraday) | 57 | 17 | 40 | 30 | +5.4 | +0.9 | 56 | +5.0 | +3.8 | +1.6 | +3.4 | +1.2 | 16.4 | +0.25 | +0.07 | +0.79 | -0.43 | 2.0 | 7 | 4 | 4 | 4 | 0 | 20 | robust to top-3 removal |
| Perplexity stock LONG | RATCHET chandelier 4xATR + 1/2 at 1.618 (intraday) | 57 | 17 | 40 | 30 | +5.4 | +0.9 | 56 | +5.0 | +3.8 | +1.6 | +3.4 | +1.2 | 16.4 | +0.25 | +0.07 | +0.79 | -0.44 | 2.3 | 7 | 4 | 4 | 4 | 0 | 20 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 2xATR after 2R + 1/2 at 1.618 (intraday) | 57 | 18 | 39 | 32 | +5.5 | +0.9 | 56 | +5.1 | +3.8 | +1.7 | +3.5 | +1.3 | 16.4 | +0.25 | +0.07 | +0.79 | -0.44 | 2.3 | 7 | 4 | 4 | 4 | 4 | 19 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 3xATR after 2R + 1/2 at 1.618 (intraday) | 57 | 17 | 40 | 30 | +5.4 | +0.9 | 56 | +5.1 | +3.8 | +1.6 | +3.5 | +1.2 | 16.4 | +0.25 | +0.07 | +0.79 | -0.44 | 2.3 | 7 | 4 | 4 | 4 | 4 | 19 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 2xATR after 3R + 1/2 at 1.618 (intraday) | 57 | 17 | 40 | 30 | +5.4 | +0.9 | 56 | +5.0 | +3.8 | +1.6 | +3.4 | +1.2 | 16.4 | +0.25 | +0.07 | +0.79 | -0.44 | 2.3 | 7 | 4 | 4 | 4 | 2 | 20 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 3xATR after 3R + 1/2 at 1.618 (intraday) | 57 | 17 | 40 | 30 | +5.4 | +0.9 | 56 | +5.0 | +3.8 | +1.6 | +3.4 | +1.2 | 16.4 | +0.25 | +0.07 | +0.79 | -0.44 | 2.3 | 7 | 4 | 4 | 4 | 2 | 20 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 2xATR after 4.5R + 1/2 at 1.618 (intraday) | 57 | 17 | 40 | 30 | +5.4 | +0.9 | 56 | +5.0 | +3.8 | +1.6 | +3.4 | +1.2 | 16.4 | +0.25 | +0.07 | +0.79 | -0.44 | 2.3 | 7 | 4 | 4 | 4 | 2 | 20 | robust to top-3 removal |
| Perplexity stock LONG | ratchet + tighten to 3xATR after 4.5R + 1/2 at 1.618 (intraday) | 57 | 17 | 40 | 30 | +5.4 | +0.9 | 56 | +5.0 | +3.8 | +1.6 | +3.4 | +1.2 | 16.4 | +0.25 | +0.07 | +0.79 | -0.44 | 2.3 | 7 | 4 | 4 | 4 | 2 | 20 | robust to top-3 removal |
| Grok stock LONG | hold, no stop | 131 | 0 | 131 | 0 | +2.0 | +0.3 | 54 | +0.2 | +1.2 | +0.4 | -0.6 | -1.5 | 17.3 | +0.06 | +0.02 | +0.49 | -0.46 | 7.2 | 2 | 1 | 1 | 1 | 0 | 17 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR, no ratchet (close) | 131 | 18 | 113 | 14 | +2.3 | +0.4 | 55 | +0.7 | +1.5 | +0.7 | -0.1 | -0.9 | 17.3 | +0.07 | +0.03 | +0.49 | -0.44 | 7.4 | 2 | 1 | 1 | 1 | 0 | 16 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + floor at initial stop (close) | 131 | 19 | 112 | 15 | +2.3 | +0.4 | 55 | +0.7 | +1.6 | +0.7 | -0.1 | -0.9 | 17.3 | +0.07 | +0.03 | +0.49 | -0.44 | 7.2 | 2 | 1 | 1 | 1 | 0 | 16 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | RATCHET chandelier 4xATR (close) | 131 | 19 | 112 | 15 | +2.3 | +0.4 | 55 | +0.7 | +1.6 | +0.7 | -0.0 | -0.9 | 17.3 | +0.07 | +0.03 | +0.49 | -0.44 | 7.3 | 2 | 1 | 1 | 1 | 0 | 16 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | ratchet + tighten to 2xATR after 2R (close) | 131 | 20 | 111 | 15 | +2.5 | +0.4 | 55 | +0.9 | +1.7 | +0.9 | +0.1 | -0.7 | 17.3 | +0.08 | +0.03 | +0.51 | -0.44 | 7.3 | 2 | 1 | 1 | 1 | 3 | 16 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | ratchet + tighten to 3xATR after 2R (close) | 131 | 19 | 112 | 15 | +2.4 | +0.4 | 55 | +0.8 | +1.7 | +0.9 | +0.1 | -0.8 | 17.3 | +0.08 | +0.03 | +0.50 | -0.44 | 7.3 | 2 | 1 | 1 | 1 | 3 | 16 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | ratchet + tighten to 2xATR after 3R (close) | 131 | 20 | 111 | 15 | +2.3 | +0.4 | 55 | +0.7 | +1.6 | +0.7 | -0.0 | -0.9 | 17.3 | +0.07 | +0.03 | +0.49 | -0.44 | 7.3 | 2 | 1 | 1 | 1 | 1 | 16 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | ratchet + tighten to 3xATR after 3R (close) | 131 | 19 | 112 | 15 | +2.3 | +0.4 | 55 | +0.7 | +1.6 | +0.7 | -0.0 | -0.9 | 17.3 | +0.07 | +0.03 | +0.49 | -0.44 | 7.3 | 2 | 1 | 1 | 1 | 1 | 16 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | ratchet + tighten to 2xATR after 4.5R (close) | 131 | 20 | 111 | 15 | +2.3 | +0.4 | 55 | +0.7 | +1.6 | +0.7 | -0.0 | -0.9 | 17.3 | +0.07 | +0.03 | +0.49 | -0.44 | 7.3 | 2 | 1 | 1 | 1 | 1 | 16 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | ratchet + tighten to 3xATR after 4.5R (close) | 131 | 19 | 112 | 15 | +2.3 | +0.4 | 55 | +0.7 | +1.6 | +0.7 | -0.0 | -0.9 | 17.3 | +0.07 | +0.03 | +0.49 | -0.44 | 7.3 | 2 | 1 | 1 | 1 | 1 | 16 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR, no ratchet + 1/2 at 1.618 (close) | 131 | 18 | 113 | 14 | +2.4 | +0.5 | 57 | +0.8 | +2.0 | +1.3 | +0.4 | -0.3 | 17.3 | +0.07 | +0.04 | +0.46 | -0.45 | 7.5 | 2 | 1 | 1 | 1 | 0 | 16 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + floor at initial stop + 1/2 at 1.618 (close) | 131 | 19 | 112 | 15 | +2.4 | +0.5 | 57 | +0.8 | +2.0 | +1.3 | +0.4 | -0.3 | 17.3 | +0.07 | +0.04 | +0.46 | -0.44 | 7.3 | 2 | 1 | 1 | 1 | 0 | 16 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | RATCHET chandelier 4xATR + 1/2 at 1.618 (close) | 131 | 19 | 112 | 15 | +2.4 | +0.5 | 57 | +0.8 | +2.0 | +1.3 | +0.4 | -0.3 | 17.3 | +0.07 | +0.04 | +0.46 | -0.44 | 7.3 | 2 | 1 | 1 | 1 | 0 | 16 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | ratchet + tighten to 2xATR after 2R + 1/2 at 1.618 (close) | 131 | 20 | 111 | 15 | +2.5 | +0.5 | 57 | +0.9 | +2.0 | +1.3 | +0.5 | -0.3 | 17.3 | +0.08 | +0.04 | +0.46 | -0.44 | 7.3 | 2 | 1 | 1 | 1 | 3 | 16 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | ratchet + tighten to 3xATR after 2R + 1/2 at 1.618 (close) | 131 | 19 | 112 | 15 | +2.5 | +0.5 | 57 | +0.9 | +2.0 | +1.3 | +0.5 | -0.3 | 17.3 | +0.07 | +0.04 | +0.46 | -0.44 | 7.3 | 2 | 1 | 1 | 1 | 3 | 16 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | ratchet + tighten to 2xATR after 3R + 1/2 at 1.618 (close) | 131 | 20 | 111 | 15 | +2.4 | +0.5 | 57 | +0.8 | +2.0 | +1.3 | +0.4 | -0.3 | 17.3 | +0.07 | +0.04 | +0.46 | -0.44 | 7.3 | 2 | 1 | 1 | 1 | 1 | 16 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | ratchet + tighten to 3xATR after 3R + 1/2 at 1.618 (close) | 131 | 19 | 112 | 15 | +2.4 | +0.5 | 57 | +0.8 | +2.0 | +1.3 | +0.4 | -0.3 | 17.3 | +0.07 | +0.04 | +0.46 | -0.44 | 7.3 | 2 | 1 | 1 | 1 | 1 | 16 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | ratchet + tighten to 2xATR after 4.5R + 1/2 at 1.618 (close) | 131 | 20 | 111 | 15 | +2.4 | +0.5 | 57 | +0.8 | +2.0 | +1.3 | +0.4 | -0.3 | 17.3 | +0.07 | +0.04 | +0.46 | -0.44 | 7.3 | 2 | 1 | 1 | 1 | 1 | 16 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | ratchet + tighten to 3xATR after 4.5R + 1/2 at 1.618 (close) | 131 | 19 | 112 | 15 | +2.4 | +0.5 | 57 | +0.8 | +2.0 | +1.3 | +0.4 | -0.3 | 17.3 | +0.07 | +0.04 | +0.46 | -0.44 | 7.3 | 2 | 1 | 1 | 1 | 1 | 16 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR, no ratchet (intraday) | 131 | 20 | 111 | 15 | +2.4 | +0.4 | 55 | +0.8 | +1.7 | +0.9 | +0.1 | -0.7 | 17.3 | +0.08 | +0.03 | +0.50 | -0.44 | 7.4 | 2 | 1 | 1 | 1 | 0 | 15 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR + floor at initial stop (intraday) | 131 | 22 | 109 | 17 | +2.3 | +0.4 | 55 | +0.8 | +1.6 | +0.8 | +0.1 | -0.7 | 17.3 | +0.07 | +0.03 | +0.50 | -0.45 | 7.6 | 2 | 1 | 1 | 1 | 0 | 15 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | RATCHET chandelier 4xATR (intraday) | 131 | 21 | 110 | 16 | +2.5 | +0.4 | 55 | +0.9 | +1.7 | +0.9 | +0.2 | -0.6 | 17.3 | +0.08 | +0.03 | +0.50 | -0.43 | 7.4 | 2 | 1 | 1 | 1 | 0 | 15 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | ratchet + tighten to 2xATR after 2R (intraday) | 131 | 22 | 109 | 17 | +2.6 | +0.4 | 55 | +1.1 | +1.9 | +1.0 | +0.3 | -0.5 | 17.3 | +0.09 | +0.03 | +0.51 | -0.43 | 7.4 | 2 | 1 | 1 | 1 | 3 | 15 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | ratchet + tighten to 3xATR after 2R (intraday) | 131 | 22 | 109 | 17 | +2.5 | +0.4 | 55 | +0.9 | +1.8 | +1.0 | +0.2 | -0.6 | 17.3 | +0.08 | +0.03 | +0.50 | -0.43 | 7.4 | 2 | 1 | 1 | 1 | 3 | 15 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | ratchet + tighten to 2xATR after 3R (intraday) | 131 | 22 | 109 | 17 | +2.5 | +0.4 | 55 | +0.9 | +1.7 | +0.9 | +0.2 | -0.6 | 17.3 | +0.08 | +0.03 | +0.50 | -0.43 | 7.4 | 2 | 1 | 1 | 1 | 1 | 15 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | ratchet + tighten to 3xATR after 3R (intraday) | 131 | 22 | 109 | 17 | +2.4 | +0.4 | 55 | +0.8 | +1.7 | +0.9 | +0.2 | -0.6 | 17.3 | +0.08 | +0.03 | +0.50 | -0.43 | 7.4 | 2 | 1 | 1 | 1 | 1 | 15 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | ratchet + tighten to 2xATR after 4.5R (intraday) | 131 | 22 | 109 | 17 | +2.5 | +0.4 | 55 | +0.9 | +1.7 | +0.9 | +0.2 | -0.6 | 17.3 | +0.08 | +0.03 | +0.50 | -0.43 | 7.4 | 2 | 1 | 1 | 1 | 1 | 15 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | ratchet + tighten to 3xATR after 4.5R (intraday) | 131 | 22 | 109 | 17 | +2.4 | +0.4 | 55 | +0.8 | +1.7 | +0.9 | +0.2 | -0.6 | 17.3 | +0.08 | +0.03 | +0.50 | -0.43 | 7.4 | 2 | 1 | 1 | 1 | 1 | 15 | LUCK (edge gone w/o top tickers) |
| Grok stock LONG | chandelier 4xATR, no ratchet + 1/2 at 1.618 (intraday) | 131 | 20 | 111 | 15 | +2.9 | +0.5 | 56 | +1.4 | +2.6 | +1.8 | +1.0 | +0.3 | 17.3 | +0.09 | +0.05 | +0.47 | -0.40 | 7.2 | 2 | 1 | 1 | 1 | 0 | 15 | robust to top-3 removal |
| Grok stock LONG | chandelier 4xATR + floor at initial stop + 1/2 at 1.618 (intraday) | 131 | 22 | 109 | 17 | +2.9 | +0.5 | 56 | +1.4 | +2.5 | +1.8 | +1.0 | +0.2 | 17.3 | +0.09 | +0.05 | +0.47 | -0.41 | 7.4 | 2 | 1 | 1 | 1 | 0 | 15 | robust to top-3 removal |
| Grok stock LONG | RATCHET chandelier 4xATR + 1/2 at 1.618 (intraday) | 131 | 21 | 110 | 16 | +3.0 | +0.5 | 56 | +1.4 | +2.6 | +1.9 | +1.1 | +0.3 | 17.3 | +0.10 | +0.05 | +0.48 | -0.40 | 7.1 | 2 | 1 | 1 | 1 | 0 | 15 | robust to top-3 removal |
| Grok stock LONG | ratchet + tighten to 2xATR after 2R + 1/2 at 1.618 (intraday) | 131 | 22 | 109 | 17 | +3.1 | +0.5 | 56 | +1.5 | +2.6 | +1.9 | +1.1 | +0.3 | 17.3 | +0.10 | +0.05 | +0.48 | -0.40 | 7.1 | 2 | 1 | 1 | 1 | 3 | 15 | robust to top-3 removal |
| Grok stock LONG | ratchet + tighten to 3xATR after 2R + 1/2 at 1.618 (intraday) | 131 | 22 | 109 | 17 | +3.0 | +0.5 | 56 | +1.4 | +2.6 | +1.8 | +1.1 | +0.3 | 17.3 | +0.10 | +0.05 | +0.47 | -0.40 | 7.1 | 2 | 1 | 1 | 1 | 3 | 15 | robust to top-3 removal |
| Grok stock LONG | ratchet + tighten to 2xATR after 3R + 1/2 at 1.618 (intraday) | 131 | 22 | 109 | 17 | +3.0 | +0.5 | 56 | +1.4 | +2.6 | +1.9 | +1.1 | +0.3 | 17.3 | +0.10 | +0.05 | +0.48 | -0.40 | 7.1 | 2 | 1 | 1 | 1 | 1 | 15 | robust to top-3 removal |
| Grok stock LONG | ratchet + tighten to 3xATR after 3R + 1/2 at 1.618 (intraday) | 131 | 22 | 109 | 17 | +3.0 | +0.5 | 56 | +1.4 | +2.6 | +1.8 | +1.0 | +0.3 | 17.3 | +0.09 | +0.05 | +0.47 | -0.40 | 7.1 | 2 | 1 | 1 | 1 | 1 | 15 | robust to top-3 removal |
| Grok stock LONG | ratchet + tighten to 2xATR after 4.5R + 1/2 at 1.618 (intraday) | 131 | 22 | 109 | 17 | +3.0 | +0.5 | 56 | +1.4 | +2.6 | +1.9 | +1.1 | +0.3 | 17.3 | +0.10 | +0.05 | +0.48 | -0.40 | 7.1 | 2 | 1 | 1 | 1 | 1 | 15 | robust to top-3 removal |
| Grok stock LONG | ratchet + tighten to 3xATR after 4.5R + 1/2 at 1.618 (intraday) | 131 | 22 | 109 | 17 | +3.0 | +0.5 | 56 | +1.4 | +2.6 | +1.8 | +1.0 | +0.3 | 17.3 | +0.09 | +0.05 | +0.47 | -0.40 | 7.1 | 2 | 1 | 1 | 1 | 1 | 15 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | hold, no stop | 60 | 0 | 60 | 0 | +3.6 | +6.3 | 73 | +4.8 | +3.4 | +2.7 | +4.6 | +3.9 | 14.3 | +0.46 | +0.32 | +0.85 | -0.63 | 3.7 | 10 | 3 | 0 | 0 | 0 | 19 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR, no ratchet (close) | 60 | 4 | 56 | 7 | +4.5 | +6.3 | 73 | +5.6 | +4.3 | +3.6 | +5.4 | +4.7 | 14.3 | +0.52 | +0.32 | +0.85 | -0.39 | 2.0 | 10 | 3 | 0 | 0 | 0 | 18 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + floor at initial stop (close) | 60 | 4 | 56 | 7 | +4.5 | +6.3 | 73 | +5.6 | +4.3 | +3.6 | +5.4 | +4.7 | 14.3 | +0.52 | +0.32 | +0.85 | -0.39 | 2.0 | 10 | 3 | 0 | 0 | 0 | 18 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | RATCHET chandelier 4xATR (close) | 60 | 7 | 53 | 12 | +4.3 | +6.3 | 73 | +5.4 | +4.1 | +3.4 | +5.2 | +4.5 | 14.3 | +0.52 | +0.32 | +0.85 | -0.39 | 1.8 | 10 | 3 | 0 | 0 | 0 | 17 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | ratchet + tighten to 2xATR after 2R (close) | 60 | 8 | 52 | 13 | +4.3 | +6.3 | 73 | +5.4 | +4.1 | +3.4 | +5.2 | +4.5 | 14.3 | +0.52 | +0.32 | +0.85 | -0.39 | 1.8 | 10 | 3 | 0 | 0 | 6 | 17 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | ratchet + tighten to 3xATR after 2R (close) | 60 | 7 | 53 | 12 | +4.3 | +6.3 | 73 | +5.4 | +4.1 | +3.4 | +5.2 | +4.5 | 14.3 | +0.52 | +0.32 | +0.85 | -0.39 | 1.8 | 10 | 3 | 0 | 0 | 6 | 17 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | ratchet + tighten to 2xATR after 3R (close) | 60 | 7 | 53 | 12 | +4.3 | +6.3 | 73 | +5.4 | +4.1 | +3.4 | +5.2 | +4.5 | 14.3 | +0.52 | +0.32 | +0.85 | -0.39 | 1.8 | 10 | 3 | 0 | 0 | 2 | 17 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | ratchet + tighten to 3xATR after 3R (close) | 60 | 7 | 53 | 12 | +4.3 | +6.3 | 73 | +5.4 | +4.1 | +3.4 | +5.2 | +4.5 | 14.3 | +0.52 | +0.32 | +0.85 | -0.39 | 1.8 | 10 | 3 | 0 | 0 | 2 | 17 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | ratchet + tighten to 2xATR after 4.5R (close) | 60 | 7 | 53 | 12 | +4.3 | +6.3 | 73 | +5.4 | +4.1 | +3.4 | +5.2 | +4.5 | 14.3 | +0.52 | +0.32 | +0.85 | -0.39 | 1.8 | 10 | 3 | 0 | 0 | 0 | 17 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | ratchet + tighten to 3xATR after 4.5R (close) | 60 | 7 | 53 | 12 | +4.3 | +6.3 | 73 | +5.4 | +4.1 | +3.4 | +5.2 | +4.5 | 14.3 | +0.52 | +0.32 | +0.85 | -0.39 | 1.8 | 10 | 3 | 0 | 0 | 0 | 17 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR, no ratchet (intraday) | 60 | 5 | 55 | 8 | +4.4 | +6.3 | 73 | +5.5 | +4.2 | +3.6 | +5.3 | +4.6 | 14.3 | +0.53 | +0.32 | +0.85 | -0.36 | 1.4 | 10 | 3 | 0 | 0 | 0 | 17 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | chandelier 4xATR + floor at initial stop (intraday) | 60 | 5 | 55 | 8 | +4.4 | +6.3 | 73 | +5.5 | +4.2 | +3.6 | +5.3 | +4.6 | 14.3 | +0.53 | +0.32 | +0.85 | -0.36 | 1.4 | 10 | 3 | 0 | 0 | 0 | 17 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | RATCHET chandelier 4xATR (intraday) | 60 | 7 | 53 | 12 | +4.5 | +6.3 | 73 | +5.6 | +4.3 | +3.7 | +5.4 | +4.8 | 14.3 | +0.53 | +0.32 | +0.85 | -0.34 | 1.2 | 10 | 3 | 0 | 0 | 0 | 17 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | ratchet + tighten to 2xATR after 2R (intraday) | 60 | 12 | 48 | 20 | +4.1 | +5.8 | 73 | +5.1 | +3.9 | +3.2 | +4.9 | +4.2 | 14.3 | +0.43 | +0.32 | +0.71 | -0.34 | 1.2 | 10 | 2 | 0 | 0 | 6 | 16 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | ratchet + tighten to 3xATR after 2R (intraday) | 60 | 7 | 53 | 12 | +4.5 | +6.3 | 73 | +5.6 | +4.3 | +3.7 | +5.4 | +4.8 | 14.3 | +0.53 | +0.32 | +0.85 | -0.34 | 1.2 | 10 | 3 | 0 | 0 | 6 | 17 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | ratchet + tighten to 2xATR after 3R (intraday) | 60 | 9 | 51 | 15 | +4.4 | +6.3 | 73 | +5.5 | +4.2 | +3.6 | +5.3 | +4.6 | 14.3 | +0.51 | +0.32 | +0.81 | -0.34 | 1.2 | 10 | 3 | 0 | 0 | 2 | 17 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | ratchet + tighten to 3xATR after 3R (intraday) | 60 | 7 | 53 | 12 | +4.5 | +6.3 | 73 | +5.6 | +4.3 | +3.7 | +5.4 | +4.8 | 14.3 | +0.53 | +0.32 | +0.85 | -0.34 | 1.2 | 10 | 3 | 0 | 0 | 2 | 17 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | ratchet + tighten to 2xATR after 4.5R (intraday) | 60 | 7 | 53 | 12 | +4.5 | +6.3 | 73 | +5.6 | +4.3 | +3.7 | +5.4 | +4.8 | 14.3 | +0.53 | +0.32 | +0.85 | -0.34 | 1.2 | 10 | 3 | 0 | 0 | 0 | 17 | robust to top-3 removal |
| Rule-filtered stock SHORT (score>=3 & <SMA200) | ratchet + tighten to 3xATR after 4.5R (intraday) | 60 | 7 | 53 | 12 | +4.5 | +6.3 | 73 | +5.6 | +4.3 | +3.7 | +5.4 | +4.8 | 14.3 | +0.53 | +0.32 | +0.85 | -0.34 | 1.2 | 10 | 3 | 0 | 0 | 0 | 17 | robust to top-3 removal |
| All stock SHORT | hold, no stop | 173 | 0 | 173 | 0 | -0.9 | -1.2 | 46 | +0.5 | -1.2 | -1.5 | +0.2 | -0.1 | 14.3 | -0.03 | -0.10 | +0.62 | -0.57 | 21.9 | 3 | 1 | 0 | 0 | 0 | 17 | LUCK (edge gone w/o top tickers) |
| All stock SHORT | chandelier 4xATR, no ratchet (close) | 173 | 27 | 146 | 16 | -0.5 | -1.2 | 46 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | 14.3 | -0.01 | -0.10 | +0.62 | -0.53 | 23.4 | 3 | 1 | 0 | 0 | 0 | 15 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + floor at initial stop (close) | 173 | 29 | 144 | 17 | -0.5 | -1.2 | 46 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | 14.3 | -0.01 | -0.10 | +0.62 | -0.53 | 22.4 | 3 | 1 | 0 | 0 | 0 | 15 | robust to top-3 removal |
| All stock SHORT | RATCHET chandelier 4xATR (close) | 173 | 30 | 143 | 17 | -0.5 | -1.2 | 46 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | 14.3 | -0.00 | -0.12 | +0.62 | -0.53 | 22.9 | 3 | 1 | 0 | 0 | 0 | 15 | robust to top-3 removal |
| All stock SHORT | ratchet + tighten to 2xATR after 2R (close) | 173 | 31 | 142 | 18 | -0.5 | -1.2 | 46 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | 14.3 | -0.00 | -0.12 | +0.62 | -0.53 | 22.9 | 3 | 1 | 0 | 0 | 6 | 15 | robust to top-3 removal |
| All stock SHORT | ratchet + tighten to 3xATR after 2R (close) | 173 | 30 | 143 | 17 | -0.5 | -1.2 | 46 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | 14.3 | -0.00 | -0.12 | +0.62 | -0.53 | 22.9 | 3 | 1 | 0 | 0 | 6 | 15 | robust to top-3 removal |
| All stock SHORT | ratchet + tighten to 2xATR after 3R (close) | 173 | 30 | 143 | 17 | -0.5 | -1.2 | 46 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | 14.3 | -0.00 | -0.12 | +0.62 | -0.53 | 22.9 | 3 | 1 | 0 | 0 | 2 | 15 | robust to top-3 removal |
| All stock SHORT | ratchet + tighten to 3xATR after 3R (close) | 173 | 30 | 143 | 17 | -0.5 | -1.2 | 46 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | 14.3 | -0.00 | -0.12 | +0.62 | -0.53 | 22.9 | 3 | 1 | 0 | 0 | 2 | 15 | robust to top-3 removal |
| All stock SHORT | ratchet + tighten to 2xATR after 4.5R (close) | 173 | 30 | 143 | 17 | -0.5 | -1.2 | 46 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | 14.3 | -0.00 | -0.12 | +0.62 | -0.53 | 22.9 | 3 | 1 | 0 | 0 | 0 | 15 | robust to top-3 removal |
| All stock SHORT | ratchet + tighten to 3xATR after 4.5R (close) | 173 | 30 | 143 | 17 | -0.5 | -1.2 | 46 | +0.8 | -0.8 | -1.1 | +0.5 | +0.2 | 14.3 | -0.00 | -0.12 | +0.62 | -0.53 | 22.9 | 3 | 1 | 0 | 0 | 0 | 15 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR, no ratchet (intraday) | 173 | 35 | 138 | 20 | -0.3 | -1.2 | 46 | +1.1 | -0.6 | -0.9 | +0.8 | +0.5 | 14.3 | +0.01 | -0.11 | +0.61 | -0.50 | 20.7 | 3 | 1 | 0 | 0 | 0 | 15 | robust to top-3 removal |
| All stock SHORT | chandelier 4xATR + floor at initial stop (intraday) | 173 | 37 | 136 | 21 | -0.3 | -1.2 | 46 | +1.0 | -0.6 | -0.9 | +0.7 | +0.4 | 14.3 | +0.01 | -0.11 | +0.61 | -0.51 | 20.3 | 3 | 1 | 0 | 0 | 0 | 15 | robust to top-3 removal |
| All stock SHORT | RATCHET chandelier 4xATR (intraday) | 173 | 38 | 135 | 22 | -0.1 | -1.2 | 46 | +1.2 | -0.4 | -0.7 | +0.9 | +0.6 | 14.3 | +0.02 | -0.11 | +0.61 | -0.49 | 20.2 | 3 | 1 | 0 | 0 | 0 | 15 | robust to top-3 removal |
| All stock SHORT | ratchet + tighten to 2xATR after 2R (intraday) | 173 | 43 | 130 | 25 | -0.3 | -1.2 | 46 | +1.0 | -0.6 | -0.9 | +0.7 | +0.4 | 14.3 | -0.02 | -0.11 | +0.53 | -0.49 | 20.2 | 3 | 1 | 0 | 0 | 6 | 14 | robust to top-3 removal |
| All stock SHORT | ratchet + tighten to 3xATR after 2R (intraday) | 173 | 38 | 135 | 22 | -0.1 | -1.2 | 46 | +1.2 | -0.4 | -0.7 | +0.9 | +0.6 | 14.3 | +0.02 | -0.11 | +0.61 | -0.49 | 20.2 | 3 | 1 | 0 | 0 | 6 | 15 | robust to top-3 removal |
| All stock SHORT | ratchet + tighten to 2xATR after 3R (intraday) | 173 | 40 | 133 | 23 | -0.2 | -1.2 | 46 | +1.2 | -0.5 | -0.8 | +0.8 | +0.5 | 14.3 | +0.01 | -0.11 | +0.59 | -0.49 | 20.2 | 3 | 1 | 0 | 0 | 2 | 15 | robust to top-3 removal |
| All stock SHORT | ratchet + tighten to 3xATR after 3R (intraday) | 173 | 38 | 135 | 22 | -0.1 | -1.2 | 46 | +1.2 | -0.4 | -0.7 | +0.9 | +0.6 | 14.3 | +0.02 | -0.11 | +0.61 | -0.49 | 20.2 | 3 | 1 | 0 | 0 | 2 | 15 | robust to top-3 removal |
| All stock SHORT | ratchet + tighten to 2xATR after 4.5R (intraday) | 173 | 38 | 135 | 22 | -0.1 | -1.2 | 46 | +1.2 | -0.4 | -0.7 | +0.9 | +0.6 | 14.3 | +0.02 | -0.11 | +0.61 | -0.49 | 20.2 | 3 | 1 | 0 | 0 | 0 | 15 | robust to top-3 removal |
| All stock SHORT | ratchet + tighten to 3xATR after 4.5R (intraday) | 173 | 38 | 135 | 22 | -0.1 | -1.2 | 46 | +1.2 | -0.4 | -0.7 | +0.9 | +0.6 | 14.3 | +0.02 | -0.11 | +0.61 | -0.49 | 20.2 | 3 | 1 | 0 | 0 | 0 | 15 | robust to top-3 removal |

### Excluded-for-mcap rows (full)
| policy   | src         | asset   | dir   |   N |   tickers |   mean |   median |   hit |   x_mkt |   x_mkt_med |
|:---------|:------------|:--------|:------|----:|----------:|-------:|---------:|------:|--------:|------------:|
| hold     | Bot         | stock   | LONG  |   1 |         1 |   -5.8 |     -5.8 |   0   |    -6.9 |        -6.9 |
| hold     | Grok        | crypto  | LONG  |  28 |        17 |   46   |     35.7 |  96.4 |    17.9 |         7   |
| hold     | Grok        | crypto  | SHORT | 115 |        55 |   -7.3 |     12.9 |  57.4 |    18.2 |        30.6 |
| hold     | Grok        | stock   | LONG  |  30 |        23 |  -16.5 |    -15.4 |  20   |   -18   |       -17.1 |
| hold     | Grok        | stock   | SHORT |  18 |        17 |   25.3 |     22.6 |  94.4 |    27   |        24.8 |
| hold     | Ilan charts | stock   | LONG  |   2 |         2 |  -18.5 |    -18.5 |   0   |   -19.3 |       -19.3 |
| hold     | Perplexity  | crypto  | LONG  |   3 |         3 |   74.7 |    149.9 |  66.7 |    43.1 |       118.2 |
| hold     | Perplexity  | crypto  | SHORT |   3 |         3 |   11.3 |     90   |  66.7 |    42.9 |       121.6 |
| t8       | Bot         | stock   | LONG  |   1 |         1 |   -5.8 |     -5.8 |   0   |    -6.9 |        -6.9 |
| t8       | Grok        | crypto  | LONG  |  28 |        17 |    4.1 |     -4   |  39.3 |    -4.4 |        -7.5 |
| t8       | Grok        | crypto  | SHORT | 115 |        55 |    4   |     -0.4 |  48.7 |     9.2 |         4.3 |
| t8       | Grok        | stock   | LONG  |  30 |        23 |   -8.6 |     -9.4 |  20   |    -8.8 |       -10.5 |
| t8       | Grok        | stock   | SHORT |  18 |        17 |    6   |     16.4 |  72.2 |     6.8 |        16.2 |
| t8       | Ilan charts | stock   | LONG  |   2 |         2 |   -0.1 |     -0.1 |  50   |     0.4 |         0.4 |
| t8       | Perplexity  | crypto  | LONG  |   3 |         3 |   10.1 |     24   |  66.7 |    -5.6 |         0.1 |
| t8       | Perplexity  | crypto  | SHORT |   3 |         3 |   15.3 |    -18.6 |  33.3 |    26.1 |       -10.5 |

### Exact-minute vs daily-cutoff (full)
Timed setups (exact/schedule/ui_log) in main non-dup population with a minute entry: 464; of which entry moved vs daily version: stocks 20, crypto 99 (all crypto timed entries move from next 00:00 UTC to the alert minute).

| policy | source | asset | dir | subset | N | DAILY-cutoff mean / median / hit / x_mkt (w/o top1) | EXACT-MINUTE mean / median / hit / x_mkt (w/o top1) | Δmean pp | Δmedian pp |
|---|---|---|---|---|---|---|---|---|---|
| hold | Bot | stock | LONG | all timed | 30 | +2.3 / +0.3 / 53% / +1.0 (w/o top1 -0.0) | +2.3 / +0.3 / 53% / +1.0 (w/o top1 -0.0) | +0.00 | +0.00 |
| hold | Bot | stock | SHORT | all timed | 19 | +0.0 / +0.8 / 58% / +1.3 (w/o top1 +0.6) | -0.0 / +0.8 / 58% / +1.3 (w/o top1 +0.7) | -0.01 | -0.00 |
| hold | Grok | crypto | LONG | all timed | 54 | +4.5 / +3.5 / 67% / +0.6 (w/o top1 -0.2) | +4.9 / +3.9 / 69% / +0.9 (w/o top1 +0.0) | +0.38 | -0.02 |
| hold | Grok | crypto | LONG | entry changed | 54 | +4.5 / +3.5 / 67% / +0.6 (w/o top1 -0.2) | +4.9 / +3.9 / 69% / +0.9 (w/o top1 +0.0) | +0.38 | -0.02 |
| hold | Grok | crypto | SHORT | all timed | 36 | -2.6 / -2.0 / 42% / +1.0 (w/o top1 +0.2) | -2.5 / -2.1 / 42% / +0.9 (w/o top1 -0.0) | +0.07 | +0.06 |
| hold | Grok | crypto | SHORT | entry changed | 36 | -2.6 / -2.0 / 42% / +1.0 (w/o top1 +0.2) | -2.5 / -2.1 / 42% / +0.9 (w/o top1 -0.0) | +0.07 | +0.06 |
| hold | Grok | stock | LONG | all timed | 127 | +0.9 / +0.3 / 54% / -0.7 (w/o top1 -1.1) | +0.8 / +0.3 / 53% / -0.8 (w/o top1 -1.3) | -0.13 | +0.00 |
| hold | Grok | stock | SHORT | all timed | 119 | -1.0 / -1.8 / 40% / +0.5 (w/o top1 +0.3) | -1.0 / -1.8 / 40% / +0.5 (w/o top1 +0.3) | -0.00 | -0.00 |
| hold | Perplexity | crypto | LONG | all timed | 9 | +46.1 / +49.7 / 100% / +14.4 (w/o top1 +12.4) | +45.5 / +50.3 / 100% / +14.5 (w/o top1 +12.4) | -0.58 | -0.69 |
| hold | Perplexity | crypto | LONG | entry changed | 9 | +46.1 / +49.7 / 100% / +14.4 (w/o top1 +12.4) | +45.5 / +50.3 / 100% / +14.5 (w/o top1 +12.4) | -0.58 | -0.69 |
| hold | Perplexity | stock | LONG | all timed | 42 | +1.9 / +0.6 / 55% / +0.9 (w/o top1 +0.1) | +1.6 / +0.4 / 55% / +0.6 (w/o top1 -0.3) | -0.28 | -0.00 |
| hold | Perplexity | stock | LONG | entry changed | 14 | +3.2 / -0.0 / 50% / +3.0 (w/o top1 +0.5) | +2.4 / -1.2 / 50% / +2.1 (w/o top1 -0.5) | -0.81 | -1.32 |
| hold | Perplexity | stock | SHORT | all timed | 28 | -3.0 / -2.3 / 39% / -1.9 (w/o top1 -2.6) | -2.9 / -2.3 / 39% / -1.7 (w/o top1 -2.5) | +0.15 | -0.00 |
| hold | Perplexity | stock | SHORT | entry changed | 6 | -11.1 / -10.2 / 33% / -10.8 (w/o top1 -14.5) | -10.3 / -10.3 / 33% / -9.9 (w/o top1 -13.7) | +0.78 | -0.12 |
| t8 | Bot | stock | LONG | all timed | 30 | +2.3 / +0.3 / 53% / +1.0 (w/o top1 -0.0) | +2.3 / +0.3 / 53% / +1.0 (w/o top1 -0.0) | +0.00 | +0.00 |
| t8 | Bot | stock | SHORT | all timed | 19 | -0.2 / +0.2 / 53% / +0.9 (w/o top1 +0.3) | -0.2 / +0.2 / 53% / +0.9 (w/o top1 +0.3) | -0.01 | -0.00 |
| t8 | Grok | crypto | LONG | all timed | 54 | +2.4 / +2.6 / 56% / -0.4 (w/o top1 -1.0) | +1.9 / +1.8 / 54% / -0.5 (w/o top1 -0.8) | -0.54 | -0.24 |
| t8 | Grok | crypto | LONG | entry changed | 54 | +2.4 / +2.6 / 56% / -0.4 (w/o top1 -1.0) | +1.9 / +1.8 / 54% / -0.5 (w/o top1 -0.8) | -0.54 | -0.24 |
| t8 | Grok | crypto | SHORT | all timed | 36 | -2.7 / -2.7 / 42% / +0.4 (w/o top1 +0.0) | -3.1 / -3.3 / 42% / -0.0 (w/o top1 -0.5) | -0.42 | +0.09 |
| t8 | Grok | crypto | SHORT | entry changed | 36 | -2.7 / -2.7 / 42% / +0.4 (w/o top1 +0.0) | -3.1 / -3.3 / 42% / -0.0 (w/o top1 -0.5) | -0.42 | +0.09 |
| t8 | Grok | stock | LONG | all timed | 127 | +0.8 / +0.1 / 52% / -0.4 (w/o top1 -0.7) | +0.7 / +0.0 / 51% / -0.5 (w/o top1 -0.9) | -0.13 | +0.00 |
| t8 | Grok | stock | SHORT | all timed | 119 | -1.2 / -2.5 / 35% / -0.1 (w/o top1 -0.3) | -1.2 / -2.5 / 35% / -0.1 (w/o top1 -0.3) | -0.00 | -0.00 |
| t8 | Perplexity | crypto | LONG | all timed | 9 | +30.6 / +31.9 / 100% / +3.9 (w/o top1 +2.0) | +30.1 / +31.8 / 100% / +4.0 (w/o top1 +2.1) | -0.52 | -0.64 |
| t8 | Perplexity | crypto | LONG | entry changed | 9 | +30.6 / +31.9 / 100% / +3.9 (w/o top1 +2.0) | +30.1 / +31.8 / 100% / +4.0 (w/o top1 +2.1) | -0.52 | -0.64 |
| t8 | Perplexity | stock | LONG | all timed | 42 | -0.8 / -2.0 / 43% / -0.8 (w/o top1 -1.4) | -0.8 / -2.3 / 40% / -0.9 (w/o top1 -1.5) | -0.04 | -0.00 |
| t8 | Perplexity | stock | LONG | entry changed | 14 | -2.2 / -3.6 / 29% / -0.7 (w/o top1 -2.5) | -2.3 / -3.7 / 21% / -0.9 (w/o top1 -2.8) | -0.09 | -0.88 |
| t8 | Perplexity | stock | SHORT | all timed | 28 | -3.1 / -3.5 / 29% / -2.5 (w/o top1 -3.0) | -2.8 / -3.5 / 29% / -2.1 (w/o top1 -2.6) | +0.26 | -0.00 |
| t8 | Perplexity | stock | SHORT | entry changed | 6 | -6.5 / -5.4 / 33% / -7.6 (w/o top1 -11.2) | -5.2 / -7.6 / 33% / -5.8 (w/o top1 -9.0) | +1.31 | -0.16 |
| fsetup | Bot | stock | LONG | all timed | 30 | +1.9 / -0.2 / 50% / +1.1 (w/o top1 +0.0) | +1.9 / -0.2 / 50% / +1.1 (w/o top1 +0.0) | +0.00 | +0.00 |
| fsetup | Bot | stock | SHORT | all timed | 19 | -0.9 / -0.9 / 47% / +0.2 (w/o top1 -0.5) | -0.9 / -0.9 / 47% / +0.2 (w/o top1 -0.5) | -0.01 | -0.00 |
| fsetup | Grok | crypto | LONG | all timed | 54 | +2.5 / +2.2 / 56% / -0.3 (w/o top1 -0.9) | +2.9 / +2.7 / 57% / -0.0 (w/o top1 -0.7) | +0.38 | -0.02 |
| fsetup | Grok | crypto | LONG | entry changed | 54 | +2.5 / +2.2 / 56% / -0.3 (w/o top1 -0.9) | +2.9 / +2.7 / 57% / -0.0 (w/o top1 -0.7) | +0.38 | -0.02 |
| fsetup | Grok | crypto | SHORT | all timed | 36 | -3.9 / -4.7 / 36% / -0.0 (w/o top1 -0.5) | -4.2 / -5.2 / 36% / -0.2 (w/o top1 -0.7) | -0.32 | +0.03 |
| fsetup | Grok | crypto | SHORT | entry changed | 36 | -3.9 / -4.7 / 36% / -0.0 (w/o top1 -0.5) | -4.2 / -5.2 / 36% / -0.2 (w/o top1 -0.7) | -0.32 | +0.03 |
| fsetup | Grok | stock | LONG | all timed | 127 | +0.5 / +0.0 / 51% / -0.6 (w/o top1 -1.0) | +0.4 / +0.0 / 50% / -0.7 (w/o top1 -1.1) | -0.13 | +0.00 |
| fsetup | Grok | stock | SHORT | all timed | 119 | -0.9 / -2.3 / 36% / +0.3 (w/o top1 +0.0) | -0.9 / -2.3 / 36% / +0.3 (w/o top1 +0.0) | -0.00 | -0.00 |
| fsetup | Perplexity | crypto | LONG | all timed | 9 | +46.1 / +49.7 / 100% / +14.4 (w/o top1 +12.4) | +45.5 / +50.3 / 100% / +14.5 (w/o top1 +12.4) | -0.58 | -0.69 |
| fsetup | Perplexity | crypto | LONG | entry changed | 9 | +46.1 / +49.7 / 100% / +14.4 (w/o top1 +12.4) | +45.5 / +50.3 / 100% / +14.5 (w/o top1 +12.4) | -0.58 | -0.69 |
| fsetup | Perplexity | stock | LONG | all timed | 42 | +1.7 / -0.8 / 48% / +1.3 (w/o top1 +0.4) | +1.5 / -0.5 / 48% / +1.0 (w/o top1 +0.1) | -0.28 | -0.00 |
| fsetup | Perplexity | stock | LONG | entry changed | 14 | +4.0 / -0.0 / 50% / +4.2 (w/o top1 +1.7) | +3.2 / -1.2 / 50% / +3.3 (w/o top1 +0.8) | -0.81 | -1.32 |
| fsetup | Perplexity | stock | SHORT | all timed | 28 | -2.7 / -2.3 / 39% / -1.7 (w/o top1 -2.5) | -2.5 / -2.3 / 39% / -1.5 (w/o top1 -2.3) | +0.15 | -0.00 |
| fsetup | Perplexity | stock | SHORT | entry changed | 6 | -11.1 / -10.2 / 33% / -10.8 (w/o top1 -14.5) | -10.3 / -10.3 / 33% / -9.9 (w/o top1 -13.7) | +0.78 | -0.12 |