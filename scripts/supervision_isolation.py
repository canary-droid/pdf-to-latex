"""Closed execution boundary for untrusted repair code. No host fallback.

Codex's installed Linux permission-profile executor provides filesystem/network
confinement (bubblewrap/seccomp). A separate transient user service provides
aggregate memory/process limits and descendant cleanup. Neither is optional.
This module and the harness are trusted controller code, never candidate imports.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import time
import tomllib
import uuid

import supervision_policy as policy
from probe.common import atomic_json, read_json, sha

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / '.venv-control/bin/python'
HARNESS = ROOT / 'scripts/supervision_checks.py'
SERVICE_GUARD = ROOT / 'scripts/supervision_service_guard.py'
SETUP = ROOT / 'results/codex-setup-20261030T105129628712Z/setup.json'
PROFILE = 'pdf-to-latex-supervision'
MEMORY = 4 * 1024 ** 3
TASKS = 128
LOG_LIMIT = 32 * 1024 ** 2
TREE_LIMIT = 128 * 1024 ** 2
STAGES = {'boundary', 'redirect', 'fake-worker', 'regressions', 'existing-tests', 'replay'}
DISABLED_FEATURES = ('apps', 'plugins', 'remote_plugin', 'plugin_discovery_prefetch',
                     'hooks', 'shell_snapshot', 'browser_use', 'browser_use_external',
                     'in_app_browser', 'computer_use', 'memories', 'multi_agent', 'multi_agent_v2',
                     'skill_search', 'skill_mcp_dependency_install', 'unbounded_connection_retries')


def private_directory(parent, name):
    path = Path(parent) / name
    path.mkdir(mode=0o700, parents=False, exist_ok=False)
    return path


def clean_environment(*, client=False, temporary=None):
    """Explicit values only: no proxies, SSH agent, API keys, PYTHONPATH or hooks."""
    env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
           'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1'}
    if client:
        env.update(HOME=str(Path.home()), CODEX_HOME=str(Path.home() / '.codex'))
    if temporary is not None:
        env['TMPDIR'] = str(temporary)
    return env


def manager_environment():
    return dict(clean_environment(), HOME=str(Path.home()),
                XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
                DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')


def executable():
    record = read_json(SETUP)
    exe = Path(record['executable'])
    if sha(exe) != record['executable_sha256']:
        raise policy.Blocked('Codex executable differs from the selected stable release')
    profile = Path(record['profile'])
    if sha(profile) != record['profile_sha256']:
        raise policy.Blocked('Selected model profile changed; inspect before qualification')
    if sha(Path.home() / '.codex/config.toml') != record['base_config_sha256']:
        raise policy.Blocked('Base configuration changed since inspected setup; review required')
    return exe


def profile_options():
    """app-server diagnostics don't accept --profile in this installed release."""
    record = read_json(SETUP)
    path = Path(record['profile'])
    if sha(path) != record['profile_sha256']: raise policy.Blocked('Selected profile changed')
    data = tomllib.loads(path.read_text())
    wanted = {'model', 'model_reasoning_effort', 'model_context_window',
              'model_auto_compact_token_limit', 'model_auto_compact_token_limit_scope', 'forced_login_method'}
    if set(data) != wanted: raise policy.Blocked('Unexpected additional model-profile settings')
    return data


def toml(value):
    if isinstance(value, dict):
        return '{' + ','.join(json.dumps(k) + '=' + toml(v) for k, v in value.items()) + '}'
    if isinstance(value, list):
        return '[' + ','.join(map(toml, value)) + ']'
    return json.dumps(value)


