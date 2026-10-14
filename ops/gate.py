#!/usr/bin/env python3
"""Israel-time gate for DST-proof cron. Both UTC crons (UTC+3 and UTC+2 variants) fire; only the one whose
UTC hour + today's Israel offset equals the target Israel hour runs. Robust to Actions start delays.
Usage: gate.py <target_hour_IL> "<github.event.schedule>" ; writes run=true|false to $GITHUB_OUTPUT."""
import os, sys, datetime as dt
from zoneinfo import ZoneInfo
target, cron = int(sys.argv[1]), (sys.argv[2] if len(sys.argv) > 2 else '').strip()
now = dt.datetime.now(ZoneInfo('Asia/Jerusalem'))
if not cron:            # workflow_dispatch / pull_request: always run
    ok, why = True, 'manual/PR trigger'
else:
    utc_hour = int(cron.split()[1]); off = int(now.utcoffset().total_seconds() // 3600)
    ok = (utc_hour + off) % 24 == target
    why = f'cron UTC {utc_hour:02d} + IL offset {off} -> {(utc_hour + off) % 24:02d}, target {target:02d}'
print(f'gate: run={ok} ({why}); Israel now {now:%Y-%m-%d %H:%M %Z}')
with open(os.environ.get('GITHUB_OUTPUT', '/dev/null'), 'a') as f:
    f.write(f'run={str(ok).lower()}\nil_date={now:%Y-%m-%d}\n')
