"""Finite book completion: source-span contracts and evidence-preserving checks.

This module has no transport, compiler, service or filesystem mutation entry point.
It does not treat target accounting or a critic's claims as semantic verification.
"""
import re
import unicodedata
from pathlib import PurePosixPath

from . import chapter_editorial as editorial, chapter_protocol
from .common import fingerprint

PROTOCOL = 'book-completion-v1'
TERMINAL = 'completion_finished_with_report'
OUTPUT_TOKENS = 131072
EFFORTS = {'convert': 'high', 'critic': 'max'}
FURNITURE = {'header', 'footer', 'page_number'}
CAPACITY = 1048576
DRAFT_RESERVE_BYTES = 524288


def braced(text, start):
    """Return one balanced TeX argument, respecting escaped braces."""
    if start >= len(text) or text[start] != '{':
        raise ValueError('Expected a braced argument')
    depth = 1
    i = start + 1
    while i < len(text):
        if text[i] == '\\':
            i += 2
            continue
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if not depth:
                return text[start+1:i], i+1
        i += 1
    raise ValueError('Unbalanced TeX argument')


def headings(text):
    result = []
    for m in re.finditer(r'\\(?:chapter|section|subsection|subsubsection|paragraph)\*?\s*\{', text):
        try:
            title, _ = braced(text, m.end()-1)
            result.append(title)
        except ValueError:
            result.append('[unbalanced heading]')
    return result


def plain(text):
    text = unicodedata.normalize('NFKD', text).casefold()
    text = re.sub(r'\\[a-zA-Z]+', ' ', text)
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()


def selected_blocks(native, ids):
    if len(ids) != len(set(ids)):
        raise ValueError('Repeated target block')
    wanted = set(ids)
    result = [b for b in native['blocks'] if b['id'] in wanted]
    if {b['id'] for b in result} != wanted:
        raise ValueError('Target block absent from exact native source')
    if [b['id'] for b in result] != list(ids):
        raise ValueError('Target source order changed')
    if any(b['kind'] in FURNITURE for b in result):
        raise ValueError('Page furniture is not a completion target')
    return result


def target(native, ids, *, title=None):
    blocks = selected_blocks(native, ids)
    if not blocks:
        raise ValueError('Empty output target')
    titles = [h for b in blocks if b['kind'] == 'paragraph_title' for h in headings(b['tex'])]
    text = '\n\n'.join(b['tex'] for b in blocks)
    return {'title': title or ' / '.join(titles) or native.get('title', native['key']),
            'first': ids[0], 'last': ids[-1], 'blocks': list(ids),
            'physical_pages': sorted({b['page']['original_physical_page'] for b in blocks}),
            'text': text, 'headings': titles, 'target_text_sha256': fingerprint(text),
            'scope_rule': 'Every assigned primary block, including nested sections and appendices; titles never narrow this span.'}


def validate_target(native, section):
    actual = target(native, section['blocks'])
    for key in ('first', 'last', 'physical_pages', 'text', 'headings', 'target_text_sha256'):
        if section.get(key) != actual[key]:
            raise ValueError('Contradictory/stale source scope: ' + key)
    # Descriptive labels are not dispatch scopes. Explicit exclusions are unsafe
    # even if a caller supplied an otherwise valid list of source block IDs.
    if re.search(r'(?i)exclude|context only|only\s+(?:section|chapter|§)', section.get('title', '')):
        raise ValueError('Contradictory output-scope label')
    return actual


def request(native, section, secondary, *, draft=None, notes='', phase='convert', context=''):
    validate_target(native, section)
    if phase not in EFFORTS or (phase == 'critic') != (draft is not None):
        raise ValueError('Conversion/critic draft dependency mismatch')
    scope = ('COMPLETE ASSIGNED SOURCE SPAN. Every block of PRIMARY EXTRACTION below is output, '
             'including all nested headings, appendix bodies, proofs, footnotes, formulas, tables, '
             'figures and captions. Neither this description nor a chapter/section title narrows it. '
             'Do not call an assigned appendix context-only. A digest is not a substitute for its body.\n'
             'Physical source pages: ' + ', '.join(map(str, section['physical_pages'])) + '\n'
             'Headings occurring inside the target (all included):\n' +
             '\n'.join('- ' + x for x in section['headings']) + '\n'
             'Only adjacent material in SECONDARY page excerpts or separately labelled context is '
             'context. Preserve the complete primary span; no model-side block markers are required.')
    body = editorial.request(section['text'], secondary, draft=draft, notes=notes,
                             section=scope, context=context, reasoning_effort=EFFORTS[phase])
    if body['model'] != 'glm53-regular' or body['max_tokens'] != OUTPUT_TOKENS or not body['stream']:
        raise ValueError('Completion settings changed')
    return body


