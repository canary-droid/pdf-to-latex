"""Offline selection and linked assessment for the existing finite suite controller."""
import copy
import difflib
import json
from pathlib import Path
import re
import shutil
from collections import Counter
import speed_suite as ctrl
from probe import speed_suite as suite, chapter_glm as runtime, chapter_protocol as protocol
from probe.common import atomic_json, read_json, sha, fingerprint
from probe.experiment import InputGuard, verify_seal

ROOT=ctrl.ROOT
PREVIOUS=ROOT/'runs/speed-suite-20261029T191756Z-3933e0'
POINTER=ROOT/'results/overnight-suite-current.json'
# Reviewed source boundaries, not generated replacements. Every span is checked
# against the actual unchanged owned-block order before it is frozen.
RECAPS=((5,10,14),(7,9,11),(8,11,14),(9,12,16))
LARGER=((5,2,8),(5,9,9),(7,1,5),(7,6,6),(7,7,7),(7,8,8),
        (8,1,7),(8,8,10),(9,1,11),(10,1,3),(11,1,5),(12,1,5),(12,6,8))


def replace_once(text,old,new):
    if text.count(old)!=1:raise ValueError('Reviewed replacement does not match exactly once')
    return text.replace(old,new,1)


def repair_tag(text):
    return replace_once(text,r'\Bigg).\tag{4.14}'+'\n'+r'\end{aligned}',
                        r'\Bigg).'+'\n'+r'\end{aligned}\tag{4.14}')


def repair_volga(text):
    return replace_once(text,r'C_{\widehat\sigma\widehat\sigma} = S\sqrt{\tau}\,n(d_1)\,d_1 d_2',
                        r'C_{\widehat\sigma\widehat\sigma} = S\sqrt{\tau}\,n(d_1)\,d_1 d_2/\widehat\sigma')


def repair_lewis(text):
    a='''$\\frac12 J^{(3)}/(\\nu^2 t^3)$, both would diverge as $t\\to0$ (like $t^{-2}$
and $t^{-3}$), contradicting'''
    b='''$\\frac12 J^{(3)}/(\\nu^2 t^3)$. \\textbf{Codex qualification:}
for nonzero $\\rho$, the displayed $\\beta_2$ diverges; its other displayed
terms do not cancel that leading term. A divergence of $\\beta_0$ is not
established: $J^{(2)}$ is undefined here and cancellation has not been excluded.
The demonstrated $\\beta_2$ behavior contradicts'''
    text=replace_once(text,a,b)
    text=replace_once(text,'''$\\beta_0$ and $\\beta_2$ to diverge like $t^{-2}$, $t^{-3}$; the short-time''',
                     '''$\\beta_2$ to diverge like $t^{-3}$ for nonzero $\\rho$.
\\textbf{Codex qualification:} no conclusion about cancellation in $\\beta_0$
is justified without $J^{(2)}$. The short-time''')
    return text


def prepare_repairs(run,old,consumed):
    """Separate derivatives: no control draft, original answer or book is edited."""
    rows=[]
    specs=[('bergomi-04-s02-tag','s3-high-bergomi-04-s02','critic-call-015',repair_tag,
            'Equation 4.14: moved tag outside aligned, inside surrounding display; mathematical tokens unchanged.'),
           ('bergomi-04-s01-volga','s3-high-bergomi-04-s01','critic-call-014',repair_volga,
            'Explanatory note: divide volatility second derivative by sigma. Main missing-square correction retained. Both historical Max and High share this error.'),
           ('gatheral-lewis-qualification','s3-high-pilot-gatheral-07-s05','critic-call-016',repair_lewis,
            'J3 brace tends to 3; beta2 inconsistency established for nonzero rho. beta0 cancellation remains unestablished without J2. Lewis 2000 pp142–144 needed.')]
    for key,original,label,fix,reason in specs:
        v=old['versions'][original][label];src=PREVIOUS/v['path'];consumed[str(src)]=sha(src)
        text=src.read_text();out=run/'offline-repairs'/key;out.mkdir(parents=True)
        (out/'original.tex').write_text(text);new=fix(text)
        notice='\n\\par\\smallskip\\noindent\\textbf{Codex editorial repair (29 October 2026).} '+reason.replace('sigma',r'$\sigma$').replace('beta2',r'$\beta_2$').replace('beta0',r'$\beta_0$').replace('J2',r'$J^{(2)}$').replace('J3',r'$J^{(3)}$')+'\n'
        new=replace_once(new,r'\end{document}',notice+r'\end{document}')
        (out/'document.tex').write_text(new)
        (out/'change.diff').write_text(''.join(difflib.unified_diff(text.splitlines(True),new.splitlines(True),fromfile=str(src),tofile='linked document.tex')))
        source=next(t['source_key'] for t in old['tasks'] if t['key']==original)
        rows.append({'key':key,'source_key':source,'path':str(out.relative_to(run)),'source_path':str(src),'source_sha256':sha(src),
                     'document_sha256':sha(out/'document.tex'),'reason':reason,'attribution':'Codex assessment; source checks in assessment.md',
                     'compilation':{'status':'not_attempted','reason':'Codex Docker socket denied; compile saved repair at operator launch'},'not_a_benchmark_input':True})
    atomic_json(run/'offline-repairs/index.json',rows)
    return rows


