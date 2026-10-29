"""Controlled compiler provisioning, separate from isolated untrusted TeX execution.

Only fixed Debian package names are allowed. Missing assets or unknown/custom
macros never cause installs, model repairs, or a network-enabled document build.
"""
from pathlib import Path
import re
import shutil
import subprocess
import time

from .common import atomic_json, read_json, sha, files_manifest
from .experiment import verify_seal
from . import tex_compile

STANDARD = ('texlive-latex-base', 'texlive-latex-recommended', 'texlive-latex-extra',
            'texlive-fonts-recommended', 'texlive-science', 'texlive-pictures', 'lmodern', 'cm-super')
OPTIONAL = ('texlive-plain-generic',)
PACKAGES = {'enumitem.sty': 'texlive-latex-extra', 'lmodern.sty': 'lmodern',
            'caption.sty': 'texlive-latex-recommended', 'subcaption.sty': 'texlive-latex-extra',
            'siunitx.sty': 'texlive-science', 'tikz.sty': 'texlive-pictures',
            'mathtools.sty': 'texlive-latex-recommended', 'booktabs.sty': 'texlive-latex-recommended',
            'microtype.sty': 'texlive-latex-recommended', 'amsthm.sty': 'texlive-latex-base',
            'ulem.sty': 'texlive-plain-generic'}


def missing_dependency(log):
    match = re.search(r"LaTeX Error: File [`']([^`'\n]+)' not found", log)
    if not match: return None
    name = match[1]
    return {'filename': name, 'kind': 'package' if name.endswith(('.sty', '.cls')) else 'asset_or_include',
            'approved_debian_package': PACKAGES.get(name), 'diagnostic': match[0]}


def ensure(run, state, root, *, extra=(), runner=subprocess.run):
    """Explicit operator launch calls this; offline preparation never builds."""
    previous = state.get('compiler_environment')
    wanted = sorted(set(STANDARD) | set(extra) | set(previous['packages'] if previous else ()))
    if not set(wanted) <= set(STANDARD + OPTIONAL): raise ValueError('Unapproved compiler dependency')
    if previous:
        verify_seal(run / previous['path'], previous['seal'])
        if set(wanted) <= set(previous['packages']): return previous['image']
    folder = run / 'compiler-environments' / str(time.time_ns()); context = folder / 'context'
    context.mkdir(parents=True)
    source = root / 'scripts/tex-compiler/Dockerfile'; shutil.copyfile(source, context / 'Dockerfile')
    iid = folder / 'image.id'
    cmd = ['docker', 'build', '--pull=false', '--network=default', '--iidfile', str(iid),
           '--build-arg', 'PDF2TEX_PACKAGES=' + ' '.join(wanted), str(context)]
    record = {'argv': cmd, 'packages': wanted, 'dockerfile_sha256': sha(source),
              'phase': 'compiler_environment_only', 'document_inputs': [],
              'network': 'Debian/image provisioning only; compilation remains --network=none', 'status': 'building'}
    atomic_json(folder / 'preparation.json', record)
    print('Compiler environment: preparing standard LaTeX packages; log:', folder / 'build.log', flush=True)
    with (folder / 'build.log').open('wb') as log:
        result = runner(cmd, stdout=log, stderr=subprocess.STDOUT, check=False)
    record['returncode'] = result.returncode
    if result.returncode or not iid.is_file():
        record['status'] = 'environment_build_failed'; atomic_json(folder / 'result.json', record)
        raise RuntimeError('Compiler environment build failed; saved TeX unchanged. See ' + str(folder / 'build.log'))
    image = iid.read_text().strip()
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', image): raise ValueError('Compiler build did not produce an immutable image ID')
    # A real smoke build, with the two observed dependencies and a relative input.
    asset = folder / 'qualification-input.tex'; asset.write_text('Relative input preserved.\n')
    document = (r'\documentclass{article}\usepackage{enumitem,lmodern,amsmath,graphicx}'
                r'\begin{document}\input{parts/check.tex}\begin{enumerate}[label=(\alph*)]\item $x^2$.\end{enumerate}\end{document}')
    qualification = tex_compile.compile_document(document, folder / 'qualification', image=image,
                    assets={'parts/check.tex': asset}, passes=2)
    record.update(image=image, qualification=qualification['status'], status='qualified' if qualification['compilation_claim'] else 'qualification_failed')
    atomic_json(folder / 'result.json', record)
    atomic_json(folder / 'manifest.json', files_manifest(folder))
    if record['status'] != 'qualified': raise RuntimeError('Compiler image qualification failed; see ' + str(folder))
    state['compiler_environment'] = {'image': image, 'packages': wanted, 'path': str(folder.relative_to(run)),
                                     'seal': sha(folder / 'manifest.json')}
    atomic_json(run / 'state.json', state)
    return image


def compile_saved(run, state, root, document, folder, assets, *, compiler=tex_compile.compile_document, provision=ensure):
    """At most one dependency-only recovery; same document/assets in both attempts."""
    environment = state.get('compiler_environment')
    if not environment: raise ValueError('Compiler environment must be provisioned separately before document compilation')
    verify_seal(run / environment['path'], environment['seal'])
    first = compiler(document, folder / 'attempt-1', image=environment['image'], assets=assets, passes=2)
    first['path'] = str((folder / 'attempt-1').relative_to(run))
    attempts = [first]
    log = folder / 'attempt-1/console.log'
    missing = missing_dependency(log.read_text()) if log.is_file() else None
    if missing:
        first['missing_dependency'] = missing
        package = missing['approved_debian_package']
        if package and package not in environment['packages']:
            image = provision(run, state, root, extra=(package,))
            second = compiler(document, folder / 'attempt-2', image=image, assets=assets, passes=2)
            second['path'] = str((folder / 'attempt-2').relative_to(run)); attempts.append(second)
        else:
            first['dependency_recovery'] = 'deferred: unknown/custom asset or package already provisioned; no install loop'
    record = {'status': attempts[-1]['status'], 'attempts': attempts,
              'document_changed': False, 'model_repair_requested': False}
    atomic_json(folder / 'compilation.json', record)
    return record
