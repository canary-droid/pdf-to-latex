#!/usr/bin/env python3
"""Saved-output finalisation only: no model transport, readiness or queue launch."""
import argparse
import copy
import difflib
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scripts'))
import book_completion as completion
from probe import book_finalisation as repairs, book_completion as scope
from probe import chapter_editorial as editorial, chapter_accuracy, chapter_sources, compiler_environment
from probe.common import read_json, atomic_json, sha, fingerprint, files_manifest, writer_lock
from probe.experiment import InputGuard, verify_seal

PARENT = ROOT / 'runs/book-completion-20261101T095516Z-b24cfa'
POINTER = ROOT / 'results/book-finalisation-current.json'
AUDIT = ROOT / 'results/book-finalisation-audit-20261101'
REPAIR_KEYS = {repairs.TIMER, repairs.JUMPS, repairs.CORRELATION, repairs.FLEURONS,
               repairs.EPILOGUE, repairs.BIBLIOGRAPHY, 'd-large-04-bergomi-07'}


def code_hashes():
    return {p: sha(ROOT / p) for p in ('scripts/book_finalisation.py', 'scripts/book_completion.py',
        'probe/book_finalisation.py', 'probe/book_completion.py', 'probe/chapter_editorial.py',
        'probe/chapter_accuracy.py', 'probe/compiler_environment.py', 'probe/tex_compile.py',
        'scripts/tex-compiler/Dockerfile')}


def policy_identity():
    return {'critic_policy_sha256': fingerprint(editorial.POLICY),
            'editorial_request_sha256': fingerprint(inspect.getsource(editorial.request)),
            'completion_request_sha256': fingerprint(inspect.getsource(scope.request)),
            'meaning_sha256': fingerprint(chapter_sources.MEANING),
            'source_policy_sha256': fingerprint(chapter_sources.SOURCE_POLICY),
            'efforts': scope.EFFORTS, 'output_tokens': scope.OUTPUT_TOKENS}


def actual_draft(parent, state, task):
    label = task['dispatched_draft_label']; key = task['key']
    draft = state['versions'][key][label]; path = parent / draft['path']
    if sha(path) != task['dispatched_draft_sha256'] or sha(path) != draft['sha256']:
        raise ValueError('Actual critic input hash mismatch: ' + key)
    call = next(c for c in state['calls'] if c['id'] == task['call'])
    request = parent / 'calls' / call['id'] / 'request.json'
    body = read_json(request)
    if fingerprint(body) != call['request_sha256'] or path.read_text() not in body['messages'][0]['content']:
        raise ValueError('Saved critic request does not contain the recorded exact draft')
    return path, request, call


def verified_pdf(parent, state, key, version):
    if not version['compilation']['status'].startswith('passed'):
        return None
    document = parent / version['path']
    if sha(document) != version['sha256']:
        raise ValueError('Selected document changed')
    assets = completion.asset_map(parent, state['source_units'][key]['source_key'], document.read_text())
    for a in reversed(version['compilation'].get('attempts', [])):
        path = parent / a['path'] / 'document.pdf'
        supplied = {x['path']: x['sha256'] for x in a.get('assets', [])}
        pdf_hash = next((x['sha256'] for x in a.get('outputs', []) if x.get('path') == 'document.pdf'), None)
        if (a.get('input_sha256') == version['sha256'] and a.get('compilation_claim') and path.is_file()
                and pdf_hash == sha(path) and all(supplied.get(k) == sha(v) for k, v in assets.items())):
            return path
    raise ValueError('Passing build lacks compatible document/assets/PDF identity: ' + key)


