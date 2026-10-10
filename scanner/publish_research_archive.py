#!/usr/bin/env python3
"""Publish the bot's research files as private release attachments for Windows.
No secrets, account credentials or arbitrary home-directory collection.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'modules'))
from scanner_artifact_archive import build

REPO = 'perezami-arch/stock-scanner'


def gh(*args):
    return subprocess.check_output(['gh', *args, '--repo', REPO], text=True).strip()


def publish(workspace, out):
    workspace = Path(workspace); out = Path(out); out.mkdir(parents=True, exist_ok=True)
    state = out/'last-published.json'
    previous = json.loads(state.read_text(encoding='utf-8')) if state.exists() else None
    roots = {name: workspace/name for name in ('scan-runs', 'news-cache', 'scanner-momentum-cache', 'openbb-snapshots', 'prompts')}
    roots['calendar'] = workspace/'research/jewish-lunar/data'
    manifest, path, bundles = build(roots, out, previous)
    if previous and previous['tag'] == manifest['tag']:
        return {'status': 'unchanged', 'tag': manifest['tag'], 'files': len(manifest['files'])}
    if not manifest['files']:
        return {'status': 'no_source_data', 'missing_roots': manifest['missing_roots']}
    private = subprocess.check_output(['gh', 'repo', 'view', REPO, '--json', 'isPrivate'], text=True)
    if not json.loads(private)['isPrivate']:
        raise ValueError('Research data publisher requires the private scanner repository')
    tags = json.loads(gh('release', 'list', '--limit', '1000', '--json', 'tagName'))
    tag = manifest['tag']
    if tag not in {r['tagName'] for r in tags}:
        gh('release', 'create', tag, '--draft', '--target', 'main', '--title', 'Scanner research data '+tag,
           '--notes', 'Research files for verified Windows synchronization. Manifest and SHA256-verified bundles. No credentials.', '--latest=false')
    remote = json.loads(gh('release', 'view', tag, '--json', 'assets,isDraft'))
    present = {a['name'] for a in remote['assets']}
    # Bundles are named by their content hash. A retry never replaces an asset.
    for bundle in bundles:
        if bundle.name not in present:
            gh('release', 'upload', tag, str(bundle))
    ready = out/tag; ready.mkdir(exist_ok=True)
    publish_manifest = ready/'manifest.json'; shutil.copy2(path, publish_manifest)
    if 'manifest.json' not in present:
        gh('release', 'upload', tag, str(publish_manifest))
    if remote['isDraft']:
        gh('release', 'edit', tag, '--draft=false', '--latest=false')
    # Commit the incremental cursor ONLY after every upload and publication succeeds.
    temp = state.with_suffix('.tmp'); shutil.copy2(path, temp); temp.replace(state)
    return {'status': 'published', 'tag': tag, 'files': len(manifest['files']), 'new_bundles': len(bundles)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--workspace', default='/workspace')
    ap.add_argument('--out', default='/workspace/scanner-archives')
    a = ap.parse_args()
    print(json.dumps(publish(a.workspace, a.out), ensure_ascii=False))


if __name__ == '__main__': main()
