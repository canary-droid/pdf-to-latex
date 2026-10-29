"""Offline citation inventory, explicit partial coverage, no metadata requests."""
import re
from pathlib import Path
from .common import fingerprint, sha
from .sciwrite_subset import citation_spans, command_spans

STATUSES={'metadata_checked':'not_checked','full_text_available':'unknown',
          'source_actually_consulted':'not_consulted','claim_supported':'not_assessed'}


def inventory(spans,book,coverage='unknown',bib_files=()):
    if coverage not in ('not_in_extract','unknown','present_partial','present'): raise ValueError('Invalid bibliography coverage')
    entries=[];occurrences=[];references=[];labels=set()
    for span in spans:
        text=span['text'];location={k:v for k,v in span.items() if k!='text'}
        # Adapt upstream extract_bibitems' inline-entry discovery; retain raw body.
        # Do NOT apply its broad author/title regexes or destructive TeX cleaner.
        starts=list(re.finditer(r'(?<!\\)\\bibitem(?:\[([^\]]*)\])?\{([^}]+)\}',text))
        for i,m in enumerate(starts):
            end=starts[i+1].start() if i+1<len(starts) else len(text)
            raw=text[m.start():end]
            entries.append({'id':'bib-'+fingerprint([location,m.start(),raw])[:20],
                'key':m[2],'raw':raw,'raw_sha256':fingerprint(raw),'location':location,
                'span':[m.start(),end],'parsed_fields':{},'parse_status':'raw_bibitem_only',**STATUSES})
        for m in citation_spans(text):
            occurrences.append({'id':'cite-'+fingerprint([location,m['start'],m['key']])[:20],
                'raw':text[m['start']:m['end']],'key':m['key'],'location':location,
                'span':[m['start'],m['end']],'status':'unresolved','candidates':[],
                'relation':'textbook_cites_work; does not imply direct consultation',**STATUSES})
        # Inventory possible printed author/year markers, not a universal parser.
        for m in re.finditer(r'\b(?:18|19|20)\d{2}[a-z]?\b',text):
            occurrences.append({'id':'year-'+fingerprint([location,m.start()])[:20],
                'raw':m[0],'key':None,'location':location,'span':[m.start(),m.end()],
                'status':'ambiguous','candidates':[],'relation':'possible printed citation year; context retained in source span',**STATUSES})
        labels.update(m['argument'] for m in command_spans(text,'label'))
        for cmd in ('ref','eqref','pageref'):
            for m in command_spans(text,cmd):references.append({'target':m['argument'],'location':location,'span':[m['start'],m['end']]})
    for c in occurrences:
        if c['key'] is not None:
            c['candidates']=[e['id'] for e in entries if e['key']==c['key']]
            c['status']='resolved' if len(c['candidates'])==1 else 'ambiguous' if c['candidates'] else 'unresolved'
    for r in references:r['status']='resolved' if r['target'] in labels else 'unknown_outside_window'
    raw_bibs=[]
    for path in bib_files:
        path=Path(path)
        raw_bibs.append({'path':str(path),'sha256':sha(path),'raw':path.read_text(),
            'status':'preserved_unparsed','reason':'Optional bibtexparser adapter not enabled; no speculative field extraction'})
    return {'schema':'local-bibliography-v1','book':book,'coverage':coverage,
        'entries':entries,'occurrences':occurrences,'cross_references':references,'raw_bib_files':raw_bibs,
        'parser_scope':'Explicit simple cite/bibitem commands; year markers are ambiguous candidates. Optional citation arguments and natural-language bibliography fields are not parsed. Comments/verbatim may remain unclassified raw evidence.',
        'missing_references_meaning':'An unmatched citation in a chapter is not evidence of a nonexistent source',
        'statuses':STATUSES,'external_lookup':'disabled','candidate_bib':'not_generated_no_supported_structured_entries'}


def candidate_bib(entries):
    """Only explicit supported fields with evidence; do not infer from raw prose."""
    supported={'author','title','year','journal','booktitle','publisher','edition','pages','doi','url'}
    lines=[];provenance=[]
    for e in entries:
        fields=e.get('parsed_fields',{})
        if not fields:continue
        if set(fields)-supported or not e.get('field_provenance') or set(fields)!=set(e['field_provenance']):
            raise ValueError('Every supported bibliography field needs source provenance')
        raw=e.get('raw')
        if not isinstance(raw,str) or fingerprint(raw)!=e['raw_sha256']:
            raise ValueError('Bibliography raw-entry binding differs')
        for name,value in fields.items():
            span=e['field_provenance'][name]
            if (not isinstance(span,dict) or set(span)!={'start','end'} or
                    type(span['start']) is not int or type(span['end']) is not int or
                    not 0<=span['start']<span['end']<=len(raw) or raw[span['start']:span['end']]!=value):
                raise ValueError('Parsed bibliography field lacks an exact source span')
        if any(not isinstance(v,str) or any(c in v for c in '{}\n\r') for v in fields.values()):
            raise ValueError('Complex BibTeX requires an optional parser; no field guessing')
        key='source'+fingerprint([e['raw_sha256'],fields])[:20]
        lines.append('@misc{'+key+',\n'+',\n'.join('  '+k+' = {'+v+'}' for k,v in sorted(fields.items()))+'\n}')
        provenance.append({'key':key,'source_entry':e['id'],'fields':e['field_provenance'],**STATUSES})
    return '\n\n'.join(lines),provenance
