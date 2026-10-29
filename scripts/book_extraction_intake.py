"""Small full-PDF intake for the existing converter; native text only, never OCR."""
import html
from pathlib import Path
import re

from probe.common import atomic_json, read_json, sha, files_manifest, windows
from probe.documents import _fitz
from probe.cli import stamp


def prepare(root, source_id):
    if not re.fullmatch(r'[a-z][a-z0-9-]*', source_id): raise ValueError('Invalid source ID')
    root = Path(root); pdf = root/'inputs'/source_id/'source.pdf'
    if not pdf.is_file(): raise ValueError(f'Missing input: {pdf}. No other book substituted; no service changed.')
    cache = pdf.parent/'intake'
    if cache.exists():
        manifest = read_json(cache/'manifest.json')
        entries = [p for p in files_manifest(cache) if p['path'] != 'manifest.json']
        if entries != manifest: raise ValueError('Changed native-text intake evidence: ' + str(cache))
        meta = read_json(cache/'metadata.json')
        if sha(pdf) != meta['source_sha256']: raise ValueError('Original PDF changed; refuse intake/resume')
    else:
        fitz = _fitz(); digest = sha(pdf); initial_stat = pdf.stat()
        # An interrupted preparation stays separate; never overwrite an existing cache.
        staging = pdf.parent/('intake-preparing-'+stamp()); staging.mkdir()
        with fitz.open(pdf) as doc:
            if not doc.is_pdf or doc.needs_pass or doc.is_encrypted or len(doc) < 1:
                raise ValueError('Input is not a readable, unencrypted PDF: ' + str(pdf))
            pages = []
            for i, page in enumerate(doc):
                text = page.get_text('text', flags=fitz.TEXTFLAGS_TEXT, sort=False)
                path = staging/'native'/f'page-{i+1:06d}.txt'; path.parent.mkdir(exist_ok=True)
                path.write_text(text, encoding='utf-8')
                pages.append({'selected_page': i+1, 'original_physical_page': i+1,
                              'pdf_catalogue_label': page.get_label(), 'printed_page': None,
                              'native_text': str(path.relative_to(staging)), 'text_sha256': sha(path),
                              'characters': len(text), 'empty_native_text': not text.strip(),
                              'blank_status': 'unverified; empty native text is not proof of a blank page'})
            toc = doc.get_toc(); top = [x for x in toc if x[0] == 1 and 1 <= x[2] <= len(doc)]
            ordered = all(a[2] < b[2] for a,b in zip(top,top[1:]))
            boundaries = [{'title': x[1], 'first_physical_page': x[2],
                           'last_physical_page': top[i+1][2]-1 if i+1 < len(top) else len(doc),
                           'basis': 'PDF top-level bookmark, not independently verified chapter boundary'}
                          for i,x in enumerate(top)] if ordered else []
            meta = {'source_id': source_id, 'source_pdf': str(pdf), 'source_sha256': digest,
                    'pages': len(doc), 'pdf_metadata': doc.metadata, 'bookmarks': toc,
                    'bookmark_sections': boundaries, 'page_label_rules': doc.get_page_labels(),
                    'title': doc.metadata.get('title') or f'{source_id} (title not established)',
                    'edition': 'Not independently established; inspect cached title/copyright pages',
                    'chapter_boundaries': 'Bookmark evidence only; all-page extraction does not depend on inferred chapters',
                    'extractor': {'name': 'PyMuPDF native text', 'version': fitz.VersionBind,
                                  'flags': fitz.TEXTFLAGS_TEXT, 'sort': False, 'ocr': False},
                    'page_map': pages, 'text_filter': 'None; retains isolated numerals and empty pages'}
            atomic_json(staging/'metadata.json', meta)
        if (pdf.stat().st_size,pdf.stat().st_mtime_ns) != (initial_stat.st_size,initial_stat.st_mtime_ns):
            raise ValueError('PDF changed during intake')
        c = read_json(root/'config.example.json')
        plan = list(windows(meta['pages'], c['window_pages'], c['overlap_pages']))
        owned = [n for w in plan for n in range(w['owned_start'],w['owned_end']+1)]
        if owned != list(range(1,meta['pages']+1)): raise ValueError('Invalid page ownership plan')
        atomic_json(staging/'window-plan.json', plan)
        links = ''.join(f'<li>Physical PDF {p["original_physical_page"]}: <a href="{p["native_text"]}">native text</a> '
                        f'({p["characters"]} characters; blank unverified)</li>' for p in meta['page_map'])
        front = ''.join('<h3>Physical PDF '+str(p['original_physical_page'])+'</h3><pre>'+html.escape(
            (staging/p['native_text']).read_text())+'</pre>' for p in meta['page_map'][:16])
        (staging/'report.html').write_text('<!doctype html><meta charset="utf-8"><h1>Book intake — '+html.escape(meta['title'])+
            '</h1><p>All '+str(meta['pages'])+' physical pages retained. No OCR or fidelity assessment yet. '
            'Edition/chapter interpretation requires source inspection; no Gatheral boundaries used.</p>'
            '<h2>Title, copyright and contents evidence (first 16 pages)</h2>'+front+
            '<h2>Bookmarks</h2><pre>'+html.escape(str(meta['bookmarks']))+'</pre><h2>Every physical page</h2><ul>'+links+'</ul>', encoding='utf-8')
        atomic_json(staging/'manifest.json', files_manifest(staging)); staging.rename(cache)
    entry = {'pdf': str(pdf.relative_to(root)), 'sha256': meta['source_sha256'], 'pages': meta['pages'],
             'original_pages': list(range(1,meta['pages']+1)), 'ocr_mode': 'auto',
             'manifest': str((cache/'metadata.json').relative_to(root))}
    registry_path = root/'sources.json'; registry = read_json(registry_path)
    if source_id in registry and registry[source_id] != entry:
        raise ValueError('Conflicting existing source registration: ' + source_id)
    if source_id not in registry:
        registry[source_id] = entry; atomic_json(registry_path, registry)
    return cache, meta
