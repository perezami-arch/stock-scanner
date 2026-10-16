#!/usr/bin/env python3
"""Israel-time gate (16.10.2026: idempotent, schedule = fallback only).
Primary trigger: routines call workflow_dispatch on time (08:24 daily / Mon 09:00 weekly, IL).
- schedule: run only if Israel time >= target AND reports/<IL date>/<kind>/ does not exist yet (late runs still execute once).
- workflow_dispatch: run unless the report already exists; force=true always runs. dry / pull_request: always run (never commit).
Usage: gate.py <HH:MM target IL> "<github.event.schedule>" <kind> <dry true|false> <force true|false>"""
import os, sys, datetime as dt
from zoneinfo import ZoneInfo
target = sys.argv[1]; cron = (sys.argv[2] if len(sys.argv) > 2 else '').strip()
kind = sys.argv[3] if len(sys.argv) > 3 else 'daily'
dry = (sys.argv[4] if len(sys.argv) > 4 else 'false').lower() == 'true'
force = (sys.argv[5] if len(sys.argv) > 5 else 'false').lower() == 'true'
if ':' not in target: target += ':00'
now = dt.datetime.now(ZoneInfo('Asia/Jerusalem')); day = f'{now:%Y-%m-%d}'
exists = os.path.isdir(f'reports/{day}/{kind}')
th, tm = map(int, target.split(':'))
if dry: ok, why = True, 'dry/PR run'
elif force: ok, why = True, 'forced'
elif exists: ok, why = False, f'reports/{day}/{kind} already exists'
elif cron and (now.hour, now.minute) < (th, tm): ok, why = False, f'cron fired before {target} IL (other DST variant)'
else: ok, why = True, ('scheduled fallback' if cron else 'dispatch') + ', no report yet'
print(f'gate: run={ok} ({why}); Israel now {now:%Y-%m-%d %H:%M %Z}')
with open(os.environ.get('GITHUB_OUTPUT', '/dev/null'), 'a') as f:
    f.write(f'run={str(ok).lower()}\nil_date={day}\n')
