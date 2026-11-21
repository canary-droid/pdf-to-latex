"""Versioned source formats. Pure parsing/validation; no transport or TeX execution.

Legacy plans have no output_format and remain LaTeX. Technical Markdown is a
transcription, never a summary or proof of source fidelity.
"""
import copy, hashlib, html, json, re
from collections import Counter
from pathlib import Path, PurePosixPath
from urllib.parse import unquote
from . import focused_recovery, book_completion, markdown_compat

PROTOCOLS={'markdown':'technical-markdown-v1','latex':'library-latex-v1'}
MARKDOWN_RULES=r'''Write a full technical transcription, not a summary. Use ATX headings, paragraphs,
lists, **Definition/Theorem/Lemma/Assumption/Proof** headings with original numbering,
and explicit proof endings. Preserve algorithms, appendices and every reference.
Use $...$ inline and $$ on separate lines for display LaTeX math. Preserve printed
numbers using \tag{...}; preserve labels with <a id="label"></a> and use local links
for references. Do not invent automatic equation numbers. Retain unknown macros
verbatim and identify their definitions or unresolved status in the accuracy notes.
Use ![descriptive figure caption](assets/exact-name.png) with the full caption nearby.
Use [^unique-id] footnotes and [^unique-id]: definitions, never delete source footnotes.
Use pipe tables only for simple rectangular data, escaping cell pipes. For merged
headers/cells or multiline mathematical cells use a complete HTML table with
rowspan/colspan, headers, units, caption and row/column relationships. Keep math in
Markdown paragraphs outside HTML if the renderer cannot display it, with explicit
cell locators; do not replace editable cell content by an image. A complex structure
that cannot be represented safely must remain verbatim in a labelled raw-tex block
with an unresolved note and source locator, not silently disappear. No scripts or
remote assets. Preserve source wording, quantities, signs, bounds and conditions.
Keep corrections and unresolved claims in a separate accuracy log after the source
fence; do not silently replace printed mathematics. Do not add wiki summaries.'''

def identity(plan):
    if 'output_format' not in plan:return {'output_format':'latex','format_protocol':'legacy-latex'}
    fmt=plan['output_format']
    if fmt not in PROTOCOLS or plan.get('format_protocol')!=PROTOCOLS[fmt]:raise ValueError('Unknown or missing output-format protocol')
    return {'output_format':fmt,'format_protocol':PROTOCOLS[fmt]}

def explicit(fmt='markdown'):
    if fmt not in PROTOCOLS:raise ValueError('Unsupported output format')
    return {'output_format':fmt,'format_protocol':PROTOCOLS[fmt]}

def suffix(fmt):return '.md' if fmt=='markdown' else '.tex'
def digest(s):return hashlib.sha256(s.encode()).hexdigest()

def conversion_request(primary,secondary,context,assets,contract):
    body=focused_recovery.conversion_request(primary,secondary,context,assets=assets)
    if contract['output_format']=='markdown':
        text=body['messages'][0]['content'].replace('Return one complete standalone LaTeX document in a tex fence, then a concise accuracy log.',
          'Return exactly one complete Markdown source in an outer fence of FOUR backticks labelled markdown, then a concise accuracy log. End the source with <!-- source-transcription-complete --> inside that fence. This marks transport completeness only, not source fidelity.')
        body['messages'][0]['content']=MARKDOWN_RULES+'\n'+text
    if contract['format_protocol']!='legacy-latex':body['messages'][0]['content']='OUTPUT CONTRACT '+json.dumps(contract)+'\n'+body['messages'][0]['content']
    return body

def critic_request(draft,primary,secondary,context,effort,images,contract):
    from . import image_review
    # Reuse the exact-edit instruction and source payload, then the qualified
    # literal-draft/image transport. Never carry converter reasoning forward.
    body=focused_recovery.critic_request(draft,primary,secondary,context,effort=effort)
    if contract['format_protocol']=='legacy-latex':return image_review.with_images(body,images)
    instruction,payload=body['messages'][0]['content'].split('\n',1);payload=json.loads(payload)
    payload.update(contract)
    body['messages'][0]['content']=instruction+'\n'+json.dumps(payload,ensure_ascii=False)
    return image_review.with_images(body,images,output_format=contract['output_format'],format_protocol=contract['format_protocol'])

