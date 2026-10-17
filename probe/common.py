"""Small durable file/lock helpers for the probe; not the later SQLite core."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import uuid


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('x', encoding='utf-8') as f:
            json.dump(value, f, indent=2, ensure_ascii=True, allow_nan=False)
            f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(temp, path)
        fd = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        if temp.exists(): temp.unlink()


@contextlib.contextmanager
def writer_lock(root):
    import fcntl
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    with (root / '.probe.lock').open('a') as f:
        try: fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc: raise RuntimeError('Another mutating probe command is running.') from exc
        try: yield
        finally: fcntl.flock(f, fcntl.LOCK_UN)


def contained(root, relative):
    root = Path(root).resolve()
    p = (root / relative).resolve()
    if p != root and root not in p.parents:
        raise ValueError('Path escapes its artifact directory')
    return p


def files_manifest(root):
    root = Path(root)
    result = []
    for path in sorted(root.rglob('*')):
        if path.is_symlink(): raise ValueError('Output symlink rejected: ' + str(path))
        if path.is_file():
            result.append({'path': path.relative_to(root).as_posix(), 'size': path.stat().st_size, 'sha256': sha(path)})
    return result


def check_manifest(root, entries):
    root = Path(root)
    paths = list(root.rglob('*'))
    if any(p.is_symlink() for p in paths): return False
    actual={p.relative_to(root).as_posix() for p in paths if p.is_file()}
    if actual != {item['path'] for item in entries}: return False
    for item in entries:
        path = contained(root, item['path'])
        if path.is_symlink() or not path.is_file() or sha(path) != item['sha256']:
            return False
    return True


def windows(count, size=8, overlap=1):
    if count < 1 or size < 1 or not 0 <= overlap <= 2: raise ValueError('Invalid window settings')
    for start in range(1, count + 1, size):
        end = min(count, start + size - 1)
        yield {'owned_start': start, 'owned_end': end,
               'input_start': max(1, start-overlap), 'input_end': min(count, end+overlap)}
