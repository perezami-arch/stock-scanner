#!/bin/sh
# Takes over from driver6 (killed 14:17). Chain: aihf druckenmiller (running) -> aihf buffett -> TradingAgents setup 2(+3 if before 15:30).
cd /workspace/fin-llm-eval
while kill -0 2814372 2>/dev/null; do sleep 10; done
echo "buffett start $(date)"
(cd ai-hedge-fund && .venv/bin/python ../aihf_bt/run_aihf.py buffett 60 > ../aihf_bt/buffett.log 2>&1)
echo "buffett end $(date)"
rm -f backtest/STOP
( while [ "$(date +%H%M)" -lt 1530 ]; do sleep 30; done; echo "deadline: no new TradingAgents setup after 15:30 ($(date))" > backtest/STOP ) &
echo "TA start $(date)"
MAXTOK=500 OLLAMA_HOST=127.0.0.1:11434 TradingAgents/.venv/bin/python backtest/run_backtest.py qwen25-3b-agent4 2 4 >> backtest/bt.log 2>&1
echo "TA end $(date)"
ai-hedge-fund/.venv/bin/python aihf_bt/analyze_filters.py > /dev/null 2>&1
echo ALL_DONE $(date)