def heading_dispositions(state, run):
    evidence = {
        'gatheral-05': [r"\subsubsection*{L\'evy Processes}"],
        'bergomi-02-s05': [r'\subsection*{2.5.5 Volatilities of volatilities}'],
        'bergomi-03-s01': [r'\subsection*{Is $\sh{T_1T_2}$ well-defined?}'],
        'd-large-02-bergomi-05': [r'\noindent\textbf{Arithmetic variance swap $w(S)=S^2$}'],
        'd-large-01-bergomi-05': [r'\subsection*{5.3.1 \quad In diffusive models}'],
        'd-large-03-bergomi-07': [r'{\LARGE\bfseries Chapter 7}', r'{\Large\bfseries Forward variance models}'],
        'd-large-07-bergomi-08': [r'\setcounter{chapter}{7}', r'\chapter{The smile of stochastic volatility models}'],
        'd-large-08-bergomi-08': [r'\subsubsection*{A.5.1 An efficient approximation}'],
        'd-large-09-bergomi-09': [r'{\LARGE\bfseries Chapter 9}'],
        'd-large-11-bergomi-11': [r'\title{Chapter 11', r'\maketitle'],
        'd-large-12-bergomi-12': [r'\title{Chapter 12', r'\Large Local-stochastic volatility models}', r'\maketitle'],
    }
    records = []
    for key, excerpts in evidence.items():
        v = state['versions'][key][state['current_versions'][key]]; doc = (run / v['path']).read_text()
        if not all(e in doc for e in excerpts):
            raise ValueError('Previously reviewed heading evidence changed: ' + key)
        row = next(r for r in state['selection_ledger'] if r['unit'] == key)
        record = {'unit': key, 'version_sha256': v['sha256'], 'flag': 'missing_heading_candidates',
                  'original_flags': row['coverage_check']['missing_heading_candidates'], 'evidence': excerpts,
                  'disposition': 'reviewed_false_alarm: headings present in alternative TeX formatting',
                  'future_checks': 'not suppressed; disposition applies only to this exact version'}
        row.setdefault('review_dispositions', []).append(record); records.append(record)
    key = 'd-large-04-bergomi-07'; v = state['versions'][key][state['current_versions'][key]]
    doc = (run / v['path']).read_text()
    single = r'01-Jan-11 & $63.8\%$  & $64.9\%$  & $319\%$ & $325\%$'
    if single not in doc or len(re.findall(r'\\begin\{table\}', doc)) != 5:
        raise ValueError('Table 7.4 single-maturity row/recombined table count differs')
    record = {'unit': key, 'version_sha256': v['sha256'], 'flag': 'table_count_warning',
              'source_blocks': ['bergomi-p0264:b6', 'bergomi-p0264:b7'],
              'evidence': single, 'disposition': 'reviewed_false_alarm: split Table 7.4 recombined; six source blocks are five complete tables',
              'numbering': 'Derivative counters restored to Tables 7.2--7.6 and Figures 7.6--7.7; actual AUX checked after build',
              'future_checks': 'not suppressed; raw heuristic result retained'}
    next(r for r in state['selection_ledger'] if r['unit'] == key).setdefault('review_dispositions', []).append(record)
    records.append(record)
    return records