def parse_markdown(answer,finish_reason):
    if finish_reason!='stop':raise ValueError('No complete normally terminated Markdown response')
    # Prefer four backticks for nested algorithms; a uniquely closed ordinary
    # three-backtick Markdown envelope is also losslessly decodable.
    matches=list(re.finditer(r'(?m)^(`{3,})markdown[ \t]*\n',answer))
    if len(matches)!=1:raise ValueError('Expected one Markdown source envelope')
    m=matches[0];end=re.search(r'(?m)^'+re.escape(m[1])+r'[ \t]*$',answer[m.end():])
    if not end:raise ValueError('Truncated Markdown envelope')
    if re.search(r'`{3,}(?:markdown|md|tex|latex)\b',answer[m.end()+end.end():]):raise ValueError('Multiple source envelopes')
    document=answer[m.end():m.end()+end.start()]
    marker='<!-- source-transcription-complete -->'
    if not document.rstrip().endswith(marker):raise ValueError('Missing Markdown completion marker')
    document=document.rstrip()[:-len(marker)].rstrip()+'\n'
    if not document.strip() or re.search(r'\\(?:documentclass|begin\{document\})',document):raise ValueError('Empty or wrong-format source')
    return document,{'protocol':PROTOCOLS['markdown'],'notes':answer[m.end()+end.end():].strip(),'completion':'Envelope/stop only; not fidelity'}

def image_references(text):
    refs=re.findall(r'!\[[^\]\n]*\]\(<?([^\s)>]+)>?(?:\s+["\'][^\n]*?["\'])?\)',text)
    refs+=re.findall(r'<img\b[^>]*\bsrc=["\']([^"\']+)',text,re.I)
    refs+=re.findall(r'!\[\[([^]|]+)(?:\|[^]]*)?\]\]',text)
    return [unquote(x) for x in refs]

def anchors(text):return re.findall(r'<a\s+id=["\']([^"\']+)["\']\s*>\s*</a>',text)
def footnotes(text):return re.findall(r'(?m)^\[\^([^\]]+)\]:',text)
def safe_asset(name):
    p=PurePosixPath(name)
    return bool(name and not p.is_absolute() and '..' not in p.parts and ':' not in name and '\\' not in name)

def structural_tokens(text):
    return (image_references(text),anchors(text),footnotes(text),
            re.findall(r'\[\^([^\]]+)\](?!:)',markdown_compat.visible(text)),
            re.findall(r'\\(?:tag\*?|label|begin|end)\s*\{[^{}]+\}',text),
            re.findall(r'(?m)^#{1,6}(?=\s)|<\/?(?:table|tr|td|th)\b[^>]*>',text),
            [len(re.findall(r'(?<!\\)\|',row)) for row in text.splitlines() if row.strip().startswith('|')])

def plain(text):
    text=re.sub(r'<!--.*?-->',' ',text,flags=re.S)
    # Strip real tags with literal attributes, never arbitrary text between
    # mathematical inequality signs (which may span several source headings).
    text=re.sub(r'''</?[A-Za-z][A-Za-z0-9]*(?:\s+[A-Za-z][\w:-]*\s*=\s*(?:"[^"]*"|'[^']*'|[^\s<>]+))*\s*/?>''',' ',text)
    text=re.sub(r'\\[A-Za-z]+\*?',' ',text)
    return re.sub(r'[^\w]+',' ',html.unescape(text)).casefold().split()

