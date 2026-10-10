
## 7. ai-hedge-fund personas as an approve/veto filter, plus API cost (box run 8.10, 14:00–16:00 IL)

**Bottom line: on the box (Qwen2.5-3B) neither persona works as a filter. Neither is worth even a weight-0 column yet. Wait for the laptop's 7B run on all ~442 stock setups (nightly from 8.10).** Details: `aihf_bt/filter_results_active.md` (script `aihf_bt/analyze_active.py`). The older hold/chand4-only tables are in `aihf_bt/filter_results.md`.

**Setup.**
- Sample: the first 60 stock setups of the stratified sample (`backtest/sample_order.csv`): 31 longs and 29 shorts, 53 tickers, trade dates 20.07–29.09, 17 distinct entry days.
- Each persona (`druckenmiller`, `buffett`) gets one LLM call per setup, in blind mode: ticker, industry and dates are withheld.
- Data comes from SEC EDGAR as filed on or before the cutoff, plus Yahoo closes up to the cutoff (`aihf_bt/edgar_client.py`). That replaces the paid Financial Datasets key, so the "Blocked" note in §3 no longer applies.
- **Leak check: 0 of 120 runs used any input dated after the cutoff.**
- Verdict mapping: *approve* = the signal is in the setup's direction; *veto* = it opposes the setup; *neutral*; *abstain* = no usable filings or an error.
- Outcome = the **active policy**: longs use chandelier 4×ATR14 (close) and sell ½ at Fib 1.618 (`tg_ch_HY2_c`); shorts use chandelier 4×ATR14 (`chand4_c`). Costs are 0.02% + 0.05% per side, entry is the next open after the cutoff, and open trades are marked at the 7.10 close. *x SPY* is measured over the same window (shorts: return + SPY return).
- **83% of these trades are still open**, so these are marks, not final results.

**Verdict counts (60 setups each).**

| persona | approve | neutral | veto | abstain/no data |
|---|---|---|---|---|
| Druckenmiller | **0** | 45 (75%) | 6 (3 longs, 3 shorts) | 9 |
| Buffett | 1 (HPQ short) | 51 (85%) | **0** | 8 |

The two personas give the same verdict on 52 of 60 setups: 44 both neutral and 8 both no-data. All 6 of Druckenmiller's vetoes were neutral for Buffett, and Buffett's single approval was neutral for Druckenmiller.

**Outcome by verdict (active policy, % per trade).**

| group | N | mean | median | hit % | x SPY mean | x SPY median |
|---|---|---|---|---|---|---|
| All 60 (no filter) | 60 | +1.48 | +1.01 | 57 | +1.35 | +0.73 |
| — longs / shorts | 31 / 29 | +2.43 / +0.46 | +0.47 / +2.24 | 58 / 55 | +1.16 / +1.56 | −0.97 / +2.73 |
| Druckenmiller veto | 6 | +1.10 | +3.54 | 67 | +1.10 | +3.82 |
| Druckenmiller neutral | 45 | +0.87 | −0.33 | 49 | +0.73 | −0.43 |
| Druckenmiller "keep all but vetoed" | 54 | +1.52 | +0.73 | 56 | +1.38 | +0.68 |
| Buffett neutral | 51 | +1.09 | +0.38 | 53 | +0.97 | +0.42 |
| Buffett approve (HPQ short) | 1 | −0.33 | — | 0 | +0.73 | — |
| no data (either persona) | 8–9 | +4.2 to +4.8 | +3.4 to +4.5 | 88–89 | +3.9 to +4.7 | — |
| *Context: all 431 stock setups in the main sheet* | 431 | +1.38 | +0.02 | 50 | +1.25 | −0.43 |

