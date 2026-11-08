# Finite extraction comparison — 5 November 2026

This separately authorised experiment does not resume either corpus queue.
The 350-document source audit is deferred and preserved. Cooking with Collateral
is excluded. Read `results/extraction-comparison-current.json` for the selected
run and its progress file for observed execution; preparation is not inference.

The selected linked preparation is
`runs/extraction-comparison-20261105T094814Z-scope`. Its parent,
`runs/extraction-comparison-20261104T233805Z`, remains preserved with zero model
calls and zero extraction attempts. The link fixes a pre-dispatch case-heading
delimiter ambiguity; all 32 source renders and the built image are reused.
The Mathpix supplement remains linked to the same original page selection.

| Document | Original physical pages | Purpose |
| --- | --- | --- |
| Some Characteristic Functions | 4–6 | Dense complete cases within the page span; corrupted native text |
| Linetsky Spectral | 25–29 | Previously affected OCR window and adjacent mathematics |
| Anfuso WWR in Tail | 7–11 | Argument, appendix and charts after references |
| Mean Reversion Bias | 7–10 | OU definitions and moment derivations |
| Breaking Barriers | 3–6 | Table A, figures, continued mathematics and conclusion |
| Information Geometry | 2–5 | Successful ordinary control |
| Combining dependent P-values | 3–6 | Six-panel figure and Tables 1–4 |
| Amplitudes and the Riemann Zeta Function | 1–3 | Previously successful two-column journal/table/figure control |

Total: **32 pages / eight documents**. The plan binds original SHA256s, physical
page maps, native page-label evidence, 200-DPI image hashes and selection reasons.
Eight critical source pages were directly inspected before candidate inference.
Those readings remain in evaluation files and are never supplied to contestants.
Information Geometry author TeX corresponds to byte-identical arXiv v3 PDF bytes;
PRL author TeX is explicitly an alternative version. Both are evaluation only.

## Arms and runtime

The baseline reuses saved MinerU 4.0.12 / DocVortex 0.5.16 / ONNX 1.31.0 output.
All 13 current model/config hashes were rechecked against saved runtime identities.
No baseline OCR is rerun. Historical overlapping-window durations cannot establish
paired per-page extraction speed.

MinerU Pro uses `opendatalab/MinerU2.5-Pro-2605-1.2B` at
`08aaea840498d49ce16247b6263196cf02814885`, with mineru-vl-utils 2.0.7's official
two-step vLLM interface, including image analysis and retained region crops.
GLM-OCR uses `zai-org/GLM-OCR` at
`2e85a62840ccac27daa451df36c736c4636b8628`, with the official SDK revision
`0288f96bb9e78cb439883eaa725eeae90bd177c5` and PP-DocLayoutV3 safetensors at
`e4f489dc536556fc1be02b973ba06756e0d4a2ac`. Its hosted MaaS route is disabled.
Margin/footnote material is retained rather than using the SDK's discard defaults.

Candidate work runs on the peer in separate temporary containers. The pinned base
is the official ARM64 vLLM 0.19.0 image digest
`4f986370d7737abacc70ac17f86695acd1dc7892a02ad89ac132639d5afee0d0`.
The built image is recorded in `runtime-prepared.json`; it preserves Torch
2.10.0+cu129 and installs Transformers 5.3.0 as documented by GLM-OCR.
The image retains three explicit upstream metadata warnings: vLLM and
compressed-tensors declare Transformers <5, and the bundled cuSPARSELt metadata
reports an unsupported platform. These are recorded exceptions, **not a clean
dependency check or proof of GPU compatibility**. Unexpected dependency failures
stop installation. Real BF16 CUDA arithmetic and the retained Information Geometry
page-3 smoke extraction must pass before an arm processes the remaining pages.
No runtime/quantisation sweep or automatic substitute is implemented.

The earlier installed nightly image was inspected and not adopted: its Torch/NCCL
requirements conflict. Failed preparation logs remain under
`results/extraction-comparison-development/`. After the operator's weight cleanup,
disk checks found 219 GiB free on the head and about 2.2 TiB on the peer. Existing
peer downloads/images are reused; model download, unpacking and build space stay
on the peer. Admission reserves 80 GiB disk there and 10 GiB for head outputs.

## Execution and safeguards

```bash
bash scripts/run-extraction-comparison.sh run
bash scripts/run-extraction-comparison.sh status
bash scripts/run-extraction-comparison.sh pause
bash scripts/run-extraction-comparison.sh resume
bash scripts/run-extraction-comparison.sh bundle
```

The launcher runs the required offline checks once for its code identity and starts
tmux `pdf-extraction-comparison`. It installs/reuses the isolated runtime, downloads
only pinned model revisions, checks both nodes and existing GLM ownership/idleness,
captures helper/build/settings/restart-policy identities, and uses the existing
stop/start helpers. Only the verified owned idle regular deployment may be stopped.
The same serving configuration is checked after restoration. GPU execution requires
at least 64 GiB available on the peer after handoff; the actual smoke result remains
the compatibility test. No baseline environment or cache is upgraded.

Each page is reserved durably before extraction. Completed/failed attempts remain;
uncertain dispatch cannot replay automatically. There are zero automatic candidate
model retries. Page content/schema failures can continue; shared integrity/runtime
failures stop the affected arm. Resuming a finished experiment sends zero requests.
Pause drains the current page/model work; it does not kill a healthy request.
The SDK's fixed HTTP read deadline is removed only in the isolated local OCR
container; the endpoint is restricted to its own loopback server. There is no
overall deadline. Compiler/connect safeguards remain separate.

