"""Bounded, source-aware Markdown compatibility. No model or renderer calls.

Formatting derivatives are not newly reviewed source. Ambiguous notes/joins are
findings, never guessed links. Code, comments, existing math and currency survive.
"""
import hashlib
import json
import re
from collections import Counter

POLICY = 'obsidian-compat-v2'
MAX_BYTES = 2 * 1024 * 1024


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def escaped(text, i):
    j = i - 1
    while j >= 0 and text[j] == '\\':
        j -= 1
    return (i - j - 1) % 2 == 1


def segments(text):
    """Yield (kind, start, end), retaining exact offsets and literal bytes."""
    i = 0
    while i < len(text):
        start = i
        if i == 0 or text[i - 1] == '\n':
            fence = re.match(r'( {0,3}(?:> ?)*)(`{3,}|~{3,})[^\n]*(?:\n|$)', text[i:])
            if fence:
                marker = fence[2]
                close = re.search(r'(?m)^' + re.escape(fence[1]) + re.escape(marker[0]) + '{' + str(len(marker)) + r',}[ \t]*$', text[i + fence.end():])
                i = i + fence.end() + close.end() if close else len(text)
                yield 'literal', start, i
                continue
            if re.match(r'(?: {4}|\t)\S', text[i:]):
                i = text.find('\n', i)
                if i < 0: i = len(text)
                yield 'literal', start, i
                continue
        if text.startswith('<!--', i) or text.startswith('%%', i):
            ending = '-->' if text.startswith('<!--', i) else '%%'
            j = text.find(ending, i + (4 if ending == '-->' else 2))
            i = j + len(ending) if j >= 0 else len(text)
            yield 'comment', start, i
            continue
        if text[i] == '`' and not escaped(text, i):
            token = re.match(r'`+', text[i:])[0]
            match = re.search(r'(?<!`)' + re.escape(token) + r'(?!`)', text[i + len(token):])
            i = i + len(token) + match.end() if match else i + len(token)
            yield 'literal', start, i
            continue
        if text.startswith(('\\(', '\\['), i) and not escaped(text, i):
            opening = text[i:i + 2]; ending = '\\)' if opening == '\\(' else '\\]'
            j = text.find(ending, i + 2)
            if j >= 0:
                i = j + 2
                yield 'paren_math' if opening == '\\(' else 'display_math', start, i
                continue
        if text[i] == '$' and not escaped(text, i):
            delimiter = '$$' if text.startswith('$$', i) else '$'
            j = i + len(delimiter)
            while j < len(text):
                if text.startswith(delimiter, j) and not escaped(text, j): break
                j += 1
            if j < len(text):
                i = j + len(delimiter)
                yield 'dollar_math', start, i
                continue
        if text[i] == '<':
            code = re.match(r'<(pre|code)\b[^>]*>', text[i:], re.I)
            if code:
                close = re.search(r'</' + code[1] + r'\s*>', text[i+code.end():], re.I)
                i = i + code.end() + close.end() if close else len(text)
                yield 'literal', start, i
                continue
            tag = re.match(r'</?[A-Za-z][^<>\n]*>', text[i:])
            if tag:
                i += tag.end(); yield 'literal', start, i; continue
        if text.startswith('](', i):
            # Literal link destinations are not mathematical source.
            j = i + 2; depth = 1
            while j < len(text) and depth:
                if not escaped(text, j):
                    depth += (text[j] == '(') - (text[j] == ')')
                j += 1
            i = j; yield 'literal', start, i; continue
        if text[i] == '\\' and i + 1 < len(text) and text[i + 1] in '\\$`':
            i += 2; yield 'literal', start, i; continue
        i += 1
        yield 'text', start, i


def visible(text):
    """Same offsets, excluding literal examples/comments from validation."""
    out = list(text)
    for kind, a, b in segments(text):
        if kind in ('literal', 'comment'):
            out[a:b] = ['\n' if c == '\n' else ' ' for c in text[a:b]]
    return ''.join(out)


