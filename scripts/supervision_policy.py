"""Acceptance and ownership policy. Never included in an automatic repair scope."""
import ast
from contextlib import contextmanager
import difflib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat

from probe.common import atomic_json, fingerprint, sha

MAX_REPAIRS = 2
MAX_SOURCE_BYTES = 512 * 1024
TERMINAL = 'suite_finished_for_inspection'
# Request construction, validation, transport, scheduling, compiler isolation and
# this policy cannot be patched by the repair agent.
SCOPE = {'scripts/editorial_chapters.py': {'finish_task'},
         'scripts/speed_suite.py': {'report', 'write_progress', 'bundle'}}
REGRESSION = re.compile(r'tests/test_supervisor_regression_[a-z0-9_]+\.py\Z')


class Blocked(RuntimeError):
    pass


@contextmanager
def lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise Blocked('Symlinked ownership lock')
    with path.open('a') as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Blocked('Owner already holds ' + str(path)) from exc
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def process(pid):
    """PID reuse and reboot cannot impersonate the original worker."""
    p = Path('/proc') / str(pid)
    try:
        fields = (p / 'stat').read_text().rsplit(')', 1)[1].split()
        if fields[0] == 'Z':
            return None
        return {'pid': int(pid), 'start_ticks': fields[19],
                'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                'executable': str((p / 'exe').resolve(strict=True)),
                'cwd': str((p / 'cwd').resolve(strict=True)),
                'argv_sha256': hashlib.sha256((p / 'cmdline').read_bytes()).hexdigest()}
    except (OSError, ValueError):
        return None


def alive(identity):
    return bool(identity) and process(identity['pid']) == identity


def regular(root, relative):
    root = Path(root).resolve()
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts:
        raise Blocked('Path escapes repair root: ' + str(relative))
    path = root
    for part in rel.parts:
        path /= part
        if path.is_symlink():
            raise Blocked('Symlink in patch path: ' + str(relative))
    if path.exists() and (not stat.S_ISREG(path.stat().st_mode) or path.stat().st_nlink != 1):
        raise Blocked('Nonregular/hardlinked patch path: ' + str(relative))
    return path


def inventory(root):
    result = {}
    for p in sorted(Path(root).rglob('*')):
        rel = str(p.relative_to(root))
        if p.is_symlink():
            raise Blocked('Symlink in development copy: ' + rel)
        if p.is_file():
            regular(root, rel)
            result[rel] = sha(p)
    return result


def code_inventory(root):
    """All implementation/tests and accepted input policy; no raw runs or Git."""
    root = Path(root)
    paths = []
    for folder in ('probe', 'scripts', 'tests', 'docs'):
        paths += [p for p in (root / folder).rglob('*') if p.is_file()
                  and '__pycache__' not in p.parts and p.suffix != '.pyc']
    paths += [root / 'probe.py', root / 'AGENTS.md']
    paths += list((root / 'scripts/tex-compiler').glob('Dockerfile'))
    return {str(p.relative_to(root)): sha(regular(root, str(p.relative_to(root)))) for p in paths if p.exists()}


def snapshot(root, dest, manifest):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=False)
    for rel, digest in manifest.items():
        source = regular(root, rel)
        if sha(source) != digest:
            raise Blocked('Baseline changed during snapshot: ' + rel)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return dest