def configuration(code, evidence, output, temporary, *, editable=False):
    """Incident-local allowlist, supplied on argv; no config files are changed."""
    paths = [Path(x).absolute() for x in (code, evidence, output, temporary)]
    for path in paths:
        if not path.is_dir() or any(p.is_symlink() for p in (path, *path.parents)):
            raise policy.Blocked('Boundary root missing or symlinked: ' + str(path))
    if len(set(paths)) != 4 or any(a in b.parents for a in paths for b in paths if a != b):
        raise policy.Blocked('Boundary roots must be distinct siblings, not overlapping grants')
    code, evidence, output, temporary = paths
    fs = {':root': 'deny', str(code): 'read',
          str(evidence): 'read', str(output): 'write', str(temporary): 'write',
          str(ROOT / '.venv-control'): 'read', str(HARNESS): 'read',
          str(Path.home() / '.codex'): 'deny', str(Path.home() / '.ssh'): 'deny',
          str(Path.home() / '.aws'): 'deny', '/run': 'deny', '/var/run': 'deny'}
    # Explicit runtime/dependency reads replace the evolving :minimal default.
    # /proc is usable only after the harness verifies a separate PID namespace.
    for name in ('/usr/bin', '/usr/lib', '/bin', '/lib', '/lib64', '/proc',
                 '/etc/ld.so.cache', '/etc/localtime', '/dev/null', '/dev/urandom', '/dev/random'):
        if Path(name).exists(): fs[name] = 'read'
    release = Path(read_json(SETUP)['executable']).parent.parent
    for relative in ('bin/codex', 'bin/codex-code-mode-host', 'bin/codex-exec-server', 'codex-path/rg'):
        if (release / relative).exists(): fs[str(release / relative)] = 'read'
    # No :workspace inheritance, no :tmp/:slash_tmp write, no automatic live
    # workspace grant. Protected policy/tests within a dev copy are additionally
    # read-only; application still checks every baseline byte independently.
    if editable:
        for rel in policy.SCOPE: fs[str(code / rel)] = 'write'
        for rel in ('scripts/supervision_policy.py', 'scripts/supervision_isolation.py',
                    'scripts/supervision_qualification.py', 'scripts/overnight_supervisor.py',
                    'scripts/supervision_checks.py', 'AGENTS.md'):
            if (code / rel).exists(): fs[str(code / rel)] = 'read'
        for p in (code / 'tests').rglob('*'):
            if p.is_file(): fs[str(p)] = 'read'
    options = {'default_permissions': 'incident-only',
               'permissions': {'incident-only': {'filesystem': fs, 'network': {'enabled': False}}},
               'approval_policy': 'never', 'forced_login_method': 'chatgpt',
               'web_search': 'disabled', 'mcp_servers': {},
               'features': {**{name: False for name in DISABLED_FEATURES},
                            'skip_host_skill_discovery': True},
               'shell_environment_policy': {'inherit': 'none', 'experimental_use_profile': False,
                    'ignore_default_excludes': False,
                    'set': {**clean_environment(), 'HOME': str(temporary), 'TMPDIR': str(temporary)}}}
    return options


def config_arguments(options):
    result = []
    for name, value in options.items(): result += ['-c', name + '=' + toml(value)]
    return result


def tree_size(root):
    # Walk by descriptors while a repair may still be writing. Never follow a
    # replaced directory/symlink into a host path during resource accounting.
    total = count = 0
    def walk(fd, depth):
        nonlocal total, count
        if depth > 32: raise policy.Blocked('Private output directory depth exceeded')
        for name in os.listdir(fd):
            try: info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError: continue
            count += 1
            if stat.S_ISREG(info.st_mode): total += info.st_size
            if total > TREE_LIMIT or count > 8192:
                raise policy.Blocked('Private repair output exceeded size/file-count limit')
            if stat.S_ISDIR(info.st_mode):
                try: child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                except FileNotFoundError: continue
                try: walk(child, depth + 1)
                finally: os.close(child)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: walk(fd, 0)
    finally: os.close(fd)
    return total


