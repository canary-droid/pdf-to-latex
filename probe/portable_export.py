"""Small English/math derivative profile for saved MiddleJson; no OCR imports.

Native DocVortex exports stay in evidence/. Its fixed CJK preamble and auxiliary
block filtering are unsuitable here, so this profile renders a limited explicit
set of structured types; unsupported content stays visible and unresolved.
"""
import html
import json
import re

from .common import atomic_json, files_manifest, sha
from .saved_pages import copy_evidence, render_region, saved_pages

TEXT_ESCAPES = {'\\':r'\textbackslash{}', '{':r'\{', '}':r'\}', '$':r'\$', '&':r'\&',
                '#':r'\#', '_':r'\_', '%':r'\%', '~':r'\textasciitilde{}', '^':r'\textasciicircum{}'}
BASE_MATH = set('frac sqrt left right int iint iiint oint sum prod lim infty sin cos tan log exp min max sup inf det gcd alpha beta gamma delta epsilon varepsilon zeta eta theta vartheta iota kappa lambda mu nu xi pi varpi rho varrho sigma varsigma tau upsilon phi varphi chi psi omega Gamma Delta Theta Lambda Xi Pi Sigma Upsilon Phi Psi Omega bar hat widehat tilde widetilde vec dot ddot overline underline prime cdot times div pm mp leq geq neq approx sim simeq equiv in notin subset supset subseteq supseteq cup cap emptyset forall exists neg land lor to mapsto rightarrow leftarrow leftrightarrow Rightarrow Leftarrow Leftrightarrow partial nabla ell Re Im mid vert Vert lvert rvert lVert rVert langle rangle mathrm mathbf mathcal mathit mathsf mathtt mathop mathopen mathclose mathrel mathbin mathord mathpunct limits nolimits displaystyle textstyle scriptstyle scriptscriptstyle quad qquad thinspace hline begin end'.split())
AMS_MATH = set('text tag tag* dfrac tfrac binom dbinom tbinom operatorname overset underset substack eqref boxed'.split())
AMS_SYMBOLS = set('mathbb mathfrak varnothing lesssim gtrsim nleq ngeq'.split())
ENVIRONMENTS = {'array', 'matrix', 'pmatrix', 'bmatrix', 'vmatrix', 'Vmatrix', 'cases', 'aligned', 'gathered', 'split'}
BASE_MATH.update('liminf limsup wedge vee ge le ldots cdots dots Big Bigl Bigr big bigl bigr bigg biggl biggr Bigg Biggl Biggr downarrow uparrow'.split())
BASE_MATH.update({'textbf','textit','negthinspace'})
AMS_MATH.add('boldsymbol')
PROSE_COMMANDS = {'textbf', 'textit', 'textsc', 'emph', 'texttt', 'textnormal',
                  'section', 'subsection', 'paragraph', 'footnote'}
LITERAL_COMMANDS = {'textbackslash', 'textasciitilde', 'textasciicircum'}
PROSE_SPACING = {'quad', 'qquad', 'thinspace'}
# Explicit pdfLaTeX UTF-8/T1 repertoire; no guessed Unicode-to-math conversion.
UNICODE_PROSE = set('ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿŒœŠšŽž–—‘’“”')
ENGINE_POLICY = 'pdflatex-utf8-t1-latin-v1'


def prose_characters(value):
    if any((ord(c) > 126 and c not in UNICODE_PROSE) or
           (ord(c) < 32 and c not in '\n\r') for c in value):
        raise ValueError('Unsupported Unicode/control character in prose; raw recognition retained')
    return {'inputenc', 'fontenc'} if any(ord(c) > 126 for c in value) else set()


def escape_text(text):
    return ''.join(TEXT_ESCAPES.get(c, c) for c in text)


