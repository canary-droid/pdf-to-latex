"""Exact-byte source inventory and portable, immutable library publication.

No model calls, service control, Git operations or metadata database changes.
"""
import os
from pathlib import Path
import re
import shutil
import unicodedata
import uuid
import zipfile

from .common import atomic_json, read_json, sha, files_manifest, contained
from .experiment import verify_seal

PROTOCOL = 'originals-batch-v1'


def slug(text, limit=70):
    value = unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode()
    value = re.sub(r'[^a-zA-Z0-9]+', '-', value).strip('-')[:limit].rstrip('-') or 'unknown'
    if value.upper() in {'CON', 'PRN', 'AUX', 'NUL', *('COM'+str(i) for i in range(10)), *('LPT'+str(i) for i in range(10))}:
        value = 'source-' + value
    return value


def inventory(originals, intake):
    originals, intake = Path(originals), Path(intake)
    old = read_json(intake/'manifest.json')
    metadata = {d['sha256']: d for d in old['documents']}
    docs = {}
    for p in sorted(originals.rglob('*')):
        if p.is_symlink():
            raise ValueError('Symlink in authoritative originals: ' + str(p))
        if not p.is_file() or p.suffix.lower() != '.pdf':
            continue
        digest = sha(p)
        with p.open('rb') as f:
            if not f.read(1024).lstrip().startswith(b'%PDF-'):
                raise ValueError('PDF header missing: ' + str(p))
        if digest not in metadata:
            raise ValueError('Original differs from reviewed intake; explicitly reconcile metadata first: ' + str(p))
        if digest not in docs:
            d = metadata[digest]
            # Reuse a recorded ID when present; the intake otherwise identifies
            # sources by the full SHA256. Never merge different-byte versions.
            ident = d.get('source_id') or 'original-' + digest[:16]
            if not re.fullmatch(r'[A-Za-z0-9_-]+', ident):
                raise ValueError('Unsafe existing source ID')
            name = d['preferred_original_name']
            match = re.match(r'((?:19|20)\d{2})[_ -]+([^_]+)[_ -]+', name)
            author = match[2] if match else d.get('pdf_metadata', {}).get('Author') or 'UnknownAuthor'
            year = match[1] if match else 'UnknownYear'
            folder = slug(author, 28)+'-'+year+'-'+slug(d['title'], 65)+'--'+digest[:16]
            docs[digest] = {**d, 'source_id': ident, 'folder': folder, 'originals': [],
                           'naming_basis': 'Intake filename/author metadata candidates; unknown fields explicit, not bibliographic verification',
                           'existing_identity': d.get('source_id') or digest}
        docs[digest]['originals'].append({'path': str(p), 'name': p.name, 'bytes': p.stat().st_size, 'sha256': digest})
    if not docs:
        raise ValueError('No original PDFs')
    for field in ('source_id', 'folder'):
        values = [d[field].casefold() for d in docs.values()]
        if len(values) != len(set(values)):
            raise ValueError('Source ID / Windows folder collision')
    baseline = {e['sha256'] for e in old['originals_baseline']['entries'] if e.get('pdf_extension')}
    return {'protocol': PROTOCOL, 'originals_root': str(originals), 'intake': str(intake),
            'intake_sha256': sha(intake/'manifest.json'), 'unique_sources': len(docs),
            'occurrences': sum(len(d['originals']) for d in docs.values()),
            'pages': sum(d['page_count'] for d in docs.values()),
            'historical_distinct_count': 63, 'added_hashes': sorted(set(docs)-baseline),
            'removed_hashes': sorted(baseline-set(docs)),
            'scope': 'Only current originals; the 376-source intake union is metadata, not dispatch scope',
            'documents': sorted(docs.values(), key=lambda d: (d['page_count'], d['source_id']))}


def verify_originals(manifest):
    expected = {x['path']: x['sha256'] for d in manifest['documents'] for x in d['originals']}
    current = {str(p): sha(p) for p in Path(manifest['originals_root']).rglob('*') if p.is_file() and p.suffix.lower()=='.pdf'}
    if current != expected:
        raise ValueError('Frozen originals inventory changed; no additions, removals or substitutions admitted')


