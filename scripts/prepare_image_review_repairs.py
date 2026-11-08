#!/usr/bin/env python3
"""Finite saved-file derivatives; no model requests, OCR or service operations."""
import sys,json,re,copy,shutil,time,difflib,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from probe.common import read_json,atomic_json,sha,writer_lock
from probe import followup_lifecycle as assembly,book_completion as scope,compiler_environment as compiler
from scripts import extraction_followup as previous
PARENT=ROOT/'runs/extraction-followup-20261105T223237Z-lifecycle'
POINTER=ROOT/'results/glm-image-review-current.json'
SP=previous.SP;CF=previous.CF;PV=previous.PV

CALCULATIONS=[
('34','Morse scale','sqrt(2)*sigma','sigma/sqrt(2)',r'For log X the diffusion coefficient is sigma. Liouville dy/dx=sqrt(2)/sigma gives x=sigma*y/sqrt(2). Thus exp(-x)=exp(-sigma*y/sqrt(2)), fixing the Morse scale. All other constants retain their definitions.'),
('36','GARCH parameter','-1-4*kappa/xi^2','-1-2*kappa/xi^2',r'For X_t=alpha V_(4t/xi^2), alpha=xi^2/(4*kappa*theta), Ito/time-change gives diffusion2X and drift1-4*kappa*X/xi^2. Canonical Eq73 has drift1+2(nu+1)X. Equating coefficients yields nu=-1-2*kappa/xi^2.'),
('38','Hypergeometric scale','A/sqrt(2)','sqrt(A)/sqrt(2)',r'After arcsinh, a=sqrt(A), b=p*tanh(x)-q*sech(x), p=mu-A/2,q=mu L. Liouville x=sqrt(A/2)*y, hence gamma=sqrt(A/2). The printed A/sqrt(2) is not the square root shown in its diffusion coefficient.'),
('38','Hypergeometric constant','(mu/A-1/2)^2/2','A*(mu/A-1/2)^2/2',r'For constant a=sqrt(A), gauge potential Q=b^2/(2A)+b_prime/2. Its constant is p^2/(2A)=(A/2)(mu/A-1/2)^2. Expanding also reproduces printed c1=q^2/(2A)-p*(p-A)/(2A) and c2=q*(A-mu)/A.'),
('38','Asymptotic limit','Q tends to infinity','Q tends to c0',r'For A>0, gamma=sqrt(A/2)>0. sech^2(gamma*y) and sinh(gamma*y)/cosh^2(gamma*y) both vanish as y tends to either infinity. Therefore the displayed Q tends to c0; agrees with the printed spectral cutoffs.'),
('39','mu=0 potential','1/8-3A*sech^2/8','A/8-3A*sech^2/8',r'Set mu=0: p=-A/2,q=0 in Q=b^2/(2A)+b_prime/2. Q=(A/8)*tanh^2-(A/4)*sech^2=A/8-3A*sech^2/8. This is a correction to the printed constant, not a new reading of the glyph.'),
('40','Jacobi drift/diffusion scaling','kappa=beta*z; A=sigma*z','kappa=beta; A=sigma',r'From the original p39 SDE and Xbar=(X-m)/z, z=ln(1+a)>0, divide drift and diffusion by z. Both factors z cancel: dXbar=beta*(gamma-Xbar)dt+sigma*sqrt(1-Xbar^2)dB. No time rescaling is specified.'),
('40','Jacobi Liouville scale','sigma*z/sqrt(2)','sigma/sqrt(2)',r'Using a_Xbar=sigma*sqrt(1-Xbar^2), dy/dXbar=sqrt(2)/(sigma*sqrt(1-Xbar^2)). With centered coordinate y=sqrt(2)/sigma*arcsin(Xbar), so Xbar=sin(sigma*y/sqrt(2)). The z cancels. This gamma denotes the potential scale, not the earlier asymmetry parameter.')]

def repair_intro_numbering(text):
    first=re.search(r'\\begin\{equation\}(.*?)\\end\{equation\}',text,re.S)
    if not first or r'V (t, x) = \mathbb{E}_{x}' not in first[1] or r'\label' in first[1]:
        raise ValueError('Unexpected introductory-display anchor')
    # Original physical p1/printed337 visibly has no number. Its accidental
    # equation environment shifted all original source numbers1–22 by one.
    return text[:first.start()]+r'\begin{equation*}'+first[1]+r'\end{equation*}'+text[first.end():]