def coverage(document,unit):
    """Conservative omissions screen, with exact locators; not semantic proof."""
    blocks=unit.get('native_blocks',[]);words=set(plain(document));missing=[]
    emitted=set(image_references(document));equations=[b for b in blocks if b['kind'] in ('equation','formula')]
    tags=lambda t:{re.sub(r'\s+','',x) for x in re.findall(r'\\tag\*?\s*\{([^{}]+)\}',t)}
    expected_tags=tags('\n'.join(b['tex'] for b in equations));found=tags(document)
    # Count only real HTML/pipe tables, not arbitrary fences or filenames.
    tables=len(re.findall(r'<table\b',document,re.I))+len(re.findall(r'(?m)^\s*\|?\s*:?-{3,}:?\s*\|[^\n]*$',document))
    expected_tables=[b for b in blocks if b['kind'] in ('table','table_body')]
    required_assets=set(a for b in blocks if b['kind'] in ('image','image_block','chart') for a in b.get('assets',[]))
    from .library_completion import validate_figure_groups
    validate_figure_groups(unit)
    groups=unit.get('coverage_metadata',{}).get('verified_figure_groups',[])
    represented=set(emitted);duplicated=[]
    # Reuse the qualified geometry/content relationship, never infer duplication
    # from overlapping rectangles or names alone.
    for group in groups:
        canonical=group['canonical'];members=set(group['members'])
        if canonical in emitted:
            represented.update(members)
            if members & emitted:duplicated.append(group['id'])
        elif members<=emitted:represented.add(canonical)
    missing_headings=[]
    normalized=' '.join(plain(re.sub(r'\[\^[^\]]+\]', '', document)))
    source_notes=markdown_compat.source_notes(unit)
    for b in blocks:
        if b['kind']=='paragraph_title':
            source_title=markdown_compat.inline_math(b['tex'])[0]
            labels={n['label'] for n in source_notes if any(r['block']==b['id'] for r in n['references'])}
            source_title=markdown_compat.SUP.sub(lambda m:'' if m[1] in labels else m[0],source_title)
            title=' '.join(plain(source_title))
            if len(title)>3 and title not in normalized:missing_headings.append({'block':b['id'],'page':b.get('page'),'title':b['tex']})
        if b['kind'] in book_completion.FURNITURE:continue
        w=set(x for x in plain(b['tex']) if len(x)>2)
        if len(w)>=12 and len(w&words)<.45*len(w):missing.append({'block':b['id'],'page':b.get('page'),'kind':b['kind'],'reason':'Low source-word evidence; inspect for omission or extraction mismatch'})
    flags=[]
    if missing_headings:flags.append('Missing source heading candidates')
    if duplicated:flags.append('Verified figure content displayed twice')
    if expected_tags-found:flags.append('Missing printed equation tags')
    if len(expected_tables)>tables:flags.append('Fewer editable tables than source regions')
    if required_assets-represented:flags.append('Missing owned source figures')
    if equations and not re.search(r'\$\$|\\\[',document):flags.append('Source equations but no display mathematics')
    if missing:flags.append('Substantive source spans need checking')
    note_check=markdown_compat.footnote_coverage(document,unit)
    if note_check['missing_or_changed_definitions'] or note_check['unbound_references']:flags.append('Source footnotes lack exact definitions or bound references')
    return {'coverage_status':'omission_risk' if flags else 'requires_source_review','flags':flags,'missing_spans':missing,
      'missing_heading_candidates':missing_headings,'missing_equation_tags':sorted(expected_tags-found),'source_equation_blocks':len(equations),'source_tables':len(expected_tables),'output_tables':tables,
      'duplicated_verified_figures':duplicated,'missing_figures':sorted(required_assets-represented),'owned_block_ids':[b['id'] for b in blocks],'footnote_coverage':note_check,
      'semantic_completeness':'Heuristic structural screen only; exact source-image review remains separate','automatic_equation_numbering':'not inferred; printed tags retained explicitly'}

