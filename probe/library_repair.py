"""Source-bound deterministic qualification and repair helpers, no inference."""
import hashlib,json,re
from pathlib import Path
from .common import sha,fingerprint

def blank_page(pdf_path,page,expected_sha):
    import fitz
    if sha(pdf_path)!=expected_sha:raise ValueError('Original PDF identity changed')
    with fitz.open(pdf_path) as pdf:
        p=pdf[page-1];image=p.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
        text=p.get_text();images=p.get_images();drawings=p.get_drawings();white=all(v==255 for v in image.samples)
        # Objects are conservative blockers even when painted white or hidden.
        blank=not text.strip() and not images and not drawings and white and not list(p.annots() or [])
        return {'source_sha256':expected_sha,'physical_page':page,'qualified_blank':blank,'native_characters':len(text),'image_objects':len(images),'drawing_objects':len(drawings),'all_white_render':white,'render_dpi':144,'render_sha256':hashlib.sha256(image.samples).hexdigest(),'page_rect':list(p.rect),'disposition':'source_verified_blank_no_inference' if blank else 'substantive_or_unqualified_do_not_skip'}

def math_spans(text):
    """Recognise unescaped TeX math delimiters; linebreak spacing is not display math."""
    opening=None;spans=[];issues=[];i=0
    while i<len(text):
        token=None;end=i+1
        if text[i]=='\\':
            j=i
            while j<len(text) and text[j]=='\\':j+=1
            if (j-i)%2 and j<len(text) and text[j] in '[]()':token='\\'+text[j];end=j+1
            else:i=j+1 if (j-i)%2 and j<len(text) and text[j] in '$%' else j;continue
        elif text[i]=='$':token='$$' if text[i:i+2]=='$$' else '$';end=i+len(token)
        if token:
            if opening is None:
                if token in ('\\]','\\)'):issues.append('Unmatched mathematical delimiter '+token)
                else:opening=(token,end)
            else:
                expected={'\\[':'\\]','\\(':'\\)'}.get(opening[0],opening[0])
                if token==expected:spans.append(text[opening[1]:i]);opening=None
                elif token in ('\\]','\\)'):issues.append('Mismatched mathematical delimiter '+token)
        i=end
    if opening:issues.append('Unclosed mathematical delimiter '+opening[0])
    return spans,issues

def unbalanced_math_groups(span):
    depth=0
    for m in re.finditer(r'[{}]',span):
        i=m.start()-1
        while i>=0 and span[i]=='\\':i-=1
        if (m.start()-i-1)%2:continue
        depth+=1 if m[0]=='{' else -1
        if depth<0:return True
    return depth!=0

def equation_labels(text):
    # Strip only wrappers. Preserve appendix and hierarchical namespaces.
    text=re.sub(r'\\(?:tag\*?|mathrm|text|operatorname)\s*\{([^{}]*)\}',r'\1',text)
    text=text.replace('\\(','').replace('\\)','').replace('\\[','').replace('\\]','')
    return {re.sub(r'\s+','',m[0]) for m in re.finditer(r'(?<![A-Za-z0-9.])(?:[A-Z]\s*\.\s*)?\d+(?:\s*\.\s*\d+)*(?:\s*[a-z])?(?![A-Za-z0-9.])',text)}

def salvage_json(answer,expected_hash):
    """Remove a single outer fence or isolate one uniquely valid object; no invented keys."""
    from .focused_recovery import single_outer_fence
    attempts=[answer,single_outer_fence(answer)]
    # Decoder handles surrounding commentary only when exactly one JSON object exists.
    decoder=json.JSONDecoder();objects=[];i=0
    while i<len(answer):
        start=answer.find('{',i)
        if start<0:break
        try:value,end=decoder.raw_decode(answer[start:]);objects.append(value);i=start+end
        except ValueError:i=start+1
    if len(objects)==1:attempts.append(json.dumps(objects[0]))
    matches=[]
    for candidate in attempts:
        if not candidate:continue
        try:value=json.loads(candidate)
        except ValueError:continue
        if isinstance(value,dict) and value.get('base_sha256')==expected_hash and isinstance(value.get('findings'),list) and value not in matches:matches.append(value)
    if len(matches)!=1:raise ValueError('No uniquely recoverable response with the exact draft hash; retain failure')
    return matches[0]

def overlap_screen(units):
    """Actual emitted equation tags and substantial repeated paragraphs, not input partitions."""
    from .book_completion import body_only,plain
    tags={};paragraphs={}
    for key,text in units:
        body=body_only(text)
        for tag in set(re.findall(r'\\tag\s*\*?\s*\{\s*([^}]+?)\s*\}',body)):tags.setdefault(re.sub(r'\s+','',tag),[]).append(key)
        for paragraph in re.split(r'\n\s*\n',body):
            clean=plain(paragraph)
            if len(clean)>220:paragraphs.setdefault(clean,[]).append(key)
    return {'duplicate_equation_tags':{k:v for k,v in tags.items() if len(set(v))>1},'repeated_substantive_paragraphs':[{'text':k,'units':sorted(set(v))} for k,v in paragraphs.items() if len(set(v))>1],'meaning':'Screening only; verify source and reconcile complete statements, not just labels'}

def lossless_images(images,destination):
    """Smaller PNG representation with exact decoded-pixel equality, no resizing."""
    from PIL import Image
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True);result=[]
    for i,item in enumerate(images):
        src=Path(item['path'])
        if sha(src)!=item['sha256']:raise ValueError('Source image identity changed')
        with Image.open(src) as im:
            im.load();raw=im.tobytes();rgb=im.convert('RGB');path=destination/(str(i)+'-lossless.png')
            im.save(path,optimize=True,compress_level=9)
            if im.mode in ('RGB','L') and rgb.getcolors(maxcolors=256) is not None:
                candidate=destination/(str(i)+'-palette.png');rgb.convert('P',palette=Image.Palette.ADAPTIVE,colors=256,dither=Image.Dither.NONE).save(candidate,optimize=True)
                with Image.open(candidate) as check:
                    if check.convert(im.mode).tobytes()==raw and candidate.stat().st_size<path.stat().st_size:path=candidate
            with Image.open(path) as check:
                if check.size!=im.size or check.convert(im.mode).tobytes()!=raw:raise ValueError('Lossless packing changed image pixels')
            chosen=path if path.stat().st_size<src.stat().st_size else src
            result.append(dict(item,path=str(chosen),sha256=sha(chosen),original_image_path=str(src),original_image_sha256=item['sha256'],pixel_sha256=hashlib.sha256(raw).hexdigest(),dimensions=list(im.size),resizing='none; verified identical decoded pixels'))
    return result
