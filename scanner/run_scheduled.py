#!/usr/bin/env python3
"""Linux bot wrapper: Monday 50-name scan and daily follow-up, with durable lock.

No remote deployment on import. Scheduled invocations use the bot's interpreter
and existing credentials/budgets; publishing uses its authenticated git account.
"""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from zoneinfo import ZoneInfo


def commands(kind, python=sys.executable):
    if kind == 'weekly':
        return [[python, '/workspace/run_unified_scan.py', '--candidates', '50', '--research-weight', '0.30']]
    if kind == 'daily':
        return [[python, '/workspace/run_unified_scan.py', '--paper', '--no-models', '--candidates', '50', '--research-weight', '0.30'],
                [python, '/workspace/run_daily_report.py']]
    raise ValueError('Unknown scheduled job')


def publish_progress(repo, daily_dir, date):
    """Publish only generated follow-up/research summaries; never keys or raw bars.

    Requires a dedicated clean checkout on main, a configured author and origin.
    No force-push, reset, stash, broad staging, or automatic conflict resolution.
    """
    repo = Path(repo).resolve()
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()
    if git('remote', 'get-url', 'origin') not in ('https://github.com/perezami-arch/stock-scanner.git', 'git@github.com:perezami-arch/stock-scanner.git'):
        raise ValueError('Unexpected publication repository')
    if git('branch', '--show-current') != 'main' or git('status', '--porcelain'):
        raise ValueError('Progress publisher requires a clean main checkout')
    git('pull', '--ff-only', 'origin', 'main')
    target = repo/'research/jewish-lunar/progress'/date
    target.mkdir(parents=True, exist_ok=True)
    files = ('research_progress.json', 'research_progress_he.md', 'followup/trade_followup.json', 'followup/trade_followup_he.md')
    paths = []
    for name in files:
        src = Path(daily_dir)/name
        if not src.is_file():
            raise FileNotFoundError(f'Incomplete daily report: {src}')
    for name in files:
        dst = target/Path(name).name
        shutil.copy2(Path(daily_dir)/name, dst)
        paths.append(dst.relative_to(repo).as_posix())
    git('add', '--', *paths)
    if git('diff', '--cached', '--name-only'):
        git('commit', '-m', f'Record daily research and trade follow-up {date}', '--', *paths)
    git('push', 'origin', 'main')  # failed push remains recoverable locally; never rewrite remote history


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('kind', choices=['weekly', 'daily'])
    ap.add_argument('--repo', default='/workspace/stock-scanner')
    ap.add_argument('--publish-progress', action='store_true')
    ap.add_argument('--archive-data', action='store_true', help='private data archives for verified Windows synchronization')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    now = datetime.now(ZoneInfo('Asia/Jerusalem')); day = now.date().isoformat()
    cmds = commands(a.kind)
    if a.dry_run:
        print(json.dumps({'timezone': 'Asia/Jerusalem', 'kind': a.kind, 'commands': cmds,
                          'publish_progress': a.publish_progress, 'archive_data': a.archive_data}, indent=2)); return
    if a.kind == 'weekly' and now.weekday() != 0:
        raise SystemExit('Weekly scheduled job only runs on Monday (Asia/Jerusalem)')
    state = Path('/workspace/scan-runs/schedule'); state.mkdir(parents=True, exist_ok=True)
    import fcntl
    with (state/'scanner.lock').open('a') as lock:
        # Serialise weekly/daily jobs; Monday daily may take longer than 36 min.
        fcntl.flock(lock, fcntl.LOCK_EX)
        marker = state/f'{day}-{a.kind}.json'
        saved = json.loads(marker.read_text()) if marker.exists() else {'completed_steps': []}
        if saved.get('status') == 'complete':
            print('Already completed', marker.name); return
        # Before scoring, cover today's Hebrew day (including the next civil day
        # after sunset on the last day of a month). Keep existing monthly files.
        try:
            from ensure_research_calendar import generate
            next_month = f'{now.year + (now.month == 12):04d}-{now.month % 12 + 1:02d}'
            for month in {now.strftime('%Y-%m'), next_month}:
                y, m = map(int, month.split('-'))
                generate(y, m, '/workspace/research/jewish-lunar/data', '/workspace/research/jewish-lunar/ephemeris/de440s.bsp')
            saved['calendar_status'] = 'ok'
        except Exception as exc:
            saved['calendar_status'] = f'{type(exc).__name__}: {exc}'
            # The scorer explicitly returns missing coverage allocation to baseline.
            print('Calendar extension unavailable:', saved['calendar_status'])
        for i, cmd in enumerate(cmds):
            if i in saved['completed_steps']:
                continue
            log = state/f'{day}-{a.kind}-{i}.log'
            with log.open('a', encoding='utf-8') as output:
                result = subprocess.run(cmd, cwd='/workspace', stdout=output, stderr=subprocess.STDOUT)
            saved.update(status='running', last_exit=result.returncode)
            if result.returncode == 0:
                saved['completed_steps'].append(i)
            marker.write_text(json.dumps(saved, indent=2), encoding='utf-8')
            # Always attempt daily trade review even if the new paper scan failed.
            if result.returncode and a.kind == 'weekly':
                raise SystemExit(result.returncode)
        if len(saved['completed_steps']) != len(cmds):
            raise SystemExit('One or more steps failed; see schedule logs. Daily review was still attempted.')
        if a.archive_data:
            from publish_research_archive import publish
            saved['data_archive'] = publish('/workspace', '/workspace/scanner-archives')
        if a.kind == 'daily' and a.publish_progress:
            publish_progress(a.repo, f'/workspace/scan-runs/daily/{day}', day)
        saved.update(status='complete', completed_at=now.isoformat())
        marker.write_text(json.dumps(saved, indent=2), encoding='utf-8')


if __name__ == '__main__': main()
