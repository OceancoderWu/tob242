"""Small stdlib-only helpers for packaging measured experiment evidence."""
import hashlib
import json
from pathlib import Path


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def verify_files(train_dir, test_dir, manifest):
    entries = [(train_dir, manifest['train_file'])]
    entries.extend((test_dir, item) for item in manifest['test_files'])
    for directory, item in entries:
        if sha(Path(directory) / item['file']) != item['sha256']:
            raise ValueError('Dataset hash mismatch: ' + item['file'])
