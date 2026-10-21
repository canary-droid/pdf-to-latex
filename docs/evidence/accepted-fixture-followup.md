# Accepted native fixture derivative and focused follow-up

Recorded 20 October 2026, Europe/London (artifact names use 19 October UTC).
This document is independent operator evidence, never a GLM input.

## Observed high-effort review

`runs/review-pages-20261019T224212Z-e0f284` used
`runs/review-input-20261019T224021Z-4aea11` against the saved conversion
`runs/convert-basic-20261018T182257Z-c99779`. Both responses identify
`glm53-regular` and finish with `stop`. Parsed proposals agree with the raw HTTP
responses and the actual requests agree with the preview. The earlier low review
`runs/review-pages-20261019T223423Z-f95dcd` is unchanged.

| Native page | Request latency | Completion tokens | Reasoning tokens | Other completion tokens | Proposals |
|---|---:|---:|---:|---:|---:|
| 1 | 13.405 s | 543 | 441 | 102 | 0 |
| 2 | 33.448 s | 1,895 | 1,153 | 742 | 4 |

Summed request latency is 46.853 seconds. Coverage was complete, but page 1
missed the comma between −1 and 1/252 and bare ordinary words in the table's
math-mode headings. Completion and block coverage are separate from fidelity.

## Explicitly authorized application

The user's selection is saved in
[fixture-native-acceptance.json](fixture-native-acceptance.json). Stable proposal
IDs incorporate the page, proposal ordinal and content fingerprint; target
hashes bind the exact original blocks. Full source/review manifest digests and
the preview manifest bind the underlying evidence. This is an explicit local
operator record, not a digital signature or a confidence-based acceptance rule.

| Target | Operation | Applied result |
|---|---|---|
| `fixture-native-p0002:b0` | Replace | Saved rotated-aside transcription, including its subscript/superscript distinction |
| `fixture-native-p0002:b3` | Replace, grouped | Saved polynomial identity with F.3 |
| `fixture-native-p0002:b4` | Replace, grouped | Saved expectation equation with F.4 |
| `fixture-native-p0002:b5` | Delete, grouped | Detached duplicate F.4 explicitly accounted for as deleted |

b3/b4/b5 are one all-or-none group. Original review files retain their original
UNACCEPTED status. There is no authorization for other proposals.

New derivative: `runs/accepted-derivative-20261019T230916Z-969d30`.
Open `review.html` for source and before/after text, `acceptance.json` for the
separate acceptance record, `inventory.json` for all 17 blocks and
`provenance.json` for hashes. The actual TeX paths are:

- `pages/fixture-native-p0001/document.tex`
- `pages/fixture-native-p0002/document.tex`

Thirteen blocks are unchanged, three replaced and one explicitly deleted; none
is silently omitted. The entire page-1 TeX is byte-identical to the earlier
portable export. Both known page-1 issues are recorded as unresolved. The zero
renderer-unsupported-block count is not a fidelity score. Original OCR, source
windows/images and a byte-identical copy of the complete high review, including
the upright aside crop, remain available in the derivative ZIP.

Compilation is **not run**. No `pdflatex`, `xelatex`, `lualatex`, `tectonic` or
`latexmk` executable was found. The operator runbook gives compilation commands
for a separate laptop build copy; do not compile into the sealed Spark artifact.

## Prepared experiment — not executed

Preview: `runs/review-regions-input-20261019T230924Z-93edf1`.
Selection: [fixture-focused-blocks.json](../fixture-focused-blocks.json).
Each request includes one selected block/draft, its source-region image, the
whole page image and adjacent native OCR blocks for context. The three crops
were inspected locally and show the paragraph, table, and F.1 with its condition
and label. No result or accuracy claim follows from preparing these inputs.

| Request directory under `pages/` | Selected block | Role | Text characters | Serialized request bytes |
|---|---|---|---:|---:|
| `fixture-native-p0001-b1` | `fixture-native-p0001:b1` | Inline-math paragraph | 5,875 | 106,855 |
| `fixture-native-p0001-b4` | `fixture-native-p0001:b4` | Table | 5,472 | 116,764 |
| `fixture-native-p0001-b2` | `fixture-native-p0001:b2` | Unchanged F.1 control | 5,926 | 99,013 |

Every request has two images, high reasoning effort, a 16,384-token allowance
and a 600-second timeout. `request.json` stores the exact prepared body;
`page.json` records selected blocks and context. All three LaTeX drafts match the
original high whole-page preview exactly. Original full-page image bytes match;
the table and control crops also match the original detail images. No accepted
page-2 corrections, known answers, human issue notes, baseline or gold fixture
TeX appear in the request data. The general prompt checks punctuation, symbols,
conditions, units and rendered LaTeX meaning, including ordinary text in maths.

The new schema requires `scope: selected_blocks`. A complete result means only
the selected region was reviewed. It cannot claim neighboring blocks or full
page coverage. Whole-page review and legacy previews retain their existing
behavior. No automatic review/repair loop or focused-response acceptance is
implemented.

## Integrity and offline validation

| Artifact | SHA-256 |
|---|---|
| Original conversion file-manifest digest | `e7bf204fbf0fb2e39ea3eb37a95e70541821aa2ef0409bbb83c3095ca5a04cb6` |
| Original high review file-manifest digest | `b8e7e270d4bc629f83188d141a9ad9b16597eb0fcce673174cd26fc7b6e0e7ac` |
| Original high preview manifest file | `5c0ce0cd761f09449a321e4358f4241853aca811635adf90d3b01416983aa647` |
| New derivative manifest file | `a0bc5aaf4763be0fe71c623373b83f92f53e7a800026c143aee3c3bf9ab2a32d` |
| `results/accepted-derivative-20261019T230916Z-969d30-upload.zip` | `f8ded825e26f524fe3ad39141b2314a78b3f36fd75fee56ae5910bc7326378a1` |
| New focused preview manifest file | `5be9aedd62b28a5922bce7af5c173469a57772d8b86941b0b9016d1853324c05` |
| `results/review-regions-input-20261019T230924Z-93edf1-upload.zip` | `8b9defb098d04a097613c8eb3967f9257a994a43601864fbe20c518585989e05` |

Manifest *digests* above use the project's canonical JSON fingerprint of the
complete sorted file inventory. Manifest *file* hashes hash the saved JSON bytes.
All 771 pre-existing files across 19 evidence roots retained their byte hashes;
all prior run membership is unchanged. This includes every existing run/result,
fixtures and registered input files. New result ZIPs were added separately.
Both new ZIPs passed CRC/content comparison against their run trees, and all
local HTML links resolve. Source-block order, unchanged fragments, explicit
deletion and exact focused request/draft bindings were checked on the real data.

The full offline suite discovered 111 tests: 95 passed, 15 errored on denied
mock socket creation, and one existing assertion failed because the expanded CLI
diagnostic wording changed. The wording was corrected and all 17 saved-page
regression tests then passed. In total, 96 distinct tests passed, including all
16 new acceptance/focused tests; the 15 mock HTTP tests still require the normal
terminal. Their denied operation is `socket.socket()` for a loopback
`ThreadingHTTPServer` (`PermissionError`, errno 1), not a live-model call.
No permissions were changed. Python compilation and `git diff --check` passed.
The live command was parser-checked only, and saved preflight text/vision/model
identity were verified read-only. Offline tests establish implementation behavior,
not GLM accuracy or TeX compilation.
