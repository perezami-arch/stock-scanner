#!/bin/bash
# (Re)start the nightly research-model loop on the box:   bash /workspace/research_nightly/start_nightly.sh
# Status:   bash /workspace/research_nightly/start_nightly.sh status      Stop:   ... stop
# Run one pass now (e.g. after a reboot or before a post-close scan):   bash /workspace/research_nightly/run_nightly.sh
P=/workspace/research-models/nightly_loop.pid; mkdir -p /workspace/research-models/logs
alive() { [ -f $P ] && kill -0 $(cat $P) 2>/dev/null && grep -q nightly_loop /proc/$(cat $P)/cmdline 2>/dev/null; }
case "${1:-start}" in
  status) if alive; then echo "running pid $(cat $P); $(cat /workspace/research-models/logs/nightly_loop.next 2>/dev/null)"; else echo "NOT running"; fi
          ls -t /workspace/research-models/qlib/pred_*.csv /workspace/research-models/finrl/pred_*.csv 2>/dev/null | head -4 ;;
  stop)   alive && kill $(cat $P) && echo stopped; rm -f $P ;;
  *)      alive && { kill $(cat $P); sleep 1; }
          nohup setsid bash /workspace/research_nightly/nightly_loop.sh > /workspace/research-models/logs/nightly_loop.out 2>&1 < /dev/null &
          echo $! > $P; sleep 1; echo "started pid $(cat $P)"; cat /workspace/research-models/logs/nightly_loop.next ;;
esac
