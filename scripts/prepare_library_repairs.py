#!/usr/bin/env python3
"""Exact saved source-checked corrections. No OCR/model requests."""
import copy,difflib,json,re,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from probe.common import read_json,atomic_json,sha
from probe import chapter_editorial as editorial,image_review,compiler_environment
PARENT=ROOT/'runs/image-review-recovery-20261106T215705Z'
CF='original-21debf82bc2c0a3d';SP='original-185f783748bb248e'

def corrections(text,source):
    records=[];before=text
    def replace(old,new,locator,kind,reason):
        nonlocal text
        if text.count(old)!=1:raise ValueError('Correction anchor is not unique: '+locator)
        records.append({'old':old,'new':new,'source':locator,'kind':kind,'reason':reason,'checked_by':'Codex direct source image and stated local calculation'});text=text.replace(old,new,1)
    if source=='cf':
        replace('$M = (b^2 - 4ac)/4c^2$',r'$M = \sqrt{b^2 - 4ac}/(2c)$','physical6 after38a','correction_to_print',r'N^2 Q^2=b^2/(4c^2)-M^2=a/c; positive convention gives M=sqrt(b^2-4ac)/(2c).')
        replace(r'where $a > 0$ and $\nu = -\frac{1}{2}$.',r'where $a > 0$ and $\nu > -\frac{1}{2}$.','physical8 relation(b)','correction_to_print','Both gamma shapes nu+1/2 must be strictly positive under density39.')
        # Individually located source glyphs, not a global g/varrho substitution.
        for old,new,loc in [
          (r'X_{\rho}(u; \alpha, \lambda)',r'X_g(u; \alpha, \lambda)','physical8 gamma definition before39'),
          (r'X _ {o} (x; a, \nu)',r'X _ {g} (x; a, \nu)','physical8 relation(a) first gamma'),
          (r'X _ {o} (y; b, \mu)',r'X _ {g} (y; b, \mu)','physical8 relation(a) second gamma'),
          (r'X _ {\varrho} (z; a - b, \beta)',r'X _ {g} (z; a - b, \beta)','physical9 continuation(c) first gamma'),
          (r'X _ {\varrho} (w; a, \gamma_ {1} - \beta)',r'X _ {g} (w; a, \gamma_ {1} - \beta)','physical9 continuation(c) second gamma'),
          (r'X _ {o} (y; a - \lambda , b)',r'X _ {g} (y; a - \lambda , b)','physical9 relation(f)'),
          (r'X _ {o} (y; b + a, \nu + \frac {1}{2})',r'X _ {g} (y; b + a, \nu + \frac {1}{2})','physical9 relation(i)')]:
            replace(old,new,loc,'transcription_repair','Original Latin italic g agrees with the defined gamma density g. Correct existing g in(b),(e),(g),(h) retained.')
        notes={
          '83ebd5a595':'Mixtures(21), physical7: the source omits explicit upper limits. The working edition retains infinity as an editorial clarification of the stated infinite mixtures. The prior claim that infinity signs were visibly printed is rejected. This is not an OCR/transcription repair.',
          '8c738d2066':'Sums relation(b), physical8: printed nu=-1/2 corrected to nu>-1/2 because both gamma shapes nu+1/2 must be positive under density(39). This corrects printed mathematics, independently of the glyph repairs.',
          'f90ed7fcc8':'Gamma-variable notation, physical8-9: each located symbol was compared with the original and density g. Seven draft o/rho/varrho occurrences are corrected to Latin italic g. Existing g in(b),(e),(g),(h) is retained. The historical assertion that the source mixes these glyphs is superseded.'}
        for suffix,body in notes.items():
            matches=[m for m in re.finditer(r'\\par\\smallskip\\noindent\\textbf\{[^\n]+\} .*?\n\\par\\smallskip',text,re.S) if suffix in m[0]]
            if len(matches)!=1:raise ValueError('Historical note not uniquely mapped '+suffix)
            old=matches[0][0];new=editorial.annotation({'id':'library-cf-'+suffix,'text':body,'status':'applied_source_checked','attribution':'Codex'}).strip()
            replace(old,new,'historical note '+suffix,'note_reconciliation','Raw old note remains in before-version and diff; new note separates print/transcription/editorial correction.')
        note=editorial.annotation({'id':'library-cf-M-2026110701','text':'After(38a), physical6: M corrected to sqrt(b^2-4ac)/(2c) from the printed N,Q product identity. Original M and all historic proposals are preserved. The High suggestion with denominator4c^2 is rejected. This local check does not constitute a complete Max review or whole-paper proof. The slash-format density denominator remains a source interpretation note.','status':'applied_source_checked','attribution':'Codex'})
    else:
        replace(r'(- 1)^{n} n! \beta^{m + 1/2} n! r^{\alpha - m - 1/2}',r'(- 1)^{n} n! \beta^{m + 1/2} r^{\alpha - m - 1/2}','physical29 psi after61','correction_to_print','The printed phi divided by printed A_n has one n!, so phi=A_n psi requires removing the duplicate n!. Original duplicated n! retained in before-version.')
        if r'\nu (r)' in text:raise ValueError('Unexpected nu substitution; source/draft identity needs reconciliation')
        note=editorial.annotation({'id':'library-spectral-2026110701','text':'Physical29: the source and actual draft both read u(r); the proposed nu-to-u change targets a nonexistent anchor and is rejected. The printed duplicate n! in psi is corrected using phi=A_n psi. This is a correction to printed mathematics, not an OCR repair. The previous eight individually assessed corrections and numbering remain unchanged.','status':'applied_source_checked','attribution':'Codex'})
    # Both current assemblies use grouped parts, not standalone document endings.
    if text.count(r'\endgroup')!=1:raise ValueError('Unexpected assembled-part envelope')
    text=text.replace(r'\endgroup',note+'\n'+r'\endgroup')
    return text,records