def prepare(parent=PARENT):
    if not completion.speed.idle(ROOT) or not completion.speed.idle(parent):
        raise ValueError('Project or parent writer active; left untouched')
    with writer_lock(ROOT):
        old = read_json(parent / 'state.json')
        if old['status'] != completion.TERMINAL or any(c['status'] != 'completed_response' for c in old['calls']):
            raise ValueError('Expected settled completion run; rediscover before finalisation')
        baseline = read_json(AUDIT / 'invariant-baseline.json')
        if any(policy_identity()[k] != baseline[k] for k in policy_identity()):
            raise ValueError('Converter/critic policy/request/settings changed')
        run = completion.book.chapter_inputs.new_path('book-finalisation'); run.mkdir(parents=True)
        instruction=Path('/home/mdi/Downloads/Codex-Book-Finalisation-2026-11-01.txt')
        if 'REVISED, UNIFIED finalisation task' not in instruction.read_text().splitlines()[0]:
            raise ValueError('Expected the revised unified finalisation instruction')
        shutil.copyfile(instruction,run/'TASK-INSTRUCTIONS.txt')
        for name in ('inputs', 'bergomi', 'source-supplement', 'bibliography', 'accuracy'):
            if (parent / name).is_dir():shutil.copytree(parent / name, run / name)
        shutil.copyfile(parent/'canonical-source-map.json',run/'canonical-source-map.json')
        state = copy.deepcopy(old)
        state.update(status='finalisation_prepared', stage='saved-output finalisation only', deliveries={},
                     suite_protocol='book-finalisation-v1')
        state.pop('inspection', None); state.pop('coding_inspection', None)
        state['finalisation'] = {'parent': str(parent), 'parent_state_sha256': sha(parent / 'state.json'),
            'created_at': completion.runtime.now(), 'inherited_calls': len(old['calls']), 'new_model_calls': 0,
            'dispatch_disabled': True, 'policy_identity': policy_identity(), 'changed_units': [],
            'instructions_sha256':sha(run/'TASK-INSTRUCTIONS.txt'),
            'compiler_dependency_authorization': ['texlive-lang-french'], 'reused_pdf_units': []}
        state['compiler_environment']['path'] = str(parent / old['compiler_environment']['path'])
        # Preserve exact historical registry/call identities but use explicit
        # parent locations. No raw responses or immutable run files are edited.
        state['versions'] = {}
        protected = {str(parent / 'state.json'): sha(parent / 'state.json')}
        for key, label in old['current_versions'].items():
            v = copy.deepcopy(old['versions'][key][label]); document = parent / v['path']
            if sha(document) != v['sha256']:raise ValueError('Selected TeX identity mismatch')
            protected[str(document)] = sha(document)
            v['path'] = str(document)
            for a in v['compilation'].get('attempts', []):a['path'] = str(parent / a['path'])
            state['versions'][key] = {label: v}
            pdf = verified_pdf(parent, old, key, old['versions'][key][label])
            if pdf and key not in REPAIR_KEYS:
                protected[str(pdf)] = sha(pdf); state['finalisation']['reused_pdf_units'].append(key)
        comparison_rows = []
        for task in old['tasks']:
            if task['phase'] != 'critic':continue
            key = task['key']; draft, request, call = actual_draft(parent, old, task)
            selected = parent / old['versions'][key][old['current_versions'][key]]['path']
            dest = run / 'comparisons' / key; dest.mkdir(parents=True)
            shutil.copyfile(draft, dest / 'actual-critic-input.tex'); shutil.copyfile(selected, dest / 'selected-critic.tex')
            delta = ''.join(difflib.unified_diff(draft.read_text().splitlines(True), selected.read_text().splitlines(True),
                                               fromfile=str(draft), tofile=str(selected)))
            (dest / 'critic-change.diff').write_text(delta)
            result = completion.material_comparison(draft.read_text(), selected.read_text())
            result.update(key=key, critic_call=call['id'], draft_path=str(draft), draft_sha256=sha(draft),
                          selected_path=str(selected), selected_sha256=sha(selected), request_sha256=sha(request),
                          actual_request_contains_exact_draft=True)
            atomic_json(dest / 'material-comparison.json', result); comparison_rows.append(result)
            for p in (draft, request, parent / 'calls' / call['id'] / 'answer.txt'):
                protected[str(p)] = sha(p)
            next(r for r in state['selection_ledger'] if r['unit'] == key)['critic_preservation_comparison'] = result
        if len(comparison_rows) != 17:raise ValueError('Unexpected completion-unit count; do not silently omit comparisons')
        atomic_json(run / 'material-comparisons.json', comparison_rows)
        for key in sorted(REPAIR_KEYS):
            label = old['current_versions'][key]; original = parent / old['versions'][key][label]['path']
            raw = None
            if key == repairs.TIMER:
                raw_record = old['versions'][key]['critic-call-004']; raw_path=parent/raw_record['path']
                if sha(raw_path)!=raw_record['sha256']:raise ValueError('Saved timer critic document changed')
                protected[str(raw_path)]=sha(raw_path);raw=raw_path.read_text()
            document, edits = repairs.repair_document(key, original.read_text(), raw_critic=raw)
            if document == original.read_text():raise ValueError('Expected finalisation edit absent: '+key)
            new_label = 'finalisation-' + fingerprint(document)[:12]
            v = completion.remember(run, state, key, new_label, document,
                {'parent_run': str(parent), 'source': str(original), 'source_sha256': sha(original),
                 'parent_label': label, 'edits': edits, 'kind': 'offline editorial/technical derivative; no model call'})
            state['current_versions'][key] = new_label
            dest = run / 'repairs' / key; dest.mkdir(parents=True)
            shutil.copyfile(original, dest / 'original-selected.tex')
            (dest / 'change.diff').write_text(''.join(difflib.unified_diff(original.read_text().splitlines(True), document.splitlines(True),
                fromfile=str(original), tofile=v['path'])))
            atomic_json(dest / 'provenance.json', v['origin'])
            row = next(r for r in state['selection_ledger'] if r['unit'] == key)
            row.update(selection=new_label, version_sha256=v['sha256'], finalisation_disposition=edits)
            state['finalisation']['changed_units'].append(key)
        # Recover the actual log, retaining the historical unavailable record.
        key = repairs.TIMER; answer = (parent / 'calls/call-004/answer.txt').read_text()
        _, envelope = chapter_accuracy.envelope(answer, completion.book.simple.extract_document)
        notes, status = editorial.notes_text(answer, envelope)
        if status != 'captured' or not editorial.tex_accuracy_entries(notes):raise ValueError('Timer in-document log not recovered')
        record = editorial.notes_record(key, notes, captured=status, phase='critic-call-004-recovered')
        record['origin'] = {'answer': str(parent / 'calls/call-004/answer.txt'), 'answer_sha256': sha(parent / 'calls/call-004/answer.txt'),
                            'location': 'fenced TeX Accuracy log; reported dispositions, not independent verification'}
        path = run / 'accuracy' / key / 'critic-call-004-recovered.json'; atomic_json(path, record)
        path.with_suffix('.md').write_text('# Recovered in-document accuracy log\n\n'+notes+'\n')
        state['accuracy_records'][key] = str(path.relative_to(run)); state['accuracy'][key] = str(path.with_suffix('.md').relative_to(run))
        shutil.copytree(AUDIT, run / 'source-review', ignore=shutil.ignore_patterns('comparisons', 'comparisons.json'))
        dispositions = heading_dispositions(state, run)
        atomic_json(run / 'reviewed-flags.json', dispositions)
        atomic_json(run / 'parent-integrity.json', protected)
        atomic_json(run/'prepared-inputs.json',{str(p):sha(p) for directory in ('inputs','bergomi','source-review')
                    for p in (run/directory).rglob('*') if p.is_file()})
        state['finalisation']['code'] = code_hashes()
        atomic_json(run / 'state.json', state)
        atomic_json(POINTER, {'run': str(run), 'parent': str(parent), 'no_inference': True})
        report(run, state)
        print('Finalisation prepared, no inference:', run)
        return run


