"""Human-readable chapter notes with conservative, program-owned continuity.

No model schema is required. Unparsed material is retained; silence never closes
an issue. A mechanically evidenced source-text edit may close a transcription
item, but free-form mathematical resolution claims remain for inspection.
"""
import copy
import difflib
import re
from pathlib import Path

from .common import atomic_json, sha, fingerprint


def envelope(answer, legacy_extractor):
    """Reuse existing extraction, also allowing unrelated fenced notes/snippets."""
    draft, info = legacy_extractor(answer)
    if draft is not None and info['status'] != 'unfenced': return draft, info
    fences = list(re.finditer(r'(?m)^ {0,3}(`{3,}|~{3,})([^\r\n]*)(?:\r?\n|$)', answer))
    candidates = []; inside = None
    for match in fences:
        if inside is None: inside = match; continue
        if match[1] == inside[1] and not match[2].strip():
            body = answer[inside.end():match.start()]
            if inside[2].strip().lower() in ('', 'tex', 'latex') and complete_document(body):
                candidates.append((body, inside, match))
            inside = None
    if len(candidates) == 1:
        body, first, last = candidates[0]
        outside = answer[:first.start()] + answer[last.end():]
        if r'\documentclass' not in outside and r'\begin{document}' not in outside:
            return body, {'status': 'single_fenced_document', 'start': first.end(), 'end': last.start(),
                          'intro_end': first.start(), 'notes_start': last.end(), 'content_change': 'none; exact slice'}
    if fences: return draft, info
    # A complete unfenced file with prose before/after still has a unique boundary.
    start = answer.find(r'\documentclass'); end = answer.find(r'\end{document}')
    if start >= 0 and end >= start and complete_document(answer):
        end += len(r'\end{document}')
        return answer[start:end], {'status': 'unfenced_document', 'start': start, 'end': end,
                                  'intro_end': start, 'notes_start': end, 'content_change': 'none; exact slice'}
    return draft, info


def complete_document(text):
    return all(text.count(t) == 1 for t in (r'\documentclass', r'\begin{document}', r'\end{document}'))


def outside_notes(answer, info):
    if info.get('status') in ('ambiguous', 'unfenced'): return '', 'unavailable_unparsed'
    prefix = answer[:info.get('intro_end', 0)].strip()
    suffix = answer[info.get('notes_start', len(answer)):].strip()
    # Introductory prose is still retained in the raw answer. Include it as notes
    # only when it identifies actual notes, not merely "Here is the document".
    if not suffix and re.search(r'(?i)accuracy|conversion notes|remarks|material (?:issues|corrections)', prefix): suffix = prefix
    return suffix, 'captured' if suffix else 'unavailable'


def field(text, name):
    match = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?' + re.escape(name) + r'(?:\*\*)?\s*:\s*(.+)', text)
    return match[1].strip().strip('`').strip('"') if match else None


def entries(text):
    """Whole Markdown entries only; never split mathematical prose by punctuation."""
    headings = list(re.finditer(r'(?m)^#{2,6}\s+.+$', text))
    starts = [m.start() for m in headings if not re.search(r'(?i)^#+\s*(accuracy|conversion) notes\s*$', m[0])]
    if not starts: starts = [m.start() for m in re.finditer(r'(?m)^[-*]\s+', text)]
    if not starts: return [text.strip()] if text.strip() else []
    prefix = text[:starts[0]].strip()
    result = [text[a:b].strip() for a,b in zip(starts,starts[1:]+[len(text)])]
    if prefix and not re.fullmatch(r'(?is)[#*\s]*(?:accuracy notes|conversion notes|a few remarks[^\n]*|a few remarks on choices made during conversion:)[:*\s]*',prefix):
        result.insert(0,prefix)
    return result


def category(text):
    # Explicitly positive/presentation entries are not an actionable issue queue.
    # Unknown free-form notes stay visible; no confidence/length-based suppression.
    plain = re.sub(r'^[#*\-\s]+', '', text).replace('**', '')
    if re.match(r'(?i)^(?:structure|numbering|equation numbering|figures|images|no figures/captions|footnotes?)\b',plain) and not re.search(r'(?i)error|missing|incorrect|omitt|repair|inconsisten|lost|uncertain|scrambl|reassembl|reconstruct',text):
        return 'presentation_or_positive'
    if re.search(r'(?i)error|missing|incorrect|omitt|repair|inconsisten|lost|uncertain|footnote|correction|source inspection|source-image|hypothes|reference|coefficient|sign\b|bound\b',text):
        return 'accuracy'
    return 'unclassified_preserved'