def appendix_spans(native):
    """Actual source blocks, not whole boundary pages; digest recaps are separate."""
    blocks = [b for b in native['blocks'] if b['kind'] not in FURNITURE]
    starts = [(i, headings(b['tex'])[0]) for i, b in enumerate(blocks)
              if b['kind'] == 'paragraph_title' and headings(b['tex'])]
    digests = [i for i, h in starts if 'digest' in plain(h)]
    result = []
    for i, title in starts:
        if 'appendix' not in plain(title):
            continue
        later = [j for j, h in starts if j > i and ('appendix' in plain(h) or 'digest' in plain(h))]
        numbered = re.match(r'(\d+(?:\.\d+)+)\s', title)
        if numbered:
            depth = len(numbered[1].split('.'))
            later += [j for j, h in starts if j > i and (m := re.match(r'(\d+(?:\.\d+)+)\s', h))
                      and len(m[1].split('.')) <= depth]
        end = min(later) if later else len(blocks)
        item = target(native, [b['id'] for b in blocks[i:end]], title=title)
        item['recap'] = any(j < i for j in digests)
        result.append(item)
    return result


def contiguous_groups(native, ids):
    wanted = set(ids); groups = []; current = []
    for b in native['blocks']:
        if b['kind'] in FURNITURE:
            continue
        if b['id'] in wanted:
            current.append(b['id'])
        elif current:
            groups.append(current); current = []
    if current:
        groups.append(current)
    if {i for g in groups for i in g} != wanted:
        raise ValueError('Missing source block in grouping')
    return groups


def split_meaningfully(native, ids, *, fits):
    """Keep complete units where possible, otherwise split only at safe headings."""
    section = target(native, ids)
    if fits(section):
        return [section]
    blocks = selected_blocks(native, ids)
    boundaries = []
    proof = False
    for i, b in enumerate(blocks):
        text = plain(b['tex'])
        if re.match(r'proof\b', text):
            proof = True
        if re.search(r'\\(?:Box|square|blacksquare)\b|[□∎]|\bQ\.?E\.?D\.?', b['tex']):
            proof = False
        titles = headings(b['tex']) if b['kind'] == 'paragraph_title' else []
        if i and titles and not proof and not re.match(r'(?i)^(proof|theorem|lemma|remark|definition|proposition|corollary)', titles[0]):
            boundaries.append(i)
    # Balanced split on a source heading; recursive admission preserves all IDs.
    if not boundaries:
        raise chapter_protocol.ContextBudgetGap('Complete indivisible source unit cannot fit; no clipping or proof splitting')
    split = min(boundaries, key=lambda i: abs(i-len(ids)/2))
    parts = split_meaningfully(native, ids[:split], fits=fits) + split_meaningfully(native, ids[split:], fits=fits)
    if [b for p in parts for b in p['blocks']] != list(ids):
        raise ValueError('Capacity split changed source coverage')
    return parts


def image_references(document):
    document = re.sub(r'(?<!\\)%[^\n]*', '', document)
    result = []
    for m in re.finditer(r'\\includegraphics\*?(?:\s*\[[^\]]*\])?\s*\{', document):
        arg, _ = braced(document, m.end()-1)
        if arg.startswith(r'\detokenize{'):
            arg, _ = braced(arg, len(r'\detokenize'))
        result.append(arg)
    return result


def body_only(document):
    # Generated notes must not satisfy a required source-body heading/figure.
    markers = list(re.finditer(r'\\(?:section|subsection)\*?\{(?:Editorial|Accuracy|GLM accuracy|Notes and)', document, re.I))
    return document[:markers[0].start()] if markers else document


