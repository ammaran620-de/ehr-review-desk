"""Validate and atomically update the locally approved Round 2 revisions."""
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from filelock import FileLock

def load_revisions(path):
    try:
        revisions = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}
    if not isinstance(revisions, dict):
        raise ValueError('Revisions must be a JSON object.')
    for event, item in revisions.items():
        if (not isinstance(item, dict) or item.get('severity') not in ('High', 'Medium', 'Low')
                or type(item.get('control', False)) is not bool
                or any(not isinstance(item.get(key), str) or not item[key].strip()
                       for key in ('message', 'rationale'))):
            raise ValueError(f'{event} needs a message, severity and rationale.')
    return revisions

def save_revision(path, event, revision):
    path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(path) + '.lock', timeout=10):
        revisions = load_revisions(path)
        revisions[event] = revision
        with NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
        try:
            temporary.write_text(json.dumps(revisions, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