def inline_math(text):
    from .library_repair import unbalanced_math_groups
    edits, findings = [], []
    for kind, a, b in segments(text):
        if kind != 'paren_math': continue
        body = text[a + 2:b - 2].strip(' \t\r\n')
        if (not body or len(body) > 8192 or '\n\n' in body or
                re.search(r'(?<!\\)\$|\\[()]', body) or unbalanced_math_groups(body)):
            findings.append({'kind': 'ambiguous_inline_math', 'offset': a})
        else:
            edits.append((a, b, '$' + body + '$', {'kind': 'inline_math_delimiters', 'offset': a,
                           'original': text[a:b], 'replacement': '$' + body + '$'}))
    return apply(text, edits), [e[3] for e in edits], findings


def apply(text, edits):
    last = len(text) + 1
    for a, b, replacement, _ in sorted(edits, reverse=True, key=lambda x: x[0]):
        if not (0 <= a < b <= len(text)) or b > last:
            raise ValueError('Overlapping or invalid compatibility edits')
        text = text[:a] + replacement + text[b:]; last = a
    return text


def canonical(text):
    text = inline_math(text)[0]
    return ' '.join(text.split())


def words(text):
    text = re.sub(r'\\[A-Za-z]+\*?', ' ', text)
    return re.findall(r'\w+', text.casefold())


SUP = re.compile(r'(?<!\$)\$\s*\^\s*\{(\d+)\}\s*\$(?!\$)')


def source_notes(unit):
    """Layout-classified definitions plus independently located body references."""
    blocks = unit.get('native_blocks', [])
    notes = []
    for b in blocks:
        if b['kind'] not in ('page_footnote', 'footnote', 'vision_footnote'): continue
        text = inline_math(b['tex'])[0].strip(); marker = SUP.match(text)
        note = {'block': b['id'], 'page': b.get('page'), 'label': marker[1] if marker else None,
                'text': text[marker.end():].strip() if marker else text, 'references': []}
        if marker:
            for ref in blocks:
                if ref['kind'] in ('page_footnote', 'footnote', 'vision_footnote'): continue
                source = inline_math(ref['tex'])[0]
                for m in SUP.finditer(visible(source)):
                    if m[1] == marker[1]:
                        note['references'].append({'block': ref['id'], 'page': ref.get('page'),
                           'before': words(source[:m.start()])[-6:], 'after': words(source[m.end():])[:6]})
        notes.append(note)
    return notes


def paragraphs(text):
    return list(re.finditer(r'(?ms)^\S.*?(?=\n[ \t]*\n|\Z)', text))


def context_matches(text, a, b, reference):
    left, right = reference['before'], reference['after']
    return bool(left or right) and (not left or words(text[:a])[-len(left):] == left) and (
        not right or words(text[b:])[:len(right)] == right)


def link_notes(text, unit):
    edits, logs, findings, appended = [], [], [], []
    notes = source_notes(unit); labels = Counter(n['label'] for n in notes if n['label'])
    masked = visible(text)
    for note in notes:
        label = note['label']
        if not label:
            # Unnumbered source notes have no invented reference. Move only a
            # unique exact paragraph; keep its source locator visible outside prose.
            matches = [p for p in paragraphs(text) if canonical(p[0].removeprefix('> ').strip('*')) == canonical(note['text'])]
            title = '**Unnumbered source note (physical page ' + str(note.get('page', {}).get('original_physical_page', 'unknown')) + ')**'
            if len(matches) == 1 and title not in text and masked[matches[0].start():matches[0].end()].strip():
                p = matches[0]; edits.append((p.start(), p.end(), '', note))
                appended.append(title + '\n\n' + note['text'])
                logs.append(dict(note, kind='relocate_unnumbered_source_note', reference='None printed; none invented'))
            continue
        if re.search(r'(?m)^\[\^' + re.escape(label) + r'\]:', masked): continue
        # Existing valid identifiers need not equal the printed numeric label.
        # Coverage below still verifies body and source-reference placement.
        existing = [p for p in paragraphs(text) if re.match(r'\[\^[^\]]+\]:', masked[p.start():p.end()])]
        if any(canonical(re.sub(r'^\[\^[^\]]+\]:\s*', '', p[0])) == canonical(note['text']) for p in existing):
            continue
        matches = []
        for p in paragraphs(text):
            m = SUP.match(masked, p.start())
            if m and m[1] == label and canonical(text[m.end():p.end()]) == canonical(note['text']):
                matches.append((p, m))
        if labels[label] != 1 or len(matches) != 1 or len(note['references']) != 1:
            findings.append(dict(note, kind='ambiguous_footnote_mapping')); continue
        p, marker = matches[0]; candidates = []
        for ref in note['references']:
            found = [m for m in SUP.finditer(masked) if m[1] == label and not (p.start() <= m.start() < p.end()) and context_matches(text, m.start(), m.end(), ref)]
            if len(found) != 1: candidates = []; break
            candidates.append(found[0])
        if len(candidates) != len(note['references']) or len({m.start() for m in candidates}) != len(candidates):
            findings.append(dict(note, kind='ambiguous_footnote_reference')); continue
        edits.append((p.start(), p.end(), '', note))
        for m in candidates: edits.append((m.start(), m.end(), '[^' + label + ']', note))
        body = text[marker.end():p.end()].strip()
        appended.append('[^' + label + ']: ' + body.replace('\n', '\n    '))
        logs.append(dict(note, kind='linked_source_footnote', references_bound=len(candidates)))
    result = apply(text, edits)
    if appended: result = result.rstrip() + '\n\n' + '\n\n'.join(appended) + '\n'
    return result, logs, findings


