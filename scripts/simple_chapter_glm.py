"""Simple whole-chapter experiment; reuses the existing safe chapter runtime.

No OCR, service operations, cloud dispatch, semantic acceptance or automatic retry.
"""
import argparse
import copy
import html
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
import unicodedata
import zipfile

from probe import chapter_glm as runtime, chapter_protocol as protocol, tex_compile, compiler_environment
from probe import chapter_sources, chapter_accuracy
from probe.common import atomic_json, read_json, sha, fingerprint, files_manifest, writer_lock
from probe.experiment import verify_seal
from probe.local_model import LocalClient, ProbeError

ROOT = runtime.ROOT
NATIVE = ROOT / 'runs/chapter-glm-input-20261026T031434Z-2392d8'
PRIOR = ROOT / 'runs/chapter-glm-trial-20261026T032225Z-ac8537'
POINTER = ROOT / 'results/simple-chapter-glm-current.json'
SESSION = 'simple-chapter-glm'
KEYS = ['klebaner-04'] + [f'gatheral-{i:02d}' for i in range(1, 12)]
GATHERAL_KEYS = [f'gatheral-{i:02d}' for i in range(1, 12)] + ['gatheral-postscript', 'gatheral-bibliography']
FRESH_SCHEDULE = 'fresh-gatheral-conversion-critic-pairs-v1'
CONVERSION_MAX_TOKENS = 131072
REVIEW_MAX_TOKENS = 32768
CONVERT = ('Can you please convert this chapter into LaTeX and give me the complete '
           'LaTeX file? The supplied content was extracted from the original PDF using '
           'MinerU. Preserve the chapter\'s content, formulas, numbering, references, '
           'figures and captions; do not summarize it.')
REVIEW = ('Please review this LaTeX chapter against the supplied MinerU extraction. '
          'Look for omitted content or conditions, corrupted mathematics, inconsistent '
          'numbering and material reference errors. Give readable findings with the '
          'location, old text, suggested correction, reason and uncertainty. Save '
          'suggestions as a review; do not regenerate the chapter. State when source '
          'images or unavailable context are needed. This is not image verification.')


def code_hashes():
    return {**runtime.code_hashes(), **{p: sha(ROOT / p) for p in
            ('scripts/simple_chapter_glm.py', 'scripts/run-simple-chapter-glm.sh', 'scripts/tex-compiler/Dockerfile')}}


def heading_key(block):
    text = ' '.join(v for _, v in runtime.inputs.strings(block['native']))
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', text).lower())


def furniture(block, blocks):
    if block['kind'] in runtime.inputs.AUX:
        return 'saved native page-furniture classification'
    box = block.get('bbox')
    if block['kind'] != 'paragraph_title' or not box or box[3] > .08:
        return None
    # Conservative evidence combination, not a top-of-page blanket exclusion:
    # a matching heading elsewhere AND a folio on the same marginal baseline.
    folio = any(b['kind'] == 'page_number' and b['page'] == block['page']
                and b.get('bbox') and abs(b['bbox'][1] - box[1]) < .015 for b in blocks)
    matches = [b['id'] for b in blocks if b['id'] != block['id']
               and b['kind'] == 'paragraph_title' and heading_key(b) == heading_key(block)]
    if folio and matches:
        return 'running title beside folio; matching heading(s): ' + ', '.join(matches)
    return None


def chapter_text(data):
    pages = [p['page']['selected_page'] for p in data['pages']]
    if pages != sorted(set(pages)) or any(p['page']['owner'] is not True for p in data['pages']):
        raise ValueError('Duplicate, unordered or context-only chapter page')
    ids = [b['id'] for b in data['blocks']]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate source block')
    text = ''; ledger = []; math_count = 0
    for block in data['blocks']:
        reason = furniture(block, data['blocks'])
        row = {'id': block['id'], 'page': block['page'], 'kind': block['kind'],
               'excluded_furniture': reason}
        if not reason:
            # Use the already prepared native renderer output, not portable_export.
            body = block['tex']
            body = re.sub(r'(?m)^% (?:Literal native mathematics follows.*|TABLE SOURCE ASSET.*)\n?', '', body)
            if not body.strip():
                raise ValueError('Empty native representation retained for investigation: ' + block['id'])
            start = len(text); text += body + '\n\n'
            row.update(start=start, end=len(text))
            for kind, formula in runtime.inputs.strings(block['native']):
                if kind in ('equation', 'equation_inline') and formula:
                    if formula not in body:
                        raise ValueError('Native formula lost: ' + block['id'])
                    math_count += 1
        ledger.append(row)
    if re.search(r'(?m)^% (SRC |SOURCE_PAGE )', text):
        raise ValueError('Output-protocol markers leaked into simple input')
    return text, {'blocks': ledger, 'native_math_strings': math_count,
                  'furniture_count': sum(bool(r['excluded_furniture']) for r in ledger),
                  'source_pages': data['pages'], 'fidelity': 'OCR unverified; no output coverage claim'}


def request(source, generated=None):
    instruction = CONVERT if generated is None else REVIEW
    if generated is None and '\\includegraphics' in source:
        instruction += ' Keep the supplied relative image paths in \\includegraphics; the image files accompany the document.'
    text = instruction + '\n\nMINERU CHAPTER EXTRACTION:\n' + source
    if generated is not None:
        text += '\n\nGENERATED LATEX:\n' + generated
    body = {'model': protocol.MODEL, 'messages': [{'role': 'user', 'content': text}],
            'max_tokens': CONVERSION_MAX_TOKENS if generated is None else REVIEW_MAX_TOKENS, 'stream': False}
    protocol.budget(body)
    return body


def continuous_request(source, generated=None):
    """Same simple prompts; explicit critic allowance and durable streaming."""
    body = request(source, generated)
    body.update(max_tokens=131072, stream=True)
    protocol.budget(body)
    return body


def without_comments(text):
    """TeX comments swallow the newline; an escaped percent is literal."""
    lines = []
    for line in text.splitlines(keepends=True):
        for pos, char in enumerate(line):
            if char == '%':
                preceding = len(line[:pos]) - len(line[:pos].rstrip('\\'))
                if preceding % 2 == 0:
                    line = line[:pos]; break
        lines.append(line)
    return ''.join(lines)


def image_references(text):
    pattern = r'\\includegraphics\*?\s*(?:\[[^\]]*\]\s*)?\{\s*(?:\\detokenize\{([^{}]+)\}|([^{}]+?))\s*\}'
    return {a or b for a, b in re.findall(pattern, without_comments(text))}


def extract_document(answer):
    """Select one fenced document, never rewrite its contents or combine answers.

    Offsets are Python character offsets into the separately retained raw answer.
    This is envelope extraction, not a content-completeness validator.
    """
    fences = list(re.finditer(r'(?m)^ {0,3}(`{3,}|~{3,})([^\r\n]*)(?:\r?\n|$)', answer))
    start, end = 0, len(answer)
    status = 'unfenced'
    if fences:
        if (len(fences) != 2 or fences[0][1] != fences[1][1]
                or fences[0][2].strip().lower() not in ('', 'tex', 'latex') or fences[1][2].strip()):
            return None, {'status': 'ambiguous', 'reason': 'Expected one complete TeX fence; incomplete/multiple/unsupported fences retained for inspection'}
        start, end = fences[0].end(), fences[1].start()
        status = 'single_fenced_document' if (answer[:fences[0].start()] + answer[fences[1].end():]).strip() else 'enclosing_fence'
    draft = answer[start:end]
    visible = without_comments(draft)
    counts = [len(re.findall(p, visible)) for p in
              (r'\\documentclass(?:\s*\[[^\]]*\])?\s*\{', r'\\begin\s*\{document\}', r'\\end\s*\{document\}')]
    if any(n > 1 for n in counts) or (status == 'single_fenced_document' and counts != [1, 1, 1]):
        return None, {'status': 'ambiguous', 'reason': 'Surrounded fence must contain one complete document, never multiple documents'}
    prefix = answer[:fences[0].start()] if fences else ''
    suffix = answer[fences[1].end():] if fences else ''
    if re.search(r'(?m)^\s*\\(?:documentclass|begin\s*\{document\}|end\s*\{document\})', without_comments(prefix + suffix)):
        return None, {'status': 'ambiguous', 'reason': 'Additional document structure outside the selected fence'}
    return draft, {'status': status, 'start': start, 'end': end,
                   'intro_end': fences[0].start() if fences else 0,
                   'notes_start': fences[1].end() if fences else len(answer),
                   'content_change': 'none; exact contiguous character slice of raw answer'}


