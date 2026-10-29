# DeepSeek Arm A preparation — 22 October 2026

This is offline preparation evidence, not a model-quality assessment. No existing
DeepSeek implementation or preview was found; one additive path and one preview
were created. The historical paired configuration and all pre-existing application
and test files remain byte-for-byte unchanged.

| Check | Observed result |
|---|---|
| Historical Qwen trial | `qwen-native-trial-20261021T062027Z-a1f40a`, 534 attempted, no pending/interrupted |
| Qwen A usable/failed | 238 structurally completed / 29 failed (26 schema, two JSON, one token limit) |
| Qwen A proposals | 46, UNACCEPTED; no usefulness score inferred |
| Qwen preview resolved through binding | `qwen-native-input-20261021T062027Z-c025fd` |
| DeepSeek preview | `deepseek-arm-a-input-20261022T180153Z-4d91d8` |
| Separate prepared run | `deepseek-arm-a-trial-20261022T180153Z-0ee3cf` |
| Exact comparison | All 267 request bodies identical to A after model normalization; input JSON byte-identical |
| Model / endpoint | `DeepSeek-V4.1-Flash-TF` / `http://127.0.0.1:8894/v1` |
| Images | 267 original crops + sixteen page contexts, 283 deduplicated files with matching hashes |
| Missing/invalid portable drafts | 78 preserved with complete structured OCR, no silent repair |
| Largest saved request | 491,360 bytes, under existing client limit |
| Preparation state | 267 pending, zero dispatches and zero project readiness calls |
| Existing inventory preservation | All 6,948 inventoried files unchanged |
| Preview bound source files | 6,910 |
| Full suite | 190 tests: 175 passed, 15 sandbox loopback bind errors, zero assertion failures |
| New focused tests | All 24 passed |
| Other checks | Python syntax, shell syntax, request/image hashes, report/archive links, ZIP CRC and whitespace passed |

Preview manifest SHA-256:
`5b10c8801a217be076f652105ab686db21f4eeae718096e841096f47e1e64268`.

The read-only deployment record at
`/home/mdi/local-llm/deepseek-flash17-setup/first-serve-853310da-v1/runs/20261022T171904Z-2128368`
matches the supplied endpoint/model and pinned runtime
`sha256:35d9bda39ffde364249f21be294dde6aeee9c51940973477ca5728f32422aa35`.
Its SMOKE-PASS SHA-256 is
`4412af9ec5716fcbc06a1f7bb3fc330e260861c3ed63db0b4dbeacc57e68aaed`.
Arithmetic, three digit images and a blank passed; saved memory after the final
control was about 8.8 GiB head and 13.4 GiB peer. No current network probe was
made by Codex. Smoke success does not establish mathematical OCR accuracy.

The initial offline inspection ZIP is
`results/deepseek-arm-a-trial-20261022T180153Z-0ee3cf-inspection-20261022T180159Z-994ead.zip`,
10,878,589 bytes, SHA-256
`43af39ec3c7dff7011b6bb786ef55196ef9d037245eca94f64af7d35149aedef`.
It contains all comparison ledgers and deduplicated images, not raw base64/API
reasoning. DeepSeek is pending. Raw book material stays ignored under runs/results.

The preparation ran with socket creation, worker spawning and client transport
patched to reject calls. Full test log:
`results/deepseek-full-tests-20261022.txt`. Every error was `socket.bind` raising
`PermissionError: [Errno 1] Operation not permitted` in an existing mock-server
test. No sandbox settings were changed; the operator must run the full normal-
terminal command in [the runbook](../DEEPSEEK-ARM-A-TRIAL.md).

Regression checks exercise actual client serialization through a synthetic
transport, exact model separation, strict response/coverage/TeX checks, 12-region
gate, at-most-once reservations, interruption/recovery, persistent stops/budget,
two-failure pause, failed-response identity, read-only waiting and partial bundles.
The preservation inventory covers pre-existing source/tests/scripts, completed
Qwen trial and its preview, native pilot and conversion. It does not claim a new
byte audit of every older result ZIP. Verification details are saved in
`results/deepseek-preparation-validation-20261022.json`.

Remaining: operator full tests, fresh project preflight, live reliability gate
and trial, then full-replacement/unchanged-control source inspection. Unsupported
TeX is separately export-blocked. No mathematical correctness, compilation,
memory headroom under sustained load or unattended live success is established.
