# Laptop package (Windows, RTX 4070 8 GB) — Fin-R1 vs Qwen2.5-7B + TradingAgents over all scanner setups

Nothing here installs anything system-wide except two Ollama models (~4.7 GB each) and a Python venv inside this folder.

## What it runs (in order, all resumable)
1. **fin_eval** — the same 20-item financial-statement calculation test used on the box, for **Qwen2.5-7B-Instruct Q4_K_M** and **Fin-R1 Q4_K_M** (same quantization, both ~4.7 GB, one model in VRAM at a time). Output: `results\fin_eval_summary.json` (score, tokens/s, `ollama ps` line proving 100% GPU). ~10-30 min.
2. **ta_qwen** — TradingAgents on all 832 runnable setups (`setups_846.csv`; 11 dup_not_counted + 3 without cutoff are skipped), Qwen2.5-7B for every agent. Setups run in the same stratified **priority order** as the box sample, so a partial run is still balanced across sources/directions. Output: `results\results.jsonl`, one line per setup.
3. **ta_finr1deep** — same pipeline on the first 120 setups, but Fin-R1 as the "deep" model (research manager + portfolio manager). Gives a like-for-like Qwen vs Fin-R1 comparison on identical setups. Output: `results\results_finr1deep.jsonl`.

`trade_date` in `setups_846.csv` is already the point-in-time cutoff bar (pre/intra-session alerts → previous close; after-close → alert-day close; crypto → previous complete UTC day; Perplexity task-list times moved 70 min earlier). TradingAgents' tools return nothing after that date (verified on the box, see ../results.md §3).

4. **aihf personas (optional, separate venv)** — ai-hedge-fund's Druckenmiller / Buffett LLM agents in *blind* backtest mode, as an approve/veto filter on the **stock** setups only. ai-hedge-fund normally needs a paid Financial Datasets key; `aihf/edgar_client.py` replaces it with SEC EDGAR filings *as filed by the cutoff date* + Yahoo closes up to the cutoff (same code as the box run, every input date logged and checked against the cutoff). One LLM call per setup. Output: `results\aihf_<persona>_<model>.jsonl`. On the box a 3B model answered "neutral" almost every time, so the 7B run here is the real test.

