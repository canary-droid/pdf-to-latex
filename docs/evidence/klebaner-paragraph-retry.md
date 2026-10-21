# Klebaner paragraph follow-up — 20 October 2026

Prepared offline; **not yet executed**. This assessment is separate from model
inputs. The selection contains only `klebaner-ch4-7-p0001:b4`, printed page 91,
original physical page 106, selected page 1.

## Observed failed trial

Inspected `runs/review-regions-20261020T185933Z-7075bd` and its original preview,
`runs/review-regions-input-20261020T185019Z-5a9907`. Source-state, preview-manifest
and preflight bindings passed verification. Every saved live request matches the
preview with only the unsupported `response_format` wrapper omitted. Images
and page data match the preview exactly.

The paragraph's retained response reports exact model `flash-next-tensorfold`,
`finish_reason: length`, `completion_tokens: 16384`,
`reasoning_tokens: 16384`, and `content: null`. The diagnostic repeatedly weighs
OCR-derived content against the image as competing authorities. It is not a
valid final response or a proposal. No diagnosis or specific expected correction
from that diagnostic is copied into the new request.

The original run has partial selected-region coverage: the nested display and
control requests completed, with one UNACCEPTED proposal for the former and
none for the latter. These outcomes were not re-reviewed for accuracy here.
All original responses, proposals, images and bundles remain unchanged.

## Controlled follow-up

New preview: `runs/review-regions-input-20261020T191957Z-311b42`.
Open `review.html` within it. Inspection ZIP:
`results/review-regions-input-20261020T191957Z-311b42-upload.zip`.
Selection: `docs/klebaner-paragraph-retry-blocks.json`.

The generic focused prompt now states that the original images are authoritative;
`native.content`, neighboring OCR and `draft_by_block` are potentially erroneous
OCR-derived comparison material. It asks for OCR corrections grounded in the
images, distinguishes errors printed in the book from OCR mistakes, and requires
uncertainty for unreadable details. It supplies no expected corrections.

The instruction prefix is recorded as focused prompt version 2. Unversioned
previews retain the exact version-1 wording. Unknown versions or inconsistent
saved prompt/data bindings fail before model discovery. Whole-page wording,
response validation, identity checks and acceptance rules are unchanged.

The only model-request changes relative to the old paragraph preview are that
generic instruction prefix and `reasoning_effort: high` → `medium`. The page
data gains an internal prompt-version field, which is not added to the model's
comparison data. Both source-image files, the draft, neighboring OCR, all schema
data and remaining request fields are identical. The retry selects just this
one paragraph; it does not repeat the other two requests or claim page coverage.

Settings: exact alias `flash-next-tensorfold`, endpoint
`http://127.0.0.1:8890/v1`, 16,384 generation tokens, 600-second timeout,
`stream: false`, medium effort. The read-only local deployment README explicitly
documents medium effort support; its live behavior is untested here. Sampling
continues to inherit server settings. Recorded budgets: 9,084 prompt characters,
381,269 prepared request bytes, two images. Omitting `response_format` at dispatch
reduces the body to 380,319 bytes. Existing image and 2 MiB request limits apply.

Use the existing preflight `runs/preflight-20261020T181856Z-070d9b`. Its passing
text/four simple vision controls and unsupported strict JSON remain unchanged.
Dispatch omits only the API wrapper; the schema remains in the prompt. Malformed
JSON, wrong identities/block references and truncated output remain failures.
No acceptance occurs automatically.

## Validation

- 42 relevant offline tests passed: 24 acceptance/focused tests, 17 saved-page
  tests and the client effort-validation test. Tests cover actual medium request
  serialization through an in-memory transport, source-authority instructions,
  unchanged input data, legacy prompt compatibility and version mismatch
  rejection. Existing malformed-response/identity/evidence checks still pass.
- Python compilation and `git diff --check` passed. Full-suite/socket tests were
  not rerun; the normal-terminal command is in the operator instructions.
- New preview verification passed; the original Klebaner preview and earlier
  accepted-fixture focused preview still validate without modification.
  New ZIP contents match the preview files exactly.
- All 2,703 snapshotted pre-existing input, fixture, run and result files retain
  their hashes and old run membership is unchanged. No inference, OCR, service,
  dependency, Git metadata or permission changes occurred. Everything is unstaged.

| Artifact | SHA-256 |
|---|---|
| Failed paragraph `response.raw` | `99bd1b709fe6ec2670b9680f1033c43a5c39af586e3073f85f9084e8ca5928bf` |
| Original review ZIP | `4abbedef2c17ced03a4ab969a85be0d1fac9df2d0eaf7e36356c98dca10803f5` |
| Retry `artifact-manifest.json` | `c7e75d6a33b821c672fb7892925c8921147fa07ecffb2ab11ca8ca2838748f67` |
| Retry inspection ZIP | `b39be5f44936f7dfa9814a7f28a693ad285c88d2a7b448d8dcd3505a7a841ead` |

Live completion and transcription fidelity remain untested. All future proposals
remain UNACCEPTED. The exact operator command is in `docs/SPARK-OPERATIONS.md`.
