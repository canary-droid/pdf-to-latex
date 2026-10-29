# Two-source meaning-focused chapters — 26 October 2026

Codex offline preparation and development checks. No inference, service change,
key access, package installation or new OCR. This is not an accuracy evaluation.

Final preparation: `runs/simple-chapter-glm-trial-20261026T210920Z-316b1a`.
Parent: `runs/simple-chapter-glm-trial-20261026T192951Z-3efb02`, unlaunched and
unchanged. All eleven consumed historical calls and the original first-dispatch
timestamp are preserved; zero new calls. No overall/generation deadline. The
ten-second connection timeout and 80-call cumulative ceiling remain unchanged.

## Input preparation and actual request inspection

Both original PDFs match their recorded identities:

- Gatheral: `inputs/gatheral/source.pdf`, 210 pages,
  `6010ddf7fe8456398d35dc7d94b16d1f8c853da5e1671d763c7f92083169a988`.
- Klebaner: `inputs/klebaner-original/source.pdf`, 431 pages,
  `4df3fd75e2c040875bb14d4540caaced3eefd5a836f0419837e619abd3c72934`.

The unchanged primary chapter text uses the existing native MinerU renderer and
verified owned-page selection. **669** existing source/native/provenance/asset
files match the parent. All three saved drafts and their conversion notes match
their original evidence. No portable-export formula filter was introduced.

Secondary native text uses installed **PyMuPDF 1.26.6**, `Page.get_text('text',
flags=TEXTFLAGS_TEXT, sort=False)`. No number/furniture filter. It caches exact
per-page text, SHA-256, original-PDF identity, physical/selected/printed mappings,
method and version. Printed mappings were already established: Gatheral physical
minus 31, Klebaner physical minus 15 in the selected chapter. Unknown mappings in
the reusable reader remain unknown. There are 161 distinct Gatheral main-chapter
pages (32–192) and 31 Klebaner pages (106–136), no duplicate/context-window pages.

Bounded inspection found no identifiable actual Open WebUI extraction or extractor
configuration in the supplied locations. Downloads contains generated `ch4.tex`
and PDFs, not a known raw Open WebUI extraction; those are not substituted. The
native-text result is not represented as an exact replay of Open WebUI.

Actual saved requests—not just cache files—were compared with the request builder.
All twelve conversion bodies contain their complete primary and secondary text.
The three scheduled saved-draft critic bodies contain both sources, the exact
initial TeX and only conversion-time baseline accuracy notes. Provenance/hashes
stay in sidecars. No later Chapter 2 audit diagnoses, expected answers, image
inspection results or known-correction list enters those requests. Source material
and historical model notes can naturally contain the topics under discussion.

| Chapter | Physical PDF pages | Conversion estimate including output | Saved-draft critic estimate including output |
| --- | --- | ---: | ---: |
| Klebaner 4 | 106–136 | 301,478 | Unavailable: conversion truncated |
| Gatheral 1 | 32–45 | 196,927 | 234,381 |
| Gatheral 2 | 46–55 | 179,297 | 204,604 |
| Gatheral 3 | 56–73 | 210,560 | Unavailable: conversion truncated |
| Gatheral 4 | 74–80 | 157,892 | 170,991 |
| Gatheral 5 | 81–104 | 225,016 | Unavailable: disconnected conversion |
| Gatheral 6 | 105–117 | 187,508 | Awaiting draft and notes |
| Gatheral 7 | 118–131 | 188,048 | Awaiting draft and notes |
| Gatheral 8 | 132–137 | 162,089 | Awaiting draft and notes |
| Gatheral 9 | 138–152 | 195,988 | Awaiting draft and notes |
| Gatheral 10 | 153–163 | 177,061 | Awaiting draft and notes |
| Gatheral 11 | 164–192 | 256,064 | Awaiting draft and notes |

These are conservative **UTF-8 request bytes + 4,096 template margin + 131,072
output**, not tokenizer counts. Controller `tokenizers`/`transformers` are absent;
no dependency was installed. All estimates fit the historically saved 1,048,576
window, but **current context fit is unverified**. Each complete request is checked
against current health before dispatch; a gap leaves sources unchanged and permits
independent eligible chapters to proceed. Future critic budgets include the actual
new draft and notes when they exist. No automatic splitting/retrieval subsystem.

