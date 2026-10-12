#!/usr/bin/env python3
"""Scanner state <-> the orphan `state` branch (checked out at STATE_DIR).

restore: STATE_DIR/<path> -> SCANNER_ROOT/<path>   (before the run)
save   : SCANNER_ROOT/<path> -> STATE_DIR/<path>   (after the run; allowlist only, size-capped, secrets never in scope)
Big caches (price pickles, momentum/levels/geometry caches, regsho, news-cache) are NOT state: they are rebuilt from Yahoo/Alpaca.
"""
import os, sys, glob, shutil, time
MAX_FILE = 5 * 1024 * 1024
STATE = [  # globs relative to the scanner root
    'scan-runs/positions_registry.csv',
    'scan-runs/platform_verdicts_ledger.csv', 'scan-runs/platform_verdicts_ledger_trial.csv',
    'scan-runs/paper_trades_ledger.csv', 'scan-runs/frozen_crypto_shorts.csv',
    'scan-runs/checkpoints/**/*.csv', 'scan-runs/checkpoints/**/*.json',
    'prompts/*',
    'x-cache/*/*.json',
    'scan-tracker-*.xlsx',
    'scanner-momentum-cache/sector_map.json', 'scanner-momentum-cache/name_map.json',
    'scanner-tool-eval/forecasts/mom121.csv', 'scanner-tool-eval/setups_prepared.csv',
    'short-data/finra_si.csv', 'short-data/yahoo_float.json',
    'tracker/overrides.json', 'tracker/overrides_auto.json',
]
X_CACHE_DAYS = 14

def files(base):
    out = set()
    for g in STATE:
        out.update(p for p in glob.glob(os.path.join(base, g), recursive=True) if os.path.isfile(p))
    trk = sorted(p for p in out if os.path.basename(p).startswith('scan-tracker-'))
    for p in trk[:-1]: out.discard(p)                    # only the newest tracker workbook
    cut = time.time() - X_CACHE_DAYS * 86400
    out = {p for p in out if '/x-cache/' not in p or os.path.getmtime(p) >= cut}
    return sorted(out)

def copy(src_base, dst_base, prune=False):
    n = skipped = 0
    keep = set()
    for p in files(src_base):
        rel = os.path.relpath(p, src_base)
        if os.path.getsize(p) > MAX_FILE: print('skip (too big):', rel); skipped += 1; continue
        d = os.path.join(dst_base, rel); os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy2(p, d); n += 1; keep.add(rel)
    if prune:  # drop stale state files (e.g. old tracker workbooks, x-cache days past the window)
        for p in files(dst_base):
            rel = os.path.relpath(p, dst_base)
            if rel not in keep: os.remove(p)
    print(f'{n} state files copied, {skipped} skipped')

if __name__ == '__main__':
    mode, state_dir, root = sys.argv[1], sys.argv[2], sys.argv[3]
    if mode == 'restore': copy(state_dir, root)
    elif mode == 'save': copy(root, state_dir, prune=True)
    else: sys.exit('usage: state.py restore|save STATE_DIR SCANNER_ROOT')
