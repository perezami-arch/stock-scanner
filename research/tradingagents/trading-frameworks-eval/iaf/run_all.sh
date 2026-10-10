#!/bin/bash
export POLARS_MAX_THREADS=2
for a in stock crypto; do for p in hold fsetup f8 t5 t8 t12; do
  [ -f meta_${a}_${p}.json ] && [ "$a$p" != "stockt5" ] && continue
  ../venv-iaf8/bin/python run_iaf.py $a $p > log_${a}_${p}.txt 2>&1; echo "$a $p exit $?"; tail -1 log_${a}_${p}.txt
done; done
echo ALLDONE
