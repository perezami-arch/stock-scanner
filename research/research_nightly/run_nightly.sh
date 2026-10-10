#!/bin/bash
# One nightly pass for the research columns: data (system python3) -> Qlib (venv-qlib) -> FinRL (venv-finrl).
# Skips a model whose pred_<D>.csv already exists. flock: two passes never overlap. Low priority (nice) on the shared box.
set -u
R=/workspace/research-models; N=/workspace/research_nightly; G=/workspace/gh-repos-eval
mkdir -p $R/logs; LOG=$R/logs/nightly_$(date +%F_%H%M).log
exec 9>$R/nightly.lock; flock -n 9 || { echo "$(date) another nightly pass is running" >> $LOG; exit 0; }
{
  echo "=== $(date) nightly pass (box time = Asia/Jerusalem)"
  DIR=$(nice -n 10 timeout 1200 python3 $N/models_data.py ${ASOF:+--asof "$ASOF"} | tail -1)
  if [ ! -d "$DIR/src_csv" ]; then echo "data prep failed"; exit 1; fi
  D=$(basename "$DIR"); echo "bar $D -> $DIR"
  if [ -f $R/qlib/pred_$D.csv ]; then echo "qlib pred_$D exists - skip"; else
    nice -n 10 timeout 5400 $G/venv-qlib/bin/python $N/qlib_nightly.py "$DIR" 2>&1 | grep -v "^\[" | tail -5; fi
  if [ -f $R/finrl/pred_$D.csv ]; then echo "finrl pred_$D exists - skip"; else
    nice -n 10 timeout 3600 $G/venv-finrl/bin/python $N/finrl_nightly.py "$DIR" 2>&1 | tail -5; fi
  ls $R/qlib/pred_$D.csv $R/finrl/pred_$D.csv 2>&1
  ls -d $R/data/20* 2>/dev/null | head -n -10 | xargs -r rm -rf          # keep the last 10 data snapshots
  echo "=== $(date) done"
} >> $LOG 2>&1
