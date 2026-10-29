#!/usr/bin/env python3
"""Bergomi intake and persistent operator launch around the existing MinerU converter."""
import argparse
import contextlib
import importlib.util
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.book_extraction_intake import prepare
from probe.common import atomic_json, read_json, sha, writer_lock
from probe import cli, chapter_protocol
from probe.local_model import LocalClient
from probe.saved_pages import converter_idle
from probe.system_probe import memory_inventory, memory_policy

spec = importlib.util.spec_from_file_location('book_launcher', ROOT/'scripts/run-gatheral-extraction.py')
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
SOURCE = 'bergomi'
SESSION = 'bergomi-extraction'
GLM = Path('/home/mdi/local-llm/glm53-flash-tensorfold')
PEER = 'mdi@192.168.100.2'
CONTAINER = 'glm53-flash-tf'
GATHERAL = ROOT/'runs/simple-chapter-glm-trial-20261026T212942Z-533351'


def checked(command, *, cwd=None, timeout=20):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError('Command failed: '+shlex.join(map(str, command))+'\n'+result.stderr.strip()+'\n'+result.stdout.strip())
    return result.stdout


def peer(command):
    return ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', PEER, command]


def project_idle():
    converter_idle(ROOT)
    if GATHERAL.exists():
        state = read_json(GATHERAL/'state.json')
        if state['status'] == 'running' or any(c['status']=='in_progress' for c in state['calls']):
            raise ValueError('Gatheral still has an active/uncertain writer; do not interrupt it')
    hits = []
    for process in Path('/proc').iterdir():
        if not process.name.isdigit() or int(process.name) == os.getpid(): continue
        try:
            if process.stat().st_uid != os.getuid(): continue
            args = [a.decode(errors='replace') for a in (process/'cmdline').read_bytes().split(b'\0') if a]
            if '-m' in args:
                i = args.index('-m'); module = args[i+1] if i+1<len(args) else ''
                if module.startswith(('probe.', 'scripts.simple_chapter_glm')) and any(a in args for a in ('worker','run','launch','ready','gate','continue','execute')):
                    hits.append(process.name)
        except (FileNotFoundError, ProcessLookupError): continue
    if hits: raise ValueError('Other project model jobs still active: '+', '.join(hits))


def deployments():
    result = {}
    for node, cmd in [('head',['docker','ps','--format','{{.Names}}']),
                      ('peer',peer("docker ps --format '{{.Names}}'"))]:
        names = checked(cmd).splitlines(); result[node] = names
        # Open WebUI is a client. Actual GLM inference is checked via health below.
        unknown = set(names)-{CONTAINER, 'open-webui', 'open_webui'}
        if unknown: raise ValueError(f'Other deployment on {node}; left untouched: {sorted(unknown)}')
    return result


def arrange_resources(folder, *, stop_glm):
    project_idle()
    config = checked(['bash','-c', 'source ./scripts/config.sh; printf "%s\\n" "$CONTAINER_NAME" "$WORKER" "$WORKER2" "$PORT"'], cwd=GLM).splitlines()
    if config != [CONTAINER, PEER, '', '8888']:
        raise ValueError('GLM helper configuration differs from verified two-node deployment; no service change')
    before = deployments(); atomic_json(folder/'deployments-before.json', before)
    resident = any(CONTAINER in names for names in before.values())
    if resident:
        if CONTAINER not in before['head']: raise ValueError('Only GLM peer is present; cannot establish idle inference safely')
        client = LocalClient('http://127.0.0.1:8888/v1', 'glm53-regular', purpose='chapter', timeout=10)
        client.discover_model(folder/'glm-idle-check')
        health, _ = client.chapter_health(folder/'glm-idle-check'); chapter_protocol.health_capacity(health)
        for key in ('requests_running','requests_pending','requests_queued','queue_size'):
            if key in health and (type(health[key]) is not int or health[key] != 0):
                raise ValueError('GLM has pending or active work: '+key)
        if not stop_glm: raise ValueError('GLM became resident before extraction; rerun launch checks, do not overlap')
        print('Stage: stop verified idle regular GLM using its existing two-node helper.', flush=True)
        output = checked(['bash', './stop.sh'], cwd=GLM, timeout=90)
        (folder/'glm-stop.log').write_text(output); print(output, flush=True)
    after = deployments(); atomic_json(folder/'deployments-after.json', after)
    if any(CONTAINER in names for names in after.values()):
        raise ValueError('GLM helper did not release both deployments; no OCR launch')
    head = memory_inventory(); floor = int(read_json(ROOT/'config.example.json')['minimum_available_gib_basic']*1024**3)
    policy = memory_policy(head, floor); remote = checked(peer('free -h'))
    atomic_json(folder/'memory.json', {'head': head, 'policy': policy, 'peer_free_h': remote})
    print('Head available GiB:', round(head['MemAvailable_bytes']/1024**3, 2) if head['MemAvailable_bytes'] else 'unknown')
    print('Peer memory:\n'+remote)
    if policy['status'] != 'meets_minimum': raise ValueError('Head memory does not meet unchanged Basic admission floor')