def validate(document,assets=(),unit=None):
    from .library_repair import math_spans,unbalanced_math_groups
    issues=[];unresolved=[]
    if len(document.strip())<20:issues.append('Empty or insufficient source')
    if re.search(r'\\(?:documentclass|begin\{document\})',document):issues.append('LaTeX document in Markdown slot')
    if re.search(r'<(?:script|iframe|object)\b|\bon\w+\s*=|javascript:',document,re.I):issues.append('Executable/unsafe HTML is not source Markdown')
    if len(re.findall(r'!\[(?!\[)',document))>len(image_references(document)):issues.append('Unsupported or malformed Markdown image reference')
    for ref in image_references(document):
        if not safe_asset(ref) or ref not in assets or not Path(assets[ref]).is_file():issues.append('Missing/nonportable figure '+ref)
    # Exclude fenced algorithms/raw structures from delimiter validation; retain
    # unsupported content explicitly rather than pretending it was rendered.
    fences=list(re.finditer(r'(?m)^(`{3,}|~{3,})([^\n]*)$',document));opened=None
    for f in fences:
        if opened is None:opened=f[1]
        elif f[1][0]==opened[0] and len(f[1])>=len(opened):opened=None
    if opened:issues.append('Unclosed code/raw fence')
    text=markdown_compat.visible(document)
    compatibility_issues=[]
    if any(kind=='paren_math' for kind,_,_ in markdown_compat.segments(document)):
        compatibility_issues.append('TeX inline delimiters are not the qualified Obsidian dollar representation')
    for kind,a,b in markdown_compat.segments(document):
        if kind=='dollar_math' and not document.startswith('$$',a) and document[a+1:b-1] != document[a+1:b-1].strip():
            compatibility_issues.append('Inline dollar delimiter-adjacent whitespace requires inspection')
    table_math=markdown_compat.html_table_math_findings(document)
    if table_math:compatibility_issues.append("Mathematics in raw HTML table requires compatible presentation")
    unresolved+=table_math
    issues+=compatibility_issues
    spans,errors=math_spans(text);issues+=errors
    if any(unbalanced_math_groups(x) for x in spans):issues.append('Unbalanced mathematics groups')
    definitions=footnotes(text);uses=re.findall(r'\[\^([^\]]+)\](?!:)',text)
    if set(uses)-set(definitions):issues.append('Missing footnote definitions: '+str(sorted(set(uses)-set(definitions))))
    if set(definitions)-set(uses):issues.append('Unreferenced footnote definitions: '+str(sorted(set(definitions)-set(uses))))
    for values,label in ((anchors(document),'anchors'),(definitions,'footnotes')):
        if len(values)!=len(set(values)):issues.append('Duplicate '+label)
    missing=set(re.findall(r'(?<!!)\[[^]]+\]\(#([^)]*)\)',document))-set(anchors(document))
    if missing:unresolved.append({'kind':'cross_unit_references','targets':sorted(missing)})
    if '```raw-tex' in document or '```{=latex}' in document:unresolved.append({'kind':'unsupported_raw_tex','reason':'Retained verbatim; not rendered/editable Markdown structure'})
    # Unknown macros remain visible; no speculative expansion.
    known=set('frac dfrac tfrac sqrt sum prod int iint iiint lim log exp sin cos tan Gamma alpha beta gamma delta epsilon varepsilon theta vartheta lambda mu nu xi pi rho varrho sigma tau phi varphi chi psi omega infty partial nabla mathrm mathbf mathbb mathcal mathsf text operatorname left right big Big bigg Bigg begin end tag label overline underline hat bar tilde vec dot ddot quad qquad cdot times le leq ge geq neq approx sim to in notin subset subseteq cup cap pm mp ldots cdots vdots ddots underbrace overbrace substack limits nolimits displaystyle textstyle scriptscriptstyle scriptstyle binom dbinom cases aligned align split matrix pmatrix bmatrix vmatrix Vmatrix uparrow downarrow langle rangle lvert rvert vert Vert angle degree perp mid forall exists neg ell Re Im det min max sup inf Pr probability hbar Delta Theta Lambda Xi Pi Sigma Phi Psi Omega Upsilon zeta eta kappa upsilon omicron triangleq dots ldots lnot mapsto Longrightarrow Rightarrow implies iff mathit textrm textnormal boldsymbol hphantom vphantom phantom bigl bigr Bigl Bigr biggl biggr Biggl Biggr choose atop mod bmod pmod'.split())
    # Standard TeX/AMS notation, not a list of document-specific macro names.
    # Recognition is separate from exercising any particular viewer/extension.
    known.update('prime doubleprime backprime ast star circ bullet oplus otimes odot oslash wedge vee bigcup bigcap bigvee bigwedge coprod oint iiiint smallint arcsin arccos arctan sinh cosh tanh coth csc sec cot gcd deg hom ker dim arg limsup liminf lg ln sgn aleph wp imath jmath emptyset varnothing varpi varsigma varkappa beth complement propto equiv cong simeq asymp ll gg prec succ preceq succeq nleq ngeq ne ni supset supseteq sqsubseteq sqsupseteq setminus smallsetminus land lor top bot vdash models parallel nparallel not lceil rceil lfloor rfloor lbrace rbrace backslash slash arrowvert Arrowvert Uparrow Downarrow updownarrow Updownarrow gets longrightarrow longleftarrow leftrightarrow longleftrightarrow Leftarrow Leftrightarrow Longleftarrow Longleftrightarrow hookrightarrow hookleftarrow rightleftharpoons searrow nearrow swarrow nwarrow widehat widetilde overrightarrow overleftarrow overset underset mathfrak mathscr boldsymbol mathop mathbin mathrel mathord mathopen mathclose mathpunct mathinner tbinom cfrac genfrac boxed bmod pod colon thinspace negthinspace enspace nonumber notag subarray displaylines hfill hspace vspace mspace substack'.split())
    known.update('square blacksquare Box Diamond lozenge blacklozenge blacktriangle blacktriangledown rightarrow leftarrow hslash eth digamma varDelta varGamma varLambda varOmega varPhi varPi varPsi varSigma varTheta varUpsilon varXi'.split())
    known.difference_update({'probability','doubleprime'})  # Not standard commands.
    viewer_commands={'bm':'boldsymbol alternative requires viewer support', 'cancel':'cancel extension', 'bcancel':'cancel extension', 'xcancel':'cancel extension', 'mathds':'double-struck font extension', 'mathbbm':'double-struck font extension', 'num':'siunitx-style quantity syntax', 'SI':'siunitx-style quantity syntax'}
    commands=set(re.findall(r'\\([A-Za-z]+)', '\n'.join(spans)))
    custom=commands-known-set(viewer_commands)
    if custom:unresolved.append({'kind':'unqualified_math_macros','macros':sorted(custom),'meaning':'No standard command or supplied definition established; retained unchanged, not proven erroneous mathematics'})
    if commands&set(viewer_commands):unresolved.append({'kind':'viewer_specific_math_commands','commands':{x:viewer_commands[x] for x in sorted(commands&set(viewer_commands))},'status':'Rendering untested; formula retained unchanged'})
    outside=text
    for content in spans:
        # Removing the exact mathematical content leaves its delimiters; only
        # unescaped alphabetic TeX commands outside those spans are diagnosed.
        outside=outside.replace(content,'',1)
    raw_commands=sorted(set(re.findall(r'(?<!\\)\\([A-Za-z]+)',outside)))
    if raw_commands:unresolved.append({'kind':'unrendered_tex_commands','commands':raw_commands})
    cov=coverage(document,unit) if unit else None
    if unit:unresolved+=markdown_compat.paragraph_boundary_findings(document,unit)
    if cov and cov['coverage_status']=='omission_risk':issues.append('Source coverage requires resolution')
    if any(x['kind'] in ('unsupported_raw_tex','unqualified_math_macros','unrendered_tex_commands','viewer_specific_math_commands') for x in unresolved):issues.append('Unresolved rendering structures/macros retained')
    return {'usable':not issues,'content_issues':issues,'unresolved_structures':unresolved,'coverage':cov,
      'format_compatibility':{'policy':markdown_compat.POLICY,'inline_issues':compatibility_issues,'viewer_tested':False},
      'mathematical_confidence':'not independently established','compilation_required':False,'format':'markdown'}

