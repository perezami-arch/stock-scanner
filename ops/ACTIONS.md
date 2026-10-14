# Running the scanner from GitHub Actions

## Workflows
| File | Trigger | What it runs |
|---|---|---|
| `weekly.yml` | Mon 09:00 Israel (crons `0 6 * * 1` + `0 7 * * 1`, gated) · manual · PR (dry) | `run_unified_scan.py` (all models, up to 20 by score) |
| `daily.yml` | weekdays 08:24 Israel (crons `24 5 * * 1-5` + `24 6 * * 1-5`, gated) · manual · PR (dry) | `run_unified_scan.py --paper --no-models` then `run_daily_report.py` |
| `_scan.yml` | reusable | layout → state restore → run → reports → state save |

* **DST:** both crons fire; `ops/gate.py` runs only the one where *cron UTC hour + today's Israel offset = target hour*. Start delays don't matter.
* **Schedules are commented out** until Ilan approves; enable by uncommenting `schedule:` on `main`.
* **Concurrency:** group `stock-scanner-state`, no cancel – weekly and daily never overlap.
* **Dry mode** (default for manual runs, always for PRs): paper scan, `--no-models`, no commits, outputs as a workflow artifact.

## Layout
The code imports flat modules from `$SCANNER_ROOT` (default `/workspace` on the box). `ops/materialize_root.sh` copies the repo into that flat
layout on the runner (`$GITHUB_WORKSPACE/runtime`), so the code runs unchanged.

## State (`state` branch)
An orphan branch `state` holds only what the next run needs (`ops/state.py`, allowlist, 5 MB per-file cap):
positions registry, platform verdict ledgers (live + trial), paper ledger, frozen crypto shorts, checkpoint CSV/JSON, `prompts/` (lessons),
`x-cache/` (last 14 days), the newest `scan-tracker-*.xlsx`, momentum `sector_map/name_map`, momentum reference CSVs, FINRA SI + float.
Not state (rebuilt each run from Yahoo/Alpaca): price pickles, momentum/levels/geometry caches, `regsho`, `news-cache`, run folders.
Restore before the run, save after a successful non-dry run, one commit per run on `state` (history = audit trail).

## Reports
Successful non-dry runs commit small outputs to `reports/YYYY-MM-DD/<weekly|daily>/<run>/` on the branch they ran on (main when scheduled):
Hebrew MD/PDF, charts, `candidates_full.csv`, levels JSON. Raw bars, `platform_raw.json` and logs stay in the 30-day artifact.
There is no chat delivery from Actions; the bot picks reports up from the repo.

## Secrets (repo → Settings → Secrets → Actions)
`XAI_API_KEY`, `OPENROUTER_API_KEY`, `ALPACA_API_KEY_ID`, `ALPACA_API_SECRET_KEY`, `FRED_API_KEY`.

## TradingAgents
Stays on the laptop (Ollama). Only its result files are uploaded to the repo (e.g. `research/tradingagents/results/`).