def capture(key, phase, text, *, capture_status='captured', complete=True, origin=None):
    status = 'review_incomplete' if not complete else capture_status
    clear = bool(re.fullmatch(r'(?is)\s*(?:#+\s*accuracy notes\s*)?(?:\*\*)?No material issues (?:reported(?: by the model)?|detected|found)(?:\*\*)?[.!]?\s*',text))
    if complete and clear: status = 'no_material_issues_reported_by_model'
    items=[];seen={}
    if text.strip() and not clear and complete:
        for entry in entries(text):
            normalized=' '.join(entry.split())
            if normalized in seen:
                seen[normalized]['duplicate_occurrences']+=1;continue
            ident=key+'-'+phase+'-'+fingerprint(entry)[:10]
            item={'id':ident,'text':entry,'category':category(entry),'status':'open',
                  'location':field(entry,'Location'),'origin':field(entry,'Origin') or 'uncertain',
                  'model_claimed_status':field(entry,'Status'),'evidence':field(entry,'Evidence'),
                  'correction':field(entry,'Correction'),'duplicate_occurrences':1}
            if re.search(r'(?i)requires? source (?:inspection|image)',entry):item['status']='requires_source_inspection'
            if item['category']=='presentation_or_positive':item['status']='informational'
            items.append(item);seen[normalized]=item
    if complete and text.strip() and not clear and capture_status=='captured' and not any(re.search(r'(?im)^\s*(?:#{1,6}|[-*])\s+|\b(?:Location|Evidence|Status|Correction):',e['text']) for e in items):
        status='captured_unparsed'
    return {'chapter':key,'phase':phase,'notes_status':status,'review_complete':complete,
            'origin':origin,'raw_notes':text,'issues':items,'fidelity':'Model claims, not mathematical certification'}


def render(record, *, provenance=True):
    out=['# '+record['chapter']+' — '+record['phase']+' accuracy notes',
         'Capture status: '+record['notes_status'],
         'Model claims; not mathematical certification.']
    if provenance and record.get('origin'):out.append('Provenance: '+str(record['origin']))
    if record['notes_status']=='no_material_issues_reported_by_model':out.append('No material issues reported by the model.')
    if 'unavailable' in record['notes_status']:out.append('Accuracy notes unavailable/unparsed. This does not mean no issues.')
    if not record['review_complete']:out.append('Review incomplete or failed. Previous open issues remain open.')
    for item in record['issues']:
        if item['category']=='presentation_or_positive':continue
        out += ['## '+item['id'], 'Status: '+item['status'],item['text']]
        out += ['Critic update: '+v['text'] for v in item.get('critic_updates',[])]
        out += item.get('resolution_limitations',[])
        if item.get('resolution'):out.append('Resolution evidence: '+str(item['resolution']))
    minor=[i for i in record['issues'] if i['category']=='presentation_or_positive']
    if minor:
        out+=['<details><summary>Retained presentation/positive observations (not actionable issues)</summary>']
        out += [i['text'] for i in minor];out+=['</details>']
    return '\n\n'.join(out)+'\n'


