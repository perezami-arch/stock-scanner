#!/bin/sh
# Takes over from driver5 (resumable; each step skips finished items).
cd /workspace/fin-llm-eval
O=$HOME/ollama/bin/ollama; PY=TradingAgents/.venv/bin/python
export OLLAMA_HOST=127.0.0.1:11434 MAXTOK=500
while kill -0 2691010 2>/dev/null; do sleep 15; done
rm -f backtest/STOP; $O stop qwen25-3b-agent4; sleep 3
python3 backtest/analyze2.py >/dev/null 2>&1
bt(){ echo "BT $1-$2 start $(date)"; $PY backtest/run_backtest.py qwen25-3b-agent4 $1 $2 >> backtest/bt.log 2>&1; $O stop qwen25-3b-agent4; sleep 3; python3 backtest/analyze2.py >/dev/null 2>&1; echo "BT $1-$2 end $(date)"; }
ev(){ echo "EVAL $1 start $(date)"; for a in 1 2 3; do NT=4 python3 eval/run_eval.py $1 results/$1.json 1500 $2 >> results/$1.log 2>&1 && break; echo "attempt $a failed" >> results/$1.log; sleep 20; done; $O stop $1; sleep 3; python3 eval/score.py > results/score.txt 2>&1; echo "EVAL $1 end $(date)"; }
ev fin-r1-q4km
bt 1 4
SUB=rev_growth,gross_margin,eps,fcf_margin,netdebt_ebitda,tax_rate,roe_avg,gm_pp,cagr,conv
ev dianjin-r1-7b-q4km $SUB
ev finance-r1-7b-q4km $SUB
bt 4 60
echo ALL_DONE $(date)
