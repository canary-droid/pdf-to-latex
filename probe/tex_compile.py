"""Optional compiler adapter. Docker image is explicit and never pulled here.

Only a disposable build folder is mounted. The compiler receives no project/home,
credentials, networking, or Docker socket. No-shell-escape is an extra restriction,
not the filesystem boundary. No host compiler fallback.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import time

from .common import atomic_json, files_manifest, sha
from .portable_export import portable_document


def command(image,work,engine='pdflatex',timeout=90):
    if not re.fullmatch(r'sha256:[a-f0-9]{64}',image):raise ValueError('Use an actual immutable compiler image ID, not a mutable tag')
    if engine!='pdflatex':raise ValueError('Only the recorded pdfLaTeX UTF-8/T1 profile is qualified by this adapter')
    # Paranoid input policy rejects absolute filenames. Resolve relative inputs
    # and assets from the read-only source tree; write every output under /work.
    return ['docker','run','--rm','--pull=never','--network=none','--read-only',
        '--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=64','--memory=512m','--memory-swap=512m','--cpus=1',
        '--user',f'{os.getuid()}:{os.getgid()}',
        '--mount',f'type=bind,src={Path(work)/"source"},dst=/source,readonly',
        '--mount',f'type=bind,src={Path(work)/"build"},dst=/work',
        '--tmpfs','/tmp:rw,nosuid,nodev,noexec,size=67108864','--workdir','/source',
        '--env','HOME=/tmp','--env','TEXMFVAR=/tmp/texmf-var','--env','TEXMFCONFIG=/tmp/texmf-config',
        '--env','TEXMFOUTPUT=/work',
        '--env','openin_any=p','--env','openout_any=p','--log-driver=none',
        '--entrypoint','timeout',image,'--signal=KILL',str(max(1,timeout-5)),
        engine,'-no-shell-escape','-interaction=nonstopmode','-halt-on-error','-file-line-error',
        '-output-directory=/work','document.tex']


def classify_log(text,returncode):
    # Docker CLI versions can return 1 (not only 125) before any TeX process.
    if re.search(r'permission denied[^\n]*(?:docker API|docker daemon|docker\.sock)|'
                 r'cannot connect to the docker daemon',text,re.I):
        return 'unavailable'
    # A policy refusal can be followed by "Emergency stop" without TeX ever
    # reading the document. It is an adapter failure, never a syntax repair.
    if re.search(r'Not reading from[^\n]*\(\s*openin_any\s*=[^)]*\)|'
                 r'Not writing to[^\n]*\(\s*openout_any\s*=[^)]*\)',text,re.I):
        return 'adapter_configuration_failure'
    if returncode==0:
        return 'passed_with_unresolved_references' if re.search(r'(undefined references|Citation .* undefined|Reference .* undefined)',text,re.I) else 'passed'
    if ('LaTeX Error: File ' in text and 'not found' in text) or re.search(r'language definition file\s+french\.ldf\s+was not found',text):return 'missing_package_or_asset'
    if 'Unicode character' in text or 'requires either XeTeX or LuaTeX' in text:return 'wrong_engine_or_encoding'
    if 'Undefined control sequence' in text:return 'missing_context_or_macro'
    if any(x in text for x in ('Missing $ inserted','Extra },','Missing } inserted','Emergency stop','Runaway argument')):return 'syntax_failure'
    return 'build_failure_unresolved'


def stage_assets(assets, destination=None):
    """Explicit caller allowlist only, never follow TeX-supplied filenames.

    Relative assets/ and parts/ paths permit chapter figures and master includes.
    No symlinks (including parents), traversal, executable formats or overwrite.
    """
    records=[];total=0
    if len(assets)>2000:raise ValueError('Too many compiler assets')
    for relative, source in sorted(assets.items()):
        p=Path(relative);source=Path(source).absolute()
        if (not re.fullmatch(r'(assets|parts)/[A-Za-z0-9_./-]+',relative)
                or any(x in ('..','.') for x in relative.split('/'))
                or p.suffix.lower() not in ('.png','.jpg','.jpeg','.pdf','.tex')):
            raise ValueError('Unsafe compiler asset path: '+relative)
        if any(x.is_symlink() for x in (source,*source.parents)) or not source.is_file():
            raise ValueError('Missing or symlink compiler asset: '+str(source))
        total+=source.stat().st_size
        if total>256*1024*1024:raise ValueError('Compiler assets exceed 256 MiB')
        record={'path':relative,'sha256':sha(source),'bytes':source.stat().st_size};records.append(record)
        if destination is not None:
            target=Path(destination)/p;target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():raise ValueError('Compiler asset collision')
            shutil.copyfile(source,target)
            if sha(target)!=record['sha256']:raise ValueError('Compiler asset changed during staging')
    return records


def compile_document(document,out,*,image=None,timeout=90,runner=subprocess.run,assets=None,
                     template='probe.portable_export.portable_document',passes=1):
    if type(passes) is not int or passes not in (1,2):raise ValueError('Compiler supports one or two bounded passes')
    assets=assets or {};asset_records=stage_assets(assets)
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    (out/'document.tex').write_text(document,encoding='utf-8')
    result={'schema':'isolated-tex-build-v1','status':'unavailable','engine':'pdflatex',
        'template':template,'input_sha256':sha(out/'document.tex'),
        'image_id':image,'compilation_claim':False,'timeout_seconds':timeout,'assets':asset_records,
        'passes_requested':passes,'passes_completed':0}
    if not image:
        result['reason']='No explicit isolated compiler image supplied; no host compiler fallback'
    elif not shutil.which('docker'):
        result['reason']='Docker client unavailable; isolated operator setup required'
    else:
        if not 1<=timeout<=120:raise ValueError('Compiler timeout must be 1–120 seconds')
        # Only explicit allowlisted caller assets join the exact document.
        with tempfile.TemporaryDirectory(prefix='pdf2tex-build-') as tmp:
            work=Path(tmp);(work/'source').mkdir();(work/'build').mkdir()
            shutil.copyfile(out/'document.tex',work/'source/document.tex')
            if stage_assets(assets,work/'source')!=asset_records:raise ValueError('Compiler assets changed')
            started=time.monotonic()
            for pass_number in range(1,passes+1):
                remaining=timeout if pass_number==1 else max(1,int(timeout-(time.monotonic()-started)))
                if pass_number>1 and time.monotonic()-started>=timeout:
                    result.update(status='timeout',compilation_claim=False,reason='Shared compiler time budget expired before second pass');break
                cmd=command(image,work,timeout=remaining);atomic_json(out/'execution.json',{'argv':cmd,'network':'none','mounts':'disposable build directory only',
                    'memory_bytes':536870912,'pids':64,'no_shell_escape':True,'pass':pass_number,'passes_requested':passes})
                try:
                    run=runner(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=remaining,check=False,
                        env={'PATH':os.environ.get('PATH','/usr/bin:/bin'),'HOME':tmp})
                    log=run.stdout.decode('utf-8','replace');(out/'console.log').write_text(log)
                    diagnostics=log
                    for name in ('document.log','texput.log'):
                        p=work/'build'/name
                        if p.is_file() and not p.is_symlink():diagnostics+='\n'+p.read_text(encoding='utf-8',errors='replace')
                    status='unavailable' if run.returncode in (125,126,127) else 'timeout' if run.returncode in (124,137) else classify_log(diagnostics,run.returncode)
                    result.update(status=status,returncode=run.returncode,
                        compilation_claim=status.startswith('passed'),compiler_banner=log.splitlines()[0] if log else None)
                    if status.startswith('passed'):result['passes_completed']+=1
                except subprocess.TimeoutExpired as exc:
                    result.update(status='timeout',compilation_claim=False,reason='Compiler wall-clock limit exceeded')
                    (out/'console.log').write_bytes(exc.stdout or b'')
                except OSError as exc:
                    result.update(status='unavailable',compilation_claim=False,reason=str(exc))
                    (out/'console.log').write_text(str(exc)+'\n')
                if passes>1:
                    evidence=out/f'pass-{pass_number}';evidence.mkdir()
                    for name in ('console.log','execution.json'):
                        if (out/name).is_file():shutil.copyfile(out/name,evidence/name)
                    for name in ('document.log','texput.log','document.aux'):
                        p=work/'build'/name
                        if p.is_file() and not p.is_symlink():shutil.copyfile(p,evidence/name)
                    atomic_json(evidence/'outcome.json',{k:v for k,v in result.items() if k!='assets'})
                if not result['compilation_claim']:break
            for name in ('document.log','texput.log','document.aux','document.pdf'):
                p=work/'build'/name
                if p.is_file() and not p.is_symlink():shutil.copyfile(p,out/name)
    result['outputs']=files_manifest(out);atomic_json(out/'result.json',result)
    return result


def compare(original,proposed,out,packages=(),*,image=None,context=()):
    """Equivalent union of packages/context, with original and proposal preserved."""
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    before=compile_document(portable_document([*context,original],packages),out/'original',image=image)
    after=compile_document(portable_document([*context,proposed],packages),out/'proposed',image=image)
    status='unavailable'
    if 'adapter_configuration_failure' in (before['status'],after['status']):status='adapter_configuration_failure'
    elif before['status'].startswith('passed') and after['status']=='syntax_failure':status='proposal_attributable_syntax_failure'
    elif before['status'].startswith('passed') and after['status'].startswith('passed'):status='both_compiled'
    elif before['status']!='unavailable' and after['status']!='unavailable':status='preexisting_or_context_failure_unresolved'
    record={'status':status,'original':before,'proposed':after,
        'fidelity':'not_assessed_by_compiler','compiler_feedback_eligible':status=='proposal_attributable_syntax_failure'}
    atomic_json(out/'comparison.json',record);return record


def feedback(comparison,original,candidate,build):
    if not comparison['compiler_feedback_eligible']:raise ValueError('Compiler failure is not attributable to this proposal')
    p=Path(build)/'proposed/console.log';log=p.read_text()
    # Diagnostics alone are bounded; full candidate/context is never clipped.
    return {'original_fragment':original,'full_candidate':candidate,'diagnostics':log[:8000],
        'diagnostics_truncated':len(log)>8000,'full_log_sha256':sha(p)}
