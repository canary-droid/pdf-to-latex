# Klebaner: three-region Flash Next experiment

Prepared offline on 20 October 2026. **No requests sent; no proposals accepted.**
This is an operator assessment, never a model input. No expected answers,
diagnoses from this document, fixture answer keys or source-provenance notes are
included in the requests.

## Bound evidence and source selection

Conversion: `runs/convert-basic-20261020T075104Z-48fd90`. The saved-page loader
validated all 120 owned pages and 15 completed windows, including source/output
hashes and original-page mappings. Its status is
`conversion_completed_unreviewed`; completion does not establish fidelity.
The registered selection is Klebaner chapters 4–7, original physical pages
106–225, using `ocr_mode: auto`. No conversion was rerun.

Preflight: `runs/preflight-20261020T181856Z-070d9b`, endpoint
`http://127.0.0.1:8890/v1`, exact model alias `flash-next-tensorfold`.
Text passed and all four simple vision controls passed with matching response
model identities. Vision is qualified only for those controls; mathematical
transcription remains unqualified. Strict JSON is **unsupported**: the preserved
HTTP 400 response says `structured output needs xgrammar on the server`.
Nothing was installed and this result was not changed.

The original page images were visually inspected, including their printed page
numbers. Block IDs use the selected PDF's page numbering, not printed numbering.
The following findings belong only to this assessment:

| Purpose | Printed / original / selected page | Actual selected block | Independent source comparison |
|---|---|---|---|
| Representative paragraph defect | 91 / 106 / 1 | `klebaner-ch4-7-p0001:b4` | The paragraph beginning “Our goal” contains inline mathematical distinctions. The source's plain `1` has become `\dot{1}`, and punctuation after constant `c` has become a gamma subscript. The source period after the dotted product is also absent from that position in the draft. These are visible transcription differences. |
| Damaged nested exponential/integral | 155 / 170 / 65 | `klebaner-ch4-7-p0065:b14` | The display following “we obtain” contains a nested exponential inside an integral. Saved OCR has broken structure and repeated `\negthinspace`/`\neg` fragments. The exporter rejects it. The request retains that raw OCR verbatim inside display delimiters as comparison data; it does not repair the expression or infer a mathematically preferable source. |
| Correct equation control | 91 / 106 / 1 | `klebaner-ch4-7-p0001:b7` | Independently compared the full saved draft with the source crop: `X(t)`, the initial term, summation bounds, coefficients, indicator interval endpoints, terminal period and tag (4.1) agree. Whitespace is immaterial here. This is a transcription control, not a proof of the author's mathematics. |

The paragraph and control come from owned local page index 0 of
`klebaner-ch4-7-0001-0008`; the nested display comes from owned local page index 1
of `klebaner-ch4-7-0065-0072`. The selection file
`docs/klebaner-flash-next-blocks.json` contains **only** these three block IDs.
The model is not told which request is a control or what errors to find.

Normalized source boxes, in request order:

- Paragraph: `[0.068, 0.499, 0.932, 0.706]`; context blocks b3 and b5.
- Nested display: `[0.069, 0.606, 0.928, 0.651]`; context blocks b13 and b15.
- Control: `[0.31, 0.853, 0.927, 0.907]`; context blocks b6 and b8.

Each request includes the selected block, its saved OCR/LaTeX draft, neighboring
OCR blocks, one complete source-page image for context and one enlarged source
crop. Only the selected block is reviewed. The generic prompt asks for complete,
source-faithful replacement LaTeX when evidence supports a change, checks
punctuation/symbols/conditions/units/rendered meaning, and forbids repairing
apparent source errors. Empty proposals are allowed.

## Prepared artifact and settings

Preview: `runs/review-regions-input-20261020T185019Z-5a9907`.
Open its `review.html`. Each `pages/REQUEST_ID/` contains `page.json`,
`request.json`, `source.png` and `region.png`; copied evidence contains only the
two relevant conversion windows. Inspection bundle:
`results/review-regions-input-20261020T185019Z-5a9907-upload.zip`.

Explicit request settings: exact alias `flash-next-tensorfold`,
`reasoning_effort: high`, `max_tokens: 16384`, `stream: false`. Request timeout:
600 seconds. Three requests run serially across two distinct pages; there is
no automatic repair/review loop.

