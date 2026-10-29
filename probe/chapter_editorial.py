"""Opt-in annotated chapter derivatives; no rewriting of historical evidence."""
import copy
import re
from pathlib import Path
from .common import fingerprint
from . import chapter_accuracy as accuracy, chapter_sources as sources

VERSION = 'annotated-chapter-v1'
POLICY = '''Produce an annotated, mathematically reliable edition for a knowledge
base. Errors originating in the published source deserve correction
just as much as extraction errors.

Apply well-supported mathematical and factual corrections directly
to the revised LaTeX. Add a concise, clearly labelled “GLM editorial
correction” note explaining each material change.

When a correction follows from the document’s explicit definitions
or a short local derivation, do not leave it unapplied merely because
an unstated alternative convention could hypothetically explain
the error.

For genuinely unresolved cases, preserve the passage and insert a
“GLM unresolved issue” note stating the problem and the evidence
needed. Do not present a speculative explanation as established.

Include every material finding in the annotated document and
accuracy log. Ignore cosmetic preferences. Preserve the original
draft separately.'''


EFFORTS=('none','low','medium','high','max')


def validate_effort(effort):
    if effort not in EFFORTS:raise ValueError('Unsupported chapter reasoning effort: '+repr(effort)+'; choose '+', '.join(EFFORTS))
    return effort


def request(primary, secondary, *, draft=None, notes='', section=None, context='', reasoning_effort='max'):
    validate_effort(reasoning_effort)
    instruction = POLICY + '\n' + sources.MEANING + '\n' + sources.SOURCE_POLICY
    instruction += ('\nUse short visible TeX notes, not comments alone: original reading, correction or unresolved issue, '
        'locator, and short supporting argument. Link material findings in the Markdown accuracy log to these notes. '
        'Do not attribute supplied Codex/ChatGPT corrections or publisher metadata to GLM. '
        'Keep all supplied relative assets. Return one usable complete fenced LaTeX document and short accuracy notes. '
        'Record uncertainty once and continue; do not draft the entire document repeatedly inside reasoning. '
        'Deliver the complete transcription even when a printed-source mathematical issue remains unresolved; '
        'preserve and visibly flag that passage rather than withhold the section. ')
    if draft is not None:
        instruction += ('\nCritic: apply or annotate the finite findings below using this draft and both sources. '
            'Check substantive local consistency and preservation; do not repeat conversion or re-prove every theorem. '
            'If the document already includes all necessary corrections and visible unresolved notes, findings alone are sufficient. '
            'State which findings are applied, unresolved, contextual or cosmetic. Never call a speculative explanation established. ')
    if section:
        instruction += ('\nProduce ONLY the coherent output section specified below, as a standalone LaTeX document. '
            'The complete chapter is context, not an instruction to emit other sections. Preserve this section\'s content, '
            'numbering, captions and references. Do not add a chapter summary or invent bridging content.\nOUTPUT SECTION:\n'+section)
    text = instruction+'\n\nPRIMARY EXTRACTION — native MinerU:\n'+primary
    text += '\n\nSECONDARY EXTRACTION — native PDF text with physical page locators:\n'+secondary
    if context: text += '\n\nAVAILABLE SAME-EDITION CONTEXT (unreviewed extraction unless labelled):\n'+context
    if draft is not None:text += '\n\nCURRENT DRAFT:\n'+draft+'\n\nFINITE FINDINGS / ACCURACY LOG (attribution retained):\n'+notes
    return {'model':'glm53-regular','messages':[{'role':'user','content':text}], 'max_tokens':131072,'stream':True,
            'reasoning_effort':reasoning_effort}


def current_version(state, key):
    """A successful findings-only review retains its complete conversion document."""
    versions=state.get('versions',{}).get(key,{})
    explicit=state.get('current_versions',{}).get(key)
    if explicit in versions:return explicit, versions[explicit]
    review=next((t for t in state.get('tasks',[]) if t.get('key')==key and t.get('phase')=='review'),{})
    label=review.get('revised_tex',{}).get('version')
    if label in versions:return label, versions[label]
    if 'first-glm' in versions:return 'first-glm',versions['first-glm']
    return None,None


