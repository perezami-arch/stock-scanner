#!/usr/bin/env python3
"""Validate/install this repository snapshot onto the EXISTING /workspace bot.

Default checks only. --apply backs up replaced files before copying. Does not
install dependencies, credentials, timers or overwrite market data/registries.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    repo = Path(__file__).resolve().parents[1]
    target = Path('/workspace').resolve()
    required = ['scanner-tool-eval/pit.py', 'scanner-tool-eval/tools/base.py',
                'trading-frameworks-eval/iaf/sim_fib.py', 'trading-frameworks-eval/iaf/prep.py']
    missing = [name for name in required if not (target/name).is_file()]
    if missing:
        raise SystemExit('Missing live bot dependencies: '+', '.join(missing))
    pairs = [(p, target/p.name) for p in (repo/'scanner').glob('*.py')]
    pairs += [(p, target/p.name) for p in (repo/'modules').glob('*.py') if p.name != 'stop_rules.py']
    pairs += [(repo/'scanner/levels_schema.json', target/'levels_schema.json')]
    pairs += [(p, target/'research/jewish-lunar'/p.relative_to(repo/'research/jewish-lunar'))
              for p in (repo/'research/jewish-lunar').rglob('*') if p.is_file() and 'progress' not in p.parts]
    if not a.apply:
        print(f'Preflight OK: {len(pairs)} files ready. Run with --apply after disabling the old scanner schedule.'); return
    backup = target/'scanner-code-backups'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    for src, dst in pairs:
        if target not in dst.resolve().parents:
            raise ValueError('Destination escaped /workspace')
        if dst.exists():
            old = backup/dst.relative_to(target); old.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, old)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    print(f'Installed {len(pairs)} files. Prior files backed up at {backup}. Timers not yet enabled.')


if __name__ == '__main__': main()