Read-only inspection of `/home/mdi/local-llm/flash-next-tensorfold/README.md`
and `recipe/README.md` documents top-level reasoning effort support; the former
describes `high` mapping to Qwen3.8's `xhigh` template level. The local recipe
identifies `TensorFold/Qwen3.8-Flash-Next-MLX-4bit-MTP`. This is the user's
explicit alternate local model experiment, not a substituted GLM alias.
The recipe's `.env` records `THINKING=1`, `CONTEXT=262144`, `MAX_TOKENS=65536`,
`TEMPERATURE=1.0`, `TOP_P=0.95`, `TOP_K=20`, port 8890 and parallelism 2.
These are launcher-file observations, not a live server-configuration audit.
The project client does not override temperature/top-p/top-k, template thinking
or seed. Sampling therefore inherits the running server configuration; no
determinism or live effort interpretation has been established.

Limits remain 48,000 prompt characters, 2 MiB serialized request size, 1 MiB
and 2,000,000 pixels per image, and at most 100 returned proposals per request.
Full-page render target is 1,400 pixels on the long edge; crop target is 1,200
(the raster bounding-box rounding produces 1,201-pixel-wide crops).

| Request suffix | Prompt characters | Prepared body bytes | Body bytes after omitting unsupported wrapper | Images |
|---|---:|---:|---:|---:|
| `p0001-b4` | 8,398 | 380,580 | 379,630 | 2 |
| `p0065-b14` | 7,342 | 305,172 | 304,222 | 2 |
| `p0001-b7` | 6,084 | 241,223 | 240,273 | 2 |

The existing preview serializer saves its canonical `response_format` wrapper.
At live dispatch, the bound preflight's unsupported strict-JSON result causes
**only that top-level field** to be omitted. The full response schema remains
in the prompt. The live run saves its actual request separately from the sealed
preview. Local JSON parsing and schema, scope, block-ID, completion and exact
response-model checks still apply. Malformed or truncated responses fail and
retain raw evidence; they never become proposals or acceptance.

## Offline validation and limits

- All 21 acceptance/focused tests and 17 saved-page tests passed (38 total).
  Five new tests exercise saved OCR selection, actual `LocalClient` serialization
  through an in-memory transport, unsupported strict-JSON dispatch, malformed
  responses/wrong scope/wrong block/wrong model/truncation, changed drafts and
  offline CLI use. No network socket or live endpoint was used.
- Python compilation and `git diff --check` passed. The full suite was not rerun;
  its previously recorded sandbox-denied mock socket tests still need the
  operator's normal terminal. No sandbox permissions were changed.
- All three prepared requests passed manifest and source-binding verification.
  Independent renders from the completed conversion reproduce all six image
  hashes exactly. Generated crops were visually inspected. The old accepted-
  derivative preview `runs/review-regions-input-20261019T230924Z-93edf1` still
  passes its original manifest and focused-input verification.
- All 2,452 snapshotted pre-existing input, fixture, run and result files remain
  byte-for-byte unchanged. Original run membership is unchanged. `sources.json`,
  AGENTS.md, preflight code, exporter validation and acceptance code are unchanged.
- No live behavior, review accuracy or TeX compilation was tested. There are no
  new model proposals yet. Future proposals remain UNACCEPTED; selected-region
  completion must never be described as full-page coverage or verified fidelity.

Bindings (SHA-256):

| Artifact | SHA-256 |
|---|---|
| Conversion `state.json` | `76c8c74eeee30d05cef816e1564f25c60c5dad0e0a1d978d0d5c7de7beca5543` |
| Preflight `model/capabilities.json` | `12f7c5d8e1bc20bde7b78f93d4c5abd4c215da1d76f47ebed3ad34231681fc96` |
| Preview `artifact-manifest.json` | `1a813e72000914f49b6480778b6130ec96d0491cd5ff834c29bf43eb9f93429a` |
| Inspection ZIP | `c2f3ce4272844d0e0da6ee15e404b66b6e8d1dba9a289fdd6d7af86afa950ed8` |
