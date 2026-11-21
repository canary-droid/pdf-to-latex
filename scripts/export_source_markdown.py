#!/usr/bin/env python3
"""Bounded offline TeX derivative; no inference, compilation or library selection."""
import argparse,json,re,sys
from pathlib import Path
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from probe.common import sha,atomic_json
from probe import source_formats as fmt,source_library
from probe.experiment import seal,verify_seal

def export(tex_path,expected,output,asset_root=None,evidence=()):
    tex_path=Path(tex_path).resolve();output=Path(output);root=Path(asset_root or tex_path.parent).resolve()
    if sha(tex_path)!=expected:raise ValueError('Saved TeX identity differs')
    if tex_path.stat().st_size>1024*1024:raise ValueError('Bounded exporter limit:1MiB source; split explicitly offline')
    if output.exists():
        verify_seal(output);prior=json.loads((output/'export.json').read_text())
        if prior['source_file_sha256']!=expected or prior['protocol']!=fmt.PROTOCOLS['markdown']:raise ValueError('Existing export identity differs')
        return prior
    output.mkdir(parents=True);text=tex_path.read_text();markdown,report=fmt.tex_export(text)
    source_library.copy_verified(tex_path,output/'original.tex',expected)
    missing=[];copied={};pending=[text];seen=set();graphicpaths=['']
    for m in re.finditer(r'\\graphicspath\s*\{((?:\{[^{}]*\})+)\}',text):graphicpaths+=re.findall(r'\{([^{}]*)\}',m[1])
    while pending:
        content=pending.pop()
        refs=[]
        for m in re.finditer(r'\\(includegraphics|input|include|bibliography|addbibresource)\*?(?:\[[^\]]*\])?\s*\{([^{}]+)\}',content):
            for ref in m[2].split(','):refs.append((m[1],ref.strip()))
        for kind,ref in refs:
            if (kind,ref) in seen:continue
            seen.add((kind,ref));suffixes=['']+(['.png','.jpg','.jpeg','.pdf','.eps'] if kind=='includegraphics' else ['.tex'] if kind in ('input','include') else ['.bib','.bbl'])
            candidates=[]
            for prefix in (graphicpaths if kind=='includegraphics' else ['']):
                for suffix in suffixes:
                    name=prefix+ref+suffix;p=root/name
                    if fmt.safe_asset(name) and not p.is_symlink() and p.resolve().is_relative_to(root) and p.is_file():candidates.append((name,p))
            candidates=list({str(p.resolve()):(name,p) for name,p in candidates}.values())
            if len(candidates)!=1:missing.append({'kind':kind,'reference':ref,'reason':'Missing or ambiguous literal dependency; not executed'});continue
            name,path=candidates[0]
            if name in ('original.tex','source.md','export.json','manifest.json','README.md') or name.startswith('review-evidence/'):
                missing.append({'kind':kind,'reference':ref,'reason':'Dependency collides with derivative provenance; not overwritten'});continue
            if len(copied)>=1000 or sum(x['bytes'] for x in copied.values())+path.stat().st_size>32*1024**2:missing.append({'kind':kind,'reference':ref,'reason':'Bounded dependency budget exceeded'});continue
            source_library.copy_verified(path,output/name);copied[name]={'sha256':sha(path),'bytes':path.stat().st_size,'original_path':str(path)}
            if kind in ('input','include'):pending.append(path.read_text())
            if kind=='includegraphics':markdown=markdown.replace(']('+ref+')',']('+quote(name,safe='/.-_')+')')
    evidence_records=[]
    for n,path in enumerate(evidence):
        path=Path(path)
        if path.suffix not in ('.json','.md','.diff') or path.stat().st_size>2*1024**2 or re.search(r'auth|credential|request|response|secret|reasoning',path.name,re.I):raise ValueError('Only compact non-secret provenance/findings allowed')
        dest=output/'review-evidence'/f'{n:02}-{path.name}';source_library.copy_verified(path,dest)
        evidence_records.append({'path':str(dest.relative_to(output)),'original_path':str(path),'sha256':sha(path)})
    (output/'source.md').write_text(markdown)
    check=fmt.validate(markdown,{name:output/name for name in copied})
    report.update(protocol=fmt.PROTOCOLS['markdown'],source_file=str(tex_path),source_file_sha256=expected,dependencies=copied,missing_dependencies=missing,retained_review_evidence=evidence_records,derivative_check=check,markdown_sha256=sha(output/'source.md'),selected=False)
    if missing or not check['usable']:report['status']='partial_unsupported'
    atomic_json(output/'export.json',report)
    (output/'README.md').write_text('# Saved-TeX Markdown derivative\n\nStatus: '+report['status']+'. Original TeX and supplied review evidence are retained. No OCR, model call, compilation or source-image review was performed. This export is not selected into the source library. See export.json for unsupported structures and dependency gaps.\n')
    seal(output);return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tex',type=Path,required=True);p.add_argument('--expected-sha256',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--asset-root',type=Path);p.add_argument('--evidence',action='append',type=Path,default=[]);a=p.parse_args()
    result=export(a.tex,a.expected_sha256,a.output,a.asset_root,a.evidence);print(json.dumps({'output':str(a.output),'status':result['status'],'issues':result['issues'],'missing_dependencies':result['missing_dependencies']},indent=2))
