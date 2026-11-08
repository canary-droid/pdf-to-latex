# Finite GLM source-image review — 6 November 2026

Current pointer: `results/glm-image-review-current.json`. Run preparation:
`runs/glm-image-review-20261106T121258Z`. Inspect actual progress; preparation is
not inference. The preceding follow-up and all its queue pointers remain unchanged.

The exact historical critic INPUT drafts are CF Cases13–18 (`call-010`) and
Information Geometry Section2 (`call-009`) from the completed extraction comparison.
Draft hashes, primary/secondary/context strings and131072 allowance were verified
against actual request JSON. The new image-reading/evidence instructions differ
from historical text-only review, so historical timing comparisons are observational.
Converter annotations inside the exact draft are deliberately retained in every arm.

Frozen work: four sequential A/B Max reviews (CF three original pages vs those
pages plus four crops; IG three original pages vs pages plus two crops), then two
identical B/Max requests simultaneously only if both sequential B reviews are usable,
image-verified and resource-qualified; finally two sequential B/High reviews. Eight
planned requests, one attempt each, within the authorised ten. Zero readiness
inference planned, at most three separately authorised if subsequently needed;
this plan does not dispatch any. No conversion, OCR or syntax-model calls.

C is deferred BEFORE dispatch: native-resolution crops cover the assigned dense
CF material and the relevant IG definitions, while full-page views provide context.
No limits or services change. Current2048/image,16384 shared,50 images are checked
against the running installed code. Max and High use installed template verification.
No inference retry, whole-paper retry or subsequent production queue follows.

Real PNG bytes are included in requests, with PDF hash, physical page, exact crop
coordinates, dimensions and image hash. Budgets count text and expanded image rows,
not base64 as text tokens. The local simple-chapter transport allows up to16MiB for
image payloads only; unchanged text-only limits remain. Missing/changed images or
stale drafts stop dispatch. No silent clarity reduction or text-only fallback.

CPU preprocessing uses the same installed frontend, tokenizer and in-memory vision
template patch as the running application, WITHOUT loading the vision tower. The
first dry run mistakenly used the checkpoint's raw text template and yielded zero
image rows; that diagnostic is preserved. The corrected check verifies positive
image rows, actual fitted shapes and pixel hashes. For EACH live request, returned
server prompt-token usage must equal the exact CPU-rendered, image-expanded count.
The installed engine enforces image-position/feature-row equality. This is observed
server usage plus verified execution-path evidence, not merely the presence of an
image field; GPU tensor contents are not directly instrumented. Failure stops further
inference. Responses, reasoning and failed allowances stay on disk.

A/B and parallel repetitions keep exact draft/image/input identities. A concurrency
trial requires both sequential B results to be usable; Max exhaustion remains a
consumed failure and does not prevent its authorised High comparison. All image
stages require >=4GiB observed host headroom on both nodes in addition to the
existing shared-pool admission. Samples bound observed headroom, not true millisecond
GPU peaks. The two-request ceiling is never raised. Pause drains active calls.

```bash
bash /home/mdi/projects/pdf-to-latex/scripts/run-glm-image-review.sh status
bash /home/mdi/projects/pdf-to-latex/scripts/run-glm-image-review.sh pause
bash /home/mdi/projects/pdf-to-latex/scripts/run-glm-image-review.sh resume
bash /home/mdi/projects/pdf-to-latex/scripts/run-glm-image-review.sh bundle
```

Normal launch/resume: `bash /home/mdi/projects/pdf-to-latex/scripts/run-glm-image-review.sh run`
Tmux: `pdf-glm-image-review`. Run-local `terminal.log`, `progress.json`, `results.json`,
`comparisons.json`, `reviews/`, `image-verification/` and `repairs/` hold outcomes.
Final inspection excludes repeated base64 requests and long reasoning, retaining
original requests in the run. Finished resume performs zero requests.

## Saved-file repairs, performed before inference

Spectral's actual theorem/lemma/assumption declarations are explicitly allowlisted,
hoisted consistently and preserved. No arbitrary preamble acceptance. Assumptions
2–4 and theorem/lemma numbering were checked in compiled text/auxiliary records.
Source inspection exposed a falsely numbered introductory display shifting source
Eqs1–22. The corrected working derivative unnumbers ONLY that original unnumbered
display; the actual compiled sequence1–22 now matches source and Section4 begins23.
Select `repairs/Spectral-numbering-qualified/` for the final editable master/PDF.
Earlier repair builds remain preserved and labelled superseded.

P-values Figure1 uses its verified six-panel composite once, at readable size within
the page. All original individual crops remain. The source-specific relationship is
manifest-backed and no generic overlap/duplicate inference is used. Real compilation,
image bounds, float warnings and rendered-page inspection passed. Select
`repairs/original-547334b059504dcb/`. CF has no demonstrated glyph or drawing clipping;
the widest rendered page was inspected and the existing edition was preserved.

Coverage uses explicit generated-note markers, with narrow legacy hashed-note
provenance; genuine Accuracy/Editorial/Notes source headings remain. Title and theorem
headings are recognised. Assembly-abort status is separate from proven missing
figures; unresolved references propagate. Automatic numbering is checked against
actual compiled numbering where recorded, otherwise remains unverified.

All eight Spectral unit4 replacements were directly compared with original pages
34,36,38,39,40 and independently checked from their stated SDEs/Liouville transform.
They are supported corrections to PRINTED mathematics, not OCR reading repairs.
Calculations and alternatives are retained in `evaluation/spectral-eight-edits.json`;
original converters and critic derivatives are preserved. Embedded historical notes
are explicitly labelled superseded, with current dispositions added. This is local
formula checking, not whole-paper verification. The two exhausted historical review
scopes remain unreviewed and are NOT retried here.