- **Druckenmiller vetoes:** 4 of the 6 vetoed trades made money: MU long +19.0%, MU long +4.8%, CHTR short +7.7% and VRT short +2.2%. The other two lost: TSLA short −2.8% and LCID long −24.4%. Vetoed vs the rest, Mann-Whitney p = 0.57 overall (0.83 longs, 0.87 shorts). Removing the vetoed trades changes the mean by +0.04 pp, which is nothing.
- **Approvals:** neither persona made enough to test. Druckenmiller made 0 and Buffett made 1.
- **The "no data" group did best,** but that comes from data coverage, not from the agent. It is made up of ETFs (SPY, QQQ), a closed-end fund (CLM) and foreign or IFRS filers without US-GAAP XBRL (INTR, STNE, TME, MNDY, SRAD). Neutral vs no-data has p = 0.09, which is not something to act on.
- **Statistical power:** the return SD is about 12.4 pp per trade. With 6 vetoes, only a difference of roughly 15 pp would be detectable (80% power, α = 0.05). Even the laptop's full run (~442 setups, if ~10% are vetoed) can only detect about 5–6 pp. All of this is in-sample: the same 60 setups were used to build the mapping, and nothing here has been checked on setups from 12.10 onward.
- **Reading:** the 3B model produces "neutral" by default. It does not form a view from 8 quarters of EDGAR data. In the laptop smoke test, the 7B model gave real directional calls on both setups it ran. So the laptop run is the real test, and the box result says nothing about whether a 7B or API model would help.
- **Timing:** median 23–24 s per setup on the contended box CPU (load average 14–80). One call per setup used ~1.1–1.2k prompt tokens and ~120–140 output tokens.

**TradingAgents on the box (Qwen2.5-3B, market + fundamentals analysts, 1 debate round + 1 risk round, 500-token cap): anecdotal only.**
TA_PLACEHOLDER

### 7b. API cost: running these agents daily on ~10 setups via OpenRouter

Prices come from OpenRouter's public model list, `https://openrouter.ai/api/v1/models`, pulled on 8.10.2026. The snapshot is in `cost/openrouter_models_2026-10-08.json`, and the Claude Sonnet 5.5 price was cross-checked on https://openrouter.ai/anthropic/claude-sonnet-5.5 ($2 in / $10 out per M; thinking is always on, and thinking tokens bill as output). Script: `cost/api_cost.py`. A month is counted as 21 trading days.

Token budgets per setup:
- **aihf:** 2 personas × 1.3k input (measured ~1.2k with the Qwen tokenizer, +10% for other tokenizers). Output is 0.15k per persona without thinking, or ~1.5k if the model thinks.
- **TradingAgents:** the measured run used **41.1k input / 5.9k output** (14 calls, 2 analysts, 500-token cap per call). A strong model without the cap writes full reports, which are re-fed into the debate, manager, trader and risk prompts, and it thinks. **Assumption:** ~120k input / ~25k output per setup.

| scenario (10 setups/day) | Claude Sonnet 5.5 ($2/$10) | GPT-5.6 Sol ($2/$10) | Claude Sonnet 4.6 ($3/$15) | Grok 4.7 ($2/$6) | Claude Opus 5.5 ($4/$20) | Gemini 3.8 Flash ($0.75/$3.75) | DeepSeek V3.2 ($0.26/$0.42) |
|---|---|---|---|---|---|---|---|
| aihf 2 personas, no thinking | $0.08/day · $2/mo | $0.08 · $2 | $0.12 · $3 | $0.07 · $1 | $0.16 · $3 | $0.03 · $1 | $0.01 · <$1 |
| aihf 2 personas, with thinking | $0.35/day · $7/mo | $0.35 · $7 | $0.53 · $11 | $0.23 · $5 | $0.70 · $15 | $0.13 · $3 | $0.02 · <$1 |
| TradingAgents, as measured (41k/5.9k) | $1.41/day · $30/mo | $1.41 · $30 | $2.12 · $44 | $1.18 · $25 | $2.82 · $59 | $0.53 · $11 | $0.13 · $3 |
| TradingAgents, strong model realistic (120k/25k) | **$4.90/day · $103/mo** | $4.90 · $103 | $7.35 · $154 | $3.90 · $82 | $9.80 · $206 | $1.84 · $39 | $0.42 · $9 |

**Per setup and per full scan (~110 tickers)** (script `cost/api_cost2.py`; aihf counted with thinking, which is the upper end; aihf only applies to stocks, so a mixed scan costs less):

