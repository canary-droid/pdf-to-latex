# Reviewing this probe's transcription

This package is a compatibility and fidelity **probe**, not a completed PDF-to-LaTeX application. MinerU output and GLM proposals remain unreviewed until checked against the source. A successful process, complete page-index list or valid LaTeX syntax does not establish mathematical fidelity.

The checklist below was prepared by visually inspecting the supplied page previews. It identifies concrete content to check; it is **not a complete gold transcription**, an OCR benchmark result or a claim that the converter/GLM has passed these checks. No live Spark inference was used to prepare it.

## Open the right evidence

- The paper is complete: `inputs/paper/source.pdf`, 17 physical pages. Its packaged page number equals its original physical page number.
- The book input is **Chapter 3 only**, not the full book: `inputs/book/source.pdf`, 30 pages, corresponding to original physical pages 89–118. Original physical page = packaged chapter page + 88. The original whole-book hash and all-page scope ledger remain in `inputs/book/manifest.json`.
- The book's hidden selectable text can be corrupt even when the page image is legible. Its full-page imagery and native text are separate evidence. Check the visible page, not copied native text, when deciding a symbol.
- Each completed conversion window has an `input.pdf`, `page-map.json` and `output/`. Use `page-map.json`: converter `page_idx` is zero-based within that window, not within the whole book. `owner: true` identifies the window responsible for that page.
- Adjacent-page context intentionally repeats between windows. This probe exports separate window documents; it does not yet reconcile them into a duplicate-free article or book. Do not concatenate all window Markdown or TeX files and call the result complete.
- The materialised `middle_json.json` plus image assets is the structured output package. Keep assets alongside `document.tex`; the raw JSON alone is not a substitute. Compilation status remains `not_run` unless a separate controlled compilation was actually performed.

Open the original window PDF beside `output/document.md` or `output/document.tex`. The generated `review.html` links the outputs; its text display is a convenience view. For long output, open the full linked file. Use original-page previews to locate content, then enlarge the source PDF for small indices, accents and punctuation.

## Ten targeted source checks

Use the paper's original physical page numbers below. For the book, both original and packaged chapter page numbers are listed. The printed page numbers given for the sampled book pages were visually inspected; they are not inferred from PDF catalogue labels.