def assembly(parts):
    """Parts are (key, exact Markdown). Qualify joins without rewriting source."""
    joined=[];seen={};duplicates=[]
    for key,text in parts:
        # Namespace local asset paths and reference/footnote IDs in the assembly
        # only. Standalone bytes remain unchanged. Global equation labels stay.
        for paragraph in re.split(r'\n\s*\n',text):
            norm=' '.join(plain(paragraph))
            if len(norm)>180:
                if norm in seen:duplicates.append({'first':seen[norm],'second':key,'sha256':digest(paragraph)})
                seen[norm]=key
        def replace_visible(pattern, replacement):
            # Namespace real links only, never code/comment examples. HTML tags
            # remain available for asset rewriting; their contents are not run.
            protected=[(a,b) for kind,a,b in markdown_compat.segments(text)
                       if kind in ('literal','comment') and not text[a:b].startswith(('<img',']('))]
            edits=[]
            for m in re.finditer(pattern,text):
                if not any(a<m.end() and b>m.start() for a,b in protected):
                    edits.append((m.start(),m.end(),replacement(m),{}))
            return markdown_compat.apply(text,edits)
        text=replace_visible(r'(!\[[^\]\n]*\]\()<?(assets/[^\s)>]+)>?',lambda m:m[1]+'parts/'+key+'/'+m[2])
        text=replace_visible(r'(\bsrc=["\'])(assets/[^"\']+)',lambda m:m[1]+'parts/'+key+'/'+m[2])
        text=replace_visible(r'\[\^([^\]]+)\]',lambda m:'[^'+key+'-'+m[1]+']')
        joined.append('<!-- owned-unit '+key+' -->\n'+text)
    result='\n\n'.join(joined)
    labels=anchors(result);fn=footnotes(result);tags=re.findall(r'\\tag\*?\s*\{([^}]+)\}',result)
    duplicate=lambda xs:sorted(k for k,v in Counter(xs).items() if v>1)
    undefined=sorted(set(re.findall(r'\]\(#([^)]*)\)',result))-set(labels))
    check={'duplicate_labels':duplicate(labels),'duplicate_equation_tags':duplicate(tags),'duplicate_footnotes':duplicate(fn),'undefined_references':undefined,
      'repeated_substantive_paragraphs':duplicates,'technical_changes':['Assembly image links prefixed with standalone part directory; footnote IDs namespaced per unit; original parts unchanged'],
      'numbering':'Printed explicit tags screened, automatic numbering not assumed'}
    check['usable']=not any(check[k] for k in ('duplicate_labels','duplicate_equation_tags','duplicate_footnotes','undefined_references','repeated_substantive_paragraphs'))
    return result,check