| model ($ in/out per M) | aihf 2 personas (thinking, 2x1.3k in / 1.5k out): per setup · per 110-ticker scan | TA measured (41.1k/5.9k): per setup · per 110-ticker scan | TA strong realistic (120k/25k): per setup · per 110-ticker scan |
|---|---|---|---|
| Claude Sonnet 5.5 ($2/$10) | $0.035 · $3.87 | $0.141 · $15.53 | $0.490 · $53.90 |
| Claude Sonnet 4.6 ($3/$15) | $0.053 · $5.81 | $0.212 · $23.30 | $0.735 · $80.85 |
| Claude Opus 5.5 ($4/$20) | $0.070 · $7.74 | $0.282 · $31.06 | $0.980 · $107.80 |
| GPT-5.6 Sol ($2/$10) | $0.035 · $3.87 | $0.141 · $15.53 | $0.490 · $53.90 |
| GPT-5.5 ($5/$30) | $0.103 · $11.33 | $0.383 · $42.08 | $1.350 · $148.50 |
| Grok 4.7 ($2/$6) | $0.023 · $2.55 | $0.118 · $12.94 | $0.390 · $42.90 |
| Grok 4.3 ($1.25/$2.5) | $0.011 · $1.18 | $0.066 · $7.27 | $0.212 · $23.38 |
| Gemini 3.8 Flash ($0.75/$3.75) | $0.013 · $1.45 | $0.053 · $5.82 | $0.184 · $20.21 |
| DeepSeek V3.2 ($0.259/$0.42) | $0.002 · $0.21 | $0.013 · $1.44 | $0.042 · $4.57 |


- **Against the $15 spend limit on the OpenRouter key:**
  - The aihf personas with Sonnet 5.5 or GPT-5.6 Sol cost about $0.10–0.35 a day. $15 lasts 2–7 months.
  - TradingAgents with a Sonnet-class model would use the $15 in **~3 trading days** at 10 setups a day under the realistic budget, or ~10 days under the measured one. **One full 110-ticker scan with TradingAgents on Sonnet 5.5 or GPT-5.6 Sol (≈$16–54) already exceeds the $15 limit.** The aihf personas on a full scan cost ≈$1–4 with Claude, GPT or Grok, or ≈$11 on GPT-5.5.
  - The same key also pays for שוק ההון's Perplexity Sonar and Claude devil's-advocate layer in the scan, so these costs come on top of that.
- **Cheaper mixes:** TradingAgents can use a cheap "quick" model for the analysts and bull/bear rounds, and a strong "deep" model only for the research manager and the risk judge. That should cut roughly 60–70% of the cost. Gemini 3.8 Flash and DeepSeek V3.2 run the whole graph for $0.4–1.8 a day.
- **Backtest on 60 setups with a strong model,** for comparison (one-off): aihf both personas ≈ $0.5–2; TradingAgents ≈ $8–30 with Sonnet 5.5, which is beyond the $15 limit unless it is capped to ~30 setups or a cheaper model is used.
- **Local on the laptop (RTX 4070 8 GB, Qwen2.5-7B Q4):** $0 apart from electricity.
  - aihf: ~6–10 s per persona call (smoke test). 10 setups × 2 personas ≈ 2–4 min.
  - TradingAgents: ~3–4.5 min per setup (estimate). 10 setups ≈ 40–55 min.
  - The nightly 23:00–08:00 queue (from 8.10) first runs aihf Druckenmiller + Buffett on ~442 stock setups, then TradingAgents on 831 setups. It should finish around 16.10; about 40% will be ready by the Monday 12.10 scan.
  - A 7B model is much weaker than Sonnet-class. That is the trade-off: local is free and unlimited, while the API is stronger but metered.

**Recommendation.**
1. Don't add any aihf or TradingAgents column from the box run.
2. Read the laptop's 7B results (Druckenmiller / Buffett on ~442 stock setups) under the same FDR and robustness rules before deciding anything. If a persona produces enough directional calls (≥30 vetoes or approvals) and they separate outcomes after FDR, add it as a weight-0 documentation column from 12.10. It earns weight only if it holds on out-of-sample setups.
3. If an API model is wanted, the cheap test is the aihf personas with Sonnet 5.5 or GPT-5.6 Sol on the same 60 setups (≈$1–2). Don't run TradingAgents on the API daily under a $15 limit.