| ID | Source location | Concrete pass criteria |
|---|---|---|
| P01 | Paper physical 2 | Preserve the effective-local-volatility conditional expectation and equation (3)'s square root of a ratio: the numerator integrates the density, while the denominator contains the squared integration variable. Check all conditioning bars and measure superscripts. In equation (5), retain the minus signs, the factor one half, all sum indices and the separate Dirac initial condition. Keep the following existence paragraph's conditions; do not replace it with a general claim of existence. |
| P02 | Paper physical 4 | Check equations (9)–(15) against the image, including the initial values for the auxiliary processes and the nested conditional expectations in (15). Preserve subscripts, superscripts, denominator scope and the minus signs in the conditional terms. Footnote 2 must remain attached to its marker and retain the measure-change statement; it is not a running footer. |
| P03 | Paper physical 5 | In equation (16), retain the leading minus sign, summation limits and each denominator `1 + tau_i L_i(t)`. In (17), retain the full time-index expressions in numerator and denominator. Preserve the distinction between the short-rate discussion, forward/bond measures and the labelled equation (18). Do not silently simplify source indices or supply missing model assumptions. |
| P04 | Paper physical 6 | The page begins with dynamics continuing the previous page's discussion, then starts “Local correlation model”. Preserve that order. Check equation (19)'s double sum and conditioning. Retain both the stated interpolation restriction on lambda and the later warning that calibrated lambda may not lie in `[0,1]`; do not “fix” this by clipping it. Footnote 4 contains an authorial criticism and must remain source text, not become a new model-generated audit. |
| P05 | Paper physical 17 | This sparse final page is not blank: retain bibliography entries [11]–[14], their numbering, titles, authors and available publication details. It must appear in the coverage report. Removing the repeated electronic-copy footer is acceptable only as an explicit layout-artefact decision, not by deleting the remaining page content. |
| B01 | Book original 91 = chapter 3, printed 69 | Preserve the finite-variation “if and only if” condition `nu < 1`. In Lemma 3.1, retain its stated domains and all three separate cases: the general case excluding zero and one, the zero case and the one case, with equations (3.2)–(3.5). Do not replace them with one generic formula. The start of Lemma 3.2 at the bottom continues onto the next page. |
| B02 | Book original 92 = chapter 4, printed 70 | Continue Lemma 3.2 from original page 91. Check all three characteristic-exponent cases (3.6)–(3.8), especially the leading drift term, the signs on lambda-plus/lambda-minus and the different coefficients. Retain the conditions on mu, the positive coefficients, and `lambda_minus < 0 < lambda_plus`. Preserve the later distinction between asymmetric coefficients and the simplifying equal-coefficient case. |
| B03 | Book original 95 = chapter 7, printed 73 | Figure 3.2 may stay an image, but both panels, axes and the legend must remain visible. Its caption must be editable and retain the parameters: mu zero, lambda-plus equal to minus lambda-minus equal to 24, second moment 0.3, the four displayed orders, and left/right times one day/five days. Preserve the following proof heading and the explicit sign-changing substitution; do not crop away the proof because the page also contains a figure. |
| B04 | Book original 97 = chapter 9, printed 75 | Check the multiline integration-by-parts calculation term by term: leading negative factors, integral limits, boundary-evaluation bars, powers and the Gamma factor. Keep each case's stated interval for nu. Preserve the definition of `C(nu, lambda)` and the later recurrence separately. The final zero-case calculation continues beyond this page; do not label a partial expression as complete. This is transcription checking, not an invitation to shorten or repair the proof. |
| B05 | Book original 114 = chapter 26, printed 92; original 117–118 = chapter 29–30, printed 95–96 | In (3.66) and (3.67), retain the opposite signs before the contour integrals, their shifted limits, denominator and separate restrictions on tau. Preserve the negative decay exponent in (3.68). Separately confirm that the final sentence beginning on original 117 continues into sparse page 118. Chapter page 30 must be exported even though it contains only a short continuation. Record these two subchecks separately if one passes and the other fails. |

These checks deliberately include inline mathematics, proof structure, an image figure with numerical caption, footnotes and sparse last pages. They do not cover every equation or every page. An empty/image-only equation is unresolved transcription, not a passing editable formula.

## Record decisions without changing the source silently

For each check, record:

1. Source ID and original hash; original physical page; window attempt and local `page_idx`; exact blocks/equations inspected.
2. Outcome: `correct`, `incorrect`, `unresolved`, or `not_converted`. Use `partly_checked` when only part of a listed case was examined.
3. Error type and consequence: omitted material, wrong sign/index, broken grouping, reading order, caption/footnote detachment, image fallback, or reference/numbering error.
4. The observed source reading and the converter reading. Keep any suspected source error as an annotation; preserve the printed expression in the faithful transcription.
5. Whether the system flagged the problem, who checked it, and the time spent reviewing/correcting it.

The probe's `review` command produces **unaccepted proposals**. It does not implement the later persistent accept/edit/defer workflow or apply corrections to MinerU output. Keep manual review notes beside the run. An edited exported TeX file is a separate manual derivative; retain its original alongside it and record the change.

When inspecting a GLM proposal, confirm that its page map and candidate ID identify the intended source object. A passing digits-and-blank vision probe establishes only basic image transport/reading. It does not qualify mathematical OCR. If vision did not qualify, GLM has no visual evidence and can inspect syntax/structure only.

Report the ten-check results with their actual checked scope, plus missing/duplicate pages and unresolved objects. Do not convert “10 checks passed” into a percentage accuracy for the whole paper, chapter or book. Synthetic known-TeX fixtures test controlled mechanisms; real scans and damaged hidden OCR require their own source checks.
