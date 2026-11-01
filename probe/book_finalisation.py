"""Case-specific offline finalisation of saved books, without model policy changes."""
import re
from . import book_completion as completion, chapter_editorial as edit

TIMER = 'bergomi-05-completion-f3a9ca342f'
JUMPS = 'bergomi-10-completion-078213f7b4'
CORRELATION = 'bergomi-11-completion-24436293b1'
FLEURONS = 'bergomi-09-completion-31d8aa8410'
EPILOGUE = 'bergomi-epilogue-completion-c59855f987'
BIBLIOGRAPHY = 'bergomi-bibliography-completion-6028d415d8'


def append_note(document, ident, text, *, attribution='Codex local check', tex=None):
    entry = {'id': ident, 'text': text, 'category': 'material', 'status': 'informational',
             'attribution': attribution, 'independent_verification': False}
    if tex:
        entry['note_tex'] = tex
    return edit.annotate(document, [entry])


def repair_document(key, document, *, raw_critic=None):
    """Exact demonstrated edits; return explicit dispositions for provenance."""
    changes = []
    def replace(old, new, reason):
        nonlocal document
        document = completion.replace_exact(document, old, new)
        changes.append({'old': old, 'new': new, 'reason': reason})

    if key == FLEURONS:
        document, changes = completion.supported_ornament(document)
        if not changes:
            raise ValueError('Expected unmapped ornamental U+2767 in the saved selection')
    elif key == TIMER:
        if not raw_critic:
            raise ValueError('Actual saved critic document required')
        core = raw_critic[:raw_critic.rfind(r'\end{document}')]
        if not document.startswith(core):
            raise ValueError('Timer selection differs from the raw critic before its generated-note suffix')
        old = document
        document = raw_critic
        changes.append({'old_suffix': old[len(core):], 'new_suffix': r'\end{document}',
                        'reason': 'Retain the complete readable in-document accuracy log; remove only the duplicate generated suffix. All prior raw/structured logs remain separately preserved.'})
        document = append_note(document, 'source-check-timer-20261101',
            'Local original-PDF images (physical 199--201, printed 182--184) were inspected on 1 November 2026. '
            'They support the restored drift-only footnote 23, time-change/path-functional footnote 25, and the distinction '
            'between the fixed quadratic-variation budget and running quadratic variation. The printed final integral on '
            'physical 199 has dt although its variable and limits use u; the existing du correction is retained. '
            'This check concerns these passages, not every claim in the GLM accuracy log.')
    elif key == JUMPS:
        needle = r'\glmcorrection{Footnote 17, eq.~(10.27)'
        start = document.index(needle)
        _, end = completion.braced(document, start + len(r'\glmcorrection'))
        old = document[start:end]
        new = r'''\glmcorrection{Footnote 17, eq.~(10.27), printed p.~414 (physical PDF p.~431).
The corrected displayed equation is retained. Inverting the preceding forward
equation with the Dupire relation gives
$\sigma^2=\sigma^2_{\rm loc}-2\lambda[(1+J)C_{K/(1+J),T}-(1+J)C_{K,T}+JK\partial_K C]/(K^2\partial_K^2C)$.
Its order-$J$ terms cancel and its small-jump limit is
$\sigma^2_{\rm loc}-\lambda J^2$. Footnote 17's displaced text and references are
retained with the footnote.}
\par\smallskip\noindent{\small\textbf{Codex source-image check, 1 November 2026.}
The original PDF image on physical page 431 shows the overall factor $2\lambda$
outside the fraction and an additional $\lambda$ multiplying $JK\partial_K C$
inside its numerator:
$2\lambda\{[(1+J)C_{K/(1+J),T}-C_{K,T}]-JC+\lambda JK\partial_K C\}/(K^2\partial_K^2C)$.
That extra inner factor is printed in the source; the extraction also flattened
the grouping. The printed expression conflicts with the displayed forward
equation and the stated small-jump check. The existing locally derived correction
removes the extra inner factor and is not undone. Original readings and the
source image remain in the linked provenance.}\par'''
        replace(old, new, 'Resolve the requested source-image question without changing the justified corrected equation.')
        replace(r'\emph{Applied; exact printed typesetting pending source-image check.}',
                r'\emph{Applied; Codex image check confirms a printed extra inner $\lambda$.}',
                'Update the corresponding accuracy-log disposition after actual local image inspection.')
        old = r'\noindent{\small The only open verification is the exact printed typesetting of (10.27) on physical page 431; its mathematical content is settled by the derivation recorded in the linked GLM note.}'
        new = r'\noindent{\small The requested image check of (10.27) on physical page 431 is now recorded above. The locally derived correction is retained; this is not a verification of the whole book.}'
        replace(old, new, 'Remove the stale pending-image-check statement; preserve the limited scope of this check.')
    elif key == CORRELATION:
        old = (r'$x_i^\tau$, $x_j^\tau$ their $\tau$-th daily return. $x_i^\tau,\, x_j^\tau$ are assumed' + '\n'
               'to be iid standard normal random variables with')
        new = (r'$x_i^\tau$, $x_j^\tau$ their $\tau$-th daily return. The return vectors are independent' + '\n'
               r'and identically distributed across time $\tau$, with standard normal marginals' + '\n'
               'and the stated correlation across assets:')
        replace(old, new, 'Clarify time independence versus asset correlation; epsilon_ii, all moments and the bias/variance derivations are unchanged.')
    elif key == 'd-large-04-bergomi-07':
        if r'\renewcommand{\thetable}' in document or r'\setcounter{table}' in document:
            raise ValueError('Expected original unnumbered-prefix article table counters')
        replacement = (r'\renewcommand{\thetable}{7.\arabic{table}}' + '\n' + r'\setcounter{table}{1}' + '\n' +
                       r'\renewcommand{\thefigure}{7.\arabic{figure}}' + '\n' + r'\setcounter{figure}{5}' + '\n' + r'\begin{document}')
        replace(r'\begin{document}', replacement,
                'Five complete tables are 7.2--7.6, with split source Table 7.4 recombined; saved AUX had numbered them 1--5. The two figures are 7.6--7.7. Correct counters only, leaving every row/caption unchanged.')
    elif key == EPILOGUE:
        replace(r'\begin{flushright}--- La Fontaine, \textup{Fables}, VIII\end{flushright}',
                r'\begin{flushright}--- La Fontaine, \textup{Fables}, VI\end{flushright}',
                'Restore VI from the supplied operator review finding; no new external-fact audit.')
        lines = document.splitlines()
        wrong = next(l for l in lines if l.startswith(r'\glmnote{2}{') and 'Barbaste' in l)
        replace(wrong, '', 'Withdraw the unsupported VIII/Le Juge de Barbaste explanation; original model response remains in the parent.')
        paragraphs = document.split('\n\n')
        for p in paragraphs:
            if p.lstrip().startswith(r'\par\smallskip\noindent\textbf{GLM') and 'Barbaste' in p:
                replace(p, '', 'Remove the stale duplicate of the withdrawn attribution claim.')
        document = append_note(document, 'operator-review-fables-20261101',
            'The supplied 1 November review restores La Fontaine, Fables, VI. The earlier model change to VIII '
            'and its Le Juge de Barbaste explanation are withdrawn. This is an operator-supplied correction, '
            'not a claim that the model or this offline edit browsed the cited edition.', attribution='Operator-supplied review')
    elif key == BIBLIOGRAPHY:
        entries = {
            '21': r'\noindent [21] Carmona, R., Nadtochiy, S.: Local volatility dynamic models, Finance and Stochastics, 13(1), pp. 1--48, 2009. DOI: \href{https://doi.org/10.1007/s00780-008-0078-4}{10.1007/s00780-008-0078-4}.\par',
            '43': r'\noindent [43] Durrleman, V.: From implied to spot volatilities, Finance and Stochastics, 14(2), pp. 157--177, 2010. DOI: \href{https://doi.org/10.1007/s00780-009-0112-1}{10.1007/s00780-009-0112-1}.\par',
        }
        for number, corrected in entries.items():
            old = next(l for l in document.splitlines() if l.startswith(r'\noindent ['+number+']'))
            replace(old, corrected, 'Apply the supplied review correction for bibliography ['+number+']; remove its stale contradictory inline note.')
        for p in document.split('\n\n'):
            if p.lstrip().startswith(r'\par\smallskip\noindent\textbf{GLM') and ('[43]' in p or '[21]' in p):
                replace(p, '', 'Remove a superseded duplicate bibliographic warning/incorrect correction; parent notes remain intact.')
            elif p.lstrip().startswith(r'\par\smallskip\noindent\textbf{GLM') and 'critic-call-035-1077f29e1f' in p:
                replace(p, '', 'Remove the mangled duplicate Nachman note; the readable inline correction and original summary remain.')
            elif p.lstrip().startswith(r'\par\smallskip\noindent\textbf{Contextual --- source-image inspection recommended.}'):
                replace(p, '', 'Withdraw the stale sign-off warning for the three supplied bibliographic corrections; no additional bibliography audit is requested.')
        line = next(l for l in document.splitlines() if l.startswith(r'\noindent [74]'))
        if '1(3), pp. 311--328, 1988' not in line:
            raise ValueError('Unexpected Nachman reading; do not replace without review')
        replace(line, line.replace(r'\glmcorr{', r'DOI: \href{https://doi.org/10.1093/rfs/1.3.311}{10.1093/rfs/1.3.311}.\glmcorr{',1),
                'Keep the existing correct Nachman volume/year/pages and add the supplied DOI.')
        document = append_note(document, 'operator-review-bibliography-20261101',
            'Operator-supplied review corrections: [43] Durrleman is 14(2), 157--177 (2010); '
            '[21] Carmona--Nadtochiy is 13(1), 1--48 (2009), so its pagination warning is withdrawn; '
            '[74] Nachman remains 1(3), 311--328 (1988). The supplied DOIs are retained. '
            'No systematic bibliography audit or new model review was performed.', attribution='Operator-supplied review')
    return document, changes
