#!/usr/bin/env python3
"""Operator-only Phase 1: update the CLI, install one profile, open a fresh task.

Does not start the book worker or implement/arm its supervisor. It does not edit
base configuration, authentication, permissions, Git, services, or frozen runs.
"""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'pdf-to-latex-supervision'
TASK = Path('/home/mdi/Downloads/Codex-configure-review-and-supervise-20261030.txt')
HANDOVER = ROOT / 'docs/CODEX-SUPERVISION-HANDOVER-20261030.md'
MODEL = 'gpt-6-astra'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def captured(argv, *, timeout=60):
    """Do not print raw auth/config output, even on a failed command."""
    p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f'{Path(argv[0]).name} {argv[1]} failed (exit {p.returncode}); '
                           'raw output withheld; no authentication or permission change attempted')
    return p.stdout + '\n' + p.stderr


def cli_version(executable):
    output = captured([str(executable), '--version'])
    match = re.search(r'^codex-cli (\d+\.\d+\.\d+)\s*$', output, re.M)
    if not match:
        raise RuntimeError('Expected a public stable codex-cli version; preview/unknown build refused')
    return match.group(1)


def chatgpt_login(executable):
    output = captured([str(executable), 'login', 'status']).lower()
    if 'logged in using chatgpt' not in output:
        raise RuntimeError('Existing ChatGPT login was not confirmed. No API-key fallback or login change.')


