#!/usr/bin/env python3
"""One linked, finite Gatheral/Bergomi completion. Preparation never dispatches."""
import argparse
import copy
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
import zipfile
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scripts'))
import editorial_chapters as book
import speed_suite as speed
from probe import book_completion as completion, chapter_concurrency as concurrent
from probe import chapter_editorial as edit, chapter_glm as runtime, chapter_protocol, chapter_accuracy
from probe import chapter_sources, tex_compile
from probe.common import atomic_json, read_json, sha, fingerprint, files_manifest, writer_lock
from probe.experiment import InputGuard, verify_seal

POINTER = ROOT / 'results/book-completion-current.json'
PYTHON = ROOT / '.venv-control/bin/python'
SESSION = 'pdf-book-completion'
TERMINAL = completion.TERMINAL
PARENTS = {'production': 'editorial-chapters-current.json', 'speed': 'speed-suite-current.json',
           'overnight': 'overnight-suite-current.json'}
REPAIR_KEYS = {'bergomi-02-s01', 'bergomi-02-s08', 'bergomi-02-s12', 'bergomi-02-s14',
               'c-recap-03-bergomi-08', 'd-large-03-bergomi-07', 'd-large-04-bergomi-07', 'd-large-09-bergomi-09'}


def hashes():
    paths = set(book.code_hashes()) | {'probe/book_completion.py', 'scripts/book_completion.py',
             'scripts/run-book-completion.sh', 'probe/compiler_environment.py', 'probe/tex_compile.py'}
    return {p: sha(ROOT / p) for p in sorted(paths)}


def folder(run, source):
    return run / ('bergomi/inputs' if source.startswith('bergomi-') else 'inputs') / source