def compile_repairs(run,state):
    path=run/'offline-repairs/index.json';rows=read_json(path)
    for row in rows:
        if row['compilation'].get('status') not in ('not_attempted',):continue
        folder=run/row['path'];doc=folder/'document.tex'
        if sha(doc)!=row['document_sha256']:raise runtime.Fatal('Linked offline repair changed')
        row['compilation']=ctrl.book.compiler_environment.compile_saved(run,state,ROOT,doc.read_text(),folder/'compilation',ctrl.book.selected_assets(run,row['source_key']))
        atomic_json(path,rows)
    runtime.save(run,state)


def reconcile_findings_only(run,state,task,call):
    """Recover the already written notes/annotation, never replay finish_task.

    The transport seal and original task remain in the parent. This derivative
    records a local finalization, not a replacement answer or a model retry.
    Repeated reconciliation validates the same evidence and writes nothing.
    """
    book=ctrl.book;key=task['key'];label='critic-'+call['id']
    folder=run/'calls'/call['id'];answer=(folder/'answer.txt').read_text()
    body=read_json(folder/'request.json')
    if call.get('seal'):verify_seal(folder,call['seal'])
    if (task['phase']!='critic' or task.get('call')!=call['id'] or call['parent']!=task['id']
            or call['status']!='completed_response' or fingerprint(body)!=call['request_sha256']
            or body.get('model')!=protocol.MODEL
            or call.get('metadata',{}).get('actual_model')!=protocol.MODEL
            or call.get('metadata',{}).get('finish_reason')!='stop'):
        raise runtime.Fatal('Local findings recovery requires the exact normally completed critic response')
    document,info=book.chapter_accuracy.envelope(answer,book.simple.extract_document)
    if (document is not None and book.chapter_accuracy.complete_document(document)) or r'\documentclass' in answer or r'\begin{document}' in answer:
        raise runtime.Fatal('This local recovery is for findings only, not a replacement or partial document')
    versions=state['versions'][key]
    if label in versions:raise runtime.Fatal('Findings-only call unexpectedly owns a replacement document')
    current=state['current_versions'][key];selected=versions[current]
    original=selected['origin'].get('from') if current==label+'-annotated' else current
    if original!=task.get('draft_label'):raise runtime.Fatal('Retained draft identity differs from reviewed input')
    draft=book.bound_output(run,state,key,original)
    if versions[original]['sha256']!=task['expected_draft_sha256'] or draft not in body['messages'][0]['content']:
        raise runtime.Fatal('Findings recovery draft/request mismatch')
    notes_path=Path('accuracy')/key/(label+'.json')
    if state['accuracy_records'][key]!=str(notes_path):raise runtime.Fatal('Unexpected partial finalization notes')
    notes=read_json(run/notes_path)
    raw,status=book.edit.notes_text(answer,info)
    expected=book.edit.notes_record(key,raw,captured=status,complete=True,phase=label)
    if notes!=expected or (run/notes_path.with_suffix('.raw.md')).read_text()!=raw:
        raise runtime.Fatal('Saved notes differ from the actual critic answer')
    annotated=book.edit.annotate(draft,[dict(x,attribution='GLM') for x in notes['items'] if x['category']=='material'])
    if book.bound_output(run,state,key,current)!=annotated:
        raise runtime.Fatal('Saved annotation is not the retained draft plus recorded notes')
    evidence={str(p.relative_to(run)):sha(p) for p in (folder/'answer.txt',folder/'request.json',run/notes_path,
        run/notes_path.with_suffix('.md'),run/notes_path.with_suffix('.raw.md'),run/versions[original]['path'],run/selected['path'])}
    dest=run/'local-recovery'/(call['id']+'.json')
    if dest.exists():
        rec=read_json(dest)
        if rec['evidence']!=evidence or rec['task']!=task['id'] or task.get('local_finalization_recovery')!=str(dest.relative_to(run)) or task['status']!='critic_unchanged':
            raise runtime.Fatal('Changed local recovery or finalization state')
        return rec
    if task['status']!='coordinator_failure':raise runtime.Fatal('Only a recorded failed finalization may be recovered here')
    rec={'at':runtime.now(),'task':task['id'],'call':call['id'],'evidence':evidence,
        'historical_status':task['status'],'historical_error':task.get('error'),
        'selected_version':current,'retained_draft':original,'status':'recovered_findings_only',
        'model_calls':0,'model_replacement':False,'suggested_edits_applied':False,
        'meaning':'Existing notes and annotation verified and reused; not mathematical verification. Compilation remains separate.'}
    atomic_json(dest,rec)
    task.update(status='critic_unchanged',local_finalization_recovery=str(dest.relative_to(run)),
        revision_diagnostic='Findings-only response; verified retained draft/annotation reused after local finalization repair')
    task.pop('error',None)
    return rec