def verify(run):
    state = read_json(run / 'state.json')
    if state['finalisation']['code'] != code_hashes():raise ValueError('Finalisation code changed; retain this derivative and prepare a new one')
    if state['finalisation']['policy_identity'] != policy_identity():raise ValueError('Critic/converter policy changed')
    InputGuard(read_json(run / 'parent-integrity.json'))
    InputGuard(read_json(run/'prepared-inputs.json'))
    for key, label in state['current_versions'].items():
        v = state['versions'][key][label]
        if sha(run / v['path']) != v['sha256']:raise ValueError('Finalisation document changed')
    if len(state['calls']) != state['finalisation']['inherited_calls'] or state['finalisation']['new_model_calls']:
        raise ValueError('Finalisation cannot add or discard calls')
    return state


def report(run, state):
    lines = ['# Book finalisation', '', '**'+state['status'].upper()+'**', '',
             f'Parent: `{state["finalisation"]["parent"]}`; {len(state["calls"])} inherited settled calls; **zero new model calls**.',
             'Converter/critic prompts, mathematical correction policy, reasoning settings and acceptance rules are unchanged.', '',
             '## Delivery index', '', '| Book | Reading PDF | Editable source | TeX-only ZIP | Complete-source ZIP | Included PDF parts |',
             '|---|---|---|---|---|---|']
    for book, item in state.get('deliveries', {}).items():
        def link(path):return '['+Path(path).name+']('+str(path)+')' if path else 'not yet built'
        lines.append('| '+ ' | '.join([book, link(item['reading_pdf']), link(item['edition']), link(item['tex_only_zip']['path']),
                     link(item['source_zip']['path']), f'{item["pdf_parts"]}/{item["text_parts"]}']) + ' |')
    lines += ['', 'The master includes part PDFs; the chapter/section document.tex files are editable. Original front/back/index supplements are PDF source pages, not editable transcription.', '',
              '## Review records', '',
              '- `material-comparisons.json` and `comparisons/`: all 17 actual hash-verified critic inputs, selected revisions and diffs.',
              '- `reviewed-flags.json`: version-specific false-alarm dispositions; original checks are retained and future checks are not weakened.',
              '- `source-review/`: inspected local source-page images and case-specific mathematical observations.',
              '- `accuracy/`: all historical logs plus recovered timer-appendix log. Reported resolutions are not automatically independent verification.',
              '- `repairs/`: original selected text, exact editorial/technical diffs and provenance.',
              '- `coverage.json`: canonical target accounting; not a mathematical-completeness certificate.', '',
              'No completed inference/OCR/criticism was rerun. No article queue, production continuation or supervision is enabled.', '']
    (run / 'FINAL-INDEX.md').write_text('\n'.join(lines))
    atomic_json(run / 'coverage.json', completion.coverage_report(run, state))
    atomic_json(run / 'finalisation-progress.json', {'status': state['status'], 'parent': state['finalisation']['parent'],
        'inherited_calls': len(state['calls']), 'new_model_calls': 0, 'deliveries': state.get('deliveries', {}),
        'index': str(run / 'FINAL-INDEX.md'), 'inspection': state.get('inspection'), 'diagnostic': state.get('diagnostic')})


