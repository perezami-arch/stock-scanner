#!/bin/bash
# Box-only scheduler (the box has no cron). Wakes at 00:30 and 04:30 Asia/Jerusalem every night and runs run_nightly.sh
# (the 04:30 wake is a retry; it does nothing if both predictions already exist). Started by start_nightly.sh with nohup.
# DOES NOT SURVIVE A BOX REBOOT - restart with:  bash /workspace/research_nightly/start_nightly.sh
export TZ=Asia/Jerusalem
while true; do
  now=$(date +%s); next=""
  for t in "today 00:30" "today 04:30" "tomorrow 00:30"; do
    s=$(date -d "$t" +%s); if [ $s -gt $((now + 30)) ]; then next=$s; break; fi
  done
  echo "$(date) next run $(date -d @$next)" > /workspace/research-models/logs/nightly_loop.next
  sleep $((next - now))
  bash /workspace/research_nightly/run_nightly.sh
done