def reconcile(initial, latest, *, sources, before, after=None):
    result=copy.deepcopy(latest);result['issues']=copy.deepcopy(initial['issues']);links=[]
    for entry in latest['issues']:
        if entry['category']=='presentation_or_positive':result['issues'].append(entry);continue
        named=field(entry['text'],'Resolves')
        refs=[i for i in result['issues'] if i['id'] in entry['text'] or
              (named and named==re.sub(r'^[#*\-\s]+','',i['text'].splitlines()[0]).strip('*: '))]
        if len(refs)==1:
            prior=refs[0];prior.setdefault('critic_updates',[]).append(entry)
            quote=field(entry['text'],'Source quote');old=field(entry['text'],'Old');new=field(entry['text'],'New')
            claimed=(field(entry['text'],'Status') or '').lower().startswith('resolved')
            supported=(latest['review_complete'] and claimed and quote and quote.strip() and any(quote in source for source in sources)
                       and old and new and old!=new and after is not None and old in before and new in after
                       and (field(entry['text'],'Origin') or '').lower() in ('extraction','transcription','extraction/transcription')
                       and before.count(old)==1 and after.count(old)==0 and after.count(quote)==1
                       and quote not in before and quote in before.replace(old,new)
                       and new in quote and new!=quote)
            if supported:
                prior['status']='resolved_with_source_evidence'
                prior['resolution']={'source_quote':quote,'old':old,'new':new,'critic_entry':entry['id'],
                                     'qualification':'Exact source quote and document edit checked; mathematical correctness not certified'}
            else:
                prior.setdefault('resolution_limitations',[]).append('Carried forward: no unambiguous exact-source-supported edit; free-form claims/derivations remain unverified')
            links.append({'initial':prior['id'],'critic':entry['id']})
        else:
            result['issues'].append(entry)  # ambiguous/new findings remain visible
    result['linked_updates']=links
    result['prior_notes_status']=initial['notes_status']
    result['open_issues']=[i['id'] for i in result['issues'] if i['status'] in ('open','requires_source_inspection')]
    return result


def write_record(folder, name, record):
    folder.mkdir(parents=True,exist_ok=True)
    paths=[folder/(name+'.json'),folder/(name+'.md')]
    if any(p.exists() for p in paths):raise ValueError('Refusing to overwrite accuracy-note version: '+name)
    atomic_json(paths[0],record);paths[1].write_text(render(record),encoding='utf-8')
    return {p.name:sha(p) for p in paths}


def save_initial(run, key, text, *, status='captured', origin=None):
    record=capture(key,'initial',text,capture_status=status,origin=origin)
    folder=run/'chapters'/key
    hashes=write_record(folder,'accuracy-initial',record)
    return record, {str((folder/n).relative_to(run)):digest for n,digest in hashes.items()}


def save_review(run, key, initial, answer, info, *, complete, before, after, sources, origin=None):
    if not complete:text=answer;status='review_incomplete'
    elif after is not None:text,status=outside_notes(answer,info)
    elif info.get('status')=='ambiguous':
        from .chapter_editorial import notes_text
        text,status=notes_text(answer,info)
    else:text=answer;status='captured' if text.strip() else 'unavailable'
    latest=capture(key,'critic',text,capture_status=status,complete=complete,origin=origin)
    merged=reconcile(initial,latest,sources=sources,before=before,after=after)
    folder=run/'chapters'/key;hashes=write_record(folder,'accuracy-post-critic',merged)
    raw=folder/'critic-accuracy.raw.md';raw.write_text(text,encoding='utf-8');hashes[raw.name]=sha(raw)
    diff=''.join(difflib.unified_diff(before.splitlines(keepends=True),(after if after is not None else before).splitlines(keepends=True),fromfile='initial.tex',tofile='revised.tex'))
    delta=folder/'initial-to-revised.diff';delta.write_text(diff,encoding='utf-8');hashes[delta.name]=sha(delta)
    material=folder/'material-changes.md'
    material.write_text('# Material-change record\n\n'+
        ('Review incomplete; initial TeX preserved.\n\n' if not complete else '')+
        ('A separate revised document was supplied. It is an experimental working derivative, not certified.\n\n' if after is not None else
         'No complete revised TeX supplied; initial TeX remains current. This is not a claim that proposed changes were applied.\n\n')+
        'The full mechanical diff is initial-to-revised.diff; it may include cosmetic changes and is not semantic verification.\n\n'+
        '\n\n'.join(i['text'] for i in latest['issues'] if i['category']!='presentation_or_positive')+'\n',encoding='utf-8')
    hashes[material.name]=sha(material)
    revision_status=folder/'revised-tex-status.md'
    revision_status.write_text('Separate revised TeX supplied; see the critic version in the run inventory.\n' if after is not None else
                               'Revised TeX not supplied as a complete successful document. Initial TeX is preserved unchanged.\n',encoding='utf-8')
    hashes[revision_status.name]=sha(revision_status)
    return merged,{str((folder/n).relative_to(run)):digest for n,digest in hashes.items()}
