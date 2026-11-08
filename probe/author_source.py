"""Static, non-executing author-source intake and substantive dependency checks.

Archive bounds/path rules follow the existing source-availability audit. This is
not a TeX interpreter or a compiler: raw files remain authoritative and unchanged.
"""
import gzip,hashlib,io,re,tarfile,zipfile
from pathlib import Path,PurePosixPath
from .common import sha
from .book_completion import braced

MAX_EXPANDED=128*1024*1024
def safe_name(name):
    p=PurePosixPath(name)
    return bool(name and not p.is_absolute() and '..' not in p.parts and '\\' not in name and not re.match(r'^[A-Za-z]:',name))

def unpack(raw):
    """Return bounded file bytes; never extract links or execute package commands."""
    if raw.lstrip().startswith((b'%PDF-',b'<!DOCTYPE',b'<!doctype',b'<html')):raise ValueError('Source response is PDF/HTML, not TeX')
    if raw[:2]==b'\x1f\x8b':
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:raw=stream.read(MAX_EXPANDED+1)
    if len(raw)>MAX_EXPANDED:raise ValueError('Source expansion cap exceeded')
    files={}
    def add(name,data):
        name=str(PurePosixPath(name))
        if not safe_name(name) or name in files:raise ValueError('Unsafe/duplicate source member '+name)
        files[name]=data
        if len(files)>10000 or sum(map(len,files.values()))>MAX_EXPANDED:raise ValueError('Archive expansion/member cap exceeded')
    if raw[:2]==b'PK':
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for entry in archive.infolist():
                if entry.is_dir():continue
                if (entry.external_attr>>16)&0o170000==0o120000 or entry.file_size>MAX_EXPANDED:raise ValueError('Archive link/oversized member')
                add(entry.filename,archive.read(entry))
    else:
        try:
            archive=tarfile.open(fileobj=io.BytesIO(raw),mode='r:')
        except tarfile.ReadError:archive=None
        if archive:
            with archive:
                for entry in archive:
                    if not safe_name(entry.name) or entry.issym() or entry.islnk() or not(entry.isfile() or entry.isdir()):raise ValueError('Unsafe archive member')
                    if entry.isdir():continue
                    if entry.size>MAX_EXPANDED:raise ValueError('Oversized archive member')
                    add(entry.name,archive.extractfile(entry).read())
        elif b'\\documentclass' in raw or b'\\documentstyle' in raw:add('source.tex',raw)
        else:raise ValueError('Unrecognised source package')
    return files

def decode(raw):
    try:return raw.decode('utf-8-sig'),'utf-8'
    except UnicodeDecodeError:return raw.decode('latin-1'),'latin-1'

def mask_verbatim(text):
    patterns=[r'\\begin\{(verbatim\*?|Verbatim|lstlisting|minted|alltt)\}.*?\\end\{\1\}',r'\\verb\*?(?P<d>[^A-Za-z\s])(?P<body>.*?)(?P=d)']
    for pattern in patterns:text=re.sub(pattern,lambda m:''.join('\n' if c=='\n' else ' ' for c in m[0]),text,flags=re.S)
    return text

def active_text(text):
    """Comments/explicit inactive branches only. No mathematical macro expansion."""
    lines=[];literal=mask_verbatim(text);offset=0
    for line in text.splitlines(True):
        cut=len(line)
        for m in re.finditer('%',line):
            if literal[offset+m.start()]!='%':continue
            n=m.start()-1
            while n>=0 and line[n]=='\\':n-=1
            if (m.start()-n-1)%2==0:cut=m.start();break
        lines.append(line[:cut]+('\n' if cut<len(line) else ''))
        offset+=len(line)
    text=''.join(lines)
    for m in reversed(list(re.finditer(r'\\begin\{comment\}.*?\\end\{comment\}',mask_verbatim(text),flags=re.S))):text=text[:m.start()]+text[m.end():]
    tokens=list(re.finditer(r'\\(?:iffalse\b|if[a-zA-Z]*\b|fi\b)',mask_verbatim(text)));excluded=[];start=None;depth=0
    for m in tokens:
        if start is None:
            if m[0]==r'\iffalse':start=m.start();depth=1
        elif m[0]==r'\fi':
            depth-=1
            if depth==0:excluded.append((start,m.end()));start=None
        else:depth+=1
    if start is not None:excluded.append((start,len(text)))
    for a,b in reversed(excluded):text=text[:a]+text[b:]
    return text