def notes_text(answer, info=None):
    """Accept standalone fenced Markdown notes; never synthesize notes from reasoning."""
    if info and info.get('status') not in ('ambiguous','unfenced'):
        text,status=accuracy.outside_notes(answer,info)
        if text.strip():return text,status
    if not answer.strip():return '', 'unavailable'
    if r'\documentclass' in answer or r'\begin{document}' in answer:
        return answer,'unavailable_unparsed'
    # The entire raw final answer is retained elsewhere, including text outside fences.
    fences=list(re.finditer(r'(?ms)^```(?:markdown|md)\s*\n(.*?)^```\s*$',answer))
    if len(fences)==1 and re.search(r'(?i)accuracy|issue|review|finding',answer):return fences[0][1],'captured'
    return answer,'captured'


def note_entries(text):
    """Recognized item boundaries only, not sentence splitting or field bullets."""
    if text.startswith('**Critic dispositions.**'):
        # An observed compact log uses explicit disposition fields in one
        # paragraph. A cosmetic field must not swallow unrelated mathematics.
        text=text.removeprefix('**Critic dispositions.**').strip()
        fields=r'(?=\b(?:Applied and verified:|Unresolved \(open, preserved as printed\):|Contextual:|Cosmetic:|One new derivation-forced fix))'
        return [x.strip() for x in re.split(fields,text) if x.strip()]
    patterns=[r'(?m)^\*\*(?:[A-Z]\d+[.)]|\d+[.)])[^\n]+',r'(?m)^\d+[.)]\s+[^\n]+',
              r'(?m)^-\s+\*\*(?!(?:Evidence|Correction|Status|Location|Reason):)[^\n]+',
              r'(?m)^[-*]\s+\*\*\[[^\]\n]+\][^\n]*',
              r'(?m)^\*\*(?:Applied|Resolved|Unresolved|Cosmetic|Verified|Material correction|No other issues|Locations needing)[^\n]*',
              r'(?m)^-\s+\*\*(?:Contextual|Mechanical|Cosmetic)[^\n]*',
              r'(?m)^-\s+\*\*(?:[a-z]+-[\w-]+|[A-Z]\d+)[^\n]+',
              r'(?m)^#{2,6}\s+(?!Accuracy notes|Updated accuracy|Existing open)[^\n]+']
    starts=sorted(set(m.start() for pattern in patterns for m in re.finditer(pattern,text)))
    # Explicit M1 followed by individual prior-issue bullets must all survive.
    if not starts:return [text.strip()] if text.strip() else []
    result=[text[a:b].strip() for a,b in zip(starts,starts[1:]+[len(text)])]
    prefix=text[:starts[0]].strip()
    if prefix:result.insert(0,prefix)
    return result


def note_furniture(text):
    """Only empty separators / accuracy-log headings, never substantive claims."""
    lines=[x.strip() for x in text.replace('**','').splitlines() if x.strip()]
    return bool(lines) and all(re.fullmatch(r'[-_*]{3,}',x) or
        re.fullmatch(r'(?:#{1,6}\s*)?(?:Updated )?Accuracy (?:log|notes)(?:\s*[—(].*)?',x,re.I) for x in lines)