def prepare():
 import fitz
 if POINTER.exists():return Path(read_json(POINTER)['run'])
 with writer_lock(ROOT),writer_lock(ROOT/'runs'):
  old=read_json(PARENT/'state.json');assert old['status']==previous.TERMINAL
  run=ROOT/'runs'/('glm-image-review-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));run.mkdir()
  s=copy.deepcopy(old);s['disable_dependency_downloads']=True
  shutil.copytree(PARENT/s['compiler_environment']['path'],run/s['compiler_environment']['path'])
  atomic_json(run/'parent-state.json',old);atomic_json(run/'repair-state.json',s)
  findings=read_json(PARENT/'accuracy'/f'{SP}-whole-4/focused-call-012.json')['findings']
  adjud=[]
  for i,(page,name,printed,corrected,reason) in enumerate(CALCULATIONS):
   f=findings[i];adjud.append({'id':i+1,'topic':name,'physical_page':int(page),'printed_page':int(page)+336,'printed_formula':printed,'converter_formula':f['old'],'critic_replacement':f['new'],'working_formula':corrected,'disposition':'supported_correction_to_printed_mathematics','independent_check':reason,'source_image':str(PARENT/'sources'/SP/f'page-{int(page):03}.png'),'source_image_sha256':sha(PARENT/'sources'/SP/f'page-{int(page):03}.png'),'limits':'Local formula check using stated SDEs; not verification of the whole section/paper'})
  atomic_json(run/'evaluation/spectral-eight-edits.json',adjud)
  report=[]
  for sid in (CF,SP,PV):
   dest=run/'repairs'/sid;dest.mkdir(parents=True);units=[];refs={};coverage=[]
   for key,label in old['current_versions'].items():
    if not key.startswith(sid):continue
    v=old['versions'][key][label];text=(PARENT/v['path']).read_text();assert sha(PARENT/v['path'])==v['sha256'];original=text
    (dest/(key+'-selected-original.tex')).write_text(original)
    if sid==SP and key.endswith('whole-1'):text=repair_intro_numbering(text)
    if sid==SP and key.endswith('whole-4'):
     for f in findings:assert f['new'] in text and f['old'] not in scope.body_only(text)
     marker=r'\section*{Editorial corrections and unresolved issues}'
     assert text.count(marker)==1
     text=text.replace(marker,r'\section*{Historical converter log (superseded where noted)}'+'\n'+r'\noindent This is the PRE-REVIEW converter record, not a description of the current formulas. The eight working corrections below have been independently checked by Codex against the original images and the stated diffusion definitions. Other source uncertainties remain open.'+'\n')
     notes='\n% PDF2TEX_GENERATED_NOTES_BEGIN\n'+r'\section*{Working mathematical corrections checked against source}'+'\n'
     from probe.chapter_editorial import tex_escape
     for row in adjud:notes+=r'\paragraph{'+tex_escape(str(row['id'])+'. '+row['topic'])+'} '+tex_escape('Printed: '+row['printed_formula']+'. Working: '+row['working_formula']+'. '+row['independent_check'])+'\n'
     text=text.replace(r'\end{document}',notes+r'\end{document}')
    native=read_json(PARENT/'inputs'/key/'native.json')
    if sid==PV:
     figure=re.search(r'\\begin\{figure\}.*?\\end\{figure\}',text,re.S);assert figure
     assets=[f'assets/{PV}-p4-region-{i}.png' for i in range(2,9)]
     assert all(text.count('{'+x+'}')==1 for x in assets)
     start=figure[0].index(r'\includegraphics');end=figure[0].index(r'\caption')
     replacement=figure[0][:start]+r'\includegraphics[width=0.95\linewidth,height=0.72\textheight,keepaspectratio]{'+assets[0]+'}\n'+figure[0][end:]
     text=text[:figure.start()]+replacement+text[figure.end():]
     group={'id':'pvalues-figure1-verified-composite','canonical':assets[0],'members':assets[1:],'source_id':PV,'physical_page':4,'verification':'Direct original-page/composite/panel inspection; exact six panels in canonical, not a generic overlap heuristic','hashes':{x:sha(PARENT/'inputs'/x) for x in assets}}
     native['verified_figure_groups']=[group];atomic_json(dest/'verified-figure-group.json',group)
     text=text.replace(r'\section*{Editorial corrections and unresolved issues}',r'\section*{Historical converter log (figure uncertainty resolved)}'+'\n'+r'\noindent Figure 1 now uses the verified complete six-panel composite once. The following historical log describes the original seven-asset draft; its figure uncertainty is resolved. All individual crop files are preserved.'+'\n')
    # Mark known generated notes by provenance, never a source Accuracy heading.
    for title in ('Editorial corrections and unresolved issues','Historical converter log (superseded where noted)','Historical converter log (figure uncertainty resolved)'):
     needle=r'\section*{'+title+'}'
     if needle in text:text=text.replace(needle,'% PDF2TEX_GENERATED_NOTES_BEGIN\n'+needle,1)
    path=dest/(key+'-working.tex');path.write_text(text);(dest/(key+'.diff')).write_text(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='preserved-original',tofile='working-derivative')))
    atomic_json(dest/(key+'-provenance.json'),{'source':str(PARENT/v['path']),'source_sha256':v['sha256'],'derivative_sha256':sha(path),'prior_build':v['compilation']})
    units.append((key,text));ids=[b['id'] for b in native['blocks']];coverage.append({'unit':key,'result':scope.coverage_check(text,native,ids)})
    for ref in read_json(PARENT/'inputs'/key/'assets.json'):refs[ref]=PARENT/'inputs'/ref
   if sid==CF:
    # Retain the already compiled complete edition; actual bounds, no typographic campaign.
    pdf=fitz.open(PARENT/'deliveries'/sid/'reading.pdf');outside=[]
    for i,p in enumerate(pdf):
     for b in p.get_text('dict')['blocks']:
      for line in b.get('lines',[]):
       for span in line['spans']:
        if not p.rect.contains(fitz.Rect(span['bbox'])):outside.append({'page':i+1,'text':span['text'],'bbox':span['bbox']})
    shutil.copytree(PARENT/'deliveries'/sid,dest/'preserved-reading-edition');atomic_json(dest/'clipping-check.json',{'glyphs_outside_physical_page':outside,'page_count':len(pdf),'decision':'No demonstrated content clipping; equations not changed','limits':'Glyph geometry plus render inspection; overfull margin warnings alone do not prove clipping'})
    report.append({'source':sid,'status':'preserved_existing_edition','clipped_glyphs':len(outside)});continue
   try:
    master,parts,log=assembly.assemble_documents(units,theorem_declarations={'theorem':'Theorem','lemma':'Lemma','assumption':'Assumption'} if sid==SP else None)
    for key,body in parts.items():
     p=dest/'parts'/(key+'.tex');p.parent.mkdir(exist_ok=True);p.write_text(body);refs['parts/'+key+'.tex']=p
    (dest/'master.tex').write_text(master)
    for name,p in list(refs.items()):
     if name.startswith('assets/'):
      target=dest/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(p,target);refs[name]=target
    result=compiler.compile_saved(run,s,ROOT,master,dest/'build',refs);atomic_json(dest/'assembly-log.json',log)
    if result['status'].startswith('passed'):
     pdfpath=run/result['attempts'][-1]['path']/'document.pdf';shutil.copyfile(pdfpath,dest/'reading.pdf');pdf=fitz.open(pdfpath);imagebounds=[]
     for n,p in enumerate(pdf,1):
      for im in p.get_image_info():imagebounds.append({'page':n,'bbox':im['bbox'],'outside':not p.rect.contains(fitz.Rect(im['bbox']))})
     fulltext='\n'.join(p.get_text() for p in pdf)
     checks={'image_bounds':imagebounds,'severe_float_warning':'Float too large' in (run/result['attempts'][-1]['path']/'console.log').read_text(),'unresolved_references':log['unresolved_references'],'printed_theorems':re.findall(r'Theorem\s+([1-6])',fulltext),'printed_assumptions':re.findall(r'Assumption\s+([1-4])',fulltext),'printed_lemmas':re.findall(r'Lemma\s+([1-2])',fulltext),'automatic_equations':'actual PDF/aux saved; inspect Eq1–22, not inferred from lack of tags'}
     atomic_json(dest/'render-checks.json',checks)
     if sid==PV:
      assert len(imagebounds)==1 and not any(x['outside'] for x in imagebounds) and not checks['severe_float_warning']
      page=pdf[imagebounds[0]['page']-1];page.get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(dest/'figure-page.png')
     else:
      assert set(checks['printed_theorems'])==set('123456');assert set(checks['printed_assumptions'])==set('1234');assert set(checks['printed_lemmas'])==set('12')
    atomic_json(dest/'coverage.json',coverage);report.append({'source':sid,'status':result['status'],'assembly_completed':True,'unresolved_references':log['unresolved_references']})
   except (ValueError,AssertionError) as exc:report.append({'source':sid,'status':'unresolved','diagnostic':str(exc),'assembly_completed':False,'missing_source_assets':None})
  atomic_json(run/'repairs/report.json',report);atomic_json(run/'repair-state.json',s)
  atomic_json(POINTER,{'run':str(run),'status':'repairs_prepared_not_frozen'});print(run);print(json.dumps(report,indent=2));return run
if __name__=='__main__':prepare()