def identity(cache):
    paths = sorted((ROOT/'probe').glob('*.py')) + [ROOT/'config.example.json', ROOT/'sources.json',
            Path(__file__), ROOT/'scripts/book_extraction_intake.py', ROOT/'scripts/run-gatheral-extraction.py']
    return {'execution_directory': str(ROOT), 'source': read_json(ROOT/'sources.json')[SOURCE],
            'intake_manifest_sha256': sha(cache/'manifest.json'),
            'code_and_configuration': {str(p.relative_to(ROOT)): sha(p) for p in paths},
            'environment': str(ROOT/'.venv-mineru'), 'model_cache': str(ROOT/'model-cache'),
            'runtime_binding': 'Converter records installed packages, model hashes, worker, source, all probe modules and settings in its run fingerprint',
            'task2_rule': 'Work in an independent ordinary development copy while extraction is unfinished. Do not change this checkout, input, environments or cache.'}


def prepare_locked():
    cache, meta = prepare(ROOT, SOURCE)
    cli.selected_sources(SOURCE)  # Existing source-loading validation.
    print(f'Book: {meta["title"]}. Stage: full-PDF MinerU Basic extraction. Pages: {meta["pages"]}.', flush=True)
    print('Source:', ROOT/'inputs/bergomi/source.pdf', '\nNative-text intake/report:', cache/'report.html', flush=True)
    return cache, meta


def start():
    operator = ROOT/'runs/bergomi-operator'; operator.mkdir(parents=True, exist_ok=True)
    launch = operator/('launch-'+cli.stamp()); launch.mkdir()
    with (launch/'terminal.log').open('a', buffering=1) as log, contextlib.redirect_stdout(base.Tee(sys.stdout, log)), contextlib.redirect_stderr(base.Tee(sys.stderr, log)):
        with writer_lock(ROOT), writer_lock(ROOT/'runs'):
            cache, meta = prepare_locked(); project_idle()
            probe = subprocess.run(['tmux','has-session','-t',SESSION], capture_output=True, text=True)
            if probe.returncode == 0: raise ValueError('Bergomi tmux session already exists; use status/attach')
            if probe.returncode != 1 or ('no server running' not in probe.stderr and 'can\'t find session' not in probe.stderr and 'No such file or directory' not in probe.stderr):
                raise ValueError('Cannot inspect tmux sessions: '+probe.stderr.strip())
            for path in (ROOT/'.venv-mineru/bin/python', ROOT/'.venv-control/bin/python', ROOT/'model-cache'):
                if not path.exists(): raise ValueError('Missing existing dependency: '+str(path))
            run, state = base.saved_run(ROOT, SOURCE)
            if state and state['status'] == 'conversion_completed_unreviewed':
                print('Extraction already complete:',run,'No restart.'); return 0
            checks = subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test_bergomi_extraction.py','-v'],
                                    cwd=ROOT, stdout=log, stderr=log)
            if checks.returncode: raise ValueError('Focused launch tests failed; see '+str(launch/'terminal.log'))
            atomic_json(launch/'execution-identity.json', identity(cache))
            arrange_resources(launch, stop_glm=True)
            atomic_json(operator/'current.json', {'launch': str(launch), 'run': str(run) if run else None})
        cmd = [str(ROOT/'.venv-control/bin/python'), '-B', '-u', str(Path(__file__)), 'worker', '--launch', str(launch)]
        checked(['tmux','new-session','-d','-s',SESSION, 'cd '+shlex.quote(str(ROOT))+' && exec '+shlex.join(cmd)])
        print('Persistent session:', SESSION, '\nTerminal log:', launch/'terminal.log')
        print('Conversion run:', run or 'assigned and printed by converter after runtime fingerprinting')
        print('Progress: .venv-control/bin/python -B scripts/run-bergomi-extraction.py status', flush=True)
    return 0


