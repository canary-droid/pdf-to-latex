#!/usr/bin/env python3
"""Guarded copy-back for this isolated Task 2; does not change Git or services itself."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from probe.common import read_json,sha,atomic_json,writer_lock
import editorial_chapters as editorial
ORIGINAL=editorial.ORIGINAL
SESSION='editorial-chapters'


def validate_destinations(manifest, source=ROOT, destination=ORIGINAL):
    for relative,record in manifest['files'].items():
        src=source/relative;dst=destination/relative
        if src.is_symlink() or not src.is_file() or sha(src)!=record['after']:raise ValueError('Development bundle changed: '+relative)
        old=record['before']
        if old is None:
            if dst.exists():raise ValueError('New destination already exists: '+relative)
        elif not dst.is_file() or dst.is_symlink() or sha(dst)!=old:
            raise ValueError('Destination changed since development baseline: '+relative+'; reconcile without overwriting')


def integrate():
    manifest=read_json(ROOT/'development/copy-back.json')
    complete,why=editorial.extraction_complete()
    if not complete:raise RuntimeError(why+'; no original files changed')
    # Participating project writers all use the same lock; workers must also be absent.
    with writer_lock(ORIGINAL):
        editorial.converter_idle(ORIGINAL)
        validate_destinations(manifest)
        run=Path(read_json(editorial.POINTER)['run']);state=editorial.verify(run)
        if state['calls']:raise ValueError('Expected offline preparation only; do not duplicate a live trial')
        dest=ORIGINAL/'runs'/run.name
        if dest.exists():raise ValueError('Prepared run destination exists; use original status/resume, never copy again')
        # All conflict checks completed before the first copy. Metadata and raw original books remain untouched.
        for relative in manifest['files']:
            dst=ORIGINAL/relative;dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/relative,dst)
        shutil.copytree(run,dest)
        for relative,record in manifest['files'].items():
            if sha(ORIGINAL/relative)!=record['after']:raise RuntimeError('Copy verification failed: '+relative)
        bundle=Path(manifest['bundle']);target=ORIGINAL/'results'/bundle.name
        if target.exists():raise ValueError('Bundle destination exists; no overwrite')
        shutil.copyfile(bundle,target)
        atomic_json(ORIGINAL/'results/editorial-chapters-current.json',{'run':str(dest),'development':str(ROOT),'copy_back_manifest':manifest})
        print('Integrated only reviewed changed files. Prepared run:',dest,'Patch:',target,flush=True)
    return dest


def worker():
    logpath=ROOT/'development/continuation-launch.log'
    with logpath.open('a',buffering=1) as log:
        os.dup2(log.fileno(),1);os.dup2(log.fileno(),2)
        print('Stage: wait read-only for owned Bergomi extraction to finish successfully. No deadline or checkout writes.',flush=True)
        while True:
            done,why=editorial.extraction_complete()
            if done:break
            state=read_json(editorial.BERGOMI/'state.json')
            # A live/finishing writer may update its exit record shortly. Paused/failed work must be resumed explicitly.
            if state['status'] not in ('running','conversion_completed_unreviewed') or 'failed exit' in why:
                raise RuntimeError(why+'; extraction must be resumed, not bypassed')
            if (ROOT/'development/pause-bootstrap.json').exists():raise RuntimeError('Operator paused bootstrap; no copy-back performed')
            print(time.strftime('%Y-%m-%d %H:%M:%S'),'Waiting:',why,flush=True);time.sleep(30)
        dest=integrate()
        # One normal-terminal full suite, not one suite per chapter. No real compiler tests unless explicitly configured by operator.
        print('Stage: one normal-terminal full suite before services/inference.',flush=True)
        testlog=dest/'normal-terminal-tests.log'
        with testlog.open('w') as output:
            result=subprocess.run([str(ORIGINAL/'.venv-control/bin/python'),'-B','-m','unittest','discover','-s','tests','-v'],
                cwd=ORIGINAL,stdout=output,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        if result.returncode:raise RuntimeError('Full suite failed; no inference. See '+str(testlog))
        # Re-enter integrated code so all imports/bindings refer to the authoritative execution checkout.
        os.execv(str(ORIGINAL/'.venv-control/bin/python'),[str(ORIGINAL/'.venv-control/bin/python'),'-B','-u',
                 str(ORIGINAL/'scripts/editorial_chapters.py'),'start-worker','--run',str(dest)])


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('run','worker','status','pause','resume','bundle'));a=p.parse_args()
    if ROOT==ORIGINAL:
        raise RuntimeError('This bootstrap is for the isolated development directory; use run-editorial-chapters.sh after integration')
    pointer=ORIGINAL/'results/editorial-chapters-current.json'
    integrated=pointer.is_file() and read_json(pointer).get('development')==str(ROOT)
    if integrated and a.action!='worker':
        return subprocess.call(['bash',str(ORIGINAL/'scripts/run-editorial-chapters.sh'),a.action])
    if a.action=='status':
        print('Development directory:',ROOT,'\nPrepared report:',Path(read_json(editorial.POINTER)['run'])/'report.html','\nLog:',ROOT/'development/continuation-launch.log')
        print('Bergomi:',editorial.extraction_complete());return 0
    if a.action=='pause':atomic_json(ROOT/'development/pause-bootstrap.json',{'requested':True});print('Bootstrap pause requested; OCR untouched.');return 0
    if a.action=='bundle':print(read_json(ROOT/'development/copy-back.json')['bundle']);return 0
    if a.action=='worker':worker();return 0
    probe=subprocess.run(['tmux','has-session','-t',SESSION],capture_output=True,text=True)
    if probe.returncode==0:raise RuntimeError('Persistent continuation already exists; inspect status or tmux attach -t '+SESSION)
    if probe.returncode!=1 or any(x in probe.stderr.lower() for x in ('permission denied','operation not permitted')):raise RuntimeError('Cannot access tmux: '+probe.stderr)
    (ROOT/'development/pause-bootstrap.json').unlink(missing_ok=True)
    cmd=shlex.join([str(ORIGINAL/'.venv-control/bin/python'),'-B','-u',str(Path(__file__)),'worker'])
    subprocess.run(['tmux','new-session','-d','-s',SESSION,'cd '+shlex.quote(str(ROOT))+' && '+cmd+
                    '; result=$?; echo "Continuation exit status: $result; inspect development/continuation-launch.log"; exit "$result"'],check=True)
    print('Persistent session:',SESSION,'\nIt waits for successful OCR exit, checks copy-back conflicts, tests once, starts regular GLM if absent, captures readiness, then runs the serial queue.')
    print('Log:',ROOT/'development/continuation-launch.log','\nStatus: bash',ROOT/'scripts/run-editorial-continuation.sh','status')
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:print('ERROR:',exc,file=sys.stderr,flush=True);raise