def compile_local_recoveries(run,state):
    """Compile only the recovered selected version, never rerun a model call."""
    for task in state['tasks']:
        if not task.get('local_finalization_recovery'):continue
        call=next(c for c in state['calls'] if c['id']==task['call'])
        rec=reconcile_findings_only(run,state,task,call)
        version=state['versions'][task['key']][rec['selected_version']]
        if version['compilation']['status']=='not_attempted':
            ctrl.book.compile_version(run,state,task['key'],rec['selected_version'])


def prepare_continuation(parent):
    """Explicit same-manifest link after a local finalizer/probe code repair."""
    parent=Path(parent).resolve()
    if not all(ctrl.idle(p) for p in (ROOT,parent)):raise RuntimeError('Writer active; no linked preparation')
    ctrl.book.converter_idle(ROOT)
    if Path(read_json(POINTER)['run']).resolve()!=parent:raise RuntimeError('Use the current overnight pointer; do not duplicate an existing link')
    old=ctrl.recorded_evidence(parent);binding=read_json(parent/'binding.json')
    if old['suite_protocol']!=suite.OVERNIGHT or old['status']!='stopped_error' or any(c['status']=='in_progress' for c in old['calls']):
        raise runtime.Fatal('Requires the stopped overnight suite with settled calls')
    if any(not c.get('seal') for c in old['calls']):raise runtime.Fatal('Every inherited call must have sealed evidence')
    a=suite.stage_tasks(old,1)
    if len(a)!=6 or any(t['status'] not in suite.GOOD|{'coordinator_failure'} for t in a):raise runtime.Fatal('Stage A responses are not all finalizable')
    if any(t['status']!='pending' for t in old['tasks'] if t['stage']!=1) or len(old['calls'])!=7:
        raise runtime.Fatal('Expected six consumed Stage A calls plus readiness; B/C/D must be untouched')
    # Copy ordinary artifact files, as in the chapter linked-continuation route.
    # The original request/response bytes and seals are never rewritten.
    snapshot={str(p):sha(p) for p in parent.rglob('*') if p.is_file() and p.name!='.probe.lock'}
    if any(p.is_symlink() for p in parent.rglob('*')):raise runtime.Fatal('Unexpected symlink in parent evidence')
    run=ctrl.book.chapter_inputs.new_path('overnight-suite')
    skip={'.probe.lock','pause.json','stop.json','terminal.log','report.html','report.md','summary.json','progress.json',
          'last-inspection.json','normal-terminal-checks.json','latest-readiness.json','effort-support-live.json','operator-handover.md'}
    shutil.copytree(parent,run,ignore=lambda path,names: [n for n in names if Path(path)==parent and n in skip])
    for p,h in snapshot.items():
        relative=Path(p).relative_to(parent)
        if len(relative.parts)==1 and relative.name in skip:continue
        if sha(run/relative)!=h:raise runtime.Fatal('Inherited copy differs: '+str(relative))
    history=run/'historical-run';history.mkdir()
    for name in ('state.json','binding.json','progress.json','terminal.log','normal-terminal-checks.json','effort-support-live.json','last-inspection.json'):
        if (parent/name).exists():shutil.copyfile(parent/name,history/name)
    state=copy.deepcopy(old);recovered=[]
    for task in suite.stage_tasks(state,1):
        if task['status']=='coordinator_failure':
            call=next(c for c in state['calls'] if c['id']==task['call'])
            recovered.append(reconcile_findings_only(run,state,task,call))
    if not recovered:raise runtime.Fatal('No eligible failed local finalization found')
    suite.finish_stage(state,1)
    state.update(status='prepared_offline',stage='Stage A finalized locally; B/C/D pending launch',active_stage=None,diagnostic=None,
                 linked_prepared_at=runtime.now())
    state.pop('diagnostic_file',None)
    current_code=ctrl.hashes()
    lineage={'path':str(parent),'state_sha256':sha(parent/'state.json'),'binding_sha256':sha(parent/'binding.json'),
        'inherited_calls':len(old['calls']),'historical_status':old['status'],'historical_diagnostic':old.get('diagnostic'),
        'code_changes':{p:{'before':binding['code'].get(p),'after':current_code.get(p)} for p in sorted(set(binding['code'])|set(current_code)) if binding['code'].get(p)!=current_code.get(p)},
        'policy':'Same frozen 44 tasks; six already answered. Only 38 pending B/C/D requests. No replay or production dispatch.',
        'local_recoveries':[r['call'] for r in recovered]}
    atomic_json(run/'continuation-lineage.json',lineage)
    state['local_recovery_parent']=lineage
    # Bind both the original snapshot and its independent copies. Mutable new
    # state/compilation indices are not sealed; all inherited evidence is.
    binding['consumed'].update(snapshot)
    binding['prepared']={str(run/Path(p).relative_to(parent)):h for p,h in binding['prepared'].items()}
    for folder in ('historical-run','local-recovery','calls','versions','accuracy','offline-repairs'):
        binding['prepared'].update({str(p):sha(p) for p in (run/folder).rglob('*') if p.is_file()})
    binding['prepared'][str(run/'continuation-lineage.json')]=sha(run/'continuation-lineage.json')
    binding.update(code=current_code,linked_parent=lineage)
    atomic_json(run/'binding.json',binding);state['binding_sha256']=fingerprint(binding)
    runtime.save(run,state);ctrl.verify(run);ctrl.report(run,state);ctrl.bundle(run,state)
    InputGuard(snapshot)  # Parent remains byte-for-byte as observed at handover.
    atomic_json(POINTER,{'run':str(run),'parent':str(parent)})
    print('PREPARED, NOT RUNNING:',run)
    return run


