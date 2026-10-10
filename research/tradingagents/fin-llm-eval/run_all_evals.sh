#!/bin/sh
cd /workspace/fin-llm-eval
for m in qwen25-7b-q4km fin-r1-q4km dianjin-r1-7b-q4km finance-r1-7b-q4km; do
  for attempt in 1 2 3; do
    NT=4 python3 eval/run_eval.py $m results/$m.json 1200 >> results/$m.log 2>&1 && break
    echo "attempt $attempt failed" >> results/$m.log; sleep 20
  done
  $HOME/ollama/bin/ollama stop $m; sleep 3
done
echo ALL_EVALS_DONE
