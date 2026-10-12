#!/usr/bin/env python3
"""Download published scanner research to a Windows folder using authenticated gh.

Works on other OSes for verification. No deletion or execution of downloaded code.
Raw data arrives only after the Linux bot runs publish_research_archive.py.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'modules'))
from scanner_artifact_archive import restore, sha

REPO = 'perezami-arch/stock-scanner'
TAG = re.compile(r'^scanner-data-[0-9a-f]{20}$')


def download(tag, asset, folder):
    if not TAG.fullmatch(tag): raise ValueError('Unexpected archive tag')
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    target = folder/asset
    expected = asset[7:-4] if re.fullmatch(r'bundle-[0-9a-f]{64}\.zip', asset) else None
    if not target.exists() or (expected and sha(target) != expected):
        with tempfile.TemporaryDirectory(dir=folder, prefix='partial-') as scratch:
            subprocess.run(['gh', 'release', 'download', tag, '--repo', REPO, '--pattern', asset, '--dir', scratch], check=True)
            fresh = Path(scratch)/asset
            if expected and sha(fresh) != expected: raise ValueError('Downloaded archive checksum mismatch')
            fresh.replace(target)
    return target


def sync(destination):
    destination = Path(destination); destination.mkdir(parents=True, exist_ok=True)
    raw = subprocess.check_output(['gh', 'api', f'repos/{REPO}/releases', '--paginate',
                                   '--jq', '.[] | select(.draft == false) | .tag_name'], text=True)
    tags = [t for t in raw.splitlines() if TAG.fullmatch(t)]
    if not tags:
        result = {'status': 'waiting_for_linux_archive', 'files_downloaded': 0,
                  'reason': 'No published data archive from the Linux bot yet'}
    else:
        # Release API ordering is not a clock. Use the manifest generation chain.
        manifests = []
        for tag in tags:
            path = download(tag, 'manifest.json', destination/'archives'/tag)
            manifest = json.loads(path.read_text(encoding='utf-8'))
            if manifest['tag'] != tag: raise ValueError('Manifest/release identity mismatch')
            manifests.append(manifest)
        manifests.sort(key=lambda m: m['generation'])
        for i,m in enumerate(manifests):
            if m['generation'] != i+1 or m.get('parent_tag') != (manifests[i-1]['tag'] if i else None):
                raise ValueError('Incomplete or forked archive history; refusing to reorder versions')
        copied = unchanged = 0
        state_path = destination/'sync-state.json'
        state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {'applied': []}
        known = set(state['applied'])
        for manifest in manifests:
            tag = manifest['tag']
            if tag in known: continue
            def fetch(t, asset): return download(t, asset, destination/'archives'/t)
            result = restore(manifest, destination/'bot-data', fetch)
            copied += result['copied']; unchanged += result['unchanged']
            known.add(tag)
            state['applied'] = [m['tag'] for m in manifests if m['tag'] in known]
            tmp = state_path.with_suffix('.tmp'); tmp.write_text(json.dumps(state, indent=2)+'\n', encoding='utf-8'); tmp.replace(state_path)
        # Verify the latest local manifest on every run, including previous runs
        # whose cursor is already saved. A missing/corrupt file is repaired.
        latest = manifests[-1]
        verified = restore(latest, destination/'bot-data', lambda t,a: download(t,a,destination/'archives'/t))
        result = {'status': 'synced', 'latest_tag': latest['tag'], 'copied': copied+verified['copied'],
                  'verified_files': verified['files'], 'applied_releases': len(known)}
    (destination/'last-sync.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--destination', required=True)
    a = ap.parse_args()
    print(json.dumps(sync(a.destination), ensure_ascii=False))


if __name__ == '__main__': main()
