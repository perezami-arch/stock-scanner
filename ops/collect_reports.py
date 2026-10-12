#!/usr/bin/env python3
"""Copy today's human-facing outputs into reports/YYYY-MM-DD/<kind>/ (small files only, no bars/raw dumps).
Usage: collect_reports.py <scanner_root> <repo_dir> <YYYY-MM-DD> <weekly|daily>"""
import os, sys, glob, shutil
root, repo, day, kind = sys.argv[1:5]
KEEP = ('.md', '.pdf', '.png', '.json', '.csv', '.html', '.txt')
SKIP_DIRS = {'bars'}; SKIP_FILES = {'platform_raw.json', 'news_alpaca.json', 'scan_stdout.log'}
MAX = 3 * 1024 * 1024
srcs = sorted(glob.glob(f'{root}/scan-runs/{day}_*')) + sorted(glob.glob(f'{root}/scan-runs/{day}[_ ]*')) 
srcs = list(dict.fromkeys(srcs)) + ([f'{root}/scan-runs/daily/{day}'] if os.path.isdir(f'{root}/scan-runs/daily/{day}') else [])
n = 0
for s in srcs:
    name = 'daily-report' if s.endswith(f'daily/{day}') else os.path.basename(s)
    for dp, dns, fns in os.walk(s):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            p = os.path.join(dp, fn)
            if not fn.endswith(KEEP) or fn in SKIP_FILES or os.path.getsize(p) > MAX: continue
            d = os.path.join(repo, 'reports', day, kind, name, os.path.relpath(p, s))
            os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy2(p, d); n += 1
print(f'{n} report files -> reports/{day}/{kind}/ from {len(srcs)} run folder(s)')