def notes_record(key, text, *, captured='captured', complete=True, attribution='GLM', phase='critic'):
    items=[];section_status=''
    entries=note_entries(text) if captured=='captured' else []
    for entry in entries:
        clean=entry.replace('**','')
        if note_furniture(entry):continue
        if re.match(r'^(Applied|Resolved|Unresolved|Cosmetic|Verified|Material correction)\b',clean):
            section_status=clean.splitlines()[0]
            if len(clean.splitlines())==1 and clean.endswith(':') and not clean.startswith('Unresolved (open, preserved as printed):'):continue
            if len(clean.splitlines())==1 and re.fullmatch(r'(Applied|Resolved|Unresolved|Cosmetic)(?:\s*\([^\n]*\))?',clean):continue
        statuses=re.findall(r'(?i)\bStatus:\s*([^\n]+)',clean)
        claimed=statuses[-1].strip() if statuses else (clean.splitlines()[0] if re.search(r'(?i)resolved|corrected|verified|informational|applied|retained',clean.splitlines()[0]) else section_status)
        leading=re.match(r'^(?:[-*]\s+|\d+[.)]\s+)?\*\*([^\n]+?)\*\*',entry)
        if not statuses and leading and re.search(r'(?i)\b(applied|resolved|unresolved|verified|informational|open)\b',leading[1]):
            claimed=leading[1]  # discussion may quote earlier, superseded uncertainty
        # Explicit mixed states remain mixed/open, never closed by a final summary.
        status_words=re.sub(r'(?i)no unresolved issues','',claimed)
        open_claim=bool(re.search(r'(?i)\bopen\b|requires[- ]source|unresolved',status_words))
        resolved=bool(re.search(r'(?i)\bresolved\b|\bverified\b',claimed)) and not open_claim
        if re.search(r'(?i)no (?:new |other )?(?:material |unresolved )?(?:issues|corrections)|^\s*#.*accuracy (?:notes|log)|^\s*(?:review outcome|capture status|Contextual:)|^-\s*Contextual, no change',clean):kind='contextual_observation'
        elif re.search(r'(?i)(usual.*unusual|wording preference|cosmetic|hyphen.*Risk|Risk.*hyphen|scattered diacritics)',clean.splitlines()[0]):kind='cosmetic'
        elif re.search(r'(?i)\(scope\)|scope.*76 entries|not an error|not a discrepancy|not defects|unchanged, informational|carried-over verifications|^.*Completeness:',clean):kind='contextual_observation'
        elif not open_claim and re.search(r'(?i)verified, no change|first-order consistency check; no change|^\s*(?:\d+[.)]\s*)?Preservation\b',clean.splitlines()[0]):kind='contextual_observation'
        else:kind='material'
        if not open_claim and re.search(r'(?i)informational|no action|verified, no change',claimed):kind='contextual_observation'
        status=('review_incomplete' if not complete else 'resolved_claim_unverified' if resolved else
                'open' if kind=='material' else 'informational')
        if complete and re.search(r'(?i)correction.*(?:→|->)|material correction|restored.*resolved',clean) and resolved:status='applied_claim_unverified'
        if complete and re.search(r'(?i)\bapplied\b|\bretained\b',claimed) and not open_claim:status='applied_claim_unverified'
        if complete and clean.startswith('- Mechanical fixes:'):status='applied_claim_unverified'
        if kind!='material':status='informational' if complete else 'review_incomplete'
        label=re.search(r'^[-*]\s+\*\*\[([^\]]+)\]',entry)
        refs=re.findall(r'\bG\d+-[A-Za-z]+\b|\b[a-f0-9]{10}\b',label[1] if label else '')
        refs+=re.findall(r'\b[\w-]+-(?:convert|critic)-call-\d+-[a-f0-9]{10}\b',entry)
        refs+=re.findall(r'`[^`\n]*?-([a-f0-9]{10})`',entry)
        items.append({'id':key+'-'+phase+'-'+fingerprint(entry)[:10], 'text':entry,'category':kind,'status':status,
                      'references':refs,'claimed_status':claimed or None,'attribution':attribution,'independent_verification':False})
    return {'chapter':key,'version':VERSION,'phase':phase,'capture_status':captured if complete else 'review_incomplete',
            'raw_notes':text,'items':items,'certification':False}