def copy_verified(source, dest, digest=None):
    source, dest = Path(source), Path(dest)
    if any(p.is_symlink() for p in (source,*source.parents,dest,*dest.parents)):
        raise ValueError('Portable copies must be regular files')
    digest = digest or sha(source)
    if sha(source) != digest:
        raise ValueError('Source copy hash mismatch: ' + str(source))
    if dest.exists():
        if not dest.is_file() or sha(dest) != digest:
            raise ValueError('Existing destination conflict: ' + str(dest))
        return digest
    dest.parent.mkdir(parents=True, exist_ok=True)
    temporary = dest.with_name(dest.name + '.' + uuid.uuid4().hex + '.partial')
    shutil.copyfile(source, temporary)
    if sha(temporary) != digest:
        raise ValueError('Copy failed integrity: ' + str(temporary))
    os.replace(temporary, dest)
    return digest


def ensure_source(root, document, original):
    root = Path(root)
    if root.is_symlink():
        raise ValueError('Library root must not be a symlink')
    raw = root/document['folder']
    if any(p.is_symlink() for p in (raw,*raw.parents)):
        raise ValueError('Source folder must not be a symlink')
    out = contained(root, document['folder'])
    out.mkdir(parents=True, exist_ok=True)
    copy_verified(original, out/'original.pdf', document['sha256'])
    metadata = {**document, 'portable_original': 'original.pdf'}
    if (out/'source.json').exists():
        if read_json(out/'source.json') != metadata:
            raise ValueError('Existing source metadata differs; explicit reconciliation required')
    else:
        atomic_json(out/'source.json', metadata)
    write_source_readme(out, document)
    return out


def source_readme(document, pointer):
    text = '# '+document['title']+'\n\n[Unchanged original](original.pdf) · [Source identity and aliases](source.json)\n\n'
    text += 'Type: '+document['document_type']+'. Source completeness: '+document.get('completeness','unverified')+'.\n\n'
    if pointer:
        text += 'Processing status: '+pointer['status']+'. [Selected generation]('+pointer['generation']+'/README.md).\n'
    else:
        text += 'Processing status: registered; no selected conversion generation yet.\n'
    text += '\nConversion, model review, compilation and independent source verification are separate. This is not complete Markdown or a mathematical accuracy certificate.\n'
    return text


def write_source_readme(out, document):
    pointer = read_json(out/'current.json') if (out/'current.json').exists() else None
    temp = out/'README.md.tmp'; temp.write_text(source_readme(document,pointer)); os.replace(temp, out/'README.md')


def publish_generation(out, generation, prepared, status, *, select=True):
    """Recover safely across copy/rename/pointer crashes; never mutate a generation."""
    out, prepared = Path(out), Path(prepared)
    verify_seal(prepared)
    if not re.fullmatch(r'[A-Za-z0-9_-]+', generation):
        raise ValueError('Unsafe generation name')
    target = out/'generations'/generation
    if target.exists():
        verify_seal(target, sha(prepared/'manifest.json'))
    else:
        staging = out/'generations'/('.'+generation+'.staging')
        staging.mkdir(parents=True, exist_ok=True)
        for r in files_manifest(prepared):
            copy_verified(prepared/r['path'], contained(staging,r['path']), r['sha256'])
        verify_seal(staging, sha(prepared/'manifest.json'))
        os.rename(staging, target)
    pointer = {'generation': str(target.relative_to(out)), 'manifest_sha256': sha(target/'manifest.json'), 'status': status}
    if select:atomic_json(out/'current.json', pointer)
    return pointer


def archive(path, root, *, text_only=False):
    """Verified archive, written via a temporary file without changing originals."""
    path, root = Path(path), Path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.partial')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(root.rglob('*')):
            if p.is_symlink():
                raise ValueError('Symlink in archive input')
            if p.is_file() and (not text_only or p.suffix in ('.md','.json','.txt','.tex','.py','.sh','.diff')):
                z.write(p, str(p.relative_to(root)))
    with zipfile.ZipFile(temporary) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP integrity failed')
    os.replace(temporary, path)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}