def save_conversion(run, task, answer, folder, *, meaning=False):
    folder.mkdir(parents=True, exist_ok=True)
    raw = folder / 'answer.raw.txt'; raw.write_text(answer, encoding='utf-8')
    draft, extraction = chapter_accuracy.envelope(answer, extract_document) if meaning else extract_document(answer)
    extraction['raw_answer_sha256'] = sha(raw)
    task.update(status='complete_response', extraction_status=extraction['status'],
                raw_answer=str(raw.relative_to(run)), draft_available=draft is not None,
                fidelity='not established; no block/output-marker contract')
    if draft is None:
        task.update(extraction_error=extraction['reason'])
    else:
        output = folder / 'generated.tex'; output.write_text(draft, encoding='utf-8')
        (folder / 'introductory-prose.txt').write_text(answer[:extraction['intro_end']], encoding='utf-8')
        (folder / 'conversion-notes.md').write_text(answer[extraction['notes_start']:], encoding='utf-8')
        task.update(output=str(output.relative_to(run)), output_sha256=sha(output),
                    outer_fence_stripped=extraction['status'] != 'unfenced',
                    notes=str((folder / 'conversion-notes.md').relative_to(run)))
        extraction['document_sha256'] = sha(output)
        if not draft.strip():
            task.update(status='empty_answer', draft_available=False, error='Final answer contains only an empty enclosing fence')
    atomic_json(folder / 'extraction.json', extraction)
    return draft


def document_observations(text, source, available):
    """Warnings, never a replacement for response status or semantic review."""
    used = image_references(text)
    return {'documentclass_present': bool(re.search(r'\\documentclass(?:\[[^\]]*\])?\{', text)),
            'begin_document_present': r'\begin{document}' in text,
            'end_document_present': r'\end{document}' in text,
            'source_assets_not_referenced': sorted(image_references(source) - used),
            'references_without_supplied_asset': sorted(used - set(available)),
            'fidelity': 'not established; normal completion is not proof of complete transcription'}


def initialize(native=NATIVE, *, fresh_gatheral_from=None):
    native = Path(native).resolve(); verify_seal(native)
    reference = Path(fresh_gatheral_from).resolve() if fresh_gatheral_from else None
    if reference:
        _, previous = recorded_evidence(reference)
        if previous['status'] == 'running' or any(c['status'] == 'in_progress' for c in previous['calls']):
            raise ValueError('Cache reference must not be running')
    keys = GATHERAL_KEYS if reference else KEYS
    run = runtime.inputs.new_path('simple-chapter-glm-trial'); run.mkdir()
    meta = read_json(native / 'inputs.json')
    gathered = [n for p in meta['parts'] if p['source'] == 'gatheral' for n in p['pages']]
    if gathered != list(range(1, 211)):
        raise ValueError('Native preparation does not account for all 210 owned pages')
    for key in keys:
        data = read_json(native / 'chapters' / key / 'source.json')
        inv = read_json(native / 'chapters' / key / 'inventory.json')
        originals = [p['page']['original_physical_page'] for p in data['pages']]
        if key == 'klebaner-04':
            expected = list(range(106, 137))
        else:
            part = next(p for p in runtime.inputs.PARTS if 'gatheral-' + p[0] == key)
            expected = list(range(part[2], part[3] + 1))
        if originals != expected:
            raise ValueError('Wrong chapter boundary: ' + key)
        text, sidecar = chapter_text(data)
        folder = run / 'inputs' / key; folder.mkdir(parents=True)
        (folder / 'source.tex').write_text(text)
        shutil.copyfile(native / 'chapters' / key / 'source.json', folder / 'native.json')
        sidecar.update(native_source_sha256=sha(folder / 'native.json'), source_sha256=sha(folder / 'source.tex'),
                       original_pages=originals, title=inv['title'])
        atomic_json(folder / 'provenance.json', sidecar)
        assets = sorted({a for b in data['blocks'] for a in b['assets']})
        for name in assets:
            src = native / name; dst = run / 'inputs' / name; dst.parent.mkdir(exist_ok=True)
            if not dst.exists(): shutil.copyfile(src, dst)
        atomic_json(folder / 'assets.json', assets)
        if not reference:
            atomic_json(folder / 'conversion-request.json', continuous_request(text))
            atomic_json(folder / 'budget.json', protocol.budget(continuous_request(text)))
    if reference:
        source_identities = chapter_sources.prepare_secondary(run, ROOT, keys, cache_run=reference)
        for key in keys:
            folder = run/'inputs'/key
            body = chapter_sources.request((folder/'source.tex').read_text(), (folder/'secondary.txt').read_text())
            atomic_json(folder/'conversion-request.json', body)
            atomic_json(folder/'budget.json', chapter_sources.budget_preview(body))
        scope = {'keys': keys, 'physical_pdf_pages': list(range(32, 199)), 'selected_page_count': 167,
                 'excluded_parts': [{'part': 'front matter', 'physical_pdf_pages': list(range(1, 32))},
                                    {'part': 'intentional blank', 'physical_pdf_pages': [199]},
                                    {'part': 'index', 'physical_pdf_pages': list(range(200, 211))}],
                 'whole_book': False, 'klebaner_included': False,
                 'order': 'Each conversion followed immediately by its critic; chapters 1–11, postscript, bibliography',
                 'critic_preview': 'Exact request assembled after each new draft and initial notes exist; no old draft substituted'}
        selected = [n for key in keys for n in read_json(run/'inputs'/key/'provenance.json')['original_pages']]
        if selected != scope['physical_pdf_pages']: raise ValueError('Fresh Gatheral ownership/scope mismatch')
        atomic_json(run/'inputs/scope.json', scope)
    atomic_json(run / 'inputs/manifest.json', files_manifest(run / 'inputs'))
    binding = {'version': 'simple-chapter-continuous-v1', 'code': code_hashes(),
               'timing_policy': 'manual_only',
               'native_preparation': str(native), 'native_manifest_sha256': sha(native / 'manifest.json'),
               'inputs_manifest_sha256': sha(run / 'inputs/manifest.json'),
               'prior_experiment': str(PRIOR), 'lineage': 'new user-authorized design; prior attempts unchanged, not inherited or replayed',
               'limits': dict(runtime.LIMITS, additional_per_task=0, wall_seconds=None), 'model': protocol.MODEL,
               'endpoint': protocol.BASE_URL, 'max_tokens': CONVERSION_MAX_TOKENS,
               'review_max_tokens': 131072, 'stream': True,
               'request_timeout': None, 'connection_timeout': 10,
               'compiler_policy': {'standard_packages': compiler_environment.STANDARD, 'automatic_recovery': 'one approved dependency update per version'},
               'sampling_and_reasoning': 'omitted; server defaults, effective Open WebUI settings unknown',
               'gate': 'Gatheral 1 completes normally with an available draft; Klebaner is independent; not fidelity certification'}
    if reference:
        binding.update(version=chapter_sources.VERSION, chapter_contract=chapter_sources.VERSION,
                       secondary_sources=source_identities, schedule_policy=FRESH_SCHEDULE, scope=scope,
                       preparation_reference=str(reference),
                       reference_records={n: sha(reference/n) for n in ('binding.json', 'state.json', 'inputs/manifest.json')},
                       previous_experiment_calls=len(previous['calls']), inherited_calls=0,
                       lineage='User-authorized fresh Gatheral experiment; reuse extraction caches only. Prior calls/drafts remain in original runs, not replayed as results or inherited into this new experiment.',
                       gate=None)
    atomic_json(run / 'binding.json', binding)
    tasks = [{'id': k + '/' + phase, 'key': k, 'phase': phase, 'status': 'pending'}
             for k in keys for phase in ('convert', 'review')]
    state = {'status': 'prepared_offline', 'first_dispatch': None, 'calls': [], 'tasks': tasks,
             'timing_policy': 'manual_only',
             'binding_sha256': fingerprint(binding), 'connection_failures': 0,
             'compile_unavailable': None, 'acceptance': 'UNACCEPTED'}
    if reference:
        state.update(chapter_contract=chapter_sources.VERSION, schedule_policy=FRESH_SCHEDULE,
                     accuracy={}, accuracy_evidence={})
    for key in keys:
        remember_version(run, state, key, 'mineru', protocol.document((run / 'inputs' / key / 'source.tex').read_text()),
                         origin={'exact_source': 'inputs/' + key + '/source.tex', 'wrapper': 'deterministic template; raw source unchanged'})
    runtime.save(run, state); report(run, state)
    atomic_json(POINTER, {'run': str(run)})
    return run