def secondary_span(folder,pages):
    entries=read_json(folder/'secondary.json')['pages'];chosen=[p for p in entries if p['physical_pdf_page'] in pages]
    if [p['physical_pdf_page'] for p in chosen]!=pages:raise ValueError('Native-text target mapping gap')
    return '\n\n'.join(f"Physical PDF page {p['physical_pdf_page']}; printed {p.get('printed_page','unknown')}\n"+p['text'] for p in chosen)


def prepare():
    parent=Path(read_json(ctrl.book.POINTER)['run']);old=read_json(PREVIOUS/'state.json');prod=read_json(parent/'state.json')
    if POINTER.exists():raise RuntimeError('Overnight preparation already exists; use run/status, no duplicate creation')
    if not all(ctrl.idle(p) for p in (ROOT,parent,PREVIOUS)):raise RuntimeError('Writer active; leave code/evidence untouched')
    ctrl.book.converter_idle(ROOT)
    if old['status']!=suite.TERMINAL or prod['status']!='paused' or any(c['status']=='in_progress' for s in (old,prod) for c in s['calls']):raise ValueError('Released finished-suite / paused-production handover required')
    consumed={}
    for origin,state in ((PREVIOUS,old),(parent,prod)):
        binding=read_json(origin/'binding.json')
        if fingerprint(binding)!=state['binding_sha256']:raise ValueError('Historical binding mismatch')
        for name in ('state.json','binding.json','concurrency-runtime-binding.json'):
            consumed[str(origin/name)]=sha(origin/name)
    pb=read_json(parent/'binding.json')
    fixed={t['id']:t for t in pb['tasks']}
    for t in prod['tasks']:
        if t['id'] in fixed and any(t.get(k)!=fixed[t['id']].get(k) for k in ('key','phase','source_key','section','context','reasoning_effort')):
            raise ValueError('Production task differs from its frozen binding')
    extra=read_json(parent/'bergomi-preparation.json')
    if fingerprint(extra)!=prod['bergomi_preparation'] or sha(parent/'bergomi/manifest.json')!=extra['seal']:
        raise ValueError('Bergomi prepared-input manifest changed')
    source_expected={str(parent/'bergomi'/x['path']):x['sha256'] for x in read_json(parent/'bergomi/manifest.json')}
    consumed[str(parent/'bergomi/manifest.json')]=extra['seal']
    # Historical code hashes remain historical. Verify consumed evidence against
    # its recorded identities, without requiring old code to equal new code.
    run=ctrl.book.chapter_inputs.new_path('overnight-suite');run.mkdir()
    tasks=[];controls={};copied=set();saved={};mapping=[]
    def copy_source(origin,key):
        if key in copied:return
        src=ctrl.source_folder(origin,key);dst=ctrl.source_folder(run,key);dst.mkdir(parents=True)
        for name in ('source.tex','native.json','provenance.json','secondary.txt','secondary.json','assets.json'):
            p=src/name
            if name=='provenance.json' and not p.exists():continue
            shutil.copyfile(p,dst/name);consumed[str(p)]=sha(p)
        native=read_json(dst/'native.json');pages=[p['page']['original_physical_page'] for p in native['pages']]
        if pages!=sorted(set(pages)) or not all(p['page']['owner'] for p in native['pages']):raise ValueError('Duplicated/nonowned chapter page')
        if pages!=[p['physical_pdf_page'] for p in read_json(dst/'secondary.json')['pages']]:raise ValueError('Dual-source ownership mismatch')
        for name in read_json(dst/'assets.json'):
            p=src.parent/name;to=dst.parent/name
            if Path(name).is_absolute() or '..' in Path(name).parts or p.is_symlink():raise ValueError('Unsafe asset')
            to.parent.mkdir(parents=True,exist_ok=True)
            if to.exists() and sha(to)!=sha(p):raise ValueError('Conflicting asset')
            if not to.exists():shutil.copyfile(p,to)
            consumed[str(p)]=sha(p)
        # Check the original prepared-input manifest, when present, for the files
        # actually consumed rather than rehashing unrelated archives/model files.
        binding=read_json(origin/'binding.json');bound={**source_expected,**binding.get('prepared',{}),**binding.get('consumed',{})}
        for p,h in consumed.items():
            if p in bound and bound[p]!=h:raise ValueError('Saved source differs from historical seal: '+p)
        copied.add(key)
    def control(origin,state,key,phase):
        t=next(t for t in state['tasks'] if t['key']==key and t['phase']==phase)
        c=next(c for c in state['calls'] if c['id']==t['call']);folder=ctrl.call_folder(origin,c);verify_seal(folder,c['seal'])
        body=read_json(folder/'request.json')
        if fingerprint(body)!=c['request_sha256']:raise ValueError('Control request hash mismatch')
        ident=key+'/'+phase;dest=run/'controls'/ident;dest.mkdir(parents=True,exist_ok=True)
        for name in ('request.json','answer.txt','settings.json','response-metadata.json','outcome.json'):
            p=folder/name
            if p.exists():shutil.copyfile(p,dest/name);consumed[str(p)]=sha(p)
        controls[ident]={'run':str(origin),'task':t['id'],'call':c['id'],'seal':c['seal'],'request_sha256':c['request_sha256'],
                        'elapsed_seconds':c.get('elapsed_seconds'),'usage':c.get('metadata',{}).get('usage'),
                        'finish_reason':c.get('metadata',{}).get('finish_reason'),'status':t['status'],'source_characters':len((t.get('section') or {}).get('text',''))}
        return t,c,body
    def base(key):return next(t for t in prod['tasks'] if t['key']==key and t['phase']=='convert')
    # Six exact historical Max inputs. No corrected derivatives or diagnoses enter.
    selections=[(PREVIOUS,old,'s1-four-bergomi-04-s03'),(PREVIOUS,old,'s1-four-bergomi-05-s01'),
                (PREVIOUS,old,'s1-four-bergomi-06-s06'),(PREVIOUS,old,'s4-dual-klebaner-04'),
                (parent,prod,'bergomi-03-s01'),(parent,prod,'bergomi-03-s02')]
    for origin,state,key in selections:
        t,c,body=control(origin,state,key,'critic');copy_source(origin,t['source_key'])
        if body['reasoning_effort']!='max':raise ValueError('Stage A requires Max control')
        matches=[v for v in state['versions'][key].values() if (origin/v['path']).read_text() in body['messages'][0]['content']]
        if not matches:raise ValueError('No exact historical input draft')
        v=max(matches,key=lambda v:(origin/v['path']).stat().st_size);draft=(origin/v['path']).read_text()
        if sha(origin/v['path'])!=v['sha256']:raise ValueError('Control draft changed')
        consumed[str(origin/v['path'])]=v['sha256'];newkey='a-high-'+key
        task={'id':newkey+'/critic','key':newkey,'stage':1,'arm':'high','phase':'critic','status':'pending',
              'source_key':t['source_key'],'section':copy.deepcopy(t.get('section')),'context':t.get('context',''),
              'reasoning_effort':'high','depends_on':None,'draft_label':'saved-control-draft','expected_draft_sha256':v['sha256'],
              'request_recipe':'exact_historical','baseline':key,'coverage':ctrl.book.recovery.section_coverage(t,read_json(ctrl.source_folder(run,t['source_key'])/'native.json')),
              'selection_reason':'Same Max critic input; varied substantial mathematics. Failed Max is a recovery comparison, not a successful-answer control.'}
        variant=suite.effort_variant(body,'high');ctrl.freeze_request(run,task,variant);tasks.append(task);saved[newkey]=draft
        atomic_json(run/'comparisons'/(newkey+'.json'),{'difference':suite.difference(body,variant),'control':controls[key+'/critic'],'draft_sha256':v['sha256']})
    def pair(stage,key,source,section,context,recipe,baseline,body=None,secondary=None):
        copy_source(parent,source);native=read_json(ctrl.source_folder(run,source)/'native.json');ts=[]
        for phase in ('convert','critic'):
            t={'id':key+'/'+phase,'key':key,'stage':stage,'arm':'dual' if recipe=='short_section' else 'production',
               'phase':phase,'status':'pending','source_key':source,'section':copy.deepcopy(section),'context':context,
               'secondary_target':secondary,'reasoning_effort':'max' if phase=='critic' else 'low' if stage==2 else 'high',
               'depends_on':key+'/convert' if phase=='critic' else None,'request_recipe':recipe,'baseline':baseline,'draft_label':None}
            t['coverage']=ctrl.book.recovery.section_coverage(t,native);tasks.append(t);ts.append(t)
        if body is None:body=ctrl.larger_body(run,ts[0]) if recipe=='short_section' else ctrl.book.body_for(run,{'phase_efforts':{'convert':'high','critic':'max'}},ts[0])
        ctrl.freeze_request(run,ts[0],body)
        atomic_json(run/'prepared'/key/'critic-dependency.json',{'task':suite.frozen_task(ts[1]),'status':'awaiting own complete draft; exact body saved before dispatch','no_placeholder_dispatch':True})
        return ts
    for key in ('bergomi-04-s01','bergomi-04-s02'):
        t,c,high=control(parent,prod,key,'convert');control(parent,prod,key,'critic')
        oldtask=next(t for t in old['tasks'] if t['key']=='s5-low-'+key and t['phase']=='convert')
        low=read_json(PREVIOUS/oldtask['frozen_request'])
        if low!=suite.effort_variant(high,'low'):raise ValueError('Skipped Low frozen input changed')
        pair(2,'b-low-'+key,t['source_key'],t['section'],t.get('context',''),'production',key,body=low)
        atomic_json(run/'comparisons'/('b-low-'+key+'.json'),{'difference':suite.difference(high,low),'copied_skipped_request':str(PREVIOUS/oldtask['frozen_request'])})
    earlier_targets={b for t in old['tasks'] if t['phase']=='convert' and t['stage'] in (1,2) for b in (t.get('section') or {}).get('blocks',[])}
    new_targets=set()
    for stage,groups in ((3,RECAPS),(4,LARGER)):
        for number,(ch,first,last) in enumerate(groups,1):
            ids=[f'bergomi-{ch:02}-s{n:02}' for n in range(first,last+1)];items=[base(k) for k in ids];source=items[0]['source_key']
            if any(t['status']!='pending' or any(c['parent']==t['id'] for c in prod['calls']) for t in items):raise ValueError('New group contains consumed production work')
            copy_source(parent,source);folder=ctrl.source_folder(run,source);native=read_json(folder/'native.json')
            section=suite.grouped_section([t['section'] for t in items],native);blocks=set(section['blocks'])
            if blocks & (new_targets|earlier_targets):raise ValueError('New target overlaps completed experiment or another new target')
            new_targets|=blocks;key=f'{"c-recap" if stage==3 else "d-large"}-{number:02}-{source}'
            context='\n\n'.join(dict.fromkeys(t.get('context','') for t in items))
            secondary=secondary_span(folder,section['physical_pages']) if stage==4 else None
            pair(stage,key,source,section,context,'short_section' if stage==4 else 'production',ids[0],secondary=secondary)
            mapping.append({'key':key,'stage':stage,'original_tasks':[t['id'] for t in items],'blocks':section['blocks'],'pages':section['physical_pages'],
                            'native_characters':len(section['text']),'title':section['title'],'matched_control':None,
                            'scope':'new useful delivery; no matched speedup claim; target blocks once, shared page/context text labelled separately'})
            atomic_json(run/'comparisons'/(key+'.json'),mapping[-1])
    # Inputs needed for linked repairs stay separate from requests and controls.
    for key in ('bergomi-04','gatheral-07'):copy_source(PREVIOUS,key)
    repairs=prepare_repairs(run,old,consumed)
    environment=copy.deepcopy(old['compiler_environment']);shutil.copytree(PREVIOUS/environment['path'],run/environment['path'])
    for name in ('concurrency-runtime-binding.json','effort-support-offline.json','pending-grouping-opportunities.json'):
        shutil.copyfile(PREVIOUS/name,run/name);consumed[str(PREVIOUS/name)]=sha(PREVIOUS/name)
    historical={t['id']:suite.document_result(old,t) for t in old['tasks']}
    atomic_json(run/'historical-report/version-specific-results.json',historical)
    atomic_json(run/'production-handover.json',{'run':str(parent),'status':prod['status'],'calls':len(prod['calls']),
        'historical_calls':len(prod.get('historical_calls',[])),'counts':dict(Counter(t['status'] for t in ctrl.book.scheduled_tasks(prod))),
        'finished_suite':str(PREVIOUS),'suite_calls':len(old['calls']),'suite_counts':dict(Counter(t['status'] for t in old['tasks'])),
        'locks_free':True,'production_pointer_unchanged':True,'completed_input_reuse':'Exact consumed call seals, versions and file hashes verified; no replay/adoption'})
    atomic_json(run/'selection.json',mapping)
    source_checks(run)
    estimates=estimate(tasks,controls,old)
    manifest={'protocol':suite.OVERNIGHT,'created_at':runtime.now(),'parent':str(PREVIOUS),'production_parent':str(parent),
        'tasks':[suite.frozen_task(t) for t in tasks],'stage_order':list(ctrl.OVERNIGHT_STAGES),'stage_caps':dict(Counter(t['stage'] for t in tasks)),
        'maximum_work_generations':len(tasks),'reference_concurrency':2,'attempts_per_work_request':1,'controls':controls,
        'deadline':None,'generation_deadline':None,'connection_timeout_seconds':10,'readiness':'once per genuine launch/resume, zero after terminal',
        'final_status':suite.TERMINAL,'production_adoption':False,'estimates':estimates,'early_checkpoint':'first two larger units; nonblocking diagnostic, no replacement targets or automatic splitting'}
    suite.validate_manifest(manifest);atomic_json(run/'suite-manifest.json',manifest)
    state={'suite_protocol':suite.OVERNIGHT,'suite_manifest':manifest,'status':'prepared_offline','created_at':runtime.now(),
        'chapter_contract':'annotated-chapter-v1','timing_policy':'manual_only','execution_limits':{'calls':None,'attempts_per_unit':1},
        'first_dispatch':None,'calls':[],'historical_calls':[],'source_history':{'finished_experiment':str(PREVIOUS),'calls':len(old['calls']),'production':str(parent),'production_calls':len(prod['calls'])},
        'tasks':tasks,'current_versions':{},'versions':{},'accuracy':{},'accuracy_records':{},'connection_failures':0,
        'compiler_environment':environment,'phase_efforts':{'convert':'high','critic':'max'},'concurrency_policy':copy.deepcopy(ctrl.concurrent.POLICY),
        'active_stage':None,'reference_concurrency':None,'stage':'prepared','launches':[],
        'stages':{str(n):{'name':title,'status':'pending','sessions':[]} for n,title in ctrl.OVERNIGHT_STAGES.items()},
        'production_stage':{'task_ids':[t['id'] for t in tasks]},'acceptance':'EXPERIMENTAL_UNACCEPTED','scope':'Frozen overnight experiments; never enter production'}
    for key,text in saved.items():
        ctrl.book.remember(run,state,key,'saved-control-draft',text,{'source':'exact historical Max critic input; no corrections applied'})
        state['current_versions'][key]='saved-control-draft'
    inventory(run,state)
    own={str(p):sha(p) for name in ('inputs','bergomi/inputs','prepared','controls','comparisons') for p in (run/name).rglob('*') if p.is_file()}
    own[str(run/'suite-manifest.json')]=sha(run/'suite-manifest.json')
    for key in saved:
        v=state['versions'][key]['saved-control-draft'];own[str(run/v['path'])]=v['sha256']
    for row in repairs:own[str(run/row['path']/'document.tex')]=row['document_sha256']
    binding={'protocol':suite.OVERNIGHT,'code':ctrl.hashes(),'consumed':consumed,'prepared':own,'manifest_sha256':sha(run/'suite-manifest.json'),
             'compiler_environment':environment,'runtime_identity':read_json(run/'concurrency-runtime-binding.json')['identity']}
    atomic_json(run/'binding.json',binding);state['binding_sha256']=fingerprint(binding);runtime.save(run,state)
    ctrl.verify(run);ctrl.report(run,state);ctrl.bundle(run,state);atomic_json(POINTER,{'run':str(run)})
    print('PREPARED, NOT RUNNING:',run,'work requests:',len(tasks))
    return run