def coverage_check(document, native, ids):
    blocks = selected_blocks(native, ids); body = body_only(document)
    got_headings = [plain(h) for h in headings(body)]
    expected_headings = [h for b in blocks if b['kind'] == 'paragraph_title' for h in headings(b['tex'])]
    missing_headings = []
    for h in expected_headings:
        words = {w for w in plain(h).split() if not w.isdigit() and len(w) > 2}
        if words and not any(len(words & set(g.split())) / len(words) >= .65 for g in got_headings):
            missing_headings.append(h)
    empty_heading_bodies = []
    positions = list(re.finditer(r'\\(?:chapter|section|subsection|subsubsection)\*?\s*\{', body))
    for index, match in enumerate(positions):
        try:
            title, end = braced(body, match.end()-1)
        except ValueError:
            continue
        if 'appendix' in plain(title):
            following = positions[index+1].start() if index+1 < len(positions) else len(body)
            segment = body[end:following]
            # An immediate nested subsection can legitimately start the body.
            nested = following < len(body) and body[following:].startswith((r'\subsection', r'\subsubsection'))
            if not nested and len(plain(segment)) < 40:
                empty_heading_bodies.append(title)
    images = set(image_references(body)); basenames = {PurePosixPath(p).name for p in images}
    missing_charts = []
    tables = []
    for b in blocks:
        if b['kind'] in ('chart', 'image'):
            absent = [a for a in b.get('assets', []) if PurePosixPath(a).name not in basenames]
            if absent:
                missing_charts.append({'block': b['id'], 'assets': absent})
        if b['kind'] == 'table':
            tables.append(b)
    table_envs = len(re.findall(r'\\begin\{(?:tabular\*?|tabularx|longtable|array)\}', body))
    image_tables = sum(any(PurePosixPath(a).name in basenames for a in b.get('assets', [])) for b in tables)
    source_text = '\n'.join(b['tex'] for b in blocks)
    numbered = set(re.findall(r'\\tag\*?\{([^}]+)\}', source_text))
    explicit = set(re.findall(r'\\tag\*?\{([^}]+)\}', body))
    auto = bool(re.search(r'\\begin\{(?:equation|align|gather|multline)\}', body))
    labels = set(re.findall(r'\\label\{([^}]+)\}', body))
    references = set(re.findall(r'\\(?:ref|eqref|pageref|autoref)\{([^}]+)\}', body))
    missing_numbers = sorted(numbered-explicit) if explicit and not auto else []
    return {'target_blocks': len(ids), 'target_sha256': fingerprint(list(ids)),
            'missing_heading_candidates': missing_headings, 'missing_required_charts': missing_charts,
            'empty_appendix_body_candidates': empty_heading_bodies,
            'table_count_warning': len(tables) > table_envs+image_tables,
            'source_tables': len(tables), 'output_table_environments': table_envs, 'output_table_images': image_tables,
            'missing_explicit_equation_numbers': missing_numbers,
            'source_numbered_equations': sorted(numbered), 'output_explicit_equation_numbers': sorted(explicit),
            'equation_sequence_status': 'automatic or unnumbered equations require inspection' if auto or not explicit else 'explicit tag comparison only',
            'undefined_labels': sorted(references-labels),
            'source_equation_blocks': sum(b['kind'] == 'equation' for b in blocks),
            'formula_images': 'Equation/footnote crops may be replaced by editable mathematics; absent crop alone is not an omission.',
            'semantic_completeness': 'not established',
            'verification': 'deterministic risk indicators only; heading presence, tag counts and model claims are insufficient proof'}


def unique_coverage(selections):
    """One document per selected unit; overlap is never silently multiplied."""
    used = {}; documents = set()
    for row in selections:
        if row['unit'] in documents:
            raise ValueError('Duplicate grouped document in edition: ' + row['unit'])
        documents.add(row['unit'])
        for block in row['blocks']:
            if block in used:
                raise ValueError('Overlapping adopted source ownership: ' + block)
            used[block] = row['unit']
    return used


def replace_exact(text, old, new):
    if not old or text.count(old) != 1:
        raise ValueError('Reviewed repair anchor absent or ambiguous')
    return text.replace(old, new, 1)


def supported_ornament(document):
    """Only the observed U+2767 ornament; no general Unicode/math filtering."""
    visible = re.sub(r'(?<!\\)%[^\n]*', '', document)
    if '❧' not in visible or r'\DeclareUnicodeCharacter{2767}' in visible or r'\newunicodechar{❧}' in visible:
        return document, []
    old = r'\begin{document}'
    new = r'\DeclareUnicodeCharacter{2767}{\ensuremath{\clubsuit}}' + '\n' + old
    return replace_exact(document, old, new), [{'old': old, 'new': new,
        'reason': 'Supported pdfLaTeX fallback for decorative U+2767; original characters and mathematical text retained.'}]