def recorded_evidence(run):
    """Verify saved evidence under its recorded binding, without claiming current code ran it."""
    binding = read_json(run / 'binding.json'); state = read_json(run / 'state.json')
    if state['binding_sha256'] != fingerprint(binding):
        raise runtime.Fatal('Changed recorded binding')
    verify_seal(run / 'inputs', binding['inputs_manifest_sha256'])
    if binding.get('recovery_manifest_sha256'):
        verify_seal(run / 'recovery', binding['recovery_manifest_sha256'])
    if binding.get('inherited_manifest_sha256'):
        verify_seal(run / 'inherited', binding['inherited_manifest_sha256'])
    for call in state['calls']:
        origin = Path(call['inherited_from']) if call.get('inherited_from') else run
        if call.get('seal'): verify_seal(origin / 'calls' / call['id'], call['seal'])
    for task in state['tasks']:
        if task.get('output') and sha(run / task['output']) != task['output_sha256']:
            raise runtime.Fatal('Changed generated output')
    for versions in state.get('versions', {}).values():
        for version in versions.values():
            if sha(run / version['path']) != version['sha256']: raise runtime.Fatal('Changed saved chapter version')
    for name, digest in state.get('accuracy_evidence', {}).items():
        if sha(run / name) != digest: raise runtime.Fatal('Changed accuracy-note evidence: ' + name)
    return binding, state


def verify(run):
    binding, state = recorded_evidence(run)
    if binding['code'] != code_hashes():
        raise runtime.Fatal('Changed code/binding; do not reseal or reset this experiment')
    if binding.get('timing_policy') != state.get('timing_policy'):
        raise runtime.Fatal('Changed sealed timing policy')
    if binding.get('chapter_contract') != state.get('chapter_contract'):
        raise runtime.Fatal('Changed chapter request contract')
    if binding.get('schedule_policy') != state.get('schedule_policy'):
        raise runtime.Fatal('Changed sealed chapter schedule policy')
    if binding.get('schedule_policy') == FRESH_SCHEDULE:
        expected = [(k+'/'+phase, k, phase) for k in binding['scope']['keys'] for phase in ('convert', 'review')]
        if [(t['id'], t['key'], t['phase']) for t in state['tasks']] != expected:
            raise runtime.Fatal('Changed fresh Gatheral task scope/order')
        reference = Path(binding['preparation_reference'])
        for name, digest in binding['reference_records'].items():
            if sha(reference/name) != digest: raise runtime.Fatal('Changed extraction-cache reference evidence: ' + name)
    if state.get('compiler_environment'):
        environment = state['compiler_environment']; verify_seal(run / environment['path'], environment['seal'])
    parent = binding.get('parent_run')
    if parent:
        for name, digest in binding['parent_records'].items():
            if sha(Path(parent) / name) != digest:
                raise runtime.Fatal('Changed linked parent evidence: ' + name)
    return binding, state


def initialize_linked(parent):
    """Explicit changed-allowance experiment; retain old calls and original wall deadline."""
    parent = Path(parent).resolve(); previous_binding, previous = recorded_evidence(parent)
    if previous['status'] in ('running', 'prepared_offline') or any(c['status'] == 'in_progress' for c in previous['calls']):
        raise ValueError('Link only stopped, finalized evidence')
    if runtime.remaining(previous) <= 0:
        raise ValueError('Original eight-hour deadline expired; explicit extension required')
    run = runtime.inputs.new_path('simple-chapter-glm-trial'); run.mkdir()
    shutil.copytree(parent / 'inputs', run / 'inputs')
    changes = []
    for key in KEYS:
        folder = run / 'inputs' / key
        old = read_json(folder / 'conversion-request.json')
        new = request((folder / 'source.tex').read_text())
        if old['max_tokens'] == new['max_tokens']:
            raise ValueError('No changed allowance; do not prepare an identical retry')
        if {k: v for k, v in new.items() if k != 'max_tokens'} != {k: v for k, v in old.items() if k != 'max_tokens'}:
            raise ValueError('Request change beyond output allowance: ' + key)
        atomic_json(folder / 'conversion-request.json', new)
        atomic_json(folder / 'budget.json', protocol.budget(new))
        changes.append({'chapter': key, 'old_max_tokens': old['max_tokens'], 'new_max_tokens': new['max_tokens'],
                        'source_sha256': sha(folder / 'source.tex'), 'only_request_change': 'max_tokens'})
    (run / 'inputs/manifest.json').unlink()  # Only the new copy; never alter the parent seal.
    atomic_json(run / 'inputs/manifest.json', files_manifest(run / 'inputs'))
    binding = {**previous_binding, 'version': 'simple-whole-chapter-131k-v1', 'code': code_hashes(),
               'inputs_manifest_sha256': sha(run / 'inputs/manifest.json'),
               'max_tokens': CONVERSION_MAX_TOKENS, 'review_max_tokens': REVIEW_MAX_TOKENS,
               'parent_run': str(parent),
               'parent_records': {n: sha(parent / n) for n in ('binding.json', 'state.json', 'inputs/manifest.json')},
               'lineage': 'explicit output-allowance comparison; inherited calls remain under original code',
               'known_openwebui_setting': {'max_tokens': 131072},
               'inherited_calls': len(previous['calls']), 'inherited_first_dispatch': previous['first_dispatch']}
    atomic_json(run / 'binding.json', binding)
    inherited = [{**c, 'parent': 'inherited/' + c['parent'], 'original_parent': c['parent'],
                  'inherited_from': c.get('inherited_from', str(parent))} for c in previous['calls']]
    state = {'status': 'prepared_linked_offline', 'first_dispatch': previous['first_dispatch'], 'calls': inherited,
             'tasks': [{'id': k + '/' + p, 'key': k, 'phase': p, 'status': 'pending'} for p in ('convert', 'review') for k in KEYS],
             'binding_sha256': fingerprint(binding), 'connection_failures': 0, 'compile_unavailable': None,
             'acceptance': 'UNACCEPTED'}
    atomic_json(run / 'allowance-change.json', {'parent': str(parent), 'requests': changes,
                'prompt_and_sources': 'unchanged', 'sampling_and_reasoning': 'unchanged; omitted',
                'review_max_tokens': REVIEW_MAX_TOKENS, 'timeout_seconds': protocol.TIMEOUT,
                'overall_budget': 'original deadline and consumed calls retained'})
    runtime.save(run, state); report(run, state)
    atomic_json(POINTER, {'run': str(run)})
    return run