def inspect_tree(root,entry,*,evidence_assets=None):
    root=Path(root).resolve();files={str(p.relative_to(root)):p for p in root.rglob('*') if p.is_file() and not p.is_symlink()}
    if not safe_name(entry) or entry not in files:raise ValueError('Missing/unsafe entry point')
    evidence_assets=evidence_assets or {};missing=[];uncertain=[];resolved=[];ordered=[];macros={};graphic_dirs=[''];visiting=[];visited=[];styles=[];annotations=[]
    def resolve(base,target,suffixes,graphic=False):
        target=target.strip()
        for _ in range(8):
            changed=re.sub(r'\\([A-Za-z]+)',lambda m:Path(entry).stem if m[1]=='jobname' else macros.get(m[1],m[0]),target)
            if changed==target:break
            target=changed
        if '\\' in target or '#' in target or not safe_name(target):return None
        candidates=[]
        for prefix in ([str(PurePosixPath(base).parent),''] if not graphic else [str(PurePosixPath(base).parent/d) for d in graphic_dirs]+graphic_dirs+[str(PurePosixPath(base).parent),'']):
            for suffix in suffixes:
                name=str(PurePosixPath(prefix)/(target+suffix))
                if name in files and name not in candidates:candidates.append(name)
        if len(candidates)==1:return candidates[0]
        if len(candidates)>1:
            # Exact relative match follows TeX's local package context; never
            # silently choose unrelated same-basename files elsewhere.
            local=str(PurePosixPath(base).parent/target)
            if local in candidates:return local
            # Multiple extensions of the same file (not different directories)
            # are normal graphics/BibTeX alternatives. Prefer the listed format.
            if len({str(PurePosixPath(x).with_suffix('')) for x in candidates})==1:return candidates[0]
            uncertain.append({'file':base,'target':target,'reason':'Multiple in-package candidates','candidates':candidates})
        if not candidates:
            # Unique case-insensitive extension/path resolution is recorded,
            # not implemented by renaming or modifying the author's files.
            wanted={str(PurePosixPath(prefix)/(target+s)).casefold() for prefix in [str(PurePosixPath(base).parent),'']+graphic_dirs for s in suffixes}
            matches=[n for n in files if n.casefold() in wanted]
            if len(matches)==1:return matches[0]
        return None
    def include(base,target,command):
        suffix=('', '.tex') if command in ('input','include','subfile','subfileinclude') else ('','.bbl','.bib')
        found=resolve(base,target,suffix)
        if not found and command in ('bibliography','addbibresource'):
            bbl=str(PurePosixPath(entry).with_suffix('.bbl'))
            if bbl in files:found=bbl
        if not found:
            missing.append({'file':base,'command':command,'target':target,'kind':'bibliography' if command in ('bibliography','addbibresource') else 'included_text'});return
        resolved.append({'file':base,'command':command,'target':target,'path':found,'sha256':sha(files[found])});walk(found)
    def walk(name):
        if name in visiting:uncertain.append({'file':name,'reason':'Recursive include cycle'});return
        visiting.append(name);visited.append(name);raw,encoding=decode(files[name].read_bytes());text=active_text(raw)
        # Literal directory/macro definitions, retained in the ordered source.
        for m in re.finditer(r'\\(?:newcommand|renewcommand|providecommand)\*?\s*\{\\([A-Za-z]+)\}\s*\{([^{}]*)\}|\\def\s*\\([A-Za-z]+)\s*\{([^{}]*)\}',text):
            key,value=(m[1],m[2]) if m[1] else (m[3],m[4])
            if not re.search(r'[\\#$]',value):macros[key]=value
        for m in re.finditer(r'\\graphicspath\s*\{',text):
            try:value,_=braced(text,m.end()-1);graphic_dirs[:]=re.findall(r'\{([^{}]*)\}',value) or ['']
            except ValueError:uncertain.append({'file':name,'reason':'Unparsed graphicspath'})
        # Only analysis masks macro definitions so their parameterised example
        # input/graphics commands are not falsely treated as executed references.
        analysis=mask_verbatim(text)
        for m in reversed(list(re.finditer(r'\\(?:newcommand|renewcommand|providecommand)\*?\s*\{\\[^{}]+\}(?:\s*\[[^]]*\]){0,2}\s*\{',text))):
            try:_,end=braced(text,m.end()-1);analysis=analysis[:m.start()]+' '*(end-m.start())+analysis[end:]
            except ValueError:uncertain.append({'file':name,'reason':'Unbalanced macro definition'})
        commands=list(re.finditer(r'\\(input|include|subfileinclude|subfile|includegraphics|bibliography|addbibresource|usepackage|RequirePackage)(?![A-Za-z])\*?(?:\s*\[[^]]*\])?\s*(?:\{([^{}]+)\}|([^\s{}%]+))',analysis))
        cursor=0;ordered.append('% BEGIN FILE '+name+'; decoding='+encoding+'\n')
        for m in commands:
            command=m[1];target=m[2] or m[3];ordered.append(text[cursor:m.start()]);cursor=m.end()
            if command in ('input','include','subfile','subfileinclude','bibliography','addbibresource'):
                ordered.append('% ORIGINAL REFERENCE '+m[0]+'\n')
                for part in target.split(','):include(name,part,command)
            else:
                ordered.append(text[m.start():m.end()])
                if command=='includegraphics':
                    found=resolve(name,target,('', '.pdf','.eps','.png','.jpg','.jpeg','.svg'),True)
                    if found:resolved.append({'file':name,'command':command,'target':target,'path':found,'sha256':sha(files[found])})
                    elif target in evidence_assets:resolved.append({'file':name,'command':command,'target':target,'evidence':evidence_assets[target],'kind':'same-version reading-PDF evidence; original image file absent'})
                    else:missing.append({'file':name,'command':command,'target':target,'kind':'figure'})
                else:
                    for part in target.split(','):
                        found=resolve(name,part,('', '.sty'))
                        if found:
                            styles.append(found);resolved.append({'file':name,'command':command,'target':part,'path':found,'sha256':sha(files[found])})
                        else:annotations.append({'package':part,'availability':'not tested; standard style availability does not gate content'})
        ordered.append(text[cursor:]+'\n% END FILE '+name+'\n');visiting.pop()
    walk(entry)
    for name in sorted(set(styles)):
        text,encoding=decode(files[name].read_bytes());ordered.append('% IN-PACKAGE STYLE/MACRO DEFINITIONS '+name+'\n'+text+'\n')
    all_text='\n'.join(ordered);main=active_text(decode(files[entry].read_bytes())[0])
    if not re.search(r'\\begin\s*\{document\}',main) or not re.search(r'\\end\s*\{document\}',main):missing.append({'file':entry,'kind':'document_envelope','reason':'Missing beginning/end'})
    record={'entry':entry,'visited_text_files':visited,'custom_definition_files':sorted(set(styles)),'resolved_dependencies':resolved,
      'missing_substantive':missing,'unresolved_content_dependencies':uncertain,'style_notes':annotations,
      'beginning_present':r'\begin{document}' in all_text,'end_present':r'\end{document}' in all_text,
      'appendix_markers':len(re.findall(r'\\appendix\b|[Aa]ppendix',all_text)),
      'bibliography_present':bool(re.search(r'\\(?:bibitem|begin\{thebibliography\}|begin\{refsection\})|@[A-Za-z]+\s*\{',all_text)),
      'section_titles':re.findall(r'\\(?:sub)*section\*?\s*\{([^{}]*)\}',all_text),
      'complete_content_dependencies':not missing and not uncertain,'compilation':'not_requested',
      'limits':'Static source-package coverage, not mathematical verification. No destructive macro expansion or commands executed. Raw multi-file package retained.'}
    return record,all_text