def math_fragment(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Empty/image-only mathematics is not editable transcription')
    if any(ord(c) > 126 or (ord(c) < 32 and c not in '\n\r') for c in text):
        raise ValueError('Unsupported Unicode/control character in math; raw recognition retained')
    # Consume escaped backslashes as tokens: \\\\ferential is a line break,
    # not a macro named ferential. Its ambiguous hyphenation stays unchanged.
    commands = {m.group(1) for m in re.finditer(r'\\([A-Za-z]+)|\\[^A-Za-z]', text) if m.group(1)}
    unknown = commands - BASE_MATH - AMS_MATH - AMS_SYMBOLS
    if unknown:
        raise ValueError('Unsupported math macros: ' + ', '.join(sorted(unknown)))
    if re.search(r'(?<!\\)[%#$]', text):
        raise ValueError('Unsupported raw TeX delimiter/control character in math')
    # Validate rather than repair delimiters. No body substitutions are made.
    depth = 0
    environments = []
    for token in re.finditer(r'\\begin\{([^}]+)\}|\\end\{([^}]+)\}|\\[^A-Za-z]|[{}]', text):
        opening, closing = token.group(1), token.group(2)
        if opening:
            if opening not in ENVIRONMENTS:
                raise ValueError('Unsupported math environment: ' + opening)
            environments.append(opening)
        elif closing:
            if not environments or environments.pop() != closing:
                raise ValueError('Unbalanced math environments')
        elif token.group() == '{':
            depth += 1
        elif token.group() == '}':
            depth -= 1
            if depth < 0:
                raise ValueError('Unbalanced math braces')
    if depth or environments:
        raise ValueError('Unbalanced math delimiters')
    packages = set()
    if commands & AMS_MATH or any(x != 'array' for x in re.findall(r'\\begin\{([^}]+)\}', text)):
        packages.add('amsmath')
    if commands & AMS_SYMBOLS:
        packages.add('amssymb')
    return text, packages


def inline_content(content):
    if isinstance(content, str):
        content = [{'type':'text', 'content':content}]
    if not isinstance(content, list):
        raise ValueError('Unsupported native inline content')
    parts, packages = [], set()
    for span in content:
        if not isinstance(span, dict) or not isinstance(span.get('content'), str):
            raise ValueError('Unsupported nested inline span; complete native data retained')
        value = span['content']
        if span['type'] == 'text':
            packages |= prose_characters(value)
            rendered = escape_text(value)
            for style in span.get('styles', []):
                if style not in ('bold', 'italic'):
                    raise ValueError('Unsupported inline style: ' + style)
                rendered = ('\\textbf{' if style == 'bold' else '\\textit{') + rendered + '}'
            parts.append(rendered)
        elif span['type'] == 'equation_inline':
            value, needed = math_fragment(value)
            packages |= needed
            parts.append(r'\(' + value + r'\)')
        else:
            raise ValueError('Unsupported inline kind: ' + span['type'])
    return ''.join(parts), packages


def render_block(block):
    kind, native = block['kind'], block['native']
    if kind == 'equation':
        text, packages = math_fragment(native.get('content'))
        return '\\[\n' + text + '\n\\]', packages
    if kind in ('text', 'paragraph_title', 'doc_title', 'aside_text', 'page_number',
                'header', 'footer', 'page_footnote', 'ref_text'):
        text, packages = inline_content(native.get('content'))
        if kind in ('paragraph_title', 'doc_title'):
            text = r'\section*{' + text + '}'
        return text, packages
    raise ValueError('Unsupported block kind: ' + kind)


def accepted_fragment(text):
    """Parse a bounded text/math grammar without rewriting. Not a TeX sandbox."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Empty replacement requires explicit delete operation')
    packages = set()
    body = text.strip()
    rotated = re.fullmatch(r'\\rotatebox\{(0|90|180|270)\}\{(.*)\}', body, re.S)
    if rotated:
        body = rotated.group(2)
        packages.add('graphicx')
    if body.startswith(r'\[') and body.endswith(r'\]'):
        _, needed = math_fragment(body[2:-2])
        return text, packages | needed
    packages |= prose_characters(body)

    def parse(pos, nested=False, depth=0):
        if depth > 64:
            raise ValueError('Excessively nested prose')
        while pos < len(body):
            c = body[pos]
            if c == '}':
                if nested:
                    return pos + 1
                raise ValueError('Unbalanced prose braces')
            if c == '{':
                pos = parse(pos + 1, True, depth + 1)
            elif body.startswith(r'\(', pos) or c == '$':
                opening, closing = (r'\(', r'\)') if c == '\\' else ('$', '$')
                start = pos + len(opening)
                # Escaped punctuation does not close a math span.
                match = re.search(r'(?<!\\)' + re.escape(closing), body[start:])
                if match is None:
                    raise ValueError('Unbalanced inline math in replacement')
                end = start + match.start()
                _, needed = math_fragment(body[start:end])
                packages.update(needed)
                pos = end + len(closing)
            elif c == '\\':
                if pos + 1 < len(body) and body[pos+1] in ' %&#_{}$\\':
                    pos += 2
                    continue
                accent = re.match(r'''\\[\'`"^~=.]''', body[pos:]) or re.match(r'\\[uvHckbd]\b', body[pos:])
                if accent:
                    pos += len(accent.group())
                    while pos < len(body) and body[pos] == ' ': pos += 1
                    arg = re.match(r'(?:\{(?:[A-Za-z]|\\[ij])\}|[A-Za-z])', body[pos:])
                    if not arg:
                        raise ValueError('Unsupported/malformed prose accent argument')
                    pos += len(arg.group())
                    continue
                command = re.match(r'\\([A-Za-z]+)(\*?)', body[pos:])
                if not command:
                    raise ValueError('Unsupported prose escape')
                name, star = command.groups()
                if name in PROSE_SPACING and not star:
                    pos += len(command.group())
                    continue
                if name not in PROSE_COMMANDS | LITERAL_COMMANDS or (star and name not in {'section','subsection','paragraph'}):
                    raise ValueError('Unsupported replacement prose macro: ' + name)
                pos += len(command.group())
                while pos < len(body) and body[pos] in ' \n\r': pos += 1
                if pos >= len(body) or body[pos] != '{':
                    raise ValueError('Missing prose command argument: ' + name)
                if name in LITERAL_COMMANDS:
                    if body[pos:pos+2] != '{}': raise ValueError('Literal command requires empty argument')
                    pos += 2
                else:
                    pos = parse(pos + 1, True, depth + 1)
            elif c in '%&#_^~':
                raise ValueError('Raw TeX control or mathematics outside math mode')
            else:
                pos += 1
        if nested:
            raise ValueError('Unbalanced prose braces')
        return pos

    parse(0)
    return text, packages


def typed_fragment(text, kind='latex_fragment'):
    """Explicit typed transformation; callers retain the original proposal bytes.

    Legacy callers use complete LaTeX. Only a verified equation block/contract
    can supply math_body. Never infer a math body from punctuation or backslashes.
    """
    if kind == 'math_body':
        _, packages = math_fragment(text)
        return {'latex': '\\[\n' + text + '\n\\]', 'packages': sorted(packages),
                'fragment_kind':kind, 'transformation':'add_display_wrappers', 'original':text}
    if kind != 'latex_fragment':
        raise ValueError('Unsupported fragment kind')
    _, packages = accepted_fragment(text)
    return {'latex':text, 'packages':sorted(packages), 'fragment_kind':kind,
            'transformation':'none', 'original':text}


def safe_compiler_fragment(text):
    """Allow malformed syntax to reach the isolated compiler, never new commands.

    This is an additional admission filter; container isolation is still required.
    It does not certify syntax or make the fragment eligible for final export.
    """
    if not isinstance(text,str) or len(text)>48000 or '\x00' in text:return False
    commands={m.group(1) for m in re.finditer(r'\\([A-Za-z]+)|\\[^A-Za-z]',text) if m.group(1)}
    allowed=BASE_MATH|AMS_MATH|AMS_SYMBOLS|PROSE_COMMANDS|LITERAL_COMMANDS|PROSE_SPACING|set('uvHckbdij')
    if commands-allowed:return False
    return all(name in ENVIRONMENTS for name in re.findall(r'\\(?:begin|end)\s*\{([^}]+)\}',text))


def portable_document(body, packages, notice='Experimental UNACCEPTED draft; compilation not yet assessed.'):
    """Shared portable template for exports and isolated compiler fixtures."""
    lines = ['% ' + notice, r'\documentclass[11pt]{article}']
    for package in sorted(set(packages)):
        option = '[utf8]' if package == 'inputenc' else '[T1]' if package == 'fontenc' else ''
        lines.append(r'\usepackage' + option + '{' + package + '}')
    return '\n\n'.join([*lines, r'\begin{document}', *body, r'\end{document}']) + '\n'


def export_saved(root, run, out, sources, *, accepted_edits=None, unresolved_issues=None):
    pages = saved_pages(root, run, sources)
    edits = accepted_edits or {}
    issues = unresolved_issues or []
    blocks = {b['id']:b for p in pages for b in p['blocks']}
    if set(edits) - set(blocks):
        raise ValueError('Unknown edit target')
    # Validate the entire edit set before emitting any page; no partial groups.
    for edit in edits.values():
        if edit['operation'] == 'replace':
            accepted_fragment(edit['latex'])
        elif edit['operation'] != 'delete' or edit['latex'] != '':
            raise ValueError('Unsupported edit operation or nonempty deletion')
    copy_evidence(run, pages, out)
    inventory = []
    sections = ['<!doctype html><meta charset="utf-8"><title>Portable OCR derivative</title>',
                '<h1>Portable OCR derivative — UNREVIEWED</h1>',
                '<p>No mathematical corrections or acceptance. Compilation not run. Native OCR is retained in evidence/.</p>']
    if edits:
        sections[1:3] = ['<h1>Derivative with explicitly accepted corrections</h1>',
            '<p>Only the recorded selections were applied. Unchanged content remains unreviewed. '
            'Compilation NOT RUN. Original proposals remain UNACCEPTED in saved evidence; '
            '<a href="acceptance.json">separate acceptance record</a> | '
            '<a href="review-evidence/review.html">original review and detail crops</a>.</p>']
    if issues:
        sections.append('<h2>Unresolved issues — no correction applied</h2><pre>'+html.escape(json.dumps(issues,ensure_ascii=False,indent=2))+'</pre>')
    for page in pages:
        folder = out/'pages'/page['page_id']
        folder.mkdir(parents=True)
        atomic_json(folder/'page.json', page)
        window = out/'evidence'/page['unit']/'input.pdf'
        render_region(window, page['page']['local_page_idx'], folder/'source.png')
        body, unresolved, packages = [], [], set()
        sections.append('<h2>'+html.escape(page['page_id'])+'</h2><p><a href="pages/'+page['page_id']+'/document.tex">Portable LaTeX</a> | <a href="pages/'+page['page_id']+'/page.json">Complete native page data</a></p><img style="max-width:650px" src="pages/'+page['page_id']+'/source.png" alt="Source page">')
        for block in page['blocks']:
            entry = {'page_id':page['page_id'], 'block_id':block['id'], 'kind':block['kind'],
                     'source_block_index':block['source_block_index'], 'reading_order':block['reading_order'],
                     'source_attempt':page['source_attempt'], 'bbox':block['bbox'],
                     'bbox_pdf_points':block['bbox_pdf_points'],
                     'coordinate_system':page['coordinate_system'], 'status':'represented', 'reason':None}
            try:
                before, _ = render_block(block)
            except ValueError:
                before = None
            edit = edits.get(block['id'])
            entry.update(before_latex=before, latex=before, operation='unchanged')
            if edit:
                entry.update(operation=edit['operation'], proposal_id=edit['proposal_id'], latex=edit['latex'])
            try:
                if edit and edit['operation'] == 'delete':
                    entry.update(status='explicitly_deleted', reason='Explicitly accepted deletion; original block retained in evidence and inventory')
                    body.append('% Explicitly deleted source block: '+block['id']+'\n')
                    fragment, needed = '', set()
                elif edit:
                    fragment, needed = accepted_fragment(edit['latex'])
                    entry.update(status='applied', reason='Explicitly accepted replacement')
                else:
                    fragment, needed = render_block(block)
                if not fragment.strip() and entry['status'] != 'explicitly_deleted':
                    raise ValueError('Empty recognition; source region must be reviewed')
                packages |= needed
                if entry['status'] != 'explicitly_deleted':
                    body.append('% Source block: '+block['id']+'\n'+fragment+'\n')
                if block['kind'] == 'aside_text' and not edit:
                    entry.update(status='unresolved', reason='Aside recognition included verbatim; rotated/substantive transcription requires source review')
            except ValueError as exc:
                entry.update(status='unresolved', reason=str(exc))
            if entry['status'] == 'unresolved':
                crop_name = f"block-{block['reading_order']}.png"
                render_region(window, page['page']['local_page_idx'], folder/crop_name, bbox=block['bbox'], max_edge=1000)
                packages.add('graphicx')
                raw = json.dumps(block['native'], ensure_ascii=True, indent=2)
                unresolved.append(r'\paragraph{'+escape_text(block['id'])+'} '+escape_text(entry['reason'])+'\n'
                                  +r'\includegraphics[width=0.8\linewidth,height=0.35\textheight,keepaspectratio]{'+crop_name+'}\n'
                                  +r'\par Raw recognition (JSON; Unicode uses explicit backslash-u escapes):\par'+'\n'
                                  +'\n'.join(r'\noindent\texttt{'+escape_text(line)+r'}\par' for line in raw.splitlines()))
                entry['source_region_image'] = 'pages/'+page['page_id']+'/'+crop_name
            inventory.append(entry)
            sections.append('<article><h3>'+html.escape(block['id'])+' — '+entry['status']+'</h3><p>'+html.escape(entry['reason'] or 'Included without mathematical repair; unreviewed')+'</p><pre>'+html.escape(json.dumps(block['native'],ensure_ascii=False,indent=2))+'</pre></article>')
            if edits:
                sections.append('<p>Before LaTeX:</p><pre>'+html.escape(before or '(unresolved; raw recognition above)')+
                    '</pre><p>After LaTeX:</p><pre>'+html.escape(entry['latex'] if entry['latex'] else '(explicit deletion)' if edit else '(unresolved)')+'</pre>')
        if unresolved:
            body += [r'\section*{Unresolved content -- source review required}', *unresolved]
        (folder/'document.tex').write_text(portable_document(body, packages,
            'Portable English/math draft. Source fidelity UNREVIEWED; compilation NOT RUN.'),encoding='utf-8')
        atomic_json(folder/'export-settings.json', {'profile':'english-math-v1', 'packages':sorted(packages),
            'body_rewrites':[{'block_id':b['id'], **edits[b['id']]} for b in page['blocks'] if b['id'] in edits],
            'unsupported_policy':'explicit unresolved content, raw recognition and source image',
            'compilation':'not_run'})
    atomic_json(out/'inventory.json', inventory)
    atomic_json(out/'provenance.json', {'source_run':str(run), 'source_state_sha256':sha(run/'state.json'),
                'profile':'english-math-v1', 'pages':pages, 'export_code_sha256':sha(__file__)})
    atomic_json(out/'summary.json', {'status':'exported_unreviewed', 'pages':len(pages),
                'represented_blocks':sum(x['status']=='represented' for x in inventory),
                'unresolved_blocks':sum(x['status']=='unresolved' for x in inventory),
                'applied_replacements':sum(x['status']=='applied' for x in inventory),
                'explicitly_deleted_blocks':sum(x['status']=='explicitly_deleted' for x in inventory),
                'unresolved_issues':issues,
                'omitted_blocks':0, 'compilation':'not_run', 'fidelity':'unreviewed'})
    (out/'review.html').write_text('\n'.join(sections),encoding='utf-8')
    atomic_json(out/'artifact-manifest.json', files_manifest(out))
    return pages
