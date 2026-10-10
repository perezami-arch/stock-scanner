"""Content-addressed research archives and verified Windows restoration.

Only explicit research roots, no credentials or arbitrary /workspace backups.
Existing local versions are retained; restoration never deletes user files.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import tempfile
import zipfile

SCHEMA = 'scanner-artifacts-1'
ALLOWED = {'.json', '.csv', '.md', '.txt', '.pdf', '.png', '.jpg', '.jpeg', '.svg',
           '.html', '.xlsx', '.parquet', '.sqlite', '.py', '.bsp'}
EXCLUDE = {'.git', '__pycache__', '.venv', 'venv', 'node_modules', 'schedule', '.tmp'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def valid_digest(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def safe_path(root, name):
    """Validate using Windows-safe components even when tests run on Linux."""
    p = PurePosixPath(name)
    reserved = {'con', 'prn', 'aux', 'nul'} | {f'{a}{i}' for a in ('com', 'lpt') for i in range(1, 10)}
    if (p.is_absolute() or not p.parts or str(p) != name or any(x in ('.', '..') for x in p.parts)
            or any(any(c in x for c in '\\:<>"|?*') or x.endswith((' ', '.')) or x.split('.')[0].lower() in reserved for x in p.parts)):
        raise ValueError('Unsafe archive path')
    root = Path(root).resolve(); target = root.joinpath(*p.parts)
    if root not in target.resolve().parents:
        raise ValueError('Archive target escaped destination')
    return target


def allowed(path, root):
    relative = path.relative_to(root)
    return (path.is_file() and not path.is_symlink() and path.suffix.lower() in ALLOWED
            and not any(p in EXCLUDE or p.lower().startswith('.env') for p in relative.parts)
            and root.resolve() in path.resolve().parents
            and path.name not in ('scanner-runtime.env', 'set_routine_env.sh'))


def build(roots, out, previous=None, bundle_limit=96*1024*1024):
    """Incremental bundles; every manifest describes all retained files.

    Objects larger than bundle_limit get a dedicated bundle. SQLite is copied
    using the online backup API, so WAL contents are included consistently.
    """
    out = Path(out); objects = out/'objects'; objects.mkdir(parents=True, exist_ok=True)
    previous = previous or {'files': {}, 'objects': {}}
    files = dict(previous['files']); refs = dict(previous['objects'])
    new, missing_roots = {}, []
    for label, root in sorted(roots.items()):
        root = Path(root)
        safe_path(out, label+'/probe')
        if not root.exists():
            missing_roots.append(label); continue
        for path in sorted(root.rglob('*')):
            if not allowed(path, root):
                continue
            rel = label+'/'+path.relative_to(root).as_posix(); safe_path(out, rel)
            fd, temp_name = tempfile.mkstemp(dir=objects); os.close(fd); temp = Path(temp_name)
            try:
                if path.suffix == '.sqlite':
                    source = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)
                    dest = sqlite3.connect(temp)
                    try: source.backup(dest)
                    finally: dest.close(); source.close()
                else:
                    before = path.stat()
                    shutil.copyfile(path, temp)
                    after = path.stat()
                    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                        raise ValueError(f'Source changed while archiving: {rel}')
                key = sha(temp); size = temp.stat().st_size
                files[rel] = {'sha256': key, 'size': size}
                if key not in refs and key not in new:
                    target = objects/key
                    if target.exists() and sha(target) != key:
                        raise ValueError('Corrupt local archive object')
                    if not target.exists(): temp.replace(target)
                    new[key] = target
            finally:
                if temp.exists(): temp.unlink()
    if previous.get('tag') and files == previous['files']:
        manifest_path = out/f"{previous['tag']}.json"
        manifest_path.write_text(json.dumps(previous, ensure_ascii=False, sort_keys=True, indent=2)+'\n', encoding='utf-8')
        return previous, manifest_path, []
    # A->B->A is a new generation, not a reuse of the first published tag.
    fingerprint = hashlib.sha256(json.dumps({'files': files, 'parent': previous.get('tag')}, sort_keys=True).encode()).hexdigest()
    tag = 'scanner-data-'+fingerprint[:20]
    bundles = []
    groups, group, size = [], [], 0
    for key, path in sorted(new.items()):
        if group and size+path.stat().st_size > bundle_limit:
            groups.append(group); group=[]; size=0
        group.append((key,path)); size+=path.stat().st_size
    if group: groups.append(group)
    for i, group in enumerate(groups):
        temp = out/f'bundle-{i}.tmp'
        with zipfile.ZipFile(temp, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for key, path in group:
                # Deterministic ZIP metadata makes upload retry content stable.
                info = zipfile.ZipInfo(key, date_time=(2000,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
                with path.open('rb') as src, z.open(info, 'w', force_zip64=True) as dst:
                    shutil.copyfileobj(src, dst)
        digest = sha(temp); name = f'bundle-{digest}.zip'; target = out/name
        if not target.exists(): temp.replace(target)
        else: temp.unlink()
        if target.stat().st_size >= 1900*1024*1024:
            raise ValueError('Bundle exceeds upload limit; reduce bundle size or split large source file')
        bundles.append(target)
        for key, path in group:
            refs[key] = {'tag': tag, 'asset': name, 'archive_sha256': digest}
    manifest = {'schema': SCHEMA, 'tag': tag, 'files': files, 'objects': refs,
                'generation': previous.get('generation', 0)+1, 'parent_tag': previous.get('tag'),
                'missing_roots': missing_roots, 'retention': 'files absent upstream are retained; no remote deletion',
                'exclusions': ['credentials/environment files', 'dependency packages', 'logs', 'symlinks', 'scheduler state']}
    manifest_path = out/f'{tag}.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2)+'\n', encoding='utf-8')
    return manifest, manifest_path, bundles


def restore(manifest, destination, fetch_asset):
    """fetch_asset(tag, asset) -> downloaded local ZIP. Verify before replacing.

    A prior local version moves into .versions by digest; unrelated files remain.
    Only a manifest-listed object is read, never extractall() or ZIP paths.
    """
    if manifest.get('schema') != SCHEMA:
        raise ValueError('Unsupported archive manifest')
    destination = Path(destination); destination.mkdir(parents=True, exist_ok=True)
    planned, portable_names = [], set()
    for rel, info in manifest['files'].items():
        target = safe_path(destination, rel)
        lower = rel.casefold()
        if lower in portable_names:
            raise ValueError('Archive contains a case-insensitive Windows path collision')
        portable_names.add(lower)
        if not valid_digest(info['sha256']) or not isinstance(info['size'], int) or info['size'] < 0:
            raise ValueError('Invalid file identity')
        ref = manifest['objects'][info['sha256']]
        if not valid_digest(ref['archive_sha256']) or ref['asset'] != f"bundle-{ref['archive_sha256']}.zip" or not ref['tag'].startswith('scanner-data-'):
            raise ValueError('Invalid asset identity')
        planned.append((rel, info, target, ref))
    downloaded, copied, unchanged = {}, 0, 0
    for rel, info, target, ref in planned:
        if target.is_file() and target.stat().st_size == info['size'] and sha(target) == info['sha256']:
            unchanged += 1; continue
        key = (ref['tag'], ref['asset'])
        if key not in downloaded:
            archive = Path(fetch_asset(*key))
            if sha(archive) != ref['archive_sha256']:
                raise ValueError('Downloaded bundle checksum mismatch')
            downloaded[key] = archive
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=target.parent); os.close(fd); temp = Path(name)
        try:
            with zipfile.ZipFile(downloaded[key]) as z:
                entry = z.getinfo(info['sha256'])
                if entry.file_size != info['size']:
                    raise ValueError('Object size mismatch')
                with z.open(entry) as src, temp.open('wb') as dst:
                    shutil.copyfileobj(src, dst)
            if sha(temp) != info['sha256']:
                raise ValueError('Object checksum mismatch')
            if target.exists():
                old = safe_path(destination, '.versions/'+rel+'/'+sha(target))
                old.parent.mkdir(parents=True, exist_ok=True)
                if not old.exists(): shutil.copy2(target, old)
            temp.replace(target); copied += 1
        finally:
            if temp.exists(): temp.unlink()
    return {'copied': copied, 'unchanged': unchanged, 'files': len(planned)}