def initialize_continuation(parent, recover_call):
    """Link unchanged requests and consumed budgets; recover one saved final answer."""
    parent = Path(parent).resolve(); old_binding, previous = recorded_evidence(parent)
    if (previous['status'] in ('running', 'prepared_offline', 'prepared_linked_offline')
            or any(c['status'] == 'in_progress' for c in previous['calls'])
            or any(t['status'] == 'in_progress' for t in previous['tasks'])):
        raise ValueError('Continuation requires stopped, finalized evidence')
    if runtime.remaining(previous) <= 0:
        raise ValueError('Original eight-hour deadline expired; explicit authorized time extension required, not a budget reset')
    selected = [t for t in previous['tasks'] if t.get('call') == recover_call and t['phase'] == 'convert']
    if len(selected) != 1 or selected[0]['status'] != 'complete_response':
        raise ValueError('Recovery requires one normally completed conversion, never a truncated response')
    call = next(c for c in previous['calls'] if c['id'] == recover_call)
    if call.get('metadata', {}).get('finish_reason') != 'stop' or call['metadata'].get('actual_model') != protocol.MODEL or not call.get('seal'):
        raise ValueError('Recovery requires sealed stop/identity evidence')
    origin = Path(call.get('inherited_from', parent))
    raw = origin / 'calls' / recover_call / 'content.txt'; answer = raw.read_text(encoding='utf-8')
    draft, extraction = extract_document(answer)
    if draft is None or not draft.strip(): raise ValueError('Saved response cannot be extracted unambiguously')
    for key in KEYS:
        folder = parent / 'inputs' / key
        if read_json(folder / 'conversion-request.json') != request((folder / 'source.tex').read_text()):
            raise ValueError('Continuation would change conversion request: ' + key)
    if old_binding.get('review_max_tokens') != REVIEW_MAX_TOKENS:
        raise ValueError('Continuation would change review allowance')
    run = runtime.inputs.new_path('simple-chapter-glm-trial'); run.mkdir()
    shutil.copytree(parent / 'inputs', run / 'inputs')
    state = copy.deepcopy(previous)
    state.update(status='prepared_linked_offline', connection_failures=0, compile_unavailable=None)
    state.pop('stop_reason', None)
    state['calls'] = [{**c, 'inherited_from': c.get('inherited_from', str(parent))} for c in previous['calls']]
    for task in state['tasks']:
        if task.get('output'):
            target = run / 'inherited' / task['output']; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(parent / task['output'], target)
            task['output'] = str(target.relative_to(run))
        if task['status'] != 'pending': task['inherited_from'] = str(parent)
    task = next(t for t in state['tasks'] if t['id'] == selected[0]['id'])
    original = copy.deepcopy(selected[0])
    for field in ('compilation', 'error', 'output', 'output_sha256'): task.pop(field, None)
    folder = run / 'recovery' / recover_call
    save_conversion(run, task, answer, folder)
    assets = read_json(run / 'inputs' / task['key'] / 'assets.json')
    task['document_observations'] = document_observations(draft, (run / 'inputs' / task['key'] / 'source.tex').read_text(), assets)
    task['recovered_from_call'] = recover_call
    task['compilation'] = {'status': 'not_attempted', 'reason': 'Recovered exact document; separate compiler check pending'}
    atomic_json(folder / 'provenance.json', {'parent_run': str(parent), 'call_origin': str(origin),
                'call': recover_call, 'call_seal': call['seal'], 'source_answer_sha256': sha(raw),
                'original_task': original, 'recovery': extraction, 'model_calls_made': 0,
                'semantic_changes': 'none; existing model corrections remain unaccepted and require review'})
    atomic_json(run / 'recovery/manifest.json', files_manifest(run / 'recovery'))
    for review in state['tasks']:
        if review['phase'] == 'review' and review['status'] == 'pending':
            conversion = next(t for t in state['tasks'] if t['id'] == review['key'] + '/convert')
            if conversion['status'] not in ('pending', 'complete_response'):
                review.update(status='unavailable', error='Conversion incomplete; preserved for separate investigation')
    binding = {**old_binding, 'version': 'simple-whole-chapter-recovery-v1', 'code': code_hashes(),
               'parent_run': str(parent),
               'parent_records': {n: sha(parent / n) for n in ('binding.json', 'state.json', 'inputs/manifest.json')},
               'recovery_manifest_sha256': sha(run / 'recovery/manifest.json'),
               'lineage': 'saved-response envelope recovery and continuation; inherited calls retain original code provenance',
               'inherited_calls': len(previous['calls']), 'inherited_first_dispatch': previous['first_dispatch'],
               'gate': 'Gatheral 1 completes normally with an available draft; Klebaner is independent; not fidelity certification'}
    atomic_json(run / 'binding.json', binding); state['binding_sha256'] = fingerprint(binding)
    runtime.save(run, state); report(run, state)
    atomic_json(POINTER, {'run': str(run)})
    return run


def review_order(tasks):
    """Review existing complete drafts first, then each new draft immediately."""
    by_id = {t['id']: t for t in tasks}; ordered = []
    for key in KEYS:
        conversion = by_id[key + '/convert']; review = by_id[key + '/review']
        if conversion['status'] == 'complete_response' and conversion.get('draft_available', True) and review['status'] == 'pending':
            ordered.append(review)
        elif conversion['status'] not in ('pending', 'complete_response') and review['status'] == 'pending':
            review.update(status='unavailable', error='Original conversion failed/incomplete; no automatic replay')
    for key in KEYS:
        for phase in ('convert', 'review'):
            task = by_id[key + '/' + phase]
            if task not in ordered: ordered.append(task)
    return ordered


def remember_version(run, state, key, label, text, *, origin=None):
    folder = run / 'versions' / key / label; folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'document.tex'
    if path.exists() and path.read_text() != text: raise runtime.Fatal('Refusing to overwrite an earlier chapter version')
    if not path.exists(): path.write_text(text, encoding='utf-8')
    version = state.setdefault('versions', {}).setdefault(key, {}).setdefault(label, {
        'path': str(path.relative_to(run)), 'sha256': sha(path), 'origin': origin,
        'acceptance': 'UNACCEPTED', 'compilation': {'status': 'not_attempted'}})
    return version


def initialize_policy_continuation(parent, *, two_sources=False):
    """Explicit new policy/binding, never a reset or mutation of expired evidence."""
    parent = Path(parent).resolve(); old_binding, previous = recorded_evidence(parent)
    if previous['status'] == 'running' or any(c['status'] == 'in_progress' for c in previous['calls']):
        raise ValueError('Parent must have exited; interrupted calls need separate investigation, not replay')
    run = runtime.inputs.new_path('simple-chapter-glm-trial'); run.mkdir()
    shutil.copytree(parent / 'inputs', run / 'inputs')
    for name in ('chapters', 'recovery', 'inherited', 'versions'):
        if (parent / name).exists(): shutil.copytree(parent / name, run / 'inherited' / name)
    (run / 'inherited').mkdir(exist_ok=True)
    atomic_json(run / 'inherited/manifest.json', files_manifest(run / 'inherited'))
    state = copy.deepcopy(previous)
    state.update(status='prepared_linked_offline', timing_policy='manual_only', versions={},
                 connection_failures=0, compile_unavailable=None)
    state.pop('stop_reason', None); state.pop('compiler_environment', None)
    if two_sources:
        if own_calls(previous): raise ValueError('Two-source update expects the unlaunched prepared continuation; do not replay a live run')
        state['chapter_contract'] = chapter_sources.VERSION
        state['accuracy_evidence'] = {}; state['accuracy'] = {}
        source_identities = chapter_sources.prepare_secondary(run, ROOT, KEYS)
    state['calls'] = [{**c, 'inherited_from': c.get('inherited_from', str(parent))} for c in previous['calls']]
    changes = []
    for task in state['tasks']:
        for field in ('output', 'notes', 'raw_answer'):
            if task.get(field): task[field] = 'inherited/' + task[field]
        if task.get('compilation', {}).get('path'):
            task['compilation']['path'] = 'inherited/' + task['compilation']['path']
        if task['status'] != 'pending': task['inherited_from'] = str(parent)
        if task['phase'] == 'convert':
            folder = run / 'inputs' / task['key']; source = (folder / 'source.tex').read_text()
            old = read_json(folder / 'conversion-request.json')
            body = chapter_sources.request(source, (folder/'secondary.txt').read_text()) if two_sources else continuous_request(source)
            if not two_sources and (old['messages'] != body['messages'] or old['max_tokens'] != body['max_tokens']):
                raise ValueError('Unexpected source/prompt/conversion allowance change')
            atomic_json(folder / 'conversion-request.json', body)
            atomic_json(folder / 'budget.json', chapter_sources.budget_preview(body) if two_sources else protocol.budget(body))
            changes.append({'chapter': task['key'], 'source_sha256': sha(folder / 'source.tex'),
                            'conversion_request_change': 'meaning-focused prompt plus secondary extraction; primary unchanged' if two_sources else 'stream=true only'})
            remember_version(run, state, task['key'], 'mineru', protocol.document(source),
                             origin={'exact_source': str((folder / 'source.tex').relative_to(run)),
                                     'source_sha256': sha(folder / 'source.tex'), 'wrapper': 'deterministic template; raw source unchanged'})
            if task['status'] == 'complete_response' and task.get('output') and task.get('draft_available', True):
                text = (run / task['output']).read_text()
                version = remember_version(run, state, task['key'], 'first-glm', text,
                                           origin={'run': str(parent), 'call': task.get('call'),
                                                   'output': task['output'].removeprefix('inherited/'),
                                                   'cached_copy_path':task['output']})
                version['compilation'] = copy.deepcopy(task.get('compilation', {'status': 'not_attempted'}))
                if two_sources:
                    note_path=run/task['notes'] if task.get('notes') else None
                    notes=note_path.read_text() if note_path and note_path.is_file() else ''
                    initial, hashes=chapter_accuracy.save_initial(run,task['key'],notes,
                        status='captured' if notes.strip() else 'unavailable',
                        origin={'kind':'retrospectively assembled from conversion-time notes only',
                                'run':str(parent),'path':task['notes'].removeprefix('inherited/') if task.get('notes') else None,
                                'cached_copy_path':task.get('notes'),'sha256':sha(note_path) if note_path and note_path.is_file() else None,
                                'later_manual_audit_included':False})
                    state['accuracy_evidence'].update(hashes);state['accuracy'][task['key']]={'initial':'chapters/'+task['key']+'/accuracy-initial.json'}
                    review=chapter_sources.request(source,(folder/'secondary.txt').read_text(),text,chapter_accuracy.render(initial,provenance=False))
                    atomic_json(folder/'review-request.json',review)
                    atomic_json(folder/'review-budget.json',chapter_sources.budget_preview(review))
                else: atomic_json(folder / 'review-request.json', continuous_request(source, text))
    (run / 'inputs/manifest.json').unlink()
    atomic_json(run / 'inputs/manifest.json', files_manifest(run / 'inputs'))
    state['tasks'] = review_order(state['tasks'])
    binding = {**old_binding, 'version': 'simple-chapter-continuous-v1', 'code': code_hashes(),
               'timing_policy': 'manual_only', 'request_timeout': None, 'connection_timeout': 10,
               'limits': {'calls': runtime.LIMITS['calls'], 'additional_per_task': 0, 'wall_seconds': None},
               'review_max_tokens': 131072, 'stream': True,
               'compiler_policy': {'standard_packages': compiler_environment.STANDARD, 'automatic_recovery': 'one approved dependency update per version; no model repair'},
               'parent_run': str(parent),
               'parent_records': {n: sha(parent / n) for n in ('binding.json', 'state.json', 'inputs/manifest.json')},
               'inputs_manifest_sha256': sha(run / 'inputs/manifest.json'),
               'inherited_manifest_sha256': sha(run / 'inherited/manifest.json'),
               'inherited_calls': len(previous['calls']), 'inherited_first_dispatch': previous['first_dispatch'],
               'lineage': 'User-authorized removal of run/generation deadlines; review existing drafts then interleave conversion/review. Original attempts and accounting retained.'}
    binding.pop('recovery_manifest_sha256', None); binding.pop('compiler_image', None)
    if two_sources:
        binding.update(version=chapter_sources.VERSION,chapter_contract=chapter_sources.VERSION,
                       secondary_sources=source_identities,
                       lineage='Linked two-source meaning-focused requests and conservative accuracy-note continuity; eleven historical calls unchanged, no replay')
    atomic_json(run / 'binding.json', binding); state['binding_sha256'] = fingerprint(binding)
    atomic_json(run / 'policy-change.json', {'parent': str(parent), 'authorization': '26 October user controlling requirements supersede wall-clock cutoffs',
                'first_dispatch_preserved': previous['first_dispatch'], 'consumed_calls': len(previous['calls']),
                'prior_deadline_enforced': False, 'generation_deadline': None, 'connection_establishment_timeout_seconds': 10,
                'requests': changes, 'review_allowance': 131072, 'no_automatic_failed_task_retries': True,
                'two_sources':two_sources,'accuracy_notes':'conversion-time baseline only; later audit excluded' if two_sources else None})
    runtime.save(run, state); report(run, state); atomic_json(POINTER, {'run': str(run)})
    return run


