# Klebaner 100-page batch preparation — 20 October 2026

**Prepared offline; no batch inference performed. All future proposals remain
UNACCEPTED.** This document is independent operator evidence, not model input.

## Observed prerequisites

Conversion: `runs/convert-basic-20261020T075104Z-48fd90`. Its saved source and
output hashes, page maps and owned-page inventory pass the existing loader.
Selected exactly the first 100 distinct owned pages of `klebaner-ch4-7`: selected
1–100, original physical PDF 106–205, in that order. There are 1,623 recognized
blocks. All IDs and native reading order are preserved, including headers and
page numbers. Overlapping window context never adds review pages. The intentional
separator pages at original 137 and 197 remain selected. The last source image
visibly shows printed page 190; the requested selection starts at printed 91.

The earlier three-region run `runs/review-regions-20261020T185933Z-7075bd`
remains partially completed with one unaccepted proposal. The paragraph retry
`runs/review-regions-20261020T192708Z-997831` completed with exact response model
`flash-next-tensorfold`, `finish_reason: stop`, 3,011 completion tokens (2,353
reasoning, 658 other completion), 46.02 seconds and one UNACCEPTED proposal.
Its source/preview/preflight provenance bindings were verified. Completion is
not an independent assessment of the correction's fidelity. No prior proposal
or diagnosis is included in the batch requests.

Existing preflight `runs/preflight-20261020T181856Z-070d9b` remains unchanged:
text passed, four simple vision controls passed, vision qualified, strict JSON
unsupported. The operator should generate a fresh preflight before launching;
the actual directory will be bound to the new live job. No future preflight or
live-result directory is invented in this preparation.

## Prepared inputs and accounting

- Preview: `runs/review-batch-input-20261020T195337Z-32f118`.
- Report: that directory's `review.html`, grouped by page.
- Inspection ZIP: `results/review-batch-input-20261020T195337Z-32f118-upload.zip`.
- Exact request/data/crop files: `units/UNIT_ID/` within the preview.
- Page inventory and original image: `pages/PAGE_ID/page.json` and `source.png`.
- The sealed `batch.json` records selection, mappings, units, policy and budgets.

| Request scope | Count | Coverage responsibility |
|---|---:|---|
| Whole page | 9 | All recognized blocks plus a visual search for missing source content |
| Block group | 296 | Every block in its explicit group; page/neighbors provide context |
| Page omissions | 91 | Entire source page against complete OCR context, including margins and regions without OCR boxes |
| Total | 396 | Each of 1,623 blocks exactly once, plus one visual omission check per page |

Whole-page mode is attempted for at most 12 recognized blocks. Denser pages
split in native block order into groups of at most six with a bounded vertical
span (0.48 normalized page height, unless a single block itself is taller).
Character/image/request overflow splits groups further; an unsplittable unit
blocks preparation rather than being truncated or silently omitted. Each group
has a complete page image and its source-box union crop. Whole-page and omission
requests include the complete image and overlapping top/bottom source tiles
covering the entire page. Blank recognition would still require a visual check.

Source images/crops are rendered into the new preview from validated saved PDF
windows; no MinerU or OCR rerun occurred. The 13 copied evidence windows include
original overlap and context beyond selected page 100, explicitly outside review
coverage. Source images for previously reviewed pages 1 and 65 match their old
preview hashes. Representative dense equation crops and the final source page
were visually inspected; this is not a manual fidelity review of all 100 pages.

The generic instructions make original images authoritative, identify OCR/drafts
as potentially wrong, require correction of transcription errors, preserve
errors actually printed in the book, and flag unreadable details. No answer key,
expected correction, prior proposal, baseline or diagnostic is loaded into model
inputs. Broken mathematics stays comparison data; no export repair occurs.

Settings: `http://127.0.0.1:8890/v1`, exact alias `flash-next-tensorfold`, medium
effort, 16,384 generation tokens per request, 600-second timeout, `stream:false`,
one request at a time. Sampling inherits current server defaults without client
overrides. Maximum observed prepared body: 857,621 bytes; maximum text: 17,880
characters; maximum images: three. These fit the existing 2 MiB request, 48,000
character, 1 MiB/image and 2,000,000 pixel/image limits. The canonical schema
wrapper is removed at dispatch only when the bound preflight reports unsupported
strict JSON; the prompt schema and strict local response validation remain.

