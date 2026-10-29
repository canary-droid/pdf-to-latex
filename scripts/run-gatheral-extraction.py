#!/usr/bin/env python3
"""Operator convenience around the existing converter; no new execution engine."""
import argparse
import contextlib
from pathlib import Path
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from probe import cli
from probe.common import read_json, writer_lock, windows


def saved_run(root, source_id='gatheral'):
    matches = []
    for path in sorted((root / 'runs').glob('convert-*/state.json')):
        state = read_json(path)
        sources = state.get('settings', {}).get('sources', {})
        if any(source_id == key or f'/{source_id}/' in ('/' + source.get('pdf', ''))
               for key, source in sources.items()):
            if set(sources) != {source_id} or state['settings']['tier'] != 'basic':
                raise ValueError(f'Existing {source_id} run has a different scope/profile: ' + str(path.parent))
            matches.append((path.parent, state))
    if len(matches) > 1:
        raise ValueError(f'Multiple {source_id} conversions exist; inspect them before selecting a resume.')
    return matches[0] if matches else (None, None)


class Tee:
    def __init__(self, terminal, log):
        self.terminal, self.log = terminal, log

    def write(self, text):
        self.terminal.write(text)
        self.log.write(text)
        self.flush()
        return len(text)

    def flush(self):
        self.terminal.flush()
        self.log.flush()


def status(root, source_id='gatheral'):
    run, state = saved_run(root, source_id)
    if run is None:
        print(f'No {source_id} conversion created yet. Startup fingerprints the model cache before creating a run.')
        logs = sorted(p for p in (root / 'runs' / (source_id+'-operator')).glob('*.log') if p.stem[:8].isdigit())
        if logs:
            print('Latest terminal log:', logs[-1])
        return 0
    print('Conversion run:', run)
    print('Recorded status:', state['status'], '(saved state is not proof a process is still running)')
    units = state['units']
    done = [r for r in units.values() if r['status'] == 'completed']
    pages = sum(r['window']['owned_end'] - r['window']['owned_start'] + 1 for r in done)
    settings = state['settings']; count = settings['sources'][source_id].get('pages')
    if count is None and source_id == 'gatheral': count = 210  # Legacy Gatheral records.
    plan = list(windows(count, settings.get('window_pages', 8), settings.get('overlap_pages', 1)))
    print(f'Completed owned pages: {pages}/{count}; windows: {len(done)}/{len(plan)}')
    print('Pending windows:', len(plan)-len(units), '; failed/interrupted:', len(units)-len(done)-sum(r['status']=='running' for r in units.values()))
    for name, record in units.items():
        if record['status'] != 'completed':
            attempt = run / record['attempt']
            print(name, record['status'], 'worker log:', attempt / 'worker.log')
            if (attempt / 'interrupted.json').exists():
                print('  Interrupted attempt retained; resume retries this window.')
    return 0


def launch(root, source_id='gatheral', *, before_convert=None):
    # Use the converter's existing project-wide lock before discovery, avoiding
    # a race between choosing a new run and another writer creating one.
    with writer_lock(root / 'runs'):
        run, _ = saved_run(root, source_id)
        if before_convert: before_convert()
        args = ['--config', str(root / 'config.example.json'), 'convert',
                '--source', source_id, '--tier', 'basic', '--ocr-isolation', 'none',
                '--converter-python', str(root / '.venv-mineru/bin/python'),
                '--models-dir', str(root / 'model-cache')]
        if run is not None:
            args += ['--resume', str(run)]
        logs = root / 'runs' / (source_id+'-operator')
        logs.mkdir(parents=True, exist_ok=True)
        log_path = logs / (cli.stamp() + '.log')
        with log_path.open('x', encoding='utf-8') as log:
            with contextlib.redirect_stdout(Tee(sys.stdout, log)), contextlib.redirect_stderr(Tee(sys.stderr, log)):
                print('Execution directory:', root)
                print('Terminal log:', log_path)
                print('Action:', 'resume ' + str(run) if run else f'new {source_id} conversion')
                code = 2
                try:
                    # Same parser and implementation as probe.py; lock held above.
                    parsed = cli.parser().parse_args(args)
                    code = parsed.func(parsed)
                except KeyboardInterrupt:
                    print('Paused by Ctrl-C; completed windows and interrupted evidence retained.')
                    code = 130
                except Exception:
                    traceback.print_exc()
                finally:
                    print('Converter exit status:', code)
                return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('run', 'status'), help='run starts or resumes; pause with Ctrl-C in its tmux pane')
    args = parser.parse_args(argv)
    try:
        return status(ROOT) if args.action == 'status' else launch(ROOT)
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print('Gatheral launcher stopped:', exc, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