def ast_scope(before, after, names):
    if max(len(before.encode()), len(after.encode())) > MAX_SOURCE_BYTES:
        raise Blocked('Operational source exceeds inspection size limit')
    a, b = ast.parse(before), ast.parse(after)
    def outside(tree):
        return ast.dump(ast.Module(body=[n for n in tree.body if not
            (isinstance(n, ast.FunctionDef) and n.name in names)], type_ignores=[]))
    if outside(a) != outside(b):
        raise Blocked('Patch changes code outside permitted functions')
    fa = {n.name: n for n in a.body if isinstance(n, ast.FunctionDef) and n.name in names}
    fb = {n.name: n for n in b.body if isinstance(n, ast.FunctionDef) and n.name in names}
    if any(sum(isinstance(n, ast.FunctionDef) and n.name in names for n in tree.body) != len(functions)
           for tree, functions in ((a, fa), (b, fb))):
        raise Blocked('Duplicate scoped function definitions')
    if fa.keys() != fb.keys():
        raise Blocked('Function removed or renamed')
    for name in fa:
        old, new = fa[name], fb[name]
        if ast.dump(old) == ast.dump(new):
            continue
        if (ast.dump(old.args) != ast.dump(new.args)
                or [ast.dump(n) for n in old.decorator_list] != [ast.dump(n) for n in new.decorator_list]
                or ast.dump(old.returns or ast.Constant(None)) != ast.dump(new.returns or ast.Constant(None))):
            raise Blocked('Repair changes function interface')
        # Change-scope check ONLY, never an execution boundary. Existing imports
        # (notably report's import statistics) remain valid, with multiplicity.
        from collections import Counter
        imports = Counter(ast.dump(n) for n in ast.walk(old) if isinstance(n, (ast.Import, ast.ImportFrom)))
        new_imports = Counter(ast.dump(n) for n in ast.walk(new) if isinstance(n, (ast.Import, ast.ImportFrom)))
        if imports != new_imports:
            raise Blocked('Changed imports in operational repair')
        calls = {ast.dump(n.func) for n in ast.walk(old) if isinstance(n, ast.Call)}
        strings = {n.value for n in ast.walk(old) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        for n in ast.walk(new):
            if isinstance(n, (ast.Global, ast.Nonlocal)):
                raise Blocked('New import/global authority in repair')
            if isinstance(n, ast.Call) and ast.dump(n.func) not in calls:
                raise Blocked('New callable in operational repair')
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value not in strings:
                raise Blocked('Changed text/policy in operational repair')
            if isinstance(n, ast.Attribute) and n.attr.startswith('__'):
                raise Blocked('Introspection in operational repair')
        # Calls enforcing source/completeness/identity remain present verbatim.
        checks = ('complete_document', 'bound_output', 'verify_seal', 'validate_manifest')
        def protected(fn):
            return sorted(ast.dump(n) for n in ast.walk(fn) if isinstance(n, ast.Call)
                          and isinstance(n.func, ast.Attribute) and n.func.attr in checks)
        if protected(old) != protected(new):
            raise Blocked('Repair changes a protected validation call')


def proposed_patch(baseline, candidate, expected):
    actual = inventory(candidate)
    changed = sorted(p for p in set(expected) | set(actual) if expected.get(p) != actual.get(p))
    if not changed or not any(REGRESSION.fullmatch(p) and p not in expected for p in changed):
        raise Blocked('Repair must include a new focused regression and an operational patch')
    patches = []
    operational = False
    for rel in changed:
        if rel not in actual:
            raise Blocked('Deletion is outside repair scope: ' + rel)
        if rel in SCOPE and rel in expected:
            if regular(candidate, rel).stat().st_size > MAX_SOURCE_BYTES:
                raise Blocked('Operational source exceeds inspection size limit')
            before = regular(baseline, rel).read_text()
            after = regular(candidate, rel).read_text()
            ast_scope(before, after, SCOPE[rel])
            operational = True
        elif REGRESSION.fullmatch(rel) and rel not in expected:
            if regular(candidate, rel).stat().st_size > 65536:
                raise Blocked('Regression exceeds inspection size limit')
            before, after = '', regular(candidate, rel).read_text()
            ast.parse(after)
        else:
            raise Blocked('Out-of-scope patch: ' + rel)
        patches.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                          fromfile='before/' + rel, tofile='after/' + rel))
    if not operational:
        raise Blocked('No operational code repair')
    return changed, ''.join(patches)


def classify(state, *, worker_alive, owned, latched=False, disabled=False, exit_code=None):
    # Terminal work may still be bundling. Observe the real worker until exit.
    if disabled:
        return 'disabled'
    if latched:
        return 'draining' if worker_alive or owned else 'paused'
    if worker_alive:
        return 'healthy'  # No duration/deadline criterion.
    if owned:
        return 'blocked_ownership'
    if state['status'] in ('paused', 'draining'):
        return 'paused'
    if state['status'] == TERMINAL:
        return 'incident' if exit_code not in (None, 0) else 'finished'
    if any(c['status'] == 'in_progress' for c in state.get('calls', [])):
        return 'blocked_uncertain'
    if state['status'] == 'prepared_offline' and exit_code is None:
        return 'ready'
    return 'incident'  # Includes stopped_error + exit 0 and missing final status.


def incident_key(state, traceback_text, exit_code):
    # No run ID, line number, call number, or temporary path: allowance persists
    # when the same failure recurs in a linked continuation or another unit.
    cause = traceback_text.strip().splitlines()[-1:] or [state.get('diagnostic') or 'worker_lost']
    cause = re.sub(r'call-\d+|0x[0-9a-f]+|/[\w./-]+|\b\d+\b', '<id>', '\n'.join(cause))
    return fingerprint({'cause': cause, 'exit_nonzero': exit_code not in (None, 0)})


def reserve_attempt(folder, key):
    path = Path(folder) / 'allowances.json'
    with lock(Path(folder) / 'allowances.lock'):
        ledger = json.loads(path.read_text()) if path.exists() else {}
        count = ledger.get(key, 0)
        if count >= MAX_REPAIRS:
            raise Blocked('Two repair attempts exhausted for incident ' + key)
        ledger[key] = count + 1
        atomic_json(path, ledger)  # Consumed BEFORE Codex starts, also on a crash.
    return count + 1