def worker(launch):
    with (launch/'terminal.log').open('a', buffering=1) as log:
        os.dup2(log.fileno(),1); os.dup2(log.fileno(),2)
        code = 2
        try:
            with writer_lock(ROOT):
                expected = read_json(launch/'execution-identity.json')
                if identity(ROOT/'inputs/bergomi/intake') != expected: raise ValueError('Execution identity changed before worker start')
                print('Book: Bergomi. Stage: MinerU Basic, serial owned windows; no GLM conversion.', flush=True)
                code = base.launch(ROOT, SOURCE, before_convert=lambda: arrange_resources(launch/'worker-check', stop_glm=False))
        except KeyboardInterrupt:
            print('Paused; saved windows/attempts preserved.'); code = 130
        except Exception as exc:
            print('ERROR:',exc,flush=True)
        finally:
            run, state = base.saved_run(ROOT,SOURCE)
            atomic_json(launch/'exit.json', {'exit_status':code, 'run':str(run) if run else None,
                                           'status':state['status'] if state else 'not_created'})
            print('Exit status:',code,'Run:',run,'Log:',launch/'terminal.log',flush=True)
    return code


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','run','resume','worker','status','pause','bundle'))
    p.add_argument('--launch',type=Path); a=p.parse_args(argv)
    if a.action=='prepare':
        with writer_lock(ROOT),writer_lock(ROOT/'runs'): prepare_locked()
    elif a.action in ('run','resume'): return start()
    elif a.action=='worker': return worker(a.launch)
    elif a.action=='status':
        intake_path=ROOT/'inputs/bergomi/intake/metadata.json'
        if intake_path.exists():
            meta=read_json(intake_path)
            print('Book:',meta['title'],'; physical pages:',meta['pages'],'; source:',meta['source_pdf'])
        base.status(ROOT,SOURCE)
        pointer=ROOT/'runs/bergomi-operator/current.json'
        if pointer.exists():
            launch=Path(read_json(pointer)['launch']);print('Terminal log:',launch/'terminal.log')
            if (launch/'exit.json').exists():print('Worker exit:',read_json(launch/'exit.json'))
        for path in sorted((ROOT/'runs/bergomi-operator').glob('launch-*/terminal.log'))[-1:]:print('Latest launch log:',path)
    elif a.action=='pause':
        # Existing converter Ctrl-C cleanup stops its child group and preserves attempts.
        panes=checked(['tmux','list-panes','-t',SESSION,'-F','#{pane_pid} #{pane_current_command}']).splitlines()
        if len(panes)!=1: raise ValueError('Ambiguous tmux panes; no signal sent')
        pid=int(panes[0].split()[0]); args=(Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
        if str(Path(__file__)).encode() not in args or b'worker' not in args:
            raise ValueError('Tmux pane is not the owned Bergomi worker; no signal sent')
        os.kill(pid,signal.SIGINT);print('Pause requested. Current window evidence retained; resume retries only incomplete windows.')
    elif a.action=='bundle':
        with writer_lock(ROOT),writer_lock(ROOT/'runs'):
            run,_=base.saved_run(ROOT,SOURCE)
            if run is None: raise ValueError('No extraction run exists yet; intake report is inputs/bergomi/intake/report.html')
            cli.report_run(run);cli.bundle_run(run)
    return 0


if __name__=='__main__':
    try: raise SystemExit(main())
    except (ValueError,RuntimeError,OSError,subprocess.SubprocessError,KeyError) as exc:
        print('Bergomi extraction NOT launched/completed:',exc,file=sys.stderr,flush=True);raise SystemExit(2)
