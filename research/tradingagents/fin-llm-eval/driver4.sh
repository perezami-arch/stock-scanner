#!/bin/sh
cd /workspace/fin-llm-eval
O=$HOME/ollama/bin/ollama
PY=TradingAgents/.venv/bin/python
while kill -0 2553135 2>/dev/null; do sleep 10; done
$O stop qwen25-7b-q4km; sleep 3
echo "BT 0-3 start $(date)"
$PY backtest/run_backtest.py qwen25-7b-agent 0 3 >> backtest/bt.log 2>&1
echo "TA NVDA full start $(date)"
$PY run_ta.py NVDA 2026-10-07 qwen25-7b-agent > results/ta_NVDA.log 2>&1
echo "TA NVDA end $(date)"
$PY backtest/run_backtest.py qwen25-7b-agent 3 60 >> backtest/bt.log 2>&1
echo "BT end $(date)"