def safe_write(path, text):
    """Idempotent completion finalization; never replace conflicting saved bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode() if isinstance(text, str) else text
    if path.exists():
        if path.read_bytes() != data:
            raise runtime.Fatal('Existing finalization evidence differs: ' + str(path))
    else:
        path.write_bytes(data)


def remember(run, state, key, label, text, origin):
    path = Path('versions') / key / label / 'document.tex'
    safe_write(run / path, text)
    records = state.setdefault('versions', {}).setdefault(key, {})
    if label in records:
        if records[label]['sha256'] != sha(run / path) or records[label]['origin'] != origin:
            raise runtime.Fatal('Version identity/ancestry changed')
    else:
        records[label] = {'path': str(path), 'sha256': sha(run / path), 'origin': origin,
                          'compilation': {'status': 'not_attempted'}}
    return records[label]


def asset_map(run, source, document):
    pool = folder(run, source).parent
    allowed = {a: pool / a for a in read_json(folder(run, source) / 'assets.json')}
    refs = completion.image_references(document)
    unknown = [a for a in refs if a not in allowed]
    if unknown:
        raise ValueError('Unresolved/unapproved local asset reference: ' + ', '.join(unknown))
    return {a: allowed[a] for a in refs}


def asset_identity(assets):
    return {k: sha(v) for k, v in sorted(assets.items())}


def normalize_asset_paths(document, allowed):
    """Only literal figure arguments with an unambiguous existing basename."""
    edits = []
    for m in reversed(list(re.finditer(r'\\includegraphics\*?(?:\s*\[[^\]]*\])?\s*\{', document))):
        arg, end = completion.braced(document, m.end()-1)
        if arg.startswith(r'\detokenize{') or arg in allowed:
            continue
        if '/' in arg or '\\' in arg:
            continue
        match = [a for a in allowed if Path(a).name == arg]
        if len(match) != 1:
            continue
        old = document[m.start():end]
        new = old[:old.rfind('{')+1] + match[0] + '}'
        document = document[:m.start()] + new + document[end:]
        edits.append({'old': old, 'new': new, 'reason': 'Resolve the exact saved image via its allowlisted assets/ path; filename and image bytes unchanged.'})
    return document, edits


def restore_figure_109(document, native):
    block = next(b for b in native['blocks'] if b['id'] == 'bergomi-p0419:b2')
    if block['assets'] != ['assets/d6bde87360b133c396f7d878.jpg']:
        raise runtime.Fatal('Figure 10.9 source identity changed')
    if r'\label{fig:109}' in document or 'd6bde87360b133c396f7d878.jpg' in document:
        raise ValueError('Figure 10.9 is already present; do not repair twice')
    # Existing native PDF corroboration in secondary.txt gives p_+; preserve this
    # source-supported reading and the figure's existing reference identifier.
    figure = r'''\begin{figure}[htbp]
\centering
\includegraphics[width=.85\linewidth]{assets/d6bde87360b133c396f7d878.jpg}
\caption{Difference of the 95\% and 105\% implied volatilities, as a function of
maturity -- in years -- (dots) along with a $1/T$ fit (line), in the two-factor
model with $\nu=0$ (no stochastic volatility) with $\mu_+=\mu_-=4$ and $p_+=70\%$.}
\label{fig:109}
\end{figure}
'''
    anchor = 'See also Appendix~A for more on this scaling.'
    if document.count(anchor) != 1:
        raise ValueError('Figure 10.9 insertion anchor changed')
    before = document
    document = completion.replace_exact(document, anchor, anchor + '\n\n' + figure)
    old_claim = '5. **Verified complete within scope:**'
    new_claim = '5. **Historical GLM completeness claim (not independently verified; the original omitted Figure 10.9):**'
    document = completion.replace_exact(document, old_claim, new_claim)
    note = (r'\par\smallskip\noindent\textbf{Codex correction (1 November 2026).} '
            'The original model response claimed Figure 10.9 was included, but its chart, caption and label were absent. '
            'Restored from saved source block bergomi-p0419:b2 (physical 419, printed 402); '
            'the original response remains unchanged in its parent run. '
            'Earlier completeness/caption claims reproduced in the historical notes are contradicted by that original file.'
            + '\\par\\smallskip\n')
    document = completion.replace_exact(document, r'\end{document}', note + r'\end{document}')
    labels = re.findall(r'\\label\{fig:([^}]+)\}', document)
    if labels.count('109') != 1 or labels.count('1010') != 1 or labels.index('109') > labels.index('1010'):
        raise ValueError('Figure 10.9/10.10 order/identity invalid')
    return document, [{'old': anchor, 'new': anchor + '\n\n' + figure,
                       'reason': 'Restore existing source chart/caption/label before Figure 10.10; actual figure counter checked separately.'},
                      {'old': old_claim, 'new': new_claim,
                       'reason': 'Correct the derivative attribution/completeness claim; original parent response remains unchanged.'},
                      {'old': r'\end{document}', 'new': note + r'\end{document}',
                       'reason': 'Qualify misleading model completeness claims without deleting the historical response.'}]


def candidate(parent, state, key, *, label=None, blocks=None, rationale=''):
    label = label or state['current_versions'][key]
    v = state['versions'][key][label]
    tasks = [t for t in state['tasks'] if t['key'] == key]
    source = next((t['source_key'] for t in tasks), key)
    native = read_json(folder(parent, source) / 'native.json')
    section = next((t['section'] for t in tasks if t.get('section')), None)
    ids = blocks if blocks is not None else section['blocks'] if section else [b['id'] for b in native['blocks'] if b['kind'] not in completion.FURNITURE]
    if sha(parent / v['path']) != v['sha256']:
        raise runtime.Fatal('Saved candidate changed')
    return {'parent': str(parent), 'key': key, 'label': label, 'source_key': source,
            'record': copy.deepcopy(v), 'blocks': list(ids), 'rationale': rationale,
            'model_review': [t['status'] for t in tasks if t['phase'] == 'critic'],
            'verification': 'targeted mechanical preservation checks; not independent full-part mathematical acceptance'}


def choose_candidates(parents, states):
    """Reviewed policy: preserve production; adopt nonoverlapping saved bodies once."""
    p, s, o = (parents[x] for x in ('production', 'speed', 'overnight'))
    ps, ss, os_ = (states[x] for x in ('production', 'speed', 'overnight'))
    choices = []
    for book_name in ('gatheral', 'bergomi'):
        cov = read_json(p / ps['editions'][book_name] / 'coverage.json')
        for row in cov['delivered_parts']:
            if row.get('content_retained'):
                choices.append(candidate(p, ps, row['key'], label=row['version'], blocks=row['target_block_ids'],
                    rationale='Retain the exact production edition selection; do not substitute a shorter benchmark recap or High alternative.'))
    choices.append(candidate(p, ps, 'bergomi-04-s02', rationale='Completed production Max revision retains the full target and already has a valid tag 4.14/build. The separate saved High tag repair is not applied twice.'))
    volga = next(x for x in read_json(o / 'offline-repairs/index.json') if x['key'] == 'bergomi-04-s01-volga')
    row = candidate(s, ss, 's3-high-bergomi-04-s01', label='critic-call-014',
                    rationale='Use the existing source-supported volatility-derivative repair; explicit formula/heading/chart preservation comparison accompanies adoption.')
    row.update(offline_repair={'parent': str(o), **volga})
    choices.append(row)
    for key in ('s1-four-bergomi-05-s01', 's1-four-bergomi-06-s01', 's1-four-bergomi-06-s06'):
        choices.append(candidate(s, ss, key, rationale='Use completed original High conversion/Max critic on this previously missing exact target; later High rereview is an alternative, not automatic authority.'))
    for key in os_['current_versions']:
        if key == 'a-high-s1-four-bergomi-04-s03' or key.startswith(('c-recap-', 'd-large-')):
            choices.append(candidate(o, os_, key, rationale='Saved coherent grouped target; include this document once, retain original draft and all accuracy notes. No promotion from timestamp/finish/build alone.'))
    # The existing Gatheral selection already has precisely the needed Lewis
    # qualification. Preserve it instead of replacing it with another experiment.
    lewis = next(x for x in choices if x['key'] == 'gatheral-07-s05')
    text = (Path(lewis['parent']) / lewis['record']['path']).read_text()
    for required in (r'\rho\ne0', 'not independently\nestablished', r'J^{(2)}'):
        if required not in text:
            raise runtime.Fatal('Gatheral Lewis qualification needs explicit reconciliation')
    lewis['rationale'] = 'Retain existing production Lewis qualification: beta_2 inconsistency for nonzero rho; beta_0 cancellation not established without J^(2). Existing offline derivative is corroborating history, not a required new investigation.'
    return choices


def canonical_plan(parent, state):
    result = {}
    for t in state['tasks']:
        if t.get('source_key', '').startswith('bergomi-') and t['phase'] == 'convert':
            if t['key'] in result and result[t['key']]['blocks'] != t['section']['blocks']:
                raise runtime.Fatal('Conflicting canonical source tasks')
            result[t['key']] = {'key': t['key'], 'source_key': t['source_key'], **copy.deepcopy(t['section'])}
    return list(result.values())


def exclude_omitted_bodies(choices, run):
    exclusions = []
    for row in choices:
        if row['key'] not in ('d-large-02-bergomi-05', 'd-large-10-bergomi-10', 'd-large-11-bergomi-11'):
            continue
        native = read_json(folder(run, row['source_key']) / 'native.json')
        omit = set()
        for span in completion.appendix_spans(native):
            if not span['recap'] and set(span['blocks']) & set(row['blocks']):
                omit.update(span['blocks'])
                exclusions.append({'unit': row['key'], 'source_key': row['source_key'], **span,
                                   'reason': 'Saved body/critic notes explicitly exclude this assigned appendix. Adopt only usable main body, retain appendix as a gap.'})
        # Digest heading is not part of a body that explicitly excludes digest.
        for b in completion.selected_blocks(native, row['blocks']):
            if b['kind'] == 'paragraph_title' and any('digest' in completion.plain(h) for h in completion.headings(b['tex'])):
                omit.add(b['id'])
        row['declared_blocks'] = list(row['blocks'])
        row['blocks'] = [b for b in row['blocks'] if b not in omit]
        row['excluded_blocks'] = sorted(omit)
    return exclusions


def reconcile_digest_headings(choices, run):
    """Restore a missing printed heading from saved extraction without inference.

    Historical section maps assigned several digest headings to the preceding
    body, whose model explicitly omitted them. Their following digest text is
    already saved. Give each heading one owner and add the exact heading locally.
    A wholly missing digest keeps its heading with its new missing-content unit.
    """
    for source in sorted({x['source_key'] for x in choices if x['source_key'].startswith('bergomi-')}):
        native = read_json(folder(run, source) / 'native.json')
        order = {b['id']: i for i, b in enumerate(native['blocks'])}
        for b in native['blocks']:
            if b['kind'] != 'paragraph_title' or not any('digest' in completion.plain(h) for h in completion.headings(b['tex'])):
                continue
            owners = [r for r in choices if b['id'] in r['blocks']]
            if owners:
                owner = owners[0]
                text = (Path(owner['parent']) / owner['record']['path']).read_text()
                if any('digest' in completion.plain(h) for h in completion.headings(completion.body_only(text))):
                    continue
                owner.setdefault('declared_blocks', list(owner['blocks']))
                owner['blocks'].remove(b['id'])
                owner.setdefault('excluded_blocks', []).append(b['id'])
            following = [r for r in choices if r['source_key'] == source and r['key'].startswith('c-recap-')
                         and order[r['blocks'][0]] > order[b['id']]]
            if following:
                row = min(following, key=lambda r: order[r['blocks'][0]])
                row.setdefault('declared_blocks', list(row['blocks']))
                row['blocks'].insert(0, b['id'])
                row.setdefault('restored_heading_blocks', []).append({'id': b['id'], 'tex': b['tex']})


def secondary_for(run, source, pages):
    data = read_json(folder(run, source) / 'secondary.json')
    return chapter_sources.render_pages([p for p in data['pages'] if p['physical_pdf_page'] in pages])


def context_contract(run, source, section):
    """Retain full parent context when admitted, otherwise exact bounded refs."""
    f = folder(run, source); n = read_json(f / 'native.json')
    ids = {b['id'] for b in n['blocks'] if b['kind'] not in completion.FURNITURE}
    if set(section['blocks']) == ids:
        return '', {'mode': 'complete_chapter_is_target', 'unavailable': []}
    secondary = secondary_for(run, source, section['physical_pages'])
    def fits(context):
        try:
            b = completion.request(n, section, secondary, phase='critic', draft='D' * completion.DRAFT_RESERVE_BYTES, context=context)
            chapter_protocol.budget(b, completion.CAPACITY); return True
        except chapter_protocol.ContextBudgetGap:
            return False
    whole = ('PARENT CHAPTER CONTEXT ONLY; primary assigned span remains authoritative.\n'
             'Native MinerU parent:\n' + (f / 'source.tex').read_text() + '\nNative PDF parent:\n' + (f / 'secondary.txt').read_text())
    if fits(whole):
        return whole, {'mode': 'full_parent_context_separate_from_target', 'unavailable': []}
    from probe import critic_context
    rows = [{'block_id': b['id'], 'text': b['tex'], 'kind': b['kind'],
             'source_location': {'source_id': n['source'], 'page': b['page']}} for b in n['blocks']]
    index = critic_context.build_index(rows, {'source': n['source'], 'native_sha256': sha(f / 'native.json')})
    added, ledger = critic_context.resolve(index, critic_context.explicit_references(section['text']), exclude=section['blocks'])
    context = 'BOUNDARY/REFERENCE CONTEXT ONLY. Other parent-chapter text is not supplied; do not infer missing definitions.\n'
    unavailable = []
    for row in added:
        proposed = context + '\n\n' + row['text']
        if fits(proposed):
            context = proposed
        else:
            unavailable.append(row['block_id'])
    return context, {'mode': 'bounded_exact_reference_blocks', 'references': ledger, 'unavailable': unavailable,
                     'no_clipping': 'Every admitted context block and every target block is complete; omissions are context only.'}


def request_for(run, state, task, *, draft_override=None):
    source = task['source_key']; native = read_json(folder(run, source) / 'native.json')
    draft = draft_override; notes = ''
    if task['phase'] == 'critic' and draft is None:
        label = task.get('draft_label') or state['current_versions'].get(task['key'])
        if label is None:
            return None
        v = state['versions'][task['key']][label]
        if sha(run / v['path']) != v['sha256']:
            raise runtime.Fatal('Critic input version changed')
        draft = (run / v['path']).read_text()
        if task['key'] in state['accuracy']:
            notes = (run / state['accuracy'][task['key']]).read_text()
    body = completion.request(native, task['section'], secondary_for(run, source, task['section']['physical_pages']),
                              phase=task['phase'], draft=draft, notes=notes,
                              context=task.get('context', ''))
    chapter_protocol.budget(body, completion.CAPACITY)
    return body


def plan_missing(run, canonical, selections, exclusions):
    owned = completion.unique_coverage(selections)
    all_ids = {b for part in canonical for b in part['blocks']}
    missing = all_ids - set(owned)
    plan = []
    # Recover the four known appendix bodies as independent coherent units.
    for span in exclusions:
        ids = [b for b in span['blocks'] if b in missing]
        if ids:
            if ids != span['blocks']:
                raise runtime.Fatal('Partially owned appendix needs an explicit boundary decision')
            plan.append((span['source_key'], ids, 'omitted appendix body'))
            missing.difference_update(ids)
    # Seven substantive sections, adjacent missing digest tails and end matter.
    by_source = defaultdict(list)
    for p in canonical:
        for b in p['blocks']:
            if b in missing and b not in by_source[p['source_key']]:
                by_source[p['source_key']].append(b)
    for source, ids in by_source.items():
        native = read_json(folder(run, source) / 'native.json')
        for group in completion.contiguous_groups(native, ids):
            plan.append((source, group, 'unconverted source blocks; adjacent missing material grouped coherently'))
    units = []
    for source, ids, reason in plan:
        native = read_json(folder(run, source) / 'native.json')
        def fits(sec):
            secondary = secondary_for(run, source, sec['physical_pages'])
            try:
                body = completion.request(native, sec, secondary, phase='critic', draft='D' * completion.DRAFT_RESERVE_BYTES)
                chapter_protocol.budget(body, completion.CAPACITY)
                return True
            except chapter_protocol.ContextBudgetGap:
                return False
        parts = completion.split_meaningfully(native, ids, fits=fits)
        for part in parts:
            key = source + '-completion-' + fingerprint(part['blocks'])[:10]
            context, context_scope = context_contract(run, source, part)
            units.append({'unit': key, 'source_key': source, 'section': part, 'reason': reason,
                          'context': context, 'context_scope': context_scope,
                          'source_native_sha256': sha(folder(run, source) / 'native.json'),
                          'secondary_sha256': sha(folder(run, source) / 'secondary.json'),
                          'capacity': {'recorded_context': completion.CAPACITY, 'critic_draft_byte_reservation': completion.DRAFT_RESERVE_BYTES,
                                       'policy': 'complete target and corroborating pages; meaningful source-heading splits only; actual runtime/draft budget rechecked, never clipped'}})
    if len({b for u in units for b in u['section']['blocks']}) != sum(len(u['section']['blocks']) for u in units):
        raise runtime.Fatal('Missing queue duplicates source blocks')
    if set(owned) & {b for u in units for b in u['section']['blocks']}:
        raise runtime.Fatal('Completion queue replays adopted source content')
    if (set(owned) & all_ids) | {b for u in units for b in u['section']['blocks']} != all_ids:
        raise runtime.Fatal('Completion queue loses source blocks')
    return units


def material_comparison(original, selected):
    """Preservation indicators, not semantic acceptance of a critic revision."""
    a, b = completion.body_only(original), completion.body_only(selected)
    def tags(t):return set(re.findall(r'\\tag\*?\{([^}]+)\}', t))
    keywords = ('assume', 'provided', 'nonzero', 'positive', 'if', 'only', 'proof')
    return {'original_body_bytes': len(a.encode()), 'selected_body_bytes': len(b.encode()),
            'large_contraction_warning': len(b.encode()) < .8 * len(a.encode()),
            'original_headings': completion.headings(a), 'selected_headings': completion.headings(b),
            'explicit_equation_numbers_removed': sorted(tags(a)-tags(b)),
            'explicit_equation_numbers_added': sorted(tags(b)-tags(a)),
            'image_names_removed': sorted(set(completion.image_references(a))-set(completion.image_references(b))),
            'condition_word_counts': {word: {'original': len(re.findall(r'\b'+word+r'\b', a, re.I)),
                                           'selected': len(re.findall(r'\b'+word+r'\b', b, re.I))} for word in keywords},
            'conclusion': 'Targeted content-preservation signals only; substantive rewrites and automatic numbering may require inspection. No mathematical proof inferred.'}


def reuse_build(run, state, key, label, candidate_row):
    """Reuse a real saved build only for exact document/asset/image identities."""
    v = state['versions'][key][label]
    old = candidate_row['record']
    parent = Path(candidate_row['parent'])
    if candidate_row.get('offline_repair'):
        repair = candidate_row['offline_repair']; parent = Path(repair['parent'])
        old = {'sha256': repair['document_sha256'], 'compilation': repair['compilation']}
    if old['sha256'] != v['sha256'] or not old.get('compilation', {}).get('status', '').startswith('passed'):
        return False
    doc = (run / v['path']).read_text()
    assets = asset_map(run, candidate_row['source_key'], doc)
    required = asset_identity(assets)
    image = state['compiler_environment']['image']
    for attempt in reversed(old['compilation'].get('attempts', [])):
        if attempt.get('input_sha256') != v['sha256'] or attempt.get('image_id') != image or not attempt.get('compilation_claim'):
            continue
        supplied = {x['path']: x['sha256'] for x in attempt.get('assets', [])}
        if any(supplied.get(k) != h for k, h in required.items()):
            continue
        original = parent / attempt['path']
        pdf = original / 'document.pdf'
        expected = next((x['sha256'] for x in attempt.get('outputs', []) if x.get('path') == 'document.pdf'), None)
        if not pdf.is_file() or not expected or sha(pdf) != expected:
            continue
        dest = run / Path(v['path']).parent / 'reused-build'; dest.mkdir()
        shutil.copyfile(pdf, dest / 'document.pdf')
        reused = copy.deepcopy(attempt); reused['path'] = str(dest.relative_to(run))
        atomic_json(dest / 'original-build-record.json', {'source': str(original), 'record': attempt})
        v['compilation'] = {'status': old['compilation']['status'], 'attempts': [reused],
                            'reused_exact_document_dependencies_image': True, 'source': str(original)}
        v.update(compiled_image=image, build_identity=fingerprint({'document': v['sha256'], 'assets': required, 'image': image}))
        return True
    return False


def inherit_candidate(run, state, row, *, prior_cache=None):
    parent = Path(row['parent']); key = row['key']; source = row['source_key']
    original = parent / row['record']['path']; text = original.read_text()
    provenance = run / 'provenance' / key; provenance.mkdir(parents=True)
    shutil.copyfile(original, provenance / 'original.tex')
    selected_source = original
    if row.get('offline_repair'):
        repair = row['offline_repair']; selected_source = Path(repair['parent']) / repair['path'] / 'document.tex'
        if sha(selected_source) != repair['document_sha256']:
            raise runtime.Fatal('Existing offline repair changed')
        text = selected_source.read_text()
    edits = []
    if key in REPAIR_KEYS:
        text, edits = completion.repair_known(key, text)
    native = read_json(folder(run, source) / 'native.json')
    if key == 'd-large-10-bergomi-10':
        text, extra = restore_figure_109(text, native); edits += extra
    if row.get('restored_heading_blocks'):
        heading = '\n\n'.join(b['tex'] for b in row['restored_heading_blocks'])
        old = r'\begin{document}'; new = old + '\n\n' + heading
        text = completion.replace_exact(text, old, new)
        edits.append({'old': old, 'new': new, 'reason': 'Restore the exact printed digest heading excluded by the preceding body; no model call or substantive rewrite.'})
    text, extra = normalize_asset_paths(text, set(read_json(folder(run, source) / 'assets.json')))
    edits += extra
    label = ('repaired-' if edits else 'reused-') + fingerprint(text)[:12]
    v = remember(run, state, key, label, text, {'source': str(selected_source), 'source_sha256': sha(selected_source),
                 'parent_run': str(parent), 'parent_key': key, 'parent_label': row['label'],
                 'decision': row['rationale'], 'edits': edits, 'no_model_regeneration': True})
    state['current_versions'][key] = label
    section = completion.target(native, row['blocks'])
    state['source_units'][key] = {'source_key': source, 'section': section, 'kind': 'reused', 'parent': str(parent), 'parent_key': key}
    record = {'unit': key, 'source_key': source, 'blocks': row['blocks'], 'selection': label,
              'version_sha256': v['sha256'], 'declared_parent_blocks': row.get('declared_blocks', row['blocks']),
              'excluded_blocks': row.get('excluded_blocks', []), 'restored_heading_blocks': row.get('restored_heading_blocks', []),
              'decision': row['rationale'], 'parent_version': row['label'], 'parent_run': str(parent),
              'model_review': row['model_review'], 'source_checked': 'only explicitly attributed prior findings; no full-part certification',
              'coverage_check': completion.coverage_check(text, native, row['blocks'])}
    parent_state = read_json(parent / 'state.json')
    candidates = parent_state['versions'].get(key, {})
    draft_label = next((name for name in candidates if name.startswith('convert-call-') and not name.endswith('-annotated')), None)
    if draft_label is None:
        draft_label = next((name for name in ('saved-control-draft', 'first-glm') if name in candidates), None)
    if draft_label:
        draft = parent / candidates[draft_label]['path']
        if sha(draft) != candidates[draft_label]['sha256']:
            raise runtime.Fatal('Original conversion/control draft identity changed')
        shutil.copyfile(draft, provenance / 'conversion-draft.tex')
        record['critic_preservation_comparison'] = material_comparison(draft.read_text(), text)
        record['critic_preservation_comparison']['original_path'] = str(draft)
        record['critic_preservation_comparison']['original_sha256'] = sha(draft)
    state['selection_ledger'].append(record)
    atomic_json(provenance / 'decision.json', {**row, 'new_version': v, 'technical_edits': edits, 'targeted_checks': record['coverage_check']})
    (provenance / 'change.diff').write_text(''.join(difflib.unified_diff(original.read_text().splitlines(True), text.splitlines(True),
                                          fromfile=str(original), tofile=v['path'])))
    accuracy = parent / 'accuracy' / key
    if accuracy.is_dir():
        shutil.copytree(accuracy, run / 'accuracy' / key)
    # Pick the existing selected log, never invent model findings from prose.
    old_state = read_json(parent / 'state.json')
    for field in ('accuracy', 'accuracy_records'):
        old_path = old_state.get(field, {}).get(key)
        if old_path and (parent / old_path).is_file():
            dst = run / 'accuracy' / key / Path(old_path).name
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(parent / old_path, dst)
            state[field][key] = str(dst.relative_to(run))
    reused = reuse_build(run, state, key, label, row)
    if not reused and prior_cache:
        previous_run, previous_state = prior_cache
        for cached_label, cached in previous_state.get('versions', {}).get(key, {}).items():
            if cached['sha256'] == v['sha256'] and cached.get('compilation', {}).get('status', '').startswith('passed'):
                if reuse_build(run, state, key, label, {'parent': str(previous_run), 'record': cached, 'source_key': source}):
                    break
    return record


def frozen_tasks(state):
    fields = ('id', 'key', 'source_key', 'phase', 'section', 'reasoning_effort', 'depends_on', 'context', 'preview_hash')
    return [{k: t.get(k) for k in fields} for t in state['tasks']]


def prepared_files(run):
    roots = ['inputs', 'bergomi', 'prepared', 'provenance', 'compiler-environments']
    result = {}
    for name in roots:
        for p in sorted((run / name).rglob('*')):
            if p.is_file():
                result[str(p)] = sha(p)
    for name in ('completion-plan.json', 'ancestry.json', 'canonical-source-map.json', 'concurrency-runtime-binding.json', 'effort-support-offline.json'):
        p = run / name
        if p.exists():
            result[str(p)] = sha(p)
    return result


def prepare():
    prior_preparation = None
    prior_cache = None
    if POINTER.exists():
        old_run = Path(read_json(POINTER)['run'])
        old_state = read_json(old_run / 'state.json')
        old_binding = read_json(old_run / 'binding.json')
        if old_binding['code'] == hashes():
            verify(old_run)
            print('Existing completion retained; no new work prepared:', old_run, old_state['status'])
            return old_run
        if old_state['calls']:
            raise runtime.Fatal('Completion already has consumed calls. A changed-code continuation must reconcile that lineage; refusing fresh preparation from old book parents.')
        if not speed.idle(old_run):
            raise runtime.Fatal('Earlier completion preparation has an active writer')
        prior_preparation = {'run': str(old_run), 'state_sha256': sha(old_run / 'state.json'),
                             'calls': 0, 'reason': 'Unlaunched preparation superseded by tested implementation; old evidence preserved.'}
        prior_cache = (old_run, old_state)
    parents = {name: Path(read_json(ROOT / 'results' / ptr)['run']) for name, ptr in PARENTS.items()}
    if not speed.idle(ROOT) or any(not speed.idle(p) for p in parents.values()):
        raise runtime.Fatal('Existing writer active; preparation stopped without editing its evidence')
    with writer_lock(ROOT):
        states = {name: read_json(p / 'state.json') for name, p in parents.items()}
        if any(c.get('status') == 'in_progress' for s in states.values() for c in s['calls']):
            raise runtime.Fatal('Parent has uncertain in-flight work; no completion preparation')
        if any(states[name]['status'] != 'suite_finished_for_inspection' for name in ('speed', 'overnight')):
            raise runtime.Fatal('Experiments changed or not finished; reconcile actual current work first')
        parent = parents['production']; ps = states['production']
        run = book.chapter_inputs.new_path('book-completion'); run.mkdir(parents=True)
        for base in ('inputs', 'bergomi/inputs'):
            src = parent / base; dst = run / base; dst.mkdir(parents=True)
            for path in src.iterdir():
                if path.is_dir() and (path.name == 'assets' or path.name.startswith(('gatheral-', 'bergomi-'))):
                    shutil.copytree(path, dst / path.name)
        for name in ('source-supplement', 'bibliography'):
            if (parent / name).is_dir():
                shutil.copytree(parent / name, run / name)
        if (parent / 'bergomi/source-supplement.pdf').is_file():
            shutil.copyfile(parent / 'bergomi/source-supplement.pdf', run / 'bergomi/source-supplement.pdf')
        env = copy.deepcopy(ps['compiler_environment'])
        verify_seal(parent / env['path'], env['seal'])
        shutil.copytree(parent / env['path'], run / env['path'])
        for name in ('concurrency-runtime-binding.json',):
            shutil.copyfile(parent / name, run / name)
        shutil.copyfile(parents['overnight'] / 'effort-support-offline.json', run / 'effort-support-offline.json')
        state = {'status': 'prepared_offline', 'created_at': runtime.now(), 'suite_protocol': completion.PROTOCOL,
                 'chapter_contract': edit.VERSION, 'timing_policy': 'manual_only', 'first_dispatch': None,
                 'calls': [], 'tasks': [], 'versions': {}, 'current_versions': {}, 'accuracy': {}, 'accuracy_records': {},
                 'source_units': {}, 'selection_ledger': [], 'compiler_environment': env, 'connection_failures': 0,
                 'phase_efforts': dict(completion.EFFORTS), 'execution_limits': {'calls': None, 'attempts_per_unit': 1},
                 'concurrency_policy': copy.deepcopy(concurrent.POLICY), 'active_stage': 1,
                 'stages': {'1': {'status': 'pending'}}, 'launches': [], 'stage': 'prepared; not running',
                 'historical_calls': {name: {'recorded': len(s['calls']), 'earlier_history': s.get('historical_calls'),
                                             'state_sha256': sha(parents[name] / 'state.json')} for name, s in states.items()}}
        canonical = canonical_plan(parent, ps)
        atomic_json(run / 'canonical-source-map.json', canonical)
        choices = choose_candidates(parents, states)
        # Require exact shared extraction identity across parent experiments.
        consumed = {}
        for name, p in parents.items():
            consumed[str(p / 'state.json')] = sha(p / 'state.json')
        if prior_cache:
            consumed[str(prior_cache[0] / 'state.json')] = sha(prior_cache[0] / 'state.json')
        source_identity = {}
        for name, date in (('gatheral', '20261025'), ('bergomi', '20261027')):
            provenance = ROOT / f'docs/source-provenance/{name}-intake-{date}.json'
            identity = read_json(provenance); pdf = ROOT / (identity.get('pdf') or identity['path'])
            if sha(pdf) != identity['sha256']:
                raise runtime.Fatal('Original book source hash differs from intake identity: ' + name)
            consumed[str(provenance)] = sha(provenance); consumed[str(pdf)] = identity['sha256']
            source_identity[name] = identity
        checked_assets = {}
        for row in choices:
            src = Path(row['parent'])
            for name in ('native.json', 'source.tex', 'secondary.json', 'secondary.txt', 'assets.json'):
                original = folder(src, row['source_key']) / name
                if sha(original) != sha(folder(run, row['source_key']) / name):
                    raise runtime.Fatal('Parent source extraction differs: ' + str(original))
                consumed[str(original)] = sha(original)
            for asset in read_json(folder(src, row['source_key']) / 'assets.json'):
                original = folder(src, row['source_key']).parent / asset
                copied = folder(run, row['source_key']).parent / asset
                if original not in checked_assets:
                    checked_assets[original] = sha(original)
                if checked_assets[original] != sha(copied):
                    raise runtime.Fatal('Parent asset identity differs: ' + str(original))
                consumed[str(original)] = checked_assets[original]
            original = src / row['record']['path']; consumed[str(original)] = sha(original)
        exclusions = exclude_omitted_bodies(choices, run)
        reconcile_digest_headings(choices, run)
        for row in choices:
            inherit_candidate(run, state, row, prior_cache=prior_cache)
        missing_units = plan_missing(run, canonical, state['selection_ledger'], exclusions)
        for u in missing_units:
            key = u['unit']; state['source_units'][key] = {'source_key': u['source_key'], 'section': u['section'], 'kind': 'new'}
            for phase in ('convert', 'critic'):
                task = {'id': key + '/' + phase, 'key': key, 'source_key': u['source_key'], 'phase': phase,
                        'section': u['section'], 'reasoning_effort': completion.EFFORTS[phase], 'status': 'pending',
                        'depends_on': key + '/convert' if phase == 'critic' else None, 'draft_label': None,
                        'context': u['context'], 'context_scope': u['context_scope'], 'attempt_limit': 1}
                state['tasks'].append(task)
                body = request_for(run, state, task)
                dest = run / 'prepared' / key / phase
                if body:
                    atomic_json(dest / 'request.json', body); task['preview_hash'] = fingerprint(body)
                    atomic_json(dest / 'budget.json', chapter_protocol.budget(body, completion.CAPACITY))
                else:
                    atomic_json(dest / 'awaits-own-draft.json', {'scope_sha256': fingerprint(u['section']), 'effort': 'max', 'output_tokens': completion.OUTPUT_TOKENS})
        state['production_stage'] = {'name': 'finite-book-completion', 'task_ids': [t['id'] for t in state['tasks']],
                                    'end_action': 'assemble-and-package-both-books; no subsequent workload'}
        owned = completion.unique_coverage(state['selection_ledger'])
        missing_parts = [p['key'] for p in canonical if not (set(p['blocks']) & set(owned))]
        partial_parts = [p['key'] for p in canonical if set(p['blocks']) & set(owned) and not set(p['blocks']) <= set(owned)]
        durations = [c.get('metadata', {}).get('latency_seconds', c.get('elapsed_seconds', 0)) for c in states['overnight']['calls'] if c['parent'] != 'readiness']
        median = sorted(durations)[len(durations)//2] if durations else 0
        estimate = {'basis': 'Median saved overnight work-request latency; actual targets differ, and compiler/finalization adds time.',
                    'median_request_seconds': median, 'serial_hours': median*len(state['tasks'])/3600,
                    'ideal_two_slot_hours': median*len(state['tasks'])/7200, 'deadline': None,
                    'warning': 'Planning estimate only; no throughput or completion-time guarantee.'}
        plan = {'protocol': completion.PROTOCOL, 'prepared_at': runtime.now(), 'parents': {k: str(p) for k, p in parents.items()},
                'reused_documents': len(choices), 'selected_by_book': dict(Counter(r['source_key'].split('-')[0] for r in state['selection_ledger'])),
                'canonical_Bergomi_parts': len(canonical), 'no_adopted_target_parts': missing_parts,
                'partially_adopted_parts': partial_parts, 'omitted_appendices': exclusions,
                'new_units': missing_units, 'planned_work_requests': len(state['tasks']),
                'readiness': 'one fresh request per genuine runtime launch; zero after terminal',
                'estimate': estimate, 'settings': {'model': 'glm53-regular', 'efforts': completion.EFFORTS,
                     'max_tokens': 131072, 'concurrency': 2, 'stream': True, 'overall_deadline': None,
                     'model_attempts_per_phase': 1, 'compiler_recovery': 'existing installed immutable compiler only; no package installation or host fallback'},
                'acceptance': 'traceable working edition; mathematical/source completeness not certified',
                'adoptions': [{'unit': r['unit'], 'source_key': r['source_key'], 'blocks': r['blocks'],
                               'selection': r['selection'], 'version_sha256': r['version_sha256']}
                              for r in state['selection_ledger']],
                'tasks': frozen_tasks(state)}
        atomic_json(run / 'completion-plan.json', plan)
        ancestry = {'parent_runs': [], 'source_identity': source_identity, 'new_calls_start_separate': True,
                    'prior_unlaunched_preparation': prior_preparation,
                    'policy': 'No historical reservations or allowances reset. New finite work is only the explicitly authorized missing spans.'}
        for name, s in states.items():
            ancestry['parent_runs'].append({'name': name, 'run': str(parents[name]), 'state_sha256': sha(parents[name] / 'state.json'),
                 'calls': s['calls'], 'historical_calls': s.get('historical_calls'), 'source_history': s.get('source_history')})
        atomic_json(run / 'ancestry.json', ancestry)
        binding = {'code': hashes(), 'prepared': prepared_files(run), 'consumed': consumed,
                   'plan_sha256': sha(run / 'completion-plan.json'), 'task_fingerprint': fingerprint(frozen_tasks(state))}
        atomic_json(run / 'binding.json', binding); state['binding_sha256'] = fingerprint(binding)
        runtime.save(run, state)
        atomic_json(POINTER, {'run': str(run), 'prepared': True, 'running': False})
        report(run, state)
        print('PREPARED, NOT RUNNING:', run)
        return run


def verify(run, *, check_files=True):
    state = read_json(run / 'state.json'); b = read_json(run / 'binding.json')
    if b['code'] != hashes() or fingerprint(b) != state['binding_sha256']:
        raise runtime.Fatal('Completion code/binding changed; no reseal or replay')
    if sha(run / 'completion-plan.json') != b['plan_sha256'] or fingerprint(frozen_tasks(state)) != b['task_fingerprint']:
        raise runtime.Fatal('Frozen completion scope/settings changed')
    if state['execution_limits'] != {'calls': None, 'attempts_per_unit': 1} or state['phase_efforts'] != completion.EFFORTS:
        raise runtime.Fatal('Completion attempt/settings boundary changed')
    if state['production_stage']['task_ids'] != [t['id'] for t in state['tasks']]:
        raise runtime.Fatal('Dispatch queue differs from approved finite preparation')
    plan = read_json(run / 'completion-plan.json')
    for expected in plan['adoptions']:
        actual = next((r for r in state['selection_ledger'] if r['unit'] == expected['unit']), {})
        if any(actual.get(k) != v for k, v in expected.items()):
            raise runtime.Fatal('Frozen adoption/coverage changed')
    if check_files:
        InputGuard({**b['consumed'], **b['prepared']})
    ids = set(state['production_stage']['task_ids'])
    work = [c for c in state['calls'] if c['parent'] != 'readiness']
    if any(c['parent'] not in ids for c in work) or len({c['parent'] for c in work}) != len(work):
        raise runtime.Fatal('Repeated or out-of-scope work reservation')
    for records in state['versions'].values():
        for v in records.values():
            if sha(run / v['path']) != v['sha256']:
                raise runtime.Fatal('Saved version changed: ' + v['path'])
    for c in state['calls']:
        if c.get('seal'):
            d = run / 'calls' / c['id']; verify_seal(d, c['seal'])
            if fingerprint(read_json(d / 'request.json')) != c['request_sha256']:
                raise runtime.Fatal('Saved request identity changed')
    completion.unique_coverage(state['selection_ledger'])
    return state


def compile_version(run, state, key, label, *, compiler=tex_compile.compile_document):
    v = state['versions'][key][label]; source = state['source_units'][key]['source_key']
    if sha(run / v['path']) != v['sha256']:
        raise runtime.Fatal('Compilation input changed')
    doc = (run / v['path']).read_text()
    try:
        assets = asset_map(run, source, doc)
    except ValueError as exc:
        v['compilation'] = {'status': 'missing_package_or_asset', 'error': str(exc), 'compilation_claim': False}
        runtime.save(run, state); return v['compilation']
    image = state['compiler_environment']['image']
    identity = fingerprint({'document': v['sha256'], 'assets': asset_identity(assets), 'image': image})
    if v.get('build_identity') == identity and v['compilation']['status'] not in ('unavailable', 'not_attempted', 'compiler_environment_failure'):
        return v['compilation']
    base = run / Path(v['path']).parent / 'builds'; base.mkdir(exist_ok=True)
    # A crash after a completed compiler write but before state publication must
    # not discard or rerun that exact attempt.
    for previous in sorted(base.glob('*/completion-build.json')):
        rec = read_json(previous)
        if rec.get('identity') == identity and rec['result']['status'] not in ('unavailable', 'compiler_environment_failure'):
            v.update(compilation=rec['result'], build_identity=identity, compiled_image=image)
            runtime.save(run, state); return v['compilation']
    out = base / str(time.time_ns())
    result = compiler(doc, out / 'attempt-1', image=image, assets=assets, passes=2)
    result['path'] = str((out / 'attempt-1').relative_to(run))
    record = {'status': result['status'], 'attempts': [result], 'document_changed': False,
              'model_repair_requested': False, 'package_installation': 'not authorized; missing dependencies stay explicit'}
    atomic_json(out / 'completion-build.json', {'identity': identity, 'result': record})
    v.update(compilation=record, build_identity=identity, compiled_image=image)
    runtime.save(run, state)
    return record


def qualify_compiler(run, state):
    env = state['compiler_environment']; verify_seal(run / env['path'], env['seal'])
    cp = subprocess.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', env['image']],
                        capture_output=True, text=True, check=False)
    result = {'at': runtime.now(), 'expected_image': env['image'], 'returncode': cp.returncode,
              'stdout': cp.stdout, 'stderr': cp.stderr, 'installation_or_pull': False,
              'saved_qualification': env['path']}
    if cp.returncode or cp.stdout.strip() != env['image']:
        result['status'] = 'unavailable'; atomic_json(run / 'compiler-runtime-check.json', result)
        raise runtime.Fatal('Existing isolated compiler image inaccessible/unavailable; no install or host fallback. See compiler-runtime-check.json')
    result['status'] = 'existing_immutable_qualified_image_available'
    atomic_json(run / 'compiler-runtime-check.json', result)


def before_reserve(run, state, task, body):
    if task['status'] != 'pending' or any(c['parent'] == task['id'] for c in state['calls']):
        raise runtime.Fatal('Completion task already consumed/reserved')
    if any(body.get(k) != v for k, v in {'model': 'glm53-regular', 'max_tokens': 131072, 'stream': True,
                                        'reasoning_effort': completion.EFFORTS[task['phase']]}.items()):
        raise runtime.Fatal('Wrong outgoing model/effort/output allowance')
    native = read_json(folder(run, task['source_key']) / 'native.json')
    completion.validate_target(native, task['section'])
    if task['phase'] == 'critic':
        label = state['current_versions'].get(task['key'])
        if not label:
            raise runtime.Fatal('Critic lacks its completed conversion')
        v = state['versions'][task['key']][label]
        doc = (run / v['path']).read_text()
        if doc not in body['messages'][0]['content']:
            raise runtime.Fatal('Outgoing critic draft differs from own conversion')
        task['dispatched_draft_label'] = label
        task['dispatched_draft_sha256'] = v['sha256']
    record = {'task': task['id'], 'body_sha256': fingerprint(body),
              'target_sha256': fingerprint(task['section']), 'draft_sha256': task.get('dispatched_draft_sha256')}
    safe_write(run / 'dispatch-previews' / (task['id'].replace('/', '-') + '.json'), json.dumps(record, indent=2) + '\n')


def finish(run, state, task, answer, call, *, compiler=compile_version):
    """Idempotent local settlement; generation/build faults do not poison siblings."""
    key, phase = task['key'], task['phase']; task['call'] = call['id']
    if task.get('settled_call') == call['id']:
        return
    if answer is None:
        task.update(status=call.get('failure_kind', 'no_final_answer'), error=call.get('error'), settled_call=call['id'])
        runtime.save(run, state); return
    document, info = chapter_accuracy.envelope(answer, book.simple.extract_document)
    label = phase + '-' + call['id']
    prior_label = task.get('dispatched_draft_label') or state['current_versions'].get(key)
    if phase == 'critic' and prior_label:
        v = state['versions'][key][prior_label]
        if task.get('dispatched_draft_sha256') and v['sha256'] != task['dispatched_draft_sha256']:
            raise runtime.Fatal('Recorded critic input changed during finalization')
    replacement = document is not None and chapter_accuracy.complete_document(document)
    if replacement:
        remember(run, state, key, label, document, {'call': call['id'], 'extraction': info})
        current = label
        status = 'conversion_completed' if phase == 'convert' else 'critic_revised'
    elif phase == 'critic' and prior_label:
        current = prior_label
        status = 'critic_revision_unusable' if r'\documentclass' in answer or r'\begin{document}' in answer else 'critic_unchanged'
    else:
        task.update(status='complete_answer_without_document', error='No unambiguous complete document; raw answer retained', settled_call=call['id'])
        runtime.save(run, state); return
    raw_notes, capture = edit.notes_text(answer, info)
    notes = edit.notes_record(key, raw_notes, captured=capture, phase=label)
    # Compare against the previous phase's immutable note record, not a partly
    # finalized current record from this same call on restart.
    previous = task.get('input_accuracy_record')
    if phase == 'critic' and previous is None:
        previous = state.get('accuracy_records', {}).get(key)
        if previous and Path(previous).name != label + '.json':
            task['input_accuracy_record'] = previous
    if previous and Path(previous).name != label + '.json':
        notes = edit.reconcile_notes(read_json(run / previous), notes)
    note_path = Path('accuracy') / key / (label + '.json')
    safe_write(run / note_path, json.dumps(notes, indent=2, ensure_ascii=False) + '\n')
    md = '# ' + key + ' ' + label + '\n\n' + '\n\n'.join('## ' + e['id'] + '\nDisposition: ' + e['status'] + '\n\n' + e['text'] for e in notes['items'])
    safe_write(run / note_path.with_suffix('.md'), md)
    safe_write(run / note_path.with_name(label + '.raw.md'), raw_notes)
    state['accuracy_records'][key] = str(note_path); state['accuracy'][key] = str(note_path.with_suffix('.md'))
    text = (run / state['versions'][key][current]['path']).read_text()
    extra = [dict(x, attribution='GLM') for x in notes['items'] if x['category'] == 'material']
    annotated = edit.annotate(text, extra) if extra else text
    allowed = set(read_json(folder(run, task['source_key']) / 'assets.json'))
    annotated, path_edits = normalize_asset_paths(annotated, allowed)
    if annotated != text:
        ann = label + '-annotated'
        remember(run, state, key, ann, annotated, {'from': current, 'notes': str(note_path), 'asset_path_edits': path_edits})
        current = ann
    state['current_versions'][key] = current
    v = state['versions'][key][current]
    native = read_json(folder(run, task['source_key']) / 'native.json')
    assessment = completion.coverage_check(annotated, native, task['section']['blocks'])
    task['coverage_check'] = assessment
    # Selection retains generated text even if indicators/builds show gaps. The
    # report never promotes these spans to source-verified complete content.
    existing = next((r for r in state['selection_ledger'] if r['unit'] == key), None)
    row = {'unit': key, 'source_key': task['source_key'], 'blocks': task['section']['blocks'],
           'selection': current, 'version_sha256': v['sha256'], 'decision': 'New own-conversion/critic completion result',
           'model_review': [status] if phase == 'critic' else [], 'coverage_check': assessment,
           'source_checked': 'not independently established', 'possible_content_gaps': any(assessment[k] for k in
               ('missing_heading_candidates', 'empty_appendix_body_candidates', 'missing_required_charts', 'table_count_warning', 'missing_explicit_equation_numbers'))}
    if phase == 'critic' and prior_label:
        actual_input = run / state['versions'][key][prior_label]['path']
        if sha(actual_input) != state['versions'][key][prior_label]['sha256']:
            raise runtime.Fatal('Actual critic comparison input changed')
        comparison = material_comparison(actual_input.read_text(), annotated)
        comparison.update(original_path=str(actual_input), original_sha256=sha(actual_input),
                          selected_sha256=v['sha256'], critic_call=call['id'])
        row['critic_preservation_comparison'] = comparison
        comparison_dir = run / 'provenance' / key / label
        safe_write(comparison_dir / 'material-comparison.json', json.dumps(comparison, indent=2, ensure_ascii=False)+'\n')
        safe_write(comparison_dir / 'critic-change.diff', ''.join(difflib.unified_diff(
            actual_input.read_text().splitlines(True), annotated.splitlines(True),
            fromfile=str(actual_input), tofile=v['path'])))
    if existing:
        existing.clear(); existing.update(row)
    else:
        state['selection_ledger'].append(row)
    runtime.save(run, state)
    try:
        compiler(run, state, key, current)
    except (OSError, ValueError) as exc:
        v['compilation'] = {'status': 'build_failure_unresolved', 'error': str(exc), 'compilation_claim': False}
    task.update(status=status, settled_call=call['id'], final_version=current)
    runtime.save(run, state)


def reconcile_unfinished(run, state, *, finish_fn=finish):
    """Recover only sealed, settled transport results. Never resend uncertainty."""
    tasks = {t['id']: t for t in state['tasks']}
    for call in state['calls']:
        path = run / 'calls' / call['id']
        if call['status'] == 'in_progress':
            if not (path / 'outcome.json').is_file() or not (path / 'manifest.json').is_file():
                raise runtime.Fatal('Uncertain reservation ' + call['id'] + ': no settled sealed outcome; inspect without replay')
            settled = read_json(path / 'outcome.json')
            if settled['status'] not in ('completed_response', 'failed'):
                raise runtime.Fatal('Transport outcome remains uncertain')
            if any(settled[k] != call[k] for k in ('id', 'parent', 'request_sha256')):
                raise runtime.Fatal('Transport settlement identity mismatch')
            seal = sha(path / 'manifest.json'); verify_seal(path, seal)
            if fingerprint(read_json(path / 'request.json')) != call['request_sha256']:
                raise runtime.Fatal('Settled request changed')
            call.update(settled, seal=seal)
        if call['parent'] == 'readiness':
            continue
        task = tasks[call['parent']]
        if task.get('settled_call') == call['id']:
            continue
        if not call.get('seal'):
            raise runtime.Fatal('Unsealed result cannot be recovered')
        verify_seal(path, call['seal'])
        answer_path = path / 'answer.txt'
        if not answer_path.exists():
            answer_path = path / 'content.txt'
        answer = answer_path.read_text() if call['status'] == 'completed_response' and answer_path.is_file() else None
        if call['status'] == 'completed_response' and answer is None:
            raise runtime.Fatal('Completed response text unavailable; no replay')
        finish_fn(run, state, task, answer, call)
    runtime.save(run, state)


def execute_queue(run, state, *, sample, verify_inputs, coordinator=concurrent.coordinate, finish_fn=finish):
    if state['status'] == TERMINAL:
        return
    coordinator(run, state, state['tasks'], body_for=request_for, finish=finish_fn,
                verify=verify_inputs, changed=lambda: report(run, state), sample=sample,
                fixed_level=2, before_reserve=lambda s, t, b: before_reserve(run, s, t, b))
    if any(t['status'] in ('pending', 'running') for t in state['tasks']):
        raise runtime.Fatal('Coordinator stopped with undispatched work; no false terminal status')
    state['stage'] = 'automatic final assembly and packaging'
    runtime.save(run, state)


def reading_order(state, key):
    unit = state['source_units'][key]; source = unit['source_key']
    book_name = source.split('-')[0]
    chapter = int(source.split('-')[1]) if source.split('-')[1].isdigit() else {'postscript': 90, 'epilogue': 90, 'bibliography': 91}.get(source.split('-')[1], 99)
    first = unit['section']['first']; m = re.search(r'p(\d+):b(\d+)', first)
    return book_name, chapter, int(m[1]) if m else 0, int(m[2]) if m else 0, key


def coverage_report(run, state):
    canonical = read_json(run / 'canonical-source-map.json')
    owned = completion.unique_coverage(state['selection_ledger'])
    rows = []
    for part in canonical:
        owners = sorted({owned[b] for b in part['blocks'] if b in owned})
        absent = [b for b in part['blocks'] if b not in owned]
        rows.append({'key': part['key'], 'title': part['title'], 'physical_pages': part['physical_pages'],
                     'source_blocks': part['blocks'], 'selected_units': owners, 'unretained_source_blocks': absent,
                     'target_accounting': 'covered' if not absent else 'partial' if owners else 'missing',
                     'output_completeness': 'not independently established; see selected-unit indicators',
                     'model_review': 'per selected unit', 'source_checked': 'only explicitly recorded individual findings'})
    return {'canonical_Bergomi': rows, 'selected_units': state['selection_ledger'],
            'canonical_counts': dict(Counter(x['target_accounting'] for x in rows)),
            'all_book_units': {k: {'source_key': u['source_key'], 'blocks': u['section']['blocks'],
                                  'selected_version': state['current_versions'].get(k)} for k, u in state['source_units'].items()},
            'not_a_semantic_completeness_claim': True}


def report(run, state):
    counts = Counter(t['status'] for t in state['tasks'])
    current = [(k, state['versions'][k][lab]) for k, lab in state['current_versions'].items()]
    builds = Counter(v['compilation']['status'] for _, v in current)
    active = [{'task': t['id'], 'call': t.get('call')} for t in state['tasks'] if t['status'] == 'running']
    timings = {k: sum(c.get('metadata', {}).get('usage', {}).get(k, 0) for c in state['calls']) for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
    summary = {'at': runtime.now(), 'status': state['status'], 'prepared_not_running': state['status'] == 'prepared_offline',
               'run': str(run), 'phase': state.get('stage'), 'active_calls': active, 'task_counts': dict(counts),
               'settled_work': sum(t.get('settled_call') is not None for t in state['tasks']), 'new_calls': len(state['calls']),
               'historical_calls': state['historical_calls'], 'reused_outputs': sum(u['kind'] == 'reused' for u in state['source_units'].values()),
               'new_output_units': sum(u['kind'] == 'new' and k in state['current_versions'] for k, u in state['source_units'].items()),
               'missing_output_units': [k for k in state['source_units'] if k not in state['current_versions']],
               'build_outcomes': dict(builds), 'tokens': timings,
               'request_seconds': sum(c.get('elapsed_seconds', 0) for c in state['calls']),
               'last_progress': max((c.get('completed_at', c.get('reserved_at', '')) for c in state['calls']), default=state['created_at']),
               'diagnostic': state.get('diagnostic'), 'report': str(run / 'report.md'), 'log': str(run / 'terminal.log'),
               'deliveries': state.get('deliveries', {}), 'inspection': state.get('inspection'),
               'accuracy': 'unverified except attributed individual findings; coverage indicators do not certify mathematics'}
    atomic_json(run / 'progress.json', summary)
    dest = ROOT / 'results/book-completion' / (run.name + '-progress.json')
    atomic_json(dest, summary)
    coverage = coverage_report(run, state)
    atomic_json(run / 'coverage.json', coverage)
    lines = ['# Gatheral/Bergomi finite completion', '', '**' + state['status'].upper() + '**', '',
             'Prepared work is not a running model job. No completion/fidelity claim follows from normal responses or builds.', '',
             f'Run: `{run}`', f'Phase: {state.get("stage")}', f'New calls: {len(state["calls"])}; active: {len(active)}.',
             f'Tasks: {dict(counts)}', f'Current builds: {dict(builds)}',
             f'Bergomi canonical target accounting: {coverage["canonical_counts"]}.', '',
             '## Selected reading units', '', '| Unit | Source span | Version | Build | Preservation indicators |', '|---|---|---|---|---|']
    for key in sorted(state['source_units'], key=lambda k: reading_order(state, k)):
        u = state['source_units'][key]; label = state['current_versions'].get(key)
        record = state['versions'][key][label] if label else {}
        row = next((r for r in state['selection_ledger'] if r['unit'] == key), {})
        ck = row.get('coverage_check', {})
        flags = {'headings': len(ck.get('missing_heading_candidates', [])), 'charts': len(ck.get('missing_required_charts', [])),
                 'empty_appendix_bodies': ck.get('empty_appendix_body_candidates', []),
                 'numbered_equation_candidates': ck.get('missing_explicit_equation_numbers', []),
                 'references': ck.get('undefined_labels', []), 'table_warning': ck.get('table_count_warning', False)}
        lines.append('| ' + ' | '.join((key, u['section']['first'] + ' … ' + u['section']['last'], label or 'MISSING',
            record.get('compilation', {}).get('status', 'not attempted'), str(flags))) + ' |')
    lines += ['', '## Boundaries', '',
              'High conversion / Max own-draft critic; 131072 output tokens; at most two concurrent requests. '
              'No overall deadline or inherited global call ceiling. One attempt per phase, no automatic resend of uncertain work. '
              'No software installation, service switch, cloud call, source-OCR rerun, articles or autonomous code repair.', '',
              '## Current paths', '', 'Progress: `' + str(dest) + '`', 'Log: `' + str(run / 'terminal.log') + '`',
              'Saved editions and ZIPs: ' + json.dumps(state.get('deliveries', {}), ensure_ascii=False),
              'Inspection ZIP: ' + str(state.get('inspection', {}).get('path')), '']
    (run / 'report.md').write_text('\n'.join(lines))
    return summary


def selected_pdf(run, version):
    if not version['compilation']['status'].startswith('passed'):
        return None
    for a in reversed(version['compilation'].get('attempts', [])):
        path = run / a['path'] / 'document.pdf'
        if a.get('input_sha256') == version['sha256'] and path.is_file():
            return path
    return None


def write_zip(path, files):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name, source in sorted(files.items()):
            if isinstance(source, bytes):
                z.writestr(name, source)
            else:
                z.write(source, name)
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None or len(z.namelist()) != len(set(z.namelist())):
            raise runtime.Fatal('Archive integrity check failed')
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def assemble(run, state, book_name, *, compile=True, compiler=tex_compile.compile_document):
    keys = sorted([k for k, u in state['source_units'].items() if u['source_key'].startswith(book_name + '-')], key=lambda k: reading_order(state, k))
    if len(keys) != len(set(keys)):
        raise runtime.Fatal('Grouped reading document duplicated')
    identity = fingerprint({'versions': {k: state['current_versions'].get(k) for k in keys},
                            'hashes': {k: state['versions'][k][state['current_versions'][k]]['sha256'] for k in keys if k in state['current_versions']},
                            'builds': {k: state['versions'][k][state['current_versions'][k]]['compilation'] for k in keys if k in state['current_versions']},
                            'compile': compile})
    previous = state.get('deliveries', {}).get(book_name)
    if previous and previous.get('identity') == identity and Path(previous['source_zip']['path']).is_file():
        return previous
    out = run / 'editions' / (book_name + '-' + str(time.time_ns())); out.mkdir(parents=True)
    master = [r'\documentclass{book}\usepackage{pdfpages,hyperref}\begin{document}',
              r'\chapter*{Traceable working edition: ' + book_name + '}',
              'Target accounting, model review, compilation and source-checked findings are separate. Unresolved issues remain visible.']
    rows = []; build_assets = {}; tex_files = {}
    for key in keys:
        u = state['source_units'][key]; label = state['current_versions'].get(key)
        row = {'unit': key, 'source_key': u['source_key'], 'blocks': u['section']['blocks'],
               'physical_pages': u['section']['physical_pages'], 'version': label, 'pdf_included': False,
               'output_completeness': 'not independently established', 'source_verification': 'per attributed finding only'}
        if not label:
            master += [r'\chapter*{Missing ' + edit.metadata_tex(key) + '}', edit.metadata_tex(u['section']['title']) + '. No usable completed draft; source preserved.']
            row['status'] = 'missing_output'; rows.append(row); continue
        v = state['versions'][key][label]; doc = run / v['path']; text = doc.read_text()
        row.update(sha256=v['sha256'], compilation=v['compilation']['status'], provenance=v['origin'])
        target = out / 'chapters' / key / 'document.tex'; target.parent.mkdir(parents=True); shutil.copyfile(doc, target)
        tex_files[f'tex/{key}.tex'] = target
        try:
            assets = asset_map(run, u['source_key'], text)
        except ValueError as exc:
            assets = {}; row['dependency_error'] = str(exc)
        for name, src in assets.items():
            dst = target.parent / name; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, dst)
        accuracy = run / 'accuracy' / key
        if accuracy.is_dir():
            shutil.copytree(accuracy, out / 'accuracy' / key)
        pdf = selected_pdf(run, v)
        part = out / 'parts' / (key + '.tex'); part.parent.mkdir(exist_ok=True)
        if pdf:
            dest = out / 'assets' / (key + '.pdf'); dest.parent.mkdir(exist_ok=True); shutil.copyfile(pdf, dest)
            part.write_text(r'\includepdf[pages=-,pagecommand={}]{assets/' + key + '.pdf}')
            build_assets['assets/' + key + '.pdf'] = dest; row['pdf_included'] = True
        else:
            part.write_text(r'\chapter*{' + edit.metadata_tex(key) + '}Compilation unsuccessful or not performed; editable text retained. This is a PDF gap.')
        build_assets['parts/' + key + '.tex'] = part
        master.append(r'\input{parts/' + key + '.tex}')
        ledger = next((r for r in state['selection_ledger'] if r['unit'] == key), {})
        row['content_indicators'] = ledger.get('coverage_check', {})
        row['model_review'] = ledger.get('model_review', [])
        row['review_dispositions'] = [d for d in ledger.get('review_dispositions', []) if d.get('version_sha256') == v['sha256']]
        rows.append(row)
    supplement = run / ('source-supplement/gatheral-front-blank-index.pdf' if book_name == 'gatheral' else 'bergomi/source-supplement.pdf')
    if supplement.is_file():
        dest = out / 'assets/source-supplement.pdf'; dest.parent.mkdir(exist_ok=True); shutil.copyfile(supplement, dest)
        build_assets['assets/source-supplement.pdf'] = dest
        master += [r'\chapter*{Original source supplement}',
                   'Front/back matter is supplied as original PDF pages, not converted editable content. ' +
                   ('The original index uses original printed-page locators.' if book_name == 'gatheral' else 'The supplied original PDF contains no index; none has been invented.'),
                   r'\includepdf[pages=-,pagecommand={}]{assets/source-supplement.pdf}']
    master.append(r'\end{document}'); (out / 'master.tex').write_text('\n'.join(master))
    atomic_json(out / 'coverage-version-manifest.json', {'book': book_name, 'reading_order': rows,
                'assembly': 'PDF inclusions; chapter text remains editable in separate standalone documents',
                'source_identity': read_json(ROOT / ('docs/source-provenance/' + book_name + ('-intake-20261025.json' if book_name == 'gatheral' else '-intake-20261027.json'))),
                'supplement': str(supplement), 'completion_claim': False})
    issues = [r for r in rows if not r['pdf_included'] or any(r.get('content_indicators', {}).get(k) for k in
        ('missing_heading_candidates', 'empty_appendix_body_candidates', 'missing_required_charts', 'missing_explicit_equation_numbers', 'undefined_labels', 'table_count_warning'))]
    atomic_json(out / 'unresolved-issues.json', {'units': issues, 'mathematics': 'Retain all embedded editorial notes; a clean mechanical check does not establish accuracy.',
        'flag_interpretation': 'Raw automated candidates are retained. Exact-version review_dispositions identify reviewed false alarms; these do not suppress checks on future versions.'})
    instructions = ('# ' + book_name.title() + ' working edition\n\nMaster includes precompiled section PDFs, not chapter text directly. '
        'Each chapters/<unit>/document.tex is a standalone editable document with inline macros and relative assets. '
        'Reading order, exact versions, source blocks, gaps and review limits are in coverage-version-manifest.json. '
        'Grouped outputs occur once. Captions, source corrections and unresolved notes are preserved. '
        'The PDF supplement is original front/back/index material, not editable transcription.\n\n'
        'Rebuild through the project completion runner using the existing isolated compiler; it compiles changed standalone documents before the PDF-inclusion master. '
        'No host compiler or package installation is authorized. If independently adapting these sources, work from each document directory; '
        'do not nest standalone documentclass/document environments.\n\n'
        'The small TeX-only ZIP excludes binaries/history; figure filenames and captions remain. Image-only charts/formulas are not reconstructed by packaging. '
        'The complete-source ZIP supplies the referenced local assets. See unresolved-issues.json; neither book is certified mathematically complete.\n')
    (out / 'README.md').write_text(instructions)
    compilation = {'status': 'not_attempted', 'compilation_claim': False}
    if compile:
        compilation = compiler((out / 'master.tex').read_text(), out / 'compile', image=state['compiler_environment']['image'], assets=build_assets, passes=2)
        atomic_json(out / 'compilation.json', compilation)
        if compilation.get('compilation_claim') and (out / 'compile/document.pdf').is_file():
            shutil.copyfile(out / 'compile/document.pdf', out / 'reading.pdf')
    stem = ROOT / 'results/book-completion' / (out.name + '-' + run.name)
    tex_files['README.md'] = (instructions + '\nTEXT ONLY: binary/image-only content is absent; references remain.\n').encode()
    tex_files['manifest.json'] = json.dumps({'book': book_name, 'reading_order': rows, 'binary_assets': 'excluded', 'complete_book': False}, indent=2, ensure_ascii=False).encode()
    tex_zip = write_zip(stem.with_name(stem.name + '-tex-only.zip'), tex_files)
    source_files = {str(p.relative_to(out)): p for p in out.rglob('*') if p.is_file() and 'compile' not in p.relative_to(out).parts}
    source_files['FILE-HASHES.json'] = json.dumps({n: sha(p) for n, p in source_files.items()}, indent=2).encode()
    source_zip = write_zip(stem.with_name(stem.name + '-complete-source.zip'), source_files)
    result = {'identity': identity, 'edition': str(out), 'reading_pdf': str(out / 'reading.pdf') if (out / 'reading.pdf').is_file() else None,
              'master_build': compilation['status'], 'text_parts': sum(r['version'] is not None for r in rows),
              'pdf_parts': sum(r['pdf_included'] for r in rows), 'pdf_gaps': [r['unit'] for r in rows if not r['pdf_included']],
              'tex_only_zip': tex_zip, 'source_zip': source_zip}
    state.setdefault('deliveries', {})[book_name] = result; runtime.save(run, state)
    return result


def finalize(run, state, *, compiler=compile_version, assembler=assemble):
    for key, label in list(state['current_versions'].items()):
        check_pause(run)
        compiler(run, state, key, label)
    for name in ('gatheral', 'bergomi'):
        check_pause(run)
        assembler(run, state, name, compile=True)
    state.update(status=TERMINAL, stage='finished finite queue; delivery and unresolved issues recorded', finished_at=runtime.now())
    runtime.save(run, state); report(run, state)


def inspection_bundle(run, state):
    report(run, state)
    dest = ROOT / 'results/inspection' / ('book-completion-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + str(time.time_ns()) + '.zip')
    files = {}
    for name in ('state.json', 'binding.json', 'completion-plan.json', 'ancestry.json', 'canonical-source-map.json', 'coverage.json', 'progress.json', 'report.md', 'validation.json',
                 'compiler-runtime-check.json', 'normal-terminal-checks.json'):
        if (run / name).is_file():
            files['prepared-run/' + name] = run / name
    checks = run / 'normal-terminal-checks.json'
    if checks.exists():
        logfile = Path(read_json(checks).get('log', ''))
        if logfile.is_file() and logfile.resolve().is_relative_to(ROOT):
            files['validation/full-tests.log'] = logfile
    for key, label in state['current_versions'].items():
        v = state['versions'][key][label]
        if not v['compilation'].get('reused_exact_document_dependencies_image'):
            for attempt in v['compilation'].get('attempts', []):
                for name in ('console.log', 'result.json'):
                    p = run / attempt['path'] / name
                    if p.is_file():
                        files[f'validation/builds/{key}/{name}'] = p
    for root in ('provenance', 'accuracy'):
        for p in (run / root).rglob('*'):
            if p.is_file() and p.suffix in ('.tex', '.md', '.json', '.diff'):
                files['prepared-run/' + p.relative_to(run).as_posix()] = p
    for key, label in state['current_versions'].items():
        v = state['versions'][key][label]
        files['selected/' + key + '/document.tex'] = run / v['path']
    for p in sorted(set(ROOT.glob('tests/test_book_completion*.py')) | set(ROOT.glob('probe/book_completion.py')) | set(ROOT.glob('scripts/book_completion.py'))):
        files['implementation/' + p.relative_to(ROOT).as_posix()] = p
    for name in ('AGENTS.md', 'docs/CODEX-HANDOVER.md', 'docs/PROJECT-STATE.md', 'docs/BOOK-COMPLETION.md', 'scripts/run-book-completion.sh', 'probe/chapter_concurrency.py'):
        if (ROOT / name).is_file():
            files['implementation/' + name] = ROOT / name
    git = subprocess.run(['git', 'diff', '--no-ext-diff', '--no-textconv'], cwd=ROOT, capture_output=True, check=True,
                         env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}).stdout
    files['working-tree.diff'] = git
    files['START-HERE.md'] = ('# Finite book completion review\n\n' +
        '**' + state['status'].upper() + '**. No inference during coding/preparation.\n\n'
        'Read prepared-run/report.md, completion-plan.json, coverage.json and each provenance decision/diff. '
        'The canonical map and partial adoption ledger retain missing appendices separately. '
        'Saved histories remain in original run directories; selections do not certify mathematics. '
        'Compiler records distinguish reuse from actual new builds. Required normal-terminal checks/readiness are automatic. '
        'No supervisor, Bubblewrap change, service switch or cloud work is required.\n').encode()
    files['FILE-HASHES.json'] = json.dumps({k: hashlib.sha256(v).hexdigest() if isinstance(v, bytes) else sha(v) for k, v in files.items()}, indent=2).encode()
    result = write_zip(dest, files); state['inspection'] = result; runtime.save(run, state); report(run, state)
    return result


def normal_checks(run):
    identity = fingerprint({'code': hashes(), 'tests': runtime.test_hashes()})
    record = run / 'normal-terminal-checks.json'
    if record.exists() and read_json(record).get('passed_identity') == identity:
        return
    log = run / ('normal-terminal-tests-' + str(time.time_ns()) + '.log')
    with log.open('w') as output:
        cp = subprocess.run([str(PYTHON), '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
    atomic_json(record, {'passed_identity': identity if cp.returncode == 0 else None, 'exit_status': cp.returncode,
                        'log': str(log), 'policy': 'once per code/test identity; no per-chapter full-suite rerun'})
    if cp.returncode:
        raise runtime.Fatal('Required tests failed; no inference. See ' + str(log))


def check_pause(run):
    if (run / 'pause.json').exists() or (run / 'stop.json').exists():
        raise runtime.StopRun('Operator pause requested; no further admission, owned work drained')


def require_current(run):
    if not POINTER.exists() or Path(read_json(POINTER)['run']).resolve() != run.resolve():
        raise runtime.Fatal('This is not the current completion generation; refusing an obsolete queue')


def worker(run):
    require_current(run)
    with (run / 'terminal.log').open('a', buffering=1) as log:
        os.dup2(log.fileno(), 1); os.dup2(log.fileno(), 2)
        state = verify(run)
        if state['status'] == TERMINAL:
            return
        b = read_json(run / 'binding.json')
        guard = InputGuard({**b['consumed'], **b['prepared'], **{str(ROOT / p): h for p, h in b['code'].items()}})
        with writer_lock(ROOT), writer_lock(run):
            try:
                state.update(status='running', stage='verify existing runtime/compiler; reconcile saved outcomes', diagnostic=None)
                state['launches'].append({'at': runtime.now(), 'calls_before': len(state['calls'])}); runtime.save(run, state)
                book.converter_idle(ROOT); runtime.check_other_jobs()
                # Read-only existing-service checks, never the service-start route.
                helpers = speed.module(); book.guard_gpu_workloads(run, helpers, resident_glm=True)
                concurrent.capture_build(helpers, run)
                sample = speed.sampler(run, state, helpers); speed.healthy(sample(0))
                efforts = speed.effort_check(run, helpers)
                if efforts.get('status') == 'probe_error':
                    raise runtime.Fatal('High/Max runtime effort rendering unverified; no dispatch')
                qualify_compiler(run, state)
                reconcile_unfinished(run, state)
                for key, label in list(state['current_versions'].items()):
                    check_pause(run)
                    compile_version(run, state, key, label)
                if any(t['status'] == 'pending' for t in state['tasks']):
                    check_pause(run)
                    runtime.readiness(run, state)
                    state['stage'] = 'whole approved missing-content queue; conversion then own critic'
                    def verify_inputs():
                        guard.check(); verify(run, check_files=False)
                    execute_queue(run, state, sample=sample, verify_inputs=verify_inputs)
                finalize(run, state)
            except runtime.StopRun as exc:
                state.update(status='draining' if (run / 'pause.json').exists() and not isinstance(exc, runtime.Fatal) else 'stopped_error', diagnostic=str(exc))
            except BaseException as exc:
                trace = concurrent.exception_trace(run, exc, 'Finite book completion worker')
                state.update(status='stopped_error', diagnostic=type(exc).__name__ + ': ' + str(exc), diagnostic_file=trace)
            finally:
                runtime.save(run, state); report(run, state)
        if state['status'] == 'draining':
            state['status'] = 'paused'
        state['writer_released_at'] = runtime.now(); runtime.save(run, state)
        inspection_bundle(run, state)
        print('Completion worker ended:', state['status'], 'Report:', run / 'report.md', flush=True)


def launch(run):
    # A terminal invocation must not perform even readiness/service/test calls.
    state = read_json(run / 'state.json')
    if state['status'] == TERMINAL:
        print('Already finished; zero dispatch/readiness. Report:', run / 'report.md'); return
    require_current(run)
    state = verify(run)
    if not speed.idle(ROOT) or not speed.idle(run):
        raise runtime.Fatal('Writer active/draining; no launch')
    for c in state['calls']:
        if c['status'] == 'in_progress' and not (run / 'calls' / c['id'] / 'manifest.json').is_file():
            raise runtime.Fatal('Uncertain in-flight call ' + c['id'] + '; no automatic replay or readiness')
    cp = subprocess.run(['tmux', 'has-session', '-t', SESSION], capture_output=True, text=True)
    if cp.returncode == 0:
        raise runtime.Fatal('Completion tmux already exists; inspect status, do not start another writer')
    if cp.returncode != 1 or any(s in cp.stderr.lower() for s in ('permission denied', 'operation not permitted')):
        raise runtime.Fatal('Cannot inspect tmux: ' + cp.stderr)
    normal_checks(run)
    book.arrange_glm(run, check_only=True)
    for name in ('pause.json', 'stop.json'):
        (run / name).unlink(missing_ok=True)
    cmd = shlex.join([str(PYTHON), '-B', '-u', str(Path(__file__).resolve()), 'worker', '--run', str(run)])
    subprocess.run(['tmux', 'new-session', '-d', '-s', SESSION, 'cd ' + shlex.quote(str(ROOT)) + ' && exec ' + cmd], check=True)
    print('STARTED persistent completion:', run, '\nLog:', run / 'terminal.log', '\nProgress:', ROOT / 'results/book-completion' / (run.name + '-progress.json'))


def status(run):
    state = read_json(run / 'state.json')
    print(json.dumps({'status': state['status'], 'phase': state.get('stage'), 'run': str(run),
                      'task_counts': dict(Counter(t['status'] for t in state['tasks'])),
                      'active': [t['id'] for t in state['tasks'] if t['status'] == 'running'],
                      'new_calls': len(state['calls']), 'report': str(run / 'report.md'), 'log': str(run / 'terminal.log'),
                      'progress': str(ROOT / 'results/book-completion' / (run.name + '-progress.json')),
                      'deliveries': state.get('deliveries'), 'inspection': state.get('inspection'), 'diagnostic': state.get('diagnostic')}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'run', 'resume', 'worker', 'status', 'pause', 'bundle', 'compile-saved'))
    parser.add_argument('--run', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(); return
    run = (args.run or Path(read_json(POINTER)['run'])).resolve()
    if args.action in ('run', 'resume'):
        launch(run)
    elif args.action == 'worker':
        worker(run)
    elif args.action == 'status':
        status(run)
    elif args.action == 'pause':
        if read_json(run / 'state.json')['status'] != TERMINAL:
            atomic_json(run / 'pause.json', {'at': runtime.now()})
        print('Pause requested; admission stops and owned requests/finalization drain. No service is stopped.')
    elif args.action == 'bundle':
        with writer_lock(ROOT), writer_lock(run):
            state = verify(run); print(inspection_bundle(run, state)['path'])
    elif args.action == 'compile-saved':
        with writer_lock(ROOT), writer_lock(run):
            state = verify(run); qualify_compiler(run, state)
            for key, label in list(state['current_versions'].items()):
                compile_version(run, state, key, label)
            for name in ('gatheral', 'bergomi'):
                assemble(run, state, name, compile=True)
            report(run, state)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('ERROR:', type(exc).__name__ + ':', exc, file=sys.stderr)
        raise SystemExit(1)