def estimate(tasks,controls,old):
    # Measured complete-chapter and substantial-section timings, not tiny-recap ETA.
    samples=[]
    for t in old['tasks']:
        if t['stage'] in (1,4) and t.get('call'):
            c=next(c for c in old['calls'] if c['id']==t['call']);n=len((t.get('section') or {}).get('text',''))
            if t['stage']==4:n=len((PREVIOUS/'inputs/klebaner-04/source.tex').read_text())
            samples.append({'phase':t['phase'],'characters':n,'seconds':c['elapsed_seconds'],'status':t['status']})
    result={}
    for stage in range(1,5):
        basis=[]
        for t in tasks:
            if t['stage']!=stage:continue
            control=controls.get(t['baseline']+'/'+t['phase']);n=len((t.get('section') or {}).get('text',''))
            if control:seconds=control['elapsed_seconds'];method='same historical Max or High control; new effort may differ'
            elif stage==3:seconds=500 if t['phase']=='convert' else 800;method='completed grouped recap observations; wide uncertainty'
            else:
                near=sorted((x for x in samples if x['phase']==t['phase']),key=lambda x:abs(x['characters']-n))[:3]
                seconds=sum(x['seconds']*max(.75,min(2,n/max(1,x['characters']))) for x in near)/len(near)
                method='nearest three substantial/chapter controls, size ratio bounded 0.75–2; not an exact forecast'
            basis.append({'task':t['id'],'source_characters':n,'seconds_basis':round(seconds,1),'method':method})
        seconds=sum(x['seconds_basis'] for x in basis)
        result[str(stage)]={'hours_range':[round(seconds/2*.65/3600,1),round(seconds*1.5/3600,1)],
                           'basis':basis,'central_two_slot_hours':round(seconds/2/3600,2),'note':'Planning only; batching, long reasoning, compiler work and serialization may exceed range. No deadline.'}
    return result