def limited_service(argv, log, *, environment, timeout=None, stdin=None, watch=()):
    """Fixed owned unit. All descendants die before results are consumed.

    timeout is used for disposable checks only. Real Codex generation has no wall
    deadline. Cancellation/resource violations stop only this random owned unit.
    """
    # A host service manager is not a way around this interactive agent's outer
    # sandbox. Only the explicitly requested normal-terminal entry may use it.
    # This placement check supplements, and never replaces, OS confinement.
    if os.environ.get('CODEX_SANDBOX_NETWORK_DISABLED') or os.environ.get('CODEX_THREAD_ID'):
        raise policy.Blocked('Normal terminal required: refusing user-service launch from a Codex tool session')
    log = Path(log); log.parent.mkdir(parents=True, exist_ok=True)
    unit = 'pdf2tex-check-' + uuid.uuid4().hex + '.service'
    from supervision_service_guard import owner_identity
    owner = owner_identity(os.getpid())
    if not owner: raise policy.Blocked('Controller owner identity unavailable')
    command = ['/usr/bin/systemd-run', '--user', '--no-ask-password', '--wait', '--pipe',
               '--collect', '--quiet', '--service-type=exec', '--unit=' + unit,
               '--property=KillMode=control-group', '--property=MemoryMax=' + str(MEMORY),
               '--property=MemorySwapMax=0', '--property=TasksMax=' + str(TASKS),
               '--property=LimitCORE=0', '--property=LimitNOFILE=256',
               '--property=LimitFSIZE=1073741824', '--property=NoNewPrivileges=yes',
               '/usr/bin/env', '-i', *[k + '=' + v for k, v in sorted(environment.items())],
               '/usr/bin/python3', '-I', SERVICE_GUARD, '--owner', json.dumps(owner), '--',
               *[str(a) for a in argv]]
    command = list(map(str, command))
    atomic_json(log.with_suffix('.command.json'), {'unit': unit, 'argv': command,
                'environment_allowlist': environment, 'memory_bytes': MEMORY, 'tasks': TASKS,
                'stdout_limit': LOG_LIMIT, 'private_tree_limit': TREE_LIMIT,
                'generation_wall_deadline': timeout, 'owner': owner, 'guard_sha256': sha(SERVICE_GUARD)})
    input_file = None
    if stdin is not None:
        data = stdin.encode()
        if len(data) > 65536: raise policy.Blocked('Repair handover exceeds 64 KiB')
        input_path = log.with_suffix('.stdin.txt')
        with input_path.open('xb') as f: f.write(data)
        input_file = input_path.open('rb')
    try:
        proc = subprocess.Popen(command, stdin=input_file or subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                env=manager_environment(), start_new_session=True)
    finally:
        if input_file: input_file.close()
    started = time.monotonic(); count = 0; success = False
    try:
        selector = selectors.DefaultSelector(); selector.register(proc.stdout, selectors.EVENT_READ)
        with log.open('xb') as out:
            while selector.get_map():
                if timeout and time.monotonic() - started > timeout:
                    raise policy.Blocked('Disposable check exceeded its execution limit')
                for root in watch: tree_size(root)
                for key, _ in selector.select(.2):
                    data = os.read(key.fileobj.fileno(), 65536)
                    if not data: selector.unregister(key.fileobj); continue
                    count += len(data)
                    if count > LOG_LIMIT: raise policy.Blocked('Child output exceeded limit')
                    out.write(data)
            rc = proc.wait()
        for root in watch: tree_size(root)
        # --wait returns after the service's control group is stopped. A leftover
        # active unit is a blocker, never permission to inspect mutable output.
        check = subprocess.run(['/usr/bin/systemctl', '--user', '--no-ask-password', 'show', unit,
                                '--property=ActiveState', '--property=LoadState'], env=manager_environment(),
                               capture_output=True, text=True, timeout=10)
        fields = dict(line.split('=', 1) for line in check.stdout.splitlines() if '=' in line)
        if not fields:
            raise policy.Blocked('Cannot verify owned user-service cleanup: ' + check.stderr.strip()[:300]
                                 + '; see ' + str(log))
        if fields.get('ActiveState') not in ('inactive', 'failed'):
            raise policy.Blocked('Owned child unit/descendants remain active')
        success = True
        return rc
    finally:
        if not success or proc.poll() is None:
            subprocess.run(['/usr/bin/systemctl', '--user', '--no-ask-password', 'stop', unit],
                           env=manager_environment(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=15)
            if proc.poll() is None: os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()


def sandbox_arguments(options, code, stage, evidence, output, temporary):
    if stage not in STAGES: raise policy.Blocked('Unknown fixed check mode')
    # CLI 0.166 requires an explicit permission selector here and rejects the
    # runtime-only --strict-config flag; exec retains that flag separately.
    return [executable(), '--profile', PROFILE, *config_arguments(options),
            'sandbox', '--permission-profile', options['default_permissions'], '--cd', code, '--',
            '/usr/bin/env', '-i', *[k + '=' + v for k, v in sorted(dict(
                clean_environment(), HOME=str(temporary), TMPDIR=str(temporary)).items())],
            PYTHON, '-I', '-B', HARNESS, stage, '--code', code, '--evidence', evidence,
            '--output', output, '--temporary', temporary]


def run_snapshot(snapshot, evidence, job, stage, *, editable=False, expected_test_failure=False):
    """All candidate imports/tests/replay and fixture post-promotion use this."""
    code = Path(snapshot); job = Path(job)
    job.mkdir(mode=0o700, parents=True, exist_ok=False)
    output = private_directory(job, 'output'); temporary = private_directory(job, 'tmp')
    before = policy.inventory(code)
    options = configuration(code, evidence, output, temporary, editable=editable)
    atomic_json(job / 'requested-permissions.json', options)
    argv = sandbox_arguments(options, code, stage, evidence, output, temporary)
    rc = limited_service(argv, job / 'execution.log', environment=clean_environment(client=True),
                         timeout=600, watch=(output, temporary))
    after = policy.inventory(code)
    if not editable and before != after:
        raise policy.Blocked('Read-only candidate snapshot changed during validation')
    result = {'exit': rc, 'stage': stage, 'snapshot_sha256': before, 'snapshot_unchanged': before == after,
              'output': str(output), 'status': 'completed' if rc == 0 else 'blocked_or_failed'}
    atomic_json(job / 'result.json', result)
    if expected_test_failure and stage == 'regressions' and rc == 1:
        tests = read_artifact(output, 'test-result.json')
        if tests.get('status') == 'failed' and tests.get('tests', 0) > 0:
            return result
    if rc != 0:
        raise policy.Blocked('Confined check failed/denied; see ' + str(job / 'execution.log'))
    return result


def read_artifact(root, name, limit=65536):
    path = policy.regular(root, name)
    if path.stat().st_size > limit: raise policy.Blocked('Oversize untrusted result')
    value = json.loads(path.read_text())
    if not isinstance(value, dict): raise policy.Blocked('Result must be an object')
    return value


def freeze(source, destination, expected=None, *, subset=False):
    """Copy bytes into controller-private storage not granted to the repair child.

    Validation mounts this copy read-only. Its exact hashes are the integration
    input; mutable development files are never the promotion source.
    """
    expected = expected or policy.inventory(source)
    policy.snapshot(source, destination, expected)
    source_unchanged = (all(sha(policy.regular(source, p)) == h for p, h in expected.items())
                        if subset else policy.inventory(source) == expected)
    if policy.inventory(destination) != expected or not source_unchanged:
        raise policy.Blocked('Candidate changed while freezing')
    return expected


def resource_preflight(folder):
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    script = ('import json,pathlib; p=pathlib.Path("/sys/fs/cgroup")/next('
              'x.split(":",2)[2].lstrip("/") for x in pathlib.Path("/proc/self/cgroup").read_text().splitlines() '
              'if x.startswith("0::")); print(json.dumps({k:(p/k).read_text().strip() '
              'for k in ("memory.max","memory.swap.max","pids.max")}))')
    rc = limited_service(['/usr/bin/python3', '-I', '-c', script], folder / 'resource-probe.log',
                         environment=clean_environment(), timeout=30)
    if rc: raise policy.Blocked('User-service resource confinement unavailable; see resource-probe.log')
    records = []
    for line in (folder / 'resource-probe.log').read_text().splitlines():
        try: records.append(json.loads(line))
        except ValueError: pass
    wanted = {'memory.max': str(MEMORY), 'memory.swap.max': '0', 'pids.max': str(TASKS)}
    if wanted not in records: raise policy.Blocked('Actual cgroup limits not observed')
    atomic_json(folder / 'resources-observed.json', wanted)
    return wanted