## Steps
1. Copy this folder to e.g. `C:\ta-backtest\`, open PowerShell there.
2. `powershell -ExecutionPolicy Bypass -File setup.ps1` — venv + TradingAgents (pinned commit), sets `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_MAX_LOADED_MODELS=1` (asks you to restart Ollama), pulls both Q4_K_M models, creates `qwen25-7b-q4km`, `fin-r1-q4km`, `qwen25-ta`, `fin-r1-ta`, runs one setup as a smoke test. `ollama ps` must show **100% GPU**.
3. `powershell -ExecutionPolicy Bypass -File launch.ps1` — registers Scheduled Task `TradingAgentsBacktest` that runs `pythonw run_queue.py` detached and re-fires every 15 min (watchdog). Survives the remote shell being cut (~14 min), sleep/wake and reboot: a lock file prevents double runs, finished items are skipped, each setup has its own child process with a hard timeout and up to 3 attempts.
4. Optional: `powershell -ExecutionPolicy Bypass -File setup_aihf.ps1` (ai-hedge-fund persona filter; own venv, runs a 2-setup smoke test and prints the full-run commands). Run it while the TradingAgents queue is stopped (`stop.ps1`) or after it finishes — both use the same GPU.
5. Check: `status.ps1`. Summaries: `.venv\Scripts\python fin_eval.py --score`, `.venv\Scripts\python summarize.py`.
6. Stop: `stop.ps1` (results kept; `launch.ps1` resumes).

## VRAM budget (8 GB)
7B Q4_K_M weights 4.7 GB + 16k-token KV cache ≈ 0.5 GB at q8_0 (≈0.9 GB at f16) + ~0.5 GB buffers ≈ 5.7-6.1 GB. Windows desktop takes ~0.5-1 GB. If `ollama ps` shows a CPU/GPU split, set `num_ctx 8192` in `Modelfile`/`Modelfile.finr1` and re-run `ollama create`.

## Expected time (estimate, not measured on this laptop)
Measured on the box (CPU, Qwen2.5-3B): one full TradingAgents stock setup = 14 LLM calls, 41k prompt + 5.9k output tokens, 28 min. On the RTX 4070 Laptop (8 GB VRAM, 32 GB RAM) a 7B Q4_K_M model sits fully in VRAM: ~35-45 tok/s generation, ~1,500-2,500 tok/s prompt → **~3-4.5 min per setup**, so all 832 setups ≈ 45-60 h (3-4 nights) and a daily scan (~17 setups) ≈ 45-65 min. The Fin-R1-deep pass on 120 setups ≈ 8-12 h more (Fin-R1 writes longer reasoning). The optional aihf persona step is one call per stock setup: ~5 s each, all 442 stock setups ≈ 30-60 min. 14B models spill into system RAM (~3× slower); 32B models are impractical on 8 GB VRAM.

## Notes
- No API keys needed: prices from Yahoo, statements from SEC EDGAR as filed by the trade date. News/social/insider/profile feeds are withheld by TradingAgents for past dates, so only the market (+fundamentals for stocks) analysts run.
- Per-call output is hard-capped in the Modelfiles (`num_predict` 1500 for Qwen, 3000 for Fin-R1). On the box a TradingAgents free-text retry ignored `max_tokens` and a small model looped for 11,900 tokens; the Modelfile cap prevents that. The 45-min per-setup timeout is the second safety net.
- The box sample (../tracker_backtest.md) used a 3B model and a 500-token cap because the box has no GPU; the laptop run is the real test.

## NIGHTLY MODE (active since 2026-10-08) - use this, not launch.ps1
Approved schedule: only 23:00-08:00, AC power only. `launch.ps1` would start a 24/7 run immediately - don't use it.
- Task `TA-Backtest-Night-Start`: daily 23:00, re-fires every 15 min until 07:45 (watchdog; lock prevents doubles),
  wake-to-run on, AC only (won't start on battery, stops if unplugged), runs only while user amira is logged on
  (Interactive: no stored password, and Ollama runs in the user session). Runs `pythonw run_queue.py --night 23:00-08:00`.
- Queue order: fin_eval (already done) -> aihf druckenmiller -> aihf buffett (all stock setups) -> ta_qwen (832) -> ta_finr1deep (120).
- Night guard (`nightwin.py`): no new TA setup starts with < 10 min left (i.e. after ~07:50), no aihf item with < 2 min,
  none on battery or if `results\STOP` exists. Exit code 3 = paused; resumes next night.
- Task `TA-Backtest-Night-Stop`: daily 08:00 (runs late on wake if missed) -> `stop_night.ps1`: kills the runner
  processes (parents first, so nothing partial is recorded) and `ollama stop`s only qwen25-ta / fin-r1-ta / qwen25-7b-q4km / fin-r1-q4km.
- Resume: results are append-only JSONL, one fsynced line per setup; finished setup_ids are skipped; a setup killed at 08:00
  writes nothing, doesn't count as an attempt, and is redone first next night. Unterminated fragments are tolerated.
- Manual: `status.ps1`; `stop.ps1` (stop now), `stop.ps1 -Disable` / `-Enable` (pause/resume the schedule).
- Originals before this change: `backup_pre_nightly\`.

## CALIBRATED TradingAgents (added 2026-10-08, approved by Ilan) - nightly step `ta_calib`
- Replaces the plain `ta_qwen` step in the nightly queue (plain results in `results\results.jsonl` are kept untouched).
  Queue now: fin_eval (done) -> aihf druckenmiller -> aihf buffett -> **ta_calib** (832) -> ta_finr1deep (120, plain).
- `run_calibrated.py` + `calib_prompt.py`: every agent sees the full setup (direction, reference entry, active-policy stop
  4xATR14 chandelier for stocks / fixed 3xATR14 for crypto, half at fib 1.618 for stock longs, 20-day horizon) and the
  scanner context (ck_score, SMA200, sector uptrend, VA120, stop distance in ATR, rule pass), all as of the cutoff bar
  (`setups_calib.csv`). A final "setup judge" call returns JSON {verdict approve|veto|neutral, p_success, reason}, with
  up to 6 closed trades from the calibration half whose result was known before the cutoff (`lessons_pool.csv`).
- Output: `results\results_calib.jsonl` (one fsynced line per setup), `results\progress_calib.log`,
  `results\attempts_calib.json` (atomic). Same night/AC/STOP guard, keepawake, 45-min child timeout, 3 attempts.
- Dry run (no LLM, safe any time): `.venv\Scripts\python run_calibrated.py --dry-run`
  (with `$env:NIGHT_WINDOW='23:00-08:00'` it must print "not starting: night window" outside 23:00-07:50).
- Calibration/holdout split and evaluation protocol: `split.md` (evaluation runs on the box: calib_eval.py).
- `stop_night.ps1` also kills `run_calibrated.py`. Backup of the files changed: `backup_pre_calib_<stamp>\`.
