"""Saved-output repair and explicit remaining-book admission, without inference."""
import re
from pathlib import Path
from .common import read_json, sha
from . import chapter_editorial as edit


def remaining_bergomi(state, run):
    """Adopt identical completed targets; never dispatch a stale pending duplicate."""
    groups={}; reconciliation=[]; canonical=[]; scheduled=[]
    for task in state['tasks']:
        if task['source_key'].startswith('bergomi-'):
            groups.setdefault((task['key'],task['phase']),[]).append(task)
    for (key,phase),tasks in groups.items():
        for task in tasks[1:]:
            if any(task.get(f)!=tasks[0].get(f) for f in ('source_key','section','context','draft_label')):
                raise ValueError('Conflicting repeated Bergomi target: '+key)
        completed=[t for t in tasks if t['status'] in ('conversion_completed','critic_revised','critic_unchanged')]
        if len(completed)>1:raise ValueError('Multiple completed versions need explicit selection: '+key)
        if completed:
            chosen=completed[0]
            call=next(c for c in state['calls'] if c['id']==chosen['call'])
            body=read_json(Path(call.get('inherited_from',run))/'calls'/call['id']/'request.json')
            expected={'model':'glm53-regular','max_tokens':131072,'stream':True,
                      'reasoning_effort':'high' if phase=='convert' else 'max'}
            if any(body.get(k)!=v for k,v in expected.items()):raise ValueError('Completed Bergomi configuration differs')
            for duplicate in tasks:
                if duplicate is chosen:continue
                if duplicate['status']!='pending' or any(c['parent']==duplicate['id'] for c in state['calls']):
                    raise ValueError('Duplicate target has consumed or uncertain attempt')
                duplicate.update(status='adopted_completed',adopted_task=chosen['id'],adopted_call=call['id'])
                reconciliation.append({'stale_task':duplicate['id'],'completed_task':chosen['id'],
                    'call':call['id'],'request_sha256':sha(Path(call.get('inherited_from',run))/'calls'/call['id']/'request.json'),
                    'target_and_context_identical':True,'settings':expected})
        else:
            if len(tasks)!=1:raise ValueError('Duplicate uncompleted target: '+key)
            chosen=tasks[0]
            if chosen['status']!='pending' or any(c['parent']==chosen['id'] for c in state['calls']):
                raise ValueError('Uncompleted target requires explicit interrupted/failed-attempt disposition: '+key)
            chosen['reasoning_effort']='high' if phase=='convert' else 'max'
            scheduled.append(chosen)
        canonical.append(chosen)
    pairs=[(t['key'],t['phase']) for t in scheduled]
    if any(pairs[i][0]!=pairs[i+1][0] or pairs[i][1]!='convert' or pairs[i+1][1]!='critic' for i in range(0,len(pairs),2)):
        raise ValueError('Bergomi must keep conversion/immediate critic order')
    return canonical,scheduled,reconciliation


def notes_from_visible_dispositions(key, document):
    """Read an observed explicit TeX disposition list; no semantic guessing."""
    pattern=r'\\item\s+\\textbf\{\[([^\]]+)\]\}\s*---\s*([^:]+):\s*'
    matches=list(re.finditer(pattern,document));items=[]
    for i,m in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else document.find(r'\end{itemize}',m.end())
        if end<0:raise ValueError('Unclosed saved disposition list')
        text=document[m.end():end].strip();claim=m[2].strip()
        status='open' if re.search(r'\bopen\b|unresolved',claim,re.I) else 'applied_claim_unverified' if 'applied' in claim else 'informational'
        items.append({'id':m[1] if 'call-' in m[1] else key+'-critic-variance-note',
                      'text':text,'claimed_status':claim,'status':status,
                      'category':'material' if status!='informational' else 'contextual_observation',
                      'attribution':'GLM','independent_verification':False})
    if not items:raise ValueError('Expected explicit saved dispositions absent')
    return items


def reference_inventory(document, supplied_assets, image_references):
    """Mechanical linkage only; literal equation numbers are not validated."""
    labels=re.findall(r'\\label\{([^}]+)\}',document)
    refs=re.findall(r'\\(?:eqref|ref|pageref|autoref)\{([^}]+)\}',document)
    figures=image_references(document)
    return {'undefined_labels':sorted(set(refs)-set(labels)),
            'duplicate_labels':sorted({x for x in labels if labels.count(x)>1}),
            'missing_assets':sorted(set(figures)-set(supplied_assets)),
            'literal_locators':re.findall(r'\b(?:Section|Chapter|Figure|Table|Eq\.|equation)\s*~?\s*\(?\d+(?:\.\d+)*\)?',document),
            'limit':'Literal numbers, bibliography attributions and cross-part semantics require source checking; compilation does not verify them.'}


def edition_summary(rows):
    retained=[r for r in rows if r.get('version')]
    gaps=[r['key'] for r in rows if not r.get('pdf_included')]
    return {'planned_parts':len(rows),'retained_content_parts':len(retained),
            'compiled_pdf_parts':sum(bool(r.get('pdf_included')) for r in rows),
            'missing_content':[r['key'] for r in rows if not r.get('version')],
            'pdf_gaps':gaps,'complete_part_delivery':not gaps,
            'semantic_completeness':'not established','independent_verification':'per finding only; not established for complete parts'}