def generated_content(document,assets,*,root=None,require_envelope=True):
    """Content blockers independent of style packages, fonts and PDF build status."""
    issues=[];text=mask_verbatim(active_text(document))
    if require_envelope and (text.count(r'\begin{document}')!=1 or text.count(r'\end{document}')!=1):issues.append('Incomplete document envelope')
    # Detect damaged display structures, without treating layout/style commands
    # or plain editorial syntax as mathematical verification failures.
    for env in ('equation','equation*','align','align*','aligned','gather','gather*','multline','multline*','split','array'):
        if text.count(r'\begin{'+env+'}')!=text.count(r'\end{'+env+'}'):issues.append('Unbalanced mathematical environment '+env)
    from .library_repair import math_spans,unbalanced_math_groups
    spans,delimiter_issues=math_spans(text);issues+=delimiter_issues
    for span in spans:
        if unbalanced_math_groups(span):issues.append('Unbalanced grouping within mathematics')
    from .book_completion import image_references
    for name in image_references(document):
        if name not in assets or not Path(assets[name]).is_file():issues.append('Missing required figure '+name)
    for m in re.finditer(r'\\(input|include|bibliography|addbibresource)\s*\{([^{}]+)\}',text):
        for name in m[2].split(','):
            suffixes=('', '.tex') if m[1] in ('input','include') else ('','.bib','.bbl')
            if not any(name+s in assets and Path(assets[name+s]).is_file() for s in suffixes):issues.append('Missing substantive '+m[1]+' '+name)
    return {'usable':not issues,'content_issues':issues,'mathematical_confidence':'not independently established','compilation_required':False}
