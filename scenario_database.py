"""Create reproducible scenario database snapshots without changing the source database."""

import hashlib
import json
import shutil
from pathlib import Path


def _fingerprint(path):
    """SHA-256 over the relative names and contents of all files under path (the database version)."""
    digest = hashlib.sha256()
    for file in sorted(path.rglob('*')):
        if file.is_file():
            digest.update(file.relative_to(path).as_posix().encode())
            digest.update(file.read_bytes())
    return digest.hexdigest()


def snapshot(source, scenario, settings):
    """Copy the source database to <source>/../scenarios/<scenario> (once per source version) with a
    scenario_manifest.json of the source fingerprint and the settings; returns the snapshot's path, which the run uses
    instead of the source, so the source database is never changed by a run."""
    source = Path(source)
    target = source.parent / 'scenarios' / scenario
    manifest = target / 'scenario_manifest.json'
    fingerprint = _fingerprint(source)
    if manifest.exists():
        saved = json.loads(manifest.read_text(encoding='utf-8'))
        if saved.get('source_fingerprint') == fingerprint:
            now = json.loads(json.dumps(settings, sort_keys=True, default=str))
            if saved.get('settings') != now:              # same database, new settings: keep the record current
                saved['settings'] = now
                manifest.write_text(json.dumps(saved, indent=2, sort_keys=True, default=str) + '\n', encoding='utf-8')
            return str(target)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    manifest.write_text(json.dumps({
        'scenario': scenario,
        'source_database': str(source),
        'source_fingerprint': fingerprint,
        'settings': settings,
    }, indent=2, sort_keys=True, default=str) + '\n', encoding='utf-8')
    return str(target)