def compile_version(run, state, key, label):
    version = state['versions'][key][label]
    if version.get('compilation', {}).get('status', '').startswith('passed'): return version['compilation']
    # Each explicit launch may retry an unavailable environment, never overwrite logs.
    if version.get('checked_under_current_environment') == state['compiler_environment']['image']:
        return version['compilation']
    assets = {n: run / 'inputs' / n for n in read_json(run / 'inputs' / key / 'assets.json')}
    folder = run / 'versions' / key / label / ('compilation-' + str(time.time_ns()))
    version.setdefault('compilation_history', []).append(copy.deepcopy(version['compilation']))
    version['compilation'] = compiler_environment.compile_saved(run, state, ROOT, (run / version['path']).read_text(), folder, assets)
    version['compilation']['path'] = str(folder.relative_to(run))
    version['checked_under_current_environment'] = state['compiler_environment']['image']
    runtime.save(run, state)
    return version['compilation']


def own_calls(state):
    return [c for c in state['calls'] if not c.get('inherited_from')]


def current():
    if not POINTER.is_file(): raise ValueError('No simple preparation; run prepare first')
    return Path(read_json(POINTER)['run'])


def compile_draft(run, state, task, text):
    folder = run / 'chapters' / task['key']; source = run / 'inputs' / task['key']
    assets = {n: run / 'inputs' / n for n in read_json(source / 'assets.json')}
    task['document_observations'] = document_observations(text, (source / 'source.tex').read_text(), assets)
    if state.get('timing_policy') == 'manual_only':
        remember_version(run, state, task['key'], 'first-glm', text, origin={'call': task.get('call')})
        compile_version(run, state, task['key'], 'mineru')
        task['compilation'] = compile_version(run, state, task['key'], 'first-glm')
        runtime.save(run, state); return
    if state['compile_unavailable'] or runtime.remaining(state) < 125:
        task['compilation'] = {'status': 'not_attempted', 'reason': state['compile_unavailable'] or 'Remaining wall budget too short'}
    else:
        try:
            destination = folder / ('compilation-' + str(time.time_ns()) if task.get('recovered_from_call') else 'compilation')
            task['compilation'] = tex_compile.compile_document(text, destination, image=protocol.IMAGE,
                                                              assets=assets, passes=2, template='model supplied complete document')
            task['compilation']['path'] = str(destination.relative_to(run))
        except (ValueError, OSError) as exc:
            task['compilation'] = {'status': 'adapter_configuration_failure', 'reason': str(exc)}
        if task['compilation']['status'] in ('unavailable', 'adapter_configuration_failure'):
            state['compile_unavailable'] = task['compilation'].get('reason', task['compilation']['status'])
    runtime.save(run, state)


def compile_recovered(run, state):
    """One separate check per operator launch when the sandbox could not compile."""
    for task in state['tasks']:
        if task.get('recovered_from_call') and task.get('compilation', {}).get('status') in ('not_attempted', 'unavailable'):
            task.setdefault('compilation_history', []).append(copy.deepcopy(task['compilation']))
            state['compile_unavailable'] = None
            compile_draft(run, state, task, (run / task['output']).read_text())


def save_accuracy_review(run, state, task, answer, info, *, complete, before, after=None):
    key=task['key']; index=state['accuracy'][key]
    initial=read_json(run/index['initial']); folder=run/'inputs'/key
    record,hashes=chapter_accuracy.save_review(run,key,initial,answer,info,complete=complete,before=before,after=after,
        sources=[(folder/'source.tex').read_text(),(folder/'secondary.txt').read_text()],
        origin={'call':task.get('call'),'technical_status':task['status']})
    state['accuracy_evidence'].update(hashes)
    index.update(post_critic='chapters/'+key+'/accuracy-post-critic.json',
                 notes_status=record['notes_status'],open_issues=record['open_issues'])
    task['accuracy_notes_status']=record['notes_status']; task['open_accuracy_issues']=len(record['open_issues'])
    runtime.save(run,state)