Preview size: 373,446,958 bytes; ZIP: 300,341,555 bytes. A live run copies its
immutable inputs and adds raw attempt records; partial bundles also include those
inputs. These large book artifacts remain under ignored `runs/` and `results/`.

## Persistence and failure policy

A new live job seals its source, preview manifest, actual preflight capabilities,
model, endpoint, request limits, effort and policy in `binding.json`. Resuming
revalidates source and prepared data, exact requests, copied input manifests and
completed attempt seals before discovery. Bound files/membership are checked
before each dispatch; any detected integrity failure stops the job.

Every unit gets an exclusive numbered attempt directory, with its reservation
and exact outgoing request persisted before dispatch. Outcomes and raw transport
evidence are retained and sealed; a checkpoint and report follow each request.
Unattempted units run first, then at most one retry of failed units. There is no
automatic prompt rewrite or repair loop. Retry counts come from both durable
state and attempt directories, so interruptions/resumes cannot reset the limit.
Already validated saved answers can be recovered after interruption without
repeating the request. An interrupted request without a committed validated
answer consumes an attempt; the remaining retry, if any, is conservative.

Isolated response failures are recorded and other units continue. Two consecutive
connection failures (including timeouts and HTTP 502/503/504) pause the job;
the streak persists until a response succeeds or a non-connection failure is
observed. Discovery unavailability pauses before chat. Changed model identity,
including a mismatched model on a truncated response, stops the job. A stopped
identity/integrity run is not automatically resumed. Maximum chat dispatches for
this preparation: 792; the limit does not predict runtime or accuracy.

`state.json`, `coverage.json` and the report distinguish completed, failed,
pending/in-flight units, retry eligibility, unreviewed blocks and missing visual
checks. Complete pages require both block and omission checks. All proposals are
UNACCEPTED and fidelity remains unreviewed. `batch-status` reads atomic checkpoints
while the job holds its writer lock. Bundling after pause/completion preserves
prior ZIPs, using a fresh filename when one already exists.

## Offline validation and limitations

All 14 batch regressions passed: owned-page selection, gap/duplicate rejection,
dense splitting, all-block/visual coverage, overflow rejection, actual request
serialization, no answer leakage, completed-work skipping, retry persistence,
connection pauses (including timeouts after HTTP 200 headers), interruptions/recovery, model mismatch, stale evidence,
concurrent status and append-only partial bundles.

Final full suite: **133 tests run; 118 passed, 15 errors**. Every error was a sandbox
`PermissionError: [Errno 1] Operation not permitted` while creating a mock HTTP
server socket. There were no application assertion failures. No permissions were
changed. Run the full suite in the normal terminal as documented. Python
compilation and `git diff --check` passed.

The complete preview passed independent source/request/coverage verification;
ZIP entries match the preview bytes. Earlier Klebaner focused previews still
validate. All 2,809 snapshotted pre-existing input, fixture, run and result files
remain byte-for-byte unchanged, with original run membership unchanged.

No batch requests, services, installations, model settings or Git metadata were
changed/run. Long-running live behavior, server availability, mathematical
accuracy and TeX compilation remain untested. `tmux` protects against desktop
disconnect, not host reboot/power loss. Hard interruption may leave a server-side
request processing; inspect activity before resuming. Exact reported aliases do
not establish unchanged model weights or inherited sampling settings if an
operator changes a server behind the same alias; this workflow cannot certify
those hidden server properties.

| Artifact | SHA-256 |
|---|---|
| Conversion `state.json` | `76c8c74eeee30d05cef816e1564f25c60c5dad0e0a1d978d0d5c7de7beca5543` |
| Batch `artifact-manifest.json` | `dcaa2e7b2cafe916d0f8a9e3bcc0121547624d5d1609586fbbb4520ffe3fe5fa` |
| Batch preview ZIP | `f74be1e064f9890330b1c9f7efceba22cb476d5dfc29a2ece58ae15bf46cb988` |