The downstream assignments are complete CF Cases 13–18 and complete Information
Geometry Section 2. Primary tasks are fixed at two assignments × three local arms
× High conversion/Max own-draft focused criticism = **12 maximum**. Each request
uses 131072 output tokens and the existing two-slot scheduler. Invalid/incomplete
conversion prevents criticism. Native CF text is quarantined consistently; other
secondary text uses the existing conservative quality assessment. All arms are
text-only downstream, with the same prompts, source scope and asset policy.
There are at most six existing-policy Low/8192 syntax repairs and one program
readiness request. The unchanged service start helper adds its fixed max-32-token
startup smoke per actual restoration; it is recorded as separate service overhead.
No failed conversion is split/retried automatically. No Mathpix downstream requests
are authorised; see the separate supplementary runbook.

## Reports

`progress.json` updates during extraction and downstream work. `terminal.log` gives
stages/page progress; detailed host/container logs stay under `host-operations/`.
Native outputs, separate readable views, model identities, source images, drafts,
reviews, accuracy logs and compiler outputs remain in the run. `comparison.html`,
`extraction-pages.csv`, `downstream.csv` and inspection ZIPs are generated before
rewriting and again on completion. Expected readings, raw source checks, model
review, compilation and mathematical verification are separate fields.

The automatic fragment checks are deliberately limited. They do not establish
full mathematical fidelity or interpret an absent match as a proven error. The
final recommendation must stay conditional where direct source comparison remains
unfinished. No downstream speed benefit is claimed merely from extraction scores.
After both workers finish, a separate combined inspection ZIP adds the Mathpix arm
without editing either run's bindings or results.


## Later observed results and current continuation

The preparation described above is historical. Read the current pointer: the
selected continuation is `runs/extraction-comparison-20261105T185601Z-layout`.
Its parent `extraction-comparison-20261105T125157Z-qualification` finished normally
with all32 Pro pages and both Pro downstream conversion/critic pairs completed.
All four actual Pro versions compiled. The baseline CF critic exhausted its output
allowance; baseline CF compilation is unresolved. Detailed timing and limitations
are in `INTERIM-DECISION.md`; direct checks in `evaluation/direct-source-review-mineru-pro.json`.

The parent first corrected the Pro context limit using pinned nested metadata
(8192 rather than guessed32768), and supplied a real empty dotenv file required by
the SDK. It then exposed a GLM-OCR import-name mismatch before page processing.
The current continuation uses a process-local compatibility alias to the existing
Transformers5.3.0 V3 Fast processor; the same image, model hashes, preprocessing
and runtime are retained. No installed files or existing failed records are edited.
An offline real-image SDK import test passed. Runtime page qualification is a
separate check; inspect progress before describing the GLM-OCR arm as qualified.
Only its missing pages and original four downstream primary tasks can run. The
other arms and all ten consumed calls are retained. No automatic recursive retries.

The latest Mathpix result remains32 pages, eight submissions, $0.16 local estimate,
seven direct TeX builds passed and one Unicode failure. Finished resume makes zero
requests. The automatic final combined package incorporates the separate Mathpix
results after the selected local run settles. No production queue follows.


## 5 November 2026,19:25 UTC finish — important GLM-OCR validity correction

`extraction-comparison-20261105T185601Z-layout` finished its finite workload and
stopped at19:25:47 UTC. The regular GLM configuration was restored; no production
queue was resumed. All32 GLM-OCR pages returned normal runtime results, but saved
source checks subsequently established a **shared adapter omission**: actual
PP-DocLayoutV3 model labels5/15 are `formula`, while our custom task map accepted
only `display_formula`/`inline_formula`. The SDK silently skips unmatched labels.
`aside_text`/`reference` were unmapped too. CF page5 layout visualisation contains
formula boxes that never reached OCR. All32 native outputs contain zero formula
regions. This is our integration defect, not demonstrated model incapability.

The normal runtime completion flags remain historical evidence, not content
approval. GLM-OCR's CF converter/critic contain visible placeholders and are
INVALID as a full-content speed comparison despite compiling. Its control
converter compiled; revised critic TeX failed, and bounded syntax patch was
rejected. All12 primary calls, one program readiness and two syntax calls across
the lineage are preserved. Nothing was replayed or granted renewed allowances.
The smoke test wrongly admitted prose-only output; this is documented explicitly.

A proposed mapping correction and fail-closed preflight/total-formula-loss guard
are saved under the run's `proposed-label-map-fix/`, with four passing offline
regressions on actual bad output/model labels. They are NOT integrated or runtime
qualified. No rerun was launched after discovering the defect. A new linked plan
must preserve consumed requests and qualify complete mathematical structure before
any further downstream calls. Current finished resume makes zero requests.

The deployed experiment passed841 tests with4 optional skips. Pro and Mathpix
results remain usable for their explicitly sampled checks; Pro's matched CF
conversion/review improvement is real for this scope, but no corpus-wide accuracy
claim follows. Read `DECISION-REPORT.md` and the direct-source-review JSON files.
The final reviewed inspection ZIP is recorded in
`results/extraction-comparison-reviewed-current.json`. Its root report prominently
disqualifies the GLM-OCR comparison and preserves all native evidence. No new
inference, paid usage, deletion, service change or Git mutation occurred in this
final saved-evidence review.