def html_math_tables(text):
    """Convert only rectangular, plain-cell HTML math tables to native Markdown.

    Unknown HTML, merged cells, nested tables and ambiguous mathematics stay
    verbatim with a rendering finding. No formulas, labels or cell order guessed.
    """
    from html.parser import HTMLParser

    class Table(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.stack = []; self.rows = []; self.caption = ''; self.cell = None
            self.kinds = []; self.row_kinds = []; self.bad = False
        def handle_starttag(self, tag, attrs):
            parents = {'table': None, 'caption': 'table', 'thead': 'table',
                       'tbody': 'table', 'tr': ('table','thead','tbody'),
                       'th': 'tr', 'td': 'tr'}
            parent = self.stack[-1] if self.stack else None
            allowed = parents.get(tag, 'FORBIDDEN')
            if allowed != parent and not (isinstance(allowed,tuple) and parent in allowed):
                self.bad = True
            if attrs and not (tag == 'th' and attrs == [('scope','col')]): self.bad = True
            self.stack.append(tag)
            if tag == 'tr': self.rows.append([]); self.row_kinds = []
            if tag in ('th','td'): self.cell = ''; self.row_kinds.append(tag)
        def handle_endtag(self, tag):
            if not self.stack or self.stack[-1] != tag: self.bad = True; return
            self.stack.pop()
            if tag in ('th','td'):
                if not self.rows: self.bad = True
                else: self.rows[-1].append(self.cell or '')
                self.cell = None
            if tag == 'tr': self.kinds.append(self.row_kinds)
        def handle_data(self, data):
            if self.cell is not None: self.cell += data
            elif self.stack and self.stack[-1] == 'caption': self.caption += data
            elif data.strip(): self.bad = True
        def handle_comment(self, data): self.bad = True
        def handle_entityref(self, name): self.bad = True

    def cell(value):
        out = []
        for kind,a,b in segments(value):
            piece = value[a:b]
            if kind in ('literal','comment') and ('`' in piece or '<' in piece):
                raise ValueError('literal/markup cell requires manual presentation')
            if kind in ('dollar_math','paren_math','display_math'):
                if piece.startswith('$$') or kind == 'display_math' or '\n' in piece:
                    raise ValueError('display/multiline cell requires manual presentation')
                if re.search(r'\\(?:text|operatorname|mathrm)\{[^}]*\|',piece):
                    raise ValueError('text-mode pipe in math requires manual presentation')
                # Native Markdown table parsers split pipes before math parsing.
                # Equivalent TeX control words avoid both table splitting and
                # accidental loss of the norm delimiter's backslash.
                piece = piece.replace('\\|', '\\Vert ').replace('|','\\vert ')
            else:
                piece = piece.replace('|','&#124;').replace('\n',' ')
            out.append(piece)
        return ''.join(out).strip()

    protected = [(a,b) for k,a,b in segments(text) if k in ('literal','comment')
                 and not re.fullmatch(r'</?[A-Za-z][^<>\n]*>', text[a:b])]
    edits=[]; findings=[]
    for m in re.finditer(r'<table\b[^>]*>.*?</table\s*>',text,re.I|re.S):
        if any(a <= m.start() < b for a,b in protected): continue
        raw=m[0]
        if not any(k in ('dollar_math','paren_math','display_math') for k,_,_ in segments(raw)): continue
        parser=Table()
        try:
            parser.feed(raw); parser.close()
            width=len(parser.rows[0]) if parser.rows else 0
            if (parser.bad or parser.stack or width < 2 or width > 8 or len(parser.rows)<2
                or len(parser.rows)>100 or any(len(r)!=width for r in parser.rows)
                or parser.kinds[0]!=['th']*width
                or any(k!=['td']*width for k in parser.kinds[1:])):
                raise ValueError('unsupported or nonrectangular HTML table')
            rows=[[cell(c) for c in row] for row in parser.rows]
            caption=parser.caption.strip()
            if '\n' in caption or any(c in caption for c in '<>`'): raise ValueError('complex caption')
            lines=['| '+' | '.join(row)+' |' for row in rows]
            lines.insert(1,'| '+' | '.join(['---']*width)+' |')
            replacement=(caption+'\n\n' if caption else '')+'\n'.join(lines)
            edits.append((m.start(),m.end(),replacement,{'kind':'html_math_table_to_markdown',
                'offset':m.start(),'rows':len(rows)-1,'columns':width,'caption':caption,
                'before_sha256':digest(raw),'after_sha256':digest(replacement),
                'pipe_notation':'TeX vertical bars become equivalent vert/Vert control words; prose pipes use HTML entity'}))
        except (ValueError,IndexError,TypeError) as exc:
            findings.append({'kind':'unrendered_html_table_math','offset':m.start(),'reason':str(exc)})
    return apply(text,edits),[e[3] for e in edits],findings


def html_table_math_findings(text):
    _,changes,pending=html_math_tables(text)
    return pending+[{'kind':'unrendered_html_table_math','offset':c['offset'],
        'reason':'Simple table requires native Markdown normalization'} for c in changes]


def normalize(text, unit=None):
    if len(text.encode()) > MAX_BYTES: raise ValueError('Markdown compatibility bound exceeded')
    unit = unit or {}; original = text
    text, logs, findings = inline_math(text)
    text, changes, pending = html_math_tables(text); logs += changes; findings += pending
    text, changes, pending = link_notes(text, unit); logs += changes; findings += pending
    # Only complete, source-backed standalone headings. Nested TeX/unknown
    # hierarchy remains an explicit finding, not a speculative conversion.
    source_titles = set()
    for block in unit.get('native_blocks', []):
        m = re.fullmatch(r'\\(?:sub)*section\*?\{([^{}\n]+)\}', block['tex'].strip())
        if m: source_titles.add(canonical(m[1]))
    edits = []; recipe_level = None
    for m in re.finditer(r'(?m)^(?:#{1,6} .+|\\(?:sub)*section\*?\{[^{}\n]+\})[ \t]*$', visible(text)):
        raw = text[m.start():m.end()]
        existing = re.match(r'^(#{1,6})\s+(\d+\s+.+)', raw)
        if existing: recipe_level = len(existing[1]); continue
        h = re.fullmatch(r'\\(section|subsection|subsubsection)\*?\{([^{}\n]+)\}[ \t]*', raw)
        if not h: continue
        title = h[2]
        if canonical(title) not in source_titles:
            findings.append({'kind': 'unbound_tex_heading', 'title': title}); continue
        level = {'section': 2, 'subsection': 3, 'subsubsection': 4}[h[1]]
        if title.strip().rstrip(':').casefold() in ('notes', 'note'):
            if recipe_level is None:
                findings.append({'kind': 'ambiguous_note_heading_hierarchy', 'title': title}); continue
            level = min(6, recipe_level + 1)
        elif re.match(r'\d+\s+', title): recipe_level = level
        replacement = '#' * level + ' ' + title
        log = {'kind': 'source_heading', 'original': raw, 'replacement': replacement}
        edits.append((m.start(), m.end(), replacement, log)); logs.append(log)
    text = apply(text, edits)
    # Joins require explicit source-checked block identity; never infer them just
    # from lowercase text, page adjacency, or an extraction merge flag.
    evidence = unit.get('markdown_compatibility_evidence', {})
    block_map = {b['id']: b for b in unit.get('native_blocks', [])}
    for join in evidence.get('joins', []):
        for block_id, expected in join.get('block_sha256', {}).items():
            if block_id not in block_map or digest(block_map[block_id]['tex']) != expected:
                raise ValueError('Stale/unowned source join evidence')
        if not join.get('source_image_checked') or len(join.get('block_sha256', {})) < 2:
            raise ValueError('Unqualified source join')
        left, right = join['left'], join['right']
        pattern = re.escape(left) + r'(?P<gap>\n[ \t\r\n]+)' + re.escape(right)
        matches = list(re.finditer(pattern, visible(text)))
        if not matches and text.count(left + ' ' + right) == 1: continue
        if len(matches) != 1:
            findings.append({'kind': 'ambiguous_source_join', 'evidence': join}); continue
        m = matches[0]; a, b = m.span('gap')
        text = text[:a] + ' ' + text[b:]
        logs.append({'kind': 'source_checked_paragraph_join', 'evidence': join})
    return text, {'policy': POLICY, 'input_sha256': digest(original), 'output_sha256': digest(text),
                  'changed': original != text, 'transformations': logs, 'unresolved': findings,
                  'source_structure_sha256': digest(json.dumps(unit.get('native_blocks', []), sort_keys=True)),
                  'review_status': 'Formatting derivative; historical review does not attest these transformed bytes',
                  'fidelity': 'Not established by formatting compatibility'}


def footnote_coverage(text, unit):
    notes = source_notes(unit); mask = visible(text); definitions = []
    for p in paragraphs(text):
        m = re.match(r'\[\^([^\]]+)\]:\s*', mask[p.start():p.end()])
        if m: definitions.append((m[1], text[p.start() + m.end():p.end()]))
    missing, references = [], []
    for note in notes:
        if note['label'] is None:
            if canonical(note['text']) not in canonical(mask): missing.append(note)
            continue
        found = [(label, body) for label, body in definitions if canonical(body) == canonical(note['text'])]
        if len(found) != 1:
            missing.append(note); continue
        label, body = found[0]
        matches = list(re.finditer(r'\[\^' + re.escape(label) + r'\](?!:)', mask))
        if len(note['references']) != 1 or any(sum(context_matches(text, m.start(), m.end(), ref) for m in matches) != 1 for ref in note['references']):
            references.append(note)
    return {'source_notes': len(notes), 'source_numbered_notes': sum(n['label'] is not None for n in notes),
            'markdown_definitions': len(definitions), 'missing_or_changed_definitions': missing,
            'unbound_references': references, 'claim': 'Source-structure/text mapping, not independent source-image verification'}


def paragraph_boundary_findings(text, unit):
    """Report a possible split, never merge merely on lowercase/page proximity.

    These are non-blocking source-check candidates, not proven omissions or
    formatting errors. Explicit qualified joins use normalize's bound evidence.
    """
    ignored = {'header','footer','page_number','page_footnote','footnote','vision_footnote'}
    blocks = [b for b in unit.get('native_blocks', []) if b['kind'] not in ignored]
    findings = []; mask = visible(text)
    for left,right in zip(blocks,blocks[1:]):
        if left['kind'] != 'text' or right['kind'] != 'text': continue
        a = left.get('page',{}).get('original_physical_page')
        b = right.get('page',{}).get('original_physical_page')
        if not isinstance(a,int) or b != a+1: continue
        before,after = canonical(left['tex']),canonical(right['tex'])
        if not before or not after or not after[0].islower() or before[-1] in '.?!:;': continue
        tail,head = before.split()[-8:],after.split()[:8]
        if len(tail)<3 or len(head)<3: continue
        pattern = r'\s+'.join(map(re.escape,tail)) + r'\n[ \t\r\n]*\n[ \t\r\n]*' + r'\s+'.join(map(re.escape,head))
        if re.search(pattern,mask):
            findings.append({'kind':'possible_source_paragraph_split','blocks':[left['id'],right['id']],
              'physical_pages':[a,b],'left_context':' '.join(tail),'right_context':' '.join(head),
              'disposition':'Needs original-image decision; preserved unchanged, not a proven omission'})
    return findings
