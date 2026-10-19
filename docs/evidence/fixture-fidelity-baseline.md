# Fixture fidelity baseline — 18 October 2026

Independent source comparison of the saved Basic conversion
`runs/convert-basic-20261018T182257Z-c99779`. This is an assessment, not an
accepted transcription or a correction proposal. No accuracy percentage is
claimed. Keep this document, the known-source TeX and expected corrections out
of GLM requests. Compare future UNACCEPTED proposals against this baseline only
after they have been produced.

## Evidence and method

The reference is [known-math.tex](../../fixtures/known-math.tex), checked against
both original PDFs: [native](../../fixtures/known-math.pdf) and
[scanned](../../fixtures/known-math-scan.pdf). Both pages of each PDF were rendered
locally and visually inspected. The existing upright aside crops were inspected
for both sources; the native OCR crop `images/page_1_equation_4.jpg` was also
inspected to check the detached equation labels. These were read-only operations;
temporary source-page renders were written outside the evidence directories.

Within the conversion run, the two attempt directories are:

- `attempts/fixture-native-0001-0002-f69a5acf/`
- `attempts/fixture-scan-0001-0002-fc8a15dd/`

Each comparison uses `output/middle_json.json`, `output/document.tex` and
`output/document.md`, plus the attempt's `input.pdf` and `page-map.json`.
Saved-source, completed-output and page-map integrity checks passed for all four
owned pages. The physical source pages are 1 and 2 for each fixture; the local
JSON `page_idx` values are 0 and 1. In the table, `p1 b2` means source page 1,
zero-based position 2 in that page's `blocks` array. Here the saved block `index`
also equals that position. The preview/export identifier is, for example,
`fixture-native-p0001:b2` or `fixture-scan-p0001:b2`.

Reference SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `fixtures/known-math.tex` | `9dbf5b8530e5c2f9705c1ad07f59fe17fc0f01726475027832850c8c8f50aad2` |
| `fixtures/known-math.pdf` | `14db4cf3bb895aa0a135086d0cea4e79b709a88a4f9d897ff010b03f0a140d08` |
| `fixtures/known-math-scan.pdf` | `4eeb95fd6e7d625f046fdc01ca7aaad9ae193ae85d342d45271a242ded393b22` |

## Comparison

**Confirmed error** means a specific discrepancy is supported by the source
TeX/page and saved output. **Apparently correct** means the inspected content
agrees; it is not a blanket fidelity certification. **Verification pending**
identifies rendering or manual acceptance work still outstanding. Whitespace
inside math source and equivalent TeX spellings are not by themselves errors.

