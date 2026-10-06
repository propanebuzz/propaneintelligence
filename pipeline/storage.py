"""Private atomic storage and process locks for recoverable pipeline runs."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile

PRIVATE = Path.home() / 'Documents/Codex/propane-private'


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(value, handle, indent=2, allow_nan=False)
            handle.flush(); os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


@contextmanager
def run_lock(path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another pipeline run is active') from None
        try: yield
        finally: fcntl.flock(handle, fcntl.LOCK_UN)


def archive_bytes(folder, data, suffix):
    digest = hashlib.sha256(data).hexdigest()
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    path = folder / (digest + suffix)
    if not path.exists():
        with path.open('xb') as handle: handle.write(data)
        os.chmod(path, 0o600)
    elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError('Private archive hash mismatch')
    return path, digest