def tex_export(tex):
    """Bounded non-executing derivative; unsupported structures stay byte-exact.

    No macro expansion or include execution. A retained raw block makes the
    export partial. The original full TeX is always saved by the CLI caller.
    """
    from .book_completion import braced
    issues=[];body=tex
    if r'\begin{document}' in tex:
        if tex.count(r'\begin{document}')!=1 or tex.count(r'\end{document}')!=1:raise ValueError('Ambiguous TeX document envelope')
        pre,body=tex.split(r'\begin{document}',1);body,tail=body.split(r'\end{document}',1)
        if tail.strip():issues.append('Trailing TeX retained in original.tex')
        if re.search(r'\\(?:newcommand|renewcommand|def|newenvironment)',pre):issues.append('Preamble macro definitions require explicit qualification; original.tex retained')
    out=[];i=0;foot=[]
    while i<len(body):
        # Math spans copied literally (including tags); TeX display delimiters
        # become Markdown display delimiters without altering their contents.
        if body.startswith(('$$',r'\[',r'\('),i) or body[i]=='$':
            start=next((s for s in ('$$',r'\[',r'\(') if body.startswith(s,i)),'$');end={r'\[':r'\]',r'\(':r'\)'}.get(start,start);j=body.find(end,i+len(start))
            if j<0:issues.append('Unclosed math retained verbatim');out.append(body[i:]);break
            content=body[i+len(start):j];out.append(('\n$$\n'+content+'\n$$\n') if start in ('$$',r'\[') else '$'+content+'$');i=j+len(end);continue
        if body[i]!='\\':out.append(body[i]);i+=1;continue
        m=re.match(r'\\([A-Za-z]+\*?)',body[i:])
        if not m:
            out.append(body[i:i+2]);i+=2;continue
        cmd=m[1];a=i+len(m[0]);z=a
        while z<len(body) and body[z].isspace():z+=1
        arg=None;end=z
        if z<len(body) and body[z]=='{':
            try:arg,end=braced(body,z)
            except ValueError:pass
        if cmd in ('section','section*','subsection','subsection*','subsubsection','subsubsection*','paragraph','paragraph*') and arg is not None:
            level={'section':1,'subsection':2,'subsubsection':3,'paragraph':4}[cmd.rstrip('*')];out.append('\n\n'+'#'*level+' '+arg+'\n\n');i=end;continue
        if cmd in ('textbf','emph','textit','texttt') and arg is not None and '\\' not in arg:
            wrap={'textbf':'**','emph':'*','textit':'*','texttt':'`'}[cmd];out.append(wrap+arg+wrap);i=end;continue
        if cmd=='footnote' and arg is not None and '\\' not in arg:
            name='tex-'+str(len(foot)+1);foot.append('[^'+name+']: '+arg);out.append('[^'+name+']');i=end;continue
        if cmd=='label' and arg is not None:out.append('<a id="'+html.escape(arg,quote=True)+'"></a>');i=end;continue
        if cmd in ('ref','eqref') and arg is not None:out.append('['+('Equation ' if cmd=='eqref' else 'Reference ')+arg+'](#'+arg+')');i=end;continue
        if cmd=='includegraphics':
            if z<len(body) and body[z]=='[':
                z=body.find(']',z)+1
                while z<len(body) and body[z].isspace():z+=1
            if z<len(body) and body[z]=='{':
                arg,end=braced(body,z);out.append('![Source figure]('+arg+')');i=end;continue
        if cmd=='begin' and arg is not None:
            close=r'\end{'+arg+'}';j=body.find(close,end)
            if j>=0:
                block=body[i:j+len(close)]
                if arg in ('equation','equation*','align','align*','gather','gather*'):
                    content=body[end:j];env={'align':'aligned','gather':'gathered'}.get(arg.rstrip('*'))
                    if env:content=r'\begin{'+env+'}'+content+r'\end{'+env+'}'
                    if not arg.endswith('*') and not re.search(r'\\tag\*?\{',content):issues.append('Automatic equation number unavailable without compiler mapping; not invented')
                    out.append('\n$$\n'+content+'\n$$\n')
                else:
                    out.append('\n```raw-tex\n'+block+'\n```\n');issues.append('Unsupported environment retained verbatim: '+arg)
                i=j+len(close);continue
        # Retain a whole command + balanced argument; no guesses or silent loss.
        fragment=body[i:end] if arg is not None else body[i:a]
        out.append('\n```raw-tex\n'+fragment+'\n```\n');issues.append('Unsupported command retained: '+cmd);i=end if arg is not None else a
    result=''.join(out).strip()+'\n'+('\n'+'\n\n'.join(foot)+'\n' if foot else '')
    return result,{'status':'partial_unsupported' if issues else 'exported_not_source_reviewed','issues':sorted(set(issues)),
       'source_tex_sha256':digest(tex),'markdown_sha256':digest(result),'source_image_review':'not performed; existing TeX review does not become a Markdown image review',
       'checking':'Static bounded translation only; preserve original.tex and original evidence'}