## Known Chapter 2 development examples

These are known development cases, not an untouched test set. Codex inspected the
original images of PDF 47, 52, 53 and 54 and the corresponding native MinerU/draft
text. This is not a repeated ten-page fidelity audit or an inference accuracy score.

- T1: PDF 47 shows ordinary C in the derivative of (2.4). Native MinerU has
  calligraphic C there and the saved draft uses `\mathcal{C}` while the other C
  terms remain ordinary. The source discrepancy predates GLM's draft.
- T2: PDF 52 prints p(k) in the density display. Saved MinerU uses `\psi(k)` and
  the draft retains psi. The surrounding source text uses p(k).
- T3: PDF 53 visibly says “Chapter 5 of Kloeden and Platen (1992)”. Native PDF text
  retains that complete locator. MinerU's footnote has a detached locator and the
  conversion notes explicitly say the stray 5 was removed, leaving an ellipsis.
  Both new Chapter 2 request bodies contain the complete native locator. The small
  fixture `tests/fixtures/gatheral-ch2-locator.json` records exact excerpts and
  provenance, and is never loaded by request preparation.
- M1: PDF 52 itself prints du in the inner integral of (2.15); this is not solely
  an OCR error. It is a material integration-variable inconsistency to assess.
- M2: PDF 54 itself prints eta/2 in (2.19), despite the preceding substitution
  yielding an eta-squared term. This is a source mathematical question, not a
  transcription-failure count.
- M3: The printed radical is also visible on PDF 54. Rearranging the literal
  preceding equation gives `A*y^2 - eta*sqrt(h)*Z*y - B = 0`, with
  `A=1+lambda*h` and `B=nu_i+(lambda*nu_bar-eta/2)*h`. The quadratic formula gives
  `(eta*sqrt(h)*Z +/- sqrt(eta^2*h*Z^2+4*A*B))/(2*A)`; replacing eta/2 in B with
  eta-squared/2 does not make the printed radical agree either. This is an algebra
  check, not validation of the stochastic discretization or justification for
  replacing a realized Z-squared with its expectation.

The user reported no substantive paragraph or simulation-step omissions in the
ten-page audit. This bounded four-page development inspection does not independently
establish that whole-chapter finding. These diagnoses live only in this assessment;
the new critic must assess the actual sources/draft without an answer key.

## Accuracy continuity and limits

Initial notes for 1/2/4 are retrospective extractions of original conversion notes.
They yield five open groups: two in Chapter 1, two in Chapter 2 and one in Chapter 4.
These are prior model claims/uncertainties, not five verified errors. Presentation
and positive bookkeeping observations remain collapsed outside the actionable list.
No historical assessment was invented for an absent note file.

New Markdown is optional in layout: a single complete TeX document is preserved
even with oddly formatted notes. Missing/unparsed notes, a model's explicit empty
issue report and failed review are distinct. Ignored issues stay open. Only an
unambiguous associated transcription edit with an exact source quotation at the
changed context can close automatically; arbitrary “fixed” statements or mathematical
claims/derivations stay for assessment. Revised working TeX, initial TeX, both note
versions, full mechanical diff and model-reported material changes remain separate.
Compilation is independent; incomplete critic output cannot replace initial TeX.

Next: reviews of saved Gatheral **1, 2, 4**, then conversion/critic pairs for **6–11**.
Klebaner, Gatheral 3 and Gatheral 5 remain explicit gaps without automatic replay.
Streaming evidence, manual controls, isolated compiler/package recovery and model
identity checks are retained. No sampling/thinking override or service change.

Final focused checks: **19 passed**. Related checks: **106 tests, 105 passed, one
opt-in real-compiler skip**. Final full suite: **484 tests in 219.624s, 466 passed,
15 sandbox socket-permission errors, three opt-in real-compiler skips**. All errors
are mock HTTP server creation denied with `PermissionError`; no application assertion
failure. Exact prepared requests, page boundaries, locator retention, baseline
provenance, inherited calls/drafts, note continuity, context gaps and ZIP integrity
were checked offline. Live accuracy, current SSE behavior and expanded compiler
image execution remain untested here; normal-terminal launch performs readiness
and compiler qualification before model work.