def task_once(run, state, task, client_factory=LocalClient):
    if task['status'] != 'pending': return
    meaning=state.get('chapter_contract') == chapter_sources.VERSION
    previous = [c for c in state['calls'] if c['parent'] == task['id']]
    if previous:
        task.update(status='unresolved_interruption', error='Saved attempt already exists; never automatically replay an uncertain completion')
        if meaning and task['phase']=='review' and not state['accuracy'][task['key']].get('post_critic'):
            conversion=next(t for t in state['tasks'] if t['id']==task['key']+'/convert')
            save_accuracy_review(run,state,task,'',{},complete=False,before=(run/conversion['output']).read_text())
        runtime.save(run, state); return
    source = (run / 'inputs' / task['key'] / 'source.tex').read_text()
    generated = None
    if task['phase'] == 'review':
        conversion = next(t for t in state['tasks'] if t['id'] == task['key'] + '/convert')
        if conversion['status'] != 'complete_response' or not conversion.get('output') or conversion.get('draft_available') is False:
            task.update(status='unavailable', error='No unambiguously extracted, normally completed nonempty conversion response')
            runtime.save(run, state); return
        generated = (run / conversion['output']).read_text()
        if state.get('timing_policy') == 'manual_only':
            compile_version(run, state, task['key'], 'mineru')
            conversion['compilation'] = compile_version(run, state, task['key'], 'first-glm')
    try:
        if meaning:
            notes=chapter_accuracy.render(read_json(run/state['accuracy'][task['key']]['initial']),provenance=False) if generated is not None else None
            body=chapter_sources.request(source,(run/'inputs'/task['key']/'secondary.txt').read_text(),generated,notes)
            folder=run/'chapters'/task['key'];folder.mkdir(parents=True,exist_ok=True)
            atomic_json(folder/(task['phase']+'-request.json'),body)
            atomic_json(folder/(task['phase']+'-budget.json'),chapter_sources.budget_preview(body))
            prepared=run/'inputs'/task['key']/('review-request.json' if generated is not None else 'conversion-request.json')
            if prepared.exists() and read_json(prepared)!=body:raise runtime.Fatal('Prepared two-source request changed')
        else: body = continuous_request(source, generated) if state.get('timing_policy') == 'manual_only' else request(source, generated)
        task.pop('error', None)
        task['status'] = 'in_progress'; runtime.save(run, state)
        text, call = runtime.invoke(run, state, task['id'], body, client_factory=client_factory)
    except protocol.ContextBudgetGap as exc:
        task.update(status='context_budget_gap',error=str(exc))
        if meaning and task['phase']=='review':save_accuracy_review(run,state,task,'',{},complete=False,before=generated)
        runtime.save(run,state);return
    except ValueError as exc:
        task.update(status='unavailable', error=str(exc)); runtime.save(run, state); return
    if text is None:
        task.update(status=call['failure_kind'], error=call['error'], call=call['id'])
        if meaning and task['phase']=='review':
            partial=run/'calls'/call['id']/'answer.txt'
            save_accuracy_review(run,state,task,partial.read_text() if partial.exists() else '',{},complete=False,before=generated)
        runtime.save(run, state)
        if call['failure_kind'] == 'operator_stop': raise runtime.StopRun('Operator stopped current request; partial evidence retained, no automatic replay')
        if state['connection_failures'] >= 2: raise runtime.StopRun('Repeated connection failures; no service change')
        return
    folder = run / 'chapters' / task['key']; folder.mkdir(parents=True, exist_ok=True)
    if task['phase'] == 'convert':
        task['call'] = call['id']
        output = save_conversion(run, task, text, folder, meaning=meaning)
        if meaning:
            extraction=read_json(folder/'extraction.json');notes,status=chapter_accuracy.outside_notes(text,extraction)
            initial,hashes=chapter_accuracy.save_initial(run,task['key'],notes,status=status,
                                origin={'call':call['id'],'kind':'conversion-time model notes'})
            state['accuracy_evidence'].update(hashes)
            state['accuracy'][task['key']]={'initial':str((folder/'accuracy-initial.json').relative_to(run))}
        runtime.save(run, state)
        if output is not None and task['status'] == 'complete_response': compile_draft(run, state, task, output)
        return
    if meaning:
        # A successful critic response and a supplied complete revision are distinct.
        (folder/'review.md').write_text(text,encoding='utf-8')
        task.update(status='complete_response',call=call['id'],output=str((folder/'review.md').relative_to(run)),
                    output_sha256=sha(folder/'review.md'),fidelity='not certified')
        revised,info=chapter_accuracy.envelope(text,extract_document)
        if revised is not None and chapter_accuracy.complete_document(revised):
            label='critic-revised-'+call['id']
            version=remember_version(run,state,task['key'],label,revised,origin={'call':call['id'],'extraction':info,
                          'kind':'working derivative; material corrections must be logged; not certified'})
            task['revised_tex']={'status':'supplied_unaccepted','version':label,'path':version['path']}
            state.setdefault('current_versions',{})[task['key']]=label
        else:
            revised=None
            state.setdefault('current_versions',{})[task['key']]='first-glm'
            task['revised_tex']={'status':'not_supplied' if info.get('status')!='ambiguous' else 'unavailable_ambiguous',
                                 'reason':'No unambiguous complete revised document; initial TeX retained'}
        save_accuracy_review(run,state,task,text,info,complete=True,before=generated,after=revised)
        runtime.save(run,state)
        if revised is not None:compile_version(run,state,task['key'],label)
        return
    name = 'generated.tex' if task['phase'] == 'convert' else 'review.md'
    # Exact final text remains in calls/. Only a single enclosing fence is unwrapped.
    output, unwrapped = protocol.unwrap(text)
    (folder / name).write_text(output)
    if not output.strip():
        task.update(status='empty_answer', call=call['id'], error='Final answer contains only an empty enclosing fence',
                    output=str((folder / name).relative_to(run)), output_sha256=sha(folder / name),
                    outer_fence_stripped=unwrapped)
        runtime.save(run, state); return
    task.update(status='complete_response', call=call['id'], output=str((folder / name).relative_to(run)),
                output_sha256=sha(folder / name), outer_fence_stripped=unwrapped,
                fidelity='not established; no block/output-marker contract')
    if task['phase'] == 'review' and state.get('timing_policy') == 'manual_only':
        task['revised_tex'] = {'status': 'not_supplied', 'reason': 'Critic returned findings; no separate complete revised document detected'}
        revised, extraction = extract_document(text)
        if revised is not None and all(s in without_comments(revised) for s in ('\\documentclass', '\\begin{document}', '\\end{document}')):
            label = 'critic-revised-' + call['id']
            version = remember_version(run, state, task['key'], label, revised,
                                       origin={'call': call['id'], 'extraction': extraction, 'status': 'unaccepted; never replaces first draft'})
            task['revised_tex'] = {'status': 'supplied_unaccepted', 'version': label, 'path': version['path']}
            compile_version(run, state, task['key'], label)
        elif extraction['status'] == 'ambiguous':
            task['revised_tex'] = {'status': 'unavailable_ambiguous', 'reason': extraction['reason'], 'raw_review_preserved': True}
    runtime.save(run, state)
    if task['phase'] == 'convert': compile_draft(run, state, task, output)


def run_schedule(run, state, client_factory=LocalClient):
    for task in state['tasks']:
        if task['status'] == 'in_progress': task['status'] = 'pending'
        if task['status'] != 'pending': continue
        if (run / 'pause.json').exists(): raise runtime.StopRun('Operator pause after current call')
        if (run / 'stop.json').exists(): raise runtime.StopRun('Operator stop requested')
        if runtime.remaining(state) <= 0: raise runtime.StopRun('Eight-hour deadline expired; no automatic extension')
        gate = next((t for t in state['tasks'] if t['id'] == 'gatheral-01/convert'), None)
        if (state.get('schedule_policy') != FRESH_SCHEDULE and
                task['key'].startswith('gatheral-') and task['id'] != 'gatheral-01/convert' and gate
                and (gate['status'] != 'complete_response' or gate.get('draft_available') is False)):
            raise runtime.StopRun('Gatheral 1 conversion unavailable; Klebaner status is independent')
        # Existing InputGuard and code fingerprints remain in force at every task.
        verify(run)
        task_once(run, state, task, client_factory)
        report(run, state)
    state['status'] = 'finished_with_gaps' if any(t['status'] != 'complete_response' for t in state['tasks']) else 'responses_completed_unaccepted'