def prepare(run):
    run=Path(run);run.mkdir(parents=True,exist_ok=True);old=read_json(PARENT/'state.json');s={k:copy.deepcopy(old[k]) for k in ['compiler_environment']};s['disable_dependency_downloads']=True
    if not (run/s['compiler_environment']['path']).exists():shutil.copytree(PARENT/s['compiler_environment']['path'],run/s['compiler_environment']['path'])
    atomic_json(run/'compiler-state.json',s)
    for source,sid in [('cf',CF),('spectral',SP)]:
        dest=run/'saved-repairs'/source
        if (dest/'provenance.json').exists():continue
        origin=PARENT/'deliveries'/source;baseline=read_json(origin/'delivery.json')['selection']['selected']
        for name,digest in baseline['files'].items():
            if sha(origin/name)!=digest:raise ValueError('Saved selected edition changed')
        dest.mkdir(parents=True,exist_ok=True)
        for name in ['parts','assets']:
            if (origin/name).exists():shutil.copytree(origin/name,dest/name)
        shutil.copyfile(origin/'master.tex',dest/'master.tex');part=dest/'parts'/(sid+'-whole-3.tex');before=part.read_text();after,log=corrections(before,source)
        (dest/'before.tex').write_text(before);part.write_text(after);atomic_json(dest/'corrections.json',log)
        (dest/'changes.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='saved-selected-part',tofile='source-checked-working-part')))
        atomic_json(dest/'provenance.json',{'parent':str(origin),'parent_selection':baseline,'source_sha256':read_json(PARENT/'plan.json')['sources'][source]['sha256'],'prior_part_sha256':baseline['files']['parts/'+part.name],'new_part_sha256':sha(part),'checks':'Original CF pages6,7,8,9 and Spectral29 directly inspected. Limited source checks; historical failed reviews retained.','correction_counts':len(log)})
        for page in ([6,7,8,9] if source=='cf' else [29]):
            p=dest/'source-pages'/f'page-{page:03}.png';p.parent.mkdir(exist_ok=True);shutil.copyfile(PARENT/'sources'/source/p.name,p)
    return s

def compile_repairs(run):
    run=Path(run);s=read_json(run/'compiler-state.json')
    for source in ['cf','spectral']:
        dest=run/'saved-repairs'/source;inputs={str(p.relative_to(dest)):p for sub in ['parts','assets'] for p in (dest/sub).rglob('*') if p.is_file()}
        if not (dest/'build/compilation.json').exists():compiler_environment.compile_saved(run,s,ROOT,(dest/'master.tex').read_text(),dest/'build',inputs)
        result=read_json(dest/'build/compilation.json')
        if result['status']=='passed':shutil.copyfile(dest/'build/attempt-1/document.pdf',dest/'reading.pdf')
        atomic_json(dest/'selection.json',image_review.compiling_selection({'path':str(PARENT/'deliveries'/source)},{'path':str(dest),'files':{name:sha(p) for name,p in inputs.items()}},result))
        print(source,result['status'])

if __name__=='__main__':
    r=Path(sys.argv[2]);prepare(r)
    if sys.argv[1]=='compile':compile_repairs(r)
