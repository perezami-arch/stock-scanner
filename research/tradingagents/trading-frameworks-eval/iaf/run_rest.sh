#!/bin/bash
export POLARS_MAX_THREADS=2
while ! grep -q ALLDONE run_all.log; do sleep 15; done
for p in f8 t5 t8; do
  ../venv-iaf8/bin/python run_iaf.py stock $p > log_stock_$p.txt 2>&1; echo "stock $p exit $?"; tail -1 log_stock_$p.txt
done
rm -rf saved_backtests
../venv-iaf8/bin/python run_iaf_save.py stock t8 40 > mcpdemo_cwd/demo.log 2>&1; echo "demo exit $?"; tail -2 mcpdemo_cwd/demo.log
echo RESTDONE