def reconcile_notes(before, latest):
    """Keep prior items unless explicitly addressed; claim and verification are separate."""
    result=copy.deepcopy(latest);result['items']=[];matched=set();history=copy.deepcopy(before.get('history',[]))
    for prior in before.get('items',[]):
        aliases=set(prior.get('references',[]))|{prior['id']}
        if re.search(r'-[a-f0-9]{10}$',prior['id']):aliases.add(prior['id'].split('-')[-1])
        updates=[x for x in latest['items'] if (len(prior['id'])>25 and prior['id'] in x['text']) or aliases.intersection(x.get('references',[]))]
        if len(updates)==1:
            entry=copy.deepcopy(updates[0]);history.append(dict(prior,superseded_by=entry['id']))
            # No supporting discussion means an ignored/unsupported "fixed" stays open.
            if re.fullmatch(r'(?is)[\s#*\w:.-]*'+re.escape(prior['id'])+r'[\s:.-]*(?:fixed|resolved)[.!\s]*',entry['text']):entry['status']='open'
            if entry['id'] not in matched:result['items'].append(entry)
            matched.add(entry['id'])
        else:result['items'].append(copy.deepcopy(prior))
    result['items'] += [x for x in latest['items'] if x['id'] not in matched]
    result['items']=list({x['id']:x for x in result['items']}.values())
    result['history']=history
    return result


def tex_escape(text):
    import unicodedata
    special={'\\':r'\textbackslash{}','{':r'\{','}':r'\}','%':r'\%','&':r'\&','#':r'\#','_':r'\_',
             '$':r'\$','~':r'\textasciitilde{}','^':r'\textasciicircum{}'}
    math={'Δ':'Delta','α':'alpha','β':'beta','γ':'gamma','δ':'delta','ε':'epsilon','κ':'kappa','η':'eta','θ':'theta','λ':'lambda','μ':'mu','ν':'nu','π':'pi','ρ':'rho',
          'σ':'sigma','τ':'tau','υ':'upsilon','φ':'phi','ϕ':'varphi','ψ':'psi','→':'rightarrow','⇒':'Rightarrow','∂':'partial',
          '−':'-','√':'surd','∞':'infty','∫':'int','∼':'sim','≈':'approx','≠':'ne','×':'times','′':'prime'}
    out=[]
    for c in text:
        if c in special:out.append(special[c])
        elif c in math:out.append(r'\ensuremath{'+('\\' if math[c].isalpha() else '')+math[c]+'}')
        elif c in '₀₁₂₃₄₅₆₇₈₉':out.append(r'\ensuremath{_{'+str('₀₁₂₃₄₅₆₇₈₉'.index(c))+'}}')
        elif c in '⁰¹²³⁴⁵⁶⁷⁸⁹':out.append(r'\ensuremath{^{'+str('⁰¹²³⁴⁵⁶⁷⁸⁹'.index(c))+'}}')
        elif c in '⁽⁾':out.append(r'\ensuremath{^{'+('(' if c=='⁽' else ')')+'}}')
        elif c=='\u0304' and out:out[-1]=r'\ensuremath{\overline{\text{'+out[-1]+'}}}'
        elif ord(c)>255 and c not in '–—…':out.append('['+unicodedata.name(c,'unrendered character').lower()+']')
        else:out.append(c)
    return ''.join(out)


def metadata_tex(text):
    """Escape generated navigation only; preserve source/TeX and raw metadata."""
    safe=''.join('[control U+%04X]'%ord(c) if (ord(c)<32 and c not in '\n\t') or ord(c)==127 else c for c in str(text))
    return tex_escape(safe)


def annotation(entry):
    label=entry.get('label',entry.get('attribution','Codex')+' accuracy finding (see disposition)')
    if entry['status'].startswith('applied'):label=entry.get('attribution','Codex')+' editorial correction (recorded claim)'
    if entry['status'] in ('open','unresolved','requires_source_inspection'):label=entry.get('attribution','Codex')+' unresolved issue'
    body=entry.get('note_tex') or tex_escape(entry.get('text',''))
    return '\n\\par\\smallskip\\noindent\\textbf{'+tex_escape(label)+' ['+tex_escape(entry['id'])+'].} '+body+'\n\\par\\smallskip\n'


def annotate(document, entries):
    if not accuracy.complete_document(document):raise ValueError('Cannot annotate an incomplete document')
    appendix='\n\\clearpage\n\\section*{Editorial corrections and unresolved issues}\n'
    visible=[e for e in entries if e.get('category','material')=='material' and
             e.get('status')!='superseded_with_recorded_disposition' and
             not any(ref in document for ref in [e['id'],*e.get('references',[])]) and
             not linked_visible_note(document,e)]
    if not visible:return document
    appendix+='\n'.join(annotation(e) for e in visible)
    return document.replace(r'\end{document}',appendix+'\n'+r'\end{document}')