| Content and location | Source requirement | Native output | Scanned output |
| --- | --- | --- | --- |
| Main source prose: p1 b0–b1, b5; p2 b1–b2 | Both headings; artificial-fixture disclaimer; instruction to keep the condition; table note distinguishing basis points from a decimal interest rate; continuation states no new assumption. | **Apparently correct:** all those words and sentences are present. Inline punctuation exception below. | **Apparently correct:** same prose present, with the same punctuation exception. |
| Inline distinctions: p1 b1 | `x_i`, `x^i`, `x_i^2`, bold x, prime, bar, `-1`, `1/252`, and `\nu\ne v`. | **Apparently correct symbols:** subscripts, superscripts, bold, prime, bar, minus and Greek nu versus Latin v are represented. `\neq` is equivalent to `\ne`. | **Apparently correct symbols:** same recognition. |
| Numerical punctuation: p1 b1 | Source has a comma immediately after `-1`, before `1/252`; it is visible at the source line ending. | **Confirmed error:** the first math span ends in `- 1`, followed by a space and a separate `1 / 2 5 2` span. The comma is absent in structured OCR, TeX and Markdown. The value itself remains 1/252. | **Confirmed error:** identical omission. Added spaces before other commas/full stops are also present, but do not establish changed values. |
| Integral and condition: p1 b2, with p1 b1 and p2 b2 controls | F.1: `I(a)=\int_0^\infty e^{-ax}\,dx=1/a`, with `a>0.` Condition also appears in prose and the later F.1 reference. | **Apparently correct:** bounds, exponent sign, differential, fraction, condition and F.1 tag retained. | **Apparently correct:** same content. Extra empty `\mathop{}` / `\mathopen{}` before `dx` are spacing/representation changes; rendered result remains to be checked. |
| Matrix and cases: p1 b3 | F.2: matrix rows `(1,-2)` and `(3,4)`; branches `x^2` for `x\ge0`, `-x` for `x<0`, including branch punctuation. | **Apparently correct content:** entries, signs, powers and both inequalities retained with F.2. Uses `matrix` and a braced `aligned` construction instead of `pmatrix`/`cases`; includes empty cells/trailing row syntax. **Verification pending:** inspect compiled branch association. | Same content and construction; **apparently correct**, with the same rendering check pending. |
| Algorithm: p1 b6 | Initialise `n=0`, `u_0=1`; stop on absolute difference of successive u values `<10^{-8}` **or** `n=100`; report which condition ended the loop. | **Apparently correct:** all initial values, indices, subtraction, strict threshold, negative exponent, logical alternative, limit and reporting clause retained. Bold paragraph label retained. | **Apparently correct content:** same conditions and prose; bold styling of “Algorithm.” is lost. This is a style difference, not a missing condition. |
| Table cells and units: p1 b4–b5 | Three columns: Case / Time (years) / Rate (basis points); A: `1/252`, `-12.5`; B: `2/252`, `10.0`; horizontal rule and explanatory note. | **Apparently correct values/association:** all headers and both rows present, including negative sign and trailing decimal zero. **Confirmed representation issue:** classified as `equation`, exported as `array{ccc}` rather than a text table; header words are bare math-mode letters, without text wrappers. | Same values, row/column order and representation issue. No numerical discrepancy observed. |
| Table rendering: p1 b4 | Headers are ordinary words with spaces, and rates retain their units and row association. | **Verification pending:** compile/view the array and confirm header readability, row separation and rule. Bare math-mode header spaces are ignored by TeX; raw presence of the words does not demonstrate a faithful rendered header. | Same pending rendering check. This is not a claim that the table failed to compile. |
| Expansion body: p2 b3 | `(x+y)^2=x^2+2xy+y^2,` | **Apparently correct body:** terms, powers, coefficient and terminal comma preserved. Label error below. | **Apparently correct body:** equivalent token-spaced expression, including comma. Label error below. |
| Expectation body: p2 b4 | `\mathbb{E}[X\mid\mathcal F_t]=\int_{\mathbb R}x\,p_t(x)\,dx.` | **Apparently correct body:** conditioning bar, script F and subscript t, real-line domain, density subscript, differential and terminal full stop preserved. | Same recognition; **apparently correct body**. |
| Equation label associations: p2 b3–b5 | F.3 belongs to the expansion; F.4 belongs to the expectation. Both are visually unambiguous on source page 2. | **Confirmed errors:** b3 has no tag; b4 (expectation) carries `\tag{F.3}`; b5 is detached prose `(F.4)`. Both native exports reproduce this. The b4 source crop spans both equation rows/labels, establishing overlapping evidence, not the cause of the OCR error. | **Confirmed errors:** same misassociation and detached label. |
| Rotated aside: p2 b0 | `Rotated label: \alpha_1\ne\alpha^1`, with distinct subscript and superscript. Upright crops confirm the complete text for both sources. | **Confirmed errors:** structured text is `Rotatedlabel:α1̸=α1` (spaces and script positions lost; no editable math structure). The combining slash is U+0338. Entire aside is absent from native `document.tex` and `document.md`. | **Confirmed errors:** structured text is `Rt ≠  : a1`, a severely incomplete/incorrect transcription. Entire aside is absent from native TeX/Markdown. |
| Aside attachment: p2 b0, b6 | Rotated label sits beside “A rotated label must remain attached to its evidence region.” | **Apparently correct sentence**, but the absent aside makes the native export incomplete. The block bbox still locates the source aside near normalized `[0.112,0.208,0.135,0.338]`. **Verification pending:** any future proposal must preserve the region association. | Same sentence survives; aside bbox is approximately `[0.112,0.208,0.134,0.338]`. Same pending association check. |
| Proof prose: p2 b7 | Preserve the full paragraph, including “Do not replace it with a summary” and the instruction to report a suspected source error separately. | **Apparently correct:** full paragraph retained, including bold “Proof text.” | **Apparently correct words/punctuation:** full paragraph retained; bold paragraph label lost. No summarisation observed. |
| Page markers: p1 b7, p2 b8 | Printed source page numbers 1 and 2. | **Apparently correct in structured OCR:** both present. Native exports omit page-number blocks; original maps remain correct. This is documented separately from missing substantive content because layout matching is not the goal. | Same. |

## Portable derivative and prepared preview

The existing [portable export report](../../runs/export-english-math-20261018T204408Z-59d26b/review.html)
accounts for all 34 blocks: 32 represented, two unresolved asides. Its page-2 TeX
retains each aside's raw recognition and region image in an unresolved appendix.
That preserves evidence but does not provide editable transcription of the
aside. The label errors remain visible in its TeX, and the derivative does not
repair the OCR mathematics or missing punctuation. Block accounting is not an
accuracy measure.

The existing [four-page input preview](../../runs/review-input-20261018T204409Z-301420/review.html)
contains source images and OCR drafts, including the upright
[native aside](../../runs/review-input-20261018T204409Z-301420/pages/fixture-native-p0002/manual-0.png)
and [scanned aside](../../runs/review-input-20261018T204409Z-301420/pages/fixture-scan-p0002/manual-0.png).
Those images support the confirmed aside findings above. This baseline has not
been inserted into that preview or any request. Existing OCR, export, preview
and result-bundle bytes remain unchanged.

## Remaining verification and interpretation

No TeX compilation or rendered derivative comparison was performed. Check the
table headers and matrix/cases rendering in a suitable existing TeX environment;
do not interpret equivalent-looking raw formulas as a compiled-output test.
Human acceptance of the full transcription, including apparently correct control
regions, remains outstanding. No live GLM review, proposal acceptance or corrected
export was performed in this preparation task.

For the next four-page review, assess whether the UNACCEPTED proposals recover
the missing punctuation, correct the label associations and transcribe/attach
the rotated aside without damaging the currently preserved prose, conditions,
values and equation bodies. A qualified simple-image preflight is only an
endpoint prerequisite; it does not establish mathematical vision accuracy.