def check_float_numbers(run, state):
    key = 'd-large-04-bergomi-07'; v = state['versions'][key][state['current_versions'][key]]
    p = run / v['compilation']['attempts'][-1]['path'] / 'document.aux'
    text = p.read_text()
    tables = re.findall(r'contentsline \{table\}\{\\numberline \{([^}]+)\}', text)
    figures = re.findall(r'contentsline \{figure\}\{\\numberline \{([^}]+)\}', text)
    if tables != ['7.2','7.3','7.4','7.5','7.6'] or figures != ['7.6','7.7']:
        raise ValueError('Chapter 7 table/figure numbering remains inconsistent')
    atomic_json(run / 'table-numbering-validation.json', {'source': str(p), 'sha256': sha(p), 'tables': tables,
                'figures': figures, 'single_maturity_row': '01-Jan-11, 63.8%, 64.9%, 319%, 325%', 'status': 'passed'})


def bundle(run, state):
    report(run, state)
    dest = ROOT / 'results/inspection' / ('book-finalisation-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'.zip')
    files = {}
    for name in ('state.json','coverage.json','material-comparisons.json','reviewed-flags.json','parent-integrity.json',
                 'FINAL-INDEX.md','finalisation-progress.json','validation.json','table-numbering-validation.json','TASK-INSTRUCTIONS.txt'):
        p=run/name
        if p.is_file():files[name]=p
    for directory in ('comparisons','repairs','source-review','accuracy'):
        for p in (run/directory).rglob('*'):
            if p.is_file() and p.suffix in ('.tex','.json','.md','.diff','.png'):
                files[p.relative_to(run).as_posix()]=p
    for key in state['finalisation']['changed_units']:
        v=state['versions'][key][state['current_versions'][key]];files['current-selected/'+key+'/document.tex']=run/v['path']
        for a in v['compilation'].get('attempts',[]):
            for name in ('console.log','result.json'):
                p=run/a['path']/name
                if p.is_file():files['builds/'+key+'/'+name]=p
    for name in code_hashes():files['implementation/'+name]=ROOT/name
    for p in (ROOT/'tests').glob('test_book_finalisation.py'):files['implementation/tests/'+p.name]=p
    for name in ('AGENTS.md','docs/BOOK-COMPLETION.md','docs/PROJECT-STATE.md','docs/CODEX-HANDOVER.md'):
        files['implementation/'+name]=ROOT/name
    settings=[]
    parent=Path(state['finalisation']['parent'])
    for call in state['calls']:
        p=parent/'calls'/call['id']/'settings.json';cfg=read_json(p)
        settings.append({'id':call['id'],'parent':call['parent'],'actual_model':call.get('metadata',{}).get('actual_model'),
            'elapsed_seconds':call.get('elapsed_seconds'),'usage':call.get('metadata',{}).get('usage'),
            'finish_reason':call.get('metadata',{}).get('finish_reason'),
            'settings':{k:cfg.get(k) for k in ('model','max_tokens','stream','requested_reasoning_effort','generation_deadline_seconds')},
            'raw_evidence_omitted_at':str(parent/'calls'/call['id'])})
    files['timings-and-settings.json']=json.dumps(settings,indent=2).encode()
    files['START-HERE.md']=('# Revised unified book finalisation\n\nRead FINAL-INDEX.md, validation.json, reviewed-flags.json and source-review/. '
        'All 17 exact critic inputs, selected revisions and compact diffs are under comparisons/. The current editorial derivatives are separate. '
        'Old logs/claims are preserved as historical evidence; recovered logs and source-check notes are identified. '
        'No new model calls or altered critic policy. Original PDFs, bulk assets, streaming/wire logs and reasoning are omitted; source paths remain recorded. '
        'The actual delivery files are indexed; successful compilation is not mathematical verification.\n').encode()
    files['FILE-HASHES.json']=json.dumps({n:hashlib.sha256(p).hexdigest() if isinstance(p,bytes) else sha(p) for n,p in files.items()},indent=2).encode()
    result=completion.write_zip(dest,files);state['inspection']=result;atomic_json(run/'state.json',state);report(run,state)
    return result


def execute(run):
    state=verify(run)
    if state['status']=='finalisation_delivered':print(run/'FINAL-INDEX.md');return
    with writer_lock(ROOT),writer_lock(run):
        try:
            state['status']='finalisation_building';atomic_json(run/'state.json',state)
            # Explicit revised-task authorization: a versioned compiler image,
            # fixed package allowlist, no document inputs/network in TeX builds.
            compiler_environment.ensure(run,state,ROOT,extra=('texlive-lang-french',))
            for key in state['finalisation']['changed_units']:
                completion.compile_version(run,state,key,state['current_versions'][key])
            bad=[k for k in state['current_versions'] if not state['versions'][k][state['current_versions'][k]]['compilation']['status'].startswith('passed')]
            if bad:raise ValueError('Unresolved part builds: '+', '.join(bad))
            check_float_numbers(run,state)
            for name in ('gatheral','bergomi'):completion.assemble(run,state,name,compile=True)
            for name,d in state['deliveries'].items():
                if not d['reading_pdf'] or d['pdf_parts']!=d['text_parts']:raise ValueError('Delivery PDF gaps remain: '+name)
            state['status']='finalisation_delivered'
            state['finalisation']['finished_at']=completion.runtime.now()
        except Exception as exc:
            state.update(status='finalisation_blocked',diagnostic=type(exc).__name__+': '+str(exc))
            raise
        finally:
            atomic_json(run/'state.json',state);report(run,state)
        verify(run);bundle(run,state)
        print('Delivered; no inference:',run/'FINAL-INDEX.md')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','run','status','bundle'))
    p.add_argument('--run',type=Path);p.add_argument('--parent',type=Path,default=PARENT);a=p.parse_args()
    if a.action=='prepare':prepare(a.parent.resolve());return
    run=(a.run or Path(read_json(POINTER)['run'])).resolve()
    if a.action=='run':execute(run)
    elif a.action=='status':print(json.dumps(read_json(run/'finalisation-progress.json'),indent=2))
    else:
        with writer_lock(ROOT),writer_lock(run):print(bundle(run,verify(run))['path'])


if __name__=='__main__':
    try:main()
    except Exception as exc:print('FINALISATION BLOCKED:',type(exc).__name__+':',exc,file=sys.stderr);raise SystemExit(1)