def select_settings(model):
    """Use current account catalog limits, never the public API's larger limit."""
    if model.get('slug') != MODEL:
        raise ValueError('The catalog did not identify gpt-6-astra')
    if 'xhigh' not in {r['effort'] for r in model.get('supported_reasoning_levels', [])}:
        raise ValueError('The current catalog does not advertise xhigh for gpt-6-astra')
    default = model.get('context_window')
    maximum = model.get('max_context_window') or default
    percent = model.get('effective_context_window_percent')
    if not isinstance(default, int) or not isinstance(maximum, int) or not default > 0:
        raise ValueError('No usable model context metadata; leave the working configuration unchanged')
    if not isinstance(percent, int) or not 1 <= percent <= 100:
        raise ValueError('Unknown client headroom factor; leave the working configuration unchanged')
    window = min(800000, maximum)
    # Below the requested extended range, use the supported nominal default.
    # This is a conservative fallback, never a provider-limit workaround.
    if window < 800000:
        window = min(default, maximum)
    threshold = min(650000, window * 85 // 100, window * percent // 100 - 16384)
    if threshold <= 0:
        raise ValueError('Insufficient advertised context headroom')
    return {'model': MODEL, 'model_reasoning_effort': 'xhigh',
            'model_context_window': window, 'model_auto_compact_token_limit': threshold,
            'model_auto_compact_token_limit_scope': 'total', 'forced_login_method': 'chatgpt'}


def profile_text(previous, settings):
    """Update only our top-level scalar keys; preserve unrelated TOML verbatim."""
    tomllib.loads(previous)
    lines = previous.splitlines(keepends=True)
    first_table = next((i for i, line in enumerate(lines) if line.lstrip().startswith('[')), len(lines))
    prefix = ''.join(line for line in lines[:first_table]
                     if not any(re.match(r'^\s*' + re.escape(k) + r'\s*=', line) for k in settings))
    additions = '\n'.join(f'{k} = {json.dumps(v)}' for k, v in settings.items()) + '\n'
    text = prefix.rstrip() + '\n\n' + additions + '\n' + ''.join(lines[first_table:])
    parsed = tomllib.loads(text)
    if any(parsed.get(k) != v for k, v in settings.items()):
        raise ValueError('Profile did not retain the requested top-level values')
    return text


def install_profile(path, settings, stamp):
    if path.is_symlink():
        raise RuntimeError('Refusing to replace a symlinked profile')
    previous = path.read_text() if path.exists() else ''
    text = profile_text(previous, settings)
    backup = None
    if text != previous:
        if path.exists():
            backup = path.with_name(path.name + '.before-' + stamp)
            if backup.exists():
                raise RuntimeError('Backup already exists; refusing to overwrite it')
            shutil.copy2(path, backup)
        # Truncate the existing regular file in place to retain its access mode.
        # New files use the operator's existing umask. No chmod/permission changes.
        with path.open('w', encoding='utf-8') as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
    return str(backup) if backup else None


def codex_processes():
    """Only executable/start identity/cwd, never command-line secrets or environment."""
    processes = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            executable = (proc / 'exe').resolve(strict=True)
            if 'codex' not in executable.name:
                continue
            stat = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
            processes.append({'pid': int(proc.name), 'executable': str(executable),
                              'start_ticks': stat[19], 'cwd': str((proc / 'cwd').resolve())})
        except (OSError, ValueError):
            continue
    return processes


def launch_args(executable, record):
    prompt = (
        'Continue the explicitly authorized three-phase PDF-to-LaTeX task. '
        f'Read {TASK} IN FULL and {HANDOVER}, then the setup record {record}. '
        'This is the requested fresh session, not another parallel coding writer. '
        'First verify Phase 1 from THIS session runtime evidence: exact model/effort, '
        'ChatGPT authentication, effective context, auto-compaction threshold/scope '
        'and executing client/server. A configured value is not an observed value; '
        'record long-context exercised=false. Do not repeat installation if the setup '
        'record already confirms the selected stable version. Then independently '
        'review the existing repair (Phase 2) and implement/qualify the narrow '
        'supervisor (Phase 3), preserving all completed work. Rediscover suite state '
        'and writers before any bound-file edit. Never launch the production queue. '
        'Do not resume this historical chat or load its full transcript. Follow '
        'AGENTS.md, leave changes unstaged and preserve sandbox/permission boundaries.'
    )
    return [str(executable), '--no-daemon', '--strict-config', '--profile', PROFILE,
            '--cd', str(ROOT), prompt]


def main():
    if len(sys.argv) != 1:
        raise RuntimeError('No arguments: this entry point performs Phase 1 and opens the remaining task')
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise RuntimeError('Run in your normal interactive terminal; no detached/parallel setup here')
    if not TASK.is_file() or not HANDOVER.is_file():
        raise RuntimeError('The full task or saved handover is missing')
    codex_home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))).resolve()
    visible = Path.home() / '.local/bin/codex'
    executable = visible.resolve(strict=True)
    if 'standalone/releases/' not in str(executable):
        raise RuntimeError('Installation no longer matches the inspected standalone CLI; inspect before updating')
    chatgpt_login(executable)
    old_version = cli_version(executable)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    evidence = ROOT / 'results' / ('codex-setup-' + stamp)
    evidence.mkdir(parents=True)
    record_path = evidence / 'setup.json'
    base = codex_home / 'config.toml'
    base_hash = digest(base) if base.exists() else None
    record = {'at_utc': stamp, 'status': 'starting', 'old_executable': str(executable),
              'old_version': old_version, 'old_executable_sha256': digest(executable),
              'base_config_sha256': base_hash, 'task_path': str(TASK), 'task_sha256': digest(TASK),
              'processes_before': codex_processes(), 'shared_daemon_action': 'none; fresh --no-daemon session',
              'authentication': 'ChatGPT', 'long_context_exercised': False}
    def save():
        record_path.write_text(json.dumps(record, indent=2) + '\n')
    save()
    # Own only this setup/fresh task; this is not a book writer lock.
    lock = (ROOT / 'results/codex-supervision-setup.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise RuntimeError('A setup/fresh task already owns the setup lock; no second session started')
    try:
        print('Checking the current public stable CLI via its supported updater. Shared daemon is left alone.', flush=True)
        # This inspected stable standalone build supports self-update. No pinned
        # "latest", preview channel, npm installation, or system-Python change.
        subprocess.run([str(executable), 'update'], check=True,
                       env={**os.environ, 'CODEX_NON_INTERACTIVE': '1'})
        executable = visible.resolve(strict=True)
        version = cli_version(executable)
        if tuple(map(int, version.split('.'))) < tuple(map(int, old_version.split('.'))):
            raise RuntimeError('Updater selected an older version; refusing an automatic downgrade')
        help_text = captured([str(executable), '--help'])
        if not all(token in help_text for token in ('--no-daemon', '--strict-config', '<name>.config.toml')):
            raise RuntimeError('Updated CLI profile/session syntax changed; leave configuration untouched')
        chatgpt_login(executable)
        # Refresh actual account model discovery, not a fabricated model catalog.
        p = subprocess.run([str(executable), 'debug', 'models'], capture_output=True, text=True, timeout=90)
        if p.returncode:
            raise RuntimeError('Current model discovery failed; configuration is unchanged (raw output withheld)')
        catalog = json.loads(p.stdout)
        models = catalog.get('models', []) if isinstance(catalog, dict) else catalog
        matches = [m for m in models if m.get('slug') == MODEL]
        if len(matches) != 1:
            raise RuntimeError('Expected exactly one gpt-6-astra catalog entry')
        settings = select_settings(matches[0])
        profile = codex_home / (PROFILE + '.config.toml')
        profile_absent = not profile.exists()
        backup = install_profile(profile, settings, stamp)
        if (digest(base) if base.exists() else None) != base_hash:
            raise RuntimeError('Base config changed during setup; preserve both versions and inspect before launch')
        record.update(status='configured_not_runtime_verified', executable=str(executable), version=version,
                      executable_sha256=digest(executable), profile=str(profile), profile_backup=backup,
                      profile_previously_absent=profile_absent,
                      profile_sha256=digest(profile), requested=settings,
                      catalog={k:matches[0].get(k) for k in ('slug','context_window','max_context_window',
                                'effective_context_window_percent','supports_experimental_context')},
                      processes_after=codex_processes(),
                      rollback='Use old_executable directly; restore profile_backup if present, otherwise '
                               'omit --profile to use the untouched base configuration. Do not restart shared sessions.')
        # The 95% factor is metadata, not a measurement in the fresh task.
        record['expected_effective_context_unverified'] = settings['model_context_window'] * matches[0]['effective_context_window_percent'] // 100
        record['expected_post_threshold_headroom_unverified'] = record['expected_effective_context_unverified'] - settings['model_auto_compact_token_limit']
        save()
        print(f'CLI {version}; profile {profile}; requested window {settings["model_context_window"]:,}, '
              f'compaction {settings["model_auto_compact_token_limit"]:,} total. Runtime verification is next.', flush=True)
        print(f'Setup/rollback record: {record_path}', flush=True)
        print('Opening one fresh task with the full instructions already supplied. No book worker started.', flush=True)
        # Retain the setup lock for this child. No --remote, sandbox override,
        # approval override, API key, credential copy, or daemon restart.
        result = subprocess.run(launch_args(executable, record_path))
        record['fresh_session_exit_code'] = result.returncode
        save()
        return result.returncode
    except Exception as exc:
        record.update(status='setup_blocked', error_type=type(exc).__name__)
        save()
        raise


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f'Codex setup stopped: {exc}', file=sys.stderr)
        raise SystemExit(1)