def report(run, state):
    totals = {'calls': len(state['calls']), 'request_seconds': sum(c.get('elapsed_seconds', 0) for c in state['calls'])}
    for field in ('prompt_tokens', 'completion_tokens'):
        totals[field] = sum(c.get('metadata', {}).get('usage', {}).get(field, 0) for c in state['calls'])
    totals['reasoning_tokens_reported'] = sum(c.get('metadata', {}).get('usage', {}).get('completion_tokens_details', {}).get('reasoning_tokens', 0) for c in state['calls'])
    totals['missing_usage_calls'] = [c['id'] for c in state['calls'] if not c.get('metadata', {}).get('usage')]
    measurements = [call_measurements(run, c) for c in state['calls']]
    manual = state.get('timing_policy') == 'manual_only'
    deadline = state['first_dispatch'] + runtime.LIMITS['wall_seconds'] if state['first_dispatch'] is not None and not manual else None
    continuation = ''
    if (run / 'binding.json').is_file():
        binding = read_json(run / 'binding.json')
        if binding.get('parent_run'):
            continuation = ('<p>Linked parent: ' + html.escape(binding['parent_run']) +
                            '. Inherited calls retain their original code provenance. New calls here: ' + str(len(own_calls(state))) +
                            '. Saved-response recovery makes no inference call; notes and original answers remain separate.</p>')
        if binding.get('schedule_policy') == FRESH_SCHEDULE:
            continuation = ('<p>Fresh Gatheral experiment: Chapters 1–11, postscript and bibliography, physical PDF pages 32–198 (167 pages). '
                            'Front matter 1–31, blank 199 and index 200–210 are outside this run; this is not complete-book coverage. '
                            'Each new conversion is followed immediately by its critic. No Klebaner or historical drafts/calls are inherited. '
                            'Prior experiment evidence is preserved separately.</p><p><a href="inputs/scope.json">Exact scope and exclusions</a></p>')
    atomic_json(run / 'summary.json', {'status': state['status'], 'totals': totals, 'tasks': state['tasks'],
                                      'calls': measurements,
                                      'deadline_epoch': deadline, 'remaining_wall_seconds_at_report': None if manual else runtime.remaining(state),
                                      'timing_policy': state.get('timing_policy', 'legacy_eight_hours'),
                                      'versions': state.get('versions', {}),
                                      'accuracy': state.get('accuracy', {}),
                                      'chapter_contract': state.get('chapter_contract', 'legacy-simple'),
                                      'fidelity': 'unverified; response completion and compilation are separate'})
    rows = []
    for t in state['tasks']:
        link = f'<a href="{html.escape(t["output"])}">output</a>' if t.get('output') else ''
        if state.get('chapter_contract') == chapter_sources.VERSION:
            for filename,label in [('source.tex','MinerU source'),('secondary.txt','native PDF text'),
                                   ('review-request.json' if t['phase']=='review' else 'conversion-request.json','prepared request')]:
                p=run/'inputs'/t['key']/filename
                if p.is_file():link+=f' <a href="{html.escape(str(p.relative_to(run)))}">{label}</a>'
        for field, label in (('raw_answer', 'raw answer'), ('notes', 'conversion notes')):
            if t.get(field): link += f' <a href="{html.escape(t[field])}">{label}</a>'
        if t.get('compilation', {}).get('path'):
            filename = 'compilation.json' if 'attempts' in t['compilation'] else 'result.json'
            link += f' <a href="{html.escape(t["compilation"]["path"])}/{filename}">compiler record</a>'
        if t.get('revised_tex', {}).get('path'):
            link += f' <a href="{html.escape(t["revised_tex"]["path"])}">separate unaccepted revision</a>'
        if state.get('accuracy',{}).get(t['key']):
            for filename,label in [('accuracy-initial.md','initial accuracy notes'),('accuracy-post-critic.md','post-critic notes'),
                                   ('material-changes.md','material changes'),('revised-tex-status.md','revision status')]:
                p=run/'chapters'/t['key']/filename
                if p.is_file():link+=f' <a href="{html.escape(str(p.relative_to(run)))}">{label}</a>'
        rows.append('<tr>' + ''.join('<td>' + html.escape(str(v)) + '</td>' for v in
                    (t['id'], t['status'], t.get('compilation', {}).get('status', 'not_attempted'), t.get('error', t.get('extraction_error', '')),
                     {'document':t.get('document_observations', {}),'accuracy_notes':t.get('accuracy_notes_status'),
                      'open_issues':t.get('open_accuracy_issues')})) + '<td>' + link + '</td></tr>')
    (run / 'report.html').write_text('<!doctype html><meta charset="utf-8"><h1>Simple chapter experiment</h1>'
        '<p>Saved MinerU and cached native PDF text (when recorded) → regular GLM complete files → immediate separate text critic. UNACCEPTED. '
        'Normal completion is not content fidelity or mathematical verification. Compilation is a separate check. '
        'No automatic corrections, block-output requirements or repeated requests.</p><p>' + html.escape(state['status']) +
        '</p>' + continuation + '<p><a href="summary.json">Summary, warnings, per-call finish reasons, requested allowances and token usage</a></p><table border="1"><tr><th>Task</th>'
        '<th>Response</th><th>Compilation</th><th>Failure</th><th>Document observations</th><th>Output</th></tr>' + ''.join(rows) + '</table>')


def call_measurements(run, call):
    origin = Path(call['inherited_from']) if call.get('inherited_from') else run
    folder = origin / 'calls' / call['id']; meta = call.get('metadata', {})
    usage = meta.get('usage', {}); details = usage.get('completion_tokens_details', {})
    completion = usage.get('completion_tokens'); reasoning = details.get('reasoning_tokens')
    asked = read_json(folder / 'request.json')['max_tokens'] if (folder / 'request.json').is_file() else None
    finish = meta.get('finish_reason')
    observation = 'not exercised/unknown; HTTP success does not prove allowance honoured'
    if finish == 'length' and asked is not None and completion is not None:
        observation = 'reported requested ceiling reached' if completion == asked else 'length before/different from requested ceiling; investigate, no automatic retry'
    result = {'id': call['id'], 'parent': call['parent'], 'inherited_from': call.get('inherited_from'),
              'requested_max_tokens': asked, 'finish_reason': finish, 'actual_model': meta.get('actual_model'),
              'prompt_tokens': usage.get('prompt_tokens'), 'completion_tokens': completion, 'reasoning_tokens': reasoning,
              'final_answer_tokens_reported': details.get('text_tokens'),
              'non_reasoning_completion_tokens_derived': completion - reasoning if completion is not None and reasoning is not None else None,
              'token_note': 'completion minus reasoning may include delimiters; not an exact final-text token count',
              'elapsed_seconds': call.get('elapsed_seconds'), 'allowance_observation': observation}
    for raw in folder.glob('attempts/*/response.raw'):
        try:
            assembled = raw.parent / 'response.assembled.json'
            value = read_json(assembled if assembled.exists() else raw); message = value['choices'][0]['message']
            result.update(final_answer_characters=len(message.get('content') or ''),
                          reasoning_characters=len(message.get('reasoning_content') or message.get('reasoning') or ''),
                          server_timings=value.get('tensorfold', {}))
        except (ValueError, KeyError, TypeError, IndexError): pass
    return result


def bundle(run):
    _, state = verify(run); report(run, state)
    out = ROOT / 'results' / (run.name.replace('trial', 'inspection') + '-' + str(time.time_ns()) + '.zip')
    with zipfile.ZipFile(out, 'x', zipfile.ZIP_DEFLATED) as z:
        for name in ('report.html', 'summary.json', 'binding.json', 'state.json', 'policy-change.json', 'offline-validation.json'):
            if (run / name).is_file(): z.write(run / name, name)
        for directory in ('chapters', 'inputs', 'recovery', 'inherited', 'versions', 'compiler-environments'):
            for f in (run / directory).rglob('*'):
                if f.is_file(): z.write(f, str(f.relative_to(run)))
        for call in state['calls']:
            for name in ('outcome.json', 'final-channel.raw.txt', 'reasoning.txt', 'request.json', 'settings.json', 'response-metadata.json'):
                f = run / 'calls' / call['id'] / name
                if f.is_file(): z.write(f, str(f.relative_to(run)))
        z.writestr('README.txt', 'UNACCEPTED experimental responses; not verified full-book output.\n'
                   'Assets appear once in inputs/assets. To compile a chapter, copy its generated.tex alongside inputs/assets.\n'
                   'Exact raw HTTP responses/reasoning remain in the separate run. Sources/provenance are in inputs.\n')
    atomic_json(run / 'latest-bundle.json', {'path': str(out), 'bytes': out.stat().st_size, 'sha256': sha(out)})
    return out