def repair_known(key, text):
    """Observed, exact technical edits. No fuzzy/global mathematical rewrite."""
    edits = []
    def fix(old, new, reason):
        nonlocal text
        text = replace_exact(text, old, new)
        edits.append({'old': old, 'new': new, 'reason': reason})
    if key == 'bergomi-02-s01':
        fix(r'\newcommand{\glmnote}[1]{\par\noindent\textcolor{blue}{\small\itshape [GLM editorial note: #1]\par}}',
            r'\newcommand{\glmnote}[1]{\par\noindent{\color{blue}\small\itshape [GLM editorial note: #1]\par}}',
            'Use a color declaration in a group; textcolor cannot enclose a paragraph break. Note text unchanged.')
    elif key == 'bergomi-02-s08':
        fix(r'\newcommand{\glmnote}[1]{\par\noindent\textcolor{blue!70!black}{\small\textbf{[GLM note]} #1\par}}',
            r'\newcommand{\glmnote}[1]{\par\noindent{\color{blue!70!black}\small\textbf{[GLM note]} #1\par}}',
            'Preserve the one-argument macro and its note; paragraph-capable color group.')
    elif key == 'bergomi-02-s14':
        fix('artifact; no source-image inspection is required.}',
            'artifact; no source-image inspection is required.',
            'Remove unmatched closing brace: glmcorrection takes only the preceding C1 argument; explanatory prose is outside that argument.')
        fix(r'\begin{document}', r'\DeclareUnicodeCharacter{2767}{\ensuremath{\clubsuit}}' + '\n' + r'\begin{document}',
            'The next real compiler failure exposed an unsupported ornamental separator; preserve its characters with the standard pdfLaTeX fallback.')
    elif key == 'bergomi-02-s12':
        if re.search(r'\\usepackage(?:\[[^\]]*\])?\{[^}]*\bamssymb\b', text):
            raise ValueError('Observed missing AMS symbol package already supplied')
        marker = r'\begin{document}'
        fix(marker, '\\usepackage{amssymb}\n'+marker, 'blacktriangleright is an AMS symbol; supply its standard package, without redefining the symbol.')
    elif key == 'c-recap-03-bergomi-08':
        repaired, changes = supported_ornament(text)
        if not changes:
            raise ValueError('Observed ornamental Unicode defect absent or already mapped')
        text = repaired; edits.extend(changes)
    elif key == 'd-large-03-bergomi-07':
        fix('\\tag{7.1}\n\\end{aligned}', '\\end{aligned}\n\\tag{7.1}', 'Move equation label outside aligned but inside the existing equation environment.')
    elif key == 'd-large-04-bergomi-07':
        fix('``100\\textcompss\'\'', '``100\\texttt{\\textbackslash{}textcompss}\'\'',
            'Undefined macro occurs only in a quoted extraction reading in an editorial note; display its literal name rather than invent a mathematical macro.')
    elif key == 'd-large-09-bergomi-09':
        for number in ('9.15', '9.33'):
            fix(r'\end{align*}\tag{'+number+'}', r'\tag{'+number+'}'+ '\n' + r'\end{align*}', 'Move misplaced tag into its existing align environment; equations unchanged.')
        note = ('the source caption reads ``formula (9.20)\'\'; the SSR is given by\n'
                '(9.21), while (9.20) is the ATMF skew -- corrected accordingly.')
        old = r'\glmnote{' + note + '}'
        fix(old, '', 'Remove the fragile footnote macro from the moving caption argument; its complete text is relocated immediately below the caption.')
        anchor = '-- see Section 9.8 below.}\n\\end{figure}'
        restored = ('-- see Section 9.8 below.}\n'
                    r'\par\smallskip\noindent{\footnotesize\textbf{GLM editorial correction (recorded claim):} '
                    + note + '}\\par\n\\end{figure}')
        fix(anchor, restored, 'Preserve the full editorial correction beside its figure; glmnote is defined as footnote and cannot safely expand inside caption.')
    return text, edits
