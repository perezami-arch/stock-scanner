#!/bin/sh
cd /workspace/fin-llm-eval
O=$HOME/ollama/bin/ollama
while kill -0 2553135 2>/dev/null; do sleep 10; done
$O stop qwen25-7b-q4km; sleep 3
echo "TA NVDA start $(date)"
TradingAgents/.venv/bin/python run_ta.py NVDA 2026-09-01 qwen25-7b-agent > results/ta_NVDA.log 2>&1
echo "TA NVDA end $(date)"
$O stop qwen25-7b-agent; sleep 3
for m in fin-r1-q4km dianjin-r1-7b-q4km finance-r1-7b-q4km; do
  for attempt in 1 2 3; do
    NT=4 python3 eval/run_eval.py $m results/$m.json 1200 >> results/$m.log 2>&1 && break
    echo "attempt $attempt failed" >> results/$m.log; sleep 20
  done
  $O stop $m; sleep 3
  echo "$m done $(date)"
done
echo "TA AAPL start $(date)"
TradingAgents/.venv/bin/python run_ta.py AAPL 2026-09-15 qwen25-7b-agent market,fundamentals > results/ta_AAPL.log 2>&1
echo "TA AAPL end $(date)"
$O stop qwen25-7b-agent
echo ALL_DONE