def execute(run, resume=False, client_factory=LocalClient):
    with writer_lock(ROOT):
        _, state = verify(run)
        if own_calls(state) and not resume: raise runtime.StopRun('Use resume; no budget reset')
        if runtime.remaining(state) <= 0: raise runtime.StopRun('Eight-hour deadline expired')
        runtime.check_other_jobs()
        if resume and (run / 'pause.json').exists(): (run / 'pause.json').unlink()
        if resume and (run / 'stop.json').exists(): (run / 'stop.json').unlink()
        state['status'] = 'running'; state.pop('stop_reason', None); runtime.save(run, state)
        try:
            if state.get('timing_policy') == 'manual_only': compiler_environment.ensure(run, state, ROOT)
            else: compile_recovered(run, state)
            runtime.readiness(run, state, client_factory)
            run_schedule(run, state, client_factory)
        except (RuntimeError, ProbeError, ValueError, KeyboardInterrupt) as exc:
            state.update(status='stopped', stop_reason=str(exc) or 'Interrupted; uncertain attempts will not be replayed')
        finally:
            runtime.save(run, state); report(run, state)
            print('Inspection ZIP:', bundle(run), flush=True)
        return 0 if state['status'] == 'responses_completed_unaccepted' else 2


def worker(run, launch, resume):
    with (launch / 'terminal.log').open('a', buffering=1) as log:
        os.dup2(log.fileno(), 1); os.dup2(log.fileno(), 2)
        result = 2
        try:
            print('Book: Gatheral. Phase: tests → compiler environment → streamed readiness → recorded chapter schedule. No elapsed-time cutoff.', flush=True)
            stamp = ROOT / 'results/simple-chapter-tests-passed.json'
            checks = {'code': code_hashes(), 'tests': [x for x in runtime.test_hashes() if not x['path'].endswith('.pyc')]}
            if not stamp.is_file() or read_json(stamp) != checks:
                env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}; env.pop('PDF2TEX_COMPILER_IMAGE', None)
                result = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=ROOT, env=env).returncode
                if result: raise runtime.StopRun('Tests failed; no model calls dispatched')
                atomic_json(stamp, checks)
            result = execute(run, resume)
        except Exception as exc:
            print('ERROR:', str(exc), 'No service or model substitution.', flush=True); result = 2
        finally:
            atomic_json(launch / 'exit.json', {'exit_status': result, 'at': runtime.now()})
    return result


def persistent(mode):
    run = current(); _, state = verify(run)
    if mode == 'run' and own_calls(state): raise ValueError('Use resume, not a new run')
    if runtime.remaining(state) <= 0: raise ValueError('Deadline expired; no new readiness')
    # Brief project lock refuses the old runner/any other live writer before launch.
    with writer_lock(ROOT): runtime.check_other_jobs()
    if not shutil.which('tmux'): raise ValueError('tmux unavailable')
    if subprocess.run(['tmux', 'has-session', '-t', SESSION], capture_output=True).returncode == 0:
        raise ValueError('Simple chapter session already exists')
    launch = run / 'launches' / str(time.time_ns()); launch.mkdir(parents=True)
    client = LocalClient(protocol.BASE_URL, protocol.MODEL, purpose='chapter', timeout=10)
    client.discover_model(launch / 'endpoint-check')
    health, _ = client.chapter_health(launch / 'endpoint-check'); protocol.health_capacity(health)
    cmd = [str(ROOT / '.venv-control/bin/python'), '-B', '-u', '-m', 'scripts.simple_chapter_glm',
           'worker', '--run', str(run), '--launch', str(launch)]
    if mode == 'resume': cmd.append('--resume')
    subprocess.run(['tmux', 'new-session', '-d', '-s', SESSION,
                    'cd ' + shlex.quote(str(ROOT)) + ' && ' + shlex.join(cmd)], check=True)
    pending = next((t['id'] for t in state['tasks'] if t['status'] == 'pending'), 'none')
    print(f'Book: Gatheral. Next task: {pending}. Model: {protocol.MODEL}.\n'
          f'Persistent session: {SESSION}. Phase: tests, then captured readiness; inference not yet confirmed.\n'
          f'Run: {run}\nReport: {run / "report.html"}\nLog: {launch / "terminal.log"}\nStatus: bash scripts/run-simple-chapter-glm.sh status')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'run', 'resume', 'worker', 'status', 'pause', 'stop', 'bundle', 'compile-recovered'))
    parser.add_argument('--run', type=Path); parser.add_argument('--launch', type=Path)
    parser.add_argument('--parent', type=Path, help='Explicit stopped evidence for a changed-output-allowance preparation')
    parser.add_argument('--continue-from', type=Path, help='Stopped parent for saved-response recovery and unchanged-request continuation')
    parser.add_argument('--recover-call', help='Normally completed saved conversion call to extract without inference')
    parser.add_argument('--policy-parent', type=Path, help='Explicit stopped parent for the user-authorized no-deadline, immediate-critic continuation')
    parser.add_argument('--two-source-parent',type=Path,help='Unlaunched preparation for linked two-source meaning-focused requests')
    parser.add_argument('--fresh-gatheral-from', type=Path, help='Fresh Gatheral-only conversion/critic pairs, reusing this sealed extraction cache without prior GLM drafts or calls')
    parser.add_argument('--resume', action='store_true'); args = parser.parse_args(argv)
    if args.fresh_gatheral_from:
        if args.action != 'prepare' or any((args.parent, args.continue_from, args.recover_call, args.policy_parent, args.two_source_parent)):
            raise ValueError('Use prepare --fresh-gatheral-from CACHE_RUN')
        with writer_lock(ROOT): print(initialize(fresh_gatheral_from=args.fresh_gatheral_from))
        return 0
    if args.two_source_parent:
        if args.action!='prepare' or args.parent or args.continue_from or args.policy_parent:raise ValueError('Use prepare --two-source-parent PARENT')
        with writer_lock(ROOT):print(initialize_policy_continuation(args.two_source_parent,two_sources=True))
        return 0
    if args.policy_parent:
        if args.action != 'prepare' or args.parent or args.continue_from: raise ValueError('Use prepare --policy-parent PARENT')
        with writer_lock(ROOT): print(initialize_policy_continuation(args.policy_parent))
        return 0
    if args.continue_from or args.recover_call:
        if args.action != 'prepare' or not args.continue_from or not args.recover_call or args.parent:
            raise ValueError('Use prepare --continue-from PARENT --recover-call CALL')
        with writer_lock(ROOT): print(initialize_continuation(args.continue_from, args.recover_call))
        return 0
    if args.parent:
        if args.action != 'prepare': raise ValueError('--parent is only valid for explicit offline preparation')
        with writer_lock(ROOT): print(initialize_linked(args.parent))
        return 0
    if args.action in ('prepare', 'run') and not POINTER.exists():
        with writer_lock(ROOT): initialize()
    if args.action == 'prepare': verify(current()); print(current()); return 0
    if args.action in ('run', 'resume'): persistent(args.action); return 0
    run = args.run if args.run else current()
    if args.action == 'worker': return worker(run, args.launch, args.resume)
    if args.action == 'stop':
        atomic_json(run / 'stop.json', {'at': runtime.now()}); print('Stop requested: interrupt current stream, preserve partial evidence; GLM service stays running.')
    elif args.action == 'pause':
        atomic_json(run / 'pause.json', {'at': runtime.now()}); print('Pause requested after current call; GLM stays running.')
    elif args.action == 'status':
        state = read_json(run / 'state.json'); print('Run:', run, '\nStatus:', state['status'], '\nCalls:', len(state['calls']), '/ 80')
        print('Timing: no overall or generation deadline; connect timeout 10s' if state.get('timing_policy') == 'manual_only' else 'Remaining wall seconds: ' + str(round(runtime.remaining(state))))
        print('Stop reason:', state.get('stop_reason', ''))
        for t in state['tasks']: print(t['id'], t['status'], t.get('error', ''), t.get('compilation', {}).get('status', ''))
        for p in sorted((run / 'launches').glob('*/exit.json')): print('Launch outcome:', p, read_json(p))
        if (run / 'latest-bundle.json').exists(): print('Inspection ZIP:', read_json(run / 'latest-bundle.json')['path'])
    elif args.action == 'bundle':
        with writer_lock(ROOT): print(bundle(run))
    elif args.action == 'compile-recovered':
        with writer_lock(ROOT):
            _, state = verify(run); compile_recovered(run, state); report(run, state)
            print('Saved recovery compiler check; no inference. See', run / 'report.html')
    return 0


if __name__ == '__main__':
    try: raise SystemExit(main())
    except (RuntimeError, ValueError, ProbeError, OSError, subprocess.SubprocessError) as exc:
        print('ERROR:', str(exc), 'No model substitution or service change.', file=sys.stderr); raise SystemExit(2)