def inventory(run,state):
    for t in state['tasks']:
        if t['phase']!='convert':continue
        native=read_json(ctrl.source_folder(run,t['source_key'])/'native.json');selected=set(t['section']['blocks'])
        blocks=[b for b in native['blocks'] if b['id'] in selected];text=t['section']['text']
        atomic_json(run/'inventories'/(t['key']+'.json'),{'coverage':t['coverage'],'ordered_blocks':[b['id'] for b in blocks],
            'locators':[{'id':b['id'],'page':b['page'],'bbox_pdf_points':b.get('bbox_pdf_points'),'kind':b['kind']} for b in blocks],
            'kinds':dict(Counter(b['kind'] for b in blocks)),'headings':[b.get('tex','') for b in blocks if 'title' in b['kind']],
            'source_tags':re.findall(r'\\tag\{([^}]+)\}',text),'reference_locators':sorted(set(re.findall(r'\[\d+(?:[,–-]\d+)*\]',text))),
            'assets':sorted({a for b in blocks for a in b.get('assets',[])}),'limitation':'Inventories diagnose omissions, not proof of complete mathematics or hypotheses'})
        if t['stage']==4:
            from probe.saved_pages import render_region
            formulas=[b for b in blocks if b['kind']=='equation']
            chosen=(formulas or blocks)[len(formulas or blocks)//2];page=chosen['page']['original_physical_page']
            image=run/'source-checks'/f'bergomi-p{page}.png'
            if not image.exists():render_region(ROOT/'inputs/bergomi/source.pdf',page-1,image,max_edge=2100)
            atomic_json(run/'source-checks'/(t['key']+'.json'),{'task':t['id'],'page':page,'block':chosen['id'],
                'image':image.name,'reason':'Representative middle formula/region for future independent inspection; not already assessed'})


def source_checks(run):
    folder=run/'source-checks';folder.mkdir()
    shutil.copyfile(ROOT/'docs/evidence/overnight-source-checks-20261029.md',folder/'assessment.md')
    from probe.saved_pages import render_region
    for book,pages in (('bergomi',[113,151,154,155,212,317,368,403]),('klebaner-original',[122,131]),('gatheral',[128])):
        for p in pages:render_region(ROOT/'inputs'/book/'source.pdf',p-1,folder/f'{book}-p{p}.png',max_edge=2000)
    (folder/'future-checks.md').write_text('New overnight outputs have NOT been source-checked. Compare source blocks/crops, conditions, signs, powers, references and unresolved notes; inspect unchanged controls as well as proposed corrections. Exact original page locators and source PDF identities are in inventories/ and provenance. No answers from this folder enter requests.\n')
