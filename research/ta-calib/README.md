# Calibrated TradingAgents (built 2026-10-08) - box workspace
Runs ONLY on LAPTOP-ROK5URJ4 (C:\ta-backtest), nightly 23:00-08:00 as queue step `ta_calib`. No LLM run on the box.
- build_calib_data.py  -> setups_calib.csv (PIT runner input), lessons_pool.csv (calibration-half closed trades),
                          outcomes_calib.csv (box-only, active policy capped at 20 bars), split.md (protocol)
- calib_prompt.py      prompt/context/lessons/JSON parsing (shared with the laptop)
- run_calibrated.py    laptop runner (copied to C:\ta-backtest)
- calib_eval.py        theta on calibration half; ONE-TIME holdout eval (holdout_lock.json); BH-FDR + clustered p
- table20.py           table of the manual 20-setup plain run -> table20.csv
- deploy/              edited run_queue.py / stop_night.ps1 / status.ps1 / README.md as deployed
- laptop_snapshot/     laptop files before the change (also on the laptop: backup_pre_calib_20261008-1629\)
Evaluate: copy C:\ta-backtest\results\results_calib.jsonl here, then
  /workspace/venv-openbb/bin/python calib_eval.py --results results_calib.jsonl