def linked_visible_note(document, entry):
    """Only an explicit quoted note label matches; never infer semantic resolution."""
    labels=re.findall(r'(?i)(?:TeX note|document note)\s*[“\"]([^”\"\n]+)[”\"]',entry.get('text',''))
    normalized=' '.join(document.split())
    return any(' '.join(label.split()) in normalized for label in labels if label.startswith(('GLM ', 'Codex ')))


def apply_edits(document, plan):
    """Hash-bound whole strings, no fuzzy matches or implicit substring interpretation."""
    if fingerprint(document)!=plan['text_fingerprint']:raise ValueError('Editorial source version changed')
    result=document
    for edit in plan.get('edits',[]):
        old,new=edit['old'],edit['new']
        if not old or result.count(old)!=1:raise ValueError('Ambiguous/missing editorial edit: '+edit['id'])
        result=result.replace(old,new,1)
    return result


def section_groups(data):
    """Whole native blocks between major numbered sections. Never clip a proof."""
    blocks=[b for b in data['blocks'] if b['kind'] not in ('header','footer','page_number')]
    from .chapter_inputs import strings
    starts=[0];headings={0:'Opening section'};proof=False
    for i,b in enumerate(blocks):
        title=' '.join(v for _,v in strings(b['native'])).strip()
        if re.match(r'(?i)^proof\b',title):proof=True
        if re.search(r'\\(?:Box|square|blacksquare)\b|[□∎]|\bQ\.?E\.?D\.?$',title):proof=False
        numbered=bool(re.match(r'^\d+\.\d+(?!\.)\s+\S',title))
        major=(b['kind']=='paragraph_title' and b['native'].get('level',2)<=2 and
               not re.match(r'(?i)^(proof|theorem|lemma|example|remark|definition|proposition|corollary)\b',title) and
               not b['native'].get('continues_prev') and (numbered or title.isupper()))
        if i and major:starts.append(i);headings[i]=title;proof=False
    # The opening title/introduction belongs with the first substantive section,
    # not a trivial standalone pilot request. Major headings end prior sections.
    if len(starts)>1 and headings[0]=='Opening section':
        headings[0]=headings[starts[1]]+' (including chapter introduction)'
        starts.pop(1)
    groups=[]
    for a,z in zip(starts,starts[1:]+[len(blocks)]):
        subset=blocks[a:z]
        groups.append({'title':headings[a],'first':subset[0]['id'],'last':subset[-1]['id'],
            'blocks':[b['id'] for b in subset], 'physical_pages':sorted(set(b['page']['original_physical_page'] for b in subset)),
            'text':'\n\n'.join(b['tex'] for b in subset),
            'boundary_status':'observed major heading; whole native blocks, no semantic completeness certification'})
    if len(groups)>1 and groups[-1]['title'].upper().endswith('SUMMARY'):
        tail=groups.pop();groups[-1]['blocks']+=tail['blocks'];groups[-1]['last']=tail['last']
        groups[-1]['text']+='\n\n'+tail['text'];groups[-1]['physical_pages']=sorted(set(groups[-1]['physical_pages']+tail['physical_pages']))
        groups[-1]['title']+=' (including concluding summary)'
    if [i for g in groups for i in g['blocks']]!=[b['id'] for b in blocks]:raise ValueError('Section ownership loss/duplication')
    return groups


def bibliography_entries(document):
    """Balanced braces preserve TeX accents; no fabricated bibliographic fields."""
    entries=[];pattern=re.compile(r'\\bibentry\{')
    for m in pattern.finditer(document):
        i=m.end();start=i;depth=1
        while i<len(document) and depth:
            c=document[i]
            if c in '{}':
                preceding=len(document[:i])-len(document[:i].rstrip('\\'))
                if preceding%2==0:depth += 1 if c=='{' else -1
            i+=1
        if depth:raise ValueError('Unclosed bibliography entry')
        entries.append({'start':start,'end':i-1,'text':document[start:i-1]})
    return entries
